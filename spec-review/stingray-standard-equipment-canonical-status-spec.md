# Stingray Standard Equipment Canonical Status Spec

Spec only. Do not implement until approved.

## Goal

Make Stingray `standardEquipment` generation use `stingray_ovs.status=standard` as the source of truth, so canonical selectable rows can supply Standard & Included equipment without duplicate `sec_stan_002` mirror rows.

This is the required generator fix before retrying `stingray-duplicate-rpo-phase-1a-standard-mirrors-spec.md`.

## Diagnosis

Root cause: `scripts/generate_stingray_form.py` currently filters standard equipment too narrowly:

```python
if choice["status"] == "standard" and (choice["step_key"] == "standard_equipment" or choice["selectable"] != "True")
```

That means active canonical rows such as `opt_efr_001`, `opt_719_001`, `opt_cf7_001`, or `opt_qeb_001` can have `stingray_ovs.status=standard` but still be excluded from `standardEquipment` because they are selectable rows outside the `standard_equipment` step.

Phase 1A proved the dependency:

- Deactivating `sec_stan_002` mirror rows succeeded at the workbook level.
- `scripts/generate_stingray_form.py` completed with `validation_errors=0`.
- Generated `standardEquipment` dropped the affected RPOs instead of re-emitting them from canonical rows.
- The change was rolled back.

Grand Sport already uses the better model in `scripts/corvette_form_generator/inspection.py`: standard equipment is derived from choices where `choice["status"] == "standard"`, without requiring a standard-equipment section mirror.

Change type: generator behavior plus focused tests; no workbook source-data mutation in this pass.

Risk level: Medium. Broadening standard-equipment eligibility can create duplicate standard-equipment rows unless canonical/mirror conflicts are resolved deterministically.

## Exact Files To Change

- `scripts/generate_stingray_form.py`
- `tests/stingray-form-regression.test.mjs`
- `tests/stingray-generator-stability.test.mjs`
- Generated artifacts after approved implementation:
  - `stingray_master.xlsx` generated `form_*` sheets
  - `form-output/stingray-form-data.json`
  - `form-output/stingray-form-data.csv`
  - `form-app/data.js`

## Constraints

- Do not edit workbook source rows in this pass.
- Do not deactivate or delete duplicate option rows in this pass.
- Do not use `display_behavior=default_selected` as standard-equipment eligibility.
- Do not add Stingray-specific runtime JavaScript.
- Do not add new dependencies.
- Preserve current `standardEquipment` output before mirror rows are deactivated.
- Preserve Grand Sport behavior and source sheets.
- Keep `stingray_ovs.status=standard` as the source fact for included/standard equipment.

## Proposed Generator Behavior

### Source Semantics

Use these meanings:

- `status=standard`: the option is included for that variant and is eligible for `standardEquipment`.
- `selectable=TRUE`: the option can appear as a visible selectable/default tile.
- `display_behavior=default_selected`: runtime should start with the option selected where applicable.
- `section_id=sec_stan_002`: current duplicate mirror workaround, not the long-term standard-equipment source.

### Standard Equipment Builder

Replace the current inline list-comprehension filter with a small helper that:

1. Starts from active generated `choices` where `choice["status"] == "standard"`.
2. Deduplicates rows by a semantic key:
   - use `(variant_id, rpo)` when `rpo` is nonblank;
   - fall back to `(variant_id, option_id)` when `rpo` is blank.
3. Chooses the best representative when multiple rows share the semantic key.
4. Emits one `standardEquipment` row per semantic key.

### Representative Preference

When multiple rows have the same `(variant_id, rpo)`, prefer in this order:

1. Active canonical `_001` rows outside `sec_stan_002`.
2. Active non-`sec_stan_002` rows.
3. Active `sec_stan_002` mirror rows.
4. Existing row order as a deterministic final tie-breaker.

This makes generated output prefer canonical rows while mirror rows are still active, and it lets Phase 1A deactivate mirror rows later without losing Standard & Included entries.

### Copy / Field Preservation

For the first generator pass, preserve current customer-facing Standard & Included copy as much as practical.

Open point for implementation:

- If canonical row copy differs from mirror row copy for a duplicated RPO, compare generated diff before accepting the new representative. If the mirror row has customer-facing copy that canonical lacks, stop and decide whether to move copy into the canonical workbook row before mirror deactivation.

Do not paper over copy differences in JavaScript.

## Tests To Add Or Update

Add focused regression coverage proving:

1. Canonical selectable rows with `status=standard` are eligible for `standardEquipment`.

   Suggested assertions:

   - `opt_efr_001` appears in `standardEquipment` for all Stingray variants.
   - `opt_719_001` appears in `standardEquipment` for all Stingray variants.
   - `opt_cf7_001` appears in coupe `standardEquipment`.
   - `opt_cm9_001` appears in convertible `standardEquipment`.

2. Duplicate mirror rows do not create duplicate Standard & Included entries.

   Suggested assertion:

   - For each `(variant_id, rpo)` in `standardEquipment`, there is no duplicate row with the same nonblank RPO.

3. Existing mirror rows can remain active until Phase 1A.

   Suggested assertion:

   - `opt_fe1_002` can still exist as a generated standard-equipment choice until the FE1 cleanup pass, but `standardEquipment` should prefer the canonical row when both rows represent the same RPO and the canonical row is standard.

4. `default_selected` is not required.

   Suggested assertion:

   - A canonical standard row without `display_behavior=default_selected`, such as `opt_qeb_001` or `opt_j6a_001`, is still eligible for `standardEquipment`.

Update brittle count tests only if the semantic output is correct. Do not treat row-count churn as sufficient validation.

## Validation Plan

Run:

```sh
.venv/bin/python scripts/generate_stingray_form.py
node --test tests/stingray-form-regression.test.mjs
node --test tests/stingray-generator-stability.test.mjs
```

Then inspect:

```sh
git diff -- scripts/generate_stingray_form.py tests/stingray-form-regression.test.mjs tests/stingray-generator-stability.test.mjs
git diff -- form-output/stingray-form-data.json form-output/stingray-form-data.csv form-app/data.js
```

Focused generated-data checks:

- No duplicate nonblank `(variant_id, rpo)` rows in `standardEquipment`.
- Canonical rows are present for Phase 1A RPOs:
  - `opt_719_001`
  - `opt_cf7_001`
  - `opt_cm9_001`
  - `opt_efr_001`
  - `opt_eyt_001`
  - `opt_j6a_001`
  - `opt_nga_001`
  - `opt_qeb_001`
- `UQT` behavior remains unchanged.
- Seat/interior tests remain unchanged.

## Non-Goals

- Do not deactivate mirror rows in this pass.
- Do not touch `FE1`, `AE4`, `AH2`, `AQ9`, or `UQT` source rows.
- Do not change pricing.
- Do not change runtime selection/default behavior.
- Do not change Grand Sport generation.

## Follow-Up

After this generator pass is implemented and validated, retry a revised Phase 1A mirror deactivation pass. That pass should verify that deactivating the mirror rows creates no `standardEquipment` loss because canonical rows already own the emitted Standard & Included entries.
