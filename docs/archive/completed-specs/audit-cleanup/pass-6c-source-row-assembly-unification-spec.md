# Pass 6C — Source-Row Assembly Route Unification Spec

Status: Implemented 2026-06-21.
Date: 2026-06-21
Recommended reasoning level for implementation agent: high.

## Goal

Remove the remaining active-model source-row assembly fork while preserving current runtime and compatibility artifacts.

Current public workflow is already mostly unified:

```text
scripts/generate_form.py --model <active_model>
  -> model_generation.generate_model_artifacts(config)
  -> form-output/runtime/<slug>-runtime-contract.json
  -> scripts/generate_registry.py
  -> form-app/data.js
```

At spec time, the remaining internal split was:

```text
stingray    -> production.py source assembly
grand_sport -> inspection.py build_contract_preview() + build_form_data_draft()
z06         -> inspection.py build_contract_preview() + build_form_data_draft()
```

Pass 6C was scoped to make all active models use one source-row assembly route and remove the temporary route-engine classifier in `model_generation.py` without changing customer-facing behavior.

## Implementation summary

Implemented on 2026-06-21.

Actual changed files:

- `scripts/corvette_form_generator/model_generation.py`
  - Removed the temporary production-vs-review route classifier.
  - Normalized stdout `route_engine` to `source_assembly` for Stingray, Grand Sport, and Z06.
  - Centralized artifact writing around one assembled source payload per model.
- `scripts/corvette_form_generator/source_assembly.py`
  - Added the shared source-assembly facade used by every active model.
  - Finalizes all active model source payloads through `build_model_runtime_contract()`.
- `scripts/corvette_form_generator/production.py`
  - Split Stingray source assembly from Stingray compatibility artifact writing.
  - Preserved legacy `form-output/stingray-form-data.json` / `.csv` payloads.
- `tests/test_generate_form_model_discovery_cli.py`
  - Updated stdout expectations to one normalized `source_assembly` route value.
- `tests/test_model_generation_route.py`
  - Replaced temporary-route assertions with guards that require the shared source assembly path and reject the retired route symbols.
- `tests/test_source_assembly_characterization.py`
  - Added focused direct-assembler characterization for Stingray and Grand Sport drift surfaces.
- `tests/test_runtime_contract_builder.py`
  - Updated source-usage guard for the new source assembly facade.
- `docs/Audit-route-map.md`
  - Refreshed the route map to show Pass 6C implemented.
- `docs/audit-cleanup/pass-6c-source-row-assembly-unification-spec.md`
  - Closed this spec with evidence.

Generated artifacts:

- Regenerated runtime contracts, Stingray compatibility JSON/CSV, registry data, and explicit review artifacts during validation.
- Retained generated diff: none. Timestamp-only/generated validation churn was restored before handoff.
- Pass 6B default-output policy remained intact; default generation did not recreate the bulky inspection/preview/draft artifacts.

Parity evidence:

- Runtime contracts matched the `/tmp/27vette-pass6c-before/runtime/` baselines with `scripts/compare-generated-contracts.mjs` for Stingray, Grand Sport, and Z06.
- Stingray compatibility JSON matched `/tmp/27vette-pass6c-before/compat/stingray-form-data.json` with `scripts/compare-generated-contracts.mjs`.
- Stingray compatibility CSV matched byte-for-byte with `cmp`; SHA-256 remained `1168abba23572a3bbfe9e86d62c2c43e421c47a7da8a54cc08a8e8426f464364`.
- Before/after generation stdout matched for all active models except the intentionally allowlisted `route_engine` change to `source_assembly`; counts, artifact maps, compatibility keys, validation errors, notes, and registry stdout stayed stable.
- Explicit Grand Sport/Z06 review-mode inspection, preview, and draft JSON artifacts matched the `/tmp/27vette-pass6c-before/review-*` baselines with timestamp-ignored comparison.

Gates run:

- `.venv/bin/python -m py_compile scripts/generate_form.py scripts/corvette_form_generator/model_generation.py scripts/corvette_form_generator/source_assembly.py scripts/corvette_form_generator/production.py scripts/corvette_form_generator/inspection.py`
- `.venv/bin/python scripts/validate_workbook_schema.py stingray_master.xlsx` — 0 issues.
- `node --test tests/stingray-form-regression.test.mjs` — 86 passing tests.
- `node --test tests/stingray-generator-stability.test.mjs` — passing.
- `node --test tests/grand-sport-contract-preview.test.mjs` — passing.
- `node --test tests/grand-sport-draft-data.test.mjs` — passing.
- `node --test tests/workbook-schema-standardization.test.mjs` — passing.
- `node --test tests/workbook-visual-copy-standardization.test.mjs` — 8 passing tests.
- `node --test tests/z06-contract-preview.test.mjs` — 3 passing tests.
- `node --test tests/z06-form-data-draft.test.mjs` — 23 passing tests.
- `node --test tests/z06-runtime-promotion.test.mjs` — 5 passing tests.
- `node --test tests/z06-interior-accessory-cleanup.test.mjs` — 7 passing tests.
- `node --test tests/z06-performance-package-interactions.test.mjs` — 17 passing tests.
- `node --test tests/z06-runtime-rule-corrections.test.mjs` — 14 passing tests.
- `node --test tests/multi-model-runtime-switching.test.mjs` — 44 passing tests.
- `.venv/bin/python -m pytest tests/test_generate_form_model_discovery_cli.py tests/test_model_generation_route.py tests/test_source_assembly_characterization.py tests/test_runtime_contract_builder.py tests/test_model_config_metadata.py tests/test_registry_promotion_metadata.py tests/test_schema_validation_metadata.py -q` — 59 passing tests.
- Optional audit/report checks:
  - `node --test tests/grand-sport-rule-audit.test.mjs` — 10 passing tests.
  - `node --test tests/audit-parser-metadata-loaders.test.mjs` — 3 passing tests.
- Final generated parity and stale artifact absence checks passed after the full suite.

Residual risks:

- Pass 6C intentionally preserved current payload semantics. It did not remove the browser GBA/ZYC product exception, decide the cross-model `requires_z25` runtime-schema question, retire Stingray compatibility JSON/CSV, or change Grand Sport/Z06 review artifact shapes.
- The source-assembly facade is now the single orchestration entrypoint, but the underlying compatibility/review payload shapes are still preserved for parity. Further consolidation should be scoped only when runtime payload drift is explicitly allowed or separately proven safe.

Recommended next pass:

- Pass 7 should begin business-rule hardcode cleanup only after this parity point. First likely target: remove the browser runtime GBA/ZYC hardcode if workbook `runtime_rule_exceptions` fully covers the behavior and focused runtime tests prove parity.

## Current preflight evidence

Branch/status at spec time:

```text
## schema-ingestion-normalization...origin/main
working tree clean
recent commits:
748696c feat: update Pass 6B inspection artifact emission spec to implemented status and document changes
b44b358 feat: add optional inspection artifact generation for models
cc8cd41 feat: add Pass 6B inspection artifact emission spec for controlled output management
```

Excel lock check:

```text
excel_lock False
```

Current file evidence:

- `scripts/generate_form.py` delegates all active models to `generate_model_artifacts(base_config, options=options)`.
- `scripts/corvette_form_generator/model_generation.py` still carries:
  - `TEMPORARY_ROUTE_ENGINES = {"stingray": "production"}`
  - `DEFAULT_ROUTE_ENGINE = "inspection_draft"`
  - `_generate_production(config)` for Stingray.
  - `_generate_inspection_draft(config, options)` for Grand Sport/Z06.
- `scripts/corvette_form_generator/production.py` still has `generate_production_artifacts()` and an explicit guard: `production generation currently supports only stingray`.
- `scripts/corvette_form_generator/inspection.py` still owns `build_contract_preview()` and `build_form_data_draft()`.
- `tests/test_generate_form_model_discovery_cli.py` still expects `route_engine == "production"` for Stingray and `"inspection_draft"` for Grand Sport/Z06.
- `tests/test_model_generation_route.py` still asserts `TEMPORARY_ROUTE_ENGINES` and `inspection_draft` exist.

Read-only direct-switch experiment:

```sh
PYTHONPATH=scripts .venv/bin/python - <<'PY'
import json
from pathlib import Path
from corvette_form_generator.model_configs import discover_generation_model_configs
from corvette_form_generator.inspection import build_contract_preview, build_form_data_draft
from corvette_form_generator.runtime_contract import build_model_runtime_contract
config = discover_generation_model_configs()['stingray']
preview = build_contract_preview(config)
draft = build_form_data_draft(config, preview=preview)
runtime = build_model_runtime_contract(config, draft)
Path('/tmp/27vette-pass6c-stingray-inspection-runtime-discovered.json').write_text(json.dumps(runtime, indent=2), encoding='utf-8')
current = json.loads(Path('form-output/runtime/stingray-runtime-contract.json').read_text())
print(json.dumps({
  'inspection_runtime': {k: len(runtime.get(k, [])) for k in ['variants','sections','contextChoices','choices','standardEquipment','rules','priceRules','interiors','colorOverrides']},
  'current_runtime': {k: len(current.get(k, [])) for k in ['variants','sections','contextChoices','choices','standardEquipment','rules','priceRules','interiors','colorOverrides']},
}, indent=2))
PY
node scripts/compare-generated-contracts.mjs form-output/runtime/stingray-runtime-contract.json /tmp/27vette-pass6c-stingray-inspection-runtime-discovered.json
```

Observed result:

```json
{
  "inspection_runtime": {
    "variants": 6,
    "sections": 32,
    "contextChoices": 8,
    "choices": 1422,
    "standardEquipment": 467,
    "rules": 113,
    "priceRules": 45,
    "interiors": 130,
    "colorOverrides": 237
  },
  "current_runtime": {
    "variants": 6,
    "sections": 51,
    "contextChoices": 8,
    "choices": 1422,
    "standardEquipment": 467,
    "rules": 144,
    "priceRules": 45,
    "interiors": 130,
    "colorOverrides": 245
  }
}
```

`compare-generated-contracts.mjs` failed. First visible diffs included extra empty `display_behavior` fields in inspection-derived Stingray choices, UQT active/selectable differences, fewer sections, fewer rules, and fewer color overrides.

Conclusion: Pass 6C must not simply route Stingray through the current `inspection.py` builder and call that no-drift. The unified route must be parity-built from the current production and inspection behaviors, with explicit contract comparisons before any route classifier is removed.

## Diagnosis

Risk level: high.

Change type: generator-only + tests + docs/spec closure. No workbook source-data edits. No runtime JS/CSS edits. No dealer submission edits.

Root cause:

Passes 1, 2, 3, 4, 5, 6A, and 6B normalized final runtime contracts, promotion paths, active model discovery, default output policy, and CLI orchestration. They intentionally did not unify source-row assembly. The remaining fork persists because Stingray production assembly and Grand Sport/Z06 inspection/draft assembly encode materially different source-row selection and normalization choices.

Key drift surfaces that must be reconciled in code, not hidden:

- Section emission: current Stingray runtime has 51 sections; inspection-derived Stingray has 32.
- Rule emission: current Stingray runtime has 144 rules; inspection-derived Stingray has 113.
- Color overrides: current Stingray runtime has 245; inspection-derived Stingray has 237.
- Choice payload shape: inspection-derived Stingray emits explicit empty `display_behavior` keys where current runtime omits them.
- Status/display behavior handling: UQT showed active/selectable differences in the direct-switch diff.
- Output surface: Stingray compatibility JSON/CSV must stay unchanged, while Grand Sport/Z06 inspection preview/draft artifacts remain opt-in from Pass 6B.

## Scope

### In scope

- Create one shared active-model source assembly implementation used by all active models.
- Remove `TEMPORARY_ROUTE_ENGINES` and `DEFAULT_ROUTE_ENGINE` from `model_generation.py`.
- Remove or rewrite the production-vs-inspection route branch in `generate_model_artifacts()`.
- Normalize the `route_engine` stdout value across active models while preserving the existing `route_engine` key for compatibility. Proposed value: `source_assembly`.
- Preserve Stingray compatibility outputs:
  - `form-output/stingray-form-data.json`
  - `form-output/stingray-form-data.csv`
- Preserve all active runtime contracts except ignored timestamp fields:
  - `form-output/runtime/stingray-runtime-contract.json`
  - `form-output/runtime/grand-sport-runtime-contract.json`
  - `form-output/runtime/z06-runtime-contract.json`
- Preserve Grand Sport/Z06 explicit review-mode JSON/Markdown semantics under `--emit-inspection --inspection-output <dir>`.
- Preserve Pass 6B default-output policy: default Grand Sport/Z06 generation must not recreate routine inspection/preview/draft files under `form-output/inspection/`.
- Update tests that currently assert the temporary route split.
- Update this spec and `docs/Audit-route-map.md` after implementation.

