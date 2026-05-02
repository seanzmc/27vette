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
    "suspicious_rows": [
        "source",
        "source_sheet",
        "source_row",
        "model_key",
        "severity",
        "reason",
        "raw_values",
        "suspicion_type",
        "review_bucket",
        "recommended_action",
        "section_family",
        "rpo",
        "raw_value",
        "classification_reason",
        "readiness_impact",
    ],
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
            for scope, ref in iter_footnote_pairs(row.get(scope_field, ""), row.get(refs_field, ""), fallback_scope):
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


def iter_footnote_pairs(scope_value: str, refs_value: str, fallback_scope: str) -> list[tuple[str, str]]:
    refs = [ref for ref in clean(refs_value).split("|") if ref]
    if not refs:
        return []
    scopes = [scope for scope in clean(scope_value).split("|") if scope]
    if not scopes:
        scopes = [fallback_scope]
    if len(scopes) == len(refs):
        return list(zip(scopes, refs))
    if len(scopes) == 1:
        return [(scopes[0], ref) for ref in refs]
    return [("|".join(scopes), ref) for ref in refs]


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


def classify_suspicious_rows(rows: list[dict[str, Any]], families: dict[str, str]) -> list[dict[str, Any]]:
    classified = [classify_suspicious_row(row, families) for row in rows]
    return sorted(
        classified,
        key=lambda row: (
            row.get("source_sheet", ""),
            row.get("model_key", ""),
            row.get("section_family", ""),
            row.get("source_row", ""),
            row.get("rpo", ""),
            row.get("raw_value", ""),
            row.get("reason", ""),
            row.get("source", ""),
        ),
    )


def classify_suspicious_row(row: dict[str, Any], families: dict[str, str]) -> dict[str, Any]:
    reason = clean(row.get("reason", ""))
    source = clean(row.get("source", ""))
    source_sheet = clean(row.get("source_sheet", ""))
    raw_values = clean(row.get("raw_values", ""))
    section_family = families.get(source_sheet, "")
    rpo = raw_values if reason == "rpo_appears_as_orderable_and_ref_only" else ""
    raw_value = raw_values
    classification = {
        "suspicion_type": "unclassified_suspicion",
        "review_bucket": "canonical_review_required",
        "recommended_action": "review_before_proposal_generation",
        "classification_reason": "No specific audit classification matched; preserve for human review.",
        "readiness_impact": "review_required",
    }
    if reason == "color_trim_model_key_ambiguous" or source.startswith("color_trim_"):
        classification = {
            "suspicion_type": "model_scope_ambiguous",
            "review_bucket": "color_trim_review_only",
            "recommended_action": "confirm_model_scope_or_import_map; do_not_variant_expand",
            "classification_reason": "Color/Trim rows are model-scoped evidence; ambiguous model_key remains visible until explicitly mapped or accepted.",
            "readiness_impact": "review_required",
        }
    elif reason == "rpo_appears_as_orderable_and_ref_only":
        classification = {
            "suspicion_type": "rpo_role_overlap",
            "review_bucket": "canonical_review_required",
            "recommended_action": "review_orderable_vs_reference_usage_before_proposal",
            "classification_reason": "The same raw RPO appears in both orderable and reference-only staging evidence.",
            "readiness_impact": "review_required",
        }
    elif "equipment_group" in reason or "Equipment Groups" in source_sheet:
        classification = {
            "suspicion_type": "derived_equipment_crosscheck",
            "review_bucket": "equipment_group_crosscheck_only",
            "recommended_action": "keep_as_cross_check; do_not_promote_to_selectable",
            "classification_reason": "Equipment Groups are derived/cross-check evidence in this importer pass.",
            "readiness_impact": "advisory",
        }
    elif reason == "variant_model_key_needs_review":
        classification = {
            "suspicion_type": "model_key_unresolved",
            "review_bucket": "import_map_gap",
            "recommended_action": "review_variant_header_body_code_mapping",
            "classification_reason": "Variant-scoped evidence lacks a resolved model_key and may need an import-map update.",
            "readiness_impact": "blocking",
        }
    elif source == "unresolved_rows":
        classification = {
            "suspicion_type": "unresolved_staging_evidence",
            "review_bucket": "import_map_gap",
            "recommended_action": "classify_source_row_or_add_safe_ignore_reason",
            "classification_reason": "A meaningful nonblank staging row could not be safely classified.",
            "readiness_impact": "review_required",
        }
    elif source.startswith("price"):
        classification = {
            "suspicion_type": "price_evidence_review",
            "review_bucket": "price_schedule_review_only",
            "recommended_action": "review_price_source_evidence_before_pricing_proposal",
            "classification_reason": "Price schedule evidence is staging-only and should be reviewed separately.",
            "readiness_impact": "review_required",
        }
    return {
        **row,
        **classification,
        "section_family": section_family,
        "rpo": rpo,
        "raw_value": raw_value,
    }


