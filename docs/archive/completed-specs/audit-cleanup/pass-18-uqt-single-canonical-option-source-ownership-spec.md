# Pass 18 — UQT Single Canonical Option Source Ownership Spec

Status: Implemented 2026-06-24.
Date: 2026-06-24
Recommended reasoning level for implementation agent: high.

Source context:

- `AGENTS.md`
- `docs/audit-cleanup/pass-16-variant-override-sheet-semantics-report.md`
- `docs/audit-cleanup/pass-17-default-selected-display-metadata-derivation-spec.md`
- `docs/metadata-runtime-redundancy-6-23.md`
- `docs/Audit-route-map.md`
- `27vette-workbook-guard` reference `variant-override-semantics-classification.md`

## Implementation completion evidence

Implemented on 2026-06-24 after approval.

Changed source files and workbook sheets:

- `scripts/corvette_form_generator/production.py`
  - Added generic Stingray production handling for model-scoped variant override `section_id`.
  - Recomputes section-derived choice metadata from the overridden section.
  - Preserves `status="standard"` when `display_behavior=display_only` is applied to an OVS-standard choice.
  - No UQT/RPO-specific production branch was added.
- `stingray_master.xlsx`
  - Added `stingray_variant_overrides` with model-scoped UQT rows for 2LT/3LT coupe/convertible display-only trim placement.
  - Added active `model_workbook_sources` row for Stingray `variant_option_overrides_sheet=stingray_variant_overrides`.
  - Removed `stingray_options.opt_uqt_001` and its six `stingray_ovs` rows.
  - Removed the four global `variant_option_overrides` Stingray UQT suppression rows.
  - Removed inactive duplicate `grandSport_options.opt_uqt_002` and its six `grandSport_ovs` rows.
  - Preserved Grand Sport and Z06 canonical UQT override rows.
- `tests/stingray-generator-stability.test.mjs`
  - Added a generic Stingray production-path guard for model-scoped section override placement and standard-preserving display-only behavior.
  - Updated UQT source/contract assertions for the new single-canonical-row shape.

Generated artifacts refreshed:

- `form-output/runtime/stingray-runtime-contract.json`
- `form-output/stingray-form-data.json`
- `form-output/stingray-form-data.csv`
- `form-output/runtime/grand-sport-runtime-contract.json` — timestamp-only drift.
- `form-app/data.js`

Generated drift allowed and verified:

- Stingray UQT choices reduced from 12 to 6 by removing duplicate `opt_uqt_001` rows.
- Stingray canonical UQT is now `opt_uqt_002` across all variants.
- Stingray 1LT UQT remains available/selectable/priced in `sec_inte_001`.
- Stingray 2LT/3LT UQT is now `standard`, `selectable=False`, `display_behavior=display_only`, and placed in `sec_2lte_001` / `sec_3lte_001` standard equipment.
- Non-UQT Stingray payload drift was rejected by an allowlist probe after ignoring generated timestamp and the expected availability-count validation message.
- Grand Sport runtime contract matched the before snapshot apart from `generated_at`.
- Z06 runtime contract was restored after the Z06 gate and had no final diff.

Workbook verification:

- Safe-save backups created:
  - `backups/stingray_master-20260624-142809.xlsx`
  - `backups/stingray_master-20260624-142858.xlsx`
- `.venv/bin/python scripts/validate_workbook_package.py stingray_master.xlsx`: valid, 0 issues.
- Post-save read-only `openpyxl` verification returned `PASS18_WORKBOOK_ROWS_OK`:
  - `stingray_options` has only `opt_uqt_002` for UQT.
  - `stingray_ovs` has six UQT rows, all `opt_uqt_002`.
  - `variant_option_overrides` has no UQT rows.
  - `stingray_variant_overrides` has four UQT display-only trim-placement rows.
  - `grandSport_options` has only `opt_uqt_001` for UQT.
  - `grandSport_ovs` has six UQT rows, all `opt_uqt_001`.
  - `grandSport_variant_overrides` and `z06_variant_overrides` retain their four UQT display-only rows.

