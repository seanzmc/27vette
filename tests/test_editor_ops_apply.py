#!/usr/bin/env python3
"""Tests for the workbook-editor op engine (Phase 2)."""

from __future__ import annotations

import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

from openpyxl import Workbook, load_workbook
from openpyxl.worksheet.table import Table

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from corvette_form_generator.editor_ops import (  # noqa: E402
    apply_batch,
    coalesce_ops,
    coerce_value,
    extract_workbook,
    flatten_items,
    validate_batch,
)

REAL_WORKBOOK = ROOT / "stingray_master.xlsx"


def op(action, sheet, key, row=None, **extra):
    out = {"action": action, "sheet": sheet, "key": key}
    if row is not None:
        out["row"] = row
    out.update(extra)
    return out


class FlattenTest(unittest.TestCase):
    def test_composite_members_carry_label(self):
        items = [{"kind": "composite", "label": "Add XYZ", "ops": [
            op("add", "s", {"option_id": "a"}, {"option_id": "a"})]}]
        flat = flatten_items(items)
        self.assertEqual(flat[0]["_composite"], "Add XYZ")

    def test_plain_ops_pass_through(self):
        flat = flatten_items([op("delete", "s", {"option_id": "a"})])
        self.assertEqual(flat[0]["action"], "delete")


class CoalesceTest(unittest.TestCase):
    K = {"option_id": "a"}

    def test_update_update_merges_later_wins(self):
        out = coalesce_ops([op("update", "s", self.K, {"price": 1, "rpo": "X"}),
                            op("update", "s", self.K, {"price": 2})])
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0]["row"], {"price": 2, "rpo": "X"})

    def test_add_update_merges_into_add(self):
        out = coalesce_ops([op("add", "s", self.K, {"option_id": "a", "price": 1}),
                            op("update", "s", self.K, {"price": 2})])
        self.assertEqual(out[0]["action"], "add")
        self.assertEqual(out[0]["row"]["price"], 2)

    def test_add_delete_cancels(self):
        out = coalesce_ops([op("add", "s", self.K, {"option_id": "a"}),
                            op("delete", "s", self.K)])
        self.assertEqual(out, [])

    def test_update_delete_becomes_delete(self):
        out = coalesce_ops([op("update", "s", self.K, {"price": 1}),
                            op("delete", "s", self.K)])
        self.assertEqual([o["action"] for o in out], ["delete"])

    def test_delete_is_a_barrier(self):
        out = coalesce_ops([op("delete", "s", self.K),
                            op("add", "s", self.K, {"option_id": "a"})])
        self.assertEqual([o["action"] for o in out], ["delete", "add"])

    def test_different_keys_untouched(self):
        out = coalesce_ops([op("update", "s", {"option_id": "a"}, {"price": 1}),
                            op("update", "s", {"option_id": "b"}, {"price": 2})])
        self.assertEqual(len(out), 2)


class CoerceTest(unittest.TestCase):
    def test_int(self):
        self.assertEqual(coerce_value("options", "price", 500), 500)
        self.assertEqual(coerce_value("options", "price", "500"), 500)
        self.assertIsNone(coerce_value("options", "price", ""))
        with self.assertRaises(ValueError):
            coerce_value("options", "price", "abc")
        with self.assertRaises(ValueError):
            coerce_value("options", "price", True)

    def test_bool(self):
        self.assertIs(coerce_value("options", "selectable", True), True)
        self.assertIs(coerce_value("options", "selectable", "False"), False)
        with self.assertRaises(ValueError):
            coerce_value("options", "selectable", "yes")

    def test_enum(self):
        self.assertEqual(coerce_value("ovs", "status", "standard"), "standard")
        with self.assertRaises(ValueError):
            coerce_value("ovs", "status", "maybe")
        # blank allowed only when "" is in the domain
        self.assertIsNone(coerce_value("options", "display_behavior", ""))
        with self.assertRaises(ValueError):
            coerce_value("ovs", "status", "")

    def test_tristate_text_enum_stays_text(self):
        self.assertEqual(coerce_value("variant_overrides", "selectable", "True"), "True")

    def test_free_text_stripped(self):
        self.assertEqual(coerce_value("options", "option_name", "  X  "), "X")
        self.assertIsNone(coerce_value("options", "description", ""))


# ─────────────────────────────────────────────────────────────
# Fixture workbook for validation/apply tests
# ─────────────────────────────────────────────────────────────

