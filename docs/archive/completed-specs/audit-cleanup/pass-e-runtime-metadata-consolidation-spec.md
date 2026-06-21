# Pass E Spec — Runtime Metadata Consolidation

## Status

Completed for approved option (a): complete promoted-model coverage for `runtime_steps`, `context_section_master`, `order_summary_sections`, and `step_order_summary_map`; classify but do not migrate/delete `section_presentation`, `context_choice_copy`, `runtime_rule_exceptions`, or variant override topology. See `docs/audit-cleanup/pass-e-runtime-metadata-inventory.md` for the final inventory.

## User intent

After Passes A-D, answer the remaining workbook frustration: runtime metadata sheets are real, but unevenly populated. Decide what should stay workbook-owned, what should be completed across active models, what can later be retired from JavaScript/Python fallback paths, and what is not safe to delete.

This pass is not audit-junk deletion. The audit-only sheets (`option_audit_groups`, `option_audit_group_members`, `rule_review_groups`) were handled by Pass A. Pass E focuses on runtime/generator metadata sheets that can affect generated contracts or browser behavior.

## Diagnosis

Root cause: runtime metadata ownership is partial and inconsistent by model. Several sheets were created to move hardcoded form behavior out of Python/JavaScript, but only some models have workbook rows. The generators then use a mix of workbook rows and fallback constants. That makes the sheets look disjointed even when they are carrying useful behavior.

Evidence inspected:

- `docs/audit-cleanup-overview.md:135` defines Pass E and names the target sheets.
- `AGENTS.md:35` says the live app supports Stingray, Grand Sport, and Z06 and treats workbook source tables as the current form source of truth.
- `scripts/corvette_form_generator/runtime_metadata.py:88` `load_runtime_steps()` reads `runtime_steps`, but falls back to Python model config if no active rows exist for a model.
- `scripts/corvette_form_generator/runtime_metadata.py:125` `load_context_sections()` reads `context_section_master`, but falls back to Python model config if no active rows exist.
- `scripts/corvette_form_generator/runtime_metadata.py:158` `load_section_presentation()` reads `section_presentation` with duplicate active-row protection.
- `scripts/corvette_form_generator/runtime_metadata.py:194` `load_variant_option_overrides()` normalizes both global `variant_option_overrides` and model-scoped fallback sheets such as `grandSport_variant_overrides` / `z06_variant_overrides`.
- `scripts/corvette_form_generator/runtime_metadata.py:245` `load_runtime_rule_exceptions()` reads `runtime_rule_exceptions`.
- `scripts/corvette_form_generator/runtime_metadata.py:263` `load_order_summary_metadata()` reads `order_summary_sections` and `step_order_summary_map`.
- `scripts/corvette_form_generator/production.py:188` through `production.py:216` loads the Pass E metadata into the Stingray production build.
- `scripts/corvette_form_generator/production.py:256` through `production.py:358` applies section presentation, steps, context choices, and variant overrides into generated sections/choices.
- `scripts/corvette_form_generator/production.py:830` through `production.py:841` emits `steps`, `sections`, `contextChoices`, `runtimeRuleExceptions`, and `orderSummary` into live app data.
- `scripts/corvette_form_generator/inspection.py:643` through `inspection.py:660` uses the same runtime metadata loaders for Grand Sport/Z06 preview and draft generation.
- `scripts/corvette_form_generator/inspection.py:929` through `inspection.py:935` emits `steps`, `sections`, and `contextChoices` in preview artifacts; `inspection.py:1173` through `inspection.py:1179` carries them into draft/runtime-contract data.
- `form-app/app.js:173` consumes generated `data.steps`.
- `form-app/app.js:609` consumes generated `data.runtimeRuleExceptions`.
- `form-app/app.js:1068` through `app.js:1080` consumes generated `data.orderSummary` when present and falls back to hardcoded JS order-summary constants when absent.
- `form-app/app.js:2042`, `app.js:2057`, `app.js:2367`, and `app.js:2458` consume generated `data.contextChoices`.
- `tests/stingray-generator-stability.test.mjs:348` through `tests/stingray-generator-stability.test.mjs:480` already protects workbook ownership of Stingray variant overrides and Phase 6 step/presentation metadata.
- `tests/stingray-form-regression.test.mjs:1751` through `tests/stingray-form-regression.test.mjs:1753` and `tests/stingray-form-regression.test.mjs:2153` through `tests/stingray-form-regression.test.mjs:2158` protect Stingray runtime rule exceptions.
- `tests/workbook-schema-standardization.test.mjs:81` through `tests/workbook-schema-standardization.test.mjs:88` still validates boolean-type consistency for `order_summary_sections`, `runtime_rule_exceptions`, `step_order_summary_map`, and model-scoped variant override sheets.

