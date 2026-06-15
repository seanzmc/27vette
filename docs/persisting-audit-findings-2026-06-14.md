# Persisting Audit Findings — 2026-06-14

Sources reviewed:

- `docs/audit-cleanup-overview.md`
- `docs/workbook-consistency-review-2026-06-11.md`
- `docs/interior-pipeline-assessment.md`

Scope: read-only audit of the current codebase and `stingray_master.xlsx` to identify which findings or follow-ups from those three planning/audit files still persist. This file is an action-plan handoff only; it does not approve workbook writes or runtime behavior changes.

Workspace evidence:

- Branch: `generator-simplification-pass1`
- Excel lock: not present during audit
- Workbook schema baseline remains valid (`scripts/validate_workbook_schema.py`)
- Generated Z06 trim cards were checked in `form-app/data.js`
- Workbook source checks were run with `openpyxl`

---

## Summary

Resolved or no longer current:

- Audit-only workbook sheets `option_audit_groups`, `option_audit_group_members`, and `rule_review_groups` are absent from `stingray_master.xlsx`.
- Obvious stale one-pass writer names from Pass B are absent from `scripts/`.
- `rule_mapping`, `grandSport_rule_mapping`, and `z06_rule_mapping` no longer carry omitted/dead-end lifecycle rows as protected infrastructure. Current counts: `rule_mapping` 150 active rows, `grandSport_rule_mapping` 122 active + 1 preserved runtime exclude, `z06_rule_mapping` 55 active rows.
- Z06 display-order cell typing from S-1/S-2 is fixed: `z06_options.display_order` is 249 integers; `z06_exclusive_members.display_order` is 41 integers.
- `order_summary_sections` and `step_order_summary_map` now have rows for Stingray, Grand Sport, and Z06: 11 summary sections and 13 step-map rows per promoted model.
- `order_summary_sections.active` and `step_order_summary_map.active` are now Excel booleans.
- Grand Sport EYT description is no longer truncated: `grandSport_options.opt_eyt_001.description` ends with `GS badge on rear quarter`.
- The Z06 3LZ R6X AH2 runtime overcharge from `interior-pipeline-assessment.md` is fixed in `form-app/app.js`: `adjustedInteriorPrice()` and `lineItemsFromInterior()` use `selectedSeatResolvedPrice()`, and `tests/z06-interior-accessory-cleanup.test.mjs` has a focused `3LZ_R6X_AH2_HUU` regression test.
- Interior generation has moved materially beyond the old assessment: `production.py` imports and calls `build_model_interiors()`, `model_interior_scope` now has workbook-owned grouping columns and Stingray rows, and `interiors.py` raises if active `model_interior_scope` grouping metadata is missing.

Still persisting and needing an action plan:

1. Runtime/order-summary fallback constants remain after Pass E option (a).
2. Optional audit/report tooling remains as opt-in historical tooling.
3. Z06 trim cards still lack tooltip copy.
4. Z06 WKS indoor car cover is still outside the indoor-cover exclusive group and still has a duplicate display order with RWJ.
5. Stingray rear script badges still use pairwise excludes instead of an exclusive group.
6. Display-order duplicate buckets still exist in eight option-sheet section/order groups.
7. Cross-model relative order drift still exists for several shared sections and one Grand Sport exclusive-member ordering surface.
8. Cross-model customer copy drift remains, including trailing-period drift pinned by tests.
9. Several section/copy decisions remain product-review items.
10. Z06 option-id suffix drift remains for U2K/U5G/UE1/VV4/CFV and no-RPO Z06 row IDs remain sparse.
11. Stingray exclusive-group ID prefix/style drift remains cosmetic.
12. Interior CSV/config remnants remain even though active interior grouping now comes from workbook metadata.

---

## Remaining issues and action plans

### 1. Runtime/order-summary fallback constants remain after Pass E option (a)

Evidence:

- `form-app/app.js` still has fallback behavior in `orderSummarySections()` and `orderSummaryStepMap()`:
  - `data.orderSummary?.sections` else `orderSectionDefinitions`
  - `data.orderSummary?.stepMap || Object.fromEntries(stepOrderSectionKeys)`
- `scripts/corvette_form_generator/model_configs.py` still carries fallback `STEP_ORDER`, `STEP_LABELS`, and `CONTEXT_SECTIONS` constants used as base config/fallback inputs.
- `README.md` still says promoted runtime-contract models may omit `orderSummary`, although the current workbook has rows for Stingray, Grand Sport, and Z06.

Status: persists by design from Pass E option (a). It is now the next fallback-retirement candidate, not an audit-scaffolding cleanup item.

Action plan:

1. Write a spec for a fallback-retirement pass, scoped only to promoted-model runtime metadata fallback behavior.
2. Add tests proving Stingray, Grand Sport, and Z06 all have generated `orderSummary.sections` and `orderSummary.stepMap` in `form-app/data.js` / runtime contracts.
3. Decide fallback semantics explicitly:
   - fail generation if promoted models lack workbook-owned rows, or
   - keep fallback only for non-promoted/future models and document that boundary.
4. Remove or narrow `orderSectionDefinitions` / `stepOrderSectionKeys` fallback usage only after the generated-data tests are green.
5. Update `README.md` / `AGENTS.md` text that still implies promoted models may omit `orderSummary` if that is no longer true.
6. Run runtime/multi-model gates: `tests/stingray-form-regression.test.mjs`, `tests/multi-model-runtime-switching.test.mjs`, plus the model draft/contract tests if generators are touched.

---

### 2. Optional audit/report tooling remains as opt-in historical tooling

Evidence:

- `scripts/build_rule_sources.py` remains in `scripts/`.
- `README.md` and `AGENTS.md` classify it as opt-in audit/report tooling, not default readiness.
- Optional tests remain: `tests/grand-sport-rule-audit.test.mjs` and `tests/audit-parser-metadata-loaders.test.mjs`.

Status: persists intentionally. It is no longer a default-gate blocker.

Action plan:

1. Keep as-is unless the user wants to retire optional historical audit tooling entirely.
2. If retiring, first prove no current workflow still needs `build_rule_sources.py` for rule provenance investigations.
3. Delete or quarantine the script and optional tests together, not piecemeal.
4. Update README/AGENTS optional audit blocks in the same pass.
5. Run default gates plus any replacement provenance checks selected in the spec.

---

### 3. Z06 trim cards still lack tooltip copy

Evidence:

- `context_choice_copy` currently has only wildcard `trim_level` rows for `1LT`, `2LT`, and `3LT`.
- Generated `form-app/data.js` has Z06 trim context choices for `1LZ`, `2LZ`, `3LZ` with `info_tooltip=false`; Stingray and Grand Sport trim choices have tooltips.

Status: persists from C-5.

Action plan:

1. Add workbook-owned `context_choice_copy` rows for Z06 trims (`1LZ`, `2LZ`, `3LZ`) with Z06-appropriate tooltip copy.
2. Prefer model-scoped rows (`model_key=z06`) unless the same LZ copy should apply to future ZR1/ZR1X.
3. Regenerate Z06 and Stingray registry data as required by the current generator path.
4. Add/extend a focused test in `tests/z06-contract-preview.test.mjs` or `tests/multi-model-runtime-switching.test.mjs` asserting Z06 trim `info_tooltip` presence.
5. Run `scripts/validate_workbook_schema.py`, `scripts/generate_form.py --model z06`, `scripts/generate_form.py --model stingray`, and targeted runtime/model tests.

---

### 4. Z06 WKS indoor car cover is still outside the indoor-cover exclusive group

Evidence:

- `z06_options.opt_wks_001` exists in `sec_lpoe_001`.
- `z06_exclusive_members` group `z06_excl_indoor_car_covers` contains `opt_rwh_001` and `opt_wkr_001`, but not `opt_wks_001`.
- `z06_options.sec_lpoe_001` still has duplicate `display_order=72` for `RWJ` (`opt_rwj_001`) and `WKS` (`opt_wks_001`).

Status: persists from S-7 and D-1.

Action plan:

1. Confirm product intent: whether WKS should be mutually exclusive with RWH/WKR on Z06.
2. If yes, add `opt_wks_001` to `z06_exclusive_members.z06_excl_indoor_car_covers` with a deterministic `display_order`.
3. Resolve the WKS/RWJ duplicate display order in `z06_options.sec_lpoe_001` in the same workbook pass.
4. Add a Z06 draft/runtime test proving WKS cannot be selected together with other indoor covers and that section ordering is deterministic.
5. Regenerate Z06 artifacts and the live registry if promoted app data changes.
6. Run Z06 draft/runtime gates and a browser smoke of the LPO Exterior section.

---

### 5. Stingray rear script badges still use pairwise excludes instead of an exclusive group

Evidence:

- `rule_mapping` still has 6 active pairwise `excludes` rows among RIK/RIN/SL8.
- No Stingray `exclusive_groups` + `exclusive_group_members` group contains all three rear-script badge options.
- Grand Sport and Z06 have equivalent model-scoped exclusive groups.

Status: persists from S-3.

Action plan:

1. Write a workbook-source spec for migrating Stingray rear-script badge behavior to an exclusive group.
2. Add a RED runtime test proving current Stingray interaction blocks instead of radio-replacing, if that is still observable.
3. Add a Stingray exclusive group and members for RIK/RIN/SL8.
4. Delete or retire the six pairwise excludes only if generated contract comparison proves the exclusive group owns the behavior; do not keep redundant skipped rows long-term.
5. Regenerate Stingray and compare contracts; if behavior intentionally changes from disabled-blocking to radio replacement, cover it in runtime tests.
6. Run `tests/stingray-form-regression.test.mjs` and `tests/multi-model-runtime-switching.test.mjs`.

---

### 6. Display-order duplicate buckets still exist

Evidence: current workbook still has 8 option-sheet duplicate `(section_id, display_order)` buckets:

- `stingray_options.sec_cust_001`, order `10`: BV4/R8C
- `stingray_options.sec_lpoe_001`, order `30`: PCX/VK3
- `grandSport_options.sec_engi_001`, order `10`: D3V/BC7
- `z06_options.sec_incl_001`, order `10`: FE6/DRG
- `z06_options.sec_incl_001`, order `20`: FE7/TR7
- `z06_options.sec_lpoe_001`, order `72`: RWJ/WKS
- `z06_options.sec_stan_001`, order `120`: no-RPO row `opt_329`/G0K
- `z06_options.sec_stan_001`, order `20`: U80/WUB

Status: persists from D-1, D-2, D-3.

Action plan:

1. Split into two passes:
   - selectable/customer-facing duplicates first (`stingray_options`, `grandSport_options`, `z06_options.sec_lpoe_001`),
   - standard/included display-only duplicates second if still worth normalizing.
2. For each bucket, decide canonical order from current UI/product intent rather than just incrementing arbitrary numbers.
3. Add a validator/test for duplicate display order within `(sheet, section_id)` after the workbook is clean; do not add a failing broad validator before deciding how to handle standard-equipment sections.
4. Regenerate affected artifacts and review diff for ordering-only changes.
5. Browser-smoke affected sections where selectable order changes.

---

### 7. Cross-model relative order and exclusive-member order drift remains

Evidence:

- GS/Z06 wheels `SOM`/`ROX` relative order still differs:
  - Grand Sport: `SOM=43`, `ROX=44`
  - Z06: `ROX=23`, `SOM=30`
- Roof `CF8`/`CM9` order still differs:
  - Stingray: `CF8=13`, `CM9=20`
  - Grand Sport/Z06: `CM9=20`, `CF8=50`
