"""Declarative table specs: the single map between workbook sheets and the
normalized SQLite schema.

Every import, validation, staging, dependency, and sync decision derives from
these specs. Sheet families and key/type/enum/ref metadata intentionally mirror
``scripts/corvette_form_generator/editor_ops.EDITOR_SHEET_META`` so that the
sync layer can hand validated changes to the existing gated write pipeline
(``editor_ops.apply_batch`` -> ``save_workbook_safely``) without translation
surprises.

Scoping facts verified against stingray_master.xlsx (2026-07-15):
- ``option_id`` is unique per options sheet but overlaps heavily across models
  (e.g. 186 shared ids between stingray and grand_sport) => model-scoped
  uniqueness ``UNIQUE(model_id, option_id)``.
- ``rule_id``/``group_id``/``price_rule_id`` currently never collide across
  models, but are still stored model-scoped for safety.
- ``interior_id`` is globally unique across lt_interiors and LZ_Interiors.
- Per-model sheet membership comes from the ``model_workbook_sources`` sheet
  (source_role -> sheet_name), never from hardcoded sheet lists.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ColumnSpec:
    header: str                  # exact workbook header
    name: str = ""               # SQL column name (defaults to sanitized header)
    ctype: str = "text"          # text | int | bool
    enum: tuple = ()             # allowed canonical values ('' allowed if present)

    def sql_name(self) -> str:
        return self.name or sanitize_identifier(self.header)


@dataclass(frozen=True)
class RefSpec:
    column: str                  # SQL column carrying the reference
    target_table: str            # referenced table
    target_column: str           # referenced column (canonical id)
    scope: str = "global"        # global | model | model_union
    union_tables: tuple = ()     # for scope=model_union: tables searched in order
    optional: bool = True        # blank value allowed


@dataclass(frozen=True)
class TableSpec:
    table: str
    # exactly one of `sheet` (fixed sheet name(s)) or `role` (model_workbook_sources
    # source_role) identifies where rows live in the workbook.
    sheet: tuple = ()            # fixed sheet name(s); >1 merges (interiors)
    role: str = ""               # model-scoped source role
    key: tuple = ()              # canonical key columns (within scope)
    columns: tuple = ()          # ColumnSpec, ordered as in workbook
    refs: tuple = ()             # RefSpec
    model_scoped: bool = False   # True => model_id column added from registry
    has_model_key_column: bool = False  # sheet itself carries model_key
    editable: bool = False       # sync path exists via editor_ops.apply_batch
    editor_family: str = ""      # EDITOR_SHEET_META family name for sync ops
    id_prefixes: tuple = ()      # confirmed strippable prefixes for display ids
    label: str = ""              # human label override

    def sql_columns(self) -> list[str]:
        return [c.sql_name() for c in self.columns]

    def column_by_name(self, name: str) -> ColumnSpec | None:
        for c in self.columns:
            if c.sql_name() == name:
                return c
        return None


def sanitize_identifier(header: str) -> str:
    out = "".join(ch.lower() if ch.isalnum() else "_" for ch in header.strip())
    while "__" in out:
        out = out.replace("__", "_")
    return out.strip("_")


BOOL = "bool"
INT = "int"

_ACTIVE = ColumnSpec("active", ctype=BOOL)
_NOTES = ColumnSpec("notes")
_DISPLAY_ORDER = ColumnSpec("display_order", ctype=INT)

DISPLAY_BEHAVIOR_ENUM = ("", "default_selected", "hidden", "display_only", "auto_only")
OVS_STATUS_ENUM = ("standard", "available", "unavailable")
RULE_TYPE_ENUM = ("includes", "excludes", "requires")
BODY_SCOPE_ENUM = ("", "coupe", "convertible")


TABLE_SPECS: tuple[TableSpec, ...] = (
    # ── Model metadata ────────────────────────────────────────────────
    TableSpec(
        table="models", sheet=("model_master",), key=("model_key",),
        columns=(
            ColumnSpec("model_key"), ColumnSpec("registry_key"),
            ColumnSpec("model_label"), ColumnSpec("model_year", ctype=INT),
            ColumnSpec("dataset_name"), ColumnSpec("export_slug"),
            ColumnSpec("expected_variant_count", ctype=INT),
            ColumnSpec("default_model", ctype=BOOL), _ACTIVE,
            ColumnSpec("setup_card_subtitle"), ColumnSpec("setup_eyebrow"),
            ColumnSpec("setup_title"), ColumnSpec("setup_description"),
            ColumnSpec("setup_fact_1"), ColumnSpec("setup_fact_2"),
            ColumnSpec("setup_fact_3"), _NOTES,
        ),
        has_model_key_column=True, editable=True, editor_family="model_master",
    ),
    TableSpec(
        table="model_registry_promotion", sheet=("model_registry_promotion",),
        key=("model_key",),
        columns=(
            ColumnSpec("model_key"), ColumnSpec("registry_key"),
            ColumnSpec("promoted_to_runtime", ctype=BOOL),
            ColumnSpec("default_model", ctype=BOOL),
            ColumnSpec("artifact_path"), ColumnSpec("artifact_type"),
            ColumnSpec("legacy_alias"), _ACTIVE, _DISPLAY_ORDER, _NOTES,
        ),
        refs=(RefSpec("model_key", "models", "model_key", optional=False),),
        has_model_key_column=True, editable=True,
        editor_family="model_registry_promotion",
    ),
    TableSpec(
        table="variants", sheet=("variant_master",), key=("variant_id",),
        columns=(
            ColumnSpec("variant_id"), ColumnSpec("model_year", ctype=INT),
            ColumnSpec("trim_level"), ColumnSpec("body_style"),
            ColumnSpec("display_name"), ColumnSpec("base_price", ctype=INT),
            _DISPLAY_ORDER, _ACTIVE,
        ),
        editable=True, editor_family="variant_master",
    ),
    TableSpec(
        table="model_variants", sheet=("model_variants",),
        key=("model_key", "variant_id"),
        columns=(
            ColumnSpec("model_key"), ColumnSpec("variant_id"),
            _DISPLAY_ORDER, _ACTIVE, _NOTES,
        ),
        refs=(
            RefSpec("model_key", "models", "model_key", optional=False),
            RefSpec("variant_id", "variants", "variant_id", optional=False),
        ),
        has_model_key_column=True, editable=True, editor_family="model_variants",
    ),
    TableSpec(
        table="sheet_registry", sheet=("model_workbook_sources",),
        key=("model_key", "source_role"),
        columns=(
            ColumnSpec("model_key"), ColumnSpec("source_role"),
            ColumnSpec("sheet_name"), _ACTIVE, _NOTES,
        ),
        refs=(RefSpec("model_key", "models", "model_key", optional=False),),
        has_model_key_column=True, editable=True,
        editor_family="model_workbook_sources", label="Workbook Sources",
    ),
    # ── Form structure ────────────────────────────────────────────────
    TableSpec(
        table="form_steps", sheet=("runtime_steps",), key=("model_key", "step_key"),
        columns=(
            ColumnSpec("model_key"), ColumnSpec("step_key"),
            ColumnSpec("step_label"), ColumnSpec("runtime_order", ctype=INT),
            ColumnSpec("source"), _ACTIVE, _NOTES,
        ),
        refs=(RefSpec("model_key", "models", "model_key", optional=False),),
        has_model_key_column=True, editable=True, editor_family="runtime_steps_meta",
        label="Runtime Steps",
    ),
    TableSpec(
        table="form_sections", sheet=("section_master",), key=("section_id",),
        columns=(
            ColumnSpec("section_id"), ColumnSpec("section_name"),
            ColumnSpec("selection_mode"), ColumnSpec("is_required", ctype=BOOL),
            _DISPLAY_ORDER, ColumnSpec("standard_behavior"), ColumnSpec("step_key"),
        ),
        id_prefixes=("sec_",), label="Sections (master)",
        # section_master has no apply_batch family yet: read-only in phase 1.
        editable=False,
    ),
    TableSpec(
        table="section_presentation", sheet=("section_presentation",),
        key=("model_key", "section_id"),
        columns=(
            ColumnSpec("model_key"), ColumnSpec("section_id"),
            ColumnSpec("display_label"), ColumnSpec("step_key"),
            ColumnSpec("display_behavior"),
            ColumnSpec("section_display_order", ctype=INT),
            ColumnSpec("standard_equipment_bucket"),
            ColumnSpec("standard_equipment_group_type"),
            ColumnSpec("auto_added_bucket"), _ACTIVE, _NOTES,
        ),
        refs=(
            RefSpec("model_key", "models", "model_key", optional=False),
            RefSpec("section_id", "form_sections", "section_id", optional=False),
        ),
        has_model_key_column=True, editable=True,
        editor_family="section_presentation_meta",
    ),
    TableSpec(
        table="context_sections", sheet=("context_section_master",),
        key=("model_key", "context_type", "section_id"),
        columns=(
            ColumnSpec("model_key"), ColumnSpec("context_type"),
            ColumnSpec("section_id"), ColumnSpec("section_name"),
            ColumnSpec("selection_mode"), ColumnSpec("choice_mode"),
            ColumnSpec("is_required", ctype=BOOL),
            ColumnSpec("standard_behavior"),
            ColumnSpec("section_display_order", ctype=INT),
            ColumnSpec("step_key"), ColumnSpec("step_label"), _ACTIVE, _NOTES,
        ),
        refs=(RefSpec("model_key", "models", "model_key", optional=False),),
        has_model_key_column=True, editable=True,
        editor_family="context_section_master_meta",
    ),
    TableSpec(
        table="order_summary_sections", sheet=("order_summary_sections",),
        key=("model_key", "section_key"),
        columns=(
            ColumnSpec("model_key"), ColumnSpec("section_key"),
            ColumnSpec("section_label"), _DISPLAY_ORDER, _ACTIVE, _NOTES,
        ),
        refs=(RefSpec("model_key", "models", "model_key", optional=False),),
        has_model_key_column=True, editable=True,
        editor_family="order_summary_sections_meta",
    ),
    TableSpec(
        table="step_order_summary_map", sheet=("step_order_summary_map",),
        key=("model_key", "step_key", "section_key"),
        columns=(
            ColumnSpec("model_key"), ColumnSpec("step_key"),
            ColumnSpec("section_key"), _ACTIVE, _NOTES,
        ),
        refs=(
            RefSpec("model_key", "models", "model_key", optional=False),
            RefSpec("section_key", "order_summary_sections", "section_key",
                    scope="model", optional=False),
        ),
        has_model_key_column=True, editable=True,
        editor_family="step_order_summary_map_meta",
    ),
    TableSpec(
        table="default_selection_rules", sheet=("default_selection_rules",),
        key=("model_key", "rule_id"),
        columns=(
            ColumnSpec("model_key"), ColumnSpec("rule_id"),
            ColumnSpec("target_option_id"),
            ColumnSpec("condition_type", enum=(
                "always", "unless_selected_rpo", "unless_selected_section",
                "when_selected_unless_selected_section")),
            ColumnSpec("condition_id"), ColumnSpec("body_style_scope"),
            ColumnSpec("trim_level_scope"), ColumnSpec("variant_scope"),
            ColumnSpec("priority", ctype=INT), _ACTIVE, _NOTES,
            ColumnSpec("display_behavior", enum=("", "default_selected")),
        ),
        refs=(
            RefSpec("model_key", "models", "model_key", optional=False),
            RefSpec("target_option_id", "options", "option_id", scope="model",
                    optional=False),
        ),
        has_model_key_column=True, editable=True,
        editor_family="default_selection_rules",
    ),
    # ── Model-scoped option data (sheets resolved via sheet_registry) ─
    TableSpec(
        table="options", role="source_option_sheet", key=("option_id",),
        columns=(
            ColumnSpec("option_id"), ColumnSpec("rpo"),
            ColumnSpec("price", ctype=INT), ColumnSpec("option_name"),
            ColumnSpec("description"), ColumnSpec("detail_raw"),
            ColumnSpec("section_id"), ColumnSpec("selectable", ctype=BOOL),
            _DISPLAY_ORDER, _ACTIVE,
            ColumnSpec("display_behavior", enum=DISPLAY_BEHAVIOR_ENUM),
        ),
        refs=(RefSpec("section_id", "form_sections", "section_id"),),
        model_scoped=True, editable=True, editor_family="options",
        id_prefixes=("opt_",),
    ),
    TableSpec(
        table="option_availability", role="status_sheet",
        key=("option_id", "variant_id"),
        columns=(
            ColumnSpec("option_id"), ColumnSpec("variant_id"),
            ColumnSpec("status", enum=OVS_STATUS_ENUM),
        ),
        refs=(
            RefSpec("option_id", "options", "option_id", scope="model",
                    optional=False),
            RefSpec("variant_id", "variants", "variant_id", optional=False),
        ),
        model_scoped=True, editable=True, editor_family="ovs",
        id_prefixes=("opt_",), label="Option Availability (OVS)",
    ),
    TableSpec(
        table="rule_mappings", role="rule_mapping_sheet", key=("rule_id",),
        columns=(
            ColumnSpec("rule_id"), ColumnSpec("source_id"),
            ColumnSpec("rule_type", enum=RULE_TYPE_ENUM),
            ColumnSpec("target_id"), ColumnSpec("original_detail_raw"),
            ColumnSpec("body_style_scope", enum=BODY_SCOPE_ENUM),
            ColumnSpec("runtime_action", enum=("", "replace")),
            ColumnSpec("disabled_reason"),
        ),
        refs=(
            RefSpec("source_id", "options", "option_id", scope="model_union",
                    union_tables=("options", "interiors"), optional=False),
            RefSpec("target_id", "options", "option_id", scope="model_union",
                    union_tables=("options", "interiors"), optional=False),
        ),
        model_scoped=True, editable=True, editor_family="rule_mapping",
        id_prefixes=("rule_",),
    ),
    TableSpec(
        table="rule_groups", role="rule_groups_sheet", key=("group_id",),
        columns=(
            ColumnSpec("group_id"),
            ColumnSpec("group_type", enum=("requires_any", "excludes_any")),
            ColumnSpec("source_id"), ColumnSpec("body_style_scope"),
            ColumnSpec("trim_level_scope"), ColumnSpec("variant_scope"),
            ColumnSpec("disabled_reason"), _ACTIVE, _NOTES,
        ),
        refs=(RefSpec("source_id", "options", "option_id", scope="model",
                      optional=False),),
        model_scoped=True, editable=True, editor_family="rule_groups",
    ),
    TableSpec(
        table="rule_group_members", role="rule_group_members_sheet",
        key=("group_id", "target_id"),
        columns=(
            ColumnSpec("group_id"), ColumnSpec("target_id"),
            _DISPLAY_ORDER, _ACTIVE,
        ),
        refs=(
            RefSpec("group_id", "rule_groups", "group_id", scope="model",
                    optional=False),
            RefSpec("target_id", "options", "option_id", scope="model",
                    optional=False),
        ),
        model_scoped=True, editable=True, editor_family="rule_group_members",
    ),
    TableSpec(
        table="exclusive_groups", role="exclusive_groups_sheet", key=("group_id",),
        columns=(
            ColumnSpec("group_id"),
            ColumnSpec("selection_mode", enum=(
                "single_within_group", "required_single_within_group")),
            _ACTIVE, _NOTES,
        ),
        model_scoped=True, editable=True, editor_family="exclusive_groups",
    ),
    TableSpec(
        table="exclusive_group_members", role="exclusive_group_members_sheet",
        key=("group_id", "option_id"),
        columns=(
            ColumnSpec("group_id"), ColumnSpec("option_id"),
            _DISPLAY_ORDER, _ACTIVE,
        ),
        refs=(
            RefSpec("group_id", "exclusive_groups", "group_id", scope="model",
                    optional=False),
            RefSpec("option_id", "options", "option_id", scope="model",
                    optional=False),
        ),
        model_scoped=True, editable=True, editor_family="exclusive_members",
    ),
    TableSpec(
        table="pricing", role="price_rules_sheet", key=("price_rule_id",),
        columns=(
            ColumnSpec("price_rule_id"), ColumnSpec("condition_option_id"),
            ColumnSpec("price_rule_type", enum=("override",)),
            ColumnSpec("target_option_id"), ColumnSpec("price_value", ctype=INT),
            ColumnSpec("body_style_scope"), ColumnSpec("trim_level_scope"),
            _NOTES,
        ),
        refs=(
            RefSpec("condition_option_id", "options", "option_id",
                    scope="model_union", union_tables=("options", "interiors"),
                    optional=False),
            RefSpec("target_option_id", "options", "option_id",
                    scope="model_union", union_tables=("options", "interiors"),
                    optional=False),
        ),
        model_scoped=True, editable=True, editor_family="price_rules",
        id_prefixes=("pr_",), label="Pricing (price rules)",
    ),
    TableSpec(
        table="variant_option_overrides", role="variant_option_overrides_sheet",
        key=("option_id", "variant_id"),
        columns=(
            ColumnSpec("option_id"), ColumnSpec("variant_id"),
            ColumnSpec("selectable", enum=("", "True", "False")),
            ColumnSpec("display_behavior",
                       enum=("", "default_selected", "display_only", "hidden")),
            ColumnSpec("section_id"), _ACTIVE, ColumnSpec("note"),
        ),
        refs=(
            RefSpec("option_id", "options", "option_id", scope="model",
                    optional=False),
            RefSpec("variant_id", "variants", "variant_id", optional=False),
            RefSpec("section_id", "form_sections", "section_id"),
        ),
        model_scoped=True, editable=True, editor_family="variant_overrides",
    ),
    # ── Shared (multi-model) sheets ───────────────────────────────────
    TableSpec(
        table="interiors", sheet=("lt_interiors", "LZ_Interiors"),
        key=("interior_id",),
        columns=(
            ColumnSpec("interior_id"), ColumnSpec("Interior Name"),
            ColumnSpec("Material"), ColumnSpec("Price", ctype=INT),
            ColumnSpec("Detail from Disclosure"), ColumnSpec("Color Overrides"),
            ColumnSpec("Trim"), ColumnSpec("Seat"), ColumnSpec("Interior Code"),
            ColumnSpec("Suede"), ColumnSpec("Stitch"), ColumnSpec("Two Tone"),
            ColumnSpec("section_id"),
            ColumnSpec("active_for_stingray", ctype=BOOL),
            ColumnSpec("requires_r6x", ctype=BOOL),
            ColumnSpec("included_option_id"),
        ),
        refs=(RefSpec("section_id", "form_sections", "section_id"),),
        editable=True, editor_family="interiors", id_prefixes=("int_",),
    ),
    TableSpec(
        table="color_overrides", sheet=("color_overrides",),
        key=("interior_id", "option_id"),
        columns=(
            ColumnSpec("interior_id"), ColumnSpec("option_id"),
            ColumnSpec("rule_type", enum=("requires",)), ColumnSpec("adds_rpo"),
        ),
        refs=(RefSpec("interior_id", "interiors", "interior_id",
                      optional=False),),
        editable=True, editor_family="color_overrides",
    ),
    TableSpec(
        table="model_interior_scope", sheet=("model_interior_scope",),
        key=("model_key", "interior_id", "trim_level"),
        columns=(
            ColumnSpec("model_key"), ColumnSpec("interior_id"),
            ColumnSpec("trim_level"), _ACTIVE,
            ColumnSpec("requires_option_id"), _NOTES,
            ColumnSpec("interior_seat_label"),
            ColumnSpec("interior_color_family"),
            ColumnSpec("interior_material_family"),
            ColumnSpec("interior_variant_label"),
            ColumnSpec("interior_group_display_order", ctype=INT),
            ColumnSpec("interior_material_display_order", ctype=INT),
            ColumnSpec("interior_choice_display_order", ctype=INT),
            ColumnSpec("interior_hierarchy_levels"),
            ColumnSpec("interior_parent_group_label"),
            ColumnSpec("interior_leaf_label"),
            ColumnSpec("interior_reference_order", ctype=INT),
            ColumnSpec("grouping_source"),
        ),
        refs=(
            RefSpec("model_key", "models", "model_key", optional=False),
            RefSpec("interior_id", "interiors", "interior_id", optional=False),
        ),
        has_model_key_column=True, editable=True,
        editor_family="model_interior_scope",
    ),
    TableSpec(
        table="interior_components", sheet=("interior_components",),
        key=("model_key", "interior_id", "rpo", "component_type"),
        columns=(
            ColumnSpec("model_key"), ColumnSpec("interior_id"),
            ColumnSpec("rpo"), ColumnSpec("component_type"),
            ColumnSpec("label"), ColumnSpec("price_ref_type"),
            ColumnSpec("price_ref_code"), ColumnSpec("price_trim_scope"),
            _DISPLAY_ORDER, _ACTIVE, _NOTES,
        ),
        refs=(
            RefSpec("model_key", "models", "model_key", optional=False),
            RefSpec("interior_id", "interiors", "interior_id", optional=False),
        ),
        has_model_key_column=True, editable=True,
        editor_family="interior_components",
    ),
    TableSpec(
        table="assets", sheet=("asset_map",),
        key=("model_key", "target_type", "target_id"),
        columns=(
            ColumnSpec("model_key"), ColumnSpec("target_type"),
            ColumnSpec("target_id"), ColumnSpec("image_url"),
            ColumnSpec("image_alt"), ColumnSpec("image_fit"),
            ColumnSpec("image_position"), ColumnSpec("hover_image_url"),
            ColumnSpec("hover_image_alt"), ColumnSpec("hover_image_position"),
            _ACTIVE, _NOTES,
        ),
        refs=(RefSpec("model_key", "models", "model_key", optional=False),),
        has_model_key_column=True, editable=True, editor_family="asset_map",
        label="Assets (asset map)",
    ),
)

# Sheets imported verbatim (no normalized table, preserved for export/audit).
RAW_PRESERVED_SHEETS: tuple[str, ...] = (
    "PriceRef",
    "context_choice_copy",
    "rule_phrase_map",
    "runtime_rule_exceptions",
)

SPEC_BY_TABLE: dict[str, TableSpec] = {s.table: s for s in TABLE_SPECS}

# Collections shown in the Model Operations workspace, in display order.
MODEL_COLLECTIONS: tuple[str, ...] = (
    "options", "option_availability", "exclusive_groups",
    "exclusive_group_members", "rule_mappings", "rule_groups",
    "rule_group_members", "pricing", "variant_option_overrides",
    "default_selection_rules", "assets", "model_interior_scope",
    "interior_components",
)

# Tables in the Form Structure workspace.
STRUCTURE_TABLES: tuple[str, ...] = (
    "models", "model_registry_promotion", "variants", "model_variants",
    "form_steps", "form_sections", "section_presentation", "context_sections",
    "order_summary_sections", "step_order_summary_map", "sheet_registry",
)

SHARED_TABLES: tuple[str, ...] = ("interiors", "color_overrides", "form_sections")
