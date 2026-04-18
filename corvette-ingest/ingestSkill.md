---
name: corvette-ingest
description: Ingest raw Chevrolet Corvette order-guide exports and GM price schedules into a flattened intermediate layer for downstream configurator use. Use this skill whenever Sean shares a new GM export workbook (Standard Equipment 1-4, Interior 1-4, Exterior 1-4, Mechanical 1-4, Equipment Groups 1-4, Options Long, Pricing), a new model-year price schedule document, or asks to refresh, re-ingest, normalize, or flatten raw Corvette source data. Trigger even if Sean does not use the word "ingest" — phrases like "new export", "new model year", "refresh the source data", "update the catalog from GM", "process this price schedule", or "capture what GM sent" all indicate ingest work. Do NOT use this skill when Sean is editing per-variant configurator sheets, building out order-form logic, or working in the Stingray / Grand Sport / Z06 / E-Ray / ZR1 / ZR1X build sheets — that is the corvette-build skill's job.
---

# Corvette Ingest

Faithfully capture what GM exported. Produce a clean flattened intermediate layer. Do not invent logic, do not infer rules from prose, do not merge with human interpretation of how the order form should cascade.

The downstream consumer is the `corvette-build` skill, which turns this flattened layer into per-variant configurator data.

## Core principle: preserve source intent

If the source says "Available" on a cell, it is Available. If a compatibility note says "Requires Z51", that text stays in a note column — it does NOT get extracted into a structured rule row. The build skill decides what becomes a rule and what becomes an enumerated row.

The one exception: structural flattening. A 4-way-split matrix sheet (Interior 1 / 2 / 3 / 4) is genuinely one logical table that GM split for print layout. Combining those into one long-format table is flattening, not interpretation.

## Determining variant scope from headers

Matrix-style sheets in a GM export follow a consistent header pattern regardless of which sheet they appear in. Always drive scope detection from the header cells, never from the sheet name.

**R1 C1** carries the model family declaration. Observed forms include single families (`Stingray`, `Grand Sport`, `Z06`, `E-Ray`, `ZR1`, `ZR1X`, `Grand Sport X`) and combined families (`ZR1 and ZR1X`). Treat the text as a human label and extract model families from it rather than expecting an exact match — for example `"ZR1 and ZR1X"` yields two model families. A future sheet could declare `"Z06 and Grand Sport X"` or similar; handle it the same way.

**R2 C3** holds the legend of cell codes (`S`, `A`, `--`, `D`, `■`, `□`, `*`). Its presence is a strong confirmation that the sheet is a matrix sheet. If R2 C3 is blank or carries different text, re-examine the sheet's structure before proceeding.

**R3** holds the column headers. Columns 1-3 are typically `Orderable RPO Code`, `Ref. Only RPO Code`, `Description`. From column 4 onward, each header is a multi-line string encoding a specific variant, e.g. `"Coupe\n1YC07\n1LT"`, `"Grand Sport Convertible\n1YE67\n3LT"`, `"ZR1X Coupe\n1YS07\n1LZ"`.

Parse each variant header into three pieces by splitting on newlines:
- **Line 1** — a body style token, optionally prefixed with the model family. Strip any model-family prefix to get just the body style (`Coupe` or `Convertible`).
- **Line 2** — the 5-character GM model code (e.g. `1YC07`, `1YS67`).
- **Line 3** — the trim code (e.g. `1LT`, `3LZ`).

When Line 1 has no model-family prefix (as in Stingray's `"Coupe\n1YC07\n1LT"`), derive the model family from R1 C1. When Line 1 is prefixed (as in ZR1X's `"ZR1X Coupe\n1YS07\n1LZ"` on a combined sheet), trust the prefix and validate it against R1 C1's declared families.

Trim codes also narrow model family even when the sheet header is broad. Trims ending in `LT` are always `Stingray` or `Grand Sport`. Trims ending in `LZ` are always `Grand Sport X`, `Z06`, `ZR1`, or `ZR1X`. Use that as a validation rule and as a tie-breaker when a combined-family declaration is broader than a single column's actual scope. Do not assign a model family that conflicts with the trim suffix.

