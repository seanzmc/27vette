#!/usr/bin/env python3
"""Checkpoint 2A/2B RED contracts: workbook-owned group display_label.

Covers the shared registry contract (registry.py), the workbook schema
validator's label gate, and the generator's group loaders. The schema tests
reuse the registry-shaped fixture from test_schema_validation_metadata.py so a
drift in that fixture cannot mask drift here.
"""

from __future__ import annotations

import csv
import json
import runpy
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

from corvette_form_generator.model_config import ModelConfig  # noqa: E402
from corvette_form_generator.rules import (  # noqa: E402
    load_exclusive_groups,
    load_rule_groups,
)
from corvette_form_generator.workbook_domain import registry  # noqa: E402

sys.path.insert(0, "tests")

GROUP_FAMILIES = ("exclusive_groups", "rule_groups")
ROOT = Path(__file__).resolve().parents[1]
REVIEW_DIR = ROOT / "workbook-manager" / "review"
# Spec §7.2 placeholders that an approved label must never equal.
PLACEHOLDER_LABELS = tuple(sorted(registry.GROUP_DISPLAY_LABEL_PLACEHOLDERS))


def _registry_columns(family: str) -> list[str]:
    return list(registry.WRITABLE_COLUMNS[family])


def _z06_model_config() -> ModelConfig:
    """A z06 config resolved against a real canonical-workbook openpyxl load."""

    from openpyxl import load_workbook

    from corvette_form_generator.model_configs import base_model_config
    from corvette_form_generator.runtime_metadata import load_model_config_overrides

    wb = load_workbook("stingray_master.xlsx", read_only=True, data_only=True)
    try:
        return load_model_config_overrides(wb, base_model_config("z06"))
    finally:
        wb.close()


def _minimal_group_workbook():
    """The shared registry-shaped fixture plus one z06 group row per family."""

    from test_schema_validation_metadata import registry_shaped_workbook

    wb = registry_shaped_workbook()
    for sheet, values in (
        ("z06_rule_groups", {"group_id": "grp_r1", "display_label": "", "group_type": "requires_any",
                             "source_id": "opt_z06", "active": True}),
        ("z06_exclusive_groups", {"group_id": "grp_e1", "display_label": "",
                                  "selection_mode": "single_within_group", "active": True}),
    ):
        ws = wb[sheet]
        headers = [c.value for c in ws[1]]
        ws.append([values.get(header) for header in headers])
    return wb


def _validate(wb):
    from test_schema_validation_metadata import validate_temp_workbook

    return validate_temp_workbook(wb)


class GroupDisplayLabelRegistryTests(unittest.TestCase):
    """The shared registry owns the display_label column for both group families."""

    def test_registry_declares_display_label_after_group_id(self) -> None:
        for family in GROUP_FAMILIES:
            columns = registry.WRITABLE_COLUMNS[family]
            self.assertIn("display_label", columns, family)
            self.assertEqual(
                columns.index("display_label"),
                columns.index("group_id") + 1,
                f"{family}: display_label must sit immediately after group_id",
            )

    def test_display_label_is_optional_not_required_on_add(self) -> None:
        for family in GROUP_FAMILIES:
            meta = registry.EDITOR_SHEET_META[family]
            self.assertIn("display_label", registry.OPTIONAL_COLUMNS[family], family)
            self.assertIn("display_label", meta["optional_columns"], family)
            self.assertNotIn("display_label", meta["required_on_add"], family)


