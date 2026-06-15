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
- Z06 trim-card tooltip copy is now workbook-owned and emitted in `form-app/data.js`; `tests/z06-form-data-draft.test.mjs` asserts the 1LZ/2LZ/3LZ tooltip copy.
- Z06 WKS is now a member of `z06_excl_indoor_car_covers`, ordered after RWH/WKR, and `z06_options.opt_wks_001` now has `display_order=73`; `tests/z06-form-data-draft.test.mjs` asserts the group membership.
- Active promoted-model option sheets no longer have duplicate active `(section_id, display_order)` buckets. The only current duplicate buckets found by the refreshed audit are future-model scaffold rows in `zr1_options.sec_stan_001` and `zr1x_options.sec_stan_001` for U80/WUB at order `20`.

Still persisting and needing an action plan:

1. Runtime/order-summary fallback constants remain after Pass E option (a).
2. Optional audit/report tooling remains as opt-in historical tooling.
3. Stingray rear script badges still use pairwise excludes instead of an exclusive group.
4. Cross-model relative order drift still exists for wheels/roof and one Grand Sport exclusive-member ordering surface.
5. Cross-model customer copy drift remains, including trailing-period drift pinned by tests.
6. Several section/copy decisions remain product-review items.
7. Z06 option-id suffix drift remains for U2K/U5G/UE1/VV4/CFV and no-RPO Z06 row IDs remain sparse.
8. Stingray exclusive-group ID prefix/style drift remains cosmetic.
9. Interior CSV/config remnants remain even though active interior grouping now comes from workbook metadata.

---

## Remaining issues and action plans

### 1. Runtime/order-summary fallback constants remain after Pass E option (a)

Evidence:

- `form-app/app.js` still has fallback behavior in `orderSummarySections()` and `orderSummaryStepMap()`:
  - `data.orderSummary?.sections` else `orderSectionDefinitions`
  - `data.orderSummary?.stepMap || Object.fromEntries(stepOrderSectionKeys)`
- `scripts/corvette_form_generator/model_configs.py` still carries fallback `STEP_ORDER`, `STEP_LABELS`, and `CONTEXT_SECTIONS` constants used as base config/fallback inputs.
- `README.md` still says promoted runtime-contract models may omit `orderSummary`, although the current workbook has rows for Stingray, Grand Sport, and Z06.
- `tests/grand-sport-draft-data.test.mjs` and `tests/z06-form-data-draft.test.mjs` now assert 11 generated `orderSummary.sections` rows and 13 `stepMap` entries for Grand Sport and Z06. `form-app/data.js` currently emits the same counts for Stingray, Grand Sport, and Z06.

Status: partly progressed. The promoted-model data gap is closed and covered by tests; the remaining work is code/docs fallback retirement or boundary narrowing.

Action plan:

1. Write a spec for a fallback-retirement pass, scoped only to promoted-model runtime metadata fallback behavior and README/AGENTS wording.
2. Keep the existing Grand Sport/Z06 generated-data tests; add a Stingray-specific assertion only if the runtime test suite does not already prove its generated `orderSummary` contract.
3. Decide fallback semantics explicitly before editing runtime code:
   - fail generation if promoted models lack workbook-owned rows, or
   - keep fallback only for non-promoted/future models and document that boundary.
4. Remove or narrow `orderSectionDefinitions` / `stepOrderSectionKeys` fallback usage only after the boundary is decided.
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

### 3. Z06 trim cards now have tooltip copy — completed

Evidence:

- `context_choice_copy` now has Z06-scoped `trim_level` rows for `1LZ`, `2LZ`, and `3LZ`.
- Generated `form-app/data.js` has Z06 trim context choices for `1LZ`, `2LZ`, and `3LZ` with non-empty `info_tooltip` copy.
- `tests/z06-form-data-draft.test.mjs` includes `Z06 trim context choices use workbook-owned LZ tooltip copy` and asserts the Head-Up Display / comfort / carbon-fiber steering-wheel tooltip text.

Status: completed.

Action plan:

1. No open action for this finding.
2. Future LZ-model tooltip work should reuse `context_choice_copy` and decide explicitly whether copy is model-scoped or shared before adding ZR1/ZR1X rows.

---

### 4. Z06 WKS indoor car cover grouping/display order — completed

Evidence:

- `z06_options.opt_wks_001` exists in `sec_lpoe_001`.
- `z06_exclusive_members` group `z06_excl_indoor_car_covers` now contains `opt_rwh_001`, `opt_wkr_001`, and `opt_wks_001` in deterministic order `10`, `20`, `30`.
- `z06_options.sec_lpoe_001` now orders `RWH=70`, `WKR=71`, `RWJ=72`, and `WKS=73`; the former RWJ/WKS duplicate bucket is gone.
- `tests/z06-form-data-draft.test.mjs` includes `Z06 indoor car cover exclusive group includes WKS`.

Status: completed.

Action plan:

1. No open action for this finding.
2. If another Z06 LPO exterior ordering change lands, keep WKS in the indoor-cover exclusive group and preserve deterministic display-order uniqueness.

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

### 6. Display-order duplicate buckets — completed for promoted option sheets

Evidence: refreshed workbook audit found no active duplicate `(section_id, display_order)` buckets in the promoted option sheets `stingray_options`, `grandSport_options`, or `z06_options`.

- Current remaining duplicate buckets are future-model scaffold rows only:
  - `zr1_options.sec_stan_001`, order `20`: WUB/U80
  - `zr1x_options.sec_stan_001`, order `20`: U80/WUB
- No broad duplicate-order validator was found in `tests/`; current tests assert specific cleaned order surfaces such as Z06 WKS grouping and Stingray/Grand Sport engine appearance order.

Status: completed for promoted runtime models; residual future-model scaffold duplicates remain outside current runtime readiness.

Action plan:

1. Add a durable validator/test for active promoted option sheets now that they are clean. Prefer no standard/included exemption for promoted models.
2. Decide separately whether future-model scaffold sheets (`zr1_options`, `zr1x_options`) should be cleaned now or only during their promotion/readiness pass.
3. If cleaning scaffold rows, order U80/WUB deterministically by product intent or stable RPO/option ID, then extend the validator to include those models.
4. Regenerate affected artifacts only for models whose generated data can change; review diffs as order-only plus timestamps.
5. Browser-smoke affected customer-facing sections only when selectable option order changes.

---

### 7. Cross-model relative order and exclusive-member order drift remains

Evidence:

- GS/Z06 wheels `SOM`/`ROX` relative order still differs:
  - Grand Sport: `SOM=43`, `ROX=44`
  - Z06: `ROX=23`, `SOM=30`
- Roof `CF8`/`CM9` order still differs:
  - Stingray: `CF8=13`, `CM9=20`
  - Grand Sport/Z06: `CM9=20`, `CF8=50`
- Grand Sport engine appearance option-sheet order has been normalized for the LS6 cover rows, but `gs_excl_ls6_engine_covers` exclusive-member order still disagrees with that source order:
  - option sheet: BC7=19, BCP=20, BCS=30, BC4=40
  - exclusive members: BC7=10, BC4=30, BCP=50, BCS=70

Status: partially progressed; wheels/roof drift persists and the Grand Sport LS6 exclusive-member surface remains stale relative to the option sheet.

Action plan:

1. Decide canonical section order per section, preferring the later reviewed GS/Z06 order only when product/visual intent agrees.
2. For Grand Sport LS6 engine covers, update `grandSport_exclusive_members.gs_excl_ls6_engine_covers` to match the intended radio order, or document why the exclusive-member order intentionally differs from `grandSport_options.sec_engi_001`.
3. Update workbook source display orders and exclusive-member display orders together for future sections/groups whose UI can read both surfaces.
4. Add parity tests scoped to the specific shared sections instead of broad all-model ordering equality.
5. Regenerate and compare generated contracts for order-only diffs.
6. Browser-smoke the affected option sections.

---

### 8. Cross-model customer copy drift remains

Evidence:

- Across 155 strict shared option IDs in active promoted option sheets, Stingray still deviates from the GS/Z06 majority on 50 option names and 86 descriptions.
- 33 shared descriptions still differ only by trailing-period style.
- `tests/workbook-visual-copy-standardization.test.mjs` still loads only `stingray_options` and `grandSport_options` at the top-level sheet map, and still pins period/no-period drift for selected accessory descriptions.
- Examples still present: AJ7, AP9, AUP, BAZ, BV4, CJ2, CM9.

Status: persists from C-2 and C-4, with counts updated after recent workbook cleanup.

Action plan:

1. Treat this as a dedicated workbook copy-convergence pass, not a drive-by cleanup.
2. Build a generated CSV/Markdown review of all shared-option name/description mismatches. Include both strict `option_id` joins and the known RPO fallback cases so Z06 suffix drift does not hide customer-copy differences.
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
- `tests/grand-sport-draft-data.test.mjs` now asserts workbook-owned grouping metadata for active Stingray/Grand Sport/Z06 scope rows and guards against old `read_interior_reference`, `grouping_fields_for_interior`, `fallback_interior_trims`, and `interior_component_metadata` symbols.

Status: the original interior runtime defect, workbook-owned grouping gap, and old fallback-symbol guards are fixed; stale CSV/config surfaces remain.

Action plan:

1. Run a consumer audit for `interior_reference_path` and the two CSVs.
2. If no active code path consumes them, remove `interior_reference_path` from `ModelConfig` and `base_model_config()`.
3. Delete or archive the two CSVs only after proving generated contracts remain stable without the config field.
4. Keep the existing tests that fail if active promoted-model interiors lack workbook-owned grouping metadata or if old fallback symbols reappear.
5. Snapshot current generated JSON, run Stingray, Grand Sport, and Z06 generators, compare generated contracts while ignoring timestamps, then run model/runtime gates after deletion.

---

## Recommended next passes

1. **Display-order guard pass**: add a durable validator/test for promoted option-sheet `(section_id, display_order)` uniqueness now that promoted sheets are clean; decide separately whether to include ZR1/ZR1X scaffold rows.
2. **Fallback-removal pass**: remove or narrow runtime/order-summary fallback constants and update README/AGENTS wording now that promoted models have workbook-owned rows and generated-data tests.
3. **Stingray rear-script exclusive-group pass**: migrate RIK/RIN/SL8 from pairwise excludes to a workbook-owned exclusive group if the intended UX is radio replacement.
4. **Cross-model ordering pass**: settle wheels/roof order drift and the Grand Sport LS6 exclusive-member order mismatch.
5. **Copy-convergence/product-decision pass**: larger workbook copy pass with explicit allowlist, RPO fallback for known Z06 suffix drift, and product review for section/copy decisions.
6. **Interior stale-surface cleanup**: remove unused CSV/config remnants after consumer audit and contract-parity proof.

---

## Gates and evidence refreshed for this update

Original audit gates:

- `.venv/bin/python /tmp/27vette_persistence_audit.py` — read-only workbook/code audit, output saved outside repo.
- `.venv/bin/python scripts/validate_workbook_schema.py stingray_master.xlsx` — valid, 0 errors/warnings.

2026-06-15 documentation refresh evidence:

- `openpyxl` read-only probes against `stingray_master.xlsx` — confirmed Z06 WKS membership/order, no promoted option-sheet duplicate display-order buckets, current copy/order drift counts, remaining ZR1/ZR1X scaffold duplicate buckets, and remaining `interior_reference_path` config field.
- `node` probe against `form-app/data.js` — confirmed Stingray, Grand Sport, and Z06 all emit 11 `orderSummary.sections` rows and 13 `stepMap` entries; confirmed Z06 1LZ/2LZ/3LZ trim choices now have non-empty `info_tooltip` copy.
- `search_files` / `read_file` probes — confirmed current runtime/config fallback symbols, tests covering Z06 tooltip/WKS/orderSummary and interior fallback-symbol guards, and copy test scope.
- `git diff -- docs/persisting-audit-findings-2026-06-14.md` — docs-only diff review.

No generators were run and no workbook or generated artifacts were modified for this report update.
