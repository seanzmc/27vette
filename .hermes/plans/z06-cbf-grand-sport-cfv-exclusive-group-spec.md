# Z06 CBF Option + Grand Sport CFV Exclusive-Group Spec

Status: spec only / awaiting approval
Date: 2026-06-25

## Diagnosis

Two workbook-owned behavior gaps are present.

1. Grand Sport CFV is active/selectable but not active in the ground-effects exclusive group.
   - `grandSport_options.opt_cfv_001` is active/selectable in `sec_perf_ground_001`.
   - `grandSport_ovs` has `opt_cfv_001` available for all six Grand Sport variants.
   - `grandSport_exclusive_members.gs_excl_ground_effects / opt_cfv_001` exists with `active=False`.
   - Generated Grand Sport runtime data therefore emits `gs_excl_ground_effects` with only `opt_cfl_001` and `opt_cfz_001`.
   - Runtime package-included lock behavior for T0F/FEY-included CFZ depends on the included target being in an active `single_within_group` exclusive group. `sec_perf_ground_001` being `single_select_opt` covers manual same-section replacement, but does not lock included CFZ peers by itself.

2. Z06 CBF is absent from active workbook source data.
   - `z06_options` has no `opt_cbf_001` / `CBF` row.
   - `z06_ovs` has no `opt_cbf_001` availability rows.
   - `z06_rule_mapping` has no CBF conflicts.
   - `z06_rule_group_members` has no CBF member in `z06_group_gba_excludes_accent_and_roof_choices`.
   - User supplied authoritative option details for this pass:
     - option_id: `opt_cbf_001`
     - RPO: `CBF`
     - Name: `Body-color painted Rockers and splitter`
     - Raw Detail: `Not available with exterior color (GBA) Black, (EFY) body-color exterior accents or (CFV/CFZ) ground effects`
     - Section: `sec_exte_001`
     - Price: `$495`
     - Z06 OVS: available in all six Z06 variants.

Risk level: medium. The pass writes workbook source data for active/promoted models and changes generated runtime data. Runtime JavaScript should remain unchanged.

Change type: workbook/data + generated artifacts + focused tests. No runtime UI copy cleanup in this pass.

## Exact Workbook Changes

### `grandSport_exclusive_members`

Update the existing row only:

| group_id | option_id | display_order | active |
| --- | --- | ---: | --- |
| `gs_excl_ground_effects` | `opt_cfv_001` | `30` | `True` |

Do not add new Grand Sport sheets or runtime logic. This keeps T0F/FEY-included CFZ hard-locked against both CFL and CFV through the existing generic include + exclusive-group runtime mechanics.

### `z06_options`

Append one active option row:

| option_id | rpo | price | option_name | description | detail_raw | section_id | selectable | display_order | active | display_behavior |
| --- | --- | ---: | --- | --- | --- | --- | --- | ---: | --- | --- |
| `opt_cbf_001` | `CBF` | `495` | `Body-color painted Rockers and splitter` | `Body-color painted rockers and splitter` | `Not available with exterior color (GBA) Black, (EFY) body-color exterior accents or (CFV/CFZ) ground effects` | `sec_exte_001` | `True` | `25` | `True` | blank |

Display order `25` is proposed because current active Z06 `sec_exte_001` orders are EFR `10`, EFY `15`, EDU `20`, and ZYC `30`. This places CBF after EDU and before ZYC without colliding. If the user wants another order, change only this value before implementation.

Do not add CBF to `z06_excl_exterior_accents`; CBF should coexist with EFR/EDU/ZYC unless one of its explicit blockers is selected.

### `z06_ovs`

Add six availability rows:

| option_id | variant_id | status |
| --- | --- | --- |
| `opt_cbf_001` | `1lz_h07` | `available` |
| `opt_cbf_001` | `2lz_h07` | `available` |
| `opt_cbf_001` | `3lz_h07` | `available` |
| `opt_cbf_001` | `1lz_h67` | `available` |
| `opt_cbf_001` | `2lz_h67` | `available` |
| `opt_cbf_001` | `3lz_h67` | `available` |

### `z06_rule_group_members`

Add CBF to the existing GBA blocker group:

| group_id | target_id | display_order | active |
| --- | --- | ---: | --- |
| `z06_group_gba_excludes_accent_and_roof_choices` | `opt_cbf_001` | `60` | `True` |

Update the parent group disabled reason only if needed to avoid stale text. Minimal acceptable wording:

`GBA black paint blocks CBF, EDU, EFY, ZYC, D84, and D86 accent/roof choices.`

