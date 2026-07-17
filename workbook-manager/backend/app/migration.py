"""Candidate database loading, reconciliation, and atomic promotion.

This module never imports into the live destination.  A canonical database is
built beside it, structurally verified, closed and synced, then promoted with
one atomic replace.
"""

from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Mapping

from . import db
from .catalog import LIVE_MODELS, MODEL_TABLE_ROLES, physical_table
from .compile_types import Finding

if TYPE_CHECKING:
    from .contract_audit import ContractAudit
    from .importer import CompiledWorkbook


@dataclass(frozen=True)
class DestinationSnapshot:
    exists: bool
    content_sha256: str = ""
    stat_signature: tuple[int, int, int, int] = ()
    sidecars: tuple[tuple[str, str, int, int], ...] = ()
    staged_changes: int = 0
    unsynced_history: int = 0
    logical_fingerprint: str = ""
    user_version: int = 0
    findings: tuple[Finding, ...] = ()


class DestinationChanged(RuntimeError):
    pass


class CandidateCheckpointError(RuntimeError):
    pass


class BackupVerificationError(RuntimeError):
    pass


class CandidateChangedAfterAudit(RuntimeError):
    pass


class EditStateCarryForwardError(RuntimeError):
    pass


_EDIT_STATE_COLUMNS = {
    "pending_changes": (
        "id", "ts", "session_id", "model_key", "table_role", "sql_table",
        "entity_key_json", "op", "old_json", "new_json", "status",
        "validation_json", "confirmed_dependencies",
    ),
    "change_history": (
        "id", "ts", "actor", "model_key", "table_role", "sql_table",
        "entity_id", "op", "old_json", "new_json", "src_sheet", "src_row",
        "validation_result", "status", "sync_status", "sync_detail",
        "pending_change_id", "related_history_id",
    ),
}


_MODEL_LOAD_ORDER = (
    "options",
    "interiors",
    "option_availability",
    "interior_scope",
    "interior_components",
    "color_overrides",
    "option_assets",
    "context_choice_assets",
    "rule_mapping",
    "price_rules",
    "rule_groups",
    "rule_group_members",
    "exclusive_groups",
    "exclusive_group_members",
    "variant_overrides",
    "default_selection_rules",
    "runtime_rule_exceptions",
)


def _quote(identifier: str) -> str:
    return '"' + identifier.replace('"', '""') + '"'


def _jsonable(value: object) -> object:
    if isinstance(value, Mapping):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (tuple, list, set, frozenset)):
        return [_jsonable(item) for item in value]
    return value


def _json(value: object) -> str:
    return json.dumps(
        _jsonable(value), sort_keys=True, separators=(",", ":"), default=str
    )


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _table_names(conn: sqlite3.Connection) -> set[str]:
    return {
        row["name"]
        for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
    }


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _integrity_errors(conn: sqlite3.Connection) -> list[dict]:
    rows = [row[0] for row in conn.execute("PRAGMA integrity_check")]
    return [] if rows == ["ok"] else [
        {"code": "sqlite_integrity_check_failed", "results": rows}
    ]


def _logical_fingerprint(conn: sqlite3.Connection) -> str:
    digest = hashlib.sha256()
    user_version = conn.execute("PRAGMA user_version").fetchone()[0]
    digest.update(f"user_version:{user_version}\n".encode())
    schema = tuple(
        conn.execute(
            "SELECT type, name, tbl_name, COALESCE(sql, '') AS sql "
            "FROM sqlite_master WHERE name NOT LIKE 'sqlite_%' "
            "ORDER BY type, name"
        )
    )
    for row in schema:
        digest.update(repr(tuple(row)).encode("utf-8"))
        digest.update(b"\n")
    for table in sorted(_table_names(conn) - {"sqlite_sequence"}):
        columns = [
            row["name"]
            for row in conn.execute(f"PRAGMA table_info({_quote(table)})")
        ]
        if not columns:
            continue
        order = ",".join(_quote(column) for column in columns)
        for row in conn.execute(
            f"SELECT * FROM {_quote(table)} ORDER BY {order}"
        ):
            digest.update(repr(tuple(row)).encode("utf-8"))
            digest.update(b"\n")
    return digest.hexdigest()