- Grand Sport LS6 engine-cover exclusive-member order still disagrees with option-sheet order:
  - option sheet: BC7=10, BCP=20, BCS=30, BC4=40
  - exclusive members: BC7=10, BC4=30, BCP=50, BCS=70

Status: persists from D-4, D-5, D-6, D-8.

Action plan:

1. Decide canonical section order per section, preferring the later reviewed GS/Z06 order only when product/visual intent agrees.
2. Update workbook source display orders and exclusive-member display orders together for any section/group whose UI can read both surfaces.
3. Add parity tests scoped to the specific shared sections instead of broad all-model ordering equality.
4. Regenerate and compare generated contracts for order-only diffs.
5. Browser-smoke the affected option sections.

---

### 8. Cross-model customer copy drift remains

Evidence:

- Across 162 shared option IDs, Stingray still deviates from the GS/Z06 majority on 51 option names and 86 descriptions.
- 34 shared descriptions still differ only by trailing-period style.
- `tests/workbook-visual-copy-standardization.test.mjs` still loads only `stingray_options` and `grandSport_options` at the top-level sheet map, and still pins period/no-period drift for selected accessory descriptions.
- Examples still present: AJ7, AP9, AUP, BAZ, BV4, CF8, CJ2, CM9.

Status: persists from C-2 and C-4.

Action plan:

1. Treat this as a dedicated workbook copy-convergence pass, not a drive-by cleanup.
2. Build a generated CSV/Markdown review of all shared-option name/description mismatches, with an allowlist for intentional model differences.
3. Keep §6 human-review items out of the automatic majority-copy patch until product decisions are made.
4. Normalize names/descriptions in matched pairs so qualifiers move consistently between name and description.
5. Decide punctuation style and update `tests/workbook-visual-copy-standardization.test.mjs` in the same pass.
6. Extend copy tests to include `z06_options` and enforce pairwise/shared option copy parity with an intentional-difference allowlist.
7. Regenerate and run visual-copy, model draft, and runtime gates as needed.

---

### 9. Product-review section/copy decisions still persist

Evidence: the following workbook differences are still present:

- `opt_uv6_001` HUD: Stingray/Grand Sport `sec_2lte_001`; Z06 `sec_1lte_001`.
- `opt_sc7_001` roof pouch: Stingray `sec_lpoi_001`; Grand Sport/Z06 `sec_lpoe_001`.
- `opt_drz_001` copy: Stingray name/description are swapped relative to GS/Z06.
- `opt_efr_001`/`opt_edu_001` accent copy: Stingray uses short copy; GS/Z06 use longer CFV/CFZ-conditional copy.
- `opt_nga_001` copy: Z06 still says only `Standard`; GS says `Standard. Corner Exit`.
- `sec_seat_002` seat-row ordering/multiplicity remains a presentation decision.

Status: persists from R-1 through R-6.

Action plan:

1. Produce a product-decision table with one row per item, current model text/section, proposed canonical rule, and order-guide evidence needed.
2. Do not majority-overwrite these in the copy-convergence pass.
3. After decisions, make one workbook-source patch per category:
   - section placement decisions,
   - copy decisions,
   - seat presentation ordering.
4. Add targeted tests only for the decisions that should stay durable across future imports.
5. Regenerate affected model artifacts and inspect customer-facing UI/exports.

---

### 10. Z06 option-id suffix and no-RPO ID drift remains

Evidence:

- Z06 still uses `_002` option IDs where Stingray/Grand Sport use `_001` for U2K, U5G, UE1, and VV4.
- CFV still differs across GS/Z06 (`grandSport_options.opt_cfv_001`, `z06_options.opt_cfv_002`), with Stingray not carrying the same option.
- Z06 still has sparse ingest-era no-RPO option IDs such as `opt_085`/`opt_329` rather than the compact Stingray/GS no-RPO sequence.

