# Interactive Ingest Wizard Pass A Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Browser-first ingest wizard: choose/upload a raw GM order-guide xlsx, profile sheets into friendly cards, confirm sheet roles, run a deterministic option/price parse with exact 1-to-1 price joins, and land on a read-only reviewable candidate table.

**Architecture:** New `scripts/corvette_form_generator/ingest/wizard/` package (profiler → parser → joiner → session store) reusing `source_profiler` primitives; new stdlib HTTP server `scripts/ingest_wizard_server.py` serving `visualizer/ingest-wizard/` static UI plus a JSON API; all run state persisted as versioned JSON under `form-output/ingest-wizard/<run-id>/`.

**Tech Stack:** Python 3 stdlib + existing `openpyxl`; vanilla JS/CSS/HTML (no frameworks, no new dependencies).

**Spec:** `docs/ingest/pass-a/interactive-ingest-wizard-pass-a-spec.md` (read it first — it defines scope, the core principle, and non-goals).

## Global Constraints

- No new dependencies; stdlib `http.server` + existing `openpyxl` only.
- Read-only toward `stingray_master.xlsx`, `form-app/`, generated `form-output/` artifacts; the wizard writes only under `form-output/ingest-wizard/`.
- Never modify the raw export file.
- Preserve raw values verbatim in evidence; normalized fields sit alongside raw fields, never replacing them.
- No fuzzy matching, no price selection heuristics, no product guessing — deterministic structure only (core principle).
- Artifact payloads carry `"schemaVersion": "pass-a-1"`.
- Server binds `127.0.0.1` by default, port `8040`.
- JSON payload keys served to the browser are camelCase.
- Tests are unittest-style, run with `.venv/bin/python -m pytest`.
- Python style: match `source_profiler.py` (module docstring, `from __future__ import annotations`, typed signatures, dict payload builders).

---

### Task 1: Test fixture builder + sheet profiler (`profiler.py`)

**Files:**
- Create: `scripts/corvette_form_generator/ingest/wizard/__init__.py`
- Create: `scripts/corvette_form_generator/ingest/wizard/profiler.py`
- Create: `tests/ingest_wizard_fixtures.py`
- Test: `tests/test_ingest_wizard_profiler.py`

**Interfaces:**
- Consumes: `corvette_form_generator.ingest.source_profiler` constants `ORDER_GUIDE_BASE_HEADERS`, `RPO_RE`, `STATUS_RE`; `corvette_form_generator.workbook.clean`.
- Produces (used by Tasks 2–6):
  - `profile_workbook(path: Path) -> dict` → `{"schemaVersion", "sourceFile", "sheets": [card]}`
  - `profile_sheet(sheet_name: str, values: list[list]) -> dict` (a "card")
  - `sheet_values(ws) -> list[list]`
  - `find_price_sections(values) -> dict[str, int]` (label → 1-based row)
  - Constants: `SCHEMA_VERSION = "pass-a-1"`, `SHEET_TYPE_OPTIONS = "options_matrix"`, `SHEET_TYPE_PRICE = "price_sheet"`, `SHEET_TYPE_UNSUPPORTED = "unsupported"`, `SUBTYPE_ORDERABLE = "orderable_options"`, `SUBTYPE_STANDARD = "standard_equipment"`, `ROLE_OPTIONS = "options"`, `ROLE_PRICE = "price"`, `ROLE_EXCLUDE = "exclude"`, `PRICE_SECTION_BASE = "Base Model Prices"`, `PRICE_SECTION_OPTIONS = "Additional Options"`
  - Card keys: `sheetName, sheetType, contentSubtype, modelFamily, modelFamilies, headerRow (1-based | None), variantColumns ([{columnIndex, columnLetter, rawHeader, label, modelCode, trim, bodyStyle}]), rowStats, statusVocabulary, confidence ("high"|"medium"|"low"), confidenceReasons, recommendedRole, recommendedReason`
  - `rowStats` for matrices: `{orderableRpoRows, refOnlyRpoRows, sectionRows, dataRows, statusCells, standardShare}`; for price sheets: `{optionPriceRows, baseModelRows, dataRows}`.
- Fixture builder produces `build_raw_export(path: Path) -> Path` writing a compact raw-export-shaped workbook.

- [ ] **Step 1: Write the fixture builder**

`tests/ingest_wizard_fixtures.py`:

```python
#!/usr/bin/env python3
"""Compact raw GM order-guide fixture workbook for wizard Pass A tests."""

from __future__ import annotations

from pathlib import Path

from openpyxl import Workbook

STINGRAY_VARIANTS = ["Coupe\n1YC07\n1LT", "Coupe\n1YC07\n2LT", "Convertible\n1YC67\n1LT"]
ZR1_VARIANTS = ["ZR1 Coupe\n1YR07\n1LZ", "ZR1X Coupe\n1YS07\n1LZ"]
BASE_HEADERS = ["Orderable RPO Code", "Ref. Only RPO Code", "Description"]


def matrix_sheet(wb: Workbook, name: str, family_title: str, variants: list[str], rows: list[list[object]]) -> None:
    ws = wb.create_sheet(name)
    ws.append([family_title])
    ws.append(["", "", "S = Standard Equipment  A = Available"])
    ws.append(BASE_HEADERS + variants)
    for row in rows:
        ws.append(row)


def build_raw_export(path: Path) -> Path:
    wb = Workbook()
    wb.remove(wb.active)

    ws = wb.create_sheet("Price Schedule")
    ws.append(["2027 CHEVROLET CORVETTE"])
    ws.append([])
    ws.append(["Base Model Prices"])
    ws.append(["", "Model", "Model Description", "List", "Factory", "MSRP(c)"])
    ws.append(["", "1YC07", "Corvette Stingray Coupe 1LT", 71000, 0, 71000])
    ws.append(["", "1YR07", "Corvette ZR1 Coupe 1LZ", 194700, 0, 194700])
    ws.append([])
    ws.append(["Additional Options"])
    ws.append(["", "Option Code", "Description", "List", "Factory", "MSRP(c)"])
    ws.append(["", "Additional Options:"])
    ws.append(["", "BV4", "Personalized Plaque", "", 395, 0, 395])
    ws.append(["", "PDB", "Carbon Wheel Package", "with ROY wheels", 16000, 0, 16000])
    ws.append(["", "PDB", "Carbon Wheel Package", "with ROZ wheels", 17000, 0, 17000])
    ws.append(["", "YYY", "Orphan priced option", "", 500, 0, 500])

    matrix_sheet(
        wb,
        "Equipment Groups 1",
        "Stingray",
        STINGRAY_VARIANTS,
        [
            ["Equipment Groups"],
            ["", "UQH", "Audio system feature, Bose premium", "--", "■", "--"],
            ["BV4", "", "Personalized Plaque. Not available with (PDB).", "A1", "A", "A"],
            ["E60", "", "Front Lift", "A/D1", "A", "--"],
            ["ZZZ", "", "Mystery option with odd status", "?", "A", "A"],
            ["", "", "Narrative-only detail row without any RPO", "", "", ""],
        ],
    )
    matrix_sheet(
        wb,
        "Equipment Groups 4",
        "ZR1 and ZR1X",
        ZR1_VARIANTS,
        [
            ["Equipment Groups"],
            ["PDB", "", "Carbon Wheel Package", "A", "A"],
            ["C2Z", "", "ZR1 only cosmetic pack", "A", "--"],
        ],
    )
    matrix_sheet(
        wb,
        "Standard Equipment 1",
        "Stingray",
        STINGRAY_VARIANTS,
        [
            ["", "AJ7", "Airbags, frontal and side-impact", "S1", "S1", "S1"],
            ["", "CJ2", "Air conditioning, dual-zone", "S", "S", "S"],
            ["", "UQH", "Audio, standard", "S", "S", "S"],
            ["EYT", "", "Rare orderable row on SE sheet", "A", "S", "S"],
        ],
    )

    ws = wb.create_sheet("Color and Trim 1")
    ws.append(["Recommended"])
    ws.append(["Some", "unrelated", "layout"])

    wb.save(path)
    return path
```

- [ ] **Step 2: Write the failing profiler tests**

`tests/test_ingest_wizard_profiler.py`:

```python
#!/usr/bin/env python3
"""Tests for the wizard Pass A sheet profiler."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for entry in (ROOT / "scripts", ROOT / "tests"):
    if str(entry) not in sys.path:
        sys.path.insert(0, str(entry))

from corvette_form_generator.ingest.wizard import profiler  # noqa: E402
from ingest_wizard_fixtures import build_raw_export  # noqa: E402


class WizardProfilerTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._tmp = tempfile.TemporaryDirectory()
        cls.raw = build_raw_export(Path(cls._tmp.name) / "raw.xlsx")
        cls.profile = profiler.profile_workbook(cls.raw)
        cls.cards = {card["sheetName"]: card for card in cls.profile["sheets"]}

    @classmethod
    def tearDownClass(cls) -> None:
        cls._tmp.cleanup()

    def test_profile_envelope(self) -> None:
        self.assertEqual(self.profile["schemaVersion"], "pass-a-1")
        self.assertEqual(self.profile["sourceFile"], "raw.xlsx")
        self.assertEqual(len(self.profile["sheets"]), 5)

    def test_options_matrix_card(self) -> None:
        card = self.cards["Equipment Groups 1"]
        self.assertEqual(card["sheetType"], "options_matrix")
        self.assertEqual(card["contentSubtype"], "orderable_options")
        self.assertEqual(card["modelFamily"], "Stingray")
        self.assertEqual(card["modelFamilies"], ["Stingray"])
        self.assertEqual(card["headerRow"], 3)
        self.assertEqual(card["recommendedRole"], "options")
        self.assertEqual(len(card["variantColumns"]), 3)
        first = card["variantColumns"][0]
        self.assertEqual(first["columnLetter"], "D")
        self.assertEqual(first["modelCode"], "1YC07")
        self.assertEqual(first["trim"], "1LT")
        self.assertEqual(first["bodyStyle"], "coupe")
        stats = card["rowStats"]
        self.assertEqual(stats["orderableRpoRows"], 3)
        self.assertEqual(stats["refOnlyRpoRows"], 1)
        self.assertEqual(stats["sectionRows"], 1)

    def test_unknown_status_symbol_downgrades_confidence(self) -> None:
        card = self.cards["Equipment Groups 1"]
        self.assertEqual(card["confidence"], "medium")
        self.assertTrue(any("?" in reason for reason in card["confidenceReasons"]))
        clean_card = self.cards["Equipment Groups 4"]
        self.assertEqual(clean_card["confidence"], "high")
        self.assertEqual(clean_card["confidenceReasons"], [])

    def test_combined_model_family_is_mixed(self) -> None:
        card = self.cards["Equipment Groups 4"]
        self.assertEqual(card["modelFamily"], "mixed")
        self.assertEqual(card["modelFamilies"], ["ZR1", "ZR1X"])

    def test_standard_equipment_subtype_recommends_exclude(self) -> None:
        card = self.cards["Standard Equipment 1"]
        self.assertEqual(card["sheetType"], "options_matrix")
        self.assertEqual(card["contentSubtype"], "standard_equipment")
        self.assertEqual(card["recommendedRole"], "exclude")
        self.assertGreaterEqual(card["rowStats"]["standardShare"], 0.6)

    def test_price_sheet_card(self) -> None:
        card = self.cards["Price Schedule"]
        self.assertEqual(card["sheetType"], "price_sheet")
        self.assertEqual(card["recommendedRole"], "price")
        self.assertEqual(card["confidence"], "high")
        self.assertEqual(card["rowStats"]["optionPriceRows"], 4)
        self.assertEqual(card["rowStats"]["baseModelRows"], 2)

    def test_unsupported_card(self) -> None:
        card = self.cards["Color and Trim 1"]
        self.assertEqual(card["sheetType"], "unsupported")
        self.assertEqual(card["recommendedRole"], "exclude")
        self.assertEqual(card["confidence"], "low")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_ingest_wizard_profiler.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'corvette_form_generator.ingest.wizard'`

- [ ] **Step 4: Implement the profiler**

`scripts/corvette_form_generator/ingest/wizard/__init__.py`:

```python
"""Interactive ingest wizard (Pass A): profiler, parser, joiner, session store."""
```

`scripts/corvette_form_generator/ingest/wizard/profiler.py`:

```python
#!/usr/bin/env python3
"""Sheet profiling for the interactive ingest wizard (Pass A, step 2).

Turns a raw GM order-guide export into friendly "sheet cards": detected sheet
type, model family, variant columns, row/header stats, confidence, and a
recommended role. Detection is structure-derived only — no product guessing
(core principle in docs/ingest/pass-a/interactive-ingest-wizard-pass-a-spec.md).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from openpyxl import load_workbook
from openpyxl.utils import get_column_letter

from corvette_form_generator.ingest.source_profiler import (
    ORDER_GUIDE_BASE_HEADERS,
    RPO_RE,
    STATUS_RE,
)
from corvette_form_generator.workbook import clean

SCHEMA_VERSION = "pass-a-1"
SHEET_TYPE_OPTIONS = "options_matrix"
SHEET_TYPE_PRICE = "price_sheet"
SHEET_TYPE_UNSUPPORTED = "unsupported"
SUBTYPE_ORDERABLE = "orderable_options"
SUBTYPE_STANDARD = "standard_equipment"
ROLE_OPTIONS = "options"
ROLE_PRICE = "price"
ROLE_EXCLUDE = "exclude"
PRICE_SECTION_BASE = "Base Model Prices"
PRICE_SECTION_OPTIONS = "Additional Options"
# Observed 2027 export: Standard Equipment sheets have S-share >= 0.80, every
# other options matrix <= 0.47 (spec "Diagnosis"). 0.60 splits with margin.
STANDARD_EQUIPMENT_S_SHARE = 0.60


def profile_workbook(path: Path) -> dict[str, Any]:
    wb = load_workbook(path, data_only=True)
    try:
        sheets = [profile_sheet(ws.title, sheet_values(ws)) for ws in wb.worksheets]
    finally:
        wb.close()
    return {"schemaVersion": SCHEMA_VERSION, "sourceFile": Path(path).name, "sheets": sheets}


def sheet_values(ws) -> list[list[Any]]:
    return [list(row) for row in ws.iter_rows(values_only=True)]


def profile_sheet(sheet_name: str, values: list[list[Any]]) -> dict[str, Any]:
    header_row = find_matrix_header_row(values)
    if header_row is not None:
        return matrix_card(sheet_name, values, header_row)
    if find_price_sections(values):
        return price_card(sheet_name, values)
    return unsupported_card(sheet_name)


def find_matrix_header_row(values: list[list[Any]]) -> int | None:
    """Return the 1-based header row carrying the order-guide base headers."""
    for index, row in enumerate(values[:10], start=1):
        cleaned = {clean(value) for value in row}
        if set(ORDER_GUIDE_BASE_HEADERS).issubset(cleaned):
            return index
    return None


def find_price_sections(values: list[list[Any]]) -> dict[str, int]:
    """Map price-schedule section labels to their 1-based row indexes."""
    sections: dict[str, int] = {}
    for index, row in enumerate(values, start=1):
        first = clean(row[0]) if row else ""
        if first in (PRICE_SECTION_BASE, PRICE_SECTION_OPTIONS) and first not in sections:
            sections[first] = index
    return sections if PRICE_SECTION_OPTIONS in sections else {}


def cell_text(row: list[Any], index: int) -> str:
    return clean(row[index]) if index < len(row) else ""


def matrix_card(sheet_name: str, values: list[list[Any]], header_row: int) -> dict[str, Any]:
    headers = values[header_row - 1]
    description_index = next(
        index for index, value in enumerate(headers) if clean(value) == "Description"
    )
    variant_columns = [
        parse_variant_header(index, clean(value))
        for index, value in enumerate(headers)
        if index > description_index and clean(value)
    ]
    stats, vocabulary = matrix_row_stats(values, header_row, variant_columns)
    family = detect_model_family(values[0][0] if values and values[0] else "")
    subtype = (
        SUBTYPE_STANDARD
        if stats["statusCells"] and stats["standardShare"] >= STANDARD_EQUIPMENT_S_SHARE
        else SUBTYPE_ORDERABLE
    )
    confidence, reasons = matrix_confidence(variant_columns, vocabulary)
    if subtype == SUBTYPE_STANDARD:
        role = ROLE_EXCLUDE
        reason = "Mostly standard-equipment rows (S statuses); include manually if needed."
    elif not stats["orderableRpoRows"]:
        role = ROLE_EXCLUDE
        reason = "No orderable RPO rows detected."
    else:
        role = ROLE_OPTIONS
        reason = f"{stats['orderableRpoRows']} orderable option rows detected."
    return {
        "sheetName": sheet_name,
        "sheetType": SHEET_TYPE_OPTIONS,
        "contentSubtype": subtype,
        "modelFamily": family["modelFamily"],
        "modelFamilies": family["modelFamilies"],
        "headerRow": header_row,
        "variantColumns": variant_columns,
        "rowStats": stats,
        "statusVocabulary": vocabulary,
        "confidence": confidence,
        "confidenceReasons": reasons,
        "recommendedRole": role,
        "recommendedReason": reason,
    }


def parse_variant_header(column_index0: int, raw_header: str) -> dict[str, Any]:
    parts = [part.strip() for part in str(raw_header).split("\n") if part.strip()]
    label = parts[0] if parts else str(raw_header)
    model_code = parts[1] if len(parts) > 1 else ""
    trim = parts[2] if len(parts) > 2 else ""
    lowered = label.lower()
    body_style = "convertible" if "convertible" in lowered else "coupe" if "coupe" in lowered else ""
    return {
        "columnIndex": column_index0 + 1,
        "columnLetter": get_column_letter(column_index0 + 1),
        "rawHeader": str(raw_header),
        "label": label,
        "modelCode": clean(model_code),
        "trim": clean(trim),
        "bodyStyle": body_style,
    }


def matrix_row_stats(
    values: list[list[Any]],
    header_row: int,
    variant_columns: list[dict[str, Any]],
) -> tuple[dict[str, Any], dict[str, int]]:
    orderable = ref_only = section = data_rows = status_cells = standard_cells = 0
    vocabulary: dict[str, int] = {}
    for row in values[header_row:]:
        first = cell_text(row, 0)
        second = cell_text(row, 1)
        third = cell_text(row, 2)
        row_statuses = [
            cell_text(row, column["columnIndex"] - 1)
            for column in variant_columns
            if cell_text(row, column["columnIndex"] - 1)
        ]
        if not first and not second and not third and not row_statuses:
            continue
        data_rows += 1
        if RPO_RE.fullmatch(first.upper()):
            orderable += 1
        elif not first and RPO_RE.fullmatch(second.upper()):
            ref_only += 1
        elif first and not second and not third:
            section += 1
        for raw in row_statuses:
            status_cells += 1
            vocabulary[raw] = vocabulary.get(raw, 0) + 1
            match = STATUS_RE.fullmatch(raw)
            if match and match.group(1) == "S":
                standard_cells += 1
    stats = {
        "orderableRpoRows": orderable,
        "refOnlyRpoRows": ref_only,
        "sectionRows": section,
        "dataRows": data_rows,
        "statusCells": status_cells,
        "standardShare": round(standard_cells / status_cells, 4) if status_cells else 0.0,
    }
    return stats, dict(sorted(vocabulary.items()))


def matrix_confidence(
    variant_columns: list[dict[str, Any]],
    vocabulary: dict[str, int],
) -> tuple[str, list[str]]:
    reasons: list[str] = []
    if not variant_columns:
        reasons.append("No variant columns detected after the Description column.")
    incomplete = [
        column["columnLetter"]
        for column in variant_columns
        if not column["modelCode"] or not column["trim"]
    ]
    if incomplete:
        reasons.append(
            "Variant headers missing model code or trim in columns: " + ", ".join(incomplete) + "."
        )
    unknown = sorted(symbol for symbol in vocabulary if not STATUS_RE.fullmatch(symbol))
    if unknown:
        reasons.append("Unrecognized status symbols: " + ", ".join(unknown[:8]) + ".")
    if not reasons:
        return "high", []
    return ("medium" if variant_columns else "low"), reasons


def detect_model_family(title_cell: Any) -> dict[str, Any]:
    title = clean(title_cell)
    if not title:
        return {"modelFamily": "unknown", "modelFamilies": []}
    parts = [part.strip() for part in title.split(" and ") if part.strip()]
    if len(parts) > 1:
        return {"modelFamily": "mixed", "modelFamilies": parts}
    return {"modelFamily": title, "modelFamilies": [title]}


def price_card(sheet_name: str, values: list[list[Any]]) -> dict[str, Any]:
    sections = find_price_sections(values)
    reasons: list[str] = []
    confidence = "high"
    if PRICE_SECTION_BASE not in sections:
        confidence = "medium"
        reasons.append("Base Model Prices section not found.")
    return {
        "sheetName": sheet_name,
        "sheetType": SHEET_TYPE_PRICE,
        "contentSubtype": "",
        "modelFamily": "all",
        "modelFamilies": [],
        "headerRow": None,
        "variantColumns": [],
        "rowStats": price_row_stats(values, sections),
        "statusVocabulary": {},
        "confidence": confidence,
        "confidenceReasons": reasons,
        "recommendedRole": ROLE_PRICE,
        "recommendedReason": "Detected price-schedule sections.",
    }


def price_row_stats(values: list[list[Any]], sections: dict[str, int]) -> dict[str, Any]:
    option_rows = base_rows = data_rows = 0
    options_start = sections.get(PRICE_SECTION_OPTIONS, 0)
    base_start = sections.get(PRICE_SECTION_BASE, 0)
    for index, row in enumerate(values, start=1):
        code = cell_text(row, 1)
        if not any(clean(value) for value in row):
            continue
        data_rows += 1
        if options_start and index > options_start and RPO_RE.fullmatch(code.upper()):
            option_rows += 1
        elif base_start and index > base_start and (not options_start or index < options_start):
            if MODEL_CODE_RE.fullmatch(code.upper()):
                base_rows += 1
    return {"optionPriceRows": option_rows, "baseModelRows": base_rows, "dataRows": data_rows}


def unsupported_card(sheet_name: str) -> dict[str, Any]:
    return {
        "sheetName": sheet_name,
        "sheetType": SHEET_TYPE_UNSUPPORTED,
        "contentSubtype": "",
        "modelFamily": "unknown",
        "modelFamilies": [],
        "headerRow": None,
        "variantColumns": [],
        "rowStats": {},
        "statusVocabulary": {},
        "confidence": "low",
        "confidenceReasons": ["No recognized options-matrix headers or price-schedule sections."],
        "recommendedRole": ROLE_EXCLUDE,
        "recommendedReason": "Unsupported layout in Pass A; handle manually.",
    }


import re  # noqa: E402  (kept near its single use for clarity)

MODEL_CODE_RE = re.compile(r"^1Y[A-Z]\d{2}$")
```