def counter_by(rows: list[dict[str, Any]], field_name: str) -> dict[str, int]:
    return dict(sorted(Counter(clean(row.get(field_name, "")) or "<blank>" for row in rows).items()))


def recommended_actions_by_bucket(rows: list[dict[str, Any]]) -> dict[str, dict[str, int]]:
    result: dict[str, Counter[str]] = defaultdict(Counter)
    for row in rows:
        result[clean(row.get("review_bucket", "")) or "<blank>"][clean(row.get("recommended_action", "")) or "<blank>"] += 1
    return {bucket: dict(sorted(actions.items())) for bucket, actions in sorted(result.items())}


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


def domain_readiness(suspicious: list[dict[str, Any]], staging: dict[str, list[dict[str, str]]]) -> dict[str, Any]:
    blocking_impacts = {"blocking", "review_required"}
    primary_blockers = [
        row
        for row in suspicious
        if row.get("review_bucket") == "import_map_gap"
        and row.get("readiness_impact") in blocking_impacts
        and row.get("source") in {"variant_matrix_rows", "unresolved_rows"}
    ]
    color_trim_blockers = [
        row
        for row in suspicious
        if row.get("review_bucket") == "color_trim_review_only" and row.get("readiness_impact") in blocking_impacts
    ]
    pricing_blockers = [
        row
        for row in suspicious
        if row.get("review_bucket") == "price_schedule_review_only" and row.get("readiness_impact") in blocking_impacts
    ]
    equipment_group_summary = equipment_group_audit(staging)
    equipment_group_blockers = [
        row
        for row in suspicious
        if row.get("review_bucket") == "equipment_group_crosscheck_only" and row.get("readiness_impact") == "blocking"
    ]
    canonical_blockers = [row for row in suspicious if row.get("readiness_impact") in blocking_impacts]
    return {
        "primary_variant_matrix_ready": not primary_blockers,
        "color_trim_ready": not color_trim_blockers and color_trim_audit(staging)["has_interior_and_compatibility_rows"],
        "pricing_ready": not pricing_blockers,
        "equipment_groups_ready": equipment_group_summary["cross_check_only"] and not equipment_group_blockers,
        "canonical_proposal_ready": not canonical_blockers and not staging["unresolved_rows"],
    }


def readiness(suspicious: list[dict[str, Any]], staging: dict[str, list[dict[str, str]]]) -> dict[str, Any]:
    reasons = []
    if staging["unresolved_rows"]:
        reasons.append("unresolved_rows_present")
    review_suspicious = [row for row in suspicious if row.get("readiness_impact") in {"blocking", "review_required"}]
    if review_suspicious:
        reasons.append("suspicious_review_rows_present")
    if not equipment_group_audit(staging)["cross_check_only"]:
        reasons.append("equipment_groups_leaked_to_primary_variant_rows")
    if staging.get("color_trim_interior_rows") and not staging.get("color_trim_compatibility_rows"):
        reasons.append("color_trim_compatibility_rows_missing")
    readiness_by_domain = domain_readiness(suspicious, staging)
    return {
        "ready_for_proposal_generation": readiness_by_domain["canonical_proposal_ready"] and not reasons,
        "advisory_only": True,
        "reasons": sorted(set(reasons)),
        **readiness_by_domain,
    }


def build_audit(staging_dir: Path) -> tuple[dict[str, Any], dict[str, list[dict[str, Any]]]]:
    staging, import_report, present_optional, missing_optional = load_staging(staging_dir)
    families = sheet_family_map(staging["sheets"])
    model_rows = model_key_counts(staging)
    status_rows = status_counts(staging, families)
    rpo_rows = rpo_counts(staging)
    footnote_rows = footnote_counts(staging)
    suspicious = classify_suspicious_rows(suspicious_rows(staging), families)
    audit = {
        "staging_dir": str(staging_dir),
        "inputs": {
            "required_files": sorted([*REQUIRED_FILES.values(), "import_report.json"]),
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
        "suspicious_rows_by_reason": counter_by(suspicious, "reason"),
        "suspicious_rows_by_type": counter_by(suspicious, "suspicion_type"),
        "suspicious_rows_by_bucket": counter_by(suspicious, "review_bucket"),
        "suspicious_rows_by_readiness_impact": counter_by(suspicious, "readiness_impact"),
        "recommended_actions_by_bucket": recommended_actions_by_bucket(suspicious),
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
