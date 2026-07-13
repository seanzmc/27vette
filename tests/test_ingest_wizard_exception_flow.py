#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import sys
import tempfile
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from unittest import mock
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for entry in (ROOT / "scripts", ROOT / "tests"):
    if str(entry) not in sys.path:
        sys.path.insert(0, str(entry))

from corvette_form_generator.ingest.wizard.session import (  # noqa: E402
    COMPILER_MUTATION_FILES,
    WizardError,
    WizardSessionStore,
)
from ingest_wizard_fixtures import build_master_workbook, build_raw_export  # noqa: E402

ROLES = {
    "Equipment Groups 1": "exclude",
    "Equipment Groups 4": "options",
    "Price Schedule": "price",
    "Standard Equipment 1": "exclude",
    "Color and Trim 1": "exclude",
}


class ExceptionFlowTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        build_raw_export(self.root / "raw.xlsx")
        self.master = build_master_workbook(self.root / "stingray_master.xlsx")
        self.store = WizardSessionStore(self.root)
        self.run_id = self.store.create_session("raw.xlsx")["session"]["runId"]
        self.store.confirm_roles(self.run_id, ROLES)
        self.store.run_parse(self.run_id)
        self.store.select_models(self.run_id, ["zr1"], {"zr1": "z06"})
        self.store.compile_canonical_rows(self.run_id)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_compiler_summary_is_compact_and_keeps_readiness_separate(self) -> None:
        summary = self.store.compiler_summary(self.run_id)

        self.assertEqual(summary["session"]["runId"], self.run_id)
        model = summary["models"]["zr1"]
        self.assertEqual(
            set(model),
            {
                "mode",
                "compileReady",
                "planReady",
                "writeReady",
                "deploymentReady",
                "blockerCount",
                "deferralCount",
                "boundaryReasons",
            },
        )
        self.assertFalse(model["compileReady"])
        self.assertFalse(model["planReady"])
        self.assertFalse(model["writeReady"])
        self.assertFalse(model["deploymentReady"])
        self.assertGreater(model["blockerCount"], 0)
        self.assertIn("manifest", summary["counts"])
        self.assertIn("exceptions", summary["counts"])
        self.assertIn("sourceFeatures", summary["counts"])
        self.assertIn("familyCoverage", summary["counts"])
        self.assertNotIn("manifest", summary)
        self.assertNotIn("exceptionQueue", summary)
        self.assertNotIn("sourceFeatureCoverage", summary)
        self.assertLess(len(str(summary)), 100_000)

    def test_exception_view_filters_and_paginates_deterministically(self) -> None:
        first = self.store.exception_queue_view(
            self.run_id,
            state="open",
            actionable="yes",
            offset=0,
            limit=2,
        )
        second = self.store.exception_queue_view(
            self.run_id,
            state="open",
            actionable="yes",
            offset=2,
            limit=2,
        )

        self.assertEqual(first["total"], 6)
        self.assertEqual(first["offset"], 0)
        self.assertEqual(first["limit"], 2)
        self.assertEqual(len(first["items"]), 2)
        self.assertEqual(len(second["items"]), 2)
        self.assertTrue(all(item["state"] == "open" for item in first["items"]))
        self.assertTrue(all(item["subject"]["allowedActions"] for item in first["items"]))
        first_ids = [item["subject"]["subjectId"] for item in first["items"]]
        second_ids = [item["subject"]["subjectId"] for item in second["items"]]
        self.assertFalse(set(first_ids) & set(second_ids))
        self.assertEqual(
            first_ids + second_ids,
            sorted(first_ids + second_ids)[:4],
        )
        self.assertIn("models", first["filters"])
        self.assertIn("families", first["filters"])
        self.assertIn("reasons", first["filters"])

    def test_section_exception_view_has_raw_evidence_and_canonical_choices(self) -> None:
        payload = self.store.exception_queue_view(
            self.run_id,
            reason="missing_section",
            state="open",
            actionable="yes",
        )

        self.assertGreater(payload["total"], 0)
        item = payload["items"][0]
        self.assertEqual(item["subject"]["allowedActions"], ["choose_section"])
        self.assertTrue(item["evidence"]["raw"])
        raw = item["evidence"]["raw"][0]
        self.assertTrue(raw["sourceEvidence"]["cells"])
        self.assertTrue(raw["sourceEvidence"]["sheetName"])
        sections = item["choices"]["sections"]
        self.assertIn("sec_whee_001", {section["sectionId"] for section in sections})
        self.assertTrue(all(section["sectionName"] for section in sections))
        self.assertEqual(item["choices"]["relationshipRuleTypes"], [])

    def test_resolve_section_validates_and_recompiles_current_subject(self) -> None:
        item = self.store.exception_queue_view(
            self.run_id,
            reason="missing_section",
            state="open",
            actionable="yes",
            limit=1,
        )["items"][0]
        subject = item["subject"]

        result = self.store.resolve_exception(
            self.run_id,
            subject_id=subject["subjectId"],
            subject_version=subject["subjectVersion"],
            action="choose_section",
            payload={"sectionId": "sec_whee_001"},
            reviewer="sean",
        )

        self.assertEqual(result["subject"]["state"], "resolved")
        resolution = result["subject"]["resolution"]
        self.assertEqual(resolution["disposition"], "resolved")
        self.assertEqual(resolution["action"], "choose_section")
        self.assertEqual(resolution["payload"], {"sectionId": "sec_whee_001"})
        self.assertEqual(resolution["reviewer"], "sean")
        self.assertIn("resolvedAt", resolution)
        self.assertEqual(result["summary"]["session"]["runId"], self.run_id)
        self.assertFalse((self.store.run_dir(self.run_id) / "apply-plan.json").exists())

    def test_reopen_resolution_recompiles_and_logs_once(self) -> None:
        subject = self.store.exception_queue_view(
            self.run_id,
            reason="missing_section",
            state="open",
            actionable="yes",
            limit=1,
        )["items"][0]["subject"]
        self.store.resolve_exception(
            self.run_id,
            subject_id=subject["subjectId"],
            subject_version=subject["subjectVersion"],
            action="choose_section",
            payload={"sectionId": "sec_whee_001"},
            reviewer="sean",
        )

        result = self.store.reopen_exception(
            self.run_id,
            subject_id=subject["subjectId"],
            subject_version=subject["subjectVersion"],
            reviewer="sean",
        )

        self.assertEqual(result["subject"]["state"], "open")
        self.assertIsNone(result["subject"]["resolution"])
        log_path = self.store.run_dir(self.run_id) / "exception-log.jsonl"
        events = [json.loads(line) for line in log_path.read_text().splitlines() if line]
        reopened = [event for event in events if event["eventType"] == "resolution_reopened"]
        self.assertEqual(len(reopened), 1)
        with self.assertRaisesRegex(Exception, "not currently resolved"):
            self.store.reopen_exception(
                self.run_id,
                subject_id=subject["subjectId"],
                subject_version=subject["subjectVersion"],
                reviewer="sean",
            )

    def test_resolution_refuses_stale_or_noncanonical_choices_without_mutation(self) -> None:
        subject = self.store.exception_queue_view(
            self.run_id,
            reason="missing_section",
            state="open",
            actionable="yes",
            limit=1,
        )["items"][0]["subject"]
        path = self.store.run_dir(self.run_id) / "exception-resolutions.json"
        before = path.read_bytes()

        with self.assertRaisesRegex(WizardError, "current canonical workbook choice"):
            self.store.resolve_exception(
                self.run_id,
                subject_id=subject["subjectId"],
                subject_version=subject["subjectVersion"],
                action="choose_section",
                payload={"sectionId": "sec_invented_999"},
                reviewer="sean",
            )
        with self.assertRaisesRegex(WizardError, "stale"):
            self.store.resolve_exception(
                self.run_id,
                subject_id=subject["subjectId"],
                subject_version="stale-version",
                action="choose_section",
                payload={"sectionId": "sec_whee_001"},
                reviewer="sean",
            )
        self.assertEqual(path.read_bytes(), before)
        self.assertEqual(self.store.compiler_detail(self.run_id)["session"]["runId"], self.run_id)

    def test_failed_resolution_recompile_restores_prior_coherent_artifact(self) -> None:
        subject = self.store.exception_queue_view(
            self.run_id,
            reason="missing_section",
            state="open",
            actionable="yes",
            limit=1,
        )["items"][0]["subject"]
        path = self.store.run_dir(self.run_id) / "exception-resolutions.json"
        before = path.read_bytes()

        with mock.patch.object(
            self.store,
            "compile_canonical_rows",
            side_effect=WizardError("forced recompile failure"),
        ):
            with self.assertRaisesRegex(WizardError, "forced recompile failure"):
                self.store.resolve_exception(
                    self.run_id,
                    subject_id=subject["subjectId"],
                    subject_version=subject["subjectVersion"],
                    action="choose_section",
                    payload={"sectionId": "sec_whee_001"},
                    reviewer="sean",
                )
        self.assertEqual(path.read_bytes(), before)
        self.assertEqual(self.store.compiler_detail(self.run_id)["session"]["runId"], self.run_id)

    def test_audit_failure_restores_all_compiler_and_session_files(self) -> None:
        subject = self.store.exception_queue_view(
            self.run_id,
            reason="missing_section",
            state="open",
            actionable="yes",
            limit=1,
        )["items"][0]["subject"]
        run_dir = self.store.run_dir(self.run_id)
        before = self.store._snapshot_run_files(run_dir, COMPILER_MUTATION_FILES)

        with mock.patch(
            "corvette_form_generator.ingest.wizard.session.append_audit_event_once",
            side_effect=OSError("forced audit failure"),
        ):
            with self.assertRaisesRegex(OSError, "forced audit failure"):
                self.store.resolve_exception(
                    self.run_id,
                    subject_id=subject["subjectId"],
                    subject_version=subject["subjectVersion"],
                    action="choose_section",
                    payload={"sectionId": "sec_whee_001"},
                    reviewer="sean",
                )

        self.assertEqual(
            self.store._snapshot_run_files(run_dir, COMPILER_MUTATION_FILES),
            before,
        )
        self.store.compiler_detail(self.run_id)

    def test_summary_reports_input_drift_and_resolve_refuses_it(self) -> None:
        subject = self.store.exception_queue_view(
            self.run_id,
            reason="missing_section",
            state="open",
            actionable="yes",
            limit=1,
        )["items"][0]["subject"]
        stat = self.master.stat()
        os.utime(self.master, ns=(stat.st_atime_ns, stat.st_mtime_ns + 1_000_000))
        try:
            freshness = self.store.compiler_summary(self.run_id)["freshness"]
            self.assertTrue(freshness["stale"])
            self.assertIn("workbook changed after compile", freshness["reasons"])
            with self.assertRaisesRegex(WizardError, "Recompile before reviewing exceptions"):
                self.store.exception_queue_view(self.run_id)
            with self.assertRaisesRegex(WizardError, "recompile before resolving"):
                self.store.resolve_exception(
                    self.run_id,
                    subject_id=subject["subjectId"],
                    subject_version=subject["subjectVersion"],
                    action="choose_section",
                    payload={"sectionId": "sec_whee_001"},
                    reviewer="sean",
                )
        finally:
            os.utime(self.master, ns=(stat.st_atime_ns, stat.st_mtime_ns))

    def test_nonprojectable_row_action_is_not_exposed(self) -> None:
        subject = {
            "reasonCode": "comparator_only_rule_group_proposal",
            "allowedActions": ["provide_typed_value", "mark_not_applicable"],
        }
        self.assertEqual(
            self.store._projectable_exception_actions(subject),
            [],
        )
        self.assertEqual(
            self.store._projectable_exception_actions(
                {
                    "reasonCode": "ambiguous_existing_identity",
                    "allowedActions": ["retain_existing"],
                }
            ),
            [],
        )

    def test_price_resolution_uses_only_finite_target_scope_choices(self) -> None:
        payload = self.store.exception_queue_view(
            self.run_id,
            reason="unresolved_price_scope",
            state="open",
            actionable="yes",
        )
        self.assertGreater(payload["total"], 0)
        item = payload["items"][0]
        self.assertTrue(item["choices"]["priceScopes"])
        self.assertTrue(
            all(scope["label"] for scope in item["choices"]["priceScopes"])
        )
        subject = item["subject"]
        with self.assertRaisesRegex(WizardError, "current target variant"):
            self.store.resolve_exception(
                self.run_id,
                subject_id=subject["subjectId"],
                subject_version=subject["subjectVersion"],
                action="provide_typed_value",
                payload={
                    "bodyStyleScope": "coupe",
                    "trimLevelScope": "NOT_A_REAL_TARGET_VARIANT",
                    "priceValue": 1234,
                },
                reviewer="sean",
            )

    def test_concurrent_resolutions_merge_without_lost_update(self) -> None:
        subjects = [
            item["subject"]
            for item in self.store.exception_queue_view(
                self.run_id,
                reason="missing_section",
                state="open",
                actionable="yes",
                limit=2,
            )["items"]
        ]

        def resolve(subject: dict) -> dict:
            return self.store.resolve_exception(
                self.run_id,
                subject_id=subject["subjectId"],
                subject_version=subject["subjectVersion"],
                action="choose_section",
                payload={"sectionId": "sec_whee_001"},
                reviewer="sean",
            )

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(resolve, subjects))
        self.assertEqual(len(results), 2)
        valid = self.store.compiler_detail(self.run_id)["resolutions"]["validEntries"]
        resolved_ids = {entry["subjectId"] for entry in valid}
        self.assertTrue({subject["subjectId"] for subject in subjects} <= resolved_ids)

    def test_model_reselection_waits_for_active_compile_mutation(self) -> None:
        compile_entered = threading.Event()
        release_compile = threading.Event()
        reselection_complete = threading.Event()

        def held_compile(run_id: str) -> dict:
            compile_entered.set()
            self.assertTrue(release_compile.wait(timeout=2))
            return {"runId": run_id}

        def reselect() -> None:
            self.store.select_models(self.run_id, ["zr1"], {"zr1": "z06"})
            reselection_complete.set()

        with mock.patch.object(self.store, "_compile_canonical_rows_locked", side_effect=held_compile):
            compile_thread = threading.Thread(
                target=self.store.compile_canonical_rows,
                args=(self.run_id,),
            )
            select_thread = threading.Thread(target=reselect)
            compile_thread.start()
            self.assertTrue(compile_entered.wait(timeout=1))
            select_thread.start()
            self.assertFalse(reselection_complete.wait(timeout=0.1))
            release_compile.set()
            compile_thread.join(timeout=2)
            select_thread.join(timeout=2)

        self.assertTrue(reselection_complete.is_set())


if __name__ == "__main__":
    unittest.main()
