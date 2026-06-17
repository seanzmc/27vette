# Stingray Rear Script Exclusive Group Spec

Recommended reasoning level: high.

## Status

Approved and implemented 2026-06-17.

Implementation evidence:

- `stingray_master.xlsx` now has `exclusive_groups.excl_rear_script_badges` with `selection_mode=single_within_group` and active members `opt_rik_001`, `opt_rin_001`, and `opt_sl8_001` in `exclusive_group_members`.
- The six scoped pairwise Stingray `rule_mapping` rows among `opt_rik_001`, `opt_rin_001`, and `opt_sl8_001` were removed after contract comparison confirmed the new exclusive group owns the behavior.
- `form-output/stingray-form-data.json` and `form-app/data.js` were regenerated; the intended contract drift is one added Stingray exclusive group and six removed pairwise rules.
- `tests/stingray-form-regression.test.mjs` now asserts the generated group, absence of pairwise rear-script rules, and replacement behavior through the existing accessory exclusive-group runtime test.

## Preflight Note: Display-Order Guard

The previous recommended next pass was a display-order guard. Current source inspection shows that guard already exists and is covered:

- `scripts/corvette_form_generator/schema_validation.py` has `validate_option_display_order_uniqueness()` and calls it from `validate_workbook_schema()` for metadata-discovered `source_option_sheet` sheets.
- `tests/test_schema_validation_metadata.py` has `test_option_display_order_duplicates_are_rejected_in_standard_sections()` and expects `duplicate_option_display_order` for active duplicate standard-section rows.
- `tests/workbook-schema-standardization.test.mjs` runs `scripts/validate_workbook_schema.py stingray_master.xlsx` and currently passes against the live workbook.

Because the durable display-order guard is already present, this spec targets the next persisting runtime/workbook cleanup item: Stingray rear-script badge behavior.

## Diagnosis

Stingray rear Corvette script badge choices still express mutual exclusion through six pairwise `rule_mapping` rows, while Grand Sport and Z06 already express the same three-RPO choice set as workbook-owned exclusive groups. The current Stingray representation works as a blocking/exclusion rule, but it preserves stale row-level duplication after the active models have converged on a cleaner exclusive-group contract.

Current evidence inspected:

- `docs/persisting-audit-findings-2026-06-14.md` lists the issue under “Stingray rear script badges still use pairwise excludes instead of an exclusive group.”
- `stingray_options` has three active selectable LPO Exterior choices:
  - row 57: `opt_rin_001`, RPO `RIN`, `Arctic White Rear Corvette Script Badge`, `sec_lpoe_001`, `display_order=160`.
  - row 58: `opt_sl8_001`, RPO `SL8`, `Edge Red Rear Corvette Script Badge`, `sec_lpoe_001`, `display_order=161`.
  - row 59: `opt_rik_001`, RPO `RIK`, `Torch Red Rear Corvette Script Badge`, `sec_lpoe_001`, `display_order=162`.
- Each Stingray option row still carries the raw GM source incompatibility text in its source-detail field:
  - `RIN`: `1. Not available with RIK, SL8.`
  - `SL8`: `1. Not available with RIK, RIN.`
  - `RIK`: `1. Not available with RIN, SL8.`
- `rule_mapping` currently has six active pairwise `excludes` rows among those options:
  - `rule_opt_rik_001_excludes_opt_rin_001`
  - `rule_opt_rik_001_excludes_opt_sl8_001`
  - `rule_opt_rin_001_excludes_opt_rik_001`
  - `rule_opt_rin_001_excludes_opt_sl8_001`
  - `rule_opt_sl8_001_excludes_opt_rik_001`
  - `rule_opt_sl8_001_excludes_opt_rin_001`
