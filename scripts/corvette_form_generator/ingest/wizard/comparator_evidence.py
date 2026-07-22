#!/usr/bin/env python3
"""Runtime-equivalent comparator evidence indexed by portable RPO semantics."""

from __future__ import annotations

import hashlib
from collections import Counter, defaultdict
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

from openpyxl import load_workbook

from corvette_form_generator.ingest.wizard.canonical_rows import COMPILER_POLICY_VERSION, semantic_hash
from corvette_form_generator.model_configs import discover_generation_model_configs
from corvette_form_generator.rules import active_source_row, load_exclusive_groups, load_rule_groups
from corvette_form_generator.runtime_metadata import active_rows
from corvette_form_generator.workbook import clean, rows_from_optional_sheet

SCHEMA_VERSION = "comparator-evidence-1"


def _scope(value: Any) -> str:
    return clean(value).lower() or "*"


def _workbook_authority(path: Path) -> dict[str, Any]:
    stat = path.stat()
    return {
        "workbookSha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "workbookMtimeNs": stat.st_mtime_ns,
        "compilerPolicyVersion": COMPILER_POLICY_VERSION,
    }


def _option_occurrences(wb, config) -> tuple[list[dict[str, Any]], dict[str, list[dict[str, Any]]]]:
    occurrences: list[dict[str, Any]] = []
    by_id: dict[str, list[dict[str, Any]]] = defaultdict(list)
    rows = rows_from_optional_sheet(wb, config.source_option_sheet)
    rpo_active_counts = Counter(
        clean(row.get("rpo")).upper()
        for row in rows
        if clean(row.get("rpo")) and active_source_row(row)
    )
    for index, row in enumerate(rows, 2):
        option_id = clean(row.get("option_id"))
        rpo = clean(row.get("rpo")).upper()
        runtime_active = active_source_row(row)
        occurrence = {
            "evidenceId": f"{config.model_key}:option:{option_id or index}",
            "optionId": option_id,
            "rpo": rpo,
            "rowIndex": index,
            "runtimeActive": runtime_active,
            "portable": bool(option_id and rpo and runtime_active and rpo_active_counts[rpo] == 1),
            "disposition": (
                "portable_active"
                if option_id and rpo and runtime_active and rpo_active_counts[rpo] == 1
                else "ambiguous_active_occurrence"
                if runtime_active and rpo and rpo_active_counts[rpo] > 1
                else "inactive_context_only"
                if not runtime_active
                else "context_only_nonportable_entity"
            ),
            "sectionId": clean(row.get("section_id")),
        }
        occurrences.append(occurrence)
        if option_id:
            by_id[option_id].append(occurrence)
    return occurrences, by_id


def _portable_rpo(option_id: str, by_id: Mapping[str, list[dict[str, Any]]]) -> tuple[str, str]:
    matches = by_id.get(clean(option_id), [])
    portable = [item for item in matches if item["portable"]]
    if len(portable) == 1:
        return portable[0]["rpo"], "active_unique"
    if any(item["runtimeActive"] for item in matches):
        return "", "ambiguous_or_nonportable_active"
    return "", "inactive_or_missing"


def _fact(fact_type: str, signature: Mapping[str, Any], evidence: Mapping[str, Any], *, context: Mapping[str, Any] | None = None, endpoint_states: Mapping[str, Any] | None = None) -> dict[str, Any]:
    endpoint_states = dict(endpoint_states or {})
    valid = all(value == "active_unique" for value in endpoint_states.values())
    disposition = "corroborating_context_only" if valid else "context_only_nonportable_entity"
    semantic = {"factType": fact_type, "signature": dict(signature), "endpointStates": endpoint_states}
    portable_evidence = {
        "sheetName": evidence.get("sheetName"),
        "rowId": evidence.get("rowId"),
    }
    if not portable_evidence["rowId"]:
        portable_evidence["signature"] = dict(signature)
    return {
        "evidenceId": f"comparator:{fact_type}:{semantic_hash({'factType': fact_type, 'sourceEvidence': portable_evidence})[:20]}",
        "factType": fact_type,
        "signature": dict(signature),
        "endpointStates": endpoint_states,
        "context": dict(context or {}),
        "sourceEvidence": dict(evidence),
        "disposition": disposition,
        "semanticFingerprint": semantic_hash(semantic),
    }


