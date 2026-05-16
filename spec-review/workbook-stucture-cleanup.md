# Workbook Structure Cleanup

Spec only. Do not implement until an implementation pass is separately approved.

## Objective

Move Corvette business rules out of generator/runtime code and back into workbook-authored source sheets wherever practical, while preserving the workbook structures that are already working.

Priority areas are:

- duplicate RPO cleanup;
- UI visibility and selection semantics;
- dependency mapping and replacement behavior;
- price calculations;
- summary/export grouping.

The cleanup direction is not to invent new Stingray-only sheets or runtime branches. Grand Sport already proves much of the workbook-owned rule structure. Stingray should use the same structures and headers wherever the same business concept exists.

## Current Workbook-Owned Architecture

The workbook already has paired model source sheets for the main business-rule surfaces:

| Business concept | Stingray source | Grand Sport source | Current contract |
| --- | --- | --- | --- |
| option rows | `stingray_options` | `grandSport_options` | same normalized headers |
| variant status rows | `stingray_ovs` | `grandSport_ovs` | same normalized headers |
| option rules | `rule_mapping` | `grandSport_rule_mapping` | same rule headers; `rule_mapping` currently has trailing blank Excel columns that should be cleaned, not copied into new schemas |
| price rules | `price_rules` | `grandSport_price_rules` | same headers |
| grouped requirements/exclusions | `rule_groups`, `rule_group_members` | `grandSport_rule_groups`, `grandSport_rule_group_members` | same group/member shape |
| mutually exclusive subsets | `exclusive_groups`, `exclusive_group_members` | `grandSport_exclusive_groups`, `grandSport_exclusive_members` | same group/member shape |
| shared section metadata | `section_master` | `section_master` | section name, selection mode, required flag, display order, standard behavior, help text, step key |

Implementation specs should first check these existing paired sheets before proposing new columns, new sheets, or model-specific code paths. If a needed capability exists on Grand Sport but not Stingray, extend Stingray to use the same workbook contract. If a capability exists on neither model, add the smallest shared/model-scoped workbook surface that can support both models consistently.

## Pass 1 Verification Snapshot

Verified on 2026-05-16 against `stingray_master.xlsx`. This was an audit-only pass; the workbook was not mutated.

Workbook package validation:

```text
status = valid
issue_count = 0
```

Source sheet contract counts:

| Sheet | Populated rows | Active rows | Selectable rows | Header status |
| --- | ---: | ---: | ---: | --- |
| `stingray_options` | 270 | 255 | 166 | matches `grandSport_options` |
| `grandSport_options` | 269 | 230 | 162 | matches `stingray_options` |
| `stingray_ovs` | 1620 | n/a | n/a | matches `grandSport_ovs` |
| `grandSport_ovs` | 1614 | n/a | n/a | matches `stingray_ovs` |
| `rule_mapping` | 235 | n/a | n/a | same first 16 headers as `grandSport_rule_mapping`, plus 7 trailing blank Excel headers |
| `grandSport_rule_mapping` | 328 | n/a | n/a | clean 16-header rule contract |
| `price_rules` | 42 | n/a | n/a | matches `grandSport_price_rules` |
| `grandSport_price_rules` | 45 | n/a | n/a | matches `price_rules` |
| `rule_groups` | 2 | 2 | n/a | matches `grandSport_rule_groups` |
| `grandSport_rule_groups` | 1 | 1 | n/a | matches `rule_groups` |
| `rule_group_members` | 5 | 5 | n/a | matches `grandSport_rule_group_members` |
| `grandSport_rule_group_members` | 18 | 18 | n/a | matches `rule_group_members` |
| `exclusive_groups` | 7 | 7 | n/a | matches `grandSport_exclusive_groups` |
| `grandSport_exclusive_groups` | 9 | 9 | n/a | matches `exclusive_groups` |
| `exclusive_group_members` | 25 | 25 | n/a | matches `grandSport_exclusive_members` |
| `grandSport_exclusive_members` | 28 | 24 | n/a | matches `exclusive_group_members` |
| `section_master` | 42 | n/a | n/a | shared source |

Pass 1 conclusions:

- The paired source-sheet structure is already in place for options, variant statuses, price rules, rule groups, and exclusive groups.
- `rule_mapping` should eventually be cleaned to the same 16-header shape as `grandSport_rule_mapping`; that is a workbook cleanup item and should not be solved by adding a new rule sheet or teaching code to depend on blank headers.
- The active duplicate-RPO diagnosis below is still current and should be the first high-risk workbook implementation pass.
- Later passes now tie back to a diagnosis item in this document. If a future implementation pass discovers a new code-owned branch or source-data issue, add that finding here before implementing the change.

## Current Findings

### Duplicate RPOs In `stingray_options`

`stingray_options` still contains active duplicate RPO groups. Verified duplicate groups include:

| RPO | Current option IDs | Current role |
| --- | --- | --- |
| `719` | `opt_719_001`, `opt_719_002` | selectable/default seat belt plus standard-equipment mirror |
| `AE4` | `opt_ae4_001`, `opt_ae4_002`, `opt_ae4_003` | multiple seat rows standing in for trim/variant behavior |
| `AH2` | `opt_ah2_001`, `opt_ah2_002`, `opt_ah2_003` | trim-equipment mirror plus selectable seat rows |
| `AQ9` | `opt_aq9_001`, `opt_aq9_002`, `opt_aq9_003`, `opt_aq9_004` | trim-equipment mirrors plus selectable seat rows |
| `CF7` | `opt_cf7_001`, `opt_cf7_002` | selectable roof plus standard-equipment mirror |
| `CM9` | `opt_cm9_001`, `opt_cm9_002` | selectable roof plus standard-equipment mirror |
| `EFR` | `opt_efr_001`, `opt_efr_002` | selectable/default exterior accent plus standard-equipment mirror |
| `EYT` | `opt_eyt_001`, `opt_eyt_002` | selectable badge package plus standard-equipment mirror |
| `FE1` | `opt_fe1_001`, `opt_fe1_002` | selectable/default suspension plus standard-equipment mirror |
| `J6A` | `opt_j6a_001`, `opt_j6a_002` | selectable/default caliper plus standard-equipment mirror |
| `NGA` | `opt_nga_001`, `opt_nga_002` | selectable/default exhaust tip plus standard-equipment mirror |
| `QEB` | `opt_qeb_001`, `opt_qeb_002` | selectable/default wheel plus standard-equipment mirror |
| `UQT` | `opt_uqt_001`, `opt_uqt_002` | trim-equipment mirror plus selectable option row |

Diagnosis: duplicates are currently acting as bridges for standard-equipment display, trim-scoped availability/selectability, default choices, and package/replace behavior. The cleanup must not just delete rows. It must first move each duplicate's business effect onto a canonical option row, existing rule rows, existing price-rule rows, grouped/exclusive groups, or a shared variant-scoped override capability if the current row-level fields cannot express the behavior.

Risk: High, data-only plus generator/runtime behavior impact. Handle as a standalone pass after a per-RPO transfer plan is reviewed.

### UI Visibility / Selection Semantics

1. `sec_exte_001` should stay multi-select at the section level.

   `section_master.sec_exte_001` is currently:

   ```text
   selection_mode = multi_select_opt
   is_required = True
   step_key = exterior_appearance
   ```

   That is compatible with the Grand Sport pattern. Grand Sport keeps the shared section multi-select because `ZYC` is allowed to remain independently selectable, then uses `grandSport_exclusive_groups.gs_excl_exterior_accents` to make only `EFR` and `EDU` mutually exclusive:

   ```text
   grandSport_exclusive_groups.gs_excl_exterior_accents
   selection_mode = single_within_group
   members = opt_efr_001 | opt_edu_001
   ```

   Stingray already uses the same generic mechanism for its current mutually exclusive exterior-accent subset:

   ```text
   exclusive_groups.excl_ext_accents
   selection_mode = single_within_group
   members = opt_efr_001 | opt_efy_001 | opt_edu_001
   ```

   Conclusion: do not change `sec_exte_001` to `single_select_req` or `single_select_opt` for Stingray. If UI copy is misleading because every currently visible Stingray option in that section happens to be mutually exclusive, fix the copy/display logic to understand exclusive-group membership, or leave the section label generic. Do not encode a model-specific section-mode exception.

