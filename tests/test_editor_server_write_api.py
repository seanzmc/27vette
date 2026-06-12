#!/usr/bin/env python3
"""Write-API tests for the workbook editor server (Phase 2)."""

from __future__ import annotations

import json
import shutil
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
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import workbook_editor_server as srv  # noqa: E402

REAL_WORKBOOK = ROOT / "stingray_master.xlsx"


@unittest.skipUnless(REAL_WORKBOOK.exists(), "canonical workbook not present")
class WriteApiTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._dir = tempfile.TemporaryDirectory()
        cls.wb_path = Path(cls._dir.name) / "copy.xlsx"
        shutil.copy2(REAL_WORKBOOK, cls.wb_path)
        srv.EditorHandler.cache = srv.WorkbookCache(cls.wb_path)
        srv.EditorHandler.log_path = Path(cls._dir.name) / "log.jsonl"
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), srv.EditorHandler)
        cls.port = cls.server.server_address[1]
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        srv.EditorHandler.log_path = None
        cls._dir.cleanup()

    def request(self, route, body, origin=None, method="POST"):
        headers = {"Content-Type": "application/json"}
        if origin:
            headers["Origin"] = origin
        req = urllib.request.Request(f"http://127.0.0.1:{self.port}{route}",
                                     data=json.dumps(body).encode(), headers=headers, method=method)
        try:
            with urllib.request.urlopen(req) as resp:
                return resp.status, json.loads(resp.read())
        except urllib.error.HTTPError as err:
            return err.code, json.loads(err.read() or b"{}")

    def mtime(self):
        return self.wb_path.stat().st_mtime_ns

    def update_batch(self, value, mtime=None):
        return {"version": 1, "workbookMtimeNs": self.mtime() if mtime is None else mtime, "items": [
            {"action": "update", "sheet": "stingray_options", "key": {"option_id": "opt_z51_001"},
             "row": {"detail_raw": value}}]}

    def test_cross_origin_post_forbidden(self):
        status, _body = self.request("/api/apply", {"batch": self.update_batch("x")},
                                     origin="http://evil.example")
        self.assertEqual(status, 403)

    def test_stale_batch_409(self):
        status, body = self.request("/api/apply", {"batch": self.update_batch("x", mtime=1)})
        self.assertEqual(status, 409)
        self.assertEqual(body["status"], "stale")

    def test_invalid_batch_422(self):
        bad = {"version": 1, "workbookMtimeNs": self.mtime(), "items": [
            {"action": "update", "sheet": "stingray_options", "key": {"option_id": "opt_z51_001"},
             "row": {"section_id": "sec_nope"}}]}
        status, body = self.request("/api/apply", {"batch": bad})
        self.assertEqual(status, 422)
        self.assertEqual(body["status"], "invalid")

    def test_validate_then_apply_then_visible(self):
        status, body = self.request("/api/validate", {"batch": self.update_batch("write-api test")})
        self.assertEqual(status, 200)
        self.assertTrue(body["ok"], body)
        status, body = self.request("/api/apply", {"batch": self.update_batch("write-api test"),
                                                   "confirmedWarnings": []})
        self.assertEqual(status, 200, body)
        self.assertEqual(body["status"], "applied")
        with urllib.request.urlopen(f"http://127.0.0.1:{self.port}/api/sheet/stingray_options") as resp:
            rows = json.loads(resp.read())["rows"]
        row = next(r for r in rows if r["option_id"] == "opt_z51_001")
        self.assertEqual(row["detail_raw"], "write-api test")


if __name__ == "__main__":
    unittest.main()
