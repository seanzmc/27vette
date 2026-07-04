#!/usr/bin/env python3
"""Tests for the wizard Pass A session store (state machine + persistence)."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for entry in (ROOT / "scripts", ROOT / "tests"):
    if str(entry) not in sys.path:
        sys.path.insert(0, str(entry))

from corvette_form_generator.ingest.wizard.session import (  # noqa: E402
    WizardError,
    WizardSessionStore,
)
from ingest_wizard_fixtures import build_raw_export  # noqa: E402

ROLES = {"Equipment Groups 1": "options", "Price Schedule": "price"}


class WizardSessionTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        build_raw_export(self.root / "raw.xlsx")
        (self.root / "stingray_master.xlsx").write_bytes(b"not-a-source")
        self.store = WizardSessionStore(self.root)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_list_source_files_excludes_master_workbook(self) -> None:
        names = [f["name"] for f in self.store.list_source_files()]
        self.assertEqual(names, ["raw.xlsx"])

    def test_upload_rejects_traversal_and_non_xlsx(self) -> None:
        with self.assertRaises(WizardError):
            self.store.save_upload("../evil.xlsx", b"x")
        with self.assertRaises(WizardError):
            self.store.save_upload("notes.txt", b"x")
        saved = self.store.save_upload("second.xlsx", b"binary")
        self.assertEqual(saved["origin"], "upload")
        self.assertIn("second.xlsx", [f["name"] for f in self.store.list_source_files()])

    def test_create_session_profiles_and_persists(self) -> None:
        created = self.store.create_session("raw.xlsx")
        run_id = created["session"]["runId"]
        self.assertEqual(created["session"]["state"], "profiled")
        self.assertEqual(len(created["profile"]["sheets"]), 5)
        run_dir = self.root / "form-output" / "ingest-wizard" / run_id
        self.assertTrue((run_dir / "session.json").is_file())
        self.assertTrue((run_dir / "sheet-profile.json").is_file())

    def test_roles_validation_fails_closed(self) -> None:
        run_id = self.store.create_session("raw.xlsx")["session"]["runId"]
        with self.assertRaises(WizardError):  # no price sheet
            self.store.confirm_roles(run_id, {"Equipment Groups 1": "options"})
        with self.assertRaises(WizardError):  # price role on an options matrix
            self.store.confirm_roles(
                run_id, {"Equipment Groups 1": "price", "Price Schedule": "price"}
            )
        with self.assertRaises(WizardError):  # options role on unsupported sheet
            self.store.confirm_roles(
                run_id, {"Color and Trim 1": "options", "Price Schedule": "price"}
            )
        with self.assertRaises(WizardError):  # unknown sheet
            self.store.confirm_roles(run_id, {"Nope": "options", "Price Schedule": "price"})
        with self.assertRaises(WizardError):  # parse before roles
            self.store.run_parse(run_id)

    def test_standard_equipment_sheet_can_be_included_by_override(self) -> None:
        run_id = self.store.create_session("raw.xlsx")["session"]["runId"]
        session = self.store.confirm_roles(
            run_id, {"Standard Equipment 1": "options", "Price Schedule": "price"}
        )
        self.assertEqual(session["state"], "roles_confirmed")

    def test_full_run_reaches_parsed_candidates(self) -> None:
        run_id = self.store.create_session("raw.xlsx")["session"]["runId"]
        with self.assertRaises(WizardError):  # candidates before parse
            self.store.candidates(run_id)
        self.store.confirm_roles(run_id, ROLES)
        result = self.store.run_parse(run_id)
        self.assertEqual(result["session"]["state"], "parsed")
        self.assertEqual(result["joinReport"]["exactMatches"], 1)  # BV4
        payload = self.store.candidates(run_id)
        self.assertEqual(payload["total"], 4)  # UQH, BV4, E60, ZZZ
        exact_only = self.store.candidates(run_id, price_match="exact")
        self.assertEqual([c["rpo"] for c in exact_only["candidates"]], ["BV4"])
        searched = self.store.candidates(run_id, query="plaque")
        self.assertEqual(len(searched["candidates"]), 1)

    def test_reconfirming_roles_resets_parse_output(self) -> None:
        run_id = self.store.create_session("raw.xlsx")["session"]["runId"]
        self.store.confirm_roles(run_id, ROLES)
        self.store.run_parse(run_id)
        self.store.confirm_roles(run_id, ROLES)
        with self.assertRaises(WizardError):
            self.store.candidates(run_id)

    def test_source_change_fails_closed(self) -> None:
        run_id = self.store.create_session("raw.xlsx")["session"]["runId"]
        raw = self.root / "raw.xlsx"
        raw.write_bytes(raw.read_bytes() + b"tail")
        with self.assertRaises(WizardError):
            self.store.confirm_roles(run_id, ROLES)

    def test_unknown_run_is_404(self) -> None:
        try:
            self.store.session_detail("20990101-000000-abcdef")
            self.fail("expected WizardError")
        except WizardError as exc:
            self.assertEqual(exc.status, 404)


if __name__ == "__main__":
    unittest.main()
