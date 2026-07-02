#!/usr/bin/env python3
"""Unit tests for includes-closure swap-rule derivation (rule_derivation.py).

Spec: docs/derived-swap-eviction-spec-2026-07-02.md §2 A1/A1b/A2/A3/A6.
"""

from __future__ import annotations

import unittest

from corvette_form_generator.rule_derivation import (
    EMISSION_ALLOWLIST,
    StaleDerivationAllowlistError,
    derive_swap_rules,
)


def rule(rule_id, source_id, rule_type, target_id, *, runtime_action="", active="True"):
    return {
        "rule_id": rule_id,
        "source_id": source_id,
        "rule_type": rule_type,
        "target_id": target_id,
        "runtime_action": runtime_action,
        "active": active,
    }


LABELS = {
    "opt_z07_001": "Z07 Performance Package",
    "opt_t0f_001": "T0F Carbon Aero",
    "opt_cfz_001": "CFZ Carbon Flash Ground Effects",
    "opt_cbf_001": "CBF Body-color Rockers and Splitter",
    "opt_pdd_001": "PDD Package",
}


def label(entity_id):
    return LABELS.get(entity_id, entity_id)


def meta(source_id, target_id):
    return {
        "target_type": "option",
        "source_type": "option",
        "source_section": "sec_a",
        "target_section": "sec_b",
        "source_selection_mode": "multi",
        "target_selection_mode": "multi",
    }


def derive(model_key, rules):
    return derive_swap_rules(model_key, rules, label, meta)


class ClosureWalkTests(unittest.TestCase):
    def test_single_hop_candidate(self):
        rules = [
            rule("inc1", "opt_t0f_001", "includes", "opt_cfz_001"),
            rule("exc1", "opt_cbf_001", "excludes", "opt_cfz_001"),
        ]
        emitted, manifest = derive("testmodel", rules)
        self.assertEqual(emitted, [])
        self.assertEqual(manifest["candidate_count"], 1)
        entry = manifest["entries"][0]
        self.assertEqual(entry["disposition"], "candidate_not_emitted")
        self.assertEqual(entry["source_id"], "opt_t0f_001")
        self.assertEqual(entry["target_id"], "opt_cbf_001")
        self.assertEqual(entry["derived_via"]["includes_path"], ["opt_t0f_001", "opt_cfz_001"])
        self.assertEqual(entry["derived_via"]["primitive_rule_id"], "exc1")

    def test_multi_hop_closure(self):
        # PDD -> Z07 -> T0F -> CFZ; CBF excludes CFZ => PDD evicts CBF.
        rules = [
            rule("inc1", "opt_pdd_001", "includes", "opt_z07_001"),
            rule("inc2", "opt_z07_001", "includes", "opt_t0f_001"),
            rule("inc3", "opt_t0f_001", "includes", "opt_cfz_001"),
            rule("exc1", "opt_cbf_001", "excludes", "opt_cfz_001"),
        ]
        _, manifest = derive("testmodel", rules)
        pdd = [e for e in manifest["entries"] if e["source_id"] == "opt_pdd_001"]
        self.assertEqual(len(pdd), 1)
        self.assertEqual(
            pdd[0]["derived_via"]["includes_path"],
            ["opt_pdd_001", "opt_z07_001", "opt_t0f_001", "opt_cfz_001"],
        )

    def test_cycle_guard(self):
        rules = [
            rule("inc1", "a", "includes", "b"),
            rule("inc2", "b", "includes", "a"),
            rule("exc1", "x", "excludes", "b"),
        ]
        _, manifest = derive("testmodel", rules)  # must terminate
        self.assertEqual(
            {(e["source_id"], e["target_id"]) for e in manifest["entries"]},
            {("a", "x")},
        )

    def test_inactive_rules_ignored(self):
        rules = [
            rule("inc1", "opt_t0f_001", "includes", "opt_cfz_001", active="False"),
            rule("exc1", "opt_cbf_001", "excludes", "opt_cfz_001"),
        ]
        _, manifest = derive("testmodel", rules)
        self.assertEqual(manifest["candidate_count"], 0)

    def test_stacked_replace_rows_are_not_primitives(self):
        rules = [
            rule("inc1", "opt_t0f_001", "includes", "opt_cfz_001"),
            rule("stk", "opt_z07_001", "excludes", "opt_cbf_001", runtime_action="replace"),
        ]
        _, manifest = derive("testmodel", rules)
        self.assertEqual(manifest["candidate_count"], 0)

    def test_self_pairs_excluded(self):
        rules = [
            rule("inc1", "a", "includes", "b"),
            rule("exc1", "a", "excludes", "b"),
        ]
        _, manifest = derive("testmodel", rules)
        self.assertEqual(manifest["candidate_count"], 0)


