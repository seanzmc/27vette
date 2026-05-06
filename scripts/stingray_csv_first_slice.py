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
    "non_selectable_references": "validation/non_selectable_references.csv",
}

OPTIONAL_TABLES = {
    "simple_dependency_rules": "logic/simple_dependency_rules.csv",
    "canonical_options": "catalog/canonical_options.csv",
    "option_presentations": "ui/option_presentations.csv",
    "option_status_rules": "logic/option_status_rules.csv",
    "canonical_base_prices": "pricing/canonical_base_prices.csv",
}

FINAL_CANONICAL_TABLES = {
    "canonical_source_documents": "canonical/source/source_documents.csv",
    "canonical_source_rows": "canonical/source/source_rows.csv",
    "canonical_source_row_classifications": "canonical/source/source_row_classifications.csv",
    "canonical_duplicate_rpo_reviews": "canonical/options/duplicate_rpo_reviews.csv",
    "final_canonical_variants": "canonical/status/variants.csv",
    "final_context_scopes": "canonical/status/context_scopes.csv",
    "final_price_books": "canonical/pricing/price_books.csv",
    "final_canonical_base_prices": "canonical/pricing/canonical_base_prices.csv",
}

SIMPLE_DEPENDENCY_RULE_FIELDS = [
    "rule_id",
    "rule_type",
    "source_option_id",
    "target_option_id",
    "violation_behavior",
    "message",
    "priority",
    "active",
]

CANONICAL_OPTION_FIELDS = [
    "canonical_option_id",
    "rpo",
    "label",
    "description",
    "canonical_kind",
    "active",
    "notes",
]

OPTION_PRESENTATION_FIELDS = [
    "presentation_id",
    "canonical_option_id",
    "legacy_option_id",
    "rpo_override",
    "presentation_role",
    "section_id",
    "section_name",
    "category_id",
    "category_name",
    "step_key",
    "choice_mode",
    "selection_mode",
    "selection_mode_label",
    "display_order",
    "selectable",
    "active",
    "label",
    "description",
    "source_detail_raw",
    "notes",
]

OPTION_STATUS_RULE_FIELDS = [
    "status_rule_id",
    "canonical_option_id",
    "presentation_id",
    "scope_model_year",
    "scope_body_style",
    "scope_trim_level",
    "scope_variant_id",
    "condition_set_id",
    "status",
    "status_label",
    "priority",
    "active",
    "notes",
]

CANONICAL_BASE_PRICE_FIELDS = [
    "canonical_base_price_id",
    "price_book_id",
    "canonical_option_id",
    "presentation_id",
    "scope_condition_set_id",
    "amount_usd",
    "priority",
    "active",
    "notes",
]

CANONICAL_SOURCE_DOCUMENT_FIELDS = [
    "source_document_id",
    "source_type",
    "model_year",
    "model_key",
    "vehicle_line",
    "source_vehicle_line",
    "source_model_line",
    "source_name",
    "source_path",
    "source_checksum",
    "imported_at",
    "notes",
]

CANONICAL_SOURCE_ROW_FIELDS = [
    "source_row_id",
    "source_document_id",
    "source_sheet",
    "source_row_number",
    "source_order",
    "source_section_path",
    "source_order_path",
    "source_option_key",
    "raw_row_hash",
    "legacy_option_id",
    "rpo",
    "raw_label",
    "raw_description",
    "raw_section",
    "raw_category",
    "raw_step",
    "raw_price",
    "raw_status",
    "raw_selectable",
    "raw_detail",
    "raw_payload_json",
    "active",
    "notes",
]

CANONICAL_SOURCE_ROW_CLASSIFICATION_FIELDS = [
    "source_row_id",
    "classification",
    "canonical_option_id",
    "presentation_id",
    "control_plane_reference_id",
    "relationship_type",
    "relationship_id",
    "review_status",
    "review_reason",
    "active",
    "notes",
]

CANONICAL_DUPLICATE_RPO_REVIEW_FIELDS = [
    "duplicate_rpo_review_id",
    "rpo",
    "model_year",
    "model_key",
    "source_row_ids",
    "duplicate_rpo_classification",
    "decision_reason",
    "review_status",
    "reviewed_by",
    "reviewed_at",
    "active",
    "notes",
]

FINAL_CANONICAL_VARIANT_FIELDS = [
    "variant_id",
    "model_year",
    "gm_model_code",
    "model_key",
    "body_style",
    "trim_level",
    "active",
    "notes",
]

FINAL_CONTEXT_SCOPE_FIELDS = [
    "context_scope_id",
    "model_year",
    "model_key",
    "variant_id",
    "body_style",
    "trim_level",
    "priority",
    "active",
    "notes",
]

FINAL_PRICE_BOOK_FIELDS = [
    "price_book_id",
    "model_year",
    "model_key",
    "currency",
    "active",
    "notes",
]

FINAL_CANONICAL_BASE_PRICE_FIELDS = [
    "canonical_base_price_id",
    "price_book_id",
    "canonical_option_id",
    "presentation_id",
    "context_scope_id",
    "amount_usd",
    "priority",
    "active",
    "notes",
]

OPTIONAL_TABLE_FIELDS = {
    "simple_dependency_rules": SIMPLE_DEPENDENCY_RULE_FIELDS,
    "canonical_options": CANONICAL_OPTION_FIELDS,
    "option_presentations": OPTION_PRESENTATION_FIELDS,
    "option_status_rules": OPTION_STATUS_RULE_FIELDS,
    "canonical_base_prices": CANONICAL_BASE_PRICE_FIELDS,
}

FINAL_CANONICAL_TABLE_FIELDS = {
    "canonical_source_documents": CANONICAL_SOURCE_DOCUMENT_FIELDS,
    "canonical_source_rows": CANONICAL_SOURCE_ROW_FIELDS,
    "canonical_source_row_classifications": CANONICAL_SOURCE_ROW_CLASSIFICATION_FIELDS,
    "canonical_duplicate_rpo_reviews": CANONICAL_DUPLICATE_RPO_REVIEW_FIELDS,
    "final_canonical_variants": FINAL_CANONICAL_VARIANT_FIELDS,
    "final_context_scopes": FINAL_CONTEXT_SCOPE_FIELDS,
    "final_price_books": FINAL_PRICE_BOOK_FIELDS,
    "final_canonical_base_prices": FINAL_CANONICAL_BASE_PRICE_FIELDS,
}

CANONICAL_OPTION_KINDS = {"customer_choice", "equipment_feature", "structured_reference", "review_required"}
PRESENTATION_ROLES = {
    "choice",
    "standard_options_display",
    "standard_equipment_display",
    "included_display",
    "package_display",
    "legacy_alias",
    "display_only",
}
OPTION_STATUSES = {"optional", "standard_choice", "standard_fixed", "included_auto", "unavailable"}
REVIEW_REQUIRED_DUPLICATE_RPOS = {"AE4", "AH2", "AQ9", "UQT"}
FINAL_CANONICAL_SOURCE_TYPES = {"order_guide", "workbook", "manual_review", "production_oracle_export"}
FINAL_CANONICAL_SOURCE_ROW_CLASSIFICATIONS = {
    "customer_choice",
    "display_only_duplicate",
    "standard_equipment_display",
    "included_display",
    "package_display",
    "package_source",
    "relationship_source",
    "price_rule_source",
    "replacement_default_source",
    "control_plane_reference",
    "ambiguous_requires_review",
    "ignore_not_stingray",
}
FINAL_CANONICAL_REVIEW_STATUSES = {"unreviewed", "reviewed", "blocked"}
FINAL_CANONICAL_DUPLICATE_RPO_CLASSIFICATIONS = {
    "display_only_duplicate",
    "true_separate_selectable_variant",
    "mixed_display_and_selectable_variants",
    "ambiguous_requires_review",
}
GM_MODEL_CODE_MODEL_KEYS = {
    "C": "stingray",
    "E": "grand_sport",
    "H": "z06",
    "R": "zr1",
    "S": "zr1x",
}
GM_MODEL_CODE_BODY_STYLES = {"07": "coupe", "67": "convertible"}


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
    "non_selectable_references": "reference_id",
    "canonical_options": "canonical_option_id",
    "option_presentations": "presentation_id",
    "option_status_rules": "status_rule_id",
    "canonical_base_prices": "canonical_base_price_id",
    "canonical_source_documents": "source_document_id",
    "canonical_source_rows": "source_row_id",
    "canonical_duplicate_rpo_reviews": "duplicate_rpo_review_id",
    "final_canonical_variants": "variant_id",
    "final_context_scopes": "context_scope_id",
    "final_price_books": "price_book_id",
    "final_canonical_base_prices": "canonical_base_price_id",
}


