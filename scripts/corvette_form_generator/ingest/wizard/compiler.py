#!/usr/bin/env python3
"""Read-only canonical-row compiler through ingest Milestone 2.1."""

from __future__ import annotations

from collections import Counter, defaultdict
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

from corvette_form_generator.editor_ops import (
    EDITOR_SHEET_META,
    GLOBAL_SHEET_FAMILIES,
    SOURCE_ROLE_FAMILIES,
    extract_workbook,
    reference_graph_summary,
    rows_of,
)
from corvette_form_generator.ingest.wizard.canonical_rows import (
    COMPILER_POLICY_VERSION,
    build_compile_report,
    build_exception_queue,
    build_manifest,
    canonical_text,
    derivation_version,
    semantic_hash,
    subject_id,
    subject_version,
    validate_artifact_graph,
)
from corvette_form_generator.ingest.wizard.decisions import (
    MODEL_CODE_PREFIXES,
    model_scoped_statuses,
    scope_candidates,
)
from corvette_form_generator.ingest.wizard.exceptions import (
    build_resolution_artifact,
    classify_resolutions,
    exception_subject,
    validate_resolution,
)
from corvette_form_generator.ingest.wizard.identity import (
    allocate_ids,
    deterministic_family_id,
    match_option_occurrences,
    option_occurrence_signature,
    reconcile_rows,
)
from corvette_form_generator.ingest.wizard.relationship_compiler import compile_relationships, load_compiler_phrase_map
from corvette_form_generator.ingest.wizard.profile_compiler import build_target_profile
from corvette_form_generator.model_configs import (
    OPTIONAL_GENERATION_SOURCE_ROLES,
    REQUIRED_GENERATION_SOURCE_ROLES,
    base_model_config,
)
from corvette_form_generator.runtime_metadata import load_rule_phrase_map
from corvette_form_generator.schema_validation import ROLE_BOOLEAN_COLUMNS
from corvette_form_generator.workbook import workbook_truthy


ROLE_ORDER = REQUIRED_GENERATION_SOURCE_ROLES + OPTIONAL_GENERATION_SOURCE_ROLES
VALID_EMPTY_SOURCE_FAMILIES = frozenset({"price_rules", "variant_overrides"})
VALID_EMPTY_GLOBAL_FAMILIES = frozenset(
    {"default_selection_rules", "model_registry_promotion"}
)
SOURCE_FEATURE_DISPOSITIONS = {
    "compiled",
    "retained_existing",
    "exception_open",
    "resolved_not_a_workbook_fact",
    "resolved_not_applicable",
    "allowed_deferral",
    "unsupported_blocker",
}


def _source_disposition(value: Any) -> str:
    aliases = {
        "compiled_ready": "compiled",
        "blocked_exception": "exception_open",
        "proposed_exception": "exception_open",
        "resolved_not_selected_target": "resolved_not_applicable",
        "corroborating_context_only": "resolved_not_applicable",
        "context_only_nonportable_entity": "resolved_not_applicable",
    }
    normalized = aliases.get(str(value), str(value))
    if normalized not in SOURCE_FEATURE_DISPOSITIONS:
        raise ValueError(f"Unsupported source-feature disposition: {value!r}")
    return normalized


def _sheet(extract: Mapping[str, Any], name: str) -> dict[str, Any] | None:
    return (extract.get("sheets") or {}).get(name)


def _headers(extract: Mapping[str, Any], name: str) -> list[str]:
    sheet = _sheet(extract, name)
    return list(sheet.get("headers") or []) if sheet else []


def _rows(extract: Mapping[str, Any], name: str) -> list[dict[str, Any]]:
    sheet = _sheet(extract, name)
    return [dict(row) for row in (sheet.get("rows") or [])] if sheet else []


def _model_source_rows(extract: Mapping[str, Any], model: str) -> list[dict[str, Any]]:
    return [row for row in rows_of(extract, "model_workbook_sources") if str(row.get("model_key") or "").strip().lower() == model]


def build_family_registry(workbook_path: Path, targets: Iterable[str]) -> dict[str, dict[str, dict[str, Any]]]:
    extract = extract_workbook(Path(workbook_path))
    source_rows = rows_of(extract, "model_workbook_sources")
    active_headers: dict[str, set[tuple[str, ...]]] = defaultdict(set)
    for row in source_rows:
        if not workbook_truthy(row.get("active")):
            continue
        role = str(row.get("source_role") or "")
        family = SOURCE_ROLE_FAMILIES.get(role)
        sheet_name = str(row.get("sheet_name") or "")
        if family and sheet_name and _headers(extract, sheet_name):
            active_headers[family].add(tuple(_headers(extract, sheet_name)))
    registry: dict[str, dict[str, dict[str, Any]]] = {}
    for target_value in targets:
        target = str(target_value).strip().lower()
        configured = _model_source_rows(extract, target)
        by_role: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for row in configured:
            by_role[str(row.get("source_role") or "")].append(row)
        entries: dict[str, dict[str, Any]] = {}
        base = base_model_config(target)
        for role in ROLE_ORDER:
            family = SOURCE_ROLE_FAMILIES.get(role)
            if not family or family not in EDITOR_SHEET_META:
                raise ValueError(f"Generation role {role!r} has no canonical editor family metadata.")
            rows = by_role.get(role, [])
            if len(rows) > 1:
                raise ValueError(f"Model {target} has duplicate model_workbook_sources rows for {role}.")
            if rows:
                sheet_name = str(rows[0].get("sheet_name") or "").strip()
                registered_active = workbook_truthy(rows[0].get("active"))
            else:
                sheet_name = str(getattr(base, role))
                registered_active = False
            headers = _headers(extract, sheet_name)
            header_source = "target_sheet"
            if not headers:
                candidates = active_headers.get(family, set())
                if len(candidates) != 1:
                    raise ValueError(
                        f"Cannot derive canonical headers for {target}/{role}: active {family} sheets disagree or are absent."
                    )
                headers = list(next(iter(candidates)))
                header_source = "active_family_consensus"
            entries[role] = {
                "family": family,
                "sheetName": sheet_name,
                "headers": headers,
                "headerSource": header_source,
                "registered": bool(rows),
                "registeredActive": registered_active,
                "required": role in REQUIRED_GENERATION_SOURCE_ROLES,
            }
        registry[target] = entries
    return registry


def _typed_exception(
    model: str,
    family: str,
    reason: str,
    identities: Iterable[Any],
    dependencies: Iterable[Mapping[str, Any]],
    *,
    evidence_references: Iterable[str] = (),
    proposed_rows: Iterable[Mapping[str, Any]] = (),
    allowed_actions: Iterable[str] = (),
    question: str = "Resolve this compiler blocker from target evidence.",
) -> dict[str, Any]:
    deps = list(dependencies)
    sid = subject_id(model, reason, identities)
    return exception_subject(
        subject_id_value=sid,
        subject_version_value=subject_version(sid, deps),
        model=model,
        family=family,
        severity="blocking",
        reason_code=reason,
        allowed_actions=allowed_actions,
        evidence_dependencies=deps,
        evidence_references=evidence_references,
        proposed_rows=proposed_rows,
        gate_impact=["compileReady"],
        question=question,
    )


def _dependency(evidence_id: str, value: Any) -> dict[str, str]:
    normalized_id = str(evidence_id).strip()
    if not normalized_id:
        raise ValueError("Evidence dependencies require a non-empty evidenceId.")
    return {"evidenceId": normalized_id, "semanticFingerprint": semantic_hash(value)}


def _complete_values(headers: Iterable[str], known: Mapping[str, Any]) -> dict[str, Any]:
    return {header: known.get(header, "") for header in headers}


def _int_price(value: Any) -> int | float | None:
    if value in (None, ""):
        return None
    number = float(value)
    return int(number) if number.is_integer() else number


def _header_price(row: Mapping[str, Any]) -> int | float | None:
    """Select price by preserved source header meaning, never column position."""

    evidence = row.get("priceColumnEvidence") or []
    normalized = {
        " ".join(str(item.get("headerText") or "").lower().split()): item.get("value")
        for item in evidence
    }
    for header in ("list price", "list", "msrp(c)", "msrp"):
        if header in normalized:
            return _int_price(normalized[header])
    return None


def _existing_section(existing_options: Iterable[Mapping[str, Any]], rpo: str) -> str:
    sections = {
        str(row.get("section_id") or "")
        for row in existing_options
        if str(row.get("rpo") or "").upper() == rpo and str(row.get("section_id") or "")
    }
    return next(iter(sections)) if len(sections) == 1 else ""


def _section_by_source_label(extract: Mapping[str, Any], label: str) -> str:
    matches = [
        str(row.get("section_id") or "")
        for row in rows_of(extract, "section_master")
        if str(row.get("section_name") or "").strip().lower() == str(label or "").strip().lower()
        and str(row.get("section_id") or "")
    ]
    return matches[0] if len(set(matches)) == 1 else ""


def _precedent_section(extract: Mapping[str, Any], target: str, rpo: str) -> str:
    source_rows = [
        row
        for row in rows_of(extract, "model_workbook_sources")
        if workbook_truthy(row.get("active"))
        and row.get("source_role") == "source_option_sheet"
        and str(row.get("model_key") or "") != target
    ]
    sections: list[str] = []
    for source in source_rows:
        matches = [
            str(row.get("section_id") or "")
            for row in _rows(extract, str(source.get("sheet_name") or ""))
            if str(row.get("rpo") or "").upper() == rpo and workbook_truthy(row.get("active", True))
        ]
        if len(matches) == 1 and matches[0]:
            sections.append(matches[0])
    counts = Counter(sections)
    agreed = [section for section, count in counts.items() if count >= 2]
    return agreed[0] if len(agreed) == 1 else ""


def _target_variant_rows(extract: Mapping[str, Any], target: str) -> list[dict[str, Any]]:
    memberships = [row for row in rows_of(extract, "model_variants") if str(row.get("model_key") or "").lower() == target]
    facts = {str(row.get("variant_id") or ""): row for row in rows_of(extract, "variant_master")}
    result = []
    for membership in memberships:
        variant_id = str(membership.get("variant_id") or "")
        if variant_id in facts:
            result.append({**facts[variant_id], **membership})
    return result


def _resolve_variant(status: Mapping[str, Any], variants: Iterable[Mapping[str, Any]]) -> str:
    trim = str(status.get("trim") or "").lower()
    body = str(status.get("bodyStyle") or "").lower()
    matches = [
        str(row.get("variant_id") or "")
        for row in variants
        if str(row.get("trim_level") or "").lower() == trim
        and str(row.get("body_style") or "").lower() == body
    ]
    return matches[0] if len(matches) == 1 else ""


def _manifest_row(
    *,
    model: str,
    family: str,
    sheet: str,
    action: str,
    key: Mapping[str, Any],
    values: Mapping[str, Any],
    signature: Any,
    dependencies: Iterable[Mapping[str, Any]],
    status: str,
    disposition: str = "compiled",
) -> dict[str, Any]:
    typed_values = dict(values)
    for column, kind in EDITOR_SHEET_META.get(family, {}).get("types", {}).items():
        if column not in typed_values or typed_values[column] in (None, ""):
            continue
        if kind == "bool":
            typed_values[column] = bool(workbook_truthy(typed_values[column]))
        elif kind == "int":
            value = typed_values[column]
            if isinstance(value, bool):
                raise ValueError(f"Canonical integer {family}.{column} cannot be Boolean.")
            number = float(value)
            if not number.is_integer():
                raise ValueError(f"Canonical integer {family}.{column} is not integral: {value!r}.")
            typed_values[column] = int(number)
    deps = list(dependencies)
    return {
        "model": model,
        "family": family,
        "sheet": sheet,
        "action": action,
        "key": dict(key),
        "values": typed_values,
        "semanticSignature": signature,
        "evidenceDependencies": deps,
        "derivationVersion": derivation_version(signature, deps),
        "status": status,
        "disposition": disposition,
    }