- Stingray `exclusive_groups` currently has no rear-script group and `exclusive_group_members` has no `opt_rik_001` / `opt_rin_001` / `opt_sl8_001` rear-script group membership.
- Grand Sport already has:
  - `grandSport_exclusive_groups.gs_excl_rear_script_badges`, `selection_mode=single_within_group`, `active=True`.
  - members `opt_rik_001@10`, `opt_rin_001@20`, `opt_sl8_001@30`.
- Z06 already has:
  - `z06_exclusive_groups.z06_excl_rear_script_badges`, `selection_mode=single_within_group`, `active=True`.
  - members `opt_rik_001@10`, `opt_rin_001@20`, `opt_sl8_001@30`.
- Current `form-app/data.js` emits no Stingray rear-script exclusive group and still emits the six Stingray pairwise rules; Grand Sport and Z06 emit equivalent exclusive groups and no pairwise rear-script rules.
- Existing tests cover generic exclusive-group behavior in `tests/stingray-form-regression.test.mjs`, including source guards for generic runtime exclusive-group handling and accessory-group replacement behavior.

Root cause:

Stingray kept legacy pairwise rule rows while Grand Sport and Z06 moved equivalent rear-script badge color choices into explicit exclusive-group rows. The business rule is workbook-owned and can be represented with existing Stingray `exclusive_groups` / `exclusive_group_members` sheets; no runtime JavaScript exception or generator branch is needed.

Risk level: medium. This is a workbook source-data behavior change for active Stingray. Intended output shape changes from pairwise `rules` to one `exclusiveGroups` entry, and intended customer interaction changes from blocking disabled peers to radio-style replacement within the LPO Exterior section.

Change type: workbook/data + generated artifacts + tests/docs. No runtime JS logic change intended.

## Ownership Decision

- The mutual-exclusion behavior belongs in workbook source sheets, not runtime JavaScript.
- Use the existing Stingray exclusive-group sheets:
  - `exclusive_groups`
  - `exclusive_group_members`
- Do not add a new sheet, helper module, runtime branch, or model/RPO-specific JavaScript behavior.
- Preserve the raw GM source-detail text on the option rows. Removing pairwise `rule_mapping` rows should not remove source evidence because the option source-detail fields still carry the incompatibility text.

## Recommended Scope

### Implement now

1. Add a Stingray rear-script exclusive group.
   - Add `exclusive_groups` row:
     - `group_id`: `excl_rear_script_badges`
     - `selection_mode`: `single_within_group`
     - `active`: `True`
     - `notes`: `Rear Corvette script badge color choices are mutually exclusive within the LPO Exterior section.`
   - Add `exclusive_group_members` rows:
     - `excl_rear_script_badges`, `opt_rik_001`, `display_order=10`, `active=True`
     - `excl_rear_script_badges`, `opt_rin_001`, `display_order=20`, `active=True`
     - `excl_rear_script_badges`, `opt_sl8_001`, `display_order=30`, `active=True`

2. Retire the redundant Stingray pairwise excludes.
   - Remove the six `rule_mapping` rows listed in Diagnosis if generated-contract comparison confirms the new exclusive group owns the behavior.
   - Do not add a disabled/stale marker row to `rule_mapping`; the current reduced header set has no active/disabled lifecycle column, and the raw source evidence remains on the option rows.

3. Add tests.
   - Extend `tests/stingray-form-regression.test.mjs` to expect `excl_rear_script_badges` in the Stingray accessory exclusive-group list.
   - Add or extend a runtime test proving selecting one of `RIK` / `RIN` / `SL8` removes the other rear-script badge selections from `state.selected` and `state.userSelected` without leaving peers disabled by pairwise rules.
   - Add a generated-data assertion that no Stingray generated `rules` remain among `opt_rik_001`, `opt_rin_001`, and `opt_sl8_001` after the exclusive group is emitted.

