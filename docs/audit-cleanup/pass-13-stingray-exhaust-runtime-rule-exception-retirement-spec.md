# Pass 13 — Stingray Exhaust Runtime-Rule-Exception Retirement Spec

Status: Implemented 2026-06-23.
Date: 2026-06-22
Recommended reasoning level for implementation agent: high.
Source context:

- `docs/Audit-route-map.md`
- `docs/audit-cleanup/pass-12-grand-sport-exhaust-default-replacement-ownership-spec.md`
- `docs/audit-cleanup/pass-8-direct-rule-field-classification-report.md`
- `27vette-workbook-guard` reference `segregated-workbook-behavior-retirement.md`
- `27vette-workbook-guard` reference `dependent-replacement-defaults.md`

## Goal

Retire Stingray `runtime_rule_exceptions.ex_nwi_nga` only if normal workbook rule/default/exclusive-group ownership can preserve current customer-facing NGA/NWI/WUB behavior.

This is the narrow follow-up to Pass 12. Pass 12 proved the same product relationship can be owned by normal Grand Sport workbook metadata: `gs_excl_exhaust_path` plus `gs_default_nga_unless_nwi`, while WUB remains only the NWI dependency/enabler. This pass applies that already-proven ownership shape to Stingray and removes only the corresponding segregated runtime exception row.

## Diagnosis

Change type for this spec: docs-only.

Change type for implementation: mixed workbook/data + generated artifacts + tests. Risk level: medium-high because this touches default selected state, dependency disabled-state, required peer replacement, generated runtime metadata, and local runtime click behavior.

Root cause: Stingray currently expresses the NGA/NWI relationship through a segregated workbook behavior sheet instead of the normal rule/default/exclusive-group graph:

- `runtime_rule_exceptions.ex_nwi_nga`
  - `source_option_id=opt_nwi_001` / NWI
  - `target_option_id=opt_nga_001` / NGA
  - `exception_type=remove_target_when_source_selected`
  - wildcard body/trim/variant scopes
  - active True

The rest of the relationship already lives in normal workbook source rows:

- `rule_mapping.rule_opt_nwi_001_requires_opt_wub_001`: NWI requires WUB.
- `default_selection_rules.default_nga`: NGA defaults/restores unless NWI is selected.
- `stingray_options` has active/selectable NGA, WUB, and NWI rows in `sec_exha_001` with display orders 10/20/30.
- `stingray_ovs` marks NGA standard on all six Stingray variants and WUB/NWI available on all six Stingray variants.

What is missing: no active Stingray exclusive group currently owns NGA/NWI as exhaust-tip peers. Generated `form-output/runtime/stingray-runtime-contract.json` emits `ex_nwi_nga` in `runtimeRuleExceptions`, emits `default_nga`, emits NWI -> WUB as a direct `requires` rule, and emits no exhaust exclusive group for NGA/NWI.

Product behavior to preserve exactly:

- NGA and NWI are related exhaust-tip choices: only one can be selected.
- One of NGA/NWI should remain selected for the current Stingray behavior path.
- NWI requires WUB.
- NGA has no reliance on WUB. NGA is standard/default either way.
- Selecting WUB alone must not remove NGA.
- Selecting NWI after WUB is selected must replace NGA.
- Removing NWI must restore NGA.
- Removing WUB while NWI is selected must invalidate/remove NWI and restore NGA.

That means WUB is an enabler/dependency for NWI, not a peer of NGA. Do not model WUB and NGA as mutually exclusive. Do not make NGA require WUB. Do not make WUB remove NGA.

## Evidence inspected for this spec

Current branch/worktree:

- `git status --short --branch` reported branch `schema-ingestion-normalization...origin/main`.
- `git merge-base --is-ancestor origin/main HEAD` returned exit code 0, so current HEAD contains `origin/main` and the pass is not starting from a stale base.
- Spec-writing verification saw only the new Pass 13 docs changes in the final worktree status. Implementation preflight must re-check dirty state before workbook edits.

Current workbook evidence from read-only `openpyxl` inspection:

- `stingray_options`:
  - `opt_nga_001` / NGA: active True, selectable True, `section_id=sec_exha_001`, display order 10.
  - `opt_wub_001` / WUB: active True, selectable True, `section_id=sec_exha_001`, display order 20.
  - `opt_nwi_001` / NWI: active True, selectable True, `section_id=sec_exha_001`, display order 30.