def _validate_manifest_contract(
    rows: Iterable[Mapping[str, Any]],
    registry: Mapping[str, Mapping[str, Mapping[str, Any]]],
    extract: Mapping[str, Any],
) -> None:
    expected_headers: dict[str, tuple[str, ...]] = {}
    boolean_columns: dict[str, tuple[str, ...]] = {}
    integer_columns: dict[str, tuple[str, ...]] = {}
    enum_columns: dict[str, dict[str, tuple[Any, ...]]] = {}
    for entries in registry.values():
        for role, entry in entries.items():
            sheet = str(entry["sheetName"])
            expected_headers[sheet] = tuple(str(value) for value in entry["headers"])
            boolean_columns[sheet] = tuple(ROLE_BOOLEAN_COLUMNS.get(role, ()))
            integer_columns[sheet] = tuple(
                column
                for column, kind in EDITOR_SHEET_META[entry["family"]].get("types", {}).items()
                if kind == "int"
            )
            enum_columns[sheet] = {
                str(column): tuple(values)
                for column, values in EDITOR_SHEET_META[entry["family"]].get("enums", {}).items()
            }
    for sheet, columns in {
        "variant_master": ("active",),
        "model_variants": ("active",),
    }.items():
        headers = tuple(_headers(extract, sheet))
        if headers:
            expected_headers[sheet] = headers
            boolean_columns[sheet] = columns
            integer_columns[sheet] = tuple(
                column
                for column, kind in EDITOR_SHEET_META[GLOBAL_SHEET_FAMILIES[sheet]].get("types", {}).items()
                if kind == "int"
            )
    for sheet, family in GLOBAL_SHEET_FAMILIES.items():
        headers = tuple(_headers(extract, sheet))
        if not headers:
            continue
        expected_headers[sheet] = headers
        boolean_columns[sheet] = tuple(
            column
            for column, kind in EDITOR_SHEET_META[family].get("types", {}).items()
            if kind == "bool"
        )
        integer_columns[sheet] = tuple(
            column
            for column, kind in EDITOR_SHEET_META[family].get("types", {}).items()
            if kind == "int"
        )
        enum_columns[sheet] = {
            str(column): tuple(values)
            for column, values in EDITOR_SHEET_META[family].get("enums", {}).items()
        }
    for row in rows:
        sheet = str(row["sheet"])
        headers = expected_headers.get(sheet)
        if headers is None:
            raise ValueError(f"No canonical header contract is registered for {sheet}.")
        values = row["values"]
        if set(values) != set(headers):
            raise ValueError(f"Canonical values do not exactly match headers for {sheet}.")
        if row["status"] == "ready" and any(value in (None, "") for value in row["key"].values()):
            raise ValueError(f"Ready canonical row has an unresolved key for {sheet}.")
        for column in boolean_columns.get(sheet, ()):
            if column in values and not isinstance(values[column], bool):
                raise ValueError(f"Canonical Boolean {sheet}.{column} is not typed.")
        for column in integer_columns.get(sheet, ()):
            if column in values and values[column] not in (None, "") and (
                isinstance(values[column], bool) or not isinstance(values[column], int)
            ):
                raise ValueError(f"Canonical integer {sheet}.{column} is not typed.")
        for column, allowed in enum_columns.get(sheet, {}).items():
            value = values.get(column)
            if value in (None, "") and "" in allowed:
                continue
            if value not in allowed:
                raise ValueError(f"Canonical enum {sheet}.{column} is invalid: {value!r}.")


def _compile_target_variants(
    extract: Mapping[str, Any],
    target: str,
    price_payload: Mapping[str, Any],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], set[str]]:
    variant_headers = _headers(extract, "variant_master")
    membership_headers = _headers(extract, "model_variants")
    existing_variants = _rows(extract, "variant_master")
    existing_memberships = {
        str(row.get("variant_id") or ""): row
        for row in _rows(extract, "model_variants")
        if str(row.get("model_key") or "").lower() == target
    }
    by_display_name: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in existing_variants:
        by_display_name[str(row.get("display_name") or "").strip().lower()].append(row)
    rows: list[dict[str, Any]] = []
    exceptions: list[dict[str, Any]] = []
    desired_variants: list[dict[str, Any]] = []
    compiled_price_rows: set[str] = set()
    for price_row in price_payload.get("baseModelPriceRows") or []:
        model_code = str(price_row.get("modelCode") or "")
        if MODEL_CODE_PREFIXES.get(model_code[:3]) != target:
            continue
        source = price_row.get("sourceEvidence") or {}
        evidence_id = f"base-price:{source.get('sheetName')}:{source.get('rowIndex')}:{model_code}"
        dependencies = [_dependency(evidence_id, price_row)]
        matches = by_display_name.get(str(price_row.get("description") or "").strip().lower(), [])
        if len(matches) != 1:
            exceptions.append(
                _typed_exception(
                    target,
                    "variant_master",
                    "unresolved_base_model_variant_identity",
                    [evidence_id],
                    dependencies,
                    evidence_references=[evidence_id],
                    question="Resolve this base-model price to one established target variant identity.",
                )
            )
            continue
        existing = dict(matches[0])
        variant_id = str(existing.get("variant_id") or "")
        source_price = _header_price(price_row)
        if source_price is None:
            exceptions.append(
                _typed_exception(
                    target,
                    "variant_master",
                    "unresolved_base_price_header",
                    [evidence_id],
                    dependencies,
                    evidence_references=[evidence_id],
                    question="Map this source price header to an approved base-price meaning.",
                )
            )
            continue
        total_price = _int_price(
            float(source_price)
            + float(price_row.get("destinationCharge") or 0)
        )
        values = _complete_values(
            variant_headers,
            {
                **existing,
                "variant_id": variant_id,
                "base_price": total_price,
                "active": bool(workbook_truthy(existing.get("active"))),
            },
        )
        action = "noop" if all(existing.get(header, "") == values.get(header, "") for header in variant_headers) else "update"
        rows.append(
            _manifest_row(
                model=target,
                family="variant_master",
                sheet="variant_master",
                action=action,
                key={"variant_id": variant_id},
                values=values,
                signature={"model": target, "family": "variant_master", "variantId": variant_id, "values": values},
                dependencies=dependencies,
                status="ready",
            )
        )
        desired_variants.append(values)
        membership = existing_memberships.get(variant_id)
        membership_values = _complete_values(
            membership_headers,
            {
                **(membership or {}),
                "model_key": target,
                "variant_id": variant_id,
                "display_order": (membership or {}).get("display_order", existing.get("display_order", "")),
                "active": bool(workbook_truthy((membership or {}).get("active", existing.get("active")))),
                "notes": (membership or {}).get("notes", "Compiled from target Price Schedule."),
            },
        )
        membership_action = (
            "add"
            if membership is None
            else "noop"
            if all(membership.get(header, "") == membership_values.get(header, "") for header in membership_headers)
            else "update"
        )
        rows.append(
            _manifest_row(
                model=target,
                family="model_variants",
                sheet="model_variants",
                action=membership_action,
                key={"model_key": target, "variant_id": variant_id},
                values=membership_values,
                signature={"model": target, "family": "model_variants", "variantId": variant_id, "values": membership_values},
                dependencies=dependencies,
                status="ready",
            )
        )
        compiled_price_rows.add(semantic_hash(price_row))
    return rows, exceptions, desired_variants, compiled_price_rows


