#!/usr/bin/env python3
"""Build an experimental shadow data object with projected CSV slices overlaid."""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from pathlib import Path
from typing import Any, Callable

from stingray_csv_first_slice import DEFAULT_PACKAGE, CsvSlice


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PRODUCTION_DATA = ROOT / "form-app" / "data.js"
DEFAULT_OWNERSHIP_MANIFEST = DEFAULT_PACKAGE / "validation" / "projected_slice_ownership.csv"
SUPPORTED_OWNERSHIP_VALUES = {"projected_owned", "preserved_cross_boundary", "production_guarded"}
GROUP_RECORD_TYPES = {"exclusiveGroup", "ruleGroup"}
SUPPORTED_RECORD_TYPES = {"selectable", "guardedOption", "rule", "priceRule", "ruleGroup", "exclusiveGroup"}
STRUCTURED_REF_NAMESPACE_ORDER = {
    "active_choice": 0,
    "production_guarded": 1,
    "interior_source": 2,
    "unresolved": 3,
}
UNRESOLVED_STRUCTURED_REF_NOTE = (
    "Structured reference does not resolve to an active choice, production_guarded option, or interior source."
)
PRODUCTION_GUARDED_PRESERVED_NOTE = "Production-guarded structured reference has active preserved_cross_boundary manifest evidence."
PRODUCTION_GUARDED_REVIEW_NOTE = "Production-guarded structured reference needs review before any migration decision."
PRESERVED_CROSS_BOUNDARY_MATCH_NOTE = "Production-guarded structured reference is backed by active preserved_cross_boundary manifest evidence."
PRESERVED_CROSS_BOUNDARY_STALE_NOTE = "Active preserved_cross_boundary manifest row points at a guarded ID with no current structured reference."
PRESERVED_CROSS_BOUNDARY_INVALID_NOTE = "Active preserved_cross_boundary manifest row points outside the guarded structured-reference contract."
PRESERVED_CROSS_BOUNDARY_UNGUARDED_NOTE = "Production-guarded structured reference has no matching active preserved_cross_boundary manifest evidence."
DIRECTION_SLICE_ROWS_CSV_FIELDS = [
    "direction_key",
    "manifest_row_id",
    "group_key",
    "ref_id",
    "pair_key",
    "source_id",
    "source_label",
    "source_category",
    "source_section",
    "source_ownership_status",
    "source_projection_status",
    "target_id",
    "target_label",
    "target_category",
    "target_section",
    "target_ownership_status",
    "target_projection_status",
    "candidate_status",
]
DECISION_LEDGER_CSV_FIELDS = [
    "group_key",
    "direction_key",
    "manifest_only_preservation_row_count",
    "manifest_only_preservation_record_count",
    "source_ids",
    "source_labels",
    "source_categories",
    "source_sections",
    "source_ownership_statuses",
    "source_projection_statuses",
    "target_ids",
    "target_labels",
    "target_categories",
    "target_sections",
    "target_ownership_statuses",
    "target_projection_statuses",
    "manifest_row_ids",
    "review_status",
    "reviewer",
    "reviewed_at",
    "decision",
    "decision_reason",
    "followup_action",
    "notes",
]
DECISION_LEDGER_REVIEW_FIELDS = [
    "review_status",
    "reviewer",
    "reviewed_at",
    "decision",
    "decision_reason",
    "followup_action",
    "notes",
]
DECISION_LEDGER_CONTEXT_FIELDS = [
    field for field in DECISION_LEDGER_CSV_FIELDS if field not in DECISION_LEDGER_REVIEW_FIELDS
]
DECISION_LEDGER_ALLOWED_REVIEW_STATUS = {"", "pending", "reviewed"}
DECISION_LEDGER_ALLOWED_DECISION = {"", "preserve", "migrate_later", "needs_research", "remove_preservation"}
DECISION_LEDGER_ALLOWED_FOLLOWUP_ACTION = {"", "none", "open_question", "create_pass_spec", "defer"}


class OverlayError(ValueError):
    pass


class OwnershipScope:
    def __init__(
        self,
        owned_rpos: set[str],
        guarded_option_refs: set[tuple[str, str]],
        preserved_cross_boundary_records: set[tuple[str, str, str, str, str]],
        preserved_cross_boundary_rows: list[dict[str, str]],
        guarded_group_ids: dict[str, set[str]],
        preserved_group_ids: dict[str, set[str]],
        projected_group_ids: dict[str, set[str]],
    ) -> None:
        self.owned_rpos = owned_rpos
        self.guarded_option_refs = guarded_option_refs
        self.preserved_cross_boundary_records = preserved_cross_boundary_records
        self.preserved_cross_boundary_rows = preserved_cross_boundary_rows
        self.guarded_group_ids = guarded_group_ids
        self.preserved_group_ids = preserved_group_ids
        self.projected_group_ids = projected_group_ids


def clone(value: Any) -> Any:
    return json.loads(json.dumps(value))


def load_production_data(path: Path) -> dict[str, Any]:
    source = path.read_text(encoding="utf-8")
    match = re.search(
        r"window\.CORVETTE_FORM_DATA\s*=\s*(\{.*\})\s*;\s*window\.STINGRAY_FORM_DATA\s*=",
        source,
        flags=re.DOTALL,
    )
    if not match:
        raise OverlayError(f"Could not locate window.CORVETTE_FORM_DATA assignment in {path}.")
    registry = json.loads(match.group(1))
    try:
        return registry["models"]["stingray"]["data"]
    except KeyError as error:
        raise OverlayError(f"Could not locate models.stingray.data in {path}: {error}.") from error


def load_fragment(args: argparse.Namespace) -> dict[str, Any]:
    if args.fragment_json:
        return json.loads(Path(args.fragment_json).read_text(encoding="utf-8"))
    return CsvSlice(Path(args.package)).legacy_fragment()


def load_ownership_scope(path: Path) -> OwnershipScope:
    rows = list(csv.DictReader(path.read_text(encoding="utf-8").splitlines()))
    owned_rpos: set[str] = set()
    guarded_option_refs: set[tuple[str, str]] = set()
    preserved_cross_boundary_records: set[tuple[str, str, str, str, str]] = set()
    preserved_cross_boundary_rows: list[dict[str, str]] = []
    guarded_group_ids: dict[str, set[str]] = {"exclusiveGroups": set(), "ruleGroups": set()}
    preserved_group_ids: dict[str, set[str]] = {"exclusiveGroups": set(), "ruleGroups": set()}
    projected_group_ids: dict[str, set[str]] = {"exclusiveGroups": set(), "ruleGroups": set()}
    seen_owned_rpos: set[str] = set()
    seen_guarded_refs: set[tuple[str, str]] = set()
    seen_preserved_records: set[tuple[str, str, str, str, str]] = set()
    seen_group_rows: set[tuple[str, str]] = set()

    for index, row in enumerate(rows, start=2):
        active = row.get("active", "")
        if active not in {"true", "false"}:
            raise OverlayError(f"{path} row {index} has unsupported active value {active!r}.")
        ownership = row.get("ownership", "")
        record_type = row.get("record_type", "")
        if ownership not in SUPPORTED_OWNERSHIP_VALUES:
            raise OverlayError(f"{path} row {index} has unsupported ownership value {ownership!r}.")
        if record_type not in SUPPORTED_RECORD_TYPES:
            raise OverlayError(f"{path} row {index} has unsupported record_type value {record_type!r}.")
        if active != "true":
            continue

        group_id = row.get("group_id", "")
        if record_type in GROUP_RECORD_TYPES and group_id:
            if (
                row.get("rpo", "")
                or row.get("source_rpo", "")
                or row.get("source_option_id", "")
                or row.get("target_rpo", "")
                or row.get("target_option_id", "")
            ):
                raise OverlayError(f"{path} row {index} group ownership row should not set rpo or source/target refs.")
            key = (record_type, group_id)
            if key in seen_group_rows:
                raise OverlayError(f"{path} has duplicate active group ownership row {key}.")
            seen_group_rows.add(key)
            surface = "exclusiveGroups" if record_type == "exclusiveGroup" else "ruleGroups"
            if ownership == "production_guarded":
                guarded_group_ids[surface].add(group_id)
            elif ownership == "preserved_cross_boundary":
                preserved_group_ids[surface].add(group_id)
            elif ownership == "projected_owned":
                projected_group_ids[surface].add(group_id)
            else:
                raise OverlayError(f"{path} row {index} has unsupported ownership value {ownership!r}.")
            continue

        has_record_refs = (
            row.get("rpo", "")
            or row.get("source_rpo", "")
            or row.get("source_option_id", "")
            or row.get("target_rpo", "")
            or row.get("target_option_id", "")
        )
        if record_type in GROUP_RECORD_TYPES and not group_id and not has_record_refs:
            raise OverlayError(f"{path} row {index} group ownership row is missing group_id.")

        if group_id:
            raise OverlayError(f"{path} row {index} group_id is only supported for exclusiveGroup or ruleGroup records.")

        if ownership == "projected_owned":
            rpo = row.get("rpo", "")
            if not rpo:
                raise OverlayError(f"{path} row {index} projected_owned row is missing rpo.")
            if record_type != "selectable":
                raise OverlayError(f"{path} row {index} projected_owned row must use record_type selectable or group_id.")
            if row.get("source_rpo", "") or row.get("source_option_id", "") or row.get("target_rpo", "") or row.get("target_option_id", ""):
                raise OverlayError(f"{path} row {index} projected_owned row should not set source/target refs.")
            if rpo in seen_owned_rpos:
                raise OverlayError(f"{path} has duplicate active projected_owned RPO {rpo}.")
            seen_owned_rpos.add(rpo)
            owned_rpos.add(rpo)
            continue

        if ownership == "production_guarded":
            if record_type != "guardedOption":
                raise OverlayError(f"{path} row {index} production_guarded row must use record_type guardedOption or group_id.")
            rpo = row.get("rpo", "")
            option_id = row.get("target_option_id", "") or row.get("source_option_id", "")
            if not (rpo or option_id):
                raise OverlayError(f"{path} row {index} production_guarded row is missing rpo or option_id.")
            if rpo and option_id:
                raise OverlayError(f"{path} row {index} production_guarded row must use either rpo or option_id, not both.")
            if row.get("source_rpo", "") or row.get("target_rpo", ""):
                raise OverlayError(f"{path} row {index} production_guarded row should not set source_rpo or target_rpo.")
            key = (rpo, option_id)
            if key in seen_guarded_refs:
                raise OverlayError(f"{path} has duplicate active production_guarded row {key}.")
            seen_guarded_refs.add(key)
            guarded_option_refs.add(key)
            continue

        source_rpo = row.get("source_rpo", "")
        source_option_id = row.get("source_option_id", "")
        target_rpo = row.get("target_rpo", "")
        target_option_id = row.get("target_option_id", "")
        if not (source_rpo or source_option_id) or not (target_rpo or target_option_id):
            raise OverlayError(
                f"{path} row {index} preserved_cross_boundary row is missing source_rpo/source_option_id or target_rpo/target_option_id."
            )
        if row.get("rpo", ""):
            raise OverlayError(f"{path} row {index} preserved_cross_boundary row should not set rpo.")
        if record_type not in {"rule", "priceRule", "ruleGroup"}:
            raise OverlayError(f"{path} row {index} preserved_cross_boundary row must use rule, priceRule, or ruleGroup.")
        key = (record_type, source_rpo, source_option_id, target_rpo, target_option_id)
        if key in seen_preserved_records:
            raise OverlayError(f"{path} has duplicate active preserved_cross_boundary row {key}.")
        seen_preserved_records.add(key)
        preserved_cross_boundary_records.add(key)
        preserved_cross_boundary_rows.append(
            {
                "manifest_row_id": f"csv_row_{index}",
                "record_type": record_type,
                "source_rpo": source_rpo,
                "source_option_id": source_option_id,
                "target_rpo": target_rpo,
                "target_option_id": target_option_id,
            }
        )

    return OwnershipScope(
        owned_rpos=owned_rpos,
        guarded_option_refs=guarded_option_refs,
        preserved_cross_boundary_records=preserved_cross_boundary_records,
        preserved_cross_boundary_rows=preserved_cross_boundary_rows,
        guarded_group_ids=guarded_group_ids,
        preserved_group_ids=preserved_group_ids,
        projected_group_ids=projected_group_ids,
    )


