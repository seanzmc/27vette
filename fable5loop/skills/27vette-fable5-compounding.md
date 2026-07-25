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
- **Profile metadata shadows or over-expands target evidence:** An RPO mentioned by comparator/profile metadata is treated as fully profile-owned, suppressing target price/status/copy; a shared interior code is treated as requiring every unique interior under that code even though LT/LZ metadata pairs ancillary RPOs with exact `interior_id` rows; or the source ledger marks a profile effect compiled without material dependencies. Fix: reconcile each evidence axis independently; target evidence owns target facts; profile-owned seat/suede/stitch/two-tone compatibility filters shared codes to the exact compatible unique interior IDs and fails closed when none match; every emitted endpoint must be compatible; and every compiled profile effect must carry all declared target dependencies on the exact `interiors` or `model_interior_scope` row that materializes the behavior.
- **Comparator price semantics collapse:** Matching some subset of trim, condition RPO, numeric price, body scope, target RPO, or rule type is treated as enough to reconcile comparator pricing; a semicolon-combined convertible/coupe qualifier is mistaken for one wildcard scope; or multiple applicable target rows with one distinct normalized price remain falsely ambiguous. Fix: require complete condition/target/type/body/trim/variant identity per qualifier clause, require all clauses to be covered, and collapse target ambiguity by distinct target-owned `listPrice` values only after model/body/trim/RPO scoping. Keep price-ledger entries target-scoped, and join unmatched price rows to a `refOnlyRpo` occurrence before compilation so material target options such as R8E retain their raw target price dependency.
- **Transformed evidence ID aliasing:** Target-specific transformed rows reuse one comparator-derived evidence ID even though their semantic payloads differ. Fix: include the target identity in transformed evidence IDs and make artifact validation reject one ID carrying multiple semantic fingerprints.
- **Silent protected-boundary failure:** Dealer submission, workbook write, or safety-boundary issue is treated like a normal error. Fix: escalate and record as boundary/fallback.
- **Gate-induced artifact churn:** Some validation gates regenerate tracked generated artifacts — the Grand Sport and Z06 draft/preview gates rewrite `generated_at` in `form-output/runtime/*-runtime-contract.json`, and the promotion gate (`z06-runtime-promotion`, which runs `scripts/generate_registry.py`) rewrites `form-app/data.js` — so running gates dirties generated surfaces and reads as a boundary violation. Fix: after any gate run in a pass that must not change generated artifacts, check `git status -- form-output form-app` and `git restore` timestamp-only churn before verification; verifiers must inspect read-only instead of re-running those gates, or they re-introduce the churn they then flag.
- **Order-dependent CSS-regex test helpers:** Node gates that extract CSS blocks with a first-match regex (e.g. `cssBlock('.choice-card')`) silently bind to whichever selector containing that substring appears first in the stylesheet. Adding a scoped override earlier in the file (like a step-specific `#stepContent[...] .choice-card`) flips the match and fails an assertion whose target style is actually intact. Fix: before classifying such a failure as a missing style, grep the stylesheet for the asserted property; when fixing, anchor the helper/assertion to the base selector rather than weakening the style check.
- **Model-scoped long-tail sheet gap:** New-model or promotion planning graded only against the model-metadata quintet (`model_master`, `model_variants`, `variant_master`, `model_workbook_sources`, `model_registry_promotion`) and the `*_options`-family sheets misses the model_key-scoped presentation sheets (`runtime_steps`, `section_presentation`, `context_section_master`, `order_summary_sections`, `step_order_summary_map`), whose absence only surfaces as a `ValueError` at post-promotion generation — `runtime_metadata.py` refuses fallback metadata for promoted models. Fix: when making or verifying any new-model plan, probe per-`model_key` row coverage across every model_key-scoped sheet in the workbook, not just the metadata quintet; require the plan to fail at plan/validation time (not promotion time) on empty required per-model sheets.
- **Surfaced-but-not-enforced review findings:** A wizard/UI pass can render a mandatory finding (e.g. a variant-reconciliation disagreement) prominently while the completion gate never reads it — the maker's own "full completion" fixture test then proves the wrong behavior by driving a disagreeing case to complete. Fix: for every spec clause of the form "X becomes a mandatory/blocking decision", probe whether the gate function can succeed while X is open; encode the disagreeing fixture case as the regression test, and when a gate gains a new blocker type, update completion-test helpers to resolve it explicitly instead of loosening the gate.
- **Fixture-shadowed branches:** A fail-closed fallback path (e.g. cross-model RPO matching when candidates aren't shared) can have zero real coverage because every fixture AND the real dataset happen to take the primary branch — tests and browser proof both pass while the guard path is unverified. Fix: when adding a matching/fallback branch, add a fixture or synthetic input that forces it, and grep tests for the branch's skip/error reason strings as the coverage check. Same class for negative-path filters: the excluded/polluting data must actually exist in the fixture (an inactive source whose sheet is never created lets an unrelated existence guard satisfy the test). Related proof hygiene: after fixing a bug mid-proof, re-create (or clean) artifacts persisted by the pre-fix code — re-inspecting the render is not enough, and downstream engines (copy, plan) propagate the stale records.
- **Tautological green metric:** A number cited as evidence of a clean run that a stricter validator upstream has made structurally impossible to be anything else — e.g. `generate_form.py` reporting `validation_errors: 0` when `assert_runtime_contract()` already raises on any error-severity row. It reads as proof and carries none. Fix: before citing a count as evidence, ask what code path could have produced a different value; if none exists, cite the gate that can actually fail instead, or a byte-comparison against an independent regeneration.
- **Consolidation that hides value changes:** Collapsing two output shapes into one is reported as "derived from X instead of Y", which conceals both dropped fields and same-named fields whose *meaning* changed (a `validation_warnings` that counted draft rows now counting contract rows, going 1 → 0). Fix: enumerate every removed key with its consumer search, and separately label each surviving key as a relocation or a value change with a measured before/after.
- **Refactor scope drifts past the claim:** Wrapping a body in a new `try/finally` or extracting a helper can quietly fix defects the receipt never claimed and simultaneously invite receipt wording that overclaims what the change reached ("one snapshot per assembly" when it is one per builder). Fix: audit such refactors in both directions — grep for sibling functions with the same structural defect and fix or record them, and re-read every scope noun in the rubric against what the diff actually does.
- **Enumerated-gaps-only plan validation:** A plan/apply pass that validates only through enumerated gap kinds misses edges nobody enumerated (e.g. an approved decision whose payload carries zero rows). Pair the enumeration with bidirectional coverage invariants — every op traces to a decision or named scaffold rule AND every approved decision traces to ≥1 op — and gate validity on both. Companion rule: when a real-data dry run finds a defect the fixtures never hit, back-port the triggering shape into the fixture in the same pass, or the fix ships without a regression guard.
- **Staged-only-vs-committed validation blindness:** A staged-edit system that validates each pending change only against committed state silently passes staged-vs-staged conflicts (two staged adds claiming one key; a staged add referencing a staged delete), which then surface as raw DB constraint errors or unresolved refs at commit. Fix: batch validation must cross-check the staged set against itself (duplicate-key map over staged adds, existence checks aware of staged deletes), and the commit path must catch constraint violations into a structured invalid result instead of raising. Encode the two-identical-adds case as the regression test.
- **Completion-record staging drift:** "Staged, not committed" is a checkable claim that silently goes false because `git rm`/`git mv` auto-stage while plain file edits and new files do not — the index then lags the worktree and committing it would produce a broken/incomplete commit (e.g. a test reading a file the same index deletes). Fix: before writing any completion record or handing to a verifier, run `git status --porcelain` and confirm no pass-attributable ` M`/`??` lines remain; verify index self-consistency with `git show :<path>`, not just worktree correctness.

- **Invisible-not-empty UI reports:** A user report that a control "never populates" or "shows nothing" can be a contrast/visibility bug, not a data bug — B.4's reference-model dropdown carried full data behind a `#555`-on-`#111214` label (hardcoded grays from a light-theme habit inside a dark-theme stylesheet). Before hunting the data path, verify the rendered control with computed styles (`getComputedStyle`, not screenshots or DOM presence), and grep the stylesheet for hardcoded hex grays that bypass the theme variables.

- **Surface-string dedup keys:** Duplicate/collision detection must key on the domain's identity, not on rendered strings — flagging duplicate proposed option names by candidate count marked 298/298 rows because GM legitimately lists every RPO on both a category sheet and "Additional Options"; keying on distinct RPOs per name gave the true 13 collisions. Before shipping any duplicate flag, ask what the domain treats as the same thing and count that; also compute the flag over the full scope, not the currently filtered view.

- **Automation-pane scroll events:** In the in-app Browser pane, programmatic scrolling (`window.scrollBy`, `scrollIntoView`) changes `scrollY` without dispatching any `scroll` event — a scroll listener under test appears dead while working fine for real users, and a hasty "fix" would chase a nonexistent bug. Verify scroll-driven behavior with real input (the computer tool's scroll action) or by dispatching a synthetic `scroll` event on `document`, and treat "scrollY moved but no listener fired" as an automation artifact until a dispatched event also fails.

- **Unverified restore-baseline prescription:** A repair plan that prescribes "restore from git history / pre-change baseline" based on inferred regression ("compiler clobbered curated values") can be wrong because the baseline was never good — two independent audits both asserted ZR1/ZR1X curated names were overwritten, but a direct diff of `281eb14^` vs current showed the long names predate the change and zero existing values were touched. Fix: before any restore-from-history deliverable starts, diff the claimed-good baseline against current for the exact fields to be restored; treat "regressed from curated state" as a hypothesis requiring that diff, not a fact derivable from current-state badness alone. Watch for type-coercion false diffs (string `'20'` vs int `20`) when comparing workbook cells.

- **Wrong-key artifact diffs:** Comparing two generated collections by keying on a column that is not the row identity silently invents differences — keying `standardEquipment` on `section_id` (present but shared across rows) reported "2 changed" where keying on `equipment_id` showed zero. Before reporting artifact drift, confirm the chosen key is unique within the collection (`len(set(keys)) == len(rows)`), and separate *order-only* differences from content differences: a section display-order change re-sorts a 1,416-row array and produces a 38k-line diff with zero field changes.
- **Self-agreeing structural checks:** A validator that only compares peer artifacts to each other (all active option sheets must share headers; published registry must match retained artifacts) reports green on *coordinated* drift, because the things it compares still agree. Renaming one column in every active options sheet at once produced zero schema issues. Fix: every structural check needs an external authority to compare against (a shared registry, a freshly derived value), not just internal consistency. When auditing a gate, ask "what change would keep all of its comparands equal to each other while still being wrong?" and make that the RED test.
- **Widening helpers that early-return:** A function documented as "widening, never narrowing" that computes a broad set and `return`s it mid-loop silently discards everything already accumulated — and if the broad set is drawn from a different activeness/ownership source than the accumulated one, adding an input *removes* results. Fix: accumulate a flag, union at the end, and make the regression test assert the subset relation (`narrow_result <= wider_result`) rather than an exact expected set.
- **Lazy package `__getattr__` recursion:** Breaking an import cycle with PEP 562 works, but `from package import submodule` inside `package.__getattr__` recurses infinitely through `_handle_fromlist`. Use `importlib.import_module` there, and probe the unknown-attribute path too — it must raise `AttributeError`, not recurse.

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
