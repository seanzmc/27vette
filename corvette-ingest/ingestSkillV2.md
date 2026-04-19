---
name: corvette-ingest-v2
description: Ingest raw Chevrolet Corvette order-guide exports and GM price schedules into a fully-specified intermediate layer for downstream configurator use. Use this replacement spec when Sean wants a new Corvette workbook ingested with explicit source-shape handling for matrix sheets, Standard Equipment, Equipment Groups, Color and Trim, and price schedules, plus blocking/warning exception gating and model-year-safe IDs.
---

# Corvette Ingest V2

Read [sharedContractV2.md](/Users/seandm/Projects/27vette/corvette-contract/sharedContractV2.md:1) before using this skill. That document defines the workbook boundary, model-family scope, IDs, rerun behavior, and exception gate that this skill depends on.

## Core principle

Faithfully capture what GM published.

- Preserve source facts.
- Normalize structure, not meaning.
- Do not invent compatibility logic.
- Do not infer unstated package logic.
- Do not silently drop anything that affects availability, pricing, or provenance.

The only permitted inference layer is explicitly documented normalization:

- variant header parsing
- footnote cleanup
- legend parsing
- Color and Trim expansion from treatment-level cells to actual interior RPO rows
- price-mode derivation

Everything else stays as published text until build decides how to interpret it.

## Inputs handled by this skill

This replacement spec supports these raw source types inside one model-year workbook:

1. matrix sheets
2. Standard Equipment sheets
3. Equipment Groups sheets
4. Color and Trim sheets
5. long-format option sheets
6. price schedule sheets or staged price tables
7. base price blocks

If a source arrives as PDF instead of a table, stage it into a sheet in the same workbook before ingest. V2 ingest does not OCR PDFs directly.

## Phase 0: Inventory and classification

Inventory every worksheet before extraction and classify it into exactly one of these shapes:

### Matrix sheet

Use this shape when all of these are true:

- `R1C1` is a model-family declaration
- `R2C3` contains the legend
- `R3C1:C3` are the option identity columns
- `R3C4+` are variant headers

Examples: Interior, Exterior, Mechanical, some Standard Equipment tabs.

### Standard Equipment sheet

Accepted shapes:

1. matrix-style Standard Equipment sheet
2. list-style Standard Equipment sheet with section headers, feature rows, and trim/variant inclusion columns

Routing rule:

- matrix-style Standard Equipment sheets flatten directly into `Availability Long`
- list-style Standard Equipment sheets are first normalized into pseudo-matrix observations, then flattened into `Availability Long`

### Equipment Groups sheet

Accepted shapes:

1. group header rows followed by member rows
2. long-format table with one row per group-member relation
3. matrix-style group sheet with variant or trim columns

Output target:

- `Equipment Group Membership`

### Color and Trim sheet

Use the dedicated two-block extraction path. Do not route this shape through matrix logic.

### Long-format option sheet

Already one row per option-context observation. Re-key it into `Availability Long` without reshaping the published meaning.

### Pricing sheet

Tabular schedule with one or more of:

- `RPO`
- `Description`
- `Price`
- `Context`
- `Notes`

If the workbook includes a base-price block and option-price table on the same sheet, classify the sheet as `Pricing sheet` and classify the base-price block separately as `Base price block`.

### Base price block

Any table whose unit of observation is one base vehicle per body/trim.

### Noise

Scratch tabs, pivots, temporary calculations, or sheets that fail all supported shapes.

Noise is ignored, but it still appears in the Phase 1 inventory report.

## Variant header parsing

Use the same header parsing model as the current ingest skill, with these V2 requirements:

- `variant_id` must include `dataset_id`
- `model_family`, `body_style`, `trim`, and `model_code` are all first-class output fields
- if header parsing fails, log a blocking exception and skip the sheet

## Legend parsing and availability normalization

The legend is no longer half-hardcoded. V2 ingest treats availability cells as one base availability state token plus zero or more co-occurring context tokens.

The square and star markers are not generic modifiers. They carry equipment-group or scope-reference context that travels alongside the base availability state.

