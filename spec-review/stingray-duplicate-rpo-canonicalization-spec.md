# Stingray Duplicate RPO Canonicalization Spec

Spec only. Do not implement until approved.

## Goal

Collapse active duplicate RPOs in `stingray_options` so each RPO has one canonical option row, preferably the `_001` option ID, while preserving current generated/runtime behavior.

This pass should produce a workbook-backed transition from duplicate source rows to canonical source rows. Deactivation happens before deletion. Deletion happens only after generated parity proves the duplicate IDs are no longer carrying behavior.

## Canonical Rule

Prefer `_001` as canonical for every duplicate RPO.

If `_001` is currently a mirror/standard-equipment row instead of the row that carries selectable/default/price behavior, move the needed behavior onto `_001` rather than choosing a later duplicate as canonical, unless verification proves `_001` cannot safely own the behavior.

For the notes below, a non-`_001` row that currently has the right behavior is treated as the **behavior source**, not automatically the final canonical row.

## Constraints

- Workbook is source of truth.
- Do not add Stingray-only code paths.
- Do not invent new sheets if an existing Grand Sport/workbook structure already solves the same problem.
- Keep Stingray and Grand Sport source structures consistent where they express the same concept.
- Deactivate duplicates before deleting them.
- Preserve generated behavior before removing any compensating code.
- Do not remove duplicate rows until rules, statuses, price rules, groups, and standard-equipment behavior are remapped or proven unnecessary.
- Be cautious with seats/interiors: current runtime subtracts selected seat price from interior display/order price, and generated interior component metadata also carries seat price components. Seat price-rule changes must verify both option-price display and interior price subtraction.

## Current Evidence

Verified from the current `stingray_master.xlsx` workbook state.

- `rule_mapping` has no references to current duplicate option IDs.
- `price_rules` has no references to current duplicate option IDs.
- `rule_groups` and `rule_group_members` have no references to current duplicate option IDs.
- `exclusive_group_members` references `opt_efr_001`, which is the desired canonical member and should remain.
- Current duplicate behavior is therefore mostly carried by duplicate rows in `stingray_options` plus their `stingray_ovs` statuses.

Runtime/generator pricing facts to preserve:

- `form-app/app.js` `optionPrice()` supports trim-scoped self-target price overrides because it checks selected/candidate option IDs before returning `base_price`.
- `form-app/app.js` `adjustedInteriorPrice()` subtracts the selected seat's `base_price`.
- `form-app/app.js` `adjustedInteriorDisplayPrice()` subtracts `optionPrice(selectedSeat.option_id)`.
- `scripts/generate_stingray_form.py` emits interior component prices from `PriceRef` for seat components.

Implication: seat canonicalization can use option-level price rules for visible seat choices, but must also verify interior display/order totals and component lines. Do not assume a seat price-rule fix is complete until the interior tests cover it.

## Duplicate RPO Manifest

| RPO | Canonical option_id | Duplicate option_ids | Current duplicate purpose | Transfer target | Required rule/status/price changes | Deactivate phase | Delete phase | Risk |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `719` | `opt_719_001` | `opt_719_002` | standard-equipment mirror | canonical status/standard output | keep `default_selected`; verify Standard & Included still shows black seat belt | Phase 1 | Phase 2 | Medium |
| `AE4` | `opt_ae4_001` | `opt_ae4_002`, `opt_ae4_003` | trim-scoped seat price rows | canonical row + trim-scoped price rules | keep 1LT base `1095`; add 2LT `2095` and 3LT `595` price overrides; move statuses to canonical | Phase 1 or later | after parity | High |
| `AH2` | `opt_ah2_001` | `opt_ah2_002`, `opt_ah2_003` | 3LT mirror plus selectable 2LT/3LT seat rows | canonical row + trim-scoped price rules | move selectable/default behavior from `opt_ah2_002`; add 2LT `1695` and 3LT `0` pricing; move statuses to canonical | Phase 1 or later | after parity | High |
| `AQ9` | `opt_aq9_001` | `opt_aq9_002`, `opt_aq9_003`, `opt_aq9_004` | 1LT/2LT mirrors plus selectable default seat rows | canonical row + variant/trim-scoped display overrides if needed | move default/selectable behavior from `opt_aq9_003`; preserve 1LT/2LT standard/default behavior; move statuses to canonical | Phase 1 or later | after parity | High |
| `CF7` | `opt_cf7_001` | `opt_cf7_002` | coupe standard-equipment mirror | canonical status/standard output | keep coupe standard, convertible unavailable; likely add `default_selected` if current UX relies on a roof default | Phase 1 | Phase 2 | Medium |
| `CM9` | `opt_cm9_001` | `opt_cm9_002` | convertible standard-equipment mirror | canonical status/standard output | keep convertible standard, coupe unavailable; likely add `default_selected` if current UX relies on a roof default | Phase 1 | Phase 2 | Medium |
| `EFR` | `opt_efr_001` | `opt_efr_002` | standard-equipment mirror | canonical status/standard output | keep `default_selected`; keep `exclusive_groups.excl_ext_accents` member as canonical ID | Phase 1 | Phase 2 | Medium |
| `EYT` | `opt_eyt_001` | `opt_eyt_002` | standard-equipment mirror | canonical status/standard output | verify standard badge package remains visible/included | Phase 1 | Phase 2 | Medium |
| `FE1` | `opt_fe1_001` | `opt_fe1_002` | standard-equipment mirror | canonical status/standard output | likely add `default_selected`; preserve Z51 replacement behavior through rules/runtime migration later | Phase 1 | Phase 2 | Medium |
| `J6A` | `opt_j6a_001` | `opt_j6a_002` | standard-equipment mirror | canonical status/standard output | likely add `default_selected`; verify caliper default remains selected/included | Phase 1 | Phase 2 | Medium |
| `NGA` | `opt_nga_001` | `opt_nga_002` | standard-equipment mirror | canonical status/standard output | likely add `default_selected`; preserve NWI replacement behavior through rules/runtime migration later | Phase 1 | Phase 2 | Medium |
| `QEB` | `opt_qeb_001` | `opt_qeb_002` | standard-equipment mirror | canonical status/standard output | likely add `default_selected`; verify wheel default remains selected/included | Phase 1 | Phase 2 | Medium |
| `UQT` | `opt_uqt_001` | `opt_uqt_002` | trim-included mirror plus selectable 1LT option row | canonical row + variant/trim-scoped display override if needed | move 1LT selectable `1495` behavior to canonical; keep 2LT/3LT included/display-only behavior; remove hardcoded `opt_uqt_002` branch only after parity | Phase 1 or later | after parity | High |

