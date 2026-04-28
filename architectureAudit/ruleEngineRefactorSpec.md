# 27vette Rules Engine Refactor Spec

## Objective

Introduce a small data-driven rules layer in the existing static Stingray configurator runtime while preserving current behavior, UI, export payloads, and `window.STINGRAY_FORM_DATA`.

This is not a framework rewrite. The first pass should only migrate a few high-value hardcoded compatibility behaviors out of `form-app/app.js` and into generated data so future Corvette models do not require new RPO-specific branches in runtime code.

## Preservation Priority

- Current Stingray form behavior must be preserved exactly.
- No UI, export, pricing, line item, selected summary, auto-added summary, or step-flow behavior should change.
- The refactor is only successful if the same user actions produce the same visible results.

## Constraints

- Do not change the app architecture.
- Keep `form-app/index.html`, `form-app/styles.css`, and the static browser runtime model.
- Keep `window.STINGRAY_FORM_DATA` as the only data input.
- Preserve current Stingray behavior exactly.
- Preserve current JSON/CSV export shape.
- Do not introduce new dependencies.
- Keep changes small and reversible.
- Pilot only 2-3 migrations before expanding vocabulary.
- Do not change `currentOrder()`.
- Do not change JSON or CSV export shape.
- Do not change line item ordering.
- Do not change selected option behavior outside the three pilots.
- Do not change auto-added option behavior.
- Do not change price calculation behavior.

## Pilot Migrations

Recommended first pilots:

1. `requires_any` for `5V7` requiring one of `5ZU` or `5ZZ`.
2. `requires_any` for `5ZU` requiring one of `G8G`, `GBA`, or `GKZ`.
3. `exclusive_group` for LS6 engine covers: `BC7`, `BCP`, `BCS`, `BC4`.

Do not migrate FE1/FE2/Z51 or NGA/NWI in the first pass. Those are default-replacement behaviors with more reconciliation risk.

## Proposed Rule Data Contract Additions

Add two minimal generated data surfaces:

```js
window.STINGRAY_FORM_DATA = {
  // existing fields remain
  rules: [],
  priceRules: [],

  ruleGroups: [
    {
      group_id: "grp_5v7_spoiler_requirement",
      group_type: "requires_any",
      source_id: "opt_5v7_001",
      target_ids: ["opt_5zu_001", "opt_5zz_001"],
      disabled_reason: "Requires 5ZU Body-Color High Wing Spoiler or 5ZZ Carbon Flash High Wing Spoiler.",
      active: "True",
      body_style_scope: "",
      trim_level_scope: "",
      variant_scope: ""
    },
    {
      group_id: "grp_5zu_paint_requirement",
      group_type: "requires_any",
      source_id: "opt_5zu_001",
      target_ids: ["opt_g8g_001", "opt_gba_001", "opt_gkz_001"],
      disabled_reason: "Requires Arctic White, Black, or Torch Red exterior paint.",
      active: "True",
      body_style_scope: "",
      trim_level_scope: "",
      variant_scope: ""
    }
  ],

  exclusiveGroups: [
    {
      group_id: "grp_ls6_engine_covers",
      option_ids: ["opt_bc7_001", "opt_bcp_001", "opt_bcs_001", "opt_bc4_001"],
      selection_mode: "single_within_group",
      active: "True",
      notes: "LS6 engine cover choices are mutually exclusive within the Engine Appearance section."
    }
  ]
};
```

### Why Separate `ruleGroups` And `exclusiveGroups`

Keep this explicit and boring.

- `rules` remains the current source-target rule list.
- `ruleGroups` handles only grouped conditions that current `rules` cannot express.
- `exclusiveGroups` handles one-of behavior independent of section selection mode.

This avoids immediately reshaping the existing `rules` array and reduces rollback risk.

## New Runtime Helpers

Add helpers inside `form-app/app.js` first. Do not create a separate module in the pilot unless the helper block becomes large.

Proposed helpers:

```js
const ruleGroupsBySource = new Map();
const exclusiveGroupByOption = new Map();

function ruleGroupAppliesToCurrentVariant(group) {}

function requiresAnyReason(choice, selectedIds) {}

function optionExclusiveGroup(optionId) {}

function removeOtherExclusiveGroupOptions(optionId) {}
```

