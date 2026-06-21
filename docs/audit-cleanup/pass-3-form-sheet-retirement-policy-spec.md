# Pass 3 — Generated Workbook `form_*` Retirement Policy Spec

Status: Implemented 2026-06-21.
Date: 2026-06-21
Recommended reasoning level for implementation agent: high.

## Goal

Retire shared generated workbook `form_*` sheets from the normal runtime-generation workflow.

Chosen policy: do not create model-scoped workbook output sheets. The runtime source of generated truth is now the promoted JSON runtime-contract surface:

```text
form-output/runtime/<slug>-runtime-contract.json
```

The existing workbook `form_*` sheets are Stingray-only generated outputs. Keeping them as routine workflow artifacts preserves a false mental model that the workbook contains the live generated contract for one active model but not the others.

## Diagnosis

Pass 0 found the current workbook still contains generated `form_*` sheets:

| sheet | current rows | current headers |
|---|---:|---:|
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

Current evidence:

- `scripts/corvette_form_generator/production.py` writes all `form_*` sheets during `generate_form.py --model stingray`, then saves `stingray_master.xlsx`.
- `scripts/corvette_form_generator/model_configs.py` carries `GENERATED_SHEETS` only for the Stingray production writer.
- `scripts/corvette_form_generator/workbook.py::write_sheet()` styles generated workbook sheets and is only appropriate when a workbook writer is explicitly scoped.
- `tests/test_editor_ops_apply.py` and `tests/test_editor_server_payload.py` use `form_steps` fixtures only to prove generated/unregistered workbook sheets are read-only in editor APIs.
- Pass 0 found no workbook formulas, defined names, or Excel table objects depending on generated `form_*` sheets.
- Pass 2 moved promoted runtime inputs to `form-output/runtime/<slug>-runtime-contract.json`; registry publication no longer needs `form_*` sheets.

Root cause: the original Stingray generator used workbook sheets as generated output/debug surfaces before the multi-model runtime-contract path existed. After Passes 1-2, those sheets are no longer needed in the runtime route and remain asymmetric by model.

Risk level: medium.

Change type: mixed generator/workbook/tests/docs. Runtime behavior should remain unchanged.

## Ownership decision

- Workbook source sheets remain canonical for product data and business rules.
- Generated runtime contracts under `form-output/runtime/` own active generated runtime payloads.
- Existing `form_*` sheets should not be routine runtime artifacts and should not be replaced by model-scoped workbook generated sheets.
- If a future debug/review need exists, add an explicit opt-in debug/report export later. Do not keep routine workbook writes for a hypothetical consumer.

## Exact implementation scope

### Code

1. `scripts/corvette_form_generator/production.py`
   - Remove default `write_sheet()` calls for:
     - `form_steps`
     - `form_context_choices`
     - `form_choices`
     - `form_standard_equipment`
     - `form_rule_groups`
     - `form_exclusive_groups`
     - `form_rules`
     - `form_price_rules`
     - `form_interiors`
     - `form_color_overrides`
     - `form_validation`
   - Stop saving `stingray_master.xlsx` during normal `generate_form.py --model stingray` runs when no workbook source data changes.
   - Remove the normal-generation `workbook_backup_path` dependency created by `save_workbook_safely()`. The generator's stdout JSON must not call `str(workbook_backup_path)` after the save is removed; either remove `workbook_backup` from the normal output or keep it as explicit `null` for compatibility.
   - Keep writing:
     - `form-output/stingray-form-data.json` compatibility artifact.
     - `form-output/stingray-form-data.csv` compatibility artifact, unless a separate CSV retirement pass approves removal.
     - `form-output/runtime/stingray-runtime-contract.json` promoted runtime contract.
   - Preserve generated JSON payload shape and counts.

2. `scripts/corvette_form_generator/model_configs.py`
   - Remove `GENERATED_SHEETS` and `ModelConfig.generated_sheets` wiring if no longer consumed after production cleanup.

3. `scripts/corvette_form_generator/model_config.py`
   - Remove `generated_sheets` from `ModelConfig` only if all consumers are removed in the same pass.

