from __future__ import annotations

import hashlib
import json
import os
import shutil
import sqlite3

import pytest

from app import staging, sync, validation
from app.catalog import LIVE_MODELS, MODEL_TABLE_ROLES, edit_spec, physical_table
from app.staging import StagingError


def valid_option_record(conn) -> dict[str, object]:
    section_id = conn.execute(
        "SELECT section_id FROM sections ORDER BY section_id LIMIT 1"
    ).fetchone()["section_id"]
    return {
        "option_id": "opt_test_901",
        "rpo": "T901",
        "price": 0,
        "option_name": "Migration Test Option",
        "description": "",
        "detail_raw": "",
        "section_id": section_id,
        "selectable": 1,
        "display_order": 9999,
        "active": 1,
        "display_behavior": None,
    }


def commit_added_option_change(conn) -> None:
    staging.stage_change(
        conn,
        model_key="stingray",
        table_role="options",
        op="add",
        key={"option_id": "opt_test_901"},
        record=valid_option_record(conn),
    )
    result = staging.commit_staged(conn, actor="test")
    assert result["status"] == "committed"


def test_catalog_edit_metadata_is_physical_and_role_keyed(imported_db):
    spec = edit_spec(imported_db, "stingray", "options")
    assert spec.sql_table == "stingray_options"
    assert spec.key == ("option_id",)
    assert spec.types["price"] == "integer"
    assert spec.enums["display_behavior"] == (
        None,
        "default_selected",
        "hidden",
        "display_only",
        "auto_only",
    )


def test_staged_option_uses_model_physical_table(imported_db):
    change = staging.stage_change(
        imported_db,
        model_key="stingray",
        table_role="options",
        op="add",
        key={"option_id": "opt_test_901"},
        record=valid_option_record(imported_db),
    )
    assert change["sql_table"] == "stingray_options"
    assert change["model_key"] == "stingray"
    assert change["table_role"] == "options"


def test_cross_model_record_is_rejected(imported_db):
    record = valid_option_record(imported_db)
    record["model_key"] = "z06"
    with pytest.raises(StagingError) as caught:
        staging.stage_change(
            imported_db,
            model_key="stingray",
            table_role="options",
            op="add",
            key={"option_id": record["option_id"]},
            record=record,
        )
    assert "model_key" in {error["field"] for error in caught.value.errors}


def test_type_enum_and_fk_errors_are_field_specific(imported_db):
    record = valid_option_record(imported_db)
    record.update(
        price="not-an-integer",
        display_behavior="invented",
        section_id="sec_missing",
    )
    errors = validation.validate_record(
        imported_db,
        "stingray",
        "options",
        record,
        op="add",
        original_key=None,
    )
    assert {error["field"] for error in errors} >= {
        "price",
        "display_behavior",
        "section_id",
    }


def test_missing_required_and_polymorphic_pair_are_rejected(imported_db):
    option = valid_option_record(imported_db)
    del option["option_name"]
    errors = validation.validate_record(
        imported_db, "stingray", "options", option, op="add"
    )
    assert "option_name" in {error["field"] for error in errors}

    rule_table = physical_table("stingray", "rule_mapping")
    rule = dict(imported_db.execute(
        f"SELECT * FROM {rule_table} WHERE source_option_id IS NOT NULL LIMIT 1"
    ).fetchone())
    rule["rule_id"] = "rule_test_invalid_pair"
    rule["source_interior_id"] = imported_db.execute(
        "SELECT interior_id FROM stingray_interiors LIMIT 1"
    ).fetchone()[0]
    errors = validation.validate_record(
        imported_db, "stingray", "rule_mapping", rule, op="add"
    )
    assert any("exactly one" in error["message"] for error in errors)


def test_update_key_is_immutable(imported_db):
    table = physical_table("stingray", "options")
    row = dict(imported_db.execute(f"SELECT * FROM {table} LIMIT 1").fetchone())
    original = {"option_id": row["option_id"]}
    row["option_id"] = "opt_renamed_901"
    errors = validation.validate_record(
        imported_db, "stingray", "options", row, op="update",
        original_key=original,
    )
    assert any("cannot change" in error["message"] for error in errors)


