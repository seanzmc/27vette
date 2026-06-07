# Z06 carbon-wheel package disabled-state spec

## Diagnosis

Root cause: the current Z06 workbook/runtime contract only blocks aluminum wheel peers while the package-included default wheel `ROY` is auto-added. Once the user switches the required carbon-fiber wheel choice from auto-added `ROY` to user-selected `ROZ` or `STZ`, the lock is no longer driven by an included target, so `disableReasonForChoice()` returns an empty reason for aluminum wheel peers.

Evidence inspected:

- Branch/status: current worktree is on `main`, behind `origin/main` by 2 commits, with unrelated untracked `.DS_Store` files and untracked `scripts/migrations/`. Do not implement on this dirty/main worktree without a separate approved worktree or explicit user approval.
- `form-app/app.js`
  - `disableReasonForChoice()` checks, in order, `requiresAnyReason()`, `excludesAnyReason()`, `includedExclusiveGroupPeerReason()`, direct excludes, then source requirements.
  - `includedExclusiveGroupPeerReason()` is what currently grays aluminum wheels when auto-added `ROY` is present.
  - After `ROZ`/`STZ` is user-selected, no package-included wheel peer remains to drive that reason.
- `stingray_master.xlsx`, read-only inspection:
  - `z06_rule_groups` has `requires_any` groups for `PDB`, `PDD`, and `PDF` requiring `ROY`/`ROZ`/`STZ`.
  - `z06_rule_groups` already has the proven blocker pattern for related issues:
    - `z06_group_z07_excludes_non_z07_aero`: source `opt_z07_001`, `excludes_any`, targets `opt_t0e_001`, `opt_5zv_001`.
    - `z06_group_z07_excludes_j56_brakes`: source `opt_z07_001`, `excludes_any`, target `opt_j56_001`.
    - `z06_group_pdb_excludes_j56_brakes`: source `opt_pdb_001`, `excludes_any`, target `opt_j56_001`.
  - `z06_rule_groups` does not have corresponding `excludes_any` groups for `PDB`/`PDD`/`PDF` blocking non-carbon wheel choices.
  - `z06_exclusive_groups` has `z06_excl_default_and_carbon_wheels`, `single_within_group`, active.
  - `z06_exclusive_members` for that group include carbon wheels `ROY`/`ROZ`/`STZ` and aluminum/default peers `SOE`, `SRK`, `ROU`, `SOA`, `SRN`, `SON`, `ROX`, `SOM`, `STX`.
- `form-app/data.js`, generated live Z06 data:
  - Emits the same `requires_any` wheel groups and the same wheel exclusive group.
  - Does not emit `excludes_any` package-to-aluminum-wheel blocker groups.
- Ad-hoc runtime probe confirmed the reported behavior:
  - After selecting `PDB`, auto-added `ROY` makes `ROU`, `ROX`, `SOA`, `SOE`, `SOM`, `SON`, `SRK`, `SRN`, and `STX` disabled with reason `ROY ... is locked because it is included with PDB...`.
  - After selecting `PDB -> ROZ`, those same aluminum wheel choices return `""` from `disableReasonForChoice()`.
  - Same failure repeats for `PDD -> ROZ` and `PDF -> ROZ`.
- Existing focused test gate `node --test tests/z06-performance-package-interactions.test.mjs` passes, so the current tests do not cover aluminum-wheel disabled state after switching from package-default `ROY` to `ROZ`/`STZ`.

Risk level: medium. This is a live promoted Z06 runtime behavior correction affecting selectable/disabled state in the customer UI, but the needed source shape already exists and is narrow.

Change type: mixed workbook/data + generated artifacts + tests. Runtime code should not change unless implementation evidence proves the workbook-owned blocker path cannot cover the behavior.

## Recommended smallest safe solution

Use the existing workbook-owned `excludes_any` pipeline already used for Z07 aero and PDB/Z07 brake blockers.

