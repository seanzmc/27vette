# Z06 Performance Package Rule Correction Pass 3 Spec

Status: implemented / verified
Created: 2026-06-02
Implemented: 2026-06-02
Repo: `/Users/seandm/Projects/27vette`
Branch observed: `z06-zr1-migration`
Workbook lock observed: none (`~$stingray_master.xlsx` absent)

## User report / acceptance target

The current Z06 performance-package behavior is still not the desired customer interaction model:

1. Wheel/brake packages and Z07 should be selectable first.
2. Selecting a package should then prompt/select the package's configurable inner choices, not grey out the package itself or force the customer to choose inner options before the package can be used.
3. Do not mess with canonical standalone options. Standalone wheels/brakes/aero/ground-effects rows should remain real selectable rows where they are real standalone options.
4. Aero packages that include ground effects should lock their included ground-effects pair. A customer should not be able to switch CFZ/CFV/CFL away from the included package component while that aero package remains selected/auto-added.
5. Exhaust tips should be mutually exclusive.
6. Default-selected rows should behave like radio-like defaults where appropriate: selecting a peer replaces the default; clicking/removing the selected default should not leave a required/default group empty.
7. Inconsistent disabling inside peer groups should be removed. Example: selecting T0F currently disables 5ZV, while selecting T0G does not disable 5ZV. The desired behavior is T0G-style peer replacement: mutual-exclusive peers should remain clickable and should unselect the previously selected peer instead of being greyed out.

## Evidence inspected

### Project rules

- `AGENTS.md`
  - Non-trivial behavior/workbook/generated/runtime changes require a spec before edits.
  - Business rules belong in workbook rows when representable.
  - Generated `form_*`, `form-output/`, and `form-app/data.js` are outputs.
- `codex-context.md`
  - Runtime should render/evaluate generated data and not accumulate Corvette product knowledge.
  - Do not alter live behavior without approval.

### Current git/workbook state

Command inspected:

```sh
git branch --show-current
git status --short --branch
python3 - <<'PY'
from pathlib import Path
print('LOCK' if Path('~$stingray_master.xlsx').exists() else 'NO_LOCK')
PY
```

Observed:

- Branch: `z06-zr1-migration`
- No Excel lock file.
- Only pre-existing untracked `.DS_Store` / backup noise was visible during this inspection.

### Current runtime behavior reproduced from `form-app/data.js` + `form-app/app.js`

A Node/vm runtime probe reproduced these behaviors:

- Selecting `Z07`:
  - `Z07` is initially selectable.
  - After selection, `Z07` reports a disabled reason: `Requires T0F Carbon Flash aero or T0G visible carbon aero.`
  - This is confusing because the selected package card appears disabled due to its own pending inner choice.
  - Auto-adds: `FE7`, `J57`, `XFS`.
- Selecting `PDB`:
  - `PDB` is initially selectable.
  - After selection, `PDB` reports a disabled reason: `PDB requires one Z06 carbon fiber wheel choice: ROY, ROZ, or STZ.`
  - Peer packages `PDD`/`PDF` are disabled by explicit excludes.
  - Auto-adds: `J57`, `J6D`.
- Selecting `PDD`:
  - Auto-adds: `Z07`, `T0F`, `CFZ`, `J57`, `FE7`, `XFS`.
  - `PDD` reports its own carbon-wheel missing requirement as a disabled reason.
  - `T0G` is disabled by explicit `PDD excludes T0G`.
  - `5ZV` is disabled by an explicit `5ZV excludes T0F` conflict.
- Selecting `PDF`:
  - Auto-adds: `Z07`, `T0G`, `CFV`, `J57`, `FE7`, `XFS`.
  - `PDF` reports its own carbon-wheel missing requirement as a disabled reason.
  - `T0F` is disabled by explicit `PDF excludes T0F`.
  - `5ZV` is not disabled, producing the user-reported inconsistency with T0F.
- Selecting `T0F`:
  - Auto-adds `CFZ`.
  - Disables `5ZV` via explicit exclude/conflict.
  - Does not select `Z07` or `J57`; carbon wheels remain disabled by their `requires J57` rules.
