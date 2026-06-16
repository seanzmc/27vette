# Active Model Non-Runtime Option Row Purge Spec

Recommended reasoning level: high.

## Status

Spec only. Do not implement until approved.

## Diagnosis

The active model option source sheets still carry rows that the current form runtime does not need as customer-selectable options. Some are already suppressed before runtime; some are better owned by other workbook sheets such as `interior_components`; some are duplicate inactive standard-equipment scaffold rows.

The goal is to remove those unnecessary source-option rows from the three active models without changing form behavior.

Current evidence inspected:

- Active branch/status: `generator-simplification-pass1`, clean worktree at inspection time.
- Stingray custom stitch behavior:
  - `section_presentation` has `model_key=stingray`, `section_id=sec_cust_002`, `display_behavior=hidden`.
  - `scripts/corvette_form_generator/production.py:211-220` applies the section-level hidden behavior and makes those source options inactive before choice emission.
  - `production.py:319-321` skips inactive options when building choices.
- Grand Sport and Z06 draft/runtime-contract path:
  - `scripts/generate_form.py:141-144` sends `grand_sport` and `z06` through the draft/inspection path, not Stingray production.
  - `scripts/corvette_form_generator/inspection.py:744-746` skips inactive option rows.
  - `inspection.py:270-282` and `inspection.py:801-808` also support option-level `display_behavior`, but they do not mirror Stingray production's section-level hidden inheritance before the active-row filter.
- Runtime rendering:
  - `form-app/app.js:690-691` hides inactive/unavailable/hidden choices generically.
  - `form-app/app.js:2389-2417` renders option-step sections only from visible choice rows.
- Generated/live registry probe from `form-app/data.js`:
  - `stingray`: `sec_cust_002` section exists, choices = 0.
  - `grandSport`: `sec_cust_002` section = 0, choices = 0.
  - `z06`: `sec_cust_002` section = 0, choices = 0.
- Workbook read-only inventory confirmed `interior_components` owns the component runtime data for:
  - Stingray/Grand Sport/Z06: `36S`, `37S`, `38S`, `N26`, `TU7`, seat component RPOs, and `R6X`.
  - Z06 additionally: `N2Z` suede steering-wheel component rows.
- Current tests that will need safe update or extension include:
  - `tests/stingray-generator-stability.test.mjs:386-389` currently expects the Stingray `sec_cust_002` hidden presentation row.
  - `tests/stingray-form-regression.test.mjs:1080-1084` asserts custom-stitch choices do not appear in runtime.
  - `tests/stingray-form-regression.test.mjs:1653-1703` asserts interior component line items for stitch/N26/TU7 remain generated through interiors.
  - `tests/z06-form-data-draft.test.mjs:375-377` asserts Z06 N26/suede/two-tone/custom-stitch source rows do not render as selectable option-step cards.
  - `tests/z06-performance-package-interactions.test.mjs:375-379` has browser/runtime coverage that N26 is not rendered as a selectable option card.

Risk level: medium. The intended source-row deletion is behavior-preserving, but deleting active standard-equipment rows or active seat-choice rows would change generated choices, standard-equipment summaries, pricing, default selections, or dealer/build output.

Change type: workbook/data + tests + generated artifacts. No intended runtime JS behavior change. No new dependencies.

## Ownership Decision

Remove rows from model option source sheets only when another workbook/runtime owner already covers the behavior or the row is already non-emitted.

Replacement owners:

- Custom stitching (`36S`, `37S`, `38S`) belongs to `interior_components` and selected-interior line items, not selectable option cards.
- Suede/two-tone interior component RPOs (`N26`, `N2Z`, `TU7`) belong to `interior_components` and selected-interior line items, not standalone option cards.
- Inactive `sec_onst_001` service-plan rows are not emitted into runtime and should not remain as source-option clutter.
- Inactive duplicate standard-equipment rows in `sec_stan_002` are not emitted and duplicate canonical selectable/default rows elsewhere.
- Inactive Grand Sport duplicate seat rows are not emitted and duplicate the active canonical Grand Sport seat choices.

