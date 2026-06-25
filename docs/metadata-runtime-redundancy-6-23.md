# Findings

## Ordered by Architecture Risk

### Highest risk

1. Runtime_rule_exceptions is now an empty segregated runtime behavior surface after Pass 15.
   - Current state after Pass 15: 0 rows / 0 active.
   - Active rows: none.
   - Current consumers:
     - scripts/corvette_form_generator/runtime_metadata.py:283
     - scripts/corvette_form_generator/production.py:180, emitted at production.py:625
     - form-app/app.js:626-668, form-app/app.js:1004-1019
     - Tests now pin the empty exception surface and retired GBA/ZYC plus Z51/FE1/FE2 canonical owners in tests/stingray-form-regression.test.mjs.
   - This sheet is workbook-owned, but no longer owns active Stingray behavior after Pass 15.
   - ex_nwi_nga is not present in current workbook evidence and is correctly not treated as open.
   - Retired canonical candidates:
     - ex_gba_zyc: Pass 14 moved this behavior to Stingray rule_groups / rule_group_members as excludes_any from GBA to ZYC and removed the reverse direct rule opt_zyc_001 excludes opt_gba_001 after generated-data and browser/runtime parity proof.
     - ex_z51_fe1 / ex_z51_fe2: Pass 15 moved this behavior to Stingray rule_mapping direct excludes from opt_z51_001 to opt_fe1_001/opt_fe2_001 with runtime_action=replace, removed the reverse FE2 -> Z51 direct rule, and preserved default_fe1 plus Z51 -> FE3 include behavior after generated-data and browser/runtime parity proof.
   - Remaining migration: none for active runtime_rule_exceptions rows.

### Medium-high risk

1. Variant override behavior is now model-scoped for active UQT behavior; the historical global sheet/loader path was retired in Pass 19.
   - variant_option_overrides: physical sheet deleted after Pass 19. No active model source role points to it, and `runtime_metadata.load_variant_option_overrides()` no longer reads a global first-choice sheet.
   - stingray_variant_overrides: 4 active rows after Pass 18, conventional row activation.
   - grandSport_variant_overrides: 4 active rows after Pass 18, conventional row activation.
   - z06_variant_overrides: 4 active rows, conventional row activation.
   - Current consumers:
     - runtime_metadata.py: variant override loading plus Pass 17 `derived_default_selected_display_behavior()`.
     - production.py: generic Stingray model-scoped variant override `section_id` application, standard-preserving `display_only`, and derived default-selected display metadata for Stingray BC7.
     - inspection.py: model-scoped variant override application and derived default-selected display metadata for Grand Sport BC7/NGA.
     - schema/type guards in schema_validation.py:42-45
     - tests in stingray-generator-stability.test.mjs, grand-sport-draft-data.test.mjs, workbook-schema-standardization.test.mjs
   - Current behavior carried:
     - Stingray model-scoped overrides: UQT display-only standard rows for 2LT/3LT only. Global Stingray UQT suppression rows were removed in Pass 18.
     - Grand Sport overrides: UQT display-only standard rows for 2LT/3LT only. BC7 coupe and NGA all-variant default_selected rows were removed in Pass 17 and now derive from default_selection_rules plus exclusive groups.
     - Z06 overrides: UQT display-only standard rows for 2LZ/3LZ.
   - The remaining model-scoped sheets still carry canonical UQT emitted choice selectability, display-only behavior, and section_id placement.
   - Remaining canonical candidate:
     - None for active UQT source ownership after Pass 18. The current source model is canonical option rows plus model-scoped variant presentation overrides for trim-standard placement/selectability.
   - Pass 17 completed the BC7/NGA default-selected migration with generated parity and browser/runtime proof. Pass 18 completed the UQT single-canonical-option-row migration with allowlisted UQT drift and browser/runtime proof. Pass 19 retired the empty global override sheet/loader path with timestamp-normalized generated parity.

### Medium risk

