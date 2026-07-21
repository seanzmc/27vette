#!/usr/bin/env python3
"""Occurrence-aware target identity and desired-state reconciliation."""

from __future__ import annotations

import re
from collections import defaultdict
from collections.abc import Iterable, Mapping, Sequence
from typing import Any

from corvette_form_generator.ingest.wizard.canonical_rows import canonical_text, normalize_token, semantic_hash

_COPY_RE = re.compile(r"\s+")


def _clean_text(value: Any) -> str:
    return _COPY_RE.sub(" ", str(value or "").strip()).lower()


def _copy_identity(row: Mapping[str, Any]) -> str:
    copy = str(row.get("description") or row.get("option_name") or "").splitlines()[0]
    return re.sub(
        r"[^a-z0-9]+",
        " ",
        _clean_text(copy),
    ).strip()


def _status_vector(row: Mapping[str, Any]) -> list[dict[str, str]]:
    result = []
    for status in row.get("statuses") or row.get("statusVector") or []:
        result.append(
            {
                "modelCode": str(status.get("modelCode") or "").upper(),
                "trim": str(status.get("trim") or "").lower(),
                "bodyStyle": str(status.get("bodyStyle") or "").lower(),
                "status": str(status.get("status") or "").lower(),
            }
        )
    return sorted(result, key=lambda item: (item["modelCode"], item["trim"], item["bodyStyle"], item["status"]))


def _price(row: Mapping[str, Any]) -> Any:
    value = row.get("listPrice") if "listPrice" in row else row.get("price")
    if value in (None, ""):
        return None
    if isinstance(value, bool):
        return str(value).lower()
    try:
        number = float(value)
    except (TypeError, ValueError):
        return _clean_text(value)
    return int(number) if number.is_integer() else number


def option_occurrence_signature(row: Mapping[str, Any]) -> str:
    payload = {
        "rpo": str(row.get("rpo") or row.get("refOnlyRpo") or "").upper(),
        "role": str(row.get("rowKind") or "orderable"),
        "sectionId": str(row.get("section_id") or row.get("sectionId") or ""),
        "copyIdentity": _clean_text(row.get("description") or row.get("option_name")),
        "statusVector": _status_vector(row),
        "priceSignature": _price(row),
        "relationshipRoles": sorted(str(value) for value in (row.get("relationshipRoles") or [])),
    }
    return semantic_hash(payload)


def _stage_two_signature(row: Mapping[str, Any]) -> str:
    return semantic_hash(
        {
            "rpo": str(row.get("rpo") or row.get("refOnlyRpo") or "").upper(),
            "sectionId": str(row.get("section_id") or row.get("sectionId") or ""),
            "statusVector": _status_vector(row),
            "priceSignature": _price(row),
        }
    )


