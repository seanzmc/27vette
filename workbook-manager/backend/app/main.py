"""FastAPI routes over the canonical workbook-congruent database."""

from __future__ import annotations

import json
import sqlite3

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from . import config, db as dbmod, importer, staging, sync as syncmod
from .catalog import (
    LIVE_MODELS,
    MODEL_TABLE_ROLES,
    edit_spec,
    resolve_model_table,
)
from .naming import display_id, humanize
from .schemas import ChangeOut, CommitRequest, StageChangeRequest, SyncRequest
from .staging import StagingError
from .validation import find_dependents


app = FastAPI(title="27vette Workbook Manager", version="0.2.0")
_conn = None


def get_conn():
    global _conn
    if _conn is None:
        config.ensure_dirs()
        existed = config.DEFAULT_DB.exists()
        _conn = dbmod.connect(config.DEFAULT_DB)
        if not existed:
            dbmod.create_canonical_schema(_conn)
    return _conn


def _staging_error(exc: StagingError):
    return HTTPException(status_code=422, detail={"errors": exc.errors})


@app.get("/api/status")
def status():
    conn = get_conn()
    counts = {}
    for model_key in LIVE_MODELS:
        for role in MODEL_TABLE_ROLES:
            try:
                table = resolve_model_table(conn, model_key, role)
            except (KeyError, sqlite3.OperationalError):
                continue
            counts[table] = conn.execute(
                f'SELECT COUNT(*) FROM "{table}"'
            ).fetchone()[0]
    staged = conn.execute(
        "SELECT COUNT(*) FROM pending_changes WHERE status='staged'"
    ).fetchone()[0]
    unsynced = len(syncmod.pending_history(conn))
    run = conn.execute(
        "SELECT * FROM import_runs ORDER BY id DESC LIMIT 1"
    ).fetchone()
    return {
        "tables": counts,
        "staged_changes": staged,
        "unsynced_committed_changes": unsynced,
        "last_import": dict(run) if run else None,
    }


@app.post("/api/import")
def run_import():
    if not config.DEFAULT_WORKBOOK.exists():
        raise HTTPException(404, f"workbook not found: {config.DEFAULT_WORKBOOK}")
    global _conn
    if _conn is not None:
        _conn.close()
        _conn = None
    return importer.import_workbook(config.DEFAULT_DB, config.DEFAULT_WORKBOOK)


@app.get("/api/import/latest")
def latest_import():
    report = importer.latest_report(get_conn())
    if report is None:
        raise HTTPException(404, "no import has run yet")
    return report


@app.get("/api/models")
def models():
    rows = get_conn().execute(
        "SELECT m.*, p.promoted_to_runtime, p.display_order AS promotion_order "
        "FROM models m LEFT JOIN model_registry_promotion p USING(model_key) "
        "ORDER BY p.display_order, m.model_key"
    ).fetchall()
    return {"models": [dict(row) for row in rows]}


@app.get("/api/structure/{model_key}")
def structure(model_key: str):
    conn = get_conn()
    if model_key not in LIVE_MODELS:
        raise HTTPException(404, f"unknown model {model_key!r}")
    steps = [dict(row) for row in conn.execute(
        "SELECT * FROM runtime_steps WHERE model_key=? ORDER BY runtime_order",
        (model_key,),
    )]
    presentations = [dict(row) for row in conn.execute(
        "SELECT * FROM section_presentation WHERE model_key=? "
        "ORDER BY section_display_order", (model_key,),
    )]
    return {
        "model_key": model_key,
        "steps": steps,
        "section_presentation": presentations,
        "variants": [dict(row) for row in conn.execute(
            "SELECT mv.*, v.trim_level, v.body_style, v.display_name, v.base_price "
            "FROM model_variants mv JOIN variants v USING(variant_id) "
            "WHERE mv.model_key=? ORDER BY mv.display_order", (model_key,),
        )],
    }


@app.get("/api/models/{model_key}/collections")
def collections(model_key: str):
    conn = get_conn()
    result = []
    for role in MODEL_TABLE_ROLES:
        try:
            spec = edit_spec(conn, model_key, role)
        except KeyError:
            continue
        result.append({
            "table_role": role,
            "sql_table": spec.sql_table,
            "label": humanize(role),
            "count": conn.execute(
                f'SELECT COUNT(*) FROM "{spec.sql_table}"'
            ).fetchone()[0],
            "editable": True,
            "sheet": staging.target_sheet_for(conn, model_key, role),
        })
    return {"model_key": model_key, "collections": result}


def _schema_dict(conn, model_key: str, role: str) -> dict:
    spec = edit_spec(conn, model_key, role)
    return {
        "model_key": model_key,
        "table_role": role,
        "sql_table": spec.sql_table,
        "key": list(spec.key),
        "columns": [
            {
                "name": column,
                "label": humanize(column),
                "ctype": spec.types[column],
                "enum": list(spec.enums.get(column, ())),
                "is_key": column in spec.key,
                "nullable": column in spec.nullable,
            }
            for column in spec.columns
            if column != "model_key"
        ],
        "sheet": staging.target_sheet_for(conn, model_key, role),
    }


