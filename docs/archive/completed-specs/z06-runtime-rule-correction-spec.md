# Z06 Runtime Rule Correction Spec

> **Archive closure (2026-07-29): COMPLETED.** Implementation is present at `ef9769e`, and the later Pass 2 plan records this pass complete with green evidence. Any trailing approval request, including the original pre-approval warning below, is historical; current operator commands are owned by `README.md`. Stage C approved this completed plan for archival.

> **For Hermes:** This is a spec-first 27vette workbook/runtime pass. Do not implement until approved. Use workbook-authored source rows wherever the workbook can represent the rule; do not add Z06/RPO-specific JavaScript or Python business-rule exceptions.

**Goal:** Correct the Z06 runtime-facing option/rule logic that is making the front end behave unlike the intended workbook/product model, while preventing another destructive future-model review script incident.

**Architecture:** The workbook remains the source of truth. Z06 product decisions should live in `z06_options`, `z06_rule_mapping`, `z06_rule_groups`, `z06_rule_group_members`, `z06_exclusive_groups`, `z06_exclusive_members`, `z06_price_rules`, `z06_variant_overrides`, interior source sheets, and section metadata. Scripts should be idempotent safe-save helpers that apply workbook rows and regenerate artifacts; runtime JS should only consume generated rules generically.

**Tech Stack / Surfaces:** `stingray_master.xlsx`, Python safe-save workbook scripts under `scripts/`, generator outputs under `form-output/inspection/` and `form-app/data.js`, Node runtime tests under `tests/`.

---

## Current evidence and diagnosis

Evidence already inspected before this spec:

- Relevant old plans:
  - `.hermes/plans/z06-package-pricing-cascade-spec.md`
  - `docs/hermes-plans/z06-runtime-preview-contract-spec.md`
  - `docs/hermes-plans/z06-full-runtime-promotion-spec.md`
- Current branch:
  - `z06-zr1-migration`
- Workbook validation:
  - `.venv/bin/python scripts/validate_workbook_package.py` passed with `issue_count: 0`.
- Current Z06 package script dry-run:
  - `.venv/bin/python scripts/apply_z06_package_pricing_cascade.py --include-changes` reports `total_changes: 0`, but the script is incomplete and does not prove all intended runtime behavior.
- Targeted Node gates:
  - `node --test tests/z06-contract-preview.test.mjs tests/z06-form-data-draft.test.mjs tests/z06-runtime-promotion.test.mjs tests/multi-model-runtime-switching.test.mjs` passed.
- Current generated/runtime tests do not fully cover the Z06 option cascade.
- Code scan did not find hardcoded Z06/PDB/PDD/PDF/Z07 package behavior in `form-app/app.js`; the currently observed behavior is primarily driven by workbook rows and missing/inconsistent workbook rows.

Primary diagnosis:

1. The existing Z06 package cascade spec was directionally correct, but its implementation stopped short of the necessary grouped requirement and consistency rows.
2. Some rules are inverted: Z07 currently requires aero before selection, when it should be selectable first, auto-add J57 at $0, and then require T0F or T0G.
3. Some rules are copied from Grand Sport/Stingray patterns without Z06-specific source truth cleanup, producing wrong prerequisites and greyed-out choices.
4. Some logic exists only as partial includes/excludes, causing inconsistent deactivation. Example: PDD blocks PDF through an indirect conflict but does not cleanly behave as a package peer against all package alternatives.
5. The future-model option review writer has been involved in destructive sheet rewrites before. Even if currently patched to preserve blank fields from existing rows, it still rewrites whole Z option sheets and should not be part of runtime cleanup.

Risk level: high. This pass affects live Z06 runtime data and user-visible option behavior. Use small workbook-owned changes, RED tests, safe-save scripts, regeneration, and gates.

Change type: mixed workbook/data + targeted script/test + generated artifact refresh. Avoid runtime JS changes unless a generic runtime defect is proven by tests.

---

## Explicit user-provided Z06 rule corrections captured

The following points must be preserved as source-of-truth requirements for the pass planning below:

1. Destructive future-model option review writer:
   - Strong preference to remove or retire the destructive script if possible.
   - If not removed immediately, ensure this pass does not call it and add guardrails so it cannot accidentally rewrite Z source sheets again.

2. Exterior accents:
   - `EFY` should be included in the exterior accent grouped options.

3. Engine cover / engine appearance logic:
   - `D3V` is not adding to `BCW` on select.
   - `D3V` and `SL9` prices should go to `$0` when `B6P` is selected.
   - The engine-cover logic should match the previously explained structure and the proven Stingray/Grand Sport pattern where applicable.

4. Z07 package:
   - `Z07` should be available to select by default.
   - Selecting `Z07` should auto-add `J57` at `$0`.
   - The auto-added `J57` should not be removable while `Z07` remains selected.
   - After selecting `Z07`, the build must require a selection of either `T0F` or `T0G`.
   - Current behavior is backwards: requiring `T0F`/`T0G` before `Z07` can be selected is wrong.

5. Package / exclusive-group consistency:
   - Exclusive group deactivation is inconsistent.
   - `PDD` deactivates `PDF` for some reason but not `PDB`.
   - Package peer behavior should be explicit and consistent for `PDB`, `PDD`, and `PDF`.
   - `T0F` and `T0G` behavior with other spoilers/aero choices in the section is inconsistent and needs workbook-owned cleanup.

6. Suspension:
   - Suspension should not be allowed to change when `Z07` is selected.
   - In fact, suspension options probably do not need to appear on the front end for Z06 at all.

7. Exhaust:
   - Exhaust section is wrong.
   - `NWI` is greyed out saying it requires `WUB`.
   - `WUB` is standard equipment on Z06, so that requirement should not be needed.
   - `NWI` should be available by default.

8. Aero prerequisite cleanup:
   - `T0F` should not have a `J57` prerequisite for Z06.

9. Paint/exterior incompatibilities:
   - Correction: this is `EFY` unavailable with `GBA`, not `EDU`.
   - `EFY` is not available with `GBA`.
   - `ZYC` is not available with `GBA`.
   - `D84` is not available with `GBA`.
   - `D86` is not available with `GBA`.

10. Brake/caliper behavior:
   - `J57` should make `J6A` unavailable.
   - If `J57` is selected, then the carbon-fiber wheels should become selectable.

11. Carbon-fiber wheel availability and package behavior:
   - The rules should be set up around `J57` being selected, whether `J57` comes from `Z07`, `PDB`, `PDD`, `PDF`, or direct selection.
   - `J57` selected should make carbon-fiber wheels available.
   - When one of the wheel-and-brake packages is selected, all aluminum wheels should deactivate so only carbon wheels are available.
   - Existing missing behavior from audit: `PDB`, `PDD`, and `PDF` each need workbook `requires_any` groups requiring one of `ROY`, `ROZ`, or `STZ`.

12. Interior trim / component presentation:
   - Interior Trim section needs a larger makeover.
   - `UQT` should show as an option only for `1LZ`; it is included in `2LZ` and `3LZ`.
   - Other components should be interior components like Grand Sport and Stingray forms.
   - Stitching, two-tone, and suede steering wheel should not show as standalone selectable options except where selected options/add-ons result from choosing an interior that includes the component.

13. Accessory packages:
   - Packages in Accessories need to auto-add included components and zero out the included component prices.

14. Standard/selectable source-of-truth contract:
   - Some Z06 standard options show `selectable=False` in `z06_options` but wind up selectable in front-end testing.
   - That suggests either the generator/runtime is overriding workbook source truth, or the generated choice status/section behavior is being interpreted differently than the source sheet intends.
   - This must be investigated as a workbook-source-of-truth contract bug, not hidden with one-off UI suppression.

15. Additional engine/pricing/interior visibility corrections:
   - `ZZ3` should zero-price `SL9` when `ZZ3` adds/includes `SL9`.
   - Z06 3LZ seat pricing is wrong: `AH2` should be `$0`; `AE4` should be `$595`.
   - Interior choices/components seem to add prices correctly in totals, but chargeable interior cards currently display `$0`; the selectable card price display should show the actual charge for suede 3LZ and other chargeable component interiors.
   - Remaining Interior Trim options need rule cleanup.
   - `N3W` should never show as a front-end option.
   - `FA5` and `FA6` are mutually exclusive.
   - `V8X` and `RYQ` should not show on the front end and should be `active=False` in the workbook.
   - `PBC` requires `ZZ3` on convertible.

