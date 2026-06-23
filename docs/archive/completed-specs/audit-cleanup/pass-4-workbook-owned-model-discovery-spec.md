# Pass 4 — Workbook-Owned Model Discovery Spec

Status: Implemented 2026-06-21.
Date: 2026-06-21
Recommended reasoning level for implementation agent: high.

## Goal

Make `scripts/generate_form.py --model <model>` discover eligible model keys from workbook metadata instead of the hardcoded Python `MODEL_CONFIGS` dictionary.

After this pass, adding a future model to the generation command should require workbook metadata/source rows, not edits to `generate_form.py` or per-model Python config constants. Runtime promotion remains separately owned by `model_registry_promotion`; activating a model for generation must not promote it to `form-app/data.js` unless the workbook promotion row explicitly does so.

## Diagnosis

### Root cause

Passes 1-3 normalized runtime-contract generation and retired the Stingray-only workbook `form_*` output surface, but the CLI still carries a model allowlist in Python:

- `scripts/generate_form.py` imports `STINGRAY_MODEL`, `GRAND_SPORT_MODEL`, and `Z06_MODEL`.
- `scripts/generate_form.py` defines `MODEL_CONFIGS = {"stingray": ..., "grand_sport": ..., "z06": ...}`.
- `argparse` restricts `--model` to `sorted(MODEL_CONFIGS)`.
- `scripts/corvette_form_generator/model_configs.py` already has a generic `base_model_config(model_key)` that can build conventional defaults for any model key, but the CLI does not use workbook metadata to decide which model keys are available.

This leaves one remaining Python edit point for future model generation even though workbook metadata already carries the model graph.

### Evidence inspected

Preflight evidence from this spec-writing pass:

- Branch/worktree:
  - current branch: `schema-ingestion-normalization`
  - `origin/main` is an ancestor of `HEAD`
  - `git rev-list --left-right --count HEAD...origin/main` returned `0\t0`
  - worktree is dirty from the just-completed Pass 3 implementation; Pass 4 implementation must re-check and avoid mixing unrelated changes.
- `docs/Audit-route-map.md:246-250` identifies Pass 4 as replacing hardcoded `MODEL_CONFIGS` with workbook-driven model discovery from `model_master` plus complete active `model_workbook_sources` rows.
- `scripts/generate_form.py:31-41` imports per-model constants and hardcodes `MODEL_CONFIGS` and `PRODUCTION_MODEL_KEYS`.
- `scripts/corvette_form_generator/model_configs.py:169-210` already exposes `base_model_config(model_key)` but still defines `STINGRAY_MODEL`, `GRAND_SPORT_MODEL`, and `Z06_MODEL` constants.
- `scripts/corvette_form_generator/runtime_metadata.py:526-657` loads `model_master`, `model_workbook_sources`, and `model_variants`, then applies workbook metadata through `load_model_config_overrides()`.
- `scripts/corvette_form_generator/runtime_metadata.py:629-632` still lets `load_model_config_overrides()` fall back to the base config's `expected_variant_count` and `variant_ids` when active `model_variants` rows are absent. Because `base_model_config()` defaults to `expected_variant_count=0` and `variant_ids=()`, discovery must validate active workbook variant rows directly before treating a model as generatable.
- `scripts/corvette_form_generator/runtime_metadata.py:69-81` scopes `active_rows(..., model_key)` to the requested key plus global keys (`all`, `shared`, `*`). That behavior is valid for runtime metadata, but generation discovery must prove model-owned source completeness with exact `model_key` matches.
- `tests/test_model_config_metadata.py` currently imports `STINGRAY_MODEL` and covers workbook override behavior, duplicate source roles, unknown roles, variant counts, duplicate variants, and registry-key drift.
- `tests/test_runtime_contract_builder.py` currently imports `GRAND_SPORT_MODEL`.
- Read-only workbook probe of `stingray_master.xlsx` found:
  - `model_master`: 5 rows total.
  - Active models: `stingray`, `grand_sport`, `z06`.
  - Inactive future scaffolds: `zr1`, `zr1x`.
  - `model_workbook_sources`: 52 rows total.
  - Active source roles:
    - `stingray`: 10 roles, no `variant_option_overrides_sheet` role.
    - `grand_sport`: 11 roles including `variant_option_overrides_sheet`.
    - `z06`: 11 roles including `variant_option_overrides_sheet`.
    - `zr1` / `zr1x`: 0 active source roles; scaffold source rows are inactive.
  - `model_variants`: 26 rows total.
  - `model_registry_promotion`: active promoted runtime rows for `stingray`, `grand_sport`, and `z06`; inactive unpromoted rows for `zr1` and `zr1x`.

