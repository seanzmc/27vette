"""Display-only naming normalization.

Canonical identifiers are never altered; every function here derives a
display value from a canonical one. Prefix stripping is deterministic and
reversible: a prefix is removed only when it is explicitly declared for the
table in canonical catalog metadata; nothing is stripped merely because it
looks repetitive, so ``canonical == confirmed_prefix + stripped_remainder``
always holds.
"""

from __future__ import annotations

import re

# Terminology preserved verbatim (case-corrected) in Title Case output.
ACRONYMS = {
    "lpo": "LPO", "ovs": "OVS", "lz": "LZ", "lt": "LT", "zr1": "ZR1",
    "zr1x": "ZR1X", "z06": "Z06", "z51": "Z51", "z52": "Z52", "z07": "Z07",
    "rpo": "RPO", "id": "ID", "gs": "GS", "cf": "CF", "api": "API",
    "url": "URL", "db": "DB",
}

_CAMEL_RE = re.compile(r"([a-z0-9])([A-Z])")


def humanize(raw: str) -> str:
    """snake_case / camelCase -> Title Case with Corvette terms preserved."""
    if not raw:
        return ""
    txt = _CAMEL_RE.sub(r"\1 \2", str(raw))
    words = re.split(r"[_\s]+", txt.strip())
    out = []
    for w in words:
        lw = w.lower()
        out.append(ACRONYMS.get(lw, w[:1].upper() + w[1:] if w else w))
    return " ".join(w for w in out if w)


def strip_prefix(canonical_id: str, prefixes: tuple[str, ...]) -> tuple[str, str]:
    """Return (confirmed_prefix, remainder). Empty prefix => nothing stripped."""
    cid = str(canonical_id or "")
    for p in prefixes:
        if p and cid.startswith(p) and len(cid) > len(p):
            return p, cid[len(p):]
    return "", cid


def display_id(canonical_id: str, prefixes: tuple[str, ...]) -> str:
    _, remainder = strip_prefix(canonical_id, prefixes)
    return humanize(remainder)


def sheet_display_name(sheet: str) -> str:
    # grandSport_options -> Grand Sport Options, LZ_Interiors -> LZ Interiors
    return humanize(sheet)
