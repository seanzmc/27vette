#!/usr/bin/env python3
"""Pass D apply CLI/store tests.

Fixture workbooks only. The live workbook is never written here; compact
fixture workbooks disable schema validation because they are not schema-complete.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
for entry in (ROOT / "scripts", ROOT / "tests"):
    if str(entry) not in sys.path:
        sys.path.insert(0, str(entry))

from corvette_form_generator.ingest.wizard.session import (  # noqa: E402
    WizardError,
    WizardSessionStore,
    read_json,
    write_json,
)
from ingest_wizard_fixtures import build_master_workbook, build_raw_export  # noqa: E402


class ApplyFlowTest(unittest.TestCase):
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

    def complete_model(self, model: str) -> None:
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
        for candidate in self.store.review_queue(self.run_id, model, "section")["candidates"]:
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
            decisions.append(
                {
                    "model": model,
                    "lane": "price",
                    "candidateId": candidate["candidateId"],
                    "action": "accept_exact_price" if candidate["priceMatch"] == "exact" else "confirm_no_price",
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
        self.store.save_decisions(self.run_id, decisions)

    def approve_plan(self) -> Path:
        self.complete_model("zr1")
        self.complete_model("zr1x")
        self.store.mark_complete(self.run_id)
        result = self.store.build_apply_plan(self.run_id, schema_validation=False)
        self.assertTrue(result["dryRun"]["ok"], result["dryRun"])
        self.store.approve_plan(self.run_id, "sean")
        return self.store.run_dir(self.run_id)

    def future_write_authority(self, *, approve: bool = True) -> tuple[Path, dict]:
        """Build stored pass-c-3-shaped proof without invoking a live write."""

        run_dir = self.approve_plan()
        self.store.apply_approved_plan(self.run_id, schema_validation=False)
        plan = read_json(run_dir / "apply-plan.json")
        for filename, payload, field in (
            ("canonical-row-manifest.json", {"schemaVersion": "canonical-rows-1"}, "canonicalManifestSha"),
            ("compile-report.json", {"schemaVersion": "compile-report-1"}, "compileReportSha"),
            ("exception-resolutions.json", {"schemaVersion": "exception-resolutions-1"}, "exceptionResolutionsSha"),
        ):
            write_json(run_dir / filename, payload)
            plan[field] = hashlib.sha256((run_dir / filename).read_bytes()).hexdigest()
        plan["schemaVersion"] = "pass-c-3"
        write_json(run_dir / "apply-plan.json", plan)
        session = read_json(run_dir / "session.json")
        session["state"] = "plan_built"
        write_json(run_dir / "session.json", session)
        scoped = self.store.approve_plan(self.run_id, "sean")["approval"]

        report = read_json(run_dir / "apply-dry-run-report.json")
        targets = list(plan["targets"])
        empty_warning_fingerprint = hashlib.sha256(b"[]").hexdigest()
        report.update(
            {
                "schemaVersion": "pass-d-2",
                "planSchemaVersion": "pass-c-3",
                "planSupersededForWrite": False,
                "planSha": hashlib.sha256((run_dir / "apply-plan.json").read_bytes()).hexdigest(),
                "approval": scoped,
                "approvedBy": scoped["approvedBy"],
                "approvedAt": scoped["approvedAt"],
                "status": "validated_write_eligible",
                "ok": True,
                "write": False,
                "schemaValidationEnabled": True,
                "schemaResult": {"error_count": 0},
                "liveWriteBlockedReason": None,
                "warnings": [],
                "warningPolicy": {
                    "confirmableIds": [],
                    "blockingIds": [],
                    "unknownIds": [],
                    "fingerprint": empty_warning_fingerprint,
                },
                "writeEligibility": {
                    "eligible": True,
                    "blockers": [],
                    "deferrals": [],
                    "targets": {
                        model: {"eligible": True, "blockers": [], "deferrals": []}
                        for model in targets
                    },
                    "acceptedWarningIds": [],
                    "warningFingerprint": empty_warning_fingerprint,
                },
                "deploymentContinuity": {
                    model: {
                        "status": "deployment_probe_passed",
                        "deploymentBlockers": [],
                        "deploymentDeferrals": [],
                    }
                    for model in targets
                },
            }
        )
        report["applyResult"] = {
            **report["applyResult"],
            "ok": True,
            "status": "validated",
            "errors": [],
            "warnings": [],
            "warningPolicy": report["warningPolicy"],
        }
        write_json(run_dir / "apply-dry-run-report.json", report)
        session = read_json(run_dir / "session.json")
        session["state"] = "dry_run_validated_write_eligible"
        write_json(run_dir / "session.json", session)
        if approve:
            self.store.approve_write(self.run_id, "sean")
        return run_dir, report

    def assert_refusal_preserves_evidence(self, run_dir: Path, action) -> None:
        before_workbook = self.master.read_bytes()
        before_report = (run_dir / "apply-dry-run-report.json").read_bytes()
        backup_dir = self.master.parent / "backups"
        before_backups = (
            sorted(path.name for path in backup_dir.glob("*") if path.is_file())
            if backup_dir.is_dir()
            else []
        )

        action()

        self.assertEqual(self.master.read_bytes(), before_workbook)
        self.assertEqual((run_dir / "apply-dry-run-report.json").read_bytes(), before_report)
        self.assertFalse((run_dir / "apply-report.json").exists())
        self.assertFalse((run_dir / "apply-workbook-edit-log.jsonl").exists())
        after_backups = (
            sorted(path.name for path in backup_dir.glob("*") if path.is_file())
            if backup_dir.is_dir()
            else []
        )
        self.assertEqual(after_backups, before_backups)

    def test_default_dry_run_writes_report_and_leaves_workbook_unchanged(self) -> None:
        run_dir = self.approve_plan()
        before = self.master.read_bytes()

        result = self.store.apply_approved_plan(self.run_id, schema_validation=False)

        self.assertTrue(result["ok"], result)
        self.assertEqual(result["status"], "validated_write_blocked")
        self.assertEqual(self.master.read_bytes(), before)
        report = read_json(run_dir / "apply-dry-run-report.json")
        plan = read_json(run_dir / "apply-plan.json")
        self.assertEqual(report["schemaVersion"], "pass-d-2")
        self.assertEqual(report["planSchemaVersion"], "pass-c-2")
        self.assertIn("startedAt", report)
        self.assertIn("completedAt", report)
        self.assertEqual(report["approvedBy"], "sean")
        self.assertIn("approvedAt", report)
        self.assertFalse(report["write"])
        self.assertTrue(report["ok"])
        self.assertEqual(report["status"], "validated_write_blocked")
        self.assertFalse(report["writeEligibility"]["eligible"])
        self.assertTrue(report["liveWriteBlockedReason"])
        blocker_kinds = {item["kind"] for item in report["writeEligibility"]["blockers"]}
        self.assertIn("plan_schema_not_writable", blocker_kinds)
        self.assertIn("blank_option_semantics", blocker_kinds)
        self.assertFalse(report["writeEligibility"]["targets"]["zr1"]["eligible"])
        self.assertFalse(report["writeEligibility"]["targets"]["zr1x"]["eligible"])
        self.assertGreater(report["opCounts"]["stage1"], 0)
        self.assertGreater(report["opCounts"]["stage2"], 0)
        self.assertEqual(
            report["opCounts"]["combinedRaw"],
            len(plan["stage1"]["items"]) + len(plan["stage2"]["items"]),
        )
        self.assertEqual(report["opCounts"]["prepared"], report["applyResult"]["opCount"])
        self.assertGreater(report["perSheetCounts"].get("model_workbook_sources", 0), 0)
        self.assertGreater(report["perSheetActionCounts"]["model_workbook_sources"]["add"], 0)
        self.assertEqual(report["boolHygieneResult"]["error_count"], 0)
        self.assertEqual(report["deploymentContinuity"]["zr1"]["status"], "not_deployment_ready")
        self.assertIn("registryLoadable", report["deploymentContinuity"]["zr1"])
        self.assertIn("registryError", report["deploymentContinuity"]["zr1"])
        self.assertIn(
            "price_rules_required_for_runtime",
            {item["kind"] for item in report["deploymentContinuity"]["zr1"]["deploymentBlockers"]},
        )
        self.assertEqual(
            report["deploymentContinuity"]["zr1"]["sourceCoverage"]["priceRuleAddOrUpdateCount"],
            0,
        )
        self.assertEqual(report["applyResult"]["status"], "validated")
        self.assertEqual(report["workbookBefore"], report["workbookAfter"])
        self.assertIsNone(report["backupPath"])
        self.assertTrue(report["verification"]["ok"])
        self.assertEqual(
            report["verification"]["preparedChecked"],
            report["operationCoverage"]["preparedCount"],
        )
        self.assertEqual(
            report["operationCoverage"]["rawCovered"],
            report["operationCoverage"]["rawCount"],
        )
        self.assertEqual(read_json(run_dir / "session.json")["state"], "dry_run_validated_write_blocked")
        self.assertFalse((run_dir / "write-approval.json").exists())
        self.assertFalse((run_dir / "apply-report.json").exists())

    def test_apply_refuses_stale_or_unapproved_inputs(self) -> None:
        with self.assertRaisesRegex(WizardError, "approved"):
            self.store.apply_approved_plan(self.run_id, schema_validation=False)
        run_dir = self.approve_plan()

        approval = read_json(run_dir / "plan-approval.json")
        approval["planSha"] = "0" * 64
        write_json(run_dir / "plan-approval.json", approval)
        with self.assertRaisesRegex(WizardError, "planSha changed"):
            self.store.apply_approved_plan(self.run_id, schema_validation=False)
        self.store.approve_plan(self.run_id, "sean")

        plan = read_json(run_dir / "apply-plan.json")
        plan["workbookFingerprint"]["sha256"] = "0" * 64
        write_json(run_dir / "apply-plan.json", plan)
        approval = read_json(run_dir / "plan-approval.json")
        approval["planSha"] = __import__("hashlib").sha256((run_dir / "apply-plan.json").read_bytes()).hexdigest()
        write_json(run_dir / "plan-approval.json", approval)
        with self.assertRaisesRegex(WizardError, "workbookFingerprint changed"):
            self.store.apply_approved_plan(self.run_id, schema_validation=False)

    def test_write_refuses_superseded_pass_c1_plan(self) -> None:
        run_dir = self.approve_plan()
        plan = read_json(run_dir / "apply-plan.json")
        plan["schemaVersion"] = "pass-c-1"
        write_json(run_dir / "apply-plan.json", plan)
        approval = read_json(run_dir / "plan-approval.json")
        approval["planSha"] = __import__("hashlib").sha256((run_dir / "apply-plan.json").read_bytes()).hexdigest()
        write_json(run_dir / "plan-approval.json", approval)

        before = self.master.read_bytes()
        with patch(
            "corvette_form_generator.editor_ops.apply_batch",
            side_effect=AssertionError("pre-pass-c-3 write reached editor_ops"),
        ) as apply_mock:
            with self.assertRaisesRegex(WizardError, "pass-c-3"):
                self.store.apply_approved_plan(self.run_id, write=True, schema_validation=True)
        apply_mock.assert_not_called()
        self.assertEqual(self.master.read_bytes(), before)
        self.assertFalse((run_dir / "apply-report.json").exists())

    def test_write_refuses_pass_c2_and_diagnostic_approval_before_editor_ops(self) -> None:
        run_dir = self.approve_plan()
        self.store.apply_approved_plan(self.run_id, schema_validation=False)
        before_workbook = self.master.read_bytes()
        before_report = (run_dir / "apply-dry-run-report.json").read_bytes()

        with patch(
            "corvette_form_generator.editor_ops.apply_batch",
            side_effect=AssertionError("pass-c-2 reached editor_ops live path"),
        ) as apply_mock:
            with self.assertRaisesRegex(WizardError, "pass-c-3"):
                self.store.apply_approved_plan(self.run_id, write=True, schema_validation=True)

        apply_mock.assert_not_called()
        self.assertEqual(self.master.read_bytes(), before_workbook)
        self.assertEqual((run_dir / "apply-dry-run-report.json").read_bytes(), before_report)
        self.assertFalse((run_dir / "write-approval.json").exists())
        self.assertFalse((run_dir / "apply-report.json").exists())
        self.assertFalse((run_dir / "apply-workbook-edit-log.jsonl").exists())

    def test_write_refuses_schema_disabled_at_service_boundary(self) -> None:
        run_dir = self.approve_plan()
        before = self.master.read_bytes()
        with patch(
            "corvette_form_generator.editor_ops.apply_batch",
            side_effect=AssertionError("schema-disabled write reached editor_ops"),
        ) as apply_mock:
            with self.assertRaisesRegex(WizardError, "schema validation"):
                self.store.apply_approved_plan(self.run_id, write=True, schema_validation=False)
        apply_mock.assert_not_called()
        self.assertEqual(self.master.read_bytes(), before)
        self.assertFalse((run_dir / "apply-report.json").exists())

    def test_dry_run_failure_still_writes_report(self) -> None:
        run_dir = self.approve_plan()
        before = self.master.read_bytes()

        with patch(
            "corvette_form_generator.editor_ops.apply_batch",
            return_value={
                "ok": False,
                "status": "bool_hygiene_failed",
                "errors": ["dry-run bool hygiene failed with 1 error(s)"],
                "warnings": [],
                "boolHygieneResult": {"error_count": 1},
            },
        ):
            result = self.store.apply_approved_plan(self.run_id, schema_validation=False)

        self.assertFalse(result["ok"])
        self.assertEqual(result["status"], "bool_hygiene_failed")
        self.assertEqual(self.master.read_bytes(), before)
        report = read_json(run_dir / "apply-dry-run-report.json")
        self.assertFalse(report["write"])
        self.assertEqual(report["status"], "bool_hygiene_failed")
        self.assertEqual(report["applyResult"]["status"], "bool_hygiene_failed")
        self.assertEqual(report["boolHygieneResult"]["error_count"], 1)
        self.assertEqual(report["workbookBefore"], report["workbookAfter"])
        self.assertEqual(report["deploymentContinuity"], {})
        self.assertEqual(read_json(run_dir / "session.json")["state"], "dry_run_approved")

    def test_legacy_plan_approval_remains_diagnostic_only(self) -> None:
        run_dir = self.approve_plan()
        plan_sha = hashlib.sha256((run_dir / "apply-plan.json").read_bytes()).hexdigest()
        write_json(
            run_dir / "plan-approval.json",
            {
                "schemaVersion": "pass-c-2",
                "approvedBy": "historical reviewer",
                "approvedAt": "2026-07-09T00:00:00",
                "planSha": plan_sha,
            },
        )
        session = read_json(run_dir / "session.json")
        session["state"] = "plan_approved"
        write_json(run_dir / "session.json", session)

        result = self.store.apply_approved_plan(self.run_id, schema_validation=False)

        self.assertTrue(result["ok"], result)
        self.assertEqual(result["status"], "validated_write_blocked")
        self.assertIn(
            "approval_schema_not_writable",
            {item["kind"] for item in result["writeEligibility"]["blockers"]},
        )
        with self.assertRaisesRegex(WizardError, "pass-c-3"):
            self.store.apply_approved_plan(self.run_id, write=True, schema_validation=True)

    def test_unknown_approval_schema_is_not_treated_as_legacy_diagnostic_authority(self) -> None:
        run_dir = self.approve_plan()
        approval = read_json(run_dir / "plan-approval.json")
        approval["schemaVersion"] = "mystery-approval-1"
        approval.pop("scope", None)
        write_json(run_dir / "plan-approval.json", approval)
        session = read_json(run_dir / "session.json")
        session["state"] = "plan_approved"
        write_json(run_dir / "session.json", session)

        with self.assertRaisesRegex(WizardError, "plan-approval-2"):
            self.store.apply_approved_plan(self.run_id, schema_validation=False)

        self.assertFalse((run_dir / "apply-dry-run-report.json").exists())

    def test_approve_write_refuses_current_plan_and_creates_no_record(self) -> None:
        run_dir = self.approve_plan()
        self.store.apply_approved_plan(self.run_id, schema_validation=False)

        with self.assertRaisesRegex(WizardError, "pass-c-3"):
            self.store.approve_write(self.run_id, "sean")

        self.assertFalse((run_dir / "write-approval.json").exists())

    def test_future_plan_still_requires_write_approval_record(self) -> None:
        run_dir, _ = self.future_write_authority(approve=False)

        def refuse() -> None:
            with patch(
                "corvette_form_generator.editor_ops.apply_batch",
                side_effect=AssertionError("missing write approval reached editor_ops"),
            ) as apply_mock:
                with self.assertRaisesRegex(WizardError, "write approval"):
                    self.store.apply_approved_plan(self.run_id, write=True, schema_validation=True)
                apply_mock.assert_not_called()

        self.assert_refusal_preserves_evidence(run_dir, refuse)

    def assert_wrong_write_approval_refuses(self, field: str, value: str, message: str) -> None:
        run_dir, _ = self.future_write_authority()
        approval = read_json(run_dir / "write-approval.json")
        approval[field] = value
        write_json(run_dir / "write-approval.json", approval)

        def refuse() -> None:
            with patch(
                "corvette_form_generator.editor_ops.apply_batch",
                side_effect=AssertionError("wrong write approval reached editor_ops"),
            ) as apply_mock:
                with self.assertRaisesRegex(WizardError, message):
                    self.store.apply_approved_plan(self.run_id, write=True, schema_validation=True)
                apply_mock.assert_not_called()

        self.assert_refusal_preserves_evidence(run_dir, refuse)

    def test_wrong_write_approval_schema_refuses_before_editor_ops(self) -> None:
        self.assert_wrong_write_approval_refuses("schemaVersion", "write-approval-0", "write-approval-1")

    def test_wrong_write_approval_scope_refuses_before_editor_ops(self) -> None:
        self.assert_wrong_write_approval_refuses("scope", "dry_run_evidence", "deployment_ready_write")

    def test_stale_eligible_report_sha_refuses_before_editor_ops(self) -> None:
        run_dir, _ = self.future_write_authority()
        report = read_json(run_dir / "apply-dry-run-report.json")
        report["completedAt"] = "2099-01-01T00:00:00"
        write_json(run_dir / "apply-dry-run-report.json", report)

        def refuse() -> None:
            with patch(
                "corvette_form_generator.editor_ops.apply_batch",
                side_effect=AssertionError("stale report reached editor_ops"),
            ) as apply_mock:
                with self.assertRaisesRegex(WizardError, "report SHA changed"):
                    self.store.apply_approved_plan(self.run_id, write=True, schema_validation=True)
                apply_mock.assert_not_called()

        self.assert_refusal_preserves_evidence(run_dir, refuse)

    def test_mixed_target_ineligibility_refuses_write_approval(self) -> None:
        run_dir, _ = self.future_write_authority(approve=False)
        report = read_json(run_dir / "apply-dry-run-report.json")
        report["writeEligibility"]["targets"]["zr1x"]["eligible"] = False
        report["writeEligibility"]["targets"]["zr1x"]["blockers"] = [
            {"kind": "fixture_blocker", "detail": "one target is blocked"}
        ]
        write_json(run_dir / "apply-dry-run-report.json", report)

        with self.assertRaisesRegex(WizardError, "Every target"):
            self.store.approve_write(self.run_id, "sean")

        self.assertFalse((run_dir / "write-approval.json").exists())
        self.assertFalse((run_dir / "apply-report.json").exists())

    def test_approve_write_refuses_stored_unknown_warning_or_warning_agreement_drift(self) -> None:
        from corvette_form_generator.editor_ops import classify_warnings

        run_dir, _ = self.future_write_authority(approve=False)
        report = read_json(run_dir / "apply-dry-run-report.json")
        warnings = [{"id": "mystery:zr1_options", "message": "unknown warning"}]
        report["warnings"] = warnings
        report["warningPolicy"] = classify_warnings(warnings)
        report["applyResult"]["warnings"] = warnings
        report["applyResult"]["warningPolicy"] = report["warningPolicy"]
        write_json(run_dir / "apply-dry-run-report.json", report)

        with self.assertRaisesRegex(WizardError, "blocking or unknown warnings"):
            self.store.approve_write(self.run_id, "sean")

        self.assertFalse((run_dir / "write-approval.json").exists())

    def test_schema_disabled_diagnostic_can_never_be_write_eligible(self) -> None:
        run_dir, _ = self.future_write_authority(approve=False)
        session = read_json(run_dir / "session.json")
        session["state"] = "dry_run_approved"
        write_json(run_dir / "session.json", session)

        result = self.store.apply_approved_plan(self.run_id, schema_validation=False)

        self.assertTrue(result["ok"], result)
        self.assertEqual(result["status"], "validated_write_blocked")
        self.assertIn(
            "schema_validation_not_run",
            {item["kind"] for item in result["writeEligibility"]["blockers"]},
        )

    def test_approve_write_requires_schema_validated_eligible_report(self) -> None:
        run_dir, _ = self.future_write_authority(approve=False)
        report = read_json(run_dir / "apply-dry-run-report.json")
        report["schemaValidationEnabled"] = False
        report["schemaResult"] = None
        write_json(run_dir / "apply-dry-run-report.json", report)

        with self.assertRaisesRegex(WizardError, "schema-validated"):
            self.store.approve_write(self.run_id, "sean")

        self.assertFalse((run_dir / "write-approval.json").exists())

    def test_approve_write_requires_report_counts_from_editor_result(self) -> None:
        run_dir, _ = self.future_write_authority(approve=False)
        report = read_json(run_dir / "apply-dry-run-report.json")
        report["operationCoverage"] = {
            **report["operationCoverage"],
            "rawCount": report["operationCoverage"]["rawCount"] - 1,
            "rawCovered": report["operationCoverage"]["rawCovered"] - 1,
        }
        write_json(run_dir / "apply-dry-run-report.json", report)

        with self.assertRaisesRegex(WizardError, "editor operation coverage"):
            self.store.approve_write(self.run_id, "sean")

        self.assertFalse((run_dir / "write-approval.json").exists())

    def assert_new_warning_refuses_before_live_write(self, warning: dict, message: str) -> None:
        from corvette_form_generator.editor_ops import classify_warnings

        run_dir, report = self.future_write_authority()
        warnings = [warning]
        preview = {
            **report["applyResult"],
            "warnings": warnings,
            "warningPolicy": classify_warnings(warnings),
            "operationCoverage": report["operationCoverage"],
            "verification": report["verification"],
        }

        def refuse() -> None:
            with patch(
                "corvette_form_generator.editor_ops.apply_batch",
                return_value=preview,
            ) as apply_mock:
                with self.assertRaisesRegex(WizardError, message):
                    self.store.apply_approved_plan(self.run_id, write=True, schema_validation=True)
                self.assertTrue(apply_mock.called)
                self.assertTrue(all(not call.kwargs.get("write") for call in apply_mock.call_args_list))

        self.assert_refusal_preserves_evidence(run_dir, refuse)

    def test_warning_drift_refuses_before_live_write(self) -> None:
        self.assert_new_warning_refuses_before_live_write(
            {"id": "scaffold:zr1_options", "message": "new scaffold warning"},
            "Warning set drifted",
        )

    def test_unknown_warning_refuses_before_live_write(self) -> None:
        self.assert_new_warning_refuses_before_live_write(
            {"id": "mystery:zr1_options", "message": "unknown warning"},
            "blocking or unknown",
        )

    def test_already_applied_replay_refuses_without_touching_evidence(self) -> None:
        run_dir = self.approve_plan()
        self.store.apply_approved_plan(self.run_id, schema_validation=False)
        session = read_json(run_dir / "session.json")
        session["state"] = "applied"
        write_json(run_dir / "session.json", session)
        before_workbook = self.master.read_bytes()
        before_report = (run_dir / "apply-dry-run-report.json").read_bytes()

        with patch(
            "corvette_form_generator.editor_ops.apply_batch",
            side_effect=AssertionError("already-applied replay reached editor_ops"),
        ) as apply_mock:
            with self.assertRaisesRegex(WizardError, "already applied"):
                self.store.apply_approved_plan(self.run_id, write=True, schema_validation=True)

        apply_mock.assert_not_called()
        self.assertEqual(self.master.read_bytes(), before_workbook)
        self.assertEqual((run_dir / "apply-dry-run-report.json").read_bytes(), before_report)
        self.assertFalse((run_dir / "apply-report.json").exists())

    def test_cli_dry_run_outputs_json_and_report(self) -> None:
        run_dir = self.approve_plan()

        completed = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts" / "ingest_wizard_apply.py"),
                "--root",
                str(self.root),
                "--workbook",
                str(self.master),
                "--run",
                self.run_id,
                "--no-schema-validation",
            ],
            check=False,
            text=True,
            capture_output=True,
        )

        self.assertEqual(completed.returncode, 0, completed.stderr + completed.stdout)
        payload = json.loads(completed.stdout)
        self.assertEqual(payload["status"], "validated_write_blocked")
        self.assertTrue((run_dir / "apply-dry-run-report.json").is_file())


if __name__ == "__main__":
    unittest.main()
