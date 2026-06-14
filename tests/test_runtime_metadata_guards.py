#!/usr/bin/env python3
"""Tests for promoted-model runtime metadata fallback guards."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

from openpyxl import Workbook

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from corvette_form_generator.runtime_metadata import (  # noqa: E402
    load_context_sections,
    load_order_summary_metadata,
    load_runtime_steps,
)

PROMOTION_HEADERS = [
    "model_key",
    "registry_key",
    "promoted_to_runtime",
    "default_model",
    "artifact_path",
    "artifact_type",
    "legacy_alias",
    "active",
    "display_order",
    "notes",
]
RUNTIME_STEP_HEADERS = ["model_key", "step_key", "step_label", "runtime_order", "source", "active", "notes"]
CONTEXT_SECTION_HEADERS = [
    "model_key",
    "context_type",
    "section_id",
    "section_name",
    "selection_mode",
    "choice_mode",
    "is_required",
    "standard_behavior",
    "section_display_order",
    "step_key",
    "step_label",
    "active",
    "notes",
]
ORDER_SUMMARY_HEADERS = ["model_key", "section_key", "section_label", "display_order", "active", "notes"]
STEP_SUMMARY_HEADERS = ["model_key", "step_key", "section_key", "active", "notes"]


def append_sheet(wb: Workbook, name: str, headers: list[str], rows: list[dict[str, object]] | None = None) -> None:
    ws = wb.create_sheet(name)
    ws.append(headers)
    for row in rows or []:
        ws.append([row.get(header, None) for header in headers])


def metadata_workbook(*, promoted: bool, runtime_rows: list[dict[str, object]] | None = None) -> Workbook:
    wb = Workbook()
    del wb[wb.sheetnames[0]]
    append_sheet(
        wb,
        "model_registry_promotion",
        PROMOTION_HEADERS,
        [
            {
                "model_key": "z06",
                "registry_key": "z06",
                "promoted_to_runtime": promoted,
                "default_model": False,
                "artifact_path": "form-output/inspection/z06-runtime-contract.json",
                "artifact_type": "draft_artifact",
                "active": True,
                "display_order": 3,
            }
        ],
    )
    append_sheet(wb, "runtime_steps", RUNTIME_STEP_HEADERS, runtime_rows or [])
    append_sheet(wb, "context_section_master", CONTEXT_SECTION_HEADERS, [])
    append_sheet(wb, "order_summary_sections", ORDER_SUMMARY_HEADERS, [])
    append_sheet(wb, "step_order_summary_map", STEP_SUMMARY_HEADERS, [])
    return wb


class RuntimeMetadataGuardTests(unittest.TestCase):
    def test_unpromoted_models_can_still_use_runtime_step_fallback(self) -> None:
        wb = metadata_workbook(promoted=False)

        rows = load_runtime_steps(wb, "z06", ["body_style"], {"body_style": "Body Style"})

        self.assertEqual(rows, [{"step_key": "body_style", "step_label": "Body Style", "runtime_order": 1, "source": "fallback_config"}])

    def test_promoted_models_cannot_use_runtime_step_fallback(self) -> None:
        wb = metadata_workbook(promoted=True)

        with self.assertRaisesRegex(ValueError, "requires workbook-owned runtime_steps rows"):
            load_runtime_steps(wb, "z06", ["body_style"], {"body_style": "Body Style"})

    def test_promoted_models_cannot_use_incomplete_runtime_steps(self) -> None:
        wb = metadata_workbook(
            promoted=True,
            runtime_rows=[
                {
                    "model_key": "z06",
                    "step_key": "body_style",
                    "step_label": "Body Style",
                    "runtime_order": 1,
                    "source": "test",
                    "active": True,
                }
            ],
        )

        with self.assertRaisesRegex(ValueError, "missing step_key values: trim_level"):
            load_runtime_steps(wb, "z06", ["body_style", "trim_level"], {"body_style": "Body Style", "trim_level": "Trim Level"})

    def test_promoted_models_cannot_use_context_section_fallback(self) -> None:
        wb = metadata_workbook(promoted=True)

        with self.assertRaisesRegex(ValueError, "requires workbook-owned context_section_master rows"):
            load_context_sections(wb, "z06", [{"section_id": "sec_context_body_style"}])

    def test_promoted_models_cannot_use_browser_order_summary_fallback(self) -> None:
        wb = metadata_workbook(promoted=True)

        with self.assertRaisesRegex(ValueError, "requires workbook-owned order_summary_sections and step_order_summary_map rows"):
            load_order_summary_metadata(wb, "z06")


if __name__ == "__main__":
    unittest.main()
