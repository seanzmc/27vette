"""Tests for workbook-manager: import fidelity, validation, staging, sync
batch construction, and comparison export.

Runs with pytest or plain unittest. API-layer tests skip automatically when
fastapi is not installed (install workbook-manager/backend/requirements.txt
into the repo venv to enable them).
"""

from __future__ import annotations

import json
import os
import shutil
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND = REPO_ROOT / "workbook-manager" / "backend"
for p in (str(BACKEND), str(REPO_ROOT / "scripts")):
    if p not in sys.path:
        sys.path.insert(0, p)

from app import db as dbmod                     # noqa: E402
from app import importer, naming, staging, sync as syncmod  # noqa: E402
from app.catalog import (  # noqa: E402
    SPEC_BY_TABLE,
    TABLE_SPECS,
    classify_workbook_sheets,
)
from app.staging import StagingError            # noqa: E402
from app.validation import find_dependents      # noqa: E402

WORKBOOK = REPO_ROOT / "stingray_master.xlsx"

try:
    import fastapi  # noqa: F401
    HAVE_FASTAPI = True
except ImportError:
    HAVE_FASTAPI = False


def fresh_db(tmpdir: Path) -> sqlite3.Connection:
    conn = dbmod.connect(tmpdir / "test.sqlite3")
    dbmod.init_schema(conn)
    return conn


class ImportedWorkbookCase(unittest.TestCase):
    """Shared imported-database fixture (imported once per class)."""

    tmpdir: Path
    conn: sqlite3.Connection
    report: dict

    @classmethod
    def setUpClass(cls):
        cls.tmpdir = Path(tempfile.mkdtemp(prefix="wbm-test-"))
        cls.conn = fresh_db(cls.tmpdir)
        cls.report = importer.import_workbook(cls.conn, WORKBOOK)

    @classmethod
    def tearDownClass(cls):
        cls.conn.close()
        shutil.rmtree(cls.tmpdir, ignore_errors=True)


class TestImportFidelity(ImportedWorkbookCase):
    def _workbook_row_count(self, sheet: str) -> int:
        from openpyxl import load_workbook
        wb = load_workbook(WORKBOOK, read_only=True)
        ws = wb[sheet]
        it = ws.iter_rows(values_only=True)
        headers = [str(h) if h is not None else "" for h in next(it)]
        count = 0
        for row in it:
            if row is None:
                continue
            rec = {h: v for h, v in zip(headers, row) if h}
            if all(v is None or str(v).strip() == "" for v in rec.values()):
                continue
            count += 1
        wb.close()
        return count

    def test_no_silent_row_loss_for_options(self):
        for model, sheet in [("stingray", "stingray_options"),
                             ("grand_sport", "grandSport_options"),
                             ("z06", "z06_options")]:
            db_count = self.conn.execute(
                "SELECT COUNT(*) c FROM options WHERE model_id=?",
                (model,)).fetchone()["c"]
            dup_or_missing = self.conn.execute(
                "SELECT COUNT(*) c FROM import_issues WHERE run_id=? AND "
                "sheet=? AND category IN ('duplicate_id','missing_identifier')",
                (self.report["run"]["id"], sheet)).fetchone()["c"]
            self.assertEqual(db_count + dup_or_missing,
                             self._workbook_row_count(sheet),
                             f"row loss in {sheet}")

    def test_every_sheet_is_classified_without_a_second_preserved_cell_store(self):
        from openpyxl import load_workbook
        wb = load_workbook(WORKBOOK, read_only=True)
        names = set(wb.sheetnames)
        classifications = classify_workbook_sheets(wb)
        wb.close()
        self.assertEqual(
            self.conn.execute("SELECT COUNT(*) c FROM raw_sheet_rows").fetchone()["c"],
            0,
        )
        self.assertEqual(names, set(classifications))

    def test_model_scoped_option_uniqueness_enforced(self):
        dup = self.conn.execute(
            "SELECT model_id, option_id, COUNT(*) c FROM options "
            "GROUP BY model_id, option_id HAVING c > 1").fetchall()
        self.assertEqual([dict(d) for d in dup], [])

    def test_cross_model_option_ids_coexist(self):
        row = self.conn.execute(
            "SELECT COUNT(DISTINCT model_id) c FROM options WHERE "
            "option_id IN (SELECT option_id FROM options GROUP BY option_id "
            "HAVING COUNT(DISTINCT model_id) > 1)").fetchone()
        self.assertGreater(row["c"], 1,
                           "expected shared option_ids across models")

    def test_model_setup_copy_columns_are_managed_and_imported(self):
        expected = {
            "setup_card_subtitle", "setup_eyebrow", "setup_title", "setup_description",
            "setup_fact_1", "setup_fact_2", "setup_fact_3",
        }
        model_spec = SPEC_BY_TABLE["models"]
        self.assertTrue(expected.issubset({column.header for column in model_spec.columns}))
        rows = self.conn.execute(
            "SELECT * FROM models WHERE active IN ('True', '1', 'TRUE', 'true') "
            "ORDER BY model_key"
        ).fetchall()
        self.assertEqual(
            [row["model_key"] for row in rows],
            ["grand_sport", "grand_sport_x", "stingray", "z06", "zr1", "zr1x"],
        )
        for row in rows:
            self.assertTrue(
                all(row[column] for column in expected),
                f"active model {row['model_key']} must have complete setup copy",
            )

    def test_import_reports_are_queryable(self):
        self.assertIn(self.report["run"]["status"],
                      ("imported", "imported_with_issues"))
        for issue in self.report["issues"]:
            self.assertTrue(issue["message"])
            self.assertIn(issue["severity"], ("error", "warning"))

    def test_ovs_rows_reference_known_options(self):
        orphans = self.conn.execute(
            "SELECT COUNT(*) c FROM option_availability oa WHERE NOT EXISTS ("
            "SELECT 1 FROM options o WHERE o.model_id = oa.model_id AND "
            "o.option_id = oa.option_id)").fetchone()["c"]
        reported = self.conn.execute(
            "SELECT COUNT(*) c FROM import_issues WHERE run_id=? AND "
            "table_name='option_availability' AND category='unresolved_ref' "
            "AND field='option_id'",
            (self.report["run"]["id"],)).fetchone()["c"]
        self.assertEqual(orphans, reported,
                         "unresolved OVS references must all be reported")

    def test_shared_physical_source_rows_import_once_with_all_model_contexts(self):
        rows = self.conn.execute(
            "SELECT src_sheet, physical_key, model_context FROM interiors"
        ).fetchall()
        identities = {(row["src_sheet"], row["physical_key"]) for row in rows}
        self.assertEqual(len(rows), len(identities))
        shared = self.conn.execute(
            "SELECT model_context FROM interiors "
            "WHERE src_sheet='lt_interiors' LIMIT 1"
        ).fetchone()
        self.assertGreater(len(json.loads(shared["model_context"])), 1)