### Out of scope

- No workbook edits.
- No generated workbook `form_*` restoration.
- No registry promotion metadata changes.
- No Stingray JSON/CSV retirement.
- No browser runtime behavior changes.
- No dealer endpoint, payload, Turnstile, or submission behavior changes.
- No product-rule cleanup:
  - no GBA/ZYC runtime-hardcode removal;
  - no `runtime_action=replace` classification pass;
  - no `body_style_scope` classification pass;
  - no Stingray exclusive-group ID/style cleanup;
  - no Z06 option-ID suffix/no-RPO cleanup;
  - no copy allowlist decisions.
- No new dependencies.

## Exact files to change

Implementation files:

1. `scripts/corvette_form_generator/model_generation.py`
   - Remove `TEMPORARY_ROUTE_ENGINES` and `DEFAULT_ROUTE_ENGINE`.
   - Replace `_generate_production()` / `_generate_inspection_draft()` route branching with one source-assembly generation path.
   - Keep `GenerationOptions` from Pass 6B for explicit review output.
   - Keep `REQUIRED_RESULT_KEYS`, including `route_engine`, unless a separately approved stdout-contract break is chosen.
   - Set `route_engine` to a single normalized value for all active models, proposed `source_assembly`.
   - Keep Grand Sport/Z06 optional inspection maps empty by default and populated only under `--emit-inspection`.

2. `scripts/corvette_form_generator/source_assembly.py`
   - New module for the shared source-row assembly implementation.
   - It should read workbook source sheets and return a model-neutral assembled payload suitable for `build_model_runtime_contract(config, data)`.
   - It must cover current production and inspection/draft behavior without model/RPO-specific product exceptions.
   - It may expose review metadata needed by inspection preview/draft artifacts, but live runtime data must stay clean through `build_model_runtime_contract()`.
   - It must preserve current per-model output by construction and by parity gates, not by suppressing failures after the fact.
   - It must have focused characterization coverage that calls the shared assembler directly before the slower end-to-end gates become the first failure signal.

3. `scripts/corvette_form_generator/production.py`
   - Retain only the Stingray compatibility writer surface if needed for JSON/CSV output.
   - Stop owning a separate source-row assembly engine.
   - Remove the `production generation currently supports only stingray` source-assembly guard if the code path no longer performs source assembly. A Stingray-only compatibility writer guard is acceptable if it only protects compatibility JSON/CSV.
   - Preserve `form-output/stingray-form-data.json` and `.csv` paths and payloads.

4. `scripts/corvette_form_generator/inspection.py`
   - Make `build_contract_preview()` and `build_form_data_draft()` consume or wrap the shared source assembly instead of owning a separate active-model assembly engine.
   - Preserve current explicit review artifact shapes for Grand Sport/Z06, except ignored timestamp fields.
   - Do not make default generation write routine inspection files.

5. `scripts/generate_form.py`
   - Update only if the shared generation call signature or help text needs a wording change.
   - Keep `--emit-inspection` and `--inspection-output` behavior from Pass 6B.

Tests:

6. `tests/test_generate_form_model_discovery_cli.py`
   - Update active model cases to expect one normalized `route_engine` value for Stingray, Grand Sport, and Z06.
   - Keep stdout key assertions.
   - Keep inactive scaffold rejection.
   - Keep Pass 6B default no-inspection and explicit review-mode assertions.

7. `tests/test_model_generation_route.py`
   - Replace source-string assertions that require `TEMPORARY_ROUTE_ENGINES` / `inspection_draft` with guards that reject those temporary symbols.
   - Assert `generate_form.py` still delegates to `model_generation.generate_model_artifacts()`.
   - Assert the shared source assembly module exists and is imported/used by the generator path.

8. `tests/test_source_assembly_characterization.py`
   - New focused Python characterization test for the shared assembler.
   - Call the shared assembler directly for Stingray and at least one current inspection-route model, preferably Grand Sport unless Z06 exposes a more relevant edge during implementation.
   - Check the known drift surfaces before runtime finalization:
     - section count and section IDs match the current route for each tested model;
     - rule count and rule IDs match;
     - color override count matches;
     - empty `display_behavior` values are omitted from runtime choices;
     - UQT selectable/active/display behavior matches current Stingray behavior;
     - interior `requires_z25` handling remains compatible with current runtime output.
   - This test is not a replacement for generated artifact parity; it is the early, local signal for the specific drift seen in preflight.

