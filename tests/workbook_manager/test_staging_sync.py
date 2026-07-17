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
    assert result["status"] == "committed", result


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


def test_partial_update_merges_current_row_and_rejects_blank_required(imported_db):
    row = imported_db.execute(
        "SELECT option_id, detail_raw FROM stingray_options LIMIT 1"
    ).fetchone()
    key = {"option_id": row["option_id"]}
    change = staging.stage_change(
        imported_db, model_key="stingray", table_role="options", op="update",
        key=key, record={"detail_raw": row["detail_raw"] + " task8 patch"},
    )
    assert change["new"]["option_name"]
    assert change["new"]["detail_raw"].endswith("task8 patch")
    staging.discard_change(imported_db, change["id"])

    with pytest.raises(StagingError) as caught:
        staging.stage_change(
            imported_db, model_key="stingray", table_role="options",
            op="update", key=key, record={"option_name": ""},
        )
    assert "option_name" in {error["field"] for error in caught.value.errors}


def test_key_only_update_is_rejected_and_sqlite_error_rolls_back(
    imported_db, monkeypatch
):
    row = imported_db.execute(
        "SELECT option_id FROM stingray_options LIMIT 1"
    ).fetchone()
    key = {"option_id": row["option_id"]}
    with pytest.raises(StagingError, match="validation failed"):
        staging.stage_change(
            imported_db, model_key="stingray", table_role="options",
            op="update", key=key, record={"option_id": row["option_id"]},
        )
    price = imported_db.execute(
        "SELECT price FROM stingray_options WHERE option_id=?",
        (row["option_id"],),
    ).fetchone()[0]
    with pytest.raises(StagingError, match="validation failed"):
        staging.stage_change(
            imported_db, model_key="stingray", table_role="options",
            op="update", key=key, record={"price": str(price)},
        )

    record = valid_option_record(imported_db)
    staging.stage_change(
        imported_db, model_key="stingray", table_role="options", op="add",
        key={"option_id": record["option_id"]}, record=record,
    )
    original = staging._apply_change

    def fail_with_sqlite_error(*args, **kwargs):
        raise sqlite3.OperationalError("injected sqlite failure")

    monkeypatch.setattr(staging, "_apply_change", fail_with_sqlite_error)
    result = staging.commit_staged(imported_db)
    monkeypatch.setattr(staging, "_apply_change", original)
    assert result["status"] == "constraint_failed"
    assert not imported_db.in_transaction
    assert imported_db.execute(
        "SELECT 1 FROM stingray_options WHERE option_id='opt_test_901'"
    ).fetchone() is None


def test_stale_update_conflict_preserves_external_value_and_batch_atomicity(
    imported_db, imported_db_path
):
    row = imported_db.execute(
        "SELECT option_id, price FROM stingray_options WHERE rpo='Z51'"
    ).fetchone()
    original_price = row["price"]
    staging.stage_change(
        imported_db,
        model_key="stingray",
        table_role="options",
        op="update",
        key={"option_id": row["option_id"]},
        record={"price": row["price"] + 1},
    )
    add_record = valid_option_record(imported_db)
    staging.stage_change(
        imported_db,
        model_key="stingray",
        table_role="options",
        op="add",
        key={"option_id": add_record["option_id"]},
        record=add_record,
    )

    external = sqlite3.connect(imported_db_path)
    external.execute(
        "UPDATE stingray_options SET price=? WHERE option_id=?",
        (99, row["option_id"]),
    )
    external.commit()
    external.close()
    history_before = imported_db.execute(
        "SELECT COUNT(*) FROM change_history"
    ).fetchone()[0]

    result = staging.commit_staged(imported_db, actor="race-test")

    assert result["status"] == "stale_conflict"
    assert result["committed"] == 0
    assert any(row["option_id"] in error for error in result["errors"])
    assert imported_db.execute(
        "SELECT price FROM stingray_options WHERE option_id=?",
        (row["option_id"],),
    ).fetchone()[0] == 99
    assert original_price != 99
    assert imported_db.execute(
        "SELECT 1 FROM stingray_options WHERE option_id='opt_test_901'"
    ).fetchone() is None
    assert imported_db.execute(
        "SELECT COUNT(*) FROM change_history"
    ).fetchone()[0] == history_before
    assert imported_db.execute(
        "SELECT COUNT(*) FROM pending_changes WHERE status='staged'"
    ).fetchone()[0] == 2
    assert not imported_db.in_transaction