Read-only workbook inventory from `stingray_master.xlsx`:

| Sheet | Current rows | Current active rows | Model coverage | Current classification |
| --- | ---: | ---: | --- | --- |
| `runtime_steps` | 28 | 28 | `stingray`: 14, `grand_sport`: 14, no `z06` rows | Pre-implementation inventory: runtime/generated-useful, incomplete across promoted models; fallback exists. |
| `context_section_master` | 4 | 4 | `stingray`: 2, `grand_sport`: 2, no `z06` rows | Pre-implementation inventory: runtime/generated-useful, incomplete across promoted models; fallback exists. |
| `section_presentation` | 33 | 33 | `stingray`: 12, `grand_sport`: 12, `z06`: 9 | Runtime/generated-useful; keep. |
| `context_choice_copy` | 3 | 3 | shared `*` trim copy for 1LT/2LT/3LT | Runtime/generated-useful for Stingray/Grand Sport trim tooltips; incomplete for LZ trim copy if Z06 needs model-specific text. |
| `order_summary_sections` | 11 | 11 | `stingray` only | Pre-implementation inventory: runtime-partial/redundant; browser uses generated rows for Stingray and JS fallback for Grand Sport/Z06. |
| `step_order_summary_map` | 13 | 13 | `stingray` only | Pre-implementation inventory: runtime-partial/redundant; browser uses generated rows for Stingray and JS fallback for Grand Sport/Z06. |
| `runtime_rule_exceptions` | 4 | 4 | `stingray` only | Runtime/generated-useful; consumed by browser for Stingray exceptions. |
| `variant_option_overrides` | 7 | not generic-active filtered | `stingray` only | Runtime/generated-useful; global sheet uses `active` as a generated choice override value, not row activation. |
| `grandSport_variant_overrides` | 13 | 13 | Grand Sport model-scoped sheet | Runtime/generated-useful; same normalized loader, different sheet contract. |
| `z06_variant_overrides` | 4 | 4 | Z06 model-scoped sheet | Runtime/generated-useful; same normalized loader, different sheet contract. |

Current generated/runtime artifact evidence:

- `form-app/data.js` currently exposes all three promoted models.
- Current live registry data counts:
  - Stingray: `steps=14`, `contextChoices=8`, `runtimeRuleExceptions=4`, `orderSummary.sections=11`, `orderSummary.stepMap=13`.
  - Grand Sport: `steps=14`, `contextChoices=8`, `runtimeRuleExceptions=0`, `orderSummary.sections=0`, `orderSummary.stepMap=0`.
  - Z06: `steps=14`, `contextChoices=8`, `runtimeRuleExceptions=0`, `orderSummary.sections=0`, `orderSummary.stepMap=0`.
- `form-output/inspection/grand-sport-runtime-contract.json` and `form-output/inspection/z06-runtime-contract.json` currently have `orderSummary.sections=0` and `orderSummary.stepMap=0`.
- No workbook formulas or defined names were found referencing the Pass E target sheets during read-only inspection.
- `codex-context.md` was requested by the planning skill but is absent in this checkout.

Risk level: Medium. Completing workbook metadata should be behavior-preserving, but the generated contracts will change if Grand Sport/Z06 begin emitting order-summary metadata, and Z06 step/context rows may change `source` fields from fallback metadata to workbook-authored metadata. Deleting any of these sheets without migration would risk runtime behavior, generated contract shape, or source-of-truth drift.

Change type if approved: mixed workbook/data + generator/tests/docs. Intended browser behavior: no user-visible behavior change.

## Recommended Pass E scope

Recommended smallest safe Pass E: complete and standardize workbook ownership for active promoted models, then leave runtime/Python fallbacks in place as compatibility paths until a later fallback-retirement pass.

Do not delete the Pass E sheets in this pass. Classify and consolidate first.

### In scope

