"""FastAPI application for the 27vette workbook manager.

Run from the repo root:

    .venv/bin/python -m uvicorn app.main:app \
        --app-dir workbook-manager/backend --port 8050

or use ``workbook-manager/run.sh``.
"""

from __future__ import annotations

import contextlib
import json
import os
import time
from pathlib import Path

import anyio
from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from . import (
    config,
    apply_rebuild,
    asset_resolutions,
    asset_workspace,
    db as dbmod,
    drafts,
    explorer,
    form_graph as form_graph_mod,
    importer,
    staging,
    sync as syncmod,
)
from .naming import display_id, humanize, sheet_display_name
from .schemas import (
    ApprovalRequest,
    ApplyRebuildRequest,
    AssetResolutionRequest,
    AssetSafeBulkRequest,
    ChangeOut,
    CommitRequest,
    DraftOperationRequest,
    ManualResolutionRequest,
    StageChangeRequest,
    SyncRequest,
    TableSchemaOut,
)
from .catalog import (
    MODEL_COLLECTIONS,
    REFERENCE_OPTION_PRESENTATION,
    SPEC_BY_FAMILY,
    SHARED_TABLES,
    SPEC_BY_TABLE,
    STRUCTURE_TABLES,
    TABLE_SPECS,
)
from .staging import StagingError
from .validation import find_dependents

WORKFLOW_MODE = "durable_apply_rebuild"
PROVISIONAL_MODE = "read_only_provisional"  # permanent legacy sync refusal token
IMPORT_TERMINAL_ALLOWLIST = (
    "applied",
    "cancelled",
    "manually_resolved_restored",
    "manually_resolved_applied",
    "abandoned_unknown",
)

# Bounded wait for a request to become a projection reader while a promotion
# holds the gate. Requests fail closed with 503 instead of hanging.
READER_WAIT_SECONDS = float(os.environ.get("WBM_READER_WAIT_SECONDS", "10"))
# Bounded wait for the shared durable-state lock. Also fails closed with 503.
STATE_LOCK_WAIT_SECONDS = float(os.environ.get("WBM_STATE_LOCK_WAIT_SECONDS", "30"))

_STORAGE_READY = False


@contextlib.asynccontextmanager
async def lifespan(app: FastAPI):
    """Bootstrap/migrate storage before the app serves any request."""
    global _STORAGE_READY
    config.ensure_dirs()
    app.state.storage_bootstrap = dbmod.bootstrap_storage(
        config.DEFAULT_DB, config.DEFAULT_PROJECTION_DB
    )
    _STORAGE_READY = True
    try:
        yield
    finally:
        _STORAGE_READY = False


def _require_storage_ready() -> None:
    """Fail with an explicit reason when the app is served without its lifespan."""
    if not _STORAGE_READY:
        raise HTTPException(503, detail={
            "status": "storage_not_bootstrapped",
            "message": "storage bootstrap runs in the FastAPI lifespan; serve "
                       "the app through its lifespan (uvicorn, or TestClient "
                       "entered as a context manager) before issuing requests",
        })


app = FastAPI(
    title="27vette Workbook Manager", version="0.1.0", lifespan=lifespan
)


def open_projection_connection():
    """Open one disposable-projection connection. The caller closes it."""
    return dbmod.connect(config.DEFAULT_PROJECTION_DB)


def open_state_connection():
    """Open one durable-state connection with manager-owned FK enforcement."""
    return dbmod.connect(config.DEFAULT_DB, foreign_keys=True)


def projection_connection():
    """Request-scoped projection connection held under the reader gate."""
    _require_storage_ready()
    stack = contextlib.ExitStack()
    try:
        stack.enter_context(
            dbmod.PROJECTION_GATE.reader(timeout=READER_WAIT_SECONDS)
        )
    except dbmod.ProjectionBusyError as exc:
        raise HTTPException(503, detail={
            "status": "projection_promotion_in_progress",
            "message": str(exc),
        }) from exc
    conn = open_projection_connection()
    try:
        yield conn
    finally:
        conn.close()
        stack.close()


def state_connection():
    """Request-scoped durable-state connection."""
    _require_storage_ready()
    conn = open_state_connection()
    try:
        yield conn
    finally:
        conn.close()


async def durable_write_lock():
    """Serialize durable-state mutation, promotion, and workbook apply.

    Declared before ``projection_connection`` on every mutating endpoint so the
    lock is always taken before a projection reader; promotion takes the lock
    and then quiesces readers, so the two orders cannot deadlock.

    Deliberately an ``async`` dependency that polls ``acquire(blocking=False)``:
    blocking on the lock from a threadpool worker parks an anyio thread token,
    and once every token is parked the lock holder can never get a thread to
    finish and release it — a permanent process wedge. Waiting on the event loop
    consumes no token, and the wait is bounded so contention degrades to 503
    rather than hanging.
    """
    deadline = time.monotonic() + STATE_LOCK_WAIT_SECONDS
    while not dbmod.STATE_LOCK.acquire(blocking=False):
        if time.monotonic() >= deadline:
            raise HTTPException(503, detail={
                "status": "state_lock_busy",
                "message": "another durable-state operation held the manager "
                           f"lock for more than {STATE_LOCK_WAIT_SECONDS}s",
            })
        await anyio.sleep(0.01)
    try:
        yield
    finally:
        dbmod.STATE_LOCK.release()


def _staging_error(exc: StagingError):
    return HTTPException(status_code=422, detail={"errors": exc.errors})


def _draft_error(exc: drafts.DraftError):
    if exc.code == "draft_not_found":
        status_code = 404
    elif exc.code in {
        "projection_not_current", "draft_not_mutable", "draft_binding_mismatch"
    }:
        status_code = 409
    else:
        status_code = 422
    return HTTPException(status_code=status_code, detail={
        "status": exc.code,
        "message": str(exc),
        "errors": exc.errors,
    })


def _workbook_state(conn) -> dict:
    path = config.DEFAULT_WORKBOOK
    imported_mtime = dbmod.get_meta(conn, "workbook_mtime_ns")
    imported_sha = dbmod.get_meta(conn, "workbook_sha256")
    identity = importer.workbook_identity(path) if path.exists() else None
    current_mtime = str(identity["mtime_ns"]) if identity else ""
    current_sha = str(identity["sha256"]) if identity else ""
    if not path.exists():
        state = "missing"
    elif not imported_mtime or not imported_sha:
        state = "unbound"
    elif imported_mtime != current_mtime or imported_sha != current_sha:
        state = "stale"
    else:
        state = "current"
    return {
        "state": state,
        "workbook_path": str(path),
        "exists": path.exists(),
        "imported_mtime_ns": imported_mtime,
        "current_mtime_ns": current_mtime,
        "imported_sha256": imported_sha,
        "current_sha256": current_sha,
        "stale": state == "stale",
        "excel_lock": (path.parent / f"~${path.name}").exists(),
    }


def _projection_active(conn) -> bool:
    if dbmod.get_meta(conn, "workbook_sha256"):
        return True
    if conn.execute("SELECT 1 FROM import_runs LIMIT 1").fetchone():
        return True
    if conn.execute("SELECT 1 FROM raw_sheet_rows LIMIT 1").fetchone():
        return True
    return any(conn.execute(
        f"SELECT 1 FROM {spec.table} LIMIT 1").fetchone()
        for spec in TABLE_SPECS)


