# Persisting Audit Findings — 2026-06-14

Sources reviewed:

- `docs/audit-cleanup-overview.md`
- `docs/workbook-consistency-review-2026-06-11.md`
- `docs/archive/old-reports/interior-pipeline-assessment.md`

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
2. Residual copy allowlist rows remain explicit product-review follow-ups after the safe convergence cohort and R-6 seat presentation/order pass.
3. R-1 through R-6 product-review decisions are completed or intentionally classified.
4. Z06 option-id suffix drift remains for U2K/U5G/UE1/VV4/CFV and no-RPO Z06 row IDs remain sparse.
5. Stingray exclusive-group ID prefix/style drift remains cosmetic.
6. Interior CSV/config remnants remain even though active interior grouping now comes from workbook metadata.

Intentionally deferred, not part of the completed source-row purge: active emitted `sec_tech_001` / connected-service standard-equipment rows remain active workbook option rows until a separate standard-equipment ownership model is designed and proven.

---

## Remaining issues and action plans

### Completed source-cleanup passes refreshed 2026-06-17

Evidence:

- `docs/archive/completed-specs/active-model-nonruntime-option-row-purge-spec.md` is now historical: current workbook probes found none of the approved purge-list option IDs in their active-model option sheets or OVS sheets, and no active-model `section_presentation.sec_cust_002` rows remain.
- `docs/archive/completed-specs/active-seat-standard-equipment-ownership-spec.md` is now historical: current workbook probes found exactly four active Stingray seat source rows in `sec_seat_002` and found the three required Stingray seat price rules.
- `docs/archive/completed-specs/rule-mapping-column-cleanup-pass1-spec.md` is now historical: current workbook probes found the reduced promoted rule-mapping headers, no retired duplicate/lifecycle columns, no `zr1_rule_mapping` / `zr1x_rule_mapping` sheets, and no future-model rule-mapping registrations.

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
2. Keep `docs/archive/completed-specs/stingray-rear-script-exclusive-group-spec.md` as the historical implementation spec.
3. Treat the intentional UX change as complete: selecting a rear-script badge now replaces the prior badge peer instead of disabling the alternatives through pairwise excludes.

---

### 6. Display-order duplicate buckets — completed for promoted option sheets

Evidence: refreshed workbook audit found no active duplicate `(section_id, display_order)` buckets in the promoted option sheets `stingray_options`, `grandSport_options`, or `z06_options`.

- Current remaining duplicate buckets are future-model scaffold rows only:
  - `zr1_options.sec_stan_001`, order `20`: WUB/U80
  - `zr1x_options.sec_stan_001`, order `20`: U80/WUB
- Active promoted option-sheet `(section_id, display_order)` uniqueness is now enforced by `scripts/validate_workbook_schema.py`; the copy-convergence pass tripped this guard when SC7 moved sections and fixed it with `stingray_options.opt_sc7_001.display_order=71`.

Status: completed for promoted runtime models; residual future-model scaffold duplicates remain outside current runtime readiness.

Action plan:

1. No open action for active promoted option-sheet display-order validation.
2. Decide separately whether future-model scaffold sheets (`zr1_options`, `zr1x_options`) should be cleaned now or only during their promotion/readiness pass.
3. If cleaning scaffold rows, order U80/WUB deterministically by product intent or stable RPO/option ID, then extend the validator scope only after those future sheets are promoted or explicitly opted in.
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
2. Keep `docs/archive/completed-specs/cross-model-ordering-pass-spec.md` as the historical implementation spec.
3. If a future source update makes `CF8` active in multiple promoted models, revisit roof ordering with a new product-order decision rather than assuming the old inactive-row finding is current.

---

### 8. Cross-model customer copy drift — completed for safe convergence cohort

Evidence:

- `docs/copy-convergence-review-2026-06-17.md` records the pre-edit strict shared-option review: 155 strict shared active option IDs and 136 drift fields reviewed.
- Safe GS/Z06-majority copy convergence was applied to Stingray source rows, excluding reviewed/deferred allowlist fields.
- `tests/workbook-visual-copy-standardization.test.mjs` now loads `z06_options`, enforces shared active option name/description parity with an allowlist, rejects trailing-period-only description drift, and guards the approved R-1 through R-6 decisions.
- The remaining copy allowlist is intentional/deferred rather than unreviewed majority drift: AP9 description, D3V description, EYK/EYT badge copy, SFZ applicability, VYW logo applicability, ZZ3 Z06 includes-list difference, NWI description, and PIN restrictions.

