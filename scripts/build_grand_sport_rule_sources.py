#!/usr/bin/env python3
"""Build workbook-backed Grand Sport rule source sheets."""

from __future__ import annotations

import json
import re
from collections import defaultdict
from typing import Any

from openpyxl import load_workbook

from corvette_form_generator.model_configs import GRAND_SPORT_MODEL
from corvette_form_generator.workbook import clean, intish, rows_from_sheet, write_sheet


RULE_MAPPING_HEADERS = [
    "rule_id",
    "source_id",
    "rule_type",
    "target_id",
    "target_type",
    "original_detail_raw",
    "review_flag",
    "source_type",
    "target_selection_mode",
    "source_selection_mode",
    "target_section",
    "source_section",
    "generation_action",
    "body_style_scope",
    "runtime_action",
    "disabled_reason",
]
RULE_GROUP_HEADERS = [
    "group_id",
    "group_type",
    "source_id",
    "body_style_scope",
    "trim_level_scope",
    "variant_scope",
    "disabled_reason",
    "active",
    "notes",
]
RULE_GROUP_MEMBER_HEADERS = ["group_id", "target_id", "display_order", "active"]
EXCLUSIVE_GROUP_HEADERS = ["group_id", "selection_mode", "active", "notes"]
EXCLUSIVE_GROUP_MEMBER_HEADERS = ["group_id", "option_id", "display_order", "active"]

APPROVED_EXCLUSIVE_GROUPS = (
    {
        "group_id": "gs_excl_ls6_engine_covers",
        "option_ids": (
            "opt_bc7_001",
            "opt_bc4_001",
            "opt_bc4_002",
            "opt_bcp_001",
            "opt_bcp_002",
            "opt_bcs_001",
            "opt_bcs_002",
        ),
        "selection_mode": "single_within_group",
        "active": "True",
        "notes": "Grand Sport LS6 engine cover choices are mutually exclusive; duplicate generated option rows are preserved for a later cleanup pass.",
    },
    {
        "group_id": "gs_excl_center_caps",
        "option_ids": ("opt_5zb_001", "opt_5zc_001", "opt_5zd_001"),
        "selection_mode": "single_within_group",
        "active": "True",
        "notes": "Grand Sport wheel center cap choices are mutually exclusive within the Wheel Accessory section.",
    },
    {
        "group_id": "gs_excl_indoor_car_covers",
        "option_ids": ("opt_rwh_001", "opt_wkr_001"),
        "selection_mode": "single_within_group",
        "active": "True",
        "notes": "Grand Sport indoor car cover choices are mutually exclusive within the LPO Exterior section.",
    },
    {
        "group_id": "gs_excl_rear_script_badges",
        "option_ids": ("opt_rik_001", "opt_rin_001", "opt_sl8_001"),
        "selection_mode": "single_within_group",
        "active": "True",
        "notes": "Rear Corvette script badge color choices are mutually exclusive within the LPO Exterior section.",
    },
    {
        "group_id": "gs_excl_suede_compartment_liners",
        "option_ids": ("opt_sxb_001", "opt_sxr_001", "opt_sxt_001"),
        "selection_mode": "single_within_group",
        "active": "True",
        "notes": "Grand Sport suede frunk/trunk compartment liner choices are mutually exclusive within the LPO Interior section.",
    },
)


def active_source_row(row: dict[str, str]) -> bool:
    return clean(row.get("active", "True")) == "True"


def option_indexes(rows: list[dict[str, str]]) -> tuple[dict[str, dict[str, str]], dict[str, list[str]]]:
    options_by_id = {row["option_id"]: row for row in rows if row.get("option_id")}
    option_ids_by_rpo: dict[str, list[str]] = defaultdict(list)
    for row in rows:
        option_id = row.get("option_id", "")
        rpo = row.get("rpo", "")
        if option_id and rpo:
            option_ids_by_rpo[rpo].append(option_id)
    return options_by_id, option_ids_by_rpo


