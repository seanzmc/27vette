#!/usr/bin/env python3
"""Reconcile a confident order-guide subset against canonical CSV context.

This script is report-only. It does not apply proposal rows, mutate canonical
CSV files, or generate app/runtime data.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SCHEMA_DECISIONS = ROOT / "data" / "import_maps" / "corvette_2027" / "schema_decisions.csv"
WARNING = "Canonical reconciliation report only. canonical_apply_ready=false."
REQUIRED_SUBSET_INPUTS = {
    "subset_report": "proposal_subset_report.json",
    "selectables": "catalog/selectables.csv",
    "display": "ui/selectable_display.csv",
    "availability": "ui/availability.csv",
    "source_refs": "meta/source_refs.csv",
}
EXPECTED_DECISIONS = {
    "availability_schema_policy": "availability_selectable_variant",
    "first_apply_boundary": "boundary_reconciliation_first",
    "proposal_metadata_policy": "metadata_import_audit",
    "section_mapping_policy": "section_import_map",
    "selectable_id_policy": "selectable_id_model_rpo",
    "source_refs_policy": "source_refs_member_table",
}
OUTPUT_HEADERS = {
    "matched_selectables.csv": [
        "proposal_selectable_id",
        "model_key",
        "orderable_rpo",
        "canonical_selectable_id",
        "match_confidence",
        "match_reasons",
        "label_match_status",
        "description_match_status",
        "notes",
    ],
    "new_selectable_candidates.csv": [
        "proposal_selectable_id",
        "model_key",
        "orderable_rpo",
        "candidate_canonical_selectable_id_preview",
        "candidate_id_status",
        "proposal_label",
        "description",
        "source_ref_count",
        "notes",
    ],
    "conflicting_selectables.csv": [
        "proposal_selectable_id",
        "model_key",
        "orderable_rpo",
        "canonical_selectable_id",
        "conflict_type",
        "proposal_value",
        "canonical_value",
        "recommended_action",
    ],
    "unavailable_canonical_context.csv": [
        "model_key",
        "reason",
        "affected_row_count",
        "notes",
    ],
    "section_mapping_needs.csv": [
        "section_family",
        "model_key",
        "affected_selectable_count",
        "required_mapping",
        "recommended_action",
    ],
    "availability_reconciliation.csv": [
        "proposal_selectable_id",
        "model_key",
        "variant_id",
        "orderable_rpo",
        "availability_value",
        "canonical_availability_status",
        "reconciliation_status",
        "notes",
    ],
    "source_ref_member_plan.csv": [
        "proposal_selectable_id",
        "proposed_target_table",
        "proposed_target_row_key",
        "source_ref_id",
        "source_sheet",
        "source_row",
        "notes",
    ],
    "apply_blockers.csv": [
        "blocker_id",
        "blocker_type",
        "severity",
        "affected_domain",
        "affected_count",
        "required_decision_or_action",
        "notes",
    ],
}


def clean(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--subset", required=True, help="Confident subset directory.")
    parser.add_argument("--canonical-root", required=True, help="Canonical CSV root, for example data/stingray.")
    parser.add_argument("--out", required=True, help="Generated reconciliation output directory.")
    parser.add_argument(
        "--schema-decisions",
        default=str(DEFAULT_SCHEMA_DECISIONS),
        help="Approved schema decision map. Defaults to data/import_maps/corvette_2027/schema_decisions.csv.",
    )
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
            raise SystemExit(f"Refusing to write canonical reconciliation output under canonical or production directory: {resolved}")


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        try:
            return [dict(row) for row in csv.DictReader(handle)]
        except csv.Error as exc:
            raise SystemExit(f"Malformed CSV input {path}: {exc}") from exc


def read_csv_if_present(path: Path) -> tuple[list[dict[str, str]], bool]:
    if not path.exists():
        return [], False
    return read_csv(path), True


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


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def load_subset(subset_dir: Path) -> tuple[dict[str, Any], dict[str, list[dict[str, str]]]]:
    missing = [filename for filename in REQUIRED_SUBSET_INPUTS.values() if not (subset_dir / filename).exists()]
    if missing:
        raise SystemExit(f"Missing required confident subset input: {', '.join(sorted(missing))}")
    return (
        load_json(subset_dir / REQUIRED_SUBSET_INPUTS["subset_report"]),
        {key: read_csv(subset_dir / filename) for key, filename in REQUIRED_SUBSET_INPUTS.items() if key != "subset_report"},
    )


def load_decisions(path: Path) -> tuple[dict[str, str], bool]:
    if not path.exists():
        return dict(EXPECTED_DECISIONS), False
    rows = read_csv(path)
    decisions = {clean(row.get("decision_id", "")): clean(row.get("selected_option_id", "")) for row in rows}
    for decision_id, expected in EXPECTED_DECISIONS.items():
        if decisions.get(decision_id) != expected:
            raise SystemExit(f"Schema decision config does not match approved decision: {decision_id}")
    return decisions, True


def canonical_context(canonical_root: Path) -> dict[str, Any]:
    selectables, selectables_present = read_csv_if_present(canonical_root / "catalog" / "selectables.csv")
    variants, variants_present = read_csv_if_present(canonical_root / "catalog" / "variants.csv")
    display, display_present = read_csv_if_present(canonical_root / "ui" / "selectable_display.csv")
    availability, availability_present = read_csv_if_present(canonical_root / "ui" / "availability.csv")
    source_refs, source_refs_present = read_csv_if_present(canonical_root / "meta" / "source_refs.csv")
    source_ref_members_present = (canonical_root / "meta" / "source_ref_members.csv").exists()
    covered_models = sorted({clean(row.get("model_key", "")) for row in variants if clean(row.get("model_key", ""))})
    if not covered_models and canonical_root.name == "stingray" and canonical_root.exists():
        covered_models = ["stingray"]
    by_rpo: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in selectables:
        rpo = clean(row.get("rpo", "")).upper()
        if rpo:
            by_rpo[rpo].append(row)
    return {
        "root": str(canonical_root),
        "files": {
            "catalog/selectables.csv": selectables_present,
            "catalog/variants.csv": variants_present,
            "ui/selectable_display.csv": display_present,
            "ui/availability.csv": availability_present,
            "meta/source_refs.csv": source_refs_present,
            "meta/source_ref_members.csv": source_ref_members_present,
            "datapackage.yaml": (canonical_root / "datapackage.yaml").exists(),
        },
        "selectables": selectables,
        "variants": variants,
        "display": display,
        "availability": availability,
        "source_refs": source_refs,
        "selectables_by_rpo": by_rpo,
        "covered_models": covered_models,
    }


def pipe_values(value: str) -> list[str]:
    return [item for item in clean(value).split("|") if item]


def norm_text(value: str) -> str:
    return re.sub(r"\s+", " ", clean(value).lower())


def norm_id(value: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "_", clean(value).lower()).strip("_")
    return normalized or "unknown"


def candidate_id(row: dict[str, str], duplicates: Counter[tuple[str, str]]) -> str:
    model_key = norm_id(row.get("model_key", ""))
    rpo = norm_id(row.get("orderable_rpo", ""))
    base = f"sel_{model_key}_{rpo}"
    if duplicates[(clean(row.get("model_key", "")), clean(row.get("orderable_rpo", "")).upper())] > 1:
        digest = hashlib.sha1(clean(row.get("proposal_selectable_id", "")).encode("utf-8")).hexdigest()[:8]
        return f"{base}_{digest}"
    return base


def compare_status(proposal: str, canonical: str) -> str:
    if not clean(proposal) and not clean(canonical):
        return "both_blank"
    if norm_text(proposal) == norm_text(canonical):
        return "exact_match"
    if not clean(canonical):
        return "canonical_missing"
    if not clean(proposal):
        return "proposal_missing"
    return "mismatch"


def source_ref_map(rows: list[dict[str, str]]) -> dict[str, dict[str, str]]:
    return {clean(row.get("source_ref_id", "")): row for row in rows if clean(row.get("source_ref_id", ""))}


def reconcile(subset_rows: dict[str, list[dict[str, str]]], context: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    covered_models = set(context["covered_models"])
    by_rpo = context["selectables_by_rpo"]
    source_refs = source_ref_map(subset_rows["source_refs"])
    display_by_id = {clean(row.get("proposal_selectable_id", "")): row for row in subset_rows["display"]}
    duplicates = Counter((clean(row.get("model_key", "")), clean(row.get("orderable_rpo", "")).upper()) for row in subset_rows["selectables"])
    matched = []
    candidates = []
    conflicts = []
    unavailable_counts: Counter[str] = Counter()
    section_counts: Counter[tuple[str, str]] = Counter()
    proposal_to_target: dict[str, str] = {}
    proposal_to_status: dict[str, str] = {}

    for row in sorted(subset_rows["selectables"], key=lambda item: (clean(item.get("model_key", "")), clean(item.get("orderable_rpo", "")), clean(item.get("proposal_selectable_id", "")))):
        proposal_id = clean(row.get("proposal_selectable_id", ""))
        model_key = clean(row.get("model_key", ""))
        rpo = clean(row.get("orderable_rpo", "")).upper()
        section_counts[(clean(row.get("section_family", "")), model_key)] += 1
        if model_key not in covered_models:
            unavailable_counts[model_key] += 1
            preview = candidate_id(row, duplicates)
            proposal_to_target[proposal_id] = preview
            proposal_to_status[proposal_id] = "unavailable_context"
            continue
        canonical_matches = by_rpo.get(rpo, [])
        if len(canonical_matches) > 1:
            conflicts.append(
                {
                    "proposal_selectable_id": proposal_id,
                    "model_key": model_key,
                    "orderable_rpo": rpo,
                    "canonical_selectable_id": "|".join(sorted(clean(match.get("selectable_id", "")) for match in canonical_matches)),
                    "conflict_type": "ambiguous_canonical_match",
                    "proposal_value": row.get("proposal_label", ""),
                    "canonical_value": "|".join(sorted(clean(match.get("label", "")) for match in canonical_matches)),
                    "recommended_action": "Review canonical duplicates before apply; do not choose a match silently.",
                }
            )
            proposal_to_target[proposal_id] = candidate_id(row, duplicates)
            proposal_to_status[proposal_id] = "ambiguous_canonical_match"
            continue
        if len(canonical_matches) == 1:
            canonical = canonical_matches[0]
            label_status = compare_status(row.get("proposal_label", ""), canonical.get("label", ""))
            description_status = compare_status(row.get("description", ""), canonical.get("description", ""))
            matched.append(
                {
                    "proposal_selectable_id": proposal_id,
                    "model_key": model_key,
                    "orderable_rpo": rpo,
                    "canonical_selectable_id": canonical.get("selectable_id", ""),
                    "match_confidence": "high" if label_status == "exact_match" else "medium",
                    "match_reasons": "model_context_and_rpo_match",
                    "label_match_status": label_status,
                    "description_match_status": description_status,
                    "notes": "Existing canonical ID is used for reconciliation only; no apply performed.",
                }
            )
            proposal_to_target[proposal_id] = clean(canonical.get("selectable_id", ""))
            proposal_to_status[proposal_id] = "matched"
            if label_status == "mismatch":
                conflicts.append(
                    {
                        "proposal_selectable_id": proposal_id,
                        "model_key": model_key,
                        "orderable_rpo": rpo,
                        "canonical_selectable_id": canonical.get("selectable_id", ""),
                        "conflict_type": "label_mismatch",
                        "proposal_value": row.get("proposal_label", ""),
                        "canonical_value": canonical.get("label", ""),
                        "recommended_action": "Review label before apply.",
                    }
                )
            if description_status == "mismatch":
                conflicts.append(
                    {
                        "proposal_selectable_id": proposal_id,
                        "model_key": model_key,
                        "orderable_rpo": rpo,
                        "canonical_selectable_id": canonical.get("selectable_id", ""),
                        "conflict_type": "description_mismatch",
                        "proposal_value": row.get("description", ""),
                        "canonical_value": canonical.get("description", ""),
                        "recommended_action": "Review description before apply.",
                    }
                )
            continue
        preview = candidate_id(row, duplicates)
        candidates.append(
            {
                "proposal_selectable_id": proposal_id,
                "model_key": model_key,
                "orderable_rpo": rpo,
                "candidate_canonical_selectable_id_preview": preview,
                "candidate_id_status": "preview_only",
                "proposal_label": row.get("proposal_label", ""),
                "description": row.get("description", ""),
                "source_ref_count": len(pipe_values(row.get("source_ref_ids", ""))),
                "notes": "Candidate ID preview only; not an approved canonical selectable_id.",
            }
        )
        proposal_to_target[proposal_id] = preview
        proposal_to_status[proposal_id] = "new_candidate"

    unavailable = [
        {
            "model_key": model_key,
            "reason": "model_not_covered_by_canonical_root",
            "affected_row_count": count,
            "notes": "Canonical root is treated as covering only its observed model context.",
        }
        for model_key, count in sorted(unavailable_counts.items())
    ]
    section_needs = [
        {
            "section_family": section_family,
            "model_key": model_key,
            "affected_selectable_count": count,
            "required_mapping": "section_family -> section_id/step_id/category_id",
            "recommended_action": "Create an explicit section import map before apply.",
        }
        for (section_family, model_key), count in sorted(section_counts.items())
    ]
    availability_rows = availability_reconciliation(subset_rows["availability"], context, proposal_to_status)
    source_plan = source_ref_member_plan(subset_rows["selectables"], source_refs, proposal_to_target)
    blockers = apply_blockers(context, unavailable, section_needs, conflicts)
    return {
        "matched_selectables.csv": matched,
        "new_selectable_candidates.csv": candidates,
        "conflicting_selectables.csv": sorted(conflicts, key=lambda row: (row["conflict_type"], row["model_key"], row["orderable_rpo"], row["proposal_selectable_id"])),
        "unavailable_canonical_context.csv": unavailable,
        "section_mapping_needs.csv": section_needs,
        "availability_reconciliation.csv": availability_rows,
        "source_ref_member_plan.csv": source_plan,
        "apply_blockers.csv": blockers,
    }


def availability_reconciliation(rows: list[dict[str, str]], context: dict[str, Any], proposal_status: dict[str, str]) -> list[dict[str, Any]]:
    canonical_available = context["files"]["ui/availability.csv"]
    out = []
    for row in sorted(rows, key=lambda item: (clean(item.get("model_key", "")), clean(item.get("variant_id", "")), clean(item.get("proposal_selectable_id", "")))):
        status = "target_schema_missing" if not canonical_available else "not_compared"
        if proposal_status.get(clean(row.get("proposal_selectable_id", ""))) == "unavailable_context":
            status = "model_context_unavailable"
        out.append(
            {
                "proposal_selectable_id": row.get("proposal_selectable_id", ""),
                "model_key": row.get("model_key", ""),
                "variant_id": row.get("variant_id", ""),
                "orderable_rpo": row.get("orderable_rpo", ""),
                "availability_value": row.get("availability_value", ""),
                "canonical_availability_status": "",
                "reconciliation_status": status,
                "notes": "Availability policy is one row per selectable plus variant_id; no canonical rows generated.",
            }
        )
    return out


def source_ref_member_plan(selectables: list[dict[str, str]], source_refs: dict[str, dict[str, str]], targets: dict[str, str]) -> list[dict[str, Any]]:
    out = []
    for row in sorted(selectables, key=lambda item: (clean(item.get("model_key", "")), clean(item.get("orderable_rpo", "")), clean(item.get("proposal_selectable_id", "")))):
        proposal_id = clean(row.get("proposal_selectable_id", ""))
        for ref_id in pipe_values(row.get("source_ref_ids", "")):
            ref = source_refs.get(ref_id, {})
            out.append(
                {
                    "proposal_selectable_id": proposal_id,
                    "proposed_target_table": "catalog/selectables.csv",
                    "proposed_target_row_key": targets.get(proposal_id, ""),
                    "source_ref_id": ref_id,
                    "source_sheet": ref.get("source_sheet", ""),
                    "source_row": ref.get("source_row", ""),
                    "notes": "source_refs_member_table plan only; no canonical source refs written.",
                }
            )
    return out


def apply_blockers(context: dict[str, Any], unavailable: list[dict[str, Any]], section_needs: list[dict[str, Any]], conflicts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    blockers = [
        {
            "blocker_id": "canonical_selectable_id_policy_not_applied",
            "blocker_type": "apply_blocker",
            "severity": "apply_blocker",
            "affected_domain": "selectables",
            "affected_count": "",
            "required_decision_or_action": "Apply the approved selectable_id_model_rpo policy in a future apply pass.",
            "notes": "Candidate IDs are preview_only in this report.",
        },
        {
            "blocker_id": "missing_section_family_import_map",
            "blocker_type": "mapping_needed",
            "severity": "apply_blocker",
            "affected_domain": "ui",
            "affected_count": sum(int(row["affected_selectable_count"]) for row in section_needs),
            "required_decision_or_action": "Create explicit section_family -> section_id/step_id/category_id map.",
            "notes": "Pass 17 reports mapping needs only.",
        },
        {
            "blocker_id": "canonical_apply_ready_false_by_design",
            "blocker_type": "apply_blocker",
            "severity": "apply_blocker",
            "affected_domain": "all",
            "affected_count": "",
            "required_decision_or_action": "Run a separate approved apply pass only after blockers are resolved.",
            "notes": "This reconciliation report does not authorize apply.",
        },
    ]
    if not context["files"]["ui/availability.csv"]:
        blockers.append(
            {
                "blocker_id": "missing_canonical_availability_schema",
                "blocker_type": "schema_context_missing",
                "severity": "apply_blocker",
                "affected_domain": "availability",
                "affected_count": "",
                "required_decision_or_action": "Create/approve canonical availability target schema.",
                "notes": "Availability rows are reported as target_schema_missing.",
            }
        )
    if not context["files"]["meta/source_ref_members.csv"]:
        blockers.append(
            {
                "blocker_id": "missing_canonical_source_ref_member_schema",
                "blocker_type": "schema_context_missing",
                "severity": "apply_blocker",
                "affected_domain": "source_refs",
                "affected_count": "",
                "required_decision_or_action": "Create/approve normalized source-ref member table schema.",
                "notes": "source_ref_member_plan.csv is plan-only.",
            }
        )
    unavailable_count = sum(int(row["affected_row_count"]) for row in unavailable)
    if unavailable_count:
        blockers.append(
            {
                "blocker_id": "non_stingray_model_context_unavailable",
                "blocker_type": "schema_context_missing",
                "severity": "apply_blocker",
                "affected_domain": "model_context",
                "affected_count": unavailable_count,
                "required_decision_or_action": "Provide canonical context for non-covered models or exclude them from apply.",
                "notes": "Do not pretend data/stingray covers other Corvette models.",
            }
        )
    ambiguous = [row for row in conflicts if row["conflict_type"] == "ambiguous_canonical_match"]
    if ambiguous:
        blockers.append(
            {
                "blocker_id": "ambiguous_canonical_match",
                "blocker_type": "apply_blocker",
                "severity": "apply_blocker",
                "affected_domain": "selectables",
                "affected_count": len(ambiguous),
                "required_decision_or_action": "Resolve duplicate canonical RPO matches before apply.",
                "notes": "The reconciler does not choose among ambiguous canonical rows.",
            }
        )
    return sorted(blockers, key=lambda row: row["blocker_id"])


def report_json(subset_report: dict[str, Any], decisions: dict[str, str], decisions_present: bool, context: dict[str, Any], outputs: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    return {
        "warning": WARNING,
        "input_summary": {
            "subset_path": "provided --subset",
            "canonical_root": context["root"],
            "out_path": "provided --out",
        },
        "canonical_context_summary": {
            "covered_models": context["covered_models"],
            "files": context["files"],
            "canonical_selectable_count": len(context["selectables"]),
        },
        "decision_summary": decisions,
        "schema_decisions_config_present": decisions_present,
        "match_counts": {
            "matched_selectables": len(outputs["matched_selectables.csv"]),
            "new_selectable_candidates": len(outputs["new_selectable_candidates.csv"]),
            "conflicting_selectables": len(outputs["conflicting_selectables.csv"]),
            "unavailable_canonical_context_rows": len(outputs["unavailable_canonical_context.csv"]),
        },
        "conflict_counts": dict(sorted(Counter(row["conflict_type"] for row in outputs["conflicting_selectables.csv"]).items())),
        "unavailable_canonical_context_counts": {
            row["model_key"]: row["affected_row_count"] for row in outputs["unavailable_canonical_context.csv"]
        },
        "apply_blockers": {
            "total": len(outputs["apply_blockers.csv"]),
            "by_type": dict(sorted(Counter(row["blocker_type"] for row in outputs["apply_blockers.csv"]).items())),
        },
        "source_subset_report_summary": subset_report.get("confident_subset_counts", {}),
        "canonical_apply_ready": False,
        "recommended_next_step": "Resolve section mapping, canonical availability/source-ref schemas, ambiguous matches, and non-covered model context before any apply.",
    }


def markdown(report: dict[str, Any]) -> str:
    return f"""# Canonical Reconciliation Report