This is not the broader front-end copy cleanup pass.

### `z06_rule_mapping`

Add three direct blocking excludes with `source_id=opt_cbf_001`:

| rule_id | source_id | rule_type | target_id | original_detail_raw | body_style_scope | runtime_action | disabled_reason |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `z06_rule_opt_cbf_001_excludes_opt_cfv_002` | `opt_cbf_001` | `excludes` | `opt_cfv_002` | supplied CBF raw detail | blank | blank | blank |
| `z06_rule_opt_cbf_001_excludes_opt_cfz_001` | `opt_cbf_001` | `excludes` | `opt_cfz_001` | supplied CBF raw detail | blank | blank | blank |
| `z06_rule_opt_cbf_001_excludes_opt_efy_001` | `opt_cbf_001` | `excludes` | `opt_efy_001` | supplied CBF raw detail | blank | blank | blank |

Add five reverse replacement excludes from the Z06 aero/package choices that include or force CFZ/CFV ground effects:

| rule_id | source_id | rule_type | target_id | original_detail_raw | body_style_scope | runtime_action | disabled_reason |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `z06_rule_opt_t0f_001_replaces_opt_cbf_001` | `opt_t0f_001` | `excludes` | `opt_cbf_001` | supplied CBF raw detail | blank | `replace` | `T0F includes CFZ ground effects, which replaces CBF.` |
| `z06_rule_opt_t0g_001_replaces_opt_cbf_001` | `opt_t0g_001` | `excludes` | `opt_cbf_001` | supplied CBF raw detail | blank | `replace` | `T0G includes CFV ground effects, which replaces CBF.` |
| `z06_rule_opt_z07_001_replaces_opt_cbf_001` | `opt_z07_001` | `excludes` | `opt_cbf_001` | supplied CBF raw detail | blank | `replace` | `Z07 requires the CFZ or CFV ground-effects aero path, which replaces CBF.` |
| `z06_rule_opt_pdd_001_replaces_opt_cbf_001` | `opt_pdd_001` | `excludes` | `opt_cbf_001` | supplied CBF raw detail | blank | `replace` | `PDD includes CFZ ground effects, which replaces CBF.` |
| `z06_rule_opt_pdf_001_replaces_opt_cbf_001` | `opt_pdf_001` | `excludes` | `opt_cbf_001` | supplied CBF raw detail | blank | `replace` | `PDF includes CFV ground effects, which replaces CBF.` |

Use direct excludes here because the user explicitly specified direct `z06_rule_mapping` rows. Do not create a new CBF-specific rule group in this pass.

Important runtime intent: CBF must not block T0F, T0G, Z07, PDD, or PDF. If CBF is selected first and the customer later selects one of those aero/package choices, the package/aero choice wins and CBF is deselected through the existing generic `runtime_action=replace` path. Manual CFV/CFZ choices remain blocked while CBF is selected.

## Generated Artifacts Expected to Change

- `form-output/runtime/grand-sport-runtime-contract.json`
- `form-output/runtime/z06-runtime-contract.json`
- `form-app/data.js`

Generated artifacts are outputs only. Do not hand-edit them.

## Spec Closure Expected to Change

- `.hermes/plans/z06-cbf-grand-sport-cfv-exclusive-group-spec.md`
  - After implementation, update status from spec-only to completed with completion date, changed workbook sheets/artifacts/tests, gate results, residual risks, and deferred follow-up.

## Tests Expected to Change

- `tests/grand-sport-draft-data.test.mjs`
  - Expect `gs_excl_ground_effects.option_ids` to include `opt_cfv_001`.
- `tests/multi-model-runtime-switching.test.mjs`
  - Expect Grand Sport T0F/FEY-included CFZ to lock CFV as well as CFL.
  - Update expected Grand Sport group metadata if asserted there.
- `tests/z06-form-data-draft.test.mjs`
  - Assert CBF emits in `sec_exte_001`, price `495`, selectable/available across all six variants.
  - Assert CBF is a target of `z06_group_gba_excludes_accent_and_roof_choices`.
  - Assert CBF direct blocking excludes CFV, CFZ, and EFY.
  - Assert T0F, T0G, Z07, PDD, and PDF carry replace excludes targeting CBF, not normal blocking excludes.
- `tests/z06-runtime-rule-corrections.test.mjs` or `tests/z06-performance-package-interactions.test.mjs`
  - Add focused runtime assertions that CBF is selectable normally, disabled/removed with GBA, conflicts with EFY, CFV, and CFZ, and does not block EDU by group membership.
  - Add focused runtime assertions that selecting T0F, T0G, Z07, PDD, or PDF while CBF is selected removes CBF and still allows the expected CFZ/CFV include/default path to apply.

