# Cross-Model Ordering Pass Spec

Recommended reasoning level: high.

## Status

Approved and implemented 2026-06-17.

Implementation evidence:

- `z06_options.opt_som_001.display_order` changed from `30` to `23`, and `z06_options.opt_rox_001.display_order` changed from `23` to `30`.
- `grandSport_exclusive_members.gs_excl_ls6_engine_covers` now orders members as BC7/BCP/BCS/BC4 at display orders 10/20/30/40.
- The roof ordering item was resolved as a characterization guard, not a workbook edit: active shared roof RPO order is consistent across promoted models, and `CF8` is currently active only for Grand Sport.
- Grand Sport and Z06 artifacts plus `form-app/data.js` were regenerated; the order-aware allowlist probe confirmed only the approved order drift.
- `tests/grand-sport-draft-data.test.mjs`, `tests/z06-form-data-draft.test.mjs`, and `tests/multi-model-runtime-switching.test.mjs` now lock the affected order surfaces.

## Preflight Findings

Current branch/status at spec time:

- Branch: `generator-simplification-pass1`
- Working tree: clean before this spec was written.
- Root `codex-context.md`: not present; `AGENTS.md` remains the active repo guide loaded in context.

Current source evidence inspected:

- `docs/persisting-audit-findings-2026-06-14.md` section 7 lists the next ordering item: shared wheel/roof ordering drift and Grand Sport LS6 exclusive-member order drift.
- `docs/workbook-consistency-review-2026-06-11.md` D-4/D-5/D-6/D-8 describe the older ordering findings and recommend aligning shared-option relative order with scoped tests.
- `stingray_master.xlsx` was inspected read-only with `openpyxl`.
- `tests/grand-sport-draft-data.test.mjs` currently pins Grand Sport wheel order and `gs_excl_ls6_engine_covers` member order.
- `tests/multi-model-runtime-switching.test.mjs` also pins `gs_excl_ls6_engine_covers` member order in the promoted registry contract.

Current workbook facts:

### Shared wheels in `sec_whee_002`

Grand Sport currently emits the shared forged/carbon-wheel subset in this relative order:

| Sheet | RPO | option_id | display_order |
|---|---:|---|---:|
| `grandSport_options` | ROU | `opt_rou_001` | 41 |
| `grandSport_options` | SON | `opt_son_001` | 42 |
| `grandSport_options` | SOM | `opt_som_001` | 43 |
| `grandSport_options` | ROX | `opt_rox_001` | 44 |
| `grandSport_options` | ROY | `opt_roy_001` | 50 |
| `grandSport_options` | ROZ | `opt_roz_001` | 60 |
| `grandSport_options` | STZ | `opt_stz_001` | 70 |

Z06 currently emits the same shared subset with ROX/SOM swapped relative to Grand Sport:

| Sheet | RPO | option_id | display_order |
|---|---:|---|---:|
| `z06_options` | ROU | `opt_rou_001` | 12 |
| `z06_options` | SON | `opt_son_001` | 22 |
| `z06_options` | ROX | `opt_rox_001` | 23 |
| `z06_options` | SOM | `opt_som_001` | 30 |
| `z06_options` | ROY | `opt_roy_001` | 40 |
| `z06_options` | ROZ | `opt_roz_001` | 41 |
| `z06_options` | STZ | `opt_stz_001` | 42 |

### Roof options in `sec_roof_001`

The older roof finding is now partly stale when limited to active emitted rows:

- `stingray_options.opt_cf8_001` exists at `display_order=13` but is `active=False`, so it does not participate in active runtime order.
- `z06_options.opt_cf8_001` exists at `display_order=50` but is `active=False`, so it does not participate in active runtime order.
- `grandSport_options.opt_cf8_001` is active at `display_order=50`; it is currently Grand Sport-only among active promoted model rows.
- Active shared roof RPO relative order is already consistent across promoted models for the overlapping active set: `CF7`, `C2Z`, `CC3`, `CM9`, `D84`, `D86`.
- Numeric gaps differ (`D84`/`D86` are 21/22 in Stingray and 60/70 in Grand Sport/Z06), but relative customer-facing order is the same.

