"""Mapping-backed synchronization through the guarded workbook editor."""

from __future__ import annotations

import json
import hashlib
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from . import config, db as dbmod
from .catalog import ROLE_EDITOR_FAMILY, canonical_record, edit_spec
from .staging import target_sheet_for
from corvette_form_generator import editor_ops


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _now_slug() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _trusted_workbook_sha256(conn: sqlite3.Connection) -> str:
    trusted = dbmod.get_meta(conn, "trusted_workbook_sha256")
    if trusted:
        return trusted
    row = conn.execute(
        "SELECT workbook_sha256 FROM import_runs ORDER BY id DESC LIMIT 1"
    ).fetchone()
    return str(row["workbook_sha256"]) if row else ""


def _latest_import_sha256(conn: sqlite3.Connection) -> str:
    row = conn.execute(
        "SELECT workbook_sha256 FROM import_runs ORDER BY id DESC LIMIT 1"
    ).fetchone()
    return str(row["workbook_sha256"]) if row else ""


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
            "SELECT * FROM schema_mapping WHERE sql_table=? "
            "AND (model_key=? OR model_key IS NULL) "
            "AND source_sheet=? AND substr(source_column,1,2)<>'__' "
            "ORDER BY source_column, id",
            (history["sql_table"], history["model_key"], sheet),
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
    synced = conn.execute(
        "SELECT id, sync_detail FROM change_history "
        "WHERE src_sheet=? AND src_row=? AND status='sync_succeeded' "
        "ORDER BY id DESC LIMIT 1",
        (history["src_sheet"], history["src_row"]),
    ).fetchone()
    if synced is not None:
        try:
            detail = json.loads(synced["sync_detail"] or "{}")
        except json.JSONDecodeError as error:
            raise ValueError("malformed synchronized source evidence") from error
        source_values = detail.get("source_values")
        trusted = _trusted_workbook_sha256(conn)
        if isinstance(source_values, dict):
            reached = _sync_chain_reaches_trusted(
                conn, int(synced["id"]), detail, trusted
            )
            if reached:
                return dict(source_values)
            if trusted != _latest_import_sha256(conn):
                raise ValueError(
                    "synchronized source evidence has no unique unbroken "
                    "hash chain to the trusted workbook"
                )
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


def _canonical_history_record(spec, raw: str | None, *, required: bool) -> dict:
    try:
        value = json.loads(raw) if raw is not None else None
    except json.JSONDecodeError as error:
        raise ValueError("malformed persisted edit row") from error
    if value is None:
        if required:
            raise ValueError("pending edit has no complete canonical row")
        return {}
    if not isinstance(value, dict) or set(value) - set(spec.columns):
        raise ValueError("persisted edit row is not a canonical record")
    try:
        return canonical_record(spec, value)
    except ValueError as error:
        raise ValueError(f"invalid persisted edit row: {error}") from error


def _sync_chain_reaches_trusted(
    conn: sqlite3.Connection,
    source_event_id: int,
    source_detail: dict,
    trusted_sha256: str,
) -> bool:
    current = source_detail.get("new_workbook_sha256")
    if not isinstance(current, str) or not current:
        return False
    if current == trusted_sha256:
        return True
    transitions: dict[str, set[str]] = {}
    for row in conn.execute(
        "SELECT sync_detail FROM change_history "
        "WHERE status='sync_succeeded' AND id>? ORDER BY id",
        (source_event_id,),
    ):
        try:
            detail = json.loads(row["sync_detail"] or "{}")
        except json.JSONDecodeError as error:
            raise ValueError("malformed successful-sync hash chain") from error
        old_hash = detail.get("old_workbook_sha256")
        new_hash = detail.get("new_workbook_sha256")
        if not isinstance(old_hash, str) or not isinstance(new_hash, str):
            continue
        if old_hash and new_hash and old_hash != new_hash:
            transitions.setdefault(old_hash, set()).add(new_hash)
    visited = set()
    while current != trusted_sha256:
        if current in visited:
            raise ValueError("cycle in successful-sync hash chain")
        visited.add(current)
        destinations = transitions.get(current, set())
        if len(destinations) > 1:
            raise ValueError("fork in successful-sync hash chain")
        if not destinations:
            return False
        current = next(iter(destinations))
    return True


def _history_item(
    conn, history: dict, *, originals_override: dict | None = None
) -> dict:
    spec = edit_spec(conn, history["model_key"], history["table_role"])
    sheet = history["src_sheet"] or target_sheet_for(
        conn, history["model_key"], history["table_role"]
    )
    if not sheet:
        raise ValueError("target workbook sheet is ambiguous")
    mappings = _mapping_rows(conn, history, sheet)
    if not mappings:
        raise ValueError("no schema_mapping route for target workbook sheet")
    old = _canonical_history_record(
        spec, history["old_json"], required=False
    )
    new = _canonical_history_record(
        spec, history["new_json"], required=history["op"] != "delete"
    )
    old.setdefault("model_key", history["model_key"])
    new.setdefault("model_key", history["model_key"])
    originals = (
        dict(originals_override) if originals_override is not None
        else _original_source_values(conn, history)
    )
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
        item["_source_values"] = {
            **originals, **item["key"], **destination,
        }
    else:
        item["_source_values"] = {}
    return item


