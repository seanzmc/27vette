#!/usr/bin/env python3
"""Generate the Stingray form contract and static-app data from stingray_master.xlsx."""

from __future__ import annotations

import csv
import json
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from openpyxl import load_workbook
from openpyxl.styles import Font, PatternFill
from openpyxl.utils import get_column_letter


ROOT = Path(__file__).resolve().parents[1]
WORKBOOK_PATH = ROOT / "stingray_master.xlsx"
OUTPUT_DIR = ROOT / "form-output"
APP_DIR = ROOT / "form-app"

GENERATED_SHEETS = [
    "form_steps",
    "form_context_choices",
    "form_choices",
    "form_standard_equipment",
    "form_rules",
    "form_price_rules",
    "form_interiors",
    "form_color_overrides",
    "form_validation",
]

STEP_ORDER = [
    "body_style",
    "trim_level",
    "paint",
    "exterior_appearance",
    "wheels",
    "calipers",
    "packages_performance",
    "aero_exhaust_stripes_accessories",
    "seat",
    "base_interior",
    "seat_belt",
    "interior_trim",
    "delivery",
    "customer_info",
    "summary",
]

STEP_LABELS = {
    "body_style": "Body Style",
    "trim_level": "Trim Level",
    "paint": "Exterior Paint",
    "exterior_appearance": "Exterior Appearance",
    "wheels": "Wheels",
    "calipers": "Brake Calipers",
    "packages_performance": "Packages & Performance",
    "aero_exhaust_stripes_accessories": "Aero, Exhaust, Stripes & Accessories",
    "seat": "Seats",
    "base_interior": "Base Interior",
    "seat_belt": "Seat Belt",
    "interior_trim": "Interior Trim",
    "delivery": "Custom Delivery",
    "customer_info": "Customer Information",
    "summary": "Summary",
    "standard_equipment": "Standard Equipment",
}

CONTEXT_SECTIONS = [
    {
        "section_id": "sec_context_body_style",
        "section_name": "Body Style",
        "category_id": "cat_context_001",
        "category_name": "Vehicle Context",
        "selection_mode": "single_select_req",
        "selection_mode_label": "Required single choice",
        "choice_mode": "single",
        "is_required": "True",
        "standard_behavior": "user_selected",
        "section_display_order": 1,
        "step_key": "body_style",
        "step_label": "Body Style",
    },
    {
        "section_id": "sec_context_trim_level",
        "section_name": "Trim Level",
        "category_id": "cat_context_001",
        "category_name": "Vehicle Context",
        "selection_mode": "single_select_req",
        "selection_mode_label": "Required single choice",
        "choice_mode": "single",
        "is_required": "True",
        "standard_behavior": "user_selected",
        "section_display_order": 2,
        "step_key": "trim_level",
        "step_label": "Trim Level",
    },
]

SECTION_STEP_OVERRIDES = {
    "sec_pain_001": "paint",
    "sec_whee_002": "wheels",
    "sec_cali_001": "calipers",
    "sec_roof_001": "exterior_appearance",
    "sec_exte_001": "exterior_appearance",
    "sec_badg_001": "exterior_appearance",
    "sec_engi_001": "exterior_appearance",
    "sec_perf_001": "packages_performance",
    "sec_susp_001": "packages_performance",
    "sec_seat_002": "seat",
    "sec_intc_001": "base_interior",
    "sec_intc_002": "base_interior",
    "sec_intc_003": "base_interior",
    "sec_seat_001": "seat_belt",
    "sec_inte_001": "interior_trim",
    "sec_lpoi_001": "interior_trim",
    "sec_gsce_001": "exterior_appearance",
    "sec_onst_001": "interior_trim",
    "sec_cust_001": "delivery",
}

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

AUTO_ONLY_OPTION_IDS = {"opt_d30_001"}

BODY_STYLE_DISPLAY_ORDER = {
    "coupe": 1,
    "convertible": 2,
}

AERO_EXHAUST_ACCESSORIES_SECTION_ORDER = {
    "sec_exha_001": 10,
    "sec_spoi_001": 20,
    "sec_stri_001": 30,
    "sec_lpoe_001": 40,
    "sec_lpow_001": 50,
    "sec_whee_001": 60,
}

FIVE_V7_OR_REQUIREMENT_TARGET_IDS = {"opt_5zu_001", "opt_5zz_001", "opt_5zw_001"}
FIVE_ZU_OR_REQUIREMENT_TARGET_IDS = {"opt_g8g_001", "opt_gba_001", "opt_gkz_001"}

SELECTION_MODE_LABELS = {
    "single_select_req": "Required single choice",
    "single_select_opt": "Optional single choice",
    "multi_select_opt": "Optional multiple choice",
    "display_only": "Display only",
}

