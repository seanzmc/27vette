# 27vette Configurator Architecture Audit

## Executive Summary

The current Stingray form is not safe to extend to other Corvette models as-is. The workbook-to-generated-data pipeline is headed in the right direction, and the runtime has reusable selection primitives, but too much model/option compatibility still lives as literal RPO logic in [form-app/app.js](/Users/seandm/Projects/27vette/form-app/app.js:228) and Stingray-specific normalization in [scripts/generate_stingray_form.py](/Users/seandm/Projects/27vette/scripts/generate_stingray_form.py:102). Adding Z06, E-Ray, ZR1, etc. on top of this would likely turn `app.js` into a growing pile of one-off fixes unless a small data-driven rule vocabulary is introduced.

## Current Data Flow

1. Source of truth is `stingray_master.xlsx`; docs explicitly say data changes belong in the workbook, while `form-app/data.js` is generated and should not be manually edited except as an emergency hotfix ([debug/workflow.md](/Users/seandm/Projects/27vette/debug/workflow.md:1), [App-refresh-workflow.md](/Users/seandm/Projects/27vette/App-refresh-workflow.md:7)).

2. [scripts/generate_stingray_form.py](/Users/seandm/Projects/27vette/scripts/generate_stingray_form.py:364) reads workbook sheets including `variant_master`, `category_master`, `section_master`, `stingray_master`, `option_variant_status`, `rule_mapping`, `price_rules`, `lt_interiors`, `LZ_Interiors`, and `color_overrides`.

3. The generator writes workbook `form_*` sheets, `form-output/stingray-form-data.json`, `form-output/stingray-form-data.csv`, and [form-app/data.js](/Users/seandm/Projects/27vette/form-app/data.js:1). The emitted data contract currently contains `variants`, `steps`, `sections`, `contextChoices`, `choices`, `standardEquipment`, `rules`, `priceRules`, `interiors`, `colorOverrides`, and `validation` ([scripts/generate_stingray_form.py](/Users/seandm/Projects/27vette/scripts/generate_stingray_form.py:1073)).

4. Runtime [form-app/app.js](/Users/seandm/Projects/27vette/form-app/app.js:39) indexes the generated arrays into maps, filters choices by current variant, evaluates rules, maintains selected/user-selected/interior state, renders steps, computes line items, and exports JSON/CSV order payloads ([form-app/app.js](/Users/seandm/Projects/27vette/form-app/app.js:894)).

## Current Runtime Rule Surface

Generic behaviors that should mostly stay in `app.js`:

- Variant-scoped filtering via `currentVariantId()`, `activeChoiceRows()`, and `choiceForCurrentVariant()` ([form-app/app.js](/Users/seandm/Projects/27vette/form-app/app.js:108)).
- Basic rule scope filtering through `ruleAppliesToCurrentVariant()` with `body_style_scope` and source/target availability checks ([form-app/app.js](/Users/seandm/Projects/27vette/form-app/app.js:117)).
- `includes` auto-add behavior, with suppression when a user has already chosen another single-select option in that section ([form-app/app.js](/Users/seandm/Projects/27vette/form-app/app.js:189)).
- `requires` and `excludes` disabled-state handling for options and interiors ([form-app/app.js](/Users/seandm/Projects/27vette/form-app/app.js:228), [form-app/app.js](/Users/seandm/Projects/27vette/form-app/app.js:268)).
- `priceRules` override evaluation ([form-app/app.js](/Users/seandm/Projects/27vette/form-app/app.js:283)).
- Single vs multi section selection behavior ([form-app/app.js](/Users/seandm/Projects/27vette/form-app/app.js:503)).
- Standard/included equipment grouping and variant filtering ([form-app/app.js](/Users/seandm/Projects/27vette/form-app/app.js:665)).
- Customer info, summary, missing required fields, and export shape ([form-app/app.js](/Users/seandm/Projects/27vette/form-app/app.js:840)).

## Hardcoded Runtime Fixes

