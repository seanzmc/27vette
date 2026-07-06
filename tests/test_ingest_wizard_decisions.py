#!/usr/bin/env python3
"""Pass B store tests: model selection, decision capture, completeness.

Fixture workbooks only; the live workbook and raw exports are never touched.
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

from corvette_form_generator.ingest.wizard.session import (  # noqa: E402
    STATE_DECISIONS_COMPLETE,
    STATE_DECISIONS_IN_PROGRESS,
    STATE_MODELS_SELECTED,
    WizardError,
    WizardSessionStore,
    read_json,
    write_json,
)
from corvette_form_generator.ingest.wizard.decisions import (  # noqa: E402
    candidate_fingerprint,
    copy_decisions,
)
from ingest_wizard_fixtures import build_master_workbook, build_raw_export  # noqa: E402


def _candidate(candidate_id: str, model_code: str, rpo: str, *, ref_only: str = "", kind: str = "orderable") -> dict:
    return {
        "candidateId": candidate_id,
        "rpo": rpo,
        "refOnlyRpo": ref_only,
        "rowKind": kind,
        "statuses": [{"modelCode": model_code, "trim": "1LZ", "bodyStyle": "coupe", "variantLabel": ""}],
        "sourceEvidence": {"sheetName": candidate_id.split(":")[0], "rowIndex": 1, "cells": {"A1": rpo or ref_only}},
    }


def _decision(model: str, lane: str, candidate: dict, payload: dict) -> dict:
    return {
        "decisionId": f"{model}:{lane}:{candidate['candidateId']}",
        "model": model,
        "lane": lane,
        "candidateId": candidate["candidateId"],
        "candidateFingerprint": candidate_fingerprint(candidate),
        "action": "assign_section",
        "payload": payload,
        "resolution": "approved_for_plan",
        "reviewerNote": "",
        "decidedAt": "2026-07-06T00:00:00",
    }


class CopyRpoIdentityBranchTest(unittest.TestCase):
    """Model-exclusive sheets: copy must match by RPO identity, fail closed."""

    def test_exactly_one_rpo_match_copies_with_new_fingerprint(self) -> None:
        source = _candidate("zr1 sheet:5", "1YR07", "AAA")
        target = _candidate("gsx sheet:9", "1YG07", "AAA")
        decisions = {"zr1:section:zr1 sheet:5": _decision("zr1", "section", source, {"sectionId": "s1"})}
        report = copy_decisions(decisions, [source, target], "zr1", "grand_sport_x")
        self.assertEqual(len(report["copied"]), 1)
        copied = report["copied"][0]
        self.assertEqual(copied["candidateId"], "gsx sheet:9")
        self.assertEqual(copied["candidateFingerprint"], candidate_fingerprint(target))
        self.assertEqual(copied["decisionId"], "grand_sport_x:section:gsx sheet:9")
        self.assertEqual(copied["copiedFrom"], "zr1")

    def test_zero_matches_skip_with_reason(self) -> None:
        source = _candidate("zr1 sheet:5", "1YR07", "AAA")
        other_target = _candidate("gsx sheet:9", "1YG07", "BBB")
        decisions = {"zr1:section:zr1 sheet:5": _decision("zr1", "section", source, {"sectionId": "s1"})}
        report = copy_decisions(decisions, [source, other_target], "zr1", "grand_sport_x")
        self.assertEqual(report["copied"], [])
        self.assertEqual(report["skipped"][0]["reason"], "no_unique_rpo_match")
        self.assertEqual(report["skipped"][0]["matches"], 0)

    def test_ambiguous_matches_skip_with_reason(self) -> None:
        source = _candidate("zr1 sheet:5", "1YR07", "AAA")
        target_a = _candidate("gsx sheet:9", "1YG07", "AAA")
        target_b = _candidate("gsx other:3", "1YG07", "AAA")
        decisions = {"zr1:section:zr1 sheet:5": _decision("zr1", "section", source, {"sectionId": "s1"})}
        report = copy_decisions(decisions, [source, target_a, target_b], "zr1", "grand_sport_x")
        self.assertEqual(report["copied"], [])
        self.assertEqual(report["skipped"][0]["reason"], "no_unique_rpo_match")
        self.assertEqual(report["skipped"][0]["matches"], 2)

    def test_source_candidate_missing_skips(self) -> None:
        source = _candidate("zr1 sheet:5", "1YR07", "AAA")
        decision = _decision("zr1", "section", source, {"sectionId": "s1"})
        target = _candidate("gsx sheet:9", "1YG07", "AAA")
        # Candidate list lacks the source candidate entirely.
        report = copy_decisions({decision["decisionId"]: decision}, [target], "zr1", "grand_sport_x")
        self.assertEqual(report["copied"], [])
        self.assertEqual(report["skipped"][0]["reason"], "source_candidate_missing")

    def test_within_batch_duplicate_target_reports(self) -> None:
        source_a = _candidate("zr1 sheet:5", "1YR07", "AAA")
        source_b = _candidate("zr1 other:7", "1YR07", "AAA")
        target = _candidate("gsx sheet:9", "1YG07", "AAA")
        decisions = {
            "zr1:section:zr1 sheet:5": _decision("zr1", "section", source_a, {"sectionId": "s1"}),
            "zr1:section:zr1 other:7": _decision("zr1", "section", source_b, {"sectionId": "s2"}),
        }
        report = copy_decisions(decisions, [source_a, source_b, target], "zr1", "grand_sport_x")
        self.assertEqual(len(report["copied"]), 1)
        self.assertEqual(report["skipped"][0]["reason"], "duplicate_target_in_batch")


class PassBStoreTest(unittest.TestCase):
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

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def run_dir(self) -> Path:
        return self.store.run_dir(self.run_id)

    def select_defaults(self) -> dict:
        return self.store.select_models(self.run_id, ["zr1", "zr1x"], {"zr1": "z06", "zr1x": "z06"})

    def zr1_candidate_ids(self) -> list[str]:
        queue = self.store.review_queue(self.run_id, "zr1", "section")
        return [candidate["candidateId"] for candidate in queue["candidates"]]

    # ------------------------------------------------------------ selection
    def test_model_options_detect_families_with_counts(self) -> None:
        options = self.store.model_options(self.run_id)["models"]
        by_key = {option["modelKey"]: option for option in options}
        self.assertIn("zr1", by_key)
        self.assertIn("zr1x", by_key)
        self.assertIn("stingray", by_key)
        self.assertEqual(by_key["zr1"]["comparatorDefault"], "z06")
        self.assertTrue(by_key["zr1"]["isDefaultTarget"])
        self.assertFalse(by_key["stingray"]["isDefaultTarget"])
        self.assertGreater(by_key["zr1"]["candidateCount"], 0)

    def test_selection_validation_fails_closed(self) -> None:
        with self.assertRaises(WizardError):
            self.store.select_models(self.run_id, [], {})
        with self.assertRaises(WizardError):
            self.store.select_models(self.run_id, ["nova"], {})
        with self.assertRaises(WizardError):
            self.store.select_models(self.run_id, ["grand_sport_x"], {})  # not in fixture export
        with self.assertRaises(WizardError):
            self.store.select_models(self.run_id, ["zr1", "zr1x"], {"zr1": "zr1x"})  # comparator=target
        with self.assertRaises(WizardError):
            self.store.select_models(self.run_id, ["zr1"], {"zr1x": "z06"})  # comparator for non-target

    def test_selection_persists_artifacts_and_state(self) -> None:
        result = self.select_defaults()
        self.assertEqual(result["session"]["state"], STATE_MODELS_SELECTED)
        selection = read_json(self.run_dir() / "model-selection.json")
        self.assertEqual(selection["targets"], ["zr1", "zr1x"])
        self.assertTrue(selection["candidatesFingerprint"])
        reconciliation = read_json(self.run_dir() / "variant-reconciliation.json")
        zr1 = reconciliation["models"]["zr1"]
        # Fixture export has ZR1 1LZ coupe only; workbook scaffold adds 3LZ conv.
        self.assertFalse(zr1["agrees"])
        self.assertEqual(len(zr1["workbookOnly"]), 1)
        self.assertTrue(reconciliation["models"]["zr1x"]["agrees"])

    def test_selection_requires_parse_first(self) -> None:
        created = self.store.create_session("raw.xlsx")
        with self.assertRaises(WizardError):
            self.store.select_models(created["session"]["runId"], ["zr1"], {})

    # ------------------------------------------------------------ decisions
    def test_decision_save_validates_and_persists(self) -> None:
        self.select_defaults()
        candidate_id = self.zr1_candidate_ids()[0]
        result = self.store.save_decisions(
            self.run_id,
            [
                {
                    "model": "zr1",
                    "lane": "section",
                    "candidateId": candidate_id,
                    "action": "assign_section",
                    "payload": {"sectionId": "sec_whee_001"},
                    "resolution": "approved_for_plan",
                }
            ],
        )
        self.assertEqual(result["session"]["state"], STATE_DECISIONS_IN_PROGRESS)
        snapshot = read_json(self.run_dir() / "decisions.json")
        self.assertEqual(len(snapshot["decisions"]), 1)
        record = snapshot["decisions"][0]
        self.assertEqual(record["decisionId"], f"zr1:section:{candidate_id}")
        self.assertTrue(record["candidateFingerprint"])
        log_lines = (self.run_dir() / "decisions-log.jsonl").read_text().strip().splitlines()
        self.assertEqual(len(log_lines), 1)

    def test_decision_rejections(self) -> None:
        self.select_defaults()
        candidate_id = self.zr1_candidate_ids()[0]
        bad = [
            {"model": "z06", "lane": "section", "candidateId": candidate_id, "resolution": "approved_for_plan"},
            {"model": "zr1", "lane": "nope", "candidateId": candidate_id, "resolution": "approved_for_plan"},
            {"model": "zr1", "lane": "section", "candidateId": "missing:1", "resolution": "approved_for_plan"},
            {"model": "zr1", "lane": "section", "candidateId": candidate_id, "resolution": "maybe"},
            {"model": "zr1", "lane": "exclusive_group", "resolution": "approved_for_plan"},  # no groupKey
        ]
        for decision in bad:
            with self.assertRaises(WizardError, msg=decision):
                self.store.save_decisions(self.run_id, [decision])

    def test_reparse_invalidates_selection_and_decisions_by_fingerprint(self) -> None:
        self.select_defaults()
        candidate_id = self.zr1_candidate_ids()[0]
        self.store.save_decisions(
            self.run_id,
            [
                {
                    "model": "zr1",
                    "lane": "section",
                    "candidateId": candidate_id,
                    "action": "assign_section",
                    "payload": {"sectionId": "sec_whee_001"},
                    "resolution": "approved_for_plan",
                }
            ],
        )
        # Simulate a re-parse that changes candidate evidence.
        candidates_file = self.run_dir() / "option-candidates.json"
        payload = read_json(candidates_file)
        target = next(c for c in payload["candidates"] if c["candidateId"] == candidate_id)
        target["sourceEvidence"]["cells"]["Z99"] = "changed"
        write_json(candidates_file, payload)
        with self.assertRaises(WizardError):
            self.store.review_queue(self.run_id, "zr1", "section")
        # Re-selection prunes the now-stale decision instead of keeping it silently.
        self.select_defaults()
        snapshot = read_json(self.run_dir() / "decisions.json")
        self.assertEqual(snapshot["decisions"], [])

    def test_restart_survival(self) -> None:
        self.select_defaults()
        candidate_id = self.zr1_candidate_ids()[0]
        self.store.save_decisions(
            self.run_id,
            [
                {
                    "model": "zr1",
                    "lane": "price",
                    "candidateId": candidate_id,
                    "action": "confirm_no_price",
                    "payload": {},
                    "resolution": "approved_for_plan",
                }
            ],
        )
        fresh_store = WizardSessionStore(self.root, workbook_path=self.master)
        queue = fresh_store.review_queue(self.run_id, "zr1", "price")
        self.assertEqual(len(queue["decisions"]), 1)
        self.assertEqual(queue["decisions"][0]["action"], "confirm_no_price")

    # ------------------------------------------------------------ lanes
    def test_review_queue_lane_feeds(self) -> None:
        self.select_defaults()
        section_queue = self.store.review_queue(self.run_id, "zr1", "section")
        self.assertEqual(
            [section["sectionId"] for section in section_queue["sections"]],
            ["sec_pain_001", "sec_whee_001"],
        )
        relationship_queue = self.store.review_queue(self.run_id, "zr1", "relationship")
        self.assertIn("hints", relationship_queue)
        prefill = self.store.review_queue(self.run_id, "zr1", "presentation")["prefill"]
        self.assertEqual(prefill["templateModel"], "z06")
        self.assertEqual(prefill["targetModel"], "zr1")
        steps = prefill["sheets"]["runtime_steps"]
        self.assertEqual(len(steps), 2)
        self.assertEqual(steps[0]["row"]["model_key"], "zr1")
        self.assertEqual(steps[0]["provenance"], {"templateModel": "z06", "sheet": "runtime_steps"})
        with self.assertRaises(WizardError):
            self.store.review_queue(self.run_id, "stingray", "section")
        with self.assertRaises(WizardError):
            self.store.review_queue(self.run_id, "zr1", "unknown_lane")

    def test_comparator_candidates_not_in_target_queue(self) -> None:
        self.select_defaults()
        for lane in ("section", "price"):
            for candidate in self.store.review_queue(self.run_id, "zr1", lane)["candidates"]:
                model_codes = {status["modelCode"][:3] for status in candidate["statuses"]}
                self.assertIn("1YR", model_codes)

    # ------------------------------------------------------- completeness
    def reconciliation_decision(self, model: str) -> dict:
        return {
            "model": model,
            "lane": "relationship",
            "groupKey": "variant_reconciliation",
            "action": "needs_product_decision",
            "payload": {"note": "workbook scaffold has 3lz_r67 the export lacks"},
            "resolution": "approved_for_plan",
        }

    def complete_model(self, model: str, *, resolve_reconciliation: bool = True) -> None:
        queue = self.store.review_queue(self.run_id, model, "section")
        decisions = []
        reconciliation = self.store.reconciliation(self.run_id)["models"].get(model, {})
        if resolve_reconciliation and not reconciliation.get("agrees", True):
            decisions.append(self.reconciliation_decision(model))
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
            decisions.append(
                {
                    "model": model,
                    "lane": "price",
                    "candidateId": candidate["candidateId"],
                    "action": "confirm_no_price",
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

    def test_variant_reconciliation_disagreement_blocks_completion(self) -> None:
        self.select_defaults()
        # Fixture zr1 reconciliation disagrees (workbook-only 3lz_r67).
        # Complete every lane but skip the reconciliation decision.
        self.complete_model("zr1", resolve_reconciliation=False)
        self.complete_model("zr1x")
        progress = self.store.progress(self.run_id)
        blockers = progress["models"]["zr1"]["blockers"]
        self.assertEqual(
            [b["reason"] for b in blockers], ["variant_reconciliation_disagreement_undecided"]
        )
        with self.assertRaises(WizardError):
            self.store.mark_complete(self.run_id)
        self.store.save_decisions(self.run_id, [self.reconciliation_decision("zr1")])
        report = self.store.mark_complete(self.run_id)
        self.assertTrue(report["allComplete"])

    def test_completeness_gate_and_holds(self) -> None:
        self.select_defaults()
        with self.assertRaises(WizardError):
            self.store.mark_complete(self.run_id)
        self.complete_model("zr1")
        progress = self.store.progress(self.run_id)
        self.assertTrue(progress["models"]["zr1"]["complete"])
        self.assertFalse(progress["models"]["zr1x"]["complete"])
        self.assertFalse(progress["allComplete"])
        self.complete_model("zr1x")
        report = self.store.mark_complete(self.run_id)
        self.assertTrue(report["allComplete"])
        self.assertEqual(report["session"]["state"], STATE_DECISIONS_COMPLETE)

    def test_hold_satisfies_candidate_requirement_but_is_enumerated(self) -> None:
        self.select_defaults()
        self.complete_model("zr1")
        self.complete_model("zr1x")
        candidate_id = self.zr1_candidate_ids()[0]
        self.store.save_decisions(
            self.run_id,
            [
                {
                    "model": "zr1",
                    "lane": "price",
                    "candidateId": candidate_id,
                    "action": "defer_price_extractor",
                    "payload": {},
                    "resolution": "hold_for_question",
                    "reviewerNote": "ask GM rep",
                }
            ],
        )
        report = self.store.mark_complete(self.run_id)
        self.assertTrue(report["allComplete"])
        holds = report["models"]["zr1"]["holds"]
        self.assertEqual(len(holds), 1)
        self.assertEqual(holds[0]["note"], "ask GM rep")

    def test_presentation_hold_blocks_completion(self) -> None:
        self.select_defaults()
        self.complete_model("zr1")
        self.complete_model("zr1x")
        self.store.save_decisions(
            self.run_id,
            [
                {
                    "model": "zr1",
                    "lane": "presentation",
                    "groupKey": "runtime_steps",
                    "action": "approve_presentation_rows",
                    "payload": {},
                    "resolution": "hold_for_question",
                }
            ],
        )
        with self.assertRaises(WizardError):
            self.store.mark_complete(self.run_id)

    def test_new_decision_after_complete_reopens(self) -> None:
        self.select_defaults()
        self.complete_model("zr1")
        self.complete_model("zr1x")
        self.store.mark_complete(self.run_id)
        candidate_id = self.zr1_candidate_ids()[0]
        result = self.store.save_decisions(
            self.run_id,
            [
                {
                    "model": "zr1",
                    "lane": "copy_split",
                    "candidateId": candidate_id,
                    "action": "split_copy",
                    "payload": {"name": "Carbon Wheel Package"},
                    "resolution": "approved_for_plan",
                }
            ],
        )
        self.assertEqual(result["session"]["state"], STATE_DECISIONS_IN_PROGRESS)

    # ------------------------------------------------- b.2: delete / batch
    def test_batch_stamping_and_delete_by_batch(self) -> None:
        self.select_defaults()
        ids = self.zr1_candidate_ids()[:3]
        self.assertGreaterEqual(len(ids), 2)
        result = self.store.save_decisions(
            self.run_id,
            [
                {
                    "model": "zr1",
                    "lane": "section",
                    "candidateId": candidate_id,
                    "action": "assign_section",
                    "payload": {"sectionId": "sec_whee_001"},
                    "resolution": "approved_for_plan",
                }
                for candidate_id in ids
            ],
        )
        batch_id = result["batchId"]
        self.assertTrue(batch_id)
        snapshot = read_json(self.run_dir() / "decisions.json")
        self.assertEqual(snapshot["schemaVersion"], "pass-b-2")
        self.assertTrue(all(record["batchId"] == batch_id for record in snapshot["decisions"]))
        deleted = self.store.delete_decisions(self.run_id, batch_id=batch_id)
        self.assertEqual(len(deleted["deleted"]), len(ids))
        self.assertEqual(read_json(self.run_dir() / "decisions.json")["decisions"], [])
        log_tail = (self.run_dir() / "decisions-log.jsonl").read_text().strip().splitlines()[-1]
        self.assertIn('"deleted"', log_tail)

    def test_delete_by_ids_and_validation(self) -> None:
        self.select_defaults()
        candidate_id = self.zr1_candidate_ids()[0]
        self.store.save_decisions(
            self.run_id,
            [
                {
                    "model": "zr1",
                    "lane": "price",
                    "candidateId": candidate_id,
                    "action": "confirm_no_price",
                    "payload": {},
                    "resolution": "approved_for_plan",
                }
            ],
        )
        with self.assertRaises(WizardError):
            self.store.delete_decisions(self.run_id)
        deleted = self.store.delete_decisions(
            self.run_id, decision_ids=[f"zr1:price:{candidate_id}", "zr1:price:missing"]
        )
        self.assertEqual(deleted["deleted"], [f"zr1:price:{candidate_id}"])

    def test_delete_drops_completed_state(self) -> None:
        self.select_defaults()
        self.complete_model("zr1")
        self.complete_model("zr1x")
        self.store.mark_complete(self.run_id)
        candidate_id = self.zr1_candidate_ids()[0]
        result = self.store.delete_decisions(self.run_id, decision_ids=[f"zr1:section:{candidate_id}"])
        self.assertEqual(result["session"]["state"], STATE_DECISIONS_IN_PROGRESS)
        self.assertFalse(self.store.progress(self.run_id)["models"]["zr1"]["complete"])

    # ---------------------------------------------- b.2: reference / split
    def test_review_queue_carries_workbook_reference_and_split(self) -> None:
        self.select_defaults()
        queue = self.store.review_queue(self.run_id, "zr1", "section")
        # Fixture master has a live z06_options row for PDB; the fixture export
        # ZR1 sheet carries PDB, so the reference must surface it. Inactive
        # zr1_options source rows must be ignored.
        self.assertIn("PDB", queue["workbookReference"])
        references = queue["workbookReference"]["PDB"]
        # Exactly one match: the inactive zr1_options source (whose sheet exists
        # with a conflicting PDB row) must be excluded by the active filter.
        self.assertEqual(len(references), 1)
        reference = references[0]
        self.assertEqual(reference["modelKey"], "z06")
        self.assertEqual(reference["sectionName"], "Wheels")
        self.assertEqual(reference["optionName"], "Carbon Fiber Wheel Package")
        splits = self.store.review_queue(self.run_id, "zr1", "copy_split")
        for candidate in splits["candidates"]:
            self.assertIn("proposedSplit", candidate)
            self.assertIn("flags", candidate["proposedSplit"])

    # ------------------------------------------------------------ copying
    def test_copy_decisions_same_candidate_and_provenance(self) -> None:
        self.select_defaults()
        candidate_id = self.zr1_candidate_ids()[0]
        self.store.save_decisions(
            self.run_id,
            [
                {
                    "model": "zr1",
                    "lane": "section",
                    "candidateId": candidate_id,
                    "action": "assign_section",
                    "payload": {"sectionId": "sec_whee_001"},
                    "resolution": "approved_for_plan",
                }
            ],
        )
        report = self.store.copy_model_decisions(self.run_id, "zr1", "zr1x")
        self.assertEqual(report["copied"], 1)
        self.assertEqual(report["copiedByLane"], {"section": 1})
        queue = self.store.review_queue(self.run_id, "zr1x", "section")
        copied = queue["decisions"][0]
        # Mixed ZR1/ZR1X sheets share candidate rows: same candidateId, new model.
        self.assertEqual(copied["candidateId"], candidate_id)
        self.assertEqual(copied["model"], "zr1x")
        self.assertEqual(copied["copiedFrom"], "zr1")
        self.assertEqual(copied["payload"], {"sectionId": "sec_whee_001"})

    def test_copy_skips_existing_and_reports(self) -> None:
        self.select_defaults()
        candidate_id = self.zr1_candidate_ids()[0]
        decision = {
            "model": "zr1",
            "lane": "section",
            "candidateId": candidate_id,
            "action": "assign_section",
            "payload": {"sectionId": "sec_whee_001"},
            "resolution": "approved_for_plan",
        }
        self.store.save_decisions(self.run_id, [decision])
        existing = dict(decision, model="zr1x", payload={"sectionId": "sec_pain_001"})
        self.store.save_decisions(self.run_id, [existing])
        report = self.store.copy_model_decisions(self.run_id, "zr1", "zr1x")
        self.assertEqual(report["copied"], 0)
        self.assertEqual(report["skipped"][0]["reason"], "target_already_decided")
        # Target keeps its own decision.
        queue = self.store.review_queue(self.run_id, "zr1x", "section")
        self.assertEqual(queue["decisions"][0]["payload"], {"sectionId": "sec_pain_001"})
        # Overwrite flag replaces it.
        report = self.store.copy_model_decisions(self.run_id, "zr1", "zr1x", overwrite=True)
        self.assertEqual(report["copied"], 1)
        queue = self.store.review_queue(self.run_id, "zr1x", "section")
        self.assertEqual(queue["decisions"][0]["payload"], {"sectionId": "sec_whee_001"})

    def test_copy_presentation_swaps_model_key_and_group_copy(self) -> None:
        self.select_defaults()
        prefill = self.store.review_queue(self.run_id, "zr1", "presentation")["prefill"]
        rows = [p["row"] for p in prefill["sheets"]["runtime_steps"]]
        self.store.save_decisions(
            self.run_id,
            [
                {
                    "model": "zr1",
                    "lane": "presentation",
                    "groupKey": "runtime_steps",
                    "action": "approve_presentation_rows",
                    "payload": {"rows": rows, "templateModel": "z06"},
                    "resolution": "approved_for_plan",
                }
            ],
        )
        report = self.store.copy_model_decisions(self.run_id, "zr1", "zr1x")
        self.assertEqual(report["copiedByLane"], {"presentation": 1})
        queue = self.store.review_queue(self.run_id, "zr1x", "presentation")
        copied = queue["decisions"][0]
        self.assertTrue(all(row["model_key"] == "zr1x" for row in copied["payload"]["rows"]))

    def test_copy_validation(self) -> None:
        self.select_defaults()
        with self.assertRaises(WizardError):
            self.store.copy_model_decisions(self.run_id, "zr1", "zr1")
        with self.assertRaises(WizardError):
            self.store.copy_model_decisions(self.run_id, "zr1", "stingray")

    # ------------------------------------------------- b.4: field-note fixes
    def test_skip_section_saves_without_section_and_exempts_price(self) -> None:
        self.select_defaults()
        ids = self.zr1_candidate_ids()
        skipped_id = ids[0]
        # Skip — don't carry over: no sectionId, no price decision owed.
        self.store.save_decisions(
            self.run_id,
            [
                {
                    "model": "zr1",
                    "lane": "section",
                    "candidateId": skipped_id,
                    "action": "exclude_row",
                    "payload": {},
                    "resolution": "not_needed",
                }
            ],
        )
        for candidate_id in ids[1:]:
            self.store.save_decisions(
                self.run_id,
                [
                    {
                        "model": "zr1",
                        "lane": "section",
                        "candidateId": candidate_id,
                        "action": "assign_section",
                        "payload": {"sectionId": "sec_whee_001"},
                        "resolution": "approved_for_plan",
                    },
                    {
                        "model": "zr1",
                        "lane": "price",
                        "candidateId": candidate_id,
                        "action": "confirm_no_price",
                        "payload": {},
                        "resolution": "approved_for_plan",
                    },
                ],
            )
        progress = self.store.progress(self.run_id)
        zr1 = progress["models"]["zr1"]
        self.assertEqual(zr1["lanes"]["price"]["required"], len(ids) - 1)
        self.assertNotIn(
            skipped_id,
            [b.get("candidateId") for b in zr1["blockers"] if b["lane"] == "price"],
        )

    def test_se_queue_uses_model_scoped_availability(self) -> None:
        self.select_defaults()
        zr1_rpos = {
            c["refOnlyRpo"]
            for c in self.store.review_queue(self.run_id, "zr1", "standard_equipment")["candidates"]
        }
        zr1x_rpos = {
            c["refOnlyRpo"]
            for c in self.store.review_queue(self.run_id, "zr1x", "standard_equipment")["candidates"]
        }
        # XFR is available on ZR1 (an option, not SE) but not on ZR1X.
        self.assertNotIn("XFR", zr1_rpos)
        self.assertIn("XFR", zr1x_rpos)
        # AJ7 is standard on both — legitimate SE row.
        self.assertIn("AJ7", zr1_rpos)
        self.assertIn("AJ7", zr1x_rpos)

    def test_source_groups_fall_back_to_sheet_name(self) -> None:
        self.select_defaults()
        queue = self.store.review_queue(self.run_id, "zr1", "section")
        self.assertIn("Equipment Groups", queue["sourceSections"])
        # CC3 sits above any section-label row: it groups under the sheet name.
        self.assertIn("Equipment Groups 4", queue["sourceSections"])
        filtered = self.store.review_queue(
            self.run_id, "zr1", "section", source_section="Equipment Groups 4"
        )
        self.assertEqual([c["rpo"] for c in filtered["candidates"]], ["CC3"])

    def test_reconciliation_carries_scaffold_flag_and_decision(self) -> None:
        self.select_defaults()
        payload = self.store.reconciliation(self.run_id)
        zr1 = payload["models"]["zr1"]
        self.assertTrue(zr1["workbookHasScaffold"])
        self.assertIsNone(zr1["decision"])
        self.store.save_decisions(
            self.run_id,
            [
                {
                    "model": "zr1",
                    "lane": "relationship",
                    "groupKey": "variant_reconciliation",
                    "action": "confirm_export_variants",
                    "payload": {},
                    "resolution": "approved_for_plan",
                }
            ],
        )
        decided = self.store.reconciliation(self.run_id)["models"]["zr1"]["decision"]
        self.assertEqual(decided["action"], "confirm_export_variants")
        self.assertEqual(decided["decisionId"], "zr1:relationship:variant_reconciliation")

    def test_duplicate_proposed_names_flagged_in_split_queue(self) -> None:
        self.select_defaults()
        queue = self.store.review_queue(self.run_id, "zr1", "copy_split")
        by_rpo = {c["rpo"]: c["proposedSplit"] for c in queue["candidates"]}
        # CC3 and CC2 both propose "Roof panel" under the comma rule.
        self.assertEqual(by_rpo["CC3"]["name"], "Roof panel")
        self.assertEqual(by_rpo["CC2"]["name"], "Roof panel")
        self.assertIn("duplicate_proposed_name", by_rpo["CC3"]["flags"])
        self.assertIn("duplicate_proposed_name", by_rpo["CC2"]["flags"])
        self.assertNotIn("duplicate_proposed_name", by_rpo["PDB"]["flags"])

    def test_workbook_opened_read_only_and_untouched(self) -> None:
        before = self.master.read_bytes()
        self.select_defaults()
        self.store.review_queue(self.run_id, "zr1", "section")
        self.store.review_queue(self.run_id, "zr1", "presentation")
        self.assertEqual(self.master.read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
