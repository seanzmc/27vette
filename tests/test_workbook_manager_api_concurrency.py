"""Pass 3 request-connection and promotion-coordination regressions.

Owning specification: docs/superpowers/specs/2026-07-22-reliable-workbook-database-workflow.md
section 6, Pass 3. These tests own the "connection race" acceptance row of that
specification's section 8 matrix: concurrent first-load/status requests and
reader-draining promotion must succeed without lock errors.

Nothing here imports the canonical workbook or writes any tracked artifact; the
manager backend is exercised against temporary split stores only.
"""

from __future__ import annotations

import concurrent.futures
import contextlib
import importlib
import json
import os
import sqlite3
import sys
import tempfile
import threading
import time
import unittest
import uuid
from pathlib import Path
from unittest import mock

import anyio

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "workbook-manager" / "backend"
SCRIPTS = ROOT / "scripts"
for path in (BACKEND, SCRIPTS):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from app import db as dbmod  # noqa: E402

try:  # pragma: no cover - availability probe only
    from fastapi.testclient import TestClient  # noqa: F401

    HAVE_FASTAPI = True
except Exception:  # pragma: no cover
    HAVE_FASTAPI = False

WORKBOOK = ROOT / "stingray_master.xlsx"


def _pop_app_modules() -> dict:
    """Drop the whole ``app`` package so config re-reads the environment.

    The bare ``app`` entry must go too: leaving the package object behind makes
    ``from . import staging`` resolve to a stale module while
    ``from .staging import StagingError`` re-imports a fresh copy.

    The popped modules are returned so the caller can restore them; sibling test
    modules hold references to the original package objects, and leaving a purged
    or re-imported package behind gives them a second ``app.config`` whose paths
    disagree with the one their ``app.sync`` was bound to.
    """
    popped = {}
    for name in list(sys.modules):
        if name == "app" or name.startswith("app."):
            popped[name] = sys.modules.pop(name)
    return popped


@contextlib.contextmanager
def manager_app(root: Path, **extra_env):
    """Import a fresh manager app bound to temporary split stores."""
    env = {
        "WBM_DB": str(root / "workbook_manager.sqlite3"),
        "WBM_PROJECTION_DB": str(root / "workbook_projection.sqlite3"),
        "WBM_VAR_DIR": str(root / "var"),
        "WBM_WORKBOOK": str(WORKBOOK),
        **extra_env,
    }
    previous = {key: os.environ.get(key) for key in env}
    os.environ.update(env)
    original_modules = _pop_app_modules()
    try:
        main = importlib.import_module("app.main")
        yield main
    finally:
        _pop_app_modules()
        sys.modules.update(original_modules)
        for key, value in previous.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


def _manifest(path: Path) -> dict:
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    try:
        row = conn.execute("SELECT * FROM storage_manifest LIMIT 1").fetchone()
        return dict(row) if row else {}
    finally:
        conn.close()


def _legacy_combined_database(path: Path) -> int:
    """Write a legacy pre-split database with one unresolved journal row."""
    conn = dbmod.connect(path)
    dbmod.init_schema(conn)
    conn.execute(
        "INSERT INTO pending_changes(ts, table_name, model_id, entity_key_json, "
        "op, status) VALUES('2026-07-22T00:00:00+00:00', 'options', 'stingray', "
        "'{\"option_id\":\"opt_legacy\"}', 'update', 'staged')"
    )
    conn.commit()
    conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    conn.close()
    return 1


class TestConnectionPragmas(unittest.TestCase):
    """C3/C4: WAL plus a bounded busy timeout everywhere; foreign keys only for
    durable manager state."""

    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory(prefix="wbm-pass3-pragma-")
        self.root = Path(self.tempdir.name)

    def tearDown(self):
        self.tempdir.cleanup()

    def test_connect_sets_wal_and_the_configured_busy_timeout(self):
        """Assert the *configured* timeout: sqlite3's own default is already
        nonzero, so ``> 0`` would pass with the pragma removed."""
        conn = dbmod.connect(self.root / "plain.sqlite3")
        try:
            self.assertEqual(
                conn.execute("PRAGMA journal_mode").fetchone()[0].lower(), "wal"
            )
            self.assertEqual(
                conn.execute("PRAGMA busy_timeout").fetchone()[0],
                dbmod.BUSY_TIMEOUT_MS,
            )
            self.assertGreater(dbmod.BUSY_TIMEOUT_MS, 0)
        finally:
            conn.close()

    def test_busy_timeout_follows_the_environment_override(self):
        module = importlib.import_module("app.db")
        with mock.patch.dict(os.environ, {"WBM_BUSY_TIMEOUT_MS": "7321"}):
            reloaded = importlib.reload(module)
            try:
                self.assertEqual(reloaded.BUSY_TIMEOUT_MS, 7321)
                conn = reloaded.connect(self.root / "override.sqlite3")
                try:
                    self.assertEqual(
                        conn.execute("PRAGMA busy_timeout").fetchone()[0], 7321
                    )
                finally:
                    conn.close()
            finally:
                importlib.reload(module)

    def test_connect_leaves_foreign_keys_off_by_default(self):
        conn = dbmod.connect(self.root / "projection.sqlite3")
        try:
            self.assertEqual(conn.execute("PRAGMA foreign_keys").fetchone()[0], 0)
        finally:
            conn.close()

    def test_durable_connection_enforces_manager_owned_foreign_keys(self):
        path = self.root / "durable.sqlite3"
        conn = dbmod.connect(path, foreign_keys=True)
        try:
            dbmod.init_durable_schema(conn)
            self.assertEqual(conn.execute("PRAGMA foreign_keys").fetchone()[0], 1)
            with self.assertRaises(sqlite3.IntegrityError):
                conn.execute(
                    "INSERT INTO change_history(ts, entity_type, entity_id, op, "
                    "status, pending_change_id) VALUES('t', 'options', 'one', "
                    "'update', 'committed', 424242)"
                )
                conn.commit()
        finally:
            conn.close()

    def test_projection_connection_still_ingests_unresolved_workbook_reference(self):
        """Workbook references must be reported by import, never enforced by SQL."""
        path = self.root / "projection-refs.sqlite3"
        conn = dbmod.connect(path)
        try:
            dbmod.init_projection_schema(conn)
            conn.execute(
                "INSERT INTO options(model_id, option_id, section_id, src_sheet, "
                "src_row) VALUES('stingray', 'opt_orphan_001', "
                "'sec_does_not_exist_001', 'stingray_options', 5)"
            )
            conn.commit()
            self.assertEqual(
                conn.execute(
                    "SELECT COUNT(*) c FROM options WHERE option_id='opt_orphan_001'"
                ).fetchone()["c"],
                1,
            )
        finally:
            conn.close()


