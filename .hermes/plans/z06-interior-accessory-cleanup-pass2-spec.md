# Z06 Interior / Accessory Cleanup Pass 2 Spec

> **For Hermes:** This is a spec-first 27vette workbook/runtime pass. Do not implement until approved. Use workbook-authored source rows wherever the workbook can represent the rule; do not add Z06/RPO-specific JavaScript or Python business-rule exceptions.

**Goal:** Clean up the remaining Z06 interior, seat, component, and accessory-package presentation issues after Pass 1 runtime-rule closure passed.

**Architecture:** The workbook remains the source of truth. Z06 interior/accessory decisions should live in `z06_options`, `z06_ovs`, `z06_variant_overrides`, `z06_rule_mapping`, `z06_price_rules`, `z06_exclusive_groups`, `z06_exclusive_members`, `LZ_Interiors`, `model_interior_scope`, `interior_components`, and `component_price_rules` where applicable. Scripts should be idempotent safe-save helpers that apply workbook rows and regenerate artifacts. Runtime JavaScript should only consume generic generated data; only make a generic runtime/rendering fix if workbook-generated data is already correct but display behavior is wrong.

**Tech Stack / Surfaces:** `stingray_master.xlsx`, Python safe-save workbook scripts under `scripts/`, Z06 generated outputs under `form-output/inspection/`, live registry in `form-app/data.js`, runtime rendering in `form-app/app.js`, Node tests under `tests/`.

---

## Pass 1 status confirmed

Pass 1 appears complete and green.

Evidence I ran from `/Users/seandm/Projects/27vette` on branch `z06-zr1-migration`:

```sh
.venv/bin/python scripts/validate_workbook_package.py
.venv/bin/python scripts/apply_z06_runtime_rule_corrections.py --include-changes
.venv/bin/python scripts/generate_z06_form.py
.venv/bin/python scripts/generate_stingray_form.py
node --test tests/z06-runtime-rule-corrections.test.mjs
node --test tests/z06-contract-preview.test.mjs tests/z06-form-data-draft.test.mjs tests/z06-runtime-promotion.test.mjs
node --test tests/multi-model-runtime-switching.test.mjs
```

Observed results:

- Workbook package validation: `status: valid`, `issue_count: 0`.
- `scripts/apply_z06_runtime_rule_corrections.py --include-changes`: dry-run `total_changes: 0`, proving the Pass 1 source rows are idempotently applied.
- `scripts/generate_z06_form.py`: generated successfully with `unresolved_issues: 0`; draft counts included `choices: 1482`, `rules: 201`, `price_rules: 36`, `interiors: 132`, `validation_warnings: 1`.
- `scripts/generate_stingray_form.py`: generated successfully with `validation_errors: 0`.
- `tests/z06-runtime-rule-corrections.test.mjs`: 7/7 passed.
- `tests/z06-contract-preview.test.mjs`, `tests/z06-form-data-draft.test.mjs`, `tests/z06-runtime-promotion.test.mjs`: 13/13 passed.
- `tests/multi-model-runtime-switching.test.mjs`: 38/38 passed.

The generator run only produced expected timestamp/workbook-save churn during verification; those are not part of this Pass 2 spec.

---

## Current evidence and diagnosis for Pass 2

Evidence inspected before writing this spec:

- `AGENTS.md` and `codex-context.md` source-of-truth / gate requirements.
- Existing Pass 1 spec: `.hermes/plans/z06-runtime-rule-correction-spec.md`.
- Current Pass 1 script/test surfaces:
  - `scripts/apply_z06_runtime_rule_corrections.py`
  - `tests/z06-runtime-rule-corrections.test.mjs`
- Generated Z06 draft data:
  - `form-output/inspection/z06-form-data-draft.json`
- Workbook sheets:
  - `z06_options`
  - `z06_ovs`
  - `z06_variant_overrides`
  - `z06_rule_mapping`
  - `z06_price_rules`
  - `z06_exclusive_groups`
  - `z06_exclusive_members`
  - `LZ_Interiors`
  - `model_interior_scope`
  - `interior_components`
  - `component_price_rules`
- Runtime rendering / pricing paths:
  - `form-app/app.js` functions `adjustedInteriorPrice`, `adjustedInteriorDisplayPrice`, `optionPrice`, `choiceDisplayPrice`, `renderInteriorCard`, `lineItemsFromInterior`, `lineItemFromInteriorComponent`.
