"""Canonical workbook-manager import, staging, sync, and API regressions."""

from __future__ import annotations

import hashlib
import os
import shutil
import sqlite3
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock

REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND = REPO_ROOT / "workbook-manager" / "backend"
for path in (str(BACKEND), str(REPO_ROOT / "scripts")):
    if path not in sys.path:
        sys.path.insert(0, path)

from app import db as dbmod  # noqa: E402
from app import importer, naming, staging, sync as syncmod  # noqa: E402
from app.catalog import physical_table  # noqa: E402
from app.staging import StagingError  # noqa: E402
from app.validation import find_dependents  # noqa: E402

WORKBOOK = REPO_ROOT / "stingray_master.xlsx"
_TEMPLATE_DIR: Path | None = None
_TEMPLATE_DB: Path | None = None

try:
    import fastapi  # noqa: F401
    HAVE_FASTAPI = True
except ImportError:
    HAVE_FASTAPI = False


def canonical_template() -> Path:
    global _TEMPLATE_DIR, _TEMPLATE_DB
    if _TEMPLATE_DB is None:
        _TEMPLATE_DIR = Path(tempfile.mkdtemp(prefix="wbm-template-"))
        _TEMPLATE_DB = _TEMPLATE_DIR / "canonical.sqlite3"
        report = importer.import_workbook(_TEMPLATE_DB, WORKBOOK)
        if report.status != "validated":
            raise AssertionError(report)
    return _TEMPLATE_DB


class ImportedWorkbookCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmpdir = Path(tempfile.mkdtemp(prefix="wbm-test-"))

    def setUp(self):
        self.db_path = self.tmpdir / f"{self._testMethodName}.sqlite3"
        shutil.copyfile(canonical_template(), self.db_path)
        self.conn = dbmod.connect(self.db_path)
        self.report = importer.latest_report(self.conn)

    def tearDown(self):
        self.conn.close()
        for suffix in ("", "-wal", "-shm"):
            try:
                Path(str(self.db_path) + suffix).unlink()
            except FileNotFoundError:
                pass

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmpdir, ignore_errors=True)


class TestImportFidelity(ImportedWorkbookCase):
    def test_option_counts_match_compiler_contract(self):
        self.assertEqual(self.conn.execute(
            "SELECT COUNT(*) FROM stingray_options").fetchone()[0], 242)
        self.assertEqual(self.conn.execute(
            "SELECT COUNT(*) FROM grand_sport_options").fetchone()[0], 241)
        self.assertEqual(self.conn.execute(
            "SELECT COUNT(*) FROM z06_options").fetchone()[0], 244)

    def test_every_sheet_has_catalog_disposition(self):
        self.assertEqual(self.conn.execute(
            "SELECT COUNT(*) FROM source_table_catalog").fetchone()[0], 65)
        self.assertEqual(self.conn.execute(
            "SELECT COUNT(DISTINCT source_sheet) FROM source_table_catalog"
        ).fetchone()[0], 65)

    def test_option_primary_keys_are_model_physical(self):
        for model in ("stingray", "grand_sport", "z06"):
            table = physical_table(model, "options")
            primary = [row["name"] for row in self.conn.execute(
                f"PRAGMA table_info({table})") if row["pk"]]
            self.assertEqual(primary, ["option_id"])

    def test_cross_model_option_ids_coexist(self):
        overlap = self.conn.execute(
            "SELECT COUNT(*) FROM stingray_options s "
            "JOIN grand_sport_options g USING(option_id)"
        ).fetchone()[0]
        self.assertGreater(overlap, 0)

    def test_import_report_and_relationships_are_clean(self):
        self.assertEqual(self.report["run"]["status"], "validated")
        self.assertFalse([
            issue for issue in self.report["issues"]
            if issue["severity"] == "error"
        ])
        self.assertEqual(list(self.conn.execute("PRAGMA foreign_key_check")), [])

    def test_registry_and_mapping_are_queryable(self):
        self.assertEqual(self.conn.execute(
            "SELECT COUNT(*) FROM model_table_registry").fetchone()[0], 51)
        self.assertEqual(self.conn.execute(
            "SELECT COUNT(*) FROM schema_mapping").fetchone()[0], 646)


