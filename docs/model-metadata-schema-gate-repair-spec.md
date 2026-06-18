# Model metadata schema gate repair spec

Date: 2026-06-18
Status: Implemented 2026-06-18.

## Goal

Restore `scripts/validate_workbook_schema.py stingray_master.xlsx` as a clean readiness gate by repairing workbook-owned model metadata and adding a clearer guard against the exact metadata drift that currently blocks the validator.

This pass is about metadata integrity only. It should not change product data, active model behavior, generated runtime payloads, or dealer submission behavior.

## Diagnosis

Current blocker:

```sh
.venv/bin/python scripts/validate_workbook_schema.py stingray_master.xlsx
```

Current result: invalid, 3 errors:

- `registry_promotion_inactive_model` for `stingray`.
- `registry_promotion_registry_key_mismatch` for `grand_sport` / `grandSport`.
- `app_registry_freshness_check_failed` caused by the same model metadata state.

Root cause:

- The current `model_master` sheet no longer has the workbook-owned model metadata schema.
- Current `model_master` headers are asset-map-shaped:
  - `model_key, target_type, target_id, image_url, image_alt, image_fit, image_position, active, notes, notes`
- Current `model_master` row content also mirrors asset-map-style rows, not model configuration rows.
- `asset_map` itself still exists separately and contains the real active image map rows. Do not replace or prune `asset_map` in this pass.
- Because `schema_validation.validate_registry_promotion_metadata()` reads `model_master` to validate promoted registry rows, the corrupt `model_master` shape makes promoted models appear inactive/mismatched even though `model_registry_promotion` itself still has the expected promoted rows.

Additional metadata drift found during read-only inventory:

- Compared to `origin/main:stingray_master.xlsx`, current `model_workbook_sources` is missing two inactive future-scaffold rows:
  - `zr1`, `rule_mapping_sheet`, `zr1_rule_mapping`, inactive.
  - `zr1x`, `rule_mapping_sheet`, `zr1x_rule_mapping`, inactive.
- These rows are not the direct schema failure, but they are part of the same workbook-owned source graph and should be restored in the same controlled metadata repair pass if the target sheets exist.

Evidence inspected:

- Current branch/status:
  - branch: `generator-simplification-pass1`
  - `origin/main` is an ancestor of current HEAD.
  - working tree was clean at spec start.
- Current workbook probes:
  - `model_master`: 111 data rows, asset-map-shaped headers/content.
  - `model_registry_promotion`: 5 rows, expected promotion rows for Stingray, Grand Sport, Z06, ZR1, ZR1X.
  - `model_workbook_sources`: 52 data rows; missing the two inactive ZR1/ZR1X rule mapping rows found in `origin/main`.
  - `asset_map`: 111 data rows, expected asset-map headers, includes current branch's additional active image rows.
- `origin/main:stingray_master.xlsx` reference:
  - `model_master` has 5 data rows and canonical headers:
    `model_key, registry_key, model_label, model_year, dataset_name, export_slug, expected_variant_count, default_model, active, notes`
  - Active rows: `stingray`, `grand_sport`, `z06`.
  - Inactive rows: `zr1`, `zr1x`.
  - `grand_sport.registry_key` is `grandSport`, matching current `model_registry_promotion` and existing tests.
- Code consumers:
  - `scripts/corvette_form_generator/runtime_metadata.py:526-568` loads model metadata from `model_master`, `model_workbook_sources`, and `model_variants`.
  - `scripts/corvette_form_generator/runtime_metadata.py:588-657` applies workbook metadata over Python base configs and fails on registry-key/variant/source drift.
  - `scripts/corvette_form_generator/registry_promotion.py:181-253` uses `model_master` to validate/load promoted runtime registry entries.
  - `scripts/corvette_form_generator/schema_validation.py:490-552` uses `model_master` to validate promotion rows, but currently has no explicit `model_master` header guard before that indirect validation.
- Tests already encode the intended model metadata shape:
  - `tests/test_model_config_metadata.py:21-80`
  - `tests/test_registry_promotion_metadata.py:35-78`

Temp-copy proof performed during spec:

- In a temporary copy only, replacing `model_master` with the `origin/main` canonical sheet contents and restoring the two inactive ZR1/ZR1X `model_workbook_sources.rule_mapping_sheet` rows made both gates pass:

```sh
.venv/bin/python scripts/validate_workbook_package.py <temp-current.xlsx>
# valid, 0 issues

.venv/bin/python scripts/validate_workbook_schema.py <temp-current.xlsx>
# valid, 0 errors, 0 warnings
```

Risk level: High for validation/readiness confidence; low for runtime if scoped correctly.

Change type: workbook metadata repair + schema-validator/test guard + docs/status update. Mixed, but no generated runtime contract or runtime JS behavior is intended.

