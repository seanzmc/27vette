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
SUPPORTED_OWNERSHIP_VALUES = {"projected_owned", "preserved_cross_boundary"}
SUPPORTED_RECORD_TYPES = {"selectable", "rule", "priceRule"}


class OverlayError(ValueError):
    pass


class OwnershipScope:
    def __init__(self, owned_rpos: set[str], preserved_cross_boundary_records: set[tuple[str, str, str]]) -> None:
        self.owned_rpos = owned_rpos
        self.preserved_cross_boundary_records = preserved_cross_boundary_records


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
    preserved_cross_boundary_records: set[tuple[str, str, str]] = set()
    seen_owned_rpos: set[str] = set()
    seen_preserved_records: set[tuple[str, str, str]] = set()

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

        if ownership == "projected_owned":
            rpo = row.get("rpo", "")
            if not rpo:
                raise OverlayError(f"{path} row {index} projected_owned row is missing rpo.")
            if record_type != "selectable":
                raise OverlayError(f"{path} row {index} projected_owned row must use record_type selectable.")
            if rpo in seen_owned_rpos:
                raise OverlayError(f"{path} has duplicate active projected_owned RPO {rpo}.")
            seen_owned_rpos.add(rpo)
            owned_rpos.add(rpo)
            continue

        source_rpo = row.get("source_rpo", "")
        target_rpo = row.get("target_rpo", "")
        if not source_rpo or not target_rpo:
            raise OverlayError(f"{path} row {index} preserved_cross_boundary row is missing source_rpo or target_rpo.")
        if row.get("rpo", ""):
            raise OverlayError(f"{path} row {index} preserved_cross_boundary row should not set rpo.")
        if record_type == "selectable":
            raise OverlayError(f"{path} row {index} preserved_cross_boundary row must use rule or priceRule.")
        key = (record_type, source_rpo, target_rpo)
        if key in seen_preserved_records:
            raise OverlayError(f"{path} has duplicate active preserved_cross_boundary row {key}.")
        seen_preserved_records.add(key)
        preserved_cross_boundary_records.add(key)

    return OwnershipScope(owned_rpos=owned_rpos, preserved_cross_boundary_records=preserved_cross_boundary_records)


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


def option_id_by_rpo(data: dict[str, Any], rpo: str) -> str:
    option_ids = {row["option_id"] for row in data.get("choices", []) if row.get("rpo") == rpo}
    if len(option_ids) != 1:
        raise OverlayError(f"Expected exactly one production option_id for RPO {rpo}, found {sorted(option_ids)}.")
    return next(iter(option_ids))


def preserved_record_id_keys(data: dict[str, Any], ownership: OwnershipScope) -> dict[str, set[tuple[str, str]]]:
    keys = {"rules": set(), "priceRules": set()}
    surface_by_record_type = {"rule": "rules", "priceRule": "priceRules"}
    for record_type, source_rpo, target_rpo in ownership.preserved_cross_boundary_records:
        surface = surface_by_record_type[record_type]
        keys[surface].add((option_id_by_rpo(data, source_rpo), option_id_by_rpo(data, target_rpo)))
    return keys


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
        if not any(item in projected_ids for item in ids):
            continue
        if any(item and item not in projected_ids for item in ids):
            if tuple(ids) not in preserved_keys and normalized_json(row) not in fragment_records:
                unclassified_cross_boundary.append(row)
            continue
        if tuple(ids) not in fragment_keys:
            dropped.append(row)
    if unclassified_cross_boundary:
        raise OverlayError(f"{surface} has unclassified cross-boundary records: {unclassified_cross_boundary[:5]}.")
    if dropped:
        raise OverlayError(f"{surface} has unreplaced migrated-slice-owned records: {dropped[:5]}.")


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
    production_ids = projected_option_ids(production, rpos)
    fragment_ids = projected_option_ids(fragment, rpos)
    if production_ids != fragment_ids:
        raise OverlayError(f"Fragment legacy option IDs do not match production: {sorted(production_ids)} != {sorted(fragment_ids)}.")
    preserved_keys_by_surface = preserved_record_id_keys(production, ownership)

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

    assert_same_normalized("choices", normalize_choices(removed_choices), normalize_choices(fragment.get("choices", [])))
    assert_same_normalized("rules", normalize_rules(removed_rules), normalize_rules(fragment.get("rules", [])))
    assert_same_normalized("priceRules", normalize_price_rules(removed_price_rules), normalize_price_rules(fragment.get("priceRules", [])))
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
    unreplaced_exclusive_groups = [
        row
        for row in production.get("exclusiveGroups", [])
        if any(option_id in production_ids for option_id in row.get("option_ids", [])) and row.get("group_id") not in fragment_exclusive_group_keys
    ]
    if unreplaced_exclusive_groups:
        raise OverlayError(f"exclusiveGroups has unreplaced migrated-slice-owned records: {unreplaced_exclusive_groups[:5]}.")

    shadow = clone(production)
    shadow["variants"] = clone(production.get("variants", []))
    shadow["ruleGroups"] = clone(production.get("ruleGroups", []))
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
