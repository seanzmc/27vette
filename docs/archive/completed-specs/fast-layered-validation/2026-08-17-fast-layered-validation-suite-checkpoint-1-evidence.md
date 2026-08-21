# Checkpoint 1 measured evidence — fast layered validation suite

Evidence file for `docs/archive/completed-specs/fast-layered-validation/2026-08-17-fast-layered-validation-suite.md` §9,
Checkpoint 1. Raw tool output, captured 2026-08-17. The durable, queryable form of
these numbers is `tests/validation_catalog.json`; this file is the transcript behind it.

Environment: darwin 25.6.0 arm64; node v26.7.0; python 3.14.7 (`.venv`).
Method: one process per gate, run serially — the same method as the Checkpoint 0
baseline, so the two are comparable.

## 1. Node lane, all 16 files, after the rewrite

One serial run, recorded whole so the per-gate seconds sum to the lane totals.
`tests/validation_catalog.json` carries the same numbers from the same run.

```text
GATE tests/grand-sport-contract-preview.test.mjs exit=1 seconds=1.46 | tests 5 pass 4 fail 1
  AssertionError: rule/detail hot spot buckets are preserved for later phases (22 vs 25)
  -- Layer 4 diagnostic. stale.grand_sport_preview_requires_hotspot_count, Checkpoint 2.
GATE tests/grand-sport-runtime-contract.test.mjs exit=0 seconds=3.25 | tests 19 pass 19 fail 0
GATE tests/multi-model-runtime-switching.test.mjs exit=0 seconds=4.52 | tests 70 pass 70 fail 0
GATE tests/nonruntime-option-source-purge.test.mjs exit=0 seconds=1.67 | tests 6 pass 6 fail 0
GATE tests/stingray-form-regression.test.mjs exit=0 seconds=4.58 | tests 91 pass 91 fail 0
GATE tests/stingray-runtime-contract.test.mjs exit=0 seconds=17.71 | tests 12 pass 12 fail 0
GATE tests/tracked-artifacts-guard.test.mjs exit=0 seconds=1.11 | tests 7 pass 7 fail 0
GATE tests/workbook-schema-standardization.test.mjs exit=0 seconds=0.91 | tests 12 pass 12 fail 0
GATE tests/workbook-visual-copy-standardization.test.mjs exit=0 seconds=0.68 | tests 8 pass 8 fail 0
GATE tests/z06-contract-preview.test.mjs exit=0 seconds=1.35 | tests 2 pass 2 fail 0
GATE tests/z06-interior-accessory-cleanup.test.mjs exit=0 seconds=1.81 | tests 7 pass 7 fail 0
GATE tests/z06-performance-package-interactions.test.mjs exit=0 seconds=6.64 | tests 21 pass 21 fail 0
GATE tests/z06-published-runtime.test.mjs exit=0 seconds=0.48 | tests 4 pass 4 fail 0
GATE tests/z06-registry-publication.test.mjs exit=0 seconds=1.44 | tests 2 pass 2 fail 0
GATE tests/z06-runtime-contract.test.mjs exit=0 seconds=1.82 | tests 24 pass 24 fail 0
GATE tests/z06-runtime-rule-corrections.test.mjs exit=0 seconds=6.01 | tests 15 pass 15 fail 0
TOTAL 55.44
```

Against Checkpoint 0: all 16 files 111.75 s -> 55.44 s; the fourteen documented
readiness gates 109.27 s -> 52.63 s, and their 6 failures across 5 files -> 0.

**Collected tests: 305 across all 16 files, 298 across the 14 readiness gates —
unchanged in total from Checkpoint 0.** `grand-sport-runtime-contract` went
18 -> 19 (one stale test split into two parity tests) and
`workbook-schema-standardization` 13 -> 12 (duplicate schema invocation
removed); those cancel. An earlier draft of this file and of the catalog stated
"309 tests over the 14", which no set of per-gate counts could produce; PR review
caught it. The catalog contract test does not sum `collected_tests` against prose,
so nothing failed — the arithmetic is stated here so it can be rechecked.

