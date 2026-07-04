#!/usr/bin/env python3
"""Exact 1-to-1 RPO price joins for the ingest wizard (Pass A, step 5).

Join keys are exact normalized RPO strings only. Ambiguous, missing, and
unmatched prices are reported for user review — never guessed (core
principle: ambiguous prices are a user decision).
"""

from __future__ import annotations

from typing import Any

from corvette_form_generator.ingest.wizard.profiler import SCHEMA_VERSION


def join_prices(candidates: list[dict[str, Any]], price_rows: list[dict[str, Any]]) -> dict[str, Any]:
    by_rpo: dict[str, list[dict[str, Any]]] = {}
    for row in price_rows:
        by_rpo.setdefault(row["rpo"], []).append(row)
    orderable_rpos: set[str] = set()
    exact = ambiguous = missing = 0
    for candidate in candidates:
        if candidate["rowKind"] != "orderable" or not candidate["rpo"]:
            candidate["priceMatch"] = None
            candidate["listPrice"] = None
            candidate["priceRows"] = []
            continue
        orderable_rpos.add(candidate["rpo"])
        matches = by_rpo.get(candidate["rpo"], [])
        candidate["priceRows"] = matches
        if len(matches) == 1:
            candidate["priceMatch"] = "exact"
            candidate["listPrice"] = matches[0]["listPrice"]
            exact += 1
        elif matches:
            candidate["priceMatch"] = "ambiguous"
            candidate["listPrice"] = None
            ambiguous += 1
        else:
            candidate["priceMatch"] = "none"
            candidate["listPrice"] = None
            missing += 1
    return {
        "schemaVersion": SCHEMA_VERSION,
        "exactMatches": exact,
        "ambiguousMatches": ambiguous,
        "missingPrices": missing,
        "unmatchedPriceRows": [row for row in price_rows if row["rpo"] not in orderable_rpos],
    }
