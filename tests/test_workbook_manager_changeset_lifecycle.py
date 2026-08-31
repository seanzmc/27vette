"""Pass 5 immutable ChangeSet lifecycle for Workbook Manager."""

from __future__ import annotations

import hashlib
import json
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND = REPO_ROOT / "workbook-manager" / "backend"
for path in (str(BACKEND), str(REPO_ROOT / "scripts")):
    if path not in sys.path:
        sys.path.insert(0, path)

from app import db as dbmod, drafts, main  # noqa: E402
from corvette_form_generator.workbook_domain.changeset import parse_changeset  # noqa: E402
from test_editor_ops_apply import build_ops_fixture  # noqa: E402
from test_workbook_changeset_service import make_valid_changeset, make_workbook  # noqa: E402


class TestImmutableChangeSetEmission(unittest.TestCase):
    def _stores(self, root: Path):
        projection = dbmod.connect(root / "projection.sqlite3")
        state = dbmod.connect(root / "state.sqlite3", foreign_keys=True)
        dbmod.init_projection_schema(projection)
        dbmod.init_durable_schema(state)
        projection.execute(
            "INSERT INTO models(src_sheet, src_row, src_family, physical_key, "
            "model_context, model_key, active) VALUES(?,?,?,?,?,?,?)",
            ("model_master", 2, "model_master", '["stingray"]', '["stingray"]',
             "stingray", "True"),
        )
        projection.execute(
            "INSERT INTO sheet_registry(src_sheet, src_row, src_family, "
            "physical_key, model_context, model_key, source_role, sheet_name, "
            "active) VALUES(?,?,?,?,?,?,?,?,?)",
            ("model_workbook_sources", 2, "model_workbook_sources",
             '["stingray","source_option_sheet"]', '["stingray"]', "stingray",
             "source_option_sheet", "stingray_options", "True"),
        )
        projection.execute(
            "INSERT INTO options(src_sheet, src_row, src_family, physical_key, "
            "model_context, model_id, option_id, rpo, option_name, price, active) "
            "VALUES(?,?,?,?,?,?,?,?,?,?,?)",
            ("stingray_options", 10, "options", '["opt_test"]', '["stingray"]',
             "stingray", "opt_test", "TST", "Original", "100", "True"),
        )
        projection.commit()
        return projection, state

    def test_commit_emits_one_exact_immutable_typed_changeset(self):
        with tempfile.TemporaryDirectory(prefix="wbm-changeset-emission-") as raw:
            projection, state = self._stores(Path(raw))
            try:
                operation = drafts.save_operation(
                    projection,
                    state,
                    projection_state="current",
                    base_workbook_sha256="a" * 64,
                    base_workbook_mtime_ns="123",
                    draft_id="draft-1",
                    table="options",
                    model_id="stingray",
                    op="update",
                    key={"option_id": "opt_test"},
                    record={"option_name": "Changed", "price": "125"},
                    session_id="session-1",
                    actor="Sean",
                )

                emitted = drafts.emit_changeset(state, draft_id="draft-1")
                parsed = parse_changeset(emitted)

                self.assertEqual(parsed, emitted)
                self.assertEqual(emitted["schemaVersion"], "workbook-changeset-1")
                self.assertEqual(emitted["source"], {
                    "kind": "workbook-manager",
                    "runId": "draft-1",
                })
                self.assertEqual(emitted["targets"], ["stingray"])
                self.assertEqual(emitted["workbook"], {
                    "sha256": "a" * 64,
                    "mtimeNs": "123",
                })
                self.assertEqual(emitted["sheetCreates"], [])
                self.assertEqual(emitted["noops"], [])
                self.assertEqual(emitted["warningAcknowledgementsRequested"], [])
                self.assertEqual(emitted["bindings"], {})
                self.assertEqual(emitted["rowChanges"], [{
                    "action": "update",
                    "sheet": "stingray_options",
                    "family": "options",
                    "key": {"option_id": "opt_test"},
                    "fields": {
                        "option_name": {"before": "Original", "after": "Changed"},
                        "price": {"before": 100, "after": 125},
                    },
                    "provenance": [{
                        "kind": "workbook-manager-draft-operation",
                        "id": str(operation["id"]),
                    }],
                }])
                stored = state.execute(
                    "SELECT * FROM draft_changesets WHERE draft_id='draft-1'"
                ).fetchone()
                self.assertIsNotNone(stored)
                self.assertEqual(json.loads(stored["payload_json"]), emitted)
                self.assertEqual(stored["change_set_id"], emitted["changeSetId"])
                self.assertEqual(
                    stored["semantic_fingerprint"], emitted["semanticFingerprint"]
                )
                with self.assertRaisesRegex(
                    sqlite3.IntegrityError, "ChangeSet artifacts are immutable"
                ):
                    state.execute(
                        "UPDATE draft_changesets SET payload_json='{}' "
                        "WHERE draft_id='draft-1'"
                    )
                with self.assertRaisesRegex(
                    sqlite3.IntegrityError, "ChangeSet artifacts are immutable"
                ):
                    state.execute(
                        "DELETE FROM draft_changesets WHERE draft_id='draft-1'"
                    )
                state.rollback()
                draft = state.execute(
                    "SELECT status FROM workflow_drafts WHERE id='draft-1'"
                ).fetchone()
                self.assertEqual(draft["status"], "changeset_emitted")

                with self.assertRaises(drafts.DraftError) as ctx:
                    drafts.emit_changeset(state, draft_id="draft-1")
                self.assertEqual(ctx.exception.code, "draft_not_mutable")
                self.assertEqual(
                    state.execute(
                        "SELECT COUNT(*) c FROM draft_changesets WHERE draft_id='draft-1'"
                    ).fetchone()["c"],
                    1,
                )
            finally:
                projection.close()
                state.close()

    def test_shared_asset_uses_real_model_context_not_wildcard_target(self):
        with tempfile.TemporaryDirectory(prefix="wbm-shared-asset-targets-") as raw:
            projection, state = self._stores(Path(raw))
            projection.execute(
                "INSERT INTO assets(src_sheet, src_row, src_family, physical_key, "
                "model_context, model_key, target_type, target_id, image_url, "
                "image_alt, image_fit, image_position, active) "
                "VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    "asset_map", 2, "asset_map", '["*","option","opt_test"]',
                    '["stingray","z06"]', "*", "option", "opt_test",
                    "https://example.test/original.png", "Shared", "cover", "center",
                    "True",
                ),
            )
            projection.commit()
            try:
                drafts.save_operation(
                    projection,
                    state,
                    projection_state="current",
                    base_workbook_sha256="a" * 64,
                    base_workbook_mtime_ns="123",
                    draft_id="shared-asset",
                    table="assets",
                    model_id="*",
                    op="update",
                    key={
                        "model_key": "*",
                        "target_type": "option",
                        "target_id": "opt_test",
                    },
                    record={"image_fit": "contain"},
                )
                emitted = drafts.emit_changeset(state, draft_id="shared-asset")
                self.assertEqual(emitted["targets"], ["stingray", "z06"])
                self.assertNotIn("*", emitted["targets"])
            finally:
                projection.close()
                state.close()

    def test_empty_draft_cannot_emit_a_changeset(self):
        with tempfile.TemporaryDirectory(prefix="wbm-empty-changeset-") as raw:
            _, state = self._stores(Path(raw))
            try:
                state.execute(
                    "INSERT INTO workflow_drafts(id, created_ts, updated_ts, status, "
                    "base_workbook_sha256, base_workbook_mtime_ns) "
                    "VALUES('empty', 't', 't', 'draft', ?, '123')",
                    ("b" * 64,),
                )
                state.commit()
                with self.assertRaises(drafts.DraftError) as ctx:
                    drafts.emit_changeset(state, draft_id="empty")
                self.assertEqual(ctx.exception.code, "empty_draft")
                self.assertEqual(
                    state.execute("SELECT status FROM workflow_drafts WHERE id='empty'")
                    .fetchone()["status"],
                    "draft",
                )
            finally:
                state.close()

    def test_commit_endpoint_returns_the_persisted_changeset(self):
        with tempfile.TemporaryDirectory(prefix="wbm-commit-endpoint-") as raw:
            projection, state = self._stores(Path(raw))
            try:
                drafts.save_operation(
                    projection,
                    state,
                    projection_state="current",
                    base_workbook_sha256="c" * 64,
                    base_workbook_mtime_ns="456",
                    draft_id="draft-api",
                    table="options",
                    model_id="stingray",
                    op="update",
                    key={"option_id": "opt_test"},
                    record={"price": "150"},
                )
                emitted = main.commit_draft(
                    "draft-api", _lock=None, state_conn=state
                )
                stored = json.loads(
                    state.execute(
                        "SELECT payload_json FROM draft_changesets "
                        "WHERE draft_id='draft-api'"
                    ).fetchone()["payload_json"]
                )
                self.assertEqual(emitted, stored)
            finally:
                projection.close()
                state.close()