def capture_destination_snapshot(destination: Path) -> DestinationSnapshot:
    path = Path(destination)
    if not path.exists():
        return DestinationSnapshot(exists=False)
    try:
        stat = path.stat()
        content_sha256 = _file_sha256(path)
        sidecars = tuple(
            (
                artifact.name,
                _file_sha256(artifact),
                artifact.stat().st_size,
                artifact.stat().st_mtime_ns,
            )
            for artifact in (
                Path(str(path) + "-wal"),
                Path(str(path) + "-shm"),
            )
            if artifact.exists()
        )
    except OSError as error:
        return DestinationSnapshot(
            exists=True,
            findings=(
                Finding(
                    severity="error",
                    status="decision_required",
                    code="legacy_destination_audit_failed",
                    message=str(error),
                ),
            ),
        )
    findings: list[Finding] = []
    if sidecars:
        findings.append(
            Finding(
                severity="error",
                status="decision_required",
                code="legacy_destination_sidecars",
                message=(
                    "The destination has SQLite WAL/SHM sidecars. Close its "
                    "owner and checkpoint it before atomic replacement."
                ),
                value={"sidecars": tuple(item[0] for item in sidecars)},
            )
        )
    staged = 0
    unsynced = 0
    logical = ""
    user_version = 0
    try:
        conn = db.connect_readonly(path)
        try:
            tables = _table_names(conn)
            if "pending_changes" in tables:
                staged = conn.execute(
                    "SELECT COUNT(*) FROM pending_changes WHERE status='staged'"
                ).fetchone()[0]
            history_columns = {
                row["name"]
                for row in conn.execute("PRAGMA table_info(change_history)")
            } if "change_history" in tables else set()
            if "sync_status" in history_columns:
                if "related_history_id" in history_columns:
                    unsynced = conn.execute(
                        "SELECT COUNT(*) FROM change_history h "
                        "WHERE h.status='committed' "
                        "AND h.sync_status='pending' "
                        "AND NOT EXISTS (SELECT 1 FROM change_history event "
                        "WHERE event.related_history_id=h.id "
                        "AND event.status='sync_succeeded')"
                    ).fetchone()[0]
                else:
                    unsynced = conn.execute(
                        "SELECT COUNT(*) FROM change_history "
                        "WHERE sync_status NOT IN ('synced', 'n/a')"
                    ).fetchone()[0]
            user_version = conn.execute("PRAGMA user_version").fetchone()[0]
            logical = _logical_fingerprint(conn)
        finally:
            conn.close()
    except (OSError, sqlite3.DatabaseError) as error:
        findings.append(
            Finding(
                severity="error",
                status="decision_required",
                code="legacy_destination_audit_failed",
                message=str(error),
            )
        )
    if staged:
        findings.append(
            Finding(
                severity="error",
                status="decision_required",
                code="legacy_pending_changes",
                message="Resolve staged legacy changes before replacement.",
                value={"count": staged},
            )
        )
    if unsynced:
        findings.append(
            Finding(
                severity="error",
                status="decision_required",
                code="legacy_unsynced_change_history",
                message="Resolve unsynced legacy history before replacement.",
                value={"count": unsynced},
            )
        )
    return DestinationSnapshot(
        exists=True,
        content_sha256=content_sha256,
        stat_signature=(stat.st_dev, stat.st_ino, stat.st_size, stat.st_mtime_ns),
        sidecars=sidecars,
        staged_changes=staged,
        unsynced_history=unsynced,
        logical_fingerprint=logical,
        user_version=user_version,
        findings=tuple(findings),
    )


def audit_legacy_destination(destination: Path) -> tuple[Finding, ...]:
    """Read legacy edit state without creating or mutating destination files."""
    return capture_destination_snapshot(destination).findings


def _edit_state_rows(
    conn: sqlite3.Connection,
) -> dict[str, tuple[tuple[object, ...], ...]]:
    tables = _table_names(conn)
    present = set(_EDIT_STATE_COLUMNS) & tables
    if not present:
        return {table: () for table in _EDIT_STATE_COLUMNS}
    counts = {
        table: conn.execute(
            f"SELECT COUNT(*) FROM {_quote(table)}"
        ).fetchone()[0]
        for table in present
    }
    if not any(counts.values()):
        return {table: () for table in _EDIT_STATE_COLUMNS}
    if present != set(_EDIT_STATE_COLUMNS):
        raise EditStateCarryForwardError(
            "canonical_edit_state_incompatible: one edit-state table is missing"
        )
    for table, expected in _EDIT_STATE_COLUMNS.items():
        actual = tuple(
            row["name"] for row in conn.execute(
                f"PRAGMA table_info({_quote(table)})"
            )
        )
        if actual != expected:
            raise EditStateCarryForwardError(
                f"canonical_edit_state_incompatible: {table} columns differ"
            )
    if "model_table_registry" not in tables:
        raise EditStateCarryForwardError(
            "canonical_edit_state_incompatible: model table registry is missing"
        )
    for table in _EDIT_STATE_COLUMNS:
        unresolved = conn.execute(
            f"SELECT COUNT(*) FROM {_quote(table)} state "
            "WHERE NOT EXISTS (SELECT 1 FROM model_table_registry registry "
            "WHERE registry.model_key=state.model_key "
            "AND registry.table_role=state.table_role "
            "AND registry.sql_table=state.sql_table AND registry.active=1)"
        ).fetchone()[0]
        if unresolved:
            raise EditStateCarryForwardError(
                f"canonical_edit_state_incompatible: {table} has {unresolved} "
                "row(s) without an exact active model-table route"
            )
    _validate_edit_state_semantics(conn)
    return {
        table: tuple(
            tuple(row) for row in conn.execute(
                f"SELECT * FROM {_quote(table)} ORDER BY id"
            )
        )
        for table in _EDIT_STATE_COLUMNS
    }