def append_sheet(wb, name, headers, rows):
    ws = wb.create_sheet(name)
    ws.append(headers)
    for row in rows:
        ws.append([row.get(h) for h in headers])
    return ws


OPTION_HEADERS = ["option_id", "rpo", "price", "option_name", "description", "detail_raw",
                  "section_id", "selectable", "display_order", "active", "display_behavior"]


def option_row(oid, rpo, section, order):
    return {"option_id": oid, "rpo": rpo, "price": 0, "option_name": rpo,
            "section_id": section, "selectable": True, "display_order": order, "active": True}


def build_ops_fixture() -> Workbook:
    wb = Workbook()
    del wb[wb.sheetnames[0]]
    append_sheet(wb, "model_master",
                 ["model_key", "model_label", "default_model", "active"],
                 [{"model_key": "stingray", "model_label": "Stingray", "default_model": True, "active": True},
                  {"model_key": "zr1", "model_label": "ZR1", "default_model": False, "active": False}])
    append_sheet(wb, "model_registry_promotion",
                 ["model_key", "promoted_to_runtime", "display_order", "active"],
                 [{"model_key": "stingray", "promoted_to_runtime": True, "display_order": 1, "active": True}])
    src = [
        ("stingray", "source_option_sheet", "stingray_options"),
        ("stingray", "status_sheet", "stingray_ovs"),
        ("stingray", "rule_groups_sheet", "rule_groups"),
        ("stingray", "rule_group_members_sheet", "rule_group_members"),
        ("stingray", "exclusive_groups_sheet", "exclusive_groups"),
        ("stingray", "exclusive_group_members_sheet", "exclusive_group_members"),
        ("stingray", "price_rules_sheet", "price_rules"),
        ("zr1", "source_option_sheet", "zr1_options"),
        ("zr1", "status_sheet", "zr1_ovs"),
    ]
    append_sheet(wb, "model_workbook_sources",
                 ["model_key", "source_role", "sheet_name", "active"],
                 [{"model_key": m, "source_role": r, "sheet_name": s, "active": True} for m, r, s in src])
    append_sheet(wb, "variant_master", ["variant_id", "display_name", "active"],
                 [{"variant_id": "1lt", "display_name": "1LT", "active": True},
                  {"variant_id": "2lt", "display_name": "2LT", "active": True},
                  {"variant_id": "zr1_c", "display_name": "ZR1", "active": False}])
    append_sheet(wb, "model_variants", ["model_key", "variant_id", "display_order", "active"],
                 [{"model_key": "stingray", "variant_id": "1lt", "display_order": 1, "active": True},
                  {"model_key": "stingray", "variant_id": "2lt", "display_order": 2, "active": True},
                  {"model_key": "zr1", "variant_id": "zr1_c", "display_order": 1, "active": True}])
    append_sheet(wb, "section_master", ["section_id", "section_name", "step_key"],
                 [{"section_id": "sec_a", "section_name": "A", "step_key": "paint"},
                  {"section_id": "sec_b", "section_name": "B", "step_key": "wheels"}])
    ws = append_sheet(wb, "stingray_options", OPTION_HEADERS,
                      [option_row("opt_one_001", "ONE", "sec_a", 10),
                       option_row("opt_two_001", "TWO", "sec_a", 20),
                       option_row("opt_thr_001", "THR", "sec_b", 10)])
    # deliberately stale table ref: data goes to row 4, ref claims row 3
    ws.add_table(Table(displayName="tbl_fixture_options", ref="A1:K3"))
    append_sheet(wb, "stingray_ovs", ["option_id", "variant_id", "status"],
                 [{"option_id": "opt_one_001", "variant_id": "1lt", "status": "available"},
                  {"option_id": "opt_one_001", "variant_id": "2lt", "status": "standard"}])
    append_sheet(wb, "rule_groups", ["group_id", "group_type", "source_id", "active", "notes"],
                 [{"group_id": "grp_one", "group_type": "requires_any", "source_id": "opt_one_001", "active": True}])
    append_sheet(wb, "rule_group_members", ["group_id", "target_id", "display_order", "active"],
                 [{"group_id": "grp_one", "target_id": "opt_two_001", "display_order": 10, "active": True}])
    append_sheet(wb, "exclusive_groups", ["group_id", "selection_mode", "active", "notes"],
                 [{"group_id": "excl_one", "selection_mode": "single_within_group", "active": True}])
    append_sheet(wb, "exclusive_group_members", ["group_id", "option_id", "display_order", "active"],
                 [{"group_id": "excl_one", "option_id": "opt_one_001", "display_order": 10, "active": True},
                  {"group_id": "excl_one", "option_id": "opt_two_001", "display_order": 20, "active": True}])
    append_sheet(wb, "price_rules",
                 ["price_rule_id", "condition_option_id", "price_rule_type", "target_option_id",
                  "price_value", "body_style_scope", "trim_level_scope", "notes"], [])
    append_sheet(wb, "zr1_options", OPTION_HEADERS, [option_row("opt_zzz_001", "ZZZ", "sec_a", 10)])
    append_sheet(wb, "zr1_ovs", ["option_id", "variant_id", "status"],
                 [{"option_id": "opt_zzz_001", "variant_id": "zr1_c", "status": "available"}])
    append_sheet(wb, "form_steps", ["step_key"], [{"step_key": "paint"}])
    return wb


