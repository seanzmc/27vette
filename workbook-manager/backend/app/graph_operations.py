"""Registry-derived helpers for coordinated Workbook Manager graph operations."""

from __future__ import annotations

import json
import sqlite3
from collections import deque
from typing import Any

from .catalog import (
    REFERENCE_OPTION_PRESENTATION,
    SPEC_BY_FAMILY,
    SPEC_BY_TABLE,
    TABLE_SPECS,
    TableSpec,
)


def _truthy(value: Any) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "y"}


def active_model_variants(conn: sqlite3.Connection, model_id: str) -> list[dict]:
    """Return active registered variants without consulting existing OVS rows."""

    rows = conn.execute(
        "SELECT mv.variant_id, v.display_name, mv.display_order "
        "FROM model_variants mv JOIN variants v ON v.variant_id=mv.variant_id "
        "WHERE mv.model_key=? AND LOWER(COALESCE(mv.active,'')) IN ('1','true','yes','y') "
        "AND LOWER(COALESCE(v.active,'')) IN ('1','true','yes','y') "
        "ORDER BY CAST(mv.display_order AS INTEGER), mv.id",
        (model_id,),
    ).fetchall()
    return [
        {
            "variant_id": str(row["variant_id"]),
            "display_name": str(row["display_name"] or row["variant_id"]),
            "display_order": row["display_order"],
        }
        for row in rows
    ]


def _row_key(spec: TableSpec, row: dict) -> tuple[str, ...]:
    return tuple(str(row.get(name) or "") for name in spec.key)


def _operation_model(operation: dict, spec: TableSpec) -> str:
    """Model identity an operation belongs to, mirroring stored row ownership."""
    final = operation.get("final") or operation.get("original") or {}
    if spec.model_scoped:
        return str(operation.get("model_id") or "")
    if spec.has_model_key_column:
        return str(final.get("model_key") or operation.get("model_id") or "")
    return ""


def _operation_applies(operation: dict, spec: TableSpec, model_id: str) -> bool:
    if operation.get("table_name") != spec.table:
        return False
    if not model_id:
        # Shared-root scans carry no model context; every operation for the
        # table applies at its own stored model identity.
        return True
    operation_model = str(operation.get("model_id") or "")
    if spec.model_scoped:
        return operation_model == model_id
    if spec.has_model_key_column:
        final = operation.get("final") or operation.get("original") or {}
        return str(final.get("model_key") or operation_model) == model_id
    return True


def _effective_rows(
    conn: sqlite3.Connection,
    spec: TableSpec,
    model_id: str,
    operations: list[dict],
) -> list[dict]:
    where = ""
    params: tuple[str, ...] = ()
    if model_id:
        if spec.model_scoped:
            where, params = " WHERE model_id=?", (model_id,)
        elif spec.has_model_key_column:
            where, params = " WHERE model_key=?", (model_id,)
    rows: dict[tuple, dict] = {}
    for row in conn.execute(f'SELECT * FROM "{spec.table}"{where}', params).fetchall():
        row = dict(row)
        rows[_identity(spec, row, model_id)] = row
    for operation in operations:
        if not _operation_applies(operation, spec, model_id):
            continue
        key = tuple(str((operation.get("entity_key") or {}).get(name) or "") for name in spec.key)
        identity = (spec.table, _operation_model(operation, spec), key)
        if operation.get("action") == "delete":
            rows.pop(identity, None)
            continue
        effective = dict(operation.get("final") or {})
        effective.update({
            "src_sheet": operation.get("source_sheet") or effective.get("src_sheet") or "",
            "src_row": operation.get("source_row"),
            "model_id": operation.get("model_id") or effective.get("model_id") or "",
        })
        if spec.has_model_key_column and not effective.get("model_key"):
            effective["model_key"] = _operation_model(operation, spec)
        rows[identity] = effective
    return list(rows.values())


def _row_model(spec: TableSpec, row: dict, fallback: str) -> str:
    if spec.model_scoped:
        return str(row.get("model_id") or fallback)
    if spec.has_model_key_column:
        return str(row.get("model_key") or fallback)
    return ""


def _identity(spec: TableSpec, row: dict, model_id: str) -> tuple:
    return (spec.table, _row_model(spec, row, model_id), _row_key(spec, row))


def _conditional_edges(spec: TableSpec) -> tuple[dict, ...]:
    """Registered conditional references of one spec as resolved edges.

    Each edge carries the discriminator that activates it, the column holding
    the referenced value, the concrete target table, and the target column the
    value resolves against (presentation domains such as ``option_rpos`` match
    the option RPO rather than the option id).
    """

    meta = dict(spec.conditional_ref)
    if not meta:
        return ()
    discriminator_column = str(meta.get("discriminator") or "")
    source_column = str(meta.get("column") or "")
    if not discriminator_column or not source_column:
        return ()
    edges: list[dict] = []
    for discriminator_value, family in dict(spec.conditional_refs).items():
        if family is None:
            continue
        target = SPEC_BY_FAMILY[family].table if family in SPEC_BY_FAMILY else family
        presentation = REFERENCE_OPTION_PRESENTATION.get(target)
        if presentation is None:
            raise ValueError(
                f"{spec.table}.{source_column} conditional target {family!r} "
                "has no reference presentation"
            )
        table = str(presentation.get("table") or target)
        if SPEC_BY_TABLE.get(table) is None:
            raise ValueError(
                f"{spec.table}.{source_column} conditional target {family!r} "
                f"resolves to unknown table {table!r}"
            )
        edges.append({
            "discriminator_column": discriminator_column,
            "discriminator_value": str(discriminator_value),
            "column": source_column,
            "target_table": table,
            "match_column": str(presentation["value"]),
        })
    return tuple(edges)