- Grand Sport parity tests and workbook patterns:
  - `tests/grand-sport-draft-data.test.mjs`, especially the UQT trim-scoped override assertions and seat-price rule assertions.

Current findings:

1. `UQT` is currently a Z06 active/selectable option in `z06_options` at row 76, section `sec_inte_001`, price `1495`.
   - Z06 generated draft emits `UQT` as `available/selectable=True` on `1LZ`, which is correct.
   - It also emits `UQT` as `standard/selectable=True`, section `sec_inte_001`, and step `interior_trim` for `2LZ` and `3LZ`, which is not the desired included-equipment behavior.
   - Grand Sport already has the target structure in `grandSport_variant_overrides`: trim-scoped UQT rows set `selectable=False`, `display_behavior=display_only`, and move standard UQT into `sec_2lte_001` / `sec_3lte_001`.
   - Z06 currently has no `z06_variant_overrides` rows for `UQT`.

2. Z06 seat option prices are not aligned with the user-provided correction.
   - `AH2` in `z06_options` row 155 has price `1695`; generated 3LZ standard rows still carry `base_price: 1695`.
   - `AE4` in `z06_options` row 154 has price `1095`; user correction says Z06 3LZ `AE4` should be `$595`.
   - There are no current Z06 price-rule rows involving `AH2` or `AE4`.
   - Grand Sport uses trim-scoped seat price rules in generated data; Pass 2 should mirror that workbook-owned pattern instead of hardcoding seat prices in JS.

3. Z06 interior component infrastructure exists but needs cleanup/verification.
   - `LZ_Interiors` and `lt_interiors` have matching headers.
   - `model_interior_scope` has 132 active Z06 rows.
   - `interior_components` has 198 active Z06 component rows.
   - Generated Z06 interiors include component arrays, for example `1LZ_AE4_HTJ_N26` has `AE4` seat component at `1095` and `N26` suede component at `695`; `2LZ_AQ9_H1Y_38S` has stitching component `38S` at `495`.
   - The issue is not that components are entirely absent; it is that standalone option rows and runtime card display need to be brought into the same clean contract as Stingray/Grand Sport.

4. `N3W` is source non-selectable but still appears in generated choices.
   - `z06_options` row 74: `N3W`, active `True`, selectable `False`, section `sec_inte_001`.
   - `z06_ovs` makes `N3W` `standard` for 3LZ and `unavailable` otherwise.
   - Generated draft emits 6 `N3W` choices. The runtime should not show unavailable rows, and Pass 1 prevents clicking source non-selectable choices, but the user requirement is stricter: `N3W` should never show as a front-end option. The workbook should represent it as included/internal component/standard equipment rather than a customer option card.

5. `FA5` and `FA6` are not mutually exclusive today.
   - `FA5` row 70 and `FA6` row 71 are active/selectable interior trim options.
   - Current `z06_rule_mapping` has no rows involving `FA5` or `FA6`.
   - Current `z06_exclusive_members` has no group membership for `FA5` or `FA6`.

6. Accessory package include rows exist, but package component zero-price rules are missing.
   - `PCQ` includes `VWE` and `VWT`; component prices are `950` and `795`.
   - `PDY` includes `RYT` and `S08`; component prices are `60` and `150`.
   - `PEF` includes `CAV` and `RIA`; component prices are `230` and `265`.
   - Current `z06_price_rules` has no override rows zeroing those included components when the package is selected.
   - These should be modeled in workbook `z06_price_rules`, not JavaScript.

7. Runtime interior card display may need a generic display-price fix after workbook data is corrected.
   - `renderInteriorCard()` displays `formatMoney(adjustedInteriorDisplayPrice(interior))`.
   - `adjustedInteriorDisplayPrice()` subtracts the currently selected seat's `optionPrice()` from the interior row price.
   - If corrected workbook/component data still causes chargeable interior cards to display `$0` while totals include a charge, fix this as a generic interior display-price calculation covered by Stingray/Grand Sport/Z06 tests, not a Z06-specific branch.

Risk level: high. This pass affects live Z06 customer-facing interior/accessory choices, generated live app data, price totals, and selected/auto-added summaries. Use RED tests, small workbook-owned changes, safe-save script(s), regeneration, and targeted gates.

