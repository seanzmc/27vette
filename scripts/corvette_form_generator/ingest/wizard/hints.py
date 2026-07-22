#!/usr/bin/env python3
"""Relationship phrase-scan hints for the ingest wizard (Pass B, lane 4).

Hints are advisory only: pure functions of candidate text that surface likely
relationship candidates for the reviewer to approve, edit, or reject. Nothing
here is ever auto-applied to a decision or the workbook.
"""

from __future__ import annotations

import re
from typing import Any

from corvette_form_generator.ingest.wizard.relationship_compiler import advisory_phrase_rows, scan_text

_KIND_BY_PHRASE = {
    "not available with": "not_available_with",
    "only available with": "only_available_with",
    "requires additional equipment": "requires_additional_equipment",
    "requires": "requires",
    "included with": "included_with",
    "included in": "included_with",
    "included on": "included_with",
    "includes": "includes",
    "deletes": "deletes",
    "replaces": "replaces",
    "upgradeable to": "upgradeable_to",
}

# Compatibility adapter for the legacy copy splitter. These patterns are
# derived from the advisory vocabulary above and are not compiler authority.
PHRASE_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = tuple(
    (kind, re.compile(re.escape(phrase), re.IGNORECASE))
    for phrase, kind in _KIND_BY_PHRASE.items()
)


def scan_candidate_text(text: str) -> list[dict[str, Any]]:
    """Return ordered relationship hints found in one candidate's text."""

    return [
        {
            "kind": _KIND_BY_PHRASE[hit["phraseKey"]],
            "matchedText": hit["matchedText"],
            "snippet": hit["snippet"],
            "rpoTokens": hit["rpoTokens"],
        }
        for hit in scan_text(text or "", advisory_phrase_rows())
    ]


def scan_candidates(candidates: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    """Map candidateId -> hints. Deterministic; text in, hints out."""

    result: dict[str, list[dict[str, Any]]] = {}
    for candidate in candidates:
        text_parts = [candidate.get("description", "")]
        for coord, value in sorted((candidate.get("sourceEvidence") or {}).get("cells", {}).items()):
            if value not in text_parts:
                text_parts.append(value)
        hints = scan_candidate_text("\n".join(text_parts))
        if hints:
            result[candidate["candidateId"]] = hints
    return result