def _import_blockers(conn) -> dict:
    terminal_placeholders = ",".join("?" for _ in IMPORT_TERMINAL_ALLOWLIST)
    active = conn.execute(
        f"SELECT COUNT(*) c FROM workflow_drafts WHERE status NOT IN "
        f"({terminal_placeholders})",
        IMPORT_TERMINAL_ALLOWLIST,
    ).fetchone()["c"]
    staged = conn.execute(
        "SELECT COUNT(*) c FROM pending_changes WHERE status='staged'"
    ).fetchone()["c"]
    committed_history = conn.execute(
        "SELECT COUNT(*) c FROM change_history WHERE status='committed' "
        "AND sync_status='pending'"
    ).fetchone()["c"]
    committed_without_history = conn.execute(
        "SELECT COUNT(*) c FROM pending_changes p WHERE p.status='committed' "
        "AND NOT EXISTS (SELECT 1 FROM change_history h WHERE "
        "h.pending_change_id=p.id)"
    ).fetchone()["c"]
    failed_history = conn.execute(
        "SELECT COUNT(*) c FROM change_history WHERE status='failed' "
        "OR sync_status='sync_failed'"
    ).fetchone()["c"]
    failed_pending = conn.execute(
        "SELECT COUNT(*) c FROM pending_changes p WHERE "
        "p.status IN ('failed', 'sync_failed') AND NOT EXISTS (SELECT 1 FROM "
        "change_history h WHERE h.pending_change_id=p.id)"
    ).fetchone()["c"]
    committed_unsynchronized = committed_history + committed_without_history
    failed = failed_history + failed_pending
    legacy_recovery = 0
    if conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' "
        "AND name='legacy_recovery_records'"
    ).fetchone():
        legacy_recovery = conn.execute(
            "SELECT COUNT(*) c FROM legacy_recovery_records WHERE unresolved=1"
        ).fetchone()["c"]
    return {
        "active": active,
        "staged": staged,
        "committed_unsynchronized": committed_unsynchronized,
        "failed": failed,
        "legacy_recovery": legacy_recovery,
        "unresolved_total": (
            active + staged + committed_unsynchronized + failed + legacy_recovery
        ),
    }


def _projection_manifest(conn) -> dict:
    """Identity of the projection this request actually opened."""
    manifest = dbmod.storage_manifest(conn) or {}
    return {
        "store_kind": manifest.get("store_kind", ""),
        "migration_id": manifest.get("migration_id", ""),
        "source_sha256": manifest.get("source_sha256", ""),
        "schema_version": manifest.get("schema_version"),
    }


def _projection_state(conn, run, workbook: dict) -> dict:
    active = _projection_active(conn)
    blocking_findings = 0
    if run:
        blocking_findings = conn.execute(
            "SELECT COUNT(*) c FROM import_issues WHERE run_id=? "
            "AND severity='error'", (run["id"],)
        ).fetchone()["c"]
    if not active:
        state = "missing"
    elif workbook["state"] != "current":
        state = "stale"
    elif not run or run["status"] != "imported" or blocking_findings:
        state = "unverified"
    else:
        state = "current"
    return {
        "state": state,
        "active": active,
        "blocking_findings": blocking_findings,
        "reimport_allowed": state in {"current", "stale", "missing", "unverified"},
        "manifest": _projection_manifest(conn),
    }


# ── status / import ──────────────────────────────────────────────────

@app.get("/api/status")
def status(
    conn=Depends(projection_connection),
    state_conn=Depends(state_connection),
):
    counts = {s.table: conn.execute(
        f"SELECT COUNT(*) c FROM {s.table}").fetchone()["c"]
        for s in TABLE_SPECS}
    staged = state_conn.execute(
        "SELECT COUNT(*) c FROM pending_changes WHERE status='staged'"
    ).fetchone()["c"]
    unsynced = state_conn.execute(
        "SELECT COUNT(*) c FROM change_history WHERE sync_status='pending'"
    ).fetchone()["c"]
    run = conn.execute(
        "SELECT * FROM import_runs ORDER BY id DESC LIMIT 1").fetchone()
    workbook = _workbook_state(conn)
    projection = _projection_state(conn, run, workbook)
    blockers = _import_blockers(state_conn)
    projection["reimport_allowed"] = (
        workbook["exists"]
        and projection["state"] in {"current", "stale", "missing", "unverified"}
        and blockers["unresolved_total"] == 0
    )
    return {
        "mode": WORKFLOW_MODE,
        "projection": projection,
        "draft": {
            "state": "blocked" if blockers["unresolved_total"] else "clear",
            **blockers,
            "terminal_import_allowlist": list(IMPORT_TERMINAL_ALLOWLIST),
        },
        "workbook": workbook,
        **apply_rebuild.output_status(
            state_conn,
            workbook_path=config.DEFAULT_WORKBOOK,
            repository_root=config.APPLY_OUTPUT_ROOT,
        ),
        "tables": counts,
        "staged_changes": staged,
        "unsynced_committed_changes": unsynced,
        "last_import": dict(run) if run else None,
    }


@app.post("/api/import")
def run_import(
    _lock=Depends(durable_write_lock),
    state_conn=Depends(state_connection),
):
    if not config.DEFAULT_WORKBOOK.exists():
        raise HTTPException(404, f"workbook not found: "
                                 f"{config.DEFAULT_WORKBOOK}")
    blockers = _import_blockers(state_conn)
    if blockers["unresolved_total"]:
        raise HTTPException(409, detail={
            "status": PROVISIONAL_MODE,
            "message": "re-import refused: unresolved legacy "
                       "draft/synchronization work exists",
            "import_blockers": blockers,
        })
    try:
        report = importer.promote_verified_projection(
            config.DEFAULT_WORKBOOK, config.DEFAULT_PROJECTION_DB
        )
    except dbmod.ProjectionBusyError as exc:
        raise HTTPException(503, detail={
            "status": "projection_readers_busy",
            "message": str(exc),
        }) from exc
    if not report["promoted"]:
        status_code = 409 if report["status"] == "source_changed" else 422
        raise HTTPException(status_code, detail=report)
    conn = open_projection_connection()
    try:
        latest = importer.latest_report(conn)
        if latest is None:
            raise RuntimeError("promoted projection is missing its import manifest")
        workbook = _workbook_state(conn)
        projection = _projection_state(conn, latest["run"], workbook)
    finally:
        conn.close()
    report["projection"] = projection
    report["verified"] = projection["state"] == "current"
    report["mode"] = PROVISIONAL_MODE
    return report


@app.get("/api/import/latest")
def latest_import(conn=Depends(projection_connection)):
    report = importer.latest_report(conn)
    if report is None:
        raise HTTPException(404, "no import has run yet")
    return report


# ── models / structure ───────────────────────────────────────────────

@app.get("/api/models")
def models(conn=Depends(projection_connection)):
    rows = conn.execute(
        "SELECT m.*, p.promoted_to_runtime, p.display_order AS "
        "promotion_order FROM models m LEFT JOIN model_registry_promotion p "
        "ON p.model_key = m.model_key ORDER BY p.display_order, m.model_key"
    ).fetchall()
    out = []
    for r in rows:
        d = dict(r)
        d["label"] = d.get("model_label") or humanize(d["model_key"])
        regs = conn.execute(
            "SELECT source_role, sheet_name, active FROM sheet_registry "
            "WHERE model_key=? ORDER BY source_role", (d["model_key"],)
        ).fetchall()
        d["sources"] = [dict(x) for x in regs]
        d["scaffold"] = d.get("active") != "True"
        out.append(d)
    return {"models": out}


