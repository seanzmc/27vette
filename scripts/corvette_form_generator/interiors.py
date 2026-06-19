"""Shared workbook-owned interior component metadata and interior building."""

from __future__ import annotations

import json
from typing import Any

from openpyxl import load_workbook

from corvette_form_generator.contract import ASSET_IMAGE_FIELDS, interior_asset_map
from corvette_form_generator.model_config import ModelConfig
from corvette_form_generator.pricing import (
    generated_interior_price,
    price_ref_component_price,
    price_ref_component_prices,
    price_ref_prices,
)
from corvette_form_generator.rules import runtime_authored_rule
from corvette_form_generator.runtime_metadata import (
    load_interior_components,
    load_model_interior_scope_map,
)
from corvette_form_generator.workbook import clean, intish, rows_from_sheet


def workbook_interior_components(
    row: dict[str, str],
    workbook_components_by_interior_id: dict[str, list[dict[str, Any]]],
    price_ref: dict[tuple[str, str, str], int],
) -> list[dict[str, Any]]:
    interior_id = clean(row.get("interior_id", "") or row.get("ID", ""))
    component_rows = workbook_components_by_interior_id.get(interior_id, [])
    if not component_rows:
        return []
    trim = clean(row.get("Trim", ""))
    components: list[dict[str, Any]] = []
    for component in component_rows:
        price_ref_type = clean(component.get("price_ref_type"))
        price_ref_code = clean(component.get("price_ref_code")) or clean(component.get("rpo"))
        price_trim_scope = clean(component.get("price_trim_scope")) or trim
        price = price_ref_component_price(price_ref, price_ref_type, price_ref_code, price_trim_scope)
        normalized = {
            "rpo": clean(component.get("rpo")),
            "label": clean(component.get("label")),
            "price": price,
            "component_type": clean(component.get("component_type")),
        }
        if normalized["price"] or normalized["rpo"] == "R6X":
            components.append(normalized)
    return components


def seat_code_from_label(label: str) -> str:
    return clean(label).split(" ", 1)[0]


WORKBOOK_GROUPING_REQUIRED_FIELDS = (
    "interior_seat_label",
    "interior_color_family",
    "interior_material_family",
    "interior_leaf_label",
    "interior_group_display_order",
    "interior_hierarchy_levels",
)


def grouping_fields_from_scope(scope_row: dict[str, Any], interior: dict[str, Any]) -> dict[str, Any]:
    missing = [field for field in WORKBOOK_GROUPING_REQUIRED_FIELDS if not clean(scope_row.get(field))]
    if missing:
        raise ValueError(
            f"Active model_interior_scope row for {scope_row.get('interior_id') or interior.get('interior_id')} "
            f"is missing workbook-owned grouping metadata: {', '.join(missing)}"
        )
    levels_text = clean(scope_row.get("interior_hierarchy_levels"))
    try:
        levels = json.loads(levels_text)
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"model_interior_scope interior_hierarchy_levels is not valid JSON for "
            f"{scope_row.get('interior_id') or interior.get('interior_id')}: {levels_text}"
        ) from exc
    if not isinstance(levels, list) or not all(isinstance(level, str) for level in levels):
        raise ValueError(
            f"model_interior_scope interior_hierarchy_levels must be a JSON string array for "
            f"{scope_row.get('interior_id') or interior.get('interior_id')}"
        )
    group_order = intish(scope_row.get("interior_group_display_order"))
    material_order = intish(scope_row.get("interior_material_display_order"), group_order)
    choice_order = intish(scope_row.get("interior_choice_display_order"), group_order)
    reference_order = intish(scope_row.get("interior_reference_order"), choice_order)
    seat_label = clean(scope_row.get("interior_seat_label"))
    color_family = clean(scope_row.get("interior_color_family"))
    material_family = clean(scope_row.get("interior_material_family"))
    leaf_label = clean(scope_row.get("interior_leaf_label"))
    return {
        "interior_trim_level": levels[0] if levels else interior["trim_level"],
        "interior_seat_code": seat_code_from_label(seat_label) or interior["seat_code"],
        "interior_seat_label": seat_label,
        "interior_color_family": color_family,
        "interior_material_family": material_family,
        "interior_variant_label": clean(scope_row.get("interior_variant_label")) or leaf_label,
        "interior_group_display_order": group_order,
        "interior_material_display_order": material_order,
        "interior_choice_display_order": choice_order,
        "interior_hierarchy_levels": json.dumps(levels, ensure_ascii=False),
        "interior_hierarchy_path": " > ".join(levels),
        "interior_parent_group_label": clean(scope_row.get("interior_parent_group_label")) or seat_label,
        "interior_leaf_label": leaf_label,
        "interior_reference_order": reference_order,
    }


