#!/usr/bin/env python3
"""Tests for the workbook-editor lint + cross-model compare module (Phase 3).

Synthetic-extract tests pin each check's behavior; real-workbook tests must
reproduce the named, already-verified findings of the 2026-06-11 consistency
review (docs/archive/old-reports/workbook-consistency-review-2026-06-11.md) — that review is the
ground truth this module makes durable.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from corvette_form_generator.editor_lints import (  # noqa: E402
    compare_options,
    lint_summary,
    load_allowlist,
    run_lints,
)
from corvette_form_generator.editor_ops import extract_workbook  # noqa: E402

REAL_WORKBOOK = ROOT / "stingray_master.xlsx"
ALLOWLIST_PATH = ROOT / "visualizer" / "workbook-editor" / "intentional-differences.json"


def make_extract(sheets: dict[str, list[dict]]) -> dict:
    """Build an extract-shaped dict (same shape as extract_workbook)."""
    out = {}
    for name, rows in sheets.items():
        headers: list[str] = []
        for row in rows:
            for col in row:
                if col not in headers:
                    headers.append(col)
        out[name] = {"headers": headers, "rows": rows}
    return {"path": "fixture", "mtime_ns": 0, "sheets": out}


def lint_fixture() -> dict:
    """One model exercising every lint check."""
    return make_extract({
        "model_master": [
            {"model_key": "m1", "model_label": "M1", "active": True, "default_model": True},
        ],
        "model_registry_promotion": [
            {"model_key": "m1", "promoted_to_runtime": True},
        ],
        "model_workbook_sources": [
            {"model_key": "m1", "source_role": "source_option_sheet", "sheet_name": "m1_options", "active": True},
            {"model_key": "m1", "source_role": "status_sheet", "sheet_name": "m1_ovs", "active": True},
            {"model_key": "m1", "source_role": "exclusive_groups_sheet", "sheet_name": "m1_exclusive_groups", "active": True},
            {"model_key": "m1", "source_role": "exclusive_group_members_sheet", "sheet_name": "m1_exclusive_members", "active": True},
            {"model_key": "m1", "source_role": "rule_groups_sheet", "sheet_name": "m1_rule_groups", "active": True},
            {"model_key": "m1", "source_role": "rule_group_members_sheet", "sheet_name": "m1_rule_group_members", "active": True},
        ],
        "model_variants": [
            {"model_key": "m1", "variant_id": "v1", "active": True},
            {"model_key": "m1", "variant_id": "v2", "active": True},
        ],
        "variant_master": [
            {"variant_id": "v1", "display_name": "V1"},
            {"variant_id": "v2", "display_name": "V2"},
        ],
        "section_master": [
            {"section_id": "sec_a", "section_name": "A"},
            {"section_id": "sec_b", "section_name": "B"},
        ],
        "m1_options": [
            {"option_id": "opt_dup", "rpo": "D1", "section_id": "sec_a",
             "display_order": 10, "selectable": True, "active": True},
            {"option_id": "opt_dup", "rpo": "D1", "section_id": "sec_a",
             "display_order": 11, "selectable": True, "active": True},
            {"option_id": "opt_orphan", "rpo": "OR", "section_id": "sec_missing",
             "display_order": 12, "selectable": False, "active": True},
            {"option_id": "opt_text", "rpo": "TX", "section_id": "sec_b",
             "display_order": "30", "selectable": False, "active": True},
            {"option_id": "opt_c1", "rpo": "C1", "section_id": "sec_b",
             "display_order": 20, "selectable": False, "active": True},
            {"option_id": "opt_c2", "rpo": "C2", "section_id": "sec_b",
             "display_order": 20, "selectable": False, "active": True},
            {"option_id": "opt_cover", "rpo": "CV", "section_id": "sec_a",
             "display_order": 40, "selectable": True, "active": True},
            {"option_id": "opt_dead", "rpo": "DD", "section_id": "sec_a",
             "display_order": 50, "selectable": False, "active": False},
        ],
        "m1_ovs": [
            {"option_id": "opt_dup", "variant_id": "v1", "status": "available"},
            {"option_id": "opt_dup", "variant_id": "v2", "status": "available"},
            {"option_id": "opt_cover", "variant_id": "v1", "status": "available"},
            # opt_cover deliberately has no v2 row -> ovs_coverage
        ],
        "m1_exclusive_groups": [
            {"group_id": "grp_small", "selection_mode": "single_within_group", "active": True},
            {"group_id": "grp_dead_member", "selection_mode": "single_within_group", "active": True},
            {"group_id": "grp_off", "selection_mode": "single_within_group", "active": False},
        ],
        "m1_exclusive_members": [
            {"group_id": "grp_small", "option_id": "opt_c1", "display_order": 10, "active": True},
            {"group_id": "grp_dead_member", "option_id": "opt_c1", "display_order": 10, "active": True},
            {"group_id": "grp_dead_member", "option_id": "opt_dead", "display_order": 20, "active": True},
        ],
        "m1_rule_groups": [
            {"group_id": "rg_empty", "group_type": "requires_any", "source_id": "opt_c1", "active": True},
        ],
        "m1_rule_group_members": [],
        "misc_meta": [
            {"meta_id": "x1", "active": "TRUE"},
            {"meta_id": "x2", "active": True},
        ],
    })


def compare_fixture() -> dict:
    """Three models exercising joins, majority labeling, and rank compare."""
    def opt(oid, rpo, name, section, order, desc="same"):
        return {"option_id": oid, "rpo": rpo, "option_name": name,
                "section_id": section, "display_order": order,
                "description": desc, "selectable": True, "active": True}

    return make_extract({
        "model_master": [
            {"model_key": k, "model_label": k, "active": True} for k in ("ma", "mb", "mc")
        ],
        "model_registry_promotion": [
            {"model_key": k, "promoted_to_runtime": True} for k in ("ma", "mb", "mc")
        ],
        "model_workbook_sources": [
            {"model_key": k, "source_role": "source_option_sheet",
             "sheet_name": f"{k}_options", "active": True} for k in ("ma", "mb", "mc")
        ],
        "section_master": [{"section_id": "sec_s", "section_name": "S"}],
        "ma_options": [
            opt("opt_x", "XX", "Alpha", "sec_s", 5),
            opt("opt_r_001", "RR", "Same Name", "sec_s", 6),
            opt("opt_m_001", "MM", "Multi A1", "sec_s", 7),
            opt("opt_m_002", "MM", "Multi A2", "sec_s", 8),
            opt("opt_o1", "O1", "Order One", "sec_s", 10),
            opt("opt_o2", "O2", "Order Two", "sec_s", 20),
        ],
        "mb_options": [
            opt("opt_x", "XX", "Beta", "sec_s", 5),
            opt("opt_r_001", "RR", "Same Name", "sec_s", 6),
            opt("opt_o1", "O1", "Order One", "sec_s", 10),
            opt("opt_o2", "O2", "Order Two", "sec_s", 20),
        ],
        "mc_options": [
            opt("opt_x", "XX", "Beta", "sec_s", 5),
            opt("opt_r_002", "RR", "Same Name", "sec_s", 6),
            opt("opt_m_003", "MM", "Multi C", "sec_s", 7),
            opt("opt_o1", "O1", "Order One", "sec_s", 30),  # after o2 -> rank swap
            opt("opt_o2", "O2", "Order Two", "sec_s", 20),
        ],
    })


def lints_by_id(lints):
    out: dict[str, list] = {}
    for lint in lints:
        out.setdefault(lint["id"], []).append(lint)
    return out


class LintFixtureTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lints = run_lints(lint_fixture())
        cls.by_id = lints_by_id(cls.lints)

    def test_duplicate_key(self):
        keys = [(l["sheet"], l["key"]) for l in self.by_id.get("duplicate_key", [])]
        self.assertEqual(keys, [("m1_options", "opt_dup")])

    def test_orphan_ref(self):
        orphans = self.by_id.get("orphan_ref", [])
        self.assertEqual([l["key"] for l in orphans], ["opt_orphan"])
        self.assertIn("sec_missing", orphans[0]["message"])

    def test_display_order_type(self):
        rows = self.by_id.get("display_order_type", [])
        self.assertEqual([l["key"] for l in rows], ["opt_text"])
        self.assertEqual(rows[0]["severity"], "error")

    def test_display_order_collision(self):
        keys = {l["key"] for l in self.by_id.get("display_order_collision", [])
                if l["sheet"] == "m1_options"}
        self.assertEqual(keys, {"opt_c1", "opt_c2"})

    def test_ovs_coverage(self):
        rows = self.by_id.get("ovs_coverage", [])
        self.assertEqual([l["key"] for l in rows], ["opt_cover+v2"])
        self.assertEqual(rows[0]["sheet"], "m1_ovs")

    def test_group_integrity(self):
        rows = self.by_id.get("group_integrity", [])
        keys = {(l["sheet"], l["key"]) for l in rows}
        self.assertIn(("m1_exclusive_groups", "grp_small"), keys)        # <2 members
        self.assertIn(("m1_exclusive_members", "grp_dead_member+opt_dead"), keys)
        self.assertIn(("m1_rule_groups", "rg_empty"), keys)              # 0 members
        self.assertNotIn(("m1_exclusive_groups", "grp_off"), keys)       # inactive group

    def test_boolean_text_uppercase_only(self):
        rows = self.by_id.get("boolean_text", [])
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["sheet"], "misc_meta")
        self.assertEqual(rows[0]["cells"], ["active"])

    def test_summary_counts_match(self):
        summary = lint_summary(self.lints)
        self.assertEqual(sum(summary.values()), len(self.lints))


class CompareFixtureTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.result = compare_options(compare_fixture(), [])
        cls.by_key = {r["joinKey"]: r for r in cls.result["rows"]}

    def test_models_and_shared_count(self):
        self.assertEqual(self.result["models"], ["ma", "mb", "mc"])
        # opt_x, opt_r (rpo-joined), opt_o1, opt_o2 are fully shared
        self.assertEqual(self.result["sharedCount"], 4)

    def test_majority_and_deviator(self):
        diff = next(d for d in self.by_key["opt_x"]["diffs"] if d["field"] == "option_name")
        self.assertEqual(diff["majority"], "Beta")
        self.assertEqual(diff["deviators"], ["ma"])

    def test_rpo_fallback_join(self):
        row = self.by_key.get("opt_r_001")
        if row is None:  # no divergence -> verify via model-only absence
            ids = [o["id"] for o in self.result["modelOnly"].get("mc", [])]
            self.assertNotIn("opt_r_002", ids)
        else:
            self.assertEqual(row["joinedVia"], "rpo")

    def test_ambiguous_rpo_not_merged(self):
        ids = [o["id"] for o in self.result["modelOnly"].get("mc", [])]
        self.assertIn("opt_m_003", ids)

    def test_relative_display_order_deviation(self):
        diffs = {d["field"]: d for d in self.by_key["opt_o1"]["diffs"]}
        self.assertIn("display_order", diffs)
        self.assertEqual(diffs["display_order"]["deviators"], ["mc"])

    def test_allowlist_suppression_and_stale(self):
        allowlist = [
            {"option_id": "opt_x", "field": "option_name", "models": ["ma"],
             "status": "intentional", "reason": "ma copy is intentional"},
            {"option_id": "opt_x", "field": "section_id", "models": ["ma"],
             "status": "intentional", "reason": "never matches"},
            {"option_id": "opt_o1", "field": "display_order", "models": ["mc"],
             "status": "pending-review", "reason": "decision pending"},
        ]
        result = compare_options(compare_fixture(), allowlist)
        by_key = {r["joinKey"]: r for r in result["rows"]}
        name_diff = next(d for d in by_key["opt_x"]["diffs"] if d["field"] == "option_name")
        self.assertEqual(name_diff["status"], "intentional")
        self.assertEqual(name_diff["reason"], "ma copy is intentional")
        order_diff = next(d for d in by_key["opt_o1"]["diffs"] if d["field"] == "display_order")
        self.assertEqual(order_diff["status"], "pending-review")
        self.assertEqual([e["reason"] for e in result["staleAllowlist"]], ["never matches"])


@unittest.skipUnless(REAL_WORKBOOK.exists(), "canonical workbook not present")
class RealWorkbookLintTest(unittest.TestCase):
    """Reproduce the named findings of the 2026-06-11 consistency review."""

    @classmethod
    def setUpClass(cls):
        cls.extract = extract_workbook(REAL_WORKBOOK)
        cls.lints = run_lints(cls.extract)
        cls.by_id = lints_by_id(cls.lints)

    def test_d1_rwj_wks_collision(self):
        hits = [l for l in self.by_id.get("display_order_collision", [])
                if l["sheet"] == "z06_options" and "sec_lpoe_001" in l["message"]]
        keys = {l["key"] for l in hits}
        self.assertIn("opt_rwj_001", keys)
        self.assertIn("opt_wks_001", keys)
        self.assertTrue(all("72" in l["message"] for l in hits))

    def test_s1_s2_display_order_typing_clean(self):
        # S-1/S-2 (and the z06_rule_group_members rows this lint surfaced)
        # were retyped to integers on 2026-06-12 via the editor op pipeline;
        # the lint that found them now guards the fix workbook-wide.
        self.assertEqual(self.by_id.get("display_order_type", []), [])

    def test_s10_boolean_text_clean(self):
        # S-10 boolean-as-text rows were converted to real Excel booleans on
        # 2026-06-12. Keep the workbook-wide lint as a regression guard.
        self.assertEqual(self.by_id.get("boolean_text", []), [])

    def test_negative_no_duplicate_keys_or_orphan_refs(self):
        # schema-validator baseline: the current workbook is referentially clean
        self.assertEqual(self.by_id.get("duplicate_key", []), [])
        self.assertEqual(self.by_id.get("orphan_ref", []), [])


@unittest.skipUnless(REAL_WORKBOOK.exists(), "canonical workbook not present")
class RealWorkbookCompareTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.extract = extract_workbook(REAL_WORKBOOK)
        cls.allowlist = load_allowlist(ALLOWLIST_PATH)
        cls.result = compare_options(cls.extract, cls.allowlist)
        cls.by_key = {r["joinKey"]: r for r in cls.result["rows"]}

    def test_allowlist_file_committed_and_loaded(self):
        self.assertTrue(ALLOWLIST_PATH.exists())
        self.assertTrue(len(self.allowlist) >= 5)
        for entry in self.allowlist:
            self.assertIn(entry.get("status"), ("intentional", "pending-review"))
            self.assertTrue(entry.get("reason"))

    def test_compared_models_exclude_scaffolds(self):
        self.assertEqual(self.result["models"], ["grand_sport", "stingray", "z06"])

    def test_c1_eyt_description_flagged(self):
        diffs = {d["field"]: d for d in self.by_key["opt_eyt_001"]["diffs"]}
        self.assertIn("description", diffs)
        self.assertNotEqual(diffs["description"]["status"], "intentional")

    def test_c2_cj2_stingray_name_deviator(self):
        diff = next(d for d in self.by_key["opt_cj2_001"]["diffs"]
                    if d["field"] == "option_name")
        self.assertEqual(diff["deviators"], ["stingray"])
        self.assertEqual(diff["majority"], "Dual-Zone Automatic Climate Control")

    def test_s4_rpo_fallback_keys(self):
        # U2K diverges, so it must surface as a single rpo-joined row
        row = self.by_key["opt_u2k_001"]
        self.assertEqual(row["joinedVia"], "rpo")
        self.assertEqual(row["optionIds"]["z06"], "opt_u2k_002")
        # none of the S-4 _002 keys may be stranded as z06-only
        z06_only = {o["id"] for o in self.result["modelOnly"]["z06"]}
        for oid in ("opt_u2k_002", "opt_u5g_002", "opt_ue1_002",
                    "opt_vv4_002", "opt_cfv_002"):
            self.assertNotIn(oid, z06_only)

    def test_zz3_includes_difference_suppressed(self):
        diff = next(d for d in self.by_key["opt_zz3_001"]["diffs"]
                    if d["field"] == "description")
        self.assertEqual(diff["status"], "intentional")
        self.assertIn("BC7", diff["reason"])

    def test_r3_drz_pending_review(self):
        diff = next(d for d in self.by_key["opt_drz_001"]["diffs"]
                    if d["field"] == "option_name")
        self.assertEqual(diff["status"], "pending-review")
        self.assertTrue(diff["reason"].startswith("R-3"))

    def test_no_stale_allowlist_entries(self):
        self.assertEqual(self.result["staleAllowlist"], [])


if __name__ == "__main__":
    unittest.main()
