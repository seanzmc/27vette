"""Non-mutating future-model raw order-guide ingestion preview helpers.

This module projects raw Z06/ZR1/ZR1X order-guide rows into the same
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

RAW_SOURCE_SHEETS: dict[str, str] = {
    "z06_standard_raw": "standard_equipment",
    "z06_intextmec_raw": "interior_exterior_mechanical",
    "zr1_zr1x_standard_raw": "standard_equipment",
    "zr1_zr1x_intextmec_raw": "interior_exterior_mechanical",
}

RAW_VARIANT_MAP: dict[tuple[str, str], tuple[str, str]] = {
    ("1YH07", "1LZ"): ("z06", "1lz_h07"),
    ("1YH07", "2LZ"): ("z06", "2lz_h07"),
    ("1YH07", "3LZ"): ("z06", "3lz_h07"),
    ("1YH67", "1LZ"): ("z06", "1lz_h67"),
    ("1YH67", "2LZ"): ("z06", "2lz_h67"),
    ("1YH67", "3LZ"): ("z06", "3lz_h67"),
    ("1YR07", "1LZ"): ("zr1", "1lz_r07"),
    ("1YR07", "3LZ"): ("zr1", "3lz_r07"),
    ("1YR67", "1LZ"): ("zr1", "1lz_r67"),
    ("1YR67", "3LZ"): ("zr1", "3lz_r67"),
    ("1YS07", "1LZ"): ("zr1x", "1lz_s07"),
    ("1YS07", "3LZ"): ("zr1x", "3lz_s07"),
    ("1YS67", "1LZ"): ("zr1x", "1lz_s67"),
    ("1YS67", "3LZ"): ("zr1x", "3lz_s67"),
}

RAW_VARIANT_IDS = (
    "1lz_h07",
    "2lz_h07",
    "3lz_h07",
    "1lz_h67",
    "2lz_h67",
    "3lz_h67",
    "1lz_r07",
    "3lz_r07",
    "1lz_r67",
    "3lz_r67",
    "1lz_s07",
    "3lz_s07",
    "1lz_s67",
    "3lz_s67",
)

FUTURE_MODEL_SOURCE_REVIEW_HEADERS = (
    "model_key",
    "source_group",
    "raw_source_sheets",
    "raw_source_spans",
    "raw_category_context",
    "source_orderable_rpo",
    "source_ref_rpo",
    "source_primary_rpo",
    "source_option_description",
    "source_disclosure_raw",
    "source_disclosure_map",
    "source_detail_raw",
    "candidate_option_id",
    "candidate_section_id",
    "candidate_section_resolution",
    "candidate_section_candidates",
    "candidate_display_behavior",
    "candidate_price",
    "price_candidate_rows",
    "price_candidate_summary",
    "base_model_list_price",
    "base_model_dfc",
    "base_model_total_price",
    "review_flags",
    "approved_option_id",
    "approved_rpo",
    "approved_price",
    "approved_option_name",
    "approved_description",
    "approved_detail_raw",
    "approved_section_id",
    "approved_selectable",
    "approved_display_behavior",
    "approved_display_order",
    "copy_from_model_key",
    "copy_from_option_id",
    "duplicate_group_id",
    "review_status",
    "review_reason",
    "active",
    "notes",
    *(f"raw_status_{variant_id}" for variant_id in RAW_VARIANT_IDS),
    *(f"status_{variant_id}" for variant_id in RAW_VARIANT_IDS),
    *(f"status_note_{variant_id}" for variant_id in RAW_VARIANT_IDS),
)

OPTION_SOURCE_HEADERS = (
    "option_id",
    "rpo",
    "price",
    "option_name",
    "description",
    "detail_raw",
    "section_id",
    "selectable",
    "display_order",
    "active",
    "display_behavior",
)

OVS_SOURCE_HEADERS = (
    "option_id",
    "variant_id",
    "status",
)

VALID_SOURCE_STATUSES = {"available", "standard", "unavailable"}

BLOCKING_REVIEW_FLAGS = {
    "section_conflict",
    "section_unresolved",
    "missing_rpo",
    "blank_variant_status",
    "unknown_status",
    "candidate_id_collision",
    "price_type_issue",
}

_RAW_STATUS_FLAGS = {
    "D": "dealer_installed_status",
    "■": "included_in_equipment_group",
    "□": "included_in_equipment_group_upgradeable",
}


def normalize_raw_status(value: Any) -> tuple[str | None, str, str | None]:
    """Return normalized status, numeric disclosure note ref, and optional flag."""

    text = clean(value)
    if not text:
        return None, "", None
    upper = text.upper()
    if upper == "--":
        return "unavailable", "", None
    if upper in {"S", "A"}:
        return ("standard" if upper == "S" else "available"), "", None
    match = re.fullmatch(r"([SA])(\d+)", upper)
    if match:
        prefix, note_ref = match.groups()
        return ("standard" if prefix == "S" else "available"), note_ref, None
    dealer_match = re.fullmatch(r"(?:A/)?D(\d*)", upper)
    if dealer_match:
        return "available", dealer_match.group(1), "dealer_installed_status"
    included_match = re.fullmatch(r"([■□])(\d*)", text)
    if included_match:
        symbol, note_ref = included_match.groups()
        return (
            "standard",
            note_ref,
            "included_in_equipment_group" if symbol == "■" else "included_in_equipment_group_upgradeable",
        )
    if text in _RAW_STATUS_FLAGS:
        return "standard" if text in {"■", "□"} else "available", "", _RAW_STATUS_FLAGS[text]
    return None, "", "unknown_status"


def _merged_anchor_lookup(ws) -> dict[tuple[int, int], tuple[int, int, int, int]]:
    lookup: dict[tuple[int, int], tuple[int, int, int, int]] = {}
    merged_cells = getattr(ws, "merged_cells", None)
    if not merged_cells:
        return lookup
    for merged_range in merged_cells.ranges:
        for row in range(merged_range.min_row, merged_range.max_row + 1):
            for col in range(merged_range.min_col, merged_range.max_col + 1):
                lookup[(row, col)] = (
                    merged_range.min_row,
                    merged_range.min_col,
                    merged_range.max_row,
                    merged_range.max_col,
                )
    return lookup


def _cell_value(ws, row: int, col: int, merge_lookup: dict[tuple[int, int], tuple[int, int, int, int]] | None = None) -> Any:
    if merge_lookup and (row, col) in merge_lookup:
        anchor_row, anchor_col, _, _ = merge_lookup[(row, col)]
        return ws.cell(anchor_row, anchor_col).value
    return ws.cell(row, col).value


def _is_merged_child(row: int, col: int, merge_lookup: dict[tuple[int, int], tuple[int, int, int, int]]) -> bool:
    if (row, col) not in merge_lookup:
        return False
    anchor_row, anchor_col, _, _ = merge_lookup[(row, col)]
    return (row, col) != (anchor_row, anchor_col)


def _raw_variant_columns(ws) -> list[dict[str, Any]]:
    columns: list[dict[str, Any]] = []
    for col in range(4, ws.max_column + 1):
        model_label = clean(ws.cell(7, col).value)
        model_code = clean(ws.cell(8, col).value)
        trim = clean(ws.cell(9, col).value)
        mapped = RAW_VARIANT_MAP.get((model_code, trim))
        if not mapped:
            continue
        model_key, variant_id = mapped
        columns.append(
            {
                "column": col,
                "model_label": model_label,
                "model_code": model_code,
                "trim": trim,
                "model_key": model_key,
                "variant_id": variant_id,
            }
        )
    return columns


def _has_status_value(ws, row: int, variant_columns: list[dict[str, Any]], merge_lookup: dict[tuple[int, int], tuple[int, int, int, int]]) -> bool:
    return any(clean(_cell_value(ws, row, int(column["column"]), merge_lookup)) for column in variant_columns)


def _raw_option_block_start(ws, row: int, variant_columns: list[dict[str, Any]], merge_lookup: dict[tuple[int, int], tuple[int, int, int, int]]) -> bool:
    description = clean(ws.cell(row, 3).value)
    if not description or description.casefold() == "description":
        return False
    if not _has_status_value(ws, row, variant_columns, merge_lookup):
        return False
    relevant_cols = [1, 2] + [int(column["column"]) for column in variant_columns]
    return not any(_is_merged_child(row, col, merge_lookup) for col in relevant_cols)


def _raw_category_context(ws, row: int, variant_columns: list[dict[str, Any]], current_category: str) -> str:
    if _has_status_value(ws, row, variant_columns, {}):
        return current_category
    text = clean(ws.cell(row, 1).value) or clean(ws.cell(row, 3).value)
    return text or current_category


def parse_raw_option_sheet(wb, sheet_name: str) -> list[dict[str, Any]]:
    """Parse one raw order-guide sheet into model-scoped option blocks."""

    if sheet_name not in wb.sheetnames:
        return []
    ws = wb[sheet_name]
    source_group = RAW_SOURCE_SHEETS[sheet_name]
    merge_lookup = _merged_anchor_lookup(ws)
    variant_columns = _raw_variant_columns(ws)
    blocks: list[dict[str, Any]] = []
    current_category = ""

    for row in range(10, ws.max_row + 1):
        if not _raw_option_block_start(ws, row, variant_columns, merge_lookup):
            current_category = _raw_category_context(ws, row, variant_columns, current_category)
            continue

        block_end = row
        for col in [1, 2] + [int(column["column"]) for column in variant_columns]:
            if (row, col) in merge_lookup:
                _, _, end_row, _ = merge_lookup[(row, col)]
                block_end = max(block_end, end_row)

        disclosures: list[dict[str, Any]] = []
        for disclosure_row in range(row + 1, block_end + 1):
            text = clean(ws.cell(disclosure_row, 3).value)
            if text:
                disclosures.append({"row": disclosure_row, "text": text})
        disclosure_map = {str(index): item["text"] for index, item in enumerate(disclosures, start=1)}

        source_orderable_rpo = clean(_cell_value(ws, row, 1, merge_lookup))
        source_ref_rpo = clean(_cell_value(ws, row, 2, merge_lookup))
        source_primary_rpo = source_orderable_rpo or source_ref_rpo

        by_model: dict[str, dict[str, Any]] = defaultdict(lambda: {
            "raw_statuses": {},
            "statuses": {},
            "status_notes": {},
            "status_note_texts": {},
            "status_flags": [],
        })
        for column in variant_columns:
            raw_status = clean(_cell_value(ws, row, int(column["column"]), merge_lookup))
            normalized, note_ref, flag = normalize_raw_status(raw_status)
            model_bucket = by_model[str(column["model_key"])]
            variant_id = str(column["variant_id"])
            model_bucket["raw_statuses"][variant_id] = raw_status
            if normalized:
                model_bucket["statuses"][variant_id] = normalized
            if note_ref:
                model_bucket["status_notes"][variant_id] = note_ref
                model_bucket["status_note_texts"][variant_id] = disclosure_map.get(note_ref, "")
            if flag:
                model_bucket["status_flags"].append(flag)

        for model_key, model_bucket in by_model.items():
            if not any(model_bucket["raw_statuses"].values()):
                continue
            blocks.append(
                {
                    "model_key": model_key,
                    "source_group": source_group,
                    "raw_source_sheet": sheet_name,
                    "raw_source_span": f"{sheet_name}:{row}-{block_end}",
                    "raw_start_row": row,
                    "raw_end_row": block_end,
                    "raw_category_context": current_category,
                    "source_orderable_rpo": source_orderable_rpo,
                    "source_ref_rpo": source_ref_rpo,
                    "source_primary_rpo": source_primary_rpo,
                    "source_option_description": clean(ws.cell(row, 3).value),
                    "source_disclosure_rows": [item["row"] for item in disclosures],
                    "source_disclosure_raw": "\n".join(item["text"] for item in disclosures),
                    "source_disclosure_map": disclosure_map,
                    "raw_statuses": dict(model_bucket["raw_statuses"]),
                    "statuses": dict(model_bucket["statuses"]),
                    "status_notes": dict(model_bucket["status_notes"]),
                    "status_note_texts": dict(model_bucket["status_note_texts"]),
                    "status_flags": _dedupe_flags(model_bucket["status_flags"]),
                }
            )

    return blocks


def build_raw_source_blocks(wb) -> list[dict[str, Any]]:
    """Parse all present raw option sheets into model-scoped option blocks."""

    blocks: list[dict[str, Any]] = []
    for sheet_name in RAW_SOURCE_SHEETS:
        blocks.extend(parse_raw_option_sheet(wb, sheet_name))
    return blocks


def _numeric_or_none(value: Any) -> int | float | None:
    parsed, flag = parse_price(value)
    return None if flag else parsed


def _first_numeric_col(ws, row: int, start_col: int = 4) -> int | None:
    for col in range(start_col, ws.max_column + 1):
        if _numeric_or_none(ws.cell(row, col).value) is not None:
            return col
    return None


def build_price_schedule_rows(wb) -> dict[str, list[dict[str, Any]]]:
    """Parse raw price schedule rows as review evidence."""

    if "price_sched_raw" not in wb.sheetnames:
        return {"base_model_prices": [], "option_price_rows": [], "gas_guzzler_rows": []}
    ws = wb["price_sched_raw"]
    base_model_prices: list[dict[str, Any]] = []
    option_price_rows: list[dict[str, Any]] = []
    gas_guzzler_rows: list[dict[str, Any]] = []
    section = ""

    for row in range(1, ws.max_row + 1):
        marker = (clean(ws.cell(row, 1).value) or clean(ws.cell(row, 2).value)).casefold()
        if marker == "base model prices":
            section = "base_models"
            continue
        if marker.startswith("additional options"):
            section = "options"
            continue
        if marker == "gas guzzler tax":
            section = "gas_guzzler"
            continue
        if section == "gas_guzzler" and marker.endswith(":"):
            section = "options"
            continue

        code = clean(ws.cell(row, 2).value)
        description = clean(ws.cell(row, 3).value)
        if not code or code in {"Model", "Option Code"} or not description:
            continue

        if section == "base_models" and re.fullmatch(r"1Y[A-Z]\d{2}", code):
            list_col = _first_numeric_col(ws, row, 4)
            list_price = _numeric_or_none(ws.cell(row, list_col).value) if list_col else None
            dfc_col = None
            for col in range(4, ws.max_column + 1):
                if clean(ws.cell(6, col).value).casefold() == "dfc":
                    dfc_col = col
                    break
            dfc = _numeric_or_none(ws.cell(row, dfc_col).value) if dfc_col else None
            total = (list_price or 0) + (dfc or 0)
            base_model_prices.append(
                {
                    "raw_price_row": row,
                    "model_code": code,
                    "model_description": description,
                    "list_price": list_price,
                    "dfc": dfc,
                    "total_price": total,
                }
            )
        elif section == "options":
            price_col = _first_numeric_col(ws, row, 4)
            option_price_rows.append(
                {
                    "raw_price_row": row,
                    "price_rpo": code,
                    "price_description": description,
                    "price_application": clean(ws.cell(row, 4).value),
                    "price_list": _numeric_or_none(ws.cell(row, price_col).value) if price_col else None,
                }
            )
        elif section == "gas_guzzler":
            price_col = _first_numeric_col(ws, row, 4)
            gas_guzzler_rows.append(
                {
                    "raw_price_row": row,
                    "price_rpo": code,
                    "price_description": description,
                    "price_list": _numeric_or_none(ws.cell(row, price_col).value) if price_col else None,
                    "pending_certification_placeholder": True,
                }
            )

    return {
        "base_model_prices": base_model_prices,
        "option_price_rows": option_price_rows,
        "gas_guzzler_rows": gas_guzzler_rows,
    }


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


def _format_disclosure_map(disclosure_map: dict[str, str]) -> str:
    return " | ".join(f"{key}={value}" for key, value in sorted(disclosure_map.items(), key=lambda item: int(item[0])))


def _review_price_candidates(block: dict[str, Any], price_rows: dict[str, list[dict[str, Any]]]) -> tuple[Any, str, str, list[str]]:
    rpo = clean(block.get("source_primary_rpo"))
    if not rpo:
        return "", "", "", []
    matches = [row for row in price_rows.get("option_price_rows", []) if clean(row.get("price_rpo")) == rpo]
    if not matches:
        return "", "", "", []
    rows = "|".join(str(row["raw_price_row"]) for row in matches)
    summary = " | ".join(
        f"row {row['raw_price_row']}: {row.get('price_list', '')} {row.get('price_application', '')}".strip()
        for row in matches
    )
    if len(matches) == 1:
        return matches[0].get("price_list", ""), rows, summary, []
    return "", rows, summary, ["price_schedule_multiple_candidates"]


def build_source_review_rows(wb) -> list[dict[str, Any]]:
    """Build workbook-ready future_model_source_review rows from raw source blocks."""

    blocks = build_raw_source_blocks(wb)
    candidates = build_section_candidates(wb)
    price_rows = build_price_schedule_rows(wb)
    rpo_counts = Counter(
        (block["model_key"], clean(block.get("source_primary_rpo")))
        for block in blocks
        if clean(block.get("source_primary_rpo"))
    )
    rpo_seen: Counter[tuple[str, str]] = Counter()
    rows: list[dict[str, Any]] = []

    for source_order, block in enumerate(blocks, start=1):
        model_key = clean(block.get("model_key"))
        rpo = clean(block.get("source_primary_rpo"))
        rpo_key = (model_key, rpo)
        if rpo:
            rpo_seen[rpo_key] += 1
        option_id = _propose_option_id(rpo, source_order, rpo_seen[rpo_key] if rpo else 1)
        section = resolve_section({"rpo": rpo, "option_name": block.get("source_option_description")}, candidates)
        candidate_price, price_candidate_rows, price_summary, price_flags = _review_price_candidates(block, price_rows)

        flags: list[str] = []
        if section["section_resolution"] == "conflict":
            flags.append("section_conflict")
        elif section["section_resolution"] != "resolved":
            flags.append("section_unresolved")
        if not rpo:
            flags.append("missing_rpo")
        elif rpo_counts[rpo_key] > 1:
            flags.append("duplicate_rpo")
        flags.extend(block.get("status_flags", []))
        flags.extend(price_flags)
        flags = _dedupe_flags(flags)

        review_status = "needs_review" if flags else "approved"
        active = not flags
        row = {header: "" for header in FUTURE_MODEL_SOURCE_REVIEW_HEADERS}
        row.update(
            {
                "model_key": model_key,
                "source_group": block.get("source_group", ""),
                "raw_source_sheets": block.get("raw_source_sheet", ""),
                "raw_source_spans": block.get("raw_source_span", ""),
                "raw_category_context": block.get("raw_category_context", ""),
                "source_orderable_rpo": block.get("source_orderable_rpo", ""),
                "source_ref_rpo": block.get("source_ref_rpo", ""),
                "source_primary_rpo": rpo,
                "source_option_description": block.get("source_option_description", ""),
                "source_disclosure_raw": block.get("source_disclosure_raw", ""),
                "source_disclosure_map": _format_disclosure_map(block.get("source_disclosure_map", {})),
                "source_detail_raw": block.get("source_disclosure_raw", ""),
                "candidate_option_id": option_id,
                "candidate_section_id": section["section_id"],
                "candidate_section_resolution": section["section_resolution"],
                "candidate_section_candidates": "|".join(section["section_candidates"]),
                "candidate_display_behavior": section["display_behavior"],
                "candidate_price": candidate_price,
                "price_candidate_rows": price_candidate_rows,
                "price_candidate_summary": price_summary,
                "review_flags": "; ".join(flags),
                "approved_option_id": option_id if active else "",
                "approved_rpo": rpo if active else "",
                "approved_price": candidate_price if active else "",
                "approved_option_name": block.get("source_option_description", "") if active else "",
                "approved_description": "",
                "approved_detail_raw": block.get("source_disclosure_raw", "") if active else "",
                "approved_section_id": section["section_id"] if active else "",
                "approved_selectable": any(status == "available" for status in block.get("statuses", {}).values()) if active else "",
                "approved_display_behavior": section["display_behavior"] if active else "",
                "approved_display_order": source_order if active else "",
                "review_status": review_status,
                "review_reason": "; ".join(flags),
                "active": active,
            }
        )
        for variant_id, raw_status in block.get("raw_statuses", {}).items():
            row[f"raw_status_{variant_id}"] = raw_status
        for variant_id, status in block.get("statuses", {}).items():
            row[f"status_{variant_id}"] = status
        for variant_id, note_ref in block.get("status_notes", {}).items():
            row[f"status_note_{variant_id}"] = note_ref
        rows.append(row)

    return rows


def _split_review_flags(value: Any) -> list[str]:
    return [flag.strip() for flag in clean(value).split(";") if flag.strip()]


def _intish_string(value: Any) -> str:
    text = clean(value)
    if not text:
        return ""
    numeric = float(text)
    if numeric.is_integer():
        return str(int(numeric))
    return text


def _selected_future_model_keys(model_keys: Iterable[str]) -> list[str]:
    requested = [clean(model_key) for model_key in model_keys if clean(model_key)]
    if not requested or requested == ["all"]:
        return list(FUTURE_MODEL_SPECS)
    if "all" in requested:
        return list(FUTURE_MODEL_SPECS)
    unknown = [model_key for model_key in requested if model_key not in FUTURE_MODEL_SPECS]
    if unknown:
        raise ValueError(f"Unknown future model key(s): {', '.join(unknown)}")
    return requested


def _section_ids(wb) -> set[str]:
    return {clean(row.get("section_id")) for row in _rows_from_sheet(wb, "section_master") if clean(row.get("section_id"))}


def _current_sheet_row_count(wb, sheet_name: str) -> int:
    return len(_rows_from_sheet(wb, sheet_name))


def _validation_errors_for_approved_row(row: dict[str, Any], spec: FutureModelSpec, section_ids: set[str], duplicate_option_ids: set[str]) -> list[str]:
    errors: list[str] = []
    option_id = clean(row.get("approved_option_id"))
    review_flags = set(_split_review_flags(row.get("review_flags")))
    blocking_flags = sorted(review_flags & BLOCKING_REVIEW_FLAGS)
    if blocking_flags:
        errors.append(f"blocking review flag(s): {', '.join(blocking_flags)}")
    if "price_schedule_multiple_candidates" in review_flags and clean(row.get("approved_price")):
        errors.append("price_schedule_multiple_candidates requires blank approved_price")
    for field in ("approved_option_id", "approved_rpo", "approved_option_name", "approved_section_id"):
        if not clean(row.get(field)):
            errors.append(f"{field} is required")
    section_id = clean(row.get("approved_section_id"))
    if section_id and section_id not in section_ids:
        errors.append(f"approved_section_id {section_id} is not in section_master")
    if not clean(row.get("approved_display_order")):
        errors.append("approved_display_order is required")
    else:
        try:
            _intish_string(row.get("approved_display_order"))
        except ValueError:
            errors.append("approved_display_order must be numeric")
    if option_id and option_id in duplicate_option_ids:
        errors.append(f"duplicate approved_option_id {option_id}")
    for variant_id in spec.variant_columns.values():
        status = clean(row.get(f"status_{variant_id}"))
        if not status:
            errors.append(f"status_{variant_id} is required")
        elif status not in VALID_SOURCE_STATUSES:
            errors.append(f"status_{variant_id} has invalid value {status}")
    return errors


def _option_row_from_review(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "option_id": clean(row.get("approved_option_id")),
        "rpo": clean(row.get("approved_rpo")),
        "price": clean(row.get("approved_price")),
        "option_name": clean(row.get("approved_option_name")),
        "description": clean(row.get("approved_description")),
        "detail_raw": clean(row.get("approved_detail_raw")),
        "section_id": clean(row.get("approved_section_id")),
        "selectable": clean(row.get("approved_selectable")),
        "display_order": _intish_string(row.get("approved_display_order")),
        "active": clean(row.get("active")),
        "display_behavior": clean(row.get("approved_display_behavior")),
    }


def _source_label(row: dict[str, Any]) -> str:
    return clean(row.get("raw_source_spans")) or clean(row.get("approved_option_id")) or clean(row.get("candidate_option_id")) or "review row"


def build_future_source_population_plan(wb, model_keys: Iterable[str]) -> dict[str, Any]:
    """Materialize approved future_model_source_review rows without mutating a workbook."""

    selected_model_keys = _selected_future_model_keys(model_keys)
    review_rows = _rows_from_sheet(wb, "future_model_source_review")
    section_ids = _section_ids(wb)
    plan: dict[str, Any] = {
        "selected_model_keys": selected_model_keys,
        "models": {},
        "error_count": 0,
    }

    for model_key in selected_model_keys:
        spec = FUTURE_MODEL_SPECS[model_key]
        model_rows = [row for row in review_rows if clean(row.get("model_key")) == model_key]
        approved_active_rows = [
            row for row in model_rows
            if clean(row.get("review_status")) == "approved" and active_bool(row.get("active"))
        ]
        option_id_counts = Counter(clean(row.get("approved_option_id")) for row in approved_active_rows if clean(row.get("approved_option_id")))
        duplicate_option_ids = {option_id for option_id, count in option_id_counts.items() if count > 1}

        option_rows: list[dict[str, Any]] = []
        ovs_rows: list[dict[str, Any]] = []
        blocked_counts: Counter[str] = Counter()
        errors: list[str] = []

        for row in model_rows:
            review_status = clean(row.get("review_status"))
            active = active_bool(row.get("active"))
            review_flags = _split_review_flags(row.get("review_flags"))
            if review_status != "approved":
                blocked_counts[review_status or "not_approved"] += 1
                for flag in review_flags:
                    blocked_counts[flag] += 1
                if not active:
                    blocked_counts["inactive"] += 1
                continue
            if not active:
                blocked_counts["inactive"] += 1
                for flag in review_flags:
                    blocked_counts[flag] += 1
                continue

            row_errors = _validation_errors_for_approved_row(row, spec, section_ids, duplicate_option_ids)
            if row_errors:
                for flag in review_flags:
                    blocked_counts[flag] += 1
                for error in row_errors:
                    blocked_counts[error] += 1
                errors.append(f"{_source_label(row)}: {'; '.join(row_errors)}")
                continue

            option_row = _option_row_from_review(row)
            option_rows.append(option_row)
            for variant_id in spec.variant_columns.values():
                ovs_rows.append(
                    {
                        "option_id": option_row["option_id"],
                        "variant_id": variant_id,
                        "status": clean(row.get(f"status_{variant_id}")),
                    }
                )

        display_order = {row["option_id"]: (float(clean(row.get("display_order")) or 0), row["option_id"]) for row in option_rows}
        option_rows.sort(key=lambda row: display_order[row["option_id"]])
        variant_order = {variant_id: index for index, variant_id in enumerate(spec.variant_columns.values())}
        ovs_rows.sort(key=lambda row: (display_order[row["option_id"]], variant_order[row["variant_id"]]))

        model_plan = {
            "model_key": model_key,
            "target_option_sheet": spec.target_option_sheet,
            "target_ovs_sheet": spec.target_ovs_sheet,
            "current_option_rows": _current_sheet_row_count(wb, spec.target_option_sheet),
            "current_ovs_rows": _current_sheet_row_count(wb, spec.target_ovs_sheet),
            "would_write_option_rows": len(option_rows),
            "would_write_ovs_rows": len(ovs_rows),
            "eligible_option_count": len(option_rows),
            "emitted_ovs_count": len(ovs_rows),
            "blocked_counts": dict(sorted(blocked_counts.items())),
            "errors": errors,
            "option_rows": option_rows,
            "ovs_rows": ovs_rows,
        }
        plan["models"][model_key] = model_plan
        plan["error_count"] += len(errors)

    return plan


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


def _raw_preview_for_model(model_key: str, review_rows: list[dict[str, Any]]) -> dict[str, Any]:
    model_rows = [row for row in review_rows if row.get("model_key") == model_key]
    spec = FUTURE_MODEL_SPECS[model_key]
    status_counts: Counter[str] = Counter()
    review_counts = {key: 0 for key in _REVIEW_KEYS}
    review_counts["price_schedule_multiple_candidates"] = 0
    review_counts["dealer_installed_status"] = 0
    review_counts["included_in_equipment_group"] = 0
    review_counts["included_in_equipment_group_upgradeable"] = 0
    section_resolution_counts: Counter[str] = Counter()
    proposed_ovs: list[dict[str, Any]] = []
    for row in model_rows:
        section_resolution_counts[clean(row.get("candidate_section_resolution"))] += 1
        for flag in clean(row.get("review_flags")).split("; "):
            if flag:
                review_counts.setdefault(flag, 0)
                review_counts[flag] += 1
        if not clean(row.get("review_flags")):
            review_counts["resolved"] += 1
        for variant_id in spec.variant_columns.values():
            status = clean(row.get(f"status_{variant_id}"))
            if not status:
                continue
            status_counts[status] += 1
            proposed_ovs.append(
                {
                    "option_id": row.get("candidate_option_id"),
                    "variant_id": variant_id,
                    "status": status,
                    "raw_status": row.get(f"raw_status_{variant_id}"),
                    "status_note_ref": row.get(f"status_note_{variant_id}"),
                    "model_key": model_key,
                    "source_sheet": row.get("raw_source_sheets"),
                    "source_span": row.get("raw_source_spans"),
                }
            )
    return {
        "model_key": model_key,
        "source_mode": "raw_order_guide",
        "target_option_sheet": spec.target_option_sheet,
        "target_ovs_sheet": spec.target_ovs_sheet,
        "variant_columns": spec.variant_columns,
        "summary": {
            "raw_source_block_count": len(model_rows),
            "review_row_count": len(model_rows),
            "proposed_option_count": len(model_rows),
            "proposed_ovs_count": len(proposed_ovs),
            "status_counts": dict(sorted(status_counts.items())),
            "section_resolution_counts": dict(sorted(section_resolution_counts.items())),
            "review_counts": review_counts,
        },
        "proposed_options": model_rows,
        "proposed_ovs": proposed_ovs,
        "review_rows": model_rows,
    }


def _has_raw_source_sheets(wb) -> bool:
    return any(sheet_name in wb.sheetnames for sheet_name in RAW_SOURCE_SHEETS)


def build_future_model_preview(wb, *, generated_at: str | None = None) -> dict[str, Any]:
    """Build the full non-mutating preview for all known future models."""

    timestamp = generated_at or datetime.now(timezone.utc).isoformat(timespec="seconds")
    if _has_raw_source_sheets(wb):
        review_rows = build_source_review_rows(wb)
        return {
            "generated_at": timestamp,
            "source_mode": "raw_order_guide",
            "models": {model_key: _raw_preview_for_model(model_key, review_rows) for model_key in FUTURE_MODEL_SPECS},
            "price_schedule": build_price_schedule_rows(wb),
            "notes": [
                "Raw order-guide sheets were read but workbook source sheets were not written.",
                "Merged RPO/status cells are parsed as option blocks; disclosure rows are attached as provenance/detail text.",
                "Option IDs, sections, prices, and status-note mappings are draft-only until manual review.",
            ],
        }

    candidates = build_section_candidates(wb)
    return {
        "generated_at": timestamp,
        "source_mode": "legacy_archive",
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
            label = row.get("rpo") or row.get("source_primary_rpo") or "<missing RPO>"
            source = row.get("source_row") or row.get("raw_source_spans") or "unknown source"
            name = row.get("option_name") or row.get("source_option_description") or ""
            examples.append(f"{source}: {label} — {name}")
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
        if preview.get("source_mode") == "raw_order_guide":
            lines.append("- Source mode: raw order-guide sheets")
        else:
            lines.append(f"- Archive sheet: `{model['archive_sheet']}`")
        lines.append(f"- Future option target: `{model['target_option_sheet']}`")
        lines.append(f"- Future OVS target: `{model['target_ovs_sheet']}`")
        if "archive_row_count" in summary:
            lines.append(f"- Archive rows: {summary['archive_row_count']}")
        if "raw_source_block_count" in summary:
            lines.append(f"- Raw source blocks: {summary['raw_source_block_count']}")
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

        unresolved = _examples(model["proposed_options"], lambda row: clean(row.get("section_resolution") or row.get("candidate_section_resolution")) == "unresolved" and clean(row.get("rpo") or row.get("source_primary_rpo")))
        conflicts = _examples(model["proposed_options"], lambda row: clean(row.get("section_resolution") or row.get("candidate_section_resolution")) == "conflict")
        missing_rpos = _examples(model["proposed_options"], lambda row: not clean(row.get("rpo") or row.get("source_primary_rpo")))
        duplicate_rpos = _examples(model["proposed_options"], lambda row: "duplicate_rpo" in clean(row.get("review_reason") or row.get("review_flags")))

        lines.append("Top unresolved RPO/name examples:")
        lines.extend(f"- {example}" for example in unresolved) if unresolved else lines.append("- none")
        lines.append("")
        lines.append("Top section conflicts:")
        if conflicts:
            for example in conflicts:
                lines.append(f"- {example}")
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