def match_option_occurrences(candidates: Sequence[Mapping[str, Any]], existing_rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    unmatched_existing = {str(row.get("option_id") or ""): dict(row) for row in existing_rows if row.get("option_id")}
    pending = set(range(len(candidates)))
    results: dict[int, dict[str, Any]] = {}
    stages = (
        (
            "full_occurrence_signature",
            lambda candidate, row: option_occurrence_signature(row) == option_occurrence_signature(candidate),
        ),
        (
            "no_rpo_copy_identity",
            lambda candidate, row: (
                not str(candidate.get("rpo") or candidate.get("refOnlyRpo") or "").strip()
                and not str(row.get("rpo") or "").strip()
                and bool(_copy_identity(candidate))
                and _copy_identity(candidate) == _copy_identity(row)
            ),
        ),
        (
            "rpo_section_status_price",
            lambda candidate, row: bool(
                str(candidate.get("rpo") or candidate.get("refOnlyRpo") or "").strip()
            )
            and _stage_two_signature(row) == _stage_two_signature(candidate),
        ),
        (
            "unique_remaining_occurrence",
            lambda candidate, row: bool(
                str(candidate.get("rpo") or candidate.get("refOnlyRpo") or "").strip()
            )
            and str(row.get("rpo") or "").upper()
            == str(candidate.get("rpo") or candidate.get("refOnlyRpo") or "").upper(),
        ),
    )
    for stage, predicate in stages:
        stage_matches = {
            index: sorted(
                option_id
                for option_id, row in unmatched_existing.items()
                if predicate(candidates[index], row)
            )
            for index in sorted(pending)
        }
        claimants: dict[str, list[int]] = defaultdict(list)
        for index, option_ids in stage_matches.items():
            if len(option_ids) == 1:
                claimants[option_ids[0]].append(index)
        for index in sorted(list(pending)):
            option_ids = stage_matches[index]
            if len(option_ids) > 1 or (
                len(option_ids) == 1 and len(claimants[option_ids[0]]) > 1
            ):
                results[index] = {
                    "status": "ambiguous",
                    "candidateIds": option_ids,
                    "matchStage": stage,
                    "candidate": dict(candidates[index]),
                }
                pending.remove(index)
            elif len(option_ids) == 1:
                option_id = option_ids[0]
                results[index] = {
                    "status": "matched",
                    "optionId": option_id,
                    "matchStage": stage,
                    "candidate": dict(candidates[index]),
                }
                unmatched_existing.pop(option_id, None)
                pending.remove(index)
    for index in sorted(pending):
        results[index] = {
            "status": "new",
            "optionId": "",
            "matchStage": "none",
            "candidate": dict(candidates[index]),
        }
    return [results[index] for index in range(len(candidates))]


def _option_id_parts(identifier: str) -> tuple[str, int] | None:
    match = re.fullmatch(r"opt_([a-z0-9_]+)_(\d{3})", identifier)
    return (match.group(1), int(match.group(2))) if match else None


def _next_numeric_option_id(reserved: set[str]) -> str:
    used = {
        int(match.group(1))
        for identifier in reserved
        if (match := re.fullmatch(r"opt_(\d{3})", identifier)) is not None
    }
    for number in range(1, 1000):
        identifier = f"opt_{number:03d}"
        if number not in used and identifier not in reserved:
            return identifier
    raise ValueError("Target-local sequential option IDs are exhausted (opt_001 through opt_999).")


def allocate_ids(family: str, model: str, rows: Sequence[Mapping[str, Any]], *, reserved_ids: Iterable[str] = ()) -> list[dict[str, Any]]:
    if family != "options":
        return [
            {**dict(row), "semanticSignature": semantic_hash(row), "allocatedId": deterministic_family_id(family, model, row)}
            for row in rows
        ]
    reserved_values = [str(value) for value in reserved_ids]
    if len(reserved_values) != len(set(reserved_values)):
        raise ValueError("Target-local option ID collision exists in the reserved identity set.")
    reserved = set(reserved_values)
    by_rpo: dict[str, list[tuple[str, Mapping[str, Any]]]] = defaultdict(list)
    for row in rows:
        raw_rpo = str(row.get("rpo") or row.get("refOnlyRpo") or "").strip()
        rpo = normalize_token(raw_rpo) if raw_rpo else ""
        signature = option_occurrence_signature(row)
        by_rpo[rpo].append((signature, row))
    allocated: list[dict[str, Any]] = []
    for rpo, entries in sorted(by_rpo.items()):
        if not rpo:
            for signature, row in sorted(entries, key=lambda item: item[0]):
                identifier = _next_numeric_option_id(reserved)
                reserved.add(identifier)
                allocated.append(
                    {**dict(row), "semanticSignature": signature, "allocatedId": identifier}
                )
            continue
        used_numbers = {
            parts[1]
            for identifier in reserved
            if (parts := _option_id_parts(identifier)) is not None and parts[0] == rpo
        }
        next_number = 1
        for signature, row in sorted(entries, key=lambda item: item[0]):
            while next_number in used_numbers or f"opt_{rpo}_{next_number:03d}" in reserved:
                next_number += 1
            if next_number > 999:
                raise ValueError(
                    f"Target-local option IDs are exhausted for RPO {rpo} (001 through 999)."
                )
            identifier = f"opt_{rpo}_{next_number:03d}"
            reserved.add(identifier)
            used_numbers.add(next_number)
            allocated.append({**dict(row), "semanticSignature": signature, "allocatedId": identifier})
            next_number += 1
    return allocated


def deterministic_family_id(family: str, model: str, signature: Mapping[str, Any]) -> str:
    model_token = normalize_token(model)
    digest = semantic_hash(signature)[:12]
    if family == "rule_mapping":
        return "_".join(
            [
                model_token,
                "rule",
                normalize_token(signature.get("sourceRpo") or signature.get("source_id")),
                normalize_token(signature.get("ruleType") or signature.get("rule_type")),
                normalize_token(signature.get("targetRpo") or signature.get("target_id")),
                digest,
            ]
        )
    if family == "rule_groups":
        return f"{model_token}_group_{normalize_token(signature.get('sourceRpo') or signature.get('source_id'))}_{normalize_token(signature.get('groupType') or signature.get('group_type'))}_{digest}"
    if family == "exclusive_groups":
        return f"{model_token}_excl_{digest}"
    if family == "price_rules":
        return f"{model_token}_pr_{normalize_token(signature.get('conditionRpo') or signature.get('condition_option_id'))}_{normalize_token(signature.get('targetRpo') or signature.get('target_option_id'))}_{digest}"
    if family == "default_selection_rules":
        return f"{model_token}_default_{normalize_token(signature.get('targetRpo') or signature.get('target_option_id'))}_{digest}"
    return f"{model_token}_{normalize_token(family)}_{digest}"


def _row_key(row: Mapping[str, Any], key_columns: Sequence[str]) -> tuple[str, ...]:
    return tuple(str(row.get(column) if row.get(column) is not None else "") for column in key_columns)


def _comparable(row: Mapping[str, Any]) -> dict[str, Any]:
    return {str(key): value for key, value in row.items() if not str(key).startswith("_")}


def reconcile_rows(
    family: str,
    desired_rows: Sequence[Mapping[str, Any]],
    existing_rows: Sequence[Mapping[str, Any]],
    *,
    key_columns: Sequence[str],
    removals: Iterable[str] = (),
    incoming_references: Mapping[str, Sequence[Mapping[str, Any]]] | None = None,
) -> list[dict[str, Any]]:
    desired_by_key: dict[tuple[str, ...], dict[str, Any]] = {}
    for row in desired_rows:
        key = _row_key(row, key_columns)
        if key in desired_by_key:
            raise ValueError(f"Duplicate desired {family} key: {key}")
        desired_by_key[key] = dict(row)
    existing_by_key: dict[tuple[str, ...], dict[str, Any]] = {}
    for row in existing_rows:
        key = _row_key(row, key_columns)
        if key in existing_by_key:
            raise ValueError(f"Duplicate existing {family} key: {key}")
        existing_by_key[key] = dict(row)
    removal_ids = set(str(value) for value in removals)
    references = incoming_references or {}
    result: list[dict[str, Any]] = []
    for key in sorted(set(desired_by_key) | set(existing_by_key)):
        desired = desired_by_key.get(key)
        existing = existing_by_key.get(key)
        key_dict = dict(zip(key_columns, key))
        if desired is not None and existing is not None:
            action = "noop" if _comparable(desired) == _comparable(existing) else "update"
            result.append({"family": family, "action": action, "key": key_dict, "values": desired, "existing": existing})
            continue
        if desired is not None:
            result.append({"family": family, "action": "add", "key": key_dict, "values": desired, "existing": None})
            continue
        identifier = key[0] if key else ""
        if identifier in removal_ids:
            incoming = list(references.get(identifier) or [])
            if incoming:
                result.append(
                    {
                        "family": family,
                        "action": "blocked",
                        "key": key_dict,
                        "values": existing,
                        "existing": existing,
                        "reasonCode": "surviving_incoming_reference",
                        "incomingReferences": incoming,
                    }
                )
            else:
                result.append({"family": family, "action": "delete", "key": key_dict, "values": existing, "existing": existing})
        else:
            result.append({"family": family, "action": "retained_existing", "key": key_dict, "values": existing, "existing": existing})
    return result
