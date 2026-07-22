#!/usr/bin/env python3
"""Shared workbook domain registry.

This package owns declarative workbook family/key/type/enum/reference
registry metadata. The literals below were extracted verbatim from
``corvette_form_generator.editor_ops`` so the editor, lints, and ingest
compiler can share one canonical source of truth.
"""

from __future__ import annotations

from corvette_form_generator.workbook import workbook_truthy

# model_workbook_sources.source_role -> schema family
SOURCE_ROLE_FAMILIES: dict[str, str] = {
    "source_option_sheet": "options",
    "status_sheet": "ovs",
    "rule_mapping_sheet": "rule_mapping",
    "rule_groups_sheet": "rule_groups",
    "rule_group_members_sheet": "rule_group_members",
    "exclusive_groups_sheet": "exclusive_groups",
    "exclusive_group_members_sheet": "exclusive_members",
    "price_rules_sheet": "price_rules",
    "variant_option_overrides_sheet": "variant_overrides",
    "color_overrides_sheet": "color_overrides",
    "interior_source_sheet": "interiors",
}

# Per-family editing metadata. Columns absent from types/enums/refs are
# free text. Headers always come from the sheet itself, never from here.
EDITOR_SHEET_META: dict[str, dict] = {
    "options": {
        "key": ("option_id",),
        "types": {
            "price": "int",
            "display_order": "int",
            "selectable": "bool",
            "active": "bool",
        },
        "enums": {
            "display_behavior": (
                "", "default_selected", "hidden", "display_only", "auto_only",
            ),
        },
        "refs": {"section_id": "sections"},
    },
    "ovs": {
        "key": ("option_id", "variant_id"),
        "types": {},
        "enums": {"status": ("standard", "available", "unavailable")},
        "refs": {"option_id": "options", "variant_id": "variants"},
    },
    "rule_mapping": {
        "key": ("rule_id",),
        "types": {},
        "enums": {
            "rule_type": ("includes", "excludes", "requires"),
            "body_style_scope": ("", "coupe", "convertible"),
            "runtime_action": ("", "replace"),
        },
        "refs": {
            "source_id": "options",
            "target_id": "options",
        },
        "ref_unions": {
            "source_id": ("options", "interiors"),
            "target_id": ("options", "interiors"),
        },
    },
    "rule_groups": {
        "key": ("group_id",),
        "types": {"active": "bool"},
        "enums": {"group_type": ("requires_any", "excludes_any")},
        "refs": {"source_id": "options"},
    },
    "rule_group_members": {
        "key": ("group_id", "target_id"),
        "types": {"display_order": "int", "active": "bool"},
        "enums": {},
        "refs": {"group_id": "rule_groups", "target_id": "options"},
    },
    "exclusive_groups": {
        "key": ("group_id",),
        "types": {"active": "bool"},
        "enums": {
            "selection_mode": (
                "single_within_group", "required_single_within_group",
            ),
        },
        "refs": {},
    },
    "exclusive_members": {
        "key": ("group_id", "option_id"),
        "types": {"display_order": "int", "active": "bool"},
        "enums": {},
        "refs": {"group_id": "exclusive_groups", "option_id": "options"},
    },
    "price_rules": {
        "key": ("price_rule_id",),
        "types": {"price_value": "int"},
        "enums": {"price_rule_type": ("override",)},
        "refs": {
            "condition_option_id": "options",
            "target_option_id": "options",
        },
        "ref_unions": {
            "condition_option_id": ("options", "interiors"),
            "target_option_id": ("options", "interiors"),
        },
    },
    "variant_overrides": {
        "key": ("option_id", "variant_id"),
        "types": {"active": "bool"},
        "enums": {
            "selectable": ("", "True", "False"),
            "display_behavior": ("", "default_selected", "display_only", "hidden"),
        },
        "refs": {
            "option_id": "options",
            "variant_id": "variants",
            "section_id": "sections",
        },
    },
    "color_overrides": {
        "key": ("interior_id", "option_id"),
        "types": {},
        "enums": {"rule_type": ("requires",)},
        "refs": {
            "interior_id": "interiors",
            "option_id": "options",
            "adds_rpo": "options",
        },
    },
    "interiors": {
        "key": ("interior_id",),
        "types": {
            "Price": "int",
            "active_for_stingray": "bool",
            "requires_r6x": "bool",
        },
        "enums": {},
        "refs": {"section_id": "sections", "included_option_id": "options"},
    },
    # ── Global (model-metadata and presentation) families ─────────────
    # Reachable only through explicit sheet names in GLOBAL_SHEET_FAMILIES;
    # the model registry (and therefore the workbook-editor UI and lints)
    # never resolves to these, so existing editor behavior is unchanged.
    "model_master": {
        "key": ("model_key",),
        "types": {"expected_variant_count": "int", "default_model": "bool", "active": "bool"},
        "enums": {},
        "refs": {},
    },
    "model_variants": {
        "key": ("model_key", "variant_id"),
        "types": {"display_order": "int", "active": "bool"},
        "enums": {},
        "refs": {},
    },
    "variant_master": {
        "key": ("variant_id",),
        "types": {"model_year": "int", "base_price": "int", "display_order": "int", "active": "bool"},
        "enums": {},
        "refs": {},
    },
    "model_workbook_sources": {
        "key": ("model_key", "source_role"),
        "types": {"active": "bool"},
        "enums": {"source_role": tuple(SOURCE_ROLE_FAMILIES)},
        "refs": {},
    },
    "model_registry_promotion": {
        "key": ("model_key",),
        "types": {"promoted_to_runtime": "bool", "default_model": "bool", "active": "bool", "display_order": "int"},
        "enums": {},
        "refs": {},
    },
    "model_interior_scope": {
        "key": ("model_key", "interior_id", "trim_level"),
        "types": {"active": "bool"},
        "enums": {},
        "refs": {"interior_id": "interiors", "requires_option_id": "options"},
    },
    "default_selection_rules": {
        "key": ("model_key", "rule_id"),
        "types": {"priority": "int", "active": "bool"},
        "enums": {
            "condition_type": (
                "always",
                "unless_selected_rpo",
                "unless_selected_section",
                "when_selected_unless_selected_section",
            ),
            "display_behavior": ("", "default_selected"),
        },
        "refs": {"target_option_id": "options"},
        "conditional_ref": {"discriminator": "condition_type", "column": "condition_id"},
        "conditional_refs": {
            "always": None,
            "unless_selected_rpo": "option_rpos",
            "unless_selected_section": "sections",
            "when_selected_unless_selected_section": "options",
        },
    },
    "asset_map": {
        "key": ("model_key", "target_type", "target_id"),
        "types": {"active": "bool"},
        "enums": {},
        "refs": {},
        "conditional_ref": {"discriminator": "target_type", "column": "target_id"},
        "conditional_refs": {"option": "options"},
    },
    "interior_components": {
        "key": ("model_key", "interior_id", "rpo", "component_type"),
        "types": {"display_order": "int", "active": "bool"},
        "enums": {},
        "refs": {"interior_id": "interiors"},
    },
    "runtime_steps_meta": {
        "key": ("model_key", "step_key"),
        "types": {"runtime_order": "int", "active": "bool"},
        "enums": {},
        "refs": {},
    },
    "section_presentation_meta": {
        "key": ("model_key", "section_id"),
        "types": {"section_display_order": "int", "active": "bool"},
        "enums": {},
        "refs": {"section_id": "sections"},
    },
    "context_section_master_meta": {
        "key": ("model_key", "context_type", "section_id"),
        "types": {"is_required": "bool", "section_display_order": "int", "active": "bool"},
        "enums": {},
        "refs": {},
    },
    "order_summary_sections_meta": {
        "key": ("model_key", "section_key"),
        "types": {"display_order": "int", "active": "bool"},
        "enums": {},
        "refs": {},
    },
    "step_order_summary_map_meta": {
        "key": ("model_key", "step_key", "section_key"),
        "types": {"active": "bool"},
        "enums": {},
        "refs": {},
    },
}

