"""SQLite schema and connection handling.

Storage conventions:
- Every canonical value is stored as TEXT exactly as it appears in the
  workbook (``''`` for blank). Types/enums from the table specs are enforced
  by the validation layer, and coercion back to workbook storage happens in
  the existing editor_ops pipeline at sync time. This keeps import lossless.
- Model-scoped tables carry a ``model_id`` column (the model_key) plus a
  composite UNIQUE constraint over ``(model_id, *key)``.
- ``src_sheet``/``src_row`` are traceability metadata only, never identity.
- Real FOREIGN KEY clauses are declared for single-table refs so the schema
  documents relationships; enforcement of *workbook* references is code-level
  (projection connections keep PRAGMA foreign_keys OFF) because import must
  ingest unresolved rows and *report* them. SQLite enforcement is enabled only
  for durable manager-state relationships the database itself owns, such as
  ``change_history.pending_change_id`` -> ``pending_changes.id``. SQLite is
  never a second workbook reference model.

Process coordination (Pass 3):
- ``STATE_LOCK`` is the one process-local lock. It covers first-start
  bootstrap/migration, durable-state mutations, candidate promotion, and
  workbook apply. Supported serving is single-process; multi-worker serving is
  unsupported and no distributed lock is added.
- ``PROJECTION_GATE`` blocks new projection readers and waits for open
  request-scoped projection connections to close before the projection file is
  replaced. Every wait is bounded and fails closed with ``ProjectionBusyError``
  rather than hanging.
- Lock ordering is ``STATE_LOCK`` first, then a projection reader. Promotion
  therefore takes ``STATE_LOCK`` and only then quiesces readers, so a request
  never holds a reader while waiting for the lock a promoter owns.
"""

from __future__ import annotations

import contextlib
import hashlib
import json
import os
import shutil
import sqlite3
import threading
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from .catalog import TABLE_SPECS, TableSpec


# 2 (Pass 3): durable ``change_history.pending_change_id`` declares
# ``REFERENCES pending_changes(id)``. 3 (Pass 4): the disposable projection
# records sheet and managed-row dispositions. 4 (Pass 5): durable workflow
# drafts and their coalesced physical-row operations. 5 (Pass 5): immutable
# emitted ChangeSet payloads. 6 (Pass 5): immutable preview-attempt evidence.
# Versions 4–6 did not change projection shape, so a verified version-3
# projection remains compatible while its durable store upgrades independently.
SCHEMA_VERSION = 6
PROJECTION_SCHEMA_VERSION = 3
# One process-local lock for bootstrap, durable-state mutation, candidate
# promotion, and workbook apply.
#
# Deliberately a plain ``Lock``, not an ``RLock``: FastAPI runs a synchronous
# generator dependency's enter and exit on separate threadpool threads, and an
# ``RLock`` can only be released by the thread that acquired it — holding one
# across the dependency's ``yield`` leaks the lock and wedges every later
# request. A plain ``Lock`` may be released from another thread. It is therefore
# NOT reentrant: no code path may acquire it while already holding it.
#
# Request paths must never *block* on this lock from a threadpool worker either:
# a parked worker consumes an anyio thread token, and once every token is parked
# the lock holder cannot get a thread to finish and release. ``main.py`` acquires
# it from an async dependency with non-blocking polling and a bounded deadline.
STATE_LOCK = threading.Lock()
_BOOTSTRAP_LOCK = STATE_LOCK
BUSY_TIMEOUT_MS = int(os.environ.get("WBM_BUSY_TIMEOUT_MS", "5000"))
READER_DRAIN_SECONDS = float(os.environ.get("WBM_READER_DRAIN_SECONDS", "10"))
_ARCHIVE_TEMP_PREFIX = ".wbm-split-archive-"
_CANDIDATE_PREFIX = ".wbm-split-candidate-"
_PROJECTION_META_KEYS = (
    "workbook_mtime_ns",
    "workbook_sha256",
    "last_import_run_id",
)


def connect(db_path: Path, *, foreign_keys: bool = False) -> sqlite3.Connection:
    """Open one connection with WAL and a bounded busy timeout.

    ``foreign_keys`` is enabled only for durable manager-state connections; the
    projection keeps enforcement off so unresolved workbook references import
    and are reported as findings.
    """
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(
        db_path, check_same_thread=False, timeout=BUSY_TIMEOUT_MS / 1000
    )
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    # The busy timeout comes from the driver ``timeout=`` above, which sets the
    # same handler; a second explicit PRAGMA here would be unobservable dead
    # code (deleting it changes nothing), so the configured value is asserted
    # instead of restated.
    conn.execute(f"PRAGMA foreign_keys={'ON' if foreign_keys else 'OFF'}")
    return conn


class ProjectionBusyError(RuntimeError):
    """Raised when a bounded projection gate wait expires."""


