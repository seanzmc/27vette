# Pass 0 — Promoted Input Baseline and Consumer Inventory

Date: 2026-06-21
Scope: read-only baseline/inventory for `docs/Audit-route-map.md` Pass 0.

## Result

Pass 0 is complete as a baseline report. No workbook rows, generator code, runtime code, generated artifacts, or app registry files were changed.

This pass establishes the current promoted inputs and the consumer surfaces that a later unified runtime-contract-builder pass must preserve or migrate deliberately.

## Constraints followed

- `stingray_master.xlsx` was inspected read-only.
- No `scripts/generate_form.py` generator was run in this pass.
- No `scripts/generate_registry.py` publication was run in this pass.
- No generated `form_*` sheet, `form-output/*` artifact, or `form-app/data.js` file was hand-edited.
- `node scripts/compare-generated-contracts.mjs` was used only as a strict timestamp-ignored equality check between copied baselines and current files.

## Current promoted inputs

Evidence sources:

- `stingray_master.xlsx` sheet `model_registry_promotion`, read-only.
- `scripts/corvette_form_generator/registry_promotion.py`, especially `current_generation_artifact_path()` / `artifact_path_for_promotion()`.

| model_key | registry_key | artifact_type | workbook artifact_path | resolved promoted input | dataset.status | sha256 |
| --- | --- | --- | --- | --- | --- | --- |
| `stingray` | `stingray` | `current_generation` | blank | `form-output/stingray-form-data.json` | blank / absent | `71394feed31cef9cfd9539e7727cc94b623ad19a1b53883de3ab1e75f761be26` |
| `grand_sport` | `grandSport` | `draft_artifact` | `form-output/inspection/grand-sport-runtime-contract.json` | `form-output/inspection/grand-sport-runtime-contract.json` | `runtime_active` | `f5475bc27bb1437f50c275351958e1d9e20a808e0e082b03a732632eee83e1ca` |
| `z06` | `z06` | `draft_artifact` | `form-output/inspection/z06-runtime-contract.json` | `form-output/inspection/z06-runtime-contract.json` | `runtime_active` | `7a9a0bbe4e5fc7f8664d2ae7d571100e65483324070aa21a94cbba370b8ac024` |

Baseline copies were written outside the repo:

```text
/tmp/27vette-pass0-baseline-20260621T032938Z/stingray-form-data.json
/tmp/27vette-pass0-baseline-20260621T032938Z/grand-sport-runtime-contract.json
/tmp/27vette-pass0-baseline-20260621T032938Z/z06-runtime-contract.json
```

Strict comparator sanity checks passed against the current files:

```sh
node scripts/compare-generated-contracts.mjs /tmp/27vette-pass0-baseline-20260621T032938Z/stingray-form-data.json form-output/stingray-form-data.json
node scripts/compare-generated-contracts.mjs /tmp/27vette-pass0-baseline-20260621T032938Z/grand-sport-runtime-contract.json form-output/inspection/grand-sport-runtime-contract.json
node scripts/compare-generated-contracts.mjs /tmp/27vette-pass0-baseline-20260621T032938Z/z06-runtime-contract.json form-output/inspection/z06-runtime-contract.json
```

All three returned `contracts match`.

Important boundary: the comparator strips only `generated_at`, `sourceGeneratedAt`, and `generatedAt`, then deep-compares everything else. Use it for no-behavior-drift builder work. Do not use it as the only validator for approved artifact path or schema-shape migrations.

## Promoted input payload counts

| model_key | variants | steps | sections | choices | standardEquipment | rules | priceRules | interiors | colorOverrides |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `stingray` | 6 | 14 | 51 | 1422 | 467 | 144 | 45 | 130 | 245 |
| `grand_sport` | 6 | 14 | 37 | 1422 | 455 | 122 | 47 | 132 | 245 |
| `z06` | 6 | 14 | 36 | 1428 | 488 | 73 | 68 | 130 | 137 |

`form-app/data.js` currently embeds these registry models:

| registry key | label | exportSlug | dataset.status | choices | rules | priceRules | interiors |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: |
| `stingray` | Stingray | `stingray` | blank / absent | 1422 | 144 | 45 | 130 |
| `grandSport` | Grand Sport | `grand-sport` | `runtime_active` | 1422 | 122 | 47 | 132 |
| `z06` | Z06 | `z06` | `runtime_active` | 1428 | 73 | 68 | 130 |

