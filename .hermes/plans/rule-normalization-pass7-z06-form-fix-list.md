# Rule Normalization Pass 7 — Z06 Form Fix List

> Status: implemented and verified on 2026-06-04 after Sean approved the spec and clarified package-wheel pricing as delta over package base.

## User fix list

Sean reported these Z06 form issues after rule normalization Pass 6:

1. Interior colors are grouped wrong. Find how they are grouped in the other models and probably make grouping workbook-owned.
2. BCW auto-adds D3V at $0.
3. J56 is deactivated on Z07 selection.
4. PDF keeps T0F selected when it should be deactivated.
5. PDB/PDD/PDF price listing is confusing. Those package cards should not show a price; the carbon-fiber wheels should show the package price because wheel choice determines the package price. Copy in the wheel section needs to update in this scenario.
6. N26 should not ever be selectable in the option steps. Correction from user during inspection: disregard the earlier “auto add only on 1LT AE4 trigger” wording. N26 should auto-add on all applicable interiors and should not be selectable on the front end.
7. Custom stitch needs to go away on the front end.

## Diagnosis

This is a mixed workbook/source-data + generated-data + generic runtime/UI pass. The fixes should stay inside the normalized rule model created by Passes 1–6:

- option visibility/selectability belongs in `z06_options` / `z06_ovs` / variant overrides if needed;
- included/auto-added behavior belongs in `z06_rule_mapping` direct `includes` rows or existing interior component metadata, not in Z06-specific JavaScript;
- mutually exclusive choices belong in `z06_exclusive_groups` / `z06_exclusive_members`;
- package/wheel requirements belong in existing `requires_any` groups plus package default includes, not restored replace swarms;
- price meaning belongs in `z06_price_rules.price_semantic`, with package presentation handled generically from workbook/generated metadata rather than hardcoded RPO branches;
- interior hierarchy should be workbook-owned on the existing interior source path, not inferred only by generator string heuristics.

Risk level: High. Several items affect selected/auto-added state, package pricing display, and interior option rendering in the customer-facing Z06 runtime. This pass must be TDD-first and verified in generated draft data, live promoted app data, and browser/runtime interactions.

Change type: mixed workbook source, generator/runtime rendering as needed, generated artifacts, tests. No dealer-submission changes.

## Evidence inspected

Files/docs:

- `AGENTS.md`
- `codex-context.md`
- `form-app/app.js`
  - `renderInteriorCard()`
  - `renderInteriorGroups()`
  - `groupInteriorsBy()`
  - `adjustedInteriorDisplayPrice()` / `optionPrice()` surfaces still need deeper inspection before implementation.
- `form-output/inspection/z06-form-data-draft.json`
- `form-output/stingray-form-data.json`
- existing tests:
  - `tests/z06-form-data-draft.test.mjs`
  - `tests/z06-performance-package-interactions.test.mjs`
  - `tests/z06-runtime-rule-corrections.test.mjs`
  - `tests/z06-runtime-promotion.test.mjs`
  - `tests/multi-model-runtime-switching.test.mjs`
  - `tests/workbook-schema-standardization.test.mjs`

Workbook sheets inspected:

- `z06_options`
- `z06_rule_mapping`
- `z06_rule_groups`
- `z06_rule_group_members`
- `z06_exclusive_groups`
- `z06_exclusive_members`
- `z06_price_rules`
- `default_selection_rules`
- `LZ_Interiors`
- `model_interior_scope`
- `interior_components`
- `component_price_rules`

Current evidence snapshots:

- Other models’ generated interiors group more specifically:
  - Stingray/Grand Sport 1LT examples use `interior_color_family` values like `HTJ Jet Black`, `HTA Jet Black`, `HUP Sky Cool Gray`, and parent labels like `AQ9 GT1 Bucket Seats` / `AE4 Competition Seats`.
  - Z06 currently groups by plain color family such as `Jet Black`, `Sky Cool Gray`, `Adrenaline Red`, and uses material as parent group label. This causes different grouping behavior than Stingray/Grand Sport.
