#!/usr/bin/env python3
"""Script-owned copy splitting for the ingest wizard (Pass B.2).

The script proposes the customer-facing name / description / disclosure split
for every candidate; the reviewer only touches flagged exceptions. Pure
functions of candidate text — deterministic, no I/O. Full raw text is always
preserved in `detailRaw`; nothing here destroys source detail.
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

SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")
TRAILING_MARKER_RE = re.compile(r"\s*\(?\d{1,2}\)?\s*$")
FOOTNOTE_MARKER_RE = re.compile(r"\(\d{1,2}\)|(?<=[a-z])\d{1,2}\b")


def _is_disclosure_sentence(sentence: str) -> bool:
    for _, pattern in PHRASE_PATTERNS:
        if pattern.search(sentence):
            return True
    return any(pattern.search(sentence) for pattern in BOILERPLATE_PATTERNS)


def propose_copy_split(candidate: dict[str, Any]) -> dict[str, Any]:
    """Deterministic name/description/disclosure proposal for one candidate."""

    raw = str(candidate.get("description") or "").strip()
    flags: list[str] = []

    first_line = raw.split("\n", 1)[0].split(" / ", 1)[0].strip()
    sentences = [s.strip() for s in SENTENCE_SPLIT_RE.split(raw.replace("\n", " ")) if s.strip()]
    if len(sentences) <= 1 and len(raw) > 60:
        flags.append(FLAG_NO_SENTENCE_BREAK)

    name = sentences[0] if sentences else first_line
    if "\n" in raw or " / " in raw:
        name = first_line
    name = TRAILING_MARKER_RE.sub("", name.rstrip(".")).strip()
    if len(name) > 60:
        flags.append(FLAG_NAME_OVER_60)

    rest = sentences[1:] if sentences and name.startswith(sentences[0].rstrip(".")[:20]) else sentences
    description_parts: list[str] = []
    disclosure_parts: list[str] = []
    for sentence in rest:
        (disclosure_parts if _is_disclosure_sentence(sentence) else description_parts).append(sentence)

    # If even the proposed name reads as disclosure text and nothing is left
    # for the description, the whole row is boilerplate — human eyes needed.
    if raw and not description_parts and disclosure_parts and _is_disclosure_sentence(name):
        flags.append(FLAG_ALL_DISCLOSURE)

    # Footnote markers in the raw text should be reconciled to disclosures;
    # markers with no disclosure sentence are a review flag, never dropped.
    if FOOTNOTE_MARKER_RE.search(raw) and not disclosure_parts:
        flags.append(FLAG_UNMATCHED_FOOTNOTE)

    return {
        "name": name,
        "description": " ".join(description_parts),
        "disclosure": " ".join(disclosure_parts),
        "detailRaw": raw,
        "flags": flags,
    }