Move the `import re` + `MODEL_CODE_RE` lines up with the other imports/constants when writing the real file (the snippet shows them last only to highlight the addition; final file has `import re` in the import block and `MODEL_CODE_RE` beside the other constants).

- [ ] **Step 5: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_ingest_wizard_profiler.py -v`
Expected: all tests PASS. If `test_price_sheet_card` disagrees on counts, check `price_row_stats` boundaries against the fixture (option rows: BV4, PDB, PDB, YYY = 4; base rows: 1YC07, 1YR07 = 2).

- [ ] **Step 6: Commit**

```bash
git add scripts/corvette_form_generator/ingest/wizard/ tests/ingest_wizard_fixtures.py tests/test_ingest_wizard_profiler.py
git commit -m "feat: Add wizard Pass A sheet profiler with friendly sheet cards"
```

---

### Task 2: Deterministic option/price parser (`parser.py`)

**Files:**
- Create: `scripts/corvette_form_generator/ingest/wizard/parser.py`
- Test: `tests/test_ingest_wizard_parser.py`

**Interfaces:**
- Consumes: Task 1 profiler (`profile_sheet`, `sheet_values`, constants), `source_profiler.parse_status`, `source_profiler.RPO_RE`.
- Produces (used by Tasks 3–5):
  - `parse_confirmed_sheets(path: Path, roles: dict[str, str]) -> dict` → `{"schemaVersion", "candidates", "priceRows", "baseModelPriceRows", "skippedRows", "skippedPriceRows"}`
  - Candidate keys: `candidateId ("<sheet>:<row>"), sheetName, rowIndex, modelFamily, modelFamilies, sectionLabel, rowKind ("orderable"|"ref_only"), rpo, refOnlyRpo, description, statuses ([{columnLetter, variantLabel, modelCode, trim, bodyStyle, raw, status, disclosureMarker, flags}]), sourceEvidence ({sheetName, rowIndex, cells: {"A5": "raw"}})`
  - Price row keys: `rpo, description, qualifier, listPrice (float), priceColumns ({"E11": 395.0}), sourceEvidence`
  - Base model row keys: `modelCode, description, listPrice, sourceEvidence`
  - `skippedRows`: `{sheetName: [{rowIndex, reason, description}]}`; `skippedPriceRows`: `[{sheetName, rowIndex, reason}]`

- [ ] **Step 1: Write the failing parser tests**

`tests/test_ingest_wizard_parser.py`:

```python
#!/usr/bin/env python3
"""Tests for the wizard Pass A deterministic option/price parser."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for entry in (ROOT / "scripts", ROOT / "tests"):
    if str(entry) not in sys.path:
        sys.path.insert(0, str(entry))

from corvette_form_generator.ingest.wizard.parser import parse_confirmed_sheets  # noqa: E402
from ingest_wizard_fixtures import build_raw_export  # noqa: E402

ROLES = {
    "Equipment Groups 1": "options",
    "Equipment Groups 4": "options",
    "Price Schedule": "price",
    "Standard Equipment 1": "exclude",
    "Color and Trim 1": "exclude",
}


class WizardParserTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._tmp = tempfile.TemporaryDirectory()
        cls.raw = build_raw_export(Path(cls._tmp.name) / "raw.xlsx")
        cls.parsed = parse_confirmed_sheets(cls.raw, ROLES)
        cls.by_id = {c["candidateId"]: c for c in cls.parsed["candidates"]}

    @classmethod
    def tearDownClass(cls) -> None:
        cls._tmp.cleanup()

    def test_only_confirmed_options_sheets_produce_candidates(self) -> None:
        sheets = {c["sheetName"] for c in self.parsed["candidates"]}
        self.assertEqual(sheets, {"Equipment Groups 1", "Equipment Groups 4"})

    def test_orderable_candidate_fields(self) -> None:
        candidate = self.by_id["Equipment Groups 1:6"]
        self.assertEqual(candidate["rpo"], "BV4")
        self.assertEqual(candidate["refOnlyRpo"], "")
        self.assertEqual(candidate["rowKind"], "orderable")
        self.assertEqual(candidate["sectionLabel"], "Equipment Groups")
        self.assertEqual(candidate["modelFamily"], "Stingray")
        self.assertIn("Personalized Plaque", candidate["description"])
        by_letter = {s["columnLetter"]: s for s in candidate["statuses"]}
        self.assertEqual(by_letter["D"]["raw"], "A1")
        self.assertEqual(by_letter["D"]["status"], "available")
        self.assertEqual(by_letter["D"]["disclosureMarker"], "1")
        self.assertEqual(by_letter["D"]["modelCode"], "1YC07")
        self.assertEqual(candidate["sourceEvidence"]["cells"]["A6"], "BV4")

    def test_ref_only_candidate(self) -> None:
        candidate = self.by_id["Equipment Groups 1:5"]
        self.assertEqual(candidate["rowKind"], "ref_only")
        self.assertEqual(candidate["refOnlyRpo"], "UQH")
        self.assertEqual(candidate["rpo"], "")

    def test_unknown_status_symbol_is_unresolved(self) -> None:
        candidate = self.by_id["Equipment Groups 1:8"]
        by_letter = {s["columnLetter"]: s for s in candidate["statuses"]}
        self.assertEqual(by_letter["D"]["status"], "unresolved")
        self.assertIn("unknown_status_symbol", by_letter["D"]["flags"])

    def test_no_rpo_content_row_is_skipped_with_reason(self) -> None:
        skipped = self.parsed["skippedRows"]["Equipment Groups 1"]
        self.assertEqual(len(skipped), 1)
        self.assertEqual(skipped[0]["rowIndex"], 9)
        self.assertEqual(skipped[0]["reason"], "no_rpo_on_content_row")

    def test_price_rows(self) -> None:
        rows = self.parsed["priceRows"]
        self.assertEqual([r["rpo"] for r in rows], ["BV4", "PDB", "PDB", "YYY"])
        bv4 = rows[0]
        self.assertEqual(bv4["listPrice"], 395.0)
        self.assertEqual(bv4["qualifier"], "")
        pdb = rows[1]
        self.assertEqual(pdb["qualifier"], "with ROY wheels")
        self.assertEqual(pdb["listPrice"], 16000.0)
        self.assertTrue(bv4["sourceEvidence"]["cells"])

    def test_base_model_price_rows(self) -> None:
        base = self.parsed["baseModelPriceRows"]
        self.assertEqual([r["modelCode"] for r in base], ["1YC07", "1YR07"])
        self.assertEqual(base[0]["listPrice"], 71000.0)


if __name__ == "__main__":
    unittest.main()
```

Fixture row math for the ids used above (`matrix_sheet` writes 3 header rows, data starts at row 4): row 4 = `Equipment Groups` section, row 5 = UQH ref-only, row 6 = BV4, row 7 = E60, row 8 = ZZZ, row 9 = narrative skip row. Price Schedule option rows land on rows 11–14.

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_ingest_wizard_parser.py -v`
Expected: FAIL — `ModuleNotFoundError` (no `parser` module).

- [ ] **Step 3: Implement the parser**

`scripts/corvette_form_generator/ingest/wizard/parser.py`:

```python
#!/usr/bin/env python3
"""Deterministic option/price extraction for the ingest wizard (Pass A, step 4).