Gate results:

- `.venv/bin/python -m py_compile scripts/corvette_form_generator/production.py`: pass.
- `.venv/bin/python scripts/validate_workbook_schema.py stingray_master.xlsx`: valid, 0 issues.
- `node --test tests/stingray-form-regression.test.mjs`: 87/87 pass.
- `node --test tests/stingray-generator-stability.test.mjs`: 14/14 pass.
- `node --test tests/grand-sport-contract-preview.test.mjs`: 6/6 pass.
- `node --test tests/grand-sport-draft-data.test.mjs`: 19/19 pass.
- `node --test tests/z06-interior-accessory-cleanup.test.mjs`: 7/7 pass; Z06 runtime contract restored afterward.
- `node --test tests/multi-model-runtime-switching.test.mjs`: 46/46 pass.
- `git diff --check`: pass.
- Registry sync probe: `PASS18_POST_GATE_ARTIFACT_SYNC_OK`.
- Z06 final artifact probe: no `form-output/runtime/z06-runtime-contract.json` diff.
- Browser/runtime proof: `PASS18_BROWSER_UQT_PROOF_OK` for Stingray, Grand Sport, and Z06 selectable vs standard/display-only UQT behavior.

What stayed unchanged:

- No runtime JavaScript behavior changes.
- No visual/layout changes.
- No dealer submission endpoint, payload shape, or Turnstile changes.
- No Z06 workbook source changes or final Z06 generated artifact diff.
- No cross-model option ID unification; Stingray keeps canonical `opt_uqt_002`, while Grand Sport/Z06 keep canonical `opt_uqt_001`.

Residual risks and follow-up:

- `variant_option_overrides` was left empty for active UQT/BC7/NGA behavior at Pass 18 completion. Historical follow-up: Pass 19 later retired the physical sheet and global-first loader path.
- The remaining model-scoped UQT display-only rows are still canonical behavior owners for trim-standard placement/selectability; there is no immediate reason to refactor them further.
- No obvious next cleanup pass is implied by UQT after this implementation. Historical follow-up on the empty global sheet became Pass 19 and was implemented on 2026-06-24.

## Goal

Normalize UQT source ownership to one canonical active UQT option row per active model while preserving current customer-facing behavior:

- 1LT / 1LZ variants expose UQT as a selectable paid option where the model currently does so.
- 2LT / 3LT and 2LZ / 3LZ variants show UQT as standard/display-only trim equipment.
- Generated/runtime behavior, pricing totals, build summary, and dealer/build output stay equivalent except for approved UQT source-row identity cleanup.

The preferred direction is option 1 from the user discussion: one canonical option row per model. This pass should not keep separate paid/selectable and standard/display-only UQT option rows inside the same active model source sheet.

## Diagnosis

Change type for this spec: docs-only.

Change type for the future implementation pass: mixed generator + workbook/data + generated artifacts + tests, with no intended runtime UX behavior change. A small generic Stingray production-path alignment is required before the workbook row migration: the production generator currently loads variant overrides but does not apply `section_id`, and its `display_only` branch forces `status="available"` instead of preserving `standard` rows.

Risk level: medium-high. This pass intentionally changes the generated UQT source identity for some Stingray standard-equipment rows and removes duplicate source rows. Strict timestamp-only contract parity is not the correct gate; the implementation must use an allowlisted UQT-only contract diff plus runtime/browser behavior proof.

Root cause:

- UQT expresses the same product behavior across active models but through different workbook ownership routes.
- Stingray currently uses two active UQT source rows plus global override suppression:
  - `stingray_options.opt_uqt_002`: paid/selectable UQT in `sec_inte_001`, price `1495`, active.
  - `stingray_options.opt_uqt_001`: nonselectable standard-equipment UQT row in `sec_2lte_001`, active.
  - `stingray_ovs` has status rows for both option IDs across all six Stingray variants.
  - `variant_option_overrides` suppresses `opt_uqt_002` on 2LT/3LT with `status=unavailable`, `selectable=False`, and emitted `active=False`. On this global sheet, `active` is emitted choice metadata, not row activation.