def normalized_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def normalize_variants(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(
        [
            {
                "variant_id": row["variant_id"],
                "model_year": int(row.get("model_year") or 0),
                "trim_level": row["trim_level"],
                "body_style": row["body_style"],
                "display_name": row["display_name"],
                "base_price": int(row.get("base_price") or 0),
                "display_order": int(row.get("display_order") or 0),
            }
            for row in rows
        ],
        key=lambda item: item["display_order"],
    )


def normalize_choices(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(
        [
            {
                "choice_id": row["choice_id"],
                "option_id": row["option_id"],
                "rpo": row["rpo"],
                "label": row["label"],
                "description": row["description"],
                "section_id": row["section_id"],
                "section_name": row["section_name"],
                "category_id": row["category_id"],
                "category_name": row["category_name"],
                "step_key": row["step_key"],
                "variant_id": row["variant_id"],
                "body_style": row["body_style"],
                "trim_level": row["trim_level"],
                "status": row["status"],
                "status_label": row["status_label"],
                "selectable": row["selectable"],
                "active": row["active"],
                "choice_mode": row["choice_mode"],
                "selection_mode": row["selection_mode"],
                "selection_mode_label": row["selection_mode_label"],
                "base_price": int(row.get("base_price") or 0),
                "display_order": int(row.get("display_order") or 0),
                "source_detail_raw": row.get("source_detail_raw", ""),
            }
            for row in rows
        ],
        key=lambda item: item["choice_id"],
    )


def normalize_rules(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(
        [
            {
                "source_id": row["source_id"],
                "rule_type": row["rule_type"],
                "target_id": row["target_id"],
                "target_type": row["target_type"],
                "source_type": row["source_type"],
                "source_section": row["source_section"],
                "target_section": row["target_section"],
                "source_selection_mode": row["source_selection_mode"],
                "target_selection_mode": row["target_selection_mode"],
                "body_style_scope": row.get("body_style_scope", ""),
                "disabled_reason": row["disabled_reason"],
                "auto_add": row["auto_add"],
                "active": row["active"],
                "runtime_action": row["runtime_action"],
                "review_flag": row["review_flag"],
            }
            for row in rows
        ],
        key=lambda item: (item["source_id"], item["rule_type"], item["target_id"], item["body_style_scope"]),
    )


def normalize_price_rules(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(
        [
            {
                "condition_option_id": row["condition_option_id"],
                "target_option_id": row["target_option_id"],
                "price_rule_type": row["price_rule_type"],
                "price_value": int(row.get("price_value") or 0),
                "body_style_scope": row.get("body_style_scope", ""),
                "trim_level_scope": row.get("trim_level_scope", ""),
                "variant_scope": row.get("variant_scope", ""),
                "review_flag": row["review_flag"],
            }
            for row in rows
        ],
        key=lambda item: (
            item["condition_option_id"],
            item["target_option_id"],
            item["body_style_scope"],
            item["price_value"],
        ),
    )


def normalize_rule_groups(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(
        [
            {
                "group_id": row["group_id"],
                "group_type": row["group_type"],
                "source_id": row["source_id"],
                "target_ids": list(row.get("target_ids", [])),
                "body_style_scope": row.get("body_style_scope", ""),
                "trim_level_scope": row.get("trim_level_scope", ""),
                "variant_scope": row.get("variant_scope", ""),
                "disabled_reason": row["disabled_reason"],
                "active": row["active"],
                "notes": row.get("notes", ""),
            }
            for row in rows
        ],
        key=lambda item: item["group_id"],
    )


def normalize_exclusive_groups(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(
        [
            {
                "group_id": row["group_id"],
                "option_ids": list(row.get("option_ids", [])),
                "selection_mode": row["selection_mode"],
                "active": row["active"],
                "notes": row.get("notes", ""),
            }
            for row in rows
        ],
        key=lambda item: item["group_id"],
    )


def projected_rpos(fragment: dict[str, Any], ownership: OwnershipScope) -> set[str]:
    rpos = {row["rpo"] for row in fragment.get("choices", []) if row.get("rpo")}
    if rpos != ownership.owned_rpos:
        raise OverlayError(
            "Projected fragment RPO scope changed: "
            f"expected {sorted(ownership.owned_rpos)}, got {sorted(rpos)}."
        )
    return rpos


def projected_option_ids(data: dict[str, Any], rpos: set[str]) -> set[str]:
    return {row["option_id"] for row in data.get("choices", []) if row.get("rpo") in rpos}


def assert_projected_choice_option_id_coverage(production: dict[str, Any], fragment: dict[str, Any], rpos: set[str]) -> None:
    # Projected selectable ownership is RPO-scoped. If production has duplicate
    # legacy option IDs for one RPO, the fragment must intentionally emit them all.
    for rpo in sorted(rpos):
        production_ids = {row["option_id"] for row in production.get("choices", []) if row.get("rpo") == rpo}
        fragment_ids = {row["option_id"] for row in fragment.get("choices", []) if row.get("rpo") == rpo}
        if production_ids == fragment_ids:
            continue
        missing = sorted(production_ids - fragment_ids)
        extra = sorted(fragment_ids - production_ids)
        raise OverlayError(
            f"Projected RPO {rpo} replacement is incomplete: projected ownership is RPO-scoped, "
            f"so fragment choices must include every production option_id for that RPO. "
            f"Missing option_ids: {missing}. Extra option_ids: {extra}."
        )


def option_id_by_rpo(data: dict[str, Any], rpo: str) -> str:
    option_ids = {row["option_id"] for row in data.get("choices", []) if row.get("rpo") == rpo}
    if len(option_ids) != 1:
        raise OverlayError(f"Expected exactly one production option_id for RPO {rpo}, found {sorted(option_ids)}.")
    return next(iter(option_ids))


def production_option_ids(data: dict[str, Any]) -> set[str]:
    option_ids = {row["option_id"] for row in data.get("choices", []) if row.get("option_id")}
    option_ids.update(row["source_id"] for row in data.get("rules", []) if row.get("source_id"))
    option_ids.update(row["target_id"] for row in data.get("rules", []) if row.get("target_id"))
    option_ids.update(row["condition_option_id"] for row in data.get("priceRules", []) if row.get("condition_option_id"))
    option_ids.update(row["target_option_id"] for row in data.get("priceRules", []) if row.get("target_option_id"))
    option_ids.update(row["source_id"] for row in data.get("ruleGroups", []) if row.get("source_id"))
    option_ids.update(target_id for row in data.get("ruleGroups", []) for target_id in row.get("target_ids", []))
    option_ids.update(option_id for row in data.get("exclusiveGroups", []) for option_id in row.get("option_ids", []))
    return option_ids


def production_choice_option_ids(data: dict[str, Any]) -> set[str]:
    return {row["option_id"] for row in data.get("choices", []) if row.get("option_id")}


def production_interior_ids(data: dict[str, Any]) -> set[str]:
    return {row["interior_id"] for row in data.get("interiors", []) if row.get("interior_id")}


def structured_record_ref(
    ref_id: str,
    source_kind: str,
    source_id: str,
    field: str,
    reference_path: str,
) -> dict[str, str]:
    return {
        "ref_id": ref_id,
        "source_kind": source_kind,
        "source_id": source_id,
        "reference_kind": "structured_ref",
        "reference_path": reference_path,
        "field": field,
    }


def structured_record_refs(data: dict[str, Any]) -> list[dict[str, str]]:
    refs: list[dict[str, str]] = []
    for row in data.get("rules", []):
        if row.get("source_id"):
            refs.append(structured_record_ref(row["source_id"], "rule", row.get("rule_id", ""), "source_id", "rules[].source_id"))
        if row.get("target_id"):
            refs.append(structured_record_ref(row["target_id"], "rule", row.get("rule_id", ""), "target_id", "rules[].target_id"))
    for row in data.get("priceRules", []):
        if row.get("condition_option_id"):
            refs.append(
                structured_record_ref(
                    row["condition_option_id"],
                    "priceRule",
                    row.get("price_rule_id", ""),
                    "condition_option_id",
                    "priceRules[].condition_option_id",
                )
            )
        if row.get("target_option_id"):
            refs.append(
                structured_record_ref(
                    row["target_option_id"],
                    "priceRule",
                    row.get("price_rule_id", ""),
                    "target_option_id",
                    "priceRules[].target_option_id",
                )
            )
    for row in data.get("ruleGroups", []):
        if row.get("source_id"):
            refs.append(
                structured_record_ref(row["source_id"], "ruleGroup", row.get("group_id", ""), "source_id", "ruleGroups[].source_id")
            )
        refs.extend(
            structured_record_ref(target_id, "ruleGroup", row.get("group_id", ""), "target_ids", "ruleGroups[].target_ids[]")
            for target_id in row.get("target_ids", [])
            if target_id
        )
    for row in data.get("exclusiveGroups", []):
        refs.extend(
            structured_record_ref(option_id, "exclusiveGroup", row.get("group_id", ""), "option_ids", "exclusiveGroups[].option_ids[]")
            for option_id in row.get("option_ids", [])
            if option_id
        )
    return refs


def option_id_by_manifest_ref(data: dict[str, Any], rpo: str, option_id: str) -> str:
    if option_id:
        if option_id not in production_option_ids(data):
            raise OverlayError(f"Preserved cross-boundary option_id {option_id} does not exist in production data.")
        return option_id
    if not rpo:
        raise OverlayError("Preserved cross-boundary row is missing both rpo and option_id for one side.")
    return option_id_by_rpo(data, rpo)


def preserved_record_id_keys(data: dict[str, Any], ownership: OwnershipScope) -> dict[str, set[tuple[str, str]]]:
    keys = {"rules": set(), "priceRules": set(), "ruleGroups": set()}
    surface_by_record_type = {"rule": "rules", "priceRule": "priceRules", "ruleGroup": "ruleGroups"}
    for record_type, source_rpo, source_option_id, target_rpo, target_option_id in ownership.preserved_cross_boundary_records:
        surface = surface_by_record_type[record_type]
        keys[surface].add(
            (
                option_id_by_manifest_ref(data, source_rpo, source_option_id),
                option_id_by_manifest_ref(data, target_rpo, target_option_id),
            )
        )
    return keys


def guarded_option_ids(data: dict[str, Any], ownership: OwnershipScope) -> set[str]:
    ids: set[str] = set()
    for rpo, option_id in ownership.guarded_option_refs:
        ids.add(option_id_by_manifest_ref(data, rpo, option_id))
    return ids


def assert_guarded_option_refs_are_not_interiors(data: dict[str, Any], ownership: OwnershipScope) -> None:
    interior_ids = production_interior_ids(data)
    invalid = [
        {"rpo": rpo, "option_id": option_id}
        for rpo, option_id in sorted(ownership.guarded_option_refs)
        if rpo in interior_ids or option_id in interior_ids
    ]
    if invalid:
        raise OverlayError(f"interior source ids cannot be production_guarded option refs: {invalid[:5]}.")


def assert_structured_refs_have_known_namespace(data: dict[str, Any], guarded_ids: set[str]) -> None:
    valid_ids = production_choice_option_ids(data) | production_interior_ids(data) | guarded_ids
    unknown = []
    seen: set[tuple[str, str, str]] = set()
    for ref in structured_record_refs(data):
        ref_id = ref["ref_id"]
        if ref_id in valid_ids:
            continue
        key = (ref["source_kind"], ref["field"], ref_id)
        if key in seen:
            continue
        seen.add(key)
        unknown.append(ref)
    if unknown:
        raise OverlayError(f"unknown structured non-choice refs: {unknown[:5]}.")


def structured_ref_namespace(ref_id: str, choice_ids: set[str], guarded_ids: set[str], interior_ids: set[str]) -> str:
    if ref_id in choice_ids:
        return "active_choice"
    if ref_id in guarded_ids:
        return "production_guarded"
    if ref_id in interior_ids:
        return "interior_source"
    return "unresolved"


def structured_ref_report_sort_key(row: dict[str, str]) -> tuple[int, str, str, str, str, str, str]:
    return (
        STRUCTURED_REF_NAMESPACE_ORDER[row["namespace"]],
        row["ref_id"],
        row["source_kind"],
        row["source_id"],
        row["reference_kind"],
        row["reference_path"],
        row["field"],
    )


def structured_reference_namespace_report(data: dict[str, Any], guarded_ids: set[str]) -> dict[str, Any]:
    choice_ids = production_choice_option_ids(data)
    interior_ids = production_interior_ids(data)
    rows = []
    for ref in structured_record_refs(data):
        namespace = structured_ref_namespace(ref["ref_id"], choice_ids, guarded_ids, interior_ids)
        status = "blocking" if namespace == "unresolved" else "allowed"
        rows.append(
            {
                "ref_id": ref["ref_id"],
                "namespace": namespace,
                "source_kind": ref["source_kind"],
                "source_id": ref["source_id"],
                "reference_kind": ref["reference_kind"],
                "reference_path": ref["reference_path"],
                "field": ref["field"],
                "status": status,
                "notes": UNRESOLVED_STRUCTURED_REF_NOTE if status == "blocking" else "",
            }
        )
    rows.sort(key=structured_ref_report_sort_key)
    counts_by_namespace = {namespace: 0 for namespace in STRUCTURED_REF_NAMESPACE_ORDER}
    for row in rows:
        counts_by_namespace[row["namespace"]] += 1
    unresolved_count = counts_by_namespace["unresolved"]
    return {
        "schema_version": 1,
        "status": "blocking" if unresolved_count else "allowed",
        "counts_by_namespace": counts_by_namespace,
        "unresolved_count": unresolved_count,
        "references": rows,
    }


def preserved_guarded_option_ids(data: dict[str, Any], ownership: OwnershipScope, guarded_ids: set[str]) -> set[str]:
    preserved_ids: set[str] = set()
    for _record_type, source_rpo, source_option_id, target_rpo, target_option_id in ownership.preserved_cross_boundary_records:
        for option_id in (
            option_id_by_manifest_ref(data, source_rpo, source_option_id),
            option_id_by_manifest_ref(data, target_rpo, target_option_id),
        ):
            if option_id in guarded_ids:
                preserved_ids.add(option_id)
    return preserved_ids


def production_guarded_candidate_status(ref_id: str, preserved_guarded_ids: set[str]) -> str:
    if ref_id in preserved_guarded_ids:
        return "cross_boundary_preserved"
    return "review_required"


def production_guarded_candidate_notes(candidate_status: str) -> str:
    if candidate_status == "cross_boundary_preserved":
        return PRODUCTION_GUARDED_PRESERVED_NOTE
    return PRODUCTION_GUARDED_REVIEW_NOTE


def production_guarded_triage_reference_sort_key(row: dict[str, str]) -> tuple[str, str, str, str, str, str]:
    return (
        row["ref_id"],
        row["source_kind"],
        row["source_id"],
        row["reference_kind"],
        row["reference_path"],
        row["field"],
    )


def production_guarded_structured_reference_triage_report(
    namespace_report: dict[str, Any],
    preserved_guarded_ids: set[str],
) -> dict[str, Any]:
    references = []
    for row in namespace_report["references"]:
        if row["namespace"] != "production_guarded":
            continue
        candidate_status = production_guarded_candidate_status(row["ref_id"], preserved_guarded_ids)
        references.append(
            {
                "ref_id": row["ref_id"],
                "namespace": row["namespace"],
                "source_kind": row["source_kind"],
                "source_id": row["source_id"],
                "reference_kind": row["reference_kind"],
                "reference_path": row["reference_path"],
                "field": row["field"],
                "status": row["status"],
                "candidate_status": candidate_status,
                "notes": production_guarded_candidate_notes(candidate_status),
            }
        )
    references.sort(key=production_guarded_triage_reference_sort_key)

    grouped: dict[str, dict[str, Any]] = {}
    for row in references:
        group = grouped.setdefault(
            row["ref_id"],
            {
                "guarded_ref_id": row["ref_id"],
                "referenced_by_count": 0,
                "source_kinds": set(),
                "source_ids": set(),
                "reference_kinds": set(),
                "reference_paths": set(),
                "candidate_statuses": set(),
            },
        )
        group["referenced_by_count"] += 1
        group["source_kinds"].add(row["source_kind"])
        group["source_ids"].add(row["source_id"])
        group["reference_kinds"].add(row["reference_kind"])
        group["reference_paths"].add(row["reference_path"])
        group["candidate_statuses"].add(row["candidate_status"])

    groups = []
    for group in grouped.values():
        candidate_statuses = group.pop("candidate_statuses")
        groups.append(
            {
                "guarded_ref_id": group["guarded_ref_id"],
                "referenced_by_count": group["referenced_by_count"],
                "source_kinds": sorted(group["source_kinds"]),
                "source_ids": sorted(group["source_ids"]),
                "reference_kinds": sorted(group["reference_kinds"]),
                "reference_paths": sorted(group["reference_paths"]),
                "candidate_status": "cross_boundary_preserved" if candidate_statuses == {"cross_boundary_preserved"} else "review_required",
            }
        )
    groups.sort(key=lambda group: group["guarded_ref_id"])

    return {
        "schema_version": 1,
        "status": "allowed",
        "production_guarded_count": len(references),
        "groups": groups,
        "references": references,
    }


def tolerant_option_id_by_manifest_ref(data: dict[str, Any], rpo: str, option_id: str) -> str:
    if option_id:
        return option_id
    if not rpo:
        return ""
    option_ids = {row["option_id"] for row in data.get("choices", []) if row.get("rpo") == rpo}
    if len(option_ids) == 1:
        return next(iter(option_ids))
    return rpo


def preserved_ref_namespace(ref_id: str, choice_ids: set[str], projected_ids: set[str], guarded_ids: set[str], interior_ids: set[str]) -> str:
    if ref_id in interior_ids:
        return "interior_source"
    if ref_id in projected_ids:
        return "active_projected_owned_choice"
    if ref_id in choice_ids:
        return "active_choice"
    if ref_id in guarded_ids:
        return "production_guarded"
    return "unknown"


def structured_rows_by_record_side(data: dict[str, Any]) -> dict[tuple[str, str, str, str, str], list[dict[str, str]]]:
    rows: dict[tuple[str, str, str, str, str], list[dict[str, str]]] = {}

    def add(record_type: str, source_id: str, target_id: str, ref_id: str, field: str, ref: dict[str, str]) -> None:
        rows.setdefault((record_type, source_id, target_id, ref_id, field), []).append(ref)

    for row in data.get("rules", []):
        source_id = row.get("source_id", "")
        target_id = row.get("target_id", "")
        if source_id:
            add("rule", source_id, target_id, source_id, "source_id", structured_record_ref(source_id, "rule", row.get("rule_id", ""), "source_id", "rules[].source_id"))
        if target_id:
            add("rule", source_id, target_id, target_id, "target_id", structured_record_ref(target_id, "rule", row.get("rule_id", ""), "target_id", "rules[].target_id"))
    for row in data.get("priceRules", []):
        source_id = row.get("condition_option_id", "")
        target_id = row.get("target_option_id", "")
        if source_id:
            add(
                "priceRule",
                source_id,
                target_id,
                source_id,
                "condition_option_id",
                structured_record_ref(source_id, "priceRule", row.get("price_rule_id", ""), "condition_option_id", "priceRules[].condition_option_id"),
            )
        if target_id:
            add(
                "priceRule",
                source_id,
                target_id,
                target_id,
                "target_option_id",
                structured_record_ref(target_id, "priceRule", row.get("price_rule_id", ""), "target_option_id", "priceRules[].target_option_id"),
            )
    for row in data.get("ruleGroups", []):
        source_id = row.get("source_id", "")
        for target_id in row.get("target_ids", []):
            if source_id:
                add(
                    "ruleGroup",
                    source_id,
                    target_id,
                    source_id,
                    "source_id",
                    structured_record_ref(source_id, "ruleGroup", row.get("group_id", ""), "source_id", "ruleGroups[].source_id"),
                )
            if target_id:
                add(
                    "ruleGroup",
                    source_id,
                    target_id,
                    target_id,
                    "target_ids",
                    structured_record_ref(target_id, "ruleGroup", row.get("group_id", ""), "target_ids", "ruleGroups[].target_ids[]"),
                )
    return rows


def preserved_contract_row_sort_key(row: dict[str, str]) -> tuple[str, str, str, str, str, str, str, str]:
    return (
        row["ref_id"],
        row["manifest_status"],
        row["namespace"],
        row["source_kind"],
        row["source_id"],
        row["reference_kind"],
        row["reference_path"],
        row["field"],
    )


def manifest_structured_lookup_field(record_type: str, field: str) -> str:
    if record_type == "priceRule":
        return "condition_option_id" if field == "source_id" else "target_option_id"
    if record_type == "ruleGroup":
        return "source_id" if field == "source_id" else "target_ids"
    return field


def preserved_cross_boundary_contract_report(
    data: dict[str, Any],
    fragment: dict[str, Any],
    ownership: OwnershipScope,
    namespace_report: dict[str, Any],
    guarded_ids: set[str],
    projected_ids: set[str],
) -> dict[str, Any]:
    choice_ids = production_choice_option_ids(data)
    interior_ids = production_interior_ids(data)
    current_rows_by_side = structured_rows_by_record_side(data)
    fragment_rows_by_side = structured_rows_by_record_side(fragment)
    current_guarded_rows = [row for row in namespace_report["references"] if row["namespace"] == "production_guarded"]
    current_guarded_keys = {
        (row["ref_id"], row["source_kind"], row["source_id"], row["field"])
        for row in current_guarded_rows
    }
    matched_guarded_keys: set[tuple[str, str, str, str]] = set()
    matches = []
    stale_preserved = []
    invalid_preserved = []

    for record_type, source_rpo, source_option_id, target_rpo, target_option_id in sorted(ownership.preserved_cross_boundary_records):
        source_id = tolerant_option_id_by_manifest_ref(data, source_rpo, source_option_id)
        target_id = tolerant_option_id_by_manifest_ref(data, target_rpo, target_option_id)
        side_refs = [
            (source_id, "source_id", preserved_ref_namespace(source_id, choice_ids, projected_ids, guarded_ids, interior_ids)),
            (target_id, "target_id", preserved_ref_namespace(target_id, choice_ids, projected_ids, guarded_ids, interior_ids)),
        ]
        pair_has_current_record = any(
            current_rows_by_side.get((record_type, source_id, target_id, ref_id, manifest_structured_lookup_field(record_type, field)))
            for ref_id, field, _namespace in side_refs
        )
        invalid_side_refs = [
            (ref_id, field, namespace)
            for ref_id, field, namespace in side_refs
            if namespace in {"interior_source", "unknown"}
        ]
        if (
            not invalid_side_refs
            and not pair_has_current_record
            and all(namespace == "active_projected_owned_choice" for _ref_id, _field, namespace in side_refs)
        ):
            invalid_side_refs = side_refs
        if invalid_side_refs:
            for ref_id, field, namespace in invalid_side_refs:
                invalid_preserved.append(
                    {
                        "ref_id": ref_id,
                        "manifest_status": "invalid_preserved",
                        "namespace": namespace,
                        "source_kind": record_type,
                        "source_id": f"{source_id}->{target_id}",
                        "reference_kind": "manifest_ref",
                        "reference_path": f"ownership.preserved_cross_boundary.{field}",
                        "field": field,
                        "status": "blocking",
                        "notes": PRESERVED_CROSS_BOUNDARY_INVALID_NOTE,
                    }
                )
            continue
        if not any(namespace == "production_guarded" for _ref_id, _field, namespace in side_refs):
            continue

        for ref_id, field, namespace in side_refs:
            if namespace != "production_guarded":
                continue
            manifest_status = "matched"
            destination = matches
            notes = PRESERVED_CROSS_BOUNDARY_MATCH_NOTE
            lookup_field = manifest_structured_lookup_field(record_type, field)
            structured_rows = current_rows_by_side.get((record_type, source_id, target_id, ref_id, lookup_field), [])
            if not structured_rows:
                manifest_status = "stale_preserved"
                destination = stale_preserved
                notes = PRESERVED_CROSS_BOUNDARY_STALE_NOTE
                structured_rows = [
                    structured_record_ref(
                        ref_id,
                        record_type,
                        f"{source_id}->{target_id}",
                        lookup_field,
                        f"manifest.preserved_cross_boundary.{field}",
                    )
                ]
            for structured_row in structured_rows:
                row = {
                    "ref_id": ref_id,
                    "manifest_status": manifest_status,
                    "namespace": namespace,
                    "source_kind": structured_row["source_kind"],
                    "source_id": structured_row["source_id"],
                    "reference_kind": structured_row["reference_kind"],
                    "reference_path": structured_row["reference_path"],
                    "field": structured_row["field"],
                    "status": "allowed" if manifest_status == "matched" else "blocking",
                    "notes": notes,
                }
                destination.append(row)
                if manifest_status == "matched":
                    matched_guarded_keys.add((row["ref_id"], row["source_kind"], row["source_id"], row["field"]))

    for (record_type, source_id, target_id, ref_id, lookup_field), structured_rows in sorted(current_rows_by_side.items()):
        if ref_id not in guarded_ids or not fragment_rows_by_side.get((record_type, source_id, target_id, ref_id, lookup_field)):
            continue
        for structured_row in structured_rows:
            key = (ref_id, structured_row["source_kind"], structured_row["source_id"], structured_row["field"])
            if key in matched_guarded_keys:
                continue
            matches.append(
                {
                    "ref_id": ref_id,
                    "manifest_status": "matched",
                    "namespace": "production_guarded",
                    "source_kind": structured_row["source_kind"],
                    "source_id": structured_row["source_id"],
                    "reference_kind": structured_row["reference_kind"],
                    "reference_path": structured_row["reference_path"],
                    "field": structured_row["field"],
                    "status": "allowed",
                    "notes": "Production guarded structured reference is emitted by the CSV fragment.",
                }
            )
            matched_guarded_keys.add(key)

    unguarded_production_guarded = []
    for row in current_guarded_rows:
        key = (row["ref_id"], row["source_kind"], row["source_id"], row["field"])
        if key in matched_guarded_keys:
            continue
        unguarded_production_guarded.append(
            {
                "ref_id": row["ref_id"],
                "manifest_status": "unguarded_production_guarded",
                "namespace": row["namespace"],
                "source_kind": row["source_kind"],
                "source_id": row["source_id"],
                "reference_kind": row["reference_kind"],
                "reference_path": row["reference_path"],
                "field": row["field"],
                "status": "blocking",
                "notes": PRESERVED_CROSS_BOUNDARY_UNGUARDED_NOTE,
            }
        )

    for rows in (matches, stale_preserved, unguarded_production_guarded, invalid_preserved):
        rows.sort(key=preserved_contract_row_sort_key)

    guarded_reference_count = len(current_guarded_rows)
    matched_count = len(matches)
    unguarded_count = len(unguarded_production_guarded)
    stale_count = len(stale_preserved)
    invalid_count = len(invalid_preserved)
    parity_ok = guarded_reference_count == matched_count + unguarded_count
    status = "allowed" if parity_ok and not stale_count and not unguarded_count and not invalid_count else "blocking"
    return {
        "schema_version": 1,
        "status": status,
        "guarded_reference_count": guarded_reference_count,
        "preserved_cross_boundary_count": len(ownership.preserved_cross_boundary_records),
        "matched_count": matched_count,
        "stale_preserved_count": stale_count,
        "unguarded_production_guarded_count": unguarded_count,
        "invalid_preserved_count": invalid_count,
        "count_parity_ok": parity_ok,
        "matches": matches,
        "stale_preserved": stale_preserved,
        "unguarded_production_guarded": unguarded_production_guarded,
        "invalid_preserved": invalid_preserved,
    }


def preserved_manifest_census_row_sort_key(row: dict[str, Any]) -> tuple[str, str, str, str, str, str, str, str, str]:
    return (
        row["candidate_status"],
        row["group_key"],
        row["manifest_row_id"],
        row["ref_id"] or "",
        row["pair_key"],
        row["source_kind"],
        row["source_id"],
        row["target_kind"],
        row["target_id"],
    )


def preserved_manifest_census_group_sort_key(group: dict[str, Any]) -> str:
    return group["group_key"]


def preserved_manifest_census_candidate_statuses(statuses: set[str]) -> str:
    if "invalid_preserved" in statuses:
        return "invalid_preserved"
    if "current_guarded_dependency" in statuses:
        return "current_guarded_dependency"
    return "manifest_only_preservation"


def preserved_cross_boundary_manifest_census_report(
    data: dict[str, Any],
    ownership: OwnershipScope,
    namespace_report: dict[str, Any],
    guarded_ids: set[str],
    projected_ids: set[str],
) -> dict[str, Any]:
    choice_ids = production_choice_option_ids(data)
    interior_ids = production_interior_ids(data)
    current_rows_by_side = structured_rows_by_record_side(data)
    current_guarded_rows = [row for row in namespace_report["references"] if row["namespace"] == "production_guarded"]
    rows: list[dict[str, Any]] = []

    for manifest_row in ownership.preserved_cross_boundary_rows:
        record_type = manifest_row["record_type"]
        source_id = tolerant_option_id_by_manifest_ref(data, manifest_row["source_rpo"], manifest_row["source_option_id"])
        target_id = tolerant_option_id_by_manifest_ref(data, manifest_row["target_rpo"], manifest_row["target_option_id"])
        pair_key = f"{source_id}->{target_id}"
        side_refs = [
            (source_id, "source_id", preserved_ref_namespace(source_id, choice_ids, projected_ids, guarded_ids, interior_ids)),
            (target_id, "target_id", preserved_ref_namespace(target_id, choice_ids, projected_ids, guarded_ids, interior_ids)),
        ]
        current_reference_rows = [
            structured_row
            for ref_id, field, namespace in side_refs
            if namespace == "production_guarded"
            for structured_row in current_rows_by_side.get(
                (record_type, source_id, target_id, ref_id, manifest_structured_lookup_field(record_type, field)),
                [],
            )
        ]
        invalid_refs = [
            (ref_id, namespace)
            for ref_id, _field, namespace in side_refs
            if namespace in {"interior_source", "unknown"}
        ]
        pair_has_current_record = bool(current_reference_rows) or any(
            current_rows_by_side.get((record_type, source_id, target_id, ref_id, manifest_structured_lookup_field(record_type, field)))
            for ref_id, field, _namespace in side_refs
        )
        invalid_projected_pair = (
            not invalid_refs
            and not pair_has_current_record
            and all(namespace == "active_projected_owned_choice" for _ref_id, _field, namespace in side_refs)
        )
        guarded_ref_ids = sorted({ref_id for ref_id, _field, namespace in side_refs if namespace == "production_guarded"})

        if invalid_refs:
            candidate_status = "invalid_preserved"
            ref_id = invalid_refs[0][0]
            group_key = ref_id
            notes = PRESERVED_CROSS_BOUNDARY_INVALID_NOTE
        elif invalid_projected_pair:
            candidate_status = "invalid_preserved"
            ref_id = None
            group_key = pair_key
            notes = PRESERVED_CROSS_BOUNDARY_INVALID_NOTE
        elif current_reference_rows:
            candidate_status = "current_guarded_dependency"
            ref_id = guarded_ref_ids[0] if guarded_ref_ids else None
            group_key = ref_id or pair_key
            notes = PRESERVED_CROSS_BOUNDARY_MATCH_NOTE
        else:
            candidate_status = "manifest_only_preservation"
            ref_id = guarded_ref_ids[0] if guarded_ref_ids else None
            group_key = ref_id or pair_key
            notes = "Active preserved_cross_boundary manifest row is valid but not a current production_guarded structured-reference dependency."

        rows.append(
            {
                "manifest_row_id": manifest_row["manifest_row_id"],
                "ref_id": ref_id,
                "pair_key": pair_key,
                "group_key": group_key,
                "manifest_status": "active",
                "source_kind": side_refs[0][2],
                "source_id": source_id,
                "target_kind": side_refs[1][2],
                "target_id": target_id,
                "ownership_status": "preserved_cross_boundary",
                "is_current_guarded_structured_ref": bool(current_reference_rows),
                "current_reference_count": len(current_reference_rows),
                "current_ref_ids": sorted({row["ref_id"] for row in current_reference_rows}),
                "current_ref_counts": {
                    ref_id: sum(1 for row in current_reference_rows if row["ref_id"] == ref_id)
                    for ref_id in sorted({row["ref_id"] for row in current_reference_rows})
                },
                "candidate_status": candidate_status,
                "notes": notes,
            }
        )

    rows.sort(key=preserved_manifest_census_row_sort_key)

    grouped: dict[str, dict[str, Any]] = {}
    for row in rows:
        row_group_keys = row["current_ref_ids"] if row["is_current_guarded_structured_ref"] else [row["group_key"]]
        for group_key in row_group_keys:
            group_ref_id = group_key if row["is_current_guarded_structured_ref"] else row["ref_id"]
            group_pair_key = "" if group_ref_id else row["pair_key"]
            group = grouped.setdefault(
                group_key,
                {
                    "group_key": group_key,
                    "ref_id": group_ref_id,
                    "pair_key": group_pair_key,
                    "active_preserved_group_membership_count": 0,
                    "current_guarded_group_membership_count": 0,
                    "current_guarded_structured_reference_count": 0,
                    "used_by_current_guarded_structured_refs": False,
                    "candidate_statuses": set(),
                    "source_kinds": set(),
                    "source_ids": set(),
                    "target_kinds": set(),
                    "target_ids": set(),
                },
            )
            group["active_preserved_group_membership_count"] += 1
            if row["is_current_guarded_structured_ref"]:
                group["current_guarded_group_membership_count"] += 1
            group["current_guarded_structured_reference_count"] += row["current_ref_counts"].get(group_key, 0)
            group["used_by_current_guarded_structured_refs"] = (
                group["used_by_current_guarded_structured_refs"] or row["is_current_guarded_structured_ref"]
            )
            group["candidate_statuses"].add(row["candidate_status"])
            group["source_kinds"].add(row["source_kind"])
            group["source_ids"].add(row["source_id"])
            group["target_kinds"].add(row["target_kind"])
            group["target_ids"].add(row["target_id"])

    groups = []
    for group in grouped.values():
        candidate_statuses = group.pop("candidate_statuses")
        groups.append(
            {
                "group_key": group["group_key"],
                "ref_id": group["ref_id"],
                "pair_key": group["pair_key"],
                "active_preserved_group_membership_count": group["active_preserved_group_membership_count"],
                "current_guarded_group_membership_count": group["current_guarded_group_membership_count"],
                "current_guarded_structured_reference_count": group["current_guarded_structured_reference_count"],
                "used_by_current_guarded_structured_refs": group["used_by_current_guarded_structured_refs"],
                "candidate_status": preserved_manifest_census_candidate_statuses(candidate_statuses),
                "source_kinds": sorted(group["source_kinds"]),
                "source_ids": sorted(group["source_ids"]),
                "target_kinds": sorted(group["target_kinds"]),
                "target_ids": sorted(group["target_ids"]),
            }
        )
    groups.sort(key=preserved_manifest_census_group_sort_key)
    for row in rows:
        row.pop("current_ref_counts")
        row.pop("current_ref_ids")

    current_guarded_manifest_row_count = sum(1 for row in rows if row["is_current_guarded_structured_ref"])
    current_guarded_structured_reference_count = sum(row["current_reference_count"] for row in rows)
    current_guarded_group_membership_count = sum(
        group["current_guarded_group_membership_count"]
        for group in groups
        if group["candidate_status"] == "current_guarded_dependency"
    )
    invalid_preserved_count = sum(1 for row in rows if row["candidate_status"] == "invalid_preserved")
    manifest_only_preservation_row_count = sum(1 for row in rows if row["candidate_status"] == "manifest_only_preservation")

    return {
        "schema_version": 1,
        "status": "blocking" if invalid_preserved_count else "allowed",
        "active_preserved_cross_boundary_row_count": len(rows),
        "active_preserved_cross_boundary_record_count": len(ownership.preserved_cross_boundary_records),
        "current_guarded_structured_reference_count": current_guarded_structured_reference_count,
        "current_guarded_manifest_row_count": current_guarded_manifest_row_count,
        "current_guarded_preserved_record_count": current_guarded_manifest_row_count,
        "current_guarded_group_membership_count": current_guarded_group_membership_count,
        "manifest_only_preservation_row_count": manifest_only_preservation_row_count,
        "manifest_only_preservation_record_count": manifest_only_preservation_row_count,
        "invalid_preserved_count": invalid_preserved_count,
        "groups": groups,
        "rows": rows,
    }


def manifest_only_preservation_triage_group_sort_key(group: dict[str, Any]) -> tuple[str, str, str]:
    return (group["group_key"], group["source_ids"][0] if group["source_ids"] else "", group["target_ids"][0] if group["target_ids"] else "")


def sorted_nonempty_values(values: list[Any]) -> list[str]:
    return sorted({str(value) for value in values if value not in {None, ""}})


def first_or_none(values: list[str]) -> str | None:
    return values[0] if values else None


def manifest_only_side_ownership_status(namespace: str) -> str:
    if namespace == "active_projected_owned_choice":
        return "projected_owned"
    if namespace == "active_choice":
        return "production_owned"
    if namespace == "production_guarded":
        return "production_guarded"
    if namespace == "interior_source":
        return "interior_source"
    return "unknown"


def manifest_only_side_projection_status(namespace: str) -> str:
    if namespace == "active_projected_owned_choice":
        return "projected_owned"
    return "not_projected"


def manifest_only_option_detail_lookup(data: dict[str, Any]) -> dict[str, dict[str, Any]]:
    existing_option_ids = production_option_ids(data)
    choices_by_option_id: dict[str, list[dict[str, Any]]] = {}
    for row in sorted(
        data.get("choices", []),
        key=lambda item: (int(item.get("display_order") or 0), item.get("choice_id", ""), item.get("option_id", "")),
    ):
        option_id = row.get("option_id", "")
        if option_id:
            choices_by_option_id.setdefault(option_id, []).append(row)

    details: dict[str, dict[str, Any]] = {}
    for option_id in sorted(existing_option_ids | set(choices_by_option_id)):
        choice_rows = choices_by_option_id.get(option_id, [])
        details[option_id] = {
            "label": first_or_none(sorted_nonempty_values([row.get("label") for row in choice_rows])),
            "category": first_or_none(sorted_nonempty_values([row.get("category_name") for row in choice_rows])),
            "section": first_or_none(sorted_nonempty_values([row.get("section_name") for row in choice_rows])),
            "exists": option_id in existing_option_ids,
        }
    return details


def manifest_only_enriched_side_fields(
    prefix: str,
    option_id: str,
    namespace: str,
    detail_lookup: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    detail = detail_lookup.get(option_id, {"label": None, "category": None, "section": None, "exists": False})
    return {
        f"{prefix}_label": detail["label"],
        f"{prefix}_category": detail["category"],
        f"{prefix}_section": detail["section"],
        f"{prefix}_ownership_status": manifest_only_side_ownership_status(namespace),
        f"{prefix}_projection_status": manifest_only_side_projection_status(namespace),
        f"{prefix}_exists": bool(detail["exists"]),
    }


def sorted_group_values(group: dict[str, set[str]]) -> dict[str, list[str]]:
    return {key: sorted(values) for key, values in group.items()}


def manifest_only_rollup_values(value: Any) -> list[Any]:
    if isinstance(value, list):
        return [item for child in value for item in manifest_only_rollup_values(child)]
    if isinstance(value, tuple):
        return [item for child in value for item in manifest_only_rollup_values(child)]
    if isinstance(value, set):
        return [item for child in sorted(value, key=str) for item in manifest_only_rollup_values(child)]
    return [value]


def manifest_only_rollup_keys(value: Any) -> list[str]:
    keys = sorted({str(item) for item in manifest_only_rollup_values(value) if item is not None and str(item) != ""})
    return keys or ["__missing__"]


def manifest_only_preservation_rollup(rows: list[dict[str, Any]], field: str) -> list[dict[str, Any]]:
    buckets: dict[str, dict[str, Any]] = {}
    for row in rows:
        for key in manifest_only_rollup_keys(row.get(field)):
            bucket = buckets.setdefault(
                key,
                {
                    "row_count": 0,
                    "record_ids": set(),
                    "group_keys": set(),
                },
            )
            bucket["row_count"] += 1
            bucket["record_ids"].add(row["manifest_row_id"])
            bucket["group_keys"].add(row["group_key"])
    return [
        {
            "key": key,
            "row_count": bucket["row_count"],
            "record_count": len(bucket["record_ids"]),
            "group_count": len(bucket["group_keys"]),
            "group_keys": sorted(bucket["group_keys"]),
        }
        for key, bucket in sorted(buckets.items())
    ]


def build_direction_rollup(rows: list[dict[str, Any]], source_field: str, target_field: str) -> list[dict[str, Any]]:
    buckets: dict[str, dict[str, Any]] = {}
    for row in rows:
        for source_key in manifest_only_rollup_keys(row.get(source_field)):
            for target_key in manifest_only_rollup_keys(row.get(target_field)):
                key = f"{source_key}->{target_key}"
                bucket = buckets.setdefault(
                    key,
                    {
                        "source_key": source_key,
                        "target_key": target_key,
                        "row_count": 0,
                        "record_ids": set(),
                        "group_keys": set(),
                    },
                )
                bucket["row_count"] += 1
                bucket["record_ids"].add(row["manifest_row_id"])
                bucket["group_keys"].add(row["group_key"])
    return [
        {
            "key": key,
            "source_key": bucket["source_key"],
            "target_key": bucket["target_key"],
            "row_count": bucket["row_count"],
            "record_count": len(bucket["record_ids"]),
            "group_count": len(bucket["group_keys"]),
            "group_keys": sorted(bucket["group_keys"]),
        }
        for key, bucket in sorted(buckets.items())
    ]


def manifest_only_ownership_projection_keys(row: dict[str, Any], prefix: str) -> list[str]:
    return [
        f"{ownership_key}/{projection_key}"
        for ownership_key in manifest_only_rollup_keys(row.get(f"{prefix}_ownership_status"))
        for projection_key in manifest_only_rollup_keys(row.get(f"{prefix}_projection_status"))
    ]


def manifest_only_ownership_projection_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    combined_rows = []
    for row in rows:
        combined_rows.append(
            {
                **row,
                "source_ownership_projection_status": manifest_only_ownership_projection_keys(row, "source"),
                "target_ownership_projection_status": manifest_only_ownership_projection_keys(row, "target"),
            }
        )
    return combined_rows


def manifest_only_direction_key(row: dict[str, Any]) -> str:
    source_keys = manifest_only_ownership_projection_keys(row, "source")
    target_keys = manifest_only_ownership_projection_keys(row, "target")
    return f"{source_keys[0]}->{target_keys[0]}"


def manifest_only_group_direction_key(group: dict[str, Any]) -> str:
    source_ownership_keys = manifest_only_rollup_keys(group.get("source_ownership_statuses"))
    source_projection_keys = manifest_only_rollup_keys(group.get("source_projection_statuses"))
    target_ownership_keys = manifest_only_rollup_keys(group.get("target_ownership_statuses"))
    target_projection_keys = manifest_only_rollup_keys(group.get("target_projection_statuses"))
    if (
        len(source_ownership_keys) == 1
        and len(source_projection_keys) == 1
        and len(target_ownership_keys) == 1
        and len(target_projection_keys) == 1
    ):
        return f"{source_ownership_keys[0]}/{source_projection_keys[0]}->{target_ownership_keys[0]}/{target_projection_keys[0]}"
    return "__mixed__".join(
        [
            " | ".join(source_ownership_keys),
            " | ".join(source_projection_keys),
            " | ".join(target_ownership_keys),
            " | ".join(target_projection_keys),
        ]
    )


def direction_slice_row_sort_key(row: dict[str, Any]) -> tuple[str, str, str, str, str]:
    return (
        row["direction_key"],
        row["group_key"],
        row["manifest_row_id"],
        row["source_id"],
        row["target_id"],
    )


def direction_slice_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    flat_rows = [
        {
            "direction_key": manifest_only_direction_key(row),
            "manifest_row_id": row["manifest_row_id"],
            "group_key": row["group_key"],
            "ref_id": row["ref_id"],
            "pair_key": row["pair_key"],
            "source_id": row["source_id"],
            "source_label": row["source_label"],
            "source_category": row["source_category"],
            "source_section": row["source_section"],
            "source_ownership_status": row["source_ownership_status"],
            "source_projection_status": row["source_projection_status"],
            "target_id": row["target_id"],
            "target_label": row["target_label"],
            "target_category": row["target_category"],
            "target_section": row["target_section"],
            "target_ownership_status": row["target_ownership_status"],
            "target_projection_status": row["target_projection_status"],
            "candidate_status": row["candidate_status"],
        }
        for row in rows
    ]
    return sorted(flat_rows, key=direction_slice_row_sort_key)


def ownership_projection_direction_slices(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    combined_rows = manifest_only_ownership_projection_rows(rows)
    slices = []
    for direction in build_direction_rollup(
        combined_rows,
        "source_ownership_projection_status",
        "target_ownership_projection_status",
    ):
        slice_rows = [
            row
            for row in combined_rows
            if direction["key"]
            in {
                f"{source_key}->{target_key}"
                for source_key in manifest_only_rollup_keys(row.get("source_ownership_projection_status"))
                for target_key in manifest_only_rollup_keys(row.get("target_ownership_projection_status"))
            }
        ]
        slices.append(
            {
                "key": direction["key"],
                "source_key": direction["source_key"],
                "target_key": direction["target_key"],
                "row_count": direction["row_count"],
                "record_count": direction["record_count"],
                "group_count": direction["group_count"],
                "group_keys": direction["group_keys"],
                "source_category_rollup": manifest_only_preservation_rollup(slice_rows, "source_category"),
                "target_category_rollup": manifest_only_preservation_rollup(slice_rows, "target_category"),
                "source_section_rollup": manifest_only_preservation_rollup(slice_rows, "source_section"),
                "target_section_rollup": manifest_only_preservation_rollup(slice_rows, "target_section"),
                "source_label_rollup": manifest_only_preservation_rollup(slice_rows, "source_label"),
                "target_label_rollup": manifest_only_preservation_rollup(slice_rows, "target_label"),
            }
        )
    return slices


def manifest_only_preservation_triage_report(census_report: dict[str, Any], data: dict[str, Any]) -> dict[str, Any]:
    detail_lookup = manifest_only_option_detail_lookup(data)
    rows = [
        {
            "manifest_row_id": row["manifest_row_id"],
            "ref_id": row["ref_id"],
            "pair_key": row["pair_key"],
            "group_key": row["group_key"],
            "source_kind": row["source_kind"],
            "source_id": row["source_id"],
            "target_kind": row["target_kind"],
            "target_id": row["target_id"],
            "manifest_status": row["manifest_status"],
            "ownership_status": row["ownership_status"],
            "candidate_status": row["candidate_status"],
            "notes": row["notes"],
            **manifest_only_enriched_side_fields("source", row["source_id"], row["source_kind"], detail_lookup),
            **manifest_only_enriched_side_fields("target", row["target_id"], row["target_kind"], detail_lookup),
        }
        for row in census_report["rows"]
        if row["candidate_status"] == "manifest_only_preservation"
    ]

    grouped: dict[str, dict[str, Any]] = {}
    for row in rows:
        group = grouped.setdefault(
            row["group_key"],
            {
                "group_key": row["group_key"],
                "pair_key": row["pair_key"] if row["ref_id"] is None else "",
                "ref_id": row["ref_id"],
                "manifest_only_preservation_row_count": 0,
                "manifest_only_preservation_record_count": 0,
                "source_kinds": set(),
                "source_ids": set(),
                "target_kinds": set(),
                "target_ids": set(),
                "ownership_statuses": set(),
                "candidate_status": "manifest_only_preservation",
                "notes": "Active preserved_cross_boundary rows that are valid but not current production_guarded structured-reference dependencies.",
                "source_labels": set(),
                "target_labels": set(),
                "source_categories": set(),
                "target_categories": set(),
                "source_sections": set(),
                "target_sections": set(),
                "source_ownership_statuses": set(),
                "target_ownership_statuses": set(),
                "source_projection_statuses": set(),
                "target_projection_statuses": set(),
            },
        )
        group["manifest_only_preservation_row_count"] += 1
        group["manifest_only_preservation_record_count"] += 1
        group["source_kinds"].add(row["source_kind"])
        group["source_ids"].add(row["source_id"])
        group["target_kinds"].add(row["target_kind"])
        group["target_ids"].add(row["target_id"])
        group["ownership_statuses"].add(row["ownership_status"])
        aggregate_fields = {
            "source_label": "source_labels",
            "target_label": "target_labels",
            "source_category": "source_categories",
            "target_category": "target_categories",
            "source_section": "source_sections",
            "target_section": "target_sections",
            "source_ownership_status": "source_ownership_statuses",
            "target_ownership_status": "target_ownership_statuses",
            "source_projection_status": "source_projection_statuses",
            "target_projection_status": "target_projection_statuses",
        }
        for field, aggregate_field in aggregate_fields.items():
            value = row[field]
            if value is not None:
                group[aggregate_field].add(value)

    groups = []
    for group in grouped.values():
        groups.append(
            {
                "group_key": group["group_key"],
                "pair_key": group["pair_key"],
                "ref_id": group["ref_id"],
                "manifest_only_preservation_row_count": group["manifest_only_preservation_row_count"],
                "manifest_only_preservation_record_count": group["manifest_only_preservation_record_count"],
                "source_kinds": sorted(group["source_kinds"]),
                "source_ids": sorted(group["source_ids"]),
                "target_kinds": sorted(group["target_kinds"]),
                "target_ids": sorted(group["target_ids"]),
                "ownership_statuses": sorted(group["ownership_statuses"]),
                "candidate_status": group["candidate_status"],
                "notes": group["notes"],
                **sorted_group_values(
                    {
                        "source_labels": group["source_labels"],
                        "target_labels": group["target_labels"],
                        "source_categories": group["source_categories"],
                        "target_categories": group["target_categories"],
                        "source_sections": group["source_sections"],
                        "target_sections": group["target_sections"],
                        "source_ownership_statuses": group["source_ownership_statuses"],
                        "target_ownership_statuses": group["target_ownership_statuses"],
                        "source_projection_statuses": group["source_projection_statuses"],
                        "target_projection_statuses": group["target_projection_statuses"],
                    }
                ),
            }
        )
    groups.sort(key=manifest_only_preservation_triage_group_sort_key)
    group_row_counts = [group["manifest_only_preservation_row_count"] for group in groups]
    group_row_count_distribution: dict[str, int] = {}
    for row_count in group_row_counts:
        key = str(row_count)
        group_row_count_distribution[key] = group_row_count_distribution.get(key, 0) + 1
    multi_row_groups = [
        {
            "group_key": group["group_key"],
            "ref_id": group["ref_id"],
            "pair_key": group["pair_key"],
            "manifest_only_preservation_row_count": group["manifest_only_preservation_row_count"],
            "manifest_only_preservation_record_count": group["manifest_only_preservation_record_count"],
            "source_kinds": group["source_kinds"],
            "source_ids": group["source_ids"],
            "target_kinds": group["target_kinds"],
            "target_ids": group["target_ids"],
            "manifest_row_ids": sorted(row["manifest_row_id"] for row in rows if row["group_key"] == group["group_key"]),
            "candidate_status": group["candidate_status"],
            "notes": group["notes"],
            "source_labels": group["source_labels"],
            "target_labels": group["target_labels"],
            "source_categories": group["source_categories"],
            "target_categories": group["target_categories"],
            "source_sections": group["source_sections"],
            "target_sections": group["target_sections"],
            "source_ownership_statuses": group["source_ownership_statuses"],
            "target_ownership_statuses": group["target_ownership_statuses"],
            "source_projection_statuses": group["source_projection_statuses"],
            "target_projection_statuses": group["target_projection_statuses"],
        }
        for group in groups
        if group["manifest_only_preservation_row_count"] > 1
    ]

    invalid_preserved_count = census_report["invalid_preserved_count"]
    return {
        "schema_version": 1,
        "status": "blocking" if invalid_preserved_count else "allowed",
        "manifest_only_preservation_row_count": len(rows),
        "manifest_only_preservation_record_count": len(rows),
        "invalid_preserved_count": invalid_preserved_count,
        "group_count": len(groups),
        "single_row_group_count": sum(1 for row_count in group_row_counts if row_count == 1),
        "multi_row_group_count": len(multi_row_groups),
        "max_group_row_count": max(group_row_counts) if group_row_counts else 0,
        "group_row_count_distribution": group_row_count_distribution,
        "multi_row_groups": multi_row_groups,
        "source_category_rollup": manifest_only_preservation_rollup(rows, "source_category"),
        "target_category_rollup": manifest_only_preservation_rollup(rows, "target_category"),
        "source_section_rollup": manifest_only_preservation_rollup(rows, "source_section"),
        "target_section_rollup": manifest_only_preservation_rollup(rows, "target_section"),
        "source_ownership_status_rollup": manifest_only_preservation_rollup(rows, "source_ownership_status"),
        "target_ownership_status_rollup": manifest_only_preservation_rollup(rows, "target_ownership_status"),
        "source_projection_status_rollup": manifest_only_preservation_rollup(rows, "source_projection_status"),
        "target_projection_status_rollup": manifest_only_preservation_rollup(rows, "target_projection_status"),
        "ownership_direction_rollup": build_direction_rollup(rows, "source_ownership_status", "target_ownership_status"),
        "projection_direction_rollup": build_direction_rollup(rows, "source_projection_status", "target_projection_status"),
        "ownership_projection_direction_rollup": build_direction_rollup(
            manifest_only_ownership_projection_rows(rows),
            "source_ownership_projection_status",
            "target_ownership_projection_status",
        ),
        "ownership_projection_direction_slices": ownership_projection_direction_slices(rows),
        "direction_slice_rows": direction_slice_rows(rows),
        "groups": groups,
        "rows": rows,
    }


def assert_preserved_option_id_refs_are_guarded(data: dict[str, Any], ownership: OwnershipScope, guarded_ids: set[str]) -> None:
    choice_ids = production_choice_option_ids(data)
    unguarded = []
    for record_type, _source_rpo, source_option_id, _target_rpo, target_option_id in sorted(ownership.preserved_cross_boundary_records):
        for option_id in (source_option_id, target_option_id):
            if option_id and option_id not in choice_ids and option_id not in guarded_ids:
                unguarded.append({"record_type": record_type, "option_id": option_id})
    if unguarded:
        raise OverlayError(f"unguarded rule-only preserved option_id refs: {unguarded[:5]}.")


def rule_group_member_keys(rows: list[dict[str, Any]]) -> set[tuple[str, str]]:
    return {
        (row.get("source_id", ""), target_id)
        for row in rows
        for target_id in row.get("target_ids", [])
    }


def group_ids_by_surface(data: dict[str, Any]) -> dict[str, set[str]]:
    return {
        "exclusiveGroups": {row.get("group_id", "") for row in data.get("exclusiveGroups", []) if row.get("group_id")},
        "ruleGroups": {row.get("group_id", "") for row in data.get("ruleGroups", []) if row.get("group_id")},
    }


def assert_preserved_records_exist(data: dict[str, Any], ownership: OwnershipScope, preserved_keys_by_surface: dict[str, set[tuple[str, str]]]) -> None:
    production_keys_by_surface = {
        "rules": {(row.get("source_id", ""), row.get("target_id", "")) for row in data.get("rules", [])},
        "priceRules": {(row.get("condition_option_id", ""), row.get("target_option_id", "")) for row in data.get("priceRules", [])},
        "ruleGroups": rule_group_member_keys(data.get("ruleGroups", [])),
    }
    missing = []
    for surface, preserved_keys in preserved_keys_by_surface.items():
        missing.extend(
            {"surface": surface, "source_id": source_id, "target_id": target_id}
            for source_id, target_id in sorted(preserved_keys - production_keys_by_surface[surface])
        )
    if missing:
        raise OverlayError(f"Preserved production records do not exist: {missing[:5]}.")
    production_group_ids = group_ids_by_surface(data)
    missing_groups = []
    for surface in ("exclusiveGroups", "ruleGroups"):
        expected_group_ids = ownership.guarded_group_ids[surface] | ownership.preserved_group_ids[surface]
        missing_groups.extend(
            {"surface": surface, "group_id": group_id}
            for group_id in sorted(expected_group_ids - production_group_ids[surface])
        )
    if missing_groups:
        raise OverlayError(f"Preserved or guarded production groups do not exist: {missing_groups[:5]}.")


def assert_projected_groups_exist(fragment: dict[str, Any], ownership: OwnershipScope) -> None:
    fragment_group_ids = group_ids_by_surface(fragment)
    missing = []
    for surface in ("exclusiveGroups", "ruleGroups"):
        missing.extend(
            {"surface": surface, "group_id": group_id}
            for group_id in sorted(ownership.projected_group_ids[surface] - fragment_group_ids[surface])
        )
    if missing:
        surfaces = sorted({item["surface"] for item in missing})
        surface_label = surfaces[0] if len(surfaces) == 1 else "groups"
        raise OverlayError(f"{surface_label} projected group is missing from fragment: {missing[:5]}.")


def assert_projected_rule_group_ownership(fragment: dict[str, Any], ownership: OwnershipScope, projected_ids: set[str]) -> None:
    # Default Pass 35 policy: a projected-owned ruleGroup may only be emitted
    # when its source and all emitted target members are projected-owned.
    projected_group_ids = ownership.projected_group_ids["ruleGroups"]
    unowned_sources = []
    unowned_targets = []
    for row in fragment.get("ruleGroups", []):
        group_id = row.get("group_id", "")
        if group_id not in projected_group_ids:
            continue
        source_id = row.get("source_id", "")
        if source_id not in projected_ids:
            unowned_sources.append({"group_id": group_id, "source_id": source_id})
        missing_target_ids = [target_id for target_id in row.get("target_ids", []) if target_id not in projected_ids]
        if missing_target_ids:
            unowned_targets.append({"group_id": group_id, "target_ids": missing_target_ids})
    if unowned_sources:
        raise OverlayError(f"projected ruleGroup source is not projected-owned: {unowned_sources[:5]}.")
    if unowned_targets:
        raise OverlayError(f"projected ruleGroup targets are not projected-owned: {unowned_targets[:5]}.")


def assert_projected_package_record_ownership(fragment: dict[str, Any], projected_ids: set[str]) -> None:
    # Default Pass 53 policy: projected package-driven include records and
    # included-zero priceRules require projected-owned package sources and
    # projected-owned emitted targets. Cross-owned package/member edges remain
    # production-owned/preserved unless a later exception model is approved.
    unowned_include_sources = []
    unowned_include_targets = []
    for row in fragment.get("rules", []):
        if row.get("rule_type", "") != "includes" or row.get("auto_add", "") != "True":
            continue
        source_id = row.get("source_id", "")
        target_id = row.get("target_id", "")
        if source_id not in projected_ids:
            unowned_include_sources.append({"source_id": source_id, "target_id": target_id})
        if target_id not in projected_ids:
            unowned_include_targets.append({"source_id": source_id, "target_id": target_id})

    unowned_price_rule_sources = []
    unowned_price_rule_targets = []
    for row in fragment.get("priceRules", []):
        if row.get("price_rule_type", "") != "override" or int(row.get("price_value") or 0) != 0:
            continue
        source_id = row.get("condition_option_id", "")
        target_id = row.get("target_option_id", "")
        if source_id not in projected_ids:
            unowned_price_rule_sources.append({"condition_option_id": source_id, "target_option_id": target_id})
        if target_id not in projected_ids:
            unowned_price_rule_targets.append({"condition_option_id": source_id, "target_option_id": target_id})

    if unowned_include_sources:
        raise OverlayError(f"projected package include source is not projected-owned: {unowned_include_sources[:5]}.")
    if unowned_include_targets:
        raise OverlayError(f"projected package include targets are not projected-owned: {unowned_include_targets[:5]}.")
    if unowned_price_rule_sources:
        raise OverlayError(f"projected package priceRule source is not projected-owned: {unowned_price_rule_sources[:5]}.")
    if unowned_price_rule_targets:
        raise OverlayError(f"projected package priceRule targets are not projected-owned: {unowned_price_rule_targets[:5]}.")


def assert_same_normalized(surface: str, left: list[dict[str, Any]], right: list[dict[str, Any]]) -> None:
    left_rows = [normalized_json(row) for row in left]
    right_rows = [normalized_json(row) for row in right]
    if left_rows != right_rows:
        missing = sorted(set(left_rows) - set(right_rows))
        extra = sorted(set(right_rows) - set(left_rows))
        raise OverlayError(f"{surface} mismatch. Missing replacements: {missing[:5]}. Extra replacements: {extra[:5]}.")


def assert_no_unreplaced_owned_records(
    surface: str,
    production_rows: list[dict[str, Any]],
    fragment_rows: list[dict[str, Any]],
    normalize: Callable[[list[dict[str, Any]]], list[dict[str, Any]]],
    id_fields: tuple[str, str],
    projected_ids: set[str],
    preserved_keys: set[tuple[str, str]],
) -> None:
    fragment_keys = {tuple(row.get(field, "") for field in id_fields) for row in normalize(fragment_rows)}
    fragment_records = {normalized_json(row) for row in normalize(fragment_rows)}
    dropped = []
    unclassified_cross_boundary = []
    for row in normalize(production_rows):
        ids = [row.get(field, "") for field in id_fields]
        row_key = tuple(ids)
        if not any(item in projected_ids for item in ids):
            continue
        if row_key in preserved_keys:
            continue
        if any(item and item not in projected_ids for item in ids):
            if normalized_json(row) not in fragment_records:
                unclassified_cross_boundary.append(row)
            continue
        if row_key not in fragment_keys:
            dropped.append(row)
    if unclassified_cross_boundary:
        raise OverlayError(f"{surface} has unclassified cross-boundary records: {unclassified_cross_boundary[:5]}.")
    if dropped:
        raise OverlayError(f"{surface} has unreplaced migrated-slice-owned records: {dropped[:5]}.")


def assert_no_unclassified_guarded_records(
    surface: str,
    production_rows: list[dict[str, Any]],
    fragment_rows: list[dict[str, Any]],
    normalize: Callable[[list[dict[str, Any]]], list[dict[str, Any]]],
    id_fields: tuple[str, str],
    guarded_ids: set[str],
    preserved_keys: set[tuple[str, str]],
) -> None:
    fragment_keys = {tuple(row.get(field, "") for field in id_fields) for row in normalize(fragment_rows)}
    unclassified = []
    for row in normalize(production_rows):
        ids = tuple(row.get(field, "") for field in id_fields)
        if not any(option_id in guarded_ids for option_id in ids):
            continue
        if ids not in preserved_keys and ids not in fragment_keys:
            unclassified.append(row)
    if unclassified:
        raise OverlayError(f"{surface} has unclassified guarded production records: {unclassified[:5]}.")


def assert_no_unclassified_guarded_rule_groups(
    production_rows: list[dict[str, Any]],
    fragment_rows: list[dict[str, Any]],
    guarded_ids: set[str],
    preserved_keys: set[tuple[str, str]],
) -> None:
    fragment_keys = rule_group_member_keys(fragment_rows)
    unclassified = []
    for row in normalize_rule_groups(production_rows):
        source_id = row.get("source_id", "")
        for target_id in row.get("target_ids", []):
            if source_id not in guarded_ids and target_id not in guarded_ids:
                continue
            key = (source_id, target_id)
            if key not in preserved_keys and key not in fragment_keys:
                unclassified.append(
                    {
                        "group_id": row["group_id"],
                        "group_type": row["group_type"],
                        "source_id": source_id,
                        "target_id": target_id,
                    }
                )
    if unclassified:
        raise OverlayError(f"ruleGroups has unclassified guarded production records: {unclassified[:5]}.")


def group_touches_ids(row: dict[str, Any], ids: set[str], surface: str) -> bool:
    if surface == "exclusiveGroups":
        return any(option_id in ids for option_id in row.get("option_ids", []))
    if row.get("source_id", "") in ids:
        return True
    return any(target_id in ids for target_id in row.get("target_ids", []))


def assert_no_unclassified_group_records(
    surface: str,
    production_rows: list[dict[str, Any]],
    fragment_rows: list[dict[str, Any]],
    ids: set[str],
    classified_group_ids: set[str],
    message: str,
) -> None:
    fragment_group_ids = {row.get("group_id", "") for row in fragment_rows if row.get("group_id", "")}
    unclassified = []
    for row in production_rows:
        group_id = row.get("group_id", "")
        if not group_id or not group_touches_ids(row, ids, surface):
            continue
        if group_id not in classified_group_ids and group_id not in fragment_group_ids:
            unclassified.append({"surface": surface, "group_id": group_id})
    if unclassified:
        raise OverlayError(f"{surface} has {message}: {unclassified[:5]}.")


def replace_by_key(
    production_rows: list[dict[str, Any]],
    fragment_rows: list[dict[str, Any]],
    remove_predicate: Callable[[dict[str, Any]], bool],
    key: Callable[[dict[str, Any]], tuple[Any, ...]],
    surface: str,
) -> list[dict[str, Any]]:
    replacements = {key(row): clone(row) for row in fragment_rows}
    replaced_keys: set[tuple[Any, ...]] = set()
    output = []
    for row in production_rows:
        if not remove_predicate(row):
            output.append(clone(row))
            continue
        row_key = key(row)
        if row_key not in replacements:
            raise OverlayError(f"{surface} removed record has no projected replacement for key {row_key}.")
        output.append(clone(replacements[row_key]))
        replaced_keys.add(row_key)
    unused_keys = sorted(set(replacements) - replaced_keys)
    if unused_keys:
        raise OverlayError(f"{surface} projected replacements were not inserted: {unused_keys[:5]}.")
    return output


def non_projected_slices(data: dict[str, Any], rpos: set[str], projected_ids: set[str]) -> dict[str, Any]:
    return {
        "choices": normalize_choices([row for row in data.get("choices", []) if row.get("rpo") not in rpos]),
        "rules": normalize_rules(
            [
                row
                for row in data.get("rules", [])
                if row.get("source_id") not in projected_ids and row.get("target_id") not in projected_ids
            ]
        ),
        "priceRules": normalize_price_rules(
            [
                row
                for row in data.get("priceRules", [])
                if row.get("condition_option_id") not in projected_ids and row.get("target_option_id") not in projected_ids
            ]
        ),
        "ruleGroups": normalize_rule_groups(
            [
                row
                for row in data.get("ruleGroups", [])
                if row.get("source_id") not in projected_ids and not any(target_id in projected_ids for target_id in row.get("target_ids", []))
            ]
        ),
        "exclusiveGroups": normalize_exclusive_groups(
            [
                row
                for row in data.get("exclusiveGroups", [])
                if not any(option_id in projected_ids for option_id in row.get("option_ids", []))
            ]
        ),
    }


def overlay_shadow_data(production: dict[str, Any], fragment: dict[str, Any], ownership: OwnershipScope) -> dict[str, Any]:
    if fragment.get("validation_errors"):
        raise OverlayError(f"Fragment validation failed: {fragment['validation_errors']}.")
    if normalize_variants(fragment.get("variants", [])) != normalize_variants(production.get("variants", [])):
        raise OverlayError("Fragment variants do not match production variants.")

    rpos = projected_rpos(fragment, ownership)
    assert_projected_choice_option_id_coverage(production, fragment, rpos)
    production_ids = projected_option_ids(production, rpos)
    fragment_ids = projected_option_ids(fragment, rpos)
    if production_ids != fragment_ids:
        raise OverlayError(f"Fragment legacy option IDs do not match production: {sorted(production_ids)} != {sorted(fragment_ids)}.")
    preserved_keys_by_surface = preserved_record_id_keys(production, ownership)
    assert_guarded_option_refs_are_not_interiors(production, ownership)
    guarded_ids = guarded_option_ids(production, ownership)
    assert_preserved_option_id_refs_are_guarded(production, ownership, guarded_ids)
    assert_structured_refs_have_known_namespace(production, guarded_ids)
    assert_preserved_records_exist(production, ownership, preserved_keys_by_surface)
    assert_projected_groups_exist(fragment, ownership)
    assert_projected_rule_group_ownership(fragment, ownership, fragment_ids)
    assert_projected_package_record_ownership(fragment, fragment_ids)

    removed_choices = [row for row in production.get("choices", []) if row.get("rpo") in rpos]
    fragment_rule_keys = {
        (row.get("source_id"), row.get("rule_type"), row.get("target_id"), row.get("body_style_scope", ""))
        for row in fragment.get("rules", [])
    }
    removed_rules = [
        row
        for row in production.get("rules", [])
        if (row.get("source_id"), row.get("rule_type"), row.get("target_id"), row.get("body_style_scope", "")) in fragment_rule_keys
    ]
    fragment_price_rule_keys = {
        (row.get("condition_option_id"), row.get("target_option_id"), row.get("body_style_scope", ""), int(row.get("price_value") or 0))
        for row in fragment.get("priceRules", [])
    }
    removed_price_rules = [
        row
        for row in production.get("priceRules", [])
        if (row.get("condition_option_id"), row.get("target_option_id"), row.get("body_style_scope", ""), int(row.get("price_value") or 0))
        in fragment_price_rule_keys
    ]
    fragment_exclusive_group_keys = {row.get("group_id") for row in fragment.get("exclusiveGroups", [])}
    removed_exclusive_groups = [
        row
        for row in production.get("exclusiveGroups", [])
        if row.get("group_id") in fragment_exclusive_group_keys
    ]
    fragment_rule_group_keys = {row.get("group_id") for row in fragment.get("ruleGroups", [])}
    removed_rule_groups = [
        row
        for row in production.get("ruleGroups", [])
        if row.get("group_id") in fragment_rule_group_keys
    ]

    assert_same_normalized("choices", normalize_choices(removed_choices), normalize_choices(fragment.get("choices", [])))
    assert_same_normalized("rules", normalize_rules(removed_rules), normalize_rules(fragment.get("rules", [])))
    assert_same_normalized("priceRules", normalize_price_rules(removed_price_rules), normalize_price_rules(fragment.get("priceRules", [])))
    assert_same_normalized("ruleGroups", normalize_rule_groups(removed_rule_groups), normalize_rule_groups(fragment.get("ruleGroups", [])))
    assert_same_normalized(
        "exclusiveGroups",
        normalize_exclusive_groups(removed_exclusive_groups),
        normalize_exclusive_groups(fragment.get("exclusiveGroups", [])),
    )
    assert_no_unreplaced_owned_records(
        "rules",
        production.get("rules", []),
        fragment.get("rules", []),
        normalize_rules,
        ("source_id", "target_id"),
        production_ids,
        preserved_keys_by_surface["rules"],
    )
    assert_no_unreplaced_owned_records(
        "priceRules",
        production.get("priceRules", []),
        fragment.get("priceRules", []),
        normalize_price_rules,
        ("condition_option_id", "target_option_id"),
        production_ids,
        preserved_keys_by_surface["priceRules"],
    )
    assert_no_unclassified_guarded_records(
        "rules",
        production.get("rules", []),
        fragment.get("rules", []),
        normalize_rules,
        ("source_id", "target_id"),
        guarded_ids,
        preserved_keys_by_surface["rules"],
    )
    assert_no_unclassified_guarded_records(
        "priceRules",
        production.get("priceRules", []),
        fragment.get("priceRules", []),
        normalize_price_rules,
        ("condition_option_id", "target_option_id"),
        guarded_ids,
        preserved_keys_by_surface["priceRules"],
    )
    assert_no_unclassified_guarded_rule_groups(
        production.get("ruleGroups", []),
        fragment.get("ruleGroups", []),
        guarded_ids,
        preserved_keys_by_surface["ruleGroups"],
    )
    classified_exclusive_group_ids = (
        ownership.guarded_group_ids["exclusiveGroups"]
        | ownership.preserved_group_ids["exclusiveGroups"]
        | ownership.projected_group_ids["exclusiveGroups"]
    )
    classified_rule_group_ids = (
        ownership.guarded_group_ids["ruleGroups"]
        | ownership.preserved_group_ids["ruleGroups"]
        | ownership.projected_group_ids["ruleGroups"]
    )
    assert_no_unclassified_group_records(
        "exclusiveGroups",
        production.get("exclusiveGroups", []),
        fragment.get("exclusiveGroups", []),
        guarded_ids,
        classified_exclusive_group_ids,
        "unclassified guarded production groups",
    )
    assert_no_unclassified_group_records(
        "ruleGroups",
        production.get("ruleGroups", []),
        fragment.get("ruleGroups", []),
        guarded_ids,
        classified_rule_group_ids,
        "unclassified guarded production groups",
    )
    assert_no_unclassified_group_records(
        "exclusiveGroups",
        production.get("exclusiveGroups", []),
        fragment.get("exclusiveGroups", []),
        production_ids,
        classified_exclusive_group_ids,
        "unclassified cross-boundary groups",
    )
    assert_no_unclassified_group_records(
        "ruleGroups",
        production.get("ruleGroups", []),
        fragment.get("ruleGroups", []),
        production_ids,
        classified_rule_group_ids,
        "unclassified cross-boundary groups",
    )
    unreplaced_exclusive_groups = [
        row
        for row in production.get("exclusiveGroups", [])
        if any(option_id in production_ids for option_id in row.get("option_ids", []))
        and row.get("group_id") not in fragment_exclusive_group_keys
        and row.get("group_id") not in ownership.preserved_group_ids["exclusiveGroups"]
        and row.get("group_id") not in ownership.guarded_group_ids["exclusiveGroups"]
    ]
    if unreplaced_exclusive_groups:
        raise OverlayError(f"exclusiveGroups has unreplaced migrated-slice-owned records: {unreplaced_exclusive_groups[:5]}.")
    unreplaced_rule_groups = [
        row
        for row in production.get("ruleGroups", [])
        if (
            row.get("source_id") in production_ids
            or any(target_id in production_ids for target_id in row.get("target_ids", []))
        )
        and row.get("group_id") not in fragment_rule_group_keys
        and row.get("group_id") not in ownership.preserved_group_ids["ruleGroups"]
        and row.get("group_id") not in ownership.guarded_group_ids["ruleGroups"]
    ]
    if unreplaced_rule_groups:
        raise OverlayError(f"ruleGroups has unreplaced migrated-slice-owned records: {unreplaced_rule_groups[:5]}.")

    shadow = clone(production)
    shadow["variants"] = clone(production.get("variants", []))
    shadow["ruleGroups"] = replace_by_key(
        production.get("ruleGroups", []),
        fragment.get("ruleGroups", []),
        lambda row: row.get("group_id") in fragment_rule_group_keys,
        lambda row: (row.get("group_id"),),
        "ruleGroups",
    )
    shadow["choices"] = replace_by_key(
        production.get("choices", []),
        fragment.get("choices", []),
        lambda row: row.get("rpo") in rpos,
        lambda row: (row.get("choice_id"),),
        "choices",
    )
    shadow["rules"] = replace_by_key(
        production.get("rules", []),
        fragment.get("rules", []),
        lambda row: (row.get("source_id"), row.get("rule_type"), row.get("target_id"), row.get("body_style_scope", "")) in fragment_rule_keys,
        lambda row: (row.get("source_id"), row.get("rule_type"), row.get("target_id"), row.get("body_style_scope", "")),
        "rules",
    )
    shadow["priceRules"] = replace_by_key(
        production.get("priceRules", []),
        fragment.get("priceRules", []),
        lambda row: (row.get("condition_option_id"), row.get("target_option_id"), row.get("body_style_scope", ""), int(row.get("price_value") or 0))
        in fragment_price_rule_keys,
        lambda row: (
            row.get("condition_option_id"),
            row.get("target_option_id"),
            row.get("body_style_scope", ""),
            int(row.get("price_value") or 0),
        ),
        "priceRules",
    )
    shadow["exclusiveGroups"] = replace_by_key(
        production.get("exclusiveGroups", []),
        fragment.get("exclusiveGroups", []),
        lambda row: row.get("group_id") in fragment_exclusive_group_keys,
        lambda row: (row.get("group_id"),),
        "exclusiveGroups",
    )

    if non_projected_slices(shadow, rpos, production_ids) != non_projected_slices(production, rpos, production_ids):
        raise OverlayError("Non-projected records changed during shadow overlay.")
    return shadow


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--production-data", default=str(DEFAULT_PRODUCTION_DATA))
    parser.add_argument("--package", default=str(DEFAULT_PACKAGE))
    parser.add_argument("--ownership-manifest", default=str(DEFAULT_OWNERSHIP_MANIFEST))
    parser.add_argument("--fragment-json", default="")
    parser.add_argument("--out", default="")
    parser.add_argument("--pretty", action="store_true")
    parser.add_argument("--as-data-js", action="store_true")
    parser.add_argument("--structured-reference-namespace-report", action="store_true")
    parser.add_argument("--production-guarded-structured-reference-triage", action="store_true")
    parser.add_argument("--preserved-cross-boundary-contract-report", action="store_true")
    parser.add_argument("--preserved-cross-boundary-manifest-census", action="store_true")
    parser.add_argument("--manifest-only-preservation-triage", action="store_true")
    parser.add_argument("--direction-slice-rows-csv-out", default="")
    parser.add_argument("--review-packet-manifest-out", default="")
    parser.add_argument("--decision-ledger-csv-out", default="")
    parser.add_argument("--validate-decision-ledger-csv", default="")
    parser.add_argument("--decision-ledger-validation-report-out", default="")
    parser.add_argument("--decision-ledger-validation-summary-out", default="")
    parser.add_argument("--manual-review-readiness-checkpoint-out", default="")
    return parser.parse_args()


def format_shadow_json(shadow: dict[str, Any], pretty: bool = False) -> str:
    indent = 2 if pretty else None
    return json.dumps(shadow, indent=indent, sort_keys=True, separators=None if pretty else (",", ":"))


def format_data_js(shadow: dict[str, Any], pretty: bool = False) -> str:
    registry_json = json.dumps(
        {
            "defaultModelKey": "stingray",
            "models": {
                "stingray": {
                    "key": "stingray",
                    "label": "Stingray",
                    "modelName": "Corvette Stingray",
                    "exportSlug": "stingray",
                    "data": shadow,
                }
            },
        },
        indent=2 if pretty else None,
        sort_keys=True,
        separators=None if pretty else (",", ":"),
    )
    if pretty:
        return (
            f"window.CORVETTE_FORM_DATA = {registry_json};\n"
            "window.STINGRAY_FORM_DATA = window.CORVETTE_FORM_DATA.models.stingray.data;"
        )
    return (
        f"window.CORVETTE_FORM_DATA={registry_json};\n"
        "window.STINGRAY_FORM_DATA=window.CORVETTE_FORM_DATA.models.stingray.data;"
    )


def format_report_json(report: dict[str, Any], pretty: bool = False) -> str:
    return json.dumps(report, indent=2 if pretty else None, sort_keys=True, separators=None if pretty else (",", ":"))


def write_or_print_output(output: str, out: str) -> None:
    if out:
        output_path = Path(out)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(output + "\n", encoding="utf-8")
    else:
        print(output)


def write_direction_slice_rows_csv(rows: list[dict[str, Any]], out: str) -> None:
    output_path = Path(out)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=DIRECTION_SLICE_ROWS_CSV_FIELDS)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: "" if row.get(field) is None else row.get(field, "") for field in DIRECTION_SLICE_ROWS_CSV_FIELDS})


def decision_ledger_joined_values(value: Any) -> str:
    return " | ".join(key for key in manifest_only_rollup_keys(value) if key != "__missing__")


def build_decision_ledger_rows(report: dict[str, Any]) -> list[dict[str, str]]:
    manifest_rows_by_group: dict[str, list[str]] = {}
    for row in report["rows"]:
        manifest_rows_by_group.setdefault(row["group_key"], []).append(row["manifest_row_id"])
    ledger_rows = []
    for group in report["groups"]:
        ledger_row = {
            "group_key": group["group_key"],
            "direction_key": manifest_only_group_direction_key(group),
            "manifest_only_preservation_row_count": str(group["manifest_only_preservation_row_count"]),
            "manifest_only_preservation_record_count": str(group["manifest_only_preservation_record_count"]),
            "source_ids": decision_ledger_joined_values(group["source_ids"]),
            "source_labels": decision_ledger_joined_values(group["source_labels"]),
            "source_categories": decision_ledger_joined_values(group["source_categories"]),
            "source_sections": decision_ledger_joined_values(group["source_sections"]),
            "source_ownership_statuses": decision_ledger_joined_values(group["source_ownership_statuses"]),
            "source_projection_statuses": decision_ledger_joined_values(group["source_projection_statuses"]),
            "target_ids": decision_ledger_joined_values(group["target_ids"]),
            "target_labels": decision_ledger_joined_values(group["target_labels"]),
            "target_categories": decision_ledger_joined_values(group["target_categories"]),
            "target_sections": decision_ledger_joined_values(group["target_sections"]),
            "target_ownership_statuses": decision_ledger_joined_values(group["target_ownership_statuses"]),
            "target_projection_statuses": decision_ledger_joined_values(group["target_projection_statuses"]),
            "manifest_row_ids": " | ".join(sorted(manifest_rows_by_group[group["group_key"]])),
        }
        ledger_row.update({field: "" for field in DECISION_LEDGER_REVIEW_FIELDS})
        ledger_rows.append(ledger_row)
    ledger_rows.sort(key=lambda row: (row["direction_key"], row["group_key"]))
    return ledger_rows


def write_decision_ledger_csv(report: dict[str, Any], out: str) -> None:
    ledger_rows = build_decision_ledger_rows(report)
    output_path = Path(out)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=DECISION_LEDGER_CSV_FIELDS)
        writer.writeheader()
        for row in ledger_rows:
            writer.writerow({field: "" if row.get(field) is None else row.get(field, "") for field in DECISION_LEDGER_CSV_FIELDS})


def valid_decision_ledger_reviewed_at(value: str) -> bool:
    return value == "" or re.fullmatch(r"\d{4}-\d{2}-\d{2}", value) is not None


def decision_ledger_validation_error(
    error_type: str,
    group_key: str | None = None,
    field: str | None = None,
    expected: Any = None,
    actual: Any = None,
    message: str = "",
) -> dict[str, Any]:
    return {
        "error_type": error_type,
        "group_key": group_key,
        "field": field,
        "expected": expected,
        "actual": actual,
        "message": message,
    }


def decision_ledger_validation_report(report: dict[str, Any], ledger_csv: str) -> dict[str, Any]:
    expected_rows = build_decision_ledger_rows(report)
    expected_by_group = {row["group_key"]: row for row in expected_rows}
    groups: list[dict[str, Any]] = []
    missing_groups: list[dict[str, Any]] = []
    unknown_groups: list[dict[str, Any]] = []
    duplicate_groups: list[dict[str, Any]] = []
    schema_errors: list[dict[str, Any]] = []
    review_value_errors: list[dict[str, Any]] = []
    schema_error_count = 0
    review_value_error_count = 0
    unknown_group_keys: set[str] = set()
    duplicate_group_keys: set[str] = set()
    seen_group_keys: set[str] = set()
    matched_group_keys: set[str] = set()

    with Path(ledger_csv).open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        actual_header = reader.fieldnames or []
        actual_rows = list(reader)

    if actual_header != DECISION_LEDGER_CSV_FIELDS:
        schema_error_count += 1
        schema_errors.append(
            decision_ledger_validation_error(
                "bad_header",
                field="header",
                expected=DECISION_LEDGER_CSV_FIELDS,
                actual=actual_header,
                message="decision ledger header does not match expected schema",
            )
        )
        errors = missing_groups + unknown_groups + duplicate_groups + schema_errors + review_value_errors
        return {
            "schema_version": 1,
            "status": "blocking",
            "ledger_row_count": len(actual_rows),
            "current_group_count": len(expected_rows),
            "matched_group_count": 0,
            "missing_group_count": 0,
            "unknown_group_count": 0,
            "duplicate_group_count": 0,
            "schema_error_count": schema_error_count,
            "review_value_error_count": review_value_error_count,
            "groups": groups,
            "missing_groups": missing_groups,
            "unknown_groups": unknown_groups,
            "duplicate_groups": duplicate_groups,
            "schema_errors": schema_errors,
            "review_value_errors": review_value_errors,
            "errors": errors,
        }

    for index, row in enumerate(actual_rows, start=2):
        group_key = row.get("group_key", "")
        expected = expected_by_group.get(group_key)
        matched = expected is not None and group_key not in seen_group_keys
        if not group_key:
            schema_error_count += 1
            schema_errors.append(
                decision_ledger_validation_error(
                    "context_mismatch",
                    field="group_key",
                    expected=None,
                    actual="",
                    message=f"ledger row {index} is missing group_key",
                )
            )
        elif expected is None:
            unknown_group_keys.add(group_key)
            unknown_groups.append(
                decision_ledger_validation_error(
                    "unknown_group",
                    group_key=group_key,
                    field="group_key",
                    expected=None,
                    actual=group_key,
                    message="ledger row group_key is not in current report groups",
                )
            )
        elif group_key in seen_group_keys:
            duplicate_group_keys.add(group_key)
            duplicate_groups.append(
                decision_ledger_validation_error(
                    "duplicate_group",
                    group_key=group_key,
                    field="group_key",
                    expected="exactly one row",
                    actual="duplicate row",
                    message="ledger row group_key appears more than once",
                )
            )
        else:
            matched_group_keys.add(group_key)
            for field in DECISION_LEDGER_CONTEXT_FIELDS:
                if row.get(field, "") != expected[field]:
                    schema_error_count += 1
                    schema_errors.append(
                        decision_ledger_validation_error(
                            "direction_mismatch" if field == "direction_key" else "context_mismatch",
                            group_key=group_key,
                            field=field,
                            expected=expected[field],
                            actual=row.get(field, ""),
                            message="ledger generated/context field does not match current report",
                        )
                    )
        seen_group_keys.add(group_key)

        review_status = row.get("review_status", "")
        decision = row.get("decision", "")
        followup_action = row.get("followup_action", "")
        reviewed_at = row.get("reviewed_at", "")
        review_errors_before = review_value_error_count
        if review_status not in DECISION_LEDGER_ALLOWED_REVIEW_STATUS:
            review_value_error_count += 1
            review_value_errors.append(
                decision_ledger_validation_error(
                    "invalid_review_status",
                    group_key=group_key,
                    field="review_status",
                    expected=sorted(DECISION_LEDGER_ALLOWED_REVIEW_STATUS),
                    actual=review_status,
                    message="review_status is not allowed",
                )
            )
        if decision not in DECISION_LEDGER_ALLOWED_DECISION:
            review_value_error_count += 1
            review_value_errors.append(
                decision_ledger_validation_error(
                    "invalid_decision",
                    group_key=group_key,
                    field="decision",
                    expected=sorted(DECISION_LEDGER_ALLOWED_DECISION),
                    actual=decision,
                    message="decision is not allowed",
                )
            )
        if followup_action not in DECISION_LEDGER_ALLOWED_FOLLOWUP_ACTION:
            review_value_error_count += 1
            review_value_errors.append(
                decision_ledger_validation_error(
                    "invalid_followup_action",
                    group_key=group_key,
                    field="followup_action",
                    expected=sorted(DECISION_LEDGER_ALLOWED_FOLLOWUP_ACTION),
                    actual=followup_action,
                    message="followup_action is not allowed",
                )
            )
        if not valid_decision_ledger_reviewed_at(reviewed_at):
            review_value_error_count += 1
            review_value_errors.append(
                decision_ledger_validation_error(
                    "invalid_reviewed_at",
                    group_key=group_key,
                    field="reviewed_at",
                    expected="YYYY-MM-DD or blank",
                    actual=reviewed_at,
                    message="reviewed_at must be blank or YYYY-MM-DD",
                )
            )

        groups.append(
            {
                "group_key": group_key,
                "direction_key": row.get("direction_key", ""),
                "matched": matched and review_value_error_count == review_errors_before,
                "review_status": review_status,
                "reviewer": row.get("reviewer", ""),
                "reviewed_at": reviewed_at,
                "decision": decision,
                "decision_reason": row.get("decision_reason", ""),
                "followup_action": followup_action,
                "notes": row.get("notes", ""),
            }
        )

    missing_group_keys = set(expected_by_group) - matched_group_keys
    for group_key in sorted(missing_group_keys):
        missing_groups.append(
            decision_ledger_validation_error(
                "missing_group",
                group_key=group_key,
                field="group_key",
                expected=group_key,
                actual=None,
                message="current report group is missing from ledger",
            )
        )

    unknown_group_count = len(unknown_group_keys)
    duplicate_group_count = len(duplicate_group_keys)
    missing_group_count = len(missing_group_keys)
    errors = missing_groups + unknown_groups + duplicate_groups + schema_errors + review_value_errors
    status = (
        "blocking"
        if schema_error_count
        or review_value_error_count
        or unknown_group_count
        or duplicate_group_count
        or missing_group_count
        else "allowed"
    )
    return {
        "schema_version": 1,
        "status": status,
        "ledger_row_count": len(actual_rows),
        "current_group_count": len(expected_rows),
        "matched_group_count": len(matched_group_keys),
        "missing_group_count": missing_group_count,
        "unknown_group_count": unknown_group_count,
        "duplicate_group_count": duplicate_group_count,
        "schema_error_count": schema_error_count,
        "review_value_error_count": review_value_error_count,
        "groups": groups,
        "missing_groups": missing_groups,
        "unknown_groups": unknown_groups,
        "duplicate_groups": duplicate_groups,
        "schema_errors": schema_errors,
        "review_value_errors": review_value_errors,
        "errors": errors,
    }


def decision_ledger_validation_count_values(groups: list[dict[str, Any]], field: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for group in groups:
        value = group.get(field, "") or ""
        counts[value] = counts.get(value, 0) + 1
    return {
        key: counts[key]
        for key in sorted(counts, key=lambda item: (item != "", item))
    }


def decision_ledger_validation_summary(validation_report: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "status": validation_report["status"],
        "ledger_row_count": validation_report["ledger_row_count"],
        "current_group_count": validation_report["current_group_count"],
        "matched_group_count": validation_report["matched_group_count"],
        "error_counts": {
            "missing_group_count": validation_report["missing_group_count"],
            "unknown_group_count": validation_report["unknown_group_count"],
            "duplicate_group_count": validation_report["duplicate_group_count"],
            "schema_error_count": validation_report["schema_error_count"],
            "review_value_error_count": validation_report["review_value_error_count"],
        },
        "review_field_counts": {
            "decision": decision_ledger_validation_count_values(validation_report["groups"], "decision"),
            "followup_action": decision_ledger_validation_count_values(validation_report["groups"], "followup_action"),
            "review_status": decision_ledger_validation_count_values(validation_report["groups"], "review_status"),
        },
    }


def manual_review_readiness_checkpoint(
    report: dict[str, Any],
    validation_report: dict[str, Any],
    validation_summary: dict[str, Any] | None = None,
) -> dict[str, Any]:
    error_counts = (
        validation_summary["error_counts"]
        if validation_summary
        else {
            "missing_group_count": validation_report["missing_group_count"],
            "unknown_group_count": validation_report["unknown_group_count"],
            "duplicate_group_count": validation_report["duplicate_group_count"],
            "schema_error_count": validation_report["schema_error_count"],
            "review_value_error_count": validation_report["review_value_error_count"],
        }
    )
    error_count = sum(error_counts.values())
    ready_for_manual_review = (
        report["status"] == "allowed"
        and report["invalid_preserved_count"] == 0
        and validation_report["status"] == "allowed"
        and validation_report["matched_group_count"] == validation_report["current_group_count"]
        and validation_report["ledger_row_count"] == validation_report["current_group_count"]
    )
    return {
        "schema_version": 1,
        "status": "ready_for_manual_review" if ready_for_manual_review else "blocked",
        "not_migration_ready": True,
        "inputs": {
            "manifest_only_report_status": report["status"],
            "validation_report_status": validation_report["status"],
        },
        "counts": {
            "manifest_only_preservation_row_count": report["manifest_only_preservation_row_count"],
            "group_count": report["group_count"],
            "invalid_preserved_count": report["invalid_preserved_count"],
            "ledger_row_count": validation_report["ledger_row_count"],
            "current_group_count": validation_report["current_group_count"],
            "matched_group_count": validation_report["matched_group_count"],
            "error_count": error_count,
        },
        "required_next_step": "manual_review",
    }


def manifest_only_review_packet_manifest(report: dict[str, Any], json_out: str, csv_out: str) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "status": report["status"],
        "generated_outputs": {
            "manifest_only_preservation_triage_json": json_out,
            "direction_slice_rows_csv": csv_out or None,
        },
        "summary": {
            "manifest_only_preservation_row_count": report["manifest_only_preservation_row_count"],
            "manifest_only_preservation_record_count": report["manifest_only_preservation_record_count"],
            "group_count": report["group_count"],
            "single_row_group_count": report["single_row_group_count"],
            "multi_row_group_count": report["multi_row_group_count"],
            "invalid_preserved_count": report["invalid_preserved_count"],
        },
        "direction_counts": [
            {
                "key": row["key"],
                "row_count": row["row_count"],
                "record_count": row["record_count"],
                "group_count": row["group_count"],
            }
            for row in report["ownership_projection_direction_rollup"]
        ],
        "multi_row_groups": [
            {
                "group_key": row["group_key"],
                "manifest_only_preservation_row_count": row["manifest_only_preservation_row_count"],
                "manifest_row_ids": row["manifest_row_ids"],
            }
            for row in report["multi_row_groups"]
        ],
        "csv": {
            "written": bool(csv_out),
            "row_count": len(report["direction_slice_rows"]) if csv_out else None,
            "header": DIRECTION_SLICE_ROWS_CSV_FIELDS if csv_out else None,
        },
    }


def main() -> None:
    args = parse_args()
    try:
        report_mode_count = (
            int(args.structured_reference_namespace_report)
            + int(args.production_guarded_structured_reference_triage)
            + int(args.preserved_cross_boundary_contract_report)
            + int(args.preserved_cross_boundary_manifest_census)
            + int(args.manifest_only_preservation_triage)
        )
        if report_mode_count > 1:
            raise OverlayError("Only one report mode can be requested at a time.")
        if report_mode_count and args.as_data_js:
            raise OverlayError("report modes cannot be combined with --as-data-js.")
        if args.structured_reference_namespace_report and not args.out:
            raise OverlayError("--structured-reference-namespace-report requires --out.")
        if args.production_guarded_structured_reference_triage and not args.out:
            raise OverlayError("--production-guarded-structured-reference-triage requires --out.")
        if args.preserved_cross_boundary_contract_report and not args.out:
            raise OverlayError("--preserved-cross-boundary-contract-report requires --out.")
        if args.preserved_cross_boundary_manifest_census and not args.out:
            raise OverlayError("--preserved-cross-boundary-manifest-census requires --out.")
        if args.manifest_only_preservation_triage and not args.out:
            raise OverlayError("--manifest-only-preservation-triage requires --out.")
        if args.direction_slice_rows_csv_out and not args.manifest_only_preservation_triage:
            raise OverlayError("--direction-slice-rows-csv-out requires --manifest-only-preservation-triage.")
        if args.review_packet_manifest_out and not args.manifest_only_preservation_triage:
            raise OverlayError("--review-packet-manifest-out requires --manifest-only-preservation-triage.")
        if args.decision_ledger_csv_out and not args.manifest_only_preservation_triage:
            raise OverlayError("--decision-ledger-csv-out requires --manifest-only-preservation-triage.")
        if args.validate_decision_ledger_csv and not args.manifest_only_preservation_triage:
            raise OverlayError("--validate-decision-ledger-csv requires --manifest-only-preservation-triage.")
        if args.decision_ledger_validation_report_out and not args.validate_decision_ledger_csv:
            raise OverlayError("--decision-ledger-validation-report-out requires --validate-decision-ledger-csv.")
        if args.decision_ledger_validation_summary_out and not args.validate_decision_ledger_csv:
            raise OverlayError("--decision-ledger-validation-summary-out requires --validate-decision-ledger-csv.")
        if args.manual_review_readiness_checkpoint_out and not args.validate_decision_ledger_csv:
            raise OverlayError("--manual-review-readiness-checkpoint-out requires --validate-decision-ledger-csv.")
        production = load_production_data(Path(args.production_data))
        fragment = load_fragment(args)
        ownership = load_ownership_scope(Path(args.ownership_manifest))
        if report_mode_count:
            assert_guarded_option_refs_are_not_interiors(production, ownership)
            guarded_ids = guarded_option_ids(production, ownership)
            namespace_report = structured_reference_namespace_report(production, guarded_ids)
            report = namespace_report
            if args.production_guarded_structured_reference_triage:
                report = production_guarded_structured_reference_triage_report(
                    namespace_report,
                    preserved_guarded_option_ids(production, ownership, guarded_ids),
                )
            if args.preserved_cross_boundary_contract_report:
                projected_ids = projected_option_ids(production, ownership.owned_rpos)
                report = preserved_cross_boundary_contract_report(
                    production,
                    fragment,
                    ownership,
                    namespace_report,
                    guarded_ids,
                    projected_ids,
                )
            if args.preserved_cross_boundary_manifest_census:
                projected_ids = projected_option_ids(production, ownership.owned_rpos)
                report = preserved_cross_boundary_manifest_census_report(
                    production,
                    ownership,
                    namespace_report,
                    guarded_ids,
                    projected_ids,
                )
            if args.manifest_only_preservation_triage:
                projected_ids = projected_option_ids(production, ownership.owned_rpos)
                census_report = preserved_cross_boundary_manifest_census_report(
                    production,
                    ownership,
                    namespace_report,
                    guarded_ids,
                    projected_ids,
                )
                report = manifest_only_preservation_triage_report(census_report, production)
            write_or_print_output(format_report_json(report, args.pretty), args.out)
            if args.direction_slice_rows_csv_out:
                write_direction_slice_rows_csv(report["direction_slice_rows"], args.direction_slice_rows_csv_out)
            if args.review_packet_manifest_out:
                packet = manifest_only_review_packet_manifest(report, args.out, args.direction_slice_rows_csv_out)
                write_or_print_output(format_report_json(packet, args.pretty), args.review_packet_manifest_out)
            if args.decision_ledger_csv_out:
                write_decision_ledger_csv(report, args.decision_ledger_csv_out)
            ledger_validation_report = None
            ledger_validation_summary = None
            if args.validate_decision_ledger_csv:
                ledger_validation_report = decision_ledger_validation_report(report, args.validate_decision_ledger_csv)
                if args.decision_ledger_validation_report_out:
                    write_or_print_output(
                        format_report_json(ledger_validation_report, args.pretty),
                        args.decision_ledger_validation_report_out,
                    )
                if args.decision_ledger_validation_summary_out:
                    ledger_validation_summary = decision_ledger_validation_summary(ledger_validation_report)
                    write_or_print_output(
                        format_report_json(ledger_validation_summary, args.pretty),
                        args.decision_ledger_validation_summary_out,
                    )
                if args.manual_review_readiness_checkpoint_out:
                    checkpoint = manual_review_readiness_checkpoint(report, ledger_validation_report, ledger_validation_summary)
                    write_or_print_output(
                        format_report_json(checkpoint, args.pretty),
                        args.manual_review_readiness_checkpoint_out,
                    )
            if namespace_report["unresolved_count"]:
                raise OverlayError(f"blocking unresolved structured refs: {namespace_report['unresolved_count']}.")
            if args.preserved_cross_boundary_contract_report and report["status"] == "blocking":
                raise OverlayError(
                    "preserved cross-boundary contract blocking findings: "
                    f"stale={report['stale_preserved_count']}, "
                    f"unguarded={report['unguarded_production_guarded_count']}, "
                    f"invalid={report['invalid_preserved_count']}, "
                    f"count_parity_ok={report['count_parity_ok']}."
                )
            if args.preserved_cross_boundary_manifest_census and report["status"] == "blocking":
                raise OverlayError(
                    "preserved cross-boundary manifest census blocking findings: "
                    f"invalid={report['invalid_preserved_count']}."
                )
            if args.manifest_only_preservation_triage and report["status"] == "blocking":
                raise OverlayError(
                    "manifest-only preservation triage blocking findings: "
                    f"invalid={report['invalid_preserved_count']}."
                )
            if ledger_validation_report and ledger_validation_report["status"] == "blocking":
                raise OverlayError(
                    "decision ledger validation blocking findings: "
                    f"missing={ledger_validation_report['missing_group_count']}, "
                    f"unknown={ledger_validation_report['unknown_group_count']}, "
                    f"duplicate={ledger_validation_report['duplicate_group_count']}, "
                    f"schema={ledger_validation_report['schema_error_count']}, "
                    f"review={ledger_validation_report['review_value_error_count']}."
                )
            overlay_shadow_data(production, fragment, ownership)
            return
        shadow = overlay_shadow_data(production, fragment, ownership)
        output = format_data_js(shadow, args.pretty) if args.as_data_js else format_shadow_json(shadow, args.pretty)
        write_or_print_output(output, args.out)
    except (OSError, json.JSONDecodeError, OverlayError, KeyError, ValueError) as error:
        print(f"shadow overlay failed: {error}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