STANDARD_SECTIONS = {
    "sec_1lte_001",
    "sec_2lte_001",
    "sec_3lte_001",
    "sec_incl_001",
    "sec_stan_001",
    "sec_stan_002",
    "sec_safe_001",
    "sec_tech_001",
}


def clean(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "True" if value else "False"
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value).strip()


def money(value: Any) -> int:
    text = clean(value).replace("$", "").replace(",", "")
    if not text:
        return 0
    try:
        return int(round(float(text)))
    except ValueError:
        return 0


def intish(value: Any, default: int = 0) -> int:
    text = clean(value)
    if not text:
        return default
    try:
        return int(float(text))
    except ValueError:
        return default


def rows_from_sheet(wb, sheet_name: str) -> list[dict[str, str]]:
    ws = wb[sheet_name]
    headers = [clean(ws.cell(1, col).value) for col in range(1, ws.max_column + 1)]
    rows: list[dict[str, str]] = []
    for row in ws.iter_rows(min_row=2, values_only=True):
        record: dict[str, str] = {}
        for header, value in zip(headers, row):
            if header:
                record[header] = clean(value)
        if any(record.values()):
            rows.append(record)
    return rows


def step_for_section(section_id: str, section_name: str, category_id: str) -> str:
    if section_id in STANDARD_SECTIONS:
        return "standard_equipment"
    if section_id in SECTION_STEP_OVERRIDES:
        return SECTION_STEP_OVERRIDES[section_id]
    name = section_name.lower()
    if "stripe" in name or "spoiler" in name or "lpo" in name or "exhaust" in name or "wheel accessory" in name:
        return "aero_exhaust_stripes_accessories"
    if category_id == "cat_exte_001":
        return "exterior_appearance"
    if category_id == "cat_inte_001":
        return "interior_trim"
    if category_id == "cat_mech_001":
        return "packages_performance"
    return "standard_equipment"


def status_to_label(status: str) -> str:
    return {
        "available": "Available",
        "standard": "Standard",
        "unavailable": "Not Available",
    }.get(status.lower(), status or "Unknown")


def normalize_mode(selection_mode: str) -> str:
    if selection_mode.startswith("single"):
        return "single"
    if selection_mode.startswith("multi"):
        return "multi"
    return "display"


def selection_mode_label(selection_mode: str) -> str:
    if not selection_mode:
        return ""
    return SELECTION_MODE_LABELS.get(selection_mode, selection_mode.replace("_", " ").title())


def canonical_option_id(option_id: str) -> str:
    return OPTION_ID_ALIASES.get(option_id, option_id)


def status_rank(status: str) -> int:
    return {"unavailable": 0, "available": 1, "standard": 2}.get(status, 0)


def best_status(*statuses: str) -> str:
    cleaned = [clean(status).lower() for status in statuses if clean(status)]
    if not cleaned:
        return "unavailable"
    return max(cleaned, key=status_rank)


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


def write_sheet(wb, name: str, headers: list[str], rows: list[dict[str, Any]]) -> None:
    if name in wb.sheetnames:
        del wb[name]
    ws = wb.create_sheet(name)
    ws.append(headers)
    for row in rows:
        ws.append([row.get(header, "") for header in headers])
    header_fill = PatternFill("solid", fgColor="1F2937")
    for cell in ws[1]:
        cell.font = Font(color="FFFFFF", bold=True)
        cell.fill = header_fill
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = ws.dimensions
    for idx, header in enumerate(headers, start=1):
        width = min(max(len(header) + 2, 12), 42)
        ws.column_dimensions[get_column_letter(idx)].width = width