| Location/function | RPO or option IDs involved | Current behavior | Why it exists | Recommended future home |
|---|---:|---|---|---|
| `LS6_ENGINE_COVER_OPTION_IDS`, `removeOtherLs6EngineCovers()` ([app.js:48](/Users/seandm/Projects/27vette/form-app/app.js:48), [app.js:393](/Users/seandm/Projects/27vette/form-app/app.js:393)) | BC7, BCP, BCS, BC4 | Forces mutual exclusivity in a multi-select section. | Engine cover rows were consolidated but still need one-of behavior. | Generated data/config: `exclusive_group_id` or section-level choice group. |
| `disableReasonForChoice()` + `reconcileSelections()` ([app.js:231](/Users/seandm/Projects/27vette/form-app/app.js:231), [app.js:457](/Users/seandm/Projects/27vette/form-app/app.js:457)) | Z51, FE1, FE2, FE3, FE4 | Z51 removes FE1/FE2, auto-adds FE3, enables FE4 through data rule. | Suspension is a replaceable default. | Generated data: default rule + replace rule. Runtime keeps generic evaluation. |
| Same functions ([app.js:233](/Users/seandm/Projects/27vette/form-app/app.js:233), [app.js:462](/Users/seandm/Projects/27vette/form-app/app.js:462)) | NWI, NGA | NWI removes default NGA exhaust; NGA re-added when no NWI. | Exhaust is another replaceable default. | Generated data/config. |
| `disableReasonForChoice()` ([app.js:234](/Users/seandm/Projects/27vette/form-app/app.js:234)) | 5V7 requires 5ZU or 5ZZ | Implements OR prerequisite in JS because current `requires` is target-by-target AND-style. | Missing `requires_any` rule concept. | Generated data with `requires_any` / `condition_group`. |
| `disableReasonForChoice()` ([app.js:237](/Users/seandm/Projects/27vette/form-app/app.js:237)) | 5ZU requires G8G/GBA/GKZ | Implements paint OR prerequisite in JS. | Same missing OR-rule concept. | Generated data with `requires_any`. |
| GBA/ZYC exceptions ([app.js:245](/Users/seandm/Projects/27vette/form-app/app.js:245), [app.js:465](/Users/seandm/Projects/27vette/form-app/app.js:465), [app.js:529](/Users/seandm/Projects/27vette/form-app/app.js:529)) | GBA, ZYC | Allows Black paint to displace ZYC instead of being blocked by it. | Direction/precedence is not expressible cleanly. | Generated data: `replaces` or `auto_remove` rule with priority. |
| `resetDefaults()` default array ([app.js:372](/Users/seandm/Projects/27vette/form-app/app.js:372)) | FE1, NGA, BC7 | Seeds defaults; BC7 only for coupe. | Workbook/data does not declare runtime defaults. | Generated data: `defaultSelections`. |
| `reconcileSelections()` section fallbacks ([app.js:479](/Users/seandm/Projects/27vette/form-app/app.js:479)) | `sec_susp_001`, `sec_seat_001`, FE1, 719 | Re-adds suspension and seatbelt defaults when empty. | Required defaults are implied by current app knowledge. | Generated data: section default rule. |
| `computeAutoAdded()` color override branch ([app.js:214](/Users/seandm/Projects/27vette/form-app/app.js:214)) | D30 and other override RPOs | Adds override RPO when selected interior + selected exterior option match. | Compound condition exists in a separate table, not the rule engine. | Generated data: compound `includes` rule. |
| `trimEquipmentRows()` regex ([app.js:700](/Users/seandm/Projects/27vette/form-app/app.js:700)) | `*LT Equipment` sections | Special display subset on Trim Level step. | UI relies on Stingray section naming. | Generated data: `standard_equipment_group=trim_equipment`. |
| `adjustedInteriorPrice()` ([app.js:146](/Users/seandm/Projects/27vette/form-app/app.js:146)) | seat/interior prices | Subtracts selected seat price from interior price. | Current workbook interior prices include seat cost. | Probably runtime generic, but should be declared in data as `price_adjustment_basis`. |

## Generation-Time Fixes