def dependency_plan(
    conn: sqlite3.Connection,
    operations: list[dict],
    *,
    table: str,
    model_id: str,
    key: dict[str, str],
) -> dict:
    """Classify direct/transitive dependents in the draft-effective graph.

    A concrete ``model_id`` scopes every scanned table to that model's rows.
    An empty ``model_id`` (shared roots such as ``interiors`` carry no model
    context) scans every model-scoped and model-key table across all models so
    the plan still classifies cross-model dependents.
    """

    root_spec = SPEC_BY_TABLE.get(table)
    if root_spec is None:
        raise ValueError(f"unknown table {table!r}")
    if set(key) != set(root_spec.key):
        raise ValueError("dependency-plan key does not match the registered key")

    effective = {
        spec.table: _effective_rows(conn, spec, model_id, operations)
        for spec in TABLE_SPECS
    }
    root_key = tuple(str(key[name]) for name in root_spec.key)
    root_row = next(
        (row for row in effective[root_spec.table] if _row_key(root_spec, row) == root_key),
        None,
    )
    if root_row is None:
        raise ValueError("draft-effective record was not found")

    root_identity = _identity(root_spec, root_row, model_id)
    visited = {root_identity}
    queue = deque([(root_spec, root_row, 0)])
    dependents: list[dict] = []
    conditional_edge_memo: dict[str, tuple[dict, ...]] = {}

    def conditional_edges_for(spec: TableSpec) -> tuple[dict, ...]:
        cached = conditional_edge_memo.get(spec.table)
        if cached is None:
            cached = _conditional_edges(spec)
            conditional_edge_memo[spec.table] = cached
        return cached

    while queue:
        target_spec, target_row, parent_depth = queue.popleft()
        target_value = str(target_row.get(target_spec.key[0]) or "")
        if not target_value:
            continue
        for other in TABLE_SPECS:
            direct_columns = [
                ref.column for ref in other.refs
                if target_spec.table in (
                    ref.union_tables if ref.scope == "model_union" else (ref.target_table,)
                )
            ]
            conditional = [
                edge for edge in conditional_edges_for(other)
                if edge["target_table"] == target_spec.table
            ]
            if not direct_columns and not conditional:
                continue
            for row in effective[other.table]:
                via_field = ""
                why = ""
                for column in direct_columns:
                    if str(row.get(column) or "") != target_value:
                        continue
                    via_field = column
                    why = (
                        f"{other.table}.{column} references "
                        f"{target_spec.table}.{target_spec.key[0]}={target_value}"
                    )
                    break
                if not via_field:
                    row_discriminator = ""
                    for edge in conditional:
                        if not row_discriminator:
                            row_discriminator = str(
                                row.get(edge["discriminator_column"]) or ""
                            ).strip().lower()
                        if row_discriminator != edge["discriminator_value"].strip().lower():
                            continue
                        match_value = str(target_row.get(edge["match_column"]) or "")
                        if not match_value:
                            continue
                        if str(row.get(edge["column"]) or "") != match_value:
                            continue
                        via_field = edge["column"]
                        why = (
                            f"{other.table}.{edge['column']} references "
                            f"{target_spec.table}.{edge['match_column']}={match_value} "
                            f"when {edge['discriminator_column']}="
                            f"{edge['discriminator_value']}"
                        )
                        break
                if not via_field:
                    continue
                identity = _identity(other, row, model_id)
                if identity in visited:
                    continue
                visited.add(identity)
                depth = parent_depth + 1
                entity_key = {name: str(row.get(name) or "") for name in other.key}
                allowed_actions = ["keep", "delete"]
                if other.column_by_name("active") is not None and _truthy(row.get("active")):
                    allowed_actions.append("deactivate")
                item = {
                    "table": other.table,
                    "family": other.editor_family or other.family,
                    "model_id": _row_model(other, row, model_id),
                    "entity_key": entity_key,
                    "src_sheet": str(row.get("src_sheet") or ""),
                    "src_row": row.get("src_row"),
                    "depth": depth,
                    "classification": "direct" if depth == 1 else "transitive",
                    "via_field": via_field,
                    "why": why,
                    "parent": {
                        "table": target_spec.table,
                        "entity_key": {
                            name: str(target_row.get(name) or "")
                            for name in target_spec.key
                        },
                    },
                    "allowed_actions": allowed_actions,
                    "selected_action": "keep",
                }
                dependents.append(item)
                queue.append((other, row, depth))

    dependents.sort(
        key=lambda item: (
            item["depth"],
            item["table"],
            json.dumps(item["entity_key"], sort_keys=True),
        )
    )
    return {
        "table": table,
        "model_id": model_id,
        "entity_key": {name: str(key[name]) for name in root_spec.key},
        "dependents": dependents,
        "count": len(dependents),
        "complete": not dependents,
    }
