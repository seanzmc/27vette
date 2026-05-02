"""Shared helpers for Chevrolet order guide import staging scripts."""

from __future__ import annotations

import csv
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

from openpyxl import load_workbook


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_STATUS_SYMBOLS = ROOT / "data" / "import_maps" / "chevrolet_common" / "status_symbols.csv"
DEFAULT_PHRASE_PATTERNS = ROOT / "data" / "import_maps" / "chevrolet_common" / "phrase_patterns.csv"
DEFAULT_SHEET_ROLES = ROOT / "data" / "import_maps" / "corvette_2027" / "sheet_roles.csv"

PRIMARY_MATRIX_ROLES = {"primary_variant_matrix"}
VARIANT_HEADER_RE = re.compile(r"(?P<body_style>[A-Za-z]+)\s+(?P<body_code>\d?[A-Z]{2}\d{2})\s+(?P<trim>[0-9A-Z]{2,3})")
RPO_RE = re.compile(r"\b[A-Z0-9]{3}\b")

STAGING_OUTPUTS = {
    "sheets": [
        "sheet_name",
        "sheet_role",
        "section_family",
        "model_group_index",
        "model_key",
        "scope_type",
        "creates_canonical_candidates",
        "notes",
    ],
    "variants": [
        "source_sheet",
        "model_key",
        "variant_label",
        "body_code",
        "body_style",
        "trim_level",
        "inferred_variant_id",
        "source_cell_range",
        "confidence",
        "notes",
    ],
    "variant_matrix_rows": [
        "source_sheet",
        "source_row",
        "model_key",
        "section_family",
        "orderable_rpo",
        "ref_rpo",
        "description",
        "variant_id",
        "body_code",
        "body_style",
        "trim_level",
        "raw_status",
        "status_symbol",
        "footnote_refs",
        "canonical_status",
        "source_detail_raw",
    ],
    "color_trim_rows": [
        "source_sheet",
        "source_row",
        "model_key",
        "scope_type",
        "exterior_color_rpo",
        "exterior_color_name",
        "interior_code",
        "interior_label",
        "seat_code",
        "trim_level",
        "raw_status",
        "status_symbol",
        "footnote_refs",
        "canonical_status",
        "source_detail_raw",
    ],
    "equipment_group_rows": [
        "source_sheet",
        "source_row",
        "model_key",
        "equipment_group_rpo",
        "orderable_rpo",
        "ref_rpo",
        "description",
        "row_kind",
        "matched_primary_row_key",
        "match_status",
        "source_detail_raw",
    ],
    "price_rows": [
        "source_sheet",
        "source_row",
        "model_key",
        "price_block_label",
        "raw_values",
        "notes",
    ],
    "status_symbols": [
        "source_sheet",
        "status_symbol",
        "raw_status_examples",
        "count",
        "canonical_status",
    ],
    "rule_phrase_candidates": [
        "source_sheet",
        "source_row",
        "model_key",
        "source_field",
        "raw_text",
        "phrase_type",
        "extracted_rpos",
        "confidence",
        "review_status",
        "notes",
    ],
    "unresolved_rows": [
        "source_sheet",
        "source_row",
        "raw_values",
        "reason",
        "review_status",
    ],
    "ignored_rows": [
        "source_sheet",
        "source_row",
        "raw_values",
        "reason",
    ],
}


def clean(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value).strip()


def raw_row_values(values: list[Any]) -> str:
    return json.dumps([clean(value) for value in values], ensure_ascii=False, separators=(",", ":"))


def load_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def load_status_map(path: Path = DEFAULT_STATUS_SYMBOLS) -> dict[str, dict[str, str]]:
    return {row["raw_symbol"]: row for row in load_csv_rows(path)}


def load_phrase_patterns(path: Path = DEFAULT_PHRASE_PATTERNS) -> list[dict[str, Any]]:
    rows = []
    for row in load_csv_rows(path):
        rows.append({**row, "compiled": re.compile(row["pattern"], re.IGNORECASE)})
    return rows


def load_sheet_role_rows(path: Path = DEFAULT_SHEET_ROLES) -> list[dict[str, Any]]:
    rows = []
    for row in load_csv_rows(path):
        rows.append({**row, "compiled": re.compile(row["sheet_name_pattern"])})
    return rows