class TestCompleteFinalGraphLifecycle(unittest.TestCase):
    def _stores(self, root: Path):
        projection, state = TestImmutableChangeSetEmission()._stores(root)
        registrations = (
            ("exclusive_groups_sheet", "exclusive_groups"),
            ("exclusive_group_members_sheet", "exclusive_group_members"),
        )
        for row_number, (role, sheet) in enumerate(registrations, start=3):
            projection.execute(
                "INSERT INTO sheet_registry(src_sheet, src_row, src_family, "
                "physical_key, model_context, model_key, source_role, sheet_name, "
                "active) VALUES(?,?,?,?,?,?,?,?,?)",
                ("model_workbook_sources", row_number, "model_workbook_sources",
                 json.dumps(["stingray", role]), json.dumps(["stingray"]),
                 "stingray", role, sheet, "True"),
            )
        projection.execute(
            "INSERT INTO exclusive_groups(src_sheet, src_row, src_family, "
            "physical_key, model_context, model_id, group_id, selection_mode, "
            "active) VALUES(?,?,?,?,?,?,?,?,?)",
            ("exclusive_groups", 2, "exclusive_groups", json.dumps(["excl_one"]),
             json.dumps(["stingray"]), "stingray", "excl_one",
             "single_within_group", "True"),
        )
        for row_number, option_id in enumerate(("opt_one_001", "opt_two_001"), start=2):
            projection.execute(
                "INSERT INTO exclusive_group_members(src_sheet, src_row, src_family, "
                "physical_key, model_context, model_id, group_id, option_id, "
                "display_order, active) VALUES(?,?,?,?,?,?,?,?,?,?)",
                ("exclusive_group_members", row_number, "exclusive_members",
                 json.dumps(["excl_one", option_id]), json.dumps(["stingray"]),
                 "stingray", "excl_one", option_id, str((row_number - 1) * 10),
                 "True"),
            )
        projection.commit()
        workbook = root / "fixture.xlsx"
        build_ops_fixture().save(workbook)
        return projection, state, workbook

    def _save(
        self,
        projection,
        state,
        workbook: Path,
        *,
        draft_id: str,
        table: str,
        op: str,
        key: dict,
        record: dict | None,
    ):
        return drafts.save_operation(
            projection,
            state,
            projection_state="current",
            base_workbook_sha256=hashlib.sha256(workbook.read_bytes()).hexdigest(),
            base_workbook_mtime_ns=str(workbook.stat().st_mtime_ns),
            draft_id=draft_id,
            table=table,
            model_id="stingray",
            op=op,
            key=key,
            record=record,
        )

    @patch("corvette_form_generator.editor_ops.validate_workbook_schema", return_value=[])
    def test_parent_and_member_additions_preview_as_one_complete_final_graph(self, _schema):
        with tempfile.TemporaryDirectory(prefix="wbm-final-graph-add-") as raw:
            projection, state, workbook = self._stores(Path(raw))
            try:
                draft_id = "draft-add-graph"
                self._save(
                    projection, state, workbook, draft_id=draft_id,
                    table="exclusive_groups", op="add", key={"group_id": "excl_new"},
                    record={"group_id": "excl_new", "selection_mode": "single_within_group",
                            "active": "True", "notes": None},
                )
                for order, option_id in ((10, "opt_one_001"), (20, "opt_two_001")):
                    self._save(
                        projection, state, workbook, draft_id=draft_id,
                        table="exclusive_group_members", op="add",
                        key={"group_id": "excl_new", "option_id": option_id},
                        record={"group_id": "excl_new", "option_id": option_id,
                                "display_order": str(order), "active": "True"},
                    )

                changeset = drafts.emit_changeset(state, draft_id=draft_id)
                attempt = drafts.preview_draft(
                    state, draft_id=draft_id, projection_state="current",
                    workbook_path=workbook,
                )

                self.assertEqual([row["action"] for row in changeset["rowChanges"]],
                                 ["add", "add", "add"])
                self.assertTrue(attempt["result"]["ok"], attempt)
                self.assertEqual(attempt["manager_state"], "preview_ready")
                self.assertEqual(attempt["allowed_verbs"], ["approve", "cancel"])
            finally:
                projection.close()
                state.close()

    @patch("corvette_form_generator.editor_ops.validate_workbook_schema", return_value=[])
    def test_parent_and_dependent_deletes_preview_as_one_complete_final_graph(self, _schema):
        with tempfile.TemporaryDirectory(prefix="wbm-final-graph-delete-") as raw:
            projection, state, workbook = self._stores(Path(raw))
            try:
                draft_id = "draft-delete-graph"
                for option_id in ("opt_one_001", "opt_two_001"):
                    self._save(
                        projection, state, workbook, draft_id=draft_id,
                        table="exclusive_group_members", op="delete",
                        key={"group_id": "excl_one", "option_id": option_id}, record=None,
                    )
                self._save(
                    projection, state, workbook, draft_id=draft_id,
                    table="exclusive_groups", op="delete", key={"group_id": "excl_one"},
                    record=None,
                )

                changeset = drafts.emit_changeset(state, draft_id=draft_id)
                attempt = drafts.preview_draft(
                    state, draft_id=draft_id, projection_state="current",
                    workbook_path=workbook,
                )

                self.assertEqual([row["action"] for row in changeset["rowChanges"]],
                                 ["delete", "delete", "delete"])
                self.assertTrue(attempt["result"]["ok"], attempt)
                self.assertEqual(attempt["result"]["warningPolicy"]["blockingIds"], [])
                self.assertEqual(attempt["manager_state"], "preview_ready")
            finally:
                projection.close()
                state.close()

    @patch("corvette_form_generator.editor_ops.validate_workbook_schema", return_value=[])
    def test_incomplete_dependent_delete_graph_is_not_approvable(self, _schema):
        with tempfile.TemporaryDirectory(prefix="wbm-final-graph-invalid-") as raw:
            projection, state, workbook = self._stores(Path(raw))
            try:
                draft_id = "draft-invalid-delete"
                self._save(
                    projection, state, workbook, draft_id=draft_id,
                    table="exclusive_groups", op="delete", key={"group_id": "excl_one"},
                    record=None,
                )
                drafts.emit_changeset(state, draft_id=draft_id)

                attempt = drafts.preview_draft(
                    state, draft_id=draft_id, projection_state="current",
                    workbook_path=workbook,
                )

                self.assertTrue(attempt["result"]["warningPolicy"]["blockingIds"])
                self.assertEqual(attempt["manager_state"], "preview_rejected")
                self.assertEqual(attempt["allowed_verbs"], ["cancel"])
                with self.assertRaises(drafts.DraftError) as ctx:
                    drafts.approve_draft(
                        state, draft_id=draft_id, projection_state="current",
                        actor="Sean", warning_ids=[],
                    )
                self.assertEqual(ctx.exception.code, "draft_not_approvable")
            finally:
                projection.close()
                state.close()

    def test_new_row_edits_coalesce_and_add_then_delete_is_a_noop(self):
        with tempfile.TemporaryDirectory(prefix="wbm-final-graph-coalesce-") as raw:
            projection, state, workbook = self._stores(Path(raw))
            try:
                draft_id = "draft-new-row-coalesce"
                self._save(
                    projection, state, workbook, draft_id=draft_id,
                    table="exclusive_groups", op="add", key={"group_id": "excl_new"},
                    record={"group_id": "excl_new", "selection_mode": "single_within_group",
                            "active": "True", "notes": None},
                )
                updated = self._save(
                    projection, state, workbook, draft_id=draft_id,
                    table="exclusive_groups", op="update", key={"group_id": "excl_new"},
                    record={"notes": "draft note"},
                )

                self.assertEqual(updated["action"], "add")
                self.assertEqual(updated["final"]["notes"], "draft note")
                self.assertEqual(len(drafts.list_operations(state, draft_id)), 1)

                removed = self._save(
                    projection, state, workbook, draft_id=draft_id,
                    table="exclusive_groups", op="delete", key={"group_id": "excl_new"},
                    record=None,
                )
                self.assertIsNone(removed)
                self.assertEqual(drafts.list_operations(state, draft_id), [])
            finally:
                projection.close()
                state.close()


