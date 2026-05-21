# Stingray + Grand Sport Engine Cover Structure Migration Spec

> For Hermes: this is a spec-first 27vette plan. Do not implement until the user approves. If implementing task-by-task, use subagent-driven-development or a single focused pass with workbook safety checks.

Goal: migrate Stingray engine-cover data/default behavior to the Grand Sport structure where Grand Sport is superior, clean up inactive Grand Sport legacy engine-cover rows, and adopt Stingray's clearer D3V body-style scoping for Grand Sport.

Architecture: keep business decisions in workbook source sheets, regenerate generated workbook sheets/artifacts, and preserve the generic runtime exclusive-group/default-selection mechanics already in `form-app/app.js`. Generated `form_*` sheets, `form-output/*`, and `form-app/data.js` are outputs, not hand-edit targets.

Change type: mixed workbook/data + generated artifacts + tests. Runtime behavior should remain behavior-compatible and should not require runtime JS changes unless tests expose a generic data-driven gap.

---

## Diagnosis

### Root cause / current asymmetry

The current engine-cover user behavior is mostly correct in both models, but the source structures differ:

1. Stingray coupe BC7 default is still represented by a generated default rule:
   - Generated artifact: `form-output/stingray-form-data.json`
   - Data key: `defaultSelectionRules`
   - Row: `default_bc7`, `target_option_id=opt_bc7_001`, `condition_type=always`, `body_style_scope=coupe`
   - Runtime path: `form-app/app.js:addGeneratedDefaultChoices()`

2. Grand Sport coupe BC7 default is represented directly as workbook-authored choice metadata:
   - Workbook sheet: `grandSport_variant_overrides`
   - Rows: `opt_bc7_001` for `1lt_e07`, `2lt_e07`, `3lt_e07`
   - Metadata: `display_behavior=default_selected`
   - Runtime path: `form-app/app.js:addWorkbookDefaultChoices()`

3. Grand Sport has inactive legacy paid-cover source rows in `grandSport_options`:
   - `opt_bcp_001` / `BCP`
   - `opt_bcs_001` / `BCS`
   - `opt_bc4_001` / `BC4`
   The active runtime choices are the `_002` rows:
   - `opt_bcp_002`
   - `opt_bcs_002`
   - `opt_bc4_002`
   The exclusive group already correctly uses the active `_002` rows, but the inactive rows still create workbook/generator/audit noise.

4. Grand Sport D3V include/price behavior is less explicitly scoped than Stingray:
   - Stingray paid-cover includes of `D3V` are body-style scoped to coupe in generated rules.
   - Grand Sport has active paid-cover includes of `D3V` that are effectively safe because `D3V` is unavailable on convertible, but the rules are not as self-documenting.
   - Desired target: Grand Sport should adopt Stingray's explicit coupe scoping for `D3V` includes/price rules where `D3V` is coupe-only.

### Evidence inspected

Workbook source sheets:
- `stingray_options`
- `grandSport_options`
- `rule_mapping`
- `grandSport_rule_mapping`
- `exclusive_groups`
- `exclusive_group_members`
- `grandSport_exclusive_groups`
- `grandSport_exclusive_members`
- `price_rules`
- `grandSport_price_rules`
- `grandSport_variant_overrides`

Generated/runtime artifacts:
- `form-output/stingray-form-data.json`
- `form-output/inspection/grand-sport-form-data-draft.json`
- `form-app/data.js`
- `form-app/app.js`

Tests:
- `tests/stingray-form-regression.test.mjs`
- `tests/grand-sport-draft-data.test.mjs`

### Risk level

Medium.

This touches live customer-facing generated data for Stingray and Grand Sport. The intended behavior is preservation, but defaults, auto-adds, exclusive-group peers, price overrides, and compatibility rules all affect build summaries and dealer submission payload contents.

### Behavior/data/doc classification