1. Create a current inventory artifact.
   - Add `docs/audit-cleanup/pass-e-runtime-metadata-inventory.md` during implementation.
   - Include row counts, model coverage, generated field coverage, consumer paths, and keep/candidate calls for every Pass E target sheet.

2. Complete workbook-owned step/context metadata for Z06.
   - Add `z06` rows to `runtime_steps` matching the current generated Z06 fallback step order/labels.
   - Add `z06` rows to `context_section_master` matching the current generated Z06 fallback body-style and trim-level context sections.
   - Expected runtime behavior: unchanged. Expected generated-data difference: Z06 metadata becomes workbook-authored rather than fallback-authored; `steps[*].source` may change from `fallback_config` to workbook source notes.

3. Complete workbook-owned order-summary metadata for Grand Sport and Z06.
   - Add `grand_sport` and `z06` rows to `order_summary_sections` equivalent to the current JS fallback `orderSectionDefinitions` in `form-app/app.js:141` through `app.js:153`.
   - Add `grand_sport` and `z06` rows to `step_order_summary_map` equivalent to current JS fallback `stepOrderSectionKeys` in `form-app/app.js:156` through `app.js:170`.
   - Expected runtime behavior: unchanged grouping/labels if workbook rows exactly match fallback constants.
   - Expected generated-data difference: Grand Sport/Z06 runtime contracts and `form-app/data.js` will begin carrying `data.orderSummary` rows instead of relying on JS fallback.

4. Keep `section_presentation` as active workbook-owned runtime metadata.
   - Do not retire it.
   - Verify existing `z06` rows are sufficient for standard-equipment presentation and hidden/display behavior.
   - If missing rows are found, inventory them but do not invent new presentation behavior without explicit source evidence.

5. Keep `context_choice_copy` as active workbook-owned runtime copy.
   - Do not retire it.
   - Classify current shared 1LT/2LT/3LT rows as Stingray/Grand Sport copy.
   - If Z06 needs 1LZ/2LZ/3LZ copy, identify that as a product-copy decision, not a generic cleanup edit.

6. Keep `runtime_rule_exceptions` for now.
   - Do not delete the sheet or rows.
   - Classify each current Stingray exception as either truly exceptional runtime behavior or a candidate for future migration into canonical workbook rules/default/exclusive metadata.
   - Do not fold these rows into normal rule sheets in Pass E unless the implementation proves a no-behavior migration with targeted runtime tests.

7. Classify, but do not rewrite, variant override sheet topology unless no-behavior proof is trivial.
   - Current topology is inconsistent: global `variant_option_overrides` for Stingray, model-scoped `grandSport_variant_overrides`, and model-scoped `z06_variant_overrides` for Grand Sport/Z06.
   - `runtime_metadata.load_variant_option_overrides()` already normalizes both contracts, so this inconsistency is tolerable but should be documented.
   - Recommended Pass E result: inventory the two contracts and decide the target shape for a later pass. Do not merge model-scoped rows into the global sheet in the same pass as order-summary/step completion unless contract comparison proves it has zero generated/runtime behavior impact.

8. Add guards that prevent new active promoted models from silently relying on Python/JS fallbacks.
   - Prefer tests that assert each promoted model has workbook rows for `runtime_steps`, `context_section_master`, `order_summary_sections`, and `step_order_summary_map`.
   - Keep fallbacks for compatibility, but require active promoted models to populate the workbook rows.

### Out of scope

- Deleting any Pass E target sheet.
- Deleting runtime/Python fallback constants from `model_configs.py` or `form-app/app.js`.
- Changing visual layout, CSS, selected-card behavior, disabled-card behavior, tooltip behavior, or mobile behavior.
- Changing customer-facing option choices, prices, rules, interiors, colors, or dealer payload semantics.
- Changing model promotion status or promoting ZR1/ZR1X.
- Refactoring generator architecture beyond the smallest code/test changes needed to validate workbook-owned metadata coverage.
- Migrating Stingray `runtime_rule_exceptions` into canonical rule sheets unless separately approved.
- Merging `variant_option_overrides`, `grandSport_variant_overrides`, and `z06_variant_overrides` into one sheet unless separately approved after inventory.
- Retiring `build_rule_sources.py` or optional Grand Sport audit/report gates; Pass D already classified them.

## Exact files and sheets to change if approved

