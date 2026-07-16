"""Canonical model table catalog and safe physical-table resolution."""

from __future__ import annotations

import sqlite3


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