class TestNaming(unittest.TestCase):
    def test_humanize_examples(self):
        self.assertEqual(naming.humanize("stingray_exterior_options"),
                         "Stingray Exterior Options")
        self.assertEqual(naming.humanize("grandSport_options"),
                         "Grand Sport Options")
        self.assertEqual(naming.humanize("z06_ovs"), "Z06 OVS")
        self.assertEqual(naming.humanize("LZ_Interiors"), "LZ Interiors")

    def test_display_id_prefix_stripping_is_reversible(self):
        prefix, remainder = naming.strip_prefix("opt_z51_001", ("opt_",))
        self.assertEqual(prefix + remainder, "opt_z51_001")
        self.assertEqual(naming.display_id("opt_z51_001", ("opt_",)),
                         "Z51 001")

    def test_unconfirmed_prefix_is_not_stripped(self):
        self.assertEqual(naming.strip_prefix("sec_pain_001", ("opt_",)),
                         ("", "sec_pain_001"))


class TestStagingWorkflow(ImportedWorkbookCase):
    def setUp(self):
        self.conn.execute("DELETE FROM pending_changes")
        self.conn.execute("DELETE FROM change_history")
        self.conn.commit()

    def test_stage_validate_commit_add_option(self):
        record = {
            "option_id": "opt_test_901", "rpo": "TST", "price": "100",
            "option_name": "Test Option", "description": "", "detail_raw": "",
            "section_id": "sec_pain_001", "selectable": "True",
            "display_order": "999", "active": "True", "display_behavior": "",
        }
        change = staging.stage_change(
            self.conn, table="options", model_id="stingray", op="add",
            key={"option_id": "opt_test_901"}, record=record)
        self.assertEqual(change["status"], "staged")
        result = staging.commit_staged(self.conn, actor="test")
        self.assertTrue(result["ok"], result)
        row = self.conn.execute(
            "SELECT * FROM options WHERE model_id='stingray' AND "
            "option_id='opt_test_901'").fetchone()
        self.assertIsNotNone(row)
        hist = self.conn.execute(
            "SELECT * FROM change_history WHERE entity_id='opt_test_901'"
        ).fetchone()
        self.assertIsNotNone(hist, "committed change must appear in audit")
        self.assertEqual(hist["sync_status"], "pending")

    def test_invalid_reference_is_rejected_with_field_detail(self):
        record = {"option_id": "opt_test_902", "rpo": "TST",
                  "section_id": "sec_does_not_exist", "price": "0",
                  "option_name": "Bad", "selectable": "True",
                  "display_order": "1", "active": "True"}
        with self.assertRaises(StagingError) as ctx:
            staging.stage_change(
                self.conn, table="options", model_id="stingray", op="add",
                key={"option_id": "opt_test_902"}, record=record)
        fields = {e["field"] for e in ctx.exception.errors}
        self.assertIn("section_id", fields)

    def test_duplicate_key_rejected_in_model_scope(self):
        existing = self.conn.execute(
            "SELECT option_id FROM options WHERE model_id='stingray' "
            "LIMIT 1").fetchone()["option_id"]
        with self.assertRaises(StagingError):
            staging.stage_change(
                self.conn, table="options", model_id="stingray", op="add",
                key={"option_id": existing},
                record={"option_id": existing, "option_name": "Dup",
                        "rpo": "X", "price": "0", "selectable": "True",
                        "display_order": "1", "active": "True"})

    def test_delete_blocked_by_dependents_then_confirmable(self):
        row = self.conn.execute(
            "SELECT o.option_id FROM options o JOIN option_availability oa "
            "ON oa.model_id=o.model_id AND oa.option_id=o.option_id "
            "WHERE o.model_id='stingray' LIMIT 1").fetchone()
        option_id = row["option_id"]
        with self.assertRaises(StagingError) as ctx:
            staging.stage_change(self.conn, table="options",
                                 model_id="stingray", op="delete",
                                 key={"option_id": option_id}, record=None)
        self.assertIn("dependent", ctx.exception.errors[0]["message"])
        change = staging.stage_change(
            self.conn, table="options", model_id="stingray", op="delete",
            key={"option_id": option_id}, record=None,
            confirm_dependencies=True)
        self.assertEqual(change["status"], "staged")
        staging.discard_change(self.conn, change["id"])

    def test_undo_before_commit(self):
        change = staging.stage_change(
            self.conn, table="exclusive_groups", model_id="stingray",
            op="add", key={"group_id": "xg_test_1"},
            record={"group_id": "xg_test_1",
                    "selection_mode": "single_within_group",
                    "active": "True", "notes": ""})
        discarded = staging.discard_change(self.conn, change["id"])
        self.assertEqual(discarded["status"], "discarded")
        result = staging.commit_staged(self.conn)
        self.assertEqual(result["status"], "empty")

    def test_read_only_table_rejected(self):
        with self.assertRaises(StagingError) as ctx:
            staging.stage_change(
                self.conn, table="form_sections", model_id="", op="add",
                key={"section_id": "sec_test_1"},
                record={"section_id": "sec_test_1"})
        self.assertIn("read-only", ctx.exception.errors[0]["message"])

    def test_key_rename_on_update_rejected(self):
        """Keys are immutable on update (verifier finding 2026-07-15): the
        workbook write path cannot rename keys, so the DB must not either."""
        row = self.conn.execute(
            "SELECT * FROM options WHERE model_id='stingray' LIMIT 1"
        ).fetchone()
        record = {c.sql_name(): row[c.sql_name()]
                  for c in SPEC_BY_TABLE["options"].columns}
        record["option_id"] = "opt_renamed_999"
        with self.assertRaises(StagingError) as ctx:
            staging.stage_change(
                self.conn, table="options", model_id="stingray", op="update",
                key={"option_id": row["option_id"]}, record=record)
        self.assertIn("cannot change on update",
                      ctx.exception.errors[0]["message"])

    def test_duplicate_staged_adds_fail_batch_validation_not_commit(self):
        """Two staged adds with the same key must fail Validate All cleanly
        (verifier finding 2026-07-15), not explode at commit."""
        rec = {"group_id": "xg_dup_1",
               "selection_mode": "single_within_group",
               "active": "True", "notes": ""}
        for _ in range(2):
            staging.stage_change(
                self.conn, table="exclusive_groups", model_id="stingray",
                op="add", key={"group_id": "xg_dup_1"}, record=dict(rec))
        result = staging.commit_staged(self.conn)
        self.assertFalse(result["ok"])
        self.assertEqual(result["status"], "invalid")
        messages = [e["message"] for r in result["validation"]["results"]
                    for e in r["errors"]]
        self.assertTrue(any("duplicate key with staged change" in m
                            for m in messages), messages)
        # nothing committed, nothing in history
        self.assertEqual(self.conn.execute(
            "SELECT COUNT(*) c FROM change_history").fetchone()["c"], 0)
        for c in staging.list_changes(self.conn, "staged"):
            staging.discard_change(self.conn, c["id"])

    def test_unknown_model_content_rejected(self):
        with self.assertRaises(StagingError) as ctx:
            staging.stage_change(
                self.conn, table="options", model_id="not_a_model", op="add",
                key={"option_id": "opt_test_910"},
                record={"option_id": "opt_test_910"})
        self.assertIn("unknown model", ctx.exception.errors[0]["message"])

    def test_active_source_backed_unpublished_model_is_editable(self):
        source = self.conn.execute(
            "SELECT * FROM options WHERE model_id='zr1' LIMIT 1"
        ).fetchone()
        record = {
            column.sql_name(): source[column.sql_name()]
            for column in SPEC_BY_TABLE["options"].columns
        }
        record["option_id"] = "opt_test_911"
        change = staging.stage_change(
            self.conn,
            table="options",
            model_id="zr1",
            op="add",
            key={"option_id": record["option_id"]},
            record=record,
        )
        self.assertEqual(change["status"], "staged")
        staging.discard_change(self.conn, change["id"])

    def test_runtime_promotion_requires_canonical_model_generatability(self):
        model = "zr1"
        source = self.conn.execute(
            "SELECT * FROM model_registry_promotion WHERE model_key=?", (model,)
        ).fetchone()
        record = {
            column.sql_name(): source[column.sql_name()]
            for column in SPEC_BY_TABLE["model_registry_promotion"].columns
        }
        record["active"] = "True"
        record["promoted_to_runtime"] = "True"
        with mock.patch.object(
            staging, "discover_generation_model_configs", return_value={}
        ):
            with self.assertRaises(StagingError) as ctx:
                staging.stage_change(
                    self.conn,
                    table="model_registry_promotion",
                    model_id=model,
                    op="update",
                    key={"model_key": model},
                    record=record,
                )
        self.assertIn("not generatable", ctx.exception.errors[0]["message"])

    def test_inactive_model_content_rejected_but_topology_editable(self):
        model = "grand_sport_x"
        original_active = self.conn.execute(
            "SELECT active FROM models WHERE model_key=?", (model,)
        ).fetchone()["active"]
        self.conn.execute("UPDATE models SET active='False' WHERE model_key=?", (model,))
        self.conn.commit()
        try:
            source = self.conn.execute(
                "SELECT * FROM options WHERE model_id=? LIMIT 1", (model,)
            ).fetchone()
            record = {
                column.sql_name(): source[column.sql_name()]
                for column in SPEC_BY_TABLE["options"].columns
            }
            record["option_id"] = "opt_test_912"
            with self.assertRaises(StagingError) as ctx:
                staging.stage_change(
                    self.conn,
                    table="options",
                    model_id=model,
                    op="add",
                    key={"option_id": record["option_id"]},
                    record=record,
                )
            self.assertIn("inactive model", ctx.exception.errors[0]["message"])

            topology = self.conn.execute(
                "SELECT * FROM model_variants WHERE model_key=? LIMIT 1", (model,)
            ).fetchone()
            topology_record = {
                column.sql_name(): topology[column.sql_name()]
                for column in SPEC_BY_TABLE["model_variants"].columns
            }
            change = staging.stage_change(
                self.conn,
                table="model_variants",
                model_id=model,
                op="update",
                key={
                    "model_key": topology["model_key"],
                    "variant_id": topology["variant_id"],
                },
                record=topology_record,
            )
            staging.discard_change(self.conn, change["id"])
        finally:
            self.conn.execute(
                "UPDATE models SET active=? WHERE model_key=?", (original_active, model)
            )
            self.conn.commit()

    def test_asset_wildcard_is_the_only_writable_wildcard_model_scope(self):
        change = staging.stage_change(
            self.conn,
            table="assets",
            model_id="*",
            op="add",
            key={"model_key": "*", "target_type": "option", "target_id": "opt_test_asset"},
            record={
                "model_key": "*",
                "target_type": "option",
                "target_id": "opt_test_asset",
                "image_url": "https://example.invalid/test.png",
                "image_alt": "Test",
                "image_fit": "contain",
                "image_position": "center",
                "hover_image_url": "",
                "hover_image_alt": "",
                "hover_image_position": "",
                "active": "True",
                "notes": "test",
            },
        )
        staging.discard_change(self.conn, change["id"])
        with self.assertRaises(StagingError):
            staging.stage_change(
                self.conn,
                table="default_selection_rules",
                model_id="*",
                op="add",
                key={"model_key": "*", "rule_id": "default_test"},
                record={"model_key": "*", "rule_id": "default_test"},
            )

    def test_inactive_source_role_rejected_while_fixed_model_content_is_editable(self):
        model = "zr1"
        role = "source_option_sheet"
        original = self.conn.execute(
            "SELECT active FROM sheet_registry WHERE model_key=? AND source_role=?",
            (model, role),
        ).fetchone()["active"]
        self.conn.execute(
            "UPDATE sheet_registry SET active='False' WHERE model_key=? AND source_role=?",
            (model, role),
        )
        self.conn.commit()
        try:
            source = self.conn.execute(
                "SELECT * FROM options WHERE model_id=? LIMIT 1", (model,)
            ).fetchone()
            record = {
                column.sql_name(): source[column.sql_name()]
                for column in SPEC_BY_TABLE["options"].columns
            }
            record["option_id"] = "opt_test_913"
            with self.assertRaises(StagingError) as ctx:
                staging.stage_change(
                    self.conn,
                    table="options",
                    model_id=model,
                    op="add",
                    key={"option_id": record["option_id"]},
                    record=record,
                )
            self.assertIn("inactive source role", ctx.exception.errors[0]["message"])

            fixed = self.conn.execute(
                "SELECT * FROM form_steps WHERE model_key=? LIMIT 1", (model,)
            ).fetchone()
            fixed_record = {
                column.sql_name(): fixed[column.sql_name()]
                for column in SPEC_BY_TABLE["form_steps"].columns
            }
            change = staging.stage_change(
                self.conn,
                table="form_steps",
                model_id=model,
                op="update",
                key={"model_key": model, "step_key": fixed["step_key"]},
                record=fixed_record,
            )
            staging.discard_change(self.conn, change["id"])
        finally:
            self.conn.execute(
                "UPDATE sheet_registry SET active=? WHERE model_key=? AND source_role=?",
                (original, model, role),
            )
            self.conn.commit()


