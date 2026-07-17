import pytest

from app import db, importer
from app.catalog import MODEL_TABLE_ROLES


def primary_key(conn, table_name: str) -> tuple[str, ...]:
    return tuple(
        row["name"]
        for row in conn.execute(f"PRAGMA table_info({table_name})")
        if row["pk"]
    )


def table_roles(conn, model_key: str) -> tuple[str, ...]:
    return tuple(
        row["table_role"]
        for row in conn.execute(
            "SELECT table_role FROM model_table_registry "
            "WHERE model_key=? AND active=1 ORDER BY table_role",
            (model_key,),
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
    assert report.live_models == ("stingray", "grand_sport", "z06")
    assert report.decision_required == ()
    assert report.contract_differences == ()
    assert conn.execute("PRAGMA foreign_key_check").fetchall() == []
    for model in report.live_models:
        assert primary_key(conn, f"{model}_options") == ("option_id",)
        assert table_roles(conn, model) == tuple(sorted(MODEL_TABLE_ROLES))
    assert not table_exists(conn, "options")