class TestDurableSchemaUpgrade(unittest.TestCase):
    """C4: a durable store built by an earlier pass must gain the manager-owned
    foreign key, or enabling enforcement on it proves nothing."""

    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory(prefix="wbm-pass3-upgrade-")
        self.root = Path(self.tempdir.name)
        self.state_path = self.root / "workbook_manager.sqlite3"
        self.projection_path = self.root / "workbook_projection.sqlite3"

    def tearDown(self):
        self.tempdir.cleanup()

    def _schema1_durable_store(self) -> int:
        """Recreate the pre-Pass-3 durable store: no FK on change_history."""
        conn = dbmod.connect(self.state_path)
        try:
            conn.execute(
                """CREATE TABLE pending_changes (
                  id INTEGER PRIMARY KEY AUTOINCREMENT,
                  ts TEXT NOT NULL, session_id TEXT NOT NULL DEFAULT '',
                  table_name TEXT NOT NULL, model_id TEXT NOT NULL DEFAULT '',
                  entity_key_json TEXT NOT NULL, op TEXT NOT NULL,
                  old_json TEXT, new_json TEXT,
                  status TEXT NOT NULL DEFAULT 'staged',
                  validation_json TEXT NOT NULL DEFAULT '{}',
                  confirmed_dependencies INTEGER NOT NULL DEFAULT 0
                )"""
            )
            conn.execute(
                """CREATE TABLE change_history (
                  id INTEGER PRIMARY KEY AUTOINCREMENT,
                  ts TEXT NOT NULL, actor TEXT NOT NULL DEFAULT '',
                  entity_type TEXT NOT NULL, entity_id TEXT NOT NULL,
                  model_id TEXT NOT NULL DEFAULT '', op TEXT NOT NULL,
                  old_json TEXT, new_json TEXT,
                  src_sheet TEXT NOT NULL DEFAULT '', src_row INTEGER,
                  validation_result TEXT NOT NULL DEFAULT '',
                  status TEXT NOT NULL,
                  sync_status TEXT NOT NULL DEFAULT 'pending',
                  sync_detail TEXT NOT NULL DEFAULT '',
                  pending_change_id INTEGER
                )"""
            )
            conn.execute(
                """CREATE TABLE legacy_recovery_records (
                  id INTEGER PRIMARY KEY AUTOINCREMENT, migration_id TEXT NOT NULL,
                  source_table TEXT NOT NULL, source_primary_key TEXT NOT NULL,
                  row_json TEXT NOT NULL, unresolved INTEGER NOT NULL DEFAULT 0,
                  UNIQUE(migration_id, source_table, source_primary_key)
                )"""
            )
            conn.execute(
                """CREATE TABLE durable_recovery_meta (
                  migration_id TEXT NOT NULL, key TEXT NOT NULL,
                  value TEXT NOT NULL, PRIMARY KEY(migration_id, key)
                )"""
            )
            conn.execute(
                "CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT NOT NULL)"
            )
            conn.execute(dbmod.MANIFEST_DDL)
            pending_id = conn.execute(
                "INSERT INTO pending_changes(ts, table_name, entity_key_json, op, "
                "status) VALUES('t', 'options', '{}', 'update', 'committed')"
            ).lastrowid
            conn.execute(
                "INSERT INTO change_history(ts, entity_type, entity_id, op, "
                "status, pending_change_id) VALUES('t', 'options', 'one', "
                "'update', 'committed', ?)",
                (pending_id,),
            )
            conn.execute(
                "INSERT INTO storage_manifest(store_kind, migration_id, "
                "source_sha256, schema_version, source_path, archive_path, "
                "table_counts_json) VALUES('durable', 'legacy-mig', 'sha', 1, "
                "?, '', '{}')",
                (str(self.state_path),),
            )
            conn.commit()
            conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        finally:
            conn.close()
        return 1

    def test_bootstrap_upgrades_a_schema1_durable_store_and_keeps_its_rows(self):
        rows = self._schema1_durable_store()
        result = dbmod.bootstrap_storage(self.state_path, self.projection_path)
        self.assertTrue(result["schema_upgraded"])

        conn = dbmod.connect(self.state_path, foreign_keys=True)
        try:
            self.assertTrue(dbmod._durable_history_declares_pending_fk(conn))
            self.assertEqual(
                conn.execute("SELECT COUNT(*) c FROM change_history").fetchone()["c"],
                rows,
            )
            self.assertEqual(
                conn.execute(
                    "SELECT COUNT(*) c FROM pending_changes"
                ).fetchone()["c"],
                1,
            )
            self.assertEqual(
                int(
                    conn.execute(
                        "SELECT schema_version FROM storage_manifest"
                    ).fetchone()["schema_version"]
                ),
                dbmod.SCHEMA_VERSION,
            )
            durable_tables = {
                row["name"]
                for row in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                )
            }
            self.assertTrue(
                {"workflow_drafts", "draft_operations"} <= durable_tables
            )
            with self.assertRaises(sqlite3.IntegrityError):
                conn.execute(
                    "INSERT INTO change_history(ts, entity_type, entity_id, op, "
                    "status, pending_change_id) VALUES('t', 'options', 'two', "
                    "'update', 'committed', 999999)"
                )
                conn.commit()
        finally:
            conn.close()

    def test_upgrade_preserves_and_reports_a_dangling_legacy_reference(self):
        """A legacy orphan is evidence: preserve it, but do not let it become
        invisible once enforcement is on (SQLite only checks on write)."""
        self._schema1_durable_store()
        conn = dbmod.connect(self.state_path)
        try:
            conn.execute(
                "INSERT INTO change_history(ts, entity_type, entity_id, op, "
                "status, pending_change_id) VALUES('t', 'options', 'orphan', "
                "'update', 'committed', 999999)"
            )
            conn.commit()
        finally:
            conn.close()

        result = dbmod.bootstrap_storage(self.state_path, self.projection_path)
        self.assertTrue(result["schema_upgraded"])
        self.assertEqual(result["orphan_history_rows"], 1)
        self.assertEqual(
            dbmod.durable_orphan_history_rows(self.state_path), 1
        )
        conn = dbmod.connect(self.state_path, foreign_keys=True)
        try:
            self.assertEqual(
                conn.execute(
                    "SELECT COUNT(*) c FROM change_history WHERE "
                    "entity_id='orphan'"
                ).fetchone()["c"],
                1,
            )
            # The store stays writable and the orphan row stays updatable.
            conn.execute(
                "UPDATE change_history SET sync_detail='seen' WHERE "
                "entity_id='orphan'"
            )
            conn.commit()
        finally:
            conn.close()

    def test_fresh_bootstrap_reports_no_upgrade_and_no_orphans(self):
        result = dbmod.bootstrap_storage(self.state_path, self.projection_path)
        self.assertEqual(result["status"], "initialized")
        self.assertFalse(result["schema_upgraded"])
        self.assertEqual(result["orphan_history_rows"], 0)

    def test_upgrade_is_idempotent_across_restarts(self):
        self._schema1_durable_store()
        first = dbmod.bootstrap_storage(self.state_path, self.projection_path)
        self.assertTrue(first["schema_upgraded"])
        second = dbmod.bootstrap_storage(self.state_path, self.projection_path)
        self.assertFalse(second["schema_upgraded"])
        self.assertEqual(second["status"], "ready")
        conn = dbmod.connect(self.state_path)
        try:
            self.assertEqual(
                conn.execute("SELECT COUNT(*) c FROM change_history").fetchone()["c"],
                1,
            )
            self.assertEqual(
                conn.execute(
                    "SELECT COUNT(*) c FROM sqlite_master WHERE name="
                    "'change_history_schema1'"
                ).fetchone()["c"],
                0,
            )
        finally:
            conn.close()

    def test_v3_durable_upgrade_preserves_a_verified_v3_projection(self):
        state = dbmod.connect(self.state_path)
        projection = dbmod.connect(self.projection_path)
        try:
            dbmod.init_durable_schema(state)
            state.execute("DROP TABLE draft_operations")
            state.execute("DROP TABLE workflow_drafts")
            dbmod._write_manifest(
                state,
                store_kind="durable",
                migration_id="split-v3",
                source_sha256="legacy-sha",
                source_path=self.state_path,
                archive_path=None,
                table_counts={},
            )
            state.execute("UPDATE storage_manifest SET schema_version=3")
            state.commit()

            dbmod.init_projection_schema(projection)
            projection.execute(
                "INSERT INTO models(src_sheet, src_row, model_key, active) "
                "VALUES('model_master', 2, 'sentinel', 'True')"
            )
            projection.execute(
                "INSERT INTO import_runs(ts, workbook_path, "
                "workbook_mtime_ns, workbook_sha256, status) "
                "VALUES('t', '/tmp/source.xlsx', '123', 'verified-sha', 'imported')"
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

        first = dbmod.bootstrap_storage(self.state_path, self.projection_path)
        self.assertEqual(first["status"], "ready")
        self.assertTrue(first["schema_upgraded"])

        projection = dbmod.connect(self.projection_path)
        state = dbmod.connect(self.state_path)
        try:
            self.assertEqual(
                projection.execute(
                    "SELECT model_key FROM models WHERE model_key='sentinel'"
                ).fetchone()["model_key"],
                "sentinel",
            )
            self.assertEqual(
                dbmod.storage_manifest(projection)["migration_id"],
                "import-verified-v3",
            )
            self.assertIsNotNone(
                state.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' "
                    "AND name='workflow_drafts'"
                ).fetchone()
            )
        finally:
            projection.close()
            state.close()

        second = dbmod.bootstrap_storage(self.state_path, self.projection_path)
        self.assertEqual(second["status"], "ready")
        self.assertFalse(second["schema_upgraded"])