class TestDurablePreviewLifecycle(unittest.TestCase):
    def _stores(self, root: Path):
        return TestImmutableChangeSetEmission()._stores(root)

    def _emitted_draft(self, root: Path, *, draft_id: str = "draft-preview"):
        projection, state = self._stores(root)
        workbook = root / "fixture.xlsx"
        workbook.write_bytes(b"preview-fixture")
        workbook_sha = hashlib.sha256(workbook.read_bytes()).hexdigest()
        workbook_mtime = str(workbook.stat().st_mtime_ns)
        drafts.save_operation(
            projection,
            state,
            projection_state="current",
            base_workbook_sha256=workbook_sha,
            base_workbook_mtime_ns=workbook_mtime,
            draft_id=draft_id,
            table="options",
            model_id="stingray",
            op="update",
            key={"option_id": "opt_test"},
            record={"price": "150"},
        )
        changeset = drafts.emit_changeset(state, draft_id=draft_id)
        return projection, state, workbook, changeset

    def test_rejected_draft_correction_is_selective_audited_and_immutable(self):
        """DRAFT-03: correction keeps failed evidence and unrelated valid work."""
        with tempfile.TemporaryDirectory(prefix="wbm-correction-") as raw:
            root = Path(raw)
            projection, state = self._stores(root)
            workbook = root / "fixture.xlsx"
            workbook.write_bytes(b"preview-fixture")
            try:
                drafts.save_operation(
                    projection, state, projection_state="current",
                    base_workbook_sha256=hashlib.sha256(workbook.read_bytes()).hexdigest(),
                    base_workbook_mtime_ns=str(workbook.stat().st_mtime_ns),
                    draft_id="draft-rejected", table="options", model_id="stingray",
                    op="update", key={"option_id": "opt_test"},
                    record={"price": "150"},
                )
                projection.execute(
                    "INSERT INTO options(src_sheet, src_row, src_family, physical_key, "
                    "model_context, model_id, option_id, rpo, option_name, price, active) "
                    "VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                    ("stingray_options", 11, "options", '[\"opt_bad\"]',
                     '[\"stingray\"]', "stingray", "opt_bad", "BAD", "Bad option",
                     "0", "True"),
                )
                projection.commit()
                bad = drafts.save_operation(
                    projection, state, projection_state="current",
                    base_workbook_sha256=hashlib.sha256(workbook.read_bytes()).hexdigest(),
                    base_workbook_mtime_ns=str(workbook.stat().st_mtime_ns),
                    draft_id="draft-rejected", table="options", model_id="stingray",
                    op="update", key={"option_id": "opt_bad"},
                    record={"option_name": "Missing six OVS rows"},
                )
                changeset = drafts.emit_changeset(state, draft_id="draft-rejected")
                drafts._persist_preview_attempt(
                    state, draft_id="draft-rejected", changeset=changeset,
                    started="2026-08-31T12:00:00+00:00", artifact_kind="formal_preview",
                    result={"ok": False, "status": "invalid", "errors": [
                        {"message": f"missing OVS row {index}"} for index in range(6)
                    ]}, exception=None,
                    identity={
                        "state": "unchanged",
                        "sha256": hashlib.sha256(workbook.read_bytes()).hexdigest(),
                        "mtimeNs": str(workbook.stat().st_mtime_ns),
                    },
                    manager_state="preview_rejected", allowed_verbs=["cancel"],
                )
                before = state.execute(
                    "SELECT payload_json FROM draft_changesets WHERE draft_id='draft-rejected'"
                ).fetchone()["payload_json"]
                attempt_before = state.execute(
                    "SELECT result_json FROM draft_preview_attempts "
                    "WHERE draft_id='draft-rejected'"
                ).fetchone()["result_json"]
                valid_id = next(
                    row["id"] for row in drafts.list_operations(state, "draft-rejected")
                    if row["id"] != bad["id"]
                )

                result = drafts.create_correction_draft(
                    projection, state, projection_state="current",
                    base_workbook_sha256=hashlib.sha256(workbook.read_bytes()).hexdigest(),
                    base_workbook_mtime_ns=str(workbook.stat().st_mtime_ns),
                    source_draft_id="draft-rejected", correction_draft_id="draft-correction",
                    selected_operation_ids=[valid_id], actor="Sean",
                    reason="Remove option missing six required OVS rows",
                )

                self.assertEqual(result["source_draft_id"], "draft-rejected")
                self.assertEqual(result["correction_draft_id"], "draft-correction")
                self.assertEqual(result["copied_operation_count"], 1)
                self.assertEqual(result["affected_models"], ["stingray"])
                self.assertEqual(
                    state.execute("SELECT status FROM workflow_drafts WHERE id='draft-rejected'").fetchone()["status"],
                    "cancelled",
                )
                self.assertEqual(len(drafts.list_operations(state, "draft-correction")), 1)
                self.assertEqual(state.execute(
                    "SELECT payload_json FROM draft_changesets WHERE draft_id='draft-rejected'"
                ).fetchone()["payload_json"], before)
                self.assertEqual(state.execute(
                    "SELECT result_json FROM draft_preview_attempts WHERE draft_id='draft-rejected'"
                ).fetchone()["result_json"], attempt_before)
                view = drafts.lifecycle_view(state, "draft-rejected")
                self.assertEqual(view["artifacts"]["correction"]["correction_draft_id"],
                                 "draft-correction")
                with self.assertRaises(sqlite3.IntegrityError):
                    state.execute(
                        "UPDATE draft_corrections SET reason='rewritten' "
                        "WHERE source_draft_id='draft-rejected'"
                    )
                state.rollback()
                with self.assertRaises(sqlite3.IntegrityError):
                    state.execute(
                        "DELETE FROM draft_corrections "
                        "WHERE source_draft_id='draft-rejected'"
                    )
                state.rollback()
                correction_operation = drafts.list_operations(
                    state, "draft-correction"
                )[0]
                discarded = drafts.discard_operation(
                    state,
                    draft_id="draft-correction",
                    operation_id=correction_operation["id"],
                )
                self.assertTrue(discarded["draft_removed"])
                self.assertEqual(
                    state.execute(
                        "SELECT status FROM workflow_drafts WHERE id='draft-correction'"
                    ).fetchone()["status"],
                    "cancelled",
                )
            finally:
                projection.close()
                state.close()

    def test_correction_refusals_and_transaction_rollback(self):
        """DRAFT-04/05: unsafe identity/state and partial transitions fail closed."""
        with tempfile.TemporaryDirectory(prefix="wbm-correction-refusal-") as raw:
            root = Path(raw)
            projection, state, workbook, changeset = self._emitted_draft(
                root, draft_id="draft-rejected"
            )
            try:
                state.execute(
                    "UPDATE workflow_drafts SET status='preview_rejected' "
                    "WHERE id='draft-rejected'"
                )
                state.commit()
                operation_id = drafts.list_operations(state, "draft-rejected")[0]["id"]
                kwargs = dict(
                    projection_state="current",
                    base_workbook_sha256=hashlib.sha256(workbook.read_bytes()).hexdigest(),
                    base_workbook_mtime_ns=str(workbook.stat().st_mtime_ns),
                    source_draft_id="draft-rejected", correction_draft_id="correction",
                    selected_operation_ids=[operation_id], actor="Sean", reason="Correct",
                )
                with self.assertRaises(drafts.DraftError) as stale:
                    drafts.create_correction_draft(
                        projection, state, **{**kwargs, "projection_state": "stale"}
                    )
                self.assertEqual(stale.exception.code, "projection_not_current")

                state.execute(
                    "UPDATE workflow_drafts SET status='workbook_state_unknown' "
                    "WHERE id='draft-rejected'"
                )
                state.commit()
                with self.assertRaises(drafts.DraftError) as unknown:
                    drafts.create_correction_draft(projection, state, **kwargs)
                self.assertEqual(unknown.exception.code, "draft_not_correctable")
                state.execute(
                    "UPDATE workflow_drafts SET status='preview_rejected' "
                    "WHERE id='draft-rejected'"
                )
                state.execute(
                    "INSERT INTO workflow_drafts(id, created_ts, updated_ts, status, "
                    "base_workbook_sha256, base_workbook_mtime_ns) "
                    "VALUES('competing', 't', 't', 'draft', 'sha', '1')"
                )
                state.commit()
                with self.assertRaises(drafts.DraftError) as competing:
                    drafts.create_correction_draft(projection, state, **kwargs)
                self.assertEqual(competing.exception.code, "competing_nonterminal_draft")
                state.execute("DELETE FROM workflow_drafts WHERE id='competing'")
                state.commit()

                with patch.object(
                    drafts,
                    "_editable_guard",
                    return_value=[{"message": "ownership no longer resolves"}],
                ):
                    with self.assertRaises(drafts.DraftError) as ownership:
                        drafts.create_correction_draft(projection, state, **kwargs)
                self.assertEqual(ownership.exception.code, "ownership_rejected")

                with patch.object(
                    drafts, "_insert_correction_link", side_effect=RuntimeError("forced")
                ):
                    with self.assertRaisesRegex(RuntimeError, "forced"):
                        drafts.create_correction_draft(projection, state, **kwargs)
                self.assertEqual(state.execute(
                    "SELECT status FROM workflow_drafts WHERE id='draft-rejected'"
                ).fetchone()["status"], "preview_rejected")
                self.assertIsNone(state.execute(
                    "SELECT 1 FROM workflow_drafts WHERE id='correction'"
                ).fetchone())
            finally:
                projection.close()
                state.close()

    def test_preview_result_mapping_matches_section_4_1(self):
        cases = (
            ({"ok": True, "status": "validated"}, "preview_ready", ["approve", "cancel"]),
            ({"ok": False, "status": "invalid_changeset"}, "preview_rejected", ["cancel"]),
            ({"ok": False, "status": "invalid"}, "preview_rejected", ["cancel"]),
            ({"ok": False, "status": "empty"}, "preview_rejected", ["cancel"]),
            ({"ok": False, "status": "bool_hygiene_failed"}, "preview_rejected", ["cancel"]),
            ({"ok": False, "status": "schema_failed"}, "preview_rejected", ["cancel"]),
            ({"ok": False, "status": "warning_blocked"}, "preview_rejected", ["cancel"]),
            ({"ok": False, "status": "stale"}, "stale", ["cancel"]),
            ({"ok": False, "status": "locked"}, "preview_retryable", ["retry_preview", "cancel"]),
            ({"ok": False, "status": "readback_failed"}, "preview_retryable", ["retry_preview", "cancel"]),
        )
        for result, expected_state, expected_verbs in cases:
            with self.subTest(status=result["status"]):
                self.assertEqual(
                    drafts._map_preview_result(result, "unchanged"),
                    (expected_state, expected_verbs),
                )
        self.assertEqual(
            drafts._map_preview_result({"ok": True, "status": "validated"}, "mismatched"),
            ("stale", ["cancel"]),
        )

    def test_preview_persists_exact_shared_service_artifact_and_lifecycle(self):
        with tempfile.TemporaryDirectory(prefix="wbm-preview-lifecycle-") as raw:
            projection, state, workbook, changeset = self._emitted_draft(Path(raw))
            service_result = {
                "ok": True,
                "schemaVersion": "workbook-change-preview-1",
                "changeSetId": changeset["changeSetId"],
                "semanticFingerprint": changeset["semanticFingerprint"],
                "workbook": changeset["workbook"],
                "status": "validated",
                "errors": [],
                "warnings": [],
                "previewFingerprint": "f" * 64,
            }
            try:
                with patch.object(
                    drafts.workbook_service,
                    "preview_changeset",
                    return_value=service_result,
                ) as preview_changeset:
                    attempt = drafts.preview_draft(
                        state,
                        draft_id="draft-preview",
                        projection_state="current",
                        workbook_path=workbook,
                    )

                preview_changeset.assert_called_once_with(workbook, changeset)
                self.assertEqual(attempt["result"], service_result)
                self.assertEqual(attempt["artifact_kind"], "formal_preview")
                self.assertEqual(attempt["manager_state"], "preview_ready")
                self.assertEqual(attempt["allowed_verbs"], ["approve", "cancel"])
                stored = state.execute(
                    "SELECT * FROM draft_preview_attempts WHERE id=?",
                    (attempt["id"],),
                ).fetchone()
                self.assertEqual(json.loads(stored["result_json"]), service_result)
                self.assertEqual(
                    state.execute(
                        "SELECT status FROM workflow_drafts WHERE id='draft-preview'"
                    ).fetchone()["status"],
                    "preview_ready",
                )
                with self.assertRaisesRegex(
                    sqlite3.IntegrityError, "preview attempt artifacts are immutable"
                ):
                    state.execute(
                        "UPDATE draft_preview_attempts SET result_json='{}' WHERE id=?",
                        (attempt["id"],),
                    )
                state.rollback()
            finally:
                projection.close()
                state.close()

    def test_invalid_shared_preview_maps_to_rejected_cancel_only(self):
        with tempfile.TemporaryDirectory(prefix="wbm-preview-rejected-") as raw:
            projection, state, workbook, _ = self._emitted_draft(Path(raw))
            refusal = {
                "ok": False,
                "status": "schema_failed",
                "errors": ["final graph is invalid"],
            }
            try:
                with patch.object(
                    drafts.workbook_service,
                    "preview_changeset",
                    return_value=refusal,
                ):
                    attempt = drafts.preview_draft(
                        state,
                        draft_id="draft-preview",
                        projection_state="current",
                        workbook_path=workbook,
                    )

                self.assertEqual(attempt["result"], refusal)
                self.assertEqual(attempt["artifact_kind"], "early_refusal")
                self.assertEqual(attempt["manager_state"], "preview_rejected")
                self.assertEqual(attempt["allowed_verbs"], ["cancel"])
            finally:
                projection.close()
                state.close()

    def test_preview_refuses_noncurrent_projection_without_calling_service(self):
        with tempfile.TemporaryDirectory(prefix="wbm-preview-freshness-") as raw:
            projection, state, workbook, _ = self._emitted_draft(Path(raw))
            try:
                with patch.object(
                    drafts.workbook_service, "preview_changeset"
                ) as preview_changeset:
                    with self.assertRaises(drafts.DraftError) as ctx:
                        drafts.preview_draft(
                            state,
                            draft_id="draft-preview",
                            projection_state="stale",
                            workbook_path=workbook,
                        )

                self.assertEqual(ctx.exception.code, "projection_not_current")
                preview_changeset.assert_not_called()
                stored = state.execute(
                    "SELECT * FROM draft_preview_attempts WHERE draft_id='draft-preview'"
                ).fetchone()
                self.assertIsNotNone(stored)
                self.assertEqual(stored["artifact_kind"], "manager_refusal")
                self.assertEqual(stored["manager_state"], "stale")
                self.assertEqual(json.loads(stored["allowed_verbs_json"]), ["cancel"])
                self.assertEqual(
                    state.execute(
                        "SELECT status FROM workflow_drafts WHERE id='draft-preview'"
                    ).fetchone()["status"],
                    "stale",
                )
            finally:
                projection.close()
                state.close()

    def test_transient_preview_exception_with_unchanged_identity_is_retryable(self):
        with tempfile.TemporaryDirectory(prefix="wbm-preview-exception-") as raw:
            projection, state, workbook, _ = self._emitted_draft(Path(raw))
            try:
                with patch.object(
                    drafts.workbook_service,
                    "preview_changeset",
                    side_effect=TimeoutError("workbook reader timed out"),
                ):
                    attempt = drafts.preview_draft(
                        state,
                        draft_id="draft-preview",
                        projection_state="current",
                        workbook_path=workbook,
                    )

                self.assertIsNone(attempt["result"])
                self.assertEqual(attempt["artifact_kind"], "exception")
                self.assertEqual(attempt["exception_class"], "TimeoutError")
                self.assertEqual(
                    attempt["exception_message"], "workbook reader timed out"
                )
                self.assertEqual(attempt["workbook_identity_state"], "unchanged")
                self.assertEqual(attempt["manager_state"], "preview_retryable")
                self.assertEqual(
                    attempt["allowed_verbs"], ["retry_preview", "cancel"]
                )
            finally:
                projection.close()
                state.close()

    def test_preview_endpoint_returns_persisted_attempt_without_writing(self):
        with tempfile.TemporaryDirectory(prefix="wbm-preview-endpoint-") as raw:
            projection, state, workbook, changeset = self._emitted_draft(Path(raw))
            service_result = {
                "ok": True,
                "schemaVersion": "workbook-change-preview-1",
                "changeSetId": changeset["changeSetId"],
                "semanticFingerprint": changeset["semanticFingerprint"],
                "workbook": changeset["workbook"],
                "status": "validated",
                "previewFingerprint": "e" * 64,
            }
            try:
                with (
                    patch.object(main.config, "DEFAULT_WORKBOOK", workbook),
                    patch.object(
                        main,
                        "_workbook_state",
                        return_value={"state": "current"},
                    ),
                    patch.object(
                        main,
                        "_projection_state",
                        return_value={"state": "current"},
                    ),
                    patch.object(
                        drafts.workbook_service,
                        "preview_changeset",
                        return_value=service_result,
                    ),
                ):
                    attempt = main.preview_draft_changeset(
                        "draft-preview",
                        _lock=None,
                        conn=projection,
                        state_conn=state,
                    )

                self.assertEqual(attempt["result"], service_result)
                self.assertEqual(attempt["manager_state"], "preview_ready")
                self.assertEqual(
                    state.execute(
                        "SELECT COUNT(*) c FROM draft_preview_attempts"
                    ).fetchone()["c"],
                    1,
                )
                self.assertEqual(
                    projection.execute(
                        "SELECT price FROM options WHERE option_id='opt_test'"
                    ).fetchone()["price"],
                    "100",
                )
                self.assertEqual(workbook.read_bytes(), b"preview-fixture")
            finally:
                projection.close()
                state.close()

    def test_preview_retry_reuses_changeset_and_creates_distinct_attempt(self):
        with tempfile.TemporaryDirectory(prefix="wbm-preview-retry-") as raw:
            projection, state, workbook, changeset = self._emitted_draft(Path(raw))
            locked = {"ok": False, "status": "locked", "errors": ["busy"]}
            validated = {
                "ok": True,
                "schemaVersion": "workbook-change-preview-1",
                "changeSetId": changeset["changeSetId"],
                "semanticFingerprint": changeset["semanticFingerprint"],
                "workbook": changeset["workbook"],
                "status": "validated",
                "previewFingerprint": "d" * 64,
            }
            try:
                with patch.object(
                    drafts.workbook_service,
                    "preview_changeset",
                    side_effect=[locked, validated],
                ) as preview_changeset:
                    first = drafts.preview_draft(
                        state,
                        draft_id="draft-preview",
                        projection_state="current",
                        workbook_path=workbook,
                    )
                    second = drafts.preview_draft(
                        state,
                        draft_id="draft-preview",
                        projection_state="current",
                        workbook_path=workbook,
                    )

                self.assertEqual(first["manager_state"], "preview_retryable")
                self.assertEqual(second["manager_state"], "preview_ready")
                self.assertNotEqual(first["id"], second["id"])
                self.assertEqual(preview_changeset.call_count, 2)
                for call in preview_changeset.call_args_list:
                    self.assertEqual(call.args, (workbook, changeset))
                self.assertEqual(
                    state.execute(
                        "SELECT COUNT(*) c FROM draft_preview_attempts"
                    ).fetchone()["c"],
                    2,
                )
            finally:
                projection.close()
                state.close()

    def test_nontransient_exception_and_identity_loss_fail_closed(self):
        cases = (
            (ValueError("unexpected parser failure"), False, "preview_rejected"),
            (TimeoutError("reader timed out"), True, "stale"),
        )
        for exception, remove_workbook, expected_state in cases:
            with self.subTest(expected_state=expected_state):
                with tempfile.TemporaryDirectory(prefix="wbm-preview-failclosed-") as raw:
                    projection, state, workbook, _ = self._emitted_draft(Path(raw))

                    def fail_preview(*_args):
                        if remove_workbook:
                            workbook.unlink()
                        raise exception

                    try:
                        with patch.object(
                            drafts.workbook_service,
                            "preview_changeset",
                            side_effect=fail_preview,
                        ):
                            attempt = drafts.preview_draft(
                                state,
                                draft_id="draft-preview",
                                projection_state="current",
                                workbook_path=workbook,
                            )
                        self.assertEqual(attempt["manager_state"], expected_state)
                        self.assertEqual(attempt["allowed_verbs"], ["cancel"])
                        self.assertEqual(attempt["exception_class"], type(exception).__name__)
                    finally:
                        projection.close()
                        state.close()


