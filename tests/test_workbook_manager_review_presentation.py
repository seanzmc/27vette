"""Checkpoint 6: Review & Apply presentation recovery.

§14.2: the backend owns semantic operation summaries (or supplies enough typed
metadata for one shared formatter). §14.3: Review & Apply presents human entity
summaries, impact/affected models, exact lifecycle stage/next action, and
expandable technical evidence. §13.5: operation results persist beside their
initiating operation until dismissed or superseded by a named state transition.
§4.3: human labels lead; canonical IDs stay expandable, never renamed.
"""

from __future__ import annotations

import hashlib
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND = REPO_ROOT / "workbook-manager" / "backend"
for path in (str(BACKEND), str(REPO_ROOT / "scripts")):
    if path not in sys.path:
        sys.path.insert(0, path)

from app import drafts  # noqa: E402
from test_workbook_manager_changeset_lifecycle import (  # noqa: E402
    TestDurablePreviewLifecycle,
)


REVIEW_VERSION = "workbook-manager-review-summary-1"


def _emitted(root: Path):
    helper = TestDurablePreviewLifecycle()
    projection, state, workbook, changeset = helper._emitted_draft(
        root, draft_id="draft-review"
    )
    return projection, state, workbook, changeset


class TestReviewSummaryContract(unittest.TestCase):
    """§14.2 typed semantic summaries derived backend-side, additive."""

    def test_lifecycle_view_carries_typed_review_summary(self):
        with tempfile.TemporaryDirectory(prefix="wbm-review-summary-") as raw:
            projection, state, workbook, changeset = _emitted(Path(raw))
            try:
                view = drafts.lifecycle_view(state, "draft-review")
                review = view["review"]
                self.assertEqual(review["schema_version"], REVIEW_VERSION)
                self.assertEqual(review["affected_models"], ["stingray"])

                groups = review["groups"]
                self.assertEqual(len(groups), 1)
                group = groups[0]
                self.assertEqual(group["model_key"], "stingray")
                self.assertEqual(group["entity_type"], "option")

                item = group["entities"][0]
                self.assertEqual(item["operation_count"], 1)
                self.assertEqual(item["entity_id"], "opt_test")
                self.assertEqual(item["entity_label"], "TST Original")
                self.assertEqual(item["actions"], ["update"])
                # One shared, backend-owned human summary (§14.2 grammar:
                # "<label>: <Field> changed from <before> to <after>").
                self.assertEqual(
                    item["summaries"],
                    ["TST Original: Price changed from 100 to 150"],
                )
                # Exact stored evidence stays reachable but separate (§14.3.5).
                self.assertEqual(item["operation_ids"], [view["operations"][0]["id"]])
                self.assertEqual(item["technical"]["table_name"], "options")
                self.assertEqual(
                    item["technical"]["source_sheet"], "stingray_options"
                )
            finally:
                projection.close()
                state.close()

    def test_review_groups_coalesce_operations_by_model_and_entity(self):
        with tempfile.TemporaryDirectory(prefix="wbm-review-group-") as raw:
            projection, state, workbook, changeset = _emitted(Path(raw))
            try:
                # The helper's draft is already locked (changeset_emitted);
                # reopen it as mutable with its real workbook binding to add a
                # second, different-entity operation.
                state.execute(
                    "UPDATE workflow_drafts SET status='draft' "
                    "WHERE id='draft-review'"
                )
                state.commit()
                projection.execute(
                    "INSERT INTO sheet_registry(src_sheet, src_row, src_family, "
                    "physical_key, model_context, model_key, source_role, "
                    "sheet_name, active) VALUES(?,?,?,?,?,?,?,?,?)",
                    ("model_workbook_sources", 3, "model_workbook_sources",
                     '["stingray","status_sheet"]', '["stingray"]', "stingray",
                     "status_sheet", "stingray_ovs", "True"),
                )
                projection.execute(
                    "INSERT INTO option_availability(src_sheet, src_row, "
                    "src_family, physical_key, model_context, model_id, "
                    "option_id, variant_id, status) VALUES(?,?,?,?,?,?,?,?,?)",
                    ("stingray_ovs", 2, "ovs", '["opt_test","1lt"]',
                     '["stingray"]', "stingray", "opt_test", "1lt", "available"),
                )
                projection.commit()
                drafts.save_operation(
                    projection, state, projection_state="current",
                    base_workbook_sha256=hashlib.sha256(
                        workbook.read_bytes()
                    ).hexdigest(),
                    base_workbook_mtime_ns=str(workbook.stat().st_mtime_ns),
                    draft_id="draft-review", table="option_availability",
                    model_id="stingray", op="update",
                    key={"option_id": "opt_test", "variant_id": "1lt"},
                    record={"status": "standard"},
                )

                view = drafts.lifecycle_view(state, "draft-review")
                groups = view["review"]["groups"]
                # §6.1: an availability (OVS) row change is semantically an
                # option-entity change, so both operations land in one option
                # group with distinct per-entity items.
                self.assertEqual(
                    [(g["entity_type"], len(g["entities"])) for g in groups],
                    [("option", 2)],
                )
                ovs_item = groups[0]["entities"][1]
                self.assertEqual(ovs_item["entity_id"], "opt_test / 1lt")
                self.assertEqual(ovs_item["summaries"], [
                    "opt_test / 1lt: Availability changed from available to standard",
                ])
                self.assertEqual(
                    ovs_item["technical"]["source_sheet"], "stingray_ovs"
                )
            finally:
                projection.close()
                state.close()

    def test_review_entities_carry_connected_destinations(self):
        """§14.3: review links open connected detail without losing context."""
        with tempfile.TemporaryDirectory(prefix="wbm-review-dest-") as raw:
            projection, state, workbook, changeset = _emitted(Path(raw))
            try:
                view = drafts.lifecycle_view(state, "draft-review")
                item = view["review"]["groups"][0]["entities"][0]
                self.assertEqual(item["destination"], {
                    "workspace": "options",
                    "entity_type": "option",
                    "entity_id": "opt_test",
                })
            finally:
                projection.close()
                state.close()