def classify_sheet(sheet_name: str, role_rows: list[dict[str, Any]]) -> dict[str, str]:
    for row in role_rows:
        match = row["compiled"].match(sheet_name)
        if not match:
            continue
        model_group_index = clean(row.get("model_group_index", ""))
        if not model_group_index and row.get("model_group_index_source") == "sheet_number":
            model_group_index = clean(match.groupdict().get("index", ""))
        return {
            "sheet_name": sheet_name,
            "sheet_role": row["sheet_role"],
            "section_family": row["section_family"],
            "scope_type": row["scope_type"],
            "creates_canonical_candidates": row["creates_canonical_candidates"].lower(),
            "model_key": row["model_key"],
            "model_group_index": model_group_index,
            "notes": row["notes"],
        }
    return {
        "sheet_name": sheet_name,
        "sheet_role": "ignored_or_unknown",
        "section_family": "unknown",
        "scope_type": "unknown",
        "creates_canonical_candidates": "false",
        "model_key": "",
        "model_group_index": "",
        "notes": "No matching sheet role map row.",
    }


def load_workbook_readonly(source: Path):
    return load_workbook(source, read_only=True, data_only=True)


def worksheet_rows(ws) -> list[tuple[int, list[str]]]:
    rows = []
    for row_index, values in enumerate(ws.iter_rows(values_only=True), start=1):
        rows.append((row_index, [clean(value) for value in values]))
    return rows


def is_blank(values: list[str]) -> bool:
    return not any(clean(value) for value in values)


def find_matrix_header(rows: list[tuple[int, list[str]]]) -> tuple[int, list[str]] | None:
    for row_index, values in rows:
        normalized = [value.lower() for value in values]
        if "orderable rpo code" in normalized and "description" in normalized:
            return row_index, values
    return None


def parse_variant_header(value: str) -> dict[str, str]:
    text = re.sub(r"\s+", " ", clean(value).replace("\n", " ")).strip()
    match = VARIANT_HEADER_RE.search(text)
    if not match:
        return {
            "variant_label": text,
            "body_code": "",
            "body_style": "",
            "trim_level": "",
            "inferred_variant_id": "",
            "confidence": "low",
        }
    body_style = match.group("body_style").lower()
    body_code = match.group("body_code")
    trim = match.group("trim")
    return {
        "variant_label": text,
        "body_code": body_code,
        "body_style": body_style,
        "trim_level": trim,
        "inferred_variant_id": f"{trim.lower()}_{body_code[-3:].lower()}",
        "confidence": "medium",
    }


def variant_columns(header_values: list[str]) -> list[dict[str, str]]:
    columns = []
    for index, value in enumerate(header_values, start=1):
        parsed = parse_variant_header(value)
        if parsed["body_code"] or "\n" in value:
            columns.append({**parsed, "column_index": str(index), "source_cell_range": f"{column_letter(index)}"})
    return columns


def column_letter(index: int) -> str:
    letters = ""
    while index:
        index, remainder = divmod(index - 1, 26)
        letters = chr(65 + remainder) + letters
    return letters


def parse_status(raw_status: str, status_map: dict[str, dict[str, str]]) -> dict[str, str]:
    raw = clean(raw_status)
    if not raw:
        return {"raw_status": "", "status_symbol": "", "footnote_refs": "", "canonical_status": ""}
    for symbol in sorted(status_map, key=len, reverse=True):
        if raw.startswith(symbol):
            return {
                "raw_status": raw,
                "status_symbol": symbol,
                "footnote_refs": raw[len(symbol) :],
                "canonical_status": status_map[symbol]["canonical_status"],
            }
    return {"raw_status": raw, "status_symbol": raw[:1], "footnote_refs": raw[1:], "canonical_status": "unknown"}


def rule_phrase_candidates(
    *,
    source_sheet: str,
    source_row: int,
    model_key: str,
    source_field: str,
    raw_text: str,
    patterns: list[dict[str, Any]],
) -> list[dict[str, str]]:
    text = clean(raw_text)
    if not text:
        return []
    candidates = []
    extracted_rpos = "|".join(sorted(set(RPO_RE.findall(text))))
    for pattern in patterns:
        if pattern["compiled"].search(text):
            candidates.append(
                {
                    "source_sheet": source_sheet,
                    "source_row": str(source_row),
                    "model_key": model_key,
                    "source_field": source_field,
                    "raw_text": text,
                    "phrase_type": pattern["phrase_type"],
                    "extracted_rpos": extracted_rpos,
                    "confidence": pattern["confidence"],
                    "review_status": "needs_review",
                    "notes": "Staging candidate only; no canonical rule generated.",
                }
            )
    return candidates