Mixed:
- Workbook/data source changes: yes.
- Generated artifacts: yes, after regeneration.
- Runtime behavior: should be unchanged; only generic runtime changes allowed if tests expose a data-driven issue.
- Tests: yes.
- Docs: no required product docs unless implementation discovers stale claims.

---

## Desired target behavior

### User interaction must remain

Stingray and Grand Sport should both behave as follows:

Coupe:
- `BC7` Black LS6 Engine Cover is selected by default.
- `BC7`, `BCP`, `BCS`, and `BC4` behave as radio peers inside the multi-select Engine Appearance section.
- Selecting `BCP`, `BCS`, or `BC4` removes `BC7`.
- Selecting `BC7` again removes the paid cover peer.
- `B6P` remains coupe-only.
- When `B6P` is selected, paid covers price at $595.
- Paid covers include `D3V` at no additional charge where `D3V` is available.

Convertible:
- Engine Appearance is not an open required section.
- `ZZ3` remains convertible-only.
- Selecting `ZZ3` auto-adds/provides `BC7` and `SL9`.
- User may replace the ZZ3-provided `BC7` with `BCP`, `BCS`, or `BC4`.
- Paid covers require `ZZ3` on convertible.
- Under `ZZ3`, paid covers price at $595.
- `D3V` remains unavailable on convertible unless separately approved by source data.

### Structural target

1. Stingray should match Grand Sport's superior default structure:
   - `BC7` coupe default should be authored through workbook choice metadata (`display_behavior=default_selected`) instead of relying on generated `default_bc7`.
   - Prefer the same source mechanism as Grand Sport variant overrides if supported for Stingray, or add an equivalent workbook-authored Stingray metadata path without runtime hardcoding.

2. Grand Sport should remove inactive legacy engine-cover source rows:
   - Remove or deactivate-through-migration-cleanup the inactive duplicate rows only after all references are migrated off them.
   - Active Grand Sport paid covers should remain `_002` rows unless the implementation spec explicitly chooses to rename/consolidate IDs. Do not rename active IDs in this pass unless necessary; ID renames increase risk to tests, generated artifacts, and app data diffs.

3. Grand Sport should adopt Stingray's explicit D3V scoping:
   - Paid-cover `includes D3V` rules should be scoped to coupe if `D3V` remains coupe-only.
   - `D3V` price override rules caused by paid covers should be scoped consistently with the include behavior.

---

## Exact files, sheets, and artifacts to change

### Workbook source: `stingray_master.xlsx`

Inspect and potentially modify these source sheets only:

Stingray sheets:
- `stingray_options`
  - Inspect `opt_bc7_001` and whether `display_behavior` can hold `default_selected` directly.
- `rule_mapping`
  - Inspect whether any manual/generated `BC7` default rows are sourced here or only in generator code.
- If no Stingray variant override source sheet exists, inspect current generator support before adding one. Possible target names must be chosen based on existing generator patterns, not invented blindly.

Grand Sport sheets:
- `grandSport_options`
  - Cleanup inactive duplicate paid-cover rows:
    - `opt_bcp_001`
    - `opt_bcs_001`
    - `opt_bc4_001`
  - Preserve active rows:
    - `opt_bcp_002`
    - `opt_bcs_002`
    - `opt_bc4_002`
    - `opt_bc7_001`
    - `opt_b6p_001`
    - `opt_zz3_001`
    - `opt_d3v_001`
    - `opt_sl9_001`
- `grandSport_rule_mapping`
  - Remove/update rows whose `source_id` points at inactive legacy rows.
  - Scope active paid-cover `includes D3V` rules to `body_style_scope=coupe` where applicable.
  - Preserve convertible `requires ZZ3` rules for active paid covers.
- `grandSport_price_rules`
  - Scope paid-cover -> D3V $0 price overrides to coupe if `D3V` remains coupe-only.
  - Preserve B6P/ZZ3 -> paid-cover $595 overrides.