Therefore, this pass should not change roof workbook rows unless implementation preflight finds newer evidence that active emitted roof ordering actually differs. It should resolve the stale roof finding by adding/keeping a targeted relative-order assertion and updating docs after implementation.

### Grand Sport LS6 engine-cover exclusive member order

Grand Sport option-sheet order is already aligned with Stingray for LS6 engine covers:

| Sheet | RPO | option_id | display_order |
|---|---:|---|---:|
| `grandSport_options` | BC7 | `opt_bc7_001` | 19 |
| `grandSport_options` | BCP | `opt_bcp_002` | 20 |
| `grandSport_options` | BCS | `opt_bcs_002` | 30 |
| `grandSport_options` | BC4 | `opt_bc4_002` | 40 |

But `grandSport_exclusive_members.gs_excl_ls6_engine_covers` still uses stale member order:

| Sheet | group_id | option_id | display_order |
|---|---|---|---:|
| `grandSport_exclusive_members` | `gs_excl_ls6_engine_covers` | `opt_bc7_001` | 10 |
| `grandSport_exclusive_members` | `gs_excl_ls6_engine_covers` | `opt_bc4_002` | 30 |
| `grandSport_exclusive_members` | `gs_excl_ls6_engine_covers` | `opt_bcp_002` | 50 |
| `grandSport_exclusive_members` | `gs_excl_ls6_engine_covers` | `opt_bcs_002` | 70 |

## Diagnosis

Root cause:

- Some ordering drift is real source-data drift: Z06 and Grand Sport disagree on the shared `SOM`/`ROX` wheel relative order.
- One ordering drift is stale metadata drift: `grandSport_exclusive_members.gs_excl_ls6_engine_covers` no longer matches the source option-sheet order after the Grand Sport engine-cover rows were normalized.
- The older roof finding is no longer an active emitted-order defect because `CF8` is active only for Grand Sport among promoted runtime rows; the remaining active shared roof choices already preserve relative order.

Risk level: medium.

Change type: workbook/data + generated artifacts + tests/docs. No runtime JavaScript behavior or styling change intended.

## Ownership Decision

Ordering is workbook-owned source data:

- Wheel and engine-cover display/member order belong in source sheets, not runtime JavaScript.
- Generated `form_*` sheets, `form-output/*`, and `form-app/data.js` are outputs and must be regenerated, not hand-edited.
- Runtime JavaScript should continue to render generated order data generically.

## Recommended Scope

### Implement now

1. Align Z06 shared wheel relative order with Grand Sport for the shared forged/carbon-wheel subset.

   Recommended canonical shared order:

   ```text
   ROU -> SON -> SOM -> ROX -> ROY -> ROZ -> STZ
   ```

   Minimal workbook edit:

   | Sheet | option_id | RPO | current display_order | target display_order |
   |---|---|---:|---:|---:|
   | `z06_options` | `opt_som_001` | SOM | 30 | 23 |
   | `z06_options` | `opt_rox_001` | ROX | 23 | 30 |

   Rationale: Grand Sport already has the shared ROU/SON/SOM/ROX sequence pinned in `tests/grand-sport-draft-data.test.mjs`; this is the only currently confirmed GS-vs-Z06 sibling wheel-order drift. The change is order-only and preserves unique Z06 display orders.

2. Align Grand Sport LS6 exclusive-member order with Grand Sport option-sheet order.

   Minimal workbook edit:

   | Sheet | group_id | option_id | current display_order | target display_order |
   |---|---|---|---:|---:|
   | `grandSport_exclusive_members` | `gs_excl_ls6_engine_covers` | `opt_bc7_001` | 10 | 10 |
   | `grandSport_exclusive_members` | `gs_excl_ls6_engine_covers` | `opt_bcp_002` | 50 | 20 |
   | `grandSport_exclusive_members` | `gs_excl_ls6_engine_covers` | `opt_bcs_002` | 70 | 30 |
   | `grandSport_exclusive_members` | `gs_excl_ls6_engine_covers` | `opt_bc4_002` | 30 | 40 |

   Intended generated `option_ids` order:

   ```text
   opt_bc7_001 -> opt_bcp_002 -> opt_bcs_002 -> opt_bc4_002
   ```

