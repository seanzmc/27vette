# Pass 20 — Variant Topology Clarification Spec

Status: Implemented on 2026-06-24.
Date: 2026-06-24
Recommended reasoning level for implementation agent: high.

Source context:

- `AGENTS.md`
- `docs/Audit-route-map.md`
- `docs/metadata-runtime-redundancy-6-23.md`
- `docs/audit-cleanup/pass-19-global-variant-option-overrides-retirement-spec.md`
- `scripts/corvette_form_generator/model_configs.py`
- `scripts/corvette_form_generator/runtime_metadata.py`
- `scripts/corvette_form_generator/inspection.py`
- `scripts/corvette_form_generator/schema_validation.py`
- `scripts/promote_model.py`
- `scripts/workbook_editor_server.py`
- `tests/workbook-schema-standardization.test.mjs`
- `tests/test_schema_validation_metadata.py`
- `tests/grand-sport-contract-preview.test.mjs`
- `tests/z06-contract-preview.test.mjs`

## Goal

Clarify the workbook topology split between `variant_master` and `model_variants` so active model generation does not depend on ambiguous or contradictory variant active semantics.

Target ownership contract:

- `variant_master` owns variant facts:
  - `variant_id`
  - trim level
  - body style
  - display name
  - model year
  - base price
  - source/catalog active status for a usable variant fact row
- `model_variants` owns model membership and generated order:
  - `model_key`
  - `variant_id`
  - `display_order`
  - active membership for that model
- `model_master.expected_variant_count` owns the expected active membership count for a generatable model.
- Active/generatable models must have active `model_variants` rows that reference active `variant_master` fact rows.
- Inactive/future model scaffold rows may remain inactive in both `model_variants` and `variant_master` until an approved promotion/intake pass activates them.

This pass should remove the current Grand Sport inconsistency where `model_variants` says Grand Sport variants are active members while `variant_master.active` still says those same fact rows are inactive.

## Diagnosis

Change type for this spec: docs-only.

Change type for the future implementation pass: mixed workbook/data + schema/generator/test/docs, with no intended customer-facing runtime behavior change.

Risk level: medium.

Root cause:

- Earlier model-promotion work made `model_variants` the active/generatable membership source, while `variant_master` continued to carry an `active` column from the shared variant catalog.
- Current active-model discovery correctly uses:

```text
model_master.active
model_workbook_sources exact-match active required source roles
model_variants exact-match active rows matching expected_variant_count
```

- But `variant_master.active` still appears in generated preview metadata as `source_active`, in tests, in promotion tooling, and in warning output.
- Grand Sport is a live active model, but its six active `model_variants` rows reference six `variant_master` rows whose `active` value is `False`.
- Z06 is also live and active, but its six active `model_variants` rows reference active `variant_master` rows.
- This creates a misleading split: generation includes Grand Sport variants from `model_variants`, while inspection emits `source_active="False"` and warns that configured Grand Sport variants are inactive in `variant_master`.

This is not a deletion pass. The two sheets have distinct roles and should both remain.

## Current evidence inspected for this spec

Branch/worktree:

- `git status --short --branch` was run before writing this spec.
- `docs/audit-cleanup/pass-20-variant-topology-clarification-spec.md` did not exist before this spec.

Workbook read-only probe via `openpyxl` after Pass 19:

```text
variant_master rows: 32 / 12 active
model_variants rows: 26 / 18 active
model_master rows: 5 / 3 active
```

Active `model_variants` by model:

```text
stingray:     6 active — 1lt_c07, 2lt_c07, 3lt_c07, 1lt_c67, 2lt_c67, 3lt_c67
grand_sport: 6 active — 1lt_e07, 2lt_e07, 3lt_e07, 1lt_e67, 2lt_e67, 3lt_e67
z06:          6 active — 1lz_h07, 2lz_h07, 3lz_h07, 1lz_h67, 2lz_h67, 3lz_h67
zr1:          0 active
zr1x:         0 active
```

Active `model_variants` rows whose `variant_master` row is inactive:

```text
grand_sport 1lt_e07 variant_master.active=False
grand_sport 2lt_e07 variant_master.active=False
grand_sport 3lt_e07 variant_master.active=False
grand_sport 1lt_e67 variant_master.active=False
grand_sport 2lt_e67 variant_master.active=False
grand_sport 3lt_e67 variant_master.active=False
```

