Prompt: Perform an audit of the codespace to determine from the data shape and schema that would need to be created with the raw order guide data so that the remaining Corvette models, Z06, ZR1, and ZR1X can have their data added to the form without great complexity. I know that they'll all need the numerous sheets that stingray and grandsport each have, and they would all use LZ interiors. Luckily a lot of the compatibility rules and color combinations are identical across the board so a lot of that can be copied, but look at the data as it sits in the workbook and then how it is processed for the form to runtime and let's work out the best way to process the order guide data for these models

Response #1: **Audit Verdict**
Report-only audit completed. I did not edit the workbook, scripts, tests, generated sheets, `form-output`, or `form-app`.

The lowest-complexity path is not to hand-build runtime data for Z06, ZR1, and ZR1X. The path should be:

`raw order guide sheets -> normalized model source sheets -> model draft generator -> registry promotion`

The current workbook is already close to supporting that. The key gap is that the code is still wired around two known models, while the workbook has enough metadata concepts to describe more.

**What The Current Data Says**

- `variant_master` already contains inactive rows for Z06, ZR1, and ZR1X.
- Z06 has 6 LZ variants: `1lz_h07`, `2lz_h07`, `3lz_h07`, `1lz_h67`, `2lz_h67`, `3lz_h67`.
- ZR1 and ZR1X each have 4 variants: 1LZ/3LZ coupe/convertible.
- Hidden archived sheets already exist: `archive_Z06_Ingest`, `archive_ZR1_Ingest`, `archive_ZR1X_Ingest`.
- `LZ_Interiors` exists and is schema-compatible with `lt_interiors`, with 132 rows and trims `1LZ`, `2LZ`, `3LZ`, `3LZ_R6X`.
- The archived raw export confirms the source shape: Z06 is sheet suffix `3`; ZR1 and ZR1X are combined in suffix `4` sheets and must be split by variant columns.

**Schema To Create**
For each new model, create the same source role set Grand Sport uses:

- `<model>_options`: same headers as `grandSport_options`.
- `<model>_ovs`: one row per `option_id` x `variant_id`.
- `<model>_rule_mapping`
- `<model>_price_rules`
- `<model>_rule_groups`
- `<model>_rule_group_members`
- `<model>_exclusive_groups`
- `<model>_exclusive_members`
- `<model>_variant_overrides` if duplicate/canonical option rows need model/trim-specific suppression.

Also add metadata rows in:

- `model_master`
- `model_workbook_sources`
- `model_variants`
- `runtime_steps`
- `context_section_master`
- `section_presentation`
- `model_interior_scope`
- `interior_components`
- `asset_map`

The important thing: do not duplicate `LZ_Interiors` per model. Use `LZ_Interiors` as the shared interior source, then scope rows per model through `model_interior_scope`.

**Best Processing Approach**

1. Parse raw `Interior`, `Exterior`, `Mechanical`, and `Standard Equipment` sheets into a normalized staging matrix.
   Use the raw row 1 family label, row 2 legend, and row 3 variant headers. ZR1/ZR1X suffix `4` sheets need family splitting by column prefix.

2. Emit model options and OVS rows.
   `*_options` owns identity, display text, section, selectability, active flag, and display behavior. `*_ovs` owns availability by concrete variant.

3. Treat Standard Equipment as status, not a separate business model.
   It should become `status=standard` in OVS and let the generator build `standardEquipment`.

4. Generate rules from `detail_raw`, then review.
   The existing parser vocabulary in [scripts/build_grand_sport_rule_sources.py](/Users/seandm/Projects/27vette/scripts/build_grand_sport_rule_sources.py:55) is the right pattern. Keep `includes` and `Included with` direction-sensitive; do not mirror package/component rules.

5. Copy compatibility only after ID resolution.
   Shared compatibility can be copied from Stingray/Grand Sport only when source and target `option_id`s resolve in the target model and the source availability scope matches. Otherwise generate a review row.

6. Price from the price schedule as a separate pass.
   Simple same-RPO prices can become option `price`. Contextual rows like trim-only, model-only, body-only, standard-with-interior, or same-RPO different price should become scoped `*_price_rules`.

