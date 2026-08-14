# Independent verifier report — 2026-07-26-pass2-compat-scope-and-six-model-gate

Separate context. Saw the rubric, the diff, and the claimed evidence; did not
see maker reasoning. Instructed to falsify, not to confirm.

## Verdict

**PASS with should-fix findings.** No receipt claim was found false. Three were
imprecise or misleading and one documented coverage reduction was undisclosed.
R10.1 was met only partially. All four have since been fixed in this run; the
maker's post-fix re-run is recorded in `validation-output.txt`.

## Criteria

Graded against `outcome.md` as delivered to the verifier, before fixes.

| Criterion | Status | Evidence |
|---|---|---|
| R8.1 consumer scan exhaustive | partial | Every code consumer reproduced; `.hermes/plans/*` and the spec itself mention the artifact and were not enumerated (documentation only) |
| R8.2 secondary-output status proven by call path | met | Real resolver over real rows; all six promotion rows are `runtime_contract` with explicit `artifact_path`; nothing resolves to the compat JSON |
| R8.3 parity, no allowlist | met | comparator exit 0; `cmp` exit 0; independent sorted-key raw diff shows exactly one differing line, `generated_at` |
| R8.4 disposition + Stage B candidate | met | CSV reader count independently reconfirmed as zero |
| R10.1 model set independent of discovery | **partial** | Catches a discovery-code bug (proved); cannot catch a workbook deactivation (proved). Docstring's second clause was false |
| R10.2 real entrypoint, isolated root | met | Fixture shells out per model with `--output-root` |
| R10.3 strict validator on the file on disk | met | Post-validation corruption of the written bytes fails 6/6 |
| R10.4 variant counts vs workbook | met | Injected variant drop fails 6/6; load-bearing because the validator does not check variants |
| R10.5 explicit six-model assertion | met | Deactivating `zr1x` → `assert 5 == 6` |
| R10.6 protected surfaces hashed before/after | met | `before` captured before generation begins; an injected mid-fixture write to `form-output/` is caught |
| R10.7 negative proof | met, weak | Real validator and real config; only the coarsest rejections exercised |
| R10.8 spec gate block green as written | met | `104 passed, 88 subtests`; the file has never existed in git history, so the block could not previously collect |
| X1 no test shaped to implementation | partial | One docstring claim false; the discovery-comparison test inert against workbook mutation |
| X2 full gate parity | met | `1 failed, 523 passed, 2 skipped`; all 16 node tallies identical |
| X3 independent verifier | met | this report |
| X4 honest receipt | partial | findings 2, 3, 6 |

## Findings

**1 — should-fix. `test_discovery_matches_the_workbooks_own_active_model_set`
cannot fail on any workbook change; its docstring said otherwise.**

Both sides read the same `model_master.active` column, and
`discover_generation_model_configs()` raises rather than dropping a model it
cannot build (`model_configs.py:200-213`). Discovery's return value is therefore
the active `model_master` set by construction.

- Mutation A — deactivate `zr1x` in a workbook copy: `1 failed, 18 passed`; the
  failure was `assert 5 == 6`. The named test **passed**. Collected tests
  silently fell 22 → 19 because the parametrized groups shrink with the workbook.
- Mutation B — deactivate `zr1x`'s `color_overrides_sheet` row: `22 errors` in
  fixture setup; the named test never reaches its assertion, so the docstring's
  "or the workbook activates one it cannot build" clause is unreachable.
- Mutation C (control) — simulate a discovery-code bug by popping `zr1` from the
  returned dict: `5 failed, 17 passed`, including the named test. It does do real
  work against code regressions.

Only unintended asymmetry makes the two sides ever disagree on a workbook edit:
the test reads `active` strictly while discovery treats blank as active.

**2 — should-fix. The six named model keys were no longer asserted anywhere.**

`git show HEAD:tests/test_generate_form_model_discovery_cli.py` asserted
`set(configs) == {"stingray","grand_sport","grand_sport_x","z06","zr1","zr1x"}`.
The new harness replaced it with a count. A workbook edit renaming or swapping a
model key while keeping six rows active would pass the whole Pass 2 gate. The
receipt disclosed the loop removal and the stdout-key move but not this.

Assertion-by-assertion diff of the removed loop: ten of eleven old assertions are
covered by the new harness (return code, stdout key shape, `model_key`,
`validation_errors`, path confinement, existence, `runtime_active`,
error-severity rows via the validator, and the protected-surface hashes, which
are covered more broadly). Membership was the only gap.

**3 — note. "Zero readers anywhere in the active tree" for the CSV is literally
false.** `test_all_model_runtime_generation.py:88` and
`test_generate_form_model_discovery_cli.py:40` both `read_bytes()` every file
under `form-output/`, the CSV included. Hashing, not consuming — but the run's
own new file contradicts its absolute phrasing. The substantive claim reproduced:
no code branch consumes CSV content.

**4 — note, pre-existing. `assert_runtime_contract` does not enforce the spec's
variant rejection rules or the workbook binding.** Probing the real validator
with the real Stingray config:

```
drop last variant       ACCEPTED      empty steps            rejected
duplicate a variant     ACCEPTED      remove orderSummary    rejected
rename a variant_id     ACCEPTED      status -> draft        rejected
drop one choice         ACCEPTED      empty choices          rejected
wrong source_workbook   ACCEPTED      blank dataset.name     rejected
                                      error-severity row     rejected
```