class GroupDisplayLabelSchemaValidationTests(unittest.TestCase):
    """§7.2 label rules enforced by validate_group_display_labels()."""

    def test_registry_shaped_group_sheets_accept_display_label(self) -> None:
        wb = _minimal_group_workbook()
        for sheet, label in (("z06_rule_groups", "Required wheels"), ("z06_exclusive_groups", "Wheel selection")):
            headers = [c.value for c in wb[sheet][1]]
            last = wb[sheet].max_row
            wb[sheet].cell(row=last, column=headers.index("display_label") + 1).value = label
        issues = _validate(wb)
        self.assertFalse(
            [i for i in issues if i.severity == "error"],
            [(i.check_id, i.message) for i in issues if i.severity == "error"],
        )

    def test_display_label_must_not_equal_placeholder(self) -> None:
        wb = _minimal_group_workbook()
        sheet = "z06_exclusive_groups"
        headers = [c.value for c in wb[sheet][1]]
        col = headers.index("display_label") + 1
        for placeholder in PLACEHOLDER_LABELS:
            wb[sheet].cell(row=wb[sheet].max_row, column=col).value = placeholder
            issues = _validate(wb)
            self.assertTrue(
                any(i.check_id == "group_display_label_invalid" for i in issues),
                f"placeholder {placeholder!r} not rejected",
            )
            wb[sheet].cell(row=wb[sheet].max_row, column=col).value = None

    def test_display_label_must_not_equal_group_id(self) -> None:
        wb = _minimal_group_workbook()
        sheet = "z06_exclusive_groups"
        headers = [c.value for c in wb[sheet][1]]
        col = headers.index("display_label") + 1
        wb[sheet].cell(row=wb[sheet].max_row, column=col).value = "grp_e1"
        issues = _validate(wb)
        self.assertTrue(any(i.check_id == "group_display_label_invalid" for i in issues), issues)

    def test_display_label_must_not_copy_terminal_hash_token(self) -> None:
        wb = _minimal_group_workbook()
        sheet = "z06_exclusive_groups"
        headers = [c.value for c in wb[sheet][1]]
        row = wb[sheet].max_row
        wb[sheet].cell(row=row, column=headers.index("group_id") + 1).value = (
            "z06_excl_engine_covers_1623e1da9d59"
        )
        wb[sheet].cell(row=row, column=headers.index("display_label") + 1).value = (
            "Engine Covers 1623e1da9d59"
        )

        issues = _validate(wb)

        self.assertTrue(any(i.check_id == "group_display_label_invalid" for i in issues), issues)

    def test_display_label_rejects_untrimmed_multiline_and_bad_length(self) -> None:
        wb = _minimal_group_workbook()
        sheet = "z06_exclusive_groups"
        headers = [c.value for c in wb[sheet][1]]
        col = headers.index("display_label") + 1
        for bad in (" padded", "two\nlines", "ab", "x" * 101):
            wb[sheet].cell(row=wb[sheet].max_row, column=col).value = bad
            issues = _validate(wb)
            self.assertTrue(
                any(i.check_id == "group_display_label_invalid" for i in issues),
                f"value {bad!r} not rejected",
            )
            wb[sheet].cell(row=wb[sheet].max_row, column=col).value = None

    def test_valid_display_label_passes_all_label_checks(self) -> None:
        wb = _minimal_group_workbook()
        sheet = "z06_exclusive_groups"
        headers = [c.value for c in wb[sheet][1]]
        col = headers.index("display_label") + 1
        wb[sheet].cell(row=wb[sheet].max_row, column=col).value = "Wheel selection"
        issues = _validate(wb)
        self.assertFalse(any(i.check_id == "group_display_label_invalid" for i in issues), issues)


class GroupDisplayLabelGeneratorTests(unittest.TestCase):
    """Generator group loaders carry display_label into their group dicts."""

    def setUp(self) -> None:
        self.config = _z06_model_config()

    def test_load_rule_groups_carries_display_label(self) -> None:
        groups = load_rule_groups(_minimal_group_workbook(), self.config)
        matching = [g for g in groups if g.get("group_id") == "grp_r1"]
        self.assertEqual(len(matching), 1, groups)
        self.assertEqual(matching[0].get("display_label"), "")

    def test_load_exclusive_groups_carries_display_label(self) -> None:
        groups = load_exclusive_groups(_minimal_group_workbook(), self.config)
        matching = [g for g in groups if g.get("group_id") == "grp_e1"]
        self.assertEqual(len(matching), 1, groups)
        self.assertEqual(matching[0].get("display_label"), "")

    def test_missing_label_loads_as_blank_not_invented(self) -> None:
        wb = _minimal_group_workbook()
        headers = [c.value for c in wb["z06_rule_groups"][1]]
        col = headers.index("display_label") + 1
        wb["z06_rule_groups"].cell(row=wb["z06_rule_groups"].max_row, column=col).value = "Required wheels"
        groups = load_rule_groups(wb, self.config)
        matching = [g for g in groups if g.get("group_id") == "grp_r1"]
        self.assertEqual(len(matching), 1, groups)
        self.assertEqual(matching[0].get("display_label"), "Required wheels")


