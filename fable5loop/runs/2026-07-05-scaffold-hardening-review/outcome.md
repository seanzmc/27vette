# Outcome Rubric: Scaffold Hardening Review

## Task summary

- Goal: Polish the existing fable5loop scaffold so Fable 5 can be expected to run a compounding loop, use a verifier, update memory with evidence and timestamps, and improve skills across runs.
- Changed surface: docs/tooling.
- Source-of-truth decision: `fable5loop/fable5-loop-contract.json` owns structural contract; `fable5loop/runs/` owns per-run proof; `fable5loop/STATE.md` owns timestamped memory; `fable5loop/skills/27vette-fable5-compounding.md` owns procedural lessons.
- Protected boundaries: workbook, generated artifacts, runtime app, styling, pricing/rules, model promotion, and dealer submission remain untouched.
- Expected files/artifacts: README pointer, fable5loop docs, run receipt files, contract/rubric updates, validator updates, and validator pytest coverage.

## Required outcome criteria

1. The repo has a canonical validator command discoverable from `README.md`.
2. Every non-trivial Fable 5 run must leave a receipt with `outcome.md`, `verifier-report.md`, `validation-output.txt`, and `run.json`.
3. The validator rejects missing verifier proof, missing run receipt artifacts, missing skill-update evidence, state entries without timestamp/evidence, and stale last-session pointers.
4. `STATE.md` requires timestamped `Evidence:` references for durable memory entries.
5. The skill requires a receipt-backed skill-update decision for every closeout.
6. Tests cover positive and negative cases for the hardened contract.

## Stop conditions

- `.venv/bin/python scripts/validate_fable5_loop.py` passes.
- `.venv/bin/python -m pytest tests/test_fable5_loop_contract.py -q` passes.
- `git diff --check -- README.md docs/fable5-compounding-loop-hardening-spec.md fable5loop scripts/validate_fable5_loop.py tests/test_fable5_loop_contract.py` passes.
- `run.json` points to this outcome, verifier report, and validation output.
