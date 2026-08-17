"""Make `scripts/` importable for every test in this directory.

Checkpoint 1 of the fast layered validation suite
(`docs/superpowers/specs/2026-08-17-fast-layered-validation-suite.md` §9) added
this. The generator lives under `scripts/`, which is not an installed package,
so a test module that imports `corvette_form_generator` needs that directory on
`sys.path`. Several files did it themselves and several did not — the ones that
did not passed anyway, because pytest imported a sibling that inserted the path
first. The Checkpoint 0 baseline measured the consequence: run alone without
`PYTHONPATH=scripts`, `test_rule_derivation.py` and
`test_source_assembly_characterization.py` error at collection and
`test_options_sheet_quality.py` reports 17 failed / 1 passed, while all three
pass beside their siblings.

Layer 0 of the same specification selects gates by changed surface, one file at
a time, so a file that only passes next to its siblings is not selectable. This
conftest is the single owner of that path insertion; pytest loads it before any
test module in this directory. The per-file insertions that already exist stay
harmless — each is guarded against duplicating the entry.
"""

from __future__ import annotations

import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"

if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))