Status: completed for safe copy convergence and punctuation drift. Residual allowlist rows remain for explicit product review only.

Action plan:

1. No open implementation action for the completed safe convergence cohort.
2. Keep residual allowlist rows out of automatic majority-copy patches unless the user provides explicit product decisions.
3. If continuing copy cleanup, start with the deferred rows named above and preserve the test allowlist as the decision ledger.

---

### 9. Product-review section/copy decisions — R-1 through R-6 completed or classified

Evidence: the following workbook differences are still present:

- `opt_uv6_001` HUD: Stingray/Grand Sport `sec_2lte_001`; Z06 `sec_1lte_001` remains intentional by user decision.
- `opt_sc7_001` roof pouch: Stingray now uses `sec_lpoe_001`, matching Grand Sport/Z06. Its Stingray display order is `71` to keep active `sec_lpoe_001` order unique.
- `opt_drz_001` copy now uses `Auto-Dimming Rear Camera Mirror` / `Inside rearview with full camera display` across active models.
- `opt_efr_001`/`opt_edu_001` accent copy was updated per user decision: EFR keeps model-specific Stingray copy; EDU uses shared name, Stingray keeps its semicolon description, and GS/Z06 use the approved shorter description.
- `opt_nga_001` copy now uses per-model exhaust-exit descriptions: Stingray `Standard, Corner Exit. NPP Performance exhaust is standard on all 2027's`, Grand Sport `Standard, Corner Exit`, Z06 `Standard, Quad Center Exit`.
- `sec_seat_002` seat presentation/order now uses active promoted seat order AQ9/AH2/AE4/AUP at 10/20/30/40; `opt_aup_001` uses `Asymmetrical Seats` / `Competition Driver Seat, GT2 Passenger Seat` across promoted sheets.

Status: R-1 through R-6 completed or intentionally classified.

Action plan:

1. No open action for R-1 through R-6.
2. If continuing residual copy cleanup, use `docs/copy-convergence-review-2026-06-17.md` plus the `COPY_FIELD_ALLOWLIST` in `tests/workbook-visual-copy-standardization.test.mjs` as the current decision ledger.

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

### 12. Interior CSV/config remnants retired after workbook-owned grouping migration

Evidence:

- `architectureAudit/stingray_interiors_refactor.csv` and `architectureAudit/grand_sport_interiors_refactor.csv` are deleted.
- `scripts/corvette_form_generator/model_configs.py` no longer assigns an interior CSV reference path.
- `scripts/corvette_form_generator/model_config.py` no longer carries `interior_reference_path` in `ModelConfig`.
- Current active builder no longer uses those CSV fallbacks: `interiors.py` builds from `model_interior_scope`, raises when active scope rows are missing, and no longer contains the old `INTERIOR_COMPONENT_LABELS` / `broad_interior_color_family` heuristic surfaces.
- `tests/grand-sport-draft-data.test.mjs` now asserts workbook-owned grouping metadata for active Stingray/Grand Sport/Z06 scope rows and guards against old `read_interior_reference`, `grouping_fields_for_interior`, `fallback_interior_trims`, `interior_component_metadata`, `interior_reference_path`, and stale interior CSV file-name surfaces.

Status: completed. The original interior runtime defect, workbook-owned grouping gap, old fallback-symbol guards, and remaining stale CSV/config surfaces are fixed/retired.

Follow-up guardrails:

1. Keep the existing tests that fail if active promoted-model interiors lack workbook-owned grouping metadata or if old fallback/config symbols reappear.
2. Do not add a replacement CSV/reference path; model/interior grouping metadata belongs in `model_interior_scope` and component membership belongs in `interior_components`.

---

## Recommended next passes

1. **Residual copy allowlist pass, if desired**: resolve the remaining copy allowlist rows from `tests/workbook-visual-copy-standardization.test.mjs`.
2. **Active standard-tech / connected-service ownership**: design a workbook-owned replacement source before deleting active `sec_tech_001` emitted standard-equipment rows.
3. **Optional audit/report tooling classification or later rule-mapping cleanup**: continue only with a scoped spec that distinguishes default readiness from opt-in provenance/report tooling.

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

