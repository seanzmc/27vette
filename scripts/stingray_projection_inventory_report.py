#!/usr/bin/env python3
"""Write production-to-CSV projection inventory artifacts for Stingray."""

from __future__ import annotations

import argparse
import csv
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from stingray_csv_first_slice import CsvSlice


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PACKAGE = ROOT / "data" / "stingray"
DEFAULT_PRODUCTION_DATA = ROOT / "form-app" / "data.js"
DEFAULT_OWNERSHIP_MANIFEST = DEFAULT_PACKAGE / "validation" / "projected_slice_ownership.csv"

SELECTABLE_FIELDS = [
    "option_id",
    "rpo",
    "label",
    "description",
    "section_id",
    "section_name",
    "category_id",
    "category_name",
    "step_key",
    "choice_mode",
    "selection_mode",
    "display_order",
    "base_price",
    "variant_count",
    "available_variant_ids",
    "statuses",
    "is_customer_facing",
    "is_csv_projected",
    "projection_status",
    "notes",
]

RELATIONSHIP_FIELDS = [
    "relationship_key",
    "surface",
    "production_id",
    "relationship_type",
    "source_id",
    "source_rpo",
    "source_label",
    "source_section",
    "source_mode",
    "target_id",
    "target_rpo",
    "target_label",
    "target_section",
    "target_mode",
    "runtime_action",
    "auto_add",
    "message",
    "price_rule_type",
    "price_value",
    "group_id",
    "group_type",
    "member_order",
    "endpoint_classification",
]

MATRIX_FIELDS = [
    "relationship_key",
    "production_surface",
    "csv_surface",
    "production_status",
    "csv_status",
    "ownership_status",
    "source_projection_status",
    "target_projection_status",
    "representable_now",
    "requires_new_selectable",
    "requires_support_change",
    "recommended_lane",
    "hard_stop_reason",
    "next_action",
]


class InventoryError(RuntimeError):
    pass


def load_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, Any]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fieldnames})