- `grandSport_exclusive_members`
  - Verify only active paid-cover IDs are present.
  - Remove inactive-member rows if they still exist as inactive cleanup noise:
    - `opt_bcp_001`
    - `opt_bcs_001`
    - `opt_bc4_001`
- `grandSport_variant_overrides`
  - Preserve existing BC7 coupe default rows.

Generated workbook sheets, regenerated only:
- `form_steps`
- `form_context_choices`
- `form_choices`
- `form_standard_equipment`
- `form_rule_groups`
- `form_exclusive_groups`
- `form_rules`
- `form_price_rules`
- `form_interiors`
- `form_color_overrides`
- `form_validation`

### Generator code to inspect, and modify only if necessary

- `scripts/generate_stingray_form.py`
  - Locate current source of `default_bc7` in `defaultSelectionRules`.
  - Remove/retire the generated `default_bc7` only after Stingray workbook-authored `default_selected` emits correctly and tests pass.
  - Do not add RPO-specific replacement logic.

- `scripts/generate_grand_sport_form.py`
  - Verify cleanup of legacy rows does not break audit/parser expectations.
  - Verify active `_002` option IDs remain emitted.

- `scripts/corvette_form_generator/model_configs.py`
  - Inspect whether Stingray supports a variant override source equivalent to Grand Sport.
  - Modify only if needed to make Stingray consume workbook-authored default metadata generically.

- `scripts/corvette_form_generator/*`
  - Only modify shared helpers if a generic metadata loader/validator already exists and needs extension for Stingray.
  - Avoid hardcoded `BC7`, `BCP`, `BCS`, `BC4`, `B6P`, `ZZ3`, or `D3V` branches.

### Generated artifacts to regenerate and review

- `stingray_master.xlsx` generated `form_*` sheets
- `form-output/stingray-form-data.json`
- `form-output/stingray-form-data.csv`
- `form-output/inspection/grand-sport-inspection.json`
- `form-output/inspection/grand-sport-inspection.md`
- `form-output/inspection/grand-sport-contract-preview.json`
- `form-output/inspection/grand-sport-contract-preview.md`
- `form-output/inspection/grand-sport-form-data-draft.json`
- `form-output/inspection/grand-sport-form-data-draft.md`
- `form-app/data.js`

### Tests to update/add

Stingray:
- `tests/stingray-form-regression.test.mjs`
  - Replace or revise the test named `coupe defaults include BC7 engine appearance from generated default rules`.
  - New expectation: coupe `opt_bc7_001` choices should have `display_behavior=default_selected` from workbook-authored metadata.
  - New expectation: `defaultSelectionRules` should no longer contain `default_bc7` after migration.
  - Preserve runtime assertions that coupe defaults select BC7.
  - Preserve radio-peer tests for BC7 <-> BCP/BCS/BC4.
  - Preserve ZZ3 auto-add + paid-cover replacement tests.

Grand Sport:
- `tests/grand-sport-draft-data.test.mjs`
  - Assert inactive legacy paid-cover rows are not emitted into active draft data, rule mappings, or exclusive group members.
  - Assert `gs_excl_ls6_engine_covers` contains only active IDs:
    - `opt_bc7_001`
    - `opt_bc4_002`
    - `opt_bcp_002`
    - `opt_bcs_002`
  - Assert active paid-cover `includes D3V` rules have `body_style_scope=coupe` if the rule is emitted.
  - Assert active paid-cover -> D3V price overrides have `body_style_scope=coupe` if the price rule is emitted.
  - Preserve existing assertions for BC7 coupe `default_selected`.

Multi-model runtime:
- `tests/multi-model-runtime-switching.test.mjs`
  - Add/update a generic runtime assertion only if current coverage does not already prove both models can switch engine covers without stale peer/default state.

---

## Implementation tasks

### Task 1: Add/adjust tests first

Objective: define the target contract before touching workbook data.

