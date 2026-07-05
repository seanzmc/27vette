---
name: 27vette-fable5-compounding
description: Run 27vette work as a compounding Fable 5 loop with independent verification, state updates, and skill distillation.
---

# 27vette Fable 5 Compounding Skill

Use this skill when Fable 5 is orchestrating a non-trivial 27vette task. The goal is not one successful run; the goal is a system where each verified run improves future runs.

## Start-of-run checklist

1. Read `AGENTS.md` and task-relevant 27vette docs.
2. Read `fable5loop/README.md`.
3. Read `fable5loop/STATE.md`.
4. Read this skill.
5. Define or select an outcome rubric from `fable5loop/outcomes/`.
6. Run `.venv/bin/python scripts/validate_fable5_loop.py` from the repo root if the loop artifacts may be touched.
7. Classify changed surface and approval requirements before edits.

## Model and agent routing

- Fable 5: orchestrator, planner, synthesizer, verifier coordinator, and final rule distiller.
- Worker agents: bounded file edits, fixture/test additions, doc updates, deterministic script runs, focused inspections.
- Independent verifier: separate context; sees rubric, final artifacts, diffs, and validation output; does not see maker reasoning.
- Human escalation: workbook writes, live dealer submission changes, ambiguous product/business decisions, safety-boundary blocks, missing credentials, or unresolvable verifier failures.

## Dynamic workflow patterns

Use one of these patterns explicitly:

- Fan-out-and-synthesize: split independent inspections or candidate fixes into clean contexts, then synthesize.
- Adversarial verification: maker writes, verifier grades, maker fixes only the verifier's evidence-backed failures.
- Loop-until-done: iterate against a clear stop condition and `max_iterations`; stop and record failure rather than looping forever.

## State update contract

Update `fable5loop/STATE.md` before ending a run:

- Verified facts: only facts backed by tool output, source files, workbook evidence, or verifier results.
- General rules: reusable rules that will help future runs.
- Open failures: failed criteria, reproduction steps, logs, hypotheses clearly marked as hypotheses.
- Lessons learned: durable insights that have been verified.
- Last session: one concise resume pointer with next action.
- Each new memory bullet: ISO date or timestamp plus `Evidence:` reference.
- Each non-trivial run: receipt folder under `fable5loop/runs/YYYY-MM-DD-slug/`.

## Skill improvement contract

Update this skill only when the run produces a durable procedural lesson. Good updates include:

- new known failure modes,
- revised routing rules,
- validated anti-patterns,
- changed validation requirements,
- better verifier criteria.

Do not add one-off task progress, PR IDs, commit hashes, stale line numbers, or unverified guesses.

Every closeout must record a skill-update decision in the run receipt `run.json`:

- `updated`: a durable procedural lesson was added to this skill.
- `not_applicable`: the run produced no durable procedural lesson; evidence explains why.
- `deferred`: the lesson candidate needs more verification before changing this skill.

## Known failure modes

- **Prompt-only loop:** Fable 5 completes a task in chat but writes no state or skill updates. Fix: require closeout checklist before done.
- **Maker self-grades:** The same context that made the change declares success. Fix: use an independent verifier with only artifacts/rubric/diffs.
- **Ungradable goal:** The outcome is subjective or vague. Fix: write measurable criteria before edits.
- **Generated artifact as source:** Agent patches `form-output/` or `form-app/data.js` directly. Fix: return to workbook/generator source-of-truth boundary.
- **Silent protected-boundary failure:** Dealer submission, workbook write, or safety-boundary issue is treated like a normal error. Fix: escalate and record as boundary/fallback.
- **Gate-induced artifact churn:** Some validation gates regenerate tracked generated artifacts (e.g. `node --test tests/z06-form-data-draft.test.mjs` rewrites the `generated_at` timestamp in `form-output/runtime/z06-runtime-contract.json`), so running gates dirties `form-output/` and reads as a boundary violation. Fix: after any gate run in a pass that must not change generated artifacts, check `git status -- form-output form-app` and `git restore` timestamp-only churn before verification; verifiers must inspect read-only instead of re-running those gates, or they re-introduce the churn they then flag.
- **Completion-record staging drift:** "Staged, not committed" is a checkable claim that silently goes false because `git rm`/`git mv` auto-stage while plain file edits and new files do not — the index then lags the worktree and committing it would produce a broken/incomplete commit (e.g. a test reading a file the same index deletes). Fix: before writing any completion record or handing to a verifier, run `git status --porcelain` and confirm no pass-attributable ` M`/`??` lines remain; verify index self-consistency with `git show :<path>`, not just worktree correctness.

## Anti-patterns

- Do not start editing before reading `STATE.md` and the task-relevant source files.
- Do not use Fable 5 for trivial high-volume worker tasks by default.
- Do not keep failed experiments only in chat.
- Do not add speculative rules to memory.
- Do not bypass `AGENTS.md` approval requirements because the loop is autonomous.

## Eval suite

Run `.venv/bin/python scripts/validate_fable5_loop.py` after any change to this directory. The eval rubric lives at `fable5loop/evals/loop-contract-rubric.json` and checks the minimum structure for the three-tier / four-layer system plus run receipt proof.

## Closeout response requirements

Every Fable 5 handoff should include:

- What changed.
- What did not change and protected boundaries preserved.
- Companion-file impact.
- Validation run and real results.
- Gates not run and why.
- STATE/skill updates made.
- Run receipt path and verifier verdict.
- Residual risks or `none implied`.