class TestProjectionReaderGate(unittest.TestCase):
    """C6: promotion drains readers deterministically and fails closed."""

    def setUp(self):
        self.gate = dbmod.ProjectionGate()

    def test_quiesce_waits_for_an_open_reader_then_proceeds(self):
        entered = threading.Event()
        released = threading.Event()

        def promote():
            with self.gate.quiesce(timeout=5.0):
                entered.set()

        with self.gate.reader(timeout=5.0):
            self.assertEqual(self.gate.active_readers, 1)
            worker = threading.Thread(target=promote)
            worker.start()
            self.assertFalse(
                entered.wait(0.2), "quiesce entered while a reader was open"
            )
            released.set()
        worker.join(5.0)
        self.assertTrue(released.is_set())
        self.assertTrue(entered.wait(5.0), "quiesce never proceeded after drain")
        self.assertFalse(self.gate.blocked)
        self.assertEqual(self.gate.active_readers, 0)

    def test_reader_arriving_during_quiesce_waits_for_promotion_to_finish(self):
        order: list[str] = []
        reader_entered = threading.Event()

        def read():
            with self.gate.reader(timeout=5.0):
                order.append("reader")
                reader_entered.set()

        with self.gate.quiesce(timeout=5.0):
            worker = threading.Thread(target=read)
            worker.start()
            self.assertFalse(
                reader_entered.wait(0.2), "reader entered during promotion"
            )
            order.append("promotion")
        worker.join(5.0)
        self.assertTrue(reader_entered.wait(5.0))
        self.assertEqual(order, ["promotion", "reader"])

    def test_quiesce_fails_closed_when_readers_do_not_drain(self):
        with self.gate.reader(timeout=5.0):
            with self.assertRaises(dbmod.ProjectionBusyError):
                with self.gate.quiesce(timeout=0.05):
                    self.fail("quiesce entered without draining readers")
        # A failed quiesce must not leave new readers blocked.
        self.assertFalse(self.gate.blocked)
        with self.gate.reader(timeout=1.0):
            self.assertEqual(self.gate.active_readers, 1)

    def test_reader_fails_closed_while_promotion_holds_the_gate(self):
        with self.gate.quiesce(timeout=5.0):
            with self.assertRaises(dbmod.ProjectionBusyError):
                with self.gate.reader(timeout=0.05):
                    self.fail("reader entered while promotion held the gate")

    def test_projection_replacement_happens_under_the_gate(self):
        """Removing the quiesce from `_replace_projection` must fail here: the
        swap itself, not just its caller, is what has to be gated."""
        observed = []
        real_replace = dbmod._replace_candidate

        def spy(candidate, target):
            observed.append(dbmod.PROJECTION_GATE.blocked)
            return real_replace(candidate, target)

        tempdir = tempfile.TemporaryDirectory(prefix="wbm-pass3-swap-")
        self.addCleanup(tempdir.cleanup)
        root = Path(tempdir.name)
        candidate = root / "candidate.sqlite3"
        target = root / "projection.sqlite3"
        candidate.write_bytes(b"candidate")
        with mock.patch.object(dbmod, "_replace_candidate", spy):
            dbmod._replace_projection(candidate, target)
        self.assertEqual(observed, [True], "projection was replaced ungated")
        self.assertFalse(dbmod.PROJECTION_GATE.blocked)
        self.assertEqual(target.read_bytes(), b"candidate")

    def test_projection_replacement_waits_for_an_open_reader(self):
        tempdir = tempfile.TemporaryDirectory(prefix="wbm-pass3-swap-wait-")
        self.addCleanup(tempdir.cleanup)
        root = Path(tempdir.name)
        candidate = root / "candidate.sqlite3"
        candidate.write_bytes(b"candidate")
        replaced = threading.Event()

        def promote():
            dbmod._replace_projection(candidate, root / "projection.sqlite3")
            replaced.set()

        with dbmod.PROJECTION_GATE.reader(timeout=5.0):
            worker = threading.Thread(target=promote)
            worker.start()
            self.assertFalse(
                replaced.wait(0.2), "projection replaced while a reader was open"
            )
        worker.join(5.0)
        self.assertTrue(replaced.wait(5.0))