3. Variant topology is split between variant_master and model_variants, and their active semantics are not aligned.
   - variant_master: 32 rows / 12 active, shared catalog.
   - model_variants: 26 rows / 18 active, model membership/order for Stingray, Grand Sport, Z06.
   - Evidence:
     - model_variants has 6 active Grand Sport variants.
     - variant_master Grand Sport 1lt_e07 etc. rows are inactive.
     - Inspection/generation path still includes configured variants from model_variants; inspection.py:671-688 builds variants from config.variant_ids and preserves source_active.
     - inspection.py:566-572 explicitly warns when configured variants are inactive in variant_master.
   - This is duplicate topology, not necessarily bad. Current evidence suggests:
     - variant_master owns variant facts: trim, body style, display name, base price.
     - model_variants owns model membership and generation order.
     - variant_master.active is ambiguous for promoted non-Stingray models and should not be treated as the sole active-model gate.
   - Recommended future action is consolidation/clarification, not deletion.

### Lower risk

4. Lower risk / keep: model_master, model_registry_promotion, and model_workbook_sources are redundant-looking but currently have distinct canonical roles.
   - model_master: active/generatable model identity and expected variant count.
   - model_registry_promotion: runtime publication decision and artifact path.
   - model_workbook_sources: model-to-source-sheet graph for generators.
   - These are consumed by model discovery, registry generation, schema validation, and tests. They are not just duplicate metadata.

5. Lower risk / keep: model_interior_scope is large but currently canonical for model/interior scoping and hierarchy metadata.
   - 572 rows / 572 active.
   - Consumed through runtime_metadata.load_model_interior_scope_map() and interiors.build_model_interiors().
   - It duplicates some interior facts from lt_interiors / LZ_Interiors, but current evidence says it owns model scoping and grouping, not option-card source rows.

## Sheet-by-sheet table:

