#!/usr/bin/env python3
"""Generate human review surfaces for a confident primary-matrix subset."""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
WARNING = "Generated review evidence, not source-of-truth config. canonical_apply_ready=false."
REQUIRED_INPUTS = {
    "report": "proposal_subset_report.json",
    "selectables": "catalog/selectables.csv",
    "display": "ui/selectable_display.csv",
    "availability": "ui/availability.csv",
    "source_refs": "meta/source_refs.csv",
}
OPTIONAL_INPUTS = {"excluded": "excluded_review_rows.csv"}


def clean(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--subset", required=True, help="Confident subset directory.")
    parser.add_argument("--out", required=True, help="Review packet output directory.")
    return parser.parse_args()


def is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False


def validate_output_dir(out_dir: Path) -> None:
    resolved = out_dir.resolve()
    forbidden_dirs = [ROOT / "data", ROOT / "data" / "stingray", ROOT / "data" / "corvette", ROOT / "form-output", ROOT / "form-app"]
    for forbidden in forbidden_dirs:
        forbidden_resolved = forbidden.resolve()
        if resolved == forbidden_resolved or is_relative_to(resolved, forbidden_resolved):
            raise SystemExit(f"Refusing to write confident subset review output under canonical or production directory: {resolved}")


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


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def load_inputs(subset_dir: Path) -> tuple[dict[str, Any], dict[str, list[dict[str, str]]], dict[str, bool]]:
    missing = [filename for filename in REQUIRED_INPUTS.values() if not (subset_dir / filename).exists()]
    if missing:
        raise SystemExit(f"Missing required confident subset input: {', '.join(sorted(missing))}")
    rows = {key: read_csv(subset_dir / filename) for key, filename in REQUIRED_INPUTS.items() if key != "report"}
    optional_presence = {}
    for key, filename in OPTIONAL_INPUTS.items():
        path = subset_dir / filename
        optional_presence[key] = path.exists()
        rows[key] = read_csv_if_present(path)
    return load_json(subset_dir / REQUIRED_INPUTS["report"]), rows, optional_presence


def pipe_values(value: str) -> list[str]:
    return [item for item in clean(value).split("|") if item]


def source_ref_map(rows: list[dict[str, str]]) -> dict[str, dict[str, str]]:
    return {clean(row.get("source_ref_id", "")): row for row in rows if clean(row.get("source_ref_id", ""))}


def display_by_id(rows: list[dict[str, str]]) -> dict[str, dict[str, str]]:
    return {clean(row.get("proposal_selectable_id", "")): row for row in rows}


def availability_by_id(rows: list[dict[str, str]]) -> dict[str, list[dict[str, str]]]:
    result: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        result[clean(row.get("proposal_selectable_id", ""))].append(row)
    return result


def variant_sort_key(row: dict[str, str]) -> tuple[str, str, str, str]:
    return (
        clean(row.get("model_key", "")),
        clean(row.get("body_style", "")),
        clean(row.get("trim_level", "")),
        clean(row.get("variant_id", "")),
    )


def variant_ids(rows: list[dict[str, str]], source_variant_ids: set[str] | None = None) -> list[str]:
    examples: dict[str, dict[str, str]] = {}
    for row in rows:
        variant_id = clean(row.get("variant_id", ""))
        if variant_id:
            examples.setdefault(variant_id, row)
    for variant_id in source_variant_ids or set():
        examples.setdefault(variant_id, {"variant_id": variant_id})
    return sorted(examples, key=lambda variant_id: variant_sort_key(examples[variant_id]))


def variants_by_model(rows: list[dict[str, str]]) -> dict[str, set[str]]:
    result: dict[str, set[str]] = defaultdict(set)
    for row in rows:
        if clean(row.get("model_key", "")) and clean(row.get("variant_id", "")):
            result[clean(row.get("model_key", ""))].add(clean(row.get("variant_id", "")))
    return result


def source_variants_by_model(selectables: list[dict[str, str]], source_refs: dict[str, dict[str, str]]) -> dict[str, set[str]]:
    result: dict[str, set[str]] = defaultdict(set)
    for selectable in selectables:
        model_key = clean(selectable.get("model_key", ""))
        if not model_key:
            continue
        for ref_id in pipe_values(selectable.get("source_ref_ids", "")):
            ref = source_refs.get(ref_id, {})
            variant_id = clean(ref.get("source_column_or_cell_range", ""))
            if variant_id:
                result[model_key].add(variant_id)
    return result


def selectables_review(
    selectables: list[dict[str, str]],
    display_rows: list[dict[str, str]],
    availability_rows: list[dict[str, str]],
    source_refs: dict[str, dict[str, str]],
) -> list[dict[str, Any]]:
    display = display_by_id(display_rows)
    availability = availability_by_id(availability_rows)
    out = []
    for row in selectables:
        proposal_id = clean(row.get("proposal_selectable_id", ""))
        availability_for_row = availability.get(proposal_id, [])
        source_ref_ids = pipe_values(row.get("source_ref_ids", ""))
        source_rows = [source_refs.get(ref_id, {}) for ref_id in source_ref_ids]
        status_counts = Counter(clean(item.get("availability_value", "")) for item in availability_for_row)
        out.append(
            {
                "proposal_selectable_id": proposal_id,
                "model_key": row.get("model_key", ""),
                "section_family": row.get("section_family", ""),
                "orderable_rpo": row.get("orderable_rpo", ""),
                "proposal_label": row.get("proposal_label", ""),
                "description": row.get("description", ""),
                "display_label": display.get(proposal_id, {}).get("display_label", ""),
                "review_status": row.get("review_status", ""),
                "proposal_filter_status": row.get("proposal_filter_status", ""),
                "availability_row_count": len(availability_for_row),
                "variant_count": len({clean(item.get("variant_id", "")) for item in availability_for_row if clean(item.get("variant_id", ""))}),
                "available_count": status_counts.get("available", 0),
                "standard_count": status_counts.get("standard", 0),
                "not_available_count": status_counts.get("not_available", 0),
                "source_ref_count": len(source_ref_ids),
                "source_sheets": "|".join(sorted({clean(item.get("source_sheet", "")) for item in source_rows if clean(item.get("source_sheet", ""))})),
                "source_rows_sample": "|".join(sorted({clean(item.get("source_row", "")) for item in source_rows if clean(item.get("source_row", ""))}, key=numeric)[:5]),
                "notes": "Generated review evidence only; proposal_selectable_id is not final canonical truth.",
            }
        )
    return sorted(out, key=lambda row: (row["model_key"], row["section_family"], row["orderable_rpo"], row["proposal_selectable_id"]))


def numeric(value: str) -> int:
    try:
        return int(clean(value) or 0)
    except ValueError:
        return 0


def availability_matrix(
    selectables: list[dict[str, str]],
    availability_rows: list[dict[str, str]],
    source_refs: dict[str, dict[str, str]],
) -> tuple[list[str], list[dict[str, Any]], list[dict[str, Any]]]:
    source_variant_map = source_variants_by_model(selectables, source_refs)
    source_variant_ids = {variant_id for variants_for_model in source_variant_map.values() for variant_id in variants_for_model}
    variants = variant_ids(availability_rows, source_variant_ids)
    by_id = availability_by_id(availability_rows)
    all_variants_by_model = variants_by_model(availability_rows)
    for model_key, source_variants in source_variant_map.items():
        all_variants_by_model[model_key].update(source_variants)
    matrix_rows = []
    gaps = []
    for selectable in sorted(selectables, key=lambda row: (row.get("model_key", ""), row.get("section_family", ""), row.get("orderable_rpo", ""), row.get("proposal_selectable_id", ""))):
        proposal_id = clean(selectable.get("proposal_selectable_id", ""))
        availability_for_row = by_id.get(proposal_id, [])
        cells = {clean(row.get("variant_id", "")): clean(row.get("availability_value", "")) for row in availability_for_row}
        model_variants = all_variants_by_model.get(clean(selectable.get("model_key", "")), set())
        observed = {variant_id for variant_id in cells if variant_id}
        missing = sorted(model_variants - observed)
        matrix = {
            "proposal_selectable_id": proposal_id,
            "model_key": selectable.get("model_key", ""),
            "section_family": selectable.get("section_family", ""),
            "orderable_rpo": selectable.get("orderable_rpo", ""),
            "proposal_label": selectable.get("proposal_label", ""),
            "coverage_status": "coverage_gap" if missing else "observed_in_confident_subset",
            "missing_variant_count": len(missing),
            "notes": "coverage_gap means not_observed_in_confident_subset; it is review evidence, not an error.",
        }
        for variant in variants:
            matrix[variant] = cells.get(variant, "")
        matrix_rows.append(matrix)
        if missing:
            gaps.append(
                {
                    "proposal_selectable_id": proposal_id,
                    "model_key": selectable.get("model_key", ""),
                    "section_family": selectable.get("section_family", ""),
                    "orderable_rpo": selectable.get("orderable_rpo", ""),
                    "missing_variant_count": len(missing),
                    "missing_variants_sample": "|".join(missing[:8]),
                }
            )
    return variants, matrix_rows, gaps


def model_section_counts(selectables: list[dict[str, str]], availability_rows: list[dict[str, str]], source_refs: dict[str, dict[str, str]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str], dict[str, Any]] = {}
    availability = availability_by_id(availability_rows)
    rpo_models: dict[str, set[str]] = defaultdict(set)
    for row in selectables:
        if clean(row.get("orderable_rpo", "")):
            rpo_models[clean(row.get("orderable_rpo", ""))].add(clean(row.get("model_key", "")))
    multi_model_rpos = {rpo for rpo, models in rpo_models.items() if len(models) > 1}
    for row in selectables:
        key = (clean(row.get("model_key", "")), clean(row.get("section_family", "")))
        entry = grouped.setdefault(
            key,
            {
                "model_key": key[0],
                "section_family": key[1],
                "retained_selectable_count": 0,
                "retained_availability_count": 0,
                "available_count": 0,
                "standard_count": 0,
                "not_available_count": 0,
                "rpos": set(),
                "multi_model_rpos": set(),
                "source_refs": set(),
            },
        )
        entry["retained_selectable_count"] += 1
        rpo = clean(row.get("orderable_rpo", ""))
        if rpo:
            entry["rpos"].add(rpo)
        if rpo in multi_model_rpos:
            entry["multi_model_rpos"].add(rpo)
        for ref_id in pipe_values(row.get("source_ref_ids", "")):
            if ref_id in source_refs:
                entry["source_refs"].add(ref_id)
        for availability_row in availability.get(clean(row.get("proposal_selectable_id", "")), []):
            entry["retained_availability_count"] += 1
            value = clean(availability_row.get("availability_value", ""))
            if value == "available":
                entry["available_count"] += 1
            elif value == "standard":
                entry["standard_count"] += 1
            elif value == "not_available":
                entry["not_available_count"] += 1
    rows = []
    for entry in grouped.values():
        rows.append(
            {
                "model_key": entry["model_key"],
                "section_family": entry["section_family"],
                "retained_selectable_count": entry["retained_selectable_count"],
                "retained_availability_count": entry["retained_availability_count"],
                "available_count": entry["available_count"],
                "standard_count": entry["standard_count"],
                "not_available_count": entry["not_available_count"],
                "unique_rpo_count": len(entry["rpos"]),
                "multi_model_rpo_count": len(entry["multi_model_rpos"]),
                "source_ref_count": len(entry["source_refs"]),
            }
        )
    return sorted(rows, key=lambda row: (row["model_key"], row["section_family"]))


def multi_model_rpos(selectables: list[dict[str, str]]) -> list[dict[str, Any]]:
    grouped: dict[str, dict[str, set[str] | int]] = {}
    for row in selectables:
        rpo = clean(row.get("orderable_rpo", ""))
        if not rpo:
            continue
        entry = grouped.setdefault(rpo, {"model_keys": set(), "section_families": set(), "selectable_count": 0})
        entry["model_keys"].add(clean(row.get("model_key", "")))
        entry["section_families"].add(clean(row.get("section_family", "")))
        entry["selectable_count"] += 1
    rows = []
    for rpo, entry in grouped.items():
        if len(entry["model_keys"]) > 1:
            rows.append(
                {
                    "rpo": rpo,
                    "model_keys": "|".join(sorted(entry["model_keys"])),
                    "selectable_count": entry["selectable_count"],
                    "section_families": "|".join(sorted(entry["section_families"])),
                }
            )
    return sorted(rows, key=lambda row: (row["rpo"], row["model_keys"]))


def source_trace_samples(selectables: list[dict[str, str]], source_refs: dict[str, dict[str, str]], limit_per_selectable: int = 3) -> list[dict[str, Any]]:
    rows = []
    for selectable in sorted(selectables, key=lambda row: (row.get("model_key", ""), row.get("section_family", ""), row.get("orderable_rpo", ""), row.get("proposal_selectable_id", ""))):
        for ref_id in pipe_values(selectable.get("source_ref_ids", ""))[:limit_per_selectable]:
            ref = source_refs.get(ref_id, {})
            rows.append(
                {
                    "proposal_selectable_id": selectable.get("proposal_selectable_id", ""),
                    "model_key": selectable.get("model_key", ""),
                    "section_family": selectable.get("section_family", ""),
                    "orderable_rpo": selectable.get("orderable_rpo", ""),
                    "source_ref_id": ref_id,
                    "source_sheet": ref.get("source_sheet", ""),
                    "source_row": ref.get("source_row", ""),
                    "source_field": ref.get("source_field", ""),
                    "raw_value": ref.get("raw_value", ""),
                    "source_detail_raw": ref.get("source_detail_raw", ""),
                }
            )
    return rows


def excluded_summary(rows: list[dict[str, str]]) -> dict[str, dict[str, int]]:
    return {
        "by_exclusion_reason": dict(sorted(Counter(clean(row.get("exclusion_reason", "")) or "<blank>" for row in rows).items())),
        "by_review_bucket": dict(sorted(Counter(clean(row.get("review_bucket", "")) or "<blank>" for row in rows).items())),
    }


def markdown_table(rows: list[dict[str, Any]], headers: list[str], limit: int = 12) -> str:
    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join("---" for _ in headers) + " |"]
    for row in rows[:limit]:
        lines.append("| " + " | ".join(clean(row.get(header, "")).replace("|", "\\|").replace("\n", " ") for header in headers) + " |")
    if len(rows) > limit:
        lines.append(f"\nShowing {limit} of {len(rows)} rows. Complete evidence is in the CSV outputs.")
    return "\n".join(lines)


