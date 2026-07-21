#!/usr/bin/env python3
"""Script-owned copy-split tests (Pass B.2): deterministic, flag-driven."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

from corvette_form_generator.ingest.wizard.copy_split import (  # noqa: E402
    FLAG_ALL_DISCLOSURE,
    FLAG_NAME_OVER_60,
    FLAG_NO_SENTENCE_BREAK,
    FLAG_ONE_WORD_NAME,
    FLAG_UNMATCHED_FOOTNOTE,
    comparator_copy_comparison,
    is_blocking_copy_proposal,
    propose_copy_split,
)


def split(text: str, markers: list[str] | None = None) -> dict:
    statuses = [{"disclosureMarker": marker} for marker in markers or []]
    return propose_copy_split({"description": text, "statuses": statuses})


class CopySplitTest(unittest.TestCase):
    def test_comparator_material_coverage_boundary_is_inclusive(self) -> None:
        comparator = {"option_name": "Visible Carbon Fiber Wheel Package"}
        at_boundary = comparator_copy_comparison(
            {"detail_raw": "Visible carbon wheel"}, comparator
        )
        below_boundary = comparator_copy_comparison(
            {"detail_raw": "Visible carbon"}, comparator
        )

        self.assertEqual(at_boundary["comparatorNameTokenCoverage"], 0.6)
        self.assertFalse(at_boundary["materialDisagreement"])
        self.assertLess(below_boundary["comparatorNameTokenCoverage"], 0.6)
        self.assertTrue(below_boundary["materialDisagreement"])

    def test_generic_one_word_proposal_blocks_even_without_helper_flag(self) -> None:
        self.assertTrue(is_blocking_copy_proposal({"name": "Wheels", "flags": []}))

    def test_every_current_and_unknown_split_flag_blocks_individually(self) -> None:
        for flag in (
            FLAG_ONE_WORD_NAME,
            FLAG_NO_SENTENCE_BREAK,
            FLAG_NAME_OVER_60,
            FLAG_UNMATCHED_FOOTNOTE,
            FLAG_ALL_DISCLOSURE,
            "future_unknown_split_flag",
        ):
            with self.subTest(flag=flag):
                self.assertTrue(
                    is_blocking_copy_proposal({"name": "Valid package name", "flags": [flag]})
                )

    def test_detail_raw_preserves_exact_source_whitespace(self) -> None:
        raw = "  Ground effects, extended splitter\n"
        result = propose_copy_split({"description": "cleaned", "detailRaw": raw, "statuses": []})
        self.assertEqual(result["detailRaw"], raw)
    def test_clean_split_name_description_disclosure(self) -> None:
        result = split(
            "Front Lift Adjustable Height with Memory. Scans and remembers locations. "
            "Not available with (PDB). Requires subscription after trial period."
        )
        self.assertEqual(result["name"], "Front Lift Adjustable Height with Memory")
        self.assertEqual(result["description"], "Scans and remembers locations.")
        self.assertIn("Not available with (PDB).", result["disclosure"])
        self.assertIn("subscription", result["disclosure"])
        self.assertEqual(result["flags"], [])
        # Raw text always preserved verbatim.
        self.assertTrue(result["detailRaw"].startswith("Front Lift"))

    def test_short_name_only_row_is_clean(self) -> None:
        result = split("Battery protection package")
        self.assertEqual(result["name"], "Battery protection package")
        self.assertEqual(result["description"], "")
        self.assertEqual(result["flags"], [])

    def test_multiline_and_slash_take_first_segment(self) -> None:
        result = split("Carbon Flash Badges / painted exterior\nextra detail line")
        self.assertEqual(result["name"], "Carbon Flash Badges")

    def test_long_unbroken_text_flags(self) -> None:
        text = "word " * 30  # >60 chars, no sentence break
        result = split(text.strip())
        self.assertIn(FLAG_NO_SENTENCE_BREAK, result["flags"])
        self.assertIn(FLAG_NAME_OVER_60, result["flags"])

    def test_numbered_disclosure_lines_match_status_markers(self) -> None:
        result = split(
            "3 Years SiriusXM\n1. Requires SiriusXM. Not available with a FGO order type.",
            markers=["1"],
        )
        self.assertEqual(result["name"], "3 Years SiriusXM")
        self.assertIn("Requires SiriusXM", result["disclosure"])
        self.assertEqual(result["matchedMarkers"], ["1"])
        self.assertEqual(result["flags"], [])

    def test_status_marker_without_disclosure_text_flags(self) -> None:
        result = split("Engine appearance package. Adds painted covers.", markers=["3"])
        self.assertIn(FLAG_UNMATCHED_FOOTNOTE, result["flags"])

    def test_numbered_line_without_marker_still_goes_to_disclosure(self) -> None:
        result = split("Roof panel\n2. Late availability.")
        self.assertIn("Late availability.", result["disclosure"])
        self.assertEqual(result["name"], "Roof panel")

    def test_boilerplate_goes_to_disclosure(self) -> None:
        result = split("OnStar services. Requires paid plan, terms and conditions apply. See dealer for details.")
        self.assertIn("terms and conditions", result["disclosure"].lower())
        self.assertIn("see dealer", result["disclosure"].lower())

    def test_all_disclosure_row_flags(self) -> None:
        result = split("Requires additional equipment. Not available with (PDB). See dealer for details.")
        self.assertIn(FLAG_ALL_DISCLOSURE, result["flags"])

    def test_deterministic(self) -> None:
        text = "Front Lift. Not available with (PDB)."
        self.assertEqual(split(text), split(text))

    # -------------------------------------------- b.4: comma naming rule
    def test_name_is_text_before_first_comma(self) -> None:
        result = split("Seats, GT2 bucket")
        self.assertEqual(result["name"], "Seats")
        self.assertEqual(result["description"], "GT2 bucket")
        # One-word names are GM's inverted style — flagged for a human rebuild.
        self.assertIn(FLAG_ONE_WORD_NAME, result["flags"])

    def test_multiword_comma_name_is_clean(self) -> None:
        result = split("Stealth Interior Trim Package, dark finish aluminum trim")
        self.assertEqual(result["name"], "Stealth Interior Trim Package")
        self.assertEqual(result["description"], "dark finish aluminum trim")
        self.assertEqual(result["flags"], [])

    def test_lpo_name_between_first_and_second_comma(self) -> None:
        result = split("LPO, Cargo net set, Genuine Corvette Accessory")
        self.assertEqual(result["name"], "Cargo net set")
        self.assertEqual(result["description"], "Genuine Corvette Accessory")
        self.assertEqual(result["flags"], [])

    def test_lpo_without_second_comma_takes_rest(self) -> None:
        result = split("LPO, Visible Carbon Fiber sill plates")
        self.assertEqual(result["name"], "Visible Carbon Fiber sill plates")
        self.assertEqual(result["description"], "")

    def test_fa5_style_one_word_name_flags(self) -> None:
        result = split("Trim, interior, carbon fiber cluster-surround and console/door switch plates")
        self.assertEqual(result["name"], "Trim")
        self.assertIn(FLAG_ONE_WORD_NAME, result["flags"])
        self.assertIn("interior", result["description"])

    def test_new_marker_stripped_from_name(self) -> None:
        result = split("NEW!  Ground effects, extended front splitter")
        self.assertEqual(result["name"], "Ground effects")
        self.assertEqual(result["description"], "extended front splitter")

    def test_plain_word_new_is_not_a_marker(self) -> None:
        result = split("New Vehicle Prep Package, dealer installed")
        self.assertEqual(result["name"], "New Vehicle Prep Package")

    def test_comma_rule_keeps_marker_disclosures(self) -> None:
        result = split(
            "Front lift adjustable height with memory, includes (TR7) automatic headlamp leveling\n"
            "1. Not available with (PDB).",
            markers=["1"],
        )
        self.assertEqual(result["name"], "Front lift adjustable height with memory")
        self.assertIn("includes (TR7)", result["disclosure"] + result["description"])
        self.assertEqual(result["matchedMarkers"], ["1"])


if __name__ == "__main__":
    unittest.main()
