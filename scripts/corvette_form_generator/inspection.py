"""Read-only model source inspection helpers."""

from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from openpyxl import load_workbook

from corvette_form_generator.mapping import best_status, status_to_label, step_for_section
from corvette_form_generator.model_config import ModelConfig
from corvette_form_generator.workbook import clean, money, rows_from_sheet


ALLOWED_STATUSES = {"available", "standard", "unavailable"}
STATUS_ALIASES = {
    "available": "available",
    "standard": "standard",
    "not available": "unavailable",
    "unavailable": "unavailable",
}
RULE_HOT_SPOT_PATTERNS = {
    "requires": re.compile(r"\brequires?\b", re.IGNORECASE),
    "not_available": re.compile(r"\bnot available\b", re.IGNORECASE),
    "included_with": re.compile(r"\bincluded with\b", re.IGNORECASE),
    "includes": re.compile(r"\bincludes?\b", re.IGNORECASE),
    "only": re.compile(r"\bonly\b", re.IGNORECASE),
    "replaces": re.compile(r"\breplaces?\b", re.IGNORECASE),
    "not_recommended": re.compile(r"\bnot recommended\b", re.IGNORECASE),
    "except": re.compile(r"\bexcept\b", re.IGNORECASE),
}
SPECIAL_REVIEW_RPOS = {"EL9", "Z25", "FEY", "Z15"}


def normalize_status(value: Any) -> str:
    text = clean(value).lower()
    return STATUS_ALIASES.get(text, text)


def normalize_selectable(value: Any) -> str:
    text = clean(value).lower()
    if text in {"yes", "true", "1", "y"}:
        return "True"
    if text in {"no", "false", "0", "n"}:
        return "False"
    return clean(value)


def normalized_option_row(row: dict[str, str], config: ModelConfig) -> dict[str, Any]:
    option_id = clean(row.get("option_id", ""))
    original_section_id = clean(row.get("Section", ""))
    resolved_section_id = original_section_id or config.blank_section_overrides.get(option_id, "")
    return {
        "option_id": option_id,
        "rpo": clean(row.get("RPO", "")),
        "price": money(row.get("Price")),
        "option_name": clean(row.get("Option Name", "")),
        "description": clean(row.get("Description", "")),
        "detail_raw": clean(row.get("Detail", "")),
        "category_id": clean(row.get("Category", "")),
        "selectable": normalize_selectable(row.get("Selectable", "")),
        "original_section_id": original_section_id,
        "section_id": resolved_section_id,
        "section_override_applied": bool(not original_section_id and resolved_section_id),
        "statuses": {variant_id: normalize_status(row.get(variant_id, "")) for variant_id in config.variant_ids},
    }