def _direct_facts(wb, config, by_id) -> list[dict[str, Any]]:
    facts = []
    for index, row in enumerate(rows_from_optional_sheet(wb, config.rule_mapping_sheet), 2):
        if not active_source_row(row):
            continue
        source_rpo, source_state = _portable_rpo(row.get("source_id", ""), by_id)
        target_rpo, target_state = _portable_rpo(row.get("target_id", ""), by_id)
        signature = {
            "sourceRpo": source_rpo,
            "ruleType": clean(row.get("rule_type")).lower(),
            "targetRpo": target_rpo,
            "bodyStyleScope": _scope(row.get("body_style_scope")),
            "trimLevelScope": _scope(row.get("trim_level_scope")),
            "variantScope": _scope(row.get("variant_scope")),
        }
        facts.append(
            _fact(
                "direct_rule",
                signature,
                {"sheetName": config.rule_mapping_sheet, "rowIndex": index, "rowId": clean(row.get("rule_id"))},
                endpoint_states={"source": source_state, "target": target_state},
            )
        )
    return facts


def _group_facts(wb, config, by_id) -> list[dict[str, Any]]:
    facts = []
    for group in load_rule_groups(wb, config):
        source_rpo, source_state = _portable_rpo(group.get("source_id", ""), by_id)
        member_results = [_portable_rpo(value, by_id) for value in group.get("target_ids", [])]
        signature = {
            "sourceRpo": source_rpo,
            "groupType": clean(group.get("group_type")).lower(),
            "memberRpos": sorted(rpo for rpo, _state in member_results if rpo),
            "bodyStyleScope": _scope(group.get("body_style_scope")),
            "trimLevelScope": _scope(group.get("trim_level_scope")),
            "variantScope": _scope(group.get("variant_scope")),
        }
        states = {"source": source_state, **{f"member:{index}": state for index, (_rpo, state) in enumerate(member_results)}}
        if len(signature["memberRpos"]) != len(set(signature["memberRpos"])):
            states["memberUniqueness"] = "duplicate_member"
        facts.append(_fact("rule_group", signature, {"sheetName": config.rule_groups_sheet, "rowId": clean(group.get("group_id"))}, endpoint_states=states))
    return facts


def _exclusive_facts(wb, config, by_id) -> list[dict[str, Any]]:
    facts = []
    for group in load_exclusive_groups(wb, config):
        member_results = [_portable_rpo(value, by_id) for value in group.get("option_ids", [])]
        signature = {
            "selectionMode": clean(group.get("selection_mode")).lower(),
            "memberRpos": sorted(rpo for rpo, _state in member_results if rpo),
        }
        states = {f"member:{index}": state for index, (_rpo, state) in enumerate(member_results)}
        if len(signature["memberRpos"]) != len(set(signature["memberRpos"])):
            states["memberUniqueness"] = "duplicate_member"
        facts.append(_fact("exclusive_group", signature, {"sheetName": config.exclusive_groups_sheet, "rowId": clean(group.get("group_id"))}, endpoint_states=states))
    return facts


def _price_facts(wb, config, by_id) -> list[dict[str, Any]]:
    facts = []
    for index, row in enumerate(rows_from_optional_sheet(wb, config.price_rules_sheet), 2):
        if not active_source_row(row):
            continue
        condition_rpo, condition_state = _portable_rpo(row.get("condition_option_id", ""), by_id)
        target_rpo, target_state = _portable_rpo(row.get("target_option_id", ""), by_id)
        signature = {
            "conditionRpo": condition_rpo,
            "priceRuleType": clean(row.get("price_rule_type")).lower(),
            "targetRpo": target_rpo,
            "bodyStyleScope": _scope(row.get("body_style_scope")),
            "trimLevelScope": _scope(row.get("trim_level_scope")),
            "variantScope": _scope(row.get("variant_scope")),
        }
        facts.append(
            _fact(
                "price_rule",
                signature,
                {"sheetName": config.price_rules_sheet, "rowIndex": index, "rowId": clean(row.get("price_rule_id"))},
                context={"priceValue": clean(row.get("price_value"))},
                endpoint_states={"condition": condition_state, "target": target_state},
            )
        )
    return facts


def _default_facts(wb, config, by_id) -> list[dict[str, Any]]:
    facts = []
    for raw_row in active_rows(wb, "default_selection_rules", config.model_key):
        row = {
            key: clean(value)
            for key, value in raw_row.items()
            if key not in {"active", "model_key"}
        }
        if not row.get("rule_id"):
            continue
        target_rpo, target_state = _portable_rpo(row.get("target_option_id", ""), by_id)
        condition_id = clean(row.get("condition_id"))
        condition_rpo, condition_state = _portable_rpo(condition_id, by_id) if condition_id else ("", "active_unique")
        signature = {
            "targetRpo": target_rpo,
            "conditionType": clean(row.get("condition_type")).lower(),
            "conditionRpo": condition_rpo,
            "bodyStyleScope": _scope(row.get("body_style_scope")),
            "trimLevelScope": _scope(row.get("trim_level_scope")),
            "variantScope": _scope(row.get("variant_scope")),
            "displayBehavior": clean(row.get("display_behavior")),
        }
        facts.append(
            _fact(
                "default_selection",
                signature,
                {"sheetName": "default_selection_rules", "rowId": clean(row.get("rule_id"))},
                context={"priority": clean(row.get("priority"))},
                endpoint_states={"target": target_state, "condition": condition_state},
            )
        )
    return facts


