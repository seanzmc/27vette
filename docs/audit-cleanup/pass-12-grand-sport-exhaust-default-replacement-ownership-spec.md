# Pass 12 — Grand Sport Exhaust Default Replacement Ownership Spec

Status: Spec only. Do not implement until approved.
Date: 2026-06-22
Recommended reasoning level for implementation agent: high.
Source report: `docs/audit-cleanup/pass-8-direct-rule-field-classification-report.md`.
Previous related passes:

- `docs/audit-cleanup/pass-9-body-style-scope-retirement-spec.md`
- `docs/audit-cleanup/pass-10-stingray-spoiler-replacement-ownership-spec.md`
- `docs/audit-cleanup/pass-11-grand-sport-package-default-replacement-ownership-spec.md`

## Goal

Retire the remaining Grand Sport exhaust direct `runtime_action=replace` row only if workbook-authored default and exclusive-group metadata can preserve the current customer-facing NWI/NGA behavior.

This is Candidate D from the Pass 8 report. It is a narrow Grand Sport workbook/source-data cleanup plus generated-artifact and test refresh. It is not a runtime direct-rule semantics pass, not a `runtime_action` column deletion pass, not a package/brake cleanup pass, not a Z06 exhaust/brake/default replacement pass, and not the Stingray runtime-rule-exception retirement pass.

## Diagnosis

Change type for this spec: docs-only.

Change type for implementation: mixed workbook/data + generated artifacts + tests. Risk level: medium-high because this touches default selected state, required peer replacement, dependency disabled-state, generated rules, and local runtime click behavior.

Root cause: `grandSport_rule_mapping` still carries a direct `runtime_action=replace` row for NWI replacing default NGA:

- `gs_rule_opt_nwi_001_excludes_opt_nga_001_replace`
- source `opt_nwi_001` / NWI
- target `opt_nga_001` / NGA
- `rule_type=excludes`
- `runtime_action=replace`

The workbook already carries part of the intended ownership:

- NGA is standard on every current Grand Sport variant and emits as `display_behavior=default_selected`.
- `default_selection_rules.gs_default_nga_unless_nwi` restores/selects NGA unless NWI is selected.
- NWI requires WUB through `grandSport_rule_mapping` row `gs_copy_rule_opt_nwi_001_requires_opt_wub_001_opt_nwi_001_requires_opt_wub_001`.
- FEY includes WUB through `grandSport_rule_mapping` row `gs_rule_opt_fey_001_includes_opt_wub_001`.
- There is an inactive `grandSport_exclusive_groups.gs_excl_exhaust_path` row, but its current member shape is not the approved product relationship because its active members are NGA and WUB, not NGA and NWI.

Product decision to preserve exactly:

- NGA and NWI are related exhaust-tip choices: only one can be selected, and one must be selected.
- NWI requires WUB.
- NGA has no reliance on WUB. NGA is standard/default either way.
- Selecting WUB alone must not remove NGA.
- Selecting NWI after WUB is selected must replace NGA.
- Removing NWI must restore NGA.
- Removing WUB while NWI is selected must invalidate/remove NWI and restore NGA.

That means WUB is an enabler/dependency for NWI, not a peer of NGA. Do not model WUB and NGA as mutually exclusive. Do not make NGA require WUB. Do not make WUB remove NGA.

Important scope correction: Stingray has the same expected NGA/NWI/WUB product behavior, but it is intentionally deferred from this pass. Current Stingray behavior is not owned by a direct `runtime_action=replace` row; it is split across `rule_mapping` NWI -> WUB, `default_selection_rules.default_nga`, and `runtime_rule_exceptions.ex_nwi_nga`. That split is a workbook-normalization problem, not a reason to keep special runtime-rule metadata permanently. A later pass should retire `runtime_rule_exceptions` into normal workbook rule/default/group ownership where behavior parity can be proven. Pass 12 fixes only Grand Sport's current direct replacement row and exhaust group shape so it follows the current workbook policy without expanding into the separate Stingray metadata-surface cleanup.