class ProjectionGate:
    """Reader gate that lets promotion replace the projection file safely.

    Readers are request-scoped projection connections. Promotion blocks new
    readers, waits for open readers to close, and only then replaces the file.
    The gate holds no state about *which* projection is current: the promoted
    projection's own import manifest and source fingerprint identify it.
    """

    def __init__(self) -> None:
        self._cond = threading.Condition()
        self._readers = 0
        self._blocked = False

    @property
    def active_readers(self) -> int:
        with self._cond:
            return self._readers

    @property
    def blocked(self) -> bool:
        with self._cond:
            return self._blocked

    @contextlib.contextmanager
    def reader(self, timeout: float = READER_DRAIN_SECONDS):
        deadline = time.monotonic() + timeout
        with self._cond:
            while self._blocked:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise ProjectionBusyError(
                        "projection readers are gated while a candidate "
                        "projection is promoted"
                    )
                self._cond.wait(remaining)
            self._readers += 1
        try:
            yield
        finally:
            with self._cond:
                self._readers -= 1
                self._cond.notify_all()

    @contextlib.contextmanager
    def quiesce(self, timeout: float = READER_DRAIN_SECONDS):
        """Block new readers, drain open readers, then yield for replacement."""
        deadline = time.monotonic() + timeout
        with self._cond:
            while self._blocked:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise ProjectionBusyError(
                        "another projection promotion holds the gate"
                    )
                self._cond.wait(remaining)
            self._blocked = True
            while self._readers:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    stuck = self._readers
                    self._blocked = False
                    self._cond.notify_all()
                    raise ProjectionBusyError(
                        f"{stuck} projection reader(s) did not drain within "
                        f"{timeout}s; projection was not replaced"
                    )
                self._cond.wait(remaining)
        try:
            yield
        finally:
            with self._cond:
                self._blocked = False
                self._cond.notify_all()


PROJECTION_GATE = ProjectionGate()


def _table_ddl(spec: TableSpec) -> str:
    cols = ["id INTEGER PRIMARY KEY AUTOINCREMENT"]
    if spec.model_scoped:
        cols.append("model_id TEXT NOT NULL")
    for c in spec.columns:
        cols.append(f'"{c.sql_name()}" TEXT')
    cols.append("src_sheet TEXT NOT NULL DEFAULT ''")
    cols.append("src_row INTEGER")
    cols.append("src_family TEXT NOT NULL DEFAULT ''")
    cols.append("physical_key TEXT NOT NULL DEFAULT ''")
    cols.append("model_context TEXT NOT NULL DEFAULT '[]'")
    key_cols = list(spec.key)
    if spec.model_scoped:
        key_cols = ["model_id", *key_cols]
    elif spec.role:
        # Shared physical source-role families keep the sheet in physical
        # identity; the same semantic key may validly exist on two source
        # sheets registered by different models.
        key_cols = ["src_sheet", *key_cols]
    quoted = ", ".join(f'"{k}"' for k in key_cols)
    cols.append(f"UNIQUE({quoted})")
    for ref in spec.refs:
        if ref.scope == "global":
            cols.append(
                f'FOREIGN KEY("{ref.column}") REFERENCES '
                f'{ref.target_table}("{ref.target_column}")'
            )
    body = ",\n  ".join(cols)
    return f"CREATE TABLE IF NOT EXISTS {spec.table} (\n  {body}\n)"


SUPPORT_DDL = [
    """CREATE TABLE IF NOT EXISTS raw_sheet_rows (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      sheet TEXT NOT NULL,
      src_row INTEGER NOT NULL,
      data_json TEXT NOT NULL,
      UNIQUE(sheet, src_row)
    )""",
    """CREATE TABLE IF NOT EXISTS import_runs (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      ts TEXT NOT NULL,
      workbook_path TEXT NOT NULL,
      workbook_mtime_ns TEXT NOT NULL,
      workbook_sha256 TEXT NOT NULL,
      status TEXT NOT NULL,
      row_counts_json TEXT NOT NULL DEFAULT '{}',
      issue_counts_json TEXT NOT NULL DEFAULT '{}'
    )""",
    """CREATE TABLE IF NOT EXISTS import_issues (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      run_id INTEGER NOT NULL REFERENCES import_runs(id),
      severity TEXT NOT NULL,          -- error | warning
      category TEXT NOT NULL,          -- duplicate_id | unresolved_ref | ...
      sheet TEXT NOT NULL DEFAULT '',
      src_row INTEGER,
      table_name TEXT NOT NULL DEFAULT '',
      model_id TEXT NOT NULL DEFAULT '',
      entity_key TEXT NOT NULL DEFAULT '',
      field TEXT NOT NULL DEFAULT '',
      message TEXT NOT NULL
    )""",
    """CREATE TABLE IF NOT EXISTS pending_changes (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      ts TEXT NOT NULL,
      session_id TEXT NOT NULL DEFAULT '',
      table_name TEXT NOT NULL,
      model_id TEXT NOT NULL DEFAULT '',
      entity_key_json TEXT NOT NULL,
      op TEXT NOT NULL,                -- add | update | delete
      old_json TEXT,
      new_json TEXT,
      status TEXT NOT NULL DEFAULT 'staged',  -- staged | committed | discarded
      validation_json TEXT NOT NULL DEFAULT '{}',
      confirmed_dependencies INTEGER NOT NULL DEFAULT 0
    )""",
    """CREATE TABLE IF NOT EXISTS change_history (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      ts TEXT NOT NULL,
      actor TEXT NOT NULL DEFAULT '',
      entity_type TEXT NOT NULL,
      entity_id TEXT NOT NULL,
      model_id TEXT NOT NULL DEFAULT '',
      op TEXT NOT NULL,
      old_json TEXT,
      new_json TEXT,
      src_sheet TEXT NOT NULL DEFAULT '',
      src_row INTEGER,
      validation_result TEXT NOT NULL DEFAULT '',
      status TEXT NOT NULL,            -- committed | rolled_back
      sync_status TEXT NOT NULL DEFAULT 'pending',  -- pending | synced | sync_failed | n/a
      sync_detail TEXT NOT NULL DEFAULT '',
      -- Database-owned relationship: enforced on durable connections only.
      pending_change_id INTEGER REFERENCES pending_changes(id)
    )""",
    """CREATE TABLE IF NOT EXISTS meta (
      key TEXT PRIMARY KEY,
      value TEXT NOT NULL
    )""",
]

