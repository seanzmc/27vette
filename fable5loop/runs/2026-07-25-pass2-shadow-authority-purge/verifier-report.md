# Independent Verifier Report — Pass 2 receipt B: shadow-authority purge

Run in a separate context with no access to the maker's reasoning, instructed to refute rather than
confirm and to default to FAIL on anything it could not reproduce itself.

## Verdict

**Cycle 1: FAIL** on three of eight criteria. **Cycle 2: FAIL** on five further points after the
cycle-1 fixes. Both cycles' findings are fixed and re-validated; see
`validation-output.txt`. No cycle-3 verification has been run, so the verdict on record is FAIL.

### Cycle 1 detail

FAIL on three of eight criteria. It reproduced a concrete regression, found two
missed live shadows plus two un-inventoried live defaults, and corrected the receipt's baseline
test counts. Every finding was accepted and fixed; the re-validation is recorded in
`validation-output.txt`.

## Criteria

| # | Claim | Verdict |
|---|---|---|
| 1 | Every deletion inert; 44 artifacts byte-identical | PASS — independently reproduced |
| 2 | Reachability table honest | PASS with caveats — every zero-claim holds; three counts were wrong |
| 3 | Requirement 9 genuinely closed | **FAIL** — a silent Python-default path remained *and* a new one was opened |
| 4 | New step-completeness check not weaker than what it replaced | **FAIL** — concrete regression reproduced |
| 5 | `UNAUTHORED_BUCKET_STEP_LABELS` honestly scoped | PASS — hit count misstated (48, not 6) |
| 6 | Live findings complete | **FAIL** — 2 missed live shadows, 2 un-inventoried live defaults, 2 undisposed candidates |
| 7 | No new test failure | PASS in substance; the receipt's baseline figures were wrong |
| 8 | No tracked workbook/artifact/registry/`form-app/` change | PASS |

## The blocking regression, as reproduced

The maker replaced a promoted-only check against the Python `STEP_ORDER` tuple with a check against
step keys referenced by the model's own `section_presentation` and `context_section_master` rows.
The verifier measured what those sheets actually contain: **`section_presentation` authors zero
`step_key` values for all six models** (11/12/8/7/7/12 rows, none with a step key). The new check
therefore saw 2 of 14 step keys.

Full drop-one-step matrix, baseline versus first fix, for promoted z06:

```
base_interior | base=FAILS | new=SILENT-OK
summary       | base=FAILS | new=SILENT-OK
(other 12)    | base=FAILS | new=FAILS
```

```
[base] z06 drop=summary -> ValueError: ... missing step_key values: summary
[new]  z06 drop=summary -> GENERATED OK (silent)
       steps shipped: 13, no 'summary'
```

It also caught that the maker's own rewritten test was made to pass by feeding the check the one
input it could still see — a `context_rows` entry for `trim_level` — leaving the 12 lost keys
uncovered. That is the sharpest finding in the report: the test was shaped to the implementation
rather than to the requirement.

**Fix.** `_referenced_step_keys()` now unions `section_presentation`, `context_section_master`, and
`step_order_summary_map` (13 of 14) with `_steps_every_other_active_model_authors()` (the 14th,
`summary`), minus the single recorded bucket-step gap — all workbook-derived, no Python list.
Re-measured: **14/14 for promoted z06 and 14/14 for unpromoted zr1**, versus 14/0 at baseline.
Locked by `test_dropping_any_single_runtime_step_fails_generation`, 30 subtests.

## Missed live shadows

1. **`mapping.status_to_label`** — the receipt dismissed it as "3-value map, all authored". The
   *keys* are authored; the three **display strings are Python-authored** and ship on every choice
   (z06: 789 Available / 488 Standard / 157 Not Available). Customer-visible at `app.js:1983`. This
   is the identical class the receipt itself flagged as LIVE for `SELECTION_MODE_LABELS`.
2. **`production.py` `disabled_reason` composition** — 734 of 790 workbook rule rows leave
   `disabled_reason` blank and receive a Python-composed sentence; all 795 shipped rules carry one.
   Rendered as tooltips and toasts at seven `app.js` sites. **The workbook already has the column.**
   Absent from the inventory entirely, and the highest-value remaining item.