Registry facts:

- `defaultModelKey` is `stingray`.
- `window.STINGRAY_FORM_DATA` legacy alias is present.

## Generated workbook `form_*` sheets

Read-only workbook inspection found the generated sheet surface still exists and is Stingray-shaped today:

| sheet | data rows | columns |
| --- | ---: | ---: |
| `form_steps` | 14 | 5 |
| `form_context_choices` | 8 | 13 |
| `form_choices` | 1422 | 26 |
| `form_standard_equipment` | 467 | 13 |
| `form_rule_groups` | 26 | 10 |
| `form_exclusive_groups` | 9 | 5 |
| `form_rules` | 144 | 16 |
| `form_price_rules` | 45 | 9 |
| `form_interiors` | 130 | 31 |
| `form_color_overrides` | 245 | 6 |
| `form_validation` | 3 | 5 |

Workbook formula / defined-name / table consumer scan:

- No workbook defined names containing `form_` were found.
- No workbook formulas containing `form_` were found.
- No Excel table objects on the generated `form_*` sheets were found by openpyxl.

## Consumer inventory

### Registry/promotion code consumers

These are the code paths that decide which promoted input is read and embedded:

- `scripts/generate_registry.py`
  - Loads workbook promotions with `load_registry_promotions()`.
  - Builds the registry with `build_registry_from_artifacts()`.
  - Prints resolved artifacts through `artifact_path_for_promotion()`.
  - Writes only `form-app/data.js`.
- `scripts/corvette_form_generator/registry_promotion.py`
  - Owns `model_registry_promotion` loading and validation.
  - Allows `artifact_type=current_generation` without `artifact_path`.
  - Resolves blank current-generation paths to `form-output/<export_slug>-form-data.json`.
  - Requires non-current-generation promoted rows to have `artifact_path`.
  - Validates non-current-generation artifacts with `assert_runtime_contract()` before promotion embedding.
- `scripts/promote_model.py`
  - Writes promotion rows for model promotion.
  - Currently plans `artifact_path=form-output/inspection/<slug>-runtime-contract.json`.
- `scripts/corvette_form_generator/schema_validation.py`
  - Validates promotion sheet headers, default count, artifact types, and artifact path shape.
- `scripts/corvette_form_generator/runtime_metadata.py`
  - Reads active `model_registry_promotion` rows as workbook metadata.

### Promoted artifact path test consumers

- `tests/test_registry_promotion_metadata.py`
  - Asserts current-generation Stingray resolves through `form-output/stingray-form-data.json`.
  - Uses Grand Sport runtime-contract path fixtures under `form-output/inspection/`.
  - Tests non-current promoted rows require `artifact_path`.
- `tests/test_runtime_metadata_guards.py`
  - Uses Z06 `artifact_path=form-output/inspection/z06-runtime-contract.json` in workbook metadata fixtures.
- `tests/test_schema_validation_metadata.py`
  - Tests promotion metadata validation and stale app-registry checks.
- `tests/stingray-generator-stability.test.mjs`
  - Reads `form-output/stingray-form-data.json` directly.
  - Reads workbook `model_registry_promotion` rows.

### Model generator/output consumers

- `scripts/generate_form.py`
  - Routes Stingray to `production.main()`.
  - Routes Grand Sport/Z06 to inspection/preview/draft/runtime-contract artifact writers.
- `scripts/corvette_form_generator/production.py`
  - Writes generated workbook `form_*` sheets.
  - Writes `form-output/stingray-form-data.json` and `.csv`.
- `scripts/corvette_form_generator/inspection.py`
  - Writes Grand Sport/Z06 inspection, preview, draft, and clean runtime-contract artifacts under `form-output/inspection/`.
- `scripts/corvette_form_generator/model_configs.py`
  - Carries the current generated `form_*` sheet list.
- `scripts/corvette_form_generator/workbook.py`
  - Treats generated `form_*` sheets as generated/do-not-hand-edit surfaces.

### Editor/workflow consumers of generated `form_*` sheets

- `tests/test_editor_ops_apply.py`
  - Uses `form_steps` fixtures to verify generated sheets are read-only in editor apply operations.