---

## Pass split

This spec deliberately splits the work into two implementation passes so the first pass fixes the runtime-blocking rule inversions and package cascade without mixing in the larger interior/accessory refactor.

### Pass 1 — Z06 runtime rule closure and destructive-writer retirement guard

Pass 1 should fix the current front-end blockers and obvious inverted/missing workbook rules:

1. Retire or isolate the destructive future-model option review writer from this workflow.
2. Fix `Z07` selectability and post-selection `requires_any` behavior.
3. Fix package peer exclusivity and package-to-carbon-wheel requirements.
4. Fix `J57`-driven carbon-wheel availability and brake/caliper exclusions.
5. Fix engine cover / `B6P` / `ZZ3` / `BCW` / `D3V` / `SL9` behavior.
6. Fix exhaust `WUB`/`NWI` behavior.
7. Fix immediate exterior accent / paint incompatibility rows: `EFY`, `ZYC`, `D84`, and `D86` unavailable with `GBA`.
8. Hide or deactivate front-end suspension options if supported directly by workbook rows, while keeping `Z07` suspension includes as internal/auto-added/standard behavior as appropriate.
9. Investigate and fix the Z06 `selectable=False` source contract mismatch where standard/source-nonselectable rows appear selectable in the front end.
10. Mark `V8X` and `RYQ` inactive so they do not appear on the front end.
11. Add the `PBC requires ZZ3 on convertible` rule.
12. Add targeted tests that prove all of the above before regenerating live runtime data.

### Pass 2 — Z06 interior/accessory presentation cleanup

Pass 2 should handle the broader, more structural cleanup:

1. Interior Trim section makeover.
2. `UQT` 1LZ-selectable / 2LZ-3LZ-included behavior.
3. Interior components: stitching, two-tone, suede steering wheel, and similar component rows should follow the Stingray/Grand Sport interior component model.
4. Correct 3LZ seat pricing and visible card pricing: `AH2=$0`, `AE4=$595`, and chargeable suede/component interiors must show their actual price on selection cards instead of `$0`.
5. `N3W` should never show as an option; `FA5` and `FA6` should be mutually exclusive.
6. Accessory package component auto-add and zero-price behavior.
7. Any remaining customer-facing section/label organization after Pass 1.

Do not start Pass 2 until Pass 1 behavior is green and the user approves the next pass.

---

## Pass 1 exact files / sheets / artifacts to inspect and likely change

### Workbook source sheets

- `stingray_master.xlsx`
  - `z06_options`
  - `z06_ovs`
  - `z06_rule_mapping`
  - `z06_rule_groups`
  - `z06_rule_group_members`
  - `z06_exclusive_groups`
  - `z06_exclusive_members`
  - `z06_price_rules`
  - `z06_variant_overrides`
  - `section_master`
  - relevant interior/source sheets only if needed to avoid breaking Pass 2 boundaries

### Scripts

- Modify or supersede:
  - `scripts/apply_z06_package_pricing_cascade.py`
- Add a new targeted safe-save script if the scope outgrows the package-only name, for example:
  - `scripts/apply_z06_runtime_rule_corrections.py`
- Inspect and possibly retire/guard:
  - `scripts/apply_future_model_option_review.py`
- Regenerate through existing approved generator path:
  - `scripts/generate_z06_form.py`
  - `scripts/generate_stingray_form.py` if live `form-app/data.js` must be refreshed

### Tests

Add or extend targeted tests:

- `tests/z06-form-data-draft.test.mjs`
- `tests/z06-runtime-promotion.test.mjs`
- `tests/multi-model-runtime-switching.test.mjs`
- Add a dedicated file if clearer:
  - `tests/z06-runtime-rule-corrections.test.mjs`

### Generated artifacts after approved implementation

Treat as outputs, not hand-edits:

- `form-output/inspection/z06-contract-preview.json`
- `form-output/inspection/z06-contract-preview.md`
- `form-output/inspection/z06-form-data-draft.json`
- `form-output/inspection/z06-form-data-draft.md`
- `form-output/inspection/z06-inspection.json`
- `form-output/inspection/z06-inspection.md`
- `form-app/data.js`
- generated `form_*` workbook sheets if the production generator writes them

---

## Pass 1 implementation plan

### Task 1: Guard or retire the destructive future-model option review script

**Objective:** Ensure this pass cannot accidentally wipe Z06/ZR1/ZR1X option-sheet values.

**Files:**
- Inspect: `scripts/apply_future_model_option_review.py`
- Inspect: any tests/references invoking it
- Modify only after explicit implementation approval.

**Steps:**
1. Search for every invocation/reference to `apply_future_model_option_review.py`.
2. If no active workflow depends on it, prefer deletion or rename-to-archived/deprecated with tests/docs updated.
3. If deletion is too risky, make the script fail closed for `z06_options`, `zr1_options`, and `zr1x_options` unless an explicit emergency flag is passed.
4. Add a regression test proving blank incoming review fields preserve existing workbook values by `option_id`, especially `price`, `section_id`, `display_order`, `selectable`, `active`, and `display_behavior`.
5. Confirm Pass 1 scripts do not call it.

**Acceptance:** The Z06 rule correction workflow does not depend on the destructive whole-sheet writer, and there is a guard/test against blank-field overwrites.

### Task 2: Build a RED runtime test for current Z07/package behavior

**Objective:** Lock the user-visible failures before changing workbook rows.

**Files:**
- Create/modify: `tests/z06-runtime-rule-corrections.test.mjs`

**Test assertions:**
1. `Z07` is selectable before selecting `T0F` or `T0G`.
2. Selecting `Z07` auto-adds `J57` at `$0`.
3. Auto-added `J57` cannot be removed while `Z07` remains selected.
4. After selecting `Z07`, missing requirements include the aero choice until one of `T0F`/`T0G` is selected.
5. Selecting `T0F` or `T0G` satisfies the `Z07` grouped requirement.
6. `T0F` itself does not require `J57` as a prerequisite.
7. Direct/selecting `J57` makes `ROY`/`ROZ`/`STZ` selectable.
8. Selecting `PDB`, `PDD`, or `PDF` requires one of `ROY`/`ROZ`/`STZ`.
9. Selecting a package disables/replaces aluminum wheel choices so only the carbon-wheel path is available for the package.
10. `PDB`/`PDD`/`PDF` are mutually exclusive peers.

**Expected before fix:** At least the Z07 selectability and package-to-wheel required assertions should fail.

### Task 3: Add workbook-owned Z07 rule correction rows

**Objective:** Invert the current Z07 behavior to the intended flow.

**Workbook ownership:**
- `z06_rule_mapping`
- `z06_rule_groups`
- `z06_rule_group_members`
- `z06_price_rules`

**Desired source behavior:**
1. Remove/deactivate any direct rule that makes `Z07` require `T0F` or `T0G` before `Z07` can be selected, if present.
2. Keep/add `Z07 includes J57`.
3. Keep/add `Z07 includes FE7` and `Z07 includes XFS` if source evidence supports them.
4. Keep/add `Z07 -> J57` price override to `$0`.
5. Keep/add `Z07 requires_any {T0F, T0G}` as a post-selection requirement, not a preselection block.
6. Ensure included `J57` is not removable while `Z07` remains selected through the existing generic includes/auto-add mechanics.

**Runtime boundary:** If generic runtime `requires_any` currently blocks the source option before selected, fix that as a generic semantic distinction only if workbook metadata cannot express the desired post-selection behavior. Do not hardcode `Z07`.

### Task 4: Add package-to-carbon-wheel required groups and consistent package exclusivity

**Objective:** Make `PDB`, `PDD`, and `PDF` behave as package peers that require a carbon-fiber wheel selection.

**Workbook ownership:**
- `z06_rule_groups`
- `z06_rule_group_members`
- `z06_exclusive_groups`
- `z06_exclusive_members`
- `z06_rule_mapping`
- `z06_price_rules`

