"""Durable Workbook Manager draft intent.

The disposable projection remains unchanged while a mutable draft records
original-to-final semantic row intent in the durable manager database. Exact
ChangeSet emission plus shared-service preview and approval attempts are durable
and immutable. Apply remains a later pass.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from corvette_form_generator import editor_ops
from corvette_form_generator.workbook_domain.changeset import (
    SCHEMA_VERSION as CHANGESET_SCHEMA_VERSION,
    changeset_fingerprint,
    parse_changeset,
)
from corvette_form_generator.workbook_domain import service as workbook_service

from .catalog import SPEC_BY_TABLE, projection_value
from .staging import _editable_guard, _fetch_row


class DraftError(ValueError):
    """A draft request failed closed before durable intent was stored."""

    def __init__(self, code: str, message: str, *, errors: list[dict] | None = None):
        super().__init__(message)
        self.code = code
        self.errors = errors or []


TRANSIENT_PREVIEW_EXCEPTIONS = (BlockingIOError, PermissionError, TimeoutError)


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


def _workbook_identity(path: Path, expected: dict) -> dict:
    """Measure workbook identity independently of the shared preview service."""
    try:
        observed = {
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "mtimeNs": str(path.stat().st_mtime_ns),
        }
    except OSError:
        return {"state": "unavailable", "sha256": "", "mtimeNs": ""}
    return {
        "state": "unchanged" if observed == expected else "mismatched",
        **observed,
    }


def _preview_attempt_dict(row) -> dict:
    result = dict(row)
    raw_result = result.pop("result_json")
    result["result"] = json.loads(raw_result) if raw_result else None
    result["allowed_verbs"] = json.loads(result.pop("allowed_verbs_json"))
    return result


def _map_preview_result(result: dict, identity_state: str) -> tuple[str, list[str]]:
    """Map one shared-service result through specification section 4.1."""
    if identity_state != "unchanged":
        return "stale", ["cancel"]
    status = result.get("status")
    if status == "validated" and result.get("ok") is True:
        return "preview_ready", ["approve", "cancel"]
    if status in {"locked", "readback_failed"}:
        return "preview_retryable", ["retry_preview", "cancel"]
    if status == "stale":
        return "stale", ["cancel"]
    return "preview_rejected", ["cancel"]


def _approval_attempt_dict(row) -> dict:
    result = dict(row)
    raw_result = result.pop("result_json")
    result["result"] = json.loads(raw_result) if raw_result else None
    result["warning_ids"] = json.loads(result.pop("warning_ids_json"))
    result["allowed_verbs"] = json.loads(result.pop("allowed_verbs_json"))
    return result


def _map_approval_result(result: dict) -> tuple[str, list[str]]:
    """Map one shared-service approval result through specification §4.1."""
    status = result.get("status")
    if (
        result.get("ok") is True
        and result.get("schemaVersion") == workbook_service.APPROVAL_SCHEMA
    ):
        return "approved", ["apply", "cancel"]
    if status == "warning_confirmation_mismatch":
        return "approval_confirmation_required", ["approve", "cancel"]
    return "approval_repreview_required", ["retry_preview", "cancel"]


def _persist_preview_attempt(
    state_conn: sqlite3.Connection,
    *,
    draft_id: str,
    changeset: dict,
    started: str,
    artifact_kind: str,
    result: dict | None,
    exception: BaseException | None,
    identity: dict,
    manager_state: str,
    allowed_verbs: list[str],
) -> dict:
    completed = _now()
    attempt_id = uuid.uuid4().hex
    state_conn.execute("BEGIN IMMEDIATE")
    try:
        state_conn.execute(
            "INSERT INTO draft_preview_attempts(id, draft_id, change_set_id, "
            "semantic_fingerprint, started_ts, completed_ts, artifact_kind, "
            "result_json, exception_class, exception_message, "
            "workbook_identity_state, observed_workbook_sha256, "
            "observed_workbook_mtime_ns, manager_state, allowed_verbs_json) "
            "VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                attempt_id,
                draft_id,
                changeset["changeSetId"],
                changeset["semanticFingerprint"],
                started,
                completed,
                artifact_kind,
                _json(result) if result is not None else None,
                type(exception).__name__ if exception is not None else "",
                str(exception) if exception is not None else "",
                identity["state"],
                identity["sha256"],
                identity["mtimeNs"],
                manager_state,
                _json(allowed_verbs),
            ),
        )
        state_conn.execute(
            "UPDATE workflow_drafts SET status=?, updated_ts=? WHERE id=?",
            (manager_state, completed, draft_id),
        )
        state_conn.commit()
    except Exception:
        state_conn.rollback()
        raise
    return _preview_attempt_dict(
        state_conn.execute(
            "SELECT * FROM draft_preview_attempts WHERE id=?", (attempt_id,)
        ).fetchone()
    )


def preview_draft(
    state_conn: sqlite3.Connection,
    *,
    draft_id: str,
    projection_state: str,
    workbook_path: Path,
) -> dict:
    """Preview one immutable draft ChangeSet through the shared service."""
    draft = state_conn.execute(
        "SELECT * FROM workflow_drafts WHERE id=?", (draft_id,)
    ).fetchone()
    if draft is None:
        raise DraftError("draft_not_found", f"draft {draft_id!r} was not found")
    if draft["status"] not in {
        "changeset_emitted",
        "preview_retryable",
        "approval_repreview_required",
    }:
        raise DraftError(
            "draft_not_previewable",
            f"draft {draft_id!r} is {draft['status']!r}, not previewable",
        )
    stored = state_conn.execute(
        "SELECT * FROM draft_changesets WHERE draft_id=?", (draft_id,)
    ).fetchone()
    if stored is None:
        raise DraftError(
            "changeset_not_found", f"draft {draft_id!r} has no emitted ChangeSet"
        )
    changeset = json.loads(stored["payload_json"])
    started = _now()
    if projection_state != "current":
        refusal = DraftError(
            "projection_not_current",
            "ChangeSet preview requires a current verified projection",
        )
        _persist_preview_attempt(
            state_conn,
            draft_id=draft_id,
            changeset=changeset,
            started=started,
            artifact_kind="manager_refusal",
            result=None,
            exception=refusal,
            identity=_workbook_identity(Path(workbook_path), changeset["workbook"]),
            manager_state="stale",
            allowed_verbs=["cancel"],
        )
        raise refusal
    try:
        result = workbook_service.preview_changeset(Path(workbook_path), changeset)
    except Exception as exc:
        identity = _workbook_identity(Path(workbook_path), changeset["workbook"])
        if identity["state"] != "unchanged":
            manager_state = "stale"
            allowed_verbs = ["cancel"]
        elif isinstance(exc, TRANSIENT_PREVIEW_EXCEPTIONS):
            manager_state = "preview_retryable"
            allowed_verbs = ["retry_preview", "cancel"]
        else:
            manager_state = "preview_rejected"
            allowed_verbs = ["cancel"]
        return _persist_preview_attempt(
            state_conn,
            draft_id=draft_id,
            changeset=changeset,
            started=started,
            artifact_kind="exception",
            result=None,
            exception=exc,
            identity=identity,
            manager_state=manager_state,
            allowed_verbs=allowed_verbs,
        )
    identity = _workbook_identity(Path(workbook_path), changeset["workbook"])
    manager_state, allowed_verbs = _map_preview_result(result, identity["state"])
    artifact_kind = (
        "formal_preview"
        if result.get("schemaVersion") == workbook_service.PREVIEW_SCHEMA
        else "early_refusal"
    )
    return _persist_preview_attempt(
        state_conn,
        draft_id=draft_id,
        changeset=changeset,
        started=started,
        artifact_kind=artifact_kind,
        result=result,
        exception=None,
        identity=identity,
        manager_state=manager_state,
        allowed_verbs=allowed_verbs,
    )


def _persist_approval_attempt(
    state_conn: sqlite3.Connection,
    *,
    draft_id: str,
    changeset: dict,
    preview_attempt,
    preview: dict,
    actor: str,
    warning_ids: list[str],
    started: str,
    artifact_kind: str,
    result: dict | None,
    exception: BaseException | None,
    manager_state: str,
    allowed_verbs: list[str],
) -> dict:
    completed = _now()
    attempt_id = uuid.uuid4().hex
    state_conn.execute("BEGIN IMMEDIATE")
    try:
        state_conn.execute(
            "INSERT INTO draft_approval_attempts(id, draft_id, preview_attempt_id, "
            "change_set_id, semantic_fingerprint, preview_fingerprint, actor, "
            "warning_ids_json, started_ts, completed_ts, artifact_kind, result_json, "
            "exception_class, exception_message, manager_state, allowed_verbs_json) "
            "VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                attempt_id,
                draft_id,
                preview_attempt["id"],
                changeset["changeSetId"],
                changeset["semanticFingerprint"],
                preview["previewFingerprint"],
                actor,
                _json(warning_ids),
                started,
                completed,
                artifact_kind,
                _json(result) if result is not None else None,
                type(exception).__name__ if exception is not None else "",
                str(exception) if exception is not None else "",
                manager_state,
                _json(allowed_verbs),
            ),
        )
        state_conn.execute(
            "UPDATE workflow_drafts SET status=?, updated_ts=? WHERE id=?",
            (manager_state, completed, draft_id),
        )
        state_conn.commit()
    except Exception:
        state_conn.rollback()
        raise
    return _approval_attempt_dict(
        state_conn.execute(
            "SELECT * FROM draft_approval_attempts WHERE id=?", (attempt_id,)
        ).fetchone()
    )


def approve_draft(
    state_conn: sqlite3.Connection,
    *,
    draft_id: str,
    projection_state: str,
    actor: str,
    warning_ids: list[str],
) -> dict:
    """Approve the exact stored ChangeSet/preview only through the shared service."""
    draft = state_conn.execute(
        "SELECT * FROM workflow_drafts WHERE id=?", (draft_id,)
    ).fetchone()
    if draft is None:
        raise DraftError("draft_not_found", f"draft {draft_id!r} was not found")
    if draft["status"] not in {"preview_ready", "approval_confirmation_required"}:
        raise DraftError(
            "draft_not_approvable",
            f"draft {draft_id!r} is {draft['status']!r}, not approvable",
        )
    stored_changeset = state_conn.execute(
        "SELECT * FROM draft_changesets WHERE draft_id=?", (draft_id,)
    ).fetchone()
    if stored_changeset is None:
        raise DraftError(
            "changeset_not_found", f"draft {draft_id!r} has no emitted ChangeSet"
        )
    preview_attempt = state_conn.execute(
        "SELECT * FROM draft_preview_attempts WHERE draft_id=? "
        "AND artifact_kind='formal_preview' AND manager_state='preview_ready' "
        "ORDER BY completed_ts DESC, rowid DESC LIMIT 1",
        (draft_id,),
    ).fetchone()
    if preview_attempt is None:
        raise DraftError(
            "preview_not_found",
            f"draft {draft_id!r} has no exact validated preview artifact",
        )
    changeset = json.loads(stored_changeset["payload_json"])
    preview = json.loads(preview_attempt["result_json"])
    accepted_warning_ids = [str(warning_id) for warning_id in warning_ids]
    started = _now()
    if projection_state != "current":
        refusal = DraftError(
            "projection_not_current",
            "ChangeSet approval requires a current verified projection",
        )
        _persist_approval_attempt(
            state_conn,
            draft_id=draft_id,
            changeset=changeset,
            preview_attempt=preview_attempt,
            preview=preview,
            actor=actor,
            warning_ids=accepted_warning_ids,
            started=started,
            artifact_kind="manager_refusal",
            result=None,
            exception=refusal,
            manager_state="stale",
            allowed_verbs=["cancel"],
        )
        raise refusal
    try:
        result = workbook_service.approve_changeset(
            changeset,
            preview,
            actor=actor,
            warning_ids=accepted_warning_ids,
        )
    except Exception as exc:
        return _persist_approval_attempt(
            state_conn,
            draft_id=draft_id,
            changeset=changeset,
            preview_attempt=preview_attempt,
            preview=preview,
            actor=actor,
            warning_ids=accepted_warning_ids,
            started=started,
            artifact_kind="exception",
            result=None,
            exception=exc,
            manager_state="approval_rejected",
            allowed_verbs=["cancel"],
        )
    manager_state, allowed_verbs = _map_approval_result(result)
    artifact_kind = (
        "formal_approval"
        if result.get("schemaVersion") == workbook_service.APPROVAL_SCHEMA
        else "early_refusal"
    )
    return _persist_approval_attempt(
        state_conn,
        draft_id=draft_id,
        changeset=changeset,
        preview_attempt=preview_attempt,
        preview=preview,
        actor=actor,
        warning_ids=accepted_warning_ids,
        started=started,
        artifact_kind=artifact_kind,
        result=result,
        exception=None,
        manager_state=manager_state,
        allowed_verbs=allowed_verbs,
    )


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
