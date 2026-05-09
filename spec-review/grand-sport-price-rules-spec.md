# Grand Sport Price Rules Spec

## Diagnosis

Grand Sport draft generation currently exports compatibility rules from `grandSport_rule_mapping`, but it intentionally emits no price rules:

- `scripts/corvette_form_generator/inspection.py`
  - `build_form_data_draft()` returns `"priceRules": []`.
  - validation emits `pricing_deferred`.
  - `draftMetadata.deferredSurfaces` includes `priceRules`.
- `tests/grand-sport-draft-data.test.mjs`
  - `Grand Sport draft emits color overrides while deferring price rules` asserts `draft.priceRules` is empty.
- `form-app/app.js`
  - runtime already supports `data.priceRules`.
  - `optionPrice(optionId)` applies `override` rows when `condition_option_id` is selected or auto-added.
  - `selectedContextIds()` includes selected options, selected interiors, and auto-added options, so price rules can be conditioned by either option IDs or interior IDs.

Root cause: there is no Grand Sport price-rule source sheet or generator path. The runtime can consume the rules, but the Grand Sport draft generator does not load them.

Risk level: medium. Pricing affects order totals and can create double-charge or no-charge errors if source rows are wrong. This pass should keep the scope narrow and workbook-owned.

Behavior type: mixed source-data and generator wiring. No visual redesign.

## Goal

Add workbook-owned Grand Sport price rules using the existing Stingray `price_rules` shape, then wire the Grand Sport draft generator to emit those rows into `priceRules`.

## Non-Goals

- Do not activate Grand Sport production runtime.
- Do not change Stingray `price_rules` behavior or Stingray generated output except for unavoidable workbook metadata.
- Do not invent a new price-rule schema.
- Do not change `form-app/app.js` unless implementation proves the existing runtime contract cannot support a required Grand Sport row.
- Do not perform broad `grandSport_rule_mapping` cleanup in this pass.
- Do not solve all Z25 presentation/section cleanup in this pass unless the safe workbook rows are already unambiguous.

## Constraints

- Workbook remains source of truth.
- Business facts must live in workbook rows, not hardcoded generator branches.
- Use the same column format as Stingray `price_rules`.
- Preserve `price_rules` as Stingray's status quo price-rule source.
- Grand Sport should use a model-scoped price-rule sheet so Stingray and Grand Sport price rules stay separated.
- Keep `variant_master` Grand Sport rows inactive.
- Use `.venv/bin/python` for project Python commands.
- Reopen or validate the workbook package after workbook edits.

## Workbook Changes

Create a new sheet:

`grandSport_price_rules`

Use the same headers as `price_rules`:

| column | purpose |
| --- | --- |
| `price_rule_id` | stable unique row id |
| `condition_option_id` | selected option or interior id that triggers the override |
| `price_rule_type` | currently `override` |
| `target_option_id` | option whose displayed/order price is overridden |
| `price_value` | replacement price |
| `body_style_scope` | optional `coupe` / `convertible` scope; blank means all |
| `review_flag` | `TRUE` only when row needs later review |
| `notes` | human-readable source note |

Do not add `trim_level_scope` or `variant_scope` in this pass. `form-app/app.js` already tolerates those fields when present, but the current Stingray sheet does not define them.

### Initial Grand Sport Price Rows

Add rows only for package components already represented by active Grand Sport compatibility `includes` rules.

| price_rule_id | condition_option_id | price_rule_type | target_option_id | price_value | notes |
| --- | --- | --- | --- | ---: | --- |
| `gs_pr_fey_j57_001` | `opt_fey_001` | `override` | `opt_j57_001` | `0` | FEY includes J57, so J57 should not add a second charge. |
| `gs_pr_fey_t0f_001` | `opt_fey_001` | `override` | `opt_t0f_001` | `0` | FEY includes T0F, so T0F should not add a second charge. |
| `gs_pr_fey_wub_001` | `opt_fey_001` | `override` | `opt_wub_001` | `0` | FEY includes WUB, so WUB should not add a second charge. |
| `gs_pr_fey_cfz_001` | `opt_fey_001` | `override` | `opt_cfz_001` | `0` | FEY includes CFZ through included T0F. |
| `gs_pr_pcq_vwe_001` | `opt_pcq_001` | `override` | `opt_vwe_001` | `0` | PCQ includes VWE, so VWE should not add a second charge. |
| `gs_pr_pcq_vwt_001` | `opt_pcq_001` | `override` | `opt_vwt_001` | `0` | PCQ includes VWT, so VWT should not add a second charge. |
| `gs_pr_pef_ria_001` | `opt_pef_001` | `override` | `opt_ria_001` | `0` | PEF includes RIA, so RIA should not add a second charge. |
| `gs_pr_pef_cav_001` | `opt_pef_001` | `override` | `opt_cav_001` | `0` | PEF includes CAV, so CAV should not add a second charge. |

Leave `body_style_scope` blank for all initial rows.
Set `review_flag` to `FALSE`.

### Z25 / EL9 Handling

Do not force the Z25 price solution into `grandSport_price_rules` until the source-price ownership is explicit.

Current facts to preserve for the implementation review:

- `form-app/app.js` can use selected interior IDs as `condition_option_id`.
- Price rules can override an option price, including auto-added `opt_z25_001`.
- Price rules cannot directly override the selected interior line price.
- Current EL9 interior rows in `lt_interiors` are:
  - `3LT_AE4_EL9`
  - `3LT_AH2_EL9`