def _validate_edit_state_semantics(conn: sqlite3.Connection) -> None:
    pending = {
        int(row["id"]): dict(row)
        for row in conn.execute("SELECT * FROM pending_changes ORDER BY id")
    }
    history = {
        int(row["id"]): dict(row)
        for row in conn.execute("SELECT * FROM change_history ORDER BY id")
    }

    def json_object(raw, *, nullable: bool = False, empty: bool = False):
        if raw is None and nullable:
            return None
        if raw == "" and empty:
            return {}
        try:
            value = json.loads(raw)
        except (TypeError, json.JSONDecodeError) as error:
            raise EditStateCarryForwardError(
                "canonical_edit_state_incompatible: malformed JSON payload"
            ) from error
        if not isinstance(value, dict):
            raise EditStateCarryForwardError(
                "canonical_edit_state_incompatible: edit-state JSON payload "
                "must be an object"
            )
        return value

    def validate_payload(row, *, pending_row: bool) -> None:
        if row["op"] not in {"add", "update", "delete"}:
            raise EditStateCarryForwardError(
                "canonical_edit_state_incompatible: unknown edit operation"
            )
        old = json_object(row["old_json"], nullable=True)
        new = json_object(row["new_json"], nullable=True)
        expected = {
            "add": (None, dict),
            "update": (dict, dict),
            "delete": (dict, None),
        }[row["op"]]
        if (
            (expected[0] is None and old is not None)
            or (expected[0] is dict and not isinstance(old, dict))
            or (expected[1] is None and new is not None)
            or (expected[1] is dict and not isinstance(new, dict))
        ):
            raise EditStateCarryForwardError(
                "canonical_edit_state_incompatible: operation payload shape differs"
            )
        if pending_row:
            key = json_object(row["entity_key_json"])
            json_object(row["validation_json"], empty=True)
            if not key or row["confirmed_dependencies"] not in (0, 1):
                raise EditStateCarryForwardError(
                    "canonical_edit_state_incompatible: invalid key or confirmation"
                )
        else:
            json_object(row["sync_detail"], empty=True)

    for change in pending.values():
        validate_payload(change, pending_row=True)
        if change["status"] not in {"committed", "discarded"}:
            raise EditStateCarryForwardError(
                "canonical_edit_state_incompatible: pending change status is "
                "not fully resolved"
            )
        if change["status"] == "committed":
            commits = [
                row for row in history.values()
                if row["status"] == "committed"
                and row["pending_change_id"] == change["id"]
            ]
            if len(commits) != 1:
                raise EditStateCarryForwardError(
                    "canonical_edit_state_incompatible: committed pending "
                    "change lacks one exact history row"
                )
            commit = commits[0]
            if any(
                commit[field] != change[field]
                for field in (
                    "model_key", "table_role", "sql_table", "op",
                    "old_json", "new_json",
                )
            ):
                raise EditStateCarryForwardError(
                    "canonical_edit_state_incompatible: pending/history route "
                    "or operation differs"
                )
    for event in history.values():
        validate_payload(event, pending_row=False)
        if event["status"] == "committed":
            if (
                event["sync_status"] != "pending"
                or event["related_history_id"] is not None
                or event["pending_change_id"] not in pending
                or pending[event["pending_change_id"]]["status"] != "committed"
            ):
                raise EditStateCarryForwardError(
                    "canonical_edit_state_incompatible: malformed committed "
                    "history state"
                )
            if not any(
                candidate["status"] == "sync_succeeded"
                and candidate["related_history_id"] == event["id"]
                for candidate in history.values()
            ):
                raise EditStateCarryForwardError(
                    "canonical_edit_state_incompatible: committed history "
                    "lacks a successful sync event"
                )
            continue
        expected_sync = {
            "sync_succeeded": "synced",
            "sync_failed": "sync_failed",
        }.get(event["status"])
        parent = history.get(event["related_history_id"])
        if (
            expected_sync is None
            or event["sync_status"] != expected_sync
            or event["pending_change_id"] is not None
            or parent is None
            or parent["status"] != "committed"
            or any(
                event[field] != parent[field]
                for field in (
                    "model_key", "table_role", "sql_table", "entity_id", "op",
                    "old_json", "new_json", "src_sheet", "src_row",
                )
            )
        ):
            raise EditStateCarryForwardError(
                "canonical_edit_state_incompatible: malformed sync history event"
            )