- Grand Sport already mostly follows the single-canonical-row pattern but still has inactive duplicate source clutter:
  - `grandSport_options.opt_uqt_001`: active/selectable canonical UQT row in `sec_inte_001`, price `1495`.
  - `grandSport_options.opt_uqt_002`: inactive standard-equipment mirror row.
  - `grandSport_ovs` still has status rows for both option IDs.
  - `grandSport_variant_overrides` moves `opt_uqt_001` to display-only trim equipment for 2LT/3LT variants with `selectable=False`, `display_behavior=display_only`, and `section_id=sec_2lte_001` / `sec_3lte_001`.
- Z06 already follows the single-canonical-row pattern:
  - `z06_options.opt_uqt_001`: one active UQT row in `sec_inte_001`, price `0`.
  - `z06_price_rules.z06_pr_1lz_uqt_001`: restores the 1LZ selectable UQT charge.
  - `z06_variant_overrides` moves 2LZ/3LZ rows to display-only trim equipment.

Conclusion: UQT does have different ownership routes across models. Cleanup is justified, but the safe cleanup is source-row normalization, not deleting UQT presentation overrides cold.

## Current evidence inspected for this spec

Branch/status at spec creation:

- `git status --short`: no output before this spec write in the active shell snapshot used for the current UQT probe. Earlier Pass 17 files may remain dirty/untracked in the broader working copy; implementation must re-run status before editing.

Workbook probes, read-only via `openpyxl`:

- `stingray_options`
  - `opt_uqt_002`, RPO `UQT`, price `1495`, section `sec_inte_001`, selectable `True`, active `True`.
  - `opt_uqt_001`, RPO `UQT`, price blank, section `sec_2lte_001`, selectable `False`, active `True`.
- `stingray_ovs`
  - 12 UQT rows: both `opt_uqt_001` and `opt_uqt_002` across all six Stingray variants.
- `variant_option_overrides`
  - 4 remaining rows after Pass 17, all for `stingray / opt_uqt_002 / 2LT|3LT`, using global emitted-value semantics.
- `grandSport_options`
  - `opt_uqt_001`, RPO `UQT`, price `1495`, section `sec_inte_001`, selectable `True`, active `True`.
  - `opt_uqt_002`, RPO `UQT`, price blank, section `sec_2lte_001`, selectable `False`, active `False`.
- `grandSport_ovs`
  - 12 UQT rows: both `opt_uqt_001` and inactive duplicate `opt_uqt_002` across all six Grand Sport variants.
- `grandSport_variant_overrides`
  - 4 active rows for `opt_uqt_001` 2LT/3LT display-only standard-equipment placement.
- `z06_options`
  - `opt_uqt_001`, RPO `UQT`, price `0`, section `sec_inte_001`, selectable `True`, active `True`.
- `z06_ovs`
  - 6 UQT rows for `opt_uqt_001` only.
- `z06_price_rules`
  - `z06_pr_1lz_uqt_001` keeps 1LZ UQT priced while 2LZ/3LZ standard UQT stays unpriced.
- `z06_variant_overrides`
  - 4 active rows for `opt_uqt_001` 2LZ/3LZ display-only standard-equipment placement.
- `section_presentation`
  - Active `trim_equipment` standard-equipment bucket rows exist for Stingray, Grand Sport, and Z06: `sec_1lte_001`, `sec_2lte_001`, `sec_3lte_001`, with Z06 display labels mapped to 1LZ/2LZ/3LZ.
- `model_workbook_sources`
  - `variant_option_overrides_sheet` active rows exist for Grand Sport (`grandSport_variant_overrides`) and Z06 (`z06_variant_overrides`), but not Stingray.

Generated artifact probes, read-only:

- Stingray currently emits 12 UQT choices:
  - `opt_uqt_002`: 6 rows. 1LT rows are paid/selectable; 2LT/3LT rows are unavailable/inactive due to `variant_option_overrides`.
  - `opt_uqt_001`: 6 nonselectable standard-equipment rows. 2LT/3LT are standard; 1LT rows are available but nonselectable standard-equipment data.
