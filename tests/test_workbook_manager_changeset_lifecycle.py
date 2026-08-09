"""Pass 5 immutable ChangeSet lifecycle for Workbook Manager."""

from __future__ import annotations

import json
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND = REPO_ROOT / "workbook-manager" / "backend"
for path in (str(BACKEND), str(REPO_ROOT / "scripts")):
    if path not in sys.path:
        sys.path.insert(0, path)

from app import db as dbmod, drafts, main  # noqa: E402
from corvette_form_generator.workbook_domain.changeset import parse_changeset  # noqa: E402


class TestImmutableChangeSetEmission(unittest.TestCase):
    def _stores(self, root: Path):
        projection = dbmod.connect(root / "projection.sqlite3")
        state = dbmod.connect(root / "state.sqlite3", foreign_keys=True)
        dbmod.init_projection_schema(projection)
        dbmod.init_durable_schema(state)
        projection.execute(
            "INSERT INTO models(src_sheet, src_row, src_family, physical_key, "
            "model_context, model_key, active) VALUES(?,?,?,?,?,?,?)",
            ("model_master", 2, "model_master", '["stingray"]', '["stingray"]',
             "stingray", "True"),
        )
        projection.execute(
            "INSERT INTO sheet_registry(src_sheet, src_row, src_family, "
            "physical_key, model_context, model_key, source_role, sheet_name, "
            "active) VALUES(?,?,?,?,?,?,?,?,?)",
            ("model_workbook_sources", 2, "model_workbook_sources",
             '["stingray","source_option_sheet"]', '["stingray"]', "stingray",
             "source_option_sheet", "stingray_options", "True"),
        )
        projection.execute(
            "INSERT INTO options(src_sheet, src_row, src_family, physical_key, "
            "model_context, model_id, option_id, rpo, option_name, price, active) "
            "VALUES(?,?,?,?,?,?,?,?,?,?,?)",
            ("stingray_options", 10, "options", '["opt_test"]', '["stingray"]',
             "stingray", "opt_test", "TST", "Original", "100", "True"),
        )
        projection.commit()
        return projection, state

    def test_commit_emits_one_exact_immutable_typed_changeset(self):
        with tempfile.TemporaryDirectory(prefix="wbm-changeset-emission-") as raw:
            projection, state = self._stores(Path(raw))
            try:
                operation = drafts.save_operation(
                    projection,
                    state,
                    projection_state="current",
                    base_workbook_sha256="a" * 64,
                    base_workbook_mtime_ns="123",
                    draft_id="draft-1",
                    table="options",
                    model_id="stingray",
                    op="update",
                    key={"option_id": "opt_test"},
                    record={"option_name": "Changed", "price": "125"},
                    session_id="session-1",
                    actor="Sean",
                )

                emitted = drafts.emit_changeset(state, draft_id="draft-1")
                parsed = parse_changeset(emitted)

                self.assertEqual(parsed, emitted)
                self.assertEqual(emitted["schemaVersion"], "workbook-changeset-1")
                self.assertEqual(emitted["source"], {
                    "kind": "workbook-manager",
                    "runId": "draft-1",
                })
                self.assertEqual(emitted["targets"], ["stingray"])
                self.assertEqual(emitted["workbook"], {
                    "sha256": "a" * 64,
                    "mtimeNs": "123",
                })
                self.assertEqual(emitted["sheetCreates"], [])
                self.assertEqual(emitted["noops"], [])
                self.assertEqual(emitted["warningAcknowledgementsRequested"], [])
                self.assertEqual(emitted["bindings"], {})
                self.assertEqual(emitted["rowChanges"], [{
                    "action": "update",
                    "sheet": "stingray_options",
                    "family": "options",
                    "key": {"option_id": "opt_test"},
                    "fields": {
                        "option_name": {"before": "Original", "after": "Changed"},
                        "price": {"before": 100, "after": 125},
                    },
                    "provenance": [{
                        "kind": "workbook-manager-draft-operation",
                        "id": str(operation["id"]),
                    }],
                }])
                stored = state.execute(
                    "SELECT * FROM draft_changesets WHERE draft_id='draft-1'"
                ).fetchone()
                self.assertIsNotNone(stored)
                self.assertEqual(json.loads(stored["payload_json"]), emitted)
                self.assertEqual(stored["change_set_id"], emitted["changeSetId"])
                self.assertEqual(
                    stored["semantic_fingerprint"], emitted["semanticFingerprint"]
                )
                with self.assertRaisesRegex(
                    sqlite3.IntegrityError, "ChangeSet artifacts are immutable"
                ):
                    state.execute(
                        "UPDATE draft_changesets SET payload_json='{}' "
                        "WHERE draft_id='draft-1'"
                    )
                with self.assertRaisesRegex(
                    sqlite3.IntegrityError, "ChangeSet artifacts are immutable"
                ):
                    state.execute(
                        "DELETE FROM draft_changesets WHERE draft_id='draft-1'"
                    )
                state.rollback()
                draft = state.execute(
                    "SELECT status FROM workflow_drafts WHERE id='draft-1'"
                ).fetchone()
                self.assertEqual(draft["status"], "changeset_emitted")

                with self.assertRaises(drafts.DraftError) as ctx:
                    drafts.emit_changeset(state, draft_id="draft-1")
                self.assertEqual(ctx.exception.code, "draft_not_mutable")
                self.assertEqual(
                    state.execute(
                        "SELECT COUNT(*) c FROM draft_changesets WHERE draft_id='draft-1'"
                    ).fetchone()["c"],
                    1,
                )
            finally:
                projection.close()
                state.close()

    def test_empty_draft_cannot_emit_a_changeset(self):
        with tempfile.TemporaryDirectory(prefix="wbm-empty-changeset-") as raw:
            _, state = self._stores(Path(raw))
            try:
                state.execute(
                    "INSERT INTO workflow_drafts(id, created_ts, updated_ts, status, "
                    "base_workbook_sha256, base_workbook_mtime_ns) "
                    "VALUES('empty', 't', 't', 'draft', ?, '123')",
                    ("b" * 64,),
                )
                state.commit()
                with self.assertRaises(drafts.DraftError) as ctx:
                    drafts.emit_changeset(state, draft_id="empty")
                self.assertEqual(ctx.exception.code, "empty_draft")
                self.assertEqual(
                    state.execute("SELECT status FROM workflow_drafts WHERE id='empty'")
                    .fetchone()["status"],
                    "draft",
                )
            finally:
                state.close()

    def test_commit_endpoint_returns_the_persisted_changeset(self):
        with tempfile.TemporaryDirectory(prefix="wbm-commit-endpoint-") as raw:
            projection, state = self._stores(Path(raw))
            try:
                drafts.save_operation(
                    projection,
                    state,
                    projection_state="current",
                    base_workbook_sha256="c" * 64,
                    base_workbook_mtime_ns="456",
                    draft_id="draft-api",
                    table="options",
                    model_id="stingray",
                    op="update",
                    key={"option_id": "opt_test"},
                    record={"price": "150"},
                )
                emitted = main.commit_draft(
                    "draft-api", _lock=None, state_conn=state
                )
                stored = json.loads(
                    state.execute(
                        "SELECT payload_json FROM draft_changesets "
                        "WHERE draft_id='draft-api'"
                    ).fetchone()["payload_json"]
                )
                self.assertEqual(emitted, stored)
            finally:
                projection.close()
                state.close()


