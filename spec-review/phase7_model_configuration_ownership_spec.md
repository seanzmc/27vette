# Phase 7 Spec — Model Configuration Ownership

Status: proposed; awaiting approval before implementation.

## 1. Diagnosis

Phase 6 finished moving step, section, context, and presentation metadata toward workbook ownership. The next remaining coded-rule finding is model-to-sheet and variant-id ownership.

Root cause: model identity and core source wiring are still primarily authored in Python constants in `scripts/corvette_form_generator/model_configs.py`. The workbook metadata sheets for this purpose already exist, and `runtime_metadata.py` already has a low-level `load_model_metadata()` helper, but the active generators still start from static `ModelConfig` constants and read fields such as `source_option_sheet`, `status_sheet`, `variant_ids`, `expected_variant_count`, model labels, and dataset names from code.

Current evidence inspected:

- `scripts/corvette_form_generator/model_configs.py`
  - `STINGRAY_MODEL` hardcodes:
    - `model_key="stingray"`
    - `model_label="Stingray"`
    - `model_year="2027"`
    - `dataset_name="2027 Corvette Stingray operational form"`
    - `source_option_sheet="stingray_options"`
    - `status_sheet="stingray_ovs"`
    - `variant_ids=("1lt_c07", "2lt_c07", "3lt_c07", "1lt_c67", "2lt_c67", "3lt_c67")`
    - `expected_variant_count=6`
  - `GRAND_SPORT_MODEL` hardcodes:
    - `model_key="grand_sport"`
    - `model_label="Grand Sport"`
    - `model_year="2027"`
    - `dataset_name="2027 Corvette Grand Sport operational form"`
    - `source_option_sheet="grandSport_options"`
    - `status_sheet="grandSport_ovs"`
    - `variant_ids=("1lt_e07", "2lt_e07", "3lt_e07", "1lt_e67", "2lt_e67", "3lt_e67")`
    - `expected_variant_count=6`
- `scripts/corvette_form_generator/model_config.py`
  - `ModelConfig` is a frozen dataclass and currently has no `with_overrides()`/`replace()` helper.
- `scripts/corvette_form_generator/runtime_metadata.py`
  - Existing `load_model_metadata(wb, model_key)` reads optional `model_master`, `model_workbook_sources`, and `model_variants` rows and returns structured dictionaries.
  - It is not yet wired into `ModelConfig` construction/override use by generators.
- `scripts/generate_stingray_form.py`
  - Starts from `MODEL_CONFIG = STINGRAY_MODEL` and module-level copies of config fields.
  - Reads `MODEL_CONFIG.source_option_sheet`, `MODEL_CONFIG.status_sheet`, and `MODEL_CONFIG.variant_ids` during generation.
  - Uses `GRAND_SPORT_MODEL` for registry merge metadata from the Grand Sport draft artifact.
- `scripts/generate_grand_sport_form.py`
  - Starts from `config = GRAND_SPORT_MODEL` and passes it into inspection/draft generation.
- `scripts/corvette_form_generator/inspection.py`
  - Uses `config.source_option_sheet` and `config.variant_ids` throughout Grand Sport inspection/draft generation.
- Workbook inspection with `openpyxl`:
  - `model_master` exists with headers but currently has 0 data rows.
  - `model_workbook_sources` exists with headers but currently has 0 data rows.
  - `model_variants` exists with headers but currently has 0 data rows.
  - `variant_master` contains the active/current variant IDs and display order, including the six Stingray rows and six Grand Sport rows that match the current constants.
- Git status:
  - Only untracked `.DS_Store` files and `backups/` were present at inspection time.
  - No implementation edits were made for this spec.

Risk level: Low-Medium.

Change type: mixed workbook/data + generator/config + test change. It should be behavior-preserving/output-preserving. The goal is not to change active model behavior, source sheet names, model registry keys, variant sets, pricing, runtime UI, or dealer submission payloads.

Data-integrity concern: if these model/source/variant fields remain only in code, future workbook model activation or source-sheet promotion can drift from generator wiring. If moved incorrectly, the generator could read the wrong source sheets, include the wrong variants, change registry labels/keys, or write malformed app data.

## 2. Objective

Make workbook-authored model metadata the preferred source for core model configuration while preserving Python constants as safe fallbacks for this migration release.

Specifically:

1. Populate `model_master`, `model_workbook_sources`, and `model_variants` with rows matching current behavior.
2. Add a `ModelConfig.with_overrides()` helper.
3. Add a loader that converts workbook model metadata into a safe `ModelConfig` override.
4. Wire both Stingray and Grand Sport generator entrypoints to resolve workbook-backed config after loading `stingray_master.xlsx`.
5. Add tests proving parity and fallback behavior.
6. Keep current generated contracts unchanged except for metadata fields that are already expected to match the constants exactly.

## 3. Exact workbook sheets to change

Canonical workbook: `stingray_master.xlsx`.

Do not edit generated `form_*` sheets directly.

### 3.1 `model_master`

Add active rows matching current constants:

```text
model_key   registry_key  model_label  model_year  dataset_name                                      export_slug   expected_variant_count  default_model  active  notes
stingray    stingray      Stingray     2027        2027 Corvette Stingray operational form           stingray      6                       TRUE           TRUE    Phase 7 parity row matching existing STINGRAY_MODEL.
grand_sport grandSport    Grand Sport  2027        2027 Corvette Grand Sport operational form        grand-sport   6                       FALSE          TRUE    Phase 7 parity row matching existing GRAND_SPORT_MODEL.
```

Notes:

- `registry_key` should match current runtime registry behavior:
  - Stingray: `stingray`
  - Grand Sport: `grandSport`
- If existing generated data derives `registry_key` through `registry_model_key(model_key)`, the implementation should validate the workbook value matches the derived key during this phase rather than changing registry behavior.
- `default_model` is metadata only in this pass unless a current code path already consumes it. Do not change model switch default behavior in Phase 7.

### 3.2 `model_workbook_sources`

Add active source rows for the sheet roles that are currently part of `ModelConfig` and materially affect generation.

Minimum required rows:

```text
model_key    source_role                       sheet_name                         active  notes
stingray     source_option_sheet               stingray_options                   TRUE    Matches current STINGRAY_MODEL.source_option_sheet.
stingray     status_sheet                      stingray_ovs                       TRUE    Matches current STINGRAY_MODEL.status_sheet.
stingray     rule_mapping_sheet                rule_mapping                       TRUE    Matches current default rule mapping sheet.
stingray     price_rules_sheet                 price_rules                        TRUE    Matches current default price rules sheet.
stingray     rule_groups_sheet                 rule_groups                        TRUE    Matches current default rule groups sheet.
stingray     rule_group_members_sheet          rule_group_members                 TRUE    Matches current default rule group members sheet.
stingray     exclusive_groups_sheet            exclusive_groups                   TRUE    Matches current default exclusive groups sheet.
stingray     exclusive_group_members_sheet     exclusive_group_members            TRUE    Matches current default exclusive group members sheet.
stingray     color_overrides_sheet             color_overrides                    TRUE    Matches current default color overrides sheet.

grand_sport  source_option_sheet               grandSport_options                 TRUE    Matches current GRAND_SPORT_MODEL.source_option_sheet.
grand_sport  status_sheet                      grandSport_ovs                     TRUE    Matches current GRAND_SPORT_MODEL.status_sheet.
grand_sport  rule_mapping_sheet                grandSport_rule_mapping            TRUE    Matches current GRAND_SPORT_MODEL.rule_mapping_sheet.
grand_sport  price_rules_sheet                 grandSport_price_rules             TRUE    Matches current GRAND_SPORT_MODEL.price_rules_sheet.
grand_sport  rule_groups_sheet                 grandSport_rule_groups             TRUE    Matches current GRAND_SPORT_MODEL.rule_groups_sheet.
grand_sport  rule_group_members_sheet          grandSport_rule_group_members      TRUE    Matches current GRAND_SPORT_MODEL.rule_group_members_sheet.
grand_sport  exclusive_groups_sheet            grandSport_exclusive_groups        TRUE    Matches current GRAND_SPORT_MODEL.exclusive_groups_sheet.
grand_sport  exclusive_group_members_sheet     grandSport_exclusive_members       TRUE    Matches current GRAND_SPORT_MODEL.exclusive_group_members_sheet.
grand_sport  color_overrides_sheet             color_overrides                    TRUE    Matches current shared color overrides sheet.
grand_sport  variant_option_overrides_sheet    grandSport_variant_overrides       TRUE    Matches current GRAND_SPORT_MODEL.variant_option_overrides_sheet.
```

Implementation may include additional non-critical source roles only if they map directly to existing `ModelConfig` fields and do not alter behavior. Keep this pass focused on model/source/variant ownership, not presentation, runtime rules, or audit parser constants.

### 3.3 `model_variants`

Add one active row per configured active model variant, preserving current config order.

