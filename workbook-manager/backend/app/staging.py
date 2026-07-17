"""Atomic staged editing for registry-resolved physical model tables."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from typing import Mapping

from .catalog import (
    RoleEditSpec,
    canonical_record,
    canonical_value,
    edit_spec,
)
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
        "model_id": spec.model_key,
        "table_role": spec.table_role,
        "table": spec.table_role,
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


def _canonical_json_record(
    spec: RoleEditSpec, raw: str | None
) -> dict | None:
    value = json.loads(raw) if raw is not None else None
    if value is None:
        return None
    if not isinstance(value, dict) or set(value) - set(spec.columns):
        raise ValueError("persisted edit row is not a canonical record")
    return canonical_record(spec, value)


def _committed_unsynced_add_target(
    conn: sqlite3.Connection,
    spec: RoleEditSpec,
    key: Mapping[str, object],
    current_row,
) -> str | None:
    """Prove a lineage-free row is an exact, still-unsynced committed add."""
    matching = []
    for row in conn.execute(
        "SELECT * FROM pending_changes WHERE model_key=? AND table_role=? "
        "AND sql_table=? AND status='committed' ORDER BY id",
        (spec.model_key, spec.table_role, spec.sql_table),
    ):
        try:
            entity_key = canonical_record(
                spec, json.loads(row["entity_key_json"])
            )
        except (json.JSONDecodeError, TypeError, ValueError):
            return None
        if entity_key == canonical_record(spec, key):
            matching.append(dict(row))
    if not matching:
        return None
    state = None
    for index, change in enumerate(matching):
        histories = conn.execute(
            "SELECT h.* FROM change_history h "
            "WHERE h.pending_change_id=? AND h.status='committed'",
            (change["id"],),
        ).fetchall()
        if len(histories) != 1 or conn.execute(
            "SELECT 1 FROM change_history WHERE related_history_id=? "
            "AND status='sync_succeeded' LIMIT 1",
            (histories[0]["id"] if histories else -1,),
        ).fetchone():
            return None
        history = histories[0]
        try:
            old = _canonical_json_record(spec, change["old_json"])
            new = _canonical_json_record(spec, change["new_json"])
            history_old = _canonical_json_record(spec, history["old_json"])
            history_new = _canonical_json_record(spec, history["new_json"])
        except (json.JSONDecodeError, TypeError, ValueError):
            return None
        if (
            history["model_key"] != spec.model_key
            or history["table_role"] != spec.table_role
            or history["sql_table"] != spec.sql_table
            or history["op"] != change["op"]
            or history_old != old
            or history_new != new
        ):
            return None
        if index == 0:
            if change["op"] != "add" or old is not None or not isinstance(new, dict):
                return None
        elif change["op"] == "update":
            if old != state or not isinstance(new, dict):
                return None
        elif change["op"] == "delete":
            if old != state or new is not None:
                return None
        else:
            return None
        state = new
    try:
        current = canonical_record(spec, dict(current_row))
    except ValueError:
        return None
    if state is None or state != current:
        return None
    return target_sheet_for(conn, spec.model_key, spec.table_role)


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
        current_row = _fetch_row(conn, spec, key)
        if current_row is not None and _committed_unsynced_add_target(
            conn, spec, key, current_row
        ):
            return []
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
    if spec.table_role == "runtime_steps" and destinations:
        destination_tables = {
            item.get("destination_table") for item in destinations
        }
        step_destinations = [
            item for item in destinations
            if item.get("destination_table") == "runtime_steps"
        ]
        if (
            destination_tables <= {"runtime_steps", "runtime_route_keys"}
            and len(step_destinations) == 1
            and step_destinations[0].get("destination_key") == dict(key)
        ):
            return []
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


def _value_changed(
    spec: RoleEditSpec, column: str, before: object, after: object
) -> bool:
    try:
        return canonical_value(spec, column, before) != canonical_value(
            spec, column, after
        )
    except (TypeError, ValueError):
        return True


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
    try:
        key = canonical_record(spec, key)
    except ValueError as error:
        raise StagingError([_issue(spec, ",".join(spec.key), str(error))]) from None
    old_row = _fetch_row(conn, spec, key) if op != "add" else None
    if op in {"update", "delete"} and old_row is None:
        raise StagingError([_issue(spec, ",".join(spec.key), "record not found")])

    old = canonical_record(spec, dict(old_row)) if old_row is not None else None
    candidate = dict(record or {}) if record is not None else None
    if op == "update":
        candidate = dict(old or {})
        candidate.update(record or {})
    elif candidate is not None:
        candidate.setdefault("model_key", model_key)

    errors = _shared_source_guard(conn, spec, op, key)
    dependents: list[dict] = []
    if op in {"add", "update"}:
        candidate_errors = validate_record(
            conn, model_key, table_role, candidate or {}, op=op,
            original_key=key if op == "update" else None,
        )
        errors += candidate_errors
        if not candidate_errors:
            candidate = canonical_record(spec, candidate or {})
            errors += _derived_guard(spec, old, candidate, op)
            if op == "update":
                changed = [
                    column for column in spec.columns
                    if column not in {"model_key", *spec.key}
                    and _value_changed(
                        spec, column, (old or {}).get(column),
                        candidate.get(column),
                    )
                ]
                if not changed:
                    errors.append(_issue(
                        spec, "", "update has no changed non-key fields"
                    ))
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

    new = candidate
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
    result["model_id"] = result["model_key"]
    legacy_table = (
        "form_steps"
        if result["table_role"] == "runtime_steps"
        else result["table_role"]
    )
    result["table"] = legacy_table
    result["table_name"] = legacy_table
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


def _dependent_is_resolved_by_staged_change(
    conn: sqlite3.Connection,
    parent_spec: RoleEditSpec,
    parent_key: Mapping[str, object],
    dependent: dict,
    staged_by_identity: Mapping[tuple[str, str, str], dict],
) -> bool:
    identity = (
        dependent["model_key"], dependent["table_role"],
        json.dumps(dependent["key"], sort_keys=True),
    )
    resolution = staged_by_identity.get(identity)
    if resolution is None:
        return False
    if resolution["op"] == "delete":
        return True
    if resolution["op"] != "update":
        return False
    child_spec = edit_spec(
        conn, dependent["model_key"], dependent["table_role"]
    )
    parent_values = {"model_key": parent_spec.model_key, **dict(parent_key)}
    candidate = resolution["new"] or {}
    for foreign_key in child_spec.foreign_keys:
        if foreign_key.target_table != parent_spec.sql_table:
            continue
        if all(
            candidate.get(child_column) == parent_values.get(parent_column)
            for child_column, parent_column in zip(
                foreign_key.columns, foreign_key.target_columns, strict=True
            )
        ):
            return False
    return True


def revalidate_staged(conn, *, commit: bool = True) -> dict:
    changes = list_changes(conn, "staged")
    staged_by_identity = {
        (
            change["model_key"], change["table_role"],
            json.dumps(change["entity_key"], sort_keys=True),
        ): change for change in changes
    }
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
        try:
            change["entity_key"] = canonical_record(
                spec, change["entity_key"] or {}
            )
            if change["old"] is not None:
                change["old"] = canonical_record(spec, change["old"])
            if change["new"] is not None:
                change["new"] = canonical_record(spec, change["new"])
        except ValueError as error:
            errors.append(_issue(spec, "", str(error)))
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
            missing = [
                dependent for dependent in dependents
                if not _dependent_is_resolved_by_staged_change(
                    conn, spec, change["entity_key"], dependent,
                    staged_by_identity,
                )
            ]
            if dependents and not change["confirmed_dependencies"]:
                errors.append(_issue(
                    spec, "", f"{len(dependents)} dependent record(s) still exist"
                ))
            elif missing:
                errors.append(_issue(
                    spec, "",
                    f"delete batch is incomplete: {len(missing)} dependent "
                    "record(s) are not staged for deletion",
                    dependents=missing,
                ))
        if errors:
            conn.execute(
                "UPDATE pending_changes SET validation_json=? WHERE id=?",
                (json.dumps({"errors": errors}), change["id"]),
            )
        else:
            conn.execute(
                "UPDATE pending_changes SET entity_key_json=?, old_json=?, "
                "new_json=?, validation_json=? WHERE id=?",
                (
                    json.dumps(change["entity_key"], sort_keys=True),
                    json.dumps(change["old"])
                    if change["old"] is not None else None,
                    json.dumps(change["new"])
                    if change["new"] is not None else None,
                    json.dumps({"errors": []}), change["id"],
                ),
            )
        ok = ok and not errors
        results.append({"change_id": change["id"], "errors": errors})
    if commit:
        conn.commit()
    return {"ok": ok, "results": results}


def _stale_conflicts(conn, changes: list[dict]) -> list[str]:
    """Compare staged old snapshots to canonical rows under the write lock."""
    conflicts = []
    for change in changes:
        if change["op"] not in {"update", "delete"}:
            continue
        spec = edit_spec(conn, change["model_key"], change["table_role"])
        current = _fetch_row(conn, spec, change["entity_key"])
        if current is None:
            conflicts.append(
                f"{spec.sql_table} {change['entity_key']} no longer exists"
            )
            continue
        current_record = canonical_record(
            spec, {column: current[column] for column in spec.columns}
        )
        expected = change.get("old")
        if expected is None:
            conflicts.append(
                f"{spec.sql_table} {change['entity_key']} has no staged old snapshot"
            )
            continue
        expected_record = canonical_record(
            spec, {column: expected.get(column) for column in spec.columns}
        )
        if current_record != expected_record:
            identity = "/".join(
                str(change["entity_key"].get(column, ""))
                for column in spec.key
            )
            conflicts.append(
                f"{spec.sql_table} {identity} changed after it was staged"
            )
    return conflicts


def _apply_change(conn, spec: RoleEditSpec, change: dict) -> None:
    record = change["new"] or {}
    if change["op"] == "add":
        columns = ["model_key"] + [
            column for column in spec.columns
            if column != "model_key" and column in record
        ]
        values = [spec.model_key] + [
            canonical_value(spec, column, record[column])
            for column in columns[1:]
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
        if not columns:
            raise sqlite3.OperationalError("update has no writable columns")
        where, key_values = _where_key(spec, change["entity_key"])
        conn.execute(
            f"UPDATE {_quote(spec.sql_table)} SET "
            + ",".join(f"{_quote(column)}=?" for column in columns)
            + f" WHERE {where}",
            [canonical_value(spec, column, record[column]) for column in columns]
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


def _ordered_changes(conn, changes: list[dict]) -> list[dict]:
    """Return a stable FK-safe batch order or raise for an unresolved cycle."""
    by_id = {change["id"]: change for change in changes}
    edges = {change["id"]: set() for change in changes}
    indegree = {change["id"]: 0 for change in changes}

    table_changes = {}
    for change in changes:
        spec = edit_spec(conn, change["model_key"], change["table_role"])
        table_changes.setdefault(spec.sql_table, []).append(change)

    def add_edge(before: int, after: int) -> None:
        if before == after or after in edges[before]:
            return
        edges[before].add(after)
        indegree[after] += 1

    for child in changes:
        child_spec = edit_spec(
            conn, child["model_key"], child["table_role"]
        )
        values = child["old"] if child["op"] == "delete" else child["new"]
        values = values or {}
        for foreign_key in child_spec.foreign_keys:
            referenced_values = tuple(
                values.get(column) for column in foreign_key.columns
            )
            parent = None
            for candidate in table_changes.get(foreign_key.target_table, ()):
                candidate_values = (
                    candidate["old"] if candidate["op"] == "delete"
                    else candidate["new"]
                ) or {}
                if tuple(
                    candidate_values.get(column)
                    for column in foreign_key.target_columns
                ) == referenced_values:
                    parent = candidate
                    break
            if child["op"] == "update":
                old_values = child["old"] or {}
                old_reference = tuple(
                    old_values.get(column) for column in foreign_key.columns
                )
                for old_parent in table_changes.get(
                    foreign_key.target_table, ()
                ):
                    if old_parent["op"] != "delete":
                        continue
                    parent_values = old_parent["old"] or {}
                    if tuple(
                        parent_values.get(column)
                        for column in foreign_key.target_columns
                    ) == old_reference:
                        add_edge(child["id"], old_parent["id"])
            if parent is None:
                continue
            if child["op"] == "delete" and parent["op"] == "delete":
                add_edge(child["id"], parent["id"])
            elif child["op"] != "delete" and parent["op"] == "add":
                add_edge(parent["id"], child["id"])
            elif parent["op"] == "delete":
                raise sqlite3.IntegrityError(
                    "batch leaves a child referencing a deleted parent"
                )

    ready = sorted(change_id for change_id, degree in indegree.items() if degree == 0)
    ordered = []
    while ready:
        change_id = ready.pop(0)
        ordered.append(by_id[change_id])
        for after in sorted(edges[change_id]):
            indegree[after] -= 1
            if indegree[after] == 0:
                ready.append(after)
                ready.sort()
    if len(ordered) != len(changes):
        raise sqlite3.IntegrityError("dependency cycle in staged batch")
    return ordered


def commit_staged(conn, actor: str = "") -> dict:
    changes = list_changes(conn, "staged")
    validation = {"ok": True, "results": []}
    if not changes:
        return {"ok": False, "status": "empty", "committed": 0,
                "validation": validation}
    try:
        conn.execute("BEGIN IMMEDIATE")
        validation = revalidate_staged(conn, commit=False)
        if not validation["ok"]:
            conn.commit()
            return {"ok": False, "status": "invalid", "committed": 0,
                    "validation": validation}
        changes = list_changes(conn, "staged")
        conflicts = _stale_conflicts(conn, changes)
        if conflicts:
            conn.rollback()
            return {
                "ok": False, "status": "stale_conflict", "committed": 0,
                "validation": validation, "errors": conflicts,
            }
        changes = _ordered_changes(conn, changes)
        for change in changes:
            spec = edit_spec(conn, change["model_key"], change["table_role"])
            _apply_change(conn, spec, change)
            _append_history(conn, spec, change, actor)
            conn.execute(
                "UPDATE pending_changes SET status='committed' WHERE id=?",
                (change["id"],),
            )
        violations = conn.execute("PRAGMA foreign_key_check").fetchall()
        if violations:
            raise sqlite3.IntegrityError(
                f"batch leaves {len(violations)} foreign-key violation(s)"
            )
        conn.commit()
    except sqlite3.Error as error:
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
        "WHERE (model_key=? OR model_key IS NULL) AND sql_table=? "
        "AND substr(source_column,1,2)<>'__' "
        "ORDER BY source_sheet",
        (model_key, spec.sql_table),
    ).fetchall()
    sheets = tuple(row["source_sheet"] for row in rows)
    return sheets[0] if len(sheets) == 1 else None