**Desired rows:**
1. Add/verify `requires_any` groups:
   - `PDB requires_any {ROY, ROZ, STZ}`
   - `PDD requires_any {ROY, ROZ, STZ}`
   - `PDF requires_any {ROY, ROZ, STZ}`
2. Ensure `PDB`, `PDD`, `PDF` are all members of a single active package exclusive group.
3. If explicit peer excludes are needed by the current generator/runtime, add symmetric workbook-owned excludes so each package blocks/replaces the other two consistently.
4. Keep package include rows:
   - `PDB -> J57/J6D`
   - `PDD -> Z07/T0F/CFZ`
   - `PDF -> Z07/T0G/CFV`
5. Keep package/target zero-price overrides for included components.
6. Keep wheel-conditioned package price overrides.

**Special pricing guard:** Do not overwrite restored direct price cells in `z06_options`, `zr1_options`, or `zr1x_options`. Join by `option_id`, not row number.

### Task 5: Model J57 as the carbon-wheel enabler

**Objective:** Make carbon-fiber wheels available whenever `J57` is selected/auto-added, regardless of whether the source is direct `J57`, `Z07`, `PDB`, `PDD`, or `PDF`.

**Workbook ownership:**
- `z06_rule_mapping`
- possibly `z06_rule_groups` if a grouped availability concept is required
- `z06_exclusive_groups` / `z06_exclusive_members` for wheel replacement

**Desired behavior:**
1. `ROY`, `ROZ`, `STZ` should require or be enabled by `J57`.
2. The requirement should be satisfied when `J57` is selected directly or auto-added by a package/Z07.
3. Selecting a carbon-fiber wheel should replace aluminum wheel choices through workbook-owned replacement/exclusive rules.
4. Selecting a wheel-and-brake package should deactivate/replace all aluminum wheels so only carbon wheels are available for the package route.

**Do not:** Hardcode `J57` wheel availability in JavaScript.

### Task 6: Fix brake/caliper exclusions around J57

**Objective:** Correct immediate brake/caliper conflicts.

**Workbook ownership:**
- `z06_rule_mapping`
- `z06_exclusive_groups`
- `z06_exclusive_members`

**Desired behavior:**
1. `J57` should make `J6A` unavailable.
2. Preserve/verify intended `J57` / `J6D` behavior:
   - If `J6D` is a soft/default caliper with `J57`, do not model it as a hard user-removable add-on unless approved.
   - If package-included `J6D` must be non-removable, keep package include/zero-price semantics explicit.

### Task 7: Fix T0F/T0G/aero/spoiler rule cleanup

**Objective:** Remove wrong Z06 prerequisites and make aero/spoiler exclusivity consistent.

**Workbook ownership:**
- `z06_rule_mapping`
- `z06_exclusive_groups`
- `z06_exclusive_members`
- `z06_rule_groups` if needed

**Desired behavior:**
1. `T0F` should not have a `J57` prerequisite for Z06.
2. `T0F` and `T0G` should behave consistently as aero package peers.
3. Their includes should remain:
   - `T0F -> CFZ`
   - `T0G -> CFV`
4. `CFZ` and `CFV` should be mutually exclusive as ground-effects peers when both are active.
5. Other spoilers/aero section choices should deactivate/replace consistently based on workbook-authored excludes/groups, not incidental one-way rules.

### Task 8: Fix engine appearance / cover behavior

**Objective:** Restore the B6P/ZZ3/BCW/D3V/SL9 logic the user previously specified.

**Workbook ownership:**
- `z06_options`
- `z06_rule_mapping`
- `z06_price_rules`
- `z06_exclusive_groups`
- `z06_exclusive_members`
- `section_master` only if section behavior is wrong

**Desired behavior:**
1. `D3V` should add/include/activate correctly with `BCW` when selected, per the approved engine-cover structure.
2. Selecting `B6P` should make `D3V` price `$0`.
3. Selecting `B6P` should make `SL9` price `$0`.
4. Selecting `ZZ3` should make `SL9` price `$0` when `ZZ3` adds/includes `SL9`.
5. `PBC` requires `ZZ3` on convertible.
6. Preserve current direct pricing where appropriate:
   - `BCW` direct price and scoped override rules should not be erased.