## Row-Level Transfer Notes

### `719`

Current rows:

| option_id | Current role | Current price | Current selectable/active | Current display behavior |
| --- | --- | ---: | --- | --- |
| `opt_719_001` | canonical selectable/default row | `0` | `TRUE` / `TRUE` | `default_selected` |
| `opt_719_002` | standard-equipment mirror | blank | `FALSE` / `TRUE` | blank |

Plan:

- Keep `opt_719_001`.
- Move/verify all six variant statuses remain `standard` on `opt_719_001`.
- Deactivate `opt_719_002` first; delete after generated Standard & Included parity.
- No new price rule expected.

Validation:

- No generated artifact references `opt_719_002`.
- Black seat belt remains selected/defaulted and appears in the expected summaries.

### `AE4`

Current rows:

| option_id | Current role | Current price | Current statuses |
| --- | --- | ---: | --- |
| `opt_ae4_001` | 1LT selectable seat row | `1095` | 1LT available |
| `opt_ae4_002` | 2LT selectable seat row | `2095` | 2LT available |
| `opt_ae4_003` | 3LT selectable seat row | `595` | 3LT available |

Plan:

- Keep `opt_ae4_001` as canonical.
- Move 2LT and 3LT availability to `opt_ae4_001` in `stingray_ovs`.
- Keep canonical base price `1095` for 1LT.
- Add trim-scoped self-target price rules for canonical `opt_ae4_001`:
  - 2LT override to `2095`.
  - 3LT override to `595`.
- Deactivate `opt_ae4_002` and `opt_ae4_003` after canonical generated choices prove parity.

Open verification:

- Confirm `optionPrice(opt_ae4_001)` changes by trim while selected interior price subtraction remains correct.
- Confirm generated interior component lines still use correct AE4 seat component pricing from `PriceRef`.

### `AH2`

Current rows:

| option_id | Current role | Current price | Current statuses |
| --- | --- | ---: | --- |
| `opt_ah2_001` | 3LT equipment mirror | blank | 3LT standard |
| `opt_ah2_002` | 3LT selectable/default seat behavior source | `0` | 3LT standard |
| `opt_ah2_003` | 2LT selectable seat row | `1695` | 2LT available |

Plan:

- Prefer `opt_ah2_001` as canonical, even though current selectable/default behavior lives on `opt_ah2_002`.
- Move `opt_ah2_002` selectable/default behavior onto `opt_ah2_001` if parity supports it.
- Move 2LT availability from `opt_ah2_003` to `opt_ah2_001`.
- Set canonical row price/display behavior so 3LT remains `0` and default-selected if that is current runtime behavior.
- Add trim-scoped self-target price rule for canonical `opt_ah2_001`:
  - 2LT override to `1695`.
- Deactivate `opt_ah2_002` and `opt_ah2_003` only after canonical choice parity.

Open verification:

- If moving selectable behavior onto `opt_ah2_001` causes standard-equipment summary duplication or interior price subtraction issues, stop and document why `opt_ah2_002` must remain canonical instead. Do not patch this with runtime-specific code.

### `AQ9`

Current rows:

| option_id | Current role | Current price | Current statuses |
| --- | --- | ---: | --- |
| `opt_aq9_001` | 2LT equipment mirror | blank | 2LT standard |
| `opt_aq9_002` | 1LT equipment mirror | blank | 1LT standard |
| `opt_aq9_003` | 1LT selectable/default seat behavior source | `0` | 1LT standard |
| `opt_aq9_004` | 2LT selectable/default seat behavior source | `0` | 2LT standard |

Plan:

- Prefer `opt_aq9_001` as canonical.
- Move 1LT status and selectable/default behavior from `opt_aq9_002` / `opt_aq9_003` onto `opt_aq9_001`.
- Preserve 2LT standard/default behavior currently split across `opt_aq9_001` and `opt_aq9_004`.
- Set canonical price to `0`.
- Add `display_behavior=default_selected` to canonical if current runtime/default behavior requires it.
- Use the same model-scoped variant override pattern already used by Grand Sport if one canonical row needs different generated section/selectable/display behavior by trim.
- Deactivate `opt_aq9_002`, `opt_aq9_003`, and `opt_aq9_004` only after 1LT and 2LT parity.

Open verification:

- Confirm 1LT and 2LT both retain GT1 as the selected/default seat where expected.
- Confirm the canonical row does not show as a duplicate paid option in trim-equipment sections.

### `UQT`

Current rows:

| option_id | Current role | Current price | Current statuses |
| --- | --- | ---: | --- |
| `opt_uqt_001` | 2LT/3LT included equipment mirror | blank | 1LT available; 2LT/3LT standard |
| `opt_uqt_002` | selectable 1LT option row, suppressed by code outside 1LT | `1495` | 1LT available; 2LT/3LT standard |

Plan:

- Keep `opt_uqt_001` as canonical.
- Move 1LT selectable/chargeable behavior from `opt_uqt_002` to `opt_uqt_001`.
- Set canonical price to `1495` if that is the visible 1LT selectable option price.
- Preserve 2LT/3LT included/display-only behavior with the same variant-scoped selectability/display pattern used by Grand Sport if the base option row cannot express trim-specific selectability.
- Deactivate `opt_uqt_002` only after the hardcoded `opt_uqt_002` generator branch is no longer needed.

Validation:

- 1LT shows UQT as selectable/chargeable.
- 2LT and 3LT include UQT in standard/included equipment and do not show it as a chargeable selectable option.
- No runtime or generator code checks `opt_uqt_002`.

### Standard-Equipment Mirror Rows

These RPOs follow the same simpler mirror cleanup pattern:

- `CF7`: keep `opt_cf7_001`; deactivate/delete `opt_cf7_002`.
- `CM9`: keep `opt_cm9_001`; deactivate/delete `opt_cm9_002`.
- `EFR`: keep `opt_efr_001`; deactivate/delete `opt_efr_002`.
- `EYT`: keep `opt_eyt_001`; deactivate/delete `opt_eyt_002`.
- `FE1`: keep `opt_fe1_001`; deactivate/delete `opt_fe1_002`.
- `J6A`: keep `opt_j6a_001`; deactivate/delete `opt_j6a_002`.
- `NGA`: keep `opt_nga_001`; deactivate/delete `opt_nga_002`.
- `QEB`: keep `opt_qeb_001`; deactivate/delete `opt_qeb_002`.

For each RPO:

- Verify canonical `stingray_ovs` rows already cover the duplicate row's statuses.
- Move any needed `display_behavior=default_selected` onto the canonical row before deactivating the mirror.
- Verify the RPO still appears in Standard & Included when the selected variant expects it.
- Verify the canonical row remains in the correct exclusive/rule group if applicable.

## Proposed Price Rules For Seat Canonicalization

Use self-target price rules only after confirming `optionPrice()` and interior pricing tests cover the behavior.

Proposed rows if `_001` remains canonical:

| price_rule_id | condition_option_id | price_rule_type | target_option_id | price_value | trim_level_scope | notes |
| --- | --- | --- | --- | ---: | --- | --- |
| `pr_2lt_ae4_seat_001` | `opt_ae4_001` | `override` | `opt_ae4_001` | `2095` | `2LT` | 2LT AE4 seat price after canonicalization |
| `pr_3lt_ae4_seat_001` | `opt_ae4_001` | `override` | `opt_ae4_001` | `595` | `3LT` | 3LT AE4 seat price after canonicalization |
| `pr_2lt_ah2_seat_001` | `opt_ah2_001` | `override` | `opt_ah2_001` | `1695` | `2LT` | 2LT AH2 seat price after canonicalization |

Do not add an AQ9 price rule unless verification proves one is needed; current AQ9 rows are priced at `0`.

Do not add a UQT price rule unless the canonical base price cannot safely be set to `1495` with variant-scoped display/selectability handling.

## Implementation Phases

### Phase 0: Build Reference Manifest

Task type: audit-only / docs-only.

Risk: Low. This phase reads workbook data and code references, then updates this spec with exact evidence and decisions. It must not write `stingray_master.xlsx`, run generators that write workbook/generated artifacts, or change runtime code.

#### Phase 0 Goal

Create the exact reference manifest required to approve Phase 1 workbook edits.

Phase 0 should answer, for each duplicate RPO:

- Which `_001` row will be canonical?
- Which non-canonical rows are behavior sources?
- Which fields must move to the canonical row?
- Which `stingray_ovs` statuses must move?
- Which rule, price-rule, group, or exclusive-group references exist today?
- Which new workbook rows are proposed for Phase 1?
- Which generated/runtime behaviors must prove parity before deactivation or deletion?

#### Exact Files And Sheets To Inspect

Read-only workbook sheets:

- `stingray_options`
- `stingray_ovs`
- `rule_mapping`
- `price_rules`
- `rule_groups`
- `rule_group_members`
- `exclusive_groups`
- `exclusive_group_members`
- `section_master`
- `PriceRef`
- `lt_interiors`
- `LZ_Interiors`

Read-only code/tests:

- `scripts/generate_stingray_form.py`
- `form-app/app.js`
- `tests/stingray-form-regression.test.mjs`
- `tests/stingray-generator-stability.test.mjs`

Do not inspect generated `form_*` workbook sheets as authoritative source. They can be referenced as current generated output evidence only if Phase 0 explicitly labels them generated/read-only.

#### Phase 0 Outputs To Add To This Spec

Append a new section named `## Phase 0 Reference Manifest` with these subsections.

1. `### Workbook Snapshot`

   Include:

   - workbook package validation status;
   - timestamp/date of inspection;
   - whether `stingray_master.xlsx` was already modified in the worktree before the audit;
   - row counts for inspected source sheets;
   - duplicate RPO count and duplicate option ID count.

2. `### Duplicate RPO Reference Table`

   One row per option ID, not one row per RPO:

   | RPO | option_id | canonical? | behavior_source? | section_id | price | selectable | active | display_behavior | `1lt_c07` | `1lt_c67` | `2lt_c07` | `2lt_c67` | `3lt_c07` | `3lt_c67` | current role |
   | --- | --- | --- | --- | --- | ---: | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |

   Required conventions:

   - `canonical?` is `YES`, `NO`, or `TBD`.
   - `behavior_source?` is `YES` when a non-canonical row currently carries price/selectable/default/status behavior that must move.
   - `current role` must use concrete language such as `standard-equipment mirror`, `1LT selectable priced seat`, `2LT/3LT included equipment mirror`, or `exclusive-group canonical member`.

3. `### Reference Scan`

   Include every reference to duplicate IDs in:

   - `rule_mapping`
   - `price_rules`
   - `rule_groups`
   - `rule_group_members`
   - `exclusive_group_members`
   - `scripts/generate_stingray_form.py`
   - `form-app/app.js`
   - tests listed above

   If a surface has no references, say `none found`.

   For code/test references, include file path and symbol/test name, not just line numbers. The goal is to explain what behavior depends on duplicate IDs or duplicate RPO assumptions.

4. `### Proposed Phase 1 Workbook Changes`

   This is a proposed edit manifest, not an implementation.

   Include one subsection per duplicate RPO:

   ```text
   #### RPO

   Canonical row:
   - option_id:
   - source row fields to keep:
   - source row fields to change:

   Duplicate rows to deactivate:
   - option_id:
   - reason:

   OVS transfers:
   - variant_id: from option_id/status -> canonical option_id/status

   Price rules to add:
   - exact 9-column `price_rules` row, or `none`

   Rules/groups to change:
   - exact row IDs, or `none`

   Open decisions:
   - list anything that still blocks Phase 1
   ```

   Use `none` explicitly when no row is needed. Do not leave blanks.