Change type: mixed workbook/data + targeted script/test + generated artifact refresh; possibly a generic runtime rendering fix if tests prove generated data is correct but card display is wrong.

---

## Pass 2 requirements

1. `UQT` should be selectable only for `1LZ`.
2. `UQT` should be included/display-only standard equipment for `2LZ` and `3LZ`, not shown as an extra standalone selectable Interior Trim option.
3. Stitching, two-tone, suede steering wheel, and similar interior component rows should not show as independent front-end options unless they are legitimate selected add-ons.
4. Interior selections should include their component effects in selected options / add-ons / auto-added output like Stingray and Grand Sport.
5. Correct Z06 3LZ seat pricing in workbook/generated/runtime behavior:
   - `AH2` should be `$0` for 3LZ standard GT2 seats.
   - `AE4` should be `$595` for 3LZ Competition Sport seats.
   - Preserve correct lower-trim pricing unless evidence shows those rows are also wrong.
6. Interior/card rendering should show actual charges on selectable cards for suede 3LZ and other chargeable component interiors; cards must not display `$0` while totals correctly include a charge.
7. `N3W` should never show as a front-end option.
8. `FA5` and `FA6` should be mutually exclusive.
9. Accessory packages should auto-add included components and zero out included component prices.
10. Package component zeroing belongs in `z06_price_rules` / generated price rules, not JavaScript.
11. Section presentation should stay consistent with Stingray/Grand Sport unless a Z06-specific workbook row explicitly says otherwise.

---

## Exact files / sheets / artifacts to inspect and likely change

### Workbook source sheets

- `stingray_master.xlsx`
  - `z06_options`
  - `z06_ovs`
  - `z06_variant_overrides`
  - `z06_rule_mapping`
  - `z06_price_rules`
  - `z06_exclusive_groups`
  - `z06_exclusive_members`
  - `LZ_Interiors`
  - `model_interior_scope`
  - `interior_components`
  - `component_price_rules`
  - `section_master` only if a section placement/standard-equipment issue cannot be represented through variant overrides.

### Scripts

- Create or modify after approval:
  - `scripts/apply_z06_interior_accessory_cleanup.py`
- Inspect but do not expand destructively:
  - `scripts/apply_z06_runtime_rule_corrections.py`
  - `scripts/corvette_form_generator/runtime_metadata.py`
  - Z06 generator paths reached from `scripts/generate_z06_form.py`
  - production app-data path reached from `scripts/generate_stingray_form.py`

### Runtime code

Modify only if a generic rendering/calculation defect remains after workbook/generated data is correct:

- `form-app/app.js`
  - `adjustedInteriorPrice`
  - `adjustedInteriorDisplayPrice`
  - `choiceDisplayPrice`
  - `renderInteriorCard`
  - `lineItemsFromInterior`
  - `lineItemFromInteriorComponent`

### Tests

Add or extend:

- `tests/z06-interior-accessory-cleanup.test.mjs`
- `tests/z06-form-data-draft.test.mjs`
- `tests/z06-runtime-promotion.test.mjs`
- `tests/multi-model-runtime-switching.test.mjs`

Use Grand Sport tests as parity examples:

- `tests/grand-sport-draft-data.test.mjs`

### Generated artifacts after approved implementation

Treat as outputs, not hand-edits:

- `form-output/inspection/z06-contract-preview.json`
- `form-output/inspection/z06-contract-preview.md`
- `form-output/inspection/z06-form-data-draft.json`
- `form-output/inspection/z06-form-data-draft.md`
- `form-output/inspection/z06-inspection.json`
- `form-output/inspection/z06-inspection.md`
- `form-output/stingray-form-data.json`
- `form-app/data.js`
- generated `form_*` workbook sheets if the production generator writes them.

---

## Pass 2 implementation plan

### Task 1: Add RED Z06 interior/accessory tests

**Objective:** Lock the current user-visible failures before changing workbook rows.

**Files:**
- Create: `tests/z06-interior-accessory-cleanup.test.mjs`
- Possibly extend: `tests/z06-form-data-draft.test.mjs`

**Test assertions:**

1. In generated Z06 data, `UQT` is:
   - `available`, `selectable=True`, section `sec_inte_001` for `1lz_h07` and `1lz_h67`.
   - `standard`, `selectable=False`, `display_behavior=display_only`, standard-equipment section `sec_2lte_001` for `2lz_h07` and `2lz_h67`.
   - `standard`, `selectable=False`, `display_behavior=display_only`, standard-equipment section `sec_3lte_001` for `3lz_h07` and `3lz_h67`.
