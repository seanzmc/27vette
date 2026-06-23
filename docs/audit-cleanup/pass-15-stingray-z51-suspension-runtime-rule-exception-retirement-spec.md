# Pass 15 — Stingray Z51 Suspension Runtime-Rule-Exception Retirement Spec

Status: Spec only. Do not implement until approved.
Date: 2026-06-23
Recommended reasoning level for implementation agent: high.

Source context:

- `AGENTS.md`
- `docs/metadata-runtime-redundancy-6-23.md`
- `docs/Audit-route-map.md`
- `docs/audit-cleanup/pass-14-stingray-gba-zyc-runtime-rule-exception-retirement-spec.md`
- `27vette-workbook-guard` reference `segregated-workbook-behavior-retirement.md`
- `27vette-workbook-guard` reference `required-default-and-soft-default-rules.md`
- `27vette-workbook-guard` reference `workbook-first-existing-pipelines.md`

## Goal

Retire the two remaining active `runtime_rule_exceptions` rows for Stingray Z51 suspension behavior:

- `ex_z51_fe1`: `opt_z51_001` removes `opt_fe1_001`.
- `ex_z51_fe2`: `opt_z51_001` removes `opt_fe2_001`.

Move this behavior into normal workbook rule ownership while preserving current live runtime behavior:

- FE1 remains the default visible standard suspension when no other suspension is selected or auto-added.
- FE2 remains a selectable non-Z51 suspension option.
- Selecting Z51 removes FE1/FE2 and auto-adds FE3.
- FE1/FE2 cannot be clicked back in while Z51 is selected.
- FE2 selected first must not block selecting Z51.
- FE4 remains selectable only when Z51 is selected and still includes B4Z.

This pass should leave `runtime_rule_exceptions` empty for Stingray if parity is proven.

## Diagnosis

Change type for this spec: docs-only.

Change type for implementation: mixed workbook/data + generated artifacts + tests + docs/spec closure. Risk level: medium-high because current live behavior depends on a segregated exception helper overriding normal direct-rule direction for one path.

Root cause: the last two `runtime_rule_exceptions` rows encode Z51 package precedence over suspension choices even though normal workbook rule rows plus the existing default-selection rule can express the same business behavior.

Current active exception rows:

- Sheet: `runtime_rule_exceptions`
- Rows:
  - `ex_z51_fe1`
    - `model_key=stingray`
    - `source_option_id=opt_z51_001` / Z51 Performance Package
    - `target_option_id=opt_fe1_001` / Corvette Standard Suspension
    - `exception_type=remove_target_when_source_selected`
    - wildcard body/trim/variant scopes
    - disabled reason: `Replaced by FE3 Z51 performance suspension.`
  - `ex_z51_fe2`
    - `model_key=stingray`
    - `source_option_id=opt_z51_001` / Z51 Performance Package
    - `target_option_id=opt_fe2_001` / Magnetic Selective Ride Control Suspension
    - `exception_type=remove_target_when_source_selected`
    - wildcard body/trim/variant scopes
    - disabled reason: `Not available with Z51 Performance Package.`

Current normal workbook graph is not equivalent without a replacement:

- `rule_mapping.rule_opt_z51_001_includes_opt_fe3_001` already expresses that Z51 includes FE3.
- `default_selection_rules.default_fe1` already expresses FE1 as the default suspension unless another suspension-section option is selected or auto-added.
- `rule_mapping.rule_opt_fe2_001_excludes_opt_z51_001` is a reverse direct exclude parsed from FE2 source detail. If the exceptions were deleted while this reverse row remained, selecting FE2 first would make Z51 unavailable. Current live behavior allows Z51 to be selected after FE2 and then removes FE2.
- No current `rule_mapping`, `rule_groups`, or `exclusive_groups` row owns Z51 -> FE1 or Z51 -> FE2 removal without `runtime_rule_exceptions`.
- There is no active suspension exclusive group. Creating one for FE1/FE2/FE3/FE4 would be broader than this pass and risks changing FE3/FE4 package/include behavior.