def test_stale_delete_conflict_preserves_changed_row_and_history(
    imported_db, imported_db_path
):
    commit_added_option_change(imported_db)
    staging.stage_change(
        imported_db,
        model_key="stingray",
        table_role="options",
        op="delete",
        key={"option_id": "opt_test_901"},
        record=None,
    )
    history_before = imported_db.execute(
        "SELECT COUNT(*) FROM change_history"
    ).fetchone()[0]
    external = sqlite3.connect(imported_db_path)
    external.execute(
        "UPDATE stingray_options SET price=99 WHERE option_id='opt_test_901'"
    )
    external.commit()
    external.close()

    result = staging.commit_staged(imported_db, actor="delete-race-test")

    assert result["status"] == "stale_conflict"
    assert result["committed"] == 0
    assert imported_db.execute(
        "SELECT price FROM stingray_options WHERE option_id='opt_test_901'"
    ).fetchone()[0] == 99
    assert imported_db.execute(
        "SELECT COUNT(*) FROM change_history"
    ).fetchone()[0] == history_before
    assert not imported_db.in_transaction


def test_equivalent_sqlite_and_json_types_do_not_create_false_stale_conflict(
    imported_db
):
    row = dict(imported_db.execute(
        "SELECT * FROM stingray_options WHERE rpo='Z51'"
    ).fetchone())
    change = staging.stage_change(
        imported_db,
        model_key="stingray",
        table_role="options",
        op="update",
        key={"option_id": row["option_id"]},
        record={"price": row["price"] + 1},
    )
    old = dict(change["old"])
    old["price"] = f"{old['price']:,}"
    old["selectable"] = "True" if old["selectable"] else "False"
    old["active"] = "True" if old["active"] else "False"
    if old["display_behavior"] is None:
        old["display_behavior"] = ""
    imported_db.execute(
        "UPDATE pending_changes SET old_json=? WHERE id=?",
        (json.dumps(old), change["id"]),
    )
    imported_db.commit()

    result = staging.commit_staged(imported_db, actor="normalization-test")

    assert result["status"] == "committed", result
    assert imported_db.execute(
        "SELECT price FROM stingray_options WHERE option_id=?",
        (row["option_id"],),
    ).fetchone()[0] == row["price"] + 1
    assert not imported_db.in_transaction


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


def test_confirmed_parent_delete_orders_complete_members_before_parent(imported_db):
    group = imported_db.execute(
        "SELECT group_id FROM stingray_exclusive_groups WHERE EXISTS ("
        "SELECT 1 FROM stingray_exclusive_group_members m "
        "WHERE m.group_id=stingray_exclusive_groups.group_id) LIMIT 1"
    ).fetchone()[0]
    members = imported_db.execute(
        "SELECT group_id, option_id FROM stingray_exclusive_group_members "
        "WHERE group_id=?", (group,),
    ).fetchall()
    staging.stage_change(
        imported_db, model_key="stingray", table_role="exclusive_groups",
        op="delete", key={"group_id": group}, record=None,
        confirm_dependencies=True,
    )
    for member in members:
        staging.stage_change(
            imported_db, model_key="stingray",
            table_role="exclusive_group_members", op="delete",
            key={"group_id": member["group_id"], "option_id": member["option_id"]},
            record=None,
        )
    result = staging.commit_staged(imported_db)
    assert result["status"] == "committed", result
    assert imported_db.execute(
        "SELECT 1 FROM stingray_exclusive_groups WHERE group_id=?", (group,)
    ).fetchone() is None