def _edit_state_digest(
    rows: Mapping[str, tuple[tuple[object, ...], ...]],
    sequences: tuple[tuple[str, int], ...] = (),
) -> str:
    digest = hashlib.sha256()
    for table in _EDIT_STATE_COLUMNS:
        digest.update(table.encode("utf-8"))
        digest.update(repr(rows[table]).encode("utf-8"))
    digest.update(repr(sequences).encode("utf-8"))
    return digest.hexdigest()


def _edit_state_sequences(
    conn: sqlite3.Connection,
) -> tuple[tuple[str, int], ...]:
    if "sqlite_sequence" not in _table_names(conn):
        return ()
    return tuple(
        (str(row["name"]), int(row["seq"]))
        for row in conn.execute(
            "SELECT name, seq FROM sqlite_sequence "
            "WHERE name IN ('pending_changes','change_history') ORDER BY name"
        )
    )


def carry_forward_canonical_edit_state(
    destination: Path,
    candidate: Path,
    snapshot: DestinationSnapshot,
) -> None:
    """Copy only exact canonical, fully synchronized edit audit state.

    The source is checked against the caller's immutable destination snapshot
    immediately before and after the copy.  Ambiguous legacy shapes are never
    translated into the canonical model-role history contract.
    """
    if not snapshot.exists:
        return
    destination_path = Path(destination)
    candidate_path = Path(candidate)
    _same_destination(destination_path, snapshot)
    source = db.connect_readonly(destination_path)
    try:
        source.execute("BEGIN")
        source_rows = _edit_state_rows(source)
        source_sequences = _edit_state_sequences(source)
        source_digest = _edit_state_digest(source_rows, source_sequences)
    finally:
        source.close()
    if not any(source_rows.values()) and not source_sequences:
        _same_destination(destination_path, snapshot)
        return

    target = db.connect(candidate_path)
    try:
        with target:
            if any(
                target.execute(
                    f"SELECT COUNT(*) FROM {_quote(table)}"
                ).fetchone()[0]
                for table in _EDIT_STATE_COLUMNS
            ):
                raise EditStateCarryForwardError(
                    "candidate edit-state tables were not empty"
                )
            target.execute("PRAGMA defer_foreign_keys=ON")
            for table, columns in _EDIT_STATE_COLUMNS.items():
                placeholders = ",".join("?" for _ in columns)
                target.executemany(
                    f"INSERT INTO {_quote(table)} "
                    f"({','.join(_quote(column) for column in columns)}) "
                    f"VALUES({placeholders})",
                    source_rows[table],
                )
            target.execute(
                "DELETE FROM sqlite_sequence "
                "WHERE name IN ('pending_changes','change_history')"
            )
            target.executemany(
                "INSERT INTO sqlite_sequence(name, seq) VALUES(?,?)",
                source_sequences,
            )
            violations = tuple(target.execute("PRAGMA foreign_key_check"))
            if violations:
                raise EditStateCarryForwardError(
                    "carried canonical edit state violates candidate foreign keys"
                )
        target_rows = _edit_state_rows(target)
        target_sequences = _edit_state_sequences(target)
        if _edit_state_digest(target_rows, target_sequences) != source_digest:
            raise EditStateCarryForwardError(
                "carried canonical edit state does not match its audited source"
            )
    finally:
        target.close()
    _same_destination(destination_path, snapshot)


def _ordered_tables(compiled: "CompiledWorkbook"):
    central = [table for table in compiled.tables if not table.model_key]
    physical = {
        (table.model_key, table.role): table
        for table in compiled.tables
        if table.model_key
    }
    yield from central
    for role in _MODEL_LOAD_ORDER:
        for model in LIVE_MODELS:
            yield physical[(model, role)]


def _insert_compiled_table(conn: sqlite3.Connection, table) -> None:
    if not table.rows:
        return
    columns = tuple(table.rows[0].values)
    if any(tuple(row.values) != columns for row in table.rows):
        raise ValueError(f"compiled column mismatch in {table.name}")
    sql = (
        f"INSERT INTO {_quote(table.name)} "
        f"({','.join(_quote(column) for column in columns)}) "
        f"VALUES({','.join('?' for _ in columns)})"
    )
    conn.executemany(
        sql,
        (tuple(row.values[column] for column in columns) for row in table.rows),
    )


def _registry_rows(compiled: "CompiledWorkbook"):
    by_key = {
        (table.model_key, table.role): table
        for table in compiled.tables
        if table.model_key
    }
    for model in LIVE_MODELS:
        for role in MODEL_TABLE_ROLES:
            table = by_key[(model, role)]
            source_sheets = tuple(sorted(
                {row.source_sheet for row in table.rows if row.source_sheet}
                or {
                    mapping.source_sheet
                    for mapping in table.schema_mappings
                    if mapping.source_sheet
                }
            ))
            split = any(
                row.lineage_role == "shared_source_split" for row in table.rows
            )
            yield (
                model,
                role,
                physical_table(model, role),
                _json(source_sheets),
                f"model_key={model}" if split else "",
                "split" if split else "exact",
                1,
            )