@unittest.skipUnless(
    HAVE_FASTAPI,
    "fastapi not installed; install workbook-manager/backend/requirements.txt",
)
class TestLifespanAndRequestConnections(unittest.TestCase):
    """C1/C2/C5/C8: lifespan bootstrap, per-request connections, one lock."""

    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory(prefix="wbm-pass3-api-")
        self.root = Path(self.tempdir.name)

    def tearDown(self):
        self.tempdir.cleanup()

    @staticmethod
    def _insert_history_draft(
        state,
        *,
        draft_id: str,
        status: str,
        updated_ts: str,
        model: str = "stingray",
        apply_result: dict | None = None,
        allowed_verbs: list[str] | None = None,
    ) -> None:
        state.execute(
            "INSERT INTO workflow_drafts(id, created_ts, updated_ts, session_id, "
            "actor, status, base_workbook_sha256, base_workbook_mtime_ns) "
            "VALUES(?,?,?,?,?,?,?,?)",
            (
                draft_id, "2026-08-29T10:00:00+00:00", updated_ts, "session-1",
                "Sean", status, f"{draft_id}-base-sha", "123",
            ),
        )
        state.execute(
            "INSERT INTO draft_operations(draft_id, created_ts, updated_ts, "
            "table_name, family, model_id, source_sheet, source_row, physical_key, "
            "entity_key_json, action, original_json, final_json, changed_fields_json, "
            "model_context_json) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                draft_id, "2026-08-29T10:00:00+00:00", updated_ts, "options",
                "options", model, f"{model}_options", 10, '["opt_test"]',
                '{"option_id":"opt_test"}', "update", "{}", "{}", "{}",
                json.dumps([model]),
            ),
        )
        if apply_result is None:
            state.commit()
            return
        change_set_id = f"changeset-{draft_id}"
        semantic = f"semantic-{draft_id}"
        preview_id = f"preview-{draft_id}"
        approval_id = f"approval-{draft_id}"
        state.execute(
            "INSERT INTO draft_changesets(draft_id, created_ts, change_set_id, "
            "semantic_fingerprint, payload_json) VALUES(?,?,?,?,?)",
            (draft_id, updated_ts, change_set_id, semantic, '{"schemaVersion":"workbook-changeset-1"}'),
        )
        state.execute(
            "INSERT INTO draft_preview_attempts(id, draft_id, change_set_id, "
            "semantic_fingerprint, started_ts, completed_ts, artifact_kind, "
            "result_json, workbook_identity_state, manager_state, allowed_verbs_json) "
            "VALUES(?,?,?,?,?,?,?,?,?,?,?)",
            (
                preview_id, draft_id, change_set_id, semantic, updated_ts, updated_ts,
                "formal_preview", "{}", "unchanged", "preview_ready", "[]",
            ),
        )
        state.execute(
            "INSERT INTO draft_approval_attempts(id, draft_id, preview_attempt_id, "
            "change_set_id, semantic_fingerprint, preview_fingerprint, actor, "
            "warning_ids_json, started_ts, completed_ts, artifact_kind, result_json, "
            "manager_state, allowed_verbs_json) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                approval_id, draft_id, preview_id, change_set_id, semantic,
                f"preview-fingerprint-{draft_id}", "Sean", "[]", updated_ts,
                updated_ts, "formal_approval", "{}", "approved", "[]",
            ),
        )
        state.execute(
            "INSERT INTO draft_apply_attempts(id, draft_id, preview_attempt_id, "
            "approval_attempt_id, change_set_id, semantic_fingerprint, "
            "preview_fingerprint, approval_fingerprint, started_ts, completed_ts, "
            "artifact_kind, result_json, workbook_identity_state, manager_state, "
            "allowed_verbs_json, active) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,0)",
            (
                f"apply-{draft_id}", draft_id, preview_id, approval_id, change_set_id,
                semantic, f"preview-fingerprint-{draft_id}",
                f"approval-fingerprint-{draft_id}", updated_ts, updated_ts,
                "formal_receipt", json.dumps(apply_result), "unchanged", status,
                json.dumps(allowed_verbs or []),
            ),
        )
        state.commit()

    def test_lifespan_bootstraps_storage_before_serving_any_request(self):
        from fastapi.testclient import TestClient

        with manager_app(self.root) as main:
            projection_path = main.config.DEFAULT_PROJECTION_DB
            state_path = main.config.DEFAULT_DB
            self.assertFalse(projection_path.exists())
            with TestClient(main.app) as client:
                # No request issued yet: startup alone must have built both stores.
                self.assertTrue(state_path.exists())
                self.assertTrue(projection_path.exists())
                projection = _manifest(projection_path)
                durable = _manifest(state_path)
                self.assertEqual(projection["store_kind"], "projection")
                self.assertEqual(durable["store_kind"], "durable")
                self.assertEqual(
                    projection["migration_id"], durable["migration_id"]
                )
                self.assertEqual(
                    main.app.state.storage_bootstrap["migration_id"],
                    durable["migration_id"],
                )
                self.assertEqual(client.get("/api/status").status_code, 200)

    def test_current_workflow_history_is_versioned_and_separate_from_legacy(self):
        """HIST-01/HIST-04: durable Apply evidence is not legacy history."""
        from fastapi.testclient import TestClient

        with manager_app(self.root) as main:
            with TestClient(main.app) as client:
                state = main.dbmod.connect(
                    main.config.DEFAULT_DB, foreign_keys=True
                )
                try:
                    state.execute(
                        "INSERT INTO workflow_drafts(id, created_ts, updated_ts, "
                        "session_id, actor, status, base_workbook_sha256, "
                        "base_workbook_mtime_ns) VALUES(?,?,?,?,?,?,?,?)",
                        (
                            "draft-applied", "2026-08-29T10:00:00+00:00",
                            "2026-08-29T10:05:00+00:00", "session-1", "Sean",
                            "applied", "base-sha", "123",
                        ),
                    )
                    state.execute(
                        "INSERT INTO draft_operations(draft_id, created_ts, updated_ts, "
                        "table_name, family, model_id, source_sheet, source_row, "
                        "physical_key, entity_key_json, action, original_json, "
                        "final_json, changed_fields_json, model_context_json) "
                        "VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                        (
                            "draft-applied", "2026-08-29T10:00:00+00:00",
                            "2026-08-29T10:01:00+00:00", "options", "options",
                            "stingray", "stingray_options", 10, '["opt_test"]',
                            '{"option_id":"opt_test"}', "update", "{}", "{}",
                            "{}", '["stingray"]',
                        ),
                    )
                    state.execute(
                        "INSERT INTO change_history(ts, actor, entity_type, entity_id, "
                        "model_id, op, status, sync_status) VALUES(?,?,?,?,?,?,?,?)",
                        (
                            "2026-07-01T00:00:00+00:00", "Legacy", "options",
                            "opt_legacy", "stingray", "update", "committed", "synced",
                        ),
                    )
                    state.commit()
                finally:
                    state.close()

                current = client.get(
                    "/api/workflow-history",
                    params={"status": "applied", "model": "stingray", "limit": 25},
                )
                self.assertEqual(200, current.status_code, current.text)
                payload = current.json()
                self.assertEqual(
                    "workbook-manager-workflow-history-1", payload["schema_version"]
                )
                self.assertEqual(1, payload["total"])
                self.assertEqual(["applied"], payload["available_statuses"])
                record = payload["history"][0]
                self.assertEqual("draft-applied", record["draft_id"])
                self.assertEqual("/api/drafts/draft-applied", record["draft_api_url"])
                self.assertEqual("Sean", record["actor"])
                self.assertEqual(["stingray"], record["affected_models"])
                self.assertEqual(1, record["operation_count"])
                self.assertEqual("base-sha", record["workbook"]["base_sha256"])

                legacy = client.get("/api/history").json()
                self.assertEqual(1, legacy["total"])
                self.assertEqual("opt_legacy", legacy["history"][0]["entity_id"])

    def test_workflow_history_summarizes_apply_and_restored_failure_evidence(self):
        """HIST-01/HIST-02: outcomes derive from immutable attempts."""
        from fastapi.testclient import TestClient

        success = {
            "ok": True,
            "status": "applied",
            "workbookState": "saved",
            "applyRebuild": {
                "status": "current",
                "affected_models": ["stingray"],
                "workbook": {
                    "state": "applied",
                    "before_sha256": "before-sha",
                    "after_sha256": "after-sha",
                },
                "generated_contracts": {"state": "current"},
                "publication": {"state": "current"},
                "rollback": {"state": "not_required", "verified": True},
            },
        }
        failure = {
            "ok": False,
            "status": "apply_rebuild_failed_rolled_back",
            "workbookState": "restored",
            "errors": ["RuntimeError: generation failed"],
            "applyRebuild": {
                "status": "restored",
                "workbook": {"state": "restored"},
                "generated_contracts": {"state": "restored"},
                "publication": {"state": "restored"},
                "rollback": {"state": "verified", "verified": True},
            },
        }
        with manager_app(self.root) as main:
            with TestClient(main.app) as client:
                state = main.dbmod.connect(main.config.DEFAULT_DB, foreign_keys=True)
                try:
                    self._insert_history_draft(
                        state, draft_id="draft-applied", status="applied",
                        updated_ts="2026-08-29T10:05:00+00:00", apply_result=success,
                    )
                    operation_id = state.execute(
                        "SELECT id FROM draft_operations WHERE draft_id=?",
                        ("draft-applied",),
                    ).fetchone()["id"]
                    state.execute(
                        "INSERT INTO draft_asset_resolutions(draft_id, operation_id, "
                        "created_ts, updated_ts, item_id, resolution_kind, "
                        "reconciliation_sha256, media_inventory_sha256, workbook_sha256, "
                        "media_url, candidate_source, candidate_reason, evidence_json) "
                        "VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",
                        (
                            "draft-applied", operation_id,
                            "2026-08-29T10:04:00+00:00",
                            "2026-08-29T10:04:00+00:00", "asset-item-1", "accepted",
                            "reconciliation-sha", "inventory-sha", "workbook-sha",
                            "https://example.invalid/asset.jpg", "exact_rpo",
                            "deterministic match", '{"reviewed":true}',
                        ),
                    )
                    state.commit()
                    self._insert_history_draft(
                        state, draft_id="draft-restored",
                        status="apply_restored_retryable",
                        updated_ts="2026-08-29T10:06:00+00:00", apply_result=failure,
                        allowed_verbs=["retry_apply", "cancel"],
                    )
                finally:
                    state.close()

                records = {
                    row["draft_id"]: row
                    for row in client.get("/api/workflow-history").json()["history"]
                }
                applied = records["draft-applied"]
                self.assertEqual("Applied and rebuilt", applied["outcome"]["summary"])
                self.assertEqual("after-sha", applied["workbook"]["after_sha256"])
                self.assertEqual("current", applied["outcome"]["generation_state"])
                self.assertEqual("current", applied["outcome"]["publication_state"])
                self.assertEqual(
                    success,
                    applied["technical_evidence"]["apply_attempts"][0]["result"],
                )
                asset_evidence = applied["technical_evidence"]["asset_resolutions"]
                self.assertEqual("asset-item-1", asset_evidence[0]["item_id"])
                self.assertEqual({"reviewed": True}, asset_evidence[0]["evidence"])

                restored = records["draft-restored"]
                self.assertEqual(
                    "Rebuild or publication failed; protected files restored",
                    restored["outcome"]["summary"],
                )
                self.assertEqual("rebuild_or_publication", restored["outcome"]["failed_stage"])
                self.assertEqual("RuntimeError: generation failed", restored["outcome"]["error"])
                self.assertEqual(
                    ["workbook", "generated_contracts", "publication"],
                    restored["outcome"]["restored_surfaces"],
                )
                self.assertEqual(["retry_apply", "cancel"], restored["outcome"]["next_actions"])

    def test_workflow_history_paginates_terminal_records_without_projection(self):
        """HIST-03: rejected/cancelled history survives missing projection."""
        from fastapi.testclient import TestClient

        with manager_app(self.root) as main:
            with TestClient(main.app) as client:
                state = main.dbmod.connect(main.config.DEFAULT_DB, foreign_keys=True)
                try:
                    self._insert_history_draft(
                        state, draft_id="draft-rejected", status="preview_rejected",
                        updated_ts="2026-08-29T10:05:00+00:00",
                    )
                    self._insert_history_draft(
                        state, draft_id="draft-cancelled", status="cancelled",
                        updated_ts="2026-08-29T10:05:00+00:00",
                    )
                finally:
                    state.close()
                main.config.DEFAULT_PROJECTION_DB.unlink()

                first = client.get(
                    "/api/workflow-history", params={"limit": 1, "offset": 0}
                )
                second = client.get(
                    "/api/workflow-history", params={"limit": 1, "offset": 1}
                )
                self.assertEqual(200, first.status_code, first.text)
                self.assertEqual(200, second.status_code, second.text)
                self.assertEqual(2, first.json()["total"])
                self.assertEqual("draft-rejected", first.json()["history"][0]["draft_id"])
                self.assertEqual("draft-cancelled", second.json()["history"][0]["draft_id"])
                for payload in (first.json(), second.json()):
                    self.assertNotIn(
                        "applied", payload["history"][0]["outcome"]["summary"].lower()
                    )

                invalid = client.get(
                    "/api/workflow-history", params={"status": "mutable_draft"}
                )
                self.assertEqual(422, invalid.status_code, invalid.text)
                self.assertEqual(
                    "invalid_history_status", invalid.json()["detail"]["status"]
                )

    def test_workflow_history_read_is_bounded_and_nonmutating(self):
        """The durable read model has a fixed query budget and cannot write."""
        with manager_app(self.root) as main:
            from fastapi.testclient import TestClient

            with TestClient(main.app):
                state = main.dbmod.connect(main.config.DEFAULT_DB, foreign_keys=True)
                try:
                    self._insert_history_draft(
                        state, draft_id="draft-a", status="cancelled",
                        updated_ts="2026-08-29T10:05:00+00:00",
                    )
                    self._insert_history_draft(
                        state, draft_id="draft-b", status="preview_rejected",
                        updated_ts="2026-08-29T10:05:00+00:00",
                    )
                    statements = []
                    state.set_trace_callback(statements.append)

                    def deny_writes(action, _arg1, _arg2, _database, _trigger):
                        if action in {
                            sqlite3.SQLITE_INSERT,
                            sqlite3.SQLITE_UPDATE,
                            sqlite3.SQLITE_DELETE,
                        }:
                            return sqlite3.SQLITE_DENY
                        return sqlite3.SQLITE_OK

                    state.set_authorizer(deny_writes)
                    payload = main.drafts.workflow_history(state, limit=25)
                finally:
                    state.close()

                self.assertEqual(
                    ["draft-b", "draft-a"],
                    [record["draft_id"] for record in payload["history"]],
                )
                select_count = sum(
                    statement.lstrip().upper().startswith("SELECT")
                    for statement in statements
                )
                self.assertLessEqual(select_count, 10, statements)

    def test_structure_schema_endpoint_serves_read_only_projections(self):
        """`/api/tables` renders every STRUCTURE_TABLE, writable or not.

        `form_sections` is a read-only projection with no editor family; when
        its columns were graded against the writable control inventory the
        whole endpoint returned 500.
        """
        from fastapi.testclient import TestClient

        with manager_app(self.root) as main:
            with TestClient(main.app) as client:
                response = client.get("/api/tables")
                self.assertEqual(200, response.status_code, response.text)
                tables = {
                    t["table"]: t
                    for t in response.json()["structure_tables"]
                }
                self.assertEqual(
                    set(main.STRUCTURE_TABLES), set(tables),
                    "every structure table must be rendered",
                )
                sections = tables["form_sections"]
                self.assertFalse(sections["editable"])
                self.assertTrue(sections["columns"])
                for column in sections["columns"]:
                    self.assertEqual(
                        "read_only", column["control"]["kind"], column["name"]
                    )

                schema = client.get("/api/records/form_sections/schema")
                self.assertEqual(200, schema.status_code, schema.text)
                self.assertFalse(schema.json()["editable"])

    def test_each_request_opens_and_closes_its_own_connections(self):
        from fastapi.testclient import TestClient

        with manager_app(self.root) as main:
            with TestClient(main.app) as client:
                self.assertEqual(client.get("/api/status").status_code, 200)
                self.assertEqual(main.dbmod.PROJECTION_GATE.active_readers, 0)

                seen = []
                for dependency in (main.projection_connection, main.state_connection):
                    conns = []
                    for _ in range(2):
                        generator = dependency()
                        conn = next(generator)
                        conns.append(conn)
                        with contextlib.suppress(StopIteration):
                            next(generator)
                        with self.assertRaises(sqlite3.ProgrammingError):
                            conn.execute("SELECT 1")
                    self.assertIsNot(conns[0], conns[1])
                    seen.append(conns)
                self.assertIsNot(seen[0][0], seen[1][0])

    def test_request_connections_carry_wal_timeout_and_scoped_foreign_keys(self):
        with manager_app(self.root) as main:
            from fastapi.testclient import TestClient

            with TestClient(main.app):
                expected = {"projection": 0, "state": 1}
                for kind, dependency in (
                    ("projection", main.projection_connection),
                    ("state", main.state_connection),
                ):
                    generator = dependency()
                    conn = next(generator)
                    try:
                        self.assertEqual(
                            conn.execute("PRAGMA journal_mode").fetchone()[0].lower(),
                            "wal",
                            kind,
                        )
                        self.assertGreater(
                            conn.execute("PRAGMA busy_timeout").fetchone()[0], 0, kind
                        )
                        self.assertEqual(
                            conn.execute("PRAGMA foreign_keys").fetchone()[0],
                            expected[kind],
                            kind,
                        )
                    finally:
                        with contextlib.suppress(StopIteration):
                            next(generator)

    def test_no_module_level_connection_or_accessor_survives_a_request(self):
        from fastapi.testclient import TestClient

        with manager_app(self.root) as main:
            with TestClient(main.app) as client:
                self.assertEqual(client.get("/api/status").status_code, 200)
            # Not `getattr(..., None)`: that passes for an attribute holding a
            # live connection *or* one that never existed. Require absence, and
            # require the lazy accessors to be gone from the source too.
            for attribute in ("_conn", "_state_conn", "_storage_bootstrapped"):
                self.assertFalse(
                    hasattr(main, attribute),
                    f"{attribute} retained process-wide connection state",
                )
            source = (
                ROOT / "workbook-manager" / "backend" / "app" / "main.py"
            ).read_text()
            for accessor in ("def get_conn", "def get_state_conn"):
                self.assertNotIn(accessor, source)
            for connection in main.dbmod.__dict__.values():
                self.assertNotIsInstance(connection, sqlite3.Connection)

    def test_requests_report_an_explicit_reason_without_the_lifespan(self):
        """Serving the app without its lifespan must fail closed with a clear
        message, not an opaque missing-table error."""
        from fastapi.testclient import TestClient

        with manager_app(self.root) as main:
            client = TestClient(main.app)  # deliberately not entered
            response = client.get("/api/status")
            self.assertEqual(response.status_code, 503)
            detail = response.json()["detail"]
            self.assertEqual(detail["status"], "storage_not_bootstrapped")
            self.assertIn("lifespan", detail["message"])

    def test_concurrent_first_load_uses_independent_connections(self):
        from fastapi.testclient import TestClient

        with manager_app(self.root) as main:
            with TestClient(main.app) as client:
                with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
                    responses = list(
                        pool.map(lambda _: client.get("/api/status"), range(16))
                    )
            for response in responses:
                self.assertEqual(response.status_code, 200, response.text)
                self.assertNotIn("database is locked", response.text)
            projection = _manifest(main.config.DEFAULT_PROJECTION_DB)
            durable = _manifest(main.config.DEFAULT_DB)
            self.assertEqual(projection["migration_id"], durable["migration_id"])
            self.assertEqual(main.dbmod.PROJECTION_GATE.active_readers, 0)

    def test_concurrent_first_load_migrates_a_legacy_database_exactly_once(self):
        from fastapi.testclient import TestClient

        state_path = self.root / "workbook_manager.sqlite3"
        legacy_rows = _legacy_combined_database(state_path)
        with manager_app(self.root) as main:
            with TestClient(main.app) as client:
                with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
                    responses = list(
                        pool.map(lambda _: client.get("/api/status"), range(8))
                    )
            for response in responses:
                self.assertEqual(response.status_code, 200, response.text)
            durable = sqlite3.connect(main.config.DEFAULT_DB)
            durable.row_factory = sqlite3.Row
            try:
                self.assertEqual(
                    durable.execute(
                        "SELECT COUNT(*) c FROM legacy_recovery_records"
                    ).fetchone()["c"],
                    legacy_rows,
                )
                migrations = durable.execute(
                    "SELECT COUNT(DISTINCT migration_id) c FROM legacy_recovery_records"
                ).fetchone()["c"]
                self.assertEqual(migrations, 1)
            finally:
                durable.close()
            archives = list(self.root.glob("*.legacy-split-*.sqlite3"))
            self.assertEqual(len(archives), 1, archives)
            self.assertEqual(
                list(self.root.glob(f"{dbmod._ARCHIVE_TEMP_PREFIX}*")), []
            )

    def test_every_durable_mutating_endpoint_holds_the_shared_process_lock(self):
        """Covers every mutating route, not a sample: dropping the dependency
        from any one of them must fail this test."""
        from fastapi.testclient import TestClient

        with manager_app(self.root) as main:
            with TestClient(main.app) as client:
                # A staged row makes /api/import refuse fast, after its
                # dependencies resolve, so the lock claim is still observed
                # without running a full workbook import.
                state = main.open_state_connection()
                try:
                    state.execute(
                        "INSERT INTO pending_changes(ts, table_name, "
                        "entity_key_json, op, status) VALUES('t', 'options', "
                        "'{}', 'update', 'staged')"
                    )
                    state.commit()
                finally:
                    state.close()

                acquisitions: list[str] = []
                real_lock = main.dbmod.STATE_LOCK

                class TrackingLock:
                    def acquire(self, blocking=True, timeout=-1):
                        acquired = real_lock.acquire(blocking, timeout)
                        if acquired:
                            acquisitions.append("acquired")
                        return acquired

                    def release(self):
                        real_lock.release()

                    def __enter__(self):
                        self.acquire()
                        return True

                    def __exit__(self, *exc):
                        self.release()
                        return False

                main.dbmod.STATE_LOCK = TrackingLock()
                try:
                    calls = {
                        "import": lambda: client.post("/api/import"),
                        "stage": lambda: client.post(
                            "/api/changes",
                            json={
                                "table": "options",
                                "model_id": "nope",
                                "op": "add",
                                "key": {"option_id": "opt_x"},
                                "record": {"option_id": "opt_x"},
                            },
                        ),
                        "discard": lambda: client.delete("/api/changes/1"),
                        "validate": lambda: client.post("/api/changes/validate"),
                        "commit": lambda: client.post(
                            "/api/changes/commit", json={"actor": "test"}
                        ),
                        "sync": lambda: client.post(
                            "/api/sync", json={"write": False}
                        ),
                        "backup": lambda: client.post("/api/backup"),
                    }
                    for name, call in calls.items():
                        acquisitions.clear()
                        call()
                        self.assertTrue(
                            acquisitions, f"{name} did not hold the shared lock"
                        )
                finally:
                    main.dbmod.STATE_LOCK = real_lock

    def test_lock_contention_cannot_starve_the_request_threadpool(self):
        """The lock must be awaited on the event loop, not from a threadpool
        worker: parked workers consume anyio tokens, and once every token is
        parked the lock holder can never get a thread to release it."""
        import inspect

        from fastapi.testclient import TestClient

        with manager_app(self.root) as main:
            self.assertTrue(
                inspect.isasyncgenfunction(main.durable_write_lock),
                "durable_write_lock must be an async dependency",
            )
            with TestClient(main.app) as client:
                def shrink():
                    limiter = anyio.to_thread.current_default_thread_limiter()
                    limiter.total_tokens = 4

                client.portal.call(shrink)
                requests = 12
                with concurrent.futures.ThreadPoolExecutor(
                    max_workers=requests
                ) as pool:
                    futures = [
                        pool.submit(client.post, "/api/backup")
                        for _ in range(requests)
                    ]
                    done, pending = concurrent.futures.wait(futures, timeout=60)
                self.assertEqual(
                    len(pending), 0, f"{len(pending)} requests never completed"
                )
                for future in done:
                    self.assertEqual(future.result().status_code, 200)

    def test_concurrent_durable_mutations_do_not_report_lock_errors(self):
        from fastapi.testclient import TestClient

        with manager_app(self.root) as main:
            with TestClient(main.app) as client:
                with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
                    responses = list(
                        pool.map(lambda _: client.post("/api/backup"), range(6))
                    )
            for response in responses:
                self.assertEqual(response.status_code, 200, response.text)
                self.assertNotIn("database is locked", response.text)


