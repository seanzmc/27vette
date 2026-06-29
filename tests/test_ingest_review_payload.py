#!/usr/bin/env python3
"""Tests for the Pass 2 ingest review payload builder."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = ROOT / "scripts"
TESTS_DIR = ROOT / "tests"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))
if str(TESTS_DIR) not in sys.path:
    sys.path.insert(0, str(TESTS_DIR))

from corvette_form_generator.ingest.candidate_normalizer import normalize_order_guide_candidates  # noqa: E402
from corvette_form_generator.ingest.expert_interpreter import interpret_order_guide_candidates  # noqa: E402
from corvette_form_generator.ingest.review_payload import (  # noqa: E402
    IngestReviewStore,
    validate_review_decisions,
)
from test_order_guide_candidate_normalizer import build_evidence  # noqa: E402
from test_order_guide_ingest_interpreter import build_candidates  # noqa: E402


class IngestReviewPayloadTests(unittest.TestCase):
    def build_store(self, tmp: Path) -> IngestReviewStore:
        workbook, evidence_dir = build_evidence(tmp)
        candidates_dir = tmp / "candidates"
        normalize_order_guide_candidates(
            evidence_dir=evidence_dir,
            workbook=workbook,
            output_dir=candidates_dir,
            run_id="unit-review",
            root=ROOT,
        )
        return IngestReviewStore(
            evidence_dir=evidence_dir,
            candidates_dir=candidates_dir,
            workbook_path=workbook,
            workbook_mtime_ns=workbook.stat().st_mtime_ns,
        )

    def build_interpretation_store(self, tmp: Path) -> IngestReviewStore:
        workbook, evidence_dir, candidates_dir = build_candidates(tmp)
        interpretation_dir = tmp / "interpretation"
        interpret_order_guide_candidates(
            evidence_dir=evidence_dir,
            candidates_dir=candidates_dir,
            workbook=workbook,
            output_dir=interpretation_dir,
            run_id="unit-interpretation-review",
            root=ROOT,
        )
        return IngestReviewStore(
            evidence_dir=evidence_dir,
            candidates_dir=candidates_dir,
            interpretation_dir=interpretation_dir,
            workbook_path=workbook,
            workbook_mtime_ns=workbook.stat().st_mtime_ns,
        )

    def build_workbook_build_store(self, tmp: Path) -> IngestReviewStore:
        workbook, evidence_dir = build_evidence(tmp)
        candidates_dir = tmp / "focused-candidates"
        normalize_order_guide_candidates(
            evidence_dir=evidence_dir,
            workbook=workbook,
            output_dir=candidates_dir,
            run_id="focused-candidates",
            root=ROOT,
            selected_models=["zr1"],
        )
        interpretation_dir = tmp / "focused-interpretation"
        interpret_order_guide_candidates(
            evidence_dir=evidence_dir,
            candidates_dir=candidates_dir,
            workbook=workbook,
            output_dir=interpretation_dir,
            run_id="focused-interpretation",
            root=ROOT,
            selected_models=["zr1"],
            primary_models=["zr1"],
        )
        return IngestReviewStore(
            evidence_dir=evidence_dir,
            candidates_dir=candidates_dir,
            interpretation_dir=interpretation_dir,
            workbook_path=workbook,
            workbook_mtime_ns=workbook.stat().st_mtime_ns,
        )

    def test_summary_contains_artifact_fingerprints_and_counts(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            store = self.build_store(Path(tmpdir))

            summary = store.summary()

            self.assertTrue(summary["enabled"])
            self.assertEqual(summary["mode"], "raw_candidates")
            self.assertFalse(summary["interpretation_enabled"])
            self.assertEqual(summary["candidate_summary"]["candidate_counts"]["price_rules"], 0)
            self.assertIn("candidate-summary.json", summary["candidate_artifacts"])
            self.assertIn("manifest.json", summary["evidence_artifacts"])
            candidate_fp = summary["candidate_artifacts"]["unresolved-review.json"]
            self.assertGreater(candidate_fp["size_bytes"], 0)
            self.assertRegex(candidate_fp["sha256"], r"^[0-9a-f]{64}$")
            self.assertIn("price_schedule_rows_not_extracted", summary["unresolved_counts"])

    def test_lists_candidates_and_unresolved_without_markdown(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            store = self.build_store(Path(tmpdir))

            options = store.list_candidates(family="options", q="ERI", limit=10)
            self.assertEqual(options["family"], "options")
            self.assertTrue(any(row["normalized_values"]["rpo"] == "ERI" for row in options["items"]))
            unresolved = store.list_candidates(family="unresolved", reason="price_schedule_rows_not_extracted", limit=10)
            self.assertEqual(unresolved["family"], "unresolved")
            self.assertEqual(unresolved["items"][0]["category"], "price_out_of_scope")
            self.assertIn("source_refs", unresolved["items"][0])

    def test_interpretation_summary_queue_reports_and_raw_drilldown(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            store = self.build_interpretation_store(Path(tmpdir))

            summary = store.summary()

            self.assertEqual(summary["mode"], "interpretation")
            self.assertTrue(summary["interpretation_enabled"])
            self.assertIn("interpretation-summary.json", summary["interpretation_artifacts"])
            self.assertEqual(summary["interpretation_summary"]["interpreted_option_count"], 6)
            self.assertEqual(summary["interpretation_summary"]["hidden_auto_confirmed_count"], 2)

            queue = store.list_interpretations(limit=20)
            self.assertEqual(queue["mode"], "interpretation")
            self.assertNotIn("auto_confirmed", {row["interpretation_confidence"] for row in queue["items"]})
            self.assertIn("ADI", {row["rpo"] for row in queue["items"]})

            auto = store.list_interpretations(include_auto=True, confidence="auto_confirmed", q="SAF", limit=20)
            self.assertTrue(any(row["rpo"] == "SAF" for row in auto["items"]))
            duplicate = store.list_interpretations(include_auto=True, duplicate="redundant_duplicates", limit=20)
            self.assertTrue(any(row["rpo"] == "DUP" for row in duplicate["items"]))
            reason = store.list_interpretations(reason="dealer_installed_or_adi", limit=20)
            self.assertEqual({row["rpo"] for row in reason["items"]}, {"ADI"})

            detail = store.interpretation(auto["items"][0]["interpretation_id"])
            self.assertEqual(detail["rpo"], "SAF")
            self.assertIn("source_occurrences", detail)
            self.assertIn("workbook_identity_match", detail)
            self.assertIn("workbook_status_match", detail)

            reports = store.interpretation_reports()
            self.assertTrue(any(row["rpo"] == "DUP" for row in reports["duplicates"]))
            self.assertIn("stingray", reports["source_coverage"])

            raw_options = store.list_candidates(family="options", q="SAF", limit=10)
            self.assertTrue(any(row["normalized_values"]["rpo"] == "SAF" for row in raw_options["items"]))

    def test_candidate_unresolved_source_and_decision_validation(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            store = self.build_store(Path(tmpdir))
            option_list = store.list_candidates(family="options", q="ERI", limit=1)
            candidate = store.candidate(option_list["items"][0]["candidate_id"])
            unresolved_list = store.list_candidates(family="unresolved", reason="target_rpo_token_ambiguous_or_missing", limit=1)
            unresolved = store.unresolved(unresolved_list["items"][0]["unresolved_id"])
            source = store.source(sheet="Exterior 1", row=5)

            self.assertEqual(candidate["candidate_family"], "options")
            self.assertEqual(unresolved["category"], "relationship_hint")
            self.assertEqual(source["row"]["source_row_index"], 5)
            decisions = {
                "version": 1,
                "decisions": [{
                    "candidate_id": candidate["candidate_id"],
                    "candidate_family": "options",
                    "decision_state": "accept_for_later_apply",
                    "reviewer_notes": "fixture",
                    "source_refs": candidate["source_refs"],
                    "raw_values_snapshot": candidate["raw_values"],
                    "normalized_values_snapshot": candidate["normalized_values"],
                    "workbook_match_snapshot": candidate["workbook_match"],
                }],
                "unresolved_decisions": [{
                    "unresolved_id": unresolved["unresolved_id"],
                    "reason": unresolved["reason"],
                    "category": unresolved["category"],
                    "decision_state": "needs_source_review",
                    "reviewer_notes": "fixture",
                    "source_refs": unresolved["source_refs"],
                    "raw_values_snapshot": unresolved["raw_values"],
                    "normalized_values_snapshot": unresolved["normalized_values"],
                    "candidate_refs": unresolved["candidate_refs"],
                }],
            }
            self.assertEqual(validate_review_decisions(decisions)["errors"], [])
            decisions["decisions"][0]["source_refs"] = []
            self.assertIn("source_refs", validate_review_decisions(decisions)["errors"][0])

    def test_interpretation_decision_validation_is_versioned_and_strict(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            store = self.build_interpretation_store(Path(tmpdir))
            row = store.list_interpretations(limit=1)["items"][0]
            detail = store.interpretation(row["interpretation_id"])
            payload = {
                "version": 2,
                "review_mode": "interpretation",
                "interpretation_decisions": [{
                    "interpretation_id": detail["interpretation_id"],
                    "model_key": detail["model_key"],
                    "rpo": detail["rpo"],
                    "interpretation_confidence": detail["interpretation_confidence"],
                    "decision_state": "needs_source_review",
                    "reviewer_notes": "fixture",
                    "review_reason_codes": detail["review_reason_codes"],
                    "source_occurrences_snapshot": detail["source_occurrences"],
                    "availability_matrix_snapshot": detail["availability_matrix"],
                    "workbook_identity_match_snapshot": detail["workbook_identity_match"],
                    "workbook_status_match_snapshot": detail["workbook_status_match"],
                    "duplicate_classification_snapshot": detail["duplicate_classification"],
                }],
            }

            self.assertEqual(validate_review_decisions(payload)["errors"], [])
            payload["interpretation_decisions"][0]["source_occurrences_snapshot"] = []
            self.assertIn("source_occurrences_snapshot", validate_review_decisions(payload)["errors"][0])
            payload["interpretation_decisions"][0]["source_occurrences_snapshot"] = detail["source_occurrences"]
            payload["interpretation_decisions"][0]["decision_state"] = "apply_now"
            self.assertIn("invalid decision_state", validate_review_decisions(payload)["errors"][0])

    def test_workbook_build_store_lists_units_and_validates_required_selection_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            store = self.build_workbook_build_store(Path(tmpdir))

            summary = store.summary()
            self.assertEqual(summary["mode"], "workbook_build")
            self.assertTrue(summary["workbook_build_enabled"])
            self.assertEqual(summary["model_selection"]["selected_models"], ["zr1"])
            self.assertIn("workbook-build-summary.json", summary["interpretation_artifacts"])

            option_units = store.list_workbook_build_units(lane="option_rows", model="zr1", limit=10)
            self.assertEqual(option_units["mode"], "workbook_build")
            self.assertEqual(option_units["lane"], "option_rows")
            self.assertTrue(any(row["rpo"] == "TOM" for row in option_units["items"]))
            detail = store.workbook_build_unit(option_units["items"][0]["review_unit_id"])
            self.assertEqual(detail["target_sheet"], "zr1_options")
            self.assertIn(detail["proposed_workbook_action"], {"create_option_row", "verify_existing_option_row"})

            ovs_units = store.list_workbook_build_units(lane="ovs_rows", action="verify_status_matrix", limit=10)
            self.assertTrue(any(row["rpo"] == "TOM" for row in ovs_units["items"]))

            validation = store.validate_workbook_build_decisions({
                "version": 3,
                "review_mode": "workbook_build",
                "selection_fingerprint": summary["workbook_build_summary"]["selection_fingerprint"],
                "workbook_build_decisions": [{
                    "review_unit_id": detail["review_unit_id"],
                    "lane": detail["lane"],
                    "model_key": detail["model_key"],
                    "rpo": detail["rpo"],
                    "target_sheet": detail["target_sheet"],
                    "proposed_workbook_action": detail["proposed_workbook_action"],
                    "decision_state": "ready_for_apply_plan",
                    "reviewer_notes": "source evidence checked",
                    "source_refs_snapshot": detail["source_refs"],
                    "raw_source_snapshot": detail["raw_source_snapshot"],
                    "workbook_presence_snapshot": detail["workbook_presence"],
                }],
            })
            self.assertEqual(validation["errors"], [])
            self.assertTrue(validation["ok"])

            bad = store.validate_workbook_build_decisions({
                "version": 3,
                "review_mode": "workbook_build",
                "selection_fingerprint": "wrong",
                "workbook_build_decisions": [{"review_unit_id": detail["review_unit_id"], "decision_state": "accept_for_later_apply"}],
            })
            self.assertFalse(bad["ok"])
            self.assertTrue(any("selection_fingerprint" in error for error in bad["errors"]))
            self.assertTrue(any("invalid decision_state" in error for error in bad["errors"]))


if __name__ == "__main__":
    unittest.main()
