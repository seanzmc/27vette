"""FastAPI routes over the canonical workbook-congruent database."""

from __future__ import annotations

import hashlib
import json
import sqlite3

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from . import config, db as dbmod, importer, staging, sync as syncmod
from .catalog import (
    CENTRAL_EDIT_ROLES,
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


_LEGACY_TABLE_ROLES = {
    "form_steps": "runtime_steps",
    "section_presentation": "section_presentation",
}
_COMPAT_ONLY_RECORD_FIELDS = {
    "id", "_display_id", "display_name", "section_name", "sections",
}


def _legacy_bool(value: object) -> str:
    return "True" if value in (True, 1, "1", "True") else "False"


def _compatibility_id(
    model_key: str, table_role: str, spec, row: dict
) -> str:
    identity = json.dumps(
        [model_key, table_role, *[row.get(column) for column in spec.key]],
        separators=(",", ":"),
        default=str,
    )
    return "compat_" + hashlib.sha256(identity.encode()).hexdigest()[:20]


def _finding_dict(finding: object, index: int) -> dict:
    get = lambda name, default="": getattr(finding, name, default)
    return {
        "id": index,
        "severity": get("severity"),
        "status": get("status"),
        "code": get("code"),
        "category": get("code"),
        "message": get("message"),
        "source_sheet": get("source_sheet"),
        "sheet": get("source_sheet"),
        "source_row": get("source_row", None),
        "src_row": get("source_row", None),
        "source_column": get("source_column"),
        "field": get("source_column"),
        "model_key": get("model_key"),
        "model_id": get("model_key"),
        "value": get("value", None),
    }


def _import_response(report) -> dict:
    findings = [
        _finding_dict(finding, index)
        for index, finding in enumerate(report.findings, start=1)
    ]
    decisions = {
        id(finding) for finding in report.decision_required
    }
    differences = {
        id(finding) for finding in report.contract_differences
    }
    legacy_status = (
        "imported" if report.status == "validated" else "imported_with_issues"
    )
    return {
        "status": report.status,
        "live_models": list(report.live_models),
        "findings": findings,
        "decision_required": [
            item for finding, item in zip(report.findings, findings, strict=True)
            if id(finding) in decisions
        ],
        "contract_differences": [
            item for finding, item in zip(report.findings, findings, strict=True)
            if id(finding) in differences
        ],
        "candidate_path": (
            str(report.candidate_path) if report.candidate_path else None
        ),
        "promoted_path": (
            str(report.promoted_path) if report.promoted_path else None
        ),
        # Checked-in React aliases. They are projections of the same report,
        # not a second import result or persistence path.
        "run": {"status": legacy_status},
        "issues": findings,
    }


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
    report = importer.import_workbook(config.DEFAULT_DB, config.DEFAULT_WORKBOOK)
    return _import_response(report)


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
    output = []
    for row in rows:
        item = dict(row)
        item["label"] = item.get("model_label") or humanize(item["model_key"])
        for field in ("active", "default_model", "promoted_to_runtime"):
            item[field] = _legacy_bool(item.get(field))
        item["scaffold"] = item["active"] != "True"
        output.append(item)
    return {"models": output}


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
    section_master = {
        row["section_id"]: dict(row)
        for row in conn.execute("SELECT * FROM sections")
    }
    variants = [dict(row) for row in conn.execute(
        "SELECT mv.*, v.trim_level, v.body_style, v.display_name, v.base_price "
        "FROM model_variants mv JOIN variants v USING(variant_id) "
        "WHERE mv.model_key=? ORDER BY mv.display_order", (model_key,),
    )]
    for variant in variants:
        variant["active"] = _legacy_bool(variant.get("active"))
    for presentation in presentations:
        master = section_master.get(presentation["section_id"], {})
        presentation["section_name"] = master.get("section_name", "")
        presentation["display_name"] = (
            presentation.get("display_label")
            or master.get("section_name")
            or display_id(presentation["section_id"], ("sec_",))
        )
        presentation["active"] = _legacy_bool(presentation.get("active"))
        presentation["id"] = _compatibility_id(
            model_key, "section_presentation",
            edit_spec(conn, model_key, "section_presentation"), presentation,
        )
    for step in steps:
        step["display_name"] = step.get("step_label") or humanize(
            step["step_key"]
        )
        step["active"] = _legacy_bool(step.get("active"))
        step["sections"] = [
            presentation for presentation in presentations
            if presentation.get("step_key") == step["step_key"]
        ]
        step["id"] = _compatibility_id(
            model_key, "runtime_steps",
            edit_spec(conn, model_key, "runtime_steps"), step,
        )
    return {
        "model_key": model_key,
        "steps": steps,
        "sections_master": list(section_master.values()),
        "section_presentation": presentations,
        "variants": variants,
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
            "table": role,
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
        "table": role,
        "label": humanize(role),
        "model_scoped": True,
        "editable": True,
        "sql_table": spec.sql_table,
        "key": list(spec.key),
        "columns": [
            {
                "name": column,
                "label": humanize(column),
                "header": column,
                "ctype": (
                    "bool" if column in spec.booleans
                    else "int" if spec.types[column] == "integer"
                    else spec.types[column]
                ),
                "enum": [
                    "" if value is None else value
                    for value in spec.enums.get(column, ())
                ],
                "is_key": column in spec.key,
                "nullable": column in spec.nullable,
            }
            for column in spec.columns
            if column != "model_key" or role in CENTRAL_EDIT_ROLES
        ],
        "sheet": staging.target_sheet_for(conn, model_key, role),
        "sheet_for_model": staging.target_sheet_for(conn, model_key, role),
        "id_prefixes": [],
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
    where = ["model_key=?"]
    values = [model_key]
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
        "records": [
            {
                **dict(row),
                "id": _compatibility_id(
                    model_key, table_role, spec, dict(row)
                ),
            }
            for row in rows
        ],
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


# Transitional aliases for the checked-in React client. These delegate to the
# same physical-table services and do not restore the removed conceptual specs.
@app.get("/api/records/{table_role}/schema")
def record_schema_compat(table_role: str, model: str = ""):
    canonical_role = _LEGACY_TABLE_ROLES.get(table_role, table_role)
    result = record_schema(model, canonical_role)
    result["table"] = table_role
    if canonical_role in CENTRAL_EDIT_ROLES:
        # Legacy structure forms carry model_key as part of the row/key.
        result["model_scoped"] = False
    return result


@app.get("/api/records/{table_role}")
def records_compat(
    table_role: str,
    model: str = "",
    search: str = "",
    limit: int = Query(200, le=2000),
    offset: int = 0,
):
    canonical_role = _LEGACY_TABLE_ROLES.get(table_role, table_role)
    result = records(model, canonical_role, search, limit, offset)
    result["model_id"] = model
    result["table"] = table_role
    return result


@app.post("/api/records/{table_role}/dependencies")
def dependencies_compat(table_role: str, body: dict):
    canonical_role = _LEGACY_TABLE_ROLES.get(table_role, table_role)
    model_key = (
        body.get("model_id")
        or body.get("model_key")
        or (body.get("key") or {}).get("model_key")
    )
    key = dict(body.get("key") or {})
    key.pop("id", None)
    key.pop("_display_id", None)
    return dependencies_post(model_key, canonical_role, {**body, "key": key})


@app.post("/api/changes", response_model=ChangeOut)
def stage(payload: StageChangeRequest):
    requested_role = payload.table_role or payload.table
    table_role = _LEGACY_TABLE_ROLES.get(requested_role, requested_role)
    key = dict(payload.key)
    record = dict(payload.record) if payload.record is not None else None
    for field in _COMPAT_ONLY_RECORD_FIELDS:
        key.pop(field, None)
        if record is not None:
            record.pop(field, None)
    embedded_models = {
        str(value) for value in (
            key.get("model_key"),
            record.get("model_key") if record is not None else None,
        ) if value not in (None, "")
    }
    explicit_models = {
        value for value in (payload.model_key, payload.model_id) if value
    }
    model_candidates = explicit_models | embedded_models
    model_key = next(iter(model_candidates)) if len(model_candidates) == 1 else ""
    if table_role in CENTRAL_EDIT_ROLES and model_key:
        key["model_key"] = model_key
        if record is not None:
            record["model_key"] = model_key
    if (
        len(model_candidates) != 1
        or (payload.table_role and payload.table
            and _LEGACY_TABLE_ROLES.get(payload.table_role, payload.table_role)
            != _LEGACY_TABLE_ROLES.get(payload.table, payload.table))
        or not model_key or not table_role
    ):
        raise HTTPException(
            status_code=422,
            detail={"errors": [{
                "field": "model_id/table",
                "message": "one consistent model and table role are required",
            }]},
        )
    try:
        return staging.stage_change(
            get_conn(), model_key=model_key,
            table_role=table_role, op=payload.op, key=key,
            record=record, session_id=payload.session_id,
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
    model_key: str = "", table_role: str = "", model: str = "",
    entity_type: str = "", sync_status: str = "",
    limit: int = Query(200, le=2000), offset: int = 0,
):
    where, values = [], []
    model_key = model_key or model
    table_role = table_role or entity_type
    if model_key:
        where.append("model_key=?")
        values.append(model_key)
    if table_role:
        where.append("table_role=?")
        values.append(table_role)
    if sync_status:
        where.append("sync_status=?")
        values.append(sync_status)
    clause = "WHERE " + " AND ".join(where) if where else ""
    total = get_conn().execute(
        f"SELECT COUNT(*) FROM change_history {clause}", values,
    ).fetchone()[0]
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
        item["model_id"] = item["model_key"]
        item["entity_type"] = item["table_role"]
        item["table"] = item["table_role"]
        output.append(item)
    return {"total": total, "history": output}


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
