#!/usr/bin/env python3
"""Pass C tests: plan builder, scratch dry-run, approval gate.

Fixture workbooks only; schema validation is off for the dry run because the
compact fixture is not schema-complete (op-level validation still runs). The
live workbook is never touched.
"""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for entry in (ROOT / "scripts", ROOT / "tests"):
    if str(entry) not in sys.path:
        sys.path.insert(0, str(entry))

from corvette_form_generator.ingest.wizard.plan_builder import build_plan  # noqa: E402
from corvette_form_generator.ingest.wizard.session import (  # noqa: E402
    WizardError,
    WizardSessionStore,
    read_json,
)
from ingest_wizard_fixtures import build_master_workbook, build_raw_export  # noqa: E402


class PlanFlowTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        build_raw_export(self.root / "raw.xlsx")
        self.master = build_master_workbook(self.root / "master.xlsx")
        self.store = WizardSessionStore(self.root, workbook_path=self.master)
        created = self.store.create_session("raw.xlsx")
        self.run_id = created["session"]["runId"]
        roles = {card["sheetName"]: card["recommendedRole"] for card in created["profile"]["sheets"]}
        self.store.confirm_roles(self.run_id, roles)
        self.store.run_parse(self.run_id)
        self.store.select_models(self.run_id, ["zr1", "zr1x"], {"zr1": "z06", "zr1x": "z06"})

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def complete_model(self, model: str, *, extra: list[dict] | None = None) -> None:
        queue = self.store.review_queue(self.run_id, model, "section")
        decisions = []
        reconciliation = self.store.reconciliation(self.run_id)["models"].get(model, {})
        if not reconciliation.get("agrees", True):
            decisions.append(
                {
                    "model": model,
                    "lane": "relationship",
                    "groupKey": "variant_reconciliation",
                    "action": "needs_product_decision",
                    "payload": {},
                    "resolution": "approved_for_plan",
                }
            )
        for candidate in queue["candidates"]:
            decisions.append(
                {
                    "model": model,
                    "lane": "section",
                    "candidateId": candidate["candidateId"],
                    "action": "assign_section",
                    "payload": {"sectionId": "sec_whee_001"},
                    "resolution": "approved_for_plan",
                }
            )
            action = "accept_exact_price" if candidate["priceMatch"] == "exact" else "confirm_no_price"
            decisions.append(
                {
                    "model": model,
                    "lane": "price",
                    "candidateId": candidate["candidateId"],
                    "action": action,
                    "payload": {},
                    "resolution": "approved_for_plan",
                }
            )
        for candidate in self.store.review_queue(self.run_id, model, "status_nuance")["candidates"]:
            decisions.append(
                {
                    "model": model,
                    "lane": "status_nuance",
                    "candidateId": candidate["candidateId"],
                    "action": "confirm_status",
                    "payload": {},
                    "resolution": "approved_for_plan",
                }
            )
        prefill = self.store.review_queue(self.run_id, model, "presentation")["prefill"]
        for sheet, proposals in prefill["sheets"].items():
            decisions.append(
                {
                    "model": model,
                    "lane": "presentation",
                    "groupKey": sheet,
                    "action": "approve_presentation_rows",
                    "payload": {"rows": [p["row"] for p in proposals], "templateModel": "z06"},
                    "resolution": "approved_for_plan",
                }
            )
        decisions.extend(extra or [])
        self.store.save_decisions(self.run_id, decisions)

    def complete_all(self, *, zr1_extra: list[dict] | None = None) -> None:
        self.complete_model("zr1", extra=zr1_extra)
        self.complete_model("zr1x")
        self.store.mark_complete(self.run_id)

    def plan_inputs(self) -> dict:
        run_dir = self.store.run_dir(self.run_id)
        selection = read_json(run_dir / "model-selection.json")
        candidates = read_json(run_dir / "option-candidates.json")["candidates"]
        decisions = {r["decisionId"]: r for r in read_json(run_dir / "decisions.json")["decisions"]}
        return {
            "workbook_path": self.master,
            "selection": selection,
            "candidates": candidates,
            "decisions": decisions,
            "candidates_fingerprint": selection["candidatesFingerprint"],
        }

    def test_plan_requires_decisions_complete(self) -> None:
        with self.assertRaises(WizardError):
            self.store.build_apply_plan(self.run_id, schema_validation=False)

    def test_plan_deterministic_and_covered(self) -> None:
        self.complete_all()
        inputs = self.plan_inputs()
        plan_a = build_plan(**inputs)
        plan_b = build_plan(**inputs)
        self.assertEqual(json.dumps(plan_a, sort_keys=True), json.dumps(plan_b, sort_keys=True))
        self.assertTrue(plan_a["valid"], plan_a["report"]["blockingGaps"])
        self.assertEqual(plan_a["coverage"]["uncoveredApprovedDecisions"], [])
        # Clean reprocess recorded: the zr1_options scaffold row is cleared.
        self.assertEqual(plan_a["report"]["clearedRows"].get("zr1_options"), 1)
        # Presentation rows land as adds on all five sheets.
        for sheet in ("runtime_steps", "section_presentation", "context_section_master", "order_summary_sections", "step_order_summary_map"):
            self.assertIn("add", plan_a["report"]["perSheetCounts"].get(sheet, {}), sheet)
        # No timestamps anywhere in the plan payload (determinism guard).
        import re

        payload = json.dumps(plan_a)
        self.assertIsNone(re.search(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}", payload))

    def test_relationship_and_exclusive_ops(self) -> None:
        extra = [
            {
                "model": "zr1",
                "lane": "relationship",
                "groupKey": "pdb-excludes-c2z",
                "action": "create_relationship_candidate",
                "payload": {"kind": "not_available_with", "sourceRpo": "PDB", "targetRpos": ["C2Z"]},
                "resolution": "approved_for_plan",
            },
            {
                "model": "zr1",
                "lane": "exclusive_group",
                "groupKey": "zr1-wheel-pack",
                "action": "create_exclusive_group",
                "payload": {"members": ["PDB", "C2Z"]},
                "resolution": "approved_for_plan",
            },
        ]
        self.complete_all(zr1_extra=extra)
        plan = build_plan(**self.plan_inputs())
        self.assertTrue(plan["valid"])
        items = plan["stage2"]["items"]
        rule = next(i for i in items if i["sheet"] == "zr1_rule_mapping" and i["action"] == "add")
        self.assertEqual(rule["row"]["rule_type"], "excludes")
        group = next(i for i in items if i["sheet"] == "zr1_exclusive_groups" and i["action"] == "add")
        self.assertEqual(group["row"]["group_id"], "excl_zr1wheelpack")
        members = [i for i in items if i["sheet"] == "zr1_exclusive_members" and i["action"] == "add"]
        self.assertEqual(len(members), 2)

    def test_standard_equipment_inclusion_becomes_standard_option(self) -> None:
        se_queue = self.store.review_queue(self.run_id, "zr1", "standard_equipment")
        extra = [
            {
                "model": "zr1",
                "lane": "standard_equipment",
                "candidateId": candidate["candidateId"],
                "action": "include_standard_equipment",
                "payload": {},
                "resolution": "approved_for_plan",
            }
            for candidate in se_queue["candidates"][:1]
        ]
        self.complete_all(zr1_extra=extra)
        plan = build_plan(**self.plan_inputs())
        adds = [i for i in plan["stage2"]["items"] if i["sheet"] == "zr1_options" and i["action"] == "add"]
        se_rows = [i for i in adds if i["row"].get("selectable") is False]
        self.assertEqual(len(se_rows), len(extra))

    def test_store_flow_build_approve_and_invalidation(self) -> None:
        self.complete_all()
        before = self.master.read_bytes()
        result = self.store.build_apply_plan(self.run_id, schema_validation=False)
        self.assertTrue(result["dryRun"]["ok"], result["dryRun"])
        self.assertEqual(result["session"]["state"], "plan_built")
        self.assertEqual(self.master.read_bytes(), before)
        run_dir = self.store.run_dir(self.run_id)
        self.assertTrue((run_dir / "apply-plan.md").is_file())

        approved = self.store.approve_plan(self.run_id, "sean")
        self.assertEqual(approved["session"]["state"], "plan_approved")
        self.assertTrue((run_dir / "plan-approval.json").is_file())

        # A new decision reopens the run and invalidates the plan.
        candidate = self.store.review_queue(self.run_id, "zr1", "section")["candidates"][0]
        saved = self.store.save_decisions(
            self.run_id,
            [
                {
                    "model": "zr1",
                    "lane": "section",
                    "candidateId": candidate["candidateId"],
                    "action": "assign_section",
                    "payload": {"sectionId": "sec_pain_001"},
                    "resolution": "approved_for_plan",
                }
            ],
        )
        self.assertEqual(saved["session"]["state"], "decisions_in_progress")
        with self.assertRaises(WizardError):
            self.store.approve_plan(self.run_id, "sean")

    def test_workbook_change_blocks_approval(self) -> None:
        self.complete_all()
        self.store.build_apply_plan(self.run_id, schema_validation=False)
        # Any workbook change after the build — even mtime-preserving — must
        # fail the approval closed (sha256 compared, not just mtime).
        import os

        stat = self.master.stat()
        data = self.master.read_bytes()
        self.master.write_bytes(data + b"\x00")
        os.utime(self.master, ns=(stat.st_atime_ns, stat.st_mtime_ns))
        with self.assertRaises(WizardError):
            self.store.approve_plan(self.run_id, "sean")

    def test_approval_requires_built_plan_and_name(self) -> None:
        self.complete_all()
        with self.assertRaises(WizardError):
            self.store.approve_plan(self.run_id, "sean")  # not built yet
        self.store.build_apply_plan(self.run_id, schema_validation=False)
        with self.assertRaises(WizardError):
            self.store.approve_plan(self.run_id, "")


if __name__ == "__main__":
    unittest.main()