class TestDurableApprovalLifecycle(unittest.TestCase):
    def _preview_ready(self, root: Path):
        helper = TestDurablePreviewLifecycle()
        projection, state, workbook, changeset = helper._emitted_draft(
            root, draft_id="draft-approval"
        )
        preview = {
            "ok": True,
            "schemaVersion": "workbook-change-preview-1",
            "changeSetId": changeset["changeSetId"],
            "semanticFingerprint": changeset["semanticFingerprint"],
            "workbook": changeset["workbook"],
            "status": "validated",
            "warningPolicy": {"blockingIds": [], "confirmableIds": ["warn-1"]},
            "previewFingerprint": "a" * 64,
        }
        with patch.object(
            drafts.workbook_service, "preview_changeset", return_value=preview
        ):
            preview_attempt = drafts.preview_draft(
                state,
                draft_id="draft-approval",
                projection_state="current",
                workbook_path=workbook,
            )
        return projection, state, changeset, preview, preview_attempt

    def test_approval_persists_exact_shared_service_artifact_and_lifecycle(self):
        with tempfile.TemporaryDirectory(prefix="wbm-approval-lifecycle-") as raw:
            projection, state, changeset, preview, preview_attempt = (
                self._preview_ready(Path(raw))
            )
            approval = {
                "ok": True,
                "schemaVersion": "workbook-change-approval-1",
                "actor": "Sean",
                "changeSetId": changeset["changeSetId"],
                "semanticFingerprint": changeset["semanticFingerprint"],
                "previewFingerprint": preview["previewFingerprint"],
                "workbook": changeset["workbook"],
                "acceptedWarningIds": ["warn-1"],
                "approvalFingerprint": "b" * 64,
            }
            try:
                with patch.object(
                    drafts.workbook_service,
                    "approve_changeset",
                    return_value=approval,
                ) as approve_changeset:
                    attempt = drafts.approve_draft(
                        state,
                        draft_id="draft-approval",
                        projection_state="current",
                        actor="Sean",
                        warning_ids=["warn-1"],
                    )

                approve_changeset.assert_called_once_with(
                    changeset, preview, actor="Sean", warning_ids=["warn-1"]
                )
                self.assertEqual(attempt["result"], approval)
                self.assertEqual(attempt["preview_attempt_id"], preview_attempt["id"])
                self.assertEqual(attempt["artifact_kind"], "formal_approval")
                self.assertEqual(attempt["manager_state"], "approved")
                self.assertEqual(attempt["allowed_verbs"], ["apply", "cancel"])
                stored = state.execute(
                    "SELECT * FROM draft_approval_attempts WHERE id=?",
                    (attempt["id"],),
                ).fetchone()
                self.assertEqual(json.loads(stored["result_json"]), approval)
                self.assertEqual(stored["preview_fingerprint"], "a" * 64)
                with self.assertRaisesRegex(
                    sqlite3.IntegrityError, "approval attempt artifacts are immutable"
                ):
                    state.execute(
                        "UPDATE draft_approval_attempts SET result_json='{}' WHERE id=?",
                        (attempt["id"],),
                    )
                state.rollback()
                with self.assertRaisesRegex(
                    sqlite3.IntegrityError, "approval attempt artifacts are immutable"
                ):
                    state.execute(
                        "DELETE FROM draft_approval_attempts WHERE id=?", (attempt["id"],)
                    )
                state.rollback()
            finally:
                projection.close()
                state.close()

    def test_approval_result_mapping_matches_section_4_1(self):
        cases = (
            (
                {"ok": True, "schemaVersion": "workbook-change-approval-1"},
                "approved",
                ["apply", "cancel"],
            ),
            (
                {"ok": False, "status": "warning_confirmation_mismatch"},
                "approval_confirmation_required",
                ["approve", "cancel"],
            ),
            (
                {"ok": False, "status": "preview_not_validated"},
                "approval_repreview_required",
                ["retry_preview", "cancel"],
            ),
            (
                {"ok": False, "status": "binding_mismatch"},
                "approval_repreview_required",
                ["retry_preview", "cancel"],
            ),
            (
                {"ok": False, "status": "warning_blocked"},
                "approval_repreview_required",
                ["retry_preview", "cancel"],
            ),
        )
        for result, expected_state, expected_verbs in cases:
            with self.subTest(result=result):
                self.assertEqual(
                    drafts._map_approval_result(result),
                    (expected_state, expected_verbs),
                )
        self.assertEqual(
            drafts._map_approval_result({"ok": False, "status": "unexpected"}),
            ("approval_rejected", ["cancel"]),
        )

    def test_approval_refuses_noncurrent_projection_without_calling_service(self):
        with tempfile.TemporaryDirectory(prefix="wbm-approval-freshness-") as raw:
            projection, state, _, _, _ = self._preview_ready(Path(raw))
            try:
                with patch.object(
                    drafts.workbook_service, "approve_changeset"
                ) as approve_changeset:
                    with self.assertRaises(drafts.DraftError) as ctx:
                        drafts.approve_draft(
                            state,
                            draft_id="draft-approval",
                            projection_state="stale",
                            actor="Sean",
                            warning_ids=[],
                        )
                self.assertEqual(ctx.exception.code, "projection_not_current")
                approve_changeset.assert_not_called()
                stored = state.execute(
                    "SELECT * FROM draft_approval_attempts WHERE draft_id='draft-approval'"
                ).fetchone()
                self.assertEqual(stored["artifact_kind"], "manager_refusal")
                self.assertEqual(stored["manager_state"], "stale")
                self.assertEqual(json.loads(stored["allowed_verbs_json"]), ["cancel"])
            finally:
                projection.close()
                state.close()

    def test_approval_exception_is_rejected_without_fabricated_artifact(self):
        with tempfile.TemporaryDirectory(prefix="wbm-approval-exception-") as raw:
            projection, state, _, _, _ = self._preview_ready(Path(raw))
            try:
                with patch.object(
                    drafts.workbook_service,
                    "approve_changeset",
                    side_effect=RuntimeError("approval service failed"),
                ):
                    attempt = drafts.approve_draft(
                        state,
                        draft_id="draft-approval",
                        projection_state="current",
                        actor="Sean",
                        warning_ids=[],
                    )
                self.assertIsNone(attempt["result"])
                self.assertEqual(attempt["artifact_kind"], "exception")
                self.assertEqual(attempt["exception_class"], "RuntimeError")
                self.assertEqual(attempt["exception_message"], "approval service failed")
                self.assertEqual(attempt["manager_state"], "approval_rejected")
                self.assertEqual(attempt["allowed_verbs"], ["cancel"])
            finally:
                projection.close()
                state.close()

    def test_confirmation_retry_reuses_exact_changeset_and_preview(self):
        with tempfile.TemporaryDirectory(prefix="wbm-approval-confirm-") as raw:
            projection, state, changeset, preview, preview_attempt = (
                self._preview_ready(Path(raw))
            )
            mismatch = {
                "ok": False,
                "status": "warning_confirmation_mismatch",
                "errors": ["confirm warn-1"],
            }
            approved = {
                "ok": True,
                "schemaVersion": "workbook-change-approval-1",
                "approvalFingerprint": "c" * 64,
            }
            try:
                with patch.object(
                    drafts.workbook_service,
                    "approve_changeset",
                    side_effect=[mismatch, approved],
                ) as approve_changeset:
                    first = drafts.approve_draft(
                        state,
                        draft_id="draft-approval",
                        projection_state="current",
                        actor="Sean",
                        warning_ids=[],
                    )
                    second = drafts.approve_draft(
                        state,
                        draft_id="draft-approval",
                        projection_state="current",
                        actor="Sean",
                        warning_ids=["warn-1"],
                    )
                self.assertEqual(first["manager_state"], "approval_confirmation_required")
                self.assertEqual(second["manager_state"], "approved")
                self.assertNotEqual(first["id"], second["id"])
                self.assertEqual(first["preview_attempt_id"], preview_attempt["id"])
                self.assertEqual(second["preview_attempt_id"], preview_attempt["id"])
                self.assertEqual(approve_changeset.call_args_list[0].args, (changeset, preview))
                self.assertEqual(approve_changeset.call_args_list[1].args, (changeset, preview))
            finally:
                projection.close()
                state.close()

    def test_repreview_required_binds_later_approval_to_new_preview(self):
        with tempfile.TemporaryDirectory(prefix="wbm-approval-repreview-") as raw:
            projection, state, changeset, _, first_preview_attempt = (
                self._preview_ready(Path(raw))
            )
            refusal = {"ok": False, "status": "binding_mismatch", "errors": ["stale"]}
            new_preview = {
                "ok": True,
                "schemaVersion": "workbook-change-preview-1",
                "changeSetId": changeset["changeSetId"],
                "semanticFingerprint": changeset["semanticFingerprint"],
                "workbook": changeset["workbook"],
                "status": "validated",
                "previewFingerprint": "d" * 64,
            }
            approval = {
                "ok": True,
                "schemaVersion": "workbook-change-approval-1",
                "approvalFingerprint": "e" * 64,
            }
            try:
                with patch.object(
                    drafts.workbook_service, "approve_changeset", return_value=refusal
                ):
                    rejected = drafts.approve_draft(
                        state,
                        draft_id="draft-approval",
                        projection_state="current",
                        actor="Sean",
                        warning_ids=[],
                    )
                self.assertEqual(rejected["manager_state"], "approval_repreview_required")
                with patch.object(
                    drafts.workbook_service, "preview_changeset", return_value=new_preview
                ):
                    second_preview_attempt = drafts.preview_draft(
                        state,
                        draft_id="draft-approval",
                        projection_state="current",
                        workbook_path=Path(raw) / "fixture.xlsx",
                    )
                self.assertNotEqual(second_preview_attempt["id"], first_preview_attempt["id"])
                with patch.object(
                    drafts.workbook_service, "approve_changeset", return_value=approval
                ) as approve_changeset:
                    approved_attempt = drafts.approve_draft(
                        state,
                        draft_id="draft-approval",
                        projection_state="current",
                        actor="Sean",
                        warning_ids=[],
                    )
                approve_changeset.assert_called_once_with(
                    changeset, new_preview, actor="Sean", warning_ids=[]
                )
                self.assertEqual(
                    approved_attempt["preview_attempt_id"], second_preview_attempt["id"]
                )
            finally:
                projection.close()
                state.close()

    def test_approval_endpoint_returns_attempt_without_apply_or_write(self):
        with tempfile.TemporaryDirectory(prefix="wbm-approval-endpoint-") as raw:
            projection, state, _, _, _ = self._preview_ready(Path(raw))
            workbook = Path(raw) / "fixture.xlsx"
            workbook_bytes = workbook.read_bytes()
            workbook_mtime = workbook.stat().st_mtime_ns
            approval = {
                "ok": True,
                "schemaVersion": "workbook-change-approval-1",
                "approvalFingerprint": "f" * 64,
            }
            try:
                with (
                    patch.object(main, "_workbook_state", return_value={"state": "current"}),
                    patch.object(main, "_projection_state", return_value={"state": "current"}),
                    patch.object(
                        drafts.workbook_service,
                        "approve_changeset",
                        return_value=approval,
                    ),
                ):
                    attempt = main.approve_draft_changeset(
                        "draft-approval",
                        main.ApprovalRequest(actor="Sean", warning_ids=["warn-1"]),
                        _lock=None,
                        conn=projection,
                        state_conn=state,
                    )
                self.assertEqual(attempt["manager_state"], "approved")
                self.assertEqual(
                    projection.execute(
                        "SELECT price FROM options WHERE option_id='opt_test'"
                    ).fetchone()["price"],
                    "100",
                )
                self.assertEqual(workbook.read_bytes(), workbook_bytes)
                self.assertEqual(workbook.stat().st_mtime_ns, workbook_mtime)
            finally:
                projection.close()
                state.close()

    def test_approval_ignores_unbound_competing_preview_attempt(self):
        with tempfile.TemporaryDirectory(prefix="wbm-approval-binding-") as raw:
            projection, state, changeset, preview, preview_attempt = (
                self._preview_ready(Path(raw))
            )
            competing_preview = {
                **preview,
                "changeSetId": "other-change-set",
                "semanticFingerprint": "other-semantic-fingerprint",
                "previewFingerprint": "9" * 64,
            }
            approval = {
                "ok": True,
                "schemaVersion": "workbook-change-approval-1",
                "approvalFingerprint": "8" * 64,
            }
            try:
                state.execute(
                    "INSERT INTO draft_preview_attempts(id, draft_id, change_set_id, "
                    "semantic_fingerprint, started_ts, completed_ts, artifact_kind, "
                    "result_json, workbook_identity_state, manager_state, "
                    "allowed_verbs_json) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        "competing-preview",
                        "draft-approval",
                        competing_preview["changeSetId"],
                        competing_preview["semanticFingerprint"],
                        "zzzz",
                        "zzzz",
                        "formal_preview",
                        json.dumps(competing_preview),
                        "unchanged",
                        "preview_ready",
                        json.dumps(["approve", "cancel"]),
                    ),
                )
                state.commit()
                with patch.object(
                    drafts.workbook_service,
                    "approve_changeset",
                    return_value=approval,
                ) as approve_changeset:
                    attempt = drafts.approve_draft(
                        state,
                        draft_id="draft-approval",
                        projection_state="current",
                        actor="Sean",
                        warning_ids=[],
                    )
                approve_changeset.assert_called_once_with(
                    changeset, preview, actor="Sean", warning_ids=[]
                )
                self.assertEqual(attempt["preview_attempt_id"], preview_attempt["id"])
            finally:
                projection.close()
                state.close()


