# Z Exclusive Group Note Cleanup Pass A Spec

## Diagnosis

The approved Z source hygiene audit found 12 Grand Sport mentions in target Z exclusive-group source sheets. These are not raw GM accessory copy and not internal provenance; they are active workbook source notes on Z-specific exclusive groups. The group IDs, selection modes, active flags, and members appear structurally Z-scoped, but the notes still say “Grand Sport,” which would be misleading if the rows are used for runtime readiness or future generated metadata.

Evidence inspected:

- Branch/worktree:
  - branch: `z06-zr1-migration`
  - upstream in sync with origin at inspection time
  - existing untracked files are `.DS_Store`, `backups/`, and prior audit spec `.hermes/plans/z-source-hygiene-audit-spec.md`
- Workbook lock:
  - `~$stingray_master.xlsx` not present during inspection
- Sheets and headers inspected read-only:
  - `z06_exclusive_groups`: `group_id`, `selection_mode`, `active`, `notes`
  - `zr1_exclusive_groups`: `group_id`, `selection_mode`, `active`, `notes`
  - `zr1x_exclusive_groups`: `group_id`, `selection_mode`, `active`, `notes`
- Target rows found:
  - `z06_exclusive_groups` rows 2, 3, 5, 6, 7, 8
  - `zr1_exclusive_groups` rows 2, 3, 5
  - `zr1x_exclusive_groups` rows 2, 3, 5

Root cause: the future-model compatibility rebase copied Grand Sport exclusive-group notes into Z model target sheets. The note text was not normalized after group IDs were rebased to Z model prefixes.

Risk level: low. This pass changes notes only. It does not change group IDs, members, active flags, selection modes, rules, prices, options, OVS rows, generated data, or runtime behavior.

Change type: workbook/data-only note cleanup. No runtime promotion.

## Decision / Ownership

Decision: workbook source data.

The incorrect text lives in workbook source sheets. The fix belongs in `stingray_master.xlsx` source rows, not Python, JavaScript, or generated artifacts.

## Exact Workbook Rows To Change

Only update `notes` cells in these rows:

### `z06_exclusive_groups`

1. `z06_excl_center_caps`
   - old: `Grand Sport wheel center cap choices are mutually exclusive within the Wheel Accessory section.`
   - new: `Wheel center cap choices are mutually exclusive within the Wheel Accessory section.`

2. `z06_excl_indoor_car_covers`
   - old: `Grand Sport indoor car cover choices are mutually exclusive within the LPO Exterior section.`
   - new: `Indoor car cover choices are mutually exclusive within the LPO Exterior section.`

3. `z06_excl_suede_compartment_liners`
   - old: `Grand Sport suede frunk/trunk compartment liner choices are mutually exclusive within the LPO Interior section.`
   - new: `Suede frunk/trunk compartment liner choices are mutually exclusive within the LPO Interior section.`

4. `z06_excl_ground_effects`
   - old: `Grand Sport ground effects choices are mutually exclusive; inactive members stay in the source for reactivation without appearing in draft output.`
   - new: `Ground effects choices are mutually exclusive; inactive members stay in the source for reactivation without appearing in draft output.`

5. `z06_excl_exterior_accents`
   - old: `Grand Sport exterior accent choices require either EFR or EDU; selected default cannot be cleared without choosing the alternate accent package.`
   - new: `Exterior accent choices require either EFR or EDU; selected default cannot be cleared without choosing the alternate accent package.`

6. `z06_excl_performance_brakes`
   - old: `Grand Sport brake choices require one active brake selection; selected default cannot be cleared without choosing another brake package.`
   - new: `Brake choices require one active brake selection; selected default cannot be cleared without choosing another brake package.`

### `zr1_exclusive_groups`

1. `zr1_excl_center_caps`
   - new: `Wheel center cap choices are mutually exclusive within the Wheel Accessory section.`
2. `zr1_excl_indoor_car_covers`
   - new: `Indoor car cover choices are mutually exclusive within the LPO Exterior section.`
3. `zr1_excl_suede_compartment_liners`
   - new: `Suede frunk/trunk compartment liner choices are mutually exclusive within the LPO Interior section.`

### `zr1x_exclusive_groups`

1. `zr1x_excl_center_caps`
   - new: `Wheel center cap choices are mutually exclusive within the Wheel Accessory section.`
