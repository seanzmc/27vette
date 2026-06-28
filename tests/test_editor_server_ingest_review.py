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
from corvette_form_generator.ingest.review_payload import IngestReviewStore  # noqa: E402
from test_order_guide_candidate_normalizer import build_evidence  # noqa: E402


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


if __name__ == "__main__":
    unittest.main()
