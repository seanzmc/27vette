# Distribution Updates 2026-06-22 TL;DR Workbook Spec

Status: spec only / awaiting approval
Created: 2026-06-25
Repo: `/Users/seandm/Projects/27vette`
Branch observed: `main`
Workbook lock observed: none (`~$stingray_master.xlsx` absent)
Recommended reasoning level for implementation: high

## Request

Add the TL;DR distribution-update decisions from `dist_updates/dist-updates-6-22.md` into the workbook in the appropriate existing source surfaces: option source rows, OVS/status rows, direct rule mappings, price rules, default-selection rules, and existing exclusive/default metadata where needed.

User boundary: use only existing pipelines and functions. Do not create new workbook sheets, new generation paths, helper scripts, runtime code paths, or hardcoded model/RPO logic.

This spec intentionally scopes the TL;DR behavior and minimum supporting workbook notes. It does not attempt a full verbatim footnote-copy convergence pass for every seatbelt footnote sentence unless that text is needed to document the workbook-owned behavior below.

## Diagnosis

Change type: workbook/data-only, plus generated artifact refresh and targeted test expectation updates after approval. No production Python/JavaScript runtime changes should be required.

Risk level: medium.

Reasons:

- The workbook can already express the active-model seatbelt behavior through `*_rule_mapping`, `*_price_rules`, and existing seatbelt exclusive groups.
- Grand Sport CFV currently has contradictory source shape: `grandSport_options.opt_cfv_001` has OVS `available` for all six variants but the option row is `active=False` and `detail_raw='1. Not available at this time.'`.
- Z06 R8E pricing from the TL;DR is already present in current workbook source rows and tests; implementation should verify/preserve it, not rewrite it unnecessarily.
- ZR1/ZR1X are inactive future scaffolds. Their option/OVS/price/default surfaces exist, but there is no `zr1_rule_mapping` or `zr1x_rule_mapping` sheet in the workbook. Therefore the R8E and PCQ/VWT TL;DR rows can be represented now through existing sheets, but full ZR1/ZR1X interior-driven 3N9 auto-include behavior cannot be implemented in this no-new-sheet/no-code pass.

## Evidence inspected

### Files

- `AGENTS.md`
  - Non-trivial workbook/runtime changes require spec-first approval.
  - Workbook owns product/business rules.
  - Do not add sheets, paths, or code when existing workbook source surfaces can represent the rule.
- `dist_updates/dist-updates-6-22.md`
  - Stingray TL;DR: `3N9 standard with EJH, EPX`.
  - Grand Sport TL;DR: `3N9 standard with EJH, EPX`; `CFV available to order`.
  - Z06 TL;DR: `3N9 standard with EJH, EPX`; `R8E without T0F/T0G = $2,600`; `R8E with T0F/T0G = $3,000`.
  - ZR1/ZR1X TL;DR: `3N9 standard with EJH, EPX`; `PCQ, VWT not available at this time`; `ZR1 R8E = $3,000`; `ZR1X R8E = $2,600`.
- `scripts/apply_workbook_ops.py`
  - Existing CLI path for workbook-editor operation batches; defaults to dry-run and writes only with `--write`.
  - Uses `corvette_form_generator.editor_ops.apply_batch`, which saves through the existing workbook safety path.
- `scripts/corvette_form_generator/production.py`
  - Reads active option rows, OVS status rows, price rules, exclusive groups, and default-selection rules through current model config.
  - Skips option rows where `active != 'True'`.
  - Emits active rows with `status='unavailable'` when OVS marks the current variant unavailable.
- `scripts/corvette_form_generator/runtime_metadata.py`
  - Loads `default_selection_rules` by `model_key`.
  - Derives default-selected display behavior from existing default-selection rules and exclusive groups.

### Current workbook source state

Read-only `openpyxl` inspection of `stingray_master.xlsx` found:

Active model sheets and relevant counts:

- `stingray_options`, `stingray_ovs`, `rule_mapping`, `price_rules`, `exclusive_groups`, `exclusive_group_members` exist.
- `grandSport_options`, `grandSport_ovs`, `grandSport_rule_mapping`, `grandSport_price_rules`, `grandSport_exclusive_groups`, `grandSport_exclusive_members` exist.
- `z06_options`, `z06_ovs`, `z06_rule_mapping`, `z06_price_rules`, `z06_exclusive_groups`, `z06_exclusive_members` exist.
- `zr1_options`, `zr1_ovs`, `zr1_price_rules`, `zr1_rule_groups`, `zr1_rule_group_members`, `zr1_exclusive_groups`, `zr1_exclusive_members`, `zr1_variant_overrides` exist.
- `zr1_rule_mapping` does not exist.
- `zr1x_options`, `zr1x_ovs`, `zr1x_price_rules`, `zr1x_rule_groups`, `zr1x_rule_group_members`, `zr1x_exclusive_groups`, `zr1x_exclusive_members`, `zr1x_variant_overrides` exist.
- `zr1x_rule_mapping` does not exist.

Active Very Dark Atmosphere interiors currently have no 3N9 include/zero-price rows:

- Stingray active `model_interior_scope` VDA interiors with no matching include/price rows:
  - `3LT_AE4_EJH`
  - `3LT_AE4_EPX_N26`
  - `3LT_AH2_EJH`
  - `3LT_AH2_EPX_N26`
- Grand Sport active `model_interior_scope` VDA interiors with no matching include/price rows:
  - `3LT_AE4_EJH`
  - `3LT_AE4_EPX_N26`
  - `3LT_AH2_EJH`
  - `3LT_AH2_EPX_N26`
- Z06 active `model_interior_scope` VDA interiors with no matching include/price rows:
  - `3LZ_AH2_EJH`
  - `3LZ_AE4_EJH`
  - `3LZ_AH2_EPX_N2Z`
  - `3LZ_AE4_EPX_N2Z`
- ZR1/ZR1X active future-scope VDA interiors exist in `model_interior_scope`, but the models are inactive and do not have direct rule-mapping sheets.

Seatbelt exclusive groups are already present for promoted active models:

- Stingray: `excl_seat_belts` contains `opt_719_001`, `opt_3n9_001`, `opt_379_001`, `opt_3a9_001`, `opt_3f9_001`, `opt_3m9_001`.
- Grand Sport: `gs_excl_seat_belts` contains the same option IDs.
- Z06: `z06_excl_seat_belts` contains the same option IDs.
- ZR1/ZR1X currently have no seatbelt exclusive-group members. Do not add new groups in this pass unless an approved future-model rule-activation pass defines that scope.

Current targeted option rows:

- `grandSport_options.opt_cfv_001`
  - RPO `CFV`
  - price `4495`
  - section `sec_perf_ground_001`
  - selectable `True`
  - active `False`
  - `detail_raw='1. Not available at this time.'`
  - `grandSport_ovs` has six `available` rows.
- `z06_options.opt_r8e_002`
  - RPO `R8E`
  - price `2600`
  - section `sec_incl_001`
  - selectable `True`
  - active `True`
  - `z06_ovs` has six `standard` rows.
- `default_selection_rules.z06_default_r8e_tax`
  - `target_option_id=opt_r8e_002`
  - `condition_type=always`
  - active `True`.
- `z06_price_rules`
  - `z06_pr_t0f_r8e_tax_3000`: `opt_t0f_001 -> opt_r8e_002 = 3000`
  - `z06_pr_t0g_r8e_tax_3000`: `opt_t0g_001 -> opt_r8e_002 = 3000`
- `zr1_options.opt_r8e_002`
  - price blank
  - section `sec_incl_001`
  - selectable `False`
  - active `True`
  - four `zr1_ovs` rows are `standard`.
- `zr1x_options.opt_r8e_002`
  - price blank
  - section `sec_incl_001`
  - selectable `False`
  - active `True`
  - four `zr1x_ovs` rows are `standard`.
- `zr1_options.opt_pcq_001` / `zr1x_options.opt_pcq_001`
  - active/selectable and OVS `available` today.