2. Runtime active Z06 choices do not show `UQT` as a selectable Interior Trim card on `2LZ`/`3LZ`.
3. `AH2` prices at `$0` for Z06 `3LZ`; `AE4` prices at `$595` for Z06 `3LZ`.
4. `N3W` is not an active front-end choice in any Z06 body/trim combination.
5. Selecting `FA5` blocks/replaces `FA6`, and selecting `FA6` blocks/replaces `FA5` according to the existing generic exclusive-group behavior.
6. Selecting `PCQ` auto-adds `VWE`/`VWT` and each included component prices at `$0`.
7. Selecting `PDY` auto-adds `RYT`/`S08` and each included component prices at `$0`.
8. Selecting `PEF` auto-adds `CAV`/`RIA` and each included component prices at `$0`.
9. A representative chargeable Z06 interior card displays its actual incremental charge, and selecting it produces matching selected/interior component line items.
10. Stingray and Grand Sport interior/accessory tests remain unchanged/passing.

**Expected before fix:** UQT standard trim selectability/section assertions, 3LZ seat pricing, FA5/FA6 exclusivity, accessory included-component zeroing, and possibly chargeable interior display assertions should fail.

### Task 2: Add a safe-save script for workbook-owned cleanup rows

**Objective:** Apply all approved workbook source edits idempotently without touching unrelated Z rows.

**Files:**
- Create: `scripts/apply_z06_interior_accessory_cleanup.py`

**Script requirements:**

1. Dry-run by default; require `--write` for workbook writes.
2. Refuse to write if `~$stingray_master.xlsx` exists.
3. Use `save_workbook_safely()` and verify saved workbook rows on disk.
4. Join by stable `option_id` / RPO, not workbook row numbers.
5. Do not call `apply_future_model_option_review.py`.
6. Report JSON summary with `total_changes`, `changes_by_sheet`, and verification facts.
7. Preserve existing prices/metadata unless this spec explicitly changes them.

### Task 3: Add Z06 UQT variant overrides

**Objective:** Match the proven Grand Sport UQT structure for Z06 LZ trims.

**Workbook ownership:**
- `z06_variant_overrides`
- possibly `z06_ovs` only if status rows are wrong; current statuses already look correct.

**Desired rows:**

- Keep `1lz_h07` and `1lz_h67` as selectable `UQT` options in `sec_inte_001`.
- Add active `z06_variant_overrides` rows for `opt_uqt_001`:
  - `2lz_h07`: `selectable=False`, `display_behavior=display_only`, `section_id=sec_2lte_001`.
  - `2lz_h67`: `selectable=False`, `display_behavior=display_only`, `section_id=sec_2lte_001`.
  - `3lz_h07`: `selectable=False`, `display_behavior=display_only`, `section_id=sec_3lte_001`.
  - `3lz_h67`: `selectable=False`, `display_behavior=display_only`, `section_id=sec_3lte_001`.

**Acceptance:** Generated data mirrors Grand Sport's UQT standard-equipment contract while retaining Z06 IDs/variants.

### Task 4: Correct Z06 3LZ seat pricing using workbook price rules

**Objective:** Fix `AH2` and `AE4` 3LZ prices without damaging lower-trim pricing.

**Workbook ownership:**
- `z06_price_rules`
- `z06_options` only if direct base prices are proven globally wrong.

**Desired behavior:**

1. `AH2` remains available/priced for trims where it is an upgrade, but prices at `$0` where it is 3LZ standard equipment.
2. `AE4` prices at `$595` on 3LZ.
3. Preserve current 1LZ/2LZ pricing unless additional source evidence says otherwise.
4. Use Grand Sport trim-scoped seat price-rule pattern as the implementation model.

**Acceptance:** Generated `priceRules` include numeric trim/variant-scoped rules, runtime `optionPrice()` returns the corrected values, and standard-equipment sections do not emit priced selectable standard rows.

### Task 5: Remove standalone/interior-component leakage from customer choices

**Objective:** Ensure component RPOs are represented as interior components or standard/included equipment, not stray customer option cards.

