"""Workbook-owned runtime model registry promotion helpers."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any

from corvette_form_generator.model_config import validate_model_key
from corvette_form_generator.runtime_contract import assert_runtime_contract, live_contract_data
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
VALID_ARTIFACT_TYPES = {"current_generation", "draft_artifact", "runtime_contract"}
VEHICLE_SETUP_FIELDS = (
    "setup_card_subtitle",
    "setup_eyebrow",
    "setup_title",
    "setup_description",
    "setup_fact_1",
    "setup_fact_2",
    "setup_fact_3",
)


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
    setup_card_subtitle: str
    setup_eyebrow: str
    setup_title: str
    setup_description: str
    setup_fact_1: str
    setup_fact_2: str
    setup_fact_3: str
    notes: str = ""


def registry_model_key(model_key: str) -> str:
    return "grandSport" if model_key == "grand_sport" else model_key


def export_slug(model_key: str) -> str:
    return validate_model_key(model_key).replace("_", "-")



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
        missing_setup_fields = [field for field in VEHICLE_SETUP_FIELDS if not clean(model.get(field))]
        if missing_setup_fields:
            raise ValueError(
                f"model_registry_promotion promoted model_key {model_key!r} requires complete vehicle setup copy; "
                f"missing {', '.join(missing_setup_fields)}"
            )
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
                setup_card_subtitle=clean(model.get("setup_card_subtitle")),
                setup_eyebrow=clean(model.get("setup_eyebrow")),
                setup_title=clean(model.get("setup_title")),
                setup_description=clean(model.get("setup_description")),
                setup_fact_1=clean(model.get("setup_fact_1")),
                setup_fact_2=clean(model.get("setup_fact_2")),
                setup_fact_3=clean(model.get("setup_fact_3")),
                notes=clean(row.get("notes")),
            )
        )

    default_count = sum(1 for promotion in promotions if promotion.default_model)
    if promotions and default_count != 1:
        raise ValueError(f"model_registry_promotion requires exactly one promoted default model; found {default_count}")
    return sorted(promotions, key=lambda promotion: (promotion.display_order, promotion.registry_key))


def resolve_artifact_path(root: Path, artifact_path: str | Path) -> Path:
    path = Path(artifact_path)
    root_resolved = root.resolve()
    candidate = path if path.is_absolute() else root_resolved / path
    resolved = candidate.resolve()
    if not resolved.is_relative_to(root_resolved):
        raise ValueError(f"Promoted artifact path resolves outside root {root_resolved}: {artifact_path}")
    return resolved


def current_generation_artifact_path(root: Path, promotion: RegistryPromotion) -> Path:
    if promotion.artifact_path:
        return resolve_artifact_path(root, promotion.artifact_path)
    return resolve_artifact_path(root, Path("form-output") / f"{export_slug(promotion.model_key)}-form-data.json")


def runtime_contract_artifact_path(root: Path, model_key: str) -> Path:
    return root / "form-output" / "runtime" / f"{export_slug(model_key)}-runtime-contract.json"


def artifact_path_for_promotion(root: Path, promotion: RegistryPromotion) -> Path:
    if promotion.artifact_type == "current_generation":
        return current_generation_artifact_path(root, promotion)
    return resolve_artifact_path(root, promotion.artifact_path)


def promotion_requires_runtime_contract_assertion(promotion: RegistryPromotion) -> bool:
    if promotion.artifact_type == "runtime_contract":
        return True
    return promotion.artifact_type != "current_generation"


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
        assert_runtime_contract(
            current_data,
            source=f"current generated model {current_model_key}",
            expected_model_label=promotion.model_label,
        )
        return current_data

    artifact = resolve_artifact_path(root, promotion.artifact_path)
    if not artifact.exists():
        raise FileNotFoundError(f"Promoted model artifact does not exist for {promotion.model_key}: {artifact}")
    data = json.loads(artifact.read_text(encoding="utf-8"))
    assert_runtime_contract(data, source=str(artifact), expected_model_label=promotion.model_label)
    return data


def load_promotion_artifact_data(promotion: RegistryPromotion, *, root: Path) -> dict[str, Any]:
    artifact = artifact_path_for_promotion(root, promotion)
    if not artifact.exists():
        raise FileNotFoundError(f"Promoted model artifact does not exist for {promotion.model_key}: {artifact}")
    data = json.loads(artifact.read_text(encoding="utf-8"))
    assert_runtime_contract(data, source=str(artifact), expected_model_label=promotion.model_label)
    return data


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
        "vehicleSetup": {
            "cardSubtitle": promotion.setup_card_subtitle,
            "eyebrow": promotion.setup_eyebrow,
            "title": promotion.setup_title,
            "description": promotion.setup_description,
            "facts": [promotion.setup_fact_1, promotion.setup_fact_2, promotion.setup_fact_3],
        },
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


def build_registry_from_artifacts(
    wb: Any,
    *,
    model_assets: dict[str, dict[str, str]],
    root: Path,
) -> dict[str, Any]:
    promotions = load_registry_promotions(wb)
    if not promotions:
        raise RuntimeError(
            "model_registry_promotion has no promoted rows; refusing to guess the app registry. "
            "Author the promotion rows in the workbook before regenerating app data."
        )

    models: dict[str, dict[str, Any]] = {}
    legacy_aliases: dict[str, str] = {}
    default_model_key = ""
    for promotion in promotions:
        data = load_promotion_artifact_data(promotion, root=root)
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


def parse_app_data_registry(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    try:
        registry_json = text.split("window.CORVETTE_FORM_DATA = ", 1)[1].split(
            ";\nwindow.STINGRAY_FORM_DATA",
            1,
        )[0]
    except IndexError as exc:
        raise ValueError(f"Could not locate window.CORVETTE_FORM_DATA in {path}") from exc
    return json.loads(registry_json)
