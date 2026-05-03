#!/usr/bin/env python3
"""Generate a human schema-decision packet from Pass 15 alignment output."""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
WARNING = "Generated decision packet, not source-of-truth config. canonical_apply_ready=false."
REQUIRED_INPUTS = {
    "report": "schema_alignment_report.json",
    "blockers": "schema_alignment_blockers.csv",
    "transformations": "schema_alignment_transformations.csv",
}
OPTIONAL_INPUTS = {
    "unmapped": "schema_alignment_unmapped_fields.csv",
    "selectables": "schema_alignment_selectables.csv",
    "display": "schema_alignment_display.csv",
    "availability": "schema_alignment_availability.csv",
    "source_refs": "schema_alignment_source_refs.csv",
}
ITEM_HEADERS = [
    "decision_id",
    "decision_area",
    "decision_title",
    "decision_status",
    "readiness_impact",
    "source_alignment_files",
    "related_blocker_ids",
    "related_transformation_ids",
    "related_unmapped_fields",
    "current_evidence_summary",
    "recommended_default",
    "required_human_decision",
    "notes",
]
OPTION_HEADERS = [
    "decision_id",
    "option_id",
    "option_label",
    "option_description",
    "pros",
    "cons",
    "implementation_notes",
    "recommended_default",
    "blocks_apply_if_unresolved",
]


