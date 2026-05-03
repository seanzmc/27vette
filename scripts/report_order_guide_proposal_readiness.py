#!/usr/bin/env python3
"""Report the safe future proposal boundary for staged order-guide evidence.

This script reads staging audit/config outputs only. It does not parse raw
workbooks, mutate staging, edit canonical CSVs, or generate proposal rows.
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_COLOR_TRIM_SCOPE = ROOT / "data" / "import_maps" / "corvette_2027" / "color_trim_scope.csv"
DEFAULT_RPO_ROLE_OVERLAPS = ROOT / "data" / "import_maps" / "corvette_2027" / "rpo_role_overlaps.csv"
AUDIT_FIRST_MESSAGE = "Run scripts/audit_order_guide_staging.py before generating the proposal readiness report."
REPORT_WARNING = (
    "This report is not a canonical proposal and is not source-of-truth config. "
    "Use data/import_maps/corvette_2027/*.csv for review decisions."
)


def clean(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--staging", required=True, help="Directory containing staging audit output.")
    parser.add_argument("--out", required=True, help="Directory where proposal readiness reports should be written.")
    parser.add_argument(
        "--color-trim-scope",
        default=str(DEFAULT_COLOR_TRIM_SCOPE),
        help="Optional Color/Trim scope decision map. Defaults to the repo-relative Corvette 2027 map.",
    )
    parser.add_argument(
        "--rpo-role-overlaps",
        default=str(DEFAULT_RPO_ROLE_OVERLAPS),
        help="Optional RPO role-overlap decision map. Defaults to the repo-relative Corvette 2027 map.",
    )
    return parser.parse_args()


def read_csv_if_present(path: Path) -> tuple[list[dict[str, str]], bool]:
    if not path.exists():
        return [], False
    with path.open(newline="", encoding="utf-8") as handle:
        return [dict(row) for row in csv.DictReader(handle)], True


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def load_audit_report(staging_dir: Path) -> dict[str, Any]:
    audit_path = staging_dir / "staging_audit_report.json"
    if not audit_path.exists():
        raise SystemExit(f"{AUDIT_FIRST_MESSAGE} Missing required input: staging_audit_report.json")
    try:
        return json.loads(audit_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Malformed staging_audit_report.json: {exc}") from exc


def audit_snapshot(audit: dict[str, Any]) -> dict[str, Any]:
    readiness = audit.get("readiness", {}) if isinstance(audit.get("readiness"), dict) else {}
    return {
        "primary_variant_matrix_ready": bool(readiness.get("primary_variant_matrix_ready", False)),
        "color_trim_ready": bool(readiness.get("color_trim_ready", False)),
        "pricing_ready": bool(readiness.get("pricing_ready", False)),
        "equipment_groups_ready": bool(readiness.get("equipment_groups_ready", False)),
        "rpo_role_overlaps_ready": bool(readiness.get("rpo_role_overlaps_ready", False)),
        "canonical_proposal_ready": bool(readiness.get("canonical_proposal_ready", False)),
        "ready_for_proposal_generation": bool(readiness.get("ready_for_proposal_generation", False)),
        "readiness_reasons": sorted(readiness.get("reasons", []) or []),
    }


def row_count(audit: dict[str, Any], key: str) -> int:
    row_counts = audit.get("row_counts", {}) if isinstance(audit.get("row_counts"), dict) else {}
    value = row_counts.get(key, {}) if isinstance(row_counts.get(key), dict) else {}
    try:
        return int(value.get("total_rows", 0) or 0)
    except (TypeError, ValueError):
        return 0


def accepted_rpo_overlap_count(audit: dict[str, Any], rpo_rows: list[dict[str, str]]) -> int:
    decisions = audit.get("rpo_role_overlap_decisions", {})
    if isinstance(decisions, dict):
        resolved = decisions.get("resolved_overlap_count")
        if isinstance(resolved, int):
            return resolved
    return sum(1 for row in rpo_rows if clean(row.get("decision_review_status", "")) == "accepted_expected_overlap")


def config_status(rows: list[dict[str, str]], field_name: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        value = clean(row.get(field_name, "")) or "<blank>"
        counts[value] = counts.get(value, 0) + 1
    return dict(sorted(counts.items()))


def included_domains(audit: dict[str, Any], rpo_rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    snapshot = audit_snapshot(audit)
    variant_count = row_count(audit, "variant_matrix_rows")
    price_count = row_count(audit, "price_rows")
    overlap_count = accepted_rpo_overlap_count(audit, rpo_rows)
    return [
        {
            "domain_key": "primary_variant_matrix_rows",
            "eligibility_status": "eligible" if snapshot["primary_variant_matrix_ready"] and variant_count > 0 else "not_ready",
            "allowed_future_use": "Future proposal input for Standard Equipment, Interior, Exterior, and Mechanical primary variant matrix evidence.",
            "source_files": ["staging_variant_matrix_rows.csv", "staging_audit_report.json"],
            "notes": f"{variant_count} staged variant-matrix rows reported by the audit.",
        },
        {
            "domain_key": "price_schedule_raw_evidence",
            "eligibility_status": "eligible" if snapshot["pricing_ready"] else "not_ready",
            "allowed_future_use": "Future proposal input as raw price evidence only; final price semantics remain out of scope.",
            "source_files": ["staging_price_rows.csv", "staging_audit_report.json"],
            "notes": f"{price_count} staged price-evidence rows reported by the audit.",
        },
        {
            "domain_key": "accepted_rpo_role_overlaps_as_separate_evidence",
            "eligibility_status": "eligible" if snapshot["rpo_role_overlaps_ready"] and overlap_count >= 0 else "not_ready",
            "allowed_future_use": "Future proposal input may preserve accepted orderable/ref-only overlaps as separate evidence only.",
            "source_files": ["staging_audit_rpo_role_overlaps.csv", "data/import_maps/corvette_2027/rpo_role_overlaps.csv"],
            "notes": f"{overlap_count} RPO overlap decisions are resolved as separate evidence.",
        },
    ]


def excluded_domains(
    audit: dict[str, Any],
    color_trim_scope_rows: list[dict[str, str]],
    color_trim_scope_present: bool,
    rpo_overlap_rows: list[dict[str, str]],
    rpo_overlap_present: bool,
) -> list[dict[str, Any]]:
    color_scope = audit.get("color_trim_scope_review", {}) if isinstance(audit.get("color_trim_scope_review"), dict) else {}
    accepted_review_only = int(color_scope.get("accepted_review_only_count", 0) or 0)
    color_reason = (
        f"{accepted_review_only} Color/Trim sections are accepted_review_only."
        if accepted_review_only
        else f"Color/Trim scope review statuses: {config_status(color_trim_scope_rows, 'review_status')}"
    )
    rpo_decisions = audit.get("rpo_role_overlap_decisions", {}) if isinstance(audit.get("rpo_role_overlap_decisions"), dict) else {}
    resolved_overlaps = int(rpo_decisions.get("resolved_overlap_count", 0) or 0)
    canonical_handling_counts = rpo_decisions.get("canonical_handling_counts", {})
    return [
        {
            "domain_key": "color_trim_canonical_import",
            "disposition": "excluded_from_first_proposal_scope",
            "reason": color_reason,
            "source_of_decision": "data/import_maps/corvette_2027/color_trim_scope.csv"
            if color_trim_scope_present
            else "missing_optional_config",
            "notes": "Color/Trim can be audit-ready while still not canonical-import-ready.",
        },
        {
            "domain_key": "equipment_groups_as_selectable_source",
            "disposition": "excluded_cross_check_only",
            "reason": "Equipment Groups remain derived/cross-check evidence and are not a source of new selectables.",
            "source_of_decision": "staging_audit_report.json",
            "notes": f"cross_check_only={audit.get('equipment_groups', {}).get('cross_check_only', '')}",
        },
        {
            "domain_key": "rpo_overlap_merging",
            "disposition": "excluded_keep_separate_evidence",
            "reason": f"{resolved_overlaps} overlap decisions are resolved; canonical handling counts: {canonical_handling_counts}",
            "source_of_decision": "data/import_maps/corvette_2027/rpo_role_overlaps.csv"
            if rpo_overlap_present
            else "missing_optional_config",
            "notes": "Accepted overlaps are not permission to merge orderable and ref-only evidence.",
        },
        {
            "domain_key": "rule_inference",
            "disposition": "excluded",
            "reason": "This report does not infer dependency, exclusion, auto-add, or availability rules from raw text.",
            "source_of_decision": "pass_10_scope",
            "notes": "Future rule proposal work needs a separate explicit scope.",
        },
        {
            "domain_key": "package_logic",
            "disposition": "excluded",
            "reason": "Package membership and package behavior are outside the first proposal boundary.",
            "source_of_decision": "pass_10_scope",
            "notes": "No RPO business behavior is interpreted here.",
        },
        {
            "domain_key": "canonical_proposal_generation_in_this_pass",
            "disposition": "excluded",
            "reason": "Pass 10 is a report/gate only.",
            "source_of_decision": "pass_10_scope",
            "notes": "No proposed canonical rows or proposed output directories are written.",
        },
    ]


def narrow_scope_ready(included: list[dict[str, Any]], audit: dict[str, Any]) -> bool:
    required_ready = all(row.get("eligibility_status") == "eligible" for row in included)
    unresolved = audit.get("unresolved_rows_by_reason", {})
    has_unresolved = bool(unresolved) if isinstance(unresolved, dict) else False
    return required_ready and not has_unresolved


def readiness_explanation(audit: dict[str, Any], excluded: list[dict[str, Any]]) -> dict[str, Any]:
    snapshot = audit_snapshot(audit)
    reasons = snapshot["readiness_reasons"]
    if snapshot["canonical_proposal_ready"]:
        summary = "Global canonical proposal readiness is true in the audit snapshot."
    else:
        summary = (
            "Global canonical proposal readiness remains false in the audit snapshot. "
            "A narrower future proposal scope can still be defined when excluded/deferred domains are intentionally outside that scope."
        )
    return {
        "summary": summary,
        "audit_reasons": reasons,
        "excluded_or_deferred_domain_keys": [row["domain_key"] for row in excluded],
    }


def first_scope_recommendation() -> dict[str, list[str]]:
    return {
        "recommended_future_inputs": [
            "Standard Equipment primary variant matrix rows",
            "Interior primary variant matrix rows",
            "Exterior primary variant matrix rows",
            "Mechanical primary variant matrix rows",
            "Price Schedule as raw price evidence only",
            "Accepted RPO overlaps as separate evidence only",
        ],
        "explicit_exclusions": [
            "Color/Trim canonical import",
            "Equipment Groups as selectable source",
            "RPO overlap merging",
            "rule inference",
            "package logic",
            "canonical rule rows",
            "canonical auto-add rows",
            "canonical dependency rows",
            "canonical exclusive group rows",
        ],
    }


def build_report(staging_dir: Path, color_trim_scope_path: Path, rpo_role_overlaps_path: Path) -> dict[str, Any]:
    audit = load_audit_report(staging_dir)
    rpo_rows, rpo_audit_present = read_csv_if_present(staging_dir / "staging_audit_rpo_role_overlaps.csv")
    color_trim_scope_rows, color_trim_scope_present = read_csv_if_present(color_trim_scope_path)
    rpo_config_rows, rpo_config_present = read_csv_if_present(rpo_role_overlaps_path)
    included = included_domains(audit, rpo_rows)
    excluded = excluded_domains(audit, color_trim_scope_rows, color_trim_scope_present, rpo_config_rows, rpo_config_present)
    return {
        "audit_snapshot": audit_snapshot(audit),
        "config_inputs": {
            "color_trim_scope_config_present": color_trim_scope_present,
            "color_trim_scope_path": str(color_trim_scope_path),
            "color_trim_scope_review_status_counts": config_status(color_trim_scope_rows, "review_status"),
            "rpo_role_overlap_config_present": rpo_config_present,
            "rpo_role_overlap_path": str(rpo_role_overlaps_path),
            "rpo_role_overlap_review_status_counts": config_status(rpo_config_rows, "review_status"),
            "staging_audit_rpo_role_overlaps_present": rpo_audit_present,
        },
        "narrow_first_proposal_scope_ready": narrow_scope_ready(included, audit),
        "included_for_future_narrow_proposal": included,
        "excluded_or_deferred_domains": excluded,
        "first_proposal_scope_recommendation": first_scope_recommendation(),
        "why_global_canonical_ready_is_false": readiness_explanation(audit, excluded),
        "non_goals": [
            "no canonical proposal rows generated",
            "no staging mutation",
            "no parser changes",
            "no app/generator/workbook/output changes",
            "no RPO business-rule interpretation",
        ],
        "notes": [
            "This report is read-only over staging, audit, and config inputs.",
            "narrow_first_proposal_scope_ready does not override canonical_proposal_ready.",
            "Missing optional CSV/config inputs enrich less context but do not fail the report.",
        ],
    }


def markdown_cell(value: Any) -> str:
    if isinstance(value, (list, dict)):
        value = json.dumps(value, sort_keys=True)
    return clean(value).replace("\n", " ").replace("|", "\\|")


def markdown_table(headers: list[str], rows: list[dict[str, Any]]) -> str:
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    for row in rows:
        lines.append("| " + " | ".join(markdown_cell(row.get(header, "")) for header in headers) + " |")
    return "\n".join(lines)


def markdown_report(report: dict[str, Any]) -> str:
    snapshot = report["audit_snapshot"]
    scope = report["first_proposal_scope_recommendation"]
    explanation = report["why_global_canonical_ready_is_false"]
    included_headers = ["domain_key", "eligibility_status", "allowed_future_use", "source_files", "notes"]
    excluded_headers = ["domain_key", "disposition", "reason", "source_of_decision", "notes"]
    return f"""# Proposal Readiness Report

