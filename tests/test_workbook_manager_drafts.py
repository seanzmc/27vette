"""Pass 5 durable-draft behavior for Workbook Manager."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND = REPO_ROOT / "workbook-manager" / "backend"
for path in (str(BACKEND), str(REPO_ROOT / "scripts")):
    if path not in sys.path:
        sys.path.insert(0, path)

from app import db as dbmod, drafts  # noqa: E402


class TestDurableDraftSchema(unittest.TestCase):
    def test_draft_tables_exist_only_in_durable_state(self):
        with tempfile.TemporaryDirectory(prefix="wbm-draft-schema-") as raw:
            root = Path(raw)
            projection = dbmod.connect(root / "projection.sqlite3")
            state = dbmod.connect(root / "state.sqlite3", foreign_keys=True)
            try:
                dbmod.init_projection_schema(projection)
                dbmod.init_durable_schema(state)
                durable_tables = {
                    row["name"]
                    for row in state.execute(
                        "SELECT name FROM sqlite_master WHERE type='table'"
                    )
                }
                projection_tables = {
                    row["name"]
                    for row in projection.execute(
                        "SELECT name FROM sqlite_master WHERE type='table'"
                    )
                }
                self.assertTrue(
                    {"workflow_drafts", "draft_operations"} <= durable_tables
                )
                self.assertFalse(
                    {"workflow_drafts", "draft_operations"} & projection_tables
                )
            finally:
                projection.close()
                state.close()


class TestDurableDraftEditing(unittest.TestCase):
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

    def test_operation_plan_is_atomic_and_idempotent(self):
        with tempfile.TemporaryDirectory(prefix="wbm-draft-plan-") as raw:
            projection, state = self._stores(Path(raw))
            try:
                projection.execute(
                    "INSERT INTO options(src_sheet, src_row, src_family, physical_key, "
                    "model_context, model_id, option_id, rpo, option_name, price, active) "
                    "VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                    ("stingray_options", 11, "options", '[\"opt_other\"]',
                     '[\"stingray\"]', "stingray", "opt_other", "OTH", "Other",
                     "200", "True"),
                )
                projection.commit()
                context = {
                    "projection_state": "current",
                    "base_workbook_sha256": "sha",
                    "base_workbook_mtime_ns": "1",
                    "draft_id": "draft-plan",
                    "session_id": "browser",
                    "actor": "test",
                }
                plan = [
                    {
                        "table": "options", "model_id": "stingray", "op": "update",
                        "key": {"option_id": "opt_test"},
                        "record": {"price": "125"},
                    },
                    {
                        "table": "options", "model_id": "stingray", "op": "update",
                        "key": {"option_id": "opt_other"},
                        "record": {"price": "250"},
                    },
                ]

                first = drafts.save_operation_plan(projection, state, operations=plan, **context)
                second = drafts.save_operation_plan(projection, state, operations=plan, **context)
                self.assertEqual(
                    [operation["id"] for operation in second],
                    [operation["id"] for operation in first],
                )
                self.assertEqual(len(drafts.list_operations(state, "draft-plan")), 2)

                with self.assertRaises(drafts.DraftError):
                    drafts.save_operation_plan(
                        projection,
                        state,
                        operations=[
                            {
                                "table": "options", "model_id": "stingray", "op": "update",
                                "key": {"option_id": "opt_test"},
                                "record": {"price": "999"},
                            },
                            {
                                "table": "options", "model_id": "stingray", "op": "update",
                                "key": {"option_id": "missing"},
                                "record": {"price": "1"},
                            },
                        ],
                        **context,
                    )
                stored = drafts.list_operations(state, "draft-plan")
                self.assertEqual(stored[0]["final"]["price"], "125")
                self.assertEqual(stored[1]["final"]["price"], "250")
            finally:
                projection.close()
                state.close()

    def test_operation_plan_add_replay_coalesces_to_the_stored_row(self):
        """Codex P2 (PR 69): a retried add-based plan must not fail with
        duplicate_record when the first attempt committed but its response
        was lost; identical replay coalesces to the same durable row."""
        with tempfile.TemporaryDirectory(prefix="wbm-draft-plan-add-") as raw:
            projection, state = self._stores(Path(raw))
            try:
                context = {
                    "projection_state": "current",
                    "base_workbook_sha256": "sha",
                    "base_workbook_mtime_ns": "1",
                    "draft_id": "draft-plan-add",
                    "session_id": "browser",
                    "actor": "test",
                }
                plan = [
                    {
                        "table": "options", "model_id": "stingray", "op": "add",
                        "key": {"option_id": "opt_guided"},
                        "record": {
                            "option_id": "opt_guided", "rpo": "GID",
                            "option_name": "Guided Option", "price": "350",
                            "section_id": "sec_ext_001", "selectable": "True",
                            "display_order": "45", "active": "True",
                        },
                    },
                ]

                first = drafts.save_operation_plan(
                    projection, state, operations=plan, **context
                )
                second = drafts.save_operation_plan(
                    projection, state, operations=plan, **context
                )
                self.assertEqual(
                    [operation["id"] for operation in second],
                    [operation["id"] for operation in first],
                )
                self.assertEqual(second[0]["action"], "add")
                self.assertEqual(second[0]["final"]["option_name"], "Guided Option")
                self.assertEqual(
                    len(drafts.list_operations(state, "draft-plan-add")), 1
                )

                with self.assertRaises(drafts.DraftError) as ctx:
                    drafts.save_operation_plan(
                        projection,
                        state,
                        operations=[
                            {
                                "table": "options", "model_id": "stingray",
                                "op": "add",
                                "key": {"option_id": "opt_guided"},
                                "record": {
                                    "option_id": "opt_guided", "rpo": "GID",
                                    "option_name": "Renamed", "price": "350",
                                    "section_id": "sec_ext_001",
                                    "selectable": "True",
                                    "display_order": "45", "active": "True",
                                },
                            },
                        ],
                        **context,
                    )
                self.assertEqual(ctx.exception.code, "duplicate_record")
                self.assertEqual(
                    len(drafts.list_operations(state, "draft-plan-add")), 1
                )
            finally:
                projection.close()
                state.close()

    def test_draft_creation_requires_current_projection(self):
        with tempfile.TemporaryDirectory(prefix="wbm-draft-state-") as raw:
            root = Path(raw)
            projection = dbmod.connect(root / "projection.sqlite3")
            state = dbmod.connect(root / "state.sqlite3", foreign_keys=True)
            try:
                dbmod.init_projection_schema(projection)
                dbmod.init_durable_schema(state)
                with self.assertRaises(drafts.DraftError) as ctx:
                    drafts.save_operation(
                        projection,
                        state,
                        projection_state="stale",
                        base_workbook_sha256="sha",
                        base_workbook_mtime_ns="1",
                        draft_id="draft-1",
                        table="options",
                        model_id="stingray",
                        op="update",
                        key={"option_id": "opt_test"},
                        record={"option_name": "Changed"},
                    )
                self.assertEqual(ctx.exception.code, "projection_not_current")
                self.assertEqual(
                    state.execute("SELECT COUNT(*) c FROM workflow_drafts").fetchone()["c"],
                    0,
                )
            finally:
                projection.close()
                state.close()

    def test_sequential_same_row_updates_coalesce_without_mutating_projection(self):
        with tempfile.TemporaryDirectory(prefix="wbm-draft-coalesce-") as raw:
            projection, state = self._stores(Path(raw))
            try:
                first = drafts.save_operation(
                    projection, state, projection_state="current",
                    base_workbook_sha256="sha", base_workbook_mtime_ns="1",
                    draft_id="draft-1", table="options", model_id="stingray",
                    op="update", key={"option_id": "opt_test"},
                    record={"option_name": "First"},
                )
                second = drafts.save_operation(
                    projection, state, projection_state="current",
                    base_workbook_sha256="sha", base_workbook_mtime_ns="1",
                    draft_id="draft-1", table="options", model_id="stingray",
                    op="update", key={"option_id": "opt_test"},
                    record={"price": "125"},
                )

                self.assertEqual(first["id"], second["id"])
                self.assertEqual(second["action"], "update")
                self.assertEqual(second["source_sheet"], "stingray_options")
                self.assertEqual(second["physical_key"], '["opt_test"]')
                self.assertEqual(second["changed_fields"], {
                    "option_name": {"before": "Original", "after": "First"},
                    "price": {"before": "100", "after": "125"},
                })
                self.assertEqual(len(drafts.list_operations(state, "draft-1")), 1)
                projected = projection.execute(
                    "SELECT option_name, price FROM options WHERE model_id='stingray' "
                    "AND option_id='opt_test'"
                ).fetchone()
                self.assertEqual(
                    dict(projected), {"option_name": "Original", "price": "100"}
                )
                self.assertEqual(
                    state.execute("SELECT COUNT(*) c FROM pending_changes").fetchone()["c"], 0
                )
                self.assertEqual(
                    state.execute("SELECT COUNT(*) c FROM change_history").fetchone()["c"], 0
                )
            finally:
                projection.close()
                state.close()

    def test_reverting_to_projection_value_removes_noop_operation(self):
        with tempfile.TemporaryDirectory(prefix="wbm-draft-revert-") as raw:
            projection, state = self._stores(Path(raw))
            try:
                drafts.save_operation(
                    projection, state, projection_state="current",
                    base_workbook_sha256="sha", base_workbook_mtime_ns="1",
                    draft_id="draft-1", table="options", model_id="stingray",
                    op="update", key={"option_id": "opt_test"},
                    record={"option_name": "Changed"},
                )
                reverted = drafts.save_operation(
                    projection, state, projection_state="current",
                    base_workbook_sha256="sha", base_workbook_mtime_ns="1",
                    draft_id="draft-1", table="options", model_id="stingray",
                    op="update", key={"option_id": "opt_test"},
                    record={"option_name": "Original"},
                )
                self.assertIsNone(reverted)
                self.assertEqual(drafts.list_operations(state, "draft-1"), [])
                self.assertEqual(
                    state.execute(
                        "SELECT COUNT(*) c FROM workflow_drafts WHERE id='draft-1'"
                    ).fetchone()["c"],
                    0,
                )
            finally:
                projection.close()
                state.close()

    def test_unchanged_update_does_not_leave_an_empty_draft(self):
        with tempfile.TemporaryDirectory(prefix="wbm-draft-unchanged-") as raw:
            projection, state = self._stores(Path(raw))
            try:
                unchanged = drafts.save_operation(
                    projection, state, projection_state="current",
                    base_workbook_sha256="sha", base_workbook_mtime_ns="1",
                    draft_id="draft-unchanged", table="options",
                    model_id="stingray", op="update",
                    key={"option_id": "opt_test"},
                    record={"option_name": "Original", "price": "100"},
                )
                self.assertIsNone(unchanged)
                self.assertEqual(drafts.list_operations(state, "draft-unchanged"), [])
                self.assertEqual(
                    state.execute(
                        "SELECT COUNT(*) c FROM workflow_drafts "
                        "WHERE id='draft-unchanged'"
                    ).fetchone()["c"],
                    0,
                )
            finally:
                projection.close()
                state.close()

    def test_discard_mutable_operation_preserves_unrelated_intent(self):
        """DRAFT-01/02: discard removes intent, never compensates for it."""
        with tempfile.TemporaryDirectory(prefix="wbm-draft-discard-") as raw:
            projection, state = self._stores(Path(raw))
            try:
                projection.execute(
                    "INSERT INTO options(src_sheet, src_row, src_family, physical_key, "
                    "model_context, model_id, option_id, rpo, option_name, price, active) "
                    "VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                    ("stingray_options", 11, "options", '[\"opt_other\"]',
                     '[\"stingray\"]', "stingray", "opt_other", "OTH", "Other",
                     "200", "True"),
                )
                projection.commit()
                first = drafts.save_operation(
                    projection, state, projection_state="current",
                    base_workbook_sha256="sha", base_workbook_mtime_ns="1",
                    draft_id="draft-discard", table="options", model_id="stingray",
                    op="update", key={"option_id": "opt_test"},
                    record={"option_name": "Changed"},
                )
                second = drafts.save_operation(
                    projection, state, projection_state="current",
                    base_workbook_sha256="sha", base_workbook_mtime_ns="1",
                    draft_id="draft-discard", table="options", model_id="stingray",
                    op="update", key={"option_id": "opt_other"},
                    record={"price": "250"},
                )

                result = drafts.discard_operation(
                    state, draft_id="draft-discard", operation_id=first["id"]
                )

                self.assertEqual(result["discarded_operation_id"], first["id"])
                self.assertEqual(result["remaining_operation_count"], 1)
                self.assertEqual(
                    [row["id"] for row in drafts.list_operations(state, "draft-discard")],
                    [second["id"]],
                )
                self.assertEqual(
                    projection.execute(
                        "SELECT option_name FROM options WHERE option_id='opt_test'"
                    ).fetchone()["option_name"],
                    "Original",
                )

                empty = drafts.discard_operation(
                    state, draft_id="draft-discard", operation_id=second["id"]
                )
                self.assertTrue(empty["draft_removed"])
                self.assertIsNone(state.execute(
                    "SELECT 1 FROM workflow_drafts WHERE id='draft-discard'"
                ).fetchone())
            finally:
                projection.close()
                state.close()

    def test_discard_final_operation_preserves_operational_asset_ignore(self):
        """A no-workbook ignore keeps its mutable draft after workbook intent is removed."""
        with tempfile.TemporaryDirectory(prefix="wbm-draft-ignore-discard-") as raw:
            projection, state = self._stores(Path(raw))
            try:
                evidence = {
                    "item_id": "unparseable:readme",
                    "resolution_kind": "ignore",
                    "reconciliation_sha256": "reconciliation",
                    "media_inventory_sha256": "inventory",
                    "workbook_sha256": "sha",
                    "media_url": "https://example.test/readme.txt",
                }
                drafts.save_asset_ignore(
                    state,
                    draft_id="draft-ignore-discard",
                    session_id="session",
                    actor="reviewer",
                    base_workbook_sha256="sha",
                    base_workbook_mtime_ns="1",
                    evidence=evidence,
                )
                operation = drafts.save_operation(
                    projection,
                    state,
                    projection_state="current",
                    base_workbook_sha256="sha",
                    base_workbook_mtime_ns="1",
                    draft_id="draft-ignore-discard",
                    table="options",
                    model_id="stingray",
                    op="update",
                    key={"option_id": "opt_test"},
                    record={"option_name": "Changed"},
                )

                result = drafts.discard_operation(
                    state,
                    draft_id="draft-ignore-discard",
                    operation_id=operation["id"],
                )

                self.assertEqual(result["remaining_operation_count"], 0)
                self.assertFalse(result["draft_removed"])
                self.assertEqual(
                    state.execute(
                        "SELECT status FROM workflow_drafts WHERE id='draft-ignore-discard'"
                    ).fetchone()["status"],
                    "draft",
                )
                self.assertEqual(
                    drafts.list_asset_resolutions(state, "draft-ignore-discard")[0]["evidence"],
                    evidence,
                )
            finally:
                projection.close()
                state.close()

    def test_unresolved_physical_target_is_rejected_before_persistence(self):
        with tempfile.TemporaryDirectory(prefix="wbm-draft-lineage-") as raw:
            projection, state = self._stores(Path(raw))
            try:
                projection.execute(
                    "UPDATE options SET src_sheet='' WHERE model_id='stingray' "
                    "AND option_id='opt_test'"
                )
                projection.commit()
                with self.assertRaises(drafts.DraftError) as ctx:
                    drafts.save_operation(
                        projection,
                        state,
                        projection_state="current",
                        base_workbook_sha256="sha",
                        base_workbook_mtime_ns="1",
                        draft_id="draft-1",
                        table="options",
                        model_id="stingray",
                        op="update",
                        key={"option_id": "opt_test"},
                        record={"option_name": "Changed"},
                    )
                self.assertEqual(ctx.exception.code, "physical_target_unresolved")
                self.assertEqual(
                    state.execute(
                        "SELECT COUNT(*) c FROM workflow_drafts"
                    ).fetchone()["c"],
                    0,
                )
            finally:
                projection.close()
                state.close()


if __name__ == "__main__":
    unittest.main()