Canonical owner for this pass:

- `rule_mapping` direct excludes from Z51 to FE1 and FE2:
  - add `rule_opt_z51_001_excludes_opt_fe1_001`
  - add `rule_opt_z51_001_excludes_opt_fe2_001`
- delete obsolete reverse direct row `rule_opt_fe2_001_excludes_opt_z51_001`
- preserve `default_selection_rules.default_fe1`
- preserve all existing Z51 include rules, including `rule_opt_z51_001_includes_opt_fe3_001`
- remove `runtime_rule_exceptions.ex_z51_fe1` and `runtime_rule_exceptions.ex_z51_fe2` only after generated-data and browser/runtime parity proof

Do not model this pass as a new suspension exclusive group. A suspension exclusive group may be worth a future product-structure review, but it would also touch FE3/FE4 semantics and is not required to retire these two exception rows.

## Evidence inspected for this spec

Current branch/worktree:

- `git status --short --branch`: `## schema-ingestion-normalization...origin/main`

Current documentation evidence:

- `docs/metadata-runtime-redundancy-6-23.md` reports `runtime_rule_exceptions` reduced by Pass 14 to exactly two active rows: `ex_z51_fe1` and `ex_z51_fe2`.
- `docs/audit-cleanup/pass-14-stingray-gba-zyc-runtime-rule-exception-retirement-spec.md` records Pass 14 completion and defers Z51/FE1/FE2 as the remaining suspension/default ownership class.

Current workbook evidence from read-only `openpyxl` inspection:

- `runtime_rule_exceptions` active rows are exactly:
  - `ex_z51_fe1`: Z51 removes FE1; disabled reason `Replaced by FE3 Z51 performance suspension.`
  - `ex_z51_fe2`: Z51 removes FE2; disabled reason `Not available with Z51 Performance Package.`
- `stingray_options`:
  - `opt_z51_001`: RPO Z51, section `sec_perf_001`, active True, selectable True, price 5395, display order 30.
  - `opt_fe1_001`: RPO FE1, section `sec_susp_001`, active True, selectable True, price 0, display order 10.
  - `opt_fe2_001`: RPO FE2, section `sec_susp_001`, active True, selectable True, price 1895, display order 11, source detail says not available with Z51.
  - `opt_fe3_001`: RPO FE3, section `sec_susp_001`, active True, selectable False, display order 12, source detail says included and only available with Z51.
  - `opt_fe4_001`: RPO FE4, section `sec_susp_001`, active True, selectable True, price 1895, display order 20, source detail says requires Z51 and includes B4Z.
- `stingray_ovs`:
  - FE1 has 6 `standard` rows.
  - FE2, FE3, FE4, and Z51 each have 6 `available` rows.
- `rule_mapping` related rows:
  - `rule_opt_fe2_001_excludes_opt_z51_001` exists and is the reverse direction that must not survive this pass.
  - `rule_opt_z51_001_includes_opt_fe3_001` exists and must be preserved.
  - Z51 include rows for G0K, G96, J55, M1N, QTU, T0A, and V08 exist and must be preserved.
  - `rule_opt_fe4_001_requires_opt_z51_001` exists and must be preserved.
  - `rule_opt_fe4_001_includes_opt_b4z_001` exists and must be preserved.
- `default_selection_rules`:
  - `default_fe1` targets `opt_fe1_001` with `condition_type=unless_selected_section`, `condition_id=sec_susp_001`, wildcard scopes, priority 10.
- `exclusive_groups` / `exclusive_group_members`:
  - No active suspension exclusive group currently contains FE1/FE2/FE3/FE4/Z51.
- `rule_groups` / `rule_group_members`:
  - No current grouped rule owns Z51 -> FE1 or Z51 -> FE2.

Current generated contract evidence from `form-output/runtime/stingray-runtime-contract.json`:

- `runtimeRuleExceptions` emits exactly `[ex_z51_fe1, ex_z51_fe2]`.
- `rules` count is 140.
- `rules` includes `rule_opt_fe2_001_excludes_opt_z51_001`.
- `rules` includes `rule_opt_z51_001_includes_opt_fe3_001` with `auto_add=True`.
- `rules` includes `rule_opt_fe4_001_requires_opt_z51_001` and `rule_opt_fe4_001_includes_opt_b4z_001`.
- `defaultSelectionRules` includes `default_fe1` with `condition_id=sec_susp_001`.
- `ruleGroups` has no suspension/Z51 group for FE1/FE2.
- `exclusiveGroups` has no suspension group for FE1/FE2/FE3/FE4.
- Current 1LT coupe generated choices keep Z51, FE1, FE2, FE3, and FE4 emitted with expected active/selectable/status values.

Current test evidence:

- `tests/stingray-form-regression.test.mjs` currently pins:
  - `runtimeRuleExceptions` IDs are `[ex_z51_fe1, ex_z51_fe2]`.
  - Z51 includes FE3.
  - FE3 renders as an auto-only suspension tile and is not manually selectable.
  - FE4 requires Z51.
  - Initial FE1 default selected state is de-duped to visible `opt_fe1_001`.
  - Selecting Z51 removes FE1/FE2 and keeps FE3 auto-added.
  - Selecting FE2 suppresses FE1.
- `tests/stingray-generator-stability.test.mjs` currently pins `jsonData.rules.length === 140` and must be updated if this pass adds two direct rules and removes one direct rule.

## Exact implementation scope after approval

### Workbook source edits

Edit only `stingray_master.xlsx` source sheets listed below, through a safe-save workbook script using `save_workbook_safely()`.

1. `rule_mapping`

   Add:

   - `rule_id=rule_opt_z51_001_excludes_opt_fe1_001`
   - `source_id=opt_z51_001`
   - `rule_type=excludes`
   - `target_id=opt_fe1_001`
   - `original_detail_raw=Z51 includes FE3 Z51 performance suspension and replaces FE1 standard suspension.`
   - `body_style_scope=` blank
   - `runtime_action=` blank
   - `disabled_reason=Replaced by FE3 Z51 performance suspension.`

   Add:

   - `rule_id=rule_opt_z51_001_excludes_opt_fe2_001`
   - `source_id=opt_z51_001`
   - `rule_type=excludes`
   - `target_id=opt_fe2_001`
   - `original_detail_raw=FE2 is not available with Z51 Performance Package.`
   - `body_style_scope=` blank
   - `runtime_action=` blank
   - `disabled_reason=Not available with Z51 Performance Package.`

   Delete:

   - `rule_opt_fe2_001_excludes_opt_z51_001`

2. `runtime_rule_exceptions`

   Delete:

   - `ex_z51_fe1`
   - `ex_z51_fe2`

### Generated artifacts

Regenerate, do not hand-edit:

- `form-output/runtime/stingray-runtime-contract.json`
- `form-output/stingray-form-data.json`
- `form-app/data.js`

### Tests

Update focused expectations in:

- `tests/stingray-form-regression.test.mjs`
- `tests/stingray-generator-stability.test.mjs`

### Documentation/spec closure

Update after implementation:

- `docs/audit-cleanup/pass-15-stingray-z51-suspension-runtime-rule-exception-retirement-spec.md`
- `docs/metadata-runtime-redundancy-6-23.md`
- `docs/Audit-route-map.md`

## Explicit non-scope

Do not change:

- `form-app/app.js` unless direct-rule parity fails and the spec is amended before implementation.
- `default_selection_rules.default_fe1`.
- Z51 include rows other than reviewing that they still exist after regeneration.
- FE3 source option metadata, selectability, display order, or auto-only behavior.
- FE4 requires/includes behavior.
- `rule_groups` or `exclusive_groups` for suspension behavior in this pass.
- `variant_option_overrides`, `grandSport_variant_overrides`, or `z06_variant_overrides`.
- Grand Sport or Z06 workbook source sheets.
- Dealer submission endpoint, payload shape, Turnstile behavior, or deployment paths.
- Visual CSS/HTML.