def _compile_target_options(
    extract: Mapping[str, Any],
    registry: Mapping[str, Mapping[str, Any]],
    target: str,
    candidates: list[dict[str, Any]],
    variants: list[dict[str, Any]],
    resolution_entries: Iterable[Mapping[str, Any]],
    status_feature_index: Mapping[str, Mapping[str, list[str]]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, str], dict[str, str], set[str], set[str]]:
    entry = registry["source_option_sheet"]
    existing_options = _rows(extract, entry["sheetName"])
    scoped_source = [
        {**candidate, "statuses": model_scoped_statuses(candidate, target)}
        for candidate in scope_candidates(candidates, target)
    ]
    grouped_candidates: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for candidate in scoped_source:
        grouped_candidates[option_occurrence_signature(candidate)].append(candidate)
    scoped: list[dict[str, Any]] = []
    candidate_aliases: dict[str, list[str]] = {}
    for signature in sorted(grouped_candidates):
        group = sorted(
            grouped_candidates[signature],
            key=lambda item: str(item.get("candidateId") or ""),
        )
        representative = dict(group[0])
        source_section_labels = sorted(
            {str(item.get("sectionLabel") or "").strip() for item in group if str(item.get("sectionLabel") or "").strip()}
        )
        source_model_families = sorted(
            {str(value) for item in group for value in item.get("modelFamilies") or [] if str(value)}
        )
        representative["sectionLabel"] = source_section_labels[0] if len(source_section_labels) == 1 else ""
        representative["modelFamilies"] = source_model_families
        representative["_sourceSectionLabels"] = source_section_labels
        evidence_candidate_ids = sorted(
            str(item.get("candidateId") or "") for item in group if item.get("candidateId")
        )
        representative["_sourceCandidateIds"] = evidence_candidate_ids
        candidate_aliases[str(representative.get("candidateId") or "")] = evidence_candidate_ids
        scoped.append(representative)
    matches = match_option_occurrences(scoped, existing_options)
    reserved = {str(row.get("option_id") or "") for row in existing_options if row.get("option_id")}
    new_candidates = [item["candidate"] for item in matches if item["status"] == "new"]
    allocated = allocate_ids("options", target, new_candidates, reserved_ids=reserved)
    new_ids: dict[str, list[str]] = defaultdict(list)
    for item in allocated:
        new_ids[item["semanticSignature"]].append(item["allocatedId"])
    rows: list[dict[str, Any]] = []
    exceptions: list[dict[str, Any]] = []
    consumed_resolution_subjects: set[str] = set()
    compiled_status_features: set[str] = set()
    resolution_entries_by_subject: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for resolution in resolution_entries:
        resolution_entries_by_subject[str(resolution.get("subjectId") or "")].append(resolution)
    candidate_disposition: dict[str, str] = {}
    rpo_ids: dict[str, str] = {}
    ovs_entry = registry["status_sheet"]
    ovs_rows: list[dict[str, Any]] = []
    price_rule_rows: list[dict[str, Any]] = []
    existing_by_id = {str(row.get("option_id") or ""): row for row in existing_options}
    used_existing: set[str] = set()
    for match in matches:
        candidate = dict(match["candidate"])
        candidate_id = str(candidate.get("candidateId") or "")
        stable_candidate_id = option_occurrence_signature(candidate)
        rpo = str(candidate.get("rpo") or candidate.get("refOnlyRpo") or "").upper()
        dependencies = [
            _dependency(
                f"target:{target}:candidate:{stable_candidate_id}",
                {
                    "optionOccurrenceSignature": stable_candidate_id,
                    "sourceSectionLabels": list(candidate.get("_sourceSectionLabels") or []),
                    "modelFamilies": sorted(str(value) for value in candidate.get("modelFamilies") or []),
                },
            )
        ]
        if match["status"] == "ambiguous":
            candidate_ids = sorted(str(value) for value in match.get("candidateIds") or [])
            for existing_id in candidate_ids:
                existing_candidate = existing_by_id[existing_id]
                dependencies.append(
                    _dependency(
                        f"workbook:{entry['sheetName']}:{existing_id}",
                        existing_candidate,
                    )
                )
            subject = _typed_exception(
                target,
                "options",
                "ambiguous_existing_identity",
                [stable_candidate_id, rpo],
                dependencies,
                evidence_references=[stable_candidate_id],
                proposed_rows=[
                    {
                        "existingId": existing_id,
                        "rpo": str(existing_by_id[existing_id].get("rpo") or ""),
                        "optionName": str(existing_by_id[existing_id].get("option_name") or ""),
                        "sectionId": str(existing_by_id[existing_id].get("section_id") or ""),
                    }
                    for existing_id in candidate_ids
                ],
                allowed_actions=["retain_existing"],
                question="Choose the unique established target occurrence.",
            )
            exceptions.append(subject)
            matching_resolutions = resolution_entries_by_subject.get(subject["subjectId"], [])
            retained_resolution = None
            if len(matching_resolutions) == 1:
                try:
                    checked = validate_resolution(matching_resolutions[0], subject)
                except ValueError:
                    checked = None
                if checked and checked.get("action") == "retain_existing":
                    retained_resolution = checked
            if retained_resolution is None:
                candidate_disposition[candidate_id] = "blocked_exception"
                continue
            option_id = str(retained_resolution["payload"]["existingId"])
            if option_id not in candidate_ids:
                raise ValueError(
                    f"Resolved existing option is not a current ambiguous identity candidate: {option_id}"
                )
            if option_id in used_existing:
                raise ValueError(f"Existing option identity was claimed more than once: {option_id}")
            existing = existing_by_id[option_id]
            used_existing.add(option_id)
            dependencies.append(_dependency(f"resolution:{subject['subjectId']}", retained_resolution))
            consumed_resolution_subjects.add(subject["subjectId"])
        elif match["status"] == "matched":
            option_id = str(match["optionId"])
            existing = existing_by_id[option_id]
            used_existing.add(option_id)
            dependencies.append(_dependency(f"workbook:{entry['sheetName']}:{option_id}", existing))
        else:
            signature = option_occurrence_signature(candidate)
            option_id = new_ids[signature].pop(0)
            existing = {}
        section_id = _existing_section(existing_options, rpo)
        if not section_id:
            section_id = _section_by_source_label(extract, str(candidate.get("sectionLabel") or ""))
        if not section_id:
            section_id = _precedent_section(extract, target, rpo)
        if not section_id:
            subject = _typed_exception(
                target,
                "options",
                "missing_section",
                [stable_candidate_id, rpo],
                dependencies,
                evidence_references=[stable_candidate_id],
                allowed_actions=["choose_section"],
                question="Choose one canonical target section.",
            )
            exceptions.append(subject)
            matching_resolutions = resolution_entries_by_subject.get(subject["subjectId"], [])
            consumed_resolution = None
            if len(matching_resolutions) == 1:
                try:
                    checked = validate_resolution(matching_resolutions[0], subject)
                except ValueError:
                    checked = None
                if checked and checked.get("action") == "choose_section" and checked.get("disposition") == "resolved":
                    consumed_resolution = checked
            if consumed_resolution is None:
                candidate_disposition[candidate_id] = "blocked_exception"
                continue
            section_id = str(consumed_resolution["payload"]["sectionId"])
            consumed_resolution_subjects.add(subject["subjectId"])
        section_row = next(
            (
                row
                for row in _rows(extract, "section_master")
                if str(row.get("section_id") or "") == section_id
            ),
            None,
        )
        if section_row is None:
            raise ValueError(f"Resolved section_id is absent from section_master: {section_id}")
        dependencies.append(_dependency(f"workbook:section_master:{section_id}", section_row))
        price_match = candidate.get("priceMatch")
        if price_match == "ambiguous":
            price_subject = _typed_exception(
                target,
                "price_rules",
                "unresolved_price_scope",
                [stable_candidate_id, rpo],
                dependencies,
                evidence_references=[stable_candidate_id],
                allowed_actions=["provide_typed_value"],
                question="Resolve the target-specific conditional price and scope.",
            )
            exceptions.append(price_subject)
            matching_resolutions = resolution_entries_by_subject.get(price_subject["subjectId"], [])
            typed_resolution = None
            if len(matching_resolutions) == 1:
                try:
                    checked = validate_resolution(matching_resolutions[0], price_subject)
                except ValueError:
                    checked = None
                if checked and checked.get("action") == "provide_typed_value" and checked.get("disposition") == "resolved":
                    typed_resolution = checked
            if typed_resolution is None:
                price = _int_price(existing.get("price"))
                row_status = "blocked"
                candidate_disposition[candidate_id] = "blocked_exception"
            else:
                payload = typed_resolution["payload"]
                resolved_price = _int_price(payload.get("priceValue"))
                if resolved_price is None:
                    raise ValueError("Resolved priceValue could not be normalized to an integer.")
                dependencies.append(_dependency(f"resolution:{price_subject['subjectId']}", typed_resolution))
                body_scope = str(payload.get("bodyStyleScope") or "")
                trim_scope = str(payload.get("trimLevelScope") or "")
                variant_scope = str(payload.get("variantScope") or "")
                if body_scope or trim_scope or variant_scope:
                    price_entry = registry["price_rules_sheet"]
                    signature = {
                        "conditionOptionId": option_id,
                        "targetOptionId": option_id,
                        "bodyStyleScope": body_scope or "*",
                        "trimLevelScope": trim_scope or "*",
                        "variantScope": variant_scope or "*",
                        "priceValue": resolved_price,
                    }
                    existing_price_rules = _rows(extract, price_entry["sheetName"])
                    semantic_matches = [
                        row
                        for row in existing_price_rules
                        if str(row.get("condition_option_id") or "") == option_id
                        and str(row.get("target_option_id") or "") == option_id
                        and str(row.get("body_style_scope") or "") == body_scope
                        and str(row.get("trim_level_scope") or "") == trim_scope
                        and str(row.get("variant_scope") or "") == variant_scope
                    ]
                    if len(semantic_matches) > 1:
                        price = _int_price(existing.get("price"))
                        row_status = "blocked"
                        candidate_disposition[candidate_id] = "blocked_exception"
                    else:
                        existing_rule = semantic_matches[0] if semantic_matches else {}
                        price_rule_id = str(existing_rule.get("price_rule_id") or deterministic_family_id("price_rules", target, signature))
                        price_values = _complete_values(
                            price_entry["headers"],
                            {
                                **existing_rule,
                                "price_rule_id": price_rule_id,
                                "condition_option_id": option_id,
                                "price_rule_type": "override",
                                "target_option_id": option_id,
                                "price_value": resolved_price,
                                "body_style_scope": body_scope,
                                "trim_level_scope": trim_scope,
                                "variant_scope": variant_scope,
                                "notes": "Ingest typed price-scope resolution",
                            },
                        )
                        price_rule_rows.append(
                            _manifest_row(
                                model=target,
                                family="price_rules",
                                sheet=price_entry["sheetName"],
                                action="add" if not existing_rule else "noop" if all(existing_rule.get(header, "") == price_values.get(header, "") for header in price_entry["headers"]) else "update",
                                key={"price_rule_id": price_rule_id},
                                values=price_values,
                                signature=signature,
                                dependencies=dependencies,
                                status="ready",
                            )
                        )
                        price = _int_price(existing.get("price"))
                        row_status = "ready"
                        candidate_disposition[candidate_id] = "compiled_ready"
                        consumed_resolution_subjects.add(price_subject["subjectId"])
                else:
                    price = resolved_price
                    row_status = "ready"
                    candidate_disposition[candidate_id] = "compiled_ready"
                    consumed_resolution_subjects.add(price_subject["subjectId"])
        elif price_match == "exact":
            price_rows = candidate.get("priceRows") or []
            price = _header_price(price_rows[0]) if len(price_rows) == 1 else None
            if price is None:
                exceptions.append(
                    _typed_exception(
                        target,
                        "options",
                        "unresolved_price_header",
                        [stable_candidate_id, rpo],
                        dependencies,
                        evidence_references=[stable_candidate_id],
                        question="Map this source price header to an approved option-price meaning.",
                    )
                )
                price = _int_price(existing.get("price"))
                row_status = "blocked"
                candidate_disposition[candidate_id] = "blocked_exception"
            else:
                row_status = "ready"
                candidate_disposition[candidate_id] = "compiled_ready"
        else:
            price = _int_price(existing.get("price"))
            row_status = "ready"
            candidate_disposition[candidate_id] = "compiled_ready"
        statuses = model_scoped_statuses(candidate, target)
        selectable = candidate.get("rowKind") == "orderable" and any(status.get("status") == "available" for status in statuses)
        active = (
            True
            if candidate.get("rowKind") == "standard_no_rpo"
            and any(status.get("status") == "standard" for status in statuses)
            else bool(workbook_truthy(existing.get("active")))
            if existing
            else bool(candidate.get("rowKind") == "orderable" and statuses)
        )
        display_order = existing.get("display_order") if existing else ""
        known = {
            "option_id": option_id,
            "rpo": rpo,
            "price": price if price is not None else "",
            "option_name": str(candidate.get("description") or "").split(",", 1)[0].strip(),
            "description": str(candidate.get("description") or ""),
            "detail_raw": str(candidate.get("description") or ""),
            "section_id": section_id,
            "selectable": bool(selectable),
            "display_order": display_order,
            "active": bool(active),
            "display_behavior": existing.get("display_behavior", ""),
        }
        values = _complete_values(entry["headers"], known)
        signature_payload = {"family": "options", "model": target, "occurrence": option_occurrence_signature({**candidate, "section_id": section_id})}
        action = "add" if not existing else "noop" if all(existing.get(key, "") == value for key, value in values.items()) else "update"
        rows.append(
            _manifest_row(model=target, family="options", sheet=entry["sheetName"], action=action, key={"option_id": option_id}, values=values, signature=signature_payload, dependencies=dependencies, status=row_status)
        )
        if rpo not in rpo_ids:
            rpo_ids[rpo] = option_id
        elif rpo_ids[rpo] != option_id:
            rpo_ids[rpo] = ""
        for status in statuses:
            if status.get("status") == "unresolved":
                exceptions.append(
                    _typed_exception(
                        target,
                        "ovs",
                        "unresolved_option_status",
                        [stable_candidate_id, rpo, status.get("modelCode"), status.get("trim"), status.get("bodyStyle")],
                        dependencies,
                        evidence_references=[stable_candidate_id],
                        question="Add deterministic source-status support before emitting this OVS row.",
                    )
                )
                continue
            variant_id = _resolve_variant(status, variants)
            if not variant_id:
                exceptions.append(
                    _typed_exception(target, "ovs", "unresolved_variant_identity", [stable_candidate_id, rpo, status.get("modelCode"), status.get("trim"), status.get("bodyStyle")], dependencies, evidence_references=[stable_candidate_id], question="Resolve this source variant to one target variant_id.")
                )
                continue
            variant_evidence = next(
                row for row in variants if str(row.get("variant_id") or "") == variant_id
            )
            status_signature = _status_semantic_signature(status)
            status_feature_ids = sorted(
                {
                    feature_id
                    for source_candidate_id in candidate.get("_sourceCandidateIds") or [candidate_id]
                    for feature_id in status_feature_index.get(source_candidate_id, {}).get(
                        status_signature, []
                    )
                }
            )
            ovs_dependencies = [
                *dependencies,
                _dependency(f"target:{target}:variant:{variant_id}", variant_evidence),
                *(_dependency(feature_id, status) for feature_id in status_feature_ids),
            ]
            ovs_values = _complete_values(
                ovs_entry["headers"],
                {"option_id": option_id, "variant_id": variant_id, "status": status.get("status") or "unresolved"},
            )
            ovs_signature = {"family": "ovs", "model": target, "optionId": option_id, "variantId": variant_id, "status": status.get("status")}
            ovs_rows.append(
                _manifest_row(model=target, family="ovs", sheet=ovs_entry["sheetName"], action="add", key={"option_id": option_id, "variant_id": variant_id}, values=ovs_values, signature=ovs_signature, dependencies=ovs_dependencies, status="ready")
            )
            compiled_status_features.update(status_feature_ids)
    ovs_by_key: dict[tuple[str, str], dict[str, Any]] = {}
    for ovs_row in ovs_rows:
        ovs_key = (
            str(ovs_row["key"]["option_id"]),
            str(ovs_row["key"]["variant_id"]),
        )
        if ovs_key not in ovs_by_key:
            ovs_by_key[ovs_key] = ovs_row
            continue
        existing_ovs_row = ovs_by_key[ovs_key]
        if existing_ovs_row["values"] != ovs_row["values"]:
            raise ValueError(f"Conflicting OVS rows for {ovs_key}.")
        dependencies_by_id = {
            dependency["evidenceId"]: dependency
            for dependency in (
                list(existing_ovs_row["evidenceDependencies"])
                + list(ovs_row["evidenceDependencies"])
            )
        }
        dependencies = [dependencies_by_id[key] for key in sorted(dependencies_by_id)]
        existing_ovs_row["evidenceDependencies"] = dependencies
        existing_ovs_row["derivationVersion"] = derivation_version(
            existing_ovs_row["semanticSignature"], dependencies
        )
    ovs_rows = list(ovs_by_key.values())
    existing_ovs = _rows(extract, ovs_entry["sheetName"])
    reconciled_ovs = reconcile_rows("ovs", [row["values"] for row in ovs_rows], existing_ovs, key_columns=EDITOR_SHEET_META["ovs"]["key"])
    action_by_key = {tuple(item["key"].values()): item["action"] for item in reconciled_ovs}
    for row in ovs_rows:
        row["action"] = action_by_key.get(tuple(row["key"].values()), row["action"])
    for item in reconciled_ovs:
        if item["action"] != "retained_existing":
            continue
        values = _complete_values(ovs_entry["headers"], item["values"])
        signature = {
            "family": "ovs",
            "model": target,
            "retainedKey": item["key"],
        }
        dependencies = [
            _dependency(
                f"workbook:{ovs_entry['sheetName']}:{canonical_text(item['key'])}",
                item["values"],
            )
        ]
        ovs_rows.append(
            _manifest_row(
                model=target,
                family="ovs",
                sheet=ovs_entry["sheetName"],
                action="noop",
                key=item["key"],
                values=values,
                signature=signature,
                dependencies=dependencies,
                status="ready",
                disposition="retained_existing",
            )
        )
    rows.extend(ovs_rows)
    for option_id, existing in sorted(existing_by_id.items()):
        if option_id in used_existing:
            continue
        dependencies = [_dependency(f"workbook:{entry['sheetName']}:{option_id}", existing)]
        signature = {"family": "options", "model": target, "retainedId": option_id}
        retained_values = _complete_values(
            entry["headers"],
            {
                **existing,
                "active": bool(workbook_truthy(existing.get("active"))),
                "selectable": bool(workbook_truthy(existing.get("selectable"))),
            },
        )
        rows.append(
            _manifest_row(
                model=target,
                family="options",
                sheet=entry["sheetName"],
                action="noop",
                key={"option_id": option_id},
                values=retained_values,
                signature=signature,
                dependencies=dependencies,
                status="ready",
                disposition="retained_existing",
            )
        )
        rpo = str(existing.get("rpo") or "").upper()
        if rpo and rpo not in rpo_ids:
            rpo_ids[rpo] = option_id
        elif rpo and rpo_ids[rpo] != option_id:
            rpo_ids[rpo] = ""
    for representative_id, aliases in candidate_aliases.items():
        disposition = candidate_disposition.get(representative_id)
        if disposition:
            for alias in aliases:
                candidate_disposition[alias] = disposition
    rows.extend(price_rule_rows)
    return (
        rows,
        exceptions,
        candidate_disposition,
        rpo_ids,
        consumed_resolution_subjects,
        compiled_status_features,
    )