5. `### Seat And Interior Pricing Verification Plan`

   Required because `AE4`, `AH2`, and `AQ9` touch seat behavior.

   Include exact current and target expectations for:

   - visible seat option price by trim;
   - selected seat `base_price`;
   - `optionPrice()` result by trim;
   - adjusted interior display price;
   - compact/plain-text order line items;
   - generated interior component prices from `PriceRef`.

   If a value cannot be proven in Phase 0 without a generated run, mark it `requires Phase 1 parity run`.

6. `### Phase 1 Approval Checklist`

   Include a checkbox list. Phase 1 is not approved until every item is checked or explicitly waived:

   - `[ ]` Canonical row chosen for every duplicate RPO.
   - `[ ]` Every behavior-source row has a transfer target.
   - `[ ]` Every proposed price rule is written with the existing 9-column `price_rules` contract.
   - `[ ]` Seat/interior pricing verification is sufficient for `AE4`, `AH2`, and `AQ9`.
   - `[ ]` `UQT` 1LT price is confirmed from workbook source.
   - `[ ]` No new sheet/column is proposed unless existing Grand Sport structure cannot represent the behavior.
   - `[ ]` Deactivate-before-delete plan is complete.
   - `[ ]` Required tests/generator checks are listed for Phase 1.

#### Phase 0 Commands

Allowed read-only commands:

```sh
.venv/bin/python scripts/validate_workbook_package.py stingray_master.xlsx
git status --short
git diff -- spec-review/stingray-duplicate-rpo-canonicalization-spec.md
git diff --check -- spec-review/stingray-duplicate-rpo-canonicalization-spec.md
```

Allowed ad hoc workbook inspection:

- Use `.venv/bin/python` with `openpyxl` in read-only/data-only mode.
- Do not call `save()`.
- Do not run `scripts/generate_stingray_form.py`.
- Do not run workbook-writing repair scripts.

#### Phase 0 Stop Conditions

Stop and ask for approval before Phase 1 if any of these are true:

- A canonical `_001` row cannot safely own behavior without a new workbook capability.
- `AE4`, `AH2`, or `AQ9` seat pricing cannot be verified with existing `price_rules` plus current interior tests.
- `UQT` requires trim-scoped selectability/display behavior and no existing shared/model-scoped structure can be reused.
- Any duplicate ID is referenced by a rule, price rule, group, exclusive group, runtime branch, or test in a way not covered by the transfer plan.
- The workbook package validator reports an issue.
- Excel lock file `~$stingray_master.xlsx` is present and not confirmed stale.

#### Phase 0 Handoff Requirements

The Phase 0 handoff must report:

- what changed in this spec;
- what did not change, especially workbook/generated/runtime state;
- workbook validation result;
- unresolved Phase 1 blockers;
- whether Phase 1 can be approved as a workbook edit pass or needs another audit.

## Phase 0 Reference Manifest

### Workbook Snapshot

Inspected on 2026-05-17. This was a read-only audit. `stingray_master.xlsx` was not saved or regenerated during Phase 0.

Pre-audit checks:

- Excel lock file: none found for `./~$stingray_master.xlsx`.
- `git status --short` before Phase 0 doc edits: clean.
- Workbook package validation: `status=valid`, `issue_count=0`.

Inspected source row counts:

| Sheet | Populated rows |
| --- | ---: |
| `stingray_options` | 270 |
| `stingray_ovs` | 1620 |
| `rule_mapping` | 235 |
| `price_rules` | 42 |
| `rule_groups` | 2 |
| `rule_group_members` | 5 |
| `exclusive_groups` | 7 |
| `exclusive_group_members` | 25 |
| `section_master` | 42 |
| `PriceRef` | 20 |
| `lt_interiors` | 132 |
| `LZ_Interiors` | 132 |

Duplicate inventory:

- Duplicate RPO count: 13.
- Duplicate option row count: 30.

### Duplicate RPO Reference Table