### Workbook sheets

Likely writes:

- `stingray_master.xlsx`
  - `runtime_steps`: add active `z06` rows only if current generated Z06 fallback values are confirmed.
  - `context_section_master`: add active `z06` rows only if current generated Z06 fallback values are confirmed.
  - `order_summary_sections`: add active `grand_sport` and `z06` rows matching current runtime fallback labels/order.
  - `step_order_summary_map`: add active `grand_sport` and `z06` rows matching current runtime fallback step grouping.

Read-only classification only:

- `section_presentation`
- `context_choice_copy`
- `runtime_rule_exceptions`
- `variant_option_overrides`
- `grandSport_variant_overrides`
- `z06_variant_overrides`

### Scripts / generator code

Possible small test-support or validation changes only:

- `scripts/corvette_form_generator/runtime_metadata.py`
  - Prefer no behavior change. Only touch if a duplicate/missing promoted-model guard belongs in loader tests rather than schema validation.
- `scripts/corvette_form_generator/schema_validation.py`
  - Possible promoted-model metadata coverage validation if this is the cleanest place to fail on missing runtime metadata rows.
- `scripts/workbook_editor_server.py` / `scripts/corvette_form_generator/editor_*`
  - Do not change unless workbook editor payload tests show the editor must surface newly completed runtime metadata rows differently.

### Tests

Likely edits/additions:

- `tests/stingray-generator-stability.test.mjs`
  - Expand existing Phase 6 workbook-owned metadata assertions from Stingray/Grand Sport to all promoted active models, including Z06.
  - Add coverage for order-summary workbook ownership if this remains the best home.
- `tests/grand-sport-contract-preview.test.mjs`
  - Assert Grand Sport runtime contract emits workbook-owned order-summary metadata after rows are added.
- `tests/grand-sport-draft-data.test.mjs`
  - Assert Grand Sport draft/runtime-contract order-summary data matches the current runtime fallback grouping if needed.
- `tests/z06-contract-preview.test.mjs`
  - Assert Z06 no longer relies on step/context fallback and emits workbook-owned order-summary metadata.
- `tests/z06-form-data-draft.test.mjs`
  - Assert Z06 runtime-contract order-summary data matches the current runtime fallback grouping if needed.
- `tests/multi-model-runtime-switching.test.mjs`
  - Assert order summary grouping/labels remain equivalent for Stingray, Grand Sport, and Z06 after generated metadata replaces JS fallback for non-Stingray models.
- `tests/workbook-schema-standardization.test.mjs`
  - Update only if new rows reveal boolean type drift or if a new workbook coverage check belongs here.
- Python metadata tests under `tests/test_*metadata*.py`
  - Add/adjust only if coverage checks are implemented in Python validators.

### Docs/artifacts

- `docs/audit-cleanup/pass-e-runtime-metadata-inventory.md` — new implementation inventory.
- `docs/audit-cleanup-overview.md` — update Pass E status after implementation.
- `README.md` / `AGENTS.md` — update only if implementation changes normal workflow, validation gates, or active metadata descriptions.

Generated artifacts expected if approved:

- `form-output/inspection/grand-sport-contract-preview.json` / `.md`
- `form-output/inspection/grand-sport-form-data-draft.json` / `.md`
- `form-output/inspection/grand-sport-runtime-contract.json`
- `form-output/inspection/z06-contract-preview.json` / `.md`
- `form-output/inspection/z06-form-data-draft.json` / `.md`
- `form-output/inspection/z06-runtime-contract.json`
- `form-output/stingray-form-data.json`
- `form-output/stingray-form-data.csv`
- `form-app/data.js`
- generated `form_*` sheets in `stingray_master.xlsx` if Stingray generation is run after the workbook write.

## Constraints

- Source of truth: workbook rows should own runtime metadata where workbook can represent it.
- Visual preservation: no CSS/layout/UI styling changes.
- Runtime behavior preservation: order-summary labels/grouping, step order, context cards, standard-equipment rendering, and runtime rule exception behavior should remain equivalent unless a separate product decision is approved.
- No hardcoded model/RPO exceptions.
- No new dependencies.
- No broad refactor.
- No generated `form_*` sheet hand edits.
- No manual workbook edits; use a safe-save script or `apply_workbook_ops.py` path that verifies package integrity.
- Stop if Excel lock `~$stingray_master.xlsx` exists.
- Do not hide missing workbook metadata by adding more fallback logic. The direction is to complete workbook rows for promoted models, not to make fallback paths quieter.
- Do not promote ZR1/ZR1X or add runtime metadata rows for inactive future models in this pass.