**Workbook ownership:**
- `z06_options`
- `z06_ovs`
- `model_interior_scope`
- `interior_components`
- possibly `z06_variant_overrides`

**Target RPOs / concepts:**

- `N3W` should never show as a front-end option.
- Stitching RPOs, two-tone RPOs, suede steering wheel/microfiber RPOs, and similar component rows should be represented through `interior_components` where they are effects of an interior choice.
- Do not remove component identity from selected/export output; move it to the correct generated component/add-on surface.

**Acceptance:** Active runtime choices no longer expose component-only RPOs as standalone cards, while selected interiors still produce the needed component RPOs in selected/add-on/export output.

### Task 6: Add FA5 / FA6 mutual exclusivity

**Objective:** Make the two carbon-fiber interior trim options mutually exclusive through workbook metadata.

**Workbook ownership:**
- `z06_exclusive_groups`
- `z06_exclusive_members`
- possibly `z06_rule_mapping` only if current generic runtime requires explicit excludes.

**Desired behavior:**

1. Add a Z06 exclusive group for `FA5` and `FA6`, active, single-within-group.
2. Preserve existing trim availability:
   - `FA5` remains available on 2LZ/3LZ where currently available.
   - `FA6` remains available on 3LZ where currently available.
3. Do not make Interior Trim globally required.

**Acceptance:** Selecting one blocks/replaces the other generically without Z06-specific JavaScript.

### Task 7: Add accessory package component zero-price rules

**Objective:** Prevent included LPO/accessory package components from double-charging.

**Workbook ownership:**
- `z06_rule_mapping` for includes, if missing.
- `z06_price_rules` for zero-price overrides.

**Current include rows to preserve and price-zero:**

- `PCQ` includes `VWE` and `VWT`; add zero price overrides for `VWE` and `VWT` when `PCQ` is selected.
- `PDY` includes `RYT` and `S08`; add zero price overrides for `RYT` and `S08` when `PDY` is selected.
- `PEF` includes `CAV` and `RIA`; add zero price overrides for `CAV` and `RIA` when `PEF` is selected.

**Additional inspection:**

- Inspect `PDA`, `PCZ`, and any other package rows with `includes` language before deciding whether they have missing include rows. Do not infer component rows solely from prose if the target RPO is not present/approved in `z06_options`.

**Acceptance:** Selecting each package auto-adds included components and included components price at `$0`; standalone component choices retain their direct prices when not included by the package.

### Task 8: Fix generic interior display price only if workbook data still proves a runtime defect

**Objective:** Ensure chargeable interior cards display the same incremental charge that line items/totals apply.

**Runtime boundary:** Prefer workbook/data fixes first. Modify `form-app/app.js` only if tests prove generated interior/component data is correct but `renderInteriorCard()`/`adjustedInteriorDisplayPrice()` displays the wrong value.

**Likely functions if needed:**
- `adjustedInteriorDisplayPrice(interior)`
- `lineItemsFromInterior(interior, autoAdded)`
- `interiorComponentPrice(component)`
- `renderInteriorCard(interior)`

**Acceptance:** Representative chargeable Z06 3LZ/component interior cards show a non-zero actual charge when appropriate, totals remain correct, and existing Stingray/Grand Sport interior display tests remain green.

### Task 9: Regenerate and verify Pass 2

**Objective:** Prove workbook rows drive the corrected generated/live runtime behavior.

**Commands after implementation:**

```sh
cd /Users/seandm/Projects/27vette
.venv/bin/python scripts/validate_workbook_package.py
.venv/bin/python scripts/apply_z06_interior_accessory_cleanup.py --include-changes
.venv/bin/python scripts/apply_z06_interior_accessory_cleanup.py --write --include-changes
.venv/bin/python scripts/validate_workbook_package.py
.venv/bin/python scripts/generate_z06_form.py
.venv/bin/python scripts/generate_stingray_form.py
node --test tests/z06-interior-accessory-cleanup.test.mjs
node --test tests/z06-runtime-rule-corrections.test.mjs
node --test tests/z06-contract-preview.test.mjs tests/z06-form-data-draft.test.mjs tests/z06-runtime-promotion.test.mjs
node --test tests/multi-model-runtime-switching.test.mjs
```

If `form-app/app.js` changes, also run the broader runtime/stability gates currently expected by `AGENTS.md` for runtime changes.

---

## Pass 2 acceptance criteria

Pass 2 is complete only when all of these are true:

1. Workbook validates with zero package issues.
2. Pass 2 safe-save script is idempotent: after `--write`, a dry-run reports `total_changes: 0`.
3. `UQT` remains selectable on Z06 1LZ and becomes display-only standard equipment on Z06 2LZ/3LZ.
4. `UQT` is not shown as a standalone selectable Interior Trim option on 2LZ/3LZ.
5. `AH2` is `$0` for Z06 3LZ standard GT2 seats.
6. `AE4` is `$595` for Z06 3LZ Competition Sport seats.
7. `N3W` never appears as an active front-end option.
8. Component-only stitching/two-tone/suede rows do not leak as independent customer option cards unless they are legitimate selected add-ons.
9. Interior selections still produce the correct component RPOs in selected/add-on/export output.
10. Chargeable interior cards display their actual incremental price; card display and total calculation agree.
11. `FA5` and `FA6` are mutually exclusive through workbook-generated metadata.
12. `PCQ`, `PDY`, and `PEF` auto-add included components and zero the included component prices.
13. Any additional accessory-package component rows discovered during inspection are either corrected or explicitly deferred with reason.
14. Generated artifacts are regenerated, not hand-edited.
15. No dealer submission endpoint/payload/Turnstile behavior changes.
16. No ZR1/ZR1X runtime behavior changes.
17. No hardcoded Z06/RPO-specific JavaScript or Python business-rule exceptions are added.
18. Existing Pass 1 Z06 rule-correction tests remain green.
19. Multi-model runtime tests remain green for Stingray and Grand Sport.

---

## Constraints repeated back

- Workbook is source of truth for Z06 business rules.
- Prefer workbook rows over Python/JavaScript product exceptions.
- Do not hand-edit generated `form_*` sheets, `form-output/`, or `form-app/data.js`; regenerate them.
- Do not use row numbers as identities for workbook joins; use stable `option_id` and verify RPO.
- Do not call or revive destructive whole-sheet future-model review writers.
- Do not overwrite restored Z06/ZR1/ZR1X prices or metadata outside this approved Z06 pass.
- Do not change dealer submission endpoint, payload shape, Turnstile behavior, or visual design.
- Do not expand to ZR1/ZR1X in Pass 2.
- Do not refactor runtime architecture.
- Do not add dependencies.
- Stop before workbook writes if Excel lock file `~$stingray_master.xlsx` exists.
- Workbook-writing scripts must save through `save_workbook_safely()` and reopen/verify on disk.

---

## Risks and non-goals

### Risks

- Z06 generated data already has active interior component infrastructure, so the main risk is double-counting or hiding component identity while trying to remove standalone option-card leakage.
- Seat-pricing changes must be trim/variant scoped; changing direct `z06_options.price` blindly could break 1LZ/2LZ pricing.
- Runtime card price display may need a generic fix that can affect Stingray/Grand Sport; cover with multi-model tests if touched.
- Accessory package prose may mention components that are not currently modeled as approved active option rows. Do not invent missing target RPOs without source evidence.
- Generated validation can create timestamp-only diffs and workbook binary save churn; review diffs after generation.

### Non-goals for Pass 2

- Do not redo Pass 1 Z07/package/brake/wheel/runtime-rule closure.
- Do not promote or modify ZR1/ZR1X runtime behavior.
- Do not redesign the full interior UX beyond the needed Z06 component/price/card cleanup.
- Do not add image assets.
- Do not change app styling.
- Do not change dealer submission behavior.
- Do not model unresolved future package pricing for PDB/PDD/PDF beyond already-passed Pass 1 behavior.

---

## Approval question

Approval to implement Pass 2 would authorize:

- add failing Z06 interior/accessory tests,
- create `scripts/apply_z06_interior_accessory_cleanup.py`,
- make targeted safe-save workbook source-row changes for Z06 UQT variant overrides, seat pricing, component-only option visibility, FA5/FA6 exclusivity, and accessory package zero-price rules,
- make a generic interior card display-price runtime fix only if tests prove it is needed after workbook data is corrected,
- regenerate Z06/live runtime artifacts through the approved generator path,
- run workbook validation and targeted runtime gates.

It would not authorize:

- ZR1/ZR1X runtime changes,
- JavaScript hardcoded RPO exceptions,
- dealer submission changes,
- visual redesign,
- new dependencies.
