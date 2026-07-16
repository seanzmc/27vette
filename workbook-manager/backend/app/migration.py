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
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Mapping

from . import db
from .catalog import LIVE_MODELS, MODEL_TABLE_ROLES, physical_table
from .compile_types import Finding

if TYPE_CHECKING:
    from .importer import CompiledWorkbook


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


def audit_legacy_destination(destination: Path) -> tuple[Finding, ...]:
    """Read legacy edit state without creating or mutating destination files."""
    path = Path(destination)
    if not path.exists():
        return ()
    sidecars = tuple(
        artifact.name
        for artifact in (Path(str(path) + "-wal"), Path(str(path) + "-shm"))
        if artifact.exists()
    )
    if sidecars:
        return (
            Finding(
                severity="error",
                status="decision_required",
                code="legacy_destination_sidecars",
                message=(
                    "The destination has SQLite WAL/SHM sidecars. Close its "
                    "owner and checkpoint it before atomic replacement; the "
                    "importer will not guess whether these files are stale."
                ),
                value={"sidecars": sidecars},
            ),
        )
    conn = db.connect_readonly(path)
    try:
        tables = _table_names(conn)
        findings: list[Finding] = []
        if "pending_changes" in tables:
            count = conn.execute(
                "SELECT COUNT(*) FROM pending_changes WHERE status='staged'"
            ).fetchone()[0]
            if count:
                findings.append(
                    Finding(
                        severity="error",
                        status="decision_required",
                        code="legacy_pending_changes",
                        message=(
                            "The destination contains staged legacy changes; "
                            "resolve them before canonical replacement."
                        ),
                        value={"count": count},
                    )
                )
        if "change_history" in tables:
            columns = {
                row["name"]
                for row in conn.execute("PRAGMA table_info(change_history)")
            }
            if "sync_status" in columns:
                count = conn.execute(
                    "SELECT COUNT(*) FROM change_history "
                    "WHERE sync_status NOT IN ('synced', 'n/a')"
                ).fetchone()[0]
                if count:
                    findings.append(
                        Finding(
                            severity="error",
                            status="decision_required",
                            code="legacy_unsynced_change_history",
                            message=(
                                "The destination contains unsynced legacy history; "
                                "resolve it before canonical replacement."
                            ),
                            value={"count": count},
                        )
                    )
        return tuple(findings)
    finally:
        conn.close()


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
            source_sheets = tuple(
                sorted({row.source_sheet for row in table.rows})
            )
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


def _source_reconciliation(compiled: "CompiledWorkbook") -> dict[str, dict]:
    lineage_rows: dict[str, set[int]] = {}
    for entry in compiled.lineage:
        lineage_rows.setdefault(entry.source_sheet, set()).add(entry.source_row)
    finding_rows: dict[str, set[int]] = {}
    for finding in compiled.findings:
        if finding.source_row is not None:
            finding_rows.setdefault(finding.source_sheet, set()).add(
                finding.source_row
            )
    result = {}
    for source in compiled.source_catalog:
        emitted = lineage_rows.get(source.source_sheet, set())
        findings = finding_rows.get(source.source_sheet, set()) - emitted
        explicitly_disposed = source.row_count - len(emitted) - len(findings)
        result[source.source_sheet] = {
            "source_rows": source.row_count,
            "lineage_source_rows": len(emitted),
            "finding_rows": len(findings),
            "catalog_disposition_rows": explicitly_disposed,
            "disposition": source.disposition,
        }
    return result


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
        "sources": _source_reconciliation(compiled),
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
                        "",
                        mapping.destination_table,
                        mapping.destination_column,
                        mapping.transform,
                        _json({"reverse_transform": mapping.reverse_transform}),
                        "mapped",
                        "",
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
    catalog = {
        row["source_sheet"]: row["row_count"]
        for row in conn.execute("SELECT source_sheet, row_count FROM source_table_catalog")
    }
    actual_lineage_rows = {
        row["source_sheet"]: row["count"]
        for row in conn.execute(
            "SELECT source_sheet, COUNT(DISTINCT source_row) AS count "
            "FROM import_lineage GROUP BY source_sheet"
        )
    }
    actual_finding_rows = {
        row["sheet"]: row["count"]
        for row in conn.execute(
            "SELECT sheet, COUNT(DISTINCT src_row) AS count FROM import_issues "
            "WHERE src_row IS NOT NULL AND NOT EXISTS ("
            "SELECT 1 FROM import_lineage WHERE source_sheet=import_issues.sheet "
            "AND source_row=import_issues.src_row) GROUP BY sheet"
        )
    }
    for sheet, expected in counts.get("sources", {}).items():
        reconciled = (
            expected["lineage_source_rows"]
            + expected["finding_rows"]
            + expected["catalog_disposition_rows"]
        )
        if (
            catalog.get(sheet) != expected["source_rows"]
            or reconciled != expected["source_rows"]
            or expected["catalog_disposition_rows"] < 0
            or actual_lineage_rows.get(sheet, 0) != expected["lineage_source_rows"]
            or actual_finding_rows.get(sheet, 0) != expected["finding_rows"]
        ):
            errors.append(
                {"code": "source_row_reconciliation_mismatch", "source_sheet": sheet,
                 "expected": expected["source_rows"], "actual": reconciled,
                 "catalog": catalog.get(sheet)}
            )
    if set(catalog) != set(counts.get("sources", {})):
        errors.append({"code": "source_catalog_coverage_mismatch"})
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


def _backup_destination(destination: Path) -> Path:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    backup = destination.with_name(f"{destination.name}.backup-{timestamp}")
    source = db.connect_readonly(destination)
    target = sqlite3.connect(backup)
    try:
        source.backup(target)
        target.commit()
    finally:
        target.close()
        source.close()
    _fsync_file(backup)
    _fsync_directory(destination.parent)
    return backup


def promote_candidate(candidate: Path, destination: Path) -> Path:
    """Checkpoint, sync, back up, and atomically promote a verified candidate."""
    candidate_path = Path(candidate)
    destination_path = Path(destination)
    conn = db.connect(candidate_path)
    try:
        errors = candidate_integrity_errors(conn)
        if errors:
            raise ValueError(f"candidate integrity failed: {errors!r}")
        conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    finally:
        conn.close()
    for suffix in ("-wal", "-shm"):
        artifact = Path(str(candidate_path) + suffix)
        if artifact.exists():
            artifact.unlink()
    _fsync_file(candidate_path)
    _fsync_directory(candidate_path.parent)
    rollback: Path | None = None
    try:
        if destination_path.exists():
            _backup_destination(destination_path)
            rollback = destination_path.with_name(
                f".{destination_path.name}.rollback-{uuid.uuid4().hex}"
            )
            os.link(destination_path, rollback)
            _fsync_directory(destination_path.parent)
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
    for path in (Path(candidate), Path(str(candidate) + "-wal"), Path(str(candidate) + "-shm")):
        try:
            path.unlink()
        except FileNotFoundError:
            pass