def write_csv(path: Path, headers: list[str], rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    normalized_rows = [{header: clean(row.get(header, "")) for header in headers} for row in rows]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=headers, lineterminator="\n")
        writer.writeheader()
        writer.writerows(normalized_rows)


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


def profile_workbook(source: Path) -> dict[str, Any]:
    wb = load_workbook_readonly(source)
    role_rows = load_sheet_role_rows()
    status_map = load_status_map()
    patterns = load_phrase_patterns()
    sheets = []
    status_counter: Counter[tuple[str, str]] = Counter()
    rule_candidate_count = 0
    variant_count = 0
    price_row_count = 0

    for sheet_name in wb.sheetnames:
        ws = wb[sheet_name]
        classification = classify_sheet(sheet_name, role_rows)
        rows = worksheet_rows(ws)
        header = find_matrix_header(rows)
        variants = []
        if header:
            _, header_values = header
            variants = variant_columns(header_values)
            variant_count += len(variants)
        for row_index, values in rows:
            if classification["sheet_role"] == "price_source" and not is_blank(values):
                price_row_count += 1
            for value in values:
                parsed = parse_status(value, status_map)
                if parsed["canonical_status"]:
                    status_counter[(parsed["status_symbol"], parsed["canonical_status"])] += 1
                rule_candidate_count += len(
                    rule_phrase_candidates(
                        source_sheet=sheet_name,
                        source_row=row_index,
                        model_key=classification["model_key"],
                        source_field="row",
                        raw_text=value,
                        patterns=patterns,
                    )
                )
        sheets.append(
            {
                **classification,
                "max_row": ws.max_row,
                "max_column": ws.max_column,
                "likely_variant_headers": [variant["variant_label"] for variant in variants],
                "likely_rpo_columns": ["Orderable RPO Code", "Ref. Only RPO Code"] if header else [],
            }
        )

    return {
        "source_path": str(source),
        "sheet_count": len(wb.sheetnames),
        "sheets": sheets,
        "detected": {
            "model_keys": sorted({sheet["model_key"] for sheet in sheets if sheet["model_key"]}),
            "section_families": sorted({sheet["section_family"] for sheet in sheets if sheet["section_family"] != "unknown"}),
            "variant_header_count": variant_count,
            "status_symbols": [
                {"status_symbol": symbol, "canonical_status": canonical, "count": count}
                for (symbol, canonical), count in sorted(status_counter.items())
            ],
            "price_schedule_rows": price_row_count,
            "rule_phrase_candidate_count": rule_candidate_count,
        },
    }