Evidence inspected for this spec:

- `docs/audit-cleanup/pass-8-direct-rule-field-classification-report.md:81` classifies the Grand Sport NWI/NGA replace row as Candidate D.
- `docs/audit-cleanup/pass-8-direct-rule-field-classification-report.md:176` defines Candidate D scope and required proof.
- `docs/Audit-route-map.md:324` recommends Candidate D after the corrected Pass 11.
- Current read-only workbook probe confirmed these relevant `grandSport_options` rows:
  - `opt_nga_001` / NGA: active/selectable, `sec_exha_001`, price 0, display order 10.
  - `opt_wub_001` / WUB: active/selectable, `sec_exha_001`, price 1995, display order 20, raw detail says included with FEY.
  - `opt_nwi_001` / NWI: active/selectable, `sec_exha_001`, price 395, display order 30, raw detail says requires WUB.
- Current read-only workbook probe confirmed these relevant `grandSport_ovs` rows:
  - NGA is `standard` for all six Grand Sport variants.
  - WUB is `available` for all six Grand Sport variants.
  - NWI is `available` for all six Grand Sport variants.
- Current read-only workbook probe confirmed these relevant `grandSport_rule_mapping` rows:
  - `gs_copy_rule_opt_nwi_001_requires_opt_wub_001_opt_nwi_001_requires_opt_wub_001`: NWI requires WUB.
  - `gs_rule_opt_fey_001_includes_opt_wub_001`: FEY includes WUB.
  - `gs_rule_opt_nwi_001_excludes_opt_nga_001_replace`: NWI currently replaces NGA through direct replacement behavior.
- Current read-only workbook probe confirmed these relevant exclusive-group rows:
  - `grandSport_exclusive_groups.gs_excl_exhaust_path` exists but is inactive.
  - `grandSport_exclusive_members.gs_excl_exhaust_path` currently has active members `opt_nga_001` and `opt_wub_001`; this is not the target relationship because WUB is not an NGA peer.
  - No active Grand Sport exhaust exclusive group currently owns NGA/NWI peer replacement.
- Current read-only workbook probe confirmed `default_selection_rules.gs_default_nga_unless_nwi` exists for `model_key=grand_sport`, `target_option_id=opt_nga_001`, `condition_type=unless_selected_rpo`, `condition_id=NWI`, wildcard scopes, active True.
- `form-output/runtime/grand-sport-runtime-contract.json` currently emits:
  - NGA/WUB/NWI choices for all six Grand Sport variants.
  - NWI requires WUB as an active direct rule.
  - FEY includes WUB as an active direct rule.
  - NWI excludes NGA with `runtime_action=replace`.
  - `gs_default_nga_unless_nwi` in `defaultSelectionRules`.
  - no active exhaust exclusive group.
- `tests/grand-sport-draft-data.test.mjs:391` currently expects the NWI/NGA direct replace row in generated rule keys.
- `tests/grand-sport-draft-data.test.mjs:532` currently asserts NGA emits as six standard/default-selected choices.
- `tests/multi-model-runtime-switching.test.mjs:1254` already tests the critical local runtime behavior: WUB enables NWI without replacing NGA; NWI replaces/restores NGA; removing WUB from the NWI path removes invalid NWI and restores NGA.
- Current read-only Stingray probe confirmed the deferred parallel debt:
  - `rule_mapping.rule_opt_nwi_001_requires_opt_wub_001`: NWI requires WUB.
  - `default_selection_rules.default_nga`: Stingray NGA default unless NWI.
  - `runtime_rule_exceptions.ex_nwi_nga`: Stingray NWI removes NGA outside normal `rule_mapping` ownership.
  - No Stingray NGA/NWI active exclusive group currently owns the peer relationship.

Current working tree note:

- Implementation preflight must re-run `git status --short --branch`. Initial spec-writing preflight saw branch `schema-ingestion-normalization`; dirty state must be rechecked before any implementation edits.

## Ownership decisions for this pass