Do not delete currently emitted rows in this pass unless the implementation first moves their behavior to an equivalent workbook owner and proves generated runtime contracts are behavior-identical. This means active Stingray seat rows and active `sec_tech_001` standard connected-service rows are deferred unless explicitly approved as a separate modeling pass.

## Exact Workbook Sheets to Change

Canonical workbook: `stingray_master.xlsx`.

Source option sheets:

- `stingray_options`
- `grandSport_options`
- `z06_options`

Matching OVS/status sheets:

- `stingray_ovs`
- `grandSport_ovs`
- `z06_ovs`

Metadata rows to remove only if no remaining active-model source options use them:

- `section_presentation` rows for active-model `sec_cust_002` hidden behavior:
  - `stingray / sec_cust_002`
  - `z06 / sec_cust_002`
  - Grand Sport currently has no matching active row.

Do not delete shared `section_master` rows in this pass. `section_master.sec_cust_002`, `section_master.sec_onst_001`, and `section_master.sec_stan_002` are shared taxonomy rows and may still be useful for historical/future-model data or later cleanup. Removing shared sections needs a separate cross-model/future-model reference audit.

## Current Safe-Delete Candidate Rows

Current row numbers are inspection-time evidence only. Use stable `option_id` keys during implementation.

### Stingray

Delete these 20 `stingray_options` rows and their 120 matching `stingray_ovs` rows:

- Custom stitch component-owned rows:
  - `opt_38s_001` / `38S` / `sec_cust_002`
  - `opt_36s_001` / `36S` / `sec_cust_002`
  - `opt_37s_001` / `37S` / `sec_cust_002`
- Interior component-owned inactive rows:
  - `opt_n26_001` / `N26` / `sec_inte_001`
  - `opt_tu7_001` / `TU7` / `sec_inte_001`
- Inactive OnStar/service-plan section rows:
  - `opt_r9w_001` / `R9W` / `sec_onst_001`
  - `opt_r6p_001` / `R6P` / `sec_onst_001`
  - `opt_prb_001` / `PRB` / `sec_onst_001`
  - `opt_r9y_001` / `R9Y` / `sec_onst_001`
  - `opt_r9v_001` / `R9V` / `sec_onst_001`
  - `opt_r9l_001` / `R9L` / `sec_onst_001`
- Inactive duplicate standard-equipment rows:
  - `opt_j6a_002` / `J6A` / `sec_stan_002`
  - `opt_eyt_002` / `EYT` / `sec_stan_002`
  - `opt_cm9_002` / `CM9` / `sec_stan_002`
  - `opt_nga_002` / `NGA` / `sec_stan_002`
  - `opt_efr_002` / `EFR` / `sec_stan_002`
  - `opt_cf7_002` / `CF7` / `sec_stan_002`
  - `opt_719_002` / `719` / `sec_stan_002`
  - `opt_fe1_002` / `FE1` / `sec_stan_002`
  - `opt_qeb_002` / `QEB` / `sec_stan_002`

Do not delete in this pass without additional modeling:

- Active Stingray seat choice/standard rows: `opt_aq9_003`, `opt_ae4_001`, `opt_aq9_004`, `opt_ah2_003`, `opt_ae4_002`, `opt_ah2_002`, `opt_ae4_003`, `opt_aup_001`, `opt_aq9_002`, `opt_aq9_001`, `opt_ah2_001`.
- Active standard connected-service/tech rows: `opt_u5g_001`, `opt_ive_001`, `opt_008`, `opt_ue1_001`, `opt_u2k_001`, `opt_vv4_001`.
- `opt_iwe_001`; current evidence treats it as 3LT standard equipment, not the same as the N26/TU7 component-only rows.

### Grand Sport

Delete these 31 `grandSport_options` rows and their 186 matching `grandSport_ovs` rows:

- Inactive duplicate seat rows:
  - `opt_aq9_004` / `AQ9` / `sec_1lte_001`
  - `opt_aq9_003` / `AQ9` / `sec_2lte_001`
  - `opt_ah2_003` / `AH2` / `sec_3lte_001`
  - `opt_aq9_002` / `AQ9` / `sec_seat_002`
  - `opt_ae4_001` / `AE4` / `sec_seat_002`
  - `opt_ae4_003` / `AE4` / `sec_seat_002`
  - `opt_ah2_002` / `AH2` / `sec_seat_002`
- Custom stitch component-owned rows:
  - `opt_38s_001` / `38S` / `sec_cust_002`
  - `opt_36s_001` / `36S` / `sec_cust_002`
  - `opt_37s_001` / `37S` / `sec_cust_002`
- Interior component-owned inactive rows:
  - `opt_n26_001` / `N26` / `sec_inte_001`
  - `opt_tu7_001` / `TU7` / `sec_inte_001`
- Inactive OnStar/service-plan section rows:
  - `opt_r9w_001` / `R9W` / `sec_onst_001`
  - `opt_r6p_001` / `R6P` / `sec_onst_001`
  - `opt_prb_001` / `PRB` / `sec_onst_001`
  - `opt_r9y_001` / `R9Y` / `sec_onst_001`
  - `opt_r9v_001` / `R9V` / `sec_onst_001`
  - `opt_r9l_001` / `R9L` / `sec_onst_001`
  - `opt_u5g_001` / `U5G` / `sec_onst_001`
  - `opt_ue1_001` / `UE1` / `sec_onst_001`
  - `opt_u2k_001` / `U2K` / `sec_onst_001`
  - `opt_vv4_001` / `VV4` / `sec_onst_001`
  - `opt_009` / blank RPO / `sec_onst_001`
- Inactive duplicate standard-equipment rows:
  - `opt_j6a_002` / `J6A` / `sec_stan_002`
  - `opt_eyt_002` / `EYT` / `sec_stan_002`
  - `opt_cm9_002` / `CM9` / `sec_stan_002`
  - `opt_nga_002` / `NGA` / `sec_stan_002`
  - `opt_efr_002` / `EFR` / `sec_stan_002`
  - `opt_cf7_002` / `CF7` / `sec_stan_002`
  - `opt_719_002` / `719` / `sec_stan_002`
  - `opt_swm_002` / `SWM` / `sec_stan_002`

Do not delete in this pass without additional modeling:

- Active Grand Sport canonical seat choices: `opt_aq9_001`, `opt_ah2_001`, `opt_ae4_002`, `opt_aup_001`.
- Active standard tech row: `opt_ive_001`.

### Z06

Delete these 6 `z06_options` rows and their 36 matching `z06_ovs` rows:

- Custom stitch component-owned rows:
  - `opt_36s_001` / `36S` / `sec_cust_002`
  - `opt_37s_001` / `37S` / `sec_cust_002`
  - `opt_38s_001` / `38S` / `sec_cust_002`
- Interior component-owned inactive rows:
  - `opt_n26_001` / `N26` / `sec_inte_001`
  - `opt_n2z_001` / `N2Z` / `sec_inte_001`
  - `opt_tu7_001` / `TU7` / `sec_inte_001`

Do not delete in this pass without additional modeling:

- Active Z06 canonical seat choices: `opt_ae4_002`, `opt_ah2_001`, `opt_aq9_001`, `opt_aup_001`.
- Active standard connected-service/tech rows: `opt_129`, `opt_ive_001`, `opt_u2k_002`, `opt_u5g_002`, `opt_ue1_002`, `opt_vv4_002`.

## Exact Files to Change

Expected source/test/doc changes after approval:

- `stingray_master.xlsx`
  - Delete approved rows from the three active model option sheets and OVS sheets.
  - Delete now-obsolete active-model `section_presentation` hidden rows for `sec_cust_002` if the active model no longer has source options in that section.
  - Refresh affected Excel table refs after row deletion.