Stingray rows:

```text
model_key  variant_id  display_order  active  notes
stingray   1lt_c07     1              TRUE    Matches current STINGRAY_MODEL.variant_ids.
stingray   2lt_c07     2              TRUE    Matches current STINGRAY_MODEL.variant_ids.
stingray   3lt_c07     3              TRUE    Matches current STINGRAY_MODEL.variant_ids.
stingray   1lt_c67     4              TRUE    Matches current STINGRAY_MODEL.variant_ids.
stingray   2lt_c67     5              TRUE    Matches current STINGRAY_MODEL.variant_ids.
stingray   3lt_c67     6              TRUE    Matches current STINGRAY_MODEL.variant_ids.
```

Grand Sport rows:

```text
model_key    variant_id  display_order  active  notes
grand_sport  1lt_e07     1              TRUE    Matches current GRAND_SPORT_MODEL.variant_ids.
grand_sport  2lt_e07     2              TRUE    Matches current GRAND_SPORT_MODEL.variant_ids.
grand_sport  3lt_e07     3              TRUE    Matches current GRAND_SPORT_MODEL.variant_ids.
grand_sport  1lt_e67     4              TRUE    Matches current GRAND_SPORT_MODEL.variant_ids.
grand_sport  2lt_e67     5              TRUE    Matches current GRAND_SPORT_MODEL.variant_ids.
grand_sport  3lt_e67     6              TRUE    Matches current GRAND_SPORT_MODEL.variant_ids.
```

Important: Grand Sport rows in `variant_master` were observed with `active=False` during inspection, while current Grand Sport generation still uses the configured Grand Sport variants. Phase 7 should preserve current generator behavior and not reinterpret `variant_master.active` as the source of Grand Sport runtime activation. Any cleanup of `variant_master.active` semantics is out of scope unless separately approved.

## 4. Exact files to change

Expected implementation files:

1. `scripts/corvette_form_generator/model_config.py`
   - Add `with_overrides()` method using `dataclasses.replace`.
   - Keep dataclass frozen.

2. `scripts/corvette_form_generator/runtime_metadata.py`
   - Either extend existing `load_model_metadata()` or add `load_model_config_overrides(wb, config)`.
   - Preferred: add `load_model_config_overrides()` returning a `ModelConfig` instance.
   - Keep `load_model_metadata()` available for tests/reporting if currently used.
   - Validate duplicate active rows and unknown source roles.

3. `scripts/generate_stingray_form.py`
   - Resolve `MODEL_CONFIG` after workbook load before reading source sheets and runtime metadata.
   - Avoid module-level stale copies of config fields where possible for fields that can now be workbook-overridden.
   - If keeping module-level constants for compatibility, ensure any workbook-overridden fields used in generation come from the resolved config, not stale globals.
   - Preserve registry merge behavior for Grand Sport draft data.

4. `scripts/generate_grand_sport_form.py`
   - Load workbook first, resolve `GRAND_SPORT_MODEL` through workbook overrides, and pass the resolved config to inspection/draft generation.

5. `scripts/migrations/...` or a new targeted migration script
   - Add/backfill rows in `model_master`, `model_workbook_sources`, and `model_variants` idempotently.
   - Must use `save_workbook_safely()`.
   - Must refuse to write if `~$stingray_master.xlsx` exists.
   - Must preserve any existing rows and update/insert only the Phase 7 keys.

6. Tests:
   - Prefer adding a focused unit test file, for example `tests/model-config-metadata.test.mjs` only if testing through Node wrappers is already practical, otherwise add Python tests if the repo has Python test infrastructure.
   - If no Python test runner is established, add targeted assertions into existing Node/generator tests or add a small Python validation script invoked by existing gates.
   - Existing full gates must still run.

Potential implementation files depending on current structure:

- `scripts/corvette_form_generator/inspection.py`
  - No direct changes should be needed if `generate_grand_sport_form.py` passes a resolved `ModelConfig`.
- `scripts/migrations/add_workbook_metadata_sheets.py`
  - Only touch if reusing the existing migration for idempotent backfill is cleaner. Prefer a new Phase 7 backfill script to keep history scoped.

Generated artifacts expected to change only after regeneration, and ideally with no contract drift:

- `stingray_master.xlsx`
- generated `form_*` sheets in `stingray_master.xlsx` after generator runs
- `form-output/stingray-form-data.json`
- `form-output/stingray-form-data.csv`
- `form-app/data.js`
- `form-output/inspection/grand-sport-*.json|md` after Grand Sport generator runs