def test_committed_unsynced_add_can_be_corrected_and_collapses_to_one_add(
    imported_db, real_workbook
):
    from corvette_form_generator import editor_ops

    available_member = imported_db.execute(
        "SELECT g.group_id, o.option_id "
        "FROM stingray_exclusive_groups g CROSS JOIN stingray_options o "
        "WHERE NOT EXISTS (SELECT 1 FROM stingray_exclusive_group_members m "
        "WHERE m.group_id=g.group_id AND m.option_id=o.option_id) "
        "ORDER BY g.group_id, o.option_id LIMIT 1"
    ).fetchone()
    assert available_member is not None
    key = dict(available_member)
    record = {**key, "display_order": 9999, "active": 1}
    staging.stage_change(
        imported_db, model_key="stingray",
        table_role="exclusive_group_members", op="add",
        key=key, record=record,
    )
    assert staging.commit_staged(imported_db)["ok"]
    staging.stage_change(
        imported_db, model_key="stingray",
        table_role="exclusive_group_members", op="update",
        key=key, record={"display_order": 9998},
    )
    assert staging.commit_staged(imported_db)["ok"]

    batch = sync.build_batch(imported_db, real_workbook)
    assert batch["skipped"] == []
    assert len(batch["items"]) == 1
    assert batch["items"][0]["action"] == "add"
    assert batch["items"][0]["row"]["display_order"] == 9998
    assert len(batch["historyIds"]) == 2
    errors, _warnings, prepared = editor_ops._prepare_batch(
        editor_ops.extract_workbook(real_workbook), {"items": batch["items"]}
    )
    assert errors == []
    assert len(prepared) == 1


def test_react_boolean_and_numeric_strings_persist_as_canonical_values(imported_db):
    record = valid_option_record(imported_db)
    record.update(
        price="1,234", display_order="9999", selectable="True",
        active="False", display_behavior="",
    )
    change = staging.stage_change(
        imported_db, model_key="stingray", table_role="options", op="add",
        key={"option_id": record["option_id"]}, record=record,
    )
    assert change["new"]["price"] == 1234
    assert change["new"]["display_order"] == 9999
    assert change["new"]["selectable"] == 1
    assert change["new"]["active"] == 0
    assert change["new"]["display_behavior"] is None
    assert staging.commit_staged(imported_db)["ok"]

    stored = dict(imported_db.execute(
        "SELECT * FROM stingray_options WHERE option_id=?",
        (record["option_id"],),
    ).fetchone())
    history = json.loads(imported_db.execute(
        "SELECT new_json FROM change_history WHERE status='committed' "
        "AND table_role='options' ORDER BY id DESC LIMIT 1"
    ).fetchone()[0])
    assert history == stored
    assert history["price"] == 1234
    assert history["selectable"] == 1
    assert history["active"] == 0
    assert history["display_behavior"] is None

    staging.stage_change(
        imported_db, model_key="stingray", table_role="options", op="update",
        key={"option_id": record["option_id"]},
        record={"active": "True", "option_name": "Corrected string add"},
    )
    assert staging.commit_staged(imported_db)["ok"]
    assert imported_db.execute(
        "SELECT active FROM stingray_options WHERE option_id=?",
        (record["option_id"],),
    ).fetchone()[0] == 1

    with pytest.raises(StagingError) as caught:
        staging.stage_change(
            imported_db, model_key="stingray", table_role="options",
            op="update", key={"option_id": record["option_id"]},
            record={"active": "not-a-boolean"},
        )
    assert caught.value.errors[0]["field"] == "active"


def test_string_form_add_delete_collapses_to_noop(imported_db, real_workbook):
    record = valid_option_record(imported_db)
    record.update(price="0", display_order="9999", selectable="True", active="True")
    staging.stage_change(
        imported_db, model_key="stingray", table_role="options", op="add",
        key={"option_id": record["option_id"]}, record=record,
    )
    assert staging.commit_staged(imported_db)["ok"]
    staging.stage_change(
        imported_db, model_key="stingray", table_role="options", op="delete",
        key={"option_id": record["option_id"]}, record=None,
    )
    assert staging.commit_staged(imported_db)["ok"]
    batch = sync.build_batch(imported_db, real_workbook)
    assert batch["skipped"] == []
    assert batch["items"] == []
    assert len(batch["noopHistoryIds"]) == 2