Steps:
1. Update Stingray regression tests so BC7 coupe default is expected from `display_behavior=default_selected`, not `defaultSelectionRules.default_bc7`.
2. Add a negative assertion that `defaultSelectionRules` does not include `default_bc7` after migration.
3. Add/adjust Grand Sport draft tests for absence of inactive legacy engine-cover IDs in active emitted rules/groups.
4. Add/adjust Grand Sport D3V scoping tests.
5. Run targeted tests and verify expected failures before source changes:
   - `node --test tests/stingray-form-regression.test.mjs`
   - `node --test tests/grand-sport-draft-data.test.mjs`

Expected pre-change result:
- Tests fail specifically on BC7 default source, Grand Sport legacy cleanup, and D3V scoping expectations.

### Task 2: Implement Stingray workbook-authored BC7 default

Objective: make Stingray BC7 coupe default use the same superior workbook-authored choice metadata pattern as Grand Sport.

Steps:
1. Inspect generator support for Stingray variant override/default metadata.
2. If Stingray can use `display_behavior` directly on `stingray_options`, set `opt_bc7_001.display_behavior=default_selected` only if body-style scoping will not incorrectly default convertible.
3. If direct option-level metadata would incorrectly affect convertible, add/use a Stingray variant override mechanism analogous to `grandSport_variant_overrides`.
4. Add variant-scoped rows for Stingray coupe variants only:
   - `1lt_c07` / `opt_bc7_001` / `display_behavior=default_selected`
   - `2lt_c07` / `opt_bc7_001` / `display_behavior=default_selected`
   - `3lt_c07` / `opt_bc7_001` / `display_behavior=default_selected`
5. Ensure convertible variants do not get `display_behavior=default_selected` for BC7.
6. Remove/retire the generator emission of `default_bc7` from `defaultSelectionRules`.

Important constraint:
- Do not make Engine Appearance required to force BC7. The correct behavior is a soft/default selected cover on coupe and package-driven cover on convertible.

### Task 3: Clean Grand Sport legacy inactive engine-cover rows

Objective: remove or fully eliminate dependence on inactive duplicate paid-cover rows.

Steps:
1. Search workbook references to:
   - `opt_bcp_001`
   - `opt_bcs_001`
   - `opt_bc4_001`
2. For references needed by active behavior, migrate them to active IDs:
   - `opt_bcp_002`
   - `opt_bcs_002`
   - `opt_bc4_002`
3. Remove inactive legacy rows from `grandSport_options` if safe, or leave them absent from all active generated outputs if physical workbook row deletion is riskier.
4. Remove inactive member rows from `grandSport_exclusive_members` if present.
5. Remove or update inactive-source rows in `grandSport_rule_mapping`.
6. Verify no active Grand Sport generated rule, price rule, choice, or exclusive group references the inactive IDs.

Important constraint:
- Do not rename active `_002` IDs to `_001` in this pass unless all generated artifacts/tests are explicitly updated and diff risk is accepted. Retaining active IDs minimizes live-data churn.

### Task 4: Adopt Stingray-style D3V scoping in Grand Sport

Objective: make Grand Sport D3V rules explicit and self-documenting.

Steps:
1. In `grandSport_rule_mapping`, scope active paid-cover `includes D3V` rows to coupe where `D3V` is coupe-only.
2. Preserve convertible paid-cover `requires ZZ3` rows.
3. In `grandSport_price_rules`, scope paid-cover -> `D3V` $0 overrides to coupe.
4. Preserve B6P -> D3V/SL9 and ZZ3 -> SL9 price overrides with appropriate body-style scoping.
5. Regenerate Grand Sport artifacts and verify no convertible build auto-adds or prices D3V.

### Task 5: Regenerate artifacts

Commands from repo root:

```sh
.venv/bin/python scripts/generate_stingray_form.py
.venv/bin/python scripts/generate_grand_sport_form.py
```

Expected outputs:
- Updated generated `form_*` workbook sheets in `stingray_master.xlsx`
- Updated `form-output/stingray-form-data.json`
- Updated `form-output/stingray-form-data.csv`
- Updated `form-output/inspection/grand-sport-*` artifacts
- Updated `form-app/data.js`

