#!/usr/bin/env python3
"""Audit staged Chevrolet order guide evidence without generating canonical rows."""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


REQUIRED_FILES = {
    "sheets": "staging_sheets.csv",
    "variants": "staging_variants.csv",
    "variant_matrix_rows": "staging_variant_matrix_rows.csv",
    "status_symbols": "staging_status_symbols.csv",
    "unresolved_rows": "staging_unresolved_rows.csv",
    "ignored_rows": "staging_ignored_rows.csv",
}

OPTIONAL_FILES = {
    "sheet_sections": "staging_sheet_sections.csv",
    "color_trim_interior_rows": "staging_color_trim_interior_rows.csv",
    "color_trim_compatibility_rows": "staging_color_trim_compatibility_rows.csv",
    "color_trim_disclosures": "staging_color_trim_disclosures.csv",
    "equipment_group_rows": "staging_equipment_group_rows.csv",
    "price_rows": "staging_price_rows.csv",
    "rule_phrase_candidates": "staging_rule_phrase_candidates.csv",
}

AUDIT_CSV_HEADERS = {
    "model_key_counts": ["staging_file", "source_sheet", "model_key", "model_key_confidence", "count"],
    "status_counts": ["source_sheet", "sheet_family", "status_context", "status_symbol", "canonical_status", "count"],
    "rpo_counts": ["staging_file", "source_sheet", "model_key", "section_family", "rpo_kind", "rpo", "count"],
    "footnote_counts": ["staging_file", "source_sheet", "model_key", "footnote_scope", "footnote_refs", "count"],
    "suspicious_rows": ["source", "source_sheet", "source_row", "model_key", "severity", "reason", "raw_values"],
}