Reads only user-confirmed sheets. Preserves raw cells as evidence, parses
per-variant OVS statuses, and extracts price-schedule rows. Rows that fail
deterministic parsing are reported, never silently dropped.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from openpyxl import load_workbook
from openpyxl.utils import get_column_letter

from corvette_form_generator.ingest.source_profiler import RPO_RE, parse_status
from corvette_form_generator.ingest.wizard.profiler import (
    MODEL_CODE_RE,
    PRICE_SECTION_BASE,
    PRICE_SECTION_OPTIONS,
    ROLE_OPTIONS,
    ROLE_PRICE,
    SCHEMA_VERSION,
    SHEET_TYPE_OPTIONS,
    cell_text,
    find_price_sections,
    profile_sheet,
    sheet_values,
)
from corvette_form_generator.workbook import clean


def parse_confirmed_sheets(path: Path, roles: dict[str, str]) -> dict[str, Any]:
    wb = load_workbook(path, data_only=True)
    candidates: list[dict[str, Any]] = []
    skipped_rows: dict[str, list[dict[str, Any]]] = {}
    price_rows: list[dict[str, Any]] = []
    base_rows: list[dict[str, Any]] = []
    skipped_price: list[dict[str, Any]] = []
    try:
        for ws in wb.worksheets:
            role = roles.get(ws.title, "")
            if role == ROLE_OPTIONS:
                values = sheet_values(ws)
                card = profile_sheet(ws.title, values)
                sheet_candidates, sheet_skipped = extract_option_candidates(ws.title, values, card)
                candidates.extend(sheet_candidates)
                if sheet_skipped:
                    skipped_rows[ws.title] = sheet_skipped
            elif role == ROLE_PRICE:
                values = sheet_values(ws)
                sheet_prices, sheet_base, sheet_skipped_price = extract_price_rows(ws.title, values)
                price_rows.extend(sheet_prices)
                base_rows.extend(sheet_base)
                skipped_price.extend(sheet_skipped_price)
    finally:
        wb.close()
    return {
        "schemaVersion": SCHEMA_VERSION,
        "candidates": candidates,
        "priceRows": price_rows,
        "baseModelPriceRows": base_rows,
        "skippedRows": skipped_rows,
        "skippedPriceRows": skipped_price,
    }