def _run_counts(compiled: "CompiledWorkbook") -> dict:
    mapping_tables: dict[str, int] = {}
    for mapping in compiled.schema_mappings:
        mapping_tables[mapping.destination_table] = (
            mapping_tables.get(mapping.destination_table, 0) + 1
        )
    return {
        "compiled_rows": len(compiled.lineage),
        "tables": {table.name: len(table.rows) for table in compiled.tables},
        "mapping_count": len(compiled.schema_mappings),
        "mapping_tables": mapping_tables,
        "required_destination_columns": {
            table.name: sorted(
                {
                    column
                    for row in table.rows
                    for column in row.values.keys()
                }
            )
            for table in compiled.tables
        },
        "source_inventory": {
            source.source_sheet: [row.source_row for row in source.rows]
            for source in compiled.source_catalog
        },
    }


def _compiled_lineage_hashes(compiled: "CompiledWorkbook") -> dict[tuple[str, str], str]:
    hashes = {}
    for table in compiled.tables:
        for row in table.rows:
            key = {column: row.values[column] for column in table.primary_key}
            evidence = {
                "values": row.values,
                "source_sheet": row.source_sheet,
                "source_row": row.source_row,
                "lineage_role": row.lineage_role,
                "mapping_parameters": row.mapping_parameters,
            }
            hashes[(table.name, _json(key))] = hashlib.sha256(
                _json(evidence).encode("utf-8")
            ).hexdigest()
    return hashes


def load_candidate(
    compiled: "CompiledWorkbook",
    path: Path,
    *,
    workbook_path: Path | None = None,
    workbook_mtime_ns: str = "",
    workbook_sha256: str = "",
) -> Path:
    """Create and transactionally load a fresh canonical candidate."""
    candidate = Path(path)
    if candidate.exists():
        raise FileExistsError(candidate)
    conn = db.connect(candidate)
    try:
        db.create_canonical_schema(conn)
        with conn:
            for table in _ordered_tables(compiled):
                _insert_compiled_table(conn, table)
            conn.executemany(
                "INSERT INTO model_table_registry("
                "model_key, table_role, sql_table, source_sheets_json, "
                "source_filter, mapping_type, active) VALUES(?,?,?,?,?,?,?)",
                tuple(_registry_rows(compiled)),
            )
            conn.executemany(
                "INSERT INTO source_table_catalog("
                "source_sheet, disposition, destination_tables_json, "
                "source_of_truth_class, row_count, reason) VALUES(?,?,?,?,?,?)",
                (
                    (
                        source.source_sheet,
                        source.disposition,
                        _json(source.destination_tables),
                        "workbook",
                        source.row_count,
                        source.reason,
                    )
                    for source in compiled.source_catalog
                ),
            )
            conn.executemany(
                "INSERT INTO schema_mapping("
                "source_sheet, source_column, model_key, source_role, "
                "sql_table, sql_column, transform_type, "
                "transform_parameters_json, contract_status, notes"
                ") VALUES(?,?,?,?,?,?,?,?,?,?)",
                (
                    (
                        mapping.source_sheet,
                        mapping.source_column,
                        mapping.model_key or None,
                        mapping.source_role,
                        mapping.destination_table,
                        mapping.destination_column,
                        mapping.transform,
                        _json(dict(mapping.transform_parameters)),
                        mapping.contract_status,
                        mapping.notes,
                    )
                    for mapping in compiled.schema_mappings
                ),
            )
            counts = _run_counts(compiled)
            lineage_hashes = _compiled_lineage_hashes(compiled)
            compiled_digest = hashlib.sha256(
                _json(counts).encode("utf-8")
            ).hexdigest()
            run_id = conn.execute(
                "INSERT INTO import_runs("
                "ts, workbook_path, workbook_mtime_ns, workbook_sha256, status, "
                "row_counts_json, issue_counts_json) VALUES(?,?,?,?,?,?,?)",
                (
                    _now(),
                    str(workbook_path) if workbook_path is not None else "",
                    workbook_mtime_ns,
                    workbook_sha256 or compiled_digest,
                    "validated",
                    _json(counts),
                    _json({"mapped": len(compiled.findings)}),
                ),
            ).lastrowid
            conn.executemany(
                "INSERT INTO import_lineage("
                "import_run_id, sql_table, primary_key_json, source_sheet, "
                "source_row, source_row_hash, lineage_role, transform_status"
                ") VALUES(?,?,?,?,?,?,?,?)",
                (
                    (
                        run_id,
                        entry.destination_table,
                        _json(dict(entry.destination_key)),
                        entry.source_sheet,
                        entry.source_row,
                        lineage_hashes[
                            (entry.destination_table, _json(entry.destination_key))
                        ],
                        entry.mapping_role,
                        "mapped",
                    )
                    for entry in compiled.lineage
                ),
            )
            conn.executemany(
                "INSERT INTO source_row_disposition("
                "import_run_id, source_sheet, source_row, disposition, "
                "destinations_json, reason, evidence_json"
                ") VALUES(?,?,?,?,?,?,?)",
                (
                    (
                        run_id,
                        source.source_sheet,
                        row.source_row,
                        row.disposition,
                        _json(row.evidence.get("destinations", ())),
                        row.reason,
                        _json(
                            {
                                "source_values": row.values,
                                **dict(row.evidence),
                            }
                        ),
                    )
                    for source in compiled.source_catalog
                    for row in source.rows
                ),
            )
            conn.executemany(
                "INSERT INTO import_issues("
                "run_id, severity, category, sheet, src_row, table_name, "
                "model_id, entity_key, field, message) VALUES(?,?,?,?,?,?,?,?,?,?)",
                (
                    (
                        run_id,
                        finding.severity,
                        finding.code,
                        finding.source_sheet,
                        finding.source_row,
                        "",
                        finding.model_key,
                        "",
                        finding.source_column,
                        finding.message,
                    )
                    for finding in compiled.findings
                ),
            )
            db.set_meta(conn, "last_import_run_id", str(run_id))
            db.set_meta(conn, "compiled_row_count", str(len(compiled.lineage)))
            if workbook_sha256:
                db.set_meta(conn, "trusted_workbook_sha256", workbook_sha256)
        return candidate
    finally:
        conn.close()


