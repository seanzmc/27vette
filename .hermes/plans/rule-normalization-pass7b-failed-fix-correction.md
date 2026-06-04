# Rule Normalization Pass 7B — Correct Failed Z06 Form Fixes

Status: proposed; do not implement until approved.

## Trigger

Sean reported that several Pass 7 handoff claims are false in browser/runtime behavior:

1. `BCW` should auto-add `D3V` at `$0`; current Pass 7 landed/tests assert the opposite.
2. Z06 `N26` is still showing as a selectable option-step card.
3. Z06 custom stitch RPOs `36S` / `37S` / `38S` are still showing as front-end selectable cards.
4. The package-card price hiding for `PDB` / `PDD` / `PDF` should be reversed.
5. `J56` deactivation on `Z07` selection is still wrong.
6. Interior colors are still grouped wrong.

This is a correction pass for failed Pass 7 work, not a broad new normalization phase.

## Constraints

- Workbook remains source of truth for Z06 product rules whenever existing sheets can represent the behavior.
- Do not add Z06-specific JavaScript product exceptions unless generic runtime data evaluation is demonstrably wrong.
- Preserve normalized pathways from Passes 1–6:
  - direct `includes` rows for package/auto-add behavior;
  - `included_zero` price rules for included target prices;
  - exclusive groups for peer replacement/deactivation;
  - workbook-owned interior/component metadata rather than front-end-only hiding.
- Generated artifacts are outputs: do not hand-edit `form-output/*`, `form-app/data.js`, or generated workbook `form_*` sheets.
- Use TDD-first: create/update RED tests that currently fail for these exact user-reported behaviors before workbook/runtime edits.
- No dealer submission endpoint/payload changes.

## Evidence from current files

Read:

- `AGENTS.md`
- `codex-context.md`
- `form-output/inspection/z06-form-data-draft.json`
- existing Z06 tests, especially `tests/z06-performance-package-interactions.test.mjs` and `tests/z06-form-data-draft.test.mjs`

Current generated Z06 draft evidence:

### `BCW` / `D3V`

- `BCW` (`opt_bcw_001`) is active/selectable, direct price `995`.
- `D3V` (`opt_d3v_001`) is active/selectable, direct price `195`.
- `BCW.source_detail_raw` says `Includes (D3V) engine lighting.`
- `D3V.source_detail_raw` says it is included with `B6P` or `BCW`.
- Active generated include exists for `B6P -> D3V`.
- No active generated include exists for `BCW -> D3V`.
- Price rule exists for `B6P -> D3V = 0`.
- No price rule exists for `BCW -> D3V = 0`.
- Current test `Z06 selecting BCW alone does not auto-add or zero D3V` asserts the opposite of the desired behavior and must be replaced.

Canonical owner:

- `z06_rule_mapping`: add/activate `BCW -> D3V` direct `includes`, `auto_add=True`.
- `z06_price_rules`: add/activate `BCW -> D3V = 0`, `price_semantic=included_zero`.

RED test target:

- Selecting `BCW` auto-adds locked `D3V`.
- `D3V` line/display price is `$0` while sourced by `BCW`.
- Removing `BCW` removes/restores `D3V` unless another active source such as `B6P` still includes it.
- `B6P -> D3V = 0` still works.

### `N26`

Current generated draft has six `N26` choice rows with:

- `active=True`
- `selectable=True`
- `display_behavior=hidden`
- `section_id=sec_inte_001`
- `base_price=695`

This means Pass 7 only set a display hint, but the generated choice contract still exposes `N26` as selectable. If the runtime does not universally suppress `display_behavior=hidden` option cards, the browser can still surface it.

Canonical owner:

- Prefer source workbook row semantics: `z06_options.selectable=False` or equivalent source setting must generate non-selectable/non-option-step behavior.
- Preserve `N26` as an interior component/add-on in `interior_components` so applicable interiors still auto-add it and price correctly.
- If `selectable=False` currently fails to suppress active option-step cards, treat that as a generator/runtime source-contract bug and fix generically.

