"""Relational validation over the normalized tables.

Two consumers:
- the importer calls :func:`check_references` for a full unresolved-relationship
  sweep after ingest;
- the staging layer calls :func:`validate_record` / :func:`find_dependents`
  for per-change validation and delete protection.

All messages carry exact entity ids, field names, and sheet references.
"""

from __future__ import annotations

import sqlite3

from .specs import SPEC_BY_TABLE, TABLE_SPECS, RefSpec, TableSpec


def _interior_models(conn: sqlite3.Connection) -> dict[str, set[str]]:
    """model -> interior ids visible to it (via its interior_source_sheet)."""
    out: dict[str, set[str]] = {}
    rows = conn.execute(
        "SELECT model_key AS m, sheet_name FROM sheet_registry "
        "WHERE source_role='interior_source_sheet'"
    ).fetchall()
    for r in rows:
        ids = {x["interior_id"] for x in conn.execute(
            "SELECT interior_id FROM interiors WHERE src_sheet=?",
            (r["sheet_name"],))}
        out[r["m"]] = ids
    return out


def _ref_exists(conn, ref: RefSpec, value: str, model_id: str,
                interior_scope: dict[str, set[str]] | None = None) -> bool:
    if ref.scope == "global":
        row = conn.execute(
            f'SELECT 1 FROM {ref.target_table} WHERE "{ref.target_column}"=? '
            "LIMIT 1", (value,)).fetchone()
        return row is not None
    if ref.scope == "model":
        target_spec = SPEC_BY_TABLE[ref.target_table]
        if target_spec.model_scoped:
            row = conn.execute(
                f'SELECT 1 FROM {ref.target_table} WHERE model_id=? AND '
                f'"{ref.target_column}"=? LIMIT 1', (model_id, value)).fetchone()
        else:
            # model-scoped ref into a model_key-column table
            row = conn.execute(
                f'SELECT 1 FROM {ref.target_table} WHERE model_key=? AND '
                f'"{ref.target_column}"=? LIMIT 1', (model_id, value)).fetchone()
        return row is not None
    if ref.scope == "model_union":
        for table in ref.union_tables:
            tspec = SPEC_BY_TABLE[table]
            if tspec.model_scoped:
                row = conn.execute(
                    f'SELECT 1 FROM {table} WHERE model_id=? AND '
                    f'"{tspec.key[0]}"=? LIMIT 1', (model_id, value)).fetchone()
                if row:
                    return True
            elif table == "interiors":
                scope = (interior_scope or {}).get(model_id)
                if scope is not None and value in scope:
                    return True
                if scope is None:
                    row = conn.execute(
                        "SELECT 1 FROM interiors WHERE interior_id=? LIMIT 1",
                        (value,)).fetchone()
                    if row:
                        return True
            else:
                row = conn.execute(
                    f'SELECT 1 FROM {table} WHERE "{tspec.key[0]}"=? LIMIT 1',
                    (value,)).fetchone()
                if row:
                    return True
        return False
    return True


def check_references(conn: sqlite3.Connection) -> list[dict]:
    """Full sweep: report every unresolved reference in every table."""
    issues: list[dict] = []
    interior_scope = _interior_models(conn)
    for spec in TABLE_SPECS:
        if not spec.refs:
            continue
        rows = conn.execute(f"SELECT * FROM {spec.table}").fetchall()
        for row in rows:
            model_id = row["model_id"] if spec.model_scoped else (
                row["model_key"] if spec.has_model_key_column else "")
            key_label = "/".join(str(row[k]) for k in spec.key)
            for ref in spec.refs:
                value = str(row[ref.column] or "")
                if value == "":
                    if not ref.optional:
                        issues.append(_issue(spec, row, ref, key_label,
                                             model_id,
                                             f"required reference "
                                             f"{ref.column} is blank"))
                    continue
                if not _ref_exists(conn, ref, value, model_id, interior_scope):
                    issues.append(_issue(
                        spec, row, ref, key_label, model_id,
                        f"{spec.table}.{ref.column}={value!r} does not match "
                        f"any {ref.target_table}.{ref.target_column}"
                        + (f" for model {model_id!r}" if ref.scope != "global"
                           else "")))
    return issues


def _issue(spec, row, ref, key_label, model_id, message) -> dict:
    return {
        "severity": "error", "category": "unresolved_ref",
        "sheet": row["src_sheet"], "src_row": row["src_row"],
        "table_name": spec.table, "model_id": model_id or "",
        "entity_key": key_label, "field": ref.column, "message": message,
    }


