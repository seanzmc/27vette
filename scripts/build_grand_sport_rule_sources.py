#!/usr/bin/env python3
"""Build workbook-backed Grand Sport rule source sheets."""

from __future__ import annotations

import json
import re
from collections import defaultdict
from datetime import datetime, timezone
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
SPECIAL_REVIEW_RPOS = ("EL9", "Z25", "FEY", "Z15")

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
    {
        "group_id": "gs_excl_ground_effects",
        "option_ids": ("opt_cfl_001", "opt_cfz_001", "opt_cfv_001"),
        "selection_mode": "single_within_group",
        "active": "True",
        "notes": "Grand Sport ground effects choices are mutually exclusive; inactive members stay in the source for reactivation without appearing in draft output.",
    },
)

INACTIVE_OPTION_RPOS = {"36S", "37S", "38S", "AUP", "R6P", "R9V", "R9W", "R9Y", "U2K"}
DISCLOSURE_ONLY_RPOS = {"EDU", "EFR"}
NO_RULE_RPOS = {"PIN"}
INTERIOR_DEFERRED_RPOS = {"36S", "37S", "38S", "AUP", "R6X"}
COLOR_OVERRIDE_RPOS = {"D30", "379", "3A9", "3F9", "3M9", "3N9"}
SEATBELT_RPOS = {"379", "3A9", "3F9", "3M9", "3N9"}

EXPLICIT_RULE_RPOS = {"BV4", "R88", "SFZ"}
EXCLUSIVE_GROUP_RULE_RPOS = {"RIK", "RIN", "SL8", "CFL", "CFV", "CFZ"}
KNOWN_DEFERRED_RPO_MENTIONS = {"CFV", "DTB", "DZU", "DZV", "DZX"}
REVIEW_SUPPRESSED_RPOS = (
    DISCLOSURE_ONLY_RPOS
    | NO_RULE_RPOS
    | INTERIOR_DEFERRED_RPOS
    | COLOR_OVERRIDE_RPOS
    | EXPLICIT_RULE_RPOS
    | EXCLUSIVE_GROUP_RULE_RPOS
)
FULL_LENGTH_STRIPE_RPOS = ("DPB", "DPC", "DPG", "DPL", "DPT", "DSY", "DSZ", "DT0", "DTB", "DTH", "DUB", "DUE", "DUK", "DUW")
GRAND_SPORT_CENTER_STRIPE_RPOS = ("DMU", "DMV", "DMW", "DMX", "DMY")

DESCRIPTION_UPDATES = {
    "EDU": "Front splitter is not body-color when CFV or CFZ ground effects is ordered. Tonneau grille is Carbon Flash-painted.",
    "EFR": "Includes tonneau grille. Rockers and splitters are not Carbon Flash when CFV visible carbon fiber ground effects is ordered.",
}


def active_source_row(row: dict[str, str]) -> bool:
    return clean(row.get("active", "True")).lower() == "true"


def ws_headers(ws) -> dict[str, int]:
    return {clean(ws.cell(1, col).value): col for col in range(1, ws.max_column + 1) if clean(ws.cell(1, col).value)}


def append_sentence(value: str, sentence: str) -> str:
    text = clean(value)
    if sentence in text:
        return text
    if not text:
        return sentence
    separator = "" if text.endswith((".", "!", "?")) else "."
    return f"{text}{separator} {sentence}"


def apply_grand_sport_review_decisions(wb) -> None:
    ws = wb[GRAND_SPORT_MODEL.source_option_sheet]
    headers = ws_headers(ws)
    for row_number in range(2, ws.max_row + 1):
        rpo = clean(ws.cell(row_number, headers["rpo"]).value).upper()
        if not rpo:
            continue
        if rpo in INACTIVE_OPTION_RPOS:
            ws.cell(row_number, headers["active"]).value = False
        if rpo == "D30":
            ws.cell(row_number, headers["selectable"]).value = False
            ws.cell(row_number, headers["active"]).value = True
            ws.cell(row_number, headers["display_behavior"]).value = "display_only"
        if rpo == "R6X":
            ws.cell(row_number, headers["active"]).value = True
            ws.cell(row_number, headers["display_behavior"]).value = "auto_only"
        if rpo in DESCRIPTION_UPDATES:
            cell = ws.cell(row_number, headers["description"])
            cell.value = append_sentence(clean(cell.value), DESCRIPTION_UPDATES[rpo])


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