- `tests/test_editor_server_payload.py`
  - Uses `form_steps` to verify generated sheets appear as read-only/non-family workbook sheets.
- `scripts/corvette_form_generator/editor_ops.py` / editor server payload paths
  - Treat generated sheets as non-editable output surfaces.

### Documentation consumers

Active docs that describe or depend on this split:

- `AGENTS.md`
- `README.md`
- `docs/Audit-route-map.md`
- `docs/ingest/pass-1/schema-and-ingest-process-report.md`
- `docs/audit-cleanup/pass-d-required-gate-split-spec.md`

Historical docs also reference older route shapes. They were not treated as active consumers for migration planning.

### Proposed future runtime artifact path consumers

A scan found `form-output/runtime/` only in `docs/Audit-route-map.md`. There is no current code/test consumer for that future path. A later Pass 2 cannot be a file move only; it must change workbook `model_registry_promotion.artifact_path`, promotion helpers/tests as needed, and registry validation expectations.

## Pass 1 implications

A behavior-preserving unified-builder pass should:

1. Preserve the three promoted inputs listed above unless the pass explicitly scopes a generated artifact change.
2. Use the copied `/tmp/27vette-pass0-baseline-20260621T032938Z/*` files as the before snapshot for strict no-drift comparisons.
3. Re-run generators only in the implementation pass where generated artifacts are expected to be rewritten.
4. Compare the post-generation promoted inputs with `node scripts/compare-generated-contracts.mjs` when no behavior drift is expected.
5. Treat any non-timestamp diff as a blocker unless the implementation spec explicitly approves it.
6. Keep artifact path normalization separate from builder unification. Path normalization needs workbook safe-save/on-disk verification and promotion tests.

## Validation commands run

```sh
git status --short --branch
python3 - <<'PY'
from pathlib import Path
print('excel_lock:', 'present' if Path('~$stingray_master.xlsx').exists() else 'absent')
PY
PYTHONPATH=scripts .venv/bin/python - <<'PY'
# read-only promotion load, artifact resolution, runtime-contract assertion for draft_artifact rows,
# SHA-256 hash collection, and /tmp baseline copy creation
PY
.venv/bin/python - <<'PY'
# read-only generated form_* sheet row/column count inspection
PY
node - <<'NODE'
// load form-app/data.js in a VM and summarize registry contents
NODE
node scripts/compare-generated-contracts.mjs /tmp/27vette-pass0-baseline-20260621T032938Z/stingray-form-data.json form-output/stingray-form-data.json
node scripts/compare-generated-contracts.mjs /tmp/27vette-pass0-baseline-20260621T032938Z/grand-sport-runtime-contract.json form-output/inspection/grand-sport-runtime-contract.json
node scripts/compare-generated-contracts.mjs /tmp/27vette-pass0-baseline-20260621T032938Z/z06-runtime-contract.json form-output/inspection/z06-runtime-contract.json
```

Gate results:

- Excel lock check: absent.
- Runtime contract assertion for Grand Sport/Z06 promoted artifacts: passed.
- Baseline copy strict comparisons against current files: passed for all three promoted inputs.
- Workbook `form_*` row/column inspection: completed read-only.
- `form-app/data.js` registry probe: completed.
- No generator/test suite gates were run because Pass 0 was report-only and intentionally avoided writing generated artifacts.

## Residual risks / pending verification

- Baselines under `/tmp` are not durable repo artifacts. They are suitable for the next local implementation pass, but should be recopied if the work is resumed in a new environment or after artifacts change.
- This pass did not prove generators reproduce the current artifacts. It established current promoted inputs and consumer surfaces. Reproducibility/parity belongs in the Pass 1 implementation gate.
- This pass did not audit every archived document. Historical references were excluded from active-consumer decisions.

## Recommended next pass

Pass 1 should be a narrow, no-behavior-change builder extraction spec. It should target the shared runtime-contract construction boundary first and leave these surfaces unchanged unless explicitly scoped:

- `model_registry_promotion` rows and artifact paths.
- `form-output/stingray-form-data.json` promoted input path.
- `form-output/inspection/*-runtime-contract.json` promoted input paths.
- Generated workbook `form_*` sheet policy.
- `form-app/data.js` publication path through `scripts/generate_registry.py`.