The model code on Line 2 is the authoritative variant identifier in GM's system. Build `variant_id` from the parsed pieces using a stable convention: `var_<model_family_slug>_<body_slug>_<trim>` (e.g. `var_stingray_coupe_2lt`, `var_grand_sport_x_convertible_3lz`). Keep the model code in a separate `model_code` column — do not try to reverse-engineer it from the variant_id.

**Sanity checks to run on every matrix sheet before extraction:**

- R1 C1 is non-blank and parses to at least one model family
- R2 C3 contains the S/A/--/D legend
- R3 C1-C3 match the `Orderable RPO Code / Ref. Only RPO Code / Description` pattern
- R3 C4 onward are all non-blank and each parses cleanly into body/code/trim
- Every model family extracted from a variant header exists in R1 C1's declaration

If any check fails, log the sheet in `Ingest Exceptions` with the specific failure and skip it. Do not guess.

## Footnote-suffix cleanup (applies to every sheet)

GM's source documents use superscripted digit markers to tie cell content to sheet-level disclosure footnotes (e.g. `HU7²` where `²` points at footnote 2 on the same sheet). The `.xlsx` export flattens superscript formatting, so these markers arrive in the data as ordinary trailing digits appended to the preceding token with no space. The markers look like part of the RPO or name unless actively un-mangled.

**The rule.** RPO codes are always exactly three characters. Any RPO-like token longer than three characters that ends in a digit has a footnote marker fused to it — the real RPO is the first three characters, the trailing digits are the marker. Similarly, any name or description that ends directly in a digit with no space has a footnote marker fused to it — the real name is everything up to the trailing digit run, the trailing digits are the marker.

Disclosures are always same-sheet — a marker in a Color and Trim 1 cell points at a footnote elsewhere on Color and Trim 1, never another sheet. The ingest skill never needs to resolve a marker across sheets.

Color and Trim sheets are the only sheets where disclosures can be whole-sheet, page-specific disclosures. On every other sheet, disclosures apply only to the row where the marker occurs unless the source explicitly says otherwise.

In-cell disclosures are written into the same cell as the option name. They always begin after a line break with `1. ` following the main option text. If a second disclosure is present, it begins after another line break with `2. `. Preserve those line breaks when reading the cell so the option name and disclosure text stay distinct.

**Apply this cleanup before anything else extracts identity or RPO codes from a cell.** If ingest builds Option Catalog entries or Availability Long rows from un-cleaned cells, it will mint phantom RPOs like `HU76`, `HUA6`, `EL98` that do not exist in GM's system. That is a data integrity bug. Fix it at read time.

**Cleanup logic:**

1. For every string cell that might carry an RPO or a display name, run a footnote-suffix check.
2. If the cell value is a candidate RPO token (all uppercase letters + digits, typical length 3-5) longer than 3 characters and ends in one or more digits, split at the 3-character boundary. The real RPO is the first three characters; the trailing digits are the footnote marker.
3. If the cell value is a name, description, or other display string and ends directly in a digit run with no separating whitespace, split at the boundary between the last non-digit character and the digit run. The real name is everything before; the digit run is the footnote marker.
4. Record the original un-cleaned cell value in a `raw_value` or `name_raw` column for provenance. Record the extracted footnote marker in a separate column or as a pipe-delimited list if multiple markers are present (rare but possible).
5. On Color and Trim sheets, collect the distinct marker values and attempt to resolve each one to its whole-sheet disclosure text. On every other sheet, resolve the marker only against the row where it occurs, including disclosures embedded in the same cell after line breaks like `\n1. ` and `\n2. `. If the disclosure can't be located, log each unresolved marker in `Ingest Exceptions` — do not silently drop them.

**Cases to handle carefully:**

