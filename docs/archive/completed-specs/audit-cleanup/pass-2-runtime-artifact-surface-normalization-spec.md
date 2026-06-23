# Pass 2 — Runtime Artifact Surface Normalization Spec

Status: Approved by user instruction to move on after Pass 1 validation; implementation in this pass.
Date: 2026-06-21

## Goal

Normalize promoted runtime artifact surfaces so every active model publishes and registry-promotion consumes the same clean runtime contract path shape:

```text
form-output/runtime/<slug>-runtime-contract.json
```

Keep generated workbook `form_*` retirement as a separate scoped workflow decision. This pass may continue writing Stingray `form_*` sheets and legacy Stingray JSON/CSV compatibility artifacts while moving the promoted registry input to the neutral runtime artifact path.

## Diagnosis

Current route state after Pass 1:

- `scripts/corvette_form_generator/runtime_contract.py` provides shared `build_model_runtime_contract(config, data)`.
- `scripts/corvette_form_generator/production.py` uses that builder for Stingray runtime JSON finalization but still writes promoted input to `form-output/stingray-form-data.json`.
- `scripts/generate_form.py` writes Grand Sport/Z06 clean runtime contracts under `form-output/inspection/`.
- `stingray_master.xlsx` sheet `model_registry_promotion` currently promotes:
  - `stingray`: `artifact_type=current_generation`, blank `artifact_path`, resolved by code to `form-output/stingray-form-data.json`.
  - `grand_sport`: `artifact_type=draft_artifact`, `artifact_path=form-output/inspection/grand-sport-runtime-contract.json`.
  - `z06`: `artifact_type=draft_artifact`, `artifact_path=form-output/inspection/z06-runtime-contract.json`.

Root cause: promoted runtime artifacts are still named by historical generation route (`current_generation` fallback or `inspection` path) rather than by clean runtime contract purpose. Registry promotion is workbook-owned, so normalizing the surface requires both generator artifact writes and `model_registry_promotion` metadata migration.

Change type: mixed generator + workbook metadata + generated artifact + tests/docs. No runtime JS behavior change intended.

Risk level: medium-high because workbook promotion metadata and app registry inputs change. Payload content should stay timestamp-ignored equivalent; artifact paths intentionally change.

## Artifact/type policy

Normalize active promoted rows to:

| model_key | artifact_type | artifact_path |
| --- | --- | --- |
| `stingray` | `runtime_contract` | `form-output/runtime/stingray-runtime-contract.json` |
| `grand_sport` | `runtime_contract` | `form-output/runtime/grand-sport-runtime-contract.json` |
| `z06` | `runtime_contract` | `form-output/runtime/z06-runtime-contract.json` |

Keep legacy resolver support for `current_generation` and `draft_artifact` so older fixtures or unpromoted flows do not break. Treat `runtime_contract` as the normalized active value going forward.

## Exact files/sheets/artifacts to change

Code/tests:

1. `scripts/corvette_form_generator/production.py`
   - Continue writing `form-output/stingray-form-data.json` and `.csv` for compatibility.
   - Also write `form-output/runtime/stingray-runtime-contract.json` from the same `runtime_data` object.
   - Do not touch `form_*` sheet generation.

2. `scripts/generate_form.py`
   - Change Grand Sport/Z06 clean runtime-contract output directory from `form-output/inspection/` to `form-output/runtime/`.
   - Keep inspection, preview, and draft artifacts under `form-output/inspection/`.

3. `scripts/corvette_form_generator/registry_promotion.py`
   - Add `runtime_contract` to valid artifact types.
   - Require `artifact_path` for `runtime_contract` rows.
   - Assert clean runtime contract for all non-legacy current-generation artifact rows and for `runtime_contract` rows.
   - Preserve blank `current_generation` fallback resolution for compatibility.

4. `scripts/corvette_form_generator/schema_validation.py`
   - Allow `runtime_contract` in promotion metadata validation.
   - Require promoted `runtime_contract` rows to have artifact paths.

5. `scripts/promote_model.py`
   - Future promotions should plan `form-output/runtime/<slug>-runtime-contract.json` and `artifact_type=runtime_contract`.

6. Tests:
   - Update `tests/test_registry_promotion_metadata.py` path/type fixtures for normalized runtime contracts.
   - Update `tests/test_schema_validation_metadata.py` and `tests/test_runtime_metadata_guards.py` fixtures where they describe promoted runtime contract rows.
   - Add/adjust an assertion that normalized runtime artifact paths are accepted and embedded.

Workbook source metadata:

7. `stingray_master.xlsx` sheet `model_registry_promotion`
   - Update only active promoted rows for `stingray`, `grand_sport`, `z06` using the table above.
   - Preserve registry keys, default model, legacy alias, active flags, display order, and unpromoted ZR1/ZR1X rows.

Generated artifacts:

8. Add/write:
   - `form-output/runtime/stingray-runtime-contract.json`
   - `form-output/runtime/grand-sport-runtime-contract.json`
   - `form-output/runtime/z06-runtime-contract.json`

