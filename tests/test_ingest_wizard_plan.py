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
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
for entry in (ROOT / "scripts", ROOT / "tests"):
    if str(entry) not in sys.path:
        sys.path.insert(0, str(entry))

from corvette_form_generator.editor_ops import extract_workbook  # noqa: E402
from corvette_form_generator.ingest.wizard.plan_builder import (  # noqa: E402
    build_manifest_plan,
    build_plan,
)
from corvette_form_generator.ingest.wizard.session import (  # noqa: E402
    WizardError,
    WizardSessionStore,
    read_json,
    write_json,
)
from ingest_wizard_fixtures import build_master_workbook, build_raw_export  # noqa: E402


class PlanFlowTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self._schema_patch = patch(
            "corvette_form_generator.editor_ops.validate_workbook_schema",
            return_value=[],
        )
        self._schema_patch.start()
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
        self._schema_patch.stop()
        self._tmp.cleanup()

    def complete_model(
        self,
        model: str,
        *,
        extra: list[dict] | None = None,
        skip_section_ids: set[str] | None = None,
    ) -> None:
        queue = self.store.review_queue(self.run_id, model, "section")
        decisions = []
        skip_section_ids = skip_section_ids or set()
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
            if candidate["candidateId"] in skip_section_ids:
                continue
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
        for candidate in self.store.review_queue(self.run_id, model, "price")["candidates"]:
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
        self.assertEqual(plan_a["schemaVersion"], "pass-c-2")
        self.assertEqual(json.dumps(plan_a, sort_keys=True), json.dumps(plan_b, sort_keys=True))
        self.assertTrue(plan_a["valid"], plan_a["report"]["blockingGaps"])
        self.assertEqual(plan_a["coverage"]["uncoveredApprovedDecisions"], [])
        # Clean reprocess recorded: the zr1_options scaffold row is cleared.
        self.assertEqual(plan_a["report"]["clearedRows"].get("zr1_options"), 1)
        # Presentation rows land as adds on all five sheets.
        for sheet in ("runtime_steps", "section_presentation", "context_section_master", "order_summary_sections", "step_order_summary_map"):
            self.assertIn("add", plan_a["report"]["perSheetCounts"].get(sheet, {}), sheet)
            self.assertIn("add", plan_a["report"]["perSheetActionCounts"].get(sheet, {}), sheet)
        # No timestamps anywhere in the plan payload (determinism guard).
        import re

        payload = json.dumps(plan_a)
        self.assertIsNone(re.search(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}", payload))

    def test_grand_sport_x_registry_key_uses_runtime_metadata_key(self) -> None:
        inputs = self.plan_inputs()
        inputs["selection"] = {**inputs["selection"], "targets": ["grand_sport_x"]}
        plan = build_plan(**inputs)
        rows = [
            item["row"]
            for item in plan["stage1"]["items"]
            if item.get("sheet") in {"model_master", "model_registry_promotion"}
        ]

        self.assertTrue(rows)
        self.assertTrue(all(row["registry_key"] == "grand_sport_x" for row in rows))

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

    def test_relationship_and_exclusive_ops_dry_run_against_live_like_headers(self) -> None:
        from openpyxl import load_workbook

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

        wb = load_workbook(self.master, read_only=True, data_only=True)
        try:
            rule_headers = [cell.value for cell in wb["z06_rule_mapping"][1]]
            group_headers = [cell.value for cell in wb["z06_exclusive_groups"][1]]
        finally:
            wb.close()
        self.assertNotIn("active", rule_headers)
        self.assertNotIn("group_name", group_headers)
        self.assertIn("notes", group_headers)

        result = self.store.build_apply_plan(self.run_id, schema_validation=False)
        self.assertTrue(result["dryRun"]["stage2"]["ok"], result["dryRun"]["stage2"]["errors"])
        self.assertEqual(result["session"]["state"], "plan_built")
        plan = read_json(self.store.run_dir(self.run_id) / "apply-plan.json")
        rule = next(i for i in plan["stage2"]["items"] if i["sheet"] == "zr1_rule_mapping" and i["action"] == "add")
        group = next(i for i in plan["stage2"]["items"] if i["sheet"] == "zr1_exclusive_groups" and i["action"] == "add")
        self.assertNotIn("active", rule["row"])
        self.assertNotIn("group_name", group["row"])
        self.assertEqual(group["row"]["notes"], "Review group: zr1-wheel-pack")

    def test_default_selection_rule_emits_from_reviewed_exclusive_payload(self) -> None:
        extra = [
            {
                "model": "zr1",
                "lane": "exclusive_group",
                "groupKey": "zr1-wheel-pack",
                "action": "create_exclusive_group",
                "payload": {"members": ["PDB", "C2Z"], "defaultRpo": "PDB"},
                "resolution": "approved_for_plan",
            }
        ]
        self.complete_all(zr1_extra=extra)
        plan = build_plan(**self.plan_inputs())
        self.assertTrue(plan["valid"], plan["report"]["blockingGaps"])
        row = next(
            item["row"]
            for item in plan["stage2"]["items"]
            if item["sheet"] == "default_selection_rules" and item["action"] == "add"
        )
        self.assertEqual(row["model_key"], "zr1")
        self.assertEqual(row["target_option_id"], "opt_pdb_002")
        self.assertEqual(row["condition_type"], "always")
        self.assertEqual(row["display_behavior"], "default_selected")

    def test_required_default_selection_without_default_blocks_plan(self) -> None:
        extra = [
            {
                "model": "zr1",
                "lane": "exclusive_group",
                "groupKey": "zr1-wheel-pack",
                "action": "create_exclusive_group",
                "payload": {"members": ["PDB", "C2Z"], "requiresDefaultSelection": True},
                "resolution": "approved_for_plan",
            }
        ]
        self.complete_all(zr1_extra=extra)
        plan = build_plan(**self.plan_inputs())
        self.assertFalse(plan["valid"])
        self.assertIn("default_selection_rules_missing", {gap["kind"] for gap in plan["report"]["blockingGaps"]})

    def test_relationship_resolves_against_retained_existing_option_rows(self) -> None:
        from openpyxl import load_workbook

        wb = load_workbook(self.master)
        wb["zr1_options"].append(["opt_tyz_001", "TYZ", "", "Existing target", "", "", "sec_whee_001", "", 30, True, ""])
        wb.save(self.master)
        wb.close()
        extra = [
            {
                "model": "zr1",
                "lane": "relationship",
                "groupKey": "pdb-excludes-tyz",
                "action": "create_relationship_candidate",
                "payload": {"kind": "not_available_with", "sourceRpo": "PDB", "targetRpos": ["TYZ"]},
                "resolution": "approved_for_plan",
            }
        ]
        self.complete_all(zr1_extra=extra)
        plan = build_plan(**self.plan_inputs())
        self.assertTrue(plan["valid"], plan["report"]["blockingGaps"])
        deletes = [
            item
            for item in plan["stage2"]["items"]
            if item["sheet"] == "zr1_options" and item["action"] == "delete" and item["key"].get("option_id") == "opt_tyz_001"
        ]
        self.assertEqual(deletes, [])
        rule = next(item for item in plan["stage2"]["items"] if item["sheet"] == "zr1_rule_mapping" and item["action"] == "add")
        self.assertEqual(rule["row"]["target_id"], "opt_tyz_001")

    def test_model_interior_scope_uses_existing_row_strategy(self) -> None:
        self.complete_all()
        plan = build_plan(**self.plan_inputs())
        scope_ops = [item for item in plan["stage2"]["items"] if item["sheet"] == "model_interior_scope"]
        self.assertFalse(
            any(item["key"] == {"model_key": "zr1", "interior_id": "1LZ_AQ9_HTA", "trim_level": "1LZ"} for item in scope_ops)
        )
        self.assertTrue(
            any(
                item["action"] == "add"
                and item["key"] == {"model_key": "zr1", "interior_id": "3LZ_AQ9_HTA", "trim_level": "3LZ"}
                for item in scope_ops
            )
        )
        self.assertTrue(
            any(
                item["action"] == "add"
                and item["key"] == {"model_key": "zr1x", "interior_id": "1LZ_AQ9_HTA", "trim_level": "1LZ"}
                for item in scope_ops
            )
        )

    def test_legacy_standard_equipment_inclusion_becomes_standard_option(self) -> None:
        se_queue = self.store.review_queue(self.run_id, "zr1", "standard_equipment")
        target = se_queue["candidates"][0]
        extra = [
            {
                "model": "zr1",
                "lane": "standard_equipment",
                "candidateId": target["candidateId"],
                "action": "include_standard_equipment",
                "payload": {},
                "resolution": "approved_for_plan",
            }
        ]
        self.complete_model("zr1", extra=extra, skip_section_ids={target["candidateId"]})
        self.complete_model("zr1x")
        plan = build_plan(**self.plan_inputs())
        self.assertTrue(plan["valid"], plan["report"]["blockingGaps"] or plan["coverage"]["uncoveredApprovedDecisions"])
        adds = [i for i in plan["stage2"]["items"] if i["sheet"] == "zr1_options" and i["action"] == "add"]
        se_row = next(i["row"] for i in adds if i["row"]["rpo"] == target["refOnlyRpo"])
        self.assertIs(se_row["selectable"], False)
        self.assertIsNone(se_row["section_id"])

    def test_ref_only_section_assignment_becomes_sectioned_option(self) -> None:
        self.complete_all()
        target = next(
            candidate
            for candidate in self.store.review_queue(self.run_id, "zr1", "section")["candidates"]
            if candidate["refOnlyRpo"] == "XFR"
        )
        self.store.save_decisions(
            self.run_id,
            [
                {
                    "model": "zr1",
                    "lane": "section",
                    "candidateId": target["candidateId"],
                    "action": "assign_section",
                    "payload": {"sectionId": "sec_pain_001", "selectable": False},
                    "resolution": "approved_for_plan",
                }
            ],
        )
        plan = build_plan(**self.plan_inputs())
        self.assertTrue(plan["valid"], plan["report"]["blockingGaps"] or plan["coverage"]["uncoveredApprovedDecisions"])
        row = next(
            i["row"]
            for i in plan["stage2"]["items"]
            if i["sheet"] == "zr1_options" and i["action"] == "add" and i["row"]["rpo"] == "XFR"
        )
        self.assertIsNone(row["price"])
        self.assertEqual(row["section_id"], "sec_pain_001")
        self.assertIs(row["selectable"], False)
        ovs_rows = [
            i["row"]
            for i in plan["stage2"]["items"]
            if i["sheet"] == "zr1_ovs" and i["action"] == "add" and i["row"]["option_id"] == row["option_id"]
        ]
        self.assertEqual(
            {ovs["variant_id"]: ovs["status"] for ovs in ovs_rows},
            {"1lz_r07": "available", "3lz_r67": "unavailable"},
        )

    def test_skipped_row_stays_out_of_plan_and_plan_stays_valid(self) -> None:
        # Full review first, then the reviewer flips one row to Skip: the row
        # must produce no ops and not strand its already-approved price
        # decision as "uncovered".
        self.complete_all()
        skipped = self.store.review_queue(self.run_id, "zr1", "section")["candidates"][0]
        self.store.save_decisions(
            self.run_id,
            [
                {
                    "model": "zr1",
                    "lane": "section",
                    "candidateId": skipped["candidateId"],
                    "action": "exclude_row",
                    "payload": {},
                    "resolution": "not_needed",
                }
            ],
        )
        plan = build_plan(**self.plan_inputs())
        self.assertTrue(plan["valid"], plan["report"]["blockingGaps"] or plan["coverage"]["uncoveredApprovedDecisions"])
        self.assertEqual(plan["coverage"]["uncoveredApprovedDecisions"], [])
        zr1_adds = [
            i["row"]["rpo"]
            for i in plan["stage2"]["items"]
            if i["sheet"] == "zr1_options" and i["action"] == "add"
        ]
        self.assertNotIn(skipped["rpo"], zr1_adds)

    def test_selectable_and_active_flags_flow_into_option_rows(self) -> None:
        self.complete_all()
        target = self.store.review_queue(self.run_id, "zr1", "section")["candidates"][0]
        self.store.save_decisions(
            self.run_id,
            [
                {
                    "model": "zr1",
                    "lane": "section",
                    "candidateId": target["candidateId"],
                    "action": "assign_section",
                    "payload": {"sectionId": "sec_whee_001", "selectable": False, "active": False},
                    "resolution": "approved_for_plan",
                }
            ],
        )
        plan = build_plan(**self.plan_inputs())
        row = next(
            i["row"]
            for i in plan["stage2"]["items"]
            if i["sheet"] == "zr1_options" and i["action"] == "add" and i["row"]["rpo"] == target["rpo"]
        )
        self.assertIs(row["selectable"], False)
        self.assertIs(row["active"], False)

    def test_unresolvable_variants_block_the_plan(self) -> None:
        self.complete_all()
        # Same decisions against a workbook with no variant rows at all: the
        # plan must fail closed instead of writing options without OVS rows.
        import shutil

        from openpyxl import load_workbook

        crippled = self.root / "master-no-variants.xlsx"
        shutil.copy2(self.master, crippled)
        wb = load_workbook(crippled)
        for sheet in ("model_variants", "variant_master"):
            ws = wb[sheet]
            if ws.max_row > 1:
                ws.delete_rows(2, ws.max_row - 1)
        wb.save(crippled)
        plan = build_plan(**{**self.plan_inputs(), "workbook_path": crippled})
        self.assertFalse(plan["valid"])
        self.assertIn("no_variants_mapped", {g["kind"] for g in plan["report"]["blockingGaps"]})

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
        self.assertEqual(approved["session"]["state"], "dry_run_approved")
        self.assertTrue((run_dir / "plan-approval.json").is_file())
        approval = read_json(run_dir / "plan-approval.json")
        plan = read_json(run_dir / "apply-plan.json")
        session = read_json(run_dir / "session.json")
        self.assertEqual(approval["schemaVersion"], "plan-approval-2")
        self.assertEqual(approval["scope"], "dry_run_evidence")
        self.assertEqual(approval["runId"], self.run_id)
        self.assertEqual(approval["targets"], ["zr1", "zr1x"])
        self.assertEqual(approval["planSchemaVersion"], "pass-c-2")
        self.assertEqual(
            approval["planSha"],
            __import__("hashlib").sha256((run_dir / "apply-plan.json").read_bytes()).hexdigest(),
        )
        self.assertEqual(approval["workbookFingerprint"], plan["workbookFingerprint"])
        self.assertEqual(approval["sourceFingerprint"], session["fingerprint"])
        self.assertEqual(approval["candidatesFingerprint"], plan["candidatesFingerprint"])
        self.assertEqual(approval["decisionsFingerprint"], plan["decisionsFingerprint"])
        self.assertEqual(
            approval["modelSelectionSha"],
            __import__("hashlib").sha256((run_dir / "model-selection.json").read_bytes()).hexdigest(),
        )
        for unavailable in ("canonicalManifestSha", "compileReportSha", "exceptionResolutionsSha"):
            self.assertNotIn(unavailable, approval)

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

    def test_compiled_ready_builds_atomic_pass_c3_plan_without_legacy_decisions(self) -> None:
        run_dir = self.store.run_dir(self.run_id)
        session = read_json(run_dir / "session.json")
        session["state"] = "compiled_ready"
        write_json(run_dir / "session.json", session)
        extract = extract_workbook(self.master)
        zr1 = next(
            row
            for row in extract["sheets"]["model_master"]["rows"]
            if row["model_key"] == "zr1"
        )
        zr1x = {**zr1, "model_key": "zr1x", "registry_key": "zr1x", "model_label": "ZR1X"}
        rows = [
            CanonicalPlanProjectionTest._manifest_row(
                model="zr1",
                family="model_master",
                sheet="model_master",
                action="noop",
                key={"model_key": "zr1"},
                values=zr1,
            ),
            CanonicalPlanProjectionTest._manifest_row(
                model="zr1x",
                family="model_master",
                sheet="model_master",
                action="add",
                key={"model_key": "zr1x"},
                values=zr1x,
            ),
        ]
        authority = {
            "fingerprint": "fixture-authority",
            "bindings": {"compilerPolicyVersion": "fixture"},
        }
        manifest = {
            "schemaVersion": "canonical-row-manifest-v1",
            "manifestSemanticSha": "fixture-manifest-semantic",
            "runAuthorityFingerprint": authority,
            "modelModes": {"zr1": "reprocess", "zr1x": "reprocess"},
            "rows": rows,
        }
        report = {
            "runAuthorityFingerprint": authority,
            "queueSubjectFingerprint": "fixture-queue",
            "comparatorEvidenceSemanticSha": "fixture-comparator",
            "models": {
                model: {"mode": "reprocess", "compileReady": True, "blockers": []}
                for model in ("zr1", "zr1x")
            },
            "deferrals": [],
            "sourceFeatureCoverage": [],
        }
        queue = {
            "queueSubjectFingerprint": "fixture-queue",
            "comparatorEvidenceSemanticSha": "fixture-comparator",
            "runAuthorityFingerprint": authority,
            "subjects": [],
        }
        resolutions = {
            "queueSubjectFingerprint": "fixture-queue",
            "validEntries": [],
        }
        comparator = {
            "comparatorEvidenceSemanticSha": "fixture-comparator",
            "runAuthorityFingerprint": authority,
            "targets": {"zr1": {}, "zr1x": {}},
        }
        detail = {
            "manifest": manifest,
            "compileReport": report,
            "exceptionQueue": queue,
            "resolutions": resolutions,
        }
        for name, payload in {
            "canonical-row-manifest.json": manifest,
            "compile-report.json": report,
            "exception-resolutions.json": resolutions,
            "exception-queue.json": queue,
            "comparator-evidence.json": comparator,
        }.items():
            write_json(run_dir / name, payload)
        before = self.master.read_bytes()

        with patch.object(self.store, "compiler_detail", return_value=detail), patch.object(
            self.store,
            "_compiler_freshness",
            return_value={"stale": False, "reasons": []},
        ):
            result = self.store.build_apply_plan(self.run_id, schema_validation=False)
            rebuilt = self.store.build_apply_plan(self.run_id, schema_validation=False)

        self.assertEqual(result["session"]["state"], "plan_built")
        self.assertEqual(result["plan"]["schemaVersion"], "pass-c-3")
        self.assertEqual(rebuilt["plan"]["schemaVersion"], "pass-c-3")
        self.assertTrue(result["plan"]["planReadiness"]["planReady"])
        self.assertEqual(result["dryRun"]["mode"], "atomic_manifest_projection")
        self.assertTrue(result["dryRun"]["combined"]["ok"], result["dryRun"])
        self.assertEqual(self.master.read_bytes(), before)
        plan = read_json(run_dir / "apply-plan.json")
        self.assertEqual(len(plan["coverage"]["manifestRows"]), 2)
        self.assertEqual(len(plan["coverage"]["noops"]), 1)
        self.assertNotEqual(plan["decisionsFingerprint"], read_json(run_dir / "decisions.json"))

    def test_pass_c3_plan_approval_requires_all_compiler_artifacts(self) -> None:
        self.complete_all()
        self.store.build_apply_plan(self.run_id, schema_validation=False)
        run_dir = self.store.run_dir(self.run_id)
        plan = read_json(run_dir / "apply-plan.json")
        plan["schemaVersion"] = "pass-c-3"
        write_json(run_dir / "apply-plan.json", plan)

        with self.assertRaisesRegex(WizardError, "canonical-row-manifest.json"):
            self.store.approve_plan(self.run_id, "sean")

        self.assertFalse((run_dir / "plan-approval.json").exists())


class CanonicalPlanProjectionTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.master = build_master_workbook(self.root / "master.xlsx")
        self.extract = extract_workbook(self.master)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _build(
        self,
        *,
        rows: list[dict],
        targets: list[str],
        modes: dict[str, str],
        comparator_targets: list[str] | None = None,
    ) -> dict:
        authority = {
            "fingerprint": "authority-sha",
            "bindings": {"compilerPolicyVersion": "fixture"},
        }
        return build_manifest_plan(
            workbook_path=self.master,
            manifest={
                "schemaVersion": "canonical-row-manifest-v1",
                "manifestSemanticSha": "manifest-semantic-sha",
                "runAuthorityFingerprint": authority,
                "modelModes": modes,
                "rows": rows,
            },
            compile_report={
                "models": {
                    target: {
                        "mode": modes[target],
                        "compileReady": True,
                        "blockers": [],
                    }
                    for target in targets
                },
                "deferrals": [],
                "runAuthorityFingerprint": authority,
                "queueSubjectFingerprint": "queue-sha",
                "comparatorEvidenceSemanticSha": "comparator-semantic-sha",
            },
            selection={
                "targets": targets,
                "comparators": {target: "z06" for target in targets},
                "sourceFingerprint": "source-sha",
                "candidatesFingerprint": "candidate-sha",
            },
            compiler_bindings={
                "canonicalManifestSha": "manifest-file-sha",
                "compileReportSha": "report-file-sha",
                "exceptionResolutionsSha": "resolution-file-sha",
                "exceptionQueueSha": "queue-file-sha",
                "comparatorEvidenceSha": "comparator-file-sha",
            },
            authority_artifacts={
                "exceptionQueue": {
                    "queueSubjectFingerprint": "queue-sha",
                    "comparatorEvidenceSemanticSha": "comparator-semantic-sha",
                    "runAuthorityFingerprint": authority,
                    "subjects": [],
                },
                "resolutions": {
                    "queueSubjectFingerprint": "queue-sha",
                    "validEntries": [],
                },
                "comparatorEvidence": {
                    "comparatorEvidenceSemanticSha": "comparator-semantic-sha",
                    "runAuthorityFingerprint": authority,
                    "targets": {
                        target: {} for target in (comparator_targets or targets)
                    },
                },
            },
        )

    @staticmethod
    def _manifest_row(
        *,
        model: str,
        family: str,
        sheet: str,
        action: str,
        key: dict,
        values: dict,
        status: str = "ready",
    ) -> dict:
        return {
            "model": model,
            "family": family,
            "sheet": sheet,
            "action": action,
            "key": key,
            "values": values,
            "status": status,
            "semanticSignature": {"fixture": [sheet, key]},
            "derivationVersion": "fixture",
        }

    def test_manifest_plan_projects_exact_mutations_and_explicit_noop_coverage(self) -> None:
        model_row = next(
            row
            for row in self.extract["sheets"]["model_master"]["rows"]
            if row["model_key"] == "zr1"
        )
        existing = self.extract["sheets"]["zr1_options"]["rows"][0]
        updated = {**existing, "description": "Canonical updated description"}
        headers = self.extract["sheets"]["zr1_options"]["headers"]
        added = {header: None for header in headers}
        added.update(
            {
                "option_id": "opt_fixture_new_001",
                "rpo": "NEW",
                "price": 100,
                "option_name": "Fixture option",
                "description": "Fixture option",
                "section_id": "sec_whee_001",
                "selectable": True,
                "active": True,
            }
        )
        rows = [
            self._manifest_row(
                model="zr1",
                family="model_master",
                sheet="model_master",
                action="noop",
                key={"model_key": "zr1"},
                values=model_row,
            ),
            self._manifest_row(
                model="zr1",
                family="options",
                sheet="zr1_options",
                action="update",
                key={"option_id": existing["option_id"]},
                values=updated,
            ),
            self._manifest_row(
                model="zr1",
                family="options",
                sheet="zr1_options",
                action="add",
                key={"option_id": added["option_id"]},
                values=added,
            ),
        ]

        first = self._build(rows=rows, targets=["zr1"], modes={"zr1": "reprocess"})
        second = self._build(rows=rows, targets=["zr1"], modes={"zr1": "reprocess"})

        self.assertEqual(first, second)
        self.assertTrue(first["valid"])
        self.assertTrue(first["planReadiness"]["planReady"])
        self.assertEqual(len(first["coverage"]["manifestRows"]), 3)
        self.assertEqual(len(first["coverage"]["noops"]), 1)
        self.assertEqual(len(first["stage2"]["items"]), 2)
        update = next(item for item in first["stage2"]["items"] if item["action"] == "update")
        self.assertNotIn("option_id", update["row"])
        self.assertEqual(update["row"]["description"], "Canonical updated description")

    def test_manifest_plan_refuses_comparator_evidence_target_drift(self) -> None:
        with self.assertRaisesRegex(ValueError, "comparator evidence target"):
            self._build(
                rows=[
                    self._manifest_row(
                        model="zr1",
                        family="model_master",
                        sheet="model_master",
                        action="noop",
                        key={"model_key": "zr1"},
                        values={"model_key": "zr1", "active": False},
                    )
                ],
                targets=["zr1"],
                modes={"zr1": "reprocess"},
                comparator_targets=["zr1x"],
            )

    def test_manifest_noop_with_text_booleans_projects_typed_normalization(self) -> None:
        from openpyxl import load_workbook

        wb = load_workbook(self.master)
        ws = wb["zr1_options"]
        headers = {
            str(cell.value): index + 1
            for index, cell in enumerate(ws[1])
            if cell.value is not None
        }
        ws.cell(row=2, column=headers["selectable"], value="False")
        ws.cell(row=2, column=headers["active"], value="True")
        ws.cell(row=2, column=headers["price"], value="0")
        wb.save(self.master)
        wb.close()

        row = extract_workbook(self.master)["sheets"]["zr1_options"]["rows"][0]
        values = {**row, "selectable": False, "active": True, "price": 0}
        plan = self._build(
            rows=[
                self._manifest_row(
                    model="zr1",
                    family="options",
                    sheet="zr1_options",
                    action="noop",
                    key={"option_id": row["option_id"]},
                    values=values,
                )
            ],
            targets=["zr1"],
            modes={"zr1": "reprocess"},
        )

        operation = plan["stage2"]["items"][0]
        self.assertEqual(operation["action"], "update")
        self.assertEqual(
            operation["row"],
            {"price": 0, "selectable": False, "active": True},
        )
        receipt = plan["coverage"]["manifestRows"][0]
        self.assertEqual(receipt["action"], "noop")
        self.assertEqual(receipt["projectionPhysicalAction"], "update")
        self.assertEqual(plan["coverage"]["noops"], [])

    def test_manifest_plan_creates_missing_target_sheet_from_comparator_headers(self) -> None:
        source_headers = self.extract["sheets"]["model_workbook_sources"]["headers"]
        source_values = {header: None for header in source_headers}
        source_values.update(
            {
                "model_key": "grand_sport_x",
                "source_role": "source_option_sheet",
                "sheet_name": "grand_sport_x_options",
                "active": True,
            }
        )
        option_headers = self.extract["sheets"]["z06_options"]["headers"]
        option_values = {header: None for header in option_headers}
        option_values.update(
            {
                "option_id": "opt_fixture_001",
                "rpo": "FIX",
                "price": 0,
                "option_name": "Fixture",
                "description": "Fixture",
                "section_id": "sec_whee_001",
                "selectable": True,
                "active": True,
            }
        )
        rows = [
            self._manifest_row(
                model="grand_sport_x",
                family="model_workbook_sources",
                sheet="model_workbook_sources",
                action="add",
                key={
                    "model_key": "grand_sport_x",
                    "source_role": "source_option_sheet",
                },
                values=source_values,
            ),
            self._manifest_row(
                model="grand_sport_x",
                family="options",
                sheet="grand_sport_x_options",
                action="add",
                key={"option_id": "opt_fixture_001"},
                values=option_values,
            ),
        ]

        plan = self._build(
            rows=rows,
            targets=["grand_sport_x"],
            modes={"grand_sport_x": "greenfield"},
        )

        create = next(item for item in plan["stage1"]["items"] if item["action"] == "create_sheet")
        self.assertEqual(create["sheet"], "grand_sport_x_options")
        self.assertEqual(create["family"], "options")
        self.assertEqual(create["headersFrom"], "z06_options")

    def test_canonical_source_registration_creates_zero_row_target_sheet(self) -> None:
        source_headers = self.extract["sheets"]["model_workbook_sources"]["headers"]
        source_values: dict = {header: None for header in source_headers}
        source_values.update(
            {
                "model_key": "grand_sport_x",
                "source_role": "variant_option_overrides_sheet",
                "sheet_name": "grand_sport_x_variant_overrides",
                "active": False,
            }
        )

        plan = self._build(
            rows=[
                self._manifest_row(
                    model="grand_sport_x",
                    family="model_workbook_sources",
                    sheet="model_workbook_sources",
                    action="add",
                    key={
                        "model_key": "grand_sport_x",
                        "source_role": "variant_option_overrides_sheet",
                    },
                    values=source_values,
                )
            ],
            targets=["grand_sport_x"],
            modes={"grand_sport_x": "greenfield"},
        )

        create = next(
            item
            for item in plan["stage1"]["items"]
            if item.get("action") == "create_sheet"
            and item.get("sheet") == "grand_sport_x_variant_overrides"
        )
        self.assertEqual(create["family"], "variant_overrides")
        self.assertEqual(create["headersFrom"], "z06_variant_overrides")
        self.assertEqual(
            create["_manifestRefs"],
            [plan["coverage"]["manifestRows"][0]["manifestRef"]],
        )

    def test_greenfield_projection_migrates_reviewed_global_rules_to_isolated_sheet(self) -> None:
        source_headers = self.extract["sheets"]["model_workbook_sources"]["headers"]
        source_values = {header: None for header in source_headers}
        source_values.update(
            {
                "model_key": "grand_sport_x",
                "source_role": "price_rules_sheet",
                "sheet_name": "z06_price_rules",
                "active": False,
            }
        )
        price_row = self.extract["sheets"]["z06_price_rules"]["rows"][0]
        option_headers = self.extract["sheets"]["z06_options"]["headers"]
        option_template = self.extract["sheets"]["z06_options"]["rows"][0]
        option_rows = []
        for option_id in (
            price_row["condition_option_id"],
            price_row["target_option_id"],
        ):
            existing_option = next(
                (
                    row
                    for row in self.extract["sheets"]["z06_options"]["rows"]
                    if row["option_id"] == option_id
                ),
                None,
            )
            option_values = (
                dict(existing_option)
                if existing_option
                else {header: option_template.get(header) for header in option_headers}
            )
            option_values.update(
                {
                    "option_id": option_id,
                    "rpo": option_id.removeprefix("opt_").removesuffix("_001").upper(),
                }
            )
            option_rows.append(
                self._manifest_row(
                    model="grand_sport_x",
                    family="options",
                    sheet="z06_options",
                    action=(
                        "noop"
                        if existing_option
                        else "add"
                    ),
                    key={"option_id": option_id},
                    values=option_values,
                )
            )
        rows = [
            self._manifest_row(
                model="grand_sport_x",
                family="model_workbook_sources",
                sheet="model_workbook_sources",
                action="add",
                key={
                    "model_key": "grand_sport_x",
                    "source_role": "price_rules_sheet",
                },
                values=source_values,
            ),
            self._manifest_row(
                model="grand_sport_x",
                family="model_workbook_sources",
                sheet="model_workbook_sources",
                action="add",
                key={
                    "model_key": "grand_sport_x",
                    "source_role": "variant_option_overrides_sheet",
                },
                values={
                    **source_values,
                    "source_role": "variant_option_overrides_sheet",
                    "sheet_name": "z06_variant_overrides",
                },
            ),
            self._manifest_row(
                model="grand_sport_x",
                family="price_rules",
                sheet="z06_price_rules",
                action="noop",
                key={"price_rule_id": price_row["price_rule_id"]},
                values=price_row,
            ),
            *option_rows,
        ]

        plan = self._build(
            rows=rows,
            targets=["grand_sport_x"],
            modes={"grand_sport_x": "greenfield"},
        )

        create = next(
            item
            for item in plan["stage1"]["items"]
            if item.get("sheet") == "grand_sport_x_price_rules"
        )
        self.assertEqual(create["sheet"], "grand_sport_x_price_rules")
        migrated = next(
            item
            for item in plan["stage2"]["items"]
            if item.get("sheet") == "grand_sport_x_price_rules"
        )
        self.assertEqual(migrated["action"], "add")
        self.assertEqual(migrated["sheet"], "grand_sport_x_price_rules")
        source = next(
            item
            for item in plan["stage1"]["items"]
            if item.get("sheet") == "model_workbook_sources"
        )
        self.assertEqual(source["row"]["sheet_name"], "grand_sport_x_price_rules")
        self.assertEqual(plan["projectionMigrations"]["rowCount"], 5)
        variant_create = next(
            item
            for item in plan["stage1"]["items"]
            if item.get("action") == "create_sheet"
            and item.get("sheet") == "grand_sport_x_variant_overrides"
        )
        self.assertEqual(variant_create["headersFrom"], "z06_variant_overrides")
        promotion = next(
            item
            for item in plan["stage1"]["items"]
            if item.get("sheet") == "model_registry_promotion"
            and item.get("key", {}).get("model_key") == "grand_sport_x"
        )
        self.assertEqual(promotion["action"], "add")
        self.assertFalse(promotion["row"]["active"])
        self.assertFalse(promotion["row"]["promoted_to_runtime"])
        self.assertEqual(
            promotion["_scaffoldRule"],
            "pass_c3_greenfield_registry_promotion",
        )

    def test_manifest_plan_refuses_target_rows_routed_to_comparator_sheet(self) -> None:
        option = self.extract["sheets"]["z06_options"]["rows"][0]
        row = self._manifest_row(
            model="zr1",
            family="options",
            sheet="z06_options",
            action="noop",
            key={"option_id": option["option_id"]},
            values=option,
        )

        with self.assertRaisesRegex(ValueError, "model_workbook_sources requires"):
            self._build(rows=[row], targets=["zr1"], modes={"zr1": "reprocess"})

    def test_manifest_plan_refuses_non_ready_or_unknown_columns(self) -> None:
        existing = self.extract["sheets"]["zr1_options"]["rows"][0]
        row = self._manifest_row(
            model="zr1",
            family="options",
            sheet="zr1_options",
            action="noop",
            key={"option_id": existing["option_id"]},
            values=existing,
            status="blocked",
        )
        with self.assertRaisesRegex(ValueError, "not ready"):
            self._build(rows=[row], targets=["zr1"], modes={"zr1": "reprocess"})

        row["status"] = "ready"
        row["values"] = {**existing, "invented_column": "not canonical"}
        with self.assertRaisesRegex(ValueError, "header"):
            self._build(rows=[row], targets=["zr1"], modes={"zr1": "reprocess"})


if __name__ == "__main__":
    unittest.main()