def extract_staging(source: Path) -> dict[str, list[dict[str, Any]] | dict[str, Any]]:
    wb = load_workbook_readonly(source)
    role_rows = load_sheet_role_rows()
    status_map = load_status_map()
    patterns = load_phrase_patterns()
    rows_by_name: dict[str, list[dict[str, Any]]] = {name: [] for name in STAGING_OUTPUTS}
    status_examples: dict[tuple[str, str, str], Counter[str]] = {}
    primary_keys: set[str] = set()

    for sheet_name in wb.sheetnames:
        ws = wb[sheet_name]
        classification = classify_sheet(sheet_name, role_rows)
        rows = worksheet_rows(ws)
        rows_by_name["sheets"].append(classification)
        header = find_matrix_header(rows)
        header_row_index = header[0] if header else 0
        headers = header[1] if header else []
        variants = variant_columns(headers) if header else []
        for variant in variants:
            rows_by_name["variants"].append(
                {
                    "source_sheet": sheet_name,
                    "model_key": classification["model_key"],
                    **{key: variant[key] for key in ["variant_label", "body_code", "body_style", "trim_level", "inferred_variant_id", "source_cell_range", "confidence"]},
                    "notes": "Detected from variant header.",
                }
            )

        for row_index, values in rows:
            if is_blank(values):
                rows_by_name["ignored_rows"].append(
                    {
                        "source_sheet": sheet_name,
                        "source_row": row_index,
                        "raw_values": raw_row_values(values),
                        "reason": "blank_row",
                    }
                )
                continue
            candidate_source_field = "row"
            candidate_text = " ".join(value for value in values if value)
            if header and row_index > header_row_index and classification["sheet_role"] in PRIMARY_MATRIX_ROLES | {"derived_equipment_summary"}:
                candidate_source_field = "description"
                candidate_text = value_at(values, 2)
            rows_by_name["rule_phrase_candidates"].extend(
                rule_phrase_candidates(
                    source_sheet=sheet_name,
                    source_row=row_index,
                    model_key=classification["model_key"],
                    source_field=candidate_source_field,
                    raw_text=candidate_text,
                    patterns=patterns,
                )
            )

            if row_index <= header_row_index and header:
                rows_by_name["ignored_rows"].append(
                    {
                        "source_sheet": sheet_name,
                        "source_row": row_index,
                        "raw_values": raw_row_values(values),
                        "reason": "header_or_legend_row",
                    }
                )
                continue

            role = classification["sheet_role"]
            if role in PRIMARY_MATRIX_ROLES and header:
                extract_matrix_row(rows_by_name, status_examples, primary_keys, classification, sheet_name, row_index, values, variants, status_map)
            elif role == "derived_equipment_summary" and header:
                extract_equipment_group_row(rows_by_name, primary_keys, classification, sheet_name, row_index, values)
            elif role == "model_global_matrix":
                extract_color_trim_row(rows_by_name, classification, sheet_name, row_index, values, status_map)
            elif role == "price_source":
                rows_by_name["price_rows"].append(
                    {
                        "source_sheet": sheet_name,
                        "source_row": row_index,
                        "model_key": classification["model_key"],
                        "price_block_label": infer_price_block(values),
                        "raw_values": raw_row_values(values),
                        "notes": "Price Schedule extraction in this pass is staging evidence only. Do not classify final canonical price rules, price books, package pricing, or included-zero pricing yet.",
                    }
                )
            elif role == "ignored_or_unknown":
                rows_by_name["unresolved_rows"].append(
                    {
                        "source_sheet": sheet_name,
                        "source_row": row_index,
                        "raw_values": raw_row_values(values),
                        "reason": "ignored_or_unknown_sheet_with_content",
                        "review_status": "needs_review",
                    }
                )

    for (sheet_name, symbol, canonical_status), examples in sorted(status_examples.items()):
        rows_by_name["status_symbols"].append(
            {
                "source_sheet": sheet_name,
                "status_symbol": symbol,
                "raw_status_examples": "|".join(sorted(examples)),
                "count": sum(examples.values()),
                "canonical_status": canonical_status,
            }
        )

    report = {
        "source_path": str(source),
        "row_counts": {name: len(rows) for name, rows in rows_by_name.items()},
        "notes": [
            "Staging output is structured raw evidence, not canonical truth.",
            "No canonical proposal rows are generated by this scaffold.",
        ],
    }
    return {**rows_by_name, "report": report}


def extract_matrix_row(
    rows_by_name: dict[str, list[dict[str, Any]]],
    status_examples: dict[tuple[str, str, str], Counter[str]],
    primary_keys: set[str],
    classification: dict[str, str],
    sheet_name: str,
    row_index: int,
    values: list[str],
    variants: list[dict[str, str]],
    status_map: dict[str, dict[str, str]],
) -> None:
    orderable_rpo = value_at(values, 0)
    ref_rpo = value_at(values, 1)
    description = value_at(values, 2)
    if not (orderable_rpo or ref_rpo or description):
        rows_by_name["ignored_rows"].append(
            {"source_sheet": sheet_name, "source_row": row_index, "raw_values": raw_row_values(values), "reason": "matrix_row_without_rpo_or_description"}
        )
        return
    row_key = f"{classification['model_key']}|{classification['section_family']}|{orderable_rpo}|{ref_rpo}|{description}"
    primary_keys.add(row_key)
    for variant in variants:
        column_index = int(variant["column_index"])
        raw_status = value_at(values, column_index - 1)
        parsed = parse_status(raw_status, status_map)
        if parsed["canonical_status"]:
            key = (sheet_name, parsed["status_symbol"], parsed["canonical_status"])
            status_examples.setdefault(key, Counter())[parsed["raw_status"]] += 1
        rows_by_name["variant_matrix_rows"].append(
            {
                "source_sheet": sheet_name,
                "source_row": row_index,
                "model_key": classification["model_key"],
                "section_family": classification["section_family"],
                "orderable_rpo": orderable_rpo,
                "ref_rpo": ref_rpo,
                "description": description,
                "variant_id": variant["inferred_variant_id"],
                "body_code": variant["body_code"],
                "body_style": variant["body_style"],
                "trim_level": variant["trim_level"],
                **parsed,
                "source_detail_raw": description,
            }
        )


