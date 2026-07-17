"""FastAPI routes over the canonical workbook-congruent database."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import APIRouter, Depends, FastAPI, HTTPException, Query, Request
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
from .schemas import (
    ChangeListOut,
    ChangeOut,
    CommitOut,
    CommitRequest,
    FindingsOut,
    HistoryOut,
    ImportReportOut,
    ImportRequest,
    ImportRunOut,
    ModelRuntimeOut,
    ModelTableRecordsOut,
    ModelTablesOut,
    ModelVariantsOut,
    OperationOut,
    SchemaMappingsOut,
    StageChangeRequest,
    SyncRequest,
    ValidationOut,
)
from .staging import StagingError
from .validation import find_dependents


router = APIRouter()


def get_conn(request: Request) -> sqlite3.Connection:
    """Return the connection owned by this FastAPI application instance."""
    conn = getattr(request.app.state, "connection", None)
    if conn is None:
        path = Path(request.app.state.db_path)
        if request.app.state.uses_default_path:
            config.ensure_dirs()
        path.parent.mkdir(parents=True, exist_ok=True)
        existed = path.exists()
        conn = dbmod.connect(path)
        if not existed:
            dbmod.create_canonical_schema(conn)
        request.app.state.connection = conn
    return conn


def _close_connection(api: FastAPI) -> None:
    conn = getattr(api.state, "connection", None)
    if conn is not None:
        conn.close()
        api.state.connection = None


def _staging_error(exc: StagingError) -> HTTPException:
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
    decisions = {id(finding) for finding in report.decision_required}
    differences = {id(finding) for finding in report.contract_differences}
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
        "run": {"status": legacy_status},
        "issues": findings,
    }


def _import_run(conn: sqlite3.Connection, import_run_id: int) -> dict:
    row = conn.execute(
        "SELECT * FROM import_runs WHERE id=?", (import_run_id,)
    ).fetchone()
    if row is None:
        raise KeyError(import_run_id)
    item = dict(row)
    item["row_counts"] = json.loads(item.pop("row_counts_json") or "{}")
    item["issue_counts"] = json.loads(item.pop("issue_counts_json") or "{}")
    return item


def _finding_row(row: sqlite3.Row) -> dict:
    item = dict(row)
    return {
        "severity": item["severity"],
        "status": "mapped",
        "code": item["category"],
        "message": item["message"],
        "source_sheet": item["sheet"],
        "source_row": item["src_row"],
        "source_column": item["field"],
        "model_key": item["model_id"],
        "sql_table": item["table_name"],
        "entity_key": item["entity_key"],
        "value": None,
    }


def _import_findings(conn: sqlite3.Connection, import_run_id: int) -> dict:
    _import_run(conn, import_run_id)
    rows = conn.execute(
        "SELECT * FROM import_issues WHERE run_id=? ORDER BY id",
        (import_run_id,),
    ).fetchall()
    return {
        "import_run_id": import_run_id,
        "findings": [_finding_row(row) for row in rows],
    }


def _schema_mappings(conn: sqlite3.Connection) -> dict:
    rows = []
    for row in conn.execute(
        "SELECT * FROM schema_mapping ORDER BY source_sheet, source_column, "
        "model_key, sql_table, sql_column"
    ):
        item = dict(row)
        item["transform_parameters"] = json.loads(
            item.pop("transform_parameters_json") or "{}"
        )
        rows.append(item)
    return {"mappings": rows}


def _model_tables(conn: sqlite3.Connection, model_key: str) -> dict:
    if model_key not in LIVE_MODELS:
        raise KeyError(model_key)
    rows = conn.execute(
        "SELECT * FROM model_table_registry "
        "WHERE model_key=? AND active=1 ORDER BY table_role", (model_key,)
    ).fetchall()
    if not rows:
        raise KeyError(model_key)
    tables = []
    for row in rows:
        item = dict(row)
        role = item["table_role"]
        sql_table = resolve_model_table(conn, model_key, role)
        spec = edit_spec(conn, model_key, role)
        tables.append({
            "model_key": model_key,
            "role": role,
            "sql_table": sql_table,
            "source_sheets": json.loads(item["source_sheets_json"] or "[]"),
            "source_filter": item["source_filter"],
            "mapping_type": item["mapping_type"],
            "active": bool(item["active"]),
            "count": conn.execute(
                f'SELECT COUNT(*) FROM "{sql_table}"'
            ).fetchone()[0],
            "key": list(spec.key),
            "editable": True,
        })
    return {"model_key": model_key, "tables": tables}


def _variants(conn: sqlite3.Connection, model_key: str) -> dict:
    if model_key not in LIVE_MODELS:
        raise KeyError(model_key)
    rows = conn.execute(
        "SELECT mv.model_key, mv.variant_id, mv.display_order, mv.active, "
        "mv.notes, v.model_year, v.trim_level, v.body_style, v.display_name, "
        "v.base_price FROM model_variants mv "
        "JOIN variants v USING(variant_id) WHERE mv.model_key=? "
        "ORDER BY mv.display_order, mv.variant_id", (model_key,),
    ).fetchall()
    return {"model_key": model_key, "variants": [dict(row) for row in rows]}


def _runtime_v2(conn: sqlite3.Connection, model_key: str) -> dict:
    if model_key not in LIVE_MODELS:
        raise KeyError(model_key)

    def rows(table: str, order_by: str) -> list[dict]:
        return [dict(row) for row in conn.execute(
            f'SELECT * FROM "{table}" WHERE model_key=? ORDER BY {order_by}',
            (model_key,),
        )]

    return {
        "model_key": model_key,
        "steps": rows("runtime_steps", "runtime_order, step_key"),
        "section_presentation": rows(
            "section_presentation", "section_display_order, section_id"
        ),
        "context_sections": rows(
            "runtime_context_sections", "section_display_order, section_id"
        ),
        "context_choices": rows(
            "runtime_context_choices", "display_order, context_choice_id"
        ),
        "summary_sections": rows(
            "runtime_summary_sections", "display_order, section_key"
        ),
        "step_summary_map": rows("runtime_step_summary_map", "step_key"),
    }


def _models(conn: sqlite3.Connection) -> dict:
    rows = conn.execute(
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


def _runtime(conn: sqlite3.Connection, model_key: str) -> dict:
    if model_key not in LIVE_MODELS:
        raise KeyError(model_key)
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
            model_key,
            "section_presentation",
            edit_spec(conn, model_key, "section_presentation"),
            presentation,
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
            model_key,
            "runtime_steps",
            edit_spec(conn, model_key, "runtime_steps"),
            step,
        )
    return {
        "model_key": model_key,
        "steps": steps,
        "sections_master": list(section_master.values()),
        "section_presentation": presentations,
        "variants": variants,
    }


def _collections(conn: sqlite3.Connection, model_key: str) -> dict:
    if model_key not in LIVE_MODELS:
        raise KeyError(model_key)
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


def _schema_dict(conn: sqlite3.Connection, model_key: str, role: str) -> dict:
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


def _records(
    conn: sqlite3.Connection,
    model_key: str,
    table_role: str,
    search: str,
    limit: int,
    offset: int,
) -> dict:
    spec = edit_spec(conn, model_key, table_role)
    registry = conn.execute(
        "SELECT source_sheets_json, source_filter, mapping_type "
        "FROM model_table_registry WHERE model_key=? AND table_role=? "
        "AND active=1",
        (model_key, table_role),
    ).fetchone()
    source_sheets = json.loads(
        registry["source_sheets_json"] or "[]"
    ) if registry else [staging.target_sheet_for(conn, model_key, table_role)]
    where = ["model_key=?"]
    values: list[object] = [model_key]
    if search:
        where.append("(" + " OR ".join(
            f'CAST("{column}" AS TEXT) LIKE ?' for column in spec.columns
        ) + ")")
        values.extend([f"%{search}%"] * len(spec.columns))
    clause = "WHERE " + " AND ".join(where)
    total = conn.execute(
        f'SELECT COUNT(*) FROM "{spec.sql_table}" {clause}', values
    ).fetchone()[0]
    order = ",".join(f'"{column}"' for column in spec.key)
    rows = conn.execute(
        f'SELECT * FROM "{spec.sql_table}" {clause} ORDER BY {order} '
        "LIMIT ? OFFSET ?", [*values, limit, offset],
    ).fetchall()
    return {
        "model_key": model_key,
        "table_role": table_role,
        "sql_table": spec.sql_table,
        "source_sheets": source_sheets,
        "source_filter": registry["source_filter"] if registry else "",
        "mapping_type": registry["mapping_type"] if registry else "exact",
        "key": list(spec.key),
        "total": total,
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


def _dependencies(
    conn: sqlite3.Connection, model_key: str, table_role: str, key: dict
) -> dict:
    dependents = find_dependents(conn, model_key, table_role, key)
    return {"dependents": dependents, "count": len(dependents)}


def _staging_errors_with_lineage(
    conn: sqlite3.Connection,
    model_key: str,
    table_role: str,
    key: dict,
    errors: list[dict],
) -> list[dict]:
    """Attach reversible workbook evidence to canonical domain errors."""
    try:
        spec = edit_spec(conn, model_key, table_role)
    except KeyError:
        return errors
    canonical_key = {column: key.get(column) for column in spec.key}
    key_json = json.dumps(canonical_key, sort_keys=True, separators=(",", ":"))
    lineage = conn.execute(
        "SELECT source_sheet, source_row FROM import_lineage "
        "WHERE sql_table=? AND primary_key_json=? ORDER BY id LIMIT 1",
        (spec.sql_table, key_json),
    ).fetchone()
    output = []
    for raw in errors:
        error = dict(raw)
        field = str(error.get("field") or "")
        mapping = conn.execute(
            "SELECT source_sheet, source_column FROM schema_mapping "
            "WHERE sql_table=? AND sql_column=? "
            "AND (model_key=? OR model_key IS NULL) "
            "ORDER BY CASE WHEN model_key=? THEN 0 ELSE 1 END, id LIMIT 1",
            (spec.sql_table, field, model_key, model_key),
        ).fetchone()
        error.setdefault(
            "source_sheet",
            str(lineage["source_sheet"] if lineage else (
                mapping["source_sheet"] if mapping
                else staging.target_sheet_for(conn, model_key, table_role) or ""
            )),
        )
        error.setdefault(
            "source_row", int(lineage["source_row"]) if lineage else None
        )
        error.setdefault(
            "source_column", str(mapping["source_column"] if mapping else field)
        )
        output.append(error)
    return output


def _stage_change(conn: sqlite3.Connection, payload: StageChangeRequest) -> dict:
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
        or (
            payload.table_role and payload.table
            and _LEGACY_TABLE_ROLES.get(payload.table_role, payload.table_role)
            != _LEGACY_TABLE_ROLES.get(payload.table, payload.table)
        )
        or not model_key
        or not table_role
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
            conn,
            model_key=model_key,
            table_role=table_role,
            op=payload.op,
            key=key,
            record=record,
            session_id=payload.session_id,
            confirm_dependencies=payload.confirm_dependencies,
        )
    except StagingError as exc:
        enriched = _staging_errors_with_lineage(
            conn, model_key, table_role, key, exc.errors
        )
        raise HTTPException(
            status_code=422, detail={"errors": enriched}
        ) from exc


def _history(
    conn: sqlite3.Connection,
    model_key: str,
    table_role: str,
    sync_status: str,
    limit: int,
    offset: int,
) -> dict:
    where, values = [], []
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
    total = conn.execute(
        f"SELECT COUNT(*) FROM change_history {clause}", values,
    ).fetchone()[0]
    rows = conn.execute(
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


@router.get("/api/status")
def status(conn: sqlite3.Connection = Depends(get_conn)):
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


def _run_import_to(db_path: Path, workbook_path: Path) -> dict:
    report = importer.import_workbook(db_path, workbook_path)
    return _import_response(report)


def run_import():
    """Compatibility callable retained for the path-only import regression."""
    if not config.DEFAULT_WORKBOOK.exists():
        raise HTTPException(404, f"workbook not found: {config.DEFAULT_WORKBOOK}")
    return _run_import_to(config.DEFAULT_DB, config.DEFAULT_WORKBOOK)


@router.post("/api/import")
def run_import_endpoint(request: Request):
    if not config.DEFAULT_WORKBOOK.exists():
        raise HTTPException(404, f"workbook not found: {config.DEFAULT_WORKBOOK}")
    _close_connection(request.app)
    return _run_import_to(
        Path(request.app.state.db_path), config.DEFAULT_WORKBOOK
    )


@router.get("/api/import/latest")
def latest_import(conn: sqlite3.Connection = Depends(get_conn)):
    report = importer.latest_report(conn)
    if report is None:
        raise HTTPException(404, "no import has run yet")
    return report


@router.post("/api/imports", response_model=ImportReportOut)
def create_import(payload: ImportRequest, request: Request):
    workbook_path = Path(payload.workbook_path)
    if not workbook_path.is_file():
        raise HTTPException(404, f"workbook not found: {workbook_path}")
    _close_connection(request.app)
    report = importer.import_workbook(
        Path(request.app.state.db_path), workbook_path
    )
    body = _import_response(report)
    canonical = {
        field: body[field]
        for field in ImportReportOut.model_fields
    }
    if report.status != "validated":
        blocking = (
            body["decision_required"]
            or body["contract_differences"]
            or body["findings"]
        )
        raise HTTPException(
            status_code=409,
            detail={"status": report.status, "findings": blocking},
        )
    return canonical


@router.get("/api/imports/{import_run_id}", response_model=ImportRunOut)
def import_run(
    import_run_id: int, conn: sqlite3.Connection = Depends(get_conn)
):
    try:
        return _import_run(conn, import_run_id)
    except KeyError:
        raise HTTPException(404, "unknown import run") from None


@router.get(
    "/api/imports/{import_run_id}/findings", response_model=FindingsOut
)
def import_findings(
    import_run_id: int, conn: sqlite3.Connection = Depends(get_conn)
):
    try:
        return _import_findings(conn, import_run_id)
    except KeyError:
        raise HTTPException(404, "unknown import run") from None


@router.get("/api/schema/mappings", response_model=SchemaMappingsOut)
def schema_mappings(conn: sqlite3.Connection = Depends(get_conn)):
    return _schema_mappings(conn)


@router.get("/api/models")
def models(conn: sqlite3.Connection = Depends(get_conn)):
    return _models(conn)


@router.get("/api/structure/{model_key}")
def structure(model_key: str, conn: sqlite3.Connection = Depends(get_conn)):
    try:
        return _runtime(conn, model_key)
    except KeyError:
        raise HTTPException(404, f"unknown model {model_key!r}") from None


@router.get("/api/models/{model_key}/collections")
def collections(
    model_key: str, conn: sqlite3.Connection = Depends(get_conn)
):
    try:
        return _collections(conn, model_key)
    except KeyError:
        raise HTTPException(404, f"unknown model {model_key!r}") from None


@router.get("/api/models/{model_key}/tables", response_model=ModelTablesOut)
def model_tables(
    model_key: str, conn: sqlite3.Connection = Depends(get_conn)
):
    try:
        return _model_tables(conn, model_key)
    except KeyError:
        raise HTTPException(404, "unknown model") from None


@router.get(
    "/api/models/{model_key}/variants", response_model=ModelVariantsOut
)
def model_variants(
    model_key: str, conn: sqlite3.Connection = Depends(get_conn)
):
    try:
        return _variants(conn, model_key)
    except KeyError:
        raise HTTPException(404, "unknown model") from None


@router.get("/api/models/{model_key}/runtime", response_model=ModelRuntimeOut)
def model_runtime(
    model_key: str, conn: sqlite3.Connection = Depends(get_conn)
):
    try:
        return _runtime_v2(conn, model_key)
    except KeyError:
        raise HTTPException(404, "unknown model") from None


@router.get("/api/models/{model_key}/tables/{table_role}/schema")
def record_schema(
    model_key: str,
    table_role: str,
    conn: sqlite3.Connection = Depends(get_conn),
):
    try:
        return _schema_dict(conn, model_key, table_role)
    except KeyError:
        raise HTTPException(404, "unknown model/table role") from None


@router.get(
    "/api/models/{model_key}/tables/{table_role}",
    response_model=ModelTableRecordsOut,
)
def records(
    model_key: str,
    table_role: str,
    search: str = "",
    limit: int = Query(200, le=2000),
    offset: int = 0,
    conn: sqlite3.Connection = Depends(get_conn),
):
    try:
        return _records(conn, model_key, table_role, search, limit, offset)
    except KeyError:
        raise HTTPException(404, "unknown model/table role") from None


@router.post("/api/models/{model_key}/tables/{table_role}/dependencies")
def dependencies_post(
    model_key: str,
    table_role: str,
    body: dict,
    conn: sqlite3.Connection = Depends(get_conn),
):
    try:
        return _dependencies(conn, model_key, table_role, body.get("key", {}))
    except KeyError:
        raise HTTPException(404, "unknown model/table role") from None


@router.get("/api/records/{table_role}/schema")
def record_schema_compat(
    table_role: str,
    model: str = "",
    conn: sqlite3.Connection = Depends(get_conn),
):
    canonical_role = _LEGACY_TABLE_ROLES.get(table_role, table_role)
    try:
        result = _schema_dict(conn, model, canonical_role)
    except KeyError:
        raise HTTPException(404, "unknown model/table role") from None
    result["table"] = table_role
    if canonical_role in CENTRAL_EDIT_ROLES:
        result["model_scoped"] = False
    return result


@router.get("/api/records/{table_role}")
def records_compat(
    table_role: str,
    model: str = "",
    search: str = "",
    limit: int = Query(200, le=2000),
    offset: int = 0,
    conn: sqlite3.Connection = Depends(get_conn),
):
    canonical_role = _LEGACY_TABLE_ROLES.get(table_role, table_role)
    try:
        result = _records(conn, model, canonical_role, search, limit, offset)
    except KeyError:
        raise HTTPException(404, "unknown model/table role") from None
    result["model_id"] = model
    result["table"] = table_role
    return result


@router.post("/api/records/{table_role}/dependencies")
def dependencies_compat(
    table_role: str,
    body: dict,
    conn: sqlite3.Connection = Depends(get_conn),
):
    canonical_role = _LEGACY_TABLE_ROLES.get(table_role, table_role)
    model_key = (
        body.get("model_id")
        or body.get("model_key")
        or (body.get("key") or {}).get("model_key")
    )
    key = dict(body.get("key") or {})
    key.pop("id", None)
    key.pop("_display_id", None)
    try:
        return _dependencies(conn, model_key, canonical_role, key)
    except KeyError:
        raise HTTPException(404, "unknown model/table role") from None


@router.post("/api/changes", response_model=ChangeOut)
def stage(
    payload: StageChangeRequest,
    conn: sqlite3.Connection = Depends(get_conn),
):
    return _stage_change(conn, payload)


@router.get("/api/changes", response_model=ChangeListOut)
def changes(
    status: str = "staged", conn: sqlite3.Connection = Depends(get_conn)
):
    return {"changes": staging.list_changes(conn, status)}


@router.delete("/api/changes/{change_id}", response_model=ChangeOut)
def discard(change_id: int, conn: sqlite3.Connection = Depends(get_conn)):
    try:
        return staging.discard_change(conn, change_id)
    except StagingError as exc:
        raise _staging_error(exc) from exc


@router.post("/api/changes/validate", response_model=ValidationOut)
def validate_changes(conn: sqlite3.Connection = Depends(get_conn)):
    return staging.revalidate_staged(conn)


@router.post("/api/changes/commit", response_model=CommitOut)
def commit(
    payload: CommitRequest, conn: sqlite3.Connection = Depends(get_conn)
):
    return staging.commit_staged(conn, actor=payload.actor)


@router.get("/api/history", response_model=HistoryOut)
def history(
    model_key: str = "",
    table_role: str = "",
    model: str = "",
    entity_type: str = "",
    sync_status: str = "",
    limit: int = Query(200, le=2000),
    offset: int = 0,
    conn: sqlite3.Connection = Depends(get_conn),
):
    return _history(
        conn,
        model_key or model,
        table_role or entity_type,
        sync_status,
        limit,
        offset,
    )


@router.post("/api/sync", response_model=OperationOut)
def sync_endpoint(
    payload: SyncRequest,
    conn: sqlite3.Connection = Depends(get_conn),
):
    if payload.write and payload.confirm != "SYNC":
        raise HTTPException(400, "live workbook writes require confirm='SYNC'")
    if payload.write and payload.expected_mtime_ns is None:
        raise HTTPException(400, "live workbook writes require reviewed mtime")
    result = syncmod.sync_workbook(
        conn,
        config.DEFAULT_WORKBOOK,
        write=payload.write,
        confirmed_warnings=tuple(payload.confirmed_warnings),
        expected_mtime_ns=payload.expected_mtime_ns,
    )
    if not result.get("ok"):
        raise HTTPException(status_code=409, detail=result)
    return result


@router.post("/api/export", response_model=OperationOut)
def export(conn: sqlite3.Connection = Depends(get_conn)):
    return syncmod.export_comparison_workbook(conn, config.DEFAULT_WORKBOOK)


@router.post("/api/backup", response_model=OperationOut)
def backup(request: Request, conn: sqlite3.Connection = Depends(get_conn)):
    return syncmod.backup_database(conn, Path(request.app.state.db_path))


def create_app(db_path: Path | None = None) -> FastAPI:
    """Build an app whose connection is isolated to ``db_path``."""

    @asynccontextmanager
    async def lifespan(api: FastAPI):
        yield
        _close_connection(api)

    api = FastAPI(
        title="27vette Workbook Manager", version="0.2.0", lifespan=lifespan
    )
    api.state.db_path = Path(db_path) if db_path is not None else config.DEFAULT_DB
    api.state.uses_default_path = db_path is None
    api.state.connection = None
    api.include_router(router)
    if config.FRONTEND_DIST.exists():
        api.mount(
            "/assets",
            StaticFiles(directory=config.FRONTEND_DIST / "assets"),
            name="assets",
        )

        @api.get("/")
        def index():
            return FileResponse(config.FRONTEND_DIST / "index.html")
    return api


app = create_app()