Active `variant_master` rows not referenced by active `model_variants`:

```text
none
```

Relevant consumers:

- `scripts/corvette_form_generator/model_configs.py`
  - `discover_generation_model_configs()` requires active `model_master`, complete active `model_workbook_sources`, and active `model_variants` count matching `model_master.expected_variant_count`.
  - It does not require active `variant_master` rows for generation discovery.
- `scripts/corvette_form_generator/runtime_metadata.py`
  - `load_model_metadata()` and `load_model_config_overrides()` resolve configured variant IDs from active `model_variants` rows.
- `scripts/corvette_form_generator/inspection.py`
  - `build_contract_preview()` reads variant facts from `variant_master` for configured variant IDs.
  - It emits `source_active` from `variant_master.active`.
  - It warns when configured variant IDs are not active in `variant_master`.
- `scripts/promote_model.py`
  - Promotion currently sets `variant_master.active=True` for variants listed in `model_variants`, implying active promoted variants should have active fact rows.
- `scripts/workbook_editor_server.py`
  - The editor uses `variant_master` for variant display names and active `model_variants` for variants by model.
- `tests/grand-sport-contract-preview.test.mjs`
  - Currently asserts Grand Sport preview variants have `source_active === "False"`, locking in the ambiguity.
- `tests/z06-contract-preview.test.mjs`
  - Asserts Z06 preview variants have `source_active === "True"`.
- `tests/workbook-schema-standardization.test.mjs`
  - Guards model metadata and active `model_variants` rows by model, but currently does not require active model variants to reference active `variant_master` fact rows.
- `scripts/corvette_form_generator/schema_validation.py`
  - Requires `variant_master` and `model_variants` sheets, but currently has no explicit topology validation tying active model membership to active fact rows.

Runtime consumer evidence:

- `form-app/app.js` does not consume `source_active`.
- `source_active` appears in generated data and preview/markdown artifacts, but it is metadata/provenance rather than customer-facing selection logic.

## Proposed source-of-truth decision

Adopt this explicit split:

1. `variant_master.active`
   - Means the variant fact row is active/usable as source metadata.
   - Active rows should exist for every active `model_variants` membership row of an active/generatable model.
   - It is not the sole model-generation gate because it does not carry `model_key` or display order.

2. `model_variants.active`
   - Means the variant is an active member of a specific model's generated variant list.
   - It owns model-specific membership and order.
   - It remains the generation membership source together with `model_master.expected_variant_count`.

3. `model_master.active`
   - Means the model is active/generatable when required source roles and active model variants are complete.

4. `model_registry_promotion.promoted_to_runtime`
   - Remains the separate browser publication decision.

## Exact files and workbook sheets to change after approval

Workbook:

- `stingray_master.xlsx`
  - Sheet: `variant_master`
    - Set `active=True` for the six Grand Sport variant fact rows:
      - `1lt_e07`
      - `2lt_e07`
      - `3lt_e07`
      - `1lt_e67`
      - `2lt_e67`
      - `3lt_e67`
  - Sheet: `model_variants`
    - No row additions/removals expected.
    - Keep Grand Sport six active membership rows and display order unchanged.
  - Sheet: `model_master`
    - No row changes expected.
  - Sheet: `model_registry_promotion`
    - No row changes expected.

Code/tests:

- `scripts/corvette_form_generator/schema_validation.py`
  - Add explicit topology validation for active/generatable models:
    - active `model_variants` rows must reference an existing `variant_master` row;
    - active `model_variants` rows for active `model_master` models must reference `variant_master.active=True`;
    - active `model_variants.display_order` values must be unique per model;
    - active `model_variants` count must match `model_master.expected_variant_count` for active models, if this is not already fully covered by the generator-discovery tests.
- `tests/test_schema_validation_metadata.py`
  - Add RED tests for missing/inactive `variant_master` rows referenced by active model variants.
- `tests/workbook-schema-standardization.test.mjs`
  - Update/extend workbook metadata assertions so active model variants reference active variant facts.
  - Keep inactive ZR1/ZR1X scaffold rows allowed.
- `tests/grand-sport-contract-preview.test.mjs`
  - Update `source_active` expectation from `False` to `True` for Grand Sport preview variants.
  - Prefer wording that asserts active Grand Sport model variants have active source fact rows, not that `source_active` drives runtime behavior.