- `zr1_options.opt_vwt_001` / `zr1x_options.opt_vwt_001`
  - active/selectable and OVS `available` today.

Existing tests/gates relevant to the pass:

- `tests/stingray-form-regression.test.mjs`
  - already tests interior-included seatbelt locking for Stingray.
- `tests/multi-model-runtime-switching.test.mjs`
  - already tests Grand Sport interior-included seatbelt locking and should be extended for EJH/EPX.
- `tests/grand-sport-draft-data.test.mjs`
  - currently expects `opt_cfv_001` not to emit as an active Grand Sport option; this expectation must change when CFV becomes available.
- `tests/z06-form-data-draft.test.mjs`
  - already tests Z06 R8E price rules and Z06 interior-included seatbelt generated rows; extend its `z06InteriorSeatbeltIncludes` fixture for EJH/EPX.
- `tests/z06-runtime-rule-corrections.test.mjs`
  - already tests R8E runtime pricing and Z06 seatbelt locking; extend the seatbelt fixture for EJH/EPX, preserving current R8E expectations.
- `tests/z06-runtime-promotion.test.mjs`
  - protects no positive prices in standard sections except R8E.

## Ownership decision

### Active-model `3N9 standard with EJH, EPX`

Use existing workbook rule and price-rule surfaces:

- `rule_mapping`
- `price_rules`
- `grandSport_rule_mapping`
- `grandSport_price_rules`
- `z06_rule_mapping`
- `z06_price_rules`

For each active model, add an `includes` rule from each active Very Dark Atmosphere interior ID to `opt_3n9_001`, paired with a zero-price override from the same interior ID to `opt_3n9_001`.

The intended behavior is parity with the existing Natural / Natural Dipped interior behavior for `HZN` / `HUF`: selecting an `EJH` or `EPX` Very Dark Atmosphere interior should auto-add `3N9` Natural Seat Belt Color at `$0` and keep the other seat-belt colors unavailable while that interior remains selected.

Use only the existing interior include + zero-price override + active seat-belt exclusive-group pipeline. Do not add pairwise seat-belt excludes. Do not add runtime JavaScript. Runtime already evaluates interior-sourced includes/price rules and uses active seatbelt exclusive groups to lock peers.

Exact active-model row map:

| Model | Rule sheet | Price sheet | Interior source_id / condition_option_id | Target |
|---|---|---|---|---|
| Stingray | `rule_mapping` | `price_rules` | `3LT_AE4_EJH` | `opt_3n9_001` |
| Stingray | `rule_mapping` | `price_rules` | `3LT_AE4_EPX_N26` | `opt_3n9_001` |
| Stingray | `rule_mapping` | `price_rules` | `3LT_AH2_EJH` | `opt_3n9_001` |
| Stingray | `rule_mapping` | `price_rules` | `3LT_AH2_EPX_N26` | `opt_3n9_001` |
| Grand Sport | `grandSport_rule_mapping` | `grandSport_price_rules` | `3LT_AE4_EJH` | `opt_3n9_001` |
| Grand Sport | `grandSport_rule_mapping` | `grandSport_price_rules` | `3LT_AE4_EPX_N26` | `opt_3n9_001` |
| Grand Sport | `grandSport_rule_mapping` | `grandSport_price_rules` | `3LT_AH2_EJH` | `opt_3n9_001` |
| Grand Sport | `grandSport_rule_mapping` | `grandSport_price_rules` | `3LT_AH2_EPX_N26` | `opt_3n9_001` |
| Z06 | `z06_rule_mapping` | `z06_price_rules` | `3LZ_AH2_EJH` | `opt_3n9_001` |
| Z06 | `z06_rule_mapping` | `z06_price_rules` | `3LZ_AE4_EJH` | `opt_3n9_001` |
| Z06 | `z06_rule_mapping` | `z06_price_rules` | `3LZ_AH2_EPX_N2Z` | `opt_3n9_001` |
| Z06 | `z06_rule_mapping` | `z06_price_rules` | `3LZ_AE4_EPX_N2Z` | `opt_3n9_001` |

