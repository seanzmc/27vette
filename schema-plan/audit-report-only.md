Report-only audit complete. I did not edit stingray*master.xlsx, generated form*_ sheets, form-output/_, form-app/data.js, generator/runtime files, tests, docs, or other project artifacts.

    Inspection used read-only workbook loading through .venv Python/openpyxl, file search/read-only code inspection, and JSON artifact reads.

    Working tree note:
    - git status showed existing untracked files:
      - spec-review/codex.md
      - spec-review/hermes.md
    - I did not create or modify them.
    - Workbook lock check: ./~$stingray_master.xlsx was absent.

    1. Executive summary

    Highest-impact findings:

    1. Most primary Stingray/Grand Sport source-sheet schemas are now header-compatible.
       - stingray_options vs grandSport_options: identical 11 headers.
       - stingray_ovs vs grandSport_ovs: identical 3 headers.
       - rule_mapping vs grandSport_rule_mapping: identical populated 16-header contract.
       - price_rules vs grandSport_price_rules: identical 9 headers.
       - rule_groups / rule_group_members / exclusive_groups / exclusive members: structurally aligned.
       - This is good for repeatable workbook-owned ingestion.

    2. The largest remaining drift is not header drift; it is value-shape drift.
       - Grand Sport boolean-like fields often use strings: "TRUE", "FALSE", "False", "True".
       - Stingray equivalent fields are often real Excel booleans.
       - Examples:
         - stingray_options.selectable: 270 bool values.
         - grandSport_options.selectable: 256 strings + 10 bools.
         - rule_mapping.review_flag: Stingray bool False; Grand Sport string "False".
         - price_rules.review_flag: Stingray bool False; Grand Sport mixed string/bool.
       - Classification: needs human review / harmless in current generator if normalized, but risky for NoSQL/JSON ingestion.

    3. Rule-path divergence is intentional in several Grand Sport areas.
       - Grand Sport uses grouped omissions and workbook-owned normalization more heavily:
         - grandSport_rule_mapping.generation_action has 114 populated rows, including omit_grouped_exclusion, omit_replaced_by_d3v_include, omit_soft_defaulted_caliper, preserve_runtime_exclude.
         - Stingray rule_mapping.generation_action has only 6 populated rows, all omit_grouped_requirement.
       - This appears to reflect Grand Sport order-guide complexity and migration state, not necessarily defects.
       - Practical risk: ingestion must preserve both raw source evidence and normalized rule outputs.

    4. Grand Sport has an extra model-specific metadata sheet:
       - grandSport_variant_overrides
       - It carries per-variant default/display/selectability metadata such as opt_nga_001, opt_bc7_001, opt_uqt_001.
       - There is no direct Stingray equivalent among the listed Stingray sheets, though shared/modern metadata sheets such as variant_option_overrides/default_selection_rules exist elsewhere in the workbook.
       - Classification: likely intentional, but should be canonicalized before future online order-guide ingestion.

    5. Interior data is the biggest cross-model canonicalization issue.
       - Stingray source uses lt_interiors plus LZ_Interiors.
       - Grand Sport draft generation currently builds Grand Sport interiors from lt_interiors plus model_interior_scope/interior_components, not from a direct grandSport_interiors sheet.
       - lt_interiors and LZ_Interiors differ at header level:
         - lt_interiors has interior_id, Price, section_id, active_for_stingray, requires_r6x, included_option_id.
         - LZ_Interiors has ID and Cost, but lacks section_id, active_for_stingray, requires_r6x, included_option_id.
       - Generated form_interiors normalizes these into a JSON-ready shape with interior_components_json/interior_components and hierarchy metadata.
       - Classification: needs human review for canonical workbook pattern.

    6. category_master is listed in AGENTS.md/request as relevant, but the current workbook does not contain a live category_master sheet.
       - Workbook sheets include archive_category_master, not category_master.
       - Classification: needs human review / likely stale documentation or retired sheet.

    7. Generated/output evidence confirms converging runtime contracts but not identical artifact shapes.
       - Stingray JSON: form-output/stingray-form-data.json.
       - Grand Sport draft JSON: form-output/inspection/grand-sport-form-data-draft.json.
       - Both have dataset, variants, steps, sections, contextChoices, choices, standardEquipment, ruleGroups, exclusiveGroups, rules, priceRules, interiors, colorOverrides, validation.
       - Grand Sport draft adds draftMetadata and extra per-choice source fields: source_option_name, source_description, text_cleanup_notes.
       - Classification: likely intentional migration/inspection metadata; should not become the permanent runtime contract unless approved.

    Recommended canonical workbook patterns:

    - Keep equivalent source sheets header-identical where possible.
    - Use lowercase snake_case field names in canonical ingestion schemas.
    - Normalize booleans to real booleans or canonical TRUE/FALSE, not mixed strings.
    - Normalize prices to numeric values; blanks mean null/not-priced, not zero.
    - Preserve raw order-guide text in source_detail_raw/detail_raw but put rules in normalized relationship sheets.
    - Prefer member-table patterns for lists:
      - rule_groups + rule_group_members
      - exclusive_groups + exclusive_group_members
      - color_overrides as row-per-link
      - interior_components as row-per-component
    - Avoid pipe/comma-delimited list values in future canonical sources except as preserved raw evidence.
    - Treat generated form_* and JSON as contract evidence only, not source of truth.

    2. Scope and methodology

    Inspected workbook sheets, read-only:

    Primary Stingray source sheets:
    - stingray_options
    - stingray_ovs
    - rule_mapping
    - price_rules
    - rule_groups
    - rule_group_members
    - exclusive_groups
    - exclusive_group_members
    - color_overrides
    - lt_interiors
    - LZ_Interiors

    Primary Grand Sport source sheets:
    - grandSport_options
    - grandSport_ovs
    - grandSport_rule_mapping
    - grandSport_price_rules
    - grandSport_rule_groups
    - grandSport_rule_group_members
    - grandSport_exclusive_groups
    - grandSport_exclusive_members
    - grandSport_variant_overrides

    Shared/reference sheets:
    - variant_master
    - section_master
    - PriceRef
    - category_master requested, but not present in current workbook; archive_category_master exists.

    Generated sheets inspected only as downstream evidence:
    - form_steps
    - form_context_choices
    - form_choices
    - form_standard_equipment
    - form_rule_groups
    - form_exclusive_groups
    - form_rules
    - form_price_rules
    - form_interiors
    - form_color_overrides
    - form_validation

    Generated artifacts inspected only as downstream evidence:
    - form-output/stingray-form-data.json
    - form-output/inspection/grand-sport-form-data-draft.json
    - form-output/inspection/grand-sport-contract-preview.json
    - form-output/inspection/grand-sport-rule-audit.json
    - form-app/data.js was located but not materially inspected beyond being an allowed downstream contract target.

    Generator/code paths inspected read-only:
    - scripts/corvette_form_generator/model_config.py
    - scripts/corvette_form_generator/model_configs.py
    - scripts/corvette_form_generator/inspection.py
    - scripts/generate_stingray_form.py
    - scripts/build_grand_sport_rule_sources.py references via search

    Important contract evidence:
    - ModelConfig default sheet names in scripts/corvette_form_generator/model_config.py:
      - rule_mapping_sheet="rule_mapping"
      - price_rules_sheet="price_rules"
      - rule_groups_sheet="rule_groups"
      - rule_group_members_sheet="rule_group_members"
      - exclusive_groups_sheet="exclusive_groups"
      - exclusive_group_members_sheet="exclusive_group_members"
      - color_overrides_sheet="color_overrides"
      - variant_option_overrides_sheet=""
    - Grand Sport overrides in scripts/corvette_form_generator/model_configs.py lines 199-205:
      - rule_mapping_sheet="grandSport_rule_mapping"
      - price_rules_sheet="grandSport_price_rules"
      - rule_groups_sheet="grandSport_rule_groups"
      - rule_group_members_sheet="grandSport_rule_group_members"
      - exclusive_groups_sheet="grandSport_exclusive_groups"
      - exclusive_group_members_sheet="grandSport_exclusive_members"
      - variant_option_overrides_sheet="grandSport_variant_overrides"

    Generated sheets and JSON were used only to verify downstream contract shape and generated impact.

    3. Sheet-pair comparison matrix

    A. stingray_options vs grandSport_options

    Role:
    - Workbook-authored option catalog rows.

    Shared key columns:
    - option_id
    - rpo
    - section_id
    - display_order
    - active

    Headers:
    - Compatible. Both have:
      option_id, rpo, price, option_name, description, detail_raw, section_id, selectable, display_order, active, display_behavior

    Data-shape compatibility:
    - Medium drift.
    - Stingray selectable is bool.
    - Grand Sport selectable is mixed string/bool.
    - RPO has numeric-looking values stored as ints in both sheets for 719 and 379 examples.
    - Price blanks are common in both and should mean null/not-priced, not zero.

    Rule/relationship compatibility:
    - Compatible at sheet level, but duplicate RPOs require option_id as primary key.
    - Examples:
      - Stingray duplicate RPO 719: opt_719_001 row 108 active, opt_719_002 row 259 inactive.
      - Grand Sport duplicate RPO 719: opt_719_001 row 174 active, opt_719_002 row 228 inactive.
      - Grand Sport duplicate RPO AQ9 spans inactive/active option IDs.

    Risk:
    - Medium for ingestion.

    Notes:
    - Header pattern is good.
    - Value normalization needed before NoSQL/JSON conversion.

    B. stingray_ovs vs grandSport_ovs

    Role:
    - Option/variant/status availability matrix.

    Shared key columns:
    - option_id
    - variant_id
    - status

    Headers:
    - Compatible. Both have option_id, variant_id, status.

    Data-shape compatibility:
    - Strong.
    - Stingray statuses:
      - available 891
      - standard 525
      - unavailable 204
    - Grand Sport statuses:
      - available 861
      - standard 547
      - unavailable 188

    Rule/relationship compatibility:
    - Strong.
    - Variant IDs intentionally differ:
      - Stingray: 1lt_c07, 2lt_c07, 3lt_c07, 1lt_c67, 2lt_c67, 3lt_c67
      - Grand Sport: 1lt_e07, 2lt_e07, 3lt_e07, 1lt_e67, 2lt_e67, 3lt_e67

    Risk:
    - Low.

    Notes:
    - This is one of the best repeatable ingestion candidates.

    C. rule_mapping vs grandSport_rule_mapping

    Role:
    - Normalized compatibility/dependency rules.

    Shared key columns:
    - rule_id
    - source_id
    - rule_type
    - target_id
    - target_type

    Headers:
    - Compatible. Both have the same populated 16 fields:
      rule_id, source_id, rule_type, target_id, target_type, original_detail_raw, review_flag, source_type, target_selection_mode, source_selection_mode, target_section, source_section, generation_action, body_style_scope, runtime_action, disabled_reason

    Data-shape compatibility:
    - Medium drift.
    - Stingray review_flag is bool.
    - Grand Sport review_flag is string "False".
    - Stingray target_type values:
      - main 235
      - option 3
    - Grand Sport target_type:
      - option 321
    - Stingray source_type:
      - main 220
      - interior 15
      - option 3
    - Grand Sport source_type:
      - option 302
      - interior 19

    Rule/relationship compatibility:
    - Medium/high drift by path, not by schema.
    - Grand Sport uses generation_action heavily:
      - 114 populated generation_action rows.
      - Examples: omit_grouped_exclusion, omit_replaced_by_d3v_include, omit_soft_defaulted_caliper, omit_redundant_scoped_duplicate, preserve_runtime_exclude.
    - Stingray has only 6 generation_action rows, all omit_grouped_requirement.

    Risk:
    - Medium/high for ingestion if generation_action semantics are not canonicalized.

    Notes:
    - Schema is strong; semantics need a canonical rule-lifecycle model:
      source/raw, normalized, omitted, replaced_by_group, preserved_runtime.

    D. price_rules vs grandSport_price_rules

    Role:
    - Conditional price override rows.

    Shared key columns:
    - price_rule_id
    - condition_option_id
    - target_option_id

    Headers:
    - Compatible. Both have:
      price_rule_id, condition_option_id, price_rule_type, target_option_id, price_value, body_style_scope, trim_level_scope, review_flag, notes

    Data-shape compatibility:
    - Medium.
    - price_value is numeric int in both.
    - Grand Sport uses trim_level_scope in 4 rows; Stingray currently has none populated.
    - body_style_scope:
      - Stingray 6 populated rows.
      - Grand Sport 13 populated rows.
    - review_flag:
      - Stingray bool.
      - Grand Sport mixed string/bool.

    Rule/relationship compatibility:
    - Strong structure, but more Grand Sport scoping.

    Risk:
    - Medium.

    Notes:
    - Good canonical pattern: condition_option_id + target_option_id + price_rule_type + price_value + optional scopes.
    - Normalize review_flag.

    E. rule_groups vs grandSport_rule_groups

    Role:
    - Grouped dependency rules, such as requires_any/excludes_any.

    Shared key columns:
    - group_id
    - source_id
    - group_type

    Headers:
    - Compatible. Both have:
      group_id, group_type, source_id, body_style_scope, trim_level_scope, variant_scope, disabled_reason, active, notes

    Data-shape compatibility:
    - Strong header compatibility, semantic divergence.
    - Stingray:
      - 2 rows.
      - group_type requires_any only.
      - grp_5v7_spoiler_requirement
      - grp_5zu_paint_requirement
    - Grand Sport:
      - 1 row.
      - group_type excludes_any.
      - gs_group_z15_excludes_non_center_stripes

    Rule/relationship compatibility:
    - Different business paths:
      - Stingray uses grouped requirements.
      - Grand Sport uses grouped exclusion for Z15 non-center stripe conflicts.

    Risk:
    - Low/medium.
    - Pattern is good, but group_type taxonomy should be canonical.

    F. rule_group_members vs grandSport_rule_group_members

    Role:
    - Member rows for grouped dependency rules.

    Shared key columns:
    - group_id
    - target_id
    - display_order

    Headers:
    - Compatible. Both have:
      group_id, target_id, display_order, active

    Data-shape compatibility:
    - Strong.
    - active is string "True" in both.

    Rule/relationship compatibility:
    - Strong.
    - Stingray has 5 members.
    - Grand Sport has 18 members for gs_group_z15_excludes_non_center_stripes.

    Risk:
    - Low.

    Notes:
    - This is a strong canonical workbook-owned pattern.

    G. exclusive_groups vs grandSport_exclusive_groups

    Role:
    - Mutually exclusive option groups.

    Shared key columns:
    - group_id
    - selection_mode

    Headers:
    - Compatible. Both have:
      group_id, selection_mode, active, notes

    Data-shape compatibility:
    - Strong with active string values.
    - Stingray:
      - 7 rows, all active True.
      - selection_mode: single_within_group 6, required_single_within_group 1.
    - Grand Sport:
      - 10 rows, 9 active True, 1 active False.
      - selection_mode: single_within_group 7, required_single_within_group 3.

    Rule/relationship compatibility:
    - Strong.
    - Grand Sport includes intentionally inactive source retention:
      - gs_excl_exhaust_path active False, note: “Inactive: WUB does not replace NGA. NWI requires WUB and replaces/restores NGA through workbook rules/defaults.”

    Risk:
    - Low/medium.
    - Inactive rows should be supported explicitly in ingestion.

    H. exclusive_group_members vs grandSport_exclusive_members

    Role:
    - Member rows for mutually exclusive option groups.

    Shared key columns:
    - group_id
    - option_id
    - display_order

    Headers:
    - Compatible. Both have:
      group_id, option_id, display_order, active

    Data-shape compatibility:
    - Strong.
    - active is string True/False.

    Rule/relationship compatibility:
    - Strong.
    - Stingray 25 rows.
    - Grand Sport 27 rows.
    - Grand Sport has one inactive member aligned with inactive/excluded path retention.

    Risk:
    - Low.

    Notes:
    - Sheet name differs:
      - Stingray: exclusive_group_members
      - Grand Sport: grandSport_exclusive_members
    - Header contract is aligned.

    I. lt_interiors vs LZ_Interiors

    Role:
    - Interior source rows for LT and LZ families / model variants.

    Shared key columns:
    - Conceptually shared: trim, seat, interior code, material, suede, stitch, two tone, disclosure, color overrides.
    - Actual key names differ.

    Headers:
    - Drift.
    - lt_interiors:
      interior_id, Interior Name, Material, Price, Detail from Disclosure, Color Overrides, Trim, Seat, Interior Code, Suede, Stitch, Two Tone, section_id, active_for_stingray, requires_r6x, included_option_id
    - LZ_Interiors:
      Trim, Seat, Interior Code, Interior Name, Material, Suede, Stitch, Two Tone, Cost, Detail from Disclosure, Color Overrides, ID

    Data-shape compatibility:
    - Medium.
    - Price vs Cost.
    - interior_id vs ID.
    - lt_interiors has model/scope metadata; LZ_Interiors does not.
    - Prices in lt_interiors are strings in sample rows; LZ_Interiors Cost is numeric.

    Rule/relationship compatibility:
    - Medium/high drift.
    - Stingray generator reads both and normalizes into form_interiors.
    - Grand Sport build path reads lt_interiors plus model_interior_scope/interior_components and emits active_for_grand_sport/requires_z25 fields.

    Risk:
    - High for ingestion if left as two ad hoc interior shapes.

    Notes:
    - Should be canonicalized before future NoSQL/JSON structures.

    J. color_overrides

    Role:
    - Row-per-link color/interior override requirement.

    Equivalent Grand Sport source:
    - No model-specific grandSport_color_overrides listed.
    - Grand Sport draft uses shared color_overrides downstream.

    Headers:
    - color_overrides has:
      interior_id, option_id, rule_type, adds_rpo

    Data-shape compatibility:
    - Strong as relationship table.
    - 245 rows.
    - rule_type all requires.
    - adds_rpo all opt_d30_001.

    Risk:
    - Low structurally, medium semantically because lt_interiors/LZ_Interiors also have Color Overrides comma-delimited raw fields.

    Notes:
    - Prefer color_overrides as canonical normalized relationship table.
    - Preserve Color Overrides raw text as source evidence only.

    K. grandSport_variant_overrides

    Role:
    - Grand Sport-specific per-option/per-variant metadata overrides.

    Headers:
    - option_id, variant_id, selectable, display_behavior, section_id, active, note

    Representative rows:
    - opt_nga_001 variant 2lt_e07 selectable blank, display_behavior default_selected, active True, note “Default black exhaust tips; NGA is standard on Grand Sport.”
    - opt_uqt_001 2LT/3LT rows display_behavior display_only, section_id sec_2lte_001/sec_3lte_001, note “2LT included equipment.”
    - opt_bc7_001 default coupe black LS6 engine cover rows.

    Data-shape compatibility:
    - No listed Stingray source-sheet counterpart.
    - active is string True.
    - selectable uses string False in 4 rows, blanks elsewhere.
    - display_behavior has default_selected and display_only.

    Risk:
    - Medium/high.
    - Useful workbook-owned pattern, but it should either become a shared canonical variant_option_overrides pattern or remain explicitly model-scoped with documented semantics.

    4. Header discrepancy table

    1. category_master requested but missing

    Stingray/shared sheet/header:
    - category_master requested.

    Grand Sport/shared sheet/header:
    - Same requested shared sheet.

    Semantic concept:
    - Category reference/master metadata.

    Discrepancy type:
    - Missing live sheet.

    Classification:
    - Needs human review.

    Recommended canonical name:
    - category_master if still required; otherwise remove from active source graph documentation and rely on section_master/step metadata.

    Evidence:
    - Workbook sheet list contains archive_category_master, not category_master.
    - section_master is present and active.

    2. lt_interiors.Price vs LZ_Interiors.Cost

    Stingray sheet/header:
    - lt_interiors.Price

    Grand Sport / LZ-related sheet/header:
    - LZ_Interiors.Cost

    Semantic concept:
    - Interior base price/cost.

    Discrepancy type:
    - Semantically equivalent headers with different names.

    Classification:
    - Needs human review.

    Recommended canonical name:
    - price

    Evidence:
    - lt_interiors row 2: Price "1790" for 1LT_AE4_HTJ_N26.
    - LZ_Interiors row 5: Cost 1790 for 1LZ_AE4_HTJ_N26.

    3. lt_interiors.interior_id vs LZ_Interiors.ID

    Semantic concept:
    - Stable interior identifier.

    Discrepancy type:
    - Semantically equivalent headers with different names.

    Classification:
    - Needs human review.

    Recommended canonical name:
    - interior_id

    Evidence:
    - lt_interiors row 2: interior_id 1LT_AE4_HTJ_N26.
    - LZ_Interiors row 5: ID 1LZ_AE4_HTJ_N26.

    4. lt_interiors.Detail from Disclosure and option detail_raw/original_detail_raw

    Semantic concept:
    - Raw order-guide/source disclosure text.

    Discrepancy type:
    - Different naming pattern across sheet families.

    Classification:
    - Harmless drift in current generator; needs normalization for ingestion.

    Recommended canonical name:
    - source_detail_raw

    Evidence:
    - stingray_options.detail_raw.
    - grandSport_options.detail_raw.
    - rule_mapping.original_detail_raw.
    - lt_interiors.Detail from Disclosure.
    - Generated JSON choices use source_detail_raw.

    5. lt_interiors.Color Overrides vs color_overrides relationship table

    Semantic concept:
    - Interior/exterior color pairing override requirement.

    Discrepancy type:
    - Free-text/list-like source field vs normalized relationship rows.

    Classification:
    - Needs human review.

    Recommended canonical name:
    - Preserve color_overrides_raw for raw source.
    - Use color_overrides table as canonical normalized relationship.

    Evidence:
    - lt_interiors row 5 Color Overrides: “G26, G4Z, GBK, GPH”.
    - color_overrides rows 2-5 expand 1LT_AQ9_HUQ into opt_g26_001, opt_g4z_001, opt_gbk_001, opt_gph_001 requiring opt_d30_001.

    6. lt_interiors.active_for_stingray absent from LZ_Interiors

    Semantic concept:
    - Model-scoped interior activation.

    Discrepancy type:
    - Missing model-scope column in one interior source shape.

    Classification:
    - Needs human review / likely intentional legacy drift.

    Recommended canonical name:
    - active_for_model or separate model_interior_scope table.

    Evidence:
    - lt_interiors has active_for_stingray.
    - LZ_Interiors has no active_for_stingray.
    - Grand Sport generated interiors include active_for_grand_sport and requires_z25 downstream.

    7. lt_interiors.requires_r6x / included_option_id absent from LZ_Interiors

    Semantic concept:
    - Required package/option scoping for R6X interiors.

    Discrepancy type:
    - Missing explicit relationship columns.

    Classification:
    - Needs human review.

    Recommended canonical pattern:
    - model_interior_scope or interior_requirement rows:
      interior_id, requires_option_id, rule_type, active

    Evidence:
    - lt_interiors has requires_r6x and included_option_id.
    - generate_stingray_form.py validates active Stingray R6X interiors require included_option_id.

    8. grandSport_exclusive_members sheet name vs exclusive_group_members

    Semantic concept:
    - Exclusive group member rows.

    Discrepancy type:
    - Naming-pattern drift at sheet name level, not header level.

    Classification:
    - Harmless drift if ModelConfig owns mapping; needs review for future parser conventions.

    Recommended canonical name:
    - For model-specific sheets: {model_key}_exclusive_group_members.
    - Or shared generic sheet with model_key column.

    Evidence:
    - Stingray: exclusive_group_members.
    - Grand Sport: grandSport_exclusive_members.
    - Headers match.

    9. Grand Sport generated choices extra source fields

    Stingray artifact/header:
    - choices keys do not include source_option_name, source_description, text_cleanup_notes.

    Grand Sport artifact/header:
    - grand-sport-form-data-draft choices include source_option_name, source_description, text_cleanup_notes.

    Semantic concept:
    - Inspection/cleanup provenance.

    Discrepancy type:
    - Generated artifact contract drift.

    Classification:
    - Likely intentional during draft migration.

    Recommended canonical name:
    - Keep under draftMetadata/provenance if inspection-only; do not mix into final runtime choices unless approved.

    Evidence:
    - form-output/stingray-form-data.json choices keys.
    - form-output/inspection/grand-sport-form-data-draft.json choices keys.

    5. Data-type and value-shape discrepancy table

    1. Options selectable

    Sheet pair:
    - stingray_options / grandSport_options

    Field:
    - selectable

    Stingray representation:
    - bool values: True/False.

    Grand Sport representation:
    - Mixed strings and booleans:
      - "TRUE" 157
      - "FALSE" 99
      - False 8
      - True 2

    Examples:
    - grandSport_options row 2 opt_aq9_004 selectable "FALSE".
    - grandSport_options row 174 opt_719_001 selectable "TRUE".
    - stingray_options row 2 opt_eyt_001 selectable True.

    Downstream impact:
    - Generator must normalize workbook_bool-like values.
    - JSON choices emit selectable booleans/values fit for runtime.

    NoSQL/JSON risk:
    - Medium. Mixed strings/booleans can produce unstable typed documents.

    Recommended normalization:
    - Canonical boolean type.
    - Accept TRUE/FALSE/True/False during ingestion but emit real boolean.

    2. Rule review_flag

    Sheet pair:
    - rule_mapping / grandSport_rule_mapping

    Field:
    - review_flag

    Stingray representation:
    - bool False in 238 rows.

    Grand Sport representation:
    - string "False" in 321 rows.

    Examples:
    - rule_mapping row 2 review_flag false.
    - grandSport_rule_mapping row 2 review_flag "False".

    Downstream impact:
    - form_rules review_flag appears as string "False" in generated sheet/JSON evidence.

    NoSQL/JSON risk:
    - Medium.

    Recommended normalization:
    - review_flag boolean; use review_status if tri-state review workflow is needed.

    3. Price rule review_flag

    Sheet pair:
    - price_rules / grandSport_price_rules

    Field:
    - review_flag

    Stingray representation:
    - bool False in 42 rows.

    Grand Sport representation:
    - 23 string values + 22 bool values.

    Examples:
    - grandSport_price_rules row 2 review_flag "False".
    - Later rows include bool False.

    Downstream impact:
    - form_price_rules emits review_flag field.

    NoSQL/JSON risk:
    - Medium.

    Recommended normalization:
    - Same boolean normalization as above.

    4. Option rpo

    Sheet pair:
    - stingray_options / grandSport_options

    Field:
    - rpo

    Stingray representation:
    - Mostly strings, but 3 ints:
      - row 108 opt_719_001 rpo 719
      - row 110 opt_379_001 rpo 379
      - row 259 opt_719_002 rpo 719

    Grand Sport representation:
    - Same issue:
      - row 174 opt_719_001 rpo 719
      - row 176 opt_379_001 rpo 379
      - row 228 opt_719_002 rpo 719

    Downstream impact:
    - Generated choices/rules likely stringify RPOs for runtime.

    NoSQL/JSON risk:
    - Medium/high if RPO identity is used as a join key.

    Recommended normalization:
    - rpo as uppercase string always.
    - Preserve original cell value only in source provenance if needed.

    5. Price blanks vs zero

    Sheet pair:
    - stingray_options / grandSport_options

    Field:
    - price

    Stingray representation:
    - 163 populated int values.
    - 107 blanks.
    - Zero is used as real 0.

    Grand Sport representation:
    - 158 populated numeric values.
    - 108 blanks.
    - Zero is used as real 0.

    Examples:
    - Stingray row 2 opt_eyt_001 price 0.
    - Stingray row 53 opt_ryq_001 price blank.
    - Grand Sport row 2 opt_aq9_004 price blank.
    - Grand Sport row 174 opt_719_001 price 0.

    Downstream impact:
    - JSON base_price/price fields need to distinguish null/not-priced from included/no charge.

    NoSQL/JSON risk:
    - High if blank is coerced to zero.

    Recommended normalization:
    - price: number|null.
    - price_status or pricing_basis if needed:
      - null = not separately priced / inherited / standard-equipment-only.
      - 0 = explicit zero-price option/package.

    6. Active fields

    Sheet pairs:
    - rule_groups / grandSport_rule_groups
    - rule_group_members / grandSport_rule_group_members
    - exclusive_groups / grandSport_exclusive_groups
    - exclusive_group_members / grandSport_exclusive_members
    - grandSport_variant_overrides

    Representation:
    - Often strings "True"/"False", not booleans.

    Examples:
    - rule_groups row 2 active "True".
    - grandSport_exclusive_groups row 11 active "False".
    - grandSport_variant_overrides active "True".

    Downstream impact:
    - inspection.py active_source_row and grouped_rule_pairs compare active values; grouped_rule_pairs checks group.get("active") == "True".

    NoSQL/JSON risk:
    - Medium.

    Recommended normalization:
    - active boolean in canonical JSON.
    - Workbook may continue to accept TRUE/FALSE but parser should normalize.

    7. Color override lists

    Sheet:
    - lt_interiors and LZ_Interiors vs color_overrides.

    Field:
    - Color Overrides

    Stingray/LZ representation:
    - Comma-delimited RPO list, e.g. “G26, G4Z, GBK, GPH”.

    Normalized representation:
    - color_overrides rows:
      interior_id, option_id, rule_type, adds_rpo

    Examples:
    - lt_interiors row 5: 1LT_AQ9_HUQ Color Overrides “G26, G4Z, GBK, GPH”.
    - color_overrides rows 2-5 map 1LT_AQ9_HUQ to opt_g26_001, opt_g4z_001, opt_gbk_001, opt_gph_001, requiring opt_d30_001.

    Downstream impact:
    - form_color_overrides emits row-per-link.
    - JSON colorOverrides has override_id, interior_id, option_id, rule_type, adds_rpo, notes.

    NoSQL/JSON risk:
    - Low if normalized table is canonical; high if parser depends on comma-delimited raw field.

    Recommended normalization:
    - color_overrides table is canonical.
    - color_overrides_raw is provenance only.

    8. Interior components

    Sheet/source:
    - lt_interiors/LZ_Interiors plus PriceRef/interior_components/model_interior_scope.

    Representation:
    - Interior component membership is partly encoded by fields like Seat, Suede, Stitch, Two Tone and prices in PriceRef.
    - Generated output emits interior_components_json and JSON interior_components array.

    Examples:
    - form_interiors row 2 for 1LT_AE4_HTJ_N26:
      - interior_components_json includes AE4 Seat Upgrade price 1095 and N26 Sueded Microfiber price 695.
    - PriceRef has OptionType Seat/Suede/Stitching/TwoTone and Code prices.

    Downstream impact:
    - Runtime can consume structured interior_components.
    - Source still has legacy derivation fields.

    NoSQL/JSON risk:
    - Medium/high unless interior_components row table is canonical.

    Recommended normalization:
    - Canonical row table:
      model_key, interior_id, component_type, rpo, label, price, active, source_note.

    9. Rule lifecycle/generation_action

    Sheet pair:
    - rule_mapping / grandSport_rule_mapping

    Field:
    - generation_action

    Stingray representation:
    - 6 rows: omit_grouped_requirement.

    Grand Sport representation:
    - 114 rows across several action types:
      - omit_grouped_exclusion 108
      - omit_replaced_by_d3v_include 2
      - omit_soft_defaulted_caliper 1
      - omit_redundant_scoped_duplicate 1
      - preserve_runtime_exclude 1
      - omit_replaced_by_brake_exclusive_group 1

    Downstream impact:
    - Grand Sport draft exports 197 rules from 321 source rows.
    - Grand Sport rule audit reports omittedInactiveOrUnemitted 116 and omittedDuplicateExclusiveGroup 8.

    NoSQL/JSON risk:
    - High if omitted/replaced rules are discarded without provenance.

    Recommended normalization:
    - Explicit lifecycle fields:
      - source_rule_status: active|omitted|replaced|review
      - normalization_reason
      - replacement_group_id or replacement_rule_id
      - preserve_in_runtime boolean

    6. Key-value alignment observations

    A. option_id is the stable join key; rpo is not unique.

    Evidence:
    - Duplicate RPOs exist in both models:
      - Stingray EYT: opt_eyt_001 active, opt_eyt_002 inactive.
      - Stingray 719: opt_719_001 active, opt_719_002 inactive.
      - Grand Sport AQ9: opt_aq9_004 inactive, opt_aq9_003 inactive, opt_aq9_001 active, opt_aq9_002 inactive.
      - Grand Sport AE4: opt_ae4_001 inactive, opt_ae4_002 active, opt_ae4_003 inactive.

    Impact:
    - Future NoSQL documents should use option_id as primary ID.
    - RPO should be an attribute and secondary lookup, not a primary key.

    B. variant_id carries model/body-style identity but no explicit model_key in core OVS sheets.

    Evidence:
    - Stingray variant IDs use c07/c67.
    - Grand Sport variant IDs use e07/e67.
    - variant_master contains all variants but active true only for current live subset.
    - Grand Sport JSON variants include model, source_active, preview_included; Stingray variants do not include model.

    Impact:
    - Ingestion should derive or explicitly store model_key.
    - Recommended: model_key on every model-scoped document/relationship or nested under model document.

    C. option status is a matrix row, while some display/selectability behavior is option-row or override-row based.

    Evidence:
    - stingray_ovs/grandSport_ovs: option_id, variant_id, status.
    - grandSport_variant_overrides adds selectable/display_behavior/section_id per option+variant.
    - stingray_options/grandSport_options also have selectable/display_behavior at option level.

    Impact:
    - Need clear precedence:
      1. variant-specific override
      2. option source row default
      3. section/selection mode default
      4. generated/runtime fallback

    D. Rule mapping vs grouped rule path.

    Evidence:
    - Stingray 5V7/5ZU uses rule_groups:
      - grp_5v7_spoiler_requirement requires_any opt_5zu_001 or opt_5zz_001.
      - grp_5zu_paint_requirement requires_any opt_g8g_001, opt_gba_001, opt_gkz_001.
    - Grand Sport Z15 uses rule_groups:
      - gs_group_z15_excludes_non_center_stripes excludes_any 18 target stripe options.
    - Grand Sport also keeps omitted source rule rows in grandSport_rule_mapping with generation_action omit_grouped_exclusion.

    Impact:
    - Good pattern when a repeated order-guide phrase maps to many equivalent binary rules.
    - Ingestion should support both raw parsed binary candidates and canonical grouped relationship.

    E. Exclusive group relationship is already normalized.

    Evidence:
    - exclusive_groups + exclusive_group_members.
    - grandSport_exclusive_groups + grandSport_exclusive_members.
    - inspection.py load_exclusive_groups builds option_ids array from member rows.

    Impact:
    - Strong NoSQL shape:
      group document with members array or separate member collection.
    - Keep member rows canonical in workbook.

    F. Color/interior availability has both raw and normalized representations.

    Evidence:
    - lt_interiors/LZ_Interiors Color Overrides comma list.
    - color_overrides normalized rows.
    - form_color_overrides and JSON colorOverrides use normalized rows.

    Impact:
    - Prefer normalized color_overrides table.
    - Preserve raw field for audit only.

    G. Interior identity/ownership has multiple source paths.

    Evidence:
    - Stingray generator reads lt_interiors and LZ_Interiors.
    - Grand Sport inspection path reads lt_interiors, PriceRef, rule_mapping, model_interior_scope, interior_components.
    - Generated Grand Sport interiors include active_for_grand_sport and requires_z25, but source is not a direct grandSport_interiors sheet.

    Impact:
    - This is a key normalization area before ingestion.
    - Recommend explicit model_interior_scope ownership.

    7. Rule-path / compatibility-path discrepancy table

    1. Business outcome:
    - Grouped requirement for one-of-many prerequisite.

    Stingray source path:
    - rule_groups:
      - grp_5v7_spoiler_requirement
      - group_type requires_any
      - source_id opt_5v7_001
    - rule_group_members:
      - opt_5zu_001
      - opt_5zz_001

    Grand Sport source path:
    - No direct equivalent in Grand Sport examples; Grand Sport uses grouped exclusions more prominently.

    Generated/runtime evidence:
    - Stingray JSON ruleGroups includes target_ids array.
    - inspection.py load_rule_groups emits group_id, group_type, source_id, target_ids.

    Dominant/common pattern:
    - rule_groups + rule_group_members.

    Alternate pattern:
    - Repeated binary requires rows in rule_mapping, sometimes omitted by generation_action.

    Practical impact:
    - Good canonical relationship pattern.
    - Avoid expanding grouped business logic into many hardcoded generator/runtime cases.

    Classification:
    - Likely intentional / preferred workbook pattern.

    Recommendation:
    - Use grouped rules when order guide means “requires any of these” or “excludes any of these.”

    2. Business outcome:
    - Z15 Grand Sport Heritage Graphics excludes non-center stripes.

    Stingray source path:
    - No equivalent Z15 pattern in Stingray source.

    Grand Sport source path:
    - grandSport_rule_groups:
      - gs_group_z15_excludes_non_center_stripes
      - group_type excludes_any
      - source_id opt_z15_001
    - grandSport_rule_group_members:
      - 18 target stripe option_ids.
    - grandSport_rule_mapping:
      - 108 rows with generation_action omit_grouped_exclusion and disabled_reason “Z15 grouped exclusion blocks non-center stripes.”

    Generated/runtime evidence:
    - Grand Sport draft JSON ruleGroups length 1, target_ids length 18.
    - Grand Sport rule audit reports omittedInactiveOrUnemitted/omittedDuplicateExclusiveGroup evidence.

    Dominant/common pattern:
    - Grouped rule as canonical output.

    Alternate pattern:
    - Repeated detailed binary exclusions retained with omit action.

    Practical impact:
    - Excellent pattern for ingestion if lifecycle/provenance is preserved.

    Classification:
    - Likely intentional.

    Recommendation:
    - Canonicalize generation_action as rule normalization status, not free text.

    3. Business outcome:
    - Mutually exclusive engine covers.

    Stingray source path:
    - exclusive_groups:
      - grp_ls6_engine_covers
    - exclusive_group_members:
      - opt_bc7_001, opt_bcp_001, opt_bcs_001, opt_bc4_001

    Grand Sport source path:
    - grandSport_exclusive_groups:
      - gs_excl_ls6_engine_covers
    - grandSport_exclusive_members:
      - opt_bc7_001, opt_bc4_002, opt_bcp_002, opt_bcs_002
    - grandSport_variant_overrides:
      - opt_bc7_001 default_selected for coupe variants.

    Generated/runtime evidence:
    - Stingray JSON exclusiveGroups length 7.
    - Grand Sport draft JSON exclusiveGroups length 9 active groups.
    - Grand Sport rule audit focusedReview.engineCoverRules exists.

    Dominant/common pattern:
    - exclusive_groups + members.

    Alternate pattern:
    - Variant default selected via grandSport_variant_overrides.

    Practical impact:
    - Requires merge of exclusivity and default/override metadata.
    - NoSQL should store exclusivity separately from default-selection policy.

    Classification:
    - Intentional, medium ingestion complexity.

    Recommendation:
    - Use exclusive_groups for peer relationship; use default_selection/variant_override rows for default state.

    4. Business outcome:
    - Price included with package / zero-price package policy.

    Stingray source path:
    - price_rules:
      - pr_z51tvs_001: opt_z51_001 overrides opt_tvs_001 to 0.
      - interior condition IDs such as 3LT_AE4_H8T override seatbelt options to 0.

    Grand Sport source path:
    - grandSport_price_rules:
      - gs_pr_fey_j57_001: opt_fey_001 overrides opt_j57_001 to 0.
      - gs_pr_fey_t0f_001: FEY includes T0F at 0.
      - gs_pr_fey_wub_001: FEY includes WUB at 0.
    - Grand Sport uses more body_style_scope and trim_level_scope.

    Generated/runtime evidence:
    - Both JSONs include priceRules with condition_option_id, target_option_id, price_rule_type, price_value.

    Dominant/common pattern:
    - price_rules table.

    Alternate pattern:
    - Some “included” semantics also appear in rule_mapping includes and generated auto_add behavior.

    Practical impact:
    - Ingestion must distinguish:
      - compatibility include
      - auto-add include
      - price override to 0
      - standard equipment status

    Classification:
    - Likely intentional but risky if merged into one generic “includes” concept.

    Recommendation:
    - Keep price rules as separate relationship type.

    5. Business outcome:
    - Interior includes/seatbelt auto-add.

    Stingray source path:
    - rule_mapping includes with source_type interior.
    - condition/source IDs like 3LT_AE4_H8T include opt_3a9_001.
    - price_rules also override included seatbelt price to 0.

    Grand Sport source path:
    - grandSport_rule_mapping includes with source_type interior, including Z25/EL9-related specifics.
    - Grand Sport generated interiors add requires_z25.

    Generated/runtime evidence:
    - form_rules rows show auto_add True for includes.
    - Grand Sport draft rules count 197 from 321 source rule rows.

    Dominant/common pattern:
    - rule_mapping includes + price_rules override.

    Alternate pattern:
    - Interior source fields and model_interior_scope/requires_z25 contribute extra model-specific state.

    Practical impact:
    - NoSQL should model interior as selectable entity with component relationships and compatibility rules.

    Classification:
    - Needs human review for final canonical interior schema.

    Recommendation:
    - Move model-specific interior requirements into model_interior_scope/interior_requirement rows, not generator special cases.

    6. Business outcome:
    - Default exhaust/engine-cover/display-only Grand Sport standard selections.

    Stingray source path:
    - Option-level display_behavior has small number of values:
      - auto_only, default_selected, hidden, display_only.
    - No listed Stingray-specific variant override sheet.

    Grand Sport source path:
    - grandSport_variant_overrides:
      - opt_nga_001 default_selected across six variants.
      - opt_bc7_001 default_selected for coupe variants.
      - opt_uqt_001 display_only for 2LT/3LT equipment sections.

    Generated/runtime evidence:
    - Grand Sport draft choices include display_behavior.
    - defaultSelectionRules in Grand Sport draft length 2.
    - Stingray JSON defaultSelectionRules length 3.

    Dominant/common pattern:
    - Emerging model/variant override metadata.

    Alternate pattern:
    - Option-level display_behavior.

    Practical impact:
    - Future parser needs deterministic precedence and canonical source ownership.

    Classification:
    - Needs Sean’s decision.

    Recommendation:
    - Prefer shared variant_option_overrides/default_selection_rules pattern with model_key and variant_id.

    7. Business outcome:
    - Color availability requiring D30.

    Stingray source path:
    - lt_interiors/LZ_Interiors Color Overrides raw comma lists.
    - color_overrides normalized rows with adds_rpo opt_d30_001.

    Grand Sport source path:
    - Grand Sport draft uses shared color_overrides and interiors from lt_interiors/scope.

    Generated/runtime evidence:
    - form_color_overrides rows 245.
    - JSON colorOverrides rows 245.

    Dominant/common pattern:
    - color_overrides relationship table.

    Alternate pattern:
    - comma-delimited Color Overrides in interior source sheets.

    Practical impact:
    - Parser should not rely on comma text as canonical.

    Classification:
    - Harmless if normalized table remains authoritative; otherwise risky.

    Recommendation:
    - Keep raw list for audit, normalized table for runtime.

    8. Recommended canonical workbook patterns

    A. Headers

    Use lowercase snake_case for canonical ingestion fields:
    - option_id
    - model_key
    - variant_id
    - rpo
    - option_name
    - description
    - source_detail_raw
    - section_id
    - selectable
    - active
    - display_order
    - display_behavior
    - price
    - status

    For interiors:
    - interior_id
    - model_key
    - trim_level
    - seat_code
    - interior_code
    - interior_name
    - material
    - price
    - suede_code
    - stitch_code
    - two_tone_code
    - section_id
    - active
    - requires_option_id
    - source_detail_raw
    - color_overrides_raw

    For rules:
    - rule_id
    - source_id
    - source_type
    - rule_type
    - target_id
    - target_type
    - source_section_id
    - target_section_id
    - source_selection_mode
    - target_selection_mode
    - body_style_scope
    - trim_level_scope
    - variant_scope
    - disabled_reason
    - auto_add
    - runtime_action
    - review_flag
    - source_detail_raw
    - normalization_status
    - normalization_reason

    B. Value types

    Canonical JSON/workbook parser output:
    - IDs: strings.
    - RPOs: uppercase strings, even numeric-looking values like "719" and "379".
    - Booleans: booleans.
    - Prices: number|null.
    - Display order: integer.
    - Scopes: string|null or arrays if multiple values are allowed.
    - Raw text: string|null.
    - List relationships: member rows, not comma/pipe strings.

    C. Blank/null conventions

    Recommended:
    - Blank price means null/not separately priced.
    - 0 means explicit zero-price.
    - Blank scope means applies to all.
    - Blank display_behavior means normal/default behavior.
    - Blank source_detail_raw means no raw disclosure.
    - Blank selectable in an override row means “do not override selectable,” not false.

    D. Relationship keys

    Use option_id/interior_id/variant_id/group_id as joins.
    Do not join primarily by RPO.

    Recommended relationship tables:
    - option_variant_status:
      model_key, option_id, variant_id, status
    - option_variant_overrides:
      model_key, option_id, variant_id, selectable, display_behavior, section_id, active, note
    - rule_mapping:
      model_key, rule_id, source_id, target_id, rule_type, scopes, normalization_status
    - rule_group_members:
      model_key, group_id, target_id, display_order, active
    - exclusive_group_members:
      model_key, group_id, option_id, display_order, active
    - color_overrides:
      model_key, interior_id, option_id, rule_type, adds_option_id
    - interior_components:
      model_key, interior_id, component_type, rpo, label, price, active

    E. Rule groups

    Canonical group_type enum:
    - requires_any
    - requires_all, if needed later
    - excludes_any
    - includes_any, only if real semantics require it

    Keep group rows separate from member rows.

    F. Exclusive groups

    Canonical selection_mode enum:
    - single_within_group
    - required_single_within_group

    Keep active inactive rows for source retention, but generated runtime should emit only active groups/members unless draft/audit mode.

    G. Package includes and auto-adds

    Separate concepts:
    - rule_mapping includes = compatibility/selection relationship.
    - rule_mapping auto_add = runtime selection behavior.
    - price_rules override = pricing behavior.
    - standard status = OVS status.

    Do not collapse these into one “included” field.

    H. Variant overrides

    Prefer shared model-scoped sheet/table:
    - variant_option_overrides
    - Fields:
      model_key, option_id, variant_id, selectable, display_behavior, section_id, active, note

    Grand Sport’s grandSport_variant_overrides is a strong candidate pattern, but it should be generalized before future ingestion.

    I. Color/interior availability

    Canonical:
    - color_overrides row table owns normalized relationships.
    - interiors own raw color_overrides_raw only as provenance.
    - model_interior_scope owns model activation/requires package metadata.

    J. Price rules

    Canonical:
    - price_rule_id
    - condition_option_id
    - target_option_id
    - price_rule_type
    - price_value
    - body_style_scope
    - trim_level_scope
    - variant_scope
    - review_flag
    - notes

    Avoid interpreting blank price as zero.

    K. Status/selectability/display fields

    Keep separate:
    - status: available|standard|unavailable
    - selectable: boolean
    - active: boolean
    - display_behavior: enum|null
      - default_selected
      - display_only
      - hidden
      - auto_only

    L. Source-detail preservation

    Preserve raw order-guide language in:
    - source_detail_raw
    - source_note
    - normalization_notes
    - original_detail_raw

    But do not use raw text as the runtime rule source after normalized rows exist.

    9. Risks for NoSQL/JSON ingestion

    1. Unstable identifiers
    - RPO is not unique.
    - option_id is stable but sometimes same RPO has active/inactive variants.
    - Recommendation: option_id primary, rpo secondary.

    2. Ambiguous relationships
    - Includes may mean auto-add, included price, standard equipment, or compatibility.
    - Recommendation: separate rule_mapping, price_rules, OVS status, default/override rows.

    3. Inconsistent null handling
    - Price blanks vs zero.
    - Blank overrides vs false overrides.
    - Blank scopes vs all scopes.
    - Recommendation: canonical null semantics.

    4. Non-normalized list values
    - Color Overrides comma lists.
    - Generated interior_hierarchy_levels JSON string in form_interiors.
    - Some generated exclusiveGroups use option_ids arrays.
    - Recommendation: source workbook should prefer member rows; generated JSON may use nested arrays.

    5. Model-specific special cases
    - Grand Sport variant overrides and generation_action values reflect model-specific migration.
    - Recommendation: promote to generic model_key-scoped metadata tables where repeatable.

    6. Difficult joins
    - Interior IDs differ between LT/LZ shapes.
    - PriceRef joins by OptionType/Trim/Code, not direct component ID.
    - Recommendation: explicit interior_components rows.

    7. Duplicate semantic fields
    - detail_raw/original_detail_raw/Detail from Disclosure/source_note/source_detail_raw.
    - Price/Cost.
    - interior_id/ID.
    - Recommendation: canonical names with source aliases in parser.

    8. Generated-output-only dependencies
    - Grand Sport draftMetadata and generated choices text_cleanup_notes should remain inspection provenance unless approved as runtime contract.
    - Recommendation: keep generated-only evidence out of source schema.

    9. Hardcoded business-rule risk
    - ModelConfig currently maps model-specific sheet names; this is fine.
    - Risk appears if generator/runtime begins encoding business facts instead of reading workbook rows.
    - Recommendation: workbook-owned normalization tables should remain authoritative.

    10. Suggested validation checks or scripts for later implementation pass

    Do not implement now. Suggested future checks:

    1. Header drift checks
    - Compare configured equivalent sheet pairs.
    - Fail/warn when required canonical headers are missing.
    - Allow known aliases only through explicit alias map:
      - Price/Cost -> price
      - ID/interior_id -> interior_id
      - Detail from Disclosure/detail_raw/original_detail_raw -> source_detail_raw

    2. Type drift checks
    - Boolean fields contain only accepted boolean values.
    - Price fields are numeric or blank.
    - display_order fields are integers.
    - RPO fields are strings after normalization.
    - status fields limited to available|standard|unavailable.

    3. Missing key reference checks
    - Every OVS option_id exists in model option sheet.
    - Every OVS variant_id exists in variant_master and belongs to model.
    - Every rule source_id/target_id resolves to an option_id, interior_id, or approved virtual source ID.
    - Every price_rules condition/target option resolves.
    - Every group member references an existing group.

    4. Orphaned group checks
    - rule_group_members without rule_groups.
    - exclusive_group_members without exclusive_groups.
    - Groups with no active members.
    - Inactive group with active members should be warning or explicit allowed state.

    5. Inconsistent RPO checks
    - Numeric RPO cells.
    - Same RPO with multiple active options in same section/variant unless explicitly allowed.
    - Rule detail mentions RPO not resolvable to active/canonical option.

    6. Section/category/variant checks
    - Every section_id exists in section_master.
    - Every section step_key is valid in runtime_steps/step metadata.
    - category_master absence or archive-only state should be reconciled.

    7. Blank/null/list convention checks
    - Flag comma-delimited canonical fields except approved raw fields.
    - Flag pipe-delimited source fields except generated-only artifacts.
    - Flag JSON-like strings in workbook source unless field is explicitly *_json generated output.

    8. Generated contract regression checks
    - Compare generated form_rules count/source count.
    - Ensure omitted/replaced source rules have normalization_status.
    - Ensure JSON choice keys remain stable per model unless a schema migration is approved.
    - Ensure Grand Sport draft-only fields do not leak into live data.js without approval.

    9. Interior normalization checks
    - Every active model interior has model_interior_scope row.
    - Every component-bearing interior has interior_components rows.
    - Every requires_r6x/requires_z25 maps to a requires_option_id.
    - PriceRef joins produce expected component prices.

    10. Color override checks
    - Every raw Color Overrides RPO has normalized color_overrides rows.
    - Every color_overrides option_id resolves to an exterior color option.
    - Every adds_rpo resolves to an option_id and expected rule type.

    11. Open questions requiring Sean’s decision

    1. Should Grand Sport’s grandSport_variant_overrides become the canonical shared variant_option_overrides pattern with model_key, or remain a model-specific sheet?
    - remain model-specific
    2. Should future ingestion prefer model-specific sheets like grandSport_options, or shared sheets with model_key columns?
    - Model specific sheets.
    3. Should category_master be restored as an active sheet, or should references to it be removed in favor of section_master/runtime metadata?
    - Remove it
    4. What is the canonical source for interiors going forward?
       - Continue lt_interiors/LZ_Interiors plus model_interior_scope?
       - Create a unified interiors source table?
       - Keep model-specific interior scope separate from base interior definitions?
    - I think the lt/LZ interiors with model_interior_scope is a good way to organize and build the interior combinations because the patterns are similar across the models with the shared trim levels. I am not sure why Stingray calls lz interiors because they arent compatible.
    5. Should LZ_Interiors be normalized to the same headers as lt_interiors?
       - ID -> interior_id
       - Cost -> price
       - add section_id/active/model-scope fields through source or scope table
    - Yes, lz interiors should be normalized with the same headers as lt interiors.
    6. Should generation_action become a controlled enum with lifecycle fields?
       - Current Grand Sport values are useful but semi-freeform.
    - Yes but it needs to be able to retain the proper functionality
    7. Should generated draft/provenance fields such as source_option_name, source_description, text_cleanup_notes remain draft-only, or become part of a permanent JSON provenance object?
    - Fields used in runtime should be preserved. I am not sure of the risk for this.
    8. How should numeric-looking RPOs be represented in the workbook itself?
       - Recommendation is text cells/canonical strings, but Excel often coerces values like 719 and 379.
    - Approved recommendation.
    9. Should active/selectable/review_flag cells be standardized to real Excel booleans or canonical TRUE/FALSE strings?
       - For parser output, they should become booleans either way.
    - booleans
    10. Should blank price always mean null/not-priced, and should explicit zero always mean zero-price?
       - This should be documented before NoSQL conversion.
    - Blank should mean null/not-priced, and zero should mean zero-price.
    11. Should raw order-guide fields be preserved per row in NoSQL documents, or separated into an audit/provenance collection?
    - Ignore NoSQL plans for now.
    12. Should grouped rules fully replace omitted binary rule rows, or should omitted binary rows remain in source with normalization_status for auditability?
    - auditability is important for troubleshooting. keep in source with normalization_status.

    Handoff

    What changed:
    - Nothing. Report-only audit.

    What did not change:
    - stingray_master.xlsx unchanged.
    - generated form_* sheets unchanged.
    - form-output/* unchanged.
    - form-app/data.js unchanged.
    - generator scripts unchanged.
    - runtime files unchanged.
    - tests/docs unchanged.
    - No dependencies added.

    Gate results:
    - No generators run, by constraint.
    - No tests run, by constraint/report-only scope.
    - Read-only inspections completed:
      - workbook source sheets
      - generated form_* evidence
      - JSON artifacts
      - generator/config consumers
    - Workbook lock file absent: ./~$stingray_master.xlsx was false/not present.

    Manual verification still pending:
    - Sean decision on canonical interior and variant-override patterns.
    - Sean decision on category_master active/retired status.
    - Later implementation pass would need formal validation scripts and approved workbook/schema edits.

    Residual risks:
    - This audit sampled representative rows and computed schema/value profiles; it did not manually review every business rule for product correctness.
    - Grand Sport remains draft/inspection-oriented in artifact naming and metadata; production activation should be separately scoped and approved.
