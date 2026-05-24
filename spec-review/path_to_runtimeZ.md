Audit complete. I made no file or workbook edits.

    I also recorded the durable project fact that Z06, ZR1, and ZR1X should reuse Grand Sport compatibility rules and exclusive groups; their real differences are option set and standard/included availability.

    Current state

    Branch / repo:
    - Branch: schemaHarden
    - Repo status: clean
    - No Excel lock file present
    - Workbook schema validation passed:
      - .venv/bin/python scripts/validate_workbook_schema.py stingray_master.xlsx
      - status: valid, issue_count: 0

    Runtime registry:
    - form-app/data.js currently exposes:
      - default model: stingray
      - runtime models: stingray, grandSport
      - window.STINGRAY_FORM_DATA alias still matches Stingray data
    - Z06, ZR1, and ZR1X are not in runtime.

    Future model workbook state:
    - model_master has inactive rows for:
      - z06
      - zr1
      - zr1x
    - model_variants is already mapped:
      - Z06: 6 variants
        - 1lz_h07, 2lz_h07, 3lz_h07, 1lz_h67, 2lz_h67, 3lz_h67
      - ZR1: 4 variants
        - 1lz_r07, 3lz_r07, 1lz_r67, 3lz_r67
      - ZR1X: 4 variants
        - 1lz_s07, 3lz_s07, 1lz_s67, 3lz_s67
    - model_workbook_sources has inactive source-role rows for all three future models.
    - model_registry_promotion has inactive/unpromoted rows for all three future models.

    Future source sheets:
    - Header-only, empty normalized sheets exist for all three:
      - z06_options, z06_ovs, rules, price rules, groups, exclusives, variant overrides
      - zr1_options, zr1_ovs, rules, price rules, groups, exclusives, variant overrides
      - zr1x_options, zr1x_ovs, rules, price rules, groups, exclusives, variant overrides
    - All are currently 0 data rows.

    Archive / preview state:
    - Hidden archive sheets exist:
      - archive_Z06_Ingest: 363 rows
      - archive_ZR1_Ingest: 336 rows
      - archive_ZR1X_Ingest: 337 rows
    - Phase 5 preview artifact exists:
      - form-output/inspection/future-model-source-preview.json
      - form-output/inspection/future-model-source-preview.md

    Preview summary:
    - Z06:
      - proposed options: 363
      - proposed OVS rows: 2178
      - statuses:
        - available: 910
        - standard: 990
        - unavailable: 278
      - section resolved: 240
      - section conflict: 14
      - section unresolved: 109
      - missing RPO: 52
      - duplicate RPO rows: 156
    - ZR1:
      - proposed options: 336
      - proposed OVS rows: 1344
      - statuses:
        - available: 450
        - standard: 684
        - unavailable: 210
      - section resolved: 212
      - section conflict: 14
      - section unresolved: 110
      - missing RPO: 52
      - duplicate RPO rows: 162
    - ZR1X:
      - proposed options: 337
      - proposed OVS rows: 1348
      - statuses:
        - available: 442
        - standard: 692
        - unavailable: 214
      - section resolved: 212
      - section conflict: 14
      - section unresolved: 111
      - missing RPO: 52
      - duplicate RPO rows: 164

    Grand Sport canonical rule state:
    - grandSport_rule_mapping: 321 rows
      - excludes: 243
      - includes: 55
      - requires: 23
    - grandSport_exclusive_groups: 9 active groups
    - grandSport_exclusive_members: 26 active members
    - grandSport_rule_groups: 1 active grouped exclusion
    - grandSport_rule_group_members: 18 active members
    - grandSport_variant_overrides: 13 rows

    Interior state:
    - LZ_Interiors exists, hidden, 132 rows.
    - Current active model_interior_scope rows:
      - grand_sport: 132
    - Current active interior_components rows:
      - stingray: 197
      - grand_sport: 198
    - No active Z06/ZR1/ZR1X interior scope/component rows yet.

    Runtime metadata gaps:
    - runtime_steps only has Stingray and Grand Sport rows.
    - context_section_master only has Stingray and Grand Sport rows.
    - section_presentation only has Stingray and Grand Sport rows.
    - order_summary_sections only has Stingray rows.
    - step_order_summary_map only has Stingray rows.
    - asset_map has Stingray and Grand Sport rows, no future model rows.
    - runtime_rule_exceptions only has Stingray rows.
    - No model_presentation sheet exists yet.
    - form-app/app.js still has hardcoded setup highlight copy for only Stingray and Grand Sport.
    - form-app/app.js still has the hardcoded GBA / opt_zyc_001 runtime exception.
    - Runtime order-summary fallback still exists and works as compatibility fallback, but new promoted models should have generated data.orderSummary.

    Generator state:
    - Registry promotion is now workbook-owned through model_registry_promotion.
    - Schema validation is metadata-aware enough to validate source/promotion scaffolds.
    - There is still no generic generate_model_form.py.
    - scripts/generate_grand_sport_form.py still imports GRAND_SPORT_MODEL.
    - scripts/build_grand_sport_rule_sources.py still imports GRAND_SPORT_MODEL.
    - ModelConfig constants still only define Stingray and Grand Sport as Python constants, though workbook metadata exists for future models.

    Main verdict

    The next work is mostly not runtime work. It is source-data normalization and model-draft generation.

    Because Z06, ZR1, and ZR1X share Grand Sport compatibility and exclusive-group behavior, do not spend effort trying to rediscover those rules from raw order-guide text. Treat Grand Sport as the canonical compatibility/exclusive template and rebase it onto each future model only after each model’s option IDs are resolved.

    The accuracy-critical work is:
    1. turn archive rows into correct normalized *_options and *_ovs;
    2. resolve section placement, missing-RPO rows, duplicate RPO identities, and standard/available/unavailable status;
    3. wire LZ interiors and model-scoped runtime metadata;
    4. copy/rebase Grand Sport compatibility/exclusive groups through an ID resolver;
    5. generate draft contracts;
    6. promote only after review.

    Todo list to get Z06, ZR1, and ZR1X to runtime

    1. Freeze the rule strategy

    - Record Grand Sport as the compatibility/exclusive canonical template for:
      - *_rule_mapping
      - *_rule_groups
      - *_rule_group_members
      - *_exclusive_groups
      - *_exclusive_members
    - Do not parse raw Z06/ZR1/ZR1X detail text as the primary rule source for compatibility.
    - Use raw detail text only as audit/provenance and to catch option-specific includes or model-only packages that are not part of shared compatibility.
    - Add tests later proving future model compatibility/exclusive contracts match Grand Sport after source/target ID rebasing.

    2. Create a human-review mapping layer for Phase 5 preview output

    Add a review-owned mapping table or artifact before writing normalized rows.

    Recommended workbook sheet:
    - future_model_source_review

    Suggested columns:
    - model_key
    - archive_sheet
    - archive_row
    - rpo
    - source_option_name
    - source_category
    - candidate_option_id
    - approved_option_id
    - approved_section_id
    - review_status
    - review_reason
    - copy_from_model_key
    - copy_from_option_id
    - notes
    - active

    This should resolve:
    - Z06:
      - 109 unresolved section rows
      - 14 section conflicts
      - 52 missing-RPO rows
      - 156 duplicate-RPO rows
    - ZR1:
      - 110 unresolved section rows
      - 14 section conflicts
      - 52 missing-RPO rows
      - 162 duplicate-RPO rows
    - ZR1X:
      - 111 unresolved section rows
      - 14 section conflicts
      - 52 missing-RPO rows
      - 164 duplicate-RPO rows

    Priority review examples:
    - UQT section conflict
    - AQ9 / AH2 seat section conflicts
    - B4Z / G0K standard vs included placement conflicts
    - SC7 LPO Exterior vs LPO Interior conflict
    - DY0, N3W, CFV, LT6, R8E, SOE, FE6, M1M unresolved rows
    - all missing-RPO standard-equipment rows

    3. Populate normalized option and OVS source sheets

    After review mapping is approved, write source rows into:
    - z06_options
    - z06_ovs
    - zr1_options
    - zr1_ovs
    - zr1x_options
    - zr1x_ovs

    Rules:
    - *_options owns:
      - stable option_id
      - RPO
      - price when directly owned by option
      - polished label/description
      - raw detail provenance
      - final section_id
      - selectable/display/active flags
      - display order
    - *_ovs owns:
      - exact variant availability
      - available
      - standard
      - unavailable
    - Standard equipment should remain status data in OVS, not separate runtime hardcoding.
    - Do not write unresolved rows into final source sheets unless clearly marked inactive/review.

    Validation:
    - option count matches reviewed expected count
    - OVS row count equals reviewed option rows x variant count unless intentionally scoped
    - no blank variant statuses
    - no unknown statuses
    - all active source rows have valid section_id
    - all active OVS rows reference known option_id and model variant

    4. Create a deterministic option-ID resolver against Grand Sport

    Needed before copying rules.

    Build a model-specific map:
    - Grand Sport option_id -> Z06 option_id
    - Grand Sport option_id -> ZR1 option_id
    - Grand Sport option_id -> ZR1X option_id

    Match priority:
    1. exact reviewed copy_from_option_id
    2. exact RPO + same semantic section
    3. exact RPO + reviewed duplicate group
    4. manual review override
    5. unresolved, do not copy rule/member

    Output review artifact:
    - resolved mappings
    - missing Grand Sport source options per target model
    - duplicate candidate mappings
    - target options with no Grand Sport equivalent
    - rules/groups that cannot be copied safely

    This is the key safety step. Grand Sport rules may be shared, but rule rows reference option IDs, not just RPOs.

    5. Rebase Grand Sport compatibility rules for each future model

    Populate:
    - z06_rule_mapping
    - zr1_rule_mapping
    - zr1x_rule_mapping

    From:
    - grandSport_rule_mapping

    Using:
    - Grand Sport -> target model option-ID resolver

    Preserve:
    - rule_type
    - target_type
    - target_selection_mode
    - source_selection_mode
    - generation_action
    - body/trim/variant scopes where still meaningful
    - runtime_action
    - disabled_reason
    - review/provenance notes

    Rewrite:
    - rule_id with model prefix
    - source_id
    - target_id
    - any scope values that use Grand Sport variant IDs

    Do not copy a rule if:
    - source option cannot resolve
    - target option cannot resolve
    - Grand Sport rule references a Grand Sport-only package not present in the target model
    - variant scope cannot map cleanly

    Expected outcome:
    - compatibility behavior matches Grand Sport where options exist;
    - unresolved cases are explicit review rows, not silent omissions.

    6. Rebase Grand Sport grouped rules

    Populate:
    - z06_rule_groups
    - z06_rule_group_members
    - zr1_rule_groups
    - zr1_rule_group_members
    - zr1x_rule_groups
    - zr1x_rule_group_members

    From:
    - grandSport_rule_groups
    - grandSport_rule_group_members

    Current Grand Sport grouped rule:
    - gs_group_z15_excludes_non_center_stripes
    - 18 active members

    Rewrite:
    - group IDs with model prefix
    - source option ID via resolver
    - member target IDs via resolver
    - scopes where applicable

    7. Rebase Grand Sport exclusive groups

    Populate:
    - z06_exclusive_groups
    - z06_exclusive_members
    - zr1_exclusive_groups
    - zr1_exclusive_members
    - zr1x_exclusive_groups
    - zr1x_exclusive_members

    From:
    - grandSport_exclusive_groups
    - grandSport_exclusive_members

    Current active Grand Sport groups include:
    - LS6 engine covers
    - center caps
    - indoor car covers
    - rear script badges
    - suede compartment liners
    - ground effects
    - Z52 packages
    - exterior accents
    - performance brakes

    Rewrite:
    - group IDs with model prefix
    - member option IDs via resolver
    - display order preserved
    - selection mode preserved

    Review carefully:
    - engine-cover group naming may not be LS6 for Z06/ZR1/ZR1X if engine/package naming differs.
    - group behavior can be identical while notes/customer copy should be model-appropriate.

    8. Build price rules from future model price schedule

    Do not blindly copy all Grand Sport price rules.

    Populate:
    - z06_price_rules
    - zr1_price_rules
    - zr1x_price_rules

    Use:
    - future model price schedule / raw order guide pricing
    - reviewed options
    - scoped conditions where same RPO has different price by model/body/trim/interior

    Copy Grand Sport price-rule patterns only when:
    - the same target option exists;
    - the same contextual pricing behavior applies;
    - the actual price value is verified for the future model.

    9. Handle variant overrides as model-specific cleanup

    Populate:
    - z06_variant_overrides
    - zr1_variant_overrides
    - zr1x_variant_overrides

    Use for:
    - duplicate/canonical row suppression
    - selectable/display behavior that differs by trim/body
    - section overrides for ambiguous duplicate RPOs

    Do not use variant overrides to hide bad source normalization. If a row should be inactive or split, fix the source option/OVS row first.

    10. Wire LZ interiors per model

    Current blocker:
    - LZ_Interiors exists, but future models have no active interior scope/component rows.

    Add active rows for:
    - model_interior_scope
      - z06
      - zr1
      - zr1x
    - interior_components
      - z06
      - zr1
      - zr1x

    Also activate each future model’s:
    - model_workbook_sources.interior_source_sheet = LZ_Interiors

    Need review:
    - Z06 has 1LZ/2LZ/3LZ.
    - ZR1 and ZR1X have 1LZ/3LZ only.
    - LZ_Interiors includes trims:
      - 1LZ
      - 2LZ
      - 3LZ
      - 3LZ_R6X
    - Scope rows must not expose 2LZ interiors to ZR1/ZR1X if those trims do not exist.
    - Component pricing must still use PriceRef correctly.
    - R6X/D30 behavior must be verified per model.

    11. Add runtime metadata rows for future models

    Before runtime promotion, add model-scoped rows for:
    - runtime_steps
    - context_section_master
    - section_presentation
    - order_summary_sections
    - step_order_summary_map
    - asset_map
    - default_selection_rules if needed
    - runtime_rule_exceptions only if actually needed

    Likely copy from Grand Sport where same step/section behavior applies:
    - runtime steps
    - context section model/body/trim setup
    - section presentation
    - standard-equipment grouping
    - selected-RPO summary grouping

    Need to fix before promotion:
    - order_summary_sections and step_order_summary_map are currently Stingray-only. New models should not rely on runtime fallback.
    - asset_map needs at least model selector images for Z06/ZR1/ZR1X if the UI should look complete.
    - runtime setup highlight copy is still hardcoded for only Stingray/Grand Sport.

    12. Move model presentation highlights into workbook/generated data

    Current runtime hardcode:
    - form-app/app.js:104 has Stingray/Grand Sport vehicleSetupHighlights.

    Before adding three more models, either:
    - create model_presentation workbook sheet and emit generated highlight metadata, preferred; or
    - knowingly add temporary runtime copy for Z06/ZR1/ZR1X, not preferred.

    Preferred sheet:
    - model_presentation

    Suggested columns:
    - model_key
    - eyebrow
    - title
    - description
    - fact_1
    - fact_2
    - fact_3
    - active
    - display_order
    - source_note

    Runtime should render:
    - generated model presentation when present;
    - fallback only for old data.

    13. Generalize the Grand Sport draft generator

    Add:
    - scripts/generate_model_form.py --model-key <model_key>

    Keep:
    - scripts/generate_grand_sport_form.py as wrapper/alias.

    The generic generator should:
    - load ModelConfig from workbook metadata;
    - read model source sheets from model_workbook_sources;
    - generate inspection, contract-preview, and draft form-data artifacts for any active model;
    - support LZ interiors through interior_source_sheet;
    - use model-specific artifact prefixes:
      - z06-form-data-draft
      - zr1-form-data-draft
      - zr1x-form-data-draft

    This is required so new models can reach runtime without new one-off Python constants.

    14. Generalize Grand Sport rule audit tooling

    Add:
    - scripts/build_model_rule_sources.py --model-key <model_key>

    Keep:
    - scripts/build_grand_sport_rule_sources.py as compatibility wrapper.

    Use it to audit:
    - copied Grand Sport rule parity
    - unresolved source/target option mappings
    - exclusive group member parity
    - model-specific missing options
    - price-rule review needs

    15. Activate source metadata only after source sheets are populated

    Once normalized future source sheets contain reviewed rows:
    - set future source-role rows active in model_workbook_sources
    - set future model_master.active = TRUE

    Do not promote to runtime yet.

    Run:
    - .venv/bin/python scripts/validate_workbook_schema.py stingray_master.xlsx

    Expected:
    - future source sheets validated by active metadata
    - no header drift
    - no broken option/OVS/rule references

    16. Generate draft artifacts for each future model

    Run expected future commands:
    - .venv/bin/python scripts/generate_model_form.py --model-key z06
    - .venv/bin/python scripts/generate_model_form.py --model-key zr1
    - .venv/bin/python scripts/generate_model_form.py --model-key zr1x

    Expected artifacts:
    - form-output/inspection/z06-inspection.json
    - form-output/inspection/z06-contract-preview.json
    - form-output/inspection/z06-form-data-draft.json
    - matching Markdown files
    - matching ZR1/ZR1X artifacts

    Review for each:
    - variants
    - choices
    - standard equipment
    - rules
    - price rules
    - exclusive groups
    - interiors
    - validation warnings/errors
    - unresolved normalization issues

    17. Add parity and model-specific contract tests

    Add tests for:
    - Z06/ZR1/ZR1X source sheet headers and active metadata.
    - OVS variant coverage.
    - no unresolved active section IDs.
    - generated draft artifacts have correct variant counts.
    - generated standard equipment counts match source OVS standard statuses.
    - Grand Sport compatibility rules rebase cleanly:
      - same count or explicit reviewed exceptions
      - no source/target IDs pointing back to Grand Sport
      - no unresolved copied rules
    - exclusive group parity:
      - same selection modes as Grand Sport
      - all copied members resolve
      - group IDs are model-prefixed
    - LZ interiors:
      - Z06 sees 1LZ/2LZ/3LZ scope
      - ZR1/ZR1X do not expose 2LZ
      - R6X component pricing remains correct
    - runtime registry excludes future models until promotion rows are enabled.
    - runtime registry includes all five models after promotion rows are enabled.

    18. Promote one model at a time, not all three at once

    Suggested promotion order:
    1. Z06
    2. ZR1
    3. ZR1X

    Reason:
    - Z06 has 6 variants like Grand Sport and will shake out LZ/option normalization with less variant-count difference risk.
    - ZR1/ZR1X have 4 variants and should follow once generic 4-variant model generation is proven.

    For each promotion:
    - set model_registry_promotion.active = TRUE
    - set promoted_to_runtime = TRUE
    - set artifact_path to the reviewed draft artifact
    - keep default_model = FALSE
    - regenerate form-app/data.js through the Stingray generator/registry writer

    19. Runtime verification after promotion

    For each promoted model:
    - form-app/data.js contains the new registry key
    - model switcher shows the model
    - default remains Stingray
    - body style choices are correct
    - trim choices are correct
    - unavailable variants are absent
    - standard equipment appears correctly
    - standard/included options are locked correctly
    - selectable options can be selected/deselected
    - exclusive groups behave like Grand Sport
    - price totals are correct
    - build download filename/export slug is correct
    - dealer submission payload includes the active model key
    - no endpoint/payload/Turnstile drift

    20. Full gates before considering runtime-ready

    Run:
    - .venv/bin/python scripts/validate_workbook_schema.py stingray_master.xlsx
    - .venv/bin/python scripts/generate_stingray_form.py
    - .venv/bin/python scripts/generate_model_form.py --model-key z06
    - .venv/bin/python scripts/generate_model_form.py --model-key zr1
    - .venv/bin/python scripts/generate_model_form.py --model-key zr1x
    - node --test tests/stingray-form-regression.test.mjs
    - node --test tests/stingray-generator-stability.test.mjs
    - node --test tests/multi-model-runtime-switching.test.mjs
    - node --test tests/workbook-schema-standardization.test.mjs
    - new future-model draft/runtime tests

    Manual smoke:
    - local static app
    - model switcher
    - body/trim selection
    - option behavior
    - standard/included summaries
    - price totals
    - build download
    - dealer modal validation
    - dealer payload model scoping

    Recommended phase breakdown

    Phase 7: Review-map and normalize future options/OVS
    - Build the review mapping layer.
    - Resolve section conflicts/unresolved rows/missing RPO/duplicates.
    - Populate *_options and *_ovs.
    - No compatibility copying yet.
    - No runtime promotion.

    Phase 8: Grand Sport compatibility/exclusive rebase
    - Build option-ID resolver.
    - Copy/rebase Grand Sport rules, grouped rules, exclusive groups, and members.
    - Produce unresolved mapping audit.
    - No runtime promotion.

    Phase 9: LZ interiors and runtime metadata
    - Add Z06/ZR1/ZR1X interior scope and components.
    - Add runtime steps/context/section/order-summary/default metadata.
    - Add model assets and presentation metadata.

    Phase 10: Generic model generator
    - Add generate_model_form.py --model-key.
    - Generalize Grand Sport draft path.
    - Generate draft artifacts for Z06/ZR1/ZR1X.

    Phase 11: Accuracy review and cleanup
    - Compare draft artifacts against source sheets.
    - Fix prices, standard equipment, labels, sections, and unresolved rule mappings.
    - Add tests for each model.

    Phase 12: Runtime promotion
    - Promote one model at a time through model_registry_promotion.
    - Regenerate form-app/data.js.
    - Run full gates and manual smoke.

    Key non-goals until the relevant phase is approved

    - Do not directly promote archive preview rows into runtime.
    - Do not promote Z06/ZR1/ZR1X before draft artifacts pass review.
    - Do not copy price rules blindly from Grand Sport.
    - Do not solve missing sections in Python/JS.
    - Do not hardcode future-model compatibility in runtime.
    - Do not change dealer submission endpoint, payload shape, or Turnstile behavior.
    - Do not remove runtime fallbacks until all promoted models have generated metadata.

    Most important practical next step

    Start Phase 7 with a review-map-driven source population pass.

    That is the bottleneck. Once option IDs and OVS statuses are accurate, the shared Grand Sport compatibility/exclusive behavior becomes a deterministic rebase problem instead of a discovery problem.
