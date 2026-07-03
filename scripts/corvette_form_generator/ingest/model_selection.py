"""Selected-model metadata helpers for order-guide ingest."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from corvette_form_generator.workbook import clean

FINGERPRINT_FILES = ["variant-matrix.json", "source-layout.json"]


def parse_model_list(value: str | list[str] | tuple[str, ...] | None) -> list[str]:
    """Normalize comma/space separated model keys into a stable unique list."""

    if value is None:
        return []
    if isinstance(value, str):
        parts = value.replace(";", ",").replace(" ", ",").split(",")
    else:
        parts = []
        for item in value:
            parts.extend(str(item).replace(";", ",").replace(" ", ",").split(","))
    out: list[str] = []
    for part in parts:
        key = clean(part).lower()
        if key and key not in out:
            out.append(key)
    return out


def infer_primary_and_comparator(
    selected_models: list[str],
    primary_models: list[str] | None = None,
    comparator_models: list[str] | None = None,
) -> tuple[list[str], list[str]]:
    """Infer the default ZR1/ZR1X + Z06 focused role split when roles are omitted."""

    selected = list(selected_models)
    primary = [model for model in (primary_models or []) if model in selected]
    comparator = [model for model in (comparator_models or []) if model in selected]
    if primary or comparator:
        if not primary:
            primary = [model for model in selected if model not in comparator]
        if not comparator:
            comparator = [model for model in selected if model not in primary]
        return primary, comparator
    if "z06" in selected and any(model in selected for model in ("zr1", "zr1x")):
        return [model for model in selected if model != "z06"], ["z06"]
    return selected, []


def evidence_fingerprints(evidence_dir: Path) -> dict[str, str]:
    fingerprints: dict[str, str] = {}
    for filename in FINGERPRINT_FILES:
        path = evidence_dir / filename
        if not path.exists():
            raise ValueError(f"Missing required evidence artifact for model selection: {path}")
        fingerprints[filename] = hashlib.sha256(path.read_bytes()).hexdigest()
    return fingerprints


def selection_fingerprint(selection: dict[str, Any]) -> str:
    encoded = json.dumps(selection, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def build_model_selection(
    *,
    evidence_dir: Path,
    variant_matrix: list[dict[str, Any]],
    run_id: str,
    selected_models: str | list[str] | tuple[str, ...],
    primary_models: str | list[str] | tuple[str, ...] | None = None,
    comparator_models: str | list[str] | tuple[str, ...] | None = None,
    selection_source: str = "cli_models_arg",
) -> dict[str, Any]:
    selected = parse_model_list(selected_models)
    if not selected:
        raise ValueError("Focused ingest requires at least one selected model.")
    primary_input = parse_model_list(primary_models)
    comparator_input = parse_model_list(comparator_models)
    primary, comparator = infer_primary_and_comparator(selected, primary_input, comparator_input)
    if sorted(set(primary) | set(comparator)) != sorted(selected):
        raise ValueError("Selected models must be partitioned into primary and comparator models.")

    variant_counts: dict[str, int] = {}
    unmatched_counts: dict[str, int] = {}
    sheet_counts: dict[str, dict[str, int]] = {}
    for row in variant_matrix:
        model = clean(row.get("parsed_target_model")).lower()
        if not model:
            continue
        if row.get("resolution_status") == "matched":
            variant_counts[model] = variant_counts.get(model, 0) + 1
            sheet = clean(row.get("source_sheet"))
            if sheet:
                sheet_counts.setdefault(model, {})[sheet] = sheet_counts.setdefault(model, {}).get(sheet, 0) + 1
        else:
            unmatched_counts[model] = unmatched_counts.get(model, 0) + 1

    available = sorted(set(variant_counts) | set(unmatched_counts))
    for model in selected:
        if model not in variant_counts:
            counts_report = "; ".join(
                f"{key}: matched={variant_counts.get(key, 0)}, unmatched={unmatched_counts.get(key, 0)}"
                for key in available
            ) or "none"
            sheets_report = "; ".join(
                f"{key}: {', '.join(sorted(sheet_counts.get(key, {}))) or 'none'}"
                for key in available
            ) or "none"
            raise ValueError(
                f"Selected model {model} was not found with matched variant columns in variant-matrix.json; "
                f"available models: {', '.join(available) or 'none'}; "
                f"variant counts: {counts_report}; "
                f"source sheets: {sheets_report}"
            )
        if variant_counts[model] <= 0:
            raise ValueError(f"Selected model {model} has no matched variant columns in variant-matrix.json")

    return {
        "version": 1,
        "run_id": run_id,
        "selected_models": selected,
        "primary_models": primary,
        "comparator_models": comparator,
        "source_variant_columns": {model: variant_counts[model] for model in selected},
        "source_sheets_by_model": {model: dict(sorted(sheet_counts.get(model, {}).items())) for model in selected},
        "available_models": available,
        "evidence_fingerprints": evidence_fingerprints(Path(evidence_dir)),
        "selection_source": selection_source,
    }


def read_model_selection(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise ValueError(f"Missing required model-selection.json artifact: {path}")
    selection = json.loads(path.read_text())
    validate_selection_shape(selection, source=str(path))
    return selection


def validate_selection_shape(selection: dict[str, Any], *, source: str = "model-selection.json") -> None:
    required = {"version", "selected_models", "primary_models", "comparator_models", "source_variant_columns", "evidence_fingerprints"}
    missing = sorted(required - set(selection))
    if missing:
        raise ValueError(f"{source} missing required keys: {missing}")
    if selection.get("version") != 1:
        raise ValueError(f"{source} must have version 1")
    selected = selection.get("selected_models")
    primary = selection.get("primary_models")
    comparator = selection.get("comparator_models")
    if not isinstance(selected, list) or not selected:
        raise ValueError(f"{source} selected_models must be a non-empty list")
    if not isinstance(primary, list) or not isinstance(comparator, list):
        raise ValueError(f"{source} primary_models and comparator_models must be lists")
    if sorted(set(primary) | set(comparator)) != sorted(selected):
        raise ValueError(f"{source} primary/comparator models must partition selected_models")


def assert_evidence_fingerprints(selection: dict[str, Any], evidence_dir: Path, *, source: str = "model-selection.json") -> None:
    """Fail closed when the persisted selection no longer matches the served evidence."""

    current = evidence_fingerprints(Path(evidence_dir))
    recorded = selection.get("evidence_fingerprints") or {}
    mismatched = sorted(name for name in FINGERPRINT_FILES if recorded.get(name) != current.get(name))
    if mismatched:
        raise ValueError(
            f"{source} evidence fingerprint mismatch against {evidence_dir} for: {', '.join(mismatched)}"
        )


def assert_selection_matches(a: dict[str, Any], b: dict[str, Any], *, left: str, right: str) -> None:
    for key in ("selected_models", "primary_models", "comparator_models", "evidence_fingerprints"):
        if a.get(key) != b.get(key):
            raise ValueError(f"Selection metadata mismatch for {key}: {left} does not match {right}")


def filter_rows_for_selection(raw_rows: list[dict[str, Any]], selected_models: list[str]) -> list[dict[str, Any]]:
    selected = set(selected_models)
    filtered = []
    for row in raw_rows:
        selected_cells = [
            cell for cell in row.get("status_cells", [])
            if clean(cell.get("model_key_candidate")).lower() in selected
        ]
        if not selected_cells:
            continue
        clone = dict(row)
        clone["all_status_cells"] = row.get("status_cells", [])
        clone["status_cells"] = selected_cells
        filtered.append(clone)
    return filtered
