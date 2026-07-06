#!/usr/bin/env python3
"""Script-owned copy splitting for the ingest wizard (Pass B.2, comma rule B.4).

The script proposes the customer-facing name / description / disclosure split
for every candidate; the reviewer only touches flagged exceptions. Pure
functions of candidate text — deterministic, no I/O. Full raw text is always
preserved in `detailRaw`; nothing here destroys source detail.

Naming rule (Sean, 2026-07-06 field notes): the name is the text up to the
first comma of the first line — unless the line starts with "LPO", then it is
the segment between the first and second comma. Sentence breaks and " / "
separators also end the name when they come before any comma. Everything
after the name is description, except disclosure text (numbered in-cell lines
keyed by status footnote digits, plus known disclosure/boilerplate phrases).
"""

from __future__ import annotations

import re
from typing import Any

from corvette_form_generator.ingest.wizard.hints import PHRASE_PATTERNS

# Relationship phrases (hints.py) extended with subscription/legal boilerplate
# owned by the splitter. A sentence matching any of these is proposed as
# disclosure text rather than customer-facing description.
BOILERPLATE_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"subscription", re.IGNORECASE),
    re.compile(r"trial\s+period", re.IGNORECASE),
    re.compile(r"see\s+(?:your\s+)?dealer", re.IGNORECASE),
    re.compile(r"functionality\s+var(?:y|ies)", re.IGNORECASE),
    re.compile(r"data\s+plan", re.IGNORECASE),
    re.compile(r"terms\s+(?:and|&)\s+conditions", re.IGNORECASE),
    re.compile(r"visit\s+\S+\.(?:com|net|org)", re.IGNORECASE),
    re.compile(r"available\s+at\s+time\s+of\s+order", re.IGNORECASE),
    re.compile(r"late\s+availability", re.IGNORECASE),
    re.compile(r"order\s+type", re.IGNORECASE),
)

FLAG_NO_SENTENCE_BREAK = "no_sentence_break"
FLAG_NAME_OVER_60 = "name_over_60_chars"
FLAG_UNMATCHED_FOOTNOTE = "unmatched_footnote_marker"
FLAG_ALL_DISCLOSURE = "all_text_matched_disclosure"
# One-word names ("Trim", "Seats", "Plaque") are GM's inverted noun-first
# style — a human needs to rebuild them (FA5-class exception).
FLAG_ONE_WORD_NAME = "one_word_name"
# Added at queue level (session.py), not here: the same proposed name on more
# than one candidate in the lane scope.
FLAG_DUPLICATE_NAME = "duplicate_proposed_name"

SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")
TRAILING_MARKER_RE = re.compile(r"\s*\(?\d{1,2}\)?\s*$")
# In-cell disclosure definition line: "1. Requires …" / "2) Not available …".
DISCLOSURE_LINE_RE = re.compile(r"^\s*(\d{1,2})[.):-]\s+(\S.*)$")
# Name ends at the first comma, " / " separator, or sentence break.
NAME_BOUNDARY_RE = re.compile(r",|\s+/\s+|(?<=[.!?])\s")
# "!+" is load-bearing: "NEW!" is a literal export marker; a plain word "New"
# starting a real name must never be stripped.
NEW_MARKER_RE = re.compile(r"^\s*NEW!+\s*", re.IGNORECASE)
LPO_PREFIX_RE = re.compile(r"^\s*LPO\s*,\s*", re.IGNORECASE)


def _is_disclosure_sentence(sentence: str) -> bool:
    for _, pattern in PHRASE_PATTERNS:
        if pattern.search(sentence):
            return True
    return any(pattern.search(sentence) for pattern in BOILERPLATE_PATTERNS)


def candidate_disclosure_markers(candidate: dict[str, Any]) -> set[str]:
    markers: set[str] = set()
    for status in candidate.get("statuses", []):
        marker = str(status.get("disclosureMarker") or "").strip()
        if marker.isdigit():
            markers.add(marker)
    return markers


def propose_copy_split(candidate: dict[str, Any]) -> dict[str, Any]:
    """Deterministic name/description/disclosure proposal for one candidate.

    GM exports embed disclosure text as numbered lines inside the description
    cell ("1. Requires …"), keyed by the digits fused onto status cells
    (A1/S2). Those lines split deterministically; phrase patterns cover
    unnumbered disclosure sentences. Names follow the comma rule (docstring
    above); rows the rule can't name confidently are flagged, never guessed
    silently.
    """

    raw = str(candidate.get("description") or "").strip()
    flags: list[str] = []
    markers = candidate_disclosure_markers(candidate)

    # Peel numbered in-cell disclosure lines out first.
    body_lines: list[str] = []
    numbered: dict[str, str] = {}
    for line in raw.split("\n"):
        match = DISCLOSURE_LINE_RE.match(line)
        if match:
            numbered[match.group(1)] = match.group(2).strip()
        elif line.strip():
            body_lines.append(line.strip())
    disclosure_parts: list[str] = [numbered[n] for n in sorted(numbered, key=int)]
    matched_markers = markers & set(numbered)

    first_line = NEW_MARKER_RE.sub("", body_lines[0] if body_lines else "")
    if LPO_PREFIX_RE.match(first_line):
        first_line = LPO_PREFIX_RE.sub("", first_line)
    boundary = NAME_BOUNDARY_RE.search(first_line)
    if boundary:
        name = first_line[: boundary.start()]
        remainder_first = first_line[boundary.end() :].strip()
    else:
        name = first_line
        remainder_first = ""
        if len(first_line) > 60:
            flags.append(FLAG_NO_SENTENCE_BREAK)
    name = TRAILING_MARKER_RE.sub("", name.rstrip(".")).strip()
    if len(name) > 60:
        flags.append(FLAG_NAME_OVER_60)

    remainder = " ".join(part for part in [remainder_first, *body_lines[1:]] if part)
    if name and len(name.split()) == 1 and remainder:
        flags.append(FLAG_ONE_WORD_NAME)

    description_parts: list[str] = []
    for sentence in (s.strip() for s in SENTENCE_SPLIT_RE.split(remainder) if s.strip()):
        (disclosure_parts if _is_disclosure_sentence(sentence) else description_parts).append(sentence)

    # If even the proposed name reads as disclosure text and nothing is left
    # for the description, the whole row is boilerplate — human eyes needed.
    if raw and not description_parts and disclosure_parts and _is_disclosure_sentence(name):
        flags.append(FLAG_ALL_DISCLOSURE)

    # Status markers must reconcile to a numbered disclosure line (or at least
    # phrase-matched disclosure text); unreconciled markers are a review flag.
    if markers and not matched_markers and not disclosure_parts:
        flags.append(FLAG_UNMATCHED_FOOTNOTE)

    return {
        "name": name,
        "description": " ".join(description_parts),
        "disclosure": " ".join(disclosure_parts),
        "detailRaw": raw,
        "markers": sorted(markers),
        "matchedMarkers": sorted(matched_markers),
        "flags": flags,
    }