4. `scripts/corvette_form_generator/workbook.py`
   - Generalize or remove the `form_*`-specific comment on `write_sheet()` if the helper remains for other workbook writers.
   - Do not weaken safe-save behavior for real workbook writes.

5. `scripts/generate_form.py`
   - Update help/comment text that says Stingray production writes `form_*` sheets.

### Workbook

6. `stingray_master.xlsx`
   - Delete existing generated `form_*` sheets once the default generator no longer writes them.
   - Use `save_workbook_safely()` for deletion.
   - Refuse to write if Excel lock file exists.
   - Reopen workbook read-only and verify all retired sheet names are absent.

### Tests

7. `tests/stingray-generator-stability.test.mjs`
   - Replace the current “Stingray generator uses the hardened workbook save path” assertion with a test that the default Stingray generator no longer performs a workbook safe-save for generated `form_*` sheets.
   - Keep workbook package validation tests for real workbook integrity.
   - Keep source-sheet/workbook-owned metadata assertions.
   - Preserve generated JSON / app data synchronization assertions.

8. `tests/test_editor_ops_apply.py`
   - Replace `form_steps` fixture use with a generic unregistered/read-only sheet name such as `generated_debug_fixture` or `readonly_generated_fixture`.
   - Continue proving editor apply rejects edits to non-editable sheets.

9. `tests/test_editor_server_payload.py`
   - Replace `form_steps` fixture use with a generic unregistered/read-only sheet fixture.
   - Continue proving editor payload marks unregistered/non-family sheets read-only.

10. Optional source guard
   - Add a focused guard that active code no longer references the retired sheet names except in historical docs/specs and the Pass 3 spec.
   - Exclude archive docs from this guard.

### Docs

11. `AGENTS.md`
   - Remove “Current generated sheets” active list.
   - Keep the durable rule: generated artifacts are outputs; workbook source rows own business behavior; do not hand-edit generated outputs.
   - State that active runtime contracts live under `form-output/runtime/`.

12. `README.md`
   - Remove generated `form_*` workbook sheets from active workbook source surface list.
   - Update Stingray workflow text: generator writes runtime/compatibility artifacts, not workbook form sheets.
   - Keep workbook editor rule: source sheets are editable; generated/runtime outputs are not.

13. `docs/Audit-route-map.md`
   - Mark Pass 3 policy as implemented after implementation lands.
   - Update bottom-line remaining issue from `form_*` policy to the next actual route item, likely workbook-owned model discovery.

14. `docs/ingest/pass-1/schema-and-ingest-process-report.md`
   - Remove stale active references that imply `form_*` sheets are current workflow surfaces.

15. `docs/audit-cleanup/pass-3-form-sheet-retirement-policy-spec.md`
   - After implementation, append implementation results, the sheet-deletion workbook backup path, gates, generated-diff handling, and residual risks. Do not report a normal Stingray generation workbook backup path unless a future approved workbook write actually creates one.

## Constraints

- No runtime behavior change.
- No visual change.
- No dealer endpoint, payload, or Turnstile change.
- No new dependencies.
- No source workbook business-data edits beyond deleting generated output sheets.
- No hand-editing generated JSON, JS, CSV, or workbook `form_*` cells.
- Do not introduce model-scoped workbook output sheets.
- Do not retire `form-output/stingray-form-data.json` or CSV compatibility output in this pass.
- Do not remove `write_sheet()` if another current safe workbook writer still needs it.
- Preserve optional inspection/preview/draft artifacts under `form-output/inspection/`.
- Restore timestamp-only generated artifact churn that is not part of the approved diff.

## Non-goals

- Full generator-route unification between `production.py` and `inspection.py`.
- Workbook-driven model discovery.
- Runtime payload trimming.
- Optional debug/report workbook export design.
- CSV compatibility artifact retirement.
- Fixing known Z06 `required_charges` expected-list drift in `tests/z06-contract-preview.test.mjs` / `tests/stingray-generator-stability.test.mjs`.

## Implementation sequence

1. Preflight:

```sh
git status --short --branch
.venv/bin/python - <<'PY'
from pathlib import Path
print('lock-present' if Path('.').joinpath(chr(126)+'$stingray_master.xlsx').exists() else 'lock-absent')
PY
.venv/bin/python scripts/validate_workbook_package.py stingray_master.xlsx
```