9. `tests/test_runtime_contract_builder.py`
   - Extend only if needed to prove the shared assembler still feeds the existing runtime finalization seam without changing final contract cleanup.

10. Existing model/runtime tests that must remain green without changing expected behavior:
   - `tests/stingray-form-regression.test.mjs`
   - `tests/stingray-generator-stability.test.mjs`
   - `tests/grand-sport-contract-preview.test.mjs`
   - `tests/grand-sport-draft-data.test.mjs`
   - `tests/z06-contract-preview.test.mjs`
   - `tests/z06-form-data-draft.test.mjs`
   - `tests/z06-interior-accessory-cleanup.test.mjs`
   - `tests/z06-performance-package-interactions.test.mjs`
   - `tests/z06-runtime-rule-corrections.test.mjs`
   - `tests/multi-model-runtime-switching.test.mjs`

Docs/spec:

11. `docs/audit-cleanup/pass-6c-source-row-assembly-unification-spec.md`
    - Update status, actual changed files, artifacts, gates, residual risks, and next pass before final handoff.

12. `docs/Audit-route-map.md`
    - Mark Pass 6C implemented after validation.
    - Remove or rewrite stale claims that source assembly is still split.
    - Keep Pass 7 as business-rule cleanup, not part of Pass 6C.

Do not edit generated artifacts by hand. Generated runtime/compatibility files may be regenerated for validation, but any retained generated diff must be intentional and explained. Since this pass is no-behavior-change, expected retained generated diff is none, except the already-approved deletion state from Pass 6B.

## Implementation constraints

- Source of truth remains `stingray_master.xlsx` and its source/metadata sheets.
- Do not solve data drift by adding hidden model/RPO-specific Python branches.
- If an existing workbook row/sheet owns a relationship, use that row/sheet rather than inventing a parallel taxonomy.
- Preserve visual/runtime/dealer behavior.
- Preserve default model and active registry models.
- Preserve Pass 6B review-output policy.
- Keep changes small enough to review; if direct extraction requires broad product-rule cleanup, stop and split the pass.
- If parity cannot be achieved without changing runtime contracts, stop and report the exact drift instead of normalizing it silently.

## Required preflight before implementation

Run these before editing code:

```sh
git status --short --branch
test ! -e './~$stingray_master.xlsx'
.venv/bin/python scripts/validate_workbook_schema.py stingray_master.xlsx
rg -n "LEGACY_MODEL_SOURCES|HEADER_PAIRS" scripts/corvette_form_generator/schema_validation.py && exit 1 || true
rg -n "TEMPORARY_ROUTE_ENGINES|inspection_draft|production generation currently supports only stingray" scripts tests docs/Audit-route-map.md docs/audit-cleanup
```

Create fresh current-route baselines from the current checked-in route, not stale artifacts:

```sh
rm -rf /tmp/27vette-pass6c-before
mkdir -p /tmp/27vette-pass6c-before/runtime /tmp/27vette-pass6c-before/compat /tmp/27vette-pass6c-before/review-grand-sport /tmp/27vette-pass6c-before/review-z06

.venv/bin/python scripts/generate_form.py --model stingray > /tmp/27vette-pass6c-before/stingray-stdout.json
.venv/bin/python scripts/generate_form.py --model grand_sport > /tmp/27vette-pass6c-before/grand-sport-stdout.json
.venv/bin/python scripts/generate_form.py --model z06 > /tmp/27vette-pass6c-before/z06-stdout.json
.venv/bin/python scripts/generate_registry.py > /tmp/27vette-pass6c-before/registry-stdout.json

cp form-output/runtime/stingray-runtime-contract.json /tmp/27vette-pass6c-before/runtime/
cp form-output/runtime/grand-sport-runtime-contract.json /tmp/27vette-pass6c-before/runtime/
cp form-output/runtime/z06-runtime-contract.json /tmp/27vette-pass6c-before/runtime/
cp form-output/stingray-form-data.json /tmp/27vette-pass6c-before/compat/
cp form-output/stingray-form-data.csv /tmp/27vette-pass6c-before/compat/

.venv/bin/python scripts/generate_form.py --model grand_sport --emit-inspection --inspection-output /tmp/27vette-pass6c-before/review-grand-sport > /tmp/27vette-pass6c-before/grand-sport-review-stdout.json
.venv/bin/python scripts/generate_form.py --model z06 --emit-inspection --inspection-output /tmp/27vette-pass6c-before/review-z06 > /tmp/27vette-pass6c-before/z06-review-stdout.json

git status --short -- form-output form-app/data.js stingray_master.xlsx
```

