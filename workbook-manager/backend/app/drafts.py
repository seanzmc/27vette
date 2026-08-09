"""Durable Workbook Manager draft intent.

The disposable projection remains unchanged while a mutable draft records
original-to-final semantic row intent in the durable manager database. Exact
ChangeSet emission is durable and immutable; shared-service preview remains a
later Pass 5 layer.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from typing import Any

from corvette_form_generator import editor_ops
from corvette_form_generator.workbook_domain.changeset import (
    SCHEMA_VERSION as CHANGESET_SCHEMA_VERSION,
    changeset_fingerprint,
    parse_changeset,
)

from .catalog import SPEC_BY_TABLE, projection_value
from .staging import _editable_guard, _fetch_row


class DraftError(ValueError):
    """A draft request failed closed before durable intent was stored."""

    def __init__(self, code: str, message: str, *, errors: list[dict] | None = None):
        super().__init__(message)
        self.code = code
        self.errors = errors or []


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def _semantic_row(spec, row) -> dict[str, Any]:
    return {column.sql_name(): row[column.sql_name()] for column in spec.columns}


def _operation_dict(row) -> dict:
    result = dict(row)
    for source, target in (
        ("entity_key_json", "entity_key"),
        ("original_json", "original"),
        ("final_json", "final"),
        ("changed_fields_json", "changed_fields"),
        ("model_context_json", "model_context"),
    ):
        raw = result.pop(source, None)
        result[target] = json.loads(raw) if raw else None
    return result


def list_operations(state_conn: sqlite3.Connection, draft_id: str) -> list[dict]:
    rows = state_conn.execute(
        "SELECT * FROM draft_operations WHERE draft_id=? ORDER BY id", (draft_id,)
    ).fetchall()
    return [_operation_dict(row) for row in rows]


def _changeset_value(family: str, field: str, value: Any) -> Any:
    """Use the shared editor coercion for ChangeSet before/after values."""
    return editor_ops.coerce_value(family, field, value)


def emit_changeset(state_conn: sqlite3.Connection, *, draft_id: str) -> dict:
    """Commit a mutable draft as one exact immutable workbook-changeset-1."""
    draft = state_conn.execute(
        "SELECT * FROM workflow_drafts WHERE id=?", (draft_id,)
    ).fetchone()
    if draft is None:
        raise DraftError("draft_not_found", f"draft {draft_id!r} was not found")
    if draft["status"] != "draft":
        raise DraftError(
            "draft_not_mutable", f"draft {draft_id!r} is {draft['status']!r}, not mutable"
        )
    operations = list_operations(state_conn, draft_id)
    if not operations:
        raise DraftError("empty_draft", "a draft must contain an operation before commit")

    targets: set[str] = set()
    row_changes = []
    for operation in operations:
        spec = SPEC_BY_TABLE.get(operation["table_name"])
        if spec is None:
            raise DraftError(
                "unknown_table",
                f"stored draft operation references unknown table {operation['table_name']!r}",
            )
        if operation["action"] != "update":
            raise DraftError(
                "draft_action_not_implemented",
                "this Pass 5 checkpoint emits update operations only",
            )
        context = operation.get("model_context") or []
        targets.update(str(model) for model in context if str(model))
        if operation.get("model_id"):
            targets.add(str(operation["model_id"]))

        key = {}
        for name, value in (operation.get("entity_key") or {}).items():
            column = spec.column_by_name(name)
            if column is None:
                raise DraftError(
                    "unknown_fields",
                    f"stored draft key contains unregistered field {name!r}",
                )
            key[column.header] = _changeset_value(
                operation["family"], column.header, value
            )
        fields = {}
        for name, pair in (operation.get("changed_fields") or {}).items():
            column = spec.column_by_name(name)
            if column is None:
                raise DraftError(
                    "unknown_fields",
                    f"stored draft change contains unregistered field {name!r}",
                )
            fields[column.header] = {
                side: _changeset_value(operation["family"], column.header, pair[side])
                for side in ("before", "after")
            }
        row_changes.append({
            "action": operation["action"],
            "sheet": operation["source_sheet"],
            "family": operation["family"],
            "key": key,
            "fields": fields,
            "provenance": [{
                "kind": "workbook-manager-draft-operation",
                "id": str(operation["id"]),
            }],
        })

    if not targets:
        raise DraftError("draft_targets_empty", "draft operations resolve no model targets")
    payload = {
        "schemaVersion": CHANGESET_SCHEMA_VERSION,
        "source": {"kind": "workbook-manager", "runId": draft_id},
        "targets": sorted(targets),
        "workbook": {
            "sha256": draft["base_workbook_sha256"],
            "mtimeNs": draft["base_workbook_mtime_ns"],
        },
        "sheetCreates": [],
        "rowChanges": row_changes,
        "noops": [],
        "warningAcknowledgementsRequested": [],
        "bindings": {},
    }
    payload["semanticFingerprint"] = changeset_fingerprint(payload)
    payload["changeSetId"] = payload["semanticFingerprint"][:24]
    payload = parse_changeset(payload)

    timestamp = _now()
    state_conn.execute("BEGIN IMMEDIATE")
    try:
        current = state_conn.execute(
            "SELECT status FROM workflow_drafts WHERE id=?", (draft_id,)
        ).fetchone()
        if current is None or current["status"] != "draft":
            raise DraftError(
                "draft_not_mutable", f"draft {draft_id!r} is no longer mutable"
            )
        state_conn.execute(
            "INSERT INTO draft_changesets(draft_id, created_ts, change_set_id, "
            "semantic_fingerprint, payload_json) VALUES(?,?,?,?,?)",
            (
                draft_id,
                timestamp,
                payload["changeSetId"],
                payload["semanticFingerprint"],
                _json(payload),
            ),
        )
        state_conn.execute(
            "UPDATE workflow_drafts SET status='changeset_emitted', updated_ts=? "
            "WHERE id=?",
            (timestamp, draft_id),
        )
        state_conn.commit()
    except Exception:
        state_conn.rollback()
        raise
    return payload


def _ensure_mutable_draft(
    state_conn: sqlite3.Connection,
    *,
    draft_id: str,
    session_id: str,
    actor: str,
    base_workbook_sha256: str,
    base_workbook_mtime_ns: str,
    timestamp: str,
) -> None:
    if not draft_id or not base_workbook_sha256 or not base_workbook_mtime_ns:
        raise DraftError(
            "draft_identity_incomplete",
            "draft id and base workbook SHA-256/mtime are required",
        )
    row = state_conn.execute(
        "SELECT * FROM workflow_drafts WHERE id=?", (draft_id,)
    ).fetchone()
    if row is None:
        state_conn.execute(
            "INSERT INTO workflow_drafts(id, created_ts, updated_ts, session_id, "
            "actor, status, base_workbook_sha256, base_workbook_mtime_ns) "
            "VALUES(?,?,?,?,?,'draft',?,?)",
            (
                draft_id,
                timestamp,
                timestamp,
                session_id,
                actor,
                base_workbook_sha256,
                base_workbook_mtime_ns,
            ),
        )
        return
    if row["status"] != "draft":
        raise DraftError(
            "draft_not_mutable", f"draft {draft_id!r} is {row['status']!r}, not mutable"
        )
    if (
        row["base_workbook_sha256"] != base_workbook_sha256
        or row["base_workbook_mtime_ns"] != base_workbook_mtime_ns
    ):
        raise DraftError(
            "draft_binding_mismatch",
            "draft base workbook SHA-256/mtime does not match the existing draft",
        )
    state_conn.execute(
        "UPDATE workflow_drafts SET updated_ts=? WHERE id=?", (timestamp, draft_id)
    )


def save_operation(
    projection_conn: sqlite3.Connection,
    state_conn: sqlite3.Connection,
    *,
    projection_state: str,
    base_workbook_sha256: str,
    base_workbook_mtime_ns: str,
    draft_id: str,
    table: str,
    model_id: str,
    op: str,
    key: dict[str, str],
    record: dict[str, Any] | None,
    session_id: str = "",
    actor: str = "",
) -> dict | None:
    """Store one coalesced physical-row operation in a mutable draft.

    This first Pass 5 slice implements updates. Adds/deletes remain on the
    contained legacy UI until complete final-graph ChangeSet handling lands.
    """
    if projection_state != "current":
        raise DraftError(
            "projection_not_current",
            "draft authoring requires a current verified projection",
        )
    spec = SPEC_BY_TABLE.get(table)
    if spec is None:
        raise DraftError("unknown_table", f"unknown table {table!r}")
    if op != "update":
        raise DraftError(
            "draft_action_not_implemented",
            "this Pass 5 checkpoint accepts update drafts only",
        )
    row = _fetch_row(projection_conn, spec, model_id, key)
    if row is None:
        raise DraftError("record_not_found", "projected record was not found")

    original = _semantic_row(spec, row)
    supplied = record or {}
    unknown = sorted(set(supplied) - set(original))
    if unknown:
        raise DraftError(
            "unknown_fields", f"draft contains unregistered fields: {', '.join(unknown)}"
        )
    final = dict(original)
    for name, value in supplied.items():
        column = spec.column_by_name(name)
        if column is None:
            raise DraftError("unknown_fields", f"draft contains unregistered field {name!r}")
        final[name] = projection_value(column, value)
    changed_keys = [name for name in spec.key if final.get(name) != original.get(name)]
    if changed_keys:
        raise DraftError(
            "key_change_rejected",
            f"key fields cannot change on update: {', '.join(changed_keys)}",
        )
    ownership_errors = _editable_guard(
        projection_conn, spec, model_id, op=op, key=key, record=final
    )
    if ownership_errors:
        raise DraftError(
            "ownership_rejected", ownership_errors[0]["message"], errors=ownership_errors
        )

    source_sheet = str(row["src_sheet"] or "").strip()
    physical_key = str(row["physical_key"] or "").strip()
    if not source_sheet or not physical_key:
        raise DraftError(
            "physical_target_unresolved",
            "draft operation requires a resolved source sheet and physical key",
        )
    family = spec.editor_family or spec.family
    timestamp = _now()

    state_conn.execute("BEGIN IMMEDIATE")
    try:
        _ensure_mutable_draft(
            state_conn,
            draft_id=draft_id,
            session_id=session_id,
            actor=actor,
            base_workbook_sha256=base_workbook_sha256,
            base_workbook_mtime_ns=base_workbook_mtime_ns,
            timestamp=timestamp,
        )
        existing = state_conn.execute(
            "SELECT * FROM draft_operations WHERE draft_id=? AND source_sheet=? "
            "AND family=? AND physical_key=?",
            (draft_id, source_sheet, family, physical_key),
        ).fetchone()
        if existing is not None:
            prior = _operation_dict(existing)
            original = prior["original"]
            final = dict(prior["final"] or original)
            for name, value in supplied.items():
                column = spec.column_by_name(name)
                if column is None:  # guarded above; retain fail-closed locality
                    raise DraftError(
                        "unknown_fields", f"draft contains unregistered field {name!r}"
                    )
                final[name] = projection_value(column, value)

        changed_fields = {
            name: {"before": original.get(name), "after": final.get(name)}
            for name in original
            if original.get(name) != final.get(name)
        }
        if not changed_fields:
            if existing is not None:
                state_conn.execute(
                    "DELETE FROM draft_operations WHERE id=?", (existing["id"],)
                )
            state_conn.commit()
            return None
        values = (
            timestamp,
            table,
            family,
            model_id or "",
            source_sheet,
            row["src_row"],
            physical_key,
            _json(key),
            "update",
            _json(original),
            _json(final),
            _json(changed_fields),
            str(row["model_context"] or "[]"),
        )
        if existing is None:
            cursor = state_conn.execute(
                "INSERT INTO draft_operations(draft_id, created_ts, updated_ts, "
                "table_name, family, model_id, source_sheet, source_row, "
                "physical_key, entity_key_json, action, original_json, final_json, "
                "changed_fields_json, model_context_json) "
                "VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (draft_id, timestamp, *values),
            )
            operation_id = cursor.lastrowid
        else:
            state_conn.execute(
                "UPDATE draft_operations SET updated_ts=?, table_name=?, family=?, "
                "model_id=?, source_sheet=?, source_row=?, physical_key=?, "
                "entity_key_json=?, action=?, original_json=?, final_json=?, "
                "changed_fields_json=?, model_context_json=? WHERE id=?",
                (*values, existing["id"]),
            )
            operation_id = existing["id"]
        state_conn.commit()
    except Exception:
        state_conn.rollback()
        raise

    stored = state_conn.execute(
        "SELECT * FROM draft_operations WHERE id=?", (operation_id,)
    ).fetchone()
    return _operation_dict(stored)