Wall times are approximate, not budgets: three serial runs of the full set
measured 53.27 s, 54.56 s and the 55.44 s recorded above. A hard timing budget
needs three stable baseline runs (spec §5, Layer 1).

Per-file movement worth naming:

| Gate | Checkpoint 0 | Checkpoint 1 | Why |
|---|---|---|---|
| `workbook-schema-standardization` | 64.97 s, 13 tests | 0.91 s, 12 tests | duplicate schema invocation removed |
| `z06-runtime-rule-corrections` | 3.91 s, 15 tests | 6.01 s, 15 tests | the sweep exercises every peer of every case, and reads the workbook for its expected side |
| `stingray-form-regression` | 2.54 s, 91 tests | 4.58 s, 91 tests | same reason |
| `grand-sport-runtime-contract` | 3.07 s, 18 tests, 2 fail | 3.25 s, 19 tests | one stale test split into two parity tests |

## 2. Python owners this checkpoint touched

```text
tests/test_runtime_metadata_guards.py    11 passed in 0.25s
tests/test_validation_catalog.py         19 passed in 0.03s
```

Run alone with `PYTHONPATH` unset (`env -u PYTHONPATH`), which errored or failed
at the Checkpoint 0 baseline:

```text
tests/test_rule_derivation.py                    15 passed in 0.02s
tests/test_source_assembly_characterization.py   32 passed in 9.41s
tests/test_options_sheet_quality.py              18 passed in 0.28s
```

Candidate lane, full file:

```text
tests/test_verify_workbook_candidate.py          16 passed in 684.74s (0:11:24)
```

At the Checkpoint 0 baseline this file measured 694.43 s with the two drift
canaries failing. Both now pass against a live probe, and the `semantic_drift`
stage has positive proof: the undeclared run reports `unexpected_drift == ["zr1"]`
and fails at that stage, while the declared run passes with the same non-empty
drift set. Run alone first, the drift pair measured `4 passed, 12 deselected in
209.00s`.

Re-run after the PR-review fixes: `test_runtime_metadata_guards.py` and
`test_validation_catalog.py` together, `30 passed in 0.24s`; the three
standalone files again `15`, `32`, `18` passed with `PYTHONPATH` unset.
`test_verify_workbook_candidate.py` was not re-run after those fixes — none of
them touch it.

## 3. Mutation canaries

Method: `git worktree add --detach /private/tmp/cp1-canary HEAD`, with the
Checkpoint 1 test files copied in. Every mutation is applied to that worktree's
own copy of the workbook, generator, or runtime. The canonical
`stingray_master.xlsx`, the tracked artifacts, and the working tree were never
mutated; the worktree was removed afterwards.

### §8.1 — a valid active asset URL change

```text
MUTATED ('grand_sport', 'opt_j6a_001',
         '.../brakes/e-g-j6a-o-cmp.webp' -> '.../brakes/e-g-j6a-o-cmp-canary.webp')
node --test tests/grand-sport-runtime-contract.test.mjs   tests 19 pass 19 fail 0
node --test tests/z06-runtime-contract.test.mjs           tests 24 pass 24 fail 0
```

Structural and parity layers stay green; no literal URL test fails. This is the
canary the retired J6F pin could not have passed.

### §8.2 — one valid new colour-override row

```text
ADDED {'interior_id': '1LT_AQ9_HUQ', 'option_id': 'opt_uvb_001',
       'rule_type': 'requires', 'adds_rpo': 'opt_d30_001'}
emitted colorOverrides 281 -> 282
node --test tests/grand-sport-runtime-contract.test.mjs   tests 19 pass 19 fail 0
```

