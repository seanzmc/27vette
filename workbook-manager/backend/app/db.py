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
  documents relationships; enforcement is code-level (PRAGMA foreign_keys
  stays OFF) because import must ingest unresolved rows and *report* them.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import sqlite3
import threading
import uuid
from pathlib import Path

from .catalog import TABLE_SPECS, TableSpec


SCHEMA_VERSION = 1
_BOOTSTRAP_LOCK = threading.RLock()
_ARCHIVE_TEMP_PREFIX = ".wbm-split-archive-"
_CANDIDATE_PREFIX = ".wbm-split-candidate-"
_PROJECTION_META_KEYS = (
    "workbook_mtime_ns",
    "workbook_sha256",
    "last_import_run_id",
)


def connect(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


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
      pending_change_id INTEGER
    )""",
    """CREATE TABLE IF NOT EXISTS meta (
      key TEXT PRIMARY KEY,
      value TEXT NOT NULL
    )""",
]

PROJECTION_SUPPORT_DDL = SUPPORT_DDL[:3] + [SUPPORT_DDL[-1]]

DURABLE_SUPPORT_DDL = SUPPORT_DDL[3:5] + [
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
    conn = sqlite3.connect(path)
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


def _read_manifest_path(path: Path) -> dict | None:
    if not path.exists():
        return None
    conn = connect(path)
    try:
        return storage_manifest(conn)
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

    with _BOOTSTRAP_LOCK:
        state_manifest = _read_manifest_path(state_path)
        if state_manifest and state_manifest.get("store_kind") == "durable":
            projection_manifest = _read_manifest_path(projection_path)
            matching = (
                projection_manifest
                and projection_manifest.get("store_kind") == "projection"
                and projection_manifest.get("migration_id") == state_manifest.get("migration_id")
                and projection_manifest.get("source_sha256") == state_manifest.get("source_sha256")
                and int(projection_manifest.get("schema_version")) == SCHEMA_VERSION
            )
            if matching:
                return {
                    "status": "ready",
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
            _replace_candidate(candidate, projection_path)
            return {
                "status": "projection_rebuilt",
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
            _replace_candidate(projection_candidate, projection_path)
            _replace_candidate(durable_candidate, state_path)
            return {
                "status": "initialized",
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
            _replace_candidate(projection_candidate, projection_path)
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
            "migration_id": migration_id,
            "archive_path": str(archive),
        }
