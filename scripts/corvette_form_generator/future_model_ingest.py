"""Non-mutating future-model archive ingestion preview helpers.

This module projects archived Z06/ZR1/ZR1X order-guide rows into the same
option/OVS-shaped data the normalized source sheets will eventually own. It is
inspection-only: callers receive JSON-serializable preview data and this module
never saves or mutates the workbook.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
import re
from typing import Any, Iterable

from corvette_form_generator.workbook import clean


@dataclass(frozen=True)
class FutureModelSpec:
    model_key: str
    archive_sheet: str
    target_option_sheet: str
    target_ovs_sheet: str
    variant_columns: dict[str, str]


FUTURE_MODEL_SPECS: dict[str, FutureModelSpec] = {
    "z06": FutureModelSpec(
        model_key="z06",
        archive_sheet="archive_Z06_Ingest",
        target_option_sheet="z06_options",
        target_ovs_sheet="z06_ovs",
        variant_columns={
            "1LZ Coupe": "1lz_h07",
            "2LZ Coupe": "2lz_h07",
            "3LZ Coupe": "3lz_h07",
            "1LZ Convertible": "1lz_h67",
            "2LZ Convertible": "2lz_h67",
            "3LZ Convertible": "3lz_h67",
        },
    ),
    "zr1": FutureModelSpec(
        model_key="zr1",
        archive_sheet="archive_ZR1_Ingest",
        target_option_sheet="zr1_options",
        target_ovs_sheet="zr1_ovs",
        variant_columns={
            "1LZ Coupe": "1lz_r07",
            "3LZ Coupe": "3lz_r07",
            "1LZ Convertible": "1lz_r67",
            "3LZ Convertible": "3lz_r67",
        },
    ),
    "zr1x": FutureModelSpec(
        model_key="zr1x",
        archive_sheet="archive_ZR1X_Ingest",
        target_option_sheet="zr1x_options",
        target_ovs_sheet="zr1x_ovs",
        variant_columns={
            "1LZ Coupe": "1lz_s07",
            "3LZ Coupe": "3lz_s07",
            "1LZ Convertible": "1lz_s67",
            "3LZ Convertible": "3lz_s67",
        },
    ),
}

_STATUS_MAP = {
    "standard": "standard",
    "available": "available",
    "not available": "unavailable",
}

_REVIEW_KEYS = (
    "resolved",
    "section_conflict",
    "section_unresolved",
    "missing_rpo",
    "duplicate_rpo",
    "blank_variant_status",
    "unknown_status",
    "price_type_issue",
    "candidate_id_collision",
)


def normalize_status(value: Any) -> tuple[str | None, str | None]:
    """Return normalized OVS status and optional review flag for archive text."""

    text = clean(value)
    if not text:
        return None, None
    normalized = _STATUS_MAP.get(text.lower())
    if normalized:
        return normalized, None
    return None, "unknown_status"


def normalize_match_text(value: Any) -> str:
    return re.sub(r"\s+", " ", clean(value).casefold()).strip()


def active_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    text = clean(value).casefold()
    if not text:
        return False
    return text in {"true", "1", "yes", "y", "active"}


def parse_price(value: Any) -> tuple[int | float | None, str | None]:
    """Parse a preview price while preserving blank as None and explicit zero as 0."""

    if value is None:
        return None, None
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if isinstance(value, float) and value.is_integer():
            return int(value), None
        return value, None
    text = clean(value)
    if not text:
        return None, None
    stripped = text.replace("$", "").replace(",", "").strip()
    try:
        numeric = float(stripped)
    except ValueError:
        return None, "price_type_issue"
    if numeric.is_integer():
        return int(numeric), None
    return numeric, None


def _header_names(ws) -> list[str]:
    first_row = next(ws.iter_rows(min_row=1, max_row=1, values_only=True), ())
    return [clean(value) for value in first_row]


def rows_from_archive_sheet(wb, sheet_name: str) -> list[dict[str, Any]]:
    ws = wb[sheet_name]
    headers = _header_names(ws)
    rows: list[dict[str, Any]] = []
    for row_idx, values in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
        record: dict[str, Any] = {"_source_row": row_idx}
        has_value = False
        for header, value in zip(headers, values):
            if not header:
                continue
            record[header] = clean(value)
            if clean(value):
                has_value = True
        if has_value:
            rows.append(record)
    return rows


def _rows_from_sheet(wb, sheet_name: str) -> list[dict[str, Any]]:
    if sheet_name not in wb.sheetnames:
        return []
    ws = wb[sheet_name]
    headers = _header_names(ws)
    rows: list[dict[str, Any]] = []
    for values in ws.iter_rows(min_row=2, values_only=True):
        record = {header: clean(value) for header, value in zip(headers, values) if header}
        if any(record.values()):
            rows.append(record)
    return rows


def build_section_candidates(wb) -> dict[str, Any]:
    """Build exact and RPO-only section evidence from active normalized sources."""

    exact: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)
    by_rpo: dict[str, list[dict[str, str]]] = defaultdict(list)
    for sheet_name in ("stingray_options", "grandSport_options"):
        for row in _rows_from_sheet(wb, sheet_name):
            if not active_bool(row.get("active")):
                continue
            rpo = clean(row.get("rpo"))
            section_id = clean(row.get("section_id"))
            if not rpo or not section_id:
                continue
            candidate = {
                "source_sheet": sheet_name,
                "option_id": clean(row.get("option_id")),
                "rpo": rpo,
                "option_name": clean(row.get("option_name")),
                "section_id": section_id,
                "display_behavior": clean(row.get("display_behavior")),
            }
            by_rpo[normalize_match_text(rpo)].append(candidate)
            exact[(normalize_match_text(rpo), normalize_match_text(row.get("option_name")))].append(candidate)
    return {"exact": dict(exact), "rpo": dict(by_rpo)}


def resolve_section(row: dict[str, Any], candidates: dict[str, dict[Any, list[dict[str, str]]]]) -> dict[str, Any]:
    rpo = clean(row.get("rpo"))
    option_name = clean(row.get("option_name"))
    if not rpo:
        return {
            "section_id": "",
            "section_resolution": "unresolved",
            "section_candidates": [],
            "display_behavior": "",
        }

    exact_matches = candidates.get("exact", {}).get((normalize_match_text(rpo), normalize_match_text(option_name)), [])
    matched_by = "exact" if exact_matches else "rpo"
    matches = exact_matches or candidates.get("rpo", {}).get(normalize_match_text(rpo), [])
    section_ids = sorted({candidate["section_id"] for candidate in matches if candidate.get("section_id")})
    display_behaviors = sorted({candidate["display_behavior"] for candidate in exact_matches if candidate.get("display_behavior")})

    if not section_ids:
        return {
            "section_id": "",
            "section_resolution": "unresolved",
            "section_candidates": [],
            "display_behavior": "",
        }
    if len(section_ids) > 1:
        return {
            "section_id": "",
            "section_resolution": "conflict",
            "section_candidates": section_ids,
            "display_behavior": "",
        }
    return {
        "section_id": section_ids[0],
        "section_resolution": "resolved",
        "section_candidates": section_ids,
        "display_behavior": display_behaviors[0] if matched_by == "exact" and len(display_behaviors) == 1 else "",
    }


def _slug_id_part(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", value.casefold()).strip("_")
    return slug or "review"


def _propose_option_id(rpo: str, source_order: int, rpo_sequence: int) -> str:
    if rpo:
        return f"opt_{_slug_id_part(rpo)}_{rpo_sequence:03d}"
    return f"opt_review_{source_order:03d}"


def _status_values_for_row(row: dict[str, Any], spec: FutureModelSpec) -> tuple[list[dict[str, str]], list[str]]:
    statuses: list[dict[str, str]] = []
    flags: list[str] = []
    for source_column, variant_id in spec.variant_columns.items():
        normalized, status_flag = normalize_status(row.get(source_column))
        if normalized:
            statuses.append(
                {
                    "variant_id": variant_id,
                    "status": normalized,
                    "source_variant_column": source_column,
                }
            )
        elif status_flag:
            flags.append(status_flag)
        else:
            flags.append("blank_variant_status")
    return statuses, flags


def _dedupe_flags(flags: Iterable[str]) -> list[str]:
    return sorted(set(flag for flag in flags if flag))


def build_preview_for_model(wb, spec: FutureModelSpec, candidates: dict[str, Any] | None = None) -> dict[str, Any]:
    """Build an option/OVS-shaped, review-only preview for one future model."""

    archive_rows = rows_from_archive_sheet(wb, spec.archive_sheet)
    candidates = candidates or build_section_candidates(wb)
    rpo_counts = Counter(clean(row.get("RPO")) for row in archive_rows if clean(row.get("RPO")))
    rpo_seen: Counter[str] = Counter()
    option_ids_seen: Counter[str] = Counter()

    proposed_options: list[dict[str, Any]] = []
    proposed_ovs: list[dict[str, Any]] = []
    review_rows: list[dict[str, Any]] = []
    review_counts = {key: 0 for key in _REVIEW_KEYS}
    status_counts: Counter[str] = Counter()
    section_resolution_counts: Counter[str] = Counter()

    for source_order, row in enumerate(archive_rows, start=1):
        rpo = clean(row.get("RPO"))
        rpo_seen[rpo] += 1 if rpo else 0
        option_id = _propose_option_id(rpo, source_order, rpo_seen[rpo] if rpo else 1)
        option_ids_seen[option_id] += 1

        price, price_flag = parse_price(row.get("Price"))
        statuses, status_flags = _status_values_for_row(row, spec)
        for status in statuses:
            status_counts[status["status"]] += 1

        section_input = {"rpo": rpo, "option_name": clean(row.get("Option Name"))}
        section = resolve_section(section_input, candidates)
        section_resolution_counts[section["section_resolution"]] += 1

        flags: list[str] = []
        if section["section_resolution"] == "resolved":
            review_counts["resolved"] += 1
        elif section["section_resolution"] == "conflict":
            flags.append("section_conflict")
        else:
            flags.append("section_unresolved")
        if not rpo:
            flags.append("missing_rpo")
        elif rpo_counts[rpo] > 1:
            flags.append("duplicate_rpo")
        if price_flag:
            flags.append(price_flag)
        flags.extend(status_flags)
        if option_ids_seen[option_id] > 1:
            flags.append("candidate_id_collision")
        flags = _dedupe_flags(flags)
        for flag in flags:
            review_counts[flag] += 1

        option = {
            "option_id": option_id,
            "rpo": rpo,
            "price": price,
            "option_name": clean(row.get("Option Name")),
            "description": clean(row.get("Description")),
            "detail_raw": clean(row.get("Detail")),
            "section_id": section["section_id"],
            "selectable": any(status["status"] == "available" for status in statuses),
            "display_order": source_order,
            "active": bool(statuses),
            "display_behavior": section["display_behavior"],
            "model_key": spec.model_key,
            "source_sheet": spec.archive_sheet,
            "source_row": row["_source_row"],
            "source_category": clean(row.get("Category")),
            "section_resolution": section["section_resolution"],
            "section_candidates": section["section_candidates"],
            "review_status": "needs_review" if flags else "resolved",
            "review_reason": "; ".join(flags),
        }
        proposed_options.append(option)
        if flags:
            review_rows.append(option)

        for status in statuses:
            proposed_ovs.append(
                {
                    "option_id": option_id,
                    "variant_id": status["variant_id"],
                    "status": status["status"],
                    "model_key": spec.model_key,
                    "source_sheet": spec.archive_sheet,
                    "source_row": row["_source_row"],
                    "source_variant_column": status["source_variant_column"],
                }
            )

    summary = {
        "archive_row_count": len(archive_rows),
        "proposed_option_count": len(proposed_options),
        "proposed_ovs_count": len(proposed_ovs),
        "status_counts": dict(sorted(status_counts.items())),
        "section_resolution_counts": dict(sorted(section_resolution_counts.items())),
        "review_counts": review_counts,
        "review_row_count": len(review_rows),
    }
    return {
        "model_key": spec.model_key,
        "archive_sheet": spec.archive_sheet,
        "target_option_sheet": spec.target_option_sheet,
        "target_ovs_sheet": spec.target_ovs_sheet,
        "variant_columns": spec.variant_columns,
        "summary": summary,
        "proposed_options": proposed_options,
        "proposed_ovs": proposed_ovs,
        "review_rows": review_rows,
    }


def build_future_model_preview(wb, *, generated_at: str | None = None) -> dict[str, Any]:
    """Build the full non-mutating preview for all known future models."""

    timestamp = generated_at or datetime.now(timezone.utc).isoformat(timespec="seconds")
    candidates = build_section_candidates(wb)
    return {
        "generated_at": timestamp,
        "models": {model_key: build_preview_for_model(wb, spec, candidates) for model_key, spec in FUTURE_MODEL_SPECS.items()},
        "notes": [
            "Inspection-only artifact: stingray_master.xlsx was read but not saved.",
            "Proposed option IDs and section mappings are draft-only until manual review resolves conflicts and missing RPO rows.",
        ],
    }


def _examples(rows: list[dict[str, Any]], predicate, limit: int = 8) -> list[str]:
    examples: list[str] = []
    for row in rows:
        if predicate(row):
            label = row.get("rpo") or "<missing RPO>"
            examples.append(f"row {row['source_row']}: {label} — {row.get('option_name', '')}")
        if len(examples) >= limit:
            break
    return examples


def render_preview_markdown(preview: dict[str, Any]) -> str:
    lines: list[str] = []
    lines.append("# Future Model Source Preview")
    lines.append("")
    lines.append(f"Generated: {preview['generated_at']}")
    lines.append("")
    lines.append("Inspection-only: workbook source sheets were not written, model activation was not changed, and runtime app data was not generated.")
    lines.append("")
    for model_key, model in preview["models"].items():
        summary = model["summary"]
        lines.append(f"## {model_key}")
        lines.append("")
        lines.append(f"- Archive sheet: `{model['archive_sheet']}`")
        lines.append(f"- Future option target: `{model['target_option_sheet']}`")
        lines.append(f"- Future OVS target: `{model['target_ovs_sheet']}`")
        lines.append(f"- Archive rows: {summary['archive_row_count']}")
        lines.append(f"- Proposed option rows: {summary['proposed_option_count']}")
        lines.append(f"- Proposed OVS rows: {summary['proposed_ovs_count']}")
        lines.append("")
        lines.append("Variant columns:")
        for source_column, variant_id in model["variant_columns"].items():
            lines.append(f"- `{source_column}` -> `{variant_id}`")
        lines.append("")
        lines.append("Status counts:")
        for status, count in summary["status_counts"].items():
            lines.append(f"- {status}: {count}")
        if not summary["status_counts"]:
            lines.append("- none")
        lines.append("")
        lines.append("Section resolution counts:")
        for resolution, count in summary["section_resolution_counts"].items():
            lines.append(f"- {resolution}: {count}")
        lines.append("")
        lines.append("Review counts:")
        for key, count in summary["review_counts"].items():
            lines.append(f"- {key}: {count}")
        lines.append("")

        unresolved = _examples(model["proposed_options"], lambda row: row["section_resolution"] == "unresolved" and row.get("rpo"))
        conflicts = _examples(model["proposed_options"], lambda row: row["section_resolution"] == "conflict")
        missing_rpos = _examples(model["proposed_options"], lambda row: not row.get("rpo"))
        duplicate_rpos = _examples(model["proposed_options"], lambda row: "duplicate_rpo" in row.get("review_reason", ""))

        lines.append("Top unresolved RPO/name examples:")
        lines.extend(f"- {example}" for example in unresolved) if unresolved else lines.append("- none")
        lines.append("")
        lines.append("Top section conflicts:")
        if conflicts:
            for example in conflicts:
                row_num = int(example.split(":", 1)[0].replace("row", "").strip())
                row = next(option for option in model["proposed_options"] if option["source_row"] == row_num)
                lines.append(f"- {example}; candidates: {', '.join(row['section_candidates'])}")
        else:
            lines.append("- none")
        lines.append("")
        lines.append("Missing-RPO examples:")
        lines.extend(f"- {example}" for example in missing_rpos) if missing_rpos else lines.append("- none")
        lines.append("")
        lines.append("Duplicate-RPO examples:")
        lines.extend(f"- {example}" for example in duplicate_rpos) if duplicate_rpos else lines.append("- none")
        lines.append("")
    lines.append("## Recommended next step")
    lines.append("")
    lines.append("Create review maps/manual decisions for missing RPO rows, duplicate RPO identity, and section conflicts before writing normalized future source sheets.")
    lines.append("")
    return "\n".join(lines)
