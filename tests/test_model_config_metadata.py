#!/usr/bin/env python3
"""Focused tests for Phase 7 workbook-backed model configuration metadata."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

from openpyxl import Workbook

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from corvette_form_generator.model_configs import STINGRAY_MODEL  # noqa: E402
from corvette_form_generator.runtime_metadata import load_model_config_overrides  # noqa: E402


def workbook_with_model_metadata(
    *,
    model_rows: list[dict[str, object]] | None = None,
    source_rows: list[dict[str, object]] | None = None,
    variant_rows: list[dict[str, object]] | None = None,
) -> Workbook:
    wb = Workbook()
    del wb[wb.sheetnames[0]]
    append_sheet(
        wb,
        "model_master",
        [
            "model_key",
            "registry_key",
            "model_label",
            "model_year",
            "dataset_name",
            "export_slug",
            "expected_variant_count",
            "default_model",
            "active",
            "notes",
        ],
        model_rows or [],
    )
    append_sheet(
        wb,
        "model_workbook_sources",
        ["model_key", "source_role", "sheet_name", "active", "notes"],
        source_rows or [],
    )
    append_sheet(
        wb,
        "model_variants",
        ["model_key", "variant_id", "display_order", "active", "notes"],
        variant_rows or [],
    )
    return wb


def append_sheet(wb: Workbook, name: str, headers: list[str], rows: list[dict[str, object]]) -> None:
    ws = wb.create_sheet(name)
    ws.append(headers)
    for row in rows:
        ws.append([row.get(header, "") for header in headers])


def stingray_model_row(**overrides: object) -> dict[str, object]:
    row: dict[str, object] = {
        "model_key": "stingray",
        "registry_key": "stingray",
        "model_label": "Workbook Stingray",
        "model_year": "2027",
        "dataset_name": "Workbook dataset",
        "expected_variant_count": 2,
        "active": True,
    }
    row.update(overrides)
    return row


class ModelConfigMetadataTests(unittest.TestCase):
    def test_header_only_metadata_falls_back_to_constants(self) -> None:
        wb = workbook_with_model_metadata()
        resolved = load_model_config_overrides(wb, STINGRAY_MODEL)
        self.assertEqual(resolved, STINGRAY_MODEL)

    def test_workbook_metadata_overrides_config_fields(self) -> None:
        wb = workbook_with_model_metadata(
            model_rows=[stingray_model_row()],
            source_rows=[
                {
                    "model_key": "stingray",
                    "source_role": "source_option_sheet",
                    "sheet_name": "workbook_options",
                    "active": True,
                },
                {
                    "model_key": "stingray",
                    "source_role": "status_sheet",
                    "sheet_name": "workbook_status",
                    "active": True,
                },
            ],
            variant_rows=[
                {"model_key": "stingray", "variant_id": "z_variant", "display_order": 2, "active": True},
                {"model_key": "stingray", "variant_id": "a_variant", "display_order": 1, "active": True},
            ],
        )
        resolved = load_model_config_overrides(wb, STINGRAY_MODEL)
        self.assertEqual(resolved.model_label, "Workbook Stingray")
        self.assertEqual(resolved.dataset_name, "Workbook dataset")
        self.assertEqual(resolved.source_option_sheet, "workbook_options")
        self.assertEqual(resolved.status_sheet, "workbook_status")
        self.assertEqual(resolved.variant_ids, ("a_variant", "z_variant"))
        self.assertEqual(resolved.expected_variant_count, 2)
        self.assertEqual(STINGRAY_MODEL.source_option_sheet, "stingray_options")

    def test_unknown_source_role_fails_fast(self) -> None:
        wb = workbook_with_model_metadata(
            source_rows=[
                {
                    "model_key": "stingray",
                    "source_role": "surprise_sheet",
                    "sheet_name": "surprise",
                    "active": True,
                }
            ]
        )
        with self.assertRaisesRegex(ValueError, "Unknown model_workbook_sources roles"):
            load_model_config_overrides(wb, STINGRAY_MODEL)

    def test_duplicate_source_role_fails_fast(self) -> None:
        wb = workbook_with_model_metadata(
            source_rows=[
                {
                    "model_key": "stingray",
                    "source_role": "source_option_sheet",
                    "sheet_name": "first",
                    "active": True,
                },
                {
                    "model_key": "stingray",
                    "source_role": "source_option_sheet",
                    "sheet_name": "second",
                    "active": True,
                },
            ]
        )
        with self.assertRaisesRegex(ValueError, "Duplicate active model_workbook_sources roles"):
            load_model_config_overrides(wb, STINGRAY_MODEL)

    def test_variant_count_mismatch_fails_fast(self) -> None:
        wb = workbook_with_model_metadata(
            model_rows=[stingray_model_row(expected_variant_count=2)],
            variant_rows=[{"model_key": "stingray", "variant_id": "only_one", "display_order": 1, "active": True}],
        )
        with self.assertRaisesRegex(ValueError, "expected 2 variants"):
            load_model_config_overrides(wb, STINGRAY_MODEL)

    def test_duplicate_variant_fails_fast(self) -> None:
        wb = workbook_with_model_metadata(
            variant_rows=[
                {"model_key": "stingray", "variant_id": "dup", "display_order": 1, "active": True},
                {"model_key": "stingray", "variant_id": "dup", "display_order": 2, "active": True},
            ]
        )
        with self.assertRaisesRegex(ValueError, "Duplicate active model_variants rows"):
            load_model_config_overrides(wb, STINGRAY_MODEL)

    def test_registry_key_mismatch_fails_fast(self) -> None:
        wb = workbook_with_model_metadata(model_rows=[stingray_model_row(registry_key="wrong")])
        with self.assertRaisesRegex(ValueError, "registry_key"):
            load_model_config_overrides(wb, STINGRAY_MODEL)


if __name__ == "__main__":
    unittest.main()