- `stingray_ovs`:
  - `opt_nga_001` is `standard` for `1lt_c07`, `2lt_c07`, `3lt_c07`, `1lt_c67`, `2lt_c67`, and `3lt_c67`.
  - `opt_wub_001` is `available` for all six current Stingray variants.
  - `opt_nwi_001` is `available` for all six current Stingray variants.
- `rule_mapping`:
  - `rule_opt_nwi_001_requires_opt_wub_001` exists and preserves NWI -> WUB dependency.
  - There is no direct NWI -> NGA `runtime_action=replace` row to retire.
- `exclusive_groups` / `exclusive_group_members`:
  - no active Stingray group currently includes NGA/NWI as exhaust-tip peers.
- `default_selection_rules`:
  - `default_nga` exists with `target_option_id=opt_nga_001`, `condition_type=unless_selected_rpo`, `condition_id=NWI`, wildcard scopes, active True.
- `runtime_rule_exceptions`:
  - `ex_nwi_nga` exists and is active.

Current generated contract evidence:

- `form-output/runtime/stingray-runtime-contract.json` emits runtime exceptions:
  - `ex_gba_zyc`
  - `ex_nwi_nga`
  - `ex_z51_fe1`
  - `ex_z51_fe2`
- It emits `defaultSelectionRules.default_nga` for NGA.
- It emits `rule_opt_nwi_001_requires_opt_wub_001` as NWI -> WUB.
- It emits no Stingray NGA/NWI exclusive group.

Current runtime/test evidence:

- `form-app/app.js` still has generic `runtimeRuleExceptions` helpers:
  - `generatedRuleExceptions()`
  - `runtimeExceptionForTarget()`
  - `runtimeExceptionAllowsCandidateOverSelectedTarget()`
  - `removeRuntimeExceptionTargets()`
- `form-app/app.js` also has the generic required-exclusive/default fallback behavior added by Pass 12. This pass should rely on that generic behavior; it must not add Stingray/RPO-specific JavaScript.
- `tests/stingray-form-regression.test.mjs` currently expects `ex_nwi_nga` in `data.runtimeRuleExceptions` along with `ex_gba_zyc`, `ex_z51_fe1`, and `ex_z51_fe2`.
- `tests/multi-model-runtime-switching.test.mjs` already contains the Grand Sport NGA/NWI/WUB runtime behavior pattern from Pass 12. This pass should add equivalent Stingray coverage, not rely only on generated-data assertions.

## Ownership decisions for this pass

### Model NGA/NWI as the Stingray exhaust-tip peer group

Target decision:

- Add or activate a Stingray exclusive group for only the true exhaust-tip peers:
  - recommended `group_id=excl_exhaust_path`, unless preflight finds an existing inactive Stingray naming convention that should be reused.
  - `selection_mode=required_single_within_group`.
  - `active=True`.
  - notes should state that NGA and NWI are mutually exclusive required exhaust-tip choices; NWI still requires WUB; WUB is not a peer.
- Active members should be exactly:
  - `opt_nga_001`, display order 10.
  - `opt_nwi_001`, display order 30.
- Do not add `opt_wub_001` as an active group member.

Rationale: the business relationship is NGA-vs-NWI. WUB only satisfies the NWI prerequisite. Keeping WUB out of the peer group preserves the product decision that WUB alone does not replace the standard NGA tip.

### Preserve WUB as NWI dependency/enabler only

Keep this row unchanged:

| behavior | row | reason |
|---|---|---|
| NWI requires WUB | `rule_mapping.rule_opt_nwi_001_requires_opt_wub_001` | NWI is only valid when WUB is selected or included. This is not replaced by the NGA/NWI exclusive group. |

Do not add any NGA -> WUB dependency, WUB -> NGA replacement, WUB -> NWI default, or WUB/NGA exclusive-group relationship.

### Preserve NGA default ownership

Keep `default_selection_rules.default_nga` active unless preflight proves its shape has changed. It should remain the default/restoration rule for NGA:

- `target_option_id=opt_nga_001`
- `condition_type=unless_selected_rpo`
- `condition_id=NWI`
- wildcard body/trim/variant scopes
- active True

If runtime parity proves `default_nga` plus an active required NGA/NWI group is insufficient, stop and report before adding a new condition type, duplicating `default_nga`, or patching runtime with RPO-specific logic.

### Retire only `runtime_rule_exceptions.ex_nwi_nga`