Sheet: runtime_rule_exceptions — 0 rows / 0 active after Pass 15; coverage none; keys model_key, exception_id, source_option_id, target_option_id, exception_type,
scopes, disabled_reason, active
Current consumer(s): runtime_metadata.py:283; production.py:180,625; form-app/app.js:626-668,1004-1019;
stingray-form-regression.test.mjs
Current behavior/data ownership: Empty exception behavior surface. Pass 14 retired ex_gba_zyc into rule_groups.grp_gba_excludes_zyc plus rule_group_members. Pass 15 retired ex_z51_fe1 and ex_z51_fe2 into rule_mapping Z51 -> FE1/FE2 replacement excludes.
Canonical-owner candidate: Existing workbook owners: rule_mapping, rule_groups/members, exclusive_groups/members, default_selection_rules, option rows.
Risk level: High
Recommended next action: Keep empty unless a future, separately approved pass proves a true exception cannot be expressed through normal rule/default/group ownership.
Required parity gates: If future rows are added, require workbook edit with safe save, generated contract diff, targeted runtime tests, and local browser proof.
────────────────────────────────────────
Sheet: variant_option_overrides — retired after Pass 19; physical worksheet absent. Former keys: model_key, option_id, variant_id,
status, selectable, active, display_behavior, notes
Current consumer(s): none for active workflow. `runtime_metadata.load_variant_option_overrides()` now reads only configured model-scoped `variant_option_overrides_sheet` roles.
Current behavior/data ownership: None. Stingray UQT global suppression rows were removed in Pass 18. The empty global sheet and global-first loader path were removed in Pass 19.
Canonical-owner candidate: Retired surface. Do not reintroduce without a new source-owner spec.
Risk level: Retired / guarded
Recommended next action: Keep retired. Use model-scoped override sheets for active variant presentation overrides.
Required parity gates: If reintroduced, require a new spec, active-source-role proof, generated contract parity, and browser/runtime proof.
────────────────────────────────────────
Sheet: stingray_variant_overrides — 4 rows / 4 active after Pass 18; coverage Stingray sheet-scoped; keys option_id, variant_id, selectable, display_behavior,
section_id, active, note
Current consumer(s): runtime_metadata.py model-scoped variant override loader; production.py generic section override/display-only application; stingray-runtime-contract.json; tests in stingray-generator-stability.test.mjs
Current behavior/data ownership: Canonical Stingray UQT display-only standard rows for 2LT/3LT.
Canonical-owner candidate: Keep as canonical for Stingray UQT trim-standard placement/selectability unless a later approved model-scoped presentation-owner replacement is designed.
Risk level: Medium-high
Recommended next action: Keep.
Required parity gates: Stingray generator + registry; allowlisted UQT contract drift if edited; stingray-generator-stability.test.mjs; stingray-form-regression.test.mjs; browser/runtime UQT proof.
────────────────────────────────────────
Sheet: grandSport_variant_overrides — 4 rows / 4 active after Pass 18; coverage Grand Sport sheet-scoped; keys option_id, variant_id, selectable, display_behavior,
section_id, active, note
Current consumer(s): Same loader via model_workbook_sources.variant_option_overrides_sheet; inspection.py draft/runtime path;
grand-sport-runtime-contract.json; Pass 17 default-selected derivation helper
Current behavior/data ownership: Override behavior. Remaining rows are Grand Sport UQT display-only standard rows. BC7 coupe and NGA all variants default-selected rows were removed in Pass 17 and now derive from default_selection_rules plus exclusive groups.
Canonical-owner candidate: Keep as canonical for Grand Sport UQT trim-standard placement/selectability. BC7/NGA defaults: migrated in Pass 17.
Risk level: Medium-high
Recommended next action: Keep.
Required parity gates: If edited, generate_form.py --model grand_sport, registry, grand-sport-contract-preview.test.mjs, grand-sport-draft-data.test.mjs, runtime/browser checks for UQT.
────────────────────────────────────────
Sheet: z06_variant_overrides — 4 rows / 4 active; coverage Z06 sheet-scoped; keys same as Grand Sport
Current consumer(s): Same loader via model_workbook_sources; inspection.py; Z06 runtime contract/tests
Current behavior/data ownership: Override behavior. UQT 2LZ/3LZ display-only standard rows.
Canonical-owner candidate: Keep as canonical for Z06 UQT trim-standard placement/selectability unless a later approved owner replaces model-scoped overrides; current z06_ovs cannot carry selectable, display_behavior, or section_id.
Risk level: Medium
Recommended next action: Keep. Do not migrate Z06 replacement behavior under a UQT cleanup pass.
Required parity gates: Future pass: generate_form.py --model z06, registry, z06-contract-preview.test.mjs, z06-form-data-draft.test.mjs, relevant Z06
runtime tests, browser check for UQT display-only rows.
────────────────────────────────────────
Sheet: model_master — 5 rows / 3 active; coverage Stingray, Grand Sport, Z06 active; ZR1/ZR1X inactive; keys model_key, registry_key, model_label,
model_year, dataset_name, export_slug, expected_variant_count, default_model, active
Current consumer(s): model_configs.py:304-320; runtime_metadata.py:526-657; schema_validation.py:430-476; registry tests
Current behavior/data ownership: Canonical model identity and generation eligibility metadata.
Canonical-owner candidate: Keep as canonical. model_registry_promotion should remain separate because publication is a distinct decision.
Risk level: Low
Recommended next action: Keep.
Required parity gates: Schema validation; pytest tests/test_model_config_metadata.py tests/test_schema_validation_metadata.py; generator discovery smoke.
────────────────────────────────────────
Sheet: model_registry_promotion — 5 rows / 3 active; active promoted Stingray, Grand Sport, Z06; keys model_key, registry_key, promoted_to_runtime,
default_model, artifact_path, artifact_type, legacy_alias, active, display_order
Current consumer(s): registry_promotion.py:194-253; generate_registry.py:27-38; schema_validation.py:477-590; test_registry_promotion_metadata.py
Current behavior/data ownership: Runtime publication metadata and promoted artifact path ownership.
Canonical-owner candidate: Keep as canonical runtime-publication sheet.
Risk level: Low
Recommended next action: Keep.
Required parity gates: generate_registry.py only in future implementation; registry promotion tests; multi-model runtime switching.
────────────────────────────────────────
Sheet: model_workbook_sources — 53 rows / 33 active after Pass 18; active roles: Stingray 11, Grand Sport 11, Z06 11; inactive ZR1/ZR1X roles; keys model_key,
source_role, sheet_name, active, notes
Current consumer(s): model_configs.py:261-320; runtime_metadata.py:545-657; schema_validation.py:339-402; editor payload/tests
Current behavior/data ownership: Generated workflow metadata. Maps each model to source sheets.
Canonical-owner candidate: Keep as canonical source graph. Python base config remains compatibility/default, not source of truth.
Risk level: Low-medium
Recommended next action: Keep.
Required parity gates: Schema validation; model config metadata tests; generator discovery for active models.
────────────────────────────────────────
Sheet: model_variants — 26 rows / 18 active; active coverage Stingray 6, Grand Sport 6, Z06 6; keys model_key, variant_id, display_order, active, notes
Current consumer(s): model_configs.py:282-320; runtime_metadata.py:552-568; generator config resolution
Current behavior/data ownership: Model-to-variant membership/order.
Canonical-owner candidate: Keep, but clarify relationship to variant_master.active.
Risk level: Medium
Recommended next action: Consolidate candidate for active semantics only; do not delete.
Required parity gates: Generator discovery tests; generated contract variant parity; model switching tests.
────────────────────────────────────────
Sheet: variant_master — 32 rows / 12 active; shared catalog; keys variant_id, model_year, trim_level, body_style, display_name, base_price, display_order,
active
Current consumer(s): production.py:169,226-238; inspection.py:428,671-688; generated contracts
Current behavior/data ownership: Variant product facts: trim/body/display/base price. active is not currently the sole promoted-model membership signal.
Canonical-owner candidate: Keep as canonical product-fact catalog; model_variants owns membership.
Risk level: Medium
Recommended next action: Consolidate candidate: define/validate active semantics against model_variants.
Required parity gates: Schema validation; all active model generators; generated variant count/name/base-price parity tests.
────────────────────────────────────────
Sheet: model_interior_scope — 572 rows / 572 active; coverage Grand Sport 132, Z06 130, ZR1 90, ZR1X 90, Stingray 130; keys include model_key, interior_id,
trim_level, requires_option_id, hierarchy/grouping fields
Current consumer(s): runtime_metadata.py:381-417; interiors.py; production.py:398; inspection.py:966; interior tests
Current behavior/data ownership: Model/interior scoping and hierarchy/grouping metadata.
Canonical-owner candidate: Keep as canonical model/interior scope owner. Source interior sheets still own interior product rows.
Risk level: Low
Recommended next action: Keep.
Required parity gates: Interior generated contract tests; grand-sport-draft-data.test.mjs; stingray-form-regression.test.mjs interior scope tests.
────────────────────────────────────────
Sheet: runtime_steps — 42 rows / 42 active; coverage Stingray/Grand Sport/Z06 14 each
Current consumer(s): runtime_metadata.py:106-155; production.py; inspection.py
Current behavior/data ownership: Workbook-owned runtime metadata, not duplicate variant topology.
Canonical-owner candidate: Keep.
Risk level: Low
Recommended next action: Keep.
Required parity gates: Runtime contract tests; multi-model runtime switching.
────────────────────────────────────────
Sheet: context_section_master — 6 rows / 6 active; coverage Stingray/Grand Sport/Z06 2 each
Current consumer(s): runtime_metadata.py:158-193; generator paths
Current behavior/data ownership: Workbook-owned context section metadata.
Canonical-owner candidate: Keep.
Risk level: Low
Recommended next action: Keep.
Required parity gates: Runtime contract/model switching tests.
────────────────────────────────────────
Sheet: section_presentation — 31 rows / 31 active; coverage Stingray 11, Grand Sport 12, Z06 8
Current consumer(s): runtime_metadata.py:196-222; generator paths
Current behavior/data ownership: Runtime presentation/placement metadata.
Canonical-owner candidate: Keep.
Risk level: Low
Recommended next action: Keep.
Required parity gates: Generated contract tests; section/step placement guards.
────────────────────────────────────────
Sheet: context_choice_copy — 6 rows / 6 active; coverage shared \*:3, Z06:3
Current consumer(s): contract.context_choice_copy_rows; generator paths
Current behavior/data ownership: Context-card copy metadata.
Canonical-owner candidate: Keep.
Risk level: Low
Recommended next action: Keep.
Required parity gates: Generated context choice tests/browser smoke if changed.
────────────────────────────────────────
Sheet: order_summary_sections — 34 rows / 34 active; coverage Stingray 11, Grand Sport 11, Z06 12
Current consumer(s): runtime_metadata.py:301-337; form-app/app.js:1125-1164
Current behavior/data ownership: Workbook-owned order summary metadata.
Canonical-owner candidate: Keep.
Risk level: Low
Recommended next action: Keep.
Required parity gates: Runtime contract tests; order summary browser smoke.
────────────────────────────────────────
Sheet: step_order_summary_map — 40 rows / 40 active; coverage Stingray 13, Grand Sport 13, Z06 14
Current consumer(s): Same as above
Current behavior/data ownership: Workbook-owned step-to-summary mapping.
Canonical-owner candidate: Keep.
Risk level: Low
Recommended next action: Keep.
Required parity gates: Same as above.
────────────────────────────────────────
Sheet: asset_map — 111 rows / 98 active; coverage Grand Sport 46, Stingray 27, Z06 38
Current consumer(s): contract.load_asset_map / load_model_asset_map; registry/model assets
Current behavior/data ownership: Model/option media metadata, not variant topology.
Canonical-owner candidate: Keep.
Risk level: Low
Recommended next action: Keep.
Required parity gates: Asset map duplicate-key checks; generated contract/browser image smoke if changed.
────────────────────────────────────────
Sheet: interior_components — 846 rows / 846 active; coverage Stingray 197, Grand Sport 198, Z06 197, ZR1 127, ZR1X 127
Current consumer(s): runtime_metadata.py:340-378; interiors.py
Current behavior/data ownership: Interior component membership/pricing metadata.
Canonical-owner candidate: Keep.
Risk level: Low
Recommended next action: Keep.
Required parity gates: Interior component tests; generated pricing parity if changed.
────────────────────────────────────────
Sheet: stingray_ovs, grandSport_ovs, z06_ovs — 1458 / 1452 / 1458 rows; no active column, all read as status rows
Current consumer(s): production.py:171-172,318-327; inspection.py:101-120
Current behavior/data ownership: Option/variant availability status matrix.
Canonical-owner candidate: Keep as canonical availability owner.
Risk level: Low
Recommended next action: Keep.
Required parity gates: OVS/source option referential validation; generated choice status parity.
────────────────────────────────────────
Sheet: zr1_variant_overrides, zr1x_variant_overrides — 0 rows / 0 active
Current consumer(s): Discovered by headers and inactive model_workbook_sources scaffold; not active current runtime source
Current behavior/data ownership: Empty future-model scaffold.
Canonical-owner candidate: Needs future-model readiness evidence before keeping or retiring.
Risk level: Low current runtime risk
Recommended next action: Needs more evidence.
Required parity gates: Future ZR1/ZR1X readiness audit only; no current runtime gate.