- Selecting `T0G`:
  - Auto-adds `CFV`.
  - Does not disable `5ZV`, showing the asymmetric behavior the user prefers as the direction for peer replacement.

### Current workbook source rows inspected

Workbook sheets inspected via read-only `openpyxl`:

- `z06_options`
- `z06_rule_mapping`
- `z06_rule_groups`
- `z06_rule_group_members`
- `z06_exclusive_groups`
- `z06_exclusive_members`
- `section_master`

Important current option rows:

- `Z07` (`opt_z07_001`)
  - section `sec_perf_z52_001`
  - selectable `True`, active `True`
  - detail says it requires the T0F/CFZ or T0G/CFV aero path and is included with PDD/PDF.
- `PDB`/`PDD`/`PDF`
  - section `sec_z06_pkg_001`
  - selectable `True`, active `True`
  - currently direct package options.
- `T0E`
  - section `sec_perf_aero_001`
  - standard/selectable/default_selected.
- `T0F`
  - section `sec_perf_aero_001`
  - selectable `True`, active `True`
  - included with `PDD`.
- `T0G`
  - section `sec_perf_aero_001`
  - selectable `True`, active `True`
  - included with `PDF`.
- `5ZV`
  - section `sec_perf_aero_001`
  - selectable `True`, active `True`
  - detail says not available with T0F, T0G, 5V5; but workbook rule rows currently only enforce the T0F conflict.
- `CFZ`
  - section `sec_perf_ground_001`
  - included with T0F.
- `CFV`
  - section `sec_perf_ground_001`
  - included with T0G.
- `CFL`
  - section `sec_perf_ground_001`
  - standalone/alternate ground effects.
- `NGA`
  - section `sec_exha_001`, standard non-selectable black exhaust tips.
- `NWI`
  - section `sec_exha_001`, selectable bright exposed quad center exhaust tips.
- Default-selected rows currently visible in Z06 source:
  - `EFR` exterior accents, already in `z06_excl_exterior_accents` required group.
  - `T0E` aero package, not currently in an active exclusive group with T0F/T0G/5ZV.
  - `J56` performance brakes, already in `z06_excl_performance_brakes` required group.
  - `719` black seat belt, section single-choice behavior likely handles this rather than exclusive group metadata.

Current rule rows causing the bad behavior:

- Package peer blocking is explicit excludes, not active radio replacement:
  - `PDB excludes PDD/PDF`
  - `PDD excludes PDB/PDF`
  - `PDF excludes PDB/PDD`
  - The older `z06_excl_carbon_wheel_packages` group exists but is inactive with a note saying explicit excludes are now used. That is opposite of the user's preferred interaction.
- Aero asymmetry is explicit excludes:
  - `5ZV excludes T0F`
  - `PDD excludes T0G`
  - `PDF excludes T0F`
  - No equivalent `5ZV excludes T0G`, which explains current inconsistency; but the preferred fix is not adding the missing exclude, it is replacing these peer blocks with radio-like exclusive-group switching.
- Package self-disable comes from runtime `requiresAnyReason(choice, selectedIds)` being used in `disableReasonForChoice()` for a selected source option. This makes selected packages (`Z07`, `PDB`, `PDD`, `PDF`) visually disabled while their own grouped requirement is pending.
- Ground effects have an active generic exclusive group:
  - `z06_excl_ground_effects`: `CFL`, `CFZ`, `CFV` as `single_within_group`.
  - But because `CFZ`/`CFV` are auto-added by T0F/T0G, clicking another ground-effect peer can currently allow a user-selected peer to suppress the package-included ground effect. That violates the desired locked-pair behavior.
- Exhaust tips are not currently in an exclusive group:
  - `NGA` black exhaust tip is standard/display-only in `sec_exha_001`.
  - `NWI` bright exposed exhaust tip is selectable in the same section.
  - No `z06_excl_exhaust_tips` row/member coverage was found.

## Root-cause diagnosis

This is a mixed workbook/runtime source-contract problem, not a simple missing row.

