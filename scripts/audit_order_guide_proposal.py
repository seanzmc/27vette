#!/usr/bin/env python3
"""Audit generated order-guide proposal artifacts without applying them."""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
WARNING = "This is an audit of generated proposal artifacts only. No canonical rows were applied."

REQUIRED_INPUTS = {
    "proposal_report": "proposal_report.json",
    "selectables": "catalog/selectables.csv",
    "selectable_display": "ui/selectable_display.csv",
    "availability": "ui/availability.csv",
    "raw_price_evidence": "pricing/raw_price_evidence.csv",
    "source_refs": "meta/source_refs.csv",
    "review_queue": "review_queue.csv",
}
OPTIONAL_INPUTS = {"rpo_overlap_evidence": "meta/rpo_role_overlap_evidence.csv"}

REVIEW_BUCKETS = {
    "standard_equipment_without_rpo": "missing_rpo_standard_equipment",
    "ref_only_only_evidence": "ref_only_evidence",
    "duplicate_or_conflicting_primary_matrix_evidence": "duplicate_or_conflicting_evidence",
    "missing_model_key": "missing_model_or_variant_context",
    "missing_variant_id": "missing_model_or_variant_context",
    "unsupported_status": "unsupported_status",
    "accepted_rpo_overlap_kept_separate": "expected_review_only",
    "excluded_color_trim_source": "boundary_exclusion_summary",
    "excluded_equipment_group_source": "boundary_exclusion_summary",
    "ambiguous_price_evidence": "price_evidence_review",
    "blank_rpo_non_standard_equipment": "missing_rpo_non_standard_equipment",
    "orderable_and_ref_same_row_review": "orderable_ref_same_row_review",
    "canonical_ready_false_but_narrow_scope_allowed": "expected_review_only",
}
BLOCKING_BUCKETS = {
    "duplicate_or_conflicting_evidence",
    "missing_model_or_variant_context",
    "unsupported_status",
    "missing_rpo_non_standard_equipment",
    "orderable_ref_same_row_review",
    "unclassified_review_item",
}
EXPECTED_BUCKETS = {
    "expected_review_only",
    "missing_rpo_standard_equipment",
    "ref_only_evidence",
    "boundary_exclusion_summary",
    "price_evidence_review",
}

SOURCE_REF_INTEGRITY_HEADERS = ["check_name", "status", "count", "sample_ids", "notes"]
REVIEW_QUEUE_SUMMARY_HEADERS = ["review_bucket", "original_reason", "count", "severity", "recommended_action", "notes"]
SELECTABLE_COUNTS_HEADERS = ["model_key", "section_family", "proposal_scope", "review_status", "count"]
AVAILABILITY_COUNTS_HEADERS = ["model_key", "variant_id", "body_style", "trim_level", "canonical_status", "availability_value", "raw_status", "count"]
SUSPICIOUS_HEADERS = [
    "suspicion_type",
    "source_file",
    "source_row",
    "model_key",
    "section_family",
    "proposal_selectable_id",
    "rpo",
    "raw_value",
    "reason",
    "recommended_action",
    "notes",
]
RPO_TRACE_HEADERS = [
    "rpo",
    "traceability_status",
    "orderable_count",
    "ref_only_count",
    "has_source_refs",
    "source_ref_ids",
    "source_sheets",
    "model_keys",
    "section_families",
    "notes",
]


