# Workbook Structure Cleanup

Objective: move Corvette business rules out of generator/runtime code and back into workbook-authored source sheets wherever practical. Priority areas are UI visibility, price calculations, and dependency mapping.

## Current Findings

### UI Visibility / Selection Semantics

1. `sec_exte_001` has conflicting source semantics.

   The workbook now correctly authors the Stingray exterior accents radio-button behavior through `exclusive_groups` / `exclusive_group_members`:

   ```text
   exclusive_groups.excl_ext_accents
   selection_mode = single_within_group
   members = opt_efr_001 | opt_efy_001 | opt_edu_001
   ```

   Runtime behavior is already generic and workbook-driven:

   ```js
   function removeOtherExclusiveGroupOptions(optionId) {
     const group = optionExclusiveGroup(optionId);
     if (!group || group.selection_mode !== "single_within_group") return;
     for (const id of group.option_ids || []) {
       if (id !== optionId) deleteSelectedOption(id);
     }
   }
   ```

   Conflict to review: `section_master` still describes `sec_exte_001` as `selection_mode=multi_select_opt`, so the generated UI labels it as optional multiple choice even though the exclusive group makes it behave like a radio group. Decide whether section-level `selection_mode` should be changed to `single_select_req` / `single_select_opt`, or whether exclusive-group copy should override the displayed selection-mode label.

2. Hidden sections are still code-owned.

   File: `scripts/generate_stingray_form.py`

   ```python
   HIDDEN_SECTION_IDS = {"sec_cust_002"}
   ...
   if display_behavior == "hidden" or option.get("section_id") in HIDDEN_SECTION_IDS:
       option["active"] = "False"
   ```

   Proposed workbook source: `section_master` or option rows should carry the visibility decision. The current `display_behavior=hidden` option-level mechanism exists, but section-level hiding is still hardcoded.

3. UQT visibility is still code-owned.

   File: `scripts/generate_stingray_form.py`

   ```python
   if option_id == "opt_uqt_002" and variant["trim_level"] != "1LT":
       status = "unavailable"
       selectable = "False"
       active = "False"
   ```

   Conflict to review: `stingray_ovs` says `opt_uqt_002` is `standard` for 2LT/3LT, while generator code suppresses that selectable row outside 1LT. If 2LT/3LT should receive UQT only through the standard-equipment row, encode that explicitly in workbook data instead of this option-id branch.

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

   Proposed workbook source: option-level `display_behavior=default_selected` is already supported and should become the only default-selection mechanism, with any conditional default scope represented in workbook rows/rules.

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

   Proposed workbook source: model this as a workbook-authored component price rule or interior price rule. The existing `price_rules` sheet handles option-level overrides, but component-level pricing may need a scoped sheet.

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

   Proposed workbook source: add component metadata to `PriceRef`, `lt_interiors`, or a dedicated `interior_components` sheet.

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

   Proposed workbook source: `rule_mapping` rows with `runtime_action=replace`, `disabled_reason`, and correct source/target section metadata. The runtime already has generic `removeReplaceRuleTargets()` support; these branches should be migrated to data if the existing rule rows are complete enough.

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

### Already Workbook-Driven / Do Not Refactor as Business Logic

1. Generic exclusive-group runtime behavior is already data-driven.

   Files/sheets: `exclusive_groups`, `exclusive_group_members`, `form-app/app.js`

   Do not replace this with section-specific JS. The correct cleanup is to align section metadata/copy with exclusive-group behavior.

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

   Files/sheets: `rule_groups`, `rule_group_members`, `form-app/app.js`

   The cleanup target is RPO-specific branches, not the generic rule-group mechanism.

## Recommended Implementation Order

**Pass 1: Low-Risk Workbook Structure Cleanup**
Task risk: Low to Medium

1. Remove generator section display-order overrides  
   Files/sheets: `scripts/generate_stingray_form.py`, `section_master`  
   Risk: Low  
   Move `STINGRAY_SECTION_DISPLAY_ORDER_OVERRIDES` into workbook-authored section ordering.
   Review needed: current `section_master` gives `sec_gsha_001=10` and `sec_gsce_001=20`, but Stingray code overrides them to `50` and `51`. If Stingray and Grand Sport need different order, add model-scoped section ordering instead of forcing one global `section_master.display_order`.

2. Remove section-step fallback/heuristic behavior where workbook already has `step_key`  
   Files/sheets: `scripts/corvette_form_generator/mapping.py`, `scripts/corvette_form_generator/model_configs.py`, `section_master`  
   Risk: Medium  
   Make `section_master.step_key` authoritative; validation should fail on missing mappings instead of guessing.

3. Move Grand Sport section label overrides to workbook  
   Files/sheets: `scripts/corvette_form_generator/model_configs.py`, `section_master` or model-scoped section sheet  
   Risk: Low  
   Replace `GRAND_SPORT_SECTION_LABEL_OVERRIDES` with workbook-authored names.