4. Regenerate affected artifacts.
   - Run `scripts/generate_form.py --model stingray`.
   - Run `scripts/generate_registry.py`.
   - Review generated diffs. Allowed generated drift is limited to:
     - Stingray `exclusiveGroups` gaining `excl_rear_script_badges` with the three members above.
     - Stingray `rules` losing the six pairwise rear-script excludes.
     - `form-app/data.js` reflecting the same generated contract update.
     - timestamps in generated artifacts.
   - No choices, prices, interiors, color overrides, standard equipment, dealer payload fields, or non-Stingray model contracts should change.

5. Update docs after implementation.
   - Mark this spec approved/implemented.
   - Update `docs/persisting-audit-findings-2026-06-14.md` to move the Stingray rear-script issue to completed and advance the recommended next pass.

### Explicitly defer

- Cross-model wheel/roof ordering drift.
- Grand Sport LS6 exclusive-member order drift.
- Cross-model customer copy convergence.
- Z06 option-id suffix/no-RPO ID drift.
- Future-model scaffold cleanup.
- Runtime refactors or generic exclusive-group algorithm changes.

## Exact Files and Sheets to Change

Workbook source sheets:

- `stingray_master.xlsx`
  - `exclusive_groups`
  - `exclusive_group_members`
  - `rule_mapping`

Generated artifacts after regeneration:

- `form-output/stingray-form-data.json`
- `form-output/stingray-form-data.csv`
- generated workbook `form_*` sheets emitted by `scripts/generate_form.py --model stingray`
- `form-app/data.js` after `scripts/generate_registry.py`

Tests:

- `tests/stingray-form-regression.test.mjs`

Docs:

- `docs/stingray-rear-script-exclusive-group-spec.md`
- `docs/persisting-audit-findings-2026-06-14.md`

No expected source-code changes outside tests/docs unless implementation exposes a generator bug in existing exclusive-group handling.

## Constraints

- Preserve live customer/dealer behavior except the intentional rear-script interaction shift from blocking pairwise excludes to exclusive-group radio replacement.
- No runtime JavaScript product/RPO-specific exception.
- No new dependencies.
- No visual/CSS/layout change.
- No dealer endpoint, Turnstile, payload shape, or submission semantics change.
- No workbook schema expansion.
- No hand edits to generated `form_*` sheets, `form-output/*`, or `form-app/data.js`; regenerate them.
- Close Excel before workbook writes. If `~$stingray_master.xlsx` exists, stop and verify lock/staleness before writing.
- Save workbook changes through `save_workbook_safely()` and verify saved rows on disk before claiming the workbook landed.
- Preserve raw source-detail evidence on the three option rows.
- Respect any pre-existing dirty work; inspect overlapping diffs before editing.

## Required Preflight Before Editing

1. Confirm branch/status and Excel lock:

```sh
git status --short --branch
ls -la '~$stingray_master.xlsx' 2>/dev/null || true
```

2. Re-probe workbook rows before writing:

```sh
.venv/bin/python - <<'PY'
from openpyxl import load_workbook
wb = load_workbook('stingray_master.xlsx', read_only=True, data_only=True)
# Print RIK/RIN/SL8 rows from stingray_options, rule_mapping, exclusive_groups,
# exclusive_group_members, grandSport_exclusive_* and z06_exclusive_*.
PY
```

3. Snapshot generated contracts before regeneration:

```sh
cp form-output/stingray-form-data.json /tmp/before-stingray-form-data.json
cp form-app/data.js /tmp/before-form-app-data.js
```

4. Stop and revise this spec if:

- the three Stingray option rows are no longer active/selectable in `sec_lpoe_001`,
- the six pairwise rule rows are already gone,
- a Stingray rear-script exclusive group already exists,
- the generated-data contract already differs from the evidence above,
- or implementation requires runtime JS product-specific behavior.

## Implementation Plan

1. Add RED tests first.
   - Assert the Stingray generated contract includes `excl_rear_script_badges` with `opt_rik_001`, `opt_rin_001`, `opt_sl8_001` after implementation.
   - Assert no generated pairwise rear-script rules remain after implementation.
   - Assert runtime replacement behavior for selecting a rear-script badge peer.