2. Hidden sections are still code-owned.

   File: `scripts/generate_stingray_form.py`

   ```python
   HIDDEN_SECTION_IDS = {"sec_cust_002"}
   ...
   if display_behavior == "hidden" or option.get("section_id") in HIDDEN_SECTION_IDS:
       option["active"] = "False"
   ```

   Proposed workbook source: option rows should carry `display_behavior=hidden` / inactive state, or a shared section visibility field should be added only if both model workflows need section-level hiding. Do not add a Stingray-only hidden-section path.

3. UQT visibility is still code-owned.

   File: `scripts/generate_stingray_form.py`

   ```python
   if option_id == "opt_uqt_002" and variant["trim_level"] != "1LT":
       status = "unavailable"
       selectable = "False"
       active = "False"
   ```

   This overlaps with the duplicate-RPO problem. Grand Sport has already used a model-scoped `grandSport_variant_overrides` pattern for trim/variant-scoped selectability. If Stingray needs one canonical UQT row that is selectable for one trim and included/display-only for another, reuse or generalize that same override structure instead of preserving an `opt_uqt_002` branch.

4. Default selected options are partly code-owned.

   File: `form-app/app.js`

   ```js
   for (const defaultRpo of ["FE1", "NGA", "BC7"]) {
   ```

   ```js
   if (!selectedOptionByRpo("Z51") && !selectedOrAutoInSection("sec_susp_001", refreshedAutoAdded)) addDefaultRpo("FE1");
   if (!selectedOptionByRpo("NWI") && !selectedOptionByRpo("NGA")) addDefaultRpo("NGA");
   if (!selectedOrAutoInSection("sec_seat_001", refreshedAutoAdded)) addDefaultRpo("719");
   ```

   Proposed workbook source: option-level `display_behavior=default_selected` already exists and should become the default-selection source. Conditional defaults should be expressed with existing rule/replacement structures where possible, not RPO-specific JavaScript.

### Price Calculations

1. Interior price adjustment subtracts selected seat price in JS.

   File: `form-app/app.js`

   ```js
   return Math.max(0, Number(interior.price || 0) - Number(seat?.base_price || 0));
   ```

   This may be runtime mechanics rather than business logic, but the contract should be explicit: either interior prices are workbook-authored as bundle totals and runtime subtracts selected seat display price, or workbook emits already-adjusted component lines.

2. D30/R6X zero-price behavior is hardcoded in JS.

   File: `form-app/app.js`

   ```js
   if (component.rpo === "R6X" && autoAdded.has("opt_d30_001")) return 0;
   ```

   Proposed workbook source: model this as a workbook-authored component price rule or interior price rule. The existing `price_rules` sheet handles option-level overrides, but component-level pricing may need a scoped source. Do not force component pricing into `price_rules` unless the target contract can represent interior component IDs and selected-interior context.

3. Interior component labels/types are code-owned in both Stingray and Grand Sport paths.

   Files: `scripts/generate_stingray_form.py`, `scripts/corvette_form_generator/inspection.py`

   ```python
   INTERIOR_COMPONENT_LABELS = {
       "36S": "Yellow Stitching",
       "37S": "Blue Stitching",
       "38S": "Red Stitching",
       "N26": "Sueded Microfiber",
       "N2Z": "Sueded Microfiber",
       "TU7": "Two-Tone",
       "R6X": "Custom Interior Trim and Seat Combination",
   }
   ```

   Proposed workbook source: add component metadata to an existing shared source if it fits cleanly, such as `PriceRef` or `lt_interiors`; add a dedicated model-consistent `interior_components` sheet only if the current sources cannot represent the metadata.

### Dependency Mapping

1. Z51, NWI, and GBA replacement behavior is still hardcoded in JS.

   File: `form-app/app.js`

   ```js
   if (choice.rpo === "FE1" && selectedOptionByRpo("Z51")) return "Replaced by FE3 Z51 performance suspension.";
   if (choice.rpo === "FE2" && selectedOptionByRpo("Z51")) return "Not available with Z51 Performance Package.";
   if (choice.rpo === "NGA" && selectedOptionByRpo("NWI")) return "Replaced by NWI center exhaust.";
   ```

   ```js
   if (selectedOptionByRpo("Z51")) {
     deleteSelectedRpo("FE1");
     deleteSelectedRpo("FE2");
   }
   if (selectedOptionByRpo("NWI")) {
     deleteSelectedRpo("NGA");
   }
   if (selectedOptionByRpo("GBA")) {
     deleteSelectedRpo("ZYC");
   }
   ```

   ```js
   if (choice.rpo === "GBA") deleteSelectedRpo("ZYC");
   ```

   Proposed workbook source: `rule_mapping` rows with `runtime_action=replace`, `disabled_reason`, and correct source/target section metadata. The runtime already has generic `removeReplaceRuleTargets()` support. Use the existing Stingray/Grand Sport rule-mapping contract before adding any new rule path.

