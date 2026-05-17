# Stingray Duplicate RPO Phase 1B FE1 Mirror Deactivation Spec

Approved and implemented on 2026-05-17.

## Diagnosis

Root cause: `FE1` still has an active `sec_stan_002` standard-equipment mirror row even though the canonical selectable suspension row already carries standard status for every Stingray variant.

Exact sheets/files inspected:

- `stingray_master.xlsx`
  - `stingray_options`
  - `stingray_ovs`
  - `rule_mapping`
  - `price_rules`
  - `exclusive_group_members`
- `form-app/app.js`
- `tests/stingray-form-regression.test.mjs`
- `form-output/stingray-form-data.json`
- `spec-review/stingray-duplicate-rpo-canonicalization-spec.md`
- `spec-review/stingray-duplicate-rpo-phase-1a-standard-mirrors-spec.md`
- `spec-review/stingray-standard-equipment-canonical-status-spec.md`

Evidence:

- `stingray_options` row `opt_fe1_001`:
  - `rpo=FE1`
  - `section_id=sec_susp_001`
  - `price=0`
  - `selectable=TRUE`
  - `active=TRUE`
  - `display_behavior` blank
- `stingray_options` row `opt_fe1_002`:
  - `rpo=FE1`
  - `section_id=sec_stan_002`
  - `selectable=FALSE`
  - `active=TRUE`
  - `display_behavior` blank
- `stingray_ovs` has `status=standard` for both `opt_fe1_001` and `opt_fe1_002` across all six Stingray variants.
- `rule_mapping`, `price_rules`, and `exclusive_group_members` have no references to `opt_fe1_001` or `opt_fe1_002`.
- The canonical standard-equipment generator pass already emits `standardEquipment` from `stingray_ovs.status=standard` and prefers canonical non-`sec_stan_002` rows.
- Current generated `standardEquipment` already uses `opt_fe1_001` for all six Stingray variants.
- `form-app/app.js` still has transitional runtime replacement/default behavior for `FE1`:
  - `defaultRpo of ["FE1", "NGA", "BC7"]`
  - `deleteSelectedRpo("FE1")` when `Z51` replaces standard suspension
  - a disabled reason for `FE1` when `Z51` is selected
- `tests/stingray-form-regression.test.mjs` currently includes one historical assertion that `opt_fe1_002` exists as a standard-equipment duplicate. That assertion must be updated because Phase 1B intentionally removes the active duplicate.

Change type: data-only workbook source edit, generated artifact refresh, and focused test expectation update.

Risk level: Medium-low. `FE1` has runtime replacement/default behavior, but Phase 1B does not change that behavior path. The row being deactivated is the non-selectable mirror; the visible selectable canonical row remains the behavior source.

## Exact Scope

Deactivate this `stingray_options` mirror row:

| RPO | Canonical row to keep | Mirror row to deactivate | Status coverage |
| --- | --- | --- | --- |
| `FE1` | `opt_fe1_001` | `opt_fe1_002` | canonical and mirror both standard in all variants |

For `opt_fe1_002`:

- Set `stingray_options.active=FALSE`.
- Keep `stingray_options.selectable=FALSE`.
- Leave `display_behavior` blank.
- Leave `stingray_ovs` rows intact for this pass.
- Do not delete the row in Phase 1B.

For `opt_fe1_001`:

- Leave `active=TRUE`.
- Leave `selectable=TRUE`.
- Leave `section_id=sec_susp_001`.
- Leave `price=0`.
- Do not add `display_behavior=default_selected` in this pass. Runtime already defaults `FE1` through the existing default-RPO path, and this pass should not broaden behavior.

## Exact Files To Change

- `stingray_master.xlsx`
- `tests/stingray-form-regression.test.mjs`
- Generated artifacts after approved implementation:
  - `form-output/stingray-form-data.json`
  - `form-output/stingray-form-data.csv`
  - `form-app/data.js`
  - generated `form_*` sheets in `stingray_master.xlsx`
- This spec file, after implementation, to record the execution result.

## Out Of Scope

- `AE4`, `AH2`, `AQ9`, `UQT`.
- Any Phase 1A rows already deactivated.
- Moving `FE1` replacement/default behavior out of runtime JavaScript.
- Adding workbook rules for `Z51 -> FE1` replacement.
- Adding or changing `display_behavior=default_selected`.
- Changing `rule_mapping`, `price_rules`, rule groups, or exclusive groups.
- Deleting duplicate rows.
- Changing Grand Sport source sheets.
- Changing dealer submission payloads or runtime endpoints.

## Constraints

- Workbook remains source of truth.
- Use `.venv/bin/python` for workbook scripts.
- Close Excel before any workbook-writing script.
- Do not ignore a real `~$stingray_master.xlsx` lock file.
- Save workbook changes only through existing safe workbook helpers if a script writes `stingray_master.xlsx`.
- Verify the saved workbook on disk before claiming the edit landed.
- Preserve current runtime behavior and visual behavior.
- Do not add dependencies.
- Do not solve generated-output changes with runtime patches.
- Keep this pass limited to `FE1`; do not opportunistically clean up seat/interior duplicates.

