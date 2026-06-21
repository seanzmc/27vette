"""Production form-data generation: Stingray compatibility and runtime artifacts.

Currently parameterized for the active current-generation model (Stingray).
Invoked through ``scripts/generate_form.py``.
"""

from __future__ import annotations

import csv
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from typing import Any

from openpyxl import load_workbook
from corvette_form_generator.contract import (
    ASSET_IMAGE_FIELDS,
    build_body_context_choices,
    build_trim_context_choices,
    context_choice_copy_rows,
    label_for,
    option_asset_map,
)
from corvette_form_generator.inspection import section_step_resolution_source
from corvette_form_generator.interiors import build_model_interiors
from corvette_form_generator.mapping import (
    best_status,
    normalize_mode,
    selection_mode_label as shared_selection_mode_label,
    status_to_label,
    step_for_section as shared_step_for_section,
)
from corvette_form_generator.model_configs import base_model_config
from corvette_form_generator.output import write_json_output
from corvette_form_generator.rules import (
    entity_section,
    entity_type,
    exclusive_group_pairs,
    grouped_exclusion_pairs,
    grouped_requirement_pairs,
    load_exclusive_groups,
    load_rule_groups,
    runtime_authored_rule,
    section_selection_mode,
    truncate_reason,
)
from corvette_form_generator.registry_promotion import runtime_contract_artifact_path
from corvette_form_generator.runtime_contract import build_model_runtime_contract
from corvette_form_generator.runtime_metadata import (
    load_context_sections,
    load_default_selection_rules,
    load_model_config_overrides,
    load_order_summary_metadata,
    load_runtime_rule_exceptions,
    load_runtime_steps,
    load_section_presentation,
    load_variant_option_overrides,
    presentation_bool,
)
from corvette_form_generator.validation import validation_error_count
from corvette_form_generator.workbook import clean, intish, money, rows_from_sheet


MODEL_CONFIG = base_model_config("stingray")
ROOT = MODEL_CONFIG.root
WORKBOOK_PATH = MODEL_CONFIG.workbook_path
OUTPUT_DIR = MODEL_CONFIG.output_dir
APP_DIR = MODEL_CONFIG.app_dir
STEP_ORDER = list(MODEL_CONFIG.step_order)
STEP_LABELS = dict(MODEL_CONFIG.step_labels)
CONTEXT_SECTIONS = [dict(section) for section in MODEL_CONFIG.context_sections]
SECTION_STEP_OVERRIDES = dict(MODEL_CONFIG.section_step_overrides)
BODY_STYLE_DISPLAY_ORDER = dict(MODEL_CONFIG.body_style_display_order)
SELECTION_MODE_LABELS = dict(MODEL_CONFIG.selection_mode_labels)
STANDARD_SECTIONS = set(MODEL_CONFIG.standard_sections)


def step_for_section(
    section_id: str,
    section_name: str,
    section_step_key: str = "",
    *,
    standard_sections: set[str] | frozenset[str] | None = None,
) -> str:
    return shared_step_for_section(
        section_id,
        section_name,
        section_step_key=section_step_key,
        standard_sections=standard_sections or STANDARD_SECTIONS,
        section_step_overrides=SECTION_STEP_OVERRIDES,
    )


def selection_mode_label(selection_mode: str) -> str:
    return shared_selection_mode_label(selection_mode, SELECTION_MODE_LABELS)


def workbook_bool(row: dict[str, str], field: str, fallback: bool) -> bool:
    value = clean(row.get(field, ""))
    if value in {"True", "False"}:
        return value == "True"
    return fallback


def standard_equipment_key(choice: dict[str, Any]) -> tuple[str, str]:
    rpo = clean(choice.get("rpo", ""))
    return choice["variant_id"], rpo or choice["option_id"]


def standard_equipment_preference(choice: dict[str, Any], index: int) -> tuple[int, int]:
    option_id = clean(choice.get("option_id", ""))
    section_id = clean(choice.get("section_id", ""))
    is_canonical = option_id.endswith("_001")
    if is_canonical and section_id != "sec_stan_002":
        rank = 0
    elif section_id != "sec_stan_002":
        rank = 1
    else:
        rank = 2
    return rank, index