@app.get("/api/structure/{model_key}")
def structure(
    model_key: str,
    draft_id: str = "",
    conn=Depends(projection_connection),
    state_conn=Depends(state_connection),
):
    # Checkpoint 4: serve the full connected form graph (spec §8) instead of
    # joining only section_presentation rows. The graph builder resolves step
    # placement presentation-first/master-fallback, scopes membership to
    # model-connected sections, and classifies buckets/context/summary/unmapped
    # records. Top-level legacy keys are preserved so existing consumers keep
    # their contract; steps[].sections now reflects complete membership.
    graph = form_graph_mod.build_form_graph(conn, model_key)
    if draft_id:
        graph = form_graph_mod.apply_draft_overlay(
            graph,
            drafts.list_operations(state_conn, draft_id),
        )
    return {
        "model_key": graph["model_key"],
        "projection_identity": {
            "workbook_sha256": dbmod.get_meta(conn, "workbook_sha256"),
            "workbook_mtime_ns": dbmod.get_meta(conn, "workbook_mtime_ns"),
        },
        "graph": {
            "version": graph["graph_version"],
            "fingerprint": graph["fingerprint"],
            "steps": graph["steps"],
            "buckets": graph["buckets"],
            "summary_only": graph["summary_only"],
            "section_nodes": graph["section_nodes"],
            "unmapped_sections": graph["unmapped_sections"],
            "inactive_records": graph["inactive_records"],
            "counts": graph["counts"],
            "draft_overlay": graph["draft_overlay"],
            "parity": graph["parity"],
            "evidence": graph["evidence"],
        },
        "steps": graph["steps"],
        "section_presentation": graph["section_presentation"],
        "context_sections": graph["context_sections"],
        "order_summary_sections": graph["order_summary_sections"],
        "step_order_summary_map": graph["step_order_summary_map"],
        "sections_master": graph["sections_master"],
        "variants": graph["variants"],
        "editing": graph["editing"],
    }


@app.get("/api/models/{model_key}/collections")
def collections(model_key: str, conn=Depends(projection_connection)):
    out = []
    for table in MODEL_COLLECTIONS:
        spec = SPEC_BY_TABLE[table]
        sheet = staging.target_sheet_for(conn, spec, model_key)
        if spec.model_scoped:
            if not sheet:
                continue  # model does not register this source role
            count = conn.execute(
                f"SELECT COUNT(*) c FROM {table} WHERE model_id=?",
                (model_key,)).fetchone()["c"]
        elif spec.has_model_key_column:
            count = conn.execute(
                f"SELECT COUNT(*) c FROM {table} WHERE model_key=?",
                (model_key,)).fetchone()["c"]
            if count == 0 and table not in ("assets",):
                # still list core collections; skip only empty optional ones
                pass
        else:
            count = conn.execute(
                f"SELECT COUNT(*) c FROM {table}").fetchone()["c"]
        reg_active = True
        if spec.role:
            reg = conn.execute(
                "SELECT active FROM sheet_registry WHERE model_key=? AND "
                "source_role=?", (model_key, spec.role)).fetchone()
            reg_active = bool(reg and reg["active"] == "True")
        out.append({
            "table": table,
            "label": spec.label or humanize(table),
            "sheet": sheet,
            "sheet_label": sheet_display_name(sheet) if sheet else "",
            "count": count,
            "editable": spec.editable and reg_active,
            "scaffold": not reg_active if spec.role else False,
        })
    # shared reference collections
    for table in SHARED_TABLES:
        spec = SPEC_BY_TABLE[table]
        count = conn.execute(f"SELECT COUNT(*) c FROM {table}").fetchone()["c"]
        out.append({
            "table": table, "label": spec.label or humanize(table),
            "sheet": spec.sheet[0] if spec.sheet else "",
            "sheet_label": sheet_display_name(spec.sheet[0])
            if spec.sheet else "",
            "count": count, "editable": spec.editable, "shared": True,
            "scaffold": False,
        })
    return {"model_key": model_key, "collections": out}


@app.get("/api/explorer/{model_key}/options/{option_id}")
def connected_option(
    model_key: str,
    option_id: str,
    draft_id: str = Query("", max_length=240),
    conn=Depends(projection_connection),
    state_conn=Depends(state_connection),
):
    detail = explorer.option_detail(conn, model_key, option_id)
    if detail is None and draft_id:
        try:
            addition = drafts.connected_addition(
                state_conn,
                draft_id=draft_id,
                table="options",
                model_key=model_key,
                entity_key={"option_id": option_id},
            )
        except drafts.DraftError as exc:
            raise _draft_error(exc)
        if addition is not None:
            proposed = {
                **addition["final"],
                "src_sheet": addition["source_sheet"],
                "src_family": addition["family"],
                "src_row": addition["source_row"],
                "physical_key": addition["physical_key"],
            }
            detail = explorer.option_detail(
                conn, model_key, option_id, option_record=proposed
            )
    if detail is None:
        raise HTTPException(
            404,
            detail={
                "status": "option_not_found",
                "message": f"option {option_id!r} was not found for model {model_key!r}",
            },
        )
    try:
        detail["draft_overlay"] = drafts.connected_overlay(
            state_conn,
            draft_id=draft_id,
            model_key=model_key,
            lineage=detail["technical"]["lineage"],
            base=detail["option"],
            projection_workbook_sha256=_workbook_state(conn)["imported_sha256"],
        )
    except drafts.DraftError as exc:
        raise _draft_error(exc)
    return detail


@app.get("/api/explorer/{model_key}/groups/{group_type}/{group_id}")
def connected_group(
    model_key: str,
    group_type: str,
    group_id: str,
    draft_id: str = Query("", max_length=240),
    conn=Depends(projection_connection),
    state_conn=Depends(state_connection),
):
    detail = explorer.group_detail(conn, model_key, group_type, group_id)
    if detail is None:
        raise HTTPException(404, detail={
            "status": "group_not_found",
            "message": f"{group_type} group {group_id!r} was not found for model {model_key!r}",
        })
    try:
        detail["draft_overlay"] = drafts.connected_overlay(
            state_conn,
            draft_id=draft_id,
            model_key=model_key,
            lineage=detail["technical"]["lineage"],
            base=detail["group"],
            projection_workbook_sha256=_workbook_state(conn)["imported_sha256"],
        )
    except drafts.DraftError as exc:
        raise _draft_error(exc)
    return detail


@app.get("/api/explorer/{model_key}/sections/{section_id}")
def connected_section(
    model_key: str, section_id: str, conn=Depends(projection_connection)
):
    detail = explorer.section_detail(conn, model_key, section_id)
    if detail is None:
        raise HTTPException(404, detail={
            "status": "section_not_found",
            "message": "section not found in selected model",
        })
    return detail


@app.get("/api/explorer/{model_key}/rules/{rule_id}")
def connected_rule(
    model_key: str, rule_id: str, conn=Depends(projection_connection)
):
    detail = explorer.rule_detail(conn, model_key, rule_id)
    if detail is None:
        raise HTTPException(404, detail={
            "status": "rule_not_found",
            "message": "rule not found in selected model",
        })
    return detail


@app.get("/api/explorer/{model_key}/search")
def explorer_search(
    model_key: str,
    query: str = Query(..., min_length=1, max_length=200),
    limit: int = Query(40, ge=1, le=100),
    conn=Depends(projection_connection),
):
    return {"model_key": model_key, "query": query,
            "results": explorer.search(conn, model_key, query, limit=limit)}


@app.get("/api/explorer/{model_key}/diagnostics")
def explorer_diagnostics(model_key: str):
    return {"model_key": model_key, "diagnostics": explorer.diagnostic_catalog()}


@app.get("/api/explorer/{model_key}/diagnostics/{diagnostic_key}")
def explorer_diagnostic_results(
    model_key: str,
    diagnostic_key: str,
    entity_id: str = Query("", max_length=240),
    limit: int = Query(100, ge=1, le=200),
    conn=Depends(projection_connection),
):
    try:
        results = explorer.diagnostic_results(
            conn, model_key, diagnostic_key, entity_id=entity_id, limit=limit
        )
    except ValueError as exc:
        raise HTTPException(422, detail={
            "status": "diagnostic_entity_required", "message": str(exc),
        }) from exc
    if results is None:
        raise HTTPException(404, detail={
            "status": "diagnostic_not_found",
            "message": f"unknown diagnostic {diagnostic_key!r}",
        })
    definition = next(item for item in explorer.diagnostic_catalog()
                      if item["key"] == diagnostic_key)
    return {"model_key": model_key, "diagnostic": definition,
            "entity_id": entity_id, "results": results}