- Grand Sport currently emits 6 UQT choices, all `opt_uqt_001`:
  - 1LT rows are paid/selectable in `interior_trim`.
  - 2LT/3LT rows are `standard`, `selectable=False`, `display_behavior=display_only`, and route to `standard_equipment`.
- Z06 currently emits 6 UQT choices, all `opt_uqt_001`:
  - 1LZ rows are selectable and get price through `z06_price_rules`.
  - 2LZ/3LZ rows are `standard`, `selectable=False`, `display_behavior=display_only`, and route to `standard_equipment`.

Code path evidence:

- `scripts/corvette_form_generator/runtime_metadata.py`
  - `load_variant_option_overrides()` supports two contracts:
    - global `variant_option_overrides`, where `active` is emitted choice metadata and rows are read with `optional_rows()`;
    - model-scoped fallback sheets, where `active` is row activation and fields include `section_id`.
- `scripts/corvette_form_generator/production.py`
  - `build_production_source_data()` loads workbook model config overrides, then calls `load_variant_option_overrides(wb, MODEL_CONFIG.model_key, MODEL_CONFIG.variant_option_overrides_sheet)`.
  - Current blocker found during review: the Stingray production path applies only `status`, `selectable`, `active`, and `display_behavior` from variant overrides; it does not apply `section_id` when building choice rows.
  - Current blocker found during review: the production `display_only` branch forces `status="available"`, while `build_standard_equipment()` includes only `status=="standard"`. That differs from the inspection path, where `display_behavior_status()` preserves `standard` for display-only standard rows.
  - Pass 18 must add a generic production-path fix before workbook row deletion: apply override `section_id` to the emitted choice and recompute section-derived fields for that choice, and preserve `status="standard"` when a display-only override is applied to an OVS-standard row.
- `scripts/corvette_form_generator/inspection.py`
  - Grand Sport/Z06 already use the model-scoped variant override contract through `keyed_variant_option_overrides()` and `apply_variant_option_override()`.
  - `display_behavior_status()` already preserves `standard` for display-only standard rows.

Test evidence:

- `tests/stingray-generator-stability.test.mjs`
  - Currently pins the remaining Stingray `opt_uqt_002` override rows and guards against hardcoded generator logic.
- `tests/grand-sport-draft-data.test.mjs`
  - Currently asserts Grand Sport emits only canonical `opt_uqt_001` and no `opt_uqt_002` choices.
- `tests/z06-interior-accessory-cleanup.test.mjs`
  - Pins Z06 UQT 1LZ selectable and 2LZ/3LZ display-only standard-equipment behavior.
- `tests/multi-model-runtime-switching.test.mjs`
  - Pins Grand Sport UQT runtime behavior from workbook overrides.

## Proposed ownership decision

Adopt one active canonical UQT option row per active model.

Recommended identity rule for this pass:

- Do not force cross-model option-id unification in the same pass. Preserve each model's current customer-selectable UQT option identity where possible to reduce live payload churn.
- Stingray canonical row: `opt_uqt_002`, because it is the current 1LT paid/selectable UQT card.
- Grand Sport canonical row: `opt_uqt_001`, already the current paid/selectable UQT card.
- Z06 canonical row: `opt_uqt_001`, already the only UQT source row.

This means the normalized source model is consistent even though the local option IDs differ by model. Cross-model `option_id` renaming for Stingray is a separate optional identity-normalization decision and is not recommended here because it would change the currently selectable Stingray 1LT UQT choice identity without adding ownership clarity.

Canonical owners after implementation:

- Active model option sheet (`*_options`): one canonical UQT product row per active model.
- Active model OVS sheet (`*_ovs`): variant availability/standard status for the canonical UQT row.
- Model-scoped variant override sheet: only variant-specific presentation/placement for standard UQT rows (`selectable=False`, `display_behavior=display_only`, trim-standard `section_id`).
- Price rules: only when needed for model-specific price semantics, currently Z06 1LZ UQT.

## Required generic production-path alignment before workbook edits

