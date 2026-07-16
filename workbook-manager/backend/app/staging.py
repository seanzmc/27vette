"""Atomic staged editing for registry-resolved physical model tables."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from typing import Mapping

from .catalog import RoleEditSpec, edit_spec
from .validation import find_dependents, validate_record


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _quote(identifier: str) -> str:
    return '"' + identifier.replace('"', '""') + '"'


class StagingError(Exception):
    def __init__(self, errors):
        super().__init__("validation failed")
        self.errors = errors


def _issue(spec: RoleEditSpec, field: str, message: str, **extra) -> dict:
    return {
        "model_key": spec.model_key,
        "table_role": spec.table_role,
        "sql_table": spec.sql_table,
        "field": field,
        "entity_key": "",
        "message": message,
        **extra,
    }


def _where_key(spec: RoleEditSpec, key: Mapping[str, object]):
    return (
        " AND ".join(f"{_quote(column)} IS ?" for column in spec.key),
        [key.get(column) for column in spec.key],
    )


def _fetch_row(conn, spec: RoleEditSpec, key: Mapping[str, object]):
    where, values = _where_key(spec, key)
    return conn.execute(
        f"SELECT * FROM {_quote(spec.sql_table)} WHERE {where}", values
    ).fetchone()


def _source_lineage(conn, spec: RoleEditSpec, key: Mapping[str, object]):
    key_json = json.dumps(dict(key), sort_keys=True, separators=(",", ":"))
    return conn.execute(
        "SELECT source_sheet, source_row FROM import_lineage "
        "WHERE sql_table=? AND primary_key_json=? "
        "ORDER BY id LIMIT 1",
        (spec.sql_table, key_json),
    ).fetchone()


def _shared_source_guard(
    conn: sqlite3.Connection, spec: RoleEditSpec, op: str,
    key: Mapping[str, object],
) -> list[dict]:
    """Reject edits whose one workbook row represents multiple SQL rows."""
    if op == "add" and spec.table_role in {"interiors", "color_overrides"}:
        return [_issue(
            spec,
            "",
            "add is not reversible without choosing shared workbook ownership; "
            "supply the source/scoping business decision before staging",
        )]
    if op == "add":
        return []
    lineage = _source_lineage(conn, spec, key)
    if lineage is None:
        return [_issue(
            spec, "", "existing row has no exact import lineage; edit blocked"
        )]
    disposition = conn.execute(
        "SELECT destinations_json FROM source_row_disposition "
        "WHERE source_sheet=? AND source_row=? AND disposition='emitted' "
        "ORDER BY import_run_id DESC LIMIT 1",
        (lineage["source_sheet"], lineage["source_row"]),
    ).fetchone()
    destinations = json.loads(disposition["destinations_json"]) if disposition else []
    if len(destinations) > 1:
        return [_issue(
            spec,
            "",
            "source row fans out to multiple canonical destinations; a "
            "one-model edit would diverge shared workbook data",
            destinations=destinations,
        )]
    return []


_DERIVED_READ_ONLY = {
    "rule_mapping": frozenset({"trim_level_scope", "variant_scope"}),
    "price_rules": frozenset({"variant_scope"}),
    "interiors": frozenset({"active"}),
    "interior_scope": frozenset({"body_style", "variant_id"}),
}


def _derived_guard(
    spec: RoleEditSpec, old_row, record: Mapping[str, object] | None, op: str
) -> list[dict]:
    record = record or {}
    errors = []
    for column in _DERIVED_READ_ONLY.get(spec.table_role, ()):
        if op == "add" and column in record and record[column] is not None:
            errors.append(_issue(
                spec, column, "compiler-derived column is read-only"
            ))
        elif op == "update" and column in record and old_row is not None \
                and record[column] != old_row[column]:
            errors.append(_issue(
                spec, column, "compiler-derived column is read-only"
            ))
    return errors


def stage_change(
    conn: sqlite3.Connection,
    *,
    model_key: str,
    table_role: str,
    op: str,
    key: dict,
    record: dict | None,
    session_id: str = "",
    confirm_dependencies: bool = False,
) -> dict:
    try:
        spec = edit_spec(conn, model_key, table_role)
    except KeyError:
        raise StagingError([{
            "model_key": model_key,
            "table_role": table_role,
            "sql_table": "",
            "field": "",
            "entity_key": "",
            "message": "unknown or inactive model/table role",
        }]) from None
    if op not in {"add", "update", "delete"}:
        raise StagingError([_issue(spec, "op", f"unsupported operation {op!r}")])
    old_row = _fetch_row(conn, spec, key) if op != "add" else None
    if op in {"update", "delete"} and old_row is None:
        raise StagingError([_issue(spec, ",".join(spec.key), "record not found")])

    errors = _shared_source_guard(conn, spec, op, key)
    errors += _derived_guard(spec, old_row, record, op)
    dependents: list[dict] = []
    if op in {"add", "update"}:
        errors += validate_record(
            conn, model_key, table_role, record or {}, op=op,
            original_key=key if op == "update" else None,
        )
    else:
        dependents = find_dependents(conn, model_key, table_role, key)
        if dependents and not confirm_dependencies:
            errors.append(_issue(
                spec,
                "",
                f"delete blocked: {len(dependents)} dependent record(s) exist",
                dependents=dependents,
            ))
    if errors:
        raise StagingError(errors)

    old = dict(old_row) if old_row is not None else None
    new = dict(record) if record is not None else None
    if new is not None:
        new["model_key"] = model_key
    cursor = conn.execute(
        "INSERT INTO pending_changes("
        "ts, session_id, model_key, table_role, sql_table, entity_key_json, "
        "op, old_json, new_json, status, validation_json, "
        "confirmed_dependencies) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
        (
            _now(), session_id, model_key, table_role, spec.sql_table,
            json.dumps(key, sort_keys=True), op,
            json.dumps(old) if old is not None else None,
            json.dumps(new) if new is not None else None,
            "staged", json.dumps({"errors": [], "dependents": dependents}),
            1 if confirm_dependencies else 0,
        ),
    )
    conn.commit()
    return get_change(conn, cursor.lastrowid)


def _change_dict(row) -> dict:
    result = dict(row)
    for field in ("entity_key_json", "old_json", "new_json", "validation_json"):
        raw = result.pop(field, None)
        result[field.removesuffix("_json")] = json.loads(raw) if raw else None
    return result


def get_change(conn, change_id: int) -> dict:
    row = conn.execute(
        "SELECT * FROM pending_changes WHERE id=?", (change_id,)
    ).fetchone()
    if row is None:
        raise StagingError([{
            "model_key": "", "table_role": "", "sql_table": "", "field": "",
            "entity_key": "", "message": f"change {change_id} not found",
        }])
    return _change_dict(row)


def list_changes(conn, status: str = "staged") -> list[dict]:
    return [
        _change_dict(row)
        for row in conn.execute(
            "SELECT * FROM pending_changes WHERE status=? ORDER BY id", (status,)
        )
    ]


def discard_change(conn, change_id: int) -> dict:
    change = get_change(conn, change_id)
    if change["status"] != "staged":
        raise StagingError([{
            "model_key": change["model_key"],
            "table_role": change["table_role"],
            "sql_table": change["sql_table"],
            "field": "", "entity_key": "",
            "message": "only staged changes can be discarded",
        }])
    conn.execute(
        "UPDATE pending_changes SET status='discarded' WHERE id=?", (change_id,)
    )
    conn.commit()
    return get_change(conn, change_id)


def revalidate_staged(conn) -> dict:
    changes = list_changes(conn, "staged")
    results = []
    seen = {}
    ok = True
    for change in changes:
        identity = (
            change["model_key"], change["table_role"],
            json.dumps(change["entity_key"], sort_keys=True),
        )
        errors = []
        if identity in seen:
            errors.append({
                "model_key": change["model_key"],
                "table_role": change["table_role"],
                "sql_table": change["sql_table"],
                "field": "", "entity_key": "",
                "message": f"duplicate staged identity with change #{seen[identity]}",
            })
        seen[identity] = change["id"]
        spec = edit_spec(conn, change["model_key"], change["table_role"])
        current = _fetch_row(conn, spec, change["entity_key"])
        if change["op"] == "add":
            errors += validate_record(
                conn, change["model_key"], change["table_role"],
                change["new"] or {}, op="add",
            )
        elif current is None:
            errors.append(_issue(spec, "", "record no longer exists"))
        elif change["op"] == "update":
            errors += validate_record(
                conn, change["model_key"], change["table_role"],
                change["new"] or {}, op="update",
                original_key=change["entity_key"],
            )
        else:
            dependents = find_dependents(
                conn, change["model_key"], change["table_role"],
                change["entity_key"],
            )
            if dependents and not change["confirmed_dependencies"]:
                errors.append(_issue(
                    spec, "", f"{len(dependents)} dependent record(s) still exist"
                ))
        conn.execute(
            "UPDATE pending_changes SET validation_json=? WHERE id=?",
            (json.dumps({"errors": errors}), change["id"]),
        )
        ok = ok and not errors
        results.append({"change_id": change["id"], "errors": errors})
    conn.commit()
    return {"ok": ok, "results": results}


def _coerce(spec: RoleEditSpec, column: str, value: object):
    if value == "" and column in spec.nullable:
        return None
    if column in spec.booleans:
        if value in (True, 1, "1", "True"):
            return 1
        if value in (False, 0, "0", "False"):
            return 0
    if value is not None and spec.types.get(column) == "integer":
        return int(str(value).replace(",", ""))
    return value


def _apply_change(conn, spec: RoleEditSpec, change: dict) -> None:
    record = change["new"] or {}
    if change["op"] == "add":
        columns = ["model_key"] + [
            column for column in spec.columns
            if column != "model_key" and column in record
        ]
        values = [spec.model_key] + [
            _coerce(spec, column, record[column]) for column in columns[1:]
        ]
        conn.execute(
            f"INSERT INTO {_quote(spec.sql_table)} "
            f"({','.join(_quote(column) for column in columns)}) "
            f"VALUES({','.join('?' for _ in columns)})",
            values,
        )
    elif change["op"] == "update":
        columns = [
            column for column in spec.columns
            if column not in {"model_key", *spec.key} and column in record
        ]
        where, key_values = _where_key(spec, change["entity_key"])
        conn.execute(
            f"UPDATE {_quote(spec.sql_table)} SET "
            + ",".join(f"{_quote(column)}=?" for column in columns)
            + f" WHERE {where}",
            [_coerce(spec, column, record[column]) for column in columns]
            + key_values,
        )
    else:
        where, values = _where_key(spec, change["entity_key"])
        conn.execute(
            f"DELETE FROM {_quote(spec.sql_table)} WHERE {where}", values
        )


def _append_history(conn, spec: RoleEditSpec, change: dict, actor: str) -> None:
    lineage = _source_lineage(conn, spec, change["entity_key"])
    conn.execute(
        "INSERT INTO change_history("
        "ts, actor, model_key, table_role, sql_table, entity_id, op, old_json, "
        "new_json, src_sheet, src_row, validation_result, status, sync_status, "
        "pending_change_id) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (
            _now(), actor, spec.model_key, spec.table_role, spec.sql_table,
            "/".join(str(change["entity_key"].get(k, "")) for k in spec.key),
            change["op"],
            json.dumps(change["old"]) if change["old"] is not None else None,
            json.dumps(change["new"]) if change["new"] is not None else None,
            lineage["source_sheet"] if lineage else target_sheet_for(
                conn, spec.model_key, spec.table_role
            ) or "",
            lineage["source_row"] if lineage else None,
            "passed", "committed", "pending", change["id"],
        ),
    )


def commit_staged(conn, actor: str = "") -> dict:
    validation = revalidate_staged(conn)
    if not validation["ok"]:
        return {"ok": False, "status": "invalid", "committed": 0,
                "validation": validation}
    changes = list_changes(conn, "staged")
    if not changes:
        return {"ok": False, "status": "empty", "committed": 0,
                "validation": validation}
    try:
        conn.execute("BEGIN")
        for change in changes:
            spec = edit_spec(conn, change["model_key"], change["table_role"])
            _apply_change(conn, spec, change)
            _append_history(conn, spec, change, actor)
            conn.execute(
                "UPDATE pending_changes SET status='committed' WHERE id=?",
                (change["id"],),
            )
        conn.commit()
    except sqlite3.IntegrityError as error:
        conn.rollback()
        return {
            "ok": False, "status": "constraint_failed", "committed": 0,
            "validation": validation,
            "errors": [f"database constraint rejected the batch: {error}"],
        }
    return {"ok": True, "status": "committed", "committed": len(changes),
            "validation": validation}


def target_sheet_for(
    conn: sqlite3.Connection, model_key: str, table_role: str
) -> str | None:
    spec = edit_spec(conn, model_key, table_role)
    rows = conn.execute(
        "SELECT DISTINCT source_sheet FROM schema_mapping "
        "WHERE model_key=? AND sql_table=? AND substr(source_column,1,2)<>'__' "
        "ORDER BY source_sheet",
        (model_key, spec.sql_table),
    ).fetchall()
    sheets = tuple(row["source_sheet"] for row in rows)
    return sheets[0] if len(sheets) == 1 else None