@app.get("/api/assets/reconciliation")
def asset_reconciliation(
    refresh: bool = False,
    model: str = Query("", max_length=80),
    section: str = Query("", max_length=160),
    target_type: str = Query("", max_length=80),
    coverage_intent: str = Query("", max_length=80),
    status: str = Query("", max_length=80),
    offset: int = Query(0, ge=0),
    limit: int = Query(24, ge=1, le=100),
    draft_id: str = Query("", max_length=120),
    conn=Depends(projection_connection),
    state_conn=Depends(state_connection),
):
    """Typed, read-only view over the shared asset reconciliation result."""

    workbook = _workbook_state(conn)
    if workbook["state"] != "current":
        raise HTTPException(409, detail={
            "status": "asset_reconciliation_workbook_not_current",
            "message": "Asset Manager requires a verified current projection of the workbook.",
        })
    try:
        snapshot = asset_workspace.get_asset_manager_snapshot(
            config.DEFAULT_WORKBOOK, refresh=refresh
        )
        ignored = drafts.active_asset_ignores(
            state_conn, fingerprints=snapshot.fingerprints
        )
        view = asset_workspace.asset_map_sync.filter_asset_manager_snapshot(
            snapshot,
            model_key=model,
            section_id=section,
            target_type=target_type,
            coverage_intent=coverage_intent,
            status=status,
            offset=offset,
            limit=limit,
            ignored_item_ids=ignored,
        )
        image_fit = SPEC_BY_TABLE["assets"].column_by_name("image_fit")
        view["controls"] = {
            "image_fit": list(image_fit.enum if image_fit is not None else ()),
        }
        evidence = drafts.list_asset_resolutions(state_conn, draft_id) if draft_id else []
        view["draft_asset_resolutions"] = {
            "count": len(evidence),
            "item_ids": [row["item_id"] for row in evidence],
            "stale_count": sum(
                1 for row in evidence
                if any(
                    row[field] != snapshot.fingerprints.get(field)
                    for field in (
                        "reconciliation_sha256",
                        "media_inventory_sha256",
                        "workbook_sha256",
                    )
                )
            ),
        }
        return view
    except asset_workspace.asset_map_sync.WordPressMediaFetchError as exc:
        raise HTTPException(502, detail={
            "status": "asset_media_inventory_unavailable",
            "message": str(exc),
        }) from exc
    except (OSError, ValueError) as exc:
        raise HTTPException(422, detail={
            "status": "asset_reconciliation_failed",
            "message": str(exc),
        }) from exc


@app.get("/api/assets/media-options")
def asset_media_options(
    query: str = Query("", max_length=200),
    limit: int = Query(50, ge=1, le=100),
    conn=Depends(projection_connection),
):
    workbook = _workbook_state(conn)
    if workbook["state"] != "current":
        raise HTTPException(409, detail={
            "status": "asset_reconciliation_workbook_not_current",
            "message": "Asset Manager requires a verified current projection of the workbook.",
        })
    try:
        return asset_workspace.search_media_options(
            config.DEFAULT_WORKBOOK, query, limit=limit
        )
    except (OSError, ValueError) as exc:
        raise HTTPException(422, detail={
            "status": "asset_reconciliation_failed",
            "message": str(exc),
        }) from exc


@app.get("/api/tables")
def tables(conn=Depends(projection_connection)):
    return {"structure_tables": [
        _schema_dict(conn, SPEC_BY_TABLE[t], None) for t in STRUCTURE_TABLES]}


# ── records ──────────────────────────────────────────────────────────

class SchemaIntegrityError(RuntimeError):
    """Raised when schema construction would expose uncontrolled or
    contradictory field metadata (spec §10.2 fail-closed requirements)."""


def _family_controls(spec) -> dict:
    """Registry-owned control metadata for a spec's family.

    Writable specs resolve through ``editor_family``; read-only projections
    such as ``form_sections`` carry no editor family and resolve through
    ``family``. The registry owns both inventories (AGENTS.md §3).
    """
    from corvette_form_generator.workbook_domain import registry

    return registry.controls_for_family(spec.editor_family or spec.family)


def _validate_control_integrity(spec) -> None:
    """Fail closed before any column is exposed (§10.2).

    - a writable field has no control metadata;
    - metadata kind contradicts registered type/enum/reference data;
    - blank/required behavior disagrees with registry validation;
    - a key is editable during update / generated-read-only fields are
      excluded from payloads by the mutation guard on `control.kind`.
    """
    from corvette_form_generator.workbook_domain import registry

    family_controls = _family_controls(spec)
    if not spec.editable:
        # Read-only projections carry no writable controls; grading them
        # against the writable inventory would fail closed on every column
        # (§10.2 applies to writable fields). Still fail closed on a column
        # with no deliberate read-only control at all.
        for c in spec.columns:
            control = family_controls.get(c.header)
            if control is None:
                raise SchemaIntegrityError(
                    f"{spec.table}.{c.sql_name()}: read-only field has no "
                    "control metadata"
                )
            if control.get("kind") != "read_only":
                raise SchemaIntegrityError(
                    f"{spec.table}.{c.header}: read-only field has control "
                    f"kind {control.get('kind')!r}"
                )
        return
    for c in spec.columns:
        header = c.header
        control = family_controls.get(header)
        if control is None:
            raise SchemaIntegrityError(
                f"{spec.table}.{c.sql_name()}: writable field has no "
                "control metadata"
            )
        kind = control.get("kind")
        if kind not in registry.CONTROL_KINDS:
            raise SchemaIntegrityError(
                f"{spec.table}.{header}: unknown control kind {kind!r}"
            )
        structural_kind = _structural_kind(spec, c)
        if structural_kind == "reference" and kind != "reference":
            raise SchemaIntegrityError(
                f"{spec.table}.{header}: reference field has control kind {kind!r}"
            )
        if structural_kind == "finite" and kind not in ("finite", "reference"):
            raise SchemaIntegrityError(
                f"{spec.table}.{header}: finite field has control kind {kind!r}"
            )
        if structural_kind == "boolean" and kind != "boolean":
            raise SchemaIntegrityError(
                f"{spec.table}.{header}: boolean field has control kind {kind!r}"
            )
        if structural_kind == "integer" and kind not in ("integer", "money"):
            raise SchemaIntegrityError(
                f"{spec.table}.{header}: integer field has control kind {kind!r}"
            )
        if structural_kind == "text":
            allowed_text_kinds = {"short_text", "long_text", "structured_text", "url"}
            if (spec.editor_family, header) in registry.PROVEN_FINITE_VALUES:
                allowed_text_kinds.add("finite")
            if (spec.editor_family, header) in registry.BOOLEAN_INHERIT_BLANK:
                allowed_text_kinds.add("boolean")
            if kind not in allowed_text_kinds:
                raise SchemaIntegrityError(
                    f"{spec.table}.{header}: text field has control kind {kind!r}"
                )
        expected_values = tuple(
            registry.PROVEN_FINITE_VALUES.get(
                (spec.editor_family, header), c.enum
            )
        )
        if expected_values and tuple(control.get("values", ())) != expected_values:
            raise SchemaIntegrityError(
                f"{spec.table}.{header}: control values disagree with registry domain"
            )
        if c.sql_name() in spec.key and not control.get("immutable_on_edit"):
            raise SchemaIntegrityError(
                f"{spec.table}.{header}: key control must be immutable on edit"
            )
        blank = control.get("blank", "")
        should_allow_blank = (
            header in spec.optional_columns
            or "" in c.enum
            or (spec.editor_family, header)
            in registry.BOOLEAN_INHERIT_BLANK
        )
        actual_blank_allowed = blank != "forbidden" and blank != "never_blank_key"
        if should_allow_blank != actual_blank_allowed:
            raise SchemaIntegrityError(
                f"{spec.table}.{header}: blank={blank!r} disagrees with "
                f"registry optional={header in spec.optional_columns}"
            )
    _reference_contract(spec)