If generated artifact diffs appear, they must be reviewed and explained as either timestamp-only or an unintended drift to fix before handoff.

## 5. Proposed implementation details

### 5.1 Add `ModelConfig.with_overrides()`

In `scripts/corvette_form_generator/model_config.py`:

```python
from dataclasses import dataclass, field, replace

@dataclass(frozen=True)
class ModelConfig:
    ...

    def with_overrides(self, **changes: Any) -> "ModelConfig":
        clean_changes = {key: value for key, value in changes.items() if value is not None}
        return replace(self, **clean_changes)
```

Implementation must not silently accept unknown field names beyond normal `replace()` behavior. If an unknown field is supplied, let it fail during development/tests.

### 5.2 Add safe workbook override loader

In `runtime_metadata.py`, add a typed helper similar to:

```python
def load_model_config_overrides(wb: Any, config: ModelConfig) -> ModelConfig:
    metadata = load_model_metadata(wb, config.model_key)
    model = metadata["model"]
    sources = {row["source_role"]: row["sheet_name"] for row in metadata["workbook_sources"]}
    variants = tuple(row["variant_id"] for row in metadata["variants"])

    allowed_source_roles = {
        "source_option_sheet",
        "status_sheet",
        "rule_mapping_sheet",
        "price_rules_sheet",
        "rule_groups_sheet",
        "rule_group_members_sheet",
        "exclusive_groups_sheet",
        "exclusive_group_members_sheet",
        "color_overrides_sheet",
        "variant_option_overrides_sheet",
    }
    unknown = sorted(set(sources) - allowed_source_roles)
    if unknown:
        raise ValueError(f"Unknown model_workbook_sources roles for {config.model_key}: {', '.join(unknown)}")

    expected_variant_count = model.get("expected_variant_count") or config.expected_variant_count
    resolved_variants = variants or config.variant_ids
    if expected_variant_count and len(resolved_variants) != expected_variant_count:
        raise ValueError(
            f"Model {config.model_key} expected {expected_variant_count} variants; "
            f"found {len(resolved_variants)} active model_variants rows."
        )

    return config.with_overrides(
        model_label=model.get("model_label") or config.model_label,
        model_year=model.get("model_year") or config.model_year,
        dataset_name=model.get("dataset_name") or config.dataset_name,
        source_option_sheet=sources.get("source_option_sheet") or config.source_option_sheet,
        status_sheet=sources.get("status_sheet") or config.status_sheet,
        variant_ids=resolved_variants,
        expected_variant_count=expected_variant_count,
        rule_mapping_sheet=sources.get("rule_mapping_sheet") or config.rule_mapping_sheet,
        price_rules_sheet=sources.get("price_rules_sheet") or config.price_rules_sheet,
        rule_groups_sheet=sources.get("rule_groups_sheet") or config.rule_groups_sheet,
        rule_group_members_sheet=sources.get("rule_group_members_sheet") or config.rule_group_members_sheet,
        exclusive_groups_sheet=sources.get("exclusive_groups_sheet") or config.exclusive_groups_sheet,
        exclusive_group_members_sheet=sources.get("exclusive_group_members_sheet") or config.exclusive_group_members_sheet,
        color_overrides_sheet=sources.get("color_overrides_sheet") or config.color_overrides_sheet,
        variant_option_overrides_sheet=sources.get("variant_option_overrides_sheet") or config.variant_option_overrides_sheet,
    )
```

Validation behavior for this phase:

- If all three model metadata sheets are empty, fall back to current constants.
- If rows exist for a model but are incomplete, use constants for omitted fields.
- If rows specify unknown source roles, fail fast.
- If active `model_variants` count does not match `expected_variant_count`, fail fast.
- If duplicate active `source_role` rows exist for one model, fail fast.
- If duplicate active `variant_id` rows exist for one model, fail fast.
- If `model_master.registry_key` is present and disagrees with current `registry_model_key(config.model_key)`, fail fast in this phase rather than changing runtime registry keys.
- Do not use workbook `registry_key` to change `form-app/data.js` registry naming until a later explicit runtime-contract pass.

### 5.3 Wire Stingray generation

In `scripts/generate_stingray_form.py`:

- Import `load_model_config_overrides`.
- After loading the workbook, resolve a local `model_config`:

```python
model_config = load_model_config_overrides(wb, STINGRAY_MODEL)
```

- Use `model_config` for reads currently dependent on `MODEL_CONFIG`:
  - source option sheet
  - status sheet
  - rule/price/group/exclusive/color source sheets
  - variant IDs
  - expected variant count
  - model label/year/dataset name
  - runtime metadata loads keyed by `model_key`