2. R6X interior include rules are generated manually.

   File: `scripts/generate_stingray_form.py`

   ```python
   manual_rules.append(
       {
           "rule_id": f"rule_{interior_id.lower()}_includes_{included_option_id}",
           "source_id": interior_id,
           "rule_type": "includes",
           "target_id": included_option_id,
   ```

   Proposed workbook source: explicit interior-to-option include rows, or a normalized interior rule source consumed by the generator. If the workbook already has `included_option_id`, document that as the source of truth and reduce the generated rule code to a generic row expansion.

### Already Workbook-Driven / Do Not Refactor As Business Logic

1. Generic exclusive-group runtime behavior is already data-driven.

   Files/sheets: `exclusive_groups`, `exclusive_group_members`, `grandSport_exclusive_groups`, `grandSport_exclusive_members`, `form-app/app.js`

   Do not replace this with section-specific JS. Use exclusive groups for true mutually exclusive subsets inside a section, especially when the section can contain an independently selectable option.

2. Generic option price overrides are already data-driven.

   File: `form-app/app.js`

   ```js
   const priceRules = priceRulesByTarget.get(optionId) || [];
   for (const rule of priceRules) {
     if (!scopeMatches(rule.body_style_scope, state.bodyStyle)) continue;
     if (!scopeMatches(rule.trim_level_scope, state.trimLevel)) continue;
     if (!scopeMatches(rule.variant_scope, currentVariantId())) continue;
     if (rule.price_rule_type === "override" && selectedIds.has(rule.condition_option_id)) {
       return Number(rule.price_value || 0);
     }
   }
   ```

   Keep this generic path. The remaining gap is component/interior pricing, not normal option price rules.

3. Generic grouped requirements/exclusions are already data-driven.

   Files/sheets: `rule_groups`, `rule_group_members`, `grandSport_rule_groups`, `grandSport_rule_group_members`, `form-app/app.js`

   The cleanup target is RPO-specific branches, not the generic rule-group mechanism.

4. Shared `section_master.step_key` is already authoritative for normal section-to-step placement.

   Tests already assert the `section_master` header contract and require `step_key` on section rows. Do not introduce new section routing metadata unless it is model-scoped and necessary.

## Recommended Implementation Order

### Pass 1: Source Contract Alignment And Diagnosis Refresh

Task risk: Low, docs/audit-only unless workbook cleanup is separately approved.

1. Verify workbook source contracts before implementation.

   Files/sheets: `stingray_options`, `grandSport_options`, `stingray_ovs`, `grandSport_ovs`, `rule_mapping`, `grandSport_rule_mapping`, `price_rules`, `grandSport_price_rules`, `exclusive_groups`, `grandSport_exclusive_groups`, `exclusive_group_members`, `grandSport_exclusive_members`

   Confirm current headers and active row counts. Clean trailing blank headers in `rule_mapping` only in a separately approved workbook pass.

2. Update this spec or implementation specs when a pass references a finding not listed above.

   This prevents later implementation steps from looking detached from diagnosis. Each pass should cite the exact code branch, workbook sheet, and generated/runtime behavior it is meant to replace.

### Pass 2: Duplicate RPO Deactivation Plan

Task risk: High, standalone workbook/generator pass.

1. Build a per-RPO canonicalization table.

   Files/sheets: `stingray_options`, `stingray_ovs`, `rule_mapping`, `price_rules`, generated `form_*` sheets

   For each duplicate RPO, identify:

   - canonical option ID to keep;
   - duplicate option IDs to deactivate first and delete later;
   - variant statuses that must transfer to the canonical option ID;
   - `selectable`, `active`, `display_behavior`, and section behavior that must move to the canonical row or to variant-scoped overrides;
   - rules that currently reference duplicate IDs;
   - price rules that currently reference duplicate IDs;
   - standard-equipment behavior that must remain visible after duplicate rows are inactive.