class ShadowingTests(unittest.TestCase):
    def test_authored_replace_row_shadows_candidate(self):
        rules = [
            rule("inc1", "opt_t0f_001", "includes", "opt_cfz_001"),
            rule("exc1", "opt_cbf_001", "excludes", "opt_cfz_001"),
            rule("auth", "opt_t0f_001", "excludes", "opt_cbf_001", runtime_action="replace"),
        ]
        emitted, manifest = derive("testmodel", rules)  # shadowing precedes allowlist gating
        self.assertEqual(emitted, [])
        entry = [e for e in manifest["entries"] if e["source_id"] == "opt_t0f_001"][0]
        self.assertEqual(entry["disposition"], "shadowed_by_authored")
        self.assertEqual(manifest["shadowed_count"], 1)


class AllowlistGatingTests(unittest.TestCase):
    def z06_cbf_rules(self):
        return [
            rule("inc1", "opt_t0f_001", "includes", "opt_cfz_001"),
            rule("inc2", "opt_t0g_001", "includes", "opt_cfv_002"),
            rule("inc3", "opt_z07_001", "includes", "opt_t0f_001"),
            rule("inc4", "opt_pdd_001", "includes", "opt_z07_001"),
            rule("inc5", "opt_pdf_001", "includes", "opt_z07_001"),
            rule("inc5b", "opt_pdf_001", "includes", "opt_cfv_002"),
            rule("exc1", "opt_cbf_001", "excludes", "opt_cfz_001"),
            rule("exc2", "opt_cbf_001", "excludes", "opt_cfv_002"),
        ]

    def test_allowlisted_candidates_emit_on_z06(self):
        emitted, manifest = derive("z06", self.z06_cbf_rules())
        emitted_pairs = {(r["source_id"], r["target_id"]) for r in emitted}
        self.assertEqual(
            emitted_pairs,
            {
                ("opt_t0f_001", "opt_cbf_001"),
                ("opt_t0g_001", "opt_cbf_001"),
                ("opt_z07_001", "opt_cbf_001"),
                ("opt_pdd_001", "opt_cbf_001"),
                ("opt_pdf_001", "opt_cbf_001"),
            },
        )
        self.assertEqual(manifest["emitted_count"], 5)

    def test_same_graph_on_other_model_emits_nothing(self):
        emitted, manifest = derive("stingray", self.z06_cbf_rules())
        self.assertEqual(emitted, [])
        self.assertEqual(manifest["emitted_count"], 0)
        self.assertTrue(
            all(e["disposition"] == "candidate_not_emitted" for e in manifest["entries"])
        )

    def test_stale_allowlist_hard_error(self):
        # z06 allowlist pairs exist but the includes graph no longer produces them.
        rules = [
            rule("exc1", "opt_cbf_001", "excludes", "opt_cfz_001"),
        ]
        with self.assertRaises(StaleDerivationAllowlistError):
            derive("z06", rules)

    def test_duplicate_paths_emit_single_rule(self):
        # PDF reaches CBF via two paths (direct CFV include and Z07->T0F->CFZ);
        # only one rule may be emitted for the pair.
        emitted, manifest = derive("z06", self.z06_cbf_rules())
        pdf_rules = [r for r in emitted if r["source_id"] == "opt_pdf_001"]
        self.assertEqual(len(pdf_rules), 1)
        dispositions = [
            e["disposition"]
            for e in manifest["entries"]
            if (e["source_id"], e["target_id"]) == ("opt_pdf_001", "opt_cbf_001")
        ]
        self.assertEqual(sorted(dispositions), ["duplicate_path_not_emitted", "emitted"])