Rule row shape:

- `rule_type=includes`
- `target_id=opt_3n9_001`
- `body_style_scope` blank
- `runtime_action` blank
- `disabled_reason` blank
- `original_detail_raw`: use the distribution-update source sentence for the owning model, e.g. `(EJH, EPX) Very Dark Atmosphere interiors comes with (3N9) Natural seat belt color.`

Price-rule row shape:

- `price_rule_type=override`
- `target_option_id=opt_3n9_001`
- `price_value=0`
- `body_style_scope` blank or `*` only if the existing model sheet convention requires `*`; do not normalize unrelated rows.
- `trim_level_scope` blank or `*` only if the existing model sheet convention requires `*`; do not normalize unrelated rows.
- `notes`: `EJH/EPX Very Dark Atmosphere interior includes Natural seat belt color.`

Recommended deterministic IDs, unless a preflight collision requires the same pattern with a numeric suffix:

| Sheet | Row ID |
|---|---|
| `rule_mapping` | `rule_3lt_ae4_ejh_includes_opt_3n9_001` |
| `rule_mapping` | `rule_3lt_ae4_epx_n26_includes_opt_3n9_001` |
| `rule_mapping` | `rule_3lt_ah2_ejh_includes_opt_3n9_001` |
| `rule_mapping` | `rule_3lt_ah2_epx_n26_includes_opt_3n9_001` |
| `price_rules` | `pr_ae4_ejh3n9_001` |
| `price_rules` | `pr_ae4_epx_n26_3n9_001` |
| `price_rules` | `pr_ah2_ejh3n9_001` |
| `price_rules` | `pr_ah2_epx_n26_3n9_001` |
| `grandSport_rule_mapping` | `gs_rule_3lt_ae4_ejh_includes_opt_3n9_001` |
| `grandSport_rule_mapping` | `gs_rule_3lt_ae4_epx_n26_includes_opt_3n9_001` |
| `grandSport_rule_mapping` | `gs_rule_3lt_ah2_ejh_includes_opt_3n9_001` |
| `grandSport_rule_mapping` | `gs_rule_3lt_ah2_epx_n26_includes_opt_3n9_001` |
| `grandSport_price_rules` | `gs_pr_ae4_ejh3n9_001` |
| `grandSport_price_rules` | `gs_pr_ae4_epx_n26_3n9_001` |
| `grandSport_price_rules` | `gs_pr_ah2_ejh3n9_001` |
| `grandSport_price_rules` | `gs_pr_ah2_epx_n26_3n9_001` |
| `z06_rule_mapping` | `z06_rule_3lz_ah2_ejh_includes_opt_3n9_001` |
| `z06_rule_mapping` | `z06_rule_3lz_ae4_ejh_includes_opt_3n9_001` |
| `z06_rule_mapping` | `z06_rule_3lz_ah2_epx_n2z_includes_opt_3n9_001` |
| `z06_rule_mapping` | `z06_rule_3lz_ae4_epx_n2z_includes_opt_3n9_001` |
| `z06_price_rules` | `z06_pr_ah2_ejh_3n9_zero` |
| `z06_price_rules` | `z06_pr_ae4_ejh_3n9_zero` |
| `z06_price_rules` | `z06_pr_ah2_epx_n2z_3n9_zero` |
| `z06_price_rules` | `z06_pr_ae4_epx_n2z_3n9_zero` |

### Grand Sport `CFV available to order`

Use existing Grand Sport option/OVS source rows:

- `grandSport_options.opt_cfv_001`
  - set `active=True`
  - keep `selectable=True`
  - keep price `4495`
  - keep section `sec_perf_ground_001`
  - remove or rewrite `detail_raw='1. Not available at this time.'`
- `grandSport_ovs`
  - preserve the existing six `available` rows for `opt_cfv_001`.

Do not add a new sheet, runtime exception, or generator branch.

### Z06 `R8E without T0F/T0G = $2,600; with T0F/T0G = $3,000`