class TestSyncBatch(ImportedWorkbookCase):
    def setUp(self):
        self.conn.execute("DELETE FROM pending_changes")
        self.conn.execute("DELETE FROM change_history")
        self.conn.commit()

    def _commit_price_edit(self):
        row = self.conn.execute(
            "SELECT * FROM options WHERE model_id='stingray' AND rpo='Z51'"
        ).fetchone()
        record = {c.sql_name(): row[c.sql_name()]
                  for c in SPEC_BY_TABLE["options"].columns}
        record["price"] = str(int(record["price"] or 0) + 1)
        staging.stage_change(
            self.conn, table="options", model_id="stingray", op="update",
            key={"option_id": row["option_id"]}, record=record)
        result = staging.commit_staged(self.conn, actor="test")
        self.assertTrue(result["ok"], result)
        return row, record

    def _commit_model_setup_edit(self):
        row = self.conn.execute(
            "SELECT * FROM models WHERE model_key='stingray'"
        ).fetchone()
        record = {c.sql_name(): row[c.sql_name()]
                  for c in SPEC_BY_TABLE["models"].columns}
        record["setup_title"] = f"{record['setup_title']} (reviewed)"
        staging.stage_change(
            self.conn, table="models", model_id="", op="update",
            key={"model_key": row["model_key"]}, record=record)
        result = staging.commit_staged(self.conn, actor="test")
        self.assertTrue(result["ok"], result)
        return row, record

    def test_batch_targets_registered_sheet_with_header_names(self):
        row, record = self._commit_price_edit()
        batch = syncmod.build_batch(self.conn, WORKBOOK)
        self.assertEqual(len(batch["items"]), 1)
        op = batch["items"][0]
        self.assertEqual(op["sheet"], "stingray_options")
        self.assertEqual(op["action"], "update")
        self.assertEqual(op["key"], {"option_id": row["option_id"]})
        self.assertEqual(op["row"]["price"], record["price"])

    def test_model_setup_edit_builds_model_master_editor_op(self):
        row, record = self._commit_model_setup_edit()
        batch = syncmod.build_batch(self.conn, WORKBOOK)
        self.assertEqual(len(batch["items"]), 1)
        op = batch["items"][0]
        self.assertEqual(op["sheet"], "model_master")
        self.assertEqual(op["action"], "update")
        self.assertEqual(op["key"], {"model_key": row["model_key"]})
        self.assertEqual(op["row"]["setup_title"], record["setup_title"])

    def test_dry_run_batch_passes_editor_ops_validation(self):
        """Fast slice of the gate: batch preparation + validation only."""
        from corvette_form_generator import editor_ops
        self._commit_price_edit()
        batch = syncmod.build_batch(self.conn, WORKBOOK)
        extract = editor_ops.extract_workbook(WORKBOOK)
        errors, warnings, prepared = editor_ops._prepare_batch(
            extract, {"items": batch["items"]})
        self.assertEqual(errors, [])
        self.assertEqual(len(prepared), 1)

    @unittest.skipUnless(os.environ.get("WBM_SLOW_GATE") == "1",
                         "full dry-run gate is slow; set WBM_SLOW_GATE=1")
    def test_dry_run_through_editor_ops_gate(self):
        # Copy the workbook so even a bug cannot touch the real file.
        wb_copy = Path(self.tmpdir) / "scratch.xlsx"
        shutil.copy2(WORKBOOK, wb_copy)
        self._commit_price_edit()
        result = syncmod.sync_workbook(self.conn, wb_copy, write=False)
        self.assertEqual(result.get("status"), "validated",
                         f"dry-run failed: {result}")
        # dry run must not mark anything synced
        pending = self.conn.execute(
            "SELECT COUNT(*) c FROM change_history WHERE "
            "sync_status='pending'").fetchone()["c"]
        self.assertEqual(pending, 1)

    @unittest.skipUnless(os.environ.get("WBM_SLOW_GATE") == "1",
                         "full live-write gate is slow; set WBM_SLOW_GATE=1")
    def test_live_write_on_scratch_copy_creates_backup_and_marks_synced(self):
        from app import config

        wb_copy = Path(self.tmpdir) / "scratch3.xlsx"
        shutil.copy2(WORKBOOK, wb_copy)
        self._commit_price_edit()
        original_log_path = config.EDIT_LOG_PATH
        config.EDIT_LOG_PATH = Path(self.tmpdir) / "workbook-edit-log.jsonl"
        try:
            result = syncmod.sync_workbook(
                self.conn, wb_copy, write=True,
                expected_mtime_ns=str(wb_copy.stat().st_mtime_ns))
        finally:
            config.EDIT_LOG_PATH = original_log_path
        self.assertEqual(result.get("status"), "applied",
                         f"live write failed: {result}")
        self.assertTrue(result.get("backupPath"))
        pending = self.conn.execute(
            "SELECT COUNT(*) c FROM change_history WHERE "
            "sync_status='pending'").fetchone()["c"]
        self.assertEqual(pending, 0)

    def test_live_write_requires_matching_mtime(self):
        wb_copy = Path(self.tmpdir) / "scratch2.xlsx"
        shutil.copy2(WORKBOOK, wb_copy)
        self._commit_price_edit()
        result = syncmod.sync_workbook(self.conn, wb_copy, write=True,
                                       expected_mtime_ns="1")
        self.assertEqual(result["status"], "stale")