7. Follow the proven Stingray/Grand Sport engine-cover pattern for dependencies vs replacement defaults.

**Evidence to inspect:** Skill/reference `engine-cover-structure-comparison.md` and existing Grand Sport/Stingray engine appearance rows/tests.

### Task 9: Fix exhaust WUB/NWI behavior

**Objective:** Remove the incorrect requirement that greys out `NWI` behind standard `WUB`.

**Workbook ownership:**
- `z06_options`
- `z06_rule_mapping`
- `z06_price_rules` only if pricing is affected

**Desired behavior:**
1. `WUB` is standard equipment on Z06.
2. `NWI` should be available by default.
3. The rule `NWI requires WUB` should be removed/deactivated for Z06 unless source evidence proves a different representation is needed.
4. Do not restore older WUB prices into Z sheets.

### Task 10: Fix exterior accents and GBA incompatibilities

**Objective:** Correct immediate exterior accent / paint incompatibility rows.

**Workbook ownership:**
- `z06_options`
- `z06_rule_mapping`
- `z06_exclusive_groups`
- `z06_exclusive_members`
- `color_overrides` only if the incompatibility is represented there

**Desired behavior:**
1. `EFY` should be included in the exterior accent grouped options.
2. Correction from prior draft: `EFY`, not `EDU`, is unavailable with `GBA`.
3. `EFY` is not available with `GBA`.
4. `ZYC` is not available with `GBA`.
5. `D84` is not available with `GBA`.
6. `D86` is not available with `GBA`.
7. Preserve existing default-selected exterior accent behavior unless explicitly changed.

### Task 11: Hide/deactivate suspension choices from the Z06 front end where appropriate

**Objective:** Prevent user changes to suspension when Z07 controls/contains the suspension behavior.

**Workbook ownership:**
- `z06_options`
- `z06_ovs`
- `z06_rule_mapping`
- section metadata if the whole suspension section should be display-only/internal

**Desired behavior:**
1. Suspension should not be user-changeable when `Z07` is selected.
2. Suspension options probably do not need to be exposed on the Z06 front end at all.
3. If suspension components are included by `Z07`, keep them as included/auto-added/internal selected output rows as appropriate, not as front-end choices.

**Boundary:** If hiding suspension requires a broader display-contract decision, keep the smallest safe representation in Pass 1 and defer deeper presentation cleanup to Pass 2.

### Task 12: Fix Z06 selectable=False source-contract mismatch

**Objective:** Prove and correct why Z06 rows that are `selectable=False` in `z06_options` can become selectable in the generated/runtime front end.

**Workbook/generator/runtime ownership to inspect:**
- `z06_options.selectable`
- `z06_options.section_id`
- `z06_ovs.status`
- `section_master.selection_mode`
- generated `form_choices`
- generated `form-output/inspection/z06-form-data-draft.json`
- generated `form-app/data.js`
- generic runtime choice rendering and `handleChoice()` behavior in `form-app/app.js`

**Desired behavior:**
1. If a source option row is non-selectable because it is standard/included/internal, the generated choice should not become customer-selectable unless a workbook-authored override explicitly says so.
2. Standard equipment can still appear in standard/included output, selected summaries, or auto-added components where appropriate.
3. The fix should be generic source-contract enforcement, not a Z06/RPO-specific UI suppression.
4. Add a test that starts from a known `z06_options.selectable=False` row and proves the generated/runtime contract respects it.

### Task 13: Deactivate unreleased front-end options V8X and RYQ

**Objective:** Remove unreleased Z06 options `V8X` and `RYQ` from the front end by making the workbook source rows inactive instead of hiding them in runtime code.

**Workbook ownership:**
- `z06_options`
- `z06_ovs`
- any associated rule/price rows only if needed to prevent dangling active references

