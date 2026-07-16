"""Workbook -> SQLite import adapter (openpyxl lives only behind this API).

Import is lossless and tolerant: rows with duplicate identifiers or
unresolved references are still ingested (first occurrence wins for
duplicates) and every problem is recorded in ``import_issues`` so nothing
fails silently. Sheets without a normalized table are preserved verbatim in
``raw_sheet_rows`` so a regenerated workbook keeps unmanaged content.
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
from typing import Literal, Mapping

from openpyxl import load_workbook

from . import db as dbmod
from . import migration
from .catalog import LIVE_MODELS
from .central_compiler import compile_central_tables
from .compile_types import (
    CompiledTable,
    DecisionRequired,
    Finding,
    LineageEntry,
    SchemaMapping,
    SourceSheet,
    freeze_mapping,
)
from .model_compiler import compile_direct_model_tables
from .shared_compiler import compile_shared_model_tables
from .specs import (
    RAW_PRESERVED_SHEETS,
    SPEC_BY_TABLE,
    TABLE_SPECS,
    TableSpec,
)
from .validation import check_references
from .workbook_profile import profile_workbook


@dataclass(frozen=True)
class CompiledWorkbook:
    tables: tuple[CompiledTable, ...]
    source_catalog: tuple[SourceSheet, ...]
    schema_mappings: tuple[SchemaMapping, ...]
    lineage: tuple[LineageEntry, ...]
    findings: tuple[Finding, ...]


@dataclass(frozen=True)
class ImportReport:
    status: Literal["validated", "decision_required", "contract_mismatch"]
    live_models: tuple[str, ...]
    findings: tuple[Finding, ...]
    decision_required: tuple[Finding, ...]
    contract_differences: tuple[Finding, ...]
    candidate_path: Path | None
    promoted_path: Path | None

    @property
    def finding_codes(self) -> tuple[str, ...]:
        return tuple(finding.code for finding in self.findings)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _cell_text(value) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "True" if value else "False"
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)


def _sheet_rows(ws) -> tuple[list[str], list[tuple[int, dict]]]:
    it = ws.iter_rows(values_only=True)
    header = next(it, None)
    if header is None:
        return [], []
    headers = [str(h) if h is not None else "" for h in header]
    rows: list[tuple[int, dict]] = []
    for idx, values in enumerate(it, start=2):
        if values is None:
            continue
        record = {h: _cell_text(v) for h, v in zip(headers, values) if h}
        if all(v == "" for v in record.values()):
            continue
        rows.append((idx, record))
    return headers, rows


def _registry_rows(wb) -> list[dict]:
    _, rows = _sheet_rows(wb["model_workbook_sources"])
    return [r for _, r in rows]


def _truthy(value: str) -> bool:
    return str(value).strip().lower() in {"true", "1", "yes", "y", "x"}


class Importer:
    def __init__(self, conn: sqlite3.Connection, workbook_path: Path):
        self.conn = conn
        self.workbook_path = Path(workbook_path)
        self.issues: list[dict] = []
        self.row_counts: dict[str, int] = {}

    # ── issue reporting ───────────────────────────────────────────────
    def issue(self, severity, category, *, sheet="", src_row=None,
              table="", model="", key="", field="", message=""):
        self.issues.append({
            "severity": severity, "category": category, "sheet": sheet,
            "src_row": src_row, "table_name": table, "model_id": model,
            "entity_key": key, "field": field, "message": message,
        })

    # ── main entry ────────────────────────────────────────────────────
    def run(self) -> dict:
        digest = hashlib.sha256(self.workbook_path.read_bytes()).hexdigest()
        mtime_ns = str(self.workbook_path.stat().st_mtime_ns)
        wb = load_workbook(self.workbook_path, read_only=True, data_only=True)
        sheet_names = set(wb.sheetnames)

        dbmod.clear_imported_data(self.conn)

        registry = _registry_rows(wb)
        handled_sheets: set[str] = set()

        for spec in TABLE_SPECS:
            if spec.role:
                self._import_model_scoped(wb, spec, registry, handled_sheets,
                                          sheet_names)
            else:
                self._import_fixed(wb, spec, handled_sheets, sheet_names)

        # Preserve every remaining sheet verbatim (declared raw + anything new).
        for name in wb.sheetnames:
            if name in handled_sheets:
                continue
            if name not in RAW_PRESERVED_SHEETS:
                self.issue("warning", "unmanaged_sheet", sheet=name,
                           message=f"sheet {name!r} has no normalized table; "
                                   "imported verbatim into raw_sheet_rows")
            self._import_raw(wb, name)

        wb.close()

        ref_issues = check_references(self.conn)
        for iss in ref_issues:
            self.issues.append(iss)

        issue_counts = {"error": 0, "warning": 0}
        for iss in self.issues:
            issue_counts[iss["severity"]] = issue_counts.get(iss["severity"], 0) + 1

        cur = self.conn.execute(
            "INSERT INTO import_runs(ts, workbook_path, workbook_mtime_ns, "
            "workbook_sha256, status, row_counts_json, issue_counts_json) "
            "VALUES(?,?,?,?,?,?,?)",
            (_now(), str(self.workbook_path), mtime_ns, digest,
             "imported_with_issues" if issue_counts["error"] else "imported",
             json.dumps(self.row_counts), json.dumps(issue_counts)),
        )
        run_id = cur.lastrowid
        self.conn.executemany(
            "INSERT INTO import_issues(run_id, severity, category, sheet, "
            "src_row, table_name, model_id, entity_key, field, message) "
            "VALUES(?,?,?,?,?,?,?,?,?,?)",
            [(run_id, i["severity"], i["category"], i["sheet"], i["src_row"],
              i["table_name"], i["model_id"], i["entity_key"], i["field"],
              i["message"]) for i in self.issues],
        )
        dbmod.set_meta(self.conn, "workbook_mtime_ns", mtime_ns)
        dbmod.set_meta(self.conn, "workbook_sha256", digest)
        dbmod.set_meta(self.conn, "last_import_run_id", str(run_id))
        self.conn.commit()
        return self.report(run_id)

    def report(self, run_id: int) -> dict:
        run = self.conn.execute(
            "SELECT * FROM import_runs WHERE id=?", (run_id,)).fetchone()
        issues = self.conn.execute(
            "SELECT * FROM import_issues WHERE run_id=? ORDER BY id",
            (run_id,)).fetchall()
        return {
            "run": dict(run),
            "issues": [dict(i) for i in issues],
        }

    # ── sheet import paths ────────────────────────────────────────────
    def _import_fixed(self, wb, spec: TableSpec, handled: set, names: set):
        total = 0
        for sheet in spec.sheet:
            if sheet not in names:
                self.issue("error", "missing_sheet", sheet=sheet,
                           table=spec.table,
                           message=f"expected sheet {sheet!r} not found")
                continue
            handled.add(sheet)
            total += self._ingest_sheet(wb, sheet, spec, model_id=None)
        self.row_counts[spec.table] = total

    def _import_model_scoped(self, wb, spec: TableSpec, registry, handled,
                             names):
        total = 0
        seen_sheets: set[tuple[str, str]] = set()
        for row in registry:
            if row.get("source_role") != spec.role:
                continue
            model = row.get("model_key", "")
            sheet = row.get("sheet_name", "")
            if not model or not sheet:
                continue
            if (model, sheet) in seen_sheets:
                continue
            seen_sheets.add((model, sheet))
            if sheet not in names:
                self.issue("error", "missing_sheet", sheet=sheet, model=model,
                           table=spec.table,
                           message=f"registered sheet {sheet!r} for model "
                                   f"{model!r} not found in workbook")
                continue
            # Shared sheets (color_overrides, interiors) are fixed-table specs;
            # a model-scoped spec re-registering a shared sheet is skipped when
            # another table already owns that sheet.
            handled.add(sheet)
            total += self._ingest_sheet(wb, sheet, spec, model_id=model)
        self.row_counts[spec.table] = total

    def _import_raw(self, wb, sheet: str):
        headers, rows = _sheet_rows(wb[sheet])
        self.conn.executemany(
            "INSERT INTO raw_sheet_rows(sheet, src_row, data_json) VALUES(?,?,?)",
            [(sheet, idx, json.dumps(rec, ensure_ascii=False))
             for idx, rec in rows],
        )
        self.row_counts[f"raw:{sheet}"] = len(rows)

    def _ingest_sheet(self, wb, sheet: str, spec: TableSpec,
                      model_id: str | None) -> int:
        headers, rows = _sheet_rows(wb[sheet])
        expected = [c.header for c in spec.columns]
        missing = [h for h in expected if h not in headers]
        extra = [h for h in headers if h and h not in expected]
        if missing:
            self.issue("error", "missing_columns", sheet=sheet,
                       table=spec.table, model=model_id or "",
                       message=f"missing columns {missing}; these fields "
                               "import as blank")
        if extra:
            self.issue("warning", "unmapped_columns", sheet=sheet,
                       table=spec.table, model=model_id or "",
                       message=f"unmapped columns {extra} preserved via raw "
                               "export copy only")

        sql_cols = ["src_sheet", "src_row"]
        if spec.model_scoped:
            sql_cols.append("model_id")
        sql_cols += [c.sql_name() for c in spec.columns]
        placeholders = ",".join("?" for _ in sql_cols)
        collist = ",".join(f'"{c}"' for c in sql_cols)
        insert = f"INSERT INTO {spec.table} ({collist}) VALUES ({placeholders})"

        seen_keys: set[tuple] = set()
        count = 0
        for idx, rec in rows:
            keyvals = tuple(rec.get(k, "") for k in spec.key)
            key_id = (model_id or "",) + keyvals if spec.model_scoped else keyvals
            key_label = "/".join(v for v in keyvals if v) or f"row{idx}"
            if any(v == "" for v in keyvals):
                self.issue("error", "missing_identifier", sheet=sheet,
                           src_row=idx, table=spec.table,
                           model=model_id or "", key=key_label,
                           field=",".join(spec.key),
                           message=f"blank key column(s) in {sheet} row {idx}")
            if key_id in seen_keys:
                self.issue("error", "duplicate_id", sheet=sheet, src_row=idx,
                           table=spec.table, model=model_id or "",
                           key=key_label,
                           message=f"duplicate key {key_label!r} in {sheet} "
                                   f"row {idx}; first occurrence kept")
                continue
            seen_keys.add(key_id)
            values = [sheet, idx]
            if spec.model_scoped:
                values.append(model_id)
            values += [rec.get(c.header, "") for c in spec.columns]
            try:
                self.conn.execute(insert, values)
                count += 1
            except sqlite3.IntegrityError as exc:
                # Fixed-sheet tables with global keys (e.g. interiors across
                # two sheets) can still collide; report instead of failing.
                self.issue("error", "duplicate_id", sheet=sheet, src_row=idx,
                           table=spec.table, model=model_id or "",
                           key=key_label, message=str(exc))
        return count


def _central_schema_mappings(
    tables: tuple[CompiledTable, ...],
) -> tuple[SchemaMapping, ...]:
    """Materialize central column ownership from immutable row evidence."""
    contracts: dict[
        tuple[str, str, str, str], tuple[set[str], set[str]]
    ] = {}
    for table in tables:
        for row in table.rows:
            for destination_column in row.values:
                parameter = row.mapping_parameters.get(destination_column, {})
                if not isinstance(parameter, Mapping):
                    parameter = {}
                source_column = str(
                    parameter.get("source_column") or destination_column
                )
                key = (
                    row.source_sheet,
                    source_column,
                    table.name,
                    destination_column,
                )
                transforms, reverse_transforms = contracts.setdefault(
                    key, (set(), set())
                )
                transforms.add(str(parameter.get("transform") or "identity"))
                reverse_transforms.add(
                    str(parameter.get("reverse_transform") or "identity")
                )
    return tuple(
        SchemaMapping(
            source_sheet=source_sheet,
            source_column=source_column,
            destination_table=destination_table,
            destination_column=destination_column,
            transform="|".join(sorted(transforms)),
            reverse_transform="|".join(sorted(reverse_transforms)),
        )
        for (
            source_sheet,
            source_column,
            destination_table,
            destination_column,
        ), (transforms, reverse_transforms) in sorted(contracts.items())
    )


def _lineage(tables: tuple[CompiledTable, ...]) -> tuple[LineageEntry, ...]:
    entries: list[LineageEntry] = []
    for table in tables:
        for row in table.rows:
            entries.append(
                LineageEntry(
                    destination_table=table.name,
                    destination_key=freeze_mapping(
                        {
                            column: row.values[column]
                            for column in table.primary_key
                        }
                    ),
                    source_sheet=row.source_sheet,
                    source_row=row.source_row,
                    mapping_role=row.lineage_role,
                )
            )
    return tuple(entries)


def compile_workbook(path: Path) -> CompiledWorkbook:
    """Run the complete read-only workbook compiler sequence."""
    workbook_path = Path(path)
    profile = profile_workbook(workbook_path)
    central = compile_central_tables(profile, workbook_path)
    direct = compile_direct_model_tables(profile, workbook_path, central)
    shared = compile_shared_model_tables(
        profile, workbook_path, central, direct
    )
    tables = tuple(central) + tuple(shared.tables)
    mappings = _central_schema_mappings(tuple(central)) + tuple(
        mapping
        for table in shared.tables
        for mapping in table.schema_mappings
    )
    return CompiledWorkbook(
        tables=tables,
        source_catalog=profile.sheets,
        schema_mappings=mappings,
        lineage=_lineage(tables),
        findings=shared.findings,
    )


def load_candidate(compiled: CompiledWorkbook, path: Path) -> Path:
    return migration.load_candidate(compiled, path)


def promote_candidate(candidate: Path, destination: Path) -> Path:
    return migration.promote_candidate(candidate, destination)


def _report(
    findings: tuple[Finding, ...],
    *,
    candidate_path: Path | None = None,
    promoted_path: Path | None = None,
) -> ImportReport:
    decisions = tuple(
        finding for finding in findings if finding.status == "decision_required"
    )
    contracts = tuple(
        finding for finding in findings if finding.status == "contract_mismatch"
    )
    if decisions:
        status: Literal[
            "validated", "decision_required", "contract_mismatch"
        ] = "decision_required"
    elif contracts:
        status = "contract_mismatch"
    else:
        status = "validated"
    return ImportReport(
        status=status,
        live_models=LIVE_MODELS,
        findings=findings,
        decision_required=decisions,
        contract_differences=contracts,
        candidate_path=candidate_path,
        promoted_path=promoted_path,
    )


def _decision_finding(error: DecisionRequired) -> Finding:
    return Finding(
        severity="error",
        status="decision_required",
        code=error.code,
        message=str(error),
        source_sheet=error.source_sheet,
        source_row=error.source_row,
        source_column=error.source_column,
        value=error.value,
    )


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _canonical_import_workbook(
    destination: Path,
    workbook_path: Path,
    *,
    audit_contracts: bool,
) -> ImportReport:
    destination_path = Path(destination)
    workbook = Path(workbook_path)

    legacy_findings = migration.audit_legacy_destination(destination_path)
    if legacy_findings:
        return _report(legacy_findings)

    if not audit_contracts:
        # TASK 6 ONLY: Task 7 deletes this branch and makes the contract
        # auditor mandatory.  Keeping the bypass behind pytest's per-test
        # marker prevents API and normal runtime callers from selecting it.
        if "PYTEST_CURRENT_TEST" not in os.environ:
            return _report(
                (
                    Finding(
                        severity="error",
                        status="contract_mismatch",
                        code="contract_audit_test_bypass_rejected",
                        message=(
                            "audit_contracts=False is restricted to Task 6 "
                            "tests until the Task 7 auditor exists."
                        ),
                    ),
                )
            )
    else:
        return _report(
            (
                Finding(
                    severity="error",
                    status="contract_mismatch",
                    code="contract_auditor_unavailable",
                    message=(
                        "Task 7 must provide the mandatory contract auditor "
                        "before production promotion is enabled."
                    ),
                ),
            )
        )

    try:
        initial_mtime_ns = str(workbook.stat().st_mtime_ns)
        initial_sha256 = _file_sha256(workbook)
    except OSError as error:
        return _report(
            (
                Finding(
                    severity="error",
                    status="decision_required",
                    code="workbook_unavailable",
                    message=str(error),
                    value=str(workbook),
                ),
            )
        )
    try:
        compiled = compile_workbook(workbook)
    except DecisionRequired as error:
        return _report((_decision_finding(error),))
    except (KeyError, ValueError) as error:
        return _report(
            (
                Finding(
                    severity="error",
                    status="contract_mismatch",
                    code="workbook_compile_contract_mismatch",
                    message=str(error),
                ),
            )
        )
    if (
        str(workbook.stat().st_mtime_ns) != initial_mtime_ns
        or _file_sha256(workbook) != initial_sha256
    ):
        return _report(
            (
                Finding(
                    severity="error",
                    status="decision_required",
                    code="workbook_changed_during_compile",
                    message=(
                        "The workbook changed during read-only compilation; "
                        "retry from a stable source file."
                    ),
                ),
            )
        )

    blocking = tuple(
        finding
        for finding in compiled.findings
        if finding.status in {"decision_required", "contract_mismatch"}
        or finding.severity == "error"
    )
    if blocking:
        return _report(blocking)

    destination_path.parent.mkdir(parents=True, exist_ok=True)
    candidate = destination_path.with_name(
        f".{destination_path.name}.candidate-{uuid.uuid4().hex}.sqlite3"
    )
    try:
        migration.load_candidate(
            compiled,
            candidate,
            workbook_path=workbook,
            workbook_mtime_ns=initial_mtime_ns,
            workbook_sha256=initial_sha256,
        )
        conn = dbmod.connect(candidate)
        try:
            errors = migration.candidate_integrity_errors(conn)
        finally:
            conn.close()
        if errors:
            findings = tuple(
                Finding(
                    severity="error",
                    status="contract_mismatch",
                    code=str(error.get("code") or "candidate_integrity_error"),
                    message=json.dumps(error, sort_keys=True, default=str),
                    value=error,
                )
                for error in errors
            )
            return _report(findings, candidate_path=candidate)
        promoted = promote_candidate(candidate, destination_path)
        return _report(
            compiled.findings,
            candidate_path=candidate,
            promoted_path=promoted,
        )
    except (OSError, sqlite3.DatabaseError, ValueError) as error:
        return _report(
            (
                Finding(
                    severity="error",
                    status="contract_mismatch",
                    code="candidate_build_or_promotion_failed",
                    message=str(error),
                ),
            ),
            candidate_path=candidate,
        )
    finally:
        migration.remove_candidate_artifacts(candidate)


def import_workbook(
    db_path: Path | sqlite3.Connection,
    workbook_path: Path,
    *,
    audit_contracts: bool = True,
) -> ImportReport | dict:
    """Import through the canonical path, or the reserved Stage 1 adapter.

    The connection form is temporary compatibility for the reserved legacy
    ``tests/test_workbook_manager.py`` suite only and is not used by the
    canonical candidate path.  Task 8 removes it with the legacy schema.
    """
    if isinstance(db_path, sqlite3.Connection):
        if audit_contracts is not True:
            raise TypeError("legacy connection import has no audit bypass")
        return Importer(db_path, workbook_path).run()
    return _canonical_import_workbook(
        Path(db_path), Path(workbook_path), audit_contracts=audit_contracts
    )


def latest_report(conn: sqlite3.Connection) -> dict | None:
    row = conn.execute(
        "SELECT id FROM import_runs ORDER BY id DESC LIMIT 1").fetchone()
    if not row:
        return None
    imp = Importer(conn, Path("."))
    return imp.report(row["id"])