If the direct `rule_mapping` migration cannot prove parity in generated data and browser/runtime behavior, stop and bring back an amended spec. Do not silently solve it with a JavaScript exception, a new broad suspension exclusive group, or a new workbook sheet.

## Constraints

- Follow `AGENTS.md` spec-first rules. Do not implement until this spec is approved.
- Use current repo/workbook evidence only. Do not rely on archived `codex-context.md`.
- Workbook owns the business rule; do not hide this in Python or JavaScript.
- Keep the implementation pass limited to the remaining two runtime exception rows and the one reverse FE2 -> Z51 direct row required for parity.
- Use `save_workbook_safely()` for workbook writes.
- Stop if `~$stingray_master.xlsx` exists or Excel appears to have the workbook open.
- Reopen/inspect the saved workbook on disk before claiming workbook edits landed.
- No new dependencies.
- No broad refactor.
- No live behavior change for Stingray, Grand Sport, or Z06.

## Expected generated-contract deltas

Expected intentional deltas after regeneration:

- `data.runtimeRuleExceptions` becomes an empty array for Stingray.
- `data.rules` gains:
  - `rule_opt_z51_001_excludes_opt_fe1_001`
  - `rule_opt_z51_001_excludes_opt_fe2_001`
- `data.rules` removes:
  - `rule_opt_fe2_001_excludes_opt_z51_001`
- `data.rules` still contains:
  - `rule_opt_z51_001_includes_opt_fe3_001`
  - `rule_opt_fe4_001_requires_opt_z51_001`
  - `rule_opt_fe4_001_includes_opt_b4z_001`
- `data.defaultSelectionRules.default_fe1` is unchanged.
- FE1, FE2, FE3, FE4, and Z51 generated choices keep current active/selectable/status/display-order behavior across all six Stingray variants.
- Stingray `rules` count changes from 140 to 141 because the pass adds two direct rules and removes one reverse direct rule.
- Non-Stingray runtime contracts should be unchanged except registry timestamp/metadata noise from `generate_registry.py`, if any.

Unexpected deltas to stop on:

- Any FE1/FE2/FE3/FE4/Z51 option row count, price, section, active/selectable/status, display order, or display behavior drift.
- Any change to FE4 requirements/includes.
- Any new suspension exclusive group or grouped rule not explicitly approved.
- Any Grand Sport/Z06 data change beyond timestamp-only registry churn.
- Any runtime JavaScript behavior/code change not explicitly justified by a parity failure and amended spec.

## Required tests and runtime behavior proof

Update/add RED tests before the workbook edit where practical. The final tests should prove source ownership and runtime behavior:

1. Generated/source ownership:
   - `data.runtimeRuleExceptions` is empty.
   - `rule_opt_z51_001_excludes_opt_fe1_001` is emitted as an active direct exclude from Z51 to FE1 with disabled reason `Replaced by FE3 Z51 performance suspension.`
   - `rule_opt_z51_001_excludes_opt_fe2_001` is emitted as an active direct exclude from Z51 to FE2 with disabled reason `Not available with Z51 Performance Package.`
   - `rule_opt_fe2_001_excludes_opt_z51_001` is absent from generated `data.rules`.
   - `rule_opt_z51_001_includes_opt_fe3_001` remains present and auto-adds FE3.
   - `default_fe1` remains present and unchanged.
   - No suspension `ruleGroups` or `exclusiveGroups` are introduced.