### Helper Responsibilities

`ruleGroupAppliesToCurrentVariant(group)`:
- Mirrors `ruleAppliesToCurrentVariant()` scope checks.
- Supports `body_style_scope`, `trim_level_scope`, and `variant_scope`.
- Empty scope means global.

`requiresAnyReason(choice, selectedIds)`:
- Finds active `requires_any` groups where `source_id === choice.option_id`.
- If none apply, returns empty string.
- If any target is selected or auto-added, returns empty string.
- Otherwise returns `disabled_reason`.
- Call this from `disableReasonForChoice()` with the existing `selectedContextIds()` helper.
- Do not add a new `selectedIdsWithContext()` helper unless implementation proves it is necessary.
- Avoid duplicate selection-context concepts.

`removeOtherExclusiveGroupOptions(optionId)`:
- Finds the exclusive group containing `optionId`.
- Deletes other selected IDs from that group.
- Preserves current single-click behavior for LS6 covers.

### Dependency Guard

- `computeAutoAdded()` must not call `disableReasonForChoice()`.
- `computeAutoAdded()` must not call `requiresAnyReason()` or other grouped-rule helpers.
- For this pilot, grouped requirement checks belong inside `disableReasonForChoice()` only.
- This guard avoids introducing recursive selection/auto-add dependencies while preserving current auto-added behavior.

## Existing `app.js` Logic To Move First

### Pilot 1: `5V7` Requires `5ZU` Or `5ZZ`

Current implementation:

```js
if (choice.rpo === "5V7" && !(selectedOptionByRpo("5ZU") || selectedOptionByRpo("5ZZ"))) {
  return "Requires 5ZU Body-Color High Wing Spoiler or 5ZZ Carbon Flash High Wing Spoiler.";
}
```

Proposed generated data:

```js
{
  group_id: "grp_5v7_spoiler_requirement",
  group_type: "requires_any",
  source_id: "opt_5v7_001",
  target_ids: ["opt_5zu_001", "opt_5zz_001"],
  disabled_reason: "Requires 5ZU Body-Color High Wing Spoiler or 5ZZ Carbon Flash High Wing Spoiler.",
  active: "True"
}
```

Runtime behavior:
- In `disableReasonForChoice(choice)`, evaluate `requiresAnyReason(choice, selectedContextIds())` before the current source-rule loop.
- If no target is selected, disable `5V7` with the same message.
- If either `5ZU` or `5ZZ` is selected or auto-added, allow `5V7`.

Test changes:
- Stop asserting that `app.js` contains `choice.rpo === "5V7"`.
- Assert `data.ruleGroups` contains the `requires_any` group.
- Add behavior-level test helper that confirms:
  - no target selected means disabled reason exists;
  - `5ZU` selected clears reason;
  - `5ZZ` selected clears reason.

Rollback plan:
- Remove the generated `ruleGroups` entry.
- Restore the existing hardcoded `choice.rpo === "5V7"` branch.
- Existing generated `rules` are already omitted for this case, so rollback is localized.

### Pilot 2: `5ZU` Requires `G8G`, `GBA`, Or `GKZ`

Current implementation:

```js
if (choice.rpo === "5ZU" && !(selectedOptionByRpo("G8G") || selectedOptionByRpo("GBA") || selectedOptionByRpo("GKZ"))) {
  return "Requires Arctic White, Black, or Torch Red exterior paint.";
}
```

Proposed generated data:

```js
{
  group_id: "grp_5zu_paint_requirement",
  group_type: "requires_any",
  source_id: "opt_5zu_001",
  target_ids: ["opt_g8g_001", "opt_gba_001", "opt_gkz_001"],
  disabled_reason: "Requires Arctic White, Black, or Torch Red exterior paint.",
  active: "True"
}
```

Runtime behavior:
- Same `requiresAnyReason()` path as `5V7`.
- Uses option IDs, not RPO string checks.
- Preserves the current disabled reason text.