- `tests/z06-contract-preview.test.mjs`
  - No required expectation change beyond ensuring the shared topology assertion applies consistently.
- `scripts/corvette_form_generator/inspection.py`
  - Prefer no code change if activating Grand Sport `variant_master` rows naturally removes the current warning.
  - If code is touched, keep it generic and metadata-only: warning text should distinguish missing/inactive fact rows from generation membership.
- `scripts/promote_model.py`
  - No required behavior change expected. The current `variant_master.active=True` promotion behavior matches the proposed ownership split.

Docs/spec closure:

- `docs/audit-cleanup/pass-20-variant-topology-clarification-spec.md`
  - Mark implemented with changed files/sheets/artifacts, gates, residual risks, and next step.
- `docs/metadata-runtime-redundancy-6-23.md`
  - Update the variant topology section from ambiguous/misaligned to clarified/aligned.
- `docs/Audit-route-map.md`
  - Add Pass 20 completion summary and update bottom-line next-step guidance.
- `AGENTS.md`
  - Update active workbook source-sheet guidance if needed to explicitly state the variant ownership split.

Generated artifacts expected after approval:

- `form-output/runtime/grand-sport-runtime-contract.json`
- `form-app/data.js`

Expected generated drift should be limited to Grand Sport variant provenance metadata:

- `variants[*].source_active`: `"False"` -> `"True"` for six Grand Sport variants.
- Any current Grand Sport warning about configured variants being inactive in `variant_master` should disappear if that warning is emitted into generated metadata or command output.
- `form-app/data.js` must be parsed before and after as `window.CORVETTE_FORM_DATA`; the browser registry allowlist is the same Grand Sport `models.grandSport.data.variants[*].source_active` drift only.
- No choices, standard equipment, rules, price rules, interiors, context choices, order-summary metadata, dealer payload fields, or customer-facing labels should change.

If Stingray or Z06 artifacts are regenerated for validation and only timestamp fields change, restore them before final handoff unless the implementation explicitly justifies a payload change.

## Constraints

- Preserve visual behavior.
- Preserve runtime JavaScript behavior.
- Preserve dealer submission endpoint, payload shape, and Turnstile behavior.
- No new dependencies.
- No broad generator-route refactor.
- No sheet deletion.
- No `variant_id` renames.
- No `model_key` renames.
- No changes to model promotion state.
- No changes to `model_registry_promotion` publication decisions.
- Do not activate ZR1/ZR1X scaffold rows.
- Do not infer new variant facts from marketing/product docs.
- Do not change option, rule, price, interior, or asset rows under this pass.
- Use workbook safe-save for workbook writes.
- Verify saved workbook rows on disk before claiming the workbook change landed.

## Risks

- Generated metadata drift is intentional but narrow. It must be allowlisted to `source_active`/warning metadata for Grand Sport variants only.
- Tests currently lock the ambiguous state for Grand Sport. Updating tests without first adding topology validation would hide the issue rather than fixing it.
- `variant_master.active` must not become a replacement for `model_variants` membership/order. The pass should align active fact rows but preserve `model_variants` as the membership source.
- Future model scaffold rows must remain inactive; a broad active-flag normalization could accidentally make ZR1/ZR1X generatable.
- If `source_active` is consumed outside the searched runtime path, generated drift could matter. Re-run consumer search before implementation and report any new consumer.

## Non-goals

- Do not merge `variant_master` and `model_variants` into one sheet.
- Do not remove either sheet.
- Do not rename generated `source_active` in this pass; that would be a separate runtime-contract shape change.
- Do not change `model_registry_promotion` semantics.
- Do not promote future models.
- Do not adjust active source sheet rows beyond `variant_master.active` for the six Grand Sport variant fact rows.
- Do not change generated choices/rules/prices/interiors.

## Implementation order after approval

1. Preflight:

```sh
git status --short --branch
python3 - <<'PY'
from pathlib import Path
lock = Path('~' + '$' + 'stingray_master.xlsx')
if lock.exists():
    raise SystemExit(f'Excel lock file exists: {lock}')
print('LOCKFILE_ABSENT')
PY
.venv/bin/python scripts/validate_workbook_package.py stingray_master.xlsx
.venv/bin/python scripts/validate_workbook_schema.py stingray_master.xlsx
```

2. Snapshot generated artifacts:

```sh
mkdir -p /tmp/pass-20-before /tmp/pass-20-after
cp form-output/runtime/stingray-runtime-contract.json /tmp/pass-20-before/stingray-runtime-contract.json
cp form-output/runtime/grand-sport-runtime-contract.json /tmp/pass-20-before/grand-sport-runtime-contract.json
cp form-output/runtime/z06-runtime-contract.json /tmp/pass-20-before/z06-runtime-contract.json
cp form-app/data.js /tmp/pass-20-before/data.js
```

3. Add focused RED tests/guards:

- Schema validation rejects active model variants referencing inactive/missing variant facts.
- Workbook schema standardization asserts active `model_variants` for active models reference active `variant_master` rows.
- Grand Sport preview expects `source_active === "True"` after source data is aligned.

4. Safe-save workbook edit:

- Set the six Grand Sport `variant_master.active` values to `True`.
- Verify on disk with `openpyxl`:
  - six Grand Sport active model variants;
  - six corresponding active `variant_master` rows;
  - ZR1/ZR1X variant rows remain inactive.

5. Regenerate and compare:

```sh
.venv/bin/python scripts/generate_form.py --model grand_sport
.venv/bin/python scripts/generate_registry.py
cp form-output/runtime/grand-sport-runtime-contract.json /tmp/pass-20-after/grand-sport-runtime-contract.json
cp form-app/data.js /tmp/pass-20-after/data.js
```

6. Run a custom allowlist diff:

- Normalize timestamps.
- Compare the Grand Sport runtime contract directly.
- Parse/export before and after `form-app/data.js` with a `global.window={}` shim and compare `window.CORVETTE_FORM_DATA` structurally.
- Allow only:
  - Grand Sport `variants[*].source_active` changing from `"False"` to `"True"`;
  - the same Grand Sport `variants[*].source_active` change inside `window.CORVETTE_FORM_DATA.models.grandSport.data`;
  - removal of the existing Grand Sport inactive-variant warning if emitted into generated metadata.
- Fail on any drift in choices, rules, price rules, standard equipment, interiors, context choices, order-summary metadata, or non-Grand-Sport model data.

7. Restore unrelated generated timestamp churn.

8. Run targeted gates.

9. Update the owning spec and standing docs with completion evidence.

## Validation plan after approval

Required gates:

```sh
.venv/bin/python -m py_compile scripts/corvette_form_generator/schema_validation.py scripts/corvette_form_generator/inspection.py scripts/promote_model.py
.venv/bin/python scripts/validate_workbook_package.py stingray_master.xlsx
.venv/bin/python scripts/validate_workbook_schema.py stingray_master.xlsx
.venv/bin/python -m pytest tests/test_schema_validation_metadata.py tests/test_model_config_metadata.py -q
node --test tests/workbook-schema-standardization.test.mjs
node --test tests/grand-sport-contract-preview.test.mjs
node --test tests/grand-sport-draft-data.test.mjs
node --test tests/multi-model-runtime-switching.test.mjs
git diff --check
```

Generated parity/allowlist checks:

```sh
node scripts/compare-generated-contracts.mjs /tmp/pass-20-before/stingray-runtime-contract.json form-output/runtime/stingray-runtime-contract.json
node scripts/compare-generated-contracts.mjs /tmp/pass-20-before/z06-runtime-contract.json form-output/runtime/z06-runtime-contract.json
```

Grand Sport requires a custom allowlist check rather than `compare-generated-contracts.mjs`, because successful implementation intentionally changes Grand Sport variant provenance metadata.

`form-app/data.js` also requires a custom allowlist check. The check must parse/export before and after `window.CORVETTE_FORM_DATA`, normalize timestamps, allow only Grand Sport `models.grandSport.data.variants[*].source_active` values changing from `"False"` to `"True"`, and fail on any other registry drift.

Optional browser proof:

- Not required if final drift is limited to Grand Sport `variants[*].source_active` metadata and no runtime JS changes are made.
- Required if any customer-facing generated choice/rule/price/interior/runtime behavior changes appear during diff review.

Final cleanliness checks:

```sh
git diff --quiet -- form-output/runtime/stingray-runtime-contract.json
git diff --quiet -- form-output/runtime/z06-runtime-contract.json
# Grand Sport/form-app generated diffs must match the explicit allowlist only.
```

## Implementation result

Implemented on 2026-06-24.