2. Snapshot before artifacts:

```sh
BASE=/tmp/27vette-pass3-form-sheet-retirement-$(date -u +%Y%m%dT%H%M%SZ)
mkdir -p "$BASE"
cp form-output/runtime/stingray-runtime-contract.json "$BASE/stingray-runtime-contract.json"
cp form-output/runtime/grand-sport-runtime-contract.json "$BASE/grand-sport-runtime-contract.json"
cp form-output/runtime/z06-runtime-contract.json "$BASE/z06-runtime-contract.json"
cp form-output/stingray-form-data.json "$BASE/stingray-form-data.json"
```

3. Remove default workbook `form_*` writer behavior from Stingray generation.

4. Add/update tests for no routine workbook generated-sheet write and editor read-only behavior.

5. Delete existing `form_*` workbook sheets through a small safe-save script or helper using `save_workbook_safely()`.

6. Reopen workbook and verify the retired sheet list is absent.

7. Regenerate active runtime artifacts:

```sh
.venv/bin/python scripts/generate_form.py --model stingray
.venv/bin/python scripts/generate_form.py --model grand_sport
.venv/bin/python scripts/generate_form.py --model z06
.venv/bin/python scripts/generate_registry.py
```

8. Reopen the workbook after regeneration and verify the retired sheet list is still absent:

```sh
.venv/bin/python - <<'PY'
from openpyxl import load_workbook

retired = {
    'form_steps',
    'form_context_choices',
    'form_choices',
    'form_standard_equipment',
    'form_rule_groups',
    'form_exclusive_groups',
    'form_rules',
    'form_price_rules',
    'form_interiors',
    'form_color_overrides',
    'form_validation',
}
wb = load_workbook('stingray_master.xlsx', read_only=True, data_only=False)
present = sorted(retired.intersection(wb.sheetnames))
wb.close()
if present:
    raise SystemExit(f'retired generated workbook sheets reappeared: {present}')
print('retired generated workbook sheets absent after regeneration')
PY
```

9. Compare runtime payloads:

```sh
node scripts/compare-generated-contracts.mjs "$BASE/stingray-runtime-contract.json" form-output/runtime/stingray-runtime-contract.json
node scripts/compare-generated-contracts.mjs "$BASE/grand-sport-runtime-contract.json" form-output/runtime/grand-sport-runtime-contract.json
node scripts/compare-generated-contracts.mjs "$BASE/z06-runtime-contract.json" form-output/runtime/z06-runtime-contract.json
node scripts/compare-generated-contracts.mjs "$BASE/stingray-form-data.json" form-output/stingray-form-data.json
```

10. Restore unrelated timestamp-only generated churn unless the generated runtime artifacts are intentionally part of the retained diff.

## Validation plan

Focused Python/tests:

```sh
.venv/bin/python -m py_compile \
  scripts/generate_form.py \
  scripts/corvette_form_generator/production.py \
  scripts/corvette_form_generator/model_config.py \
  scripts/corvette_form_generator/model_configs.py \
  scripts/corvette_form_generator/workbook.py

.venv/bin/python -m pytest \
  tests/test_editor_ops_apply.py \
  tests/test_editor_server_payload.py \
  tests/test_model_config_metadata.py \
  tests/test_runtime_contract_builder.py \
  tests/test_registry_promotion_metadata.py \
  tests/test_schema_validation_metadata.py \
  tests/test_runtime_metadata_guards.py \
  -q
```

Workbook/schema:

```sh
.venv/bin/python scripts/validate_workbook_package.py stingray_master.xlsx
.venv/bin/python scripts/validate_workbook_schema.py stingray_master.xlsx
```

Runtime/generator:

```sh
.venv/bin/python scripts/generate_form.py --model stingray
node --test tests/stingray-form-regression.test.mjs
node --test tests/grand-sport-contract-preview.test.mjs
node --test tests/grand-sport-draft-data.test.mjs
node --test tests/z06-form-data-draft.test.mjs
node --test tests/multi-model-runtime-switching.test.mjs
```