1. **Old explicit-exclude rows are still modeling radio peers as hard conflicts.**
   The package/aero rows currently use `excludes` rows that make peers grey out instead of letting the selected peer replace the previous peer. The inactive `z06_excl_carbon_wheel_packages` group note explicitly says the workbook intentionally moved to explicit excludes; that is now confirmed as the wrong interaction model.

2. **The runtime displays selected source options with pending `requires_any` groups as disabled.**
   `form-app/app.js` uses `requiresAnyReason(choice, selectedIds)` inside `disableReasonForChoice()`. That is useful for missing-requirement messaging, but it makes selected source packages look inactive/disabled while the customer is still choosing inner options. The requirement should be reported in `missingRequirementDetails()`, not as a disabled state on the package that was just selected.

3. **Included auto-added choices are not protected strongly enough against user-selected exclusive peers.**
   `computeAutoAdded()` avoids adding an included target when `userSelectedExclusiveGroupPeer()` exists. That works for some optional defaults, but it is wrong for hard package pairs like `T0F -> CFZ` and `T0G -> CFV`. Package-included ground effects need to stay locked while the package/aero source is selected.

4. **Default-selected rows lack complete radio/default metadata coverage.**
   Some default rows rely only on `display_behavior=default_selected` and section behavior. Required/default radio-like groups need explicit active workbook-owned groups where the section is multi-select or where peer replacement/last-default prevention is required.

5. **Exhaust tips are under-modeled.**
   The workbook has standard `NGA` and selectable `NWI` exhaust tip rows but no active exclusive group, so the runtime cannot generically replace/restore exhaust-tip peers using the same structure proven in Grand Sport (`WUB` enables `NWI`; `NWI` replaces/restores `NGA`).

## Change classification

Mixed:

- workbook source data: yes
- safe-save migration/apply script: yes
- generated Z06/runtime artifacts: yes, after workbook changes
- runtime generic behavior: likely yes
- tests: yes
- generated workbook sheets: output only, not hand-edited

Risk level: medium-high because this touches selected-state mechanics for Z06 package/aero/brake/wheel/default behavior. The safe approach is targeted Z06 tests plus multi-model regression coverage to prove Stingray/Grand Sport are not regressed.

## Proposed smallest safe Pass 3

### A. Workbook source corrections

Implement through a new idempotent safe-save script, for example:

`/Users/seandm/Projects/27vette/scripts/apply_z06_performance_package_rule_corrections.py`

Dry-run default, `--write` required, using `save_workbook_safely()`.

#### A1. Reactivate package peer exclusive group

- Reactivate `z06_excl_carbon_wheel_packages` or replace it with a clearer active group ID if the existing one is semantically stale.
- Members: `PDB`, `PDD`, `PDF`.
- `selection_mode`: `single_within_group` unless a package must be required; current user direction says selectable package-first, not required package.
- Remove/deactivate explicit package-peer excludes:
  - `PDB -> PDD/PDF`
  - `PDD -> PDB/PDF`
  - `PDF -> PDB/PDD`

Expected runtime behavior:

- PDB/PDD/PDF remain clickable/selectable when a peer is already selected.
- Clicking a peer unselects the prior peer rather than greying the peer out.

#### A2. Add/activate aero package exclusive group

Create or activate a Z06 aero peer group:

- Members: `T0E`, `T0F`, `T0G`, `5ZV`.
- Include `T0E` because it is the workbook default-selected aero row.
- `selection_mode`: likely `single_within_group`, plus generic default-preservation behavior should prevent emptying the default-selected group if no peer is selected.
- Deactivate explicit aero peer excludes that currently cause greyed-out behavior:
  - `5ZV excludes T0F`
  - `PDD excludes T0G` if PDD keeps including/locking T0F.
  - `PDF excludes T0F` if PDF keeps including/locking T0G.
- Do **not** add a new `5ZV excludes T0G` row just to mirror the current T0F problem; that would make the disliked behavior more consistent but still wrong.

Expected runtime behavior:

- `T0F`, `T0G`, `5ZV`, and default `T0E` switch as peers.
- T0F no longer greys out 5ZV; selecting 5ZV removes T0F where no hard package include is active.
- T0G and T0F share the same replacement semantics.

#### A3. Keep package-included aero/ground effects locked

Current includes should remain workbook-authored:

- `T0F includes CFZ`
- `T0G includes CFV`
- `PDD includes Z07/T0F/CFZ`
- `PDF includes Z07/T0G/CFV`

But runtime must treat package-included `CFZ`/`CFV` as locked while their source package/aero is selected.

Possible source-data addition if the generic runtime needs a signal:

- Use existing `includes` rules as the lock signal for options whose target is in an exclusive group and whose source is selected/auto-added.
- Do not invent RPO-specific JS (`if T0F then CFZ`).

Expected behavior:

- Selecting T0F auto-adds CFZ.
- With T0F selected, clicking CFV/CFL should not replace/suppress CFZ unless the user first switches away from T0F to a different aero peer.
- Selecting T0G auto-adds CFV and locks it similarly.
- Selecting PDD/PDF should lock their included aero+ground pair through the same generic include mechanics.

#### A4. Exhaust-tip exclusive/default structure

Add workbook-owned Z06 exhaust-tip group:

- Group ID suggestion: `z06_excl_exhaust_tips`.
- Members: `NGA`, `NWI`.
- Selection mode: probably `single_within_group`, with `NGA` converted to/selectively represented as a default-selected row if the runtime should restore it when NWI is removed.

Important: this must respect the existing source truth:

- `WUB` is standard and should not become a selectable dependency blocker.
- `NWI` should remain selectable without requiring WUB, matching prior approved Z06 correction.
- `NGA` should be the default/restored exhaust tip if the customer has not chosen `NWI`.

#### A5. Default-selected group coverage

Audit current Z06 `display_behavior=default_selected` rows:

- `EFR`: already covered by required exterior accent group.
- `T0E`: needs active aero group coverage.
- `J56`: already covered by required brake group.
- `719`: likely section-owned single required seat-belt default; confirm no change needed unless runtime evidence shows it can be emptied incorrectly.
- Exhaust default: likely add `NGA` as default/restored if the product decision is to include black exhaust tips as default selected RPOs.

Do not make a section required just to force radio behavior. Use workbook group metadata where the customer interaction is radio-like.

### B. Generic runtime correction

Target file:

- `/Users/seandm/Projects/27vette/form-app/app.js`

Proposed generic changes:

1. Keep `requires_any` failures in `missingRequirementDetails()` but stop presenting the selected source package itself as disabled.
   - Do not call `requiresAnyReason(choice, selectedIds)` as a disabled reason for the currently selected `choice.option_id`, or make this behavior conditional so selected options remain visually active while pending requirements are reported separately.
   - Unselected options that require prerequisites should still show disable reasons when appropriate.

2. Strengthen included-target locking inside exclusive groups.
   - If a selected/auto-added source includes a target that belongs to an exclusive group, treat that target as non-removable while the source remains selected/auto-added.
   - Clicking another peer in the same exclusive group should be blocked with a clear reason or ignored, unless the click also switches/removes the source that included the target.
   - This must be generic and based on generated include/exclusive-group data.

3. Preserve radio/default behavior for `single_within_group` groups containing a `default_selected` active member.
   - Selecting a peer should replace the default.
   - Clicking the selected default/peer should not leave the group empty when the group's active current-variant member set has a default-selected member and the section/group is intended as radio-like.
   - Reconcile should not re-add the default while a user-selected peer is present.

### C. Tests to add/update first

Add/update targeted RED tests before workbook/runtime changes.

Likely file options:

- Extend `tests/z06-runtime-rule-corrections.test.mjs`, or
- Add a focused `tests/z06-performance-package-interactions.test.mjs`.

Specific assertions:

1. Package-first flow:
   - `Z07`, `PDB`, `PDD`, `PDF` are selectable initially.
   - After selecting any one, `disableReasonForChoice(selectedPackage)` is empty.
   - Missing requirement details still show inner choices where applicable (`Z07 -> T0F/T0G`; PDB/PDD/PDF -> ROY/ROZ/STZ).