### Risk level

Medium.

This pass should not change generated runtime payloads or workbook source data, but it changes the CLI model resolution path used by every generator run. A bad implementation can:

- accidentally make inactive ZR1/ZR1X scaffolds generatable or promoted;
- silently fall back to default sheet names when required workbook metadata is missing;
- silently treat an active future model with complete source roles but missing/blank variant metadata as generatable because Python defaults are empty/zero;
- let shared/global source rows satisfy per-model generation completeness if discovery reuses `active_rows(..., model_key)` without exact-match filtering;
- break `--model stingray` by removing the production route boundary too early;
- break imports/tests that still rely on per-model constants;
- make `--help` or error handling depend on a corrupt/missing workbook in a confusing way.

### Change type

Mixed code/tests/docs, no workbook source-data change intended.

## Ownership decision

- Workbook owns model availability for generation through `model_master.active`, `model_workbook_sources.active`, and `model_variants.active`.
- Workbook owns runtime promotion separately through `model_registry_promotion.promoted_to_runtime` and `active`.
- Python may keep generic filesystem paths, compatibility defaults, output route selection, and validation helpers.
- Python should not keep a hardcoded list of active model keys in `generate_form.py`.
- Discovery must not rely on Python fallback config to prove workbook variant availability. Active `model_master.expected_variant_count` and exact-match active `model_variants` rows are part of the generation-eligibility contract.

## Exact files to change

### Required code changes

1. `scripts/corvette_form_generator/model_configs.py`
   - Keep `base_model_config(model_key)` as the generic factory.
   - Add a workbook-backed discovery helper here rather than creating a new module unless implementation proves a new module is necessary.
   - Proposed helper shape:
     - `REQUIRED_GENERATION_SOURCE_ROLES = (...)`
     - `discover_generation_model_configs(workbook_path: Path = WORKBOOK_PATH) -> dict[str, ModelConfig]`
   - The helper should:
     - open `stingray_master.xlsx` read-only;
     - load active `model_master` rows in workbook row order;
     - exclude inactive `model_master` rows such as `zr1` and `zr1x`;
     - require every active/generatable model to have `model_master.expected_variant_count > 0`;
     - require at least one exact-match active `model_variants` row for the model;
     - require exact-match active `model_variants` count to equal `model_master.expected_variant_count`;
     - require every active/generatable model to have the complete required active source-role set with exact `model_key` matches only;
     - not let global/shared rows (`all`, `shared`, `*`) satisfy generation source-role completeness;
     - treat `variant_option_overrides_sheet` as optional because Stingray currently has no active role for it;
     - call `base_model_config(model_key)` then `load_model_config_overrides(wb, base_config)`;
     - use `load_model_config_overrides()` as a second-stage config resolver, not as the sole proof that variants exist;
     - fail fast on duplicate active model rows, unknown roles, missing required exact-match roles, duplicate exact-match variants, missing/zero expected variant count, no active exact-match variant rows, and expected-variant-count mismatch;
     - not inspect or require runtime promotion.
   - Remove `STINGRAY_MODEL`, `GRAND_SPORT_MODEL`, and `Z06_MODEL` after all imports are updated.

2. `scripts/generate_form.py`
   - Replace the hardcoded `MODEL_CONFIGS` dictionary with workbook discovery.
   - Accept `--model` as a string, then validate it against discovered active/generatable models with a clear error such as:
     - `Unsupported or inactive model 'zr1'. Active generatable models: stingray, grand_sport, z06.`
   - Keep `PRODUCTION_MODEL_KEYS = {"stingray"}` in this pass. This pass is model discovery, not full generation-route unification.
   - Keep `run_production()` for Stingray and `run_draft()` for non-production models.
   - Do not make runtime promotion decisions here.
   - Do not write `stingray_master.xlsx`.

3. `scripts/corvette_form_generator/production.py`
   - Replace `from corvette_form_generator.model_configs import STINGRAY_MODEL` with `base_model_config("stingray")` or another generic equivalent.
   - Preserve the Stingray production path behavior from Pass 3:
     - no routine workbook save;
     - `"workbook_backup": null` in stdout JSON;
     - compatibility JSON/CSV and runtime-contract artifacts still written.

