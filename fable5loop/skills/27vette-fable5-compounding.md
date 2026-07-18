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
- **Gate-induced artifact churn:** Some validation gates regenerate tracked generated artifacts — the Grand Sport and Z06 draft/preview gates rewrite `generated_at` in `form-output/runtime/*-runtime-contract.json`, and the promotion gate (`z06-runtime-promotion`, which runs `scripts/generate_registry.py`) rewrites `form-app/data.js` — so running gates dirties generated surfaces and reads as a boundary violation. Fix: after any gate run in a pass that must not change generated artifacts, check `git status -- form-output form-app` and `git restore` timestamp-only churn before verification; verifiers must inspect read-only instead of re-running those gates, or they re-introduce the churn they then flag.
- **Order-dependent CSS-regex test helpers:** Node gates that extract CSS blocks with a first-match regex (e.g. `cssBlock('.choice-card')`) silently bind to whichever selector containing that substring appears first in the stylesheet. Adding a scoped override earlier in the file (like a step-specific `#stepContent[...] .choice-card`) flips the match and fails an assertion whose target style is actually intact. Fix: before classifying such a failure as a missing style, grep the stylesheet for the asserted property; when fixing, anchor the helper/assertion to the base selector rather than weakening the style check.
- **Model-scoped long-tail sheet gap:** New-model or promotion planning graded only against the model-metadata quintet (`model_master`, `model_variants`, `variant_master`, `model_workbook_sources`, `model_registry_promotion`) and the `*_options`-family sheets misses the model_key-scoped presentation sheets (`runtime_steps`, `section_presentation`, `context_section_master`, `order_summary_sections`, `step_order_summary_map`), whose absence only surfaces as a `ValueError` at post-promotion generation — `runtime_metadata.py` refuses fallback metadata for promoted models. Fix: when making or verifying any new-model plan, probe per-`model_key` row coverage across every model_key-scoped sheet in the workbook, not just the metadata quintet; require the plan to fail at plan/validation time (not promotion time) on empty required per-model sheets.
- **Surfaced-but-not-enforced review findings:** A wizard/UI pass can render a mandatory finding (e.g. a variant-reconciliation disagreement) prominently while the completion gate never reads it — the maker's own "full completion" fixture test then proves the wrong behavior by driving a disagreeing case to complete. Fix: for every spec clause of the form "X becomes a mandatory/blocking decision", probe whether the gate function can succeed while X is open; encode the disagreeing fixture case as the regression test, and when a gate gains a new blocker type, update completion-test helpers to resolve it explicitly instead of loosening the gate.
- **Fixture-shadowed branches:** A fail-closed fallback path (e.g. cross-model RPO matching when candidates aren't shared) can have zero real coverage because every fixture AND the real dataset happen to take the primary branch — tests and browser proof both pass while the guard path is unverified. Fix: when adding a matching/fallback branch, add a fixture or synthetic input that forces it, and grep tests for the branch's skip/error reason strings as the coverage check. Same class for negative-path filters: the excluded/polluting data must actually exist in the fixture (an inactive source whose sheet is never created lets an unrelated existence guard satisfy the test). Related proof hygiene: after fixing a bug mid-proof, re-create (or clean) artifacts persisted by the pre-fix code — re-inspecting the render is not enough, and downstream engines (copy, plan) propagate the stale records.
- **Enumerated-gaps-only plan validation:** A plan/apply pass that validates only through enumerated gap kinds misses edges nobody enumerated (e.g. an approved decision whose payload carries zero rows). Pair the enumeration with bidirectional coverage invariants — every op traces to a decision or named scaffold rule AND every approved decision traces to ≥1 op — and gate validity on both. Companion rule: when a real-data dry run finds a defect the fixtures never hit, back-port the triggering shape into the fixture in the same pass, or the fix ships without a regression guard.
- **Completion-record staging drift:** "Staged, not committed" is a checkable claim that silently goes false because `git rm`/`git mv` auto-stage while plain file edits and new files do not — the index then lags the worktree and committing it would produce a broken/incomplete commit (e.g. a test reading a file the same index deletes). Fix: before writing any completion record or handing to a verifier, run `git status --porcelain` and confirm no pass-attributable ` M`/`??` lines remain; verify index self-consistency with `git show :<path>`, not just worktree correctness.

- **Invisible-not-empty UI reports:** A user report that a control "never populates" or "shows nothing" can be a contrast/visibility bug, not a data bug — B.4's reference-model dropdown carried full data behind a `#555`-on-`#111214` label (hardcoded grays from a light-theme habit inside a dark-theme stylesheet). Before hunting the data path, verify the rendered control with computed styles (`getComputedStyle`, not screenshots or DOM presence), and grep the stylesheet for hardcoded hex grays that bypass the theme variables.

- **Surface-string dedup keys:** Duplicate/collision detection must key on the domain's identity, not on rendered strings — flagging duplicate proposed option names by candidate count marked 298/298 rows because GM legitimately lists every RPO on both a category sheet and "Additional Options"; keying on distinct RPOs per name gave the true 13 collisions. Before shipping any duplicate flag, ask what the domain treats as the same thing and count that; also compute the flag over the full scope, not the currently filtered view.

- **Automation-pane scroll events:** In the in-app Browser pane, programmatic scrolling (`window.scrollBy`, `scrollIntoView`) changes `scrollY` without dispatching any `scroll` event — a scroll listener under test appears dead while working fine for real users, and a hasty "fix" would chase a nonexistent bug. Verify scroll-driven behavior with real input (the computer tool's scroll action) or by dispatching a synthetic `scroll` event on `document`, and treat "scrollY moved but no listener fired" as an automation artifact until a dispatched event also fails.

- **Adverb rubrics:** A criterion like "flagged exceptions drop materially" is ungradable — the verifier had to invent the metric post-hoc (flag composition, marker-match rate) and the headline count moved 5% while the actual goal hit 100%. Write criteria as named measurable metrics ("zero unmatched-footnote flags on the real export"), and have verifiers reproduce before/after numbers by reconstructing the prior code via `git show HEAD:<path>` into a scratchpad module instead of trusting recorded values.

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