3. **`presentation_bool(..., default=False)`** — 11 of 57 `section_presentation` rows leave
   `standard_equipment_bucket` blank, 51 leave `auto_added_bucket` blank. A live, non-fail-closed
   Python default deciding bucket membership.
4. **`inspection.SPECIAL_REVIEW_RPOS`** — `config.special_rule_review_rpos` is empty for all six
   models, so the hardcoded `{EL9, Z25, FEY, Z15}` fallback fires every run. Inspection scope only.

It further held that `production.py`'s `sec_stan_002` and `interiors.py`'s `opt_z25_001`, while
correctly *kept*, appear nowhere in the validation output — so their disposition was unstated, which
violates criterion 1's "no candidate is dismissed by reading alone".

## What it confirmed

- **Byte-identity**: fresh `git worktree` at `bdf6690`; all six models generated on both sides into
  isolated `--output-root`s. With `--emit-inspection` **44/44 identical**; without, **14/14**.
- **Every zero-hit claim holds**, re-instrumented on the baseline: `cleanup_display_text` 2,248
  calls / 0 changed; `STATUS_ALIASES` 7,452 status cells / exactly 3 distinct values / zero
  `"not available"`; `step_for_section` 10,206 calls / **10,206 from `section_master.step_key`**,
  zero from the override map, standard set, or name heuristic; `trim.replace("_R6X","")` 0 of 704;
  z25 rule-derived set 0 additions.
- **Criterion 5**: `sections[].step_label` has no consumer anywhere in `form-app/` or the tests;
  `app.js` builds `runtimeSteps` from `data.steps` and all eleven `step_label` reads go through it.
- **RED genuinely failed at baseline**: the new unpromoted-model test fails at `bdf6690`, both
  subtests. The four rewritten `test_runtime_metadata_guards.py` tests were retargeted honestly, not
  weakened.
- All 16 node gate counts match, including the three pre-existing failures.

## Refutation attempts that failed to refute

Dropping `paint` or `delivery` from zr1 — the new code correctly raises where baseline was silent.
`selection_mode_label` title-case fallback: 1,882 calls, 0 fallbacks. `STEP_LABELS.get(k, title())`:
212 calls, 0 misses at baseline. `body_style_display_order.get(bs, 99)`: only `coupe`/`convertible`
exist, never fires. Searching `form-app/` for a `sections[].step_label` consumer: none exists.

## Receipt inaccuracies corrected

| Claimed | Measured |
|---|---|
| baseline `6 failed, 459 passed` | `5 failed, 462 passed, 15 subtests` at `bdf6690` |
| `standard_equipment` label: 6 hits | 48 (8 sections × 6 models) |
| `cleanup_display_text`: 2,323 strings | 2,248 calls |
| `step_for_section`: 8,500 hits | 10,206 |
| "7 changed source/test files" | 9 |

## Evidence inspected

`git worktree add --detach <tmp> bdf6690`; `scripts/generate_form.py` across six models × two modes
× two trees; the working-tree diff of all nine changed files; `form-app/app.js` for every
`step_label`, `status_label`, `selection_mode_label`, and `disabled_reason` read; every remaining
`.get(x, <literal>)`, `or <literal>`, and `default=` across the thirteen generation-lane modules;
a drop-one-step matrix over all 14 steps for a promoted and an unpromoted model; direct workbook
counts for `section_presentation.step_key`, `*_ovs.status`, `rule_mapping.disabled_reason`, and
`model_interior_scope.trim_level`.

## Validation Output Inspected

`fable5loop/runs/2026-07-25-pass2-shadow-authority-purge/validation-output.txt` was re-executed
rather than accepted. The full Python suite and all 16 node gates were re-run in both trees; the
baseline figures in the receipt did not match measurement and were corrected. The receipt's own
disclosure that the grand-sport gates rewrite tracked artifacts with `generated_at`-only deltas was
confirmed, and the restoration verified by SHA-256. Workbook SHA `8858cff4…` unchanged in both trees.

## Required Fixes Before Pass

