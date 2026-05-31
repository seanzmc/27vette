"""Read-only Z06/ZR1/ZR1X rule readiness audit helpers."""

from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timezone
from typing import Any, Iterable

try:
    from corvette_form_generator.workbook import clean, rows_from_sheet
except ModuleNotFoundError:  # pragma: no cover - supports pytest imports via scripts.*
    from scripts.corvette_form_generator.workbook import clean, rows_from_sheet

Z_MODEL_KEYS = ("z06", "zr1", "zr1x")
_TRUE_VALUES = {"true", "1", "yes", "y", "active"}
_FALSE_VALUES = {"false", "0", "no", "n", "inactive"}
_VALID_OVS_STATUSES = {"available", "standard", "unavailable"}
_HOT_SPOT_RPOS = {
    "engineAppearance": {"B6P", "ZZ3", "BC4", "BCP", "BCS", "D3V", "SL9"},
    "exhaust": {"WUB", "NWI", "NGA"},
    "suspension": {"FE1", "FE2", "FE3", "FE4", "FE5", "FE6", "FE7", "FE8", "FE9"},
    "brakes": {"J6D", "J57", "J58", "J59", "J60"},
    "performancePackages": {"Z07", "ZTK", "Z52", "PDB", "PCQ"},
    "wheels": {"Q9I", "Q9A", "Q9B", "Q9C", "Q9D", "ROY", "ROZ", "R88", "5DF", "5DG", "5DH"},
    "groundEffectsAero": {"5V5", "T0F", "T0G", "VWE", "CFV", "CFZ"},
    "stripesExteriorAccents": {"DPB", "DPC", "DPG", "DPL", "DPT", "DSY", "DSZ", "DT0", "DTB", "DTH", "DUB", "DUE", "DUK", "DUW", "EYK", "EFR", "EDU", "SFZ"},
}


def active_bool(value: Any, *, default: bool = True) -> bool:
    text = clean(value).casefold()
    if not text:
        return default
    if text in _TRUE_VALUES:
        return True
    if text in _FALSE_VALUES:
        return False
    return default


def optional_rows(wb: Any, sheet_name: str) -> list[dict[str, str]]:
    if sheet_name not in wb.sheetnames:
        return []
    return rows_from_sheet(wb, sheet_name)


def active_rows(rows: Iterable[dict[str, str]]) -> list[dict[str, str]]:
    return [row for row in rows if active_bool(row.get("active"))]


def _model_variant_ids(wb: Any, model_key: str) -> list[str]:
    variants = []
    for row in optional_rows(wb, "variant_master"):
        if clean(row.get("model_key")) == model_key and active_bool(row.get("active")):
            variant_id = clean(row.get("variant_id"))
            if variant_id:
                variants.append(variant_id)
    return variants


def _option_indexes(option_rows: list[dict[str, str]]) -> dict[str, Any]:
    by_id = {clean(row.get("option_id")): row for row in option_rows if clean(row.get("option_id"))}
    active_by_id = {clean(row.get("option_id")): row for row in option_rows if clean(row.get("option_id")) and active_bool(row.get("active"))}
    rpo_by_id = {option_id: clean(row.get("rpo")) for option_id, row in by_id.items()}
    return {"by_id": by_id, "active_by_id": active_by_id, "rpo_by_id": rpo_by_id}


def _rule_semantic_key(row: dict[str, str]) -> tuple[str, str, str, str, str]:
    return (
        clean(row.get("source_id")),
        clean(row.get("rule_type")).casefold(),
        clean(row.get("target_id")),
        clean(row.get("body_style_scope")) or "*",
        clean(row.get("runtime_action")),
    )


def _exclusive_pairs(groups: list[dict[str, str]], members: list[dict[str, str]]) -> set[tuple[str, str]]:
    active_group_ids = {clean(row.get("group_id")) for row in groups if active_bool(row.get("active"))}
    members_by_group: dict[str, list[str]] = defaultdict(list)
    for member in members:
        group_id = clean(member.get("group_id"))
        option_id = clean(member.get("option_id"))
        if group_id in active_group_ids and option_id and active_bool(member.get("active")):
            members_by_group[group_id].append(option_id)
    pairs: set[tuple[str, str]] = set()
    for option_ids in members_by_group.values():
        for source_id in option_ids:
            for target_id in option_ids:
                if source_id != target_id:
                    pairs.add((source_id, target_id))
    return pairs


