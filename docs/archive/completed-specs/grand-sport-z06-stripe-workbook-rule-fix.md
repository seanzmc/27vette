# Spec: Grand Sport/Z06 stripe workbook rule fix

## Diagnosis

The requested behavior is workbook-owned, not runtime-owned.

Business requirements:

1. Grand Sport and Z06: `SHT` and `VPO` must be selectable together.
2. Grand Sport and Z06: selecting `PDA` must auto-add `SNE` and `VPW`.
3. Grand Sport and Z06: rear hash graphics `VPW` and `VPO` must be selectable with a dual racing stripe.

Evidence inspected from `stingray_master.xlsx` read-only:

- `grandSport_options`
  - `opt_sht_001` / `SHT` is active/selectable in `sec_stri_001`.
  - `opt_vpo_001` / `VPO` is active/selectable in `sec_stri_001`.
  - `opt_pda_001` / `PDA` is active/selectable in `sec_stri_001`.
  - `opt_sne_001` / `SNE` is active/selectable in `sec_stri_001`.
  - `opt_vpw_001` / `VPW` is active/selectable in `sec_stri_001`.
- `z06_options`
  - Same five option IDs/RPOs are active/selectable and currently placed in `sec_stri_001`.
- `section_master`
  - `sec_stri_001` is `Stripes` with `selection_mode=single_select_opt`.
  - `sec_hash_001` is `Hash Marks` with `selection_mode=single_select_opt`.
  - `sec_gsha_001` is `GS Hash Marks` with `selection_mode=single_select_opt`.
  - `sec_gsce_001` is `GS Center Stripes` with `selection_mode=single_select_opt`.
- `grandSport_rule_mapping`
  - `gs_rule_opt_pda_001_includes_opt_sne_001` is active.
  - `gs_rule_opt_pda_001_includes_opt_vpw_001` is active.
- `z06_rule_mapping`
  - `z06_rule_opt_pda_001_includes_opt_sne_001` is active.
  - `z06_rule_opt_pda_001_includes_opt_vpw_001` is active.
- `grandSport_rule_groups` / `grandSport_rule_group_members`
  - Dual racing stripe source groups currently target `SHT` and `SNE`, not `VPO` or `VPW`.
  - `VPO` and `VPW` have active mutual/conflicting Jake-graphics group members.
  - `SHT` does not directly target `VPO` in an active group.
- `z06_rule_groups` / `z06_rule_group_members`
  - Dual racing stripe source groups currently target `SHT` and `SNE`, not `VPO` or `VPW`.
  - `VPO` and `VPW` have active mutual/conflicting Jake-graphics group members.
  - `SHT` does not directly target `VPO` in an active group.

Root cause:

- `VPO` and `VPW` are rear hash graphics but are placed in `sec_stri_001`, whose `single_select_opt` behavior makes them peers of the dual racing stripes and other stripe choices. That section placement prevents combinations even when no explicit rule group blocks them.
- `PDA -> SNE` and `PDA -> VPW` include rules already exist in both Grand Sport and Z06 workbook source sheets; the fix should preserve and test those rows rather than re-adding duplicate rules.
- `PDA` also cannot live in the same `single_select_opt` section as its included `SNE` target, or generic runtime reconciliation suppresses the include as a selected peer. The workbook needs a separate package/graphics section for `PDA` so `PDA` can auto-add both `SNE` and `VPW` without a runtime exception.
- Current explicit dual-stripe blocker groups already block hood/Jake graphics `SHT` and `SNE`, not rear hash graphics `VPO`/`VPW`. The dual-stripe part of the reported bug is therefore primarily bad section ownership for `VPO`/`VPW`, not missing runtime logic.

Risk level: medium.

Change type: workbook/data-only plus generated artifact refresh and tests. No runtime JavaScript change is expected.

## Exact workbook changes

Use a safe-save workbook writer. Do not edit generated `form_*` sheets directly.

### 1. Add a package/graphics section for PDA

Add this source section row in `section_master` if it is not already present:

- `section_id=sec_jake_001`
- `section_name=Jake Graphics Package`
- `selection_mode=multi_select_opt`
- `is_required=False`
- `display_order=27`
- `standard_behavior=locked_included`
- `step_key=aero_exhaust_stripes_accessories`

Reasoning:

- `PDA` is the package/source option that includes component graphics.
- It cannot share `sec_stri_001` with `SNE`, because `sec_stri_001` is a `single_select_opt` radio-style section and suppresses included same-section peers.
- A separate workbook section preserves generic runtime behavior and avoids an RPO-specific JavaScript workaround.

### 2. Move rear hash graphics out of the Stripes single-select section and move PDA into the package section

Update these source option rows:

- `grandSport_options`
  - `option_id=opt_pda_001`, `rpo=PDA`: change `section_id` from `sec_stri_001` to `sec_jake_001`.
  - `option_id=opt_vpo_001`, `rpo=VPO`: change `section_id` from `sec_stri_001` to `sec_hash_001`.
  - `option_id=opt_vpw_001`, `rpo=VPW`: change `section_id` from `sec_stri_001` to `sec_hash_001`.
- `z06_options`
  - `option_id=opt_pda_001`, `rpo=PDA`: change `section_id` from `sec_stri_001` to `sec_jake_001`.
  - `option_id=opt_vpo_001`, `rpo=VPO`: change `section_id` from `sec_stri_001` to `sec_hash_001`.
  - `option_id=opt_vpw_001`, `rpo=VPW`: change `section_id` from `sec_stri_001` to `sec_hash_001`.

Reasoning:

- `VPO` and `VPW` are rear hash graphics, not full-length dual racing stripes.
- Moving them to `sec_hash_001` lets each rear hash option be selected with one `sec_stri_001` dual racing stripe while preserving single-select behavior between rear hash peers inside `sec_hash_001`.
- This also allows `SHT` (`sec_stri_001`) and `VPO` (`sec_hash_001`) to coexist, because there is no active explicit `SHT -> VPO` or `VPO -> SHT` blocker in the inspected group rows.

Do not move `SHT` or `SNE` in this pass unless a separate product decision says those hood graphics should also be independent from dual racing stripes.

### 3. Preserve PDA include rules and keep rule-section metadata aligned

Verify these direct include rows remain active and unmodified:

- `grandSport_rule_mapping`
  - `gs_rule_opt_pda_001_includes_opt_sne_001`
  - `gs_rule_opt_pda_001_includes_opt_vpw_001`
- `z06_rule_mapping`
  - `z06_rule_opt_pda_001_includes_opt_sne_001`
  - `z06_rule_opt_pda_001_includes_opt_vpw_001`

Do not create duplicate include rows. The existing workbook contract already expresses the `PDA` auto-add behavior.

Also update `source_section` / `target_section` metadata in `grandSport_rule_mapping` and `z06_rule_mapping` where the moved options appear:

- `source_id=opt_pda_001`: `source_section=sec_jake_001`.
- `target_id=opt_vpw_001` or `target_id=opt_vpo_001`: `target_section=sec_hash_001`.
- `target_id=opt_sne_001`: keep `target_section=sec_stri_001`.

### 3. Clean/update explanatory notes only if needed

After moving `VPO`/`VPW`, inspect active blocker group notes and disabled reasons for stale wording that says rear hash graphics conflict with dual racing stripes.

Expected semantic boundaries:

- Keep dual racing stripe groups blocking `SHT` and `SNE` if hood/Jake graphics are still not compatible with dual racing stripes.
- Do not let dual racing stripe groups target `VPO` or `VPW`.
- Keep `VPO` and `VPW` as rear-hash peers if product intent is that only one rear hash graphic can be selected at a time.
- Keep `PDA` blockers against dual racing stripes unless product intent explicitly says the full `PDA` package can pair with dual stripes despite including `SNE`.

Likely note updates:

- Update `*_group_vpw_excludes_*` notes from “VPW conflicts with SHT and VPO” to “VPW conflicts with VPO; SHT compatibility is governed by its own product rule” only if the implementation also removes any active `VPW -> SHT` member. If that member stays active, leave the note accurate.
- Update any `*_group_pda_excludes_*` notes only if stale wording implies `VPW` itself blocks dual racing stripes. The reason should describe the package/hood graphic conflict, not rear-hash conflict.

## Tests to add/update

Add focused regression coverage before or with the workbook writer.

### Grand Sport runtime/generated-data test

In `tests/multi-model-runtime-switching.test.mjs` or a Grand Sport draft/runtime-focused test:

- Activate Grand Sport, choose a valid body/trim, reset/reconcile.
- Assert generated choices place:
  - `VPO` and `VPW` in `sec_hash_001`.
  - representative dual racing stripe, `SHT`, `SNE`, and `PDA` still in `sec_stri_001` unless explicitly changed.
- Select a representative dual racing stripe (`DPB` is acceptable if active for the selected variant), then select `VPO`; assert both selected.
- Select the same representative dual racing stripe, then select `VPW`; assert both selected.
- Select `SHT`, then select `VPO`; assert both selected.
- Select `PDA`; assert auto-added map/order summary includes `SNE` and `VPW` from the workbook include rules.

### Z06 draft/runtime test

In `tests/z06-form-data-draft.test.mjs` and/or `tests/multi-model-runtime-switching.test.mjs` if Z06 is promoted in `form-app/data.js`:

- Assert generated Z06 draft choices place `VPO` and `VPW` in `sec_hash_001`.
- Assert `PDA -> SNE` and `PDA -> VPW` include rules are emitted.
- If runtime-promoted Z06 is available in `form-app/data.js`, perform the same runtime interaction assertions as Grand Sport.
- If Z06 is only draft/preview in the current branch, keep interaction coverage at generated-contract level and state browser/runtime verification pending until promoted/runtime data is available.

### Workbook-source guard test

Add or update a workbook/schema test that reads raw workbook rows and asserts:

- `grandSport_options.opt_vpo_001.section_id === sec_hash_001`
- `grandSport_options.opt_vpw_001.section_id === sec_hash_001`
- `z06_options.opt_vpo_001.section_id === sec_hash_001`
- `z06_options.opt_vpw_001.section_id === sec_hash_001`
- Both `PDA` include rows remain active in `grandSport_rule_mapping` and `z06_rule_mapping`.
- No active `*_rule_group_members` row under a dual-racing-stripe source group targets `opt_vpo_001` or `opt_vpw_001`.

## Implementation constraints

- Workbook source of truth only. Do not patch this with RPO-specific JavaScript.
- Use existing source sheets and existing generator/runtime pathways:
  - `grandSport_options`
  - `z06_options`
  - `grandSport_rule_mapping`
  - `z06_rule_mapping`
  - `*_rule_groups`
  - `*_rule_group_members`
- Do not add a new review sheet, duplicate taxonomy, helper module, or runtime exception unless inspection proves the existing section/rule sheets cannot express the behavior.
- Do not edit generated `form_*` sheets manually.
- Do not alter Stingray stripe behavior in this pass.
- Do not promote or change ZR1/ZR1X.
- Do not change dealer submission endpoint, payload shape, Turnstile behavior, or deployment paths.
- Do not change option prices, display order, active/selectable flags, or labels unless a stale note/description is directly tied to the fixed rule semantics.
- Preserve workbook table schemas.
- Stop before writing if `~$stingray_master.xlsx` exists or Excel is open.

## Validation plan

Preflight:

```sh
git status --short --branch
.venv/bin/python scripts/validate_workbook_package.py stingray_master.xlsx
```

Workbook writer/dry-run expectations:

- Add a small idempotent script or use the existing safe workbook writer pattern.
- Dry-run should report exactly four option-section updates, plus any explicitly scoped note-only updates.
- `--write` must use `save_workbook_safely()` and verify saved rows on disk with `openpyxl`.

Regeneration:

```sh
.venv/bin/python scripts/generate_grand_sport_form.py
.venv/bin/python scripts/generate_z06_form.py
```

Targeted tests:

```sh
node --test tests/grand-sport-draft-data.test.mjs
node --test tests/grand-sport-rule-audit.test.mjs
node --test tests/z06-form-data-draft.test.mjs
```

Runtime/multi-model tests if `form-app/data.js` contains promoted Grand Sport/Z06 runtime data on the active branch:

```sh
node --test tests/multi-model-runtime-switching.test.mjs
```

If `generate_stingray_form.py` is needed to sync live `form-app/data.js` after workbook changes on the active branch, run:

```sh
.venv/bin/python scripts/generate_stingray_form.py
node --test tests/stingray-form-regression.test.mjs
node --test tests/multi-model-runtime-switching.test.mjs
```

Manual/browser verification after runtime data is regenerated:

- Grand Sport:
  - Select a dual racing stripe, then select `VPO`; both remain selected.
  - Select a dual racing stripe, then select `VPW`; both remain selected.
  - Select `SHT`, then select `VPO`; both remain selected.
  - Select `PDA`; `SNE` and `VPW` appear as auto-added/included.
- Z06, if promoted/runtime-visible:
  - Same interaction checks.
- Confirm no unexpected disabled tooltips cite dual racing stripes for `VPO` or `VPW`.

## Risks and non-goals

Risks:

- Moving `VPO`/`VPW` changes section grouping in generated artifacts; review generated diffs to confirm only intended model choices moved sections.
- `PDA` includes `SNE`; if `SNE` remains incompatible with dual racing stripes, then `PDA` will still be incompatible with dual racing stripes. That is intentional unless the product decision is expanded.
- If `sec_hash_001` is not desired for Grand Sport customer wording, a follow-up could add a dedicated rear-hash section row, but that is out of scope for the smallest safe pass.

Non-goals:

- No runtime hardcodes.
- No new workbook schema.
- No ZR1/ZR1X edits.
- No pricing, ordering, label, or image changes.
- No live deployment.

## Approval question

Approve the workbook-only pass to move `VPO` and `VPW` from `sec_stri_001` to `sec_hash_001` for Grand Sport and Z06, preserve/verify existing `PDA -> SNE/VPW` include rules, regenerate affected artifacts, and add the regression tests above?