3. Resolve the roof-order audit item as verification-only unless implementation preflight contradicts current evidence.

   - Do not edit `stingray_options`, `grandSport_options`, or `z06_options` roof rows in this pass by default.
   - Add or update a targeted test/probe proving active shared roof RPO relative order is consistent across promoted models for the current overlapping active set.
   - If implementation preflight finds `CF8` active in multiple promoted models or another active roof relative-order mismatch, stop and revise this spec before workbook edits.

4. Add/extend tests.

   Required test coverage:

   - `tests/grand-sport-draft-data.test.mjs`
     - Update `expectedGrandSportExclusiveGroups.gs_excl_ls6_engine_covers.option_ids` to `opt_bc7_001`, `opt_bcp_002`, `opt_bcs_002`, `opt_bc4_002`.
     - Keep the existing Grand Sport wheel order assertion unchanged unless the implementation intentionally changes Grand Sport wheels.
   - `tests/multi-model-runtime-switching.test.mjs`
     - Update `expectedGrandSportExclusiveGroups.gs_excl_ls6_engine_covers.optionIds` to the same member order.
     - Add or update a scoped runtime/registry assertion for the shared wheel subset order across Grand Sport and Z06.
     - Add or update a scoped active-roof relative-order assertion so the stale CF8/CM9 audit item does not reappear without active emitted evidence.
   - `tests/z06-form-data-draft.test.mjs`
     - Add a Z06 wheel-order assertion for the shared subset showing `ROU`, `SON`, `SOM`, `ROX`, `ROY`, `ROZ`, `STZ` in that relative order while preserving Z06-specific wheel rows around them.

5. Regenerate affected artifacts.

   Run:

   ```sh
   .venv/bin/python scripts/generate_form.py --model grand_sport
   .venv/bin/python scripts/generate_form.py --model z06
   .venv/bin/python scripts/generate_registry.py
   ```

6. Update docs after implementation.

   - Mark this spec approved/implemented.
   - Update `docs/persisting-audit-findings-2026-06-14.md` section 7 and the recommended next-pass list.
   - Keep the roof note explicit: resolved by current active-row verification, not by a roof workbook edit, unless implementation discovers a real active roof drift.

### Explicitly defer

- Cross-model customer copy convergence.
- Product-review section/copy decisions such as HUD/roof pouch/DRZ/accent copy.
- Z06 option-id suffix/no-RPO row cleanup.
- Future-model scaffold ordering for ZR1/ZR1X.
- Runtime refactors or product/RPO-specific JavaScript.
- Broad all-model order equality across every shared RPO; this pass only targets confirmed shared-section surfaces.

## Exact Files and Sheets to Change

Workbook source sheets:

- `stingray_master.xlsx`
  - `z06_options`
  - `grandSport_exclusive_members`

Generated artifacts after regeneration:

- `form-output/inspection/grand-sport-runtime-contract.json`
- `form-output/inspection/grand-sport-form-data-draft.json`
- `form-output/inspection/z06-runtime-contract.json`
- `form-output/inspection/z06-form-data-draft.json`
- `form-app/data.js`
- generated workbook `form_*` sheets as emitted by the affected model generation runs

Tests:

- `tests/grand-sport-draft-data.test.mjs`
- `tests/z06-form-data-draft.test.mjs`
- `tests/multi-model-runtime-switching.test.mjs`

Docs:

- `docs/cross-model-ordering-pass-spec.md`
- `docs/persisting-audit-findings-2026-06-14.md`

No expected source-code changes outside tests/docs unless implementation exposes a generator bug in ordering emission.

## Constraints

- Preserve live customer/dealer behavior except intentional display/member order changes.
- No runtime JavaScript product/RPO-specific exception.
- No new dependencies.
- No visual/CSS/layout change.
- No dealer endpoint, Turnstile, payload shape, or submission semantics change.
- No workbook schema expansion.
- No hand edits to generated `form_*` sheets, `form-output/*`, or `form-app/data.js`; regenerate them.
- Close Excel before workbook writes. If `~$stingray_master.xlsx` exists, stop and verify lock/staleness before writing.
- Save workbook changes through `save_workbook_safely()` and verify saved rows on disk before claiming the workbook landed.
- Preserve all prices, labels, descriptions, active/selectable flags, option placement, rule semantics, and default-selection behavior.
- Respect pre-existing dirty work; inspect overlapping diffs before editing.