4. Align `sec_exte_001` section metadata with exclusive-group behavior  
   Files/sheets: `section_master`, `exclusive_groups`, `exclusive_group_members`, generated tests  
   Risk: Low to Medium  
   `excl_ext_accents` is correctly workbook-authored, but `sec_exte_001.selection_mode=multi_select_opt` conflicts with the single-choice behavior. Decide whether to change the section selection mode or add UI copy driven by exclusive-group membership.

**Pass 2: Low-Risk Text / Description Overrides**
Task risk: Low

1. Remove Grand Sport text cleanup and exact replacements  
   Files/sheets: `scripts/corvette_form_generator/inspection.py`, `grandSport_options`  
   Risk: Low  
   Correct workbook `option_name` / `description` values directly instead of mutating strings in code.

2. Move generated color override notes/reasons into workbook  
   Files/sheets: `scripts/generate_stingray_form.py`, `scripts/corvette_form_generator/inspection.py`, `color_overrides`  
   Risk: Low  
   Add workbook columns like `notes`, `auto_add_reason`, or `disabled_reason`.

**Pass 3: Medium-Risk Visibility / Availability Fixes**
Task risk: Medium

1. Replace `HIDDEN_SECTION_IDS` with workbook-authored visibility  
   Files/sheets: `scripts/generate_stingray_form.py`, `stingray_options`, maybe `section_master`  
   Risk: Medium  
   Rows in `sec_cust_002` are currently active/selectable in workbook but hidden by code. Decide whether each row should be inactive, hidden, or visible.

2. Replace `opt_uqt_002` hardcoded availability override  
   Files/sheets: `scripts/generate_stingray_form.py`, `stingray_ovs` or new `stingray_variant_overrides`  
   Risk: Medium  
   The workbook currently says UQT is standard on 2LT/3LT, while code forces it unavailable outside 1LT. This needs source-of-truth confirmation before changing.

**Pass 4: High-Risk Runtime Defaults / Replacement Rules**
Task risk: High, standalone pass

1. Move hardcoded default selections out of JS  
   Files/sheets: `form-app/app.js`, `stingray_options`, possibly new default-scope sheet  
   Risk: High  
   Rules: `FE1`, `NGA`, `BC7`, `719`.

2. Move hardcoded replacement/removal behavior out of JS  
   Files/sheets: `form-app/app.js`, `rule_mapping`, `rule_groups`, `exclusive_groups`  
   Risk: High  
   Rules: `Z51 -> FE1/FE2`, `NWI -> NGA`, `GBA -> ZYC`, special `GBA/ZYC` exception.
   Confirm existing `rule_mapping` coverage first, then migrate one branch at a time to `runtime_action=replace` rows with workbook-authored `disabled_reason`.

This pass can change actual selection behavior and should have focused regression tests before implementation.

**Pass 5: High-Risk Interior Component / R6X Pricing**
Task risk: High, standalone pass

1. Move interior component metadata to workbook  
   Files/sheets: `scripts/generate_stingray_form.py`, `scripts/corvette_form_generator/inspection.py`, `lt_interiors`, `PriceRef`, new `interior_components` sheet  
   Risk: High  
   Current code authors labels/types for `R6X`, `36S`, `37S`, `38S`, `N26`, `N2Z`, `TU7`.

2. Move generated R6X include rules to workbook  
   Files/sheets: `scripts/generate_stingray_form.py`, `rule_mapping`, `lt_interiors`  
   Risk: High  
   Current code creates interior-to-`opt_r6x_001` include rules.

3. Replace JS D30/R6X zero-price branch with workbook price rule  
   Files/sheets: `form-app/app.js`, `price_rules`, maybe component price rules sheet  
   Risk: High  
   Current branch: R6X component price becomes `0` when `opt_d30_001` is auto-added.
   Existing `price_rules` only covers option-level pricing cleanly. Do not force component pricing into that sheet unless the target contract can represent interior component IDs and selected-interior context.

**Pass 6: Medium-Risk Summary / Export Grouping**
Task risk: Medium

1. Move order summary grouping out of JS maps  
   Files/sheets: `form-app/app.js`, generated JSON, workbook/generated sheet such as `form_order_sections`  
   Risk: Medium  
   Current JS maps steps to labels like `Performance & Mechanical`, `Seats & Interior`, `Auto-Added / Required`.

**Pass 7: Audit-Only Rule Parser Cleanup**
Task risk: Low if kept audit-only, Medium if removed

1. Move special audit buckets into workbook tags/groups  
   Files/sheets: `scripts/build_grand_sport_rule_sources.py`, new workbook tag/group sheet  
   Risk: Low  
   `ENGINE_COVER_RPOS` and special review RPOs should be workbook-authored audit metadata.

2. Keep phrase parsing audit-only  
   Files/sheets: `scripts/build_grand_sport_rule_sources.py`  
   Risk: Medium if changed  
   Do not make parsed rules authoritative. Runtime should consume workbook-authored `rule_mapping`.

**Suggested Order**

1. Pass 1
2. Pass 2
3. Pass 6
4. Pass 3
5. Pass 4 alone
6. Pass 5 alone
7. Pass 7 whenever convenient

For each implementation pass, I’d write a short spec first, then run `.venv/bin/python scripts/generate_stingray_form.py` and `node --test tests/stingray-form-regression.test.mjs` after changes.
