#!/usr/bin/env python3
"""Deterministic comparator-backed Color/Trim and metadata profiles."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable, Mapping
from typing import Any

from corvette_form_generator.editor_ops import EDITOR_SHEET_META
from corvette_form_generator.ingest.wizard.canonical_rows import semantic_hash
from corvette_form_generator.workbook import workbook_truthy

PRESENTATION_FAMILIES = {
    "runtime_steps": "runtime_steps_meta",
    "section_presentation": "section_presentation_meta",
    "context_section_master": "context_section_master_meta",
    "order_summary_sections": "order_summary_sections_meta",
    "step_order_summary_map": "step_order_summary_map_meta",
}


def _sheet(extract: Mapping[str, Any], name: str) -> Mapping[str, Any] | None:
    return (extract.get("sheets") or {}).get(name)


def _headers(extract: Mapping[str, Any], name: str) -> list[str]:
    sheet = _sheet(extract, name)
    return list(sheet.get("headers") or []) if sheet else []


def _rows(extract: Mapping[str, Any], name: str) -> list[dict[str, Any]]:
    sheet = _sheet(extract, name)
    return [dict(row) for row in (sheet.get("rows") or [])] if sheet else []


def _complete(headers: Iterable[str], source: Mapping[str, Any]) -> dict[str, Any]:
    return {str(header): source.get(str(header), "") for header in headers}


def _number(value: Any) -> int | float | None:
    if value in (None, ""):
        return None
    number = float(value)
    return int(number) if number.is_integer() else number


def _typed_values(family: str, values: Mapping[str, Any]) -> dict[str, Any]:
    result = dict(values)
    for column, kind in EDITOR_SHEET_META[family].get("types", {}).items():
        if column not in result or result[column] in (None, ""):
            continue
        if kind == "bool":
            result[column] = bool(workbook_truthy(result[column]))
        elif kind == "int":
            value = result[column]
            if isinstance(value, bool):
                raise ValueError(f"Profile integer {family}.{column} cannot be Boolean.")
            number = float(value)
            if not number.is_integer():
                raise ValueError(f"Profile integer {family}.{column} is not integral: {value!r}.")
            result[column] = int(number)
    return result


def _dependency(evidence_id: str, value: Any) -> dict[str, str]:
    return {"evidenceId": evidence_id, "semanticFingerprint": semantic_hash(value)}


def _row_record(
    *,
    extract: Mapping[str, Any],
    model: str,
    family: str,
    sheet: str,
    source: Mapping[str, Any],
    key: Mapping[str, Any],
    evidence_id: str,
    headers_override: Iterable[str] = (),
) -> dict[str, Any]:
    headers = list(headers_override) or _headers(extract, sheet)
    if not headers:
        raise ValueError(f"Shared profile requires canonical headers for {sheet}.")
    values = _typed_values(family, _complete(headers, source))
    existing = [
        row
        for row in _rows(extract, sheet)
        if all(row.get(column, "") == value for column, value in key.items())
    ]
    if len(existing) > 1:
        raise ValueError(f"Shared profile found duplicate target key in {sheet}: {dict(key)!r}.")
    action = (
        "add"
        if not existing
        else "noop"
        if all(existing[0].get(header, "") == values.get(header, "") for header in headers)
        else "update"
    )
    signature = {
        "model": model,
        "family": family,
        "sheet": sheet,
        "key": dict(key),
        "values": values,
    }
    return {
        "model": model,
        "family": family,
        "sheet": sheet,
        "action": action,
        "key": dict(key),
        "values": values,
        "semanticSignature": signature,
        "evidenceDependencies": [_dependency(evidence_id, source)],
    }


def _active_model_sources(extract: Mapping[str, Any], model: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for row in _rows(extract, "model_workbook_sources"):
        if str(row.get("model_key") or "").lower() != model:
            continue
        if not workbook_truthy(row.get("active")):
            continue
        role = str(row.get("source_role") or "")
        sheet = str(row.get("sheet_name") or "")
        if role in result:
            raise ValueError(f"Comparator {model} has duplicate active source role {role}.")
        if role and sheet:
            result[role] = sheet
    return result


def _target_trim_family(variants: Iterable[Mapping[str, Any]]) -> tuple[str, set[str]]:
    trims = {str(row.get("trim_level") or "").strip().upper() for row in variants}
    if not trims or "" in trims:
        raise ValueError("Shared interior profile requires complete target trim identities.")
    families = {
        "LT" if trim in {"1LT", "2LT", "3LT"} else "LZ" if trim in {"1LZ", "3LZ"} else ""
        for trim in trims
    }
    if "" in families or len(families) != 1:
        raise ValueError(f"Target trims do not resolve to one LT/LZ interior family: {sorted(trims)}")
    return next(iter(families)), trims


def _base_interior_trim(value: Any) -> str:
    return str(value or "").strip().upper().split("_", 1)[0]


def build_target_profile(
    extract: Mapping[str, Any],
    registry: Mapping[str, Mapping[str, Any]],
    *,
    target: str,
    comparator: str,
    variants: Iterable[Mapping[str, Any]],
) -> dict[str, Any]:
    """Build one target-local shared profile from its selected comparator."""

    target = str(target).strip().lower()
    comparator = str(comparator).strip().lower()
    variant_rows = [dict(row) for row in variants]
    family, target_trims = _target_trim_family(variant_rows)
    comparator_sources = _active_model_sources(extract, comparator)
    comparator_option_sheet = comparator_sources.get("source_option_sheet")
    if not comparator_option_sheet:
        raise ValueError(f"Comparator {comparator} lacks an active option source.")
    comparator_status_sheet = comparator_sources.get("status_sheet")
    if not comparator_status_sheet:
        raise ValueError(f"Comparator {comparator} lacks an active status source.")

    target_option_sheet = str(registry["source_option_sheet"]["sheetName"])
    target_ovs_sheet = str(registry["status_sheet"]["sheetName"])
    paint_section = next(
        (
            row
            for row in _rows(extract, "section_master")
            if str(row.get("section_id") or "") == "sec_pain_001"
        ),
        None,
    )
    if paint_section is None:
        raise ValueError("Shared paint profile requires canonical section sec_pain_001.")
    paint_rows = [
        row
        for row in _rows(extract, comparator_option_sheet)
        if str(row.get("section_id") or "") == "sec_pain_001"
        and workbook_truthy(row.get("active", True))
    ]
    by_rpo: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in paint_rows:
        rpo = str(row.get("rpo") or "").strip().upper()
        if rpo:
            by_rpo[rpo].append(row)
    if not by_rpo or any(len(rows) != 1 for rows in by_rpo.values()):
        raise ValueError(f"Comparator {comparator} paint RPO identities must be non-empty and unique.")

    comparator_variant_ids = {
        str(row.get("variant_id") or "")
        for row in _rows(extract, "model_variants")
        if str(row.get("model_key") or "").strip().lower() == comparator
        and workbook_truthy(row.get("active", True))
        and str(row.get("variant_id") or "")
    }
    if not comparator_variant_ids:
        raise ValueError(
            f"Comparator {comparator} paint availability requires active comparator variants."
        )
    paint_option_ids = {
        str(group[0].get("option_id") or "") for group in by_rpo.values()
    }
    paint_statuses: dict[str, dict[str, str]] = defaultdict(dict)
    for row in _rows(extract, comparator_status_sheet):
        option_id = str(row.get("option_id") or "")
        variant_id = str(row.get("variant_id") or "")
        status = str(row.get("status") or "").strip().lower()
        if option_id not in paint_option_ids or variant_id not in comparator_variant_ids:
            continue
        if variant_id in paint_statuses[option_id]:
            raise ValueError(
                f"Comparator {comparator} paint availability has duplicate status "
                f"for {option_id}/{variant_id}."
            )
        paint_statuses[option_id][variant_id] = status
    for rpo, rows in sorted(by_rpo.items()):
        option_id = str(rows[0].get("option_id") or "")
        statuses = paint_statuses.get(option_id, {})
        if set(statuses) != comparator_variant_ids or set(statuses.values()) != {"available"}:
            raise ValueError(
                f"Comparator {comparator} paint availability for {rpo} must be available "
                f"on every active comparator variant."
            )

    records: list[dict[str, Any]] = []
    option_rpo_ids: dict[str, str] = {}
    target_existing_by_rpo: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in _rows(extract, target_option_sheet):
        rpo = str(row.get("rpo") or "").strip().upper()
        if rpo:
            target_existing_by_rpo[rpo].append(row)
    for rpo in sorted(by_rpo):
        source = dict(by_rpo[rpo][0])
        source_id = str(source.get("option_id") or "")
        if not source_id:
            raise ValueError(f"Comparator paint {rpo} lacks a canonical option_id.")
        existing = target_existing_by_rpo.get(rpo, [])
        if len(existing) > 1:
            raise ValueError(f"Target {target} has duplicate paint RPO {rpo}.")
        if existing and str(existing[0].get("option_id") or "") != source_id:
            raise ValueError(
                f"Target {target} paint {rpo} does not use shared canonical ID {source_id}."
            )
        records.append(
            _row_record(
                extract=extract,
                model=target,
                family="options",
                sheet=target_option_sheet,
                source=source,
                key={"option_id": source_id},
                evidence_id=f"workbook:shared-profile:{comparator}:{comparator_option_sheet}:{source_id}",
                headers_override=registry["source_option_sheet"]["headers"],
            )
        )
        option_rpo_ids[rpo] = source_id
        for variant in variant_rows:
            variant_id = str(variant.get("variant_id") or "")
            ovs_source = {"option_id": source_id, "variant_id": variant_id, "status": "available"}
            records.append(
                _row_record(
                    extract=extract,
                    model=target,
                    family="ovs",
                    sheet=target_ovs_sheet,
                    source=ovs_source,
                    key={"option_id": source_id, "variant_id": variant_id},
                    evidence_id=(
                        f"workbook:shared-profile:{comparator}:{comparator_option_sheet}:"
                        f"{source_id}:target-variant:{variant_id}"
                    ),
                    headers_override=registry["status_sheet"]["headers"],
                )
            )

    interior_entry = registry["interior_source_sheet"]
    expected_sheet = "lt_interiors" if family == "LT" else "LZ_Interiors"
    configured_interior_sheet = str(interior_entry["sheetName"])
    if configured_interior_sheet != expected_sheet and interior_entry.get("registered"):
        raise ValueError(
            f"Target {target} trims require {expected_sheet}, not configured {configured_interior_sheet}."
        )
    interior_sheet = expected_sheet
    source_interiors = [
        row
        for row in _rows(extract, interior_sheet)
        if _base_interior_trim(row.get("Trim")) in target_trims
    ]
    source_interior_ids = {str(row.get("interior_id") or "") for row in source_interiors}
    if not source_interior_ids:
        raise ValueError(f"Target {target} has no {family} interior rows for trims {sorted(target_trims)}.")
    interior_code_ids: dict[str, set[str]] = defaultdict(set)
    comparator_rpo_by_option_id = {
        str(row.get("option_id") or ""): str(row.get("rpo") or "").strip().upper()
        for row in _rows(extract, comparator_option_sheet)
        if str(row.get("option_id") or "") and str(row.get("rpo") or "")
    }
    interior_compatibility_rpos: dict[str, list[str]] = {}
    interior_component_rpos: set[str] = set()
    for row in source_interiors:
        code = str(row.get("Interior Code") or "").strip().upper()
        interior_id = str(row.get("interior_id") or "")
        if code and interior_id:
            interior_code_ids[code].add(interior_id)
        compatibility_rpos = {
            str(row.get(column) or "").strip().upper()
            for column in ("Seat", "Suede", "Stitch", "Two Tone")
            if str(row.get(column) or "").strip()
        }
        interior_component_rpos.update(
            str(row.get(column) or "").strip().upper()
            for column in ("Suede", "Stitch", "Two Tone")
            if str(row.get(column) or "").strip()
        )
        included_option_rpo = comparator_rpo_by_option_id.get(
            str(row.get("included_option_id") or ""),
            "",
        )
        if included_option_rpo:
            compatibility_rpos.add(included_option_rpo)
        if interior_id:
            interior_compatibility_rpos[interior_id] = sorted(compatibility_rpos)

    scope_rows = [
        row
        for row in _rows(extract, "model_interior_scope")
        if str(row.get("model_key") or "").lower() == comparator
        and str(row.get("trim_level") or "").strip().upper() in target_trims
        and str(row.get("interior_id") or "") in source_interior_ids
        and workbook_truthy(row.get("active", True))
    ]
    scope_keys = {
        (str(row.get("interior_id") or ""), str(row.get("trim_level") or "").strip().upper())
        for row in scope_rows
    }
    expected_scope = {
        (str(row.get("interior_id") or ""), _base_interior_trim(row.get("Trim")))
        for row in source_interiors
    }
    if scope_keys != expected_scope:
        missing = sorted(expected_scope - scope_keys)
        extra = sorted(scope_keys - expected_scope)
        raise ValueError(
            f"Comparator {comparator} interior scope does not exactly cover {target}: "
            f"missing={missing[:5]!r} extra={extra[:5]!r}."
        )
    interior_requirements: dict[str, str] = {}
    required_option_trims: dict[str, set[str]] = defaultdict(set)
    for source in sorted(scope_rows, key=lambda row: (str(row.get("interior_id")), str(row.get("trim_level")))):
        target_source = {**source, "model_key": target}
        interior_id = str(source.get("interior_id") or "")
        trim = str(source.get("trim_level") or "").strip().upper()
        requires_option_id = str(source.get("requires_option_id") or "")
        if requires_option_id:
            interior_requirements[interior_id] = requires_option_id
            required_option_trims[requires_option_id].add(trim)
        records.append(
            _row_record(
                extract=extract,
                model=target,
                family="model_interior_scope",
                sheet="model_interior_scope",
                source=target_source,
                key={"model_key": target, "interior_id": interior_id, "trim_level": trim},
                evidence_id=(
                    f"workbook:shared-profile:{comparator}:target:{target}:"
                    f"model_interior_scope:{interior_id}:{trim}"
                ),
            )
        )

    required_option_rpo_ids: dict[str, str] = {}
    required_options: dict[str, dict[str, Any]] = {}
    comparator_options = _rows(extract, comparator_option_sheet)
    live_section_ids = {
        str(row.get("section_id") or "") for row in _rows(extract, "section_master")
    }
    comparator_options_by_rpo: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in comparator_options:
        rpo = str(row.get("rpo") or "").strip().upper()
        if rpo and workbook_truthy(row.get("active", True)):
            comparator_options_by_rpo[rpo].append(row)
    option_precedents: dict[str, dict[str, Any]] = {}
    for rpo, matches in sorted(comparator_options_by_rpo.items()):
        if len(matches) != 1:
            continue
        source = dict(matches[0])
        section_id = str(source.get("section_id") or "")
        if section_id not in live_section_ids:
            continue
        option_id = str(source.get("option_id") or "")
        option_precedents[rpo] = {
            "sectionId": section_id,
            "basePrice": _number(source.get("price")),
            "evidenceId": (
                f"workbook:comparator-placement:{comparator}:{comparator_option_sheet}:"
                f"{option_id or rpo}"
            ),
            "source": source,
            "conditionalPriceRules": [],
        }
    comparator_rpo_by_option_id = {
        str(row.get("option_id") or ""): str(row.get("rpo") or "").strip().upper()
        for row in comparator_options
        if str(row.get("option_id") or "") and str(row.get("rpo") or "")
    }
    comparator_price_sheet = comparator_sources.get("price_rules_sheet")
    if comparator_price_sheet:
        for row in _rows(extract, comparator_price_sheet):
            target_rpo = comparator_rpo_by_option_id.get(
                str(row.get("target_option_id") or ""), ""
            )
            condition_rpo = comparator_rpo_by_option_id.get(
                str(row.get("condition_option_id") or ""), ""
            )
            if not target_rpo or not condition_rpo or target_rpo not in option_precedents:
                continue
            price_value = _number(row.get("price_value"))
            if price_value is None:
                continue
            rule_id = str(row.get("price_rule_id") or "")
            option_precedents[target_rpo]["conditionalPriceRules"].append(
                {
                    "conditionRpo": condition_rpo,
                    "targetRpo": target_rpo,
                    "priceValue": price_value,
                    "priceRuleType": str(row.get("price_rule_type") or "").lower(),
                    "bodyStyleScope": str(row.get("body_style_scope") or "*"),
                    "trimLevelScope": str(row.get("trim_level_scope") or "*"),
                    "variantScope": str(row.get("variant_scope") or "*"),
                    "evidenceId": (
                        f"workbook:comparator-price:{comparator}:{comparator_price_sheet}:"
                        f"{rule_id}"
                    ),
                    "source": dict(row),
                }
            )
    for option_id, required_trims in sorted(required_option_trims.items()):
        matches = [
            row
            for row in comparator_options
            if str(row.get("option_id") or "") == option_id
            and workbook_truthy(row.get("active", True))
        ]
        if len(matches) != 1:
            raise ValueError(
                f"Comparator {comparator} must provide one active required option {option_id}."
            )
        source = dict(matches[0])
        rpo = str(source.get("rpo") or "").strip().upper()
        section_id = str(source.get("section_id") or "")
        if not rpo or section_id not in live_section_ids:
            raise ValueError(
                f"Comparator required option {option_id} lacks a valid RPO/section identity."
            )
        existing = target_existing_by_rpo.get(rpo, [])
        if len(existing) > 1:
            raise ValueError(f"Target {target} has duplicate required-option RPO {rpo}.")
        if existing and str(existing[0].get("option_id") or "") != option_id:
            raise ValueError(
                f"Target {target} required option {rpo} does not use shared canonical ID {option_id}."
            )
        if rpo in option_rpo_ids and option_rpo_ids[rpo] != option_id:
            raise ValueError(f"Profile RPO {rpo} resolves to conflicting option identities.")
        option_rpo_ids[rpo] = option_id
        required_option_rpo_ids[rpo] = option_id
        required_interior_prices = {
            _number(interior.get("Price"))
            for interior in source_interiors
            if interior_requirements.get(str(interior.get("interior_id") or ""))
            == option_id
        }
        required_interior_prices.discard(None)
        option_presentation_price = _number(source.get("price"))
        price_allocation = None
        if len(required_interior_prices) == 1 and option_presentation_price is not None:
            interior_presentation_price = next(iter(required_interior_prices))
            assert interior_presentation_price is not None
            price_allocation = {
                "optionPrice": option_presentation_price,
                "interiorPrice": interior_presentation_price,
                "totalPrice": option_presentation_price + interior_presentation_price,
                "interiorIds": sorted(
                    interior_id
                    for interior_id, required_option_id in interior_requirements.items()
                    if required_option_id == option_id
                ),
            }
        required_options[rpo] = {
            "optionId": option_id,
            "sectionId": section_id,
            "requiredTrims": sorted(required_trims),
            "statusByVariant": {
                str(variant.get("variant_id") or ""): (
                    "available"
                    if str(variant.get("trim_level") or "").strip().upper() in required_trims
                    else "unavailable"
                )
                for variant in variant_rows
            },
            "evidenceId": (
                f"workbook:shared-profile:{comparator}:{comparator_option_sheet}:"
                f"required-option:{option_id}"
            ),
            "source": source,
            "priceAllocation": price_allocation,
        }

    component_rows = [
        row
        for row in _rows(extract, "interior_components")
        if str(row.get("model_key") or "").lower() == comparator
        and str(row.get("interior_id") or "") in source_interior_ids
        and workbook_truthy(row.get("active", True))
    ]
    for source in sorted(
        component_rows,
        key=lambda row: (
            str(row.get("interior_id")),
            str(row.get("rpo")),
            str(row.get("component_type")),
        ),
    ):
        target_source = {**source, "model_key": target}
        key = {
            "model_key": target,
            "interior_id": str(source.get("interior_id") or ""),
            "rpo": str(source.get("rpo") or ""),
            "component_type": str(source.get("component_type") or ""),
        }
        records.append(
            _row_record(
                extract=extract,
                model=target,
                family="interior_components",
                sheet="interior_components",
                source=target_source,
                key=key,
                evidence_id=(
                    f"workbook:shared-profile:{comparator}:interior_components:"
                    f"{semantic_hash(key)}"
                ),
            )
        )

    comparator_color_sheet = comparator_sources.get("color_overrides_sheet")
    if not comparator_color_sheet:
        raise ValueError(f"Comparator {comparator} lacks an active color-overrides source.")
    target_color_sheet = str(registry["color_overrides_sheet"]["sheetName"])
    color_override_rows = [
        row
        for row in _rows(extract, comparator_color_sheet)
        if str(row.get("interior_id") or "") in source_interior_ids
        and workbook_truthy(row.get("active", True))
    ]
    color_key_columns = tuple(EDITOR_SHEET_META["color_overrides"]["key"])
    if target_color_sheet != comparator_color_sheet:
        for source in sorted(
            color_override_rows,
            key=lambda row: tuple(str(row.get(column) or "") for column in color_key_columns),
        ):
            key = {column: source.get(column, "") for column in color_key_columns}
            records.append(
                _row_record(
                    extract=extract,
                    model=target,
                    family="color_overrides",
                    sheet=target_color_sheet,
                    source=source,
                    key=key,
                    evidence_id=(
                        f"workbook:shared-profile:{comparator}:{comparator_color_sheet}:"
                        f"{semantic_hash(key)}"
                    ),
                    headers_override=registry["color_overrides_sheet"]["headers"],
                )
            )

    for sheet, presentation_family in PRESENTATION_FAMILIES.items():
        source_rows = [
            row
            for row in _rows(extract, sheet)
            if str(row.get("model_key") or "").lower() == comparator
            and workbook_truthy(row.get("active", True))
        ]
        if not source_rows:
            raise ValueError(f"Comparator {comparator} has no active {sheet} profile.")
        if sheet == "section_presentation":
            invalid_sections = sorted(
                {
                    str(row.get("section_id") or "")
                    for row in source_rows
                    if str(row.get("section_id") or "") not in live_section_ids
                }
            )
            if invalid_sections:
                raise ValueError(
                    f"Comparator presentation section references are invalid: {invalid_sections}."
                )
        key_columns = tuple(EDITOR_SHEET_META[presentation_family]["key"])
        for source in source_rows:
            target_source = {**source, "model_key": target}
            key = {column: target_source.get(column, "") for column in key_columns}
            records.append(
                _row_record(
                    extract=extract,
                    model=target,
                    family=presentation_family,
                    sheet=sheet,
                    source=target_source,
                    key=key,
                    evidence_id=(
                        f"workbook:shared-profile:{comparator}:target:{target}:"
                        f"{sheet}:{semantic_hash(source)}"
                    ),
                )
            )

    model_headers = _headers(extract, "model_master")
    existing_models = [
        row for row in _rows(extract, "model_master") if str(row.get("model_key") or "").lower() == target
    ]
    if len(existing_models) > 1:
        raise ValueError(f"Target {target} has duplicate model_master rows.")
    model_years = {str(row.get("model_year") or "") for row in variant_rows}
    if len(model_years) != 1:
        raise ValueError(f"Target {target} variants do not establish one model year.")
    label = target.replace("_", " ").title()
    existing_model = existing_models[0] if existing_models else {}
    model_source = {
        **existing_model,
        "model_key": target,
        "registry_key": existing_model.get("registry_key") or target,
        "model_label": existing_model.get("model_label") or label,
        "model_year": next(iter(model_years)),
        "dataset_name": (
            existing_model.get("dataset_name")
            or f"{next(iter(model_years))} Corvette {label} operational form"
        ),
        "export_slug": existing_model.get("export_slug") or target.replace("_", "-"),
        "expected_variant_count": len(variant_rows),
        "default_model": bool(
            workbook_truthy(existing_model.get("default_model"))
        ),
        "active": bool(workbook_truthy(existing_model.get("active"))),
        "notes": (
            existing_model.get("notes")
            or "Inactive metadata compiled from selected target and comparator profile."
        ),
    }
    records.append(
        _row_record(
            extract=extract,
            model=target,
            family="model_master",
            sheet="model_master",
            source=_complete(model_headers, model_source),
            key={"model_key": target},
            evidence_id=f"workbook:shared-profile:{comparator}:target-model:{target}",
        )
    )

    existing_sources = {
        str(row.get("source_role") or ""): row
        for row in _rows(extract, "model_workbook_sources")
        if str(row.get("model_key") or "").lower() == target
    }
    for role, entry in sorted(registry.items()):
        role_sheet = (
            interior_sheet
            if role == "interior_source_sheet"
            else str(entry["sheetName"])
        )
        source = {
            **existing_sources.get(role, {}),
            "model_key": target,
            "source_role": role,
            "sheet_name": role_sheet,
            "active": bool(workbook_truthy(existing_sources.get(role, {}).get("active"))),
            "notes": existing_sources.get(role, {}).get("notes")
            or "Inactive source role compiled from canonical family registration.",
        }
        records.append(
            _row_record(
                extract=extract,
                model=target,
                family="model_workbook_sources",
                sheet="model_workbook_sources",
                source=source,
                key={"model_key": target, "source_role": role},
                evidence_id=f"workbook:shared-profile:{target}:source-role:{role}",
            )
        )

    return {
        "rows": records,
        "optionRpoIds": option_rpo_ids,
        "requiredOptionRpoIds": required_option_rpo_ids,
        "requiredOptions": required_options,
        "optionPrecedents": option_precedents,
        "interiorCodeIds": {
            code: sorted(interior_ids) for code, interior_ids in sorted(interior_code_ids.items())
        },
        "interiorIds": sorted(source_interior_ids),
        "interiorRequirements": interior_requirements,
        "interiorCompatibilityRpos": interior_compatibility_rpos,
        "interiorComponentRpos": sorted(interior_component_rpos),
        "trimFamily": family,
        "targetTrims": sorted(target_trims),
        "interiorSheet": interior_sheet,
    }