## Required Preflight Before Editing

1. Confirm branch/status and Excel lock:

```sh
git status --short --branch
.venv/bin/python scripts/validate_workbook_package.py stingray_master.xlsx
```

Also confirm no Excel lock file exists using Python/pathlib or shell-safe quoting.

2. Snapshot generated contracts before regeneration:

```sh
cp form-output/inspection/grand-sport-runtime-contract.json /tmp/before-grand-sport-runtime-contract.json
cp form-output/inspection/grand-sport-form-data-draft.json /tmp/before-grand-sport-form-data-draft.json
cp form-output/inspection/z06-runtime-contract.json /tmp/before-z06-runtime-contract.json
cp form-output/inspection/z06-form-data-draft.json /tmp/before-z06-form-data-draft.json
cp form-app/data.js /tmp/before-cross-model-ordering-data.js
```

3. Re-probe workbook rows before writing:

- `z06_options` rows for `opt_rox_001`, `opt_som_001`, and nearby `sec_whee_002` rows.
- `grandSport_exclusive_members.gs_excl_ls6_engine_covers` rows.
- Active `sec_roof_001` rows in `stingray_options`, `grandSport_options`, and `z06_options`.

4. Stop and revise this spec if:

- `z06_options.opt_rox_001` or `z06_options.opt_som_001` are no longer active in `sec_whee_002`.
- Either target Z06 display-order value is already occupied by a different active `sec_whee_002` row after preflight.
- Grand Sport LS6 option IDs or option-sheet order differ from the table above.
- `CF8` or another roof option is active across multiple promoted models with a real emitted relative-order mismatch.
- Any implementation requires runtime JS product-specific behavior.

## Implementation Plan

1. Add RED tests and characterization guards first.
   - Update the existing expected Grand Sport LS6 group order in tests to the target order.
   - Add a scoped Z06 wheel-order assertion expecting the shared subset order `ROU`, `SON`, `SOM`, `ROX`, `ROY`, `ROZ`, `STZ`.
   - These two order-change assertions should fail before workbook edits and pass after the workbook source rows are updated.
   - Add a scoped active-roof relative-order assertion that documents no roof workbook edit is currently needed. This is a characterization/guard assertion and should already pass if the preflight evidence is still correct; do not chase it as a RED failure unless the source data contradicts this spec.

2. Write the workbook source edit.
   - Use a temporary or repo-local one-pass Python apply script while developing.
   - Load `stingray_master.xlsx`, modify only `z06_options` and `grandSport_exclusive_members`, and save through `save_workbook_safely()`.
   - Delete the one-pass script after verification if it is not a reusable guarded workflow entrypoint.

3. Verify workbook on disk.
   - Reopen with `openpyxl` read-only.
   - Confirm `z06_options.opt_som_001.display_order=23` and `z06_options.opt_rox_001.display_order=30`.
   - Confirm `grandSport_exclusive_members.gs_excl_ls6_engine_covers` order is BC7/BCP/BCS/BC4 at 10/20/30/40.
   - Confirm no active `(source option sheet, section_id, display_order)` collisions were introduced.

4. Regenerate and compare.
   - Regenerate Grand Sport, Z06, then registry.
   - Review before/after generated contracts with an order-aware allowlist probe. Do not use `scripts/compare-generated-contracts.mjs` as a pass/fail gate for the changed Grand Sport/Z06 contracts because that helper intentionally asserts full equality apart from timestamp keys and should fail when this pass succeeds.
   - Allowed generated drift:
     - Grand Sport LS6 exclusive group `option_ids` order changes to BC7/BCP/BCS/BC4.
     - Z06 wheel choices for `SOM` and `ROX` swap display-order values/order.
     - `form-app/data.js` reflects the same promoted generated data update.
     - Generated timestamps.
   - No choices added/removed, no prices changed, no interiors changed, no standard equipment changed, no rule semantics changed, no dealer payload fields changed, and no Stingray model contract changed.

