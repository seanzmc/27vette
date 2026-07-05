# Routine Template: nightly-eval-compounding

This is a template for a future hosted Routine or scheduled agent run. It is not currently scheduled by this repo.

## Trigger

- Suggested schedule: daily at 07:00 local, only after a human approves hosted execution and delivery target.
- Suggested event trigger: CI failure, PR open, or explicit API trigger for a named 27vette task.

## Model roles

- Orchestrator: Fable 5 for long-horizon planning, synthesis, verifier coordination, and rule distillation.
- Worker: lower-cost bounded worker for mechanical edits, test scaffolding, or focused inspections.
- Verifier: independent grader for outcome criteria; use a clean context and no maker reasoning.
- Fallback/escalation: protected safety-boundary domains and dealer/workbook live-risk decisions go to human review or approved fallback.

## Run protocol

1. Read `fable5loop/README.md`.
2. Read `fable5loop/STATE.md`.
3. Read `fable5loop/skills/27vette-fable5-compounding.md`.
4. Read the task-specific outcome rubric from `fable5loop/outcomes/` or create one before editing.
5. Run `.venv/bin/python scripts/validate_fable5_loop.py` as a preflight from the repo root.
6. Execute the task using the smallest safe changed surface.
7. Use an independent verifier to grade the output.
8. Iterate until the verifier passes or `max_iterations` is reached.
9. Run relevant 27vette validation gates.
10. Write before walking away: create the run receipt, update `STATE.md`, and record the skill-update decision.
11. Run `.venv/bin/python scripts/validate_fable5_loop.py` again if loop artifacts changed.
12. Deliver a digest with changes, validation, gates not run, residual risks, and next step.

## Digest format

- Task:
- Verdict:
- Files changed:
- Validation run:
- Verifier result:
- STATE updates:
- Skill updates:
- Boundaries preserved:
- Blockers/escalations:

## Guardrails

- Do not schedule this routine from the Hermes TUI expecting live delivery; local cron output is not delivered back into the TUI.
- Do not run live dealer submissions.
- Do not write `stingray_master.xlsx` unless the task has explicit workbook approval and Excel lock checks pass.
- Do not mutate generated artifacts as source fixes.