| RPO | option_id | canonical? | behavior_source? | section_id | price | selectable | active | display_behavior | `1lt_c07` | `1lt_c67` | `2lt_c07` | `2lt_c67` | `3lt_c07` | `3lt_c67` | current role |
| --- | --- | --- | --- | --- | ---: | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `719` | `opt_719_001` | YES | YES | `sec_seat_001` | 0 | TRUE | TRUE | `default_selected` | standard | standard | standard | standard | standard | standard | preferred canonical, selectable row, priced row, default selected |
| `719` | `opt_719_002` | NO | YES | `sec_stan_002` |  | FALSE | TRUE |  | standard | standard | standard | standard | standard | standard | standard-equipment mirror |
| `AE4` | `opt_ae4_001` | YES | YES | `sec_seat_002` | 1095 | TRUE | TRUE |  | available | available | unavailable | unavailable | unavailable | unavailable | preferred canonical, 1LT selectable priced seat |
| `AE4` | `opt_ae4_002` | NO | YES | `sec_seat_002` | 2095 | TRUE | TRUE |  | unavailable | unavailable | available | available | unavailable | unavailable | 2LT selectable priced seat |
| `AE4` | `opt_ae4_003` | NO | YES | `sec_seat_002` | 595 | TRUE | TRUE |  | unavailable | unavailable | unavailable | unavailable | available | available | 3LT selectable priced seat |
| `AH2` | `opt_ah2_001` | YES | YES | `sec_3lte_001` |  | FALSE | TRUE |  | unavailable | unavailable | unavailable | unavailable | standard | standard | preferred canonical, 3LT equipment mirror |
| `AH2` | `opt_ah2_002` | NO | YES | `sec_seat_002` | 0 | TRUE | TRUE |  | unavailable | unavailable | unavailable | unavailable | standard | standard | 3LT selectable priced seat behavior source |
| `AH2` | `opt_ah2_003` | NO | YES | `sec_seat_002` | 1695 | TRUE | TRUE |  | unavailable | unavailable | available | available | unavailable | unavailable | 2LT selectable priced seat |
| `AQ9` | `opt_aq9_001` | YES | YES | `sec_2lte_001` |  | FALSE | TRUE |  | unavailable | unavailable | standard | standard | unavailable | unavailable | preferred canonical, 2LT equipment mirror |
| `AQ9` | `opt_aq9_002` | NO | YES | `sec_1lte_001` |  | FALSE | TRUE |  | standard | standard | unavailable | unavailable | unavailable | unavailable | 1LT equipment mirror |
| `AQ9` | `opt_aq9_003` | NO | YES | `sec_seat_002` | 0 | TRUE | TRUE |  | standard | standard | unavailable | unavailable | unavailable | unavailable | 1LT selectable default seat behavior source |
| `AQ9` | `opt_aq9_004` | NO | YES | `sec_seat_002` | 0 | TRUE | TRUE |  | unavailable | unavailable | standard | standard | unavailable | unavailable | 2LT selectable default seat behavior source |
| `CF7` | `opt_cf7_001` | YES | YES | `sec_roof_001` | 0 | TRUE | TRUE |  | standard | unavailable | standard | unavailable | standard | unavailable | preferred canonical, selectable roof row |
| `CF7` | `opt_cf7_002` | NO | YES | `sec_stan_002` |  | FALSE | TRUE |  | standard | unavailable | standard | unavailable | standard | unavailable | standard-equipment mirror |
| `CM9` | `opt_cm9_001` | YES | YES | `sec_roof_001` | 0 | TRUE | TRUE |  | unavailable | standard | unavailable | standard | unavailable | standard | preferred canonical, selectable roof row |
| `CM9` | `opt_cm9_002` | NO | YES | `sec_stan_002` |  | FALSE | TRUE |  | unavailable | standard | unavailable | standard | unavailable | standard | standard-equipment mirror |
| `EFR` | `opt_efr_001` | YES | YES | `sec_exte_001` | 0 | TRUE | TRUE | `default_selected` | standard | standard | standard | standard | standard | standard | preferred canonical, exclusive-group member, default selected |
| `EFR` | `opt_efr_002` | NO | YES | `sec_stan_002` |  | FALSE | TRUE |  | standard | standard | standard | standard | standard | standard | standard-equipment mirror |
| `EYT` | `opt_eyt_001` | YES | YES | `sec_badg_001` | 0 | TRUE | TRUE |  | standard | standard | standard | standard | standard | standard | preferred canonical, selectable badge row |
| `EYT` | `opt_eyt_002` | NO | YES | `sec_stan_002` |  | FALSE | TRUE |  | standard | standard | standard | standard | standard | standard | standard-equipment mirror |
| `FE1` | `opt_fe1_001` | YES | YES | `sec_susp_001` | 0 | TRUE | TRUE |  | standard | standard | standard | standard | standard | standard | preferred canonical, visible suspension tile |
| `FE1` | `opt_fe1_002` | NO | YES | `sec_stan_002` |  | FALSE | TRUE |  | standard | standard | standard | standard | standard | standard | standard-equipment mirror |
| `J6A` | `opt_j6a_001` | YES | YES | `sec_cali_001` | 0 | TRUE | TRUE |  | standard | standard | standard | standard | standard | standard | preferred canonical, selectable caliper row |
| `J6A` | `opt_j6a_002` | NO | YES | `sec_stan_002` |  | FALSE | TRUE |  | standard | standard | standard | standard | standard | standard | standard-equipment mirror |
| `NGA` | `opt_nga_001` | YES | YES | `sec_exha_001` | 0 | TRUE | TRUE |  | standard | standard | standard | standard | standard | standard | preferred canonical, visible exhaust row |
| `NGA` | `opt_nga_002` | NO | YES | `sec_stan_002` |  | FALSE | TRUE |  | standard | standard | standard | standard | standard | standard | standard-equipment mirror |
| `QEB` | `opt_qeb_001` | YES | YES | `sec_whee_002` | 0 | TRUE | TRUE |  | standard | standard | standard | standard | standard | standard | preferred canonical, selectable wheel row |
| `QEB` | `opt_qeb_002` | NO | YES | `sec_stan_002` |  | FALSE | TRUE |  | standard | standard | standard | standard | standard | standard | standard-equipment mirror |
| `UQT` | `opt_uqt_001` | YES | YES | `sec_2lte_001` |  | FALSE | TRUE |  | available | available | standard | standard | standard | standard | preferred canonical, 2LT/3LT included equipment mirror |
| `UQT` | `opt_uqt_002` | NO | YES | `sec_inte_001` | 1495 | TRUE | TRUE |  | available | available | standard | standard | standard | standard | 1LT selectable priced row, suppressed by code outside 1LT |

### Reference Scan

Workbook source references to duplicate option IDs:

| Surface | Result |
| --- | --- |
| `rule_mapping` | none found |
| `price_rules` | none found |
| `rule_groups` | none found |
| `rule_group_members` | none found |
| `exclusive_groups` | none found |
| `exclusive_group_members` | `excl_ext_accents` references canonical `opt_efr_001`; keep this reference |

Current proposed seat price-rule IDs do not already exist in `price_rules`:

- `pr_2lt_ae4_seat_001`
- `pr_3lt_ae4_seat_001`
- `pr_2lt_ah2_seat_001`

Code and test references:

- `scripts/generate_stingray_form.py`
  - `build_form_data()` contains a hardcoded `opt_uqt_002` trim branch that suppresses the duplicate row outside 1LT.
  - `price_ref_component_prices()`, `price_ref_component_price()`, and `interior_component_metadata()` emit seat/interior component pricing from `PriceRef`; these are part of the seat canonicalization risk.
