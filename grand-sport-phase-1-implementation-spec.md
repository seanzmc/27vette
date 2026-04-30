# Grand Sport Phase 1 Source Inventory And Phase 2 Spec

Date: 2026-04-29

## Phase 1 Scope

Approved scope was source inventory and concrete Phase 2 planning only. No runtime behavior, app UI, export schema, Formidable wiring, final Grand Sport data generation, Grand Sport rules, EL9/Z25/FEY/Z15 behavior, or Stingray behavior was changed.

Temporary read-only workbook inspection was done with scratch scripts outside the repo. No generator scaffolding was added to the repository in Phase 1 because the current source was concrete enough to write the Phase 2 implementation plan without touching code.

## Stingray Baseline Gate Results

Before Phase 1 document work:

| Command | Result |
| --- | --- |
| `.venv/bin/python scripts/generate_stingray_form.py` | PASS: `validation_errors: 0`, `choices: 1548`, `standard_equipment: 464`, `rules: 238`, `price_rules: 43`, `interiors: 130` |
| `node --test tests/stingray-form-regression.test.mjs` | PASS: 53 tests, 0 failures |

The generator does refresh timestamps in `form-app/data.js`, `form-output/stingray-form-data.json`, and `stingray_master.xlsx`; that is existing Stingray behavior and not a Grand Sport implementation change.

## Source Inventory Results

### Workbook Sources

| Source | Rows | Phase 1 finding |
| --- | ---: | --- |
| `variant_master` | 32 | Contains the six Grand Sport variants as inactive rows. |
| `grandSport` | 269 | Main Grand Sport option/status matrix; all 269 rows have unique `option_id`s and 223 unique RPOs. |
| `section_master` | 37 | Contains all nonblank Grand Sport section IDs, including GS-specific sections. |
| `lt_interiors` | 132 | Regular Grand Sport should use LT interiors; includes Grand Sport-only EL9 rows. |
| `LZ_Interiors` | 132 | Present, but for LZ-family models; not for regular Grand Sport. |
| `color_overrides` | 245 | Includes eight EL9/D30 rows for LT EL9 interiors. |
| `PriceRef` | 20 | Contains component prices: 14 Seat, 3 Stitching, 2 Suede, 1 TwoTone. |
| `rule_mapping` | 238 | Current sheet is Stingray-oriented; do not reuse as Grand Sport truth. |
| `price_rules` | 36 | Current sheet is Stingray/interior-price-rule oriented; reuse structure, not every row blindly. |
| archived raw order guide | n/a | `archived/referenceSheets/2027 Chevrolet Car Corvette Export copy.xlsx` has Grand Sport raw sheets: `Standard Equipment 2`, `Interior 2`, `Exterior 2`, `Mechanical 2`. |

### Confirmed Grand Sport Variants

| variant_id | model_year | body_style | trim_level | display_name | base_price | active now |
| --- | ---: | --- | --- | --- | ---: | --- |
| `1lt_e07` | 2027 | coupe | 1LT | Corvette Grand Sport Coupe 1LT | 88495 | False |
| `2lt_e07` | 2027 | coupe | 2LT | Corvette Grand Sport Coupe 2LT | 95595 | False |
| `3lt_e07` | 2027 | coupe | 3LT | Corvette Grand Sport Coupe 3LT | 100245 | False |
| `1lt_e67` | 2027 | convertible | 1LT | Corvette Grand Sport Convertible 1LT | 95495 | False |
| `2lt_e67` | 2027 | convertible | 2LT | Corvette Grand Sport Convertible 2LT | 102595 | False |
| `3lt_e67` | 2027 | convertible | 3LT | Corvette Grand Sport Convertible 3LT | 107245 | False |

Do not mutate `active` globally in Phase 2. The generator should select variants through model config.

### Grand Sport Status Counts

| variant_id | Available | Standard | Not Available |
| --- | ---: | ---: | ---: |
| `1lt_e07` | 142 | 79 | 48 |
| `2lt_e07` | 150 | 97 | 22 |
| `3lt_e07` | 153 | 98 | 18 |
| `1lt_e67` | 137 | 78 | 54 |
| `2lt_e67` | 144 | 96 | 29 |
| `3lt_e67` | 147 | 97 | 25 |