Delete or deactivate this single exception row only after generated-data and local-runtime tests prove the active Stingray NGA/NWI group plus existing default/dependency metadata is behavior-equivalent:

| current workbook row | source | target | current owner | canonical owner after pass |
|---|---|---|---|---|
| `runtime_rule_exceptions.ex_nwi_nga` | `opt_nwi_001` / NWI | `opt_nga_001` / NGA | segregated runtime exception | Stingray exhaust exclusive group with NGA/NWI members plus `default_selection_rules.default_nga`; WUB remains NWI prerequisite |

If deleting/deactivating this row makes local runtime behavior diverge, restore the row and close the pass as a characterization finding rather than masking the regression in JavaScript.

## Exact files/sheets/artifacts to change if approved

Source workbook:

- `stingray_master.xlsx`
  - `exclusive_groups`
  - `exclusive_group_members`
  - `runtime_rule_exceptions`

Source workbook rows to inspect but preserve unless preflight proves mismatch:

- `stingray_options.opt_nga_001`
- `stingray_options.opt_wub_001`
- `stingray_options.opt_nwi_001`
- `stingray_ovs` rows for NGA/WUB/NWI across all six Stingray variants
- `rule_mapping.rule_opt_nwi_001_requires_opt_wub_001`
- `default_selection_rules.default_nga`

Generated artifacts expected to refresh:

- `form-output/runtime/stingray-runtime-contract.json`
- `form-output/stingray-form-data.json`
- `form-output/stingray-form-data.csv`
- `form-app/data.js`

Tests expected to change:

- `tests/stingray-form-regression.test.mjs`
- `tests/multi-model-runtime-switching.test.mjs`

Docs/status closure to update after implementation:

- `docs/audit-cleanup/pass-13-stingray-exhaust-runtime-rule-exception-retirement-spec.md`
- `docs/Audit-route-map.md`

Do not change in this pass:

- `form-app/app.js`, unless preflight RED proves existing generic Pass 12 runtime behavior is insufficient. If that happens, stop and update this spec before implementation.
- `grandSport_*` workbook sheets.
- `z06_*` workbook sheets.
- `runtime_rule_exceptions.ex_z51_fe1`.
- `runtime_rule_exceptions.ex_z51_fe2`.
- `runtime_rule_exceptions.ex_gba_zyc`.
- `variant_option_overrides` or model-scoped variant override sheets.
- `runtime_action` workbook columns or generated payload field names.
- direct-rule `scopeMatches()` / body-style semantics.
- dealer submission code, endpoint, payload shape, or Turnstile behavior.

## Constraints

- Visual preservation: no UI/HTML/CSS/runtime-rendering changes.
- No refactor.
- No new dependencies.
- Workbook remains source of truth; use normal workbook exclusive-group/default/dependency metadata, not Stingray/RPO-specific JavaScript.
- Use `save_workbook_safely()` and verify the workbook saved on disk.
- Close/avoid Excel. Stop if `~$stingray_master.xlsx` exists.
- Do not hand-edit generated artifacts; regenerate from workbook source.
- Do not delete the `runtime_rule_exceptions` sheet in this pass.
- Do not claim the whole `runtime_rule_exceptions` surface is retired; only `ex_nwi_nga` is in scope.
- Do not model WUB as an NGA/NWI peer.
- Do not make NGA depend on WUB.
- Do not let selecting WUB alone remove NGA.
- Do not make NWI selectable before WUB is selected or included.
- Do not bundle Z51 suspension exception cleanup, GBA/ZYC cleanup, variant override cleanup, or Z06 brake/default replacement cleanup.

## Implementation plan if approved

1. Preflight.

   ```sh
   cd /Users/seandm/Projects/27vette
   git status --short --branch
   git merge-base --is-ancestor origin/main HEAD
   test ! -e './~$stingray_master.xlsx'
   .venv/bin/python scripts/validate_workbook_package.py stingray_master.xlsx
   ```

   Confirm any dirty files are pre-existing and non-overlapping. Do not proceed with workbook writes if unrelated dirty files overlap the approved implementation paths.

2. Snapshot current generated Stingray artifacts.

   ```sh
   mkdir -p /tmp/27vette-pass13-before
   cp form-output/runtime/stingray-runtime-contract.json /tmp/27vette-pass13-before/
   cp form-output/stingray-form-data.json /tmp/27vette-pass13-before/
   cp form-output/stingray-form-data.csv /tmp/27vette-pass13-before/
   cp form-app/data.js /tmp/27vette-pass13-before/data.js
   ```

