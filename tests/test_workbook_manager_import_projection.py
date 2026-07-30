"""Pass 2 storage-split and legacy-recovery regressions."""

from __future__ import annotations

import hashlib
import json
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "workbook-manager" / "backend"
SCRIPTS = ROOT / "scripts"
for path in (BACKEND, SCRIPTS):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from app import db as dbmod  # noqa: E402


class TestSplitStoreMigration(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory(prefix="wbm-pass2-")
        self.root = Path(self.tempdir.name)
        self.state_path = self.root / "workbook_manager.sqlite3"
        self.projection_path = self.root / "workbook_projection.sqlite3"

    def tearDown(self):
        self.tempdir.cleanup()

    def _legacy_database(self) -> tuple[bytes, dict[str, int]]:
        conn = dbmod.connect(self.state_path)
        dbmod.init_schema(conn)
        conn.execute(
            "INSERT INTO models(model_key, registry_key, src_sheet, src_row) "
            "VALUES('legacy_model', 'legacyRegistry', 'model_master', 2)"
        )
        pending_id = conn.execute(
            "INSERT INTO pending_changes(ts, session_id, table_name, model_id, "
            "entity_key_json, op, old_json, new_json, status, validation_json, "
            "confirmed_dependencies) VALUES(?,?,?,?,?,?,?,?,?,?,?)",
            (
                "2026-07-22T12:00:00+00:00",
                "legacy-session",
                "options",
                "legacy_model",
                '{"option_id":"opt_legacy"}',
                "update",
                '{"price":"1"}',
                '{"price":"2"}',
                "committed",
                '{"errors":[]}',
                1,
            ),
        ).lastrowid
        history_id = conn.execute(
            "INSERT INTO change_history(ts, actor, entity_type, entity_id, "
            "model_id, op, old_json, new_json, src_sheet, src_row, "
            "validation_result, status, sync_status, sync_detail, "
            "pending_change_id) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                "2026-07-22T12:01:00+00:00",
                "legacy-user",
                "options",
                "opt_legacy",
                "legacy_model",
                "update",
                '{"price":"1"}',
                '{"price":"2"}',
                "legacy_options",
                10,
                "passed",
                "committed",
                "pending",
                "",
                pending_id,
            ),
        ).lastrowid
        dbmod.set_meta(conn, "workbook_sha256", "abc123")
        dbmod.set_meta(conn, "workbook_mtime_ns", "456")
        dbmod.set_meta(conn, "last_import_run_id", "7")
        dbmod.set_meta(conn, "legacy_unknown_meta", "preserve-me")
        conn.commit()
        conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        conn.close()
        return self.state_path.read_bytes(), {
            "pending_changes": int(pending_id),
            "change_history": int(history_id),
        }

    def _assert_exact_recovery(self) -> None:
        state = dbmod.connect(self.state_path)
        try:
            rows = state.execute(
                "SELECT source_table, source_primary_key, row_json "
                "FROM legacy_recovery_records ORDER BY source_table"
            ).fetchall()
            self.assertEqual(len(rows), 2)
            self.assertEqual(
                {row["source_table"] for row in rows},
                {"pending_changes", "change_history"},
            )
            self.assertEqual(
                len({(row["source_table"], row["source_primary_key"]) for row in rows}),
                2,
            )
        finally:
            state.close()

    def test_first_start_splits_projection_and_preserves_exact_legacy_rows(self):
        legacy_bytes, ids = self._legacy_database()

        result = dbmod.bootstrap_storage(self.state_path, self.projection_path)

        self.assertEqual(result["status"], "migrated")
        self.assertTrue(self.projection_path.exists())
        archive = Path(result["archive_path"])
        self.assertTrue(archive.exists())
        self.assertEqual(archive.read_bytes(), legacy_bytes)
        self.assertIn(hashlib.sha256(legacy_bytes).hexdigest(), archive.name)

        projection = dbmod.connect(self.projection_path)
        state = dbmod.connect(self.state_path)
        try:
            self.assertEqual(
                projection.execute(
                    "SELECT registry_key FROM models WHERE model_key='legacy_model'"
                ).fetchone()["registry_key"],
                "legacyRegistry",
            )
            self.assertEqual(dbmod.get_meta(projection, "workbook_sha256"), "abc123")
            with self.assertRaises(sqlite3.OperationalError):
                projection.execute("SELECT * FROM pending_changes").fetchall()

            rows = state.execute(
                "SELECT source_table, source_primary_key, row_json "
                "FROM legacy_recovery_records ORDER BY source_table"
            ).fetchall()
            self.assertEqual(len(rows), 2)
            recovered = {row["source_table"]: json.loads(row["row_json"]) for row in rows}
            self.assertEqual(recovered["pending_changes"]["id"], ids["pending_changes"])
            self.assertEqual(recovered["pending_changes"]["confirmed_dependencies"], 1)
            self.assertEqual(recovered["change_history"]["id"], ids["change_history"])
            self.assertEqual(recovered["change_history"]["sync_status"], "pending")
            self.assertEqual(
                state.execute(
                    "SELECT value FROM durable_recovery_meta "
                    "WHERE key='legacy_unknown_meta'"
                ).fetchone()["value"],
                "preserve-me",
            )
            projection_marker = dbmod.storage_manifest(projection)
            state_marker = dbmod.storage_manifest(state)
            self.assertEqual(projection_marker["migration_id"], state_marker["migration_id"])
            self.assertEqual(projection_marker["source_sha256"], state_marker["source_sha256"])
            # Both stores must carry the version the code currently builds; a
            # literal here would go stale the moment a schema change lands.
            self.assertEqual(
                projection_marker["schema_version"], dbmod.SCHEMA_VERSION
            )
            self.assertEqual(state_marker["schema_version"], dbmod.SCHEMA_VERSION)
        finally:
            projection.close()
            state.close()

    def test_restart_is_idempotent_and_does_not_duplicate_recovery_rows(self):
        self._legacy_database()
        first = dbmod.bootstrap_storage(self.state_path, self.projection_path)
        state_before = self.state_path.read_bytes()
        projection_before = self.projection_path.read_bytes()

        second = dbmod.bootstrap_storage(self.state_path, self.projection_path)

        self.assertEqual(second["status"], "ready")
        self.assertEqual(second["migration_id"], first["migration_id"])
        self.assertEqual(self.state_path.read_bytes(), state_before)
        self.assertEqual(self.projection_path.read_bytes(), projection_before)
        state = dbmod.connect(self.state_path)
        try:
            self.assertEqual(
                state.execute("SELECT COUNT(*) c FROM legacy_recovery_records").fetchone()["c"],
                2,
            )
        finally:
            state.close()

    def test_new_install_initializes_two_matching_versioned_stores(self):
        result = dbmod.bootstrap_storage(self.state_path, self.projection_path)
        self.assertEqual(result["status"], "initialized")
        state = dbmod.connect(self.state_path)
        projection = dbmod.connect(self.projection_path)
        try:
            self.assertEqual(
                dbmod.storage_manifest(state)["migration_id"],
                dbmod.storage_manifest(projection)["migration_id"],
            )
            with self.assertRaises(sqlite3.OperationalError):
                projection.execute("SELECT * FROM pending_changes").fetchall()
            self.assertIsNotNone(
                state.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' "
                    "AND name='legacy_recovery_records'"
                ).fetchone()
            )
        finally:
            state.close()
            projection.close()

    def test_restart_recovers_partial_and_verified_archive_temporaries(self):
        legacy_bytes, _ = self._legacy_database()
        partial = self.root / f"{dbmod._ARCHIVE_TEMP_PREFIX}partial.tmp"
        partial.write_bytes(legacy_bytes[:100])
        verified = self.root / f"{dbmod._ARCHIVE_TEMP_PREFIX}verified.tmp"
        verified.write_bytes(legacy_bytes)

        result = dbmod.bootstrap_storage(self.state_path, self.projection_path)

        archive = Path(result["archive_path"])
        self.assertEqual(archive.read_bytes(), legacy_bytes)
        self.assertFalse(partial.exists())
        self.assertFalse(verified.exists())
        self._assert_exact_recovery()

    def test_multiple_verified_archive_temporaries_abort_as_ambiguous(self):
        legacy_bytes, _ = self._legacy_database()
        for suffix in ("one", "two"):
            path = self.root / f"{dbmod._ARCHIVE_TEMP_PREFIX}{suffix}.tmp"
            path.write_bytes(legacy_bytes)

        with self.assertRaisesRegex(RuntimeError, "ambiguous verified"):
            dbmod.bootstrap_storage(self.state_path, self.projection_path)

        self.assertEqual(self.state_path.read_bytes(), legacy_bytes)

    def test_restart_before_projection_replacement_keeps_legacy_authoritative(self):
        legacy_bytes, _ = self._legacy_database()
        with mock.patch.object(
            dbmod, "_replace_candidate", side_effect=RuntimeError("before replace")
        ):
            with self.assertRaisesRegex(RuntimeError, "before replace"):
                dbmod.bootstrap_storage(self.state_path, self.projection_path)
        self.assertEqual(self.state_path.read_bytes(), legacy_bytes)

        result = dbmod.bootstrap_storage(self.state_path, self.projection_path)
        self.assertEqual(result["status"], "migrated")
        self._assert_exact_recovery()

    def test_restart_after_projection_before_durable_replacement_is_idempotent(self):
        legacy_bytes, _ = self._legacy_database()
        real_replace = dbmod._replace_candidate
        calls = 0

        def fail_second(candidate, target):
            nonlocal calls
            calls += 1
            if calls == 2:
                raise RuntimeError("before durable replace")
            return real_replace(candidate, target)

        with mock.patch.object(dbmod, "_replace_candidate", side_effect=fail_second):
            with self.assertRaisesRegex(RuntimeError, "before durable replace"):
                dbmod.bootstrap_storage(self.state_path, self.projection_path)
        self.assertEqual(self.state_path.read_bytes(), legacy_bytes)

        result = dbmod.bootstrap_storage(self.state_path, self.projection_path)
        self.assertEqual(result["status"], "migrated")
        self._assert_exact_recovery()

    def test_restart_after_durable_replacement_uses_completed_marker(self):
        self._legacy_database()
        real_replace = dbmod._replace_candidate

        def fail_after_replace(candidate, target):
            real_replace(candidate, target)
            if Path(target) == self.state_path:
                raise RuntimeError("after durable replace")

        with mock.patch.object(dbmod, "_replace_candidate", side_effect=fail_after_replace):
            with self.assertRaisesRegex(RuntimeError, "after durable replace"):
                dbmod.bootstrap_storage(self.state_path, self.projection_path)

        result = dbmod.bootstrap_storage(self.state_path, self.projection_path)
        self.assertEqual(result["status"], "ready")
        self._assert_exact_recovery()


if __name__ == "__main__":
    unittest.main()
