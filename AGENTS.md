# Agent Instructions for 27vette

## Spec-first mode

For non-trivial tasks, write a spec before edits and wait for approval.

The spec must include:

- Diagnosis: root cause, exact files to inspect, risk level, and whether the task is behavior-only, styling-only, or mixed.
- Exact files to change.
- Constraints repeated back.
- Risks and non-goals.
- Validation plan.

Use concrete file, symbol, and code-path evidence. If the task is risky, split it into smaller approved steps.

## Global workflow

- Production behavior remains the oracle.
- CSV projection is shadow/experimental only unless cutover is explicitly approved.
- Do not touch production app/runtime/generator/workbook surfaces unless the task explicitly approves it.
- Do not migrate interiors unless explicitly approved.
- Minimum change that solves the task. Nothing speculative.
- Touch only what you must. Clean up only your own changes.
- Do not assume. Surface tradeoffs and confusion.
- Define success criteria and verify before handoff.

## Python commands

Use the project virtual environment for Python commands.

Do not run project scripts with bare system Python. Use `.venv/bin/python`, for example:

`.venv/bin/python scripts/stingray_csv_shadow_overlay.py`

## Dependency setup

If `.venv` does not exist, create it from the repo root:

`python3 -m venv .venv`

`source .venv/bin/activate`

`python -m pip install --upgrade pip`

`python -m pip install -r requirements.txt`

Do not commit `.venv/`.

## Handoff

Every task handoff must include:

- What changed: files and behavior impact.
- What did not change: especially preserved production, schema, workflow, or visual constraints.
- Gate results: typecheck, lint, tests, or why they were not run.
- Manual verification still pending, residual risks, or follow-up work.
