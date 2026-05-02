# 27vette Current Context

## Current status

- Stingray functional baseline is stable.
- Multi-model registry is active.
- Stingray and Grand Sport both load through `window.CORVETTE_FORM_DATA`.
- Stingray generator output is stable and protected by regression/generator-stability tests.
- Grand Sport runtime loads and Base Interior is populated.
- Grand Sport has model-scoped interiors, including EL9 only in Grand Sport; Stingray EL9 remains inactive.
- Grand Sport exclusive groups are implemented and browser-checked.
- Recent source-of-truth cleanup moved several Stingray generator patches into workbook data.
- Current likely next phase: Grand Sport cleanup/rules/pricing, using the cleaned Stingray workflow as the pattern.

## Validation commands

Use targeted tests first when possible, then full gates once per pass.

Core generator:
`.venv/bin/python scripts/generate_stingray_form.py`

Core tests:
`node --test tests/stingray-form-regression.test.mjs`
`node --test tests/stingray-generator-stability.test.mjs`
`node --test tests/grand-sport-contract-preview.test.mjs`
`node --test tests/grand-sport-draft-data.test.mjs`
`node --test tests/multi-model-runtime-switching.test.mjs`

## Hard boundaries

- Do not alter Stingray behavior unless the task explicitly says so.
- Do not wire Formidable yet.
- Do not change runtime/UI/export schema unless explicitly approved.
- Prefer workbook/source data changes over Python patches.
- Prefer model config/generator data changes over runtime branches.
- Keep raw `source_detail_raw` available for audit/rule extraction.
- Do not solve bad source data by hiding or aliasing it in Python unless there is a documented reason.

## Source-of-truth rules

- Workbook/source tables should own business data and cleanup decisions.
- Python should read clean source data, validate it, and generate app data.
- Runtime should render and evaluate generated data, not infer Corvette-specific business rules.
- If a row is not real maintained source data, remove it from the workbook/source tables. Do not preserve bad rows with alias, hiding, or suppression logic unless there is a documented reason.

## Completed Stingray source cleanup

- Moved display behavior, section mode/order, manual rules, D30/R6X price row, and several inline option corrections into workbook data.
- Added workbook fields:
  - `stingray_master.display_behavior`
  - `price_rules.body_style_scope`
  - `lt_interiors.active_for_stingray`
  - `lt_interiors.requires_r6x`
  - `lt_interiors.included_option_id`
- Deleted duplicate Stingray engine-cover `_002` source rows and removed matching Python alias/consolidation logic.
- Remaining Stingray Python-bound areas include hidden sections, interior component/pricing helpers, and other explicitly deferred cleanup.

## Grand Sport current state

- Grand Sport data is generated through the shared scaffold and model config.
- Grand Sport draft/runtime data exists in the registry but is still incomplete for full production use.
- Grand Sport has interiors populated from `architectureAudit/grand_sport_interiors_refactor.csv`.
- Grand Sport has 5 exclusive groups implemented:
  - `gs_excl_ls6_engine_covers`
  - `gs_excl_center_caps`
  - `gs_excl_indoor_car_covers`
  - `gs_excl_rear_script_badges`
  - `gs_excl_suede_compartment_liners`
- Grand Sport still needs focused cleanup for rules, price rules, text cleanup, display order, and section placement.
- Grand Sport should be normalized to match the Stingray workbook/source-data workflow, not handled through a separate workbook/schema or accumulating Python patches.

## Current task guidance

Use short, scoped prompts. Avoid restating full history.
For each pass:

1. Read this file and the current phase spec.
2. Inspect only relevant files.
3. Make the smallest approved change.
4. Run targeted tests first.
5. Run full gates once at the end.
6. Report briefly: files changed, behavior changed, tests run/results, manual checks needed.