def inspect_model_sources(config: ModelConfig) -> dict[str, Any]:
    wb = load_workbook(config.workbook_path, data_only=True, read_only=True)
    raw_rows = rows_from_sheet(wb, config.source_option_sheet)
    variants_raw = rows_from_sheet(wb, "variant_master")
    categories = {row["category_id"]: row for row in rows_from_sheet(wb, "category_master")}
    sections = {row["section_id"]: row for row in rows_from_sheet(wb, "section_master")}
    rows = [normalized_option_row(row, config) for row in raw_rows]

    variant_rows = [row for row in variants_raw if row.get("variant_id", "") in config.variant_ids]
    active_variant_ids = {row["variant_id"] for row in variant_rows if row.get("active") == "True"}
    configured_variant_ids = set(config.variant_ids)

    status_counts: Counter[str] = Counter()
    status_counts_by_variant: dict[str, Counter[str]] = {variant_id: Counter() for variant_id in config.variant_ids}
    unknown_status_cells: list[dict[str, Any]] = []
    missing_status_cells: list[dict[str, Any]] = []
    matrix_rows: list[dict[str, Any]] = []
    candidate_choices: list[dict[str, Any]] = []
    candidate_standard_equipment: list[dict[str, Any]] = []

    for row in rows:
        normalized_statuses = [status for status in row["statuses"].values() if status]
        effective_status = best_status(*normalized_statuses)
        matrix_rows.append(
            {
                "option_id": row["option_id"],
                "rpo": row["rpo"],
                "effective_status": effective_status,
                "effective_status_label": status_to_label(effective_status),
                "statuses": row["statuses"],
            }
        )
        for variant_id, status in row["statuses"].items():
            if not status:
                missing_status_cells.append({"option_id": row["option_id"], "rpo": row["rpo"], "variant_id": variant_id})
                continue
            status_counts[status] += 1
            status_counts_by_variant[variant_id][status] += 1
            if status not in ALLOWED_STATUSES:
                unknown_status_cells.append(
                    {
                        "option_id": row["option_id"],
                        "rpo": row["rpo"],
                        "variant_id": variant_id,
                        "status": status,
                    }
                )
            if status in {"available", "standard"}:
                candidate_choices.append(
                    {
                        "choice_id": f"{variant_id}__{row['option_id']}",
                        "option_id": row["option_id"],
                        "rpo": row["rpo"],
                        "variant_id": variant_id,
                        "status": status,
                        "selectable": row["selectable"],
                        "section_id": row["section_id"],
                    }
                )
            if status == "standard":
                candidate_standard_equipment.append(
                    {
                        "option_id": row["option_id"],
                        "rpo": row["rpo"],
                        "variant_id": variant_id,
                        "section_id": row["section_id"],
                        "option_name": row["option_name"],
                    }
                )

    selectable_counts = Counter(row["selectable"] or "<blank>" for row in rows)
    active_rows = [row for row in rows if any(status in {"available", "standard"} for status in row["statuses"].values())]
    standard_rows = [row for row in rows if any(status == "standard" for status in row["statuses"].values())]
    unique_rpos = sorted({row["rpo"] for row in rows if row["rpo"]})

    section_mapping_rows: list[dict[str, Any]] = []
    missing_sections: Counter[str] = Counter()
    unknown_sections: Counter[str] = Counter()
    unknown_categories: Counter[str] = Counter()
    section_category_mismatches: list[dict[str, Any]] = []
    for row in rows:
        section_id = row["section_id"]
        category_id = row["category_id"]
        if not section_id:
            missing_sections[row["option_id"]] += 1
        elif section_id not in sections:
            unknown_sections[section_id] += 1
        if category_id and category_id not in categories:
            unknown_categories[category_id] += 1
        section = sections.get(section_id, {})
        if section and category_id and section.get("category_id") != category_id:
            section_category_mismatches.append(
                {
                    "option_id": row["option_id"],
                    "rpo": row["rpo"],
                    "section_id": section_id,
                    "row_category_id": category_id,
                    "section_category_id": section.get("category_id", ""),
                }
            )
        step_key = step_for_section(
            section_id,
            section.get("section_name", ""),
            section.get("category_id", category_id),
            standard_sections=config.standard_sections,
            section_step_overrides=config.section_step_overrides,
        )
        section_mapping_rows.append(
            {
                "option_id": row["option_id"],
                "rpo": row["rpo"],
                "category_id": category_id,
                "section_id": section_id,
                "original_section_id": row["original_section_id"],
                "section_override_applied": row["section_override_applied"],
                "step_key": step_key,
            }
        )

    blank_section_overrides = []
    for option_id, configured_section_id in config.blank_section_overrides.items():
        row = next((candidate for candidate in rows if candidate["option_id"] == option_id), None)
        blank_section_overrides.append(
            {
                "option_id": option_id,
                "rpo": row["rpo"] if row else "",
                "source_section_blank": bool(row and not row["original_section_id"]),
                "configured_section_id": configured_section_id,
                "resolved_section_id": row["section_id"] if row else "",
                "handled_by_explicit_config": bool(row and row["section_override_applied"] and row["section_id"] == configured_section_id),
            }
        )

    rule_hot_spots = []
    hot_spot_counts: Counter[str] = Counter()
    special_mentions: defaultdict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        text = "\n".join(part for part in (row["detail_raw"], row["description"], row["option_name"]) if part)
        matched_terms = [name for name, pattern in RULE_HOT_SPOT_PATTERNS.items() if pattern.search(text)]
        for term in matched_terms:
            hot_spot_counts[term] += 1
        mentioned_specials = [rpo for rpo in SPECIAL_REVIEW_RPOS if re.search(rf"\b{re.escape(rpo)}\b", text)]
        if matched_terms or row["rpo"] in SPECIAL_REVIEW_RPOS or mentioned_specials:
            record = {
                "option_id": row["option_id"],
                "rpo": row["rpo"],
                "option_name": row["option_name"],
                "section_id": row["section_id"],
                "matched_terms": matched_terms,
                "special_mentions": mentioned_specials,
                "detail_raw": row["detail_raw"],
            }
            rule_hot_spots.append(record)
            for rpo in mentioned_specials:
                special_mentions[rpo].append(
                    {
                        "option_id": row["option_id"],
                        "rpo": row["rpo"],
                        "option_name": row["option_name"],
                    }
                )

    warnings = []
    if len(variant_rows) != config.expected_variant_count:
        warnings.append(f"Expected {config.expected_variant_count} configured variants, found {len(variant_rows)} in variant_master.")
    if configured_variant_ids - active_variant_ids:
        warnings.append(
            "Configured Grand Sport variants are present but inactive in variant_master, preserving the live Stingray-only generator path: "
            f"{', '.join(sorted(configured_variant_ids - active_variant_ids))}."
        )
    if missing_status_cells:
        warnings.append(f"Missing status cells: {len(missing_status_cells)}.")
    if unknown_status_cells:
        warnings.append(f"Unknown status cells: {len(unknown_status_cells)}.")
    if missing_sections:
        warnings.append(f"Rows still missing resolved sections: {sum(missing_sections.values())}.")
    if unknown_sections:
        warnings.append(f"Unknown resolved section ids: {', '.join(sorted(unknown_sections))}.")
    if unknown_categories:
        warnings.append(f"Unknown category ids: {', '.join(sorted(unknown_categories))}.")
    if section_category_mismatches:
        warnings.append(f"Section/category mismatches: {len(section_category_mismatches)}.")
    unresolved_blank_overrides = [row["option_id"] for row in blank_section_overrides if not row["handled_by_explicit_config"]]
    if unresolved_blank_overrides:
        warnings.append(f"Configured blank-section overrides not resolved: {', '.join(unresolved_blank_overrides)}.")

    return {
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "status": "inspection_generated",
        "config": {
            "model_key": config.model_key,
            "model_label": config.model_label,
            "model_year": config.model_year,
            "source_option_sheet": config.source_option_sheet,
            "variant_ids": list(config.variant_ids),
            "expected_variant_count": config.expected_variant_count,
            "blank_section_overrides": dict(config.blank_section_overrides),
            "notes": list(config.notes),
        },
        "variants": {
            "configured_count": len(config.variant_ids),
            "expected_count": config.expected_variant_count,
            "found_in_variant_master": variant_rows,
            "missing_from_variant_master": sorted(configured_variant_ids - {row["variant_id"] for row in variant_rows}),
            "inactive_configured": sorted(configured_variant_ids - active_variant_ids),
        },
        "counts": {
            "option_rows": len(rows),
            "unique_rpos": len(unique_rpos),
            "variant_status_cells": len(rows) * len(config.variant_ids),
            "candidate_choice_rows_available_or_standard": len(candidate_choices),
            "candidate_standard_equipment_cells": len(candidate_standard_equipment),
            "candidate_standard_option_rows": len(standard_rows),
            "selectable_counts": dict(sorted(selectable_counts.items())),
            "active_option_rows_available_or_standard": len(active_rows),
            "inactive_option_rows_all_unavailable_or_blank": len(rows) - len(active_rows),
            "status_counts": dict(sorted(status_counts.items())),
            "status_counts_by_variant": {
                variant_id: dict(sorted(counts.items())) for variant_id, counts in status_counts_by_variant.items()
            },
            "missing_status_cells": len(missing_status_cells),
            "unknown_status_cells": len(unknown_status_cells),
        },
        "unique_rpos": unique_rpos,
        "status_matrix": matrix_rows,
        "section_mappings": {
            "rows": section_mapping_rows,
            "missing_sections": dict(sorted(missing_sections.items())),
            "unknown_sections": dict(sorted(unknown_sections.items())),
            "unknown_categories": dict(sorted(unknown_categories.items())),
            "section_category_mismatches": section_category_mismatches,
        },
        "blank_section_overrides": blank_section_overrides,
        "candidate_standard_equipment": candidate_standard_equipment,
        "candidate_choices_sample": candidate_choices[:100],
        "rule_detail_hot_spots": {
            "counts": dict(sorted(hot_spot_counts.items())),
            "rows": rule_hot_spots,
            "special_mentions": {rpo: rows for rpo, rows in sorted(special_mentions.items())},
        },
        "missing_status_cells": missing_status_cells,
        "unknown_status_cells": unknown_status_cells,
        "warnings": warnings,
    }


