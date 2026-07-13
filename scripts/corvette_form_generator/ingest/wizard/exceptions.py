#!/usr/bin/env python3
"""Typed exception, resolution, and audit contracts for Milestone 1."""

from __future__ import annotations

import hashlib
import json
import os
import time
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

from corvette_form_generator.ingest.wizard.canonical_rows import (
    canonical_text,
    normalize_dependencies,
    semantic_hash,
    sha256_hex,
)

EXCEPTION_RESOLUTIONS_SCHEMA = "exception-resolutions-1"
ALLOWED_DEFERRAL_KINDS = {"asset_map_media_missing"}
ALLOWED_ACTIONS = frozenset(
    {
        "provide_typed_value",
        "retain_existing",
        "approve_removal",
        "mark_not_applicable",
        "record_allowed_deferral",
        "choose_section",
        "choose_relationship",
    }
)
ALLOWED_DISPOSITIONS = frozenset({"resolved", "resolved_not_applicable", "retained_existing", "allowed_deferral"})
ACTION_DISPOSITIONS = {
    "provide_typed_value": "resolved",
    "approve_removal": "resolved",
    "choose_section": "resolved",
    "choose_relationship": "resolved",
    "retain_existing": "retained_existing",
    "mark_not_applicable": "resolved_not_applicable",
    "record_allowed_deferral": "allowed_deferral",
}

REASON_ACTIONS = {
    "missing_price_scope": {"provide_typed_value"},
    "unresolved_price_scope": {"provide_typed_value"},
    "missing_section": {"choose_section"},
    "unresolved_relationship_endpoint": {"choose_relationship"},
    "unsupported_relationship_type": {"choose_relationship"},
    "unsupported_relationship_direction": {"choose_relationship"},
    "comparator_only_relationship_proposal": {"choose_relationship", "mark_not_applicable"},
    "comparator_only_rule_group_proposal": {"provide_typed_value", "mark_not_applicable"},
    "comparator_only_exclusive_group_proposal": {"provide_typed_value", "mark_not_applicable"},
    "comparator_only_price_rule_proposal": {"provide_typed_value", "mark_not_applicable"},
    "comparator_only_default_selection_proposal": {"provide_typed_value", "mark_not_applicable"},
    "ambiguous_existing_identity": {"retain_existing"},
    "deletion_reference_impact": {"approve_removal", "retain_existing"},
    "asset_map_media_missing": {"record_allowed_deferral"},
}


def validate_subject_action_contract(reason_code: str, actions: Iterable[str]) -> list[str]:
    normalized = sorted(set(str(action) for action in actions))
    unknown = sorted(set(normalized) - ALLOWED_ACTIONS)
    if unknown:
        raise ValueError(f"Unknown exception actions: {', '.join(unknown)}")
    unsupported = sorted(set(normalized) - REASON_ACTIONS.get(str(reason_code), set()))
    if unsupported:
        raise ValueError(
            f"Exception reason {reason_code!r} does not support actions: {', '.join(unsupported)}"
        )
    return normalized


def exception_subject(
    *,
    subject_id_value: str,
    subject_version_value: str,
    model: str,
    family: str,
    severity: str,
    reason_code: str,
    allowed_actions: Iterable[str],
    evidence_dependencies: Iterable[Mapping[str, Any]],
    evidence_references: Iterable[str],
    proposed_rows: Iterable[Mapping[str, Any]],
    gate_impact: Iterable[str],
    question: str,
) -> dict[str, Any]:
    actions = validate_subject_action_contract(reason_code, allowed_actions)
    if severity not in {"blocking", "warning"}:
        raise ValueError(f"Invalid exception severity: {severity!r}")
    return {
        "subjectId": str(subject_id_value),
        "exceptionId": f"exception:{subject_id_value}",
        "subjectVersion": str(subject_version_value),
        "model": str(model),
        "family": str(family),
        "severity": severity,
        "reasonCode": str(reason_code),
        "question": str(question),
        "allowedActions": actions,
        "proposedRows": list(proposed_rows),
        "evidenceDependencies": normalize_dependencies(evidence_dependencies),
        "evidenceReferences": sorted(set(str(value) for value in evidence_references if str(value))),
        "gateImpact": sorted(set(str(value) for value in gate_impact if str(value))),
    }


