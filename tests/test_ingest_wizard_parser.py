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
