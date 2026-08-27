"""Durable Workbook Manager draft intent.

The disposable projection remains unchanged while a mutable draft records
original-to-final semantic row intent in the durable manager database. Exact
ChangeSet emission plus shared-service preview, approval, and apply attempts are
durable and immutable. Apply remains backend-only until the separately owned
API/browser enablement pass.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from corvette_form_generator import editor_ops
from corvette_form_generator.contract import WILDCARD_MODEL_KEY
from corvette_form_generator.workbook_domain.changeset import (
    SCHEMA_VERSION as CHANGESET_SCHEMA_VERSION,
    changeset_fingerprint,
    parse_changeset,
)
from corvette_form_generator.workbook_domain import service as workbook_service

from .catalog import SPEC_BY_TABLE, projection_value
from .staging import _editable_guard, _fetch_row, target_sheet_for


class DraftError(ValueError):
    """A draft request failed closed before durable intent was stored."""

    def __init__(self, code: str, message: str, *, errors: list[dict] | None = None):
        super().__init__(message)
        self.code = code
        self.errors = errors or []


TRANSIENT_PREVIEW_EXCEPTIONS = (BlockingIOError, PermissionError, TimeoutError)
TRANSIENT_APPLY_EXCEPTIONS = (BlockingIOError, PermissionError, TimeoutError)


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


def connected_addition(
    state_conn: sqlite3.Connection,
    *,
    draft_id: str,
    table: str,
    model_key: str,
    entity_key: dict,
) -> dict | None:
    if not draft_id:
        return None
    draft = state_conn.execute(
        "SELECT id FROM workflow_drafts WHERE id=?", (draft_id,)
    ).fetchone()
    if draft is None:
        return None
    rows = state_conn.execute(
        "SELECT * FROM draft_operations WHERE draft_id=? AND table_name=? "
        "AND action='add' AND (model_id='' OR model_id=?) ORDER BY id DESC",
        (draft_id, table, model_key),
    ).fetchall()
    return next((
        operation for operation in map(_operation_dict, rows)
        if operation.get("entity_key") == entity_key
    ), None)


def connected_overlay(
    state_conn: sqlite3.Connection,
    *,
    draft_id: str,
    model_key: str,
    lineage: dict,
    base: dict,
    projection_workbook_sha256: str,
) -> dict:
    """Return one projection-preserving overlay for a connected entity."""
    empty = {
        "draft_id": draft_id,
        "draft_revision": 0,
        "state": "unchanged",
        "base": None,
        "proposed": None,
        "effective": None,
        "conflicts": [],
    }
    if not draft_id:
        return empty
    draft = state_conn.execute(
        "SELECT * FROM workflow_drafts WHERE id=?", (draft_id,)
    ).fetchone()
    if draft is None:
        return empty
    operation_row = state_conn.execute(
        "SELECT * FROM draft_operations WHERE draft_id=? AND source_sheet=? "
        "AND family=? AND physical_key=? AND (model_id='' OR model_id=?) "
        "ORDER BY id DESC LIMIT 1",
        (
            draft_id,
            lineage.get("source_sheet"),
            lineage.get("source_family"),
            lineage.get("physical_key"),
            model_key,
        ),
    ).fetchone()
    if operation_row is None:
        return empty
    operation = _operation_dict(operation_row)
    operation_base = (
        operation.get("original")
        if operation["action"] == "add"
        else operation.get("original") or base
    )
    if draft["base_workbook_sha256"] != projection_workbook_sha256:
        return {
            "draft_id": draft_id,
            "draft_revision": int(operation["id"]),
            "state": "conflicted",
            "base": operation_base,
            "proposed": operation.get("final"),
            "effective": None,
            "conflicts": [{
                "code": "draft_binding_stale",
                "message": "The draft is bound to a different workbook import.",
            }],
        }
    state = {
        "update": "modified",
        "add": "added",
        "delete": "pending_deletion",
    }[operation["action"]]
    proposed = operation.get("final")
    return {
        "draft_id": draft_id,
        "draft_revision": int(operation["id"]),
        "state": state,
        "base": operation_base,
        "proposed": proposed,
        "effective": proposed if state != "pending_deletion" else None,
        "conflicts": [],
    }


def _asset_resolution_dict(row) -> dict:
    result = dict(row)
    result["evidence"] = json.loads(result.pop("evidence_json"))
    return result


def list_asset_resolutions(
    state_conn: sqlite3.Connection, draft_id: str
) -> list[dict]:
    rows = state_conn.execute(
        "SELECT * FROM draft_asset_resolutions WHERE draft_id=? ORDER BY id",
        (draft_id,),
    ).fetchall()
    return [_asset_resolution_dict(row) for row in rows]


def active_asset_ignores(
    state_conn: sqlite3.Connection,
    *,
    fingerprints: dict[str, str],
) -> set[str]:
    """Return ignore identities that still bind the current media snapshot."""

    rows = state_conn.execute(
        "SELECT r.* FROM draft_asset_resolutions r "
        "JOIN workflow_drafts d ON d.id=r.draft_id "
        "WHERE r.resolution_kind='ignore' AND d.status!='cancelled'"
    ).fetchall()
    return {
        row["item_id"]
        for row in rows
        if row["reconciliation_sha256"] == fingerprints.get("reconciliation_sha256")
        and row["media_inventory_sha256"] == fingerprints.get("media_inventory_sha256")
        and row["workbook_sha256"] == fingerprints.get("workbook_sha256")
    }


def assert_asset_resolutions_current(
    state_conn: sqlite3.Connection,
    *,
    draft_id: str,
    snapshot,
) -> None:
    """Fail closed when reviewed asset evidence no longer matches draft or inventory."""

    evidence_rows = list_asset_resolutions(state_conn, draft_id)
    if not evidence_rows:
        return
    current_items = {item["id"]: item for item in snapshot.items}
    current_fingerprints = snapshot.fingerprints
    errors: list[dict] = []
    for row in evidence_rows:
        evidence = row["evidence"]
        if any(
            row[field] != current_fingerprints.get(field)
            for field in (
                "reconciliation_sha256",
                "media_inventory_sha256",
                "workbook_sha256",
            )
        ):
            errors.append({
                "item_id": row["item_id"],
                "message": "asset reconciliation evidence is stale; refresh and resolve again",
            })
            continue
        item = current_items.get(row["item_id"])
        if item is None:
            errors.append({
                "item_id": row["item_id"],
                "message": "asset reconciliation item no longer exists",
            })
            continue
        if row["resolution_kind"] == "ignore":
            if row["media_url"] not in snapshot.media_urls:
                errors.append({
                    "item_id": row["item_id"],
                    "message": "ignored media identity no longer exists in this inventory",
                })
            continue
        operation = state_conn.execute(
            "SELECT * FROM draft_operations WHERE id=? AND draft_id=?",
            (row["operation_id"], draft_id),
        ).fetchone()
        if operation is None:
            errors.append({
                "item_id": row["item_id"],
                "message": "asset evidence no longer has its bound draft operation",
            })
            continue
        final = json.loads(operation["final_json"]) if operation["final_json"] else None
        expected_final = evidence.get("final_values")
        if expected_final is not None and any(
            (final or {}).get(field) != value for field, value in expected_final.items()
        ):
            errors.append({
                "item_id": row["item_id"],
                "message": "asset draft values changed after the reviewed resolution",
            })
    if errors:
        raise DraftError(
            "asset_reconciliation_stale",
            "asset evidence is stale; return to Asset Manager before freezing the ChangeSet",
            errors=errors,
        )


def list_drafts(state_conn: sqlite3.Connection, *, limit: int = 50) -> list[dict]:
    """Return durable draft identities for browser recovery and selection."""
    rows = state_conn.execute(
        "SELECT d.*, COUNT(o.id) AS operation_count "
        "FROM workflow_drafts d LEFT JOIN draft_operations o ON o.draft_id=d.id "
        "GROUP BY d.id ORDER BY d.updated_ts DESC, d.id DESC LIMIT ?",
        (limit,),
    ).fetchall()
    return [dict(row) for row in rows]


def lifecycle_view(state_conn: sqlite3.Connection, draft_id: str) -> dict:
    """Return one manager-owned view over exact stored lifecycle evidence."""
    draft_row = state_conn.execute(
        "SELECT * FROM workflow_drafts WHERE id=?", (draft_id,)
    ).fetchone()
    if draft_row is None:
        raise DraftError("draft_not_found", f"draft {draft_id!r} was not found")

    operations = list_operations(state_conn, draft_id)
    asset_resolutions = list_asset_resolutions(state_conn, draft_id)
    by_operation: dict[int, list[dict]] = {}
    for resolution in asset_resolutions:
        if resolution.get("operation_id") is not None:
            by_operation.setdefault(int(resolution["operation_id"]), []).append(resolution)
    for operation in operations:
        operation["asset_resolutions"] = by_operation.get(int(operation["id"]), [])
    model_keys = {
        str(model_key)
        for operation in operations
        for model_key in (
            [operation.get("model_id")] + (operation.get("model_context") or [])
        )
        if str(model_key or "")
    }
    physical_targets = [
        {
            "operation_id": operation["id"],
            "table": operation["table_name"],
            "family": operation["family"],
            "source_sheet": operation["source_sheet"],
            "source_row": operation["source_row"],
            "physical_key": operation["physical_key"],
            "entity_key": operation["entity_key"],
            "model_context": operation.get("model_context") or [],
        }
        for operation in operations
    ]

    changeset_row = state_conn.execute(
        "SELECT * FROM draft_changesets WHERE draft_id=?", (draft_id,)
    ).fetchone()
    changeset = None
    if changeset_row is not None:
        changeset = dict(changeset_row)
        changeset["artifact"] = json.loads(changeset.pop("payload_json"))

    preview_attempts = [
        _preview_attempt_dict(row)
        for row in state_conn.execute(
            "SELECT * FROM draft_preview_attempts WHERE draft_id=? "
            "ORDER BY started_ts, rowid",
            (draft_id,),
        ).fetchall()
    ]
    approval_attempts = [
        _approval_attempt_dict(row)
        for row in state_conn.execute(
            "SELECT * FROM draft_approval_attempts WHERE draft_id=? "
            "ORDER BY started_ts, rowid",
            (draft_id,),
        ).fetchall()
    ]
    apply_attempts = [
        _apply_attempt_dict(row)
        for row in state_conn.execute(
            "SELECT * FROM draft_apply_attempts WHERE draft_id=? "
            "ORDER BY started_ts, rowid",
            (draft_id,),
        ).fetchall()
    ]
    manual_resolutions = [
        _manual_resolution_dict(row)
        for row in state_conn.execute(
            "SELECT * FROM draft_manual_resolutions WHERE draft_id=? "
            "ORDER BY created_ts, rowid",
            (draft_id,),
        ).fetchall()
    ]
    draft = dict(draft_row)
    cancellation = (
        {
            "status": draft["status"],
            "updated_ts": draft["updated_ts"],
        }
        if draft["status"] == "cancelled"
        else None
    )
    return {
        "draft": draft,
        "context": {
            "model_keys": sorted(model_keys),
            "physical_targets": physical_targets,
        },
        "operations": operations,
        "artifacts": {
            "changeset": changeset,
            "preview_attempts": preview_attempts,
            "approval_attempts": approval_attempts,
            "apply_attempts": apply_attempts,
            "cancellation": cancellation,
            "manual_resolutions": manual_resolutions,
            "asset_resolutions": asset_resolutions,
        },
    }


def _changeset_value(family: str, field: str, value: Any) -> Any:
    """Use the shared editor coercion for ChangeSet before/after values."""
    if value is None:
        return None
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
        context = operation.get("model_context") or []
        targets.update(str(model) for model in context if str(model))
        if operation.get("model_id") and operation["model_id"] != WILDCARD_MODEL_KEY:
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
        blocking = (result.get("warningPolicy") or {}).get("blockingIds") or []
        if blocking:
            return "preview_rejected", ["cancel"]
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
    if status in {"preview_not_validated", "binding_mismatch", "warning_blocked"}:
        return "approval_repreview_required", ["retry_preview", "cancel"]
    return "approval_rejected", ["cancel"]


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
        "AND change_set_id=? AND semantic_fingerprint=? "
        "AND artifact_kind='formal_preview' AND manager_state='preview_ready' "
        "ORDER BY completed_ts DESC, rowid DESC LIMIT 1",
        (
            draft_id,
            stored_changeset["change_set_id"],
            stored_changeset["semantic_fingerprint"],
        ),
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


def _apply_attempt_dict(row) -> dict:
    result = dict(row)
    raw_result = result.pop("result_json")
    result["result"] = json.loads(raw_result) if raw_result else None
    result["allowed_verbs"] = json.loads(result.pop("allowed_verbs_json"))
    return result


def _manual_resolution_dict(row) -> dict:
    result = dict(row)
    result["evidence"] = json.loads(result.pop("evidence_json"))
    return result


def _map_apply_result(
    result: dict, *, identity_state: str, exact_formal_receipt: bool = False
) -> tuple[str, list[str]]:
    """Map one shared-service apply result through specification section 4.1."""
    status = result.get("status")
    workbook_state = result.get("workbookState")
    if status in {"stale", "stale_before_save"} and workbook_state == "untouched":
        return "stale", ["cancel"]
    if status == "workbook_restore_failed" or workbook_state == "unknown":
        return "workbook_state_unknown", ["resolve_manually"]
    if workbook_state == "restored":
        if (
            status in {
                "apply_verification_failed_rolled_back",
                "apply_rebuild_failed_rolled_back",
            }
            and identity_state == "unchanged"
            and exact_formal_receipt
        ):
            return "apply_restored_retryable", ["retry_apply", "cancel"]
        return "workbook_state_unknown", ["resolve_manually"]
    if workbook_state != "untouched" or identity_state != "unchanged":
        return "workbook_state_unknown", ["resolve_manually"]
    if status == "locked":
        return "apply_retryable", ["retry_apply", "cancel"]
    if status in {"warning_confirmation_mismatch", "needs_confirmation"}:
        return "approval_confirmation_required", ["approve", "cancel"]
    if status in {"approval_invalid", "binding_mismatch", "warning_blocked"}:
        return "approval_repreview_required", ["retry_preview", "cancel"]
    if status in {
        "invalid",
        "empty",
        "schema_validation_required",
        "readback_failed",
        "bool_hygiene_failed",
        "schema_failed",
    }:
        return "apply_rejected", ["cancel"]
    return "workbook_state_unknown", ["resolve_manually"]


def _is_exact_formal_receipt(
    result: dict, changeset: dict, preview: dict, approval: dict
) -> bool:
    """Require the complete shared receipt shape and exact artifact identities."""
    required_keys = {
        "ok",
        "schemaVersion",
        "changeSetId",
        "semanticFingerprint",
        "previewFingerprint",
        "approvalFingerprint",
        "status",
        "workbookState",
        "errors",
        "warnings",
        "backupPath",
        "logPath",
        "operationCoverage",
        "verification",
        "schemaResult",
        "boolHygieneResult",
        "gateReminders",
        "createdAt",
    }
    return (
        required_keys.issubset(result)
        and isinstance(result.get("ok"), bool)
        and result.get("schemaVersion") == workbook_service.RECEIPT_SCHEMA
        and isinstance(result.get("status"), str)
        and result.get("workbookState")
        in {"saved", "restored", "untouched", "unknown"}
        and isinstance(result.get("errors"), list)
        and isinstance(result.get("warnings"), list)
        and result.get("changeSetId") == changeset.get("changeSetId")
        and result.get("semanticFingerprint")
        == changeset.get("semanticFingerprint")
        and result.get("previewFingerprint") == preview.get("previewFingerprint")
        and result.get("approvalFingerprint")
        == approval.get("approvalFingerprint")
    )


def _is_exact_applied_receipt(
    result: dict, changeset: dict, preview: dict, approval: dict
) -> bool:
    """Verify a complete, exactly bound saved receipt and its write proofs."""
    coverage = result.get("operationCoverage") or {}
    verification = result.get("verification") or {}
    schema_result = result.get("schemaResult") or {}
    bool_result = result.get("boolHygieneResult") or {}
    counts = (
        coverage.get("rawCount"),
        coverage.get("rawCovered"),
        coverage.get("preparedCount"),
        verification.get("preparedChecked"),
        verification.get("preparedCount"),
    )
    return (
        _is_exact_formal_receipt(result, changeset, preview, approval)
        and result.get("ok") is True
        and result.get("status") == "applied"
        and result.get("workbookState") == "saved"
        and all(type(value) is int and value > 0 for value in counts)
        and coverage.get("rawCount") == coverage.get("rawCovered")
        and coverage.get("preparedCount") == verification.get("preparedCount")
        and verification.get("ok") is True
        and verification.get("preparedChecked") == verification.get("preparedCount")
        and schema_result.get("status") == "valid"
        and schema_result.get("error_count") == 0
        and bool_result.get("status") == "valid"
        and bool_result.get("error_count") == 0
    )


def _latest_apply_artifacts(state_conn: sqlite3.Connection, draft_id: str):
    stored_changeset = state_conn.execute(
        "SELECT * FROM draft_changesets WHERE draft_id=?", (draft_id,)
    ).fetchone()
    if stored_changeset is None:
        raise DraftError(
            "changeset_not_found", f"draft {draft_id!r} has no emitted ChangeSet"
        )
    approval_attempt = state_conn.execute(
        "SELECT * FROM draft_approval_attempts WHERE draft_id=? "
        "AND change_set_id=? AND semantic_fingerprint=? "
        "AND artifact_kind='formal_approval' AND manager_state='approved' "
        "ORDER BY completed_ts DESC, rowid DESC LIMIT 1",
        (
            draft_id,
            stored_changeset["change_set_id"],
            stored_changeset["semantic_fingerprint"],
        ),
    ).fetchone()
    if approval_attempt is None:
        raise DraftError(
            "approval_not_found",
            f"draft {draft_id!r} has no exact approved artifact",
        )
    preview_attempt = state_conn.execute(
        "SELECT * FROM draft_preview_attempts WHERE id=? "
        "AND draft_id=? AND change_set_id=? AND semantic_fingerprint=? "
        "AND artifact_kind='formal_preview' AND manager_state='preview_ready'",
        (
            approval_attempt["preview_attempt_id"],
            draft_id,
            stored_changeset["change_set_id"],
            stored_changeset["semantic_fingerprint"],
        ),
    ).fetchone()
    if preview_attempt is None:
        raise DraftError(
            "preview_not_found", f"draft {draft_id!r} has no exact preview artifact"
        )
    changeset = json.loads(stored_changeset["payload_json"])
    preview = json.loads(preview_attempt["result_json"])
    approval = json.loads(approval_attempt["result_json"])
    if approval_attempt["preview_fingerprint"] != preview.get("previewFingerprint"):
        raise DraftError(
            "artifact_binding_mismatch",
            "stored preview and approval identities do not bind exactly",
        )
    return changeset, preview_attempt, preview, approval_attempt, approval


def _begin_apply_attempt(
    state_conn: sqlite3.Connection,
    *,
    draft_id: str,
    changeset: dict,
    preview_attempt,
    preview: dict,
    approval_attempt,
    approval: dict,
) -> str:
    """Commit durable applying state before any call can reach the writer."""
    attempt_id = uuid.uuid4().hex
    started = _now()
    state_conn.execute("BEGIN IMMEDIATE")
    try:
        current = state_conn.execute(
            "SELECT status FROM workflow_drafts WHERE id=?", (draft_id,)
        ).fetchone()
        if current is None or current["status"] not in {
            "approved",
            "apply_retryable",
            "apply_restored_retryable",
        }:
            status = current["status"] if current is not None else "missing"
            raise DraftError(
                "draft_not_applicable",
                f"draft {draft_id!r} is {status!r}, not applicable",
            )
        state_conn.execute(
            "INSERT INTO draft_apply_attempts(id, draft_id, preview_attempt_id, "
            "approval_attempt_id, change_set_id, semantic_fingerprint, "
            "preview_fingerprint, approval_fingerprint, started_ts, "
            "manager_state, allowed_verbs_json, active) "
            "VALUES(?,?,?,?,?,?,?,?,?,'applying','[]',1)",
            (
                attempt_id,
                draft_id,
                preview_attempt["id"],
                approval_attempt["id"],
                changeset["changeSetId"],
                changeset["semanticFingerprint"],
                preview["previewFingerprint"],
                approval["approvalFingerprint"],
                started,
            ),
        )
        state_conn.execute(
            "UPDATE workflow_drafts SET status='applying', updated_ts=? WHERE id=?",
            (started, draft_id),
        )
        state_conn.commit()
    except Exception:
        state_conn.rollback()
        raise
    return attempt_id


def _finish_apply_attempt(
    state_conn: sqlite3.Connection,
    *,
    attempt_id: str,
    draft_id: str,
    artifact_kind: str,
    result: dict | None,
    exception: BaseException | None,
    identity: dict,
    manager_state: str,
    allowed_verbs: list[str],
) -> dict:
    completed = _now()
    state_conn.execute("BEGIN IMMEDIATE")
    try:
        state_conn.execute(
            "UPDATE draft_apply_attempts SET completed_ts=?, artifact_kind=?, "
            "result_json=?, exception_class=?, exception_message=?, "
            "workbook_identity_state=?, observed_workbook_sha256=?, "
            "observed_workbook_mtime_ns=?, manager_state=?, allowed_verbs_json=?, "
            "active=0 WHERE id=? AND active=1",
            (
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
                attempt_id,
            ),
        )
        if state_conn.execute("SELECT changes() c").fetchone()["c"] != 1:
            raise DraftError("apply_attempt_not_active", "apply attempt is not active")
        state_conn.execute(
            "UPDATE workflow_drafts SET status=?, updated_ts=? WHERE id=?",
            (manager_state, completed, draft_id),
        )
        state_conn.commit()
    except Exception:
        state_conn.rollback()
        raise
    return _apply_attempt_dict(
        state_conn.execute(
            "SELECT * FROM draft_apply_attempts WHERE id=?", (attempt_id,)
        ).fetchone()
    )


def apply_draft(
    state_conn: sqlite3.Connection,
    *,
    draft_id: str,
    workbook_path: Path,
    log_path: Path | None = None,
    prepare_apply: Callable[[], Any] | None = None,
    complete_apply: Callable[[dict, Any], dict] | None = None,
) -> dict:
    """Apply exact stored artifacts once through the shared workbook service."""
    draft = state_conn.execute(
        "SELECT * FROM workflow_drafts WHERE id=?", (draft_id,)
    ).fetchone()
    if draft is None:
        raise DraftError("draft_not_found", f"draft {draft_id!r} was not found")
    terminal = state_conn.execute(
        "SELECT * FROM draft_apply_attempts WHERE draft_id=? "
        "AND manager_state='applied' AND active=0 "
        "ORDER BY completed_ts DESC, rowid DESC LIMIT 1",
        (draft_id,),
    ).fetchone()
    if draft["status"] == "applied" and terminal is not None:
        return _apply_attempt_dict(terminal)
    active = state_conn.execute(
        "SELECT id FROM draft_apply_attempts WHERE draft_id=? AND active=1",
        (draft_id,),
    ).fetchone()
    if active is not None or draft["status"] == "applying":
        raise DraftError("apply_attempt_active", "an apply attempt is already active")
    if draft["status"] not in {
        "approved",
        "apply_retryable",
        "apply_restored_retryable",
    }:
        raise DraftError(
            "draft_not_applicable",
            f"draft {draft_id!r} is {draft['status']!r}, not applicable",
        )
    changeset, preview_attempt, preview, approval_attempt, approval = (
        _latest_apply_artifacts(state_conn, draft_id)
    )
    attempt_id = _begin_apply_attempt(
        state_conn,
        draft_id=draft_id,
        changeset=changeset,
        preview_attempt=preview_attempt,
        preview=preview,
        approval_attempt=approval_attempt,
        approval=approval,
    )
    path = Path(workbook_path)
    try:
        prepared_apply = prepare_apply() if prepare_apply is not None else None
        result = workbook_service.apply_changeset(
            path, changeset, preview, approval, log_path=log_path
        )
        if (
            complete_apply is not None
            and _is_exact_applied_receipt(result, changeset, preview, approval)
        ):
            result = complete_apply(result, prepared_apply)
    except Exception as exc:
        identity = _workbook_identity(path, changeset["workbook"])
        if isinstance(exc, TRANSIENT_APPLY_EXCEPTIONS) and identity["state"] == "unchanged":
            manager_state, allowed_verbs = "apply_retryable", ["retry_apply", "cancel"]
        elif identity["state"] == "unchanged":
            manager_state, allowed_verbs = "apply_rejected", ["cancel"]
        else:
            manager_state, allowed_verbs = "workbook_state_unknown", ["resolve_manually"]
        return _finish_apply_attempt(
            state_conn,
            attempt_id=attempt_id,
            draft_id=draft_id,
            artifact_kind="exception",
            result=None,
            exception=exc,
            identity=identity,
            manager_state=manager_state,
            allowed_verbs=allowed_verbs,
        )
    identity = _workbook_identity(path, changeset["workbook"])
    exact_formal_receipt = _is_exact_formal_receipt(
        result, changeset, preview, approval
    )
    if _is_exact_applied_receipt(result, changeset, preview, approval):
        manager_state, allowed_verbs = "applied", []
    else:
        manager_state, allowed_verbs = _map_apply_result(
            result,
            identity_state=identity["state"],
            exact_formal_receipt=exact_formal_receipt,
        )
    artifact_kind = (
        "formal_receipt"
        if exact_formal_receipt
        else "early_refusal"
    )
    return _finish_apply_attempt(
        state_conn,
        attempt_id=attempt_id,
        draft_id=draft_id,
        artifact_kind=artifact_kind,
        result=result,
        exception=None,
        identity=identity,
        manager_state=manager_state,
        allowed_verbs=allowed_verbs,
    )


def cancel_draft(state_conn: sqlite3.Connection, *, draft_id: str) -> dict:
    """Cancel an eligible lifecycle without deleting immutable history."""
    cancellable = {
        "draft",
        "changeset_emitted",
        "preview_ready",
        "preview_retryable",
        "preview_rejected",
        "stale",
        "approval_confirmation_required",
        "approval_repreview_required",
        "approval_rejected",
        "approved",
        "apply_retryable",
        "apply_restored_retryable",
        "apply_rejected",
    }
    row = state_conn.execute(
        "SELECT * FROM workflow_drafts WHERE id=?", (draft_id,)
    ).fetchone()
    if row is None:
        raise DraftError("draft_not_found", f"draft {draft_id!r} was not found")
    if row["status"] not in cancellable:
        raise DraftError(
            "draft_not_cancellable",
            f"draft {draft_id!r} is {row['status']!r}, not cancellable",
        )
    timestamp = _now()
    state_conn.execute(
        "UPDATE workflow_drafts SET status='cancelled', updated_ts=? WHERE id=?",
        (timestamp, draft_id),
    )
    state_conn.commit()
    return dict(
        state_conn.execute(
            "SELECT * FROM workflow_drafts WHERE id=?", (draft_id,)
        ).fetchone()
    )


def _verify_changeset_final_rows(workbook_path: Path, changeset: dict) -> dict:
    """Independently prove the exact ChangeSet effects for manual recovery."""
    errors: list[str] = []
    try:
        parsed = parse_changeset(changeset)
        extract = editor_ops.extract_workbook(Path(workbook_path))
    except Exception as exc:
        return {"ok": False, "errors": [f"{type(exc).__name__}: {exc}"]}
    sheets = extract.get("sheets") or {}
    for create in parsed.get("sheetCreates", []):
        target = sheets.get(create["sheet"])
        template = sheets.get(create["headersFrom"])
        if target is None or template is None:
            errors.append(
                f"created sheet {create['sheet']!r} or template "
                f"{create['headersFrom']!r} is absent"
            )
        elif target.get("headers") != template.get("headers"):
            errors.append(f"created sheet {create['sheet']!r} headers differ")
    for index, change in enumerate(parsed.get("rowChanges", [])):
        sheet = sheets.get(change["sheet"])
        key_columns = tuple(
            editor_ops.EDITOR_SHEET_META.get(change["family"], {}).get("key") or ()
        )
        if sheet is None or not key_columns:
            errors.append(
                f"rowChanges[{index}] cannot resolve sheet/family "
                f"{change['sheet']!r}/{change['family']!r}"
            )
            continue
        matches = [
            row
            for row in sheet.get("rows", [])
            if all(row.get(column) == change["key"].get(column) for column in key_columns)
        ]
        if change["action"] == "delete":
            if matches:
                errors.append(f"rowChanges[{index}] deleted row still exists")
            continue
        if len(matches) != 1:
            errors.append(
                f"rowChanges[{index}] final key matched {len(matches)} rows, expected 1"
            )
            continue
        for field, pair in change["fields"].items():
            actual = matches[0].get(field)
            expected = pair["after"]
            bool_mismatch = (
                isinstance(actual, bool) or isinstance(expected, bool)
            ) and type(actual) is not type(expected)
            if bool_mismatch or actual != expected:
                errors.append(
                    f"rowChanges[{index}] field {field!r} expected "
                    f"{expected!r}, got {actual!r}"
                )
    return {
        "ok": not errors,
        "changeSetId": parsed["changeSetId"],
        "checkedRowChanges": len(parsed.get("rowChanges", [])),
        "checkedSheetCreates": len(parsed.get("sheetCreates", [])),
        "errors": errors,
    }


def resolve_unknown_draft(
    state_conn: sqlite3.Connection,
    *,
    draft_id: str,
    resolution: str,
    workbook_path: Path,
    actor: str,
    evidence: dict,
) -> dict:
    """Record one immutable human recovery decision for an unknown write."""
    draft = state_conn.execute(
        "SELECT * FROM workflow_drafts WHERE id=?", (draft_id,)
    ).fetchone()
    if draft is None:
        raise DraftError("draft_not_found", f"draft {draft_id!r} was not found")
    if draft["status"] != "workbook_state_unknown":
        raise DraftError(
            "draft_not_unknown", f"draft {draft_id!r} is not awaiting recovery"
        )
    attempt = state_conn.execute(
        "SELECT * FROM draft_apply_attempts WHERE draft_id=? "
        "AND manager_state='workbook_state_unknown' AND active=0 "
        "ORDER BY completed_ts DESC, rowid DESC LIMIT 1",
        (draft_id,),
    ).fetchone()
    if attempt is None:
        raise DraftError("unknown_attempt_not_found", "no unknown apply attempt exists")
    expected = {
        "sha256": draft["base_workbook_sha256"],
        "mtimeNs": draft["base_workbook_mtime_ns"],
    }
    identity = _workbook_identity(Path(workbook_path), expected)
    if resolution == "restored":
        if identity["state"] != "unchanged":
            raise DraftError(
                "restored_identity_not_proven",
                "restored resolution requires the exact base SHA-256/mtime",
            )
        manager_state = "manually_resolved_restored"
    elif resolution == "applied":
        stored = state_conn.execute(
            "SELECT payload_json FROM draft_changesets WHERE draft_id=?",
            (draft_id,),
        ).fetchone()
        verification = (
            _verify_changeset_final_rows(
                Path(workbook_path), json.loads(stored["payload_json"])
            )
            if stored is not None
            else {"ok": False, "errors": ["stored ChangeSet is absent"]}
        )
        if not verification.get("ok") or identity["state"] == "unavailable":
            raise DraftError(
                "applied_rows_not_proven",
                "applied resolution requires exact final-row and ChangeSet evidence",
                errors=verification.get("errors") or [],
            )
        evidence = {**evidence, "managerVerification": verification}
        manager_state = "manually_resolved_applied"
    elif resolution == "abandoned_unknown":
        manager_state = "abandoned_unknown"
    else:
        raise DraftError("invalid_resolution", f"unknown resolution {resolution!r}")
    resolution_id = uuid.uuid4().hex
    timestamp = _now()
    state_conn.execute("BEGIN IMMEDIATE")
    try:
        state_conn.execute(
            "INSERT INTO draft_manual_resolutions(id, draft_id, apply_attempt_id, "
            "created_ts, actor, resolution, evidence_json, "
            "observed_workbook_sha256, observed_workbook_mtime_ns, manager_state) "
            "VALUES(?,?,?,?,?,?,?,?,?,?)",
            (
                resolution_id,
                draft_id,
                attempt["id"],
                timestamp,
                actor,
                resolution,
                _json(evidence),
                identity["sha256"],
                identity["mtimeNs"],
                manager_state,
            ),
        )
        state_conn.execute(
            "UPDATE workflow_drafts SET status=?, updated_ts=? WHERE id=?",
            (manager_state, timestamp, draft_id),
        )
        state_conn.commit()
    except Exception:
        state_conn.rollback()
        raise
    return _manual_resolution_dict(
        state_conn.execute(
            "SELECT * FROM draft_manual_resolutions WHERE id=?", (resolution_id,)
        ).fetchone()
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


def _upsert_asset_resolution(
    state_conn: sqlite3.Connection,
    *,
    draft_id: str,
    operation_id: int | None,
    evidence: dict[str, Any],
    timestamp: str,
) -> None:
    required = {
        "item_id", "resolution_kind", "reconciliation_sha256",
        "media_inventory_sha256", "workbook_sha256",
    }
    missing = sorted(required - set(evidence))
    if missing:
        raise DraftError(
            "asset_evidence_incomplete",
            f"asset resolution evidence is missing: {', '.join(missing)}",
        )
    state_conn.execute(
        "INSERT INTO draft_asset_resolutions(draft_id, operation_id, created_ts, "
        "updated_ts, item_id, resolution_kind, reconciliation_sha256, "
        "media_inventory_sha256, workbook_sha256, media_url, candidate_source, "
        "candidate_reason, evidence_json) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?) "
        "ON CONFLICT(draft_id, item_id) DO UPDATE SET "
        "operation_id=excluded.operation_id, updated_ts=excluded.updated_ts, "
        "resolution_kind=excluded.resolution_kind, "
        "reconciliation_sha256=excluded.reconciliation_sha256, "
        "media_inventory_sha256=excluded.media_inventory_sha256, "
        "workbook_sha256=excluded.workbook_sha256, media_url=excluded.media_url, "
        "candidate_source=excluded.candidate_source, "
        "candidate_reason=excluded.candidate_reason, evidence_json=excluded.evidence_json",
        (
            draft_id,
            operation_id,
            timestamp,
            timestamp,
            evidence["item_id"],
            evidence["resolution_kind"],
            evidence["reconciliation_sha256"],
            evidence["media_inventory_sha256"],
            evidence["workbook_sha256"],
            evidence.get("media_url", ""),
            evidence.get("candidate_source", ""),
            evidence.get("candidate_reason", ""),
            _json(evidence),
        ),
    )


def save_asset_ignore(
    state_conn: sqlite3.Connection,
    *,
    draft_id: str,
    session_id: str,
    actor: str,
    base_workbook_sha256: str,
    base_workbook_mtime_ns: str,
    evidence: dict[str, Any],
    manage_transaction: bool = True,
) -> dict:
    """Store a no-workbook operational disposition beside the mutable draft."""

    timestamp = _now()
    if manage_transaction:
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
        _upsert_asset_resolution(
            state_conn,
            draft_id=draft_id,
            operation_id=None,
            evidence=evidence,
            timestamp=timestamp,
        )
        if manage_transaction:
            state_conn.commit()
    except Exception:
        if manage_transaction:
            state_conn.rollback()
        raise
    row = state_conn.execute(
        "SELECT * FROM draft_asset_resolutions WHERE draft_id=? AND item_id=?",
        (draft_id, evidence["item_id"]),
    ).fetchone()
    return _asset_resolution_dict(row)


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
    asset_evidence: dict[str, Any] | None = None,
    manage_transaction: bool = True,
) -> dict | None:
    """Store one coalesced physical-row operation in a mutable draft.

    Individual add/delete operations resolve identity and ownership here, but
    relational validity is intentionally deferred until the complete immutable
    ChangeSet reaches the shared final-graph preview service.
    """
    if projection_state != "current":
        raise DraftError(
            "projection_not_current",
            "draft authoring requires a current verified projection",
        )
    spec = SPEC_BY_TABLE.get(table)
    if spec is None:
        raise DraftError("unknown_table", f"unknown table {table!r}")
    if op not in {"add", "update", "delete"}:
        raise DraftError(
            "invalid_draft_action",
            f"unsupported draft action {op!r}",
        )
    if set(key) != set(spec.key) or any(not str(key.get(name, "")).strip() for name in spec.key):
        raise DraftError(
            "invalid_entity_key",
            f"draft key must contain exactly nonblank fields: {', '.join(spec.key)}",
        )
    row = _fetch_row(projection_conn, spec, model_id, key)
    source_sheet = str(
        row["src_sheet"] if row is not None else target_sheet_for(
            projection_conn, spec, model_id
        ) or ""
    ).strip()
    physical_key = str(
        row["physical_key"] if row is not None
        else _json([str(key[name]) for name in spec.key])
    ).strip()
    family = spec.editor_family or spec.family
    prior_row = state_conn.execute(
        "SELECT * FROM draft_operations WHERE draft_id=? AND source_sheet=? "
        "AND family=? AND physical_key=?",
        (draft_id, source_sheet, family, physical_key),
    ).fetchone()
    prior_operation = _operation_dict(prior_row) if prior_row is not None else None
    prior_is_add = prior_operation is not None and prior_operation["action"] == "add"
    if op in {"update", "delete"} and row is None and not prior_is_add:
        raise DraftError("record_not_found", "projected record was not found")
    if op == "add" and (row is not None or prior_operation is not None):
        raise DraftError("duplicate_record", "projected record already exists")

    supplied = record or {}
    column_names = {column.sql_name() for column in spec.columns}
    unknown = sorted(set(supplied) - column_names)
    if unknown:
        raise DraftError(
            "unknown_fields", f"draft contains unregistered fields: {', '.join(unknown)}"
        )
    original = _semantic_row(spec, row) if row is not None else None
    if prior_is_add and op == "update":
        assert prior_operation is not None
        final = dict(prior_operation["final"] or {})
        for name, value in supplied.items():
            column = spec.column_by_name(name)
            assert column is not None
            try:
                final[name] = projection_value(column, value)
            except ValueError as exc:
                raise DraftError("invalid_field_value", str(exc)) from exc
        op = "add"
    elif op == "add":
        final = {name: None for name in column_names}
        for name, value in supplied.items():
            column = spec.column_by_name(name)
            assert column is not None
            try:
                final[name] = projection_value(column, value)
            except ValueError as exc:
                raise DraftError("invalid_field_value", str(exc)) from exc
        mismatched_keys = [
            name for name in spec.key
            if str(final.get(name) or "") != str(key.get(name) or "")
        ]
        if mismatched_keys:
            raise DraftError(
                "key_mismatch",
                f"add record key fields must match the entity key: {', '.join(mismatched_keys)}",
            )
    elif op == "update":
        assert original is not None
        final = dict(original)
        for name, value in supplied.items():
            column = spec.column_by_name(name)
            assert column is not None
            try:
                final[name] = projection_value(column, value)
            except ValueError as exc:
                raise DraftError("invalid_field_value", str(exc)) from exc
        changed_keys = [name for name in spec.key if final.get(name) != original.get(name)]
        if changed_keys:
            raise DraftError(
                "key_change_rejected",
                f"key fields cannot change on update: {', '.join(changed_keys)}",
            )
    else:
        final = None
    ownership_errors = _editable_guard(
        projection_conn,
        spec,
        model_id,
        op=op,
        key=key,
        record=final if final is not None else original,
    )
    if ownership_errors:
        raise DraftError(
            "ownership_rejected", ownership_errors[0]["message"], errors=ownership_errors
        )

    if not source_sheet or not physical_key:
        raise DraftError(
            "physical_target_unresolved",
            "draft operation requires a resolved source sheet and physical key",
        )
    timestamp = _now()

    if manage_transaction:
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
            if prior["action"] == "add" and op == "delete":
                state_conn.execute(
                    "DELETE FROM draft_operations WHERE id=?", (existing["id"],)
                )
                if manage_transaction:
                    state_conn.commit()
                return None
            if prior["action"] == "delete":
                if op == "delete":
                    if manage_transaction:
                        state_conn.commit()
                    return prior
                raise DraftError(
                    "draft_operation_conflict",
                    "a deleted draft row cannot be edited without recreating the draft",
                )
            original = prior["original"]
            if op == "delete":
                final = None
            else:
                final = dict(prior["final"] or original or {})
                for name, value in supplied.items():
                    column = spec.column_by_name(name)
                    assert column is not None
                    try:
                        final[name] = projection_value(column, value)
                    except ValueError as exc:
                        raise DraftError("invalid_field_value", str(exc)) from exc
                if prior["action"] == "add":
                    op = "add"

        if op == "add":
            changed_fields = {
                name: {"before": None, "after": value}
                for name, value in (final or {}).items()
                if value is not None
            }
        elif op == "delete":
            changed_fields = {
                name: {"before": value, "after": None}
                for name, value in (original or {}).items()
                if value is not None
            }
        else:
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
            remaining = state_conn.execute(
                "SELECT COUNT(*) AS c FROM draft_operations WHERE draft_id=?",
                (draft_id,),
            ).fetchone()["c"]
            if remaining == 0:
                state_conn.execute(
                    "DELETE FROM workflow_drafts WHERE id=? AND status='draft'",
                    (draft_id,),
                )
            if manage_transaction:
                state_conn.commit()
            return None
        values = (
            timestamp,
            table,
            family,
            model_id or "",
            source_sheet,
            row["src_row"] if row is not None else None,
            physical_key,
            _json(key),
            op,
            _json(original) if original is not None else None,
            _json(final) if final is not None else None,
            _json(changed_fields),
            str(
                row["model_context"] if row is not None
                else _json([model_id] if model_id else [])
                or "[]"
            ),
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
        if asset_evidence is not None:
            _upsert_asset_resolution(
                state_conn,
                draft_id=draft_id,
                operation_id=int(operation_id),
                evidence=asset_evidence,
                timestamp=timestamp,
            )
        if manage_transaction:
            state_conn.commit()
    except Exception:
        if manage_transaction:
            state_conn.rollback()
        raise

    stored = state_conn.execute(
        "SELECT * FROM draft_operations WHERE id=?", (operation_id,)
    ).fetchone()
    result = _operation_dict(stored)
    result["asset_resolutions"] = [
        _asset_resolution_dict(row)
        for row in state_conn.execute(
            "SELECT * FROM draft_asset_resolutions WHERE operation_id=? ORDER BY id",
            (operation_id,),
        ).fetchall()
    ]
    return result