def test_legacy_raw_add_history_normalizes_or_fails_closed(
    imported_db, real_workbook
):
    def rewrite_legacy_history(history_id, payload):
        imported_db.execute("DROP TRIGGER change_history_append_only_update")
        try:
            imported_db.execute(
                "UPDATE change_history SET new_json=? WHERE id=?",
                (json.dumps(payload), history_id),
            )
        finally:
            imported_db.execute(
                "CREATE TRIGGER change_history_append_only_update "
                "BEFORE UPDATE ON change_history BEGIN SELECT RAISE(ABORT, "
                "'change_history is append-only'); END"
            )

    record = valid_option_record(imported_db)
    staging.stage_change(
        imported_db, model_key="stingray", table_role="options", op="add",
        key={"option_id": record["option_id"]}, record=record,
    )
    assert staging.commit_staged(imported_db)["ok"]
    pending_id, history_id, raw = imported_db.execute(
        "SELECT p.id, h.id, h.new_json FROM pending_changes p "
        "JOIN change_history h ON h.pending_change_id=p.id "
        "WHERE h.status='committed' ORDER BY h.id DESC LIMIT 1"
    ).fetchone()
    raw = json.loads(raw)
    raw.update(price="0", display_order="9,999", selectable="True", active="True")
    raw_json = json.dumps(raw)
    imported_db.execute(
        "UPDATE pending_changes SET new_json=? WHERE id=?", (raw_json, pending_id)
    )
    rewrite_legacy_history(history_id, raw)
    imported_db.commit()

    staging.stage_change(
        imported_db, model_key="stingray", table_role="options", op="update",
        key={"option_id": record["option_id"]},
        record={"option_name": "Legacy raw recovered"},
    )
    assert staging.commit_staged(imported_db)["ok"]
    assert sync.build_batch(imported_db, real_workbook)["skipped"] == []

    first_history = imported_db.execute(
        "SELECT new_json FROM change_history WHERE id=?", (history_id,)
    ).fetchone()[0]
    invalid = json.loads(first_history)
    invalid["active"] = "not-a-boolean"
    rewrite_legacy_history(history_id, invalid)
    imported_db.commit()
    batch = sync.build_batch(imported_db, real_workbook)
    assert batch["items"] == []
    assert "active must be boolean" in batch["skipped"][0]["reason"]


def test_committed_unsynced_add_delete_collapses_to_guarded_noop(
    imported_db, real_workbook, monkeypatch
):
    record = valid_option_record(imported_db)
    staging.stage_change(
        imported_db, model_key="stingray", table_role="options", op="add",
        key={"option_id": record["option_id"]}, record=record,
    )
    assert staging.commit_staged(imported_db)["ok"]
    staging.stage_change(
        imported_db, model_key="stingray", table_role="options", op="delete",
        key={"option_id": record["option_id"]}, record=None,
    )
    assert staging.commit_staged(imported_db)["ok"]
    batch = sync.build_batch(imported_db, real_workbook)
    assert batch["items"] == []
    assert len(batch["noopHistoryIds"]) == 2

    monkeypatch.setattr(
        sync.editor_ops, "apply_batch",
        lambda *_args, **_kwargs: pytest.fail("net no-op must not invoke editor"),
    )
    dry = sync.sync_workbook(imported_db, real_workbook, write=False)
    assert dry["status"] == "validated"
    live = sync.sync_workbook(
        imported_db, real_workbook, write=True,
        expected_mtime_ns=dry["workbookMtimeNs"],
    )
    assert live["status"] == "applied_noop"
    assert sync.pending_history(imported_db) == []


def test_failed_add_dry_run_remains_correctable(
    imported_db, real_workbook, monkeypatch
):
    record = valid_option_record(imported_db)
    staging.stage_change(
        imported_db, model_key="stingray", table_role="options", op="add",
        key={"option_id": record["option_id"]}, record=record,
    )
    assert staging.commit_staged(imported_db)["ok"]
    monkeypatch.setattr(
        sync.editor_ops, "apply_batch",
        lambda *_args, **_kwargs: {
            "ok": False, "status": "invalid", "errors": ["injected dry failure"]
        },
    )
    assert not sync.sync_workbook(imported_db, real_workbook, write=False)["ok"]
    staging.stage_change(
        imported_db, model_key="stingray", table_role="options", op="update",
        key={"option_id": record["option_id"]},
        record={"option_name": "Recovered after dry failure"},
    )
    assert staging.commit_staged(imported_db)["ok"]
    assert sync.build_batch(imported_db, real_workbook)["items"][0]["action"] == "add"


def test_committed_add_recovery_requires_one_unique_target_sheet(
    imported_db, monkeypatch
):
    record = valid_option_record(imported_db)
    staging.stage_change(
        imported_db, model_key="stingray", table_role="options", op="add",
        key={"option_id": record["option_id"]}, record=record,
    )
    assert staging.commit_staged(imported_db)["ok"]
    monkeypatch.setattr(staging, "target_sheet_for", lambda *_args: None)
    with pytest.raises(StagingError) as caught:
        staging.stage_change(
            imported_db, model_key="stingray", table_role="options",
            op="update", key={"option_id": record["option_id"]},
            record={"option_name": "must remain blocked"},
        )
    assert "no exact import lineage" in caught.value.errors[0]["message"]


