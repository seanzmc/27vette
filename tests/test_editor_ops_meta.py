#!/usr/bin/env python3
"""Tests for the workbook-editor sheet meta registry (Phase 1)."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from corvette_form_generator.editor_ops import (  # noqa: E402
    EDITOR_SHEET_META,
    SOURCE_ROLE_FAMILIES,
)


class SourceRoleFamiliesTest(unittest.TestCase):
    def test_every_role_maps_to_a_defined_family(self):
        for role, family in SOURCE_ROLE_FAMILIES.items():
            self.assertIn(family, EDITOR_SHEET_META, f"role {role} -> unknown family {family}")

    def test_known_roles_present(self):
        expected_roles = {
            "source_option_sheet", "status_sheet", "rule_mapping_sheet",
            "rule_groups_sheet", "rule_group_members_sheet",
            "exclusive_groups_sheet", "exclusive_group_members_sheet",
            "price_rules_sheet", "variant_option_overrides_sheet",
            "color_overrides_sheet", "interior_source_sheet",
        }
        self.assertEqual(set(SOURCE_ROLE_FAMILIES), expected_roles)


class EditorSheetMetaTest(unittest.TestCase):
    def test_every_family_declares_key_columns(self):
        for family, meta in EDITOR_SHEET_META.items():
            self.assertTrue(meta["key"], f"family {family} has empty key")
            self.assertIsInstance(meta["key"], tuple)

    def test_options_family_shape(self):
        meta = EDITOR_SHEET_META["options"]
        self.assertEqual(meta["key"], ("option_id",))
        self.assertEqual(meta["types"]["display_order"], "int")
        self.assertEqual(meta["types"]["selectable"], "bool")
        self.assertIn("display_behavior", meta["enums"])
        self.assertEqual(meta["refs"]["section_id"], "sections")

    def test_ovs_family_shape(self):
        meta = EDITOR_SHEET_META["ovs"]
        self.assertEqual(meta["key"], ("option_id", "variant_id"))
        self.assertEqual(
            tuple(meta["enums"]["status"]), ("standard", "available", "unavailable")
        )


if __name__ == "__main__":
    unittest.main()