4. `scripts/build_rule_sources.py`
   - Inspect before editing. It already uses `base_model_config(args.model)` and may not require a code change.
   - If it has its own hardcoded model choices or stale help text, update only the discovery/help surface needed by this pass.

### Required test changes

1. `tests/test_model_config_metadata.py`
   - Replace `STINGRAY_MODEL` usage with `base_model_config("stingray")`.
   - Add RED/green tests for the discovery helper:
     - active rows in `model_master` with complete active required `model_workbook_sources` rows are discovered;
     - inactive scaffold rows are excluded even if sheet names exist;
     - missing required active source roles for an active model fail fast;
     - inactive source-role rows do not satisfy required-role completeness;
     - global/shared source rows (`all`, `shared`, `*`) do not satisfy per-model generation completeness;
     - missing or zero `model_master.expected_variant_count` fails fast for active models;
     - missing/blank exact-match active `model_variants` rows fail fast even if source roles are complete;
     - exact-match active variant count must equal `expected_variant_count`;
     - runtime promotion metadata is not required for discovery.

2. `tests/test_runtime_contract_builder.py`
   - Replace `GRAND_SPORT_MODEL` usage with `base_model_config("grand_sport")`, or use a resolved config only if the test needs workbook metadata.

3. `tests/stingray-generator-stability.test.mjs`
   - Add or update a source guard that `scripts/generate_form.py` no longer defines a hardcoded `MODEL_CONFIGS` map or uses `choices=sorted(MODEL_CONFIGS)`.
   - Keep the existing Pass 3 guard proving routine Stingray generation does not write workbook generated sheets.

4. Add a required focused Python or Node CLI smoke/negative test, for example `tests/test_generate_form_model_discovery_cli.py`, that verifies:
   - `generate_form.py --model stingray` succeeds;
   - `generate_form.py --model stingray` still reaches the Stingray production path, not the draft/inspection path;
   - `generate_form.py --model zr1` fails while ZR1 is inactive, without writing artifacts or promoting it.

### Required docs changes

1. `docs/Audit-route-map.md`
   - Link Pass 4 to this spec.
   - Do not mark Pass 4 implemented until the implementation pass lands.

2. `docs/audit-cleanup/pass-4-workbook-owned-model-discovery-spec.md`
   - Update status/evidence after implementation if approved and run.

3. `README.md` / `AGENTS.md`
   - Change only if implementation changes user-facing command semantics or active-model wording.
   - Do not expand docs beyond the approved model-discovery scope.

## Required source-role completeness policy

For active/generatable models, require active `model_workbook_sources` rows with an exact `model_key` equal to the candidate model for:

- `source_option_sheet`
- `status_sheet`
- `rule_mapping_sheet`
- `price_rules_sheet`
- `rule_groups_sheet`
- `rule_group_members_sheet`
- `exclusive_groups_sheet`
- `exclusive_group_members_sheet`
- `color_overrides_sheet`
- `interior_source_sheet`

Treat this role as optional:

- `variant_option_overrides_sheet`

Reason: the current workbook has no active Stingray `variant_option_overrides_sheet` role, while Grand Sport and Z06 do. Requiring it would create a workbook schema change not needed for model discovery.

Do not use `active_rows(wb, "model_workbook_sources", model_key)` directly for this completeness check unless that helper is changed or wrapped to exact-match semantics. The current helper intentionally includes global keys (`all`, `shared`, `*`), which must not satisfy model-owned generation availability.

## Required variant completeness policy

For active/generatable models, require active workbook variant metadata with exact `model_key` matches:

- `model_master.expected_variant_count` must parse to an integer greater than 0.
- At least one active `model_variants` row must exist for the model.
- Active exact-match `model_variants` count must equal `model_master.expected_variant_count`.
- Duplicate active exact-match `variant_id` values must fail fast.

Do not rely on `load_model_config_overrides()` alone to prove variant availability. It still has compatibility fallback semantics for absent variant metadata; generation discovery must be stricter than that fallback path.

## Constraints

