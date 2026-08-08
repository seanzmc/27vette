"""Pass 5 durable-draft behavior for Workbook Manager."""

from __future__ import annotations

import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND = REPO_ROOT / "workbook-manager" / "backend"
for path in (str(BACKEND), str(REPO_ROOT / "scripts")):
    if path not in sys.path:
        sys.path.insert(0, path)

from app import db as dbmod  # noqa: E402
try:  # RED phase: the Pass 5 draft service does not exist yet.
    from app import drafts  # noqa: E402
except ImportError:
    drafts = None


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

    def test_draft_creation_requires_current_projection(self):
        self.assertIsNotNone(drafts, "Pass 5 durable draft service is missing")
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
            finally:
                projection.close()
                state.close()


if __name__ == "__main__":
    unittest.main()