def test_incomplete_confirmed_parent_delete_fails_before_commit(imported_db):
    group = imported_db.execute(
        "SELECT group_id FROM stingray_exclusive_groups WHERE EXISTS ("
        "SELECT 1 FROM stingray_exclusive_group_members m "
        "WHERE m.group_id=stingray_exclusive_groups.group_id) LIMIT 1"
    ).fetchone()[0]
    staging.stage_change(
        imported_db, model_key="stingray", table_role="exclusive_groups",
        op="delete", key={"group_id": group}, record=None,
        confirm_dependencies=True,
    )
    result = staging.commit_staged(imported_db)
    assert result["status"] == "invalid"
    assert imported_db.execute(
        "SELECT 1 FROM stingray_exclusive_groups WHERE group_id=?", (group,)
    ).fetchone() is not None


def test_parent_add_is_ordered_before_staged_child_add(imported_db):
    parent = dict(imported_db.execute(
        "SELECT * FROM stingray_exclusive_groups LIMIT 1"
    ).fetchone())
    child = dict(imported_db.execute(
        "SELECT * FROM stingray_exclusive_group_members LIMIT 1"
    ).fetchone())
    parent["group_id"] = "exclusive_task8_901"
    child["group_id"] = parent["group_id"]
    parent_change = staging.stage_change(
        imported_db, model_key="stingray", table_role="exclusive_groups",
        op="add", key={"group_id": parent["group_id"]}, record=parent,
    )
    child_change = staging.stage_change(
        imported_db, model_key="stingray",
        table_role="exclusive_group_members", op="add",
        key={"group_id": child["group_id"], "option_id": child["option_id"]},
        record=child,
    )
    ordered = staging._ordered_changes(
        imported_db, [child_change, parent_change]
    )
    assert [change["id"] for change in ordered] == [
        parent_change["id"], child_change["id"],
    ]
    assert staging.commit_staged(imported_db)["status"] == "committed"


def test_child_fk_move_resolves_parent_dependency_and_orders_update_first(
    imported_db
):
    child = dict(imported_db.execute(
        "SELECT * FROM stingray_rule_mapping "
        "WHERE source_option_id IS NOT NULL LIMIT 1"
    ).fetchone())
    old_option = child["source_option_id"]
    replacement = imported_db.execute(
        "SELECT option_id FROM stingray_options WHERE option_id<>? LIMIT 1",
        (old_option,),
    ).fetchone()[0]
    parent_spec = edit_spec(imported_db, "stingray", "options")
    dependent = next(
        item for item in validation.find_dependents(
            imported_db, "stingray", "options", {"option_id": old_option}
        )
        if item["table_role"] == "rule_mapping"
        and item["key"]["rule_id"] == child["rule_id"]
        and "source_option_id" in item["field"]
    )
    child["source_option_id"] = replacement
    resolution = {
        "id": 2, "model_key": "stingray", "table_role": "rule_mapping",
        "sql_table": "stingray_rule_mapping", "op": "update",
        "entity_key": {"rule_id": child["rule_id"]},
        "old": dict(imported_db.execute(
            "SELECT * FROM stingray_rule_mapping WHERE rule_id=?",
            (child["rule_id"],),
        ).fetchone()),
        "new": child,
    }
    staged = {(
        "stingray", "rule_mapping",
        json.dumps(resolution["entity_key"], sort_keys=True),
    ): resolution}
    assert staging._dependent_is_resolved_by_staged_change(
        imported_db, parent_spec, {"option_id": old_option},
        dependent, staged,
    )
    parent_change = {
        "id": 1, "model_key": "stingray", "table_role": "options",
        "sql_table": "stingray_options", "op": "delete",
        "entity_key": {"option_id": old_option},
        "old": dict(imported_db.execute(
            "SELECT * FROM stingray_options WHERE option_id=?", (old_option,),
        ).fetchone()),
        "new": None,
    }
    assert [change["id"] for change in staging._ordered_changes(
        imported_db, [parent_change, resolution]
    )] == [resolution["id"], parent_change["id"]]


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


