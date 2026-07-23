"""FastAPI application for the 27vette workbook manager.

Run from the repo root:

    .venv/bin/python -m uvicorn app.main:app \
        --app-dir workbook-manager/backend --port 8050

or use ``workbook-manager/run.sh``.
"""

from __future__ import annotations

import json
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from . import config, db as dbmod, importer, staging, sync as syncmod
from .naming import display_id, humanize, sheet_display_name
from .schemas import (
    ChangeOut,
    CommitRequest,
    StageChangeRequest,
    SyncRequest,
    TableSchemaOut,
)
from .specs import (
    MODEL_COLLECTIONS,
    SHARED_TABLES,
    SPEC_BY_TABLE,
    STRUCTURE_TABLES,
    TABLE_SPECS,
)
from .staging import StagingError
from .validation import find_dependents

app = FastAPI(title="27vette Workbook Manager", version="0.1.0")

_conn = None

PROVISIONAL_MODE = "read_only_provisional"
IMPORT_TERMINAL_ALLOWLIST = (
    "applied",
    "cancelled",
    "manually_resolved_restored",
    "manually_resolved_applied",
    "abandoned_unknown",
)


def get_conn():
    global _conn
    if _conn is None:
        config.ensure_dirs()
        _conn = dbmod.connect(config.DEFAULT_DB)
        dbmod.init_schema(_conn)
    return _conn


def _staging_error(exc: StagingError):
    return HTTPException(status_code=422, detail={"errors": exc.errors})


