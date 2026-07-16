"""Canonical model table catalog and safe physical-table resolution."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from types import MappingProxyType
from typing import Mapping


LIVE_MODELS = ("stingray", "grand_sport", "z06")
MODEL_TABLE_ROLES = (
    "options",
    "option_availability",
    "rule_mapping",
    "price_rules",
    "rule_groups",
    "rule_group_members",
    "exclusive_groups",
    "exclusive_group_members",
    "variant_overrides",
    "interiors",
    "interior_scope",
    "interior_components",
    "color_overrides",
    "option_assets",
    "context_choice_assets",
    "default_selection_rules",
    "runtime_rule_exceptions",
)


ROLE_KEYS: Mapping[str, tuple[str, ...]] = MappingProxyType({
    "options": ("option_id",),
    "option_availability": ("option_id", "variant_id"),
    "rule_mapping": ("rule_id",),
    "price_rules": ("price_rule_id",),
    "rule_groups": ("group_id",),
    "rule_group_members": ("group_id", "target_option_id"),
    "exclusive_groups": ("group_id",),
    "exclusive_group_members": ("group_id", "option_id"),
    "variant_overrides": ("option_id", "variant_id"),
    "interiors": ("interior_id",),
    "interior_scope": ("interior_id", "trim_level", "body_style", "variant_id"),
    "interior_components": ("interior_id", "rpo", "component_type"),
    "color_overrides": ("interior_id", "option_id"),
    "option_assets": ("option_id",),
    "context_choice_assets": ("context_choice_id",),
    "default_selection_rules": ("rule_id",),
    "runtime_rule_exceptions": ("exception_id",),
})

ROLE_BOOLEAN_COLUMNS: Mapping[str, frozenset[str]] = MappingProxyType({
    "options": frozenset({"selectable", "active"}),
    "rule_groups": frozenset({"active"}),
    "rule_group_members": frozenset({"active"}),
    "exclusive_groups": frozenset({"active"}),
    "exclusive_group_members": frozenset({"active"}),
    "variant_overrides": frozenset({"selectable", "active"}),
    "interiors": frozenset({"requires_r6x", "active"}),
    "interior_scope": frozenset({"active"}),
    "interior_components": frozenset({"active"}),
    "option_assets": frozenset({"active"}),
    "context_choice_assets": frozenset({"active"}),
    "default_selection_rules": frozenset({"active"}),
    "runtime_rule_exceptions": frozenset({"active"}),
})

ROLE_ENUMS: Mapping[str, Mapping[str, tuple[object, ...]]] = MappingProxyType({
    "options": MappingProxyType({
        "display_behavior": (
            None, "default_selected", "hidden", "display_only", "auto_only"
        ),
    }),
    "option_availability": MappingProxyType({
        "status": ("standard", "available", "unavailable"),
    }),
    "rule_mapping": MappingProxyType({
        "rule_type": ("includes", "excludes", "requires"),
        "runtime_action": (None, "replace"),
    }),
    "price_rules": MappingProxyType({"price_rule_type": ("override",)}),
    "rule_groups": MappingProxyType({
        "group_type": ("requires_any", "excludes_any"),
    }),
    "exclusive_groups": MappingProxyType({
        "selection_mode": (
            "single_within_group", "required_single_within_group"
        ),
    }),
    "variant_overrides": MappingProxyType({
        "display_behavior": (
            None, "default_selected", "display_only", "hidden"
        ),
    }),
    "color_overrides": MappingProxyType({"rule_type": ("requires",)}),
    "default_selection_rules": MappingProxyType({
        "condition_type": (
            "always",
            "unless_selected_rpo",
            "unless_selected_section",
            "when_selected_unless_selected_section",
        ),
        "display_behavior": (None, "default_selected"),
    }),
})

ROLE_EDITOR_FAMILY: Mapping[str, str] = MappingProxyType({
    "options": "options",
    "option_availability": "ovs",
    "rule_mapping": "rule_mapping",
    "price_rules": "price_rules",
    "rule_groups": "rule_groups",
    "rule_group_members": "rule_group_members",
    "exclusive_groups": "exclusive_groups",
    "exclusive_group_members": "exclusive_members",
    "variant_overrides": "variant_overrides",
    "interiors": "interiors",
    "interior_scope": "model_interior_scope",
    "interior_components": "interior_components",
    "color_overrides": "color_overrides",
    "option_assets": "asset_map",
    "context_choice_assets": "asset_map",
    "default_selection_rules": "default_selection_rules",
    "runtime_rule_exceptions": "runtime_rule_exceptions",
})

ROLE_EXCLUSIVE_COLUMN_PAIRS: Mapping[str, tuple[tuple[str, str], ...]] = (
    MappingProxyType({
        "rule_mapping": (("source_option_id", "source_interior_id"),),
        "price_rules": (("condition_option_id", "condition_interior_id"),),
    })
)


@dataclass(frozen=True)
class ForeignKeySpec:
    columns: tuple[str, ...]
    target_table: str
    target_columns: tuple[str, ...]


@dataclass(frozen=True)
class RoleEditSpec:
    model_key: str
    table_role: str
    sql_table: str
    key: tuple[str, ...]
    columns: tuple[str, ...]
    types: Mapping[str, str]
    nullable: frozenset[str]
    required: frozenset[str]
    booleans: frozenset[str]
    enums: Mapping[str, tuple[object, ...]]
    foreign_keys: tuple[ForeignKeySpec, ...]


def physical_table(model_key: str, role: str) -> str:
    """Return a canonical physical table name for validated catalog values."""
    if model_key not in LIVE_MODELS or role not in MODEL_TABLE_ROLES:
        raise KeyError((model_key, role))
    return f"{model_key}_{role}"


def resolve_model_table(
    conn: sqlite3.Connection, model_key: str, role: str
) -> str:
    """Resolve an active registry row and reject unexpected identifiers."""
    row = conn.execute(
        "SELECT sql_table FROM model_table_registry "
        "WHERE model_key=? AND table_role=? AND active=1",
        (model_key, role),
    ).fetchone()
    if row is None or row["sql_table"] != physical_table(model_key, role):
        raise KeyError((model_key, role))
    return row["sql_table"]


def _quote_identifier(identifier: str) -> str:
    return '"' + identifier.replace('"', '""') + '"'


def edit_spec(
    conn: sqlite3.Connection, model_key: str, role: str
) -> RoleEditSpec:
    """Return immutable edit metadata for one allowlisted physical table."""
    table = resolve_model_table(conn, model_key, role)
    info = conn.execute(
        f"PRAGMA table_info({_quote_identifier(table)})"
    ).fetchall()
    if not info:
        raise KeyError((model_key, role))
    columns = tuple(row["name"] for row in info)
    types = MappingProxyType({
        row["name"]: "integer"
        if str(row["type"]).upper().startswith("INT") else "text"
        for row in info
    })
    nullable = frozenset(
        row["name"] for row in info if not row["notnull"] and not row["pk"]
    )
    required = frozenset(
        row["name"] for row in info
        if row["name"] != "model_key"
        and (row["pk"] or (row["notnull"] and row["dflt_value"] is None))
    )
    raw_fks = conn.execute(
        f"PRAGMA foreign_key_list({_quote_identifier(table)})"
    ).fetchall()
    grouped: dict[int, list[sqlite3.Row]] = {}
    for row in raw_fks:
        grouped.setdefault(int(row["id"]), []).append(row)
    foreign_keys = tuple(
        ForeignKeySpec(
            columns=tuple(row["from"] for row in sorted(rows, key=lambda x: x["seq"])),
            target_table=str(rows[0]["table"]),
            target_columns=tuple(
                row["to"] for row in sorted(rows, key=lambda x: x["seq"])
            ),
        )
        for _, rows in sorted(grouped.items())
    )
    return RoleEditSpec(
        model_key=model_key,
        table_role=role,
        sql_table=table,
        key=ROLE_KEYS[role],
        columns=columns,
        types=types,
        nullable=nullable,
        required=required,
        booleans=ROLE_BOOLEAN_COLUMNS.get(role, frozenset()),
        enums=ROLE_ENUMS.get(role, MappingProxyType({})),
        foreign_keys=foreign_keys,
    )