def _rule_group_pairs(groups: list[dict[str, str]], members: list[dict[str, str]], group_type: str) -> set[tuple[str, str]]:
    source_by_group = {
        clean(row.get("group_id")): clean(row.get("source_id"))
        for row in groups
        if active_bool(row.get("active")) and clean(row.get("group_type")).casefold() == group_type
    }
    pairs: set[tuple[str, str]] = set()
    for member in members:
        group_id = clean(member.get("group_id"))
        source_id = source_by_group.get(group_id)
        target_id = clean(member.get("target_id"))
        if source_id and target_id and active_bool(member.get("active")):
            pairs.add((source_id, target_id))
    return pairs


def _option_reference_issues(rules: list[dict[str, str]], options_by_id: dict[str, dict[str, str]], active_options_by_id: dict[str, dict[str, str]]) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    missing: list[dict[str, str]] = []
    inactive: list[dict[str, str]] = []
    for row in rules:
        refs = [("source_id", clean(row.get("source_id")))]
        if clean(row.get("target_type")) in ("", "option"):
            refs.append(("target_id", clean(row.get("target_id"))))
        for field, option_id in refs:
            if not option_id:
                continue
            issue = {"rule_id": clean(row.get("rule_id")), "field": field, "option_id": option_id}
            if option_id not in options_by_id:
                missing.append(issue)
            elif option_id not in active_options_by_id:
                inactive.append(issue)
    return missing, inactive


def _member_reference_issues(members: list[dict[str, str]], option_field: str, active_options_by_id: dict[str, dict[str, str]]) -> list[dict[str, str]]:
    issues = []
    for row in members:
        option_id = clean(row.get(option_field))
        if option_id and active_bool(row.get("active")) and option_id not in active_options_by_id:
            issues.append({"group_id": clean(row.get("group_id")), "field": option_field, "option_id": option_id})
    return issues


def _variant_status_audit(options: list[dict[str, str]], ovs_rows: list[dict[str, str]], variant_ids: list[str]) -> dict[str, Any]:
    active_option_ids = {clean(row.get("option_id")) for row in options if active_bool(row.get("active")) and clean(row.get("option_id"))}
    status_by_option: dict[str, set[str]] = defaultdict(set)
    invalid_rows = []
    dangling_rows = []
    for row in ovs_rows:
        option_id = clean(row.get("option_id"))
        variant_id = clean(row.get("variant_id"))
        status = clean(row.get("status")).casefold()
        if option_id not in active_option_ids:
            dangling_rows.append({"option_id": option_id, "variant_id": variant_id, "status": status})
        if status and status not in _VALID_OVS_STATUSES:
            invalid_rows.append({"option_id": option_id, "variant_id": variant_id, "status": status})
        if option_id and variant_id:
            status_by_option[option_id].add(variant_id)
    required = set(variant_ids)
    missing = []
    for option_id in sorted(active_option_ids):
        missing_variants = sorted(required - status_by_option.get(option_id, set()))
        if missing_variants:
            missing.append({"option_id": option_id, "missing_variant_ids": missing_variants})
    return {
        "optionsMissingVariantStatuses": missing,
        "danglingOvsRows": dangling_rows,
        "invalidOvsStatuses": invalid_rows,
    }


def _default_rule_issues(default_rows: list[dict[str, str]], active_options_by_id: dict[str, dict[str, str]]) -> list[dict[str, str]]:
    issues = []
    for row in default_rows:
        if not active_bool(row.get("active")):
            continue
        option_id = clean(row.get("target_option_id"))
        if option_id and option_id not in active_options_by_id:
            issues.append({"rule_id": clean(row.get("rule_id")), "target_option_id": option_id})
    return issues


def _hot_spots(options: list[dict[str, str]], rules: list[dict[str, str]], exclusive_groups: list[dict[str, str]], defaults: list[dict[str, str]]) -> dict[str, Any]:
    rpo_by_id = {clean(row.get("option_id")): clean(row.get("rpo")) for row in options if clean(row.get("option_id"))}
    result: dict[str, Any] = {}
    for name, rpos in _HOT_SPOT_RPOS.items():
        option_ids = sorted(option_id for option_id, rpo in rpo_by_id.items() if rpo in rpos)
        rule_rows = [
            clean(row.get("rule_id"))
            for row in rules
            if rpo_by_id.get(clean(row.get("source_id"))) in rpos or rpo_by_id.get(clean(row.get("target_id"))) in rpos
        ]
        result[name] = {"optionIds": option_ids, "ruleIds": rule_rows, "optionCount": len(option_ids), "ruleCount": len(rule_rows)}
    result["defaults"] = {
        "defaultSelectionRules": sum(1 for row in defaults if active_bool(row.get("active"))),
        "defaultSelectedOptions": sorted(clean(row.get("option_id")) for row in options if clean(row.get("display_behavior")) == "default_selected"),
    }
    result["requiredExclusiveGroups"] = sorted(
        clean(row.get("group_id"))
        for row in exclusive_groups
        if active_bool(row.get("active")) and clean(row.get("selection_mode")) == "required_single_within_group"
    )
    return result


