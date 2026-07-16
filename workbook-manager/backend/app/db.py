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

import sqlite3
from pathlib import Path

from .specs import TABLE_SPECS, TableSpec


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
        cols.append(f'"{c.sql_name()}" TEXT NOT NULL DEFAULT \'\'')
    cols.append("src_sheet TEXT NOT NULL DEFAULT ''")
    cols.append("src_row INTEGER")
    key_cols = list(spec.key)
    if spec.model_scoped:
        key_cols = ["model_id", *key_cols]
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
