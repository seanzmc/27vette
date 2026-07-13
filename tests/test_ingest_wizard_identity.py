#!/usr/bin/env python3
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

from corvette_form_generator.ingest.wizard.identity import (  # noqa: E402
    allocate_ids,
    deterministic_family_id,
    match_option_occurrences,
    option_occurrence_signature,
    reconcile_rows,
)


class IdentityContractTest(unittest.TestCase):
    def candidate(self, rpo: str, description: str, *, section: str = "sec_whee_001", statuses=None, price=0):
        return {
            "rpo": rpo,
            "description": description,
            "section_id": section,
            "statuses": statuses or [{"modelCode": "1YR07", "trim": "1LZ", "bodyStyle": "coupe", "status": "available"}],
            "listPrice": price,
            "relationshipRoles": [],
        }

    def existing(self, option_id: str, rpo: str, description: str, *, section="sec_whee_001", price=0):
        return {
            "option_id": option_id,
            "rpo": rpo,
            "description": description,
            "section_id": section,
            "price": price,
            "statuses": [{"modelCode": "1YR07", "trim": "1LZ", "bodyStyle": "coupe", "status": "available"}],
            "active": False,
            "selectable": True,
        }

    def test_occurrence_signature_excludes_coordinates_and_order(self) -> None:
        base = self.candidate("PDB", "Carbon wheel package", price=16000)
        moved = dict(base, candidateId="Equipment Groups 4:999", rowIndex=999, display_order=77)
        self.assertEqual(option_occurrence_signature(base), option_occurrence_signature(moved))

    def test_unique_signature_reuses_existing_id(self) -> None:
        candidate = self.candidate("PDB", "Carbon wheel package", price=16000)
        existing = self.existing("opt_pdb_001", "PDB", "Carbon wheel package", price=16000)
        result = match_option_occurrences([candidate], [existing])
        self.assertEqual(result[0]["optionId"], "opt_pdb_001")
        self.assertEqual(result[0]["matchStage"], "full_occurrence_signature")

    def test_ambiguous_duplicate_is_blocked(self) -> None:
        candidate = self.candidate("PDB", "Carbon wheel package", price=16000)
        existing = [
            self.existing("opt_pdb_001", "PDB", "Carbon wheel package", price=16000),
            self.existing("opt_pdb_002", "PDB", "Carbon wheel package", price=16000),
        ]
        result = match_option_occurrences([candidate], existing)
        self.assertEqual(result[0]["status"], "ambiguous")
        self.assertEqual(result[0]["candidateIds"], ["opt_pdb_001", "opt_pdb_002"])

    def test_no_rpo_standard_row_matches_unique_existing_copy_identity(self) -> None:
        candidate = self.candidate("", "Air filtration system with pollen filter")
        candidate["rowKind"] = "standard_no_rpo"
        existing = self.existing("opt_509", "", "Air filtration system with pollen filter")

        result = match_option_occurrences([candidate], [existing])

        self.assertEqual(result[0]["status"], "matched")
        self.assertEqual(result[0]["optionId"], "opt_509")
        self.assertEqual(result[0]["matchStage"], "no_rpo_copy_identity")

    def test_matching_stages_apply_globally_before_weaker_candidates(self) -> None:
        exact = self.candidate("PDB", "Carbon wheel package", price=16000)
        weaker = self.candidate("PDB", "Different copy", price=16000)
        existing = self.existing("opt_pdb_001", "PDB", "Carbon wheel package", price=16000)
        first = match_option_occurrences([weaker, exact], [existing])
        second = match_option_occurrences([exact, weaker], [existing])
        by_copy = lambda rows: {row["candidate"]["description"]: row for row in rows}
        for result in (by_copy(first), by_copy(second)):
            self.assertEqual(result["Carbon wheel package"]["optionId"], "opt_pdb_001")
            self.assertEqual(result["Carbon wheel package"]["matchStage"], "full_occurrence_signature")
            self.assertEqual(result["Different copy"]["status"], "new")

    def test_new_option_ids_are_reserved_and_input_order_invariant(self) -> None:
        candidates = [
            self.candidate("PDB", "Carbon wheel package, ROY", price=16000),
            self.candidate("PDB", "Carbon wheel package, ROZ", price=17000),
        ]
        first = allocate_ids("options", "zr1", candidates, reserved_ids={"opt_pdb_001"})
        second = allocate_ids("options", "zr1", list(reversed(candidates)), reserved_ids={"opt_pdb_001"})
        by_signature = lambda rows: {row["semanticSignature"]: row["allocatedId"] for row in rows}
        self.assertEqual(by_signature(first), by_signature(second))
        self.assertEqual(set(by_signature(first).values()), {"opt_pdb_002", "opt_pdb_003"})

    def test_new_no_rpo_standard_ids_are_deterministic_and_order_invariant(self) -> None:
        candidates = [
            {**self.candidate("", "Air filtration system"), "rowKind": "standard_no_rpo"},
            {**self.candidate("", "Carpeted floor mats"), "rowKind": "standard_no_rpo"},
        ]

        first = allocate_ids("options", "grand_sport_x", candidates)
        second = allocate_ids("options", "grand_sport_x", list(reversed(candidates)))
        by_signature = lambda rows: {row["semanticSignature"]: row["allocatedId"] for row in rows}

        self.assertEqual(by_signature(first), by_signature(second))
        self.assertTrue(all(identifier.startswith("opt_std_") for identifier in by_signature(first).values()))
        self.assertEqual(len(set(by_signature(first).values())), 2)

    def test_non_option_id_format_is_stable_and_model_local(self) -> None:
        first = deterministic_family_id("rule_mapping", "zr1", {"sourceRpo": "PDB", "ruleType": "requires", "targetRpo": "PEF"})
        second = deterministic_family_id("rule_mapping", "zr1", {"targetRpo": "PEF", "ruleType": "requires", "sourceRpo": "PDB"})
        self.assertEqual(first, second)
        self.assertTrue(first.startswith("zr1_rule_pdb_requires_pef_"))
        self.assertEqual(len(first.rsplit("_", 1)[-1]), 12)

    def test_reconcile_rows_reuses_ovs_composite_key(self) -> None:
        desired = [{"option_id": "opt_pdb_001", "variant_id": "1lz_r07", "status": "available"}]
        existing = [{"option_id": "opt_pdb_001", "variant_id": "1lz_r07", "status": "available"}]
        result = reconcile_rows("ovs", desired, existing, key_columns=("option_id", "variant_id"))
        self.assertEqual(result[0]["action"], "noop")

    def test_reconcile_retains_unmatched_existing_without_removal_evidence(self) -> None:
        result = reconcile_rows("options", [], [self.existing("opt_old_001", "OLD", "Established")], key_columns=("option_id",))
        self.assertEqual(result[0]["action"], "retained_existing")

    def test_reconcile_blocks_delete_with_surviving_reference(self) -> None:
        existing = [self.existing("opt_old_001", "OLD", "Established")]
        result = reconcile_rows(
            "options",
            [],
            existing,
            key_columns=("option_id",),
            removals={"opt_old_001"},
            incoming_references={"opt_old_001": [{"sheet": "zr1_rule_mapping", "key": "rule-1"}]},
        )
        self.assertEqual(result[0]["action"], "blocked")
        self.assertEqual(result[0]["reasonCode"], "surviving_incoming_reference")


if __name__ == "__main__":
    unittest.main()
