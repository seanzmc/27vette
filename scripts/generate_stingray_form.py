#!/usr/bin/env python3
"""Generate the Stingray form contract and static-app data from stingray_master.xlsx."""

from __future__ import annotations

import csv
import json
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from typing import Any

from openpyxl import load_workbook
from corvette_form_generator.mapping import (
    best_status,
    normalize_mode,
    selection_mode_label as shared_selection_mode_label,
    status_to_label,
    step_for_section as shared_step_for_section,
)
from corvette_form_generator.model_configs import STINGRAY_MODEL
from corvette_form_generator.output import write_app_data, write_json_output
from corvette_form_generator.validation import validation_error_count
from corvette_form_generator.workbook import clean, intish, money, rows_from_sheet, write_sheet


MODEL_CONFIG = STINGRAY_MODEL
ROOT = MODEL_CONFIG.root
WORKBOOK_PATH = MODEL_CONFIG.workbook_path
OUTPUT_DIR = MODEL_CONFIG.output_dir
APP_DIR = MODEL_CONFIG.app_dir
INTERIOR_REFERENCE_PATH = MODEL_CONFIG.interior_reference_path
GENERATED_SHEETS = list(MODEL_CONFIG.generated_sheets)
STEP_ORDER = list(MODEL_CONFIG.step_order)
STEP_LABELS = dict(MODEL_CONFIG.step_labels)
CONTEXT_SECTIONS = [dict(section) for section in MODEL_CONFIG.context_sections]
SECTION_STEP_OVERRIDES = dict(MODEL_CONFIG.section_step_overrides)
BODY_STYLE_DISPLAY_ORDER = dict(MODEL_CONFIG.body_style_display_order)
SELECTION_MODE_LABELS = dict(MODEL_CONFIG.selection_mode_labels)
STANDARD_SECTIONS = set(MODEL_CONFIG.standard_sections)

OPTION_ID_ALIASES = {
    "opt_bc4_002": "opt_bc4_001",
    "opt_bcp_002": "opt_bcp_001",
    "opt_bcs_002": "opt_bcs_001",
    "opt_bc7_002": "opt_bc7_001",
}

CONSOLIDATED_ENGINE_COVERS = {"opt_bc4_001", "opt_bcp_001", "opt_bcs_001"}

HIDDEN_OPTION_IDS = {
    "opt_bc4_002",
    "opt_bcp_002",
    "opt_bcs_002",
    "opt_bc7_002",
    "opt_n26_001",
    "opt_tu7_001",
    "opt_zf1_001",
}

HIDDEN_SECTION_IDS = {"sec_cust_002"}

AUTO_ONLY_OPTION_IDS = {"opt_r6x_001"}
DISPLAY_ONLY_OPTION_IDS = {"opt_d30_001"}

SECTION_MODE_OVERRIDES = {
    "sec_spoi_001": "multi_select_opt",
}

SECTION_DISPLAY_ORDER_OVERRIDES = {
    "sec_roof_001": 10,
    "sec_exte_001": 20,
    "sec_badg_001": 30,
    "sec_engi_001": 40,
    "sec_whee_002": 10,
    "sec_cali_001": 20,
    "sec_whee_001": 30,
}

ENGINE_APPEARANCE_OPTION_ORDER = {
    "opt_bc7_001": 10,
    "opt_bcp_001": 20,
    "opt_bcs_001": 30,
    "opt_bc4_001": 40,
    "opt_b6p_001": 50,
    "opt_zz3_001": 60,
    "opt_d3v_001": 70,
    "opt_sl9_001": 80,
    "opt_slk_001": 90,
    "opt_sln_001": 100,
    "opt_vup_001": 110,
}

AERO_EXHAUST_ACCESSORIES_SECTION_ORDER = {
    "sec_exha_001": 10,
    "sec_spoi_001": 20,
    "sec_stri_001": 30,
    "sec_lpoe_001": 40,
    "sec_lpow_001": 50,
}

FIVE_V7_OR_REQUIREMENT_TARGET_IDS = {"opt_5zu_001", "opt_5zz_001", "opt_5zw_001"}
FIVE_ZU_OR_REQUIREMENT_TARGET_IDS = {"opt_g8g_001", "opt_gba_001", "opt_gkz_001"}
T0A_REPLACEMENT_OPTION_IDS = {"opt_tvs_001", "opt_5zz_001", "opt_5zu_001"}
GRAND_SPORT_ONLY_INTERIOR_IDS = {"3LT_AE4_EL9", "3LT_AH2_EL9"}

RULE_GROUPS = [
    {
        "group_id": "grp_5v7_spoiler_requirement",
        "group_type": "requires_any",
        "source_id": "opt_5v7_001",
        "target_ids": ["opt_5zu_001", "opt_5zz_001"],
        "body_style_scope": "",
        "trim_level_scope": "",
        "variant_scope": "",
        "disabled_reason": "Requires 5ZU Body-Color High Wing Spoiler or 5ZZ Carbon Flash High Wing Spoiler.",
        "active": "True",
        "notes": "5V7 is available when either approved high wing spoiler is selected.",
    },
    {
        "group_id": "grp_5zu_paint_requirement",
        "group_type": "requires_any",
        "source_id": "opt_5zu_001",
        "target_ids": ["opt_g8g_001", "opt_gba_001", "opt_gkz_001"],
        "body_style_scope": "",
        "trim_level_scope": "",
        "variant_scope": "",
        "disabled_reason": "Requires Arctic White, Black, or Torch Red exterior paint.",
        "active": "True",
        "notes": "5ZU body-color spoiler requires one approved body color.",
    },
]