### Base availability state tokens

- `S` -> `Standard Equipment`
- `A` -> `Available`
- `--` -> `Not Available`
- `D` -> `ADI Available`

If a workbook literally uses `A/D` instead of `D`, preserve `A/D` in the raw token field, normalize the canonical label to `ADI Available`, and log a warning that the workbook used a legacy token form.

### Context tokens

- `■` -> `Included in Equipment Group`
- `□` -> `Included in Equipment Group but upgradeable`
- `*` -> `Indicates availability of feature on multiple models`

If the workbook legend spells a label differently, preserve the workbook wording in `availability_context_labels_raw` or `availability_state_label_raw`, but still normalize to the canonical label above when the meaning matches.

If a token appears in a cell and cannot be mapped from either the canonical table above or the workbook legend, log a blocking exception.

`■` and `□` do not replace explicit `Equipment Group Membership` extraction. They are corroborating context about how a feature participates in a group when the workbook also publishes the concrete group relationships elsewhere.

### Availability Long fields

`Availability Long` now carries:

| Column | Meaning |
|---|---|
| `dataset_id` | From shared contract |
| `model_year` | From shared contract |
| `option_id` | FK to `Option Catalog` |
| `rpo_code` | Readable duplicate |
| `variant_id` | Full namespaced key |
| `model_family` | Parsed from headers |
| `body_style` | Parsed from headers |
| `trim` | Parsed from headers |
| `availability_raw` | Exact literal cell content |
| `availability_state_raw` | `S`, `A`, `--`, `D`, or legacy `A/D` |
| `availability_state_label_raw` | Workbook legend wording for the base-state token when needed |
| `availability_label` | Canonical base availability label |
| `availability_context_tokens_raw` | Pipe-delimited `■|□|*` when present |
| `availability_context_labels_raw` | Pipe-delimited workbook legend wording for context tokens when needed |
| `availability_context_labels` | Pipe-delimited canonical context labels |
| `source_sheet` | Raw sheet name |
| `source_cell` | Cell address |
| `compat_note_ref` | Footnote marker if present |
| `compat_note_text` | Verbatim note text carried through |
| `compat_note_source_type` | One of the shared provenance types |

## Footnote cleanup and note provenance

Apply footnote-suffix cleanup before any identity or availability extraction.

V2 note provenance rules:

- same-sheet resolved footnote -> `footnote_same_sheet`
- numbered in-cell disclosure line -> `cell_inline_disclosure`
- prose note living on the row but outside the cell -> `row_note`
- Color and Trim whole-sheet disclosure -> `sheet_disclosure`
- legend-driven explanatory note -> `legend_note`
- price schedule context prose -> `pricing_context_note`

`compat_note_text` must never mix source types silently. If multiple notes apply, concatenate them with ` || ` and keep the highest-specificity source type first in the concatenated order.

## Option Catalog

`Option Catalog` remains the identity table, but V2 makes classification deterministic.

### Required columns

| Column | Meaning |
|---|---|
| `dataset_id` | |
| `model_year` | |
| `option_id` | `my27_opt_<rpo>` |
| `rpo_code` | Canonical 3-character RPO |
| `name` | Canonical display name |
| `name_raw` | Raw source name |
| `description` | Canonical base description |
| `description_raw` | Raw description segment |
| `section` | Canonical single section |
| `source_sections` | Pipe-delimited observed sections |
| `option_kind` | Canonical kind |
| `option_kind_basis` | Why that kind was assigned |
| `footnote_markers` | Pipe-delimited markers |
| `footnote_texts` | Pipe-delimited resolved texts |
| `source_sheets` | Pipe-delimited raw sheets |
| `notes` | Verbatim carried-through prose |

### `section` precedence

When an RPO appears on multiple sheets, assign `section` using this order:

1. Color and Trim identity rows
2. Equipment Groups
3. Standard Equipment
4. explicit source-sheet section from matrix or long-format sheet
5. `Pricing Only`

Always keep every observed source section in `source_sections`.

### `option_kind` assignment