9. Regenerate:
   - `form-output/stingray-form-data.json` may get timestamp-only compatibility churn.
   - Grand Sport/Z06 inspection/preview/draft artifacts may get timestamp-only validation churn.
   - `form-app/data.js` should be regenerated from the normalized runtime artifact paths.

Docs:

10. Update this spec with implementation results.
11. Update Pass 1 spec status to record the previously blocked Stingray generator parity gate completion.
12. Update `docs/Audit-route-map.md` Pass 2 status only if implementation lands.

## Constraints

- No `form_*` retirement in this pass.
- No hand-editing generated `form_*` sheets.
- No runtime JS behavior change.
- No dealer submission endpoint, payload shape, or Turnstile change.
- No new dependencies.
- No product/RPO/model-specific business logic.
- Workbook remains source of truth for promotion metadata.
- Use `save_workbook_safely()` and refuse Excel lock files for the workbook write.
- Verify `model_registry_promotion` rows from disk after saving.
- Review generated diffs; expected non-timestamp diff is new artifact path metadata/reporting only, not runtime payload content.

## Risks and mitigations

1. Registry stale risk
   - Mitigation: run all model generators, then `scripts/generate_registry.py`, then schema freshness validation.

2. Runtime payload drift risk
   - Mitigation: snapshot old promoted inputs to `/tmp`, generate normalized artifacts, compare old-vs-new contracts with `scripts/compare-generated-contracts.mjs` for each model.

3. Workbook save risk
   - Mitigation: check Excel lock first, save through `save_workbook_safely()`, reopen workbook read-only and print verified rows.

4. Legacy compatibility risk
   - Mitigation: keep `current_generation` and `draft_artifact` support in promotion helpers/tests; only active workbook rows move to `runtime_contract`.

5. `form_*` scope creep risk
   - Mitigation: leave all `form_*` writer behavior unchanged and state Pass 3 remains separate.

## Non-goals

- No full Stingray source-row route switch to inspection/draft builder.
- No deletion or retirement of generated workbook `form_*` sheets.
- No generated sheet policy decision.
- No model discovery refactor.
- No optional audit/report artifact cleanup.
- No browser smoke unless runtime JS changes unexpectedly.

## Validation plan

Preflight:

```sh
git status --short --branch
python3 - <<'PY'
from pathlib import Path
print('excel_lock:', 'present' if Path('~$stingray_master.xlsx').exists() else 'absent')
PY
```

Implementation checks:

```sh
.venv/bin/python -m py_compile \
  scripts/generate_form.py \
  scripts/promote_model.py \
  scripts/corvette_form_generator/production.py \
  scripts/corvette_form_generator/registry_promotion.py \
  scripts/corvette_form_generator/schema_validation.py

.venv/bin/python -m pytest \
  tests/test_runtime_contract_builder.py \
  tests/test_registry_promotion_metadata.py \
  tests/test_schema_validation_metadata.py \
  tests/test_runtime_metadata_guards.py \
  -q
```

Generation/parity:

```sh
BASE=/tmp/27vette-pass2-before
mkdir -p "$BASE"
cp form-output/stingray-form-data.json "$BASE/stingray-form-data.json"
cp form-output/inspection/grand-sport-runtime-contract.json "$BASE/grand-sport-runtime-contract.json"
cp form-output/inspection/z06-runtime-contract.json "$BASE/z06-runtime-contract.json"

.venv/bin/python scripts/generate_form.py --model stingray
.venv/bin/python scripts/generate_form.py --model grand_sport
.venv/bin/python scripts/generate_form.py --model z06
.venv/bin/python scripts/generate_registry.py

node scripts/compare-generated-contracts.mjs "$BASE/stingray-form-data.json" form-output/runtime/stingray-runtime-contract.json
node scripts/compare-generated-contracts.mjs "$BASE/grand-sport-runtime-contract.json" form-output/runtime/grand-sport-runtime-contract.json
node scripts/compare-generated-contracts.mjs "$BASE/z06-runtime-contract.json" form-output/runtime/z06-runtime-contract.json
```

Targeted runtime/model gates:

```sh
.venv/bin/python scripts/validate_workbook_schema.py stingray_master.xlsx
node --test tests/grand-sport-contract-preview.test.mjs
node --test tests/grand-sport-draft-data.test.mjs
node --test tests/z06-contract-preview.test.mjs
node --test tests/z06-form-data-draft.test.mjs
node --test tests/multi-model-runtime-switching.test.mjs
```

Known unrelated gate state:

- `node --test tests/stingray-generator-stability.test.mjs` currently fails on a pre-existing Z06 `order_summary_sections` expected-list mismatch (`required_charges` row). This pass will not hide or “fix” that unrelated expectation unless it becomes directly blocking for artifact path normalization.

## Approval basis

User requested: “Finish the blocked pass 1 validation then move on to the next route normalization pass: artifact surface normalization toward `form-output/runtime/<slug>-runtime-contract.json`, still keeping `form_*` retirement as a separate scoped workflow decision.”

## Implementation results

Implemented files and workbook surfaces:

- Added normalized runtime-contract writes:
  - `form-output/runtime/stingray-runtime-contract.json`
  - `form-output/runtime/grand-sport-runtime-contract.json`
  - `form-output/runtime/z06-runtime-contract.json`
- Removed obsolete inspection-path runtime-contract artifacts:
  - `form-output/inspection/grand-sport-runtime-contract.json`
  - `form-output/inspection/z06-runtime-contract.json`
- Updated `scripts/corvette_form_generator/production.py` so Stingray still writes legacy JSON/CSV and `form_*` sheets, and also writes the normalized runtime contract.
- Updated `scripts/generate_form.py` so Grand Sport/Z06 clean runtime contracts write to `form-output/runtime/`; inspection/preview/draft artifacts remain under `form-output/inspection/`.
- Updated `scripts/corvette_form_generator/registry_promotion.py` and `scripts/corvette_form_generator/schema_validation.py` to accept `artifact_type=runtime_contract` while preserving legacy `current_generation` / `draft_artifact` support.
- Updated `scripts/promote_model.py` so future promotion plans use `form-output/runtime/<slug>-runtime-contract.json` and `artifact_type=runtime_contract`.
- Updated promotion/schema/runtime-metadata tests for normalized runtime artifact metadata.
- Updated `stingray_master.xlsx` sheet `model_registry_promotion` active promoted rows:
  - `stingray`: `artifact_type=runtime_contract`, `artifact_path=form-output/runtime/stingray-runtime-contract.json`.
  - `grand_sport`: `artifact_type=runtime_contract`, `artifact_path=form-output/runtime/grand-sport-runtime-contract.json`.
  - `z06`: `artifact_type=runtime_contract`, `artifact_path=form-output/runtime/z06-runtime-contract.json`.
- Updated active docs: `README.md`, `docs/Audit-route-map.md`, and this spec.

Workbook save evidence:

- Excel lock check: absent.
- Workbook saved through `save_workbook_safely()`.
- Backup created: `/Users/seandm/Projects/27vette/backups/stingray_master-20260621-021537.xlsx`.
- Reopened workbook read-only and verified `model_registry_promotion` rows on disk after save.

Generated artifact handling:

- Kept new normalized runtime contracts under `form-output/runtime/`.
- Restored timestamp-only churn in legacy/generated compatibility outputs:
  - `form-app/data.js`
  - `form-output/stingray-form-data.json`
  - Grand Sport/Z06 inspection, preview, and draft artifacts under `form-output/inspection/`.
- `form_*` workbook sheets were still written by the Stingray generator during validation, but their workflow policy was not changed.

Gate results:

```text
.venv/bin/python -m py_compile scripts/generate_form.py scripts/promote_model.py scripts/corvette_form_generator/production.py scripts/corvette_form_generator/registry_promotion.py scripts/corvette_form_generator/schema_validation.py tests/test_runtime_contract_builder.py tests/test_registry_promotion_metadata.py tests/test_schema_validation_metadata.py tests/test_runtime_metadata_guards.py
PASS

.venv/bin/python -m pytest tests/test_runtime_contract_builder.py tests/test_registry_promotion_metadata.py tests/test_schema_validation_metadata.py tests/test_runtime_metadata_guards.py -q
PASS: 33 passed

.venv/bin/python scripts/generate_form.py --model stingray
.venv/bin/python scripts/generate_form.py --model grand_sport
.venv/bin/python scripts/generate_form.py --model z06
.venv/bin/python scripts/generate_registry.py
PASS

node scripts/compare-generated-contracts.mjs /tmp/27vette-pass2-before-20260621T061552Z/stingray-form-data.json form-output/runtime/stingray-runtime-contract.json
PASS: contracts match

node scripts/compare-generated-contracts.mjs /tmp/27vette-pass2-before-20260621T061552Z/grand-sport-runtime-contract.json form-output/runtime/grand-sport-runtime-contract.json
PASS: contracts match

node scripts/compare-generated-contracts.mjs /tmp/27vette-pass2-before-20260621T061552Z/z06-runtime-contract.json form-output/runtime/z06-runtime-contract.json
PASS: contracts match

.venv/bin/python scripts/validate_workbook_schema.py stingray_master.xlsx
PASS: valid, issue_count=0

node --test tests/grand-sport-contract-preview.test.mjs
PASS: 6 passed

node --test tests/grand-sport-draft-data.test.mjs
PASS: 19 passed

node --test tests/z06-form-data-draft.test.mjs
PASS: 23 passed

node --test tests/multi-model-runtime-switching.test.mjs
PASS: 44 passed

node --test tests/z06-contract-preview.test.mjs
FAIL: pre-existing expected section count mismatch, 12 actual vs 11 expected, due required_charges row.
```

Residual risk:

- `tests/z06-contract-preview.test.mjs` and `tests/stingray-generator-stability.test.mjs` still carry pre-existing expected-list drift around the Z06 `required_charges` order-summary/section metadata. This pass did not hide that failure.
- Browser smoke was not run because runtime JS was not changed and `multi-model-runtime-switching.test.mjs` covered registry/runtime behavior.
- Generated workbook `form_*` retirement remains a separate Pass 3 decision.