- A cell whose content is just a 3-character RPO (`HU6`, `AQ9`, `AE4`) is already clean — no trailing digit fusion. The length check protects this.
- A cell whose content is a 2-character token followed by a digit (`GT1 buckets`, `GT2 / Competition buckets`) is not an RPO at all — `GT1` and `GT2` are seat-type labels, not RPOs. RPO detection should only trigger on tokens that match the RPO shape (letter-digit-letter-digit pattern or all-uppercase-alphanumeric, typical length 3).
- A cell value `1YC07` is a GM model code, not an RPO with a footnote. Model codes have a consistent shape (digit + letter + 3 digits) and should be recognized before the RPO footnote rule runs.
- A cell value like `Napa leather seating surfaces with perforated sueded microfiber inserts5` has a footnote `5` on a long descriptive string. Strip it; preserve in `name_raw`.

**Reporting.** In the Phase 1 plan, report the count of distinct footnote markers detected across the export and whether each one resolved to a disclosure text. This gives Sean visibility into whether ingest has full provenance for every disclosed caveat.

## Color and Trim extraction

Color and Trim sheets are structurally different from matrix sheets. They cover all variants together, use a two-block layout, and encode three distinct kinds of information at once. They need their own extraction path.

**Identifying a Color and Trim sheet.** R1 C1 holds a label like `Recommended` or `Custom Interior Trim and Seat Combinations` rather than a model family. R2 C1 holds a shorter legend (just `A` and `--`, not the full S/A/--/D/■/□/* set). The sheet then has two distinct data blocks separated by a banner row in the middle that repeats the `Interior Colors` header text.

**Block 1 (Seat/Trim × Interior Color).** The first data block captures which seat-and-trim combinations can be ordered in which interior colors, and what RPO represents that intersection.

- Columns 1-4: `Decor Level`, `Seat Type`, `Seat Code`, `Seat Trim` (seat material description).
- Columns 5 onward: interior color *treatments* — these are not atomic colors. A column header can be a plain color (`Jet Black`), a dipped or styled color (`Adrenaline Red Dipped`, `Ultimate Suede Jet Black`), or an asymmetric two-tone treatment (`Asymmetrical Adrenaline Red / Jet Black`). Treat the column header as an opaque label that identifies the interior treatment.
- Data rows: each row is one (decor × seat × seat-trim) combination. Cell values are either an interior color RPO (like `HTA`, `HUU`, `EJH`) — meaning the combination is available and this RPO represents the entire (row × column) intersection — or `--` for not available.
- The `Decor Level` column may hold comma-separated trim codes like `1LT, 1LZ` or `3LT, 3LZ` — expand these into separate logical trim scopes. A row with `3LT, 3LZ` means the RPO in that row applies to both 3LT and 3LZ trims.
- The `Seat Code` column may hold a slash-separated pair like `AH2 / AE4`. Expand these into separate rows — one per seat code — carrying the same interior color RPO, trim, and seat_trim. Different seat codes have different downstream compatibility and companion options, so grouping them loses information the build skill needs.

**Block 2 (Exterior Paint × Interior Color).** The second data block captures which exterior paints are paired with which interior treatments. The interior color columns match Block 1 exactly.

- Columns 1-4: `Exterior Solid Paint` (paint name), typically blank, `Color Code` (exterior RPO), `Touch-Up Paint Number`.
- Columns 5 onward: same interior color treatment columns as Block 1.
- Data rows: each row is one exterior paint. Cell values are `A` (this exterior/interior pairing is published as available) or `--` (not published, and therefore requires `D30` Color Combination Override to be ordered).

**The D30 and R6X rules.** Any exterior/interior combination that does not appear as `A` in Block 2 of its own sheet requires `D30` Color Combination Override to be ordered. Record this explicitly in the output; do not leave it implicit.

The difference between Sheet 1 and Sheet 2 is a separate axis: any interior selected from Sheet 2 requires `R6X` Custom Interior Trim and Seat Combinations *regardless* of whether the exterior/interior pairing is published as `A` or `--`. R6X is charged once on any Sheet 2 interior selection.

Per the disclosure on Sheet 2, if both R6X and D30 apply to the same build (an interior from Sheet 2 combined with an exterior that Sheet 2 marks `--`), both option codes exist on the build but only one is charged. The ingest skill does not decide how that pricing collapses — it just records both requirements accurately so the build skill and the form can handle the pricing collapse downstream.

**Availability label states for Block 2 cells:**
- Sheet 1 `A` → `Published Available`
- Sheet 1 `--` → `Requires D30 Override`
- Sheet 2 `A` → `Requires R6X`
- Sheet 2 `--` → `Requires R6X and D30 (one charge collapses per disclosure)`

**Footnote markers.** Color and Trim sheets carry trailing footnote digits on names (e.g. `Adrenaline Red2`, `Sebring Orange Tintcoat9`, `Natural Dipped4`) and sometimes on RPOs (e.g. `HU76` is really `HU7` with footnote `6`). Apply the footnote-suffix cleanup described above. Preserve raw strings in `name_raw` / `raw_value` columns. Resolve markers to disclosure text from the same sheet; log unresolved markers in `Ingest Exceptions`.

**Outputs Color and Trim feeds.**

1. Every *interior color treatment* column header in Block 1 becomes one row in `Option Catalog` with `option_kind = interior_color`. The "color" here is the treatment as a whole — dipped, asymmetric, and suede treatments each get their own `option_id`. The interior color RPO is not in the column header; it lives in the cell and becomes the canonical `rpo_code` for that (row × column) intersection. Because the same interior color treatment (column) can have different RPOs across different seat/trim rows, each distinct cell-RPO becomes its own Option Catalog entry, with the color-treatment name copied into its `name` and the seat/trim scope captured in `notes`.

2. Every *exterior paint* in Block 2 becomes one row in `Option Catalog` with `option_kind = exterior_color`. Capture the paint name, `rpo_code` from the Color Code column, and `touch_up_paint_number` in notes. These are also the primary source for exterior paints in the main options list — Color and Trim is authoritative for exterior colors, not the Exterior matrix sheets.

3. Seat-and-trim combinations from Block 1 feed a new output sheet `Interior Trim Combos` (see schema below).

4. Exterior/interior pairings from Block 2 feed a new output sheet `Color Combination Availability` (see schema below).

### Output sheet: `Interior Trim Combos`

One row per published (trim × seat × seat_trim × interior_color_treatment) intersection from Block 1 of either Color and Trim sheet. `3LT, 3LZ` in the source row expands to two rows. `AH2 / AE4` in the source also expands to two rows — one per seat code — because seat codes carry different compatibility downstream.

Footnotes attached to Block 1 cells, column headers, or row labels are carried into every expanded row that row or column produced. The row already establishes the trim scope, so do not add separate trim/model/body footnote-scope columns here. If the disclosure text itself clearly names a specific model family, keep that disclosure with the rows it unambiguously applies to. If there is no reliable way to tell whether a disclosure in this section is more specific than the row already implies, do the default: keep the full disclosure text with the row and do not try to split or parse extra scope from it.

| Column | Meaning |
|---|---|
| `combo_id` | Stable key, e.g. `ctc_3lt_ah2_htt` |
| `source_sheet` | `Color and Trim 1` or `Color and Trim 2` |
| `combo_source` | `recommended` (from Sheet 1) or `custom_r6x` (from Sheet 2, requires R6X) |
| `trim` | Single trim code: `1LT`, `2LT`, `3LT`, `1LZ`, `2LZ`, `3LZ` |
| `seat_codes_raw` | The raw seat code cell value as it appeared in the source (`AQ9`, `AH2 / AE4`, `AUP`) |
| `seat_code` | Single seat RPO for this row (`AQ9`, `AH2`, `AE4`, `AUP`) — slash-separated source pairs are expanded into one row per code |
| `seat_type_name` | From the `Seat Type` column |
| `seat_trim_material` | From the `Seat Trim` column |
| `interior_color_treatment_name` | The column header as it appears in the source |
| `interior_color_rpo` | The RPO from the cell |
| `requires_rpos` | `R6X` if combo_source is custom_r6x, else blank |
| `notes` | |

### Output sheet: `Color Combination Availability`

One row per (exterior_rpo × interior_color_treatment) pairing from Block 2 of either Color and Trim sheet. Every pairing gets a row — both `A` and `--` — because the build skill needs to know which combinations are published-unavailable (and therefore D30-able) versus simply never offered.

| Column | Meaning |
|---|---|
| `pair_id` | Stable key, e.g. `cca_g26_jet_black` |
| `source_sheet` | `Color and Trim 1` or `Color and Trim 2` |
| `combo_source` | `recommended` or `custom_r6x` |
| `exterior_color_rpo` | |
| `exterior_color_name` | |
| `touch_up_paint_number` | |
| `interior_color_treatment_name` | |
| `availability_raw` | `A` or `--` |
| `availability_label` | One of: `Published Available` (Sheet 1 `A`), `Requires D30 Override` (Sheet 1 `--`), `Requires R6X` (Sheet 2 `A`), `Requires R6X and D30 (one charge collapses per disclosure)` (Sheet 2 `--`) |
| `notes` | |

**Important:** the D30 inference is not read from the source. The Color and Trim sheets show `--` to mean "not a published combination." Per Sean's ordering rules, customers can still order that combination by adding D30. Record the inference explicitly in `availability_label` so downstream consumers don't have to re-derive it. The R6X requirement on all Sheet 2 selections is similarly inferred from the sheet-level disclosure, not from the cells themselves.

### Relationship to matrix-sheet exterior colors

 Color and Trim is authoritative for exterior paint identity (name, RPO, touch-up number) and cross-interior compatibility. The matrix sheets are authoritative for per-variant availability. Both feed the Option Catalog (with Color and Trim winning on identity fields) and both feed Availability Long (matrix sheets populate the per-variant rows, Color and Trim populates the color-combination cross-reference).

## Inputs this skill handles

1. **GM order-guide export workbook** — a multi-sheet .xlsx with raw matrix tabs grouped by section (Standard Equipment, Equipment Groups, Interior, Exterior, Mechanical, Wheels, Color and Trim, Options Long). Sections are typically split across multiple sheets, one per model family or group of related model families — but the split is not stable across model years. Never assume which model a sheet covers from the sheet name or its trailing number. Always read the sheet's header rows to determine variant scope. See **Determining variant scope from headers** below.

2. **GM price schedule** — usually a separate document (PDF, Word, or a Pricing tab). Lists base model prices and option prices, often with trim-context notes like "2LT/3LT only" or "LT6 and LT7 Engines only". Prices may vary by trim for the same RPO.

3. **Prior-year ingested workbook** — for model-year updates, the previous year's flattened layer is a useful reference for deltas but not a source of truth for the new year.

## Outputs this skill produces

Write to newly created output sheets in the same workbook/document being prepared for ingest. Do not edit raw source sheets in place.

The full output set is seven sheets: `Option Catalog`, `Availability Long`, `Pricing Long`, `Base Prices`, `Interior Trim Combos`, `Color Combination Availability`, and `Ingest Exceptions`. The first four are primary; the next two are Color and Trim extractions documented in the section above; the last logs everything that could not be cleanly placed.

### 1. `Option Catalog` (identity only)

One row per distinct RPO observed across all sources. Identity fields only — no price, no availability, no rules.

| Column | Meaning |
|---|---|
| `option_id` | Stable workbook key, lowercase `opt_<rpo>` format |
| `rpo_code` | GM RPO code (uppercase, exactly 3 characters after footnote cleanup) |
| `name` | Short display name (footnote digits stripped) |
| `name_raw` | Original name as it appeared in the source, including any fused footnote digits |
| `description` | Longer description when source provides one (footnote digits stripped) |
| `description_raw` | Original description as it appeared in the source |
| `section` | Top-level bucket (Interior, Exterior, Mechanical, Wheels, Standard Equipment, Equipment Groups, Color and Trim, Accessories) |
| `option_kind` | One of: `standalone`, `package`, `seat`, `seat_color`, `exterior_color`, `interior_color`, `wheel`, `caliper`, `spoiler`, `stripe`, `trim_material`, `accessory`, `lpo` |
| `footnote_markers` | Pipe-delimited list of footnote digit markers attached to this RPO or its name across sources |
| `footnote_texts` | Pipe-delimited resolved disclosure texts for each marker, or `UNRESOLVED` if the marker could not be located on its source sheet |
| `source_sheets` | Pipe-delimited list of raw sheet names where this RPO appeared |
| `notes` | Source compatibility prose copied verbatim |

If the same RPO appears with slightly different names across sheets, pick the most specific one for `name` and record the variants in `notes`. Flag ambiguous cases to Sean instead of silently resolving them.

If an option is flagged with no price in the price schedule, compare its RPO against the RPOs found on the Standard Equipment sheets. When the same RPO is present there, treat that as confirmation that the item is standard equipment and reflect that in `Option Catalog` using `section = Standard Equipment` and the most specific standard-equipment identity text available. If a no-price RPO does not appear on Standard Equipment, do not auto-promote it to standard equipment; leave the catalog identity as-is and log the mismatch in `Ingest Exceptions`.

### 2. `Availability Long` (flattened variant × option matrix)

One row per (variant × option) observation from the raw matrix sheets. This is the flattened version of Options Long / the 1-4 split sheets.

| Column | Meaning |
|---|---|
| `option_id` | FK to Option Catalog |
| `rpo_code` | Redundant but kept for readability |
| `variant_id` | `var_<model>_<body>_<trim>` e.g. `var_stingray_coupe_2lt` |
| `model_family` | Stingray, Grand Sport, Z06, E-Ray, ZR1, ZR1X |
| `body_style` | Coupe / Convertible |
| `trim` | 1LT, 2LT, 3LT, 1LZ, 2LZ, 3LZ, etc. |
| `availability_raw` | Exact source cell value: `S`, `A`, `A/D`, `--`, `■`, or similar |
| `availability_label` | Source's own label: `Standard Equipment`, `Available`, `Available / ADI Available`, `Not Available`, `Included in Equipment Group` |
| `source_sheet` | Raw sheet name |
| `source_cell` | e.g. `Interior 1!D4` for traceability |
| `compat_note_ref` | Footnote marker if the cell carries one |
| `compat_note_text` | Full footnote text if present |

Do NOT collapse `A/D` and `A` into a single state. Do NOT drop `Not Available` rows. The build skill decides what to do with them.

### 3. `Pricing Long` (flattened price schedule)

One row per (RPO × price context) from the price schedule. A single RPO with two trim-dependent prices produces two rows.

| Column | Meaning |
|---|---|
| `price_id` | Stable key, e.g. `prc_ae4_01` |
| `option_id` | FK to Option Catalog |
| `rpo_code` | |
| `price` | Numeric price |
| `price_mode` | `paid`, `included_standard`, `no_charge`, `credit`, `surcharge` |
| `context_trim` | Pipe-delimited trim codes where this price applies, or blank for all |
| `context_body` | Pipe-delimited body styles where this price applies, or blank for all |
| `context_model` | Pipe-delimited model families where this price applies, or blank for all |
| `context_note_raw` | Exact context prose from the source |
| `requires_rpos` | Pipe-delimited RPOs named as prerequisites in the source note |
| `excludes_rpos` | Pipe-delimited RPOs named as conflicts in the source note |
| `source_document` | Filename of the price schedule |
| `source_page_or_row` | Location reference |

Token extraction from context notes (`context_note_raw` → `context_trim`, `requires_rpos`, etc.) is pattern-matching, not interpretation. If the note says "2LT/LZ or 3LT/LZ", that tokenizes cleanly to `context_trim=2LT|2LZ|3LT|3LZ`. If a note is ambiguous ("available with performance packages"), leave the tokenized fields blank and keep the raw note — don't guess what counts as a performance package.

When the price schedule flags an RPO with no price, cross-check that RPO against Standard Equipment. If the RPO appears on Standard Equipment, treat the no-price state as standard-equipment evidence rather than a missing paid price. If it does not appear there, keep the no-price record as written and log the unresolved pricing/status mismatch in `Ingest Exceptions`.

### 4. `Base Prices`

One row per variant with base pricing.

| Column | Meaning |
|---|---|
| `variant_id` | |
| `model_code` | e.g. `1YC07` |
| `description` | "Corvette Stingray Coupe 2LT" |
| `list_price` | |
| `msrp_c` | |
| `dfc` | Destination and Freight Charge |

### 5. `Ingest Exceptions`

Any row the ingest could not cleanly place. Ambiguous RPOs, footnotes without referents, cells with unexpected values, price notes that didn't tokenize. Do not silently drop anything — log it here.

| Column | Meaning |
|---|---|
| `exception_id` | |
| `source_sheet` | |
| `source_cell_or_row` | |
| `raw_value` | |
| `reason` | |
| `suggested_action` | What Sean or the build skill should do |

## How to work

### Step 1: Inventory the inputs

Walk every sheet in the raw export. For each one, inspect its contents to classify it as:
- **Matrix sheet** (R1 C1 holds a model family label, R2 C3 holds the S/A legend, R3 holds variant-column headers) — feeds Availability Long
- **Color and Trim sheet** (has a distinct two-block structure covering all variants together — see **Color and Trim extraction** below) — feeds multiple outputs
- **Long-format sheet** (already one row per option × variant, like Options Long) — feeds Availability Long directly
- **Pricing sheet** (option × price × context) — feeds Pricing Long
- **Base pricing sheet** (variant × price, like the `Pricing` tab's Base Model Prices block) — feeds Base Prices
- **Footnote/legend sheet** — reference only, capture notes
- **Noise** (pivot tables, scratch work, sheets that fail the matrix sanity checks and don't match any other shape) — ignore

Classification is driven by what's inside the sheet, not by its name. A sheet called `Interior 7` that passes the matrix sanity checks for a model family not previously seen in Corvette history (for example Grand Sport X mid-year) is a matrix sheet covering that model family. A sheet called `Interior 1` whose R1 C1 has changed from last year's `Stingray` to something else is covering what R1 C1 now says, not what the name implies.

Show Sean the classification before processing, including for each matrix sheet: the sheet name, the model families extracted from R1 C1, the count of variant columns parsed from R3, and any sanity-check failures. Ask about anything ambiguous.

### Step 2: Extract Option Catalog first

Build the RPO universe from every source. This is the one table every other output links to. Get it stable before moving on.

Flag RPOs that appear in the price schedule but not in the order-guide export, and vice versa — those are exceptions Sean needs to see.

### Step 3: Flatten availability

Walk each matrix sheet. For each cell in the variant-crossing region, emit one `Availability Long` row. Preserve the raw cell value; add the label mapping in a separate column. Keep `source_cell` so Sean can trace anything suspicious back to its origin.

For sheets already in long format (Options Long), just re-key to match the schema and pass through.

### Step 4: Extract Color and Trim

Process both Color and Trim sheets (if present). For each one:
- Parse Block 1 (Seat/Trim × Interior Color) into `Interior Trim Combos` rows. Expand comma-separated `Decor Level` values into one row per trim.
- Add one Option Catalog entry per distinct interior color RPO observed in Block 1 cells (`option_kind = interior_color`).
- Parse Block 2 (Exterior Paint × Interior Color) into `Color Combination Availability` rows. Every cell produces a row, including `--` cells (mapped to the appropriate D30/R6X availability_label).
- Add one Option Catalog entry per exterior paint row in Block 2 (`option_kind = exterior_color`). Treat Color and Trim as authoritative for exterior paint identity; merge with any entries already in Option Catalog from Exterior matrix sheets, preferring the Color and Trim name and touch-up number.
- Strip footnote digits from names for canonical fields; preserve raw strings.

### Step 5: Flatten pricing

Walk the price schedule. For each priced item, emit one or more `Pricing Long` rows — one per distinct context. Tokenize context notes using documented patterns only; leave ambiguous notes in `context_note_raw` unprocessed.

For items flagged with no price, compare the RPO to `Option Catalog` entries sourced from Standard Equipment / Standard Equipment sheets. If there is a match, update or merge the `Option Catalog` entry so that RPO is explicitly treated as standard equipment. If there is no match, do not guess whether it is standard or optional — preserve the no-price pricing record and log the discrepancy in `Ingest Exceptions` for Sean to review.

### Step 6: Log exceptions

Every piece of source data that didn't end up somewhere in outputs 1-4 goes in `Ingest Exceptions`. Include a row count reconciliation: "Source had N option × variant cells; output has M rows; difference accounted for by [list]".

## Two-phase execution

For any non-trivial ingest:

**Phase 1 — Report and plan.** Produce a written report describing:
- What sheets exist in the source
- How they'll be classified
- How many distinct RPOs are expected in Option Catalog
- Expected row counts for Availability Long and Pricing Long
- Any ambiguities flagged for Sean's review

Stop here. Wait for Sean to confirm before creating and populating the new output sheets in the same document.

**Phase 2 — Execute.** Only after Phase 1 is approved. Write the seven output sheets. Report the actual row counts back and note any deviation from the Phase 1 estimates.

## What this skill does NOT do

- Does not extract rules from compatibility notes. `"Requires Z51"` stays as a note in `Option Catalog.notes` or `Availability Long.compat_note_text`. The build skill decides if it becomes a structured rule.
- Does not enumerate legal combinations. No row like "AE4 + suede + red + two-tone = legal". That's the build skill.
- Does not merge model years. Each model year gets its own ingested workbook.
- Does not modify the raw source sheets. Always write to newly created output sheets in the same workbook/document.
- Does not consult prior-year structured interpretations (Option Rules Clean, Choice Groups Clean, etc.) — those belong to the build skill's migration pass.

## Failure modes to avoid

- Minting phantom RPOs by failing to strip fused footnote digits. `HU76` is not an RPO — it is `HU7` with footnote marker `6`. Ingest must apply the footnote-suffix cleanup before any cell value is accepted as an RPO, display name, or description.
- Inferring a sheet's model coverage from its name or trailing number. Sheet names are labels, not schema. Every year GM may add, remove, split, or combine model families, and the per-section sheet counts will shift. Always read R1 C1 and the R3 variant headers.
- Treating a Color and Trim sheet as a matrix sheet. It will fail the matrix sanity checks (R1 C1 is not a model family, R2 C3 does not hold the full S/A legend) — log the failure and route it through the Color and Trim extraction path instead of skipping it.
- Dropping `--` cells from Color and Trim Block 2. Every `--` carries information (the combination requires D30 to order) that the build skill needs.
- Treating the interior color column headers as atomic colors. They are full interior treatments — a dipped color and its plain counterpart are distinct treatments with different RPOs.
- Silently resolving ambiguous RPO name variants. Log them.
- Dropping `Not Available` rows because they "aren't useful". The build skill needs the explicit unavailability signal.
- Collapsing `A/D` (ADI Available) into `A` (Available). They mean different things for allocation.
- Tokenizing prose that doesn't have clean patterns. If a note says "available with appropriate package", the tokenized fields stay blank.
- Writing output before Phase 1 approval.