## Pass 14 completed implementation:

Pass 14 implemented the former safest next pass for `runtime_rule_exceptions.ex_gba_zyc` only.

What changed:

- Added Stingray `rule_groups.grp_gba_excludes_zyc` as an `excludes_any` group from `opt_gba_001` to `opt_zyc_001`.
- Added the matching `rule_group_members` target `opt_zyc_001`.
- Removed `runtime_rule_exceptions.ex_gba_zyc`.
- Removed reverse direct rule `rule_mapping.rule_opt_zyc_001_excludes_opt_gba_001` so GBA remains selectable after ZYC is selected.
- Preserved `rule_mapping.rule_opt_zyc_001_includes_opt_drg_001` and the remaining Z51/FE1/FE2 runtime exceptions.
- Regenerated Stingray runtime artifacts and `form-app/data.js`.

Parity proven:

- Generated contract deltas were limited to the approved grouped-exclusion addition, reverse direct-rule removal, `ex_gba_zyc` removal, and the resulting compatibility-rule count change from 141 to 140.
- Browser/runtime proof on the local form showed ZYC selected first leaves GBA selectable; selecting GBA removes ZYC from selected/user-selected state; ZYC remains disabled with the workbook-owned reason; clicking ZYC while GBA is selected does not re-add it; model switching to Grand Sport and Z06 still renders.