def interior_combination_codes(wb) -> set[str]:
    codes: set[str] = set()
    for row in rows_from_sheet(wb, "lt_interiors"):
        for key in ("Interior Code", "Seat", "Stitch", "Suede", "Two Tone"):
            value = clean(row.get(key, "")).upper()
            if re.fullmatch(r"[A-Z0-9]{3}", value):
                codes.add(value)
        for token in clean(row.get("interior_id", "")).upper().split("_"):
            if re.fullmatch(r"[A-Z0-9]{3}", token):
                codes.add(token)
    return codes


def suppress_review_for(source_rpo: str, fragment: str) -> bool:
    if source_rpo in REVIEW_SUPPRESSED_RPOS:
        return True
    lower = fragment.lower()
    return "interior" in lower and source_rpo not in EXPLICIT_RULE_RPOS


def add_review_row(skipped: list[dict[str, Any]], source_id: str, source_rpo: str, reason: str, fragment: str) -> None:
    if suppress_review_for(source_rpo, fragment):
        return
    skipped.append(
        {
            "option_id": source_id,
            "rpo": source_rpo,
            "reason": reason,
            "fragment": fragment,
        }
    )


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
    audit_origin: str = "",
    audit_phrase: str = "",
    audit_fragment: str = "",
    audit_source_option_id: str = "",
    audit_source_rpo: str = "",
    audit_stingray_rule_id: str = "",
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
        "_audit_origin": audit_origin,
        "_audit_phrase": audit_phrase,
        "_audit_fragment": audit_fragment,
        "_audit_source_option_id": audit_source_option_id,
        "_audit_source_rpo": audit_source_rpo,
        "_audit_stingray_rule_id": audit_stingray_rule_id,
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
            audit_origin="copied_from_stingray",
            audit_stingray_rule_id=rule.get("rule_id", ""),
        )
        rows.append(copied)
    return rows


