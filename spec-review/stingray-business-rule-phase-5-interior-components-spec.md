# Phase 5 Spec — Interior Component Source Of Truth

## Status

Proposed. Do not implement until approved.

Phase 4 is assumed complete and green: Stingray UQT availability, hidden `sec_cust_002` behavior, and R6X included-option fallback are now workbook-owned or validation-owned. Phase 5 should start from that baseline and avoid reintroducing generator/runtime RPO-specific business rules.

## Diagnosis

Root cause: interior component decomposition is still inferred in Python from string tokens and hardcoded component labels instead of being authored as workbook data.

Current hardcoded paths to inspect before implementation:

- `scripts/generate_stingray_form.py`
  - `INTERIOR_COMPONENT_LABELS`
  - `interior_component_metadata(row, price_ref)`
  - `generated_interior_price(row, price_ref)`
  - `r6x_price_component(row, price_ref)`
  - Stingray interior generation loop over `lt_interiors` and `LZ_Interiors`
- `scripts/corvette_form_generator/inspection.py`
  - `INTERIOR_COMPONENT_LABELS`
  - `interior_component_metadata(row, price_ref)`
  - Grand Sport draft interior generation loop currently filtering `lt_interiors` by hardcoded trim set `{"1LT", "2LT", "3LT", "3LT_R6X"}`
- `scripts/corvette_form_generator/runtime_metadata.py`
  - Existing `load_model_interior_scope()` exists, but `interior_components` and `component_price_rules` readers are not yet sufficient/used for generated interior component output.
- `stingray_master.xlsx`
  - `interior_components` sheet exists but has no rows.
  - `model_interior_scope` sheet exists but has no rows.
  - `component_price_rules` sheet exists but has no rows.
  - `lt_interiors` and `LZ_Interiors` currently remain the source rows for generated interiors.
  - `PriceRef` currently remains the price lookup source for seat, stitching, suede, two-tone, and R6X component prices.

Business risk: medium-high.

Why this matters:

- Generated `interior_components` affect order line items, selected/auto-added RPO summaries, Markdown export, plain-text export, and dealer payload content.
- Hardcoded labels like `"Yellow Stitching"`, `"Sueded Microfiber"`, and `"Custom Interior Trim and Seat Combination"` can drift from workbook/customer-facing language.
- Token parsing from `interior_id` silently changes behavior if workbook IDs change.
- Grand Sport interior scope is still partially inferred from hardcoded trim names rather than model-scoped workbook rows.

Change type: mixed.

- Workbook data change: yes.
- Generator behavior change: yes, but intended output parity for current generated contracts.
- Runtime JavaScript change: no, unless validation proves runtime cannot consume the same generated shape.
- Styling change: no.
- Docs-only: no.

## Goal

Move interior component ownership into workbook-authored rows while preserving the current generated data contract and runtime behavior.

Successful Phase 5 outcome:

1. Active Stingray and Grand Sport component-bearing interiors have explicit workbook rows in `interior_components`.
2. Grand Sport live/draft interior inclusion is controlled by `model_interior_scope` or an equivalent workbook-authored model scope, not a hardcoded trim set.
3. Generator/inspection code reads workbook component rows first.
4. Legacy token parsing remains only as a temporary fallback for inactive/unpopulated rows during this phase, or is removed if full workbook coverage is proven.
5. Existing generated counts and behavior stay stable unless an approved workbook correction intentionally changes them.
6. Tests prove workbook ownership, not just output parity.

## Exact Files And Sheets To Change

Workbook:

- `stingray_master.xlsx`
  - `interior_components`
  - `model_interior_scope`
  - possibly `component_price_rules` if component-level conditional pricing is needed in this phase
  - `lt_interiors` only for data inspection or if an explicit source-data correction is discovered
  - `LZ_Interiors` only for data inspection or if an explicit source-data correction is discovered
  - `PriceRef` only for inspection; do not alter prices in this phase unless separately approved

Python:

- `scripts/corvette_form_generator/runtime_metadata.py`
  - Add or extend workbook readers for `interior_components` and model interior scope.
- `scripts/generate_stingray_form.py`
  - Replace Stingray component derivation with workbook-backed component resolution.
  - Keep generated interior object shape unchanged.
- `scripts/corvette_form_generator/inspection.py`
  - Replace Grand Sport draft component derivation with the same workbook-backed component resolution.
  - Replace hardcoded Grand Sport interior trim scope with workbook model scope if full scope rows are available.

Tests:

- `tests/stingray-form-regression.test.mjs`
  - Existing component-price/export tests must remain green.
- `tests/stingray-generator-stability.test.mjs`
  - Add workbook ownership tests for `interior_components` and generator no-hardcode checks.
- `tests/grand-sport-draft-data.test.mjs`
  - Add/adjust Grand Sport interior scope and component rows tests.
- `tests/multi-model-runtime-switching.test.mjs`
  - Keep Grand Sport export/interior behavior green.

Generated artifacts:

- `form-output/stingray-form-data.json`
- `form-output/stingray-form-data.csv`
- `form-app/data.js`
- `form-output/inspection/grand-sport-inspection.json`
- `form-output/inspection/grand-sport-inspection.md`
- `form-output/inspection/grand-sport-contract-preview.json`
- `form-output/inspection/grand-sport-contract-preview.md`
- `form-output/inspection/grand-sport-form-data-draft.json`
- `form-output/inspection/grand-sport-form-data-draft.md`
- `form-output/inspection/grand-sport-rule-audit.json`
- `form-output/inspection/grand-sport-rule-audit.md`

Only retain generated diffs that are required and reviewed. Revert timestamp-only Grand Sport inspection diffs unless the implementation intentionally updates them.

## Constraints

- Preserve current customer-facing runtime behavior unless an approved workbook row correction intentionally changes it.
- Preserve visual behavior and CSS; this phase is not a UI/styling pass.
- Preserve the generated data schema consumed by `form-app/app.js`:
  - `interior_components` remains an array of objects with at least `rpo`, `label`, `price`, and `component_type`.
  - `interior_components_json` remains populated consistently.
  - selected interior price behavior remains compatible with current runtime order/export helpers.
- No runtime refactor.
- No new dependencies.
- Do not add model/RPO-specific Python or JavaScript branches when a workbook row can express the business fact.
- Do not hide workbook data problems with script fallbacks once a sheet is declared source-of-truth for active rows.
- Do not edit generated `form_*` workbook sheets directly.
- Close Excel before any workbook-writing script.
- If `~$stingray_master.xlsx` exists, stop and confirm whether the file is stale before deleting or writing.
- Workbook writes must save through `save_workbook_safely()` and be verified on disk with `openpyxl` after save.
- Do not change dealer submission endpoint, payload shape, or Turnstile behavior.

## Proposed Workbook Contracts

### `interior_components`

Existing headers:

```text
model_key, interior_id, rpo, component_type, label, price_ref_type, price_ref_code, price_trim_scope, display_order, active, notes
```

Expected row semantics:

- `model_key`: `stingray`, `grand_sport`, or shared/global key only if truly model-neutral.
- `interior_id`: generated interior identity from `lt_interiors.interior_id` or `LZ_Interiors.ID`.
- `rpo`: component RPO emitted in order/export lines.
- `component_type`: one of current runtime-compatible values such as `seat`, `r6x`, `stitching`, `suede`, `two_tone`.
- `label`: customer-facing component label emitted into generated data.
- `price_ref_type`: lookup category used against `PriceRef` component pricing, such as `seat`, `stitching`, `suede`, `twotone`.
- `price_ref_code`: lookup code; default to `rpo` only when that is actually correct.
- `price_trim_scope`: optional override for trim-scoped lookup; if blank, use the source interior trim.
- `display_order`: stable component ordering inside an interior.
- `active`: workbook row activation.
- `notes`: source/review note.

### `model_interior_scope`

Existing headers:

```text
model_key, interior_id, trim_level, active, requires_option_id, notes
```

Expected row semantics:

- `model_key`: model that owns the scope row.
- `interior_id`: interior allowed for that model.
- `trim_level`: model trim emitted in generated data, normalized without `_R6X` unless an approved rule requires otherwise.
- `active`: whether this interior is available for that model output.
- `requires_option_id`: optional package/option implied by the interior, e.g. Grand Sport launch package rows that require/auto-add `opt_z25_001` if that remains the intended workbook relationship.
- `notes`: review/source evidence.

### `component_price_rules`

Do not use this sheet unless implementation discovers a component price condition that cannot be represented by `interior_components` plus `PriceRef`.

If used, it must be generic and model-scoped. It must not become an RPO-specific script substitute.

## Proposed Implementation Plan

### Step 1 — Preflight And Baseline

Run from repo root:

```sh
git status --short --branch
python3 - <<'PY'
from pathlib import Path
print('LOCK_PRESENT' if Path('~$stingray_master.xlsx').exists() else 'NO_LOCK')
PY
.venv/bin/python scripts/validate_workbook_package.py stingray_master.xlsx
.venv/bin/python scripts/generate_stingray_form.py
.venv/bin/python scripts/generate_grand_sport_form.py
node --test tests/stingray-form-regression.test.mjs
node --test tests/multi-model-runtime-switching.test.mjs
node --test tests/stingray-generator-stability.test.mjs
node --test tests/grand-sport-contract-preview.test.mjs
node --test tests/grand-sport-draft-data.test.mjs
node --test tests/grand-sport-rule-audit.test.mjs
```

Stop if the baseline is not green.

### Step 2 — Populate Workbook Rows

Create an idempotent workbook migration script or one-off Python script that:

1. Reads current generated component output from the existing code path or derives equivalent rows from `lt_interiors`, `LZ_Interiors`, and `PriceRef`.
2. Writes explicit `interior_components` rows for every current component-bearing active Stingray interior and Grand Sport draft interior.
3. Writes `model_interior_scope` rows for Grand Sport draft interiors currently included by the hardcoded trim set.
4. Optionally writes Stingray `model_interior_scope` rows only if needed by the generator design; do not duplicate `lt_interiors.active_for_stingray` unless the implementation explicitly promotes this sheet as the model scope source for Stingray too.
5. Saves through `save_workbook_safely()`.
6. Verifies on disk with `openpyxl`:
   - expected row counts;
   - no duplicate active `(model_key, interior_id, rpo, component_type)` rows;
   - no active component rows with blank `label`, `rpo`, or `component_type`;
   - every active component row resolves a price if its current generated counterpart has a non-zero price.

Important: workbook rows should reproduce current behavior. Do not use Phase 5 to correct prices/labels unless the correction is explicitly approved.

### Step 3 — Add Generic Metadata Readers

In `scripts/corvette_form_generator/runtime_metadata.py`, add reusable readers:

- `load_interior_components(wb, model_key)` returning active rows grouped by `interior_id` and sorted by `display_order`.
- `load_model_interior_scope_map(wb, model_key)` or extend `load_model_interior_scope()` to return a lookup keyed by `interior_id`.

Reader validation should detect and surface:

- duplicate active component rows for the same model/interior/RPO/component type;
- active component rows with missing required fields;
- model scope rows referencing unknown interiors if that can be checked at the caller layer.

### Step 4 — Use Workbook Components In Stingray Generator

In `scripts/generate_stingray_form.py`:

1. Load workbook component rows once near the other runtime metadata readers.
2. Replace direct `interior_component_metadata(row, interior_component_price_ref)` calls with `resolved_interior_components(row, model_key, price_ref)`.
3. For an active Stingray interior with workbook component rows, use only workbook rows.
4. For active Stingray interiors with no workbook component rows, either:
   - emit a validation error once full coverage is expected, or
   - temporarily fall back to `interior_component_metadata()` during implementation only.
5. Keep generated output shape unchanged.
6. Do not remove `PriceRef` pricing. Workbook component rows identify the component; `PriceRef` remains the price source unless separately approved.

### Step 5 — Use Workbook Components And Scope In Grand Sport Draft

In `scripts/corvette_form_generator/inspection.py`:

1. Use the same component reader/resolver for Grand Sport draft interiors.
2. Replace the hardcoded trim inclusion condition:

```py
if trim not in {"1LT", "2LT", "3LT", "3LT_R6X"}:
    continue
```

with workbook model scope if `model_interior_scope` has active Grand Sport rows.

3. Preserve current Grand Sport draft counts unless the workbook scope rows intentionally encode a different approved count.
4. Preserve EL9/Z25 behavior currently tested:
   - `3LT_AE4_EL9` and `3LT_AH2_EL9` remain available for Grand Sport.
   - `requires_z25` remains true for those rows if that is still encoded in source/detail/rules.
   - Grand Sport export still auto-adds `Z25` at `$0` from workbook rules.

### Step 6 — Remove Or Isolate Hardcoded Labels

After full active row coverage is verified:

- Remove `INTERIOR_COMPONENT_LABELS` as a required source for active generated rows, or leave it only in a clearly named legacy fallback path used by tests/fixtures.
- Add a stability test asserting active workbook rows, not `INTERIOR_COMPONENT_LABELS`, own labels for current active generated interiors.

Do not remove token parsing until tests prove full component coverage for all active rows that need components.

## Validation Plan

Targeted checks after workbook write:

```sh
.venv/bin/python scripts/validate_workbook_package.py stingray_master.xlsx
PYTHONPATH=scripts .venv/bin/python - <<'PY'
from openpyxl import load_workbook
from corvette_form_generator.workbook import rows_from_sheet, clean
wb = load_workbook('stingray_master.xlsx', read_only=True, data_only=True)
components = rows_from_sheet(wb, 'interior_components')
active = [r for r in components if clean(r.get('active')).lower() == 'true']
print('active_components', len(active))
print('blank_required', [r for r in active if not clean(r.get('interior_id')) or not clean(r.get('rpo')) or not clean(r.get('component_type')) or not clean(r.get('label'))][:5])
PY
```

Generator gates:

```sh
.venv/bin/python scripts/generate_stingray_form.py
.venv/bin/python scripts/generate_grand_sport_form.py
```

Tests:

```sh
node --test tests/stingray-form-regression.test.mjs
node --test tests/multi-model-runtime-switching.test.mjs
node --test tests/stingray-generator-stability.test.mjs
node --test tests/grand-sport-contract-preview.test.mjs
node --test tests/grand-sport-draft-data.test.mjs
node --test tests/grand-sport-rule-audit.test.mjs
```

Expected specific assertions:

- Existing Stingray component tests remain green:
  - generated interiors expose priced component metadata from `PriceRef`;
  - R6X component order output uses `PriceRef` pricing;
  - R6X keeps normal price when D30 is present;
  - selected/auto-added RPO summaries do not duplicate R6X.
- New/updated tests prove:
  - `interior_components` has active workbook rows for component-bearing generated interiors;
  - active component rows have no duplicate active keys;
  - generator source no longer requires `INTERIOR_COMPONENT_LABELS` for active generated rows;
  - Grand Sport draft interior scope is workbook-owned if `model_interior_scope` is populated;
  - generated Stingray and Grand Sport interior counts remain unchanged unless explicitly approved.

Diff review:

```sh
git status --short --branch
git diff --stat
git diff -- scripts/corvette_form_generator/runtime_metadata.py scripts/generate_stingray_form.py scripts/corvette_form_generator/inspection.py tests/stingray-generator-stability.test.mjs tests/stingray-form-regression.test.mjs tests/grand-sport-draft-data.test.mjs tests/multi-model-runtime-switching.test.mjs
```

Review generated data diffs for more than timestamp changes. If generated data changes beyond expected workbook-owned metadata fields, stop and explain before proceeding.

## Risks

- Component row explosion: every component-bearing interior may need one or more rows, making workbook review heavier.
- Partial coverage risk: if some active interiors still depend on token parsing, source-of-truth migration is incomplete.
- Price drift risk: workbook component rows identify components while `PriceRef` computes prices; mismatched `price_ref_type`, `price_ref_code`, or `price_trim_scope` can change output silently.
- Grand Sport scope risk: replacing trim-set filtering with `model_interior_scope` can accidentally add/remove draft interiors if rows are incomplete.
- Label drift risk: customer-facing labels may change if workbook rows do not match current hardcoded labels exactly.
- Generated artifact noise: Grand Sport inspection artifacts may change only timestamps; revert timestamp-only diffs unless required.

## Non-Goals

- Do not change runtime UI, layout, CSS, or visual behavior.
- Do not change dealer submission endpoint or payload contract.
- Do not change actual component prices or launch package prices unless separately approved.
- Do not migrate step/section/presentation metadata; that belongs to Phase 6.
- Do not migrate model registry/source configuration; that belongs to Phase 7.
- Do not refactor `form-app/app.js`.
- Do not delete `lt_interiors`, `LZ_Interiors`, or `PriceRef`.
- Do not edit generated `form_*` workbook sheets manually.

## Rollback Plan

If Phase 5 causes drift:

1. Revert Python/test changes.
2. Restore `stingray_master.xlsx` from the `save_workbook_safely()` backup created during the workbook write, or set new `interior_components` / `model_interior_scope` rows inactive if that is safer for review.
3. Regenerate Stingray data:

```sh
.venv/bin/python scripts/generate_stingray_form.py
```

4. Re-run targeted tests:

```sh
node --test tests/stingray-form-regression.test.mjs
node --test tests/stingray-generator-stability.test.mjs
```

5. Revert generated artifacts if needed.

## Approval Request

Approve Phase 5 only if the intended implementation is:

- workbook-populate first;
- parity-preserving;
- no new dependencies;
- no runtime visual changes;
- no dealer submission changes;
- no new hardcoded RPO/model-specific script branches;
- full validation gates before handoff.