PROJECTION_SUPPORT_DDL = SUPPORT_DDL[:3] + [
    """CREATE TABLE IF NOT EXISTS sheet_dispositions (
      sheet TEXT PRIMARY KEY,
      disposition TEXT NOT NULL,
      family TEXT NOT NULL DEFAULT '',
      model_context TEXT NOT NULL DEFAULT '[]',
      opaque_columns_json TEXT NOT NULL DEFAULT '[]'
    )""",
    """CREATE TABLE IF NOT EXISTS managed_row_dispositions (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      sheet TEXT NOT NULL,
      src_row INTEGER NOT NULL,
      family TEXT NOT NULL,
      physical_key TEXT NOT NULL DEFAULT '',
      model_context TEXT NOT NULL DEFAULT '[]',
      disposition TEXT NOT NULL,
      blocking INTEGER NOT NULL DEFAULT 0,
      field TEXT NOT NULL DEFAULT '',
      value TEXT NOT NULL DEFAULT '',
      reason_token TEXT NOT NULL DEFAULT '',
      contract_impact TEXT NOT NULL DEFAULT '',
      UNIQUE(sheet, src_row, family)
    )""",
    SUPPORT_DDL[-1],
]

DURABLE_SUPPORT_DDL = SUPPORT_DDL[3:5] + [
    """CREATE TABLE IF NOT EXISTS workflow_drafts (
      id TEXT PRIMARY KEY,
      created_ts TEXT NOT NULL,
      updated_ts TEXT NOT NULL,
      session_id TEXT NOT NULL DEFAULT '',
      actor TEXT NOT NULL DEFAULT '',
      status TEXT NOT NULL DEFAULT 'draft',
      base_workbook_sha256 TEXT NOT NULL,
      base_workbook_mtime_ns TEXT NOT NULL
    )""",
    """CREATE TABLE IF NOT EXISTS draft_operations (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      draft_id TEXT NOT NULL REFERENCES workflow_drafts(id),
      created_ts TEXT NOT NULL,
      updated_ts TEXT NOT NULL,
      table_name TEXT NOT NULL,
      family TEXT NOT NULL,
      model_id TEXT NOT NULL DEFAULT '',
      source_sheet TEXT NOT NULL,
      source_row INTEGER,
      physical_key TEXT NOT NULL,
      entity_key_json TEXT NOT NULL,
      action TEXT NOT NULL,
      original_json TEXT,
      final_json TEXT,
      changed_fields_json TEXT NOT NULL,
      model_context_json TEXT NOT NULL DEFAULT '[]',
      UNIQUE(draft_id, source_sheet, family, physical_key)
    )""",
    """CREATE TABLE IF NOT EXISTS draft_changesets (
      draft_id TEXT PRIMARY KEY REFERENCES workflow_drafts(id),
      created_ts TEXT NOT NULL,
      change_set_id TEXT NOT NULL UNIQUE,
      semantic_fingerprint TEXT NOT NULL UNIQUE,
      payload_json TEXT NOT NULL
    )""",
    """CREATE TRIGGER IF NOT EXISTS draft_changesets_immutable_update
    BEFORE UPDATE ON draft_changesets
    BEGIN
      SELECT RAISE(ABORT, 'draft ChangeSet artifacts are immutable');
    END""",
    """CREATE TRIGGER IF NOT EXISTS draft_changesets_immutable_delete
    BEFORE DELETE ON draft_changesets
    BEGIN
      SELECT RAISE(ABORT, 'draft ChangeSet artifacts are immutable');
    END""",
    """CREATE TABLE IF NOT EXISTS draft_preview_attempts (
      id TEXT PRIMARY KEY,
      draft_id TEXT NOT NULL REFERENCES workflow_drafts(id),
      change_set_id TEXT NOT NULL,
      semantic_fingerprint TEXT NOT NULL,
      started_ts TEXT NOT NULL,
      completed_ts TEXT NOT NULL,
      artifact_kind TEXT NOT NULL,
      result_json TEXT,
      exception_class TEXT NOT NULL DEFAULT '',
      exception_message TEXT NOT NULL DEFAULT '',
      workbook_identity_state TEXT NOT NULL,
      observed_workbook_sha256 TEXT NOT NULL DEFAULT '',
      observed_workbook_mtime_ns TEXT NOT NULL DEFAULT '',
      manager_state TEXT NOT NULL,
      allowed_verbs_json TEXT NOT NULL
    )""",
    """CREATE TRIGGER IF NOT EXISTS draft_preview_attempts_immutable_update
    BEFORE UPDATE ON draft_preview_attempts
    BEGIN
      SELECT RAISE(ABORT, 'draft preview attempt artifacts are immutable');
    END""",
    """CREATE TRIGGER IF NOT EXISTS draft_preview_attempts_immutable_delete
    BEFORE DELETE ON draft_preview_attempts
    BEGIN
      SELECT RAISE(ABORT, 'draft preview attempt artifacts are immutable');
    END""",
    """CREATE TABLE IF NOT EXISTS legacy_recovery_records (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      migration_id TEXT NOT NULL,
      source_table TEXT NOT NULL,
      source_primary_key TEXT NOT NULL,
      row_json TEXT NOT NULL,
      unresolved INTEGER NOT NULL DEFAULT 0,
      UNIQUE(migration_id, source_table, source_primary_key)
    )""",
    """CREATE TABLE IF NOT EXISTS durable_recovery_meta (
      migration_id TEXT NOT NULL,
      key TEXT NOT NULL,
      value TEXT NOT NULL,
      PRIMARY KEY(migration_id, key)
    )""",
    """CREATE TABLE IF NOT EXISTS meta (
      key TEXT PRIMARY KEY,
      value TEXT NOT NULL
    )""",
]