- `form-app/app.js`
  - `optionPrice()` supports self-target trim-scoped price overrides.
  - `selectedSeatChoice()`, `adjustedInteriorPrice()`, and `adjustedInteriorDisplayPrice()` subtract selected seat pricing from interior pricing.
  - `addDefaultRpo()` / reconcile logic still hardcodes defaults for `FE1`, `NGA`, and `719`; this is relevant to mirror cleanup but belongs to the later default-selection cleanup pass.
- `tests/stingray-form-regression.test.mjs`
  - `UQT is selectable only on 1LT and included-only on higher trims` protects the `UQT` behavior that must survive canonicalization.
  - `FE1 default selection prefers the visible suspension tile` and `initial selected FE1 state is de-duped to the visible suspension choice` explicitly cover `opt_fe1_001` versus `opt_fe1_002`.
  - `Stingray workbook default-selected standard choices seed every variant` currently expects `opt_efr_001` and `opt_719_001`.
  - `generated interiors expose priced component metadata from PriceRef`, `compact and plain text order output break selected interior into priced component RPO lines`, and `interior pricing subtracts the selected seat price` must cover seat canonicalization.
  - `exclusive group selection replaces ZZ3 default BC7 engine cover` references canonical `opt_efr_001` in the expected exterior accents group.
- `tests/stingray-generator-stability.test.mjs`
  - no direct duplicate option ID references found in Phase 0 scan; keep it in the Phase 1 gate because workbook source/header changes can affect generator stability.

### Proposed Phase 1 Workbook Changes

These are proposed edits only. They are not implemented by Phase 0.

#### `719`

Canonical row:

- option_id: `opt_719_001`
- source row fields to keep: `section_id=sec_seat_001`, `price=0`, `selectable=TRUE`, `active=TRUE`, `display_behavior=default_selected`
- source row fields to change: none

Duplicate rows to deactivate:

- `opt_719_002`: standard-equipment mirror; canonical statuses already cover all six variants.

OVS transfers:

- none; `opt_719_001` and `opt_719_002` are both `standard` across all six variants.

Price rules to add:

- none

Rules/groups to change:

- none

Open decisions:

- none for Phase 1, assuming generated Standard & Included parity passes after deactivation.

#### `AE4`

Canonical row:

- option_id: `opt_ae4_001`
- source row fields to keep: `section_id=sec_seat_002`, `price=1095`, `selectable=TRUE`, `active=TRUE`
- source row fields to change: none on the base row unless Phase 1 parity requires display metadata

Duplicate rows to deactivate:

- `opt_ae4_002`: 2LT priced behavior source
- `opt_ae4_003`: 3LT priced behavior source

OVS transfers:

- `2lt_c07`: `opt_ae4_002=available` -> `opt_ae4_001=available`
- `2lt_c67`: `opt_ae4_002=available` -> `opt_ae4_001=available`
- `3lt_c07`: `opt_ae4_003=available` -> `opt_ae4_001=available`
- `3lt_c67`: `opt_ae4_003=available` -> `opt_ae4_001=available`

Price rules to add:

| price_rule_id | condition_option_id | price_rule_type | target_option_id | price_value | body_style_scope | trim_level_scope | review_flag | notes |
| --- | --- | --- | --- | ---: | --- | --- | --- | --- |
| `pr_2lt_ae4_seat_001` | `opt_ae4_001` | `override` | `opt_ae4_001` | 2095 |  | `2LT` | FALSE | 2LT AE4 seat price after canonicalization |
| `pr_3lt_ae4_seat_001` | `opt_ae4_001` | `override` | `opt_ae4_001` | 595 |  | `3LT` | FALSE | 3LT AE4 seat price after canonicalization |

Rules/groups to change:

- none

Open decisions:

- Phase 1 must prove selected-seat interior subtraction uses the trim-scoped `optionPrice()` result where user-facing display/order output needs it.
- Phase 1 must verify `PriceRef` component pricing still emits AE4 seat component prices: `1LT=1095`, `2LT=2095`, `3LT=595`, `3LT R6X=1590`.

#### `AH2`

Canonical row:

- option_id: `opt_ah2_001`
- source row fields to keep: `active=TRUE`
- source row fields to change if `_001` remains canonical: `section_id=sec_seat_002`, `price=0`, `selectable=TRUE`; `display_behavior` remains open pending parity

Duplicate rows to deactivate:

- `opt_ah2_002`: 3LT selectable/zero-price behavior source
- `opt_ah2_003`: 2LT priced behavior source

OVS transfers:

- `2lt_c07`: `opt_ah2_003=available` -> `opt_ah2_001=available`
- `2lt_c67`: `opt_ah2_003=available` -> `opt_ah2_001=available`
- `3lt_c07`: already `opt_ah2_001=standard`
- `3lt_c67`: already `opt_ah2_001=standard`

Price rules to add:

| price_rule_id | condition_option_id | price_rule_type | target_option_id | price_value | body_style_scope | trim_level_scope | review_flag | notes |
| --- | --- | --- | --- | ---: | --- | --- | --- | --- |
| `pr_2lt_ah2_seat_001` | `opt_ah2_001` | `override` | `opt_ah2_001` | 1695 |  | `2LT` | FALSE | 2LT AH2 seat price after canonicalization |

Rules/groups to change:

- none

Open decisions:

- High-risk blocker before broad Phase 1: confirm changing `opt_ah2_001` from a 3LT equipment mirror to a selectable seat row does not break Standard & Included or interior filtering.
- If `_001` cannot safely own selectable behavior, split AH2 into a separate exception decision instead of silently choosing `opt_ah2_002` as canonical.
- Phase 1 must verify `PriceRef` component pricing still emits AH2 seat component prices: `2LT=1695`, `3LT R6X=995`.

#### `AQ9`

Canonical row:

- option_id: `opt_aq9_001`
- source row fields to keep: `active=TRUE`
- source row fields to change if `_001` remains canonical: `section_id=sec_seat_002`, `price=0`, `selectable=TRUE`; `display_behavior` remains open pending parity

Duplicate rows to deactivate:

- `opt_aq9_002`: 1LT equipment mirror
- `opt_aq9_003`: 1LT selectable/default behavior source
- `opt_aq9_004`: 2LT selectable/default behavior source

OVS transfers:

- `1lt_c07`: `opt_aq9_002/opt_aq9_003=standard` -> `opt_aq9_001=standard`
- `1lt_c67`: `opt_aq9_002/opt_aq9_003=standard` -> `opt_aq9_001=standard`
- `2lt_c07`: already `opt_aq9_001=standard`; preserve behavior from `opt_aq9_004`
- `2lt_c67`: already `opt_aq9_001=standard`; preserve behavior from `opt_aq9_004`

Price rules to add:

- none expected; all current selectable AQ9 behavior is priced at `0`

Rules/groups to change:

- none

Open decisions:

- High-risk blocker before broad Phase 1: confirm a single canonical AQ9 row can be both the standard equipment source and visible/default seat row for 1LT and 2LT without a Stingray variant override sheet.
- If a variant override is needed, reuse/generalize the existing Grand Sport-style model-scoped override pattern rather than adding a Stingray-only code branch.

#### `CF7`

Canonical row:

- option_id: `opt_cf7_001`
- source row fields to keep: `section_id=sec_roof_001`, `price=0`, `selectable=TRUE`, `active=TRUE`
- source row fields to change: none unless Phase 1 parity proves a workbook-authored default is needed

Duplicate rows to deactivate:

- `opt_cf7_002`: coupe standard-equipment mirror

OVS transfers:

- none; canonical and duplicate statuses match: coupe standard, convertible unavailable

Price rules to add:

- none

Rules/groups to change:

- none

Open decisions:

- Verify selected/default roof behavior after mirror deactivation; do not add `default_selected` without parity evidence.

#### `CM9`

Canonical row:

- option_id: `opt_cm9_001`
- source row fields to keep: `section_id=sec_roof_001`, `price=0`, `selectable=TRUE`, `active=TRUE`
- source row fields to change: none unless Phase 1 parity proves a workbook-authored default is needed

Duplicate rows to deactivate:

- `opt_cm9_002`: convertible standard-equipment mirror

OVS transfers:

- none; canonical and duplicate statuses match: coupe unavailable, convertible standard

Price rules to add:

- none

Rules/groups to change:

- none

Open decisions:

- Verify selected/default roof behavior after mirror deactivation; do not add `default_selected` without parity evidence.

#### `EFR`

Canonical row:

- option_id: `opt_efr_001`
- source row fields to keep: `section_id=sec_exte_001`, `price=0`, `selectable=TRUE`, `active=TRUE`, `display_behavior=default_selected`
- source row fields to change: none

Duplicate rows to deactivate:

- `opt_efr_002`: standard-equipment mirror

OVS transfers:

- none; canonical and duplicate statuses match across all six variants

Price rules to add:

- none

Rules/groups to change:

- keep `exclusive_group_members.excl_ext_accents -> opt_efr_001`

Open decisions:

- none for Phase 1, assuming generated Standard & Included parity passes after deactivation.

#### `EYT`

Canonical row:

- option_id: `opt_eyt_001`
- source row fields to keep: `section_id=sec_badg_001`, `price=0`, `selectable=TRUE`, `active=TRUE`
- source row fields to change: none unless Phase 1 parity proves a workbook-authored default is needed

Duplicate rows to deactivate:

- `opt_eyt_002`: standard-equipment mirror

OVS transfers:

- none; canonical and duplicate statuses match across all six variants

Price rules to add:

- none

Rules/groups to change:

- none

Open decisions:

- Verify Standard & Included behavior after mirror deactivation.

#### `FE1`

Canonical row:

- option_id: `opt_fe1_001`
- source row fields to keep: `section_id=sec_susp_001`, `price=0`, `selectable=TRUE`, `active=TRUE`
- source row fields to change: none in this duplicate cleanup pass

Duplicate rows to deactivate:

- `opt_fe1_002`: standard-equipment mirror

OVS transfers:

- none; canonical and duplicate statuses match across all six variants

Price rules to add:

- none

Rules/groups to change:

- none in this pass; Z51 replacement/default behavior remains a later runtime-default/rule-mapping pass

Open decisions:

- Phase 1 must update tests that currently expect `opt_fe1_002` to exist as a standard-equipment duplicate, or split FE1 mirror deactivation into its own test-update pass.

#### `J6A`

Canonical row:

- option_id: `opt_j6a_001`
- source row fields to keep: `section_id=sec_cali_001`, `price=0`, `selectable=TRUE`, `active=TRUE`
- source row fields to change: none unless Phase 1 parity proves a workbook-authored default is needed

Duplicate rows to deactivate:

- `opt_j6a_002`: standard-equipment mirror

OVS transfers:

- none; canonical and duplicate statuses match across all six variants

Price rules to add:

- none

Rules/groups to change:

- none

Open decisions:

- Verify selected/default caliper behavior after mirror deactivation.

#### `NGA`

Canonical row:

- option_id: `opt_nga_001`
- source row fields to keep: `section_id=sec_exha_001`, `price=0`, `selectable=TRUE`, `active=TRUE`
- source row fields to change: none in this duplicate cleanup pass

Duplicate rows to deactivate:

- `opt_nga_002`: standard-equipment mirror

OVS transfers:

- none; canonical and duplicate statuses match across all six variants

Price rules to add:

- none

Rules/groups to change:

- none in this pass; NWI replacement/default behavior remains a later runtime-default/rule-mapping pass

Open decisions:

- Verify Standard & Included behavior after mirror deactivation.

#### `QEB`

Canonical row:

- option_id: `opt_qeb_001`
- source row fields to keep: `section_id=sec_whee_002`, `price=0`, `selectable=TRUE`, `active=TRUE`
- source row fields to change: none unless Phase 1 parity proves a workbook-authored default is needed

Duplicate rows to deactivate:

- `opt_qeb_002`: standard-equipment mirror

OVS transfers:

- none; canonical and duplicate statuses match across all six variants

Price rules to add:

- none

Rules/groups to change:

- none