2. `zr1x_excl_indoor_car_covers`
   - new: `Indoor car cover choices are mutually exclusive within the LPO Exterior section.`
3. `zr1x_excl_suede_compartment_liners`
   - new: `Suede frunk/trunk compartment liner choices are mutually exclusive within the LPO Interior section.`

## Files / Artifacts To Change

Change:

- `stingray_master.xlsx`
  - `z06_exclusive_groups.notes`
  - `zr1_exclusive_groups.notes`
  - `zr1x_exclusive_groups.notes`

No other file should be changed by implementation.

Do not change:

- generated `form_*` workbook sheets
- `form-output/`
- `form-app/data.js`
- `form-app/app.js`
- tests
- scripts
- `model_master`, `variant_master`, `model_workbook_sources`, or `model_registry_promotion`

## Implementation Plan

Use a small workbook-safe Python script run from the repo root:

1. Refuse to run if `~$stingray_master.xlsx` exists.
2. Open `stingray_master.xlsx` with `openpyxl` in write mode.
3. Locate each target row by `group_id`, not by hardcoded row number.
4. Verify the current note exactly matches the expected old text before changing it.
5. Update only the `notes` cell.
6. Save with `save_workbook_safely()` from `scripts/corvette_form_generator/workbook.py`.
7. Reopen the workbook read-only and verify:
   - all 12 target notes equal expected new text
   - no `Grand Sport` mentions remain in the three `*_exclusive_groups` sheets
   - row counts and headers are unchanged
8. Run workbook validators.
9. Review git diff for `stingray_master.xlsx` only, plus the already-created spec files if present.

## Constraints

- Visual preservation: no app UI/CSS/HTML changes.
- No refactor.
- No new dependencies.
- Workbook source-of-truth rule applies: fix workbook notes, not generated artifacts or code.
- Do not edit generated `form_*` sheets directly.
- Do not regenerate app data for this note-only cleanup unless validation unexpectedly shows generated output must be refreshed.
- Do not activate or promote Z06/ZR1/ZR1X.
- Do not change dealer submission endpoint, payload shape, or Turnstile behavior.
- Do not make product-rule decisions in this pass. In particular, do not change the Z06 `SHT` stripe exclusion rules from audit bucket `needs human product decision`.
- Stop if Excel lock file exists.

## Risks and Non-goals

Risks:

- Low workbook-write risk: any write to `stingray_master.xlsx` must use safe-save and on-disk verification.
- If the old note text has drifted since inspection, the script should stop rather than applying fuzzy edits.

Non-goals:

- Do not change exclusive-group membership.
- Do not change `selection_mode`, including Z06 required groups.
- Do not clean `z06_rule_mapping` SHT/Grand Sport Heritage text.
- Do not clean `future_model_source_review` or `future_model_option_review` provenance.
- Do not normalize safe raw GM accessory copy in Z option sheets.
- Do not generate runtime artifacts.

## Validation Plan

Pre-write:

```sh
git branch --show-current
git status --short --branch
test ! -e '~$stingray_master.xlsx'
.venv/bin/python scripts/validate_workbook_package.py stingray_master.xlsx
.venv/bin/python scripts/validate_workbook_schema.py stingray_master.xlsx
```

Implementation verification:

- On-disk `openpyxl` readback of the 12 exact `notes` cells.
- Scan `z06_exclusive_groups`, `zr1_exclusive_groups`, and `zr1x_exclusive_groups` for `Grand Sport`; expected count: 0.
- Verify row counts are unchanged:
  - `z06_exclusive_groups`: currently 7 data rows
  - `zr1_exclusive_groups`: currently 4 data rows
  - `zr1x_exclusive_groups`: currently 4 data rows

Post-write validators:

```sh
.venv/bin/python scripts/validate_workbook_package.py stingray_master.xlsx
.venv/bin/python scripts/validate_workbook_schema.py stingray_master.xlsx
```

Diff review:

```sh
git diff --stat
git diff -- stingray_master.xlsx
```

Generators/tests:

- Not run by default for this pass because it changes only future-model inactive source notes and does not regenerate artifacts or runtime data.
- If a validator or diff review reveals generated-contract impact, stop and propose a follow-up validation/generation spec.

## Approval Question

Approve Cleanup Pass A exactly as scoped above: update only the 12 Grand Sport wording notes in Z exclusive-group source sheets using safe-save, then verify workbook/package/schema and read back the changed cells?
