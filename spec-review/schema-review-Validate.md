Review complete. I treated this as report/spec review only and made no edits.

    What I verified:
    - Repo is clean: git status --short && git diff --stat returned no output.
    - Workbook schema currently validates:
      .venv/bin/python scripts/validate_workbook_schema.py stingray_master.xlsx
      returned status: valid, issue_count: 0.
    - The cited workbook/runtime/generator issues are mostly valid against the current repo.

    Verdict:
    The attached findings are directionally correct and useful. I would tighten them in two places:

    1. The codebase is not purely “two-model hardcoded” anymore.
       There is already a partial metadata substrate in scripts/corvette_form_generator/runtime_metadata.py, especially load_model_metadata() and load_model_config_overrides(), which read:
       - model_master
       - model_workbook_sources
       - model_variants

       But this substrate is only used to override known Python ModelConfig constants. It does not yet discover and generate arbitrary active/promoted models.

    2. variant_master does contain inactive future-model variants, but it does not directly carry model_key.
       Current headers are:
       - variant_id
       - model_year
       - trim_level
       - body_style
       - display_name
       - base_price
       - display_order
       - active

       Future variants are inferable by IDs:
       - Z06: 1lz_h07, 2lz_h07, 3lz_h07, 1lz_h67, 2lz_h67, 3lz_h67
       - ZR1: likely 1lz_r07, 3lz_r07, 1lz_r67, 3lz_r67
       - ZR1X: likely 1lz_s07, 3lz_s07, 1lz_s67, 3lz_s67

       The model_variants metadata table is therefore the right place to explicitly bind those IDs to model keys.

    Validated findings by priority:

    P1 valid: schema validation is still model/sheet-name hardcoded
    Evidence:
    - scripts/corvette_form_generator/schema_validation.py:13-78
    - Hardcoded examples:
      - stingray_options
      - grandSport_options
      - rule_mapping
      - grandSport_rule_mapping
      - price_rules
      - grandSport_price_rules
      - lt_interiors
      - LZ_Interiors

    Correction:
    - The validator already knows about LZ_Interiors, but it validates it as a named sheet, not as a source role for active LZ models.

    P1 valid: app-data promotion is two-model only
    Evidence:
    - scripts/generate_stingray_form.py:197-243
    - load_grand_sport_registry_data() explicitly loads Grand Sport draft/current app data.
    - build_app_data_registry() builds Stingray, then optionally Grand Sport.
    - Default model is hardcoded to "stingray".

    Correction:
    - The attached finding is accurate, but this should be solved as registry promotion, not as part of raw ingestion.

    P1 valid: LZ interiors exist but are not repeatably wired
    Evidence from workbook:
    - LZ_Interiors: hidden, 132 rows, trims 1LZ, 2LZ, 3LZ, 3LZ_R6X
    - lt_interiors: visible, 132 rows, trims 1LT, 2LT, 3LT, 3LT_R6X
    - model_interior_scope: 132 rows, all grand_sport
    - interior_components: stingray:197, grand_sport:198
    - No Z06/ZR1/ZR1X interior scope/component rows yet.

    Evidence from code:
    - scripts/corvette_form_generator/inspection.py:468-539
    - build_grand_sport_interiors() reads lt_interiors directly.
    - Emitted source_sheet is hardcoded to "lt_interiors".
    - active_for_grand_sport is hardcoded true.

    Correction:
    - This is more than a missing sheet config. The interior builder itself is still Grand Sport/LT-shaped. LZ support needs source-sheet config and output-field cleanup.

    P1 valid: runtime contains model presentation facts
    Evidence:
    - form-app/app.js:104-119
    - vehicleSetupHighlights hardcodes Stingray and Grand Sport copy/facts:
      - LS6
      - horsepower
      - Magnetic Ride Control
      - Z52

    Correction:
    - This is mostly presentation metadata, but because it includes model-specific performance facts, it should become workbook/generated registry metadata before adding more models.

    P1 valid: runtime has a remaining business exception
    Evidence:
    - form-app/app.js:868
    - if (choice.rpo === "GBA" && rule.source_id === "opt_zyc_001") continue;

    Correction:
    - This is the highest-risk runtime business exception in the findings because it directly changes disablement behavior. It should move to generated rule metadata or a workbook-authored runtime exception table before model expansion.

    P2 valid: order summary metadata is incomplete
    Evidence from workbook:
    - order_summary_sections: 11 rows, all stingray
    - step_order_summary_map: 13 rows, all stingray

    Evidence from runtime:
    - form-app/app.js:132-161
    - form-app/app.js:932-943
    - Runtime falls back to hardcoded order-summary sections and step map when generated data is absent.

    Correction:
    - The runtime fallback is acceptable as a compatibility fallback, but new promoted models should be required to have generated data.orderSummary.

    P2 valid: Grand Sport scripts are not generic enough
    Evidence:
    - scripts/corvette_form_generator/model_configs.py:150-218
      - only STINGRAY_MODEL and GRAND_SPORT_MODEL
    - scripts/generate_grand_sport_form.py
      - imports GRAND_SPORT_MODEL
    - scripts/build_grand_sport_rule_sources.py
      - imports GRAND_SPORT_MODEL
      - reads lt_interiors directly at line 165

    Correction:
    - The existing ModelConfig shape is reusable, but model discovery and command entrypoints are still specific.

    Recommended implementation spec

    Title:
    Prepare repeatable multi-model schema/generator/runtime substrate for Z06, ZR1, and ZR1X

    Diagnosis:
    The workbook already has partial future-model evidence and a partial metadata substrate, but the active generation path is still split between:
    - Stingray production generation
    - Grand Sport draft/inspection generation
    - runtime fallbacks/hardcoded presentation
    - schema validation hardcoded to Stingray/Grand Sport sheet names

    Root cause:
    The pipeline has metadata tables but no full active-model loop. Known-model Python constants still drive generation, validation, interiors, registry promotion, and runtime fallbacks.

    Risk level:
    High if done as one broad migration, because the live app supports active dealer submissions.

    Recommended scope:
    Mixed:
    - workbook metadata substrate
    - generator validation/genericity
    - runtime metadata consumption
    - no raw order-guide ingestion yet
    - no live promotion of Z06/ZR1/ZR1X yet unless separately approved

    Exact files to inspect/change:

    Workbook sheets:
    - model_master
    - model_workbook_sources
    - model_variants
    - runtime_steps
    - context_section_master
    - section_presentation
    - model_interior_scope
    - interior_components
    - asset_map
    - order_summary_sections
    - step_order_summary_map
    - possibly new sheet: model_presentation
    - possibly new sheet: runtime_rule_exceptions
    - source-template sheets for future models, but preferably header/schema only in the first pass:
      - z06_options
      - z06_ovs
      - z06_rule_mapping
      - z06_price_rules
      - z06_rule_groups
      - z06_rule_group_members
      - z06_exclusive_groups
      - z06_exclusive_members
      - z06_variant_overrides
      - matching zr1_*
      - matching zr1x_*

    Generator/code files:
    - scripts/corvette_form_generator/schema_validation.py
    - scripts/corvette_form_generator/model_configs.py
    - scripts/corvette_form_generator/runtime_metadata.py
    - scripts/corvette_form_generator/inspection.py
    - scripts/generate_stingray_form.py
    - scripts/generate_grand_sport_form.py
    - scripts/build_grand_sport_rule_sources.py
    - possibly new:
      - scripts/generate_model_form.py
      - scripts/build_model_rule_sources.py
      - scripts/corvette_form_generator/model_discovery.py

    Runtime files:
    - form-app/app.js
    - form-app/data.js only through generator output, not hand edits

    Tests:
    - existing:
      - tests/stingray-form-regression.test.mjs
      - tests/stingray-generator-stability.test.mjs
      - tests/grand-sport-contract-preview.test.mjs
      - tests/grand-sport-draft-data.test.mjs
      - tests/grand-sport-rule-audit.test.mjs
      - tests/multi-model-runtime-switching.test.mjs
    - likely new/expanded:
      - schema validation tests for metadata-derived active models
      - registry promotion tests
      - generated model-presentation contract tests
      - runtime exception contract tests
      - LZ interior source-selection tests

    Constraints to preserve:
    - No live runtime behavior changes during substrate-only passes.
    - No dealer submission endpoint, payload-shape, or Turnstile changes.
    - No new dependencies unless explicitly approved.
    - No runtime hardcoded model/RPO business facts when workbook rows can own them.
    - Do not edit generated form_* sheets directly.
    - Do not hand-edit form-app/data.js; regenerate it.
    - Preserve visual layout unless a later approved pass explicitly targets UI.
    - Preserve current Stingray and Grand Sport generated output parity unless a specific migration intentionally changes it.
    - Close Excel before any workbook write.
    - Refuse workbook write if ~$stingray_master.xlsx exists and is not confirmed stale.
    - Use .venv/bin/python, not system Python.
    - Verify workbook saves by rereading the saved workbook from disk.

    Non-goals for this first implementation pass:
    - Do not parse raw Z06/ZR1/ZR1X order guides yet.
    - Do not activate Z06/ZR1/ZR1X in the live registry yet.
    - Do not promote archive sheets to live customer-facing data yet.
    - Do not refactor frontend layout.
    - Do not remove runtime fallbacks until generated data exists for all promoted models.
    - Do not seed copied compatibility rules until target option IDs have been resolved.

    Recommended phased fix path:

    Phase 1: Metadata substrate and validation discovery
    Goal:
    Make validation understand active workbook metadata without changing generated app behavior.

    Work:
    - Update schema_validation.py to derive active model source sheets from model_master + model_workbook_sources.
    - Keep current Stingray/Grand Sport validations as fallback/compatibility.
    - Validate required source roles per active/promoted model.
    - Validate headers by role, not by exact known sheet name.
    - Validate option/OVS/rule/price/exclusive source sheets for every active model.
    - Add inactive Z06/ZR1/ZR1X metadata rows only if approved, but do not require their source sheets until marked active/promoted.

    Risk:
    Medium. Validator behavior changes but runtime should not.

    Rollback:
    Revert validator changes or deactivate new metadata rows.

    Validation:
    - .venv/bin/python scripts/validate_workbook_schema.py stingray_master.xlsx
    - full current test suite if validator tests are added.

    Phase 2: LZ interior source ownership
    Goal:
    Let a model config/metadata row choose lt_interiors vs LZ_Interiors.

    Work:
    - Add an interior_source_sheet role or equivalent metadata field.
    - Refactor build_grand_sport_interiors() into generic build_model_interiors(config).
    - Stop hardcoding lt_interiors, source_sheet: "lt_interiors", and active_for_grand_sport.
    - Add tests proving Grand Sport output remains unchanged when still scoped to current rows.
    - Add Z06/ZR1/ZR1X interior metadata only as inactive/scope-ready rows if approved.

    Risk:
    High if it alters current Grand Sport interiors. Must be parity-tested.

    Rollback:
    Revert generator changes or point metadata back to old source.

    Validation:
    - .venv/bin/python scripts/generate_grand_sport_form.py
    - node --test tests/grand-sport-draft-data.test.mjs
    - node --test tests/grand-sport-contract-preview.test.mjs

    Phase 3: Workbook-owned model presentation metadata
    Goal:
    Move vehicleSetupHighlights business/presentation facts out of form-app/app.js.

    Work:
    - Add workbook sheet, likely model_presentation, with fields:
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
    - Emit presentation metadata into each model registry entry.
    - Change activeModelHighlight() to read generated registry data, with current hardcoded copy only as temporary fallback.
    - Add tests that Stingray/Grand Sport generated registry contains the current copy exactly.

    Risk:
    Medium. Presentation-only, but customer-facing.

    Rollback:
    Deactivate workbook rows or restore runtime fallback.

    Validation:
    - node --test tests/multi-model-runtime-switching.test.mjs
    - node --test tests/stingray-form-regression.test.mjs

    Phase 4: Runtime business exception migration
    Goal:
    Remove choice.rpo === "GBA" && rule.source_id === "opt_zyc_001" from runtime JS.

    Work:
    - Decide whether this belongs in:
      - normalized rule data, preferred if the source rule can express it; or
      - new workbook table runtime_rule_exceptions, if it is truly an evaluator exception.
    - Emit generated exception metadata.
    - Replace the hardcoded branch with generic generated exception handling.
    - Add regression tests for the current GBA/ZYC behavior before and after migration.

    Risk:
    High. This changes rule evaluation if done incorrectly.

    Rollback:
    Revert runtime/generator change or deactivate exception row.

    Validation:
    - targeted runtime rule test
    - node --test tests/stingray-form-regression.test.mjs
    - manual smoke of selecting GBA and ZYC-related option paths

    Phase 5: Generic model draft generator
    Goal:
    Allow a command to generate a draft contract for any workbook-backed model key.

    Work:
    - Add scripts/generate_model_form.py --model-key <key> or equivalent.
    - Discover config from workbook metadata, with Python constants only as compatibility defaults.
    - Keep Grand Sport command as wrapper or compatibility alias.
    - Generalize Grand Sport-specific validation messages where reasonable.
    - Keep app registry promotion separate.

    Risk:
    Medium/high. Broad generator path, but can be draft-only.

    Rollback:
    Keep old Grand Sport command path intact until parity passes.

    Validation:
    - .venv/bin/python scripts/generate_grand_sport_form.py
    - .venv/bin/python scripts/generate_model_form.py --model-key grand_sport
    - compare Grand Sport draft artifact parity
    - Grand Sport test suite

    Phase 6: Generic registry promotion
    Goal:
    Replace two-model registry building with a metadata-driven promoted-model registry.

    Work:
    - Add promotion status to model_master or a dedicated promotion sheet:
      - active
      - promoted_to_runtime
      - default_model
      - draft_artifact_path or export_slug
    - Refactor build_app_data_registry() to loop promoted model artifacts.
    - Preserve window.STINGRAY_FORM_DATA alias.
    - Keep default model as workbook-owned metadata.
    - Do not promote Z06/ZR1/ZR1X until their generated data is reviewed and approved.

    Risk:
    High because it affects live form-app/data.js.

    Rollback:
    Revert registry writer or set only Stingray/Grand Sport as promoted.

    Validation:
    - full current suite
    - local static app smoke:
      - model switching
      - body/trim selection
      - option select/deselect
      - price totals
      - build download
      - dealer submission modal validation
      - dealer payload model scoping

    Recommended immediate next step:
    Approve Phase 1 only: metadata-derived schema validation, with no runtime or generated-data behavior changes. That gives you a safer foundation before touching interiors, runtime presentation, or registry promotion.

    Gate results from this review:
    - git status --short && git diff --stat: clean
    - .venv/bin/python scripts/validate_workbook_schema.py stingray_master.xlsx: passed, 0 issues

    What changed:
    - Nothing.

    What did not change:
    - Workbook
    - generated form_* sheets
    - form-output
    - form-app/data.js
    - runtime behavior
    - dealer submission path/payload
    - tests/config/docs

    Manual verification still pending:
    - I did not run mutating generators because this was a review/spec pass.
    - I did not inspect every archived Z06/ZR1/ZR1X row for semantic readiness; I only verified the hidden archive sheets exist and the workbook metadata gaps described above are real.