def markdown(
    summary: dict[str, Any],
    selectables_review: list[dict[str, Any]],
    model_counts: list[dict[str, Any]],
    multi_model: list[dict[str, Any]],
    coverage_gaps: list[dict[str, Any]],
) -> str:
    return f"""# Confident Subset Review

{WARNING}

This packet is generated review evidence, not source-of-truth config. No canonical rows were applied or generated.

## Inputs

- subset: `{summary["input_summary"]["subset_path"]}`
- output: `{summary["input_summary"]["out_path"]}`

## Summary

- retained_selectables: `{summary["retained_selectables"]}`
- retained_availability_rows: `{summary["retained_availability_rows"]}`
- multi_model_rpo_count: `{summary["multi_model_rpo_count"]}`
- missing_coverage_count: `{summary["missing_coverage_count"]}`
- source_trace_sample_count: `{summary["source_trace_sample_count"]}`
- canonical_apply_ready=false

## Model/Section Summary

{markdown_table(model_counts, ["model_key", "section_family", "retained_selectable_count", "retained_availability_count", "unique_rpo_count", "multi_model_rpo_count"])}

## Multi-Model RPOs

{markdown_table(multi_model, ["rpo", "model_keys", "selectable_count", "section_families"])}

## Coverage Gaps

coverage_gap means not_observed_in_confident_subset. It is review evidence, not an error.

{markdown_table(coverage_gaps, ["proposal_selectable_id", "model_key", "section_family", "orderable_rpo", "missing_variant_count", "missing_variants_sample"])}

## Source Traceability

- retained source refs: `{summary["source_traceability"]["source_ref_count"]}`
- source trace samples: `{summary["source_trace_sample_count"]}`
- unresolved referenced source refs: `{summary["source_traceability"]["unresolved_referenced_source_ref_count"]}`

## Selectables Sample

{markdown_table(selectables_review, ["proposal_selectable_id", "model_key", "section_family", "orderable_rpo", "proposal_label", "availability_row_count", "source_ref_count"])}

## Complete CSV review surfaces

- `confident_subset_selectables_review.csv`
- `confident_subset_availability_matrix.csv`
- `confident_subset_model_section_counts.csv`
- `confident_subset_source_trace_samples.csv`

No canonical rows were applied or generated.
"""