def _collapse_pending_add_chain(
    spec, chain: list[dict]
) -> tuple[dict | None, list[int]]:
    first = chain[0]
    if first["op"] != "add" or first["src_row"] is not None:
        raise ValueError("pending recovery chain does not start with an unsynced add")
    state = _canonical_history_record(spec, first["new_json"], required=True)
    deleted = False
    for history in chain[1:]:
        if deleted or history["op"] not in {"update", "delete"}:
            raise ValueError("invalid operation after pending add")
        old = _canonical_history_record(spec, history["old_json"], required=True)
        if old != state:
            raise ValueError("pending add recovery history is not contiguous")
        if history["op"] == "delete":
            if history["new_json"] is not None:
                raise ValueError("pending delete has unexpected new row")
            deleted = True
            state = None
        else:
            state = _canonical_history_record(
                spec, history["new_json"], required=True
            )
    history_ids = [int(history["id"]) for history in chain]
    if deleted:
        return None, history_ids
    synthetic = dict(first)
    synthetic["new_json"] = json.dumps(state)
    return synthetic, history_ids


def build_batch(conn, workbook_path: Path) -> dict:
    """Build a deterministic editor batch from unsynced append-only history."""
    items = []
    skipped = []
    current_source_values = {}
    histories = pending_history(conn)
    grouped = {}
    for history in histories:
        identity = (
            history["model_key"], history["table_role"],
            history["sql_table"], history["entity_id"],
        )
        grouped.setdefault(identity, []).append(history)
    processed = set()
    noop_history_ids = []
    noop_source_values = {}
    for history in histories:
        if history["id"] in processed:
            continue
        identity = (
            history["model_key"], history["table_role"],
            history["sql_table"], history["entity_id"],
        )
        history_ids = [int(history["id"])]
        try:
            if history["op"] == "add" and history["src_row"] is None:
                chain = grouped[identity]
                history_ids = [int(item["id"]) for item in chain]
                processed.update(history_ids)
                spec = edit_spec(
                    conn, history["model_key"], history["table_role"]
                )
                collapsed, history_ids = _collapse_pending_add_chain(spec, chain)
                if collapsed is None:
                    noop_history_ids.extend(history_ids)
                    noop_source_values.update({item: {} for item in history_ids})
                    continue
                history = collapsed
            else:
                processed.add(history["id"])
            lineage = (
                (history["src_sheet"], history["src_row"])
                if history["src_row"] is not None
                else (history["src_sheet"], f"history:{history['id']}")
            )
            item = _history_item(
                conn, history,
                originals_override=current_source_values.get(lineage),
            )
            current_source_values[lineage] = item["_source_values"]
            item["_history_ids"] = history_ids
            items.append(item)
        except (KeyError, ValueError) as error:
            skipped.append({"history_id": history["id"], "reason": str(error)})
    return {
        "workbookMtimeNs": str(Path(workbook_path).stat().st_mtime_ns),
        "items": [
            {key: value for key, value in item.items() if not key.startswith("_")}
            for item in items
        ],
        "historyIds": [
            history_id for item in items for history_id in item["_history_ids"]
        ] + noop_history_ids,
        "noopHistoryIds": noop_history_ids,
        "sourceValuesByHistoryId": {
            history_id: item["_source_values"]
            for item in items for history_id in item["_history_ids"]
        } | noop_source_values,
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
    workbook_path = Path(workbook_path)
    trusted_sha256 = _trusted_workbook_sha256(conn)
    current_sha256 = _file_sha256(workbook_path)
    if not trusted_sha256 or current_sha256 != trusted_sha256:
        return {
            "ok": False,
            "status": "stale_source",
            "errors": [
                "workbook content does not match the trusted synchronization base"
            ],
            "trustedWorkbookSha256": trusted_sha256,
            "workbookSha256": current_sha256,
            "skipped": [],
        }
    batch = build_batch(conn, workbook_path)
    if batch["skipped"]:
        return {
            "ok": False,
            "status": "unreversible",
            "errors": [item["reason"] for item in batch["skipped"]],
            "skipped": batch["skipped"],
        }
    if not batch["historyIds"]:
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
    # Close the check/use window as far as practical before the guarded editor.
    pre_editor_sha256 = _file_sha256(workbook_path)
    if pre_editor_sha256 != trusted_sha256:
        return {
            "ok": False, "status": "stale_source",
            "errors": ["workbook changed after synchronization preflight"],
            "trustedWorkbookSha256": trusted_sha256,
            "workbookSha256": pre_editor_sha256,
            "skipped": [],
        }
    if batch["items"]:
        result = dict(editor_ops.apply_batch(
            Path(workbook_path),
            {"workbookMtimeNs": batch["workbookMtimeNs"], "items": batch["items"]},
            write=write,
            confirmed_warnings=confirmed_warnings,
            source="workbook-manager",
            log_path=config.EDIT_LOG_PATH if write else None,
        ))
    else:
        result = {
            "ok": True,
            "status": "applied_noop" if write else "validated",
            "backupPath": "",
        }
    result.update(
        skipped=[], workbookMtimeNs=batch["workbookMtimeNs"],
        workbookSha256=pre_editor_sha256, opCount=len(batch["items"]),
    )
    if write:
        post_editor_sha256 = _file_sha256(workbook_path)
        detail = {
            "status": result.get("status"),
            "errors": result.get("errors", []),
            "backup": str(result.get("backupPath", "")),
            "old_workbook_sha256": trusted_sha256,
            "new_workbook_sha256": post_editor_sha256,
        }
        for history_id in batch["historyIds"]:
            event_detail = dict(detail)
            if result.get("ok"):
                event_detail["source_values"] = batch[
                    "sourceValuesByHistoryId"
                ][history_id]
            _append_sync_event(
                conn, history_id, success=bool(result.get("ok")),
                detail=event_detail,
            )
        if result.get("ok"):
            dbmod.set_meta(
                conn, "trusted_workbook_sha256", post_editor_sha256
            )
            result["workbookSha256"] = post_editor_sha256
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
