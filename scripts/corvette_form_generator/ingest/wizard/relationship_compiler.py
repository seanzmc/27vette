#!/usr/bin/env python3
"""Workbook-directed relationship phrase scanning and compilation."""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

from openpyxl import load_workbook

from corvette_form_generator.ingest.source_profiler import RPO_RE
from corvette_form_generator.ingest.wizard.canonical_rows import derivation_version, semantic_hash, subject_id, subject_version
from corvette_form_generator.ingest.wizard.exceptions import exception_subject
from corvette_form_generator.ingest.wizard.identity import option_occurrence_signature
from corvette_form_generator.runtime_metadata import load_rule_phrase_map

RPO_TOKEN_RE = re.compile(r"\(([A-Z0-9]{2,4})\)|\b([A-Z0-9]{3,4})\b")
SNIPPET_CHARS = 180


def _phrase_key(row: Mapping[str, Any]) -> str:
    return str(row.get("phrase") or "").strip().lower()


def load_compiler_phrase_map(workbook_path: Path) -> list[dict[str, Any]]:
    wb = load_workbook(Path(workbook_path), read_only=True, data_only=True)
    try:
        rows = load_rule_phrase_map(wb, fallback_phrases=())
    finally:
        wb.close()
    if not rows:
        raise ValueError("Compiler requires active workbook rule_phrase_map rows; Python fallback is disabled.")
    result = []
    for row in rows:
        phrase_key = _phrase_key(row)
        if not phrase_key or not row.get("rule_type") or not row.get("direction"):
            raise ValueError(f"Incomplete active rule_phrase_map row: {row!r}")
        item = dict(row)
        item["phraseKey"] = phrase_key
        item["semanticFingerprint"] = semantic_hash(
            {
                "phraseKey": phrase_key,
                "ruleType": row.get("rule_type"),
                "direction": row.get("direction"),
                "stopPhrases": list(row.get("stop_phrases") or ()),
            }
        )
        result.append(item)
    return sorted(result, key=lambda item: (-len(item["phraseKey"]), item["phraseKey"]))


def _rpo_tokens(text: str) -> list[str]:
    tokens: list[str] = []
    for match in RPO_TOKEN_RE.finditer(text or ""):
        parenthesized = match.group(1)
        token = (parenthesized or match.group(2) or "").upper()
        if not token or not RPO_RE.fullmatch(token) or token in tokens:
            continue
        if not parenthesized and (token.isdigit() or token.isalpha()):
            continue
        tokens.append(token)
    return tokens


