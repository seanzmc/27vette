#!/usr/bin/env python3
"""Report schema alignment for a confident order-guide proposal subset.

This is a read-only report over generated proposal artifacts. It does not
create canonical rows, mutate canonical CSVs, or apply proposal data.
"""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
WARNING = "Generated schema-alignment report only. canonical_apply_ready=false."
REQUIRED_INPUTS = {
    "subset_report": "proposal_subset_report.json",
    "selectables": "catalog/selectables.csv",
    "display": "ui/selectable_display.csv",
    "availability": "ui/availability.csv",
    "source_refs": "meta/source_refs.csv",
}
OPTIONAL_INPUTS = {
    "excluded_review_rows": "excluded_review_rows.csv",
    "review_summary": "review/confident_subset_review_summary.json",
    "review_selectables": "review/confident_subset_selectables_review.csv",
    "review_availability_matrix": "review/confident_subset_availability_matrix.csv",
}
SCHEMA_CONTEXT_FILES = [
    "schema-refactor.md",
    "safeMigrationPlan.md",
    "orderGuideImporterScripts.md",
    "data/stingray/catalog/selectables.csv",
    "data/stingray/catalog/variants.csv",
    "data/stingray/catalog/item_sets.csv",
    "data/stingray/catalog/item_set_members.csv",
    "data/stingray/ui/selectable_display.csv",
    "data/stingray/ui/availability.csv",
    "data/stingray/pricing/base_prices.csv",
    "data/stingray/meta/source_refs.csv",
    "data/stingray/datapackage.yaml",
]
OWNED_OUTPUTS = [
    "schema_alignment_report.json",
    "schema_alignment_report.md",
    "schema_alignment_selectables.csv",
    "schema_alignment_display.csv",
    "schema_alignment_availability.csv",
    "schema_alignment_source_refs.csv",
    "schema_alignment_unmapped_fields.csv",
    "schema_alignment_transformations.csv",
    "schema_alignment_blockers.csv",
]
ALIGNMENT_HEADERS = [
    "source_file",
    "source_field",
    "source_values",
    "target_table",
    "target_field",
    "alignment_status",
    "transformation_needed",
    "schema_context_confidence",
    "notes",
]
TRANSFORMATION_HEADERS = [
    "source_file",
    "source_field",
    "target_table",
    "target_field",
    "alignment_status",
    "transformation_needed",
    "notes",
]
BLOCKER_HEADERS = [
    "blocker_key",
    "blocker_type",
    "affected_table",
    "severity",
    "notes",
]


