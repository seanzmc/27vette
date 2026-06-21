#!/usr/bin/env python3
# pyright: reportMissingImports=false
"""Tests for shared runtime-contract finalization."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from corvette_form_generator.model_configs import GRAND_SPORT_MODEL  # noqa: E402
from corvette_form_generator.registry_promotion import live_contract_data  # noqa: E402
from corvette_form_generator.runtime_contract import build_model_runtime_contract  # noqa: E402


class RuntimeContractBuilderTests(unittest.TestCase):
    def test_builder_preserves_existing_live_contract_cleanup_behavior(self) -> None:
        draft = {
            "dataset": {
                "status": "draft_not_runtime_active",
                "name": "2027 Corvette Grand Sport form data draft",
            },
            "choices": [
                {
                    "choice_id": "choice-1",
                    "source_detail_raw": "raw note",
                    "choice_mode": "single",
                    "selection_mode": "single_select_req",
                    "selection_mode_label": "Required single selection",
                    "source_option_name": "draft-only name",
                    "source_description": "draft-only description",
                    "text_cleanup_notes": ["draft-only note"],
                }
            ],
            "standardEquipment": [{"equipment_id": "std-1", "source_detail_raw": "raw note"}],
            "validation": [
                {
                    "check_id": "grand_sport_draft_status",
                    "severity": "warning",
                    "entity_type": "dataset",
                    "entity_id": "",
                    "message": "draft marker",
                },
                {
                    "check_id": "active_variants",
                    "severity": "pass",
                    "entity_type": "variant",
                    "entity_id": "",
                    "message": "ok",
                },
            ],
            "draftMetadata": {"sourcePreviewStatus": "read_only_preview"},
        }

        expected = live_contract_data(draft)
        actual = build_model_runtime_contract(GRAND_SPORT_MODEL, draft)

        self.assertEqual(actual, expected)
        self.assertEqual(actual["dataset"]["status"], "runtime_active")
        self.assertEqual(actual["dataset"]["name"], "2027 Corvette Grand Sport operational form")
        self.assertEqual(actual["choices"], [{"choice_id": "choice-1"}])
        self.assertEqual(actual["standardEquipment"], [{"equipment_id": "std-1"}])
        self.assertEqual([row["check_id"] for row in actual["validation"]], ["active_variants"])
        self.assertNotIn("draftMetadata", actual)

    def test_active_routes_use_shared_runtime_contract_builder(self) -> None:
        production_source = (ROOT / "scripts" / "corvette_form_generator" / "production.py").read_text()
        inspection_source = (ROOT / "scripts" / "corvette_form_generator" / "inspection.py").read_text()

        self.assertIn("from corvette_form_generator.runtime_contract import build_model_runtime_contract", production_source)
        self.assertIn("from corvette_form_generator.runtime_contract import build_model_runtime_contract", inspection_source)
        self.assertIn("build_model_runtime_contract(MODEL_CONFIG, data)", production_source)
        self.assertIn("build_model_runtime_contract(config, draft)", inspection_source)
        self.assertNotIn("from corvette_form_generator.registry_promotion import live_contract_data", production_source)
        self.assertNotIn("from corvette_form_generator.registry_promotion import live_contract_data", inspection_source)


if __name__ == "__main__":
    unittest.main()
