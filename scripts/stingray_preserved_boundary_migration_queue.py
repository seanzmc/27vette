#!/usr/bin/env python3
"""Classify remaining Stingray preserved cross-boundary rows into migration lanes."""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PACKAGE = ROOT / "data" / "stingray"
DEFAULT_PRODUCTION_DATA = ROOT / "form-app" / "data.js"
DEFAULT_OWNERSHIP_MANIFEST = DEFAULT_PACKAGE / "validation" / "projected_slice_ownership.csv"
DEFAULT_NON_SELECTABLE_REFERENCES = DEFAULT_PACKAGE / "validation" / "non_selectable_references.csv"

BUCKETS = [
    "ready_plain_exclude",
    "ready_requires",
    "ready_include_zero_auto_add",
    "catalog_unlock_needed",
    "color_support_needed",
    "z51_or_package_adjacent",
    "legacy_rule_only_or_non_selectable",
    "missing_or_unprojected_endpoint",
    "paired_price_rule_needed",
    "oracle_mismatch_or_ambiguous",
    "already_csv_owned_stale_preserved",
    "blocked_needs_design",
]

LANES_BY_BUCKET = {
    "ready_plain_exclude": "LANE B - plain excludes",
    "ready_requires": "LANE A - requires",
    "ready_include_zero_auto_add": "LANE C - include plus included-zero auto-add",
    "catalog_unlock_needed": "LANE F - catalog unlock",
    "color_support_needed": "LANE E - paint/color support",
    "z51_or_package_adjacent": "LANE Z - Z51/package-adjacent design",
    "legacy_rule_only_or_non_selectable": "LANE H - legacy/non-selectable design",
    "missing_or_unprojected_endpoint": "LANE F - endpoint research",
    "paired_price_rule_needed": "LANE C - paired price-rule design",
    "oracle_mismatch_or_ambiguous": "LANE R - oracle research",
    "already_csv_owned_stale_preserved": "LANE G - ownership cleanup",
    "blocked_needs_design": "LANE R - design review",
}

SAFE_BUCKETS = {"ready_plain_exclude", "ready_requires", "ready_include_zero_auto_add"}
COLOR_RPOS = {"GBA", "GKZ", "GPH", "GTR", "GBK", "G26", "G8G"}
Z51_PACKAGE_RPOS = {"Z51", "T0A", "TVS", "FE2", "FE3", "FE4", "J55", "G96", "M1N", "QTU", "V08", "ZYC"}
LEGACY_OR_NON_SELECTABLE_RPOS = {"5VM", "5W8", "5ZW", "CF8", "RYQ", "CFX"}
LEGACY_OR_NON_SELECTABLE_OPTION_IDS = {"opt_5vm_001", "opt_5w8_001", "opt_5zw_001", "opt_cf8_001", "opt_ryq_001", "opt_cfx_001"}
LEGACY_RULE_ONLY_RPOS = {"5VM", "5W8", "5ZW"}
LEGACY_RULE_ONLY_OPTION_IDS = {"opt_5vm_001", "opt_5w8_001", "opt_5zw_001"}
STRUCTURED_REFERENCE_RPOS = {"CF8", "RYQ"}
STRUCTURED_REFERENCE_OPTION_IDS = {"opt_cf8_001", "opt_ryq_001"}
DISPLAY_OR_DUPLICATE_RPOS = {"CFX"}
DISPLAY_OR_DUPLICATE_OPTION_IDS = {"opt_cfx_001"}

LEGACY_DESIGN_SUBTYPES = [
    "normal_selectable_misclassified",
    "rule_only_legacy_option_id",
    "production_structured_reference",
    "non_stingray_or_cross_variant_reference",
    "display_only_or_duplicate_reference",
    "package_control_plane_reference",
    "runtime_generated_placeholder",
    "ambiguous_needs_manual_decision",
]

RECOMMENDED_HANDLINGS = [
    "project_as_normal_selectable",
    "model_as_legacy_reference",
    "model_as_structured_non_selectable",
    "keep_preserved_runtime_owned",
    "requires_schema_design",
    "requires_manual_review",
]

LEGACY_IDENTIFIER_GROUPS = ["5VM", "5W8", "5ZW", "CF8", "RYQ", "CFX"]
STRIPE_RPOS = {"DPB", "DPC", "DPG", "DPL", "DPT", "DSY", "DSZ", "DT0", "DTH", "DUB", "DUE", "DUK", "DUW", "DZU", "DZV", "DZX"}
ROOF_RPOS = {"CF7", "CF8", "CC3", "C2Z", "D84", "D86", "CM9"}
EXTERIOR_ACCENT_RPOS = {"EFY", "EDU", "RYQ", "5V7", "STI", "PCU", "5ZU", "5ZZ"}
PASS_157_SURFACE_GROUPS = {
    "z51_or_package_adjacent": {"Z51", "T0A", "TVS", "5ZU", "5ZZ", "5V7", "STI", "PCU"},
    "stripe_rpos": STRIPE_RPOS,
    "roof_rpos": ROOF_RPOS,
    "exterior_accent_rpos": EXTERIOR_ACCENT_RPOS,
}
REGISTERED_REFERENCE_PREFLIGHT_BUCKETS = [
    "reference_selector_candidate",
    "hidden_rule_only_preserved",
    "keep_preserved_runtime_owned",
    "normal_catalog_projection_candidate",
    "needs_schema_design",
    "oracle_mismatch_or_ambiguous",
]
REGISTERED_REFERENCE_DECISIONS = [
    "yes_reference_selector",
    "freeze_preserve_for_now",
    "no_keep_preserved",
    "manual_review",
    "normal_catalog_projection_needed",
]
REFERENCE_SELECTOR_TARGET_RPOS = {"5VM", "5W8", "5ZW"}
REFERENCE_SELECTOR_MODEL_NAME = "Option A - non_selectable_reference selector"
REFERENCE_SELECTOR_SAFETY_RULES = [
    "non_selectable_reference IDs must exist in non_selectable_references.csv.",
    "non_selectable_reference IDs must not exist in selectables.csv.",
    "non_selectable_reference rules may compile to legacy production-shaped rules.",
    "non_selectable_reference rows must not create UI/display/catalog rows.",
    "non_selectable_reference condition terms must only be used for registered references.",
    "Unknown references fail validation.",
    "A reference with projection_policy=never_project_as_selectable cannot be converted to a normal selectable by migration scripts.",
]
REFERENCE_SELECTOR_FUTURE_IMPLEMENTATION_FILES = [
    "data/stingray/logic/dependency_rules.csv",
    "data/stingray/logic/condition_sets.csv",
    "data/stingray/logic/condition_terms.csv",
    "scripts/stingray_csv_first_slice.py",
    "tests/stingray/first-slice-csv.test.mjs",
    "tests/stingray/first-slice-shadow-data.test.mjs",
]

HIDDEN_REFERENCE_CONTROL_PLANE_TARGETS = {
    "5V7",
    "5ZU",
    "5ZZ",
    "T0A",
    "TVS",
    "Z51",
    "opt_5v7_001",
    "opt_5zu_001",
    "opt_5zz_001",
    "opt_t0a_001",
    "opt_tvs_001",
    "opt_z51_001",
}


class QueueError(ValueError):
    pass


def load_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def is_active(row: dict[str, str]) -> bool:
    return row.get("active", "").lower() == "true"


def load_production_data(path: Path) -> dict[str, Any]:
    source = path.read_text(encoding="utf-8")
    match = re.search(
        r"window\.CORVETTE_FORM_DATA\s*=\s*(\{.*\})\s*;\s*window\.STINGRAY_FORM_DATA\s*=",
        source,
        flags=re.DOTALL,
    )
    if not match:
        raise QueueError(f"Could not locate window.CORVETTE_FORM_DATA assignment in {path}.")
    registry = json.loads(match.group(1))
    try:
        return registry["models"]["stingray"]["data"]
    except KeyError as error:
        raise QueueError(f"Could not locate models.stingray.data in {path}: {error}.") from error


def option_id_for_rpo(rpo: str) -> str:
    if not rpo:
        return ""
    return f"opt_{rpo.lower()}_001"


