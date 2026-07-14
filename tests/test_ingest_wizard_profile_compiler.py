#!/usr/bin/env python3
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for entry in (ROOT / "scripts", ROOT / "tests"):
    if str(entry) not in sys.path:
        sys.path.insert(0, str(entry))

from corvette_form_generator.editor_ops import extract_workbook  # noqa: E402
from corvette_form_generator.ingest.wizard.compiler import build_family_registry  # noqa: E402
from corvette_form_generator.ingest.wizard.profile_compiler import build_target_profile  # noqa: E402
from ingest_wizard_fixtures import build_master_workbook  # noqa: E402


class ProfileCompilerTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.workbook = build_master_workbook(Path(self.tmp.name) / "master.xlsx")

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_grand_sport_x_lt_profile_includes_grand_sport_exclusive_interior(self) -> None:
        from openpyxl import load_workbook

        workbook = load_workbook(self.workbook)
        sources = workbook["model_workbook_sources"]
        z06_sources = [tuple(cell.value for cell in row) for row in sources.iter_rows(min_row=2)]
        for row in z06_sources:
            if row[0] == "z06":
                sources.append(["grand_sport", *row[1:]])

        lz = workbook["LZ_Interiors"]
        lt = workbook.create_sheet("lt_interiors")
        lt.append([cell.value for cell in lz[1]])
        lt.append(
            [
                "3LT_AE4_EL9",
                "Santorini Blue Dipped with Torch Red accents",
                "Napa leather seating surfaces",
                1995,
                "Included and only available with (Z25) Grand Sport Launch Edition.",
                "G26, G4Z, GBK, GPH",
                "3LT",
                "AE4",
                "EL9",
                "",
                "",
                "",
                "sec_intc_003",
                False,
                False,
                "",
            ]
        )

        scope = workbook["model_interior_scope"]
        scope.append(
            [
                "grand_sport",
                "3LT_AE4_EL9",
                "3LT",
                True,
                "opt_z25_001",
                "Grand Sport launch interior.",
                "AE4 Competition Sport Bucket Seats",
                "EL9 Santorini Blue Dipped",
                "Napa leather",
                "EL9 Santorini Blue Dipped",
                1,
                1,
                1,
                '["3LT", "AE4 Competition Sport Bucket Seats", "EL9 Santorini Blue Dipped"]',
                "AE4 Competition Sport Bucket Seats",
                "EL9 Santorini Blue Dipped",
                1,
                "fixture",
            ]
        )
        for sheet_name in (
            "runtime_steps",
            "section_presentation",
            "context_section_master",
            "order_summary_sections",
            "step_order_summary_map",
        ):
            sheet = workbook[sheet_name]
            rows = [tuple(cell.value for cell in row) for row in sheet.iter_rows(min_row=2)]
            for row in rows:
                if row[0] == "z06":
                    sheet.append(["grand_sport", *row[1:]])
        workbook.save(self.workbook)
        workbook.close()

        extract = extract_workbook(self.workbook)
        registry = build_family_registry(self.workbook, ["grand_sport_x"])["grand_sport_x"]
        profile = build_target_profile(
            extract,
            registry,
            target="grand_sport_x",
            comparator="grand_sport",
            variants=[
                {
                    "variant_id": "3lt_gsx_r07",
                    "model_year": 2027,
                    "trim_level": "3lt",
                    "body_style": "coupe",
                }
            ],
        )

        self.assertEqual(profile["trimFamily"], "LT")
        self.assertEqual(profile["interiorSheet"], "lt_interiors")
        self.assertIn("3LT_AE4_EL9", profile["interiorIds"])
        el9_scope = next(
            row
            for row in profile["rows"]
            if row["family"] == "model_interior_scope"
            and row["values"].get("interior_id") == "3LT_AE4_EL9"
        )
        self.assertEqual(el9_scope["values"]["model_key"], "grand_sport_x")
        self.assertEqual(el9_scope["values"]["trim_level"], "3LT")


if __name__ == "__main__":
    unittest.main()
