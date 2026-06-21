# Pass 5B — Role-Driven Schema Validator Cleanup Spec

Status: Implemented 2026-06-21.
Date: 2026-06-21
Recommended reasoning level for implementation agent: high.

## Goal

Make workbook schema validation derive active model source-sheet requirements and header parity from workbook metadata instead of legacy Stingray/Grand Sport seed constants.

This is the source-contract half of Pass 5. Current preflight confirms Pass 5A has landed: Grand Sport default editor reminders no longer include `node --test tests/grand-sport-rule-audit.test.mjs` in `scripts/corvette_form_generator/editor_ops.py`. Pass 5B must preserve or strengthen validation coverage while removing legacy assumptions that can hide missing workbook metadata.

## Diagnosis

### Root cause

The schema validator is partly metadata-driven but still seeded by static model assumptions:

- `scripts/corvette_form_generator/schema_validation.py:70` defines `LEGACY_MODEL_SOURCES` for Stingray and Grand Sport.
- `scripts/corvette_form_generator/schema_validation.py:130` defines static `HEADER_PAIRS` for Stingray/Grand Sport sheets.
- `scripts/corvette_form_generator/schema_validation.py:141` defines static `REQUIRED_SHEETS` including Stingray/Grand Sport source sheets.
- `scripts/corvette_form_generator/schema_validation.py:413` builds `metadata_source_graph()` from the legacy seed graph before reading `model_workbook_sources`.
- `scripts/corvette_form_generator/schema_validation.py:751` still runs static `HEADER_PAIRS` checks even though `source_role_header_drift` now checks all active source sheets by role.
- `scripts/corvette_form_generator/schema_validation.py:20` also has source-sheet entries in `BOOLEAN_COLUMNS`, `PRICE_COLUMNS`, and `RPO_COLUMNS` for Stingray/Grand Sport sheets. Those duplicate role-derived column validation and must either be removed/reduced to true globals or retained with an explicit compatibility reason.

This can make validation pass because Python knows about legacy Stingray/Grand Sport sheets, rather than because the workbook graph is complete and traceable.

### Current workbook evidence

Read-only workbook probe from this spec-writing pass found:

- Active models from `model_master`: `stingray`, `grand_sport`, `z06`.
- Active `model_workbook_sources` roles:
  - `stingray`: 10 roles; no `variant_option_overrides_sheet` role.
  - `grand_sport`: 11 roles including `variant_option_overrides_sheet`.
  - `z06`: 11 roles including `variant_option_overrides_sheet`.
- Active `model_registry_promotion` rows for all three models use:
  - `artifact_type=runtime_contract`
  - `form-output/runtime/<slug>-runtime-contract.json`

That means active model source-sheet validation can be driven from workbook rows without relying on Stingray/Grand Sport Python seeds.

### Current route evidence

`generate_form.py` now discovers active/generatable models from workbook metadata, but still routes models differently:

- `generate_form.py:30` imports `discover_generation_model_configs()`.
- `generate_form.py:33` still defines `PRODUCTION_MODEL_KEYS = {"stingray"}`.
- `generate_form.py:130-133` sends Stingray to `run_production()` and Grand Sport/Z06 to `run_draft()`.

Pass 5B should not change this route split; it only normalizes schema validation ownership.

### Risk level

Medium/high.

This pass can accidentally weaken validation if static constants are removed before equivalent metadata-driven checks exist. The dangerous part is not deleting constants; it is preserving every mandatory active-model validation currently enforced by `REQUIRED_SHEETS`, `HEADER_PAIRS`, and the legacy seed graph while making their source workbook-owned.

### Change type

Source-contract validation code + tests + spec closure. No workbook write and no generated/runtime artifact change intended.

## Validation contract to preserve

### Mandatory global sheets

The validator must still require these global/source-contract sheets by name because they are not model-specific source roles:

- `model_master`
- `model_workbook_sources`
- `model_variants`
- `model_registry_promotion`
- `variant_master`
- `section_master`
- `lt_interiors`
- `LZ_Interiors`
- `model_interior_scope`
- `interior_components`
- `PriceRef`

If implementation proves one of these is already validated by a narrower direct check, keep the same failure semantics and document the owner in the completed spec.

### Mandatory active-model source roles

For every active row in `model_master`, require active exact-match `model_workbook_sources` rows for the canonical generator-required roles in `scripts/corvette_form_generator/model_configs.py`:

```py
REQUIRED_GENERATION_SOURCE_ROLES
```

`variant_option_overrides_sheet` remains optional because it is listed in `OPTIONAL_GENERATION_SOURCE_ROLES` and Stingray currently has no active role for it.

