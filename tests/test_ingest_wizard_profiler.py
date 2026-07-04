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