def active_interior_flags(config: ModelConfig) -> dict[str, bool]:
    flags = {"active_for_stingray": config.model_key == "stingray"}
    flags[f"active_for_{config.model_key}"] = True
    return flags


def build_model_interiors(config: ModelConfig, wb: Any | None = None) -> list[dict[str, Any]]:
    close_workbook = wb is None
    if wb is None:
        wb = load_workbook(config.workbook_path, data_only=True, read_only=True)
    try:
        interior_rows = rows_from_sheet(wb, config.interior_source_sheet)
        price_ref_rows = rows_from_sheet(wb, "PriceRef")
        rule_rows = rows_from_sheet(wb, config.rule_mapping_sheet)
        z25_interior_ids = {
            row.get("source_id", "")
            for row in rule_rows
            if row.get("rule_type", "").lower() == "includes"
            and row.get("target_id", "") == "opt_z25_001"
            and runtime_authored_rule(row)
        }
        interior_price_ref = price_ref_prices(price_ref_rows)
        interior_component_price_ref = price_ref_component_prices(price_ref_rows)
        workbook_components_by_interior_id = load_interior_components(wb, config.model_key)
        model_interior_scope = load_model_interior_scope_map(wb, config.model_key)
        interior_assets = interior_asset_map(wb, config.model_key)
    finally:
        if close_workbook:
            wb.close()

    if not model_interior_scope:
        raise ValueError(
            f"{config.model_label} interior generation requires active model_interior_scope rows; "
            "CSV/reference and trim-derived fallbacks are retired."
        )

    active_flags = active_interior_flags(config)
    interiors: list[dict[str, Any]] = []

    for row in interior_rows:
        trim = clean(row.get("Trim", ""))
        interior_id = clean(row.get("interior_id", ""))
        scope_row = model_interior_scope.get(interior_id)
        if not scope_row:
            continue
        requires_option_id = clean(scope_row.get("requires_option_id"))
        interior = {
            "interior_id": interior_id,
            "source_sheet": config.interior_source_sheet,
            **active_flags,
            "requires_z25": "True" if requires_option_id == "opt_z25_001" or interior_id in z25_interior_ids else "False",
            "trim_level": clean(scope_row.get("trim_level")) or trim.replace("_R6X", ""),
            "requires_r6x": "True" if "_R6X" in trim or interior_id.endswith("_R6X") else "False",
            "seat_code": clean(row.get("Seat", "")),
            "interior_code": clean(row.get("Interior Code", "")),
            "interior_name": clean(row.get("Interior Name", "")),
            "material": clean(row.get("Material", "")),
            "price": generated_interior_price(row, interior_price_ref),
            "suede": clean(row.get("Suede", "")),
            "stitch": clean(row.get("Stitch", "")),
            "two_tone": clean(row.get("Two Tone", "")),
            "section_id": clean(row.get("section_id", "")),
            "color_overrides_raw": clean(row.get("Color Overrides", "")),
            "source_note": clean(row.get("Detail from Disclosure", "")),
            "interior_components": workbook_interior_components(
                row,
                workbook_components_by_interior_id,
                interior_component_price_ref,
            ),
        }
        interior["interior_components_json"] = json.dumps(interior["interior_components"], separators=(",", ":"))
        interior.update(grouping_fields_from_scope(scope_row, interior))
        if asset := interior_assets.get(interior["interior_code"].upper()):
            interior.update({field: asset.get(field, "") for field in ASSET_IMAGE_FIELDS})
        interiors.append(interior)

    return interiors