## Implementation Plan

1. Confirm no Excel lock file exists.
2. Write a narrow workbook mutation script or one-off safe script that:
   - loads `stingray_master.xlsx`;
   - confirms `opt_fe1_002` currently matches `rpo=FE1`, `section_id=sec_stan_002`, `selectable=FALSE`, `active=TRUE`;
   - confirms `opt_fe1_001` remains `rpo=FE1`, `section_id=sec_susp_001`, `selectable=TRUE`, `active=TRUE`;
   - changes only `opt_fe1_002.active` to `FALSE`;
   - saves via `save_workbook_safely()`.
3. Reopen the saved workbook with `openpyxl` and verify:
   - `opt_fe1_002.active=FALSE`;
   - `opt_fe1_001.active=TRUE`;
   - `stingray_ovs` FE1 rows are unchanged.
4. Run workbook package validation.
5. Run `scripts/generate_stingray_form.py`.
6. Update `tests/stingray-form-regression.test.mjs` so the FE1 duplicate test asserts the mirror is no longer emitted while the visible canonical tile still wins default behavior.
7. Update `tests/stingray-generator-stability.test.mjs` only if the generated closed-out count changes as expected.
8. Inspect generated diffs for unintended changes.
9. Run focused regression gates.

## Expected Generated Output

- `choices` should drop by 6 compared with the current Phase 1A state because one inactive mirror row should no longer emit one choice per active Stingray variant.
- `standardEquipment` should remain unchanged at the semantic level and continue to include `opt_fe1_001` for all six Stingray variants.
- No generated choice rows should reference `opt_fe1_002`.
- `FE1` should remain selected by default through the existing runtime default path.
- Selecting `Z51` should still remove `FE1` and auto-add `FE3`.

## Tests To Update

Update `tests/stingray-form-regression.test.mjs`:

- Replace the historical expectation that `opt_fe1_002` exists as a generated standard-equipment duplicate.
- Keep the assertion that `opt_fe1_001` exists as a visible selectable suspension choice.
- Add or keep an assertion that no generated choice for the current variant uses `opt_fe1_002`.
- Keep the runtime assertions that:
  - `defaultChoiceForRpo()` prefers selectable non-`standard_equipment` rows;
  - initial selected FE1 state contains exactly one `FE1`;
  - the selected FE1 row is `opt_fe1_001`;
  - selecting `Z51` removes `FE1` and still includes `FE3`.

Update `tests/stingray-generator-stability.test.mjs` only for the expected closed-out `choices` count if needed.

## Validation Plan

Workbook validation:

```sh
.venv/bin/python scripts/validate_workbook_package.py stingray_master.xlsx
```

Generator:

```sh
.venv/bin/python scripts/generate_stingray_form.py
```

Tests:

```sh
node --test tests/stingray-form-regression.test.mjs
node --test tests/stingray-generator-stability.test.mjs
```

Focused generated-data checks:

- `stingray_options.opt_fe1_002.active=FALSE` on disk.
- `stingray_options.opt_fe1_001.active=TRUE` on disk.
- No generated `choices` rows reference `opt_fe1_002`.
- `standardEquipment` contains `opt_fe1_001` for all six Stingray variants.
- No duplicate nonblank `(variant_id, rpo)` rows exist in `standardEquipment`.
- Runtime default state selects exactly one `FE1`, and it is `opt_fe1_001`.
- Runtime `Z51` selection removes `FE1` and auto-adds `FE3`.

## Rollback Plan

If generated output loses required FE1 behavior:

- restore only `opt_fe1_002.active=TRUE`;
- regenerate;
- restore the old FE1 duplicate test expectation only if the duplicate must remain active;
- document which runtime or source-data dependency still requires the mirror row before retrying.

## 2026-05-17 Execution Result

Implemented successfully.

What changed:

- Set `stingray_options.active=FALSE` for `opt_fe1_002`.
- Left `opt_fe1_001` active/selectable in `sec_susp_001`.
- Left `stingray_ovs` FE1 rows intact.
- Regenerated the Stingray form artifacts.
- Updated the FE1 regression test so it now asserts the mirror row is no longer emitted while the visible canonical suspension tile remains the default FE1 row.
- Updated the generated contract choice count from `1464` to `1458`.

Validation result:

- Workbook package validation returned `status=valid`, `issue_count=0`.
- `scripts/generate_stingray_form.py` completed with `validation_errors=0`.
- Generated `choices` dropped from `1464` to `1458`, matching one inactive mirror row across six variants.
- Generated `standardEquipment` remained `467`.
- Focused generated-data inspection found no generated choice rows for `opt_fe1_002`.
- Focused generated-data inspection found `opt_fe1_001` in `standardEquipment` for all six Stingray variants.
- Focused generated-data inspection found no duplicate nonblank `(variant_id, rpo)` rows in `standardEquipment`.
- Runtime regression coverage still proves default FE1 selection uses `opt_fe1_001`, and selecting `Z51` removes `FE1` while auto-adding `FE3`.

## Approval Gate

Phase 1B was approved and implemented.