class TestComparisonExport(ImportedWorkbookCase):
    def test_export_is_explicitly_disposable(self):
        from app import config
        config.VAR_DIR = self.tmpdir / "var"
        config.EXPORT_DIR = config.VAR_DIR / "exports"
        config.DB_BACKUP_DIR = config.VAR_DIR / "db-backups"
        result = syncmod.export_comparison_workbook(self.conn, WORKBOOK)
        self.assertTrue(result["disposable"])
        self.assertIn("DISPOSABLE-comparison-", Path(result["path"]).name)
        self.assertTrue(Path(result["path"]).is_relative_to(config.EXPORT_DIR))

    def test_export_preserves_unmanaged_and_row_counts(self):
        import os
        os.environ.setdefault("WBM_VAR_DIR", str(self.tmpdir / "var"))
        from app import config
        config.VAR_DIR = self.tmpdir / "var"
        config.EXPORT_DIR = config.VAR_DIR / "exports"
        config.DB_BACKUP_DIR = config.VAR_DIR / "db-backups"
        result = syncmod.export_comparison_workbook(self.conn, WORKBOOK)
        self.assertTrue(result["ok"])
        from openpyxl import load_workbook
        orig = load_workbook(WORKBOOK, read_only=True)
        regen = load_workbook(result["path"], read_only=True)
        self.assertEqual(set(orig.sheetnames), set(regen.sheetnames),
                         "regenerated workbook must keep every sheet")
        # unmanaged sheet content preserved verbatim (PriceRef)
        def rows(wb, sheet):
            return [tuple(str(c) if c is not None else "" for c in r)
                    for r in wb[sheet].iter_rows(values_only=True)]
        self.assertEqual(rows(orig, "PriceRef"), rows(regen, "PriceRef"))
        # managed sheet keeps its row count
        self.assertEqual(len(rows(orig, "stingray_options")),
                         len(rows(regen, "stingray_options")))
        self.assertEqual(
            rows(orig, "model_master"),
            rows(regen, "model_master"),
            "managed model_master setup copy must round-trip without drift",
        )
        orig.close()
        regen.close()