- Avoid broad refactoring. This is a targeted config-source replacement, not a generator architecture rewrite.

If the current script’s module-level `MODEL_CONFIG`, `ROOT`, `WORKBOOK_PATH`, `OUTPUT_DIR`, `APP_DIR`, and similar constants make a full local rename risky, keep path constants as-is and only route model metadata reads through the resolved `model_config`.

### 5.4 Wire Grand Sport generation

In `scripts/generate_grand_sport_form.py`:

- Load workbook.
- Resolve:

```python
config = load_model_config_overrides(wb, GRAND_SPORT_MODEL)
```

- Pass resolved `config` into existing inspection/draft generation.
- Preserve the intentional non-mutating behavior for `form-app/data.js` from this script.

### 5.5 Idempotent workbook backfill script

Create something like:

```text
scripts/migrations/backfill_model_config_metadata.py
```

Requirements:

- Use `.venv/bin/python` with `PYTHONPATH=scripts` if needed.
- Check for `~$stingray_master.xlsx` and stop if present.
- Load workbook and record `loaded_mtime_ns`.
- Insert/update rows by stable keys:
  - `model_master`: `model_key`
  - `model_workbook_sources`: `(model_key, source_role)`
  - `model_variants`: `(model_key, variant_id)`
- Preserve unknown existing rows.
- Use `save_workbook_safely()`.
- After save, reopen or inspect on disk to verify row counts/keys before reporting success.

## 6. Constraints

- Visual preservation: no UI layout, styling, copy, or step presentation changes in Phase 7.
- No runtime behavior change: no changes to option availability, defaults, price calculations, selected/auto-added RPOs, exports, or dealer payloads.
- No dealer submission changes: do not change endpoint, payload shape, Turnstile behavior, or submission modal behavior.
- No new dependencies.
- No broad refactor: keep changes narrowly scoped to model metadata ownership and validation.
- Workbook source-of-truth: model/source/variant metadata should be workbook-authored once backfilled; Python constants remain fallback only.
- Do not edit generated `form_*` workbook sheets by hand.
- Do not write workbook while Excel lock file `~$stingray_master.xlsx` exists.
- Do not hide bad workbook rows in generator logic. Validate/fail for duplicate/unknown/inconsistent model metadata.
- Do not use `variant_master.active` to change Grand Sport active variants in this pass.
- Do not change Grand Sport artifact naming or production promotion behavior.
- Do not stage `.DS_Store`, workbook backups, temp files, or unrelated generated output.

## 7. Risks

1. Wrong sheet-role row could make a generator read the wrong workbook sheet.
   - Mitigation: backfill rows from current constants, validate role names, and run full generator/tests.

2. Variant row ordering drift could alter generated choices/context order or validation counts.
   - Mitigation: preserve current `variant_ids` order and compare generated contracts.

3. `registry_key` mismatch could change model registry names in `form-app/data.js`.
   - Mitigation: validate workbook registry key against current `registry_model_key()` and do not use it to change output in Phase 7.

4. Stale module-level constants in `generate_stingray_form.py` could make partial override behavior inconsistent.
   - Mitigation: audit all uses of `MODEL_CONFIG`, `STEP_ORDER`, `STEP_LABELS`, `CONTEXT_SECTIONS`, `SECTION_STEP_OVERRIDES`, `STANDARD_SECTIONS`, and sheet-name fields. Only model/source/variant fields should be routed through the resolved config in this phase.

5. Existing tests may not isolate workbook fallback behavior.
   - Mitigation: add focused tests or fixture-based assertions around `load_model_config_overrides()`.

6. Workbook write safety.
   - Mitigation: use `save_workbook_safely()`, stop on lock file, and verify saved rows on disk.

## 8. Non-goals

- Do not remove `STINGRAY_MODEL` or `GRAND_SPORT_MODEL` constants.
- Do not make workbook metadata the only source; constants remain fallback for one release.
- Do not change runtime model registry behavior or default model behavior.
- Do not change active dealer-submission behavior.
- Do not migrate audit parser constants. That is Phase 8.
- Do not alter step/section/presentation metadata. That was Phase 6.
- Do not alter runtime defaults/exceptions/pricing. Those were earlier phases.
- Do not update deployment artifacts beyond normal regeneration required for validation.

## 9. Validation plan

### 9.1 Pre-flight