@unittest.skipUnless(
    HAVE_FASTAPI,
    "fastapi not installed; install workbook-manager/backend/requirements.txt",
)
class TestPromotionReaderDrain(unittest.TestCase):
    """C6/C7: a gated swap quiesces request readers and is then visible."""

    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory(prefix="wbm-pass3-promote-")
        self.root = Path(self.tempdir.name)

    def tearDown(self):
        self.tempdir.cleanup()

    def test_requests_are_refused_while_promotion_holds_the_projection_gate(self):
        from fastapi.testclient import TestClient

        with manager_app(self.root, WBM_READER_WAIT_SECONDS="0.05") as main:
            with TestClient(main.app) as client:
                self.assertEqual(client.get("/api/status").status_code, 200)
                with main.dbmod.PROJECTION_GATE.quiesce(timeout=5.0):
                    blocked = client.get("/api/status")
                self.assertEqual(blocked.status_code, 503)
                self.assertIn("projection", blocked.text.lower())
                self.assertEqual(client.get("/api/status").status_code, 200)

    def test_promotion_waits_for_an_in_flight_reader_before_replacement(self):
        from fastapi.testclient import TestClient

        with manager_app(self.root) as main:
            with TestClient(main.app) as client:
                self.assertEqual(client.get("/api/status").status_code, 200)
                generator = main.projection_connection()
                reader = next(generator)
                reader.execute("SELECT 1")
                entered = threading.Event()

                def promote():
                    with main.dbmod.PROJECTION_GATE.quiesce(timeout=5.0):
                        entered.set()

                worker = threading.Thread(target=promote)
                worker.start()
                self.assertFalse(
                    entered.wait(0.2),
                    "promotion quiesced while a request connection was open",
                )
                with contextlib.suppress(StopIteration):
                    next(generator)
                self.assertTrue(entered.wait(5.0))
                worker.join(5.0)
                self.assertEqual(main.dbmod.PROJECTION_GATE.active_readers, 0)

    def test_after_a_gated_swap_the_next_request_reports_the_promoted_manifest(self):
        from fastapi.testclient import TestClient

        with manager_app(self.root) as main:
            with TestClient(main.app) as client:
                before = client.get("/api/status").json()
                original = before["projection"]["manifest"]["migration_id"]
                self.assertTrue(original)

                promoted_id = uuid.uuid4().hex
                candidate = self.root / "candidate.sqlite3"
                conn = main.dbmod.connect(candidate)
                try:
                    main.dbmod.init_projection_schema(conn)
                    main.dbmod._write_manifest(
                        conn,
                        store_kind="projection",
                        migration_id=promoted_id,
                        source_sha256="promoted-sha",
                        source_path=candidate,
                        archive_path=None,
                        table_counts={},
                    )
                    conn.commit()
                    conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
                finally:
                    conn.close()

                with main.dbmod.PROJECTION_GATE.quiesce(timeout=5.0):
                    os.replace(candidate, main.config.DEFAULT_PROJECTION_DB)

                after = client.get("/api/status").json()
                self.assertEqual(
                    after["projection"]["manifest"]["migration_id"], promoted_id
                )
                self.assertEqual(
                    after["projection"]["manifest"]["source_sha256"], "promoted-sha"
                )
                self.assertNotEqual(original, promoted_id)


