import hashlib
import os
import sqlite3
from dataclasses import replace

from app import db, importer
from app.catalog import LIVE_MODELS, MODEL_TABLE_ROLES
from app.compile_types import freeze_mapping


def _digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_failed_candidate_does_not_replace_verified_database(
    tmp_path, broken_fk_workbook
):
    destination = tmp_path / "workbook.sqlite3"
    conn = db.connect(destination)
    db.create_canonical_schema(conn)
    db.set_meta(conn, "verification_marker", "keep")
    conn.commit()
    conn.close()
    before = _digest(destination)

    report = importer.import_workbook(
        destination, broken_fk_workbook, audit_contracts=False
    )

    assert report.status == "decision_required"
    assert _digest(destination) == before
    assert not list(tmp_path.glob("*.candidate*"))


def test_successful_candidate_has_complete_lineage(tmp_path, real_workbook):
    destination = tmp_path / "workbook.sqlite3"

    report = importer.import_workbook(
        destination, real_workbook, audit_contracts=False
    )

    assert report.status == "validated"
    assert report.live_models == LIVE_MODELS
    assert report.promoted_path == destination
    conn = db.connect(destination)
    try:
        assert conn.execute("PRAGMA foreign_key_check").fetchall() == []
        assert conn.execute("SELECT COUNT(*) FROM import_lineage").fetchone()[0] == 8922
        assert conn.execute("SELECT COUNT(*) FROM source_table_catalog").fetchone()[0] == 65
        assert conn.execute("SELECT COUNT(*) FROM import_issues").fetchone()[0] == 444
        assert conn.execute("SELECT COUNT(*) FROM model_table_registry").fetchone()[0] == 51
        assert conn.execute("SELECT COUNT(*) FROM schema_mapping").fetchone()[0] == 601
        assert conn.execute(
            "SELECT COUNT(DISTINCT sql_table) FROM schema_mapping"
        ).fetchone()[0] == 68
        run = conn.execute("SELECT * FROM import_runs").fetchone()
        assert run["workbook_path"] == str(real_workbook)
        assert run["workbook_sha256"] == _digest(real_workbook)
        assert run["status"] == "validated"
    finally:
        conn.close()


def test_legacy_pending_changes_block_replacement(legacy_db_path, real_workbook):
    conn = sqlite3.connect(legacy_db_path)
    conn.execute(
        "INSERT INTO pending_changes("
        "ts, session_id, table_name, model_id, entity_key_json, op, old_json, "
        "new_json, status, validation_json, confirmed_dependencies"
        ") VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            "2026-07-16T12:00:00+00:00",
            "migration-test",
            "options",
            "stingray",
            '{"option_id":"opt_pending"}',
            "add",
            None,
            '{"option_id":"opt_pending"}',
            "staged",
            "{}",
            0,
        ),
    )
    conn.commit()
    conn.close()
    before = _digest(legacy_db_path)

    report = importer.import_workbook(
        legacy_db_path, real_workbook, audit_contracts=False
    )

    assert report.status == "decision_required"
    assert report.finding_codes == ("legacy_pending_changes",)
    assert _digest(legacy_db_path) == before


def test_legacy_unsynced_history_blocks_replacement(tmp_path, real_workbook):
    destination = tmp_path / "legacy-history.sqlite3"
    conn = sqlite3.connect(destination)
    conn.execute(
        "CREATE TABLE change_history ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT NOT NULL, "
        "actor TEXT NOT NULL DEFAULT '', entity_type TEXT NOT NULL, "
        "entity_id TEXT NOT NULL, model_id TEXT NOT NULL DEFAULT '', "
        "op TEXT NOT NULL, old_json TEXT, new_json TEXT, "
        "src_sheet TEXT NOT NULL DEFAULT '', src_row INTEGER, "
        "validation_result TEXT NOT NULL DEFAULT '', status TEXT NOT NULL, "
        "sync_status TEXT NOT NULL DEFAULT 'pending', "
        "sync_detail TEXT NOT NULL DEFAULT '', pending_change_id INTEGER)"
    )
    conn.execute(
        "INSERT INTO change_history(ts, entity_type, entity_id, op, status) "
        "VALUES('2026-07-16T12:00:00+00:00', 'options', 'opt_pending', "
        "'add', 'committed')"
    )
    conn.commit()
    conn.close()
    before = _digest(destination)

    report = importer.import_workbook(
        destination, real_workbook, audit_contracts=False
    )

    assert report.status == "decision_required"
    assert report.finding_codes == ("legacy_unsynced_change_history",)
    assert _digest(destination) == before


