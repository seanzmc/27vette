# Pass 3 — Generated Workbook `form_*` Retirement Policy Spec

Status: Spec only. Do not implement until approved.
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
   - After implementation, append implementation results, workbook backup path, gates, generated-diff handling, and residual risks.

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

8. Compare runtime payloads:

```sh
node scripts/compare-generated-contracts.mjs "$BASE/stingray-runtime-contract.json" form-output/runtime/stingray-runtime-contract.json
node scripts/compare-generated-contracts.mjs "$BASE/grand-sport-runtime-contract.json" form-output/runtime/grand-sport-runtime-contract.json
node scripts/compare-generated-contracts.mjs "$BASE/z06-runtime-contract.json" form-output/runtime/z06-runtime-contract.json
node scripts/compare-generated-contracts.mjs "$BASE/stingray-form-data.json" form-output/stingray-form-data.json
```

9. Restore unrelated timestamp-only generated churn unless the generated runtime artifacts are intentionally part of the retained diff.

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

## Residual risks

- Some human workflow may still open `form_*` sheets for ad hoc debugging even though Pass 0 found no code/formula/table dependency. Mitigation: do not create a new debug writer until someone names a real consumer.
- Deleting workbook sheets can change workbook binary structure and sheet order. Mitigation: package validation plus read-only sheet-absence verification.
- Removing default workbook save from Stingray generation changes operational expectation: `generate_form.py --model stingray` should no longer require Excel closed for generated-sheet writes. Real future workbook writes still need the lock guard.
- Existing docs/archive files may still mention historical `form_*` behavior. Active docs should be updated; archive docs should not be rewritten just to erase history.

## Approval prompt

Approve Pass 3 implementation as scoped above?

Recommended answer: approve. It removes the last Stingray-only generated workbook surface from the runtime workflow while preserving JSON runtime contracts, legacy Stingray compatibility artifacts, editor read-only protections, and the separate future decisions for CSV/debug exports and full generator-route unification.
