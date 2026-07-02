"""Shared rule-source loading, rule-pair derivation, and rule assembly."""

from __future__ import annotations

import re
from collections import defaultdict
from typing import Any

from corvette_form_generator.contract import label_for
from corvette_form_generator.model_config import ModelConfig
from corvette_form_generator.rule_derivation import derive_swap_rules, write_derivation_manifest
from corvette_form_generator.workbook import clean, intish, rows_from_optional_sheet


def active_source_row(row: dict[str, str]) -> bool:
    return clean(row.get("active", "True")) == "True"


def runtime_authored_rule(row: dict[str, str]) -> bool:
    return True


def entity_type(entity_id: str, option_rows: dict[str, dict[str, Any]], interiors_by_id: dict[str, dict[str, Any]]) -> str:
    if entity_id in interiors_by_id:
        return "interior"
    if entity_id in option_rows:
        return "option"
    return ""


def entity_section(entity_id: str, option_rows: dict[str, dict[str, Any]], interiors_by_id: dict[str, dict[str, Any]]) -> str:
    if entity_id in option_rows:
        return clean(option_rows[entity_id].get("section_id", ""))
    if entity_id in interiors_by_id:
        return clean(interiors_by_id[entity_id].get("section_id", ""))
    return ""


def section_selection_mode(section_id: str, sections_by_id: dict[str, dict[str, Any]]) -> str:
    return clean(sections_by_id.get(section_id, {}).get("selection_mode", ""))


def load_rule_groups(wb, config: ModelConfig) -> list[dict[str, Any]]:
    members_by_group: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows_from_optional_sheet(wb, config.rule_group_members_sheet):
        if active_source_row(row):
            members_by_group[row.get("group_id", "")].append(row)

    rule_groups: list[dict[str, Any]] = []
    for row in rows_from_optional_sheet(wb, config.rule_groups_sheet):
        if not active_source_row(row):
            continue
        group_id = row.get("group_id", "")
        members = sorted(members_by_group.get(group_id, []), key=lambda member: intish(member.get("display_order")))
        rule_groups.append(
            {
                "group_id": group_id,
                "group_type": row.get("group_type", ""),
                "source_id": row.get("source_id", ""),
                "target_ids": [member.get("target_id", "") for member in members if member.get("target_id", "")],
                "body_style_scope": row.get("body_style_scope", ""),
                "trim_level_scope": row.get("trim_level_scope", ""),
                "variant_scope": row.get("variant_scope", ""),
                "disabled_reason": row.get("disabled_reason", ""),
                "active": row.get("active", ""),
                "notes": row.get("notes", ""),
            }
        )
    return rule_groups


def load_exclusive_groups(wb, config: ModelConfig) -> list[dict[str, Any]]:
    members_by_group: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows_from_optional_sheet(wb, config.exclusive_group_members_sheet):
        if active_source_row(row):
            members_by_group[row.get("group_id", "")].append(row)

    exclusive_groups: list[dict[str, Any]] = []
    for row in rows_from_optional_sheet(wb, config.exclusive_groups_sheet):
        if not active_source_row(row):
            continue
        group_id = row.get("group_id", "")
        members = sorted(members_by_group.get(group_id, []), key=lambda member: intish(member.get("display_order")))
        exclusive_groups.append(
            {
                "group_id": group_id,
                "option_ids": [member.get("option_id", "") for member in members if member.get("option_id", "")],
                "selection_mode": row.get("selection_mode", ""),
                "active": row.get("active", ""),
                "notes": row.get("notes", ""),
            }
        )
    return exclusive_groups


def grouped_rule_pairs(rule_groups: list[dict[str, Any]], group_type: str) -> set[tuple[str, str]]:
    pairs: set[tuple[str, str]] = set()
    for group in rule_groups:
        if group.get("active") != "True" or group.get("group_type") != group_type:
            continue
        source_id = group.get("source_id", "")
        for target_id in group.get("target_ids", []):
            pairs.add((source_id, target_id))
    return pairs


def grouped_requirement_pairs(rule_groups: list[dict[str, Any]]) -> set[tuple[str, str]]:
    return grouped_rule_pairs(rule_groups, "requires_any")


def grouped_exclusion_pairs(rule_groups: list[dict[str, Any]]) -> set[tuple[str, str]]:
    return grouped_rule_pairs(rule_groups, "excludes_any")


def exclusive_group_pairs(exclusive_groups: list[dict[str, Any]]) -> set[tuple[str, str]]:
    pairs: set[tuple[str, str]] = set()
    for group in exclusive_groups:
        if group.get("active") != "True":
            continue
        option_ids = [option_id for option_id in group.get("option_ids", []) if option_id]
        for source_id in option_ids:
            for target_id in option_ids:
                if source_id != target_id:
                    pairs.add((source_id, target_id))
    return pairs