2. Write the workbook source edit.
   - Use a small repo-local or temporary Python apply script that loads `stingray_master.xlsx`, modifies only the three scoped sheets, saves through `save_workbook_safely()`, then is deleted if it is one-pass tooling.
   - Add the group/member rows exactly once; make the script idempotent while developing, but do not keep it as routine workflow documentation after verification.
   - Delete the six scoped `rule_mapping` rows by `rule_id`.

3. Verify workbook on disk.
   - Reopen with `openpyxl` read-only.
   - Confirm the new group and three members exist.
   - Confirm the six pairwise `rule_mapping` rows are absent.
   - Confirm the three option source-detail fields still carry the original incompatibility text.

4. Regenerate and compare.
   - Run Stingray generation and registry publication.
   - Compare `form-output/stingray-form-data.json` against `/tmp/before-stingray-form-data.json` with timestamp-insensitive tooling and manual diff review.
   - Confirm only the allowed generated drift occurred.

5. Update docs and run gates.

## Validation Plan

Targeted gates:

```sh
.venv/bin/python scripts/generate_form.py --model stingray
.venv/bin/python scripts/generate_registry.py
.venv/bin/python scripts/validate_workbook_schema.py stingray_master.xlsx
node scripts/compare-generated-contracts.mjs /tmp/before-stingray-form-data.json form-output/stingray-form-data.json
node --test tests/stingray-form-regression.test.mjs
node --test tests/multi-model-runtime-switching.test.mjs
git diff --check
```

If `form-app/data.js` changes beyond the Stingray model entry or registry timestamp-equivalent churn, also run:

```sh
node --test tests/grand-sport-contract-preview.test.mjs
node --test tests/grand-sport-draft-data.test.mjs
node --test tests/z06-contract-preview.test.mjs
node --test tests/z06-form-data-draft.test.mjs
```

Manual/browser verification:

- Browser-smoke Stingray LPO Exterior only if runtime tests pass but generated diff or implementation suggests UI ordering/disabled-state behavior may differ beyond the intended radio replacement.
- If browser smoke is run, verify selecting `RIK`, then `RIN`, then `SL8` leaves only the latest rear-script badge selected and the build summary/dealer payload include only that RPO.

## Risks

- Intentional behavior change: selected rear-script badge peers will be replaced instead of blocked/disabled by pairwise excludes.
- Removing pairwise rules could hide source evidence if the option rows did not preserve raw detail text; preflight and post-write verification must prove the raw detail remains.
- Group member order differs from Stingray option-sheet display order. This spec follows existing Grand Sport/Z06 group member order (`RIK`, `RIN`, `SL8`) while preserving Stingray option display order (`RIN`, `SL8`, `RIK`). If implementation proves member order affects customer-facing display, stop and revise the spec.
- Generated artifact churn can mask unrelated changes; snapshot and compare before regeneration.
- Workbook writes are risky if Excel is open; do not bypass lock-file safety.

## Non-Goals

- No cross-model copy normalization.
- No LPO Exterior display-order cleanup beyond preserving existing Stingray option order.
- No Grand Sport/Z06 rear-script changes.
- No runtime JS refactor.
- No workbook schema changes.
- No generated artifact hand edits.
- No dealer submission changes.

## Handoff Requirements

The implementation handoff must report:

- What changed: workbook sheets/rows, generated artifacts, tests, docs, and the intentional Stingray rear-script interaction impact.
- What did not change: runtime JS product logic, visual/CSS layout, dealer boundaries, non-Stingray models, prices/interiors/standard equipment.
- Gate results: exact commands and pass/fail output.
- Manual verification pending or skipped with reason.
- Next step guidance: likely cross-model ordering pass unless this implementation exposes a more urgent workbook-rule issue.

## Approval Question

Approve this Stingray rear-script exclusive-group pass as scoped above?

Recommended answer: `rear-script pass approved.`