def extract_option_candidates(
    sheet_name: str,
    values: list[list[Any]],
    card: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    if card["sheetType"] != SHEET_TYPE_OPTIONS or not card["headerRow"]:
        return [], [{"rowIndex": None, "reason": "sheet_not_options_matrix", "description": ""}]
    variant_columns = card["variantColumns"]
    candidates: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    section_label = ""
    for row_number in range(card["headerRow"] + 1, len(values) + 1):
        row = values[row_number - 1]
        first = cell_text(row, 0)
        second = cell_text(row, 1)
        third = cell_text(row, 2)
        statuses = extract_statuses(row, variant_columns)
        if not first and not second and not third and not statuses:
            continue
        if first and not second and not third and not RPO_RE.fullmatch(first.upper()):
            section_label = first
            continue
        rpo = first.upper() if RPO_RE.fullmatch(first.upper()) else ""
        ref_only = second.upper() if RPO_RE.fullmatch(second.upper()) else ""
        if not rpo and not ref_only:
            skipped.append(
                {"rowIndex": row_number, "reason": "no_rpo_on_content_row", "description": third}
            )
            continue
        candidates.append(
            {
                "candidateId": f"{sheet_name}:{row_number}",
                "sheetName": sheet_name,
                "rowIndex": row_number,
                "modelFamily": card["modelFamily"],
                "modelFamilies": card["modelFamilies"],
                "sectionLabel": section_label,
                "rowKind": "orderable" if rpo else "ref_only",
                "rpo": rpo,
                "refOnlyRpo": ref_only,
                "description": third,
                "statuses": statuses,
                "sourceEvidence": row_evidence(sheet_name, row_number, row),
            }
        )
    return candidates, skipped


def extract_statuses(row: list[Any], variant_columns: list[dict[str, Any]]) -> list[dict[str, Any]]:
    statuses: list[dict[str, Any]] = []
    for column in variant_columns:
        raw = cell_text(row, column["columnIndex"] - 1)
        if not raw:
            continue
        parsed = parse_status(raw)
        statuses.append(
            {
                "columnLetter": column["columnLetter"],
                "variantLabel": column["label"],
                "modelCode": column["modelCode"],
                "trim": column["trim"],
                "bodyStyle": column["bodyStyle"],
                "raw": raw,
                "status": parsed["parsed_base_status"],
                "disclosureMarker": parsed["status_marker"],
                "flags": parsed["status_flags"],
            }
        )
    return statuses


def row_evidence(sheet_name: str, row_number: int, row: list[Any]) -> dict[str, Any]:
    cells = {
        f"{get_column_letter(index + 1)}{row_number}": str(value)
        for index, value in enumerate(row)
        if value is not None and clean(value) != ""
    }
    return {"sheetName": sheet_name, "rowIndex": row_number, "cells": cells}


def numeric_value(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = clean(value).replace("$", "").replace(",", "")
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def numeric_columns(row: list[Any], row_number: int, start_index: int) -> dict[str, float]:
    columns: dict[str, float] = {}
    for index in range(start_index, len(row)):
        number = numeric_value(row[index])
        if number is not None:
            columns[f"{get_column_letter(index + 1)}{row_number}"] = number
    return columns


def extract_price_rows(
    sheet_name: str,
    values: list[list[Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    sections = find_price_sections(values)
    options_start = sections.get(PRICE_SECTION_OPTIONS, 0)
    base_start = sections.get(PRICE_SECTION_BASE, 0)
    option_rows: list[dict[str, Any]] = []
    base_rows: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    if base_start:
        base_end = options_start - 1 if options_start > base_start else len(values)
        for row_number in range(base_start + 1, base_end + 1):
            row = values[row_number - 1]
            code = cell_text(row, 1).upper()
            if not MODEL_CODE_RE.fullmatch(code):
                continue
            price_columns = numeric_columns(row, row_number, 3)
            if not price_columns:
                skipped.append(
                    {"sheetName": sheet_name, "rowIndex": row_number, "reason": "no_numeric_price"}
                )
                continue
            base_rows.append(
                {
                    "modelCode": code,
                    "description": cell_text(row, 2),
                    "listPrice": next(iter(price_columns.values())),
                    "sourceEvidence": row_evidence(sheet_name, row_number, row),
                }
            )
    if options_start:
        for row_number in range(options_start + 1, len(values) + 1):
            row = values[row_number - 1]
            if cell_text(row, 0) in (PRICE_SECTION_BASE, PRICE_SECTION_OPTIONS):
                break
            code = cell_text(row, 1).upper()
            if not RPO_RE.fullmatch(code):
                continue
            qualifier_cell = row[3] if len(row) > 3 else None
            qualifier = (
                clean(qualifier_cell)
                if numeric_value(qualifier_cell) is None and clean(qualifier_cell)
                else ""
            )
            price_columns = numeric_columns(row, row_number, 3)
            if not price_columns:
                skipped.append(
                    {"sheetName": sheet_name, "rowIndex": row_number, "reason": "no_numeric_price"}
                )
                continue
            option_rows.append(
                {
                    "rpo": code,
                    "description": cell_text(row, 2),
                    "qualifier": qualifier,
                    "listPrice": next(iter(price_columns.values())),
                    "priceColumns": price_columns,
                    "sourceEvidence": row_evidence(sheet_name, row_number, row),
                }
            )
    return option_rows, base_rows, skipped
```

Note: `MODEL_CODE_RE` is imported from the profiler (Task 1 defines it beside the other constants).

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_ingest_wizard_parser.py tests/test_ingest_wizard_profiler.py -v`
Expected: all PASS (profiler suite re-run to catch import regressions).

- [ ] **Step 5: Commit**

```bash
git add scripts/corvette_form_generator/ingest/wizard/parser.py tests/test_ingest_wizard_parser.py
git commit -m "feat: Add wizard Pass A deterministic option/price parser"
```

---

### Task 3: Exact 1-to-1 price joiner (`joiner.py`)

**Files:**
- Create: `scripts/corvette_form_generator/ingest/wizard/joiner.py`
- Test: `tests/test_ingest_wizard_joiner.py`

**Interfaces:**
- Consumes: Task 2 candidate and price-row dict shapes.
- Produces (used by Tasks 4–6): `join_prices(candidates: list[dict], price_rows: list[dict]) -> dict` — mutates each candidate in place adding `priceMatch ("exact"|"ambiguous"|"none"|None)`, `listPrice (float|None)`, `priceRows (list)`; returns `{"schemaVersion", "exactMatches", "ambiguousMatches", "missingPrices", "unmatchedPriceRows"}` (counts are candidate-level, not RPO-level).

- [ ] **Step 1: Write the failing joiner tests**

`tests/test_ingest_wizard_joiner.py`:

```python
#!/usr/bin/env python3
"""Tests for the wizard Pass A exact 1-to-1 price joiner."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

from corvette_form_generator.ingest.wizard.joiner import join_prices  # noqa: E402


def candidate(candidate_id: str, rpo: str, row_kind: str = "orderable") -> dict:
    return {"candidateId": candidate_id, "rpo": rpo, "refOnlyRpo": "", "rowKind": row_kind}


def price_row(rpo: str, price: float, qualifier: str = "") -> dict:
    return {"rpo": rpo, "listPrice": price, "qualifier": qualifier, "description": ""}


class WizardJoinerTest(unittest.TestCase):
    def test_exact_ambiguous_none_and_unmatched(self) -> None:
        candidates = [
            candidate("a:1", "BV4"),
            candidate("a:2", "PDB"),
            candidate("a:3", "C2Z"),
            candidate("a:4", "", row_kind="ref_only"),
        ]
        prices = [
            price_row("BV4", 395.0),
            price_row("PDB", 16000.0, "ROY"),
            price_row("PDB", 17000.0, "ROZ"),
            price_row("YYY", 500.0),
        ]
        report = join_prices(candidates, prices)

        self.assertEqual(candidates[0]["priceMatch"], "exact")
        self.assertEqual(candidates[0]["listPrice"], 395.0)
        self.assertEqual(len(candidates[0]["priceRows"]), 1)

        self.assertEqual(candidates[1]["priceMatch"], "ambiguous")
        self.assertIsNone(candidates[1]["listPrice"])
        self.assertEqual(len(candidates[1]["priceRows"]), 2)

        self.assertEqual(candidates[2]["priceMatch"], "none")
        self.assertIsNone(candidates[2]["listPrice"])

        self.assertIsNone(candidates[3]["priceMatch"])

        self.assertEqual(report["exactMatches"], 1)
        self.assertEqual(report["ambiguousMatches"], 1)
        self.assertEqual(report["missingPrices"], 1)
        self.assertEqual([r["rpo"] for r in report["unmatchedPriceRows"]], ["YYY"])

    def test_same_rpo_on_two_sheets_joins_exactly_on_both(self) -> None:
        candidates = [candidate("a:1", "BV4"), candidate("b:1", "BV4")]
        report = join_prices(candidates, [price_row("BV4", 395.0)])
        self.assertEqual([c["priceMatch"] for c in candidates], ["exact", "exact"])
        self.assertEqual(report["exactMatches"], 2)
        self.assertEqual(report["unmatchedPriceRows"], [])


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_ingest_wizard_joiner.py -v`
Expected: FAIL — `ModuleNotFoundError` (no `joiner` module).

- [ ] **Step 3: Implement the joiner**

`scripts/corvette_form_generator/ingest/wizard/joiner.py`:

```python
#!/usr/bin/env python3
"""Exact 1-to-1 RPO price joins for the ingest wizard (Pass A, step 5).

Join keys are exact normalized RPO strings only. Ambiguous, missing, and
unmatched prices are reported for user review — never guessed (core
principle: ambiguous prices are a user decision).
"""

from __future__ import annotations

from typing import Any

from corvette_form_generator.ingest.wizard.profiler import SCHEMA_VERSION


def join_prices(candidates: list[dict[str, Any]], price_rows: list[dict[str, Any]]) -> dict[str, Any]:
    by_rpo: dict[str, list[dict[str, Any]]] = {}
    for row in price_rows:
        by_rpo.setdefault(row["rpo"], []).append(row)
    orderable_rpos: set[str] = set()
    exact = ambiguous = missing = 0
    for candidate in candidates:
        if candidate["rowKind"] != "orderable" or not candidate["rpo"]:
            candidate["priceMatch"] = None
            candidate["listPrice"] = None
            candidate["priceRows"] = []
            continue
        orderable_rpos.add(candidate["rpo"])
        matches = by_rpo.get(candidate["rpo"], [])
        candidate["priceRows"] = matches
        if len(matches) == 1:
            candidate["priceMatch"] = "exact"
            candidate["listPrice"] = matches[0]["listPrice"]
            exact += 1
        elif matches:
            candidate["priceMatch"] = "ambiguous"
            candidate["listPrice"] = None
            ambiguous += 1
        else:
            candidate["priceMatch"] = "none"
            candidate["listPrice"] = None
            missing += 1
    return {
        "schemaVersion": SCHEMA_VERSION,
        "exactMatches": exact,
        "ambiguousMatches": ambiguous,
        "missingPrices": missing,
        "unmatchedPriceRows": [row for row in price_rows if row["rpo"] not in orderable_rpos],
    }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_ingest_wizard_joiner.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add scripts/corvette_form_generator/ingest/wizard/joiner.py tests/test_ingest_wizard_joiner.py
git commit -m "feat: Add wizard Pass A exact 1-to-1 price joiner"
```

---

### Task 4: Session store (`session.py`)

**Files:**
- Create: `scripts/corvette_form_generator/ingest/wizard/session.py`
- Test: `tests/test_ingest_wizard_session.py`

**Interfaces:**
- Consumes: Tasks 1–3 (`profile_workbook`, `parse_confirmed_sheets`, `join_prices`, role/type constants).
- Produces (used by Tasks 5–6):
  - `class WizardError(ValueError)` with `.status: int` (default 400; 404 for unknown run)
  - `class WizardSessionStore(root: Path)` with methods:
    - `list_source_files() -> list[{name, origin, sizeBytes}]`
    - `save_upload(filename: str, data: bytes) -> {name, origin, sizeBytes}`
    - `create_session(file_name: str) -> {"session", "profile"}`
    - `session_detail(run_id: str) -> {"session", "profile", "roles" (dict|None), "joinReport" (dict|None)}`
    - `confirm_roles(run_id: str, roles: dict[str, str]) -> session dict`
    - `run_parse(run_id: str) -> {"session", "joinReport"}`
    - `candidates(run_id, sheet="", price_match="", family="", query="") -> {"session", "total", "matched", "candidates", "skippedRows", "unmatchedPriceRows"}`
    - `list_sessions() -> list[session dict]`
  - Session dict: `{schemaVersion, runId, state, sourceFile, sourcePath, fingerprint: {sha256, sizeBytes, mtimeNs}}`; states: `"profiled" → "roles_confirmed" → "parsed"`.
  - Artifacts under `<root>/form-output/ingest-wizard/<run-id>/`: `session.json`, `sheet-profile.json`, `sheet-roles.json`, `option-candidates.json`, `price-rows.json`, `join-report.json`; uploads under `<root>/form-output/ingest-wizard/uploads/`.

- [ ] **Step 1: Write the failing session tests**

`tests/test_ingest_wizard_session.py`:

```python
#!/usr/bin/env python3
"""Tests for the wizard Pass A session store (state machine + persistence)."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for entry in (ROOT / "scripts", ROOT / "tests"):
    if str(entry) not in sys.path:
        sys.path.insert(0, str(entry))

from corvette_form_generator.ingest.wizard.session import (  # noqa: E402
    WizardError,
    WizardSessionStore,
)
from ingest_wizard_fixtures import build_raw_export  # noqa: E402

ROLES = {"Equipment Groups 1": "options", "Price Schedule": "price"}


class WizardSessionTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        build_raw_export(self.root / "raw.xlsx")
        (self.root / "stingray_master.xlsx").write_bytes(b"not-a-source")
        self.store = WizardSessionStore(self.root)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_list_source_files_excludes_master_workbook(self) -> None:
        names = [f["name"] for f in self.store.list_source_files()]
        self.assertEqual(names, ["raw.xlsx"])

    def test_upload_rejects_traversal_and_non_xlsx(self) -> None:
        with self.assertRaises(WizardError):
            self.store.save_upload("../evil.xlsx", b"x")
        with self.assertRaises(WizardError):
            self.store.save_upload("notes.txt", b"x")
        saved = self.store.save_upload("second.xlsx", b"binary")
        self.assertEqual(saved["origin"], "upload")
        self.assertIn("second.xlsx", [f["name"] for f in self.store.list_source_files()])

    def test_create_session_profiles_and_persists(self) -> None:
        created = self.store.create_session("raw.xlsx")
        run_id = created["session"]["runId"]
        self.assertEqual(created["session"]["state"], "profiled")
        self.assertEqual(len(created["profile"]["sheets"]), 5)
        run_dir = self.root / "form-output" / "ingest-wizard" / run_id
        self.assertTrue((run_dir / "session.json").is_file())
        self.assertTrue((run_dir / "sheet-profile.json").is_file())

    def test_roles_validation_fails_closed(self) -> None:
        run_id = self.store.create_session("raw.xlsx")["session"]["runId"]
        with self.assertRaises(WizardError):  # no price sheet
            self.store.confirm_roles(run_id, {"Equipment Groups 1": "options"})
        with self.assertRaises(WizardError):  # price role on an options matrix
            self.store.confirm_roles(
                run_id, {"Equipment Groups 1": "price", "Price Schedule": "price"}
            )
        with self.assertRaises(WizardError):  # options role on unsupported sheet
            self.store.confirm_roles(
                run_id, {"Color and Trim 1": "options", "Price Schedule": "price"}
            )
        with self.assertRaises(WizardError):  # unknown sheet
            self.store.confirm_roles(run_id, {"Nope": "options", "Price Schedule": "price"})
        with self.assertRaises(WizardError):  # parse before roles
            self.store.run_parse(run_id)

    def test_standard_equipment_sheet_can_be_included_by_override(self) -> None:
        run_id = self.store.create_session("raw.xlsx")["session"]["runId"]
        session = self.store.confirm_roles(
            run_id, {"Standard Equipment 1": "options", "Price Schedule": "price"}
        )
        self.assertEqual(session["state"], "roles_confirmed")

    def test_full_run_reaches_parsed_candidates(self) -> None:
        run_id = self.store.create_session("raw.xlsx")["session"]["runId"]
        with self.assertRaises(WizardError):  # candidates before parse
            self.store.candidates(run_id)
        self.store.confirm_roles(run_id, ROLES)
        result = self.store.run_parse(run_id)
        self.assertEqual(result["session"]["state"], "parsed")
        self.assertEqual(result["joinReport"]["exactMatches"], 1)  # BV4
        payload = self.store.candidates(run_id)
        self.assertEqual(payload["total"], 4)  # UQH, BV4, E60, ZZZ
        exact_only = self.store.candidates(run_id, price_match="exact")
        self.assertEqual([c["rpo"] for c in exact_only["candidates"]], ["BV4"])
        searched = self.store.candidates(run_id, query="plaque")
        self.assertEqual(len(searched["candidates"]), 1)

    def test_reconfirming_roles_resets_parse_output(self) -> None:
        run_id = self.store.create_session("raw.xlsx")["session"]["runId"]
        self.store.confirm_roles(run_id, ROLES)
        self.store.run_parse(run_id)
        self.store.confirm_roles(run_id, ROLES)
        with self.assertRaises(WizardError):
            self.store.candidates(run_id)

    def test_source_change_fails_closed(self) -> None:
        run_id = self.store.create_session("raw.xlsx")["session"]["runId"]
        build_raw_export(self.root / "raw.xlsx")  # rewrite -> new bytes
        raw = self.root / "raw.xlsx"
        raw.write_bytes(raw.read_bytes() + b"tail")
        with self.assertRaises(WizardError):
            self.store.confirm_roles(run_id, ROLES)

    def test_unknown_run_is_404(self) -> None:
        try:
            self.store.session_detail("20990101-000000-abcdef")
            self.fail("expected WizardError")
        except WizardError as exc:
            self.assertEqual(exc.status, 404)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_ingest_wizard_session.py -v`
Expected: FAIL — `ModuleNotFoundError` (no `session` module).

- [ ] **Step 3: Implement the session store**

`scripts/corvette_form_generator/ingest/wizard/session.py`:

```python
#!/usr/bin/env python3
"""Run-state persistence and fail-closed state machine for the ingest wizard.

States: profiled -> roles_confirmed -> parsed. Every transition persists JSON
artifacts under form-output/ingest-wizard/<run-id>/ so a run can be reopened
and later passes can consume the output. The canonical workbook and the raw
source file are never written.
"""

from __future__ import annotations

import hashlib
import json
import re
import time
import uuid
from pathlib import Path
from typing import Any

from corvette_form_generator.ingest.wizard.joiner import join_prices
from corvette_form_generator.ingest.wizard.parser import parse_confirmed_sheets
from corvette_form_generator.ingest.wizard.profiler import (
    ROLE_EXCLUDE,
    ROLE_OPTIONS,
    ROLE_PRICE,
    SCHEMA_VERSION,
    SHEET_TYPE_OPTIONS,
    SHEET_TYPE_PRICE,
    profile_workbook,
)

STATE_PROFILED = "profiled"
STATE_ROLES_CONFIRMED = "roles_confirmed"
STATE_PARSED = "parsed"
VALID_ROLES = {ROLE_OPTIONS, ROLE_PRICE, ROLE_EXCLUDE}
RUN_ID_RE = re.compile(r"^[0-9]{8}-[0-9]{6}-[0-9a-f]{6}$")
PARSE_ARTIFACTS = ("option-candidates.json", "price-rows.json", "join-report.json")


class WizardError(ValueError):
    """User-visible wizard failure; maps to an HTTP 4xx response."""

    def __init__(self, message: str, status: int = 400) -> None:
        super().__init__(message)
        self.status = status


def write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def file_fingerprint(path: Path) -> dict[str, Any]:
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    stat = path.stat()
    return {"sha256": digest, "sizeBytes": stat.st_size, "mtimeNs": stat.st_mtime_ns}


class WizardSessionStore:
    def __init__(self, root: Path) -> None:
        self.root = Path(root)
        self.base = self.root / "form-output" / "ingest-wizard"
        self.uploads = self.base / "uploads"

    # ------------------------------------------------------------- files
    def list_source_files(self) -> list[dict[str, Any]]:
        files: list[dict[str, Any]] = []
        for directory, origin in ((self.root, "project"), (self.uploads, "upload")):
            if not directory.is_dir():
                continue
            for path in sorted(directory.glob("*.xlsx")):
                if path.name == "stingray_master.xlsx" or path.name.startswith("~$"):
                    continue
                files.append(
                    {"name": path.name, "origin": origin, "sizeBytes": path.stat().st_size}
                )
        return files

    def save_upload(self, filename: str, data: bytes) -> dict[str, Any]:
        name = Path(str(filename)).name
        if (
            not name
            or name != filename
            or not name.lower().endswith(".xlsx")
            or name.startswith("~$")
        ):
            raise WizardError("Upload filename must be a plain .xlsx basename.")
        self.uploads.mkdir(parents=True, exist_ok=True)
        target = self.uploads / name
        target.write_bytes(data)
        return {"name": name, "origin": "upload", "sizeBytes": target.stat().st_size}

    def resolve_source(self, name: str) -> Path:
        if Path(str(name)).name != name:
            raise WizardError("Source file must be a plain basename.")
        for directory in (self.uploads, self.root):
            path = directory / name
            if path.is_file():
                return path
        raise WizardError(f"Source file not found: {name}")

    # ---------------------------------------------------------- sessions
    def create_session(self, file_name: str) -> dict[str, Any]:
        source = self.resolve_source(file_name)
        run_id = time.strftime("%Y%m%d-%H%M%S") + "-" + uuid.uuid4().hex[:6]
        run_dir = self.base / run_id
        run_dir.mkdir(parents=True)
        profile = profile_workbook(source)
        session = {
            "schemaVersion": SCHEMA_VERSION,
            "runId": run_id,
            "state": STATE_PROFILED,
            "sourceFile": file_name,
            "sourcePath": str(source),
            "fingerprint": file_fingerprint(source),
        }
        write_json(run_dir / "session.json", session)
        write_json(run_dir / "sheet-profile.json", profile)
        return {"session": session, "profile": profile}

    def run_dir(self, run_id: str) -> Path:
        if not RUN_ID_RE.fullmatch(str(run_id)):
            raise WizardError(f"Invalid run id: {run_id}")
        run_dir = self.base / run_id
        if not (run_dir / "session.json").is_file():
            raise WizardError(f"Unknown run: {run_id}", status=404)
        return run_dir

    def load_session(self, run_id: str, *, verify_source: bool = True) -> dict[str, Any]:
        session = read_json(self.run_dir(run_id) / "session.json")
        if verify_source:
            source = Path(session["sourcePath"])
            if not source.is_file():
                raise WizardError("Source file for this run is missing; start a new run.")
            if file_fingerprint(source)["sha256"] != session["fingerprint"]["sha256"]:
                raise WizardError("Source file changed since it was profiled; start a new run.")
        return session

    def list_sessions(self) -> list[dict[str, Any]]:
        if not self.base.is_dir():
            return []
        sessions = []
        for run_dir in sorted(self.base.iterdir(), reverse=True):
            session_file = run_dir / "session.json"
            if session_file.is_file():
                sessions.append(read_json(session_file))
        return sessions

    def session_detail(self, run_id: str) -> dict[str, Any]:
        run_dir = self.run_dir(run_id)
        roles_file = run_dir / "sheet-roles.json"
        report_file = run_dir / "join-report.json"
        return {
            "session": self.load_session(run_id, verify_source=False),
            "profile": read_json(run_dir / "sheet-profile.json"),
            "roles": read_json(roles_file)["roles"] if roles_file.is_file() else None,
            "joinReport": read_json(report_file) if report_file.is_file() else None,
        }

    # ------------------------------------------------------------- roles
    def confirm_roles(self, run_id: str, roles: dict[str, str]) -> dict[str, Any]:
        session = self.load_session(run_id)
        run_dir = self.run_dir(run_id)
        profile = read_json(run_dir / "sheet-profile.json")
        cards = {card["sheetName"]: card for card in profile["sheets"]}
        confirmed: dict[str, str] = {}
        for sheet, role in (roles or {}).items():
            if sheet not in cards:
                raise WizardError(f"Unknown sheet: {sheet}")
            if role not in VALID_ROLES:
                raise WizardError(f"Invalid role for {sheet}: {role}")
            confirmed[sheet] = role
        for sheet in cards:
            confirmed.setdefault(sheet, ROLE_EXCLUDE)
        for sheet, role in confirmed.items():
            sheet_type = cards[sheet]["sheetType"]
            if role == ROLE_OPTIONS and sheet_type != SHEET_TYPE_OPTIONS:
                raise WizardError(
                    f"{sheet} was not detected as an options matrix; it cannot take the options role."
                )
            if role == ROLE_PRICE and sheet_type != SHEET_TYPE_PRICE:
                raise WizardError(
                    f"{sheet} was not detected as a price sheet; it cannot take the price role."
                )
        options = [sheet for sheet, role in confirmed.items() if role == ROLE_OPTIONS]
        price = [sheet for sheet, role in confirmed.items() if role == ROLE_PRICE]
        if not options:
            raise WizardError("Confirm at least one options sheet.")
        if len(price) != 1:
            raise WizardError("Confirm exactly one price sheet.")
        write_json(run_dir / "sheet-roles.json", {"schemaVersion": SCHEMA_VERSION, "roles": confirmed})
        for stale in PARSE_ARTIFACTS:
            (run_dir / stale).unlink(missing_ok=True)
        session["state"] = STATE_ROLES_CONFIRMED
        write_json(run_dir / "session.json", session)
        return session

    # ------------------------------------------------------------- parse
    def run_parse(self, run_id: str) -> dict[str, Any]:
        session = self.load_session(run_id)
        if session["state"] not in (STATE_ROLES_CONFIRMED, STATE_PARSED):
            raise WizardError("Confirm sheet roles before parsing.")
        run_dir = self.run_dir(run_id)
        roles = read_json(run_dir / "sheet-roles.json")["roles"]
        parsed = parse_confirmed_sheets(Path(session["sourcePath"]), roles)
        report = join_prices(parsed["candidates"], parsed["priceRows"])
        write_json(
            run_dir / "option-candidates.json",
            {
                "schemaVersion": SCHEMA_VERSION,
                "candidates": parsed["candidates"],
                "skippedRows": parsed["skippedRows"],
            },
        )
        write_json(
            run_dir / "price-rows.json",
            {
                "schemaVersion": SCHEMA_VERSION,
                "priceRows": parsed["priceRows"],
                "baseModelPriceRows": parsed["baseModelPriceRows"],
                "skippedPriceRows": parsed["skippedPriceRows"],
            },
        )
        write_json(run_dir / "join-report.json", report)
        session["state"] = STATE_PARSED
        write_json(run_dir / "session.json", session)
        return {"session": session, "joinReport": report}

    # -------------------------------------------------------- candidates
    def candidates(
        self,
        run_id: str,
        *,
        sheet: str = "",
        price_match: str = "",
        family: str = "",
        query: str = "",
    ) -> dict[str, Any]:
        session = self.load_session(run_id, verify_source=False)
        if session["state"] != STATE_PARSED:
            raise WizardError("Run the parse before requesting candidates.")
        run_dir = self.run_dir(run_id)
        payload = read_json(run_dir / "option-candidates.json")
        report = read_json(run_dir / "join-report.json")
        rows = payload["candidates"]
        if sheet:
            rows = [row for row in rows if row["sheetName"] == sheet]
        if family:
            rows = [row for row in rows if row["modelFamily"] == family]
        if price_match:
            rows = [row for row in rows if (row["priceMatch"] or "") == price_match]
        if query:
            needle = query.lower()
            rows = [
                row
                for row in rows
                if needle in row["rpo"].lower()
                or needle in row["refOnlyRpo"].lower()
                or needle in row["description"].lower()
            ]
        return {
            "session": session,
            "total": len(payload["candidates"]),
            "matched": len(rows),
            "candidates": rows,
            "skippedRows": payload["skippedRows"],
            "unmatchedPriceRows": report["unmatchedPriceRows"],
        }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_ingest_wizard_session.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add scripts/corvette_form_generator/ingest/wizard/session.py tests/test_ingest_wizard_session.py
git commit -m "feat: Add wizard Pass A session store with fail-closed state machine"
```

---

### Task 5: Wizard HTTP server (`ingest_wizard_server.py`)

**Files:**
- Create: `scripts/ingest_wizard_server.py`
- Test: `tests/test_ingest_wizard_server.py`

**Interfaces:**
- Consumes: Task 4 `WizardSessionStore` / `WizardError`.
- Produces: HTTP API used by the Task 6 UI —
  - `GET /` , `/wizard.js`, `/wizard.css` — static files from `visualizer/ingest-wizard/` (Task 6 creates them; server 404s until then, which is fine for API tests)
  - `GET /api/wizard/files` → `{"files": [...]}`
  - `POST /api/wizard/upload?filename=<name>` (raw body) → `{"file": {...}}`
  - `GET /api/wizard/sessions` → `{"sessions": [...]}`
  - `POST /api/wizard/sessions` body `{"file": name}` → `{"session", "profile"}`
  - `GET /api/wizard/sessions/<run-id>` → `session_detail` payload
  - `POST /api/wizard/sessions/<run-id>/roles` body `{"roles": {...}}` → `{"session"}`
  - `POST /api/wizard/sessions/<run-id>/parse` → `{"session", "joinReport"}`
  - `GET /api/wizard/sessions/<run-id>/candidates?sheet=&priceMatch=&family=&q=` → candidates payload
  - Errors: `{"error": message}` with `WizardError.status`; unknown route → 404; upload bigger than 50 MB → 400.

- [ ] **Step 1: Write the failing server tests**

`tests/test_ingest_wizard_server.py`:

```python
#!/usr/bin/env python3
"""HTTP API tests for the ingest wizard server (Pass A)."""

from __future__ import annotations

import json
import sys
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for entry in (ROOT / "scripts", ROOT / "tests"):
    if str(entry) not in sys.path:
        sys.path.insert(0, str(entry))

import ingest_wizard_server as srv  # noqa: E402
from corvette_form_generator.ingest.wizard.session import WizardSessionStore  # noqa: E402
from ingest_wizard_fixtures import build_raw_export  # noqa: E402


class WizardServerTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._tmp = tempfile.TemporaryDirectory()
        cls.root = Path(cls._tmp.name)
        build_raw_export(cls.root / "raw.xlsx")
        srv.WizardHandler.store = WizardSessionStore(cls.root)
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), srv.WizardHandler)
        cls.port = cls.server.server_address[1]
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls) -> None:
        cls.server.shutdown()
        cls._tmp.cleanup()

    def request(self, method: str, path: str, body: bytes | None = None) -> tuple[int, dict]:
        request = urllib.request.Request(
            f"http://127.0.0.1:{self.port}{path}", data=body, method=method
        )
        if body is not None:
            request.add_header("Content-Type", "application/json")
        try:
            with urllib.request.urlopen(request) as response:
                return response.status, json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as error:
            return error.code, json.loads(error.read().decode("utf-8"))

    def post_json(self, path: str, payload: dict) -> tuple[int, dict]:
        return self.request("POST", path, json.dumps(payload).encode("utf-8"))

    def test_full_wizard_flow(self) -> None:
        status, files = self.request("GET", "/api/wizard/files")
        self.assertEqual(status, 200)
        self.assertIn("raw.xlsx", [f["name"] for f in files["files"]])

        status, created = self.post_json("/api/wizard/sessions", {"file": "raw.xlsx"})
        self.assertEqual(status, 200)
        run_id = created["session"]["runId"]
        self.assertEqual(created["session"]["state"], "profiled")
        self.assertEqual(len(created["profile"]["sheets"]), 5)

        status, _ = self.post_json(
            f"/api/wizard/sessions/{run_id}/roles",
            {"roles": {"Equipment Groups 1": "options", "Price Schedule": "price"}},
        )
        self.assertEqual(status, 200)

        status, parsed = self.post_json(f"/api/wizard/sessions/{run_id}/parse", {})
        self.assertEqual(status, 200)
        self.assertEqual(parsed["session"]["state"], "parsed")
        self.assertEqual(parsed["joinReport"]["exactMatches"], 1)

        status, table = self.request(
            "GET", f"/api/wizard/sessions/{run_id}/candidates?priceMatch=exact"
        )
        self.assertEqual(status, 200)
        self.assertEqual([c["rpo"] for c in table["candidates"]], ["BV4"])
        self.assertEqual(table["candidates"][0]["listPrice"], 395.0)
        self.assertTrue(table["candidates"][0]["sourceEvidence"]["cells"])

        status, detail = self.request("GET", f"/api/wizard/sessions/{run_id}")
        self.assertEqual(status, 200)
        self.assertEqual(detail["session"]["state"], "parsed")
        self.assertIsNotNone(detail["roles"])
        self.assertIsNotNone(detail["joinReport"])

    def test_error_mapping(self) -> None:
        status, payload = self.post_json("/api/wizard/sessions", {"file": "missing.xlsx"})
        self.assertEqual(status, 400)
        self.assertIn("error", payload)

        status, _ = self.request("GET", "/api/wizard/sessions/20990101-000000-abcdef")
        self.assertEqual(status, 404)

        status, _ = self.request("GET", "/api/nope")
        self.assertEqual(status, 404)

        run_id = self.post_json("/api/wizard/sessions", {"file": "raw.xlsx"})[1]["session"]["runId"]
        status, payload = self.post_json(f"/api/wizard/sessions/{run_id}/parse", {})
        self.assertEqual(status, 400)
        self.assertIn("roles", payload["error"].lower())

    def test_upload_endpoint(self) -> None:
        status, payload = self.request(
            "POST", "/api/wizard/upload?filename=extra.xlsx", b"binary-bytes"
        )
        self.assertEqual(status, 200)
        self.assertEqual(payload["file"]["name"], "extra.xlsx")
        status, payload = self.request(
            "POST", "/api/wizard/upload?filename=..%2Fevil.xlsx", b"x"
        )
        self.assertEqual(status, 400)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/test_ingest_wizard_server.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'ingest_wizard_server'`

- [ ] **Step 3: Implement the server**

`scripts/ingest_wizard_server.py`:

```python
#!/usr/bin/env python3
"""Local dev server for the interactive ingest wizard (Pass A).

Read-only toward the canonical workbook and raw exports; writes only
run-scoped JSON under form-output/ingest-wizard/. See
docs/ingest/pass-a/interactive-ingest-wizard-pass-a-spec.md.
"""

from __future__ import annotations

import argparse
import json
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from corvette_form_generator.ingest.wizard.session import (  # noqa: E402
    WizardError,
    WizardSessionStore,
)

UI_DIR = ROOT / "visualizer" / "ingest-wizard"
STATIC_FILES = {
    "/": ("index.html", "text/html; charset=utf-8"),
    "/wizard.js": ("wizard.js", "text/javascript; charset=utf-8"),
    "/wizard.css": ("wizard.css", "text/css; charset=utf-8"),
}
MAX_UPLOAD_BYTES = 50 * 1024 * 1024


class WizardHandler(BaseHTTPRequestHandler):
    store: WizardSessionStore | None = None

    # ------------------------------------------------------------ plumbing
    def log_message(self, format: str, *args) -> None:  # noqa: A002 - stdlib signature
        pass

    def _send_json(self, payload: dict, status: int = 200) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_error_json(self, message: str, status: int) -> None:
        self._send_json({"error": message}, status=status)

    def _read_body(self) -> bytes:
        length = int(self.headers.get("Content-Length") or 0)
        if length > MAX_UPLOAD_BYTES:
            raise WizardError("Request body too large.")
        return self.rfile.read(length) if length else b""

    def _json_body(self) -> dict:
        body = self._read_body()
        if not body:
            return {}
        try:
            payload = json.loads(body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise WizardError(f"Invalid JSON body: {exc}") from exc
        if not isinstance(payload, dict):
            raise WizardError("JSON body must be an object.")
        return payload

    def _serve_static(self, path: str) -> None:
        name, content_type = STATIC_FILES[path]
        file_path = UI_DIR / name
        if not file_path.is_file():
            self._send_error_json(f"UI file missing: {name}", 404)
            return
        body = file_path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    # ------------------------------------------------------------- routes
    def do_GET(self) -> None:  # noqa: N802 - stdlib naming
        split = urlsplit(self.path)
        path = unquote(split.path)
        query = parse_qs(split.query)
        try:
            if path in STATIC_FILES:
                self._serve_static(path)
            elif path == "/api/wizard/files":
                self._send_json({"files": self.store.list_source_files()})
            elif path == "/api/wizard/sessions":
                self._send_json({"sessions": self.store.list_sessions()})
            elif path.startswith("/api/wizard/sessions/") and path.endswith("/candidates"):
                run_id = path[len("/api/wizard/sessions/"):-len("/candidates")]
                self._send_json(
                    self.store.candidates(
                        run_id,
                        sheet=(query.get("sheet") or [""])[0],
                        price_match=(query.get("priceMatch") or [""])[0],
                        family=(query.get("family") or [""])[0],
                        query=(query.get("q") or [""])[0],
                    )
                )
            elif path.startswith("/api/wizard/sessions/"):
                run_id = path[len("/api/wizard/sessions/"):]
                self._send_json(self.store.session_detail(run_id))
            else:
                self._send_error_json("Not found.", 404)
        except WizardError as exc:
            self._send_error_json(str(exc), exc.status)

    def do_POST(self) -> None:  # noqa: N802 - stdlib naming
        split = urlsplit(self.path)
        path = unquote(split.path)
        query = parse_qs(split.query)
        try:
            if path == "/api/wizard/upload":
                filename = (query.get("filename") or [""])[0]
                saved = self.store.save_upload(filename, self._read_body())
                self._send_json({"file": saved})
            elif path == "/api/wizard/sessions":
                payload = self._json_body()
                file_name = str(payload.get("file") or "")
                if not file_name:
                    raise WizardError("Request body must name a source file.")
                self._send_json(self.store.create_session(file_name))
            elif path.startswith("/api/wizard/sessions/") and path.endswith("/roles"):
                run_id = path[len("/api/wizard/sessions/"):-len("/roles")]
                payload = self._json_body()
                roles = payload.get("roles")
                if not isinstance(roles, dict):
                    raise WizardError("Request body must carry a roles object.")
                session = self.store.confirm_roles(run_id, roles)
                self._send_json({"session": session})
            elif path.startswith("/api/wizard/sessions/") and path.endswith("/parse"):
                run_id = path[len("/api/wizard/sessions/"):-len("/parse")]
                self._json_body()  # accept and ignore an empty JSON body
                self._send_json(self.store.run_parse(run_id))
            else:
                self._send_error_json("Not found.", 404)
        except WizardError as exc:
            self._send_error_json(str(exc), exc.status)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8040)
    parser.add_argument("--root", default=str(ROOT), help="Project root holding raw exports.")
    args = parser.parse_args()

    WizardHandler.store = WizardSessionStore(Path(args.root))
    server = ThreadingHTTPServer((args.host, args.port), WizardHandler)
    print(f"ingest wizard: http://{args.host}:{args.port}/")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/test_ingest_wizard_server.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add scripts/ingest_wizard_server.py tests/test_ingest_wizard_server.py
git commit -m "feat: Add ingest wizard HTTP server with Pass A JSON API"
```

---

### Task 6: Browser UI (`visualizer/ingest-wizard/`)

**Files:**
- Create: `visualizer/ingest-wizard/index.html`
- Create: `visualizer/ingest-wizard/wizard.css`
- Create: `visualizer/ingest-wizard/wizard.js`

**Interfaces:**
- Consumes: Task 5 API exactly as specified (no other endpoints).
- Produces: the four-stage wizard page (Choose file → Sheet cards → Confirm roles → Candidates). No decision capture, no editing, no export (Pass A is read-only review).

UI requirements (verify each manually in Task 7):

1. **Choose file** — lists `/api/wizard/files` with origin badges, upload control posting to `/api/wizard/upload`, and a "Profile sheets" button that creates the session.
2. **Sheet cards** — one card per sheet: friendly type label ("Options matrix", "Price sheet", "Unsupported"), model family chip, subtype note for standard equipment, variant-column chips (label + model code + trim), row-stat line ("147 orderable options · 20 ref-only rows"), confidence badge with reasons on hover/expand, and a three-way role control (Options / Price / Exclude) preselected to `recommendedRole`.
3. **Confirm roles** — "Confirm sheet roles" button posts roles; validation errors from the server render inline (red banner, no state change). On success a "Run first parse" button appears.
4. **Candidates** — summary chips (total candidates, exact / ambiguous / missing price counts, unmatched price rows, skipped rows), filters (sheet select, price-match select, text search), and the table: RPO, ref-only RPO, name/description, model family + sheet, per-variant status chips (raw symbol with parsed status in the title attribute), price + match badge, and an expandable evidence drawer showing `sourceEvidence.cells` plus any joined price rows.

Implementation notes:

- Vanilla JS, one `state` object, `fetch` wrappers `getJSON(path)` / `postJSON(path, body)` that throw on `{"error"}` payloads and surface messages in a single `#error-banner` element.
- Render with template functions returning HTML strings + one delegated click/change listener per stage container; no frameworks.
- Dark "carbon" styling consistent with the repo's current form restyle: near-black background (`#111`), panel gray (`#1b1b1d`), light text, single accent for actions; system font stack; no external fonts or CDNs.
- Status chip colors by parsed status: standard = subdued green, available = blue, unavailable = gray strikethrough symbol, unresolved = amber; raw symbol is always the visible text.
- Price match badge: exact = green with the price, ambiguous = amber "n candidates", none = gray "no price".
- Keep the three files under ~150 (html), ~200 (css), ~400 (js) lines; split rendering helpers by stage inside `wizard.js`.

- [ ] **Step 1: Write `index.html`** — stage containers `#stage-files`, `#stage-sheets`, `#stage-candidates`, header with run-id display, error banner, and script/style includes.
- [ ] **Step 2: Write `wizard.css`** — layout (cards grid, table), chips/badges, stage visibility classes.
- [ ] **Step 3: Write `wizard.js`** — state machine mirroring session states; on load fetch files; stage transitions per the UI requirements above.
- [ ] **Step 4: Manual smoke check**

```bash
.venv/bin/python scripts/ingest_wizard_server.py --port 8040
```

Open `http://127.0.0.1:8040/`, walk the four stages against the original Pass A raw export, and check the browser console for errors. (Full proof-of-success verification is Task 7.)

- [ ] **Step 5: Commit**

```bash
git add visualizer/ingest-wizard/
git commit -m "feat: Add ingest wizard browser UI (choose, profile, confirm, candidates)"
```

---

### Task 7: Docs, full test run, and proof-of-success verification

**Files:**
- Modify: `Order-Guide_IngestPrompt.md` (pass sequence section)
- Modify: `README.md` (repository map + server workflow command)
- Modify: `docs/ingest/README.md` (Pass A status: implemented)
- Modify: `docs/ingest/pass-a/interactive-ingest-wizard-pass-a-spec.md` (Status → Implemented, validation results, residual risks)

**Interfaces:**
- Consumes: everything above.
- Produces: closed-out Pass A per AGENTS.md §11.

- [ ] **Step 1: Update `Order-Guide_IngestPrompt.md`** — in "Pass sequence and artifacts", add before the Pass 0 line:

```markdown
- Pass A — interactive ingest wizard (current entry path): browser-first upload/choose → sheet-card profiling → user sheet-role confirmation → deterministic option/price parse → exact 1-to-1 price joins → read-only candidate table. Artifacts under `form-output/ingest-wizard/<run-id>/`: `session.json`, `sheet-profile.json`, `sheet-roles.json`, `option-candidates.json`, `price-rows.json`, `join-report.json`. No apply planning, decision capture, or workbook writes.
```

and change the paragraph intro so Pass 0–5 read as the superseded legacy entry path (kept as libraries/reference). Also extend the transient-artifact boundary sentence in "Contract and inputs" to include `form-output/ingest-wizard/<run-id>/`.

- [ ] **Step 2: Update `README.md`** — repository map line under `workbook_editor_server.py`:

```text
  ingest_wizard_server.py     localhost ingest wizard UI (raw order-guide intake)
```

and in "Workbook Editor Workflow" (or an adjacent new subsection "Ingest Wizard"):

```sh
.venv/bin/python scripts/ingest_wizard_server.py [--port 8040]
```

- [ ] **Step 3: Update `docs/ingest/README.md`** — flip the Pass A bullet to "implemented", keep the superseded note accurate.

- [ ] **Step 4: Run the full test suite**

Run: `.venv/bin/python -m pytest tests/`
Expected: all tests pass, including the pre-existing ingest/editor suites.

- [ ] **Step 5: Browser proof of success** — start the server, open the browser, and verify against the real raw export:

- choose the original Pass A raw export;
- sheet cards: 23 sheets — 16 options matrices (4 flagged standard-equipment subtype, recommended exclude), 1 price sheet, 2 unsupported Color and Trim; `Equipment Groups 4` shows `mixed` family (ZR1 + ZR1X) with 8 variant columns;
- confirm recommended roles, run the parse;
- candidate table: `BV4` shows an exact price match at 395 with evidence cells; `PDB`, `PDD`, `PDF` show ambiguous matches with 3 price rows each; filters and the evidence drawer work.

- [ ] **Step 6: Close out the spec** — set Status to `Implemented <date>` with changed files, validation results (test counts + browser verification), companion-file impact, and residual risks. Verify `git status` shows no `stingray_master.xlsx` change.

- [ ] **Step 7: Commit**

```bash
git add Order-Guide_IngestPrompt.md README.md docs/ingest/README.md docs/ingest/pass-a/
git commit -m "feat: Close out ingest wizard Pass A with docs and verification results"
```