7. Promote through a generic model generator.
   Today [scripts/corvette_form_generator/model_configs.py](/Users/seandm/Projects/27vette/scripts/corvette_form_generator/model_configs.py:150) defines only Stingray and Grand Sport, and [scripts/generate_stingray_form.py](/Users/seandm/Projects/27vette/scripts/generate_stingray_form.py:219) hardcodes the registry composition. That should become metadata-driven before adding three more live models.

**Main Blockers**

- The generator model list is not generic yet. `ModelConfig` can describe more models, but there is no generic “load every active model from workbook metadata” path.
- Grand Sport generation still writes draft/inspection artifacts through [scripts/generate_grand_sport_form.py](/Users/seandm/Projects/27vette/scripts/generate_grand_sport_form.py:35), while production registry writing is in the Stingray entrypoint.
- Interior generation for Grand Sport currently reads `lt_interiors` directly in [scripts/corvette_form_generator/inspection.py](/Users/seandm/Projects/27vette/scripts/corvette_form_generator/inspection.py:468). LZ models need that source sheet to become model-configurable.
- Schema validation is hardcoded to Stingray/Grand Sport sheet pairs in [scripts/corvette_form_generator/schema_validation.py](/Users/seandm/Projects/27vette/scripts/corvette_form_generator/schema_validation.py:51). It should validate active `model_workbook_sources` rows instead.
- Runtime vehicle setup highlight copy is hardcoded for two models in [form-app/app.js](/Users/seandm/Projects/27vette/form-app/app.js:104). New models will render with fallback copy unless this moves into workbook/registry metadata.

**Recommended Next Step**
The clean next implementation pass is a spec for a generic `generate_model_form.py` path that can accept a workbook-backed `model_key`, produce the same draft contract Grand Sport produces, and later let the registry writer include all active/promoted models. Keep raw order guide ingestion separate from runtime promotion.

Validation run: `.venv/bin/python scripts/validate_workbook_schema.py stingray_master.xlsx` passed with `0` issues.

Generators/tests not run because this was report-only and the generators write workbook/artifact outputs.

Prompt #2: Run the same audit on the workbook as well as the runtime code because my layout updates were knowingly performed outside of the workspace guidelines so I need a review of schema repeatability with paths to fix issues and a list of hardcoded "business rules" or variant specific information that should be workbook owned so that i can begin the process of making said preparations.

**Verdict**
The workbook is valid, but the current pipeline is only partially repeatable. Stingray and Grand Sport have a normalized shape; Z06, ZR1, and ZR1X are still archive/source material, not active model-owned data. The biggest blocker is not the raw order guide shape. It is the remaining two-model assumptions in validation, generation, registry promotion, interiors, and a few runtime presentation/business exceptions.

**Findings**

1. **P1: Schema validation is hardcoded to Stingray and Grand Sport.**
   [schema_validation.py](/Users/seandm/Projects/27vette/scripts/corvette_form_generator/schema_validation.py:13) explicitly names `stingray_*` and `grandSport_*` sheets in boolean/price/RPO checks, required sheets, header pairs, and OVS validation.
   Fix path: make validation derive active models and source-role sheets from `model_master`, `model_workbook_sources`, and `model_variants`.

2. **P1: App data promotion is two-model only.**
   [generate_stingray_form.py](/Users/seandm/Projects/27vette/scripts/generate_stingray_form.py:197) only loads a Grand Sport draft beside Stingray, and [line 219](/Users/seandm/Projects/27vette/scripts/generate_stingray_form.py:219) builds a registry with Stingray plus maybe Grand Sport.
   Fix path: extract a generic active-model registry builder that loops promoted model configs/data artifacts instead of naming Grand Sport.