Open decisions:

- Verify selected/default wheel behavior after mirror deactivation.

#### `UQT`

Canonical row:

- option_id: `opt_uqt_001`
- source row fields to keep: `active=TRUE`
- source row fields to change if `_001` remains canonical: `section_id=sec_inte_001`, `price=1495`, `selectable=TRUE`; variant-scoped display/selectability remains required for 2LT/3LT

Duplicate rows to deactivate:

- `opt_uqt_002`: 1LT selectable priced behavior source, currently suppressed by generator code outside 1LT

OVS transfers:

- none required for status values; `opt_uqt_001` already has 1LT available and 2LT/3LT standard

Price rules to add:

- none expected if canonical base price becomes `1495`

Rules/groups to change:

- none

Open decisions:

- High-risk blocker before broad Phase 1: define or reuse a model-scoped variant override so `opt_uqt_001` is selectable/chargeable for 1LT but included/non-chargeable for 2LT/3LT.
- Do not remove the `opt_uqt_002` generator branch until canonical UQT output proves parity.

### Seat And Interior Pricing Verification Plan

Current source expectations:

| Seat RPO | Current row source | Current visible option prices | PriceRef evidence | Target after canonicalization |
| --- | --- | --- | --- | --- |
| `AE4` | `opt_ae4_001`, `opt_ae4_002`, `opt_ae4_003` | 1LT `1095`, 2LT `2095`, 3LT `595` | `1LT=1095`, `2LT=2095`, `3LT=595`, `3LT R6X=1590` | `opt_ae4_001` base `1095`; self-target price rules for 2LT/3LT |
| `AH2` | `opt_ah2_001`, `opt_ah2_002`, `opt_ah2_003` | 2LT `1695`, 3LT `0` | `2LT=1695`, `3LT R6X=995` | `opt_ah2_001` base `0`; self-target price rule for 2LT |
| `AQ9` | `opt_aq9_001`, `opt_aq9_002`, `opt_aq9_003`, `opt_aq9_004` | 1LT `0`, 2LT `0` | no priced `AQ9` `PriceRef` seat row found in Phase 0 | `opt_aq9_001` base `0`; no price rule expected |

Verification required in Phase 1 parity run:

- visible seat option price by trim matches current behavior;
- selected seat `base_price` does not break `adjustedInteriorPrice()`;
- `optionPrice()` returns the trim-scoped override where needed;
- adjusted interior display price remains correct;
- compact/plain-text order line items still show the right seat/interior component breakdown;
- generated interior component prices from `PriceRef` remain correct for `AE4` and `AH2`.

Values that require Phase 1 parity run:

- final adjusted interior display/order totals after canonical seat row replacement;
- whether `AH2` and `AQ9` `_001` rows can safely move from trim-equipment sections into `sec_seat_002`;
- whether a shared/model-scoped variant override is required for `AQ9` or `UQT`.

### Phase 1 Approval Checklist

- [x] Canonical row chosen for every duplicate RPO.
- [x] Every behavior-source row has a proposed transfer target.
- [x] Every proposed price rule is written with the existing 9-column `price_rules` contract.
- [ ] Seat/interior pricing verification is sufficient for `AE4`, `AH2`, and `AQ9`.
- [x] `UQT` 1LT price is confirmed from workbook source as `1495`.
- [ ] No new sheet/column is proposed unless existing Grand Sport structure cannot represent the behavior.
- [x] Deactivate-before-delete plan is complete.
- [x] Required tests/generator checks are listed for Phase 1.

Phase 1 recommendation:

- A narrow Phase 1A can likely target only straightforward standard-equipment mirror rows whose canonical row already has matching statuses: `719`, `CF7`, `CM9`, `EFR`, `EYT`, `FE1`, `J6A`, `NGA`, `QEB`.
- Do not include `AE4`, `AH2`, `AQ9`, or `UQT` in the first workbook mutation unless the Phase 1 spec also implements the seat/interior and variant-scoped behavior checks above.
- `FE1` has an existing regression test that expects `opt_fe1_002` to exist as a standard-equipment duplicate; include the test update in any Phase 1A FE1 edit or leave FE1 for a separate pass.

### Phase 1: Deactivate With Transfer

Workbook mutation allowed only after Phase 0 is approved.

1. Move statuses/behavior/pricing to canonical rows.
2. Add approved price rules or variant-scoped overrides.
3. Deactivate duplicate rows with `active=FALSE` or `display_behavior=hidden`, but do not delete.
4. Regenerate and compare generated output for behavior parity.
5. Keep any duplicate row active if parity cannot be proven.

### Phase 2: Delete After Parity

1. Delete duplicate option rows only after generated app data and tests prove no duplicate IDs are needed.
2. Delete duplicate OVS rows and obsolete rule/price references.
3. Remove any generator/runtime code that only compensated for duplicate IDs.

## Validation Plan

Workbook checks:

- No duplicate ID references remain in `rule_mapping`, `price_rules`, `rule_groups`, `rule_group_members`, `exclusive_groups`, or `exclusive_group_members`, except intended canonical IDs.
- Canonical rows cover all transferred `stingray_ovs` statuses.
- Duplicate rows are inactive before deletion.
- `price_rules` uses the existing 9-column contract and does not introduce a seat-specific schema.

Generated checks after approved workbook mutation:

```sh
.venv/bin/python scripts/generate_stingray_form.py
node --test tests/stingray-form-regression.test.mjs
node --test tests/stingray-generator-stability.test.mjs
```

Additional focused checks:

- No generated choice/rule/price rule/exclusive group references a deactivated duplicate option ID.
- Standard & Included summaries still show default/standard RPOs.
- Seat options show the correct price by trim.
- Interior display price and compact/plain-text order output still subtract selected seat pricing correctly.
- `UQT` remains selectable/chargeable for 1LT and included/non-chargeable for 2LT/3LT.

Shared-contract checks if variant override logic changes:

```sh
node --test tests/grand-sport-draft-data.test.mjs
node --test tests/multi-model-runtime-switching.test.mjs
```
