---
name: 27vette-fable5-compounding
description: Use for non-trivial 27vette Fable 5 work that should follow the compounding loop with verifier proof, STATE updates, and run receipts.
---

# 27vette Fable 5 Compounding

This Claude Code project skill is a thin wrapper. The canonical workflow lives in `fable5loop/`.

## Instructions

1. Read `AGENTS.md`.
2. Read `fable5loop/README.md`.
3. Read `fable5loop/STATE.md`.
4. Read `fable5loop/skills/27vette-fable5-compounding.md` in full and follow it.
5. Define or select the outcome rubric from `fable5loop/outcomes/` before editing.
6. Preserve the normal 27vette source-of-truth, spec-first, workbook, generated-artifact, and dealer-submission boundaries.
7. Before closeout, create/update the run receipt, update `STATE.md`, record the skill-update decision, run the relevant gates, and run `.venv/bin/python scripts/validate_fable5_loop.py` if loop artifacts changed.

Do not copy durable procedure into this wrapper. Update the canonical `fable5loop/skills/27vette-fable5-compounding.md` only when a verified reusable lesson should change future Fable 5 runs.