def build_packet(subset_dir: Path) -> tuple[dict[str, Any], dict[str, list[dict[str, Any]]], str]:
    subset_report, rows, optional_presence = load_inputs(subset_dir)
    source_refs = source_ref_map(rows["source_refs"])
    selectables_review_rows = selectables_review(rows["selectables"], rows["display"], rows["availability"], source_refs)
    variants, availability_matrix_rows, coverage_gaps = availability_matrix(rows["selectables"], rows["availability"], source_refs)
    model_counts = model_section_counts(rows["selectables"], rows["availability"], source_refs)
    source_samples = source_trace_samples(rows["selectables"], source_refs)
    multi_model = multi_model_rpos(rows["selectables"])
    referenced_refs = set()
    for row in rows["selectables"]:
        referenced_refs.update(pipe_values(row.get("source_ref_ids", "")))
    for row in rows["availability"]:
        referenced_refs.add(clean(row.get("source_ref_id", "")))
    unresolved_refs = sorted(ref for ref in referenced_refs if ref and ref not in source_refs)
    summary = {
        "warning": WARNING,
        "input_summary": {
            "subset_path": "provided --subset",
            "out_path": "provided --out",
            "required_input_presence": {filename: True for filename in REQUIRED_INPUTS.values()},
            "excluded_review_rows_present": optional_presence["excluded"],
        },
        "retained_selectables": len(rows["selectables"]),
        "retained_availability_rows": len(rows["availability"]),
        "multi_model_rpo_count": len(multi_model),
        "missing_coverage_count": len(coverage_gaps),
        "source_trace_sample_count": len(source_samples),
        "canonical_apply_ready": False,
        "variant_columns": variants,
        "source_traceability": {
            "source_ref_count": len(rows["source_refs"]),
            "referenced_source_ref_count": len(referenced_refs),
            "unresolved_referenced_source_ref_count": len(unresolved_refs),
            "unresolved_referenced_source_refs": unresolved_refs[:10],
        },
        "excluded_review_rows_present": optional_presence["excluded"],
        "excluded_review_summary": excluded_summary(rows["excluded"]) if optional_presence["excluded"] else {},
        "source_subset_report_summary": {
            "confident_subset_counts": subset_report.get("confident_subset_counts", {}),
            "readiness": subset_report.get("readiness", {}),
        },
    }
    csvs = {
        "confident_subset_selectables_review.csv": selectables_review_rows,
        "confident_subset_availability_matrix.csv": availability_matrix_rows,
        "confident_subset_model_section_counts.csv": model_counts,
        "confident_subset_source_trace_samples.csv": source_samples,
    }
    return summary, csvs, markdown(summary, selectables_review_rows, model_counts, multi_model, coverage_gaps)


