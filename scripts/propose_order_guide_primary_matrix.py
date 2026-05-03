#!/usr/bin/env python3
"""Generate narrow primary-matrix proposal artifacts from staged order-guide evidence.

This script writes proposal/review output only under the requested --out
directory. It does not mutate staging, canonical CSVs, app data, raw workbooks,
or production generated artifacts.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
READINESS_FIRST_MESSAGE = "Run scripts/report_order_guide_proposal_readiness.py before generating primary matrix proposals."
PROPOSAL_WARNING = (
    "Generated proposal files are review artifacts only and must not be copied blindly into data/stingray. "
    "They are not canonical source data."
)
PRIMARY_SECTION_FAMILIES = {"standard_equipment", "interior", "exterior", "mechanical"}
FORBIDDEN_OUTPUTS = [
    "logic/dependency_rules.csv",
    "logic/auto_adds.csv",
    "logic/exclusive_groups.csv",
    "logic/exclusive_group_members.csv",
    "pricing/base_prices.csv",
    "pricing/price_rules.csv",
    "support/color_trim*.csv",
    "data/stingray/**/*.csv",
    "form-app/data.js",
    "form-output/*",
]

SELECTABLE_HEADERS = [
    "proposal_selectable_id",
    "proposal_scope",
    "proposal_status",
    "source_sheet",
    "model_key",
    "section_family",
    "orderable_rpo",
    "ref_rpo",
    "proposal_label",
    "description",
    "selectable_source",
    "has_orderable_rpo",
    "has_ref_rpo",
    "review_status",
    "source_ref_ids",
    "notes",
]
DISPLAY_HEADERS = [
    "proposal_selectable_id",
    "proposal_status",
    "model_key",
    "section_family",
    "section_name",
    "category_name",
    "display_label",
    "display_description",
    "source_description_raw",
    "source_detail_raw",
    "review_status",
    "source_ref_ids",
]
AVAILABILITY_HEADERS = [
    "proposal_selectable_id",
    "proposal_status",
    "model_key",
    "variant_id",
    "body_code",
    "body_style",
    "trim_level",
    "orderable_rpo",
    "ref_rpo",
    "raw_status",
    "status_symbol",
    "footnote_refs",
    "canonical_status",
    "availability_value",
    "source_ref_id",
    "review_status",
    "notes",
]
PRICE_HEADERS = [
    "source_ref_id",
    "source_sheet",
    "source_row",
    "guide_family",
    "model_key",
    "model_key_confidence",
    "price_block_label",
    "raw_values",
    "notes",
    "review_status",
]
SOURCE_REF_HEADERS = [
    "source_ref_id",
    "source_file",
    "source_sheet",
    "source_row",
    "source_column_or_cell_range",
    "source_field",
    "raw_value",
    "raw_status",
    "orderable_rpo",
    "ref_rpo",
    "source_detail_raw",
]
RPO_OVERLAP_HEADERS = [
    "rpo",
    "orderable_count",
    "ref_only_count",
    "source_sheets",
    "model_keys",
    "section_families",
    "sample_descriptions",
    "decision_review_status",
    "decision_canonical_handling",
    "recommended_action",
    "notes",
    "review_status",
]
REVIEW_QUEUE_HEADERS = [
    "review_item_id",
    "severity",
    "reason",
    "source_file",
    "source_sheet",
    "source_row",
    "model_key",
    "proposal_selectable_id",
    "rpo",
    "raw_value",
    "recommended_action",
    "notes",
]


def clean(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--staging", required=True, help="Directory containing staging, audit, and readiness output.")
    parser.add_argument("--out", required=True, help="Directory where proposal artifacts should be written.")
    return parser.parse_args()


def stable_hash(value: str, length: int = 10) -> str:
    return hashlib.sha1(value.encode("utf-8")).hexdigest()[:length]


def safe_id_part(value: str) -> str:
    cleaned = "".join(char.lower() if char.isalnum() else "_" for char in clean(value))
    while "__" in cleaned:
        cleaned = cleaned.replace("__", "_")
    return cleaned.strip("_") or "blank"


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


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def read_csv_if_present(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    return read_csv(path)


def load_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Malformed JSON input {path.name}: {exc}") from exc


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
            raise SystemExit(f"Refusing to write proposal output under canonical or production directory: {resolved}")


def load_required_inputs(staging_dir: Path) -> tuple[dict[str, Any], dict[str, Any], list[dict[str, str]], list[dict[str, str]], list[dict[str, str]]]:
    readiness_path = staging_dir / "proposal_readiness_report.json"
    if not readiness_path.exists():
        raise SystemExit(f"{READINESS_FIRST_MESSAGE} Missing required input: proposal_readiness_report.json")
    audit_path = staging_dir / "staging_audit_report.json"
    if not audit_path.exists():
        raise SystemExit("Missing required input: staging_audit_report.json")
    matrix_path = staging_dir / "staging_variant_matrix_rows.csv"
    if not matrix_path.exists():
        raise SystemExit("Missing required input: staging_variant_matrix_rows.csv")
    price_path = staging_dir / "staging_price_rows.csv"
    if not price_path.exists():
        raise SystemExit("Missing required input: staging_price_rows.csv")

    readiness = load_json(readiness_path)
    if not readiness.get("narrow_first_proposal_scope_ready", False):
        raise SystemExit("Cannot generate primary matrix proposals when narrow_first_proposal_scope_ready=false")

    overlap_required = any(
        row.get("domain_key") == "accepted_rpo_role_overlaps_as_separate_evidence" and row.get("eligibility_status") == "eligible"
        for row in readiness.get("included_for_future_narrow_proposal", [])
        if isinstance(row, dict)
    )
    overlap_path = staging_dir / "staging_audit_rpo_role_overlaps.csv"
    if overlap_required and not overlap_path.exists():
        raise SystemExit("Missing required input: staging_audit_rpo_role_overlaps.csv")

    return (
        readiness,
        load_json(audit_path),
        read_csv(matrix_path),
        read_csv(price_path),
        read_csv_if_present(overlap_path),
    )


def source_ref_id(source_file: str, row: dict[str, str], suffix: str = "") -> str:
    parts = [
        source_file,
        clean(row.get("source_sheet", "")),
        clean(row.get("source_row", "")),
        clean(row.get("variant_id", "")),
        clean(row.get("orderable_rpo", "")),
        clean(row.get("ref_rpo", "")),
        suffix,
    ]
    readable = ":".join(part for part in parts[:3] if part)
    return f"{readable}:{stable_hash('|'.join(parts))}"


def proposal_id(row: dict[str, str]) -> str:
    model_key = safe_id_part(row.get("model_key", "needs_review"))
    section = safe_id_part(row.get("section_family", "unknown"))
    orderable = clean(row.get("orderable_rpo", ""))
    ref = clean(row.get("ref_rpo", ""))
    if orderable:
        return f"prop_{model_key}_{section}_{safe_id_part(orderable)}"
    if ref:
        return f"prop_{model_key}_{section}_ref_{safe_id_part(ref)}_{stable_hash(clean(row.get('description', '')), 6)}"
    return f"prop_{model_key}_{section}_norpo_{stable_hash(clean(row.get('description', '')), 8)}"


def first_description_line(value: str) -> str:
    for line in clean(value).splitlines():
        if clean(line):
            return clean(line)
    return ""


def availability_value(canonical_status: str) -> str:
    status = clean(canonical_status)
    if status in {"standard", "available", "not_available"}:
        return status
    if status == "adi_available":
        return "review_only"
    return "needs_review"


def is_primary_matrix_row(row: dict[str, str]) -> bool:
    source_sheet = clean(row.get("source_sheet", ""))
    return (
        clean(row.get("section_family", "")) in PRIMARY_SECTION_FAMILIES
        and not source_sheet.startswith("Equipment Groups")
        and not source_sheet.startswith("Color and Trim")
    )


def selectable_scope_and_review(row: dict[str, str]) -> tuple[str, str]:
    section = clean(row.get("section_family", ""))
    if section == "standard_equipment" and not clean(row.get("orderable_rpo", "")) and not clean(row.get("ref_rpo", "")):
        return "standard_equipment_review_only", "needs_review"
    if not clean(row.get("orderable_rpo", "")):
        return "primary_matrix_review_evidence", "needs_review"
    return "primary_matrix_selectable_candidate", "proposal_only"


def review_item(reason: str, row: dict[str, str], source_file: str, severity: str = "review", proposal_selectable_id: str = "", notes: str = "") -> dict[str, Any]:
    rpo = clean(row.get("orderable_rpo", "")) or clean(row.get("ref_rpo", "")) or clean(row.get("rpo", ""))
    raw_value = clean(row.get("description", "")) or clean(row.get("raw_values", "")) or rpo
    item_key = "|".join([reason, source_file, clean(row.get("source_sheet", "")), clean(row.get("source_row", "")), proposal_selectable_id, rpo, raw_value])
    return {
        "review_item_id": f"review_{stable_hash(item_key, 12)}",
        "severity": severity,
        "reason": reason,
        "source_file": source_file,
        "source_sheet": clean(row.get("source_sheet", "")),
        "source_row": clean(row.get("source_row", "")),
        "model_key": clean(row.get("model_key", "")),
        "proposal_selectable_id": proposal_selectable_id,
        "rpo": rpo,
        "raw_value": raw_value,
        "recommended_action": review_action(reason),
        "notes": notes,
    }


def review_action(reason: str) -> str:
    return {
        "missing_model_key": "review_model_key_before_accepting_proposal",
        "missing_variant_id": "review_variant_scope_before_accepting_proposal",
        "unsupported_status": "review_status_mapping_before_accepting_proposal",
        "blank_rpo_non_standard_equipment": "review_non_standard_row_without_rpo",
        "standard_equipment_without_rpo": "keep_as_review_evidence; do_not_treat_as_confirmed_selectable",
        "duplicate_or_conflicting_primary_matrix_evidence": "review_duplicate_primary_matrix_evidence",
        "ref_only_only_evidence": "review_reference_only_usage_before_accepting_selectable",
        "orderable_and_ref_same_row_review": "preserve_orderable_and_ref_separately",
        "accepted_rpo_overlap_kept_separate": "keep_overlap_as_separate_evidence; do_not_merge",
        "excluded_equipment_group_source": "exclude_from_selectable_proposal",
        "excluded_color_trim_source": "exclude_from_primary_matrix_proposal",
    }.get(reason, "review_before_accepting_proposal")


def build_primary_outputs(matrix_rows: list[dict[str, str]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    source_refs: list[dict[str, Any]] = []
    review_rows: list[dict[str, Any]] = []
    grouped: dict[str, dict[str, Any]] = {}
    availability_rows: list[dict[str, Any]] = []
    seen_availability: set[tuple[str, str, str, str, str]] = set()

    for row in matrix_rows:
        if not is_primary_matrix_row(row):
            continue
        pid = proposal_id(row)
        src_ref = source_ref_id("staging_variant_matrix_rows.csv", row)
        source_refs.append(
            {
                "source_ref_id": src_ref,
                "source_file": "staging_variant_matrix_rows.csv",
                "source_sheet": row.get("source_sheet", ""),
                "source_row": row.get("source_row", ""),
                "source_column_or_cell_range": row.get("variant_id", ""),
                "source_field": "variant_matrix_row",
                "raw_value": row.get("description", ""),
                "raw_status": row.get("raw_status", ""),
                "orderable_rpo": row.get("orderable_rpo", ""),
                "ref_rpo": row.get("ref_rpo", ""),
                "source_detail_raw": row.get("source_detail_raw", ""),
            }
        )

        proposal_scope, row_review_status = selectable_scope_and_review(row)
        entry = grouped.setdefault(
            pid,
            {
                "rows": [],
                "source_ref_ids": set(),
                "proposal_scope": proposal_scope,
                "review_status": row_review_status,
                "representative": row,
            },
        )
        entry["rows"].append(row)
        entry["source_ref_ids"].add(src_ref)
        if row_review_status == "needs_review":
            entry["review_status"] = "needs_review"
            entry["proposal_scope"] = proposal_scope

        if not clean(row.get("model_key", "")):
            review_rows.append(review_item("missing_model_key", row, "staging_variant_matrix_rows.csv", proposal_selectable_id=pid))
        if not clean(row.get("variant_id", "")):
            review_rows.append(review_item("missing_variant_id", row, "staging_variant_matrix_rows.csv", proposal_selectable_id=pid))
        if availability_value(row.get("canonical_status", "")) == "needs_review":
            review_rows.append(review_item("unsupported_status", row, "staging_variant_matrix_rows.csv", proposal_selectable_id=pid))
        if not clean(row.get("orderable_rpo", "")) and not clean(row.get("ref_rpo", "")) and clean(row.get("section_family", "")) == "standard_equipment":
            review_rows.append(review_item("standard_equipment_without_rpo", row, "staging_variant_matrix_rows.csv", proposal_selectable_id=pid))
        if not clean(row.get("orderable_rpo", "")) and clean(row.get("ref_rpo", "")):
            review_rows.append(review_item("ref_only_only_evidence", row, "staging_variant_matrix_rows.csv", proposal_selectable_id=pid))
        if clean(row.get("orderable_rpo", "")) and clean(row.get("ref_rpo", "")):
            review_rows.append(review_item("orderable_and_ref_same_row_review", row, "staging_variant_matrix_rows.csv", proposal_selectable_id=pid))
        if not clean(row.get("orderable_rpo", "")) and not clean(row.get("ref_rpo", "")) and clean(row.get("section_family", "")) != "standard_equipment":
            review_rows.append(review_item("blank_rpo_non_standard_equipment", row, "staging_variant_matrix_rows.csv", proposal_selectable_id=pid))

        availability_key = (pid, clean(row.get("variant_id", "")), clean(row.get("raw_status", "")), clean(row.get("source_row", "")), src_ref)
        if availability_key in seen_availability:
            review_rows.append(review_item("duplicate_or_conflicting_primary_matrix_evidence", row, "staging_variant_matrix_rows.csv", proposal_selectable_id=pid))
            continue
        seen_availability.add(availability_key)
        availability_rows.append(
            {
                "proposal_selectable_id": pid,
                "proposal_status": "proposal_only",
                "model_key": row.get("model_key", ""),
                "variant_id": row.get("variant_id", ""),
                "body_code": row.get("body_code", ""),
                "body_style": row.get("body_style", ""),
                "trim_level": row.get("trim_level", ""),
                "orderable_rpo": row.get("orderable_rpo", ""),
                "ref_rpo": row.get("ref_rpo", ""),
                "raw_status": row.get("raw_status", ""),
                "status_symbol": row.get("status_symbol", ""),
                "footnote_refs": row.get("footnote_refs", ""),
                "canonical_status": row.get("canonical_status", ""),
                "availability_value": availability_value(row.get("canonical_status", "")),
                "source_ref_id": src_ref,
                "review_status": "proposal_only" if row_review_status != "needs_review" else "needs_review",
                "notes": PROPOSAL_WARNING,
            }
        )

    selectable_rows: list[dict[str, Any]] = []
    display_rows: list[dict[str, Any]] = []
    for pid, entry in grouped.items():
        rep = entry["representative"]
        label = first_description_line(rep.get("description", "")) or clean(rep.get("orderable_rpo", "")) or clean(rep.get("ref_rpo", "")) or pid
        source_ref_ids = "|".join(sorted(entry["source_ref_ids"]))
        selectable_rows.append(
            {
                "proposal_selectable_id": pid,
                "proposal_scope": entry["proposal_scope"],
                "proposal_status": "proposal_only",
                "source_sheet": rep.get("source_sheet", ""),
                "model_key": rep.get("model_key", ""),
                "section_family": rep.get("section_family", ""),
                "orderable_rpo": rep.get("orderable_rpo", ""),
                "ref_rpo": rep.get("ref_rpo", ""),
                "proposal_label": label,
                "description": first_description_line(rep.get("description", "")),
                "selectable_source": "primary_variant_matrix",
                "has_orderable_rpo": "true" if clean(rep.get("orderable_rpo", "")) else "false",
                "has_ref_rpo": "true" if clean(rep.get("ref_rpo", "")) else "false",
                "review_status": entry["review_status"],
                "source_ref_ids": source_ref_ids,
                "notes": PROPOSAL_WARNING,
            }
        )
        display_rows.append(
            {
                "proposal_selectable_id": pid,
                "proposal_status": "proposal_only",
                "model_key": rep.get("model_key", ""),
                "section_family": rep.get("section_family", ""),
                "section_name": rep.get("section_family", "").replace("_", " ").title(),
                "category_name": rep.get("section_family", "").replace("_", " ").title(),
                "display_label": label,
                "display_description": first_description_line(rep.get("description", "")),
                "source_description_raw": rep.get("description", ""),
                "source_detail_raw": rep.get("source_detail_raw", ""),
                "review_status": entry["review_status"],
                "source_ref_ids": source_ref_ids,
            }
        )

    return (
        sorted(selectable_rows, key=lambda row: (row["model_key"], row["section_family"], row["orderable_rpo"], row["ref_rpo"], row["proposal_label"])),
        sorted(display_rows, key=lambda row: (row["model_key"], row["section_family"], row["display_label"], row["proposal_selectable_id"])),
        sorted(availability_rows, key=lambda row: (row["model_key"], row["variant_id"], row["proposal_selectable_id"], row["source_ref_id"])),
        sorted(source_refs, key=lambda row: (row["source_file"], row["source_sheet"], row["source_row"], row["source_field"], row["source_ref_id"])),
        review_rows,
    )


def price_outputs(price_rows: list[dict[str, str]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    output_rows: list[dict[str, Any]] = []
    source_refs: list[dict[str, Any]] = []
    for row in price_rows:
        src_ref = source_ref_id("staging_price_rows.csv", row)
        output_rows.append(
            {
                "source_ref_id": src_ref,
                "source_sheet": row.get("source_sheet", ""),
                "source_row": row.get("source_row", ""),
                "guide_family": row.get("guide_family", ""),
                "model_key": row.get("model_key", ""),
                "model_key_confidence": row.get("model_key_confidence", ""),
                "price_block_label": row.get("price_block_label", ""),
                "raw_values": row.get("raw_values", ""),
                "notes": row.get("notes", ""),
                "review_status": "raw_price_evidence_only",
            }
        )
        source_refs.append(
            {
                "source_ref_id": src_ref,
                "source_file": "staging_price_rows.csv",
                "source_sheet": row.get("source_sheet", ""),
                "source_row": row.get("source_row", ""),
                "source_column_or_cell_range": "",
                "source_field": "raw_price_evidence",
                "raw_value": row.get("raw_values", ""),
                "raw_status": "",
                "orderable_rpo": "",
                "ref_rpo": "",
                "source_detail_raw": row.get("notes", ""),
            }
        )
    return (
        sorted(output_rows, key=lambda row: (row["source_sheet"], int(row["source_row"] or 0), row["source_ref_id"])),
        sorted(source_refs, key=lambda row: (row["source_file"], row["source_sheet"], row["source_row"], row["source_field"], row["source_ref_id"])),
    )


def overlap_outputs(overlap_rows: list[dict[str, str]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    evidence: list[dict[str, Any]] = []
    source_refs: list[dict[str, Any]] = []
    review_rows: list[dict[str, Any]] = []
    for row in overlap_rows:
        rpo = clean(row.get("rpo", ""))
        if clean(row.get("decision_review_status", "")) != "accepted_expected_overlap":
            continue
        src_ref = f"staging_audit_rpo_role_overlaps.csv:{rpo}:{stable_hash(json.dumps(row, sort_keys=True), 8)}"
        evidence.append(
            {
                "rpo": rpo,
                "orderable_count": row.get("orderable_count", ""),
                "ref_only_count": row.get("ref_only_count", ""),
                "source_sheets": row.get("source_sheets", ""),
                "model_keys": row.get("model_keys", ""),
                "section_families": row.get("section_families", ""),
                "sample_descriptions": row.get("sample_descriptions", ""),
                "decision_review_status": row.get("decision_review_status", ""),
                "decision_canonical_handling": row.get("decision_canonical_handling", ""),
                "recommended_action": row.get("recommended_action", ""),
                "notes": row.get("decision_notes", ""),
                "review_status": row.get("decision_review_status", ""),
            }
        )
        source_refs.append(
            {
                "source_ref_id": src_ref,
                "source_file": "staging_audit_rpo_role_overlaps.csv",
                "source_sheet": row.get("source_sheets", ""),
                "source_row": "",
                "source_column_or_cell_range": "",
                "source_field": "rpo_role_overlap",
                "raw_value": rpo,
                "raw_status": "",
                "orderable_rpo": rpo,
                "ref_rpo": rpo,
                "source_detail_raw": row.get("sample_descriptions", ""),
            }
        )
        review_rows.append(
            review_item(
                "accepted_rpo_overlap_kept_separate",
                {"rpo": rpo, "description": row.get("sample_descriptions", ""), "model_key": row.get("model_keys", "")},
                "staging_audit_rpo_role_overlaps.csv",
                severity="info",
                notes="Accepted overlap is preserved as separate evidence and not merged.",
            )
        )
    return (
        sorted(evidence, key=lambda row: row["rpo"]),
        sorted(source_refs, key=lambda row: (row["source_file"], row["raw_value"], row["source_ref_id"])),
        sorted(review_rows, key=lambda row: (row["severity"], row["reason"], row["rpo"])),
    )


def boundary_review_rows(staging_dir: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for row in read_csv_if_present(staging_dir / "staging_equipment_group_rows.csv"):
        rows.append(review_item("excluded_equipment_group_source", row, "staging_equipment_group_rows.csv", severity="info", notes="Equipment Groups are cross-check only."))
        break
    for filename in ["staging_color_trim_interior_rows.csv", "staging_color_trim_compatibility_rows.csv", "staging_color_trim_disclosures.csv"]:
        color_rows = read_csv_if_present(staging_dir / filename)
        if color_rows:
            rows.append(review_item("excluded_color_trim_source", color_rows[0], filename, severity="info", notes="Color/Trim is accepted_review_only and excluded from first canonical proposal."))
            break
    return rows


def forbidden_outputs_absent(out_dir: Path) -> list[str]:
    absent: list[str] = []
    for pattern in FORBIDDEN_OUTPUTS:
        matches = list(out_dir.glob(pattern))
        if matches:
            raise SystemExit(f"Forbidden proposal output generated unexpectedly: {matches[0]}")
        absent.append(pattern)
    return absent


def report(
    readiness: dict[str, Any],
    audit: dict[str, Any],
    selectable_rows: list[dict[str, Any]],
    display_rows: list[dict[str, Any]],
    availability_rows: list[dict[str, Any]],
    price_rows: list[dict[str, Any]],
    overlap_rows: list[dict[str, Any]],
    review_rows: list[dict[str, Any]],
    out_dir: Path,
) -> dict[str, Any]:
    readiness_snapshot = readiness.get("audit_snapshot", {})
    return {
        "proposal_only": True,
        "warning": PROPOSAL_WARNING,
        "input_readiness": {
            "narrow_first_proposal_scope_ready": readiness.get("narrow_first_proposal_scope_ready", False),
            "canonical_proposal_ready": readiness_snapshot.get("canonical_proposal_ready", False),
            "ready_for_proposal_generation": readiness_snapshot.get("ready_for_proposal_generation", False),
            "readiness_reasons": readiness_snapshot.get("readiness_reasons", []),
        },
        "row_counts": {
            "catalog_selectables": len(selectable_rows),
            "ui_selectable_display": len(display_rows),
            "ui_availability": len(availability_rows),
            "pricing_raw_price_evidence": len(price_rows),
            "meta_rpo_role_overlap_evidence": len(overlap_rows),
            "review_queue": len(review_rows),
        },
        "review_queue_by_reason": dict(sorted(Counter(row.get("reason", "") for row in review_rows).items())),
        "source_audit_summary": {
            "primary_variant_matrix_ready": audit.get("readiness", {}).get("primary_variant_matrix_ready", ""),
            "pricing_ready": audit.get("readiness", {}).get("pricing_ready", ""),
            "equipment_groups_ready": audit.get("readiness", {}).get("equipment_groups_ready", ""),
            "color_trim_ready": audit.get("readiness", {}).get("color_trim_ready", ""),
            "rpo_role_overlaps_ready": audit.get("readiness", {}).get("rpo_role_overlaps_ready", ""),
        },
        "forbidden_outputs_verified_absent": forbidden_outputs_absent(out_dir),
        "non_goals_confirmed": [
            "no canonical data/stingray CSVs written",
            "no app data generated",
            "no production form-output artifacts written",
            "no Color/Trim canonical import",
            "no Equipment Groups selectable source",
            "no dependency, auto-add, exclusive-group, package, or final price rules emitted",
            "accepted RPO overlaps kept as separate evidence",
        ],
    }


def generate(staging_dir: Path, out_dir: Path) -> None:
    validate_output_dir(out_dir)
    readiness, audit, matrix_rows, staged_price_rows, staged_overlap_rows = load_required_inputs(staging_dir)
    selectable_rows, display_rows, availability_rows, matrix_source_refs, review_rows = build_primary_outputs(matrix_rows)
    price_rows, price_source_refs = price_outputs(staged_price_rows)
    overlap_rows, overlap_source_refs, overlap_review_rows = overlap_outputs(staged_overlap_rows)
    review_rows = sorted(
        [*review_rows, *overlap_review_rows, *boundary_review_rows(staging_dir)],
        key=lambda row: (row["severity"], row["reason"], row["source_sheet"], row["source_row"], row["proposal_selectable_id"], row["rpo"]),
    )
    source_refs = sorted(
        [*matrix_source_refs, *price_source_refs, *overlap_source_refs],
        key=lambda row: (row["source_file"], row["source_sheet"], row["source_row"], row["source_field"], row["source_ref_id"]),
    )

    write_csv(out_dir / "catalog" / "selectables.csv", SELECTABLE_HEADERS, selectable_rows)
    write_csv(out_dir / "ui" / "selectable_display.csv", DISPLAY_HEADERS, display_rows)
    write_csv(out_dir / "ui" / "availability.csv", AVAILABILITY_HEADERS, availability_rows)
    write_csv(out_dir / "pricing" / "raw_price_evidence.csv", PRICE_HEADERS, price_rows)
    write_csv(out_dir / "meta" / "source_refs.csv", SOURCE_REF_HEADERS, source_refs)
    write_csv(out_dir / "meta" / "rpo_role_overlap_evidence.csv", RPO_OVERLAP_HEADERS, overlap_rows)
    write_csv(out_dir / "review_queue.csv", REVIEW_QUEUE_HEADERS, review_rows)
    write_json(out_dir / "proposal_report.json", report(readiness, audit, selectable_rows, display_rows, availability_rows, price_rows, overlap_rows, review_rows, out_dir))


def main() -> int:
    args = parse_args()
    generate(Path(args.staging), Path(args.out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