2026-06-18 interior stale-surface cleanup evidence:

- Active source guard — `tests/grand-sport-draft-data.test.mjs` fails when `interior_reference_path` remains in active config and passes after removal.
- Config/file cleanup — `ModelConfig.interior_reference_path`, the `base_model_config()` CSV-path assignment, and the two `architectureAudit/*_interiors_refactor.csv` files are removed.
- Controlled generation proof — regenerated Stingray, Grand Sport, and Z06 contracts matched between the removed-field implementation and a temporary control run with the unused field restored, proving the retired config surface did not affect generated payloads.
- Targeted gates — workbook package/schema validation, interior-focused Node tests, multi-model runtime switching, Python compile, and model config metadata tests passed.

2026-06-17 Stingray rear-script exclusive-group implementation evidence:

- Workbook source edit — `exclusive_groups.excl_rear_script_badges` plus three `exclusive_group_members` rows were added; the six pairwise RIK/RIN/SL8 Stingray `rule_mapping` rows were removed; the three option `detail_raw` source notes were preserved.
- Generated contract comparison — after ignoring timestamps and the rule-count validation message, the only payload drift was one added Stingray exclusive group and six removed rear-script pairwise rules; choices, prices, interiors, color overrides, standard equipment, dealer payload fields, and non-Stingray model contracts were unchanged.
- Targeted gates — Stingray generation, registry publication, workbook package/schema validation, allowed-drift contract comparison, Stingray runtime regression, multi-model runtime switching, and `git diff --check` passed for this pass.

2026-06-17 cross-model ordering implementation evidence:

- Workbook source edit — `z06_options` swapped the `SOM`/`ROX` display-order values to align the shared wheel subset, and `grandSport_exclusive_members.gs_excl_ls6_engine_covers` was reordered to match `grandSport_options.sec_engi_001`.
- Roof finding resolution — active shared roof order is now covered by a characterization guard; no roof workbook rows changed because `CF8` is active only for Grand Sport in current promoted data.
- Generated contract review — an order-aware allowlist probe against `/tmp/before-*` snapshots confirmed only the approved Grand Sport LS6 group order and Z06 wheel order drift in draft/runtime artifacts.
- Targeted gates — Grand Sport/Z06 generation, registry publication, workbook package/schema validation, order-aware generated-contract probe, Grand Sport draft, Z06 draft, multi-model runtime switching, and `git diff --check` passed for this pass.

2026-06-17 copy-convergence/product-decision implementation evidence:

- Workbook source edit — safe GS/Z06-majority copy convergence was applied to Stingray option source rows; R-1 through R-6 decisions were applied or intentionally classified.
- Review artifact — `docs/copy-convergence-review-2026-06-17.md` records the 155 strict shared IDs, 136 reviewed drift fields, 116 mechanical copy fields, 10 user-decision fields, and 10 deferred allowlist fields.
- Guardrail behavior — moving SC7 to `sec_lpoe_001` triggered the active promoted display-order validator; the workbook was corrected with `stingray_options.opt_sc7_001.display_order=71` and schema validation returned valid.
- Targeted gates — workbook package/schema validation, Stingray/Grand Sport/Z06 generation, registry publication, visual-copy standardization, Stingray regression/stability, Grand Sport preview/draft, Z06 preview/draft, and multi-model runtime switching passed.

2026-06-17 R-6 seat presentation/order implementation evidence:

- Workbook source edit — active `sec_seat_002` rows in `stingray_options`, `grandSport_options`, and `z06_options` now use order AQ9/AH2/AE4/AUP at 10/20/30/40; `opt_aup_001` uses `Asymmetrical Seats` / `Competition Driver Seat, GT2 Passenger Seat` across promoted sheets.
- Guardrail test — `tests/workbook-visual-copy-standardization.test.mjs` removes AUP from the copy allowlist and asserts the R-6 copy/order contract.
- Targeted gates — workbook package/schema validation, Stingray/Grand Sport/Z06 generation, registry publication, visual-copy standardization, Stingray regression/stability, Grand Sport draft, Z06 draft, and multi-model runtime switching passed.