If current-route generation creates unexplained non-timestamp drift before any implementation, stop and classify it before coding.

## Validation plan after implementation

Focused Python/code checks:

```sh
.venv/bin/python -m py_compile \
  scripts/generate_form.py \
  scripts/corvette_form_generator/model_generation.py \
  scripts/corvette_form_generator/source_assembly.py \
  scripts/corvette_form_generator/production.py \
  scripts/corvette_form_generator/inspection.py

.venv/bin/python -m pytest \
  tests/test_generate_form_model_discovery_cli.py \
  tests/test_model_generation_route.py \
  tests/test_source_assembly_characterization.py \
  tests/test_runtime_contract_builder.py \
  -q
```

Regenerate active models and registry:

```sh
.venv/bin/python scripts/generate_form.py --model stingray > /tmp/27vette-pass6c-after-stingray-stdout.json
.venv/bin/python scripts/generate_form.py --model grand_sport > /tmp/27vette-pass6c-after-grand-sport-stdout.json
.venv/bin/python scripts/generate_form.py --model z06 > /tmp/27vette-pass6c-after-z06-stdout.json
.venv/bin/python scripts/generate_registry.py > /tmp/27vette-pass6c-after-registry-stdout.json
```

Stdout contract parity, with only the intentional `route_engine` value change allowlisted:

```sh
.venv/bin/python - <<'PY'
import json
from pathlib import Path

before_dir = Path('/tmp/27vette-pass6c-before')
after_files = {
    'stingray': Path('/tmp/27vette-pass6c-after-stingray-stdout.json'),
    'grand_sport': Path('/tmp/27vette-pass6c-after-grand-sport-stdout.json'),
    'z06': Path('/tmp/27vette-pass6c-after-z06-stdout.json'),
}
before_files = {
    'stingray': before_dir / 'stingray-stdout.json',
    'grand_sport': before_dir / 'grand-sport-stdout.json',
    'z06': before_dir / 'z06-stdout.json',
}
expected_before_routes = {
    'stingray': 'production',
    'grand_sport': 'inspection_draft',
    'z06': 'inspection_draft',
}
expected_after_route = 'source_assembly'
must_match_keys = [
    'model_key',
    'model_label',
    'runtime_contract_json',
    'runtime_contract_artifacts',
    'compatibility_artifacts',
    'inspection_artifacts',
    'preview_artifacts',
    'draft_artifacts',
    'counts',
    'validation_errors',
    'notes',
]

for model_key in ('stingray', 'grand_sport', 'z06'):
    before = json.loads(before_files[model_key].read_text())
    after = json.loads(after_files[model_key].read_text())
    assert set(before) == set(after), (model_key, sorted(set(before) ^ set(after)))
    assert before['route_engine'] == expected_before_routes[model_key], before['route_engine']
    assert after['route_engine'] == expected_after_route, after['route_engine']
    for key in must_match_keys:
        assert before[key] == after[key], (model_key, key, before[key], after[key])
    assert after['validation_errors'] == 0, model_key
    if model_key == 'stingray':
        assert set(after['compatibility_artifacts']) == {'json', 'csv'}, after['compatibility_artifacts']
    else:
        assert after['compatibility_artifacts'] == {}, after['compatibility_artifacts']
    assert after['inspection_artifacts'] == {}, after['inspection_artifacts']
    assert after['preview_artifacts'] == {}, after['preview_artifacts']
    assert after['draft_artifacts'] == {}, after['draft_artifacts']

registry_before = json.loads((before_dir / 'registry-stdout.json').read_text())
registry_after = json.loads(Path('/tmp/27vette-pass6c-after-registry-stdout.json').read_text())
assert registry_before == registry_after, (registry_before, registry_after)
assert registry_after['status'] == 'registry_generated'
assert registry_after['default_model'] == 'stingray'
assert registry_after['models'] == ['stingray', 'grandSport', 'z06']
assert set(registry_after['artifacts']) == {'stingray', 'grandSport', 'z06'}
PY
```

