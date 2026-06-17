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
- Active-model non-runtime option-row purge is complete: the approved purge-list rows are absent from the matching active option sheets and OVS sheets, and active-model `section_presentation.sec_cust_002` rows are absent.
- Stingray active seat canonicalization is complete: active seat source rows are now the four canonical `sec_seat_002` rows `opt_aq9_001`, `opt_ah2_001`, `opt_ae4_002`, and `opt_aup_001`, with the three required Stingray trim-scoped seat price rules present.
- Rule-mapping column cleanup Pass 1 is complete: promoted rule-mapping sheets now use the reduced runtime-source header set, retired duplicate/lifecycle columns are absent, and unpromoted ZR1/ZR1X rule-mapping sheets/source registrations are absent.
- Browser order-summary fallback retirement / boundary narrowing is complete: promoted runtime models carry generated workbook-owned `orderSummary` metadata, browser `orderSectionDefinitions` / `stepOrderSectionKeys` fallback constants are removed, and Python step/context constants are documented as unpromoted compatibility / completeness-check inputs.
- Stingray rear script badge cleanup is complete: `exclusive_groups.excl_rear_script_badges` and its three members now own RIK/RIN/SL8 replacement behavior, and the six redundant pairwise Stingray `rule_mapping` excludes are gone.
- Cross-model ordering cleanup is complete for the confirmed active surfaces: Z06 `SOM`/`ROX` order now matches the Grand Sport shared wheel sequence, Grand Sport LS6 exclusive-member order now matches its option-sheet order, and active shared roof order is guarded without a workbook edit.

Still persisting and needing an action plan:

1. Optional audit/report tooling remains as opt-in historical tooling.
2. Cross-model customer copy drift remains, including trailing-period drift pinned by tests.
3. Several section/copy decisions remain product-review items.
4. Z06 option-id suffix drift remains for U2K/U5G/UE1/VV4/CFV and no-RPO Z06 row IDs remain sparse.
5. Stingray exclusive-group ID prefix/style drift remains cosmetic.
6. Interior CSV/config remnants remain even though active interior grouping now comes from workbook metadata.

Intentionally deferred, not part of the completed source-row purge: active emitted `sec_tech_001` / connected-service standard-equipment rows remain active workbook option rows until a separate standard-equipment ownership model is designed and proven.

---

## Remaining issues and action plans

### Completed source-cleanup passes refreshed 2026-06-17

Evidence:

- `docs/active-model-nonruntime-option-row-purge-spec.md` is now historical: current workbook probes found none of the approved purge-list option IDs in their active-model option sheets or OVS sheets, and no active-model `section_presentation.sec_cust_002` rows remain.
- `docs/active-seat-standard-equipment-ownership-spec.md` is now historical: current workbook probes found exactly four active Stingray seat source rows in `sec_seat_002` and found the three required Stingray seat price rules.
- `docs/rule-mapping-column-cleanup-pass1-spec.md` is now historical: current workbook probes found the reduced promoted rule-mapping headers, no retired duplicate/lifecycle columns, no `zr1_rule_mapping` / `zr1x_rule_mapping` sheets, and no future-model rule-mapping registrations.

Status: completed. These are not current recommended next passes.

Action plan:

1. No open implementation action for the completed non-runtime option-row purge, Stingray seat canonicalization, or rule-mapping column cleanup Pass 1.
2. Keep their docs as historical specs with top-level completed status.
3. Keep their deferred follow-ons separate:
   - active `sec_tech_001` / connected-service ownership requires a future standard-equipment source model,
   - `body_style_scope` / `runtime_action` cleanup requires future parity-proven rule modeling,
   - fallback retirement remains a separate runtime/generator boundary pass.

---

### 1. Runtime/order-summary fallback constants after Pass E option (a) — completed

Evidence:

- `form-app/app.js` no longer carries browser order-summary fallback constants `orderSectionDefinitions`, `orderSectionLabels`, `orderSectionOrder`, or `stepOrderSectionKeys`.
- `orderSummarySections()` and `orderSummaryStepMap()` now require generated `data.orderSummary` metadata and raise a clearly named missing-generated-data error instead of returning an empty/malformed fallback.
- `tests/multi-model-runtime-switching.test.mjs` guards against reintroducing the retired browser fallback symbols and verifies every active registry model emits generated `orderSummary.sections` and `orderSummary.stepMap`.
- `scripts/corvette_form_generator/model_configs.py` and `runtime_metadata.py` now document Python step/context constants as unpromoted compatibility defaults and promoted completeness-check inputs, not active promoted runtime metadata ownership.
- `README.md` now documents that all promoted runtime models carry workbook-owned `orderSummary` metadata.

Status: completed.

Action plan:

1. No open action for browser order-summary fallback retirement.
2. Keep Python `STEP_ORDER`, `STEP_LABELS`, and `CONTEXT_SECTIONS` only as unpromoted compatibility / completeness-check inputs unless a later future-model workflow pass approves removing that fallback boundary.

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

### 5. Stingray rear script badges use a workbook-owned exclusive group — completed

Evidence:

- `exclusive_groups` now has active `excl_rear_script_badges` with `selection_mode=single_within_group`.
- `exclusive_group_members` now has active members `opt_rik_001`, `opt_rin_001`, and `opt_sl8_001` at display orders 10/20/30.
- `rule_mapping` no longer has the six redundant pairwise `excludes` rows among RIK/RIN/SL8.
- Grand Sport and Z06 have equivalent model-scoped exclusive groups.
- The three Stingray option rows still preserve their raw GM source incompatibility details in `stingray_options.detail_raw`.
- `form-output/stingray-form-data.json` now emits the Stingray rear-script exclusive group and no pairwise rear-script rules.
- `tests/stingray-form-regression.test.mjs` asserts the generated group, absence of pairwise rear-script rules, and replacement behavior through the accessory exclusive-group runtime path.

