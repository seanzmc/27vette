#!/usr/bin/env python3
"""Generate human review packets from order-guide staging audit output.

This script reads staging and audit evidence only. It does not parse raw
workbooks, mutate staging CSVs, update import maps, or generate canonical rows.
"""

from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_COLOR_TRIM_SCOPE = ROOT / "data" / "import_maps" / "corvette_2027" / "color_trim_scope.csv"
DEFAULT_RPO_ROLE_OVERLAPS = ROOT / "data" / "import_maps" / "corvette_2027" / "rpo_role_overlaps.csv"

AUDIT_PREREQUISITE_MESSAGE = "Run scripts/audit_order_guide_staging.py before generating the review packet."
SOURCE_OF_TRUTH_WARNING = (
    "Do not edit this generated review packet as source of truth. "
    "Transfer approved decisions into data/import_maps/corvette_2027/*.csv."
)

COLOR_TRIM_DECISION_OPTIONS = "approved|accepted_review_only|deferred|needs_review"
RPO_OVERLAP_DECISION_OPTIONS = "approved|accepted_expected_overlap|deferred|needs_review"

COLOR_TRIM_HEADERS = [
    "source_sheet",
    "section_role",
    "section_index",
    "start_row",
    "end_row",
    "guide_family",
    "observed_model_key",
    "scope_type",
    "row_count",
    "sample_interior_rpos",
    "sample_exterior_colors",
    "current_review_status",
    "current_model_key",
    "current_confidence",
    "recommended_decision_options",
    "notes",
]

RPO_OVERLAP_HEADERS = [
    "rpo",
    "orderable_count",
    "ref_only_count",
    "source_sheets",
    "model_keys",
    "section_families",
    "sample_descriptions",
    "current_review_status",
    "current_classification",
    "current_canonical_handling",
    "current_recommended_action",
    "recommended_decision_options",
    "notes",
]