def load_production_data(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    match = re.search(
        r"window\.CORVETTE_FORM_DATA\s*=\s*(\{.*\})\s*;\s*window\.STINGRAY_FORM_DATA\s*=",
        text,
        re.DOTALL,
    )
    if not match:
        raise InventoryError(f"Could not locate window.CORVETTE_FORM_DATA assignment in {path}.")
    registry = json.loads(match.group(1))
    try:
        return registry["models"]["stingray"]["data"]
    except KeyError as exc:
        raise InventoryError(f"Could not locate models.stingray.data in {path}.") from exc


def truthy(value: str) -> bool:
    return str(value).lower() == "true"


def count_by(rows: list[dict[str, Any]], field: str) -> dict[str, int]:
    return dict(sorted(Counter(str(row.get(field, "")) for row in rows).items()))


def unique_join(values: list[Any]) -> str:
    return "|".join(sorted({str(value) for value in values if value not in ("", None)}))


def option_id_for_rpo(choices_by_option: dict[str, dict[str, Any]], rpo: str) -> str:
    matches = sorted(option_id for option_id, row in choices_by_option.items() if row.get("rpo") == rpo)
    return matches[0] if matches else ""


def relationship_rule_key(rule: dict[str, Any]) -> str:
    return "|".join(
        [
            "rule",
            str(rule.get("source_id", "")),
            str(rule.get("target_id", "")),
            str(rule.get("rule_type", "")),
            str(rule.get("runtime_action", "")),
            str(rule.get("auto_add", "")),
        ]
    )


def relationship_price_rule_key(rule: dict[str, Any]) -> str:
    return "|".join(
        [
            "priceRule",
            str(rule.get("condition_option_id", "")),
            str(rule.get("target_option_id", "")),
            str(rule.get("price_rule_type", "")),
            str(int(rule.get("price_value") or 0)),
        ]
    )


def exclusive_member_key(group_id: str, option_id: str) -> str:
    return f"exclusiveGroup|{group_id}|{option_id}"


def rule_group_member_key(group_id: str, source_id: str, target_id: str, member_order: int) -> str:
    return f"ruleGroup|{group_id}|{source_id}|{target_id}|{member_order}"


def ownership_scope(
    ownership_rows: list[dict[str, str]], choices_by_option: dict[str, dict[str, Any]]
) -> dict[str, Any]:
    active = [row for row in ownership_rows if row.get("active") == "true"]
    projected_rpos = {
        row["rpo"]
        for row in active
        if row.get("record_type") == "selectable" and row.get("ownership") == "projected_owned" and row.get("rpo")
    }
    guarded_rpos = {
        row["rpo"]
        for row in active
        if row.get("record_type") == "guardedOption" and row.get("ownership") == "production_guarded" and row.get("rpo")
    }
    guarded_ids = {
        row["target_option_id"]
        for row in active
        if row.get("record_type") == "guardedOption" and row.get("ownership") == "production_guarded" and row.get("target_option_id")
    }
    preserved_pairs: set[tuple[str, str, str]] = set()
    preserved_rows_by_pair: dict[tuple[str, str, str], dict[str, str]] = {}
    for row in active:
        if row.get("ownership") != "preserved_cross_boundary":
            continue
        source_id = row.get("source_option_id") or option_id_for_rpo(choices_by_option, row.get("source_rpo", ""))
        target_id = row.get("target_option_id") or option_id_for_rpo(choices_by_option, row.get("target_rpo", ""))
        if not source_id or not target_id:
            continue
        key = (row.get("record_type", ""), source_id, target_id)
        preserved_pairs.add(key)
        preserved_rows_by_pair[key] = row
    return {
        "projected_rpos": projected_rpos,
        "guarded_rpos": guarded_rpos,
        "guarded_ids": guarded_ids,
        "preserved_pairs": preserved_pairs,
        "preserved_rows_by_pair": preserved_rows_by_pair,
    }


def customer_choice_inventory(data: dict[str, Any], projected_rpos: set[str]) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for choice in data["choices"]:
        if choice.get("active") == "True" and choice.get("selectable") == "True":
            grouped[choice["option_id"]].append(choice)

    rows: list[dict[str, Any]] = []
    representative: dict[str, dict[str, Any]] = {}
    for option_id, choices in sorted(grouped.items()):
        choices = sorted(choices, key=lambda row: row["variant_id"])
        base = choices[0]
        representative[option_id] = base
        projected = base["rpo"] in projected_rpos
        rows.append(
            {
                "option_id": option_id,
                "rpo": base.get("rpo", ""),
                "label": base.get("label", ""),
                "description": base.get("description", ""),
                "section_id": base.get("section_id", ""),
                "section_name": base.get("section_name", ""),
                "category_id": base.get("category_id", ""),
                "category_name": base.get("category_name", ""),
                "step_key": base.get("step_key", ""),
                "choice_mode": base.get("choice_mode", ""),
                "selection_mode": base.get("selection_mode", ""),
                "display_order": base.get("display_order", ""),
                "base_price": base.get("base_price", ""),
                "variant_count": len(choices),
                "available_variant_ids": unique_join([row.get("variant_id", "") for row in choices if row.get("status") == "available"]),
                "statuses": unique_join([row.get("status", "") for row in choices]),
                "is_customer_facing": "true",
                "is_csv_projected": str(projected).lower(),
                "projection_status": "customer-facing projected" if projected else "customer-facing missing",
                "notes": "",
            }
        )
    return rows, representative


def choice_lookup(data: dict[str, Any]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for choice in data["choices"]:
        result.setdefault(choice["option_id"], choice)
    return result


def interior_ids(data: dict[str, Any]) -> set[str]:
    ids: set[str] = set()
    for row in data.get("interiors", []):
        for field in ("interior_id", "id", "source_id"):
            if row.get(field):
                ids.add(str(row[field]))
    return ids


def endpoint_projection_status(
    option_id: str,
    choices_by_option: dict[str, dict[str, Any]],
    customer_choices_by_option: dict[str, dict[str, Any]],
    interiors: set[str],
    scope: dict[str, Any],
) -> str:
    choice = choices_by_option.get(option_id)
    if choice:
        rpo = choice.get("rpo", "")
        if rpo in scope["projected_rpos"]:
            return "customer-facing projected"
        if option_id in customer_choices_by_option:
            return "customer-facing missing"
        if rpo in scope["guarded_rpos"] or option_id in scope["guarded_ids"]:
            return "hidden/control-plane"
        return "hidden/control-plane"
    if option_id in interiors:
        return "runtime-only/structured reference"
    if option_id in scope["guarded_ids"]:
        return "hidden/control-plane"
    return "runtime-only/structured reference"


def endpoint_metadata(option_id: str, choices_by_option: dict[str, dict[str, Any]]) -> dict[str, str]:
    row = choices_by_option.get(option_id, {})
    return {
        "id": option_id,
        "rpo": str(row.get("rpo", option_id if option_id and not row else "")),
        "label": str(row.get("label", "")),
        "section": str(row.get("section_id", "")),
        "mode": str(row.get("selection_mode", "")),
    }


def relationship_lane(row: dict[str, Any]) -> str:
    surface = row["surface"]
    if surface == "priceRules":
        return "price override"
    if surface in {"exclusiveGroups", "ruleGroups"}:
        return "group behavior"
    if row.get("runtime_action") == "replace":
        return "replacement/default behavior"
    if row.get("relationship_type") == "includes" and row.get("auto_add") == "True":
        return "package include"
    if "runtime-only/structured reference" in row["endpoint_classification"] or "hidden/control-plane" in row["endpoint_classification"]:
        return "hidden/control-plane"
    return "simple dependency"


def relationship_rows(data: dict[str, Any], scope: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, str]]:
    choices_by_option = choice_lookup(data)
    _selectable_rows, customer_by_option = customer_choice_inventory(data, scope["projected_rpos"])
    interiors = interior_ids(data)
    rows: list[dict[str, Any]] = []
    key_to_surface: dict[str, str] = {}

    def side_status(option_id: str) -> str:
        return endpoint_projection_status(option_id, choices_by_option, customer_by_option, interiors, scope)

    def add_row(row: dict[str, Any]) -> None:
        row["endpoint_classification"] = f"{row.get('source_projection_status', '')}->{row.get('target_projection_status', '')}"
        rows.append(row)

    for rule in data["rules"]:
        source = endpoint_metadata(rule["source_id"], choices_by_option)
        target = endpoint_metadata(rule["target_id"], choices_by_option)
        key = relationship_rule_key(rule)
        key_to_surface[key] = "rules"
        add_row(
            {
                "relationship_key": key,
                "surface": "rules",
                "production_id": rule.get("rule_id", key),
                "relationship_type": rule.get("rule_type", ""),
                "source_id": rule.get("source_id", ""),
                "source_rpo": source["rpo"],
                "source_label": source["label"],
                "source_section": rule.get("source_section") or source["section"],
                "source_mode": rule.get("source_selection_mode") or source["mode"],
                "target_id": rule.get("target_id", ""),
                "target_rpo": target["rpo"],
                "target_label": target["label"],
                "target_section": rule.get("target_section") or target["section"],
                "target_mode": rule.get("target_selection_mode") or target["mode"],
                "runtime_action": rule.get("runtime_action", ""),
                "auto_add": rule.get("auto_add", ""),
                "message": rule.get("disabled_reason", ""),
                "price_rule_type": "",
                "price_value": "",
                "group_id": "",
                "group_type": "",
                "member_order": "",
                "source_projection_status": side_status(rule["source_id"]),
                "target_projection_status": side_status(rule["target_id"]),
            }
        )

    for price_rule in data["priceRules"]:
        source = endpoint_metadata(price_rule["condition_option_id"], choices_by_option)
        target = endpoint_metadata(price_rule["target_option_id"], choices_by_option)
        key = relationship_price_rule_key(price_rule)
        key_to_surface[key] = "priceRules"
        add_row(
            {
                "relationship_key": key,
                "surface": "priceRules",
                "production_id": price_rule.get("price_rule_id", key),
                "relationship_type": "priceRule",
                "source_id": price_rule.get("condition_option_id", ""),
                "source_rpo": source["rpo"],
                "source_label": source["label"],
                "source_section": source["section"],
                "source_mode": source["mode"],
                "target_id": price_rule.get("target_option_id", ""),
                "target_rpo": target["rpo"],
                "target_label": target["label"],
                "target_section": target["section"],
                "target_mode": target["mode"],
                "runtime_action": "",
                "auto_add": "",
                "message": price_rule.get("notes", ""),
                "price_rule_type": price_rule.get("price_rule_type", ""),
                "price_value": int(price_rule.get("price_value") or 0),
                "group_id": "",
                "group_type": "",
                "member_order": "",
                "source_projection_status": side_status(price_rule["condition_option_id"]),
                "target_projection_status": side_status(price_rule["target_option_id"]),
            }
        )

    for group in data.get("exclusiveGroups", []):
        for order, option_id in enumerate(group.get("option_ids", []), start=1):
            target = endpoint_metadata(option_id, choices_by_option)
            key = exclusive_member_key(group["group_id"], option_id)
            key_to_surface[key] = "exclusiveGroups"
            add_row(
                {
                    "relationship_key": key,
                    "surface": "exclusiveGroups",
                    "production_id": group["group_id"],
                    "relationship_type": "exclusive_group_member",
                    "source_id": group["group_id"],
                    "source_rpo": "",
                    "source_label": group.get("notes", ""),
                    "source_section": "",
                    "source_mode": group.get("selection_mode", ""),
                    "target_id": option_id,
                    "target_rpo": target["rpo"],
                    "target_label": target["label"],
                    "target_section": target["section"],
                    "target_mode": target["mode"],
                    "runtime_action": "",
                    "auto_add": "",
                    "message": group.get("notes", ""),
                    "price_rule_type": "",
                    "price_value": "",
                    "group_id": group["group_id"],
                    "group_type": "exclusive",
                    "member_order": order,
                    "source_projection_status": "hidden/control-plane",
                    "target_projection_status": side_status(option_id),
                }
            )

    for group in data.get("ruleGroups", []):
        for order, target_id in enumerate(group.get("target_ids", []), start=1):
            source = endpoint_metadata(group["source_id"], choices_by_option)
            target = endpoint_metadata(target_id, choices_by_option)
            key = rule_group_member_key(group["group_id"], group["source_id"], target_id, order)
            key_to_surface[key] = "ruleGroups"
            add_row(
                {
                    "relationship_key": key,
                    "surface": "ruleGroups",
                    "production_id": group["group_id"],
                    "relationship_type": group.get("group_type", ""),
                    "source_id": group.get("source_id", ""),
                    "source_rpo": source["rpo"],
                    "source_label": source["label"],
                    "source_section": source["section"],
                    "source_mode": source["mode"],
                    "target_id": target_id,
                    "target_rpo": target["rpo"],
                    "target_label": target["label"],
                    "target_section": target["section"],
                    "target_mode": target["mode"],
                    "runtime_action": "",
                    "auto_add": "",
                    "message": group.get("disabled_reason", ""),
                    "price_rule_type": "",
                    "price_value": "",
                    "group_id": group["group_id"],
                    "group_type": group.get("group_type", ""),
                    "member_order": order,
                    "source_projection_status": side_status(group["source_id"]),
                    "target_projection_status": side_status(target_id),
                }
            )

    rows.sort(key=lambda row: row["relationship_key"])
    return rows, key_to_surface


def fragment_owned_keys(fragment: dict[str, Any]) -> set[str]:
    keys = {relationship_rule_key(row) for row in fragment.get("rules", [])}
    keys.update(relationship_price_rule_key(row) for row in fragment.get("priceRules", []))
    for group in fragment.get("exclusiveGroups", []):
        for option_id in group.get("option_ids", []):
            keys.add(exclusive_member_key(group["group_id"], option_id))
    for group in fragment.get("ruleGroups", []):
        for order, target_id in enumerate(group.get("target_ids", []), start=1):
            keys.add(rule_group_member_key(group["group_id"], group["source_id"], target_id, order))
    return keys


def preserved_relationship_keys(relationship_rows_: list[dict[str, Any]], scope: dict[str, Any]) -> set[str]:
    keys: set[str] = set()
    preserved_pairs = scope["preserved_pairs"]
    for row in relationship_rows_:
        if row["surface"] == "rules" and ("rule", row["source_id"], row["target_id"]) in preserved_pairs:
            keys.add(row["relationship_key"])
        if row["surface"] == "priceRules" and ("priceRule", row["source_id"], row["target_id"]) in preserved_pairs:
            keys.add(row["relationship_key"])
    return keys


def matrix_rows(relationships: list[dict[str, Any]], fragment: dict[str, Any], scope: dict[str, Any]) -> list[dict[str, Any]]:
    csv_owned = fragment_owned_keys(fragment)
    preserved = preserved_relationship_keys(relationships, scope)
    rows: list[dict[str, Any]] = []
    for rel in relationships:
        is_csv_owned = rel["relationship_key"] in csv_owned
        is_preserved = rel["relationship_key"] in preserved
        source_status = rel.get("source_projection_status", "")
        target_status = rel.get("target_projection_status", "")
        lane = relationship_lane(rel)
        requires_new_selectable = "customer-facing missing" in {source_status, target_status}
        requires_support_change = lane in {"replacement/default behavior", "hidden/control-plane"} or (
            rel["surface"] == "priceRules" and not is_csv_owned
        )
        representable_now = (
            not requires_new_selectable
            and not requires_support_change
            and "customer-facing projected" in {source_status, target_status}
        )
        if is_csv_owned:
            csv_status = "CSV-owned relationship"
            ownership_status = "CSV-owned relationship"
            next_action = "keep CSV-owned"
            hard_stop = ""
        elif is_preserved:
            csv_status = "active preserved relationship"
            ownership_status = "active preserved relationship"
            next_action = "keep preserved until lane is approved"
            hard_stop = ""
        else:
            csv_status = "outside projected boundary"
            ownership_status = "outside projected boundary"
            next_action = "inventory before migration"
            hard_stop = "requires new selectable projection first" if requires_new_selectable else ""
        if requires_support_change and not is_csv_owned:
            hard_stop = hard_stop or "requires support design"
        rows.append(
            {
                "relationship_key": rel["relationship_key"],
                "production_surface": rel["surface"],
                "csv_surface": rel["surface"] if is_csv_owned else "",
                "production_status": "active",
                "csv_status": csv_status,
                "ownership_status": ownership_status,
                "source_projection_status": source_status,
                "target_projection_status": target_status,
                "representable_now": str(representable_now).lower(),
                "requires_new_selectable": str(requires_new_selectable).lower(),
                "requires_support_change": str(requires_support_change).lower(),
                "recommended_lane": lane,
                "hard_stop_reason": hard_stop,
                "next_action": next_action,
            }
        )
    rows.sort(key=lambda row: row["relationship_key"])
    return rows


def summary(
    selectable_rows: list[dict[str, Any]],
    relationships: list[dict[str, Any]],
    matrix: list[dict[str, Any]],
    data: dict[str, Any],
    package_dir: Path,
) -> dict[str, Any]:
    condition_sets = load_csv(package_dir / "logic" / "condition_sets.csv")
    condition_terms = load_csv(package_dir / "logic" / "condition_terms.csv")
    dependency_rules = [row for row in load_csv(package_dir / "logic" / "dependency_rules.csv") if truthy(row.get("active", ""))]
    term_groups: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in condition_terms:
        term_groups[row["condition_set_id"]].append(row)
    single_term_sets = {condition_set_id for condition_set_id, rows in term_groups.items() if len(rows) == 1}
    return {
        "schema_version": 1,
        "production_selectables": {
            "customer_facing_count": len(selectable_rows),
            "csv_projected_customer_facing_count": sum(1 for row in selectable_rows if row["projection_status"] == "customer-facing projected"),
            "customer_facing_missing_count": sum(1 for row in selectable_rows if row["projection_status"] == "customer-facing missing"),
        },
        "production_relationships": {
            "rules": {
                "total": len(data.get("rules", [])),
                "by_rule_type": count_by(data.get("rules", []), "rule_type"),
                "by_runtime_action": count_by(data.get("rules", []), "runtime_action"),
                "by_auto_add": count_by(data.get("rules", []), "auto_add"),
            },
            "price_rules": {"total": len(data.get("priceRules", []))},
            "exclusive_groups": {"total": len(data.get("exclusiveGroups", []))},
            "rule_groups": {"total": len(data.get("ruleGroups", []))},
        },
        "csv_projection": {
            "csv_owned_relationship_count": sum(1 for row in matrix if row["csv_status"] == "CSV-owned relationship"),
            "active_preserved_relationship_count": sum(1 for row in matrix if row["ownership_status"] == "active preserved relationship"),
            "outside_projected_boundary_count": sum(1 for row in matrix if row["csv_status"] == "outside projected boundary"),
            "by_recommended_lane": count_by(matrix, "recommended_lane"),
            "by_next_action": count_by(matrix, "next_action"),
        },
        "condition_boilerplate": {
            "condition_sets": len(condition_sets),
            "condition_terms": len(condition_terms),
            "single_term_condition_sets": len(single_term_sets),
            "simple_selected_terms": sum(
                1
                for row in condition_terms
                if row.get("term_type") == "selected" and row.get("operator") == "is_true" and row.get("negate") == "false"
            ),
            "active_dependency_rules": len(dependency_rules),
            "dependency_rules_using_single_term_target_condition": sum(
                1 for row in dependency_rules if row.get("target_condition_set_id", "") in single_term_sets
            ),
        },
        "csv_table_recommendation": {
            "human_authored_source_of_truth": [
                "catalog/selectables.csv",
                "ui/selectable_display.csv",
                "pricing/base_prices.csv",
                "logic/auto_adds.csv",
                "logic/dependency_rules.csv",
                "logic/rule_groups.csv",
                "logic/rule_group_members.csv",
                "logic/exclusive_groups.csv",
                "logic/exclusive_group_members.csv",
                "validation/projected_slice_ownership.csv",
                "validation/non_selectable_references.csv",
            ],
            "compiler_intermediate_or_candidate_generated": [
                "logic/condition_sets.csv",
                "logic/condition_terms.csv",
            ],
        },
    }


def build_report(args: argparse.Namespace) -> dict[str, Any]:
    package_dir = Path(args.package)
    data = load_production_data(Path(args.production_data))
    ownership_rows = load_csv(Path(args.ownership_manifest))
    initial_choices = choice_lookup(data)
    scope = ownership_scope(ownership_rows, initial_choices)
    selectable_rows, _customer_by_option = customer_choice_inventory(data, scope["projected_rpos"])
    relationships, _surfaces = relationship_rows(data, scope)
    fragment = CsvSlice(package_dir).legacy_fragment()
    matrix = matrix_rows(relationships, fragment, scope)
    return {
        "selectables": selectable_rows,
        "relationships": relationships,
        "matrix": matrix,
        "summary": summary(selectable_rows, relationships, matrix, data, package_dir),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--production-data", default=str(DEFAULT_PRODUCTION_DATA))
    parser.add_argument("--package", default=str(DEFAULT_PACKAGE))
    parser.add_argument("--ownership-manifest", default=str(DEFAULT_OWNERSHIP_MANIFEST))
    parser.add_argument("--out-dir", required=True)
    args = parser.parse_args()

    try:
        report = build_report(args)
        out_dir = Path(args.out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        write_csv(out_dir / "production_selectable_inventory.csv", SELECTABLE_FIELDS, report["selectables"])
        write_csv(out_dir / "production_relationship_inventory.csv", RELATIONSHIP_FIELDS, report["relationships"])
        write_csv(out_dir / "csv_projection_matrix.csv", MATRIX_FIELDS, report["matrix"])
        (out_dir / "projection_summary.json").write_text(
            json.dumps(report["summary"], indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        print(f"wrote projection inventory artifacts to {out_dir}")
    except InventoryError as exc:
        raise SystemExit(f"projection inventory failed: {exc}") from exc


if __name__ == "__main__":
    main()