**Desired behavior:**
1. `V8X` should be `active=False` in the workbook and absent from generated front-end choices.
2. `RYQ` should be `active=False` in the workbook and absent from generated front-end choices.
3. Any existing pricing placeholders for `V8X`/`RYQ` should remain recoverable in source history/notes if needed, but they should not be runtime-active until pricing/product treatment is approved.
4. Add a generated-data/runtime test proving neither RPO appears as an active front-end selectable choice.

### Task 14: Regenerate and verify Pass 1

**Objective:** Prove workbook rows drive the corrected runtime behavior.

**Commands after implementation:**

```sh
cd /Users/seandm/Projects/27vette
.venv/bin/python scripts/validate_workbook_package.py
.venv/bin/python scripts/generate_z06_form.py
.venv/bin/python scripts/generate_stingray_form.py
node --test tests/z06-runtime-rule-corrections.test.mjs
node --test tests/z06-contract-preview.test.mjs tests/z06-form-data-draft.test.mjs tests/z06-runtime-promotion.test.mjs
node --test tests/multi-model-runtime-switching.test.mjs
```

If generated/live app data changed, also run broader gates currently expected by `AGENTS.md` for generated runtime changes.

---

## Pass 1 acceptance criteria

Pass 1 is complete only when all of these are true:

1. No approved implementation step uses `apply_future_model_option_review.py` to rewrite Z option sheets.
2. The destructive writer is removed, deprecated, or guarded with tests/explicit emergency-only behavior.
3. Workbook validates with zero package issues.
4. Z07 is selectable before selecting T0F/T0G.
5. Selecting Z07 auto-adds J57 at `$0` and J57 is not removable while Z07 is selected.
6. Z07 then requires one of T0F/T0G.
7. T0F does not require J57.
8. PDB/PDD/PDF are mutually exclusive and consistently disable/replace each other.
9. PDB/PDD/PDF each require one of ROY/ROZ/STZ.
10. J57 selected/auto-added enables ROY/ROZ/STZ.
11. Wheel-and-brake packages deactivate aluminum wheels so only carbon wheels are available.
12. J57 makes J6A unavailable.
13. B6P zeroes D3V and SL9; ZZ3 zeroes SL9 when it adds/includes SL9; D3V/BCW behavior matches approved engine-cover logic.
14. PBC requires ZZ3 on convertible.
15. NWI is not blocked by a redundant WUB requirement on Z06.
16. EFY is in the exterior accent group; EFY, ZYC, D84, and D86 are unavailable with GBA.
17. Suspension is not user-changeable through the Z06 front end when Z07 owns/includes it, or the remaining suspension exposure is explicitly documented as deferred with reason.
18. Z06 source rows marked `selectable=False` do not become selectable in generated/runtime data unless a workbook-authored override explicitly permits it.
19. V8X and RYQ are workbook `active=False` and do not appear as active front-end choices.
20. Runtime tests fail before the fix and pass after the workbook/generator changes.
21. Generated artifacts are regenerated, not hand-edited.
22. No dealer submission endpoint/payload/Turnstile behavior changes.

---

## Pass 2 scope: interior/accessory presentation cleanup

Pass 2 should get its own implementation approval after Pass 1 lands.

### Pass 2 diagnosis to verify before edits

Inspect:

- `z06_options`
- `z06_ovs`
- `LZ_Interiors`
- `lt_interiors` only as structural comparison
- Grand Sport/Stingray interior component generation paths
- `form-output/inspection/z06-form-data-draft.json`
- `form-app/data.js`
- runtime rendering for Interior Trim / Interior Color / component sections

### Pass 2 requirements

1. `UQT` should appear as selectable only for `1LZ`.
2. `UQT` should be included for `2LZ` and `3LZ`, not shown as an extra standalone selectable option.
3. Stitching, two-tone, suede steering wheel, and similar interior component rows should not show as independent front-end options unless they are legitimate selected add-ons.
4. Interior selections should include their component effects in selected options / add-ons / auto-added output like Stingray and Grand Sport.
5. Correct Z06 3LZ seat pricing in workbook/generated data: `AH2=$0`, `AE4=$595`.
6. Interior/card rendering should show the actual charge on selectable cards for suede 3LZ and other chargeable component interiors; do not leave cards displaying `$0` when totals correctly include a charge.
7. `N3W` should never show as a front-end option.
8. `FA5` and `FA6` should be mutually exclusive.
9. Accessory packages should auto-add included components and zero out included component prices.
10. Package component zeroing should be modeled in `z06_price_rules`, not JavaScript.
11. Section presentation should be consistent with Stingray/Grand Sport unless a Z06-specific workbook row explicitly says otherwise.