```sh
cd /Users/seandm/Projects/27vette
git status --short
test ! -e './~$stingray_master.xlsx'
.venv/bin/python scripts/validate_workbook_package.py stingray_master.xlsx
```

### 9.2 Workbook backfill verification

After running the Phase 7 migration script:

```sh
PYTHONPATH=scripts .venv/bin/python scripts/migrations/backfill_model_config_metadata.py
.venv/bin/python scripts/validate_workbook_package.py stingray_master.xlsx
```

Then inspect saved workbook rows on disk with `openpyxl`:

- `model_master` has exactly one active row for `stingray` and one active row for `grand_sport`.
- `model_workbook_sources` has all required active source roles for both models.
- `model_variants` has exactly six active rows for `stingray` and six active rows for `grand_sport`, in the current config order.

### 9.3 Static checks

```sh
.venv/bin/python -m py_compile \
  scripts/corvette_form_generator/model_config.py \
  scripts/corvette_form_generator/runtime_metadata.py \
  scripts/generate_stingray_form.py \
  scripts/generate_grand_sport_form.py \
  scripts/migrations/backfill_model_config_metadata.py
```

If Python tests are added:

```sh
.venv/bin/python -m pytest <new-or-existing-python-test-path>
```

Only use this command if pytest is already configured/available in the project; do not add pytest as a new dependency for Phase 7.

### 9.4 Generator and app-data gates

```sh
.venv/bin/python scripts/generate_stingray_form.py
.venv/bin/python scripts/generate_grand_sport_form.py
node --test tests/stingray-form-regression.test.mjs
node --test tests/multi-model-runtime-switching.test.mjs
node --test tests/stingray-generator-stability.test.mjs
node --test tests/grand-sport-contract-preview.test.mjs
node --test tests/grand-sport-draft-data.test.mjs
node --test tests/grand-sport-rule-audit.test.mjs
```

### 9.5 Parity review

Review diffs carefully:

```sh
git diff -- \
  scripts/corvette_form_generator/model_config.py \
  scripts/corvette_form_generator/runtime_metadata.py \
  scripts/generate_stingray_form.py \
  scripts/generate_grand_sport_form.py \
  scripts/migrations/backfill_model_config_metadata.py \
  stingray_master.xlsx \
  form-output/stingray-form-data.json \
  form-output/stingray-form-data.csv \
  form-output/inspection \
  form-app/data.js \
  tests
```

Expected result:

- Workbook source rows added for model metadata.
- Code reads workbook metadata with fallback.
- Generated contracts should remain behaviorally equivalent.
- No runtime UI changes.
- No dealer payload changes.

If contract comparison tooling from Phase 9 already exists, also run it against before/after snapshots. If not, do not create broad comparison infrastructure in Phase 7 unless implementation drift makes it necessary.

## 10. Rollback plan

1. Code rollback:
   - Revert changes to `model_config.py`, `runtime_metadata.py`, generator entrypoints, tests, and migration script.
   - Existing constants restore old behavior.

2. Workbook rollback:
   - Restore the backup produced by `save_workbook_safely()`, or set Phase 7 rows in `model_master`, `model_workbook_sources`, and `model_variants` to `active=FALSE` and regenerate.

3. Generated artifact rollback:
   - Re-run the generator from the restored workbook/config, or restore prior generated artifacts if needed.

4. Deployment rollback if ever deployed:
   - Redeploy prior static `form-app` artifact. Phase 7 should not require deployment unless paired with regenerated app-data in a release.

## 11. Handoff requirements after implementation

The implementation handoff must report:

- What changed:
  - exact code files
  - exact workbook sheets/row counts
  - generated artifacts
  - behavior impact, ideally "no intended behavior change"
- What did not change:
  - runtime UI
  - selected/auto-added RPO logic
  - pricing
  - dealer endpoint/payload/Turnstile
  - generated schema unless explicitly verified equivalent
- Gate results:
  - workbook package validation
  - py_compile
  - generators
  - Node test suite listed above
  - any focused config-loader tests
- Manual verification still pending.
- Residual risks and follow-up work.

## 12. Approval boundary

This Phase 7 spec is ready for review. Do not implement until approved because it touches workbook source data, generator configuration paths, tests, and generated artifacts.

Recommended implementation pass after approval:

1. Add `with_overrides()` and workbook config loader validation.
2. Add idempotent workbook backfill script and populate Phase 7 rows.
3. Wire Stingray and Grand Sport generation to resolved configs.
4. Add focused tests/fallback assertions.
5. Run full gates and review generated diffs for parity.