def explicit_review_rules(
    options_by_id: dict[str, dict[str, str]],
    option_ids_by_rpo: dict[str, list[str]],
    modes_by_section: dict[str, str],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []

    def add(source_rpo: str, target_rpos: tuple[str, ...], detail: str) -> None:
        for source_id in option_ids_by_rpo.get(source_rpo, []):
            for target_id in ids_for_codes(list(target_rpos), option_ids_by_rpo):
                rows.append(
                    make_rule(
                        source_id,
                        "excludes",
                        target_id,
                        detail,
                        options_by_id,
                        modes_by_section,
                        rule_id_prefix="gs_approved",
                        audit_origin="approved_user_decision",
                        audit_phrase="approved_excludes",
                        audit_fragment=detail,
                        audit_source_option_id=source_id,
                        audit_source_rpo=source_rpo,
                    )
                )

    add("BV4", ("R8C",), "BV4 personalized plaque is not available with R8C Museum Delivery.")
    stripe_targets = ("EYK",) + FULL_LENGTH_STRIPE_RPOS + GRAND_SPORT_CENTER_STRIPE_RPOS
    add("R88", stripe_targets, "R88 is not available with EYK or stripe options.")
    add("SFZ", stripe_targets, "SFZ is not available with EYK or stripe options.")
    return rows


def extracted_rules(
    options: list[dict[str, str]],
    options_by_id: dict[str, dict[str, str]],
    option_ids_by_rpo: dict[str, list[str]],
    modes_by_section: dict[str, str],
    ignored_mention_codes: set[str],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    rows: list[dict[str, Any]] = []
    skipped_requires_review: list[dict[str, Any]] = []
    unresolved_rpo_mentions: list[dict[str, Any]] = []
    for option in options:
        source_id = option.get("option_id", "")
        source_rpo = option.get("rpo", "")
        detail_raw = option.get("detail_raw", "")
        if not source_id or not detail_raw:
            continue
        for fragment in detail_fragments(detail_raw):
            lower = fragment.lower()
            for code in sorted(set(rpo_codes(fragment))):
                if code in ignored_mention_codes or source_rpo in REVIEW_SUPPRESSED_RPOS:
                    continue
                if code != source_rpo and not option_ids_by_rpo.get(code):
                    unresolved_rpo_mentions.append(
                        {
                            "option_id": source_id,
                            "rpo": source_rpo,
                            "mentioned_rpo": code,
                            "fragment": fragment,
                        }
                    )
            if "not recommended with" in lower:
                add_review_row(skipped_requires_review, source_id, source_rpo, "not_recommended_with", fragment)
                continue
            if "sold orders only" in lower or "sold order" in lower:
                add_review_row(skipped_requires_review, source_id, source_rpo, "sold_order_only_note", fragment)
            if "not available at this time" in lower:
                add_review_row(skipped_requires_review, source_id, source_rpo, "timing_availability_note", fragment)
            if "except" in lower:
                add_review_row(skipped_requires_review, source_id, source_rpo, "except_clause", fragment)
            if source_rpo in NO_RULE_RPOS | DISCLOSURE_ONLY_RPOS | INTERIOR_DEFERRED_RPOS | COLOR_OVERRIDE_RPOS:
                continue
            before_count = len(rows)
            if "not available with" in lower:
                codes = rpo_codes(phrase_tail(fragment, "not available with"))
                for target_id in ids_for_codes(codes, option_ids_by_rpo):
                    rows.append(
                        make_rule(
                            source_id,
                            "excludes",
                            target_id,
                            detail_raw,
                            options_by_id,
                            modes_by_section,
                            audit_origin="parsed_from_detail_raw",
                            audit_phrase="not_available_with",
                            audit_fragment=fragment,
                            audit_source_option_id=source_id,
                            audit_source_rpo=source_rpo,
                        )
                    )
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
                            audit_origin="parsed_from_detail_raw",
                            audit_phrase="requires",
                            audit_fragment=fragment,
                            audit_source_option_id=source_id,
                            audit_source_rpo=source_rpo,
                        )
                    )
            if "includes" in lower and "included with" not in lower:
                codes = rpo_codes(phrase_tail(fragment, "includes", (" requires",)))
                for target_id in ids_for_codes(codes, option_ids_by_rpo):
                    rows.append(
                        make_rule(
                            source_id,
                            "includes",
                            target_id,
                            detail_raw,
                            options_by_id,
                            modes_by_section,
                            audit_origin="parsed_from_detail_raw",
                            audit_phrase="includes",
                            audit_fragment=fragment,
                            audit_source_option_id=source_id,
                            audit_source_rpo=source_rpo,
                        )
                    )
            if "included and only available with" in lower:
                codes = rpo_codes(phrase_tail(fragment, "included and only available with"))
                for including_source_id in ids_for_codes(codes, option_ids_by_rpo):
                    rows.append(
                        make_rule(
                            including_source_id,
                            "includes",
                            source_id,
                            detail_raw,
                            options_by_id,
                            modes_by_section,
                            audit_origin="parsed_from_detail_raw",
                            audit_phrase="included_and_only_available_with",
                            audit_fragment=fragment,
                            audit_source_option_id=source_id,
                            audit_source_rpo=source_rpo,
                        )
                    )
            if "included with" in lower:
                codes = rpo_codes(phrase_tail(fragment, "included with"))
                for including_source_id in ids_for_codes(codes, option_ids_by_rpo):
                    rows.append(
                        make_rule(
                            including_source_id,
                            "includes",
                            source_id,
                            detail_raw,
                            options_by_id,
                            modes_by_section,
                            audit_origin="parsed_from_detail_raw",
                            audit_phrase="included_with",
                            audit_fragment=fragment,
                            audit_source_option_id=source_id,
                            audit_source_rpo=source_rpo,
                        )
                    )
            if "only available with" in lower and "included" not in lower:
                codes = rpo_codes(phrase_tail(fragment, "only available with"))
                for target_id in ids_for_codes(codes, option_ids_by_rpo):
                    rows.append(
                        make_rule(
                            source_id,
                            "requires",
                            target_id,
                            detail_raw,
                            options_by_id,
                            modes_by_section,
                            audit_origin="parsed_from_detail_raw",
                            audit_phrase="only_available_with",
                            audit_fragment=fragment,
                            audit_source_option_id=source_id,
                            audit_source_rpo=source_rpo,
                        )
                    )
            if len(rows) == before_count and any(
                phrase in lower
                for phrase in (
                    "not available with",
                    "requires",
                    "includes",
                    "included with",
                    "only available with",
                )
            ):
                add_review_row(skipped_requires_review, source_id, source_rpo, "supported_clause_without_resolved_rule", fragment)
    return rows, skipped_requires_review, unresolved_rpo_mentions


