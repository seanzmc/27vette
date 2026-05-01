#!/usr/bin/env python3
"""Evaluate the first Stingray CSV migration slice without touching production generation."""

from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PACKAGE = ROOT / "data" / "stingray"


TABLES = {
    "variants": "catalog/variants.csv",
    "selectables": "catalog/selectables.csv",
    "item_sets": "catalog/item_sets.csv",
    "item_set_members": "catalog/item_set_members.csv",
    "condition_sets": "logic/condition_sets.csv",
    "condition_terms": "logic/condition_terms.csv",
    "auto_adds": "logic/auto_adds.csv",
    "dependency_rules": "logic/dependency_rules.csv",
    "exclusive_groups": "logic/exclusive_groups.csv",
    "exclusive_group_members": "logic/exclusive_group_members.csv",
    "price_books": "pricing/price_books.csv",
    "base_prices": "pricing/base_prices.csv",
    "price_policies": "pricing/price_policies.csv",
    "price_rules": "pricing/price_rules.csv",
}


ID_FIELDS = {
    "variants": "variant_id",
    "selectables": "selectable_id",
    "item_sets": "set_id",
    "condition_sets": "condition_set_id",
    "auto_adds": "auto_add_id",
    "dependency_rules": "rule_id",
    "exclusive_groups": "exclusive_group_id",
    "price_books": "price_book_id",
    "base_prices": "base_price_id",
    "price_policies": "price_policy_id",
    "price_rules": "price_rule_id",
}


def load_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def is_active(row: dict[str, str]) -> bool:
    return row.get("active", "").lower() == "true"


def as_bool(value: str) -> bool:
    return value.lower() == "true"


def as_int(value: str, default: int = 0) -> int:
    if value == "":
        return default
    return int(value)