def _structural_kind(spec, c) -> str:
    ref_by_col = {ref.column: ref for ref in spec.refs}
    conditional_column = dict(spec.conditional_ref).get("column", "")
    if c.sql_name() in ref_by_col:
        return "reference"
    if c.header == conditional_column:
        return "reference"
    if c.enum:
        return "finite"
    if c.ctype == "bool":
        return "boolean"
    return "integer" if c.ctype == "int" else "text"


def _reference_presentation(target: str) -> dict:
    """Return a presentation adapter only when every named column exists."""
    presentation = REFERENCE_OPTION_PRESENTATION.get(target)
    if presentation is None:
        raise SchemaIntegrityError(
            f"reference target {target!r} has no human-label presentation"
        )
    table = str(presentation.get("table") or target)
    target_spec = SPEC_BY_TABLE.get(table)
    if target_spec is None:
        raise SchemaIntegrityError(
            f"reference target {target!r} resolves to unknown table {table!r}"
        )
    registered = {column.sql_name() for column in target_spec.columns}
    required = {
        str(presentation["value"]),
        *(str(column) for column in presentation["labels"]),
    }
    active_column = str(presentation.get("active") or "")
    if active_column:
        required.add(active_column)
    missing = sorted(required - registered)
    if missing:
        raise SchemaIntegrityError(
            f"reference target {target!r} presentation uses unregistered "
            f"columns: {missing}"
        )
    return presentation


def _reference_contract(spec, field: str | None = None,
                        discriminator: str = "") -> dict:
    """Resolve registry-owned reference targets without accepting table input."""
    direct = {
        ref.column: ref for ref in spec.refs
    }
    conditional = dict(spec.conditional_ref)
    conditional_column = conditional.get("column", "")

    if field is None:
        targets = []
        for ref in spec.refs:
            targets.extend(ref.union_tables or (ref.target_table,))
        for family in dict(spec.conditional_refs).values():
            if family is None:
                continue
            targets.append(
                SPEC_BY_FAMILY[family].table if family in SPEC_BY_FAMILY else family
            )
        for target in set(targets):
            _reference_presentation(target)
        return {}

    column = spec.column_by_name(field)
    if column is None:
        raise HTTPException(404, detail={
            "status": "unknown_reference_field",
            "message": f"{spec.table}.{field} is not a registered field",
        })
    ref = direct.get(column.sql_name())
    if ref:
        for target in ref.union_tables or (ref.target_table,):
            _reference_presentation(target)
        return {
            "scope": ref.scope,
            "targets": list(ref.union_tables or (ref.target_table,)),
        }
    if column.header != conditional_column:
        raise HTTPException(422, detail={
            "status": "field_is_not_reference",
            "message": f"{spec.table}.{field} is not a reference field",
        })
    if not discriminator:
        raise HTTPException(422, detail={
            "status": "reference_discriminator_required",
            "message": f"{spec.table}.{field} requires "
                       f"{conditional.get('discriminator', 'a discriminator')}",
        })
    conditional_targets = dict(spec.conditional_refs)
    if discriminator not in conditional_targets:
        raise HTTPException(422, detail={
            "status": "invalid_reference_discriminator",
            "message": f"{discriminator!r} is not registered for "
                       f"{spec.table}.{field}",
        })
    family = conditional_targets[discriminator]
    if family is None:
        return {"scope": "none", "targets": []}
    target = SPEC_BY_FAMILY[family].table if family in SPEC_BY_FAMILY else family
    _reference_presentation(target)
    return {"scope": "model", "targets": [target]}


# Version of the normalized table-schema response contract. Bump when the
# per-column metadata shape changes so stale browser bundles cannot silently
# misrender new kinds.
TABLE_SCHEMA_VERSION = "workbook-manager-table-schema-2"


def _schema_dict(conn, spec, model_key: str | None) -> dict:
    cols = []
    ref_by_col = {r.column: r for r in spec.refs}
    conditional = dict(spec.conditional_ref)
    conditional_column = conditional.get("column", "")
    conditional_targets = dict(spec.conditional_refs)
    _validate_control_integrity(spec)
    from corvette_form_generator.workbook_domain import registry as _registry

    family_controls = _family_controls(spec)
    for c in spec.columns:
        ref = ref_by_col.get(c.sql_name())
        reference = None
        field_kind = "free_text"
        finite_values = list(c.enum)
        if c.ctype == "bool" and not finite_values:
            finite_values = ["True", "False"]
        if ref:
            reference = {
                "kind": "union" if ref.union_tables else "ordinary",
                "table": ref.target_table,
                "column": ref.target_column,
                "scope": ref.scope,
                "union": list(ref.union_tables),
            }
            field_kind = "reference"
        elif c.header == conditional_column:
            targets = []
            for value, family in conditional_targets.items():
                if family is None:
                    targets.append({"value": value, "target": None, "derived": False})
                    continue
                target_table = SPEC_BY_FAMILY[family].table if family in SPEC_BY_FAMILY else family
                targets.append({
                    "value": value,
                    "target": target_table,
                    "derived": family not in SPEC_BY_FAMILY,
                })
            reference = {
                "kind": "conditional",
                "discriminator": conditional.get("discriminator", ""),
                "targets": targets,
            }
            field_kind = "reference"
        elif finite_values:
            field_kind = "finite"
        cols.append({
            "name": c.sql_name(), "header": c.header,
            "label": humanize(c.sql_name()), "ctype": c.ctype,
            "enum": list(c.enum), "is_key": c.sql_name() in spec.key,
            "optional": c.header in spec.optional_columns,
            "required_on_add": c.header in spec.required_on_add,
            "required_on_effective_active_row": (
                c.header in spec.required_on_effective_active_row
            ),
            "field_kind": field_kind,
            "finite_values": finite_values,
            "reference": reference,
            # Retain the existing response member through Pass 7's UI update.
            "ref": reference if ref else None,
            # Checkpoint 3B: normalized control metadata from the shared
            # registry (spec §10.1/§10.2).
            "control": _registry.normalize_control(family_controls[c.header]),
        })
    return {
        "table": spec.table, "label": spec.label or humanize(spec.table),
        "key": list(spec.key), "model_scoped": spec.model_scoped,
        "schema_version": TABLE_SCHEMA_VERSION,
        "model_context": {
            "required": bool(spec.model_scoped or spec.has_model_key_column or spec.role),
            "source": "row_model_key" if spec.has_model_key_column else (
                "physical_source_registration" if spec.role else "none"
            ),
            "value": model_key,
        },
        "editable": spec.editable,
        "sheet_for_model": staging.target_sheet_for(conn, spec, model_key or "")
        if (model_key or spec.sheet) else None,
        "columns": cols, "id_prefixes": list(spec.id_prefixes),
    }


@app.get("/api/records/{table}/schema", response_model=TableSchemaOut)
def record_schema(
    table: str, model: str = "", conn=Depends(projection_connection)
):
    spec = SPEC_BY_TABLE.get(table)
    if spec is None:
        raise HTTPException(404, f"unknown table {table!r}")
    return _schema_dict(conn, spec, model or None)


REFERENCE_OPTIONS_VERSION = "workbook-manager-reference-options-1"


def _label_sql(columns: tuple[str, ...]) -> str:
    parts = [
        f"COALESCE(NULLIF(TRIM(CAST(\"{column}\" AS TEXT)), ''), '')"
        for column in columns
    ]
    return "TRIM(" + " || ' ' || ".join(parts) + ")"