{REPORT_WARNING}

## Audit Snapshot

- primary_variant_matrix_ready: `{json.dumps(snapshot["primary_variant_matrix_ready"])}`
- color_trim_ready: `{json.dumps(snapshot["color_trim_ready"])}`
- pricing_ready: `{json.dumps(snapshot["pricing_ready"])}`
- equipment_groups_ready: `{json.dumps(snapshot["equipment_groups_ready"])}`
- rpo_role_overlaps_ready: `{json.dumps(snapshot["rpo_role_overlaps_ready"])}`
- canonical_proposal_ready: `{json.dumps(snapshot["canonical_proposal_ready"])}`
- ready_for_proposal_generation: `{json.dumps(snapshot["ready_for_proposal_generation"])}`
- narrow_first_proposal_scope_ready: `{json.dumps(report["narrow_first_proposal_scope_ready"])}`
- readiness_reasons: `{json.dumps(snapshot["readiness_reasons"], sort_keys=True)}`

## Included Future Proposal Inputs

{markdown_table(included_headers, report["included_for_future_narrow_proposal"])}

## Excluded Or Deferred Domains

{markdown_table(excluded_headers, report["excluded_or_deferred_domains"])}

## First Proposal Scope Recommendation

Recommended future inputs:
{chr(10).join(f"- {item}" for item in scope["recommended_future_inputs"])}

Explicit exclusions:
{chr(10).join(f"- {item}" for item in scope["explicit_exclusions"])}

## Why Global Canonical Readiness Can Remain False

{explanation["summary"]}

Audit reasons: `{json.dumps(explanation["audit_reasons"], sort_keys=True)}`

Excluded/deferred domains: `{json.dumps(explanation["excluded_or_deferred_domain_keys"], sort_keys=True)}`

## Non-Goals

{chr(10).join(f"- {item}" for item in report["non_goals"])}
"""


def write_reports(out_dir: Path, report: dict[str, Any]) -> None:
    write_json(out_dir / "proposal_readiness_report.json", report)
    write_text(out_dir / "proposal_readiness_report.md", markdown_report(report))


def main() -> int:
    args = parse_args()
    report = build_report(Path(args.staging), Path(args.color_trim_scope), Path(args.rpo_role_overlaps))
    write_reports(Path(args.out), report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