def clean(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--alignment", required=True, help="Pass 15 schema alignment output directory.")
    parser.add_argument("--out", required=True, help="Decision packet output directory.")
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
            raise SystemExit(f"Refusing to write schema decision packet output under canonical or production directory: {resolved}")


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


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def load_inputs(alignment_dir: Path) -> tuple[dict[str, Any], dict[str, list[dict[str, str]]], dict[str, bool]]:
    missing = [filename for filename in REQUIRED_INPUTS.values() if not (alignment_dir / filename).exists()]
    if missing:
        raise SystemExit(f"Missing required schema alignment input: {', '.join(sorted(missing))}")
    report = load_json(alignment_dir / REQUIRED_INPUTS["report"])
    rows = {key: read_csv(alignment_dir / filename) for key, filename in REQUIRED_INPUTS.items() if key != "report"}
    optional_presence = {}
    for key, filename in OPTIONAL_INPUTS.items():
        path = alignment_dir / filename
        optional_presence[key] = path.exists()
        rows[key] = read_csv_if_present(path)
    return report, rows, optional_presence


def row_ref(prefix: str, row: dict[str, str], index: int) -> str:
    if prefix == "blocker":
        return f"blocker:{clean(row.get('blocker_key', '')) or index}"
    if prefix == "transformation":
        return (
            f"transformation:{clean(row.get('source_file', ''))}:"
            f"{clean(row.get('source_field', ''))}->{clean(row.get('target_table', ''))}:"
            f"{clean(row.get('target_field', '')) or '<none>'}"
        )
    return f"{prefix}:{index}"


def refs(rows: list[dict[str, str]], prefix: str, predicate) -> list[str]:
    return sorted({row_ref(prefix, row, index) for index, row in enumerate(rows, start=1) if predicate(row)})


def fields(rows: list[dict[str, str]], predicate) -> list[str]:
    values = set()
    for row in rows:
        if predicate(row):
            values.add(f"{clean(row.get('source_file', ''))}:{clean(row.get('source_field', ''))}")
    return sorted(values)


def contains_any(row: dict[str, str], needles: list[str]) -> bool:
    haystack = " ".join(clean(value).lower() for value in row.values())
    return any(needle in haystack for needle in needles)


def item(
    decision_id: str,
    decision_area: str,
    decision_title: str,
    readiness_impact: str,
    source_alignment_files: list[str],
    blocker_ids: list[str],
    transformation_ids: list[str],
    unmapped_fields: list[str],
    current_evidence_summary: str,
    recommended_default: str,
    required_human_decision: str,
    notes: str,
    decision_status: str = "needs_decision",
) -> dict[str, Any]:
    return {
        "decision_id": decision_id,
        "decision_area": decision_area,
        "decision_title": decision_title,
        "decision_status": decision_status,
        "readiness_impact": readiness_impact,
        "source_alignment_files": "|".join(source_alignment_files),
        "related_blocker_ids": "|".join(blocker_ids),
        "related_transformation_ids": "|".join(transformation_ids),
        "related_unmapped_fields": "|".join(unmapped_fields),
        "current_evidence_summary": current_evidence_summary,
        "recommended_default": recommended_default,
        "required_human_decision": required_human_decision,
        "notes": notes,
    }


def option(
    decision_id: str,
    option_id: str,
    label: str,
    description: str,
    pros: str,
    cons: str,
    implementation_notes: str,
    recommended_default: str,
    blocks_apply: str,
) -> dict[str, Any]:
    return {
        "decision_id": decision_id,
        "option_id": option_id,
        "option_label": label,
        "option_description": description,
        "pros": pros,
        "cons": cons,
        "implementation_notes": implementation_notes,
        "recommended_default": recommended_default,
        "blocks_apply_if_unresolved": blocks_apply,
    }


def build_items(rows: dict[str, list[dict[str, str]]], report: dict[str, Any]) -> list[dict[str, Any]]:
    blockers = rows["blockers"]
    transformations = rows["transformations"]
    unmapped = rows.get("unmapped", [])
    schema_context = report.get("schema_context_summary", {})
    files = schema_context.get("files", {}) if isinstance(schema_context, dict) else {}
    availability_present = bool(files.get("data/stingray/ui/availability.csv", {}).get("present", False))
    source_refs_present = bool(files.get("data/stingray/meta/source_refs.csv", {}).get("present", False))

    selectable_blockers = refs(blockers, "blocker", lambda row: contains_any(row, ["selectable_id", "canonical_selectable"]))
    selectable_transforms = refs(transformations, "transformation", lambda row: contains_any(row, ["proposal_selectable_id", "selectable_id"]))
    section_blockers = refs(blockers, "blocker", lambda row: contains_any(row, ["section_family", "section_id", "category"]))
    section_transforms = refs(transformations, "transformation", lambda row: contains_any(row, ["section_family", "section_id", "step_id", "category_id"]))
    availability_blockers = refs(blockers, "blocker", lambda row: contains_any(row, ["availability"]))
    availability_transforms = refs(transformations, "transformation", lambda row: clean(row.get("source_file", "")) == "ui/availability.csv")
    source_blockers = refs(blockers, "blocker", lambda row: contains_any(row, ["source_refs", "source ref", "source_ref"]))
    source_transforms = refs(transformations, "transformation", lambda row: clean(row.get("source_file", "")) == "meta/source_refs.csv" or contains_any(row, ["source_ref"]))
    metadata_unmapped = fields(
        unmapped,
        lambda row: contains_any(row, ["proposal_status", "review_status", "proposal_filter_status", "proposal_scope", "proposal-only"]),
    )
    metadata_transforms = refs(
        transformations,
        "transformation",
        lambda row: contains_any(row, ["proposal_status", "review_status", "proposal_filter_status", "proposal_scope"]),
    )
    boundary_blockers = refs(blockers, "blocker", lambda row: contains_any(row, ["canonical_apply", "color_trim", "equipment", "price", "rules", "packages"]))

    return [
        item(
            "selectable_id_policy",
            "canonical_selectable_id_policy",
            "Decide how proposal_selectable_id maps to final canonical selectable_id",
            "apply_blocker",
            ["schema_alignment_blockers.csv", "schema_alignment_transformations.csv", "schema_alignment_selectables.csv"],
            selectable_blockers,
            selectable_transforms,
            fields(unmapped, lambda row: contains_any(row, ["proposal_selectable_id"])),
            "proposal_selectable_id is proposal-only and not canonical truth; Pass 15 marks it transform_required.",
            "conservative_starting_point: keep proposal_selectable_id as review-only until a canonical ID policy is approved.",
            "Choose the canonical selectable_id policy for any future apply.",
            "No final canonical IDs are generated by this packet.",
        ),
        item(
            "section_mapping_policy",
            "ui_section_step_category_mapping",
            "Decide how section_family maps to canonical section_id / step_id / category_id",
            "schema_decision_needed",
            ["schema_alignment_blockers.csv", "schema_alignment_transformations.csv", "schema_alignment_display.csv"],
            section_blockers,
            section_transforms,
            fields(unmapped, lambda row: contains_any(row, ["section_family", "section_id"])),
            "section_family is too broad to be final section_id; Pass 15 marks it as requiring mapping.",
            "conservative_starting_point: use an explicit import map for section_family to UI taxonomy before apply.",
            "Approve the section, step, and category mapping approach.",
            "Do not infer fine categories from descriptions in this decision packet.",
        ),
        item(
            "availability_schema_policy",
            "canonical_availability_shape",
            "Decide canonical availability table shape and status enum",
            "schema_decision_needed",
            ["schema_alignment_blockers.csv", "schema_alignment_transformations.csv", "schema_alignment_availability.csv"],
            availability_blockers,
            availability_transforms,
            fields(unmapped, lambda row: clean(row.get("source_file", "")) == "ui/availability.csv"),
            f"Confident subset has available/standard/not_available values; target availability schema present={availability_present}.",
            "conservative_starting_point: preserve one row per selectable plus variant_id in first prototype.",
            "Choose the canonical availability table shape and confirm the status enum.",
            "Do not broaden availability or fill missing variants here.",
        ),
        item(
            "source_refs_policy",
            "source_refs_governance_shape",
            "Decide how row-level source refs map into canonical governance/source traceability",
            "schema_decision_needed",
            ["schema_alignment_blockers.csv", "schema_alignment_transformations.csv", "schema_alignment_source_refs.csv"],
            source_blockers,
            source_transforms,
            fields(unmapped, lambda row: contains_any(row, ["source_ref", "source_sheet", "source_row"])),
            f"Confident subset source refs are row-level evidence; target meta/source_refs.csv present={source_refs_present}.",
            "conservative_starting_point: keep source refs as import evidence until governance shape is approved.",
            "Choose whether source refs become canonical rows, a membership relation, or import-only evidence.",
            "Missing canonical source_refs schema is a schema-context gap, not an importer failure.",
        ),
        item(
            "proposal_metadata_policy",
            "proposal_only_metadata_disposition",
            "Decide what happens to proposal_status/review_status/proposal_filter_status/proposal_scope fields",
            "transformation_needed",
            ["schema_alignment_transformations.csv", "schema_alignment_unmapped_fields.csv"],
            [],
            metadata_transforms,
            metadata_unmapped,
            "Proposal-only metadata is useful for review but is not canonical business data.",
            "conservative_starting_point: preserve metadata in generated archive/import audit only.",
            "Approve which proposal metadata is dropped, archived, or mapped to provenance after apply.",
            "These fields must not be copied into canonical business tables blindly.",
        ),
        item(
            "first_apply_boundary",
            "first_apply_boundary_confirmation",
            "Confirm first apply boundary before any canonical mutation",
            "boundary_confirmation",
            ["schema_alignment_report.json", "schema_alignment_blockers.csv"],
            boundary_blockers,
            [],
            [],
            "Pass 15 recommends selectables/display/availability from confident subset only, with exclusions preserved.",
            "conservative_starting_point: produce a reconciliation report against canonical CSV before apply.",
            "Confirm whether a future apply prototype may proceed within the stated boundary.",
            "No apply is authorized by this packet.",
            decision_status="accepted_boundary",
        ),
    ]


def build_options() -> list[dict[str, Any]]:
    return [
        option(
            "selectable_id_policy",
            "selectable_id_model_rpo",
            "derive from model_key + rpo + disambiguator",
            "Create canonical IDs from model scope, orderable RPO, and a deterministic disambiguator when needed.",
            "Readable and reviewable; keeps model-specific collisions visible.",
            "Needs collision policy and reconciliation against existing canonical IDs.",
            "Use only after a human-approved ID format.",
            "conservative_starting_point",
            "yes",
        ),
        option(
            "selectable_id_policy",
            "selectable_id_source_hash",
            "derive from stable source hash",
            "Use source evidence to create deterministic IDs.",
            "Stable across reruns if evidence is stable.",
            "Less readable and can churn if source references change.",
            "Hash inputs must be documented before use.",
            "",
            "yes",
        ),
        option(
            "selectable_id_policy",
            "selectable_id_manual",
            "manually assign IDs during apply",
            "Human assigns canonical IDs during a future apply/reconciliation pass.",
            "Maximum control for first import.",
            "Slower and harder to repeat automatically.",
            "Use for small reviewed slices or conflicts.",
            "",
            "yes",
        ),
        option(
            "selectable_id_policy",
            "selectable_id_reconcile_existing",
            "use existing canonical IDs when reconciling against data/stingray",
            "Match proposal evidence to existing IDs before minting new IDs.",
            "Reduces duplicate canonical rows.",
            "Requires a separate reconciliation report.",
            "Best paired with a read-only canonical comparison pass.",
            "",
            "yes",
        ),
        option(
            "section_mapping_policy",
            "section_broad_placeholder",
            "map section_family to broad placeholder sections",
            "Use importer section families as temporary broad UI sections.",
            "Fastest path to a prototype review.",
            "Not final UI taxonomy; can hide category nuance.",
            "Clearly mark as provisional if used.",
            "",
            "yes",
        ),
        option(
            "section_mapping_policy",
            "section_import_map",
            "use import map for section_family to section_id/step_id",
            "Create explicit mapping config before apply.",
            "Reviewable and repeatable.",
            "Requires human taxonomy decisions first.",
            "Preferred once target UI schema is stable.",
            "conservative_starting_point",
            "yes",
        ),
        option(
            "section_mapping_policy",
            "section_defer",
            "defer finer UI mapping until app schema is stable",
            "Keep section_family as proposal evidence only.",
            "Avoids premature UI schema decisions.",
            "Blocks canonical UI apply.",
            "Useful if schema-refactor is still moving.",
            "",
            "yes",
        ),
        option(
            "availability_schema_policy",
            "availability_selectable_variant",
            "one row per selectable + variant_id",
            "Represent availability as explicit variant-scoped rows.",
            "Matches current confident subset shape.",
            "May be verbose; may not match final condition-set model.",
            "Preserve available/standard/not_available only.",
            "conservative_starting_point",
            "yes",
        ),
        option(
            "availability_schema_policy",
            "availability_condition_set",
            "one row per selectable + condition_set_id",
            "Compile variant scopes into condition sets.",
            "Can reduce duplication and match rule-driven schemas.",
            "Requires condition-set generation decisions.",
            "Do not synthesize until condition schema is stable.",
            "",
            "yes",
        ),
        option(
            "availability_schema_policy",
            "availability_hybrid",
            "hybrid variant matrix compiled into condition sets later",
            "Keep variant rows now and compile later.",
            "Preserves evidence while allowing later optimization.",
            "Adds a later migration step.",
            "Good bridge if schema is unsettled.",
            "",
            "yes",
        ),
        option(
            "source_refs_policy",
            "source_refs_canonical_rows",
            "canonical meta/source_refs.csv row per source cell/field",
            "Promote row-level source refs into canonical governance table.",
            "Strong traceability.",
            "Requires canonical source_refs schema.",
            "Use only after schema exists.",
            "",
            "yes",
        ),
        option(
            "source_refs_policy",
            "source_refs_member_table",
            "source_ref member table linking canonical rows to source refs",
            "Keep source refs normalized and link many refs to one canonical row.",
            "Avoids pipe-delimited source_ref_ids.",
            "Requires an additional relation table decision.",
            "Good if multiple source cells support one canonical row.",
            "conservative_starting_point",
            "yes",
        ),
        option(
            "source_refs_policy",
            "source_refs_import_only",
            "keep proposal source refs as import-only evidence",
            "Archive generated source refs with proposals instead of canonical tables.",
            "Avoids schema churn.",
            "Canonical rows lose direct row-level provenance unless copied elsewhere.",
            "Acceptable only if archive retention is approved.",
            "",
            "yes",
        ),
        option(
            "proposal_metadata_policy",
            "metadata_drop_after_apply",
            "drop after apply",
            "Do not carry proposal_status/review_status/filter metadata into canonical CSVs.",
            "Keeps canonical business data clean.",
            "Review history must live elsewhere.",
            "Pair with generated archive retention.",
            "",
            "no",
        ),
        option(
            "proposal_metadata_policy",
            "metadata_import_audit",
            "preserve in import audit metadata",
            "Store proposal metadata in audit/provenance outputs, not business tables.",
            "Traceable and avoids canonical pollution.",
            "Requires audit retention convention.",
            "Conservative default for this pipeline.",
            "conservative_starting_point",
            "no",
        ),
        option(
            "proposal_metadata_policy",
            "metadata_change_log",
            "preserve in change_log/provenance table",
            "Map metadata to a future provenance or change log table.",
            "Useful for future audits.",
            "Needs table/schema decision.",
            "Do not implement until schema is explicit.",
            "",
            "yes",
        ),
        option(
            "proposal_metadata_policy",
            "metadata_archive_only",
            "keep only in generated proposal archive",
            "Retain metadata in ignored/generated packet outputs only.",
            "No canonical schema impact.",
            "Requires generated archive availability for future audit.",
            "Good if canonical governance is deferred.",
            "",
            "no",
        ),
        option(
            "first_apply_boundary",
            "boundary_confident_apply_prototype",
            "proceed later with confident subset apply prototype",
            "Future pass applies only approved confident subset tables after schema decisions.",
            "Narrow and testable.",
            "Still requires ID, UI, availability, and source-ref decisions first.",
            "No current apply is authorized.",
            "",
            "yes",
        ),
        option(
            "first_apply_boundary",
            "boundary_reconciliation_first",
            "produce reconciliation report against canonical CSV first",
            "Compare confident subset to current canonical rows before any apply.",
            "Reduces duplicate/conflicting canonical writes.",
            "Adds one read-only pass.",
            "Best next step if canonical data already has overlapping content.",
            "conservative_starting_point",
            "no",
        ),
        option(
            "first_apply_boundary",
            "boundary_defer_full_schema",
            "defer apply until full schema/datapackage exists",
            "Wait for schema and datapackage stability.",
            "Lowest apply risk.",
            "Delays import value.",
            "Use if target tables remain incomplete.",
            "",
            "no",
        ),
    ]


def optional_notes(optional_presence: dict[str, bool], rows: dict[str, list[dict[str, str]]]) -> list[str]:
    notes = []
    missing = [filename for key, filename in OPTIONAL_INPUTS.items() if not optional_presence.get(key, False)]
    if missing:
        notes.append(f"Optional alignment context missing: {', '.join(sorted(missing))}.")
    known_blocker_types = {"apply_blocker", "schema_decision_needed", "transformation_needed", "advisory"}
    unexpected = sorted({clean(row.get("blocker_type", "")) for row in rows["blockers"] if clean(row.get("blocker_type", "")) not in known_blocker_types})
    if unexpected:
        notes.append(f"Unexpected blocker types observed but not promoted to new decision rows: {', '.join(unexpected)}.")
    return notes


def markdown_table(rows: list[dict[str, Any]], headers: list[str], limit: int = 12) -> str:
    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join("---" for _ in headers) + " |"]
    for row in rows[:limit]:
        lines.append("| " + " | ".join(clean(row.get(header, "")).replace("|", "\\|").replace("\n", " ") for header in headers) + " |")
    if len(rows) > limit:
        lines.append(f"\nShowing {limit} of {len(rows)} rows. Complete evidence is in the CSV outputs.")
    return "\n".join(lines)