class CsvSlice:
    def __init__(self, package_dir: Path) -> None:
        self.package_dir = package_dir
        self.tables = {name: load_csv(package_dir / relative_path) for name, relative_path in TABLES.items()}
        self.variants = {row["variant_id"]: row for row in self.tables["variants"] if is_active(row)}
        self.selectables = {row["selectable_id"]: row for row in self.tables["selectables"] if is_active(row)}
        self.item_sets = {row["set_id"]: row for row in self.tables["item_sets"] if is_active(row)}
        self.condition_sets = {row["condition_set_id"]: row for row in self.tables["condition_sets"] if is_active(row)}
        self.price_policies = {row["price_policy_id"]: row for row in self.tables["price_policies"]}
        self.item_set_members = self._build_item_set_members()
        self.condition_terms = self._build_condition_terms()
        self.exclusive_members = self._build_exclusive_members()
        self.exclusive_groups_by_member = self._build_exclusive_groups_by_member()

    def _build_item_set_members(self) -> dict[str, list[str]]:
        members: dict[str, list[str]] = defaultdict(list)
        for row in self.tables["item_set_members"]:
            if is_active(row):
                members[row["set_id"]].append(row["member_selectable_id"])
        return dict(members)

    def _build_condition_terms(self) -> dict[str, list[dict[str, str]]]:
        terms: dict[str, list[dict[str, str]]] = defaultdict(list)
        for row in self.tables["condition_terms"]:
            terms[row["condition_set_id"]].append(row)
        for rows in terms.values():
            rows.sort(key=lambda item: (item["or_group"], as_int(item["term_order"])))
        return dict(terms)

    def _build_exclusive_members(self) -> dict[str, list[str]]:
        members: dict[str, list[str]] = defaultdict(list)
        for row in self.tables["exclusive_group_members"]:
            if is_active(row):
                members[row["exclusive_group_id"]].append(row["member_selectable_id"])
        return dict(members)

    def _build_exclusive_groups_by_member(self) -> dict[str, list[str]]:
        groups: dict[str, list[str]] = defaultdict(list)
        for group_id, members in self.exclusive_members.items():
            for member_id in members:
                groups[member_id].append(group_id)
        return dict(groups)

    def validate(self) -> list[str]:
        errors: list[str] = []
        for table_name, id_field in ID_FIELDS.items():
            seen: set[str] = set()
            for row in self.tables[table_name]:
                row_id = row.get(id_field, "")
                if not row_id:
                    errors.append(f"{table_name} has a row missing {id_field}.")
                elif row_id in seen:
                    errors.append(f"{table_name} has duplicate {id_field}: {row_id}.")
                seen.add(row_id)

        for set_id, members in self.item_set_members.items():
            if set_id not in self.item_sets:
                errors.append(f"item_set_members references missing set_id: {set_id}.")
            if not members:
                errors.append(f"item set has no active members: {set_id}.")
            for member_id in members:
                if member_id not in self.selectables:
                    errors.append(f"item_set_members references missing selectable: {member_id}.")

        for row in self.tables["condition_terms"]:
            condition_set_id = row["condition_set_id"]
            if condition_set_id not in self.condition_sets:
                errors.append(f"condition_terms references missing condition_set_id: {condition_set_id}.")
            term_type = row["term_type"]
            left_ref = row["left_ref"]
            if term_type == "selected" and left_ref not in self.selectables:
                errors.append(f"condition term references missing selectable: {left_ref}.")
            if term_type == "selected_any_in_set" and left_ref not in self.item_sets:
                errors.append(f"condition term references missing item set: {left_ref}.")

        for row in self.tables["auto_adds"]:
            if not is_active(row):
                continue
            self._validate_selector(errors, "auto_adds", row["source_selector_type"], row["source_selector_id"])
            self._validate_condition_ref(errors, "auto_adds", row.get("trigger_condition_set_id", ""))
            self._validate_condition_ref(errors, "auto_adds", row.get("scope_condition_set_id", ""))
            self._validate_selectable_ref(errors, "auto_adds", row["target_selectable_id"])
            if row["target_price_policy_id"] not in self.price_policies:
                errors.append(f"auto_adds references missing price policy: {row['target_price_policy_id']}.")

        for row in self.tables["dependency_rules"]:
            if not is_active(row):
                continue
            self._validate_selector(errors, "dependency_rules", row["subject_selector_type"], row["subject_selector_id"])
            self._validate_condition_ref(errors, "dependency_rules", row.get("applies_when_condition_set_id", ""))
            self._validate_condition_ref(errors, "dependency_rules", row.get("target_condition_set_id", ""))

        for row in self.tables["exclusive_group_members"]:
            if not is_active(row):
                continue
            if row["exclusive_group_id"] not in self.exclusive_members:
                errors.append(f"exclusive_group_members references inactive group: {row['exclusive_group_id']}.")
            self._validate_selectable_ref(errors, "exclusive_group_members", row["member_selectable_id"])

        for row in self.tables["base_prices"] + self.tables["price_rules"]:
            if not is_active(row):
                continue
            self._validate_selector(errors, "pricing", row["target_selector_type"], row["target_selector_id"])
            self._validate_condition_ref(errors, "pricing", row.get("scope_condition_set_id", ""))
            self._validate_condition_ref(errors, "pricing", row.get("applies_when_condition_set_id", ""))

        return errors

    def _validate_selectable_ref(self, errors: list[str], table_name: str, selectable_id: str) -> None:
        if selectable_id and selectable_id not in self.selectables:
            errors.append(f"{table_name} references missing selectable: {selectable_id}.")

    def _validate_condition_ref(self, errors: list[str], table_name: str, condition_set_id: str) -> None:
        if condition_set_id and condition_set_id not in self.condition_sets:
            errors.append(f"{table_name} references missing condition set: {condition_set_id}.")

    def _validate_selector(self, errors: list[str], table_name: str, selector_type: str, selector_id: str) -> None:
        if selector_type == "global":
            return
        if selector_type == "selectable":
            self._validate_selectable_ref(errors, table_name, selector_id)
        elif selector_type == "selectable_set":
            if selector_id not in self.item_sets:
                errors.append(f"{table_name} references missing item set: {selector_id}.")
            elif not self.item_set_members.get(selector_id):
                errors.append(f"{table_name} references item set with no active members: {selector_id}.")
        else:
            errors.append(f"{table_name} uses unsupported selector type: {selector_type}.")

    def evaluate(self, variant_id: str, explicit_selected_ids: list[str]) -> dict[str, Any]:
        validation_errors = self.validate()
        variant = self.variants.get(variant_id)
        if variant is None:
            validation_errors.append(f"Unknown variant_id: {variant_id}.")
            context = {}
        else:
            context = {
                "variant_id": variant["variant_id"],
                "body_style": variant["body_style"],
                "trim_level": variant["trim_level"],
                "model_year": variant["model_year"],
            }

        explicit_selected = [selectable_id for selectable_id in explicit_selected_ids if selectable_id]
        selected = set(explicit_selected)
        auto_triggers: dict[str, list[str]] = defaultdict(list)

        changed = True
        while changed:
            changed = False
            for row in sorted(
                (item for item in self.tables["auto_adds"] if is_active(item)),
                key=lambda item: as_int(item.get("priority", "")),
            ):
                if not self.selector_matches(row["source_selector_type"], row["source_selector_id"], selected):
                    continue
                if row["trigger_condition_set_id"] and not self.condition_matches(row["trigger_condition_set_id"], context, selected):
                    continue
                if row["scope_condition_set_id"] and not self.condition_matches(row["scope_condition_set_id"], context, selected):
                    continue
                target_id = row["target_selectable_id"]
                if self.has_selected_exclusive_peer(target_id, selected):
                    continue
                if row["auto_add_id"] not in auto_triggers[target_id]:
                    auto_triggers[target_id].append(row["auto_add_id"])
                if target_id not in selected:
                    selected.add(target_id)
                    changed = True

        requirements = self.evaluate_requirements(context, selected)
        conflicts = self.evaluate_conflicts(context, selected)
        lines = self.build_lines(explicit_selected, selected, auto_triggers, context)

        return {
            "variant_id": variant_id,
            "context": context,
            "explicit_selected_ids": explicit_selected,
            "lines": lines,
            "requirements": requirements,
            "conflicts": conflicts,
            "validation_errors": validation_errors,
        }

    def selector_matches(self, selector_type: str, selector_id: str, selected: set[str]) -> bool:
        if selector_type == "global":
            return True
        if selector_type == "selectable":
            return selector_id in selected
        if selector_type == "selectable_set":
            return any(member_id in selected for member_id in self.item_set_members.get(selector_id, []))
        return False

    def condition_matches(self, condition_set_id: str, context: dict[str, str], selected: set[str]) -> bool:
        terms = self.condition_terms.get(condition_set_id, [])
        if not terms:
            return False
        by_group: dict[str, list[dict[str, str]]] = defaultdict(list)
        for term in terms:
            by_group[term["or_group"]].append(term)
        return any(all(self.term_matches(term, context, selected) for term in group_terms) for group_terms in by_group.values())

    def term_matches(self, term: dict[str, str], context: dict[str, str], selected: set[str]) -> bool:
        term_type = term["term_type"]
        left_ref = term["left_ref"]
        operator = term["operator"]
        right_value = term["right_value"]
        if term_type == "context" and operator == "eq":
            matched = context.get(left_ref, "") == right_value
        elif term_type == "selected" and operator == "is_true":
            matched = left_ref in selected
        elif term_type == "selected_any_in_set" and operator == "is_true":
            matched = any(member_id in selected for member_id in self.item_set_members.get(left_ref, []))
        else:
            matched = False
        return not matched if as_bool(term.get("negate", "")) else matched

    def has_selected_exclusive_peer(self, target_id: str, selected: set[str]) -> bool:
        for group_id in self.exclusive_groups_by_member.get(target_id, []):
            members = self.exclusive_members.get(group_id, [])
            if any(member_id != target_id and member_id in selected for member_id in members):
                return True
        return False

    def evaluate_requirements(self, context: dict[str, str], selected: set[str]) -> list[dict[str, Any]]:
        requirements: list[dict[str, Any]] = []
        for row in sorted(
            (item for item in self.tables["dependency_rules"] if is_active(item)),
            key=lambda item: as_int(item.get("priority", "")),
        ):
            if row["rule_type"] != "requires":
                continue
            if as_bool(row["subject_must_be_selected"]) and not self.selector_matches(
                row["subject_selector_type"],
                row["subject_selector_id"],
                selected,
            ):
                continue
            if row["applies_when_condition_set_id"] and not self.condition_matches(
                row["applies_when_condition_set_id"],
                context,
                selected,
            ):
                continue
            target_condition_set_id = row["target_condition_set_id"]
            if target_condition_set_id and not self.condition_matches(target_condition_set_id, context, selected):
                requirements.append(
                    {
                        "rule_id": row["rule_id"],
                        "required_condition_set_id": target_condition_set_id,
                        "message": row["message"],
                        "violation_behavior": row["violation_behavior"],
                    }
                )
        return requirements

    def evaluate_conflicts(self, context: dict[str, str], selected: set[str]) -> list[dict[str, Any]]:
        conflicts: list[dict[str, Any]] = []
        for row in sorted(
            (item for item in self.tables["exclusive_groups"] if is_active(item)),
            key=lambda item: as_int(item.get("priority", "")),
        ):
            if row["scope_condition_set_id"] and not self.condition_matches(row["scope_condition_set_id"], context, selected):
                continue
            members = self.exclusive_members.get(row["exclusive_group_id"], [])
            selected_members = [member_id for member_id in members if member_id in selected]
            if len(selected_members) > as_int(row["max_selected"], 1):
                conflicts.append(
                    {
                        "exclusive_group_id": row["exclusive_group_id"],
                        "member_ids": selected_members,
                        "message": row["message"],
                        "conflict_policy": row["conflict_policy"],
                    }
                )
        return conflicts

    def build_lines(
        self,
        explicit_selected: list[str],
        selected: set[str],
        auto_triggers: dict[str, list[str]],
        context: dict[str, str],
    ) -> list[dict[str, Any]]:
        ordered_ids = list(explicit_selected)
        ordered_ids.extend(selectable_id for selectable_id in selected if selectable_id not in set(ordered_ids))
        lines: list[dict[str, Any]] = []
        for selectable_id in ordered_ids:
            selectable = self.selectables.get(selectable_id, {})
            auto_add_ids = auto_triggers.get(selectable_id, [])
            explicit = selectable_id in explicit_selected
            if explicit and auto_add_ids:
                provenance = "explicit+auto"
            elif explicit:
                provenance = "explicit"
            else:
                provenance = "auto"
            lines.append(
                {
                    "selectable_id": selectable_id,
                    "rpo": selectable.get("rpo", ""),
                    "label": selectable.get("label", ""),
                    "provenance": provenance,
                    "price_usd": self.resolve_price(selectable_id, context, selected, auto_add_ids),
                    "auto_add_ids": auto_add_ids,
                }
            )
        return lines

    def resolve_price(
        self,
        selectable_id: str,
        context: dict[str, str],
        selected: set[str],
        auto_add_ids: list[str],
    ) -> int:
        if self.has_included_zero_policy(auto_add_ids):
            return 0

        price = self.base_price(selectable_id, context, selected)
        matched_rules = [
            row
            for row in self.tables["price_rules"]
            if is_active(row)
            and self.selector_targets_selectable(row["target_selector_type"], row["target_selector_id"], selectable_id)
            and self.condition_matches(row["applies_when_condition_set_id"], context, selected)
        ]
        matched_rules.sort(key=lambda row: as_int(row["priority"]), reverse=True)
        for row in matched_rules:
            if row["price_action"] == "set_static":
                price = as_int(row["amount_usd"])
                if row["stack_mode"] in {"exclusive", "stop_after_apply"}:
                    break
        return price

    def has_included_zero_policy(self, auto_add_ids: list[str]) -> bool:
        auto_add_rows = {row["auto_add_id"]: row for row in self.tables["auto_adds"] if is_active(row)}
        return any(
            self.price_policies.get(auto_add_rows[auto_add_id]["target_price_policy_id"], {}).get("policy_type") == "force_amount"
            and as_int(self.price_policies[auto_add_rows[auto_add_id]["target_price_policy_id"]]["amount_usd"]) == 0
            for auto_add_id in auto_add_ids
            if auto_add_id in auto_add_rows
        )

    def base_price(self, selectable_id: str, context: dict[str, str], selected: set[str]) -> int:
        candidates = [
            row
            for row in self.tables["base_prices"]
            if is_active(row)
            and self.selector_targets_selectable(row["target_selector_type"], row["target_selector_id"], selectable_id)
            and (not row["scope_condition_set_id"] or self.condition_matches(row["scope_condition_set_id"], context, selected))
        ]
        candidates.sort(
            key=lambda row: (
                as_int(row["priority"]),
                2 if row["target_selector_type"] == "selectable" else 1,
            ),
            reverse=True,
        )
        return as_int(candidates[0]["amount_usd"]) if candidates else 0

    def selector_targets_selectable(self, selector_type: str, selector_id: str, selectable_id: str) -> bool:
        if selector_type == "selectable":
            return selector_id == selectable_id
        if selector_type == "selectable_set":
            return selectable_id in self.item_set_members.get(selector_id, [])
        return False


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--package", default=str(DEFAULT_PACKAGE))
    parser.add_argument("--variant-id", required=True)
    parser.add_argument("--selected", default="")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    package = CsvSlice(Path(args.package))
    selected = [item for item in args.selected.split("|") if item]
    print(json.dumps(package.evaluate(args.variant_id, selected), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