The implementation must first align Stingray production override handling with the existing model-scoped contract used by Grand Sport/Z06. This is generic generator behavior, not a UQT hardcode.

Target file:

- `scripts/corvette_form_generator/production.py`

Required behavior:

1. When a variant override supplies `section_id`, build the emitted choice from that override section rather than the source option's base section.
   - Recompute `section_name`, `standard_equipment_group_type`, `step_key`, `selection_mode`, `selection_mode_label`, and `choice_mode` from the resolved choice section.
   - Preserve the source option's product fields: `option_id`, `rpo`, label, description, raw source detail, price, display order, and base selectable/active before override application.
2. When `display_behavior == "display_only"`, match the inspection path's status behavior:
   - if the OVS/override status is `standard`, keep `status="standard"`;
   - otherwise use `status="available"`;
   - always set `selectable="False"` and `active="True"`.
3. Keep `auto_only` behavior unchanged.
4. Do not add RPO/model-specific branches such as `if option_id == "opt_uqt_002"`.

RED/guard expectations before workbook row deletion:

- Add or update a focused generator test that would fail with current `production.py` if a Stingray model-scoped variant override supplies `section_id=sec_2lte_001` plus `display_behavior=display_only` for an OVS-standard row.
- The test should prove the emitted choice is standard equipment, not merely nonselectable.
- Keep the existing source-string guard against hardcoded `opt_uqt_002` logic.

## Exact workbook changes for the implementation pass

Preflight before writing:

- Confirm Excel is closed and `~$stingray_master.xlsx` is absent.
- Run `.venv/bin/python scripts/validate_workbook_package.py stingray_master.xlsx`.
- Snapshot current generated artifacts to `/tmp/pass-18-before/`.

Workbook edit target: `stingray_master.xlsx` via `save_workbook_safely()` only.

### Stingray

1. Add a model-scoped `stingray_variant_overrides` sheet with the same contract as `grandSport_variant_overrides` / `z06_variant_overrides`:

```text
option_id, variant_id, selectable, display_behavior, section_id, active, note
```

2. Add an active `model_workbook_sources` row:

```text
model_key=stingray
source_role=variant_option_overrides_sheet
sheet_name=stingray_variant_overrides
active=True
notes=Model-scoped Stingray variant presentation overrides; active is row activation.
```

3. Move remaining Stingray UQT standard-placement behavior from global emitted-value overrides to `stingray_variant_overrides` using canonical `opt_uqt_002`:

```text
opt_uqt_002 / 2lt_c07 / selectable=False / display_behavior=display_only / section_id=sec_2lte_001 / active=True
opt_uqt_002 / 2lt_c67 / selectable=False / display_behavior=display_only / section_id=sec_2lte_001 / active=True
opt_uqt_002 / 3lt_c07 / selectable=False / display_behavior=display_only / section_id=sec_3lte_001 / active=True
opt_uqt_002 / 3lt_c67 / selectable=False / display_behavior=display_only / section_id=sec_3lte_001 / active=True
```

4. Delete the four remaining global `variant_option_overrides` rows for Stingray `opt_uqt_002` suppression. Leave the global sheet header-only unless a later pass explicitly retires the sheet.

5. Delete `stingray_options.opt_uqt_001`.

6. Delete all six `stingray_ovs` rows for `opt_uqt_001`.

7. Keep `stingray_options.opt_uqt_002` and its six `stingray_ovs` rows. Its 2LT/3LT OVS statuses should remain `standard`; the new `stingray_variant_overrides` rows should own display-only trim placement.

Expected generated Stingray UQT shape after implementation:

- 6 UQT choices total, all `opt_uqt_002`.
- 1LT coupe/convertible rows: `status=available`, `selectable=True`, `active=True`, section `sec_inte_001`, step `interior_trim`, price `1495`.
- 2LT/3LT coupe/convertible rows: `status=standard`, `selectable=False`, `active=True`, `display_behavior=display_only`, section `sec_2lte_001` or `sec_3lte_001`, step `standard_equipment`.
- No emitted `opt_uqt_001` Stingray choices.