def rule_key(row: dict[str, Any]) -> tuple[str, str, str, str, str]:
    return (
        row["source_id"],
        row["rule_type"],
        row["target_id"],
        row.get("body_style_scope", ""),
        row.get("runtime_action", ""),
    )


def dedupe_rules_with_omissions(rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    deduped: dict[tuple[str, str, str, str, str], dict[str, Any]] = {}
    omitted: list[dict[str, Any]] = []
    for row in rows:
        if row["source_id"] == row["target_id"]:
            omitted.append({**row, "_audit_omit_reason": "self_reference"})
            continue
        key = rule_key(row)
        if key in deduped:
            omitted.append({**row, "_audit_omit_reason": "duplicate_rule_key"})
            continue
        deduped[key] = row
    return sorted(deduped.values(), key=lambda row: (row["source_id"], row["rule_type"], row["target_id"], row.get("body_style_scope", ""))), omitted


def dedupe_rules(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return dedupe_rules_with_omissions(rows)[0]


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
        active_option_ids = [option_id for option_id in option_ids if active_source_row(options_by_id[option_id])]
        if len(active_option_ids) < 2:
            continue
        groups.append({key: group[key] for key in EXCLUSIVE_GROUP_HEADERS})
        existing_member_sets.append(set(active_option_ids))
        for index, option_id in enumerate(option_ids, start=1):
            members.append(
                {
                    "group_id": group["group_id"],
                    "option_id": option_id,
                    "display_order": index * 10,
                    "active": "True" if active_source_row(options_by_id[option_id]) else "False",
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
            if member.get("option_id", "") in options_by_id and active_source_row(options_by_id[member.get("option_id", "")])
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


def exclusive_group_pairs(exclusive_groups: list[dict[str, Any]], exclusive_group_members: list[dict[str, Any]]) -> set[tuple[str, str]]:
    option_ids_by_group: dict[str, list[str]] = defaultdict(list)
    for member in exclusive_group_members:
        if active_source_row(member):
            option_ids_by_group[member.get("group_id", "")].append(member.get("option_id", ""))

    pairs: set[tuple[str, str]] = set()
    for group in exclusive_groups:
        if not active_source_row(group):
            continue
        option_ids = [option_id for option_id in option_ids_by_group.get(group.get("group_id", ""), []) if option_id]
        for source_id in option_ids:
            for target_id in option_ids:
                if source_id != target_id:
                    pairs.add((source_id, target_id))
    return pairs


def public_rule(row: dict[str, Any]) -> dict[str, Any]:
    return {header: row.get(header, "") for header in RULE_MAPPING_HEADERS}


def audit_rule(row: dict[str, Any]) -> dict[str, Any]:
    return {
        **public_rule(row),
        "origin": row.get("_audit_origin", ""),
        "matched_phrase": row.get("_audit_phrase", ""),
        "fragment": row.get("_audit_fragment", ""),
        "source_option_id": row.get("_audit_source_option_id", ""),
        "source_rpo": row.get("_audit_source_rpo", ""),
        "source_stingray_rule_id": row.get("_audit_stingray_rule_id", ""),
        "omit_reason": row.get("_audit_omit_reason", ""),
    }


def copied_rule_audit_rows(rules: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for rule in rules:
        if rule.get("_audit_origin") != "copied_from_stingray":
            continue
        rows.append(
            {
                "source_stingray_rule_id": rule.get("_audit_stingray_rule_id", ""),
                "grand_sport_rule_id": rule.get("rule_id", ""),
                "source_id": rule.get("source_id", ""),
                "rule_type": rule.get("rule_type", ""),
                "target_id": rule.get("target_id", ""),
                "body_style_scope": rule.get("body_style_scope", ""),
                "reason": "Both Stingray source and target ids resolve to active Grand Sport options.",
            }
        )
    return rows


def parsed_rule_audit_rows(rules: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for rule in rules:
        if rule.get("_audit_origin") != "parsed_from_detail_raw":
            continue
        rows.append(
            {
                "option_id": rule.get("_audit_source_option_id", ""),
                "rpo": rule.get("_audit_source_rpo", ""),
                "fragment": rule.get("_audit_fragment", ""),
                "matched_phrase": rule.get("_audit_phrase", ""),
                "rule_id": rule.get("rule_id", ""),
                "source_id": rule.get("source_id", ""),
                "rule_type": rule.get("rule_type", ""),
                "target_id": rule.get("target_id", ""),
                "body_style_scope": rule.get("body_style_scope", ""),
            }
        )
    return rows


def review_hot_spots(
    options: list[dict[str, str]],
    option_ids_by_rpo: dict[str, list[str]],
) -> dict[str, Any]:
    duplicate_rpos = []
    for rpo, option_ids in sorted(option_ids_by_rpo.items()):
        if len(option_ids) <= 1:
            continue
        duplicate_rpos.append(
            {
                "rpo": rpo,
                "option_ids": option_ids,
                "reason": "Duplicate active Grand Sport RPO; verify parsed rules point at the intended option variant.",
            }
        )

    special_mentions = []
    for option in options:
        text = " ".join(part for part in (option.get("detail_raw", ""), option.get("description", ""), option.get("option_name", "")) if part)
        mentioned = [rpo for rpo in SPECIAL_REVIEW_RPOS if re.search(rf"\b{re.escape(rpo)}\b", text)]
        if option.get("rpo", "") in SPECIAL_REVIEW_RPOS or mentioned:
            special_mentions.append(
                {
                    "option_id": option.get("option_id", ""),
                    "rpo": option.get("rpo", ""),
                    "mentioned_rpos": mentioned,
                    "detail_raw": option.get("detail_raw", ""),
                }
            )

    return {
        "duplicateRpos": duplicate_rpos,
        "specialPackageMentions": special_mentions,
    }


def render_audit_markdown(audit: dict[str, Any]) -> str:
    summary = audit["summary"]
    lines = [
        "# Grand Sport Rule Audit",
        "",
        f"Generated: `{audit['dataset']['generated_at']}`",
        f"Status: `{audit['dataset']['status']}`",
        "",
        "## Summary",
        "",
        f"- Copied Stingray candidates: {summary['copiedRuleCandidates']}",
        f"- Raw detail candidates: {summary['rawDetailRuleCandidates']}",
        f"- Final workbook rule rows: {summary['finalWorkbookRuleRows']}",
        f"- Expected draft runtime rules: {summary['expectedDraftRuntimeRules']}",
        f"- Omitted duplicate exclusive-group rules: {summary['omittedDuplicateExclusiveGroup']}",
        f"- Skipped/review rows: {summary['skippedRequiresReview']}",
        f"- Unresolved RPO mentions: {summary['unresolvedRpoMentions']}",
        "",
        "## Copied From Stingray",
        "",
    ]
    for row in audit["copiedFromStingray"][:25]:
        lines.append(f"- `{row['source_stingray_rule_id']}` -> `{row['grand_sport_rule_id']}`: {row['source_id']} {row['rule_type']} {row['target_id']}")
    if len(audit["copiedFromStingray"]) > 25:
        lines.append(f"- ... {len(audit['copiedFromStingray']) - 25} more")

    lines.extend(["", "## Parsed From Detail Raw", ""])
    for row in audit["parsedFromDetailRaw"][:35]:
        scope = f" [{row['body_style_scope']}]" if row.get("body_style_scope") else ""
        lines.append(f"- `{row['rpo']}` {row['source_id']} {row['rule_type']} {row['target_id']}{scope}: {row['matched_phrase']}")
    if len(audit["parsedFromDetailRaw"]) > 35:
        lines.append(f"- ... {len(audit['parsedFromDetailRaw']) - 35} more")

    lines.extend(["", "## Omitted Duplicate Exclusive Group Rules", ""])
    for row in audit["omittedDuplicateExclusiveGroup"][:35]:
        lines.append(f"- `{row['rule_id']}`: {row['source_id']} excludes {row['target_id']}")
    if not audit["omittedDuplicateExclusiveGroup"]:
        lines.append("- none")

    lines.extend(["", "## Skipped Requires Review", ""])
    for row in audit["skippedRequiresReview"][:50]:
        lines.append(f"- `{row['rpo']}` {row['option_id']} [{row['reason']}]: {row['fragment']}")
    if not audit["skippedRequiresReview"]:
        lines.append("- none")

    lines.extend(["", "## Unresolved RPO Mentions", ""])
    for row in audit["unresolvedRpoMentions"][:50]:
        lines.append(f"- `{row['rpo']}` {row['option_id']} mentions `{row['mentioned_rpo']}`: {row['fragment']}")
    if not audit["unresolvedRpoMentions"]:
        lines.append("- none")

    lines.extend(["", "## Review Hot Spots", ""])
    lines.append(f"- Duplicate active RPOs: {len(audit['reviewHotSpots']['duplicateRpos'])}")
    lines.append(f"- Special package mention rows: {len(audit['reviewHotSpots']['specialPackageMentions'])}")
    return "\n".join(lines) + "\n"


def write_rule_audit(
    config,
    options: list[dict[str, str]],
    option_ids_by_rpo: dict[str, list[str]],
    copied_rules: list[dict[str, Any]],
    raw_rules: list[dict[str, Any]],
    rules: list[dict[str, Any]],
    omitted_deduped: list[dict[str, Any]],
    skipped_requires_review: list[dict[str, Any]],
    unresolved_rpo_mentions: list[dict[str, Any]],
    exclusive_groups: list[dict[str, Any]],
    exclusive_group_members: list[dict[str, Any]],
) -> dict[str, str]:
    grouped_excludes = exclusive_group_pairs(exclusive_groups, exclusive_group_members)
    omitted_exclusive = [
        rule
        for rule in rules
        if rule.get("rule_type") == "excludes" and (rule.get("source_id", ""), rule.get("target_id", "")) in grouped_excludes
    ]
    audit = {
        "dataset": {
            "name": "2027 Corvette Grand Sport rule audit",
            "model": config.model_label,
            "model_year": config.model_year,
            "source_workbook": config.workbook_path.name,
            "source_option_sheet": config.source_option_sheet,
            "source_rule_sheet": config.rule_mapping_sheet,
            "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
            "status": "rule_audit_generated",
        },
        "summary": {
            "copiedRuleCandidates": len(copied_rules),
            "rawDetailRuleCandidates": len(raw_rules),
            "dedupedOrSelfReferenceCandidates": len(omitted_deduped),
            "finalWorkbookRuleRows": len(rules),
            "expectedDraftRuntimeRules": len(rules) - len(omitted_exclusive),
            "omittedDuplicateExclusiveGroup": len(omitted_exclusive),
            "skippedRequiresReview": len(skipped_requires_review),
            "unresolvedRpoMentions": len(unresolved_rpo_mentions),
            "exclusiveGroups": len(exclusive_groups),
            "exclusiveGroupMembers": len(exclusive_group_members),
        },
        "sourceSheets": {
            "optionSheet": config.source_option_sheet,
            "ruleSheet": config.rule_mapping_sheet,
            "ruleGroupsSheet": config.rule_groups_sheet,
            "ruleGroupMembersSheet": config.rule_group_members_sheet,
            "exclusiveGroupsSheet": config.exclusive_groups_sheet,
            "exclusiveMembersSheet": config.exclusive_group_members_sheet,
        },
        "copiedFromStingray": copied_rule_audit_rows(rules),
        "parsedFromDetailRaw": parsed_rule_audit_rows(rules),
        "omittedDeduped": [audit_rule(row) for row in omitted_deduped],
        "omittedDuplicateExclusiveGroup": [audit_rule(row) for row in omitted_exclusive],
        "skippedRequiresReview": skipped_requires_review,
        "unresolvedRpoMentions": unresolved_rpo_mentions,
        "reviewHotSpots": review_hot_spots(options, option_ids_by_rpo),
    }
    output_dir = config.output_dir / "inspection"
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "grand-sport-rule-audit.json"
    md_path = output_dir / "grand-sport-rule-audit.md"
    json_path.write_text(json.dumps(audit, indent=2), encoding="utf-8")
    md_path.write_text(render_audit_markdown(audit), encoding="utf-8")
    return {"json": str(json_path), "markdown": str(md_path)}


def main() -> None:
    config = GRAND_SPORT_MODEL
    wb = load_workbook(config.workbook_path)
    apply_grand_sport_review_decisions(wb)
    all_grand_sport_options = rows_from_sheet(wb, config.source_option_sheet)
    grand_sport_options = [row for row in all_grand_sport_options if active_source_row(row)]
    ignored_mention_codes = interior_combination_codes(wb) | KNOWN_DEFERRED_RPO_MENTIONS
    options_by_id, option_ids_by_rpo = option_indexes(grand_sport_options)
    all_options_by_id, _ = option_indexes(all_grand_sport_options)
    modes_by_section = section_modes(rows_from_sheet(wb, "section_master"))

    copied_rules = copy_stingray_rules(rows_from_sheet(wb, "rule_mapping"), options_by_id, modes_by_section)
    approved_rules = explicit_review_rules(options_by_id, option_ids_by_rpo, modes_by_section)
    raw_rules, skipped_requires_review, unresolved_rpo_mentions = extracted_rules(
        grand_sport_options,
        options_by_id,
        option_ids_by_rpo,
        modes_by_section,
        ignored_mention_codes,
    )
    rules, omitted_deduped = dedupe_rules_with_omissions(copied_rules + approved_rules + raw_rules)

    exclusive_groups, exclusive_group_members = build_exclusive_sources(
        rows_from_sheet(wb, "exclusive_groups"),
        rows_from_sheet(wb, "exclusive_group_members"),
        all_options_by_id,
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
    audit_paths = write_rule_audit(
        config,
        grand_sport_options,
        option_ids_by_rpo,
        copied_rules,
        raw_rules,
        rules,
        omitted_deduped,
        skipped_requires_review,
        unresolved_rpo_mentions,
        exclusive_groups,
        exclusive_group_members,
    )

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
                "skipped_requires_review": len(skipped_requires_review),
                "unresolved_rpo_mentions": len(unresolved_rpo_mentions),
                "rule_audit_artifacts": audit_paths,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
