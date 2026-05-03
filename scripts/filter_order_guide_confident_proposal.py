#!/usr/bin/env python3
"""Filter a broad order-guide proposal into a confident primary-matrix subset."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
FILTER_STATUS = "confident_subset"
REPORT_WARNING = "Generated confident subset files are still proposal artifacts only. canonical_apply_ready is false."

REQUIRED_INPUTS = {
    "proposal_report": "proposal_report.json",
    "proposal_audit_report": "proposal_audit_report.json",
    "selectables": "catalog/selectables.csv",
    "selectable_display": "ui/selectable_display.csv",
    "availability": "ui/availability.csv",
    "source_refs": "meta/source_refs.csv",
    "review_queue": "review_queue.csv",
}
OPTIONAL_INPUTS = {
    "review_queue_summary": "proposal_review_queue_summary.csv",
    "source_ref_integrity": "proposal_source_ref_integrity.csv",
    "suspicious_rows": "proposal_suspicious_rows.csv",
}
OWNED_OUTPUTS = [
    "catalog/selectables.csv",
    "ui/selectable_display.csv",
    "ui/availability.csv",
    "meta/source_refs.csv",
    "proposal_subset_report.json",
    "excluded_review_rows.csv",
]
FORBIDDEN_OUTPUTS = [
    "pricing/raw_price_evidence.csv",
    "pricing/base_prices.csv",
    "pricing/price_rules.csv",
    "logic/dependency_rules.csv",
    "logic/auto_adds.csv",
    "logic/exclusive_groups.csv",
    "logic/exclusive_group_members.csv",
    "support/color_trim*.csv",
    "data/stingray/**/*.csv",
    "form-app/data.js",
    "form-output/*",
]
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
    "missing_rpo_standard_equipment",
    "ref_only_evidence",
    "duplicate_or_conflicting_evidence",
    "missing_model_or_variant_context",
    "unsupported_status",
    "boundary_exclusion_summary",
    "price_evidence_review",
    "missing_rpo_non_standard_equipment",
    "orderable_ref_same_row_review",
    "unclassified_review_item",
}
NONBLOCKING_BUCKETS = {"expected_review_only"}


def clean(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--proposal", required=True, help="Broad proposal directory.")
    parser.add_argument("--out", required=True, help="Confident subset output directory.")
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
            raise SystemExit(f"Refusing to write confident proposal subset output under canonical or production directory: {resolved}")
    for pattern in FORBIDDEN_OUTPUTS:
        matches = list(out_dir.glob(pattern))
        if matches:
            raise SystemExit(f"Refusing to write confident proposal subset because forbidden output path exists: {matches[0]}")


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        try:
            return [dict(row) for row in csv.DictReader(handle)]
        except csv.Error as exc:
            raise SystemExit(f"Malformed CSV input {path}: {exc}") from exc


def read_csv_if_present(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    return read_csv(path)


def load_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Malformed JSON input {path}: {exc}") from exc


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


def pipe_values(value: str) -> list[str]:
    return [item for item in clean(value).split("|") if item]


def stable_hash(value: str, length: int = 12) -> str:
    return hashlib.sha1(value.encode("utf-8")).hexdigest()[:length]


def load_inputs(proposal_dir: Path) -> tuple[dict[str, list[dict[str, str]]], dict[str, Any], dict[str, Any], dict[str, bool]]:
    missing = [filename for filename in REQUIRED_INPUTS.values() if not (proposal_dir / filename).exists()]
    if missing:
        raise SystemExit(f"Missing required proposal input: {', '.join(sorted(missing))}")
    rows: dict[str, list[dict[str, str]]] = {}
    for key, filename in REQUIRED_INPUTS.items():
        if key in {"proposal_report", "proposal_audit_report"}:
            continue
        rows[key] = read_csv(proposal_dir / filename)
    optional_presence: dict[str, bool] = {}
    for key, filename in OPTIONAL_INPUTS.items():
        path = proposal_dir / filename
        optional_presence[key] = path.exists()
        rows[key] = read_csv_if_present(path)
    return (
        rows,
        load_json(proposal_dir / REQUIRED_INPUTS["proposal_report"]),
        load_json(proposal_dir / REQUIRED_INPUTS["proposal_audit_report"]),
        optional_presence,
    )


def review_bucket(reason: str) -> str:
    return REVIEW_BUCKETS.get(clean(reason), "unclassified_review_item")


def review_exclusions(review_rows: list[dict[str, str]]) -> tuple[dict[str, set[str]], list[dict[str, Any]], set[str], set[str], int]:
    by_selectable: dict[str, set[str]] = defaultdict(set)
    excluded_rows: list[dict[str, Any]] = []
    blocking_seen: set[str] = set()
    nonblocking_seen: set[str] = set()
    rows_without_selectable = 0
    for row in review_rows:
        reason = clean(row.get("reason", ""))
        bucket = review_bucket(reason)
        proposal_id = clean(row.get("proposal_selectable_id", ""))
        if bucket in BLOCKING_BUCKETS:
            blocking_seen.add(bucket)
        if bucket in NONBLOCKING_BUCKETS:
            nonblocking_seen.add(bucket)
        if not proposal_id:
            rows_without_selectable += 1
        if proposal_id and bucket in BLOCKING_BUCKETS:
            by_selectable[proposal_id].add(bucket)
        excluded_rows.append(
            {
                "exclusion_id": f"excl_{stable_hash(json.dumps(row, sort_keys=True))}",
                "exclusion_reason": f"review_bucket_{bucket}",
                "review_bucket": bucket,
                "original_reason": reason,
                "proposal_selectable_id": proposal_id,
                "model_key": row.get("model_key", ""),
                "section_family": "",
                "rpo": row.get("rpo", ""),
                "source_sheet": row.get("source_sheet", ""),
                "source_row": row.get("source_row", ""),
                "raw_value": row.get("raw_value", ""),
                "recommended_action": row.get("recommended_action", ""),
                "notes": row.get("notes", ""),
            }
        )
    return by_selectable, excluded_rows, blocking_seen, nonblocking_seen, rows_without_selectable


def add_filter_status(row: dict[str, str]) -> dict[str, Any]:
    return {**row, "proposal_filter_status": FILTER_STATUS}


def source_ref_ids(source_refs: list[dict[str, str]]) -> set[str]:
    return {clean(row.get("source_ref_id", "")) for row in source_refs if clean(row.get("source_ref_id", ""))}


def selectable_exclusion_reason(row: dict[str, str], valid_refs: set[str], review_by_id: dict[str, set[str]]) -> str:
    proposal_id = clean(row.get("proposal_selectable_id", ""))
    if clean(row.get("proposal_scope", "")) == "standard_equipment_review_only":
        return "review_only"
    if clean(row.get("review_status", "")) != "proposal_only":
        return "review_only"
    if not clean(row.get("orderable_rpo", "")):
        return "no_rpo"
    if clean(row.get("has_orderable_rpo", "")) != "true" and clean(row.get("has_ref_rpo", "")) == "true":
        return "ref_only"
    if not clean(row.get("model_key", "")) or clean(row.get("model_key", "")) == "corvette":
        return "missing_model_key"
    refs = pipe_values(row.get("source_ref_ids", ""))
    if not refs or any(ref not in valid_refs for ref in refs):
        return "unresolved_source_ref"
    if proposal_id in review_by_id:
        return "blocking_review_bucket"
    if clean(row.get("source_sheet", "")).startswith("Color and Trim") or clean(row.get("source_sheet", "")).startswith("Equipment Groups"):
        return "boundary_excluded"
    return ""


def availability_exclusion_reason(row: dict[str, str], retained_ids: set[str], valid_refs: set[str]) -> str:
    if clean(row.get("proposal_selectable_id", "")) not in retained_ids:
        return "selectable_excluded"
    if clean(row.get("availability_value", "")) not in {"available", "standard", "not_available"}:
        return "unsupported_status"
    if not clean(row.get("model_key", "")):
        return "missing_model_key"
    if not clean(row.get("variant_id", "")):
        return "missing_variant_id"
    if not clean(row.get("source_ref_id", "")) or clean(row.get("source_ref_id", "")) not in valid_refs:
        return "unresolved_source_ref"
    return ""


def exclusion_row(reason: str, row: dict[str, str], notes: str = "") -> dict[str, Any]:
    return {
        "exclusion_id": f"excl_{stable_hash(reason + json.dumps(row, sort_keys=True))}",
        "exclusion_reason": reason,
        "review_bucket": "",
        "original_reason": "",
        "proposal_selectable_id": row.get("proposal_selectable_id", ""),
        "model_key": row.get("model_key", ""),
        "section_family": row.get("section_family", ""),
        "rpo": row.get("orderable_rpo", "") or row.get("ref_rpo", "") or row.get("rpo", ""),
        "source_sheet": row.get("source_sheet", ""),
        "source_row": row.get("source_row", ""),
        "raw_value": row.get("description", "") or row.get("display_label", "") or row.get("raw_value", ""),
        "recommended_action": recommended_action(reason),
        "notes": notes,
    }


def recommended_action(reason: str) -> str:
    return {
        "no_rpo": "exclude_no_rpo_review_evidence_from_confident_subset",
        "review_only": "exclude_review_only_material",
        "ref_only": "exclude_reference_only_evidence",
        "missing_model_key": "review_model_scope_before_confident_subset",
        "missing_variant_id": "review_variant_scope_before_confident_subset",
        "unsupported_status": "exclude_unsupported_status_availability",
        "unresolved_source_ref": "fix_source_ref_before_confident_subset",
        "blocking_review_bucket": "resolve_or_exclude_review_bucket_before_confident_subset",
        "boundary_excluded": "keep_boundary_domain_out_of_confident_subset",
        "price_evidence_excluded": "price_evidence_is_raw_and_not_matched_to_selectables",
        "selectable_excluded": "exclude_availability_for_removed_selectable",
    }.get(reason, "review_exclusion_before_future_subset")


def duplicate_ids(rows: list[dict[str, Any]]) -> list[str]:
    counts = Counter(clean(row.get("proposal_selectable_id", "")) for row in rows)
    return sorted(pid for pid, count in counts.items() if pid and count > 1)


def filter_subset(rows: dict[str, list[dict[str, str]]]) -> tuple[dict[str, list[dict[str, Any]]], dict[str, Any]]:
    valid_refs = source_ref_ids(rows["source_refs"])
    review_by_id, review_excluded, blocking_seen, nonblocking_seen, rows_without_selectable = review_exclusions(rows["review_queue"])
    excluded: list[dict[str, Any]] = list(review_excluded)
    excluded_counts: Counter[str] = Counter()

    retained_selectables: list[dict[str, Any]] = []
    excluded_selectable_ids: set[str] = set()
    for row in rows["selectables"]:
        reason = selectable_exclusion_reason(row, valid_refs, review_by_id)
        if reason:
            excluded_counts[reason] += 1
            excluded_selectable_ids.add(clean(row.get("proposal_selectable_id", "")))
            excluded.append(exclusion_row(reason, row))
        else:
            retained_selectables.append(add_filter_status(row))

    retained_ids = {clean(row.get("proposal_selectable_id", "")) for row in retained_selectables}
    retained_availability: list[dict[str, Any]] = []
    for row in rows["availability"]:
        reason = availability_exclusion_reason(row, retained_ids, valid_refs)
        if reason:
            excluded_counts[reason] += 1
            if reason != "selectable_excluded":
                excluded.append(exclusion_row(reason, row))
        else:
            retained_availability.append(add_filter_status(row))

    retained_display = [add_filter_status(row) for row in rows["selectable_display"] if clean(row.get("proposal_selectable_id", "")) in retained_ids]
    referenced_refs: set[str] = set()
    for row in retained_selectables:
        referenced_refs.update(pipe_values(row.get("source_ref_ids", "")))
    for row in retained_availability:
        referenced_refs.add(clean(row.get("source_ref_id", "")))
    retained_source_refs = [row for row in rows["source_refs"] if clean(row.get("source_ref_id", "")) in referenced_refs]
    retained_ref_ids = source_ref_ids(retained_source_refs)
    unresolved_retained = sorted(ref for ref in referenced_refs if ref and ref not in retained_ref_ids)
    duplicate_retained_ids = duplicate_ids(retained_selectables)
    if duplicate_retained_ids:
        excluded_counts["duplicate_proposal_id"] += len(duplicate_retained_ids)
        for pid in duplicate_retained_ids:
            excluded.append(exclusion_row("duplicate_proposal_id", {"proposal_selectable_id": pid}, "Duplicate retained proposal ID blocks subset readiness."))

    outputs = {
        "selectables": sorted(retained_selectables, key=lambda row: (row.get("model_key", ""), row.get("section_family", ""), row.get("orderable_rpo", ""), row.get("proposal_selectable_id", ""))),
        "display": sorted(retained_display, key=lambda row: (row.get("model_key", ""), row.get("section_family", ""), row.get("display_label", ""), row.get("proposal_selectable_id", ""))),
        "availability": sorted(retained_availability, key=lambda row: (row.get("model_key", ""), row.get("variant_id", ""), row.get("proposal_selectable_id", ""), row.get("source_ref_id", ""))),
        "source_refs": sorted(retained_source_refs, key=lambda row: (row.get("source_sheet", ""), numeric(row.get("source_row", "")), row.get("source_field", ""), row.get("source_ref_id", ""))),
        "excluded": sorted(excluded, key=lambda row: (row.get("exclusion_reason", ""), row.get("proposal_selectable_id", ""), row.get("source_sheet", ""), numeric(row.get("source_row", "")))),
    }
    meta = {
        "excluded_counts": excluded_counts,
        "blocking_review_buckets_used": sorted(blocking_seen),
        "nonblocking_review_buckets_observed": sorted(nonblocking_seen),
        "review_rows_without_selectable_id_count": rows_without_selectable,
        "unresolved_retained_refs": unresolved_retained,
        "duplicate_retained_ids": duplicate_retained_ids,
        "broad_counts": {
            "broad_selectables": len(rows["selectables"]),
            "broad_selectable_display": len(rows["selectable_display"]),
            "broad_availability": len(rows["availability"]),
            "broad_source_refs": len(rows["source_refs"]),
            "broad_review_queue": len(rows["review_queue"]),
            "broad_price_evidence_count": 0,
        },
    }
    return outputs, meta


def numeric(value: str) -> int:
    try:
        return int(clean(value) or 0)
    except ValueError:
        return 0


def known_headers(rows: list[dict[str, Any]]) -> list[str]:
    if not rows:
        return []
    return list(rows[0].keys())


def write_owned_outputs(out_dir: Path, outputs: dict[str, list[dict[str, Any]]], report: dict[str, Any]) -> None:
    write_csv(out_dir / "catalog" / "selectables.csv", known_headers(outputs["selectables"]), outputs["selectables"])
    write_csv(out_dir / "ui" / "selectable_display.csv", known_headers(outputs["display"]), outputs["display"])
    write_csv(out_dir / "ui" / "availability.csv", known_headers(outputs["availability"]), outputs["availability"])
    write_csv(out_dir / "meta" / "source_refs.csv", known_headers(outputs["source_refs"]), outputs["source_refs"])
    write_csv(out_dir / "excluded_review_rows.csv", [
        "exclusion_id",
        "exclusion_reason",
        "review_bucket",
        "original_reason",
        "proposal_selectable_id",
        "model_key",
        "section_family",
        "rpo",
        "source_sheet",
        "source_row",
        "raw_value",
        "recommended_action",
        "notes",
    ], outputs["excluded"])
    write_json(out_dir / "proposal_subset_report.json", report)


def forbidden_outputs_absent(out_dir: Path) -> list[str]:
    absent: list[str] = []
    for pattern in FORBIDDEN_OUTPUTS:
        matches = list(out_dir.glob(pattern))
        if matches:
            raise SystemExit(f"Forbidden confident subset output exists: {matches[0]}")
        absent.append(pattern)
    return absent


def report(proposal_dir: Path, out_dir: Path, outputs: dict[str, list[dict[str, Any]]], meta: dict[str, Any], proposal_report: dict[str, Any], audit_report: dict[str, Any], optional_presence: dict[str, bool]) -> dict[str, Any]:
    retained_refs = {clean(row.get("source_ref_id", "")) for row in outputs["source_refs"] if clean(row.get("source_ref_id", ""))}
    referenced_refs = set()
    for row in outputs["selectables"]:
        referenced_refs.update(pipe_values(row.get("source_ref_ids", "")))
    for row in outputs["availability"]:
        referenced_refs.add(clean(row.get("source_ref_id", "")))
    unresolved = sorted(ref for ref in referenced_refs if ref and ref not in retained_refs)
    unused = sorted(ref for ref in retained_refs if ref and ref not in referenced_refs)
    reasons = []
    if unresolved:
        reasons.append("unresolved_retained_source_refs")
    if meta["duplicate_retained_ids"]:
        reasons.append("duplicate_retained_proposal_ids")
    ready = not unresolved and not meta["duplicate_retained_ids"]
    broad_counts = dict(meta["broad_counts"])
    broad_counts["broad_price_evidence_count"] = proposal_report.get("row_counts", {}).get("pricing_raw_price_evidence", 0)
    excluded_counts = dict(sorted((key, count) for key, count in meta["excluded_counts"].items() if count))
    for required_key in [
        "no_rpo",
        "review_only",
        "ref_only",
        "missing_model_key",
        "missing_variant_id",
        "unsupported_status",
        "unresolved_source_ref",
        "blocking_review_bucket",
        "boundary_excluded",
        "price_evidence_excluded",
        "other",
    ]:
        excluded_counts.setdefault(required_key, 0)
    excluded_counts["price_evidence_excluded"] = broad_counts["broad_price_evidence_count"]
    return {
        "warning": REPORT_WARNING,
        "input_summary": {
            "required_input_presence": {filename: True for filename in REQUIRED_INPUTS.values()},
            "optional_input_presence": {OPTIONAL_INPUTS[key]: present for key, present in sorted(optional_presence.items())},
            "broad_proposal_path": "provided --proposal",
            "subset_output_path": "provided --out",
        },
        "broad_counts": broad_counts,
        "confident_subset_counts": {
            "retained_selectables": len(outputs["selectables"]),
            "retained_selectable_display": len(outputs["display"]),
            "retained_availability": len(outputs["availability"]),
            "retained_source_refs": len(outputs["source_refs"]),
            "excluded_selectables": broad_counts["broad_selectables"] - len(outputs["selectables"]),
            "excluded_availability_rows": broad_counts["broad_availability"] - len(outputs["availability"]),
            "excluded_review_rows": len(outputs["excluded"]),
        },
        "excluded_counts_by_reason": excluded_counts,
        "source_ref_integrity": {
            "retained_referenced_source_refs": len(referenced_refs),
            "retained_source_refs_count": len(retained_refs),
            "unresolved_retained_refs_count": len(unresolved),
            "unused_retained_source_refs_count": len(unused),
            "unresolved_retained_refs": unresolved,
            "source_refs_ready": not unresolved,
        },
        "blocking_review_buckets_used": meta["blocking_review_buckets_used"],
        "nonblocking_review_buckets_observed": meta["nonblocking_review_buckets_observed"],
        "review_rows_without_selectable_id_count": meta["review_rows_without_selectable_id_count"],
        "forbidden_outputs_verified_absent": forbidden_outputs_absent(out_dir),
        "readiness": {
            "confident_subset_ready": ready,
            "source_refs_ready": not unresolved,
            "canonical_apply_ready": False,
            "reasons": reasons,
        },
        "source_audit_summary": {
            "canonical_apply_ready": audit_report.get("readiness", {}).get("canonical_apply_ready", False),
            "source_refs_ready": audit_report.get("readiness", {}).get("source_refs_ready", ""),
            "review_queue_ready": audit_report.get("readiness", {}).get("review_queue_ready", ""),
        },
        "recommended_next_step": "Review the confident subset row counts and decide whether to generate a human-readable confident-subset review packet or compare against existing canonical CSV after the CSV refactor is fully migrated.",
    }


def generate(proposal_dir: Path, out_dir: Path) -> None:
    validate_output_dir(out_dir)
    rows, proposal_report, audit_report, optional_presence = load_inputs(proposal_dir)
    outputs, meta = filter_subset(rows)
    subset_report = report(proposal_dir, out_dir, outputs, meta, proposal_report, audit_report, optional_presence)
    write_owned_outputs(out_dir, outputs, subset_report)


def main() -> int:
    args = parse_args()
    generate(Path(args.proposal), Path(args.out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
