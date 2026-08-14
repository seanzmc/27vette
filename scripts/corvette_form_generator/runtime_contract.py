"""Model-neutral runtime-contract finalization and validation."""

from __future__ import annotations

import json
from typing import Any

from corvette_form_generator.model_config import ModelConfig

DRAFT_ONLY_TOP_LEVEL_FIELDS = ("draftMetadata", "_derivationManifest")
DRAFT_ONLY_CHOICE_FIELDS = ("source_option_name", "source_description", "text_cleanup_notes")
DRAFT_ONLY_PROVENANCE_FIELDS = (
    "copy_from_model_key",
    "suggested_copy_from",
    "raw_source_sheet",
    "raw_source_sheets",
    "review_status",
    "review_flags",
)
DRAFT_ONLY_LIVE_CONTRACT_FIELDS = frozenset(
    (*DRAFT_ONLY_TOP_LEVEL_FIELDS, *DRAFT_ONLY_CHOICE_FIELDS, *DRAFT_ONLY_PROVENANCE_FIELDS)
)
RUNTIME_CHOICE_ROW_TRIM_FIELDS = frozenset(
    ("source_detail_raw", "choice_mode", "selection_mode", "selection_mode_label")
)
RUNTIME_STANDARD_EQUIPMENT_ROW_TRIM_FIELDS = frozenset(("source_detail_raw",))
REQUIRED_RUNTIME_LIST_FIELDS = (
    "variants",
    "steps",
    "sections",
    "contextChoices",
    "choices",
    "standardEquipment",
    "ruleGroups",
    "exclusiveGroups",
    "rules",
    "priceRules",
    "interiors",
    "colorOverrides",
    "defaultSelectionRules",
    "validation",
)
REQUIRED_NON_EMPTY_RUNTIME_LIST_FIELDS = frozenset(("variants", "steps", "sections", "contextChoices", "choices"))
VALID_VALIDATION_SEVERITIES = frozenset(("pass", "info", "warning", "error"))


def validation_severity_count(rows: Any, severity: str) -> int:
    """Count validation rows carrying one severity."""

    if not isinstance(rows, list):
        return 0
    wanted = severity.strip().lower()
    return sum(
        1 for row in rows if isinstance(row, dict) and str(row.get("severity", "")).strip().lower() == wanted
    )


def validation_error_count(rows: Any) -> int:
    return validation_severity_count(rows, "error")


def _runtime_payload_trim_fields(path: tuple[str, ...]) -> frozenset[str]:
    if path == ("choices", "[]"):
        return RUNTIME_CHOICE_ROW_TRIM_FIELDS
    if path == ("standardEquipment", "[]"):
        return RUNTIME_STANDARD_EQUIPMENT_ROW_TRIM_FIELDS
    return frozenset()


def _strip_live_contract_provenance(value: Any, path: tuple[str, ...] = ()) -> Any:
    if isinstance(value, dict):
        runtime_payload_fields = _runtime_payload_trim_fields(path)
        return {
            key: _strip_live_contract_provenance(child, (*path, key))
            for key, child in value.items()
            if key not in DRAFT_ONLY_LIVE_CONTRACT_FIELDS and key not in runtime_payload_fields
        }
    if isinstance(value, list):
        return [_strip_live_contract_provenance(item, (*path, "[]")) for item in value]
    return value


def _json_path_parts(path: str) -> tuple[str, ...]:
    if path == "$":
        return ()
    parts: list[str] = []
    for part in path.removeprefix("$.").split("."):
        if "[" in part and part.endswith("]"):
            name = part.split("[", 1)[0]
            if name:
                parts.append(name)
            parts.append("[]")
        else:
            parts.append(part)
    return tuple(parts)


