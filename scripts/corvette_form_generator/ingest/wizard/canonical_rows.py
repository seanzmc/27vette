#!/usr/bin/env python3
"""Deterministic contracts for headless ingest compiler artifacts.

Authority envelopes prove which exact files were compiled. Semantic hashes are
computed independently from declared evidence dependencies so unrelated source
or workbook churn does not stale unaffected subjects and derivations.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Iterable, Mapping
from typing import Any

COMPILER_POLICY_VERSION = "options-recurrence-prevention-4.4-v1"
CANONICAL_ROWS_SCHEMA = "canonical-rows-1"
EXCEPTION_QUEUE_SCHEMA = "exception-queue-1"
COMPILE_REPORT_SCHEMA = "compile-report-1"

ACTIONS = frozenset({"add", "update", "delete", "noop"})
ROW_STATUSES = frozenset({"ready", "blocked", "suppressed"})
READINESS_FIELDS = ("compileReady", "planReady", "writeReady", "deploymentReady")

_SEMANTIC_EXCLUDED_KEYS = frozenset(
    {
        "runAuthorityFingerprint",
        "authority",
        "authorityEnvelope",
        "generatedAt",
        "generated_at",
        "reviewedAt",
        "selectedAt",
        "occurredAt",
        "timestamp",
        "reviewer",
        "reviewerDisplayName",
        "absolutePath",
        "sourcePath",
        "mtimeNs",
        "mtime_ns",
        "fileSha256",
        "fullFileSha256",
        "manifestSemanticSha",
        "compileReportSemanticSha",
        "queueSubjectFingerprint",
        "resolutionSemanticSha",
        "comparatorEvidenceSemanticSha",
        "eventId",
        "rowIndex",
        "row_index",
        "columnIndex",
        "column_index",
        "columnLetter",
        "column_letter",
        "cellCoordinate",
        "cell_coordinate",
        "sourceRowIndex",
        "sourceColumnIndex",
    }
)
_TOKEN_RE = re.compile(r"[^a-z0-9]+")


def _jsonable(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    if isinstance(value, (set, frozenset)):
        return sorted((_jsonable(item) for item in value), key=lambda item: json.dumps(item, sort_keys=True))
    return value


def canonical_bytes(value: Any) -> bytes:
    return (json.dumps(_jsonable(value), ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def canonical_text(value: Any) -> str:
    return canonical_bytes(value).decode("utf-8")


def sha256_hex(value: Any) -> str:
    payload = value if isinstance(value, bytes) else canonical_bytes(value)
    return hashlib.sha256(payload).hexdigest()


def _semantic_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {
            str(key): _semantic_value(item)
            for key, item in value.items()
            if str(key) not in _SEMANTIC_EXCLUDED_KEYS
            and not str(key).endswith("FullFileSha")
            and not str(key).endswith("FileSha")
        }
    if isinstance(value, (list, tuple)):
        return [_semantic_value(item) for item in value]
    if isinstance(value, (set, frozenset)):
        return sorted((_semantic_value(item) for item in value), key=lambda item: canonical_text(item))
    return value


def semantic_hash(value: Any) -> str:
    return sha256_hex(_semantic_value(value))


def normalize_token(value: Any) -> str:
    token = _TOKEN_RE.sub("_", str(value or "").strip().lower()).strip("_")
    return token or "none"


def normalize_dependencies(dependencies: Iterable[Mapping[str, Any]]) -> list[dict[str, str]]:
    normalized: list[dict[str, str]] = []
    seen: set[str] = set()
    for dependency in dependencies:
        evidence_id = str(dependency.get("evidenceId") or "").strip()
        fingerprint = str(dependency.get("semanticFingerprint") or "").strip()
        if not evidence_id or not fingerprint:
            raise ValueError("Evidence dependencies require evidenceId and semanticFingerprint.")
        if evidence_id in seen:
            raise ValueError(f"Duplicate evidence dependency: {evidence_id}")
        seen.add(evidence_id)
        normalized.append({"evidenceId": evidence_id, "semanticFingerprint": fingerprint})
    return sorted(normalized, key=lambda item: item["evidenceId"])


def subject_id(model: str, exception_kind: str, semantic_identities: Iterable[Any]) -> str:
    model_token = normalize_token(model)
    kind_token = normalize_token(exception_kind)
    identities = sorted(str(value).strip().lower() for value in semantic_identities if str(value).strip())
    digest = sha256_hex({"model": model_token, "kind": kind_token, "identities": identities})[:16]
    return f"subject:{model_token}:{kind_token}:{digest}"


def subject_version(subject_id_value: str, dependencies: Iterable[Mapping[str, Any]], *, policy_version: str = COMPILER_POLICY_VERSION) -> str:
    return sha256_hex(
        {
            "subjectId": subject_id_value,
            "evidenceDependencies": normalize_dependencies(dependencies),
            "compilerPolicyVersion": policy_version,
        }
    )


def derivation_version(semantic_signature: Any, dependencies: Iterable[Mapping[str, Any]], *, policy_version: str = COMPILER_POLICY_VERSION) -> str:
    return sha256_hex(
        {
            "semanticSignature": semantic_signature,
            "evidenceDependencies": normalize_dependencies(dependencies),
            "compilerPolicyVersion": policy_version,
        }
    )


def _authority_envelope(authority: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(authority, Mapping) or not authority:
        raise ValueError("runAuthorityFingerprint is required.")
    envelope = dict(authority)
    bindings = envelope.get("bindings")
    fingerprint = str(envelope.get("fingerprint") or "")
    if not isinstance(bindings, Mapping) or not fingerprint:
        raise ValueError("runAuthorityFingerprint requires fingerprint and bindings.")
    expected = hashlib.sha256(canonical_bytes(bindings)).hexdigest()
    if fingerprint != expected:
        raise ValueError("runAuthorityFingerprint does not match its bindings.")
    return envelope


def _validate_subject(subject: Mapping[str, Any]) -> dict[str, Any]:
    required = (
        "subjectId",
        "exceptionId",
        "subjectVersion",
        "model",
        "family",
        "severity",
        "reasonCode",
        "allowedActions",
        "proposedRows",
        "evidenceDependencies",
        "evidenceReferences",
        "gateImpact",
    )
    missing = [field for field in required if field not in subject]
    if missing:
        raise ValueError(f"Exception subject is missing fields: {', '.join(missing)}")
    result = dict(subject)
    result["evidenceDependencies"] = normalize_dependencies(subject["evidenceDependencies"])
    expected = subject_version(str(subject["subjectId"]), result["evidenceDependencies"])
    if subject["subjectVersion"] != expected:
        raise ValueError("Exception subjectVersion does not match declared evidenceDependencies.")
    if subject["severity"] not in {"blocking", "warning"}:
        raise ValueError(f"Invalid exception severity: {subject['severity']!r}")
    return result


def build_exception_queue(
    authority: Mapping[str, Any],
    comparator_semantic_sha: str,
    subjects: Iterable[Mapping[str, Any]],
    *,
    evidence_partitions: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    normalized = sorted((_validate_subject(subject) for subject in subjects), key=lambda item: item["subjectId"])
    ids = [item["subjectId"] for item in normalized]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate exception subjectId values.")
    queue_fingerprint = semantic_hash({"schemaVersion": EXCEPTION_QUEUE_SCHEMA, "subjects": normalized})
    return {
        "schemaVersion": EXCEPTION_QUEUE_SCHEMA,
        "runAuthorityFingerprint": _authority_envelope(authority),
        "comparatorEvidenceSemanticSha": str(comparator_semantic_sha),
        "queueSubjectFingerprint": queue_fingerprint,
        "subjects": normalized,
        **dict(evidence_partitions or {}),
    }


def _validate_manifest_row(row: Mapping[str, Any]) -> dict[str, Any]:
    required = ("model", "family", "sheet", "action", "key", "values", "semanticSignature", "evidenceDependencies", "derivationVersion", "status")
    missing = [field for field in required if field not in row]
    if missing:
        raise ValueError(f"Canonical row is missing fields: {', '.join(missing)}")
    if row["action"] not in ACTIONS:
        raise ValueError(f"Invalid canonical action: {row['action']!r}")
    if row["status"] not in ROW_STATUSES:
        raise ValueError(f"Invalid canonical row status: {row['status']!r}")
    if not isinstance(row["key"], Mapping) or not row["key"]:
        raise ValueError("Canonical row key must be a non-empty object.")
    if not isinstance(row["values"], Mapping):
        raise ValueError("Canonical row values must be an object.")
    result = dict(row)
    result["evidenceDependencies"] = normalize_dependencies(row["evidenceDependencies"])
    expected = derivation_version(row["semanticSignature"], result["evidenceDependencies"])
    if row["derivationVersion"] != expected:
        raise ValueError("Canonical derivationVersion does not match declared dependencies.")
    return result


def build_manifest(
    authority: Mapping[str, Any],
    comparator_semantic_sha: str,
    queue_subject_fingerprint: str,
    resolution_semantic_sha: str,
    rows: Iterable[Mapping[str, Any]],
    *,
    coverage: Iterable[Mapping[str, Any]] = (),
    model_modes: Mapping[str, str] | None = None,
    evidence_partitions: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    normalized = sorted(
        (_validate_manifest_row(row) for row in rows),
        key=lambda item: (item["model"], item["family"], item["sheet"], canonical_text(item["key"])),
    )
    workbook_keys = [
        (item["sheet"], canonical_text(item["key"]))
        for item in normalized
    ]
    if len(workbook_keys) != len(set(workbook_keys)):
        duplicates = sorted({key for key in workbook_keys if workbook_keys.count(key) > 1})
        raise ValueError(f"Duplicate canonical workbook keys: {duplicates[:5]}")
    semantic_payload = {
        "schemaVersion": CANONICAL_ROWS_SCHEMA,
        "rows": normalized,
        "coverage": list(coverage),
        "modelModes": dict(model_modes or {}),
    }
    return {
        "schemaVersion": CANONICAL_ROWS_SCHEMA,
        "runAuthorityFingerprint": _authority_envelope(authority),
        "comparatorEvidenceSemanticSha": str(comparator_semantic_sha),
        "queueSubjectFingerprint": str(queue_subject_fingerprint),
        "resolutionSemanticSha": str(resolution_semantic_sha),
        "manifestSemanticSha": semantic_hash(semantic_payload),
        "rows": normalized,
        "coverage": list(coverage),
        "modelModes": dict(model_modes or {}),
        **dict(evidence_partitions or {}),
    }


def _validate_model_readiness(models: Mapping[str, Mapping[str, Any]]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for model, entry in sorted(models.items()):
        missing = [field for field in READINESS_FIELDS if field not in entry]
        if missing:
            raise ValueError(f"Compile readiness for {model} is missing: {', '.join(missing)}")
        blockers = entry.get("blockers")
        if not isinstance(blockers, list):
            raise ValueError(f"Compile readiness blockers for {model} must be a list.")
        if entry.get("compileReady") is True and blockers:
            raise ValueError(f"Compile readiness for {model} contradicts its blocker list.")
        item = dict(entry)
        item["planReady"] = False
        item["writeReady"] = False
        item["deploymentReady"] = False
        result[str(model)] = item
    return result


def build_compile_report(
    authority: Mapping[str, Any],
    comparator_semantic_sha: str,
    queue_subject_fingerprint: str,
    resolution_semantic_sha: str,
    manifest_semantic_sha: str,
    models: Mapping[str, Mapping[str, Any]],
    source_feature_coverage: Iterable[Mapping[str, Any]],
    deferrals: Iterable[Mapping[str, Any]],
    *,
    family_counts: Mapping[str, Any] | None = None,
    manifest_counts: Mapping[str, Any] | None = None,
    incoming_reference_impact: Mapping[str, Any] | None = None,
    comparator_dispositions: Iterable[Mapping[str, Any]] = (),
    family_coverage: Iterable[Mapping[str, Any]] = (),
) -> dict[str, Any]:
    readiness = _validate_model_readiness(models)
    normalized_source_coverage = sorted(
        (dict(item) for item in source_feature_coverage), key=canonical_text
    )
    normalized_family_coverage = sorted(
        (dict(item) for item in family_coverage), key=canonical_text
    )
    for model, entry in readiness.items():
        if not entry.get("compileReady"):
            continue
        contradictory = any(
            item.get("model") in {model, "*"}
            and item.get("disposition") in {"unsupported_blocker", "exception_open"}
            for item in normalized_source_coverage
        ) or any(
            item.get("model") in {model, "*"}
            and item.get("disposition") == "unsupported_blocker"
            for item in normalized_family_coverage
        )
        if contradictory:
            raise ValueError(f"Compile readiness for {model} contradicts blocking coverage.")
    semantic_payload = {
        "schemaVersion": COMPILE_REPORT_SCHEMA,
        "models": readiness,
        "sourceFeatureCoverage": normalized_source_coverage,
        "deferrals": sorted((dict(item) for item in deferrals), key=canonical_text),
        "familyCounts": dict(family_counts or {}),
        "manifestCounts": dict(manifest_counts or {}),
        "incomingReferenceImpact": dict(incoming_reference_impact or {}),
        "comparatorDispositions": sorted((dict(item) for item in comparator_dispositions), key=canonical_text),
        "familyCoverage": normalized_family_coverage,
    }
    return {
        "schemaVersion": COMPILE_REPORT_SCHEMA,
        "runAuthorityFingerprint": _authority_envelope(authority),
        "comparatorEvidenceSemanticSha": str(comparator_semantic_sha),
        "queueSubjectFingerprint": str(queue_subject_fingerprint),
        "resolutionSemanticSha": str(resolution_semantic_sha),
        "manifestSemanticSha": str(manifest_semantic_sha),
        "compileReportSemanticSha": semantic_hash(semantic_payload),
        **semantic_payload,
    }


def validate_artifact_graph(
    manifest: Mapping[str, Any],
    report: Mapping[str, Any],
    comparator: Mapping[str, Any] | None = None,
    queue: Mapping[str, Any] | None = None,
    resolutions: Mapping[str, Any] | None = None,
) -> None:
    if manifest.get("schemaVersion") != CANONICAL_ROWS_SCHEMA:
        raise ValueError("Expected canonical-rows-1 manifest.")
    if report.get("schemaVersion") != COMPILE_REPORT_SCHEMA:
        raise ValueError("Expected compile-report-1.")
    artifacts = [manifest, report]
    if comparator is not None:
        artifacts.append(comparator)
    if queue is not None:
        artifacts.append(queue)
    authority_envelope = _authority_envelope(manifest.get("runAuthorityFingerprint") or {})
    authority = canonical_text(authority_envelope)
    if not authority or any(
        canonical_text(_authority_envelope(artifact.get("runAuthorityFingerprint") or {})) != authority
        for artifact in artifacts
    ):
        raise ValueError("Artifact graph contains mixed runAuthorityFingerprint envelopes.")
    normalized_rows = sorted(
        (_validate_manifest_row(row) for row in manifest.get("rows") or []),
        key=lambda item: (item["model"], item["family"], item["sheet"], canonical_text(item["key"])),
    )
    evidence_identities: dict[str, str] = {}

    def record_evidence_identities(items: Iterable[Mapping[str, Any]]) -> None:
        for item in items:
            for dependency in item.get("evidenceDependencies") or []:
                evidence_id = str(dependency.get("evidenceId") or "")
                fingerprint = str(dependency.get("semanticFingerprint") or "")
                previous = evidence_identities.setdefault(evidence_id, fingerprint)
                if previous != fingerprint:
                    raise ValueError(
                        f"Conflicting evidence identity {evidence_id}: "
                        f"{previous} != {fingerprint}."
                    )

    record_evidence_identities(normalized_rows)
    from corvette_form_generator.editor_ops import EDITOR_SHEET_META

    for row in normalized_rows:
        metadata = EDITOR_SHEET_META.get(str(row.get("family") or ""), {})
        values = row["values"]
        for column, kind in metadata.get("types", {}).items():
            value = values.get(column)
            if value in (None, ""):
                continue
            if kind == "bool" and not isinstance(value, bool):
                raise ValueError(f"Canonical Boolean {row['sheet']}.{column} is not typed.")
            if kind == "int" and (isinstance(value, bool) or not isinstance(value, int)):
                raise ValueError(f"Canonical integer {row['sheet']}.{column} is not typed.")
        for column, allowed in metadata.get("enums", {}).items():
            value = values.get(column)
            if value in (None, "") and "" in allowed:
                continue
            if value not in allowed:
                raise ValueError(f"Canonical enum {row['sheet']}.{column} is invalid: {value!r}.")
    manifest_payload = {
        "schemaVersion": CANONICAL_ROWS_SCHEMA,
        "rows": normalized_rows,
        "coverage": list(manifest.get("coverage") or []),
        "modelModes": dict(manifest.get("modelModes") or {}),
    }
    if manifest.get("manifestSemanticSha") != semantic_hash(manifest_payload):
        raise ValueError("Canonical manifest semantic hash mismatch.")
    report_payload = {
        field: report.get(field)
        for field in (
            "schemaVersion",
            "models",
            "sourceFeatureCoverage",
            "deferrals",
            "familyCounts",
            "manifestCounts",
            "incomingReferenceImpact",
            "comparatorDispositions",
            "familyCoverage",
        )
    }
    if report.get("compileReportSemanticSha") != semantic_hash(report_payload):
        raise ValueError("Compile report semantic hash mismatch.")
    for model, readiness in (report.get("models") or {}).items():
        if not readiness.get("compileReady"):
            continue
        contradictory = bool(readiness.get("blockers")) or any(
            row.get("status") == "blocked" and row.get("model") in {model, "*"}
            for row in normalized_rows
        )
        contradictory = contradictory or any(
            item.get("model") in {model, "*"}
            and item.get("disposition") in {"unsupported_blocker", "exception_open"}
            for item in report.get("sourceFeatureCoverage") or []
        )
        contradictory = contradictory or any(
            item.get("model") in {model, "*"}
            and item.get("disposition") == "unsupported_blocker"
            for item in report.get("familyCoverage") or []
        )
        if contradictory:
            raise ValueError(f"Compile readiness for {model} contradicts blocking evidence.")
    if report.get("manifestSemanticSha") != manifest.get("manifestSemanticSha"):
        raise ValueError("Compile report does not bind the current canonical manifest.")
    for field in ("comparatorEvidenceSemanticSha", "queueSubjectFingerprint", "resolutionSemanticSha"):
        if report.get(field) != manifest.get(field):
            raise ValueError(f"Artifact graph mismatch for {field}.")
    if comparator is not None:
        from corvette_form_generator.ingest.wizard.comparator_evidence import validate_comparator_artifact

        validate_comparator_artifact(comparator)
        if manifest.get("comparatorEvidenceSemanticSha") != comparator.get("comparatorEvidenceSemanticSha"):
            raise ValueError("Manifest does not bind the current comparator evidence.")
        expected_comparator_partitions = {
            str(target): str(entry.get("comparatorEvidenceFingerprint") or "")
            for target, entry in sorted((comparator.get("targets") or {}).items())
        }
        if manifest.get("comparatorEvidenceFingerprint") != expected_comparator_partitions:
            raise ValueError("Manifest comparator evidence partitions are invalid.")
    normalized_subjects: list[dict[str, Any]] = []
    if queue is not None:
        from corvette_form_generator.ingest.wizard.exceptions import validate_subject_action_contract

        forbidden_queue_fields = {
            "resolutionSemanticSha",
            "entries",
            "validEntries",
            "staleEntries",
            "supersededEntries",
            "deferrals",
        }
        if forbidden_queue_fields.intersection(queue):
            raise ValueError("Exception queue may not depend on resolution state.")
        normalized_subjects = sorted(
            (_validate_subject(subject) for subject in queue.get("subjects") or []),
            key=lambda item: item["subjectId"],
        )
        record_evidence_identities(normalized_subjects)
        for subject in normalized_subjects:
            validate_subject_action_contract(subject["reasonCode"], subject["allowedActions"])
        expected_queue_sha = semantic_hash(
            {"schemaVersion": EXCEPTION_QUEUE_SCHEMA, "subjects": normalized_subjects}
        )
        if queue.get("queueSubjectFingerprint") != expected_queue_sha:
            raise ValueError("Exception queue semantic hash mismatch.")
        if manifest.get("queueSubjectFingerprint") != queue.get("queueSubjectFingerprint"):
            raise ValueError("Manifest does not bind the current exception queue.")
        if queue.get("comparatorEvidenceSemanticSha") != manifest.get("comparatorEvidenceSemanticSha"):
            raise ValueError("Exception queue does not bind the current comparator evidence.")
        forbidden = {"resolutionSemanticSha", "validEntries", "staleEntries", "supersededEntries"}
        if any(key in forbidden for subject in queue.get("subjects") or [] for key in subject):
            raise ValueError("Queue subjects may not contain resolution state.")
        for field in (
            "targetEvidenceFingerprint",
            "comparatorEvidenceFingerprint",
            "phraseEvidenceFingerprint",
            "workbookEvidenceFingerprint",
        ):
            if queue.get(field) != manifest.get(field):
                raise ValueError(f"Artifact graph mismatch for {field} partitions.")
    if resolutions is not None:
        if queue is None:
            raise ValueError("Resolution validation requires the current exception queue.")
        from corvette_form_generator.ingest.wizard.exceptions import classify_resolutions

        valid_entries = list(resolutions.get("validEntries") or [])
        classified = classify_resolutions(valid_entries, normalized_subjects)
        if classified["stale"] or classified["superseded"]:
            raise ValueError("Resolution artifact contains entries that are not current for this queue.")
        if resolutions.get("entries") != resolutions.get("validEntries"):
            raise ValueError("Resolution entries and validEntries must be identical.")
        semantic_entries = [
            {
                "subjectId": entry.get("subjectId"),
                "subjectVersion": entry.get("subjectVersion"),
                "action": entry.get("action"),
                "payload": entry.get("payload") or {},
                "disposition": entry.get("disposition"),
            }
            for entry in sorted(
                classified["valid"],
                key=lambda item: str(item.get("subjectId") or ""),
            )
        ]
        expected_resolution_sha = semantic_hash(
            {"schemaVersion": resolutions.get("schemaVersion"), "entries": semantic_entries}
        )
        if resolutions.get("resolutionSemanticSha") != expected_resolution_sha:
            raise ValueError("Resolution artifact semantic hash mismatch.")
        if resolutions.get("queueSubjectFingerprint") != manifest.get("queueSubjectFingerprint"):
            raise ValueError("Resolutions do not bind the current exception queue.")
        if resolutions.get("resolutionSemanticSha") != manifest.get("resolutionSemanticSha"):
            raise ValueError("Manifest does not bind the current resolutions.")
