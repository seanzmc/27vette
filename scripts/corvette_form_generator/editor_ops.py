#!/usr/bin/env python3
"""Workbook-editor sheet metadata (Phase 1).

The workbook owns its data; this module owns only what the workbook cannot
express about itself: which columns form each sheet family's primary key,
intended cell types, enum domains, and which columns reference other
workbook entities. Keyed by the schema *family* names that
``model_workbook_sources.source_role`` values map onto.

Phase 2 adds op schema, coalescing, typed apply, and non-breaking
validation here (see workbook-editor-integration-spec.md §4.4).
"""

from __future__ import annotations

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
            "normalization_status": ("active", "omitted", "replaced", "preserved"),
        },
        "refs": {
            "source_id": "options",
            "target_id": "options",
            "source_section": "sections",
            "target_section": "sections",
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
        "refs": {"interior_id": "interiors", "option_id": "options"},
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
}
