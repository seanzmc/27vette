#!/usr/bin/env python3
"""Pure canonical-manifest-to-ChangeSet projection (``workbook-changeset-1``).

This module ports the currently verified ``build_manifest_plan()``
validation/projection into the shared immutable ChangeSet contract. It
validates and translates only: it does not rematch identity, derive
business behavior, choose IDs/values/sheets/actions, or read
``decisions.json``. ``plan_builder.build_manifest_plan`` stays untouched
for the test-local legacy-equivalence comparison and is deleted in the
Task 6 production touch; this emitter is the only current-session
emission surface.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from corvette_form_generator.editor_ops import (
    EDITOR_SHEET_META,
    GLOBAL_SHEET_FAMILIES,
    SOURCE_ROLE_FAMILIES,
    extract_workbook,
    model_sheet_registry,
)
from corvette_form_generator.ingest.wizard.plan_builder import (
    MANIFEST_ACTION_ORDER,
    MANIFEST_STAGE1_FAMILIES,
    MODEL_PLAN_CONFIG,
    MODEL_SHEET_ROLES,
)
from corvette_form_generator.model_configs import base_model_config
from corvette_form_generator.workbook import workbook_truthy
from corvette_form_generator.workbook_domain.changeset import (
    canonical_json,
    changeset_fingerprint,
    parse_changeset,
)


def _manifest_key_text(key: dict[str, Any]) -> str:
    return canonical_json({str(column): key[column] for column in sorted(key)})


def _manifest_normalized_row(family: str, row: dict[str, Any]) -> dict[str, Any]:
    types = EDITOR_SHEET_META[family].get("types") or {}
    normalized: dict[str, Any] = {}
    for column, raw_value in row.items():
        value = None if raw_value == "" else raw_value
        if value is not None and types.get(column) == "int":
            text = str(value).strip()
            value = int(text) if text.lstrip("-").isdigit() else value
        elif value is not None and types.get(column) == "bool":
            value = workbook_truthy(value)
        normalized[column] = value
    return normalized


def emit_manifest_changeset(
    *,
    workbook_path: Path,
    run_id: str,
    manifest: dict[str, Any],
    compile_report: dict[str, Any],
    selection: dict[str, Any],
    compiler_bindings: dict[str, str],
    authority_artifacts: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """Project an exact-current canonical manifest into a ChangeSet.

    Same validation and projection semantics as ``build_manifest_plan()``;
    only the output assembly differs (immutable ``workbook-changeset-1``
    instead of a two-stage pass-c-3 plan). The returned payload is signed
    and round-tripped through ``parse_changeset()`` before return.
    """

    workbook_path = Path(workbook_path)
    targets = [str(target) for target in selection.get("targets") or []]
    if not targets or len(targets) != len(set(targets)):
        raise ValueError("Canonical changeset needs a nonempty unique target selection.")
    modes = {str(key): str(value) for key, value in (manifest.get("modelModes") or {}).items()}
    report_models = {
        str(key): dict(value or {})
        for key, value in (compile_report.get("models") or {}).items()
    }
    if set(targets) != set(modes) or set(targets) != set(report_models):
        raise ValueError("Canonical changeset target set does not match compiler artifacts.")
    required_authority_artifacts = {
        "exceptionQueue",
        "resolutions",
        "comparatorEvidence",
    }
    if set(authority_artifacts) != required_authority_artifacts:
        raise ValueError(
            "Canonical changeset requires the complete exception queue, resolutions, "
            "and comparator evidence artifact set."
        )
    queue = authority_artifacts["exceptionQueue"]
    resolutions = authority_artifacts["resolutions"]
    comparator_evidence = authority_artifacts["comparatorEvidence"]
    if set(comparator_evidence.get("targets") or {}) != set(targets):
        raise ValueError(
            "Canonical changeset comparator evidence target set does not match selection."
        )
    authority = manifest.get("runAuthorityFingerprint")
    if not authority or any(
        artifact.get("runAuthorityFingerprint") != authority
        for artifact in (compile_report, queue, comparator_evidence)
    ):
        raise ValueError("Canonical changeset authority fingerprints do not agree.")
    queue_fingerprint = str(queue.get("queueSubjectFingerprint") or "")
    if not queue_fingerprint or any(
        str(value or "") != queue_fingerprint
        for value in (
            compile_report.get("queueSubjectFingerprint"),
            resolutions.get("queueSubjectFingerprint"),
        )
    ):
        raise ValueError("Canonical changeset queue and resolution fingerprints do not agree.")
    comparator_semantic_sha = str(
        comparator_evidence.get("comparatorEvidenceSemanticSha") or ""
    )
    if not comparator_semantic_sha or any(
        str(value or "") != comparator_semantic_sha
        for value in (
            compile_report.get("comparatorEvidenceSemanticSha"),
            queue.get("comparatorEvidenceSemanticSha"),
        )
    ):
        raise ValueError("Canonical changeset comparator evidence bindings do not agree.")
    unknown_subject_models = {
        str(subject.get("model") or "")
        for subject in queue.get("subjects") or []
        if str(subject.get("model") or "") not in set(targets)
    }
    if unknown_subject_models:
        raise ValueError(
            "Canonical changeset exception queue contains subjects outside the selected "
            f"targets: {sorted(unknown_subject_models)}"
        )
    current_subjects = {
        (str(subject.get("subjectId") or ""), str(subject.get("subjectVersion") or ""))
        for subject in queue.get("subjects") or []
    }
    orphan_resolutions = [
        entry
        for entry in resolutions.get("validEntries") or []
        if (
            str(entry.get("subjectId") or ""),
            str(entry.get("subjectVersion") or ""),
        )
        not in current_subjects
    ]
    if orphan_resolutions:
        raise ValueError(
            "Canonical changeset resolutions do not map to the exact current exception queue."
        )
    for target in targets:
        model_report = report_models[target]
        if not model_report.get("compileReady") or model_report.get("blockers"):
            raise ValueError(f"Canonical target {target} is not compile-ready.")
        if str(model_report.get("mode") or "") != modes[target]:
            raise ValueError(f"Canonical target {target} mode does not match the manifest.")
    if compile_report.get("deferrals"):
        raise ValueError("Canonical changeset cannot project unresolved compiler deferrals.")

    extract = extract_workbook(workbook_path)
    sheets = extract.get("sheets") or {}
    registry, registered_family = model_sheet_registry(extract)
    registered_family = {**GLOBAL_SHEET_FAMILIES, **registered_family}
    comparators = {
        str(key): str(value)
        for key, value in (selection.get("comparators") or {}).items()
    }
    if set(comparators) != set(targets):
        raise ValueError("Canonical changeset comparator targets do not match the selection.")

    rows = [dict(row) for row in manifest.get("rows") or []]
    if not rows:
        raise ValueError("Canonical manifest has no rows to project.")
    greenfield_targets = {
        model for model, mode in modes.items() if mode == "greenfield"
    }
    isolated_role_by_family = {
        family: role for role, family in MODEL_SHEET_ROLES
    }
    greenfield_sheets = {
        (model, family): str(getattr(base_model_config(model), role))
        for model in greenfield_targets
        for family, role in isolated_role_by_family.items()
    }
    target_option_ids = {
        model: {
            str(row.get("key", {}).get("option_id") or "")
            for row in rows
            if row.get("model") == model and row.get("family") == "options"
        }
        for model in greenfield_targets
    }
    target_interior_ids = {
        model: {
            str(row.get("key", {}).get("interior_id") or "")
            for row in rows
            if row.get("model") == model
            and row.get("family") == "model_interior_scope"
        }
        for model in greenfield_targets
    }
    rule_group_ids_with_applicable_members = {
        model: {
            str(row.get("values", {}).get("group_id") or "")
            for row in rows
            if row.get("model") == model
            and row.get("family") == "rule_group_members"
            and str(row.get("values", {}).get("target_id") or "")
            in target_option_ids[model] | target_interior_ids[model]
        }
        for model in greenfield_targets
    }
    applicable_rule_group_ids = {
        model: {
            str(row.get("values", {}).get("group_id") or "")
            for row in rows
            if row.get("model") == model
            and row.get("family") == "rule_groups"
            and str(row.get("values", {}).get("group_id") or "")
            in rule_group_ids_with_applicable_members[model]
            and str(row.get("values", {}).get("source_id") or "")
            in target_option_ids[model] | target_interior_ids[model]
        }
        for model in greenfield_targets
    }
    applicable_exclusive_member_counts = {
        model: {
            group_id: sum(
                1
                for row in rows
                if row.get("model") == model
                and row.get("family") == "exclusive_members"
                and str(row.get("values", {}).get("group_id") or "") == group_id
                and str(row.get("values", {}).get("option_id") or "")
                in target_option_ids[model]
            )
            for group_id in {
                str(row.get("values", {}).get("group_id") or "")
                for row in rows
                if row.get("model") == model
                and row.get("family") == "exclusive_members"
            }
        }
        for model in greenfield_targets
    }
    applicable_exclusive_group_ids = {
        model: {
            group_id
            for group_id, count in applicable_exclusive_member_counts[model].items()
            if count >= 2
        }
        for model in greenfield_targets
    }

    def greenfield_row_is_applicable(row: dict[str, Any]) -> bool:
        model = str(row.get("model") or "")
        family = str(row.get("family") or "")
        values = row.get("values") or {}
        option_ids = target_option_ids.get(model, set())
        reference_ids = option_ids | target_interior_ids.get(model, set())
        if family == "price_rules":
            return {
                str(values.get("condition_option_id") or ""),
                str(values.get("target_option_id") or ""),
            } <= reference_ids
        if family == "rule_mapping":
            return {
                str(values.get("source_id") or ""),
                str(values.get("target_id") or ""),
            } <= reference_ids
        if family == "rule_group_members":
            return (
                str(values.get("target_id") or "") in reference_ids
                and str(values.get("group_id") or "")
                in applicable_rule_group_ids.get(model, set())
            )
        if family == "exclusive_members":
            return (
                str(values.get("option_id") or "") in option_ids
                and str(values.get("group_id") or "")
                in applicable_exclusive_group_ids.get(model, set())
            )
        if family == "rule_groups":
            return str(values.get("group_id") or "") in applicable_rule_group_ids.get(
                model, set()
            )
        if family == "exclusive_groups":
            return str(values.get("group_id") or "") in applicable_exclusive_group_ids.get(
                model, set()
            )
        return True

    projection_migrations: list[dict[str, Any]] = []
    projection_scope_exclusions: list[dict[str, Any]] = []
    migrated_rows: list[dict[str, Any]] = []
    for index, original in enumerate(rows):
        row = dict(original)
        model = str(row.get("model") or "")
        family = str(row.get("family") or "")
        if model in greenfield_targets and family == "model_workbook_sources":
            values = dict(row.get("values") or {})
            role = str(values.get("source_role") or "")
            source_family = SOURCE_ROLE_FAMILIES.get(role)
            target_sheet = greenfield_sheets.get((model, source_family or ""))
            if target_sheet and str(values.get("sheet_name") or "") != target_sheet:
                previous_sheet = str(values.get("sheet_name") or "")
                values["sheet_name"] = target_sheet
                row["values"] = values
                projection_migrations.append(
                    {
                        "manifestIndex": index,
                        "model": model,
                        "family": family,
                        "sourceRole": role,
                        "fromSheet": previous_sheet,
                        "toSheet": target_sheet,
                        "fromAction": str(row.get("action") or ""),
                        "toAction": str(row.get("action") or ""),
                        "reason": "greenfield_target_sheet_isolation",
                    }
                )
        elif model in greenfield_targets and family in isolated_role_by_family:
            target_sheet = greenfield_sheets[(model, family)]
            previous_sheet = str(row.get("sheet") or "")
            previous_action = str(row.get("action") or "")
            if previous_sheet != target_sheet:
                if not greenfield_row_is_applicable(row):
                    if previous_action != "noop":
                        raise ValueError(
                            "Greenfield target-sheet isolation cannot discard a non-noop "
                            f"{model}/{family} row outside the target reference domain."
                        )
                    row["projectionScopeDisposition"] = (
                        "retained_existing_noop_outside_target_domain"
                    )
                    projection_scope_exclusions.append(
                        {
                            "manifestIndex": index,
                            "model": model,
                            "family": family,
                            "sheet": previous_sheet,
                            "action": previous_action,
                            "key": dict(row.get("key") or {}),
                            "reason": "outside_greenfield_target_reference_domain",
                        }
                    )
                    migrated_rows.append(row)
                    continue
                row["sheet"] = target_sheet
                if target_sheet not in sheets and previous_action in {
                    "noop",
                    "update",
                }:
                    row["action"] = "add"
                projection_migrations.append(
                    {
                        "manifestIndex": index,
                        "model": model,
                        "family": family,
                        "fromSheet": previous_sheet,
                        "toSheet": target_sheet,
                        "fromAction": previous_action,
                        "toAction": str(row.get("action") or ""),
                        "reason": "greenfield_target_sheet_isolation",
                    }
                )
        migrated_rows.append(row)
    rows = migrated_rows
    source_sheet_by_model_family: dict[tuple[str, str], str] = {}
    source_sheet = sheets.get("model_workbook_sources") or {}
    for source_row in source_sheet.get("rows") or []:
        source_family = SOURCE_ROLE_FAMILIES.get(
            str(source_row.get("source_role") or "")
        )
        source_model = str(source_row.get("model_key") or "")
        source_name = str(source_row.get("sheet_name") or "")
        if source_model and source_family and source_name:
            source_sheet_by_model_family[(source_model, source_family)] = source_name
    for manifest_row in rows:
        if manifest_row.get("family") != "model_workbook_sources":
            continue
        source_values = manifest_row.get("values") or {}
        source_model = str(source_values.get("model_key") or "")
        source_family = SOURCE_ROLE_FAMILIES.get(
            str(source_values.get("source_role") or "")
        )
        source_name = str(source_values.get("sheet_name") or "")
        if not (source_model and source_family):
            continue
        if manifest_row.get("action") == "delete":
            source_sheet_by_model_family.pop((source_model, source_family), None)
        elif source_name:
            source_sheet_by_model_family[(source_model, source_family)] = source_name
    seen_keys: set[tuple[str, str]] = set()
    sheet_families: dict[str, str] = {}
    checked_rows: list[dict[str, Any]] = []

    for index, row in enumerate(rows):
        model = str(row.get("model") or "")
        family = str(row.get("family") or "")
        sheet = str(row.get("sheet") or "")
        action = str(row.get("action") or "")
        status = str(row.get("status") or "")
        key = dict(row.get("key") or {})
        values = dict(row.get("values") or {})
        if model not in targets and model != "*":
            raise ValueError(f"Manifest row {index} has unselected model {model!r}.")
        if status != "ready":
            raise ValueError(f"Manifest row {index} is not ready.")
        if family not in EDITOR_SHEET_META:
            raise ValueError(f"Manifest row {index} has unknown family {family!r}.")
        if action not in MANIFEST_ACTION_ORDER:
            raise ValueError(f"Manifest row {index} has unsupported action {action!r}.")
        if not sheet:
            raise ValueError(f"Manifest row {index} has no physical sheet.")
        prior_family = sheet_families.setdefault(sheet, family)
        if prior_family != family:
            raise ValueError(f"Manifest sheet {sheet} maps to multiple families.")
        expected_source_sheet = source_sheet_by_model_family.get((model, family))
        if (
            expected_source_sheet
            and sheet != expected_source_sheet
            and row.get("projectionScopeDisposition")
            != "retained_existing_noop_outside_target_domain"
        ):
            raise ValueError(
                f"Manifest row {index} routes {model!r}/{family!r} to {sheet!r}; "
                f"model_workbook_sources requires {expected_source_sheet!r}."
            )
        key_columns = list(EDITOR_SHEET_META[family]["key"])
        if sorted(key) != sorted(key_columns) or any(
            not str(value or "").strip() for value in key.values()
        ):
            raise ValueError(
                f"Manifest row {index} key must be exactly nonblank {key_columns}."
            )
        physical_key = (sheet, _manifest_key_text(key))
        if physical_key in seen_keys:
            raise ValueError(f"Manifest maps physical key more than once: {physical_key!r}.")
        seen_keys.add(physical_key)
        for column in key_columns:
            if values.get(column) != key[column]:
                raise ValueError(
                    f"Manifest row {index} values do not preserve key column {column}."
                )

        sheet_data = sheets.get(sheet)
        if sheet_data is None:
            if action != "add":
                raise ValueError(
                    f"Manifest row {index} cannot {action} absent sheet {sheet}."
                )
            headers = list(values)
        else:
            headers = list(sheet_data.get("headers") or [])
            if registered_family.get(sheet) not in {None, family}:
                raise ValueError(f"Manifest family disagrees with workbook registry for {sheet}.")
        if set(values) != set(headers):
            raise ValueError(
                f"Manifest row {index} values do not match the exact {sheet} header vector."
            )

        existing = None
        if sheet_data is not None:
            matching = [
                candidate
                for candidate in sheet_data.get("rows") or []
                if all(
                    str(candidate.get(column) or "").strip()
                    == str(key[column] or "").strip()
                    for column in key_columns
                )
            ]
            if len(matching) > 1:
                raise ValueError(f"Workbook key is ambiguous before projection: {physical_key!r}.")
            existing = matching[0] if matching else None
        if action == "add" and existing is not None:
            raise ValueError(f"Manifest add already exists in workbook: {physical_key!r}.")
        if action in {"update", "delete", "noop"} and existing is None:
            raise ValueError(f"Manifest {action} is missing in workbook: {physical_key!r}.")
        if action == "noop" and _manifest_normalized_row(
            family, existing or {}
        ) != _manifest_normalized_row(family, values):
            raise ValueError(f"Manifest noop does not equal workbook state: {physical_key!r}.")
        typed_normalization_columns = [
            column
            for column, kind in EDITOR_SHEET_META[family].get("types", {}).items()
            if existing is not None
            and (
                (
                    kind == "bool"
                    and isinstance(values.get(column), bool)
                    and not isinstance(existing.get(column), bool)
                )
                or (
                    kind == "int"
                    and isinstance(values.get(column), int)
                    and not isinstance(values.get(column), bool)
                    and (
                        not isinstance(existing.get(column), int)
                        or isinstance(existing.get(column), bool)
                    )
                )
            )
        ]
        checked_rows.append(
            {
                **row,
                "model": model,
                "family": family,
                "sheet": sheet,
                "action": action,
                "key": key,
                "values": values,
                "projectionPhysicalAction": (
                    "update"
                    if action == "noop" and typed_normalization_columns
                    else action
                ),
                "typedNormalizationColumns": typed_normalization_columns,
                # Private to the emitter: current workbook row used for exact
                # before values; never serialized into the ChangeSet.
                "_existing": existing,
            }
        )

    missing_sheets = sorted(sheet for sheet in sheet_families if sheet not in sheets)
    creates: list[dict[str, Any]] = []
    for sheet in missing_sheets:
        family = sheet_families[sheet]
        sheet_rows = [row for row in checked_rows if row["sheet"] == sheet]
        expected_headers = set(sheet_rows[0]["values"])
        target = str(sheet_rows[0]["model"])
        comparator = comparators[target]
        candidates = sorted(
            entry["sheet"]
            for entry in registry.get(comparator, [])
            if entry.get("family") == family
            and set((sheets.get(entry["sheet"]) or {}).get("headers") or [])
            == expected_headers
        )
        if len(candidates) != 1:
            raise ValueError(
                f"Missing sheet {sheet} needs one exact comparator header template; found {candidates}."
            )
        creates.append(
            {
                "action": "create_sheet",
                "sheet": sheet,
                "family": family,
                "headersFrom": candidates[0],
            }
        )

    planned_sheets = set(sheets) | {item["sheet"] for item in creates}
    for migration in projection_migrations:
        if migration.get("family") != "model_workbook_sources":
            continue
        target_sheet = str(migration.get("toSheet") or "")
        if not target_sheet or target_sheet in planned_sheets:
            continue
        source_sheet_name = str(migration.get("fromSheet") or "")
        source_role = str(migration.get("sourceRole") or "")
        source_family = SOURCE_ROLE_FAMILIES.get(source_role)
        model = str(migration.get("model") or "")
        key_columns = list(EDITOR_SHEET_META.get(source_family or "", {}).get("key") or [])
        if source_sheet_name not in sheets and source_family:
            comparator = comparators.get(model, "")
            candidates = sorted(
                entry["sheet"]
                for entry in registry.get(comparator, [])
                if entry.get("family") == source_family
                and set(key_columns).issubset(
                    set((sheets.get(entry["sheet"]) or {}).get("headers") or [])
                )
            )
            if len(candidates) == 1:
                source_sheet_name = candidates[0]
        template = sheets.get(source_sheet_name) or {}
        if not source_family or not template.get("headers"):
            raise ValueError(
                f"Greenfield source registration {source_role!r} cannot create "
                f"{target_sheet!r} from {source_sheet_name!r}."
            )
        missing_keys = [
            key
            for key in EDITOR_SHEET_META[source_family]["key"]
            if key not in template["headers"]
        ]
        if missing_keys:
            raise ValueError(
                f"Greenfield source template {source_sheet_name!r} lacks key "
                f"column(s) {missing_keys}."
            )
        creates.append(
            {
                "action": "create_sheet",
                "sheet": target_sheet,
                "family": source_family,
                "headersFrom": source_sheet_name,
            }
        )
        planned_sheets.add(target_sheet)

    for manifest_index, row in enumerate(checked_rows):
        if (
            row.get("family") != "model_workbook_sources"
            or row.get("action") == "delete"
        ):
            continue
        values = row.get("values") or {}
        target_sheet = str(values.get("sheet_name") or "")
        source_role = str(values.get("source_role") or "")
        source_family = SOURCE_ROLE_FAMILIES.get(source_role)
        model = str(values.get("model_key") or row.get("model") or "")
        if (
            not target_sheet
            or not source_family
            or target_sheet in planned_sheets
        ):
            continue
        comparator = comparators.get(model, "")
        key_columns = set(EDITOR_SHEET_META[source_family].get("key") or [])
        candidates = sorted(
            entry["sheet"]
            for entry in registry.get(comparator, [])
            if entry.get("role") == source_role
            and entry.get("family") == source_family
            and key_columns.issubset(
                set((sheets.get(entry["sheet"]) or {}).get("headers") or [])
            )
        )
        if len(candidates) != 1:
            raise ValueError(
                f"Canonical source registration {source_role!r} cannot create "
                f"{target_sheet!r}; expected one exact comparator template, "
                f"found {candidates}."
            )
        creates.append(
            {
                "action": "create_sheet",
                "sheet": target_sheet,
                "family": source_family,
                "headersFrom": candidates[0],
            }
        )
        planned_sheets.add(target_sheet)

    promotion_sheet = sheets.get("model_registry_promotion") or {}
    promotion_headers = list(promotion_sheet.get("headers") or [])
    existing_promotions = {
        str(row.get("model_key") or "")
        for row in promotion_sheet.get("rows") or []
    }
    next_promotion_order = 1 + max(
        [
            int(row.get("display_order") or 0)
            for row in promotion_sheet.get("rows") or []
        ]
        or [0]
    )
    scaffold_changes: list[dict[str, Any]] = []
    for model in sorted(greenfield_targets):
        if model in existing_promotions:
            continue
        config = MODEL_PLAN_CONFIG[model]
        promotion_values: dict[str, Any] = {
            header: None for header in promotion_headers
        }
        promotion_values.update(
            {
                "model_key": model,
                "registry_key": config["registryKey"],
                "promoted_to_runtime": False,
                "default_model": False,
                "artifact_path": (
                    f"form-output/runtime/{config['exportSlug']}-runtime-contract.json"
                ),
                "artifact_type": "runtime_contract",
                "active": False,
                "display_order": next_promotion_order,
                "notes": "Inactive greenfield deployment-proof scaffold.",
            }
        )
        scaffold_changes.append(
            {
                "action": "add",
                "sheet": "model_registry_promotion",
                "family": "model_registry_promotion",
                "key": {"model_key": model},
                "fields": {
                    column: {"before": None, "after": value}
                    for column, value in promotion_values.items()
                    if value is not None
                },
                "provenance": [
                    {
                        "kind": "scaffold",
                        "id": "pass_c3_greenfield_registry_promotion",
                        "scaffoldRule": "pass_c3_greenfield_registry_promotion",
                    }
                ],
            }
        )
        next_promotion_order += 1

    ordered_rows = sorted(
        enumerate(checked_rows),
        key=lambda pair: (
            0 if pair[1]["family"] in MANIFEST_STAGE1_FAMILIES else 1,
            pair[1]["sheet"],
            MANIFEST_ACTION_ORDER[pair[1]["action"]],
            _manifest_key_text(pair[1]["key"]),
            pair[0],
        ),
    )
    sheet_creates = sorted(
        (
            {
                "sheet": item["sheet"],
                "family": item["family"],
                "headersFrom": item["headersFrom"],
            }
            for item in creates
        ),
        key=lambda item: item["sheet"],
    )
    row_changes: list[dict[str, Any]] = []
    noop_receipts: list[dict[str, Any]] = []
    for original_index, row in ordered_rows:
        manifest_ref = f"manifest-{original_index:05d}"
        provenance = [
            {"kind": "manifest", "id": manifest_ref, "manifestRef": manifest_ref}
        ]
        physical_action = str(row.get("projectionPhysicalAction") or row["action"])
        if row["action"] == "noop" and physical_action == "noop":
            noop_receipts.append(
                {
                    "action": "noop",
                    "sheet": row["sheet"],
                    "family": row["family"],
                    "key": row["key"],
                    "noopRef": f"noop-{len(noop_receipts):05d}",
                    "semanticSignature": row.get("semanticSignature"),
                    "derivationVersion": row.get("derivationVersion"),
                    "projectionScopeDisposition": row.get(
                        "projectionScopeDisposition"
                    ),
                    "canonicalValues": dict(row.get("values") or {}),
                    "evidenceDependencies": list(
                        row.get("evidenceDependencies") or []
                    ),
                    "provenance": provenance,
                }
            )
            continue
        existing = row.get("_existing") or {}
        key_columns = set(EDITOR_SHEET_META[row["family"]]["key"])
        if physical_action == "add":
            fields = {
                column: {"before": None, "after": value}
                for column, value in row["values"].items()
                if value is not None
            }
        elif physical_action == "update":
            typed_columns = set(row.get("typedNormalizationColumns") or [])
            delta_columns = [
                column
                for column in row["values"]
                if column not in key_columns
                and (not typed_columns or column in typed_columns)
                and existing.get(column) != row["values"][column]
            ]
            if not delta_columns:
                raise ValueError(
                    f"Manifest row {original_index} update has no field-level delta."
                )
            fields = {
                column: {
                    "before": existing.get(column),
                    "after": row["values"][column],
                }
                for column in delta_columns
            }
        elif physical_action == "delete":
            fields = {
                column: {"before": existing.get(column), "after": None}
                for column in row["values"]
                if existing.get(column) is not None
            }
        else:  # defensive: MANIFEST_ACTION_ORDER validation covers actions
            raise ValueError(
                f"Manifest row {original_index} has unsupported action {physical_action!r}."
            )
        row_changes.append(
            {
                "sortKey": (
                    0 if row["family"] in MANIFEST_STAGE1_FAMILIES else 1,
                    row["sheet"],
                    MANIFEST_ACTION_ORDER[physical_action],
                    _manifest_key_text(row["key"]),
                    original_index,
                ),
                "entry": {
                    "action": physical_action,
                    "sheet": row["sheet"],
                    "family": row["family"],
                    "key": row["key"],
                    "fields": fields,
                    "provenance": provenance,
                },
            }
        )

    for scaffold in scaffold_changes:
        row_changes.append(
            {
                "sortKey": (
                    0,
                    scaffold["sheet"],
                    MANIFEST_ACTION_ORDER["add"],
                    _manifest_key_text(scaffold["key"]),
                    -1,
                ),
                "entry": scaffold,
            }
        )
    row_changes = [item["entry"] for item in sorted(
        row_changes, key=lambda item: item["sortKey"]
    )]

    workbook_fingerprint = {
        "sha256": hashlib.sha256(workbook_path.read_bytes()).hexdigest(),
        "mtimeNs": str(workbook_path.stat().st_mtime_ns),
    }
    bound_hashes = dict(sorted(compiler_bindings.items()))
    payload = {
        "schemaVersion": "workbook-changeset-1",
        "source": {"kind": "ingest", "runId": str(run_id)},
        "targets": sorted(targets),
        "workbook": workbook_fingerprint,
        "sheetCreates": sheet_creates,
        "rowChanges": row_changes,
        "noops": noop_receipts,
        "warningAcknowledgementsRequested": [],
        "bindings": {
            "canonicalManifestSha": bound_hashes.get("canonicalManifestSha"),
            "canonicalManifestSemanticSha": manifest.get("manifestSemanticSha"),
            "runAuthorityFingerprint": manifest.get("runAuthorityFingerprint"),
            "queueSubjectFingerprint": queue_fingerprint,
            "comparatorEvidenceSemanticSha": comparator_semantic_sha,
            "resolutionSemanticSha": manifest.get("resolutionSemanticSha"),
            "compilerBindings": bound_hashes,
        },
    }
    payload["semanticFingerprint"] = changeset_fingerprint(payload)
    payload["changeSetId"] = payload["semanticFingerprint"][:24]
    return parse_changeset(payload)
