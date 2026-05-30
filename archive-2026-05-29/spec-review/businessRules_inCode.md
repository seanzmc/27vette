# Business Rules in Code

## Task given

Review active JavaScript + Python scripts + runtime files in `/Users/seandm/Projects/27vette`.

Goal: find business rules still hardcoded in code, not served by workbook.

Scope:

- Focus hardcoded mapping logic.
- Ignore `/archive` and `/archived`.
- Report-only. No edits.

For each found rule:

- Give file path + line number.
- Suggest Excel/workbook table schema to replace hardcode.
- Present as bullets.

I inspected `scripts/**/*.py`, `form-app/app.js`, generated `form-app/data.js` for context, and workbook sheet headers.

## **Findings**

- Hardcoded step order, labels, and section-to-step mapping: [model_configs.py](/Users/seandm/Projects/27vette/scripts/corvette_form_generator/model_configs.py:29), [model_configs.py](/Users/seandm/Projects/27vette/scripts/corvette_form_generator/model_configs.py:91), [mapping.py](/Users/seandm/Projects/27vette/scripts/corvette_form_generator/mapping.py:43).  
  Suggested schema: `runtime_steps(model_key, step_key, step_label, runtime_order, active)` and `section_step_map(model_key, section_id, step_key, active, notes)`. Existing `section_master.step_key` could absorb most of this.

- Hardcoded “standard equipment section” bucket: [model_configs.py](/Users/seandm/Projects/27vette/scripts/corvette_form_generator/model_configs.py:130), [mapping.py](/Users/seandm/Projects/27vette/scripts/corvette_form_generator/mapping.py:55).  
  Suggested schema: add `section_master.standard_equipment_bucket` or create `section_presentation(model_key, section_id, presentation_bucket, active)`.

- Hardcoded body-style ordering: [model_configs.py](/Users/seandm/Projects/27vette/scripts/corvette_form_generator/model_configs.py:118), [generate_stingray_form.py](/Users/seandm/Projects/27vette/scripts/generate_stingray_form.py:687).  
  Suggested schema: `body_style_master(model_key, body_style, label, display_order, active)`.

- Hardcoded synthetic body/trim context sections: [model_configs.py](/Users/seandm/Projects/27vette/scripts/corvette_form_generator/model_configs.py:64), [generate_stingray_form.py](/Users/seandm/Projects/27vette/scripts/generate_stingray_form.py:648), [inspection.py](/Users/seandm/Projects/27vette/scripts/corvette_form_generator/inspection.py:1177), [form-app/app.js](/Users/seandm/Projects/27vette/form-app/app.js:1463).  
  Suggested schema: `context_section_master(model_key, context_type, section_id, section_name, selection_mode, step_key, display_order, active)`.

- Hardcoded Grand Sport section label overrides: [model_configs.py](/Users/seandm/Projects/27vette/scripts/corvette_form_generator/model_configs.py:143).  
  Suggested schema: `section_label_overrides(model_key, section_id, display_label, active, notes)`.

- Hardcoded model-to-sheet and variant-id mapping: [model_configs.py](/Users/seandm/Projects/27vette/scripts/corvette_form_generator/model_configs.py:150), [model_configs.py](/Users/seandm/Projects/27vette/scripts/corvette_form_generator/model_configs.py:174).  
  Suggested schema: `model_master(model_key, model_label, model_year, dataset_name, active)` and `model_workbook_sources(model_key, source_role, sheet_name)`, plus `model_variants(model_key, variant_id, display_order, active)`.

- Hardcoded hidden section behavior for `sec_cust_002`: [generate_stingray_form.py](/Users/seandm/Projects/27vette/scripts/generate_stingray_form.py:42), [generate_stingray_form.py](/Users/seandm/Projects/27vette/scripts/generate_stingray_form.py:628).  
  Suggested schema: add `section_master.display_behavior` or `section_runtime_flags(model_key, section_id, display_behavior, active)`.

- Hardcoded Stingray section display-order overrides: [generate_stingray_form.py](/Users/seandm/Projects/27vette/scripts/generate_stingray_form.py:196), [generate_stingray_form.py](/Users/seandm/Projects/27vette/scripts/generate_stingray_form.py:652).  
  Suggested schema: use `section_master.display_order` directly or add `section_display_overrides(model_key, section_id, display_order, active)`.

- Hardcoded option availability rule for `opt_uqt_002` only on `1LT`: [generate_stingray_form.py](/Users/seandm/Projects/27vette/scripts/generate_stingray_form.py:783).  
  Suggested schema: represent in `stingray_ovs(option_id, variant_id, status)` or a generic `variant_option_overrides(option_id, variant_id, status, selectable, active, note)`.