def test_delete_finds_all_option_dependents(imported_db):
    prefix = physical_table("stingray", "options").removesuffix("_options")
    row = imported_db.execute(
        f"SELECT a.option_id FROM {prefix}_option_availability a "
        f"JOIN {prefix}_exclusive_group_members e "
        "ON e.option_id=a.option_id ORDER BY a.option_id LIMIT 1"
    ).fetchone()
    assert row is not None
    dependents = validation.find_dependents(
        imported_db, "stingray", "options", {"option_id": row["option_id"]}
    )
    assert {item["table_role"] for item in dependents} >= {
        "option_availability",
        "exclusive_group_members",
    }
    assert all(item["model_key"] == "stingray" for item in dependents)


def test_commit_is_atomic_and_history_is_append_only(imported_db):
    commit_added_option_change(imported_db)
    table = physical_table("stingray", "options")
    assert imported_db.execute(
        f"SELECT 1 FROM {table} WHERE option_id='opt_test_901'"
    ).fetchone()
    history = imported_db.execute(
        "SELECT * FROM change_history ORDER BY id"
    ).fetchall()
    assert len(history) == 1
    assert history[0]["sql_table"] == table
    assert history[0]["table_role"] == "options"
    assert history[0]["status"] == "committed"
    with pytest.raises(sqlite3.IntegrityError, match="append-only"):
        imported_db.execute("UPDATE change_history SET actor='tampered'")


def test_sync_batch_restores_workbook_field_names(imported_db, real_workbook):
    commit_added_option_change(imported_db)
    batch = sync.build_batch(imported_db, real_workbook)
    assert batch["items"][0]["sheet"] == "stingray_options"
    assert batch["items"][0]["key"] == {"option_id": "opt_test_901"}
    assert batch["items"][0]["row"]["option_id"] == "opt_test_901"
    assert "model_key" not in batch["items"][0]["row"]


def test_polymorphic_rule_mapping_reverses_to_one_source_field(
    imported_db, real_workbook
):
    table = physical_table("stingray", "rule_mapping")
    row = dict(imported_db.execute(
        f"SELECT * FROM {table} WHERE source_option_id IS NOT NULL LIMIT 1"
    ).fetchone())
    key = {"rule_id": row["rule_id"]}
    row["original_detail_raw"] += " task8"
    staging.stage_change(
        imported_db, model_key="stingray", table_role="rule_mapping",
        op="update", key=key, record=row,
    )
    assert staging.commit_staged(imported_db)["ok"]
    item = sync.build_batch(imported_db, real_workbook)["items"][0]
    assert item["row"]["source_id"]
    assert "source_option_id" not in item["row"]
    assert "source_interior_id" not in item["row"]


def test_every_populated_role_builds_a_mapping_backed_update_batch(
    imported_db, real_workbook
):
    from corvette_form_generator import editor_ops

    items = []
    covered = set()
    for role in MODEL_TABLE_ROLES:
        for model_key in LIVE_MODELS:
            connection = sqlite3.connect(":memory:")
            connection.row_factory = sqlite3.Row
            imported_db.backup(connection)
            connection.execute("PRAGMA foreign_keys=ON")
            spec = edit_spec(connection, model_key, role)
            lineage = connection.execute(
                "SELECT l.primary_key_json FROM import_lineage l "
                "JOIN source_row_disposition d "
                "ON d.source_sheet=l.source_sheet AND d.source_row=l.source_row "
                "WHERE l.sql_table=? "
                "AND json_array_length(d.destinations_json)=1 LIMIT 1",
                (spec.sql_table,),
            ).fetchone()
            if lineage is None:
                connection.close()
                continue
            key = json.loads(lineage["primary_key_json"])
            where = " AND ".join(f'"{column}" IS ?' for column in spec.key)
            record = dict(connection.execute(
                f'SELECT * FROM "{spec.sql_table}" WHERE {where}',
                [key.get(column) for column in spec.key],
            ).fetchone())
            staging.stage_change(
                connection, model_key=model_key, table_role=role,
                op="update", key=key, record=record,
            )
            assert staging.commit_staged(connection)["ok"]
            batch = sync.build_batch(connection, real_workbook)
            assert batch["skipped"] == []
            assert len(batch["items"]) == 1
            items.extend(batch["items"])
            covered.add(role)
            connection.close()
            break
        if role not in covered:
            assert role == "runtime_rule_exceptions"
            assert staging.target_sheet_for(
                imported_db, "stingray", role
            ) == "runtime_rule_exceptions"
    assert covered == set(MODEL_TABLE_ROLES) - {"runtime_rule_exceptions"}
    extract = editor_ops.extract_workbook(real_workbook)
    errors, _warnings, prepared = editor_ops._prepare_batch(
        extract, {"items": items}
    )
    assert errors == []
    assert len(prepared) == len(items)


