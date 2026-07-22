#!/usr/bin/env python3
"""Tests for the shared workbook domain registry (workbook_domain.registry)."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from corvette_form_generator import editor_ops  # noqa: E402
from corvette_form_generator.workbook_domain.registry import (  # noqa: E402
    EDITOR_SHEET_META,
    GLOBAL_SHEET_FAMILIES,
    SOURCE_ROLE_FAMILIES,
    family_spec,
    registered_sheet_families,
)


def test_editor_ops_uses_shared_registry_objects():
    assert editor_ops.EDITOR_SHEET_META is EDITOR_SHEET_META
    assert editor_ops.GLOBAL_SHEET_FAMILIES is GLOBAL_SHEET_FAMILIES
    assert editor_ops.SOURCE_ROLE_FAMILIES is SOURCE_ROLE_FAMILIES


def test_registered_sheet_families_uses_live_workbook_rows():
    extract = {
        "sheets": {
            "model_workbook_sources": {
                "rows": [{
                    "model_key": "demo",
                    "source_role": "source_option_sheet",
                    "sheet_name": "demo_options",
                    "active": True,
                }]
            }
        }
    }
    assert registered_sheet_families(extract)["demo_options"] == "options"
    assert family_spec("options")["key"] == ("option_id",)