2. Runtime behavior:
   - Initial Stingray coupe 1LT reset/reconcile selects exactly one FE1 visible suspension choice.
   - Selecting Z51 from the initial FE1-default path removes FE1 and auto-adds FE3.
   - While Z51 is selected, FE1 has disabled reason `Replaced by FE3 Z51 performance suspension.` and cannot be clicked back in.
   - Selecting FE2 first suppresses FE1 but leaves Z51 selectable.
   - Selecting Z51 after FE2 removes FE2 and auto-adds FE3.
   - While Z51 is selected, FE2 has disabled reason `Not available with Z51 Performance Package.` and cannot be clicked back in.
   - Clearing Z51, if the UI path allows it, restores the FE1 default and removes FE3 auto-add.
   - FE4 remains disabled before Z51 with `Requires Z51 Performance Package.`, becomes selectable after Z51, and still includes B4Z.
3. No adjacent behavior drift:
   - Current Z51 package auto-added RPO summary still includes FE3 in the performance/mechanical section, not as a duplicate selectable suspension line.
   - GBA/ZYC grouped exclusion behavior from Pass 14 still passes.
   - NGA/NWI exhaust behavior from Pass 13 still passes.
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

- Snapshot the pre-change `form-output/runtime/stingray-runtime-contract.json`.
- Compare pre/post generated contract with `node scripts/compare-generated-contracts.mjs` and classify the intentional deltas above.
- Probe `form-app/data.js` to ensure promoted runtime data matches the regenerated Stingray contract and no Grand Sport/Z06 payload drift was introduced.

Local browser/manual verification required before final handoff:

- Serve `form-app` locally.
- Stingray coupe 1LT path A:
  - reset/reconcile;
  - confirm FE1 is selected exactly once;
  - select Z51;
  - confirm FE1 is removed/disabled and cannot be clicked back in;
  - confirm FE3 is auto-added and appears in the correct summary section.
- Stingray coupe 1LT path B:
  - reset/reconcile;
  - select FE2;
  - confirm Z51 remains clickable;
  - select Z51;
  - confirm FE2 is removed/disabled and cannot be clicked back in;
  - confirm FE3 is auto-added.
- Stingray coupe 1LT path C:
  - confirm FE4 is disabled before Z51;
  - select Z51;
  - confirm FE4 becomes selectable;
  - select FE4 and confirm B4Z is included.
- Smoke model switching to Grand Sport and Z06 to confirm no obvious runtime break.

## Risks and mitigations

- Risk: deleting the exceptions while leaving `rule_opt_fe2_001_excludes_opt_z51_001` changes behavior by making Z51 unavailable after FE2 is selected.
  - Mitigation: delete the reverse FE2 -> Z51 row in the same approved pass and add tests proving Z51 can replace selected FE2.
- Risk: adding only Z51 -> FE2 and forgetting FE1 leaves the visible FE1 default selected alongside Z51/FE3.
  - Mitigation: add and test Z51 -> FE1 direct exclude plus runtime selected-state checks.
- Risk: replacing the exceptions with a broad suspension exclusive group changes FE3/FE4 behavior.
  - Mitigation: do not create suspension exclusive-group metadata in this pass.
- Risk: generated-contract tests pass but local click behavior regresses.
  - Mitigation: require browser/manual proof for FE1, FE2, FE3, and FE4 paths.
- Risk: generated registry refresh introduces unrelated Grand Sport/Z06 diffs.
  - Mitigation: inspect generated diffs and stop/restore unrelated drift.

## Non-goals

- Do not migrate variant override sheets.
- Do not create a suspension exclusive group or grouped rule.
- Do not change FE3 option-card selectability or auto-add behavior.
- Do not change FE4 requirements/includes.
- Do not delete `runtime_action`, change direct-rule scope semantics, or trim generated rule payload fields.
- Do not change runtime JavaScript product behavior.
- Do not change dealer submission behavior.

## Approval prompt

Approve Pass 15 implementation exactly as scoped above: add Z51 -> FE1 and Z51 -> FE2 direct excludes, delete reverse FE2 -> Z51 direct exclude, delete `runtime_rule_exceptions.ex_z51_fe1` and `runtime_rule_exceptions.ex_z51_fe2`, regenerate, update focused tests/docs, and prove generated-data plus local-runtime parity.
