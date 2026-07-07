#!/usr/bin/env python3
"""HTTP API tests for the ingest wizard server Pass B endpoints."""

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
for entry in (ROOT / "scripts", ROOT / "tests"):
    if str(entry) not in sys.path:
        sys.path.insert(0, str(entry))

import ingest_wizard_server as srv  # noqa: E402
from corvette_form_generator.ingest.wizard.session import WizardSessionStore  # noqa: E402
from ingest_wizard_fixtures import build_master_workbook, build_raw_export  # noqa: E402


class WizardServerPassBTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._tmp = tempfile.TemporaryDirectory()
        cls.root = Path(cls._tmp.name)
        build_raw_export(cls.root / "raw.xlsx")
        master = build_master_workbook(cls.root / "master.xlsx")
        srv.WizardHandler.store = WizardSessionStore(cls.root, workbook_path=master)
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), srv.WizardHandler)
        cls.port = cls.server.server_address[1]
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls) -> None:
        cls.server.shutdown()
        cls._tmp.cleanup()

    def request(self, method: str, path: str, body: bytes | None = None) -> tuple[int, dict]:
        request = urllib.request.Request(
            f"http://127.0.0.1:{self.port}{path}", data=body, method=method
        )
        if body is not None:
            request.add_header("Content-Type", "application/json")
        try:
            with urllib.request.urlopen(request) as response:
                return response.status, json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as error:
            return error.code, json.loads(error.read().decode("utf-8"))

    def post_json(self, path: str, payload: dict) -> tuple[int, dict]:
        return self.request("POST", path, json.dumps(payload).encode("utf-8"))

    def start_parsed_run(self) -> str:
        status, created = self.post_json("/api/wizard/sessions", {"file": "raw.xlsx"})
        self.assertEqual(status, 200)
        run_id = created["session"]["runId"]
        roles = {card["sheetName"]: card["recommendedRole"] for card in created["profile"]["sheets"]}
        status, _ = self.post_json(f"/api/wizard/sessions/{run_id}/roles", {"roles": roles})
        self.assertEqual(status, 200)
        status, _ = self.post_json(f"/api/wizard/sessions/{run_id}/parse", {})
        self.assertEqual(status, 200)
        return run_id

    def test_pass_b_flow_over_http(self) -> None:
        run_id = self.start_parsed_run()

        status, models = self.request("GET", f"/api/wizard/sessions/{run_id}/models")
        self.assertEqual(status, 200)
        keys = {model["modelKey"] for model in models["models"]}
        self.assertLessEqual({"zr1", "zr1x"}, keys)

        status, selected = self.post_json(
            f"/api/wizard/sessions/{run_id}/models",
            {"targets": ["zr1", "zr1x"], "comparators": {"zr1": "z06", "zr1x": "z06"}},
        )
        self.assertEqual(status, 200)
        self.assertEqual(selected["session"]["state"], "models_selected")
        self.assertIn("zr1", selected["reconciliation"]["models"])

        status, reconciliation = self.request(
            "GET", f"/api/wizard/sessions/{run_id}/reconciliation"
        )
        self.assertEqual(status, 200)
        self.assertTrue(reconciliation["models"]["zr1x"]["agrees"])

        status, queue = self.request(
            "GET", f"/api/wizard/sessions/{run_id}/review?model=zr1&lane=section"
        )
        self.assertEqual(status, 200)
        self.assertTrue(queue["candidates"])
        self.assertTrue(queue["sections"])
        candidate_id = queue["candidates"][0]["candidateId"]

        status, saved = self.post_json(
            f"/api/wizard/sessions/{run_id}/decisions",
            {
                "decisions": [
                    {
                        "model": "zr1",
                        "lane": "section",
                        "candidateId": candidate_id,
                        "action": "assign_section",
                        "payload": {"sectionId": "sec_whee_001"},
                        "resolution": "approved_for_plan",
                    }
                ]
            },
        )
        self.assertEqual(status, 200)
        self.assertEqual(saved["session"]["state"], "decisions_in_progress")

        status, progress = self.request("GET", f"/api/wizard/sessions/{run_id}/progress")
        self.assertEqual(status, 200)
        self.assertFalse(progress["allComplete"])

        status, blocked = self.post_json(f"/api/wizard/sessions/{run_id}/complete", {})
        self.assertEqual(status, 409)
        self.assertIn("blocking items remain", blocked["error"])

        status, detail = self.request("GET", f"/api/wizard/sessions/{run_id}")
        self.assertEqual(status, 200)
        self.assertEqual(detail["modelSelection"]["targets"], ["zr1", "zr1x"])

    def test_copy_decisions_endpoint_and_source_section_filter(self) -> None:
        run_id = self.start_parsed_run()
        self.post_json(
            f"/api/wizard/sessions/{run_id}/models",
            {"targets": ["zr1", "zr1x"], "comparators": {"zr1": "z06", "zr1x": "z06"}},
        )
        status, queue = self.request(
            "GET", f"/api/wizard/sessions/{run_id}/review?model=zr1&lane=section"
        )
        self.assertEqual(status, 200)
        self.assertIn("Equipment Groups", queue["sourceSections"])
        status, filtered = self.request(
            "GET",
            f"/api/wizard/sessions/{run_id}/review?model=zr1&lane=section&sourceSection=No%20Such%20Section",
        )
        self.assertEqual(status, 200)
        self.assertEqual(filtered["candidates"], [])

        candidate_id = queue["candidates"][0]["candidateId"]
        self.post_json(
            f"/api/wizard/sessions/{run_id}/decisions",
            {
                "decisions": [
                    {
                        "model": "zr1",
                        "lane": "section",
                        "candidateId": candidate_id,
                        "action": "assign_section",
                        "payload": {"sectionId": "sec_whee_001"},
                        "resolution": "approved_for_plan",
                    }
                ]
            },
        )
        status, copied = self.post_json(
            f"/api/wizard/sessions/{run_id}/copy-decisions",
            {"fromModel": "zr1", "toModel": "zr1x"},
        )
        self.assertEqual(status, 200)
        self.assertEqual(copied["copied"], 1)
        self.assertEqual(copied["copiedByLane"], {"section": 1})
        status, payload = self.post_json(
            f"/api/wizard/sessions/{run_id}/copy-decisions", {"fromModel": "zr1"}
        )
        self.assertEqual(status, 400)
        self.assertIn("toModel", payload["error"])

    def test_review_decision_state_filter_and_section_skip(self) -> None:
        run_id = self.start_parsed_run()
        self.post_json(
            f"/api/wizard/sessions/{run_id}/models",
            {"targets": ["zr1", "zr1x"], "comparators": {"zr1": "z06", "zr1x": "z06"}},
        )
        status, queue = self.request(
            "GET", f"/api/wizard/sessions/{run_id}/review?model=zr1&lane=section"
        )
        self.assertEqual(status, 200)
        ids = [candidate["candidateId"] for candidate in queue["candidates"][:2]]
        self.assertEqual(len(ids), 2)

        status, saved = self.post_json(
            f"/api/wizard/sessions/{run_id}/decisions",
            {
                "decisions": [
                    {
                        "model": "zr1",
                        "lane": "section",
                        "candidateId": ids[0],
                        "action": "exclude_row",
                        "payload": {},
                        "resolution": "not_needed",
                    },
                    {
                        "model": "zr1",
                        "lane": "section",
                        "candidateId": ids[1],
                        "action": "assign_section",
                        "payload": {"sectionId": "sec_whee_001"},
                        "resolution": "approved_for_plan",
                    },
                    {
                        "model": "zr1",
                        "lane": "price",
                        "candidateId": ids[0],
                        "action": "confirm_no_price",
                        "payload": {},
                        "resolution": "approved_for_plan",
                    },
                    {
                        "model": "zr1",
                        "lane": "price",
                        "candidateId": ids[1],
                        "action": "confirm_no_price",
                        "payload": {},
                        "resolution": "approved_for_plan",
                    },
                ]
            },
        )
        self.assertEqual(status, 200)
        self.assertTrue(saved["batchId"])

        status, undecided_section = self.request(
            "GET",
            f"/api/wizard/sessions/{run_id}/review?model=zr1&lane=section&decisionState=undecided",
        )
        self.assertEqual(status, 200)
        undecided_section_ids = {candidate["candidateId"] for candidate in undecided_section["candidates"]}
        self.assertNotIn(ids[0], undecided_section_ids)
        self.assertNotIn(ids[1], undecided_section_ids)

        status, decided_section = self.request(
            "GET",
            f"/api/wizard/sessions/{run_id}/review?model=zr1&lane=section&decisionState=decided",
        )
        self.assertEqual(status, 200)
        decided_section_ids = {candidate["candidateId"] for candidate in decided_section["candidates"]}
        self.assertLessEqual(set(ids), decided_section_ids)

        status, undecided_price = self.request(
            "GET",
            f"/api/wizard/sessions/{run_id}/review?model=zr1&lane=price&decisionState=undecided",
        )
        self.assertEqual(status, 200)
        undecided_price_ids = {candidate["candidateId"] for candidate in undecided_price["candidates"]}
        self.assertNotIn(ids[0], undecided_price_ids)  # skipped in section, no price decision owed
        self.assertNotIn(ids[1], undecided_price_ids)  # has a price decision

        status, decided_price = self.request(
            "GET",
            f"/api/wizard/sessions/{run_id}/review?model=zr1&lane=price&decisionState=decided",
        )
        self.assertEqual(status, 200)
        decided_price_ids = {candidate["candidateId"] for candidate in decided_price["candidates"]}
        self.assertNotIn(ids[0], decided_price_ids)
        self.assertIn(ids[1], decided_price_ids)

        for lane in ("price", "copy_split", "relationship", "duplicate"):
            status, later_queue = self.request(
                "GET", f"/api/wizard/sessions/{run_id}/review?model=zr1&lane={lane}"
            )
            self.assertEqual(status, 200, lane)
            later_ids = {candidate["candidateId"] for candidate in later_queue["candidates"]}
            self.assertNotIn(ids[0], later_ids, lane)

        status, payload = self.request(
            "GET",
            f"/api/wizard/sessions/{run_id}/review?model=zr1&lane=section&decisionState=nope",
        )
        self.assertEqual(status, 400)
        self.assertIn("Invalid decision state", payload["error"])

    def test_delete_endpoint_and_batch_undo(self) -> None:
        run_id = self.start_parsed_run()
        self.post_json(
            f"/api/wizard/sessions/{run_id}/models",
            {"targets": ["zr1", "zr1x"], "comparators": {"zr1": "z06", "zr1x": "z06"}},
        )
        status, queue = self.request(
            "GET", f"/api/wizard/sessions/{run_id}/review?model=zr1&lane=section"
        )
        ids = [candidate["candidateId"] for candidate in queue["candidates"][:2]]
        status, saved = self.post_json(
            f"/api/wizard/sessions/{run_id}/decisions",
            {
                "decisions": [
                    {
                        "model": "zr1",
                        "lane": "section",
                        "candidateId": candidate_id,
                        "action": "assign_section",
                        "payload": {"sectionId": "sec_whee_001"},
                        "resolution": "approved_for_plan",
                    }
                    for candidate_id in ids
                ]
            },
        )
        self.assertEqual(status, 200)
        self.assertTrue(saved["batchId"])
        status, deleted = self.post_json(
            f"/api/wizard/sessions/{run_id}/decisions/delete", {"batchId": saved["batchId"]}
        )
        self.assertEqual(status, 200)
        self.assertEqual(len(deleted["deleted"]), 2)
        status, payload = self.post_json(f"/api/wizard/sessions/{run_id}/decisions/delete", {})
        self.assertEqual(status, 400)
        status, payload = self.post_json(
            f"/api/wizard/sessions/{run_id}/decisions/delete", {"decisionIds": "x"}
        )
        self.assertEqual(status, 400)

    def test_pass_b_error_mapping(self) -> None:
        run_id = self.start_parsed_run()
        status, payload = self.post_json(
            f"/api/wizard/sessions/{run_id}/models", {"targets": "zr1"}
        )
        self.assertEqual(status, 400)
        self.assertIn("targets", payload["error"])
        status, payload = self.request("GET", f"/api/wizard/sessions/{run_id}/review?model=zr1&lane=section")
        self.assertEqual(status, 400)
        self.assertIn("Select target models", payload["error"])
        status, payload = self.post_json(f"/api/wizard/sessions/{run_id}/decisions", {"decisions": "x"})
        self.assertEqual(status, 400)


if __name__ == "__main__":
    unittest.main()
