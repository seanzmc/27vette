# Grand Sport Onboarding Spec

Date: 2026-04-29

## Purpose

Add 2027 Corvette Grand Sport to the existing configurator using the completed Stingray implementation as the functional baseline. This is a spec only; it does not start implementation, generate Grand Sport output, wire Formidable, or change Stingray behavior.

## Baseline To Preserve

Stingray is closed out as the current functional baseline:

- `.venv/bin/python scripts/generate_stingray_form.py` passes with `validation_errors: 0`.
- `node --test tests/stingray-form-regression.test.mjs` passes.
- Browser smoke passed for body/trim, generated choices, rules, rule groups, exclusive groups, grouped interiors, interior component pricing, R6X/D30 pricing, compact JSON/CSV, and `plainTextOrderSummary()`.

Do not regress these behaviors while onboarding Grand Sport.

## 1. Source Data Inventory

| Source area | Current evidence | Grand Sport readiness |
| --- | --- | --- |
| Variants | `stingray_master.xlsx` `variant_master` includes inactive Grand Sport rows `1lt_e07`, `2lt_e07`, `3lt_e07`, `1lt_e67`, `2lt_e67`, `3lt_e67` with 2027 base prices and display names. | Present. Needs model-scoped activation/filtering instead of changing global `active` blindly. |
| Option catalog | `stingray_master.xlsx` `grandSport` has 269 option rows with `option_id`, `RPO`, `Price`, `Option Name`, `Description`, `Detail`, `Category`, `Selectable`, and `Section`. | Present. Needs normalization into the current `choices` contract. |
| Option variant status | `grandSport` has columns `1lt_e07` through `3lt_e67`; each has Available/Standard/Not Available values. | Present. Needs conversion to canonical lowercase statuses. |
| Standard equipment | Grand Sport standard rows are derivable from `grandSport` status columns plus `section_master`; archived raw source also has `Standard Equipment 2`. | Present. Needs generated `standardEquipment` rows. |
| Price references | `grandSport.Price`, `variant_master.base_price`, and `PriceRef` exist. `PriceRef` has seat, stitching, suede, and two-tone component prices. | Present. Needs validation against Grand Sport-specific package and interior pricing. |
| Rule mapping | Current `rule_mapping` is Stingray-oriented. `grandSport.Detail` contains rule text for Z15/hash marks, Z25/EL9, FEY/FEB/T0F/J57/WUB/CFZ, engine covers, covers, stripes, paint constraints, etc. | Needs extraction/mapping. Do not reuse Stingray `rule_mapping` blindly. |
| Interiors | `lt_interiors` has 132 LT rows, including Grand Sport-only `3LT_AE4_EL9` and `3LT_AH2_EL9`. `LZ_Interiors` exists for LZ-family models, including `3LZ_*_EL9`, but regular Grand Sport variants are LT. | Present for Grand Sport. Needs model-scoped activation and hierarchy coverage for EL9. |
| Color overrides | `color_overrides` has 245 rows for LT interiors and includes 8 EL9 rows requiring D30 for selected exterior colors. | Present. Reuse for Grand Sport LT interiors. |
| Exclusive groups | Current generated exclusive groups are hardcoded in `generate_stingray_form.py`; Grand Sport likely reuses covers and engine covers, but also needs Grand Sport graphics/hash-mark group handling. | Partially present. Extend generator/config. |
| Rule groups | Current `RULE_GROUPS` covers 5V7 and 5ZU Stingray cases. Grand Sport needs new grouped requirements, especially Z15 requiring one of the hash marks and T0F requiring either FEY or both FEB/J57. | Extend generator/config. |
| Raw order guide | `archived/referenceSheets/2027 Chevrolet Car Corvette Export copy.xlsx` has `Standard Equipment 2`, `Interior 2`, `Exterior 2`, and `Mechanical 2` for Grand Sport; `archived/referenceSheets/v3_test.xlsx` has `Grand Sport Ingest`. | Available for audit/reference, not the first write target. |

## 2. Contract Fit Analysis

