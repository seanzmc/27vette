# Findings

## Ordered by Architecture Risk

### Highest risk

1. Runtime_rule_exceptions is still an active segregated runtime behavior surface, reduced by Pass 14.
   - Current state after Pass 14: 2 rows / 2 active, all model_key=stingray.
   - Active rows:
     - ex_z51_fe1: opt_z51_001 removes opt_fe1_001
     - ex_z51_fe2: opt_z51_001 removes opt_fe2_001
   - Current consumers:
     - scripts/corvette_form_generator/runtime_metadata.py:283
     - scripts/corvette_form_generator/production.py:180, emitted at production.py:625
     - form-app/app.js:626-668, form-app/app.js:1004-1019
     - Tests pin the current rows and the retired GBA/ZYC canonical owner in tests/stingray-form-regression.test.mjs:1824-1869, 2305-2351
   - This sheet is workbook-owned, but not proven canonical. It owns exception behavior that plausibly belongs in normal rule/default/group ownership.
   - ex_nwi_nga is not present in current workbook evidence and is correctly not treated as open.
   - Retired canonical candidate:
     - ex_gba_zyc: Pass 14 moved this behavior to Stingray rule_groups / rule_group_members as excludes_any from GBA to ZYC and removed the reverse direct rule opt_zyc_001 excludes opt_gba_001 after generated-data and browser/runtime parity proof.
   - Remaining likely canonical candidates:
     - ex_z51_fe1 / ex_z51_fe2: suspension/default ownership, likely involving rule_mapping, exclusive_groups, and default_selection_rules.default_fe1. Current workbook already has default_fe1 and Z51 includes FE3, but no normal group/row currently owns “selecting Z51 removes FE1/FE2” without the exception sheet.
   - Any remaining migration requires workbook-source changes and generated-contract/runtime parity proof.

### Medium-high risk

1. Variant override behavior is split across three sheet contracts with different active semantics.
   - variant_option_overrides: 7 rows; raw active=True count is 3, but the loader treats all 7 rows as sourced override rows because this sheet’s active column is an override value, not row activation (runtime_metadata.py:237-245).
   - grandSport_variant_overrides: 13 rows / 13 active, conventional row activation.
   - z06_variant_overrides: 4 rows / 4 active, conventional row activation.
   - Current consumers:
     - runtime_metadata.py:232-276
     - production.py:194-200, 326-339
     - inspection.py:286-302, 646-664, 714-725
     - schema/type guards in schema_validation.py:42-45
     - tests in stingray-generator-stability.test.mjs:400-417, workbook-schema-standardization.test.mjs:50-57, 86-89, 185-187
   - Current behavior carried:
     - Stingray variant_option_overrides: UQT unavailable override for 2LT/3LT rows; BC7 coupe default_selected.
     - Grand Sport overrides: UQT display-only standard rows for 2LT/3LT; BC7 coupe default_selected; NGA all-variant default_selected.
     - Z06 overrides: UQT display-only standard rows for 2LZ/3LZ.
   - This is not safe to delete just because it looks redundant. It currently changes emitted choice status, selectable, active, display_behavior, and sometimes section_id.
   - Likely canonical candidates:
     - Default-selected BC7/NGA behavior: default_selection_rules plus exclusive groups, if generator/runtime can derive emitted choice display metadata from those normal owners.
     - UQT trim display-only behavior: existing option/status rows plus model/variant metadata or standard-equipment presentation metadata. Current \*\_ovs sheets only carry status, so moving selectable, display_behavior, or per-variant section_id likely requires generator/schema work unless the source option rows are remodeled.
   - Migration requires generator changes for at least some rows.

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

