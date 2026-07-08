#!/usr/bin/env python3
"""Pass C editor_ops extensions: global sheet families + create_sheet ops.

Fixture workbooks only; schema validation is disabled because the compact
fixture is not a schema-complete workbook. The live workbook is never used.
"""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

from openpyxl import load_workbook

ROOT = Path(__file__).resolve().parents[1]
for entry in (ROOT / "scripts", ROOT / "tests"):
    if str(entry) not in sys.path:
        sys.path.insert(0, str(entry))

from corvette_form_generator.editor_ops import apply_batch  # noqa: E402
from ingest_wizard_fixtures import build_master_workbook  # noqa: E402


def batch(path: Path, items: list[dict]) -> dict:
    return {"workbookMtimeNs": str(path.stat().st_mtime_ns), "items": items}


class GlobalFamilyOpsTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.path = build_master_workbook(Path(self._tmp.name) / "master.xlsx")

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def run_batch(self, items: list[dict], *, write: bool = False) -> dict:
        return apply_batch(
            self.path,
            batch(self.path, items),
            write=write,
            run_schema_validation=False,
            log_path=Path(self._tmp.name) / "edit-log.jsonl",
        )

    def test_model_master_add_via_global_family(self) -> None:
        result = self.run_batch(
            [
                {
                    "action": "add",
                    "sheet": "model_master",
                    "key": {"model_key": "grand_sport_x"},
                    "row": {
                        "model_key": "grand_sport_x",
                        "registry_key": "grandSportX",
                        "model_label": "Grand Sport X",
                        "expected_variant_count": 6,
                        "default_model": False,
                        "active": False,
                    },
                }
            ],
            write=True,
        )
        self.assertTrue(result["ok"], result)
        wb = load_workbook(self.path, read_only=True)
        rows = list(wb["model_master"].iter_rows(values_only=True))
        wb.close()
        self.assertIn("grand_sport_x", [row[0] for row in rows])

    def test_presentation_family_add(self) -> None:
        result = self.run_batch(
            [
                {
                    "action": "add",
                    "sheet": "runtime_steps",
                    "key": {"model_key": "zr1", "step_key": "paint"},
                    "row": {"model_key": "zr1", "step_key": "paint", "step_label": "Paint", "runtime_order": 1},
                }
            ],
            write=True,
        )
        self.assertTrue(result["ok"], result)

    def test_default_selection_rules_global_family_add(self) -> None:
        result = self.run_batch(
            [
                {
                    "action": "add",
                    "sheet": "default_selection_rules",
                    "key": {"model_key": "zr1", "rule_id": "default_pdb"},
                    "row": {
                        "model_key": "zr1",
                        "rule_id": "default_pdb",
                        "target_option_id": "opt_pdb_001",
                        "condition_type": "always",
                        "body_style_scope": "*",
                        "trim_level_scope": "*",
                        "variant_scope": "*",
                        "priority": 10,
                        "active": True,
                        "display_behavior": "default_selected",
                    },
                }
            ],
            write=True,
        )
        self.assertTrue(result["ok"], result)
        wb = load_workbook(self.path, read_only=True)
        rows = list(wb["default_selection_rules"].iter_rows(values_only=True))
        wb.close()
        self.assertIn("default_pdb", [row[1] for row in rows])

    def test_default_selection_rules_rejects_bad_display_behavior(self) -> None:
        result = self.run_batch(
            [
                {
                    "action": "add",
                    "sheet": "default_selection_rules",
                    "key": {"model_key": "zr1", "rule_id": "bad_default"},
                    "row": {
                        "model_key": "zr1",
                        "rule_id": "bad_default",
                        "target_option_id": "opt_pdb_001",
                        "condition_type": "always",
                        "priority": 10,
                        "active": True,
                        "display_behavior": "default-selected",
                    },
                }
            ]
        )
        self.assertFalse(result["ok"])
        self.assertTrue(any("display_behavior" in error for error in result["errors"]))

    def test_global_family_key_and_type_enforcement(self) -> None:
        result = self.run_batch(
            [
                {
                    "action": "add",
                    "sheet": "model_master",
                    "key": {"model_key": "x"},
                    "row": {"model_key": "x", "expected_variant_count": "not-a-number"},
                }
            ]
        )
        self.assertFalse(result["ok"])
        self.assertTrue(any("expected integer" in e for e in result["errors"]))
        result = self.run_batch(
            [{"action": "update", "sheet": "model_variants", "key": {"model_key": "zr1"}, "row": {"active": True}}]
        )
        self.assertFalse(result["ok"])
        self.assertTrue(any("key must be exactly" in e for e in result["errors"]))

    def test_create_sheet_then_add_rows_in_same_batch(self) -> None:
        result = self.run_batch(
            [
                {
                    "action": "create_sheet",
                    "sheet": "grandSportX_options",
                    "family": "options",
                    "headersFrom": "z06_options",
                },
                # New sheet is not in the model registry yet, so ops carry the
                # created family; a follow-up source-row add registers it.
                {
                    "action": "add",
                    "sheet": "model_workbook_sources",
                    "key": {"model_key": "grand_sport_x", "source_role": "source_option_sheet"},
                    "row": {
                        "model_key": "grand_sport_x",
                        "source_role": "source_option_sheet",
                        "sheet_name": "grandSportX_options",
                        "active": True,
                    },
                },
                {
                    "action": "add",
                    "sheet": "grandSportX_options",
                    "key": {"option_id": "opt_zzz_001"},
                    "row": {
                        "option_id": "opt_zzz_001",
                        "rpo": "ZZZ",
                        "option_name": "Test Option",
                        "section_id": "sec_whee_001",
                        "active": True,
                    },
                },
            ],
            write=True,
        )
        self.assertTrue(result["ok"], result)
        wb = load_workbook(self.path, read_only=True)
        self.assertIn("grandSportX_options", wb.sheetnames)
        rows = list(wb["grandSportX_options"].iter_rows(values_only=True))
        wb.close()
        self.assertEqual(rows[0][0], "option_id")
        self.assertEqual(rows[1][0], "opt_zzz_001")

    def test_create_sheet_failures(self) -> None:
        result = self.run_batch(
            [{"action": "create_sheet", "sheet": "z06_options", "family": "options", "headersFrom": "z06_options"}]
        )
        self.assertFalse(result["ok"])
        self.assertTrue(any("already exists" in e for e in result["errors"]))
        result = self.run_batch(
            [{"action": "create_sheet", "sheet": "new_sheet", "family": "nope", "headersFrom": "z06_options"}]
        )
        self.assertFalse(result["ok"])
        result = self.run_batch(
            [{"action": "create_sheet", "sheet": "new_sheet", "family": "options", "headersFrom": "missing"}]
        )
        self.assertFalse(result["ok"])

    def test_dry_run_leaves_file_untouched(self) -> None:
        before = self.path.read_bytes()
        result = self.run_batch(
            [
                {
                    "action": "create_sheet",
                    "sheet": "grandSportX_ovs",
                    "family": "ovs",
                    "headersFrom": "z06_options",
                }
            ]
        )
        # ovs keys aren't in z06_options headers -> template key check fails.
        self.assertFalse(result["ok"])
        self.assertEqual(self.path.read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