Assign `option_kind` using this precedence:

1. Color and Trim Block 1 cell RPO -> `interior_color`
2. Color and Trim Block 2 paint row RPO -> `exterior_color`
3. Equipment Group root row -> `package`
4. source section explicitly Wheels -> `wheel`
5. source section explicitly Calipers or name contains `caliper` -> `caliper`
6. source section/name contains `seat belt` -> `seat_belt`
7. source section/name contains `seat` and the RPO is a selectable seat code -> `seat`
8. source section/name contains `stripe` -> `stripe`
9. source section/name contains `spoiler` -> `spoiler`
10. source section/name contains `trim`, `carbon fiber trim`, or `stealth` -> `trim_material`
11. LPO/dealer installed item -> `lpo`
12. otherwise -> `standalone`

If two rules conflict, log a warning and keep the higher-precedence rule.

## Standard Equipment extraction

V2 explicitly supports both matrix-style and list-style Standard Equipment.

### Matrix-style Standard Equipment

Flatten exactly like any other matrix sheet.

- `S` becomes `availability_label = Standard Equipment`
- `--` becomes `Not Available`
- context tokens are preserved

### List-style Standard Equipment

Normalize the list into one observation per included variant or trim.

Rules:

- section header rows become section context only
- feature rows mint or enrich `Option Catalog` rows
- each included trim/variant marker becomes one `Availability Long` row with `availability_label = Standard Equipment`
- if the sheet only states trim inclusion, expand to all matching body styles known in `Base Prices`

If a list-style Standard Equipment row cannot be expanded to concrete variants, log a blocking exception.

## Equipment Groups extraction

V2 adds a durable bundle-membership output.

### Output sheet: `Equipment Group Membership`

| Column | Meaning |
|---|---|
| `dataset_id` | |
| `model_year` | |
| `group_membership_id` | Stable key |
| `group_rpo_code` | Group/package RPO |
| `group_name` | Group/package name |
| `member_rpo_code` | Child/member RPO |
| `member_name` | Child/member name |
| `model_family_scope` | Pipe-delimited family scope |
| `body_scope` | Pipe-delimited body scope |
| `trim_scope` | Pipe-delimited trim scope |
| `inclusion_mode` | `member_of_group`, `required_with_group`, or `standard_via_group` |
| `source_sheet` | |
| `source_row` | |
| `notes` | Verbatim notes |

Extraction rules:

- group header rows mint or enrich the group RPO in `Option Catalog` as `option_kind = package`
- member rows always produce `Equipment Group Membership` rows
- if the source expresses trim-bound inclusion, preserve it in `trim_scope`
- if the source expresses model/body limits, preserve them directly

## Color and Trim extraction

V2 closes the treatment-to-RPO handoff by expanding Block 2 through Block 1.

### `Interior Trim Combos`

Required columns:

| Column | Meaning |
|---|---|
| `dataset_id` | |
| `model_year` | |
| `combo_id` | Stable key |
| `source_sheet` | |
| `source_sheet_origin` | `recommended` or `custom_r6x` |
| `model_family_scope` | Derived family scope |
| `body_scope` | Default `Coupe|Convertible` unless narrowed by source |
| `trim` | Single trim |
| `seat_codes_raw` | Raw source value |
| `seat_code` | Single seat code |
| `seat_type_name` | |
| `seat_trim_material` | |
| `interior_color_name` | Treatment name |
| `interior_color_rpo` | Actual interior RPO |
| `auto_added_rpos` | Blank or `R6X` |
| `footnote_markers` | |
| `footnote_texts` | |
| `source_note` | Whole-sheet or row/cell disclosures |

Family-scope rule:

- `LT` trim rows default to `Stingray|Grand Sport`
- `LZ` trim rows default to `Grand Sport X|Z06|ZR1|ZR1X`
- if a disclosure explicitly narrows the family scope, use the narrower scope

### `Color Combination Availability`

V2 output is no longer treatment-only. Expand Block 2 by joining each treatment column to the matching `Interior Trim Combos` rows so build receives concrete interior RPO rows.

Required columns:

| Column | Meaning |
|---|---|
| `dataset_id` | |
| `model_year` | |
| `pair_id` | Stable key |
| `source_sheet` | |
| `source_sheet_origin` | `recommended` or `custom_r6x` |
| `model_family_scope` | From the joined interior rows |
| `body_scope` | Default `Coupe|Convertible` unless narrowed |
| `trim_scope` | Pipe-delimited trim scope for the joined interior rows |
| `exterior_color_rpo` | Paint code |
| `exterior_color_name` | Paint name |
| `touch_up_paint_number` | |
| `interior_color_name` | Treatment name |
| `interior_color_rpo` | Actual joined interior RPO |
| `availability_raw` | `A` or `--` |
| `availability_label` | Canonical pair label |
| `auto_added_rpos` | Blank, `D30`, `R6X`, or `D30|R6X` |
| `source_note` | Disclosure text |

Pair-label rules:

- Sheet 1 `A` -> `Published Available`
- Sheet 1 `--` -> `Requires D30 Override`
- Sheet 2 `A` -> `Requires R6X`
- Sheet 2 `--` -> `Requires R6X and D30 (one charge collapses per disclosure)`

This sheet does not feed `Availability Long`.

## Price schedule extraction

### Accepted schedule shapes

V2 accepts:

1. one row per RPO-price-note observation
2. one row per RPO with separate trim/body price columns

If the sheet uses separate price columns, first normalize it into row observations before populating `Pricing Long`.

### `Pricing Long`

Required columns:

| Column | Meaning |
|---|---|
| `dataset_id` | |
| `model_year` | |
| `price_id` | Stable key |
| `option_id` | FK |
| `rpo_code` | |
| `price` | Numeric |
| `price_mode` | Canonical mode |
| `price_mode_basis` | Raw signal that produced the mode |
| `context_trim` | Pipe-delimited trim scope |
| `context_body` | Pipe-delimited body scope |
| `context_model` | Pipe-delimited family scope |
| `context_note_raw` | Exact context prose |
| `requires_rpos` | Tokenized prerequisites |
| `excludes_rpos` | Tokenized conflicts |
| `source_sheet` | |
| `source_row` | |

### `price_mode` derivation

- positive numeric -> `paid`
- positive numeric plus explicit `surcharge` or mandatory-charge wording -> `surcharge`
- `0`, `0.00`, `N/C`, `No Charge` -> `no_charge`
- negative numeric or explicit `credit` wording -> `credit`
- blank or `Included` plus corroborated Standard Equipment evidence -> `included_standard`
- blank with no corroboration -> blocking exception

## Base Prices

`Base Prices` must use the shared explicit shape from the contract. Do not rely on a freeform description row as the only source of body or trim.

## Ingest Exceptions

Required columns:

| Column | Meaning |
|---|---|
| `dataset_id` | |
| `model_year` | |
| `exception_id` | Stable key |
| `severity` | `blocking` or `warning` |
| `blocking_scope` | `global`, `model_family`, `variant`, or blank |
| `affected_model_families` | Pipe-delimited |
| `affected_variant_ids` | Pipe-delimited |
| `affected_rpos` | Pipe-delimited |
| `source_sheet` | |
| `source_cell_or_row` | |
| `raw_value` | |
| `reason` | |
| `suggested_action` | |

## Two-phase execution

### Phase 1: Inventory and plan

Report:

- source-sheet inventory and classification
- detected model families and variant counts
- legend tokens observed and whether each token mapped cleanly
- expected row counts by output sheet
- blocking vs warning exceptions discovered before write

Stop for approval.

### Phase 2: Execute

After approval:

- replace the generated ingest sheets in place
- write all eight output sheets
- report actual row counts
- report blocking and warning exception totals

## Failure modes V2 explicitly avoids

- partial legend mapping
- undefined Standard Equipment extraction
- undefined Equipment Groups extraction
- treatment-only Color and Trim handoff
- blank `price_mode` logic
- ambiguous note provenance
- year-unsafe IDs
- build proceeding past blocking ingest defects