Test changes:
- Stop asserting `app.js` contains the literal `G8G/GBA/GKZ` branch.
- Assert `data.ruleGroups` contains the target IDs.
- Add behavior tests for no paint vs each allowed paint.

Rollback plan:
- Remove the generated `ruleGroups` entry.
- Restore the hardcoded branch.
- No workbook schema rollback needed if `ruleGroups` is additive.

### Pilot 3: LS6 Engine Covers Exclusive Group

Current implementation:

```js
const LS6_ENGINE_COVER_OPTION_IDS = new Set(["opt_bc7_001", "opt_bcp_001", "opt_bcs_001", "opt_bc4_001"]);

function removeOtherLs6EngineCovers(optionId) {
  if (!LS6_ENGINE_COVER_OPTION_IDS.has(optionId)) return;
  for (const id of LS6_ENGINE_COVER_OPTION_IDS) {
    if (id !== optionId) deleteSelectedOption(id);
  }
}
```

Current call site:

```js
removeOtherLs6EngineCovers(choice.option_id);
```

Proposed generated data:

```js
{
  group_id: "grp_ls6_engine_covers",
  option_ids: ["opt_bc7_001", "opt_bcp_001", "opt_bcs_001", "opt_bc4_001"],
  selection_mode: "single_within_group",
  active: "True",
  notes: "LS6 engine cover choices are mutually exclusive within the Engine Appearance section."
}
```

Runtime behavior:
- Replace `removeOtherLs6EngineCovers(choice.option_id)` with `removeOtherExclusiveGroupOptions(choice.option_id)`.
- Runtime should not know “LS6” or any specific RPO.
- Behavior remains: selecting one cover removes the other selected covers.

Test changes:
- Stop asserting `const LS6_ENGINE_COVER_OPTION_IDS` exists.
- Assert `data.exclusiveGroups` includes the four option IDs.
- Add behavior-level unit test for selecting `BCP` after `BC7` removes `BC7`.
- Keep the existing data test that BC4/BCP/BCS are consolidated and B6P price overrides exist.

Rollback plan:
- Restore `LS6_ENGINE_COVER_OPTION_IDS`.
- Restore `removeOtherLs6EngineCovers()`.
- Leave generated `exclusiveGroups` unused until retried.

## Logic That Stays Temporarily

Keep these hardcoded in the first pass:

- Z51 replacing FE1/FE2 and auto-adding FE3.
- NWI replacing NGA.
- GBA/ZYC precedence.
- Default seeding for FE1, NGA, BC7, and 719.
- Color override auto-add behavior using `data.colorOverrides`.
- Interior price subtraction.
- `runtime_action === "replace"` handling for T0A.

Reason: these touch reconciliation, defaults, auto-added line items, pricing, or summary behavior. They should be migrated after the first pilot proves the grouped-rule helpers are stable.

Out of scope for this pilot:
- FE1/FE2/Z51 replacement behavior.
- NGA/NWI replacement behavior.
- GBA/ZYC precedence.
- D30/R6X color override and auto-add behavior.
- T0A replacement behavior.
- Default seeding.
- Color overrides.
- Interior pricing.

## Generation Script Changes

In `scripts/generate_stingray_form.py`:

1. Add `rule_groups` generation near existing `raw_rules`.
2. Keep current skips for 5V7 and 5ZU generated `requires` rows during the pilot.
3. Emit `ruleGroups` into JSON and `form-app/data.js`.
4. Optionally write a workbook sheet `form_rule_groups` for auditability.
5. Add `exclusive_groups` generation with the LS6 option IDs.
6. Emit `exclusiveGroups` into JSON and `form-app/data.js`.
7. Optionally write `form_exclusive_groups`.

Suggested workbook sheet headers:

`form_rule_groups`:

```text
group_id
group_type
source_id
target_ids
body_style_scope
trim_level_scope
variant_scope
disabled_reason
active
notes
```

`form_exclusive_groups`:

```text
group_id
option_ids
selection_mode
active
notes
```

For `target_ids` and `option_ids`, use pipe-delimited IDs in workbook sheets and arrays in JSON.

### Generated-Data Diff Expectations

