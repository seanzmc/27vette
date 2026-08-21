# Checkpoint 3 measured evidence — fast layered validation suite

Evidence file for `docs/archive/completed-specs/fast-layered-validation/2026-08-17-fast-layered-validation-suite.md` §9,
Checkpoint 3. Raw tool output from the closing acceptance run, captured 2026-08-18.

Environment: darwin arm64; node v26.7.0; python 3.14.7 (`.venv`).
Method: the new matrix gate run once from a clean worktree against the published
registry. Catalog and loop validators run after the catalog/handoff edits.

## 1. Runtime state matrix

```text
node --test tests/runtime-state-matrix.test.mjs
✔ the matrix enumerates every promoted model and declared active variant
✔ stingray: every declared variant satisfies the rest-state matrix
✔ stingray: representative transitions preserve generic rule contracts
✔ grandSport: every declared variant satisfies the rest-state matrix
✔ grandSport: representative transitions preserve generic rule contracts
✔ grand_sport_x: every declared variant satisfies the rest-state matrix
✔ grand_sport_x: representative transitions preserve generic rule contracts
✔ z06: every declared variant satisfies the rest-state matrix
✔ z06: representative transitions preserve generic rule contracts
✔ zr1: every declared variant satisfies the rest-state matrix
✔ zr1: representative transitions preserve generic rule contracts
✔ zr1x: every declared variant satisfies the rest-state matrix
✔ zr1x: representative transitions preserve generic rule contracts
✔ model switching clears incompatible prior-model state for every promoted pair
✔ the report names every promoted model and active variant the matrix exercised
✔ forced failure: model activation binds the wrong registry data
✔ forced failure: body/trim resolve to the wrong variant
✔ forced failure: reset plus reconciliation is not a fixed point
✔ forced failure: a second reconciliation is not idempotent
✔ forced failure: a selected option does not exist in context
✔ forced failure: a selected option remains disabled
✔ forced failure: two peers remain selected in a single-selection exclusive group
✔ forced failure: a required selection is neither satisfied nor reported
✔ forced failure: include/default rule contract is dropped
✔ forced failure: order totals disagree with the exposed lines
✔ forced failure: model switch keeps prior-model user state
✔ forced failure: dealer payload identity does not match the active model/variant
ℹ tests 27
ℹ pass 27
ℹ fail 0
ℹ duration_ms 2668.502959
```

Workbook-discovered coverage, measured from the §6.2 snapshot against the
published registry:

| Model | Registry key | Active variants |
|---|---|---|
| stingray | stingray | 6 (`1lt_c07` … `3lt_c67`) |
| grand_sport | grandSport | 6 (`1lt_e07` … `3lt_e67`) |
| grand_sport_x | grand_sport_x | 6 (`1lt_g07` … `3lt_g67`) |
| z06 | z06 | 6 (`1lz_h07` … `3lz_h67`) |
| zr1 | zr1 | 4 (`1lz_r07`, `3lz_r07`, `1lz_r67`, `3lz_r67`) |
| zr1x | zr1x | 4 (`1lz_s07`, `3lz_s07`, `1lz_s67`, `3lz_s67`) |
| **total** | **6** | **32** |

The report assertion requires `seen == variants`. It failed empty until every
rest-state case passed, then passed with the 32-variant list above.

## 2. Forced-failure inventory

Each §4.3 invariant has one injected defect. All twelve fail their own
assertion:

1. bind another model's dataset → model activation
2. change trim without resetting → variant resolution
3. `reconcileSelections` rewrites interior after itself → not a fixed point
4. second `reconcileSelections` rewrites interior → not idempotent
5. select a nonexistent option id → selected options exist
6. `disableReasonForChoice` returns a reason for a selected option → selected-not-disabled
7. force two exclusive-group peers selected → exclusive single selection
8. clear interior and suppress `missingRequired` → required reporting
9. drop a default-selected option → default/rule contract
10. increment `total_msrp` → order totals
11. restore `userSelected` / interior after `activateModel` → model-switch clearance
12. rewrite dealer payload `model` → payload identity

No live dealer request is made in any of these.

## 3. What this checkpoint deliberately did not do

- Did not retire `stingray-form-regression`, `z06-interior-accessory-cleanup`,
  `z06-performance-package-interactions`, `z06-runtime-rule-corrections`, or the
  named product cases in `multi-model-runtime-switching`. Spec Checkpoint 3
  requires equivalent-or-stronger failure detection first; that is Checkpoint 4.
- Did not promote `promoted_model_membership` to an established lock.
- Did not write the workbook or any generated artifact.
- Did not rerun the full twelve-stage candidate lane (about 11 minutes). The
  cheap harness-override test and the matrix itself were run; the lane now
  appends the matrix to `browser_harness`.