No test should justify preserving an unnecessary group. Tests should assert the intended workbook-owned behavior and runtime result. Do not change workbook behavior merely to satisfy a broad or stale test; if a non-targeted test fails, first prove that the test is a current validation gate for this workbook/runtime contract before changing this spec or implementation.

## Constraints and Non-goals

- No new workbook sheets.
- No runtime RPO/model hardcodes.
- No new dependencies.
- No dealer submission endpoint, payload, or Turnstile changes.
- Do not change front-end copy/tone in this pass except the minimal stale GBA group reason update if needed.
- Do not add CBF to `z06_excl_exterior_accents`.
- Do not make CBF block T0F, T0G, Z07, PDD, or PDF; those aero/package choices should replace/deselect CBF through workbook-authored replace rules.
- Do not start the broader exclusive-group consolidation/layout pass here.
- Do not reorganize Grand Sport aero packages, stripe/Jake sections, transport graphics, or accessories layout in this pass.
- Preserve current generated-data workflow: workbook source rows -> `scripts/generate_form.py --model <model>` -> `scripts/generate_registry.py`.

## Broader Deferred Follow-up

Separate report/spec pass recommended after this narrow fix:

- Audit Grand Sport aero package groups, including whether `5ZV` belongs in a workbook-owned aero peer/blocker relationship.
- Audit Grand Sport stripe/Jake graphics section ownership; consider separate sections for Jake Hood graphics instead of mixing with full-length stripes where source semantics support it.
- Audit accessories sections for layout/grouping improvements.
- Audit front-end wording for exclusive/required/related option labels and disabled/auto-added copy.

That pass should be report-first because it may change section ownership, copy, grouping, and runtime layout behavior.

## Validation Plan

Preflight:

```sh
cd /Users/seandm/Projects/27vette
test ! -e '~$stingray_master.xlsx'
.venv/bin/python scripts/validate_workbook_package.py stingray_master.xlsx
```

After approved workbook write, verify on disk with `openpyxl`:

- `grandSport_exclusive_members.gs_excl_ground_effects / opt_cfv_001 active=True`
- `z06_options.opt_cbf_001` row exists with price `495`, section `sec_exte_001`, active/selectable true.
- Six `z06_ovs` rows exist for `opt_cbf_001`.
- `z06_rule_group_members` includes `z06_group_gba_excludes_accent_and_roof_choices / opt_cbf_001`.
- Three `z06_rule_mapping` blocking excludes exist from `opt_cbf_001` to `opt_cfv_002`, `opt_cfz_001`, and `opt_efy_001`.
- Five `z06_rule_mapping` replace excludes exist from `opt_t0f_001`, `opt_t0g_001`, `opt_z07_001`, `opt_pdd_001`, and `opt_pdf_001` to `opt_cbf_001`.

Regenerate:

```sh
.venv/bin/python scripts/generate_form.py --model grand_sport
.venv/bin/python scripts/generate_form.py --model z06
.venv/bin/python scripts/generate_registry.py
```

Targeted gates:

```sh
.venv/bin/python scripts/validate_workbook_schema.py stingray_master.xlsx
node --test tests/grand-sport-contract-preview.test.mjs
node --test tests/grand-sport-draft-data.test.mjs
node --test tests/z06-contract-preview.test.mjs
node --test tests/z06-form-data-draft.test.mjs
node --test tests/z06-runtime-rule-corrections.test.mjs
node --test tests/z06-performance-package-interactions.test.mjs
node --test tests/multi-model-runtime-switching.test.mjs
```

Manual verification pending after gates:

- Browser smoke Grand Sport: select FEY/T0F and confirm CFZ is auto-added/locked and both CFL and CFV cannot suppress it while source remains active.
- Browser smoke Z06: CBF normal availability, GBA disables/removes CBF, EFY/CFV/CFZ conflicts, EDU remains compatible, and T0F/T0G/Z07/PDD/PDF remain selectable and replace CBF when chosen.

## Approval

Approve this narrow workbook/data pass to implement:

1. Activate Grand Sport CFV in `gs_excl_ground_effects`.
2. Add Z06 CBF option/OVS/rules exactly as specified above.
3. Regenerate Grand Sport + Z06 + registry artifacts and update focused tests.

Broader exclusive-group consolidation, section/layout grouping, and front-end copy cleanup remain deferred.