def section_modes(rows: list[dict[str, str]]) -> dict[str, str]:
    return {row["section_id"]: row.get("selection_mode", "") for row in rows if row.get("section_id")}


def option_section(option_id: str, options_by_id: dict[str, dict[str, str]]) -> str:
    return options_by_id.get(option_id, {}).get("section_id", "")


def option_selection_mode(option_id: str, options_by_id: dict[str, dict[str, str]], modes_by_section: dict[str, str]) -> str:
    return modes_by_section.get(option_section(option_id, options_by_id), "")


def rpo_codes(text: str) -> list[str]:
    codes: list[str] = []
    for group in re.findall(r"\(([A-Z0-9][A-Z0-9/,\s-]*)\)", text):
        for code in re.split(r"[/,\s]+", group.replace("-", " ")):
            if re.fullmatch(r"[A-Z0-9]{3}", code):
                codes.append(code)
    return codes


def phrase_tail(text: str, phrase: str, stop_phrases: tuple[str, ...] = ()) -> str:
    match = re.search(re.escape(phrase), text, flags=re.IGNORECASE)
    if not match:
        return ""
    tail = text[match.end() :]
    lower_tail = tail.lower()
    stop_indexes = [
        lower_tail.find(stop_phrase.lower())
        for stop_phrase in stop_phrases
        if lower_tail.find(stop_phrase.lower()) >= 0
    ]
    if stop_indexes:
        tail = tail[: min(stop_indexes)]
    return tail


def detail_fragments(detail_raw: str) -> list[str]:
    fragments = []
    for line in re.split(r"(?:^|\n)\s*\d+\.\s*", detail_raw):
        text = re.sub(r"\s+", " ", line).strip()
        if text:
            fragments.append(text)
    return fragments or ([re.sub(r"\s+", " ", detail_raw).strip()] if detail_raw.strip() else [])


def scoped_body_style(text: str) -> str:
    has_coupe = re.search(r"\bcoupe\b", text, flags=re.IGNORECASE)
    has_convertible = re.search(r"\bconvertible\b", text, flags=re.IGNORECASE)
    if has_coupe and not has_convertible:
        return "coupe"
    if has_convertible and not has_coupe:
        return "convertible"
    return ""


def ids_for_codes(codes: list[str], option_ids_by_rpo: dict[str, list[str]]) -> list[str]:
    option_ids: list[str] = []
    for code in codes:
        option_ids.extend(option_ids_by_rpo.get(code, []))
    return option_ids


def make_rule(
    source_id: str,
    rule_type: str,
    target_id: str,
    detail_raw: str,
    options_by_id: dict[str, dict[str, str]],
    modes_by_section: dict[str, str],
    body_style_scope: str = "",
    runtime_action: str = "",
    generation_action: str = "",
    disabled_reason: str = "",
    rule_id_prefix: str = "gs_rule",
) -> dict[str, Any]:
    rule_slug = "_".join(part for part in (source_id, rule_type, target_id, body_style_scope, runtime_action) if part)
    return {
        "rule_id": f"{rule_id_prefix}_{rule_slug}",
        "source_id": source_id,
        "rule_type": rule_type,
        "target_id": target_id,
        "target_type": "option",
        "original_detail_raw": detail_raw,
        "review_flag": "False",
        "source_type": "option",
        "target_selection_mode": option_selection_mode(target_id, options_by_id, modes_by_section),
        "source_selection_mode": option_selection_mode(source_id, options_by_id, modes_by_section),
        "target_section": option_section(target_id, options_by_id),
        "source_section": option_section(source_id, options_by_id),
        "generation_action": generation_action,
        "body_style_scope": body_style_scope,
        "runtime_action": runtime_action,
        "disabled_reason": disabled_reason,
    }