def write_inspection_artifacts(report: dict[str, Any], output_dir: Path) -> dict[str, str]:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "grand-sport-inspection.json"
    md_path = output_dir / "grand-sport-inspection.md"
    json_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    md_path.write_text(render_markdown_report(report), encoding="utf-8")
    return {"json": str(json_path), "markdown": str(md_path)}


def render_markdown_report(report: dict[str, Any]) -> str:
    counts = report["counts"]
    warnings = report["warnings"]
    section_mappings = report["section_mappings"]
    hot_spots = report["rule_detail_hot_spots"]
    lines = [
        "# Grand Sport Inspection",
        "",
        f"Generated: `{report['generated_at']}`",
        f"Source sheet: `{report['config']['source_option_sheet']}`",
        f"Status: `{report['status']}`",
        "",
        "## Variant Validation",
        "",
        f"- Configured variants: {', '.join(report['config']['variant_ids'])}",
        f"- Found in `variant_master`: {len(report['variants']['found_in_variant_master'])}",
        f"- Missing from `variant_master`: {', '.join(report['variants']['missing_from_variant_master']) or 'none'}",
        f"- Inactive configured variants: {', '.join(report['variants']['inactive_configured']) or 'none'}",
        "",
        "## Counts",
        "",
        f"- Option rows: {counts['option_rows']}",
        f"- Unique RPOs: {counts['unique_rpos']}",
        f"- Variant status cells: {counts['variant_status_cells']}",
        f"- Candidate choice rows with available/standard status: {counts['candidate_choice_rows_available_or_standard']}",
        f"- Candidate standard equipment cells: {counts['candidate_standard_equipment_cells']}",
        f"- Candidate standard option rows: {counts['candidate_standard_option_rows']}",
        f"- Active option rows with available/standard status: {counts['active_option_rows_available_or_standard']}",
        f"- Inactive option rows all unavailable/blank: {counts['inactive_option_rows_all_unavailable_or_blank']}",
        f"- Selectable counts: `{json.dumps(counts['selectable_counts'], sort_keys=True)}`",
        f"- Status counts: `{json.dumps(counts['status_counts'], sort_keys=True)}`",
        f"- Missing status cells: {counts['missing_status_cells']}",
        f"- Unknown status cells: {counts['unknown_status_cells']}",
        "",
        "## Section Mapping",
        "",
        f"- Rows still missing resolved sections: {sum(section_mappings['missing_sections'].values())}",
        f"- Unknown section ids: {', '.join(section_mappings['unknown_sections']) or 'none'}",
        f"- Unknown category ids: {', '.join(section_mappings['unknown_categories']) or 'none'}",
        f"- Section/category mismatches: {len(section_mappings['section_category_mismatches'])}",
        "",
        "## Blank-Section Overrides",
        "",
    ]
    for row in report["blank_section_overrides"]:
        handled = "yes" if row["handled_by_explicit_config"] else "no"
        lines.append(
            f"- `{row['rpo']}` / `{row['option_id']}`: blank source section -> `{row['resolved_section_id']}` "
            f"(configured `{row['configured_section_id']}`, handled by config: {handled})"
        )
    lines.extend(
        [
            "",
            "## Rule/Detail Hot Spots",
            "",
            f"- Hot spot counts: `{json.dumps(hot_spots['counts'], sort_keys=True)}`",
            f"- Rows requiring later rule review: {len(hot_spots['rows'])}",
            "",
            "| RPO | Option | Section | Matched Terms | Special Mentions |",
            "| --- | --- | --- | --- | --- |",
        ]
    )
    for row in hot_spots["rows"][:40]:
        lines.append(
            "| "
            + " | ".join(
                [
                    f"`{row['rpo']}`",
                    row["option_name"].replace("|", "\\|"),
                    f"`{row['section_id']}`",
                    ", ".join(row["matched_terms"]) or "",
                    ", ".join(row["special_mentions"]) or "",
                ]
            )
            + " |"
        )
    if len(hot_spots["rows"]) > 40:
        lines.append(f"| ... | {len(hot_spots['rows']) - 40} additional rows in JSON artifact |  |  |  |")
    lines.extend(["", "## Warnings", ""])
    if warnings:
        lines.extend(f"- {warning}" for warning in warnings)
    else:
        lines.append("- none")
    lines.append("")
    return "\n".join(lines)