class TestNaming(unittest.TestCase):
    def test_humanize_examples(self):
        self.assertEqual(naming.humanize("stingray_exterior_options"),
                         "Stingray Exterior Options")
        self.assertEqual(naming.humanize("grandSport_options"),
                         "Grand Sport Options")

    def test_display_id_prefix_stripping_is_reversible(self):
        prefix, remainder = naming.strip_prefix("opt_z51_001", ("opt_",))
        self.assertEqual(prefix + remainder, "opt_z51_001")


def option_record(conn, option_id="opt_test_901"):
    section = conn.execute(
        "SELECT section_id FROM sections ORDER BY section_id LIMIT 1"
    ).fetchone()[0]
    return {
        "option_id": option_id, "rpo": "TST", "price": 100,
        "option_name": "Test Option", "description": "", "detail_raw": "",
        "section_id": section, "selectable": 1, "display_order": 999,
        "active": 1, "display_behavior": None,
    }


class TestStagingWorkflow(ImportedWorkbookCase):
    def setUp(self):
        super().setUp()

    def test_stage_validate_commit_add_option(self):
        record = option_record(self.conn)
        change = staging.stage_change(
            self.conn, model_key="stingray", table_role="options", op="add",
            key={"option_id": record["option_id"]}, record=record,
        )
        self.assertEqual(change["sql_table"], "stingray_options")
        result = staging.commit_staged(self.conn, actor="test")
        self.assertTrue(result["ok"], result)
        self.assertIsNotNone(self.conn.execute(
            "SELECT * FROM stingray_options WHERE option_id='opt_test_901'"
        ).fetchone())

    def test_invalid_reference_is_rejected_with_field_detail(self):
        record = option_record(self.conn, "opt_test_902")
        record["section_id"] = "sec_missing"
        with self.assertRaises(StagingError) as caught:
            staging.stage_change(
                self.conn, model_key="stingray", table_role="options", op="add",
                key={"option_id": record["option_id"]}, record=record,
            )
        self.assertIn("section_id", {e["field"] for e in caught.exception.errors})

    def test_duplicate_key_rejected_in_model_scope(self):
        existing = self.conn.execute(
            "SELECT option_id FROM stingray_options LIMIT 1").fetchone()[0]
        with self.assertRaises(StagingError):
            staging.stage_change(
                self.conn, model_key="stingray", table_role="options", op="add",
                key={"option_id": existing}, record=option_record(self.conn, existing),
            )

    def test_delete_blocked_by_all_physical_dependents(self):
        row = self.conn.execute(
            "SELECT a.option_id FROM stingray_option_availability a "
            "JOIN stingray_exclusive_group_members e USING(option_id) LIMIT 1"
        ).fetchone()
        with self.assertRaises(StagingError) as caught:
            staging.stage_change(
                self.conn, model_key="stingray", table_role="options",
                op="delete", key={"option_id": row[0]}, record=None,
            )
        roles = {
            item["table_role"]
            for item in caught.exception.errors[0]["dependents"]
        }
        self.assertIn("option_availability", roles)
        self.assertIn("exclusive_group_members", roles)

    def test_key_rename_on_update_rejected(self):
        row = dict(self.conn.execute(
            "SELECT * FROM stingray_options LIMIT 1").fetchone())
        key = {"option_id": row["option_id"]}
        row["option_id"] = "opt_renamed_999"
        with self.assertRaises(StagingError) as caught:
            staging.stage_change(
                self.conn, model_key="stingray", table_role="options",
                op="update", key=key, record=row,
            )
        self.assertIn("cannot change", caught.exception.errors[0]["message"])

    def test_cross_model_payload_rejected(self):
        record = option_record(self.conn, "opt_test_903")
        record["model_key"] = "z06"
        with self.assertRaises(StagingError):
            staging.stage_change(
                self.conn, model_key="stingray", table_role="options", op="add",
                key={"option_id": record["option_id"]}, record=record,
            )


