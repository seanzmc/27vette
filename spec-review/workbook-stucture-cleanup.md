Recommended implementation order:

**Pass 1: Low-Risk Workbook Structure Cleanup**
Task risk: Low to Medium

1. Remove generator section display-order overrides  
   Files/sheets: `scripts/generate_stingray_form.py`, `section_master`  
   Risk: Low  
   Move `STINGRAY_SECTION_DISPLAY_ORDER_OVERRIDES` into `section_master.display_order`.

2. Remove section-step fallback/heuristic behavior where workbook already has `step_key`  
   Files/sheets: `scripts/corvette_form_generator/mapping.py`, `scripts/corvette_form_generator/model_configs.py`, `section_master`  
   Risk: Medium  
   Make `section_master.step_key` authoritative; validation should fail on missing mappings instead of guessing.

3. Move Grand Sport section label overrides to workbook  
   Files/sheets: `scripts/corvette_form_generator/model_configs.py`, `section_master` or model-scoped section sheet  
   Risk: Low  
   Replace `GRAND_SPORT_SECTION_LABEL_OVERRIDES` with workbook-authored names.

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