### Model NGA/NWI as the required exhaust-tip peer group

Target decision:

- Activate or replace the inactive Grand Sport exhaust group so the active group owns only the true peer relationship:
  - `group_id=gs_excl_exhaust_path` unless preflight finds a better existing active naming convention.
  - `selection_mode=required_single_within_group`.
  - `active=True`.
  - notes should state that NGA and NWI are mutually exclusive required exhaust-tip choices; NWI still requires WUB; WUB is not a peer.
- Active members should be exactly:
  - `opt_nga_001`, display order 10.
  - `opt_nwi_001`, display order 30.
- Remove WUB from the active members of this group, either by deleting the `opt_wub_001` member row or setting that member inactive, depending on the workbook cleanup convention confirmed during preflight.

Rationale: the business relationship is NGA-vs-NWI. WUB only satisfies the NWI prerequisite. Keeping WUB in the peer group would incorrectly imply WUB can replace NGA or satisfy the required exhaust-tip choice by itself.

### Preserve WUB as NWI dependency/enabler only

Keep these rows unchanged:

| row behavior | rule_id | reason |
|---|---|---|
| NWI requires WUB | `gs_copy_rule_opt_nwi_001_requires_opt_wub_001_opt_nwi_001_requires_opt_wub_001` | NWI is only valid when WUB is selected or included. This is not replaced by the NGA/NWI exclusive group. |
| FEY includes WUB | `gs_rule_opt_fey_001_includes_opt_wub_001` | FEY package content can satisfy the NWI dependency by including WUB. This does not make WUB an NGA peer. |

Do not add any NGA -> WUB dependency, WUB -> NGA replacement, WUB -> NWI default, or WUB/NGA exclusive-group relationship.

### Preserve and verify NGA default ownership

Keep `default_selection_rules.gs_default_nga_unless_nwi` active unless preflight proves its shape has already changed. It should remain the restoration/default rule for NGA:

- `model_key=grand_sport`
- `target_option_id=opt_nga_001`
- `condition_type=unless_selected_rpo`
- `condition_id=NWI`
- wildcard body/trim/variant scopes
- active True

The implementation may need no new default row if `gs_default_nga_unless_nwi` plus `required_single_within_group` covers default restoration. If runtime parity proves this is insufficient, stop and report before inventing a new condition type or runtime-specific workaround.

### Delete the direct replacement row only after parity proof

Delete this direct row only after generated-data and runtime tests prove the active NGA/NWI group plus existing default/dependency metadata is behavior-equivalent:

| current workbook row from probe | rule_id | source | target | current runtime_action | canonical owner after pass |
|---:|---|---|---|---|---|
| 120 | `gs_rule_opt_nwi_001_excludes_opt_nga_001_replace` | `opt_nwi_001` / NWI | `opt_nga_001` / NGA | replace | `gs_excl_exhaust_path` with NGA/NWI members plus `gs_default_nga_unless_nwi`; WUB remains a separate NWI prerequisite |

If deleting this row makes local runtime behavior diverge, restore the direct row and close the pass as a characterization finding rather than masking the regression in RPO-specific JavaScript.

## Exact files/sheets/artifacts to change if approved

Source workbook:

- `stingray_master.xlsx`
  - `grandSport_exclusive_groups`
  - `grandSport_exclusive_members`
  - `grandSport_rule_mapping`

Generated artifacts expected to refresh:

- `form-output/runtime/grand-sport-runtime-contract.json`
- `form-output/grand-sport-form-data.json`
- `form-output/grand-sport-form-data.csv`
- `form-app/data.js`

Tests expected to change:

- `tests/grand-sport-draft-data.test.mjs`
- `tests/grand-sport-contract-preview.test.mjs` only if preview counts or expected group inventory change
- `tests/multi-model-runtime-switching.test.mjs`

Docs/status closure to update after implementation:

- `docs/audit-cleanup/pass-12-grand-sport-exhaust-default-replacement-ownership-spec.md`
- `docs/Audit-route-map.md`

Do not change in this pass:

- `form-app/app.js`
- `scripts/corvette_form_generator/*`
- `rule_mapping`
- `z06_rule_mapping`
- Stingray/Z06 exclusive groups or default-selection rows
- Stingray `runtime_rule_exceptions.ex_nwi_nga`
- `default_selection_rules.gs_default_nga_unless_nwi`, except for exact-row verification or a separately justified preflight correction
- NWI -> WUB requirement behavior
- FEY -> WUB include behavior
- `runtimeRuleExceptions`
- `variant_option_overrides`
- `runtime_action` workbook columns
- generated rule payload field names
- direct-rule `scopeMatches()` / body-style semantics
- dealer submission code, endpoint, payload shape, or Turnstile behavior

## Constraints

- Visual preservation: no UI/HTML/CSS/runtime-rendering changes.
- No refactor.
- No new dependencies.
- Workbook remains source of truth; use workbook exclusive-group/default/dependency metadata, not Grand Sport/RPO-specific JavaScript.
- Use `save_workbook_safely()` and verify workbook saved on disk.
- Close/avoid Excel. Stop if `~$stingray_master.xlsx` exists.
- Do not hand-edit generated artifacts; regenerate from workbook source.
- Do not delete the `runtime_action` column.
- Do not trim generated `rules.runtime_action` payload shape.
- Do not make WUB an active member of the NGA/NWI peer group.
- Do not make NGA depend on WUB.
- Do not let selecting WUB alone remove NGA.
- Do not make NWI selectable before WUB is selected or included.
- Do not bundle any FEY/FEB package, J57/J6A brake, Stingray spoiler, or Z06 replacement behavior.
- Do not normalize Stingray `runtime_rule_exceptions` or `variant_option_overrides` in this pass; both are explicitly deferred to a future workbook-normalization pass.

## Implementation plan if approved

1. Preflight.

   ```sh
   cd /Users/seandm/Projects/27vette
   git status --short --branch
   test ! -e './~$stingray_master.xlsx'
   .venv/bin/python scripts/validate_workbook_package.py stingray_master.xlsx
   ```

   Before editing, inspect dirty files and confirm no unrelated user changes overlap approved implementation paths. If unrelated dirty files exist, leave them untouched and report them in the handoff.

2. Snapshot current generated Grand Sport artifacts.

   ```sh
   mkdir -p /tmp/27vette-pass12-before
   cp form-output/runtime/grand-sport-runtime-contract.json /tmp/27vette-pass12-before/
   cp form-output/grand-sport-form-data.json /tmp/27vette-pass12-before/
   cp form-app/data.js /tmp/27vette-pass12-before/data.js
   ```

3. Read-only confirm candidate row identity before workbook write.

   Assert exact row identities:

   - `grandSport_options.opt_nga_001`: RPO NGA, active True, selectable True, `section_id=sec_exha_001`, `display_order=10`.
   - `grandSport_options.opt_wub_001`: RPO WUB, active True, selectable True, `section_id=sec_exha_001`, `display_order=20`.
   - `grandSport_options.opt_nwi_001`: RPO NWI, active True, selectable True, `section_id=sec_exha_001`, `display_order=30`.
   - `grandSport_ovs` has NGA standard, WUB available, and NWI available for all six current Grand Sport variants.
   - `grandSport_rule_mapping.gs_copy_rule_opt_nwi_001_requires_opt_wub_001_opt_nwi_001_requires_opt_wub_001`: `opt_nwi_001` requires `opt_wub_001`, blank `body_style_scope`, active/default runtime action.
   - `grandSport_rule_mapping.gs_rule_opt_fey_001_includes_opt_wub_001`: `opt_fey_001` includes `opt_wub_001`, blank `body_style_scope`, active/default runtime action.
   - `grandSport_rule_mapping.gs_rule_opt_nwi_001_excludes_opt_nga_001_replace`: `opt_nwi_001` excludes `opt_nga_001`, `runtime_action=replace`, blank `body_style_scope`.
   - `default_selection_rules.gs_default_nga_unless_nwi`: active Grand Sport NGA default unless NWI.
   - Current `gs_excl_exhaust_path` parent/member state, including whether WUB is still an active member.

   Stop if any identity differs; update the spec or ask for approval before adapting the pass.