Workbook safety:
- Close Excel first.
- Stop if `~$stingray_master.xlsx` exists unless confirmed stale.
- Use the project venv; do not run generators with bare system Python.
- After workbook write, verify saved workbook on disk using `openpyxl` or equivalent inspection.

### Task 6: Validate behavior and diffs

Run targeted gates first:

```sh
node --test tests/stingray-form-regression.test.mjs
node --test tests/grand-sport-draft-data.test.mjs
node --test tests/grand-sport-contract-preview.test.mjs
node --test tests/grand-sport-rule-audit.test.mjs
node --test tests/multi-model-runtime-switching.test.mjs
```

Then run current full suite:

```sh
node --test tests/stingray-form-regression.test.mjs
node --test tests/stingray-generator-stability.test.mjs
node --test tests/grand-sport-contract-preview.test.mjs
node --test tests/grand-sport-draft-data.test.mjs
node --test tests/grand-sport-rule-audit.test.mjs
node --test tests/multi-model-runtime-switching.test.mjs
```

Diff review checklist:
- `default_bc7` removed from Stingray `defaultSelectionRules`.
- Stingray coupe BC7 choices have `display_behavior=default_selected`.
- Stingray convertible BC7 choices do not have `display_behavior=default_selected`.
- Grand Sport emitted data no longer references inactive legacy paid-cover IDs in active rules/groups/choices.
- Grand Sport active paid covers still use `_002` IDs unless explicitly approved otherwise.
- Grand Sport paid-cover D3V rules/price overrides are coupe-scoped.
- No dealer submission endpoint/payload/Turnstile changes.
- No runtime visual/CSS changes.

---

## Constraints and boundaries

- Visual preservation: no UI/CSS/HTML changes unless a test proves generic runtime support is missing.
- No refactor: do not restructure runtime or generator architecture beyond the smallest generic metadata support needed.
- No new dependencies.
- Workbook source-of-truth: express business decisions in workbook source rows where possible.
- Generated sheets/artifacts are not hand-edited.
- Do not add RPO-specific JavaScript exceptions.
- Do not add model-specific Python exceptions unless they are temporary migration fallback and explicitly called out.
- Do not alter dealer submission endpoint, payload shape, Turnstile behavior, or deployment paths.
- Preserve live Stingray and Grand Sport customer behavior.
- Do not change active option IDs unless explicitly approved.
- Do not make Engine Appearance a required section.

---

## Risks

1. Incorrect Stingray BC7 scoping could default BC7 on convertible.
   - Mitigation: variant-scoped metadata or explicit body-style-scoped generation tests.

2. Removing Grand Sport inactive rows could break audit/parser fallback assumptions.
   - Mitigation: search references first; update tests and generator consumers before row removal.

3. D3V scoping could accidentally suppress coupe auto-add/pricing.
   - Mitigation: tests for coupe paid-cover -> D3V include and $0 price.

4. Generated `form-app/data.js` can change live app behavior.
   - Mitigation: targeted runtime tests and diff review of line-item behavior.

5. Workbook writes can corrupt or race Excel.
   - Mitigation: no Excel lock file, use `.venv`, safe workbook save path, on-disk verification after write.

---

## Non-goals

- Do not redesign Engine Appearance UI.
- Do not change section names, step placement, or visual order except as unavoidable generated-output consequences.
- Do not migrate other defaults such as FE1/NGA/J6A/QEB in this pass.
- Do not rename Grand Sport active `_002` paid-cover IDs unless separately approved.
- Do not change option prices except D3V scoping of existing $0 overrides.
- Do not alter dealer submission behavior.
- Do not clean unrelated inactive rows.

---

## Approval request

Approve this spec to proceed with implementation as a workbook-first migration pass?

If approved, implementation should begin with RED tests, then workbook/source changes, regeneration, and the full targeted validation suite above.