### Grand Sport

1. Keep `grandSport_options.opt_uqt_001` as the canonical UQT row.

2. Keep the four `grandSport_variant_overrides` UQT display-only section-placement rows for `opt_uqt_001`.

3. Delete inactive duplicate `grandSport_options.opt_uqt_002`.

4. Delete all six `grandSport_ovs` rows for `opt_uqt_002`.

Expected generated Grand Sport UQT shape after implementation:

- Still 6 UQT choices total, all `opt_uqt_001`.
- No generated payload drift except removal of inactive source clutter should be expected. If generated Grand Sport runtime changes beyond timestamps, stop and classify before continuing.

### Z06

No workbook source changes expected.

Z06 should remain the reference pattern for one active canonical UQT row plus model-scoped display-only standard-equipment overrides and a 1LZ price rule.

## Exact repo files expected to change in implementation

Expected source/workbook/test/docs changes:

- `scripts/corvette_form_generator/production.py`
  - Generic variant override `section_id` support in the Stingray production path.
  - Generic display-only status preservation matching the inspection path.
- `stingray_master.xlsx`
- `tests/stingray-generator-stability.test.mjs`
- `tests/stingray-form-regression.test.mjs` if current runtime assertions need updated UQT identity/standard-equipment expectations.
- `tests/grand-sport-draft-data.test.mjs`
- `tests/z06-interior-accessory-cleanup.test.mjs` only if a focused source-owner guard is needed; no Z06 behavior change should be introduced.
- `tests/workbook-schema-standardization.test.mjs` if its source-role/sheet inventory assertions need the new `stingray_variant_overrides` role.
- `docs/audit-cleanup/pass-18-uqt-single-canonical-option-source-ownership-spec.md` for completion evidence before handoff.
- `docs/Audit-route-map.md` and `docs/metadata-runtime-redundancy-6-23.md` if the implementation changes the standing next-step guidance.

Expected generated artifacts after regeneration:

- `form-output/runtime/stingray-runtime-contract.json`
- `form-output/stingray-form-data.json`
- `form-output/stingray-form-data.csv`
- `form-output/runtime/grand-sport-runtime-contract.json` with timestamp-only drift if Grand Sport is regenerated for verification.
- `form-app/data.js`

Expected code changes:

- Required: `scripts/corvette_form_generator/production.py` generic override-section/display-only alignment.
- Not expected: `scripts/corvette_form_generator/inspection.py`, `form-app/app.js`, or RPO-specific generator branches.

## Constraints to preserve

- No visual styling changes.
- No runtime JavaScript product/RPO hardcodes.
- No dealer submission endpoint, payload boundary, Turnstile behavior, or WordPress route changes.
- No new dependencies.
- No broad refactor of generator routing.
- No changes to BC7/NGA Pass 17 derivation.
- Pass 18 did not delete `grandSport_variant_overrides` or `z06_variant_overrides` wholesale.
- Pass 18 did not delete the global `variant_option_overrides` sheet wholesale; making it header-only for active rows was enough for that pass. Historical follow-up: Pass 19 later retired the empty sheet and global-first loader path.
- Do not change Z06 UQT behavior, including `z06_price_rules.z06_pr_1lz_uqt_001`.
- Do not force cross-model `option_id` unification for UQT unless the user explicitly approves the extra identity churn.

## Risks

1. Stingray generated UQT identity drift is intentional but must be tightly allowlisted.
   - Standard-equipment Stingray UQT rows should move from `opt_uqt_001` to canonical `opt_uqt_002`.
   - The paid/selectable Stingray 1LT UQT card should keep `opt_uqt_002`.

2. Price fields can look different even when totals remain correct.
   - Grand Sport standard UQT rows already carry base price `1495` while `status=standard` and `display_behavior=display_only` prevent customer charge behavior.
   - Stingray standard rows may similarly carry the canonical row price after cleanup. Runtime total tests must prove 2LT/3LT do not charge UQT as an add-on.