Selectable source values:

| Selectable | Rows |
| --- | ---: |
| `yes` | 167 |
| `no` | 102 |

Category row counts:

| Category | Rows |
| --- | ---: |
| `cat_exte_001` | 98 |
| `cat_stan_001` | 66 |
| `cat_inte_001` | 47 |
| `cat_equi_001` | 29 |
| `cat_mech_001` | 29 |

## Grand Sport Contract Mapping Table

| `grandSport` column | Existing generated surface | Field mapping | Notes |
| --- | --- | --- | --- |
| `option_id` | `choices`, `standardEquipment`, `rules`, `priceRules` | `option_id`; `choice_id = <variant_id>__<option_id>` | All current Grand Sport option IDs are unique. Keep canonicalization support for known duplicate RPO cases, but do not alias unless required. |
| `RPO` | `choices`, exports | `rpo` | Multiple option IDs may share an RPO, e.g. visible/selectable plus standard duplicate rows. Existing de-dupe/runtime ranking patterns matter. |
| `Price` | `choices`, `priceRules`, exports | `base_price = money(Price)` | Blank means 0 for display/export unless option is unavailable. Validate package-included price overrides later. |
| `Option Name` | `choices`, exports | `label` | Preserve source wording. |
| `Description` | `choices`, exports | `description` | Preserve source wording. |
| `Detail` | `choices`, `rules`, `ruleGroups`, `exclusiveGroups`, `validation` | `source_detail_raw`; rule extraction source | Grand Sport has 36 rows with `Requires`, 47 with `Not available`, 17 with `Included with`, 10 with `Includes`, 11 with `only available`. Do not parse all rules in Phase 2 unless explicitly scoped. |
| `Category` | `choices`, `sections` | `category_id` | Must resolve through `category_master`. All populated category IDs are known. |
| `Selectable` | `choices` | `selectable = "True"` for `yes`, `"False"` for `no` | Match existing generated boolean string convention. |
| `Section` | `choices`, `sections`, `standardEquipment`, order recap | `section_id`, then section-derived fields | Three rows are blank and need normalization: `PCQ`, `PDY`, `PEF`. |
| `1lt_e07` to `3lt_e67` | `choices`, `standardEquipment` | one generated choice per option per configured variant, `status = available/standard/unavailable` | Use exact variant IDs from `variant_master`. |

## Required Section Mapping

Most Grand Sport sections can reuse existing section-to-step logic. The following sections need explicit Phase 2 attention:

| Section | Rows | Current derived step | Phase 2 action |
| --- | ---: | --- | --- |
| blank | 3 | needs investigation | Normalize `PCQ` to exterior/LPO, `PDY` and `PEF` to interior/LPO before generation. |
| `sec_gsce_001` GS Center Stripes | 5 | `exterior_appearance` | Make this explicit in model config so future generic logic does not move it accidentally. |
| `sec_gsha_001` GS Hash Marks | 6 | `exterior_appearance` | Make explicit; needed by Z15 rule group and hash-mark paint exclusions. |
| `sec_spec_001` Special Edition | 1 | `packages_performance` | Make explicit; owns Z25 Launch Edition. |
| `sec_colo_001` Color Override | 2 | `interior_trim` | Keep display-only/auto-only behavior consistent with D30 handling. |
| `sec_cust_002` Custom Stitch | 3 | `interior_trim` | Current Stingray hides this as manually selectable. Confirm Grand Sport wants component-line handling, not selectable cards. |

Specific blank section rows:

| RPO | Option | Current category | Recommended section |
| --- | --- | --- | --- |
| `PCQ` | LPO, Grille Screen Protection Package | `cat_exte_001` | `sec_lpoe_001` |
| `PDY` | LPO, Roadside Safety Package | `cat_inte_001` | `sec_lpoi_001` |
| `PEF` | LPO, Contoured Liner Protection Package | `cat_inte_001` | `sec_lpoi_001` |

## Required Model-Specific Config Fields

Phase 2 should introduce a model config object rather than more top-level Stingray constants.

Required config fields:

| Field | Grand Sport value / purpose |
| --- | --- |
| `model_key` | `grand_sport` |
| `model_label` | `Grand Sport` |
| `dataset_name` | `2027 Corvette Grand Sport operational form` |
| `source_option_sheet` | `grandSport` |
| `option_header_map` | maps `RPO`, `Price`, `Option Name`, `Description`, `Detail`, `Category`, `Selectable`, `Section` to canonical names |
| `variant_ids` | `1lt_e07`, `2lt_e07`, `3lt_e07`, `1lt_e67`, `2lt_e67`, `3lt_e67` |
| `expected_variant_count` | 6 |
| `trim_levels` | `1LT`, `2LT`, `3LT` |
| `body_styles` | `coupe`, `convertible` |
| `variant_id_suffixes` | `e07`, `e67` or explicit ID list; prefer explicit ID list |
| `section_step_overrides` | at minimum GS center stripes, GS hash marks, Special Edition, Color Override |
| `section_display_order_overrides` | current shared overrides plus GS section order decisions |
| `section_mode_overrides` | current shared spoiler override only if needed; otherwise source section modes |
| `standard_sections` | same standard/display section set unless GS source adds more |
| `hidden_option_ids` | start from shared hidden set, then confirm GS-specific visibility |
| `hidden_section_ids` | likely `sec_cust_002`, if custom stitch remains component-only |
| `auto_only_option_ids` | `opt_r6x_001` if present in source; do not assume until mapped |
| `display_only_option_ids` | `opt_d30_001` and any GS display-only rows |
| `option_id_aliases` | engine-cover aliases if GS duplicates must be collapsed; inspect before applying |
| `manual_rules` | only the minimum approved GS rules in later phases; not Phase 2 unless scaffolding only |
| `rule_groups` | Z15 hash-mark requirement later; scaffold shape in Phase 2 |
| `exclusive_groups` | shared cover/engine groups plus GS graphics groups later; scaffold shape in Phase 2 |
| `price_rule_injections` | D30/R6X, engine-cover package pricing, package-included zeroing later |
| `interior_source` | `lt_interiors` for regular Grand Sport |
| `active_interior_predicate` | LT trims including Grand Sport-only EL9 rows; excludes LZ |
| `interior_reference_path` | likely new `architectureAudit/grand_sport_interiors_refactor.csv` or model-scoped shared reference |
| `validation_expectations` | expected variants, status rows, nonblank section coverage, active interior coverage |
| `output_prefix` | do not overwrite Stingray outputs in Phase 2 unless explicitly approved |

## Generator Logic To Become Shared

Move these from `scripts/generate_stingray_form.py` into shared generator code:

- workbook reading helpers: `clean`, `money`, `intish`, `rows_from_sheet`
- sheet writing helper: `write_sheet`
- generated sheet list and output serialization shape
- `STEP_ORDER`, `STEP_LABELS`, `CONTEXT_SECTIONS` unless model context is added later
- status normalization and status labels
- selection mode label and `choice_mode` normalization
- generic `step_for_section(section_id, section_name, category_id, config)`
- context choice generation for body style and trim
- option row normalization from a model-specific source sheet
- choice generation from model variants and option statuses
- standard equipment generation
- rule serialization shape for `includes`, `requires`, `excludes`, `runtime_action`
- `ruleGroups` and `exclusiveGroups` serialization shape
- `priceRules` serialization shape
- color override serialization shape
- interior component metadata for seats, R6X, stitching, suede, and two-tone
- interior grouping fields from a model-specific reference CSV
- validation row construction and validation summary
- JSON/CSV export generation and `form-app/data.js` writing, but with output target controlled by config

## Logic To Remain Stingray-Specific

Keep these in the Stingray model config or Stingray entrypoint:

- source option sheet `stingray_master`
- active variant IDs `1lt_c07` through `3lt_c67`
- dataset name `2027 Corvette Stingray operational form`
- Stingray expected output counts where tests assert them
- current Stingray `OPTION_ID_ALIASES` unless GS proves the same duplicate contract
- current Stingray `CONSOLIDATED_ENGINE_COVERS` price normalization if the GS source rows need different handling
- `HIDDEN_OPTION_IDS` choices for BC4/BCP/BCS/BC7 duplicates, N26/TU7, and ZF1
- `HIDDEN_SECTION_IDS = {"sec_cust_002"}` if Grand Sport custom stitch is not yet approved to hide the same way
- `UQT` 1LT-only correction if it is Stingray-specific after GS inspection
- current `FIVE_V7_OR_REQUIREMENT_TARGET_IDS`, `FIVE_ZU_OR_REQUIREMENT_TARGET_IDS`, and `T0A_REPLACEMENT_OPTION_IDS`
- current Stingray `RULE_GROUPS`
- current Stingray `EXCLUSIVE_GROUPS` until proven shared
- current Stingray manual rules for T0A/Z51, TVS/T0A, BC7/ZZ3, R6X includes
- current validation message wording that says “active Stingray variants”
- `active_for_stingray` interior field name; shared code should produce a model-neutral active flag while the Stingray output remains backward compatible
- current output targets: `form-output/stingray-form-data.*` and `form-app/data.js`

## Recommended Generator Architecture

Use a shared core with model-specific entrypoints. Do not clone the full generator as a maintained file.

Proposed shape:

```text
scripts/
  generate_stingray_form.py
  generate_grand_sport_form.py
  corvette_form_generator/
    __init__.py
    workbook_io.py
    model_config.py
    pipeline.py
    interiors.py
    rules.py
    validation.py
```

Phase 2 should focus on extraction without changing Stingray output:

1. Move pure helpers and static shared surfaces into `corvette_form_generator`.
2. Create a `ModelConfig` data structure.
3. Express Stingray as a config and keep `generate_stingray_form.py` behavior/output stable.
4. Add a Grand Sport config file or object, but do not emit final Grand Sport app data yet unless the Phase 2 approval explicitly asks for a dry-run artifact.
5. Keep all current Stingray tests passing.

Output safety:

- Phase 2 should not write Grand Sport into `form-app/data.js`.
- If a dry run is needed, write to a sandboxed inspection path such as `form-output/grand-sport-draft-data.json` only after approval.
- Keep workbook mutation limited to current Stingray generator behavior until a Grand Sport output target is approved.

## Exact Files Proposed For Phase 2

Primary code files:

- `scripts/corvette_form_generator/__init__.py`
- `scripts/corvette_form_generator/model_config.py`
- `scripts/corvette_form_generator/workbook_io.py`
- `scripts/corvette_form_generator/pipeline.py`
- `scripts/corvette_form_generator/interiors.py`
- `scripts/corvette_form_generator/rules.py`
- `scripts/corvette_form_generator/validation.py`
- `scripts/generate_stingray_form.py`
- `scripts/generate_grand_sport_form.py`

Configuration/reference files:

- `architectureAudit/grand_sport_interiors_refactor.csv` or a model-scoped extension of `architectureAudit/stingray_interiors_refactor.csv`
- optional `scripts/corvette_form_generator/model_configs.py` if configs are kept in Python rather than separate JSON/YAML

Tests:

- `tests/stingray-form-regression.test.mjs` should continue to pass unchanged initially.
- Add `tests/grand-sport-generator-contract.test.mjs` only after a Grand Sport draft output exists.
- Consider extracting common test loader helpers to `tests/helpers/form-runtime.mjs` only when duplication appears.

Docs:

- Update `grand-sport-phase-1-implementation-spec.md` or create `grand-sport-phase-2-results.md` after Phase 2.
- Do not update README until Grand Sport generation is actually usable.

## Phase 2 Implementation Spec

### Diagnosis

The current generator is functionally correct for Stingray but hardcodes the model at several layers: source sheet, active variant filter, dataset name, interior activation, hidden/auto/display-only option sets, rule groups, exclusive groups, manual rules, validation wording, and output paths. Grand Sport source data already exists, but adding it by modifying those constants in place would risk breaking the closed-out Stingray baseline.

Risk level: medium. The main risk is accidental Stingray output drift during generator extraction.

### Exact Files To Change

Phase 2 should change or add only:

- `scripts/generate_stingray_form.py`
- `scripts/generate_grand_sport_form.py`
- `scripts/corvette_form_generator/__init__.py`
- `scripts/corvette_form_generator/model_config.py`
- `scripts/corvette_form_generator/workbook_io.py`
- `scripts/corvette_form_generator/pipeline.py`
- `scripts/corvette_form_generator/interiors.py`
- `scripts/corvette_form_generator/rules.py`
- `scripts/corvette_form_generator/validation.py`
- optionally `architectureAudit/grand_sport_interiors_refactor.csv` if Phase 2 includes only reference scaffolding, not final interior behavior

Do not change:

- `form-app/app.js`
- `form-app/index.html`
- `form-app/styles.css`
- export schema
- Formidable wiring
- Grand Sport final generated app data

### Constraints

- Preserve exact Stingray runtime behavior and export schema.
- No UI redesign.
- No Grand Sport rule implementation beyond config placeholders unless separately approved.
- No final Grand Sport `form-app/data.js`.
- No global workbook row activation changes.
- Use `.venv/bin/python` for generator validation.
- Keep Phase 2 extraction small enough to review.

### Phase 2 Steps

1. Create shared generator package with pure helper extraction.
2. Add `ModelConfig` with Stingray config that reproduces current behavior.
3. Update `generate_stingray_form.py` to call the shared pipeline with Stingray config.
4. Run Stingray gates and compare output counts and generated JSON shape.
5. Add a Grand Sport config skeleton with source sheet, variants, section mappings, blank-section normalization, and validation expectations.
6. Add `generate_grand_sport_form.py` as a non-final dry-run entrypoint that either does not write app output or writes only to an explicitly approved draft path.
7. Stop before implementing Grand Sport rules, EL9/Z25/FEY/Z15 behavior, or runtime model context.

### Phase 2 Validation Plan

Run before and after changes:

```sh
.venv/bin/python scripts/generate_stingray_form.py
node --test tests/stingray-form-regression.test.mjs
```

Additional Phase 2 checks:

- `git diff -- form-app/data.js form-output/stingray-form-data.json` should show only expected timestamp churn after generator runs, unless approved extraction changes intentionally alter formatting.
- Run a read-only Grand Sport config inspection command if added; it must not overwrite Stingray outputs.
- Verify `variant_id`s remain unchanged for Stingray and Grand Sport.

## Risks

- The current generator mutates `stingray_master.xlsx` every time it runs; Phase 2 must avoid accidental Grand Sport workbook writes until output targets are approved.
- `form-app/app.js` still has hardcoded model identity and some RPO defaults. Grand Sport-only data can be inspected without runtime changes, but combined models need a model context.
- Grand Sport has compound rule text, especially `T0F requires FEY or FEB + J57`; current `requires_any` cannot express OR-of-AND without either simplification or rule vocabulary growth.
- `PCQ`, `PDY`, and `PEF` have blank source sections. If not normalized, generated step placement will be wrong or unstable.
- EL9 is intentionally inactive for Stingray and must become active only in Grand Sport. This requires model-scoped interior activation, not a shared blanket interior flag.
- Existing Stingray tests assert implementation details in places; Phase 2 should avoid test churn unless extraction changes names or structure.

## Next Implementation Prompt

Implement Phase 2 generator scaffolding only.

Scope:

- Extract shared generator helpers from `scripts/generate_stingray_form.py` into `scripts/corvette_form_generator/`.
- Add a `ModelConfig` structure.
- Re-express the current Stingray generator through the shared pipeline without changing Stingray behavior or output contract.
- Add a Grand Sport config skeleton covering source sheet `grandSport`, variants `1lt_e07` through `3lt_e67`, section mappings, blank-section normalization for `PCQ`/`PDY`/`PEF`, and validation expectations.
- Add `scripts/generate_grand_sport_form.py` only as a non-final dry-run/scaffold entrypoint. Do not write final Grand Sport app data.

Do not:

- change runtime behavior;
- change app UI;
- change export schema;
- wire Formidable;
- implement Grand Sport rules;
- implement EL9/Z25/FEY/Z15 behavior;
- overwrite `form-app/data.js` with Grand Sport data;
- break or modify Stingray output beyond unavoidable generated timestamps.

Required gates before and after:

```sh
.venv/bin/python scripts/generate_stingray_form.py
node --test tests/stingray-form-regression.test.mjs
```