RED test target:

- Generated Z06 option choices for `N26` must not be customer-selectable option-step cards.
- Browser/runtime option sections must not render a selectable `N26` card.
- Selecting applicable interiors still yields `N26` in selected/auto-added/build output through component metadata.

### Custom stitch `36S` / `37S` / `38S`

Current generated draft has six choice rows each for `36S`, `37S`, and `38S` with:

- `active=True`
- `selectable=True`
- `display_behavior=hidden`
- `section_id=sec_cust_002`
- `base_price=495`

As with `N26`, Pass 7 left generated choices selectable and relied on a hidden display hint that failed in the browser.

Canonical owner:

- Remove/hide standalone option-step choice presentation for `36S` / `37S` / `38S` through source `z06_options` selectability/display behavior and/or generic generated-choice filtering.
- Preserve stitch choices as interior variants/components where needed for order/build/dealer evidence.

RED test target:

- No selectable front-end option cards for `36S`, `37S`, or `38S`.
- Interior rows/selected interior output can still carry stitch RPO evidence where the workbook says the interior variant includes it.

### `PDB` / `PDD` / `PDF` package pricing

Latest user correction says to reverse the Pass 7 change that made package cards price-less.

Current generated draft still contains direct package base prices:

- `PDB`: `16000`
- `PDD`: `25495`
- `PDF`: `26495`

Pass 7 runtime code changed presentation to hide package-card display prices and show wheel deltas when packages are selected. That runtime presentation must be reverted or narrowed according to the latest direction.

Assumption for approval: restore package cards to direct price display and remove the package-selected wheel-delta presentation/copy introduced in Pass 7. Keep the underlying workbook package/component price rules intact unless a later pricing pass changes the business model.

Canonical owner:

- Runtime display behavior, because source data already carries package base prices.
- Remove/adjust only the generic Pass 7 display override; do not alter package source prices just to change card display.

RED test target:

- Package cards `PDB` / `PDD` / `PDF` render their direct package prices again.
- Wheel cards do not become the primary package-price display surface solely because a package is selected.
- Order line pricing remains internally consistent with workbook price rules.

### `J56` / `Z07`

Current generated draft:

- `J56` is active/selectable/default_selected in `sec_perf_brake_001`.
- `J57` is active/selectable, direct price `9000`, and source text says it is included with `Z07` or `PDB`.
- `Z07 -> J57 = 0` price rule exists.
- `Z07 -> T0F` include exists.
- There are active replacement/exclusive interactions involving `J57` and default calipers.

The reported failure is that `J56` deactivation on `Z07` selection is still wrong. The intended state from prior Z06 rule corrections is:

- `Z07` should be selectable first.
- Selecting `Z07` auto-adds non-removable `J57` at `$0`.
- `J56` should not remain the active selected brake while `Z07` is selected.
- The UI should communicate that `Z07` includes `J57`, not leave `J56` in a misleading selected/deactivated state.

Canonical owner:

- `z06_rule_mapping`: `Z07 -> J57` include must be active and correctly generated.
- `z06_exclusive_groups` / members: `J56` and `J57` must be brake peers so included `J57` replaces default `J56` generically.
- Runtime: if generated source is correct but selected/default replay re-adds `J56`, fix generic included-peer/default reconciliation.

RED test target:

- Reset/default starts with `J56` selected when appropriate.
- Selecting `Z07` results in selected/auto-added `J57`, not selected `J56`.
- `J57` price is `$0` under `Z07`.
- Removing `Z07` restores the appropriate default brake if no other source still includes `J57`.

### Interior grouping

Current generated draft shows Z06 interiors now have coded `interior_color_family` values such as:

- `HTA Jet Black`
- `HTJ Jet Black`
- `H1Y Jet Black`
- `HTM Jet Black`
- `HTP Jet Black`