- Hardcoded interior component RPO decomposition and labels: [generate_stingray_form.py](/Users/seandm/Projects/27vette/scripts/generate_stingray_form.py:365), [generate_stingray_form.py](/Users/seandm/Projects/27vette/scripts/generate_stingray_form.py:386), [inspection.py](/Users/seandm/Projects/27vette/scripts/corvette_form_generator/inspection.py:37), [inspection.py](/Users/seandm/Projects/27vette/scripts/corvette_form_generator/inspection.py:291).  
  Suggested schema: `interior_components(interior_id, rpo, component_type, label, price_ref_type, price_ref_code, price_trim_scope, display_order, active)`.

- Hardcoded R6X included-option fallback and generated manual rule: [generate_stingray_form.py](/Users/seandm/Projects/27vette/scripts/generate_stingray_form.py:836), [generate_stingray_form.py](/Users/seandm/Projects/27vette/scripts/generate_stingray_form.py:949).  
  Suggested schema: keep `lt_interiors.included_option_id` mandatory for these rows, or move the relationship to `rule_mapping(rule_id, source_id, source_type, rule_type, target_id, target_type, source_section, target_section, disabled_reason, active)`.

- Hardcoded standard-equipment dedupe preference around `_001` and `sec_stan_002`: [generate_stingray_form.py](/Users/seandm/Projects/27vette/scripts/generate_stingray_form.py:539).  
  Suggested schema: `standard_equipment_priority(model_key, section_id, canonical_rank, duplicate_group_key, active)` or add `standard_equipment_rank` / `canonical_preference` to source option rows.

- Hardcoded Grand Sport interior trim scope and Z25 derivation: [inspection.py](/Users/seandm/Projects/27vette/scripts/corvette_form_generator/inspection.py:431), [inspection.py](/Users/seandm/Projects/27vette/scripts/corvette_form_generator/inspection.py:453).  
  Suggested schema: `model_interior_scope(model_key, interior_id, trim_level, active, requires_option_id, notes)`.

- Hardcoded rule-text phrase mapping in the Grand Sport audit parser: [build_grand_sport_rule_sources.py](/Users/seandm/Projects/27vette/scripts/build_grand_sport_rule_sources.py:50), [build_grand_sport_rule_sources.py](/Users/seandm/Projects/27vette/scripts/build_grand_sport_rule_sources.py:213).  
  Suggested schema: `rule_phrase_map(phrase, rule_type, direction, stop_phrases, review_flag_default, active)`.

- Hardcoded engine-cover RPO audit group: [build_grand_sport_rule_sources.py](/Users/seandm/Projects/27vette/scripts/build_grand_sport_rule_sources.py:58), [build_grand_sport_rule_sources.py](/Users/seandm/Projects/27vette/scripts/build_grand_sport_rule_sources.py:471).  
  Suggested schema: `option_audit_groups(group_id, group_label, active)` and `option_audit_group_members(group_id, rpo, option_id, active)`.

- Hardcoded special review RPOs: [inspection.py](/Users/seandm/Projects/27vette/scripts/corvette_form_generator/inspection.py:36), [model_configs.py](/Users/seandm/Projects/27vette/scripts/corvette_form_generator/model_configs.py:213), [build_grand_sport_rule_sources.py](/Users/seandm/Projects/27vette/scripts/build_grand_sport_rule_sources.py:597).  
  Suggested schema: `rule_review_groups(model_key, group_id, rpo, review_reason, active)`.

- Hardcoded runtime order-summary grouping: [form-app/app.js](/Users/seandm/Projects/27vette/form-app/app.js:113), [form-app/app.js](/Users/seandm/Projects/27vette/form-app/app.js:128), [form-app/app.js](/Users/seandm/Projects/27vette/form-app/app.js:1667).  
  Suggested schema: `order_summary_sections(model_key, section_key, section_label, display_order, active)` and `step_order_summary_map(model_key, step_key, section_key, active)`.

- Hardcoded runtime RPO conflicts/replacements/defaults: [form-app/app.js](/Users/seandm/Projects/27vette/form-app/app.js:613), [form-app/app.js](/Users/seandm/Projects/27vette/form-app/app.js:853), [form-app/app.js](/Users/seandm/Projects/27vette/form-app/app.js:1014), [form-app/app.js](/Users/seandm/Projects/27vette/form-app/app.js:1040), [form-app/app.js](/Users/seandm/Projects/27vette/form-app/app.js:1096).  
  Suggested schema: use `rule_mapping` for replaces/excludes, plus `default_selection_rules(model_key, condition_type, condition_id, target_option_id, body_style_scope, trim_level_scope, priority, active)`.

- Hardcoded runtime price waiver for R6X when `opt_d30_001` is auto-added: [form-app/app.js](/Users/seandm/Projects/27vette/form-app/app.js:738).  
  Suggested schema: `price_rules(price_rule_id, condition_option_id, price_rule_type, target_option_id, target_component_rpo, price_value, body_style_scope, trim_level_scope, variant_scope, active)`.

- Hardcoded trim-equipment grouping by section name regex: [form-app/app.js](/Users/seandm/Projects/27vette/form-app/app.js:1391).  
  Suggested schema: add `standard_equipment_group_type` to `section_master` or create `standard_equipment_groups(model_key, section_id, group_type, default_open, active)`.