## Risks

- Generated contract drift is expected for Grand Sport/Z06 order-summary metadata. It must be reviewed as intentional and behavior-equivalent, not ignored.
- Z06 `runtime_steps` rows may change `steps[*].source` from fallback metadata to workbook-authored metadata. That is source/provenance drift, not a UI change, if labels/order match.
- Workbook boolean typing may drift if rows are appended with Python booleans in sheets that currently contain text booleans or vice versa. Schema tests should catch this.
- Duplicating order-summary rows from JS fallback into workbook could freeze fallback labels that should differ by model later. If model-specific labels are desired, require product-copy decisions.
- `variant_option_overrides.active` has two meanings across sheet contracts. A careless generic active-row filter would break Stingray UQT overrides.
- `runtime_rule_exceptions` may represent real gaps in the canonical rule model. Deleting it before a targeted migration would reintroduce Stingray regressions such as GBA/ZYC or Z51 suspension behavior.

## Non-goals

- No sheet retirement in Pass E unless a target sheet is proven completely stale during implementation. Current evidence does not support deleting any Pass E target sheet outright.
- No runtime fallback retirement. Removing fallback constants from Python/JS is a later pass after workbook coverage is complete and proven.
- No variant-override topology migration in the same pass unless the user explicitly expands scope.
- No product-copy rewrite for Z06 trim cards.
- No rule-normalization or pricing cleanup.

## Implementation outline after approval

1. Re-run read-only inventory.
   - Check workbook row counts and headers for all Pass E target sheets.
   - Check promoted active models from `model_master` / `model_registry_promotion`.
   - Confirm no Excel lock file exists before any write path is prepared.

2. Snapshot generated runtime contracts.
   - Copy current `form-app/data.js`, `form-output/stingray-form-data.json`, and Grand Sport/Z06 runtime-contract JSON files to `/tmp` or a local ignored scratch path for comparison.

3. Add tests/guards first.
   - Add a failing guard proving every promoted active model has workbook-owned `runtime_steps` and `context_section_master` rows.
   - Add a failing guard proving every promoted active model has workbook-owned `order_summary_sections` and `step_order_summary_map` rows.
   - Add or update contract/runtime tests to assert Grand Sport/Z06 order-summary grouping remains equivalent to current fallback behavior once emitted.

4. Write workbook rows with safe-save.
   - Add only deterministic rows matching current generated/fallback behavior.
   - Verify the saved workbook on disk with `openpyxl` after save.
   - Refresh table refs if the target sheets have Excel tables.

5. Regenerate affected artifacts.
   - Generate Grand Sport and Z06 runtime contracts first.
   - Generate Stingray last to refresh `form-app/data.js` registry data if promoted runtime contracts changed.

6. Compare generated contracts.
   - For Z06 steps/context, expected difference should be provenance/source only if rows match fallback values.
   - For Grand Sport/Z06 order summary, expected difference should be addition of `orderSummary.sections` and `orderSummary.stepMap` matching JS fallback constants.
   - No choice, price, rule, interior, color, or dealer payload changes should appear unless explicitly explained.

7. Update inventory/overview docs.
   - Record keep/consolidate/defer calls per sheet.
   - Mark Pass E completed only after gates pass.

## Validation plan

Preflight/read-only:

```sh
git status --short --branch
.venv/bin/python - <<'PY'
from openpyxl import load_workbook
wb = load_workbook('stingray_master.xlsx', read_only=True, data_only=False)
for sheet in [
    'runtime_steps', 'context_section_master', 'section_presentation',
    'context_choice_copy', 'order_summary_sections', 'step_order_summary_map',
    'runtime_rule_exceptions', 'variant_option_overrides',
    'grandSport_variant_overrides', 'z06_variant_overrides',
]:
    print(sheet, sheet in wb.sheetnames)
PY
```

After workbook writes:

```sh
.venv/bin/python scripts/validate_workbook_package.py stingray_master.xlsx
.venv/bin/python scripts/validate_workbook_schema.py stingray_master.xlsx
```

