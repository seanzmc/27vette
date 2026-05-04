#!/usr/bin/env python3
"""Classify canonical reconciliation output into human review buckets."""

from __future__ import annotations

import argparse
import csv
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SCHEMA_DECISIONS = ROOT / "data" / "import_maps" / "corvette_2027" / "schema_decisions.csv"
WARNING = "Generated reconciliation triage only, not apply. canonical_apply_ready=false."
REQUIRED_INPUTS = {
    "report": "reconciliation_report.json",
    "matched": "matched_selectables.csv",
    "new_candidates": "new_selectable_candidates.csv",
    "conflicts": "conflicting_selectables.csv",
    "unavailable": "unavailable_canonical_context.csv",
    "sections": "section_mapping_needs.csv",
    "availability": "availability_reconciliation.csv",
    "source_refs": "source_ref_member_plan.csv",
    "blockers": "apply_blockers.csv",
}
OPTIONAL_INPUTS = {"report_md": "reconciliation_report.md"}
HEADERS = {
    "matched_selectables_review.csv": [
        "proposal_selectable_id",
        "model_key",
        "orderable_rpo",
        "canonical_selectable_id",
        "match_confidence",
        "match_reasons",
        "label_match_status",
        "description_match_status",
        "review_bucket",
        "triage_status",
        "recommended_action",
        "notes",
    ],
    "new_candidates_review.csv": [
        "proposal_selectable_id",
        "model_key",
        "orderable_rpo",
        "candidate_canonical_selectable_id_preview",
        "candidate_bucket",
        "triage_status",
        "source_ref_count",
        "proposal_label",
        "description",
        "recommended_action",
        "readiness_impact",
        "notes",
    ],
    "conflicts_review.csv": [
        "triage_id",
        "conflict_bucket",
        "original_conflict_type",
        "proposal_selectable_id",
        "model_key",
        "orderable_rpo",
        "canonical_selectable_id",
        "proposal_value",
        "canonical_value",
        "recommended_action",
        "readiness_impact",
        "triage_status",
        "notes",
    ],
    "apply_blockers_review.csv": [
        "blocker_id",
        "blocker_type",
        "severity",
        "blocker_bucket",
        "triage_status",
        "affected_domain",
        "affected_count",
        "required_decision_or_action",
        "recommended_next_action",
        "notes",
    ],
    "section_mapping_requirements.csv": [
        "section_family",
        "model_key",
        "affected_selectable_count",
        "affected_conflict_count",
        "affected_new_candidate_count",
        "required_mapping",
        "recommended_action",
        "suggested_config_file",
        "triage_status",
        "notes",
    ],
    "availability_triage_summary.csv": [
        "model_key",
        "reconciliation_status",
        "availability_value",
        "affected_row_count",
        "recommended_action",
        "triage_status",
        "notes",
    ],
    "source_ref_plan_summary.csv": [
        "proposed_target_table",
        "target_status",
        "model_key",
        "model_key_confidence",
        "planned_member_count",
        "source_ref_count",
        "recommended_action",
        "triage_status",
        "notes",
    ],
}