MANIFEST_DDL = """CREATE TABLE IF NOT EXISTS storage_manifest (
  store_kind TEXT PRIMARY KEY,
  migration_id TEXT NOT NULL,
  source_sha256 TEXT NOT NULL,
  schema_version INTEGER NOT NULL,
  source_path TEXT NOT NULL,
  archive_path TEXT NOT NULL,
  table_counts_json TEXT NOT NULL
)"""


def init_schema(conn: sqlite3.Connection) -> None:
    for spec in TABLE_SPECS:
        conn.execute(_table_ddl(spec))
    for ddl in SUPPORT_DDL:
        conn.execute(ddl)
    for ddl in PROJECTION_SUPPORT_DDL[3:-1]:
        conn.execute(ddl)
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_history_entity "
        "ON change_history(entity_type, entity_id)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_issues_run ON import_issues(run_id)"
    )
    conn.commit()


def clear_imported_data(conn: sqlite3.Connection) -> None:
    """Remove imported rows (not staged changes / history) before re-import."""
    for spec in TABLE_SPECS:
        conn.execute(f"DELETE FROM {spec.table}")
    conn.execute("DELETE FROM raw_sheet_rows")
    conn.commit()


def get_meta(conn: sqlite3.Connection, key: str, default: str = "") -> str:
    row = conn.execute("SELECT value FROM meta WHERE key=?", (key,)).fetchone()
    return row["value"] if row else default


def set_meta(conn: sqlite3.Connection, key: str, value: str) -> None:
    conn.execute(
        "INSERT INTO meta(key, value) VALUES(?, ?) "
        "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
        (key, value),
    )


def init_projection_schema(conn: sqlite3.Connection) -> None:
    """Initialize only disposable workbook-projection tables."""
    for spec in TABLE_SPECS:
        conn.execute(_table_ddl(spec))
    for ddl in PROJECTION_SUPPORT_DDL:
        conn.execute(ddl)
    conn.execute(MANIFEST_DDL)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_issues_run ON import_issues(run_id)")
    conn.commit()


def init_durable_schema(conn: sqlite3.Connection) -> None:
    """Initialize durable manager/recovery state without projection rows."""
    for ddl in DURABLE_SUPPORT_DDL:
        conn.execute(ddl)
    conn.execute(MANIFEST_DDL)
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_legacy_recovery_source "
        "ON legacy_recovery_records(source_table, source_primary_key)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_history_entity "
        "ON change_history(entity_type, entity_id)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_draft_operations_draft "
        "ON draft_operations(draft_id, id)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_draft_preview_attempts_draft "
        "ON draft_preview_attempts(draft_id, started_ts)"
    )
    conn.commit()


def storage_manifest(conn: sqlite3.Connection) -> dict | None:
    exists = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='storage_manifest'"
    ).fetchone()
    if not exists:
        return None
    row = conn.execute("SELECT * FROM storage_manifest LIMIT 1").fetchone()
    return dict(row) if row else None


def _fsync_file(path: Path) -> None:
    with path.open("rb") as handle:
        os.fsync(handle.fileno())


def _fsync_dir(path: Path) -> None:
    try:
        fd = os.open(path, os.O_RDONLY)
    except OSError:
        return
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _checkpoint_legacy(path: Path) -> None:
    if not path.exists():
        return
    conn = connect(path)
    try:
        conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    finally:
        conn.close()
    wal = Path(f"{path}-wal")
    if wal.exists() and wal.stat().st_size:
        raise RuntimeError(f"refusing split migration from live WAL sidecar: {wal}")