def extract_equipment_group_row(
    rows_by_name: dict[str, list[dict[str, Any]]],
    primary_keys: set[str],
    classification: dict[str, str],
    sheet_name: str,
    row_index: int,
    values: list[str],
) -> None:
    orderable_rpo = value_at(values, 0)
    ref_rpo = value_at(values, 1)
    description = value_at(values, 2)
    if not (orderable_rpo or ref_rpo or description):
        rows_by_name["ignored_rows"].append(
            {"source_sheet": sheet_name, "source_row": row_index, "raw_values": raw_row_values(values), "reason": "equipment_group_row_without_rpo_or_description"}
        )
        return
    row_key = f"{classification['model_key']}|{classification['section_family']}|{orderable_rpo}|{ref_rpo}|{description}"
    matched = row_key in primary_keys
    rows_by_name["equipment_group_rows"].append(
        {
            "source_sheet": sheet_name,
            "source_row": row_index,
            "model_key": classification["model_key"],
            "equipment_group_rpo": orderable_rpo if orderable_rpo and orderable_rpo != "Equipment Groups" else "",
            "orderable_rpo": orderable_rpo if orderable_rpo != "Equipment Groups" else "",
            "ref_rpo": ref_rpo,
            "description": description,
            "row_kind": "derived_cross_check",
            "matched_primary_row_key": row_key if matched else "",
            "match_status": "matched_primary" if matched else "unmatched_primary_review",
            "source_detail_raw": description,
        }
    )


def extract_color_trim_row(
    rows_by_name: dict[str, list[dict[str, Any]]],
    classification: dict[str, str],
    sheet_name: str,
    row_index: int,
    values: list[str],
    status_map: dict[str, dict[str, str]],
) -> None:
    lowered_values = {value.lower() for value in values if value}
    if (
        len(values) < 5
        or value_at(values, 0).lower() in {"recommended", "decor level"}
        or "interior colors" in lowered_values
    ):
        rows_by_name["ignored_rows"].append(
            {"source_sheet": sheet_name, "source_row": row_index, "raw_values": raw_row_values(values), "reason": "color_trim_header_or_legend_row"}
        )
        return
    trim_level = value_at(values, 0)
    seat_code = value_at(values, 2)
    interior_label = value_at(values, 3)
    for value in values[4:]:
        if not value:
            continue
        parsed = parse_status(value, status_map)
        rows_by_name["color_trim_rows"].append(
            {
                "source_sheet": sheet_name,
                "source_row": row_index,
                "model_key": classification["model_key"],
                "scope_type": "model_global",
                "exterior_color_rpo": "",
                "exterior_color_name": "",
                "interior_code": value if parsed["canonical_status"] != "not_available" else "",
                "interior_label": interior_label,
                "seat_code": seat_code,
                "trim_level": trim_level,
                **parsed,
                "source_detail_raw": raw_row_values(values),
            }
        )


def infer_price_block(values: list[str]) -> str:
    joined = " ".join(value for value in values if value).lower()
    if "base model prices" in joined:
        return "base_model_prices"
    if "model" in joined and "price" in joined:
        return "price_header"
    return "raw_price_schedule_row"


def value_at(values: list[str], index: int) -> str:
    if index >= len(values):
        return ""
    return clean(values[index])


def write_staging_outputs(out_dir: Path, staging: dict[str, list[dict[str, Any]] | dict[str, Any]]) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    for name, headers in STAGING_OUTPUTS.items():
        rows = staging[name]
        assert isinstance(rows, list)
        write_csv(out_dir / f"staging_{name}.csv", headers, rows)
    report = staging["report"]
    assert isinstance(report, dict)
    write_json(out_dir / "import_report.json", report)