| Surface | Fit | Plan |
| --- | --- | --- |
| `variants` | Extend generator | Add `model` or `model_family` while preserving existing `variant_id`s. Export only the selected model in the first pass, or add runtime model context before exporting both models together. |
| `contextChoices` | Extend generator | Reuse body style and trim choices for a single-model Grand Sport dataset. If one app contains Stingray plus Grand Sport, add a model context step first. |
| `steps` | Reuse as-is | Existing order fits Grand Sport: body, trim, paint, exterior appearance, wheels, packages/performance, accessories, seat, base interior, seat belt, interior trim, delivery, customer info, summary. |
| `sections` | Add model-specific mapping | `section_master` already includes GS Center Stripes, GS Hash Marks, and Special Edition. Confirm step mapping for `sec_gsce_001`, `sec_gsha_001`, and `sec_spec_001`. |
| `choices` | Extend generator | Build from `grandSport`, not `stingray_master`, using the same output fields and status normalization. |
| `standardEquipment` | Reuse contract, extend generator | Same shape can work. Generate from Grand Sport statuses where status is `Standard` and display-only/standard sections apply. |
| `rules` | Add model-specific mapping | Existing `includes`, `requires`, `excludes`, `runtime_action=replace`, scopes, and auto-add are reusable. Grand Sport rules must be extracted from `grandSport.Detail` and/or hand-authored config. |
| `ruleGroups` | Extend generator | Reuse `requires_any`. Add Grand Sport groups for hash marks and compound package prerequisites. |
| `exclusiveGroups` | Extend generator | Reuse `single_within_group`. Add GS hash marks, GS center stripes, covers, and any model-specific spoiler/aero exclusivity. |
| `priceRules` | Reuse contract, extend generator | Existing override shape works for seatbelt includes, engine-cover package pricing, D30/R6X zeroing, and package-driven no-charge components. |
| `interiors` | Add model-specific activation | Reuse LT interior rows for regular Grand Sport. Activate EL9 for Grand Sport, keep it inactive for Stingray. Do not pull LZ interiors unless onboarding Grand Sport X or LZ models. |
| `colorOverrides` | Reuse as-is for LT | Existing LT rows include EL9. Filter to active Grand Sport interiors. |
| `validation` | Extend generator | Replace Stingray-specific “expected 6 active Stingray variants” with model-config expected counts and source coverage checks. |

## 3. Model Identity Strategy

Use explicit model identity in generated data:

- `model`: `Grand Sport`
- `model_year`: `2027`
- body styles: `coupe`, `convertible`
- trims: `1LT`, `2LT`, `3LT`
- variant IDs: preserve current workbook IDs:
  - `1lt_e07`, `2lt_e07`, `3lt_e07`
  - `1lt_e67`, `2lt_e67`, `3lt_e67`
- display names: preserve `variant_master.display_name`, e.g. `Corvette Grand Sport Coupe 1LT`.

Do not rename or rewrite existing Stingray `variant_id`s. The current runtime resolves variants by `body_style + trim_level`; that is safe only when one model is loaded. If a combined Stingray plus Grand Sport app is required, add `state.model` and model-scoped context before combining both variant sets.

## 4. Generator Strategy

Recommended path: create a shared generator core plus thin model-specific entrypoints.

Implementation shape:

- Extract shared helpers from `scripts/generate_stingray_form.py` into a generator module after the first approved implementation step.
- Keep `scripts/generate_stingray_form.py` as the Stingray entrypoint and preserve its outputs.
- Add `scripts/generate_grand_sport_form.py` only after the shared core exists, with a model config that points at `grandSport`, expected variants, model label, interior activation rules, manual rule groups, exclusive groups, and validation expectations.

Avoid a long-term cloned generator. A temporary copy is acceptable only as a short-lived discovery tool if the first shared extraction proves too risky, but it should not become the maintained Grand Sport path.

## 5. Runtime Strategy

`form-app/app.js` can consume a Grand Sport-only data object with limited genericization, but it cannot safely consume Stingray and Grand Sport variants together today.

Runtime changes likely needed:

- Replace hardcoded `vehicleInformation().model = "Corvette Stingray"` with generated model identity from `variant.model`, dataset metadata, or equivalent.
- Replace fallback `variantName` text of `Stingray` with generated model fallback.
- If both models are present in one app, add model state and a `model` context step; update `currentVariant()` to match `model + body_style + trim_level`.
- Make `trimEquipmentRows()` less LT-name-specific only if Grand Sport standard equipment uses non-`LT Equipment` labels in generated data. Current GS trims are LT, so this is not a blocker.

Runtime changes not justified yet:

- No fork of selection rendering.
- No new export schema.
- No new interior UI flow.
- No styling changes.

## 6. Rule And Compatibility Strategy

