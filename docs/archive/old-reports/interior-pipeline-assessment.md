# Interior Pipeline Assessment — Z06 Pricing Defect and Cross-Model Normalization

Date: 2026-06-10
Status: verified and corrected against the current `work/27vette-copy-2026-06-09` workspace.
Scope: diagnosis/spec for the Z06 3LZ R6X build-summary overcharge and a workspace-guideline-compliant normalization path. This file is a planning artifact only; it does not approve implementation.

2026-06-18 status note: the old CSV/reference fallback surfaces described below are historical. Current active generation no longer reads `interior_reference_path`; `ModelConfig.interior_reference_path`, the `base_model_config()` CSV assignment, and `architectureAudit/stingray_interiors_refactor.csv` / `architectureAudit/grand_sport_interiors_refactor.csv` were retired in `docs/interior-stale-surface-cleanup-spec.md`. Use current code/tests over the stale 2026-06-10 line references in this assessment.

## 1. Reported Symptom

Z06, 3LZ, AH2 seat, custom interior `3LZ_R6X_AH2_HUU`:

- Current generated registry data contains the target interior at `price: 995` with an `R6X` component at `price: 995`.
- Current runtime build-summary math still renders two interior lines:
  - `HUU Adrenaline Red interior / Jet Black seats $700`
  - `R6X Custom Interior Trim and Seat Combination $995`
- The selected-options total is therefore $1,695. The intended total for this selected interior setup is $995.

Verified with a read-only Node runtime probe against `form-app/data.js` and `form-app/app.js` in this workspace.

## 2. Current Interior Pipeline Evidence

### 2.1 Production/Stingray path

Current production generation is not `scripts/generate_stingray_form.py`; that file is absent in this workspace. The active production path is `scripts/corvette_form_generator/production.py`, invoked through `scripts/generate_form.py --model stingray`.

`production.py` still has its own interior-building loop rather than calling the shared `build_model_interiors()` function, but it now imports shared helpers from `scripts/corvette_form_generator/interiors.py` and `scripts/corvette_form_generator/pricing.py`:

- reads `MODEL_CONFIG.interior_source_sheet` (`lt_interiors` for Stingray) at `production.py:204`
- reads `PriceRef` at `production.py:205-207`
- loads workbook-authored `interior_components` at `production.py:233`
- reads `MODEL_CONFIG.interior_reference_path` at `production.py:237`
- emits generated `interior_components_json` and grouping fields at `production.py:451-532`

Stingray grouping is still sourced from `architectureAudit/stingray_interiors_refactor.csv` through `MODEL_CONFIG.interior_reference_path`, so curated hierarchy/display data still lives outside the workbook.

### 2.2 Shared Grand Sport/Z06 preview path

Grand Sport and Z06 use `scripts/corvette_form_generator/inspection.py`, which calls `build_model_interiors(config)` from `scripts/corvette_form_generator/interiors.py`.

Verified symbols:

- `inspection.py:21` imports `build_model_interiors`
- `inspection.py:952` calls `build_model_interiors(config)`
- `interiors.py:266` defines `build_model_interiors(config)`
- `interiors.py:286` reads `config.interior_reference_path`

Current model configs use `ROOT / "architectureAudit" / f"{model_key}_interiors_refactor.csv"` for the shared path. The repo currently has:

- `architectureAudit/stingray_interiors_refactor.csv`
- `architectureAudit/grand_sport_interiors_refactor.csv`

There is no `architectureAudit/z06_interiors_refactor.csv`.

### 2.3 Workbook source surfaces

Read-only workbook inspection verified these current sheets and counts:

- `model_interior_scope`: 442 rows total; 132 `grand_sport`, 130 `z06`, 90 `zr1`, 90 `zr1x`; no `stingray` rows.
- `model_interior_scope` headers: `model_key`, `interior_id`, `trim_level`, `active`, `requires_option_id`, `notes`.
- `interior_components`: 846 rows.
- `interior_components` headers: `model_key`, `interior_id`, `rpo`, `component_type`, `label`, `price_ref_type`, `price_ref_code`, `price_trim_scope`, `display_order`, `active`, `notes`.
- `LZ_Interiors`: 130 rows.
- `lt_interiors`: 132 rows.
- `PriceRef`: 21 rows.

