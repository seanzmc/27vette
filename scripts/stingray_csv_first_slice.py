#!/usr/bin/env python3
"""Evaluate the first Stingray CSV migration slice without touching production generation."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PACKAGE = ROOT / "data" / "stingray"


TABLES = {
    "variants": "catalog/variants.csv",
    "selectables": "catalog/selectables.csv",
    "selectable_display": "ui/selectable_display.csv",
    "item_sets": "catalog/item_sets.csv",
    "item_set_members": "catalog/item_set_members.csv",
    "condition_sets": "logic/condition_sets.csv",
    "condition_terms": "logic/condition_terms.csv",
    "auto_adds": "logic/auto_adds.csv",
    "dependency_rules": "logic/dependency_rules.csv",
    "rule_groups": "logic/rule_groups.csv",
    "rule_group_members": "logic/rule_group_members.csv",
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
    "selectable_display": "selectable_id",
    "item_sets": "set_id",
    "condition_sets": "condition_set_id",
    "auto_adds": "auto_add_id",
    "dependency_rules": "rule_id",
    "rule_groups": "rule_group_id",
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
        self.selectable_display = {row["selectable_id"]: row for row in self.tables["selectable_display"]}
        self.price_policies = {row["price_policy_id"]: row for row in self.tables["price_policies"]}
        self.auto_adds = {row["auto_add_id"]: row for row in self.tables["auto_adds"] if is_active(row)}
        self.item_set_members = self._build_item_set_members()
        self.condition_terms = self._build_condition_terms()
        self.rule_group_members = self._build_rule_group_members()
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

    def _build_rule_group_members(self) -> dict[str, list[dict[str, str]]]:
        members: dict[str, list[dict[str, str]]] = defaultdict(list)
        for row in self.tables["rule_group_members"]:
            if is_active(row):
                members[row["rule_group_id"]].append(row)
        for rows in members.values():
            rows.sort(key=lambda item: (as_int(item.get("member_order", "")), item["target_selectable_id"]))
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

        for set_id in self.item_sets:
            if not self.item_set_members.get(set_id):
                errors.append(f"item set has no active members: {set_id}.")
        for set_id, members in self.item_set_members.items():
            if set_id not in self.item_sets:
                errors.append(f"item_set_members references missing set_id: {set_id}.")
            for member_id in members:
                if member_id not in self.selectables:
                    errors.append(f"item_set_members references missing selectable: {member_id}.")

        for selectable_id, row in self.selectable_display.items():
            self._validate_selectable_ref(errors, "selectable_display", selectable_id)
            self._validate_condition_ref(errors, "selectable_display", row.get("status_condition_set_id", ""))

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
            if not self.supports_condition_term(term_type, row["operator"]):
                errors.append(f"condition term uses unsupported type/operator: {term_type}/{row['operator']}.")

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
            if row["rule_type"] not in {"requires", "excludes"}:
                errors.append(f"dependency_rules uses unsupported rule_type: {row['rule_type']}.")
            self._validate_selector(errors, "dependency_rules", row["subject_selector_type"], row["subject_selector_id"])
            self._validate_condition_ref(errors, "dependency_rules", row.get("applies_when_condition_set_id", ""))
            self._validate_condition_ref(errors, "dependency_rules", row.get("target_condition_set_id", ""))

        for row in self.tables["rule_groups"]:
            if not is_active(row):
                continue
            group_id = row["rule_group_id"]
            if row["group_type"] != "requires_any":
                errors.append(f"rule_groups uses unsupported group_type: {row['group_type']}.")
            if not row["source_selectable_id"]:
                errors.append("rule_groups has a row missing source_selectable_id.")
            self._validate_selectable_ref(errors, "rule_groups", row["source_selectable_id"])
            for scope_field in ("body_style_scope", "trim_level_scope", "variant_scope"):
                if row.get(scope_field, ""):
                    errors.append(f"rule_groups uses unsupported {scope_field}: {row[scope_field]}.")
            if row["group_type"] == "requires_any" and not row.get("disabled_reason", ""):
                errors.append(f"requires_any rule group is missing disabled_reason: {group_id}.")
            if not self.rule_group_members.get(group_id):
                errors.append(f"rule group has no active members: {group_id}.")

        active_rule_group_ids = {row["rule_group_id"] for row in self.tables["rule_groups"] if is_active(row)}
        for row in self.tables["rule_group_members"]:
            if not is_active(row):
                continue
            group_id = row["rule_group_id"]
            if group_id not in active_rule_group_ids:
                errors.append(f"rule_group_members references inactive group: {group_id}.")
            self._validate_selectable_ref(errors, "rule_group_members", row["target_selectable_id"])
            try:
                as_int(row.get("member_order", ""))
            except ValueError:
                errors.append(f"rule_group_members has unsupported member_order: {row.get('member_order', '')}.")

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

        base_price_keys: dict[tuple[str, str, str, str], list[str]] = defaultdict(list)
        for row in self.tables["base_prices"]:
            if not is_active(row):
                continue
            key = (
                row["target_selector_type"],
                row["target_selector_id"],
                row.get("scope_condition_set_id", ""),
                row.get("priority", ""),
            )
            base_price_keys[key].append(row["base_price_id"])
        for ids in base_price_keys.values():
            if len(ids) > 1:
                errors.append(f"ambiguous same-priority base prices: {', '.join(ids)}.")

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

    def supports_condition_term(self, term_type: str, operator: str) -> bool:
        return (term_type, operator) in {
            ("context", "eq"),
            ("selected", "is_true"),
            ("selected_any_in_set", "is_true"),
        }

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
        matched_auto_adds: dict[str, list[str]] = defaultdict(list)

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
                if row["auto_add_id"] not in matched_auto_adds[target_id]:
                    matched_auto_adds[target_id].append(row["auto_add_id"])
                if target_id not in selected:
                    selected.add(target_id)
                    changed = True

        open_requirements = self.evaluate_requirements(context, selected)
        conflicts = self.evaluate_conflicts(context, selected)
        selected_lines = self.build_lines(explicit_selected, selected, matched_auto_adds, context)
        selected_line_ids = [line["selectable_id"] for line in selected_lines]
        if len(selected_line_ids) != len(set(selected_line_ids)):
            validation_errors.append("duplicate final selected lines after auto-add closure.")
        auto_added_ids = [
            line["selectable_id"]
            for line in selected_lines
            if line["selectable_id"] not in explicit_selected and line["matched_auto_add_ids"]
        ]

        return {
            "variant_id": variant_id,
            "context": context,
            "explicit_selected_ids": explicit_selected,
            "selected_lines": selected_lines,
            "auto_added_ids": auto_added_ids,
            "open_requirements": open_requirements,
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
        if not self.supports_condition_term(term_type, operator):
            return False
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
                        "member_selectable_ids": selected_members,
                        "message": row["message"],
                        "conflict_policy": row["conflict_policy"],
                    }
                )
        for row in sorted(
            (item for item in self.tables["dependency_rules"] if is_active(item)),
            key=lambda item: as_int(item.get("priority", "")),
        ):
            if row["rule_type"] != "excludes":
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
            if target_condition_set_id and self.condition_matches(target_condition_set_id, context, selected):
                conflicts.append(
                    {
                        "conflict_source": "dependency_rule",
                        "rule_id": row["rule_id"],
                        "target_condition_set_id": target_condition_set_id,
                        "target_selectable_id": self.condition_selected_selectable(target_condition_set_id),
                        "message": row["message"],
                        "violation_behavior": row["violation_behavior"],
                    }
                )
        return conflicts

    def build_lines(
        self,
        explicit_selected: list[str],
        selected: set[str],
        matched_auto_adds: dict[str, list[str]],
        context: dict[str, str],
    ) -> list[dict[str, Any]]:
        ordered_ids = list(explicit_selected)
        ordered_ids.extend(selectable_id for selectable_id in matched_auto_adds if selectable_id in selected and selectable_id not in set(ordered_ids))
        ordered_ids.extend(sorted(selectable_id for selectable_id in selected if selectable_id not in set(ordered_ids)))
        lines: list[dict[str, Any]] = []
        for selectable_id in ordered_ids:
            selectable = self.selectables.get(selectable_id, {})
            auto_add_ids = matched_auto_adds.get(selectable_id, [])
            explicit = selectable_id in explicit_selected
            provenance = ["explicit"] if explicit else ["auto"]
            price_result = self.resolve_price(selectable_id, context, selected, auto_add_ids)
            lines.append(
                {
                    "selectable_id": selectable_id,
                    "rpo": selectable.get("rpo", ""),
                    "label": selectable.get("label", ""),
                    "provenance": provenance,
                    "final_price_usd": price_result["final_price_usd"],
                    "matched_base_price_id": price_result["matched_base_price_id"],
                    "matched_price_rule_ids": price_result["matched_price_rule_ids"],
                    "matched_auto_add_ids": auto_add_ids,
                }
            )
        return lines

    def resolve_price(
        self,
        selectable_id: str,
        context: dict[str, str],
        selected: set[str],
        auto_add_ids: list[str],
    ) -> dict[str, Any]:
        base_price = self.base_price(selectable_id, context, selected)
        price = base_price["amount_usd"]
        matched_price_rule_ids: list[str] = []
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
                matched_price_rule_ids.append(row["price_rule_id"])
                if row["stack_mode"] in {"exclusive", "stop_after_apply"}:
                    break
        if self.has_included_zero_policy(auto_add_ids):
            price = 0
        return {
            "final_price_usd": price,
            "matched_base_price_id": base_price["base_price_id"],
            "matched_price_rule_ids": matched_price_rule_ids,
        }

    def has_included_zero_policy(self, auto_add_ids: list[str]) -> bool:
        return any(
            self.price_policies.get(self.auto_adds[auto_add_id]["target_price_policy_id"], {}).get("policy_type") == "force_amount"
            and as_int(self.price_policies[self.auto_adds[auto_add_id]["target_price_policy_id"]]["amount_usd"]) == 0
            for auto_add_id in auto_add_ids
            if auto_add_id in self.auto_adds
        )

    def base_price(self, selectable_id: str, context: dict[str, str], selected: set[str]) -> dict[str, Any]:
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
        if not candidates:
            return {"base_price_id": None, "amount_usd": 0}
        return {
            "base_price_id": candidates[0]["base_price_id"],
            "amount_usd": as_int(candidates[0]["amount_usd"]),
        }

    def selector_targets_selectable(self, selector_type: str, selector_id: str, selectable_id: str) -> bool:
        if selector_type == "selectable":
            return selector_id == selectable_id
        if selector_type == "selectable_set":
            return selectable_id in self.item_set_members.get(selector_id, [])
        return False

    def legacy_fragment(self) -> dict[str, Any]:
        validation_errors = self.validate()
        fragment = {
            "variants": self.legacy_variants(),
            "choices": self.legacy_choices(),
            "ruleGroups": self.legacy_rule_groups(),
            "exclusiveGroups": self.legacy_exclusive_groups(),
            "rules": self.legacy_rules(),
            "priceRules": self.legacy_price_rules(),
            "documented_mismatches": [],
            "validation_errors": validation_errors,
        }
        return fragment

    def legacy_variants(self) -> list[dict[str, Any]]:
        rows = []
        for index, variant in enumerate(sorted(self.variants.values(), key=lambda row: row["variant_id"]), start=1):
            rows.append(
                {
                    "variant_id": variant["variant_id"],
                    "model_year": as_int(variant["model_year"]),
                    "trim_level": variant["trim_level"],
                    "body_style": variant["body_style"],
                    "display_name": f"Corvette Stingray {variant['label'].split()[-1]} {variant['trim_level']}",
                    "base_price": as_int(variant["base_price_usd"]),
                    "display_order": index,
                }
            )
        rows.sort(key=lambda row: (row["body_style"] != "coupe", row["trim_level"]))
        for index, row in enumerate(rows, start=1):
            row["display_order"] = index
        return rows

    def legacy_choices(self) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for variant in sorted(self.variants.values(), key=lambda row: row["variant_id"]):
            context = {
                "variant_id": variant["variant_id"],
                "body_style": variant["body_style"],
                "trim_level": variant["trim_level"],
                "model_year": variant["model_year"],
            }
            for selectable_id in sorted(self.selectables, key=lambda item: as_int(self.display_row(item).get("display_order", ""))):
                display = self.display_row(selectable_id)
                status, status_label = self.legacy_status(display, context)
                option_id = self.legacy_option_id(selectable_id)
                rows.append(
                    {
                        "choice_id": f"{variant['variant_id']}__{option_id}",
                        "option_id": option_id,
                        "rpo": self.selectables[selectable_id]["rpo"],
                        "label": display.get("label") or self.selectables[selectable_id]["label"],
                        "description": display.get("description") or self.selectables[selectable_id]["description"],
                        "section_id": display["section_id"],
                        "section_name": display["section_name"],
                        "category_id": display["category_id"],
                        "category_name": display["category_name"],
                        "step_key": display["step_key"],
                        "variant_id": variant["variant_id"],
                        "body_style": variant["body_style"],
                        "trim_level": variant["trim_level"],
                        "status": status,
                        "status_label": status_label,
                        "selectable": display["selectable"],
                        "active": display["active"],
                        "choice_mode": display["choice_mode"],
                        "selection_mode": display["selection_mode"],
                        "selection_mode_label": display["selection_mode_label"],
                        "base_price": self.legacy_base_price(selectable_id),
                        "display_order": as_int(display["display_order"]),
                        "source_detail_raw": display.get("source_detail_raw", ""),
                    }
                )
        rows.sort(key=lambda row: (row["variant_id"], row["display_order"], row["option_id"]))
        return rows

    def legacy_rules(self) -> list[dict[str, Any]]:
        rows = []
        for row in sorted((item for item in self.tables["auto_adds"] if is_active(item)), key=lambda item: item["auto_add_id"]):
            for source_id in self.selector_selectable_ids(row["source_selector_type"], row["source_selector_id"]):
                rows.append(self.legacy_include_rule(row, source_id))
        for row in sorted((item for item in self.tables["dependency_rules"] if is_active(item)), key=lambda item: item["rule_id"]):
            target_id = self.condition_selected_selectable(row["target_condition_set_id"])
            if not target_id:
                continue
            for source_id in self.selector_selectable_ids(row["subject_selector_type"], row["subject_selector_id"]):
                rows.append(self.legacy_dependency_rule(row, source_id, target_id))
        rows.sort(key=lambda item: (item["source_id"], item["rule_type"], item["target_id"], item["body_style_scope"]))
        return rows

    def legacy_include_rule(self, row: dict[str, str], source_selectable_id: str) -> dict[str, Any]:
        target_selectable_id = row["target_selectable_id"]
        source_display = self.display_row(source_selectable_id)
        target_display = self.display_row(target_selectable_id)
        return {
            "rule_id": f"rule_{self.legacy_option_id(source_selectable_id)}_includes_{self.legacy_option_id(target_selectable_id)}",
            "source_id": self.legacy_option_id(source_selectable_id),
            "rule_type": "includes",
            "target_id": self.legacy_option_id(target_selectable_id),
            "target_type": "main",
            "source_type": "main",
            "source_section": source_display["section_id"],
            "target_section": target_display["section_id"],
            "source_selection_mode": source_display["selection_mode"],
            "target_selection_mode": target_display["selection_mode"],
            "body_style_scope": row.get("legacy_body_style_scope", self.condition_body_style_scope(row.get("scope_condition_set_id", ""))),
            "disabled_reason": f"Included with {self.selectables[source_selectable_id]['rpo']} {source_display.get('label') or self.selectables[source_selectable_id]['label']}.",
            "auto_add": "True",
            "active": "True",
            "runtime_action": "active",
            "source_note": target_display.get("source_detail_raw", ""),
            "review_flag": "False",
        }

    def legacy_dependency_rule(self, row: dict[str, str], source_selectable_id: str, target_selectable_id: str) -> dict[str, Any]:
        source_display = self.display_row(source_selectable_id)
        target_display = self.display_row(target_selectable_id)
        rule_type = row["rule_type"]
        if rule_type == "requires":
            target_type = "option" if row["subject_selector_type"] == "selectable" else "main"
            source_type = "option" if row["subject_selector_type"] == "selectable" else "main"
        else:
            target_type = "main"
            source_type = "main"
        return {
            "rule_id": f"rule_{self.legacy_option_id(source_selectable_id)}_{rule_type}_{self.legacy_option_id(target_selectable_id)}",
            "source_id": self.legacy_option_id(source_selectable_id),
            "rule_type": rule_type,
            "target_id": self.legacy_option_id(target_selectable_id),
            "target_type": target_type,
            "source_type": source_type,
            "source_section": source_display["section_id"],
            "target_section": target_display["section_id"],
            "source_selection_mode": source_display["selection_mode"],
            "target_selection_mode": target_display["selection_mode"],
            "body_style_scope": self.condition_body_style_scope(row.get("applies_when_condition_set_id", "")),
            "disabled_reason": row["message"],
            "auto_add": "False",
            "active": "True",
            "runtime_action": "active",
            "source_note": source_display.get("source_detail_raw", ""),
            "review_flag": "False",
        }

    def legacy_price_rules(self) -> list[dict[str, Any]]:
        rows = []
        for row in sorted((item for item in self.tables["auto_adds"] if is_active(item)), key=lambda item: item["auto_add_id"]):
            if not self.has_included_zero_policy([row["auto_add_id"]]):
                continue
            target_id = row["target_selectable_id"]
            if self.legacy_base_price(target_id) == 0:
                continue
            for source_id in self.selector_selectable_ids(row["source_selector_type"], row["source_selector_id"]):
                rows.append(
                    {
                        "price_rule_id": f"pr_{self.legacy_option_id(source_id)}_{self.legacy_option_id(target_id)}_included_zero",
                        "condition_option_id": self.legacy_option_id(source_id),
                        "target_option_id": self.legacy_option_id(target_id),
                        "price_rule_type": "override",
                        "price_value": 0,
                        "body_style_scope": "",
                        "trim_level_scope": "",
                        "variant_scope": "",
                        "review_flag": "False",
                        "notes": row.get("legacy_notes", ""),
                    }
                )
        for row in sorted((item for item in self.tables["price_rules"] if is_active(item)), key=lambda item: item["price_rule_id"]):
            source_id = self.condition_selected_selectable(row["applies_when_condition_set_id"])
            if not source_id:
                continue
            for target_id in self.selector_selectable_ids(row["target_selector_type"], row["target_selector_id"]):
                rows.append(
                    {
                        "price_rule_id": f"pr_{self.legacy_option_id(source_id)}_{self.legacy_option_id(target_id)}_{self.condition_body_style_scope(row['applies_when_condition_set_id'])}",
                        "condition_option_id": self.legacy_option_id(source_id),
                        "target_option_id": self.legacy_option_id(target_id),
                        "price_rule_type": "override",
                        "price_value": as_int(row["amount_usd"]),
                        "body_style_scope": self.condition_body_style_scope(row["applies_when_condition_set_id"]),
                        "trim_level_scope": "",
                        "variant_scope": "",
                        "review_flag": "False",
                        "notes": row.get("explanation", ""),
                    }
                )
        rows.sort(key=lambda item: (item["condition_option_id"], item["target_option_id"], item["body_style_scope"], item["price_value"]))
        return rows

    def legacy_rule_groups(self) -> list[dict[str, Any]]:
        rows = []
        for row in sorted((item for item in self.tables["rule_groups"] if is_active(item)), key=lambda item: item["rule_group_id"]):
            target_ids = [
                self.legacy_option_id(member["target_selectable_id"])
                for member in self.rule_group_members.get(row["rule_group_id"], [])
            ]
            rows.append(
                {
                    "group_id": row.get("legacy_group_id") or row["rule_group_id"],
                    "group_type": row["group_type"],
                    "source_id": self.legacy_option_id(row["source_selectable_id"]),
                    "target_ids": target_ids,
                    "body_style_scope": row.get("body_style_scope", ""),
                    "trim_level_scope": row.get("trim_level_scope", ""),
                    "variant_scope": row.get("variant_scope", ""),
                    "disabled_reason": row["disabled_reason"],
                    "active": "True",
                    "notes": row.get("legacy_notes", ""),
                }
            )
        return rows

    def legacy_exclusive_groups(self) -> list[dict[str, Any]]:
        rows = []
        for row in sorted((item for item in self.tables["exclusive_groups"] if is_active(item)), key=lambda item: item["exclusive_group_id"]):
            option_ids = [self.legacy_option_id(selectable_id) for selectable_id in self.exclusive_members.get(row["exclusive_group_id"], [])]
            rows.append(
                {
                    "group_id": row.get("legacy_group_id") or row["exclusive_group_id"],
                    "option_ids": option_ids,
                    "selection_mode": "single_within_group" if as_int(row["max_selected"], 1) == 1 else "multi_within_group",
                    "active": "True",
                    "notes": row.get("legacy_notes") or row.get("message", ""),
                }
            )
        return rows

    def selector_selectable_ids(self, selector_type: str, selector_id: str) -> list[str]:
        if selector_type == "selectable":
            return [selector_id]
        if selector_type == "selectable_set":
            return list(self.item_set_members.get(selector_id, []))
        return []

    def condition_selected_selectable(self, condition_set_id: str) -> str:
        selected_terms = [
            term["left_ref"]
            for term in self.condition_terms.get(condition_set_id, [])
            if term["term_type"] == "selected" and term["operator"] == "is_true" and not as_bool(term.get("negate", ""))
        ]
        return selected_terms[0] if len(selected_terms) == 1 else ""

    def condition_body_style_scope(self, condition_set_id: str) -> str:
        body_terms = [
            term["right_value"]
            for term in self.condition_terms.get(condition_set_id, [])
            if term["term_type"] == "context"
            and term["left_ref"] == "body_style"
            and term["operator"] == "eq"
            and not as_bool(term.get("negate", ""))
        ]
        return body_terms[0] if len(set(body_terms)) == 1 else ""

    def legacy_status(self, display: dict[str, str], context: dict[str, str]) -> tuple[str, str]:
        condition_set_id = display.get("status_condition_set_id", "")
        matched = True if not condition_set_id else self.condition_matches(condition_set_id, context, set())
        if matched:
            return display["status_when_matched"], display["status_label_when_matched"]
        return display["status_when_unmatched"], display["status_label_when_unmatched"]

    def legacy_base_price(self, selectable_id: str) -> int:
        candidates = [
            row
            for row in self.tables["base_prices"]
            if is_active(row) and self.selector_targets_selectable(row["target_selector_type"], row["target_selector_id"], selectable_id)
        ]
        candidates.sort(key=lambda row: (as_int(row["priority"]), 2 if row["target_selector_type"] == "selectable" else 1), reverse=True)
        return as_int(candidates[0]["amount_usd"]) if candidates else 0

    def display_row(self, selectable_id: str) -> dict[str, str]:
        return self.selectable_display.get(selectable_id, {})

    def legacy_option_id(self, selectable_id: str) -> str:
        return self.display_row(selectable_id).get("legacy_option_id") or selectable_id


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--package", default=str(DEFAULT_PACKAGE))
    parser.add_argument("--emit-legacy-fragment", action="store_true")
    parser.add_argument("--out", default="")
    parser.add_argument("--scenario-json", default="")
    parser.add_argument("--variant-id", default="")
    parser.add_argument("--selected-ids", default="")
    parser.add_argument("--selected", default="")
    return parser.parse_args()


def scenario_from_args(args: argparse.Namespace) -> tuple[str, list[str]]:
    if args.scenario_json:
        scenario = json.loads(args.scenario_json)
        return scenario["variant_id"], list(scenario.get("selected_ids", []))
    if not args.variant_id:
        raise ValueError("--variant-id is required unless --scenario-json is provided.")
    if args.selected_ids:
        return args.variant_id, [item.strip() for item in args.selected_ids.split(",") if item.strip()]
    return args.variant_id, [item for item in args.selected.split("|") if item]


def main() -> None:
    args = parse_args()
    package = CsvSlice(Path(args.package))
    try:
        if args.emit_legacy_fragment:
            result = package.legacy_fragment()
        else:
            variant_id, selected = scenario_from_args(args)
            result = package.evaluate(variant_id, selected)
    except (KeyError, json.JSONDecodeError, ValueError) as error:
        print(json.dumps({"validation_errors": [str(error)]}, indent=2, sort_keys=True))
        sys.exit(1)
    output = json.dumps(result, indent=2, sort_keys=True)
    if args.out:
        output_path = Path(args.out)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(output + "\n", encoding="utf-8")
    else:
        print(output)
    if result["validation_errors"]:
        sys.exit(1)


if __name__ == "__main__":
    main()
