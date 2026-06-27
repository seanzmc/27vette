# Z Source Hygiene Cleanup Pass B Spec — Z06 SHT Rule Text

## Diagnosis

Cleanup Pass A removed Grand Sport wording from active Z exclusive-group source notes. The remaining scoped Grand Sport contamination from the Z source hygiene audit is in `stingray_master.xlsx` sheet `z06_rule_mapping`, rows currently 75-90.

Evidence inspected:

- Repo branch/status:
  - branch: `z06-zr1-migration`
  - `stingray_master.xlsx` is already modified from Cleanup Pass A
  - Cleanup specs and safe-save backup directory are untracked
  - Excel lock file `~$stingray_master.xlsx` is absent
- Workbook sheet `z06_rule_mapping` headers:
  - `rule_id`, `source_id`, `rule_type`, `target_id`, `target_type`, `original_detail_raw`, `review_flag`, `source_type`, `target_selection_mode`, `source_selection_mode`, `target_section`, `source_section`, `generation_action`, `body_style_scope`, `runtime_action`, `disabled_reason`, `normalization_status`, `normalization_reason`, `replacement_group_id`, `replacement_rule_id`
- Workbook sheet `z06_options` source row for `opt_sht_001` / RPO `SHT`:
  - option name: `LPO, Jake hood graphic with Tech Bronze accent, Genuine Corvette Accessory`
  - source detail: `Not available with PDA, SNE or RPO stripes (DPB, DPC, DPG, DPL, DPT, DSY, DSZ, DT0, DTB, DTH, DUB, DUE, DUK, DUW, DZU, DZV, DZX). Included with (PCZ) Tech Bronze Accent Package, LPO.`
- Current 16 `z06_rule_mapping` rows all have:
  - `source_id=opt_sht_001`
  - `rule_type=excludes`
  - `target_type=option`
  - `source_section=sec_stri_001`
  - `target_section=sec_stri_001`
  - `normalization_status=active`
  - `original_detail_raw=1. Not available with RPO stripes (DPB, DPC, DPG, DPL, DPT, DSY, DSZ, DT0, DTB, DTH, DUB, DUE, DUK, DUW, DZU, DZV, DZX) or (Z15) Grand Sport Heritage Graphics.`
- Current target rows are stripe options:
  - `opt_dpb_001` DPB
  - `opt_dpc_001` DPC
  - `opt_dpg_001` DPG
  - `opt_dpl_001` DPL
  - `opt_dpt_001` DPT
  - `opt_dsy_001` DSY
  - `opt_dsz_001` DSZ
  - `opt_dt0_001` DT0
  - `opt_dth_001` DTH
  - `opt_dub_001` DUB
  - `opt_due_001` DUE
  - `opt_duk_001` DUK
  - `opt_duw_001` DUW
  - `opt_dzu_001` DZU
  - `opt_dzv_001` DZV
  - `opt_dzx_001` DZX

Root cause:

The `z06_rule_mapping.original_detail_raw` cells for the SHT stripe-exclusion rules retain copied Grand Sport-specific source prose mentioning `(Z15) Grand Sport Heritage Graphics`. The rule semantics themselves appear aligned with the Z06 `SHT` option's own source detail for stripe incompatibility, but the provenance/rationale text is wrong for Z06 runtime readiness.

Risk level: medium-low if limited to text cleanup in `original_detail_raw`; medium if expanding to new rule semantics. This pass should be data-only/workbook-only and should not change generated/runtime artifacts.

Change type: workbook source-data cleanup only.

## Exact Files / Sheets / Cells to Change

File:

- `/Users/seandm/Projects/27vette/stingray_master.xlsx`

Sheet:

- `z06_rule_mapping`

Rows to change, located by `rule_id` rather than row number:

- `z06_rule_opt_sht_001_excludes_opt_dpb_001`
- `z06_rule_opt_sht_001_excludes_opt_dpc_001`
- `z06_rule_opt_sht_001_excludes_opt_dpg_001`
- `z06_rule_opt_sht_001_excludes_opt_dpl_001`
- `z06_rule_opt_sht_001_excludes_opt_dpt_001`
- `z06_rule_opt_sht_001_excludes_opt_dsy_001`
- `z06_rule_opt_sht_001_excludes_opt_dsz_001`
- `z06_rule_opt_sht_001_excludes_opt_dt0_001`
- `z06_rule_opt_sht_001_excludes_opt_dth_001`
- `z06_rule_opt_sht_001_excludes_opt_dub_001`
- `z06_rule_opt_sht_001_excludes_opt_due_001`
- `z06_rule_opt_sht_001_excludes_opt_duk_001`
- `z06_rule_opt_sht_001_excludes_opt_duw_001`
- `z06_rule_opt_sht_001_excludes_opt_dzu_001`
- `z06_rule_opt_sht_001_excludes_opt_dzv_001`
- `z06_rule_opt_sht_001_excludes_opt_dzx_001`

Column to change:

- `original_detail_raw`

Old exact text expected in all 16 cells:

```text
1. Not available with RPO stripes (DPB, DPC, DPG, DPL, DPT, DSY, DSZ, DT0, DTB, DTH, DUB, DUE, DUK, DUW, DZU, DZV, DZX) or (Z15) Grand Sport Heritage Graphics.
```

New text:

```text
Not available with PDA, SNE or RPO stripes (DPB, DPC, DPG, DPL, DPT, DSY, DSZ, DT0, DTB, DTH, DUB, DUE, DUK, DUW, DZU, DZV, DZX). Included with (PCZ) Tech Bronze Accent Package, LPO.
```

Rationale for using the full `SHT` source detail:

- It removes the invalid Grand Sport/Z15 phrase.
- It matches the Z06 `z06_options.detail_raw` source row for `opt_sht_001` exactly.
- It preserves the current active stripe-exclusion rule semantics without inventing new logic in this cleanup pass.

## Constraints Repeated Back

- Visual preservation: no runtime UI or styling changes.
- No refactor.
- No new dependencies.
- Workbook is source of truth for product/business source data.
- Do not hand-edit generated `form_*` sheets, `form-output/`, or `form-app/data.js`.
- Do not promote Z06, ZR1, or ZR1X to runtime.
- Do not change live Stingray or Grand Sport behavior.
- Do not change dealer submission endpoint, payload shape, or Turnstile behavior.
- Do not add hardcoded Z06/SHT runtime or generator exceptions.
- Use `save_workbook_safely()` and verify saved workbook cells on disk.
- Check `~$stingray_master.xlsx` before writing.
- Locate rows by `rule_id` and verify old text exactly before editing.

## Non-goals

- Do not add missing `PDA` or `SNE` exclusion rules in this pass. The replacement text reflects the full source detail, but this pass only cleans the 16 already-existing stripe-exclusion rule rationale cells. Adding PDA/SNE rules is a separate business-rule completeness pass.
- Do not change `rule_id`, `source_id`, `rule_type`, `target_id`, `target_type`, `review_flag`, sections, normalization status, replacement fields, or active/selectable option rows.
- Do not touch `zr1_rule_mapping` or `zr1x_rule_mapping`; the audit found no Grand Sport mentions there.
- Do not clean internal provenance references in `future_model_source_review` / `future_model_option_review`.
- Do not normalize safe raw GM multi-model accessory copy.
- Do not regenerate runtime artifacts.

## Cleanup Pass C Context Kept Explicit

Pass C should remain separate and should focus on generated/runtime-boundary readiness, not source-text cleanup. Candidate Pass C scope:

- Add or verify guards ensuring future-model review/provenance fields such as `copy_from_model_key=grand_sport`, `suggested_copy_from=grand_sport:*`, and other staging lineage do not leak into `form-app/data.js` or any runtime JSON if Z06/ZR1/ZR1X are later promoted.
- Inspect generation contracts before any Z runtime promotion.
- Keep Pass C read-only/spec-first unless explicitly approved to add tests or generator guards.

Pass C should not be mixed into Pass B because Pass B writes only workbook source text.

## Risks

- The new text includes PDA/SNE because that is the exact Z06 SHT source detail. However, existing row semantics only target stripe options; the text will mention incompatibilities not represented by these 16 rows. That mismatch already exists at the source-detail level and should be handled by a later completeness pass, not hidden by keeping stale Grand Sport wording.
- If the workbook changed after inspection, exact old-text verification must stop the write.
- `stingray_master.xlsx` is already modified from Cleanup Pass A, so handoff must report cumulative workbook state carefully.

## Validation Plan

Before write:

```sh
git branch --show-current
git status --short --branch
test ! -e '~$stingray_master.xlsx'
```

Write:

- Use `.venv/bin/python` with `openpyxl`.
- Import and call `save_workbook_safely()` from `scripts/corvette_form_generator/workbook.py`.
- Verify all 16 target rows exist by `rule_id`.
- Verify each `original_detail_raw` cell equals the old exact text before changing.
- Save safely.

After write:

- Reopen `stingray_master.xlsx` from disk and verify all 16 target rows have the new exact text.
- Re-scan `z06_rule_mapping` for `Grand Sport`; expected count for this scoped sheet should be `0` unless unrelated text appears outside the inspected SHT rows.
- Run workbook validators:

```sh
.venv/bin/python scripts/validate_workbook_package.py stingray_master.xlsx
.venv/bin/python scripts/validate_workbook_schema.py stingray_master.xlsx
```

Diff review:

- Compare current workbook to the safe-save backup for `z06_rule_mapping` scoped cell diffs; expected 16 `original_detail_raw` cell changes only.

Tests/generators:

- Do not run generators or runtime tests for this pass unless scope expands. This is inactive future-model workbook source-text cleanup only.

## Approval Gate

Implementation is blocked until the user approves this spec. After approval, run exactly this Pass B workbook-safe text cleanup and report handoff with changed/unchanged surfaces, gate results, backup path, and Pass C context still pending.
