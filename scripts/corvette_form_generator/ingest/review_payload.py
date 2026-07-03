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
WORKBOOK_BUILD_FILES = [
    "model-selection.json",
    "workbook-build-summary.json",
    "workbook-build-review-units.json",
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
# Pass 5 focused workbook-build vocabulary. The proposed action names the
# workbook destination/work implied by the unit; the reviewer resolution only
# says whether the reviewer accepts that unit for a later dry-run plan.
ALLOWED_WORKBOOK_BUILD_ACTIONS = {
    "create_option_row",
    "verify_existing_option_row",
    "create_ovs_rows",
    "verify_status_matrix",
    "create_relationship_candidate",
    "classify_duplicate_source",
    "defer_price_extractor",
    "defer_color_trim_extractor",
    "needs_product_decision",
    "needs_source_mapping_decision",
    "ignore_for_selected_models",
    "blocked_unsupported_source_structure",
}
ALLOWED_WORKBOOK_BUILD_RESOLUTIONS = {
    "approved_for_plan",
    "hold_for_question",
    "not_needed",
}
WORKBOOK_BUILD_LANES = {
    "option_rows",
    "ovs_rows",
    "relationships",
    "pricing",
    "duplicates_and_source_coverage",
    "blocked_extractor_gaps",
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
        workbook_build_enabled = loaded["workbook_build_enabled"]
        return {
            "enabled": True,
            "mode": "workbook_build" if workbook_build_enabled else "interpretation" if interpretation_enabled else "raw_candidates",
            "interpretation_enabled": interpretation_enabled,
            "workbook_build_enabled": workbook_build_enabled,
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
            "model_selection": loaded.get("model_selection", {}),
            "workbook_build_summary": loaded.get("workbook_build_summary", {}),
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

    def model_selection(self) -> dict[str, Any]:
        loaded = self._require_workbook_build()
        return loaded["model_selection"]

    def workbook_build_summary(self) -> dict[str, Any]:
        loaded = self._require_workbook_build()
        return loaded["workbook_build_summary"]

    def list_workbook_build_units(
        self,
        *,
        lane: str = "",
        model: str = "",
        action: str = "",
        q: str = "",
        offset: int = 0,
        limit: int = 200,
    ) -> dict[str, Any]:
        loaded = self._require_workbook_build()
        rows = loaded["workbook_build_units"]
        filtered = [
            row for row in rows
            if (not lane or row.get("lane") == lane)
            and (not model or row.get("model_key") == model)
            and (not action or row.get("proposed_workbook_action") == action)
            and (not q or q.lower() in json.dumps(row, ensure_ascii=False).lower())
        ]
        limit = max(1, min(int(limit or 200), 500))
        offset = max(0, int(offset or 0))
        return {
            "mode": "workbook_build",
            "lane": lane,
            "model": model,
            "action": action,
            "total": len(filtered),
            "offset": offset,
            "limit": limit,
            "items": filtered[offset:offset + limit],
        }

    def workbook_build_unit(self, review_unit_id: str) -> dict[str, Any]:
        review_unit_id = unquote(review_unit_id)
        loaded = self._require_workbook_build()
        for row in loaded["workbook_build_units"]:
            if row.get("review_unit_id") == review_unit_id:
                return row
        raise KeyError(f"unknown review_unit_id: {review_unit_id}")

    def validate_workbook_build_decisions(self, payload: dict[str, Any]) -> dict[str, Any]:
        loaded = self._require_workbook_build()
        return validate_workbook_build_decisions(
            payload,
            expected_selection_fingerprint=loaded["workbook_build_summary"].get("selection_fingerprint", ""),
            known_unit_ids={row.get("review_unit_id") for row in loaded["workbook_build_units"]},
        )

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

    def _require_workbook_build(self) -> dict[str, Any]:
        loaded = self._require_interpretation()
        if not loaded["workbook_build_enabled"]:
            raise ValueError("No focused workbook-build artifacts configured.")
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
        workbook_build_enabled = False
        model_selection: dict[str, Any] = {}
        workbook_build_summary: dict[str, Any] = {}
        workbook_build_units: list[dict[str, Any]] = []
        evidence_artifacts = artifact_fingerprints(self.evidence_dir, EVIDENCE_FILES)
        candidates_selection_path = self.candidates_dir / "model-selection.json"
        if self.interpretation_dir is not None:
            interpretation = {name: _read_json(self.interpretation_dir / name) for name in INTERPRETATION_FILES}
            _validate_interpretation_artifacts(interpretation)
            present = [name for name in WORKBOOK_BUILD_FILES if (self.interpretation_dir / name).exists()]
            focused = bool(present) or candidates_selection_path.exists() or bool(candidate_summary.get("selection_metadata"))
            if focused:
                # Fail closed: a focused Pass 5 run must never fall back to the
                # broad all-model review because an artifact is missing.
                missing = [name for name in WORKBOOK_BUILD_FILES if name not in present]
                if missing:
                    raise ValueError(
                        "Focused Pass 5 candidates require workbook-build artifacts; "
                        f"missing from {self.interpretation_dir}: {', '.join(missing)}"
                    )
                if not candidates_selection_path.exists():
                    raise ValueError(
                        f"Missing required focused model-selection.json artifact: {candidates_selection_path}"
                    )
                for name in WORKBOOK_BUILD_FILES:
                    interpretation[name] = _read_json(self.interpretation_dir / name)
                _validate_workbook_build_artifacts(
                    interpretation,
                    candidates_selection=_read_json(candidates_selection_path),
                    candidate_summary=candidate_summary,
                    evidence_artifacts=evidence_artifacts,
                )
                workbook_build_enabled = True
                model_selection = interpretation["model-selection.json"]
                workbook_build_summary = interpretation["workbook-build-summary.json"]
                workbook_build_units = interpretation["workbook-build-review-units.json"]
            artifact_names = INTERPRETATION_FILES + (WORKBOOK_BUILD_FILES if workbook_build_enabled else [])
            interpretation_artifacts = artifact_fingerprints(self.interpretation_dir, artifact_names)
        candidate_artifact_names = CANDIDATE_FILES + (["model-selection.json"] if (self.candidates_dir / "model-selection.json").exists() else [])
        self._loaded = {
            "evidence": evidence,
            "candidates": candidates,
            "candidate_summary": candidate_summary,
            "unresolved_review": unresolved_review,
            "evidence_artifacts": evidence_artifacts,
            "candidate_artifacts": artifact_fingerprints(self.candidates_dir, candidate_artifact_names),
            "interpretation_enabled": interpretation is not None,
            "workbook_build_enabled": workbook_build_enabled,
            "interpretation": interpretation or {},
            "interpretation_summary": (interpretation or {}).get("interpretation-summary.json", {}),
            "interpretation_artifacts": interpretation_artifacts,
            "model_selection": model_selection,
            "workbook_build_summary": workbook_build_summary,
            "workbook_build_units": workbook_build_units,
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


def validate_workbook_build_decisions(
    payload: dict[str, Any],
    *,
    expected_selection_fingerprint: str,
    known_unit_ids: set[str | None],
) -> dict[str, Any]:
    errors: list[str] = []
    if payload.get("version") != 3:
        errors.append("version must be 3")
    if payload.get("review_mode") != "focused_workbook_build":
        errors.append("review_mode must be focused_workbook_build")
    if payload.get("selection_fingerprint") != expected_selection_fingerprint:
        errors.append("selection_fingerprint does not match focused workbook-build artifacts")
    decisions = payload.get("workbook_build_decisions")
    if not isinstance(decisions, list):
        errors.append("workbook_build_decisions must be a list")
        decisions = []
    for index, decision in enumerate(decisions):
        ctx = f"workbook_build_decisions[{index}]"
        if decision.get("reviewer_resolution") not in ALLOWED_WORKBOOK_BUILD_RESOLUTIONS:
            errors.append(f"{ctx}: invalid reviewer_resolution")
        if decision.get("proposed_workbook_action") not in ALLOWED_WORKBOOK_BUILD_ACTIONS:
            errors.append(f"{ctx}: invalid proposed_workbook_action")
        unit_id = decision.get("review_unit_id")
        if not unit_id:
            errors.append(f"{ctx}: missing review_unit_id")
        elif unit_id not in known_unit_ids:
            errors.append(f"{ctx}: unknown review_unit_id")
        for key in ("lane", "model_key", "target_sheet", "workbook_presence_snapshot"):
            if key not in decision:
                errors.append(f"{ctx}: missing {key}")
        if not decision.get("source_refs_snapshot"):
            errors.append(f"{ctx}: missing source_refs_snapshot")
        if "raw_source_snapshot" not in decision:
            errors.append(f"{ctx}: missing raw_source_snapshot")
    return {"ok": not errors, "errors": errors, "warnings": []}


def _validate_workbook_build_artifacts(
    artifacts: dict[str, Any],
    *,
    candidates_selection: dict[str, Any],
    candidate_summary: dict[str, Any],
    evidence_artifacts: dict[str, dict[str, Any]],
) -> None:
    selection = artifacts["model-selection.json"]
    summary = artifacts["workbook-build-summary.json"]
    units = artifacts["workbook-build-review-units.json"]
    if selection.get("version") != 1:
        raise ValueError("model-selection.json must have version 1")
    if not selection.get("selected_models"):
        raise ValueError("model-selection.json missing selected_models")
    if candidates_selection != selection:
        raise ValueError("candidate model-selection.json does not match interpretation model-selection.json")
    if not candidate_summary.get("selection_metadata"):
        raise ValueError("candidate-summary.json is missing selection_metadata for a focused Pass 5 run")
    if candidate_summary["selection_metadata"] != selection:
        raise ValueError("candidate-summary.json selection_metadata does not match model-selection.json")
    for name, expected_sha in (selection.get("evidence_fingerprints") or {}).items():
        if evidence_artifacts.get(name, {}).get("sha256") != expected_sha:
            raise ValueError(f"model-selection.json evidence fingerprint mismatch for {name}")
    if summary.get("version") != 1 or summary.get("review_mode") != "focused_workbook_build":
        raise ValueError("workbook-build-summary.json must be focused_workbook_build version 1")
    if summary.get("selection_metadata") != selection:
        raise ValueError("workbook-build-summary.json selection_metadata does not match model-selection.json")
    if not isinstance(units, list):
        raise ValueError("workbook-build-review-units.json must be a list")
    selected = set(selection.get("selected_models") or [])
    primary = set(selection.get("primary_models") or [])
    comparator = set(selection.get("comparator_models") or [])
    for index, unit in enumerate(units, start=1):
        required = {
            "review_unit_id",
            "lane",
            "model_key",
            "model_role",
            "target_sheet",
            "proposed_workbook_action",
            "workbook_presence",
            "source_refs",
            "raw_source_snapshot",
        }
        missing = sorted(required - set(unit))
        if missing:
            raise ValueError(f"workbook-build-review-units.json item {index} missing keys: {missing}")
        if unit.get("lane") not in WORKBOOK_BUILD_LANES:
            raise ValueError(f"workbook-build-review-units.json item {index} has unknown lane {unit.get('lane')!r}")
        if unit.get("proposed_workbook_action") not in ALLOWED_WORKBOOK_BUILD_ACTIONS:
            raise ValueError(
                f"workbook-build-review-units.json item {index} has unsupported proposed_workbook_action "
                f"{unit.get('proposed_workbook_action')!r}"
            )
        model_key = unit.get("model_key") or ""
        if unit.get("lane") == "blocked_extractor_gaps" and not model_key:
            continue
        if model_key not in selected:
            raise ValueError(
                f"workbook-build-review-units.json item {index} leaks non-selected model {model_key!r}"
            )
        role = unit.get("model_role")
        if model_key in comparator and role != "comparator":
            raise ValueError(
                f"workbook-build-review-units.json item {index} must mark comparator model {model_key!r} as comparator"
            )
        if model_key in primary and role != "primary":
            raise ValueError(
                f"workbook-build-review-units.json item {index} must mark primary model {model_key!r} as primary"
            )
        if role == "comparator":
            target = str(unit.get("target_sheet") or "")
            leaked = next((m for m in primary if target == m or target.startswith(f"{m}_")), None)
            if leaked:
                raise ValueError(
                    f"workbook-build-review-units.json item {index} lets comparator {model_key!r} "
                    f"target primary sheet {target!r} for model {leaked!r}"
                )


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