Sheet: runtime_rule_exceptions — 2 rows / 2 active after Pass 14; coverage stingray:2; keys model_key, exception_id, source_option_id, target_option_id, exception_type,
scopes, disabled_reason, active
Current consumer(s): runtime_metadata.py:283; production.py:180,625; form-app/app.js:626-668,1004-1019;
stingray-form-regression.test.mjs:1824-1869,2309-2351
Current behavior/data ownership: Exception behavior. Removes/disables selected targets via generated runtimeRuleExceptions. Current active rows are
ex_z51_fe1 and ex_z51_fe2. Pass 14 retired ex_gba_zyc into rule_groups.grp_gba_excludes_zyc plus rule_group_members.
Canonical-owner candidate: Existing workbook owners: rule_mapping, rule_groups/members, exclusive_groups/members, default_selection_rules, option rows.
Risk level: High
Recommended next action: Migrate/classify the remaining Z51/FE1/FE2 suspension/default behavior as a separate behavior class, or defer if normal ownership cannot prove parity.
Required parity gates: Future pass: regenerate affected model + registry; strict generated-contract diff with approved deltas; node --test
tests/stingray-form-regression.test.mjs; node --test tests/multi-model-runtime-switching.test.mjs; local browser/runtime proof for the specific remaining behavior.
────────────────────────────────────────
Sheet: variant_option_overrides — 7 rows; raw active=True count 3 but loader consumes all 7; coverage stingray:7; keys model_key, option_id, variant_id,
status, selectable, active, display_behavior, notes
Current consumer(s): runtime_metadata.py:232-276; production.py:194-200,326-339; tests in stingray-generator-stability.test.mjs
Current behavior/data ownership: Override behavior. For Stingray, UQT rows use active=False as emitted override value; BC7 coupe rows set
display_behavior=default_selected.
Canonical-owner candidate: UQT: option rows / OVS / possibly variant metadata. BC7 default: default_selection_rules + exclusive group, if generator derives
choice display metadata from defaults.
Risk level: Medium-high
Recommended next action: Consolidate candidate, not delete. First clarify row activation semantics if this sheet remains.
Required parity gates: Future pass: Stingray generator + registry; generated choice parity for UQT and BC7; stingray-generator-stability.test.mjs;
stingray-form-regression.test.mjs; browser/default replay checks.
────────────────────────────────────────
Sheet: grandSport_variant_overrides — 13 rows / 13 active; coverage Grand Sport sheet-scoped; keys option_id, variant_id, selectable, display_behavior,
section_id, active, note
Current consumer(s): Same loader via model_workbook_sources.variant_option_overrides_sheet; inspection.py draft/runtime path;
grand-sport-runtime-contract.json
Current behavior/data ownership: Override behavior. UQT 2LT/3LT display-only standard rows; BC7 coupe default-selected; NGA all variants default-selected.
Canonical-owner candidate: Defaults: default_selection_rules + exclusive groups. UQT trim/section behavior: model/variant metadata or source option/status
remodeling; may need generator changes.
Risk level: Medium-high
Recommended next action: Consolidate candidate, after Stingray/global override semantics are clarified.
Required parity gates: Future pass: generate_form.py --model grand_sport, registry, grand-sport-contract-preview.test.mjs, grand-sport-draft-data.test.mjs,
runtime/browser checks for UQT, BC7, NGA.
────────────────────────────────────────
Sheet: z06_variant_overrides — 4 rows / 4 active; coverage Z06 sheet-scoped; keys same as Grand Sport
Current consumer(s): Same loader via model_workbook_sources; inspection.py; Z06 runtime contract/tests
Current behavior/data ownership: Override behavior. UQT 2LZ/3LZ display-only standard rows.
Canonical-owner candidate: Likely source option/status plus standard-equipment presentation metadata, but current z06_ovs cannot carry selectable,
display_behavior, or section_id.
Risk level: Medium
Recommended next action: Needs more evidence before migration. Do not migrate Z06 replacement behavior under this pass.
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
Sheet: model_workbook_sources — 52 rows / 32 active; active roles: Stingray 10, Grand Sport 11, Z06 11; inactive ZR1/ZR1X roles; keys model_key,
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

- The remaining `runtime_rule_exceptions` rows are the Z51/FE1/FE2 suspension/default behavior (`ex_z51_fe1`, `ex_z51_fe2`). Treat them as a separate spec-first pass because they involve default/standard suspension ownership, not paint/accent conflict behavior.

Validation run for this audit:

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