| Grand Sport need | Classification | Notes |
| --- | --- | --- |
| Status-driven availability by six Grand Sport variants | generator mapping | Convert `grandSport` matrix to `choices.status`; do not encode as runtime rules. |
| Standard/included rows | generator mapping | Same `standardEquipment` contract. |
| Z15 Grand Sport Heritage Graphics requires one hash-mark choice | `ruleGroup` | Use `requires_any` over `17A`, `20A`, `55A`, `75A`, `97A`, `DX4`. |
| Hash marks not available with matching/incompatible paints | existing `excludes` / `requires` | Extract from `grandSport.Detail`; some may be paint-specific excludes. |
| GS center stripes and hash marks mutual exclusion within their sections | `exclusiveGroup` or section single-select | Sections are `single_select_opt`; generated behavior may be enough inside section. Use exclusive groups only for cross-section conflicts. |
| Z25 Grand Sport Launch Edition includes/locks EL9 and 3F9 | `rules`, `priceRules`, interior mapping | Needs explicit include/availability rules and tests. EL9 is already in LT interiors and color overrides. |
| EL9 only available with Z25 | `rules` for interior requires | Interior `disableReasonForInterior()` already handles interior-sourced/target rules if generated. |
| FEY Z52 Track Performance Package includes J57, WUB, T0F/CFZ components | `rules` and `priceRules` | Source details show included content. Decide whether included components should appear as auto-added lines and whether prices zero under FEY. |
| T0F requires FEY or FEB plus J57 | `ruleGroup` | Existing `requires_any` handles FEY-or-other only if targets are alternatives; FEB plus J57 is an AND branch inside an OR, which is a runtime gap unless simplified by generator mapping. |
| NWI requires WUB and replaces NGA | existing rule plus runtime gap | `requires` can handle WUB. NGA replacement is currently hardcoded by RPO and likely works if RPOs match, but should become data-driven before relying on it for multiple models. |
| Engine cover BC4/BCP/BCS with B6P/ZZ3 and D3V includes | existing `rules`, `exclusiveGroup`, `priceRules` | Current Stingray mapping likely reusable because option IDs match, but validate against Grand Sport statuses. |
| D30 color override | existing color override branch | Reuse with Grand Sport LT interior IDs, including EL9 rows. |
| R6X component pricing | existing priceRule and interior component pricing | Reuse if Grand Sport uses the same LT R6X interiors and `PriceRef` values. |
| Custom stitching/suede/two-tone component lines | existing interior component mapping | Reuse for `36S`, `37S`, `38S`, `N26`, `N2Z`, and `TU7` where present. |

Runtime gaps to avoid until proven necessary:

- Compound OR-of-AND requirements, e.g. `T0F requires FEY OR (FEB AND J57)`.
- Data-driven default selections replacing hardcoded FE1/NGA/BC7.
- Model context if both Stingray and Grand Sport are loaded at once.

## 7. Interior Strategy

Regular Grand Sport should reuse the LT interior source path, not LZ.

Plan:

- Use `lt_interiors` for `1LT`, `2LT`, `3LT` Grand Sport variants.
- Activate `3LT_AE4_EL9` and `3LT_AH2_EL9` for Grand Sport; keep them inactive for Stingray.
- Add an EL9 hierarchy entry to the interior reference. Current `architectureAudit/stingray_interiors_refactor.csv` is Stingray-focused and the Stingray tests assert EL9 is inactive. Grand Sport should either extend this CSV with model-scoped rows or use a new `grand_sport_interiors_refactor.csv`.
- Prefer a model-scoped interior reference file if EL9 or Launch Edition grouping makes the shared CSV ambiguous.
- Reuse component pricing for seats, R6X, stitching, suede, and two-tone through `PriceRef`.
- Reuse D30 color overrides; EL9 already has D30 rows for `G26`, `G4Z`, `GBK`, and `GPH`.
- Do not use `LZ_Interiors` for regular Grand Sport. Keep LZ work for Grand Sport X/Z06/ZR1/ZR1X.

Specific EL9 handling:

- `3LT_AE4_EL9`: price 595, AE4 seat, included/only available with Z25.
- `3LT_AH2_EL9`: price 0, AH2 seat, included/only available with Z25.
- Both should include or price-adjust `3F9` red seat belts if Z25/EL9 source rules say they are included.

## 8. Export Strategy

Grand Sport should use the existing export surfaces:

- `currentOrder()`
- `compactOrder()`
- `plainTextOrderSummary()`
- compact JSON export
- compact CSV export

