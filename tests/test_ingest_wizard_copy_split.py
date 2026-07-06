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
    FLAG_UNMATCHED_FOOTNOTE,
    propose_copy_split,
)


def split(text: str, markers: list[str] | None = None) -> dict:
    statuses = [{"disclosureMarker": marker} for marker in markers or []]
    return propose_copy_split({"description": text, "statuses": statuses})


class CopySplitTest(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