class TestDependencyInspection(ImportedWorkbookCase):
    def test_option_dependents_span_tables(self):
        row = self.conn.execute(
            "SELECT o.option_id FROM options o JOIN exclusive_group_members "
            "egm ON egm.model_id=o.model_id AND egm.option_id=o.option_id "
            "WHERE o.model_id='stingray' LIMIT 1").fetchone()
        deps = find_dependents(self.conn, SPEC_BY_TABLE["options"],
                               "stingray", {"option_id": row["option_id"]})
        tables = {d["table"] for d in deps}
        self.assertIn("exclusive_group_members", tables)
        for d in deps:
            self.assertTrue(d["entity_key"])
            self.assertTrue(d["src_sheet"])


class TestPass1BrowserContainment(unittest.TestCase):
    def test_browser_has_persistent_provisional_banner_and_no_write_control(self):
        app_source = (REPO_ROOT / "workbook-manager" / "frontend" / "src" /
                      "App.jsx").read_text()
        sync_source = (REPO_ROOT / "workbook-manager" / "frontend" / "src" /
                       "components" / "ChangesSync.jsx").read_text()
        self.assertIn("Read-only / provisional", app_source)
        self.assertNotIn("write: true", sync_source)
        self.assertNotIn("Write to stingray_master.xlsx", sync_source)


