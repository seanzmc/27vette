---
name: corvette-ingest-v3
description: Ingest a Corvette workbook into one simple six-variant matrix sheet plus one separate interiors sheet for the Excel ChatGPT add-in. Stay close to the workbook. Do not infer package logic or build a generalized model.
---

# Corvette Ingest V3

## Purpose

- Ingest one Corvette workbook into a simple intermediate output that stays close to the workbook.
- Copy what the workbook visibly says instead of building a broader data model.
- Normalize only what is required to produce the reduced outputs below.

## Source Sheets In Scope

Handle only these workbook sources:

1. Interior sheets
2. Exterior sheets
3. Mechanical sheets
4. Standard Equipment sheets
5. price schedule sheet(s)
6. interior color / trim sheet(s), handled separately

Ignore all other sheet types unless Sean explicitly asks for them.

## Output Sheets

Create only these generated sheets:

1. Stingray Ingest (combined row-based output for Interior, Exterior, Mechanical, and Standard Equipment content)
2. Grand Sport Ingest (combined row-based output for Interior, Exterior, Mechanical, and Standard Equipment content)
3. Z06 Ingest (combined row-based output for Interior, Exterior, Mechanical, and Standard Equipment content)
4. ZR1 Ingest (combined row-based output for Interior, Exterior, Mechanical, and Standard Equipment content)
5. ZR1X Ingest (combined row-based output for Interior, Exterior, Mechanical, and Standard Equipment content)
6. `Corvette Interiors`

Do not create separate availability, pricing, base price, equipment-group, or package-membership sheets.

## Variant Output

Create one sheet with all variant base prices together, using the same variant names as the output sheets for easy reference.

Source: price schedule sheet(s) only.

Output columns:
| Variant | List Price | DFC Price |
|---|---|---|

Ex. | Corvette Stingray Coupe 1LT |	$71,000.00 | $2,495.00 |

## Main Output: `#Variant Ingest`

Use one combined row-based output for Interior, Exterior, Mechanical, and Standard Equipment content, per variant.

The source sheets are separated by variant, readable in R1 C1.
The sheet names can also help identify the source variant:
Sheet names ending in
1 = Stingray
2= Grand Sport
3= Z06
4= ZR1 & ZR1X
Note: ZR1 and ZR1X content is mixed together in the source sheets and must be separated by reading the variant-specific columns.

Headers must be exactly:

| RPO | Price | Option Name | Description | Detail | Category | 1LT Coupe | 2LT Coupe | 3LT Coupe | 1LT Convertible | 2LT Convertible | 3LT Convertible |
|---|---|---|---|---|---|---|---|---|---|---|

### Row rules

- Create one output row for each workbook row or feature observation that belongs in scope.
- Standard Equipment observations belong in this same sheet.
- If a Standard Equipment row has no published RPO, leave `RPO` blank. Never invent a code.
- If the workbook repeats an item on separate rows or sheets, keep separate rows unless the duplication is obviously identical and safe to collapse.

### Column rules

- `RPO`: published option code exactly as shown, or blank if none is published
- `Price`: matched from the price schedule by `RPO` when a clear match exists; otherwise blank
- `Option Name`: option name from the workbook
- `Description`: base descriptive text from the workbook
- `Detail`: extra trailing detail text if clearly separable; otherwise blank
- `Category`: category information from the workbook, such as `Interior`, `Exterior`, `Mechanical`, or `Standard Equipment`
- variant columns: only `Standard`, `Available`, or `Not Available`

## Variant Columns

Use only these six variant columns (Use the trim level identifiers from the source sheets- retaining source 1LZ vs 1LT, etc. - Example below would only work for Stingray or Grand Sport, not Z06 or ZR1 which use 1LZ/2LZ/3LZ):

1. `1LT Coupe`
2. `2LT Coupe`
3. `3LT Coupe`
4. `1LT Convertible`
5. `2LT Convertible`
6. `3LT Convertible`

Do not add more variant columns.

If a source sheet does not clearly map to these six variants, stop and report the problem instead of guessing.

## Symbol Mapping

Normalize workbook symbols to only these meanings:

- `S` -> `Standard`
- Square -> `Standard`
- `A` -> `Available`
- `A/D` -> `Available`
- dash / hyphen marker -> `Not Available`

Do not preserve extra availability nuance beyond these three values.

Do not create:

- context labels
- availability-state plus context-token systems
- group-related availability labels
- ADI-specific canonical modeling

If a matrix cell contains a symbol that does not clearly map using the rules above, stop and report it. Do not guess.

## Text Extraction

Extract `Option Name`, `Description`, and `Detail` as literally as possible. They will all exist in the same cell in the source sheet, so the main task is to split them.

Use this rule set:

- If the source gives one combined descriptive field, split conservatively:
  - Name = the leading text up to the first comma.
  - `Description` = base descriptive text, after the name, but before any clearly separable trailing detail.
  - `Detail` = detail is described in "In-cell disclosures" below. Move the entire text of the detail to the Detail column, including the leading number.
- If no clean split is visible, keep the full main text in `Description` and leave `Detail` blank.

## Footnote Markers

GM's source documents use superscripted digit markers to tie cell content to sheet-level disclosure footnotes (e.g. `HU7²` where `²` points at footnote 2 on the same sheet). The `.xlsx` export flattens superscript formatting, so these markers arrive in the data as ordinary trailing digits appended to the preceding token with no space. The markers look like part of the RPO or name unless actively un-mangled.

**The rule.** RPO codes are always exactly three characters. Any RPO-like token longer than three characters that ends in a digit has a footnote marker fused to it — the real RPO is the first three characters, the trailing digits are the marker. Similarly, any name or description that ends directly in a digit with no space has a footnote marker fused to it — the real name is everything up to the trailing digit run, the trailing digits are the marker.

Color and Trim sheets are the only sheets where disclosures can be whole-sheet, page-specific disclosures. On every other sheet, disclosures apply only to the row where the marker occurs unless the source explicitly says otherwise.

- **In-cell disclosures** are written into the same cell as the option name. They always begin after a line break with `1. ` following the main option text. If a second disclosure is present, it begins after another line break with `2. `. Preserve those line breaks when reading the cell so the option name and disclosure text stay distinct.

**Apply this cleanup before anything else extracts identity or RPO codes from a cell.** If ingest builds rows from un-cleaned cells, it will mint phantom RPOs like `HU76`, `HUA6`, `EL98` that do not exist in GM's system. That is a data integrity bug. Fix it at read time.

Do not invent or rewrite prose.

## Standard Equipment Handling

- Do not give Standard Equipment its own special output model.
- Combine Interior / Exterior / Mechanical Standard Equipment observations into `Corvette Ingest`.
- Use the same six variant columns and the same three simplified values:
  - `Standard`
  - `Available`
  - `Not Available`

When the workbook visibly answers the value for a variant, copy it directly.

## Price Matching

- Match price from the price schedule by `RPO` when possible.
- Keep pricing logic simple.
- If one clear price is found for that `RPO`, place it in `Price`.
- If no price is found, leave `Price` blank.
- If multiple conflicting prices exist and no simple literal match is clear, leave `Price` blank and report the ambiguity.

Do not create:

- price modes
- surcharge / credit / included-standard taxonomies
- pricing context systems

## Separate Interior Output: `Corvette Interiors`

Handle interior color / trim sheets separately from the main ingest output.

Do not force interior combinations into the other Ingest sheets.

Use a simple row-based output with these headers:

| Trim | Seat | Interior Code | Interior Name | Material | Detail from Disclosure | Color Overrides |
|---|---|---|---|---|---|---|

### Interior rules

- List every possible interior color combination shown by the workbook.
- Slash combinations should be separated into multiple rows, one per combination, with the same `Interior Code` and `Interior Name` for each row.
- Keep coded notes for override or special-combination logic when the workbook provides them.
- Keep the structure literal and workbook-facing.
- Color Overrides should list the RPO codes of any exterior colors that the workbook says are incompatible with that interior, identified by a -- in the sheets lower color matrix. If no incompatibilities are listed, leave blank.
Move a copy of the 10 exterior colors with their RPO codes into each variant sheet in the "Exterior" category, matching the price for the premium colors and listing the rest as $0.
Do not build a treatment-to-RPO abstraction unless the workbook already makes that mapping explicit and it is required to list the combinations correctly.

## Validation And Failure Handling

Use lightweight validation only.

Stop and report the issue if any of these happen:

- the six variant columns cannot be identified clearly
- a non-interior matrix cell uses a symbol that does not map cleanly to `Standard`, `Available`, or `Not Available`
- a source row cannot be read well enough to place its literal workbook values into the required output columns
- an interior combination cannot be listed as a concrete row from the sheet

Do not stop for these cases:

- price not found for an `RPO`
- `RPO` missing on a Standard Equipment feature
- `Detail` left blank because no clean split exists

In those cases, leave the field blank and continue.

## Must Not Do

- Never make an option available for a variant unless the source matrix indicates it.
- Never broaden availability across all variants.
- Never infer package membership.
- Never process Equipment Groups sheets.
- Never replace literal workbook structure with a more abstract model unless necessary for the simplified output.
- Never create generalized package logic.
- Never create bundle-membership extraction.
- Never create broad rule systems.
- Never create extra downstream-oriented tables unless they are part of the two outputs above.
- Never infer compatibility logic.
- Never invent missing RPOs, descriptions, details, or notes.
- When the workbook visibly answers the question, copy it instead of interpreting it.