def test_compiler_returns_complete_canonical_contract(real_workbook):
    compiled = importer.compile_workbook(real_workbook)

    assert len(compiled.tables) == 68
    assert sum(len(table.rows) for table in compiled.tables) == 8922
    assert len(compiled.source_catalog) == 65
    assert len(compiled.lineage) == 8922
    assert len([finding for finding in compiled.findings if finding.status == "mapped"]) == 444
    assert {
        (table.model_key, table.role)
        for table in compiled.tables
        if table.model_key
    } == {
        (model, role) for model in LIVE_MODELS for role in MODEL_TABLE_ROLES
    }


def test_structurally_failed_candidate_is_removed_and_destination_is_stable(
    tmp_path, real_workbook, monkeypatch
):
    destination = tmp_path / "verified.sqlite3"
    conn = db.connect(destination)
    db.create_canonical_schema(conn)
    db.set_meta(conn, "verification_marker", "keep")
    conn.commit()
    conn.close()
    before = _digest(destination)

    compiled = importer.compile_workbook(real_workbook)
    tables = list(compiled.tables)
    table_index = next(
        index
        for index, table in enumerate(tables)
        if table.name == "stingray_option_availability"
    )
    table = tables[table_index]
    rows = list(table.rows)
    values = dict(rows[0].values)
    values["option_id"] = "opt_missing_candidate_fk"
    rows[0] = replace(rows[0], values=freeze_mapping(values))
    tables[table_index] = replace(table, rows=tuple(rows))
    broken = replace(compiled, tables=tuple(tables))
    monkeypatch.setattr(importer, "compile_workbook", lambda _: broken)

    report = importer.import_workbook(
        destination, real_workbook, audit_contracts=False
    )

    assert report.status == "contract_mismatch"
    assert report.finding_codes == ("candidate_build_or_promotion_failed",)
    assert _digest(destination) == before
    assert not list(tmp_path.glob(".*.candidate-*"))
    assert not list(tmp_path.glob("*.backup-*"))


def test_existing_destination_is_backed_up_before_atomic_replacement(
    tmp_path, real_workbook
):
    destination = tmp_path / "verified.sqlite3"
    conn = db.connect(destination)
    db.create_canonical_schema(conn)
    db.set_meta(conn, "verification_marker", "backup-proof")
    conn.commit()
    conn.close()

    report = importer.import_workbook(
        destination, real_workbook, audit_contracts=False
    )

    assert report.status == "validated"
    backups = list(tmp_path.glob("verified.sqlite3.backup-*"))
    assert len(backups) == 1
    backup = db.connect(backups[0])
    try:
        assert db.get_meta(backup, "verification_marker") == "backup-proof"
        assert backup.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
    finally:
        backup.close()


def test_contract_audit_bypass_is_unavailable_to_normal_callers(
    tmp_path, real_workbook, monkeypatch
):
    monkeypatch.delenv("PYTEST_CURRENT_TEST")

    report = importer.import_workbook(
        tmp_path / "workbook.sqlite3", real_workbook, audit_contracts=False
    )

    assert report.status == "contract_mismatch"
    assert report.finding_codes == ("contract_audit_test_bypass_rejected",)
    assert not (tmp_path / "workbook.sqlite3").exists()


def test_destination_sidecars_block_before_candidate_build(
    tmp_path, real_workbook
):
    destination = tmp_path / "verified.sqlite3"
    conn = db.connect(destination)
    db.create_canonical_schema(conn)
    db.set_meta(conn, "verification_marker", "keep")
    conn.commit()
    conn.close()
    before = _digest(destination)
    wal = tmp_path / "verified.sqlite3-wal"
    wal.write_bytes(b"active-or-stale-wal-must-not-be-guessed")

    report = importer.import_workbook(
        destination, real_workbook, audit_contracts=False
    )

    assert report.status == "decision_required"
    assert report.finding_codes == ("legacy_destination_sidecars",)
    assert _digest(destination) == before
    assert wal.read_bytes() == b"active-or-stale-wal-must-not-be-guessed"
    assert not list(tmp_path.glob(".*.candidate-*"))


def test_post_replace_failure_restores_byte_identical_destination(
    tmp_path, real_workbook, monkeypatch
):
    destination = tmp_path / "verified.sqlite3"
    conn = db.connect(destination)
    db.create_canonical_schema(conn)
    db.set_meta(conn, "verification_marker", "keep")
    conn.commit()
    conn.close()
    before = _digest(destination)
    real_replace = os.replace

    def replace_then_fail(source, target):
        real_replace(source, target)
        if ".candidate-" in str(source):
            raise OSError("injected failure after candidate replacement")

    monkeypatch.setattr("app.migration.os.replace", replace_then_fail)

    report = importer.import_workbook(
        destination, real_workbook, audit_contracts=False
    )

    assert report.status == "contract_mismatch"
    assert _digest(destination) == before
    assert not list(tmp_path.glob(".*.candidate-*"))
    assert not list(tmp_path.glob(".*.rollback-*"))