def _semantic_partition(
    target: str,
    comparator: str,
    occurrences: Iterable[Mapping[str, Any]],
    facts: Iterable[Mapping[str, Any]],
) -> dict[str, Any]:
    semantic_occurrences = sorted(
        (
            {
                key: occurrence.get(key)
                for key in (
                    "optionId",
                    "rpo",
                    "runtimeActive",
                    "portable",
                    "disposition",
                    "sectionId",
                )
            }
            for occurrence in occurrences
        ),
        key=semantic_hash,
    )
    semantic_facts = sorted(
        (
            {
                key: fact.get(key)
                for key in (
                    "factType",
                    "signature",
                    "endpointStates",
                    "context",
                    "disposition",
                    "semanticFingerprint",
                )
            }
            for fact in facts
        ),
        key=lambda item: (str(item.get("factType") or ""), str(item.get("semanticFingerprint") or "")),
    )
    return {
        "target": str(target),
        "comparator": str(comparator),
        "optionOccurrences": semantic_occurrences,
        "facts": semantic_facts,
    }


def validate_comparator_artifact(artifact: Mapping[str, Any]) -> None:
    targets = artifact.get("targets") or {}
    for target, entry in targets.items():
        expected = semantic_hash(
            _semantic_partition(
                str(target),
                str(entry.get("comparator") or ""),
                entry.get("optionOccurrences") or [],
                entry.get("facts") or [],
            )
        )
        if entry.get("comparatorEvidenceFingerprint") != expected:
            raise ValueError(f"Comparator partition fingerprint mismatch for {target}.")
    semantic_payload = {
        "schemaVersion": SCHEMA_VERSION,
        "targets": {
            str(target): {
                "target": entry.get("target"),
                "comparator": entry.get("comparator"),
                "comparatorEvidenceFingerprint": entry.get("comparatorEvidenceFingerprint"),
            }
            for target, entry in sorted(targets.items())
        },
    }
    if artifact.get("comparatorEvidenceSemanticSha") != semantic_hash(semantic_payload):
        raise ValueError("Comparator evidence semantic hash mismatch.")


def build_comparator_evidence(
    workbook_path: Path,
    target_comparators: Mapping[str, str],
    *,
    run_authority_fingerprint: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    path = Path(workbook_path)
    configs = discover_generation_model_configs(path)
    unknown = sorted({str(value) for value in target_comparators.values()} - set(configs))
    if unknown:
        raise ValueError(f"Comparator is not generation-discoverable and active: {', '.join(unknown)}")
    wb = load_workbook(path, read_only=True, data_only=True)
    try:
        targets: dict[str, dict[str, Any]] = {}
        for target, comparator in sorted(target_comparators.items()):
            config = configs[str(comparator)]
            occurrences, by_id = _option_occurrences(wb, config)
            facts = (
                _direct_facts(wb, config, by_id)
                + _group_facts(wb, config, by_id)
                + _exclusive_facts(wb, config, by_id)
                + _price_facts(wb, config, by_id)
                + _default_facts(wb, config, by_id)
            )
            facts.sort(key=lambda item: (item["factType"], item["semanticFingerprint"]))
            semantic_partition = _semantic_partition(str(target), str(comparator), occurrences, facts)
            targets[str(target)] = {
                "target": str(target),
                "comparator": str(comparator),
                "optionOccurrences": occurrences,
                "facts": facts,
                "comparatorEvidenceFingerprint": semantic_hash(semantic_partition),
            }
    finally:
        wb.close()
    semantic_payload = {
        "schemaVersion": SCHEMA_VERSION,
        "targets": {
            target: {
                "target": entry["target"],
                "comparator": entry["comparator"],
                "comparatorEvidenceFingerprint": entry["comparatorEvidenceFingerprint"],
            }
            for target, entry in sorted(targets.items())
        },
    }
    return {
        "schemaVersion": SCHEMA_VERSION,
        "runAuthorityFingerprint": dict(run_authority_fingerprint or _workbook_authority(path)),
        "comparatorEvidenceSemanticSha": semantic_hash(semantic_payload),
        "targets": targets,
    }