For `3LZ_R6X_AH2_HUU`, `LZ_Interiors` has:

- `Price = 0`
- `Trim = 3LZ_R6X`
- `Seat = AH2`
- `requires_r6x = True`
- `included_option_id = opt_r6x_001`

For the same interior, `interior_components` has an active Z06 row:

- `rpo = R6X`
- `component_type = r6x`
- `price_ref_type = r6x`
- `price_ref_code = R6X`
- `price_trim_scope = 3LZ_R6X`

`PriceRef` currently contains both:

- `OptionType = R6X`, blank trim, `Code = R6X`, `Price = 995`
- seat-keyed rows such as `Seat / 3LZ R6X / AH2 = 995` and `Seat / 3LZ R6X / AE4 = 1590`

## 3. Diagnosis

### 3.1 Root cause: runtime line-item math uses raw seat `base_price`, not the trim-scoped resolved seat price

The confirmed defect is in generic runtime math, not in the current Z06 `interior_components` price lookup.

`form-app/app.js` currently has two interior price notions:

- `adjustedInteriorPrice(interior)` at `app.js:677-680` subtracts `seat.base_price`.
- `adjustedInteriorDisplayPrice(interior)` at `app.js:682-685` subtracts `optionPrice(seat.option_id)`, which respects runtime price rules.

`lineItemsFromInterior(interior, autoAdded)` at `app.js:1150-1161` computes:

```text
replacedSeatPrice = selectedInteriorReplacesSeat(interior) ? Number(seat?.base_price || 0) : 0
componentBaseTotal = sum(component.price)
identityPrice = max(0, replacedSeatPrice + adjustedInteriorPrice(interior) - componentBaseTotal)
```

For Z06 3LZ AH2 + `3LZ_R6X_AH2_HUU`, the generated data has:

- selected AH2 choice raw `base_price = 1695`
- 3LZ AH2 price rule in `z06_price_rules`: `z06_pr_3lz_ah2_seat_001`, override to `0`
- selected interior `price = 995`
- R6X component `price = 995`

The runtime uses the raw `1695` twice and never applies the seat override in this identity split:

```text
identityPrice = max(0, 1695 + max(0, 995 - 1695) - 995) = 700
```

That exactly matches the observed $700 interior identity line and $1,695 total.

### 3.2 Corrected finding: current Z06 R6X component pricing is not missing

The previous draft incorrectly said Z06 `interior_components` rows have wrong price-ref keys and miss `PriceRef`.

Current workspace evidence says otherwise:

- `interior_components.price_ref_type = r6x`, `price_ref_code = R6X` is compatible with `PriceRef` row `OptionType = R6X`, blank trim, `Code = R6X`, `Price = 995`.
- `scripts/corvette_form_generator/pricing.py:47-58` falls back from the scoped key to `(normalized_type, "", normalized_code)`, so `price_trim_scope = 3LZ_R6X` still resolves to the blank-trim R6X row.
- Current `form-app/data.js` already emits `3LZ_R6X_AH2_HUU` with an `R6X` component at `995`.

Do not change Z06 R6X component rows to seat-keyed lookups as part of this fix. In this workspace, the durable contract is: R6X is a flat $995 interior component resolved by `PriceRef` `OptionType = R6X`, while seat-keyed `3LT/3LZ R6X` rows are delta inputs for interior totals.

### 3.3 Missing Z06 hierarchy reference still matters, but it is not the $700 cause

`read_interior_reference(reference_path)` in `interiors.py:143-169` returns empty data when the configured CSV is absent. Because `architectureAudit/z06_interiors_refactor.csv` does not exist, Z06 falls back to `grouping_fields_for_interior(..., reference=None)`.

Current tests already assert some Z06 grouping behavior (`tests/z06-form-data-draft.test.mjs`, "Z06 interiors group by customer-facing color family instead of interior code"), but the underlying grouping remains heuristic/generated from code rather than workbook-authored hierarchy metadata.