def _audit_model(wb: Any, model_key: str) -> dict[str, Any]:
    options = optional_rows(wb, f"{model_key}_options")
    rules = optional_rows(wb, f"{model_key}_rule_mapping")
    ovs_rows = optional_rows(wb, f"{model_key}_ovs")
    rule_groups = optional_rows(wb, f"{model_key}_rule_groups")
    rule_group_members = optional_rows(wb, f"{model_key}_rule_group_members")
    exclusive_groups = optional_rows(wb, f"{model_key}_exclusive_groups")
    exclusive_members = optional_rows(wb, f"{model_key}_exclusive_members")
    defaults = [row for row in optional_rows(wb, "default_selection_rules") if clean(row.get("model_key")) == model_key]
    indexes = _option_indexes(options)
    active_rule_groups = active_rows(rule_groups)
    active_rule_group_members = active_rows(rule_group_members)
    active_exclusive_groups = active_rows(exclusive_groups)
    active_exclusive_members = active_rows(exclusive_members)

    missing_refs, inactive_refs = _option_reference_issues(rules, indexes["by_id"], indexes["active_by_id"])
    missing_rule_group_members = _member_reference_issues(rule_group_members, "target_id", indexes["active_by_id"])
    missing_exclusive_members = _member_reference_issues(exclusive_members, "option_id", indexes["active_by_id"])
    missing_defaults = _default_rule_issues(defaults, indexes["active_by_id"])
    duplicate_keys = [key for key, count in Counter(_rule_semantic_key(row) for row in rules).items() if count > 1]
    exclusive_pairs = _exclusive_pairs(exclusive_groups, exclusive_members)
    rule_group_excludes = _rule_group_pairs(rule_groups, rule_group_members, "excludes_any")
    rule_group_requires = _rule_group_pairs(rule_groups, rule_group_members, "requires_any")
    direct_excludes_covered = [
        clean(row.get("rule_id"))
        for row in rules
        if clean(row.get("rule_type")).casefold() == "excludes"
        and (clean(row.get("source_id")), clean(row.get("target_id"))) in (exclusive_pairs | rule_group_excludes)
    ]
    variant_audit = _variant_status_audit(options, ovs_rows, _model_variant_ids(wb, model_key))
    grand_sport_hits = [
        {"sheet": f"{model_key}_rule_mapping", "id": clean(row.get("rule_id"))}
        for row in rules
        if "grand sport" in " | ".join(row.values()).casefold()
    ] + [
        {"sheet": f"{model_key}_exclusive_groups", "id": clean(row.get("group_id"))}
        for row in exclusive_groups
        if "grand sport" in " | ".join(row.values()).casefold()
    ]

    focused_counts = {
        "duplicateSemanticRules": len(duplicate_keys),
        "directExcludesCoveredByExclusiveGroups": len(direct_excludes_covered),
        "missingOptionReferences": len(missing_refs),
        "inactiveOptionReferences": len(inactive_refs),
        "missingRuleGroupMemberReferences": len(missing_rule_group_members),
        "missingExclusiveMemberReferences": len(missing_exclusive_members),
        "missingDefaultRuleTargets": len(missing_defaults),
        "optionsMissingVariantStatuses": len(variant_audit["optionsMissingVariantStatuses"]),
        "danglingOvsRows": len(variant_audit["danglingOvsRows"]),
        "invalidOvsStatuses": len(variant_audit["invalidOvsStatuses"]),
        "grandSportTextHits": len(grand_sport_hits),
    }
    return {
        "modelKey": model_key,
        "summary": {
            "activeOptions": len(indexes["active_by_id"]),
            "optionRows": len(options),
            "ovsRows": len(ovs_rows),
            "ruleMappingRows": len(rules),
            "exclusiveGroups": len(active_exclusive_groups),
            "exclusiveMembers": len(active_exclusive_members),
            "ruleGroups": len(active_rule_groups),
            "ruleGroupMembers": len(active_rule_group_members),
            "defaultSelectionRules": sum(1 for row in defaults if active_bool(row.get("active"))),
        },
        "ruleTypeCounts": dict(sorted(Counter(clean(row.get("rule_type")) for row in rules if clean(row.get("rule_type"))).items())),
        "focusedReviewCounts": focused_counts,
        "focusedReview": {
            "duplicateSemanticRules": [list(key) for key in duplicate_keys],
            "directExcludesCoveredByExclusiveGroups": direct_excludes_covered,
            "missingOptionReferences": missing_refs,
            "inactiveOptionReferences": inactive_refs,
            "missingRuleGroupMemberReferences": missing_rule_group_members,
            "missingExclusiveMemberReferences": missing_exclusive_members,
            "missingDefaultRuleTargets": missing_defaults,
            **variant_audit,
            "grandSportTextHits": grand_sport_hits,
        },
        "groups": {
            "exclusive": [
                {"group_id": clean(row.get("group_id")), "selection_mode": clean(row.get("selection_mode")), "active": active_bool(row.get("active"))}
                for row in exclusive_groups
            ],
            "ruleGroups": [
                {"group_id": clean(row.get("group_id")), "group_type": clean(row.get("group_type")), "source_id": clean(row.get("source_id")), "active": active_bool(row.get("active"))}
                for row in rule_groups
            ],
        },
        "hotSpots": _hot_spots(options, rules, exclusive_groups, defaults),
    }


