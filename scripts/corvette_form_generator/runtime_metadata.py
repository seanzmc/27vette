"""Safe workbook-owned runtime metadata readers.

This module is intentionally substrate-only.  It provides generic loaders for
optional metadata sheets created by the workbook metadata migration without
changing generator or runtime behavior.  Missing or header-only sheets return
empty structures or caller-provided fallbacks.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Iterable, Mapping

from corvette_form_generator.workbook import clean, intish, rows_from_sheet

_TRUE_VALUES = {"1", "true", "t", "yes", "y", "on", "active", "enabled"}
_FALSE_VALUES = {"0", "false", "f", "no", "n", "off", "inactive", "disabled"}
_GLOBAL_MODEL_KEYS = {"all", "shared", "*"}


def truthy(value: Any, default: bool = False) -> bool:
    """Return a permissive workbook boolean value.

    Blank/unknown values return ``default`` so callers can choose whether a
    missing optional flag should behave as enabled or disabled.
    """

    if value is None:
        return default
    if isinstance(value, bool):
        return value
    text = clean(value).lower()
    if not text:
        return default
    if text in _TRUE_VALUES:
        return True
    if text in _FALSE_VALUES:
        return False
    return default


def optional_rows(wb: Any, sheet_name: str) -> list[dict[str, str]]:
    """Read rows from an optional workbook sheet.

    Missing, blank, or header-only sheets return an empty list.  Malformed
    workbooks still surface errors from ``rows_from_sheet`` when the sheet is
    present, matching the existing helper's behavior for real data problems.
    """

    if not sheet_name or sheet_name not in wb.sheetnames:
        return []
    return rows_from_sheet(wb, sheet_name)


def active_rows(wb: Any, sheet_name: str, model_key: str | None = None) -> list[dict[str, str]]:
    """Read active rows from an optional sheet, optionally scoped by model_key."""

    rows = optional_rows(wb, sheet_name)
    if model_key is not None:
        model = clean(model_key).lower()
        allowed_model_keys = _GLOBAL_MODEL_KEYS | {model}
        rows = [
            row
            for row in rows
            if clean(row.get("model_key", "")).lower() in allowed_model_keys
        ]
    return [row for row in rows if truthy(row.get("active", "True"), default=True)]


def _copy_mapping_rows(rows: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    return [dict(deepcopy(row)) for row in rows]


def load_runtime_steps(
    wb: Any,
    model_key: str,
    fallback_order: Iterable[str],
    fallback_labels: Mapping[str, Any],
) -> list[dict[str, Any]]:
    """Load runtime step metadata or synthesize it from fallback order/labels."""

    rows = active_rows(wb, "runtime_steps", model_key)
    if not rows:
        return [
            {
                "step_key": clean(step_key),
                "step_label": clean(fallback_labels.get(step_key, step_key)),
                "runtime_order": index,
                "source": "fallback_config",
                "notes": "",
            }
            for index, step_key in enumerate(fallback_order, start=1)
            if clean(step_key)
        ]

    steps: list[dict[str, Any]] = []
    for row in rows:
        step_key = clean(row.get("step_key"))
        if not step_key:
            continue
        steps.append(
            {
                "step_key": step_key,
                "step_label": clean(row.get("step_label")) or clean(fallback_labels.get(step_key, step_key)),
                "runtime_order": intish(row.get("runtime_order"), len(steps) + 1),
                "source": clean(row.get("source")),
                "notes": clean(row.get("notes")),
            }
        )
    return sorted(steps, key=lambda row: (row["runtime_order"], row["step_key"]))


def load_context_sections(
    wb: Any,
    model_key: str,
    fallback_sections: Iterable[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """Load context section metadata or return caller-provided fallback sections."""

    rows = active_rows(wb, "context_section_master", model_key)
    if not rows:
        return _copy_mapping_rows(fallback_sections)

    sections: list[dict[str, Any]] = []
    for row in rows:
        section_id = clean(row.get("section_id"))
        if not section_id:
            continue
        sections.append(
            {
                "context_type": clean(row.get("context_type")),
                "section_id": section_id,
                "section_name": clean(row.get("section_name")),
                "selection_mode": clean(row.get("selection_mode")),
                "choice_mode": clean(row.get("choice_mode")),
                "is_required": truthy(row.get("is_required"), default=False),
                "standard_behavior": clean(row.get("standard_behavior")),
                "section_display_order": intish(row.get("section_display_order"), len(sections) + 1),
                "step_key": clean(row.get("step_key")),
                "step_label": clean(row.get("step_label")),
                "notes": clean(row.get("notes")),
            }
        )
    return sorted(sections, key=lambda row: (row["section_display_order"], row["section_id"]))


def load_section_presentation(wb: Any, model_key: str) -> list[dict[str, Any]]:
    rows = active_rows(wb, "section_presentation", model_key)
    presentations: list[dict[str, Any]] = []
    for row in rows:
        section_id = clean(row.get("section_id"))
        if not section_id:
            continue
        presentations.append(
            {
                "section_id": section_id,
                "display_label": clean(row.get("display_label")),
                "step_key": clean(row.get("step_key")),
                "presentation_bucket": clean(row.get("presentation_bucket")),
                "display_behavior": clean(row.get("display_behavior")),
                "section_display_order": intish(row.get("section_display_order"), 0),
                "standard_equipment_bucket": clean(row.get("standard_equipment_bucket")),
                "standard_equipment_group_type": clean(row.get("standard_equipment_group_type")),
                "notes": clean(row.get("notes")),
            }
        )
    return sorted(presentations, key=lambda row: (row["section_display_order"], row["section_id"]))


def load_variant_option_overrides(
    wb: Any,
    model_key: str,
    fallback_sheet: str = "",
) -> list[dict[str, Any]]:
    rows = active_rows(wb, "variant_option_overrides", model_key)
    if not rows and fallback_sheet:
        rows = active_rows(wb, fallback_sheet, model_key=None)
    overrides: list[dict[str, Any]] = []
    for row in rows:
        option_id = clean(row.get("option_id") or row.get("rpo"))
        variant_id = clean(row.get("variant_id"))
        if not option_id or not variant_id:
            continue
        overrides.append(
            {
                "option_id": option_id,
                "variant_id": variant_id,
                "status": clean(row.get("status")),
                "selectable": clean(row.get("selectable")),
                "display_behavior": clean(row.get("display_behavior")),
                "notes": clean(row.get("notes")),
            }
        )
    return overrides


def load_default_selection_rules(wb: Any, model_key: str) -> list[dict[str, Any]]:
    return _load_rule_rows(wb, "default_selection_rules", model_key, id_field="rule_id")


def load_runtime_rule_exceptions(wb: Any, model_key: str) -> list[dict[str, Any]]:
    return _load_rule_rows(wb, "runtime_rule_exceptions", model_key, id_field="exception_id")


def _load_rule_rows(wb: Any, sheet_name: str, model_key: str, *, id_field: str) -> list[dict[str, Any]]:
    rules: list[dict[str, Any]] = []
    for row in active_rows(wb, sheet_name, model_key):
        record: dict[str, Any] = {
            key: clean(value) for key, value in row.items() if key not in {"active", "model_key"}
        }
        if id_field in record and not record[id_field]:
            continue
        if "priority" in record:
            record["priority"] = intish(record["priority"], 0)
        rules.append(record)
    return rules


def load_order_summary_metadata(wb: Any, model_key: str) -> dict[str, list[dict[str, Any]]]:
    sections: list[dict[str, Any]] = []
    for row in active_rows(wb, "order_summary_sections", model_key):
        section_key = clean(row.get("section_key"))
        if not section_key:
            continue
        sections.append(
            {
                "section_key": section_key,
                "section_label": clean(row.get("section_label")),
                "display_order": intish(row.get("display_order"), len(sections) + 1),
                "notes": clean(row.get("notes")),
            }
        )

    step_map: list[dict[str, Any]] = []
    for row in active_rows(wb, "step_order_summary_map", model_key):
        step_key = clean(row.get("step_key"))
        section_key = clean(row.get("section_key"))
        if step_key and section_key:
            step_map.append({"step_key": step_key, "section_key": section_key, "notes": clean(row.get("notes"))})

    return {
        "sections": sorted(sections, key=lambda row: (row["display_order"], row["section_key"])),
        "step_map": step_map,
    }


def load_standard_equipment_groups(wb: Any, model_key: str) -> list[dict[str, Any]]:
    groups: list[dict[str, Any]] = []
    for row in active_rows(wb, "standard_equipment_groups", model_key):
        section_id = clean(row.get("section_id"))
        if not section_id:
            continue
        groups.append(
            {
                "section_id": section_id,
                "group_type": clean(row.get("group_type")),
                "default_open": truthy(row.get("default_open"), default=False),
                "canonical_rank": intish(row.get("canonical_rank"), 0),
                "duplicate_group_key": clean(row.get("duplicate_group_key")),
                "notes": clean(row.get("notes")),
            }
        )
    return sorted(groups, key=lambda row: (row["canonical_rank"], row["section_id"]))


def load_component_price_rules(wb: Any, model_key: str) -> list[dict[str, Any]]:
    """Load generic component price rule rows without applying business behavior."""

    rules: list[dict[str, Any]] = []
    for row in active_rows(wb, "component_price_rules", model_key):
        rule_id = clean(row.get("price_rule_id"))
        if not rule_id:
            continue
        rules.append(
            {
                "price_rule_id": rule_id,
                "condition_option_id": clean(row.get("condition_option_id")),
                "target_component_rpo": clean(row.get("target_component_rpo")),
                "price_rule_type": clean(row.get("price_rule_type")),
                "price_value": intish(row.get("price_value"), 0),
                "body_style_scope": clean(row.get("body_style_scope")),
                "trim_level_scope": clean(row.get("trim_level_scope")),
                "variant_scope": clean(row.get("variant_scope")),
                "notes": clean(row.get("notes")),
            }
        )
    return rules


def load_model_interior_scope(wb: Any, model_key: str) -> list[dict[str, Any]]:
    scope: list[dict[str, Any]] = []
    for row in active_rows(wb, "model_interior_scope", model_key):
        interior_id = clean(row.get("interior_id"))
        if not interior_id:
            continue
        scope.append(
            {
                "interior_id": interior_id,
                "trim_level": clean(row.get("trim_level")),
                "requires_option_id": clean(row.get("requires_option_id")),
                "notes": clean(row.get("notes")),
            }
        )
    return scope


def load_model_metadata(wb: Any, model_key: str) -> dict[str, Any]:
    """Load model registry/source/variant metadata from optional model sheets."""

    model_rows = active_rows(wb, "model_master", model_key)
    model: dict[str, Any] = {}
    if model_rows:
        row = model_rows[0]
        model = {
            "model_key": clean(row.get("model_key")),
            "registry_key": clean(row.get("registry_key")),
            "model_label": clean(row.get("model_label")),
            "model_year": clean(row.get("model_year")),
            "dataset_name": clean(row.get("dataset_name")),
            "export_slug": clean(row.get("export_slug")),
            "expected_variant_count": intish(row.get("expected_variant_count"), 0),
            "default_model": truthy(row.get("default_model"), default=False),
            "notes": clean(row.get("notes")),
        }

    sources: list[dict[str, Any]] = []
    for row in active_rows(wb, "model_workbook_sources", model_key):
        source_role = clean(row.get("source_role"))
        sheet_name = clean(row.get("sheet_name"))
        if source_role and sheet_name:
            sources.append({"source_role": source_role, "sheet_name": sheet_name, "notes": clean(row.get("notes"))})

    variants: list[dict[str, Any]] = []
    for row in active_rows(wb, "model_variants", model_key):
        variant_id = clean(row.get("variant_id"))
        if variant_id:
            variants.append(
                {
                    "variant_id": variant_id,
                    "display_order": intish(row.get("display_order"), len(variants) + 1),
                    "notes": clean(row.get("notes")),
                }
            )

    return {
        "model": model,
        "workbook_sources": sources,
        "variants": sorted(variants, key=lambda row: (row["display_order"], row["variant_id"])),
    }
