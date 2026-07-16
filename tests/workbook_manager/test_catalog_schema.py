import sqlite3

import pytest

from app import db
from app.catalog import (
    LIVE_MODELS,
    MODEL_TABLE_ROLES,
    physical_table,
    resolve_model_table,
)


def test_connection_enables_foreign_keys(connection):
    assert connection.execute("PRAGMA foreign_keys").fetchone()[0] == 1


def test_each_live_model_has_identical_physical_roles(connection):
    db.create_canonical_schema(connection)
    names = {
        row["name"]
        for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )
    }
    for model in LIVE_MODELS:
        assert {physical_table(model, role) for role in MODEL_TABLE_ROLES} <= names


def test_option_id_is_actual_primary_key(connection):
    db.create_canonical_schema(connection)
    for model in LIVE_MODELS:
        info = connection.execute(
            f"PRAGMA table_info({physical_table(model, 'options')})"
        ).fetchall()
        pk = [row["name"] for row in info if row["pk"]]
        assert pk == ["option_id"]


def test_model_owned_table_rejects_wrong_model(connection):
    db.create_canonical_schema(connection)
    connection.executemany(
        "INSERT INTO models(model_key, registry_key, model_label, active) "
        "VALUES(?, ?, ?, 1)",
        (
            ("stingray", "stingray", "Stingray"),
            ("z06", "z06", "Z06"),
        ),
    )
    connection.execute(
        "INSERT INTO sections(section_id, section_name) VALUES('sec_x', 'Test')"
    )
    with pytest.raises(sqlite3.IntegrityError, match="CHECK constraint failed"):
        connection.execute(
            "INSERT INTO stingray_options("
            "model_key, option_id, rpo, price, option_name, section_id, "
            "selectable, display_order, active"
            ") VALUES('z06', 'opt_x', 'X', 0, 'Test', 'sec_x', 1, 1, 1)"
        )


def test_registry_resolves_only_expected_physical_table(connection):
    db.create_canonical_schema(connection)
    connection.execute(
        "INSERT INTO models(model_key, registry_key, model_label, active) "
        "VALUES('stingray', 'stingray', 'Stingray', 1)"
    )
    connection.execute(
        "INSERT INTO model_table_registry("
        "model_key, table_role, sql_table, mapping_type, active"
        ") VALUES('stingray', 'options', 'stingray_options', 'exact', 1)"
    )
    assert resolve_model_table(connection, "stingray", "options") == (
        "stingray_options"
    )
    with pytest.raises(KeyError):
        physical_table("zr1", "options")
    with pytest.raises(KeyError):
        resolve_model_table(connection, "z06", "options")
