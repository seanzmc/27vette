# Asset/media audit report for 2026-06-30

Audit complete. Current repo worktree is clean (git status --short returned no output). I did not edit repo files or generated artifacts. I did patch the stale local Hermes skill reference for asset_map because it still described the old no-hover/no-context-choice shape.

## High-level finding:

The active runtime path is mostly source-of-truth aligned now: workbook metadata discovers the active models, promoted registry rows publish runtime contracts, asset_map feeds generic media fields, and runtime rendering is generic. The main risks are not “missing runtime wiring”; they are structural redundancy and a few remaining code-owned policy decisions that can create drift as more models/assets are added.

## Evidence inspected:

- Generator entrypoints:
  - scripts/generate_form.py
  - scripts/generate_registry.py
  - scripts/corvette_form_generator/model_generation.py
  - scripts/corvette_form_generator/source_assembly.py
- Asset path:
  - scripts/corvette_form_generator/contract.py
  - scripts/corvette_form_generator/asset_map_sync.py
  - scripts/corvette_form_generator/production.py
  - scripts/corvette_form_generator/inspection.py
  - scripts/corvette_form_generator/registry_promotion.py
- Runtime:
  - form-app/app.js
  - form-app/styles.css
  - form-app/data.js
- Metadata/source-of-truth loaders:
  - scripts/corvette_form_generator/model_configs.py
  - scripts/corvette_form_generator/runtime_metadata.py
  - scripts/corvette_form_generator/schema_validation.py
- Tests:
  - tests/test_asset_map_sync.py
  - tests/multi-model-runtime-switching.test.mjs
  - related asset/default metadata assertions in tests/stingray-generator-stability.test.mjs, tests/grand-sport-draft-data.test.mjs, tests/z06-form-data-draft.test.mjs

## Current active model/runtime state:

- Active/generatable workbook models:
  - stingray
  - grand_sport
  - z06
- Promoted runtime models:
  - stingray -> form-output/runtime/stingray-runtime-contract.json
  - grand_sport -> form-output/runtime/grand-sport-runtime-contract.json
  - z06 -> form-output/runtime/z06-runtime-contract.json
- All three promoted artifacts exist and reported 0 generated validation errors.
- All three active models have a full active model_workbook_sources role set.

## Current asset_map state:

- Headers:
  - model_key
  - target_type
  - target_id
  - image_url
  - image_alt
  - image_fit
  - image_position
  - hover_image_url
  - hover_image_alt
  - hover_image_position
  - active
  - notes
- Active rows: 192
- Inactive rows: 2
- Active rows by target type:
  - option: 183
  - model: 3
  - context_choice: 6
- Active duplicate exact keys: 0
- Active rows missing image_url: 0
- Active hover-media rows: 6
- Active wildcard/shared rows: 0

## Generated media counts:

- Stingray:
  - choices: 1416
  - choices with image: 306
  - context choices with image: 2
  - context choices with hover: 2
- Grand Sport:
  - choices: 1428
  - choices with image: 366
  - context choices with image: 2
  - context choices with hover: 2
- Z06:
  - choices: 1434
  - choices with image: 426
  - context choices with image: 2
  - context choices with hover: 2

## Report-only sync probe:
I ran scripts/sync_asset_map.py against a deterministic media URL list built from the current active asset_map URLs only. It did not write anything.

### Result:

- keep: 192
- flag_missing: 268
- writes: 0
- inserts: 0
- unmatched media: 0
- unparseable files: 0
- report dir: /tmp/27vette-asset-audit.To4jiI/report

### Missing-image report summary:

- Stingray: 93 missing
- Grand Sport: 91 missing
- Z06: 84 missing
- All 268 are target_type=option
- Top missing sections:
  - Stingray sec_lpoe_001: 23
  - Stingray sec_stri_001: 18
  - Grand Sport sec_stri_001: 17
  - Z06 sec_stri_001: 17
  - Grand Sport sec_lpoe_001: 16
  - Z06 sec_lpoe_001: 13

## Findings:

1. Good: workbook-owned model discovery and registry promotion are now the primary path.

- generate_form.py discovers active generatable models from workbook metadata, not a hardcoded model map.
- generate_registry.py is the only app registry writer and loads model_registry_promotion.
- model_registry_promotion currently promotes all three active models through runtime-contract artifacts.
- form-app/data.js is generated from promoted artifacts, not manually assembled in runtime code.

