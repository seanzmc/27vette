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


def _insert_variant_domains(connection):
    connection.executemany(
        "INSERT INTO models(model_key, registry_key, model_label, active) "
        "VALUES(?, ?, ?, 1)",
        (
            ("stingray", "stingray", "Stingray"),
            ("z06", "z06", "Z06"),
        ),
    )
    connection.execute("INSERT INTO body_styles VALUES('coupe')")
    connection.execute("INSERT INTO trim_levels VALUES('1lt')")
    connection.executemany(
        "INSERT INTO variants("
        "variant_id, model_year, trim_level, body_style, display_name, "
        "base_price, display_order, active"
        ") VALUES(?, 2026, '1lt', 'coupe', ?, 0, 1, 1)",
        (
            ("stingray_1lt_coupe", "Stingray 1LT Coupe"),
            ("z06_1lt_coupe", "Z06 1LT Coupe"),
        ),
    )
    connection.executemany(
        "INSERT INTO model_variants("
        "model_key, variant_id, display_order, active"
        ") VALUES(?, ?, 1, 1)",
        (
            ("stingray", "stingray_1lt_coupe"),
            ("z06", "z06_1lt_coupe"),
        ),
    )
    connection.execute(
        "INSERT INTO sections(section_id, section_name) VALUES('sec_x', 'Test')"
    )
    connection.execute(
        "INSERT INTO stingray_options("
        "model_key, option_id, rpo, price, option_name, section_id, "
        "selectable, display_order, active"
        ") VALUES('stingray', 'opt_x', 'X', 0, 'Test', 'sec_x', 1, 1, 1)"
    )


def test_model_variant_reference_rejects_cross_model_membership(connection):
    db.create_canonical_schema(connection)
    _insert_variant_domains(connection)
    with pytest.raises(sqlite3.IntegrityError, match="FOREIGN KEY constraint failed"):
        connection.execute(
            "INSERT INTO stingray_option_availability("
            "model_key, option_id, variant_id, status"
            ") VALUES('stingray', 'opt_x', 'z06_1lt_coupe', 'available')"
        )


def test_model_variant_reference_accepts_same_model_membership(connection):
    db.create_canonical_schema(connection)
    _insert_variant_domains(connection)
    connection.execute(
        "INSERT INTO stingray_option_availability("
        "model_key, option_id, variant_id, status"
        ") VALUES('stingray', 'opt_x', 'stingray_1lt_coupe', 'available')"
    )
    assert connection.execute(
        "SELECT variant_id FROM stingray_option_availability"
    ).fetchone()["variant_id"] == "stingray_1lt_coupe"


def test_every_model_owned_variant_reference_is_model_scoped(connection):
    db.create_canonical_schema(connection)
    variant_columns = {
        "option_availability": "variant_id",
        "rule_mapping": "variant_scope",
        "price_rules": "variant_scope",
        "rule_groups": "variant_scope",
        "variant_overrides": "variant_id",
        "interior_scope": "variant_id",
        "default_selection_rules": "variant_scope",
        "runtime_rule_exceptions": "variant_scope",
    }
    for model in LIVE_MODELS:
        for role, column in variant_columns.items():
            foreign_keys = connection.execute(
                f"PRAGMA foreign_key_list({physical_table(model, role)})"
            ).fetchall()
            grouped = {}
            for row in foreign_keys:
                grouped.setdefault(row["id"], []).append(row)
            assert any(
                {(row["from"], row["to"]) for row in rows}
                == {("model_key", "model_key"), (column, "variant_id")}
                and {row["table"] for row in rows} == {"model_variants"}
                for rows in grouped.values()
            ), (model, role, column)


def test_interior_scope_uniqueness_treats_null_as_unrestricted(connection):
    db.create_canonical_schema(connection)
    connection.execute(
        "INSERT INTO models(model_key, registry_key, model_label, active) "
        "VALUES('stingray', 'stingray', 'Stingray', 1)"
    )
    connection.execute("INSERT INTO trim_levels VALUES('1lt')")
    connection.execute(
        "INSERT INTO sections(section_id, section_name) VALUES('sec_x', 'Test')"
    )
    connection.execute(
        "INSERT INTO stingray_interiors("
        "model_key, interior_id, interior_name, price, section_id, active"
        ") VALUES('stingray', 'int_x', 'Test', 0, 'sec_x', 1)"
    )
    connection.execute(
        "INSERT INTO stingray_interior_scope("
        "model_key, interior_id, active"
        ") VALUES('stingray', 'int_x', 1)"
    )
    with pytest.raises(sqlite3.IntegrityError, match="UNIQUE constraint failed"):
        connection.execute(
            "INSERT INTO stingray_interior_scope("
            "model_key, interior_id, active"
            ") VALUES('stingray', 'int_x', 1)"
        )
    connection.execute(
        "INSERT INTO stingray_interior_scope("
        "model_key, interior_id, trim_level, active"
        ") VALUES('stingray', 'int_x', '1lt', 1)"
    )
    assert connection.execute(
        "SELECT COUNT(*) FROM stingray_interior_scope"
    ).fetchone()[0] == 2
    index_sql = connection.execute(
        "SELECT sql FROM sqlite_master WHERE type='index' AND name=?",
        ("stingray_interior_scope_null_safe_scope_unique",),
    ).fetchone()["sql"]
    assert index_sql.startswith(
        'CREATE UNIQUE INDEX "stingray_interior_scope_null_safe_scope_unique" '
        'ON "stingray_interior_scope"'
    )