This is a source-of-truth and validation gap, not the direct pricing defect.

### 3.4 Curated interior hierarchy and labels remain outside the workbook

The active workbook owns interior availability and component membership through `model_interior_scope`, `lt_interiors`, `LZ_Interiors`, and `interior_components`, but hierarchy/display metadata still comes from CSVs or code fallbacks:

- `architectureAudit/stingray_interiors_refactor.csv`
- `architectureAudit/grand_sport_interiors_refactor.csv`
- absent Z06 CSV, causing fallback behavior
- hardcoded labels and heuristics in `interiors.py`, including `INTERIOR_COMPONENT_LABELS`, token parsing, and `broad_interior_color_family()`

This conflicts with the project rule that workbook-representable business data should live in the workbook.

## 4. What Is Already Working

Verified current gates:

```sh
node --test tests/z06-interior-accessory-cleanup.test.mjs tests/z06-form-data-draft.test.mjs
```

Result: 22 tests passed.

This means existing Z06 draft/interior/accessory tests are green, but they do not currently fail on the reported `3LZ_R6X_AH2_HUU` build-summary overcharge. Add a focused RED test before implementation.

Current generated Z06 data is otherwise consistent with this specific diagnosis:

- `3LZ_R6X_AH2_HUU.price = 995`
- `3LZ_R6X_AH2_HUU.interior_components[0].price = 995`
- AH2 raw choice rows remain `base_price = 1695` across Z06 trims
- `z06_price_rules` owns the 3LZ AH2 override to `0`

## 5. Workspace-Guideline-Compliant Proposal

Principle: keep business facts in workbook rows; keep generators boring; make runtime render/evaluate the generated contract without re-deriving product pricing from stale raw seat prices.

### Pass 1 — narrow defect fix: make interior line-item splitting use resolved seat price

Change type: runtime + tests only. No workbook write.

Exact files to change:

- `form-app/app.js`
- a focused Node runtime test, most likely in `tests/z06-interior-accessory-cleanup.test.mjs` or `tests/multi-model-runtime-switching.test.mjs`

Required behavior:

- Add a RED assertion for Z06 3LZ coupe, AH2, selected interior `3LZ_R6X_AH2_HUU`:
  - build summary must not include a `$700` HUU identity charge
  - R6X component line remains `$995`
  - selected-options total for this interior/seat portion remains `$995`, not `$1,695`
- Update generic interior line-item math to use the resolved seat price where the selected seat has trim/body-scoped price rules.
- Do not add Z06/R6X/AH2 hardcoded branches.
- Do not change dealer submission endpoint, payload shape, Turnstile behavior, or visual styling.
- Do not alter generated workbook sheets or `stingray_master.xlsx` in this pass.

Likely implementation direction:

- Replace raw `Number(seat?.base_price || 0)` use inside `lineItemsFromInterior()` with the already available `optionPrice(seat.option_id)` resolved value, or route through one generic helper so `adjustedInteriorPrice()` and `lineItemsFromInterior()` cannot diverge.
- Preserve current Stingray and Grand Sport behavior by running multi-model runtime tests.

Validation:

```sh
node --test tests/z06-interior-accessory-cleanup.test.mjs
node --test tests/multi-model-runtime-switching.test.mjs
node --test tests/stingray-form-regression.test.mjs
```

### Pass 2 — source-of-truth normalization for interior grouping metadata

Change type: workbook schema/data + generator + tests. Requires spec approval before edits.

Do not bundle this with Pass 1 unless explicitly approved.

Candidate workbook owner:

- Prefer extending existing `model_interior_scope` only if inspection proves it is the right canonical owner for model-specific interior presentation metadata.
- Current `model_interior_scope` already owns model/interior/trim activity and requirements. It does not currently have grouping columns, so adding `color_family`, `material_family`, `leaf_label`, `seat_label`, `display_order`, or `replaces_seat` is a schema extension and must be explicitly approved.
- If another existing workbook metadata sheet already owns presentation fields by the time this pass starts, use that existing owner instead of adding duplicate columns.

Exact files/sheets likely involved:

- `stingray_master.xlsx`
  - `model_interior_scope` or another approved workbook-owned interior presentation metadata sheet
  - potentially `interior_components` only for labels/order if current rows are incomplete
- `scripts/corvette_form_generator/interiors.py`
- `scripts/corvette_form_generator/production.py`
- `scripts/corvette_form_generator/model_configs.py`
- schema/metadata loaders and tests as needed
- generated artifacts after approval/regeneration

Required behavior:

- Migrate Stingray and Grand Sport hierarchy/display metadata from the two existing CSVs into workbook-owned rows.
- Author/review Z06 hierarchy/display metadata in workbook rows rather than relying on missing-CSV fallback heuristics.
- Add validation that active interiors missing required grouping metadata fail loudly or at least emit a blocking validation error during the approved transition.
- Retire CSV consumption only after parity is proven.

Validation:

```sh
.venv/bin/python scripts/validate_workbook_schema.py stingray_master.xlsx
.venv/bin/python scripts/generate_form.py --model stingray
.venv/bin/python scripts/generate_form.py --model grand_sport
.venv/bin/python scripts/generate_form.py --model z06
node --test tests/stingray-generator-stability.test.mjs
node --test tests/grand-sport-draft-data.test.mjs
node --test tests/z06-form-data-draft.test.mjs
node --test tests/multi-model-runtime-switching.test.mjs
```

Also snapshot and compare generated contracts before/after, using `scripts/compare-generated-contracts.mjs` where applicable, so timestamp-only churn is separated from substantive hierarchy changes.

### Pass 3 — unify the production and shared interior builders

Change type: generator refactor + parity tests. Requires separate approval after Pass 2 proves workbook-owned metadata.

Goal:

- Move Stingray production interiors from the bespoke loop in `production.py` onto the shared `build_model_interiors()` path or extract one shared helper used by both production and inspection paths.
- Preserve production contract parity for Stingray except for explicitly approved field additions.
- Do not change live dealer submission behavior.

Validation:

```sh
.venv/bin/python scripts/generate_form.py --model stingray
node --test tests/stingray-form-regression.test.mjs
node --test tests/stingray-generator-stability.test.mjs
node --test tests/multi-model-runtime-switching.test.mjs
```

### Pass 4 — delete transitional heuristics/fallbacks only after parity is proven

Change type: cleanup + validation hardening. Requires separate approval.

Targets:

- `INTERIOR_COMPONENT_LABELS` hardcodes that are now workbook-owned
- legacy token parsing used only as fallback
- silent missing CSV fallback
- color-family heuristics where workbook grouping metadata is complete

Non-goal: do not delete fallbacks while any active model still depends on them for generated parity.

## 6. Risks and Non-Goals

Risks:

- Runtime pricing changes can affect Stingray and Grand Sport interior line items if not covered by multi-model tests.
- Workbook schema extensions can create churn in generated artifacts and validators if not staged separately.
- Retiring CSVs before workbook parity would risk visible grouping/order regressions.
- Seat-keyed R6X PriceRef rows are easy to misinterpret; they are not the current component-pricing lookup for R6X and should not be deleted or repurposed without a separate pricing audit.

Non-goals for the immediate defect pass:

- no workbook write
- no generated `form_*` sheet edits
- no new dependencies
- no visual restyle
- no dealer submission endpoint/payload/Turnstile changes
- no ZR1/ZR1X promotion or runtime activation
- no broad generator unification in the same pass

## 7. Recommended Migration Order

1. Pass 1: fix the runtime identity split with a focused RED test for the reported Z06 3LZ R6X AH2 case.
2. Pass 2: migrate interior grouping/display metadata into workbook-owned rows and add loud validation for missing active metadata.
3. Pass 3: unify Stingray production and shared interior generation after workbook metadata parity is proven.
4. Pass 4: retire CSV and heuristic fallbacks after all active models are workbook-backed and contract diffs are reviewed.

This order fits `AGENTS.md`: it fixes the live/customer-facing defect in the smallest safe runtime pass, then handles workbook-source normalization as separately approved schema/data work.