def _latest_counts(conn: sqlite3.Connection) -> dict:
    row = conn.execute(
        "SELECT row_counts_json FROM import_runs ORDER BY id DESC LIMIT 1"
    ).fetchone()
    return json.loads(row[0]) if row else {}


def reconcile_source_counts(conn: sqlite3.Connection) -> list[dict]:
    errors: list[dict] = []
    counts = _latest_counts(conn)
    expected_tables = counts.get("tables", {})
    for table, expected in expected_tables.items():
        actual = conn.execute(f"SELECT COUNT(*) FROM {_quote(table)}").fetchone()[0]
        if actual != expected:
            errors.append(
                {"code": "compiled_table_count_mismatch", "table": table,
                 "expected": expected, "actual": actual}
            )
    lineage_count = conn.execute("SELECT COUNT(*) FROM import_lineage").fetchone()[0]
    if lineage_count != counts.get("compiled_rows"):
        errors.append(
            {"code": "lineage_count_mismatch", "expected": counts.get("compiled_rows"),
             "actual": lineage_count}
        )
    expected_inventory = {
        (sheet, int(source_row))
        for sheet, rows in counts.get("source_inventory", {}).items()
        for source_row in rows
    }
    actual_inventory = {
        (row["source_sheet"], row["source_row"])
        for row in conn.execute(
            "SELECT source_sheet, source_row FROM source_row_disposition"
        )
    }
    if actual_inventory != expected_inventory:
        errors.append(
            {
                "code": "source_row_reconciliation_mismatch",
                "missing": sorted(expected_inventory - actual_inventory),
                "unexpected": sorted(actual_inventory - expected_inventory),
            }
        )
    catalog = {
        row["source_sheet"]: row["row_count"]
        for row in conn.execute(
            "SELECT source_sheet, row_count FROM source_table_catalog"
        )
    }
    disposition_counts = {
        row["source_sheet"]: row["count"]
        for row in conn.execute(
            "SELECT source_sheet, COUNT(*) AS count "
            "FROM source_row_disposition GROUP BY source_sheet"
        )
    }
    normalized_disposition_counts = {
        sheet: disposition_counts.get(sheet, 0) for sheet in catalog
    }
    if catalog != normalized_disposition_counts:
        errors.append({"code": "source_catalog_coverage_mismatch"})
    orphan_lineage = conn.execute(
        "SELECT COUNT(*) FROM import_lineage l WHERE NOT EXISTS ("
        "SELECT 1 FROM source_row_disposition d "
        "WHERE d.source_sheet=l.source_sheet AND d.source_row=l.source_row "
        "AND d.disposition='emitted')"
    ).fetchone()[0]
    emitted_without_lineage = conn.execute(
        "SELECT COUNT(*) FROM source_row_disposition d "
        "WHERE d.disposition='emitted' AND NOT EXISTS ("
        "SELECT 1 FROM import_lineage l WHERE l.source_sheet=d.source_sheet "
        "AND l.source_row=d.source_row)"
    ).fetchone()[0]
    invalid_dispositions = conn.execute(
        "SELECT COUNT(*) FROM source_row_disposition "
        "WHERE disposition='' OR reason='' OR disposition='emission_required' "
        "OR disposition IN ('decision_required', 'contract_mismatch') "
        "OR evidence_json='{}' OR (disposition='emitted' "
        "AND destinations_json='[]')"
    ).fetchone()[0]
    if orphan_lineage or emitted_without_lineage or invalid_dispositions:
        errors.append(
            {
                "code": "source_row_disposition_invalid",
                "orphan_lineage": orphan_lineage,
                "emitted_without_lineage": emitted_without_lineage,
                "invalid_dispositions": invalid_dispositions,
            }
        )
    return errors