def clean(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--proposal", required=True, help="Generated proposal directory to audit.")
    parser.add_argument("--out", required=True, help="Directory where proposal audit outputs should be written.")
    return parser.parse_args()


def is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False


def validate_output_dir(out_dir: Path) -> None:
    resolved = out_dir.resolve()
    forbidden_dirs = [ROOT / "data", ROOT / "data" / "stingray", ROOT / "form-output", ROOT / "form-app"]
    for forbidden in forbidden_dirs:
        forbidden_resolved = forbidden.resolve()
        if resolved == forbidden_resolved or is_relative_to(resolved, forbidden_resolved):
            raise SystemExit(f"Refusing to write proposal audit output under canonical or production directory: {resolved}")


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        try:
            return [dict(row) for row in csv.DictReader(handle)]
        except csv.Error as exc:
            raise SystemExit(f"Malformed CSV input {path}: {exc}") from exc


def write_csv(path: Path, headers: list[str], rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=headers, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({header: clean(row.get(header, "")) for header in headers})


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def load_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Malformed JSON input {path}: {exc}") from exc


def load_inputs(proposal_dir: Path) -> tuple[dict[str, list[dict[str, str]]], dict[str, Any], dict[str, bool]]:
    if not proposal_dir.exists() or not proposal_dir.is_dir():
        raise SystemExit(f"Proposal directory does not exist: {proposal_dir}")
    missing = [filename for filename in REQUIRED_INPUTS.values() if not (proposal_dir / filename).exists()]
    if missing:
        raise SystemExit(f"Missing required proposal input: {', '.join(sorted(missing))}")
    proposal_report = load_json(proposal_dir / REQUIRED_INPUTS["proposal_report"])
    rows: dict[str, list[dict[str, str]]] = {}
    for key, filename in REQUIRED_INPUTS.items():
        if key == "proposal_report":
            continue
        rows[key] = read_csv(proposal_dir / filename)
    optional_presence: dict[str, bool] = {}
    for key, filename in OPTIONAL_INPUTS.items():
        path = proposal_dir / filename
        optional_presence[key] = path.exists()
        rows[key] = read_csv(path) if path.exists() else []
    return rows, proposal_report, optional_presence


def pipe_values(value: str) -> list[str]:
    return [item for item in clean(value).split("|") if item]


def counter_dict(counter: Counter[Any]) -> dict[str, int]:
    return {str(key): value for key, value in sorted(counter.items(), key=lambda item: str(item[0]))}


def review_bucket(reason: str) -> str:
    return REVIEW_BUCKETS.get(clean(reason), "unclassified_review_item")


def review_queue_summary(review_rows: list[dict[str, str]]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    grouped: dict[tuple[str, str, str, str], dict[str, Any]] = {}
    by_reason: Counter[str] = Counter()
    by_bucket: Counter[str] = Counter()
    by_severity: Counter[str] = Counter()
    by_model: Counter[str] = Counter()
    by_selectable: Counter[str] = Counter()
    for row in review_rows:
        reason = clean(row.get("reason", ""))
        bucket = review_bucket(reason)
        severity = clean(row.get("severity", "")) or "<blank>"
        action = clean(row.get("recommended_action", ""))
        key = (bucket, reason, severity, action)
        grouped.setdefault(
            key,
            {
                "review_bucket": bucket,
                "original_reason": reason,
                "count": 0,
                "severity": severity,
                "recommended_action": action,
                "notes": bucket_notes(bucket),
            },
        )["count"] += 1
        by_reason[reason or "<blank>"] += 1
        by_bucket[bucket] += 1
        by_severity[severity] += 1
        by_model[clean(row.get("model_key", "")) or "<blank>"] += 1
        by_selectable[clean(row.get("proposal_selectable_id", "")) or "<blank>"] += 1
    rows_out = sorted(grouped.values(), key=lambda row: (row["review_bucket"], row["original_reason"], row["severity"], row["recommended_action"]))
    return rows_out, {
        "counts_by_original_reason": counter_dict(by_reason),
        "counts_by_review_bucket": counter_dict(by_bucket),
        "counts_by_severity": counter_dict(by_severity),
        "counts_by_model_key": counter_dict(by_model),
        "counts_by_proposal_selectable_id": counter_dict(by_selectable),
        "blocking_review_bucket_count": sum(count for bucket, count in by_bucket.items() if bucket in BLOCKING_BUCKETS),
        "expected_review_bucket_count": sum(count for bucket, count in by_bucket.items() if bucket in EXPECTED_BUCKETS),
    }


def bucket_notes(bucket: str) -> str:
    if bucket in EXPECTED_BUCKETS:
        return "Expected review-only or boundary evidence; advisory unless it blocks a narrower scope."
    if bucket in BLOCKING_BUCKETS:
        return "Likely blocker for future narrowing until reviewed or excluded."
    return "Unclassified review item; inspect before future narrowing."


def selectable_counts(selectables: list[dict[str, str]]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    counts: Counter[tuple[str, str, str, str]] = Counter()
    ids: Counter[str] = Counter()
    by_scope: Counter[str] = Counter()
    by_status: Counter[str] = Counter()
    by_model: Counter[str] = Counter()
    by_section: Counter[str] = Counter()
    no_rpo_standard = 0
    ref_only = 0
    confident = 0
    review_only = 0
    for row in selectables:
        key = (
            clean(row.get("model_key", "")) or "<blank>",
            clean(row.get("section_family", "")) or "<blank>",
            clean(row.get("proposal_scope", "")) or "<blank>",
            clean(row.get("review_status", "")) or "<blank>",
        )
        counts[key] += 1
        ids[clean(row.get("proposal_selectable_id", ""))] += 1
        by_scope[key[2]] += 1
        by_status[key[3]] += 1
        by_model[key[0]] += 1
        by_section[key[1]] += 1
        if clean(row.get("proposal_scope", "")) == "standard_equipment_review_only":
            no_rpo_standard += 1
        if clean(row.get("has_orderable_rpo", "")) != "true" and clean(row.get("has_ref_rpo", "")) == "true":
            ref_only += 1
        if clean(row.get("review_status", "")) == "proposal_only":
            confident += 1
        else:
            review_only += 1
    rows_out = [
        {"model_key": model, "section_family": section, "proposal_scope": scope, "review_status": status, "count": count}
        for (model, section, scope, status), count in sorted(counts.items())
    ]
    duplicate_ids = [item for item, count in ids.items() if item and count > 1]
    return rows_out, {
        "total_selectables": len(selectables),
        "confident_count": confident,
        "review_only_count": review_only,
        "counts_by_proposal_scope": counter_dict(by_scope),
        "counts_by_review_status": counter_dict(by_status),
        "counts_by_model_key": counter_dict(by_model),
        "counts_by_section_family": counter_dict(by_section),
        "no_rpo_standard_equipment_review_only_count": no_rpo_standard,
        "ref_only_only_proposal_count": ref_only,
        "duplicate_proposal_id_count": len(duplicate_ids),
        "duplicate_proposal_ids": sorted(duplicate_ids),
    }


def availability_counts(rows: list[dict[str, str]]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    counts: Counter[tuple[str, str, str, str, str, str, str]] = Counter()
    by_canonical: Counter[str] = Counter()
    by_value: Counter[str] = Counter()
    by_raw_symbol: Counter[str] = Counter()
    by_variant: Counter[str] = Counter()
    missing_source_ref = 0
    needs_review = 0
    for row in rows:
        key = (
            clean(row.get("model_key", "")) or "<blank>",
            clean(row.get("variant_id", "")) or "<blank>",
            clean(row.get("body_style", "")) or "<blank>",
            clean(row.get("trim_level", "")) or "<blank>",
            clean(row.get("canonical_status", "")) or "<blank>",
            clean(row.get("availability_value", "")) or "<blank>",
            clean(row.get("raw_status", "")) or "<blank>",
        )
        counts[key] += 1
        by_canonical[key[4]] += 1
        by_value[key[5]] += 1
        by_raw_symbol[f"{clean(row.get('raw_status', ''))}/{clean(row.get('status_symbol', ''))}"] += 1
        by_variant[key[1]] += 1
        if not clean(row.get("source_ref_id", "")):
            missing_source_ref += 1
        if key[5] in {"needs_review", "review_only"}:
            needs_review += 1
    rows_out = [
        {
            "model_key": model,
            "variant_id": variant,
            "body_style": body_style,
            "trim_level": trim,
            "canonical_status": canonical,
            "availability_value": value,
            "raw_status": raw,
            "count": count,
        }
        for (model, variant, body_style, trim, canonical, value, raw), count in sorted(counts.items())
    ]
    return rows_out, {
        "total_availability_rows": len(rows),
        "counts_by_canonical_status": counter_dict(by_canonical),
        "counts_by_availability_value": counter_dict(by_value),
        "counts_by_raw_status_symbol": counter_dict(by_raw_symbol),
        "counts_by_variant_id": counter_dict(by_variant),
        "rows_missing_source_ref_id": missing_source_ref,
        "rows_with_unsupported_or_needs_review_availability": needs_review,
    }


def price_quality(rows: list[dict[str, str]]) -> dict[str, Any]:
    by_model: Counter[str] = Counter()
    by_confidence: Counter[str] = Counter()
    by_status: Counter[str] = Counter()
    unresolved = 0
    for row in rows:
        by_model[clean(row.get("model_key", "")) or "<blank>"] += 1
        confidence = clean(row.get("model_key_confidence", "")) or "<blank>"
        by_confidence[confidence] += 1
        status = clean(row.get("review_status", "")) or "<blank>"
        by_status[status] += 1
        if confidence == "needs_review" or status == "needs_review":
            unresolved += 1
    return {
        "raw_price_evidence_count": len(rows),
        "counts_by_model_key": counter_dict(by_model),
        "counts_by_model_key_confidence": counter_dict(by_confidence),
        "review_status_counts": counter_dict(by_status),
        "unresolved_or_needs_review_price_evidence_count": unresolved,
    }


def collect_referenced_source_ids(selectables: list[dict[str, str]], availability: list[dict[str, str]], prices: list[dict[str, str]]) -> tuple[set[str], list[dict[str, str]]]:
    refs: set[str] = set()
    missing_rows: list[dict[str, str]] = []
    for row in selectables:
        ids = pipe_values(row.get("source_ref_ids", ""))
        if ids:
            refs.update(ids)
        else:
            missing_rows.append({"source_file": "catalog/selectables.csv", **row})
    for row in availability:
        source_ref = clean(row.get("source_ref_id", ""))
        if source_ref:
            refs.add(source_ref)
        else:
            missing_rows.append({"source_file": "ui/availability.csv", **row})
    for row in prices:
        source_ref = clean(row.get("source_ref_id", ""))
        if source_ref:
            refs.add(source_ref)
        else:
            missing_rows.append({"source_file": "pricing/raw_price_evidence.csv", **row})
    return refs, missing_rows


def source_ref_integrity(
    selectables: list[dict[str, str]],
    availability: list[dict[str, str]],
    prices: list[dict[str, str]],
    source_refs: list[dict[str, str]],
) -> tuple[list[dict[str, Any]], dict[str, Any], list[dict[str, Any]]]:
    source_ref_ids = {clean(row.get("source_ref_id", "")) for row in source_refs if clean(row.get("source_ref_id", ""))}
    referenced_ids, missing_ref_rows = collect_referenced_source_ids(selectables, availability, prices)
    unresolved = sorted(referenced_ids - source_ref_ids)
    unused = sorted(source_ref_ids - referenced_ids)
    missing_traceability = []
    for row in source_refs:
        source_file = clean(row.get("source_file", ""))
        requires_row_number = source_file != "staging_audit_rpo_role_overlaps.csv"
        if (
            not clean(row.get("source_sheet", ""))
            or (requires_row_number and not clean(row.get("source_row", "")))
            or not (clean(row.get("raw_value", "")) or clean(row.get("source_detail_raw", "")))
        ):
            missing_traceability.append(row)
    checks = [
        integrity_row("unresolved_referenced_source_refs", not unresolved, len(unresolved), unresolved, "Every referenced source_ref_id should exist in meta/source_refs.csv."),
        integrity_row("unused_source_refs", True, len(unused), unused, "Unused source refs are advisory; they may support review-only evidence."),
        integrity_row("proposal_rows_missing_source_refs", not missing_ref_rows, len(missing_ref_rows), [sample_proposal_id(row) for row in missing_ref_rows], "Proposal rows should carry source_ref_id/source_ref_ids."),
        integrity_row("source_refs_missing_traceability", not missing_traceability, len(missing_traceability), [clean(row.get("source_ref_id", "")) for row in missing_traceability], "Source refs should include source_sheet, source_row, and raw_value or source_detail_raw."),
    ]
    suspicious = []
    for ref_id in unresolved[:10]:
        suspicious.append(suspicious_row("unresolved_source_ref", "", "", "", "", "", "", ref_id, "source_ref_id_not_found", "Fix or regenerate proposal source refs.", "Referenced source_ref_id is absent from meta/source_refs.csv."))
    for row in missing_ref_rows[:10]:
        suspicious.append(suspicious_row("missing_source_ref", row.get("source_file", ""), row.get("source_row", ""), row.get("model_key", ""), row.get("section_family", ""), row.get("proposal_selectable_id", ""), clean(row.get("orderable_rpo", "")) or clean(row.get("ref_rpo", "")), sample_raw(row), "proposal_row_missing_source_ref", "Regenerate or review proposal row traceability.", "Proposal row lacks source_ref_id/source_ref_ids."))
    for row in missing_traceability[:10]:
        suspicious.append(suspicious_row("source_ref_missing_traceability", "meta/source_refs.csv", row.get("source_row", ""), "", "", "", row.get("orderable_rpo", "") or row.get("ref_rpo", ""), row.get("source_ref_id", ""), "source_ref_missing_traceability", "Inspect source_ref row.", "Source ref is missing source_sheet, source_row, raw_value, or source_detail_raw."))
    summary = {
        "total_source_refs": len(source_refs),
        "unresolved_source_ref_count": len(unresolved),
        "unused_source_ref_count": len(unused),
        "proposal_rows_missing_source_ref_count": len(missing_ref_rows),
        "source_refs_missing_traceability_count": len(missing_traceability),
        "source_ref_integrity_ready": not unresolved and not missing_ref_rows and not missing_traceability,
    }
    return checks, summary, suspicious


def integrity_row(check_name: str, passed: bool, count: int, samples: list[str], notes: str) -> dict[str, Any]:
    return {
        "check_name": check_name,
        "status": "pass" if passed else "fail",
        "count": count,
        "sample_ids": "|".join(sorted(clean(sample) for sample in samples if clean(sample))[:10]),
        "notes": notes,
    }


def sample_proposal_id(row: dict[str, str]) -> str:
    return clean(row.get("proposal_selectable_id", "")) or clean(row.get("source_ref_id", "")) or sample_raw(row)


def sample_raw(row: dict[str, str]) -> str:
    return clean(row.get("raw_value", "")) or clean(row.get("display_label", "")) or clean(row.get("proposal_label", "")) or clean(row.get("raw_values", ""))


def suspicious_row(
    suspicion_type: str,
    source_file: str,
    source_row: str,
    model_key: str,
    section_family: str,
    proposal_selectable_id: str,
    rpo: str,
    raw_value: str,
    reason: str,
    recommended_action: str,
    notes: str,
) -> dict[str, Any]:
    return {
        "suspicion_type": suspicion_type,
        "source_file": source_file,
        "source_row": source_row,
        "model_key": model_key,
        "section_family": section_family,
        "proposal_selectable_id": proposal_selectable_id,
        "rpo": rpo,
        "raw_value": raw_value,
        "reason": reason,
        "recommended_action": recommended_action,
        "notes": notes,
    }


def duplicate_and_conflict_suspicious(selectables: list[dict[str, str]]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    suspicious: list[dict[str, Any]] = []
    id_counts = Counter(clean(row.get("proposal_selectable_id", "")) for row in selectables)
    for proposal_id, count in sorted(id_counts.items()):
        if proposal_id and count > 1:
            suspicious.append(suspicious_row("duplicate_proposal_id", "catalog/selectables.csv", "", "", "", proposal_id, "", proposal_id, "duplicate_proposal_id", "Review proposal ID generation.", f"{count} rows share this proposal ID."))
    grouped: dict[tuple[str, str, str, str], set[str]] = defaultdict(set)
    examples: dict[tuple[str, str, str, str], dict[str, str]] = {}
    for row in selectables:
        key = (
            clean(row.get("model_key", "")),
            clean(row.get("section_family", "")),
            clean(row.get("orderable_rpo", "")),
            clean(row.get("ref_rpo", "")),
        )
        grouped[key].add(clean(row.get("proposal_label", "")) or clean(row.get("description", "")))
        examples.setdefault(key, row)
    for key, labels in sorted(grouped.items()):
        if (key[2] or key[3]) and len(labels) > 1:
            row = examples[key]
            suspicious.append(suspicious_row("conflicting_labels_for_same_rpo_scope", "catalog/selectables.csv", "", key[0], key[1], row.get("proposal_selectable_id", ""), key[2] or key[3], " | ".join(sorted(labels)), "conflicting_labels_descriptions", "Review before future narrowing.", "Same RPO/model/section has multiple labels/descriptions."))
    return suspicious, {
        "duplicate_proposal_id_count": sum(1 for count in id_counts.values() if count > 1),
        "conflicting_label_group_count": sum(1 for labels in grouped.values() if len(labels) > 1),
    }


def rpo_overlap_traceability(rows: list[dict[str, str]], source_refs: list[dict[str, str]], present: bool) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    if not present:
        return [], {
            "optional_input_present": False,
            "total_overlap_evidence_rows": 0,
            "rows_with_source_evidence": 0,
            "rows_missing_row_level_source_refs": 0,
            "traceability_level": "absent",
            "rpo_overlap_traceability_ready": False,
            "notes": "Optional RPO overlap evidence file is absent.",
        }
    refs_by_rpo: dict[str, list[str]] = defaultdict(list)
    row_level_refs_by_rpo: dict[str, list[str]] = defaultdict(list)
    for row in source_refs:
        if clean(row.get("source_file", "")) == "staging_audit_rpo_role_overlaps.csv":
            rpo = clean(row.get("raw_value", ""))
            if rpo:
                ref_id = clean(row.get("source_ref_id", ""))
                refs_by_rpo[rpo].append(ref_id)
                if clean(row.get("source_row", "")):
                    row_level_refs_by_rpo[rpo].append(ref_id)
    out_rows = []
    summary_level_only = 0
    with_source_evidence = 0
    for row in rows:
        rpo = clean(row.get("rpo", ""))
        ref_ids = sorted(ref for ref in refs_by_rpo.get(rpo, []) if ref)
        has_source_fields = bool(clean(row.get("source_sheets", "")) or clean(row.get("sample_descriptions", "")))
        if has_source_fields:
            with_source_evidence += 1
        status = "row_level_source_refs" if row_level_refs_by_rpo.get(rpo) else "summary_level_only"
        if status == "summary_level_only":
            summary_level_only += 1
        out_rows.append(
            {
                "rpo": rpo,
                "traceability_status": status,
                "orderable_count": row.get("orderable_count", ""),
                "ref_only_count": row.get("ref_only_count", ""),
                "has_source_refs": "true" if ref_ids else "false",
                "source_ref_ids": "|".join(ref_ids),
                "source_sheets": row.get("source_sheets", ""),
                "model_keys": row.get("model_keys", ""),
                "section_families": row.get("section_families", ""),
                "notes": "Summary-level accepted overlap evidence; do not merge orderable/ref-only meanings." if not ref_ids else "Row-level source_ref_id exists for this overlap evidence.",
            }
        )
    return sorted(out_rows, key=lambda row: row["rpo"]), {
        "optional_input_present": True,
        "total_overlap_evidence_rows": len(rows),
        "rows_with_source_evidence": with_source_evidence,
        "rows_missing_row_level_source_refs": summary_level_only,
        "traceability_level": "summary_level_only" if summary_level_only else "row_level",
        "rpo_overlap_traceability_ready": len(rows) > 0,
        "notes": "Summary-level RPO overlap evidence is advisory and acceptable for this audit pass.",
    }


def readiness(
    selectable_quality: dict[str, Any],
    availability_quality: dict[str, Any],
    price_quality_summary: dict[str, Any],
    review_summary: dict[str, Any],
    source_ref_summary: dict[str, Any],
    overlap_summary: dict[str, Any],
) -> dict[str, Any]:
    reasons = []
    selectables_ready = selectable_quality["duplicate_proposal_id_count"] == 0
    if not selectables_ready:
        reasons.append("duplicate_proposal_ids_present")
    availability_ready = availability_quality["rows_missing_source_ref_id"] == 0
    if availability_quality["rows_missing_source_ref_id"]:
        reasons.append("availability_rows_missing_source_ref")
    price_ready = price_quality_summary["raw_price_evidence_count"] > 0
    if not price_ready:
        reasons.append("raw_price_evidence_missing")
    review_ready = review_summary["blocking_review_bucket_count"] == 0
    if not review_ready:
        reasons.append("blocking_review_buckets_present")
    source_refs_ready = source_ref_summary["source_ref_integrity_ready"]
    if not source_refs_ready:
        reasons.append("source_ref_integrity_failures")
    overlap_ready = overlap_summary["rpo_overlap_traceability_ready"]
    if not overlap_ready:
        reasons.append("rpo_overlap_traceability_absent_or_incomplete")
    return {
        "selectables_ready": selectables_ready,
        "availability_ready": availability_ready,
        "price_evidence_ready": price_ready,
        "review_queue_ready": review_ready,
        "source_refs_ready": source_refs_ready,
        "rpo_overlap_traceability_ready": overlap_ready,
        "canonical_apply_ready": False,
        "reasons": sorted(set(reasons)),
        "notes": [
            "canonical_apply_ready is always false in Pass 12.",
            "review_queue_ready is advisory and false only when likely-blocking buckets are present.",
        ],
    }


def markdown_table(rows: list[dict[str, Any]], headers: list[str]) -> str:
    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join("---" for _ in headers) + " |"]
    for row in rows:
        lines.append("| " + " | ".join(clean(row.get(header, "")).replace("|", "\\|").replace("\n", " ") for header in headers) + " |")
    return "\n".join(lines)


def markdown_report(report: dict[str, Any], queue_rows: list[dict[str, Any]], integrity_rows: list[dict[str, Any]]) -> str:
    readiness_rows = [{"field": key, "value": value} for key, value in report["readiness"].items() if key != "notes"]
    queue_preview = queue_rows[:12]
    integrity_preview = integrity_rows[:8]
    return f"""# Proposal Audit Report

{WARNING}

## Input Summary

- required inputs present: `{json.dumps(report["input_summary"]["required_input_presence"], sort_keys=True)}`
- optional inputs present: `{json.dumps(report["input_summary"]["optional_input_presence"], sort_keys=True)}`

## Readiness

{markdown_table(readiness_rows, ["field", "value"])}

## Review Queue Buckets

{markdown_table(queue_preview, ["review_bucket", "original_reason", "count", "severity", "recommended_action"])}

## Selectables Quality

- total selectables: `{report["selectables_quality"]["total_selectables"]}`
- confident count: `{report["selectables_quality"]["confident_count"]}`
- review-only count: `{report["selectables_quality"]["review_only_count"]}`
- no-RPO standard-equipment review-only count: `{report["selectables_quality"]["no_rpo_standard_equipment_review_only_count"]}`
- ref-only-only proposal count: `{report["selectables_quality"]["ref_only_only_proposal_count"]}`

## Availability Quality

- total availability rows: `{report["availability_quality"]["total_availability_rows"]}`
- rows missing source_ref_id: `{report["availability_quality"]["rows_missing_source_ref_id"]}`
- availability values: `{json.dumps(report["availability_quality"]["counts_by_availability_value"], sort_keys=True)}`

## Source-Ref Integrity

{markdown_table(integrity_preview, ["check_name", "status", "count", "sample_ids"])}

## RPO Overlap Traceability

- optional input present: `{report["rpo_overlap_traceability"]["optional_input_present"]}`
- total overlap evidence rows: `{report["rpo_overlap_traceability"]["total_overlap_evidence_rows"]}`
- traceability level: `{report["rpo_overlap_traceability"]["traceability_level"]}`

## Recommended Next Step

{report["recommended_next_step"]}

No canonical rows were applied.
"""


def build_audit(proposal_dir: Path) -> tuple[dict[str, Any], dict[str, list[dict[str, Any]]]]:
    rows, proposal_report, optional_presence = load_inputs(proposal_dir)
    queue_rows, queue_summary = review_queue_summary(rows["review_queue"])
    selectable_count_rows, selectable_quality = selectable_counts(rows["selectables"])
    availability_count_rows, availability_quality = availability_counts(rows["availability"])
    price_quality_summary = price_quality(rows["raw_price_evidence"])
    integrity_rows, source_ref_summary, integrity_suspicious = source_ref_integrity(
        rows["selectables"], rows["availability"], rows["raw_price_evidence"], rows["source_refs"]
    )
    duplicate_suspicious, duplicate_summary = duplicate_and_conflict_suspicious(rows["selectables"])
    overlap_rows, overlap_summary = rpo_overlap_traceability(
        rows["rpo_overlap_evidence"], rows["source_refs"], optional_presence["rpo_overlap_evidence"]
    )
    suspicious_rows = sorted(
        [*integrity_suspicious, *duplicate_suspicious],
        key=lambda row: (row["suspicion_type"], row["source_file"], row["source_row"], row["proposal_selectable_id"], row["raw_value"]),
    )
    selectable_quality = {**selectable_quality, **duplicate_summary}
    readiness_summary = readiness(selectable_quality, availability_quality, price_quality_summary, queue_summary, source_ref_summary, overlap_summary)
    input_summary = {
        "required_input_presence": {filename: True for filename in REQUIRED_INPUTS.values()},
        "optional_input_presence": {OPTIONAL_INPUTS["rpo_overlap_evidence"]: optional_presence["rpo_overlap_evidence"]},
        "row_counts_by_input_file": {
            REQUIRED_INPUTS["selectables"]: len(rows["selectables"]),
            REQUIRED_INPUTS["selectable_display"]: len(rows["selectable_display"]),
            REQUIRED_INPUTS["availability"]: len(rows["availability"]),
            REQUIRED_INPUTS["raw_price_evidence"]: len(rows["raw_price_evidence"]),
            REQUIRED_INPUTS["source_refs"]: len(rows["source_refs"]),
            REQUIRED_INPUTS["review_queue"]: len(rows["review_queue"]),
            OPTIONAL_INPUTS["rpo_overlap_evidence"]: len(rows["rpo_overlap_evidence"]),
        },
    }
    report = {
        "warning": WARNING,
        "input_summary": input_summary,
        "proposal_counts": {
            "selectables_count": len(rows["selectables"]),
            "selectable_display_count": len(rows["selectable_display"]),
            "availability_count": len(rows["availability"]),
            "raw_price_evidence_count": len(rows["raw_price_evidence"]),
            "source_refs_count": len(rows["source_refs"]),
            "review_queue_count": len(rows["review_queue"]),
            "rpo_overlap_evidence_count": len(rows["rpo_overlap_evidence"]),
        },
        "review_queue_summary": queue_summary,
        "selectables_quality": selectable_quality,
        "availability_quality": availability_quality,
        "price_evidence_quality": price_quality_summary,
        "source_ref_integrity": source_ref_summary,
        "rpo_overlap_traceability": overlap_summary,
        "suspicious_rows": {
            "count": len(suspicious_rows),
            "counts_by_type": counter_dict(Counter(row["suspicion_type"] for row in suspicious_rows)),
        },
        "readiness": readiness_summary,
        "recommended_next_step": "Narrow the next proposal pass to confident selectables only, excluding review-only/no-RPO/ref-only evidence, unless this audit identifies a clearer blocker.",
        "source_proposal_report_summary": {
            "proposal_only": proposal_report.get("proposal_only"),
            "row_counts": proposal_report.get("row_counts", {}),
            "forbidden_outputs_verified_absent": proposal_report.get("forbidden_outputs_verified_absent", []),
        },
    }
    csvs = {
        "proposal_review_queue_summary.csv": queue_rows,
        "proposal_selectable_counts.csv": selectable_count_rows,
        "proposal_availability_counts.csv": availability_count_rows,
        "proposal_source_ref_integrity.csv": integrity_rows,
        "proposal_suspicious_rows.csv": suspicious_rows,
    }
    if optional_presence["rpo_overlap_evidence"]:
        csvs["proposal_rpo_overlap_traceability.csv"] = overlap_rows
    return report, csvs


def write_outputs(out_dir: Path, report: dict[str, Any], csvs: dict[str, list[dict[str, Any]]]) -> None:
    write_json(out_dir / "proposal_audit_report.json", report)
    write_text(out_dir / "proposal_audit_report.md", markdown_report(report, csvs["proposal_review_queue_summary.csv"], csvs["proposal_source_ref_integrity.csv"]))
    headers = {
        "proposal_review_queue_summary.csv": REVIEW_QUEUE_SUMMARY_HEADERS,
        "proposal_selectable_counts.csv": SELECTABLE_COUNTS_HEADERS,
        "proposal_availability_counts.csv": AVAILABILITY_COUNTS_HEADERS,
        "proposal_source_ref_integrity.csv": SOURCE_REF_INTEGRITY_HEADERS,
        "proposal_suspicious_rows.csv": SUSPICIOUS_HEADERS,
        "proposal_rpo_overlap_traceability.csv": RPO_TRACE_HEADERS,
    }
    for filename, rows in csvs.items():
        write_csv(out_dir / filename, headers[filename], rows)


def main() -> int:
    args = parse_args()
    out_dir = Path(args.out)
    validate_output_dir(out_dir)
    report, csvs = build_audit(Path(args.proposal))
    write_outputs(out_dir, report, csvs)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