def test_allowlisted_physical_identifiers_are_quoted_in_ddl(connection):
    db.create_canonical_schema(connection)
    physical_tables = {
        physical_table(model, role)
        for model in LIVE_MODELS
        for role in MODEL_TABLE_ROLES
    }
    for table in physical_tables:
        sql = connection.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name=?",
            (table,),
        ).fetchone()["sql"]
        assert sql.startswith(f'CREATE TABLE "{table}"')
        for referenced in physical_tables:
            assert f"REFERENCES {referenced}" not in sql


def _composite_foreign_keys(connection, table):
    grouped = {}
    for row in connection.execute(f"PRAGMA foreign_key_list({table})"):
        grouped.setdefault(row["id"], []).append(row)
    return [
        (
            {row["table"] for row in rows},
            {(row["from"], row["to"]) for row in rows},
        )
        for rows in grouped.values()
    ]


def test_runtime_route_consumers_share_model_scoped_foreign_key(connection):
    db.create_canonical_schema(connection)
    for table, route_column in (
        ("runtime_steps", "step_key"),
        ("runtime_context_sections", "step_key"),
        ("runtime_step_summary_map", "step_key"),
    ):
        assert (
            {"runtime_route_keys"},
            {("model_key", "model_key"), (route_column, "route_key")},
        ) in _composite_foreign_keys(connection, table)


def test_runtime_summary_map_rejects_unknown_model_route(connection):
    db.create_canonical_schema(connection)
    connection.execute(
        "INSERT INTO models(model_key, registry_key, model_label, active) "
        "VALUES('z06', 'z06', 'Z06', 1)"
    )
    connection.execute(
        "INSERT INTO runtime_summary_sections("
        "model_key, section_key, section_label, display_order, active"
        ") VALUES('z06', 'required_charges', 'Required Charges', 1, 1)"
    )
    with pytest.raises(sqlite3.IntegrityError, match="FOREIGN KEY constraint failed"):
        connection.execute(
            "INSERT INTO runtime_step_summary_map("
            "model_key, step_key, section_key, active"
            ") VALUES('z06', 'unknown_route', 'required_charges', 1)"
        )


def test_runtime_summary_map_allows_only_one_destination_per_route(connection):
    db.create_canonical_schema(connection)
    connection.execute(
        "INSERT INTO models(model_key, registry_key, model_label, active) "
        "VALUES('z06', 'z06', 'Z06', 1)"
    )
    connection.execute(
        "INSERT INTO runtime_route_keys(model_key, route_key, route_kind) "
        "VALUES('z06', 'standard_equipment', 'hidden_summary_bucket')"
    )
    connection.executemany(
        "INSERT INTO runtime_summary_sections("
        "model_key, section_key, section_label, display_order, active"
        ") VALUES('z06', ?, ?, ?, 1)",
        (
            ("required_charges", "Required Charges", 1),
            ("pricing_summary", "Pricing Summary", 2),
        ),
    )
    connection.execute(
        "INSERT INTO runtime_step_summary_map("
        "model_key, step_key, section_key, active"
        ") VALUES('z06', 'standard_equipment', 'required_charges', 1)"
    )
    with pytest.raises(sqlite3.IntegrityError, match="UNIQUE constraint failed"):
        connection.execute(
            "INSERT INTO runtime_step_summary_map("
            "model_key, step_key, section_key, active"
            ") VALUES('z06', 'standard_equipment', 'pricing_summary', 1)"
        )


def test_price_ref_null_scope_has_null_safe_identity(connection):
    db.create_canonical_schema(connection)
    connection.execute(
        "INSERT INTO price_ref(option_type, trim_level, code, price) "
        "VALUES('stitching', NULL, '36S', 495)"
    )
    with pytest.raises(sqlite3.IntegrityError, match="UNIQUE constraint failed"):
        connection.execute(
            "INSERT INTO price_ref(option_type, trim_level, code, price) "
            "VALUES('stitching', NULL, '36S', 595)"
        )
    connection.execute(
        "INSERT INTO price_ref(option_type, trim_level, code, price) "
        "VALUES('stitching', '1lt', '36S', 595)"
    )
    assert connection.execute("SELECT COUNT(*) FROM price_ref").fetchone()[0] == 2
    info = connection.execute("PRAGMA table_info(price_ref)").fetchall()
    assert [row["name"] for row in info if row["pk"]] == ["price_ref_id"]


@pytest.mark.parametrize(
    "option_type, trim_level, code",
    (
        ("", None, "36S"),
        ("stitching", "", "36S"),
        ("stitching", "<unrestricted>", "36S"),
        ("stitching", None, ""),
    ),
)
def test_price_ref_rejects_empty_or_sentinel_identity_parts(
    connection, option_type, trim_level, code
):
    db.create_canonical_schema(connection)
    with pytest.raises(sqlite3.IntegrityError, match="CHECK constraint failed"):
        connection.execute(
            "INSERT INTO price_ref(option_type, trim_level, code, price) "
            "VALUES(?, ?, ?, 495)",
            (option_type, trim_level, code),
        )