class TestSyncBatch(ImportedWorkbookCase):
    def setUp(self):
        super().setUp()

    def _commit_price_edit(self):
        row = dict(self.conn.execute(
            "SELECT * FROM stingray_options WHERE rpo='Z51'").fetchone())
        key = {"option_id": row["option_id"]}
        row["price"] += 1
        staging.stage_change(
            self.conn, model_key="stingray", table_role="options", op="update",
            key=key, record=row,
        )
        self.assertTrue(staging.commit_staged(self.conn, actor="test")["ok"])
        return key, row

    def test_batch_targets_registered_sheet_with_header_names(self):
        key, record = self._commit_price_edit()
        item = syncmod.build_batch(self.conn, WORKBOOK)["items"][0]
        self.assertEqual(item["sheet"], "stingray_options")
        self.assertEqual(item["key"], key)
        self.assertEqual(item["row"]["price"], record["price"])

    def test_dry_run_batch_passes_editor_ops_validation(self):
        from corvette_form_generator import editor_ops
        self._commit_price_edit()
        batch = syncmod.build_batch(self.conn, WORKBOOK)
        extract = editor_ops.extract_workbook(WORKBOOK)
        errors, _warnings, prepared = editor_ops._prepare_batch(
            extract, {"items": batch["items"]})
        self.assertEqual(errors, [])
        self.assertEqual(len(prepared), 1)

    @unittest.skipUnless(os.environ.get("WBM_SLOW_GATE") == "1",
                         "full gate is slow; set WBM_SLOW_GATE=1")
    def test_live_write_only_on_scratch_copy(self):
        scratch = self.tmpdir / "scratch.xlsx"
        shutil.copy2(WORKBOOK, scratch)
        before = hashlib.sha256(WORKBOOK.read_bytes()).hexdigest()
        old_log_path = syncmod.config.EDIT_LOG_PATH
        syncmod.config.EDIT_LOG_PATH = self.tmpdir / "edit-log.jsonl"
        self._commit_price_edit()
        try:
            dry = syncmod.sync_workbook(self.conn, scratch, write=False)
            self.assertEqual(dry["status"], "validated")
            live = syncmod.sync_workbook(
                self.conn, scratch, write=True,
                expected_mtime_ns=dry["workbookMtimeNs"],
            )
        finally:
            syncmod.config.EDIT_LOG_PATH = old_log_path
        self.assertEqual(live["status"], "applied")
        self.assertTrue(live["backupPath"])
        self.assertEqual(hashlib.sha256(WORKBOOK.read_bytes()).hexdigest(), before)
        statuses = [row[0] for row in self.conn.execute(
            "SELECT status FROM change_history ORDER BY id")]
        self.assertEqual(statuses, ["committed", "sync_succeeded"])


class TestDependencyInspection(ImportedWorkbookCase):
    def test_option_dependents_span_physical_roles(self):
        row = self.conn.execute(
            "SELECT option_id FROM stingray_exclusive_group_members LIMIT 1"
        ).fetchone()
        dependencies = find_dependents(
            self.conn, "stingray", "options", {"option_id": row[0]}
        )
        self.assertIn("exclusive_group_members",
                      {item["table_role"] for item in dependencies})