Next implementation candidate:

- Completed by Pass 15. There are no remaining active `runtime_rule_exceptions` rows.

## Pass 15 completed implementation:

Pass 15 implemented the former remaining `runtime_rule_exceptions` cleanup for Stingray Z51 suspension/default behavior.

What changed:

- Added `rule_mapping.rule_opt_z51_001_excludes_opt_fe1_001` and `rule_mapping.rule_opt_z51_001_excludes_opt_fe2_001` as direct Z51 replacement excludes with `runtime_action=replace`.
- Removed reverse direct rule `rule_mapping.rule_opt_fe2_001_excludes_opt_z51_001` so FE2 selected first does not block selecting Z51.
- Removed `runtime_rule_exceptions.ex_z51_fe1` and `runtime_rule_exceptions.ex_z51_fe2`.
- Preserved `default_selection_rules.default_fe1`, Z51 -> FE3 include behavior, and FE4 requires/includes behavior.
- Regenerated Stingray runtime artifacts and `form-app/data.js`.

Parity proven:

- Generated contract deltas were limited to the approved direct-rule additions, reverse direct-rule removal, `runtimeRuleExceptions` reduction from 2 to 0, and the resulting compatibility-rule count change from 140 to 141.
- Local browser/runtime proof showed FE2 selected first leaves Z51 clickable; selecting Z51 removes FE1/FE2; FE3 remains auto-added; FE1/FE2 disabled reasons match the retired exceptions; and no Stingray runtime exceptions are emitted.