### Pass 2 likely files/sheets

- `stingray_master.xlsx`
  - `z06_options`
  - `z06_ovs`
  - `z06_rule_mapping`
  - `z06_price_rules`
  - `z06_rule_groups`
  - `z06_rule_group_members`
  - `section_master`
  - `LZ_Interiors`
- Generator helpers only if they need a generic interior-component output improvement.
- Tests:
  - dedicated Z06 interior/accessory runtime tests
  - multi-model tests ensuring Stingray/Grand Sport remain stable

### Pass 2 validation commands

```sh
cd /Users/seandm/Projects/27vette
.venv/bin/python scripts/validate_workbook_package.py
.venv/bin/python scripts/generate_z06_form.py
.venv/bin/python scripts/generate_stingray_form.py
node --test tests/z06-runtime-rule-corrections.test.mjs
node --test tests/z06-interior-accessory-cleanup.test.mjs
node --test tests/z06-contract-preview.test.mjs tests/z06-form-data-draft.test.mjs tests/z06-runtime-promotion.test.mjs
node --test tests/multi-model-runtime-switching.test.mjs
```

---

## Constraints repeated back

- Workbook is source of truth for Z06 business rules.
- Prefer workbook rows over Python/JavaScript product exceptions.
- Do not hand-edit generated `form_*` sheets, `form-output/`, or `form-app/data.js`; regenerate them.
- Do not use row numbers as identities for workbook joins; use stable `option_id` and verify RPO.
- Do not overwrite restored Z06/ZR1/ZR1X prices or metadata.
- Do not restore old WUB prices into Z sheets; WUB is standard/no-price on Z models.
- Do not change dealer submission endpoint, payload shape, Turnstile behavior, or visual design unless a generic runtime defect forces it and is approved.
- Do not expand to ZR1/ZR1X in Pass 1.
- Do not do the interior/accessory makeover in Pass 1 unless a small row change is required to unblock the package/rule closure.
- Stop before workbook writes if Excel lock file `~$stingray_master.xlsx` exists.
- Workbook-writing scripts must save through `save_workbook_safely()` and reopen/verify on disk.

---

## Risks and non-goals

### Risks

- Existing generated Z06 artifacts are already modified in the working tree; implementation must diff-review outputs carefully to avoid mixing unrelated generated drift with intentional workbook changes.
- Some current runtime mechanics may treat `requires_any` as a preselection block. If so, a generic semantic adjustment may be required for post-selection grouped requirements.
- Suspension hiding may require distinguishing display-only/internal included components from selectable front-end choices.
- Engine-cover behavior can regress if modeled as hard includes instead of dependency/replacement/default semantics.
- Accessory/interior cleanup is broad enough to deserve a separate pass.

### Non-goals for Pass 1

- Do not fully redesign the Z06 interior trim/component system.
- Do not implement accessory package component auto-add/zeroing unless directly tied to a Pass 1 rule blocker.
- Do not promote or modify ZR1/ZR1X runtime behavior.
- Do not refactor runtime architecture.
- Do not add dependencies.
- Do not change app styling.

---

## Approval question

Approval to implement Pass 1 would authorize:

- guard/retire destructive future-model review script usage for this workflow,
- add failing Z06 runtime tests for the listed rule corrections,
- make targeted safe-save workbook source-row changes for Z06 rules/prices/groups/exclusives/option metadata,
- update the targeted Z06 safe-save script or create a more accurately named `apply_z06_runtime_rule_corrections.py`,
- regenerate Z06/live runtime artifacts through the approved generator path,
- run workbook validation and targeted runtime gates.

It would not authorize:

- the Pass 2 interior/accessory makeover,
- ZR1/ZR1X runtime changes,
- JavaScript hardcoded RPO exceptions,
- dealer submission changes,
- visual redesign.