def validate_mapping_coverage(conn: sqlite3.Connection) -> list[dict]:
    errors: list[dict] = []
    counts = _latest_counts(conn)
    actual = conn.execute("SELECT COUNT(*) FROM schema_mapping").fetchone()[0]
    if actual != counts.get("mapping_count"):
        errors.append(
            {"code": "schema_mapping_count_mismatch",
             "expected": counts.get("mapping_count"), "actual": actual}
        )
    actual_mapping_tables = {
        row["sql_table"]: row["count"]
        for row in conn.execute(
            "SELECT sql_table, COUNT(*) AS count FROM schema_mapping "
            "GROUP BY sql_table"
        )
    }
    if actual_mapping_tables != counts.get("mapping_tables", {}):
        errors.append({"code": "schema_mapping_coverage_mismatch"})
    mapping_rows = tuple(
        conn.execute(
            "SELECT source_sheet, source_column, model_key, sql_table, "
            "sql_column FROM schema_mapping"
        )
    )
    semantic_keys = [
        (
            row["source_sheet"],
            row["source_column"],
            row["model_key"],
            row["sql_table"],
            row["sql_column"],
        )
        for row in mapping_rows
    ]
    if len(semantic_keys) != len(set(semantic_keys)):
        errors.append({"code": "schema_mapping_semantic_duplicate"})
    sentinel = "__27vette_global_schema_mapping__"
    if sentinel in LIVE_MODELS or any(
        row["model_key"] == sentinel for row in mapping_rows
    ):
        errors.append({"code": "schema_mapping_global_sentinel_collision"})
    actual_columns = {
        (row["sql_table"], row["sql_column"]) for row in mapping_rows
    }
    required_columns = {
        (table, column)
        for table, columns in counts.get(
            "required_destination_columns", {}
        ).items()
        for column in columns
    }
    if not required_columns <= actual_columns:
        errors.append(
            {
                "code": "schema_mapping_destination_coverage_missing",
                "missing": sorted(required_columns - actual_columns),
            }
        )
    tables = _table_names(conn)
    missing_destination_columns = []
    for table, column in actual_columns:
        if table not in tables or column not in {
            row["name"]
            for row in conn.execute(f"PRAGMA table_info({_quote(table)})")
        }:
            missing_destination_columns.append((table, column))
    if missing_destination_columns:
        errors.append(
            {
                "code": "schema_mapping_destination_column_missing",
                "missing": sorted(missing_destination_columns),
            }
        )
    expected_physical = {
        physical_table(model, role)
        for model in LIVE_MODELS
        for role in MODEL_TABLE_ROLES
    }
    tables = _table_names(conn)
    if not expected_physical <= tables:
        errors.append(
            {"code": "physical_role_tables_missing",
             "missing": sorted(expected_physical - tables)}
        )
    registry = {
        (row["model_key"], row["table_role"], row["sql_table"])
        for row in conn.execute(
            "SELECT model_key, table_role, sql_table FROM model_table_registry"
        )
    }
    expected_registry = {
        (model, role, physical_table(model, role))
        for model in LIVE_MODELS
        for role in MODEL_TABLE_ROLES
    }
    if registry != expected_registry:
        errors.append({"code": "physical_role_registry_mismatch"})
    return errors


def candidate_integrity_errors(conn: sqlite3.Connection) -> list[dict]:
    errors = [dict(row) for row in conn.execute("PRAGMA foreign_key_check")]
    errors.extend(reconcile_source_counts(conn))
    errors.extend(validate_mapping_coverage(conn))
    return errors


