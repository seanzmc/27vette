#!/usr/bin/env python3
"""HTTP boundary tests for retired Pass B mutation and GET-only evidence."""

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
from corvette_form_generator.ingest.wizard.session import (  # noqa: E402
    WizardSessionStore,
    write_json,
)
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
        roles = {
            card["sheetName"]: card["recommendedRole"]
            for card in created["profile"]["sheets"]
        }
        self.assertEqual(
            self.post_json(
                f"/api/wizard/sessions/{run_id}/roles", {"roles": roles}
            )[0],
            200,
        )
        self.assertEqual(
            self.post_json(f"/api/wizard/sessions/{run_id}/parse", {})[0], 200
        )
        return run_id

    def test_current_model_selection_remains_writable(self) -> None:
        run_id = self.start_parsed_run()
        status, models = self.request(
            "GET", f"/api/wizard/sessions/{run_id}/models"
        )
        self.assertEqual(status, 200)
        keys = {model["modelKey"] for model in models["models"]}
        self.assertLessEqual({"zr1", "zr1x"}, keys)

        status, selected = self.post_json(
            f"/api/wizard/sessions/{run_id}/models",
            {
                "targets": ["zr1"],
                "comparators": {"zr1": "z06"},
            },
        )
        self.assertEqual(status, 200)
        self.assertEqual(selected["session"]["state"], "models_selected")

    def test_historical_plan_is_json_only_get_evidence(self) -> None:
        run_id = self.start_parsed_run()
        run_dir = self.root / "form-output" / "ingest-wizard" / run_id
        write_json(run_dir / "apply-plan.json", {"schemaVersion": "pass-c-3"})
        write_json(run_dir / "apply-plan-dryrun.json", {"ok": True})

        status, payload = self.request(
            "GET", f"/api/wizard/sessions/{run_id}/plan"
        )
        self.assertEqual(status, 200)
        self.assertEqual(payload["plan"]["schemaVersion"], "pass-c-3")
        self.assertEqual(payload["dryRun"], {"ok": True})

    def test_historical_pass_b_mutations_return_exact_gone_response(self) -> None:
        run_id = self.start_parsed_run()
        for suffix in (
            "/decisions",
            "/decisions/delete",
            "/copy-decisions",
            "/complete",
        ):
            with self.subTest(suffix=suffix):
                status, payload = self.post_json(
                    f"/api/wizard/sessions/{run_id}{suffix}", {}
                )
                self.assertEqual(status, 410)
                self.assertEqual(
                    payload, {"error": "Historical ingest mutation is retired."}
                )


if __name__ == "__main__":
    unittest.main()