def test_multiple_pending_updates_preserve_earlier_source_values(
    imported_db, real_workbook
):
    row = dict(imported_db.execute(
        "SELECT * FROM stingray_options WHERE rpo='Z51'"
    ).fetchone())
    key = {"option_id": row["option_id"]}
    description = f"{row['description']} task8 retained".strip()
    staging.stage_change(
        imported_db, model_key="stingray", table_role="options", op="update",
        key=key, record={"description": description},
    )
    assert staging.commit_staged(imported_db)["ok"]
    staging.stage_change(
        imported_db, model_key="stingray", table_role="options", op="update",
        key=key, record={"price": row["price"] + 1},
    )
    assert staging.commit_staged(imported_db)["ok"]

    items = sync.build_batch(imported_db, real_workbook)["items"]
    assert len(items) == 2
    assert items[0]["row"]["description"] == description
    assert items[1]["row"]["description"] == description


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


def test_central_structure_edits_commit_and_build_canonical_batches(
    imported_db, real_workbook
):
    step = dict(imported_db.execute(
        "SELECT * FROM runtime_steps WHERE model_key='stingray' LIMIT 1"
    ).fetchone())
    presentation = dict(imported_db.execute(
        "SELECT * FROM section_presentation "
        "WHERE model_key='stingray' LIMIT 1"
    ).fetchone())
    staging.stage_change(
        imported_db, model_key="stingray", table_role="runtime_steps",
        op="update",
        key={"model_key": "stingray", "step_key": step["step_key"]},
        record={"notes": f"{step['notes']} task8".strip()},
    )
    staging.stage_change(
        imported_db, model_key="stingray", table_role="section_presentation",
        op="update",
        key={
            "model_key": "stingray", "section_id": presentation["section_id"],
        },
        record={"notes": f"{presentation['notes']} task8".strip()},
    )
    assert staging.commit_staged(imported_db)["ok"]
    batch = sync.build_batch(imported_db, real_workbook)
    assert batch["skipped"] == []
    assert {(item["sheet"], item["action"]) for item in batch["items"]} == {
        ("runtime_steps", "update"),
        ("section_presentation", "update"),
    }