def validate_resolution(resolution: Mapping[str, Any], subject: Mapping[str, Any]) -> dict[str, Any]:
    action = str(resolution.get("action") or "")
    if action not in subject.get("allowedActions", ()) or action not in ALLOWED_ACTIONS:
        raise ValueError(f"Resolution action {action!r} is not allowed for this exception.")
    reason_code = str(subject.get("reasonCode") or "")
    if action not in REASON_ACTIONS.get(reason_code, set()):
        raise ValueError(f"Resolution action {action!r} has no typed contract for {reason_code!r}.")
    if resolution.get("subjectId") != subject.get("subjectId"):
        raise ValueError("Resolution subjectId does not match the exception.")
    if resolution.get("subjectVersion") != subject.get("subjectVersion"):
        raise ValueError("Resolution subjectVersion is stale.")
    payload = resolution.get("payload")
    if not isinstance(payload, Mapping):
        raise ValueError("Resolution payload must be a typed object.")
    disposition = str(resolution.get("disposition") or "")
    if disposition not in ALLOWED_DISPOSITIONS:
        raise ValueError(f"Resolution disposition {disposition!r} is invalid.")
    if disposition != ACTION_DISPOSITIONS[action]:
        raise ValueError(
            f"Resolution action {action!r} requires disposition {ACTION_DISPOSITIONS[action]!r}."
        )
    if disposition == "allowed_deferral":
        kind = str(payload.get("kind") or "")
        if kind not in ALLOWED_DEFERRAL_KINDS:
            raise ValueError(f"Deferral kind {kind!r} is not allowlisted.")
    if action == "choose_section":
        if set(payload) != {"sectionId"} or not isinstance(payload.get("sectionId"), str) or not payload["sectionId"].strip():
            raise ValueError("choose_section requires exactly one non-empty string sectionId.")
    elif action == "choose_relationship":
        required = {"sourceOptionId", "ruleType", "targetOptionId"}
        if set(payload) != required or not all(isinstance(payload.get(key), str) and payload[key].strip() for key in required):
            raise ValueError("choose_relationship requires exact string sourceOptionId, ruleType, and targetOptionId fields.")
        if payload["ruleType"] not in {"requires", "includes", "excludes", "replaces"}:
            raise ValueError("choose_relationship ruleType is not supported.")
    elif action == "provide_typed_value" and reason_code in {"missing_price_scope", "unresolved_price_scope"}:
        allowed = {"bodyStyleScope", "trimLevelScope", "priceValue"}
        if not payload or set(payload) - allowed:
            raise ValueError("Price-scope resolution contains unsupported fields.")
        if reason_code == "unresolved_price_scope" and "priceValue" not in payload:
            raise ValueError("unresolved_price_scope requires a numeric priceValue.")
        for key in set(payload) - {"priceValue"}:
            if not isinstance(payload[key], str) or not payload[key].strip():
                raise ValueError(f"Price-scope field {key} must be a non-empty string.")
        if "priceValue" in payload and (isinstance(payload["priceValue"], bool) or not isinstance(payload["priceValue"], (int, float))):
            raise ValueError("priceValue must be numeric.")
        if "priceValue" in payload and not float(payload["priceValue"]).is_integer():
            raise ValueError("priceValue must be a whole-dollar integer.")
    elif action == "provide_typed_value" and reason_code in {
        "comparator_only_rule_group_proposal",
        "comparator_only_exclusive_group_proposal",
        "comparator_only_price_rule_proposal",
        "comparator_only_default_selection_proposal",
    }:
        if payload != {"decision": "confirm_proposal"}:
            raise ValueError("Comparator proposal confirmation requires decision=confirm_proposal.")
    elif action == "provide_typed_value":
        raise ValueError(f"provide_typed_value has no typed payload contract for {reason_code!r}.")
    elif action == "retain_existing":
        if set(payload) != {"existingId"} or not isinstance(payload.get("existingId"), str) or not payload["existingId"].strip():
            raise ValueError("retain_existing requires exactly one non-empty existingId.")
    elif action == "mark_not_applicable":
        if set(payload) != {"reason"} or not isinstance(payload.get("reason"), str) or not payload["reason"].strip():
            raise ValueError("mark_not_applicable requires exactly one non-empty reason.")
    elif action == "approve_removal":
        if set(payload) != {"reason"} or not isinstance(payload.get("reason"), str) or not payload["reason"].strip():
            raise ValueError("approve_removal requires exactly one non-empty reason.")
    elif action == "record_allowed_deferral":
        if set(payload) != {"kind", "reason"}:
            raise ValueError("record_allowed_deferral requires exact kind and reason fields.")
        if payload.get("kind") not in ALLOWED_DEFERRAL_KINDS:
            raise ValueError(f"Deferral kind {payload.get('kind')!r} is not allowlisted.")
        if not isinstance(payload.get("reason"), str) or not payload["reason"].strip():
            raise ValueError("record_allowed_deferral reason must be a non-empty string.")
    result = dict(resolution)
    result["payload"] = dict(payload)
    return result