@app.get("/api/models/{model_key}/tables/{table_role}/schema")
def record_schema(model_key: str, table_role: str):
    try:
        return _schema_dict(get_conn(), model_key, table_role)
    except KeyError:
        raise HTTPException(404, "unknown model/table role") from None


@app.get("/api/models/{model_key}/tables/{table_role}")
def records(
    model_key: str,
    table_role: str,
    search: str = "",
    limit: int = Query(200, le=2000),
    offset: int = 0,
):
    conn = get_conn()
    try:
        spec = edit_spec(conn, model_key, table_role)
    except KeyError:
        raise HTTPException(404, "unknown model/table role") from None
    where = []
    values = []
    if search:
        where.append("(" + " OR ".join(
            f'CAST("{column}" AS TEXT) LIKE ?' for column in spec.columns
        ) + ")")
        values.extend([f"%{search}%"] * len(spec.columns))
    clause = "WHERE " + " AND ".join(where) if where else ""
    total = conn.execute(
        f'SELECT COUNT(*) FROM "{spec.sql_table}" {clause}', values
    ).fetchone()[0]
    order = ",".join(f'"{column}"' for column in spec.key)
    rows = conn.execute(
        f'SELECT * FROM "{spec.sql_table}" {clause} ORDER BY {order} '
        "LIMIT ? OFFSET ?", [*values, limit, offset],
    ).fetchall()
    return {
        "model_key": model_key, "table_role": table_role,
        "sql_table": spec.sql_table, "total": total,
        "records": [dict(row) for row in rows],
    }


@app.post("/api/models/{model_key}/tables/{table_role}/dependencies")
def dependencies_post(model_key: str, table_role: str, body: dict):
    try:
        dependents = find_dependents(
            get_conn(), model_key, table_role, body.get("key", {})
        )
    except KeyError:
        raise HTTPException(404, "unknown model/table role") from None
    return {"dependents": dependents, "count": len(dependents)}


@app.post("/api/changes", response_model=ChangeOut)
def stage(payload: StageChangeRequest):
    try:
        return staging.stage_change(
            get_conn(), model_key=payload.model_key,
            table_role=payload.table_role, op=payload.op, key=payload.key,
            record=payload.record, session_id=payload.session_id,
            confirm_dependencies=payload.confirm_dependencies,
        )
    except StagingError as exc:
        raise _staging_error(exc)


@app.get("/api/changes")
def changes(status: str = "staged"):
    return {"changes": staging.list_changes(get_conn(), status)}


@app.delete("/api/changes/{change_id}", response_model=ChangeOut)
def discard(change_id: int):
    try:
        return staging.discard_change(get_conn(), change_id)
    except StagingError as exc:
        raise _staging_error(exc)


@app.post("/api/changes/validate")
def validate_changes():
    return staging.revalidate_staged(get_conn())


@app.post("/api/changes/commit")
def commit(payload: CommitRequest):
    return staging.commit_staged(get_conn(), actor=payload.actor)


@app.get("/api/history")
def history(
    model_key: str = "", table_role: str = "",
    limit: int = Query(200, le=2000), offset: int = 0,
):
    where, values = [], []
    if model_key:
        where.append("model_key=?")
        values.append(model_key)
    if table_role:
        where.append("table_role=?")
        values.append(table_role)
    clause = "WHERE " + " AND ".join(where) if where else ""
    rows = get_conn().execute(
        f"SELECT * FROM change_history {clause} ORDER BY id DESC "
        "LIMIT ? OFFSET ?", [*values, limit, offset],
    ).fetchall()
    output = []
    for row in rows:
        item = dict(row)
        old_json = item.pop("old_json")
        new_json = item.pop("new_json")
        item["old"] = json.loads(old_json) if old_json else None
        item["new"] = json.loads(new_json) if new_json else None
        output.append(item)
    return {"history": output}


@app.post("/api/sync")
def sync_endpoint(payload: SyncRequest):
    if payload.write and payload.confirm != "SYNC":
        raise HTTPException(400, "live workbook writes require confirm='SYNC'")
    if payload.write and payload.expected_mtime_ns is None:
        raise HTTPException(400, "live workbook writes require reviewed mtime")
    return syncmod.sync_workbook(
        get_conn(), config.DEFAULT_WORKBOOK, write=payload.write,
        confirmed_warnings=tuple(payload.confirmed_warnings),
        expected_mtime_ns=payload.expected_mtime_ns,
    )


@app.post("/api/export")
def export():
    return syncmod.export_comparison_workbook(get_conn(), config.DEFAULT_WORKBOOK)


@app.post("/api/backup")
def backup():
    return syncmod.backup_database(get_conn(), config.DEFAULT_DB)


if config.FRONTEND_DIST.exists():
    app.mount("/assets", StaticFiles(
        directory=config.FRONTEND_DIST / "assets"), name="assets"
    )

    @app.get("/")
    def index():
        return FileResponse(config.FRONTEND_DIST / "index.html")