Targeted `tests/stingray-generator-stability.test.mjs` coverage for changed assertions:

```sh
node --test --test-name-pattern "workbook|generated JSON|Stingray generated contract" tests/stingray-generator-stability.test.mjs
```

Known expected red unless separately fixed:

```sh
node --test tests/z06-contract-preview.test.mjs
node --test tests/stingray-generator-stability.test.mjs
```

If full-file runs still fail only on the pre-existing Z06 `required_charges` expected-list drift, report as unrelated and do not fix in Pass 3.

Docs/checks:

```sh
git diff --check
rg -n "form_steps|form_context_choices|form_choices|form_standard_equipment|form_rule_groups|form_exclusive_groups|form_rules|form_price_rules|form_interiors|form_color_overrides|form_validation|generated form_\* workbook sheets|writes workbook form sheets" AGENTS.md README.md docs scripts tests
```

The grep should return only historical/spec references, tests intentionally covering read-only generic sheets, or the Pass 3 implementation-results section.

## Rollback plan

- Restore `stingray_master.xlsx` from the safe-save backup created during sheet deletion.
- Revert code/test/docs changes.
- Regenerate active models and registry.
- Compare restored runtime contracts against pre-pass snapshots.

## Implementation results — 2026-06-21

### Changed surfaces

- `scripts/corvette_form_generator/production.py`
  - Removed routine workbook `form_*` sheet writes from normal Stingray generation.
  - Removed the normal-generation `save_workbook_safely()` call and `workbook_backup_path` dependency.
  - Kept Stingray JSON, CSV, and runtime-contract artifact writes.
  - Emits `"workbook_backup": null` in stdout JSON for compatibility; normal generation no longer creates a workbook backup.
- `scripts/corvette_form_generator/model_config.py` and `scripts/corvette_form_generator/model_configs.py`
  - Removed `ModelConfig.generated_sheets` and `GENERATED_SHEETS` wiring after all active consumers were removed.
- `scripts/corvette_form_generator/workbook.py`
  - Kept `write_sheet()` available for explicit future workbook export/debug callers, but removed the stale routine `form_*` wording.
- `scripts/generate_form.py`
  - Updated Stingray usage text to describe JSON/CSV/runtime-contract artifact generation, not workbook generated-sheet output.
- `tests/test_editor_ops_apply.py` and `tests/test_editor_server_payload.py`
  - Replaced `form_steps` fixtures with a generic `readonly_generated_fixture` while preserving read-only editor coverage for unregistered/generated/debug sheets.
- `tests/stingray-generator-stability.test.mjs`
  - Replaced the old hardened workbook-save assertion with a guard that Stingray generation no longer calls `save_workbook_safely()`, `write_sheet()`, or `workbook_backup_path` during routine generation.
- `AGENTS.md`, `README.md`, `docs/Audit-route-map.md`, and `docs/ingest/pass-1/schema-and-ingest-process-report.md`
  - Updated active workflow docs to describe `form-output/runtime/` as the generated runtime-contract surface and retired workbook `form_*` sheets from the routine workflow.

### Workbook change

- Deleted existing generated workbook sheets from `stingray_master.xlsx` through `save_workbook_safely()`:
  - `form_steps`
  - `form_context_choices`
  - `form_choices`
  - `form_standard_equipment`
  - `form_rule_groups`
  - `form_exclusive_groups`
  - `form_rules`
  - `form_price_rules`
  - `form_interiors`
  - `form_color_overrides`
  - `form_validation`
- Safe-save backup: `backups/stingray_master-20260621-135747.xlsx`.
- Read-only pre-delete probe found no formulas or defined names outside retired sheets referencing retired sheet names.
- Read-only post-delete and post-regeneration probes verified all retired sheet names are absent on disk.

### Regeneration and generated-diff handling

- Ran:
  - `.venv/bin/python scripts/generate_form.py --model stingray`
  - `.venv/bin/python scripts/generate_form.py --model grand_sport`
  - `.venv/bin/python scripts/generate_form.py --model z06`
  - `.venv/bin/python scripts/generate_registry.py`