class GroupDisplayLabelReviewArtifactTests(unittest.TestCase):
    def test_csv_and_json_are_exact_approved_decision_companions(self) -> None:
        csv_path = REVIEW_DIR / "group-display-label-review.csv"
        self.assertNotIn(b"\r\n", csv_path.read_bytes())
        with csv_path.open(
            newline="", encoding="utf-8-sig"
        ) as fh:
            csv_rows = list(csv.DictReader(fh))
        payload = json.loads(
            (REVIEW_DIR / "group-display-label-review.json").read_text(encoding="utf-8")
        )
        json_rows = payload["records"]

        def identity(row: dict) -> tuple[str, str, str]:
            return row["model_key"], row["group_type"], row["group_id"]

        def stable_key(row: dict) -> tuple[str, str, str, int, str]:
            sheet, row_number = row["source_sheet_row"].rsplit("!", 1)
            return row["model_key"], row["group_type"], sheet, int(row_number), row["group_id"]

        self.assertEqual(payload["record_count"], len(csv_rows))
        self.assertEqual([identity(row) for row in csv_rows], [identity(row) for row in json_rows])
        self.assertEqual(csv_rows, sorted(csv_rows, key=stable_key))
        self.assertEqual({row["review_status"] for row in csv_rows}, {"approved"})
        self.assertTrue(
            all(
                registry.GROUP_DISPLAY_LABEL_MIN_LENGTH
                <= len(row["proposed_display_label"])
                <= registry.GROUP_DISPLAY_LABEL_MAX_LENGTH
                for row in csv_rows
            )
        )
        for csv_row, json_row in zip(csv_rows, json_rows, strict=True):
            for field in (
                "proposed_display_label",
                "review_status",
                "reviewer_note",
                "audience",
            ):
                self.assertEqual(csv_row[field], json_row[field], (identity(csv_row), field))

    def test_approved_review_labels_match_canonical_workbook(self) -> None:
        from openpyxl import load_workbook

        with (REVIEW_DIR / "group-display-label-review.csv").open(
            newline="", encoding="utf-8-sig"
        ) as fh:
            rows = list(csv.DictReader(fh))
        wb = load_workbook(ROOT / "stingray_master.xlsx", read_only=True, data_only=True)
        try:
            for row in rows:
                sheet_name, row_number = row["source_sheet_row"].rsplit("!", 1)
                ws = wb[sheet_name]
                headers = [str(cell.value or "") for cell in ws[1]]
                self.assertEqual(
                    headers.index("display_label"),
                    headers.index("group_id") + 1,
                    sheet_name,
                )
                actual = ws.cell(
                    row=int(row_number),
                    column=headers.index("display_label") + 1,
                ).value
                self.assertEqual(
                    actual,
                    row["proposed_display_label"],
                    (row["model_key"], row["group_type"], row["group_id"]),
                )
        finally:
            wb.close()

    def test_review_generator_refuses_to_overwrite_approved_decisions(self) -> None:
        script_path = REVIEW_DIR / "generate_group_display_label_review.py"
        module_globals = runpy.run_path(str(script_path), run_name="group_label_review_generator")

        with tempfile.TemporaryDirectory() as tmp:
            review_dir = Path(tmp)
            paths = []
            for name in ("group-display-label-review.csv", "group-display-label-review.json"):
                source = REVIEW_DIR / name
                target = review_dir / name
                shutil.copy2(source, target)
                paths.append(target)
            before = {path.name: path.read_bytes() for path in paths}
            module_globals["REVIEW_DIR"] = review_dir

            with self.assertRaisesRegex(RuntimeError, "reviewed decisions"):
                module_globals["main"]()

            self.assertEqual({path.name: path.read_bytes() for path in paths}, before)


if __name__ == "__main__":
    unittest.main()