2. Package peer replacement:
   - Select `PDB`, then click `PDD`; PDD becomes selected and PDB is removed.
   - Peer package cards are not disabled merely because another package is selected.

3. Aero peer replacement and consistency:
   - Starting from default `T0E`, select `T0F`; T0E is removed and T0F is selected.
   - With T0F selected and no package lock, `5ZV` is not disabled; clicking `5ZV` removes T0F.
   - T0G has the same behavior, not a different disable profile.

4. Included ground-effects lock:
   - Select `T0F`; CFZ is auto-added at $0.
   - CFV/CFL cannot replace CFZ while T0F remains selected.
   - Switch from T0F to T0G; CFZ is removed and CFV is auto-added/locked.

5. Exhaust-tip exclusivity/default:
   - Initial Z06 build includes/restores `NGA` if approved as the default exhaust-tip selected RPO.
   - Select `NWI`; `NGA` is removed.
   - Remove/switch `NWI`; `NGA` is restored, if that is the approved default behavior.
   - `NWI` does not require WUB.

6. Existing guardrails preserved:
   - Source non-selectable standard rows are not customer-clickable unless explicitly modeled as default/restored choices.
   - Z06 Pass 1 and Pass 2 tests remain green.
   - Grand Sport WUB/NWI/NGA behavior remains green.

### D. Regeneration and gates

After approval and implementation:

```sh
.venv/bin/python scripts/validate_workbook_package.py
.venv/bin/python scripts/apply_z06_performance_package_rule_corrections.py --include-changes
.venv/bin/python scripts/apply_z06_performance_package_rule_corrections.py --write --include-changes
.venv/bin/python scripts/apply_z06_performance_package_rule_corrections.py --include-changes
.venv/bin/python scripts/generate_z06_form.py
.venv/bin/python scripts/generate_stingray_form.py
node --test tests/z06-performance-package-interactions.test.mjs
node --test tests/z06-runtime-rule-corrections.test.mjs
node --test tests/z06-interior-accessory-cleanup.test.mjs
node --test tests/z06-contract-preview.test.mjs tests/z06-form-data-draft.test.mjs tests/z06-runtime-promotion.test.mjs
node --test tests/multi-model-runtime-switching.test.mjs
node --test tests/stingray-form-regression.test.mjs tests/stingray-generator-stability.test.mjs tests/grand-sport-contract-preview.test.mjs tests/grand-sport-draft-data.test.mjs tests/grand-sport-rule-audit.test.mjs
```

Then browser-smoke the Z06 flow:

- Switch to Z06.
- Select Z07/PDB/PDD/PDF and confirm cards remain selected/active while missing inner choices are shown separately.
- Confirm T0F/T0G/5ZV switch rather than grey each other out.
- Confirm T0F locks CFZ and T0G locks CFV.
- Confirm exhaust-tip peer behavior.
- Check browser console for JS errors.

## Non-goals / boundaries

- Do not change direct canonical option rows just to hide symptoms.
- Do not hand-edit generated `form_*` sheets, `form-output`, or `form-app/data.js`.
- Do not add model/RPO-specific branches to runtime JS.
- Do not change dealer submission endpoint, Turnstile behavior, payload shape, or deployment configuration.
- Do not address broader package-combination pricing beyond preserving existing package/price-rule behavior and included zero-pricing needed by these interactions.
- Do not modify ZR1/ZR1X in this pass.

## Open product decision before implementation

One detail needs explicit confirmation during approval:

- Should `NGA` be a true selected/default-restored exhaust-tip RPO for Z06, mirroring Grand Sport's default exhaust-tip behavior, or should it remain display-only standard equipment while only `NWI` is a selected customer option?

My recommendation: model it like Grand Sport if the customer-facing build summary should show the default exhaust-tip RPO and allow NWI to replace it. If NGA should remain standard-equipment-only, still add `NGA`/`NWI` mutual exclusivity where possible, but avoid making NGA a selected customer RPO.

## Approval request

Approve Pass 3 to implement the workbook/runtime/test changes above.
