"""Workbook-owned runtime model registry promotion helpers."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any

from corvette_form_generator.runtime_metadata import truthy
from corvette_form_generator.workbook import clean, intish, rows_from_sheet

MODEL_REGISTRY_PROMOTION_SHEET = "model_registry_promotion"
MODEL_REGISTRY_PROMOTION_HEADERS = [
    "model_key",
    "registry_key",
    "promoted_to_runtime",
    "default_model",
    "artifact_path",
    "artifact_type",
    "legacy_alias",
    "active",
    "display_order",
    "notes",
]
DRAFT_ONLY_TOP_LEVEL_FIELDS = ("draftMetadata",)
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
VALID_ARTIFACT_TYPES = {"current_generation", "draft_artifact"}


@dataclass(frozen=True)
class RegistryPromotion:
    model_key: str
    registry_key: str
    model_label: str
    export_slug: str
    artifact_path: str
    artifact_type: str
    legacy_alias: str
    default_model: bool
    display_order: int
    notes: str = ""


def registry_model_key(model_key: str) -> str:
    return "grandSport" if model_key == "grand_sport" else model_key


def export_slug(model_key: str) -> str:
    return model_key.replace("_", "-")


def _strip_live_contract_provenance(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: _strip_live_contract_provenance(child)
            for key, child in value.items()
            if key not in DRAFT_ONLY_LIVE_CONTRACT_FIELDS
        }
    if isinstance(value, list):
        return [_strip_live_contract_provenance(item) for item in value]
    return value


def live_contract_data(data: dict[str, Any]) -> dict[str, Any]:
    """Strip inspection-only provenance fields before embedding runtime data."""

    cleaned = json.loads(json.dumps(data))
    return _strip_live_contract_provenance(cleaned)


def _rows(wb: Any, sheet_name: str) -> list[dict[str, str]]:
    if sheet_name not in wb.sheetnames:
        return []
    return rows_from_sheet(wb, sheet_name)


def _model_rows_by_key(wb: Any) -> dict[str, dict[str, str]]:
    rows: dict[str, dict[str, str]] = {}
    for row in _rows(wb, "model_master"):
        model_key = clean(row.get("model_key")).lower()
        if model_key and model_key not in rows:
            rows[model_key] = row
    return rows


def promotion_sheet_has_rows(wb: Any) -> bool:
    return bool(_rows(wb, MODEL_REGISTRY_PROMOTION_SHEET))


def load_registry_promotions(wb: Any) -> list[RegistryPromotion]:
    """Load active/promoted registry rows.

    Missing or header-only sheets return an empty list so callers can preserve
    the legacy hardcoded registry fallback. Once rows exist, this sheet is
    authoritative for runtime promotion.
    """

    promotion_rows = _rows(wb, MODEL_REGISTRY_PROMOTION_SHEET)
    if not promotion_rows:
        return []

    model_rows = _model_rows_by_key(wb)
    promotions: list[RegistryPromotion] = []
    seen_registry_keys: set[str] = set()
    for row in promotion_rows:
        if not truthy(row.get("active"), default=True) or not truthy(row.get("promoted_to_runtime"), default=False):
            continue
        model_key = clean(row.get("model_key")).lower()
        registry_key = clean(row.get("registry_key")) or registry_model_key(model_key)
        artifact_type = clean(row.get("artifact_type")) or "draft_artifact"
        artifact_path = clean(row.get("artifact_path"))
        if not model_key:
            raise ValueError("model_registry_promotion promoted rows require model_key")
        model = model_rows.get(model_key)
        if not model:
            raise ValueError(f"model_registry_promotion promoted model_key {model_key!r} is missing from model_master")
        if not truthy(model.get("active"), default=True):
            raise ValueError(f"model_registry_promotion promoted model_key {model_key!r} is inactive in model_master")
        expected_registry_key = clean(model.get("registry_key")) or registry_model_key(model_key)
        if registry_key != expected_registry_key:
            raise ValueError(
                f"model_registry_promotion registry_key {registry_key!r} for {model_key!r} does not match model_master {expected_registry_key!r}"
            )
        if registry_key in seen_registry_keys:
            raise ValueError(f"Duplicate promoted registry_key {registry_key!r} in model_registry_promotion")
        seen_registry_keys.add(registry_key)
        if artifact_type not in VALID_ARTIFACT_TYPES:
            raise ValueError(f"Unsupported model_registry_promotion artifact_type {artifact_type!r} for {model_key!r}")
        if artifact_type != "current_generation" and not artifact_path:
            raise ValueError(f"model_registry_promotion artifact_path is required for promoted {model_key!r}")
        promotions.append(
            RegistryPromotion(
                model_key=model_key,
                registry_key=registry_key,
                model_label=clean(model.get("model_label")) or model_key.replace("_", " ").title(),
                export_slug=clean(model.get("export_slug")) or export_slug(model_key),
                artifact_path=artifact_path,
                artifact_type=artifact_type,
                legacy_alias=clean(row.get("legacy_alias")),
                default_model=truthy(row.get("default_model"), default=False),
                display_order=intish(row.get("display_order"), len(promotions) + 1),
                notes=clean(row.get("notes")),
            )
        )

    default_count = sum(1 for promotion in promotions if promotion.default_model)
    if promotions and default_count != 1:
        raise ValueError(f"model_registry_promotion requires exactly one promoted default model; found {default_count}")
    return sorted(promotions, key=lambda promotion: (promotion.display_order, promotion.registry_key))


def resolve_artifact_path(root: Path, artifact_path: str) -> Path:
    path = Path(artifact_path)
    if path.is_absolute():
        return path
    return root / path


def load_promotion_data(
    promotion: RegistryPromotion,
    *,
    current_model_key: str,
    current_data: dict[str, Any],
    root: Path,
) -> dict[str, Any]:
    if promotion.artifact_type == "current_generation":
        if promotion.model_key != current_model_key:
            raise ValueError(
                f"current_generation promotion {promotion.model_key!r} does not match current generated model {current_model_key!r}"
            )
        return current_data

    artifact = resolve_artifact_path(root, promotion.artifact_path)
    if not artifact.exists():
        raise FileNotFoundError(f"Promoted model artifact does not exist for {promotion.model_key}: {artifact}")
    return live_contract_data(json.loads(artifact.read_text(encoding="utf-8")))


def model_registry_entry(
    promotion: RegistryPromotion,
    data: dict[str, Any],
    asset: dict[str, str] | None = None,
) -> dict[str, Any]:
    entry = {
        "key": promotion.registry_key,
        "label": promotion.model_label,
        "modelName": f"Corvette {promotion.model_label}",
        "exportSlug": promotion.export_slug,
        "data": data,
    }
    if asset and asset.get("image_url"):
        entry.update(asset)
    return entry


def build_registry_from_promotions(
    wb: Any,
    *,
    current_model_key: str,
    current_data: dict[str, Any],
    model_assets: dict[str, dict[str, str]],
    root: Path,
) -> dict[str, Any] | None:
    promotions = load_registry_promotions(wb)
    if not promotions:
        return None

    models: dict[str, dict[str, Any]] = {}
    legacy_aliases: dict[str, str] = {}
    default_model_key = ""
    for promotion in promotions:
        data = load_promotion_data(promotion, current_model_key=current_model_key, current_data=current_data, root=root)
        models[promotion.registry_key] = model_registry_entry(promotion, data, model_assets.get(promotion.registry_key))
        if promotion.default_model:
            default_model_key = promotion.registry_key
        if promotion.legacy_alias:
            legacy_aliases[promotion.legacy_alias] = promotion.registry_key
    return {
        "defaultModelKey": default_model_key,
        "models": models,
        "legacyAliases": legacy_aliases,
    }