# ── per-record validation (staging) ───────────────────────────────────

def validate_record(conn: sqlite3.Connection, spec: TableSpec, model_id: str,
                    record: dict, *, op: str, original_key: dict | None = None
                    ) -> list[dict]:
    errors: list[dict] = []

    def err(field, message):
        errors.append({
            "table": spec.table, "model_id": model_id or "",
            "field": field, "message": message,
            "entity_key": "/".join(str(record.get(k, "")) for k in spec.key),
        })

    # key completeness
    for k in spec.key:
        if str(record.get(k, "")).strip() == "":
            err(k, f"key field {k!r} is required")
    if errors:
        return errors

    # types + enums
    for col in spec.columns:
        name = col.sql_name()
        value = str(record.get(name, "") or "")
        if value == "":
            continue
        if col.ctype == "int":
            try:
                int(str(value).replace(",", ""))
            except ValueError:
                err(name, f"{name} must be an integer, got {value!r}")
        elif col.ctype == "bool":
            if value not in ("True", "False"):
                err(name, f"{name} must be True or False, got {value!r}")
        if col.enum and value not in col.enum:
            err(name, f"{name} must be one of {list(col.enum)}, got {value!r}")

    # keys are immutable on update (the workbook write path cannot rename
    # keys either — editor_ops treats them as immutable; renames must be
    # modeled as delete + add so dependents are inspected)
    if op == "update" and original_key:
        changed = [k for k in spec.key
                   if str(record.get(k)) != str(original_key.get(k))]
        if changed:
            for k in changed:
                err(k, f"key field {k!r} cannot change on update "
                       f"({original_key.get(k)!r} → {record.get(k)!r}); "
                       "stage a delete plus an add instead")
            return errors

    # uniqueness within scope
    if op == "add":
        where = " AND ".join(f'"{k}"=?' for k in spec.key)
        params = [str(record.get(k, "")) for k in spec.key]
        if spec.model_scoped:
            where = "model_id=? AND " + where
            params = [model_id, *params]
        row = conn.execute(
            f"SELECT 1 FROM {spec.table} WHERE {where} LIMIT 1", params
        ).fetchone()
        if row:
            err(",".join(spec.key),
                "a record with this key already exists in scope "
                + (f"(model {model_id})" if spec.model_scoped else "(global)"))

    # references
    interior_scope = _interior_models(conn)
    for ref in spec.refs:
        value = str(record.get(ref.column, "") or "")
        if value == "":
            if not ref.optional:
                err(ref.column, f"required reference {ref.column} is blank")
            continue
        if not _ref_exists(conn, ref, value, model_id, interior_scope):
            err(ref.column,
                f"{ref.column}={value!r} does not resolve to "
                f"{ref.target_table}.{ref.target_column}"
                + (f" for model {model_id!r}" if ref.scope != "global" else ""))
    return errors


# ── dependency inspection (delete protection) ────────────────────────

def find_dependents(conn: sqlite3.Connection, spec: TableSpec,
                    model_id: str, key: dict) -> list[dict]:
    """Records in other tables that reference the given record."""
    dependents: list[dict] = []
    # A record is referenced through its first key column value (canonical id)
    # by RefSpecs in other tables that target this table.
    target_col = spec.key[0]
    target_value = str(key.get(target_col, ""))
    if not target_value:
        return dependents
    for other in TABLE_SPECS:
        for ref in other.refs:
            targets = (ref.target_table,) if ref.scope != "model_union" \
                else ref.union_tables
            if spec.table not in targets:
                continue
            where = f'"{ref.column}"=?'
            params: list = [target_value]
            if other.model_scoped and spec.model_scoped:
                where += " AND model_id=?"
                params.append(model_id)
            rows = conn.execute(
                f"SELECT * FROM {other.table} WHERE {where}", params
            ).fetchall()
            for row in rows:
                dependents.append({
                    "table": other.table,
                    "model_id": row["model_id"] if other.model_scoped else (
                        row["model_key"] if other.has_model_key_column else ""),
                    "field": ref.column,
                    "entity_key": "/".join(str(row[k]) for k in other.key),
                    "src_sheet": row["src_sheet"],
                    "src_row": row["src_row"],
                })
    return dependents