def truncate_reason(text: str, limit: int = 180) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "..."


def build_draft_rules(
    wb,
    config: ModelConfig,
    option_rows: dict[str, dict[str, Any]],
    sections_by_id: dict[str, dict[str, Any]],
    interiors: list[dict[str, Any]],
    grouped_requires: set[tuple[str, str]],
    grouped_excludes: set[tuple[str, str]],
) -> list[dict[str, Any]]:
    interiors_by_id = {row["interior_id"]: row for row in interiors if row.get("interior_id")}
    valid_ids = set(option_rows) | set(interiors_by_id)
    raw_rules: list[dict[str, Any]] = []
    for rule in rows_from_optional_sheet(wb, config.rule_mapping_sheet):
        rule_type = rule.get("rule_type", "").lower()
        source_id = rule.get("source_id", "")
        target_id = rule.get("target_id", "")
        if not rule_type or source_id not in valid_ids or target_id not in valid_ids:
            continue
        if not runtime_authored_rule(rule):
            continue
        if rule_type == "requires" and (source_id, target_id) in grouped_requires:
            continue
        source_section = entity_section(source_id, option_rows, interiors_by_id)
        target_section = entity_section(target_id, option_rows, interiors_by_id)
        source_mode = section_selection_mode(source_section, sections_by_id)
        target_mode = section_selection_mode(target_section, sections_by_id)
        replaces_default = rule.get("runtime_action", "") == "replace"
        redundant = (
            rule_type == "excludes"
            and source_section
            and source_section == target_section
            and source_mode.startswith("single")
            and target_mode.startswith("single")
            and not replaces_default
        )
        source_label = label_for(source_id, option_rows, interiors_by_id)
        target_label = label_for(target_id, option_rows, interiors_by_id)
        disabled_reason = rule.get("disabled_reason", "")
        auto_add = "False"
        if not disabled_reason and replaces_default:
            disabled_reason = f"{source_label} removes {target_label}."
        elif not disabled_reason and rule_type == "excludes":
            disabled_reason = f"Blocked by {source_label}."
        elif not disabled_reason and rule_type == "requires":
            disabled_reason = f"Requires {target_label}."
        elif not disabled_reason and rule_type == "includes":
            disabled_reason = f"Included with {source_label}."
            auto_add = "True"
        elif rule_type == "includes":
            auto_add = "True"
        raw_rules.append(
            {
                "rule_id": rule.get("rule_id", ""),
                "source_id": source_id,
                "rule_type": rule_type,
                "target_id": target_id,
                "target_type": entity_type(target_id, option_rows, interiors_by_id),
                "source_type": entity_type(source_id, option_rows, interiors_by_id),
                "source_section": source_section,
                "target_section": target_section,
                "source_selection_mode": source_mode,
                "target_selection_mode": target_mode,
                "body_style_scope": rule.get("body_style_scope", ""),
                "disabled_reason": disabled_reason,
                "auto_add": auto_add,
                "active": "False" if redundant else "True",
                "runtime_action": "replace" if replaces_default else "omit_redundant_same_section_exclude" if redundant else "active",
                "source_note": truncate_reason(rule.get("original_detail_raw", ""), 500),
            }
        )
    extend_with_derived_swap_rules(config, raw_rules, option_rows, interiors_by_id, sections_by_id)
    return raw_rules


def extend_with_derived_swap_rules(
    config: ModelConfig,
    raw_rules: list[dict[str, Any]],
    option_rows: dict[str, dict[str, Any]],
    interiors_by_id: dict[str, dict[str, Any]],
    sections_by_id: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """Append allowlist-approved derived swap rules and write the manifest.

    Shared by both rule-assembly routes (draft models via ``build_draft_rules``,
    Stingray via ``production.py``) so derivation behavior cannot diverge.
    Returns the derivation manifest.
    """

    def label(entity_id: str) -> str:
        return label_for(entity_id, option_rows, interiors_by_id)

    def meta(source_id: str, target_id: str) -> dict[str, Any]:
        source_section = entity_section(source_id, option_rows, interiors_by_id)
        target_section = entity_section(target_id, option_rows, interiors_by_id)
        return {
            "target_type": entity_type(target_id, option_rows, interiors_by_id),
            "source_type": entity_type(source_id, option_rows, interiors_by_id),
            "source_section": source_section,
            "target_section": target_section,
            "source_selection_mode": section_selection_mode(source_section, sections_by_id),
            "target_selection_mode": section_selection_mode(target_section, sections_by_id),
        }

    emitted, manifest = derive_swap_rules(
        config.model_key,
        raw_rules,
        label,
        meta,
    )
    raw_rules.extend(emitted)
    write_derivation_manifest(config.output_dir, config.model_key, manifest)
    return manifest