def clean(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--staging", required=True, help="Directory containing staging CSVs and import_report.json.")
    parser.add_argument("--out", required=True, help="Path to write staging_audit_report.json.")
    return parser.parse_args()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


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


def load_staging(staging_dir: Path) -> tuple[dict[str, list[dict[str, str]]], dict[str, Any], list[str], list[str]]:
    if not staging_dir.exists() or not staging_dir.is_dir():
        raise SystemExit(f"Staging directory does not exist: {staging_dir}")

    missing_required = [filename for filename in REQUIRED_FILES.values() if not (staging_dir / filename).exists()]
    if missing_required:
        raise SystemExit(f"Missing required staging file(s): {', '.join(sorted(missing_required))}")

    report_path = staging_dir / "import_report.json"
    if not report_path.exists():
        raise SystemExit("Missing required staging file: import_report.json")

    staging: dict[str, list[dict[str, str]]] = {}
    present_optional: list[str] = []
    missing_optional: list[str] = []

    for key, filename in REQUIRED_FILES.items():
        staging[key] = read_csv(staging_dir / filename)
    for key, filename in OPTIONAL_FILES.items():
        path = staging_dir / filename
        if path.exists():
            staging[key] = read_csv(path)
            present_optional.append(filename)
        else:
            staging[key] = []
            missing_optional.append(filename)

    try:
        import_report = json.loads(report_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Malformed import_report.json: {exc}") from exc

    return staging, import_report, sorted(present_optional), sorted(missing_optional)


def sheet_family_map(sheets: list[dict[str, str]]) -> dict[str, str]:
    return {row.get("sheet_name", ""): row.get("section_family", "") or row.get("sheet_role", "") for row in sheets}


def count_rows_by_file_and_sheet(staging: dict[str, list[dict[str, str]]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for name, rows in sorted(staging.items()):
        by_sheet = Counter(row.get("source_sheet", row.get("sheet_name", "")) or "<blank>" for row in rows)
        result[name] = {
            "total_rows": len(rows),
            "by_source_sheet": dict(sorted(by_sheet.items())),
        }
    return result


def model_key_counts(staging: dict[str, list[dict[str, str]]]) -> list[dict[str, Any]]:
    rows_out = []
    for name, rows in sorted(staging.items()):
        for (source_sheet, model_key, confidence), count in sorted(
            Counter(
                (
                    row.get("source_sheet", row.get("sheet_name", "")) or "<blank>",
                    row.get("model_key", "") or "<blank>",
                    row.get("model_key_confidence", "") or "<blank>",
                )
                for row in rows
                if "model_key" in row
            ).items()
        ):
            rows_out.append(
                {
                    "staging_file": name,
                    "source_sheet": source_sheet,
                    "model_key": model_key,
                    "model_key_confidence": confidence,
                    "count": count,
                }
            )
    return sorted(rows_out, key=lambda row: (row["staging_file"], row["source_sheet"], row["model_key"], row["model_key_confidence"]))


def variant_columns(variants: list[dict[str, str]]) -> dict[str, list[dict[str, str]]]:
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in variants:
        grouped[row.get("source_sheet", "")].append(
            {
                "model_key": row.get("model_key", ""),
                "body_code": row.get("body_code", ""),
                "body_style": row.get("body_style", ""),
                "trim_level": row.get("trim_level", ""),
                "variant_label": row.get("variant_label", ""),
                "confidence": row.get("confidence", ""),
            }
        )
    return {
        sheet: sorted(rows, key=lambda row: (row["model_key"], row["body_code"], row["trim_level"], row["variant_label"]))
        for sheet, rows in sorted(grouped.items())
    }


def status_counts(staging: dict[str, list[dict[str, str]]], families: dict[str, str]) -> list[dict[str, Any]]:
    counts: Counter[tuple[str, str, str, str, str]] = Counter()
    for row in staging["status_symbols"]:
        source_sheet = row.get("source_sheet", "")
        count = int(row.get("count", "0") or 0)
        counts[
            (
                source_sheet,
                families.get(source_sheet, ""),
                row.get("status_context", ""),
                row.get("status_symbol", ""),
                row.get("canonical_status", ""),
            )
        ] += count
    for file_name in ["variant_matrix_rows", "color_trim_compatibility_rows"]:
        for row in staging.get(file_name, []):
            symbol = row.get("status_symbol", "")
            if not symbol:
                continue
            source_sheet = row.get("source_sheet", "")
            counts[(source_sheet, families.get(source_sheet, ""), file_name, symbol, row.get("canonical_status", ""))] += 1
    return [
        {
            "source_sheet": source_sheet,
            "sheet_family": sheet_family,
            "status_context": context,
            "status_symbol": symbol,
            "canonical_status": canonical,
            "count": count,
        }
        for (source_sheet, sheet_family, context, symbol, canonical), count in sorted(counts.items())
    ]


def rpo_counts(staging: dict[str, list[dict[str, str]]]) -> list[dict[str, Any]]:
    specs = [
        ("variant_matrix_rows", "orderable_rpo", "orderable"),
        ("variant_matrix_rows", "ref_rpo", "ref_only"),
        ("equipment_group_rows", "orderable_rpo", "equipment_group_orderable"),
        ("equipment_group_rows", "ref_rpo", "equipment_group_ref_only"),
        ("color_trim_interior_rows", "interior_rpo", "interior_rpo"),
        ("color_trim_compatibility_rows", "exterior_color_rpo", "exterior_color_rpo"),
    ]
    counts: Counter[tuple[str, str, str, str, str, str]] = Counter()
    for file_name, field_name, rpo_kind in specs:
        for row in staging.get(file_name, []):
            rpo = row.get(field_name, "")
            if not rpo:
                continue
            counts[
                (
                    file_name,
                    row.get("source_sheet", ""),
                    row.get("model_key", "") or "<blank>",
                    row.get("section_family", ""),
                    rpo_kind,
                    rpo,
                )
            ] += 1
    return [
        {
            "staging_file": file_name,
            "source_sheet": source_sheet,
            "model_key": model_key,
            "section_family": section_family,
            "rpo_kind": rpo_kind,
            "rpo": rpo,
            "count": count,
        }
        for (file_name, source_sheet, model_key, section_family, rpo_kind, rpo), count in sorted(counts.items())
    ]


def footnote_counts(staging: dict[str, list[dict[str, str]]]) -> list[dict[str, Any]]:
    specs = [
        ("variant_matrix_rows", "footnote_scope", "footnote_refs", "status_cell"),
        ("color_trim_interior_rows", "footnote_scope", "footnote_refs", ""),
        ("color_trim_compatibility_rows", "footnote_scope", "footnote_refs", "compatibility_status_cell"),
        ("color_trim_compatibility_rows", "interior_footnote_scope", "interior_footnote_refs", ""),
    ]
    counts: Counter[tuple[str, str, str, str, str]] = Counter()
    for file_name, scope_field, refs_field, fallback_scope in specs:
        for row in staging.get(file_name, []):
            refs = row.get(refs_field, "")
            if not refs:
                continue
            scope = row.get(scope_field, "") or fallback_scope
            for ref in refs.split("|"):
                if ref:
                    counts[
                        (
                            file_name,
                            row.get("source_sheet", ""),
                            row.get("model_key", "") or "<blank>",
                            scope,
                            ref,
                        )
                    ] += 1
    return [
        {
            "staging_file": file_name,
            "source_sheet": source_sheet,
            "model_key": model_key,
            "footnote_scope": scope,
            "footnote_refs": refs,
            "count": count,
        }
        for (file_name, source_sheet, model_key, scope, refs), count in sorted(counts.items())
    ]


def duplicate_variant_rows(rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    counts: Counter[tuple[str, str, str, str, str, str, str, str]] = Counter()
    examples: dict[tuple[str, str, str, str, str, str, str, str], dict[str, str]] = {}
    for row in rows:
        key = (
            row.get("source_sheet", ""),
            row.get("model_key", ""),
            row.get("variant_id", ""),
            row.get("orderable_rpo", ""),
            row.get("ref_rpo", ""),
            row.get("description", ""),
            row.get("raw_status", ""),
            row.get("source_row", ""),
        )
        counts[key] += 1
        examples.setdefault(key, row)
    suspicious = []
    for key, count in sorted(counts.items()):
        if count < 2:
            continue
        row = examples[key]
        suspicious.append(
            {
                "source": "variant_matrix_rows",
                "source_sheet": row.get("source_sheet", ""),
                "source_row": row.get("source_row", ""),
                "model_key": row.get("model_key", ""),
                "severity": "review",
                "reason": "duplicate_variant_matrix_evidence",
                "raw_values": json.dumps({"count": count, "key": key}, separators=(",", ":")),
            }
        )
    return suspicious


def suspicious_rows(staging: dict[str, list[dict[str, str]]]) -> list[dict[str, Any]]:
    rows_out: list[dict[str, Any]] = []
    rows_out.extend(duplicate_variant_rows(staging["variant_matrix_rows"]))

    orderable = {row["rpo"] for row in rpo_counts(staging) if row["rpo_kind"] == "orderable"}
    ref_only = {row["rpo"] for row in rpo_counts(staging) if row["rpo_kind"] == "ref_only"}
    for rpo in sorted(orderable & ref_only):
        rows_out.append(
            {
                "source": "rpo_counts",
                "source_sheet": "",
                "source_row": "",
                "model_key": "",
                "severity": "review",
                "reason": "rpo_appears_as_orderable_and_ref_only",
                "raw_values": rpo,
            }
        )

    for row in staging["variant_matrix_rows"]:
        if row.get("model_key_confidence") == "needs_review" or (row.get("body_code") and not row.get("model_key")):
            rows_out.append(
                {
                    "source": "variant_matrix_rows",
                    "source_sheet": row.get("source_sheet", ""),
                    "source_row": row.get("source_row", ""),
                    "model_key": row.get("model_key", ""),
                    "severity": "review",
                    "reason": "variant_model_key_needs_review",
                    "raw_values": json.dumps({key: row.get(key, "") for key in ["body_code", "variant_id", "description"]}, separators=(",", ":")),
                }
            )

    for row in staging.get("color_trim_interior_rows", []):
        if row.get("model_key_confidence") == "needs_review":
            rows_out.append(
                {
                    "source": "color_trim_interior_rows",
                    "source_sheet": row.get("source_sheet", ""),
                    "source_row": row.get("source_row", ""),
                    "model_key": row.get("model_key", ""),
                    "severity": "info",
                    "reason": "color_trim_model_key_ambiguous",
                    "raw_values": row.get("source_detail_raw", ""),
                }
            )

    for row in staging["unresolved_rows"]:
        rows_out.append(
            {
                "source": "unresolved_rows",
                "source_sheet": row.get("source_sheet", ""),
                "source_row": row.get("source_row", ""),
                "model_key": row.get("model_key", ""),
                "severity": "review",
                "reason": row.get("reason", "unresolved_row"),
                "raw_values": row.get("raw_values", ""),
            }
        )

    return sorted(rows_out, key=lambda row: (row["source_sheet"], row["model_key"], row["source_row"], row["reason"], row["source"]))


def equipment_group_audit(staging: dict[str, list[dict[str, str]]]) -> dict[str, Any]:
    leaked_primary_rows = [row for row in staging["variant_matrix_rows"] if "Equipment Groups" in row.get("source_sheet", "")]
    rows = staging.get("equipment_group_rows", [])
    match_counts = Counter(row.get("match_status", "") or "<blank>" for row in rows)
    return {
        "row_count": len(rows),
        "match_status_counts": dict(sorted(match_counts.items())),
        "variant_matrix_leak_count": len(leaked_primary_rows),
        "cross_check_only": len(leaked_primary_rows) == 0,
    }


def color_trim_audit(staging: dict[str, list[dict[str, str]]]) -> dict[str, Any]:
    sections = staging.get("sheet_sections", [])
    section_counts = Counter(row.get("section_role", "") for row in sections if row.get("source_sheet", "").startswith("Color and Trim"))
    return {
        "section_role_counts": dict(sorted(section_counts.items())),
        "interior_row_count": len(staging.get("color_trim_interior_rows", [])),
        "compatibility_row_count": len(staging.get("color_trim_compatibility_rows", [])),
        "disclosure_row_count": len(staging.get("color_trim_disclosures", [])),
        "has_interior_and_compatibility_rows": bool(staging.get("color_trim_interior_rows")) and bool(staging.get("color_trim_compatibility_rows")),
    }


def readiness(suspicious: list[dict[str, Any]], staging: dict[str, list[dict[str, str]]]) -> dict[str, Any]:
    reasons = []
    if staging["unresolved_rows"]:
        reasons.append("unresolved_rows_present")
    review_suspicious = [row for row in suspicious if row.get("severity") == "review"]
    if review_suspicious:
        reasons.append("suspicious_review_rows_present")
    if not equipment_group_audit(staging)["cross_check_only"]:
        reasons.append("equipment_groups_leaked_to_primary_variant_rows")
    if staging.get("color_trim_interior_rows") and not staging.get("color_trim_compatibility_rows"):
        reasons.append("color_trim_compatibility_rows_missing")
    return {
        "ready_for_proposal_generation": not reasons,
        "advisory_only": True,
        "reasons": sorted(set(reasons)),
    }


def build_audit(staging_dir: Path) -> tuple[dict[str, Any], dict[str, list[dict[str, Any]]]]:
    staging, import_report, present_optional, missing_optional = load_staging(staging_dir)
    families = sheet_family_map(staging["sheets"])
    model_rows = model_key_counts(staging)
    status_rows = status_counts(staging, families)
    rpo_rows = rpo_counts(staging)
    footnote_rows = footnote_counts(staging)
    suspicious = suspicious_rows(staging)
    audit = {
        "staging_dir": str(staging_dir),
        "inputs": {
            "required_files": sorted(REQUIRED_FILES.values()) + ["import_report.json"],
            "optional_files_present": present_optional,
            "optional_files_missing": missing_optional,
        },
        "row_counts": count_rows_by_file_and_sheet(staging),
        "model_key_counts": model_rows,
        "variant_columns_by_sheet": variant_columns(staging["variants"]),
        "status_counts": status_rows,
        "rpo_counts": rpo_rows,
        "footnote_counts": footnote_rows,
        "ignored_rows_by_reason": dict(sorted(Counter(row.get("reason", "") for row in staging["ignored_rows"]).items())),
        "unresolved_rows_by_reason": dict(sorted(Counter(row.get("reason", "") for row in staging["unresolved_rows"]).items())),
        "equipment_groups": equipment_group_audit(staging),
        "color_trim": color_trim_audit(staging),
        "suspicious_row_count": len(suspicious),
        "readiness": readiness(suspicious, staging),
        "source_import_report_summary": {
            key: import_report.get(key)
            for key in [
                "row_counts",
                "section_role_counts",
                "model_key_counts_by_staging_file",
                "model_key_confidence_counts_by_staging_file",
                "unresolved_rows_by_reason",
                "ignored_rows_by_reason",
            ]
            if key in import_report
        },
        "notes": [
            "Audit output is advisory review metadata only.",
            "Suspicious rows do not cause a nonzero exit.",
            "No canonical proposal rows are generated.",
            "Staging CSVs are read only and are not modified or normalized.",
        ],
    }
    csvs = {
        "model_key_counts": model_rows,
        "status_counts": status_rows,
        "rpo_counts": rpo_rows,
        "footnote_counts": footnote_rows,
        "suspicious_rows": suspicious,
    }
    return audit, csvs


def main() -> int:
    args = parse_args()
    out_path = Path(args.out)
    audit, csvs = build_audit(Path(args.staging))
    write_json(out_path, audit)
    out_dir = out_path.parent
    for name, rows in csvs.items():
        write_csv(out_dir / f"staging_audit_{name}.csv", AUDIT_CSV_HEADERS[name], rows)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
