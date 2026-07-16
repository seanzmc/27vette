"""Staged editing workflow.

Edits never touch the normalized tables directly:

    stage (pending_changes, status=staged)  -> undo possible
      -> validate (single or batch, against current DB + other staged rows)
      -> commit (DB transaction: apply to normalized table, append
         change_history rows, mark pending row committed)
      -> sync (sync.py turns committed-but-unsynced history into an
         editor_ops batch for the workbook)

Deletes are blocked while dependent records exist unless the change is
staged with ``confirmed_dependencies``.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone

from .specs import SPEC_BY_TABLE, TableSpec
from .validation import find_dependents, validate_record


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class StagingError(Exception):
    def __init__(self, errors):
        super().__init__("validation failed")
        self.errors = errors


def _fetch_row(conn, spec: TableSpec, model_id: str, key: dict):
    where = " AND ".join(f'"{k}"=?' for k in spec.key)
    params = [str(key.get(k, "")) for k in spec.key]
    if spec.model_scoped:
        where = "model_id=? AND " + where
        params = [model_id, *params]
    return conn.execute(
        f"SELECT * FROM {spec.table} WHERE {where}", params).fetchone()


def _editable_guard(conn, spec: TableSpec, model_id: str) -> list[dict]:
    if not spec.editable:
        return [{"table": spec.table, "model_id": model_id, "field": "",
                 "entity_key": "",
                 "message": f"{spec.table} is read-only in phase 1 (no gated "
                            "workbook write path exists for its sheet)"}]
    if spec.model_scoped and model_id:
        reg = conn.execute(
            "SELECT active FROM sheet_registry WHERE model_key=? AND "
            "source_role=?", (model_id, spec.role)).fetchone()
        if reg and reg["active"] not in ("True", "1", "TRUE", "true"):
            return [{"table": spec.table, "model_id": model_id, "field": "",
                     "entity_key": "",
                     "message": f"model {model_id!r} registers "
                                f"{spec.table} as inactive scaffold; editing "
                                "is blocked until the source is activated"}]
    return []


def stage_change(conn: sqlite3.Connection, *, table: str, model_id: str,
                 op: str, key: dict, record: dict | None,
                 session_id: str = "", confirm_dependencies: bool = False
                 ) -> dict:
    spec = SPEC_BY_TABLE.get(table)
    if spec is None:
        raise StagingError([{"table": table, "field": "", "entity_key": "",
                             "model_id": model_id,
                             "message": f"unknown table {table!r}"}])
    guard = _editable_guard(conn, spec, model_id)
    if guard:
        raise StagingError(guard)

    old_row = _fetch_row(conn, spec, model_id, key) if op != "add" else None
    if op in ("update", "delete") and old_row is None:
        raise StagingError([{"table": table, "model_id": model_id,
                             "field": ",".join(spec.key),
                             "entity_key": "/".join(str(key.get(k, ""))
                                                    for k in spec.key),
                             "message": "record not found"}])

    errors: list[dict] = []
    dependents: list[dict] = []
    if op in ("add", "update"):
        errors = validate_record(conn, spec, model_id, record or {}, op=op,
                                 original_key=key if op == "update" else None)
    if op == "delete":
        dependents = find_dependents(conn, spec, model_id, key)
        if dependents and not confirm_dependencies:
            raise StagingError([{
                "table": table, "model_id": model_id, "field": "",
                "entity_key": "/".join(str(key.get(k, "")) for k in spec.key),
                "message": f"delete blocked: {len(dependents)} dependent "
                           "record(s) exist; resolve them or stage with "
                           "confirm_dependencies=true",
                "dependents": dependents,
            }])
    if errors:
        raise StagingError(errors)

    old_json = json.dumps({k: old_row[k] for k in old_row.keys()}) \
        if old_row is not None else None
    cur = conn.execute(
        "INSERT INTO pending_changes(ts, session_id, table_name, model_id, "
        "entity_key_json, op, old_json, new_json, status, validation_json, "
        "confirmed_dependencies) VALUES(?,?,?,?,?,?,?,?,?,?,?)",
        (_now(), session_id, table, model_id or "", json.dumps(key), op,
         old_json, json.dumps(record) if record is not None else None,
         "staged", json.dumps({"errors": [], "dependents": dependents}),
         1 if confirm_dependencies else 0),
    )
    conn.commit()
    return get_change(conn, cur.lastrowid)


def get_change(conn, change_id: int) -> dict:
    row = conn.execute(
        "SELECT * FROM pending_changes WHERE id=?", (change_id,)).fetchone()
    if row is None:
        raise StagingError([{"table": "", "model_id": "", "field": "",
                             "entity_key": "",
                             "message": f"change {change_id} not found"}])
    return _change_dict(row)


def _change_dict(row) -> dict:
    d = dict(row)
    for f in ("entity_key_json", "old_json", "new_json", "validation_json"):
        raw = d.pop(f, None)
        d[f.replace("_json", "")] = json.loads(raw) if raw else None
    return d


def list_changes(conn, status: str = "staged") -> list[dict]:
    rows = conn.execute(
        "SELECT * FROM pending_changes WHERE status=? ORDER BY id",
        (status,)).fetchall()
    return [_change_dict(r) for r in rows]


def discard_change(conn, change_id: int) -> dict:
    change = get_change(conn, change_id)
    if change["status"] != "staged":
        raise StagingError([{"table": change["table_name"], "field": "",
                             "model_id": change["model_id"], "entity_key": "",
                             "message": "only staged changes can be discarded"}])
    conn.execute("UPDATE pending_changes SET status='discarded' WHERE id=?",
                 (change_id,))
    conn.commit()
    return get_change(conn, change_id)


def revalidate_staged(conn) -> dict:
    """Batch validation of all staged changes against current data, plus
    cross-change checks (duplicate keys among staged adds)."""
    results = []
    ok = True
    staged = list_changes(conn, "staged")
    # cross-change: two staged adds claiming the same (table, model, key)
    seen_adds: dict[tuple, int] = {}
    add_collisions: dict[int, int] = {}
    for change in staged:
        if change["op"] != "add":
            continue
        spec = SPEC_BY_TABLE[change["table_name"]]
        key_id = (change["table_name"], change["model_id"],
                  tuple(str((change["new"] or {}).get(k, ""))
                        for k in spec.key))
        if key_id in seen_adds:
            add_collisions[change["id"]] = seen_adds[key_id]
        else:
            seen_adds[key_id] = change["id"]
    for change in staged:
        spec = SPEC_BY_TABLE[change["table_name"]]
        errors: list[dict] = []
        dependents: list[dict] = []
        if change["op"] in ("add", "update"):
            errors = validate_record(
                conn, spec, change["model_id"], change["new"] or {},
                op=change["op"],
                original_key=change["entity_key"]
                if change["op"] == "update" else None)
            if change["op"] == "add":
                # ignore duplicate error caused by this same change being
                # re-validated? adds are not applied yet, so none exists.
                pass
        elif change["op"] == "delete":
            if _fetch_row(conn, spec, change["model_id"],
                          change["entity_key"]) is None:
                errors = [{"table": spec.table,
                           "model_id": change["model_id"], "field": "",
                           "entity_key": "", "message": "record no longer "
                           "exists (conflict since staging)"}]
            dependents = find_dependents(conn, spec, change["model_id"],
                                         change["entity_key"])
            if dependents and not change["confirmed_dependencies"]:
                errors.append({"table": spec.table,
                               "model_id": change["model_id"], "field": "",
                               "entity_key": "",
                               "message": f"{len(dependents)} dependent "
                                          "record(s) still exist"})
        if change["id"] in add_collisions:
            errors.append({
                "table": spec.table, "model_id": change["model_id"],
                "field": ",".join(spec.key), "entity_key": "",
                "message": f"duplicate key with staged change "
                           f"#{add_collisions[change['id']]}; discard one",
            })
        if change["op"] == "update" and _fetch_row(
                conn, spec, change["model_id"], change["entity_key"]) is None:
            errors.append({"table": spec.table, "model_id": change["model_id"],
                           "field": "", "entity_key": "",
                           "message": "record no longer exists (conflict "
                                      "since staging)"})
        conn.execute(
            "UPDATE pending_changes SET validation_json=? WHERE id=?",
            (json.dumps({"errors": errors, "dependents": dependents}),
             change["id"]))
        if errors:
            ok = False
        results.append({"change_id": change["id"], "errors": errors,
                        "dependents": dependents})
    conn.commit()
    return {"ok": ok, "results": results}


def commit_staged(conn, actor: str = "") -> dict:
    """Apply all staged changes in one DB transaction + audit rows."""
    validation = revalidate_staged(conn)
    if not validation["ok"]:
        return {"ok": False, "status": "invalid", "validation": validation,
                "committed": 0}
    changes = list_changes(conn, "staged")
    if not changes:
        return {"ok": False, "status": "empty", "committed": 0,
                "validation": validation}
    try:
        conn.execute("BEGIN")
        for change in changes:
            spec = SPEC_BY_TABLE[change["table_name"]]
            _apply_change(conn, spec, change)
            _append_history(conn, spec, change, actor)
            conn.execute(
                "UPDATE pending_changes SET status='committed' WHERE id=?",
                (change["id"],))
        conn.commit()
    except sqlite3.IntegrityError as exc:
        conn.rollback()
        return {"ok": False, "status": "constraint_failed", "committed": 0,
                "validation": validation,
                "errors": [f"database constraint rejected the batch; "
                           f"nothing was committed: {exc}"]}
    except Exception:
        conn.rollback()
        raise
    return {"ok": True, "status": "committed", "committed": len(changes),
            "validation": validation}


def _apply_change(conn, spec: TableSpec, change: dict) -> None:
    model_id = change["model_id"]
    key = change["entity_key"]
    record = change["new"] or {}
    if change["op"] == "add":
        cols = []
        vals = []
        if spec.model_scoped:
            cols.append("model_id")
            vals.append(model_id)
        for c in spec.columns:
            cols.append(c.sql_name())
            vals.append(str(record.get(c.sql_name(), "") or ""))
        # traceability: sheet comes from the model registry (or fixed sheet)
        cols.append("src_sheet")
        vals.append(target_sheet_for(conn, spec, model_id) or "")
        collist = ",".join(f'"{c}"' for c in cols)
        ph = ",".join("?" for _ in cols)
        conn.execute(f"INSERT INTO {spec.table} ({collist}) VALUES ({ph})",
                     vals)
    elif change["op"] == "update":
        sets = ", ".join(f'"{c.sql_name()}"=?' for c in spec.columns)
        params = [str(record.get(c.sql_name(), "") or "")
                  for c in spec.columns]
        where = " AND ".join(f'"{k}"=?' for k in spec.key)
        params += [str(key.get(k, "")) for k in spec.key]
        if spec.model_scoped:
            where = "model_id=? AND " + where
            params.insert(len(spec.columns), model_id)
        conn.execute(f"UPDATE {spec.table} SET {sets} WHERE {where}", params)
    elif change["op"] == "delete":
        where = " AND ".join(f'"{k}"=?' for k in spec.key)
        params = [str(key.get(k, "")) for k in spec.key]
        if spec.model_scoped:
            where = "model_id=? AND " + where
            params = [model_id, *params]
        conn.execute(f"DELETE FROM {spec.table} WHERE {where}", params)


def _append_history(conn, spec: TableSpec, change: dict, actor: str) -> None:
    old = change["old"] or {}
    conn.execute(
        "INSERT INTO change_history(ts, actor, entity_type, entity_id, "
        "model_id, op, old_json, new_json, src_sheet, src_row, "
        "validation_result, status, sync_status, pending_change_id) "
        "VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (_now(), actor, spec.table,
         "/".join(str(change["entity_key"].get(k, "")) for k in spec.key),
         change["model_id"], change["op"],
         json.dumps(change["old"]) if change["old"] else None,
         json.dumps(change["new"]) if change["new"] else None,
         old.get("src_sheet", "") or target_sheet_for(
             conn, spec, change["model_id"]) or "",
         old.get("src_row"),
         "passed", "committed",
         "pending" if spec.editable else "n/a",
         change["id"]),
    )


def target_sheet_for(conn, spec: TableSpec, model_id: str) -> str | None:
    """Workbook sheet a change to (table, model) writes to."""
    if spec.sheet:
        return spec.sheet[0]
    if spec.role and model_id:
        row = conn.execute(
            "SELECT sheet_name FROM sheet_registry WHERE model_key=? AND "
            "source_role=?", (model_id, spec.role)).fetchone()
        return row["sheet_name"] if row else None
    return None