class TestDurableApplyLifecycle(unittest.TestCase):
    def _approved(self, root: Path):
        helper = TestDurableApprovalLifecycle()
        projection, state, changeset, preview, preview_attempt = helper._preview_ready(root)
        approval = {
            "ok": True,
            "schemaVersion": "workbook-change-approval-1",
            "actor": "Sean",
            "changeSetId": changeset["changeSetId"],
            "semanticFingerprint": changeset["semanticFingerprint"],
            "previewFingerprint": preview["previewFingerprint"],
            "workbook": changeset["workbook"],
            "acceptedWarningIds": ["warn-1"],
            "approvalFingerprint": "b" * 64,
        }
        with patch.object(
            drafts.workbook_service, "approve_changeset", return_value=approval
        ):
            approval_attempt = drafts.approve_draft(
                state,
                draft_id="draft-approval",
                projection_state="current",
                actor="Sean",
                warning_ids=["warn-1"],
            )
        return (
            projection,
            state,
            root / "fixture.xlsx",
            changeset,
            preview,
            preview_attempt,
            approval,
            approval_attempt,
        )

    def test_apply_persists_before_writer_and_terminal_replay_is_idempotent(self):
        with tempfile.TemporaryDirectory(prefix="wbm-apply-lifecycle-") as raw:
            root = Path(raw)
            (
                projection,
                state,
                workbook,
                changeset,
                preview,
                preview_attempt,
                approval,
                approval_attempt,
            ) = self._approved(root)
            receipt = {
                "ok": True,
                "schemaVersion": "workbook-change-receipt-1",
                "changeSetId": changeset["changeSetId"],
                "semanticFingerprint": changeset["semanticFingerprint"],
                "previewFingerprint": preview["previewFingerprint"],
                "approvalFingerprint": approval["approvalFingerprint"],
                "status": "applied",
                "workbookState": "saved",
                "errors": [],
                "warnings": [],
                "backupPath": str(root / "backup.xlsx"),
                "logPath": str(root / "edit-log.jsonl"),
                "operationCoverage": {
                    "rawCount": 1,
                    "rawCovered": 1,
                    "preparedCount": 1,
                },
                "verification": {
                    "ok": True,
                    "preparedChecked": 1,
                    "preparedCount": 1,
                    "errors": [],
                },
                "schemaResult": {"status": "valid", "error_count": 0},
                "boolHygieneResult": {"status": "valid", "error_count": 0},
                "gateReminders": [],
                "createdAt": "2026-08-14T00:00:00+00:00",
            }

            def observe_durable_applying(*args, **kwargs):
                self.assertEqual(args, (workbook, changeset, preview, approval))
                active = state.execute(
                    "SELECT * FROM draft_apply_attempts WHERE draft_id='draft-approval'"
                ).fetchone()
                self.assertEqual(active["active"], 1)
                self.assertEqual(active["manager_state"], "applying")
                self.assertEqual(
                    state.execute(
                        "SELECT status FROM workflow_drafts WHERE id='draft-approval'"
                    ).fetchone()["status"],
                    "applying",
                )
                with self.assertRaises(drafts.DraftError) as active_ctx:
                    drafts.apply_draft(
                        state, draft_id="draft-approval", workbook_path=workbook
                    )
                self.assertEqual(active_ctx.exception.code, "apply_attempt_active")
                workbook.write_bytes(b"saved workbook bytes")
                return receipt

            try:
                with patch.object(
                    drafts.workbook_service,
                    "apply_changeset",
                    side_effect=observe_durable_applying,
                ) as apply_changeset:
                    attempt = drafts.apply_draft(
                        state, draft_id="draft-approval", workbook_path=workbook
                    )
                    replay = drafts.apply_draft(
                        state, draft_id="draft-approval", workbook_path=workbook
                    )

                apply_changeset.assert_called_once()
                self.assertEqual(replay, attempt)
                self.assertEqual(attempt["result"], receipt)
                self.assertEqual(attempt["artifact_kind"], "formal_receipt")
                self.assertEqual(attempt["manager_state"], "applied")
                self.assertEqual(attempt["allowed_verbs"], [])
                self.assertEqual(attempt["preview_attempt_id"], preview_attempt["id"])
                self.assertEqual(attempt["approval_attempt_id"], approval_attempt["id"])
                self.assertEqual(attempt["active"], 0)
                dbmod.set_meta(projection, "workbook_sha256", changeset["workbook"]["sha256"])
                dbmod.set_meta(projection, "workbook_mtime_ns", changeset["workbook"]["mtimeNs"])
                projection.commit()
                with patch.object(main.config, "DEFAULT_WORKBOOK", workbook):
                    self.assertEqual(main._workbook_state(projection)["state"], "stale")
                with self.assertRaisesRegex(
                    sqlite3.IntegrityError, "apply attempt artifacts are immutable"
                ):
                    state.execute(
                        "UPDATE draft_apply_attempts SET result_json='{}' WHERE id=?",
                        (attempt["id"],),
                    )
                state.rollback()
            finally:
                projection.close()
                state.close()

    def test_lifecycle_view_exposes_exact_artifacts_and_physical_context(self):
        with tempfile.TemporaryDirectory(prefix="wbm-lifecycle-view-") as raw:
            root = Path(raw)
            projection, state, workbook, changeset, preview, _, approval, _ = (
                self._approved(root)
            )
            retryable = {
                "ok": False,
                "status": "locked",
                "workbookState": "untouched",
            }
            try:
                with patch.object(
                    drafts.workbook_service,
                    "apply_changeset",
                    return_value=retryable,
                ):
                    apply_attempt = drafts.apply_draft(
                        state,
                        draft_id="draft-approval",
                        workbook_path=workbook,
                    )

                view = drafts.lifecycle_view(state, "draft-approval")
                self.assertEqual(view["context"]["model_keys"], ["stingray"])
                self.assertEqual(
                    view["context"]["physical_targets"],
                    [{
                        "operation_id": view["operations"][0]["id"],
                        "table": "options",
                        "family": "options",
                        "source_sheet": "stingray_options",
                        "source_row": 10,
                        "physical_key": '["opt_test"]',
                        "entity_key": {"option_id": "opt_test"},
                        "model_context": ["stingray"],
                    }],
                )
                self.assertEqual(
                    view["artifacts"]["changeset"]["artifact"], changeset
                )
                self.assertEqual(
                    view["artifacts"]["preview_attempts"][0]["result"], preview
                )
                self.assertEqual(
                    view["artifacts"]["approval_attempts"][0]["result"], approval
                )
                self.assertEqual(
                    view["artifacts"]["apply_attempts"][0], apply_attempt
                )
                self.assertIsNone(view["artifacts"]["cancellation"])
                self.assertEqual(view["artifacts"]["manual_resolutions"], [])

                drafts.cancel_draft(state, draft_id="draft-approval")
                cancelled = drafts.lifecycle_view(state, "draft-approval")
                self.assertEqual(
                    cancelled["artifacts"]["cancellation"]["status"],
                    "cancelled",
                )
                self.assertEqual(
                    cancelled["artifacts"]["apply_attempts"],
                    view["artifacts"]["apply_attempts"],
                )
            finally:
                projection.close()
                state.close()

    def test_apply_uses_real_shared_writer_on_disposable_workbook(self):
        with tempfile.TemporaryDirectory(prefix="wbm-real-apply-") as raw:
            root = Path(raw)
            workbook = make_workbook(root)
            changeset = make_valid_changeset(workbook)
            state = dbmod.connect(root / "state.sqlite3", foreign_keys=True)
            dbmod.init_durable_schema(state)
            state.execute(
                "INSERT INTO workflow_drafts(id, created_ts, updated_ts, actor, status, "
                "base_workbook_sha256, base_workbook_mtime_ns) "
                "VALUES('real-apply', 't', 't', 'Sean', 'changeset_emitted', ?, ?)",
                (changeset["workbook"]["sha256"], changeset["workbook"]["mtimeNs"]),
            )
            state.execute(
                "INSERT INTO draft_changesets(draft_id, created_ts, change_set_id, "
                "semantic_fingerprint, payload_json) VALUES(?,?,?,?,?)",
                (
                    "real-apply",
                    "t",
                    changeset["changeSetId"],
                    changeset["semanticFingerprint"],
                    json.dumps(changeset, sort_keys=True, separators=(",", ":")),
                ),
            )
            state.commit()
            try:
                with patch.object(
                    drafts.workbook_service.editor_ops,
                    "validate_workbook_schema",
                    return_value=[],
                ):
                    preview = drafts.preview_draft(
                        state,
                        draft_id="real-apply",
                        projection_state="current",
                        workbook_path=workbook,
                    )
                    self.assertEqual(preview["manager_state"], "preview_ready")
                    approval = drafts.approve_draft(
                        state,
                        draft_id="real-apply",
                        projection_state="current",
                        actor="Sean",
                        warning_ids=[],
                    )
                    self.assertEqual(approval["manager_state"], "approved")
                    attempt = drafts.apply_draft(
                        state,
                        draft_id="real-apply",
                        workbook_path=workbook,
                        log_path=root / "edit-log.jsonl",
                    )
                self.assertEqual(attempt["manager_state"], "applied")
                self.assertEqual(attempt["result"]["status"], "applied")
                self.assertEqual(attempt["result"]["workbookState"], "saved")
                self.assertTrue(Path(attempt["result"]["backupPath"]).exists())
                self.assertTrue((root / "edit-log.jsonl").exists())
                self.assertTrue(
                    drafts._verify_changeset_final_rows(workbook, changeset)["ok"]
                )
                self.assertNotEqual(
                    hashlib.sha256(workbook.read_bytes()).hexdigest(),
                    changeset["workbook"]["sha256"],
                )
            finally:
                state.close()

    def test_apply_mapping_is_explicit_and_fails_closed(self):
        cases = tuple(
            (status, "untouched", "stale", ["cancel"])
            for status in ("stale", "stale_before_save")
        ) + (
            ("locked", "untouched", "apply_retryable", ["retry_apply", "cancel"]),
        ) + tuple(
            (status, "untouched", "approval_confirmation_required", ["approve", "cancel"])
            for status in ("warning_confirmation_mismatch", "needs_confirmation")
        ) + tuple(
            (status, "untouched", "approval_repreview_required", ["retry_preview", "cancel"])
            for status in ("approval_invalid", "binding_mismatch", "warning_blocked")
        ) + tuple(
            (status, "untouched", "apply_rejected", ["cancel"])
            for status in (
                "invalid",
                "empty",
                "schema_validation_required",
                "readback_failed",
                "bool_hygiene_failed",
                "schema_failed",
            )
        ) + (
            ("workbook_restore_failed", "unknown", "workbook_state_unknown", ["resolve_manually"]),
            ("new_unrecognized_result", "saved", "workbook_state_unknown", ["resolve_manually"]),
        )
        for status, workbook_state, expected_state, expected_verbs in cases:
            result = {"status": status, "workbookState": workbook_state}
            with self.subTest(result=result):
                self.assertEqual(
                    drafts._map_apply_result(result, identity_state="unchanged"),
                    (expected_state, expected_verbs),
                )
        restored = {
            "status": "apply_verification_failed_rolled_back",
            "workbookState": "restored",
        }
        self.assertEqual(
            drafts._map_apply_result(
                restored,
                identity_state="unchanged",
                exact_formal_receipt=True,
            ),
            ("apply_restored_retryable", ["retry_apply", "cancel"]),
        )
        self.assertEqual(
            drafts._map_apply_result(restored, identity_state="unchanged"),
            ("workbook_state_unknown", ["resolve_manually"]),
        )

    def test_malformed_or_unbound_receipts_never_grant_apply_authority(self):
        with tempfile.TemporaryDirectory(prefix="wbm-receipt-binding-") as raw:
            projection, state, workbook, changeset, preview, _, approval, _ = self._approved(
                Path(raw)
            )
            try:
                minimal_applied = {
                    "ok": True,
                    "schemaVersion": "workbook-change-receipt-1",
                    "changeSetId": changeset["changeSetId"],
                    "semanticFingerprint": changeset["semanticFingerprint"],
                    "previewFingerprint": preview["previewFingerprint"],
                    "approvalFingerprint": approval["approvalFingerprint"],
                    "status": "applied",
                    "workbookState": "saved",
                }
                self.assertFalse(
                    drafts._is_exact_formal_receipt(
                        minimal_applied, changeset, preview, approval
                    )
                )
                self.assertFalse(
                    drafts._is_exact_applied_receipt(
                        minimal_applied, changeset, preview, approval
                    )
                )
                unbound_restored = {
                    **minimal_applied,
                    "ok": False,
                    "approvalFingerprint": "wrong",
                    "status": "apply_verification_failed_rolled_back",
                    "workbookState": "restored",
                    "errors": ["failed"],
                    "warnings": [],
                    "backupPath": "backup.xlsx",
                    "logPath": None,
                    "operationCoverage": None,
                    "verification": None,
                    "schemaResult": None,
                    "boolHygieneResult": None,
                    "gateReminders": [],
                    "createdAt": "2026-08-14T00:00:00+00:00",
                }
                self.assertFalse(
                    drafts._is_exact_formal_receipt(
                        unbound_restored, changeset, preview, approval
                    )
                )
                self.assertEqual(
                    drafts._map_apply_result(
                        unbound_restored,
                        identity_state="unchanged",
                        exact_formal_receipt=False,
                    ),
                    ("workbook_state_unknown", ["resolve_manually"]),
                )
                incomplete_proof = {
                    **unbound_restored,
                    "ok": True,
                    "approvalFingerprint": approval["approvalFingerprint"],
                    "status": "applied",
                    "workbookState": "saved",
                    "errors": [],
                    "operationCoverage": {},
                    "verification": {"ok": True},
                    "schemaResult": {"status": "valid", "error_count": 0},
                    "boolHygieneResult": {"status": "valid", "error_count": 0},
                }
                self.assertTrue(
                    drafts._is_exact_formal_receipt(
                        incomplete_proof, changeset, preview, approval
                    )
                )
                self.assertFalse(
                    drafts._is_exact_applied_receipt(
                        incomplete_proof, changeset, preview, approval
                    )
                )
                with patch.object(
                    drafts.workbook_service,
                    "apply_changeset",
                    return_value=minimal_applied,
                ):
                    attempt = drafts.apply_draft(
                        state,
                        draft_id="draft-approval",
                        workbook_path=workbook,
                    )
                self.assertEqual(attempt["artifact_kind"], "early_refusal")
                self.assertEqual(attempt["manager_state"], "workbook_state_unknown")
            finally:
                projection.close()
                state.close()

    def test_apply_exceptions_use_independently_observed_identity(self):
        cases = (
            (TimeoutError("locked"), False, "apply_retryable", ["retry_apply", "cancel"]),
            (ValueError("pre-writer refusal"), False, "apply_rejected", ["cancel"]),
            (ValueError("uncontained"), True, "workbook_state_unknown", ["resolve_manually"]),
        )
        for exception, remove_workbook, expected_state, expected_verbs in cases:
            with self.subTest(expected_state=expected_state):
                with tempfile.TemporaryDirectory(prefix="wbm-apply-exception-") as raw:
                    projection, state, workbook, *_ = self._approved(Path(raw))

                    def fail_apply(*_args, **_kwargs):
                        if remove_workbook:
                            workbook.unlink()
                        raise exception

                    try:
                        with patch.object(
                            drafts.workbook_service,
                            "apply_changeset",
                            side_effect=fail_apply,
                        ):
                            attempt = drafts.apply_draft(
                                state,
                                draft_id="draft-approval",
                                workbook_path=workbook,
                            )
                        self.assertEqual(attempt["manager_state"], expected_state)
                        self.assertEqual(attempt["allowed_verbs"], expected_verbs)
                    finally:
                        projection.close()
                        state.close()

    def test_retry_reuses_exact_artifacts_and_cancel_preserves_history(self):
        with tempfile.TemporaryDirectory(prefix="wbm-apply-retry-") as raw:
            root = Path(raw)
            projection, state, workbook, changeset, preview, _, approval, _ = (
                self._approved(root)
            )
            retryable = {
                "ok": False,
                "status": "locked",
                "workbookState": "untouched",
            }
            restored = {
                "ok": False,
                "schemaVersion": "workbook-change-receipt-1",
                "changeSetId": changeset["changeSetId"],
                "semanticFingerprint": changeset["semanticFingerprint"],
                "previewFingerprint": preview["previewFingerprint"],
                "approvalFingerprint": approval["approvalFingerprint"],
                "status": "apply_verification_failed_rolled_back",
                "workbookState": "restored",
                "errors": ["verification failed"],
                "warnings": [],
                "backupPath": str(root / "backup.xlsx"),
                "logPath": None,
                "operationCoverage": None,
                "verification": {"ok": False},
                "schemaResult": None,
                "boolHygieneResult": None,
                "gateReminders": [],
                "createdAt": "2026-08-14T00:00:00+00:00",
            }
            try:
                with patch.object(
                    drafts.workbook_service,
                    "apply_changeset",
                    side_effect=[retryable, restored],
                ) as apply_changeset:
                    first = drafts.apply_draft(
                        state, draft_id="draft-approval", workbook_path=workbook
                    )
                    second = drafts.apply_draft(
                        state, draft_id="draft-approval", workbook_path=workbook
                    )
                self.assertEqual(first["manager_state"], "apply_retryable")
                self.assertEqual(second["manager_state"], "apply_restored_retryable")
                self.assertEqual(apply_changeset.call_count, 2)
                for call in apply_changeset.call_args_list:
                    self.assertEqual(call.args, (workbook, changeset, preview, approval))

                cancelled = drafts.cancel_draft(state, draft_id="draft-approval")
                self.assertEqual(cancelled["status"], "cancelled")
                self.assertEqual(
                    state.execute(
                        "SELECT COUNT(*) c FROM draft_apply_attempts "
                        "WHERE draft_id='draft-approval'"
                    ).fetchone()["c"],
                    2,
                )
            finally:
                projection.close()
                state.close()

    def test_orphaned_applying_becomes_unknown_and_manual_resolution_is_durable(self):
        with tempfile.TemporaryDirectory(prefix="wbm-apply-recovery-") as raw:
            root = Path(raw)
            projection, state, workbook, changeset, preview, preview_attempt, approval, approval_attempt = self._approved(root)
            attempt_id = drafts._begin_apply_attempt(
                state,
                draft_id="draft-approval",
                changeset=changeset,
                preview_attempt=preview_attempt,
                preview=preview,
                approval_attempt=approval_attempt,
                approval=approval,
            )
            dbmod._write_manifest(
                state,
                store_kind="durable",
                migration_id="pass6b-recovery",
                source_sha256="source-sha",
                source_path=root / "state.sqlite3",
                archive_path=None,
                table_counts={},
            )
            state.commit()
            dbmod._write_manifest(
                projection,
                store_kind="projection",
                migration_id="pass6b-recovery",
                source_sha256="source-sha",
                source_path=root / "projection.sqlite3",
                archive_path=None,
                table_counts={},
            )
            projection.commit()
            state.close()
            projection.close()
            bootstrap = dbmod.bootstrap_storage(
                root / "state.sqlite3", root / "projection.sqlite3"
            )
            self.assertEqual(bootstrap["recovered_apply_attempts"], 1)
            state = dbmod.connect(root / "state.sqlite3", foreign_keys=True)
            attempt = state.execute(
                "SELECT * FROM draft_apply_attempts WHERE id=?", (attempt_id,)
            ).fetchone()
            self.assertEqual(attempt["manager_state"], "workbook_state_unknown")
            self.assertEqual(attempt["active"], 0)
            self.assertEqual(
                state.execute(
                    "SELECT status FROM workflow_drafts WHERE id='draft-approval'"
                ).fetchone()["status"],
                "workbook_state_unknown",
            )

            resolution = drafts.resolve_unknown_draft(
                state,
                draft_id="draft-approval",
                resolution="restored",
                workbook_path=workbook,
                actor="Sean",
                evidence={"recovery": "base hash independently confirmed"},
            )
            self.assertEqual(resolution["manager_state"], "manually_resolved_restored")
            self.assertEqual(resolution["observed_workbook_sha256"], changeset["workbook"]["sha256"])
            lifecycle = drafts.lifecycle_view(state, "draft-approval")
            self.assertEqual(
                lifecycle["artifacts"]["manual_resolutions"], [resolution]
            )
            with self.assertRaisesRegex(
                sqlite3.IntegrityError, "manual resolution artifacts are immutable"
            ):
                state.execute(
                    "DELETE FROM draft_manual_resolutions WHERE id=?",
                    (resolution["id"],),
                )
            state.rollback()
            state.close()