| Location/function | RPO or option IDs involved | Current behavior | Why it exists | Recommended future home |
|---|---:|---|---|---|
| `WORKBOOK_PATH`, dataset name ([generate_stingray_form.py:19](/Users/seandm/Projects/27vette/scripts/generate_stingray_form.py:19), [generate_stingray_form.py:1075](/Users/seandm/Projects/27vette/scripts/generate_stingray_form.py:1075)) | Stingray workbook | Generator is model-specific by name and output contract. | This script is currently a Stingray exporter. | Keep for now; later split model config from generator. |
| `STEP_ORDER`, `STEP_LABELS`, `CONTEXT_SECTIONS` ([generate_stingray_form.py:36](/Users/seandm/Projects/27vette/scripts/generate_stingray_form.py:36)) | body_style, trim_level | Injects synthetic body/trim steps. | Good current form model. | Config/data, reusable across models. |
| `SECTION_STEP_OVERRIDES`, `step_for_section()` ([generate_stingray_form.py:102](/Users/seandm/Projects/27vette/scripts/generate_stingray_form.py:102), [generate_stingray_form.py:257](/Users/seandm/Projects/27vette/scripts/generate_stingray_form.py:257)) | many `sec_*` IDs | Hard maps sections to runtime steps. | Needed because workbook sections are not already app-step-ready. | Config, not app runtime. |
| `OPTION_ID_ALIASES`, `CONSOLIDATED_ENGINE_COVERS` ([generate_stingray_form.py:125](/Users/seandm/Projects/27vette/scripts/generate_stingray_form.py:125)) | BC4/BCP/BCS/BC7 duplicates | Collapses duplicate rows and normalizes price/status. | QA found duplicate body-style rows. | Upstream workbook if possible; otherwise model config. |
| `HIDDEN_OPTION_IDS`, `AUTO_ONLY_OPTION_IDS`, `DISPLAY_ONLY_OPTION_IDS` ([generate_stingray_form.py:134](/Users/seandm/Projects/27vette/scripts/generate_stingray_form.py:134)) | N26, TU7, ZF1, R6X, D30 | Suppresses or changes runtime visibility/selectability. | QA-specific cleanup and override handling. | Generated data fields from workbook/config. |
| Option mutation block ([generate_stingray_form.py:378](/Users/seandm/Projects/27vette/scripts/generate_stingray_form.py:378)) | T0A, FE3, ZYC, BC7 | Reassigns sections, selectability, order, status. | Makes current UI behavior workable. | Config or upstream workbook normalization. |
| Active variants filter ([generate_stingray_form.py:428](/Users/seandm/Projects/27vette/scripts/generate_stingray_form.py:428)) | `c07`, `c67` | Exports exactly active Stingray coupe/convertible variants. | Stingray-only app. | Model import config. |
| UQT trim-only branch ([generate_stingray_form.py:568](/Users/seandm/Projects/27vette/scripts/generate_stingray_form.py:568)) | UQT | Selectable only on 1LT; standard equipment otherwise. | QA data correction. | Workbook/source availability or config. |
| Interior export branch ([generate_stingray_form.py:608](/Users/seandm/Projects/27vette/scripts/generate_stingray_form.py:608)) | LT vs LZ interiors, R6X | Marks LT interiors active for Stingray and LZ inactive. | Current app only supports Stingray LT interiors. | Model-scoped interior import config. |
| Manual rules ([generate_stingray_form.py:677](/Users/seandm/Projects/27vette/scripts/generate_stingray_form.py:677)) | T0A/Z51, TVS/T0A, BC7/ZZ3, R6X interiors | Adds rules absent or awkward in workbook mapping. | Fills current rule gaps. | Workbook/config once vocabulary supports them. |
| Skipped rules ([generate_stingray_form.py:742](/Users/seandm/Projects/27vette/scripts/generate_stingray_form.py:742)) | 5V7, 5ZU OR requirements | Drops generated `requires` rows so JS can hardcode OR behavior. | Current rule model cannot express OR. | Rule vocabulary: `requires_any`. |
| `runtime_action=replace` ([generate_stingray_form.py:755](/Users/seandm/Projects/27vette/scripts/generate_stingray_form.py:755)) | T0A replacements | Marks three excludes as replacement instead of blocker. | Good concept, but narrow. | Keep field, generalize semantics. |
| Validation floor ([generate_stingray_form.py:836](/Users/seandm/Projects/27vette/scripts/generate_stingray_form.py:836)) | 6 Stingray variants | Fails if not exactly six active variants. | Good for Stingray, wrong for multi-model. | Model config expected variant count. |

## Rule Engine Gap Analysis

| Behavior needed | Current implementation | Proposed rule type/data | Difficulty | Risk |
|---|---|---|---|---|
| OR prerequisite | Hardcoded 5V7 and 5ZU checks in `app.js`; generator drops rows | `requires_any` with `target_ids` or `condition_group` | Medium | High: current choices could become incorrectly blocked. |
| Replace default | Mix of `runtime_action=replace`, hardcoded deletes, default re-adds | `replaces` / `auto_remove` + `defaultSelection` | Medium | High: FE1/NGA/T0A defaults are visible behavior. |
| Mutually exclusive group inside multi-select section | LS6 set in JS | `exclusive_group_id` on choices or group table | Low | Medium. |
| Conditional include with two conditions | `colorOverrides` loop separate from rules | `includes` with `conditions: all([interior, option])` | Medium | High for D30/R6X override behavior. |
| Runtime default candidates | `defaultChoiceForRpo()` avoids standard-equipment duplicate | `is_default_candidate`, `default_priority` | Low | Medium. |
| Variant/model scoping beyond body style | only `body_style_scope` in rules | `scope: {model_family, body_style, trim_level, variant_id}` | Medium | High for second model import. |
| Summary/export inclusion control | hardcoded omission of standard equipment; docs note missing flag ([debug/qa-3.md](/Users/seandm/Projects/27vette/debug/qa-3.md:34)) | `include_in_summary`, `include_in_export` | Low | Low. |
| Section/step ordering per model | Python constants | config tables: `form_steps`, `section_step_map` | Low | Medium. |

