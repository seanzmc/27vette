# Pass E Runtime Metadata Inventory

Status: Completed with Pass E option (a).

Scope: workbook/runtime metadata sheets only. Audit-only sheets (`option_audit_groups`, `option_audit_group_members`, `rule_review_groups`) remain classified by Pass A and were not touched here.

## Completed metadata coverage

| Sheet | Rows after Pass E | Promoted-model coverage | Current use | Pass E action |
| --- | ---: | --- | --- | --- |
| `runtime_steps` | 42 | `stingray`: 14, `grand_sport`: 14, `z06`: 14 | Generator emits `data.steps`; browser renders runtime steps from generated data. | Added 14 Z06 rows so all promoted models use workbook-owned step metadata. |
| `context_section_master` | 6 | `stingray`: 2, `grand_sport`: 2, `z06`: 2 | Generator emits body-style and trim context sections. | Added 2 Z06 rows so promoted Z06 no longer relies on Python context-section fallback. |
| `order_summary_sections` | 33 | `stingray`: 11, `grand_sport`: 11, `z06`: 11 | Generator emits `orderSummary.sections`; browser uses generated metadata before JS fallback. | Added 11 Grand Sport and 11 Z06 rows. |
| `step_order_summary_map` | 39 | `stingray`: 13, `grand_sport`: 13, `z06`: 13 | Generator emits `orderSummary.stepMap`; browser uses generated mapping before JS fallback. | Added 13 Grand Sport and 13 Z06 rows. |

Generated-contract result after regeneration:

- Stingray: unchanged ignoring timestamps.
- Grand Sport: only new top-level runtime-contract field is `orderSummary` with 11 sections and 13 step-map entries.
- Z06: now emits workbook-owned `runtime_steps` (`source: pass_e_runtime_metadata_consolidation`), workbook-owned context sections, and `orderSummary` with 11 sections and 13 step-map entries.

## Classified but not migrated/deleted

| Sheet | Rows after Pass E | Coverage | Classification | Reason not migrated/deleted in option (a) |
| --- | ---: | --- | --- | --- |
| `section_presentation` | 33 | `stingray`: 12, `grand_sport`: 12, `z06`: 9 | Runtime/generated-useful; keep. | It owns standard-equipment bucket/group display and section presentation overrides. No topology migration requested. |
| `context_choice_copy` | 3 | shared `*` rows for 1LT/2LT/3LT copy | Runtime/generated-useful; keep. | It supplies generated trim-choice copy/tooltips for LT trim families. LZ-specific copy can be considered later, but was out of scope here. |
| `runtime_rule_exceptions` | 4 | `stingray`: 4 | Runtime/generated-useful; keep. | Browser consumes generated exceptions for Stingray-specific runtime default/selection behavior. No Grand Sport/Z06 migration requested. |
| `variant_option_overrides` | 7 | `stingray`: 7 | Runtime/generated-useful; keep. | This global sheet uses `active` as an emitted choice-field override, not as row activation; topology differs from model-scoped sheets. |
| `grandSport_variant_overrides` | 13 | Grand Sport sheet-local rows | Runtime/generated-useful; keep. | Same normalized loader as global overrides, but separate model-scoped sheet topology. No topology consolidation in option (a). |
| `z06_variant_overrides` | 4 | Z06 sheet-local rows | Runtime/generated-useful; keep. | Same normalized loader as global overrides, but separate model-scoped sheet topology. No topology consolidation in option (a). |

## Consumers

- `scripts/corvette_form_generator/runtime_metadata.py`
  - `load_runtime_steps()`
  - `load_context_sections()`
  - `load_section_presentation()`
  - `load_variant_option_overrides()`
  - `load_runtime_rule_exceptions()`
  - `load_order_summary_metadata()`
- `scripts/corvette_form_generator/production.py`
  - Emits Stingray runtime metadata to `form-output/stingray-form-data.json` and `form-app/data.js`.
- `scripts/corvette_form_generator/inspection.py`
  - Now emits `orderSummary` into Grand Sport/Z06 previews, drafts, and runtime-contract artifacts.
- `form-app/app.js`
  - Renders generated `steps`, `sections`, `contextChoices`, `runtimeRuleExceptions`, and generated `orderSummary` when present.
  - JS order-summary fallbacks remain in place for compatibility, but promoted models are now guarded by tests to carry completed workbook metadata.

## Guards added

- `scripts/corvette_form_generator/runtime_metadata.py`
  - Promoted runtime models now raise instead of silently using `runtime_steps` fallback rows.
  - Promoted runtime models now raise instead of silently using `context_section_master` fallback rows.
  - Promoted runtime models now raise instead of silently using browser order-summary fallback metadata when `order_summary_sections` or `step_order_summary_map` rows are missing.
- `tests/stingray-generator-stability.test.mjs`
  - Derives promoted models from `model_registry_promotion`.
  - Requires all promoted models (`stingray`, `grand_sport`, `z06`) to have workbook-owned `runtime_steps`, `context_section_master`, `order_summary_sections`, and `step_order_summary_map` rows.
- `tests/test_runtime_metadata_guards.py`
  - Covers the promoted-model fallback guards while preserving fallback behavior for unpromoted models.
- `tests/grand-sport-contract-preview.test.mjs`
- `tests/grand-sport-draft-data.test.mjs`
- `tests/z06-contract-preview.test.mjs`
- `tests/z06-form-data-draft.test.mjs`
  - Require generated Grand Sport/Z06 artifacts to carry 11 order-summary sections and 13 step-map entries.
  - Z06 tests also guard against silent `fallback_config` step metadata.

## Non-goals preserved

- No deletion of classified runtime metadata sheets.
- No migration of `section_presentation`, `context_choice_copy`, `runtime_rule_exceptions`, or variant override topology.
- No removal of Python/JavaScript fallback constants.
- No change to dealer submission boundaries or deployment paths.