def load_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def load_optional_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    if not path.exists():
        return [], []
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        return list(reader.fieldnames or []), [dict(row) for row in reader]


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
        self.optional_table_fields: dict[str, list[str]] = {}
        for name, relative_path in OPTIONAL_TABLES.items():
            fields, rows = load_optional_csv(package_dir / relative_path)
            self.optional_table_fields[name] = fields
            self.tables[name] = rows
        for name, relative_path in FINAL_CANONICAL_TABLES.items():
            fields, rows = load_optional_csv(package_dir / relative_path)
            self.optional_table_fields[name] = fields
            self.tables[name] = rows
        self.ownership_rows = self._load_ownership_rows()
        self.variants = {row["variant_id"]: row for row in self.tables["variants"] if is_active(row)}
        self.final_canonical_variants = {
            row.get("variant_id", ""): row
            for row in self.tables["final_canonical_variants"]
            if is_active(row) and row.get("variant_id", "")
        }
        self.final_context_scopes = {
            row.get("context_scope_id", ""): row
            for row in self.tables["final_context_scopes"]
            if is_active(row) and row.get("context_scope_id", "")
        }
        self.final_price_books = {
            row.get("price_book_id", ""): row
            for row in self.tables["final_price_books"]
            if is_active(row) and row.get("price_book_id", "")
        }
        self.final_canonical_base_prices = [
            row for row in self.tables["final_canonical_base_prices"] if is_active(row)
        ]
        self.canonical_namespace_errors: list[str] = []
        self._validate_canonical_namespace_foundation()
        self.canonical_option_errors: list[str] = []
        self.canonical_options = {row["canonical_option_id"]: row for row in self.tables["canonical_options"] if is_active(row)}
        self.option_presentations = {
            row["presentation_id"]: row for row in self.tables["option_presentations"] if is_active(row)
        }
        self.option_status_rules = [
            row for row in self.tables["option_status_rules"] if is_active(row)
        ]
        self.canonical_base_prices = [
            row for row in self.tables["canonical_base_prices"] if is_active(row)
        ]
        self._merge_canonical_presentations()
        self._validate_final_canonical_pricing()
        self.selectables = {row["selectable_id"]: row for row in self.tables["selectables"] if is_active(row)}
        self.projected_owned_selectable_ids = self._build_projected_owned_selectable_ids()
        self.item_sets = {row["set_id"]: row for row in self.tables["item_sets"] if is_active(row)}
        self.condition_sets = {row["condition_set_id"]: row for row in self.tables["condition_sets"] if is_active(row)}
        self.selectable_display = {row["selectable_id"]: row for row in self.tables["selectable_display"]}
        self.price_policies = {row["price_policy_id"]: row for row in self.tables["price_policies"]}
        self.auto_adds = {row["auto_add_id"]: row for row in self.tables["auto_adds"] if is_active(row)}
        self.non_selectable_references = {
            row["reference_id"]: row for row in self.tables["non_selectable_references"] if is_active(row)
        }
        self.non_selectable_reference_selectors = self._build_non_selectable_reference_selectors()
        self.item_set_members = self._build_item_set_members()
        self.simple_dependency_rule_errors: list[str] = []
        self._merge_simple_dependency_rules()
        self.condition_terms = self._build_condition_terms()
        self.rule_group_members = self._build_rule_group_members()
        self.exclusive_members = self._build_exclusive_members()
        self.exclusive_groups_by_member = self._build_exclusive_groups_by_member()

    def _load_ownership_rows(self) -> list[dict[str, str]]:
        path = self.package_dir / "validation" / "projected_slice_ownership.csv"
        return load_csv(path) if path.exists() else []

    def _build_projected_owned_selectable_ids(self) -> set[str]:
        projected_rpos = {
            row.get("rpo", "")
            for row in self.ownership_rows
            if row.get("record_type", "") == "selectable"
            and row.get("ownership", "") == "projected_owned"
            and is_active(row)
            and row.get("rpo", "")
        }
        projected_option_ids = {
            row.get("source_option_id") or row.get("target_option_id") or row.get("rpo", "")
            for row in self.ownership_rows
            if row.get("record_type", "") == "selectable"
            and row.get("ownership", "") == "projected_owned"
            and is_active(row)
            and (row.get("source_option_id") or row.get("target_option_id"))
        }
        return {
            selectable_id
            for selectable_id, row in self.selectables.items()
            if row.get("rpo", "") in projected_rpos or selectable_id in projected_option_ids
        }

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

    def _build_non_selectable_reference_selectors(self) -> dict[str, dict[str, str]]:
        selectors: dict[str, dict[str, str]] = {}
        for row in self.non_selectable_references.values():
            reference_id = row.get("reference_id", "")
            rpo = row.get("rpo", "")
            option_id = row.get("option_id", "")
            for selector_id in {reference_id, f"ref_{rpo.lower()}" if rpo else "", option_id}:
                if selector_id:
                    selectors[selector_id] = row
        return selectors

    def _merge_simple_dependency_rules(self) -> None:
        fields = self.optional_table_fields.get("simple_dependency_rules", [])
        if fields and fields != SIMPLE_DEPENDENCY_RULE_FIELDS:
            unexpected = [field for field in fields if field not in SIMPLE_DEPENDENCY_RULE_FIELDS]
            missing = [field for field in SIMPLE_DEPENDENCY_RULE_FIELDS if field not in fields]
            details = []
            if unexpected:
                details.append(f"unsupported columns: {', '.join(unexpected)}")
            if missing:
                details.append(f"missing columns: {', '.join(missing)}")
            self.simple_dependency_rule_errors.append(f"simple_dependency_rules.csv uses {'; '.join(details)}.")
            return

        rows = self.tables.get("simple_dependency_rules", [])
        if not rows:
            return

        active_dependency_rule_ids = {
            row["rule_id"]
            for row in self.tables["dependency_rules"]
            if is_active(row)
        }
        seen_active_rule_ids: set[str] = set()
        for row in rows:
            row_id = row.get("rule_id", "")
            if row.get("active", "").lower() not in {"true", "false"}:
                self.simple_dependency_rule_errors.append(
                    f"simple_dependency_rules {row_id or '<missing>'} uses unsupported active value: {row.get('active', '')}."
                )
                continue
            if not is_active(row):
                continue
            row_errors = self._validate_simple_dependency_rule_row(row, active_dependency_rule_ids, seen_active_rule_ids)
            if row_errors:
                self.simple_dependency_rule_errors.extend(row_errors)
                continue
            seen_active_rule_ids.add(row_id)
            self._append_simple_dependency_rule(row)

    def _validate_simple_dependency_rule_row(
        self,
        row: dict[str, str],
        active_dependency_rule_ids: set[str],
        seen_active_rule_ids: set[str],
    ) -> list[str]:
        errors: list[str] = []
        row_id = row.get("rule_id", "")
        if not row_id:
            errors.append("simple_dependency_rules has a row missing rule_id.")
        elif row_id in seen_active_rule_ids:
            errors.append(f"simple_dependency_rules has duplicate active rule_id: {row_id}.")
        elif row_id in active_dependency_rule_ids:
            errors.append(f"simple_dependency_rules {row_id} collides with active dependency_rules row.")

        rule_type = row.get("rule_type", "")
        if rule_type not in {"excludes", "requires"}:
            errors.append(f"simple_dependency_rules {row_id or '<missing>'} uses unsupported rule_type: {rule_type}.")

        for field in ("source_option_id", "target_option_id", "violation_behavior", "message", "priority"):
            if not row.get(field, ""):
                errors.append(f"simple_dependency_rules {row_id or '<missing>'} is missing {field}.")

        for field in ("source_option_id", "target_option_id"):
            selectable_id = row.get(field, "")
            if selectable_id and selectable_id not in self.projected_owned_selectable_ids:
                errors.append(
                    f"simple_dependency_rules {row_id or '<missing>'} {field} is not an active projected-owned selectable: {selectable_id}."
                )

        try:
            as_int(row.get("priority", ""))
        except ValueError:
            errors.append(f"simple_dependency_rules {row_id or '<missing>'} has unsupported priority: {row.get('priority', '')}.")

        if row.get("target_option_id", "") and row.get("target_option_id", "") in self.selectables:
            condition_error = self._simple_dependency_condition_collision_error(row)
            if condition_error:
                errors.append(condition_error)

        return errors

    def _simple_dependency_condition_id(self, target_selectable_id: str) -> str:
        target = self.selectables[target_selectable_id]
        return f"cs_selected_{target['rpo'].lower()}"

    def _simple_dependency_condition_collision_error(self, row: dict[str, str]) -> str:
        target_id = row["target_option_id"]
        condition_set_id = self._simple_dependency_condition_id(target_id)
        existing_condition_sets = [
            item for item in self.tables["condition_sets"] if item.get("condition_set_id", "") == condition_set_id
        ]
        if not existing_condition_sets:
            return ""
        existing_terms = [
            term for term in self.tables["condition_terms"] if term.get("condition_set_id", "") == condition_set_id
        ]
        compatible = (
            len(existing_condition_sets) == 1
            and is_active(existing_condition_sets[0])
            and len(existing_terms) == 1
            and existing_terms[0].get("or_group", "") == "g1"
            and existing_terms[0].get("term_order", "") == "1"
            and existing_terms[0].get("term_type", "") == "selected"
            and existing_terms[0].get("left_ref", "") == target_id
            and existing_terms[0].get("operator", "") == "is_true"
            and existing_terms[0].get("right_value", "") == ""
            and existing_terms[0].get("negate", "") == "false"
        )
        if compatible:
            return ""
        return (
            f"simple_dependency_rules {row['rule_id']} generated condition_set_id {condition_set_id} "
            f"already exists but does not select {target_id}."
        )

    def _append_simple_dependency_rule(self, row: dict[str, str]) -> None:
        target_id = row["target_option_id"]
        condition_set_id = self._simple_dependency_condition_id(target_id)
        if not any(item.get("condition_set_id", "") == condition_set_id for item in self.tables["condition_sets"]):
            target_rpo = self.selectables[target_id]["rpo"]
            condition_set = {
                "condition_set_id": condition_set_id,
                "label": f"{target_rpo} selected",
                "description": "",
                "active": "true",
            }
            self.tables["condition_sets"].append(condition_set)
            self.condition_sets[condition_set_id] = condition_set
            self.tables["condition_terms"].append(
                {
                    "condition_set_id": condition_set_id,
                    "or_group": "g1",
                    "term_order": "1",
                    "term_type": "selected",
                    "left_ref": target_id,
                    "operator": "is_true",
                    "right_value": "",
                    "negate": "false",
                }
            )
        self.tables["dependency_rules"].append(
            {
                "rule_id": row["rule_id"],
                "rule_type": row["rule_type"],
                "subject_selector_type": "selectable",
                "subject_selector_id": row["source_option_id"],
                "subject_must_be_selected": "true",
                "applies_when_condition_set_id": "",
                "target_condition_set_id": condition_set_id,
                "violation_behavior": row["violation_behavior"],
                "message": row["message"],
                "priority": row["priority"],
                "active": row["active"],
            }
        )

    def _optional_table_field_errors(self, table_name: str) -> list[str]:
        fields = self.optional_table_fields.get(table_name, [])
        if not fields:
            return []
        expected = OPTIONAL_TABLE_FIELDS[table_name]
        if fields == expected:
            return []
        unexpected = [field for field in fields if field not in expected]
        missing = [field for field in expected if field not in fields]
        details = []
        if unexpected:
            details.append(f"unsupported columns: {', '.join(unexpected)}")
        if missing:
            details.append(f"missing columns: {', '.join(missing)}")
        return [f"{table_name}.csv uses {'; '.join(details)}."]

    def _final_canonical_table_field_errors(self, table_name: str) -> list[str]:
        fields = self.optional_table_fields.get(table_name, [])
        if not fields:
            return []
        expected = FINAL_CANONICAL_TABLE_FIELDS[table_name]
        if fields == expected:
            return []
        unexpected = [field for field in fields if field not in expected]
        missing = [field for field in expected if field not in fields]
        details = []
        if unexpected:
            details.append(f"unsupported columns: {', '.join(unexpected)}")
        if missing:
            details.append(f"missing columns: {', '.join(missing)}")
        return [f"{FINAL_CANONICAL_TABLES[table_name]} uses {'; '.join(details)}."]

    def _validate_active_value(self, table_path: str, row_id: str, row: dict[str, str]) -> bool:
        active = row.get("active", "")
        if active not in {"true", "false"}:
            self.canonical_namespace_errors.append(
                f"{table_path} {row_id or '<missing>'} uses unsupported active value: {active}."
            )
            return False
        return active == "true"

    def _validate_canonical_namespace_foundation(self) -> None:
        for table_name in FINAL_CANONICAL_TABLES:
            self.canonical_namespace_errors.extend(self._final_canonical_table_field_errors(table_name))
        if self.canonical_namespace_errors:
            return
        self._validate_unique_active_final_ids("final_canonical_variants", "canonical/status/variants", "variant_id")
        self._validate_unique_active_final_ids("final_context_scopes", "canonical/status/context_scopes", "context_scope_id")
        self._validate_unique_active_final_ids("final_price_books", "canonical/pricing/price_books", "price_book_id")
        self._validate_unique_active_final_ids(
            "final_canonical_base_prices",
            "canonical/pricing/canonical_base_prices",
            "canonical_base_price_id",
        )

        for row in self.tables["canonical_source_documents"]:
            row_id = row.get("source_document_id", "")
            if not row_id:
                self.canonical_namespace_errors.append("canonical/source/source_documents has a row missing source_document_id.")
            source_type = row.get("source_type", "")
            if source_type not in FINAL_CANONICAL_SOURCE_TYPES:
                self.canonical_namespace_errors.append(
                    f"canonical/source/source_documents {row_id or '<missing>'} uses unsupported source_type: {source_type}."
                )

        for row in self.tables["canonical_source_rows"]:
            row_id = row.get("source_row_id", "")
            if not self._validate_active_value("canonical/source/source_rows", row_id, row):
                continue
            if not row_id:
                self.canonical_namespace_errors.append("canonical/source/source_rows has a row missing source_row_id.")
            if not row.get("source_document_id", ""):
                self.canonical_namespace_errors.append(
                    f"canonical/source/source_rows {row_id or '<missing>'} is missing source_document_id."
                )
            if not row.get("raw_row_hash", ""):
                self.canonical_namespace_errors.append(
                    f"canonical/source/source_rows {row_id or '<missing>'} is missing raw_row_hash."
                )

        for row in self.tables["canonical_source_row_classifications"]:
            row_id = row.get("source_row_id", "")
            if not self._validate_active_value("canonical/source/source_row_classifications", row_id, row):
                continue
            if not row_id:
                self.canonical_namespace_errors.append(
                    "canonical/source/source_row_classifications has a row missing source_row_id."
                )
            classification = row.get("classification", "")
            if classification not in FINAL_CANONICAL_SOURCE_ROW_CLASSIFICATIONS:
                self.canonical_namespace_errors.append(
                    f"canonical/source/source_row_classifications {row_id or '<missing>'} uses unsupported classification: {classification}."
                )
            review_status = row.get("review_status", "")
            if review_status not in FINAL_CANONICAL_REVIEW_STATUSES:
                self.canonical_namespace_errors.append(
                    f"canonical/source/source_row_classifications {row_id or '<missing>'} uses unsupported review_status: {review_status}."
                )

        for row in self.tables["canonical_duplicate_rpo_reviews"]:
            row_id = row.get("duplicate_rpo_review_id", "")
            if not self._validate_active_value("canonical/options/duplicate_rpo_reviews", row_id, row):
                continue
            if not row_id:
                self.canonical_namespace_errors.append(
                    "canonical/options/duplicate_rpo_reviews has a row missing duplicate_rpo_review_id."
                )
            if not row.get("rpo", ""):
                self.canonical_namespace_errors.append(
                    f"canonical/options/duplicate_rpo_reviews {row_id or '<missing>'} is missing rpo."
                )
            classification = row.get("duplicate_rpo_classification", "")
            if classification not in FINAL_CANONICAL_DUPLICATE_RPO_CLASSIFICATIONS:
                self.canonical_namespace_errors.append(
                    f"canonical/options/duplicate_rpo_reviews {row_id or '<missing>'} uses unsupported duplicate_rpo_classification: {classification}."
                )
            review_status = row.get("review_status", "")
            if review_status not in FINAL_CANONICAL_REVIEW_STATUSES:
                self.canonical_namespace_errors.append(
                    f"canonical/options/duplicate_rpo_reviews {row_id or '<missing>'} uses unsupported review_status: {review_status}."
                )

        self._validate_final_canonical_variants()
        self._validate_final_context_scopes()
        self._validate_final_price_books()

    def _validate_unique_active_final_ids(self, table_name: str, table_path: str, id_field: str) -> None:
        seen: set[str] = set()
        for row in self.tables[table_name]:
            if not is_active(row):
                continue
            row_id = row.get(id_field, "")
            if not row_id:
                continue
            if row_id in seen:
                self.canonical_namespace_errors.append(f"{table_path} has duplicate active {id_field}: {row_id}.")
            seen.add(row_id)

    def _validate_final_canonical_variants(self) -> None:
        for row in self.tables["final_canonical_variants"]:
            row_id = row.get("variant_id", "")
            if not self._validate_active_value("canonical/status/variants", row_id, row):
                continue
            for field in ("variant_id", "model_year", "gm_model_code", "model_key", "body_style", "trim_level"):
                if not row.get(field, ""):
                    self.canonical_namespace_errors.append(
                        f"canonical/status/variants {row_id or '<missing>'} is missing {field}."
                    )
            gm_model_code = row.get("gm_model_code", "")
            if gm_model_code:
                model_prefix = gm_model_code[:1]
                body_suffix = gm_model_code[1:]
                expected_model_key = GM_MODEL_CODE_MODEL_KEYS.get(model_prefix)
                expected_body_style = GM_MODEL_CODE_BODY_STYLES.get(body_suffix)
                if len(gm_model_code) != 3 or not expected_model_key or not expected_body_style:
                    self.canonical_namespace_errors.append(
                        f"canonical/status/variants {row_id or '<missing>'} uses unsupported gm_model_code: {gm_model_code}."
                    )
                else:
                    if row.get("model_key", "") != expected_model_key:
                        self.canonical_namespace_errors.append(
                            f"canonical/status/variants {row_id or '<missing>'} gm_model_code {gm_model_code} contradicts model_key {row.get('model_key', '')}."
                        )
                    if row.get("body_style", "") != expected_body_style:
                        self.canonical_namespace_errors.append(
                            f"canonical/status/variants {row_id or '<missing>'} gm_model_code {gm_model_code} contradicts body_style {row.get('body_style', '')}."
                        )
                    expected_variant_id = f"{row.get('trim_level', '').lower()}_{gm_model_code.lower()}"
                    if row_id and row.get("trim_level", "") and row_id != expected_variant_id:
                        self.canonical_namespace_errors.append(
                            f"canonical/status/variants {row_id} does not match trim plus gm_model_code convention: {expected_variant_id}."
                        )

    def _validate_final_context_scopes(self) -> None:
        for row in self.tables["final_context_scopes"]:
            row_id = row.get("context_scope_id", "")
            if not self._validate_active_value("canonical/status/context_scopes", row_id, row):
                continue
            if not row_id:
                self.canonical_namespace_errors.append("canonical/status/context_scopes has a row missing context_scope_id.")
            for field in ("model_year", "model_key"):
                if not row.get(field, ""):
                    self.canonical_namespace_errors.append(
                        f"canonical/status/context_scopes {row_id or '<missing>'} is missing {field}."
                    )
            try:
                if as_int(row.get("priority", "")) < 0:
                    raise ValueError
            except ValueError:
                self.canonical_namespace_errors.append(
                    f"canonical/status/context_scopes {row_id or '<missing>'} has unsupported priority: {row.get('priority', '')}."
                )
            variant_id = row.get("variant_id", "")
            if variant_id:
                variant = self.final_canonical_variants.get(variant_id)
                if not variant:
                    self.canonical_namespace_errors.append(
                        f"canonical/status/context_scopes {row_id or '<missing>'} references missing variant_id: {variant_id}."
                    )
                    continue
                for field in ("model_year", "model_key", "body_style", "trim_level"):
                    expected = row.get(field, "")
                    if expected and expected != variant.get(field, ""):
                        self.canonical_namespace_errors.append(
                            f"canonical/status/context_scopes {row_id or '<missing>'} {field} contradicts variant {variant_id}."
                        )
            elif not self.final_context_scope_variant_ids(row):
                self.canonical_namespace_errors.append(
                    f"canonical/status/context_scopes {row_id or '<missing>'} resolves to no active variants."
                )

    def _validate_final_price_books(self) -> None:
        for row in self.tables["final_price_books"]:
            row_id = row.get("price_book_id", "")
            if not self._validate_active_value("canonical/pricing/price_books", row_id, row):
                continue
            for field in ("price_book_id", "model_year", "model_key", "currency"):
                if not row.get(field, ""):
                    self.canonical_namespace_errors.append(
                        f"canonical/pricing/price_books {row_id or '<missing>'} is missing {field}."
                    )
            if row.get("model_year", "") and row.get("model_key", "") and not self.final_price_book_variant_ids(row):
                self.canonical_namespace_errors.append(
                    f"canonical/pricing/price_books {row_id or '<missing>'} does not align with any active canonical variants."
                )

    def _validate_final_canonical_pricing(self) -> None:
        if self.canonical_namespace_errors:
            return
        for row in self.tables["final_canonical_base_prices"]:
            row_id = row.get("canonical_base_price_id", "")
            if not self._validate_active_value("canonical/pricing/canonical_base_prices", row_id, row):
                continue
            canonical_id = row.get("canonical_option_id", "")
            presentation_id = row.get("presentation_id", "")
            if not row_id:
                self.canonical_namespace_errors.append(
                    "canonical/pricing/canonical_base_prices has a row missing canonical_base_price_id."
                )
            if bool(canonical_id) == bool(presentation_id):
                self.canonical_namespace_errors.append(
                    f"canonical/pricing/canonical_base_prices {row_id or '<missing>'} must reference exactly one of canonical_option_id or presentation_id."
                )
            if canonical_id and canonical_id not in self.canonical_options:
                self.canonical_namespace_errors.append(
                    f"canonical/pricing/canonical_base_prices {row_id or '<missing>'} references missing canonical option: {canonical_id}."
                )
            if presentation_id and presentation_id not in self.option_presentations:
                self.canonical_namespace_errors.append(
                    f"canonical/pricing/canonical_base_prices {row_id or '<missing>'} references missing presentation: {presentation_id}."
                )
            price_book_id = row.get("price_book_id", "")
            price_book = self.final_price_books.get(price_book_id)
            if not price_book_id:
                self.canonical_namespace_errors.append(
                    f"canonical/pricing/canonical_base_prices {row_id or '<missing>'} is missing price_book_id."
                )
            elif not price_book:
                self.canonical_namespace_errors.append(
                    f"canonical/pricing/canonical_base_prices {row_id or '<missing>'} references missing price book: {price_book_id}."
                )
            context_scope_id = row.get("context_scope_id", "")
            if context_scope_id and context_scope_id not in self.final_context_scopes:
                self.canonical_namespace_errors.append(
                    f"canonical/pricing/canonical_base_prices {row_id or '<missing>'} references missing context scope: {context_scope_id}."
                )
            if price_book and not self.final_canonical_price_variant_ids(row):
                self.canonical_namespace_errors.append(
                    f"canonical/pricing/canonical_base_prices {row_id or '<missing>'} context does not align with price book {price_book_id}."
                )
            try:
                as_int(row.get("amount_usd", ""))
            except ValueError:
                self.canonical_namespace_errors.append(
                    f"canonical/pricing/canonical_base_prices {row_id or '<missing>'} has unsupported amount_usd: {row.get('amount_usd', '')}."
                )
            try:
                if as_int(row.get("priority", "")) < 0:
                    raise ValueError
            except ValueError:
                self.canonical_namespace_errors.append(
                    f"canonical/pricing/canonical_base_prices {row_id or '<missing>'} has unsupported priority: {row.get('priority', '')}."
                )

        self._validate_final_canonical_price_conflicts()

    def _validate_final_canonical_price_conflicts(self) -> None:
        seen: dict[tuple[str, str, str, frozenset[str], int, int], dict[str, str]] = {}
        for row in self.final_canonical_base_prices:
            try:
                priority = as_int(row.get("priority", ""))
            except ValueError:
                continue
            target_type = "presentation" if row.get("presentation_id", "") else "canonical"
            target_id = row.get("presentation_id", "") or row.get("canonical_option_id", "")
            variants = frozenset(self.final_canonical_price_variant_ids(row))
            if not target_id or not variants:
                continue
            key = (
                target_type,
                target_id,
                row.get("price_book_id", ""),
                variants,
                self.final_canonical_price_scope_specificity(row),
                priority,
            )
            prior = seen.get(key)
            if prior and prior.get("amount_usd", "") != row.get("amount_usd", ""):
                self.canonical_namespace_errors.append(
                    "canonical/pricing/canonical_base_prices "
                    f"{prior.get('canonical_base_price_id', '')} and {row.get('canonical_base_price_id', '')} "
                    "have conflicting same-priority prices for the same target and effective context."
                )
            else:
                seen[key] = row

    def final_context_scope_variant_ids(self, scope: dict[str, str]) -> set[str]:
        variant_id = scope.get("variant_id", "")
        if variant_id:
            return {variant_id} if variant_id in self.final_canonical_variants else set()
        variants = set()
        for candidate_id, variant in self.final_canonical_variants.items():
            if scope.get("model_year", "") and variant.get("model_year", "") != scope["model_year"]:
                continue
            if scope.get("model_key", "") and variant.get("model_key", "") != scope["model_key"]:
                continue
            if scope.get("body_style", "") and variant.get("body_style", "") != scope["body_style"]:
                continue
            if scope.get("trim_level", "") and variant.get("trim_level", "") != scope["trim_level"]:
                continue
            variants.add(candidate_id)
        return variants

    def final_price_book_variant_ids(self, price_book: dict[str, str]) -> set[str]:
        return {
            variant_id
            for variant_id, variant in self.final_canonical_variants.items()
            if variant.get("model_year", "") == price_book.get("model_year", "")
            and variant.get("model_key", "") == price_book.get("model_key", "")
        }

    def final_canonical_price_variant_ids(self, row: dict[str, str]) -> set[str]:
        price_book = self.final_price_books.get(row.get("price_book_id", ""))
        if not price_book:
            return set()
        price_book_variants = self.final_price_book_variant_ids(price_book)
        context_scope_id = row.get("context_scope_id", "")
        if not context_scope_id:
            return price_book_variants
        scope = self.final_context_scopes.get(context_scope_id)
        if not scope:
            return set()
        return price_book_variants & self.final_context_scope_variant_ids(scope)

    def final_canonical_price_scope_specificity(self, row: dict[str, str]) -> int:
        context_scope_id = row.get("context_scope_id", "")
        if not context_scope_id:
            return 0
        scope = self.final_context_scopes.get(context_scope_id, {})
        if scope.get("variant_id", ""):
            return 4
        if scope.get("body_style", "") and scope.get("trim_level", ""):
            return 3
        if scope.get("body_style", "") or scope.get("trim_level", ""):
            return 2
        return 1

    def context_model_key(self, context: dict[str, str]) -> str:
        if context.get("model_key", ""):
            return context["model_key"]
        variant = self.variants.get(context.get("variant_id", ""), {})
        return variant.get("model_key", "")

    def final_price_book_matches_context(self, price_book_id: str, context: dict[str, str]) -> bool:
        price_book = self.final_price_books.get(price_book_id, {})
        if not price_book:
            return False
        if context.get("model_year", "") and price_book.get("model_year", "") != context.get("model_year", ""):
            return False
        model_key = self.context_model_key(context)
        return not model_key or price_book.get("model_key", "") == model_key

    def final_context_scope_matches_context(self, context_scope_id: str, context: dict[str, str]) -> bool:
        if not context_scope_id:
            return True
        scope = self.final_context_scopes.get(context_scope_id, {})
        if not scope:
            return False
        if scope.get("variant_id", "") and context.get("variant_id", "") != scope["variant_id"]:
            return False
        if scope.get("model_year", "") and context.get("model_year", "") != scope["model_year"]:
            return False
        if scope.get("model_key", "") and self.context_model_key(context) != scope["model_key"]:
            return False
        if scope.get("body_style", "") and context.get("body_style", "") != scope["body_style"]:
            return False
        if scope.get("trim_level", "") and context.get("trim_level", "") != scope["trim_level"]:
            return False
        return True

    def _merge_canonical_presentations(self) -> None:
        for table_name in ("canonical_options", "option_presentations", "option_status_rules", "canonical_base_prices"):
            self.canonical_option_errors.extend(self._optional_table_field_errors(table_name))
        if self.canonical_option_errors:
            return
        if not (self.canonical_options or self.option_presentations or self.option_status_rules or self.canonical_base_prices):
            return

        existing_selectable_ids = {row.get("selectable_id", "") for row in self.tables["selectables"] if is_active(row)}
        existing_condition_set_ids = {
            row.get("condition_set_id", "") for row in self.tables["condition_sets"] if is_active(row)
        }
        existing_price_book_ids = {
            row.get("price_book_id", "") for row in self.tables["price_books"] if is_active(row)
        }
        presentation_ids_by_canonical: dict[str, list[str]] = defaultdict(list)
        legacy_ids: dict[str, str] = {}

        for row in self.tables["canonical_options"]:
            row_id = row.get("canonical_option_id", "")
            if row.get("active", "").lower() not in {"true", "false"}:
                self.canonical_option_errors.append(
                    f"canonical_options {row_id or '<missing>'} uses unsupported active value: {row.get('active', '')}."
                )
                continue
            if not is_active(row):
                continue
            if not row_id:
                self.canonical_option_errors.append("canonical_options has a row missing canonical_option_id.")
            if not row.get("rpo", ""):
                self.canonical_option_errors.append(f"canonical_options {row_id or '<missing>'} is missing rpo.")
            if row.get("canonical_kind", "") not in CANONICAL_OPTION_KINDS:
                self.canonical_option_errors.append(
                    f"canonical_options {row_id or '<missing>'} uses unsupported canonical_kind: {row.get('canonical_kind', '')}."
                )
            if row.get("canonical_kind", "") == "display_only":
                self.canonical_option_errors.append(
                    f"canonical_options {row_id or '<missing>'} cannot use display_only as a canonical business status."
                )
            if row.get("rpo", "") in REVIEW_REQUIRED_DUPLICATE_RPOS:
                self.canonical_option_errors.append(
                    f"canonical_options {row_id or '<missing>'} uses duplicate RPO {row.get('rpo', '')}, "
                    "which requires explicit review and cannot be auto-collapsed."
                )

        for row in self.tables["option_presentations"]:
            row_id = row.get("presentation_id", "")
            if row.get("active", "").lower() not in {"true", "false"}:
                self.canonical_option_errors.append(
                    f"option_presentations {row_id or '<missing>'} uses unsupported active value: {row.get('active', '')}."
                )
                continue
            if not is_active(row):
                continue
            canonical_id = row.get("canonical_option_id", "")
            legacy_id = row.get("legacy_option_id", "")
            presentation_role = row.get("presentation_role", "")
            if not row_id:
                self.canonical_option_errors.append("option_presentations has a row missing presentation_id.")
            if canonical_id not in self.canonical_options:
                self.canonical_option_errors.append(
                    f"option_presentations {row_id or '<missing>'} references missing canonical option: {canonical_id}."
                )
            if not legacy_id:
                self.canonical_option_errors.append(f"option_presentations {row_id or '<missing>'} is missing legacy_option_id.")
            elif legacy_id in existing_selectable_ids:
                self.canonical_option_errors.append(
                    f"option_presentations {row_id or '<missing>'} legacy_option_id collides with active selectables.csv row: {legacy_id}."
                )
            elif legacy_id in legacy_ids:
                self.canonical_option_errors.append(
                    f"option_presentations {row_id or '<missing>'} duplicate legacy_option_id {legacy_id} also used by {legacy_ids[legacy_id]}."
                )
            else:
                legacy_ids[legacy_id] = row_id
            if presentation_role not in PRESENTATION_ROLES:
                self.canonical_option_errors.append(
                    f"option_presentations {row_id or '<missing>'} uses unsupported presentation_role: {presentation_role}."
                )
            if presentation_role == "choice" and row.get("selection_mode", "") == "display_only":
                self.canonical_option_errors.append(
                    f"option_presentations {row_id or '<missing>'} cannot use display_only selection_mode for a choice presentation."
                )
            if presentation_role != "choice" and row.get("selectable", "") == "True":
                self.canonical_option_errors.append(
                    f"option_presentations {row_id or '<missing>'} display presentation must not be selectable."
                )
            try:
                as_int(row.get("display_order", ""))
            except ValueError:
                self.canonical_option_errors.append(
                    f"option_presentations {row_id or '<missing>'} has unsupported display_order: {row.get('display_order', '')}."
                )
            if canonical_id:
                presentation_ids_by_canonical[canonical_id].append(row_id)

        for canonical_id, presentation_ids in presentation_ids_by_canonical.items():
            choice_presentations = [
                self.option_presentations[presentation_id]
                for presentation_id in presentation_ids
                if self.option_presentations[presentation_id].get("presentation_role", "") == "choice"
                and self.option_presentations[presentation_id].get("selectable", "") == "True"
            ]
            if len(choice_presentations) > 1:
                canonical = self.canonical_options.get(canonical_id, {})
                ids = ", ".join(row["presentation_id"] for row in choice_presentations)
                self.canonical_option_errors.append(
                    f"canonical_options {canonical_id} would auto-collapse multiple selectable choices for RPO {canonical.get('rpo', '')}: {ids}."
                )

        for row in self.tables["option_status_rules"]:
            row_id = row.get("status_rule_id", "")
            if row.get("active", "").lower() not in {"true", "false"}:
                self.canonical_option_errors.append(
                    f"option_status_rules {row_id or '<missing>'} uses unsupported active value: {row.get('active', '')}."
                )
                continue
            if not is_active(row):
                continue
            canonical_id = row.get("canonical_option_id", "")
            presentation_id = row.get("presentation_id", "")
            if not row_id:
                self.canonical_option_errors.append("option_status_rules has a row missing status_rule_id.")
            if not (canonical_id or presentation_id):
                self.canonical_option_errors.append(
                    f"option_status_rules {row_id or '<missing>'} must reference canonical_option_id or presentation_id."
                )
            if canonical_id and canonical_id not in self.canonical_options:
                self.canonical_option_errors.append(
                    f"option_status_rules {row_id or '<missing>'} references missing canonical option: {canonical_id}."
                )
            if presentation_id and presentation_id not in self.option_presentations:
                self.canonical_option_errors.append(
                    f"option_status_rules {row_id or '<missing>'} references missing presentation: {presentation_id}."
                )
            if canonical_id and presentation_id:
                presentation = self.option_presentations.get(presentation_id, {})
                if presentation and presentation.get("canonical_option_id", "") != canonical_id:
                    self.canonical_option_errors.append(
                        f"option_status_rules {row_id or '<missing>'} canonical_option_id does not match presentation {presentation_id}."
                    )
            status = row.get("status", "")
            if status not in OPTION_STATUSES:
                self.canonical_option_errors.append(
                    f"option_status_rules {row_id or '<missing>'} uses unsupported status: {status}."
                )
            if status == "display_only":
                self.canonical_option_errors.append(
                    f"option_status_rules {row_id or '<missing>'} cannot use display_only as a business status."
                )
            condition_set_id = row.get("condition_set_id", "")
            if condition_set_id and condition_set_id not in existing_condition_set_ids:
                self.canonical_option_errors.append(
                    f"option_status_rules {row_id or '<missing>'} references missing condition set: {condition_set_id}."
                )
            try:
                as_int(row.get("priority", ""))
            except ValueError:
                self.canonical_option_errors.append(
                    f"option_status_rules {row_id or '<missing>'} has unsupported priority: {row.get('priority', '')}."
                )

        for row in self.tables["canonical_base_prices"]:
            row_id = row.get("canonical_base_price_id", "")
            if row.get("active", "").lower() not in {"true", "false"}:
                self.canonical_option_errors.append(
                    f"canonical_base_prices {row_id or '<missing>'} uses unsupported active value: {row.get('active', '')}."
                )
                continue
            if not is_active(row):
                continue
            canonical_id = row.get("canonical_option_id", "")
            presentation_id = row.get("presentation_id", "")
            if not row_id:
                self.canonical_option_errors.append("canonical_base_prices has a row missing canonical_base_price_id.")
            if bool(canonical_id) == bool(presentation_id):
                self.canonical_option_errors.append(
                    f"canonical_base_prices {row_id or '<missing>'} must reference exactly one of canonical_option_id or presentation_id."
                )
            if canonical_id and canonical_id not in self.canonical_options:
                self.canonical_option_errors.append(
                    f"canonical_base_prices {row_id or '<missing>'} references missing canonical option: {canonical_id}."
                )
            if presentation_id and presentation_id not in self.option_presentations:
                self.canonical_option_errors.append(
                    f"canonical_base_prices {row_id or '<missing>'} references missing presentation: {presentation_id}."
                )
            price_book_id = row.get("price_book_id", "")
            if price_book_id and price_book_id not in existing_price_book_ids:
                self.canonical_option_errors.append(
                    f"canonical_base_prices {row_id or '<missing>'} references missing price book: {price_book_id}."
                )
            condition_set_id = row.get("scope_condition_set_id", "")
            if condition_set_id and condition_set_id not in existing_condition_set_ids:
                self.canonical_option_errors.append(
                    f"canonical_base_prices {row_id or '<missing>'} references missing condition set: {condition_set_id}."
                )
            try:
                as_int(row.get("amount_usd", ""))
            except ValueError:
                self.canonical_option_errors.append(
                    f"canonical_base_prices {row_id or '<missing>'} has unsupported amount_usd: {row.get('amount_usd', '')}."
                )
            try:
                as_int(row.get("priority", ""))
            except ValueError:
                self.canonical_option_errors.append(
                    f"canonical_base_prices {row_id or '<missing>'} has unsupported priority: {row.get('priority', '')}."
                )

        if self.canonical_option_errors:
            return

        for row in sorted(self.option_presentations.values(), key=lambda item: item["presentation_id"]):
            canonical = self.canonical_options[row["canonical_option_id"]]
            legacy_id = row["legacy_option_id"]
            self.tables["selectables"].append(
                {
                    "selectable_id": legacy_id,
                    "selectable_type": "option",
                    "rpo": row.get("rpo_override", "") or canonical["rpo"],
                    "label": row.get("label", "") or canonical["label"],
                    "description": row.get("description", "") or canonical["description"],
                    "active": row["active"],
                    "availability_condition_set_id": "",
                    "notes": row.get("notes", "") or f"Canonical presentation {row['presentation_id']}.",
                }
            )
            self.tables["selectable_display"].append(
                {
                    "selectable_id": legacy_id,
                    "legacy_option_id": legacy_id,
                    "section_id": row["section_id"],
                    "section_name": row["section_name"],
                    "category_id": row["category_id"],
                    "category_name": row["category_name"],
                    "step_key": row["step_key"],
                    "choice_mode": row["choice_mode"],
                    "selection_mode": row["selection_mode"],
                    "selection_mode_label": row["selection_mode_label"],
                    "display_order": row["display_order"],
                    "selectable": row["selectable"],
                    "active": row["active"],
                    "status_condition_set_id": "",
                    "status_when_matched": "optional",
                    "status_label_when_matched": "Available",
                    "status_when_unmatched": "optional",
                    "status_label_when_unmatched": "Available",
                    "label": row.get("label", "") or canonical["label"],
                    "description": row.get("description", "") or canonical["description"],
                    "source_detail_raw": row.get("source_detail_raw", ""),
                    "canonical_option_id": row["canonical_option_id"],
                    "presentation_id": row["presentation_id"],
                    "presentation_role": row["presentation_role"],
                }
            )

    def validate(self) -> list[str]:
        errors: list[str] = []
        errors.extend(self.canonical_namespace_errors)
        errors.extend(self.canonical_option_errors)
        errors.extend(self.simple_dependency_rule_errors)
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
            if term_type == "reference_selected":
                self._validate_non_selectable_reference_ref(errors, "condition_terms", left_ref)
            if not self.supports_condition_term(term_type, row["operator"]):
                errors.append(f"condition term uses unsupported type/operator: {term_type}/{row['operator']}.")

        for row in self.non_selectable_references.values():
            option_id = row.get("option_id", "")
            if option_id and option_id in self.selectables and row.get("projection_policy", "") == "never_project_as_selectable":
                errors.append(f"non-selectable reference is also a selectable: {option_id}.")

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
            self._validate_dependency_reference_legacy_metadata(errors, row)

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
        elif selector_type == "non_selectable_reference":
            if table_name != "dependency_rules":
                errors.append(f"{table_name} uses unsupported selector type: {selector_type}.")
            else:
                self._validate_non_selectable_reference_ref(errors, table_name, selector_id)
        else:
            errors.append(f"{table_name} uses unsupported selector type: {selector_type}.")

    def _validate_non_selectable_reference_ref(self, errors: list[str], table_name: str, reference_selector_id: str) -> None:
        if reference_selector_id not in self.non_selectable_reference_selectors:
            errors.append(f"{table_name} references unknown non-selectable reference: {reference_selector_id}.")

    def _validate_dependency_reference_legacy_metadata(self, errors: list[str], row: dict[str, str]) -> None:
        target_id = self.condition_selected_selectable(row.get("target_condition_set_id", ""))
        if not target_id:
            return
        source_ids = self.selector_selectable_ids(row["subject_selector_type"], row["subject_selector_id"])
        if not source_ids:
            return
        for option_id in source_ids + [target_id]:
            reference = self.reference_for_option_id(option_id)
            if not reference:
                continue
            missing_fields = [
                field
                for field in ("legacy_section_id", "legacy_selection_mode")
                if not reference.get(field, "")
            ]
            if missing_fields:
                missing_description = " and ".join(f"missing {field}" for field in missing_fields)
                errors.append(
                    f"dependency_rules {row['rule_id']} uses non-selectable reference {option_id} "
                    f"{missing_description}."
                )

    def supports_condition_term(self, term_type: str, operator: str) -> bool:
        return (term_type, operator) in {
            ("context", "eq"),
            ("selected", "is_true"),
            ("selected_any_in_set", "is_true"),
            ("reference_selected", "is_true"),
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
                "model_key": variant["model_key"],
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
        if selector_type == "non_selectable_reference":
            option_id = self.non_selectable_reference_option_id(selector_id)
            return selector_id in selected or bool(option_id and option_id in selected)
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
        elif term_type == "reference_selected" and operator == "is_true":
            option_id = self.non_selectable_reference_option_id(left_ref)
            matched = left_ref in selected or bool(option_id and option_id in selected)
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
        exact_selectable_candidates = [
            row
            for row in self.tables["base_prices"]
            if is_active(row)
            and row["target_selector_type"] == "selectable"
            and self.selector_targets_selectable(row["target_selector_type"], row["target_selector_id"], selectable_id)
            and (not row["scope_condition_set_id"] or self.condition_matches(row["scope_condition_set_id"], context, selected))
        ]
        exact_selectable_candidates.sort(key=lambda row: as_int(row["priority"]), reverse=True)
        if exact_selectable_candidates:
            return {
                "base_price_id": exact_selectable_candidates[0]["base_price_id"],
                "amount_usd": as_int(exact_selectable_candidates[0]["amount_usd"]),
            }

        display = self.display_row(selectable_id)
        presentation_id = display.get("presentation_id", "")
        canonical_id = display.get("canonical_option_id", "")
        final_presentation_candidates = [
            row
            for row in self.final_canonical_base_prices
            if presentation_id
            and row.get("presentation_id", "") == presentation_id
            and self.final_price_book_matches_context(row.get("price_book_id", ""), context)
            and self.final_context_scope_matches_context(row.get("context_scope_id", ""), context)
        ]
        self.sort_final_canonical_price_candidates(final_presentation_candidates)
        if final_presentation_candidates:
            return {
                "base_price_id": final_presentation_candidates[0]["canonical_base_price_id"],
                "amount_usd": as_int(final_presentation_candidates[0]["amount_usd"]),
            }

        presentation_candidates = [
            row
            for row in self.canonical_base_prices
            if presentation_id
            and row.get("presentation_id", "") == presentation_id
            and (not row["scope_condition_set_id"] or self.condition_matches(row["scope_condition_set_id"], context, selected))
        ]
        presentation_candidates.sort(key=lambda row: as_int(row["priority"]), reverse=True)
        if presentation_candidates:
            return {
                "base_price_id": presentation_candidates[0]["canonical_base_price_id"],
                "amount_usd": as_int(presentation_candidates[0]["amount_usd"]),
            }

        final_canonical_candidates = [
            row
            for row in self.final_canonical_base_prices
            if canonical_id
            and row.get("canonical_option_id", "") == canonical_id
            and self.final_price_book_matches_context(row.get("price_book_id", ""), context)
            and self.final_context_scope_matches_context(row.get("context_scope_id", ""), context)
        ]
        self.sort_final_canonical_price_candidates(final_canonical_candidates)
        if final_canonical_candidates:
            return {
                "base_price_id": final_canonical_candidates[0]["canonical_base_price_id"],
                "amount_usd": as_int(final_canonical_candidates[0]["amount_usd"]),
            }

        canonical_candidates = [
            row
            for row in self.canonical_base_prices
            if canonical_id
            and row.get("canonical_option_id", "") == canonical_id
            and (not row["scope_condition_set_id"] or self.condition_matches(row["scope_condition_set_id"], context, selected))
        ]
        canonical_candidates.sort(key=lambda row: as_int(row["priority"]), reverse=True)
        if canonical_candidates:
            return {
                "base_price_id": canonical_candidates[0]["canonical_base_price_id"],
                "amount_usd": as_int(canonical_candidates[0]["amount_usd"]),
            }

        broader_candidates = [
            row
            for row in self.tables["base_prices"]
            if is_active(row)
            and row["target_selector_type"] != "selectable"
            and self.selector_targets_selectable(row["target_selector_type"], row["target_selector_id"], selectable_id)
            and (not row["scope_condition_set_id"] or self.condition_matches(row["scope_condition_set_id"], context, selected))
        ]
        broader_candidates.sort(key=lambda row: as_int(row["priority"]), reverse=True)
        if not broader_candidates:
            return {"base_price_id": None, "amount_usd": 0}
        return {
            "base_price_id": broader_candidates[0]["base_price_id"],
            "amount_usd": as_int(broader_candidates[0]["amount_usd"]),
        }

    def sort_final_canonical_price_candidates(self, rows: list[dict[str, str]]) -> None:
        rows.sort(
            key=lambda row: (
                -self.final_canonical_price_scope_specificity(row),
                -as_int(row.get("priority", "")),
                row.get("canonical_base_price_id", ""),
            )
        )

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
                        "base_price": self.legacy_base_price(selectable_id, context),
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
        source_display = self.display_or_reference_row(source_selectable_id)
        target_display = self.display_or_reference_row(target_selectable_id)
        rule_type = row["rule_type"]
        if rule_type == "requires":
            scoped_direct_selectable = row["subject_selector_type"] == "selectable" and row.get("applies_when_condition_set_id", "")
            target_type = "option" if scoped_direct_selectable else "main"
            source_type = "option" if scoped_direct_selectable else "main"
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
        if selector_type == "non_selectable_reference":
            option_id = self.non_selectable_reference_option_id(selector_id)
            return [option_id] if option_id else []
        return []

    def condition_selected_selectable(self, condition_set_id: str) -> str:
        selected_terms = [
            term["left_ref"]
            for term in self.condition_terms.get(condition_set_id, [])
            if term["term_type"] == "selected" and term["operator"] == "is_true" and not as_bool(term.get("negate", ""))
        ]
        reference_terms = [
            self.non_selectable_reference_option_id(term["left_ref"])
            for term in self.condition_terms.get(condition_set_id, [])
            if term["term_type"] == "reference_selected" and term["operator"] == "is_true" and not as_bool(term.get("negate", ""))
        ]
        endpoint_terms = selected_terms + [term for term in reference_terms if term]
        return endpoint_terms[0] if len(endpoint_terms) == 1 else ""

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
        if display.get("presentation_id", ""):
            return self.canonical_presentation_status(display, context)
        condition_set_id = display.get("status_condition_set_id", "")
        matched = True if not condition_set_id else self.condition_matches(condition_set_id, context, set())
        if matched:
            return display["status_when_matched"], display["status_label_when_matched"]
        return display["status_when_unmatched"], display["status_label_when_unmatched"]

    def canonical_presentation_status(self, display: dict[str, str], context: dict[str, str]) -> tuple[str, str]:
        canonical_id = display.get("canonical_option_id", "")
        presentation_id = display.get("presentation_id", "")
        candidates = [
            row
            for row in self.option_status_rules
            if self.option_status_rule_targets(row, canonical_id, presentation_id)
            and self.option_status_rule_matches_context(row, context)
        ]
        candidates.sort(
            key=lambda row: (
                self.option_status_rule_specificity(row),
                as_int(row.get("priority", "")),
                row.get("status_rule_id", ""),
            ),
            reverse=True,
        )
        if candidates:
            row = candidates[0]
            status = row["status"]
            return self.legacy_status_value(status), row.get("status_label", "") or self.default_status_label(status)
        return display["status_when_matched"], display["status_label_when_matched"]

    def option_status_rule_targets(self, row: dict[str, str], canonical_id: str, presentation_id: str) -> bool:
        if row.get("presentation_id", ""):
            return row["presentation_id"] == presentation_id
        return row.get("canonical_option_id", "") == canonical_id

    def option_status_rule_matches_context(self, row: dict[str, str], context: dict[str, str]) -> bool:
        scoped_fields = {
            "scope_model_year": "model_year",
            "scope_body_style": "body_style",
            "scope_trim_level": "trim_level",
            "scope_variant_id": "variant_id",
        }
        for rule_field, context_field in scoped_fields.items():
            expected = row.get(rule_field, "")
            if expected and context.get(context_field, "") != expected:
                return False
        condition_set_id = row.get("condition_set_id", "")
        if condition_set_id and not self.condition_matches(condition_set_id, context, set()):
            return False
        return True

    def option_status_rule_specificity(self, row: dict[str, str]) -> int:
        scoped_count = sum(
            1
            for field in ("scope_model_year", "scope_body_style", "scope_trim_level", "scope_variant_id", "condition_set_id")
            if row.get(field, "")
        )
        presentation_bonus = 10 if row.get("presentation_id", "") else 0
        return presentation_bonus + scoped_count

    def default_status_label(self, status: str) -> str:
        return {
            "optional": "Available",
            "standard_choice": "Standard",
            "standard_fixed": "Standard",
            "included_auto": "Included",
            "unavailable": "Not Available",
        }.get(status, status)

    def legacy_status_value(self, status: str) -> str:
        return {
            "optional": "available",
            "standard_choice": "standard",
            "standard_fixed": "standard",
            "included_auto": "available",
            "unavailable": "unavailable",
        }.get(status, status)

    def legacy_base_price(self, selectable_id: str, context: dict[str, str] | None = None) -> int:
        exact_selectable_candidates = [
            row
            for row in self.tables["base_prices"]
            if is_active(row)
            and row["target_selector_type"] == "selectable"
            and self.selector_targets_selectable(row["target_selector_type"], row["target_selector_id"], selectable_id)
        ]
        exact_selectable_candidates.sort(key=lambda row: as_int(row["priority"]), reverse=True)
        if exact_selectable_candidates:
            return as_int(exact_selectable_candidates[0]["amount_usd"])

        display = self.display_row(selectable_id)
        presentation_id = display.get("presentation_id", "")
        canonical_id = display.get("canonical_option_id", "")
        if context is not None:
            final_presentation_candidates = [
                row
                for row in self.final_canonical_base_prices
                if presentation_id
                and row.get("presentation_id", "") == presentation_id
                and self.final_price_book_matches_context(row.get("price_book_id", ""), context)
                and self.final_context_scope_matches_context(row.get("context_scope_id", ""), context)
            ]
            self.sort_final_canonical_price_candidates(final_presentation_candidates)
            if final_presentation_candidates:
                return as_int(final_presentation_candidates[0]["amount_usd"])

        presentation_candidates = [
            row
            for row in self.canonical_base_prices
            if presentation_id and row.get("presentation_id", "") == presentation_id
        ]
        presentation_candidates.sort(key=lambda row: as_int(row["priority"]), reverse=True)
        if presentation_candidates:
            return as_int(presentation_candidates[0]["amount_usd"])

        if context is not None:
            final_canonical_candidates = [
                row
                for row in self.final_canonical_base_prices
                if canonical_id
                and row.get("canonical_option_id", "") == canonical_id
                and self.final_price_book_matches_context(row.get("price_book_id", ""), context)
                and self.final_context_scope_matches_context(row.get("context_scope_id", ""), context)
            ]
            self.sort_final_canonical_price_candidates(final_canonical_candidates)
            if final_canonical_candidates:
                return as_int(final_canonical_candidates[0]["amount_usd"])

        canonical_candidates = [
            row
            for row in self.canonical_base_prices
            if canonical_id and row.get("canonical_option_id", "") == canonical_id
        ]
        canonical_candidates.sort(key=lambda row: as_int(row["priority"]), reverse=True)
        if canonical_candidates:
            return as_int(canonical_candidates[0]["amount_usd"])

        broader_candidates = [
            row
            for row in self.tables["base_prices"]
            if is_active(row)
            and row["target_selector_type"] != "selectable"
            and self.selector_targets_selectable(row["target_selector_type"], row["target_selector_id"], selectable_id)
        ]
        broader_candidates.sort(key=lambda row: as_int(row["priority"]), reverse=True)
        return as_int(broader_candidates[0]["amount_usd"]) if broader_candidates else 0

    def display_row(self, selectable_id: str) -> dict[str, str]:
        return self.selectable_display.get(selectable_id, {})

    def display_or_reference_row(self, selectable_or_reference_option_id: str) -> dict[str, str]:
        display = self.display_row(selectable_or_reference_option_id)
        if display:
            return display
        reference = self.reference_for_option_id(selectable_or_reference_option_id)
        if reference:
            return {
                "section_id": reference.get("legacy_section_id", ""),
                "selection_mode": reference.get("legacy_selection_mode", ""),
                "source_detail_raw": reference.get("notes", ""),
            }
        return {}

    def legacy_option_id(self, selectable_id: str) -> str:
        return self.display_row(selectable_id).get("legacy_option_id") or selectable_id

    def reference_for_option_id(self, option_id: str) -> dict[str, str]:
        for row in self.non_selectable_references.values():
            if row.get("option_id", "") == option_id:
                return row
        return {}

    def non_selectable_reference_option_id(self, reference_selector_id: str) -> str:
        return self.non_selectable_reference_selectors.get(reference_selector_id, {}).get("option_id", "")


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
