"""Registry-driven validation for canonical physical model tables."""

from __future__ import annotations

import json
import sqlite3
from typing import Mapping

from .catalog import (
    CENTRAL_EDIT_ROLES,
    MODEL_TABLE_ROLES,
    ROLE_EXCLUSIVE_COLUMN_PAIRS,
    RoleEditSpec,
    canonical_value,
    edit_spec,
)


def _quote(identifier: str) -> str:
    return '"' + identifier.replace('"', '""') + '"'


def _blank(value: object) -> bool:
    return value is None or (isinstance(value, str) and value.strip() == "")


def _where_key(spec: RoleEditSpec, key: Mapping[str, object]):
    clauses = []
    values = []
    for column in spec.key:
        clauses.append(f"{_quote(column)} IS ?")
        values.append(key.get(column))
    return " AND ".join(clauses), values


def _error(spec: RoleEditSpec, field: str, message: str, record=None) -> dict:
    record = record or {}
    return {
        "model_key": spec.model_key,
        "model_id": spec.model_key,
        "table_role": spec.table_role,
        "table": spec.table_role,
        "sql_table": spec.sql_table,
        "field": field,
        "entity_key": "/".join(str(record.get(k, "")) for k in spec.key),
        "message": message,
    }


def validate_record(
    conn: sqlite3.Connection,
    model_key: str,
    role: str,
    record: Mapping[str, object],
    *,
    op: str,
    original_key: Mapping[str, object] | None = None,
) -> list[dict]:
    """Validate one canonical row without accepting a caller SQL identifier."""
    spec = edit_spec(conn, model_key, role)
    errors: list[dict] = []
    canonical: dict[str, object] = {}
    for column, value in record.items():
        try:
            canonical[column] = canonical_value(spec, column, value)
        except ValueError as error:
            canonical[column] = value
            errors.append(_error(spec, column, str(error), record))
    record = canonical
    supplied_model = record.get("model_key")
    if supplied_model is not None and supplied_model != model_key:
        errors.append(_error(
            spec, "model_key",
            f"record model_key {supplied_model!r} does not match route "
            f"model_key {model_key!r}", record,
        ))

    unknown = set(record) - set(spec.columns)
    for column in sorted(unknown):
        errors.append(_error(spec, column, "unknown canonical column", record))

    for column in spec.key:
        if column not in spec.nullable and _blank(record.get(column)):
            errors.append(_error(
                spec, column, f"key field {column!r} is required", record
            ))
    if op in {"add", "update"}:
        for column in sorted(spec.required):
            if _blank(record.get(column)):
                errors.append(_error(
                    spec, column, f"required field {column!r} is missing", record
                ))
    for left, right in ROLE_EXCLUSIVE_COLUMN_PAIRS.get(role, ()):
        populated = int(not _blank(record.get(left))) + int(
            not _blank(record.get(right))
        )
        if populated != 1:
            errors.append(_error(
                spec,
                f"{left},{right}",
                f"exactly one of {left!r} and {right!r} is required",
                record,
            ))
    if op == "update" and original_key is not None:
        for column in spec.key:
            if record.get(column) != original_key.get(column):
                errors.append(_error(
                    spec,
                    column,
                    f"key field {column!r} cannot change on update "
                    f"({original_key.get(column)!r} -> {record.get(column)!r}); "
                    "stage a delete plus an add instead",
                    record,
                ))

    for column, value in record.items():
        if column == "model_key" or column not in spec.types or _blank(value):
            continue
        allowed = spec.enums.get(column)
        if allowed and value not in allowed:
            errors.append(_error(
                spec, column,
                f"{column} must be one of {list(allowed)!r}, got {value!r}",
                record,
            ))

    if op == "add" and not errors:
        where, values = _where_key(spec, record)
        if conn.execute(
            f"SELECT 1 FROM {_quote(spec.sql_table)} WHERE {where} LIMIT 1",
            values,
        ).fetchone():
            errors.append(_error(
                spec, ",".join(spec.key),
                "a record with this key already exists in model scope", record,
            ))

    candidate = dict(record)
    candidate["model_key"] = model_key
    for foreign_key in spec.foreign_keys:
        values = [candidate.get(column) for column in foreign_key.columns]
        if any(_blank(value) for value in values):
            continue
        where = " AND ".join(
            f"{_quote(column)}=?" for column in foreign_key.target_columns
        )
        if conn.execute(
            f"SELECT 1 FROM {_quote(foreign_key.target_table)} "
            f"WHERE {where} LIMIT 1",
            values,
        ).fetchone() is None:
            staged_parent = False
            for pending in conn.execute(
                "SELECT new_json FROM pending_changes "
                "WHERE sql_table=? AND status='staged' AND op='add'",
                (foreign_key.target_table,),
            ):
                staged = json.loads(pending["new_json"] or "{}")
                if all(
                    staged.get(target_column) == value
                    for target_column, value in zip(
                        foreign_key.target_columns, values, strict=True
                    )
                ):
                    staged_parent = True
                    break
            if staged_parent:
                continue
            for column in foreign_key.columns:
                if column != "model_key":
                    errors.append(_error(
                        spec,
                        column,
                        f"reference does not resolve to "
                        f"{foreign_key.target_table}",
                        record,
                    ))
    return errors