But `interior_parent_group_label` is still `None` in generated interior rows, and browser grouping is still reported wrong. This suggests Pass 7 only improved one field while leaving the group hierarchy incomplete or not matching the Stingray/Grand Sport runtime grouping contract.

Canonical owner:

- Existing workbook interior source path: `LZ_Interiors`, `model_interior_scope`, and any existing hierarchy/display-order metadata used by Stingray/Grand Sport.
- Generator should emit complete hierarchy fields, not rely only on string fallback.

RED test target:

- Compare representative Z06 interiors against the proven Stingray/Grand Sport grouping pattern:
  - seat parent groups should be meaningful and stable;
  - color families should not collapse incompatible interiors;
  - custom stitch/suede variants should appear under correct interior choices or component/variant structures, not as confusing standalone option cards.
- Browser/runtime should render the same hierarchy intended by generated data.

## Exact files/sheets likely to change after approval

Workbook source sheets:

- `z06_options`
- `z06_rule_mapping`
- `z06_price_rules`
- `z06_exclusive_groups`
- `z06_exclusive_members`
- `LZ_Interiors`
- `model_interior_scope`
- `interior_components`

Runtime/generator if source contract is currently ignored:

- `form-app/app.js`
- `scripts/corvette_form_generator/inspection.py`
- potentially shared generator helpers that decide whether `selectable=False` / `display_behavior=hidden` rows emit as option-step choices

Tests:

- `tests/z06-performance-package-interactions.test.mjs`
- `tests/z06-form-data-draft.test.mjs`
- `tests/z06-runtime-rule-corrections.test.mjs`
- possibly one browser-style DOM/runtime regression in the existing Z06 test suite

Generated outputs after workbook/generator changes:

- `form-output/inspection/z06-form-data-draft.json`
- `form-output/inspection/z06-*` related inspection artifacts
- `form-app/data.js` only after approved promotion/regeneration path

## Validation plan

1. Add RED tests for all six failed behaviors and confirm they fail before source edits.
2. Apply workbook-owned source corrections with safe-save:
   - require Excel closed and no `~$stingray_master.xlsx` lock file;
   - back up workbook;
   - save via `save_workbook_safely()`;
   - reopen and verify exact rows.
3. Regenerate Z06 artifacts and production app data as required by approved scope.
4. Run workbook validators:
   - `.venv/bin/python scripts/validate_workbook_schema.py`
   - `.venv/bin/python scripts/validate_workbook_package.py`
5. Run focused Z06 tests.
6. Run multi-model runtime regression to ensure generic include/default changes do not break Stingray or Grand Sport.
7. Browser smoke the exact user paths:
   - `BCW -> D3V $0`
   - no standalone selectable `N26`
   - no standalone selectable `36S`/`37S`/`38S`
   - package cards show restored prices per latest correction
   - `Z07 -> J57 $0` replaces/hides/deactivates `J56` correctly
   - interior group hierarchy matches desired model pattern

## Risks

- The current tests passed while browser behavior failed, so tests must be rewritten around real runtime/DOM behavior, not just generated-field assertions.
- `display_behavior=hidden` currently appears insufficient because generated choices remain `selectable=True`.
- Reversing package price display may conflict with the previous Pass 7 memory/spec; latest user correction wins.
- Interior grouping needs a concrete target hierarchy from Stingray/Grand Sport comparison, not another heuristic-only change.

## Non-goals

- No broad ZR1/ZR1X migration work.
- No dealer submission changes.
- No new review taxonomy or parallel workbook sheets.
- No hardcoded Z06 RPO branches in runtime unless a generic source-contract bug is impossible to fix safely.

## Approval request

Approve this Pass 7B correction and I will implement it TDD-first: flip/add RED tests for the exact failed behaviors, make workbook-owned corrections first, only touch generator/runtime where source metadata is currently ignored, regenerate, run gates, and browser-smoke the reported paths.
