# 27vette Fable 5 Outcome Rubric Template

Use this before starting any non-trivial Fable 5 run. The maker agent may not declare completion until an independent verifier can grade these criteria from artifacts and tool output.

## Task summary

- Goal:
- Changed surface: docs / tooling / workbook / generated artifacts / runtime / styling / ingest / mixed
- Source-of-truth decision:
- Protected boundaries:
- Expected files/sheets/artifacts:

## Required outcome criteria

1. **Scope is explicit.** The run names exactly what may change and what must remain untouched.
2. **Source evidence is read first.** Relevant repo files, docs, scripts, tests, workbook/sheet names, or generated contracts are inspected before edits.
3. **Independent verifier is used.** A verifier with no exposure to maker reasoning checks the final artifacts against this rubric or a task-specific derivative and writes `verifier-report.md` in the run receipt folder.
4. **Validation is real.** Relevant tests, validators, generation commands, or manual verification steps are run and their real outputs are reported.
5. **Memory compounds.** Verified facts and durable lessons are written back to `STATE.md` with timestamps and `Evidence:` references; procedural lessons are added to the skill only when generalized and verified.
6. **Safety boundaries are handled.** Any classifier block, protected 27vette boundary, missing credential, unavailable tool, or live-submission risk is escalated or explicitly marked not run.

## Stop conditions

The loop may stop only when all are true:

- The requested deliverable exists on disk or the blocker is documented with evidence.
- The independent verifier returns pass in `verifier-report.md`, or the remaining failure is explicitly accepted by a human and recorded in `run.json`.
- `STATE.md` has a last-session update.
- `run.json` records validation output, verifier result, state-update evidence, and skill-update decision.
- Relevant validation has been run.

## Independent verifier prompt skeleton

You are the verifier for a 27vette Fable 5 compounding-loop run. Do not assume the maker is correct. Inspect only the final artifacts, relevant diffs, source guidance, and validation output. Grade each criterion as pass/fail/blocked with evidence. Do not edit files. Return:

- Verdict: pass / fail / blocked
- Criteria table
- Evidence inspected
- Validation Output Inspected
- Required fixes before pass
- Durable lesson candidates, if any
- Explicit statement that the verifier did not edit files

## Max iterations

Default `max_iterations`: 3 maker/verifier cycles. After three failed cycles, stop and write the failure to `STATE.md` with reproduction details and next investigation step.
