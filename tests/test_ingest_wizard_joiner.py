#!/usr/bin/env python3
"""Tests for the wizard Pass A exact 1-to-1 price joiner."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

from corvette_form_generator.ingest.wizard.joiner import join_prices  # noqa: E402


def candidate(candidate_id: str, rpo: str, row_kind: str = "orderable") -> dict:
    return {"candidateId": candidate_id, "rpo": rpo, "refOnlyRpo": "", "rowKind": row_kind}


def price_row(rpo: str, price: float, qualifier: str = "") -> dict:
    return {"rpo": rpo, "listPrice": price, "qualifier": qualifier, "description": ""}


class WizardJoinerTest(unittest.TestCase):
    def test_exact_ambiguous_none_and_unmatched(self) -> None:
        candidates = [
            candidate("a:1", "BV4"),
            candidate("a:2", "PDB"),
            candidate("a:3", "C2Z"),
            candidate("a:4", "", row_kind="ref_only"),
        ]
        prices = [
            price_row("BV4", 395.0),
            price_row("PDB", 16000.0, "ROY"),
            price_row("PDB", 17000.0, "ROZ"),
            price_row("YYY", 500.0),
        ]
        report = join_prices(candidates, prices)

        self.assertEqual(candidates[0]["priceMatch"], "exact")
        self.assertEqual(candidates[0]["listPrice"], 395.0)
        self.assertEqual(len(candidates[0]["priceRows"]), 1)

        self.assertEqual(candidates[1]["priceMatch"], "ambiguous")
        self.assertIsNone(candidates[1]["listPrice"])
        self.assertEqual(len(candidates[1]["priceRows"]), 2)

        self.assertEqual(candidates[2]["priceMatch"], "none")
        self.assertIsNone(candidates[2]["listPrice"])

        self.assertIsNone(candidates[3]["priceMatch"])

        self.assertEqual(report["exactMatches"], 1)
        self.assertEqual(report["ambiguousMatches"], 1)
        self.assertEqual(report["missingPrices"], 1)
        self.assertEqual([r["rpo"] for r in report["unmatchedPriceRows"]], ["YYY"])

    def test_same_rpo_on_two_sheets_joins_exactly_on_both(self) -> None:
        candidates = [candidate("a:1", "BV4"), candidate("b:1", "BV4")]
        report = join_prices(candidates, [price_row("BV4", 395.0)])
        self.assertEqual([c["priceMatch"] for c in candidates], ["exact", "exact"])
        self.assertEqual(report["exactMatches"], 2)
        self.assertEqual(report["unmatchedPriceRows"], [])


if __name__ == "__main__":
    unittest.main()
