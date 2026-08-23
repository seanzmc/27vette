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

# Promotable artifact-type domain. Owned here so schema validation, promotion
# parsing, and the editor cannot drift into three different vocabularies.
#
# Pass 3 requirement 7 narrowed this to one value. `current_generation` published
# whatever happened to sit at a generator's output path, and `draft_artifact`
# published a review artifact; both bypassed the guarantee that what reaches the
# browser is a strictly validated runtime contract. A promoted row now names its
# contract explicitly or it does not publish.
REGISTRY_PROMOTION_ARTIFACT_TYPES: tuple[str, ...] = ("runtime_contract",)
DEFAULT_REGISTRY_PROMOTION_ARTIFACT_TYPE = "runtime_contract"

GROUP_DISPLAY_LABEL_MIN_LENGTH = 3
GROUP_DISPLAY_LABEL_MAX_LENGTH = 100
GROUP_DISPLAY_LABEL_PLACEHOLDERS = frozenset({
    "Related options",
    "Unnamed group",
    "Label pending workbook review",
})
GROUP_DISPLAY_LABEL_HASH_SUFFIX_PATTERN = r"[_-]([0-9a-f]{6,})$"

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
        "ref_unions": {"source_id": ("options", "interiors")},
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
        "types": {"selectable": "bool", "active": "bool"},
        "enums": {
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
        "types": {"model_year": "int", "expected_variant_count": "int", "default_model": "bool", "active": "bool"},
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
        "enums": {"artifact_type": REGISTRY_PROMOTION_ARTIFACT_TYPES},
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
        "enums": {"image_fit": ("cover", "contain", "swatch")},
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

# Complete workbook-writable column ownership. These tuples include free-text
# fields as well as typed/reference fields; consumers must not infer writable
# columns from a physical sheet or from the partial type maps above.
WRITABLE_COLUMNS: dict[str, tuple[str, ...]] = {
    "options": ("option_id", "rpo", "price", "option_name", "description", "detail_raw", "section_id", "selectable", "display_order", "active", "display_behavior"),
    "ovs": ("option_id", "variant_id", "status"),
    "rule_mapping": ("rule_id", "source_id", "rule_type", "target_id", "original_detail_raw", "body_style_scope", "runtime_action", "disabled_reason"),
    "rule_groups": ("group_id", "display_label", "group_type", "source_id", "body_style_scope", "trim_level_scope", "variant_scope", "disabled_reason", "active", "notes"),
    "rule_group_members": ("group_id", "target_id", "display_order", "active"),
    "exclusive_groups": ("group_id", "display_label", "selection_mode", "active", "notes"),
    "exclusive_members": ("group_id", "option_id", "display_order", "active"),
    "price_rules": ("price_rule_id", "condition_option_id", "price_rule_type", "target_option_id", "price_value", "body_style_scope", "trim_level_scope", "notes"),
    "variant_overrides": ("option_id", "variant_id", "selectable", "display_behavior", "section_id", "active", "note"),
    "color_overrides": ("interior_id", "option_id", "rule_type", "adds_rpo"),
    "interiors": ("interior_id", "Interior Name", "Material", "Price", "Detail from Disclosure", "Color Overrides", "Trim", "Seat", "Interior Code", "Suede", "Stitch", "Two Tone", "section_id", "active_for_stingray", "requires_r6x", "included_option_id"),
    "model_master": ("model_key", "registry_key", "model_label", "model_year", "dataset_name", "export_slug", "expected_variant_count", "default_model", "active", "setup_card_subtitle", "setup_eyebrow", "setup_title", "setup_description", "setup_fact_1", "setup_fact_2", "setup_fact_3", "notes"),
    "model_variants": ("model_key", "variant_id", "display_order", "active", "notes"),
    "variant_master": ("variant_id", "model_year", "trim_level", "body_style", "display_name", "base_price", "display_order", "active"),
    "model_workbook_sources": ("model_key", "source_role", "sheet_name", "active", "notes"),
    "model_registry_promotion": ("model_key", "registry_key", "promoted_to_runtime", "default_model", "artifact_path", "artifact_type", "legacy_alias", "active", "display_order", "notes"),
    "model_interior_scope": ("model_key", "interior_id", "trim_level", "active", "requires_option_id", "notes", "interior_seat_label", "interior_color_family", "interior_material_family", "interior_variant_label", "interior_group_display_order", "interior_material_display_order", "interior_choice_display_order", "interior_hierarchy_levels", "interior_parent_group_label", "interior_leaf_label", "interior_reference_order", "grouping_source"),
    "default_selection_rules": ("model_key", "rule_id", "target_option_id", "condition_type", "condition_id", "body_style_scope", "trim_level_scope", "variant_scope", "priority", "active", "notes", "display_behavior"),
    "asset_map": ("model_key", "target_type", "target_id", "image_url", "image_alt", "image_fit", "image_position", "hover_image_url", "hover_image_alt", "hover_image_position", "active", "notes"),
    "interior_components": ("model_key", "interior_id", "rpo", "component_type", "label", "price_ref_type", "price_ref_code", "price_trim_scope", "display_order", "active", "notes"),
    "runtime_steps_meta": ("model_key", "step_key", "step_label", "runtime_order", "source", "active", "notes"),
    "section_presentation_meta": ("model_key", "section_id", "display_label", "step_key", "display_behavior", "section_display_order", "standard_equipment_bucket", "standard_equipment_group_type", "auto_added_bucket", "active", "notes"),
    "context_section_master_meta": ("model_key", "context_type", "section_id", "section_name", "selection_mode", "choice_mode", "is_required", "standard_behavior", "section_display_order", "step_key", "step_label", "active", "notes"),
    "order_summary_sections_meta": ("model_key", "section_key", "section_label", "display_order", "active", "notes"),
    "step_order_summary_map_meta": ("model_key", "step_key", "section_key", "active", "notes"),
}

# Blanks are accepted only for explicitly optional writable columns. Required
# sets are authored independently for add and effective-active-row checks so a
# manager cannot infer business requiredness from type or reference shape.
OPTIONAL_COLUMNS: dict[str, tuple[str, ...]] = {
    "options": ("rpo", "price", "description", "detail_raw", "display_order", "display_behavior"),
    "rule_mapping": ("original_detail_raw", "body_style_scope", "runtime_action", "disabled_reason"),
    # Checkpoint 2B: display_label is deliberate human copy, optional until the
    # approved migration (Checkpoint 2D) fills it. Blank means label pending.
    "rule_groups": ("display_label", "body_style_scope", "trim_level_scope", "variant_scope", "disabled_reason", "notes"),
    "exclusive_groups": ("display_label", "notes"),
    "rule_group_members": ("display_order",),
    "price_rules": ("body_style_scope", "trim_level_scope", "notes"),
    "variant_overrides": ("selectable", "display_behavior", "section_id", "note"),
    "interiors": ("Detail from Disclosure", "Color Overrides", "Suede", "Stitch", "Two Tone", "included_option_id"),
    "model_variants": ("notes",),
    "model_workbook_sources": ("notes",),
    "model_registry_promotion": ("legacy_alias", "notes"),
    "model_interior_scope": (
        "requires_option_id",
        "interior_group_display_order",
        "interior_material_display_order",
        "interior_choice_display_order",
        "interior_reference_order",
    ),
    "default_selection_rules": ("condition_id", "body_style_scope", "trim_level_scope", "variant_scope", "display_behavior"),
    "asset_map": ("image_alt", "hover_image_url", "hover_image_alt", "hover_image_position", "notes"),
    "section_presentation_meta": ("display_label", "step_key", "display_behavior", "section_display_order", "standard_equipment_bucket", "standard_equipment_group_type", "auto_added_bucket"),
    "context_section_master_meta": ("section_display_order",),
}

for _family, _meta in EDITOR_SHEET_META.items():
    _columns = WRITABLE_COLUMNS[_family]
    _explicit_optional = set(OPTIONAL_COLUMNS.get(_family, ()))
    _required_set = set(_meta["key"])
    _required_set.update(_meta.get("types", ()))
    _required_set.update(
        column
        for column, values in _meta.get("enums", {}).items()
        if "" not in values
    )
    _required_set.update(_meta.get("refs", ()))
    _conditional = _meta.get("conditional_ref") or {}
    if _conditional.get("discriminator"):
        _required_set.add(_conditional["discriminator"])
    _required_set.difference_update(_explicit_optional)
    _required = tuple(column for column in _columns if column in _required_set)
    _optional = tuple(column for column in _columns if column not in _required_set)
    _meta["columns"] = _columns
    _meta["optional_columns"] = _optional
    _meta["required_on_add"] = _required
    _meta["required_on_effective_active_row"] = _required

# ── Checkpoint 3B field-control metadata (spec §10.1) ─────────────────
#
# Every writable field above has an explicit control entry in FIELD_CONTROLS;
# absence of a control is an error, never an implicit free-text input. Kinds
# come from the §10.1 vocabulary in CONTROL_KINDS. Finite values are encoded
# only for domains proven per §19.3 (workbook rows + generator parsing +
# runtime consumers); unproven candidate vocabularies stay deliberate text and
# are listed in the owning specification's unresolved-domain inventory.
#
# blank semantics: "forbidden" = registry-required, must be non-blank;
# "allowed" = optional or the registered domain contains "" (blank means
# inherit/unset); "never_blank_key" = key columns, required always.
CONTROL_KINDS: frozenset[str] = frozenset((
    "boolean", "finite", "reference", "integer", "money", "url",
    "structured_text", "short_text", "long_text",
    "immutable", "generated", "read_only",
))


def humanize(name: str) -> str:
    """Human label from a column name ('section_display_order' ->
    'Section display order'). Header spellings pass through unchanged."""
    cleaned = name.replace("_", " ").strip()
    return cleaned[:1].upper() + cleaned[1:] if cleaned else cleaned


# Free-text controls are named explicitly. Structural type/enum/reference
# metadata below remains deliberate registry metadata, but a new untyped
# writable field gets no control until it is added to one of these sets. That is
# what makes the §10.8 missing-control test capable of failing.
LONG_FORM_FIELDS: frozenset[str] = frozenset((
    "description", "detail_raw", "original_detail_raw", "disabled_reason",
    "notes", "note", "setup_description", "section_name", "display_name",
    "interior_seat_label", "interior_parent_group_label", "interior_leaf_label",
    "interior_variant_label", "interior_color_family", "interior_material_family",
))

SHORT_FORM_FIELDS: frozenset[str] = frozenset((
    "Color Overrides", "Detail from Disclosure", "Interior Code",
    "Interior Name", "Material", "Seat", "Stitch", "Suede", "Trim",
    "Two Tone", "artifact_path", "body_style", "choice_mode",
    "context_type", "dataset_name", "display_behavior", "display_label",
    "export_slug", "group_id", "grouping_source", "hover_image_alt",
    "hover_image_position", "image_alt", "image_position",
    "interior_choice_display_order", "interior_group_display_order",
    "interior_hierarchy_levels", "interior_id",
    "interior_material_display_order", "interior_reference_order", "label",
    "legacy_alias", "model_key", "model_label", "option_id", "option_name",
    "price_ref_code", "price_ref_type", "price_rule_id", "price_trim_scope",
    "registry_key", "rpo", "rule_id", "section_id", "section_key",
    "section_label", "setup_card_subtitle", "setup_eyebrow", "setup_fact_1",
    "setup_fact_2", "setup_fact_3", "setup_title", "sheet_name", "source",
    "standard_behavior", "step_key", "step_label", "target_type",
    "trim_level", "variant_id",
))

STRUCTURED_TEXT_FIELDS: frozenset[str] = frozenset((
    "body_style_scope", "trim_level_scope", "variant_scope",
))

URL_FIELDS: frozenset[str] = frozenset(("image_url", "hover_image_url"))

# Boolean-with-inherit columns: workbook authors only True or blank; blank
# inherits False through runtime_metadata.presentation_bool().
BOOLEAN_INHERIT_BLANK: frozenset[tuple[str, str]] = frozenset((
    ("section_presentation_meta", "standard_equipment_bucket"),
    ("section_presentation_meta", "auto_added_bucket"),
))

# Proven finite domains (§19.3 evidence recorded inline):
# - interior_components.component_type: five authored values across 1,044
#   workbook rows; consumed by interiors.py/runtime_metadata.py assembly.
# - context_section_master_meta.selection_mode: exact parity with the
#   generator's SELECTION_MODE_LABELS customer-label vocabulary
#   (model_configs.py); observed rows use single_select_req.
# - section_presentation_meta.standard_equipment_group_type: only "" /
#   "trim_equipment" authored; app.js compares === "trim_equipment".
PROVEN_FINITE_VALUES: dict[tuple[str, str], tuple[str, ...]] = {
    ("interior_components", "component_type"): (
        "seat", "suede", "stitching", "r6x", "two_tone",
    ),
    ("context_section_master_meta", "selection_mode"): (
        "single_select_req", "single_select_opt", "multi_select_opt",
        "display_only",
    ),
    ("section_presentation_meta", "standard_equipment_group_type"): (
        "", "trim_equipment",
    ),
}


def _controls_for(family: str) -> dict[str, dict]:
    """Build controls from deliberate structural and text classifications."""
    meta = EDITOR_SHEET_META[family]
    keys = set(meta["key"])
    types = meta.get("types", {})
    enums = meta.get("enums", {})
    refs = meta.get("refs", {})
    unions = meta.get("ref_unions", {})
    conditional_column = (meta.get("conditional_ref") or {}).get("column")
    optional = set(meta.get("optional_columns", ()))
    controls: dict[str, dict] = {}
    for order, column in enumerate(WRITABLE_COLUMNS[family], start=1):
        label = humanize(column)
        proven = PROVEN_FINITE_VALUES.get((family, column))
        inherit_blank = (family, column) in BOOLEAN_INHERIT_BLANK
        if refs.get(column) or unions.get(column) or column == conditional_column:
            kind = "reference"
        elif proven:
            kind = "finite"
        elif enums.get(column):
            kind = "finite"
        elif types.get(column) == "bool" or inherit_blank:
            kind = "boolean"
        elif types.get(column) == "int":
            # Price-shaped names are whole-dollar MSRP contributions (§10.1).
            kind = "money" if "price" in column.lower() else "integer"
        elif column in URL_FIELDS:
            kind = "url"
        elif column in STRUCTURED_TEXT_FIELDS:
            kind = "structured_text"
        elif column in LONG_FORM_FIELDS:
            kind = "long_text"
        elif column in SHORT_FORM_FIELDS:
            kind = "short_text"
        else:
            # Fail closed: the exhaustive inventory test and Manager schema
            # construction report the family/field instead of silently exposing
            # an arbitrary text input.
            continue
        # Blank semantics are one rule for every kind: blank is meaningful
        # when the field is registry-optional, the registered domain contains
        # "", or the column inherits on blank (presentation_bool).
        blank_allowed = (
            column in optional
            or "" in enums.get(column, ())
            or inherit_blank
        )
        kind = "finite" if proven else kind
        values = tuple(proven or enums.get(column, ()))
        controls[column] = {
            "kind": kind,
            "label": label,
            "group": humanize(family),
            "order": order,
            "blank": "never_blank_key" if column in keys
            else ("allowed" if blank_allowed else "forbidden"),
            "help": {
                "boolean": "Choose Yes or No; use inherit only when blank is allowed.",
                "finite": "Choose one registered value.",
                "reference": "Choose a current referenced record by human label.",
                "integer": "Enter a whole number.",
                "money": "Enter a whole-dollar amount.",
                "url": "Enter the complete media URL.",
                "structured_text": "Enter the registered structured scope syntax.",
                "short_text": "Enter the workbook value for this field.",
                "long_text": "Enter the workbook copy or notes for this field.",
            }[kind],
            "affects": (family,),
            **({"values": values} if values else {}),
            **({"values": ("True", "False")} if kind == "boolean" else {}),
            **({"step": 1} if kind in ("integer", "money") else {}),
            **({"source": "projection_reference_options"}
               if kind == "reference" else {}),
            # Keys stay locked on update (§10.3); the structural kind above
            # still drives add-flow rendering and domain validation.
            **({"immutable_on_edit": True} if column in keys else {}),
        }
    return controls


for _family in WRITABLE_COLUMNS:
    EDITOR_SHEET_META[_family]["controls"] = _controls_for(_family)

# Compatibility/public convenience alias. The family-owned mapping above is
# authoritative; consumers must not maintain a parallel list.
FIELD_CONTROLS: dict[str, dict[str, dict]] = {
    family: meta["controls"] for family, meta in EDITOR_SHEET_META.items()
}


def normalize_control(entry: dict) -> dict:
    """Normalized public shape for schema responses (§10.2)."""
    return {key: entry[key] for key in sorted(entry)}


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


# Read-only workbook families. These are never writable through the editor or
# the Workbook Manager, but their shape is still shared contract: the manager
# projects them and reference validation resolves against them. Keeping them
# here stops consumers from hand-authoring a second copy of the columns.
READONLY_SHEET_META: dict[str, dict] = {
    "sections": {
        "sheet": "section_master",
        "key": ("section_id",),
        "columns": (
            "section_id",
            "section_name",
            "selection_mode",
            "is_required",
            "display_order",
            "standard_behavior",
            "step_key",
        ),
        "types": {"is_required": "bool", "display_order": "int"},
        "label": "Sections (master)",
        "id_prefixes": ("sec_",),
    },
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


def active_model_keys(extract: dict) -> set[str]:
    rows = extract.get("sheets", {}).get("model_master", {}).get("rows", [])
    return {
        str(row.get("model_key")).strip()
        for row in rows
        if workbook_truthy(row.get("active")) and str(row.get("model_key") or "").strip()
    }


def models_for_write_targets(extract: dict, targets) -> set[str]:
    """Return the models a set of workbook write targets can affect.

    Deliberately widening, never narrowing. A row in a global family can change
    any model's generated output, so a global target marks every active model as
    touched. Callers use this for *reporting* which models changed; it must
    never be used to skip generating or validating a model.
    """

    sheet_families = registered_sheet_families(extract)
    models_by_sheet: dict[str, set[str]] = {}
    for row in extract.get("sheets", {}).get("model_workbook_sources", {}).get("rows", []):
        if not workbook_truthy(row.get("active")):
            continue
        sheet = str(row.get("sheet_name") or "")
        model_key = str(row.get("model_key") or "").strip()
        if sheet and model_key:
            models_by_sheet.setdefault(sheet, set()).add(model_key)

    touched: set[str] = set()
    saw_global = False
    for target in targets:
        sheet = str(target.get("sheet") or "").strip()
        if sheet not in sheet_families:
            raise KeyError(f"Unregistered workbook sheet: {sheet!r}")
        if sheet in GLOBAL_SHEET_FAMILIES:
            saw_global = True
            continue
        touched.update(models_by_sheet.get(sheet, set()))
    if saw_global:
        # Union, never replace. model_master activeness and source-sheet
        # registration disagree for scaffold models, and a target already
        # collected must not be dropped by widening.
        touched.update(active_model_keys(extract))
        for owners in models_by_sheet.values():
            touched.update(owners)
    return touched