def scan_text(text: str, phrase_rows: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    source = str(text or "")
    lower = source.lower()
    hits: list[dict[str, Any]] = []
    occupied: list[tuple[int, int]] = []
    for row in sorted(phrase_rows, key=lambda item: (-len(_phrase_key(item)), _phrase_key(item))):
        phrase = _phrase_key(row)
        start = 0
        while phrase and (index := lower.find(phrase, start)) >= 0:
            end = index + len(phrase)
            start = end
            if any(index >= taken_start and end <= taken_end for taken_start, taken_end in occupied):
                continue
            segment_end = min(len(source), end + SNIPPET_CHARS)
            after_lower = lower[end:segment_end]
            stops = [after_lower.find(str(stop).lower()) for stop in row.get("stop_phrases") or ()]
            stops = [value for value in stops if value >= 0]
            if stops:
                segment_end = end + min(stops)
            segment = source[end:segment_end]
            hits.append(
                {
                    "phraseKey": phrase,
                    "startOffset": index,
                    "matchedText": source[index:end],
                    "ruleType": str(row.get("rule_type") or "").lower(),
                    "direction": str(row.get("direction") or ""),
                    "rpoTokens": _rpo_tokens(segment),
                    "snippet": source[max(0, index - 30):segment_end].strip(),
                    "phraseEvidenceId": f"phrase:{phrase}",
                    "phraseSemanticFingerprint": str(row.get("semanticFingerprint") or semantic_hash(row)),
                }
            )
            occupied.append((index, end))
    return sorted(hits, key=lambda item: (source.lower().find(item["matchedText"].lower()), item["phraseKey"]))


def _exception(
    candidate: Mapping[str, Any],
    *,
    reason: str,
    family: str,
    dependencies: list[dict[str, str]],
    proposed_rows: Iterable[Mapping[str, Any]] = (),
    evidence_references: Iterable[str] = (),
    identity_values: Iterable[Any] = (),
    allowed_actions: Iterable[str] = ("choose_relationship",),
    question: str,
) -> dict[str, Any]:
    model = str(candidate.get("model") or candidate.get("targetModel") or "unknown")
    references = list(evidence_references)
    proposals = list(proposed_rows)
    identities = [
        option_occurrence_signature(candidate),
        candidate.get("rpo") or candidate.get("refOnlyRpo"),
        reason,
        sorted(references),
        semantic_hash(proposals) if proposals else "",
        sorted(str(value) for value in identity_values),
        sorted(str(dep.get("evidenceId") or "") for dep in dependencies),
    ]
    sid = subject_id(model, reason, identities)
    return exception_subject(
        subject_id_value=sid,
        subject_version_value=subject_version(sid, dependencies),
        model=model,
        family=family,
        severity="blocking",
        reason_code=reason,
        allowed_actions=allowed_actions,
        evidence_dependencies=dependencies,
        evidence_references=references,
        proposed_rows=proposals,
        gate_impact=["compileReady"],
        question=question,
    )


def compile_relationships(
    candidates: Iterable[Mapping[str, Any]],
    phrase_rows: Iterable[Mapping[str, Any]],
    *,
    target_rpos: Iterable[str],
    comparator_facts: Iterable[Mapping[str, Any]] = (),
    active_rule_types: Iterable[str] = ("requires", "includes", "excludes"),
) -> dict[str, list[dict[str, Any]]]:
    target_set = {str(value).upper() for value in target_rpos if str(value)}
    active_types = {str(value).lower() for value in active_rule_types}
    rows: list[dict[str, Any]] = []
    exceptions: list[dict[str, Any]] = []
    dispositions: list[dict[str, Any]] = []
    candidate_list = [dict(candidate) for candidate in candidates]
    explicit_signatures: set[str] = set()
    for candidate in candidate_list:
        stable_candidate_id = option_occurrence_signature(candidate)
        feature_candidate_id = str(candidate.get("_sourceFeatureId") or stable_candidate_id)
        source_rpo = str(candidate.get("rpo") or candidate.get("refOnlyRpo") or "").upper()
        description = str(candidate.get("description") or "")
        candidate_dep = {
            "evidenceId": f"candidate:{stable_candidate_id}",
            "semanticFingerprint": semantic_hash(
                {"optionOccurrenceSignature": stable_candidate_id, "description": description}
            ),
        }
        if candidate.get("rowKind") == "standard_no_rpo":
            dispositions.append({"featureId": f"relationship:{feature_candidate_id}", "disposition": "resolved_not_a_workbook_fact", "evidenceIds": [candidate_dep["evidenceId"]]})
            continue
        hits = scan_text(description, phrase_rows)
        if not hits:
            dispositions.append({"featureId": f"relationship:{feature_candidate_id}", "disposition": "resolved_not_a_workbook_fact", "evidenceIds": [candidate_dep["evidenceId"]]})
            continue
        for hit in hits:
            phrase_dep = {"evidenceId": hit["phraseEvidenceId"], "semanticFingerprint": hit["phraseSemanticFingerprint"]}
            dependencies = [candidate_dep, phrase_dep]
            if not hit["rpoTokens"]:
                feature_id = f"relationship:{feature_candidate_id}:{hit['phraseKey']}:{hit['startOffset']}:missing-endpoint"
                dispositions.append({"featureId": feature_id, "disposition": "resolved_not_a_workbook_fact", "evidenceIds": [value["evidenceId"] for value in dependencies]})
                continue
            for mentioned_rpo in hit["rpoTokens"]:
                feature_id = f"relationship:{feature_candidate_id}:{hit['phraseKey']}:{hit['startOffset']}:{mentioned_rpo}"
                if source_rpo not in target_set or mentioned_rpo not in target_set:
                    exceptions.append(
                        _exception(candidate, reason="unresolved_relationship_endpoint", family="rule_mapping", dependencies=dependencies, evidence_references=[stable_candidate_id, feature_id], identity_values=[mentioned_rpo], allowed_actions=(), question=f"Resolve endpoint {mentioned_rpo} to an active typed target before offering a reviewer action.")
                    )
                    dispositions.append({"featureId": feature_id, "disposition": "blocked_exception", "evidenceIds": [value["evidenceId"] for value in dependencies]})
                    continue
                rule_type = hit["ruleType"]
                if rule_type not in active_types:
                    exceptions.append(
                        _exception(candidate, reason="unsupported_relationship_type", family="rule_mapping", dependencies=dependencies, evidence_references=[stable_candidate_id, feature_id], identity_values=[rule_type, mentioned_rpo], allowed_actions=("choose_relationship", "mark_not_applicable"), question=f"Represent {rule_type} through an active workbook rule type.")
                    )
                    dispositions.append({"featureId": feature_id, "disposition": "blocked_exception", "evidenceIds": [value["evidenceId"] for value in dependencies]})
                    continue
                if hit["direction"] == "mentioned_to_source":
                    relationship_source, relationship_target = mentioned_rpo, source_rpo
                elif hit["direction"] == "source_to_mentioned":
                    relationship_source, relationship_target = source_rpo, mentioned_rpo
                else:
                    exceptions.append(
                        _exception(candidate, reason="unsupported_relationship_direction", family="rule_mapping", dependencies=dependencies, evidence_references=[stable_candidate_id, feature_id], identity_values=[hit["direction"], mentioned_rpo], allowed_actions=("choose_relationship", "mark_not_applicable"), question="Choose the exact relationship direction.")
                    )
                    dispositions.append({"featureId": feature_id, "disposition": "blocked_exception", "evidenceIds": [value["evidenceId"] for value in dependencies]})
                    continue
                semantic_signature = {
                    "sourceRpo": relationship_source,
                    "ruleType": rule_type,
                    "targetRpo": relationship_target,
                    "bodyStyleScope": "*",
                    "trimLevelScope": "*",
                    "variantScope": "*",
                }
                signature_hash = semantic_hash(semantic_signature)
                explicit_signatures.add(signature_hash)
                rows.append(
                    {
                        **semantic_signature,
                        "semanticSignature": signature_hash,
                        "evidenceDependencies": dependencies,
                        "derivationVersion": derivation_version(semantic_signature, dependencies),
                        "sourceFeatureId": feature_id,
                    }
                )
                dispositions.append({"featureId": feature_id, "disposition": "compiled_ready", "evidenceIds": [value["evidenceId"] for value in dependencies]})
    candidates_by_rpo = {
        str(candidate.get("rpo") or candidate.get("refOnlyRpo") or "").upper(): candidate
        for candidate in candidate_list
    }
    grouped_facts: dict[str, list[dict[str, Any]]] = {}
    for raw_fact in comparator_facts:
        fact = dict(raw_fact)
        if fact.get("disposition") != "corroborating_context_only":
            continue
        if fact.get("factType") not in {"direct_rule", "rule_group", "exclusive_group", "price_rule", "default_selection"}:
            continue
        key = semantic_hash({"factType": fact.get("factType"), "signature": fact.get("signature") or {}})
        grouped_facts.setdefault(key, []).append(fact)
    family_by_type = {
        "direct_rule": "rule_mapping",
        "rule_group": "rule_groups",
        "exclusive_group": "exclusive_groups",
        "price_rule": "price_rules",
        "default_selection": "default_selection_rules",
    }
    for fact_key in sorted(grouped_facts):
        facts = grouped_facts[fact_key]
        fact = facts[0]
        fact_type = str(fact["factType"])
        signature = dict(fact.get("signature") or {})
        if fact_type == "direct_rule" and semantic_hash(signature) in explicit_signatures:
            continue
        required_rpos = {
            str(value).upper()
            for value in (
                [signature.get("sourceRpo"), signature.get("targetRpo"), signature.get("conditionRpo")]
                + list(signature.get("memberRpos") or [])
            )
            if str(value or "")
        }
        if not required_rpos or not required_rpos <= target_set:
            continue
        source_rpo = str(
            signature.get("sourceRpo")
            or signature.get("conditionRpo")
            or sorted(required_rpos)[0]
        ).upper()
        candidate = candidates_by_rpo.get(source_rpo)
        if candidate is None:
            continue
        dependencies = [
            {
                "evidenceId": f"candidate:{option_occurrence_signature(candidate)}",
                "semanticFingerprint": semantic_hash(
                    {
                        "optionOccurrenceSignature": option_occurrence_signature(candidate),
                        "description": str(candidate.get("description") or ""),
                    }
                ),
            },
            *[
                {
                    "evidenceId": str(item.get("evidenceId") or f"comparator:{fact_key}"),
                    "semanticFingerprint": str(item.get("semanticFingerprint") or semantic_hash(item)),
                }
                for item in facts
            ],
        ]
        references = [str(item.get("evidenceId") or "") for item in facts]
        exceptions.append(
            _exception(
                candidate,
                reason=(
                    "comparator_only_relationship_proposal"
                    if fact_type == "direct_rule"
                    else f"comparator_only_{fact_type}_proposal"
                ),
                family=family_by_type[fact_type],
                dependencies=dependencies,
                proposed_rows=[signature],
                evidence_references=references,
                identity_values=[fact_type],
                allowed_actions=(
                    ("choose_relationship", "mark_not_applicable")
                    if fact_type == "direct_rule"
                    else ("provide_typed_value", "mark_not_applicable")
                ),
                question="Confirm or reject this comparator-corroborated target relationship.",
            )
        )
        for item in facts:
            dispositions.append(
                {
                    "featureId": str(item.get("evidenceId") or ""),
                    "disposition": "proposed_exception",
                    "evidenceIds": [value["evidenceId"] for value in dependencies],
                }
            )
    return {
        "rows": sorted(rows, key=lambda item: item["semanticSignature"]),
        "exceptions": sorted(exceptions, key=lambda item: item["subjectId"]),
        "dispositions": sorted(dispositions, key=lambda item: item["featureId"]),
    }


def advisory_phrase_rows() -> list[dict[str, Any]]:
    """Compatibility-only hint vocabulary; never used by the production compiler."""
    rows = [
        ("not available with", "excludes", "source_to_mentioned"),
        ("only available with", "requires", "source_to_mentioned"),
        ("requires additional equipment", "requires", "source_to_mentioned"),
        ("requires", "requires", "source_to_mentioned"),
        ("included with", "includes", "mentioned_to_source"),
        ("included in", "includes", "mentioned_to_source"),
        ("included on", "includes", "mentioned_to_source"),
        ("includes", "includes", "source_to_mentioned"),
        ("deletes", "deletes", "source_to_mentioned"),
        ("replaces", "replaces", "source_to_mentioned"),
        ("upgradeable to", "upgradeable_to", "source_to_mentioned"),
    ]
    return [
        {
            "phrase": phrase,
            "phraseKey": phrase,
            "rule_type": rule_type,
            "direction": direction,
            "stop_phrases": (),
            "semanticFingerprint": semantic_hash({"phrase": phrase, "ruleType": rule_type, "direction": direction}),
        }
        for phrase, rule_type, direction in rows
    ]