3. Read-only confirm candidate row identity before workbook write.

   Assert exact row identities:

   - `stingray_options.opt_nga_001`: RPO NGA, active True, selectable True, `section_id=sec_exha_001`, display order 10.
   - `stingray_options.opt_wub_001`: RPO WUB, active True, selectable True, `section_id=sec_exha_001`, display order 20.
   - `stingray_options.opt_nwi_001`: RPO NWI, active True, selectable True, `section_id=sec_exha_001`, display order 30.
   - `stingray_ovs` has NGA standard and WUB/NWI available for all six current Stingray variants.
   - `rule_mapping.rule_opt_nwi_001_requires_opt_wub_001`: `opt_nwi_001` requires `opt_wub_001`, blank `body_style_scope`, active/default runtime action.
   - `default_selection_rules.default_nga`: active Stingray NGA default unless NWI.
   - `runtime_rule_exceptions.ex_nwi_nga`: active `remove_target_when_source_selected` from NWI to NGA with wildcard scopes.
   - Current Stingray exclusive group state, including whether an inactive or stale exhaust group already exists.

   Stop if any identity differs; update the spec or ask for approval before adapting the pass.

4. Add RED/characterization test changes before workbook write.

   Update tests so they fail against the current source state but express the target canonical ownership:

   - `tests/stingray-form-regression.test.mjs` should expect no `ex_nwi_nga` in generated `runtimeRuleExceptions` after the workbook change.
   - It should continue expecting `ex_gba_zyc`, `ex_z51_fe1`, and `ex_z51_fe2` until separate passes retire or reclassify them.
   - It should assert an active Stingray exhaust exclusive group with option IDs exactly `["opt_nga_001", "opt_nwi_001"]` and `selection_mode="required_single_within_group"`.
   - It should assert WUB is not an exhaust peer.
   - It should assert NWI -> WUB remains an active direct `requires` rule.
   - It should assert `default_nga` remains in `defaultSelectionRules`.
   - `tests/multi-model-runtime-switching.test.mjs` should add Stingray local-runtime behavior coverage equivalent to the Grand Sport Pass 12 behavior:
     - initial reset/reconcile selects NGA;
     - NWI is disabled before WUB;
     - selecting WUB leaves NGA selected and enables NWI;
     - selecting NWI removes NGA;
     - clicking/removing NWI restores NGA;
     - removing WUB from the NWI path removes invalid NWI and restores NGA;
     - WUB is never treated as an NGA/NWI peer.

5. Write the workbook through a small safe-save script.

   Required script behavior:

   - Load `stingray_master.xlsx`.
   - Stop if `~$stingray_master.xlsx` exists.
   - Add or update one Stingray `exclusive_groups` parent row for the NGA/NWI peer group.
   - Add or update two active `exclusive_group_members` rows for `opt_nga_001` and `opt_nwi_001`.
   - Ensure no active `exclusive_group_members` row for that group contains `opt_wub_001`.
   - Delete or deactivate only `runtime_rule_exceptions.ex_nwi_nga`.
   - Leave `ex_z51_fe1`, `ex_z51_fe2`, and `ex_gba_zyc` unchanged.
   - Leave `default_selection_rules.default_nga` unchanged.
   - Leave NWI -> WUB `rule_mapping` unchanged.
   - Save through `save_workbook_safely()`.

6. Reopen and verify workbook on disk.

   Use `.venv/bin/python` and `openpyxl` read-only inspection to assert:

   - the Stingray exhaust group is active and has expected selection mode;
   - active members are exactly `opt_nga_001` and `opt_nwi_001`;
   - WUB is not active in that group;
   - `runtime_rule_exceptions.ex_nwi_nga` is absent or inactive, according to the approved write decision;
   - all other runtime exception rows remain active unchanged;
   - `default_nga` and NWI -> WUB still exist unchanged.

7. Regenerate artifacts.

   ```sh
   .venv/bin/python scripts/generate_form.py --model stingray
   .venv/bin/python scripts/generate_registry.py
   ```

8. Review generated diffs.

   Expected generated behavior drift:

   - Stingray runtime contract gains one active NGA/NWI exclusive group.
   - Stingray runtime contract loses only `runtimeRuleExceptions.ex_nwi_nga`.
   - `default_nga` remains.
   - NWI -> WUB remains.
   - No Grand Sport/Z06 generated behavior changes except registry timestamp or embedding churn caused by `generate_registry.py`.

   Compare behavior fields with a targeted Node probe rather than relying only on whole-contract equality, because this pass intentionally changes generated contract shape.