5. Update docs and run gates.

## Validation Plan

Targeted gates:

```sh
.venv/bin/python scripts/generate_form.py --model grand_sport
.venv/bin/python scripts/generate_form.py --model z06
.venv/bin/python scripts/generate_registry.py
.venv/bin/python scripts/validate_workbook_schema.py stingray_master.xlsx
# Run the order-aware generated contract probe described below; do not use compare-generated-contracts.mjs as the green gate for this intentional order-changing pass.
node --test tests/grand-sport-draft-data.test.mjs
node --test tests/z06-form-data-draft.test.mjs
node --test tests/multi-model-runtime-switching.test.mjs
git diff --check
```

Order-aware generated contract gate:

- Run a small Node probe against the `/tmp/before-*` snapshots and regenerated JSON contracts.
- The probe must fail unless the only non-timestamp payload drift is:
  - Grand Sport `gs_excl_ls6_engine_covers.option_ids` order changing from `BC7, BC4, BCP, BCS` to `BC7, BCP, BCS, BC4`.
  - Z06 wheel choices `SOM` and `ROX` swapping display-order values/order.
  - Generated validation/order messages that directly reflect those two order-only changes.
- `scripts/compare-generated-contracts.mjs` may be run manually as a diagnostic to inspect the expected diff, but it is not a green gate for this pass because it asserts deep equality after ignoring only timestamp keys.

Because `generate_registry.py` updates promoted `form-app/data.js`, run the multi-model runtime test even though runtime JS is not expected to change.

If generated diffs show unexpected non-order drift, also run:

```sh
node --test tests/grand-sport-contract-preview.test.mjs
node --test tests/z06-contract-preview.test.mjs
node --test tests/z06-performance-package-interactions.test.mjs
```

Manual/browser verification:

- Browser-smoke only if generated diff or tests show a customer-facing ordering issue not covered by static/runtime tests.
- If run, verify:
  - Grand Sport Engine Appearance LS6 engine-cover tiles display in BC7/BCP/BCS/BC4 radio order and still replace peers.
  - Z06 Wheels displays the shared forged/carbon wheel subset with SOM before ROX and no disabled-state regressions for wheel packages.
  - Build summary/dealer payload still contain selected RPOs normally; order-only change should not alter payload shape.

## Risks

- The Z06 wheel order may have been intentionally grouped by Z06-specific wheel family/finish. This spec recommends Grand Sport as the canonical shared-subset order; approval should be read as approval of that product/visual decision for `SOM` before `ROX`.
- Changing display order affects customer-facing card order and generated contract order, even though it should not affect option availability or pricing.
- Grand Sport LS6 exclusive-member order is runtime-visible through generated exclusive-group ordering; tests must prove replacement behavior still works after member-order change.
- Generated artifact churn can mask unrelated changes; snapshot and compare before regeneration.
- Workbook writes are risky if Excel is open; do not bypass lock-file safety.

## Non-Goals

- No broad shared-option order normalization outside the named wheel/LS6 surfaces.
- No roof row edits unless preflight disproves the current active-row finding.
- No copy/name/description normalization.
- No section-placement/product-decision edits.
- No Z06 package/wheel availability logic changes.
- No runtime JS refactor.
- No workbook schema changes.
- No generated artifact hand edits.
- No dealer submission changes.

## Handoff Requirements

The implementation handoff must report:

- What changed: workbook sheets/rows, generated artifacts, tests, docs, and the intentional customer-facing order impact.
- What did not change: runtime JS product logic, visual/CSS layout, dealer boundaries, prices, rules, interiors, standard equipment, and non-target ordering surfaces.
- Gate results: exact commands and pass/fail output.
- Manual verification pending or skipped with reason.
- Next step guidance: likely copy-convergence/product-decision pass unless this implementation exposes a more urgent workbook-order issue.

## Approval Question

Approve this cross-model ordering pass as scoped above?

Recommended answer: `cross-model ordering pass approved.`