The validator should import or otherwise share `REQUIRED_GENERATION_SOURCE_ROLES` and `OPTIONAL_GENERATION_SOURCE_ROLES` with generation discovery. If implementation deliberately does not import them, it must document why the validator/generator drift risk is still closed.

Each active source-role row must point to an existing workbook sheet. Missing role rows and missing sheets must be explicit schema errors tied to `model_workbook_sources`, not silently filled from Python constants.

### Header parity

For each role in `HEADER_MATCH_ROLES`, all active source sheets for that role must share identical nonblank headers. This role-driven check should replace the static `HEADER_PAIRS` enforcement.

The replacement must still catch current Stingray/Grand Sport/Z06 parity drift for:

- option source sheets
- OVS/status sheets
- rule mapping sheets
- price rules sheets
- rule group sheets
- rule group member sheets
- exclusive group sheets
- exclusive group member sheets
- interior source sheets

### Existing dynamic column validations

The existing role-driven column validations must continue to run from the workbook-derived source graph:

- boolean cell typing through `ROLE_BOOLEAN_COLUMNS`
- RPO text typing through `ROLE_RPO_COLUMNS`
- price typing through `ROLE_PRICE_COLUMNS`
- active option display-order uniqueness
- inactive/future scaffold option display-order uniqueness through inactive `model_workbook_sources` rows

`BOOLEAN_COLUMNS`, `PRICE_COLUMNS`, and `RPO_COLUMNS` should retain only true global/non-role sheets such as `model_registry_promotion`, `PriceRef`, and `interior_components`. Active model source-sheet validation should come from role-derived columns instead of hardcoded Stingray/Grand Sport sheet names.

### Inactive/future scaffold behavior

Inactive/future scaffold rows must not become mandatory active model sources.

The validator should continue to inspect inactive source option sheets only for explicitly scoped future-scaffold hygiene checks, such as `duplicate_future_scaffold_option_display_order`, without requiring inactive models to have a complete active role graph.

## Exact files to change

1. `scripts/corvette_form_generator/schema_validation.py`
   - Replace `metadata_source_graph()` legacy seeding with workbook-owned graph construction.
   - Import or otherwise share `REQUIRED_GENERATION_SOURCE_ROLES` / `OPTIONAL_GENERATION_SOURCE_ROLES` from `model_configs.py`.
   - Remove `LEGACY_MODEL_SOURCES` if no compatibility fallback remains.
   - Remove `HEADER_PAIRS` once equivalent role-driven tests prove coverage.
   - Replace static model source entries in `REQUIRED_SHEETS` with:
     - global required sheets; plus
     - active source sheets discovered from `model_workbook_sources`.
   - Reduce `BOOLEAN_COLUMNS`, `PRICE_COLUMNS`, and `RPO_COLUMNS` to true global/non-role sheets, or document any retained compatibility entries in this spec before handoff.
   - Add explicit errors for active models missing mandatory source roles.
   - Keep unknown/duplicate active `model_workbook_sources` role errors.
   - Keep missing active source-sheet errors.
   - Preserve inactive/future scaffold display-order checks.

2. `tests/test_schema_validation_metadata.py`
   - Update fixtures so tests pass because workbook metadata is present, not because legacy seeds fill missing rows.
   - Add RED/green tests for:
     - missing `model_workbook_sources` emits `missing_required_sheet` and does not fall back to legacy source seeds;
     - active model missing `source_option_sheet` emits an explicit missing-role error;
     - active model missing `status_sheet` emits an explicit missing-role error;
     - shared/all role rows do not satisfy active model exact-match required roles;
     - active model with all mandatory roles validates source sheets without `LEGACY_MODEL_SOURCES`;
     - role-driven header parity catches drift between any two active source sheets for the same role, including Z06-style metadata rows;
     - inactive scaffold model rows do not require a complete active role graph;
     - inactive source option sheets still participate in future-scaffold display-order checks when the sheet exists;
     - removing a legacy Stingray/Grand Sport source sheet from `model_workbook_sources` is an error even if the old hardcoded sheet name exists.

3. `docs/audit-cleanup/pass-5b-schema-validator-role-driven-spec.md`
   - Update this spec before final handoff.
   - Change status to `Implemented <date>`.
   - Record changed files, exact gates, whether any compatibility fallback remains, and any intentionally deferred stale route-map updates.

## Constraints and boundaries

- No workbook writes.
- No generated artifact updates.
- No runtime JavaScript/CSS/HTML edits.
- No model generation route changes.
- Do not touch `generate_form.py` or `PRODUCTION_MODEL_KEYS` in this pass.
- Do not change `model_workbook_sources` rows.
- Do not weaken `validate_workbook_schema.py` readiness coverage.
- Do not delete optional audit/report tooling.
- Do not fold Pass 6 runtime hardcode cleanup into this pass.
- Do not update `docs/Audit-route-map.md` unless explicitly scoped as a docs status refresh.