EXCLUSIVE_GROUPS = [
    {
        "group_id": "grp_ls6_engine_covers",
        "option_ids": ["opt_bc7_001", "opt_bcp_001", "opt_bcs_001", "opt_bc4_001"],
        "selection_mode": "single_within_group",
        "active": "True",
        "notes": "LS6 engine cover choices are mutually exclusive within the Engine Appearance section.",
    },
    {
        "group_id": "grp_spoiler_high_wing",
        "option_ids": ["opt_t0a_001", "opt_tvs_001", "opt_5zz_001", "opt_5zu_001"],
        "selection_mode": "single_within_group",
        "active": "True",
        "notes": "Spoiler choices are mutually exclusive within the Spoiler section.",
    },
    {
        "group_id": "excl_center_caps",
        "option_ids": ["opt_rxj_001", "opt_vwd_001", "opt_5zd_001", "opt_5zc_001", "opt_rxh_001"],
        "selection_mode": "single_within_group",
        "active": "True",
        "notes": "Center cap choices are mutually exclusive within the Wheels section.",
    },
    {
        "group_id": "excl_indoor_car_covers",
        "option_ids": ["opt_rwh_001", "opt_sl1_001", "opt_wkr_001", "opt_wkq_001"],
        "selection_mode": "single_within_group",
        "active": "True",
        "notes": "Indoor car cover choices are mutually exclusive within the Aero, Exhaust, Stripes & Accessories section.",
    },
    {
        "group_id": "excl_outdoor_car_covers",
        "option_ids": ["opt_rnx_001", "opt_rwj_001"],
        "selection_mode": "single_within_group",
        "active": "True",
        "notes": "Outdoor car cover choices are mutually exclusive within the Aero, Exhaust, Stripes & Accessories section.",
    },
    {
        "group_id": "excl_suede_trunk_liner",
        "option_ids": ["opt_sxb_001", "opt_sxr_001", "opt_sxt_001"],
        "selection_mode": "single_within_group",
        "active": "True",
        "notes": "Suede trunk liner choices are mutually exclusive within the Interior Trim section.",
    },
]

def step_for_section(section_id: str, section_name: str, category_id: str) -> str:
    return shared_step_for_section(
        section_id,
        section_name,
        category_id,
        standard_sections=STANDARD_SECTIONS,
        section_step_overrides=SECTION_STEP_OVERRIDES,
    )


def selection_mode_label(selection_mode: str) -> str:
    return shared_selection_mode_label(selection_mode, SELECTION_MODE_LABELS)


def canonical_option_id(option_id: str) -> str:
    return OPTION_ID_ALIASES.get(option_id, option_id)


def rule_body_style_scope(rule: dict[str, str], source_id: str, target_id: str) -> str:
    note = clean(rule.get("original_detail_raw", ""))
    if target_id == "opt_zz3_001" or "Convertible Engine Appearance Package" in note:
        return "convertible"
    if target_id == "opt_b6p_001" or "on Coupe" in note or "Coupe Engine Appearance Package" in note:
        return "coupe"
    return ""


def option_key(option: dict[str, str]) -> str:
    return option["option_id"]


def interior_price(row: dict[str, str]) -> int:
    return money(row.get("Price") or row.get("Cost"))


def price_ref_key(trim: str, code: str) -> tuple[str, str]:
    return (clean(trim).replace("_", " "), clean(code))


def price_ref_prices(rows: list[dict[str, str]]) -> dict[tuple[str, str], int]:
    prices: dict[tuple[str, str], int] = {}
    for row in rows:
        if clean(row.get("OptionType", "")).lower() != "seat":
            continue
        trim = clean(row.get("Trim", ""))
        code = clean(row.get("Code", ""))
        if trim and code:
            prices[price_ref_key(trim, code)] = money(row.get("Price"))
    return prices


def price_ref_component_prices(rows: list[dict[str, str]]) -> dict[tuple[str, str, str], int]:
    prices: dict[tuple[str, str, str], int] = {}
    for row in rows:
        option_type = clean(row.get("OptionType", "")).lower()
        code = clean(row.get("Code", ""))
        if not option_type or not code:
            continue
        prices[(option_type, clean(row.get("Trim", "")).replace("_", " "), code)] = money(row.get("Price"))
    return prices


def price_ref_component_price(
    price_ref: dict[tuple[str, str, str], int],
    option_type: str,
    code: str,
    trim: str = "",
) -> int:
    normalized_type = clean(option_type).lower()
    normalized_trim = clean(trim).replace("_", " ")
    normalized_code = clean(code)
    if (normalized_type, normalized_trim, normalized_code) in price_ref:
        return price_ref[(normalized_type, normalized_trim, normalized_code)]
    return price_ref.get((normalized_type, "", normalized_code), 0)


def r6x_price_component(row: dict[str, str], price_ref: dict[tuple[str, str], int]) -> int:
    trim = clean(row.get("Trim", ""))
    interior_id = clean(row.get("interior_id", "") or row.get("ID", ""))
    if "R6X" not in trim and "R6X" not in interior_id:
        return 0

    seat = clean(row.get("Seat", ""))
    r6x_trim = trim if "R6X" in trim else f"{trim}_R6X"
    base_trim = r6x_trim.replace("_R6X", "")
    r6x_price = price_ref.get(price_ref_key(r6x_trim, seat))
    if r6x_price is None:
        return 0
    return max(0, r6x_price - price_ref.get(price_ref_key(base_trim, seat), 0))


def generated_interior_price(row: dict[str, str], price_ref: dict[tuple[str, str], int]) -> int:
    return interior_price(row) + r6x_price_component(row, price_ref)


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


def clean_reference_label(value: str) -> str:
    label = clean(value)
    if " - " in label:
        head, tail = label.split(" - ", 1)
        if re.search(r"\b(option|expandable|choice|card)\b", tail, re.IGNORECASE):
            label = head
    label = re.sub(r"\s*\([^)]*(?:expandable|only one option|no need)[^)]*\)\s*$", "", label, flags=re.IGNORECASE)
    return label.strip()


