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
            finally:
                projection.close()
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
                self.assertEqual(dbmod.storage_manifest(state)["schema_version"], 7)
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
                self.assertEqual(dbmod.storage_manifest(state)["schema_version"], 7)
            finally:
                state.close()


if __name__ == "__main__":
    unittest.main()