def test_shared_fanout_row_is_not_editable_per_model(imported_db):
    row = imported_db.execute(
        "SELECT l.sql_table, l.primary_key_json FROM import_lineage l "
        "JOIN source_row_disposition d "
        "ON d.source_sheet=l.source_sheet AND d.source_row=l.source_row "
        "WHERE l.sql_table='stingray_interiors' "
        "AND json_array_length(d.destinations_json)>1 LIMIT 1"
    ).fetchone()
    assert row is not None
    key = json.loads(row["primary_key_json"])
    record = dict(imported_db.execute(
        "SELECT * FROM stingray_interiors WHERE interior_id=?",
        (key["interior_id"],),
    ).fetchone())
    record["interior_name"] += " unsafe divergence"
    with pytest.raises(StagingError, match="validation failed") as caught:
        staging.stage_change(
            imported_db, model_key="stingray", table_role="interiors",
            op="update", key=key, record=record,
        )
    assert "fans out" in caught.value.errors[0]["message"]


def test_dry_run_always_calls_guarded_editor_path(
    imported_db, real_workbook, monkeypatch
):
    commit_added_option_change(imported_db)
    calls = []

    def fake_apply(path, batch, **kwargs):
        calls.append((path, batch, kwargs))
        return {"ok": True, "status": "validated"}

    monkeypatch.setattr(sync.editor_ops, "apply_batch", fake_apply)
    before = imported_db.execute(
        "SELECT COUNT(*) FROM change_history"
    ).fetchone()[0]
    result = sync.sync_workbook(imported_db, real_workbook, write=False)
    after = imported_db.execute(
        "SELECT COUNT(*) FROM change_history"
    ).fetchone()[0]
    assert result["status"] == "validated"
    assert calls[0][2]["write"] is False
    assert before == after


@pytest.mark.skipif(
    os.environ.get("WBM_SLOW_GATE") != "1", reason="set WBM_SLOW_GATE=1"
)
def test_scratch_copy_dry_and_live_sync_preserve_real_workbook(
    imported_db, real_workbook, tmp_path, monkeypatch
):
    before_hash = hashlib.sha256(real_workbook.read_bytes()).hexdigest()
    scratch = tmp_path / "scratch.xlsx"
    shutil.copy2(real_workbook, scratch)
    row = dict(imported_db.execute(
        "SELECT * FROM stingray_options WHERE rpo='Z51'"
    ).fetchone())
    key = {"option_id": row["option_id"]}
    row["price"] += 1
    staging.stage_change(
        imported_db, model_key="stingray", table_role="options",
        op="update", key=key, record=row,
    )
    assert staging.commit_staged(imported_db)["ok"]
    monkeypatch.setattr(sync.config, "EDIT_LOG_PATH", tmp_path / "edit-log.jsonl")

    dry = sync.sync_workbook(imported_db, scratch, write=False)
    assert dry["status"] == "validated"
    live = sync.sync_workbook(
        imported_db,
        scratch,
        write=True,
        expected_mtime_ns=dry["workbookMtimeNs"],
    )
    assert live["status"] == "applied"
    assert live["backupPath"]
    assert hashlib.sha256(real_workbook.read_bytes()).hexdigest() == before_hash
    events = imported_db.execute(
        "SELECT status FROM change_history ORDER BY id"
    ).fetchall()
    assert [row["status"] for row in events] == ["committed", "sync_succeeded"]