3. The global `variant_option_overrides.active` semantics are dangerous.
   - Migrating Stingray UQT into a model-scoped sheet should remove the remaining need for emitted-value `active=False` rows.
   - Tests must guard that the old suppression rows are gone and not reintroduced.

4. Workbook table refs and sheet creation can corrupt the workbook if done casually.
   - Use `save_workbook_safely()` and verify saved headers/rows on disk after reopening.

5. Strict generated-contract parity is not applicable.
   - Use an allowlisted contract diff that permits only UQT row identity/count/placement changes plus timestamps.
   - Any non-UQT payload drift should fail the pass unless explicitly explained and approved.

6. The Stingray production path must be fixed generically before workbook rows move.
   - Without `section_id` override support, `stingray_variant_overrides` would not move standard UQT rows into `sec_2lte_001` / `sec_3lte_001`.
   - Without standard-preserving `display_only`, standard UQT rows would become `available` and fail standard-equipment export.
   - This is a generator-contract alignment with the existing inspection path, not a UQT exception.

## Non-goals

- Do not implement this spec without approval.
- Do not normalize all duplicate/nonruntime option rows beyond UQT.
- Do not rename UQT option IDs across all models.
- Do not retire the variant override sheet family wholesale.
- Do not remove Z06 price-rule semantics.
- Do not change customer-facing labels/copy for UQT.
- Do not modify runtime JavaScript to special-case UQT.

## Validation plan for the implementation pass

Preflight:

```sh
git status --short --branch
test ! -e '~$stingray_master.xlsx'
.venv/bin/python scripts/validate_workbook_package.py stingray_master.xlsx
mkdir -p /tmp/pass-18-before /tmp/pass-18-after
cp form-output/runtime/stingray-runtime-contract.json /tmp/pass-18-before/
cp form-output/runtime/grand-sport-runtime-contract.json /tmp/pass-18-before/
cp form-output/runtime/z06-runtime-contract.json /tmp/pass-18-before/
cp form-output/stingray-form-data.json /tmp/pass-18-before/
cp form-app/data.js /tmp/pass-18-before/
```

Code-alignment proof before workbook deletion:

```sh
node --test tests/stingray-generator-stability.test.mjs
```

The implementation should add a focused assertion in that test file (or an equally targeted generator test) that fails before the generic `production.py` fix and passes before any workbook rows are deleted. The assertion must prove production applies model-scoped override `section_id` and preserves `standard` for display-only standard rows without hardcoding UQT.

After workbook write:

```sh
.venv/bin/python scripts/validate_workbook_package.py stingray_master.xlsx
.venv/bin/python - <<'PY'
# Reopen workbook read-only and assert:
# - exactly one active UQT option row per active model sheet;
# - no stingray_options.opt_uqt_001;
# - no grandSport_options.opt_uqt_002;
# - no stingray_ovs/grandSport_ovs duplicate UQT rows for removed option IDs;
# - no active rows in global variant_option_overrides for UQT;
# - stingray_variant_overrides has exactly four UQT display_only section rows;
# - Grand Sport and Z06 UQT override rows remain unchanged.
PY
```

Regeneration:

```sh
.venv/bin/python scripts/generate_form.py --model stingray
.venv/bin/python scripts/generate_form.py --model grand_sport
.venv/bin/python scripts/generate_registry.py
```

Do not regenerate Z06 as an implementation artifact-writing step for this pass unless implementation unexpectedly touches a shared Z06 path. Z06 source data is unchanged. If a required Z06 gate invokes `scripts/generate_form.py --model z06 --emit-inspection` and rewrites `form-output/runtime/z06-runtime-contract.json`, run it in a snapshot-and-restore flow so the final diff does not include Z06 timestamp churn.

Generated contract checks:

- Run a custom Node/Python diff that ignores timestamps and allowlists only:
  - Stingray UQT row count changing from 12 to 6.
  - Stingray standard UQT row identity moving from `opt_uqt_001` to `opt_uqt_002`.
  - Stingray 2LT/3LT UQT rows gaining/retaining `display_behavior=display_only`, standard-equipment section placement, and `selectable=False`.
  - Deletion of emitted unavailable/inactive Stingray `opt_uqt_002` rows.