## TDD plan

1. RED
   - Add focused failing tests in `tests/test_schema_validation_metadata.py` for missing `model_workbook_sources`, missing active source roles, exact-match role semantics, and role-driven header parity without relying on legacy seeds.
   - Run:

```sh
.venv/bin/python -m pytest tests/test_schema_validation_metadata.py -q
```

   - Expected failures should show current legacy behavior masking missing metadata or current static checks not covering the new role-driven fixture.

2. GREEN
   - Refactor `schema_validation.py` to build the source graph from active `model_master` + `model_workbook_sources`.
   - Add explicit missing-role validation for active models.
   - Replace static header-pair checks with role-driven checks.
   - Re-run the focused tests.

3. Regression gates

```sh
.venv/bin/python scripts/validate_workbook_schema.py stingray_master.xlsx
.venv/bin/python -m pytest tests/test_schema_validation_metadata.py tests/test_model_config_metadata.py tests/test_registry_promotion_metadata.py -q
git diff --check
```

## Expected non-changes

- `form-app/data.js` should not change.
- `form-output/*` should not change.
- `stingray_master.xlsx` should not change.
- Runtime behavior should not change.
- Active model promotion should not change.

## Completion requirements

When implementing this spec, update this file before final handoff with:

- final status and date;
- changed files;
- focused RED failure evidence;
- final gate results;
- whether `LEGACY_MODEL_SOURCES`, `HEADER_PAIRS`, and source-sheet entries in `REQUIRED_SHEETS` were removed or retained with a documented compatibility reason;
- whether source-sheet entries in `BOOLEAN_COLUMNS`, `PRICE_COLUMNS`, and `RPO_COLUMNS` were removed/reduced to true globals or retained with a documented compatibility reason;
- any residual risk or follow-up.

## Completion evidence

Implemented 2026-06-21.

Changed files:

- `scripts/corvette_form_generator/schema_validation.py`
- `tests/test_schema_validation_metadata.py`
- `docs/audit-cleanup/pass-5b-schema-validator-role-driven-spec.md`

Implementation notes:

- `schema_validation.py` now imports `REQUIRED_GENERATION_SOURCE_ROLES` and `OPTIONAL_GENERATION_SOURCE_ROLES` from `model_configs.py` so schema validation and generation discovery share the canonical role lists.
- Removed `LEGACY_MODEL_SOURCES`; active source graphs are built from exact-match active `model_workbook_sources` rows for active `model_master` models.
- Removed `HEADER_PAIRS`; header parity is enforced by source role through `source_role_header_drift`.
- Reduced `REQUIRED_SHEETS` to global/source-contract sheets. Model source sheets are required through active `model_workbook_sources` rows.
- Reduced `BOOLEAN_COLUMNS`, `PRICE_COLUMNS`, and `RPO_COLUMNS` to true global/non-role sheets. Active model source-sheet cell typing is added through `ROLE_BOOLEAN_COLUMNS`, `ROLE_PRICE_COLUMNS`, and `ROLE_RPO_COLUMNS` over the workbook-derived source graph.
- Added `missing_model_source_role` errors for active models missing required exact-match roles.
- Shared/all source rows do not satisfy active model exact-match required generation roles.

RED evidence:

```sh
.venv/bin/python -m pytest tests/test_schema_validation_metadata.py -q
```

Failed before implementation with 5 expected failures covering:

- missing `model_workbook_sources` not reported as required;
- active model missing `source_option_sheet` not reported;
- active model missing `status_sheet` not reported;
- shared source rows satisfying/obscuring exact-match requirements;
- legacy Grand Sport seed fallback leaking into complete-source fixture expectations.

Final gates:

```sh
.venv/bin/python -m pytest tests/test_schema_validation_metadata.py -q
```

Result: `22 passed`.

```sh
.venv/bin/python scripts/validate_workbook_schema.py stingray_master.xlsx
```

Result: workbook schema valid with `issue_count: 0`.

```sh
.venv/bin/python -m pytest tests/test_schema_validation_metadata.py tests/test_model_config_metadata.py tests/test_registry_promotion_metadata.py -q
```

Result: `48 passed`.

```sh
git diff --check
```

Result: passed.

Residual follow-up:

- `docs/Audit-route-map.md` still needs a separate docs/status refresh for stale top-level evidence and completed Pass 5 state.
- This pass did not change the remaining internal generation route split: Stingray still uses `production.py`; Grand Sport/Z06 still use the inspection/draft route.

## Historical approval prompt

Approve Pass 5B implementation as scoped above?