9. Run targeted gates.

   ```sh
   .venv/bin/python scripts/validate_workbook_package.py stingray_master.xlsx
   .venv/bin/python scripts/validate_workbook_schema.py stingray_master.xlsx
   node --test tests/stingray-form-regression.test.mjs
   node --test tests/multi-model-runtime-switching.test.mjs
   git diff --check
   ```

   If `form-app/app.js` unexpectedly changes, also run:

   ```sh
   node --test tests/z06-runtime-rule-corrections.test.mjs
   node --test tests/z06-performance-package-interactions.test.mjs
   ```

10. Browser/local-runtime smoke before final handoff.

    Serve the app and verify Stingray manually or through the runtime harness:

    - Initial Stingray Coupe 1LT: NGA selected, NWI unselected, WUB unselected.
    - NWI disabled before WUB is selected and cites WUB/Quad Center Exit dependency.
    - Select WUB: WUB selected, NGA remains selected, NWI enabled.
    - Select NWI: NWI selected, NGA removed.
    - Remove NWI: NGA restored.
    - Remove WUB from the NWI path: WUB removed, invalid NWI removed, NGA restored, NWI disabled again.
    - Confirm Grand Sport still follows the Pass 12 behavior.

11. Close the spec and route map.

    Before final handoff, update:

    - `docs/audit-cleanup/pass-13-stingray-exhaust-runtime-rule-exception-retirement-spec.md`
    - `docs/Audit-route-map.md`

    Record completion date, files/sheets/artifacts changed, gate results, residual risks, and the next recommended pass.

## Risks

- Generated-data assertions can pass while click behavior regresses. The local runtime path is mandatory.
- Existing generic runtime behavior from Pass 12 may not fully cover Stingray if Stingray source data differs in subtle ways. If so, stop and report rather than patching a Stingray-specific JavaScript branch.
- Deleting the wrong `runtime_rule_exceptions` row could change Z51 suspension or GBA/ZYC behavior. This pass must touch only `ex_nwi_nga`.
- Adding WUB to the exclusive group would make WUB incorrectly replace NGA.
- Regeneration may update `form-app/data.js`; review diffs so expected Stingray behavior changes do not hide unrelated workbook or registry drift.
- Pre-existing dirty files can pollute review context; leave unrelated user work untouched and report it separately.

## Non-goals

- Do not retire the whole `runtime_rule_exceptions` sheet.
- Do not retire or classify `ex_z51_fe1`, `ex_z51_fe2`, or `ex_gba_zyc`.
- Do not retire `variant_option_overrides` or model-scoped variant override sheets.
- Do not normalize Stingray exclusive-group ID naming beyond the one new exhaust group needed for this behavior.
- Do not migrate Z06 exhaust/brake/default behavior.
- Do not delete `runtime_action` fields or change direct-rule runtime matching semantics.
- Do not change dealer submission behavior.

## Validation plan

Required implementation gates:

```sh
.venv/bin/python scripts/validate_workbook_package.py stingray_master.xlsx
.venv/bin/python scripts/validate_workbook_schema.py stingray_master.xlsx
.venv/bin/python scripts/generate_form.py --model stingray
.venv/bin/python scripts/generate_registry.py
node --test tests/stingray-form-regression.test.mjs
node --test tests/multi-model-runtime-switching.test.mjs
git diff --check
```

Required workbook/generated probes:

- Reopen `stingray_master.xlsx` and verify the exact source rows listed above.
- Probe `form-output/runtime/stingray-runtime-contract.json` and `form-app/data.js` for:
  - `ex_nwi_nga` absent;
  - `ex_gba_zyc`, `ex_z51_fe1`, and `ex_z51_fe2` still present;
  - `default_nga` still present;
  - NWI -> WUB direct rule still present;
  - new Stingray NGA/NWI exclusive group present and WUB absent from that group.

Required local runtime/browser smoke:

- Stingray NGA/NWI/WUB path as described in step 10.
- Grand Sport NGA/NWI/WUB path still green.

## Implementation result

Implemented 2026-06-23.

Workbook sheets changed:

- `exclusive_groups`: added active `excl_exhaust_path` with `selection_mode=required_single_within_group`.
- `exclusive_group_members`: added active `excl_exhaust_path` members `opt_nga_001` and `opt_nwi_001`; WUB is not a member.
- `runtime_rule_exceptions`: removed only `ex_nwi_nga`; `ex_z51_fe1`, `ex_z51_fe2`, and `ex_gba_zyc` remain active.

Runtime/source files changed:

- `form-app/app.js`: updated the generic required-exclusive fallback check so generated default-selection rules can restore a required exclusive-group peer even when the fallback choice is not emitted as `display_behavior=default_selected`. This was required because Stingray `default_nga` is a generated default rule while Grand Sport also emits NGA as default-selected choice metadata. The change is generic and not Stingray/RPO-specific.

Generated artifacts refreshed:

- `form-output/runtime/stingray-runtime-contract.json`
- `form-output/stingray-form-data.json`
- `form-app/data.js`

Generated behavior changed as intended:

- `ex_nwi_nga` is absent from Stingray `runtimeRuleExceptions`.
- `excl_exhaust_path` is emitted with exactly `opt_nga_001` and `opt_nwi_001` and `required_single_within_group`.
- `default_nga` remains emitted.
- NWI -> WUB remains emitted as a direct `requires` rule.
- `ex_z51_fe1`, `ex_z51_fe2`, and `ex_gba_zyc` remain emitted.

Tests changed:

- `tests/stingray-form-regression.test.mjs`: asserts `ex_nwi_nga` retirement and new canonical Stingray exhaust group/default/dependency ownership.
- `tests/multi-model-runtime-switching.test.mjs`: adds Stingray local-runtime coverage for WUB enabling NWI, WUB not replacing NGA, NWI replacing/restoring NGA, and WUB removal invalidating NWI/restoring NGA.
- `tests/stingray-generator-stability.test.mjs`: updates the closed-out Stingray rule count from 144 to 141 after removing the emitted runtime exception row payload.

Validation results:

- Preflight RED tests failed for the intended reason before workbook changes:
  - `node --test --test-name-pattern 'runtime defaults and RPO exceptions' tests/stingray-form-regression.test.mjs` failed because `ex_nwi_nga` was still emitted.
  - `node --test --test-name-pattern 'exclusive groups are model-scoped|Stingray WUB enables NWI' tests/multi-model-runtime-switching.test.mjs` failed because the Stingray exhaust group was not emitted.
- Workbook backup from safe-save: `backups/stingray_master-20260623-000004.xlsx`.
- Reopened workbook verification passed for the new group, members, removed exception row, preserved remaining exception rows, preserved `default_nga`, and preserved NWI -> WUB.
- `.venv/bin/python scripts/generate_form.py --model stingray` passed with 0 validation errors.
- `.venv/bin/python scripts/generate_registry.py` passed.
- Generated contract probe passed for expected exception/group/default/rule drift.
- `.venv/bin/python scripts/validate_workbook_package.py stingray_master.xlsx` passed.
- `.venv/bin/python scripts/validate_workbook_schema.py stingray_master.xlsx` passed.
- `node --test tests/stingray-form-regression.test.mjs` passed: 87/87.
- `node --test tests/stingray-generator-stability.test.mjs` passed: 13/13.
- `node --test tests/multi-model-runtime-switching.test.mjs` passed: 46/46.
- Because `form-app/app.js` changed generically, adjacent Z06 runtime gates were run:
  - `node --test tests/z06-runtime-rule-corrections.test.mjs` passed: 14/14.
  - `node --test tests/z06-performance-package-interactions.test.mjs` passed: 17/17.
- `git diff --check` passed.

Manual verification still pending:

- No separate browser smoke was run. The local runtime harness now covers the required Stingray and Grand Sport NGA/NWI/WUB click behavior.

Residual follow-up:

- `runtime_rule_exceptions` still contains `ex_z51_fe1`, `ex_z51_fe2`, and `ex_gba_zyc`; those need classification before migration or deletion.
- `variant_option_overrides` and model-scoped variant override sheets remain separate architecture-risk surfaces and were not touched.

## Recommended next pass after this one

After Pass 13, write a report-only classification for the remaining segregated behavior rows:

- `runtime_rule_exceptions.ex_z51_fe1`
- `runtime_rule_exceptions.ex_z51_fe2`
- `runtime_rule_exceptions.ex_gba_zyc`
- `variant_option_overrides` and model-scoped variant override rows

Do not implement that broader retirement until each row is mapped to a canonical owner and the required parity tests are known.