@unittest.skipUnless(HAVE_FASTAPI, "fastapi not installed")
class TestApi(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmpdir = Path(tempfile.mkdtemp(prefix="wbm-api-"))
        os.environ["WBM_DB"] = str(cls.tmpdir / "api.sqlite3")
        os.environ["WBM_VAR_DIR"] = str(cls.tmpdir / "var")
        # Force a FULL re-import of the app package so config re-reads the
        # env vars above. The bare "app" entry must be deleted too: leaving
        # the package object in sys.modules makes `from . import staging`
        # resolve to the stale module via the package attribute while
        # `from .staging import StagingError` re-imports a fresh copy —
        # two StagingError classes, and main.py's `except StagingError`
        # misses the raise (500 instead of 422).
        for mod in list(sys.modules):
            if mod == "app" or mod.startswith("app."):
                del sys.modules[mod]
        from app import importer as api_importer
        report = api_importer.import_workbook(
            Path(os.environ["WBM_DB"]), WORKBOOK)
        if report.status != "validated":
            raise AssertionError(report)
        from fastapi.testclient import TestClient
        from app.main import app as fastapi_app
        cls.client = TestClient(fastapi_app)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmpdir, ignore_errors=True)

    def test_status_and_models(self):
        status = self.client.get("/api/status").json()
        self.assertEqual(status["tables"]["stingray_options"], 242)
        models = self.client.get("/api/models").json()["models"]
        keys = {m["model_key"] for m in models}
        self.assertLessEqual({"stingray", "grand_sport", "z06"}, keys)
        stingray = next(m for m in models if m["model_key"] == "stingray")
        self.assertEqual(stingray["label"], stingray["model_label"])
        self.assertIn(stingray["active"], {"True", "False"})
        self.assertIn(stingray["default_model"], {"True", "False"})
        self.assertIn(stingray["promoted_to_runtime"], {"True", "False"})
        self.assertIsInstance(stingray["scaffold"], bool)

    def test_structure_and_collections(self):
        structure = self.client.get("/api/structure/stingray").json()
        self.assertTrue(structure["steps"])
        step = structure["steps"][0]
        self.assertTrue(step["display_name"])
        self.assertIn(step["active"], {"True", "False"})
        self.assertIsInstance(step["sections"], list)
        self.assertTrue(structure["section_presentation"])
        presentation = structure["section_presentation"][0]
        self.assertTrue(presentation["display_name"])
        self.assertIn(presentation["active"], {"True", "False"})
        self.assertIn(structure["variants"][0]["active"], {"True", "False"})
        collections = self.client.get(
            "/api/models/stingray/collections").json()["collections"]
        self.assertIn("options", {row["table_role"] for row in collections})
        self.assertIn("options", {row["table"] for row in collections})

    def test_transitional_record_routes_delegate_to_physical_tables(self):
        schema = self.client.get(
            "/api/records/options/schema?model=stingray"
        )
        self.assertEqual(schema.status_code, 200, schema.text)
        body = schema.json()
        self.assertEqual(body["table"], "options")
        self.assertTrue(body["model_scoped"])
        self.assertEqual(body["table_role"], "options")
        records = self.client.get(
            "/api/records/options?model=stingray&limit=2"
        )
        self.assertEqual(records.status_code, 200, records.text)
        self.assertEqual(records.json()["table"], "options")
        self.assertEqual(len(records.json()["records"]), 2)
        row_ids = [row["id"] for row in records.json()["records"]]
        self.assertEqual(len(set(row_ids)), 2)
        repeated = self.client.get(
            "/api/records/options?model=stingray&limit=2"
        ).json()["records"]
        self.assertEqual(row_ids, [row["id"] for row in repeated])

    def test_legacy_structure_tables_use_canonical_central_services(self):
        schema = self.client.get(
            "/api/records/form_steps/schema?model=stingray"
        )
        self.assertEqual(schema.status_code, 200, schema.text)
        self.assertEqual(schema.json()["table"], "form_steps")
        self.assertEqual(schema.json()["table_role"], "runtime_steps")
        self.assertEqual(schema.json()["sql_table"], "runtime_steps")
        self.assertEqual(schema.json()["key"], ["model_key", "step_key"])

        records = self.client.get(
            "/api/records/form_steps?model=stingray&limit=1"
        )
        self.assertEqual(records.status_code, 200, records.text)
        row = records.json()["records"][0]
        self.assertEqual(row["model_key"], "stingray")
        self.assertTrue(row["id"])

        response = self.client.post("/api/changes", json={
            "model_id": "",
            "table": "form_steps",
            "op": "update",
            "key": {
                "id": row["id"],
                "model_key": row["model_key"],
                "step_key": row["step_key"],
            },
            "record": {
                **row,
                "display_name": "derived UI label must be stripped",
                "sections": [],
                "notes": f"{row['notes']} compatibility".strip(),
            },
        })
        self.assertEqual(response.status_code, 200, response.text)
        body = response.json()
        self.assertEqual(body["model_key"], "stingray")
        self.assertEqual(body["table_role"], "runtime_steps")
        self.assertEqual(body["table"], "form_steps")
        self.assertNotIn("id", body["new"])
        self.assertNotIn("display_name", body["new"])
        self.assertNotIn("sections", body["new"])
        validation = self.client.post("/api/changes/validate")
        self.assertEqual(validation.status_code, 200, validation.text)
        self.assertTrue(validation.json()["ok"], validation.text)
        self.client.delete(f"/api/changes/{body['id']}")

    def test_legacy_section_presentation_uses_canonical_central_service(self):
        section_schema = self.client.get(
            "/api/records/section_presentation/schema?model=stingray"
        )
        self.assertEqual(section_schema.status_code, 200, section_schema.text)
        self.assertEqual(
            section_schema.json()["table_role"], "section_presentation"
        )
        section_row = self.client.get(
            "/api/records/section_presentation?model=stingray&limit=1"
        ).json()["records"][0]
        section_change = self.client.post("/api/changes", json={
            "table": "section_presentation",
            "model_id": "",
            "op": "update",
            "key": {
                "id": section_row["id"],
                "model_key": section_row["model_key"],
                "section_id": section_row["section_id"],
            },
            "record": {
                **section_row,
                "display_name": "derived label",
                "notes": f"{section_row['notes']} compatibility".strip(),
            },
        })
        self.assertEqual(section_change.status_code, 200, section_change.text)
        section_body = section_change.json()
        self.assertEqual(section_body["table_role"], "section_presentation")
        self.assertEqual(section_body["table"], "section_presentation")
        self.assertNotIn("id", section_body["new"])
        self.assertNotIn("display_name", section_body["new"])
        validation = self.client.post("/api/changes/validate")
        self.assertEqual(validation.status_code, 200, validation.text)
        self.assertTrue(validation.json()["ok"], validation.text)
        self.client.delete(f"/api/changes/{section_body['id']}")

    def test_import_response_retains_canonical_fields_and_legacy_aliases(self):
        finding = types.SimpleNamespace(
            severity="warning", status="mapped", code="mapped_test",
            message="mapped", source_sheet="runtime_steps", source_row=2,
            source_column="step_key", model_key="stingray", value=None,
        )
        report = types.SimpleNamespace(
            status="validated", live_models=("stingray",),
            findings=(finding,), decision_required=(),
            contract_differences=(), candidate_path=None,
            promoted_path=None,
        )
        main_module = sys.modules["app.main"]
        with mock.patch.object(
            main_module.importer, "import_workbook", return_value=report
        ):
            response = self.client.post("/api/import")
        self.assertEqual(response.status_code, 200, response.text)
        body = response.json()
        self.assertEqual(body["status"], "validated")
        self.assertEqual(body["live_models"], ["stingray"])
        self.assertEqual(body["findings"][0]["code"], "mapped_test")
        self.assertEqual(body["run"]["status"], "imported")
        self.assertEqual(body["issues"][0]["category"], "mapped_test")

    def test_transitional_dependency_and_stage_payload_aliases(self):
        row = self.client.get(
            "/api/records/options?model=stingray&search=Z51&limit=1"
        ).json()["records"][0]
        dependencies = self.client.post(
            "/api/records/options/dependencies",
            json={"model_id": "stingray", "key": {"option_id": row["option_id"]}},
        )
        self.assertEqual(dependencies.status_code, 200, dependencies.text)
        if dependencies.json()["dependents"]:
            dependent = dependencies.json()["dependents"][0]
            self.assertIn("table", dependent)
            self.assertIn("src_sheet", dependent)
            self.assertIn("src_row", dependent)
        resp = self.client.post("/api/changes", json={
            "model_id": "stingray", "table": "options", "op": "update",
            "key": {"option_id": row["option_id"]},
            "record": {"price": row["price"] + 1},
        })
        self.assertEqual(resp.status_code, 200, resp.text)
        self.assertEqual(resp.json()["model_id"], "stingray")
        self.assertEqual(resp.json()["table"], "options")
        self.assertEqual(resp.json()["table_name"], "options")

    def test_react_string_values_stage_as_canonical_types(self):
        row = self.client.get(
            "/api/records/options?model=stingray&search=Z51&limit=1"
        ).json()["records"][0]
        response = self.client.post("/api/changes", json={
            "model_id": "stingray", "table": "options", "op": "update",
            "key": {"option_id": row["option_id"]},
            "record": {
                "price": f"{row['price'] + 1:,}",
                "active": "False" if row["active"] else "True",
            },
        })
        self.assertEqual(response.status_code, 200, response.text)
        change = response.json()
        self.assertIsInstance(change["new"]["price"], int)
        self.assertIn(change["new"]["active"], (0, 1))
        self.client.delete(f"/api/changes/{change['id']}")

    def test_stage_endpoint_validation_error_shape(self):
        resp = self.client.post("/api/changes", json={
            "model_id": "stingray", "table": "options", "op": "add",
            "key": {"option_id": "opt_x"},
            "record": {"option_id": "opt_x", "price": "not-a-number"},
        })
        self.assertEqual(resp.status_code, 422)
        self.assertTrue(any(
            error["field"] == "price"
            for error in resp.json()["detail"]["errors"]
        ))

    def test_live_sync_requires_confirmation(self):
        response = self.client.post("/api/sync", json={"write": True})
        self.assertEqual(response.status_code, 400)


if __name__ == "__main__":
    unittest.main(verbosity=2)
