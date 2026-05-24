**Spec**

**Diagnosis:**  
FEY already has an active workbook-backed `includes` rule for T0F, and FEY already has a `$0` price override for T0F. The failure is caused by T0F’s own prerequisite model: T0F currently has direct `requires` rules for FEB and J57. Runtime auto-add logic only auto-adds an included target when that target’s own requirements are already satisfied, so FEY can auto-add J57 but still cannot auto-add T0F because T0F still sees FEB as missing.

**Change type:** data + generated artifacts + tests.  
**Risk:** medium-low, because it affects live Grand Sport rule behavior, but the intended fix uses existing workbook rule-group vocabulary instead of new hardcoded runtime logic.

**Files / Sheets To Change**

- `stingray_master.xlsx`
  - `grandSport_rule_groups`
  - `grandSport_rule_group_members`
- Generated artifacts after regeneration:
  - `form-output/inspection/grand-sport-form-data-draft.json`
  - `form-output/inspection/grand-sport-form-data-draft.md`
  - likely Grand Sport inspection/audit artifacts if generator rewrites them
  - `form-app/data.js` via Stingray app-data registry generation
  - `form-output/stingray-form-data.json`
  - `form-output/stingray-form-data.csv`
  - generated `form_*` workbook sheets if `generate_stingray_form.py` rewrites them
- Tests:
  - `tests/grand-sport-draft-data.test.mjs`
  - `tests/multi-model-runtime-switching.test.mjs`

**Workbook Rule Model**

Add a grouped requirement for T0F:

- `grandSport_rule_groups`
  - `group_id`: `gs_group_t0f_z52_requirement`
  - `group_type`: `requires_any`
  - `source_id`: `opt_t0f_001`
  - `disabled_reason`: `Requires FEB Z52 Sport Performance Package or FEY Z52 Track Performance Package.`
  - `active`: `TRUE`
  - `notes`: T0F is available with FEB plus required J57, or included by FEY.

- `grandSport_rule_group_members`
  - `gs_group_t0f_z52_requirement -> opt_feb_001`
  - `gs_group_t0f_z52_requirement -> opt_fey_001`

Keep the existing direct rule:

- `opt_t0f_001 requires opt_j57_001`

Do not remove or weaken:

- `opt_fey_001 includes opt_t0f_001`
- `opt_fey_001 includes opt_j57_001`
- `opt_fey_001 includes opt_cfz_001`
- `opt_t0f_001 includes opt_cfz_001`
- FEY/T0F/CFZ `$0` price overrides

**Expected Runtime Behavior**

- If FEB and J57 are selected, T0F is optional/selectable.
- If FEB is selected without J57, T0F remains unavailable because J57 is still required.
- If FEY is selected, FEY auto-adds J57 and T0F.
- T0F is auto-added at `$0` under FEY.
- T0F cannot be manually removed while FEY remains selected, because auto-added choices are selected/disabled in the existing runtime path.
- CFZ remains auto-added at `$0` through FEY/T0F behavior.
- No new JavaScript RPO-specific exception should be added.

**Constraints**

- Workbook source of truth remains hard constraint.
- No new dependencies.
- No unrelated refactor.
- No dealer submission endpoint, payload, or Turnstile changes.
- Do not edit generated `form_*` sheets directly.
- Do not hardcode FEY/T0F business logic in `form-app/app.js`.
- Check for `~$stingray_master.xlsx` before writing the workbook.
- Verify workbook changes on disk after save.

**Validation Plan**

1. Verify no Excel lock file:

   ```sh
   ls -la ~$stingray_master.xlsx
   ```

2. Edit workbook source rows only.

3. Verify workbook rows on disk with `openpyxl`.

4. Regenerate Grand Sport draft:

   ```sh
   .venv/bin/python scripts/generate_grand_sport_form.py
   ```

5. Regenerate app registry:

   ```sh
   .venv/bin/python scripts/generate_stingray_form.py
   ```

6. Run targeted tests:

   ```sh
   node --test tests/grand-sport-draft-data.test.mjs
   node --test tests/multi-model-runtime-switching.test.mjs
   ```

7. Diff-review generated output to confirm only intended Grand Sport rule/runtime data changed.

**Non-Goals**

- Do not redesign the rule engine.
- Do not change FEY package pricing.
- Do not change CFZ/T0F labels or placement.
- Do not migrate Grand Sport generation architecture.
- Do not touch Hermes’ separate spec work.
