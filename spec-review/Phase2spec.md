    Phase 1 progress review

    I checked the current repo state before drafting Phase 2.

    Current status:
    - git status --short && git diff --stat: clean output
    - Excel lock check: ~$stingray_master.xlsx not present
    - .venv/bin/python scripts/validate_workbook_schema.py stingray_master.xlsx: valid, 0 issues
    - .venv/bin/python -m unittest tests/test_schema_validation_metadata.py tests/test_model_config_metadata.py: 11 tests passed

    Phase 1 appears integrated cleanly. The repo now has metadata-derived validation tests and the workbook still validates.

    What Phase 1 unlocked:
    - schema_validation.py can validate active source sheets through model_master + model_workbook_sources.
    - Adding new source roles now needs deliberate registration in:
      - scripts/corvette_form_generator/schema_validation.py
      - scripts/corvette_form_generator/runtime_metadata.py
      - ModelConfig if generators consume the role

    What Phase 1 did not yet solve:
    - interior_source_sheet is not a known source role yet.
    - ModelConfig has no interior_source_sheet.
    - build_grand_sport_interiors() still hardcodes:
      - lt_interiors
      - source_sheet: "lt_interiors"
      - active_for_grand_sport: True
      - LT fallback trims
    - build_grand_sport_rule_sources.py still reads lt_interiors directly in interior_combination_codes().

    Phase 2 spec: LZ interior source ownership

    Diagnosis:
    The workbook already contains both interior source sheets:

    - lt_interiors
      - visible
      - 132 rows
      - trims: 1LT, 2LT, 3LT, 3LT_R6X
    - LZ_Interiors
      - hidden
      - 132 rows
      - trims: 1LZ, 2LZ, 3LZ, 3LZ_R6X
      - headers match lt_interiors

    But the generator path cannot choose between them by model metadata yet.

    Current workbook metadata:
    - model_workbook_sources has 19 rows.
    - Active roles exist for Stingray and Grand Sport source/options/rules/color overrides.
    - No interior_source_sheet role exists yet.
    - model_interior_scope has 132 rows, all grand_sport.
    - interior_components has:
      - stingray: 197 rows
      - grand_sport: 198 rows
      - no Z06/ZR1/ZR1X rows yet.

    Current code evidence:
    - scripts/corvette_form_generator/model_config.py
      - ModelConfig has no interior_source_sheet.
    - scripts/corvette_form_generator/runtime_metadata.py
      - _MODEL_CONFIG_SOURCE_ROLES does not include interior_source_sheet.
      - load_model_config_overrides() cannot load it.
    - scripts/corvette_form_generator/schema_validation.py
      - Phase 1 source-role validation does not yet know interior_source_sheet.
    - scripts/corvette_form_generator/inspection.py:468-541
      - build_grand_sport_interiors() reads lt_interiors directly.
      - emits source_sheet: "lt_interiors".
      - emits active_for_grand_sport: True.
      - has LT-specific fallback trim logic.
    - scripts/build_grand_sport_rule_sources.py:163-173
      - interior_combination_codes() reads lt_interiors directly.

    Root cause:
    Interior source ownership is still split:
    - source data lives in workbook sheets,
    - model scoping lives in model_interior_scope,
    - component metadata lives in interior_components,
    - but the generator still chooses the interior source sheet in Python.

    Change classification:
    - Mixed code + workbook metadata.
    - Generator/source-of-truth migration.
    - No runtime UI behavior change intended.
    - No live app promotion change.
    - No Z06/ZR1/ZR1X activation.

    Risk level:
    High if generated interiors drift. Grand Sport draft output must remain byte/semantic parity except expected timestamps if generators run.

    Exact files to change:

    Code:
    - scripts/corvette_form_generator/model_config.py
      - Add interior_source_sheet: str = "lt_interiors" to ModelConfig.

    - scripts/corvette_form_generator/runtime_metadata.py
      - Add interior_source_sheet to _MODEL_CONFIG_SOURCE_ROLES.
      - Load sources.get("interior_source_sheet") into config.with_overrides().

    - scripts/corvette_form_generator/schema_validation.py
      - Add interior_source_sheet to known source roles.
      - Validate active interior source sheets by role:
        - sheet exists
        - headers match other active interior source sheets where applicable
        - boolean columns: active_for_stingray, requires_r6x
        - price column: Price
      - Preserve existing direct lt_interiors / LZ_Interiors compatibility check.

    - scripts/corvette_form_generator/inspection.py
      - Refactor build_grand_sport_interiors(config) into generic build_model_interiors(config).
      - Keep build_grand_sport_interiors(config) as a compatibility wrapper if needed.
      - Read rows_from_sheet(wb, config.interior_source_sheet).
      - Emit source_sheet from config.interior_source_sheet.
      - Replace hardcoded active_for_grand_sport: True with a model-key-derived active flag, while preserving current Grand Sport output:
        - Grand Sport interiors still include active_for_grand_sport: True
        - Grand Sport interiors still include active_for_stingray: False
      - Replace LT-specific fallback trim logic with generic fallback derived from config.variant_ids, while preserving Grand Sport behavior when model_interior_scope is present.

    - scripts/build_grand_sport_rule_sources.py
      - Load config overrides before rule audit processing.
      - Change interior_combination_codes(wb) to interior_combination_codes(wb, config).
      - Read rows_from_sheet(wb, config.interior_source_sheet) instead of lt_interiors.

    Tests:
    - tests/test_model_config_metadata.py
      - Add test proving interior_source_sheet can be loaded from model_workbook_sources.

    - tests/test_schema_validation_metadata.py
      - Add test proving interior_source_sheet is accepted as a known role.
      - Add test proving missing active interior source sheet is reported.
      - Add test proving LZ_Interiors can be used as a metadata-discovered interior source sheet.

    - tests/grand-sport-draft-data.test.mjs
      - Update Grand Sport interior test to assert:
        - draft still has 132 interiors
        - all emitted interiors have source_sheet === "lt_interiors"
        - all emitted interiors preserve active_for_grand_sport === true
        - all emitted interiors preserve active_for_stingray === false
        - implementation uses config.interior_source_sheet
        - implementation no longer hardcodes source sheet selection.

    - tests/grand-sport-rule-audit.test.mjs
      - Add or update assertion proving the rule audit uses config.interior_source_sheet for interior code suppression, not a direct lt_interiors string.

    Workbook:
    - stingray_master.xlsx
      - Add active model_workbook_sources rows:
        - stingray, interior_source_sheet, lt_interiors, True
        - grand_sport, interior_source_sheet, lt_interiors, True
      - No Z06/ZR1/ZR1X rows in this phase unless separately approved.

    Workbook safety:
    - Check ~$stingray_master.xlsx before writing.
    - Use the project safe-save helper.
    - Reread the saved workbook and verify the new rows are present.
    - Run package validation after save.

    Explicit non-goals:
    - Do not activate Z06, ZR1, or ZR1X.
    - Do not add Z06/ZR1/ZR1X interior scope rows.
    - Do not duplicate LZ_Interiors.
    - Do not change form-app/app.js.
    - Do not change dealer submission endpoint/payload/Turnstile behavior.
    - Do not hand-edit generated form_* sheets.
    - Do not hand-edit form-app/data.js.
    - Do not refactor the full Grand Sport generator into a generic model generator yet; that remains Phase 5.
    - Do not migrate model presentation or runtime GBA/ZYC exception yet.
    - Do not change Stingray production interior generation behavior in scripts/generate_stingray_form.py during this phase unless a test exposes a necessary config compatibility issue.

    Constraints repeated back:
    - Preserve current Stingray runtime behavior.
    - Preserve current Grand Sport draft interior output.
    - No new dependencies.
    - Workbook owns the model-to-interior-source relationship.
    - Generator should read source metadata generically.
    - Runtime should not gain model-specific business rules.
    - Generated timestamp-only drift should be reverted unless the generated content intentionally changed.
    - Any workbook write must be verified on disk before claiming success.

    Implementation outline:
    1. Write failing tests for interior_source_sheet config metadata and schema validation.
    2. Add interior_source_sheet to ModelConfig, runtime metadata roles, and schema validation roles.
    3. Safely add workbook metadata rows for Stingray and Grand Sport.
    4. Refactor Grand Sport interior builder to use config.interior_source_sheet.
    5. Refactor Grand Sport rule audit interior code lookup to use config.interior_source_sheet.
    6. Run generators/tests and compare generated output.
    7. Revert timestamp-only generated artifact drift if no semantic generated output changed.
    8. Handoff with exact changed workbook rows, files, gates, and any residual risks.

    Validation plan:
    - Workbook/package:
      - .venv/bin/python scripts/validate_workbook_package.py stingray_master.xlsx
      - .venv/bin/python scripts/validate_workbook_schema.py stingray_master.xlsx

    - Focused Python:
      - .venv/bin/python -m unittest tests/test_model_config_metadata.py
      - .venv/bin/python -m unittest tests/test_schema_validation_metadata.py

    - Grand Sport generator:
      - .venv/bin/python scripts/generate_grand_sport_form.py

    - Grand Sport tests:
      - node --test tests/grand-sport-draft-data.test.mjs
      - node --test tests/grand-sport-contract-preview.test.mjs
      - node --test tests/grand-sport-rule-audit.test.mjs

    - Regression safety:
      - node --test tests/stingray-generator-stability.test.mjs
      - node --test tests/workbook-schema-standardization.test.mjs
      - optionally node --test tests/multi-model-runtime-switching.test.mjs if generated app data or runtime-facing contracts drift unexpectedly.

    Rollback:
    - Code rollback:
      - revert changes to model_config.py, runtime_metadata.py, schema_validation.py, inspection.py, and build_grand_sport_rule_sources.py.
    - Workbook rollback:
      - remove/deactivate the new interior_source_sheet rows from model_workbook_sources.
      - restore safe-save backup if needed.
    - Generated artifacts:
      - revert form-output/inspection/* timestamp-only drift.

    Acceptance criteria:
    - model_workbook_sources owns current active models’ interior source sheet.
    - Grand Sport draft still emits exactly 132 interiors.
    - Grand Sport draft still uses LT interiors and emits source_sheet: "lt_interiors".
    - Grand Sport output still has active_for_grand_sport === true and active_for_stingray === false.
    - The code path can select LZ_Interiors through config/metadata without adding model-specific Python branches.
    - Workbook schema remains valid.
    - No runtime behavior or live app data changes.

    Approval request:
    Approve this Phase 2 spec and I’ll implement only this interior source ownership pass.