- Require zero non-UQT drift in Stingray.
- Require timestamp-only drift for Grand Sport after regeneration; if Grand Sport runtime changes beyond timestamp, stop and classify before continuing.
- Require no final `form-output/runtime/z06-runtime-contract.json` diff. If `tests/z06-interior-accessory-cleanup.test.mjs` rewrites it as a timestamp-only side effect, restore the pre-gate file before final diff review and report that restoration.
- Verify `form-app/data.js` registry payload matches regenerated Stingray/Grand Sport artifacts and preserves the existing Z06 payload except for registry wrapper formatting/timestamps already present in the source artifacts.

Targeted gates:

```sh
.venv/bin/python scripts/validate_workbook_schema.py stingray_master.xlsx
node --test tests/stingray-generator-stability.test.mjs
node --test tests/stingray-form-regression.test.mjs
node --test tests/grand-sport-draft-data.test.mjs
node --test tests/grand-sport-contract-preview.test.mjs
node --test tests/multi-model-runtime-switching.test.mjs
```

Z06 regression gate with artifact restoration:

```sh
cp form-output/runtime/z06-runtime-contract.json /tmp/pass-18-before/z06-runtime-contract.pre-z06-gate.json
node --test tests/z06-interior-accessory-cleanup.test.mjs
cmp /tmp/pass-18-before/z06-runtime-contract.pre-z06-gate.json form-output/runtime/z06-runtime-contract.json || cp /tmp/pass-18-before/z06-runtime-contract.pre-z06-gate.json form-output/runtime/z06-runtime-contract.json
git diff --quiet -- form-output/runtime/z06-runtime-contract.json
```

Rationale: `tests/z06-interior-accessory-cleanup.test.mjs` calls `scripts/generate_form.py --model z06 --emit-inspection`, and the non-Stingray generator writes `form-output/runtime/z06-runtime-contract.json` with a fresh `generated_at`. Pass 18 still needs the Z06 behavioral guard, but the final implementation diff should not carry Z06 timestamp churn because Z06 source behavior is out of scope.

Browser/runtime proof:

Serve the app locally:

```sh
cd form-app
../.venv/bin/python -m http.server 8000
```

Browser proof must cover:

- Stingray 1LT coupe and convertible:
  - UQT visible/selectable in Interior Trim.
  - Selecting UQT adds the expected priced selected RPO and price total.
- Stingray 2LT/3LT coupe and convertible:
  - UQT appears as standard/display-only trim equipment.
  - UQT is not selectable as a paid add-on.
  - Price total does not add a paid UQT line.
- Grand Sport 1LT and 2LT/3LT:
  - Existing selectable vs standard/display-only behavior unchanged.
- Z06 1LZ and 2LZ/3LZ:
  - Existing selectable/price-rule vs standard/display-only behavior unchanged.
- Model switching between Stingray, Grand Sport, and Z06 does not leak UQT state or duplicate UQT cards.

Completion requirements:

- Update this spec to `Implemented` with changed files/sheets/artifacts, gate results, allowed generated drift, browser proof, residual risks, and next-pass guidance.
- Update `docs/Audit-route-map.md` and `docs/metadata-runtime-redundancy-6-23.md` if they would otherwise still describe UQT as an open source-ownership mismatch.

## Historical approval prompt

Pass 18 was approved and implemented on 2026-06-24 as a narrow generator-alignment plus workbook-source ownership cleanup to normalize UQT to one canonical active option row per active model: first add generic Stingray production support for model-scoped variant override `section_id` and standard-preserving `display_only`, then use `opt_uqt_002` as Stingray's canonical row and `opt_uqt_001` for Grand Sport/Z06, add a model-scoped `stingray_variant_overrides` sheet for display-only trim placement, delete only duplicate UQT source/OVS/global suppression rows, regenerate Stingray/Grand Sport plus registry, run the Z06 gate in snapshot-and-restore mode so no Z06 artifact diff remains, run the targeted gates and browser/runtime proof, and update this spec with completion evidence before handoff.
