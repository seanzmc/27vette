"""Staged editing workflow.

Edits never touch the normalized tables directly:

    stage (pending_changes, status=staged)  -> undo possible
      -> validate (single or batch, against current DB + other staged rows)
      -> commit (DB transaction: apply to normalized table, append
         change_history rows, mark pending row committed)
      -> sync (sync.py turns committed-but-unsynced history into an
         editor_ops batch for the workbook)

Deletes are blocked while dependent records exist. Coordinated deletes belong
in one draft ChangeSet whose complete final graph is validated by the shared
preview service; the legacy staged-row path has no dependency bypass.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone

from corvette_form_generator.model_configs import discover_generation_model_configs

from .catalog import SPEC_BY_TABLE, TableSpec
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


def _editable_guard(
    conn,
    spec: TableSpec,
    model_id: str,
    *,
    op: str,
    key: dict,
    record: dict | None,
) -> list[dict]:
    def reject(message: str) -> list[dict]:
        return [{
            "table": spec.table,
            "model_id": model_id,
            "field": "model_key",
            "entity_key": "",
            "message": message,
        }]

    if not spec.editable:
        return reject(
            f"{spec.table} is read-only in phase 1 (no gated workbook write "
            "path exists for its sheet)"
        )

    row_model = str((record or {}).get("model_key") or key.get("model_key") or "")
    candidate_model = str(model_id or row_model).strip()
    if row_model and model_id and row_model != model_id:
        return reject(
            f"model context {model_id!r} does not match row model_key {row_model!r}"
        )
    if candidate_model == "*":
        if spec.editor_family != "asset_map":
            return reject("wildcard model scope is writable only for asset_map")
        return []

    model_definition = spec.editor_family == "model_master"
    topology = spec.editor_family in {"model_workbook_sources", "model_variants"}
    publication = spec.editor_family == "model_registry_promotion"
    active_fixed = spec.editor_family in {
        "model_interior_scope",
        "default_selection_rules",
        "interior_components",
        "runtime_steps_meta",
        "section_presentation_meta",
        "context_section_master_meta",
        "order_summary_sections_meta",
        "step_order_summary_map_meta",
        "asset_map",
    }
    model_owned = spec.model_scoped or bool(spec.role) or model_definition or topology or publication or active_fixed
    if not model_owned:
        return []
    if not candidate_model:
        return reject(f"{spec.table} requires a concrete model context")

    model = conn.execute(
        "SELECT active FROM models WHERE model_key=?", (candidate_model,)
    ).fetchone()
    if model is None:
        return reject(f"unknown model {candidate_model!r}")
    model_active = str(model["active"]).strip().lower() in {"true", "1", "yes"}

    if model_definition:
        if op == "add":
            return reject("adding a new model_master identity is outside this workflow")
        return []
    if topology:
        return []
    if not model_active:
        return reject(f"inactive model {candidate_model!r} cannot own {spec.table} content")

    if publication and record:
        publishing = str(record.get("active") or "").lower() in {"true", "1", "yes"} and str(
            record.get("promoted_to_runtime") or ""
        ).lower() in {"true", "1", "yes"}
        if publishing:
            from . import config

            generatable = discover_generation_model_configs(config.DEFAULT_WORKBOOK)
            if candidate_model not in generatable:
                return reject(
                    f"model {candidate_model!r} cannot be promoted because it is not generatable"
                )

    if spec.role:
        reg = conn.execute(
            "SELECT sheet_name, active FROM sheet_registry WHERE model_key=? AND "
            "source_role=?",
            (candidate_model, spec.role),
        ).fetchone()
        if reg is None:
            return reject(
                f"model {candidate_model!r} has no {spec.role!r} source registration"
            )
        if str(reg["active"]).strip().lower() not in {"true", "1", "yes"}:
            return reject(
                f"model {candidate_model!r} registers {spec.table} as an inactive "
                "source role"
            )
        if not str(reg["sheet_name"] or "").strip():
            return reject(
                f"model {candidate_model!r} has no physical source sheet for {spec.table}"
            )
    return []


def stage_change(conn: sqlite3.Connection, *, table: str, model_id: str,
                 op: str, key: dict, record: dict | None,
                 session_id: str = "",
                 state_conn: sqlite3.Connection | None = None,
                 ) -> dict:
    state = state_conn or conn
    spec = SPEC_BY_TABLE.get(table)
    if spec is None:
        raise StagingError([{"table": table, "field": "", "entity_key": "",
                             "model_id": model_id,
                             "message": f"unknown table {table!r}"}])
    guard = _editable_guard(
        conn,
        spec,
        model_id,
        op=op,
        key=key,
        record=record,
    )
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
        if dependents:
            raise StagingError([{
                "table": table, "model_id": model_id, "field": "",
                "entity_key": "/".join(str(key.get(k, "")) for k in spec.key),
                "message": f"delete blocked: {len(dependents)} dependent "
                           "record(s) exist; emit the parent and dependent "
                           "deletes together through one draft ChangeSet",
                "dependents": dependents,
            }])
    if errors:
        raise StagingError(errors)

    old_json = json.dumps({k: old_row[k] for k in old_row.keys()}) \
        if old_row is not None else None
    cur = state.execute(
        "INSERT INTO pending_changes(ts, session_id, table_name, model_id, "
        "entity_key_json, op, old_json, new_json, status, validation_json, "
        "confirmed_dependencies) VALUES(?,?,?,?,?,?,?,?,?,?,?)",
        (_now(), session_id, table, model_id or "", json.dumps(key), op,
         old_json, json.dumps(record) if record is not None else None,
         "staged", json.dumps({"errors": [], "dependents": dependents}), 0),
    )
    state.commit()
    return get_change(state, cur.lastrowid)


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


def revalidate_staged(
    conn, state_conn: sqlite3.Connection | None = None
) -> dict:
    """Batch validation of all staged changes against current data, plus
    cross-change checks (duplicate keys among staged adds)."""
    results = []
    ok = True
    state = state_conn or conn
    staged = list_changes(state, "staged")
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
            if dependents:
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
        state.execute(
            "UPDATE pending_changes SET validation_json=? WHERE id=?",
            (json.dumps({"errors": errors, "dependents": dependents}),
             change["id"]))
        if errors:
            ok = False
        results.append({"change_id": change["id"], "errors": errors,
                        "dependents": dependents})
    state.commit()
    return {"ok": ok, "results": results}


def commit_staged(
    conn, actor: str = "", state_conn: sqlite3.Connection | None = None
) -> dict:
    """Apply all staged changes in one DB transaction + audit rows."""
    state = state_conn or conn
    validation = revalidate_staged(conn, state)
    if not validation["ok"]:
        return {"ok": False, "status": "invalid", "validation": validation,
                "committed": 0}
    changes = list_changes(state, "staged")
    if not changes:
        return {"ok": False, "status": "empty", "committed": 0,
                "validation": validation}
    try:
        conn.execute("BEGIN")
        if state is not conn:
            state.execute("BEGIN")
        for change in changes:
            spec = SPEC_BY_TABLE[change["table_name"]]
            _apply_change(conn, spec, change)
            _append_history(state, conn, spec, change, actor)
            state.execute(
                "UPDATE pending_changes SET status='committed' WHERE id=?",
                (change["id"],))
        conn.commit()
        if state is not conn:
            state.commit()
    except sqlite3.IntegrityError as exc:
        conn.rollback()
        if state is not conn:
            state.rollback()
        return {"ok": False, "status": "constraint_failed", "committed": 0,
                "validation": validation,
                "errors": [f"database constraint rejected the batch; "
                           f"nothing was committed: {exc}"]}
    except Exception:
        conn.rollback()
        if state is not conn:
            state.rollback()
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


def _append_history(
    state_conn, projection_conn, spec: TableSpec, change: dict, actor: str
) -> None:
    old = change["old"] or {}
    state_conn.execute(
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
             projection_conn, spec, change["model_id"]) or "",
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
