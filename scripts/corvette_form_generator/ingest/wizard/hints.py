#!/usr/bin/env python3
"""Relationship phrase-scan hints for the ingest wizard (Pass B, lane 4).

Hints are advisory only: pure functions of candidate text that surface likely
relationship candidates for the reviewer to approve, edit, or reject. Nothing
here is ever auto-applied to a decision or the workbook.
"""

from __future__ import annotations

import re
from typing import Any

from corvette_form_generator.ingest.source_profiler import RPO_RE

# Ordered so more specific phrases win the `kind` label when several overlap.
PHRASE_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("not_available_with", re.compile(r"not\s+available\s+with", re.IGNORECASE)),
    ("only_available_with", re.compile(r"only\s+available\s+(?:with|on)", re.IGNORECASE)),
    ("requires_additional_equipment", re.compile(r"requires\s+additional\s+equipment", re.IGNORECASE)),
    ("requires", re.compile(r"\brequires?\b", re.IGNORECASE)),
    ("included_with", re.compile(r"included\s+(?:with|in|on)", re.IGNORECASE)),
    ("includes", re.compile(r"\bincludes?\b", re.IGNORECASE)),
    ("deletes", re.compile(r"\bdeletes?\b", re.IGNORECASE)),
    ("replaces", re.compile(r"\breplaces?\b", re.IGNORECASE)),
    ("upgradeable_to", re.compile(r"upgradeable\s+to", re.IGNORECASE)),
)

# Parenthesized tokens are trusted at RPO length; bare tokens must mix
# letters and digits (Z51, E60, BV4 …) — all-alpha flags ordinary uppercase
# words, all-digit flags prices/quantities.
RPO_TOKEN_RE = re.compile(r"\(([A-Z0-9]{2,4})\)|\b([A-Z0-9]{3,4})\b")
SNIPPET_CHARS = 90


def scan_candidate_text(text: str) -> list[dict[str, Any]]:
    """Return ordered relationship hints found in one candidate's text."""

    hints: list[dict[str, Any]] = []
    for kind, pattern in PHRASE_PATTERNS:
        for match in pattern.finditer(text or ""):
            start = max(0, match.start() - SNIPPET_CHARS // 3)
            end = min(len(text), match.end() + SNIPPET_CHARS)
            snippet = text[start:end].strip()
            hints.append(
                {
                    "kind": kind,
                    "matchedText": match.group(0),
                    "snippet": snippet,
                    "rpoTokens": _rpo_tokens(text[match.end():end]),
                }
            )
    return hints


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


def _rpo_tokens(text: str) -> list[str]:
    tokens: list[str] = []
    for match in RPO_TOKEN_RE.finditer(text or ""):
        parenthesized = match.group(1)
        token = (parenthesized or match.group(2) or "").upper()
        if not token or not RPO_RE.fullmatch(token) or token in tokens:
            continue
        if not parenthesized and (token.isdigit() or token.isalpha()):
            continue
        tokens.append(token)
    return tokens