Current workbook source already matches the TL;DR. Implementation should verify and preserve:

- `z06_options.opt_r8e_002.price = 2600`
- all six `z06_ovs` rows for `opt_r8e_002` are `standard`
- `default_selection_rules.z06_default_r8e_tax` exists and is active
- `z06_price_rules.z06_pr_t0f_r8e_tax_3000` exists and is active shape-compatible
- `z06_price_rules.z06_pr_t0g_r8e_tax_3000` exists and is active shape-compatible

No workbook change is expected for this TL;DR item unless a pre-implementation re-probe finds drift.

### ZR1/ZR1X `R8E` prices

Use existing inactive future-model source sheets:

- `zr1_options.opt_r8e_002.price = 3000`
- `zr1x_options.opt_r8e_002.price = 2600`

Recommended addition through the existing shared default-selection sheet, because Z06 required-charge behavior uses the same path:

- add `default_selection_rules.zr1_default_r8e_tax`
  - `model_key=zr1`
  - `target_option_id=opt_r8e_002`
  - `condition_type=always`
  - `body_style_scope=*`
  - `trim_level_scope=*`
  - `variant_scope=*`
  - active `True`
  - priority before other ZR1 defaults, e.g. `205`
- add `default_selection_rules.zr1x_default_r8e_tax`
  - same shape, `model_key=zr1x`
  - priority before other ZR1X defaults, e.g. `305`

Because ZR1/ZR1X are inactive and unpromoted, these rows should not affect `form-app/data.js` unless a separate future-model generation/promotion pass activates those models.

### ZR1/ZR1X `PCQ, VWT not available at this time`

Use existing option source and OVS status rows:

- `zr1_options.opt_pcq_001.detail_raw = '1. Not available at this time.'`
- `zr1x_options.opt_pcq_001.detail_raw = '1. Not available at this time.'`
- `zr1_options.opt_vwt_001.detail_raw = '1. Not available at this time. Included with (PCQ) Grille Screen Protection Package, LPO.'`
- `zr1x_options.opt_vwt_001.detail_raw = '1. Not available at this time. Included with (PCQ) Grille Screen Protection Package, LPO.'`
- set all `zr1_ovs` rows for `opt_pcq_001` and `opt_vwt_001` to `unavailable`
- set all `zr1x_ovs` rows for `opt_pcq_001` and `opt_vwt_001` to `unavailable`
- keep the option rows active so the workbook retains the source facts and a future inactive-preview generator can emit unavailable status if used.

Do not set these rows inactive unless the implementation probe proves future Z generators suppress unavailable rows incorrectly. If that happens, stop and report; do not hide it with code.

### ZR1/ZR1X `3N9 standard with EJH, EPX`

Current no-new-sheet/no-code scope cannot fully implement this behavior for ZR1/ZR1X because the workbook has no `zr1_rule_mapping` or `zr1x_rule_mapping` sheet, and existing `zr1_rule_groups` / `zr1x_rule_groups` only support grouped `excludes_any` relationships, not single-target interior `includes` rules.

Allowed in this pass:

- update `zr1_options.opt_3n9_001.detail_raw` and `zr1x_options.opt_3n9_001.detail_raw` to mention that EJH/EPX Very Dark Atmosphere interiors include Natural seat belt color.
- do not add partial `zr1_price_rules` / `zr1x_price_rules` zero-price rows without the matching include behavior; that would encode only half of the standard-with relationship.

Deferred:

- Full ZR1/ZR1X interior-sourced 3N9 auto-include behavior should wait for the future ZR1/ZR1X activation/schema pass that establishes active direct-rule source ownership without violating the no-new-sheet/no-code boundary.

## Exact files / workbook sheets / artifacts to change after approval

### Source workbook

`stingray_master.xlsx`:

- `stingray_options`
  - minimum TL;DR supporting note update: `opt_3n9_001.detail_raw`
- `rule_mapping`
  - add four EJH/EPX -> `opt_3n9_001` include rows.
- `price_rules`
  - add four EJH/EPX -> `opt_3n9_001` zero-price override rows.