The spec's rejection matrix requires rejecting miscounted or duplicate variants
and a workbook binding that does not match the candidate snapshot. Neither is
enforced. Framing R10.3 as *the* strict gate overstates the validator's coverage.

**5 — note.** The negative proof therefore establishes discrimination only at the
"collection is empty / key is missing" level.

**6 — note, imprecise.** "The suite generates the six-model set once per run
instead of twice" — before this run it was generated once, by the CLI test.
"Twice" is the counterfactual had the harness been added without removing the
loop.

**7 — note, confirmed.** Running all 16 node gates dirties `form-app/data.js` and
two runtime contracts by `generated_at` only — 4 lines, exactly the files the
receipt names. Restored with `git checkout --`.

**Verifier's own disclosure.** While reproducing the `test_schema_validation_metadata.py`
experiment the verifier wrote through a symlink into the tracked file
(`1 file changed, 2 deletions(-)`). Restored immediately with `git checkout --`;
the in-flight suite run was killed and re-run clean. Final tree matches the run's
intended three entries and the workbook SHA-256 is unchanged.

## Claims reproduced exactly

- Workbook SHA-256 `d11674e3213a8858b13f5e4283b82868046ed34335c96419a8fe909034760bfd`,
  unchanged start and end; `form-output/` and `form-app/data.js` clean vs HEAD.
- Parity: comparator `contracts match` exit 0; `cmp` exit 0; independent
  sorted-key raw diff shows one line, `generated_at`. No allowlist.
- No promotion row resolves to the compatibility JSON — **stronger than claimed**:
  the fallback branch is unreachable for all six rows, not only the three promoted.
- `promotion_requires_runtime_contract_assertion` has zero callers; every other
  hit is a `.claude/worktrees/` copy.
- The R8.1 correction reproduces verbatim: removing the two fixture lines gives
  `1 failed, 43 passed` with `Promoted model artifact does not exist for stingray`.
- Gate block `104 passed, 88 subtests passed`; full suite `1 failed, 523 passed,
  2 skipped`; all 16 node tallies identical including the three known failures.
- "Green as written for the first time": `git log --all --` for the new file is
  empty, so the block previously failed at collection.

## Could not verify

1. The 501-passed pre-run baseline was not re-run at HEAD. Arithmetically
   consistent (523 + 1 − 22 − 1 = 501) but not executed.
2. The narrative about a renamed-snapshot spurious difference on the first
   attempt — a process claim with no artifact. The resulting code comment is sound.
3. `run.json` did not exist at verification time; closeout must clear both that
   and the STATE.md reference for the loop-contract test to pass.

## Evidence inspected

- `fable5loop/runs/2026-07-26-pass2-compat-scope-and-six-model-gate/outcome.md` (rubric)
- `git diff -- tests/` and the full text of `tests/test_all_model_runtime_generation.py`
- `git show HEAD:tests/test_generate_form_model_discovery_cli.py` for the removed assertions
- `docs/superpowers/specs/2026-07-23-validation-single-lane-active-surface-cleanup.md` Pass 2 requirements 8 and 10, §3.7, §3.8
- `scripts/corvette_form_generator/registry_promotion.py`, `runtime_contract.py`, `model_configs.py`, `production.py`, `model_generation.py`
- `stingray_master.xlsx` sheets `model_master` and `model_registry_promotion`, read through the real loaders
- Mutated copies of the workbook and of the harness, in temporary directories only

## Validation Output Inspected

`fable5loop/runs/2026-07-26-pass2-compat-scope-and-six-model-gate/validation-output.txt`, re-executed rather than read:
the Pass 2 gate block (104 passed / 88 subtests), the full Python suite
(1 failed / 523 passed / 2 skipped), all 16 node gates, both parity comparisons,
the workbook SHA-256, and the R8.1 fixture-removal failure. All reproduced.

## Required Fixes Before Pass

1. Correct `test_discovery_matches_the_workbooks_own_active_model_set`'s docstring; it claims a
   failure mode the test cannot reach.
2. Restore a membership assertion over the six named model keys, and pin the parametrized tests to
   the named set so per-model coverage cannot shrink with the workbook.
3. Correct the receipt's "zero readers" and "once instead of twice" phrasings.

All three were applied and re-run (`31 passed`) before closeout.

## Durable Lesson Candidates

1. A test whose expected set is derived from the same source the code under test reads cannot detect
   a change to that source. Pair derived comparisons with a named expected set; pin `parametrize` to
   the named set; state per assertion which direction of change it catches.
2. "No consumer" from a filename grep is unsound when paths are constructed by f-string. Resolve
   paths through the real resolver over the real rows, and confirm by deleting the suspected-dead
   line and re-running.

Both were added to `fable5loop/skills/27vette-fable5-compounding.md`.

## File Edit Statement

The verifier modified no tracked file as part of verification. Two incidents were self-disclosed and
reverted immediately with `git checkout --`: node gates rewriting `form-app/data.js` and two runtime
contracts by `generated_at`, and a symlinked scratch edit that reached
`tests/test_schema_validation_metadata.py`. The final tree contains only this run's intended entries
and the workbook SHA-256 is unchanged.
