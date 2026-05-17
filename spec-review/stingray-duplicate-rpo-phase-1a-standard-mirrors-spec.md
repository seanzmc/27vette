# Stingray Duplicate RPO Phase 1A Standard-Mirror Deactivation Spec

Spec only. Do not implement until approved.

## Diagnosis

Root cause: `stingray_options` still has active non-selectable `sec_stan_002` mirror rows for RPOs whose canonical `_001` rows already carry the same variant status coverage in `stingray_ovs`. These mirror rows duplicate standard-equipment output and keep duplicate RPOs active even though the canonical rows can own the behavior.

Exact sheets/files inspected:

- `stingray_master.xlsx`
  - `stingray_options`
  - `stingray_ovs`
  - `rule_mapping`
  - `price_rules`
  - `exclusive_group_members`
- `spec-review/stingray-duplicate-rpo-canonicalization-spec.md`
- `tests/stingray-form-regression.test.mjs`

Evidence from Phase 0:

- `rule_mapping`, `price_rules`, `rule_groups`, and `rule_group_members` have no references to the duplicate standard-mirror IDs in this pass.
- `exclusive_group_members` uses canonical `opt_efr_001`, not duplicate `opt_efr_002`.
- Canonical and mirror rows have matching `stingray_ovs` statuses for the scoped RPOs.

Change type: data-only workbook source edit, followed by generated artifact refresh and focused test updates only if generated parity requires them.

Risk level: Medium. The workbook edit is simple, but standard/included equipment output can change if the generator currently depends on mirror rows instead of canonical standard rows.

## Exact Scope

Deactivate these `stingray_options` mirror rows:

| RPO | Canonical row to keep | Mirror row to deactivate | Status coverage |
| --- | --- | --- | --- |
| `719` | `opt_719_001` | `opt_719_002` | canonical and mirror both standard in all variants |
| `CF7` | `opt_cf7_001` | `opt_cf7_002` | canonical and mirror both standard for coupe, unavailable for convertible |
| `CM9` | `opt_cm9_001` | `opt_cm9_002` | canonical and mirror both unavailable for coupe, standard for convertible |
| `EFR` | `opt_efr_001` | `opt_efr_002` | canonical and mirror both standard in all variants |
| `EYT` | `opt_eyt_001` | `opt_eyt_002` | canonical and mirror both standard in all variants |
| `J6A` | `opt_j6a_001` | `opt_j6a_002` | canonical and mirror both standard in all variants |
| `NGA` | `opt_nga_001` | `opt_nga_002` | canonical and mirror both standard in all variants |
| `QEB` | `opt_qeb_001` | `opt_qeb_002` | canonical and mirror both standard in all variants |

For each mirror row:

- Set `stingray_options.active=FALSE`.
- Keep `stingray_options.selectable=FALSE`.
- Leave `display_behavior` blank unless generator parity proves `hidden` is required.
- Leave `stingray_ovs` rows intact for this pass.
- Do not delete any rows in Phase 1A.

## Out Of Scope

- `FE1` / `opt_fe1_002`: exclude because `tests/stingray-form-regression.test.mjs` currently asserts the duplicate exists as a standard-equipment row, and FE1 is tied to replacement/default logic.
- Seat duplicates: `AE4`, `AH2`, `AQ9`.
- `UQT`.
- Any new workbook sheets or columns.
- Any runtime JavaScript changes.
- Deleting duplicate rows.
- Changing `rule_mapping`, `price_rules`, rule groups, or exclusive groups.
- Changing Grand Sport source sheets.

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

## Implementation Plan

1. Confirm no Excel lock file exists.
2. Write a narrow workbook mutation script or one-off safe script that:
   - loads `stingray_master.xlsx`;
   - confirms each target row currently matches expected `option_id`, `rpo`, `section_id=sec_stan_002`, `selectable=FALSE`, `active=TRUE`;
   - changes only `active` to `FALSE` on the eight target rows;
   - saves via `save_workbook_safely()`.
3. Reopen the saved workbook with `openpyxl` and verify the eight target rows are `active=FALSE`.
4. Run `scripts/generate_stingray_form.py`.
5. Inspect generated diffs for unintended changes.
6. Run focused regression gates.
7. If standard/included equipment output drops a canonical RPO, stop and diagnose generator ownership before broadening the change.

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

Focused assertions to verify manually or with targeted inspection:

- The eight mirror rows are inactive in `stingray_options`.
- Canonical rows remain active.
- `exclusive_group_members.excl_ext_accents` still references `opt_efr_001`.
- No generated active choice references:
  - `opt_719_002`
  - `opt_cf7_002`
  - `opt_cm9_002`
  - `opt_efr_002`
  - `opt_eyt_002`
  - `opt_j6a_002`
  - `opt_nga_002`
  - `opt_qeb_002`
- Standard & Included summaries still include the relevant RPOs through canonical rows.
- Dealer submission payload shape is unchanged.

## Rollback Plan

If generated output loses required standard-equipment behavior:

- restore only the changed `active` cells for the affected mirror rows to `TRUE`;
- regenerate;
- document the generator dependency before attempting a different source-data fix.

## 2026-05-17 Execution Result

Attempted implementation and rolled back.

What happened:

- The workbook edit itself succeeded: the eight mirror rows were set to `active=FALSE` and verified on disk.
- `scripts/generate_stingray_form.py` completed with `validation_errors=0`.
- The generated invariant check failed: `standardEquipment` no longer contained the affected RPOs through the canonical rows.

Conclusion:

The current generator still depends on these `sec_stan_002` mirror rows to populate Standard & Included equipment. Deactivating the mirror rows alone is not behavior-preserving.

Rollback:

- Restored `stingray_master.xlsx`, `form-output/stingray-form-data.json`, `form-output/stingray-form-data.csv`, and `form-app/data.js` with `git restore`.
- Reopened the workbook and verified the eight mirror rows are back to `active=TRUE`.
- Re-ran workbook package validation; result was `status=valid`, `issue_count=0`.

Next required spec:

- Before retrying this pass, update the generator so standard equipment can be emitted from canonical selectable rows when their `stingray_ovs.status=standard`.
- The generator change must preserve current Standard & Included behavior before any mirror row is deactivated.
- Do not rerun this Phase 1A workbook edit unchanged.

## Approval Gate

Do not implement until approved. Approval should explicitly confirm Phase 1A scope excludes `FE1`, `AE4`, `AH2`, `AQ9`, and `UQT`.