Add three active workbook groups in `z06_rule_groups`:

1. `z06_group_pdb_excludes_aluminum_wheels`
   - `group_type`: `excludes_any`
   - `source_id`: `opt_pdb_001`
   - scopes: `*` body, trim, variant
   - `disabled_reason`: `PDB requires ROY, ROZ, or STZ carbon fiber wheels; aluminum wheel choices are not available while PDB is selected.`
   - `active`: `True`
   - notes should state that this preserves the carbon-wheel package lock after switching from default `ROY` to `ROZ`/`STZ`.

2. `z06_group_pdd_excludes_aluminum_wheels`
   - same shape, source `opt_pdd_001`, PDD-specific disabled copy.

3. `z06_group_pdf_excludes_aluminum_wheels`
   - same shape, source `opt_pdf_001`, PDF-specific disabled copy.

Add active `z06_rule_group_members` rows for each of those groups targeting the non-carbon wheel members of `z06_excl_default_and_carbon_wheels`:

- `opt_soe_002` / SOE
- `opt_srk_001` / SRK
- `opt_rou_001` / ROU
- `opt_soa_001` / SOA
- `opt_srn_001` / SRN
- `opt_son_001` / SON
- `opt_rox_001` / ROX
- `opt_som_001` / SOM
- `opt_stx_001` / STX

Do not target carbon wheel choices `opt_roy_001`, `opt_roz_001`, or `opt_stz_001`; those must remain selectable switches while the package remains selected.

Implementation should use `save_workbook_safely()` through a small idempotent workbook update path or approved existing workbook writer. If a one-pass script is used, retire it or leave it untracked only long enough to apply and verify; do not add a stale routine workflow script unless explicitly approved.

## Exact files / sheets / artifacts to change

Source workbook:

- `stingray_master.xlsx`
  - `z06_rule_groups`
  - `z06_rule_group_members`

Generated artifacts after regeneration:

- `form-output/inspection/z06-form-data-draft.json`
- `form-output/inspection/z06-form-data-draft.md`
- `form-output/inspection/z06-contract-preview.json`
- `form-output/inspection/z06-contract-preview.md`
- `form-output/inspection/z06-inspection.json`
- `form-output/inspection/z06-inspection.md`
- `form-app/data.js` after `scripts/generate_stingray_form.py` syncs the live promoted registry
- Generated `form_*` workbook sheets if `scripts/generate_stingray_form.py` rewrites them as part of the current production path

Tests:

- `tests/z06-form-data-draft.test.mjs`
  - Add a generated-contract assertion that `PDB`, `PDD`, and `PDF` each emit an active `excludes_any` group targeting the nine aluminum/default wheel option IDs above, while not targeting `ROY`/`ROZ`/`STZ`.
- `tests/z06-performance-package-interactions.test.mjs`
  - Extend the carbon wheel package interaction test or add a new test:
    - select each of `PDB`, `PDD`, `PDF`;
    - verify aluminum wheels are disabled while auto-added `ROY` is present;
    - select `ROZ`, reconcile, verify all aluminum wheels are still disabled;
    - optionally repeat with `STZ` for one package or all three;
    - verify `ROY`/`ROZ`/`STZ` remain switchable and package missing requirements remain satisfied.

## Constraints

- Preserve visual styling and DOM structure; this is disabled-state logic, not a restyle.
- No runtime RPO-specific JavaScript exceptions unless the workbook-owned `excludes_any` path is proven insufficient.
- No new dependencies.
- Do not edit generated `form_*` sheets, `form-output`, or `form-app/data.js` by hand; regenerate them.
- Do not change dealer submission endpoint, payload shape, Turnstile behavior, download behavior, or model registry keys.
- Do not change package peer behavior: `PDB`, `PDD`, and `PDF` must remain clickable radio-like peers, not gray each other out.
- Do not disable carbon wheel switches: `ROY`, `ROZ`, and `STZ` must remain selectable while any carbon wheel package is selected.
- Do not make canonical aluminum wheel option rows inactive; they are valid standalone wheel choices when no carbon wheel package owns the wheel requirement.
- Close Excel before workbook writes and stop if `~$stingray_master.xlsx` exists.
- Use `.venv/bin/python`, not bare system Python, for workbook/generator commands.