Runtime and compatibility parity:

```sh
node scripts/compare-generated-contracts.mjs /tmp/27vette-pass6c-before/runtime/stingray-runtime-contract.json form-output/runtime/stingray-runtime-contract.json
node scripts/compare-generated-contracts.mjs /tmp/27vette-pass6c-before/runtime/grand-sport-runtime-contract.json form-output/runtime/grand-sport-runtime-contract.json
node scripts/compare-generated-contracts.mjs /tmp/27vette-pass6c-before/runtime/z06-runtime-contract.json form-output/runtime/z06-runtime-contract.json
node scripts/compare-generated-contracts.mjs /tmp/27vette-pass6c-before/compat/stingray-form-data.json form-output/stingray-form-data.json
cmp -s /tmp/27vette-pass6c-before/compat/stingray-form-data.csv form-output/stingray-form-data.csv
shasum -a 256 form-output/stingray-form-data.csv
```

Pass 6B absence check must still pass:

```sh
for path in \
  form-output/inspection/grand-sport-inspection.json \
  form-output/inspection/grand-sport-inspection.md \
  form-output/inspection/grand-sport-contract-preview.json \
  form-output/inspection/grand-sport-contract-preview.md \
  form-output/inspection/grand-sport-form-data-draft.json \
  form-output/inspection/grand-sport-form-data-draft.md \
  form-output/inspection/z06-inspection.json \
  form-output/inspection/z06-inspection.md \
  form-output/inspection/z06-contract-preview.json \
  form-output/inspection/z06-contract-preview.md \
  form-output/inspection/z06-form-data-draft.json \
  form-output/inspection/z06-form-data-draft.md
 do
  test ! -e "$path" || { echo "default generation recreated stale inspection artifact: $path"; exit 1; }
 done
```

Explicit review-mode parity:

```sh
rm -rf /tmp/27vette-pass6c-after-review-grand-sport /tmp/27vette-pass6c-after-review-z06
.venv/bin/python scripts/generate_form.py --model grand_sport --emit-inspection --inspection-output /tmp/27vette-pass6c-after-review-grand-sport > /tmp/27vette-pass6c-after-grand-sport-review-stdout.json
.venv/bin/python scripts/generate_form.py --model z06 --emit-inspection --inspection-output /tmp/27vette-pass6c-after-review-z06 > /tmp/27vette-pass6c-after-z06-review-stdout.json

node scripts/compare-generated-contracts.mjs /tmp/27vette-pass6c-before/review-grand-sport/grand-sport-inspection.json /tmp/27vette-pass6c-after-review-grand-sport/grand-sport-inspection.json
node scripts/compare-generated-contracts.mjs /tmp/27vette-pass6c-before/review-grand-sport/grand-sport-contract-preview.json /tmp/27vette-pass6c-after-review-grand-sport/grand-sport-contract-preview.json
node scripts/compare-generated-contracts.mjs /tmp/27vette-pass6c-before/review-grand-sport/grand-sport-form-data-draft.json /tmp/27vette-pass6c-after-review-grand-sport/grand-sport-form-data-draft.json
node scripts/compare-generated-contracts.mjs /tmp/27vette-pass6c-before/review-z06/z06-inspection.json /tmp/27vette-pass6c-after-review-z06/z06-inspection.json
node scripts/compare-generated-contracts.mjs /tmp/27vette-pass6c-before/review-z06/z06-contract-preview.json /tmp/27vette-pass6c-after-review-z06/z06-contract-preview.json
node scripts/compare-generated-contracts.mjs /tmp/27vette-pass6c-before/review-z06/z06-form-data-draft.json /tmp/27vette-pass6c-after-review-z06/z06-form-data-draft.json
```

Full affected model/runtime gates, sequential because tests can regenerate shared artifacts:

```sh
.venv/bin/python scripts/validate_workbook_schema.py stingray_master.xlsx
for t in \
  tests/stingray-form-regression.test.mjs \
  tests/stingray-generator-stability.test.mjs \
  tests/grand-sport-contract-preview.test.mjs \
  tests/grand-sport-draft-data.test.mjs \
  tests/workbook-schema-standardization.test.mjs \
  tests/workbook-visual-copy-standardization.test.mjs \
  tests/z06-contract-preview.test.mjs \
  tests/z06-form-data-draft.test.mjs \
  tests/z06-runtime-promotion.test.mjs \
  tests/z06-interior-accessory-cleanup.test.mjs \
  tests/z06-performance-package-interactions.test.mjs \
  tests/z06-runtime-rule-corrections.test.mjs \
  tests/multi-model-runtime-switching.test.mjs
 do
  node --test "$t"
done
.venv/bin/python -m pytest \
  tests/test_generate_form_model_discovery_cli.py \
  tests/test_model_generation_route.py \
  tests/test_source_assembly_characterization.py \
  tests/test_runtime_contract_builder.py \
  tests/test_model_config_metadata.py \
  tests/test_registry_promotion_metadata.py \
  tests/test_schema_validation_metadata.py \
  -q
```

Optional audit path, because `grand-sport-rule-audit.test.mjs` depends on generated draft data and should not regress if shared assembly changes:

```sh
node --test tests/grand-sport-rule-audit.test.mjs
node --test tests/audit-parser-metadata-loaders.test.mjs
```

Final review:

```sh
git diff --check
git status --short
rg -n "TEMPORARY_ROUTE_ENGINES|inspection_draft|production generation currently supports only stingray" scripts tests docs/Audit-route-map.md docs/audit-cleanup
```

The final `rg` should find only historical mentions in completed specs, if any. Active code/tests/route-map should not require the retired route split.

## Risks and mitigations

Risk: a wholesale Stingray switch to the current inspection builder silently drops sections, rules, color overrides, or payload fields.

Mitigation: baseline current route first, compare every preserved runtime and compatibility artifact, and treat any non-timestamp drift as a blocker unless separately approved.

Risk: a shared assembler grows a new parallel taxonomy or model-specific product branches.

Mitigation: keep the assembler workbook-driven and generic; defer product-rule cleanup to Pass 7.

Risk: explicit review artifacts for Grand Sport/Z06 drift while runtime contracts stay green.

Mitigation: snapshot explicit review-mode artifacts before implementation and compare all review JSON outputs after implementation.

Risk: tests continue asserting the temporary route split.

Mitigation: update route tests to reject `TEMPORARY_ROUTE_ENGINES` and require one normalized source assembly path.

Risk: stdout route normalization hides drift in counts, artifact maps, validation errors, compatibility outputs, or registry publication metadata.

Mitigation: compare before/after generation stdout and registry stdout explicitly, allowlisting only the intended `route_engine` value change.

Risk: end-to-end generated artifact parity is the first signal for source-assembly regressions, making failures slow and hard to localize.

Mitigation: add a focused direct-assembler characterization test for Stingray and one current inspection-route model that checks the known drift surfaces from preflight.

Risk: generated timestamp churn hides unintended payload drift.

Mitigation: use `compare-generated-contracts.mjs`, `cmp`, SHA-256, generated diff review, and restore unrelated generated churn before handoff.

Risk: this pass expands into business-rule cleanup.

Mitigation: keep GBA/ZYC, `runtime_action`, `body_style_scope`, exclusive-group drift, Z06 ID cleanup, and copy decisions out of scope.

## Completion requirements (satisfied)

The implementation summary above records:

- final status and date;
- actual changed files;
- whether `TEMPORARY_ROUTE_ENGINES`, `DEFAULT_ROUTE_ENGINE`, and `inspection_draft` were removed from active code/tests;
- generated artifacts touched and restored;
- runtime contract parity evidence;
- Stingray compatibility JSON/CSV parity evidence;
- stdout and registry stdout parity evidence, with only `route_engine` allowlisted;
- focused direct-assembler characterization test evidence;
- explicit review-mode parity evidence;
- Pass 6B stale-file absence evidence;
- gates run;
- residual risks;
- recommended next pass.

Also update `docs/Audit-route-map.md` so it no longer describes active source assembly as split after implementation.

## Recommended next pass after Pass 6C

Pass 7 should begin business-rule hardcode cleanup only after source assembly is genuinely unified and parity-proven. First likely Pass 7 item: remove the browser runtime GBA/ZYC hardcode only if workbook `runtime_rule_exceptions` fully covers the behavior and focused runtime tests can prove parity.

## Historical approval prompt

Approved by user on 2026-06-21: "6c is approved".