- `grandSport_options`
  - `opt_3n9_001.detail_raw`
  - `opt_cfv_001.active`
  - `opt_cfv_001.detail_raw`
- `grandSport_rule_mapping`
  - add four EJH/EPX -> `opt_3n9_001` include rows.
- `grandSport_price_rules`
  - add four EJH/EPX -> `opt_3n9_001` zero-price override rows.
- `z06_options`
  - minimum TL;DR supporting note update: `opt_3n9_001.detail_raw`
  - verify/preserve `opt_r8e_002.price=2600`.
- `z06_rule_mapping`
  - add four EJH/EPX -> `opt_3n9_001` include rows.
- `z06_price_rules`
  - add four EJH/EPX -> `opt_3n9_001` zero-price override rows.
  - verify/preserve existing T0F/T0G -> R8E `$3000` rows.
- `zr1_options`
  - `opt_3n9_001.detail_raw` note-only update for EJH/EPX.
  - `opt_r8e_002.price=3000`.
  - `opt_pcq_001.detail_raw`.
  - `opt_vwt_001.detail_raw`.
- `zr1_ovs`
  - `opt_pcq_001` all variants -> `unavailable`.
  - `opt_vwt_001` all variants -> `unavailable`.
- `zr1x_options`
  - `opt_3n9_001.detail_raw` note-only update for EJH/EPX.
  - `opt_r8e_002.price=2600`.
  - `opt_pcq_001.detail_raw`.
  - `opt_vwt_001.detail_raw`.
- `zr1x_ovs`
  - `opt_pcq_001` all variants -> `unavailable`.
  - `opt_vwt_001` all variants -> `unavailable`.
- `default_selection_rules`
  - add `zr1_default_r8e_tax`.
  - add `zr1x_default_r8e_tax`.
  - verify/preserve `z06_default_r8e_tax`.

### Test expectation files

Patch existing tests only; do not add new test infrastructure:

- `tests/stingray-form-regression.test.mjs`
  - extend active Stingray 3LT seatbelt runtime coverage to include EJH/EPX -> 3N9.
- `tests/multi-model-runtime-switching.test.mjs`
  - extend Grand Sport 3LT seatbelt runtime coverage to include EJH/EPX -> 3N9.
- `tests/grand-sport-draft-data.test.mjs`
  - remove `opt_cfv_001` from the inactive/deferred suppression assertion.
  - add/assert `opt_cfv_001` emits as active/selectable/available with price `4495` in `sec_perf_ground_001`.
- `tests/z06-form-data-draft.test.mjs`
  - extend `z06InteriorSeatbeltIncludes` with EJH/EPX -> `opt_3n9_001`.
  - keep current R8E assertions unchanged.
- `tests/z06-runtime-rule-corrections.test.mjs`
  - extend `z06InteriorSeatbeltIncludes` with EJH/EPX -> `opt_3n9_001`.
  - keep current R8E assertions unchanged.

### Generated artifacts after regeneration

Expected generated output changes after approved workbook edits:

- `form-output/runtime/stingray-runtime-contract.json`
- `form-output/runtime/grand-sport-runtime-contract.json`
- `form-output/runtime/z06-runtime-contract.json`
- `form-app/data.js`

Possible additional checked artifacts if current generators/tests refresh them:

- model preview/draft artifacts under `form-output/` that are already part of the current workflow.

Do not hand-edit generated artifacts. Regenerate through existing commands only.

### Spec artifact to update on closure

- `.hermes/plans/distribution-updates-2026-06-22-tldr-workbook-spec.md`
  - after implementation, update status, completion date, changed sheets/files/artifacts, gates, residual risks, and next step.

## Proposed implementation sequence

1. Preflight:
   - confirm branch/status and unrelated dirty files.
   - confirm `~$stingray_master.xlsx` absent.
   - run workbook package validation before writing.

