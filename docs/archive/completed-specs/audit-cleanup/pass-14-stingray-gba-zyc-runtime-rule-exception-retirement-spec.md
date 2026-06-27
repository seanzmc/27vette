# Pass 14 — Stingray GBA/ZYC Runtime-Rule-Exception Retirement Spec

Status: Implemented 2026-06-23.
Date: 2026-06-23
Recommended reasoning level for implementation agent: high.

Source context:

- `AGENTS.md`
- `docs/metadata-runtime-redundancy-6-23.md`
- `docs/Audit-route-map.md`
- `docs/audit-cleanup/pass-13-stingray-exhaust-runtime-rule-exception-retirement-spec.md`
- `27vette-workbook-guard` reference `segregated-workbook-behavior-retirement.md`

Note: the user-referenced `docs/metadata-runtime-redundancy.md` is not present in the current repo. Current evidence was taken from `docs/metadata-runtime-redundancy-6-23.md` and re-probed against the live repo/workbook before this spec.

## Goal

Retire only `runtime_rule_exceptions.ex_gba_zyc` by moving the Stingray GBA paint vs ZYC accent conflict into normal workbook rule-group ownership, while preserving current live Stingray behavior.

This pass must not change Z51/FE1/FE2 behavior, variant override sheets, direct-rule scope semantics, runtime JavaScript product logic, model promotion, dealer submission, or visual styling.

## Diagnosis

Change type for this spec: docs-only.

Change type for implementation: mixed workbook/data + generated artifacts + tests. Risk level: medium-high because the current behavior depends on interaction between a reverse direct exclude row and a generated `runtimeRuleExceptions` precedence helper.

Root cause: the current workbook expresses the GBA/ZYC conflict through a segregated exception sheet even though normal workbook graph ownership can express the intended source/target relationship.

Current active exception row:

- Sheet: `runtime_rule_exceptions`
- Row: `ex_gba_zyc`
- `model_key=stingray`
- `source_option_id=opt_gba_001` / GBA Black paint
- `target_option_id=opt_zyc_001` / ZYC Carbon Flash Mirrors and Spoiler
- `exception_type=remove_target_when_source_selected`
- wildcard body/trim/variant scopes
- disabled reason before implementation correction used stale ZYC copy; final grouped-exclusion copy below names the Carbon Flash painted mirrors and spoiler package correctly.

Current normal workbook graph is not equivalent without the exception:

- `rule_mapping.rule_opt_zyc_001_excludes_opt_gba_001` is a reverse direct excludes row: ZYC excludes GBA.
- Current runtime has a generated exception helper that lets GBA remain selectable while ZYC is selected and then removes ZYC after selecting GBA.
- If `ex_gba_zyc` were deleted without changing the reverse direct row, GBA would become disabled while ZYC is selected. That would change live behavior.
- `rule_groups.grp_gba_excludes_edu` already proves Stingray uses workbook-owned grouped exclusions from GBA for at least one accent conflict, but that existing group has EDU-specific disabled copy and should not be broadened in this pass.
- Z06 has an analogous normal grouped exclusion precedent: `z06_group_gba_excludes_accent_and_roof_choices` includes `opt_zyc_001` as a target of GBA.

Canonical owner for this pass: `rule_groups` + `rule_group_members` for a GBA -> ZYC `excludes_any` group, plus removal of the obsolete reverse direct ZYC -> GBA row and removal of the segregated exception row.

## Evidence inspected for this spec

Current branch/worktree:

- `git status --short --branch`: `## schema-ingestion-normalization...origin/main`
- `git merge-base --is-ancestor origin/main HEAD`: exit code 0.
- `~$stingray_master.xlsx`: absent during read-only probe.

Current documentation evidence:

- `docs/metadata-runtime-redundancy-6-23.md` reports `runtime_rule_exceptions` as 3 rows / 3 active and recommends `ex_gba_zyc` as the safest first implementation candidate.
- `docs/Audit-route-map.md:330-340` reports Pass 13 completed `ex_nwi_nga` retirement and recommends classifying/retiring remaining `ex_z51_fe1`, `ex_z51_fe2`, `ex_gba_zyc`, and variant override surfaces.

Current workbook evidence from read-only `openpyxl` inspection:

- `runtime_rule_exceptions` has exactly 3 active rows:
  - `ex_z51_fe1`: `opt_z51_001` removes `opt_fe1_001`.
  - `ex_z51_fe2`: `opt_z51_001` removes `opt_fe2_001`.
  - `ex_gba_zyc`: `opt_gba_001` removes `opt_zyc_001`.
- `stingray_options`:
  - `opt_gba_001`: RPO GBA, section `sec_pain_001`, active True, selectable True, price 0, display order 2.
  - `opt_zyc_001`: RPO ZYC, section `sec_spoi_001`, active True, selectable True, price 295, display order 15.
- `stingray_ovs`:
  - `opt_gba_001`: 6 rows, all `available`.
  - `opt_zyc_001`: 6 rows, all `available`.
- `rule_mapping` GBA/ZYC rows:
  - `rule_opt_zyc_001_excludes_opt_gba_001`: reverse direct exclude from ZYC to GBA.
  - `rule_opt_zyc_001_includes_opt_drg_001`: ZYC includes DRG. Preserve this row unchanged.
  - D84/D86/EFY reverse excludes to GBA also exist. They are outside this pass and must remain unchanged.
- `rule_groups` / `rule_group_members`:
  - Existing Stingray `grp_gba_excludes_edu` is `excludes_any` from GBA to EDU only.
  - Its disabled reason is EDU-specific, so this pass should not add ZYC to that group and thereby change EDU disabled copy.
- `z06_rule_groups` / `z06_rule_group_members`:
  - `z06_group_gba_excludes_accent_and_roof_choices` is a workbook-owned grouped exclusion from GBA to EFY, ZYC, D84, D86, and EDU. This is precedent, not a row to copy wholesale.

Current generated contract evidence from `form-output/runtime/stingray-runtime-contract.json`:

- `runtimeRuleExceptions` emits `[ex_gba_zyc, ex_z51_fe1, ex_z51_fe2]`.
- `ruleGroups` currently includes `grp_gba_excludes_edu` but no GBA -> ZYC grouped exclusion.
- `rules` currently emits `rule_opt_zyc_001_excludes_opt_gba_001` and `rule_opt_zyc_001_includes_opt_drg_001`.
- Generated GBA and ZYC choices are active/selectable/available for all six current Stingray variants.

Current runtime/test evidence:

- `form-app/app.js` has generic generated exception helpers at lines around 626-668.
- `disableReasonForChoice()` checks runtime exceptions before grouped exclusions.
- `selectedExcludesTarget()` and `excludesAnyReason()` already consume `excludes_any` rule groups generically.
- `reconcileSelections()` deletes selected choices whose `disableReasonForChoice(..., includeSelectedRequirements: false)` returns a reason, so a selected ZYC should be removed after GBA is selected when GBA -> ZYC grouped exclusion exists.
- `tests/stingray-form-regression.test.mjs` currently pins `ex_gba_zyc` in generated metadata and includes a runtime behavior test named `GBA replaces selected ZYC through workbook-generated runtime exception metadata`.

## Ownership decisions for this pass

### Move GBA -> ZYC conflict into a normal grouped exclusion

Add a new Stingray rule group rather than broadening `grp_gba_excludes_edu`.

Recommended new `rule_groups` row:

- `group_id=grp_gba_excludes_zyc`
- `group_type=excludes_any`
- `source_id=opt_gba_001`
- wildcard/blank scopes matching current Stingray grouped exclusion conventions
- `disabled_reason=ZYC Carbon Flash painted mirrors and spoiler package is not available with Black exterior paint.`
- `active=True`
- `notes=Workbook-owned grouped exclusion replacing retired runtime_rule_exceptions.ex_gba_zyc.`

Recommended new `rule_group_members` row:

- `group_id=grp_gba_excludes_zyc`
- `target_id=opt_zyc_001`
- `display_order=10`
- `active=True`

Rationale: grouped exclusion is a normal workbook owner already emitted and consumed by generic runtime code. A separate group preserves current EDU disabled copy from `grp_gba_excludes_edu`.

### Remove obsolete reverse direct rule for this behavior class

Delete only this `rule_mapping` row:

- `rule_opt_zyc_001_excludes_opt_gba_001`

