#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
import tempfile
import threading
import unittest
import urllib.error
import urllib.parse
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

ROLES = {
    "Exterior 1": "exclude",
    "Mechanical 4": "options",
    "Price Schedule": "price",
    "Standard Equipment 1": "exclude",
    "Color and Trim 1": "exclude",
}


class WizardServerMilestone2Test(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._tmp = tempfile.TemporaryDirectory()
        cls.root = Path(cls._tmp.name)
        build_raw_export(cls.root / "raw.xlsx")
        master = build_master_workbook(cls.root / "stingray_master.xlsx")
        srv.WizardHandler.store = WizardSessionStore(cls.root, workbook_path=master)
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), srv.WizardHandler)
        cls.port = cls.server.server_address[1]
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls) -> None:
        cls.server.shutdown()
        cls._tmp.cleanup()

    def request(self, method: str, path: str, payload: dict | None = None) -> tuple[int, dict]:
        body = json.dumps(payload).encode("utf-8") if payload is not None else None
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

    def start_models_run(self) -> str:
        status, created = self.request("POST", "/api/wizard/sessions", {"file": "raw.xlsx"})
        self.assertEqual(status, 200)
        run_id = created["session"]["runId"]
        self.assertEqual(
            self.request("POST", f"/api/wizard/sessions/{run_id}/roles", {"roles": ROLES})[0],
            200,
        )
        self.assertEqual(
            self.request("POST", f"/api/wizard/sessions/{run_id}/parse", {})[0],
            200,
        )
        status, selected = self.request(
            "POST",
            f"/api/wizard/sessions/{run_id}/models",
            {"targets": ["zr1"], "comparators": {"zr1": "z06"}},
        )
        self.assertEqual(status, 200)
        self.assertEqual(selected["session"]["state"], "models_selected")
        return run_id

    def test_compile_post_and_compact_get(self) -> None:
        run_id = self.start_models_run()

        status, compiled = self.request(
            "POST", f"/api/wizard/sessions/{run_id}/compile", {}
        )
        self.assertEqual(status, 200)
        self.assertEqual(compiled["session"]["state"], "compiled_with_exceptions")
        self.assertIn("models", compiled)
        self.assertNotIn("manifest", compiled)

        status, summary = self.request(
            "GET", f"/api/wizard/sessions/{run_id}/compile"
        )
        self.assertEqual(status, 200)
        self.assertEqual(summary["session"]["runId"], run_id)
        self.assertIn("exceptions", summary["counts"])

    def test_exception_get_resolve_and_reopen(self) -> None:
        run_id = self.start_models_run()
        self.assertEqual(
            self.request("POST", f"/api/wizard/sessions/{run_id}/compile", {})[0],
            200,
        )
        query = urllib.parse.urlencode(
            {"reason": "missing_section", "state": "open", "actionable": "yes", "limit": 1}
        )
        status, queue = self.request(
            "GET", f"/api/wizard/sessions/{run_id}/exceptions?{query}"
        )
        self.assertEqual(status, 200)
        subject = queue["items"][0]["subject"]
        self.assertIn("presentation", queue["items"][0])
        self.assertNotIn("presentation", subject)

        status, resolved = self.request(
            "POST",
            f"/api/wizard/sessions/{run_id}/exceptions/resolve",
            {
                "subjectId": subject["subjectId"],
                "subjectVersion": subject["subjectVersion"],
                "action": "choose_section",
                "payload": {"sectionId": "sec_whee_001"},
                "reviewer": "sean",
            },
        )
        self.assertEqual(status, 200)
        self.assertEqual(resolved["subject"]["state"], "resolved")

        status, reopened = self.request(
            "POST",
            f"/api/wizard/sessions/{run_id}/exceptions/reopen",
            {
                "subjectId": subject["subjectId"],
                "subjectVersion": subject["subjectVersion"],
                "reviewer": "sean",
            },
        )
        self.assertEqual(status, 200)
        self.assertEqual(reopened["subject"]["state"], "open")

    def test_resolution_endpoint_rejects_read_only_presentation_payload(self) -> None:
        run_id = self.start_models_run()
        self.assertEqual(
            self.request("POST", f"/api/wizard/sessions/{run_id}/compile", {})[0],
            200,
        )
        query = urllib.parse.urlencode(
            {"reason": "missing_section", "state": "open", "actionable": "yes", "limit": 1}
        )
        item = self.request(
            "GET", f"/api/wizard/sessions/{run_id}/exceptions?{query}"
        )[1]["items"][0]

        status, response = self.request(
            "POST",
            f"/api/wizard/sessions/{run_id}/exceptions/resolve",
            {
                "subjectId": item["subject"]["subjectId"],
                "subjectVersion": item["subject"]["subjectVersion"],
                "action": "choose_section",
                "payload": {"sectionId": "sec_whee_001"},
                "reviewer": "sean",
                "presentation": item["presentation"],
            },
        )

        self.assertEqual(status, 400)
        self.assertIn("unknown fields", response["error"])

    def test_exception_preview_endpoint_is_strict_and_side_effect_free(self) -> None:
        run_id = self.start_models_run()
        self.assertEqual(
            self.request("POST", f"/api/wizard/sessions/{run_id}/compile", {})[0],
            200,
        )
        query = urllib.parse.urlencode(
            {"reason": "missing_section", "state": "open", "actionable": "yes", "limit": 1}
        )
        subject = self.request(
            "GET", f"/api/wizard/sessions/{run_id}/exceptions?{query}"
        )[1]["items"][0]["subject"]

        status, preview = self.request(
            "POST",
            f"/api/wizard/sessions/{run_id}/exceptions/preview",
            {
                "subjectId": subject["subjectId"],
                "subjectVersion": subject["subjectVersion"],
                "action": "choose_section",
                "payload": {"sectionId": "sec_whee_001"},
            },
        )
        self.assertEqual(status, 200)
        self.assertEqual(preview["subjectId"], subject["subjectId"])
        self.assertTrue(preview["decisionEffect"]["rows"])

        status, response = self.request(
            "POST",
            f"/api/wizard/sessions/{run_id}/exceptions/preview",
            {
                "subjectId": subject["subjectId"],
                "subjectVersion": subject["subjectVersion"],
                "action": "choose_section",
                "payload": {"sectionId": "sec_whee_001"},
                "reviewer": "not-accepted-for-preview",
            },
        )
        self.assertEqual(status, 400)
        self.assertIn("unknown fields", response["error"])

    def test_resolution_endpoint_rejects_unknown_top_level_fields(self) -> None:
        run_id = self.start_models_run()
        self.assertEqual(
            self.request("POST", f"/api/wizard/sessions/{run_id}/compile", {})[0],
            200,
        )
        query = urllib.parse.urlencode(
            {"reason": "missing_section", "state": "open", "actionable": "yes", "limit": 1}
        )
        subject = self.request(
            "GET", f"/api/wizard/sessions/{run_id}/exceptions?{query}"
        )[1]["items"][0]["subject"]

        status, response = self.request(
            "POST",
            f"/api/wizard/sessions/{run_id}/exceptions/resolve",
            {
                "subjectId": subject["subjectId"],
                "subjectVersion": subject["subjectVersion"],
                "action": "choose_section",
                "payload": {"sectionId": "sec_whee_001"},
                "reviewer": "sean",
                "disposition": "resolved",
            },
        )
        self.assertEqual(status, 400)
        self.assertIn("unknown fields", response["error"])

    def test_compiler_get_routes_reject_unknown_or_duplicate_query_fields(self) -> None:
        run_id = self.start_models_run()
        self.assertEqual(
            self.request("POST", f"/api/wizard/sessions/{run_id}/compile", {})[0],
            200,
        )

        status, response = self.request(
            "GET", f"/api/wizard/sessions/{run_id}/compile?unexpected=1"
        )
        self.assertEqual(status, 400)
        self.assertIn("query is invalid", response["error"])

        status, response = self.request(
            "GET",
            f"/api/wizard/sessions/{run_id}/exceptions?reason=missing_section&reason=unresolved_price_scope",
        )
        self.assertEqual(status, 400)
        self.assertIn("duplicate=['reason']", response["error"])

        status, response = self.request(
            "GET",
            f"/api/wizard/sessions/{run_id}/exceptions?q=zr1",
        )
        self.assertEqual(status, 200)
        self.assertGreater(response["total"], 0)
        self.assertTrue(
            all("zr1" in str(item["subject"]).lower() for item in response["items"])
        )

        severity = response["filters"]["severities"][0]
        status, response = self.request(
            "GET",
            f"/api/wizard/sessions/{run_id}/exceptions?severity={severity}",
        )
        self.assertEqual(status, 200)
        self.assertTrue(
            all(item["subject"]["severity"] == severity for item in response["items"])
        )

        status, response = self.request(
            "GET",
            f"/api/wizard/sessions/{run_id}/exceptions?query=missing_section",
        )
        self.assertEqual(status, 400)
        self.assertIn("unknown=['query']", response["error"])

        status, response = self.request(
            "GET",
            f"/api/wizard/sessions/{run_id}/exceptions?q=missing&q=section",
        )
        self.assertEqual(status, 400)
        self.assertIn("duplicate=['q']", response["error"])

        for path, expected in (
            (f"/api/wizard/sessions/{run_id}/compile?unexpected=", "unknown=['unexpected']"),
            (f"/api/wizard/sessions/{run_id}/exceptions?query=", "unknown=['query']"),
            (f"/api/wizard/sessions/{run_id}/exceptions?q=&q=missing_section", "duplicate=['q']"),
            (
                f"/api/wizard/sessions/{run_id}/exceptions?reason=missing_section&reason=",
                "duplicate=['reason']",
            ),
        ):
            status, response = self.request("GET", path)
            self.assertEqual(status, 400)
            self.assertIn(expected, response["error"])


if __name__ == "__main__":
    unittest.main()