- Stingray generator smoke output included `"workbook_backup": null`, `choices: 1422`, `context_choices: 8`, `standard_equipment: 467`, `rules: 144`, `price_rules: 45`, `interiors: 130`, and `validation_errors: 0`.
- Compared pre/post generated contracts with `node scripts/compare-generated-contracts.mjs`; all matched after timestamp normalization:
  - `form-output/runtime/stingray-runtime-contract.json`
  - `form-output/runtime/grand-sport-runtime-contract.json`
  - `form-output/runtime/z06-runtime-contract.json`
  - `form-output/stingray-form-data.json`
- Restored timestamp-only generated artifact churn in `form-output/*` and `form-app/data.js`; retained diff is source/docs/tests plus workbook sheet deletion.

### Validation results

- Preflight:
  - `git status --short --branch` on `schema-ingestion-normalization`.
  - Excel lock probe: lock absent.
  - `.venv/bin/python scripts/validate_workbook_package.py stingray_master.xlsx` — valid, 0 issues.
- Python:
  - `.venv/bin/python -m py_compile scripts/generate_form.py scripts/corvette_form_generator/production.py scripts/corvette_form_generator/model_config.py scripts/corvette_form_generator/model_configs.py scripts/corvette_form_generator/workbook.py` — pass.
  - `.venv/bin/python -m pytest tests/test_editor_ops_apply.py tests/test_editor_server_payload.py tests/test_model_config_metadata.py tests/test_runtime_contract_builder.py tests/test_registry_promotion_metadata.py tests/test_schema_validation_metadata.py tests/test_runtime_metadata_guards.py -q` — 95 passed.
- Workbook/schema:
  - `.venv/bin/python scripts/validate_workbook_package.py stingray_master.xlsx` — valid, 0 issues.
  - `.venv/bin/python scripts/validate_workbook_schema.py stingray_master.xlsx` — valid, 0 errors, 0 warnings.
- Runtime/generator:
  - `node --test --test-name-pattern "routine workbook|generated JSON|Stingray generated contract" tests/stingray-generator-stability.test.mjs` — 3 passed.
  - `node --test tests/stingray-form-regression.test.mjs` — 86 passed.
  - `node --test tests/workbook-schema-standardization.test.mjs` — 9 passed.
  - `node --test tests/grand-sport-contract-preview.test.mjs` — 6 passed.
  - `node --test tests/grand-sport-draft-data.test.mjs` — 19 passed.
  - `node --test tests/z06-form-data-draft.test.mjs` — 23 passed.
  - `node --test tests/multi-model-runtime-switching.test.mjs` — 44 passed.
- Docs/checks:
  - `git diff --check` — pass.
  - Active `scripts/` and `tests/` search shows no retired sheet names or `GENERATED_SHEETS` consumers; only `workbook.py::write_sheet()` remains as an explicit helper.

### Known red not fixed in this pass

- A broader `tests/stingray-generator-stability.test.mjs` run with the spec's original `workbook|generated JSON|Stingray generated contract` pattern still hits the pre-existing Z06 `required_charges` expected-list drift in the Phase 6 workbook-owned metadata assertion. This is the known non-goal called out above and was not fixed in Pass 3.

## Residual risks

- Some human workflow may still open `form_*` sheets for ad hoc debugging even though Pass 0 found no code/formula/table dependency. Mitigation: do not create a new debug writer until someone names a real consumer.
- Deleting workbook sheets can change workbook binary structure and sheet order. Mitigation: package validation plus read-only sheet-absence verification.
- Removing default workbook save from Stingray generation changes operational expectation: `generate_form.py --model stingray` should no longer require Excel closed for generated-sheet writes. Real future workbook writes still need the lock guard.
- Existing docs/archive files may still mention historical `form_*` behavior. Active docs should be updated; archive docs should not be rewritten just to erase history.

## Historical Approval Prompt

Approve Pass 3 implementation as scoped above?

Recommended answer: approve. It removes the last Stingray-only generated workbook surface from the runtime workflow while preserving JSON runtime contracts, legacy Stingray compatibility artifacts, editor read-only protections, and the separate future decisions for CSV/debug exports and full generator-route unification.