def _relationship_rows(
    extract: Mapping[str, Any],
    target: str,
    registry: Mapping[str, Mapping[str, Any]],
    rpo_ids: Mapping[str, str],
    option_ids: set[str],
    endpoint_ids: set[str],
    relationship_result: Mapping[str, Any],
    resolution_entries: Iterable[Mapping[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], set[str], dict[str, str]]:
    entry = registry["rule_mapping_sheet"]
    rows: list[dict[str, Any]] = []
    exceptions: list[dict[str, Any]] = []
    consumed: set[str] = set()
    disposition_overrides: dict[str, str] = {}
    existing_rules = _rows(extract, entry["sheetName"])
    resolutions_by_subject: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for resolution in resolution_entries:
        resolutions_by_subject[str(resolution.get("subjectId") or "")].append(resolution)
    rpo_by_id = {
        option_id: rpo
        for rpo, option_id in rpo_ids.items()
        if option_id
    }
    known_feature_ids = {
        str(item.get("featureId") or "")
        for item in relationship_result.get("dispositions") or []
        if str(item.get("featureId") or "")
    }

    def current_resolution(subject: Mapping[str, Any]) -> dict[str, Any] | None:
        matches = resolutions_by_subject.get(str(subject.get("subjectId") or ""), [])
        if len(matches) != 1:
            return None
        try:
            return validate_resolution(matches[0], subject)
        except ValueError:
            return None

    def update_disposition(subject: Mapping[str, Any], disposition: str) -> None:
        for reference in subject.get("evidenceReferences") or []:
            reference = str(reference)
            if reference in known_feature_ids:
                disposition_overrides[reference] = disposition

    def emit_rule(
        *,
        source_id: str,
        target_id: str,
        semantic_rule_type: str,
        dependencies: Iterable[Mapping[str, Any]],
        evidence_references: Iterable[str],
    ) -> bool:
        stored_rule_type = "excludes" if semantic_rule_type == "replaces" else semantic_rule_type
        runtime_action = "replace" if semantic_rule_type == "replaces" else ""
        signature = {
            "sourceRpo": rpo_by_id.get(source_id, source_id),
            "ruleType": semantic_rule_type,
            "targetRpo": rpo_by_id.get(target_id, target_id),
            "bodyStyleScope": "*",
            "trimLevelScope": "*",
            "variantScope": "*",
        }
        semantic_matches = [
            row
            for row in existing_rules
            if str(row.get("source_id") or "") == source_id
            and str(row.get("target_id") or "") == target_id
            and str(row.get("rule_type") or "") == stored_rule_type
            and str(row.get("body_style_scope") or "") == ""
            and str(row.get("runtime_action") or "") == runtime_action
        ]
        if len(semantic_matches) > 1:
            exceptions.append(
                _typed_exception(
                    target,
                    "rule_mapping",
                    "ambiguous_existing_relationship_identity",
                    [source_id, semantic_rule_type, target_id],
                    dependencies,
                    evidence_references=evidence_references,
                    question="Choose the unique established relationship occurrence.",
                )
            )
            return False
        existing = semantic_matches[0] if semantic_matches else {}
        rule_id = str(
            existing.get("rule_id")
            or deterministic_family_id("rule_mapping", target, signature)
        )
        values = _complete_values(
            entry["headers"],
            {
                **existing,
                "rule_id": rule_id,
                "source_id": source_id,
                "rule_type": stored_rule_type,
                "target_id": target_id,
                "original_detail_raw": "",
                "body_style_scope": "",
                "runtime_action": runtime_action,
                "disabled_reason": "",
                "active": True,
            },
        )
        rows.append(
            _manifest_row(
                model=target,
                family="rule_mapping",
                sheet=entry["sheetName"],
                action=(
                    "add"
                    if not existing
                    else "noop"
                    if all(
                        existing.get(header, "") == values.get(header, "")
                        for header in entry["headers"]
                    )
                    else "update"
                ),
                key={"rule_id": rule_id},
                values=values,
                signature=signature,
                dependencies=dependencies,
                status="ready",
            )
        )
        return True

    for source in relationship_result.get("rows") or []:
        source_id = str(source.get("sourceId") or "") or rpo_ids.get(
            str(source.get("sourceRpo") or "")
        )
        target_id = str(source.get("targetId") or "") or rpo_ids.get(
            str(source.get("targetRpo") or "")
        )
        dependencies = list(source["evidenceDependencies"])
        subject = None
        resolution = None
        if (
            not source_id
            or not target_id
            or source_id not in endpoint_ids
            or target_id not in endpoint_ids
        ):
            # This relationship depends on an upstream option identity/section
            # blocker. Recompute it after that owning subject is resolved instead
            # of creating a duplicate reviewer task.
            disposition_overrides[str(source.get("sourceFeatureId") or "")] = "blocked_exception"
            continue
        else:
            rule_type = str(source["ruleType"])
        if source_id not in endpoint_ids or target_id not in endpoint_ids:
            raise ValueError("Resolved relationship endpoints are not current emitted target identities.")
        emitted = emit_rule(
            source_id=str(source_id),
            target_id=str(target_id),
            semantic_rule_type=rule_type,
            dependencies=dependencies,
            evidence_references=[str(source.get("sourceFeatureId") or "")],
        )
        if emitted and subject and resolution:
            consumed.add(str(subject["subjectId"]))
            update_disposition(subject, "compiled_ready")

    for subject in relationship_result.get("exceptions") or []:
        resolution = current_resolution(subject)
        if resolution is None:
            continue
        if resolution.get("action") == "mark_not_applicable":
            update_disposition(subject, "resolved_not_applicable")
            consumed.add(str(subject["subjectId"]))
            continue
        if resolution.get("action") != "choose_relationship":
            continue
        payload = resolution["payload"]
        source_id = str(payload["sourceOptionId"])
        target_id = str(payload["targetOptionId"])
        if source_id not in option_ids or target_id not in option_ids:
            raise ValueError("Resolved relationship endpoints are not current emitted target options.")
        dependencies = [
            *(subject.get("evidenceDependencies") or []),
            _dependency(f"resolution:{subject['subjectId']}", resolution),
        ]
        emitted = emit_rule(
            source_id=source_id,
            target_id=target_id,
            semantic_rule_type=str(payload["ruleType"]),
            dependencies=dependencies,
            evidence_references=subject.get("evidenceReferences") or [],
        )
        if emitted:
            consumed.add(str(subject["subjectId"]))
            update_disposition(subject, "compiled_ready")
    aggregated: dict[str, dict[str, Any]] = {}
    for row in rows:
        rule_id = str(row["key"]["rule_id"])
        if rule_id not in aggregated:
            aggregated[rule_id] = row
            continue
        existing_row = aggregated[rule_id]
        if existing_row["values"] != row["values"]:
            raise ValueError(f"Conflicting canonical relationship rows for {rule_id}.")
        dependencies_by_id = {
            dependency["evidenceId"]: dependency
            for dependency in (
                list(existing_row["evidenceDependencies"])
                + list(row["evidenceDependencies"])
            )
        }
        dependencies = [dependencies_by_id[key] for key in sorted(dependencies_by_id)]
        existing_row["evidenceDependencies"] = dependencies
        existing_row["derivationVersion"] = derivation_version(
            existing_row["semanticSignature"], dependencies
        )
    return list(aggregated.values()), exceptions, consumed, disposition_overrides


def _comparator_proposal_rows(
    extract: Mapping[str, Any],
    target: str,
    registry: Mapping[str, Mapping[str, Any]],
    rpo_ids: Mapping[str, str],
    relationship_result: Mapping[str, Any],
    resolution_entries: Iterable[Mapping[str, Any]],
) -> tuple[list[dict[str, Any]], set[str], dict[str, str], set[str]]:
    rows: list[dict[str, Any]] = []
    consumed: set[str] = set()
    disposition_overrides: dict[str, str] = {}
    compiled_fact_keys: set[str] = set()
    resolutions_by_subject: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for resolution in resolution_entries:
        resolutions_by_subject[str(resolution.get("subjectId") or "")].append(resolution)

    def manifest_action(
        existing: Mapping[str, Any],
        values: Mapping[str, Any],
        headers: Iterable[str],
    ) -> str:
        if not existing:
            return "add"
        return (
            "noop"
            if all(existing.get(header, "") == values.get(header, "") for header in headers)
            else "update"
        )

    def add_row(
        *,
        family: str,
        entry: Mapping[str, Any],
        existing: Mapping[str, Any],
        key: Mapping[str, Any],
        values: Mapping[str, Any],
        signature: Mapping[str, Any],
        dependencies: Iterable[Mapping[str, Any]],
    ) -> None:
        rows.append(
            _manifest_row(
                model=target,
                family=family,
                sheet=str(entry["sheetName"]),
                action=manifest_action(existing, values, entry["headers"]),
                key=key,
                values=values,
                signature=signature,
                dependencies=dependencies,
                status="ready",
            )
        )

    reason_fact_type = {
        "comparator_only_rule_group_proposal": "rule_group",
        "comparator_only_exclusive_group_proposal": "exclusive_group",
        "comparator_only_price_rule_proposal": "price_rule",
        "comparator_only_default_selection_proposal": "default_selection",
    }
    for subject in relationship_result.get("exceptions") or []:
        reason = str(subject.get("reasonCode") or "")
        fact_type = reason_fact_type.get(reason)
        if fact_type is None:
            continue
        matches = resolutions_by_subject.get(str(subject.get("subjectId") or ""), [])
        if len(matches) != 1:
            continue
        try:
            resolution = validate_resolution(matches[0], subject)
        except ValueError:
            continue
        if resolution.get("action") != "provide_typed_value":
            continue
        proposals = list(subject.get("proposedRows") or [])
        if len(proposals) != 1:
            continue
        proposal = dict(proposals[0])
        payload = dict(resolution["payload"])
        dependencies = [
            *(subject.get("evidenceDependencies") or []),
            _dependency(f"resolution:{subject['subjectId']}", resolution),
        ]
        emitted_before = len(rows)

        if reason == "comparator_only_rule_group_proposal":
            source_id = rpo_ids.get(str(proposal.get("sourceRpo") or "").upper())
            member_ids = [
                rpo_ids.get(str(rpo).upper())
                for rpo in proposal.get("memberRpos") or []
            ]
            if not source_id or not member_ids or not all(member_ids):
                continue
            parent_entry = registry["rule_groups_sheet"]
            member_entry = registry["rule_group_members_sheet"]
            body_scope = "" if proposal.get("bodyStyleScope") in {None, "", "*"} else str(proposal["bodyStyleScope"])
            trim_scope = "" if proposal.get("trimLevelScope") in {None, "", "*"} else str(proposal["trimLevelScope"])
            variant_scope = "" if proposal.get("variantScope") in {None, "", "*"} else str(proposal["variantScope"])
            existing_parents = [
                row
                for row in _rows(extract, parent_entry["sheetName"])
                if str(row.get("source_id") or "") == source_id
                and str(row.get("group_type") or "") == str(proposal.get("groupType") or "")
                and str(row.get("body_style_scope") or "") == body_scope
                and str(row.get("trim_level_scope") or "") == trim_scope
                and str(row.get("variant_scope") or "") == variant_scope
            ]
            if len(existing_parents) > 1:
                continue
            existing_parent = existing_parents[0] if existing_parents else {}
            group_id = str(
                existing_parent.get("group_id")
                or deterministic_family_id("rule_groups", target, proposal)
            )
            existing_members = [
                row
                for row in _rows(extract, member_entry["sheetName"])
                if str(row.get("group_id") or "") == group_id
            ]
            if existing_parent and {
                str(row.get("target_id") or "") for row in existing_members
            } != set(member_ids):
                continue
            parent_values = _complete_values(
                parent_entry["headers"],
                {
                    **existing_parent,
                    "group_id": group_id,
                    "group_type": str(proposal.get("groupType") or ""),
                    "source_id": source_id,
                    "body_style_scope": body_scope,
                    "trim_level_scope": trim_scope,
                    "variant_scope": variant_scope,
                    "disabled_reason": "",
                    "active": True,
                    "notes": "Ingest typed comparator proposal confirmation",
                },
            )
            add_row(
                family="rule_groups",
                entry=parent_entry,
                existing=existing_parent,
                key={"group_id": group_id},
                values=parent_values,
                signature=proposal,
                dependencies=dependencies,
            )
            existing_by_target = {
                str(row.get("target_id") or ""): row for row in existing_members
            }
            for order, member_id in enumerate(member_ids, start=1):
                existing_member = existing_by_target.get(str(member_id), {})
                member_values = _complete_values(
                    member_entry["headers"],
                    {
                        **existing_member,
                        "group_id": group_id,
                        "target_id": member_id,
                        "display_order": order,
                        "active": True,
                    },
                )
                add_row(
                    family="rule_group_members",
                    entry=member_entry,
                    existing=existing_member,
                    key={"group_id": group_id, "target_id": member_id},
                    values=member_values,
                    signature={**proposal, "memberRpo": proposal["memberRpos"][order - 1]},
                    dependencies=dependencies,
                )

        elif reason == "comparator_only_exclusive_group_proposal":
            member_ids = [
                rpo_ids.get(str(rpo).upper())
                for rpo in proposal.get("memberRpos") or []
            ]
            if not member_ids or not all(member_ids):
                continue
            parent_entry = registry["exclusive_groups_sheet"]
            member_entry = registry["exclusive_group_members_sheet"]
            all_members = _rows(extract, member_entry["sheetName"])
            matching_parents = []
            for parent in _rows(extract, parent_entry["sheetName"]):
                group_id = str(parent.get("group_id") or "")
                existing_ids = {
                    str(row.get("option_id") or "")
                    for row in all_members
                    if str(row.get("group_id") or "") == group_id
                }
                if (
                    str(parent.get("selection_mode") or "") == str(payload["selectionMode"])
                    and existing_ids == set(member_ids)
                ):
                    matching_parents.append(parent)
            if len(matching_parents) > 1:
                continue
            existing_parent = matching_parents[0] if matching_parents else {}
            group_id = str(
                existing_parent.get("group_id")
                or deterministic_family_id("exclusive_groups", target, proposal)
            )
            parent_values = _complete_values(
                parent_entry["headers"],
                {
                    **existing_parent,
                    "group_id": group_id,
                    "selection_mode": str(payload["selectionMode"]),
                    "active": True,
                    "notes": "Ingest typed comparator proposal confirmation",
                },
            )
            add_row(
                family="exclusive_groups",
                entry=parent_entry,
                existing=existing_parent,
                key={"group_id": group_id},
                values=parent_values,
                signature=proposal,
                dependencies=dependencies,
            )
            existing_members = {
                str(row.get("option_id") or ""): row
                for row in all_members
                if str(row.get("group_id") or "") == group_id
            }
            for order, member_id in enumerate(member_ids, start=1):
                existing_member = existing_members.get(str(member_id), {})
                member_values = _complete_values(
                    member_entry["headers"],
                    {
                        **existing_member,
                        "group_id": group_id,
                        "option_id": member_id,
                        "display_order": order,
                        "active": True,
                    },
                )
                add_row(
                    family="exclusive_group_members",
                    entry=member_entry,
                    existing=existing_member,
                    key={"group_id": group_id, "option_id": member_id},
                    values=member_values,
                    signature={**proposal, "memberRpo": proposal["memberRpos"][order - 1]},
                    dependencies=dependencies,
                )

        elif reason == "comparator_only_price_rule_proposal":
            condition_id = rpo_ids.get(str(proposal.get("conditionRpo") or "").upper())
            target_id = rpo_ids.get(str(proposal.get("targetRpo") or "").upper())
            if not condition_id or not target_id:
                continue
            entry = registry["price_rules_sheet"]
            body_scope = "" if payload["bodyStyleScope"] == "*" else str(payload["bodyStyleScope"])
            trim_scope = "" if payload["trimLevelScope"] == "*" else str(payload["trimLevelScope"])
            variant_scope = "" if payload["variantScope"] == "*" else str(payload["variantScope"])
            existing_rules = [
                row
                for row in _rows(extract, entry["sheetName"])
                if str(row.get("condition_option_id") or "") == condition_id
                and str(row.get("target_option_id") or "") == target_id
                and str(row.get("price_rule_type") or "") == str(proposal.get("priceRuleType") or "")
                and str(row.get("body_style_scope") or "") == body_scope
                and str(row.get("trim_level_scope") or "") == trim_scope
                and str(row.get("variant_scope") or "") == variant_scope
            ]
            if len(existing_rules) > 1:
                continue
            existing = existing_rules[0] if existing_rules else {}
            target_signature = {
                **proposal,
                "bodyStyleScope": payload["bodyStyleScope"],
                "trimLevelScope": payload["trimLevelScope"],
                "variantScope": payload["variantScope"],
                "priceValue": int(payload["priceValue"]),
            }
            price_rule_id = str(
                existing.get("price_rule_id")
                or deterministic_family_id("price_rules", target, target_signature)
            )
            values = _complete_values(
                entry["headers"],
                {
                    **existing,
                    "price_rule_id": price_rule_id,
                    "condition_option_id": condition_id,
                    "price_rule_type": str(proposal.get("priceRuleType") or ""),
                    "target_option_id": target_id,
                    "price_value": int(payload["priceValue"]),
                    "body_style_scope": body_scope,
                    "trim_level_scope": trim_scope,
                    "variant_scope": variant_scope,
                    "notes": "Ingest target-authored comparator price confirmation",
                },
            )
            add_row(
                family="price_rules",
                entry=entry,
                existing=existing,
                key={"price_rule_id": price_rule_id},
                values=values,
                signature=target_signature,
                dependencies=dependencies,
            )

        else:
            target_id = rpo_ids.get(str(proposal.get("targetRpo") or "").upper())
            condition_type = str(proposal.get("conditionType") or "")
            if not target_id or condition_type not in {
                "always",
                "unless_selected_rpo",
                "when_selected_unless_selected_section",
            }:
                continue
            if condition_type == "always":
                condition_id = ""
            elif condition_type == "unless_selected_rpo":
                condition_id = str(proposal.get("conditionRpo") or "").upper()
            else:
                condition_id = rpo_ids.get(str(proposal.get("conditionRpo") or "").upper()) or ""
            if condition_type != "always" and not condition_id:
                continue
            default_sheet = _sheet(extract, "default_selection_rules")
            if default_sheet is None:
                continue
            entry = {
                "sheetName": "default_selection_rules",
                "headers": list(default_sheet["headers"]),
            }
            target_signature = {
                **proposal,
                "priority": int(payload["priority"]),
                "displayBehavior": str(payload["displayBehavior"]),
            }
            existing_rules = [
                row
                for row in _rows(extract, "default_selection_rules")
                if str(row.get("model_key") or "") == target
                and str(row.get("target_option_id") or "") == target_id
                and str(row.get("condition_type") or "") == condition_type
                and str(row.get("condition_id") or "") == condition_id
            ]
            if len(existing_rules) > 1:
                continue
            existing = existing_rules[0] if existing_rules else {}
            rule_id = str(
                existing.get("rule_id")
                or deterministic_family_id("default_selection_rules", target, target_signature)
            )
            values = _complete_values(
                entry["headers"],
                {
                    **existing,
                    "model_key": target,
                    "rule_id": rule_id,
                    "target_option_id": target_id,
                    "condition_type": condition_type,
                    "condition_id": condition_id,
                    "body_style_scope": "" if proposal.get("bodyStyleScope") in {None, "", "*"} else str(proposal["bodyStyleScope"]),
                    "trim_level_scope": "" if proposal.get("trimLevelScope") in {None, "", "*"} else str(proposal["trimLevelScope"]),
                    "variant_scope": "" if proposal.get("variantScope") in {None, "", "*"} else str(proposal["variantScope"]),
                    "priority": int(payload["priority"]),
                    "active": True,
                    "notes": "Ingest target-authored comparator default confirmation",
                    "display_behavior": str(payload["displayBehavior"]),
                },
            )
            add_row(
                family="default_selection_rules",
                entry=entry,
                existing=existing,
                key={"model_key": target, "rule_id": rule_id},
                values=values,
                signature=target_signature,
                dependencies=dependencies,
            )

        if len(rows) == emitted_before:
            continue
        consumed.add(str(subject["subjectId"]))
        for reference in subject.get("evidenceReferences") or []:
            if str(reference).startswith("comparator:"):
                disposition_overrides[str(reference)] = "compiled_ready"
        compiled_fact_keys.add(
            semantic_hash({"factType": fact_type, "signature": proposal})
        )
    return rows, consumed, disposition_overrides, compiled_fact_keys


def _status_semantic_signature(status: Mapping[str, Any]) -> str:
    return semantic_hash(
        {key: value for key, value in status.items() if key != "columnLetter"}
    )


def _candidate_feature_index(
    candidates: Iterable[Mapping[str, Any]],
) -> dict[str, str]:
    by_occurrence: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for candidate in candidates:
        by_occurrence[option_occurrence_signature(candidate)].append(candidate)
    index: dict[str, str] = {}
    for candidate_signature, group in sorted(by_occurrence.items()):
        for ordinal, candidate in enumerate(
            sorted(group, key=lambda item: str(item.get("candidateId") or "")),
            start=1,
        ):
            index[str(candidate.get("candidateId") or "")] = (
                f"option-occurrence:{candidate_signature}:{ordinal}"
            )
    return index


def _status_feature_index(
    candidates: Iterable[Mapping[str, Any]],
) -> dict[str, dict[str, list[str]]]:
    by_occurrence: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for candidate in candidates:
        by_occurrence[option_occurrence_signature(candidate)].append(candidate)
    index: dict[str, dict[str, list[str]]] = {}
    for candidate_signature, group in sorted(by_occurrence.items()):
        for candidate_ordinal, candidate in enumerate(
            sorted(group, key=lambda item: str(item.get("candidateId") or "")),
            start=1,
        ):
            status_groups: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
            for status in candidate.get("statuses") or []:
                status_groups[_status_semantic_signature(status)].append(status)
            candidate_index: dict[str, list[str]] = {}
            for status_signature, statuses in sorted(status_groups.items()):
                candidate_index[status_signature] = [
                    f"status:{candidate_signature}:{candidate_ordinal}:{status_signature}:{ordinal}"
                    for ordinal in range(1, len(statuses) + 1)
                ]
            index[str(candidate.get("candidateId") or "")] = candidate_index
    return index


def _source_feature_ledger(
    targets: list[str],
    option_payload: Mapping[str, Any],
    price_payload: Mapping[str, Any],
    roles_payload: Mapping[str, Any],
    candidate_dispositions: Mapping[tuple[str, str], str],
    relationship_dispositions: Iterable[Mapping[str, Any]],
    comparator_artifact: Mapping[str, Any],
    compiled_base_price_rows: set[str],
    compiled_status_features: set[str],
    status_feature_index: Mapping[str, Mapping[str, list[str]]],
    candidate_feature_index: Mapping[str, str],
    *,
    color_trim_profiled: bool = False,
) -> list[dict[str, Any]]:
    ledger: list[dict[str, Any]] = []
    for sheet_name, role in sorted((roles_payload.get("roles") or {}).items()):
        if role == "exclude":
            disposition = (
                "compiled"
                if color_trim_profiled
                and "color" in sheet_name.lower()
                and "trim" in sheet_name.lower()
                else "exception_open"
                if "color" in sheet_name.lower() and "trim" in sheet_name.lower()
                else "resolved_not_applicable"
            )
            ledger.append({"featureId": f"source-sheet:{sheet_name}", "model": "*", "family": "source_sheet", "disposition": disposition, "evidenceIds": [f"sheet-role:{sheet_name}"]})
    candidates = option_payload.get("candidates") or []
    for candidate in candidates:
        candidate_id = str(candidate.get("candidateId") or "")
        candidate_feature_id = candidate_feature_index[candidate_id]
        applicable = False
        for target in targets:
            key = (target, candidate_id)
            if key in candidate_dispositions:
                applicable = True
                ledger.append({"featureId": f"candidate:{target}:{candidate_feature_id}", "model": target, "family": "options", "disposition": _source_disposition(candidate_dispositions[key]), "evidenceIds": [candidate_feature_id]})
        if not applicable:
            ledger.append({"featureId": f"candidate:unselected:{candidate_feature_id}", "model": "*", "family": "options", "disposition": "resolved_not_applicable", "evidenceIds": [candidate_feature_id]})
        seen_status_signatures: set[str] = set()
        for status in candidate.get("statuses") or []:
            status_signature = _status_semantic_signature(status)
            if status_signature in seen_status_signatures:
                continue
            seen_status_signatures.add(status_signature)
            selected_models = [
                target
                for target in targets
                if any(
                    scoped.get("columnLetter") == status.get("columnLetter")
                    for scoped in model_scoped_statuses(candidate, target)
                )
            ]
            model = selected_models[0] if len(selected_models) == 1 else "*"
            for feature_id in status_feature_index.get(candidate_id, {}).get(status_signature, []):
                disposition = (
                    "compiled"
                    if feature_id in compiled_status_features
                    else "exception_open"
                    if selected_models
                    else "resolved_not_applicable"
                )
                ledger.append({"featureId": feature_id, "model": model, "family": "ovs", "disposition": disposition, "evidenceIds": [feature_id]})
    for sheet, rows in sorted((option_payload.get("skippedRows") or {}).items()):
        for item in rows:
            row_index = item.get("rowIndex")
            ledger.append({"featureId": f"skipped-option:{sheet}:{row_index}:{item.get('reason')}", "model": "*", "family": "options", "disposition": "unsupported_blocker" if item.get("reason") != "sheet_not_options_matrix" else "resolved_not_applicable", "evidenceIds": [f"{sheet}:{row_index}"]})
    selected_candidates = [
        candidate
        for candidate in candidates
        if any((target, str(candidate.get("candidateId") or "")) in candidate_dispositions for target in targets)
    ]
    selected_price_dispositions: dict[str, set[str]] = defaultdict(set)
    for candidate in selected_candidates:
        candidate_id = str(candidate.get("candidateId") or "")
        candidate_blocked = any(
            candidate_dispositions.get((target, candidate_id)) == "blocked_exception"
            for target in targets
        )
        disposition = "compiled" if candidate.get("priceMatch") == "exact" and not candidate_blocked else "exception_open"
        for price_row in candidate.get("priceRows") or []:
            selected_price_dispositions[semantic_hash(price_row)].add(disposition)
    for row in sorted(price_payload.get("priceRows") or [], key=semantic_hash):
        rpo = str(row.get("rpo") or "")
        row_hash = semantic_hash(row)
        row_dispositions = selected_price_dispositions.get(semantic_hash(row), set())
        disposition = "exception_open" if "exception_open" in row_dispositions else "compiled" if "compiled" in row_dispositions else "resolved_not_applicable"
        ledger.append({"featureId": f"price:{rpo}:{row_hash}", "model": "*", "family": "price_rules", "disposition": disposition, "evidenceIds": [str((row.get("sourceEvidence") or {}).get("sheetName") or "price")]})
    for row in sorted(price_payload.get("baseModelPriceRows") or [], key=semantic_hash):
        model = MODEL_CODE_PREFIXES.get(str(row.get("modelCode") or "")[:3], "*")
        row_hash = semantic_hash(row)
        disposition = (
            "compiled"
            if semantic_hash(row) in compiled_base_price_rows
            else "exception_open"
            if model in targets
            else "resolved_not_applicable"
        )
        ledger.append({"featureId": f"base-price:{row.get('modelCode')}:{row_hash}", "model": model, "family": "variant_master", "disposition": disposition, "evidenceIds": [str((row.get("sourceEvidence") or {}).get("sheetName") or "price")]})
    for row in sorted(price_payload.get("skippedPriceRows") or [], key=semantic_hash):
        ledger.append({"featureId": f"skipped-price:{semantic_hash(row)}", "model": "*", "family": "price_rules", "disposition": "unsupported_blocker", "evidenceIds": [f"{row.get('sheetName')}:{row.get('rowIndex')}"]})
    relationship_dispositions = list(relationship_dispositions)
    comparator_effects: dict[str, str] = {}
    for disposition in relationship_dispositions:
        feature_id = str(disposition.get("featureId") or "")
        if feature_id.startswith("comparator:"):
            for evidence_id in disposition.get("evidenceIds") or []:
                comparator_effects[str(evidence_id)] = str(disposition.get("disposition") or "")
            continue
        model = str(disposition.get("model") or "*")
        ledger.append({"featureId": f"relationship:{model}:{disposition.get('featureId')}", "model": model, "family": "rule_mapping", "disposition": _source_disposition(disposition.get("disposition")), "evidenceIds": list(disposition.get("evidenceIds") or [])})
    comparator_exception_ids = {
        evidence_id
        for disposition in relationship_dispositions
        if disposition.get("disposition") == "proposed_exception"
        for evidence_id in disposition.get("evidenceIds") or []
        if str(evidence_id).startswith("comparator:")
    }
    for target, entry in sorted((comparator_artifact.get("targets") or {}).items()):
        for fact in entry.get("facts") or []:
            evidence_id = str(fact.get("evidenceId") or "")
            disposition = (
                _source_disposition(comparator_effects[evidence_id])
                if evidence_id in comparator_effects
                else "exception_open"
                if evidence_id in comparator_exception_ids
                else "resolved_not_applicable"
            )
            ledger.append({"featureId": f"comparator:{target}:{evidence_id}", "model": target, "family": fact.get("factType"), "disposition": disposition, "evidenceIds": [evidence_id]})
    ids = [item["featureId"] for item in ledger]
    if len(ids) != len(set(ids)):
        duplicates = sorted({value for value in ids if ids.count(value) > 1})
        raise ValueError(f"Duplicate source-feature ledger entries: {duplicates}")
    return sorted(ledger, key=lambda item: item["featureId"])


def _merge_manifest_rows(rows: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Collapse shared-sheet derivations to one canonical workbook row."""

    semantic_relationships: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    others: list[dict[str, Any]] = []
    for raw in rows:
        row = dict(raw)
        if row.get("family") == "rule_mapping":
            values = dict(row.get("values") or {})
            values.pop("rule_id", None)
            semantic_relationships[(str(row.get("sheet") or ""), semantic_hash(values))].append(row)
        else:
            others.append(row)
    collapsed = list(others)
    action_rank = {"noop": 0, "update": 1, "add": 2, "delete": 3}
    for group in semantic_relationships.values():
        selected = min(
            group,
            key=lambda row: (
                action_rank.get(str(row.get("action") or ""), 9),
                canonical_text(row.get("key") or {}),
            ),
        )
        dependencies = {
            dependency["evidenceId"]: dependency
            for row in group
            for dependency in row.get("evidenceDependencies") or []
        }
        selected = dict(selected)
        models = {str(row.get("model") or "") for row in group}
        selected["model"] = next(iter(models)) if len(models) == 1 else "*"
        selected["evidenceDependencies"] = [dependencies[key] for key in sorted(dependencies)]
        selected["derivationVersion"] = derivation_version(
            selected["semanticSignature"], selected["evidenceDependencies"]
        )
        collapsed.append(selected)
    by_key: dict[tuple[str, str], dict[str, Any]] = {}
    for row in collapsed:
        key = (str(row.get("sheet") or ""), canonical_text(row.get("key") or {}))
        existing = by_key.get(key)
        if existing is None:
            by_key[key] = row
            continue
        if existing.get("values") != row.get("values") or existing.get("action") != row.get("action"):
            raise ValueError(f"Conflicting canonical workbook rows for {key}.")
        dependencies = {
            dependency["evidenceId"]: dependency
            for item in (existing, row)
            for dependency in item.get("evidenceDependencies") or []
        }
        existing["model"] = existing["model"] if existing["model"] == row["model"] else "*"
        existing["evidenceDependencies"] = [dependencies[value] for value in sorted(dependencies)]
        existing["derivationVersion"] = derivation_version(
            existing["semanticSignature"], existing["evidenceDependencies"]
        )
    return sorted(
        by_key.values(),
        key=lambda row: (str(row.get("sheet") or ""), canonical_text(row.get("key") or {})),
    )


def _retained_existing_rows(
    extract: Mapping[str, Any],
    targets: Iterable[str],
    registry: Mapping[str, Mapping[str, Mapping[str, Any]]],
    current_rows: Iterable[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    emitted = {
        (str(row.get("sheet") or ""), canonical_text(row.get("key") or {}))
        for row in current_rows
    }
    retained: list[dict[str, Any]] = []

    def add_rows(model: str, family: str, sheet: str, headers: Iterable[str], rows: Iterable[Mapping[str, Any]]) -> None:
        key_columns = tuple(EDITOR_SHEET_META[family]["key"])
        bool_columns = {
            column
            for column, kind in EDITOR_SHEET_META[family].get("types", {}).items()
            if kind == "bool"
        }
        for source in rows:
            key = {column: source.get(column, "") for column in key_columns}
            workbook_key = (sheet, canonical_text(key))
            if workbook_key in emitted:
                continue
            values = _complete_values(headers, source)
            for column in bool_columns:
                if column in values:
                    values[column] = bool(workbook_truthy(values[column]))
            signature = {"family": family, "sheet": sheet, "retainedKey": key}
            dependencies = [_dependency(f"workbook:{sheet}:{canonical_text(key)}", source)]
            retained.append(
                _manifest_row(
                    model=model,
                    family=family,
                    sheet=sheet,
                    action="noop",
                    key=key,
                    values=values,
                    signature=signature,
                    dependencies=dependencies,
                    status="ready",
                    disposition="retained_existing",
                )
            )
            emitted.add(workbook_key)

    target_list = [str(target) for target in targets]
    sheet_targets: dict[str, set[str]] = defaultdict(set)
    for target in target_list:
        for entry in registry[target].values():
            sheet_targets[str(entry["sheetName"])].add(target)
    for target in target_list:
        for entry in registry[str(target)].values():
            add_rows(
                "*" if len(sheet_targets[str(entry["sheetName"])]) > 1 else str(target),
                str(entry["family"]),
                str(entry["sheetName"]),
                entry["headers"],
                _rows(extract, str(entry["sheetName"])),
            )
        for sheet, family in sorted(GLOBAL_SHEET_FAMILIES.items()):
            for row in _rows(extract, sheet):
                row_model = str(row.get("model_key") or "").lower()
                if row_model not in {"", str(target), "*"}:
                    continue
                add_rows(
                    row_model if row_model in target_list else "*",
                    family,
                    sheet,
                    _headers(extract, sheet),
                    [row],
                )
    return retained


def _family_coverage(
    extract: Mapping[str, Any],
    targets: list[str],
    registry: Mapping[str, Mapping[str, Mapping[str, Any]]],
    manifest_rows: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    coverage: list[dict[str, Any]] = []
    blockers: list[dict[str, Any]] = []
    output_rows: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in manifest_rows:
        output_rows[(row["model"], row["family"])].append(row)
    for target in targets:
        for role in ROLE_ORDER:
            entry = registry[target][role]
            family = entry["family"]
            feature_id = f"family:{target}:{family}"
            family_rows = output_rows[(target, family)] + output_rows[("*", family)]
            if family_rows:
                disposition = (
                    "retained_existing"
                    if all(row.get("disposition") == "retained_existing" for row in family_rows)
                    else "compiled"
                )
                evidence_ids = [f"sheet:{entry['sheetName']}"]
            elif _rows(extract, entry["sheetName"]):
                disposition = "retained_existing"
                evidence_ids = [f"sheet:{entry['sheetName']}"]
            elif family in VALID_EMPTY_SOURCE_FAMILIES:
                disposition = "explicit_empty"
                evidence_ids = [f"role:{role}:verified-zero-row"]
            else:
                disposition = "unsupported_blocker"
                evidence_ids = [f"role:{role}:missing-target-evidence"]
                blockers.append(
                    _typed_exception(target, family, "unsupported_family", [family], [_dependency(f"family:{target}:{family}", entry)], evidence_references=evidence_ids, question=f"Provide target evidence for required family {family}.")
                )
            coverage.append({"featureId": feature_id, "model": target, "family": family, "disposition": disposition, "evidenceIds": evidence_ids})
        for sheet_name, family in sorted(GLOBAL_SHEET_FAMILIES.items()):
            relevant = [row for row in _rows(extract, sheet_name) if str(row.get("model_key") or "").lower() in {"", target, "*"}]
            family_rows = output_rows[(target, family)] + output_rows[("*", family)]
            if family_rows:
                disposition = (
                    "retained_existing"
                    if all(row.get("disposition") == "retained_existing" for row in family_rows)
                    else "compiled"
                )
                evidence_ids = [f"global-sheet:{sheet_name}"]
            elif relevant:
                disposition = "retained_existing"
                evidence_ids = [f"global-sheet:{sheet_name}"]
            elif family in VALID_EMPTY_GLOBAL_FAMILIES:
                disposition = "explicit_empty"
                evidence_ids = [f"global-sheet:{sheet_name}:verified-zero-row"]
            else:
                disposition = "unsupported_blocker"
                evidence_ids = [f"global-sheet:{sheet_name}:missing-target-row"]
                blockers.append(
                    _typed_exception(target, family, "unsupported_global_family", [sheet_name], [_dependency(f"global-family:{target}:{sheet_name}", {"sheet": sheet_name, "target": target})], evidence_references=evidence_ids, question=f"Provide target metadata for {sheet_name}.")
                )
            coverage.append({"featureId": f"global-family:{target}:{family}", "model": target, "family": family, "disposition": disposition, "evidenceIds": evidence_ids})
    ids = [item["featureId"] for item in coverage]
    if len(ids) != len(set(ids)):
        raise ValueError("Family coverage must contain exactly one disposition per model/family.")
    return coverage, blockers


def _evidence_partitions(
    targets: Iterable[str],
    manifest_rows: Iterable[Mapping[str, Any]],
    subjects: Iterable[Mapping[str, Any]],
    phrase_rows: Iterable[Mapping[str, Any]],
    comparator_artifact: Mapping[str, Any],
) -> dict[str, Any]:
    target_dependencies: dict[str, dict[str, str]] = {str(target): {} for target in targets}
    workbook_dependencies: dict[str, str] = {}
    target_set = set(target_dependencies)
    for item in [*manifest_rows, *subjects]:
        model = str(item.get("model") or "")
        affected = target_set if model == "*" else ({model} if model in target_set else set())
        for dependency in item.get("evidenceDependencies") or []:
            evidence_id = str(dependency.get("evidenceId") or "")
            fingerprint = str(dependency.get("semanticFingerprint") or "")
            if not evidence_id or not fingerprint:
                continue
            if evidence_id.startswith(("phrase:", "comparator:")):
                continue
            if evidence_id.startswith("target:"):
                for target in affected:
                    target_dependencies[target][evidence_id] = fingerprint
            if evidence_id.startswith(
                (
                    "workbook:",
                    "section:",
                    "precedent:",
                    "global-family:",
                    "existing-relationship:",
                )
            ):
                workbook_dependencies[evidence_id] = fingerprint
    return {
        "targetEvidenceFingerprint": {
            target: semantic_hash(
                [
                    {"evidenceId": evidence_id, "fingerprint": fingerprint}
                    for evidence_id, fingerprint in sorted(dependencies.items())
                ]
            )
            for target, dependencies in sorted(target_dependencies.items())
        },
        "comparatorEvidenceFingerprint": {
            str(target): str(entry.get("comparatorEvidenceFingerprint") or "")
            for target, entry in sorted((comparator_artifact.get("targets") or {}).items())
        },
        "phraseEvidenceFingerprint": {
            str(row.get("phrase") or "").strip().lower(): semantic_hash(row)
            for row in phrase_rows
            if str(row.get("phrase") or "").strip()
        },
        "workbookEvidenceFingerprint": dict(sorted(workbook_dependencies.items())),
    }


def compile_canonical_rows(
    *,
    workbook_path: Path,
    option_payload: Mapping[str, Any],
    price_payload: Mapping[str, Any],
    join_report: Mapping[str, Any],
    roles_payload: Mapping[str, Any],
    selection: Mapping[str, Any],
    comparator_artifact: Mapping[str, Any],
    run_authority_fingerprint: Mapping[str, Any],
    resolution_entries: Iterable[Mapping[str, Any]] = (),
) -> dict[str, Any]:
    resolution_entries = list(resolution_entries)
    targets = [str(value) for value in selection.get("targets") or []]
    if not targets:
        raise ValueError("Compiler requires selected target models.")
    comparators = {str(key): str(value) for key, value in (selection.get("comparators") or {}).items()}
    if set(comparators) != set(targets):
        raise ValueError("Compiler comparators must cover the exact target set.")
    if set(comparator_artifact.get("targets") or {}) != set(targets):
        raise ValueError("Comparator artifact does not cover the exact selected targets.")
    registry = build_family_registry(Path(workbook_path), targets)
    extract = extract_workbook(Path(workbook_path))
    phrase_rows = load_compiler_phrase_map(Path(workbook_path))
    manifest_rows: list[dict[str, Any]] = []
    exceptions: list[dict[str, Any]] = []
    candidate_dispositions: dict[tuple[str, str], str] = {}
    relationship_dispositions: list[dict[str, Any]] = []
    target_rpo_index: dict[str, set[str]] = {}
    compiled_comparator_fact_keys: dict[str, set[str]] = defaultdict(set)
    comparator_effect_dispositions: dict[tuple[str, str], str] = {}
    consumed_resolution_subjects: set[str] = set()
    compiled_base_price_rows: set[str] = set()
    compiled_status_features: set[str] = set()
    profiled_targets: set[str] = set()
    candidates = [dict(candidate) for candidate in option_payload.get("candidates") or []]
    candidate_feature_index = _candidate_feature_index(candidates)
    status_feature_index = _status_feature_index(candidates)
    join_counts = Counter(str(candidate.get("priceMatch") or "") for candidate in candidates)
    expected_join_counts = {
        "exactMatches": join_counts.get("exact", 0),
        "ambiguousMatches": join_counts.get("ambiguous", 0),
        "missingPrices": join_counts.get("none", 0),
    }
    for field, expected in expected_join_counts.items():
        if int(join_report.get(field, -1)) != expected:
            raise ValueError(
                f"Join report {field}={join_report.get(field)!r} does not match candidate evidence {expected}."
            )
    matched_price_rows = {
        semantic_hash(row)
        for candidate in candidates
        for row in candidate.get("priceRows") or []
    }
    expected_unmatched_rows = sorted(
        semantic_hash(row)
        for row in price_payload.get("priceRows") or []
        if semantic_hash(row) not in matched_price_rows
    )
    reported_unmatched_rows = sorted(
        semantic_hash(row) for row in join_report.get("unmatchedPriceRows") or []
    )
    if reported_unmatched_rows != expected_unmatched_rows:
        raise ValueError("Join report unmatchedPriceRows do not match parsed price evidence.")
    for target in targets:
        variant_rows, variant_exceptions, variants, compiled_prices = _compile_target_variants(
            extract, target, price_payload
        )
        manifest_rows.extend(variant_rows)
        exceptions.extend(variant_exceptions)
        compiled_base_price_rows.update(compiled_prices)
        option_rows, option_exceptions, dispositions, rpo_ids, consumed, compiled_statuses = _compile_target_options(
            extract,
            registry[target],
            target,
            candidates,
            variants,
            resolution_entries,
            status_feature_index,
        )
        profile_variants_by_id = {
            str(row.get("variant_id") or ""): dict(row)
            for row in _target_variant_rows(extract, target)
            if str(row.get("variant_id") or "")
        }
        profile_variants_by_id.update(
            {
                str(row.get("variant_id") or ""): dict(row)
                for row in variants
                if str(row.get("variant_id") or "")
            }
        )
        profile = build_target_profile(
            extract,
            registry[target],
            target=target,
            comparator=comparators[target],
            variants=profile_variants_by_id.values(),
        )
        registry[target]["interior_source_sheet"] = {
            **registry[target]["interior_source_sheet"],
            "sheetName": profile["interiorSheet"],
            "headers": _headers(extract, profile["interiorSheet"]),
        }
        profile_rows = [
            _manifest_row(
                model=str(row["model"]),
                family=str(row["family"]),
                sheet=str(row["sheet"]),
                action=str(row["action"]),
                key=row["key"],
                values=row["values"],
                signature=row["semanticSignature"],
                dependencies=row["evidenceDependencies"],
                status="ready",
            )
            for row in profile["rows"]
        ]
        profile_rpos = {str(rpo).upper() for rpo in profile["optionRpoIds"]}
        profile_option_ids = {
            str(option_id) for option_id in profile["optionRpoIds"].values()
        }
        option_rows = [
            row
            for row in option_rows
            if not (
                row["family"] == "options"
                and str(row["values"].get("rpo") or "").upper() in profile_rpos
            )
            and not (
                row["family"] == "ovs"
                and str(row["values"].get("option_id") or "") in profile_option_ids
            )
        ]
        option_rows.extend(
            row for row in profile_rows if row["family"] in {"options", "ovs"}
        )
        manifest_rows.extend(
            row for row in profile_rows if row["family"] not in {"options", "ovs"}
        )
        for rpo, option_id in profile["optionRpoIds"].items():
            existing_id = rpo_ids.get(str(rpo))
            if existing_id and existing_id != option_id:
                raise ValueError(
                    f"Target {target} profile RPO {rpo} conflicts with compiled option identity."
                )
            rpo_ids[str(rpo)] = str(option_id)
        profiled_targets.add(target)
        consumed_resolution_subjects.update(consumed)
        compiled_status_features.update(compiled_statuses)
        manifest_rows.extend(option_rows)
        exceptions.extend(option_exceptions)
        candidate_dispositions.update({(target, key): value for key, value in dispositions.items()})
        comparator_facts = list((comparator_artifact.get("targets") or {}).get(target, {}).get("facts") or [])
        scoped = [
            {
                **candidate,
                "targetModel": target,
                "_sourceFeatureId": candidate_feature_index[str(candidate.get("candidateId") or "")],
            }
            for candidate in scope_candidates(candidates, target)
        ]
        target_rpos = set(rpo_ids) | {
            str(candidate.get("rpo") or candidate.get("refOnlyRpo") or "").upper()
            for candidate in scoped
        }
        target_rpo_index[target] = target_rpos
        rpo_by_option_id = {
            str(option_id): str(rpo).upper()
            for rpo, option_id in rpo_ids.items()
            if str(option_id)
        }
        endpoint_catalog = {
            token: [
                {
                    "endpointType": "interior",
                    "endpointId": interior_id,
                    "profileRequiredRpo": rpo_by_option_id.get(
                        str(profile["interiorRequirements"].get(interior_id) or ""),
                        "",
                    ),
                }
                for interior_id in interior_ids
            ]
            for token, interior_ids in profile["interiorCodeIds"].items()
        }
        ignored_endpoint_tokens = {
            "GT1",
            "GT2",
            target.upper().replace("_", ""),
            comparators[target].upper().replace("_", ""),
            *(str(model).upper().replace("_", "") for model in targets),
        }
        relationship_result = compile_relationships(
            scoped,
            phrase_rows,
            target_rpos=target_rpos,
            comparator_facts=comparator_facts,
            endpoint_catalog=endpoint_catalog,
            ignored_endpoint_tokens=ignored_endpoint_tokens,
        )
        ready_option_ids = {
            str(row["values"].get("option_id") or "")
            for row in option_rows
            if row.get("family") == "options" and row.get("status") == "ready"
        }
        relationship_rows, relationship_identity_exceptions, consumed, disposition_overrides = _relationship_rows(
            extract,
            target,
            registry[target],
            rpo_ids,
            ready_option_ids,
            ready_option_ids | set(profile["interiorIds"]),
            relationship_result,
            resolution_entries,
        )
        consumed_resolution_subjects.update(consumed)
        ready_rpo_ids: dict[str, str] = {}
        for row in option_rows:
            if row.get("family") != "options" or row.get("status") != "ready":
                continue
            values = row.get("values") or {}
            rpo = str(values.get("rpo") or "").upper()
            option_id = str(values.get("option_id") or "")
            if not rpo or not option_id:
                continue
            if rpo in ready_rpo_ids and ready_rpo_ids[rpo] != option_id:
                ready_rpo_ids[rpo] = ""
            elif rpo not in ready_rpo_ids:
                ready_rpo_ids[rpo] = option_id
        proposal_rows, proposal_consumed, proposal_dispositions, proposal_fact_keys = _comparator_proposal_rows(
            extract,
            target,
            registry[target],
            ready_rpo_ids,
            relationship_result,
            resolution_entries,
        )
        consumed_resolution_subjects.update(proposal_consumed)
        disposition_overrides.update(proposal_dispositions)
        comparator_effect_dispositions.update(
            {
                (target, evidence_id): disposition
                for evidence_id, disposition in disposition_overrides.items()
                if evidence_id.startswith("comparator:")
            }
        )
        compiled_comparator_fact_keys[target].update(proposal_fact_keys)
        compiled_comparator_fact_keys[target].update(
            semantic_hash({"factType": "direct_rule", "signature": row["semanticSignature"]})
            for row in relationship_rows
            if row.get("status") == "ready"
        )
        manifest_rows.extend(relationship_rows)
        manifest_rows.extend(proposal_rows)
        exceptions.extend(relationship_identity_exceptions)
        exceptions.extend(relationship_result["exceptions"])
        identity_blocked_features = {
            reference
            for item in relationship_identity_exceptions
            for reference in item.get("evidenceReferences") or []
        }
        relationship_dispositions.extend(
            {
                **item,
                "model": target,
                "disposition": (
                    disposition_overrides[str(item.get("featureId") or "")]
                    if str(item.get("featureId") or "") in disposition_overrides
                    else "blocked_exception"
                    if item.get("featureId") in identity_blocked_features
                    else item.get("disposition")
                ),
            }
            for item in relationship_result["dispositions"]
        )
    manifest_rows.extend(_retained_existing_rows(extract, targets, registry, manifest_rows))
    manifest_rows = _merge_manifest_rows(manifest_rows)
    family_coverage, family_blockers = _family_coverage(extract, targets, registry, manifest_rows)
    exceptions.extend(family_blockers)
    # Source-sheet exclusions are evidence too. Color/Trim is known applicable but
    # unparsed, so each source sheet gets one primary blocker rather than a mirrored
    # generic source-feature blocker.
    for sheet_name, role in sorted((roles_payload.get("roles") or {}).items()):
        if role == "exclude" and "color" in sheet_name.lower() and "trim" in sheet_name.lower():
            if profiled_targets != set(targets):
                exceptions.append(
                    _typed_exception("*", "source_sheet", "unsupported_color_trim_source", [sheet_name], [_dependency(f"sheet-role:{sheet_name}", {"sheet": sheet_name, "role": role})], evidence_references=[sheet_name], question="Add a deterministic Color and Trim parser before compiling this source.")
                )
    feature_coverage = _source_feature_ledger(
        targets,
        option_payload,
        price_payload,
        roles_payload,
        candidate_dispositions,
        relationship_dispositions,
        comparator_artifact,
        compiled_base_price_rows,
        compiled_status_features,
        status_feature_index,
        candidate_feature_index,
        color_trim_profiled=profiled_targets == set(targets),
    )
    for feature in feature_coverage:
        if feature.get("disposition") != "unsupported_blocker":
            continue
        feature_id = str(feature["featureId"])
        exceptions.append(
            _typed_exception(
                str(feature.get("model") or "*"),
                str(feature.get("family") or "source_feature"),
                "unsupported_source_feature",
                [feature_id],
                [_dependency(feature_id, feature)],
                evidence_references=list(feature.get("evidenceIds") or []),
                question="Classify or support this source feature before compile readiness.",
            )
        )
    # Deduplicate identical subjects emitted by repeated source occurrences while
    # refusing contradictory definitions for the same stable semantic subject.
    subjects_by_id: dict[str, dict[str, Any]] = {}
    for item in exceptions:
        existing = subjects_by_id.get(item["subjectId"])
        if existing is not None and semantic_hash(existing) != semantic_hash(item):
            raise ValueError(f"Conflicting exception definitions for {item['subjectId']}.")
        subjects_by_id[item["subjectId"]] = item
    subjects = sorted(subjects_by_id.values(), key=lambda item: item["subjectId"])
    comparator_sha = str(comparator_artifact.get("comparatorEvidenceSemanticSha") or semantic_hash(comparator_artifact.get("targets") or {}))
    evidence_partitions = _evidence_partitions(
        targets, manifest_rows, subjects, phrase_rows, comparator_artifact
    )
    queue = build_exception_queue(
        run_authority_fingerprint,
        comparator_sha,
        subjects,
        evidence_partitions=evidence_partitions,
    )
    classified = classify_resolutions(resolution_entries, subjects)
    resolutions = build_resolution_artifact(
        queue["queueSubjectFingerprint"],
        classified["valid"],
        stale_entries=classified["stale"],
        superseded_entries=classified["superseded"],
    )
    # Validation alone never clears readiness. Each row-producing or non-row
    # action must record an explicit compiler effect before its subject closes.
    valid_subjects = {
        entry["subjectId"]
        for entry in classified["valid"]
        if entry["subjectId"] in consumed_resolution_subjects
    }
    unresolved = [subject for subject in subjects if subject["subjectId"] not in valid_subjects]
    _validate_manifest_contract(manifest_rows, registry, extract)
    established_models = {
        str(row.get("model_key") or "").lower()
        for row in _rows(extract, "model_master")
        if str(row.get("model_key") or "").strip()
    }
    model_modes = {
        target: "reprocess" if target in established_models else "greenfield"
        for target in targets
    }
    manifest = build_manifest(
        run_authority_fingerprint,
        comparator_sha,
        queue["queueSubjectFingerprint"],
        resolutions["resolutionSemanticSha"],
        manifest_rows,
        coverage=family_coverage,
        model_modes=model_modes,
        evidence_partitions=evidence_partitions,
    )
    models = {}
    for target in targets:
        blockers = [
            {"subjectId": item["subjectId"], "reasonCode": item["reasonCode"], "family": item["family"]}
            for item in unresolved
            if item["model"] in {target, "*"} and item["severity"] == "blocking"
        ]
        models[target] = {
            "mode": model_modes[target],
            "compileReady": not blockers,
            "planReady": False,
            "writeReady": False,
            "deploymentReady": False,
            "blockers": blockers,
            "boundaryReasons": ["milestone_1_no_plan_projection", "milestone_1_no_write_or_deployment"],
        }
    family_counts = dict(Counter(row["family"] for row in manifest_rows))
    manifest_counts = {
        "|".join(key): count
        for key, count in sorted(
            Counter(
                (row["model"], row["family"], row["action"], row["status"])
                for row in manifest_rows
            ).items()
        )
    }
    proposed_comparator_ids = {
        (str(subject.get("model") or ""), str(reference))
        for subject in subjects
        if str(subject.get("reasonCode") or "").startswith("comparator_only_")
        for reference in subject.get("evidenceReferences") or []
        if str(reference).startswith("comparator:")
    }
    comparator_dispositions = []
    for target, entry in sorted((comparator_artifact.get("targets") or {}).items()):
        for fact in entry.get("facts") or []:
            evidence_id = str(fact.get("evidenceId") or "")
            signature = fact.get("signature") or {}
            comparison_signature = signature
            if fact.get("factType") == "direct_rule":
                comparison_signature = {
                    "sourceRpo": signature.get("sourceRpo"),
                    "ruleType": signature.get("ruleType"),
                    "targetRpo": signature.get("targetRpo"),
                    "bodyStyleScope": signature.get("bodyStyleScope") or "*",
                    "trimLevelScope": signature.get("trimLevelScope") or "*",
                    "variantScope": signature.get("variantScope") or "*",
                }
            fact_key = semantic_hash(
                {"factType": fact.get("factType"), "signature": comparison_signature}
            )
            required_rpos = {
                str(value).upper()
                for value in (
                    [signature.get("sourceRpo"), signature.get("targetRpo"), signature.get("conditionRpo")]
                    + list(signature.get("memberRpos") or [])
                )
                if str(value or "")
            }
            if fact.get("disposition") != "corroborating_context_only":
                disposition = "comparator_nonportable_context_only"
            elif comparator_effect_dispositions.get((target, evidence_id)) == "resolved_not_applicable":
                disposition = "resolved_not_applicable"
            elif comparator_effect_dispositions.get((target, evidence_id)) == "compiled_ready":
                disposition = "corroborated_target_match"
            elif (target, evidence_id) in proposed_comparator_ids:
                disposition = "target_proposal_exception"
            elif fact_key in compiled_comparator_fact_keys.get(target, set()):
                disposition = "corroborated_target_match"
            else:
                disposition = "target_endpoint_missing_context_only"
            comparator_dispositions.append(
                {"target": target, "evidenceId": evidence_id, "disposition": disposition}
            )
    comparator_dispositions.sort(
        key=lambda item: (
            str(item.get("target") or ""),
            str(item.get("evidenceId") or ""),
            str(item.get("disposition") or ""),
        )
    )
    report = build_compile_report(
        run_authority_fingerprint,
        comparator_sha,
        queue["queueSubjectFingerprint"],
        resolutions["resolutionSemanticSha"],
        manifest["manifestSemanticSha"],
        models,
        feature_coverage,
        resolutions.get("deferrals") or [],
        family_counts=family_counts,
        manifest_counts=manifest_counts,
        incoming_reference_impact={
            **reference_graph_summary(extract),
            "deletionCandidates": sum(row["action"] == "delete" for row in manifest_rows),
            "blockedDeletions": sum(
                row["status"] == "blocked" and row["action"] == "delete"
                for row in manifest_rows
            ),
            "status": (
                "no_deletions_proposed"
                if not any(row["action"] == "delete" for row in manifest_rows)
                else "deletions_require_reference_review"
            ),
        },
        comparator_dispositions=comparator_dispositions,
        family_coverage=family_coverage,
    )
    validate_artifact_graph(manifest, report, comparator_artifact, queue, resolutions)
    return {
        "comparator-evidence.json": dict(comparator_artifact),
        "canonical-row-manifest.json": manifest,
        "exception-queue.json": queue,
        "exception-resolutions.json": resolutions,
        "compile-report.json": report,
        "exception-log-events": [],
    }