def clean(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reconciliation", required=True, help="Pass 17 reconciliation output directory.")
    parser.add_argument("--out", required=True, help="Triage output directory.")
    parser.add_argument("--schema-decisions", default=str(DEFAULT_SCHEMA_DECISIONS), help="Optional approved schema decisions CSV.")
    return parser.parse_args()


def is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False


def validate_output_dir(out_dir: Path) -> None:
    resolved = out_dir.resolve()
    for forbidden in [ROOT / "data", ROOT / "data" / "stingray", ROOT / "data" / "corvette", ROOT / "form-output", ROOT / "form-app"]:
        forbidden_resolved = forbidden.resolve()
        if resolved == forbidden_resolved or is_relative_to(resolved, forbidden_resolved):
            raise SystemExit(f"Refusing to write reconciliation triage output under canonical or production directory: {resolved}")


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        try:
            return [dict(row) for row in csv.DictReader(handle)]
        except csv.Error as exc:
            raise SystemExit(f"Malformed CSV input {path}: {exc}") from exc


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


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def load_inputs(reconciliation_dir: Path) -> tuple[dict[str, Any], dict[str, list[dict[str, str]]], dict[str, bool]]:
    missing = [filename for filename in REQUIRED_INPUTS.values() if not (reconciliation_dir / filename).exists()]
    if missing:
        raise SystemExit(f"Missing required reconciliation input: {', '.join(sorted(missing))}")
    report = load_json(reconciliation_dir / REQUIRED_INPUTS["report"])
    rows = {key: read_csv(reconciliation_dir / filename) for key, filename in REQUIRED_INPUTS.items() if key != "report"}
    optional = {key: (reconciliation_dir / filename).exists() for key, filename in OPTIONAL_INPUTS.items()}
    return report, rows, optional


def schema_decisions_present(path: Path) -> bool:
    return path.exists()


def conflict_buckets(conflict_rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    types_by_selectable: dict[str, set[str]] = defaultdict(set)
    for row in conflict_rows:
        types_by_selectable[clean(row.get("proposal_selectable_id", ""))].add(clean(row.get("conflict_type", "")))
    out = []
    for index, row in enumerate(sorted(conflict_rows, key=lambda item: (clean(item.get("proposal_selectable_id", "")), clean(item.get("conflict_type", "")), clean(item.get("orderable_rpo", "")))), start=1):
        proposal_id = clean(row.get("proposal_selectable_id", ""))
        conflict_type = clean(row.get("conflict_type", ""))
        values = types_by_selectable[proposal_id]
        missing_proposal = not clean(row.get("proposal_value", ""))
        missing_canonical = not clean(row.get("canonical_value", ""))
        if {"label_mismatch", "description_mismatch"}.issubset(values):
            bucket = "label_and_description_conflict"
            action = "review_label_and_description_update"
            status = "review_required"
            impact = "review_required"
        elif conflict_type == "label_mismatch":
            bucket = "label_only_conflict"
            action = "review_label_update"
            status = "review_required"
            impact = "review_required"
        elif conflict_type == "description_mismatch":
            bucket = "description_only_conflict"
            action = "review_description_update"
            status = "review_required"
            impact = "review_required"
        elif conflict_type == "ambiguous_canonical_match":
            bucket = "ambiguous_canonical_match"
            action = "resolve_ambiguous_canonical_match"
            status = "blocked"
            impact = "apply_blocker"
        elif "section" in conflict_type or "display" in conflict_type:
            bucket = "section_or_display_conflict"
            action = "review_section_mapping"
            status = "blocked"
            impact = "mapping_needed"
        elif missing_canonical:
            bucket = "canonical_missing_required_field"
            action = "inspect_canonical_row"
            status = "review_required"
            impact = "review_required"
        elif missing_proposal:
            bucket = "proposal_missing_required_field"
            action = "inspect_proposal_row"
            status = "review_required"
            impact = "review_required"
        else:
            bucket = "unknown_conflict_type"
            action = "defer_until_schema_decision"
            status = "review_required"
            impact = "review_required"
        out.append(
            {
                "triage_id": f"conflict_{index:05d}",
                "conflict_bucket": bucket,
                "original_conflict_type": conflict_type,
                "proposal_selectable_id": row.get("proposal_selectable_id", ""),
                "model_key": row.get("model_key", ""),
                "orderable_rpo": row.get("orderable_rpo", ""),
                "canonical_selectable_id": row.get("canonical_selectable_id", ""),
                "proposal_value": row.get("proposal_value", ""),
                "canonical_value": row.get("canonical_value", ""),
                "recommended_action": action,
                "readiness_impact": impact,
                "triage_status": status,
                "notes": "Original conflict_type is preserved; triage does not resolve conflicts.",
            }
        )
    return out


def new_candidate_buckets(rows: list[dict[str, str]], section_needs: list[dict[str, str]]) -> list[dict[str, Any]]:
    section_models = {clean(row.get("model_key", "")) for row in section_needs}
    out = []
    for row in sorted(rows, key=lambda item: (clean(item.get("model_key", "")), clean(item.get("orderable_rpo", "")), clean(item.get("proposal_selectable_id", "")))):
        source_count = int(clean(row.get("source_ref_count", "")) or 0)
        if source_count <= 0:
            bucket = "missing_source_refs"
            status = "blocked"
            action = "restore_source_ref_evidence"
            impact = "apply_blocker"
        elif not clean(row.get("proposal_label", "")):
            bucket = "needs_label_review"
            status = "review_required"
            action = "review_label_before_apply_plan"
            impact = "review_required"
        elif not clean(row.get("description", "")):
            bucket = "needs_description_review"
            status = "review_required"
            action = "review_description_before_apply_plan"
            impact = "review_required"
        elif clean(row.get("candidate_id_status", "")) == "preview_only":
            bucket = "clean_new_candidate"
            status = "candidate_for_future_apply_plan"
            action = "include_in_future_apply_plan_after_section_mapping"
            impact = "mapping_needed" if clean(row.get("model_key", "")) in section_models else "candidate"
        else:
            bucket = "candidate_id_preview_only"
            status = "review_required"
            action = "confirm_candidate_id_status"
            impact = "review_required"
        out.append(
            {
                "proposal_selectable_id": row.get("proposal_selectable_id", ""),
                "model_key": row.get("model_key", ""),
                "orderable_rpo": row.get("orderable_rpo", ""),
                "candidate_canonical_selectable_id_preview": row.get("candidate_canonical_selectable_id_preview", ""),
                "candidate_bucket": bucket,
                "triage_status": status,
                "source_ref_count": row.get("source_ref_count", ""),
                "proposal_label": row.get("proposal_label", ""),
                "description": row.get("description", ""),
                "recommended_action": action,
                "readiness_impact": impact,
                "notes": "Candidate IDs remain preview-only and are not approved for insertion.",
            }
        )
    return out


def matched_buckets(rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    out = []
    for row in sorted(rows, key=lambda item: (clean(item.get("model_key", "")), clean(item.get("orderable_rpo", "")), clean(item.get("proposal_selectable_id", "")))):
        label = clean(row.get("label_match_status", ""))
        desc = clean(row.get("description_match_status", ""))
        confidence = clean(row.get("match_confidence", ""))
        if label == "mismatch":
            bucket = "label_review_needed"
            action = "review_label_update"
            status = "review_required"
        elif desc == "mismatch":
            bucket = "description_review_needed"
            action = "review_description_update"
            status = "review_required"
        elif confidence == "high" and label in {"exact_match", "normalized_match"} and desc in {"exact_match", "normalized_match"}:
            bucket = "strong_match"
            action = "retain_match_for_future_apply_plan"
            status = "advisory"
        elif confidence in {"medium", "low"}:
            bucket = "weak_match"
            action = "review_match_confidence"
            status = "review_required"
        else:
            bucket = "matched_but_section_mapping_needed"
            action = "review_section_mapping"
            status = "review_required"
        out.append({**row, "review_bucket": bucket, "triage_status": status, "recommended_action": action})
    return out


def blocker_bucket(row: dict[str, str]) -> tuple[str, str, str]:
    blocker_id = clean(row.get("blocker_id", ""))
    blocker_type = clean(row.get("blocker_type", ""))
    if blocker_id in {"missing_canonical_availability_schema", "missing_canonical_source_ref_member_schema"}:
        return "schema_context_missing", "blocked", "create_or_approve_missing_schema"
    if blocker_id == "missing_section_family_import_map" or blocker_type == "mapping_needed":
        return "mapping_needed", "blocked", "create_section_family_map_in_future_pass"
    if blocker_id == "non_stingray_model_context_unavailable":
        return "canonical_context_unavailable", "blocked", "provide_model_context_or_exclude_from_apply"
    if blocker_id == "canonical_selectable_id_policy_not_applied":
        return "policy_not_applied", "blocked", "apply_id_policy_in_future_apply_plan"
    if blocker_id == "canonical_apply_ready_false_by_design":
        return "design_boundary", "advisory", "keep_apply_in_separate_approved_pass"
    return "advisory", "review_required", "inspect_blocker"


def blocker_review(rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    out = []
    for row in sorted(rows, key=lambda item: clean(item.get("blocker_id", ""))):
        bucket, status, action = blocker_bucket(row)
        out.append({**row, "blocker_bucket": bucket, "triage_status": status, "recommended_next_action": action})
    return out


def section_requirements(section_rows: list[dict[str, str]], conflicts: list[dict[str, Any]], candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    conflict_counts = Counter(clean(row.get("model_key", "")) for row in conflicts)
    candidate_counts = Counter(clean(row.get("model_key", "")) for row in candidates)
    out = []
    for row in sorted(section_rows, key=lambda item: (clean(item.get("model_key", "")), clean(item.get("section_family", "")))):
        model_key = clean(row.get("model_key", ""))
        out.append(
            {
                "section_family": row.get("section_family", ""),
                "model_key": model_key,
                "affected_selectable_count": row.get("affected_selectable_count", ""),
                "affected_conflict_count": conflict_counts.get(model_key, 0),
                "affected_new_candidate_count": candidate_counts.get(model_key, 0),
                "required_mapping": row.get("required_mapping", ""),
                "recommended_action": "create_section_family_map_in_future_pass",
                "suggested_config_file": "data/import_maps/corvette_2027/section_family_map.csv",
                "triage_status": "blocked",
                "notes": "No section map was created by this triage pass.",
            }
        )
    return out


def availability_summary(rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    grouped: Counter[tuple[str, str, str]] = Counter()
    for row in rows:
        grouped[(clean(row.get("model_key", "")), clean(row.get("reconciliation_status", "")), clean(row.get("availability_value", "")))] += 1
    out = []
    for (model_key, status, value), count in sorted(grouped.items()):
        action = "create_canonical_availability_schema" if status == "target_schema_missing" else "provide_model_context_or_exclude_from_apply"
        triage_status = "blocked" if status in {"target_schema_missing", "model_context_unavailable"} else "advisory"
        out.append(
            {
                "model_key": model_key,
                "reconciliation_status": status,
                "availability_value": value,
                "affected_row_count": count,
                "recommended_action": action,
                "triage_status": triage_status,
                "notes": "Availability remains report-only; no canonical rows generated.",
            }
        )
    return out


def infer_model_key(proposal_id: str) -> tuple[str, str]:
    value = clean(proposal_id)
    for model in ["grand_sport", "stingray", "z06", "zr1", "zr1x"]:
        if f"prop_{model}_" in value:
            return model, "inferred_from_proposal_id"
    return "", ""


def target_status(target: str) -> str:
    target = clean(target)
    if not target:
        return "missing_target"
    if target.startswith("sel_"):
        return "preview_target"
    return "matched_canonical_target"


def source_ref_summary(rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str, str, str], set[str]] = defaultdict(set)
    counts: Counter[tuple[str, str, str, str]] = Counter()
    for row in rows:
        model_key, confidence = infer_model_key(row.get("proposal_selectable_id", ""))
        key = (clean(row.get("proposed_target_table", "")), target_status(row.get("proposed_target_row_key", "")), model_key, confidence)
        counts[key] += 1
        if clean(row.get("source_ref_id", "")):
            grouped[key].add(clean(row.get("source_ref_id", "")))
    out = []
    for (table, status, model_key, confidence), count in sorted(counts.items()):
        action = "preserve_as_plan_only"
        triage_status = "advisory" if status == "matched_canonical_target" else "blocked"
        out.append(
            {
                "proposed_target_table": table,
                "target_status": status,
                "model_key": model_key,
                "model_key_confidence": confidence,
                "planned_member_count": count,
                "source_ref_count": len(grouped[(table, status, model_key, confidence)]),
                "recommended_action": action,
                "triage_status": triage_status,
                "notes": "source_ref_member_plan remains plan-only; no canonical source-ref rows generated.",
            }
        )
    return out


def count_by(rows: list[dict[str, Any]], field: str) -> dict[str, int]:
    return dict(sorted(Counter(clean(row.get(field, "")) for row in rows).items()))


def build_report(report: dict[str, Any], optional: dict[str, bool], schema_decisions_present_flag: bool, outputs: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    blockers = outputs["apply_blockers_review.csv"]
    conflicts = outputs["conflicts_review.csv"]
    ready = not any(row["triage_status"] == "blocked" for row in blockers + conflicts + outputs["section_mapping_requirements.csv"])
    reasons = []
    if any(row["conflict_bucket"] == "ambiguous_canonical_match" for row in conflicts):
        reasons.append("ambiguous_canonical_matches_present")
    if outputs["section_mapping_requirements.csv"]:
        reasons.append("section_mapping_requirements_unresolved")
    if any(row["blocker_bucket"] == "schema_context_missing" for row in blockers):
        reasons.append("missing_availability_or_source_ref_schema")
    if conflicts:
        reasons.append("conflicts_require_review")
    return {
        "warning": WARNING,
        "input_summary": {"reconciliation_path": "provided --reconciliation", "out_path": "provided --out"},
        "optional_input_presence": {**optional, "schema_decisions_csv": schema_decisions_present_flag},
        "reconciliation_counts": report.get("match_counts", {}),
        "conflict_bucket_counts": count_by(conflicts, "conflict_bucket"),
        "new_candidate_bucket_counts": count_by(outputs["new_candidates_review.csv"], "candidate_bucket"),
        "matched_bucket_counts": count_by(outputs["matched_selectables_review.csv"], "review_bucket"),
        "blocker_bucket_counts": count_by(blockers, "blocker_bucket"),
        "section_mapping_requirement_counts": count_by(outputs["section_mapping_requirements.csv"], "section_family"),
        "availability_triage_counts": count_by(outputs["availability_triage_summary.csv"], "reconciliation_status"),
        "source_ref_plan_summary": count_by(outputs["source_ref_plan_summary.csv"], "target_status"),
        "canonical_apply_ready": False,
        "triage_ready_for_apply_plan": ready,
        "reasons": reasons,
        "recommended_next_step": "Review conflict buckets and create approved section/source/availability schemas before an apply-plan generator.",
    }


def markdown(summary: dict[str, Any]) -> str:
    return f"""# Reconciliation Triage Report

{WARNING}

This is generated triage only, not apply.

- canonical_apply_ready=false
- triage_ready_for_apply_plan={str(summary["triage_ready_for_apply_plan"]).lower()}
- conflict buckets: `{json.dumps(summary["conflict_bucket_counts"], sort_keys=True)}`
- new candidate buckets: `{json.dumps(summary["new_candidate_bucket_counts"], sort_keys=True)}`
- blocker buckets: `{json.dumps(summary["blocker_bucket_counts"], sort_keys=True)}`

No canonical rows were generated or applied.

No section map was created.
"""


def build_outputs(reconciliation_dir: Path, schema_decisions_path: Path) -> tuple[dict[str, Any], dict[str, list[dict[str, Any]]]]:
    report, rows, optional = load_inputs(reconciliation_dir)
    conflicts = conflict_buckets(rows["conflicts"])
    candidates = new_candidate_buckets(rows["new_candidates"], rows["sections"])
    matched = matched_buckets(rows["matched"])
    blockers = blocker_review(rows["blockers"])
    sections = section_requirements(rows["sections"], conflicts, candidates)
    availability = availability_summary(rows["availability"])
    source_refs = source_ref_summary(rows["source_refs"])
    outputs = {
        "matched_selectables_review.csv": matched,
        "new_candidates_review.csv": candidates,
        "conflicts_review.csv": conflicts,
        "apply_blockers_review.csv": blockers,
        "section_mapping_requirements.csv": sections,
        "availability_triage_summary.csv": availability,
        "source_ref_plan_summary.csv": source_refs,
    }
    summary = build_report(report, optional, schema_decisions_present(schema_decisions_path), outputs)
    return summary, outputs


def write_outputs(out_dir: Path, summary: dict[str, Any], outputs: dict[str, list[dict[str, Any]]]) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    write_json(out_dir / "reconciliation_triage_report.json", summary)
    write_text(out_dir / "reconciliation_triage_report.md", markdown(summary))
    for filename, rows in outputs.items():
        write_csv(out_dir / filename, HEADERS[filename], rows)


def main() -> int:
    args = parse_args()
    out_dir = Path(args.out)
    validate_output_dir(out_dir)
    summary, outputs = build_outputs(Path(args.reconciliation), Path(args.schema_decisions))
    write_outputs(out_dir, summary, outputs)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