- Preserve visual behavior.
- Preserve runtime behavior and generated payloads except timestamps from validation runs.
- Preserve dealer endpoint, dealer payload shape, and Turnstile behavior.
- No new dependencies.
- No workbook writes in Pass 4 implementation unless a later approved correction explicitly requires source metadata changes. Current evidence shows no workbook source change is needed.
- Use `.venv/bin/python`, not system Python.
- Do not promote ZR1 or ZR1X.
- Do not activate ZR1 or ZR1X in `model_master`.
- Do not infer or invent future-model source data.
- Do not remove `PRODUCTION_MODEL_KEYS = {"stingray"}` in this pass; generation-route unification is a later architecture pass.
- Do not delete compatibility JSON/CSV outputs.
- Do not hand-edit generated artifacts. Regenerate, compare, and restore timestamp-only churn when payload parity is expected.
- Before implementation, re-check branch/status and verify the base against `origin/main`; stale local base/regeneration can undo recent workbook fixes.

## Non-goals

- Full unification of the Stingray production path and non-Stingray draft/inspection path.
- Runtime promotion or activation of any inactive future model.
- Workbook edits to `model_master`, `model_workbook_sources`, `model_variants`, or `model_registry_promotion`.
- Schema validator Pass 5 cleanup.
- Removing optional inspection/preview/draft artifacts.
- Browser runtime changes.
- Dealer submission changes.

## Implementation outline

1. Re-run preflight:

```sh
git status --short --branch
git branch --show-current
git merge-base --is-ancestor origin/main HEAD; echo $?
git rev-list --left-right --count HEAD...origin/main
```

Stop before generator/workbook work if the branch is stale relative to `origin/main` or if unrelated dirty files overlap this pass.

2. Add discovery helper in `model_configs.py`.

Suggested semantics:

```text
active model_master row
+ expected_variant_count > 0
+ complete required exact-match active model_workbook_sources roles
+ at least one exact-match active model_variants row
+ exact-match active model_variants count == expected_variant_count
= generatable model config
```

3. Replace `generate_form.py` hardcoded model map with discovered configs.

4. Replace per-model config constant imports in affected code/tests with `base_model_config(<key>)` or the discovery helper.

5. Run source guards and focused tests before generators.

6. Snapshot generated runtime contracts to `/tmp` before regeneration.

7. Regenerate active models and registry, compare generated contracts ignoring timestamps, then restore timestamp-only generated churn if no substantive payload changes are approved.

8. Confirm `generate_form.py --model zr1` remains rejected while ZR1 is inactive and unpromoted.

## Validation plan

### Static/source checks

```sh
.venv/bin/python -m py_compile \
  scripts/generate_form.py \
  scripts/build_rule_sources.py \
  scripts/corvette_form_generator/model_config.py \
  scripts/corvette_form_generator/model_configs.py \
  scripts/corvette_form_generator/production.py \
  scripts/corvette_form_generator/runtime_metadata.py
```

```sh
rg -n "MODEL_CONFIGS|STINGRAY_MODEL|GRAND_SPORT_MODEL|Z06_MODEL|choices=sorted\(MODEL_CONFIGS\)" scripts tests
```

Expected after implementation: only historical/docs references or intentionally retained compatibility text outside active `scripts/` and `tests/`. Active generation code should not use the per-model constants.

### Focused Python tests

```sh
.venv/bin/python -m pytest \
  tests/test_model_config_metadata.py \
  tests/test_generate_form_model_discovery_cli.py \
  tests/test_runtime_contract_builder.py \
  tests/test_registry_promotion_metadata.py \
  tests/test_schema_validation_metadata.py \
  -q
```

### Workbook/schema checks

```sh
.venv/bin/python scripts/validate_workbook_package.py stingray_master.xlsx
.venv/bin/python scripts/validate_workbook_schema.py stingray_master.xlsx
```

### Generator smoke and negative CLI guard

```sh
.venv/bin/python scripts/generate_form.py --model stingray
.venv/bin/python scripts/generate_form.py --model grand_sport
.venv/bin/python scripts/generate_form.py --model z06
.venv/bin/python scripts/generate_registry.py
```

Negative guard:

```sh
if .venv/bin/python scripts/generate_form.py --model zr1; then
  echo "ERROR: inactive zr1 unexpectedly generated" >&2
  exit 1
fi
```

Expected: `zr1` fails with a clear unsupported/inactive model error while workbook rows remain inactive and unpromoted.

### Generated contract parity

Before regeneration, snapshot:

```sh
BASE=/tmp/27vette-pass4-model-discovery-$(date -u +%Y%m%dT%H%M%SZ)
mkdir -p "$BASE"
cp form-output/runtime/stingray-runtime-contract.json "$BASE/stingray-runtime-contract.json"
cp form-output/runtime/grand-sport-runtime-contract.json "$BASE/grand-sport-runtime-contract.json"
cp form-output/runtime/z06-runtime-contract.json "$BASE/z06-runtime-contract.json"
cp form-output/stingray-form-data.json "$BASE/stingray-form-data.json"
```

After regeneration:

```sh
node scripts/compare-generated-contracts.mjs "$BASE/stingray-runtime-contract.json" form-output/runtime/stingray-runtime-contract.json
node scripts/compare-generated-contracts.mjs "$BASE/grand-sport-runtime-contract.json" form-output/runtime/grand-sport-runtime-contract.json
node scripts/compare-generated-contracts.mjs "$BASE/z06-runtime-contract.json" form-output/runtime/z06-runtime-contract.json
node scripts/compare-generated-contracts.mjs "$BASE/stingray-form-data.json" form-output/stingray-form-data.json
```

Expected: all match after timestamp normalization.

### Runtime/model tests

Run sequentially where tests can regenerate shared artifacts:

```sh
node --test tests/stingray-generator-stability.test.mjs
node --test tests/stingray-form-regression.test.mjs
node --test tests/workbook-schema-standardization.test.mjs
node --test tests/grand-sport-contract-preview.test.mjs
node --test tests/grand-sport-draft-data.test.mjs
node --test tests/z06-contract-preview.test.mjs
node --test tests/z06-form-data-draft.test.mjs
node --test tests/multi-model-runtime-switching.test.mjs
```

### Final checks

```sh
git diff --check
git status --short --branch
```

Review generated artifact diffs. If they are timestamp-only and no generated payload change is approved, restore them before handoff and rerun the focused sync/stability gates necessary to prove retained files are valid.

## Rollback plan

- Revert code/test/docs changes.
- No workbook backup should be needed because this pass should not write `stingray_master.xlsx`.
- If a validation run created timestamp-only generated artifact churn, restore `form-output/*` and `form-app/data.js` from git.
- Re-run current active model generators and registry if needed to return generated artifacts to a known state.

## Residual risks

- Discovery helper strictness can reject a real active model if the required-role set is too broad. The required-role list above intentionally keeps `variant_option_overrides_sheet` optional to avoid this for Stingray.
- Keeping `PRODUCTION_MODEL_KEYS = {"stingray"}` means one generation-route seam remains after this pass. That is deliberate; route unification is not part of model discovery.
- Existing full `tests/stingray-generator-stability.test.mjs` has a known unrelated Z06 `required_charges` expected-list drift from Pass 3 validation. If still present, report it separately and do not patch it inside Pass 4 unless the user explicitly approves that fix.
- `--help` behavior depends on the chosen CLI implementation. Prefer parsing `--model` as a string then validating after workbook discovery so help remains available even if workbook metadata is temporarily invalid.

## Historical approval prompt

Pre-implementation approval prompt:

Historical question: should Pass 4 implementation proceed as scoped above?

Recommended answer was: approve. This removes the remaining Python active-model allowlist from `generate_form.py` while preserving current generated runtime contracts, keeping ZR1/ZR1X inactive/unpromoted, and leaving the larger production-vs-draft route unification for a later pass.

## Implementation evidence

Implemented 2026-06-21.

Changed code/tests:

- `scripts/corvette_form_generator/model_configs.py`
  - Added `REQUIRED_GENERATION_SOURCE_ROLES` and `discover_generation_model_configs()`.
  - Discovery reads `stingray_master.xlsx` metadata read-only.
  - Active/generatable models must have complete exact-match active `model_workbook_sources` roles, positive `model_master.expected_variant_count`, and exact-match active `model_variants` count equal to expected count.
  - Per-model config constants were removed.
- `scripts/generate_form.py`
  - Removed hardcoded `MODEL_CONFIGS` and argparse choices.
  - Validates requested model against workbook-discovered active/generatable configs.
  - Keeps `PRODUCTION_MODEL_KEYS = {"stingray"}` unchanged.
- `scripts/corvette_form_generator/production.py`
  - Uses `base_model_config("stingray")` instead of `STINGRAY_MODEL`.
- `tests/test_model_config_metadata.py`
  - Added discovery tests for active metadata, inactive scaffold exclusion, exact source-role matching, shared/global row rejection, positive expected variant count, active variant rows, variant-count matching, and promotion independence.