def standard_equipment_row(choice: dict[str, Any]) -> dict[str, Any]:
    return {
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
        "standard_equipment_group_type": choice.get("standard_equipment_group_type", ""),
        "display_order": choice["display_order"],
        "source_detail_raw": choice["source_detail_raw"],
    }


def build_standard_equipment(choices: list[dict[str, Any]]) -> list[dict[str, Any]]:
    selected: dict[tuple[str, str], tuple[int, dict[str, Any]]] = {}
    key_order: list[tuple[str, str]] = []
    for index, choice in enumerate(choices):
        if choice["status"] != "standard":
            continue
        key = standard_equipment_key(choice)
        if key not in selected:
            selected[key] = (index, choice)
            key_order.append(key)
            continue
        existing_index, existing_choice = selected[key]
        if standard_equipment_preference(choice, index) < standard_equipment_preference(existing_choice, existing_index):
            selected[key] = (index, choice)
    return [standard_equipment_row(selected[key][1]) for key in key_order]


def main() -> None:
    global MODEL_CONFIG

    wb = load_workbook(WORKBOOK_PATH)
    MODEL_CONFIG = load_model_config_overrides(wb, base_model_config("stingray"))

    variants_raw = rows_from_sheet(wb, "variant_master")
    sections = {row["section_id"]: row for row in rows_from_sheet(wb, "section_master")}
    options_raw = rows_from_sheet(wb, MODEL_CONFIG.source_option_sheet)
    statuses_raw = rows_from_sheet(wb, MODEL_CONFIG.status_sheet)
    context_copy_rows = context_choice_copy_rows(wb, MODEL_CONFIG.model_key)
    rules_raw = rows_from_sheet(wb, MODEL_CONFIG.rule_mapping_sheet)
    price_rules_raw = rows_from_sheet(wb, MODEL_CONFIG.price_rules_sheet)
    color_overrides_raw = rows_from_sheet(wb, MODEL_CONFIG.color_overrides_sheet)
    rule_groups = load_rule_groups(wb, MODEL_CONFIG)
    exclusive_groups = load_exclusive_groups(wb, MODEL_CONFIG)
    default_selection_rules = load_default_selection_rules(wb, MODEL_CONFIG.model_key)
    runtime_rule_exceptions = load_runtime_rule_exceptions(wb, MODEL_CONFIG.model_key)
    order_summary_metadata = load_order_summary_metadata(wb, MODEL_CONFIG.model_key)
    runtime_steps = load_runtime_steps(wb, MODEL_CONFIG.model_key, MODEL_CONFIG.step_order, MODEL_CONFIG.step_labels)
    context_sections = [
        {**row, "selection_mode_label": selection_mode_label(row.get("selection_mode", ""))}
        for row in load_context_sections(wb, MODEL_CONFIG.model_key, MODEL_CONFIG.context_sections)
    ]
    section_presentation_rows = load_section_presentation(wb, MODEL_CONFIG.model_key)
    section_presentation = {row["section_id"]: row for row in section_presentation_rows}
    standard_section_ids = {
        section_id
        for section_id, presentation in section_presentation.items()
        if presentation_bool(presentation, "standard_equipment_bucket", default=False)
    } or set(STANDARD_SECTIONS)
    variant_option_override_rows = load_variant_option_overrides(
        wb, MODEL_CONFIG.model_key, MODEL_CONFIG.variant_option_overrides_sheet
    )
    variant_option_overrides = {
        (row["option_id"], row["variant_id"]): row
        for row in variant_option_override_rows
    }
    option_assets = option_asset_map(wb, MODEL_CONFIG.model_key)
    grouped_requires = grouped_requirement_pairs(rule_groups)
    grouped_excludes = grouped_exclusion_pairs(rule_groups) | exclusive_group_pairs(exclusive_groups)

    display_behavior_by_option_id = {
        row["option_id"]: clean(row.get("display_behavior", "")).lower()
        for row in options_raw
        if clean(row.get("display_behavior", ""))
    }
    hidden_option_ids = {
        option_id
        for option_id, display_behavior in display_behavior_by_option_id.items()
        if display_behavior == "hidden"
    }
    for option in options_raw:
        option_display_behavior = display_behavior_by_option_id.get(option["option_id"], "")
        section_display_behavior = clean(
            section_presentation.get(option.get("section_id", ""), {}).get("display_behavior", "")
        ).lower()
        display_behavior = option_display_behavior or section_display_behavior
        option["_display_behavior"] = display_behavior
        if display_behavior == "hidden":
            option["active"] = "False"
            hidden_option_ids.add(option["option_id"])

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

    section_rows: list[dict[str, Any]] = [dict(row) for row in context_sections]
    for section_id, section in sections.items():
        presentation = section_presentation.get(section_id, {})
        section_name = clean(presentation.get("display_label")) or section.get("section_name", "")
        presentation_step_key = clean(presentation.get("step_key"))
        step_key = step_for_section(
            section_id,
            section_name,
            presentation_step_key or section.get("step_key", ""),
            standard_sections=standard_section_ids,
        )
        selection_mode = section.get("selection_mode", "")
        section_display_order = (
            intish(presentation.get("section_display_order"))
            if clean(presentation.get("section_display_order"))
            else intish(section.get("display_order"))
        )
        section_rows.append(
            {
                "section_id": section_id,
                "section_name": section_name,
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

    step_rows: list[dict[str, Any]] = [dict(row) for row in runtime_steps]
    section_ids_by_step: dict[str, list[str]] = defaultdict(list)
    for row in section_rows:
        section_ids_by_step[row["step_key"]].append(row["section_id"])
    for row in step_rows:
        row["section_ids"] = "|".join(sorted(section_ids_by_step.get(row["step_key"], [])))

    context_choices = build_body_context_choices(
        active_variants, context_copy_rows, MODEL_CONFIG.model_key, BODY_STYLE_DISPLAY_ORDER
    ) + build_trim_context_choices(active_variants, context_copy_rows, MODEL_CONFIG.model_key)

    options_by_id: dict[str, dict[str, Any]] = {}
    for option in options_raw:
        if option["option_id"] in options_by_id and option.get("active") != "True":
            continue
        section = sections.get(option.get("section_id", ""), {})
        presentation = section_presentation.get(option.get("section_id", ""), {})
        section_name = clean(presentation.get("display_label")) or section.get("section_name", "")
        presentation_step_key = clean(presentation.get("step_key"))
        step_key = step_for_section(
            option.get("section_id", ""),
            section_name,
            presentation_step_key or section.get("step_key", ""),
            standard_sections=standard_section_ids,
        )
        mode = section.get("selection_mode", "")
        options_by_id[option["option_id"]] = {
            "option_id": option["option_id"],
            "rpo": option.get("rpo", ""),
            "label": option.get("option_name", ""),
            "description": option.get("description", ""),
            "source_detail_raw": option.get("detail_raw", ""),
            "section_id": option.get("section_id", ""),
            "section_name": section_name,
            "standard_equipment_group_type": clean(presentation.get("standard_equipment_group_type")),
            "step_key": step_key,
            "selection_mode": mode,
            "selection_mode_label": selection_mode_label(mode),
            "choice_mode": normalize_mode(mode),
            "selectable": option.get("selectable", ""),
            "active": option.get("active", ""),
            "display_behavior": option.get("_display_behavior", ""),
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
            display_behavior = option.get("display_behavior", "")
            override = variant_option_overrides.get((option_id, variant["variant_id"]), {})
            if clean(override.get("status")):
                status = clean(override["status"]).lower()
            if clean(override.get("selectable")):
                selectable = clean(override["selectable"])
            if clean(override.get("active")):
                active = clean(override["active"])
            if clean(override.get("display_behavior")):
                display_behavior = clean(override["display_behavior"]).lower()
            if display_behavior == "auto_only":
                status = "unavailable"
                selectable = "False"
                active = "False"
            elif display_behavior == "display_only":
                status = "available"
                selectable = "False"
                active = "True"
            choice = {
                "choice_id": f"{variant['variant_id']}__{option_id}",
                "option_id": option_id,
                "rpo": option["rpo"],
                "label": option["label"],
                "description": option["description"],
                "section_id": option["section_id"],
                "section_name": option["section_name"],
                "standard_equipment_group_type": option.get("standard_equipment_group_type", ""),
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
            if display_behavior:
                choice["display_behavior"] = display_behavior
            if asset := option_assets.get(option_id):
                choice.update(asset)
            choices.append(choice)

    validation_rows: list[dict[str, Any]] = []
    source_interior_ids: set[str] = set()
    for row in rows_from_sheet(wb, MODEL_CONFIG.interior_source_sheet):
        interior_id = row.get("interior_id", "")
        if interior_id:
            source_interior_ids.add(interior_id)
        active_for_stingray = workbook_bool(row, "active_for_stingray", False)
        requires_r6x = workbook_bool(row, "requires_r6x", False)
        included_option_id = clean(row.get("included_option_id", ""))
        if active_for_stingray and requires_r6x and not included_option_id:
            validation_rows.append(
                {
                    "check_id": f"missing_r6x_included_option_{interior_id}",
                    "severity": "error",
                    "entity_type": "interior",
                    "entity_id": interior_id,
                    "message": "R6X interior requires included_option_id in lt_interiors.",
                }
            )

    interiors = build_model_interiors(MODEL_CONFIG)
    for row in interiors:
        # Keep the existing Stingray runtime contract byte-for-byte compatible
        # while sharing the workbook-owned interior builder with draft models.
        row.pop("requires_z25", None)

    interiors_by_id = {row["interior_id"]: row for row in interiors if row["interior_id"]}

    raw_rules: list[dict[str, Any]] = []
    for rule in rules_raw:
        rule_type = rule.get("rule_type", "").lower()
        source_id = rule.get("source_id", "")
        target_id = rule.get("target_id", "")
        if not runtime_authored_rule(rule):
            continue
        if rule_type == "requires" and (source_id, target_id) in grouped_requires:
            continue
        if source_id in hidden_option_ids or target_id in hidden_option_ids:
            continue
        source_section = entity_section(source_id, options_by_id, interiors_by_id)
        target_section = entity_section(target_id, options_by_id, interiors_by_id)
        source_mode = section_selection_mode(source_section, sections)
        target_mode = section_selection_mode(target_section, sections)
        body_style_scope = rule.get("body_style_scope", "")
        replaces_t0a = rule.get("runtime_action", "") == "replace"
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
        if rule.get("disabled_reason", ""):
            disabled_reason = rule.get("disabled_reason", "")
        elif replaces_t0a:
            disabled_reason = f"{source_label} removes this default."
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
                "target_type": entity_type(target_id, options_by_id, interiors_by_id),
                "source_type": entity_type(source_id, options_by_id, interiors_by_id),
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
            }
        )

    price_rules = [
        {
            "price_rule_id": row.get("price_rule_id", ""),
            "condition_option_id": row.get("condition_option_id", ""),
            "target_option_id": row.get("target_option_id", ""),
            "price_rule_type": row.get("price_rule_type", "").lower(),
            "price_value": money(row.get("price_value")),
            "body_style_scope": row.get("body_style_scope", ""),
            "trim_level_scope": row.get("trim_level_scope", ""),
            "variant_scope": row.get("variant_scope", ""),
            "notes": row.get("notes", ""),
        }
        for row in price_rules_raw
        if row.get("condition_option_id", "") not in hidden_option_ids and row.get("target_option_id", "") not in hidden_option_ids
    ]

    known_interior_ids = source_interior_ids
    color_overrides = [
        {
            "override_id": f"co_{idx:03d}",
            "interior_id": row.get("interior_id", ""),
            "option_id": row.get("option_id", ""),
            "rule_type": row.get("rule_type", "").lower(),
            "adds_rpo": row.get("adds_rpo", ""),
            "notes": "Exterior/interior pairing requires the listed override RPO.",
        }
        for idx, row in enumerate(
            (row for row in color_overrides_raw if row.get("interior_id", "") in known_interior_ids),
            start=1,
        )
    ]
    for row in interiors:
        row.pop("_included_option_id", None)

    # Heuristic step placement is a validation error on every pathway: the
    # workbook owns placement via section_presentation / section_master /
    # model config overrides, matching the draft path's contract preview check.
    sections_with_choices = {
        option["section_id"] for option in options_by_id.values() if option["active"] == "True" and option["section_id"]
    }
    for section_id in sorted(sections_with_choices):
        if section_step_resolution_source(section_id, sections, MODEL_CONFIG, section_presentation) == "heuristic":
            validation_rows.append(
                {
                    "check_id": f"heuristic_section_step_key_{section_id}",
                    "severity": "error",
                    "entity_type": "section",
                    "entity_id": section_id,
                    "message": f"Active {MODEL_CONFIG.model_label} choices fell back to heuristic step placement instead of workbook-owned placement.",
                }
            )

    # Validation floor
    if len(active_variants) != MODEL_CONFIG.expected_variant_count:
        validation_rows.append(
            {
                "check_id": "active_variant_count",
                "severity": "error",
                "entity_type": "variant",
                "entity_id": "",
                "message": f"Expected {MODEL_CONFIG.expected_variant_count} active {MODEL_CONFIG.model_label} variants; found {len(active_variants)}.",
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
                "message": f"Expected {expected_status_rows} canonical {MODEL_CONFIG.status_sheet} rows; found {canonical_status_rows}.",
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
    standard_equipment = build_standard_equipment(choices)
    validation_rows.extend(
        [
            {
                "check_id": "active_variants",
                "severity": "pass",
                "entity_type": "variant",
                "entity_id": "",
                "message": f"{len(active_variants)} active {MODEL_CONFIG.model_label} variants exported.",
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
        "ruleGroups": rule_groups,
        "exclusiveGroups": exclusive_groups,
        "rules": [row for row in raw_rules if row["active"] == "True"],
        "priceRules": price_rules,
        "defaultSelectionRules": default_selection_rules,
        "runtimeRuleExceptions": runtime_rule_exceptions,
        "orderSummary": order_summary_metadata,
        "interiors": [row for row in interiors if row["active_for_stingray"]],
        "colorOverrides": color_overrides,
        "validation": validation_rows,
    }
    wb.close()

    OUTPUT_DIR.mkdir(exist_ok=True)
    APP_DIR.mkdir(exist_ok=True)
    json_path = OUTPUT_DIR / "stingray-form-data.json"
    runtime_data = build_model_runtime_contract(MODEL_CONFIG, data)
    write_json_output(json_path, runtime_data)
    runtime_json_path = runtime_contract_artifact_path(ROOT, MODEL_CONFIG.model_key)
    runtime_json_path.parent.mkdir(parents=True, exist_ok=True)
    write_json_output(runtime_json_path, runtime_data)
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
                *ASSET_IMAGE_FIELDS,
            ],
        )
        writer.writeheader()
        for row in choices:
            writer.writerow({key: row.get(key, "") for key in writer.fieldnames})

    print(json.dumps({
        "workbook": str(WORKBOOK_PATH),
        "workbook_backup": None,
        "json": str(json_path),
        "runtime_contract_json": str(runtime_json_path),
        "csv": str(csv_path),
        "choices": len(choices),
        "context_choices": len(context_choices),
        "standard_equipment": len(standard_equipment),
        "rules": len(data["rules"]),
        "price_rules": len(price_rules),
        "interiors": len(data["interiors"]),
        "validation_errors": validation_error_count(validation_rows),
    }, indent=2))