class OpsFixtureBase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._dir = tempfile.TemporaryDirectory()
        cls.wb_path = Path(cls._dir.name) / "fixture.xlsx"
        build_ops_fixture().save(cls.wb_path)
        cls.extract = extract_workbook(cls.wb_path)

    @classmethod
    def tearDownClass(cls):
        cls._dir.cleanup()


def batch(*items, mtime=None):
    return {"version": 1, "workbook": "fixture.xlsx", "workbookMtimeNs": mtime, "items": list(items)}


def add_option_composite(oid="opt_new_001", statuses=("available", "available"), section="sec_a", order=30):
    row = option_row(oid, oid[4:7].upper(), section, order)
    row.update({"description": None, "detail_raw": None, "display_behavior": None})
    ops = [op("add", "stingray_options", {"option_id": oid}, row)]
    for vid, status in zip(("1lt", "2lt"), statuses):
        if status is not None:
            ops.append(op("add", "stingray_ovs", {"option_id": oid, "variant_id": vid},
                          {"option_id": oid, "variant_id": vid, "status": status}))
    return {"kind": "composite", "label": f"Add {oid}", "ops": ops}


class ValidateBatchTest(OpsFixtureBase):
    def errors_of(self, *items):
        return validate_batch(self.extract, batch(*items))["errors"]

    def warnings_of(self, *items):
        return validate_batch(self.extract, batch(*items))["warnings"]

    def test_clean_add_option_composite(self):
        result = validate_batch(self.extract, batch(add_option_composite()))
        self.assertEqual(result["errors"], [])

    def test_readonly_and_unknown_sheet(self):
        self.assertTrue(self.errors_of(op("update", "form_steps", {"step_key": "paint"}, {"step_key": "x"})))
        self.assertTrue(self.errors_of(op("update", "section_master", {"section_id": "sec_a"}, {"section_name": "X"})))
        self.assertTrue(self.errors_of(op("update", "nope", {"option_id": "a"}, {})))

    def test_unknown_column_and_immutable_key(self):
        self.assertTrue(self.errors_of(op("update", "stingray_options", {"option_id": "opt_one_001"}, {"bogus": 1})))
        self.assertTrue(self.errors_of(op("update", "stingray_options", {"option_id": "opt_one_001"}, {"option_id": "x"})))

    def test_key_existence(self):
        self.assertTrue(self.errors_of(op("update", "stingray_options", {"option_id": "missing"}, {"price": 1})))
        self.assertTrue(self.errors_of(op("add", "stingray_options", {"option_id": "opt_one_001"},
                                          option_row("opt_one_001", "ONE", "sec_a", 99))))

    def test_type_enum_ref_violations(self):
        self.assertTrue(self.errors_of(op("update", "stingray_options", {"option_id": "opt_one_001"}, {"price": "abc"})))
        self.assertTrue(self.errors_of(op("update", "stingray_ovs",
                                          {"option_id": "opt_one_001", "variant_id": "1lt"}, {"status": "maybe"})))
        self.assertTrue(self.errors_of(op("update", "stingray_options", {"option_id": "opt_one_001"},
                                          {"section_id": "sec_nope"})))

    def test_batch_aware_refs(self):
        result = validate_batch(self.extract, batch(add_option_composite()))
        self.assertEqual(result["errors"], [])
        self.assertTrue(self.errors_of(op("add", "stingray_ovs",
                                          {"option_id": "opt_ghost_001", "variant_id": "1lt"},
                                          {"option_id": "opt_ghost_001", "variant_id": "1lt", "status": "available"})))

    def test_ovs_coverage_enforced(self):
        partial = add_option_composite(statuses=("available", None))  # missing 2lt
        errors = self.errors_of(partial)
        self.assertTrue(any("OVS coverage" in e and "2lt" in e for e in errors))

    def test_group_integrity(self):
        lone_group = op("add", "rule_groups", {"group_id": "grp_new"},
                        {"group_id": "grp_new", "group_type": "requires_any",
                         "source_id": "opt_one_001", "active": True, "notes": None})
        self.assertTrue(any("member" in e for e in self.errors_of(lone_group)))
        lone_excl = op("add", "exclusive_groups", {"group_id": "excl_new"},
                       {"group_id": "excl_new", "selection_mode": "single_within_group",
                        "active": True, "notes": None})
        self.assertTrue(any("member" in e for e in self.errors_of(lone_excl)))

    def test_display_order_collision_warns(self):
        warnings = self.warnings_of(op("update", "stingray_options", {"option_id": "opt_two_001"},
                                       {"display_order": 10}))
        self.assertTrue(any(w["id"].startswith("dorder:") for w in warnings))

    def test_referenced_delete_warns(self):
        warnings = self.warnings_of(op("delete", "stingray_options", {"option_id": "opt_one_001"}))
        self.assertTrue(any(w["id"].startswith("refdel:") for w in warnings))
        items = [op("delete", "stingray_ovs", {"option_id": "opt_one_001", "variant_id": "1lt"}),
                 op("delete", "stingray_ovs", {"option_id": "opt_one_001", "variant_id": "2lt"}),
                 op("delete", "rule_groups", {"group_id": "grp_one"}),
                 op("delete", "rule_group_members", {"group_id": "grp_one", "target_id": "opt_two_001"}),
                 op("delete", "exclusive_group_members", {"group_id": "excl_one", "option_id": "opt_one_001"}),
                 op("delete", "stingray_options", {"option_id": "opt_one_001"})]
        warnings = self.warnings_of(*items)
        self.assertFalse(any(w["id"] == "refdel:stingray_options:opt_one_001" for w in warnings))

    def test_scaffold_model_warns(self):
        warnings = self.warnings_of(op("update", "zr1_options", {"option_id": "opt_zzz_001"}, {"price": 1}))
        self.assertTrue(any(w["id"] == "scaffold:zr1_options" for w in warnings))