def _archive_legacy(source: Path, source_hash: str) -> Path:
    final = source.with_name(f"{source.name}.legacy-split-{source_hash}.sqlite3")
    if final.exists():
        if _sha256(final) != source_hash:
            raise RuntimeError(f"legacy archive hash mismatch: {final}")
        return final
    candidates = sorted(source.parent.glob(f"{_ARCHIVE_TEMP_PREFIX}*"))
    matching = [candidate for candidate in candidates if _sha256(candidate) == source_hash]
    if len(matching) > 1:
        raise RuntimeError("ambiguous verified legacy archive candidates")
    for candidate in candidates:
        if candidate not in matching:
            candidate.unlink()
    if matching:
        os.replace(matching[0], final)
        _fsync_dir(source.parent)
        return final
    temp = source.with_name(f"{_ARCHIVE_TEMP_PREFIX}{uuid.uuid4().hex}.tmp")
    shutil.copyfile(source, temp)
    _fsync_file(temp)
    if _sha256(temp) != source_hash:
        temp.unlink(missing_ok=True)
        raise RuntimeError("legacy archive copy failed hash verification")
    os.replace(temp, final)
    _fsync_dir(source.parent)
    return final


def _table_exists(conn: sqlite3.Connection, table: str) -> bool:
    return conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)
    ).fetchone() is not None


def _copy_table(
    source: sqlite3.Connection, target: sqlite3.Connection, table: str
) -> tuple[int, int, str, str]:
    if not _table_exists(source, table):
        empty = hashlib.sha256(b"[]").hexdigest()
        return 0, 0, empty, empty
    source_columns = [row["name"] for row in source.execute(f'PRAGMA table_info("{table}")')]
    target_columns = {row["name"] for row in target.execute(f'PRAGMA table_info("{table}")')}
    columns = [column for column in source_columns if column in target_columns]
    source_count = int(
        source.execute(f'SELECT COUNT(*) c FROM "{table}"').fetchone()["c"]
    )
    if not columns:
        empty = hashlib.sha256(b"[]").hexdigest()
        return source_count, 0, empty, empty
    quoted = ", ".join(f'"{column}"' for column in columns)
    placeholders = ", ".join("?" for _ in columns)
    rows = source.execute(f'SELECT {quoted} FROM "{table}"').fetchall()
    target.executemany(
        f'INSERT INTO "{table}" ({quoted}) VALUES ({placeholders})',
        [tuple(row[column] for column in columns) for row in rows],
    )
    source_values = [tuple(row[column] for column in columns) for row in rows]
    target_rows = target.execute(f'SELECT {quoted} FROM "{table}"').fetchall()
    target_values = [tuple(row[column] for column in columns) for row in target_rows]

    def fingerprint(values) -> str:
        encoded = json.dumps(
            sorted(values, key=lambda value: repr(value)),
            default=str,
            separators=(",", ":"),
        ).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()

    return source_count, len(rows), fingerprint(source_values), fingerprint(target_values)


def _write_manifest(
    conn: sqlite3.Connection,
    *,
    store_kind: str,
    migration_id: str,
    source_sha256: str,
    source_path: Path,
    archive_path: Path | None,
    table_counts: dict,
) -> None:
    conn.execute("DELETE FROM storage_manifest")
    conn.execute(
        "INSERT INTO storage_manifest(store_kind, migration_id, source_sha256, "
        "schema_version, source_path, archive_path, table_counts_json) "
        "VALUES(?,?,?,?,?,?,?)",
        (
            store_kind,
            migration_id,
            source_sha256,
            SCHEMA_VERSION,
            str(source_path),
            str(archive_path or ""),
            json.dumps(table_counts, sort_keys=True),
        ),
    )


def _candidate_path(target: Path, kind: str) -> Path:
    return target.with_name(f"{_CANDIDATE_PREFIX}{kind}-{uuid.uuid4().hex}.sqlite3")


def _build_projection_candidate(
    source_path: Path | None,
    target_path: Path,
    *,
    migration_id: str,
    source_sha256: str,
    archive_path: Path | None,
) -> Path:
    candidate = _candidate_path(target_path, "projection")
    conn = connect(candidate)
    try:
        init_projection_schema(conn)
        conn.execute("BEGIN IMMEDIATE")
        counts: dict[str, dict] = {}
        if source_path is not None:
            source = connect(source_path)
            try:
                tables = [
                    *(spec.table for spec in TABLE_SPECS),
                    "raw_sheet_rows",
                    "import_runs",
                    "import_issues",
                ]
                for table in tables:
                    source_count, destination_count, source_fingerprint, destination_fingerprint = _copy_table(source, conn, table)
                    counts[table] = {
                        "source": source_count,
                        "destination": destination_count,
                        "source_fingerprint": source_fingerprint,
                        "destination_fingerprint": destination_fingerprint,
                    }
                    if source_count != destination_count or source_fingerprint != destination_fingerprint:
                        raise RuntimeError(f"projection migration count mismatch for {table}")
                if _table_exists(source, "meta"):
                    for key in _PROJECTION_META_KEYS:
                        row = source.execute(
                            "SELECT value FROM meta WHERE key=?", (key,)
                        ).fetchone()
                        if row:
                            set_meta(conn, key, row["value"])
            finally:
                source.close()
        _write_manifest(
            conn,
            store_kind="projection",
            migration_id=migration_id,
            source_sha256=source_sha256,
            source_path=source_path or target_path,
            archive_path=archive_path,
            table_counts=counts,
        )
        conn.commit()
        conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    except Exception:
        conn.close()
        candidate.unlink(missing_ok=True)
        raise
    conn.close()
    _fsync_file(candidate)
    return candidate