Status: persists from S-4 and S-5. Mostly tooling/cosmetic unless cross-model joins depend on stable `option_id`.

Action plan:

1. Decide whether cross-model tooling should treat `option_id` as a strict cross-model key or continue to fall back to RPO for known drift cases.
2. If strict keys are desired, write a reference-integrity migration spec for Z06 option IDs.
3. Update all dependent sheets together: `z06_options`, `z06_ovs`, `z06_rule_mapping`, groups/members, price rules, variant overrides, assets if applicable.
4. Add a schema/reference test for renamed IDs before the write pass.
5. Regenerate Z06 and live registry artifacts; run Z06 and multi-model gates.
6. If strict keys are not worth the touch surface, document RPO fallback as the audit/tooling convention and leave workbook IDs untouched.

---

### 11. Stingray exclusive-group ID prefix/style drift remains cosmetic

Evidence:

- Stingray `exclusive_groups.group_id` values still mix `grp_*` and `excl_*` without model prefix.
- Grand Sport and Z06 use model-scoped prefixes such as `gs_excl_*` and `z06_excl_*`.

Status: persists from S-6. No customer-facing behavior impact found in this audit.

Action plan:

1. Do not prioritize unless group IDs become a tooling or editor UX problem.
2. If normalizing, treat as a reference migration: update group IDs and every member/reference together.
3. Add a schema/reference-integrity test before the migration.
4. Regenerate and compare contracts to prove IDs are internal-only or update tests if emitted group IDs are part of the contract.

---

### 12. Interior CSV/config remnants remain after workbook-owned grouping migration

Evidence:

- `architectureAudit/stingray_interiors_refactor.csv` and `architectureAudit/grand_sport_interiors_refactor.csv` still exist.
- `scripts/corvette_form_generator/model_configs.py` still assigns `interior_reference_path=ROOT / "architectureAudit" / f"{model_key}_interiors_refactor.csv"`.
- `scripts/corvette_form_generator/model_config.py` still carries `interior_reference_path` in `ModelConfig`.
- Current active builder no longer uses those CSV fallbacks: `interiors.py` builds from `model_interior_scope`, raises when active scope rows are missing, and no longer contains the old `INTERIOR_COMPONENT_LABELS` / `broad_interior_color_family` heuristic surfaces.

Status: the original interior runtime defect and workbook-owned grouping gap are fixed, but stale CSV/config surfaces remain.

Action plan:

1. Run a consumer audit for `interior_reference_path` and the two CSVs.
2. If no active code path consumes them, remove `interior_reference_path` from `ModelConfig` and `base_model_config()`.
3. Delete or archive the two CSVs only after proving `model_interior_scope` contains complete grouping metadata for Stingray and Grand Sport and generated contracts remain stable.
4. Add/keep tests that fail if active interiors lack workbook-owned grouping metadata.
5. Run Stingray, Grand Sport, Z06 generator and model/runtime gates after deletion.

---

## Recommended next passes

1. **Z06 tooltip + WKS/display-order micro-pass**: small workbook-source pass with visible customer impact and clear tests.
2. **Display-order uniqueness pass**: clean current duplicate buckets, then add a durable validator/test.
3. **Fallback-removal pass**: remove or narrow runtime/order-summary fallback constants now that promoted models have workbook-owned rows.
4. **Copy-convergence/product-decision pass**: larger workbook copy pass with explicit allowlist and product review.
5. **Interior stale-surface cleanup**: remove unused CSV/config remnants after consumer audit.

---

## Gates run for this audit

- `.venv/bin/python /tmp/27vette_persistence_audit.py` — read-only workbook/code audit, output saved outside repo.
- `node` probe against `form-app/data.js` — confirmed Z06 trim choices still lack `info_tooltip` while Stingray/Grand Sport have it.
- `.venv/bin/python scripts/validate_workbook_schema.py stingray_master.xlsx` — valid, 0 errors/warnings.

No generators were run and no workbook or generated artifacts were modified for this report.