def rpo_from_option_id(option_id: str) -> str:
    match = re.fullmatch(r"opt_(.+?)_001", option_id or "")
    return match.group(1).upper() if match else ""


def selected_condition_targets(condition_terms: list[dict[str, str]]) -> dict[str, set[str]]:
    targets: dict[str, set[str]] = defaultdict(set)
    for row in condition_terms:
        if row.get("term_type") == "selected" and row.get("operator") == "is_true" and row.get("negate") == "false":
            targets[row.get("left_ref", "")].add(row.get("condition_set_id", ""))
    return dict(targets)


def dependency_pairs(dependency_rules: list[dict[str, str]], condition_terms: list[dict[str, str]]) -> set[tuple[str, str, str]]:
    selected_targets = selected_condition_targets(condition_terms)
    condition_to_target = {
        condition_set_id: target_id
        for target_id, condition_ids in selected_targets.items()
        for condition_set_id in condition_ids
    }
    pairs: set[tuple[str, str, str]] = set()
    for row in dependency_rules:
        if not is_active(row) or row.get("subject_selector_type") != "selectable":
            continue
        target_id = condition_to_target.get(row.get("target_condition_set_id", ""))
        if target_id:
            pairs.add((row.get("rule_type", ""), row.get("subject_selector_id", ""), target_id))
    return pairs


def auto_add_pairs(auto_adds: list[dict[str, str]], price_policies: list[dict[str, str]]) -> set[tuple[str, str, str]]:
    policies = {row.get("price_policy_id", ""): row for row in price_policies}
    pairs: set[tuple[str, str, str]] = set()
    for row in auto_adds:
        if not is_active(row) or row.get("source_selector_type") != "selectable":
            continue
        policy = policies.get(row.get("target_price_policy_id", ""), {})
        pairs.add((row.get("source_selector_id", ""), row.get("target_selectable_id", ""), policy.get("policy_type", "")))
    return pairs


def price_rule_pairs(price_rules: list[dict[str, str]]) -> set[tuple[str, str]]:
    return {
        (row.get("condition_option_id", ""), row.get("target_option_id", ""))
        for row in price_rules
        if row.get("condition_option_id", "") and row.get("target_option_id", "")
    }