## Suggested Normalized Rule Vocabulary

Keep it small:

- `includes`: source selected auto-adds target. Example: Z51 includes FE3/T0A.
- `excludes`: source blocks target. Example: 5V7 excludes incompatible ground effects.
- `requires_all`: source selectable only when every target is selected. Existing `requires` can map here.
- `requires_any`: source selectable when at least one target is selected. Example: 5V7 requires either 5ZU or 5ZZ; 5ZU requires one of G8G/GBA/GKZ.
- `replaces`: source removes target without making source itself unavailable. Example: TVS/5ZZ/5ZU replace T0A.
- `default_selection`: section-scoped default, optionally with conditions. Example: default FE1 unless Z51; default NGA unless NWI; default BC7 on coupe.
- `exclusive_group`: one-of grouping independent of section selection mode. Example: BC7/BCP/BCS/BC4 engine covers.
- `price_override`: keep current `priceRules` shape. Example: Z51 sets TVS to $0; B6P sets LS6 covers to $595.
- `visibility/selectability`: generated choice fields, not JS RPO checks. Example: R6X auto-only, D30 display-only, ZF1 hidden.

## Migration Plan

1. **Audit only**: This response. No code changes.

2. **Extract pure rule evaluation helpers**: Move existing rule evaluation into testable pure functions without changing behavior. Keep the same data shape first.

3. **Move one or two hardcoded behaviors into data-driven rules**: Start with low-risk LS6 `exclusive_group` and one `requires_any` case. Do not touch suspension/exhaust defaults first.

4. **Expand rule vocabulary**: Add `default_selection`, `replaces`, compound conditions, and richer scope only after the first two cases prove stable.

5. **Prepare for second model import**: Convert Python constants into model config tables/files: variant filter, expected variant count, section-to-step map, hidden/auto/display-only choices, aliases, and manual rules.

## Testing Strategy

Current tests pass: `node --test tests/stingray-form-regression.test.mjs` reports 28/28 passing.

Tests that should remain: generated data contract checks, exported order shape, customer info export, body/trim step flow, standard equipment placement, price override behavior, and high-value Stingray regressions.

Tests that should change: string-matching tests that assert implementation details in `appSource`, such as the LS6 set, default RPO array, hardcoded 5V7/5ZU expressions, and exact helper names ([tests/stingray-form-regression.test.mjs](/Users/seandm/Projects/27vette/tests/stingray-form-regression.test.mjs:53), [tests/stingray-form-regression.test.mjs](/Users/seandm/Projects/27vette/tests/stingray-form-regression.test.mjs:151), [tests/stingray-form-regression.test.mjs](/Users/seandm/Projects/27vette/tests/stingray-form-regression.test.mjs:203)).

New tests needed: pure rule-evaluator fixtures for `requires_any`, `replaces`, `exclusive_group`, `default_selection`, and compound color/interior overrides; generator contract tests that assert those rules are emitted from data/config; one browser smoke test for Z51/T0A/TVS and one for D30/R6X color override behavior.

## Risk Notes

The riskiest behaviors to preserve are Z51 suspension replacement, T0A spoiler replacement, NGA/NWI exhaust defaulting, D30/R6X auto-adds, and interior price subtraction. These are current working customer-facing behaviors, so migration should move one rule family at a time and compare generated order payloads before/after.

Do not run the generator casually during this migration: it mutates `stingray_master.xlsx`, `form-app/data.js`, and `form-output/*` ([App-refresh-workflow.md](/Users/seandm/Projects/27vette/App-refresh-workflow.md:39)). For this audit, I did not modify files.

## Handoff

What changed: no files changed.

What did not change: all runtime behavior, generated data, workbook sheets, tests, and docs were left untouched.

Gate results: typecheck N/A, lint N/A, test passed with `node --test tests/stingray-form-regression.test.mjs` at 28/28. Manual browser verification was not run because this was a read-only architecture audit.

Residual risk: this audit is based on static inspection plus the current regression suite, not a fresh workbook regeneration or browser walkthrough.