# Targets whose rows can be partitioned by model. Narrowing applies whenever the
# caller supplies a model, independent of the RefSpec's declared scope: a
# `global` write contract still must not offer another model's rows in a picker.
# Each entry was measured against the canonical projection and still offers
# every value the real data stores, so narrowing never hides a row's current
# value from the editor.
#
# `form_sections` is deliberately absent. Its projected `model_context` is empty
# for all 48 rows (the read-only section spec carries no `source_role`, so the
# importer records no context), so the json_each filter matches zero sections
# for every model. Narrowing section pickers would empty them. That is a
# projection/contract gap, not a query fix.
#
# Narrowing a `global` ref also requires the SOURCE row to have a model
# identity. `color_overrides` has neither `model_id` nor `model_key`, so its
# rows are not owned by a model; restricting its interior choice to one model
# would block legitimate shared authoring even though the target is
# partitionable.
def _model_partition_sql(table: str, target_spec) -> str | None:
    if target_spec is not None and target_spec.model_scoped:
        return '"model_id"=?'
    if target_spec is not None and target_spec.has_model_key_column:
        return '"model_key"=?'
    if table == "interiors":
        return ('"src_sheet" IN (SELECT "sheet_name" FROM "sheet_registry" '
                'WHERE "model_key"=? AND '
                "\"source_role\"='interior_source_sheet')")
    if table == "variants":
        return ('"variant_id" IN (SELECT "variant_id" FROM "model_variants" '
                'WHERE "model_key"=?)')
    return None


def _reference_target_select(target: str, scope: str, model: str,
                             source_model_owned: bool
                             ) -> tuple[str, list[str]]:
    presentation = _reference_presentation(target)
    table = str(presentation.get("table") or target)
    value = str(presentation["value"])
    labels = tuple(str(item) for item in presentation["labels"])
    active_column = str(presentation.get("active") or "")
    where = [f"TRIM(COALESCE(CAST(\"{value}\" AS TEXT), '')) <> ''"]
    params: list[str] = []
    target_spec = SPEC_BY_TABLE.get(table)

    narrowing = _model_partition_sql(table, target_spec)
    if scope in ("model", "model_union"):
        if not model:
            raise HTTPException(422, detail={
                "status": "reference_model_required",
                "message": "this reference field requires a selected model",
            })
        if table == "form_sections":
            # Only reachable for a declared model-scoped ref into sections;
            # left exactly as before rather than widened to `global` refs.
            narrowing = (
                "EXISTS (SELECT 1 FROM json_each(COALESCE(\"model_context\", '[]')) "
                "WHERE json_each.value=?)"
            )
    elif not source_model_owned:
        # Global ref on a row that is not owned by a model: the supplied model
        # is context for the browsing session, not a constraint on the value.
        narrowing = None
    if model and narrowing:
        where.append(narrowing)
        params.append(model)

    label = _label_sql(labels)
    active = (
        f"CASE WHEN COALESCE(CAST(\"{active_column}\" AS TEXT), 'True')="
        "'False' THEN 0 ELSE 1 END"
        if active_column else "1"
    )
    sql = (
        f'SELECT CAST("{value}" AS TEXT) AS value, '
        f"COALESCE(NULLIF({label}, ''), CAST(\"{value}\" AS TEXT)) AS label, "
        f"{active} AS active FROM \"{table}\" WHERE " + " AND ".join(where)
    )
    return sql, params


def _reference_options(conn, spec, field: str, model: str, query: str,
                       discriminator: str, limit: int, offset: int) -> dict:
    contract = _reference_contract(spec, field, discriminator)
    targets = contract["targets"]
    scope = contract["scope"]
    if not targets:
        return {
            "schema_version": REFERENCE_OPTIONS_VERSION,
            "field": field,
            "scope": scope,
            "query": query,
            "total": 0,
            "offset": offset,
            "limit": limit,
            "options": [],
        }

    selects, base_params = [], []
    for target in targets:
        sql, params = _reference_target_select(
            target, scope, model,
            bool(spec.model_scoped or spec.has_model_key_column),
        )
        selects.append(sql)
        base_params.extend(params)
    raw = " UNION ALL ".join(selects)
    cte = (
        "WITH raw_candidates AS (" + raw + "), candidates AS ("
        "SELECT value, MIN(label) AS label, MAX(active) AS active "
        "FROM raw_candidates GROUP BY value) "
    )
    normalized_query = query.strip()
    filter_sql = ""
    filter_params: list[str] = []
    if normalized_query:
        filter_sql = "WHERE value LIKE ? COLLATE NOCASE OR label LIKE ? COLLATE NOCASE"
        like = f"%{normalized_query}%"
        filter_params = [like, like]
    count = conn.execute(
        cte + "SELECT COUNT(*) AS total FROM candidates " + filter_sql,
        [*base_params, *filter_params],
    ).fetchone()["total"]
    rows = conn.execute(
        cte + "SELECT value, label, active FROM candidates " + filter_sql
        + " ORDER BY label COLLATE NOCASE, value COLLATE NOCASE LIMIT ? OFFSET ?",
        [*base_params, *filter_params, limit, offset],
    ).fetchall()
    return {
        "schema_version": REFERENCE_OPTIONS_VERSION,
        "field": field,
        "scope": scope,
        "query": normalized_query,
        "total": count,
        "offset": offset,
        "limit": limit,
        "options": [
            {
                "value": row["value"],
                "label": row["label"],
                "secondary": row["value"],
                "active": bool(row["active"]),
            }
            for row in rows
        ],
    }


@app.get("/api/records/{table}/reference-options")
def reference_options(
    table: str,
    field: str,
    model: str = "",
    query: str = Query("", max_length=200),
    discriminator: str = Query("", max_length=200),
    limit: int = Query(25, ge=1, le=100),
    offset: int = Query(0, ge=0),
    conn=Depends(projection_connection),
):
    spec = SPEC_BY_TABLE.get(table)
    if spec is None:
        raise HTTPException(404, f"unknown table {table!r}")
    _validate_control_integrity(spec)
    return _reference_options(
        conn, spec, field, model, query, discriminator, limit, offset
    )


@app.get("/api/records/{table}")
def records(table: str, model: str = "", search: str = "",
            limit: int = Query(200, le=2000), offset: int = 0,
            conn=Depends(projection_connection)):
    spec = SPEC_BY_TABLE.get(table)
    if spec is None:
        raise HTTPException(404, f"unknown table {table!r}")
    where, params = [], []
    if spec.model_scoped and model:
        where.append("model_id=?")
        params.append(model)
    elif spec.has_model_key_column and model:
        where.append("model_key=?")
        params.append(model)
    if search:
        like = f"%{search}%"
        ors = [f'"{c.sql_name()}" LIKE ?' for c in spec.columns]
        where.append("(" + " OR ".join(ors) + ")")
        params += [like] * len(spec.columns)
    wsql = ("WHERE " + " AND ".join(where)) if where else ""
    total = conn.execute(
        f"SELECT COUNT(*) c FROM {table} {wsql}", params).fetchone()["c"]
    rows = conn.execute(
        f"SELECT * FROM {table} {wsql} ORDER BY id LIMIT ? OFFSET ?",
        [*params, limit, offset]).fetchall()
    out = []
    for r in rows:
        d = dict(r)
        raw_context = d.get("model_context")
        if isinstance(raw_context, str):
            d["model_context"] = json.loads(raw_context) if raw_context else []
        d["_display_id"] = display_id(str(d.get(spec.key[0], "")),
                                      spec.id_prefixes)
        out.append(d)
    return {"table": table, "total": total, "offset": offset,
            "records": out}


@app.post("/api/records/{table}/dependencies")
def dependencies_post(
    table: str, body: dict, conn=Depends(projection_connection)
):
    spec = SPEC_BY_TABLE.get(table)
    if spec is None:
        raise HTTPException(404, f"unknown table {table!r}")
    deps = find_dependents(conn, spec, str(body.get("model_id", "")),
                           body.get("key", {}))
    return {"table": table, "dependents": deps, "count": len(deps)}