def _build_durable_candidate(
    source_path: Path | None,
    target_path: Path,
    *,
    migration_id: str,
    source_sha256: str,
    archive_path: Path | None,
) -> Path:
    candidate = _candidate_path(target_path, "durable")
    conn = connect(candidate)
    try:
        init_durable_schema(conn)
        conn.execute("BEGIN IMMEDIATE")
        counts: dict[str, dict] = {}
        if source_path is not None:
            source = connect(source_path)
            try:
                for table in ("pending_changes", "change_history"):
                    if not _table_exists(source, table):
                        empty = hashlib.sha256(b"[]").hexdigest()
                        counts[table] = {
                            "source": 0,
                            "destination": 0,
                            "source_fingerprint": empty,
                            "destination_fingerprint": empty,
                        }
                        continue
                    rows = source.execute(f'SELECT * FROM "{table}" ORDER BY id').fetchall()
                    source_payloads: list[str] = []
                    for row in rows:
                        payload = {key: row[key] for key in row.keys()}
                        serialized_payload = json.dumps(
                            payload, sort_keys=True, separators=(",", ":")
                        )
                        source_payloads.append(serialized_payload)
                        status = str(payload.get("status") or "")
                        sync_status = str(payload.get("sync_status") or "")
                        unresolved = status in {"staged", "failed", "sync_failed"} or sync_status in {
                            "pending",
                            "sync_failed",
                        }
                        conn.execute(
                            "INSERT INTO legacy_recovery_records(migration_id, "
                            "source_table, source_primary_key, row_json, unresolved) "
                            "VALUES(?,?,?,?,?)",
                            (
                                migration_id,
                                table,
                                str(payload.get("id")),
                                serialized_payload,
                                1 if unresolved else 0,
                            ),
                        )
                    destination_payloads = [
                        result["row_json"]
                        for result in conn.execute(
                            "SELECT row_json FROM legacy_recovery_records "
                            "WHERE migration_id=? AND source_table=? "
                            "ORDER BY source_primary_key",
                            (migration_id, table),
                        )
                    ]
                    source_fingerprint = hashlib.sha256(
                        json.dumps(sorted(source_payloads), separators=(",", ":")).encode()
                    ).hexdigest()
                    destination_fingerprint = hashlib.sha256(
                        json.dumps(
                            sorted(destination_payloads), separators=(",", ":")
                        ).encode()
                    ).hexdigest()
                    counts[table] = {
                        "source": len(rows),
                        "destination": len(destination_payloads),
                        "source_fingerprint": source_fingerprint,
                        "destination_fingerprint": destination_fingerprint,
                    }
                    if (
                        len(rows) != len(destination_payloads)
                        or source_fingerprint != destination_fingerprint
                    ):
                        raise RuntimeError(
                            f"durable migration count/fingerprint mismatch for {table}"
                        )
                if _table_exists(source, "meta"):
                    for row in source.execute("SELECT key, value FROM meta ORDER BY key"):
                        if row["key"] in _PROJECTION_META_KEYS:
                            continue
                        conn.execute(
                            "INSERT INTO durable_recovery_meta(migration_id, key, value) "
                            "VALUES(?,?,?)",
                            (migration_id, row["key"], row["value"]),
                        )
            finally:
                source.close()
        _write_manifest(
            conn,
            store_kind="durable",
            migration_id=migration_id,
            source_sha256=source_sha256,
            source_path=source_path or target_path,
            archive_path=archive_path,
            table_counts=counts,
        )
        conn.commit()
        conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    except Exception:
        conn.close()
        candidate.unlink(missing_ok=True)
        raise
    conn.close()
    _fsync_file(candidate)
    return candidate


def _replace_candidate(candidate: Path, target: Path) -> None:
    os.replace(candidate, target)
    _fsync_file(target)
    _fsync_dir(target.parent)


