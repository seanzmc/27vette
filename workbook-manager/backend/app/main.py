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
def structure(model_key: str, conn=Depends(projection_connection)):

    def rows(table, order):
        spec = SPEC_BY_TABLE[table]
        return [dict(r) for r in conn.execute(
            f"SELECT * FROM {table} WHERE model_key=? ORDER BY {order}",
            (model_key,))]

    steps = rows("form_steps", "CAST(runtime_order AS INTEGER)")
    presentation = rows("section_presentation",
                        "CAST(section_display_order AS INTEGER)")
    sections = {r["section_id"]: dict(r) for r in conn.execute(
        "SELECT * FROM form_sections")}
    for p in presentation:
        master = sections.get(p["section_id"], {})
        p["step_key"] = p.get("step_key") or master.get("step_key")
        p["section_name"] = master.get("section_name", "")
        p["display_name"] = p.get("display_label") or master.get(
            "section_name") or display_id(p["section_id"], ("sec_",))
    for s in steps:
        s["display_name"] = s.get("step_label") or humanize(s["step_key"])
        s["sections"] = [p for p in presentation
                         if p.get("step_key") == s["step_key"]]
    return {
        "model_key": model_key,
        "steps": steps,
        "sections_master": list(sections.values()),
        "section_presentation": presentation,
        "context_sections": rows("context_sections",
                                 "CAST(section_display_order AS INTEGER)"),
        "order_summary_sections": rows("order_summary_sections",
                                       "CAST(display_order AS INTEGER)"),
        "step_order_summary_map": rows("step_order_summary_map", "id"),
        "variants": [dict(r) for r in conn.execute(
            "SELECT mv.*, vm.trim_level, vm.body_style, vm.display_name, "
            "vm.base_price FROM model_variants mv LEFT JOIN variants vm ON "
            "vm.variant_id = mv.variant_id WHERE mv.model_key=? "
            "ORDER BY CAST(mv.display_order AS INTEGER)", (model_key,))],
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

def _schema_dict(conn, spec, model_key: str | None) -> dict:
    cols = []
    ref_by_col = {r.column: r for r in spec.refs}
    conditional = dict(spec.conditional_ref)
    conditional_column = conditional.get("column", "")
    conditional_targets = dict(spec.conditional_refs)
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
        })
    return {
        "table": spec.table, "label": spec.label or humanize(spec.table),
        "key": list(spec.key), "model_scoped": spec.model_scoped,
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
