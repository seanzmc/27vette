# Z Option Canonical Pricing Pass Spec

## Diagnosis

The next runtime-readiness move should be option-sheet canonicalization, not broader runtime/rule expansion. The Z06/ZR1/ZR1X option and OVS universes are structurally aligned, but their runtime-facing option sheets are still not canonical because all direct option prices are blank.

Current workbook evidence:

- `z06_options`
  - 239 rows
  - 0 nonblank direct prices
  - 239 blank prices
- `zr1_options`
  - 203 rows
  - 0 nonblank direct prices
  - 203 blank prices
- `zr1x_options`
  - 204 rows
  - 0 nonblank direct prices
  - 204 blank prices
- `z06_price_rules`: 0 rows
- `zr1_price_rules`: 0 rows
- `zr1x_price_rules`: 0 rows

Source pricing evidence exists upstream in `future_model_source_review`:

- `candidate_price`
- `price_candidate_rows`
- `price_candidate_summary`
- `approved_price`

Current evidence counts:

- Z06:
  - source rows: 334
  - active approved option rows: 239
  - source rows with `candidate_price`: 142
  - rows tied to active option IDs with `candidate_price`: 135
  - candidate text buckets:
    - plain candidate text: 109
    - conditional text: 19
    - standard/no-charge-ish text: 7
- ZR1:
  - source rows: 305
  - active approved option rows: 203
  - source rows with `candidate_price`: 114
  - rows tied to active option IDs with `candidate_price`: 106
  - candidate text buckets:
    - plain candidate text: 77
    - conditional text: 22
    - standard/no-charge-ish text: 7
- ZR1X:
  - source rows: 305
  - active approved option rows: 204
  - source rows with `candidate_price`: 114
  - rows tied to active option IDs with `candidate_price`: 107
  - candidate text buckets:
    - plain candidate text: 78
    - conditional text: 22
    - standard/no-charge-ish text: 7

Root cause:

The future-model source audit/parser captured candidate prices, but those prices were not approved into the normalized Z option sheets. The canonical runtime-facing `*_options.price` fields remain blank, and conditional/package pricing has not been separated into `*_price_rules` yet.

Change type: workbook/data-only first, with optional small audit tooling if needed. Runtime behavior, form-app promotion, and rule expansion are out of scope.

Risk level: medium. Direct prices are necessary for canonical option sheets, but conditional/package rows must not be blindly copied into `*_options.price` if their price depends on trim, body style, model, or selected combinations.

## User constraint / direction

The user explicitly wants every near-term move to make the Z model option sheets canonical before adding or changing rules and other runtime behavior.

Therefore this pass must:

- treat `z06_options`, `zr1_options`, and `zr1x_options` as the immediate target contract;
- populate direct option prices only when evidence is straightforward;
- hold conditional/package cases separately for later price-rule or package design;
- not let PDB/PDD/PDF or other combo pricing force premature runtime/rule work;
- not create another confusing review taxonomy.

## Exact files / sheets / artifacts

Primary workbook:

- `stingray_master.xlsx`

Primary sheets to inspect:

- `z06_options`
- `zr1_options`
- `zr1x_options`
- `future_model_source_review`
- `future_model_option_review`
- `z06_price_rules`
- `zr1_price_rules`
- `zr1x_price_rules`

Potential generated/report artifacts:

- `.hermes/plans/z-option-canonical-pricing-audit.json`
- `.hermes/plans/z-option-canonical-pricing-audit.md`
- `.hermes/plans/z-option-canonical-pricing-matrix.csv`

Possible implementation files if audit logic needs to become repeatable:

- `scripts/build_future_z_pricing_audit.py`
- `scripts/corvette_form_generator/future_z_pricing_audit.py`
- `tests/test_future_z_pricing_audit.py`

Do not edit in this pass unless explicitly expanded:

- `form-app/data.js`
- runtime JS/CSS/HTML
- generated `form_*` sheets by hand
- model activation / registry promotion sheets
- Z rule/exclusive/default sheets except read-only inspection

## Proposed smallest safe pass

### Step 4A — Read-only canonical pricing matrix

Build a pricing matrix for every active Z option row. Each row should include:

- `model_key`
- `option_sheet`
- `option_row`
- `option_id`
- `rpo`
- `option_name`
- `current_price`
- matched `future_model_source_review` row(s)
- `candidate_price`
- `price_candidate_rows`
- `price_candidate_summary`
- `approved_price`
- classification:
  - `direct_price_candidate`
  - `zero_or_standard_candidate`
  - `conditional_price_candidate`
  - `package_combo_price_candidate`
  - `missing_price_evidence`
  - `ambiguous_price_evidence`
- recommended workbook action:
  - `write_options_price`
  - `leave_blank_standard_or_included`
  - `defer_to_price_rules`
  - `defer_to_package_combo_design`
  - `needs_human_review`
- notes / evidence summary

Classification rules for the matrix:

- `direct_price_candidate`
  - exactly one candidate price;
  - candidate maps to an active canonical option ID;
  - candidate summary does not contain conditional hints such as `Coupe Only`, `Convertible`, trim-only text, `Std on`, or combination/package wording;
  - not one of the explicitly-known package-combo cases.
- `conditional_price_candidate`
  - price summary contains body-style/trim/model conditions (`Coupe Only`, `3LT/LZ Only`, `Std on ZR1/ZR1X`, etc.).
- `package_combo_price_candidate`
  - known combo/package rows such as Z06 `PDB`, `PDD`, `PDF`;
  - or rows whose source description/summary indicates price changes based on selected combinations rather than the option alone.
- `zero_or_standard_candidate`
  - standard/no-charge/included evidence where direct price should remain blank or become zero depending on existing workbook conventions.
- `missing_price_evidence`
  - active option has no candidate price evidence.
- `ambiguous_price_evidence`
  - multiple conflicting candidate prices or unclear mapping.

### Step 4B — After approval, direct-price workbook write only

If the matrix looks good, the first workbook write should populate only direct option prices in:

- `z06_options.price`
- `zr1_options.price`
- `zr1x_options.price`

Rows classified as conditional/package/missing/ambiguous should remain blank in `*_options.price` and be listed for later follow-up.

Do not write `*_price_rules` in Step 4B unless specifically approved after the audit. The goal is canonical option sheets first.

## Special PDB / PDD / PDF handling

Z06 package options require a separate design decision and should not be auto-written as simple direct prices in this pass:

- `opt_pdb_001` / `PDB`
- `opt_pdd_001` / `PDD`
- `opt_pdf_001` / `PDF`

User context:

These are package-like options with multiple option combinations and prices within each RPO. They may need conditional price-rule / auto-add-style behavior when a qualifying combination is selected, similar in spirit to D30 auto-add behavior, rather than a simple one-price option row.

Pass behavior:

- classify them as `package_combo_price_candidate`;
- preserve their option rows as canonical option identities;
- do not populate direct price until the package-combo pricing model is chosen;
- do not add runtime/rule behavior in this pass.

## Constraints

- Workbook is source of truth.
- Do not hardcode model/RPO-specific runtime JS behavior.
- Do not add new dependencies.
- Do not refactor runtime/generator structure outside the pricing audit/write need.
- Do not change live dealer submission endpoint, payload shape, or Turnstile behavior.
- Do not activate or promote Z models to runtime.
- Do not touch interiors.
- Do not expand rule groups/rules/exclusive groups as part of direct-price cleanup.
- Do not overwrite user/open-Excel workbook state; respect `~$stingray_master.xlsx` and use `save_workbook_safely()` for writes.
- After any workbook write, reopen with `openpyxl` and verify exact changed cells on disk.

## Risks

- Candidate prices may be stale, ambiguous, or copied from broad source rows.
- Price summaries like `1LT/LZ`, `3LT/LZ Only`, `Coupe Only`, or `Std on ZR1/ZR1X` indicate conditional behavior that should not be flattened into direct option prices.
- `approved_price` is currently blank in inspected source rows, so the audit must treat `candidate_price` as evidence, not already-approved runtime truth.
- Missing direct prices for standard/included rows may be correct and should not automatically become `0` unless that is consistent with existing Stingray/Grand Sport conventions.
- PDB/PDD/PDF could corrupt pricing if treated as one-price direct options.

## Non-goals

- No runtime promotion.
- No app-data generation for Z runtime.
- No visual/runtime behavior changes.
- No dealer-submission changes.
- No interiors pass.
- No package-combo implementation yet.
- No rule/exclusive/default expansion.
- No mass copy of `candidate_price` into option sheets.

## Validation plan

Read-only Step 4A:

```sh
.venv/bin/python scripts/build_future_z_pricing_audit.py --model-key all --format json > .hermes/plans/z-option-canonical-pricing-audit.json
.venv/bin/python scripts/build_future_z_pricing_audit.py --model-key all --format markdown > .hermes/plans/z-option-canonical-pricing-audit.md
```

If a script is added:

```sh
.venv/bin/python -m pytest tests/test_future_z_pricing_audit.py -q
```

After any workbook write in Step 4B:

```sh
.venv/bin/python scripts/validate_workbook_package.py stingray_master.xlsx
.venv/bin/python scripts/validate_workbook_schema.py stingray_master.xlsx
.venv/bin/python -m pytest \
  tests/test_future_model_source_review.py \
  tests/test_future_model_source_population.py \
  tests/test_future_model_option_review.py \
  tests/test_future_model_option_population.py \
  tests/test_future_model_compatibility_rebase.py \
  tests/test_future_model_lz_interiors.py \
  tests/test_future_model_option_pricing.py \
  tests/test_future_z_rule_audit.py \
  -q
```

Optional post-write check:

- Reopen workbook and report:
  - number of nonblank prices in each Z option sheet;
  - exact option IDs changed;
  - remaining blank-price counts by classification;
  - package/conditional rows deferred.

## Approval gate

Approve Step 4A to build the read-only canonical pricing matrix/audit. Do not write prices to the workbook until the matrix is reviewed.