After implementation, generated data changes should be limited to:
- Added `ruleGroups`.
- Added `exclusiveGroups`.
- Optional audit sheets such as `form_rule_groups` and `form_exclusive_groups`.

Existing generated surfaces should not be reshaped as part of this pilot unless absolutely necessary and explicitly justified:
- `choices`
- `rules`
- `priceRules`
- `sections`
- `interiors`
- `standardEquipment`
- `contextChoices`

## Runtime Evaluation Order

Inside `disableReasonForChoice(choice)`:

1. Existing inactive/unavailable checks.
2. Pilot `requires_any` group check.
3. Existing temporary RPO hardcoded checks that remain.
4. Existing target `excludes` checks.
5. Existing source `requires` / `excludes` checks.
6. Existing display-only fallback.

After pilots are fully migrated, remove only the specific hardcoded branches for `5V7` and `5ZU`.

Inside `handleChoice(choice)`:

1. Keep existing single-section behavior.
2. For multi-select add path, call `removeOtherExclusiveGroupOptions(choice.option_id)`.
3. Remove `removeOtherLs6EngineCovers()` only after tests pass.

## Test Updates

Update `tests/stingray-form-regression.test.mjs` in a narrow way.

Keep tests for:
- Generated data loading.
- Engine cover consolidation and B6P price overrides.
- Current UI flow hooks.
- Export shape.
- Current replacement/default behaviors that remain hardcoded.
- T0A replacement behavior.
- D30/R6X behavior.
- Interior pricing behavior.

Change tests that currently assert implementation details:
- Replace `assert.match(appSource, /choice\.rpo === "5V7"/)` with `data.ruleGroups` assertions.
- Replace `assert.match(appSource, /choice\.rpo === "5ZU"/)` with `data.ruleGroups` assertions.
- Replace `assert.match(appSource, /const LS6_ENGINE_COVER_OPTION_IDS/)` with `data.exclusiveGroups` assertions.

Add focused tests:
- `requires_any groups are exported for 5V7 and 5ZU`.
- `exclusiveGroups exports LS6 engine covers`.
- `app runtime has generic grouped-rule helpers`.
- The old hardcoded `5V7` and `5ZU` branches are removed.
- The old LS6-specific constant/function is removed.
- If feasible without browser automation, expose/evaluate helper behavior through source-level fixtures. If not feasible yet, keep data-contract tests now and add browser smoke after implementation.

Acceptance floor:
- Tests must prove grouped data is generated.
- Tests must prove `app.js` consumes grouped data through generic helpers.
- Tests must prove the old hardcoded `5V7` and `5ZU` branches are removed.
- Tests must prove the old LS6-specific constant/function is removed.
- Unrelated regression tests must still pass.
- Implementation is not accepted if tests only prove that `ruleGroups` and `exclusiveGroups` exist.

## Validation Plan

After implementation approval, run:

```sh
python3 scripts/generate_stingray_form.py
node --test tests/stingray-form-regression.test.mjs
```

Then manually smoke test:

- Select `5V7` before spoiler requirement is satisfied: disabled reason should match current behavior.
- Select `5ZU`, then `5V7`: `5V7` should become available.
- Select `5ZZ`, then `5V7`: `5V7` should become available.
- Select `5ZU` before allowed paint: disabled reason should match current behavior.
- Select G8G, GBA, or GKZ, then `5ZU`: `5ZU` should become available.
- Select BC7, then BCP/BCS/BC4: only the last selected LS6 cover should remain selected.
- Confirm export payload shape is unchanged.

## Non-Goals

- No React/Vite/build system.
- No full generic rules framework.
- No migration of all compatibility logic.
- No workbook-wide schema redesign.
- No change to UI layout, styling, labels, or export contract.
- No migration of high-risk defaults until pilot migrations are stable.

## Approval Boundary

Implementation should happen in one small approved pass:

- Add generated `ruleGroups` and `exclusiveGroups`.
- Add generic runtime helpers.
- Migrate only `5V7`, `5ZU`, and LS6 exclusivity.
- Update focused regression tests.

Anything involving Z51/FE1/FE2, NGA/NWI, GBA/ZYC, D30/R6X, or default seeding should be a separate approved spec after this pilot passes.
