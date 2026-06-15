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
RUNTIME_CHOICE_ROW_TRIM_FIELDS = frozenset(
    ("source_detail_raw", "choice_mode", "selection_mode", "selection_mode_label")
)
RUNTIME_STANDARD_EQUIPMENT_ROW_TRIM_FIELDS = frozenset(("source_detail_raw",))
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


def assert_runtime_contract(data: dict[str, Any], *, source: str) -> None:
    """Fail fast when a promoted artifact still carries draft-only content.

    Promotion no longer strips draft provenance at load time; the draft
    generation pathway emits a clean ``*-runtime-contract.json`` alongside the
    draft artifacts, and that contract is embedded verbatim.
    """

    problems: list[str] = []
    leaks = find_draft_only_fields(data)
    if leaks:
        problems.append(f"draft-only fields present: {', '.join(leaks[:5])}{'...' if len(leaks) > 5 else ''}")
    dataset = data.get("dataset")
    status = dataset.get("status") if isinstance(dataset, dict) else None
    if status != "runtime_active":
        problems.append(f"dataset.status is {status!r}, expected 'runtime_active'")
    if problems:
        raise ValueError(
            f"Promoted artifact {source} is not a clean runtime contract ({'; '.join(problems)}). "
            "Regenerate it with scripts/generate_form.py --model <key>."
        )


def live_contract_data(data: dict[str, Any]) -> dict[str, Any]:
    """Derive the clean runtime contract from a draft dataset.

    Runs at draft-generation emit time (see
    ``inspection.write_runtime_contract_artifact``); promotion loads the
    emitted contract verbatim and only validates it.
    """

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


def current_generation_artifact_path(root: Path, promotion: RegistryPromotion) -> Path:
    if promotion.artifact_path:
        return resolve_artifact_path(root, promotion.artifact_path)
    return root / "form-output" / f"{promotion.export_slug}-form-data.json"


def artifact_path_for_promotion(root: Path, promotion: RegistryPromotion) -> Path:
    if promotion.artifact_type == "current_generation":
        return current_generation_artifact_path(root, promotion)
    return resolve_artifact_path(root, promotion.artifact_path)


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
    data = json.loads(artifact.read_text(encoding="utf-8"))
    assert_runtime_contract(data, source=str(artifact))
    return data


def load_promotion_artifact_data(promotion: RegistryPromotion, *, root: Path) -> dict[str, Any]:
    artifact = artifact_path_for_promotion(root, promotion)
    if not artifact.exists():
        raise FileNotFoundError(f"Promoted model artifact does not exist for {promotion.model_key}: {artifact}")
    data = json.loads(artifact.read_text(encoding="utf-8"))
    if promotion.artifact_type != "current_generation":
        assert_runtime_contract(data, source=str(artifact))
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
