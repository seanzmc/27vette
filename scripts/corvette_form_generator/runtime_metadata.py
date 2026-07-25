"""Safe workbook-owned runtime metadata readers.

Generic loaders for the workbook's metadata sheets. The workbook is the only
authority for anything these sheets can express: a missing required row for an
active model raises rather than falling back to a Python default.
"""

from __future__ import annotations

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
    """Fail rather than substitute a Python default for workbook-owned metadata.

    The workbook is the only authority for anything a workbook column can
    express. A Python fallback here would make the shipped runtime impossible
    to predict from the source of truth, so a missing row is an error for every
    active/generatable model, not only promoted ones.
    """

    raise ValueError(
        f"Model {model_key!r} requires active workbook-owned {sheet_name} rows. "
        "Author them in the workbook; generation does not substitute defaults."
    )


# One measured workbook gap, expressed as two SEPARATE facts. Conflating them is
# unsafe: adding a key to supply a label would otherwise also exempt that key
# from the completeness guard, silently re-opening the defect this guard exists
# to catch.
#
# Fact 1 -- ``standard_equipment`` is a bucket, not a navigable step, so no model
# authors a ``runtime_steps`` row for it and the completeness check must not
# demand one.
BUCKET_STEP_KEYS = frozenset({"standard_equipment"})

# Fact 2 -- it still needs a display string. This is the last Python-authored
# display string in the generator. It only ever lands in ``sections[].step_label``,
# which no consumer reads: ``form-app/app.js`` and every test read
# ``steps[].step_label`` instead. Removing it requires six workbook rows.
UNAUTHORED_BUCKET_STEP_LABELS = {"standard_equipment": "Standard Equipment"}


def _referenced_step_keys(wb: Any, model_key: str) -> set[str]:
    """Every step_key the workbook itself points at for this model.

    Derived from the workbook, never from a Python list, so the completeness
    check cannot become its own authority over what steps must exist.
    """

    # Model-scoped sheets only. ``section_master`` is model-agnostic, so its step
    # keys span every model and cannot speak for the one being generated.
    referenced: set[str] = set()
    for sheet_name in ("section_presentation", "context_section_master", "step_order_summary_map"):
        referenced |= {clean(row.get("step_key")) for row in active_rows(wb, sheet_name, model_key)}
    referenced |= _steps_any_other_active_model_authors(wb, model_key)
    # The recorded bucket-step gap is exempt: it is a bucket, not a navigable
    # step, so it has no runtime_steps row to find. Tracked in one place.
    return {step_key for step_key in referenced if step_key} - BUCKET_STEP_KEYS


def _steps_any_other_active_model_authors(wb: Any, model_key: str) -> set[str]:
    """Steps authored by any other active model, so this one must author them too.

    The model-scoped sheets above cannot see a terminal step such as ``summary``,
    which no section or order-summary row points at. Rather than reintroduce a
    Python list of expected steps, require consistency with the rest of the
    workbook.

    This is a UNION, not an intersection. An intersection is defeated by dropping
    the same step from two models, or by deactivating a single peer row -- both
    ordinary authoring actions. A union survives both: every remaining peer still
    demands the step.

    Known limit, deliberately accepted: dropping a step from EVERY active model
    passes, because nothing is left to compare against. That is a wholesale
    workbook change rather than a drifting edit. A model that legitimately needs a
    different step set will fail loudly here and must author the row -- the right
    failure direction for a lane whose whole point is that the workbook decides.
    """

    model = clean(model_key).lower()
    active_models = {clean(row.get("model_key")).lower() for row in active_rows(wb, "model_master")}
    peer_steps: set[str] = set()
    for row in active_rows(wb, "runtime_steps"):
        other = clean(row.get("model_key")).lower()
        step_key = clean(row.get("step_key"))
        if not step_key or other == model or other not in active_models:
            continue
        peer_steps.add(step_key)
    return peer_steps


def step_label_lookup(runtime_steps: list[dict[str, Any]]) -> dict[str, str]:
    """Step labels come from workbook-owned ``runtime_steps`` rows only."""

    return {row["step_key"]: row["step_label"] for row in runtime_steps}


def workbook_step_label(step_labels: Mapping[str, str], step_key: str) -> str:
    """Return the workbook-authored label for one step.

    Raises unless the workbook authors the step, or it is the single recorded
    bucket-step gap above.
    """

    if step_key in step_labels:
        return step_labels[step_key]
    if step_key in UNAUTHORED_BUCKET_STEP_LABELS:
        return UNAUTHORED_BUCKET_STEP_LABELS[step_key]
    raise ValueError(
        f"Step {step_key!r} has no workbook-owned runtime_steps row to supply its label. "
        "Author the runtime_steps row; generation does not invent step labels."
    )


def load_runtime_steps(wb: Any, model_key: str) -> list[dict[str, Any]]:
    """Load workbook-owned runtime step metadata.

    Every active/generatable model must author its own rows. Completeness is
    checked against the step keys the workbook's own section metadata
    references, so no Python constant decides which steps exist.
    """

    rows = active_rows(wb, "runtime_steps", model_key)
    if not rows:
        _require_workbook_metadata(wb, model_key, "runtime_steps")

    steps: list[dict[str, Any]] = []
    for row in rows:
        step_key = clean(row.get("step_key"))
        if not step_key:
            continue
        step_label = clean(row.get("step_label"))
        if not step_label:
            raise ValueError(
                f"Model {model_key!r} runtime_steps row {step_key!r} has a blank step_label. "
                "Author it; generation does not fall back to the raw step key."
            )
        steps.append(
            {
                "step_key": step_key,
                "step_label": step_label,
                "runtime_order": intish(row.get("runtime_order"), len(steps) + 1),
                "source": clean(row.get("source")) or "workbook",
            }
        )
    actual_step_keys = {row["step_key"] for row in steps}
    missing_step_keys = sorted(_referenced_step_keys(wb, model_key) - actual_step_keys)
    if missing_step_keys:
        raise ValueError(
            f"Model {model_key!r} has incomplete workbook-owned runtime_steps rows; "
            f"its section metadata references missing step_key values: {', '.join(missing_step_keys)}"
        )
    return sorted(steps, key=lambda row: (row["runtime_order"], row["step_key"]))


def load_context_sections(wb: Any, model_key: str) -> list[dict[str, Any]]:
    """Load workbook-owned context section metadata."""

    rows = active_rows(wb, "context_section_master", model_key)
    if not rows:
        _require_workbook_metadata(wb, model_key, "context_section_master")

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
                "auto_added_bucket": clean(row.get("auto_added_bucket")),
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