- `form-app/app.js` currently groups interior cards first by generated `interior_color_family`, then by `interior_material_family`.
- Current `z06_options` rows:
  - `BCW`: active/selectable, `sec_engi_001`, direct price 995.
  - `D3V`: active/selectable, `sec_engi_001`, direct price 195.
  - `N26`: active/selectable, `sec_inte_001`, direct price 695. This contradicts the new user direction that N26 should never be a selectable option-step card.
  - `J56`: active/selectable, `sec_perf_brake_001`, `display_behavior=default_selected`, direct price 0.
  - `J57`: active/selectable, `sec_perf_brake_001`, direct price 9000.
  - `PDB`: active/selectable, `sec_z06_pkg_001`, direct price 16000.
  - `PDD`: active/selectable, `sec_z06_pkg_001`, direct price 25495.
  - `PDF`: active/selectable, `sec_z06_pkg_001`, direct price 26495.
- Current `z06_rule_mapping` relevant rows:
  - `B6P -> D3V` include is active.
  - No `BCW -> D3V` include was found in the inspected rule rows, so the reported “BCW auto-adds D3V” likely needs runtime/browser reproduction and may be caused by section/engine-cover interaction or stale generated state, not the obvious source row. The RED test should reproduce the exact front-end path before changing workbook rows.
  - `Z07 -> J57`, `Z07 -> FE7`, `Z07 -> XFS`, and `Z07 -> T0F` includes are active.
  - `PDD -> T0F`, `PDD -> CFZ`, `PDF -> T0G`, `PDF -> CFV`, `PDF -> Z07`, and package wheel-default includes are active.
  - `PDF -> T0F` and `PDD -> T0G` direct excludes are currently marked omitted/replaced by `z06_excl_aero_packages`, so if PDF leaves T0F selected, the fix should preserve the normalized exclusive-group/include path and adjust generic included-peer reconciliation if workbook data is already correct.
- Current `z06_price_rules` relevant rows:
  - `B6P -> BCW = 895`, `price_semantic=conditional_component_price`.
  - `ZZ3 -> BCW = 895`, `price_semantic=conditional_component_price`.
  - `B6P -> D3V = 0`, `price_semantic=included_zero`.
  - `PDB/PDD/PDF -> included components = 0`, `price_semantic=included_zero`.
  - `ROY/ROZ/STZ -> PDB/PDD/PDF` package prices exist as `price_semantic=package_price_by_component`.
  - Package rows still have direct base prices, causing the package cards to display a price before the carbon-wheel choice communicates the combination price.
- Current generated Z06 choices show package card prices:
  - PDB: 16000
  - PDD: 25495
  - PDF: 26495
  - ROY: 11995
  - ROZ: 13995
  - STZ: 15500
  The requested UX wants package cards price-less and the selected carbon-fiber wheel card to show the relevant package combination price.
- `interior_components` has active Z06 component rows for:
  - N26 suede: 17 rows
  - N2Z suede: 37 rows
  - 36S/37S/38S custom stitch: 13/13/18 rows
  - AE4/AH2 seats
  This supports moving N26/custom-stitch presentation through existing interior component metadata instead of selectable option cards.

## Proposed canonical ownership by issue

### 1. Interior grouping wrong / make grouping workbook-owned

Owner: existing workbook interior source path.

Preferred fix:

- Add explicit hierarchy/display columns to the existing owning interior sheet/path, likely `LZ_Interiors` and/or `model_interior_scope`, after confirming which generator loader emits hierarchy fields.
- Do not create a parallel `z06_interior_grouping` sheet unless implementation proves neither existing sheet can carry the hierarchy safely.
- Target generated fields should remain the runtime contract:
  - `interior_color_family`
  - `interior_material_family`
  - `interior_parent_group_label`
  - `interior_leaf_label`
  - `interior_group_display_order`
  - `interior_material_display_order`
  - `interior_choice_display_order`
  - `interior_hierarchy_path`
- Make Z06 grouping match the superior Stingray/Grand Sport pattern where appropriate: seat parent groups and coded color families such as `HTJ Jet Black` vs plain `Jet Black`, while preserving Z06/LZ naming where customer-facing labels differ.