## Controlled pass plan

### Pass 1 — Repair workbook-owned model metadata

Decision owner: workbook metadata sheets.

Exact workbook sheets to change:

1. `stingray_master.xlsx` / `model_master`
   - Replace the current asset-map-shaped sheet content with the canonical model metadata table.
   - Use the `origin/main:stingray_master.xlsx` `model_master` rows as the starting reference because they match current tests and make the validator pass in temp-copy proof.
   - Required headers:
     - `model_key`
     - `registry_key`
     - `model_label`
     - `model_year`
     - `dataset_name`
     - `export_slug`
     - `expected_variant_count`
     - `default_model`
     - `active`
     - `notes`
   - Required rows:
     - `stingray`, `stingray`, `Stingray`, active/default, expected variants `6`.
     - `grand_sport`, `grandSport`, `Grand Sport`, active/non-default, expected variants `6`.
     - `z06`, `z06`, `Z06`, active/non-default, expected variants `6`.
     - `zr1`, `zr1`, `ZR1`, inactive/non-default, expected variants `4`.
     - `zr1x`, `zr1x`, `ZR1X`, inactive/non-default, expected variants `4`.
   - Notes may keep the current `origin/main` text or be rewritten to durable non-phase wording. If notes are rewritten, do not use pass/phase/source-process language that can become stale.

2. `stingray_master.xlsx` / `model_workbook_sources`
   - Restore these inactive source graph rows if absent and if the target sheets exist:
     - `zr1`, `rule_mapping_sheet`, `zr1_rule_mapping`, `active=False`.
     - `zr1x`, `rule_mapping_sheet`, `zr1x_rule_mapping`, `active=False`.
   - Do not activate them.
   - Do not change active Stingray, Grand Sport, or Z06 source rows.

Implementation constraints:

- Use a small idempotent workbook repair script or one-off safe-save writer.
- Save through `save_workbook_safely()`.
- Stop if `~$stingray_master.xlsx` exists.
- Before write, snapshot the current workbook metadata rows so rollback/audit can show exactly what changed.
- Touch only `model_master` and the two missing inactive `model_workbook_sources` rows.
- Do not touch `asset_map`; it is a separate sheet and currently has branch-local image rows beyond `origin/main`.
- Do not touch `model_registry_promotion` unless a post-repair validator still proves it is wrong.
- Do not regenerate runtime artifacts in this pass unless validation proves a metadata repair changed generated contracts unexpectedly.

Pass 1 verification:

```sh
.venv/bin/python scripts/validate_workbook_package.py stingray_master.xlsx
.venv/bin/python - <<'PY'
from openpyxl import load_workbook

wb = load_workbook('stingray_master.xlsx', read_only=True, data_only=True)
expected_headers = [
    'model_key', 'registry_key', 'model_label', 'model_year', 'dataset_name',
    'export_slug', 'expected_variant_count', 'default_model', 'active', 'notes',
]
ws = wb['model_master']
headers = [cell.value for cell in next(ws.iter_rows(max_row=1))]
print(headers)
assert headers == expected_headers, headers
rows = {row[0]: row for row in ws.iter_rows(min_row=2, values_only=True) if row[0]}
print(rows)
for key in ('stingray', 'grand_sport', 'z06', 'zr1', 'zr1x'):
    assert key in rows, key
assert rows['grand_sport'][1] == 'grandSport'
assert rows['stingray'][8] is True
assert rows['grand_sport'][8] is True
assert rows['z06'][8] is True
assert rows['zr1'][8] is False
assert rows['zr1x'][8] is False
PY
```

Expected Pass 1 output:

- Workbook binary change.
- No generated artifacts.
- `model_master` value/type diff should show replacement of the corrupted asset-map-shaped table with the 5 canonical model metadata rows.
- `model_workbook_sources` diff should show only the two inactive rule-mapping rows restored.

### Pass 2 — Add explicit `model_master` schema guard

Decision owner: validator/test code.

Exact files to change:

- `scripts/corvette_form_generator/schema_validation.py`
- `tests/test_schema_validation_metadata.py`

Recommended behavior:

- Add a `MODEL_MASTER_HEADERS` constant matching the canonical header list above.
- In `validate_workbook_schema()`, before promotion validation, assert `model_master` headers match exactly.
- Emit a clear error such as `model_master_header_drift` if headers differ.
- Optional but recommended in the same narrow guard: reject duplicate active `model_master.model_key` rows with `duplicate_active_model_master_row` so registry validation cannot depend on accidental first/last duplicate behavior.

Tests:

- Add a schema-validation unit test where `model_master` is asset-map-shaped and assert `model_master_header_drift` is emitted.
- If adding the duplicate guard, add a unit test with duplicate active `model_master` rows for the same `model_key`.
- Keep existing `registry_promotion_registry_key_mismatch` tests intact; this guard should make the current corruption easier to diagnose, not weaken promotion validation.

Pass 2 validation:

```sh
.venv/bin/python -m pytest tests/test_schema_validation_metadata.py tests/test_registry_promotion_metadata.py tests/test_model_config_metadata.py -q
.venv/bin/python scripts/validate_workbook_schema.py stingray_master.xlsx
```

### Pass 3 — Refresh status docs/spec after the repair lands

Decision owner: docs/status only.

Exact docs to change:

- `docs/model-metadata-schema-gate-repair-spec.md`
- `docs/actual-tasks-remaining-6-17.md` if it mentions the schema gate blocker or next-pass guidance after this repair.
- Any current architecture/risk handoff doc in the working tree that still says the validator is blocked by model metadata drift.

Validation:

```sh
git diff --check -- docs/model-metadata-schema-gate-repair-spec.md docs/actual-tasks-remaining-6-17.md
```

## Non-goals

- No runtime JS changes.
- No generated `form-output/*` or `form-app/data.js` hand edits.
- No model promotion changes.
- No changes to product option rows, rules, prices, OVS rows, interiors, colors, or assets.
- No pruning of branch-local `asset_map` rows.
- No broad schema-standardization pass beyond explicit model metadata integrity.
- No attempt to resolve unrelated future-model data completeness.

## Risks

- Replacing `model_master` from `origin/main` could lose any intentional branch-local model metadata if it existed after divergence. Current inspection shows current `model_master` is asset-map-shaped, not a valid branch-local model metadata table. Still, implementation should snapshot current rows and diff against `origin/main` before writing.
- `model_workbook_sources` missing ZR1/ZR1X rule-mapping rows are inactive and should not affect runtime. Restoring them improves future-model source graph completeness but must not activate them.
- If `validate_workbook_schema.py` still fails after `model_master` repair, stop and report the new exact validator output before expanding scope.

## Validation plan for approved implementation

Preflight:

```sh
git branch --show-current
git status --short --branch
git fetch origin main --quiet
git merge-base --is-ancestor origin/main HEAD; echo $?
python3 - <<'PY'
from pathlib import Path
print('LOCK_PRESENT' if Path('~$stingray_master.xlsx').exists() else 'NO_LOCK_FILE')
PY
.venv/bin/python scripts/validate_workbook_package.py stingray_master.xlsx
```

Focused gates:

```sh
.venv/bin/python scripts/validate_workbook_package.py stingray_master.xlsx
.venv/bin/python scripts/validate_workbook_schema.py stingray_master.xlsx
.venv/bin/python -m pytest tests/test_schema_validation_metadata.py tests/test_registry_promotion_metadata.py tests/test_model_config_metadata.py -q
git diff --check -- stingray_master.xlsx scripts/corvette_form_generator/schema_validation.py tests/test_schema_validation_metadata.py docs/model-metadata-schema-gate-repair-spec.md
```

Optional no-behavior confirmation if implementation wants extra assurance:

```sh
.venv/bin/python scripts/generate_registry.py
# Then inspect git diff and restore generated artifacts if the only change was timestamp/noise and this pass did not intend runtime artifact changes.
```

Do not run model generators by default for this metadata repair unless the schema validator still fails or generated registry behavior needs a focused proof.

## Implementation result

Implemented on 2026-06-18.

- `stingray_master.xlsx` / `model_master` was restored to the canonical workbook-owned model metadata contract.
- `asset_map` was not changed.
- `model_registry_promotion` was not changed.
- The two inactive future `model_workbook_sources` rule-mapping rows were not restored because their target sheets, `zr1_rule_mapping` and `zr1x_rule_mapping`, do not currently exist in this workbook. This keeps the repair within the approved "if target sheets exist" constraint.
- `scripts/corvette_form_generator/schema_validation.py` now reports direct `model_master_header_drift` and `duplicate_active_model_master_row` errors before indirect registry-promotion validation.
- `tests/test_schema_validation_metadata.py` covers asset-map-shaped `model_master` drift and duplicate active model keys.

Validation run:

- `.venv/bin/python scripts/validate_workbook_package.py stingray_master.xlsx`
- `.venv/bin/python scripts/validate_workbook_schema.py stingray_master.xlsx`
- `.venv/bin/python -m pytest tests/test_schema_validation_metadata.py tests/test_registry_promotion_metadata.py tests/test_model_config_metadata.py -q`
- `git diff --check -- stingray_master.xlsx scripts/corvette_form_generator/schema_validation.py tests/test_schema_validation_metadata.py docs/model-metadata-schema-gate-repair-spec.md docs/actual-tasks-remaining-6-17.md`
