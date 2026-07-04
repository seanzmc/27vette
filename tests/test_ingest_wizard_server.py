#!/usr/bin/env python3
"""HTTP API tests for the ingest wizard server (Pass A)."""

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
from ingest_wizard_fixtures import build_raw_export  # noqa: E402


class WizardServerTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._tmp = tempfile.TemporaryDirectory()
        cls.root = Path(cls._tmp.name)
        build_raw_export(cls.root / "raw.xlsx")
        srv.WizardHandler.store = WizardSessionStore(cls.root)
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

    def test_full_wizard_flow(self) -> None:
        status, files = self.request("GET", "/api/wizard/files")
        self.assertEqual(status, 200)
        self.assertIn("raw.xlsx", [f["name"] for f in files["files"]])

        status, created = self.post_json("/api/wizard/sessions", {"file": "raw.xlsx"})
        self.assertEqual(status, 200)
        run_id = created["session"]["runId"]
        self.assertEqual(created["session"]["state"], "profiled")
        self.assertEqual(len(created["profile"]["sheets"]), 5)

        status, _ = self.post_json(
            f"/api/wizard/sessions/{run_id}/roles",
            {"roles": {"Equipment Groups 1": "options", "Price Schedule": "price"}},
        )
        self.assertEqual(status, 200)

        status, parsed = self.post_json(f"/api/wizard/sessions/{run_id}/parse", {})
        self.assertEqual(status, 200)
        self.assertEqual(parsed["session"]["state"], "parsed")
        self.assertEqual(parsed["joinReport"]["exactMatches"], 1)

        status, table = self.request(
            "GET", f"/api/wizard/sessions/{run_id}/candidates?priceMatch=exact"
        )
        self.assertEqual(status, 200)
        self.assertEqual([c["rpo"] for c in table["candidates"]], ["BV4"])
        self.assertEqual(table["candidates"][0]["listPrice"], 395.0)
        self.assertTrue(table["candidates"][0]["sourceEvidence"]["cells"])

        status, detail = self.request("GET", f"/api/wizard/sessions/{run_id}")
        self.assertEqual(status, 200)
        self.assertEqual(detail["session"]["state"], "parsed")
        self.assertIsNotNone(detail["roles"])
        self.assertIsNotNone(detail["joinReport"])

    def test_error_mapping(self) -> None:
        status, payload = self.post_json("/api/wizard/sessions", {"file": "missing.xlsx"})
        self.assertEqual(status, 400)
        self.assertIn("error", payload)

        status, _ = self.request("GET", "/api/wizard/sessions/20990101-000000-abcdef")
        self.assertEqual(status, 404)

        status, _ = self.request("GET", "/api/nope")
        self.assertEqual(status, 404)

        run_id = self.post_json("/api/wizard/sessions", {"file": "raw.xlsx"})[1]["session"]["runId"]
        status, payload = self.post_json(f"/api/wizard/sessions/{run_id}/parse", {})
        self.assertEqual(status, 400)
        self.assertIn("roles", payload["error"].lower())

    def test_upload_endpoint(self) -> None:
        status, payload = self.request(
            "POST", "/api/wizard/upload?filename=extra.xlsx", b"binary-bytes"
        )
        self.assertEqual(status, 200)
        self.assertEqual(payload["file"]["name"], "extra.xlsx")
        status, payload = self.request(
            "POST", "/api/wizard/upload?filename=..%2Fevil.xlsx", b"x"
        )
        self.assertEqual(status, 400)


if __name__ == "__main__":
    unittest.main()