def test_every_populated_role_builds_a_mapping_backed_edit_batch(
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
            blocked = {
                "model_key", *spec.key,
                *staging._DERIVED_READ_ONLY.get(role, ()),
                *(column for fk in spec.foreign_keys for column in fk.columns),
            }
            writable = [
                column for column in spec.columns if column not in blocked
            ]
            preferred = (
                [column for column in writable if column in spec.booleans]
                + [column for column in writable
                   if spec.types[column] == "integer"
                   and column not in spec.booleans]
                + [column for column in writable
                   if spec.types[column] == "text"
                   and column not in spec.enums]
                + [column for column in writable if column in spec.enums
                   and any(value != record[column]
                           for value in spec.enums[column])]
            )
            op = "update" if preferred else "delete"
            if preferred:
                column = preferred[0]
                if column in spec.booleans:
                    record[column] = 0 if record[column] else 1
                elif spec.types[column] == "integer":
                    record[column] = (record[column] or 0) + 1
                elif column in spec.enums:
                    record[column] = next(
                        value for value in spec.enums[column]
                        if value != record[column]
                    )
                else:
                    record[column] = f"{record[column] or ''} task8".strip()
            staging.stage_change(
                connection, model_key=model_key, table_role=role,
                op=op, key=key, record=record if op == "update" else None,
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


def test_external_workbook_drift_blocks_before_editor(
    imported_db, real_workbook, tmp_path, monkeypatch
):
    scratch = tmp_path / "drifted.xlsx"
    shutil.copy2(real_workbook, scratch)
    row = dict(imported_db.execute(
        "SELECT * FROM stingray_options WHERE rpo='Z51'"
    ).fetchone())
    key = {"option_id": row["option_id"]}
    staging.stage_change(
        imported_db, model_key="stingray", table_role="options", op="update",
        key=key, record={"price": row["price"] + 1},
    )
    assert staging.commit_staged(imported_db)["ok"]
    scratch.write_bytes(scratch.read_bytes() + b"external-drift")
    called = False

    def forbidden(*args, **kwargs):
        nonlocal called
        called = True
        raise AssertionError("editor must not run")

    monkeypatch.setattr(sync.editor_ops, "apply_batch", forbidden)
    result = sync.sync_workbook(imported_db, scratch, write=False)
    assert result["status"] == "stale_source"
    assert called is False


def test_successful_sync_advances_trusted_hash_for_next_sync(
    imported_db, real_workbook, tmp_path, monkeypatch
):
    scratch = tmp_path / "successive.xlsx"
    shutil.copy2(real_workbook, scratch)

    def fake_apply(path, batch, **kwargs):
        if kwargs["write"]:
            path.write_bytes(path.read_bytes() + b"guarded-sync")
            return {"ok": True, "status": "applied", "backupPath": "test-backup"}
        return {"ok": True, "status": "validated"}

    monkeypatch.setattr(sync.editor_ops, "apply_batch", fake_apply)
    for increment in (1, 2):
        row = dict(imported_db.execute(
            "SELECT * FROM stingray_options WHERE rpo='Z51'"
        ).fetchone())
        key = {"option_id": row["option_id"]}
        staging.stage_change(
            imported_db, model_key="stingray", table_role="options",
            op="update", key=key, record={"price": row["price"] + increment},
        )
        assert staging.commit_staged(imported_db)["ok"]
        dry = sync.sync_workbook(imported_db, scratch, write=False)
        assert dry["status"] == "validated"
        live = sync.sync_workbook(
            imported_db, scratch, write=True,
            expected_mtime_ns=dry["workbookMtimeNs"],
        )
        assert live["status"] == "applied"
    trusted = imported_db.execute(
        "SELECT value FROM meta WHERE key='trusted_workbook_sha256'"
    ).fetchone()[0]
    assert trusted == hashlib.sha256(scratch.read_bytes()).hexdigest()
    details = [json.loads(row[0]) for row in imported_db.execute(
        "SELECT sync_detail FROM change_history WHERE status='sync_succeeded'"
    )]
    assert all(detail["old_workbook_sha256"] for detail in details)
    assert all(detail["new_workbook_sha256"] for detail in details)


def test_later_sync_uses_values_from_prior_successful_sync(
    imported_db, real_workbook, tmp_path, monkeypatch
):
    scratch = tmp_path / "successive-fields.xlsx"
    shutil.copy2(real_workbook, scratch)

    def fake_apply(path, batch, **kwargs):
        if kwargs["write"]:
            path.write_bytes(path.read_bytes() + b"guarded-sync")
            return {"ok": True, "status": "applied", "backupPath": "backup"}
        return {"ok": True, "status": "validated"}

    monkeypatch.setattr(sync.editor_ops, "apply_batch", fake_apply)
    row = dict(imported_db.execute(
        "SELECT * FROM stingray_options WHERE rpo='Z51'"
    ).fetchone())
    key = {"option_id": row["option_id"]}
    description = f"{row['description']} task8 synced".strip()
    staging.stage_change(
        imported_db, model_key="stingray", table_role="options", op="update",
        key=key, record={"description": description},
    )
    assert staging.commit_staged(imported_db)["ok"]
    dry = sync.sync_workbook(imported_db, scratch, write=False)
    assert sync.sync_workbook(
        imported_db, scratch, write=True,
        expected_mtime_ns=dry["workbookMtimeNs"],
    )["ok"]

    staging.stage_change(
        imported_db, model_key="stingray", table_role="options", op="update",
        key=key, record={"price": row["price"] + 1},
    )
    assert staging.commit_staged(imported_db)["ok"]
    item = sync.build_batch(imported_db, scratch)["items"][0]
    assert item["row"]["description"] == description

    committed = dict(imported_db.execute(
        "SELECT * FROM change_history WHERE status='committed' ORDER BY id LIMIT 1"
    ).fetchone())
    disposition = imported_db.execute(
        "SELECT id, evidence_json FROM source_row_disposition "
        "WHERE source_sheet=? AND source_row=? ORDER BY import_run_id DESC LIMIT 1",
        (committed["src_sheet"], committed["src_row"]),
    ).fetchone()
    evidence = json.loads(disposition["evidence_json"])
    evidence["source_values"]["description"] = "reimported description"
    imported_db.execute(
        "UPDATE source_row_disposition SET evidence_json=? WHERE id=?",
        (json.dumps(evidence), disposition["id"]),
    )
    imported_db.execute(
        "UPDATE meta SET value='reimported-workbook-hash' "
        "WHERE key='trusted_workbook_sha256'"
    )
    imported_db.execute(
        "UPDATE import_runs SET workbook_sha256='reimported-workbook-hash'"
    )
    imported_db.commit()
    assert sync._original_source_values(
        imported_db, committed
    )["description"] == "reimported description"


def test_cross_row_sync_chain_preserves_earlier_row_values(
    imported_db, real_workbook, tmp_path, monkeypatch
):
    scratch = tmp_path / "cross-row-chain.xlsx"
    shutil.copy2(real_workbook, scratch)

    def fake_apply(path, batch, **kwargs):
        if kwargs["write"]:
            path.write_bytes(path.read_bytes() + b"guarded-sync")
            return {"ok": True, "status": "applied", "backupPath": "backup"}
        return {"ok": True, "status": "validated"}

    monkeypatch.setattr(sync.editor_ops, "apply_batch", fake_apply)
    spec = edit_spec(imported_db, "stingray", "options")
    rows = []
    for candidate in imported_db.execute(
        "SELECT * FROM stingray_options WHERE rpo<>'' ORDER BY option_id"
    ):
        candidate = dict(candidate)
        key = {"option_id": candidate["option_id"]}
        if not staging._shared_source_guard(imported_db, spec, "update", key):
            rows.append(candidate)
        if len(rows) == 2:
            break
    description = f"{rows[0]['description']} retained across row B".strip()

    def commit_and_sync(row, patch):
        try:
            staging.stage_change(
                imported_db, model_key="stingray", table_role="options",
                op="update", key={"option_id": row["option_id"]}, record=patch,
            )
        except StagingError as error:
            pytest.fail(str(error.errors))
        assert staging.commit_staged(imported_db)["ok"]
        dry = sync.sync_workbook(imported_db, scratch, write=False)
        assert sync.sync_workbook(
            imported_db, scratch, write=True,
            expected_mtime_ns=dry["workbookMtimeNs"],
        )["ok"]

    commit_and_sync(rows[0], {"description": description})
    commit_and_sync(rows[1], {"price": rows[1]["price"] + 1})
    staging.stage_change(
        imported_db, model_key="stingray", table_role="options", op="update",
        key={"option_id": rows[0]["option_id"]},
        record={"price": rows[0]["price"] + 1},
    )
    assert staging.commit_staged(imported_db)["ok"]
    item = sync.build_batch(imported_db, scratch)["items"][0]
    assert item["row"]["description"] == description


def test_broken_sync_hash_chain_fails_closed(
    imported_db, real_workbook, tmp_path, monkeypatch
):
    scratch = tmp_path / "broken-chain.xlsx"
    shutil.copy2(real_workbook, scratch)

    def fake_apply(path, batch, **kwargs):
        if kwargs["write"]:
            path.write_bytes(path.read_bytes() + b"guarded-sync")
            return {"ok": True, "status": "applied", "backupPath": "backup"}
        return {"ok": True, "status": "validated"}

    monkeypatch.setattr(sync.editor_ops, "apply_batch", fake_apply)
    spec = edit_spec(imported_db, "stingray", "options")
    row = next(
        dict(candidate) for candidate in imported_db.execute(
            "SELECT * FROM stingray_options WHERE rpo<>'' ORDER BY option_id"
        )
        if not staging._shared_source_guard(
            imported_db, spec, "update",
            {"option_id": candidate["option_id"]},
        )
    )
    key = {"option_id": row["option_id"]}
    try:
        staging.stage_change(
            imported_db, model_key="stingray", table_role="options", op="update",
            key=key, record={"description": "chain source"},
        )
    except StagingError as error:
        pytest.fail(str(error.errors))
    assert staging.commit_staged(imported_db)["ok"]
    dry = sync.sync_workbook(imported_db, scratch, write=False)
    assert sync.sync_workbook(
        imported_db, scratch, write=True,
        expected_mtime_ns=dry["workbookMtimeNs"],
    )["ok"]
    imported_db.execute(
        "UPDATE meta SET value='unreachable-current-hash' "
        "WHERE key='trusted_workbook_sha256'"
    )
    imported_db.commit()
    staging.stage_change(
        imported_db, model_key="stingray", table_role="options", op="update",
        key=key, record={"price": row["price"] + 1},
    )
    assert staging.commit_staged(imported_db)["ok"]
    batch = sync.build_batch(imported_db, scratch)
    assert batch["items"] == []
    assert "no unique unbroken hash chain" in batch["skipped"][0]["reason"]


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