class TestDurableSchemaMigrations(unittest.TestCase):
    def test_v4_durable_upgrade_preserves_draft_and_verified_projection(self):
        with tempfile.TemporaryDirectory(prefix="wbm-schema5-upgrade-") as raw:
            root = Path(raw)
            state_path = root / "state.sqlite3"
            projection_path = root / "projection.sqlite3"
            state = dbmod.connect(state_path)
            projection = dbmod.connect(projection_path)
            try:
                dbmod.init_durable_schema(state)
                state.execute("DROP TABLE IF EXISTS draft_changesets")
                state.execute(
                    "INSERT INTO workflow_drafts(id, created_ts, updated_ts, status, "
                    "base_workbook_sha256, base_workbook_mtime_ns) "
                    "VALUES('sentinel-draft', 't', 't', 'draft', ?, '123')",
                    ("d" * 64,),
                )
                state.execute(
                    "INSERT INTO draft_operations(draft_id, created_ts, updated_ts, "
                    "table_name, family, source_sheet, physical_key, entity_key_json, "
                    "action, changed_fields_json) VALUES('sentinel-draft', 't', 't', "
                    "'options', 'options', 'stingray_options', '[\"opt_test\"]', "
                    "'{\"option_id\":\"opt_test\"}', 'update', "
                    "'{\"price\":{\"before\":100,\"after\":125}}')"
                )
                dbmod._write_manifest(
                    state,
                    store_kind="durable",
                    migration_id="durable-v4",
                    source_sha256="source-sha",
                    source_path=state_path,
                    archive_path=None,
                    table_counts={},
                )
                state.execute("UPDATE storage_manifest SET schema_version=4")
                state.commit()

                dbmod.init_projection_schema(projection)
                projection.execute(
                    "INSERT INTO models(src_sheet, src_row, model_key, active) "
                    "VALUES('model_master', 2, 'sentinel-model', 'True')"
                )
                dbmod._write_manifest(
                    projection,
                    store_kind="projection",
                    migration_id="import-verified-v3",
                    source_sha256="verified-sha",
                    source_path=Path("/tmp/source.xlsx"),
                    archive_path=None,
                    table_counts={"models": 1},
                )
                projection.execute("UPDATE storage_manifest SET schema_version=3")
                projection.commit()
            finally:
                state.close()
                projection.close()

            first = dbmod.bootstrap_storage(state_path, projection_path)
            self.assertEqual(first["status"], "ready")
            self.assertTrue(first["schema_upgraded"])
            state = dbmod.connect(state_path)
            projection = dbmod.connect(projection_path)
            try:
                self.assertIsNotNone(
                    state.execute(
                        "SELECT name FROM sqlite_master WHERE type='table' "
                        "AND name='draft_changesets'"
                    ).fetchone()
                )
                self.assertIsNotNone(
                    state.execute(
                        "SELECT name FROM sqlite_master WHERE type='table' "
                        "AND name='draft_preview_attempts'"
                    ).fetchone()
                )
                self.assertIsNotNone(
                    state.execute(
                        "SELECT name FROM sqlite_master WHERE type='table' "
                        "AND name='draft_approval_attempts'"
                    ).fetchone()
                )
                self.assertEqual(
                    state.execute(
                        "SELECT COUNT(*) c FROM draft_operations "
                        "WHERE draft_id='sentinel-draft'"
                    ).fetchone()["c"],
                    1,
                )
                self.assertEqual(
                    projection.execute(
                        "SELECT model_key FROM models WHERE model_key='sentinel-model'"
                    ).fetchone()["model_key"],
                    "sentinel-model",
                )
                self.assertEqual(
                    dbmod.storage_manifest(projection)["migration_id"],
                    "import-verified-v3",
                )
            finally:
                state.close()
                projection.close()

            second = dbmod.bootstrap_storage(state_path, projection_path)
            self.assertEqual(second["status"], "ready")
            self.assertFalse(second["schema_upgraded"])

    def test_v5_upgrade_preserves_emitted_changeset(self):
        with tempfile.TemporaryDirectory(prefix="wbm-schema6-upgrade-") as raw:
            state_path = Path(raw) / "state.sqlite3"
            state = dbmod.connect(state_path)
            try:
                dbmod.init_durable_schema(state)
                state.execute("DROP TABLE draft_preview_attempts")
                state.execute(
                    "INSERT INTO workflow_drafts(id, created_ts, updated_ts, status, "
                    "base_workbook_sha256, base_workbook_mtime_ns) "
                    "VALUES('emitted', 't', 't', 'changeset_emitted', ?, '123')",
                    ("e" * 64,),
                )
                state.execute(
                    "INSERT INTO draft_changesets(draft_id, created_ts, change_set_id, "
                    "semantic_fingerprint, payload_json) VALUES('emitted', 't', "
                    "'change-set-sentinel', 'fingerprint-sentinel', '{\"sentinel\":true}')"
                )
                dbmod._write_manifest(
                    state,
                    store_kind="durable",
                    migration_id="durable-v5",
                    source_sha256="source-sha",
                    source_path=state_path,
                    archive_path=None,
                    table_counts={},
                )
                state.execute("UPDATE storage_manifest SET schema_version=5")
                state.commit()
            finally:
                state.close()

            manifest = dbmod._read_manifest_path(state_path)
            self.assertTrue(dbmod._upgrade_durable_store(state_path, manifest))
            state = dbmod.connect(state_path)
            try:
                stored = state.execute(
                    "SELECT * FROM draft_changesets WHERE draft_id='emitted'"
                ).fetchone()
                self.assertEqual(stored["change_set_id"], "change-set-sentinel")
                self.assertEqual(json.loads(stored["payload_json"]), {"sentinel": True})
                self.assertIsNotNone(
                    state.execute(
                        "SELECT name FROM sqlite_master WHERE type='table' "
                        "AND name='draft_preview_attempts'"
                    ).fetchone()
                )
                self.assertIsNotNone(
                    state.execute(
                        "SELECT name FROM sqlite_master WHERE type='table' "
                        "AND name='draft_approval_attempts'"
                    ).fetchone()
                )
                self.assertIsNotNone(
                    state.execute(
                        "SELECT name FROM sqlite_master WHERE type='table' "
                        "AND name='draft_apply_attempts'"
                    ).fetchone()
                )
                self.assertIsNotNone(
                    state.execute(
                        "SELECT name FROM sqlite_master WHERE type='table' "
                        "AND name='draft_manual_resolutions'"
                    ).fetchone()
                )
                self.assertIsNotNone(
                    state.execute(
                        "SELECT name FROM sqlite_master WHERE type='table' "
                        "AND name='draft_asset_resolutions'"
                    ).fetchone()
                )
                self.assertEqual(
                    dbmod.storage_manifest(state)["schema_version"],
                    dbmod.SCHEMA_VERSION,
                )
            finally:
                state.close()

    def test_v6_upgrade_preserves_preview_attempt(self):
        with tempfile.TemporaryDirectory(prefix="wbm-schema7-upgrade-") as raw:
            state_path = Path(raw) / "state.sqlite3"
            state = dbmod.connect(state_path)
            try:
                dbmod.init_durable_schema(state)
                state.execute("DROP TABLE draft_approval_attempts")
                state.execute(
                    "INSERT INTO workflow_drafts(id, created_ts, updated_ts, status, "
                    "base_workbook_sha256, base_workbook_mtime_ns) "
                    "VALUES('previewed', 't', 't', 'preview_ready', ?, '123')",
                    ("f" * 64,),
                )
                state.execute(
                    "INSERT INTO draft_changesets(draft_id, created_ts, change_set_id, "
                    "semantic_fingerprint, payload_json) VALUES('previewed', 't', "
                    "'change-set-preview', 'semantic-preview', '{\"sentinel\":true}')"
                )
                state.execute(
                    "INSERT INTO draft_preview_attempts(id, draft_id, change_set_id, "
                    "semantic_fingerprint, started_ts, completed_ts, artifact_kind, "
                    "result_json, workbook_identity_state, manager_state, "
                    "allowed_verbs_json) VALUES('preview-attempt', 'previewed', "
                    "'change-set-preview', 'semantic-preview', 't', 't', "
                    "'formal_preview', '{\"previewFingerprint\":\"sentinel\"}', "
                    "'unchanged', 'preview_ready', '[\"approve\",\"cancel\"]')"
                )
                dbmod._write_manifest(
                    state,
                    store_kind="durable",
                    migration_id="durable-v6",
                    source_sha256="source-sha",
                    source_path=state_path,
                    archive_path=None,
                    table_counts={},
                )
                state.execute("UPDATE storage_manifest SET schema_version=6")
                state.commit()
            finally:
                state.close()

            manifest = dbmod._read_manifest_path(state_path)
            self.assertTrue(dbmod._upgrade_durable_store(state_path, manifest))
            state = dbmod.connect(state_path)
            try:
                stored = state.execute(
                    "SELECT * FROM draft_preview_attempts WHERE id='preview-attempt'"
                ).fetchone()
                self.assertEqual(stored["manager_state"], "preview_ready")
                self.assertEqual(
                    json.loads(stored["result_json"]),
                    {"previewFingerprint": "sentinel"},
                )
                self.assertIsNotNone(
                    state.execute(
                        "SELECT name FROM sqlite_master WHERE type='table' "
                        "AND name='draft_approval_attempts'"
                    ).fetchone()
                )
                self.assertIsNotNone(
                    state.execute(
                        "SELECT name FROM sqlite_master WHERE type='table' "
                        "AND name='draft_apply_attempts'"
                    ).fetchone()
                )
                self.assertIsNotNone(
                    state.execute(
                        "SELECT name FROM sqlite_master WHERE type='table' "
                        "AND name='draft_asset_resolutions'"
                    ).fetchone()
                )
                self.assertEqual(
                    dbmod.storage_manifest(state)["schema_version"],
                    dbmod.SCHEMA_VERSION,
                )
            finally:
                state.close()

    def test_v7_upgrade_preserves_approval_attempt_and_adds_apply_recovery(self):
        with tempfile.TemporaryDirectory(prefix="wbm-schema8-upgrade-") as raw:
            state_path = Path(raw) / "state.sqlite3"
            state = dbmod.connect(state_path)
            try:
                dbmod.init_durable_schema(state)
                state.execute("DROP TABLE draft_asset_resolutions")
                state.execute("DROP TABLE draft_manual_resolutions")
                state.execute("DROP TABLE draft_apply_attempts")
                state.execute(
                    "INSERT INTO workflow_drafts(id, created_ts, updated_ts, status, "
                    "base_workbook_sha256, base_workbook_mtime_ns) "
                    "VALUES('approved', 't', 't', 'approved', ?, '123')",
                    ("a" * 64,),
                )
                state.execute(
                    "INSERT INTO draft_changesets(draft_id, created_ts, change_set_id, "
                    "semantic_fingerprint, payload_json) VALUES('approved', 't', "
                    "'change-set-approved', 'semantic-approved', '{\"sentinel\":true}')"
                )
                state.execute(
                    "INSERT INTO draft_preview_attempts(id, draft_id, change_set_id, "
                    "semantic_fingerprint, started_ts, completed_ts, artifact_kind, "
                    "result_json, workbook_identity_state, manager_state, "
                    "allowed_verbs_json) VALUES('preview-approved', 'approved', "
                    "'change-set-approved', 'semantic-approved', 't', 't', "
                    "'formal_preview', '{\"previewFingerprint\":\"preview\"}', "
                    "'unchanged', 'preview_ready', '[\"approve\",\"cancel\"]')"
                )
                state.execute(
                    "INSERT INTO draft_approval_attempts(id, draft_id, preview_attempt_id, "
                    "change_set_id, semantic_fingerprint, preview_fingerprint, "
                    "warning_ids_json, started_ts, completed_ts, artifact_kind, "
                    "result_json, manager_state, allowed_verbs_json) VALUES("
                    "'approval-sentinel', 'approved', 'preview-approved', "
                    "'change-set-approved', 'semantic-approved', 'preview', '[]', "
                    "'t', 't', 'formal_approval', '{\"approvalFingerprint\":\"approval\"}', "
                    "'approved', '[\"apply\",\"cancel\"]')"
                )
                dbmod._write_manifest(
                    state,
                    store_kind="durable",
                    migration_id="durable-v7",
                    source_sha256="source-sha",
                    source_path=state_path,
                    archive_path=None,
                    table_counts={},
                )
                state.execute("UPDATE storage_manifest SET schema_version=7")
                state.commit()
            finally:
                state.close()

            manifest = dbmod._read_manifest_path(state_path)
            self.assertTrue(dbmod._upgrade_durable_store(state_path, manifest))
            state = dbmod.connect(state_path)
            try:
                self.assertEqual(
                    state.execute(
                        "SELECT manager_state FROM draft_approval_attempts "
                        "WHERE id='approval-sentinel'"
                    ).fetchone()["manager_state"],
                    "approved",
                )
                self.assertIsNotNone(
                    state.execute(
                        "SELECT name FROM sqlite_master WHERE type='table' "
                        "AND name='draft_apply_attempts'"
                    ).fetchone()
                )
                self.assertIsNotNone(
                    state.execute(
                        "SELECT name FROM sqlite_master WHERE type='table' "
                        "AND name='draft_manual_resolutions'"
                    ).fetchone()
                )
                self.assertIsNotNone(
                    state.execute(
                        "SELECT name FROM sqlite_master WHERE type='table' "
                        "AND name='draft_asset_resolutions'"
                    ).fetchone()
                )
                self.assertEqual(
                    dbmod.storage_manifest(state)["schema_version"],
                    dbmod.SCHEMA_VERSION,
                )
            finally:
                state.close()


if __name__ == "__main__":
    unittest.main()