def clean(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--subset", required=True, help="Confident proposal subset directory.")
    parser.add_argument("--out", required=True, help="Schema alignment output directory.")
    return parser.parse_args()


def is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False


def validate_output_dir(out_dir: Path) -> None:
    resolved = out_dir.resolve()
    forbidden_dirs = [
        ROOT / "data",
        ROOT / "data" / "stingray",
        ROOT / "data" / "corvette",
        ROOT / "form-output",
        ROOT / "form-app",
    ]
    for forbidden in forbidden_dirs:
        forbidden_resolved = forbidden.resolve()
        if resolved == forbidden_resolved or is_relative_to(resolved, forbidden_resolved):
            raise SystemExit(f"Refusing to write schema alignment output under canonical or production directory: {resolved}")


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


def csv_headers(path: Path) -> list[str]:
    with path.open(newline="", encoding="utf-8") as handle:
        try:
            reader = csv.reader(handle)
            return [clean(header) for header in next(reader, [])]
        except csv.Error as exc:
            raise SystemExit(f"Malformed CSV schema context {path}: {exc}") from exc


def load_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Malformed JSON input {path}: {exc}") from exc


def load_json_if_present(path: Path) -> tuple[dict[str, Any], bool]:
    if not path.exists():
        return {}, False
    return load_json(path), True


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


def load_inputs(subset_dir: Path) -> tuple[dict[str, Any], dict[str, list[dict[str, str]]], dict[str, bool], dict[str, Any]]:
    missing = [filename for filename in REQUIRED_INPUTS.values() if not (subset_dir / filename).exists()]
    if missing:
        raise SystemExit(f"Missing required confident subset input: {', '.join(sorted(missing))}")
    subset_report = load_json(subset_dir / REQUIRED_INPUTS["subset_report"])
    rows = {key: read_csv(subset_dir / filename) for key, filename in REQUIRED_INPUTS.items() if key != "subset_report"}
    optional_presence: dict[str, bool] = {}
    optional_json: dict[str, Any] = {}
    for key, filename in OPTIONAL_INPUTS.items():
        path = subset_dir / filename
        if filename.endswith(".json"):
            optional_json[key], optional_presence[key] = load_json_if_present(path)
        else:
            optional_presence[key] = path.exists()
            rows[key] = read_csv_if_present(path)
    return subset_report, rows, optional_presence, optional_json


def schema_context_summary() -> dict[str, Any]:
    files: dict[str, dict[str, Any]] = {}
    for rel_path in SCHEMA_CONTEXT_FILES:
        path = ROOT / rel_path
        entry: dict[str, Any] = {"present": path.exists(), "headers": [], "kind": "document" if not rel_path.endswith(".csv") else "csv"}
        if path.exists() and rel_path.endswith(".csv"):
            entry["headers"] = csv_headers(path)
        files[rel_path] = entry
    corvette_files = []
    corvette_root = ROOT / "data" / "corvette"
    if corvette_root.exists():
        for path in sorted(corvette_root.glob("**/*")):
            if path.is_file():
                rel = path.relative_to(ROOT).as_posix()
                corvette_files.append(rel)
                files[rel] = {
                    "present": True,
                    "headers": csv_headers(path) if path.suffix == ".csv" else [],
                    "kind": "csv" if path.suffix == ".csv" else "document",
                }
    found_schema_csvs = [key for key, value in files.items() if value["present"] and value["kind"] == "csv"]
    required_for_full = [
        "data/stingray/catalog/selectables.csv",
        "data/stingray/ui/selectable_display.csv",
        "data/stingray/ui/availability.csv",
        "data/stingray/meta/source_refs.csv",
    ]
    if not found_schema_csvs:
        confidence = "incomplete"
    elif all(files.get(path, {}).get("present") for path in required_for_full):
        confidence = "sufficient_for_field_mapping"
    else:
        confidence = "partial"
    return {
        "schema_context_confidence": confidence,
        "files": files,
        "data_corvette_files": corvette_files,
        "missing_schema_context": sorted(key for key, value in files.items() if not value["present"]),
    }


def headers_for(schema: dict[str, Any], rel_path: str) -> set[str]:
    return set(schema.get("files", {}).get(rel_path, {}).get("headers", []) or [])


def unique_values(rows: list[dict[str, str]], field: str, limit: int = 12) -> str:
    values = sorted({clean(row.get(field, "")) for row in rows if clean(row.get(field, ""))})
    if len(values) > limit:
        return "|".join(values[:limit]) + f"|...(+{len(values) - limit})"
    return "|".join(values)


def alignment_row(
    source_file: str,
    source_field: str,
    source_values: str,
    target_table: str,
    target_field: str,
    alignment_status: str,
    transformation_needed: str,
    confidence: str,
    notes: str,
) -> dict[str, Any]:
    return {
        "source_file": source_file,
        "source_field": source_field,
        "source_values": source_values,
        "target_table": target_table,
        "target_field": target_field,
        "alignment_status": alignment_status,
        "transformation_needed": transformation_needed,
        "schema_context_confidence": confidence,
        "notes": notes,
    }


def target_status(schema: dict[str, Any], target_table: str, target_field: str, fallback_status: str) -> str:
    if not schema.get("files", {}).get(target_table, {}).get("present", False):
        return "target_schema_missing"
    if target_field and target_field not in headers_for(schema, target_table):
        return "target_schema_missing"
    return fallback_status


def selectables_alignment(rows: list[dict[str, str]], schema: dict[str, Any]) -> list[dict[str, Any]]:
    confidence = schema["schema_context_confidence"]
    target = "data/stingray/catalog/selectables.csv"
    mappings = [
        ("proposal_selectable_id", "selectable_id", "transform_required", "canonical selectable_id policy required; proposal ID remains review-only."),
        ("proposal_scope", "", "excluded_from_first_apply", "Proposal boundary metadata should not become canonical selectable data."),
        ("proposal_status", "", "excluded_from_first_apply", "Proposal-only warning/status metadata."),
        ("source_sheet", "source_refs", "review_required", "Workbook source identity belongs in traceability/governance evidence."),
        ("model_key", "model_key", "review_required", "Model scope likely belongs to variant/scope relation, not selectable identity alone."),
        ("section_family", "section_id", "transform_required", "section_family is a broad importer family and is not final section_id."),
        ("orderable_rpo", "rpo", "direct_map", "Orderable RPO is the cleanest direct selectable field."),
        ("ref_rpo", "", "review_required", "Ref-only evidence must remain separate from orderable selectable identity."),
        ("proposal_label", "label", "direct_map", "Proposal label can map after ID and review policy are settled."),
        ("description", "description", "direct_map", "Raw proposal description can map as description with source review."),
        ("selectable_source", "", "excluded_from_first_apply", "Importer provenance metadata."),
        ("has_orderable_rpo", "", "excluded_from_first_apply", "Generated QA metadata."),
        ("has_ref_rpo", "", "excluded_from_first_apply", "Generated QA metadata."),
        ("review_status", "", "excluded_from_first_apply", "Review workflow metadata, not canonical data."),
        ("source_ref_ids", "source_refs", "review_required", "May require normalized source-ref membership rather than pipe-delimited IDs."),
        ("notes", "notes", "review_required", "Proposal warnings should not be copied blindly."),
        ("proposal_filter_status", "", "excluded_from_first_apply", "Generated confident-subset marker."),
    ]
    out = []
    for source_field, target_field, status, notes in mappings:
        out.append(
            alignment_row(
                "catalog/selectables.csv",
                source_field,
                unique_values(rows, source_field),
                target,
                target_field,
                target_status(schema, target, target_field, status) if target_field and target_field != "source_refs" else status,
                "yes" if status in {"transform_required", "review_required"} else "no",
                confidence,
                notes,
            )
        )
    return out


def display_alignment(rows: list[dict[str, str]], schema: dict[str, Any]) -> list[dict[str, Any]]:
    confidence = schema["schema_context_confidence"]
    target = "data/stingray/ui/selectable_display.csv"
    mappings = [
        ("proposal_selectable_id", "selectable_id", "transform_required", "Depends on future canonical selectable_id policy."),
        ("proposal_status", "", "excluded_from_first_apply", "Proposal-only metadata."),
        ("model_key", "", "review_required", "UI display may need model/variant scoping outside this table."),
        ("section_family", "section_id", "transform_required", "section_family is too broad to be a final section_id."),
        ("section_name", "section_name", "direct_map", "Section name is display evidence, subject to UI taxonomy review."),
        ("category_name", "category_name", "direct_map", "Category name can map only after category_id policy is settled."),
        ("display_label", "label", "direct_map", "Display label maps cleanly after selectable_id transform."),
        ("display_description", "description", "direct_map", "Display description maps cleanly after selectable_id transform."),
        ("source_description_raw", "source_detail_raw", "review_required", "Raw source text should remain evidence unless explicitly promoted."),
        ("source_detail_raw", "source_detail_raw", "review_required", "Raw source detail is traceability/display evidence."),
        ("review_status", "", "excluded_from_first_apply", "Review workflow metadata."),
        ("source_ref_ids", "", "review_required", "May need normalized traceability relation."),
        ("proposal_filter_status", "", "excluded_from_first_apply", "Generated confident-subset marker."),
    ]
    out = []
    for source_field, target_field, status, notes in mappings:
        out.append(
            alignment_row(
                "ui/selectable_display.csv",
                source_field,
                unique_values(rows, source_field),
                target,
                target_field,
                target_status(schema, target, target_field, status) if target_field else status,
                "yes" if status in {"transform_required", "review_required"} else "no",
                confidence,
                notes,
            )
        )
    return out


def availability_alignment(rows: list[dict[str, str]], schema: dict[str, Any]) -> list[dict[str, Any]]:
    confidence = schema["schema_context_confidence"]
    target = "data/stingray/ui/availability.csv"
    mappings = [
        ("proposal_selectable_id", "selectable_id", "transform_required", "Depends on future canonical selectable_id policy."),
        ("proposal_status", "", "excluded_from_first_apply", "Proposal-only metadata."),
        ("model_key", "model_key", "review_required", "Variant/model scope must match final availability schema."),
        ("variant_id", "variant_id", "direct_map", "Confident subset availability is already variant-scoped."),
        ("body_code", "body_code", "direct_map", "Body code is scope evidence if target schema keeps it."),
        ("body_style", "body_style", "direct_map", "Body style is scope evidence if target schema keeps it."),
        ("trim_level", "trim_level", "direct_map", "Trim level is scope evidence if target schema keeps it."),
        ("orderable_rpo", "rpo", "review_required", "Selectable identity should come through canonical selectable_id, not standalone RPO only."),
        ("ref_rpo", "", "review_required", "Ref-only evidence remains separate."),
        ("raw_status", "", "review_required", "Raw status is source evidence; canonical availability should use normalized status."),
        ("status_symbol", "", "review_required", "Status symbol is source evidence."),
        ("footnote_refs", "", "review_required", "Footnotes require an approved source-evidence or footnote schema."),
        ("canonical_status", "status", "direct_map", "Normalized status values are already available/standard/not_available."),
        ("availability_value", "status", "direct_map", "Expected values are available, standard, and not_available."),
        ("source_ref_id", "source_ref_id", "review_required", "Traceability target schema is not confirmed in current checkout."),
        ("review_status", "", "excluded_from_first_apply", "Review workflow metadata."),
        ("notes", "notes", "review_required", "Proposal warning notes should not be copied blindly."),
        ("proposal_filter_status", "", "excluded_from_first_apply", "Generated confident-subset marker."),
    ]
    out = []
    for source_field, target_field, status, notes in mappings:
        out.append(
            alignment_row(
                "ui/availability.csv",
                source_field,
                unique_values(rows, source_field),
                target,
                target_field,
                target_status(schema, target, target_field, status) if target_field else status,
                "yes" if status in {"transform_required", "review_required"} else "no",
                confidence,
                notes,
            )
        )
    return out


def source_refs_alignment(rows: list[dict[str, str]], schema: dict[str, Any]) -> list[dict[str, Any]]:
    confidence = schema["schema_context_confidence"]
    target = "data/stingray/meta/source_refs.csv"
    target_present = schema.get("files", {}).get(target, {}).get("present", False)
    status = "review_required"
    mappings = [
        ("source_ref_id", "source_ref_id", "Source reference ID format should be reviewed before canonical use."),
        ("source_file", "source_file", "Generated staging source filename."),
        ("source_sheet", "source_sheet", "Workbook sheet traceability."),
        ("source_row", "source_row", "Workbook row traceability."),
        ("source_column_or_cell_range", "source_column_or_cell_range", "Workbook cell/column traceability."),
        ("source_field", "source_field", "Extractor field context."),
        ("raw_value", "raw_value", "Raw workbook evidence."),
        ("raw_status", "raw_status", "Raw status evidence."),
        ("orderable_rpo", "orderable_rpo", "Orderable RPO source evidence."),
        ("ref_rpo", "ref_rpo", "Reference-only RPO source evidence."),
        ("source_detail_raw", "source_detail_raw", "Raw detail source evidence."),
    ]
    return [
        alignment_row(
            "meta/source_refs.csv",
            source_field,
            unique_values(rows, source_field),
            target,
            target_field,
            status,
            "yes",
            confidence,
            f"{notes} Missing canonical source_refs schema is a schema-context gap, not an importer failure."
            if not target_present
            else notes,
        )
        for source_field, target_field, notes in mappings
    ]


def unmapped_fields(all_alignment: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(
        [
            row
            for row in all_alignment
            if row["alignment_status"]
            in {"excluded_from_first_apply", "review_required", "unsupported_in_current_schema", "target_schema_missing", "schema_decision_needed"}
            or not clean(row.get("target_field", ""))
        ],
        key=lambda row: (row["source_file"], row["source_field"], row["alignment_status"]),
    )


def transformations(all_alignment: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for row in all_alignment:
        if row["alignment_status"] == "direct_map":
            continue
        rows.append(
            {
                "source_file": row["source_file"],
                "source_field": row["source_field"],
                "target_table": row["target_table"],
                "target_field": row["target_field"],
                "alignment_status": row["alignment_status"],
                "transformation_needed": row["transformation_needed"],
                "notes": row["notes"],
            }
        )
    return sorted(rows, key=lambda row: (row["source_file"], row["source_field"], row["alignment_status"]))


def blockers(schema: dict[str, Any]) -> list[dict[str, Any]]:
    rows = [
        {
            "blocker_key": "no_final_canonical_selectable_id_policy",
            "blocker_type": "schema_decision_needed",
            "affected_table": "catalog/selectables.csv",
            "severity": "apply_blocker",
            "notes": "proposal_selectable_id is review-only and must not be copied as final selectable_id.",
        },
        {
            "blocker_key": "section_family_not_final_section_id",
            "blocker_type": "transformation_needed",
            "affected_table": "ui/selectable_display.csv",
            "severity": "schema_decision_needed",
            "notes": "section_family is a broad importer family and needs UI section/category mapping.",
        },
        {
            "blocker_key": "canonical_apply_ready_false_by_design",
            "blocker_type": "apply_blocker",
            "affected_table": "all",
            "severity": "apply_blocker",
            "notes": "Pass 15 reports alignment only; it does not imply canonical apply readiness.",
        },
        {
            "blocker_key": "color_trim_excluded_from_first_apply",
            "blocker_type": "advisory",
            "affected_table": "support/color_trim",
            "severity": "advisory",
            "notes": "Color/Trim remains accepted_review_only and outside this first apply boundary.",
        },
        {
            "blocker_key": "price_evidence_excluded_from_confident_subset",
            "blocker_type": "advisory",
            "affected_table": "pricing",
            "severity": "advisory",
            "notes": "Raw price evidence was intentionally excluded from the confident subset.",
        },
        {
            "blocker_key": "rules_packages_dependencies_excluded",
            "blocker_type": "advisory",
            "affected_table": "logic",
            "severity": "advisory",
            "notes": "Rule, package, auto-add, dependency, and exclusivity inference remain out of scope.",
        },
    ]
    if not schema.get("files", {}).get("data/stingray/ui/availability.csv", {}).get("present", False):
        rows.append(
            {
                "blocker_key": "missing_canonical_availability_schema",
                "blocker_type": "schema_decision_needed",
                "affected_table": "ui/availability.csv",
                "severity": "schema_decision_needed",
                "notes": "Canonical availability target is missing in current schema context; this is distinct from excluded first-apply items.",
            }
        )
    if not schema.get("files", {}).get("data/stingray/meta/source_refs.csv", {}).get("present", False):
        rows.append(
            {
                "blocker_key": "missing_canonical_source_refs_schema",
                "blocker_type": "schema_decision_needed",
                "affected_table": "meta/source_refs.csv",
                "severity": "schema_decision_needed",
                "notes": "Canonical source_refs target is missing; this is a canonical schema-context gap, not an importer failure.",
            }
        )
    return sorted(rows, key=lambda row: (row["blocker_type"], row["blocker_key"]))


def count_statuses(rows: list[dict[str, Any]]) -> dict[str, int]:
    return dict(sorted(Counter(row["alignment_status"] for row in rows).items()))


def markdown_table(rows: list[dict[str, Any]], headers: list[str], limit: int = 12) -> str:
    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join("---" for _ in headers) + " |"]
    for row in rows[:limit]:
        lines.append("| " + " | ".join(clean(row.get(header, "")).replace("|", "\\|").replace("\n", " ") for header in headers) + " |")
    if len(rows) > limit:
        lines.append(f"\nShowing {limit} of {len(rows)} rows. Complete evidence is in the CSV outputs.")
    return "\n".join(lines)


def build_report(subset_dir: Path) -> tuple[dict[str, Any], dict[str, list[dict[str, Any]]], str]:
    subset_report, rows, optional_presence, optional_json = load_inputs(subset_dir)
    schema = schema_context_summary()
    selectables_rows = selectables_alignment(rows["selectables"], schema)
    display_rows = display_alignment(rows["display"], schema)
    availability_rows = availability_alignment(rows["availability"], schema)
    source_ref_rows = source_refs_alignment(rows["source_refs"], schema)
    all_alignment = selectables_rows + display_rows + availability_rows + source_ref_rows
    unmapped = unmapped_fields(all_alignment)
    transformation_rows = transformations(all_alignment)
    blocker_rows = blockers(schema)
    table_summary = {
        "selectables": count_statuses(selectables_rows),
        "display": count_statuses(display_rows),
        "availability": count_statuses(availability_rows),
        "source_refs": count_statuses(source_ref_rows),
    }
    report = {
        "warning": WARNING,
        "input_summary": {
            "subset_path": "provided --subset",
            "out_path": "provided --out",
            "required_input_presence": {filename: True for filename in REQUIRED_INPUTS.values()},
            "optional_input_presence": optional_presence,
        },
        "schema_context_summary": schema,
        "confident_subset_counts": {
            "selectables": len(rows["selectables"]),
            "display": len(rows["display"]),
            "availability": len(rows["availability"]),
            "source_refs": len(rows["source_refs"]),
            "excluded_review_rows": len(rows.get("excluded_review_rows", [])),
            "review_summary_retained_selectables": optional_json.get("review_summary", {}).get("retained_selectables", ""),
        },
        "alignment_counts_by_status": count_statuses(all_alignment),
        "table_alignment_summary": table_summary,
        "blocker_counts_by_type": dict(sorted(Counter(row["blocker_type"] for row in blocker_rows).items())),
        "recommended_first_apply_boundary": [
            "Apply only after canonical schema is stable.",
            "Start with selectables, display, and availability from confident subset only.",
            "Exclude Color/Trim.",
            "Exclude Equipment Groups.",
            "Exclude price evidence.",
            "Exclude rules, packages, auto-adds, dependencies, and exclusivity.",
            "Keep proposal_selectable_id as proposal-only until a canonical ID policy is approved.",
        ],
        "canonical_apply_ready": False,
        "reasons": [
            "schema_alignment_report_only",
            "no_final_canonical_selectable_id_policy",
            "section_family_requires_ui_mapping",
        ],
        "recommended_next_step": "Review schema_alignment_blockers.csv and approve canonical ID and UI section mapping policies before any apply/proposal-to-canonical pass.",
        "source_subset_report_summary": {
            "readiness": subset_report.get("readiness", {}),
            "confident_subset_counts": subset_report.get("confident_subset_counts", {}),
        },
    }
    csvs = {
        "schema_alignment_selectables.csv": selectables_rows,
        "schema_alignment_display.csv": display_rows,
        "schema_alignment_availability.csv": availability_rows,
        "schema_alignment_source_refs.csv": source_ref_rows,
        "schema_alignment_unmapped_fields.csv": unmapped,
        "schema_alignment_transformations.csv": transformation_rows,
        "schema_alignment_blockers.csv": blocker_rows,
    }
    markdown = markdown_report(report, blocker_rows, transformation_rows)
    return report, csvs, markdown


def markdown_report(report: dict[str, Any], blocker_rows: list[dict[str, Any]], transformation_rows: list[dict[str, Any]]) -> str:
    schema = report["schema_context_summary"]
    found_files = [
        {"file": path, "headers": "|".join(value.get("headers", []))}
        for path, value in schema["files"].items()
        if value.get("present")
    ]
    return f"""# Confident Subset Schema Alignment

{WARNING}

This is a schema-alignment report only. It is generated review evidence, not source-of-truth config.

## Summary

- canonical_apply_ready=false
- schema_context_confidence: `{schema["schema_context_confidence"]}`
- retained selectables: `{report["confident_subset_counts"]["selectables"]}`
- retained availability rows: `{report["confident_subset_counts"]["availability"]}`
- source refs: `{report["confident_subset_counts"]["source_refs"]}`

## Schema Context Found

{markdown_table(found_files, ["file", "headers"], limit=10)}

## Table Alignment Summary

```json
{json.dumps(report["table_alignment_summary"], indent=2, sort_keys=True)}
```

## Top Transformation Needs

{markdown_table(transformation_rows, ["source_file", "source_field", "target_table", "target_field", "alignment_status", "transformation_needed"], limit=14)}

## Blockers By Type

{markdown_table(blocker_rows, ["blocker_key", "blocker_type", "affected_table", "severity", "notes"], limit=14)}

## Recommended First Apply Boundary

- Apply only after canonical schema is stable.
- Start with selectables/display/availability from confident subset only.
- Exclude Color/Trim, Equipment Groups, price evidence, rules, packages, auto-adds, dependencies, and exclusivity.
- Preserve proposal IDs as proposal-only until a canonical ID policy is approved.

No canonical rows were generated or applied.
"""


def write_outputs(out_dir: Path, report: dict[str, Any], csvs: dict[str, list[dict[str, Any]]], markdown: str) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    write_json(out_dir / "schema_alignment_report.json", report)
    write_text(out_dir / "schema_alignment_report.md", markdown)
    for filename, rows in csvs.items():
        if filename == "schema_alignment_blockers.csv":
            headers = BLOCKER_HEADERS
        elif filename == "schema_alignment_transformations.csv":
            headers = TRANSFORMATION_HEADERS
        else:
            headers = ALIGNMENT_HEADERS
        write_csv(out_dir / filename, headers, rows)


def main() -> int:
    args = parse_args()
    out_dir = Path(args.out)
    validate_output_dir(out_dir)
    report, csvs, markdown = build_report(Path(args.subset))
    write_outputs(out_dir, report, csvs, markdown)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