def markdown(report: dict[str, Any], items: list[dict[str, Any]], options: list[dict[str, Any]], notes: list[str]) -> str:
    alignment_counts = report.get("alignment_counts_by_status", {})
    blocker_counts = report.get("blocker_counts_by_type", {})
    note_text = "\n".join(f"- {note}" for note in notes) if notes else "- No unexpected alignment notes."
    return f"""# Schema Decision Packet

{WARNING}

This is a generated decision packet, not source-of-truth config. It turns Pass 15 alignment evidence into human decisions only.

## Inputs

- alignment: `provided --alignment`
- output: `provided --out`

## Alignment Summary

- canonical_apply_ready=false
- alignment counts: `{json.dumps(alignment_counts, sort_keys=True)}`
- blocker counts: `{json.dumps(blocker_counts, sort_keys=True)}`

proposal_selectable_id is not canonical selectable_id.

section_family is not final section_id.

Color/Trim, Equipment Groups, rules, packages, and prices remain excluded from the first apply boundary.

No apply is authorized by this packet.

## Decision Items

{markdown_table(items, ["decision_id", "decision_area", "decision_status", "readiness_impact", "recommended_default"], limit=10)}

## Decision Options Summary

{markdown_table(options, ["decision_id", "option_id", "option_label", "recommended_default", "blocks_apply_if_unresolved"], limit=18)}

## First Apply Boundary

The future first apply boundary, if later authorized, should remain limited to selectables/display/availability from the confident subset only. It should exclude Color/Trim canonical import, Equipment Groups as selectable source, price evidence, rule inference, package logic, auto-adds, dependencies, and exclusivity.

## Additional Alignment Notes

{note_text}

No canonical rows were generated or applied.
"""


def build_packet(alignment_dir: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]], str]:
    report, rows, optional_presence = load_inputs(alignment_dir)
    items = build_items(rows, report)
    options = build_options()
    notes = optional_notes(optional_presence, rows)
    return items, options, markdown(report, items, options, notes)


def write_outputs(out_dir: Path, items: list[dict[str, Any]], options: list[dict[str, Any]], markdown_text: str) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    write_text(out_dir / "schema_decision_packet.md", markdown_text)
    write_csv(out_dir / "schema_decision_items.csv", ITEM_HEADERS, sorted(items, key=lambda row: row["decision_id"]))
    write_csv(out_dir / "schema_decision_options.csv", OPTION_HEADERS, sorted(options, key=lambda row: (row["decision_id"], row["option_id"])))


def main() -> int:
    args = parse_args()
    out_dir = Path(args.out)
    validate_output_dir(out_dir)
    items, options, markdown_text = build_packet(Path(args.alignment))
    write_outputs(out_dir, items, options, markdown_text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