def _fsync_file(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _same_destination(
    destination: Path, expected: DestinationSnapshot
) -> DestinationSnapshot:
    actual = capture_destination_snapshot(destination)
    if actual != expected:
        raise DestinationChanged(
            "destination_changed_during_import: destination snapshot drifted"
        )
    return actual


def _verify_backup(backup: Path, source: DestinationSnapshot) -> None:
    conn = db.connect_readonly(backup)
    try:
        errors = _integrity_errors(conn)
        logical = _logical_fingerprint(conn)
        user_version = conn.execute("PRAGMA user_version").fetchone()[0]
    finally:
        conn.close()
    if errors or logical != source.logical_fingerprint or user_version != source.user_version:
        raise BackupVerificationError(
            "backup_verification_failed: integrity or logical fingerprint mismatch"
        )


def _backup_destination(
    destination: Path, snapshot: DestinationSnapshot
) -> Path:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    backup = destination.with_name(f"{destination.name}.backup-{timestamp}")
    source = db.connect_readonly(destination)
    target = sqlite3.connect(backup)
    try:
        source.backup(target)
        target.commit()
        target.close()
        source.close()
        _verify_backup(backup, snapshot)
        _same_destination(destination, snapshot)
        _fsync_file(backup)
        _fsync_directory(destination.parent)
        return backup
    except BaseException:
        try:
            target.close()
        except sqlite3.Error:
            pass
        try:
            source.close()
        except sqlite3.Error:
            pass
        try:
            backup.unlink()
        except OSError:
            pass
        raise


def _checkpoint_and_verify_candidate(candidate: Path) -> None:
    conn = db.connect(candidate)
    try:
        errors = _integrity_errors(conn)
        errors.extend(candidate_integrity_errors(conn))
        if errors:
            raise ValueError(f"candidate integrity failed: {errors!r}")
        try:
            checkpoint = tuple(
                conn.execute("PRAGMA wal_checkpoint(TRUNCATE)").fetchone()
            )
        except sqlite3.DatabaseError as error:
            raise CandidateCheckpointError(
                f"candidate_checkpoint_failed: {error}"
            ) from error
        if len(checkpoint) != 3 or checkpoint[0] != 0 or checkpoint[1] != checkpoint[2]:
            raise CandidateCheckpointError(
                f"candidate_checkpoint_incomplete: {checkpoint!r}"
            )
    finally:
        conn.close()
    for suffix in ("-wal", "-shm"):
        artifact = Path(str(candidate) + suffix)
        if artifact.exists():
            artifact.unlink()
    _fsync_file(candidate)
    _fsync_directory(candidate.parent)
    readonly = db.connect_readonly(candidate)
    try:
        errors = _integrity_errors(readonly)
        errors.extend(
            [dict(row) for row in readonly.execute("PRAGMA foreign_key_check")]
        )
        errors.extend(reconcile_source_counts(readonly))
        errors.extend(validate_mapping_coverage(readonly))
        if errors:
            raise ValueError(
                f"candidate read-only verification failed: {errors!r}"
            )
    finally:
        readonly.close()


def finalize_candidate_for_audit(candidate: Path) -> None:
    """Checkpoint and freeze the exact sidecar-free candidate to be audited."""

    _checkpoint_and_verify_candidate(Path(candidate))


def promote_candidate(
    candidate: Path,
    destination: Path,
    snapshot: DestinationSnapshot,
) -> Path:
    """Reject direct promotion; the audited importer owns this boundary."""
    raise PermissionError(
        "contract_audit_required: use import_workbook for audited promotion"
    )


def _promote_audited_candidate(
    candidate: Path,
    destination: Path,
    snapshot: DestinationSnapshot,
    *,
    audit: ContractAudit,
) -> Path:
    """Promote only after the importer completed an empty contract audit."""
    from .contract_audit import ContractAudit, verify_audit_authorization

    if not isinstance(audit, ContractAudit):
        raise PermissionError("Completed audit for this exact candidate required")
    candidate_path = Path(candidate)
    destination_path = Path(destination)
    authorization = verify_audit_authorization(audit, candidate_path)
    if authorization == "missing":
        raise PermissionError("Completed audit for this exact candidate required")
    if authorization != "valid":
        raise CandidateChangedAfterAudit(
            "Candidate logical state or sidecars changed after contract audit"
        )
    _same_destination(destination_path, snapshot)
    rollback: Path | None = None
    try:
        if destination_path.exists():
            _backup_destination(destination_path, snapshot)
            _same_destination(destination_path, snapshot)
            rollback = destination_path.with_name(
                f".{destination_path.name}.rollback-{uuid.uuid4().hex}"
            )
            os.link(destination_path, rollback)
            _fsync_directory(destination_path.parent)
        _same_destination(destination_path, snapshot)
        authorization = verify_audit_authorization(
            audit, candidate_path, consume=True
        )
        if authorization != "valid":
            raise CandidateChangedAfterAudit(
                "Candidate logical state or sidecars changed before replacement"
            )
        os.replace(candidate_path, destination_path)
        _fsync_directory(destination_path.parent)
    except BaseException:
        if rollback is not None and rollback.exists():
            os.replace(rollback, destination_path)
            _fsync_directory(destination_path.parent)
        elif not candidate_path.exists() and destination_path.exists():
            destination_path.unlink()
            _fsync_directory(destination_path.parent)
        raise
    else:
        if rollback is not None:
            try:
                rollback.unlink()
                _fsync_directory(destination_path.parent)
            except OSError:
                # Promotion was already durably synced. A cleanup failure may
                # leave a harmless byte-identical rollback link, but must not
                # turn a successful replacement into a false failure report.
                pass
    return destination_path


def remove_candidate_artifacts(candidate: Path) -> None:
    paths = [
        Path(candidate),
        Path(str(candidate) + "-wal"),
        Path(str(candidate) + "-shm"),
    ]
    for path in paths:
        try:
            path.unlink()
        except OSError:
            pass
