# Independent verifier report — 2026-07-26-pass3-candidate-lane

Separate context. Saw the rubric, the diff, and the claimed evidence; not the
maker's reasoning. Instructed to falsify.

## Verdict

**Cycle 1: FAIL.** The implementation is substantially correct and its
load-bearing claims survive adversarial testing, but it failed on four counts: a
rubric-scoped requirement was silently not delivered, two receipt claims were
false as written, and two of requirement 12's proofs caught nothing. All six
findings were fixed and re-proved; see `validation-output.txt` for the post-fix
evidence.

The verifier modified no tracked file and never needed `git checkout --`.

## Criteria

| # | Status | Evidence |
|---|---|---|
| P1 | partial | All ten stages ran in order in a real run, but stage 10 ran after a stage-7 failure (Finding 2) |
| P2 | met | Package defect → `workbook_package`; options defect → `options_sheet_quality`; generation failure → `generate_models`; later stages genuinely unrun |
| P3 | met | `declared=[z06]` vs `declared=[]`: generated set, registry set, and per-model drift all identical |
| P4 | partial | Undeclared drift fails; but a duplicated row was invisible and `orderSummary.sections` was positional (Finding 5) |
| P5 | met | `--changed-model '*'` → all six declared, `ok: True` |
| P6 | met | Report on disk with `schemaVersion` and every §3.7.1.4 field per model |
| P7 | met | One `assert_runtime_contract(..., config=…)` call; one dead duplicate check (Finding 7) |
| P8 | met | Harness: 48/48 on empty registry, 48/48 on missing file, 42/6 on a registry missing z06, 48/0 on a byte-identical copy |
| P9 | partial | Asserted on normal and `StageFailure` paths, not on exception or `KeyboardInterrupt` (Finding 3) |
| X1 | met | Every test carries a "Breaks if…" docstring |
| X2 | unmet | 2 of 4 weakenings caught (Finding 4) |
| X3 | not verified | Full Python suite and 15 of 16 node gates not re-run |
| X5 | unmet | Requirement 6 in scope, undelivered, not restated as open (Finding 1) |

## Findings