# ── staged changes ───────────────────────────────────────────────────

@app.get("/api/drafts")
def durable_drafts(
    limit: int = Query(50, ge=1, le=200),
    state_conn=Depends(state_connection),
):
    return {"drafts": drafts.list_drafts(state_conn, limit=limit)}


@app.get("/api/drafts/{draft_id}")
def draft_lifecycle(draft_id: str, state_conn=Depends(state_connection)):
    try:
        return drafts.lifecycle_view(state_conn, draft_id)
    except drafts.DraftError as exc:
        raise _draft_error(exc)

@app.post("/api/drafts/{draft_id}/operations")
def save_draft_operation(
    draft_id: str,
    payload: DraftOperationRequest,
    _lock=Depends(durable_write_lock),
    conn=Depends(projection_connection),
    state_conn=Depends(state_connection),
):
    workbook = _workbook_state(conn)
    run = conn.execute(
        "SELECT * FROM import_runs ORDER BY id DESC LIMIT 1"
    ).fetchone()
    projection = _projection_state(conn, run, workbook)
    try:
        return drafts.save_operation(
            conn,
            state_conn,
            projection_state=projection["state"],
            base_workbook_sha256=workbook["imported_sha256"],
            base_workbook_mtime_ns=workbook["imported_mtime_ns"],
            draft_id=draft_id,
            table=payload.table,
            model_id=payload.model_id,
            op=payload.op,
            key=payload.key,
            record=payload.record,
            session_id=payload.session_id,
            actor=payload.actor,
        )
    except drafts.DraftError as exc:
        raise _draft_error(exc)


@app.get("/api/drafts/{draft_id}/operations")
def draft_operations(draft_id: str, state_conn=Depends(state_connection)):
    return {"draft_id": draft_id, "operations": drafts.list_operations(
        state_conn, draft_id
    )}


def _asset_draft_context(conn):
    workbook = _workbook_state(conn)
    run = conn.execute(
        "SELECT * FROM import_runs ORDER BY id DESC LIMIT 1"
    ).fetchone()
    return workbook, _projection_state(conn, run, workbook)


@app.post("/api/drafts/{draft_id}/asset-resolutions")
def save_asset_resolution(
    draft_id: str,
    payload: AssetResolutionRequest,
    _lock=Depends(durable_write_lock),
    conn=Depends(projection_connection),
    state_conn=Depends(state_connection),
):
    workbook, projection = _asset_draft_context(conn)
    snapshot = asset_workspace.get_cached_asset_manager_snapshot(
        config.DEFAULT_WORKBOOK, payload.fingerprints
    )
    if snapshot is None:
        raise HTTPException(409, detail={
            "status": "asset_reconciliation_stale",
            "message": "The reviewed asset snapshot is no longer cached/current; refresh Asset Manager.",
        })
    try:
        return asset_resolutions.save_resolution(
            conn,
            state_conn,
            snapshot=snapshot,
            projection_state=projection["state"],
            base_workbook_sha256=workbook["imported_sha256"],
            base_workbook_mtime_ns=workbook["imported_mtime_ns"],
            draft_id=draft_id,
            item_id=payload.item_id,
            resolution_kind=payload.resolution_kind,
            fingerprints=payload.fingerprints,
            selected_url=payload.selected_url,
            target_item_id=payload.target_item_id,
            values=payload.values,
            session_id=payload.session_id,
            actor=payload.actor,
        )
    except drafts.DraftError as exc:
        raise _draft_error(exc)


@app.post("/api/drafts/{draft_id}/asset-resolutions/safe")
def save_all_safe_asset_resolutions(
    draft_id: str,
    payload: AssetSafeBulkRequest,
    _lock=Depends(durable_write_lock),
    conn=Depends(projection_connection),
    state_conn=Depends(state_connection),
):
    workbook, projection = _asset_draft_context(conn)
    snapshot = asset_workspace.get_cached_asset_manager_snapshot(
        config.DEFAULT_WORKBOOK, payload.fingerprints
    )
    if snapshot is None:
        raise HTTPException(409, detail={
            "status": "asset_reconciliation_stale",
            "message": "The reviewed asset snapshot is no longer cached/current; refresh Asset Manager.",
        })
    try:
        results = asset_resolutions.save_all_safe(
            conn,
            state_conn,
            snapshot=snapshot,
            fingerprints=payload.fingerprints,
            projection_state=projection["state"],
            base_workbook_sha256=workbook["imported_sha256"],
            base_workbook_mtime_ns=workbook["imported_mtime_ns"],
            draft_id=draft_id,
            session_id=payload.session_id,
            actor=payload.actor,
        )
        return {"draft_id": draft_id, "accepted": len(results), "operations": results}
    except drafts.DraftError as exc:
        raise _draft_error(exc)


@app.post("/api/drafts/{draft_id}/commit")
def commit_draft(
    draft_id: str,
    _lock=Depends(durable_write_lock),
    conn=Depends(projection_connection),
    state_conn=Depends(state_connection),
):
    try:
        if drafts.list_asset_resolutions(state_conn, draft_id):
            snapshot = asset_workspace.get_asset_manager_snapshot(
                config.DEFAULT_WORKBOOK, refresh=True
            )
            drafts.assert_asset_resolutions_current(
                state_conn, draft_id=draft_id, snapshot=snapshot
            )
        return drafts.emit_changeset(state_conn, draft_id=draft_id)
    except drafts.DraftError as exc:
        raise _draft_error(exc)
    except asset_workspace.asset_map_sync.WordPressMediaFetchError as exc:
        raise HTTPException(502, detail={
            "status": "asset_media_inventory_unavailable",
            "message": str(exc),
        }) from exc
    except (OSError, ValueError) as exc:
        raise HTTPException(422, detail={
            "status": "asset_reconciliation_failed",
            "message": str(exc),
        }) from exc


@app.post("/api/drafts/{draft_id}/preview")
def preview_draft_changeset(
    draft_id: str,
    _lock=Depends(durable_write_lock),
    conn=Depends(projection_connection),
    state_conn=Depends(state_connection),
):
    workbook = _workbook_state(conn)
    run = conn.execute(
        "SELECT * FROM import_runs ORDER BY id DESC LIMIT 1"
    ).fetchone()
    projection = _projection_state(conn, run, workbook)
    try:
        return drafts.preview_draft(
            state_conn,
            draft_id=draft_id,
            projection_state=projection["state"],
            workbook_path=config.DEFAULT_WORKBOOK,
        )
    except drafts.DraftError as exc:
        raise _draft_error(exc)


@app.post("/api/drafts/{draft_id}/approve")
def approve_draft_changeset(
    draft_id: str,
    payload: ApprovalRequest,
    _lock=Depends(durable_write_lock),
    conn=Depends(projection_connection),
    state_conn=Depends(state_connection),
):
    workbook = _workbook_state(conn)
    run = conn.execute(
        "SELECT * FROM import_runs ORDER BY id DESC LIMIT 1"
    ).fetchone()
    projection = _projection_state(conn, run, workbook)
    try:
        return drafts.approve_draft(
            state_conn,
            draft_id=draft_id,
            projection_state=projection["state"],
            actor=payload.actor,
            warning_ids=payload.warning_ids,
        )
    except drafts.DraftError as exc:
        raise _draft_error(exc)