## Risks and non-goals

Risks:

- `PDD`/`PDF` auto-add `Z07`; adding package-level wheel blocker groups should not interfere with the existing Z07 aero/brake blockers, but tests should cover PDD/PDF specifically.
- The disabled reason will change from an include-lock reason under auto-added `ROY` to package blocker copy if `excludesAnyReason()` is evaluated before `includedExclusiveGroupPeerReason()`. That is acceptable if visual disabled state and product behavior are correct, but the test should assert non-empty disabled reason rather than exact copy except for generated-contract copy.
- Generated artifact churn may include timestamps or unrelated registry sync; review diffs and restore unrelated noise if it is not semantically tied to this pass.
- Current worktree is on `main` and dirty with untracked files; implementation should be in a clean branch/worktree.

Non-goals:

- Do not revisit package pricing display/deltas.
- Do not change Z07 aero behavior, J56/J57 brake behavior, wheel package peer switching, or default ROY include rules except as necessary to add the blocker groups.
- Do not expand this into ZR1/ZR1X readiness or wheel modeling.
- Do not refactor `form-app/app.js`.

## Validation plan

Before writing:

```sh
git branch --show-current
git status --short --branch
test ! -e '~$stingray_master.xlsx'
```

After workbook write, verify saved workbook package and source rows:

```sh
.venv/bin/python scripts/validate_workbook_package.py stingray_master.xlsx
.venv/bin/python - <<'PY'
# Read-only openpyxl verification of the three z06_rule_groups rows
# and 27 z06_rule_group_members rows on disk.
PY
```

Regenerate:

```sh
.venv/bin/python scripts/generate_z06_form.py
.venv/bin/python scripts/generate_stingray_form.py
```

Targeted tests:

```sh
node --test tests/z06-form-data-draft.test.mjs
node --test tests/z06-performance-package-interactions.test.mjs
node --test tests/z06-runtime-rule-corrections.test.mjs
node --test tests/z06-runtime-promotion.test.mjs
node --test tests/multi-model-runtime-switching.test.mjs
```

Because this touches live `form-app/data.js` and runtime disabled-state behavior, also run the current full suite if generated diffs are broader than the Z06 wheel blocker groups:

```sh
node --test tests/stingray-form-regression.test.mjs
node --test tests/stingray-generator-stability.test.mjs
node --test tests/grand-sport-contract-preview.test.mjs
node --test tests/grand-sport-draft-data.test.mjs
node --test tests/grand-sport-rule-audit.test.mjs
node --test tests/z06-contract-preview.test.mjs
node --test tests/z06-form-data-draft.test.mjs
node --test tests/z06-runtime-promotion.test.mjs
node --test tests/multi-model-runtime-switching.test.mjs
node --test tests/z06-performance-package-interactions.test.mjs
node --test tests/z06-runtime-rule-corrections.test.mjs
```

Manual browser smoke:

- Serve `form-app` locally.
- Select Z06 coupe 1LZ.
- Select `PDB`, verify aluminum/default wheel cards are visually disabled while `ROY` is auto-added.
- Select `ROZ`, verify aluminum/default wheel cards remain visually disabled and `ROY` is released.
- Repeat for `PDD` and `PDF`.
- Verify `ROY`, `ROZ`, and `STZ` remain switchable under each package.
- Check browser console for JavaScript errors.

## Approval question

Approve this pass to add workbook-owned `excludes_any` aluminum-wheel blocker groups for `PDB`/`PDD`/`PDF`, regenerate Z06/live artifacts, and add the focused generated-data/runtime tests above?