class TestSingleProcessDeployment(unittest.TestCase):
    """C9: multi-worker serving is refused and documented as unsupported."""

    def test_run_script_refuses_multi_worker_invocation(self):
        script = ROOT / "workbook-manager" / "run.sh"
        source = script.read_text()
        self.assertIn("--workers", source)
        import subprocess

        result = subprocess.run(
            [str(script), "--workers", "4"],
            capture_output=True,
            text=True,
            timeout=60,
        )
        self.assertNotEqual(result.returncode, 0)
        combined = (result.stdout + result.stderr).lower()
        self.assertIn("single", combined)

    def test_run_script_refuses_the_environment_worker_count(self):
        """uvicorn reads WEB_CONCURRENCY when the flag is absent, so refusing
        only argv would leave multi-worker serving reachable."""
        import subprocess

        script = ROOT / "workbook-manager" / "run.sh"
        result = subprocess.run(
            [str(script)],
            capture_output=True,
            text=True,
            timeout=60,
            env={**os.environ, "WEB_CONCURRENCY": "4"},
        )
        self.assertNotEqual(result.returncode, 0)
        combined = (result.stdout + result.stderr).lower()
        self.assertIn("single-process", combined)
        self.assertIn("web_concurrency", combined)

    def test_docs_record_single_process_only_serving(self):
        manager_readme = (ROOT / "workbook-manager" / "README.md").read_text()
        self.assertIn("single-process", manager_readme.lower())
        self.assertIn("multi-worker", manager_readme.lower())


if __name__ == "__main__":
    unittest.main(verbosity=2)
