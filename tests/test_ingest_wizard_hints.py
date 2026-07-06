#!/usr/bin/env python3
"""Phrase-scan hint tests (Pass B): deterministic, advisory-only."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

from corvette_form_generator.ingest.wizard.hints import (  # noqa: E402
    scan_candidate_text,
    scan_candidates,
)


class HintScanTest(unittest.TestCase):
    def test_phrase_kinds_detected(self) -> None:
        cases = {
            "Not available with (PDB).": "not_available_with",
            "Only available with Z51 performance package": "only_available_with",
            "Requires additional equipment": "requires_additional_equipment",
            "Requires (E60) front lift": "requires",
            "Included with 2LZ trim": "included_with",
            "Deletes rear spoiler": "deletes",
            "Replaces standard exhaust": "replaces",
        }
        for text, expected_kind in cases.items():
            kinds = [hint["kind"] for hint in scan_candidate_text(text)]
            self.assertIn(expected_kind, kinds, text)

    def test_rpo_tokens_parenthesized_and_digit_rule(self) -> None:
        hints = scan_candidate_text("Not available with (PDB) or Z51. Requires MAG ride.")
        not_available = next(h for h in hints if h["kind"] == "not_available_with")
        self.assertIn("PDB", not_available["rpoTokens"])
        self.assertIn("Z51", not_available["rpoTokens"])
        requires = next(h for h in hints if h["kind"] == "requires")
        # Bare all-alpha token (MAG) must not be flagged: mixed-char rule.
        self.assertNotIn("MAG", requires["rpoTokens"])

    def test_bare_numeric_tokens_not_flagged(self) -> None:
        hints = scan_candidate_text("Requires 866 credit or Z51 package (1500 max)")
        requires = next(h for h in hints if h["kind"] == "requires")
        self.assertNotIn("866", requires["rpoTokens"])
        self.assertNotIn("1500", requires["rpoTokens"])
        self.assertIn("Z51", requires["rpoTokens"])

    def test_deterministic_and_pure(self) -> None:
        text = "Requires (E60). Not available with (PDB)."
        self.assertEqual(scan_candidate_text(text), scan_candidate_text(text))
        self.assertEqual(scan_candidate_text(""), [])

    def test_scan_candidates_maps_by_id_and_reads_evidence(self) -> None:
        candidates = [
            {
                "candidateId": "s:2",
                "description": "Plain option",
                "sourceEvidence": {"cells": {"C2": "Plain option"}},
            },
            {
                "candidateId": "s:3",
                "description": "Front lift",
                "sourceEvidence": {"cells": {"C3": "Front lift. Not available with (PDB)."}},
            },
        ]
        hints = scan_candidates(candidates)
        self.assertNotIn("s:2", hints)
        self.assertEqual(hints["s:3"][0]["kind"], "not_available_with")
        self.assertEqual(hints["s:3"][0]["rpoTokens"], ["PDB"])


if __name__ == "__main__":
    unittest.main()