- If Z25 should be auto-added by EL9 and have no separate option charge, that can be represented as:
  - `grandSport_rule_mapping`: EL9 interior id `includes` `opt_z25_001`.
  - `grandSport_price_rules`: EL9 interior id overrides `opt_z25_001` to `0`.
- If the Z25 package charge should appear in the EL9 interior line item, then `lt_interiors` source pricing must be updated intentionally. Do not guess that price in this pass.

## Code Changes

### `scripts/corvette_form_generator/model_config.py`

Add an optional model config field:

```python
price_rules_sheet: str = "price_rules"
```

This keeps Stingray default behavior on `price_rules` and lets Grand Sport point to `grandSport_price_rules`.

### `scripts/corvette_form_generator/model_configs.py`

Set:

```python
GRAND_SPORT_MODEL.price_rules_sheet = "grandSport_price_rules"
```

Leave `STINGRAY_MODEL` on the default `price_rules`.

### `scripts/corvette_form_generator/inspection.py`

Add a Grand Sport draft price-rule builder that mirrors the Stingray output shape:

- load rows from `config.price_rules_sheet`;
- skip blank rows;
- normalize `price_rule_type` to lowercase;
- normalize `price_value` with existing money helpers;
- include `body_style_scope`, `review_flag`, and `notes`;
- include `trim_level_scope` and `variant_scope` as empty strings in emitted JSON for runtime compatibility, even though the workbook sheet does not define those columns;
- validate each row references known source/target IDs:
  - `condition_option_id` may be an option ID or an interior ID;
  - `target_option_id` must be an option ID;
  - unknown references become validation errors and are not silently emitted.

Update `build_form_data_draft()`:

- emit `priceRules` from the new builder;
- change the validation row from warning `pricing_deferred` to pass when at least one row is emitted;
- remove `priceRules` from `draftMetadata.deferredSurfaces` when rows are emitted;
- keep a warning only if the sheet is missing or empty.

Do not add pricing facts in Python.

### `scripts/generate_stingray_form.py`

No intended behavior change in this pass.

Only touch this file if shared model config changes require a compatibility update. If touched, preserve Stingray output counts and `priceRules` contents.

## Tests

### `tests/grand-sport-draft-data.test.mjs`

Replace the deferred price-rule assertion with workbook-owned price-rule assertions:

- `draft.priceRules.length` equals the number of active rows in `grandSport_price_rules`.
- FEY rows exist and override:
  - `opt_j57_001`
  - `opt_t0f_001`
  - `opt_wub_001`
  - `opt_cfz_001`
- PCQ rows exist and override:
  - `opt_vwe_001`
  - `opt_vwt_001`
- PEF rows exist and override:
  - `opt_ria_001`
  - `opt_cav_001`
- `draft.draftMetadata.deferredSurfaces` no longer contains `priceRules`.
- validation contains a pass row for price rules.

### `tests/grand-sport-contract-preview.test.mjs`

Only update if contract preview validation surfaces price-rule reference checks. Otherwise leave unchanged.

### `tests/stingray-generator-stability.test.mjs`

Add workbook stability assertions:

- `grandSport_price_rules` exists.
- Its headers exactly match `price_rules`.
- Stingray `price_rules` headers are unchanged.

Keep existing Stingray `jsonData.priceRules.length === 42` unless a separate Stingray change is explicitly approved.

### `tests/multi-model-runtime-switching.test.mjs`

Add one runtime switching assertion if packaged `form-app/data.js` now includes Grand Sport price rules:

- switching to Grand Sport makes `data.priceRules` include `gs_pr_fey_j57_001`;
- switching back to Stingray keeps Stingray price rules available and does not leak Grand Sport price-rule IDs.

## Validation Plan

Run:

```bash
.venv/bin/python -m py_compile scripts/corvette_form_generator/inspection.py scripts/corvette_form_generator/model_config.py scripts/corvette_form_generator/model_configs.py scripts/generate_grand_sport_form.py scripts/generate_stingray_form.py
.venv/bin/python scripts/validate_workbook_package.py stingray_master.xlsx
.venv/bin/python scripts/generate_grand_sport_form.py
.venv/bin/python scripts/generate_stingray_form.py
node --test tests/grand-sport-draft-data.test.mjs
node --test tests/grand-sport-contract-preview.test.mjs
node --test tests/multi-model-runtime-switching.test.mjs
node --test tests/stingray-generator-stability.test.mjs
node --test tests/stingray-form-regression.test.mjs
git diff --check
```

Manual verification:

- Open `stingray_master.xlsx` after save and confirm there is no Excel repair prompt.
- In the local Grand Sport browser test, verify:
  - selecting FEY auto-adds J57, T0F, WUB, and CFZ at `$0`;
  - selecting PCQ auto-adds VWE and VWT at `$0`;
  - selecting PEF auto-adds RIA and CAV at `$0`;
  - Stingray still shows the same price behavior as before.

## Risks

- Package rows can double-charge if an included option does not get an override.
- Package rows can under-charge if the package parent price is not correct in `grandSport_options`.
- Z25/EL9 cannot be fully solved by option price rules alone if the intended display charge belongs on the selected interior line.
- If `grandSport_price_rules` is created incorrectly as a damaged Excel table/range, Excel may show the repair prompt again.

## Success Criteria

- Grand Sport draft emits workbook-backed `priceRules`.
- Initial package price overrides are represented only in `grandSport_price_rules`.
- Stingray continues to use `price_rules`.
- Grand Sport remains draft-only.
- Workbook validation passes and Excel opens without repair.