4. Add RED/characterization test changes before workbook write.

   Update tests so they fail against the current source state but express the target workbook ownership:

   - `tests/grand-sport-draft-data.test.mjs` should expect an active Grand Sport exhaust exclusive group with option IDs exactly `["opt_nga_001", "opt_nwi_001"]` and `selection_mode="required_single_within_group"`.
   - The same test should assert no active generated exclusive group contains `opt_wub_001` with `opt_nga_001`.
   - The same test should assert the direct rule key `opt_nwi_001::excludes::opt_nga_001::::replace` is absent after the workbook change.
   - Keep or strengthen assertions that NWI requires WUB and FEY includes WUB.
   - Keep assertions that NGA emits as six standard/default-selected choices.

5. Write the workbook through a small safe-save script.

   The script should:

   - Load `stingray_master.xlsx`.
   - Stop if `~$stingray_master.xlsx` exists.
   - Assert exact preflight identities again before mutation.
   - Update `grandSport_exclusive_groups.gs_excl_exhaust_path` to active `required_single_within_group` with corrected notes, or create an equivalent row only if the existing row is absent.
   - Ensure active `grandSport_exclusive_members` for `gs_excl_exhaust_path` are exactly `opt_nga_001` and `opt_nwi_001` in workbook display order.
   - Remove or deactivate the stale WUB member in that group.
   - Delete only `grandSport_rule_mapping.gs_rule_opt_nwi_001_excludes_opt_nga_001_replace`.
   - Leave NWI -> WUB and FEY -> WUB rows unchanged.
   - Save via `save_workbook_safely()`.

6. Verify workbook saved on disk.

   Reopen with `openpyxl` read-only and assert the exact post-save state:

   - `gs_excl_exhaust_path` active True, `selection_mode=required_single_within_group`.
   - Active members exactly `opt_nga_001`, `opt_nwi_001`; WUB is not active in the group.
   - NWI -> WUB requirement row still exists unchanged.
   - FEY -> WUB include row still exists unchanged.
   - NWI -> NGA direct replace row is absent.
   - `gs_default_nga_unless_nwi` still exists unchanged.

7. Regenerate affected artifacts.

   ```sh
   .venv/bin/python scripts/generate_form.py --model grand_sport
   .venv/bin/python scripts/generate_registry.py
   ```

8. Compare generated artifacts against the snapshot.

   Expected/allowed substantive Grand Sport changes:

   - one fewer direct generated rule for `opt_nwi_001` replacing `opt_nga_001`.
   - one active generated exclusive group added or activated for NGA/NWI.
   - no active generated exclusive group member for WUB in the exhaust peer group.
   - no change to NWI -> WUB requirement.
   - no change to FEY -> WUB include.
   - no change to NGA standard/default-selected choice rows.

   Any other generated drift must be classified before continuing. Restore unrelated timestamp-only or unapproved generated churn.

9. Run targeted gates.

   ```sh
   node --test tests/grand-sport-contract-preview.test.mjs
   node --test tests/grand-sport-draft-data.test.mjs
   node --test tests/multi-model-runtime-switching.test.mjs
   ```

   If generated registry data changed beyond Grand Sport's expected contract, also run:

   ```sh
   node --test tests/stingray-form-regression.test.mjs
   ```

10. Local runtime/browser smoke.

   Because Pass 11 previously regressed local click behavior despite generated-data expectations, do not rely on JSON tests only. Verify in local runtime or equivalent DOM/runtime harness:

   - Grand Sport defaults select NGA on reset.
   - NWI is disabled before WUB is selected and cites WUB/Quad Center Exit as the dependency.
   - Selecting WUB leaves NGA selected.
   - Selecting NWI after WUB removes NGA and selects NWI.
   - Clicking/removing NWI restores NGA.
   - Removing WUB while NWI is selected removes invalid NWI and restores NGA.
   - The exhaust group cannot be emptied by clicking NGA off when no NWI is valid/selected.

