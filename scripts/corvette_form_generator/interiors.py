"""Shared interior reference parsing, component metadata, and interior building."""

from __future__ import annotations

import csv
import json
import re
from pathlib import Path
from typing import Any

from openpyxl import load_workbook

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


INTERIOR_COMPONENT_LABELS = {
    "36S": "Yellow Stitching",
    "37S": "Blue Stitching",
    "38S": "Red Stitching",
    "N26": "Sueded Microfiber",
    "N2Z": "Sueded Microfiber",
    "TU7": "Two-Tone",
    "R6X": "Custom Interior Trim and Seat Combination",
}


def interior_component_metadata(
    row: dict[str, str],
    price_ref: dict[tuple[str, str, str], int],
) -> list[dict[str, Any]]:
    trim = clean(row.get("Trim", ""))
    interior_id = clean(row.get("interior_id", "") or row.get("ID", ""))
    seat = clean(row.get("Seat", ""))
    tokens = set(interior_id.split("_"))
    components: list[dict[str, Any]] = []

    if "R6X" in trim or "R6X" in tokens:
        r6x_trim = trim if "R6X" in trim else f"{trim}_R6X"
        components.append(
            {
                "rpo": "R6X",
                "label": INTERIOR_COMPONENT_LABELS["R6X"],
                "price": price_ref_component_price(price_ref, "seat", seat, r6x_trim),
                "component_type": "r6x",
            }
        )
    else:
        seat_price = price_ref_component_price(price_ref, "seat", seat, trim)
        if seat_price:
            components.append(
                {
                    "rpo": seat,
                    "label": f"{seat} Seat Upgrade",
                    "price": seat_price,
                    "component_type": "seat",
                }
            )

    for rpo in ("36S", "37S", "38S"):
        if rpo in tokens:
            components.append(
                {
                    "rpo": rpo,
                    "label": INTERIOR_COMPONENT_LABELS[rpo],
                    "price": price_ref_component_price(price_ref, "stitching", rpo),
                    "component_type": "stitching",
                }
            )

    for rpo in ("N26", "N2Z"):
        if rpo in tokens:
            components.append(
                {
                    "rpo": rpo,
                    "label": INTERIOR_COMPONENT_LABELS[rpo],
                    "price": price_ref_component_price(price_ref, "suede", rpo),
                    "component_type": "suede",
                }
            )

    if "TU7" in tokens:
        components.append(
            {
                "rpo": "TU7",
                "label": INTERIOR_COMPONENT_LABELS["TU7"],
                "price": price_ref_component_price(price_ref, "twotone", "TU7"),
                "component_type": "two_tone",
            }
        )

    return [component for component in components if component["price"] or component["rpo"] == "R6X"]


def workbook_interior_component_metadata(
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


def clean_reference_label(value: str) -> str:
    label = clean(value)
    if " - " in label:
        head, tail = label.split(" - ", 1)
        if re.search(r"\b(option|expandable|choice|card)\b", tail, re.IGNORECASE):
            label = head
    label = re.sub(r"\s*\([^)]*(?:expandable|only one option|no need)[^)]*\)\s*$", "", label, flags=re.IGNORECASE)
    return label.strip()


def read_interior_reference(reference_path: Path) -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]]]:
    reference_by_id: dict[str, dict[str, Any]] = {}
    reference_rows: list[dict[str, Any]] = []
    current_levels = [""] * 6
    if not reference_path.exists():
        return reference_by_id, reference_rows
    with reference_path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row_number, row in enumerate(reader, start=2):
            for index in range(6):
                key = f"level{index}"
                value = clean_reference_label(row.get(key, ""))
                if value:
                    current_levels[index] = value
                    for deeper in range(index + 1, 6):
                        current_levels[deeper] = ""
            interior_id = clean(row.get("interior_id", ""))
            levels = [level for level in current_levels if level]
            record = {
                "row_number": row_number,
                "interior_id": interior_id,
                "levels": levels,
            }
            reference_rows.append(record)
            if interior_id:
                reference_by_id[interior_id] = record
    return reference_by_id, reference_rows


def seat_code_from_label(label: str) -> str:
    return clean(label).split(" ", 1)[0]


def broad_interior_color_family(label: str) -> str:
    value = clean(label)
    if not value:
        return "Other Interior Choices"
    lower = value.lower()
    if "asymmetrical santorini blue" in lower:
        return "Asymmetrical Santorini Blue / Jet Black"
    if "asymmetrical adrenaline red" in lower:
        return "Asymmetrical Adrenaline Red / Jet Black"
    if "ultimate suede jet black" in lower:
        return "Ultimate Suede Jet Black"
    if lower.startswith("sky cool gray"):
        return "Sky Cool Gray"
    if lower.startswith("santorini blue"):
        return "Santorini Blue"
    for marker in (" interior", " seats"):
        idx = lower.find(marker)
        if idx > 0:
            value = value[:idx]
            lower = value.lower()
    for marker in (" with ", " suede", " two tone"):
        idx = lower.find(marker)
        if idx > 0:
            return value[:idx].strip()
    return value