def load_non_selectable_references(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    return [row for row in load_csv(path) if is_active(row)]


def registry_indexes(rows: list[dict[str, str]]) -> dict[str, dict[str, str]]:
    indexes: dict[str, dict[str, str]] = {}
    for row in rows:
        for key in [row.get("rpo", ""), row.get("option_id", ""), row.get("reference_id", "")]:
            if key:
                indexes[key] = row
    return indexes


def registry_matches(refs: set[str], registry: dict[str, dict[str, str]]) -> list[dict[str, str]]:
    matches_by_id: dict[str, dict[str, str]] = {}
    for ref in refs:
        row = registry.get(ref)
        if row:
            matches_by_id[row.get("reference_id", "")] = row
    return [matches_by_id[key] for key in sorted(matches_by_id)]


def join_unique(values: list[str]) -> str:
    return "|".join(sorted({value for value in values if value}))


def registry_details(refs: set[str], registry: dict[str, dict[str, str]]) -> dict[str, Any]:
    matches = registry_matches(refs, registry)
    return {
        "registered_reference": bool(matches),
        "registered_references": [row.get("reference_id", "") for row in matches],
        "reference_type": join_unique([row.get("reference_type", "") for row in matches]),
        "projection_policy": join_unique([row.get("projection_policy", "") for row in matches]),
        "compiler_policy": join_unique([row.get("compiler_policy", "") for row in matches]),
    }


def source_refs_for_row(row: dict[str, Any]) -> set[str]:
    refs = {
        row.get("source_rpo", ""),
        row.get("source_option_id", ""),
        row.get("source_resolved_option_id", ""),
    }
    canonical = {canonical_identifier(ref) for ref in refs if ref}
    return {ref for ref in refs if ref} | {ref for ref in canonical if ref}


def target_refs_for_row(row: dict[str, Any]) -> set[str]:
    refs = {
        row.get("target_rpo", ""),
        row.get("target_option_id", ""),
        row.get("target_resolved_option_id", ""),
    }
    canonical = {canonical_identifier(ref) for ref in refs if ref}
    return {ref for ref in refs if ref} | {ref for ref in canonical if ref}


def registered_reference_ids_for_refs(refs: set[str], registry: dict[str, dict[str, str]]) -> list[str]:
    return [row.get("rpo", "") or row.get("option_id", "") for row in registry_matches(refs, registry)]


def reference_role(row: dict[str, Any], registry: dict[str, dict[str, str]]) -> str:
    source_matches = registered_reference_ids_for_refs(source_refs_for_row(row), registry)
    target_matches = registered_reference_ids_for_refs(target_refs_for_row(row), registry)
    if source_matches and target_matches:
        return "both"
    if source_matches:
        return "source"
    if target_matches:
        return "target"
    return ""


def production_indexes(data: dict[str, Any]) -> dict[str, Any]:
    choices_by_option: dict[str, list[dict[str, Any]]] = defaultdict(list)
    choices_by_rpo: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for choice in data.get("choices", []):
        option_id = choice.get("option_id", "")
        rpo = choice.get("rpo", "")
        if option_id:
            choices_by_option[option_id].append(choice)
        if rpo:
            choices_by_rpo[rpo].append(choice)

    rules_by_pair: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for rule in data.get("rules", []):
        rules_by_pair[(rule.get("source_id", ""), rule.get("target_id", ""))].append(rule)

    price_rules_by_pair: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for rule in data.get("priceRules", []):
        price_rules_by_pair[(rule.get("condition_option_id", ""), rule.get("target_option_id", ""))].append(rule)

    return {
        "choices_by_option": dict(choices_by_option),
        "choices_by_rpo": dict(choices_by_rpo),
        "rules_by_pair": dict(rules_by_pair),
        "price_rules_by_pair": dict(price_rules_by_pair),
    }


def unique_option_for_rpo(indexes: dict[str, Any], rpo: str) -> str:
    choices = indexes["choices_by_rpo"].get(rpo, [])
    selectable_ids = sorted(
        {
            choice.get("option_id", "")
            for choice in choices
            if choice.get("option_id", "") and str(choice.get("selectable", "")).lower() == "true"
        }
    )
    if len(selectable_ids) == 1:
        return selectable_ids[0]
    all_ids = sorted({choice.get("option_id", "") for choice in choices if choice.get("option_id", "")})
    if len(all_ids) == 1:
        return all_ids[0]
    return option_id_for_rpo(rpo)


def endpoint(
    row: dict[str, str],
    side: str,
    indexes: dict[str, Any],
    csv_selectable_ids: set[str],
    projected_rpos: set[str],
) -> dict[str, Any]:
    rpo = row.get(f"{side}_rpo", "")
    option_id = row.get(f"{side}_option_id", "")
    if not option_id and rpo:
        option_id = unique_option_for_rpo(indexes, rpo)
    if not rpo and option_id:
        choices = indexes["choices_by_option"].get(option_id, [])
        rpos = sorted({choice.get("rpo", "") for choice in choices if choice.get("rpo", "")})
        rpo = rpos[0] if len(rpos) == 1 else rpo_from_option_id(option_id)

    choices = indexes["choices_by_option"].get(option_id, [])
    selectable_choices = [choice for choice in choices if str(choice.get("selectable", "")).lower() == "true"]
    normal_selectable = bool(selectable_choices)
    exists_in_oracle = bool(choices) or bool(indexes["choices_by_rpo"].get(rpo, []))
    projected = bool(rpo and rpo in projected_rpos and option_id in csv_selectable_ids)
    non_selectable = (
        rpo in LEGACY_OR_NON_SELECTABLE_RPOS
        or option_id in LEGACY_OR_NON_SELECTABLE_OPTION_IDS
        or (exists_in_oracle and not normal_selectable)
    )
    return {
        "rpo": rpo,
        "option_id": option_id,
        "exists_in_oracle": exists_in_oracle,
        "normal_selectable": normal_selectable,
        "projected": projected,
        "non_selectable": non_selectable,
    }


def endpoint_refs(source: dict[str, Any], target: dict[str, Any]) -> set[str]:
    return {value for value in [source["rpo"], source["option_id"], target["rpo"], target["option_id"]] if value}


def has_color_ref(refs: set[str]) -> bool:
    return bool(refs & COLOR_RPOS)


def has_z51_or_package_ref(refs: set[str], row: dict[str, str]) -> bool:
    reason = row.get("reason", "").lower()
    return bool(refs & Z51_PACKAGE_RPOS) or "spoiler replace" in reason or "package" in reason


def has_legacy_ref(source: dict[str, Any], target: dict[str, Any]) -> bool:
    refs = endpoint_refs(source, target)
    return bool(refs & LEGACY_OR_NON_SELECTABLE_RPOS) or bool(refs & LEGACY_OR_NON_SELECTABLE_OPTION_IDS) or source["non_selectable"] or target["non_selectable"]


def has_explicit_legacy_option_ref(row: dict[str, str]) -> bool:
    return row.get("source_option_id", "") in LEGACY_OR_NON_SELECTABLE_OPTION_IDS or row.get("target_option_id", "") in LEGACY_OR_NON_SELECTABLE_OPTION_IDS


def classify_row(row: dict[str, str], manifest_row_id: str, context: dict[str, Any]) -> dict[str, Any]:
    indexes = context["production_indexes"]
    source = endpoint(row, "source", indexes, context["csv_selectable_ids"], context["projected_rpos"])
    target = endpoint(row, "target", indexes, context["csv_selectable_ids"], context["projected_rpos"])
    refs = endpoint_refs(source, target)
    source_id = source["option_id"]
    target_id = target["option_id"]
    record_type = row.get("record_type", "")
    rules = indexes["rules_by_pair"].get((source_id, target_id), [])
    price_rules = indexes["price_rules_by_pair"].get((source_id, target_id), [])
    rule_types = sorted({rule.get("rule_type", "") for rule in rules if rule.get("rule_type", "")})
    oracle_rule_type = rule_types[0] if len(rule_types) == 1 else ""
    oracle_messages = sorted(
        {
            str(rule.get("disabled_reason", "") or rule.get("message", ""))
            for rule in rules
            if str(rule.get("disabled_reason", "") or rule.get("message", ""))
        }
    )
    oracle_message = oracle_messages[0] if len(oracle_messages) == 1 else ""

    dependency_pairs_set = context["dependency_pairs"]
    auto_add_pairs_set = context["auto_add_pairs"]
    price_rule_pairs_set = context["price_rule_pairs"]

    bucket = "oracle_mismatch_or_ambiguous"
    reason = "Oracle relationship is missing or ambiguous."

    if record_type == "rule" and oracle_rule_type and (oracle_rule_type, source_id, target_id) in dependency_pairs_set:
        bucket = "already_csv_owned_stale_preserved"
        reason = f"dependency_rules.csv already owns {oracle_rule_type} {source_id} -> {target_id}."
    elif record_type == "rule" and oracle_rule_type == "includes" and (source_id, target_id, "force_amount") in auto_add_pairs_set:
        bucket = "already_csv_owned_stale_preserved"
        reason = f"auto_adds.csv already owns include {source_id} -> {target_id}."
    elif record_type == "priceRule" and (source_id, target_id) in price_rule_pairs_set:
        bucket = "already_csv_owned_stale_preserved"
        reason = f"price_rules.csv already owns priceRule {source_id} -> {target_id}."
    elif has_color_ref(refs) or record_type == "ruleGroup":
        bucket = "color_support_needed"
        reason = "Paint/color or color rule-group behavior needs dedicated support."
    elif has_explicit_legacy_option_ref(row):
        bucket = "legacy_rule_only_or_non_selectable"
        reason = "Source or target is an explicit legacy rule-only option reference."
    elif has_z51_or_package_ref(refs, row):
        bucket = "z51_or_package_adjacent"
        reason = "Z51, package-adjacent, or spoiler replacement/default behavior remains design-gated."
    elif has_legacy_ref(source, target):
        bucket = "legacy_rule_only_or_non_selectable"
        reason = "Source or target is a legacy rule-only or production non-selectable reference."
    elif source["exists_in_oracle"] and source["normal_selectable"] and not source["projected"]:
        bucket = "catalog_unlock_needed"
        reason = f"Source {source['rpo'] or source_id} is a normal oracle selectable but is not projected-owned."
    elif target["exists_in_oracle"] and target["normal_selectable"] and not target["projected"]:
        bucket = "catalog_unlock_needed"
        reason = f"Target {target['rpo'] or target_id} is a normal oracle selectable but is not projected-owned."
    elif not source["projected"] or not target["projected"]:
        bucket = "missing_or_unprojected_endpoint"
        reason = "Source or target endpoint is missing from the projected CSV selectable surface."
    elif record_type == "priceRule":
        bucket = "paired_price_rule_needed"
        reason = "Preserved priceRule row needs paired pricing migration design."
    elif record_type == "rule" and oracle_rule_type == "excludes" and not price_rules:
        bucket = "ready_plain_exclude"
        reason = "Oracle confirms plain exclude with projected-owned endpoints and no paired priceRule."
    elif record_type == "rule" and oracle_rule_type == "requires" and not price_rules:
        bucket = "ready_requires"
        reason = "Oracle confirms requirement with projected-owned endpoints and no paired priceRule."
    elif record_type == "rule" and oracle_rule_type == "includes" and price_rules:
        zero_price_rules = [price_rule for price_rule in price_rules if str(price_rule.get("price_value", "")) in {"0", "0.0"}]
        if zero_price_rules and context["has_included_zero_policy"]:
            bucket = "ready_include_zero_auto_add"
            reason = "Oracle confirms include plus included-zero priceRule with projected-owned endpoints."
        else:
            bucket = "paired_price_rule_needed"
            reason = "Include has paired price behavior that is not a simple included-zero policy."
    elif record_type == "rule" and price_rules:
        bucket = "paired_price_rule_needed"
        reason = "Rule has paired priceRule behavior and needs pricing-aware migration."
    elif record_type not in {"rule", "priceRule", "ruleGroup"}:
        bucket = "blocked_needs_design"
        reason = f"Unsupported preserved record type for migration queue: {record_type}."

    return {
        "manifest_row_id": manifest_row_id,
        "record_type": record_type,
        "source_rpo": row.get("source_rpo", ""),
        "source_option_id": row.get("source_option_id", ""),
        "target_rpo": row.get("target_rpo", ""),
        "target_option_id": row.get("target_option_id", ""),
        "source_resolved_option_id": source_id,
        "target_resolved_option_id": target_id,
        "oracle_rule_type": oracle_rule_type,
        "oracle_message": oracle_message,
        "oracle_rule_count": len(rules),
        "oracle_price_rule_count": len(price_rules),
        "source_projected": source["projected"],
        "target_projected": target["projected"],
        "bucket": bucket,
        "reason": reason,
        "recommended_next_lane": LANES_BY_BUCKET[bucket],
    }


def build_report(args: argparse.Namespace) -> dict[str, Any]:
    package = Path(args.package)
    production_data = load_production_data(Path(args.production_data))
    manifest_path = Path(args.ownership_manifest)
    manifest_rows = load_csv(manifest_path)
    active_preserved = [
        (index, row)
        for index, row in enumerate(manifest_rows, start=2)
        if is_active(row) and row.get("ownership", "") == "preserved_cross_boundary"
    ]

    selectables = [row for row in load_csv(package / "catalog" / "selectables.csv") if is_active(row)]
    ownership = [row for row in manifest_rows if is_active(row)]
    condition_terms = load_csv(package / "logic" / "condition_terms.csv")
    dependency_rules = load_csv(package / "logic" / "dependency_rules.csv")
    auto_adds = load_csv(package / "logic" / "auto_adds.csv")
    price_policies = load_csv(package / "pricing" / "price_policies.csv")
    price_rules = load_csv(package / "pricing" / "price_rules.csv")
    non_selectable_references = load_non_selectable_references(Path(args.non_selectable_references))

    context = {
        "production_indexes": production_indexes(production_data),
        "csv_selectable_ids": {row["selectable_id"] for row in selectables},
        "projected_rpos": {
            row.get("rpo", "")
            for row in ownership
            if row.get("record_type", "") == "selectable" and row.get("ownership", "") == "projected_owned" and row.get("rpo", "")
        },
        "dependency_pairs": dependency_pairs(dependency_rules, condition_terms),
        "auto_add_pairs": auto_add_pairs(auto_adds, price_policies),
        "price_rule_pairs": price_rule_pairs(price_rules),
        "has_included_zero_policy": any(
            row.get("price_policy_id", "") == "included_zero"
            and row.get("policy_type", "") == "force_amount"
            and row.get("amount_usd", "") == "0"
            for row in price_policies
        ),
        "non_selectable_registry": registry_indexes(non_selectable_references),
    }

    classified_rows = [
        classify_row(row, f"csv_row_{index}", context)
        for index, row in active_preserved
    ]
    for row in classified_rows:
        row.update(registry_details(row_refs(row), context["non_selectable_registry"]))
    classified_rows.sort(
        key=lambda row: (
            BUCKETS.index(row["bucket"]),
            row["record_type"],
            row["source_rpo"] or row["source_option_id"],
            row["target_rpo"] or row["target_option_id"],
            row["manifest_row_id"],
        )
    )
    bucket_counts = Counter(row["bucket"] for row in classified_rows)
    bucket_summary = {bucket: bucket_counts.get(bucket, 0) for bucket in BUCKETS}
    recommended = recommended_next_lane(bucket_summary)
    return {
        "schema_version": 1,
        "status": "allowed",
        "active_preserved_cross_boundary_count": len(active_preserved),
        "classified_row_count": len(classified_rows),
        "bucket_summary": bucket_summary,
        "recommended_next_lane": recommended,
        "rows": classified_rows,
    }


def canonical_identifier(ref: str) -> str:
    rpo = rpo_from_option_id(ref)
    return rpo or ref


def row_refs(row: dict[str, Any]) -> set[str]:
    refs = {
        row.get("source_rpo", ""),
        row.get("source_option_id", ""),
        row.get("target_rpo", ""),
        row.get("target_option_id", ""),
        row.get("source_resolved_option_id", ""),
        row.get("target_resolved_option_id", ""),
    }
    canonical = {canonical_identifier(ref) for ref in refs if ref}
    return {ref for ref in refs if ref} | {ref for ref in canonical if ref}


def legacy_identifiers_for_row(row: dict[str, Any]) -> list[str]:
    refs = row_refs(row)
    return [identifier for identifier in LEGACY_IDENTIFIER_GROUPS if identifier in refs]


def endpoint_status(row: dict[str, Any], side: str) -> str:
    rpo = row.get(f"{side}_rpo", "")
    option_id = row.get(f"{side}_option_id", "")
    resolved_option_id = row.get(f"{side}_resolved_option_id", "")
    refs = {ref for ref in [rpo, option_id, resolved_option_id, canonical_identifier(option_id), canonical_identifier(resolved_option_id)] if ref}
    if refs & LEGACY_RULE_ONLY_RPOS or refs & LEGACY_RULE_ONLY_OPTION_IDS:
        return "rule_only_legacy_option_id"
    if refs & STRUCTURED_REFERENCE_RPOS or refs & STRUCTURED_REFERENCE_OPTION_IDS:
        return "production_structured_reference"
    if refs & DISPLAY_OR_DUPLICATE_RPOS or refs & DISPLAY_OR_DUPLICATE_OPTION_IDS:
        return "display_only_or_duplicate_reference"
    if row.get(f"{side}_projected", False):
        return "projected_owned_selectable"
    return "unprojected_or_missing"


def oracle_behavior(row: dict[str, Any]) -> str:
    parts: list[str] = []
    if row.get("oracle_rule_count", 0):
        rule_type = row.get("oracle_rule_type", "") or "ambiguous"
        parts.append(f"rule:{rule_type}")
    if row.get("oracle_price_rule_count", 0):
        parts.append(f"priceRule:{row['oracle_price_rule_count']}")
    return " + ".join(parts) if parts else "not_found"


def related_surfaces(row: dict[str, Any]) -> list[str]:
    refs = row_refs(row)
    return [
        surface
        for surface, surface_refs in PASS_157_SURFACE_GROUPS.items()
        if refs & surface_refs
    ]


def classify_legacy_design_row(row: dict[str, Any]) -> dict[str, str]:
    refs = row_refs(row)
    source_status = endpoint_status(row, "source")
    target_status = endpoint_status(row, "target")
    surfaces = related_surfaces(row)

    if refs & LEGACY_RULE_ONLY_RPOS or refs & LEGACY_RULE_ONLY_OPTION_IDS:
        return {
            "subtype": "rule_only_legacy_option_id",
            "recommended_handling": "model_as_legacy_reference",
            "recommended_next_lane": "LANE H: add legacy_reference table or structured-reference support",
            "should_be_normal_selectable": "no - production uses this as a generated rule-only option id",
        }
    if refs & STRUCTURED_REFERENCE_RPOS or refs & STRUCTURED_REFERENCE_OPTION_IDS:
        return {
            "subtype": "production_structured_reference",
            "recommended_handling": "model_as_structured_non_selectable",
            "recommended_next_lane": "LANE H: add legacy_reference table or structured-reference support",
            "should_be_normal_selectable": "no - production uses this as a structured non-selectable reference",
        }
    if refs & DISPLAY_OR_DUPLICATE_RPOS or refs & DISPLAY_OR_DUPLICATE_OPTION_IDS:
        return {
            "subtype": "display_only_or_duplicate_reference",
            "recommended_handling": "model_as_structured_non_selectable",
            "recommended_next_lane": "LANE H: add legacy_reference table or structured-reference support",
            "should_be_normal_selectable": "no - production indicates a display-only or duplicate reference surface",
        }
    if source_status == "unprojected_or_missing" or target_status == "unprojected_or_missing":
        return {
            "subtype": "normal_selectable_misclassified",
            "recommended_handling": "project_as_normal_selectable",
            "recommended_next_lane": "LANE A: project normal selectables misclassified as legacy",
            "should_be_normal_selectable": "yes - inspect as catalog projection candidate before rule migration",
        }
    if "z51_or_package_adjacent" in surfaces:
        return {
            "subtype": "package_control_plane_reference",
            "recommended_handling": "requires_schema_design",
            "recommended_next_lane": "LANE Z: package-adjacent design",
            "should_be_normal_selectable": "no - package/control-plane behavior needs design before projection",
        }
    return {
        "subtype": "ambiguous_needs_manual_decision",
        "recommended_handling": "requires_manual_review",
        "recommended_next_lane": "LANE G: manual review list only",
        "should_be_normal_selectable": "unknown - needs manual decision",
    }


def build_legacy_nonselectable_design_report(args: argparse.Namespace) -> dict[str, Any]:
    queue = build_report(args)
    legacy_rows = [
        row
        for row in queue["rows"]
        if row.get("bucket", "") == "legacy_rule_only_or_non_selectable"
    ]
    design_rows: list[dict[str, Any]] = []
    for row in legacy_rows:
        decision = classify_legacy_design_row(row)
        design_rows.append(
            {
                "manifest_row_id": row["manifest_row_id"],
                "record_type": row["record_type"],
                "source_rpo": row["source_rpo"],
                "source_option_id": row["source_option_id"],
                "target_rpo": row["target_rpo"],
                "target_option_id": row["target_option_id"],
                "source_resolved_option_id": row["source_resolved_option_id"],
                "target_resolved_option_id": row["target_resolved_option_id"],
                "current_reason": row["reason"],
                "oracle_behavior": oracle_behavior(row),
                "source_status": endpoint_status(row, "source"),
                "target_status": endpoint_status(row, "target"),
                "legacy_identifiers": legacy_identifiers_for_row(row),
                "related_surfaces": related_surfaces(row),
                "registered_reference": row["registered_reference"],
                "registered_references": row["registered_references"],
                "reference_type": row["reference_type"],
                "projection_policy": row["projection_policy"],
                "compiler_policy": row["compiler_policy"],
                "subtype": decision["subtype"],
                "recommended_handling": decision["recommended_handling"],
                "recommended_next_lane": decision["recommended_next_lane"],
                "should_be_normal_selectable": decision["should_be_normal_selectable"],
            }
        )

    design_rows.sort(
        key=lambda row: (
            LEGACY_DESIGN_SUBTYPES.index(row["subtype"]),
            row["record_type"],
            row["source_rpo"] or row["source_option_id"] or row["source_resolved_option_id"],
            row["target_rpo"] or row["target_option_id"] or row["target_resolved_option_id"],
            row["manifest_row_id"],
        )
    )

    subtype_counts = Counter(row["subtype"] for row in design_rows)
    handling_counts = Counter(row["recommended_handling"] for row in design_rows)
    related_surface_counts = Counter(surface for row in design_rows for surface in row["related_surfaces"])
    identifier_groups = {
        identifier: {
            "count": sum(1 for row in design_rows if identifier in row["legacy_identifiers"]),
            "manifest_row_ids": [
                row["manifest_row_id"]
                for row in design_rows
                if identifier in row["legacy_identifiers"]
            ],
        }
        for identifier in LEGACY_IDENTIFIER_GROUPS
    }
    recommended = recommend_legacy_design_next_lane(subtype_counts)
    return {
        "schema_version": 1,
        "status": "allowed",
        "source_bucket": "legacy_rule_only_or_non_selectable",
        "source_row_count": len(legacy_rows),
        "classified_row_count": len(design_rows),
        "subtype_summary": {subtype: subtype_counts.get(subtype, 0) for subtype in LEGACY_DESIGN_SUBTYPES},
        "recommended_handling_summary": {
            handling: handling_counts.get(handling, 0)
            for handling in RECOMMENDED_HANDLINGS
        },
        "related_surface_summary": {
            surface: related_surface_counts.get(surface, 0)
            for surface in PASS_157_SURFACE_GROUPS
        },
        "identifier_groups": identifier_groups,
        "recommended_next_lane": recommended,
        "rows": design_rows,
    }


def selector_preflight_decision(row: dict[str, Any]) -> dict[str, Any]:
    reference_types = set(row.get("reference_type", "").split("|"))
    oracle = oracle_behavior(row)
    role = row.get("reference_role", "")

    if "legacy_option_id" in reference_types:
        source_token = row.get("source_rpo") or row.get("source_option_id") or row.get("source_resolved_option_id")
        target_token = row.get("target_rpo") or row.get("target_option_id") or row.get("target_resolved_option_id")
        if source_token in LEGACY_RULE_ONLY_RPOS | LEGACY_RULE_ONLY_OPTION_IDS and target_token in LEGACY_RULE_ONLY_RPOS | LEGACY_RULE_ONLY_OPTION_IDS:
            impact_classification = "future_schema_completeness_only"
        elif source_token in HIDDEN_REFERENCE_CONTROL_PLANE_TARGETS or target_token in HIDDEN_REFERENCE_CONTROL_PLANE_TARGETS:
            impact_classification = "hidden_production_control_plane_only"
        else:
            impact_classification = "future_schema_completeness_only"
        return {
            "bucket": "hidden_rule_only_preserved",
            "candidate_selector_model": "preserve_hidden_rule_only_reference",
            "candidate_selector_detail": "freeze preserved row; no customer-facing or cutover-blocking migration reason",
            "recommended_handling": "freeze_preserve_for_now",
            "can_migrate_without_customer_selectable_projection": False,
            "compiler_schema_support_required": False,
            "customer_facing_impact": "none",
            "cutover_blocking": False,
            "preserved_classification": impact_classification,
            "freeze_status": "frozen_preserve_for_now",
            "rationale": "Remaining registered rule-only legacy option rows are hidden production/control-plane or future schema-completeness rows; active production rule objects alone are not a migration reason.",
        }

    if "structured_reference" in reference_types:
        return {
            "bucket": "keep_preserved_runtime_owned",
            "candidate_selector_model": "keep_preserved_only",
            "candidate_selector_detail": "registry explanation only",
            "recommended_handling": "no_keep_preserved",
            "can_migrate_without_customer_selectable_projection": False,
            "compiler_schema_support_required": False,
            "customer_facing_impact": "none",
            "cutover_blocking": False,
            "preserved_classification": "runtime_owned_structured_reference",
            "freeze_status": "preserve_runtime_owned",
            "rationale": "Production structured reference remains runtime/generated-owned until a broader structured-reference model is approved.",
        }

    if "display_duplicate" in reference_types and oracle == "rule:includes":
        return {
            "bucket": "needs_schema_design",
            "candidate_selector_model": "non_selectable_auto_add_target",
            "candidate_selector_detail": "auto_add target_selectable_id cannot currently point to a non-selectable reference",
            "recommended_handling": "manual_review",
            "can_migrate_without_customer_selectable_projection": False,
            "compiler_schema_support_required": True,
            "customer_facing_impact": "none",
            "cutover_blocking": False,
            "preserved_classification": "future_schema_completeness_only",
            "freeze_status": "preserve_until_approved_cutover_scope",
            "rationale": "Display duplicate include target may need non-selectable auto-add target support before migration.",
        }

    if "display_duplicate" in reference_types:
        return {
            "bucket": "keep_preserved_runtime_owned",
            "candidate_selector_model": "keep_preserved_only",
            "candidate_selector_detail": "display duplicate is not a dependency selector candidate",
            "recommended_handling": "no_keep_preserved",
            "can_migrate_without_customer_selectable_projection": False,
            "compiler_schema_support_required": False,
            "customer_facing_impact": "none",
            "cutover_blocking": False,
            "preserved_classification": "display_duplicate_runtime_owned",
            "freeze_status": "preserve_runtime_owned",
            "rationale": "Display duplicate reference should not be treated as a customer-selectable catalog row.",
        }

    return {
        "bucket": "oracle_mismatch_or_ambiguous",
        "candidate_selector_model": "manual_research",
        "candidate_selector_detail": "registered reference type did not match a known selector preflight rule",
        "recommended_handling": "manual_review",
        "can_migrate_without_customer_selectable_projection": False,
        "compiler_schema_support_required": False,
        "customer_facing_impact": "unknown",
        "cutover_blocking": False,
        "preserved_classification": "manual_review",
        "freeze_status": "preserve_until_reviewed",
        "rationale": "Reference needs manual review before a selector model can be proposed.",
    }


def build_registered_reference_selector_preflight_report(args: argparse.Namespace) -> dict[str, Any]:
    queue = build_report(args)
    registry = registry_indexes(load_non_selectable_references(Path(args.non_selectable_references)))
    registered_rows = [row for row in queue["rows"] if row.get("registered_reference") is True]
    preflight_rows: list[dict[str, Any]] = []
    for row in registered_rows:
        role = reference_role(row, registry)
        row_with_role = {**row, "reference_role": role}
        decision = selector_preflight_decision(row_with_role)
        involved = registered_reference_ids_for_refs(row_refs(row), registry)
        preflight_rows.append(
            {
                "manifest_row_id": row["manifest_row_id"],
                "record_type": row["record_type"],
                "source_rpo": row["source_rpo"],
                "source_option_id": row["source_option_id"],
                "target_rpo": row["target_rpo"],
                "target_option_id": row["target_option_id"],
                "source_resolved_option_id": row["source_resolved_option_id"],
                "target_resolved_option_id": row["target_resolved_option_id"],
                "oracle_behavior": oracle_behavior(row),
                "oracle_message": row.get("oracle_message", ""),
                "registered_reference_involved": involved,
                "reference_role": role,
                "reference_type": row["reference_type"],
                "projection_policy": row["projection_policy"],
                "compiler_policy": row["compiler_policy"],
                "current_preserved_reason": row["reason"],
                "candidate_selector_model": decision["candidate_selector_model"],
                "candidate_selector_detail": decision["candidate_selector_detail"],
                "recommended_handling": decision["recommended_handling"],
                "bucket": decision["bucket"],
                "rationale": decision["rationale"],
                "can_migrate_without_customer_selectable_projection": decision["can_migrate_without_customer_selectable_projection"],
                "compiler_schema_support_required": decision["compiler_schema_support_required"],
                "customer_facing_impact": decision["customer_facing_impact"],
                "cutover_blocking": decision["cutover_blocking"],
                "preserved_classification": decision["preserved_classification"],
                "freeze_status": decision["freeze_status"],
            }
        )

    preflight_rows.sort(
        key=lambda row: (
            REGISTERED_REFERENCE_PREFLIGHT_BUCKETS.index(row["bucket"]),
            row["registered_reference_involved"],
            row["record_type"],
            row["source_rpo"] or row["source_option_id"] or row["source_resolved_option_id"],
            row["target_rpo"] or row["target_option_id"] or row["target_resolved_option_id"],
            row["manifest_row_id"],
        )
    )
    bucket_counts = Counter(row["bucket"] for row in preflight_rows)
    reference_summary = build_registered_reference_summary(preflight_rows)
    compiler_schema_support_required = any(row["compiler_schema_support_required"] for row in preflight_rows)
    can_migrate_without_projection = any(row["can_migrate_without_customer_selectable_projection"] for row in preflight_rows)
    return {
        "schema_version": 1,
        "status": "allowed",
        "inspected_row_count": len(preflight_rows),
        "bucket_summary": {
            bucket: bucket_counts.get(bucket, 0)
            for bucket in REGISTERED_REFERENCE_PREFLIGHT_BUCKETS
        },
        "reference_summary": reference_summary,
        "can_any_reference_migrate_without_customer_selectable_projection": can_migrate_without_projection,
        "compiler_schema_support_required": compiler_schema_support_required,
        "recommended_next_pass": recommend_registered_reference_next_pass(reference_summary, bucket_counts),
        "rows": preflight_rows,
    }


def build_registered_reference_summary(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    summary: dict[str, dict[str, Any]] = {}
    for identifier in LEGACY_IDENTIFIER_GROUPS:
        matching = [row for row in rows if identifier in row["registered_reference_involved"]]
        if not matching:
            continue
        decisions = Counter(row["recommended_handling"] for row in matching)
        models = Counter(row["candidate_selector_model"] for row in matching)
        buckets = Counter(row["bucket"] for row in matching)
        reference_types = sorted({row["reference_type"] for row in matching if row["reference_type"]})
        summary[identifier] = {
            "row_count": len(matching),
            "source_count": sum(1 for row in matching if row["reference_role"] in {"source", "both"}),
            "target_count": sum(1 for row in matching if row["reference_role"] in {"target", "both"}),
            "both_count": sum(1 for row in matching if row["reference_role"] == "both"),
            "reference_type": "|".join(reference_types),
            "recommended_handling": decisions.most_common(1)[0][0],
            "candidate_selector_model": models.most_common(1)[0][0],
            "dominant_bucket": buckets.most_common(1)[0][0],
            "compiler_schema_support_required": any(row["compiler_schema_support_required"] for row in matching),
            "can_migrate_without_customer_selectable_projection": any(
                row["can_migrate_without_customer_selectable_projection"] for row in matching
            ),
            "customer_facing_impact": sorted({row["customer_facing_impact"] for row in matching}),
            "preserved_classification": sorted({row["preserved_classification"] for row in matching}),
            "freeze_status": sorted({row["freeze_status"] for row in matching}),
        }
    return summary


def endpoint_token(row: dict[str, Any], side: str) -> str:
    rpo = row.get(f"{side}_rpo", "")
    option_id = row.get(f"{side}_option_id", "")
    resolved_option_id = row.get(f"{side}_resolved_option_id", "")
    return rpo or rpo_from_option_id(option_id) or rpo_from_option_id(resolved_option_id) or option_id or resolved_option_id


def selector_slug(value: str) -> str:
    canonical = rpo_from_option_id(value) or value
    return re.sub(r"[^a-z0-9]+", "_", canonical.lower()).strip("_")


def reference_selector_id(identifier: str) -> str:
    return f"ref_{selector_slug(identifier)}"


def registered_reference_for_side(
    row: dict[str, Any],
    side: str,
    registry: dict[str, dict[str, str]],
) -> dict[str, str] | None:
    refs = source_refs_for_row(row) if side == "source" else target_refs_for_row(row)
    matches = [
        match
        for match in registry_matches(refs, registry)
        if (match.get("rpo", "") or rpo_from_option_id(match.get("option_id", ""))) in REFERENCE_SELECTOR_TARGET_RPOS
    ]
    if len(matches) == 1:
        return matches[0]
    return None


def proposed_reference_or_selectable_selector(
    row: dict[str, Any],
    side: str,
    registry: dict[str, dict[str, str]],
) -> dict[str, str]:
    reference = registered_reference_for_side(row, side, registry)
    if reference:
        identifier = reference.get("rpo", "") or rpo_from_option_id(reference.get("option_id", ""))
        return {
            "selector_type": "non_selectable_reference",
            "selector_id": reference_selector_id(identifier),
            "registry_reference_id": reference.get("reference_id", ""),
            "projection_policy": reference.get("projection_policy", ""),
        }
    return {
        "selector_type": "selectable",
        "selector_id": row.get(f"{side}_resolved_option_id", "") or row.get(f"{side}_option_id", ""),
        "registry_reference_id": "",
        "projection_policy": "",
    }


def proposed_condition_for_target(row: dict[str, Any], registry: dict[str, dict[str, str]]) -> dict[str, Any]:
    reference = registered_reference_for_side(row, "target", registry)
    target = endpoint_token(row, "target")
    target_slug = selector_slug(target)
    if reference:
        identifier = reference.get("rpo", "") or rpo_from_option_id(reference.get("option_id", ""))
        ref_id = reference_selector_id(identifier)
        condition_set_id = f"cs_ref_selected_{selector_slug(identifier)}"
        return {
            "condition_set": {
                "condition_set_id": condition_set_id,
                "description": f"{identifier} registered non-selectable reference is selected.",
                "status": "future_reference_condition_set",
            },
            "condition_term": {
                "condition_set_id": condition_set_id,
                "or_group": "g1",
                "term_order": "1",
                "term_type": "reference_selected",
                "left_ref": ref_id,
                "operator": "is_true",
                "right_value": "",
                "negate": "false",
                "registry_reference_id": reference.get("reference_id", ""),
            },
        }
    condition_set_id = f"cs_selected_{target_slug}"
    return {
        "condition_set": {
            "condition_set_id": condition_set_id,
            "description": f"{target} selectable is selected.",
            "status": "existing_or_standard_selected_condition_set",
        },
        "condition_term": {
            "condition_set_id": condition_set_id,
            "or_group": "g1",
            "term_order": "1",
            "term_type": "selected",
            "left_ref": row.get("target_resolved_option_id", "") or row.get("target_option_id", ""),
            "operator": "is_true",
            "right_value": "",
            "negate": "false",
            "registry_reference_id": "",
        },
    }


def proposed_rule_id(row: dict[str, Any]) -> str:
    rule_prefix = "req" if row.get("oracle_behavior") == "rule:requires" else "excl"
    source = selector_slug(endpoint_token(row, "source"))
    target = selector_slug(endpoint_token(row, "target"))
    return f"dep_{rule_prefix}_{source}_{target}"


def representation_bucket(row: dict[str, Any]) -> str:
    role = row.get("reference_role", "")
    if role == "both":
        return "both_subject_and_target_reference"
    if role == "source":
        return "subject_reference"
    if role == "target":
        return "target_reference_condition"
    return "ambiguous"


def design_risk_notes(row: dict[str, Any], subject: dict[str, str], condition: dict[str, Any]) -> str:
    notes: list[str] = []
    if subject["selector_type"] == "non_selectable_reference":
        notes.append("requires validator/compiler support for non_selectable_reference subjects")
    if condition["condition_term"]["term_type"] == "reference_selected":
        notes.append("requires validator/compiler support for reference_selected condition terms")
    if row.get("target_rpo", "") in Z51_PACKAGE_RPOS:
        notes.append("target is package-adjacent and would still need scope approval before migration")
    if not row.get("oracle_message", ""):
        notes.append("production message must be re-read during migration implementation")
    return "; ".join(notes) if notes else "no additional ambiguity under Option A"


def build_non_selectable_reference_selector_design_report(args: argparse.Namespace) -> dict[str, Any]:
    preflight = build_registered_reference_selector_preflight_report(args)
    registry = registry_indexes(load_non_selectable_references(Path(args.non_selectable_references)))
    candidates = [
        row
        for row in preflight["rows"]
        if row.get("bucket") == "reference_selector_candidate"
        and set(row.get("registered_reference_involved", [])) <= REFERENCE_SELECTOR_TARGET_RPOS
    ]
    frozen_rows = [
        row
        for row in preflight["rows"]
        if row.get("bucket") == "hidden_rule_only_preserved"
        and set(row.get("registered_reference_involved", [])) <= REFERENCE_SELECTOR_TARGET_RPOS
    ]
    design_rows: list[dict[str, Any]] = []
    for row in candidates:
        subject = proposed_reference_or_selectable_selector(row, "source", registry)
        condition = proposed_condition_for_target(row, registry)
        oracle_rule_type = row.get("oracle_behavior", "").replace("rule:", "")
        dependency_rule = {
            "rule_id": proposed_rule_id(row),
            "rule_type": oracle_rule_type,
            "subject_selector_type": subject["selector_type"],
            "subject_selector_id": subject["selector_id"],
            "subject_must_be_selected": "true",
            "applies_when_condition_set_id": "",
            "target_condition_set_id": condition["condition_set"]["condition_set_id"],
            "violation_behavior": "disable_and_block",
            "message": row.get("oracle_message", ""),
            "priority": "<migration_priority>",
            "active": "true",
        }
        bucket = representation_bucket(row)
        design_rows.append(
            {
                "manifest_row_id": row["manifest_row_id"],
                "record_type": row["record_type"],
                "source_rpo": row["source_rpo"],
                "source_option_id": row["source_option_id"],
                "target_rpo": row["target_rpo"],
                "target_option_id": row["target_option_id"],
                "current_preserved_row": {
                    "manifest_row_id": row["manifest_row_id"],
                    "record_type": row["record_type"],
                    "source": endpoint_token(row, "source"),
                    "source_option_id": row["source_resolved_option_id"],
                    "target": endpoint_token(row, "target"),
                    "target_option_id": row["target_resolved_option_id"],
                    "reason": row["current_preserved_reason"],
                },
                "oracle_behavior": row["oracle_behavior"],
                "oracle_message": row.get("oracle_message", ""),
                "registered_reference_involved": row["registered_reference_involved"],
                "reference_role": row["reference_role"],
                "representation_bucket": bucket,
                "proposed_dependency_rule": dependency_rule,
                "proposed_condition_set": condition["condition_set"],
                "proposed_condition_term": condition["condition_term"],
                "compiler_support_needed": True,
                "validator_support_needed": True,
                "risk_notes": design_risk_notes(row, subject, condition),
            }
        )

    design_rows.sort(
        key=lambda row: (
            row["representation_bucket"],
            row["source_rpo"] or row["source_option_id"] or row["current_preserved_row"]["source"],
            row["target_rpo"] or row["target_option_id"] or row["current_preserved_row"]["target"],
            row["manifest_row_id"],
        )
    )
    representation_counts = Counter(row["representation_bucket"] for row in design_rows)
    ambiguous_count = representation_counts.get("ambiguous", 0)
    has_candidates = len(candidates) > 0
    return {
        "schema_version": 1,
        "status": "allowed",
        "proposed_selector_model": REFERENCE_SELECTOR_MODEL_NAME if has_candidates else "Lane closed - preserve hidden rule-only references",
        "model_decision": (
            "Use dependency_rules.csv with subject_selector_type=non_selectable_reference and condition term_type=reference_selected."
            if has_candidates
            else "No remaining 5VM/5W8/5ZW rows are customer-facing or cutover-blocking; preserve them as hidden rule-only/control-plane rows."
        ),
        "option_a_preferred": has_candidates,
        "option_b_rejected": "Do not reuse selector_type=selectable for registered non-selectable references; it would blur catalog and production-only references.",
        "option_c_rejected": "A separate reference dependency table is not needed unless a future cutover scope requires full hidden rule-only schema completeness.",
        "candidate_row_count": len(candidates),
        "frozen_preserved_row_count": len(frozen_rows),
        "covered_row_count": len(design_rows),
        "ambiguous_row_count": ambiguous_count,
        "representation_summary": {
            "subject_reference_count": representation_counts.get("subject_reference", 0)
            + representation_counts.get("both_subject_and_target_reference", 0),
            "target_reference_condition_count": representation_counts.get("target_reference_condition", 0)
            + representation_counts.get("both_subject_and_target_reference", 0),
            "both_subject_and_target_reference_count": representation_counts.get("both_subject_and_target_reference", 0),
            "ambiguous_count": ambiguous_count,
        },
        "compiler_support_needed": has_candidates,
        "validator_support_needed": has_candidates,
        "data_migration_performed": False,
        "future_implementation_files": REFERENCE_SELECTOR_FUTURE_IMPLEMENTATION_FILES if has_candidates else [],
        "safety_rules": REFERENCE_SELECTOR_SAFETY_RULES,
        "frozen_rows": [
            {
                "manifest_row_id": row["manifest_row_id"],
                "source": endpoint_token(row, "source"),
                "target": endpoint_token(row, "target"),
                "registered_reference_involved": row["registered_reference_involved"],
                "preserved_classification": row["preserved_classification"],
                "freeze_status": row["freeze_status"],
                "rationale": row["rationale"],
            }
            for row in frozen_rows
        ],
        "rows": design_rows,
    }


def recommend_registered_reference_next_pass(
    reference_summary: dict[str, dict[str, Any]],
    bucket_counts: Counter[str],
) -> str:
    selector_candidates = [
        identifier
        for identifier, summary in reference_summary.items()
        if summary["recommended_handling"] == "yes_reference_selector"
    ]
    if selector_candidates:
        return f"LANE F: customer-facing/cutover-blocking non-selectable reference selector work for {', '.join(selector_candidates)}"
    if bucket_counts.get("needs_schema_design", 0):
        return "No registered-reference migration recommended; schema-design rows need explicit customer-facing or cutover approval"
    return "No registered-reference migration recommended; keep hidden references preserved/frozen unless cutover scope changes"
    recommended = recommend_legacy_design_next_lane(subtype_counts)
    return {
        "schema_version": 1,
        "status": "allowed",
        "source_bucket": "legacy_rule_only_or_non_selectable",
        "source_row_count": len(legacy_rows),
        "classified_row_count": len(design_rows),
        "subtype_summary": {subtype: subtype_counts.get(subtype, 0) for subtype in LEGACY_DESIGN_SUBTYPES},
        "recommended_handling_summary": {
            handling: handling_counts.get(handling, 0)
            for handling in RECOMMENDED_HANDLINGS
        },
        "related_surface_summary": {
            surface: related_surface_counts.get(surface, 0)
            for surface in PASS_157_SURFACE_GROUPS
        },
        "identifier_groups": identifier_groups,
        "recommended_next_lane": recommended,
        "rows": design_rows,
    }


def recommend_legacy_design_next_lane(subtype_counts: Counter[str]) -> str:
    if subtype_counts.get("normal_selectable_misclassified", 0):
        return f"LANE A: project normal selectables misclassified as legacy ({subtype_counts['normal_selectable_misclassified']} rows)"
    structured_count = (
        subtype_counts.get("rule_only_legacy_option_id", 0)
        + subtype_counts.get("production_structured_reference", 0)
        + subtype_counts.get("display_only_or_duplicate_reference", 0)
    )
    if structured_count:
        return f"LANE H: add legacy_reference table or structured-reference support ({structured_count} rows)"
    if subtype_counts.get("runtime_generated_placeholder", 0):
        return f"LANE F: compiler support for non-selectable reference emission ({subtype_counts['runtime_generated_placeholder']} rows)"
    ambiguous_count = subtype_counts.get("ambiguous_needs_manual_decision", 0)
    if ambiguous_count:
        return f"LANE G: manual review list only ({ambiguous_count} rows)"
    return "No legacy/non-selectable rows remain."


def recommended_next_lane(bucket_summary: dict[str, int]) -> str:
    for bucket in ["ready_plain_exclude", "ready_requires", "ready_include_zero_auto_add"]:
        if bucket_summary.get(bucket, 0):
            return LANES_BY_BUCKET[bucket]
    non_empty = [(count, bucket) for bucket, count in bucket_summary.items() if count]
    if not non_empty:
        return "No active preserved rows remain."
    count, bucket = max(non_empty, key=lambda item: (item[0], -BUCKETS.index(item[1])))
    return f"{LANES_BY_BUCKET[bucket]} ({count} rows)"


def print_text(report: dict[str, Any]) -> None:
    print(f"Remaining active preserved_cross_boundary rows: {report['active_preserved_cross_boundary_count']}")
    print()
    for bucket in BUCKETS:
        print(f"{bucket}: {report['bucket_summary'][bucket]}")
    print()
    print(f"Recommended next migration lane: {report['recommended_next_lane']}")
    print()
    print("record_type source target bucket recommended next lane reason")
    for row in report["rows"]:
        source = row["source_rpo"] or row["source_option_id"] or row["source_resolved_option_id"]
        target = row["target_rpo"] or row["target_option_id"] or row["target_resolved_option_id"]
        print(
            f"{row['record_type']} {source} {target} {row['bucket']} "
            f"{row['recommended_next_lane']} {row['reason']}"
        )


def print_legacy_nonselectable_design_text(report: dict[str, Any]) -> None:
    print(f"Legacy/non-selectable preserved rows: {report['source_row_count']}")
    print()
    for subtype in LEGACY_DESIGN_SUBTYPES:
        print(f"{subtype}: {report['subtype_summary'][subtype]}")
    print()
    print("Recommended handling summary:")
    for handling in RECOMMENDED_HANDLINGS:
        print(f"{handling}: {report['recommended_handling_summary'][handling]}")
    print()
    print("Identifier groups:")
    for identifier in LEGACY_IDENTIFIER_GROUPS:
        print(f"{identifier}: {report['identifier_groups'][identifier]['count']}")
    print()
    print(f"Recommended next action: {report['recommended_next_lane']}")
    print()
    print("record_type source target subtype handling next lane oracle behavior")
    for row in report["rows"]:
        source = row["source_rpo"] or row["source_option_id"] or row["source_resolved_option_id"]
        target = row["target_rpo"] or row["target_option_id"] or row["target_resolved_option_id"]
        print(
            f"{row['record_type']} {source} {target} {row['subtype']} "
            f"{row['recommended_handling']} {row['recommended_next_lane']} {row['oracle_behavior']}"
        )


def print_registered_reference_selector_preflight_text(report: dict[str, Any]) -> None:
    print(f"Registered-reference preserved rows inspected: {report['inspected_row_count']}")
    print()
    for bucket in REGISTERED_REFERENCE_PREFLIGHT_BUCKETS:
        print(f"{bucket}: {report['bucket_summary'][bucket]}")
    print()
    print(
        "Can migrate without customer-selectable projection: "
        f"{str(report['can_any_reference_migrate_without_customer_selectable_projection']).lower()}"
    )
    print(f"Compiler/schema support required: {str(report['compiler_schema_support_required']).lower()}")
    print(f"Recommended next pass: {report['recommended_next_pass']}")
    print()
    print("reference rows decision classification freeze status")
    for identifier, summary in report["reference_summary"].items():
        print(
            f"{identifier} {summary['row_count']} {summary['recommended_handling']} "
            f"{'|'.join(summary['preserved_classification'])} "
            f"{'|'.join(summary['freeze_status'])}"
        )
    print()
    print("record_type source target reference role bucket classification freeze status")
    for row in report["rows"]:
        source = row["source_rpo"] or row["source_option_id"] or row["source_resolved_option_id"]
        target = row["target_rpo"] or row["target_option_id"] or row["target_resolved_option_id"]
        references = "|".join(row["registered_reference_involved"])
        print(
            f"{row['record_type']} {source} {target} {references} {row['reference_role']} "
            f"{row['bucket']} {row['preserved_classification']} {row['freeze_status']}"
        )


def print_non_selectable_reference_selector_design_text(report: dict[str, Any]) -> None:
    print(f"Non-selectable reference selector design candidates: {report['candidate_row_count']}")
    print(f"Frozen hidden rule-only preserved rows: {report['frozen_preserved_row_count']}")
    print(f"Proposed selector model: {report['proposed_selector_model']}")
    print(f"Covered rows: {report['covered_row_count']}")
    print(f"Ambiguous rows: {report['ambiguous_row_count']}")
    print(f"Model decision: {report['model_decision']}")
    print()
    print("Representation summary:")
    for key, value in report["representation_summary"].items():
        print(f"{key}: {value}")
    print()
    print("Safety rules:")
    for index, rule in enumerate(report["safety_rules"], start=1):
        print(f"{index}. {rule}")
    print()
    print("Future implementation files:")
    if report["future_implementation_files"]:
        for path in report["future_implementation_files"]:
            print(path)
    else:
        print("none")
    print()
    if report["frozen_rows"]:
        print("Frozen rows:")
        print("source target reference classification freeze status")
        for row in report["frozen_rows"]:
            references = "|".join(row["registered_reference_involved"])
            print(
                f"{row['source']} {row['target']} {references} "
                f"{row['preserved_classification']} {row['freeze_status']}"
            )
    print()
    print("record_type source target rule_id subject_selector target_condition risk notes")
    for row in report["rows"]:
        preserved = row["current_preserved_row"]
        dependency = row["proposed_dependency_rule"]
        subject = f"{dependency['subject_selector_type']}:{dependency['subject_selector_id']}"
        print(
            f"{row['record_type']} {preserved['source']} {preserved['target']} "
            f"{dependency['rule_id']} {subject} {dependency['target_condition_set_id']} "
            f"{row['risk_notes']}"
        )


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="Write the full report as JSON to stdout.")
    parser.add_argument(
        "--legacy-nonselectable-design",
        action="store_true",
        help="Write the Pass 157 legacy/non-selectable design report as text.",
    )
    parser.add_argument(
        "--legacy-nonselectable-design-json",
        action="store_true",
        help="Write the Pass 157 legacy/non-selectable design report as JSON.",
    )
    parser.add_argument(
        "--registered-reference-selector-preflight",
        action="store_true",
        help="Write the Pass 159 registered-reference selector preflight as text.",
    )
    parser.add_argument(
        "--registered-reference-selector-preflight-json",
        action="store_true",
        help="Write the Pass 159 registered-reference selector preflight as JSON.",
    )
    parser.add_argument(
        "--non-selectable-reference-selector-design",
        action="store_true",
        help="Write the Pass 160 non-selectable reference selector design report as text.",
    )
    parser.add_argument(
        "--non-selectable-reference-selector-design-json",
        action="store_true",
        help="Write the Pass 160 non-selectable reference selector design report as JSON.",
    )
    parser.add_argument("--package", default=str(DEFAULT_PACKAGE), help="Stingray CSV package directory.")
    parser.add_argument("--production-data", default=str(DEFAULT_PRODUCTION_DATA), help="Production form-app/data.js oracle path.")
    parser.add_argument("--ownership-manifest", default=str(DEFAULT_OWNERSHIP_MANIFEST), help="Projected slice ownership manifest path.")
    parser.add_argument(
        "--non-selectable-references",
        default=str(DEFAULT_NON_SELECTABLE_REFERENCES),
        help="Non-selectable reference registry path.",
    )
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    try:
        if args.non_selectable_reference_selector_design or args.non_selectable_reference_selector_design_json:
            report = build_non_selectable_reference_selector_design_report(args)
        elif args.registered_reference_selector_preflight or args.registered_reference_selector_preflight_json:
            report = build_registered_reference_selector_preflight_report(args)
        elif args.legacy_nonselectable_design or args.legacy_nonselectable_design_json:
            report = build_legacy_nonselectable_design_report(args)
        else:
            report = build_report(args)
    except QueueError as error:
        print(str(error), file=sys.stderr)
        return 1
    if args.non_selectable_reference_selector_design_json:
        print(json.dumps(report, indent=2, sort_keys=True))
    elif args.non_selectable_reference_selector_design:
        print_non_selectable_reference_selector_design_text(report)
    elif args.registered_reference_selector_preflight_json:
        print(json.dumps(report, indent=2, sort_keys=True))
    elif args.registered_reference_selector_preflight:
        print_registered_reference_selector_preflight_text(report)
    elif args.legacy_nonselectable_design_json:
        print(json.dumps(report, indent=2, sort_keys=True))
    elif args.legacy_nonselectable_design:
        print_legacy_nonselectable_design_text(report)
    elif args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print_text(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
