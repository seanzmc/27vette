"""Safe workbook-owned runtime metadata readers.

This module is intentionally substrate-only.  It provides generic loaders for
optional metadata sheets created by the workbook metadata migration without
changing generator or runtime behavior.  Missing or header-only sheets return
empty structures or caller-provided fallbacks.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Iterable, Mapping

from corvette_form_generator.model_config import ModelConfig
from corvette_form_generator.workbook import clean, intish, rows_from_sheet

_TRUE_VALUES = {"1", "true", "t", "yes", "y", "on", "active", "enabled"}
_FALSE_VALUES = {"0", "false", "f", "no", "n", "off", "inactive", "disabled"}
_GLOBAL_MODEL_KEYS = {"all", "shared", "*"}
_MODEL_CONFIG_SOURCE_ROLES = {
    "source_option_sheet",
    "status_sheet",
    "rule_mapping_sheet",
    "price_rules_sheet",
    "rule_groups_sheet",
    "rule_group_members_sheet",
    "exclusive_groups_sheet",
    "exclusive_group_members_sheet",
    "color_overrides_sheet",
    "variant_option_overrides_sheet",
    "interior_source_sheet",
}


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


def promoted_runtime_model(wb: Any, model_key: str) -> bool:
    """Return whether model_key is promoted to the live runtime registry."""

    model = clean(model_key).lower()
    for row in active_rows(wb, "model_registry_promotion", model):
        if clean(row.get("model_key")).lower() == model and truthy(row.get("promoted_to_runtime"), default=False):
            return True
    return False


def _require_workbook_metadata(wb: Any, model_key: str, sheet_name: str) -> None:
    if promoted_runtime_model(wb, model_key):
        raise ValueError(
            f"Promoted runtime model {model_key!r} requires workbook-owned {sheet_name} rows; "
            "fallback metadata is only allowed for unpromoted compatibility paths."
        )


def _copy_mapping_rows(rows: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    return [dict(deepcopy(row)) for row in rows]


def load_runtime_steps(
    wb: Any,
    model_key: str,
    fallback_order: Iterable[str],
    fallback_labels: Mapping[str, Any],
) -> list[dict[str, Any]]:
    """Load runtime step metadata.

    Promoted runtime models must have workbook-owned rows. Fallback
    order/labels are compatibility defaults for unpromoted models and the
    expected-key set for promoted completeness checks.
    """

    rows = active_rows(wb, "runtime_steps", model_key)
    if not rows:
        _require_workbook_metadata(wb, model_key, "runtime_steps")
        return [
            {
                "step_key": clean(step_key),
                "step_label": clean(fallback_labels.get(step_key, step_key)),
                "runtime_order": index,
                "source": "fallback_config",
            }
            for index, step_key in enumerate(fallback_order, start=1)
            if clean(step_key)
        ]

    steps: list[dict[str, Any]] = []
    expected_step_keys = [clean(step_key) for step_key in fallback_order if clean(step_key)]
    for row in rows:
        step_key = clean(row.get("step_key"))
        if not step_key:
            continue
        steps.append(
            {
                "step_key": step_key,
                "step_label": clean(row.get("step_label")) or clean(fallback_labels.get(step_key, step_key)),
                "runtime_order": intish(row.get("runtime_order"), len(steps) + 1),
                "source": clean(row.get("source")) or "workbook",
            }
        )
    if promoted_runtime_model(wb, model_key):
        actual_step_keys = {row["step_key"] for row in steps}
        missing_step_keys = [step_key for step_key in expected_step_keys if step_key not in actual_step_keys]
        if missing_step_keys:
            raise ValueError(
                f"Promoted runtime model {model_key!r} has incomplete workbook-owned runtime_steps rows; "
                f"missing step_key values: {', '.join(missing_step_keys)}"
            )
    return sorted(steps, key=lambda row: (row["runtime_order"], row["step_key"]))


def load_context_sections(
    wb: Any,
    model_key: str,
    fallback_sections: Iterable[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """Load context section metadata.

    Promoted runtime models must have workbook-owned rows. Caller-provided
    fallback sections are compatibility defaults for unpromoted models only.
    """

    rows = active_rows(wb, "context_section_master", model_key)
    if not rows:
        _require_workbook_metadata(wb, model_key, "context_section_master")
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
                "is_required": clean(row.get("is_required")),
                "standard_behavior": clean(row.get("standard_behavior")),
                "section_display_order": intish(row.get("section_display_order"), len(sections) + 1),
                "step_key": clean(row.get("step_key")),
                "step_label": clean(row.get("step_label")),
            }
        )
    return sorted(sections, key=lambda row: (row["section_display_order"], row["section_id"]))


def load_section_presentation(wb: Any, model_key: str) -> list[dict[str, Any]]:
    rows = active_rows(wb, "section_presentation", model_key)
    presentations: list[dict[str, Any]] = []
    seen: set[str] = set()
    for row in rows:
        section_id = clean(row.get("section_id"))
        if not section_id:
            continue
        if section_id in seen:
            raise ValueError(f"Duplicate active section_presentation row for model {model_key}: section_id={section_id}")
        seen.add(section_id)
        presentations.append(
            {
                "section_id": section_id,
                "display_label": clean(row.get("display_label")),
                "step_key": clean(row.get("step_key")),
                "display_behavior": clean(row.get("display_behavior")),
                "section_display_order": clean(row.get("section_display_order")),
                "standard_equipment_bucket": clean(row.get("standard_equipment_bucket")),
                "standard_equipment_group_type": clean(row.get("standard_equipment_group_type")),
            }
        )
    return sorted(presentations, key=lambda row: (intish(row["section_display_order"], 0), row["section_id"]))


def keyed_section_presentation(wb: Any, model_key: str) -> dict[str, dict[str, Any]]:
    return {row["section_id"]: row for row in load_section_presentation(wb, model_key)}


def presentation_bool(row: Mapping[str, Any], key: str, default: bool = False) -> bool:
    value = clean(row.get(key))
    if not value:
        return default
    return truthy(value, default=default)


def load_variant_option_overrides(
    wb: Any,
    model_key: str,
    fallback_sheet: str = "",
) -> list[dict[str, Any]]:
    """Load model-scoped variant option override rows.

    Active runtime models now resolve variant presentation overrides through
    their configured ``model_workbook_sources.variant_option_overrides_sheet``.
    The historical global ``variant_option_overrides`` contract is retired and
    must not shadow a model-scoped sheet if rows are reintroduced there.
    Model-scoped sheets use ``active`` as row activation, so emitted active
    override values remain neutralized.
    """

    sourced_rows = active_rows(wb, fallback_sheet, model_key=None) if fallback_sheet else []
    overrides: list[dict[str, Any]] = []
    for row in sourced_rows:
        option_id = clean(row.get("option_id") or row.get("rpo"))
        variant_id = clean(row.get("variant_id"))
        if not option_id or not variant_id:
            continue
        overrides.append(
            {
                "option_id": option_id,
                "variant_id": variant_id,
                "status": "",
                "selectable": clean(row.get("selectable")),
                "active": "",
                "display_behavior": clean(row.get("display_behavior")),
                "section_id": clean(row.get("section_id")),
                "note": clean(row.get("note") or row.get("notes")),
                "notes": clean(row.get("notes") or row.get("note")),
            }
        )
    return overrides


def load_default_selection_rules(wb: Any, model_key: str) -> list[dict[str, Any]]:
    return _load_rule_rows(
        wb,
        "default_selection_rules",
        model_key,
        id_field="rule_id",
        exclude_fields={"display_behavior"},
    )


def load_default_selection_display_rules(wb: Any, model_key: str) -> list[dict[str, Any]]:
    return [
        rule
        for rule in _load_rule_rows(wb, "default_selection_rules", model_key, id_field="rule_id")
        if clean(rule.get("display_behavior")) == "default_selected"
    ]


def _scope_matches(scope: Any, value: Any) -> bool:
    entries = [entry.strip() for entry in clean(scope).split("|") if entry.strip()]
    if not entries or "*" in entries:
        return True
    return clean(value) in entries


def _active_single_selection_group_option_ids(exclusive_groups: Iterable[Mapping[str, Any]]) -> set[str]:
    option_ids: set[str] = set()
    for group in exclusive_groups:
        if clean(group.get("active")) != "True":
            continue
        if clean(group.get("selection_mode")) not in {"single_within_group", "required_single_within_group"}:
            continue
        members = [clean(option_id) for option_id in group.get("option_ids", []) if clean(option_id)]
        if len(members) < 2:
            continue
        option_ids.update(members)
    return option_ids


def derived_default_selected_display_behavior(
    choice: Mapping[str, Any],
    model_key: str,
    default_selection_rules: Iterable[Mapping[str, Any]],
    exclusive_groups: Iterable[Mapping[str, Any]],
) -> bool:
    """Return whether a choice should emit default_selected display metadata.

    The source of truth is workbook ``default_selection_rules`` plus active
    single-selection exclusive-group metadata.  Only rules explicitly marked
    with ``display_behavior=default_selected`` may add display metadata.
    """

    if clean(choice.get("status")) != "standard":
        return False
    if clean(choice.get("selectable")) != "True" or clean(choice.get("active")) != "True":
        return False
    option_id = clean(choice.get("option_id"))
    if not option_id or option_id not in _active_single_selection_group_option_ids(exclusive_groups):
        return False
    for rule in default_selection_rules:
        if clean(rule.get("display_behavior")) != "default_selected":
            continue
        if clean(rule.get("target_option_id")) != option_id:
            continue
        if clean(rule.get("condition_type")) not in {"always", "unless_selected_rpo"}:
            continue
        if not _scope_matches(rule.get("body_style_scope"), choice.get("body_style")):
            continue
        if not _scope_matches(rule.get("trim_level_scope"), choice.get("trim_level")):
            continue
        if not _scope_matches(rule.get("variant_scope"), choice.get("variant_id")):
            continue
        return True
    return False


def load_runtime_rule_exceptions(wb: Any, model_key: str) -> list[dict[str, Any]]:
    return _load_rule_rows(wb, "runtime_rule_exceptions", model_key, id_field="exception_id")


def _load_rule_rows(
    wb: Any,
    sheet_name: str,
    model_key: str,
    *,
    id_field: str,
    exclude_fields: set[str] | None = None,
) -> list[dict[str, Any]]:
    rules: list[dict[str, Any]] = []
    omitted = {"active", "model_key", *(exclude_fields or set())}
    for row in active_rows(wb, sheet_name, model_key):
        record: dict[str, Any] = {
            key: clean(value) for key, value in row.items() if key not in omitted
        }
        if id_field in record and not record[id_field]:
            continue
        if "priority" in record:
            record["priority"] = intish(record["priority"], 0)
        rules.append(record)
    return sorted(rules, key=lambda row: (row.get("priority", 0), row.get(id_field, "")))


def load_order_summary_metadata(wb: Any, model_key: str) -> dict[str, Any]:
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

    step_map: dict[str, str] = {}
    for row in active_rows(wb, "step_order_summary_map", model_key):
        step_key = clean(row.get("step_key"))
        section_key = clean(row.get("section_key"))
        if step_key and section_key:
            step_map[step_key] = section_key

    if promoted_runtime_model(wb, model_key) and (not sections or not step_map):
        missing = []
        if not sections:
            missing.append("order_summary_sections")
        if not step_map:
            missing.append("step_order_summary_map")
        raise ValueError(
            f"Promoted runtime model {model_key!r} requires workbook-owned {' and '.join(missing)} rows; "
            "browser order-summary fallback is only allowed for unpromoted compatibility paths."
        )

    return {
        "sections": sorted(sections, key=lambda row: (row["display_order"], row["section_key"])),
        "stepMap": step_map,
    }


def load_interior_components(wb: Any, model_key: str) -> dict[str, list[dict[str, Any]]]:
    """Load workbook-owned interior component rows grouped by interior_id."""

    grouped: dict[str, list[dict[str, Any]]] = {}
    seen: set[tuple[str, str, str]] = set()
    for row in active_rows(wb, "interior_components", model_key):
        interior_id = clean(row.get("interior_id"))
        rpo = clean(row.get("rpo"))
        component_type = clean(row.get("component_type"))
        label = clean(row.get("label"))
        if not interior_id or not rpo or not component_type or not label:
            raise ValueError(
                "Active interior_components row is missing required fields "
                f"for model {model_key}: interior_id={interior_id!r}, rpo={rpo!r}, "
                f"component_type={component_type!r}, label={label!r}"
            )
        key = (interior_id, rpo, component_type)
        if key in seen:
            raise ValueError(
                "Duplicate active interior_components row for "
                f"model {model_key}: interior_id={interior_id}, rpo={rpo}, component_type={component_type}"
            )
        seen.add(key)
        grouped.setdefault(interior_id, []).append(
            {
                "interior_id": interior_id,
                "rpo": rpo,
                "component_type": component_type,
                "label": label,
                "price_ref_type": clean(row.get("price_ref_type")),
                "price_ref_code": clean(row.get("price_ref_code")) or rpo,
                "price_trim_scope": clean(row.get("price_trim_scope")),
                "display_order": intish(row.get("display_order"), len(grouped.get(interior_id, [])) + 1),
                "notes": clean(row.get("notes")),
            }
        )
    for rows in grouped.values():
        rows.sort(key=lambda item: (item["display_order"], item["rpo"], item["component_type"]))
    return grouped


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
                "interior_seat_label": clean(row.get("interior_seat_label")),
                "interior_color_family": clean(row.get("interior_color_family")),
                "interior_material_family": clean(row.get("interior_material_family")),
                "interior_variant_label": clean(row.get("interior_variant_label")),
                "interior_group_display_order": clean(row.get("interior_group_display_order")),
                "interior_material_display_order": clean(row.get("interior_material_display_order")),
                "interior_choice_display_order": clean(row.get("interior_choice_display_order")),
                "interior_hierarchy_levels": clean(row.get("interior_hierarchy_levels")),
                "interior_parent_group_label": clean(row.get("interior_parent_group_label")),
                "interior_leaf_label": clean(row.get("interior_leaf_label")),
                "interior_reference_order": clean(row.get("interior_reference_order")),
                "grouping_source": clean(row.get("grouping_source")),
                "notes": clean(row.get("notes")),
            }
        )
    return scope


def load_model_interior_scope_map(wb: Any, model_key: str) -> dict[str, dict[str, Any]]:
    scope_map: dict[str, dict[str, Any]] = {}
    for row in load_model_interior_scope(wb, model_key):
        interior_id = row["interior_id"]
        if interior_id in scope_map:
            raise ValueError(f"Duplicate active model_interior_scope row for model {model_key}: interior_id={interior_id}")
        scope_map[interior_id] = row
    return scope_map


def _split_phrase_list(value: Any) -> tuple[str, ...]:
    text = clean(value)
    if not text:
        return ()
    parts = text.split("|") if "|" in text else text.split(",")
    return tuple(part for part in (part.strip() for part in parts) if part)


_LEGACY_RULE_PHRASE_FALLBACKS: dict[str, dict[str, Any]] = {
    "not available with": {
        "rule_type": "excludes",
        "direction": "source_to_mentioned",
        "stop_phrases": (),
        "review_flag_default": True,
    },
    "requires": {
        "rule_type": "requires",
        "direction": "source_to_mentioned",
        "stop_phrases": (" or included with", " included with"),
        "review_flag_default": True,
    },
    "includes": {
        "rule_type": "includes",
        "direction": "source_to_mentioned",
        "stop_phrases": (" requires",),
        "review_flag_default": True,
    },
    "included and only available with": {
        "rule_type": "includes",
        "direction": "mentioned_to_source",
        "stop_phrases": (),
        "review_flag_default": True,
    },
    "included with": {
        "rule_type": "includes",
        "direction": "mentioned_to_source",
        "stop_phrases": (),
        "review_flag_default": True,
    },
    "only available with": {
        "rule_type": "requires",
        "direction": "source_to_mentioned",
        "stop_phrases": (),
        "review_flag_default": True,
    },
}


def _normalized_rule_phrase_row(row: Mapping[str, Any], *, fallback: bool = False) -> dict[str, Any]:
    phrase = clean(row.get("phrase"))
    return {
        "phrase": phrase,
        "rule_type": clean(row.get("rule_type")),
        "direction": clean(row.get("direction")),
        "stop_phrases": _split_phrase_list(row.get("stop_phrases")),
        "review_flag_default": truthy(row.get("review_flag_default"), default=False),
        "notes": clean(row.get("notes")) or ("fallback_config" if fallback else ""),
    }


def _fallback_rule_phrase_row(value: Any) -> dict[str, Any] | None:
    if isinstance(value, Mapping):
        row = _normalized_rule_phrase_row(value, fallback=True)
        return row if row["phrase"] else None

    phrase = clean(value)
    if not phrase:
        return None
    legacy = _LEGACY_RULE_PHRASE_FALLBACKS.get(phrase.lower(), {})
    return {
        "phrase": phrase,
        "rule_type": clean(legacy.get("rule_type")),
        "direction": clean(legacy.get("direction")) or "review_only",
        "stop_phrases": tuple(legacy.get("stop_phrases", ())),
        "review_flag_default": bool(legacy.get("review_flag_default", False)),
        "notes": "fallback_config",
    }


def load_rule_phrase_map(wb: Any, fallback_phrases: Iterable[Any] = ()) -> list[dict[str, Any]]:
    """Load workbook-authored rule phrase parser metadata.

    Missing or header-only workbooks fall back to legacy-equivalent parser
    metadata.  If the workbook sheet contains rows, active workbook rows are
    authoritative; disabled rows do not silently re-enable Python fallbacks.
    """

    workbook_rows = optional_rows(wb, "rule_phrase_map")
    rows = [row for row in workbook_rows if truthy(row.get("active", "True"), default=True)]
    if workbook_rows:
        phrase_rows: list[dict[str, Any]] = []
        seen: set[str] = set()
        for row in rows:
            phrase = clean(row.get("phrase"))
            if not phrase:
                continue
            phrase_key = phrase.lower()
            if phrase_key in seen:
                raise ValueError(f"Duplicate active rule_phrase_map row: phrase={phrase}")
            seen.add(phrase_key)
            phrase_rows.append(_normalized_rule_phrase_row(row))
        return phrase_rows

    return [row for row in (_fallback_rule_phrase_row(phrase) for phrase in fallback_phrases) if row]


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


def _registry_model_key(model_key: str) -> str:
    return "grandSport" if model_key == "grand_sport" else model_key


def _duplicate_values(rows: Iterable[Mapping[str, Any]], field: str) -> list[str]:
    seen: set[str] = set()
    duplicates: set[str] = set()
    for row in rows:
        value = clean(row.get(field))
        if not value:
            continue
        if value in seen:
            duplicates.add(value)
        seen.add(value)
    return sorted(duplicates)


def load_model_config_overrides(wb: Any, config: ModelConfig) -> ModelConfig:
    """Return ``config`` with safe workbook-authored model metadata applied.

    Missing or incomplete metadata falls back to the supplied Python constants.
    Invalid active metadata fails fast so workbook drift cannot silently alter
    generator wiring.
    """

    model_rows = active_rows(wb, "model_master", config.model_key)
    if len(model_rows) > 1:
        raise ValueError(f"Duplicate active model_master rows for model {config.model_key}")

    metadata = load_model_metadata(wb, config.model_key)
    model = metadata["model"]
    source_rows = metadata["workbook_sources"]
    variant_rows = metadata["variants"]

    duplicate_roles = _duplicate_values(source_rows, "source_role")
    if duplicate_roles:
        raise ValueError(
            f"Duplicate active model_workbook_sources roles for {config.model_key}: {', '.join(duplicate_roles)}"
        )
    sources = {row["source_role"]: row["sheet_name"] for row in source_rows}
    unknown_roles = sorted(set(sources) - _MODEL_CONFIG_SOURCE_ROLES)
    if unknown_roles:
        raise ValueError(f"Unknown model_workbook_sources roles for {config.model_key}: {', '.join(unknown_roles)}")

    duplicate_variants = _duplicate_values(variant_rows, "variant_id")
    if duplicate_variants:
        raise ValueError(
            f"Duplicate active model_variants rows for {config.model_key}: {', '.join(duplicate_variants)}"
        )

    registry_key = clean(model.get("registry_key"))
    expected_registry_key = _registry_model_key(config.model_key)
    if registry_key and registry_key != expected_registry_key:
        raise ValueError(
            f"Model {config.model_key} registry_key {registry_key!r} does not match current registry key "
            f"{expected_registry_key!r}."
        )

    expected_variant_count = intish(model.get("expected_variant_count"), config.expected_variant_count)
    if not expected_variant_count:
        expected_variant_count = config.expected_variant_count
    resolved_variants = tuple(row["variant_id"] for row in variant_rows) or config.variant_ids
    if expected_variant_count and len(resolved_variants) != expected_variant_count:
        raise ValueError(
            f"Model {config.model_key} expected {expected_variant_count} variants; "
            f"found {len(resolved_variants)} active model_variants rows."
        )

    return config.with_overrides(
        model_label=clean(model.get("model_label")) or config.model_label,
        model_year=clean(model.get("model_year")) or config.model_year,
        dataset_name=clean(model.get("dataset_name")) or config.dataset_name,
        source_option_sheet=sources.get("source_option_sheet") or config.source_option_sheet,
        status_sheet=sources.get("status_sheet") or config.status_sheet,
        variant_ids=resolved_variants,
        expected_variant_count=expected_variant_count,
        rule_mapping_sheet=sources.get("rule_mapping_sheet") or config.rule_mapping_sheet,
        price_rules_sheet=sources.get("price_rules_sheet") or config.price_rules_sheet,
        rule_groups_sheet=sources.get("rule_groups_sheet") or config.rule_groups_sheet,
        rule_group_members_sheet=sources.get("rule_group_members_sheet") or config.rule_group_members_sheet,
        exclusive_groups_sheet=sources.get("exclusive_groups_sheet") or config.exclusive_groups_sheet,
        exclusive_group_members_sheet=sources.get("exclusive_group_members_sheet") or config.exclusive_group_members_sheet,
        color_overrides_sheet=sources.get("color_overrides_sheet") or config.color_overrides_sheet,
        variant_option_overrides_sheet=sources.get("variant_option_overrides_sheet")
        or config.variant_option_overrides_sheet,
        interior_source_sheet=sources.get("interior_source_sheet") or config.interior_source_sheet,
    )