**1 — blocking. Requirement 6 in scope, undelivered, unmentioned.**
`tests/z06-runtime-promotion.test.mjs:161` still ran `scripts/generate_registry.py`
against the tracked app. The receipt listed only requirements 7/8/9 as deferred
and attributed the resulting `data.js` churn to Pass 4A — but that churn is
exactly what requirement 6 owns. Also unmodified from §3.7's file list without
comment: `generate_registry.py`, `registry_promotion.py`, `schema_validation.py`
and three test files (most belong to deferred 7/8/9; requirement 6's file does not).

**2 — should-fix. "Stages after a failure do not run" false for stage 10.**
Injecting a `validate_contracts` failure produced `stagesRun` ending in
`semantic_drift` and a report with two failed stages, because the drift block sat
outside the `try/except StageFailure`. Gating was correct (`failedStage` named the
earlier stage); reporting fidelity was not. Secondary: `stagesNotRun` could not
distinguish an early abort from `run_harness=False`.

**3 — should-fix. Byte-identity not asserted on every code path.**
A nonexistent workbook, an exception inside a stage runner, and a
`KeyboardInterrupt` mid-stage each escaped before the check — no report, no
`boundaryViolations`. The protected surfaces were byte-identical after every
attempt, so no write vector was found; the false claim was about the assertion.
Related and unexecuted: `--harness` is caller-selectable, so pointing it at a
writing gate would let the lane's own subprocess rewrite `form-app/data.js`.

**4 — blocking. Two of requirement 12's proofs caught nothing.**
Against a weakened lane shadowed via `PYTHONPATH`:

| Weakening | Caught by |
|---|---|
| `declared` used as a generation filter | `test_declaring_a_changed_model_does_not_reduce_the_generated_set` ✓ |
| drift made positional | `test_drift_detection_ignores_order_but_not_content` ✓ |
| `boundary_violations = []` hardcoded | **nothing** |
| stage 9 removed (`if False:`) | **nothing** |

No test ever observed a non-empty `boundaryViolations`, and every fixture passed
`run_harness=False`, so deleting stage 9 was invisible to the whole file.

**5 — should-fix. Drift missed a real change and reported a false one.**
`contract_entity_index` built `{key: row}` dicts, so duplicate identities
collapsed: appending a byte-identical duplicate `choices` row gave zero drift
(latent — all six current contracts have unique keys, verified across all twelve
`ENTITY_KEYS` collections). And it walked only top-level lists, so
`orderSummary.sections` reversed reported `['orderSummary']` — a false positive of
exactly the kind the design exists to prevent.

**6 — note.** Stage 7 largely re-runs the assertion
`build_model_runtime_contract()` already performs before writing; proving it
required injection rather than a real defect.

**7 — note.** The lane's "exactly one default model" check is unreachable —
`load_registry_promotions()` raises on that first.

## Claims confirmed under adversarial testing

- **Scoping never narrows.** `declared` is read at exactly one site plus report
  assembly; generation, validation, and registry all iterate the full set. Two
  full runs: generated set, registry set, and drift rows all equal.
- **Fail-closed ordering** for package, schema, options, and generation defects —
  later stages genuinely unrun, `models` empty, not merely unreported.
- **The browser stage has no fallback.** env unset → 48/48; empty registry →
  0/48; nonexistent path → 0/48; byte-identical copy → 48/48; copy with `z06`
  deleted → 42/6. In a real lane run stage 9's `data_js` was inside the lane's
  temp root.
- **Promotion gating.** `promote_model.py --model z06` exits 1 with
  `candidate_lane_failed`, no `backup_path`, all ten stages in order, protected
  paths clean. An exception or `KeyboardInterrupt` escaping the lane aborts
  before `save_workbook_safely` rather than writing.
- **"Not a synthetic failure"** — confirmed; it is the staleness STATE.md
  recorded on 2026-07-25, caught by a gate for the first time.
- **"Before this change the command reported `validated`"** — confirmed by
  running `git show HEAD:scripts/promote_model.py`: `status: validated, ok: True`.
- **Escaping artifact paths** are rejected by `resolve_artifact_path()`, and it is
  a read path regardless, so no write vector exists there.

## Could not verify

1. Python full-suite parity (542 passed) — not run; ~13 minutes, budget spent on
   nine full lane invocations. The +19 accounting is plausible but unchecked.
2. `tests/test_verify_workbook_candidate.py` end-to-end unmodified — ran 5 of 12
   tests, against weakened builds.
3. `tests/test_promote_model.py` — verified by reading plus injection, not by run.
4. 15 of 16 node gate tallies, including the three claimed pre-existing failures.
   The one gate this change modified was run (48/0 with the override unset).
5. Whether `--harness` pointed at a writing gate actually dirties tracked paths —
   deliberately not executed to avoid contaminating concurrent measurements.
6. Closeout: at verification time the run folder had no `run.json` or verifier
   report and STATE.md had no Pass 3 entry. The spec's Pass 3 section is
   correctly not marked complete.

## Evidence inspected

- The rubric and `validation-output.txt` for this run
- `scripts/verify_workbook_candidate.py`, `scripts/promote_model.py` (and
  `git show HEAD:` of the latter), `registry_promotion.py`, `runtime_contract.py`
- `git diff` for the modified test files; both new files in full
- The spec's Pass 3 section, §3.7, §3.7.1, §3.8
- Mutated copies of the workbook, of the lane, and of the registry, in temporary
  directories only

## Validation Output Inspected

`fable5loop/runs/2026-07-26-pass3-candidate-lane/validation-output.txt`, with the
claims re-executed rather than read: the full lane in both declared and
undeclared form, `promote_model.py --model z06`, the harness probes, the
fail-closed injections, and the boundary attempts. Nine full lane invocations.

## Required Fixes Before Pass

1. Deliver requirement 6 or remove it from the claimed scope and record it open.
2. Stop stage 10 from running after an earlier stage failure; distinguish
   caller-skipped stages from unreached ones.
3. Make the byte-identity assertion cover exception and interrupt paths.
4. Add tests that fail when the boundary check is removed and when stage 9 is
   removed.
5. Fix duplicate-identity collapse and nested-list positional comparison in the
   drift index.
6. Remove the unreachable duplicate default-model check.

All six were applied and re-proved; evidence in `validation-output.txt`.

## Durable Lesson Candidates

1. A criterion of the form "the tool asserts X itself" is not proven by tests
   that only ever observe X passing. At least one test must observe the assertion
   *firing*, or a build that never computes X satisfies the whole suite.
2. When every test in a file disables an expensive stage for speed, that stage
   has no coverage at all — deleting it is invisible. Keep exactly one test that
   runs the whole thing.
3. A scope line in a rubric is a claim. Enumerate the requirements it names
   against the diff before writing the receipt; the one that quietly goes missing
   is the one whose damage gets misattributed to another pass.

## File Edit Statement

The verifier modified no tracked file. `stingray_master.xlsx` and
`form-app/data.js` hashed identical at start and end;
`git status --porcelain -- stingray_master.xlsx form-app/data.js form-output`
was empty throughout. All mutation was performed on copies in temporary
directories.