@app.post("/api/drafts/{draft_id}/apply-rebuild")
def apply_and_rebuild_draft(
    draft_id: str,
    payload: ApplyRebuildRequest,
    _lock=Depends(durable_write_lock),
    conn=Depends(projection_connection),
    state_conn=Depends(state_connection),
):
    """Reach the writer only through one exact approved Apply and Rebuild action."""

    if payload.confirm != "APPLY AND REBUILD":
        raise HTTPException(422, detail={
            "status": "apply_rebuild_confirmation_required",
            "message": "type APPLY AND REBUILD to run the exact approved pipeline",
        })
    draft_row = state_conn.execute(
        "SELECT status FROM workflow_drafts WHERE id=?", (draft_id,)
    ).fetchone()
    if draft_row is not None and draft_row["status"] == "applied":
        try:
            return drafts.apply_draft(
                state_conn,
                draft_id=draft_id,
                workbook_path=config.DEFAULT_WORKBOOK,
                log_path=config.EDIT_LOG_PATH,
            )
        except drafts.DraftError as exc:
            raise _draft_error(exc)
    workbook = _workbook_state(conn)
    run = conn.execute(
        "SELECT * FROM import_runs ORDER BY id DESC LIMIT 1"
    ).fetchone()
    projection = _projection_state(conn, run, workbook)
    if projection["state"] != "current":
        raise HTTPException(409, detail={
            "status": "projection_not_current",
            "message": "Apply and Rebuild requires the exact current imported projection",
            "projection": projection,
        })
    operations = drafts.list_operations(state_conn, draft_id)
    candidate_models = sorted({
        str(model)
        for operation in operations
        for model in (
            [operation.get("model_id")] + (operation.get("model_context") or [])
        )
        if str(model or "") not in {"", "*"}
    })

    def prepare():
        return apply_rebuild.prepare_rollback_set(
            draft_id=draft_id,
            workbook_path=config.DEFAULT_WORKBOOK,
            repository_root=config.APPLY_OUTPUT_ROOT,
            rollback_root=config.APPLY_ROLLBACK_DIR,
            candidate_models=candidate_models,
            requested_by=payload.actor,
        )

    def complete(receipt, rollback):
        return apply_rebuild.complete_apply_rebuild(
            receipt,
            rollback=rollback,
            operations=operations,
            workbook_path=config.DEFAULT_WORKBOOK,
            repository_root=config.APPLY_OUTPUT_ROOT,
        )

    try:
        return drafts.apply_draft(
            state_conn,
            draft_id=draft_id,
            workbook_path=config.DEFAULT_WORKBOOK,
            log_path=config.EDIT_LOG_PATH,
            prepare_apply=prepare,
            complete_apply=complete,
        )
    except drafts.DraftError as exc:
        raise _draft_error(exc)


@app.post("/api/drafts/{draft_id}/cancel")
def cancel_draft(
    draft_id: str,
    _lock=Depends(durable_write_lock),
    state_conn=Depends(state_connection),
):
    try:
        return drafts.cancel_draft(state_conn, draft_id=draft_id)
    except drafts.DraftError as exc:
        raise _draft_error(exc)


@app.post("/api/drafts/{draft_id}/resolve-unknown")
def resolve_unknown_draft(
    draft_id: str,
    payload: ManualResolutionRequest,
    _lock=Depends(durable_write_lock),
    state_conn=Depends(state_connection),
):
    try:
        return drafts.resolve_unknown_draft(
            state_conn,
            draft_id=draft_id,
            resolution=payload.resolution,
            workbook_path=config.DEFAULT_WORKBOOK,
            actor=payload.actor,
            evidence=payload.evidence,
        )
    except drafts.DraftError as exc:
        raise _draft_error(exc)


@app.post("/api/changes", response_model=ChangeOut)
def stage(
    payload: StageChangeRequest,
    _lock=Depends(durable_write_lock),
    conn=Depends(projection_connection),
    state_conn=Depends(state_connection),
):
    try:
        return staging.stage_change(
            conn, table=payload.table, model_id=payload.model_id,
            op=payload.op, key=payload.key, record=payload.record,
            session_id=payload.session_id,
            state_conn=state_conn)
    except StagingError as exc:
        raise _staging_error(exc)


@app.get("/api/changes")
def changes(status: str = "staged", state_conn=Depends(state_connection)):
    return {"changes": staging.list_changes(state_conn, status)}


@app.delete("/api/changes/{change_id}", response_model=ChangeOut)
def discard(
    change_id: int,
    _lock=Depends(durable_write_lock),
    state_conn=Depends(state_connection),
):
    try:
        return staging.discard_change(state_conn, change_id)
    except StagingError as exc:
        raise _staging_error(exc)


@app.post("/api/changes/validate")
def validate_changes(
    _lock=Depends(durable_write_lock),
    conn=Depends(projection_connection),
    state_conn=Depends(state_connection),
):
    return staging.revalidate_staged(conn, state_conn)


@app.post("/api/changes/commit")
def commit(
    payload: CommitRequest,
    _lock=Depends(durable_write_lock),
    conn=Depends(projection_connection),
    state_conn=Depends(state_connection),
):
    return staging.commit_staged(conn, actor=payload.actor, state_conn=state_conn)


# ── history / sync / export / backup ─────────────────────────────────

@app.get("/api/history")
def history(model: str = "", entity_type: str = "", sync_status: str = "",
            limit: int = Query(200, le=2000), offset: int = 0,
            conn=Depends(state_connection)):
    where, params = [], []
    if model:
        where.append("model_id=?")
        params.append(model)
    if entity_type:
        where.append("entity_type=?")
        params.append(entity_type)
    if sync_status:
        where.append("sync_status=?")
        params.append(sync_status)
    wsql = ("WHERE " + " AND ".join(where)) if where else ""
    rows = conn.execute(
        f"SELECT * FROM change_history {wsql} ORDER BY id DESC "
        "LIMIT ? OFFSET ?", [*params, limit, offset]).fetchall()
    total = conn.execute(
        f"SELECT COUNT(*) c FROM change_history {wsql}", params
    ).fetchone()["c"]
    out = []
    for r in rows:
        d = dict(r)
        d["old"] = json.loads(d.pop("old_json")) if d.get("old_json") else None
        d["new"] = json.loads(d.pop("new_json")) if d.get("new_json") else None
        out.append(d)
    return {"total": total, "history": out}


@app.post("/api/sync")
def sync_endpoint(
    payload: SyncRequest,
    _lock=Depends(durable_write_lock),
    projection=Depends(projection_connection),
    conn=Depends(state_connection),
):
    if payload.write:
        raise HTTPException(409, detail={
            "status": PROVISIONAL_MODE,
            "message": "legacy live sync writes are permanently disabled; use "
                       "the exact approved Apply and Rebuild action",
        })
    return syncmod.sync_workbook(
        conn, config.DEFAULT_WORKBOOK, write=payload.write,
        confirmed_warnings=tuple(payload.confirmed_warnings),
        expected_mtime_ns=payload.expected_mtime_ns,
        projection_conn=projection)


@app.post("/api/export")
def export(conn=Depends(projection_connection)):
    workbook = _workbook_state(conn)
    run = conn.execute(
        "SELECT * FROM import_runs ORDER BY id DESC LIMIT 1").fetchone()
    projection = _projection_state(conn, run, workbook)
    if projection["state"] != "current":
        raise HTTPException(409, detail={
            "status": "projection_not_current",
            "message": "comparison export requires a current verified projection",
            "projection": projection,
        })
    return syncmod.export_comparison_workbook(conn, config.DEFAULT_WORKBOOK)


@app.post("/api/backup")
def backup(
    _lock=Depends(durable_write_lock),
    conn=Depends(state_connection),
):
    return syncmod.backup_database(conn, config.DEFAULT_DB)


# ── frontend static hosting ──────────────────────────────────────────

if config.FRONTEND_DIST.exists():
    app.mount("/assets", StaticFiles(
        directory=config.FRONTEND_DIST / "assets"), name="assets")

    @app.get("/")
    def index():
        return FileResponse(config.FRONTEND_DIST / "index.html")