class ApplyBatchTest(unittest.TestCase):
    def setUp(self):
        self._dir = tempfile.TemporaryDirectory()
        self.path = Path(self._dir.name) / "fixture.xlsx"
        build_ops_fixture().save(self.path)
        self.log = Path(self._dir.name) / "log.jsonl"

    def tearDown(self):
        self._dir.cleanup()

    def run_batch(self, *items, write=True, confirmed=(), allow_stale=False, mtime=None):
        b = batch(*items, mtime=self.path.stat().st_mtime_ns if mtime is None else mtime)
        return apply_batch(self.path, b, write=write, confirmed_warnings=confirmed,
                           log_path=self.log, run_schema_validation=False, allow_stale=allow_stale)

    def test_add_option_round_trip_and_table_heal(self):
        result = self.run_batch(add_option_composite())
        self.assertTrue(result["ok"], result)
        wb = load_workbook(self.path)
        ws = wb["stingray_options"]
        rows = {ws.cell(row=r, column=1).value: r for r in range(2, ws.max_row + 1)}
        self.assertIn("opt_new_001", rows)
        r = rows["opt_new_001"]
        self.assertIsInstance(ws.cell(row=r, column=3).value, int)   # price typed
        self.assertIsInstance(ws.cell(row=r, column=8).value, bool)  # selectable typed
        self.assertEqual(ws.tables["tbl_fixture_options"].ref, "A1:K5")  # healed 3 -> 5
        self.assertEqual(wb["stingray_ovs"].max_row, 5)  # 2 ovs rows added
        wb.close()
        self.assertTrue(self.log.exists())
        entry = json.loads(self.log.read_text().splitlines()[-1])
        self.assertEqual(entry["opCount"], 3)
        self.assertIn("stingray_options", entry["sheets"])
        backups = Path(self._dir.name) / "backups"
        self.assertTrue(any(backups.iterdir()))

    def test_update_and_delete(self):
        # mtime passed as a string, as the browser must send it (JS precision)
        result = self.run_batch(
            op("update", "stingray_options", {"option_id": "opt_thr_001"}, {"price": 777, "description": "x"}),
            op("delete", "stingray_ovs", {"option_id": "opt_one_001", "variant_id": "2lt"}),
            mtime=str(self.path.stat().st_mtime_ns),
        )
        self.assertTrue(result["ok"], result)
        wb = load_workbook(self.path)
        ws = wb["stingray_options"]
        r = next(r for r in range(2, ws.max_row + 1) if ws.cell(row=r, column=1).value == "opt_thr_001")
        self.assertEqual(ws.cell(row=r, column=3).value, 777)
        self.assertEqual(wb["stingray_ovs"].max_row, 2)
        wb.close()

    def test_blanking_a_cell(self):
        result = self.run_batch(op("update", "stingray_options", {"option_id": "opt_thr_001"},
                                   {"option_name": ""}))
        self.assertTrue(result["ok"], result)
        wb = load_workbook(self.path)
        ws = wb["stingray_options"]
        r = next(r for r in range(2, ws.max_row + 1) if ws.cell(row=r, column=1).value == "opt_thr_001")
        self.assertIsNone(ws.cell(row=r, column=4).value)
        wb.close()

    def test_validate_only_makes_no_changes(self):
        before = self.path.stat().st_mtime_ns
        result = self.run_batch(add_option_composite(), write=False)
        self.assertTrue(result["ok"])
        self.assertEqual(result["status"], "validated")
        self.assertEqual(self.path.stat().st_mtime_ns, before)
        self.assertFalse(self.log.exists())

    def test_warning_requires_confirmation(self):
        item = op("update", "stingray_options", {"option_id": "opt_two_001"}, {"display_order": 10})
        result = self.run_batch(item)
        self.assertFalse(result["ok"])
        self.assertEqual(result["status"], "needs_confirmation")
        wid = result["warnings"][0]["id"]
        result = self.run_batch(item, confirmed=(wid,))
        self.assertTrue(result["ok"], result)

    def test_invalid_batch_refused(self):
        result = self.run_batch(op("update", "stingray_options", {"option_id": "opt_one_001"},
                                   {"section_id": "sec_nope"}))
        self.assertEqual(result["status"], "invalid")

    def test_lock_and_stale_refusal(self):
        lock = self.path.with_name(f"~${self.path.name}")
        lock.write_text("")
        self.assertEqual(self.run_batch(add_option_composite())["status"], "locked")
        lock.unlink()
        self.assertEqual(self.run_batch(add_option_composite(), mtime=1)["status"], "stale")
        result = self.run_batch(add_option_composite(), mtime=1, allow_stale=True)
        self.assertTrue(result["ok"], result)