class TestReviewTerminologyAndResults(unittest.TestCase):
    """§12 lifecycle language plus §13.5 persistent result states."""

    def test_review_apply_source_uses_spec_operator_terminology(self):
        source = (
            REPO_ROOT / "workbook-manager" / "frontend" / "src" /
            "components" / "ChangesSync.jsx"
        ).read_text(encoding="utf-8")
        # §14.4 lifecycle language: human state, not raw machine states.
        self.assertIn("operatorLifecycle", source)
        self.assertIn("Draft locked for validation", source)
        self.assertIn("Validated against the workbook", source)
        self.assertIn("Validated changes approved", source)
        self.assertIn("Approved changes written", source)
        self.assertIn("Draft cancelled, audit record kept", source)
        self.assertIn("Manual recovery required", source)

    def test_operation_results_persist_until_state_transition(self):
        source = (
            REPO_ROOT / "workbook-manager" / "frontend" / "src" /
            "components" / "ChangesSync.jsx"
        ).read_text(encoding="utf-8")
        # §13.5: results persist beside their operation until dismissed or a
        # named state transition supersedes them; an unrelated refresh cannot
        # clear them. Pinned lifecycle-derived results plus an explicit
        # dismissal set implement that contract.
        self.assertIn("dismissedResults", source)
        self.assertIn("pinnedResults", source)
        self.assertIn("localStorage", source)
        for expected in (
            "Draft validation passed. Nothing was written.",
            "Validated changes were approved. Nothing was written.",
            "Draft cancelled. Its audit record was kept.",
            "Manual recovery was recorded",
        ):
            self.assertIn(expected, source)

    def test_persistent_draft_tray_uses_operator_lifecycle_language(self):
        source = (
            REPO_ROOT / "workbook-manager" / "frontend" / "src" / "App.jsx"
        ).read_text(encoding="utf-8")
        self.assertIn("operatorLifecycle", source)
        self.assertIn("operatorLifecycle[draftLifecycle?.draft?.status]", source)

    def test_apply_completion_remains_visible_while_projection_is_stale(self):
        source = (
            REPO_ROOT / "workbook-manager" / "frontend" / "src" / "App.jsx"
        ).read_text(encoding="utf-8")
        self.assertIn("reviewAvailable", source)
        self.assertIn("ready || reviewAvailable", source)
        self.assertIn("savedTerminalReview", source)

    def test_advanced_leads_with_durable_workflow_history_and_discloses_legacy(self):
        """HIST-01–04: current workflow evidence is the primary history UI."""
        history_source = (
            REPO_ROOT / "workbook-manager" / "frontend" / "src" /
            "components" / "HistoryView.jsx"
        ).read_text(encoding="utf-8")
        app_source = (
            REPO_ROOT / "workbook-manager" / "frontend" / "src" / "App.jsx"
        ).read_text(encoding="utf-8")
        api_source = (
            REPO_ROOT / "workbook-manager" / "frontend" / "src" / "api.js"
        ).read_text(encoding="utf-8")

        self.assertIn("Workflow history", history_source)
        self.assertIn("Legacy staging history", history_source)
        self.assertIn("technical_evidence", history_source)
        self.assertIn("Open exact draft", history_source)
        self.assertIn("api.workflowHistory", history_source)
        self.assertIn("workflowHistory:", api_source)
        self.assertIn("onOpenDraft", app_source)
        self.assertIn("await refreshDraft(id)", app_source)
        self.assertIn("ready || status", app_source)
        self.assertIn('["changes", "advanced"].includes(id)', app_source)


if __name__ == "__main__":
    unittest.main()