def _replace_projection(
    candidate: Path,
    target: Path,
    verify: Callable[[Path], None] | None = None,
) -> None:
    """Replace the projection file only while the reader gate is quiesced.

    Bootstrap runs before the app serves requests, so there is nothing to drain
    today. Routing every projection replacement through the gate keeps that
    invariant true for the Pass 4 promotion path rather than leaving an ungated
    ``os.replace`` for it to copy.
    """
    with PROJECTION_GATE.quiesce():
        rollback = target.with_name(f".{target.name}.rollback-{uuid.uuid4().hex}")
        had_target = target.exists()
        target_sidecars = tuple(Path(f"{target}{suffix}") for suffix in ("-wal", "-shm"))
        rollback_sidecars = tuple(
            rollback.with_name(f"{rollback.name}{suffix}") for suffix in ("-wal", "-shm")
        )
        original_sidecars: set[int] = set()
        backed_up = False
        try:
            if had_target:
                shutil.copy2(target, rollback)
                _fsync_file(rollback)
                for index, (sidecar, sidecar_backup) in enumerate(
                    zip(target_sidecars, rollback_sidecars)
                ):
                    if sidecar.exists():
                        shutil.copy2(sidecar, sidecar_backup)
                        _fsync_file(sidecar_backup)
                        original_sidecars.add(index)
                _fsync_dir(target.parent)
                backed_up = True
                checkpoint = connect(target)
                try:
                    result = checkpoint.execute("PRAGMA wal_checkpoint(TRUNCATE)").fetchone()
                    if result[0] != 0 or result[1] != result[2]:
                        raise ProjectionBusyError(
                            "active projection WAL could not be fully checkpointed"
                        )
                finally:
                    checkpoint.close()
                # A complete, reader-drained checkpoint proves any remaining
                # sidecars stale. Remove them before binding the path to the
                # promoted main database, while retaining byte-for-byte copies
                # for rollback until reopen verification succeeds.
                for sidecar in target_sidecars:
                    sidecar.unlink(missing_ok=True)
                _fsync_dir(target.parent)
            _replace_candidate(candidate, target)
            if verify is not None:
                verify(target)
        except Exception as promotion_error:
            if backed_up or not had_target:
                try:
                    for sidecar in target_sidecars:
                        sidecar.unlink(missing_ok=True)
                    if backed_up:
                        _replace_candidate(rollback, target)
                        for index, (sidecar, sidecar_backup) in enumerate(
                            zip(target_sidecars, rollback_sidecars)
                        ):
                            if index in original_sidecars:
                                shutil.copy2(sidecar_backup, sidecar)
                                _fsync_file(sidecar)
                        _fsync_dir(target.parent)
                    else:
                        target.unlink(missing_ok=True)
                        _fsync_dir(target.parent)
                except Exception as restore_error:
                    raise RuntimeError(
                        "projection replacement failed and prior projection could not "
                        f"be restored: promotion={promotion_error!r}; "
                        f"restore={restore_error!r}"
                    ) from restore_error
            raise
        finally:
            rollback.unlink(missing_ok=True)
            for sidecar_backup in rollback_sidecars:
                sidecar_backup.unlink(missing_ok=True)


def _read_manifest_path(path: Path) -> dict | None:
    if not path.exists():
        return None
    conn = connect(path)
    try:
        return storage_manifest(conn)
    finally:
        conn.close()


def _durable_history_declares_pending_fk(conn: sqlite3.Connection) -> bool:
    return any(
        row["table"] == "pending_changes" and row["from"] == "pending_change_id"
        for row in conn.execute('PRAGMA foreign_key_list("change_history")')
    )


def _upgrade_durable_store(state_path: Path, manifest: dict) -> bool:
    """Bring a durable store built by an earlier schema version up to date.

    Schema 2 adds the database-owned ``change_history.pending_change_id`` ->
    ``pending_changes.id`` foreign key. Schema 3 changes only the disposable
    projection. Schema 4 adds durable draft tables; schema 5 adds immutable
    emitted ChangeSet artifacts; schema 6 adds immutable preview-attempt
    evidence. Rebuild the history table only when its foreign key is absent,
    preserve every row, and create all missing durable objects idempotently.
    Returns True when an upgrade applied.
    """
    stored_version = int(manifest.get("schema_version") or 0)
    if stored_version >= SCHEMA_VERSION:
        return False
    if stored_version < 1:
        raise RuntimeError(
            f"durable store schema version {stored_version} is not upgradable"
        )
    conn = connect(state_path)
    try:
        if _durable_history_declares_pending_fk(conn):
            for ddl in DURABLE_SUPPORT_DDL:
                conn.execute(ddl)
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_draft_operations_draft "
                "ON draft_operations(draft_id, id)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_draft_preview_attempts_draft "
                "ON draft_preview_attempts(draft_id, started_ts)"
            )
            conn.execute(
                "UPDATE storage_manifest SET schema_version=?", (SCHEMA_VERSION,)
            )
            conn.commit()
            return True
        columns = [
            row["name"] for row in conn.execute('PRAGMA table_info("change_history")')
        ]
        quoted = ", ".join(f'"{column}"' for column in columns)
        conn.execute("BEGIN IMMEDIATE")
        before = int(
            conn.execute("SELECT COUNT(*) c FROM change_history").fetchone()["c"]
        )
        conn.execute("ALTER TABLE change_history RENAME TO change_history_schema1")
        for ddl in DURABLE_SUPPORT_DDL:
            if "CREATE TABLE IF NOT EXISTS change_history " in ddl:
                conn.execute(ddl)
                break
        conn.execute(
            f"INSERT INTO change_history ({quoted}) "
            f"SELECT {quoted} FROM change_history_schema1"
        )
        after = int(
            conn.execute("SELECT COUNT(*) c FROM change_history").fetchone()["c"]
        )
        if after != before:
            conn.rollback()
            raise RuntimeError(
                f"durable schema upgrade lost rows: {before} -> {after}"
            )
        conn.execute("DROP TABLE change_history_schema1")
        for ddl in DURABLE_SUPPORT_DDL:
            conn.execute(ddl)
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_history_entity "
            "ON change_history(entity_type, entity_id)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_draft_operations_draft "
            "ON draft_operations(draft_id, id)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_draft_preview_attempts_draft "
            "ON draft_preview_attempts(draft_id, started_ts)"
        )
        conn.execute(
            "UPDATE storage_manifest SET schema_version=?", (SCHEMA_VERSION,)
        )
        conn.commit()
        conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        return True
    finally:
        conn.close()


