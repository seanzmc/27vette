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
from corvette_form_generator.ingest.review_payload import (  # noqa: E402
    IngestReviewStore,
    validate_review_decisions,
)
from test_order_guide_candidate_normalizer import build_evidence  # noqa: E402


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

    def test_summary_contains_artifact_fingerprints_and_counts(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            store = self.build_store(Path(tmpdir))

            summary = store.summary()

            self.assertTrue(summary["enabled"])
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


if __name__ == "__main__":
    unittest.main()