1. Repair the step-completeness check so it is not weaker than the Python list it replaced, for
   promoted and unpromoted models alike — and cover the full drop-one-step matrix in the test.
2. Inventory the four missed live shadows, and state the disposition of `sec_stan_002` and
   `opt_z25_001` explicitly.
3. Correct the baseline test counts and the four misstated measurements.

## Durable Lesson Candidates

- A deletion receipt proved by byte-identity cannot detect a weakened *guard*: guards only fire on
  inputs the happy path never produces. Every removed check needs its own drop-one/break-one matrix
  against the thing it used to catch.
- When a test is written after the implementation and passes by supplying the one input the new code
  can still see, it documents the implementation, not the requirement. Derive the fixture from the
  requirement's full input space instead.
- "The values are workbook-authored" is not the same claim as "the display strings are
  workbook-authored." A lookup keyed on workbook data can still ship Python copy. Check which side
  of the mapping reaches the customer.

## File Edit Statement

The verifier edited no tracked file. All generation ran under isolated `--output-root`s in the
session scratchpad. The `git worktree` was removed and artifacts dirtied by the node gates were
restored with `git checkout --`, confirmed by SHA-256.

## Disposition

### Cycle 2

Cycle 2 confirmed the single-drop repair independently — **84 of 84 cases across all six models**,
where the maker had only tested two — and then broke the fix five more ways:

1. **The cross-model rule was an intersection**, defeated by dropping the same step from two models,
   or by setting `active=False` on a single peer row. `summary` is the only step with no
   model-scoped workbook reference, so it was the only key exposed — the configurator's final step,
   silently dropped from a shipped contract. Fixed by switching to a union. The remaining
   drop-from-all-six case is now disclosed as a known limit rather than framed as intended.
2. **The new test could not catch a re-narrowing.** Cycle 2 simulated a future change reducing the
   check to peer comparison alone and re-ran every case: all still passed. Fixed by extending to all
   six models, asserting on the completeness message, and adding a case that strips a step from every
   model so only `step_order_summary_map` can catch it.
3. **`UNAUTHORED_BUCKET_STEP_LABELS` conflated two questions.** Adding `{"paint": "Paint"}` to supply
   a label also exempted `paint` from the completeness guard — demonstrated, not theorized. Split
   into `BUCKET_STEP_KEYS` and the label map.
4. **A new non-fail-closed default was introduced while fixing.** `clean(row.get("step_label")) or
   step_key` shipped the raw snake_case key as a customer-visible label, contradicting the module's
   own docstring. Now raises.
5. **The corrected figures were wrong again**: `6 failed, 464 passed` should be `5 failed, 467
   passed` — the sixth failure was this receipt's own incompleteness.

It also verified every one of the four missed-shadow counts exactly, and all five cycle-1 figure
corrections. It independently reproduced the maker's original `step_for_section` undercount, getting
8,500 before noticing `production.py` imports the function under an alias — the same mistake, found
the same way.

## Disposition

| Finding | Action |
|---|---|
| Cycle 1 — step-completeness regression | Fixed with three workbook-scoped sources plus cross-model consistency; 14/14 for both promoted and unpromoted, locked by a 30-subtest drop-one matrix |
| 4 missed live shadows | Added to the inventory in `validation-output.txt` with measured hit counts; all need workbook columns and therefore user approval |
| `sec_stan_002` / `opt_z25_001` undisposed | Now stated explicitly, with why each is kept |
| 5 misstated figures | Corrected |
| Cycle 2 — intersection defeated | Switched to a union; drop-from-two and deactivate-one-peer now fail; drop-from-all-six disclosed as a known limit |
| Cycle 2 — test could not catch re-narrowing | All six models (84 subtests), `assertRaisesRegex`, plus a case pinning the workbook-scoped sheets independently |
| Cycle 2 — label/exemption conflation | Split into `BUCKET_STEP_KEYS` and `UNAUTHORED_BUCKET_STEP_LABELS` |
| Cycle 2 — blank `step_label` fallback | Now raises |
| Cycle 2 — figures wrong again | Corrected to 5 failed / 467 passed |