Do not change the export schema unless a downstream consumer requires it. The export content must use generated model identity so the title becomes `2027 Corvette Grand Sport`, not `2027 Corvette Stingray`.

## 9. Testing Strategy

Add a Grand Sport regression file or split shared fixtures cleanly:

- generator validation: Grand Sport run has `validation_errors: 0`
- variant count: six Grand Sport variants generated
- variant IDs: exact `1lt_e07` through `3lt_e67`
- choices generated: nonzero choices with correct status normalization from `grandSport`
- standard equipment generated: counts per variant and expected rows from `Standard` statuses
- sections: GS Center Stripes, GS Hash Marks, and Special Edition map to intended steps
- key availability rules: Z15/hash marks, Z25/EL9, FEY/FEB/T0F/J57/WUB/CFZ, NWI/WUB/NGA, engine covers
- `ruleGroups`: Z15 hash mark requirement and any Grand Sport OR requirements
- `exclusiveGroups`: covers, center caps, engine covers, GS graphics groups as needed
- interiors: LT interiors active, EL9 active only for Grand Sport, LZ interiors inactive for regular Grand Sport
- component pricing: AE4/AH2, R6X, N26/N2Z, TU7, 36S/37S/38S
- D30/R6X pricing: D30 zeroes only R6X component when applicable
- compact export: JSON and CSV schema unchanged, model title correct
- plain text summary: Grand Sport title and selected sections correct
- no Stingray regression: existing Stingray tests still pass after shared generator/runtime changes

Browser smoke checklist for Grand Sport:

- select Grand Sport body and trim context
- select paint
- select GS hash mark with Z15 behavior
- select Z25 and verify EL9 availability/selection
- select FEY/T0F path and verify included/required rows
- select NWI and verify WUB/NGA behavior
- select seat/interior and verify component pricing
- export compact JSON, CSV, and plain text summary

## 10. Migration Plan

### Phase 1: Source Inventory And Schema Mapping

- Freeze the current Stingray baseline.
- Record source row counts for `variant_master`, `grandSport`, `section_master`, `PriceRef`, `lt_interiors`, `color_overrides`, and raw archived Grand Sport sheets.
- Produce a mapping table from `grandSport` columns to `choices`, `standardEquipment`, `rules`, and validation rows.
- Decide whether the first Grand Sport artifact is single-model or combined-model. Do not combine models until model context exists.

### Phase 2: Generator Support

- Extract a shared generator core from `generate_stingray_form.py`.
- Keep Stingray entrypoint and output behavior stable.
- Add a Grand Sport model config for source sheet, model label, variant IDs, expected variant count, section-step overrides, hidden/display/auto-only options, manual rules, rule groups, exclusive groups, and interior activation.

### Phase 3: Generated Data Inspection

- Generate Grand Sport data only after the Phase 2 implementation is approved.
- Inspect counts and validation rows before touching runtime.
- Compare Grand Sport generated surfaces to Stingray contract shape.
- Validate no accidental Stingray `generated_at` or workbook churn beyond intended files.

### Phase 4: Runtime Smoke With No UI Redesign

- Load the Grand Sport-only generated data into the existing static runtime.
- Make only generic runtime changes required for model identity.
- Do not redesign layout, cards, interior display, or exports.

### Phase 5: Grand Sport-Specific Rules, Interiors, Pricing

- Add Z15/hash-mark grouped requirement.
- Add Z25/EL9 interior rules and price/seatbelt handling.
- Add FEY/FEB/T0F/J57/WUB/CFZ package rules.
- Validate engine covers, NWI/NGA, color overrides, R6X/D30, and component pricing.

### Phase 6: Regression Tests

- Add Grand Sport generator/runtime tests.
- Keep existing Stingray regression file passing.
- Add shared export tests that assert unchanged schema and model-correct content.

### Phase 7: Browser Smoke

- Run a representative Grand Sport build path in the browser.
- Export compact JSON, compact CSV, and plain text.
- Run the existing Stingray browser smoke again after any shared runtime change.

## Non-Goals

- No styling polish.
- No Formidable wiring.
- No new customer workflow.
- No export schema change.
- No Grand Sport X/LZ onboarding in this pass.
- No combined multi-model app until model identity is represented in runtime state.

## Approval Boundary

Implementation should not start until this spec is approved. The first implementation step should be source/generator scaffolding only, with Stingray regression tests run before and after.
