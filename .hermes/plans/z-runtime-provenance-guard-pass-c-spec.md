# Z Runtime Provenance Guard Cleanup Pass C Spec

## Diagnosis

Cleanup Pass A and B removed customer-facing Grand Sport contamination from active Z source sheets. The remaining Grand Sport references in the Z workflow are mostly intentional staging/review provenance, but runtime promotion needs a guard so review-only lineage never leaks into live app data if Z06/ZR1/ZR1X artifacts are later promoted.

Evidence inspected:

- Branch/status before this pass: `z06-zr1-migration`; `stingray_master.xlsx` is modified by Pass A/B; no Excel lock file was present during Pass B.
- Runtime registry promotion helper: `scripts/corvette_form_generator/registry_promotion.py`
  - `live_contract_data()` already strips top-level `draftMetadata` and choice-level `source_option_name`, `source_description`, `text_cleanup_notes`.
  - It does not currently strip arbitrary nested future-model review fields like `copy_from_model_key`, `suggested_copy_from`, `raw_source_sheet`, `raw_source_sheets`, `review_status`, or `review_flags` if a future promoted draft artifact contains them outside choices.
- Live generation fallback: `scripts/generate_stingray_form.py`
  - has a duplicate `live_contract_data()` implementation for legacy Grand Sport fallback.
- Schema validator: `scripts/corvette_form_generator/schema_validation.py`
  - already checks live `form-app/data.js` for `draftMetadata` and draft-only choice fields.
  - It does not currently check recursive review/provenance fields or `grand_sport:` lineage tokens.
- Tests: `tests/test_registry_promotion_metadata.py` already covers basic stripping for promoted Grand Sport draft artifacts.

Root cause:

The live-contract sanitizer is too narrow for future-model promotion. It covers known Grand Sport draft fields but not future-model review lineage fields. If Z draft artifacts later include `copy_from_model_key=grand_sport`, `suggested_copy_from=grand_sport:*`, raw source sheet provenance, or review flags, those fields could survive into runtime unless explicitly stripped/validated.

Risk level: low-to-medium. This is generator/helper/test/validator-only and does not write the workbook or generated app data. The main risk is over-stripping fields that runtime still needs, so the forbidden field list must avoid runtime-required fields such as `source_id`, `source_type`, `source_section`, `source_note`, `source_detail_raw`, `source_sheet`, and interior tooltip fields.

Change type: generator/helper/test/validator guard only. No workbook write.

## Exact Files to Change

- `scripts/corvette_form_generator/registry_promotion.py`
  - Add a recursive live-contract scrubber for draft/provenance-only keys.
  - Strip these known review/provenance keys anywhere in promoted artifact data:
    - `draftMetadata`
    - `copy_from_model_key`
    - `suggested_copy_from`
    - `raw_source_sheet`
    - `raw_source_sheets`
    - `review_status`
    - `review_flags`
    - existing draft-only choice fields: `source_option_name`, `source_description`, `text_cleanup_notes`
  - Preserve runtime-needed keys including `source_id`, `source_type`, `source_section`, `source_selection_mode`, `source_note`, `source_detail_raw`, and `source_sheet`.

- `scripts/generate_stingray_form.py`
  - Reuse the shared `live_contract_data()` from `registry_promotion.py` instead of keeping a duplicate narrower sanitizer.

- `scripts/corvette_form_generator/schema_validation.py`
  - Extend live app data validation to recursively fail on forbidden provenance keys and `grand_sport:` lineage token values.
  - Do not fail on legitimate Grand Sport model keys/labels or normal customer-facing text containing “Grand Sport”. Only block explicit lineage tokens such as `grand_sport:`.

- `tests/test_registry_promotion_metadata.py`
  - Add/extend tests proving promoted artifacts strip nested future-model provenance fields and `grand_sport:*` suggested-copy values while preserving runtime-needed source fields.

No workbook sheets or generated artifacts should be edited in this pass.

## Constraints

- No workbook writes.
- No generated `form_*` sheet edits.
- No `form-output/` regeneration unless tests invoke existing scripts as part of gates.
- No `form-app/data.js` hand edit.
- No Z06/ZR1/ZR1X runtime promotion.
- No dealer submission endpoint, payload, or Turnstile changes.
- No new dependencies.
- No broad refactor.
- Preserve live Stingray and Grand Sport behavior.
- Preserve runtime-required source fields used by app/tooltips.

## Non-goals

- Do not clean internal provenance rows in `future_model_source_review` / `future_model_option_review`.
- Do not remove legitimate Grand Sport model data from current live Grand Sport runtime.
- Do not add or complete Z product rules, interiors, pricing, or activation.
- Do not regenerate app data as part of this pass unless a gate explicitly requires it.

## Validation Plan

Run targeted Python tests:

```sh
.venv/bin/python -m pytest tests/test_registry_promotion_metadata.py -q
```

Run schema validator against current workbook/app data:

```sh
.venv/bin/python scripts/validate_workbook_schema.py stingray_master.xlsx
```

Run targeted future-model staging tests to ensure review/provenance workflows still work outside live contract stripping:

```sh
.venv/bin/python -m pytest tests/test_future_model_source_review.py tests/test_future_model_option_review.py tests/test_future_model_source_population.py tests/test_future_model_option_population.py -q
```

Review diff:

```sh
git diff -- scripts/corvette_form_generator/registry_promotion.py scripts/generate_stingray_form.py scripts/corvette_form_generator/schema_validation.py tests/test_registry_promotion_metadata.py
```

## Approval

User approved moving on to Cleanup Pass C. This spec records the exact implementation boundary before edits.