def read_interior_reference() -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]]]:
    reference_by_id: dict[str, dict[str, Any]] = {}
    reference_rows: list[dict[str, Any]] = []
    current_levels = [""] * 6
    with INTERIOR_REFERENCE_PATH.open(newline="", encoding="utf-8") as handle:
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


def grouping_fields_for_interior(
    interior: dict[str, Any],
    reference: dict[str, Any] | None,
    reference_order: int,
    fallback: bool = False,
) -> dict[str, Any]:
    seat_label = reference["levels"][1] if reference and len(reference["levels"]) > 1 else f"{interior['seat_code']} Seats"
    levels = reference["levels"] if reference else [
        interior["trim_level"],
        seat_label,
        "Other Interior Choices",
        interior["interior_name"] or interior["interior_id"],
    ]
    leaf_label = levels[-1] if levels else interior["interior_name"] or interior["interior_id"]
    color_family = levels[2] if len(levels) > 2 else leaf_label
    material_family = interior.get("material") or "Standard interior"
    if len(levels) > 3 and levels[-2] != color_family:
        material_family = levels[-2]
    parent_group = levels[-2] if len(levels) > 1 else color_family
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


def label_for(entity_id: str, options: dict[str, dict[str, Any]], interiors: dict[str, dict[str, Any]]) -> str:
    if entity_id in options:
        option = options[entity_id]
        rpo = option.get("rpo") or entity_id
        return f"{rpo} {option.get('label', '')}".strip()
    if entity_id in interiors:
        interior = interiors[entity_id]
        return f"{interior.get('interior_id')} {interior.get('interior_name')}".strip()
    return entity_id


def truncate_reason(text: str, limit: int = 180) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "..."