def _workbook_state(conn) -> dict:
    path = config.DEFAULT_WORKBOOK
    imported_mtime = dbmod.get_meta(conn, "workbook_mtime_ns")
    current_mtime = str(path.stat().st_mtime_ns) if path.exists() else ""
    if not path.exists():
        state = "missing"
    elif not imported_mtime:
        state = "unbound"
    elif imported_mtime != current_mtime:
        state = "stale"
    else:
        state = "current"
    return {
        "state": state,
        "workbook_path": str(path),
        "exists": path.exists(),
        "imported_mtime_ns": imported_mtime,
        "current_mtime_ns": current_mtime,
        "stale": bool(imported_mtime) and imported_mtime != current_mtime,
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
    return {
        "staged": staged,
        "committed_unsynchronized": committed_unsynchronized,
        "failed": failed,
        "unresolved_total": staged + committed_unsynchronized + failed,
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
    elif workbook["state"] == "stale":
        state = "stale"
    elif not run or run["status"] != "imported" or blocking_findings:
        state = "unverified"
    else:
        state = "current"
    return {
        "state": state,
        "active": active,
        "blocking_findings": blocking_findings,
        "reimport_allowed": not active,
    }


# ── status / import ──────────────────────────────────────────────────

@app.get("/api/status")
def status():
    conn = get_conn()
    counts = {s.table: conn.execute(
        f"SELECT COUNT(*) c FROM {s.table}").fetchone()["c"]
        for s in TABLE_SPECS}
    staged = conn.execute(
        "SELECT COUNT(*) c FROM pending_changes WHERE status='staged'"
    ).fetchone()["c"]
    unsynced = conn.execute(
        "SELECT COUNT(*) c FROM change_history WHERE sync_status='pending'"
    ).fetchone()["c"]
    run = conn.execute(
        "SELECT * FROM import_runs ORDER BY id DESC LIMIT 1").fetchone()
    workbook = _workbook_state(conn)
    projection = _projection_state(conn, run, workbook)
    blockers = _import_blockers(conn)
    return {
        "mode": PROVISIONAL_MODE,
        "projection": projection,
        "draft": {
            "state": "blocked" if blockers["unresolved_total"] else "clear",
            **blockers,
            "terminal_import_allowlist": list(IMPORT_TERMINAL_ALLOWLIST),
        },
        "workbook": workbook,
        "generated_artifacts": {
            "state": "unverified",
            "reason": "generation is outside the provisional manager workflow",
        },
        "publication": {
            "state": "unverified",
            "reason": "runtime publication is outside the manager workflow",
        },
        "tables": counts,
        "staged_changes": staged,
        "unsynced_committed_changes": unsynced,
        "last_import": dict(run) if run else None,
    }


@app.post("/api/import")
def run_import():
    conn = get_conn()
    if not config.DEFAULT_WORKBOOK.exists():
        raise HTTPException(404, f"workbook not found: "
                                 f"{config.DEFAULT_WORKBOOK}")
    active_projection = _projection_active(conn)
    blockers = _import_blockers(conn)
    if active_projection or blockers["unresolved_total"]:
        reasons = []
        if active_projection:
            reasons.append("an active projection already exists; candidate "
                           "promotion is not implemented until Pass 4")
        if blockers["unresolved_total"]:
            reasons.append("unresolved legacy draft/synchronization work exists")
        raise HTTPException(409, detail={
            "status": PROVISIONAL_MODE,
            "message": "re-import refused: " + "; ".join(reasons),
            "active_projection": active_projection,
            "import_blockers": blockers,
        })
    report = importer.import_workbook(conn, config.DEFAULT_WORKBOOK)
    workbook = _workbook_state(conn)
    projection = _projection_state(conn, report["run"], workbook)
    report["projection"] = projection
    report["verified"] = projection["state"] == "current"
    report["mode"] = PROVISIONAL_MODE
    return report


@app.get("/api/import/latest")
def latest_import():
    conn = get_conn()
    report = importer.latest_report(conn)
    if report is None:
        raise HTTPException(404, "no import has run yet")
    return report


# ── models / structure ───────────────────────────────────────────────

@app.get("/api/models")
def models():
    conn = get_conn()
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
def structure(model_key: str):
    conn = get_conn()

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
def collections(model_key: str):
    conn = get_conn()
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


@app.get("/api/tables")
def tables():
    conn = get_conn()
    return {"structure_tables": [
        _schema_dict(conn, SPEC_BY_TABLE[t], None) for t in STRUCTURE_TABLES]}


# ── records ──────────────────────────────────────────────────────────

def _schema_dict(conn, spec, model_key: str | None) -> dict:
    cols = []
    ref_by_col = {r.column: r for r in spec.refs}
    for c in spec.columns:
        ref = ref_by_col.get(c.sql_name())
        cols.append({
            "name": c.sql_name(), "header": c.header,
            "label": humanize(c.sql_name()), "ctype": c.ctype,
            "enum": list(c.enum), "is_key": c.sql_name() in spec.key,
            "ref": {"table": ref.target_table, "column": ref.target_column,
                    "scope": ref.scope,
                    "union": list(ref.union_tables)} if ref else None,
        })
    return {
        "table": spec.table, "label": spec.label or humanize(spec.table),
        "key": list(spec.key), "model_scoped": spec.model_scoped,
        "editable": spec.editable,
        "sheet_for_model": staging.target_sheet_for(conn, spec, model_key or "")
        if (model_key or spec.sheet) else None,
        "columns": cols, "id_prefixes": list(spec.id_prefixes),
    }


@app.get("/api/records/{table}/schema", response_model=TableSchemaOut)
def record_schema(table: str, model: str = ""):
    conn = get_conn()
    spec = SPEC_BY_TABLE.get(table)
    if spec is None:
        raise HTTPException(404, f"unknown table {table!r}")
    return _schema_dict(conn, spec, model or None)


@app.get("/api/records/{table}")
def records(table: str, model: str = "", search: str = "",
            limit: int = Query(200, le=2000), offset: int = 0):
    conn = get_conn()
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
        d["_display_id"] = display_id(str(d.get(spec.key[0], "")),
                                      spec.id_prefixes)
        out.append(d)
    return {"table": table, "total": total, "offset": offset,
            "records": out}


@app.post("/api/records/{table}/dependencies")
def dependencies_post(table: str, body: dict):
    conn = get_conn()
    spec = SPEC_BY_TABLE.get(table)
    if spec is None:
        raise HTTPException(404, f"unknown table {table!r}")
    deps = find_dependents(conn, spec, str(body.get("model_id", "")),
                           body.get("key", {}))
    return {"table": table, "dependents": deps, "count": len(deps)}


# ── staged changes ───────────────────────────────────────────────────

@app.post("/api/changes", response_model=ChangeOut)
def stage(payload: StageChangeRequest):
    conn = get_conn()
    try:
        return staging.stage_change(
            conn, table=payload.table, model_id=payload.model_id,
            op=payload.op, key=payload.key, record=payload.record,
            session_id=payload.session_id,
            confirm_dependencies=payload.confirm_dependencies)
    except StagingError as exc:
        raise _staging_error(exc)


@app.get("/api/changes")
def changes(status: str = "staged"):
    conn = get_conn()
    return {"changes": staging.list_changes(conn, status)}


@app.delete("/api/changes/{change_id}", response_model=ChangeOut)
def discard(change_id: int):
    conn = get_conn()
    try:
        return staging.discard_change(conn, change_id)
    except StagingError as exc:
        raise _staging_error(exc)


@app.post("/api/changes/validate")
def validate_changes():
    conn = get_conn()
    return staging.revalidate_staged(conn)


@app.post("/api/changes/commit")
def commit(payload: CommitRequest):
    conn = get_conn()
    return staging.commit_staged(conn, actor=payload.actor)


# ── history / sync / export / backup ─────────────────────────────────

@app.get("/api/history")
def history(model: str = "", entity_type: str = "", sync_status: str = "",
            limit: int = Query(200, le=2000), offset: int = 0):
    conn = get_conn()
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
def sync_endpoint(payload: SyncRequest):
    conn = get_conn()
    if payload.write:
        raise HTTPException(409, detail={
            "status": PROVISIONAL_MODE,
            "message": "live workbook writes are disabled during the "
                       "read-only provisional workflow; only the exact bound "
                       "ChangeSet service may be enabled in Pass 7",
        })
    return syncmod.sync_workbook(
        conn, config.DEFAULT_WORKBOOK, write=payload.write,
        confirmed_warnings=tuple(payload.confirmed_warnings),
        expected_mtime_ns=payload.expected_mtime_ns)


@app.post("/api/export")
def export():
    conn = get_conn()
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
def backup():
    conn = get_conn()
    return syncmod.backup_database(conn, config.DEFAULT_DB)


# ── frontend static hosting ──────────────────────────────────────────

if config.FRONTEND_DIST.exists():
    app.mount("/assets", StaticFiles(
        directory=config.FRONTEND_DIST / "assets"), name="assets")

    @app.get("/")
    def index():
        return FileResponse(config.FRONTEND_DIST / "index.html")
