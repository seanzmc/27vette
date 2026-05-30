# Stingray Standard Selected Options Fix Spec

> Spec only. Do not implement in this pass. Define the source-data and validation changes needed to restore missing Stingray standard selected options (including `EFR`) to parity with Grand Sport where applicable.

## Goal

Fix Stingray default/standard selected options so the generated Stingray form includes all required standard selections that should be preselected for each Stingray variant/trim/body combination.

Primary reported gap:

- `EFR` is present/selected in comparable Grand Sport contexts but missing from Stingray standard selected options.

Success means this is resolved through workbook/source data and generator pipeline behavior, not hardcoded model-specific runtime patches.

## Constraints

- Workbook is source of truth; no hidden one-off business rules in runtime code.
- Keep Stingray and Grand Sport structurally consistent in sheet shape and generated contracts.
- Scope changes to Stingray standard selections only unless cross-model schema normalization is required.
- Do not regress existing Stingray rules, prices, exports, or section rendering.

## Diagnosis Scope

Perform a focused diff between Stingray and Grand Sport for standard/preselected option behavior:

1. Identify where Grand Sport marks `EFR` as standard/selected.
2. Trace Stingray workbook rows for equivalent section/category/RPO behavior.
3. Confirm where Stingray data drops `EFR`:
   - workbook source row status/active/selectable/display behavior,
   - normalization/contract preview transforms,
   - generated `interiors`/`choices`/`standard_equipment` output,
   - runtime preselection logic.
4. Enumerate any additional missing Stingray standard options discovered during this audit (not only `EFR`).

## Files To Inspect

- `stingray_master.xlsx` (read/update through existing workbook-safe scripts only)
- `scripts/generate_stingray_form.py`
- `scripts/corvette_form_generator/model_configs.py`
- `scripts/corvette_form_generator/*` modules that map workbook `status`/selection behavior into output
- `form-app/data.js` (generated output verification)
- `tests/stingray-form-regression.test.mjs`
- any existing Stingray/Grand Sport contract preview or audit artifacts under `form-output/inspection/`

## Proposed Fix Plan

### P0 — Reproduce and Pinpoint

- Add/extend a deterministic check that asserts whether `EFR` is standard-selected for each expected Stingray context.
- Capture current failing matrix by variant + trim + body style + relevant prerequisite options.

Deliverable:

- explicit failing table (contexts where `EFR` expected vs actual).

### P1 — Source Data Correction (Preferred)

- Correct Stingray workbook rows so `EFR` is represented with the correct standard-selection semantics (status, active/selectable/display behavior, placement, and any required include/require rule rows).
- If `EFR` is package-driven in some contexts and truly standard in others, encode that by workbook-authored rules rather than hardcoded conditional logic.

Deliverable:

- workbook row-level change set describing old values -> new values for affected Stingray rows.

### P1 — Generator/Normalizer Alignment (Only if Needed)

If workbook rows are correct but generated output still drops `EFR`:

- fix generic transformation logic so standard-selected behavior is preserved for both Stingray and Grand Sport.
- avoid Stingray-only special case code unless there is an explicit documented exception.

Deliverable:

- minimal code change in generator/normalization path with model-agnostic behavior.

### P2 — Regression Hardening

- Add regression assertions ensuring `EFR` remains standard-selected in all intended Stingray contexts.
- Add a cross-model guard: if Grand Sport and Stingray share the same standard-selection semantics for an RPO in equivalent contexts, generator output should remain consistent unless explicitly documented.

Deliverable:

- updated tests with clear failure messages naming variant/trim/body and missing RPO.

## Validation Plan

After implementation (future execution pass), run:

1. `.venv/bin/python scripts/generate_stingray_form.py`
2. `node --test tests/stingray-form-regression.test.mjs`
3. Any targeted tests added for standard-selection parity.

Manual verification checklist:

- Stingray UI opens with expected default selections and includes `EFR` where required.
- No unexpected auto-add/remove behavior occurs when toggling nearby options/packages.
- Grand Sport behavior is unchanged unless intentionally touched.

## Non-Goals

- No pricing refactor.
- No unrelated label/copy cleanup.
- No redesign of section ordering.
- No speculative fixes for unrelated Stingray/Grand Sport compatibility rules unless directly required for `EFR` standard-selection correctness.

## Open Questions

- Is `EFR` universally standard across all Stingray variants/trims, or context-specific?
- If context-specific, what are the exact gating conditions (trim, package, body style, interior dependency)?
- Are there other RPOs currently masked by the same root cause in Stingray standard-selected mapping?

## Acceptance Criteria

- `EFR` appears as standard-selected in every Stingray context defined by workbook rules.
- Any additional missing Stingray standard-selected options found in the same root cause are fixed in the same pass.
- Changes are source-data-first (workbook/rules), with generator updates only where necessary and model-generic.
- Stingray regression tests pass, and no Grand Sport regressions are introduced.