- Tests, likely:
  - `tests/stingray-generator-stability.test.mjs`
    - Replace the old assertion that `section_presentation.stingray/sec_cust_002.display_behavior === "hidden"` with assertions that the non-runtime source rows are gone and interior component ownership remains.
  - `tests/grand-sport-draft-data.test.mjs` or a new shared source-contract test.
  - `tests/z06-form-data-draft.test.mjs`
    - Keep runtime non-render assertions, but add/source-adjust workbook assertions so Z06 no longer passes by retaining inactive hidden source rows.
  - `tests/z06-performance-package-interactions.test.mjs`
    - Keep browser/runtime assertion that N26 does not render; do not make it depend on an option-source row existing.
  - Prefer one shared test, e.g. `tests/nonruntime-option-source-purge.test.mjs`, that reads `stingray_master.xlsx` and asserts all approved purged rows are absent from both option sheets and OVS sheets.
- A temporary implementation helper may be used, but do not retain a one-pass writer as executable documentation after the workbook write is verified. If a script is added for reviewability, delete it before final handoff unless it becomes a durable validator.

Generated outputs expected to refresh, not hand edit:

- `form_*` generated workbook sheets from the Stingray generator.
- `form-output/stingray-form-data.json`
- `form-output/stingray-form-data.csv`
- `form-output/inspection/grand-sport-*` generated artifacts.
- `form-output/inspection/z06-*` generated artifacts.
- `form-app/data.js` after `scripts/generate_registry.py`.

Expected generated-data behavior:

- Runtime choices, prices, rules, interiors, standard equipment, color overrides, and dealer/build payload behavior should remain unchanged for customer-facing paths.
- Inspection artifacts may show lower source-row/OVS counts. That count drift is expected and should be reported separately from runtime behavior.

## Implementation Constraints

- Spec-first: do not implement until approved.
- Workbook source-of-truth: delete source rows only when another workbook sheet owns the runtime behavior or the row is already non-emitted.
- No runtime JS special cases and no model/RPO hardcodes in browser code.
- No new dependencies.
- No visual changes.
- No dealer submission behavior changes.
- Do not delete active emitted rows merely because their labels are ugly/noisy.
- Do not delete `interior_components` rows for `36S`, `37S`, `38S`, `N26`, `N2Z`, `TU7`, seats, or `R6X`; those rows are the replacement owner.
- Do not delete `PriceRef` rows needed for interior/component pricing.
- Preserve workbook boolean cell storage conventions; do not normalize unrelated True/False cells.
- Check for `~$stingray_master.xlsx` before any workbook write and stop if Excel has the workbook open.
- Save through `save_workbook_safely()` and verify the workbook on disk with `openpyxl` after writing.
- Delete matching OVS rows whenever an option row is deleted.
- Fail the pass if a to-be-deleted option id is still referenced by an active rule, price rule, rule-group member, exclusive-group member, variant override, asset row, default-selection rule, color override, or other runtime owner not named in this spec.

## Required Preflight Before Workbook Write

1. Snapshot current generated behavior to temp files outside the repo, including:
   - `form-output/stingray-form-data.json`
   - `form-output/inspection/grand-sport-form-data-draft.json`
   - `form-output/inspection/grand-sport-runtime-contract.json`
   - `form-output/inspection/z06-form-data-draft.json`
   - `form-output/inspection/z06-runtime-contract.json`
   - `form-app/data.js` parsed structurally by model.
2. Re-run a read-only workbook inventory immediately before writing:
   - Confirm exact option IDs still exist where expected.
   - Confirm matching OVS row counts.
   - Confirm active `interior_components` rows exist for component-owned RPOs.
   - Confirm no active non-OVS references to deleted option IDs.
3. Classify and print a dry-run delete plan by sheet with counts.
4. Stop if the dry run includes any row outside the approved exact option-id lists.

## Validation Plan

Workbook package/schema:

```sh
.venv/bin/python scripts/validate_workbook_package.py stingray_master.xlsx
.venv/bin/python scripts/validate_workbook_schema.py stingray_master.xlsx
```

Regenerate active model artifacts:

```sh
.venv/bin/python scripts/generate_form.py --model stingray
.venv/bin/python scripts/generate_form.py --model grand_sport
.venv/bin/python scripts/generate_form.py --model z06
.venv/bin/python scripts/generate_registry.py
```

Behavior-equivalence checks:

```sh
node scripts/compare-generated-contracts.mjs /tmp/before-stingray-form-data.json form-output/stingray-form-data.json
node scripts/compare-generated-contracts.mjs /tmp/before-grand-sport-runtime-contract.json form-output/inspection/grand-sport-runtime-contract.json
node scripts/compare-generated-contracts.mjs /tmp/before-z06-runtime-contract.json form-output/inspection/z06-runtime-contract.json
```

The comparison should be clean for runtime behavior surfaces, ignoring timestamps. If only inspection/source-count artifacts change, report that as expected non-runtime drift. If choices, standard equipment, rules, interiors, prices, or dealer-relevant payload fields change unexpectedly, stop and restore or split the pass.

Targeted tests:

```sh
node --test tests/stingray-form-regression.test.mjs
node --test tests/stingray-generator-stability.test.mjs
node --test tests/grand-sport-contract-preview.test.mjs
node --test tests/grand-sport-draft-data.test.mjs
node --test tests/z06-contract-preview.test.mjs
node --test tests/z06-form-data-draft.test.mjs
node --test tests/z06-interior-accessory-cleanup.test.mjs
node --test tests/z06-performance-package-interactions.test.mjs
node --test tests/z06-runtime-rule-corrections.test.mjs
node --test tests/multi-model-runtime-switching.test.mjs
```

Source-row purge guard:

Add or update a test that asserts all approved option IDs are absent from their model option and OVS sheets, and that no active model option source sheet contains:

- `section_id=sec_cust_002`
- `section_id=sec_onst_001`
- inactive `sec_stan_002` duplicate rows
- inactive source-option rows for active-model `interior_components` component RPOs `36S`, `37S`, `38S`, `N26`, `N2Z`, `TU7`
- the listed inactive Grand Sport duplicate seat option IDs

The guard must not fail on explicitly deferred active emitted rows.

Manual/browser verification:

- Stingray: Interior Trim step still has no Custom Stitch or OnStar selectable cards; selected interior line items still show stitch/N26/TU7 component RPOs when applicable.
- Grand Sport: no Custom Stitch/OnStar component cards; seat defaults and selectable seat cards behave as before.
- Z06: no N26/N2Z/TU7/custom stitch option cards; Z06 package/performance tests and interior component line items behave as before.
- Confirm dealer/build output still includes interior component line items where previously included.

## Risks

- Active standard connected-service rows in `sec_tech_001` are currently emitted standard equipment. Deleting them would change visible trim standard-equipment data unless a separate standard-equipment ownership decision is made.
- Active Stingray duplicate seat rows currently emit choices/standard equipment and encode variant/trim price/status behavior. They are not safe to delete in this pass without a seat-normalization model that preserves generated contracts.
- Removing `section_presentation` hidden rows is safe only after the source option rows are gone and generated contracts compare clean.
- Deleting source rows without matching OVS cleanup can break coverage/stability gates.
- Deleting rows that still have rule/price/group references can create orphan references or silently remove behavior.

## Non-Goals

- No runtime JS refactor.
- No new sheet or parallel taxonomy.
- No deletion of `interior_components`, `model_interior_scope`, `lt_interiors`, `LZ_Interiors`, or `PriceRef` rows.
- No cleanup of future ZR1/ZR1X option sheets.
- No broad standard-equipment redesign.
- No active seat-row canonicalization unless separately approved after this purge.
- No removal of shared `section_master` taxonomy rows.

## Approval Question

Approve this pass as a source-row purge limited to the exact safe-delete lists above?

Recommended answer: approve this limited pass first. It removes rows that are already non-runtime or owned by `interior_components` while protecting currently emitted seat and standard-equipment behavior. After it is green, write a separate seat/standard-equipment modeling spec for any active emitted rows you still want removed from option sheets.