Regeneration:

```sh
.venv/bin/python scripts/generate_form.py --model grand_sport
.venv/bin/python scripts/generate_form.py --model z06
.venv/bin/python scripts/generate_form.py --model stingray
```

Contract comparison:

```sh
node scripts/compare-generated-contracts.mjs /tmp/pass-e-before-grand-sport-runtime-contract.json form-output/inspection/grand-sport-runtime-contract.json
node scripts/compare-generated-contracts.mjs /tmp/pass-e-before-z06-runtime-contract.json form-output/inspection/z06-runtime-contract.json
node scripts/compare-generated-contracts.mjs /tmp/pass-e-before-stingray-form-data.json form-output/stingray-form-data.json
```

Expected comparison result:

- Grand Sport/Z06 `orderSummary` additions are intentional and equivalent to current JS fallback constants.
- Z06 `steps`/context provenance may change from fallback to workbook source; labels/order/sections/context choices must remain equivalent.
- No unexpected choices/rules/prices/interiors/colors/dealer payload changes.

Targeted tests:

```sh
node --test tests/stingray-generator-stability.test.mjs
node --test tests/grand-sport-contract-preview.test.mjs
node --test tests/grand-sport-draft-data.test.mjs
node --test tests/z06-contract-preview.test.mjs
node --test tests/z06-form-data-draft.test.mjs
node --test tests/multi-model-runtime-switching.test.mjs
node --test tests/workbook-schema-standardization.test.mjs
```

Python metadata/editor tests if validators or editor metadata are touched:

```sh
.venv/bin/python -m pytest tests/test_model_config_metadata.py tests/test_registry_promotion_metadata.py tests/test_schema_validation_metadata.py tests/test_editor_server_payload.py tests/test_editor_ops_meta.py -q
```

Broader default suite if generated app data changes beyond expected metadata fields:

```sh
.venv/bin/python scripts/validate_workbook_schema.py stingray_master.xlsx
node --test tests/stingray-form-regression.test.mjs
node --test tests/stingray-generator-stability.test.mjs
node --test tests/grand-sport-contract-preview.test.mjs
node --test tests/grand-sport-draft-data.test.mjs
node --test tests/workbook-schema-standardization.test.mjs
node --test tests/workbook-visual-copy-standardization.test.mjs
node --test tests/z06-contract-preview.test.mjs
node --test tests/z06-form-data-draft.test.mjs
node --test tests/z06-runtime-promotion.test.mjs
node --test tests/z06-interior-accessory-cleanup.test.mjs
node --test tests/z06-performance-package-interactions.test.mjs
node --test tests/z06-runtime-rule-corrections.test.mjs
node --test tests/multi-model-runtime-switching.test.mjs
.venv/bin/python -m pytest tests/test_model_config_metadata.py tests/test_registry_promotion_metadata.py tests/test_schema_validation_metadata.py -q
```

Manual/browser verification if approved implementation changes `form-app/data.js`:

- Switch between Stingray, Grand Sport, and Z06.
- Confirm step rail labels/order are unchanged.
- Confirm body/trim setup cards still render and select correctly.
- Build a Grand Sport order and verify summary grouping/labels match current behavior.
- Build a Z06 order and verify summary grouping/labels match current behavior.
- Verify Stingray GBA/ZYC and Z51 suspension runtime-rule exception behavior still works.

## Approval question

Approve Pass E as a no-user-visible-behavior consolidation pass that completes workbook-owned runtime metadata for all promoted models and documents/defer-classifies the remaining runtime metadata sheets?

Recommended approval wording: `Pass E approved.`

If you want a narrower first slice, approve option (a):

- (a) Recommended: complete `runtime_steps`, `context_section_master`, `order_summary_sections`, and `step_order_summary_map` for promoted models; classify but do not migrate variant overrides or runtime exceptions.
- (b) Inventory-only: write the inventory report and make no workbook/code/test changes.
- (c) Broader: include variant override topology migration too. Higher risk; not recommended for the same pass as order-summary/step completion.

## Next step guidance

After Pass E lands cleanly, the next safe pass would be fallback retirement: remove or shrink Python/JS fallback constants only after all promoted runtime metadata is workbook-owned and tests prove generated data carries the needed rows. Do not start that fallback-retirement pass until Pass E comparison shows behavior equivalence.
