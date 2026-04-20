# Corvette Shared Contract V2

This document is the shared operating contract for the replacement Corvette ingest/build specs.

If this file and a V2 skill file disagree, this file wins on:

- workbook substrate
- model-year and dataset boundaries
- canonical model-family handling
- ID and scope conventions
- generated-sheet replace policy
- exception severity and build gating

## 1. Canonical Substrate

The canonical working substrate is a single Excel workbook (`.xlsx`) per model year.

- Raw GM export sheets and generated output sheets live in the same workbook.
- Raw sheets are read-only.
- Generated sheets may be replaced on rerun.
- If Sean mirrors the workbook into Google Sheets for review, the Excel workbook remains the source of truth for ingest/build runs.

## 2. Run Boundary

One ingest/build run operates on one workbook for one model year.

- The workbook is the isolation boundary.
- Generated IDs are namespaced by `dataset_id`.
- Cross-year joins are not allowed inside a single run.

## 3. Model Year and Dataset ID

Every generated sheet in V2 carries these shared fields where relevant:

- `model_year` as a four-digit integer, e.g. `2027`
- `dataset_id` as `my<yy>`, e.g. `my27`

ID examples:

- `option_id = my27_opt_ae4`
- `variant_id = my27_var_stingray_coupe_2lt`
- `price_id = my27_prc_ae4_01`
- `combo_id = my27_ctc_stingray_3lt_ah2_hta`
- `pair_id = my27_cca_stingray_g26_hta_01`
- `exception_id = my27_exc_0042`

## 4. Canonical Model Families

The supported model-family labels in this refactor are:

- `Stingray`
- `Grand Sport`
- `Grand Sport X`
- `Z06`
- `ZR1`
- `ZR1X`

Rules:

- Use the workbook-declared family label exactly.
- Do not substitute `E-Ray` for any of the six labels above.
- If a workbook declares a family outside this set, ingest logs a blocking exception and stops before sheet generation unless Sean explicitly approves the new family.

Trim tie-break rules:

- `LT` trims may only resolve to `Stingray` or `Grand Sport`
- `LZ` trims may only resolve to `Grand Sport X`, `Z06`, `ZR1`, or `ZR1X`

If a workbook header and trim suffix conflict, ingest logs a blocking exception and does not guess.

## 5. Scope Conventions

Shared scope fields use these conventions:

- `model_family_scope`: pipe-delimited model families
- `body_scope`: pipe-delimited `Coupe|Convertible`
- `trim_scope`: pipe-delimited trims such as `1LT|2LT|3LT`

Blank scope means "all values valid in the current dataset" only when the source truly has no narrower bound. Blank never means "unknown".

### Shared availability vocabulary

`Availability Long` uses one base availability state plus zero or more co-occurring context labels.

Canonical base availability states:

- `Standard Equipment`
- `Available`
- `Not Available`
- `ADI Available`

Canonical context labels:

- `Included in Equipment Group`
- `Included in Equipment Group but upgradeable`
- `Indicates availability of feature on multiple models`

Context labels do not replace or rewrite the base availability state. They travel alongside it as inclusion/reference context.

## 6. Generated Sheet Replace Policy

The default rerun mode is full rebuild of generated sheets.

- Raw sheets are never edited or deleted.
- Generated sheets are replaced in place by name.
- Partial patch mode is not part of the default contract.
- If Sean wants a patch-only update, that must be requested explicitly and treated as an exception workflow.

## 7. Shared Output Set

The V2 ingest/build contract assumes this ingest output set:

1. `Option Catalog`
2. `Availability Long`
3. `Pricing Long`
4. `Base Prices`
5. `Interior Trim Combos`
6. `Color Combination Availability`
7. `Equipment Group Membership`
8. `Ingest Exceptions`

Build consumes all eight sheets.

Color and Trim derived outputs use this additional rule:

- `Interior Trim Combos` does not carry `model_family_scope` or `body_scope`
- `Color Combination Availability` does not carry `model_family_scope` or `body_scope`

Interior and exterior colors are treated as not model-family-specific and not body-style-specific in the shared contract. Trim-specific behavior may still be carried where needed.

## 8. Note and Provenance Vocabulary

When a generated field contains carried-through note text, it must also identify the note source type when the schema supports it.

Allowed source types:

- `footnote_same_sheet`
- `cell_inline_disclosure`
- `row_note`
- `sheet_disclosure`
- `legend_note`
- `pricing_context_note`

Priority rule:

- Structured rule fields are promoted from the most specific note source available.
- When multiple note texts contribute to one derived rule, preserve the verbatim combined text in `source_note` using ` || ` as the separator.

## 9. Exception Severity and Build Gate

`Ingest Exceptions` must include:

- `severity`: `blocking` or `warning`
- `blocking_scope`: `global`, `model_family`, `variant`, or blank for warning rows
- `affected_model_families`
- `affected_variant_ids`
- `affected_rpos`

Blocking exceptions include:

- unknown or conflicting model-family resolution
- unparseable variant headers
- unresolved legend tokens that affect availability interpretation
- price rows that cannot be converted into a valid `price_mode`
- Color and Trim rows that cannot be expanded to a concrete `interior_color_rpo`
- IDs or keys that cannot be generated uniquely

Warnings include:

- non-critical naming drift across source sheets
- unresolved descriptive footnotes that do not alter availability or pricing
- notes that remain ambiguous but are preserved verbatim

Build gate:

- Build must stop if any blocking exception is `global`
- Build must stop for a target family if any blocking exception affects that family
- Build must stop for a target variant if any blocking exception affects that variant
- Build may proceed past warnings, but must report them

## 10. Canonical Base Price Shape

`Base Prices` must carry explicit decomposition fields, not just a descriptive string.

Required shared fields:

- `dataset_id`
- `model_year`
- `variant_id`
- `model_family`
- `body_style`
- `trim`
- `model_code`
- `description`
- `list_price`
- `msrp_c`
- `dfc`

Build must never parse body/trim back out of `description`.

## 11. Validation Floor

Every completed build validation set must cover all of these cases:

1. standard seat path
2. package-dependent price split
3. D30-only color override
4. R6X plus D30 collapsed-pricing case
5. additive interior option gated by selected base interior

Three sample builds is the minimum count only if those five behaviors are covered across the chosen samples.