def _source_evidence(
    conn: sqlite3.Connection, table: str, key: Mapping[str, object]
) -> tuple[str, int | None]:
    key_json = json.dumps(dict(key), sort_keys=True, separators=(",", ":"))
    row = conn.execute(
        "SELECT source_sheet, source_row FROM import_lineage "
        "WHERE sql_table=? AND primary_key_json=? "
        "ORDER BY id LIMIT 1",
        (table, key_json),
    ).fetchone()
    return (str(row["source_sheet"]), int(row["source_row"])) if row else ("", None)


def find_dependents(
    conn: sqlite3.Connection,
    model_key: str,
    role: str,
    key: Mapping[str, object],
) -> list[dict]:
    """Inspect every canonical model role for inbound SQLite foreign keys."""
    target = edit_spec(conn, model_key, role)
    target_values = dict(key)
    target_values["model_key"] = model_key
    dependents: list[dict] = []
    for other_role in (*MODEL_TABLE_ROLES, *CENTRAL_EDIT_ROLES):
        other = edit_spec(conn, model_key, other_role)
        for foreign_key in other.foreign_keys:
            if foreign_key.target_table != target.sql_table:
                continue
            try:
                values = [
                    target_values[column]
                    for column in foreign_key.target_columns
                ]
            except KeyError:
                continue
            where = " AND ".join(
                f"{_quote(column)} IS ?" for column in foreign_key.columns
            )
            rows = conn.execute(
                f"SELECT * FROM {_quote(other.sql_table)} WHERE {where}", values
            ).fetchall()
            for row in rows:
                row_key = {column: row[column] for column in other.key}
                source_sheet, source_row = _source_evidence(
                    conn, other.sql_table, row_key
                )
                dependents.append({
                    "model_key": model_key,
                    "model_id": model_key,
                    "table_role": other_role,
                    "table": other_role,
                    "sql_table": other.sql_table,
                    "field": ",".join(foreign_key.columns),
                    "entity_key": "/".join(str(row[column]) for column in other.key),
                    "key": row_key,
                    "source_sheet": source_sheet,
                    "source_row": source_row,
                    "src_sheet": source_sheet,
                    "src_row": source_row,
                })
    return dependents


def check_references(conn: sqlite3.Connection) -> list[dict]:
    """Return SQLite's canonical unresolved relationship report."""
    return [
        {
            "severity": "error",
            "category": "unresolved_ref",
            "sql_table": row[0],
            "rowid": row[1],
            "target_table": row[2],
            "foreign_key_id": row[3],
            "message": "canonical foreign key violation",
        }
        for row in conn.execute("PRAGMA foreign_key_check")
    ]