Next implementation candidate:

- `runtime_rule_exceptions` has no remaining active rows. The next architecture-risk surface in this report is variant override semantics, not another runtime-rule-exception retirement pass.

## Pass 16 completed report-only classification:

Pass 16 classified the active variant override sheets before any row migration, schema change, generator change, or test rewrite.

Report created:

- `docs/audit-cleanup/pass-16-variant-override-sheet-semantics-report.md`

What the report proved:

- `variant_option_overrides` has 7 consumed Stingray rows. Its `active` column is an emitted override value, not row activation, so the four `active=False` UQT rows are real behavior.
- `grandSport_variant_overrides` has 13 active model-scoped rows; `active` is row activation.
- `z06_variant_overrides` has 4 active model-scoped rows; `active` is row activation.
- UQT trim-scoped included-equipment behavior is not fully owned by OVS rows because the current override rows also carry selectability, `display_behavior=display_only`, and trim-standard `section_id` placement.
- Stingray/Grand Sport BC7 and Grand Sport NGA default-selected display metadata are better candidates for generator derivation from existing `default_selection_rules` plus exclusive groups.

## Pass 17 completed default-selected display metadata derivation:

Pass 17 implemented the first variant-override migration slice after the Pass 16 report.

Spec/closure updated:

- `docs/audit-cleanup/pass-17-default-selected-display-metadata-derivation-spec.md`

What the implementation changed:

- Added generator derivation for `display_behavior=default_selected` from existing `default_selection_rules` plus active single-selection exclusive groups.
- Guarded derivation to the approved row class only: Stingray `default_bc7`, Grand Sport `gs_default_bc7_coupe`, and Grand Sport `gs_default_nga_unless_nwi`.
- Deleted only redundant Stingray BC7 and Grand Sport BC7/NGA rows from variant override sheets.
- Preserved UQT rows in `variant_option_overrides`, `grandSport_variant_overrides`, and `z06_variant_overrides`.
- Proved timestamp-normalized generated parity plus browser/runtime BC7/NGA/UQT behavior.

Next implementation candidate:

- If continuing this cleanup track, spec UQT source ownership for trim-standard placement/selectability. Do not delete remaining variant override rows until the source model for selectability, display-only behavior, and per-variant section placement is explicitly chosen.

Original report validation run before implementation passes:

- Read-only probes only:
  - git status --short and branch check: branch schema-ingestion-normalization; no status output.
  - Lock-file check: LOCKFILE_ABSENT.
  - openpyxl.load_workbook(..., read_only=True, data_only=True) workbook inspection only.
  - Read-only generated runtime contract JSON inspection.
  - Repo searches and file reads.
- Generators/tests: not run.
- Workbook writes: none.
- Runtime/generator/test/docs edits: none.
- Generated artifact refresh: none.

Context note:

- Root codex-context.md was not present in the repo. archive-2026-05-29/codex-context.md is retired historical context and should not be used for current guidance. Current guidance should come from AGENTS.md plus live repo/workbook evidence.