Changed files and sheets:

- `stingray_master.xlsx`
  - Sheet `variant_master`: set `active=True` for `1lt_e07`, `2lt_e07`, `3lt_e07`, `1lt_e67`, `2lt_e67`, and `3lt_e67`.
  - Sheet `model_variants`: unchanged; Grand Sport keeps six active membership/order rows.
  - ZR1/ZR1X scaffold membership remained inactive.
- `scripts/corvette_form_generator/schema_validation.py`
  - Added variant-topology validation for active models: active model variants must reference existing active variant fact rows, active display order must be unique per model, and active membership count must match `model_master.expected_variant_count` when specified.
- `tests/test_schema_validation_metadata.py`
  - Added focused schema tests for missing/inactive variant fact rows, duplicate active display order, and expected-count mismatch.
- `tests/workbook-schema-standardization.test.mjs`
  - Added live workbook guard that active model variants reference active `variant_master` fact rows.
- `tests/grand-sport-contract-preview.test.mjs`
  - Updated Grand Sport `source_active` expectation to `"True"`.
- Generated artifacts:
  - `form-output/runtime/grand-sport-runtime-contract.json`
  - `form-app/data.js`
- Standing docs:
  - `AGENTS.md`
  - `docs/metadata-runtime-redundancy-6-23.md`
  - `docs/Audit-route-map.md`
  - this spec file

Generated drift:

- Explicit allowlist passed for both Grand Sport runtime contract and parsed `window.CORVETTE_FORM_DATA` in `form-app/data.js`.
- Allowed drift was only the six Grand Sport `variants[*].source_active` values changing from `"False"` to `"True"`.
- Stingray and Z06 runtime contracts matched their pre-pass snapshots with generated timestamps ignored and had no final diff.

Gates run:

```sh
.venv/bin/python -m py_compile scripts/corvette_form_generator/schema_validation.py scripts/corvette_form_generator/inspection.py scripts/promote_model.py
.venv/bin/python scripts/validate_workbook_package.py stingray_master.xlsx
.venv/bin/python scripts/validate_workbook_schema.py stingray_master.xlsx
.venv/bin/python -m pytest tests/test_schema_validation_metadata.py tests/test_model_config_metadata.py -q
node --test tests/workbook-schema-standardization.test.mjs
node --test tests/grand-sport-contract-preview.test.mjs
node --test tests/grand-sport-draft-data.test.mjs
node --test tests/multi-model-runtime-switching.test.mjs
node scripts/compare-generated-contracts.mjs /tmp/pass-20-before/stingray-runtime-contract.json form-output/runtime/stingray-runtime-contract.json
node scripts/compare-generated-contracts.mjs /tmp/pass-20-before/z06-runtime-contract.json form-output/runtime/z06-runtime-contract.json
# custom Node allowlist for Grand Sport runtime contract and form-app/data.js registry source_active drift
git diff --check
```

Gate results:

- Workbook package validation: valid, 0 issues.
- Workbook schema validation: valid, 0 issues.
- Pytest metadata/model config tests: 43 passed.
- `workbook-schema-standardization.test.mjs`: 9 passed.
- `grand-sport-contract-preview.test.mjs`: 6 passed.
- `grand-sport-draft-data.test.mjs`: 19 passed.
- `multi-model-runtime-switching.test.mjs`: 46 passed.
- Custom runtime/data.js allowlist: `PASS20_FINAL_RUNTIME_AND_DATAJS_ALLOWLIST_OK`.
- `git diff --check`: passed.

Browser proof:

- Not run. No runtime JavaScript changed, and generated drift was provenance metadata only.

Residual risks / follow-up:

- `variant_master` and `model_variants` both remain active source sheets with distinct owners; do not collapse either sheet without a separate spec.
- No obvious next cleanup pass is implied by this pass alone. Larger remaining cleanup candidates are separate scopes: direct-rule field classification/migration, runtime/generator fallback retirement, and broader generator consolidation.

## Historical approval prompt

Pass 20 was approved and implemented as a narrow variant-topology clarification pass: align the six active Grand Sport `variant_master` fact rows with active `model_variants` membership, add schema/tests so active model variants must reference active variant facts, allowlist only Grand Sport `source_active`/warning metadata drift in both the runtime contract and parsed `form-app/data.js` registry, and update docs with the clarified ownership split between `variant_master` and `model_variants`.
