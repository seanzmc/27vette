"""Read-only payload builder for ingest review wizard artifacts."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any
from urllib.parse import unquote

ALLOWED_FAMILIES = {"options", "ovs", "rules", "price_rules", "unresolved"}
FAMILY_FILES = {
    "options": "candidate-options.json",
    "ovs": "candidate-ovs.json",
    "rules": "candidate-rules.json",
    "price_rules": "candidate-price-rules.json",
}
EVIDENCE_FILES = [
    "source-layout.json",
    "variant-matrix.json",
    "raw-rows.json",
    "disclosure-links.json",
    "manifest.json",
]
CANDIDATE_FILES = [
    "candidate-options.json",
    "candidate-ovs.json",
    "candidate-rules.json",
    "candidate-price-rules.json",
    "candidate-summary.json",
    "unresolved-review.json",
    "unresolved-review.md",
]
INTERPRETATION_FILES = [
    "interpretation-summary.json",
    "interpreted-options.json",
    "review-queue.json",
    "duplicate-rpo-report.json",
    "source-sheet-coverage.json",
    "blocked-interpretation.json",
]
# Legacy Pass 2/4 review states. Keep accepting them for backward-compatible
# review exports, but do not treat them as the next ingest direction. Pass 5
# replaces the primary reviewer vocabulary with concrete workbook-destination
# actions and a new export version.
ALLOWED_DECISION_STATES = {
    "accept_for_later_apply",
    "edit_before_apply",
    "skip",
    "needs_source_review",
    "blocked_out_of_scope",
}


class IngestReviewStore:
    """Load Pass 0/1 and optional Pass 3 artifacts for UI-friendly read-only views."""

    def __init__(
        self,
        *,
        evidence_dir: Path,
        candidates_dir: Path,
        workbook_path: Path,
        workbook_mtime_ns: int | str,
        interpretation_dir: Path | None = None,
    ) -> None:
        self.evidence_dir = Path(evidence_dir)
        self.candidates_dir = Path(candidates_dir)
        self.interpretation_dir = Path(interpretation_dir) if interpretation_dir else None
        self.workbook_path = Path(workbook_path)
        self.workbook_mtime_ns = str(workbook_mtime_ns)
        self._loaded: dict[str, Any] | None = None

    def summary(self) -> dict[str, Any]:
        loaded = self._load()
        interpretation_enabled = loaded["interpretation_enabled"]
        return {
            "enabled": True,
            "mode": "interpretation" if interpretation_enabled else "raw_candidates",
            "interpretation_enabled": interpretation_enabled,
            "workbook": {
                "path": str(self.workbook_path),
                "mtimeNs": self.workbook_mtime_ns,
            },
            "evidence_dir": str(self.evidence_dir),
            "candidates_dir": str(self.candidates_dir),
            "interpretation_dir": str(self.interpretation_dir) if self.interpretation_dir else "",
            "evidence_artifacts": loaded["evidence_artifacts"],
            "candidate_artifacts": loaded["candidate_artifacts"],
            "interpretation_artifacts": loaded.get("interpretation_artifacts", {}),
            "candidate_summary": loaded["candidate_summary"],
            "candidate_counts": loaded["candidate_summary"].get("candidate_counts", {}),
            "unresolved_counts": loaded["unresolved_review"].get("unresolved_counts", {}),
            "interpretation_summary": loaded.get("interpretation_summary", {}),
            "families": ["options", "ovs", "rules", "price_rules", "unresolved"],
        }

    def list_candidates(
        self,
        *,
        family: str = "options",
        status: str = "",
        model: str = "",
        reason: str = "",
        q: str = "",
        offset: int = 0,
        limit: int = 200,
    ) -> dict[str, Any]:
        family = family or "options"
        if family not in ALLOWED_FAMILIES:
            raise ValueError(f"unknown ingest candidate family: {family}")
        rows = self._family_rows(family)
        filtered = [
            row for row in rows
            if self._row_matches(row, family=family, status=status, model=model, reason=reason, q=q)
        ]
        limit = max(1, min(int(limit or 200), 500))
        offset = max(0, int(offset or 0))
        return {
            "family": family,
            "total": len(filtered),
            "offset": offset,
            "limit": limit,
            "items": filtered[offset:offset + limit],
        }

    def candidate(self, candidate_id: str) -> dict[str, Any]:
        candidate_id = unquote(candidate_id)
        for family in FAMILY_FILES:
            for row in self._family_rows(family):
                if row.get("candidate_id") == candidate_id:
                    return row
        raise KeyError(f"unknown candidate_id: {candidate_id}")

    def unresolved(self, unresolved_id: str) -> dict[str, Any]:
        unresolved_id = unquote(unresolved_id)
        for row in self._family_rows("unresolved"):
            if row.get("unresolved_id") == unresolved_id:
                return row
        raise KeyError(f"unknown unresolved_id: {unresolved_id}")

    def list_interpretations(
        self,
        *,
        confidence: str = "",
        model: str = "",
        reason: str = "",
        duplicate: str = "",
        q: str = "",
        include_auto: bool = False,
        offset: int = 0,
        limit: int = 200,
    ) -> dict[str, Any]:
        loaded = self._require_interpretation()
        rows = loaded["interpretation"]["interpreted-options.json"]
        filtered = [
            row for row in rows
            if self._interpretation_matches(
                row,
                confidence=confidence,
                model=model,
                reason=reason,
                duplicate=duplicate,
                q=q,
                include_auto=include_auto,
            )
        ]
        limit = max(1, min(int(limit or 200), 500))
        offset = max(0, int(offset or 0))
        return {
            "mode": "interpretation",
            "total": len(filtered),
            "offset": offset,
            "limit": limit,
            "include_auto": include_auto,
            "items": filtered[offset:offset + limit],
        }

    def interpretation(self, interpretation_id: str) -> dict[str, Any]:
        interpretation_id = unquote(interpretation_id)
        loaded = self._require_interpretation()
        for row in loaded["interpretation"]["interpreted-options.json"]:
            if row.get("interpretation_id") == interpretation_id:
                return row
        raise KeyError(f"unknown interpretation_id: {interpretation_id}")

    def interpretation_reports(self) -> dict[str, Any]:
        loaded = self._require_interpretation()
        return {
            "duplicates": loaded["interpretation"]["duplicate-rpo-report.json"],
            "source_coverage": loaded["interpretation"]["source-sheet-coverage.json"],
            "blocked": loaded["interpretation"]["blocked-interpretation.json"],
        }

    def source(self, *, sheet: str, row: int) -> dict[str, Any]:
        loaded = self._load()
        sheet = unquote(sheet)
        row = int(row)
        raw_row = next(
            (
                item for item in loaded["evidence"]["raw-rows.json"]
                if item.get("source_sheet") == sheet and item.get("source_row_index") == row
            ),
            None,
        )
        if raw_row is None:
            raise KeyError(f"unknown source row: {sheet} row {row}")
        disclosures = [
            item for item in loaded["evidence"]["disclosure-links.json"]
            if item.get("source_sheet") == sheet and item.get("source_row_index") == row
        ]
        layout = next(
            (item for item in loaded["evidence"]["source-layout.json"] if item.get("source_sheet") == sheet),
            None,
        )
        return {"row": raw_row, "disclosures": disclosures, "layout": layout}

    def _family_rows(self, family: str) -> list[dict[str, Any]]:
        loaded = self._load()
        if family == "unresolved":
            return loaded["unresolved_review"].get("items", [])
        return loaded["candidates"][FAMILY_FILES[family]]

    def _row_matches(
        self,
        row: dict[str, Any],
        *,
        family: str,
        status: str,
        model: str,
        reason: str,
        q: str,
    ) -> bool:
        if status and row.get("resolution_status") != status:
            return False
        if reason and row.get("reason") != reason:
            return False
        if model and not _contains_model(row, model):
            return False
        if q and q.lower() not in json.dumps(row, ensure_ascii=False).lower():
            return False
        return True

    def _interpretation_matches(
        self,
        row: dict[str, Any],
        *,
        confidence: str,
        model: str,
        reason: str,
        duplicate: str,
        q: str,
        include_auto: bool,
    ) -> bool:
        if not include_auto and row.get("interpretation_confidence") == "auto_confirmed":
            return False
        if confidence and row.get("interpretation_confidence") != confidence:
            return False
        if model and row.get("model_key") != model:
            return False
        if reason and reason not in (row.get("review_reason_codes") or []):
            return False
        if duplicate and row.get("duplicate_classification") != duplicate:
            return False
        if q and q.lower() not in json.dumps(row, ensure_ascii=False).lower():
            return False
        return True

    def _require_interpretation(self) -> dict[str, Any]:
        loaded = self._load()
        if not loaded["interpretation_enabled"]:
            raise ValueError("No ingest interpretation directory configured.")
        return loaded

    def _load(self) -> dict[str, Any]:
        if self._loaded is not None:
            return self._loaded
        evidence = {name: _read_json(self.evidence_dir / name) for name in EVIDENCE_FILES}
        candidates = {name: _read_json(self.candidates_dir / name) for name in FAMILY_FILES.values()}
        candidate_summary = _read_json(self.candidates_dir / "candidate-summary.json")
        unresolved_review = _read_json(self.candidates_dir / "unresolved-review.json")
        _validate_unresolved_review(unresolved_review)
        interpretation: dict[str, Any] | None = None
        interpretation_artifacts: dict[str, dict[str, Any]] = {}
        if self.interpretation_dir is not None:
            interpretation = {name: _read_json(self.interpretation_dir / name) for name in INTERPRETATION_FILES}
            _validate_interpretation_artifacts(interpretation)
            interpretation_artifacts = artifact_fingerprints(self.interpretation_dir, INTERPRETATION_FILES)
        self._loaded = {
            "evidence": evidence,
            "candidates": candidates,
            "candidate_summary": candidate_summary,
            "unresolved_review": unresolved_review,
            "evidence_artifacts": artifact_fingerprints(self.evidence_dir, EVIDENCE_FILES),
            "candidate_artifacts": artifact_fingerprints(self.candidates_dir, CANDIDATE_FILES),
            "interpretation_enabled": interpretation is not None,
            "interpretation": interpretation or {},
            "interpretation_summary": (interpretation or {}).get("interpretation-summary.json", {}),
            "interpretation_artifacts": interpretation_artifacts,
        }
        return self._loaded


def disabled_summary(message: str = "No ingest evidence/candidate directories configured.") -> dict[str, Any]:
    return {"enabled": False, "message": message, "mode": "disabled", "interpretation_enabled": False}


def artifact_fingerprints(directory: Path, filenames: list[str]) -> dict[str, dict[str, Any]]:
    fingerprints: dict[str, dict[str, Any]] = {}
    for name in filenames:
        path = directory / name
        if not path.exists():
            raise ValueError(f"Missing ingest artifact: {path}")
        stat = path.stat()
        fingerprints[name] = {
            "path": str(path),
            "mtime_ns": str(stat.st_mtime_ns),
            "size_bytes": stat.st_size,
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        }
    return fingerprints


def validate_review_decisions(payload: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    for index, decision in enumerate(payload.get("interpretation_decisions") or []):
        ctx = f"interpretation_decisions[{index}]"
        if decision.get("decision_state") not in ALLOWED_DECISION_STATES:
            errors.append(f"{ctx}: invalid decision_state")
        for key in (
            "interpretation_id",
            "model_key",
            "rpo",
            "interpretation_confidence",
            "duplicate_classification_snapshot",
        ):
            if not decision.get(key):
                errors.append(f"{ctx}: missing {key}")
        if not decision.get("source_occurrences_snapshot"):
            errors.append(f"{ctx}: missing source_occurrences_snapshot")
        if "workbook_identity_match_snapshot" not in decision:
            errors.append(f"{ctx}: missing workbook_identity_match_snapshot")
        if "workbook_status_match_snapshot" not in decision:
            errors.append(f"{ctx}: missing workbook_status_match_snapshot")
    for index, decision in enumerate(payload.get("decisions") or []):
        ctx = f"decisions[{index}]"
        if decision.get("decision_state") not in ALLOWED_DECISION_STATES:
            errors.append(f"{ctx}: invalid decision_state")
        if not decision.get("candidate_id"):
            errors.append(f"{ctx}: missing candidate_id")
        if not decision.get("candidate_family"):
            errors.append(f"{ctx}: missing candidate_family")
        if not decision.get("source_refs"):
            errors.append(f"{ctx}: missing source_refs")
    for index, decision in enumerate(payload.get("unresolved_decisions") or []):
        ctx = f"unresolved_decisions[{index}]"
        if decision.get("decision_state") not in ALLOWED_DECISION_STATES:
            errors.append(f"{ctx}: invalid decision_state")
        if not decision.get("unresolved_id"):
            errors.append(f"{ctx}: missing unresolved_id")
        if not decision.get("reason"):
            errors.append(f"{ctx}: missing reason")
        if not decision.get("category"):
            errors.append(f"{ctx}: missing category")
        if not decision.get("source_refs"):
            errors.append(f"{ctx}: missing source_refs")
    return {"ok": not errors, "errors": errors, "warnings": []}


def _contains_model(row: dict[str, Any], model: str) -> bool:
    normalized = row.get("normalized_values") or {}
    models = normalized.get("model_key_candidates") or []
    return (
        normalized.get("model_key") == model
        or (isinstance(models, list) and model in models)
        or ((row.get("workbook_match") or {}).get("model_key") == model)
    )


def _read_json(path: Path) -> Any:
    if not path.exists():
        raise ValueError(f"Missing ingest artifact: {path}")
    return json.loads(path.read_text())


def _validate_unresolved_review(payload: dict[str, Any]) -> None:
    if payload.get("version") != 1:
        raise ValueError("unresolved-review.json must have version 1")
    if not isinstance(payload.get("items"), list):
        raise ValueError("unresolved-review.json missing items list")
    for index, item in enumerate(payload["items"], start=1):
        required = {
            "unresolved_id",
            "reason",
            "category",
            "severity",
            "candidate_refs",
            "source_refs",
            "raw_values",
            "normalized_values",
            "blocked_decision",
            "suggested_decision_states",
        }
        missing = sorted(required - set(item))
        if missing:
            raise ValueError(f"unresolved-review.json item {index} missing keys: {missing}")


def _validate_interpretation_artifacts(artifacts: dict[str, Any]) -> None:
    summary = artifacts["interpretation-summary.json"]
    if summary.get("version") != 1:
        raise ValueError("interpretation-summary.json must have version 1")
    interpreted = artifacts["interpreted-options.json"]
    if not isinstance(interpreted, list):
        raise ValueError("interpreted-options.json must be a list")
    for index, item in enumerate(interpreted, start=1):
        required = {
            "interpretation_id",
            "model_key",
            "rpo",
            "interpretation_confidence",
            "duplicate_classification",
            "source_occurrences",
            "availability_matrix",
            "workbook_identity_match",
            "workbook_status_match",
            "review_reason_codes",
        }
        missing = sorted(required - set(item))
        if missing:
            raise ValueError(f"interpreted-options.json item {index} missing keys: {missing}")