Rationale: leaving the reverse direct row while deleting `ex_gba_zyc` would block GBA when ZYC is selected, changing current behavior. The new grouped exclusion will own the intended GBA -> ZYC disabled/removal direction.

Preserve all other GBA-related direct rules in this pass, including:

- `rule_opt_d84_001_excludes_opt_gba_001`
- `rule_opt_d86_001_excludes_opt_gba_001`
- `rule_opt_efy_001_excludes_opt_gba_001`
- `rule_opt_zyc_001_includes_opt_drg_001`

Those rows are different behavior classes and need separate classification before migration.

### Remove only `ex_gba_zyc` from `runtime_rule_exceptions`

Delete only this row:

- `runtime_rule_exceptions.ex_gba_zyc`

Leave these rows unchanged:

- `runtime_rule_exceptions.ex_z51_fe1`
- `runtime_rule_exceptions.ex_z51_fe2`

### Do not change runtime JavaScript unless parity fails

Expected implementation should need no runtime code change. Existing generic grouped-exclusion evaluation should preserve behavior after the workbook graph changes.

If implementation evidence proves grouped exclusions are not parity-equivalent, stop and report rather than adding an RPO/model-specific JavaScript branch.

## Exact files, sheets, and artifacts to change

Implementation may change:

- `stingray_master.xlsx`
  - `rule_groups`
  - `rule_group_members`
  - `rule_mapping`
  - `runtime_rule_exceptions`
- Generated artifacts from approved generation:
  - `form-output/runtime/stingray-runtime-contract.json`
  - `form-output/stingray-form-data.json`
  - `form-output/stingray-form-data.csv`
  - `form-app/data.js`
  - any other current Stingray artifacts that `scripts/generate_form.py --model stingray` rewrites; review and report exact diffs.
- Tests:
  - `tests/stingray-form-regression.test.mjs`
  - `tests/multi-model-runtime-switching.test.mjs` only if shared/multi-model runtime coverage needs an assertion update after preflight.
- Specs/docs for closure:
  - `docs/audit-cleanup/pass-14-stingray-gba-zyc-runtime-rule-exception-retirement-spec.md`
  - `docs/metadata-runtime-redundancy-6-23.md`
  - `docs/Audit-route-map.md`

Implementation must not change:

- `form-app/app.js` unless generic parity failure is proven and a smaller amended spec is approved.
- `variant_option_overrides`, `grandSport_variant_overrides`, `z06_variant_overrides`.
- `runtime_rule_exceptions.ex_z51_fe1` or `runtime_rule_exceptions.ex_z51_fe2`.
- Z06 or Grand Sport workbook source sheets.
- Dealer submission endpoint, payload shape, Turnstile behavior, or deployment paths.
- Visual CSS/HTML.

## Constraints

- Follow `AGENTS.md` spec-first rules. This spec was approved before implementation.
- Use current repo/workbook evidence only. Do not read or rely on archived `codex-context.md`.
- Workbook owns the business rule; do not hide the conflict in Python or JavaScript.
- Keep the implementation pass small and behavior-class-specific.
- Use `save_workbook_safely()` for workbook writes.
- Stop if `~$stingray_master.xlsx` exists or Excel appears to have the workbook open.
- Reopen/inspect the saved workbook on disk before claiming workbook edits landed.
- No new dependencies.
- No broad refactor.
- No live behavior change for Stingray, Grand Sport, or Z06.

## Expected generated-contract deltas

Expected intentional deltas after regeneration:

- `data.runtimeRuleExceptions` removes `ex_gba_zyc` and still contains exactly `ex_z51_fe1` and `ex_z51_fe2`.
- `data.ruleGroups` gains `grp_gba_excludes_zyc` with source `opt_gba_001`, group type `excludes_any`, and target `opt_zyc_001`.
- `data.rules` no longer contains `rule_opt_zyc_001_excludes_opt_gba_001`.
- `data.rules` still contains `rule_opt_zyc_001_includes_opt_drg_001`.
- GBA/ZYC generated choices remain active/selectable/available for all six current Stingray variants.
- Non-Stingray runtime contracts should be unchanged except registry timestamp/metadata noise from `generate_registry.py`, if any.

Unexpected deltas to stop on:

- Any change to option counts, section placement, price, active/selectable/status, or display order for GBA/ZYC.
- Any change to Z51/FE1/FE2 exception rows.
- Any Grand Sport/Z06 data change beyond timestamp-only registry churn.
- Any runtime JavaScript behavior/code change not explicitly justified by a parity failure.

## Required tests and runtime behavior proof

Update/add RED tests before the workbook edit where practical. The final tests should prove both source ownership and runtime behavior:

1. Generated/source ownership:
   - `ex_gba_zyc` is absent from `data.runtimeRuleExceptions`.
   - `ex_z51_fe1` and `ex_z51_fe2` remain present.
   - `grp_gba_excludes_zyc` is emitted as `excludes_any` from GBA to ZYC.
   - `rule_opt_zyc_001_excludes_opt_gba_001` is absent from generated `data.rules`.
   - `rule_opt_zyc_001_includes_opt_drg_001` remains present.
2. Runtime behavior:
   - With ZYC selected first, GBA remains selectable.
   - Selecting GBA removes ZYC from `state.selected` and `state.userSelected`.
   - While GBA is selected, ZYC has disabled reason `ZYC Carbon Flash painted mirrors and spoiler package is not available with Black exterior paint.`
   - Clicking ZYC while GBA is selected does not re-add ZYC.
   - ZYC still includes DRG when ZYC is selected on a non-GBA path.
3. No adjacent behavior drift:
   - Existing Z51/FE1/FE2 exception behavior remains covered.
   - Existing EDU/GBA grouped exclusion copy/behavior remains unchanged.
   - Multi-model runtime switching stays green.

## Validation plan

Preflight:

```sh
git status --short --branch
test ! -e '~$stingray_master.xlsx'
```

After workbook edit and on-disk verification:

```sh
.venv/bin/python scripts/validate_workbook_package.py stingray_master.xlsx
.venv/bin/python scripts/generate_form.py --model stingray
.venv/bin/python scripts/generate_registry.py
.venv/bin/python scripts/validate_workbook_schema.py stingray_master.xlsx
node --test tests/stingray-form-regression.test.mjs
node --test tests/stingray-generator-stability.test.mjs
node --test tests/multi-model-runtime-switching.test.mjs
```

Generated-contract review:

- Compare a pre-change copy of `form-output/runtime/stingray-runtime-contract.json` to the regenerated contract with `node scripts/compare-generated-contracts.mjs` and classify the approved deltas above.
- Probe `form-app/data.js` to ensure promoted runtime data matches the regenerated Stingray contract and no Grand Sport/Z06 payload drift was introduced.

Local browser/manual verification required before final handoff:

- Serve `form-app` locally.
- Stingray coupe 1LT path:
  - select ZYC first;
  - confirm GBA remains clickable;
  - select GBA;
  - confirm ZYC is removed/disabled and cannot be clicked back in;
  - confirm the disabled reason matches the current copy.
- Smoke model switching to Grand Sport and Z06 to confirm no obvious runtime break.

## Risks and mitigations

- Risk: deleting `ex_gba_zyc` while leaving the reverse direct rule changes behavior by making GBA disabled when ZYC is selected.
  - Mitigation: delete `rule_opt_zyc_001_excludes_opt_gba_001` in the same approved pass and add tests for GBA-over-ZYC selection.
- Risk: broadening `grp_gba_excludes_edu` would change EDU disabled copy.
  - Mitigation: add a separate `grp_gba_excludes_zyc` group with ZYC-specific copy.
- Risk: tests pass on generated data but local click behavior regresses.
  - Mitigation: keep runtime click assertions and run browser/manual smoke.
- Risk: generated registry refresh introduces unrelated Grand Sport/Z06 diffs.
  - Mitigation: inspect generated diffs and stop/restore unrelated drift.

## Non-goals

- Do not retire `ex_z51_fe1` or `ex_z51_fe2`.
- Do not migrate variant override sheets.
- Do not consolidate all GBA accent/roof conflicts.
- Do not delete `runtime_action`, change direct-rule scope semantics, or trim generated rule payload fields.
- Do not change runtime JavaScript product behavior.
- Do not change dealer submission behavior.

## Completion evidence