Coverage expands with no hardcoded aggregate count involved. The retired
`assert.equal(draft.colorOverrides.length, 263)` would have failed on both the
pre- and post-mutation workbook.

### §8.3 — a promoted-model membership change

```text
DEPROMOTED zr1x (model_registry_promotion.promoted_to_runtime -> False)

before republication:
  z06-registry-publication      tests 2  pass 1 fail 1
    - publication parity PASSES: result.models follows the workbook to 5 models
    - the rebuild-vs-tracked-registry comparison FAILS, correctly: form-app/data.js
      is now stale relative to the workbook
  z06-published-runtime         tests 4  pass 3 fail 1  (reads the same stale registry)
  multi-model-runtime-switching tests 70 pass 70 fail 0 (also reads the stale registry)

after `.venv/bin/python scripts/generate_registry.py` inside the canary worktree:
  registry_generated ['stingray', 'grandSport', 'grand_sport_x', 'z06', 'zr1']
  z06-registry-publication      tests 2  pass 2 fail 0
  z06-published-runtime         tests 4  pass 4 fail 0
  multi-model-runtime-switching tests 70 pass 62 fail 8
```

Both parity gates follow the change. The declared membership pin fails
deliberately, which is what §8 canary 3 asks for — with the caveat that it fires
only after republication, because it reads the published registry rather than the
promotion rows.

### §8.5 and forced failures — the new assertions are not vacuous

```text
inspection.py stops applying image_alt from asset_map
  -> grand-sport-runtime-contract 18/19
     "1lt_e07__opt_eyt_001 image_alt does not match its active asset_map row"

build_color_overrides drops one resolvable row
  -> grand-sport-runtime-contract 18/19
     "emitted colorOverrides drifted from the resolvable rows of color_overrides"

rules.py drops one interior-sourced includes row
  -> z06-runtime-contract 23/24
     "emitted interior-sourced includes rules drifted from their workbook rows"

app.js disableReasonForChoice returns "" for seat-belt choices
  -> z06-runtime-rule-corrections 14/15
     "3LZ_AH2_HVZ should refuse opt_719_001, which the workbook marks unavailable"
  -> stingray-form-regression 90/91
     "3LT_AE4_HAG should refuse opt_719_001, which the workbook marks unavailable"

load_default_selection_display_rules drops its first row per model
  -> tests/test_runtime_metadata_guards.py 3 failed, 8 passed
```

### Omission canaries added after PR review

Review found the first version of the Stingray sweep deriving its cases, blocked
peers, and added RPOs from the payload it was exercising: a generator that
dropped one relationship removed the case and its expectation together, and the
non-empty guard only fired if *every* case disappeared. Both sweeps now read
their expected relationships from the model's registered rule-mapping and
colour-override sheets and assert registry-vs-workbook parity before driving the
runtime. These two canaries are the proof that the omission is now visible —
neither was run before, and neither would have failed the earlier version.

Both were run in a second throwaway worktree, regenerating stingray and z06 and
republishing the registry inside it.

```text
rules.py drops one interior-targeted excludes row
  -> stingray-form-regression 90/91
     "published interior exclude rules drifted from the workbook rule-mapping sheet"
  -> z06-runtime-rule-corrections 14/15
     same assertion

build_color_overrides drops one resolvable row
  -> z06-runtime-rule-corrections 14/15
     "published colour overrides drifted from the workbook colour-override sheet"
  -> stingray-form-regression 88/91
     its own override-parity assertion plus two pre-existing D30-context tests
```

## 4. What this checkpoint did not measure

- Node 22 / Python 3.12 CI reference timings. Still uninstalled on this machine;
  every number above is local evidence and is not the CI baseline.
- The Workbook Manager checkpoint inventory and the full Python inventory. No
  file in either lane was changed except through `tests/conftest.py`, which only
  adds a `sys.path` entry those files already depended on transitively.
- Spec §8 canaries 4, 6, 7 and 8. They belong to later checkpoints.