{WARNING}

This is a reconciliation report only. It compares confident subset proposal artifacts to canonical CSV context and does not apply rows.

## Selected Human Decisions

```json
{json.dumps(report["decision_summary"], indent=2, sort_keys=True)}
```

## Summary

- canonical_apply_ready=false
- covered canonical models: `{ "|".join(report["canonical_context_summary"]["covered_models"]) }`
- matched selectables: `{report["match_counts"]["matched_selectables"]}`
- new selectable candidates: `{report["match_counts"]["new_selectable_candidates"]}`
- conflicting selectables: `{report["match_counts"]["conflicting_selectables"]}`
- apply blockers: `{report["apply_blockers"]["total"]}`

## Recommended Next Step

{report["recommended_next_step"]}

No canonical rows were generated or applied.
"""


def write_outputs(out_dir: Path, report: dict[str, Any], outputs: dict[str, list[dict[str, Any]]]) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    write_json(out_dir / "reconciliation_report.json", report)
    write_text(out_dir / "reconciliation_report.md", markdown(report))
    for filename, rows in outputs.items():
        write_csv(out_dir / filename, OUTPUT_HEADERS[filename], rows)


def main() -> int:
    args = parse_args()
    out_dir = Path(args.out)
    validate_output_dir(out_dir)
    subset_report, subset_rows = load_subset(Path(args.subset))
    decisions, decisions_present = load_decisions(Path(args.schema_decisions))
    context = canonical_context(Path(args.canonical_root))
    outputs = reconcile(subset_rows, context)
    report = report_json(subset_report, decisions, decisions_present, context, outputs)
    write_outputs(out_dir, report, outputs)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