def find_draft_only_fields(value: Any, path: str = "$") -> list[str]:
    """Return JSON paths of fields that must not ship in a runtime contract."""

    leaks: list[str] = []
    path_parts = _json_path_parts(path)
    if isinstance(value, dict):
        runtime_payload_fields = _runtime_payload_trim_fields(path_parts)
        for key, child in value.items():
            child_path = f"{path}.{key}"
            if key in DRAFT_ONLY_LIVE_CONTRACT_FIELDS or key in runtime_payload_fields:
                leaks.append(child_path)
            else:
                leaks.extend(find_draft_only_fields(child, child_path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            leaks.extend(find_draft_only_fields(child, f"{path}[{index}]"))
    return leaks


def assert_runtime_contract(
    data: dict[str, Any],
    *,
    source: str,
    config: ModelConfig | None = None,
    expected_model_label: str | None = None,
) -> None:
    """Reject malformed, incomplete, draft, or error-bearing runtime payloads."""

    problems: list[str] = []
    if not isinstance(data, dict) or not data:
        problems.append("payload must be a non-empty object")
        data = {}

    leaks = find_draft_only_fields(data)
    if leaks:
        problems.append(f"draft-only fields present: {', '.join(leaks[:5])}{'...' if len(leaks) > 5 else ''}")

    dataset = data.get("dataset")
    if not isinstance(dataset, dict):
        problems.append("dataset must be an object")
        dataset = {}
    for field in ("name", "model", "model_year"):
        if not isinstance(dataset.get(field), str) or not str(dataset.get(field)).strip():
            problems.append(f"dataset.{field} must be a non-empty string")
    if dataset.get("status") != "runtime_active":
        problems.append(f"dataset.status is {dataset.get('status')!r}, expected 'runtime_active'")
    if config is not None:
        expected = {
            "name": config.dataset_name,
            "model": config.model_label,
            "model_year": config.model_year,
        }
        for field, value in expected.items():
            if dataset.get(field) != value:
                problems.append(f"dataset.{field} is {dataset.get(field)!r}, expected {value!r}")
    if expected_model_label is not None and dataset.get("model") != expected_model_label:
        problems.append(f"dataset.model is {dataset.get('model')!r}, expected {expected_model_label!r}")

    for field in REQUIRED_RUNTIME_LIST_FIELDS:
        rows = data.get(field)
        if not isinstance(rows, list):
            problems.append(f"{field} must be a list")
        elif any(not isinstance(row, dict) for row in rows):
            problems.append(f"{field} must contain only objects")
        elif field in REQUIRED_NON_EMPTY_RUNTIME_LIST_FIELDS and not rows:
            problems.append(f"{field} must not be empty")
    if not isinstance(data.get("orderSummary"), dict):
        problems.append("orderSummary must be an object")

    validation = data.get("validation")
    if isinstance(validation, list):
        invalid_severities = sorted(
            {
                str(row.get("severity", "")).strip()
                for row in validation
                if isinstance(row, dict) and str(row.get("severity", "")).strip() not in VALID_VALIDATION_SEVERITIES
            }
        )
        if invalid_severities:
            problems.append(f"validation contains invalid severities: {invalid_severities!r}")
        error_count = validation_error_count(validation)
        if error_count:
            problems.append(f"contains {error_count} error-severity validation finding(s)")

    if problems:
        raise ValueError(
            f"Runtime contract {source} is not publishable ({'; '.join(problems)}). "
            "Correct the workbook/source generation error and regenerate it."
        )


def live_contract_data(data: dict[str, Any]) -> dict[str, Any]:
    """Return a deep-cleaned runtime payload without asserting completeness."""

    cleaned = _strip_live_contract_provenance(json.loads(json.dumps(data)))
    dataset = cleaned.get("dataset")
    if isinstance(dataset, dict) and dataset.get("status") == "draft_not_runtime_active":
        dataset["status"] = "runtime_active"
        name = dataset.get("name")
        if isinstance(name, str):
            dataset["name"] = name.replace(" form data draft", " operational form")
    validation = cleaned.get("validation")
    if isinstance(validation, list):
        cleaned["validation"] = [
            row
            for row in validation
            if not (
                isinstance(row, dict)
                and row.get("severity") == "warning"
                and str(row.get("check_id", "")).endswith("_draft_status")
            )
        ]
    return cleaned


def build_model_runtime_contract(config: ModelConfig, data: dict[str, Any]) -> dict[str, Any]:
    """Finalize and strictly validate one model's browser runtime contract."""

    cleaned = live_contract_data(data)
    dataset = cleaned.setdefault("dataset", {})
    if not isinstance(dataset, dict):
        raise ValueError(f"Runtime contract source for {config.model_key} has a non-object dataset")
    dataset.update(
        {
            "name": config.dataset_name,
            "model": config.model_label,
            "model_year": config.model_year,
            "status": "runtime_active",
        }
    )
    assert_runtime_contract(cleaned, source=f"generated {config.model_key}", config=config)
    return cleaned