def build_z_rule_audit(wb: Any, model_keys: Iterable[str] | None = None, *, generated_at: str | None = None) -> dict[str, Any]:
    selected = [clean(model_key) for model_key in (model_keys or Z_MODEL_KEYS) if clean(model_key)]
    if not selected or "all" in selected:
        selected = list(Z_MODEL_KEYS)
    unknown = [model_key for model_key in selected if model_key not in Z_MODEL_KEYS]
    if unknown:
        raise ValueError(f"Unknown Z model key(s): {', '.join(unknown)}")
    models = {model_key: _audit_model(wb, model_key) for model_key in selected}
    return {
        "status": "rule_audit_generated",
        "generated_at": generated_at or datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "selected_model_keys": selected,
        "models": models,
        "notes": [
            "Read-only audit: workbook was inspected but not saved.",
            "Audit uses the same rule/exclusive/default source-sheet concepts as Stingray and Grand Sport.",
            "Pricing, interiors, and runtime promotion are intentionally out of scope.",
        ],
    }


def render_z_rule_audit_markdown(audit: dict[str, Any]) -> str:
    lines = ["# Z Rule / Exclusive / Default Audit", "", f"Status: `{audit['status']}`", f"Generated: `{audit['generated_at']}`", ""]
    for note in audit.get("notes", []):
        lines.append(f"- {note}")
    for model_key, model in audit["models"].items():
        lines.extend(["", f"## {model_key.upper()}", "", "### Summary"])
        for key, value in model["summary"].items():
            lines.append(f"- {key}: {value}")
        lines.append("\n### Rule types")
        if model["ruleTypeCounts"]:
            for key, value in model["ruleTypeCounts"].items():
                lines.append(f"- {key}: {value}")
        else:
            lines.append("- none")
        lines.append("\n### Focused review counts")
        for key, value in model["focusedReviewCounts"].items():
            lines.append(f"- {key}: {value}")
        lines.append("\n### Hot spots")
        for key, value in model["hotSpots"].items():
            if isinstance(value, dict):
                summary = ", ".join(f"{k}={v}" for k, v in value.items() if not isinstance(v, list))
                list_bits = []
                if value.get("optionIds"):
                    list_bits.append(f"options: {' | '.join(value['optionIds'][:12])}")
                if value.get("ruleIds"):
                    list_bits.append(f"rules: {' | '.join(value['ruleIds'][:12])}")
                if value.get("defaultSelectedOptions"):
                    list_bits.append(f"defaultSelected: {' | '.join(value['defaultSelectedOptions'])}")
                lines.append(f"- {key}: {summary}" + (f" ({'; '.join(list_bits)})" if list_bits else ""))
            else:
                lines.append(f"- {key}: {value}")
    lines.append("")
    return "\n".join(lines)