Status: completed 2026-06-17.

Action plan:

1. No remaining implementation action for Stingray rear-script badges.
2. Keep `docs/stingray-rear-script-exclusive-group-spec.md` as the historical implementation spec.
3. Treat the intentional UX change as complete: selecting a rear-script badge now replaces the prior badge peer instead of disabling the alternatives through pairwise excludes.

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

### 7. Cross-model relative order and exclusive-member order drift — completed for confirmed active surfaces

Evidence:

- GS/Z06 shared wheels now agree on the confirmed shared forged/carbon-wheel sequence `ROU`, `SON`, `SOM`, `ROX`, `ROY`, `ROZ`, `STZ`:
  - Grand Sport: `SOM=43`, `ROX=44`
  - Z06: `SOM=23`, `ROX=30`
- The older roof `CF8`/`CM9` finding is not active emitted cross-model drift:
  - `CF8` is currently active only in Grand Sport.
  - Active shared roof order is guarded as `CF7`, `C2Z`, `CC3`, `CM9`, `D84`, `D86` across promoted models.
- Grand Sport engine appearance option-sheet order is normalized for the LS6 cover rows, and `gs_excl_ls6_engine_covers` exclusive-member order now agrees with that source order:
  - option sheet: BC7=19, BCP=20, BCS=30, BC4=40
  - exclusive members: BC7=10, BCP=20, BCS=30, BC4=40
- `tests/grand-sport-draft-data.test.mjs`, `tests/z06-form-data-draft.test.mjs`, and `tests/multi-model-runtime-switching.test.mjs` cover these order surfaces.

Status: completed 2026-06-17 for the confirmed active ordering surfaces.

Action plan:

1. No remaining implementation action for the scoped cross-model ordering pass.
2. Keep `docs/cross-model-ordering-pass-spec.md` as the historical implementation spec.
3. If a future source update makes `CF8` active in multiple promoted models, revisit roof ordering with a new product-order decision rather than assuming the old inactive-row finding is current.

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

1. **Copy-convergence/product-decision pass**: larger workbook copy pass with explicit allowlist, RPO fallback for known Z06 suffix drift, and product review for section/copy decisions.
2. **Interior stale-surface cleanup**: remove unused CSV/config remnants after consumer audit and contract-parity proof.
3. **Future-model scaffold display-order decision**: decide whether ZR1/ZR1X standard-equipment duplicate display-order buckets should be cleaned now or only during their promotion/readiness pass.

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

2026-06-17 documentation refresh evidence:

- `openpyxl` read-only probes against `stingray_master.xlsx` — confirmed active-model nonruntime purge-list rows and matching OVS rows are absent; active-model `section_presentation.sec_cust_002` rows are absent; Stingray active seats are canonicalized to four `sec_seat_002` rows; the three Stingray seat price rules are present; promoted rule-mapping sheets use the reduced header set; retired rule-mapping columns and ZR1/ZR1X rule-mapping registrations are absent; promoted runtime metadata row counts remain complete.
- `rg` probe against `form-app`, `scripts`, and this document — confirmed `orderSectionDefinitions`, `stepOrderSectionKeys`, `STEP_ORDER`, `STEP_LABELS`, `CONTEXT_SECTIONS`, and `interior_reference_path` still exist where the remaining action plans say they persist.
- Docs-only status refresh — updated completed status in the three historical specs and this persistence handoff; no workbook, generated artifact, runtime, or test changes were made.

2026-06-17 fallback-retirement implementation evidence:

- `form-app/app.js` source guard — retired browser order-summary fallback symbols and fallback expressions are absent.
- Active registry data tests — Stingray, Grand Sport, and Z06 all emit generated `orderSummary.sections` and `orderSummary.stepMap` metadata.
- Runtime/generator boundary docs — Python step/context constants remain documented as unpromoted compatibility / promoted completeness-check inputs, not browser runtime fallbacks.

2026-06-17 Stingray rear-script exclusive-group implementation evidence:

- Workbook source edit — `exclusive_groups.excl_rear_script_badges` plus three `exclusive_group_members` rows were added; the six pairwise RIK/RIN/SL8 Stingray `rule_mapping` rows were removed; the three option `detail_raw` source notes were preserved.
- Generated contract comparison — after ignoring timestamps and the rule-count validation message, the only payload drift was one added Stingray exclusive group and six removed rear-script pairwise rules; choices, prices, interiors, color overrides, standard equipment, dealer payload fields, and non-Stingray model contracts were unchanged.
- Targeted gates — Stingray generation, registry publication, workbook package/schema validation, allowed-drift contract comparison, Stingray runtime regression, multi-model runtime switching, and `git diff --check` passed for this pass.

2026-06-17 cross-model ordering implementation evidence:

- Workbook source edit — `z06_options` swapped the `SOM`/`ROX` display-order values to align the shared wheel subset, and `grandSport_exclusive_members.gs_excl_ls6_engine_covers` was reordered to match `grandSport_options.sec_engi_001`.
- Roof finding resolution — active shared roof order is now covered by a characterization guard; no roof workbook rows changed because `CF8` is active only for Grand Sport in current promoted data.
- Generated contract review — an order-aware allowlist probe against `/tmp/before-*` snapshots confirmed only the approved Grand Sport LS6 group order and Z06 wheel order drift in draft/runtime artifacts.
- Targeted gates — Grand Sport/Z06 generation, registry publication, workbook package/schema validation, order-aware generated-contract probe, Grand Sport draft, Z06 draft, multi-model runtime switching, and `git diff --check` passed for this pass.