@unittest.skipUnless(REAL_WORKBOOK.exists(), "canonical workbook not present")
class RealWorkbookApplyTest(unittest.TestCase):
    def setUp(self):
        self._dir = tempfile.TemporaryDirectory()
        self.path = Path(self._dir.name) / "copy.xlsx"
        shutil.copy2(REAL_WORKBOOK, self.path)
        self.log = Path(self._dir.name) / "log.jsonl"

    def tearDown(self):
        self._dir.cleanup()

    def test_gs_update_heals_stale_table_refs(self):
        wb = load_workbook(self.path)
        self.assertEqual(wb["grandSport_options"].tables["tbl_grandSport_options"].ref, "A1:K267")
        wb.close()
        b = {"version": 1, "workbookMtimeNs": self.path.stat().st_mtime_ns, "items": [
            {"action": "update", "sheet": "grandSport_options", "key": {"option_id": "opt_fey_001"},
             "row": {"detail_raw": "editor apply test"}}]}
        result = apply_batch(self.path, b, write=True, log_path=self.log, source="test")
        self.assertTrue(result["ok"], result)
        self.assertEqual((result["schemaResult"] or {}).get("error_count"), 0)
        wb = load_workbook(self.path)
        self.assertEqual(wb["grandSport_options"].tables["tbl_grandSport_options"].ref, "A1:K274")
        wb.close()

    def test_bad_ref_refused_on_real_workbook(self):
        b = {"version": 1, "workbookMtimeNs": self.path.stat().st_mtime_ns, "items": [
            {"action": "update", "sheet": "stingray_options", "key": {"option_id": "opt_z51_001"},
             "row": {"section_id": "sec_nope"}}]}
        result = apply_batch(self.path, b, write=True, log_path=self.log, source="test")
        self.assertEqual(result["status"], "invalid")


if __name__ == "__main__":
    unittest.main()