def main() -> None:
    wb = load_workbook(WORKBOOK_PATH)

    variants_raw = rows_from_sheet(wb, "variant_master")
    categories = {row["category_id"]: row for row in rows_from_sheet(wb, "category_master")}
    sections = {row["section_id"]: row for row in rows_from_sheet(wb, "section_master")}
    options_raw = rows_from_sheet(wb, MODEL_CONFIG.source_option_sheet)
    statuses_raw = rows_from_sheet(wb, "option_variant_status")
    rules_raw = rows_from_sheet(wb, "rule_mapping")
    price_rules_raw = rows_from_sheet(wb, "price_rules")
    lt_interiors_raw = rows_from_sheet(wb, "lt_interiors")
    lz_interiors_raw = rows_from_sheet(wb, "LZ_Interiors")
    price_ref_rows = rows_from_sheet(wb, "PriceRef")
    price_ref = price_ref_prices(price_ref_rows)
    interior_component_price_ref = price_ref_component_prices(price_ref_rows)
    color_overrides_raw = rows_from_sheet(wb, "color_overrides")
    interior_reference_by_id, interior_reference_rows = read_interior_reference()

    status_by_option_variant_raw = {(row["option_id"], row["variant_id"]): row["status"].lower() for row in statuses_raw}
    for option in options_raw:
        original_option_id = option["option_id"]
        option["option_id"] = canonical_option_id(original_option_id)
        if option["option_id"] in CONSOLIDATED_ENGINE_COVERS:
            option["price"] = "695"
        if option["option_id"] == "opt_t0a_001":
            option["section_id"] = "sec_spoi_001"
            option["selectable"] = "True"
            option["display_order"] = "25"
        if option["option_id"] == "opt_fe3_001":
            option["section_id"] = "sec_susp_001"
            option["selectable"] = "False"
            option["display_order"] = "12"
        if option["option_id"] == "opt_zyc_001":
            option["display_order"] = "15"
        if option["option_id"] in ENGINE_APPEARANCE_OPTION_ORDER:
            option["display_order"] = str(ENGINE_APPEARANCE_OPTION_ORDER[option["option_id"]])
        if original_option_id in HIDDEN_OPTION_IDS or option.get("section_id") in HIDDEN_SECTION_IDS:
            option["active"] = "False"

    for row in statuses_raw:
        row["option_id"] = canonical_option_id(row["option_id"])
        if row["option_id"] in CONSOLIDATED_ENGINE_COVERS:
            alias_status = status_by_option_variant_raw.get((f"{row['option_id'][:-3]}002", row["variant_id"]), row["status"])
            row["status"] = best_status(row["status"], alias_status)
        if row["option_id"] == "opt_bc7_001" and row["variant_id"].endswith("c67"):
            row["status"] = "available"

    for rule in rules_raw:
        rule["source_id"] = canonical_option_id(rule.get("source_id", ""))
        rule["target_id"] = canonical_option_id(rule.get("target_id", ""))

    existing_price_rule_ids = {row.get("price_rule_id", "") for row in price_rules_raw}
    for option_id in sorted(CONSOLIDATED_ENGINE_COVERS):
        engine_cover_price_rules = [
            {
                "price_rule_id": f"pr_b6p_coupe_{option_id}_001",
                "condition_option_id": "opt_b6p_001",
                "body_style_scope": "coupe",
                "notes": "B6P selected sets coupe LS6 engine cover price to 595",
            },
            {
                "price_rule_id": f"pr_zz3_convertible_{option_id}_001",
                "condition_option_id": "opt_zz3_001",
                "body_style_scope": "convertible",
                "notes": "ZZ3 selected sets convertible LS6 engine cover price to 595",
            },
        ]
        for price_rule in engine_cover_price_rules:
            if price_rule["price_rule_id"] in existing_price_rule_ids:
                continue
            price_rules_raw.append(
                {
                    "price_rule_id": price_rule["price_rule_id"],
                    "condition_option_id": price_rule["condition_option_id"],
                    "target_option_id": option_id,
                    "price_rule_type": "override",
                    "price_value": "595",
                    "body_style_scope": price_rule["body_style_scope"],
                    "trim_level_scope": "",
                    "variant_scope": "",
                    "review_flag": "False",
                    "notes": price_rule["notes"],
                }
            )

    active_variants = [
        {
            "variant_id": row["variant_id"],
            "model_year": intish(row.get("model_year")),
            "trim_level": row["trim_level"].upper(),
            "body_style": row["body_style"].lower(),
            "display_name": row["display_name"],
            "base_price": money(row.get("base_price")),
            "display_order": intish(row.get("display_order")),
        }
        for row in variants_raw
        if row.get("active") == "True" and row.get("variant_id", "") in MODEL_CONFIG.variant_ids
    ]
    variant_by_id = {row["variant_id"]: row for row in active_variants}

    section_rows: list[dict[str, Any]] = [dict(row) for row in CONTEXT_SECTIONS]
    for section_id, section in sections.items():
        category = categories.get(section.get("category_id", ""), {})
        step_key = step_for_section(section_id, section.get("section_name", ""), section.get("category_id", ""))
        selection_mode = SECTION_MODE_OVERRIDES.get(section_id, section.get("selection_mode", ""))
        section_display_order = SECTION_DISPLAY_ORDER_OVERRIDES.get(
            section_id,
            AERO_EXHAUST_ACCESSORIES_SECTION_ORDER.get(section_id, intish(section.get("display_order"))),
        )
        section_rows.append(
            {
                "section_id": section_id,
                "section_name": section.get("section_name", ""),
                "category_id": section.get("category_id", ""),
                "category_name": category.get("category_name", ""),
                "selection_mode": selection_mode,
                "selection_mode_label": selection_mode_label(selection_mode),
                "choice_mode": normalize_mode(selection_mode),
                "is_required": section.get("is_required", ""),
                "standard_behavior": section.get("standard_behavior", ""),
                "section_display_order": section_display_order,
                "step_key": step_key,
                "step_label": STEP_LABELS.get(step_key, step_key.replace("_", " ").title()),
            }
        )

    step_rows: list[dict[str, Any]] = [
        {
            "step_key": step_key,
            "step_label": STEP_LABELS[step_key],
            "runtime_order": idx + 1,
            "source": "runtime",
            "section_ids": "",
        }
        for idx, step_key in enumerate(STEP_ORDER)
    ]
    section_ids_by_step: dict[str, list[str]] = defaultdict(list)
    for row in section_rows:
        section_ids_by_step[row["step_key"]].append(row["section_id"])
    for row in step_rows:
        row["section_ids"] = "|".join(sorted(section_ids_by_step.get(row["step_key"], [])))

    body_context_choices = []
    body_styles = sorted(
        {row["body_style"] for row in active_variants},
        key=lambda body_style: BODY_STYLE_DISPLAY_ORDER.get(body_style, 99),
    )
    for body_style in body_styles:
        body_variants = [row for row in active_variants if row["body_style"] == body_style]
        body_context_choices.append(
            {
                "context_choice_id": f"body_style__{body_style}",
                "context_type": "body_style",
                "value": body_style,
                "label": body_style.title(),
                "description": f"{len(body_variants)} trims available",
                "section_id": "sec_context_body_style",
                "step_key": "body_style",
                "body_style": body_style,
                "trim_level": "",
                "variant_id": "",
                "base_price": "",
                "display_order": BODY_STYLE_DISPLAY_ORDER.get(body_style, 99),
            }
        )
    trim_context_choices = []
    for variant in active_variants:
        trim_context_choices.append(
            {
                "context_choice_id": f"trim_level__{variant['body_style']}__{variant['trim_level'].lower()}",
                "context_type": "trim_level",
                "value": variant["trim_level"],
                "label": variant["trim_level"],
                "description": variant["display_name"],
                "section_id": "sec_context_trim_level",
                "step_key": "trim_level",
                "body_style": variant["body_style"],
                "trim_level": variant["trim_level"],
                "variant_id": variant["variant_id"],
                "base_price": variant["base_price"],
                "display_order": variant["display_order"],
            }
        )
    context_choices = body_context_choices + trim_context_choices

    options_by_id: dict[str, dict[str, Any]] = {}
    for option in options_raw:
        if option["option_id"] in options_by_id and option.get("active") != "True":
            continue
        section = sections.get(option.get("section_id", ""), {})
        category = categories.get(section.get("category_id", ""), {})
        step_key = step_for_section(option.get("section_id", ""), section.get("section_name", ""), section.get("category_id", ""))
        mode = SECTION_MODE_OVERRIDES.get(option.get("section_id", ""), section.get("selection_mode", ""))
        options_by_id[option["option_id"]] = {
            "option_id": option["option_id"],
            "rpo": option.get("rpo", ""),
            "label": option.get("option_name", ""),
            "description": option.get("description", ""),
            "source_detail_raw": option.get("detail_raw", ""),
            "section_id": option.get("section_id", ""),
            "section_name": section.get("section_name", ""),
            "category_id": section.get("category_id", ""),
            "category_name": category.get("category_name", ""),
            "step_key": step_key,
            "selection_mode": mode,
            "selection_mode_label": selection_mode_label(mode),
            "choice_mode": normalize_mode(mode),
            "selectable": option.get("selectable", ""),
            "active": option.get("active", ""),
            "base_price": money(option.get("price")),
            "display_order": intish(option.get("display_order")),
        }

    status_by_option_variant: dict[tuple[str, str], str] = {}
    for row in statuses_raw:
        key = (row["option_id"], row["variant_id"])
        status_by_option_variant[key] = best_status(status_by_option_variant.get(key, ""), row["status"])
    choices: list[dict[str, Any]] = []
    for option_id, option in options_by_id.items():
        if option["active"] != "True":
            continue
        for variant in active_variants:
            status = status_by_option_variant.get((option_id, variant["variant_id"]), "unavailable")
            selectable = option["selectable"]
            active = option["active"]
            if option_id == "opt_uqt_002" and variant["trim_level"] != "1LT":
                status = "unavailable"
                selectable = "False"
                active = "False"
            if option_id in AUTO_ONLY_OPTION_IDS:
                status = "unavailable"
                selectable = "False"
                active = "False"
            if option_id in DISPLAY_ONLY_OPTION_IDS:
                status = "available"
                selectable = "False"
                active = "True"
            choices.append(
                {
                    "choice_id": f"{variant['variant_id']}__{option_id}",
                    "option_id": option_id,
                    "rpo": option["rpo"],
                    "label": option["label"],
                    "description": option["description"],
                    "section_id": option["section_id"],
                    "section_name": option["section_name"],
                    "category_id": option["category_id"],
                    "category_name": option["category_name"],
                    "step_key": option["step_key"],
                    "variant_id": variant["variant_id"],
                    "body_style": variant["body_style"],
                    "trim_level": variant["trim_level"],
                    "status": status,
                    "status_label": status_to_label(status),
                    "selectable": selectable,
                    "active": active,
                    "choice_mode": option["choice_mode"],
                    "selection_mode": option["selection_mode"],
                    "selection_mode_label": option["selection_mode_label"],
                    "base_price": option["base_price"],
                    "display_order": option["display_order"],
                    "source_detail_raw": option["source_detail_raw"],
                }
            )

    interiors: list[dict[str, Any]] = []
    for row in lt_interiors_raw:
        trim = row.get("Trim", "")
        interior_id = row.get("interior_id", "")
        components = interior_component_metadata(row, interior_component_price_ref)
        interiors.append(
            {
                "interior_id": interior_id,
                "source_sheet": "lt_interiors",
                "active_for_stingray": trim in {"1LT", "2LT", "3LT", "3LT_R6X"} and interior_id not in GRAND_SPORT_ONLY_INTERIOR_IDS,
                "trim_level": trim.replace("_R6X", ""),
                "requires_r6x": "True" if "_R6X" in trim or row.get("interior_id", "").endswith("_R6X") else "False",
                "seat_code": row.get("Seat", ""),
                "interior_code": row.get("Interior Code", ""),
                "interior_name": row.get("Interior Name", ""),
                "material": row.get("Material", ""),
                "price": generated_interior_price(row, price_ref),
                "suede": row.get("Suede", ""),
                "stitch": row.get("Stitch", ""),
                "two_tone": row.get("Two Tone", ""),
                "section_id": row.get("section_id", ""),
                "color_overrides_raw": row.get("Color Overrides", ""),
                "source_note": row.get("Detail from Disclosure", ""),
                "interior_components": components,
                "interior_components_json": json.dumps(components, separators=(",", ":")),
            }
        )
    for row in lz_interiors_raw:
        components = interior_component_metadata(row, interior_component_price_ref)
        interiors.append(
            {
                "interior_id": row.get("ID", ""),
                "source_sheet": "LZ_Interiors",
                "active_for_stingray": False,
                "trim_level": row.get("Trim", "").replace("_R6X", ""),
                "requires_r6x": "True" if "_R6X" in row.get("Trim", "") or row.get("ID", "").endswith("_R6X") else "False",
                "seat_code": row.get("Seat", ""),
                "interior_code": row.get("Interior Code", ""),
                "interior_name": row.get("Interior Name", ""),
                "material": row.get("Material", ""),
                "price": generated_interior_price(row, price_ref),
                "suede": row.get("Suede", ""),
                "stitch": row.get("Stitch", ""),
                "two_tone": row.get("Two Tone", ""),
                "section_id": "",
                "color_overrides_raw": row.get("Color Overrides", ""),
                "source_note": row.get("Detail from Disclosure", ""),
                "interior_components": components,
                "interior_components_json": json.dumps(components, separators=(",", ":")),
            }
        )
    validation_rows: list[dict[str, Any]] = []
    reference_order_by_id = {
        row["interior_id"]: index
        for index, row in enumerate((row for row in interior_reference_rows if row["interior_id"]), start=1)
    }
    active_interior_ids = {
        row["interior_id"]
        for row in interiors
        if row["interior_id"] and row["active_for_stingray"]
    }
    all_interior_ids = {row["interior_id"] for row in interiors if row["interior_id"]}
    for interior_id, reference in interior_reference_by_id.items():
        if interior_id not in all_interior_ids:
            validation_rows.append(
                {
                    "check_id": f"missing_reference_interior_{interior_id}",
                    "severity": "error",
                    "entity_type": "interior",
                    "entity_id": interior_id,
                    "message": f"Interior reference row {reference['row_number']} does not resolve to generated interior data.",
                }
            )
        elif interior_id not in active_interior_ids:
            validation_rows.append(
                {
                    "check_id": f"inactive_reference_interior_{interior_id}",
                    "severity": "error",
                    "entity_type": "interior",
                    "entity_id": interior_id,
                    "message": f"Interior reference row {reference['row_number']} resolves to an inactive Stingray interior.",
                }
            )

    fallback_order = len(reference_order_by_id) + 1
    for row in interiors:
        if not row["interior_id"]:
            continue
        reference = interior_reference_by_id.get(row["interior_id"])
        if row["active_for_stingray"] and reference:
            row.update(grouping_fields_for_interior(row, reference, reference_order_by_id[row["interior_id"]]))
        elif row["active_for_stingray"]:
            row.update(grouping_fields_for_interior(row, None, fallback_order, fallback=True))
            fallback_order += 1
            validation_rows.append(
                {
                    "check_id": f"unmapped_active_interior_{row['interior_id']}",
                    "severity": "warning",
                    "entity_type": "interior",
                    "entity_id": row["interior_id"],
                    "message": "Active Stingray interior is not represented in the CSV hierarchy and was placed in Other Interior Choices.",
                }
            )
        else:
            row.update(grouping_fields_for_interior(row, reference, reference_order_by_id.get(row["interior_id"], fallback_order)))

    interiors_by_id = {row["interior_id"]: row for row in interiors if row["interior_id"]}
    r6x_interior_ids = [
        row["interior_id"]
        for row in interiors
        if row["interior_id"] and row["active_for_stingray"] and row["requires_r6x"] == "True"
    ]
    existing_price_rule_ids = {row.get("price_rule_id", "") for row in price_rules_raw}
    if "pr_d30_r6x_001" not in existing_price_rule_ids:
        price_rules_raw.append(
            {
                "price_rule_id": "pr_d30_r6x_001",
                "condition_option_id": "opt_d30_001",
                "target_option_id": "opt_r6x_001",
                "price_rule_type": "override",
                "price_value": "0",
                "review_flag": "False",
                "notes": "R6X prices at $0 only when D30 is present in the selected context.",
            }
        )

    raw_rules: list[dict[str, Any]] = []
    manual_rules = [
        {
            "rule_id": "rule_opt_t0a_001_requires_opt_z51_001",
            "source_id": "opt_t0a_001",
            "rule_type": "requires",
            "target_id": "opt_z51_001",
            "target_type": "option",
            "source_type": "option",
            "source_section": "sec_spoi_001",
            "target_section": "sec_perf_001",
            "source_selection_mode": "single_select_opt",
            "target_selection_mode": "multi_select_opt",
            "original_detail_raw": "T0A is available only when Z51 is selected.",
            "review_flag": "False",
        },
        {
            "rule_id": "rule_opt_tvs_001_excludes_opt_t0a_001",
            "source_id": "opt_tvs_001",
            "rule_type": "excludes",
            "target_id": "opt_t0a_001",
            "target_type": "option",
            "source_type": "option",
            "source_section": "sec_spoi_001",
            "target_section": "sec_spoi_001",
            "source_selection_mode": "single_select_opt",
            "target_selection_mode": "single_select_opt",
            "original_detail_raw": "TVS replaces the default T0A Z51 spoiler when selected.",
            "review_flag": "False",
        },
        {
            "rule_id": "rule_opt_bc7_001_requires_opt_zz3_001_convertible",
            "source_id": "opt_bc7_001",
            "rule_type": "requires",
            "target_id": "opt_zz3_001",
            "target_type": "option",
            "source_type": "option",
            "source_section": "sec_engi_001",
            "target_section": "sec_engi_001",
            "source_selection_mode": "multi_select_opt",
            "target_selection_mode": "multi_select_opt",
            "original_detail_raw": "BC7 requires ZZ3 Convertible Engine Appearance Package on Convertible.",
            "review_flag": "False",
        },
    ]
    for interior_id in r6x_interior_ids:
        manual_rules.append(
            {
                "rule_id": f"rule_{interior_id.lower()}_includes_opt_r6x_001",
                "source_id": interior_id,
                "rule_type": "includes",
                "target_id": "opt_r6x_001",
                "target_type": "option",
                "source_type": "interior",
                "source_section": interiors_by_id[interior_id].get("section_id", ""),
                "target_section": "sec_colo_001",
                "source_selection_mode": "single_select_req",
                "target_selection_mode": "multi_select_opt",
                "original_detail_raw": "R6X is included with this custom interior trim and seat combination.",
                "review_flag": "False",
            }
        )
    for rule in rules_raw + manual_rules:
        rule_type = rule.get("rule_type", "").lower()
        source_id = rule.get("source_id", "")
        target_id = rule.get("target_id", "")
        if source_id in CONSOLIDATED_ENGINE_COVERS and target_id == "opt_b6p_001" and rule_type in {"excludes", "requires"}:
            continue
        if source_id == "opt_5v7_001" and rule_type == "requires" and target_id in FIVE_V7_OR_REQUIREMENT_TARGET_IDS:
            continue
        if source_id == "opt_5zu_001" and rule_type == "requires" and target_id in FIVE_ZU_OR_REQUIREMENT_TARGET_IDS:
            continue
        if source_id in HIDDEN_OPTION_IDS or target_id in HIDDEN_OPTION_IDS:
            continue
        source_section = rule.get("source_section", "")
        target_section = rule.get("target_section", "")
        source_mode = SECTION_MODE_OVERRIDES.get(source_section, rule.get("source_selection_mode", ""))
        target_mode = SECTION_MODE_OVERRIDES.get(target_section, rule.get("target_selection_mode", ""))
        body_style_scope = rule_body_style_scope(rule, source_id, target_id)
        replaces_t0a = rule_type == "excludes" and target_id == "opt_t0a_001" and source_id in T0A_REPLACEMENT_OPTION_IDS
        redundant = (
            rule_type == "excludes"
            and source_section
            and source_section == target_section
            and source_mode.startswith("single")
            and target_mode.startswith("single")
            and not replaces_t0a
        )
        action = "replace" if replaces_t0a else "omit_redundant_same_section_exclude" if redundant else "active"
        if redundant:
            validation_rows.append(
                {
                    "check_id": f"redundant_{rule.get('rule_id', '')}",
                    "severity": "info",
                    "entity_type": "rule",
                    "entity_id": rule.get("rule_id", ""),
                    "message": "Same-section single-select excludes are redundant because the section choice mode already prevents multiple selections.",
                }
            )
        disabled_reason = ""
        auto_add = "False"
        source_label = label_for(source_id, options_by_id, interiors_by_id)
        target_label = label_for(target_id, options_by_id, interiors_by_id)
        if replaces_t0a:
            disabled_reason = "Removes T0A when Z51 is selected."
        elif rule_type == "excludes":
            disabled_reason = f"Blocked by {source_label}."
        elif rule_type == "requires":
            disabled_reason = f"Requires {target_label}."
        elif rule_type == "includes":
            disabled_reason = f"Included with {source_label}."
            auto_add = "True"
        raw_rules.append(
            {
                "rule_id": rule.get("rule_id", ""),
                "source_id": source_id,
                "rule_type": rule_type,
                "target_id": target_id,
                "target_type": rule.get("target_type", ""),
                "source_type": rule.get("source_type", ""),
                "source_section": source_section,
                "target_section": target_section,
                "source_selection_mode": source_mode,
                "target_selection_mode": target_mode,
                "body_style_scope": body_style_scope,
                "disabled_reason": disabled_reason,
                "auto_add": auto_add,
                "active": "False" if redundant else "True",
                "runtime_action": action,
                "source_note": truncate_reason(rule.get("original_detail_raw", ""), 500),
                "review_flag": rule.get("review_flag", ""),
            }
        )

    price_rules = [
        {
            "price_rule_id": row.get("price_rule_id", ""),
            "condition_option_id": canonical_option_id(row.get("condition_option_id", "")),
            "target_option_id": canonical_option_id(row.get("target_option_id", "")),
            "price_rule_type": row.get("price_rule_type", "").lower(),
            "price_value": money(row.get("price_value")),
            "body_style_scope": row.get("body_style_scope", ""),
            "trim_level_scope": row.get("trim_level_scope", ""),
            "variant_scope": row.get("variant_scope", ""),
            "review_flag": row.get("review_flag", ""),
            "notes": row.get("notes", ""),
        }
        for row in price_rules_raw
        if row.get("condition_option_id", "") not in HIDDEN_OPTION_IDS and row.get("target_option_id", "") not in HIDDEN_OPTION_IDS
    ]

    color_overrides = [
        {
            "override_id": f"co_{idx:03d}",
            "interior_id": row.get("interior_id", ""),
            "option_id": row.get("option_id", ""),
            "rule_type": row.get("rule_type", "").lower(),
            "adds_rpo": row.get("adds_rpo", ""),
            "notes": "Exterior/interior pairing requires the listed override RPO.",
        }
        for idx, row in enumerate(color_overrides_raw, start=1)
    ]

    # Validation floor
    if len(active_variants) != 6:
        validation_rows.append(
            {
                "check_id": "active_variant_count",
                "severity": "error",
                "entity_type": "variant",
                "entity_id": "",
                "message": f"Expected 6 active Stingray variants; found {len(active_variants)}.",
            }
        )
    expected_status_rows = len(active_variants) * len(options_by_id)
    canonical_status_rows = len({(row["option_id"], row["variant_id"]) for row in statuses_raw})
    if canonical_status_rows != expected_status_rows:
        validation_rows.append(
            {
                "check_id": "availability_row_count",
                "severity": "error",
                "entity_type": "availability",
                "entity_id": "",
                "message": f"Expected {expected_status_rows} canonical option_variant_status rows; found {canonical_status_rows}.",
            }
        )
    valid_ids = set(options_by_id) | set(interiors_by_id)
    for rule in raw_rules:
        for key in ["source_id", "target_id"]:
            if rule[key] not in valid_ids:
                validation_rows.append(
                    {
                        "check_id": f"missing_{key}_{rule['rule_id']}",
                        "severity": "error",
                        "entity_type": "rule",
                        "entity_id": rule["rule_id"],
                        "message": f"{key} {rule[key]} does not resolve to an option or interior.",
                    }
                )
    for rule in price_rules:
        for key in ["condition_option_id", "target_option_id"]:
            if rule[key] not in valid_ids:
                validation_rows.append(
                    {
                        "check_id": f"missing_{key}_{rule['price_rule_id']}",
                        "severity": "error",
                        "entity_type": "price_rule",
                        "entity_id": rule["price_rule_id"],
                        "message": f"{key} {rule[key]} does not resolve to an option or interior.",
                    }
                )

    status_counts = Counter(row["status"] for row in choices)
    standard_equipment = [
        {
            "equipment_id": f"std_{choice['variant_id']}__{choice['option_id']}",
            "variant_id": choice["variant_id"],
            "body_style": choice["body_style"],
            "trim_level": choice["trim_level"],
            "option_id": choice["option_id"],
            "rpo": choice["rpo"],
            "label": choice["label"],
            "description": choice["description"],
            "section_id": choice["section_id"],
            "section_name": choice["section_name"],
            "category_name": choice["category_name"],
            "display_order": choice["display_order"],
            "source_detail_raw": choice["source_detail_raw"],
        }
        for choice in choices
        if choice["status"] == "standard" and (choice["step_key"] == "standard_equipment" or choice["selectable"] != "True")
    ]
    validation_rows.extend(
        [
            {
                "check_id": "active_variants",
                "severity": "pass",
                "entity_type": "variant",
                "entity_id": "",
                "message": f"{len(active_variants)} active Stingray variants exported.",
            },
            {
                "check_id": "availability_rows",
                "severity": "pass",
                "entity_type": "availability",
                "entity_id": "",
                "message": f"{len(choices)} choice rows exported ({dict(status_counts)}).",
            },
            {
                "check_id": "rules",
                "severity": "pass",
                "entity_type": "rule",
                "entity_id": "",
                "message": f"{sum(1 for row in raw_rules if row['active'] == 'True')} active compatibility rules exported from {len(raw_rules)} source rules.",
            },
        ]
    )

    write_sheet(
        wb,
        "form_steps",
        ["step_key", "step_label", "runtime_order", "source", "section_ids"],
        step_rows,
    )
    write_sheet(
        wb,
        "form_context_choices",
        [
            "context_choice_id",
            "context_type",
            "value",
            "label",
            "description",
            "section_id",
            "step_key",
            "body_style",
            "trim_level",
            "variant_id",
            "base_price",
            "display_order",
        ],
        context_choices,
    )
    write_sheet(
        wb,
        "form_choices",
        [
            "choice_id",
            "option_id",
            "rpo",
            "label",
            "description",
            "section_id",
            "section_name",
            "category_id",
            "category_name",
            "step_key",
            "variant_id",
            "body_style",
            "trim_level",
            "status",
            "status_label",
            "selectable",
            "active",
            "choice_mode",
            "selection_mode",
            "selection_mode_label",
            "base_price",
            "display_order",
            "source_detail_raw",
        ],
        choices,
    )
    write_sheet(
        wb,
        "form_standard_equipment",
        [
            "equipment_id",
            "variant_id",
            "body_style",
            "trim_level",
            "option_id",
            "rpo",
            "label",
            "description",
            "section_id",
            "section_name",
            "category_name",
            "display_order",
            "source_detail_raw",
        ],
        standard_equipment,
    )
    write_sheet(
        wb,
        "form_rule_groups",
        [
            "group_id",
            "group_type",
            "source_id",
            "target_ids",
            "body_style_scope",
            "trim_level_scope",
            "variant_scope",
            "disabled_reason",
            "active",
            "notes",
        ],
        [{**row, "target_ids": "|".join(row["target_ids"])} for row in RULE_GROUPS],
    )
    write_sheet(
        wb,
        "form_exclusive_groups",
        ["group_id", "option_ids", "selection_mode", "active", "notes"],
        [{**row, "option_ids": "|".join(row["option_ids"])} for row in EXCLUSIVE_GROUPS],
    )
    write_sheet(
        wb,
        "form_rules",
        [
            "rule_id",
            "source_id",
            "rule_type",
            "target_id",
            "target_type",
            "source_type",
            "source_section",
            "target_section",
            "source_selection_mode",
            "target_selection_mode",
            "body_style_scope",
            "disabled_reason",
            "auto_add",
            "active",
            "runtime_action",
            "source_note",
            "review_flag",
        ],
        raw_rules,
    )
    write_sheet(
        wb,
        "form_price_rules",
        [
            "price_rule_id",
            "condition_option_id",
            "target_option_id",
            "price_rule_type",
            "price_value",
            "body_style_scope",
            "trim_level_scope",
            "variant_scope",
            "review_flag",
            "notes",
        ],
        price_rules,
    )
    write_sheet(
        wb,
        "form_interiors",
        [
            "interior_id",
            "source_sheet",
            "active_for_stingray",
            "trim_level",
            "requires_r6x",
            "seat_code",
            "interior_code",
            "interior_name",
            "material",
            "price",
            "suede",
            "stitch",
            "two_tone",
            "section_id",
            "color_overrides_raw",
            "source_note",
            "interior_components_json",
            "interior_trim_level",
            "interior_seat_code",
            "interior_seat_label",
            "interior_color_family",
            "interior_material_family",
            "interior_variant_label",
            "interior_group_display_order",
            "interior_material_display_order",
            "interior_choice_display_order",
            "interior_hierarchy_levels",
            "interior_hierarchy_path",
            "interior_parent_group_label",
            "interior_leaf_label",
            "interior_reference_order",
        ],
        interiors,
    )
    write_sheet(
        wb,
        "form_color_overrides",
        ["override_id", "interior_id", "option_id", "rule_type", "adds_rpo", "notes"],
        color_overrides,
    )
    write_sheet(
        wb,
        "form_validation",
        ["check_id", "severity", "entity_type", "entity_id", "message"],
        validation_rows,
    )
    wb.save(WORKBOOK_PATH)

    generated_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    data = {
        "dataset": {
            "name": MODEL_CONFIG.dataset_name,
            "source_workbook": WORKBOOK_PATH.name,
            "generated_at": generated_at,
        },
        "variants": active_variants,
        "steps": step_rows,
        "sections": section_rows,
        "contextChoices": context_choices,
        "choices": choices,
        "standardEquipment": standard_equipment,
        "ruleGroups": RULE_GROUPS,
        "exclusiveGroups": EXCLUSIVE_GROUPS,
        "rules": [row for row in raw_rules if row["active"] == "True"],
        "priceRules": price_rules,
        "interiors": [row for row in interiors if row["active_for_stingray"]],
        "colorOverrides": color_overrides,
        "validation": validation_rows,
    }

    OUTPUT_DIR.mkdir(exist_ok=True)
    APP_DIR.mkdir(exist_ok=True)
    json_path = OUTPUT_DIR / "stingray-form-data.json"
    write_json_output(json_path, data)
    write_app_data(APP_DIR / "data.js", "STINGRAY_FORM_DATA", data)
    csv_path = OUTPUT_DIR / "stingray-form-data.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            lineterminator="\n",
            fieldnames=[
                "choice_id",
                "option_id",
                "rpo",
                "label",
                "section_id",
                "step_key",
                "variant_id",
                "body_style",
                "trim_level",
                "status",
                "selectable",
                "base_price",
            ],
        )
        writer.writeheader()
        for row in choices:
            writer.writerow({key: row.get(key, "") for key in writer.fieldnames})

    print(json.dumps({
        "workbook": str(WORKBOOK_PATH),
        "json": str(json_path),
        "csv": str(csv_path),
        "choices": len(choices),
        "context_choices": len(context_choices),
        "standard_equipment": len(standard_equipment),
        "rules": len(data["rules"]),
        "price_rules": len(price_rules),
        "interiors": len(data["interiors"]),
        "validation_errors": validation_error_count(validation_rows),
    }, indent=2))


if __name__ == "__main__":
    main()
