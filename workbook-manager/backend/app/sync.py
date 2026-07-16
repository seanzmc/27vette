"""Mapping-backed synchronization through the guarded workbook editor."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from . import config
from .catalog import ROLE_EDITOR_FAMILY, edit_spec
from .staging import target_sheet_for
from corvette_form_generator import editor_ops


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _now_slug() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")


def pending_history(conn) -> list[dict]:
    rows = conn.execute(
        "SELECT h.* FROM change_history h "
        "WHERE h.status='committed' AND h.sync_status='pending' "
        "AND NOT EXISTS (SELECT 1 FROM change_history event "
        "WHERE event.related_history_id=h.id "
        "AND event.status='sync_succeeded') ORDER BY h.id"
    ).fetchall()
    return [dict(row) for row in rows]


def _mapping_rows(conn, history: dict, sheet: str) -> tuple[dict, ...]:
    return tuple(
        dict(row)
        for row in conn.execute(
            "SELECT * FROM schema_mapping WHERE model_key=? AND sql_table=? "
            "AND source_sheet=? AND substr(source_column,1,2)<>'__' "
            "ORDER BY source_column, id",
            (history["model_key"], history["sql_table"], sheet),
        )
    )


def _reverse_value(source_column: str, mappings: list[dict], record: dict):
    values = [record.get(mapping["sql_column"]) for mapping in mappings]
    transforms = {
        json.loads(mapping["transform_parameters_json"] or "{}").get(
            "reverse_transform", "identity"
        )
        for mapping in mappings
    }
    if len(transforms) != 1:
        raise ValueError(f"conflicting reverse transforms for {source_column}")
    reverse = transforms.pop()
    non_null = [value for value in values if value is not None]
    if len(set(map(str, non_null))) > 1:
        raise ValueError(f"contradictory canonical values for {source_column}")
    current = non_null[0] if non_null else None
    if reverse == "restore_target_type_option":
        return "option"
    if reverse == "restore_target_type_context_choice":
        return "context_choice"
    if reverse == "restore_original_boolean_from_lineage":
        return bool(current) if current is not None else ""
    if reverse == "restore_scope_active_flag":
        return bool(current) if current is not None else ""
    if reverse in {
        "restore_original_number_from_lineage",
        "restore_original_text_from_lineage",
        "restore_original_scope_from_lineage",
        "coalesce_typed_entity_reference_then_restore_original_text_from_lineage",
        "identity",
        "restore_source_header",
        "restore_exact_model_owner",
    }:
        return "" if current is None else current
    raise ValueError(
        f"unreversible mapping for {source_column}: {reverse}"
    )


def _workbook_record(
    spec, mappings: tuple[dict, ...], record: dict, *,
    originals: dict | None = None, baseline: dict | None = None,
) -> dict:
    grouped: dict[str, list[dict]] = {}
    for mapping in mappings:
        grouped.setdefault(mapping["source_column"], []).append(mapping)
    output = {}
    for source_column, rows in grouped.items():
        unchanged = baseline is not None and all(
            record.get(row["sql_column"]) == baseline.get(row["sql_column"])
            for row in rows
        )
        if unchanged and originals is not None and source_column in originals:
            value = originals[source_column]
        else:
            value = _reverse_value(source_column, rows, record)
        if any(row["sql_column"] in spec.booleans for row in rows) and value != "":
            value = bool(value)
        output[source_column] = value
    return output


def _original_source_values(conn, history: dict) -> dict:
    if not history["src_sheet"] or history["src_row"] is None:
        return {}
    row = conn.execute(
        "SELECT evidence_json FROM source_row_disposition "
        "WHERE source_sheet=? AND source_row=? AND disposition='emitted' "
        "ORDER BY import_run_id DESC LIMIT 1",
        (history["src_sheet"], history["src_row"]),
    ).fetchone()
    if row is None:
        return {}
    evidence = json.loads(row["evidence_json"] or "{}")
    return dict(evidence.get("source_values") or {})


def _history_item(conn, history: dict) -> dict:
    spec = edit_spec(conn, history["model_key"], history["table_role"])
    sheet = history["src_sheet"] or target_sheet_for(
        conn, history["model_key"], history["table_role"]
    )
    if not sheet:
        raise ValueError("target workbook sheet is ambiguous")
    mappings = _mapping_rows(conn, history, sheet)
    if not mappings:
        raise ValueError("no schema_mapping route for target workbook sheet")
    old = json.loads(history["old_json"]) if history["old_json"] else {}
    new = json.loads(history["new_json"]) if history["new_json"] else {}
    old.setdefault("model_key", history["model_key"])
    new.setdefault("model_key", history["model_key"])
    originals = _original_source_values(conn, history)
    source = old if history["op"] != "add" else new
    source_record = _workbook_record(
        spec, mappings, source, originals=originals,
        baseline=old if history["op"] != "add" else None,
    )
    family = ROLE_EDITOR_FAMILY[history["table_role"]]
    key_columns = editor_ops.EDITOR_SHEET_META[family]["key"]
    missing = [column for column in key_columns if column not in source_record]
    if missing:
        raise ValueError(f"schema_mapping does not reconstruct key fields {missing}")
    item = {
        "action": history["op"],
        "sheet": sheet,
        "key": {column: source_record[column] for column in key_columns},
        "_history_id": history["id"],
    }
    if history["op"] in {"add", "update"}:
        destination = _workbook_record(
            spec, mappings, new, originals=originals,
            baseline=old if history["op"] == "update" else None,
        )
        if history["op"] == "update":
            destination = {
                column: value for column, value in destination.items()
                if column not in key_columns
            }
        item["row"] = destination
    return item


def build_batch(conn, workbook_path: Path) -> dict:
    """Build a deterministic editor batch from unsynced append-only history."""
    items = []
    skipped = []
    for history in pending_history(conn):
        try:
            items.append(_history_item(conn, history))
        except (KeyError, ValueError) as error:
            skipped.append({"history_id": history["id"], "reason": str(error)})
    return {
        "workbookMtimeNs": str(Path(workbook_path).stat().st_mtime_ns),
        "items": [
            {key: value for key, value in item.items() if not key.startswith("_")}
            for item in items
        ],
        "historyIds": [item["_history_id"] for item in items],
        "skipped": skipped,
    }


def _append_sync_event(conn, history_id: int, *, success: bool, detail: dict):
    source = conn.execute(
        "SELECT * FROM change_history WHERE id=?", (history_id,)
    ).fetchone()
    if source is None:
        raise RuntimeError(f"history row {history_id} disappeared")
    status = "sync_succeeded" if success else "sync_failed"
    conn.execute(
        "INSERT INTO change_history("
        "ts, actor, model_key, table_role, sql_table, entity_id, op, old_json, "
        "new_json, src_sheet, src_row, validation_result, status, sync_status, "
        "sync_detail, related_history_id) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (
            _now(), "workbook-sync", source["model_key"], source["table_role"],
            source["sql_table"], source["entity_id"], source["op"],
            source["old_json"], source["new_json"], source["src_sheet"],
            source["src_row"], source["validation_result"], status,
            "synced" if success else "sync_failed",
            json.dumps(detail, sort_keys=True), history_id,
        ),
    )


def sync_workbook(
    conn: sqlite3.Connection,
    workbook_path: Path,
    *,
    write: bool = False,
    confirmed_warnings=(),
    expected_mtime_ns: str | None = None,
) -> dict:
    batch = build_batch(conn, workbook_path)
    if batch["skipped"]:
        return {
            "ok": False,
            "status": "unreversible",
            "errors": [item["reason"] for item in batch["skipped"]],
            "skipped": batch["skipped"],
        }
    if not batch["items"]:
        return {
            "ok": False, "status": "empty",
            "errors": ["no committed changes are pending synchronization"],
            "skipped": [],
        }
    if write and expected_mtime_ns is None:
        return {
            "ok": False, "status": "confirmation_required",
            "errors": ["live sync requires the reviewed dry-run mtime"],
            "skipped": [],
        }
    if write and str(expected_mtime_ns) != batch["workbookMtimeNs"]:
        return {
            "ok": False, "status": "stale",
            "errors": ["workbook changed since the reviewed dry-run"],
            "skipped": [],
        }
    result = dict(editor_ops.apply_batch(
        Path(workbook_path),
        {"workbookMtimeNs": batch["workbookMtimeNs"], "items": batch["items"]},
        write=write,
        confirmed_warnings=confirmed_warnings,
        source="workbook-manager",
        log_path=config.EDIT_LOG_PATH if write else None,
    ))
    result.update(
        skipped=[], workbookMtimeNs=batch["workbookMtimeNs"],
        opCount=len(batch["items"]),
    )
    if write:
        detail = {
            "status": result.get("status"),
            "errors": result.get("errors", []),
            "backup": str(result.get("backupPath", "")),
        }
        for history_id in batch["historyIds"]:
            _append_sync_event(
                conn, history_id, success=bool(result.get("ok")), detail=detail
            )
        conn.commit()
    return result


def export_comparison_workbook(conn: sqlite3.Connection, workbook_path: Path) -> dict:
    """Delegate comparison export to the audited canonical reverse adapter."""
    from .export_adapter import export_comparison_workbook as export_adapter

    config.ensure_dirs()
    destination = config.EXPORT_DIR / f"regenerated-{_now_slug()}.xlsx"
    path = export_adapter(conn, Path(workbook_path), destination)
    return {"ok": True, "path": str(path)}


def backup_database(conn: sqlite3.Connection, db_path: Path) -> dict:
    config.ensure_dirs()
    out = config.DB_BACKUP_DIR / f"workbook-manager-{_now_slug()}.sqlite3"
    destination = sqlite3.connect(out)
    try:
        conn.backup(destination)
    finally:
        destination.close()
    return {"ok": True, "path": str(out)}
