import json

import pytest

from app import db, importer


APPROVED_LIVE_MODELS = ("stingray", "grand_sport", "z06")
APPROVED_MODEL_TABLE_ROLES = frozenset(
    {
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
    }
)


def test_approved_completion_contract_has_17_literal_roles():
    assert len(APPROVED_MODEL_TABLE_ROLES) == 17


def primary_key(conn, table_name: str) -> tuple[str, ...]:
    return tuple(
        row["name"]
        for row in conn.execute(f"PRAGMA table_info({table_name})")
        if row["pk"]
    )


def active_model_keys(conn) -> tuple[str, ...]:
    return tuple(
        row["model_key"]
        for row in conn.execute(
            "SELECT model_key FROM models WHERE active=1 ORDER BY model_key"
        )
    )


def table_exists(conn, table_name: str) -> bool:
    return (
        conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
            (table_name,),
        ).fetchone()
        is not None
    )


@pytest.fixture
def audited_database(tmp_path, real_workbook):
    database_path = tmp_path / "audited.sqlite3"
    report = importer.import_workbook(database_path, real_workbook)
    conn = db.connect(database_path)
    try:
        yield conn, report
    finally:
        conn.close()


def test_objective_completion(audited_database):
    conn, report = audited_database
    assert report.status == "validated"
    assert report.live_models == APPROVED_LIVE_MODELS
    assert report.decision_required == ()
    assert report.contract_differences == ()
    assert conn.execute("PRAGMA foreign_key_check").fetchall() == []

    active_models = active_model_keys(conn)
    assert len(active_models) == 3
    assert set(active_models) == set(APPROVED_LIVE_MODELS)
    registry_models = {
        row["model_key"]
        for row in conn.execute(
            "SELECT DISTINCT model_key FROM model_table_registry "
            "WHERE active=1"
        )
    }
    assert registry_models == set(APPROVED_LIVE_MODELS)

    for model in APPROVED_LIVE_MODELS:
        registry_rows = conn.execute(
            "SELECT model_key, table_role, sql_table "
            "FROM model_table_registry "
            "WHERE model_key=? AND active=1 ORDER BY table_role",
            (model,),
        ).fetchall()
        assert len(registry_rows) == 17
        assert {
            row["table_role"] for row in registry_rows
        } == APPROVED_MODEL_TABLE_ROLES
        assert all(row["model_key"] == model for row in registry_rows)
        assert all(
            row["sql_table"] == f"{model}_{row['table_role']}"
            for row in registry_rows
        )
        assert primary_key(conn, f"{model}_options") == ("option_id",)
    assert not table_exists(conn, "options")

    mapping_statuses = {
        row["contract_status"]
        for row in conn.execute("SELECT contract_status FROM schema_mapping")
    }
    assert mapping_statuses == {
        "exact",
        "identifier_normalized",
        "shared_source_split",
        "semantic_alias",
        "derived_from_contract",
    }
    assert {
        row["source_role"]
        for row in conn.execute(
            "SELECT source_role FROM schema_mapping "
            "WHERE source_sheet='grandSport_options'"
        )
    } == {"source_option_sheet"}
    assert all(
        json.loads(row["source_sheets_json"]) == ["runtime_rule_exceptions"]
        for row in conn.execute(
            "SELECT source_sheets_json FROM model_table_registry "
            "WHERE table_role='runtime_rule_exceptions'"
        )
    )