Implemented 2026-06-23 after approval.

Changed workbook sheets:

- `rule_groups`: added `grp_gba_excludes_zyc` as an `excludes_any` group from `opt_gba_001` to `opt_zyc_001`.
- `rule_group_members`: added `grp_gba_excludes_zyc` member `opt_zyc_001`.
- `rule_mapping`: removed only `rule_opt_zyc_001_excludes_opt_gba_001`; preserved `rule_opt_zyc_001_includes_opt_drg_001` and other GBA-related direct rules.
- `runtime_rule_exceptions`: removed only `ex_gba_zyc`; preserved `ex_z51_fe1` and `ex_z51_fe2`.

Changed files/artifacts:

- `stingray_master.xlsx`
- `form-output/runtime/stingray-runtime-contract.json`
- `form-output/stingray-form-data.json`
- `form-app/data.js`
- `tests/stingray-form-regression.test.mjs`
- `tests/stingray-generator-stability.test.mjs`
- `docs/audit-cleanup/pass-14-stingray-gba-zyc-runtime-rule-exception-retirement-spec.md`
- `docs/metadata-runtime-redundancy-6-23.md`
- `docs/Audit-route-map.md`

Workbook save and verification:

- Preflight branch/status: `schema-ingestion-normalization...origin/main` with only the Pass 14 spec untracked before implementation edits.
- Excel lock file: absent.
- Workbook save used `save_workbook_safely()`.
- Backup created: `backups/stingray_master-20260623-162549.xlsx`.
- On-disk workbook verification confirmed `runtime_rule_exceptions` now contains only `ex_z51_fe1` and `ex_z51_fe2`; reverse direct rule `rule_opt_zyc_001_excludes_opt_gba_001` is absent; `rule_opt_zyc_001_includes_opt_drg_001` remains; `grp_gba_excludes_zyc` group/member exist.

Generated-contract deltas:

- `runtimeRuleExceptions`: removed `ex_gba_zyc`; retained `ex_z51_fe1` and `ex_z51_fe2`.
- `ruleGroups`: added `grp_gba_excludes_zyc` with target `opt_zyc_001` and corrected disabled reason `ZYC Carbon Flash painted mirrors and spoiler package is not available with Black exterior paint.`
- `rules`: removed `rule_opt_zyc_001_excludes_opt_gba_001`; retained `rule_opt_zyc_001_includes_opt_drg_001`.
- Compatibility rule count changed from 141 to 140 because the reverse direct rule was intentionally removed.
- GBA/ZYC choices remained active/selectable/available across all six Stingray variants.

Gates run:

```sh
.venv/bin/python scripts/validate_workbook_package.py stingray_master.xlsx
.venv/bin/python scripts/generate_form.py --model stingray
.venv/bin/python scripts/generate_registry.py
.venv/bin/python scripts/validate_workbook_schema.py stingray_master.xlsx
node --test tests/stingray-form-regression.test.mjs
node --test tests/stingray-generator-stability.test.mjs
node --test tests/multi-model-runtime-switching.test.mjs
```

All listed gates passed after expected test updates.

Local browser/runtime proof:

- Served `form-app` at `http://127.0.0.1:8000/`.
- Stingray coupe 1LT runtime proof showed:
  - ZYC selected first leaves GBA selectable.
  - Selecting GBA removes ZYC from both `state.selected` and `state.userSelected`.
  - ZYC remains disabled with `ZYC Carbon Flash painted mirrors and spoiler package is not available with Black exterior paint.`
  - Clicking ZYC while GBA is selected does not re-add ZYC.
- Browser smoke switching rendered Grand Sport and Z06 order forms without console errors.

What stayed unchanged:

- Runtime JavaScript code.
- Z51/FE1/FE2 exception behavior.
- Variant override sheets.
- Grand Sport and Z06 workbook source sheets.
- Visual styling and HTML.
- Dealer submission endpoint, payload shape, and Turnstile behavior.

Residual follow-up:

- Remaining `runtime_rule_exceptions` rows are `ex_z51_fe1` and `ex_z51_fe2`; handle them in a separate spec-first suspension/default ownership pass.
- Variant override sheets remain medium-high risk and should be classified separately from the Z51/FE1/FE2 exception behavior.