class EmittedRuleShapeTests(unittest.TestCase):
    def test_no_derived_fields_on_emitted_rules(self):
        rules = [
            rule("inc1", "opt_t0f_001", "includes", "opt_cfz_001"),
            rule("inc2", "opt_t0g_001", "includes", "opt_cfv_002"),
            rule("inc3", "opt_z07_001", "includes", "opt_t0f_001"),
            rule("inc4", "opt_pdd_001", "includes", "opt_z07_001"),
            rule("inc5", "opt_pdf_001", "includes", "opt_z07_001"),
            rule("exc1", "opt_cbf_001", "excludes", "opt_cfz_001"),
            rule("exc2", "opt_cbf_001", "excludes", "opt_cfv_002"),
        ]
        emitted, _ = derive("z06", rules)
        self.assertTrue(emitted)
        for emitted_rule in emitted:
            for key in emitted_rule:
                self.assertFalse(
                    key.startswith("derived"),
                    f"provenance is manifest-only; found contract field {key!r}",
                )
            self.assertEqual(emitted_rule["runtime_action"], "replace")
            self.assertEqual(emitted_rule["rule_type"], "excludes")
            self.assertEqual(emitted_rule["active"], "True")

    def test_verbose_reason_copy(self):
        rules = [
            rule("inc1", "opt_t0f_001", "includes", "opt_cfz_001"),
            rule("inc2", "opt_t0g_001", "includes", "opt_cfv_002"),
            rule("inc3", "opt_z07_001", "includes", "opt_t0f_001"),
            rule("inc4", "opt_pdd_001", "includes", "opt_z07_001"),
            rule("inc5", "opt_pdf_001", "includes", "opt_z07_001"),
            rule("exc1", "opt_cbf_001", "excludes", "opt_cfz_001"),
            rule("exc2", "opt_cbf_001", "excludes", "opt_cfv_002"),
        ]
        emitted, _ = derive("z06", rules)
        t0f = [r for r in emitted if r["source_id"] == "opt_t0f_001"][0]
        self.assertEqual(
            t0f["disabled_reason"],
            "CBF Body-color Rockers and Splitter was removed: T0F Carbon Aero includes "
            "CFZ Carbon Flash Ground Effects, which replaces it.",
        )
        self.assertNotIn("default", t0f["disabled_reason"])


class DeterminismTests(unittest.TestCase):
    def test_deterministic_across_input_order(self):
        base = [
            rule("inc1", "opt_t0f_001", "includes", "opt_cfz_001"),
            rule("inc2", "opt_t0g_001", "includes", "opt_cfv_002"),
            rule("inc3", "opt_z07_001", "includes", "opt_t0f_001"),
            rule("inc4", "opt_pdd_001", "includes", "opt_z07_001"),
            rule("inc5", "opt_pdf_001", "includes", "opt_z07_001"),
            rule("exc1", "opt_cbf_001", "excludes", "opt_cfz_001"),
            rule("exc2", "opt_cbf_001", "excludes", "opt_cfv_002"),
        ]
        emitted_a, manifest_a = derive("z06", base)
        emitted_b, manifest_b = derive("z06", list(reversed(base)))
        self.assertEqual(emitted_a, emitted_b)
        self.assertEqual(manifest_a, manifest_b)


class CurrentAllowlistScopeTests(unittest.TestCase):
    def test_allowlist_is_exactly_the_five_z06_cbf_pairs(self):
        self.assertEqual(
            EMISSION_ALLOWLIST,
            frozenset(
                {
                    ("z06", "opt_t0f_001", "opt_cbf_001"),
                    ("z06", "opt_t0g_001", "opt_cbf_001"),
                    ("z06", "opt_z07_001", "opt_cbf_001"),
                    ("z06", "opt_pdd_001", "opt_cbf_001"),
                    ("z06", "opt_pdf_001", "opt_cbf_001"),
                }
            ),
        )


if __name__ == "__main__":
    unittest.main()