class TestSchema5Migration(unittest.TestCase):
    def test_v4_durable_upgrade_preserves_draft_and_verified_projection(self):
        with tempfile.TemporaryDirectory(prefix="wbm-schema5-upgrade-") as raw:
            root = Path(raw)
            state_path = root / "state.sqlite3"
            projection_path = root / "projection.sqlite3"
            state = dbmod.connect(state_path)
            projection = dbmod.connect(projection_path)
            try:
                dbmod.init_durable_schema(state)
                state.execute("DROP TABLE IF EXISTS draft_changesets")
                state.execute(
                    "INSERT INTO workflow_drafts(id, created_ts, updated_ts, status, "
                    "base_workbook_sha256, base_workbook_mtime_ns) "
                    "VALUES('sentinel-draft', 't', 't', 'draft', ?, '123')",
                    ("d" * 64,),
                )
                state.execute(
                    "INSERT INTO draft_operations(draft_id, created_ts, updated_ts, "
                    "table_name, family, source_sheet, physical_key, entity_key_json, "
                    "action, changed_fields_json) VALUES('sentinel-draft', 't', 't', "
                    "'options', 'options', 'stingray_options', '[\"opt_test\"]', "
                    "'{\"option_id\":\"opt_test\"}', 'update', "
                    "'{\"price\":{\"before\":100,\"after\":125}}')"
                )
                dbmod._write_manifest(
                    state,
                    store_kind="durable",
                    migration_id="durable-v4",
                    source_sha256="source-sha",
                    source_path=state_path,
                    archive_path=None,
                    table_counts={},
                )
                state.execute("UPDATE storage_manifest SET schema_version=4")
                state.commit()

                dbmod.init_projection_schema(projection)
                projection.execute(
                    "INSERT INTO models(src_sheet, src_row, model_key, active) "
                    "VALUES('model_master', 2, 'sentinel-model', 'True')"
                )
                dbmod._write_manifest(
                    projection,
                    store_kind="projection",
                    migration_id="import-verified-v3",
                    source_sha256="verified-sha",
                    source_path=Path("/tmp/source.xlsx"),
                    archive_path=None,
                    table_counts={"models": 1},
                )
                projection.execute("UPDATE storage_manifest SET schema_version=3")
                projection.commit()
            finally:
                state.close()
                projection.close()

            first = dbmod.bootstrap_storage(state_path, projection_path)
            self.assertEqual(first["status"], "ready")
            self.assertTrue(first["schema_upgraded"])
            state = dbmod.connect(state_path)
            projection = dbmod.connect(projection_path)
            try:
                self.assertIsNotNone(
                    state.execute(
                        "SELECT name FROM sqlite_master WHERE type='table' "
                        "AND name='draft_changesets'"
                    ).fetchone()
                )
                self.assertEqual(
                    state.execute(
                        "SELECT COUNT(*) c FROM draft_operations "
                        "WHERE draft_id='sentinel-draft'"
                    ).fetchone()["c"],
                    1,
                )
                self.assertEqual(
                    projection.execute(
                        "SELECT model_key FROM models WHERE model_key='sentinel-model'"
                    ).fetchone()["model_key"],
                    "sentinel-model",
                )
                self.assertEqual(
                    dbmod.storage_manifest(projection)["migration_id"],
                    "import-verified-v3",
                )
            finally:
                state.close()
                projection.close()

            second = dbmod.bootstrap_storage(state_path, projection_path)
            self.assertEqual(second["status"], "ready")
            self.assertFalse(second["schema_upgraded"])


if __name__ == "__main__":
    unittest.main()