def write_outputs(out_dir: Path, summary: dict[str, Any], csvs: dict[str, list[dict[str, Any]]], markdown_text: str) -> None:
    write_json(out_dir / "confident_subset_review_summary.json", summary)
    write_text(out_dir / "confident_subset_review.md", markdown_text)
    headers = {
        "confident_subset_selectables_review.csv": [
            "proposal_selectable_id",
            "model_key",
            "section_family",
            "orderable_rpo",
            "proposal_label",
            "description",
            "display_label",
            "review_status",
            "proposal_filter_status",
            "availability_row_count",
            "variant_count",
            "available_count",
            "standard_count",
            "not_available_count",
            "source_ref_count",
            "source_sheets",
            "source_rows_sample",
            "notes",
        ],
        "confident_subset_availability_matrix.csv": list(csvs["confident_subset_availability_matrix.csv"][0].keys()) if csvs["confident_subset_availability_matrix.csv"] else [],
        "confident_subset_model_section_counts.csv": [
            "model_key",
            "section_family",
            "retained_selectable_count",
            "retained_availability_count",
            "available_count",
            "standard_count",
            "not_available_count",
            "unique_rpo_count",
            "multi_model_rpo_count",
            "source_ref_count",
        ],
        "confident_subset_source_trace_samples.csv": [
            "proposal_selectable_id",
            "model_key",
            "section_family",
            "orderable_rpo",
            "source_ref_id",
            "source_sheet",
            "source_row",
            "source_field",
            "raw_value",
            "source_detail_raw",
        ],
    }
    for filename, rows in csvs.items():
        write_csv(out_dir / filename, headers[filename], rows)


def main() -> int:
    args = parse_args()
    out_dir = Path(args.out)
    validate_output_dir(out_dir)
    summary, csvs, markdown_text = build_packet(Path(args.subset))
    write_outputs(out_dir, summary, csvs, markdown_text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
