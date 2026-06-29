#!/usr/bin/env python3
"""Server tests for Pass 2 read-only ingest review endpoints."""

from __future__ import annotations

import json
import sys
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = ROOT / "scripts"
TESTS_DIR = ROOT / "tests"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))
if str(TESTS_DIR) not in sys.path:
    sys.path.insert(0, str(TESTS_DIR))

import workbook_editor_server as srv  # noqa: E402
from corvette_form_generator.ingest.candidate_normalizer import normalize_order_guide_candidates  # noqa: E402
from corvette_form_generator.ingest.expert_interpreter import interpret_order_guide_candidates  # noqa: E402
from corvette_form_generator.ingest.review_payload import IngestReviewStore  # noqa: E402
from test_order_guide_candidate_normalizer import build_evidence  # noqa: E402
from test_order_guide_ingest_interpreter import build_candidates  # noqa: E402


class IngestReviewServerTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._tmp = tempfile.TemporaryDirectory()
        tmp = Path(cls._tmp.name)
        cls.workbook, cls.evidence_dir = build_evidence(tmp)
        cls.candidates_dir = tmp / "candidates"
        normalize_order_guide_candidates(
            evidence_dir=cls.evidence_dir,
            workbook=cls.workbook,
            output_dir=cls.candidates_dir,
            run_id="server-review",
            root=ROOT,
        )
        srv.EditorHandler.cache = srv.WorkbookCache(cls.workbook)
        srv.EditorHandler.ingest_review = IngestReviewStore(
            evidence_dir=cls.evidence_dir,
            candidates_dir=cls.candidates_dir,
            workbook_path=cls.workbook,
            workbook_mtime_ns=cls.workbook.stat().st_mtime_ns,
        )
        cls.mtime_before = cls.workbook.stat().st_mtime_ns
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), srv.EditorHandler)
        cls.port = cls.server.server_address[1]
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls) -> None:
        cls.server.shutdown()
        srv.EditorHandler.ingest_review = None
        cls._tmp.cleanup()

    def request(self, route: str, body: dict | None = None, method: str = "GET") -> tuple[int, dict]:
        data = None if body is None else json.dumps(body).encode()
        headers = {"Content-Type": "application/json"} if body is not None else {}
        req = urllib.request.Request(
            f"http://127.0.0.1:{self.port}{route}",
            data=data,
            headers=headers,
            method=method,
        )
        try:
            with urllib.request.urlopen(req) as resp:
                return resp.status, json.loads(resp.read())
        except urllib.error.HTTPError as err:
            return err.code, json.loads(err.read() or b"{}")

    def test_ingest_summary_and_lists_are_read_only(self) -> None:
        status, summary = self.request("/api/ingest/summary")
        self.assertEqual(status, 200)
        self.assertTrue(summary["enabled"])
        self.assertIn("unresolved-review.json", summary["candidate_artifacts"])

        status, options = self.request("/api/ingest/candidates?family=options&q=ERI")
        self.assertEqual(status, 200)
        self.assertEqual(options["family"], "options")
        self.assertTrue(options["items"])

        status, unresolved = self.request("/api/ingest/candidates?family=unresolved&reason=price_schedule_rows_not_extracted")
        self.assertEqual(status, 200)
        self.assertEqual(unresolved["items"][0]["category"], "price_out_of_scope")
        self.assertEqual(self.workbook.stat().st_mtime_ns, self.mtime_before)

    def test_detail_source_and_validation_endpoints(self) -> None:
        _status, options = self.request("/api/ingest/candidates?family=options&q=ERI")
        candidate_id = options["items"][0]["candidate_id"]
        status, detail = self.request(f"/api/ingest/candidate/{candidate_id}")
        self.assertEqual(status, 200)
        self.assertEqual(detail["candidate_id"], candidate_id)

        _status, unresolved = self.request("/api/ingest/candidates?family=unresolved&reason=target_rpo_token_ambiguous_or_missing")
        unresolved_id = unresolved["items"][0]["unresolved_id"]
        status, unresolved_detail = self.request(f"/api/ingest/unresolved/{unresolved_id}")
        self.assertEqual(status, 200)
        self.assertEqual(unresolved_detail["category"], "relationship_hint")

        status, source = self.request("/api/ingest/source?sheet=Exterior%201&row=5")
        self.assertEqual(status, 200)
        self.assertEqual(source["row"]["source_row_index"], 5)

        status, validation = self.request(
            "/api/ingest/review/validate",
            body={"decisions": [{
                "candidate_id": candidate_id,
                "candidate_family": "options",
                "decision_state": "skip",
                "source_refs": [],
            }]},
            method="POST",
        )
        self.assertEqual(status, 200)
        self.assertFalse(validation["ok"])
        self.assertIn("source_refs", validation["errors"][0])

    def test_interpretation_endpoints_are_read_only_and_preserve_raw_routes(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            workbook, evidence_dir, candidates_dir = build_candidates(tmp)
            interpretation_dir = tmp / "interpretation"
            interpret_order_guide_candidates(
                evidence_dir=evidence_dir,
                candidates_dir=candidates_dir,
                workbook=workbook,
                output_dir=interpretation_dir,
                run_id="server-interpretation",
                root=ROOT,
            )
            previous_store = srv.EditorHandler.ingest_review
            srv.EditorHandler.ingest_review = IngestReviewStore(
                evidence_dir=evidence_dir,
                candidates_dir=candidates_dir,
                interpretation_dir=interpretation_dir,
                workbook_path=workbook,
                workbook_mtime_ns=workbook.stat().st_mtime_ns,
            )
            mtime_before = workbook.stat().st_mtime_ns
            try:
                status, summary = self.request("/api/ingest/summary")
                self.assertEqual(status, 200)
                self.assertEqual(summary["mode"], "interpretation")
                self.assertTrue(summary["interpretation_enabled"])

                status, queue = self.request("/api/ingest/interpretations?limit=20")
                self.assertEqual(status, 200)
                self.assertEqual(queue["mode"], "interpretation")
                self.assertNotIn("auto_confirmed", {row["interpretation_confidence"] for row in queue["items"]})

                status, audit = self.request("/api/ingest/interpretations?include_auto=true&confidence=auto_confirmed&q=SAF")
                self.assertEqual(status, 200)
                self.assertTrue(audit["items"])
                interpretation_id = audit["items"][0]["interpretation_id"]

                status, detail = self.request(f"/api/ingest/interpretation/{interpretation_id}")
                self.assertEqual(status, 200)
                self.assertEqual(detail["rpo"], "SAF")
                self.assertIn("source_occurrences", detail)

                status, duplicates = self.request("/api/ingest/interpretation/reports/duplicates")
                self.assertEqual(status, 200)
                self.assertTrue(any(row["rpo"] == "DUP" for row in duplicates["items"]))
                status, coverage = self.request("/api/ingest/interpretation/reports/source-coverage")
                self.assertEqual(status, 200)
                self.assertIn("stingray", coverage["items"])

                status, raw_options = self.request("/api/ingest/candidates?family=options&q=SAF")
                self.assertEqual(status, 200)
                self.assertTrue(raw_options["items"])
                self.assertEqual(workbook.stat().st_mtime_ns, mtime_before)
            finally:
                srv.EditorHandler.ingest_review = previous_store

    def test_workbook_build_endpoints_are_read_only_and_filterable(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            workbook, evidence_dir = build_evidence(tmp)
            candidates_dir = tmp / "focused-candidates"
            normalize_order_guide_candidates(
                evidence_dir=evidence_dir,
                workbook=workbook,
                output_dir=candidates_dir,
                run_id="focused-server-candidates",
                root=ROOT,
                selected_models=["zr1"],
            )
            interpretation_dir = tmp / "focused-interpretation"
            interpret_order_guide_candidates(
                evidence_dir=evidence_dir,
                candidates_dir=candidates_dir,
                workbook=workbook,
                output_dir=interpretation_dir,
                run_id="focused-server-interpretation",
                root=ROOT,
                selected_models=["zr1"],
                primary_models=["zr1"],
            )
            previous_store = srv.EditorHandler.ingest_review
            srv.EditorHandler.ingest_review = IngestReviewStore(
                evidence_dir=evidence_dir,
                candidates_dir=candidates_dir,
                interpretation_dir=interpretation_dir,
                workbook_path=workbook,
                workbook_mtime_ns=workbook.stat().st_mtime_ns,
            )
            mtime_before = workbook.stat().st_mtime_ns
            try:
                status, selection = self.request("/api/ingest/workbook-build/selection")
                self.assertEqual(status, 200)
                self.assertEqual(selection["selected_models"], ["zr1"])

                status, summary = self.request("/api/ingest/workbook-build/summary")
                self.assertEqual(status, 200)
                self.assertEqual(summary["review_mode"], "focused_workbook_build")

                status, units = self.request("/api/ingest/workbook-build/units?lane=option_rows&model=zr1&q=TOM")
                self.assertEqual(status, 200)
                self.assertTrue(units["items"])
                review_unit_id = units["items"][0]["review_unit_id"]

                status, detail = self.request(f"/api/ingest/workbook-build/unit/{review_unit_id}")
                self.assertEqual(status, 200)
                self.assertEqual(detail["review_unit_id"], review_unit_id)

                status, validation = self.request(
                    "/api/ingest/workbook-build/validate",
                    body={
                        "version": 3,
                        "review_mode": "workbook_build",
                        "selection_fingerprint": summary["selection_fingerprint"],
                        "workbook_build_decisions": [{
                            "review_unit_id": review_unit_id,
                            "decision_state": "accept_for_later_apply",
                        }],
                    },
                    method="POST",
                )
                self.assertEqual(status, 200)
                self.assertFalse(validation["ok"])
                self.assertIn("invalid decision_state", "\n".join(validation["errors"]))
                self.assertEqual(workbook.stat().st_mtime_ns, mtime_before)
            finally:
                srv.EditorHandler.ingest_review = previous_store


if __name__ == "__main__":
    unittest.main()