- `tests/test_generate_form_model_discovery_cli.py`
  - Added CLI smoke/negative tests for Stingray production-path generation and inactive `zr1` rejection.
- `tests/stingray-generator-stability.test.mjs`
  - Added source guard against reintroducing hardcoded `MODEL_CONFIGS` / per-model constants / argparse choices.
- `tests/test_runtime_contract_builder.py`
  - Replaced `GRAND_SPORT_MODEL` import with `base_model_config("grand_sport")`.

Validation summary:

- `origin/main` verified as ancestor of `HEAD`; branch was not stale (`HEAD...origin/main` count `0\t0`).
- `.venv/bin/python -m py_compile scripts/generate_form.py scripts/build_rule_sources.py scripts/corvette_form_generator/model_config.py scripts/corvette_form_generator/model_configs.py scripts/corvette_form_generator/production.py scripts/corvette_form_generator/runtime_metadata.py` — pass.
- `rg -n "MODEL_CONFIGS|STINGRAY_MODEL|GRAND_SPORT_MODEL|Z06_MODEL|choices=sorted\(MODEL_CONFIGS\)" scripts tests` — active hits only in the new source guard assertions.
- `.venv/bin/python -m pytest tests/test_model_config_metadata.py tests/test_generate_form_model_discovery_cli.py tests/test_runtime_contract_builder.py tests/test_registry_promotion_metadata.py tests/test_schema_validation_metadata.py -q` — 47 passed.
- `PYTHONPATH=scripts .venv/bin/python` discovery probe — discovered `['stingray', 'grand_sport', 'z06']`; all have six active variants and expected count 6.
- Negative CLI probe: `.venv/bin/python scripts/generate_form.py --model zr1` rejects `zr1` with `Unsupported or inactive model 'zr1'. Active generatable models: grand_sport, stingray, z06`.
- `.venv/bin/python scripts/validate_workbook_package.py stingray_master.xlsx` — valid, 0 issues.
- `.venv/bin/python scripts/generate_form.py --model stingray` — pass, `choices=1422`, `rules=144`, `validation_errors=0`.
- `.venv/bin/python scripts/generate_form.py --model grand_sport` — pass, `choices=1422`, `rules=122`, `validation_warnings=1`.
- `.venv/bin/python scripts/generate_form.py --model z06` — pass, `choices=1428`, `rules=73`, `validation_warnings=1`.
- `.venv/bin/python scripts/generate_registry.py` — pass, published `stingray`, `grandSport`, `z06` from runtime contracts.
- `.venv/bin/python scripts/validate_workbook_schema.py stingray_master.xlsx` — valid, 0 issues.
- Runtime-contract parity checks against `/tmp/27vette-pass4-model-discovery-20260621T185808Z` — all matched after timestamp normalization for Stingray, Grand Sport, Z06 runtime contracts and `form-output/stingray-form-data.json`.
- Generated `form-output/*` and `form-app/data.js` timestamp-only churn was restored; no generated artifact diff is retained.

Node gate results:

- Passed:
  - `node --test tests/stingray-form-regression.test.mjs`
  - `node --test tests/workbook-schema-standardization.test.mjs`
  - `node --test tests/grand-sport-contract-preview.test.mjs`
  - `node --test tests/grand-sport-draft-data.test.mjs`
  - `node --test tests/z06-form-data-draft.test.mjs`
  - `node --test tests/multi-model-runtime-switching.test.mjs`
  - `node --test tests/workbook-visual-copy-standardization.test.mjs`
  - `node --test tests/z06-runtime-promotion.test.mjs`
  - `node --test tests/z06-interior-accessory-cleanup.test.mjs`
  - `node --test tests/z06-performance-package-interactions.test.mjs`
  - `node --test tests/z06-runtime-rule-corrections.test.mjs`
- Known pre-existing/stale expectation failures, not patched in this pass:
  - `node --test tests/stingray-generator-stability.test.mjs` fails only in the existing Z06 order-summary expectation: actual workbook data includes `required_charges / Required Charges / 15`; the new Pass 4 source guard in that file passed.
  - `node --test tests/z06-contract-preview.test.mjs` fails because Z06 preview section count is now 12 vs stale expected 11, same required-charges surface.

No workbook source rows were changed. No ZR1/ZR1X rows were activated or promoted.
