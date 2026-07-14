#!/usr/bin/env python3
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for entry in (ROOT / "scripts", ROOT / "tests"):
    if str(entry) not in sys.path:
        sys.path.insert(0, str(entry))

from corvette_form_generator.ingest.wizard.relationship_compiler import (  # noqa: E402
    compile_relationships,
    load_compiler_phrase_map,
    scan_text,
)
from ingest_wizard_fixtures import build_master_workbook  # noqa: E402


class RelationshipCompilerTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.workbook = build_master_workbook(Path(self.tmp.name) / "master.xlsx")
        self.phrases = load_compiler_phrase_map(self.workbook)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_requires_workbook_authored_phrase_rows(self) -> None:
        empty = Path(self.tmp.name) / "empty.xlsx"
        from openpyxl import Workbook
        wb = Workbook()
        wb.save(empty)
        with self.assertRaisesRegex(ValueError, "rule_phrase_map"):
            load_compiler_phrase_map(empty)

    def test_included_with_reverses_direction(self) -> None:
        hits = scan_text("Personalized plaque included with (PEF).", self.phrases)
        hit = next(item for item in hits if item["phraseKey"] == "included with")
        self.assertEqual(hit["ruleType"], "includes")
        self.assertEqual(hit["direction"], "mentioned_to_source")
        compiled = compile_relationships(
            [{"candidateId": "row:1", "rpo": "BV4", "description": "Personalized plaque included with (PEF)."}],
            self.phrases,
            target_rpos={"BV4", "PEF"},
        )
        row = compiled["rows"][0]
        self.assertEqual((row["sourceRpo"], row["targetRpo"]), ("PEF", "BV4"))

    def test_stop_phrase_bounds_token_scan(self) -> None:
        hits = scan_text("Package requires (PDB) or included with (PEF)", self.phrases)
        requires = next(item for item in hits if item["phraseKey"] == "requires")
        self.assertEqual(requires["rpoTokens"], ["PDB"])

    def test_unknown_endpoint_is_typed_blocker(self) -> None:
        compiled = compile_relationships(
            [{"candidateId": "row:2", "rpo": "BV4", "description": "Not available with (ZZZ)."}],
            self.phrases,
            target_rpos={"BV4"},
        )
        self.assertEqual(compiled["rows"], [])
        self.assertEqual(compiled["exceptions"][0]["reasonCode"], "unresolved_relationship_endpoint")
        self.assertEqual(compiled["exceptions"][0]["allowedActions"], [])

    def test_interior_code_expands_to_typed_canonical_interior_endpoints(self) -> None:
        compiled = compile_relationships(
            [
                {
                    "candidateId": "row:interior",
                    "rpo": "3M9",
                    "description": "Not available with (HU2) Adrenaline Red interiors.",
                }
            ],
            self.phrases,
            target_rpos={"3M9"},
            endpoint_catalog={
                "HU2": [
                    {"endpointType": "interior", "endpointId": "3LZ_AH2_HU2"},
                    {"endpointType": "interior", "endpointId": "3LZ_AE4_HU2"},
                ]
            },
        )
        self.assertEqual(compiled["exceptions"], [])
        self.assertEqual(
            {row["targetId"] for row in compiled["rows"]},
            {"3LZ_AH2_HU2", "3LZ_AE4_HU2"},
        )
        self.assertEqual(
            {row["targetType"] for row in compiled["rows"]},
            {"interior"},
        )

    def test_descriptive_model_and_seat_aliases_are_not_product_endpoints(self) -> None:
        compiled = compile_relationships(
            [
                {
                    "candidateId": "row:aliases",
                    "rpo": "TU7",
                    "description": "Requires (AH2) GT2 seats on ZR1 and ZR1X.",
                }
            ],
            self.phrases,
            target_rpos={"TU7", "AH2"},
            ignored_endpoint_tokens={"GT2", "ZR1", "ZR1X"},
        )
        self.assertEqual(compiled["exceptions"], [])
        self.assertEqual(
            [(row["sourceRpo"], row["targetRpo"]) for row in compiled["rows"]],
            [("TU7", "AH2")],
        )

    def test_multi_interior_requires_stays_a_typed_tooling_blocker(self) -> None:
        compiled = compile_relationships(
            [
                {
                    "candidateId": "row:requires-interior",
                    "rpo": "N26",
                    "description": "Requires (HU6) Sky Cool Gray Suede interiors.",
                }
            ],
            self.phrases,
            target_rpos={"N26"},
            endpoint_catalog={
                "HU6": [
                    {"endpointType": "interior", "endpointId": "2LT_AH2_HU6_N26"},
                    {"endpointType": "interior", "endpointId": "2LT_AE4_HU6_N26"},
                ]
            },
        )
        self.assertEqual(compiled["rows"], [])
        self.assertEqual(
            [item["reasonCode"] for item in compiled["exceptions"]],
            ["unresolved_relationship_identity"],
        )
        self.assertEqual(compiled["exceptions"][0]["allowedActions"], [])

    def test_profile_requirement_consumes_multi_interior_include_without_direct_rules(self) -> None:
        compiled = compile_relationships(
            [
                {
                    "candidateId": "row:profile-include",
                    "rpo": "Z25",
                    "description": "Includes (EL9) Santorini Blue Dipped interior.",
                }
            ],
            self.phrases,
            target_rpos={"Z25"},
            endpoint_catalog={
                "EL9": [
                    {
                        "endpointType": "interior",
                        "endpointId": "3LT_AE4_EL9",
                        "profileRequiredRpo": "Z25",
                    },
                    {
                        "endpointType": "interior",
                        "endpointId": "3LT_AH2_EL9",
                        "profileRequiredRpo": "Z25",
                    },
                ]
            },
        )
        self.assertEqual(compiled["exceptions"], [])
        self.assertEqual(compiled["rows"], [])
        self.assertEqual(
            compiled["dispositions"][0]["disposition"],
            "compiled_profile_effect",
        )

    def test_replaces_without_active_representation_is_exception(self) -> None:
        compiled = compile_relationships(
            [{"candidateId": "row:3", "rpo": "BV4", "description": "Replaces (PDB)."}],
            self.phrases,
            target_rpos={"BV4", "PDB"},
            active_rule_types={"requires", "includes", "excludes"},
        )
        self.assertEqual(compiled["exceptions"][0]["reasonCode"], "unsupported_relationship_type")

    def test_non_product_prose_gets_explicit_disposition(self) -> None:
        compiled = compile_relationships(
            [{"candidateId": "row:4", "rpo": "BV4", "description": "Hand polished by specialists."}],
            self.phrases,
            target_rpos={"BV4"},
        )
        self.assertEqual(compiled["dispositions"][0]["disposition"], "resolved_not_a_workbook_fact")

    def test_phrase_without_a_product_endpoint_is_context_not_a_reviewer_task(self) -> None:
        compiled = compile_relationships(
            [
                {
                    "candidateId": "row:context",
                    "rpo": "BV4",
                    "description": "Custom leather includes seats, doors and console.",
                }
            ],
            self.phrases,
            target_rpos={"BV4"},
        )
        self.assertEqual(compiled["exceptions"], [])
        self.assertEqual(
            compiled["dispositions"][0]["disposition"],
            "resolved_not_a_workbook_fact",
        )

    def test_standard_no_rpo_copy_does_not_create_relationship_tasks(self) -> None:
        compiled = compile_relationships(
            [
                {
                    "candidateId": "row:standard-copy",
                    "rowKind": "standard_no_rpo",
                    "rpo": "",
                    "description": "Air filtration system includes pollen filter.",
                }
            ],
            self.phrases,
            target_rpos=set(),
        )
        self.assertEqual(compiled["exceptions"], [])
        self.assertEqual(
            compiled["dispositions"][0]["disposition"],
            "resolved_not_a_workbook_fact",
        )

    def test_comparator_only_fact_is_prefilled_exception_never_ready_row(self) -> None:
        compiled = compile_relationships(
            [{"candidateId": "row:5", "rpo": "BV4", "description": "Personalized plaque."}],
            self.phrases,
            target_rpos={"BV4", "PDB"},
            comparator_facts=[{"factType": "direct_rule", "signature": {"sourceRpo": "BV4", "ruleType": "requires", "targetRpo": "PDB"}, "evidenceId": "cmp:1", "disposition": "corroborating_context_only"}],
        )
        self.assertEqual(compiled["rows"], [])
        proposal = next(item for item in compiled["exceptions"] if item["reasonCode"] == "comparator_only_relationship_proposal")
        self.assertEqual(proposal["proposedRows"][0]["sourceRpo"], "BV4")


if __name__ == "__main__":
    unittest.main()