def durable_orphan_history_rows(state_path: Path) -> int:
    """Count durable history rows whose ``pending_change_id`` has no parent.

    The upgrade copies rows with enforcement off so pre-existing legacy evidence
    is preserved rather than dropped or refused. SQLite only checks a foreign key
    on write, so such a row stays invisible unless it is counted explicitly.
    """
    if not state_path.exists():
        return 0
    conn = connect(state_path)
    try:
        if not _table_exists(conn, "change_history"):
            return 0
        return sum(
            1
            for row in conn.execute("PRAGMA foreign_key_check")
            if row[0] == "change_history"
        )
    finally:
        conn.close()


def bootstrap_storage(state_path: Path, projection_path: Path) -> dict:
    """Initialize or split the legacy combined database before consumers run."""
    state_path = Path(state_path)
    projection_path = Path(projection_path)
    if state_path == projection_path:
        raise ValueError("durable and projection database paths must differ")
    state_path.parent.mkdir(parents=True, exist_ok=True)
    projection_path.parent.mkdir(parents=True, exist_ok=True)

    with STATE_LOCK:
        state_manifest = _read_manifest_path(state_path)
        if state_manifest and state_manifest.get("store_kind") == "durable":
            upgraded = _upgrade_durable_store(state_path, state_manifest)
            if upgraded:
                state_manifest = _read_manifest_path(state_path) or state_manifest
            projection_manifest = _read_manifest_path(projection_path)
            verified_import = (
                projection_manifest
                and str(projection_manifest.get("migration_id") or "").startswith("import-")
                and bool(projection_manifest.get("source_sha256"))
            )
            matching = (
                projection_manifest
                and projection_manifest.get("store_kind") == "projection"
                and PROJECTION_SCHEMA_VERSION
                <= int(projection_manifest.get("schema_version") or 0)
                <= SCHEMA_VERSION
                and (
                    verified_import
                    or (
                        projection_manifest.get("migration_id")
                        == state_manifest.get("migration_id")
                        and projection_manifest.get("source_sha256")
                        == state_manifest.get("source_sha256")
                    )
                )
            )
            if matching:
                return {
                    "status": "ready",
                    "schema_upgraded": upgraded,
                    "orphan_history_rows": (
                        durable_orphan_history_rows(state_path) if upgraded else 0
                    ),
                    "migration_id": state_manifest["migration_id"],
                    "archive_path": state_manifest.get("archive_path", ""),
                }
            archive = Path(state_manifest.get("archive_path") or "")
            source = archive if archive.is_file() else None
            candidate = _build_projection_candidate(
                source,
                projection_path,
                migration_id=state_manifest["migration_id"],
                source_sha256=state_manifest["source_sha256"],
                archive_path=source,
            )
            _replace_projection(candidate, projection_path)
            return {
                "status": "projection_rebuilt",
                "schema_upgraded": upgraded,
                "orphan_history_rows": (
                    durable_orphan_history_rows(state_path) if upgraded else 0
                ),
                "migration_id": state_manifest["migration_id"],
                "archive_path": str(source or ""),
            }

        if not state_path.exists():
            migration_id = uuid.uuid4().hex
            projection_candidate = _build_projection_candidate(
                None,
                projection_path,
                migration_id=migration_id,
                source_sha256="",
                archive_path=None,
            )
            durable_candidate = _build_durable_candidate(
                None,
                state_path,
                migration_id=migration_id,
                source_sha256="",
                archive_path=None,
            )
            _replace_projection(projection_candidate, projection_path)
            _replace_candidate(durable_candidate, state_path)
            return {
                "status": "initialized",
                "schema_upgraded": False,
                "orphan_history_rows": 0,
                "migration_id": migration_id,
                "archive_path": "",
            }

        _checkpoint_legacy(state_path)
        source_hash = _sha256(state_path)
        archive = _archive_legacy(state_path, source_hash)
        migration_id = source_hash
        projection_candidate: Path | None = None
        durable_candidate: Path | None = None
        try:
            projection_candidate = _build_projection_candidate(
                archive,
                projection_path,
                migration_id=migration_id,
                source_sha256=source_hash,
                archive_path=archive,
            )
            durable_candidate = _build_durable_candidate(
                archive,
                state_path,
                migration_id=migration_id,
                source_sha256=source_hash,
                archive_path=archive,
            )
            _replace_projection(projection_candidate, projection_path)
            projection_candidate = None
            _replace_candidate(durable_candidate, state_path)
            durable_candidate = None
        finally:
            if projection_candidate:
                projection_candidate.unlink(missing_ok=True)
            if durable_candidate:
                durable_candidate.unlink(missing_ok=True)
        return {
            "status": "migrated",
            "schema_upgraded": False,
            "orphan_history_rows": 0,
            "migration_id": migration_id,
            "archive_path": str(archive),
        }