@unittest.skipUnless(HAVE_FASTAPI, "fastapi not installed; install "
                     "workbook-manager/backend/requirements.txt")
class TestApi(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import os
        cls.tmpdir = Path(tempfile.mkdtemp(prefix="wbm-api-"))
        os.environ["WBM_DB"] = str(cls.tmpdir / "api.sqlite3")
        os.environ["WBM_VAR_DIR"] = str(cls.tmpdir / "var")
        # Force a FULL re-import of the app package so config re-reads the
        # env vars above. The bare "app" entry must be deleted too: leaving
        # the package object in sys.modules makes `from . import staging`
        # resolve to the stale module via the package attribute while
        # `from .staging import StagingError` re-imports a fresh copy —
        # two StagingError classes, and main.py's `except StagingError`
        # misses the raise (500 instead of 422).
        for mod in list(sys.modules):
            if mod == "app" or mod.startswith("app."):
                del sys.modules[mod]
        from fastapi.testclient import TestClient
        from app import main as mainmod
        cls.mainmod = mainmod
        cls.client = TestClient(mainmod.app)
        cls.client.post("/api/import")

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmpdir, ignore_errors=True)

    def test_status_and_models(self):
        status = self.client.get("/api/status").json()
        self.assertGreater(status["tables"]["options"], 900)
        models = self.client.get("/api/models").json()["models"]
        keys = {m["model_key"] for m in models}
        self.assertLessEqual({"stingray", "grand_sport", "z06"}, keys)

    def test_status_reports_provisional_surfaces_separately(self):
        status = self.client.get("/api/status").json()
        self.assertEqual(status["mode"], "read_only_provisional")
        self.assertEqual(status["projection"]["state"], "unverified")
        self.assertTrue(status["projection"]["active"])
        self.assertEqual(status["draft"]["state"], "clear")
        self.assertIn("state", status["workbook"])
        self.assertEqual(status["generated_artifacts"]["state"], "unverified")
        self.assertEqual(status["publication"]["state"], "unverified")

    def test_structure_and_collections(self):
        structure = self.client.get("/api/structure/stingray").json()
        self.assertTrue(structure["steps"])
        cols = self.client.get(
            "/api/models/stingray/collections").json()["collections"]
        tables = {c["table"] for c in cols}
        self.assertIn("options", tables)
        self.assertIn("pricing", tables)

    def test_stage_endpoint_validation_error_shape(self):
        resp = self.client.post("/api/changes", json={
            "table": "options", "model_id": "stingray", "op": "add",
            "key": {"option_id": "opt_x"},
            "record": {"option_id": "opt_x", "price": "not-a-number"}})
        self.assertEqual(resp.status_code, 422)
        detail = resp.json()["detail"]
        self.assertTrue(any(e["field"] == "price"
                            for e in detail["errors"]))

    def test_records_search(self):
        resp = self.client.get(
            "/api/records/options", params={"model": "stingray",
                                            "search": "Z51"}).json()
        self.assertGreater(resp["total"], 0)

    def test_schema_exposes_final_shared_field_and_model_context_metadata(self):
        defaults = self.client.get(
            "/api/records/default_selection_rules/schema",
            params={"model": "stingray"},
        ).json()
        self.assertTrue(defaults["model_context"]["required"])
        by_name = {column["name"]: column for column in defaults["columns"]}
        self.assertEqual(by_name["condition_type"]["field_kind"], "finite")
        condition_ref = by_name["condition_id"]["reference"]
        self.assertEqual(condition_ref["kind"], "conditional")
        self.assertTrue(
            any(target["derived"] for target in condition_ref["targets"])
        )
        self.assertTrue(by_name["condition_id"]["optional"])
        self.assertEqual(by_name["notes"]["field_kind"], "free_text")

        mappings = self.client.get(
            "/api/records/rule_mappings/schema", params={"model": "stingray"}
        ).json()
        mapping_fields = {column["name"]: column for column in mappings["columns"]}
        self.assertEqual(mapping_fields["source_id"]["reference"]["kind"], "union")

    def test_live_sync_is_provisionally_read_only_even_when_fully_confirmed(self):
        current_mtime = str(WORKBOOK.stat().st_mtime_ns)
        resp = self.client.post("/api/sync", json={
            "write": True,
            "confirm": "SYNC",
            "expected_mtime_ns": current_mtime,
        })
        self.assertEqual(resp.status_code, 409)
        detail = resp.json()["detail"]
        self.assertEqual(detail["status"], "read_only_provisional")
        self.assertIn("Pass 7", detail["message"])

    def test_reimport_refuses_to_replace_an_active_projection(self):
        conn = self.mainmod.get_conn()
        before_runs = conn.execute("SELECT COUNT(*) c FROM import_runs").fetchone()["c"]
        before_options = conn.execute("SELECT COUNT(*) c FROM options").fetchone()["c"]
        resp = self.client.post("/api/import")
        self.assertEqual(resp.status_code, 409)
        detail = resp.json()["detail"]
        self.assertTrue(detail["active_projection"])
        self.assertEqual(detail["status"], "read_only_provisional")
        self.assertEqual(
            conn.execute("SELECT COUNT(*) c FROM import_runs").fetchone()["c"],
            before_runs,
        )
        self.assertEqual(
            conn.execute("SELECT COUNT(*) c FROM options").fetchone()["c"],
            before_options,
        )

    def test_unverified_projection_refuses_comparison_export(self):
        status = self.client.get("/api/status").json()
        self.assertEqual(status["projection"]["state"], "unverified")
        resp = self.client.post("/api/export")
        self.assertEqual(resp.status_code, 409)
        detail = resp.json()["detail"]
        self.assertEqual(detail["status"], "projection_not_current")

    def test_import_reports_all_unresolved_legacy_workflow_blockers(self):
        conn = self.mainmod.get_state_conn()
        pending_id = conn.execute(
            "INSERT INTO pending_changes(ts, table_name, entity_key_json, op, "
            "status) VALUES('test', 'options', '{}', 'update', 'staged')"
        ).lastrowid
        pending_history_id = conn.execute(
            "INSERT INTO change_history(ts, entity_type, entity_id, op, status, "
            "sync_status) VALUES('test', 'options', 'one', 'update', "
            "'committed', 'pending')"
        ).lastrowid
        failed_history_id = conn.execute(
            "INSERT INTO change_history(ts, entity_type, entity_id, op, status, "
            "sync_status) VALUES('test', 'options', 'two', 'update', "
            "'committed', 'sync_failed')"
        ).lastrowid
        conn.commit()
        try:
            resp = self.client.post("/api/import")
            self.assertEqual(resp.status_code, 409)
            blockers = resp.json()["detail"]["import_blockers"]
            self.assertEqual(blockers["staged"], 1)
            self.assertEqual(blockers["committed_unsynchronized"], 1)
            self.assertEqual(blockers["failed"], 1)
            self.assertEqual(blockers["unresolved_total"], 3)
        finally:
            conn.execute("DELETE FROM pending_changes WHERE id=?", (pending_id,))
            conn.execute(
                "DELETE FROM change_history WHERE id IN (?, ?)",
                (pending_history_id, failed_history_id),
            )
            conn.commit()


if __name__ == "__main__":
    unittest.main(verbosity=2)
