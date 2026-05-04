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


class OverlayError(ValueError):
    pass


class OwnershipScope:
    def __init__(
        self,
        owned_rpos: set[str],
        guarded_option_refs: set[tuple[str, str]],
        preserved_cross_boundary_records: set[tuple[str, str, str, str, str]],
        guarded_group_ids: dict[str, set[str]],
        preserved_group_ids: dict[str, set[str]],
        projected_group_ids: dict[str, set[str]],
    ) -> None:
        self.owned_rpos = owned_rpos
        self.guarded_option_refs = guarded_option_refs
        self.preserved_cross_boundary_records = preserved_cross_boundary_records
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

    return OwnershipScope(
        owned_rpos=owned_rpos,
        guarded_option_refs=guarded_option_refs,
        preserved_cross_boundary_records=preserved_cross_boundary_records,
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


def structured_record_refs(data: dict[str, Any]) -> list[dict[str, str]]:
    refs: list[dict[str, str]] = []
    for row in data.get("rules", []):
        if row.get("source_id"):
            refs.append({"surface": "rules", "field": "source_id", "id": row["source_id"]})
        if row.get("target_id"):
            refs.append({"surface": "rules", "field": "target_id", "id": row["target_id"]})
    for row in data.get("priceRules", []):
        if row.get("condition_option_id"):
            refs.append({"surface": "priceRules", "field": "condition_option_id", "id": row["condition_option_id"]})
        if row.get("target_option_id"):
            refs.append({"surface": "priceRules", "field": "target_option_id", "id": row["target_option_id"]})
    for row in data.get("ruleGroups", []):
        if row.get("source_id"):
            refs.append({"surface": "ruleGroups", "field": "source_id", "id": row["source_id"]})
        refs.extend(
            {"surface": "ruleGroups", "field": "target_ids", "id": target_id}
            for target_id in row.get("target_ids", [])
            if target_id
        )
    for row in data.get("exclusiveGroups", []):
        refs.extend(
            {"surface": "exclusiveGroups", "field": "option_ids", "id": option_id}
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
        ref_id = ref["id"]
        if ref_id in valid_ids:
            continue
        key = (ref["surface"], ref["field"], ref_id)
        if key in seen:
            continue
        seen.add(key)
        unknown.append(ref)
    if unknown:
        raise OverlayError(f"unknown structured non-choice refs: {unknown[:5]}.")


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


def main() -> None:
    args = parse_args()
    try:
        production = load_production_data(Path(args.production_data))
        fragment = load_fragment(args)
        ownership = load_ownership_scope(Path(args.ownership_manifest))
        shadow = overlay_shadow_data(production, fragment, ownership)
        output = format_data_js(shadow, args.pretty) if args.as_data_js else format_shadow_json(shadow, args.pretty)
        if args.out:
            output_path = Path(args.out)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(output + "\n", encoding="utf-8")
        else:
            print(output)
    except (OSError, json.JSONDecodeError, OverlayError, KeyError, ValueError) as error:
        print(f"shadow overlay failed: {error}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