# Fixed sheet-name -> family mapping for global sheets. Kept out of
# model_sheet_registry on purpose: only batch preparation/apply consult it.
GLOBAL_SHEET_FAMILIES: dict[str, str] = {
    "model_master": "model_master",
    "model_variants": "model_variants",
    "variant_master": "variant_master",
    "model_workbook_sources": "model_workbook_sources",
    "model_registry_promotion": "model_registry_promotion",
    "model_interior_scope": "model_interior_scope",
    "default_selection_rules": "default_selection_rules",
    "asset_map": "asset_map",
    "interior_components": "interior_components",
    "runtime_steps": "runtime_steps_meta",
    "section_presentation": "section_presentation_meta",
    "context_section_master": "context_section_master_meta",
    "order_summary_sections": "order_summary_sections_meta",
    "step_order_summary_map": "step_order_summary_map_meta",
}


def family_spec(name: str) -> dict:
    try:
        return EDITOR_SHEET_META[name]
    except KeyError as exc:
        raise KeyError(f"Unknown workbook family: {name}") from exc


def registered_sheet_families(extract: dict) -> dict[str, str]:
    result = dict(GLOBAL_SHEET_FAMILIES)
    rows = extract.get("sheets", {}).get("model_workbook_sources", {}).get("rows", [])
    for row in rows:
        if not workbook_truthy(row.get("active")):
            continue
        family = SOURCE_ROLE_FAMILIES.get(str(row.get("source_role") or ""))
        sheet = str(row.get("sheet_name") or "")
        if family and sheet:
            result[sheet] = family
    return result