def copy_stingray_rules(
    stingray_rules: list[dict[str, str]],
    options_by_id: dict[str, dict[str, str]],
    modes_by_section: dict[str, str],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for rule in stingray_rules:
        source_id = rule.get("source_id", "")
        target_id = rule.get("target_id", "")
        rule_type = rule.get("rule_type", "").lower()
        if source_id not in options_by_id or target_id not in options_by_id or not rule_type:
            continue
        copied = make_rule(
            source_id,
            rule_type,
            target_id,
            rule.get("original_detail_raw", ""),
            options_by_id,
            modes_by_section,
            body_style_scope=rule.get("body_style_scope", ""),
            runtime_action=rule.get("runtime_action", ""),
            generation_action=rule.get("generation_action", ""),
            disabled_reason=rule.get("disabled_reason", ""),
            rule_id_prefix=f"gs_copy_{rule.get('rule_id', 'rule')}",
        )
        rows.append(copied)
    return rows


def extracted_rules(
    options: list[dict[str, str]],
    options_by_id: dict[str, dict[str, str]],
    option_ids_by_rpo: dict[str, list[str]],
    modes_by_section: dict[str, str],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for option in options:
        source_id = option.get("option_id", "")
        detail_raw = option.get("detail_raw", "")
        if not source_id or not detail_raw:
            continue
        for fragment in detail_fragments(detail_raw):
            lower = fragment.lower()
            if "not recommended with" in lower:
                continue
            if "not available with" in lower:
                codes = rpo_codes(phrase_tail(fragment, "not available with"))
                for target_id in ids_for_codes(codes, option_ids_by_rpo):
                    rows.append(make_rule(source_id, "excludes", target_id, detail_raw, options_by_id, modes_by_section))
            if "requires" in lower:
                codes = rpo_codes(phrase_tail(fragment, "requires", (" or included with", " included with")))
                for target_id in ids_for_codes(codes, option_ids_by_rpo):
                    rows.append(
                        make_rule(
                            source_id,
                            "requires",
                            target_id,
                            detail_raw,
                            options_by_id,
                            modes_by_section,
                            body_style_scope=scoped_body_style(fragment),
                        )
                    )
            if "includes" in lower and "included with" not in lower:
                codes = rpo_codes(phrase_tail(fragment, "includes", (" requires",)))
                for target_id in ids_for_codes(codes, option_ids_by_rpo):
                    rows.append(make_rule(source_id, "includes", target_id, detail_raw, options_by_id, modes_by_section))
            if "included and only available with" in lower:
                codes = rpo_codes(phrase_tail(fragment, "included and only available with"))
                for including_source_id in ids_for_codes(codes, option_ids_by_rpo):
                    rows.append(make_rule(including_source_id, "includes", source_id, detail_raw, options_by_id, modes_by_section))
            if "included with" in lower:
                codes = rpo_codes(phrase_tail(fragment, "included with"))
                for including_source_id in ids_for_codes(codes, option_ids_by_rpo):
                    rows.append(make_rule(including_source_id, "includes", source_id, detail_raw, options_by_id, modes_by_section))
            if "only available with" in lower and "included" not in lower:
                codes = rpo_codes(phrase_tail(fragment, "only available with"))
                for target_id in ids_for_codes(codes, option_ids_by_rpo):
                    rows.append(make_rule(source_id, "requires", target_id, detail_raw, options_by_id, modes_by_section))
    return rows


def dedupe_rules(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    deduped: dict[tuple[str, str, str, str, str], dict[str, Any]] = {}
    for row in rows:
        if row["source_id"] == row["target_id"]:
            continue
        key = (
            row["source_id"],
            row["rule_type"],
            row["target_id"],
            row.get("body_style_scope", ""),
            row.get("runtime_action", ""),
        )
        deduped.setdefault(key, row)
    return sorted(deduped.values(), key=lambda row: (row["source_id"], row["rule_type"], row["target_id"], row.get("body_style_scope", "")))


def build_exclusive_sources(
    stingray_groups: list[dict[str, str]],
    stingray_members: list[dict[str, str]],
    options_by_id: dict[str, dict[str, str]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    groups: list[dict[str, Any]] = []
    members: list[dict[str, Any]] = []
    existing_member_sets: list[set[str]] = []

    for group in APPROVED_EXCLUSIVE_GROUPS:
        option_ids = [option_id for option_id in group["option_ids"] if option_id in options_by_id]
        if not option_ids:
            continue
        groups.append({key: group[key] for key in EXCLUSIVE_GROUP_HEADERS})
        existing_member_sets.append(set(option_ids))
        for index, option_id in enumerate(option_ids, start=1):
            members.append(
                {
                    "group_id": group["group_id"],
                    "option_id": option_id,
                    "display_order": index * 10,
                    "active": "True",
                }
            )

    members_by_group: dict[str, list[dict[str, str]]] = defaultdict(list)
    for member in stingray_members:
        if active_source_row(member):
            members_by_group[member.get("group_id", "")].append(member)

    for group in stingray_groups:
        if not active_source_row(group):
            continue
        option_ids = [
            member.get("option_id", "")
            for member in sorted(members_by_group[group.get("group_id", "")], key=lambda row: intish(row.get("display_order")))
            if member.get("option_id", "") in options_by_id
        ]
        if not option_ids or len(option_ids) != len(members_by_group[group.get("group_id", "")]):
            continue
        member_set = set(option_ids)
        if any(member_set <= existing for existing in existing_member_sets):
            continue
        group_id = f"gs_copy_{group['group_id']}"
        groups.append(
            {
                "group_id": group_id,
                "selection_mode": group.get("selection_mode", ""),
                "active": "True",
                "notes": f"Copied from Stingray group {group['group_id']} because all member option IDs exist for Grand Sport.",
            }
        )
        existing_member_sets.append(member_set)
        for index, option_id in enumerate(option_ids, start=1):
            members.append({"group_id": group_id, "option_id": option_id, "display_order": index * 10, "active": "True"})

    return groups, members


def main() -> None:
    config = GRAND_SPORT_MODEL
    wb = load_workbook(config.workbook_path)
    grand_sport_options = [row for row in rows_from_sheet(wb, config.source_option_sheet) if active_source_row(row)]
    options_by_id, option_ids_by_rpo = option_indexes(grand_sport_options)
    modes_by_section = section_modes(rows_from_sheet(wb, "section_master"))

    copied_rules = copy_stingray_rules(rows_from_sheet(wb, "rule_mapping"), options_by_id, modes_by_section)
    raw_rules = extracted_rules(grand_sport_options, options_by_id, option_ids_by_rpo, modes_by_section)
    rules = dedupe_rules(copied_rules + raw_rules)

    exclusive_groups, exclusive_group_members = build_exclusive_sources(
        rows_from_sheet(wb, "exclusive_groups"),
        rows_from_sheet(wb, "exclusive_group_members"),
        options_by_id,
    )

    for legacy_sheet in ("grandSport_exclusive_group_members",):
        if legacy_sheet in wb.sheetnames and legacy_sheet != config.exclusive_group_members_sheet:
            del wb[legacy_sheet]

    write_sheet(wb, config.rule_mapping_sheet, RULE_MAPPING_HEADERS, rules)
    write_sheet(wb, config.rule_groups_sheet, RULE_GROUP_HEADERS, [])
    write_sheet(wb, config.rule_group_members_sheet, RULE_GROUP_MEMBER_HEADERS, [])
    write_sheet(wb, config.exclusive_groups_sheet, EXCLUSIVE_GROUP_HEADERS, exclusive_groups)
    write_sheet(wb, config.exclusive_group_members_sheet, EXCLUSIVE_GROUP_MEMBER_HEADERS, exclusive_group_members)
    wb.save(config.workbook_path)

    print(
        json.dumps(
            {
                "rule_mapping_rows": len(rules),
                "copied_rule_candidates": len(copied_rules),
                "raw_detail_rule_candidates": len(raw_rules),
                "exclusive_groups": len(exclusive_groups),
                "exclusive_group_members": len(exclusive_group_members),
                "rule_groups": 0,
                "rule_group_members": 0,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