11. Closure.

   Before final handoff, update this spec status to Implemented or Corrected/Deferred with:

   - completion date
   - changed workbook sheets
   - generated artifacts
   - tests/gates run
   - browser/runtime smoke result or explicit not-run reason
   - residual risks and next pass

   Also update `docs/Audit-route-map.md` so Candidate D is no longer described as merely unwritten/pending if implementation lands.

## Risks

- Required exclusive group semantics may not fully replace direct `runtime_action=replace` behavior for already-selected/default-selected NGA. If so, restore the direct row and report the gap rather than hiding it in RPO-specific runtime logic.
- The existing inactive `gs_excl_exhaust_path` row currently includes WUB as a member. Accidentally activating it without correcting members would create wrong product behavior.
- Generated-data tests can pass while local click behavior regresses. The implementation must run the existing runtime interaction test and perform a local runtime smoke.
- NWI dependency behavior and NGA default behavior are different concepts. Combining them into one group/dependency could make WUB incorrectly remove NGA or make NGA incorrectly depend on WUB.

## Non-goals

- No Stingray or Z06 exhaust behavior changes.
- No Stingray `runtime_rule_exceptions.ex_nwi_nga` retirement; that belongs in a future pass that moves runtime exceptions into normal workbook rule/default/group ownership.
- No `variant_option_overrides` retirement; a future pass should evaluate moving remaining variant-specific defaults, including engine-cover defaults, into `default_selection_rules` where that existing mechanism can own the behavior.
- No package/brake/aero replacement cleanup.
- No runtime hardcode or RPO-specific branch.
- No deletion of `runtime_action` fields or columns.
- No payload trimming.
- No body-style scope matching changes.
- No dealer submission changes.

## Deferred follow-up — workbook metadata surface cleanup

This pass intentionally records but does not fix two workbook-normalization debts:

1. `runtime_rule_exceptions` should not remain a small segregated rule surface for behavior that can be represented by normal workbook rules, exclusive groups, default-selection rows, and generic runtime evaluation. Stingray `ex_nwi_nga` is the concrete near-term example: it should be moved into the same normal workflow pattern used for Grand Sport once this narrower Grand Sport pass proves the required-group/default behavior.
2. `variant_option_overrides` should be audited for rows that duplicate default-selection behavior. Engine-cover defaults already have `default_selection_rules` coverage and should be candidates for moving test expectations and behavior ownership there instead of preserving a separate override surface.

Keep these follow-ups separate from Pass 12 so the current change stays limited to Grand Sport's direct replacement row and active exhaust group structure after the Pass 11 local-runtime regression.

## Validation plan

Spec-writing validation:

```sh
git diff -- docs/audit-cleanup/pass-12-grand-sport-exhaust-default-replacement-ownership-spec.md docs/Audit-route-map.md
git diff --check -- docs/audit-cleanup/pass-12-grand-sport-exhaust-default-replacement-ownership-spec.md docs/Audit-route-map.md
```

Implementation validation if approved:

```sh
git status --short --branch
test ! -e './~$stingray_master.xlsx'
.venv/bin/python scripts/validate_workbook_package.py stingray_master.xlsx
.venv/bin/python scripts/generate_form.py --model grand_sport
.venv/bin/python scripts/generate_registry.py
node --test tests/grand-sport-contract-preview.test.mjs
node --test tests/grand-sport-draft-data.test.mjs
node --test tests/multi-model-runtime-switching.test.mjs
```

Manual/runtime verification still required for implementation:

- Local Grand Sport form behavior for WUB/NWI/NGA click sequence listed in Implementation step 10.
- Confirm no visual/styling/dealer-submission changes.

## Approval prompt

Approve Pass 12 to implement the Grand Sport NGA/NWI exhaust ownership cleanup exactly as scoped above?