def main() -> None:
    wb = load_workbook(WORKBOOK_PATH)

    variants_raw = rows_from_sheet(wb, "variant_master")
    categories = {row["category_id"]: row for row in rows_from_sheet(wb, "category_master")}
    sections = {row["section_id"]: row for row in rows_from_sheet(wb, "section_master")}
    options_raw = rows_from_sheet(wb, "stingray_master")
    statuses_raw = rows_from_sheet(wb, "option_variant_status")
    rules_raw = rows_from_sheet(wb, "rule_mapping")
    price_rules_raw = rows_from_sheet(wb, "price_rules")
    lt_interiors_raw = rows_from_sheet(wb, "lt_interiors")
    lz_interiors_raw = rows_from_sheet(wb, "LZ_Interiors")
    color_overrides_raw = rows_from_sheet(wb, "color_overrides")

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
        price_rule_id = f"pr_b6p_{option_id}_001"
        if price_rule_id in existing_price_rule_ids:
            continue
        price_rules_raw.append(
            {
                "price_rule_id": price_rule_id,
                "condition_option_id": "opt_b6p_001",
                "target_option_id": option_id,
                "price_rule_type": "override",
                "price_value": "595",
                "review_flag": "False",
                "notes": "B6P selected sets LS6 engine cover price to 595",
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
        if row.get("active") == "True" and row.get("variant_id", "").endswith(("c07", "c67"))
    ]
    variant_by_id = {row["variant_id"]: row for row in active_variants}

    section_rows: list[dict[str, Any]] = [dict(row) for row in CONTEXT_SECTIONS]
    for section_id, section in sections.items():
        category = categories.get(section.get("category_id", ""), {})
        step_key = step_for_section(section_id, section.get("section_name", ""), section.get("category_id", ""))
        section_display_order = AERO_EXHAUST_ACCESSORIES_SECTION_ORDER.get(section_id, intish(section.get("display_order")))
        section_rows.append(
            {
                "section_id": section_id,
                "section_name": section.get("section_name", ""),
                "category_id": section.get("category_id", ""),
                "category_name": category.get("category_name", ""),
                "selection_mode": section.get("selection_mode", ""),
                "selection_mode_label": selection_mode_label(section.get("selection_mode", "")),
                "choice_mode": normalize_mode(section.get("selection_mode", "")),
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
        mode = section.get("selection_mode", "")
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
        interiors.append(
            {
                "interior_id": row.get("interior_id", ""),
                "source_sheet": "lt_interiors",
                "active_for_stingray": trim in {"1LT", "2LT", "3LT", "3LT_R6X"},
                "trim_level": trim.replace("_R6X", ""),
                "requires_r6x": "True" if "_R6X" in trim or row.get("interior_id", "").endswith("_R6X") else "False",
                "seat_code": row.get("Seat", ""),
                "interior_code": row.get("Interior Code", ""),
                "interior_name": row.get("Interior Name", ""),
                "material": row.get("Material", ""),
                "price": interior_price(row),
                "suede": row.get("Suede", ""),
                "stitch": row.get("Stitch", ""),
                "two_tone": row.get("Two Tone", ""),
                "section_id": row.get("section_id", ""),
                "color_overrides_raw": row.get("Color Overrides", ""),
                "source_note": row.get("Detail from Disclosure", ""),
            }
        )
    for row in lz_interiors_raw:
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
                "price": interior_price(row),
                "suede": row.get("Suede", ""),
                "stitch": row.get("Stitch", ""),
                "two_tone": row.get("Two Tone", ""),
                "section_id": "",
                "color_overrides_raw": row.get("Color Overrides", ""),
                "source_note": row.get("Detail from Disclosure", ""),
            }
        )
    interiors_by_id = {row["interior_id"]: row for row in interiors if row["interior_id"]}

    raw_rules: list[dict[str, Any]] = []
    validation_rows: list[dict[str, Any]] = []
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
    ]
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
        source_mode = rule.get("source_selection_mode", "")
        target_mode = rule.get("target_selection_mode", "")
        body_style_scope = rule_body_style_scope(rule, source_id, target_id)
        redundant = (
            rule_type == "excludes"
            and source_section
            and source_section == target_section
            and source_mode.startswith("single")
            and target_mode.startswith("single")
            and target_id != "opt_t0a_001"
        )
        action = "omit_redundant_same_section_exclude" if redundant else "active"
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
        if rule_type == "excludes":
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
        ["price_rule_id", "condition_option_id", "target_option_id", "price_rule_type", "price_value", "review_flag", "notes"],
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
            "name": "2027 Corvette Stingray operational form",
            "source_workbook": WORKBOOK_PATH.name,
            "generated_at": generated_at,
        },
        "variants": active_variants,
        "steps": step_rows,
        "sections": section_rows,
        "contextChoices": context_choices,
        "choices": choices,
        "standardEquipment": standard_equipment,
        "rules": [row for row in raw_rules if row["active"] == "True"],
        "priceRules": price_rules,
        "interiors": [row for row in interiors if row["active_for_stingray"]],
        "colorOverrides": color_overrides,
        "validation": validation_rows,
    }

    OUTPUT_DIR.mkdir(exist_ok=True)
    APP_DIR.mkdir(exist_ok=True)
    json_path = OUTPUT_DIR / "stingray-form-data.json"
    json_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    (APP_DIR / "data.js").write_text(
        "window.STINGRAY_FORM_DATA = " + json.dumps(data, indent=2) + ";\n",
        encoding="utf-8",
    )
    csv_path = OUTPUT_DIR / "stingray-form-data.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
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
        "validation_errors": sum(1 for row in validation_rows if row["severity"] == "error"),
    }, indent=2))


if __name__ == "__main__":
    main()