2. Re-probe current workbook rows:
   - active VDA `model_interior_scope` rows by model.
   - existing include/price rows for target interiors.
   - active seat-belt exclusive-group membership for `excl_seat_belts`, `gs_excl_seat_belts`, and `z06_excl_seat_belts`.
   - current CFV/R8E/PCQ/VWT source rows.
   - current `default_selection_rules` R8E rows.

3. Apply workbook source edits through existing workbook-editor operations / `scripts/apply_workbook_ops.py` batch path, or another existing safe-save entrypoint.
   - No new helper script.
   - No new sheet.
   - No generator/runtime code edits.
   - Dry-run first; write only after dry-run output matches the spec.

4. Reopen `stingray_master.xlsx` read-only and verify exact saved cells/rows on disk.

5. Regenerate active model artifacts:

```sh
.venv/bin/python scripts/generate_form.py --model stingray
.venv/bin/python scripts/generate_form.py --model grand_sport
.venv/bin/python scripts/generate_form.py --model z06
.venv/bin/python scripts/generate_registry.py
```

6. Patch existing tests listed above to match the workbook-owned behavior.

7. Review diffs for unrelated workbook/generated churn before running full targeted gates.

## Constraints repeated back

- Visual preservation: no CSS, HTML, card layout, media, or UI styling changes.
- No refactor: no generator/runtime restructuring.
- No new dependencies.
- No new workbook sheets, generated paths, helper scripts, or production code paths.
- Workbook source-of-truth: model the behavior in existing workbook rows, not in JavaScript or hidden Python branches.
- No hardcoded model/RPO-specific runtime behavior.
- Generated `form-output/*` and `form-app/data.js` are outputs only.
- Do not edit generated workbook `form_*` sheets.
- Dealer submission boundary: do not touch endpoint, payload shape, Turnstile, or submission code.
- Preserve Z06 R8E behavior already present unless the preflight probe proves drift.
- Do not promote ZR1/ZR1X or imply they are live runtime models.
- Do not add ZR1/ZR1X direct-rule sheets or fake half-behavior through price rules alone.
- Do not claim workbook changes landed until the saved workbook has been reopened and verified on disk.

## Risks and non-goals

Risks:

- Activating Grand Sport CFV changes generated Grand Sport runtime data and a current test expectation that suppresses `opt_cfv_001`.
- Adding EJH/EPX seatbelt includes changes runtime behavior for active models; browser/runtime tests should prove included 3N9 locks other seatbelt peers and prices at zero.
- ZR1/ZR1X future scaffolds are not promoted; workbook edits there should be source-prep only and must not alter live `form-app/data.js`.
- If the workbook editor ops path cannot express row appends cleanly for rule/price rows, stop and ask before using an ad hoc writer. The user explicitly requested no new code paths.
- `zr1_options` and `zr1x_options` currently store booleans as text in some cells. Do not normalize unrelated cell types while making these targeted edits.

Non-goals:

- No full order-guide footnote copy convergence beyond the TL;DR-supporting workbook notes.
- No ZR1/ZR1X runtime activation or promotion.
- No creation of `zr1_rule_mapping` or `zr1x_rule_mapping`.
- No changes to model discovery, registry promotion, runtime contract builder, or app submission behavior.
- No cleanup of unrelated seatbelt recommendations, Z15/J57 copy, stripe rules, or package/aero behavior unless separately approved.
- No broad workbook schema/type normalization.

## Validation plan

Pre-write validation:

```sh
.venv/bin/python scripts/validate_workbook_package.py stingray_master.xlsx
.venv/bin/python scripts/validate_workbook_schema.py stingray_master.xlsx
```

Workbook apply dry-run/write using existing pipeline:

```sh
.venv/bin/python scripts/apply_workbook_ops.py <approved-ops-batch>.json
.venv/bin/python scripts/apply_workbook_ops.py <approved-ops-batch>.json --write
```

Post-write workbook verification:

- Reopen `stingray_master.xlsx` with `openpyxl` read-only and verify:
  - 12 active-model EJH/EPX include rows exist across `rule_mapping`, `grandSport_rule_mapping`, and `z06_rule_mapping`.
  - 12 matching zero-price override rows exist across `price_rules`, `grandSport_price_rules`, and `z06_price_rules`.
  - The active model seat-belt exclusive groups still contain all six seat-belt option IDs before relying on peer locking:
    - `exclusive_groups.excl_seat_belts` + `exclusive_group_members`: `opt_719_001`, `opt_3n9_001`, `opt_379_001`, `opt_3a9_001`, `opt_3f9_001`, `opt_3m9_001`.
    - `grandSport_exclusive_groups.gs_excl_seat_belts` + `grandSport_exclusive_members`: same six option IDs.
    - `z06_exclusive_groups.z06_excl_seat_belts` + `z06_exclusive_members`: same six option IDs.
  - `grandSport_options.opt_cfv_001.active=True` and no longer carries the unavailable-at-this-time detail.
  - `grandSport_ovs.opt_cfv_001` still has six `available` statuses.
  - `z06_options.opt_r8e_002.price=2600`.
  - `z06_price_rules` still has T0F/T0G -> R8E `3000` rows.
  - `zr1_options.opt_r8e_002.price=3000`.
  - `zr1x_options.opt_r8e_002.price=2600`.
  - `zr1_ovs` / `zr1x_ovs` PCQ and VWT statuses are all `unavailable`.
  - `default_selection_rules` contains `zr1_default_r8e_tax` and `zr1x_default_r8e_tax`.

Regeneration:

```sh
.venv/bin/python scripts/generate_form.py --model stingray
.venv/bin/python scripts/generate_form.py --model grand_sport
.venv/bin/python scripts/generate_form.py --model z06
.venv/bin/python scripts/generate_registry.py
```

Focused active-model gates:

```sh
node --test tests/stingray-form-regression.test.mjs
node --test tests/grand-sport-contract-preview.test.mjs
node --test tests/grand-sport-draft-data.test.mjs
node --test tests/z06-contract-preview.test.mjs
node --test tests/z06-form-data-draft.test.mjs
node --test tests/z06-runtime-rule-corrections.test.mjs
node --test tests/multi-model-runtime-switching.test.mjs
```

Workbook/source metadata gates:

```sh
.venv/bin/python scripts/validate_workbook_schema.py stingray_master.xlsx
.venv/bin/python -m pytest tests/test_model_config_metadata.py tests/test_registry_promotion_metadata.py tests/test_schema_validation_metadata.py -q
```

Optional future-Z source sanity check:

- Not run in the current repo: `tests/test_future_z_rule_audit.py` and `tests/test_future_model_option_pricing.py` are absent, so do not include them as runnable gates for this pass.
- If future-Z source tests are reintroduced before implementation, re-inventory current `tests/` paths first and add only existing, relevant future-Z gates.

Manual verification pending after gates:

- Local browser smoke for active models only:
  - Stingray EJH/EPX interiors auto-add 3N9 at zero price and block other seatbelts.
  - Grand Sport EJH/EPX interiors auto-add 3N9 at zero price and block other seatbelts.
  - Grand Sport CFV appears as an available selectable ground-effects option.
  - Z06 EJH/EPX interiors auto-add 3N9 at zero price and block other seatbelts.
  - Z06 R8E remains selected by default at `$2,600`, rising to `$3,000` with T0F/T0G.

## Approval question

Approve this workbook-only TL;DR pass as scoped above?

Recommended approval shape: approve active-model EJH/EPX seatbelt rows, Grand Sport CFV activation, Z06 R8E verification/preservation, and inactive ZR1/ZR1X source-prep for R8E + PCQ/VWT, with ZR1/ZR1X 3N9 behavior explicitly deferred because the required direct-rule source sheets do not exist under the no-new-sheet/no-code boundary.

## Next step guidance

If approved and implemented, the next safe pass is a separate footnote/copy convergence review for the full `dist_updates/dist-updates-6-22.md` text, because this spec deliberately models only the TL;DR behavior and minimal supporting notes. That pass should be copy/data-only and should not change rule/pricing behavior unless a new business rule is found during workbook-source inspection.