3. **P1: LZ interiors exist but are not wired as a repeatable source.**
   Workbook has hidden `LZ_Interiors` with the same 132-row shape as `lt_interiors`, but `model_interior_scope` only has `grand_sport:132`, and `interior_components` only has `stingray`/`grand_sport`. [inspection.py](/Users/seandm/Projects/27vette/scripts/corvette_form_generator/inspection.py:468) reads `lt_interiors` directly and falls back to LT trims at [line 499](/Users/seandm/Projects/27vette/scripts/corvette_form_generator/inspection.py:499).
   Fix path: add an interior source role/config field, add Z06/ZR1/ZR1X rows to `model_interior_scope` and `interior_components`, and emit source sheet / active flags generically.

4. **P1: Runtime contains model-specific presentation/business facts.**
   [app.js](/Users/seandm/Projects/27vette/form-app/app.js:104) hardcodes Stingray and Grand Sport setup highlights, including LS6, horsepower, Magnetic Ride, Z52, etc.
   Fix path: add workbook-owned model presentation metadata, or extend `model_master`/`asset_map`, emit it into each registry model entry, and have `activeModelHighlight()` read generated data.

5. **P1: One explicit runtime business exception remains in JS.**
   [app.js](/Users/seandm/Projects/27vette/form-app/app.js:868) special-cases `choice.rpo === "GBA"` and `rule.source_id === "opt_zyc_001"`.
   Fix path: move this to `runtime_rule_exceptions` or normalize the source rule so runtime only evaluates generated rule metadata.

6. **P2: Order summary metadata is only workbook-owned for Stingray.**
   Workbook `order_summary_sections` has `stingray:11`; `step_order_summary_map` has `stingray:13`. Runtime falls back to hardcoded definitions at [app.js](/Users/seandm/Projects/27vette/form-app/app.js:132) and [line 147](/Users/seandm/Projects/27vette/form-app/app.js:147).
   Fix path: add shared/per-model rows for every model and require generated `data.orderSummary` for all promoted models.

7. **P2: Grand Sport inspection/draft scripts are not generic enough for the next models.**
   [model_configs.py](/Users/seandm/Projects/27vette/scripts/corvette_form_generator/model_configs.py:150) only defines `STINGRAY_MODEL` and `GRAND_SPORT_MODEL`; [inspection.py](/Users/seandm/Projects/27vette/scripts/corvette_form_generator/inspection.py:1731) emits Grand Sport-specific validation messages; [build_grand_sport_rule_sources.py](/Users/seandm/Projects/27vette/scripts/build_grand_sport_rule_sources.py:14) imports `GRAND_SPORT_MODEL` directly.
   Fix path: create generic `generate_model_form.py` / `build_model_rule_sources.py` driven by `ModelConfig` plus workbook metadata.

**Workbook Shape**
Current workbook status:

- `model_master`: only `stingray`, `grand_sport`.
- `model_workbook_sources`: `stingray:9`, `grand_sport:10`.
- `model_variants`: `stingray:6`, `grand_sport:6`.
- `archive_Z06_Ingest`, `archive_ZR1_Ingest`, `archive_ZR1X_Ingest` exist hidden with normalized ingest-like headers.
- `LZ_Interiors` exists hidden and matches `lt_interiors` headers.
- No active workbook metadata yet for Z06/ZR1/ZR1X sources, runtime steps, presentation, assets, interior scope, summary sections, or rule exceptions.

**Recommended Prep Order**

1. Add inactive/active metadata rows for Z06, ZR1, ZR1X in `model_master`, `model_workbook_sources`, and `model_variants`.
2. Promote archive ingest sheets into normalized source sheets matching `grandSport_options` / `grandSport_ovs` shape.
3. Add LZ interior scope/components for the three models before touching runtime.
4. Generalize validator/generator/model registry loops.
5. Move runtime hardcodes into workbook-backed metadata, starting with model highlights and the `GBA` exception.

**Gates**
No files were changed. I ran:

- `git status --short && git diff --stat` → clean output.
- `.venv/bin/python scripts/validate_workbook_schema.py stingray_master.xlsx` → `status: valid`, `issue_count: 0`.

Manual verification still pending: none of the archive Z06/ZR1/ZR1X rows were promoted or regenerated, and I did not run mutating generators because this was an audit-only pass.