RED test:

- Add a generated-data test that compares representative Z06 interiors to the model-owned grouping contract:
  - 1LZ AQ9 and AE4 Jet Black should not collapse into one ambiguous plain `Jet Black` group when seat/color-code separation is required.
  - Z06 grouping should use workbook-authored hierarchy fields, not generator-only string fallback.

### 2. BCW auto-adds D3V at $0

Owner: first reproduce in runtime; likely `z06_rule_mapping` and/or generic runtime include logic.

Current source evidence does not show `BCW -> D3V`; it shows `B6P -> D3V` and `B6P -> BCW` price override. Therefore implementation must first reproduce the exact path.

Preferred fix after RED:

- If selecting BCW auto-adds D3V because a bad workbook include exists elsewhere, retire that source row with lifecycle metadata and replacement reason.
- If runtime is applying a transitive or reverse include incorrectly, fix the generic runtime include evaluation, not a Z06/RPO exception.
- Preserve `B6P -> D3V` included-zero behavior unless the reproduced bug proves it is the wrong source.

RED test:

- In `tests/z06-runtime-rule-corrections.test.mjs` or a new focused Z06 browser/runtime test, select BCW alone and assert D3V is not auto-added and no D3V $0 line appears solely from BCW.
- Select B6P and assert D3V still auto-adds/zeroes if that remains intended.

### 3. J56 deactivated on Z07 selection

Owner: `z06_exclusive_groups`, `z06_rule_mapping`, generic include/exclusive behavior.

Current source has:

- `z06_excl_performance_brakes`: `required_single_within_group`, members J56 and J57.
- `Z07 -> J57` include.
- `Z07 -> J57 = 0` price rule.

User wording says J56 is deactivated on Z07 selection. This needs precise RED behavior:

- If selecting Z07 should include/lock J57 and replace the J56 default, J56 being unavailable while Z07 is selected may be correct.
- If the problem is that J56 remains visually selected/deactivated incorrectly, or the UI message/disable state is confusing, fix the generic included-peer replacement/visual state.

Proposed interpretation for implementation unless user amends:

- Z07 should auto-add non-removable J57 at $0 and remove the J56 default from selected state.
- The UI should not show J56 as the active selected brake while Z07 is selected.
- If the card is visible, it should be clear that Z07 includes J57 rather than presenting J56 as a broken/deactivated selected item.

RED test:

- Select Z07 and assert selected/auto-added state contains J57 and does not contain selected J56.
- Assert J56 is not represented as the active selected brake after Z07; if disabled messaging is under test, assert the reason is generic and accurate.

### 4. PDF keeps T0F selected when it should be deactivated

Owner: `z06_rule_mapping`, `z06_exclusive_groups`, generic included-peer reconciliation.

Current normalized workbook data already says:

- `PDF -> T0G` include active.
- `PDF -> CFV` include active.
- `PDF -> T0F` direct exclude retired into `z06_excl_aero_packages`.
- `T0F`, `T0G`, `T0E`, `5ZV` are active peers in `z06_excl_aero_packages`.

Preferred fix:

- Keep the retired direct `PDF -> T0F` row retired.
- Do not restore a direct replace swarm.
- If selecting PDF while T0F is already selected leaves T0F selected, fix generic include/exclusive reconciliation so PDF’s included T0G replaces T0F within the active aero exclusive group.

RED test:

- Select T0F first, then PDF.
- Assert T0F is removed/deactivated and T0G/CFV are included/locked through PDF.
- Re-run PDD counterpart to ensure PDD still keeps T0F and removes T0G.

### 5. PDB/PDD/PDF card prices should move to carbon-fiber wheels

Owner: `z06_options`, `z06_price_rules`, generated data, generic price display/copy.

Current semantic price rules already classify package price by wheel:

- ROY/ROZ/STZ -> PDB/PDD/PDF are `package_price_by_component`.

But current card display is confusing because package option rows still have direct `base_price` values. The proposed workbook-owned model is:

- Package selector cards PDB/PDD/PDF: no direct displayed price.
- Carbon-fiber wheel cards ROY/ROZ/STZ: display the package-specific effective price when a package is selected, using existing `package_price_by_component` semantics.
- The wheel section copy explains that wheel choice determines the package price when a carbon-fiber wheel/brake/aero package is selected.

Implementation design options to inspect before writing:

1. Set direct package source prices to blank/0 and rely on `package_price_by_component` rules plus generic display logic to present prices on wheels.
2. If runtime `optionPrice()` can only target the package row, add a generic generated/audit metadata flag or generic display helper that, for `package_price_by_component`, shows the package-target price on the selected condition/wheel card when the package source is selected.
3. Add workbook-authored section/help copy to `section_master` or the existing section copy path if one exists; do not hardcode copy in app.js unless no workbook copy surface exists.

RED tests:

- Generated-data test: PDB/PDD/PDF package rows do not emit direct customer-facing card prices.
- Runtime test: after selecting PDB/PDD/PDF, ROY/ROZ/STZ wheel cards show the package-specific prices:
  - PDB: ROY 16000, ROZ 17000, STZ 17500
  - PDD: ROY 25495, ROZ 26495, STZ 26995
  - PDF: ROY 26495, ROZ 27495, STZ 27995
- Runtime total remains unchanged compared with current package-selection totals.
- Wheel section copy includes the new package-price explanation.

### 6. N26 should not be selectable; auto-add on all applicable interiors

Owner: `z06_options`, `interior_components`, generated interior line items, possibly generic runtime line-item behavior.

Corrected user direction:

- N26 should not ever be a selectable card in the option steps.
- N26 should auto-add on all interiors/components that require it, not only a 1LZ AE4 trigger.

Current evidence:

- `z06_options.N26` is active/selectable in `sec_inte_001`, direct price 695.
- `interior_components` already has 17 active Z06 N26 component rows with `component_type=suede`.

Preferred fix:

- Move N26 out of customer-selectable option sections by making the option source nonselectable/auto-only/display-only or moving it to a non-choice/standard/included section according to the existing source contract.
- Preserve/generated N26 as an auto-added line item when selected interiors include the N26 component.
- Use `interior_components` as the workbook source for applicability and price contribution.
- Do not add a direct option-card rule or RPO-specific JavaScript.

RED tests:

- Z06 generated choices should not include selectable N26 cards in option steps.
- Selecting an interior whose `interior_components` includes N26 should add N26 to line items/build output as an auto-added component with correct price semantics.
- Interiors without N26 should not add it.

### 7. Custom stitch should go away on the front end

Owner: `interior_components` / generated interior hierarchy / runtime rendering.

Current evidence:

- Active Z06 custom-stitch component rows exist for 36S, 37S, and 38S.
- The current front end can surface stitch-specific interior variants/cards/groups depending on generated hierarchy.

Preferred fix:

- Keep raw workbook evidence if needed for dealer handoff/pricing, but remove custom-stitch as a front-end selectable/grouping dimension.
- Do not delete source rows blindly. Either:
  - mark stitching component rows as non-display/audit-only if existing schema supports it, or
  - add a minimal workbook-owned display/include metadata field to the existing `interior_components` path if current rows cannot distinguish dealer-output component from front-end grouping component.
- Generated interior cards should not produce visible “Custom Stitch” choice surfaces or separate front-end variants solely for stitch color.

RED tests:

- Z06 generated/runtime interiors should not show custom-stitch-specific leaf labels/groups on the front end.
- Dealer/export line items should remain accurate if the stitch RPO still needs to be included with a chosen interior.

## Exact files / sheets likely to change after approval

Workbook source:

- `stingray_master.xlsx`
  - `z06_options`
  - `z06_rule_mapping`
  - `z06_price_rules`
  - `z06_exclusive_groups` / `z06_exclusive_members` only if inspection proves group metadata needs correction
  - `LZ_Interiors`
  - `model_interior_scope`
  - `interior_components`
  - `section_master` if workbook-owned section copy already lives there or can be extended safely

Generator/runtime code, only as needed after RED tests:

- `scripts/generate_z06_form.py`
- `scripts/generate_stingray_form.py`
- shared generator helpers under `scripts/corvette_form_generator/`
- `form-app/app.js`
  - only for generic rendering/reconciliation behavior that cannot be expressed by generated data alone

Tests:

- likely new `tests/z06-form-fix-list.test.mjs` or focused additions to:
  - `tests/z06-form-data-draft.test.mjs`
  - `tests/z06-performance-package-interactions.test.mjs`
  - `tests/z06-runtime-rule-corrections.test.mjs`
  - `tests/z06-runtime-promotion.test.mjs`
  - `tests/multi-model-runtime-switching.test.mjs`
  - `tests/workbook-schema-standardization.test.mjs` if new workbook columns/semantics are added

Generated artifacts to regenerate/review, not hand-edit:

- `form-output/inspection/z06-*`
- `form-output/stingray-form-data.json`
- `form-app/data.js`
- generated `form_*` sheets inside `stingray_master.xlsx`

## Implementation approach after approval

1. Preflight:

```sh
git branch --show-current
git status --short --branch
if [ -e './~$stingray_master.xlsx' ]; then echo LOCK_PRESENT; else echo NO_LOCK_FILE; fi
.venv/bin/python scripts/validate_workbook_package.py stingray_master.xlsx
.venv/bin/python scripts/validate_workbook_schema.py stingray_master.xlsx
```

Stop before workbook writes if Excel lock file exists or unrelated tracked changes are present.

2. Add RED tests for the seven reported behaviors before workbook/runtime edits. Tests must fail for the reported behavior, not due to typos.

3. Inspect exact current runtime functions for:

- include reconciliation and exclusive peer replacement;
- price display for options and interiors;
- line-item/export behavior for interior components;
- section copy rendering.

4. Design the smallest safe workbook migration. Use a dry-run-by-default script if workbook writes are more than a handful of rows.

5. Apply workbook changes through `save_workbook_safely()` only.

6. Reopen the workbook with `openpyxl` and verify exact target rows on disk.

7. Regenerate:

```sh
.venv/bin/python scripts/generate_z06_form.py
.venv/bin/python scripts/generate_stingray_form.py
```

8. Run focused GREEN tests, then broader Z06/multi-model gates.

9. Browser smoke exact user paths:

- Interior color grouping and custom-stitch visibility.
- BCW selected alone: D3V should not auto-add.
- B6P selected: D3V should still follow intended included-zero behavior if preserved.
- Z07 selected: J57 included/locked at $0, J56 not active selected.
- T0F selected then PDF selected: T0F removed, T0G/CFV included/locked.
- PDB/PDD/PDF selected: package card no price; wheel cards show package-combination price; totals remain correct.
- N26 absent from option-step selectable cards; selected applicable interiors add N26 through component/line-item behavior.

10. Restore unrelated generated timestamp churn before handoff.

## Constraints / boundaries

- Stay inside normalized workbook-owned rule pathways from Passes 1–6.
- Do not restore redundant same-group excludes or Z06 replace swarms.
- Do not add Z06/RPO-specific JavaScript exceptions unless a generic runtime capability is missing and the spec is amended.
- Do not add a parallel interior grouping taxonomy if `LZ_Interiors`, `model_interior_scope`, or `interior_components` can carry the needed data.
- Do not hand-edit generated `form_*` sheets, JSON, or `form-app/data.js`.
- Do not change dealer submission endpoint, Turnstile, payload shape, deployment behavior, or styling beyond minimal copy/rendering needed for the listed issues.
- Do not touch ZR1/ZR1X in this pass.
- Preserve total-price correctness while moving package price display from package cards to carbon-fiber wheel cards.
- Preserve dealer handoff/build-output accuracy when hiding N26/custom-stitch from the front end.

## Validation plan

Preflight and workbook validators:

```sh
.venv/bin/python scripts/validate_workbook_package.py stingray_master.xlsx
.venv/bin/python scripts/validate_workbook_schema.py stingray_master.xlsx
```

Focused tests after RED/GREEN:

```sh
node --test tests/z06-form-data-draft.test.mjs
node --test tests/z06-runtime-rule-corrections.test.mjs
node --test tests/z06-performance-package-interactions.test.mjs
node --test tests/z06-runtime-promotion.test.mjs
```

Runtime/multi-model regression:

```sh
node --test tests/multi-model-runtime-switching.test.mjs
node --test tests/stingray-form-regression.test.mjs tests/stingray-generator-stability.test.mjs
node --test tests/grand-sport-contract-preview.test.mjs tests/grand-sport-draft-data.test.mjs tests/grand-sport-rule-audit.test.mjs
```

Python suite:

```sh
.venv/bin/python -m pytest tests -q
```

Browser smoke:

- Serve `form-app` locally.
- Exercise the exact seven reported Z06 paths.
- Check browser console for JavaScript errors.

## Open questions before implementation

1. For J56/Z07: should J56 be hidden/available-but-unselected while Z07 is selected, or is the issue specifically that J56 appears selected/deactivated instead of being replaced by included J57? This spec assumes Z07 should replace selected/default J56 with included/locked J57.
2. For custom stitch: should stitch RPOs disappear only as front-end choice/grouping UI while remaining in dealer/build output when selected by an interior, or should they be fully omitted from customer summaries too? This spec assumes hidden from front-end choice/grouping but preserved for dealer/build accuracy if required.
3. Resolved on approval: for package price display, show the delta over the package base on ROY/ROZ/STZ when a PDB/PDD/PDF package is selected. Package cards should still be price-less; the wheel cards should explain and display the package-specific delta over the package base.

## Approval

Approved by Sean. Implementation should start with RED tests for these exact user-reported behaviors, then workbook/source changes, regeneration, focused gates, full affected gates, and browser smoke.

## Implementation results

Implemented files:

- `stingray_master.xlsx`
  - `z06_options`: hid N26 and 36S/37S/38S from customer option-step cards while keeping source/generated rows for dealer/build accuracy.
  - `section_presentation`: hid Z06 custom stitch section presentation.
  - `z06_exclusive_groups`: updated carbon-wheel group customer copy to explain package-base deltas.
- `scripts/corvette_form_generator/inspection.py`
  - Z-family fallback interior hierarchy now uses workbook-owned interior codes for coded color families such as `HTA Jet Black` and `HTJ Jet Black`, preserving seat hierarchy.
- `form-app/app.js`
  - Generic package/component price display now keeps PDB/PDD/PDF package cards price-less, keeps package base in order lines, and shows ROY/ROZ/STZ deltas over package base when a package is selected.
  - Generic included-exclusive reconciliation now lets direct package includes win over indirect includes, so PDF replaces a prior T0F/CFZ state with T0G/CFV.
- Generated artifacts refreshed:
  - `form-output/inspection/z06-*`
  - `form-output/stingray-form-data.json`
  - `form-app/data.js`
- Tests updated/added:
  - `tests/z06-form-data-draft.test.mjs`
  - `tests/z06-performance-package-interactions.test.mjs`
  - `tests/z06-runtime-rule-corrections.test.mjs`

Verified gates:

```sh
.venv/bin/python scripts/validate_workbook_schema.py stingray_master.xlsx
.venv/bin/python scripts/validate_workbook_package.py stingray_master.xlsx
node --test tests/workbook-schema-standardization.test.mjs tests/z06-form-data-draft.test.mjs tests/z06-runtime-rule-corrections.test.mjs tests/z06-performance-package-interactions.test.mjs tests/z06-runtime-promotion.test.mjs tests/z06-contract-preview.test.mjs
```

Result: workbook schema valid, workbook package valid, 49 Node tests passed, 0 failed.

Browser smoke with local `python3 -m http.server 8765` verified:

- PDB/PDD/PDF cards render without direct prices.
- After PDB, ROY shows `$0`, ROZ shows `$1,000`, STZ shows `$1,500`.
- Wheel section copy says ROZ/STZ show only the delta over the package base.
- Selecting T0F then PDF leaves PDF selected, T0F/CFZ unavailable but not selected, and T0G/CFV auto-added.
- N26 and custom stitch text are absent from the front-end option-step page.