2. Deactivate duplicates before deleting them.

   Files/sheets: `stingray_options`, `stingray_ovs`, `rule_mapping`, `price_rules`

   First pass should mark duplicate rows inactive or hidden and move needed behavior to canonical rows. Do not delete rows until generated parity is proven. Use Grand Sport's standard-mirror and trim-scoped selectability cleanup as the model: deactivate superseded duplicate rows, keep status coverage, and use variant-scoped overrides only when one canonical option row needs different selectability/display behavior per variant.

3. Remap rules to canonical option IDs only when the canonical row now owns that behavior.

   Files/sheets: `rule_mapping`, `rule_groups`, `exclusive_groups`, `price_rules`

   Do not blindly copy duplicate rules onto canonical rows. Some duplicate rules were compensating for a bridge row and may already be represented by canonical pricing, exclusive groups, or default/replacement rules. Preserve behavior, not duplicate row artifacts.

4. Delete duplicate rows only after parity.

   Delete duplicate `stingray_options`, `stingray_ovs`, and rule rows after generated app data and tests prove no duplicate IDs are needed. No generated choice, rule, price rule, exclusive group, order export, or app registry should reference a decommissioned duplicate option ID.

### Pass 3: Low-Risk Workbook Structure Cleanup

Task risk: Low to Medium.

1. Remove generator section display-order overrides.

   Files/sheets: `scripts/generate_stingray_form.py`, `section_master`

   Move Stingray-only display-order override values into workbook-authored section ordering only if the shared section order is correct for both models. If Stingray and Grand Sport need different order, use a model-scoped section ordering surface consistent across models instead of forcing one global `section_master.display_order`.

2. Remove section-step fallback/heuristic behavior where workbook already has `step_key`.

   Files/sheets: `scripts/corvette_form_generator/mapping.py`, `scripts/corvette_form_generator/model_configs.py`, `section_master`

   Make `section_master.step_key` authoritative; validation should fail on missing mappings instead of guessing. Verify this is still needed, because tests already assert the `section_master` step-key contract.

3. Move Grand Sport section label overrides to workbook only if they remain code-owned.

   Files/sheets: `scripts/corvette_form_generator/model_configs.py`, `section_master` or model-scoped section sheet

   Replace `GRAND_SPORT_SECTION_LABEL_OVERRIDES` with workbook-authored names only after verifying the current code still owns those labels and no existing workbook column already does.

4. Preserve `sec_exte_001` as a multi-select section.

   Files/sheets: `section_master`, `exclusive_groups`, `exclusive_group_members`, `grandSport_exclusive_groups`, `grandSport_exclusive_members`

   Do not change shared `sec_exte_001.selection_mode` to single-select. If any copy or UI affordance is confusing, fix it through generic exclusive-group awareness or copy, not a shared section-mode change.

### Pass 4: Low-Risk Text / Description Overrides

Task risk: Low.

1. Remove Grand Sport text cleanup and exact replacements only if still present.

   Files/sheets: `scripts/corvette_form_generator/inspection.py`, `grandSport_options`

   Correct workbook `option_name` / `description` values directly instead of mutating strings in code.

2. Move generated color override notes/reasons into workbook.

   Files/sheets: `scripts/generate_stingray_form.py`, `scripts/corvette_form_generator/inspection.py`, `color_overrides`

   Add workbook columns only if the current shared/model-specific color override contract cannot already carry the notes.

### Pass 5: Medium-Risk Visibility / Availability Fixes

Task risk: Medium.

1. Replace `HIDDEN_SECTION_IDS` with workbook-authored visibility.

   Files/sheets: `scripts/generate_stingray_form.py`, `stingray_options`, maybe `section_master`

   Rows in `sec_cust_002` are currently active/selectable in workbook but hidden by code. Decide whether each row should be inactive, hidden, component-only, or visible.