def grouping_fields_for_interior(
    interior: dict[str, Any],
    reference: dict[str, Any] | None,
    reference_order: int,
    fallback: bool = False,
) -> dict[str, Any]:
    seat_label = reference["levels"][1] if reference and len(reference["levels"]) > 1 else f"{interior['seat_code']} Seats"
    fallback_color_family = broad_interior_color_family(interior["interior_name"] or "Other Interior Choices")
    levels = reference["levels"] if reference else [
        interior["trim_level"],
        seat_label,
        fallback_color_family,
        interior["material"] or "Standard interior",
        interior["interior_name"] or interior["interior_id"],
    ]
    leaf_label = levels[-1] if levels else interior["interior_name"] or interior["interior_id"]
    color_family = levels[2] if len(levels) > 2 else broad_interior_color_family(leaf_label)
    trim_value = clean(interior.get("trim_level", ""))
    interior_id_value = clean(interior.get("interior_id", ""))
    if "R6X" in trim_value or "R6X" in interior_id_value:
        color_family = "Custom Interior trim and seat combinations"
    elif not reference:
        color_family = fallback_color_family
    material_family = interior.get("material") or "Standard interior"
    if len(levels) > 3 and levels[-2] != color_family:
        material_family = levels[-2]
    parent_group = seat_label if len(levels) > 1 else color_family
    return {
        "interior_trim_level": levels[0] if levels else interior["trim_level"],
        "interior_seat_code": seat_code_from_label(seat_label) or interior["seat_code"],
        "interior_seat_label": seat_label,
        "interior_color_family": "Other Interior Choices" if fallback else color_family,
        "interior_material_family": material_family,
        "interior_variant_label": leaf_label,
        "interior_group_display_order": reference_order,
        "interior_material_display_order": reference_order,
        "interior_choice_display_order": reference_order,
        "interior_hierarchy_levels": json.dumps(levels, ensure_ascii=False),
        "interior_hierarchy_path": " > ".join(levels),
        "interior_parent_group_label": parent_group,
        "interior_leaf_label": leaf_label,
        "interior_reference_order": reference_order,
    }


WORKBOOK_GROUPING_REQUIRED_FIELDS = (
    "interior_seat_label",
    "interior_color_family",
    "interior_material_family",
    "interior_leaf_label",
    "interior_group_display_order",
    "interior_hierarchy_levels",
)


def has_workbook_grouping_fields(scope_row: dict[str, Any] | None) -> bool:
    if not scope_row:
        return False
    return all(clean(scope_row.get(field)) for field in WORKBOOK_GROUPING_REQUIRED_FIELDS)


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


def fallback_interior_trims(config: ModelConfig) -> set[str]:
    trims: set[str] = set()
    for variant_id in config.variant_ids:
        trim = clean(variant_id.split("_", 1)[0]).upper()
        if not trim:
            continue
        trims.add(trim)
        if trim.startswith("3"):
            trims.add(f"{trim}_R6X")
    return trims


def active_interior_flags(config: ModelConfig) -> dict[str, bool]:
    flags = {"active_for_stingray": config.model_key == "stingray"}
    flags[f"active_for_{config.model_key}"] = True
    return flags


def build_model_interiors(config: ModelConfig) -> list[dict[str, Any]]:
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
    finally:
        wb.close()

    reference_by_id, reference_rows = read_interior_reference(config.interior_reference_path)
    reference_order_by_id = {
        row["interior_id"]: index
        for index, row in enumerate((row for row in reference_rows if row["interior_id"]), start=1)
    }
    fallback_order = len(reference_order_by_id) + 1
    fallback_trims = fallback_interior_trims(config)
    active_flags = active_interior_flags(config)
    interiors: list[dict[str, Any]] = []

    for row in interior_rows:
        trim = clean(row.get("Trim", ""))
        interior_id = clean(row.get("interior_id", ""))
        scope_row = model_interior_scope.get(interior_id)
        if model_interior_scope:
            if not scope_row:
                continue
        elif fallback_trims and trim not in fallback_trims:
            continue
        components = workbook_interior_component_metadata(row, workbook_components_by_interior_id, interior_component_price_ref)
        legacy_components = interior_component_metadata(row, interior_component_price_ref)
        if not components and legacy_components:
            if model_interior_scope:
                raise ValueError(
                    f"{config.model_label} interior {interior_id} has component-bearing legacy output but no active interior_components workbook rows."
                )
            components = legacy_components
        trim_level = clean(scope_row.get("trim_level")) if scope_row else ""
        requires_option_id = clean(scope_row.get("requires_option_id")) if scope_row else ""
        interior = {
            "interior_id": interior_id,
            "source_sheet": config.interior_source_sheet,
            **active_flags,
            "requires_z25": "True" if requires_option_id == "opt_z25_001" or interior_id in z25_interior_ids else "False",
            "trim_level": trim_level or trim.replace("_R6X", ""),
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
            "interior_components": components,
            "interior_components_json": json.dumps(components, separators=(",", ":")),
        }
        if model_interior_scope:
            if scope_row is None:
                raise ValueError(f"Missing active model_interior_scope row for {config.model_label} interior {interior_id}")
            interior.update(grouping_fields_from_scope(scope_row, interior))
        else:
            reference = reference_by_id.get(interior_id)
            if reference:
                interior.update(grouping_fields_for_interior(interior, reference, reference_order_by_id[interior_id]))
            else:
                interior.update(grouping_fields_for_interior(interior, None, fallback_order, fallback=False))
                fallback_order += 1
        interiors.append(interior)

    return interiors