Risk: low.

2. Good: runtime media rendering is generic.

- form-app/app.js:320-337 renders card media from generated fields:
  - image_url
  - image_alt
  - image_fit
  - image_position
  - hover_image_url
  - hover_image_alt
  - hover_image_position
- No hardcoded image URL map was found in runtime.
- Runtime tests confirm model assets, paint assets, context choice media, and rendered card media.

Risk: low.

3. Hole: asset_map_sync keys desired/existing targets by (model_key, target_id) instead of (model_key, target_type, target_id).
   Evidence:

- Runtime/generator loader correctly keys assets by (target_type, target_id) in contract.py.
- Sync code collapses target type in multiple places:
  - asset_map_sync.py:390 uses desired[(model_key, option_id)]
  - asset_map_sync.py:411 uses desired[(model_key, target_id)]
  - asset_map_sync.py:426 uses desired[(model_key, target_id)]
  - asset_map_sync.py:436-455 returns existing rows keyed by (model_key, target_id_key)
  - asset_map_sync.py:555 iterates (model_key, target_id), info
    Current data has no active duplicate collisions, but the code shape is now weaker than the workbook contract. Since asset_map supports model, option, and context_choice, the sync planner should preserve target_type in its identity key.

Risk: medium. It is a structural bug waiting for a target-id collision.

Smallest safe pass:

- Change sync plan keys to (model_key, target_type, target_id).
- Add tests with same target_id across two target types.
- Keep report CSV unchanged or add explicit key fields only.
- No workbook writes required.

4. Hole: duplicate active asset_map rows would silently last-win in generator/runtime.
   Evidence:

- contract.py:31-43 builds assets[(target_type, target_id)] = fields with no duplicate check.
- Current workbook has 0 active duplicate exact keys, so this is not an active data bug.
- But if a duplicate is introduced, generated output would silently depend on row order.

Risk: medium. This violates canonical workbook row discipline because ambiguous workbook rows should fail loudly.

Smallest safe pass:

- Add duplicate active (model_key, target_type, target_id) validation in load_asset_map() or schema validation.
- Add a focused test.
- Do not change current workbook rows.

5. Redundancy: 38 active option asset payload groups are repeated across models.
   Evidence:

- Active wildcard/shared rows: 0.
- Repeated identical option media payload groups: 38.
- Examples repeated across Grand Sport, Stingray, and Z06:
  - seat belts: opt_379_001, opt_3a9_001, opt_3f9_001, opt_3m9_001, opt_3n9_001, opt_719_001
  - paints: opt_g26_001, opt_g4z_001, opt_g8g_001, opt_gba_001
- contract.py:35 requires exact model_key, so shared rows cannot reduce this yet.

Risk: low-to-medium. Current output is correct, but workbook maintenance grows with each active model.

Smallest safe pass:

- Add support for model_key="\*" shared asset_map rows:
  - load wildcard first
  - overlay exact model rows second
  - keep exact duplicate rows invalid
- Add parity tests proving current generated artifacts do not change after migration.
- Migrate only obvious identical payloads first, probably paint and seatbelt rows.

6. Hole/noise: sync uses active+selectable option rows as the media coverage policy.
   Evidence:

- asset_map_sync.py:371-397 treats every active/selectable source option as a desired option media target.
- Report-only probe produced 268 flag_missing option rows, including admin/delivery and possibly non-visual sections such as sec_cust_001.
- This creates a useful broad audit list, but it is too broad to equal “should have an image.”

Risk: medium for workflow quality. It can bury real image gaps in expected-no-image rows.

Guideline concern:
Media coverage expectation is content/workbook policy. If not every selectable option should have an image, the script should not define that policy alone.

Smallest safe pass:

- Keep the broad report.
- Add a separate workbook-authored or metadata-derived “image expected” classification before treating a row as a real missing-image gap.
- Avoid seeding blank asset_map rows.
- Keep report-only default.

7. Redundancy: active model generation still has two assembly paths.
   Evidence:

- source_assembly.py:35-44 routes Stingray through production.build_production_source_data().
- source_assembly.py:46-56 routes Grand Sport/Z06 through inspection/preview/draft builders.
- Both paths now merge asset_map media:
  - Stingray: production.py:203-204, 282-284, 390-391
  - Grand Sport/Z06: inspection.py:668-697, 976, 1016, 1063-1064