2. Replace `opt_uqt_002` hardcoded availability override as part of duplicate-RPO cleanup.

   Files/sheets: `scripts/generate_stingray_form.py`, `stingray_options`, `stingray_ovs`, optional shared/model-scoped variant override sheet

   Do not preserve an option-specific code branch. If needed, use the same variant-scoped selectability/display pattern Grand Sport uses.

### Pass 6: High-Risk Runtime Defaults / Replacement Rules

Task risk: High, standalone pass.

1. Move hardcoded default selections out of JS.

   Files/sheets: `form-app/app.js`, `stingray_options`, possibly existing rule/default structures

   Rules: `FE1`, `NGA`, `BC7`, `719`.

2. Move hardcoded replacement/removal behavior out of JS.

   Files/sheets: `form-app/app.js`, `rule_mapping`, `rule_groups`, `exclusive_groups`

   Rules: `Z51 -> FE1/FE2`, `NWI -> NGA`, `GBA -> ZYC`, special `GBA/ZYC` exception.

   Confirm existing `rule_mapping` coverage first, then migrate one branch at a time to `runtime_action=replace` rows with workbook-authored `disabled_reason`.

This pass can change actual selection behavior and should have focused regression tests before implementation.

### Pass 7: High-Risk Interior Component / R6X Pricing

Task risk: High, standalone pass.

1. Move interior component metadata to workbook.

   Files/sheets: `scripts/generate_stingray_form.py`, `scripts/corvette_form_generator/inspection.py`, `lt_interiors`, `PriceRef`, maybe `interior_components`

   Current code authors labels/types for `R6X`, `36S`, `37S`, `38S`, `N26`, `N2Z`, `TU7`.

2. Move generated R6X include rules to workbook.

   Files/sheets: `scripts/generate_stingray_form.py`, `rule_mapping`, `lt_interiors`

   Current code creates interior-to-`opt_r6x_001` include rules.

3. Replace JS D30/R6X zero-price branch with workbook price rule.

   Files/sheets: `form-app/app.js`, `price_rules`, maybe component price rules sheet

   Current branch: R6X component price becomes `0` when `opt_d30_001` is auto-added. Existing `price_rules` only covers option-level pricing cleanly. Do not force component pricing into that sheet unless the target contract can represent interior component IDs and selected-interior context.

### Pass 8: Medium-Risk Summary / Export Grouping

Task risk: Medium.

1. Move order summary grouping out of JS maps.

   Files/sheets: `form-app/app.js`, generated JSON, workbook/generated sheet such as `form_order_sections`

   Current JS maps steps to labels like `Performance & Mechanical`, `Seats & Interior`, `Auto-Added / Required`.

### Pass 9: Audit-Only Rule Parser Cleanup

Task risk: Low if kept audit-only, Medium if removed.

1. Move special audit buckets into workbook tags/groups only if still code-owned.

   Files/sheets: `scripts/build_grand_sport_rule_sources.py`, new workbook tag/group sheet only if no existing rule metadata can carry the audit tag

   `ENGINE_COVER_RPOS` and special review RPOs should be workbook-authored audit metadata if they remain active.

2. Keep phrase parsing audit-only.

   Files/sheets: `scripts/build_grand_sport_rule_sources.py`

   Do not make parsed rules authoritative. Runtime should consume workbook-authored `rule_mapping` / `grandSport_rule_mapping`.

## Suggested Order

1. Pass 1: Source contract alignment and diagnosis refresh.
2. Pass 2: Duplicate RPO deactivation plan.
3. Pass 3: Low-risk workbook structure cleanup.
4. Pass 4: Text / description overrides.
5. Pass 8: Summary / export grouping.
6. Pass 5: Visibility / availability fixes.
7. Pass 6 alone: runtime defaults / replacement rules.
8. Pass 7 alone: interior component / R6X pricing.
9. Pass 9 whenever convenient.

For each implementation pass, write a short pass-specific spec first. Do not run generators or mutate the workbook until that pass is approved.

Minimum validation after approved implementation that changes Stingray generated data:

```sh
.venv/bin/python scripts/generate_stingray_form.py
node --test tests/stingray-form-regression.test.mjs
node --test tests/stingray-generator-stability.test.mjs
```

If a pass changes shared model contracts or app registry behavior, also run:

```sh
node --test tests/grand-sport-draft-data.test.mjs
node --test tests/multi-model-runtime-switching.test.mjs
```
