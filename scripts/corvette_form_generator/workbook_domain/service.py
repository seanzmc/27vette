#!/usr/bin/env python3
"""Shared workbook ChangeSet service: preview, approval, guarded apply, receipts.

This module owns the mutable ChangeSet lifecycle. The immutable
``workbook-changeset-1`` proposal (workbook_domain.changeset) is never
rewritten here; previews, approvals, and receipts are separate JSON
artifacts bound to the ChangeSet's semantic fingerprint and to each
other. The actual validation and write engine remains
``editor_ops.apply_batch`` — this service adds exact-fingerprint binding
and receipt creation on top of it.
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from pathlib import Path

from corvette_form_generator import editor_ops
from corvette_form_generator.workbook_domain.changeset import (
    ChangeSetError,
    canonical_json,
    changeset_to_editor_batch,
    parse_changeset,
)

PREVIEW_SCHEMA = "workbook-change-preview-1"
APPROVAL_SCHEMA = "workbook-change-approval-1"
RECEIPT_SCHEMA = "workbook-change-receipt-1"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _fingerprint(payload: dict, exclude: str) -> str:
    body = {key: value for key, value in payload.items() if key != exclude}
    return hashlib.sha256(canonical_json(body).encode("utf-8")).hexdigest()


def _fingerprint_matches(payload: dict, field: str) -> bool:
    stored = payload.get(field)
    return isinstance(stored, str) and stored == _fingerprint(payload, field)


def _live_workbook_fingerprint(path: Path) -> dict:
    path = Path(path)
    return {
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "mtimeNs": str(path.stat().st_mtime_ns),
    }


def preview_changeset(workbook_path, changeset: dict) -> dict:
    """Validate a ChangeSet against the live workbook without writing.

    Parses the ChangeSet, verifies the live workbook matches the reviewed
    SHA/mtime precondition, converts to an editor batch, and runs the
    shared final-state validator (``apply_batch(write=False)``). Returns a
    ``workbook-change-preview-1`` dict carrying a deterministic
    ``previewFingerprint`` over its own contents.
    """
    path = Path(workbook_path)
    try:
        parsed = parse_changeset(changeset)
    except ChangeSetError as exc:
        return {"ok": False, "status": "invalid_changeset", "errors": [str(exc)]}
    if _live_workbook_fingerprint(path) != parsed["workbook"]:
        return {
            "ok": False,
            "status": "stale",
            "errors": ["live workbook no longer matches the ChangeSet's "
                       "reviewed SHA-256/mtime precondition; re-emit or re-bind"],
        }
    try:
        batch = changeset_to_editor_batch(parsed, editor_ops.extract_workbook(path))
    except ChangeSetError as exc:
        return {"ok": False, "status": "stale", "errors": [str(exc)]}
    result = editor_ops.apply_batch(path, batch, write=False)
    preview = {
        "ok": result["ok"],
        "schemaVersion": PREVIEW_SCHEMA,
        "changeSetId": parsed["changeSetId"],
        "semanticFingerprint": parsed["semanticFingerprint"],
        "workbook": dict(parsed["workbook"]),
        "status": result["status"],
        "errors": result.get("errors", []),
        "warnings": result.get("warnings", []),
        "warningPolicy": result.get("warningPolicy"),
        "operationCoverage": result.get("operationCoverage"),
        "verification": result.get("verification"),
        "schemaResult": result.get("schemaResult"),
        "boolHygieneResult": result.get("boolHygieneResult"),
        "gateReminders": result.get("gateReminders"),
        "createdAt": _now(),
    }
    preview["previewFingerprint"] = _fingerprint(preview, "previewFingerprint")
    return preview


def approve_changeset(changeset: dict, preview: dict, *, actor: str,
                      warning_ids) -> dict:
    """Bind an operator approval to the exact reviewed ChangeSet/preview.

    Requires a passing preview of the exact ChangeSet, no blocking warning
    IDs, and an accepted-warning set exactly equal to the preview's
    confirmable IDs. Returns ``workbook-change-approval-1``; grants write
    authority only when later presented with matching artifacts.
    """
    if preview.get("schemaVersion") != PREVIEW_SCHEMA or not preview.get("ok"):
        return {"ok": False, "status": "preview_not_validated",
                "errors": ["approval requires a passing workbook-change-preview-1"]}
    if preview.get("status") != "validated":
        return {"ok": False, "status": "preview_not_validated",
                "errors": [f"preview status is {preview.get('status')!r}, not 'validated'"]}
    if not _fingerprint_matches(preview, "previewFingerprint"):
        return {"ok": False, "status": "binding_mismatch",
                "errors": ["preview contents do not match previewFingerprint"]}
    if (preview.get("semanticFingerprint") != changeset.get("semanticFingerprint")
            or preview.get("changeSetId") != changeset.get("changeSetId")
            or preview.get("workbook") != changeset.get("workbook")):
        return {"ok": False, "status": "binding_mismatch",
                "errors": ["preview does not bind the exact ChangeSet being approved"]}
    policy = preview.get("warningPolicy") or {}
    blocking = sorted(policy.get("blockingIds") or [])
    if blocking:
        return {"ok": False, "status": "warning_blocked",
                "errors": [f"preview emitted unconfirmable warning IDs: {blocking}"]}
    confirmable = sorted(policy.get("confirmableIds") or [])
    accepted = sorted(str(wid) for wid in (warning_ids or []))
    if accepted != confirmable:
        missing = sorted(set(confirmable) - set(accepted))
        extra = sorted(set(accepted) - set(confirmable))
        return {"ok": False, "status": "warning_confirmation_mismatch",
                "errors": [f"accepted warning IDs must exactly match confirmable IDs; "
                           f"missing: {missing}; unexpected: {extra}"]}
    approval = {
        "ok": True,
        "schemaVersion": APPROVAL_SCHEMA,
        "actor": actor,
        "changeSetId": changeset["changeSetId"],
        "semanticFingerprint": changeset["semanticFingerprint"],
        "previewFingerprint": preview["previewFingerprint"],
        "workbook": dict(changeset["workbook"]),
        "acceptedWarningIds": accepted,
        "createdAt": _now(),
    }
    approval["approvalFingerprint"] = _fingerprint(approval, "approvalFingerprint")
    return approval


def apply_changeset(workbook_path, changeset: dict, preview: dict,
                    approval: dict, *, log_path=None) -> dict:
    """Apply an approved ChangeSet once through the guarded write path.

    Requires exact ChangeSet/preview/approval fingerprint binding and a
    live workbook still matching the reviewed precondition, then calls
    ``apply_batch(write=True)`` exactly once. Returns a
    ``workbook-change-receipt-1`` dict describing the outcome, including
    ``workbookState`` (``saved``/``restored``/``untouched``/``unknown``).
    """
    path = Path(workbook_path)
    if approval.get("schemaVersion") != APPROVAL_SCHEMA or not approval.get("ok"):
        return {"ok": False, "status": "approval_invalid",
                "workbookState": "untouched",
                "errors": ["apply requires a passing workbook-change-approval-1"]}
    if not _fingerprint_matches(preview, "previewFingerprint"):
        return {"ok": False, "status": "binding_mismatch",
                "workbookState": "untouched",
                "errors": ["preview contents do not match previewFingerprint"]}
    if not _fingerprint_matches(approval, "approvalFingerprint"):
        return {"ok": False, "status": "approval_invalid",
                "workbookState": "untouched",
                "errors": ["approval contents do not match approvalFingerprint"]}
    if (approval.get("semanticFingerprint") != changeset.get("semanticFingerprint")
            or approval.get("semanticFingerprint") != preview.get("semanticFingerprint")
            or approval.get("previewFingerprint") != preview.get("previewFingerprint")
            or approval.get("workbook") != changeset.get("workbook")
            or changeset.get("workbook") != preview.get("workbook")):
        return {"ok": False, "status": "binding_mismatch",
                "workbookState": "untouched",
                "errors": ["ChangeSet, preview, and approval fingerprints do not "
                           "bind the same reviewed artifacts"]}
    if _live_workbook_fingerprint(path) != changeset["workbook"]:
        return {"ok": False, "status": "stale",
                "workbookState": "untouched",
                "errors": ["live workbook no longer matches the reviewed SHA-256/"
                           "mtime precondition; re-preview and re-approve"]}
    try:
        parsed = parse_changeset(changeset)
        batch = changeset_to_editor_batch(parsed, editor_ops.extract_workbook(path))
    except ChangeSetError as exc:
        return {"ok": False, "status": "stale",
                "workbookState": "untouched", "errors": [str(exc)]}
    result = editor_ops.apply_batch(
        path,
        batch,
        write=True,
        confirmed_warnings=tuple(approval["acceptedWarningIds"]),
        log_path=log_path,
        run_schema_validation=True,
    )
    receipt = {
        "ok": result["ok"],
        "schemaVersion": RECEIPT_SCHEMA,
        "changeSetId": changeset["changeSetId"],
        "semanticFingerprint": changeset["semanticFingerprint"],
        "previewFingerprint": preview["previewFingerprint"],
        "approvalFingerprint": approval["approvalFingerprint"],
        "status": result["status"],
        "workbookState": result.get("workbookState")
        or ("saved" if result["ok"] else "untouched"),
        "errors": result.get("errors", []),
        "warnings": result.get("warnings", []),
        "backupPath": result.get("backupPath"),
        "logPath": result.get("logPath"),
        "operationCoverage": result.get("operationCoverage"),
        "verification": result.get("verification"),
        "schemaResult": result.get("schemaResult"),
        "boolHygieneResult": result.get("boolHygieneResult"),
        "gateReminders": result.get("gateReminders"),
        "createdAt": _now(),
    }
    return receipt