- Both paths finalize through build_model_runtime_contract(), which is good.
- Compatibility artifact writing remains Stingray-only in production.py:651-690.

Risk: medium. Runtime output is currently aligned, but logic is duplicated. Every metadata/media change must be kept consistent in production and inspection code.

Smallest safe pass:

- Do not remove Stingray compatibility artifacts yet.
- Extract shared media/context-choice/choice-row assembly helpers first.
- Prove parity for all three runtime contracts.
- Only then consider routing Stingray through the same source assembly as the other active models.

8. Source-of-truth debt: hardcoded default-selected display derivation allowlist (resolved by Phase 3).

   Status update 2026-06-30: resolved by Phase 3. The hardcoded Python allowlist was removed in favor of workbook-authored `default_selection_rules.display_behavior`; current generated runtime behavior was preserved. See `docs/asset-media-drift/phase-3-default-selected-display-authoring.md` and the active route map `docs/asset-media-drift-remediation-spec-2026-06-30.md` for closure evidence and remaining guardrail follow-up.

   Historical evidence at audit time:

- runtime_metadata.py:20-26 had \_DEFAULT_SELECTED_DISPLAY_RULE_IDS_BY_MODEL with specific model/rule IDs.
- runtime_metadata.py:302-340 gated derivation through that hardcoded allowlist.
- Workbook default_selection_rules were still emitted and used, but this allowlist decided which defaults became display_behavior=default_selected.

Risk at audit time: medium. This was an explicit model/rule-specific code gate. It was documented as a migration guard, but it became architecture debt under the “boring scripts” guideline.

Completed smallest safe pass:

- Moved default-selected presentation intent fully into workbook-authored rows/metadata.
- Kept generated output parity.
- Added tests that fail if the old Python allowlist is reintroduced, if the new workbook column contains an invalid value, or if the live workbook's populated default-selection display rows drift from the approved three.

9. Minor source-of-truth/presentation debt: a few code fallbacks and stale labels remain.
   Evidence:

- model_configs.py:150-159 has Grand Sport section label overrides in code.
- model_configs.py:161-169 has stale Grand Sport notes saying read-only inspection/not activated, while Grand Sport is promoted.
- production.py:161-169 remains explicitly Stingray-only.
- production.py:397-403 still validates active_for_stingray in the legacy path.
- app.js:1163-1169 hardcodes sec_incl_001 for auto-added summary bucket routing.

Risk: low-to-medium. These are not breaking current runtime behavior, but they are the kind of code-owned model/presentation policy that will accumulate.

Smallest safe pass:

- Separate doc/stale-note cleanup from behavior changes.
- For behavior/presentation routing, prefer workbook/generated metadata before editing runtime conditions.

## Validation run:

- .venv/bin/python scripts/validate_workbook_schema.py stingray_master.xlsx
  - passed, status valid, 0 issues
- .venv/bin/python -m pytest tests/test_asset_map_sync.py -q
  - passed, 19 tests
- node --test tests/multi-model-runtime-switching.test.mjs
  - passed, 46 tests
- Report-only sync probe:
  - passed, no writes/inserts, manifest generated under /tmp/27vette-asset-audit.To4jiI/report

Gates not run:

- I did not regenerate model artifacts or form-app/data.js; this was a report-only audit and current artifacts already existed.
- I did not run the full Node suite; targeted runtime/model switching and sync tests covered the audited surfaces.
- I did not run live WordPress media fetch; deterministic media list was enough for the relationship audit and avoids mutable external results.
- I did not run browser manual smoke; no runtime behavior was changed.

## Recommended next pass:
A. First: fix asset_map_sync identity keys and add duplicate active asset_map validation.
Reason: small, no workbook data change, closes the highest structural risk before more media/model growth.

B. Second: add media coverage intent classification to reduce the 268 missing-image noise.
Reason: preserves report-first workflow while avoiding script-owned policy.

C. Third: wildcard/shared asset_map support and migrate obvious identical rows.
Reason: reduces workbook redundancy after identity/validation is safe.

D. Later: converge Stingray/Grand Sport/Z06 generation assembly.
Reason: important, but larger and higher risk because Stingray still has compatibility artifacts.