def clean(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--staging", required=True, help="Directory containing staging and audit output.")
    parser.add_argument("--out", required=True, help="Directory where review packet files should be written.")
    parser.add_argument(
        "--color-trim-scope",
        default=str(DEFAULT_COLOR_TRIM_SCOPE),
        help="Optional Color/Trim scope decision map to show current review status.",
    )
    parser.add_argument(
        "--rpo-role-overlaps",
        default=str(DEFAULT_RPO_ROLE_OVERLAPS),
        help="Optional RPO role-overlap decision map to show current review status.",
    )
    return parser.parse_args()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def read_csv_if_present(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    return read_csv(path)


def write_csv(path: Path, headers: list[str], rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=headers, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({header: clean(row.get(header, "")) for header in headers})


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def load_required_audit(staging_dir: Path) -> tuple[dict[str, Any], list[dict[str, str]]]:
    if not staging_dir.exists() or not staging_dir.is_dir():
        raise SystemExit(f"Staging directory does not exist: {staging_dir}")

    required = [
        staging_dir / "staging_audit_report.json",
        staging_dir / "staging_audit_rpo_role_overlaps.csv",
    ]
    missing = [path.name for path in required if not path.exists()]
    if missing:
        raise SystemExit(f"{AUDIT_PREREQUISITE_MESSAGE} Missing required audit file(s): {', '.join(missing)}")

    try:
        audit_report = json.loads((staging_dir / "staging_audit_report.json").read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Malformed staging_audit_report.json: {exc}") from exc

    return audit_report, read_csv(staging_dir / "staging_audit_rpo_role_overlaps.csv")


def unique_values(rows: list[dict[str, str]], *fields: str, limit: int = 8) -> str:
    values: list[str] = []
    seen: set[str] = set()
    for row in rows:
        for field in fields:
            value = clean(row.get(field, ""))
            if not value or value in seen:
                continue
            values.append(value)
            seen.add(value)
            break
        if len(values) >= limit:
            break
    return " | ".join(values)


def load_scope_decisions(path: Path) -> dict[tuple[str, str], dict[str, str]]:
    rows = read_csv_if_present(path)
    return {(clean(row.get("sheet_name", "")), clean(row.get("section_role", ""))): row for row in rows}


def load_rpo_decisions(path: Path) -> dict[str, dict[str, str]]:
    rows = read_csv_if_present(path)
    return {clean(row.get("rpo", "")): row for row in rows if clean(row.get("rpo", ""))}


def section_int(row: dict[str, str], field: str) -> int:
    try:
        return int(clean(row.get(field, "")) or 0)
    except ValueError:
        return 0


def color_trim_rows(staging_dir: Path, color_trim_scope_path: Path) -> list[dict[str, Any]]:
    sections = [
        row
        for row in read_csv_if_present(staging_dir / "staging_sheet_sections.csv")
        if clean(row.get("section_role", "")).startswith("color_trim_")
    ]
    interior_by_sheet: dict[str, list[dict[str, str]]] = defaultdict(list)
    compatibility_by_sheet: dict[str, list[dict[str, str]]] = defaultdict(list)
    disclosure_by_sheet: dict[str, list[dict[str, str]]] = defaultdict(list)

    for row in read_csv_if_present(staging_dir / "staging_color_trim_interior_rows.csv"):
        interior_by_sheet[clean(row.get("source_sheet", ""))].append(row)
    for row in read_csv_if_present(staging_dir / "staging_color_trim_compatibility_rows.csv"):
        compatibility_by_sheet[clean(row.get("source_sheet", ""))].append(row)
    for row in read_csv_if_present(staging_dir / "staging_color_trim_disclosures.csv"):
        disclosure_by_sheet[clean(row.get("source_sheet", ""))].append(row)

    decisions = load_scope_decisions(color_trim_scope_path)
    rows_out: list[dict[str, Any]] = []
    for section in sections:
        sheet = clean(section.get("source_sheet", ""))
        section_role = clean(section.get("section_role", ""))
        decision = decisions.get((sheet, section_role), {})
        if section_role == "color_trim_interior_matrix":
            evidence_rows = interior_by_sheet.get(sheet, [])
        elif section_role == "color_trim_compatibility_matrix":
            evidence_rows = compatibility_by_sheet.get(sheet, [])
        elif section_role == "color_trim_disclosure":
            evidence_rows = disclosure_by_sheet.get(sheet, [])
        else:
            evidence_rows = []

        rows_out.append(
            {
                "source_sheet": sheet,
                "section_role": section_role,
                "section_index": clean(section.get("section_index", "")),
                "start_row": clean(section.get("start_row", "")),
                "end_row": clean(section.get("end_row", "")),
                "guide_family": clean(section.get("guide_family", "")),
                "observed_model_key": clean(section.get("model_key", "")),
                "scope_type": clean(section.get("scope_type", "")),
                "row_count": len(evidence_rows),
                "sample_interior_rpos": unique_values(
                    interior_by_sheet.get(sheet, []),
                    "interior_rpo",
                    "interior_rpo_raw",
                ),
                "sample_exterior_colors": unique_values(
                    compatibility_by_sheet.get(sheet, []),
                    "exterior_color_name",
                    "exterior_color_name_raw",
                ),
                "current_review_status": clean(decision.get("review_status", "")) or "needs_review",
                "current_model_key": clean(decision.get("model_key", "")),
                "current_confidence": clean(decision.get("confidence", "")),
                "recommended_decision_options": COLOR_TRIM_DECISION_OPTIONS,
                "notes": clean(decision.get("notes", "")) or "No explicit scope decision map row found for this section.",
            }
        )
    return sorted(
        rows_out,
        key=lambda row: (
            clean(row["source_sheet"]),
            section_int({"section_index": clean(row["section_index"])}, "section_index"),
            clean(row["section_role"]),
        ),
    )


def rpo_overlap_rows(audit_overlap_rows: list[dict[str, str]], rpo_decision_path: Path) -> list[dict[str, Any]]:
    decisions = load_rpo_decisions(rpo_decision_path)
    rows_out: list[dict[str, Any]] = []
    for row in audit_overlap_rows:
        rpo = clean(row.get("rpo", ""))
        decision = decisions.get(rpo, {})
        rows_out.append(
            {
                "rpo": rpo,
                "orderable_count": clean(row.get("orderable_count", "")),
                "ref_only_count": clean(row.get("ref_only_count", "")),
                "source_sheets": clean(row.get("source_sheets", "")),
                "model_keys": clean(row.get("model_keys", "")),
                "section_families": clean(row.get("section_families", "")),
                "sample_descriptions": clean(row.get("sample_descriptions", "")),
                "current_review_status": clean(decision.get("review_status", ""))
                or clean(row.get("decision_review_status", ""))
                or "needs_review",
                "current_classification": clean(decision.get("classification", ""))
                or clean(row.get("decision_classification", "")),
                "current_canonical_handling": clean(decision.get("canonical_handling", ""))
                or clean(row.get("decision_canonical_handling", "")),
                "current_recommended_action": clean(decision.get("recommended_action", ""))
                or clean(row.get("decision_recommended_action", ""))
                or clean(row.get("recommended_action", "")),
                "recommended_decision_options": RPO_OVERLAP_DECISION_OPTIONS,
                "notes": clean(decision.get("notes", "")) or clean(row.get("decision_notes", "")),
            }
        )
    return sorted(rows_out, key=lambda row: clean(row["rpo"]))


def markdown_cell(value: Any) -> str:
    return clean(value).replace("\n", " ").replace("|", "\\|")


def markdown_table(headers: list[str], rows: list[dict[str, Any]], limit: int = 20) -> str:
    capped = rows[:limit]
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    for row in capped:
        lines.append("| " + " | ".join(markdown_cell(row.get(header, "")) for header in headers) + " |")
    if len(rows) > limit:
        lines.append(f"\nShowing {limit} of {len(rows)} rows. The CSV is the complete review surface.")
    else:
        lines.append("\nThe CSV is the complete review surface.")
    return "\n".join(lines)


def readiness_snapshot(audit_report: dict[str, Any]) -> list[tuple[str, Any]]:
    readiness = audit_report.get("readiness", {}) if isinstance(audit_report.get("readiness", {}), dict) else {}
    rpo_decisions = (
        audit_report.get("rpo_role_overlap_decisions", {})
        if isinstance(audit_report.get("rpo_role_overlap_decisions", {}), dict)
        else {}
    )
    color_trim_scope = (
        audit_report.get("color_trim_scope_review", {})
        if isinstance(audit_report.get("color_trim_scope_review", {}), dict)
        else {}
    )
    return [
        ("primary_variant_matrix_ready", readiness.get("primary_variant_matrix_ready", "")),
        ("color_trim_ready", readiness.get("color_trim_ready", "")),
        ("pricing_ready", readiness.get("pricing_ready", "")),
        ("equipment_groups_ready", readiness.get("equipment_groups_ready", "")),
        ("rpo_role_overlaps_ready", readiness.get("rpo_role_overlaps_ready", "")),
        ("canonical_proposal_ready", readiness.get("canonical_proposal_ready", "")),
        ("color_trim_review_status_counts", color_trim_scope.get("review_status_counts", {})),
        ("resolved_overlap_count", rpo_decisions.get("resolved_overlap_count", "")),
        ("mapped_overlap_count", rpo_decisions.get("mapped_overlap_count", "")),
        ("observed_overlap_count", rpo_decisions.get("observed_overlap_count", "")),
    ]


def write_color_trim_markdown(path: Path, audit_report: dict[str, Any], rows: list[dict[str, Any]]) -> None:
    snapshot = "\n".join(f"- {key}: `{json.dumps(value, sort_keys=True)}`" for key, value in readiness_snapshot(audit_report))
    table_headers = [
        "source_sheet",
        "section_role",
        "section_index",
        "start_row",
        "end_row",
        "row_count",
        "sample_interior_rpos",
        "sample_exterior_colors",
        "current_review_status",
    ]
    content = f"""# Color/Trim Scope Review

{SOURCE_OF_TRUTH_WARNING}

This review packet is generated evidence only. It does not update staging CSVs, import maps, or canonical CSVs.

## Readiness Snapshot

{snapshot}

## Decision Options

- `approved`: eligible for later canonical proposal work.
- `accepted_review_only`: intentionally retained as evidence, not canonical import-ready.
- `deferred`: known not ready yet.
- `needs_review`: unresolved.

## Review Rows

{markdown_table(table_headers, rows)}
"""
    write_text(path, content)


def write_rpo_markdown(path: Path, audit_report: dict[str, Any], rows: list[dict[str, Any]]) -> None:
    snapshot = "\n".join(f"- {key}: `{json.dumps(value, sort_keys=True)}`" for key, value in readiness_snapshot(audit_report))
    table_headers = [
        "rpo",
        "orderable_count",
        "ref_only_count",
        "source_sheets",
        "model_keys",
        "section_families",
        "sample_descriptions",
        "current_review_status",
        "current_canonical_handling",
    ]
    content = f"""# RPO Role-Overlap Review

{SOURCE_OF_TRUTH_WARNING}

This review packet is generated evidence only. It does not update staging CSVs, import maps, or canonical CSVs.

## Readiness Snapshot

{snapshot}

## Decision Options

- `approved`: explicitly reviewed and eligible for later proposal handling.
- `accepted_expected_overlap`: explicitly accepted as expected orderable/ref-only overlap.
- `deferred`: known not ready yet.
- `needs_review`: unresolved.

## Review Rows

{markdown_table(table_headers, rows)}
"""
    write_text(path, content)


def generate_review_packet(staging_dir: Path, out_dir: Path, color_trim_scope_path: Path, rpo_decision_path: Path) -> None:
    audit_report, audit_overlap_rows = load_required_audit(staging_dir)
    color_rows = color_trim_rows(staging_dir, color_trim_scope_path)
    rpo_rows = rpo_overlap_rows(audit_overlap_rows, rpo_decision_path)

    out_dir.mkdir(parents=True, exist_ok=True)
    write_csv(out_dir / "color_trim_scope_review.csv", COLOR_TRIM_HEADERS, color_rows)
    write_csv(out_dir / "rpo_role_overlap_review.csv", RPO_OVERLAP_HEADERS, rpo_rows)
    write_color_trim_markdown(out_dir / "color_trim_scope_review.md", audit_report, color_rows)
    write_rpo_markdown(out_dir / "rpo_role_overlap_review.md", audit_report, rpo_rows)


def main() -> int:
    args = parse_args()
    generate_review_packet(Path(args.staging), Path(args.out), Path(args.color_trim_scope), Path(args.rpo_role_overlaps))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
