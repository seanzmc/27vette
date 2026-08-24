"""Workbook Manager adapter over the shared workbook-domain registry.

This module owns database-only routing and display facts. Writable columns,
keys, types, enums, references, optionality, and requiredness remain owned by
``workbook_domain.registry``.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Any

from corvette_form_generator.schema_validation import REQUIRED_SHEETS
from corvette_form_generator.workbook import workbook_truthy
from corvette_form_generator.workbook_domain.registry import (
    EDITOR_SHEET_META,
    GLOBAL_SHEET_FAMILIES,
    READONLY_SHEET_META,
    SOURCE_ROLE_FAMILIES,
)


KNOWN_PRESERVED_SHEETS = (
    "PriceRef",
    "context_choice_copy",
    "rule_phrase_map",
    "runtime_rule_exceptions",
)
RAW_PRESERVED_SHEETS = KNOWN_PRESERVED_SHEETS


@dataclass(frozen=True)
class ColumnSpec:
    header: str
    ctype: str = "text"
    enum: tuple = ()
    optional: bool = False

    def sql_name(self) -> str:
        return sanitize_identifier(self.header)


@dataclass(frozen=True)
class RefSpec:
    column: str
    target_table: str
    target_column: str
    scope: str = "global"
    union_tables: tuple = ()
    optional: bool = True


@dataclass(frozen=True)
class TableSpec:
    table: str
    family: str
    sheet: tuple = ()
    role: str = ""
    key: tuple = ()
    columns: tuple = ()
    refs: tuple = ()
    model_scoped: bool = False
    has_model_key_column: bool = False
    editable: bool = True
    editor_family: str = ""
    id_prefixes: tuple = ()
    label: str = ""
    optional_columns: tuple = ()
    required_on_add: tuple = ()
    required_on_effective_active_row: tuple = ()
    shared_contract: tuple = ()
    conditional_ref: tuple = ()
    conditional_refs: tuple = ()

    def sql_columns(self) -> list[str]:
        return [column.sql_name() for column in self.columns]

    def column_by_name(self, name: str) -> ColumnSpec | None:
        return next((column for column in self.columns if column.sql_name() == name), None)

    def column_by_header(self, header: str) -> ColumnSpec | None:
        return next((column for column in self.columns if column.header == header), None)

    def ref_contract(self) -> tuple:
        return self.shared_contract


@dataclass(frozen=True)
class SheetClassification:
    sheet: str
    disposition: str
    family: str = ""
    spec: TableSpec | None = None
    models: tuple[str, ...] = ()


@dataclass(frozen=True)
class ColumnReconciliation:
    known: tuple[str, ...]
    opaque: tuple[str, ...]
    missing_required: tuple[str, ...]
    missing_optional: tuple[str, ...]
    duplicate: tuple[str, ...]


class RequiredValueError(ValueError):
    pass


def sanitize_identifier(header: str) -> str:
    out = "".join(ch.lower() if ch.isalnum() else "_" for ch in header.strip())
    while "__" in out:
        out = out.replace("__", "_")
    return out.strip("_")


def shared_ref_contract(meta: dict) -> tuple:
    return (
        tuple(sorted((column, target) for column, target in meta.get("refs", {}).items())),
        tuple(
            sorted(
                (column, tuple(targets))
                for column, targets in meta.get("ref_unions", {}).items()
            )
        ),
        tuple(sorted((meta.get("conditional_ref") or {}).items())),
        tuple(
            sorted(
                (value, target)
                for value, target in meta.get("conditional_refs", {}).items()
            )
        ),
    )


# family -> (SQL table, fixed sheet, source role, physical model scope,
#             model_key column, label, id prefixes)
_ROUTING: dict[str, tuple] = {
    "model_master": ("models", "model_master", "", False, True, "", ()),
    "model_registry_promotion": ("model_registry_promotion", "model_registry_promotion", "", False, True, "", ()),
    "variant_master": ("variants", "variant_master", "", False, False, "", ()),
    "model_variants": ("model_variants", "model_variants", "", False, True, "", ()),
    "model_workbook_sources": ("sheet_registry", "model_workbook_sources", "", False, True, "Workbook Sources", ()),
    "runtime_steps_meta": ("form_steps", "runtime_steps", "", False, True, "Runtime Steps", ()),
    "section_presentation_meta": ("section_presentation", "section_presentation", "", False, True, "", ()),
    "context_section_master_meta": ("context_sections", "context_section_master", "", False, True, "", ()),
    "order_summary_sections_meta": ("order_summary_sections", "order_summary_sections", "", False, True, "", ()),
    "step_order_summary_map_meta": ("step_order_summary_map", "step_order_summary_map", "", False, True, "", ()),
    "default_selection_rules": ("default_selection_rules", "default_selection_rules", "", False, True, "", ()),
    "options": ("options", "", "source_option_sheet", True, False, "", ("opt_",)),
    "ovs": ("option_availability", "", "status_sheet", True, False, "Option Availability (OVS)", ("opt_",)),
    "rule_mapping": ("rule_mappings", "", "rule_mapping_sheet", True, False, "", ("rule_",)),
    "rule_groups": ("rule_groups", "", "rule_groups_sheet", True, False, "", ()),
    "rule_group_members": ("rule_group_members", "", "rule_group_members_sheet", True, False, "", ()),
    "exclusive_groups": ("exclusive_groups", "", "exclusive_groups_sheet", True, False, "", ()),
    "exclusive_members": ("exclusive_group_members", "", "exclusive_group_members_sheet", True, False, "", ()),
    "price_rules": ("pricing", "", "price_rules_sheet", True, False, "Pricing (price rules)", ("pr_",)),
    "variant_overrides": ("variant_option_overrides", "", "variant_option_overrides_sheet", True, False, "", ()),
    "interiors": ("interiors", "", "interior_source_sheet", False, False, "", ("int_",)),
    "color_overrides": ("color_overrides", "", "color_overrides_sheet", False, False, "", ()),
    "model_interior_scope": ("model_interior_scope", "model_interior_scope", "", False, True, "", ()),
    "interior_components": ("interior_components", "interior_components", "", False, True, "", ()),
    "asset_map": ("assets", "asset_map", "", False, True, "Assets (asset map)", ()),
}

_FAMILY_TO_TABLE = {family: routing[0] for family, routing in _ROUTING.items()}
_FAMILY_TO_TABLE.update({"sections": "form_sections", "variants": "variants"})

# Database presentation facts for bounded reference selectors. Allowed targets,
# values, and scope still come from the shared workbook registry; this adapter
# only states which projected columns form a human label. ``option_rpos`` is the
# one derived conditional-reference domain and is read from the option RPO
# column rather than exposed as an arbitrary table.
REFERENCE_OPTION_PRESENTATION: dict[str, dict] = {
    "options": {
        "value": "option_id", "labels": ("rpo", "option_name"),
        "active": "active",
    },
    "option_rpos": {
        "table": "options", "value": "rpo",
        "labels": ("rpo", "option_name"), "active": "active",
    },
    "interiors": {
        "value": "interior_id", "labels": ("interior_name",),
    },
    "form_sections": {
        "value": "section_id", "labels": ("section_name",),
    },
    "sections": {
        "table": "form_sections", "value": "section_id",
        "labels": ("section_name",),
    },
    "variants": {
        "value": "variant_id", "labels": ("display_name",),
        "active": "active",
    },
    "rule_groups": {
        "value": "group_id", "labels": ("display_label",),
        "active": "active",
    },
    "exclusive_groups": {
        "value": "group_id", "labels": ("display_label",),
        "active": "active",
    },
}


def _reference_specs(family: str, meta: dict) -> tuple[RefSpec, ...]:
    union_map = meta.get("ref_unions", {})
    optional = set(meta.get("optional_columns", ()))
    refs: list[RefSpec] = []
    for column, target in meta.get("refs", {}).items():
        targets = tuple(union_map.get(column, ()))
        scope = "model_union" if targets else (
            "model" if target in {"options", "rule_groups", "exclusive_groups", "order_summary_sections_meta"} else "global"
        )
        target_table = _FAMILY_TO_TABLE.get(target, target)
        target_family = EDITOR_SHEET_META.get(target, {})
        target_column = tuple(target_family.get("key", (column,)))[0]
        refs.append(
            RefSpec(
                column=sanitize_identifier(column),
                target_table=target_table,
                target_column=sanitize_identifier(target_column),
                scope=scope,
                union_tables=tuple(_FAMILY_TO_TABLE.get(name, name) for name in targets),
                optional=column in optional,
            )
        )
    return tuple(refs)


def _build_spec(family: str) -> TableSpec:
    meta = EDITOR_SHEET_META[family]
    table, fixed_sheet, role, model_scoped, has_model_key, label, prefixes = _ROUTING[family]
    optional = tuple(meta["optional_columns"])
    columns = tuple(
        ColumnSpec(
            header=header,
            ctype=meta.get("types", {}).get(header, "text"),
            enum=tuple(meta.get("enums", {}).get(header, ())),
            optional=header in optional,
        )
        for header in meta["columns"]
    )
    return TableSpec(
        table=table,
        family=family,
        sheet=(fixed_sheet,) if fixed_sheet else (),
        role=role,
        key=tuple(sanitize_identifier(key) for key in meta["key"]),
        columns=columns,
        refs=_reference_specs(family, meta),
        model_scoped=model_scoped,
        has_model_key_column=has_model_key,
        editable=True,
        editor_family=family,
        id_prefixes=prefixes,
        label=label,
        optional_columns=optional,
        required_on_add=tuple(meta["required_on_add"]),
        required_on_effective_active_row=tuple(meta["required_on_effective_active_row"]),
        shared_contract=shared_ref_contract(meta),
        conditional_ref=tuple(sorted((meta.get("conditional_ref") or {}).items())),
        conditional_refs=tuple(sorted(meta.get("conditional_refs", {}).items())),
    )


WRITABLE_FAMILIES = tuple(EDITOR_SHEET_META)
WRITABLE_SPECS = tuple(_build_spec(family) for family in WRITABLE_FAMILIES)
SPEC_BY_FAMILY = {spec.family: spec for spec in WRITABLE_SPECS}

def _build_readonly_spec(family: str, table: str) -> TableSpec:
    meta = READONLY_SHEET_META[family]
    return TableSpec(
        table=table,
        family=family,
        sheet=(meta["sheet"],),
        key=tuple(sanitize_identifier(key) for key in meta["key"]),
        columns=tuple(
            ColumnSpec(header, meta.get("types", {}).get(header, "text"))
            for header in meta["columns"]
        ),
        editable=False,
        id_prefixes=meta.get("id_prefixes", ()),
        label=meta.get("label", ""),
    )


_SECTION_SPEC = _build_readonly_spec("sections", "form_sections")

TABLE_SPECS = (*WRITABLE_SPECS, _SECTION_SPEC)
SPEC_BY_TABLE = {spec.table: spec for spec in TABLE_SPECS}

MODEL_COLLECTIONS = (
    "options",
    "option_availability",
    "exclusive_groups",
    "exclusive_group_members",
    "rule_mappings",
    "rule_groups",
    "rule_group_members",
    "pricing",
    "variant_option_overrides",
    "default_selection_rules",
    "assets",
    "model_interior_scope",
    "interior_components",
)
STRUCTURE_TABLES = (
    "models",
    "model_registry_promotion",
    "variants",
    "model_variants",
    "form_steps",
    "form_sections",
    "section_presentation",
    "context_sections",
    "order_summary_sections",
    "step_order_summary_map",
    "sheet_registry",
)
SHARED_TABLES = ("interiors", "color_overrides", "form_sections")


def classify_workbook_sheets(wb) -> dict[str, SheetClassification]:
    result: dict[str, SheetClassification] = {}
    for sheet, family in GLOBAL_SHEET_FAMILIES.items():
        if sheet in wb.sheetnames:
            spec = SPEC_BY_FAMILY[family]
            result[sheet] = SheetClassification(sheet, "managed_writable", family, spec)
    if "section_master" in wb.sheetnames:
        result["section_master"] = SheetClassification(
            "section_master", "managed_read_only", "sections", _SECTION_SPEC
        )
    if "model_workbook_sources" in wb.sheetnames:
        ws = wb["model_workbook_sources"]
        headers = [str(cell.value).strip() if cell.value else "" for cell in ws[1]]
        registrations: dict[str, tuple[str, set[str]]] = {}
        for values in ws.iter_rows(min_row=2, values_only=True):
            row = {header: value for header, value in zip(headers, values) if header}
            if not workbook_truthy(row.get("active")):
                continue
            family = SOURCE_ROLE_FAMILIES.get(str(row.get("source_role") or ""))
            sheet = str(row.get("sheet_name") or "").strip()
            model = str(row.get("model_key") or "").strip()
            if not family or not sheet or sheet not in wb.sheetnames:
                continue
            prior = registrations.get(sheet)
            if prior and prior[0] != family:
                raise ValueError(f"sheet {sheet!r} is actively registered to multiple families")
            models = prior[1] if prior else set()
            models.add(model)
            registrations[sheet] = (family, models)
        for sheet, (family, models) in registrations.items():
            result[sheet] = SheetClassification(
                sheet,
                "managed_writable",
                family,
                SPEC_BY_FAMILY[family],
                tuple(sorted(models)),
            )
    for sheet in wb.sheetnames:
        if sheet in result:
            continue
        if sheet in KNOWN_PRESERVED_SHEETS:
            disposition = "workbook_preserved_known"
        else:
            disposition = "workbook_preserved_unknown"
        result[sheet] = SheetClassification(sheet, disposition)
    return result


def reconcile_columns(spec: TableSpec, headers: list[str]) -> ColumnReconciliation:
    counts = Counter(header for header in headers if header)
    duplicate = tuple(sorted(header for header, count in counts.items() if count > 1))
    owned = {column.header for column in spec.columns}
    known = tuple(header for header in headers if header in owned)
    opaque = tuple(header for header in headers if header and header not in owned)
    present = set(headers)
    optional = set(spec.optional_columns)
    missing_optional = tuple(header for header in optional if header not in present)
    missing_required = tuple(
        header for header in spec.required_on_add if header not in present
    )
    return ColumnReconciliation(
        known=known,
        opaque=opaque,
        missing_required=missing_required,
        missing_optional=missing_optional,
        duplicate=duplicate,
    )


def projection_value(column: ColumnSpec, value: Any):
    if value is None or (isinstance(value, str) and not value.strip()):
        if column.optional:
            return None
        raise RequiredValueError(f"required field {column.header} is blank")
    if isinstance(value, bool):
        return "True" if value else "False"
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)


def required_sheet_names(wb) -> set[str]:
    classifications = classify_workbook_sheets(wb)
    active_managed = {
        sheet
        for sheet, classification in classifications.items()
        if classification.disposition.startswith("managed_")
    }
    return set(REQUIRED_SHEETS) | active_managed