def classify_resolutions(entries: Iterable[Mapping[str, Any]], subjects: Iterable[Mapping[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    by_id = {str(subject["subjectId"]): subject for subject in subjects}
    valid: list[dict[str, Any]] = []
    stale: list[dict[str, Any]] = []
    superseded: list[dict[str, Any]] = []
    seen: set[str] = set()
    current_by_subject: set[tuple[str, str]] = set()
    for raw in entries:
        entry = dict(raw)
        sid = str(entry.get("subjectId") or "")
        key = canonical_text({"subjectId": sid, "subjectVersion": entry.get("subjectVersion"), "action": entry.get("action"), "payload": entry.get("payload")})
        if key in seen:
            raise ValueError(f"Duplicate resolution entry for {sid}.")
        seen.add(key)
        subject = by_id.get(sid)
        if subject is None:
            superseded.append(entry)
            continue
        if entry.get("subjectVersion") != subject.get("subjectVersion"):
            stale.append(entry)
            continue
        current_key = (sid, str(entry.get("subjectVersion") or ""))
        if current_key in current_by_subject:
            raise ValueError(f"Conflicting current resolutions for {sid}.")
        current_by_subject.add(current_key)
        valid.append(validate_resolution(entry, subject))
    sort_key = lambda item: (str(item.get("subjectId") or ""), str(item.get("subjectVersion") or ""), str(item.get("action") or ""))
    return {"valid": sorted(valid, key=sort_key), "stale": sorted(stale, key=sort_key), "superseded": sorted(superseded, key=sort_key)}


def _resolution_semantic_entry(entry: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "subjectId": entry.get("subjectId"),
        "subjectVersion": entry.get("subjectVersion"),
        "action": entry.get("action"),
        "payload": entry.get("payload") or {},
        "disposition": entry.get("disposition"),
    }


def build_resolution_artifact(
    queue_subject_fingerprint: str,
    valid_entries: Iterable[Mapping[str, Any]],
    *,
    stale_entries: Iterable[Mapping[str, Any]] = (),
    superseded_entries: Iterable[Mapping[str, Any]] = (),
    deferrals: Iterable[Mapping[str, Any]] = (),
) -> dict[str, Any]:
    checked_deferrals: list[dict[str, Any]] = []
    for raw in deferrals:
        item = dict(raw)
        if item.get("disposition") == "allowed_deferral" and item.get("kind") not in ALLOWED_DEFERRAL_KINDS:
            raise ValueError(f"Deferral kind {item.get('kind')!r} is not allowlisted.")
        checked_deferrals.append(item)
    valid = sorted((dict(entry) for entry in valid_entries), key=lambda item: str(item.get("subjectId") or ""))
    semantic_entries = [_resolution_semantic_entry(entry) for entry in valid]
    return {
        "schemaVersion": EXCEPTION_RESOLUTIONS_SCHEMA,
        "queueSubjectFingerprint": str(queue_subject_fingerprint),
        "resolutionSemanticSha": semantic_hash({"schemaVersion": EXCEPTION_RESOLUTIONS_SCHEMA, "entries": semantic_entries}),
        "entries": valid,
        "validEntries": valid,
        "staleEntries": list(stale_entries),
        "supersededEntries": list(superseded_entries),
        "deferrals": checked_deferrals,
    }


def build_audit_event(
    *,
    queue_subject_fingerprint: str,
    subject_id_value: str,
    subject_version_value: str,
    event_type: str,
    prior_state: str,
    next_state: str,
    cause_fingerprint: str,
    resolution_entry_semantic_sha: str = "",
    reviewer: str = "",
    occurred_at: str = "",
) -> dict[str, Any]:
    identity = {
        "eventType": str(event_type),
        "subjectId": str(subject_id_value),
        "subjectVersion": str(subject_version_value),
        "priorState": str(prior_state),
        "nextState": str(next_state),
        "resolutionEntrySemanticSha": str(resolution_entry_semantic_sha),
        "causeFingerprint": str(cause_fingerprint),
    }
    return {
        "eventId": sha256_hex(identity),
        "queueSubjectFingerprint": str(queue_subject_fingerprint),
        **identity,
        "reviewer": str(reviewer),
        "occurredAt": str(occurred_at or time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())),
    }


def append_audit_event_once(path: Path, event: Mapping[str, Any]) -> bool:
    """Append one deterministic audit event unless its eventId already exists."""

    target = Path(path)
    existing_ids: set[str] = set()
    if target.is_file():
        for line in target.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            existing = json.loads(line)
            existing_ids.add(str(existing.get("eventId") or ""))
    event_id = str(event.get("eventId") or "")
    if not event_id:
        raise ValueError("Audit event requires eventId.")
    if event_id in existing_ids:
        return False
    with target.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(dict(event), sort_keys=True, ensure_ascii=False) + "\n")
        handle.flush()
        os.fsync(handle.fileno())
    return True
