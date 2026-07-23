"""Workbook -> SQLite import adapter (openpyxl lives only behind this API).

Import is tolerant: rows with duplicate identifiers or
unresolved references are still ingested (first occurrence wins for
duplicates) and every problem is recorded in ``import_issues`` so nothing
fails silently. Sheets without a normalized table remain workbook-owned and
are classified without copying their cells into a second SQLite store.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from openpyxl import load_workbook
from corvette_form_generator.schema_validation import REQUIRED_SHEETS

from . import db as dbmod
from .catalog import (
    RAW_PRESERVED_SHEETS,
    SPEC_BY_TABLE,
    TABLE_SPECS,
    TableSpec,
    RequiredValueError,
    projection_value,
    reconcile_columns,
)
from .validation import check_references


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
    return [r for _, r in rows if _truthy(r.get("active", ""))]


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

        # Preserved and unknown sheets remain workbook-owned. Record only their
        # disposition/count; never create a second SQLite cell store.
        for name in wb.sheetnames:
            if name in handled_sheets:
                continue
            _headers, rows = _sheet_rows(wb[name])
            disposition = "preserved" if name in RAW_PRESERVED_SHEETS else "unknown"
            self.row_counts[f"{disposition}:{name}"] = len(rows)
            if name not in RAW_PRESERVED_SHEETS:
                self.issue("warning", "unmanaged_sheet", sheet=name,
                           message=f"sheet {name!r} has no normalized table; "
                                   "left workbook-owned without cell projection")

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
                if sheet in REQUIRED_SHEETS:
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
        seen_sheets: set[tuple[str, ...]] = set()
        shared_models: dict[str, set[str]] = {}
        if not spec.model_scoped:
            for row in registry:
                if row.get("source_role") == spec.role and row.get("sheet_name"):
                    shared_models.setdefault(row["sheet_name"], set()).add(
                        row.get("model_key", "")
                    )
        for row in registry:
            if row.get("source_role") != spec.role:
                continue
            model = row.get("model_key", "")
            sheet = row.get("sheet_name", "")
            if not model or not sheet:
                continue
            sheet_identity = (model, sheet) if spec.model_scoped else (sheet,)
            if sheet_identity in seen_sheets:
                continue
            seen_sheets.add(sheet_identity)
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
            total += self._ingest_sheet(
                wb,
                sheet,
                spec,
                model_id=model if spec.model_scoped else None,
                model_context=sorted(shared_models.get(sheet, ())),
            )
        self.row_counts[spec.table] = total


    def _ingest_sheet(
        self,
        wb,
        sheet: str,
        spec: TableSpec,
        model_id: str | None,
        model_context: list[str] | None = None,
    ) -> int:
        headers, rows = _sheet_rows(wb[sheet])
        reconciliation = reconcile_columns(spec, headers)
        if reconciliation.duplicate:
            self.issue(
                "error",
                "duplicate_headers",
                sheet=sheet,
                table=spec.table,
                model=model_id or "",
                message=f"duplicate managed headers {list(reconciliation.duplicate)}",
            )
        if reconciliation.missing_required:
            self.issue("error", "missing_columns", sheet=sheet,
                       table=spec.table, model=model_id or "",
                       message=f"missing required columns "
                               f"{list(reconciliation.missing_required)}")
        if reconciliation.opaque:
            self.issue("warning", "unmapped_columns", sheet=sheet,
                       table=spec.table, model=model_id or "",
                       message=f"opaque managed-sheet columns "
                               f"{list(reconciliation.opaque)} remain workbook-owned")

        sql_cols = ["src_sheet", "src_row", "src_family", "physical_key", "model_context"]
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
            row_context = list(model_context or ([model_id] if model_id else []))
            if spec.has_model_key_column:
                row_model = str(rec.get("model_key") or "").strip()
                row_context = [row_model] if row_model else []
            values = [
                sheet,
                idx,
                spec.editor_family or spec.family,
                json.dumps(list(keyvals), separators=(",", ":")),
                json.dumps(row_context),
            ]
            if spec.model_scoped:
                values.append(model_id)
            projected_values = []
            for column in spec.columns:
                try:
                    projected_values.append(
                        projection_value(column, rec.get(column.header, ""))
                    )
                except RequiredValueError as exc:
                    self.issue(
                        "error",
                        "missing_required_value",
                        sheet=sheet,
                        src_row=idx,
                        table=spec.table,
                        model=model_id or "",
                        key=key_label,
                        field=column.header,
                        message=str(exc),
                    )
                    projected_values.append(None)
            values += projected_values
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


def import_workbook(conn: sqlite3.Connection, workbook_path: Path) -> dict:
    return Importer(conn, workbook_path).run()


def latest_report(conn: sqlite3.Connection) -> dict | None:
    row = conn.execute(
        "SELECT id FROM import_runs ORDER BY id DESC LIMIT 1").fetchone()
    if not row:
        return None
    imp = Importer(conn, Path("."))
    return imp.report(row["id"])
