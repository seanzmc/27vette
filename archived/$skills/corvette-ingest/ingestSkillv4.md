---
name: ingestSkillv4
revision: corvette-ingest-v4.1
description: >
  Strict, database-ready ingest logic for the 2027 Chevrolet Corvette workbook.
  Requires an approved preflight manifest and structural validation before any
  generated workbook output is written. Preserves raw source values, applies
  context-aware normalization, resolves Z06/ZR1/ZR1X layout conflicts, and
  emits traceable normalized outputs plus review projections.
---

# `ingestSkillv4` — Revised Markdown Documentation

## 1. Purpose

`ingestSkillv4` ingests the 2027 Chevrolet Corvette pricing/configuration workbook into database-ready, row-based outputs while preserving full source traceability.

The revised skill must:

- Validate an approved **preflight manifest** and workbook structure before writing any generated workbook output.
- Enforce exact workbook shape rules from `WorkbookShape.md`.
- Address all high-impact constraints identified in `skill_gaps.md`.
- Preserve source sheets unchanged.
- Preserve raw values and write normalized/database fields separately.
- Resolve the Z06/ZR1/ZR1X layout conflict correctly.
- Distinguish standard matrix dash semantics from Color & Trim dash semantics.
- Treat Equipment Groups as reference data only.
- Normalize prices, RPOs, symbols, footnotes, and text contextually.
- Produce deterministic, idempotent, auditable outputs.

---

## 2. Resolved Policy Decisions

| Topic                        | Final Policy                                                                                                                                                                | Reason                                                                                                                 |
| ---------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------- |
| Canonical output shape       | Use normalized database tables as canonical outputs. Matrix-style sheets are review projections.                                                                            | Long-form normalized tables avoid hardcoded six-column assumptions and are safer for database loading.                 |
| ZR1/ZR1X review output       | Emit separate ZR1/ZR1X trim/body review sheets.                                                                                                                             | This satisfies the requirement that ZR1 and ZR1X output separately for `1LZ`/`3LZ` and each body style.                |
| Extra sheets                 | Unexpected non-generated source sheets are fatal unless explicitly allowed by the preflight manifest. Prior approved generated sheets are ignored during source validation. | The workbook is expected to have a strict 23-source-sheet shape. Extra source-like sheets can create ambiguous ingest. |
| Hidden required content      | Hidden required source sheets, rows, or columns inside required ranges are fatal.                                                                                           | Hidden required data is not safely auditable.                                                                          |
| Unknown availability symbols | Fatal during preflight. Report all unknown symbols at once.                                                                                                                 | No output may be written if source availability cannot be mapped safely.                                               |
| Equipment Groups             | Parse and write to `Ingest_Equipment_Groups_Reference` with `reference_only = true`; never use them to infer availability.                                                  | They are useful reference data but must not become option availability rows.                                           |
| Failed preflight reporting   | Return a Markdown validation report out-of-band/API response. Do not write workbook output sheets on failed preflight.                                                      | Reconciles “preflight before output” with required validation reporting.                                               |
| Price statuses               | Use granular statuses: `priced`, `priced_zero`, `no_charge`, `included`, `credit`, `tbd`, `missing`, `not_applicable`, `not_found`, `ambiguous`.                            | Distinguishes true zero, no-charge, included, missing, and ambiguous cases.                                            |
| Sheet-name normalization     | Limited auto-binding is allowed only when unique and non-conflicting. Conflicts are fatal.                                                                                  | Data Integrity takes priority over convenience.                                                                        |

---

## 3. Non-Negotiable Data Integrity Rules

| Rule                            | Requirement                                                                                                  |
| ------------------------------- | ------------------------------------------------------------------------------------------------------------ |
| Source immutability             | Never edit, rename, hide, unmerge, clear, or reformat source sheets.                                         |
| Preflight first                 | No generated workbook output may be written until manifest and structure checks pass.                        |
| Manifest required               | A concrete approved preflight manifest artifact is required for full ingest.                                 |
| Data Integrity priority         | If auto-correction creates a conflict, stop and flag for manual review.                                      |
| Raw-plus-normalized             | Preserve raw source values and write normalized fields separately.                                           |
| No destructive cleanup          | Do not globally strip digits, dashes, punctuation, symbols, superscripts, trademarks, or locale suffixes.    |
| No inferred availability        | Availability, standardness, incompatibility, and override rules must come from explicit source matrix cells. |
| No phantom RPOs                 | Never create RPOs by blind truncation or digit stripping.                                                    |
| Equipment Groups reference only | Equipment Groups may validate context but must not broaden availability.                                     |
| Idempotency                     | Reruns must replace generated outputs deterministically and never append duplicates.                         |

---

# 4. Required Preflight Manifest

## 4.1 Manifest Requirement

A full ingest requires an approved external preflight manifest, supplied as JSON or YAML, for example:

```text
preflight_manifest.json
```

or

```text
preflight_manifest.yaml
```

The code may contain a baseline copy of the `WorkbookShape.md` shape for self-validation, but the embedded baseline does **not** replace the required approved manifest in production mode.

If the manifest is missing, malformed, unapproved, incompatible with the skill version, or has a checksum conflict:

| Severity | Error Code                          | Action                                                              |
| -------- | ----------------------------------- | ------------------------------------------------------------------- |
| `FATAL`  | `FATAL_MISSING_OR_INVALID_MANIFEST` | Stop. Return Markdown validation report. Write no workbook outputs. |

## 4.2 Manifest Artifact Schema

The manifest must contain at least:

| Field                      |      Type | Required | Description                                                       |
| -------------------------- | --------: | -------: | ----------------------------------------------------------------- |
| `manifest_id`              |      text |      yes | Stable manifest identifier.                                       |
| `manifest_version`         |      text |      yes | Shape manifest version.                                           |
| `manifest_sha256`          |      text |      yes | SHA-256 checksum of manifest contents.                            |
| `workbook_shape_source`    |      text |      yes | Usually `WorkbookShape.md`.                                       |
| `skill_name`               |      text |      yes | Must equal `ingestSkillv4`.                                       |
| `skill_version_min`        |      text |      yes | Minimum supported skill version.                                  |
| `skill_version_max`        | text/null |       no | Maximum supported skill version, if bounded.                      |
| `approval_state`           |      enum |      yes | Must be `approved` for full ingest.                               |
| `approved_by`              |      text |      yes | Human or system approver.                                         |
| `approved_at_utc`          |  datetime |      yes | Approval timestamp.                                               |
| `expected_workbook_sha256` | text/null |       no | Optional exact workbook checksum. If supplied, mismatch is fatal. |
| `source_file_name_pattern` | text/null |       no | Optional filename validation.                                     |
| `model_year`               |   integer |      yes | `2027`.                                                           |
| `make`                     |      text |      yes | `Chevrolet`.                                                      |
| `vehicle_model`            |      text |      yes | `Corvette`.                                                       |
| `required_source_sheets`   |     array |      yes | Exact source sheet definitions.                                   |
| `generated_sheet_names`    |     array |      yes | Approved generated output sheet names.                            |
| `price_schedule_shape`     |    object |      yes | Price Schedule section/header rules.                              |
| `color_trim_shape`         |    object |      yes | Color & Trim matrix rules.                                        |
| `symbol_map_version`       |      text |      yes | Availability symbol map version.                                  |
| `null_policy_version`      |      text |      yes | Null/status convention version.                                   |

## 4.3 Manifest Sheet Definition Schema

Each `required_source_sheets[]` entry must define:

| Field                  |         Type | Required | Description                                                                                                         |
| ---------------------- | -----------: | -------: | ------------------------------------------------------------------------------------------------------------------- |
| `canonical_name`       |         text |      yes | Exact required sheet name.                                                                                          |
| `allowed_aliases`      |        array |       no | Explicitly approved aliases.                                                                                        |
| `source_group`         |         enum |      yes | `Price Schedule`, `Standard Equipment`, `Equipment Groups`, `Interior`, `Exterior`, `Mechanical`, `Color and Trim`. |
| `suffix`               | integer/null |      yes | `1..4`, `1..2`, or null for Price Schedule.                                                                         |
| `model_family`         |    text/null |      yes | Suffix-derived family or mixed `ZR1/ZR1X`.                                                                          |
| `expected_range`       |     A1 range |      yes | Exact expected used range.                                                                                          |
| `row_1_banner_rule`    |  object/null |      yes | Matrix sheet banner validation rule.                                                                                |
| `row_2_legend_rule`    |  object/null |      yes | Matrix sheet legend validation rule.                                                                                |
| `row_3_header_rule`    |  object/null |      yes | Matrix sheet header validation rule.                                                                                |
| `descriptor_columns`   |  object/null |      yes | Usually `A:C`.                                                                                                      |
| `availability_columns` |  object/null |      yes | Usually `D:I` or `D:K`.                                                                                             |
| `merged_cell_policy`   |       object |      yes | Allowed merged zones and handling.                                                                                  |
| `hidden_policy`        |       object |      yes | Hidden sheet/row/column policy.                                                                                     |

---

# 5. Required Source Workbook Manifest

The workbook must contain exactly these **23 source sheets**, plus only approved generated sheets from prior runs.

Unexpected non-generated source sheets are fatal unless explicitly allowed by the approved preflight manifest.

|   # | Required Sheet Name    | Expected Range | Source Role                              |
| --: | ---------------------- | -------------- | ---------------------------------------- |
|   1 | `Price Schedule`       | `A1:J296`      | Base model and option pricing            |
|   2 | `Standard Equipment 1` | `A1:I82`       | Stingray standard equipment matrix       |
|   3 | `Standard Equipment 2` | `A1:I85`       | Grand Sport standard equipment matrix    |
|   4 | `Standard Equipment 3` | `A1:I85`       | Z06 standard equipment matrix            |
|   5 | `Standard Equipment 4` | `A1:K88`       | ZR1/ZR1X standard equipment matrix       |
|   6 | `Equipment Groups 1`   | `A1:I175`      | Stingray equipment group reference       |
|   7 | `Equipment Groups 2`   | `A1:I174`      | Grand Sport equipment group reference    |
|   8 | `Equipment Groups 3`   | `A1:I177`      | Z06 equipment group reference            |
|   9 | `Equipment Groups 4`   | `A1:K144`      | ZR1/ZR1X equipment group reference       |
|  10 | `Interior 1`           | `A1:I100`      | Stingray interior options                |
|  11 | `Interior 2`           | `A1:I100`      | Grand Sport interior options             |
|  12 | `Interior 3`           | `A1:I104`      | Z06 interior options                     |
|  13 | `Interior 4`           | `A1:K104`      | ZR1/ZR1X interior options                |
|  14 | `Exterior 1`           | `A1:I105`      | Stingray exterior options                |
|  15 | `Exterior 2`           | `A1:I104`      | Grand Sport exterior options             |
|  16 | `Exterior 3`           | `A1:I104`      | Z06 exterior options                     |
|  17 | `Exterior 4`           | `A1:K74`       | ZR1/ZR1X exterior options                |
|  18 | `Mechanical 1`         | `A1:I53`       | Stingray mechanical options              |
|  19 | `Mechanical 2`         | `A1:I51`       | Grand Sport mechanical options           |
|  20 | `Mechanical 3`         | `A1:I49`       | Z06 mechanical options                   |
|  21 | `Mechanical 4`         | `A1:K50`       | ZR1/ZR1X mechanical options              |
|  22 | `Color and Trim 1`     | `A1:Q27`       | Recommended color/trim compatibility     |
|  23 | `Color and Trim 2`     | `A1:H22`       | Custom interior color/trim compatibility |

---

# 6. Sheet Name, Suffix, and Alias Rules

## 6.1 Canonical Sheet Names

Canonical source sheet names are the exact names in the manifest table above.

Matching may apply only these non-destructive normalizations:

1. Trim leading/trailing whitespace.
2. Collapse internal whitespace to one space.
3. Case-insensitive compare.
4. Treat `&` and `and` as equivalent only for `Color and Trim`.
5. Treat hyphen-like joiners as separators only if the result maps uniquely.

## 6.2 Alias and Conflict Policy

| Condition                                            | Severity | Action                                                           |
| ---------------------------------------------------- | -------- | ---------------------------------------------------------------- |
| Exact canonical name exists                          | `OK`     | Use it.                                                          |
| Name differs only by case/spacing and maps uniquely  | `WARN`   | Auto-bind; preserve raw sheet name.                              |
| `Color & Trim 1` maps uniquely to `Color and Trim 1` | `WARN`   | Auto-bind; preserve raw sheet name.                              |
| Missing required sheet                               | `FATAL`  | Stop.                                                            |
| Two sheets normalize to same canonical sheet         | `FATAL`  | Stop.                                                            |
| Required sheet hidden                                | `FATAL`  | Stop.                                                            |
| Hidden row/column in expected required range         | `FATAL`  | Stop.                                                            |
| Unexpected non-generated sheet                       | `FATAL`  | Stop unless manifest explicitly allows.                          |
| Approved prior generated sheet                       | `INFO`   | Ignore during source validation; replace after preflight passes. |
| Alias maps to multiple targets                       | `FATAL`  | Stop; manual review.                                             |
| Auto-correction creates conflict                     | `FATAL`  | Data Integrity wins; stop.                                       |

## 6.3 Suffix Rules

| Sheet Group          |     Valid Suffixes | Meaning           |
| -------------------- | -----------------: | ----------------- |
| `Standard Equipment` | `1`, `2`, `3`, `4` | Matrix source     |
| `Equipment Groups`   | `1`, `2`, `3`, `4` | Reference matrix  |
| `Interior`           | `1`, `2`, `3`, `4` | Matrix source     |
| `Exterior`           | `1`, `2`, `3`, `4` | Matrix source     |
| `Mechanical`         | `1`, `2`, `3`, `4` | Matrix source     |
| `Color and Trim`     |           `1`, `2` | Color/trim matrix |
| `Price Schedule`     |               none | Pricing source    |

## 6.4 Suffix-to-Family Mapping

| Suffix | Model Family                                                  |
| -----: | ------------------------------------------------------------- |
|    `1` | `Stingray`                                                    |
|    `2` | `Grand Sport`                                                 |
|    `3` | `Z06`                                                         |
|    `4` | Mixed `ZR1` and `ZR1X`; must be split by availability headers |

---

# 7. Mandatory Preflight Sequence

No generated workbook output may be written until these steps pass.

| Step | Phase                       | Required Checks                                                                                                          |
| ---: | --------------------------- | ------------------------------------------------------------------------------------------------------------------------ |
|    1 | Manifest validation         | Manifest exists, is approved, checksum-valid, and compatible with `ingestSkillv4`.                                       |
|    2 | Source sheet validation     | Required 23 source sheets exist; no missing, duplicate, hidden, extra, or conflicting sheets.                            |
|    3 | Range validation            | Used ranges match manifest ranges; non-empty cells outside expected ranges are fatal. Formatting-only cells are ignored. |
|    4 | Suffix validation           | Sheet suffixes match allowed group suffixes.                                                                             |
|    5 | Matrix row validation       | Row 1 banner, Row 2 legend, Row 3 headers are present and in exact expected rows.                                        |
|    6 | Banner/family validation    | Row 1 family banner agrees with suffix/family.                                                                           |
|    7 | Header validation           | Descriptor and availability headers match the exact logical expected order.                                              |
|    8 | Symbol inventory            | Collect all unique availability symbols from matrix cells and Color & Trim cells; report all unmapped symbols at once.   |
|    9 | Price Schedule validation   | Locate required price sections, List Price, DFC, and Column D context/notes.                                             |
|   10 | Color & Trim validation     | Resolve merged headers, identify top and lower matrices, validate dash semantics.                                        |
|   11 | Equipment Groups validation | Validate reference matrix shape and merged section bars.                                                                 |
|   12 | Output safety plan          | Identify approved generated sheets and prepare atomic replace plan.                                                      |

If any fatal error occurs during preflight:

- Return a Markdown validation report in the API/tool response.
- Do **not** write, clear, or replace workbook output sheets.
- Do **not** mutate the source workbook.

---

# 8. Matrix Sheet Structural Rules

These rules apply to:

- `Standard Equipment 1–4`
- `Equipment Groups 1–4`
- `Interior 1–4`
- `Exterior 1–4`
- `Mechanical 1–4`

## 8.1 Structural Rows

|    Row | Required Meaning                               | Processing Rule                                   |
| -----: | ---------------------------------------------- | ------------------------------------------------- |
|  Row 1 | Model-family banner                            | Validate only; never extracted as data.           |
|  Row 2 | Availability legend                            | Validate/inventory only; never extracted as data. |
|  Row 3 | Headers                                        | Validate only; never extracted as data.           |
| Row 4+ | Data, section headers, notes, blank separators | Extract or skip according to row-type rules.      |

If Row 3 is shifted to Row 4 or any other row, fail with:

```text
FATAL_BAD_HEADER_ROW
```

## 8.2 Required Column Shape

| Suffix | Expected Used Columns | Descriptor Columns | Availability Columns |
| -----: | --------------------- | ------------------ | -------------------- |
|    `1` | `A:I`                 | `A:C`              | `D:I`                |
|    `2` | `A:I`                 | `A:C`              | `D:I`                |
|    `3` | `A:I`                 | `A:C`              | `D:I`                |
|    `4` | `A:K`                 | `A:C`              | `D:K`                |

Non-empty cells outside the expected used range are fatal unless explicitly allowed by the manifest.

## 8.3 Descriptor Header Rules

Row 3 columns `A:C` must resolve to these logical fields.

| Column | Logical Field     | Accepted Header Meaning                                          |
| ------ | ----------------- | ---------------------------------------------------------------- |
| `A`    | `rpo_raw`         | `RPO`, `Code`, `Option Code`, `Published Code`                   |
| `B`    | `ref_select_raw`  | `Ref`, `Reference`, `Select`, `Ref/Select`, `Selection`          |
| `C`    | `description_raw` | `Description`, `Feature`, `Option`, `Name`, `Option Description` |

If columns `A:C` are blank, shifted, merged incorrectly, or cannot be mapped uniquely, fail with:

```text
FATAL_BAD_HEADER_ROW
```

## 8.4 Exact Availability Header Order

After logical merged-header expansion, each availability column must resolve to the following canonical trim/body tuple.

### Suffix `1` — Stingray

| Column | Required Header   |
| ------ | ----------------- |
| `D`    | `1LT Coupe`       |
| `E`    | `2LT Coupe`       |
| `F`    | `3LT Coupe`       |
| `G`    | `1LT Convertible` |
| `H`    | `2LT Convertible` |
| `I`    | `3LT Convertible` |

### Suffix `2` — Grand Sport

| Column | Required Header   |
| ------ | ----------------- |
| `D`    | `1LT Coupe`       |
| `E`    | `2LT Coupe`       |
| `F`    | `3LT Coupe`       |
| `G`    | `1LT Convertible` |
| `H`    | `2LT Convertible` |
| `I`    | `3LT Convertible` |

### Suffix `3` — Z06

Z06 must use `LZ` trim headers, not `LT`.

| Column | Required Header   |
| ------ | ----------------- |
| `D`    | `1LZ Coupe`       |
| `E`    | `2LZ Coupe`       |
| `F`    | `3LZ Coupe`       |
| `G`    | `1LZ Convertible` |
| `H`    | `2LZ Convertible` |
| `I`    | `3LZ Convertible` |

If a future manifest explicitly approves additional Z06 LZ trims after `3LZ`, process them only if the manifest and row headers agree exactly. Otherwise stop.

### Suffix `4` — ZR1/ZR1X

Suffix `4` sheets must resolve to eight distinct columns.

| Column | Required Header        |
| ------ | ---------------------- |
| `D`    | `ZR1 1LZ Coupe`        |
| `E`    | `ZR1 3LZ Coupe`        |
| `F`    | `ZR1 1LZ Convertible`  |
| `G`    | `ZR1 3LZ Convertible`  |
| `H`    | `ZR1X 1LZ Coupe`       |
| `I`    | `ZR1X 3LZ Coupe`       |
| `J`    | `ZR1X 1LZ Convertible` |
| `K`    | `ZR1X 3LZ Convertible` |

If row labels are split across merged group headers, the logical expanded header must still resolve to this exact tuple per column.

Do not infer ZR1/ZR1X boundaries by position alone.

## 8.5 Row 1 Banner Rules

| Suffix | Required Banner Resolution                                                 | Forbidden Conflicts                                                         |
| -----: | -------------------------------------------------------------------------- | --------------------------------------------------------------------------- |
|    `1` | Must include `Stingray`                                                    | Must not resolve to `Grand Sport`, `Z06`, `ZR1`, or `ZR1X`                  |
|    `2` | Must include `Grand Sport`                                                 | Must not resolve to `Stingray`, `Z06`, `ZR1`, or `ZR1X`                     |
|    `3` | Must include `Z06`                                                         | Must not resolve to `Stingray`, `Grand Sport`, `ZR1`, or `ZR1X`             |
|    `4` | Must indicate mixed `ZR1`/`ZR1X` or headers must explicitly partition both | Must not omit either `ZR1` or `ZR1X` from the resolved availability headers |

Mismatch error:

```text
FATAL_BANNER_MISMATCH
```

## 8.6 Row 2 Legend Rules

Row 2 must contain an availability legend. The parser must inventory all nonblank values in availability cells before extraction.

Known legend symbols:

| Raw Symbol               | Meaning       |
| ------------------------ | ------------- |
| `S`                      | Standard      |
| `A`                      | Available     |
| `D`                      | Available     |
| `*`                      | Available     |
| `□`                      | Standard      |
| `■`                      | Standard      |
| `-`, `--`, `–`, `—`, `−` | Not Available |
| blank                    | Ignore/null   |

If a symbol appears in availability cells but is missing from the row-2 legend, the run may continue only if the symbol is known and mapped. Log:

```text
WARN_SYMBOL_USED_NOT_IN_LEGEND
```

If a nonblank symbol is unknown or cannot be parsed safely, fail preflight with:

```text
FATAL_UNMAPPED_SYMBOL
```

Report all unmapped symbols in a single validation report.

## 8.7 Data Row Validity

A row is a data row if it has at least one of:

- A code-like value in column `A`.
- A nonblank reference/select value in column `B`.
- A nonblank feature/option description in column `C`.
- At least one recognized availability symbol in columns `D+`.

Rows that are only visual section bars, blank separators, disclosure-only rows, or note rows are not emitted as option rows. They are captured as:

- `source_section`
- `source_note`
- footnote disclosure
- skipped-row record

## 8.8 Merged Cells in Matrix Sheets

| Location                | Handling                                                          |
| ----------------------- | ----------------------------------------------------------------- |
| Row 1 banners           | Logical fill across merged banner span for validation only.       |
| Row 2 legends           | Logical fill/read for legend parsing only.                        |
| Row 3 headers           | Logical fill from merged headers; must resolve exactly.           |
| Section bars            | Capture as `source_section`; do not emit as option rows.          |
| Availability data cells | Must not be merged. Merged availability data is fatal.            |
| Descriptor data cells   | Allowed only when manifest-approved; preserve merged range trace. |

---

# 9. Layout Resolution

## 9.1 Canonical Availability Output

The canonical database output is long-form:

```text
Ingest_Option_Availability
```

It emits one row per source row per availability observation:

```text
source option/feature × model_family × trim_code × body_style
```

Blank availability cells emit no observation.

## 9.2 Review Projection Outputs

Review sheets are projections generated from canonical normalized data.

| Review Sheet                  | Required Availability Columns                                                                  |
| ----------------------------- | ---------------------------------------------------------------------------------------------- |
| `Stingray Ingest`             | `1LT Coupe`, `2LT Coupe`, `3LT Coupe`, `1LT Convertible`, `2LT Convertible`, `3LT Convertible` |
| `Grand Sport Ingest`          | `1LT Coupe`, `2LT Coupe`, `3LT Coupe`, `1LT Convertible`, `2LT Convertible`, `3LT Convertible` |
| `Z06 Ingest`                  | `1LZ Coupe`, `2LZ Coupe`, `3LZ Coupe`, `1LZ Convertible`, `2LZ Convertible`, `3LZ Convertible` |
| `ZR1 1LZ Coupe Ingest`        | Single variant projection                                                                      |
| `ZR1 3LZ Coupe Ingest`        | Single variant projection                                                                      |
| `ZR1 1LZ Convertible Ingest`  | Single variant projection                                                                      |
| `ZR1 3LZ Convertible Ingest`  | Single variant projection                                                                      |
| `ZR1X 1LZ Coupe Ingest`       | Single variant projection                                                                      |
| `ZR1X 3LZ Coupe Ingest`       | Single variant projection                                                                      |
| `ZR1X 1LZ Convertible Ingest` | Single variant projection                                                                      |
| `ZR1X 3LZ Convertible Ingest` | Single variant projection                                                                      |

ZR1 and ZR1X must never be collapsed into a shared six-column LT layout.

---

# 10. ZR1/ZR1X Boundary Algorithm

Suffix `4` sheets contain eight availability columns and must be split deterministically.

## 10.1 Header Expansion

1. Build a logical grid from the source sheet.
2. For each merged range in rows `1:3`, copy the top-left displayed value across the merged range in the logical grid.
3. Preserve physical source coordinates and merged ranges in trace fields.
4. Ignore row 2 for variant header extraction except as a legend row.

## 10.2 Per-Column Token Resolution

For each column `D:K`, extract exactly one:

| Token Type     | Allowed Values         |
| -------------- | ---------------------- |
| `model_family` | `ZR1`, `ZR1X`          |
| `trim_code`    | `1LZ`, `3LZ`           |
| `body_style`   | `Coupe`, `Convertible` |

Tokenization rules:

- Match `ZR1X` before `ZR1` so `ZR1` is not falsely extracted from `ZR1X`.
- Accept body synonyms only if manifest-approved, e.g. `Conv` → `Convertible`, `Cpe` → `Coupe`.
- Accept split headers only when the merged group span unambiguously assigns family to each column.

## 10.3 Required Tuple Set

The resolved suffix-4 columns must equal this set exactly:

```text
ZR1|1LZ|Coupe
ZR1|3LZ|Coupe
ZR1|1LZ|Convertible
ZR1|3LZ|Convertible
ZR1X|1LZ|Coupe
ZR1X|3LZ|Coupe
ZR1X|1LZ|Convertible
ZR1X|3LZ|Convertible
```

## 10.4 Fatal Boundary Conditions

Fail with `FATAL_ZR1_ZR1X_AMBIGUOUS_COLUMNS` if:

- A column lacks family, trim, or body.
- A column resolves to multiple families.
- `ZR1`/`ZR1X` boundary is based only on position.
- Duplicate resolved tuples exist.
- Any required tuple is missing.
- Merged headers are blank or inconsistent.
- Row 1, Row 3, and suffix imply conflicting families.

---

# 11. Availability Symbol Mapping

## 11.1 Standard Variant Matrices

Applies to:

- `Standard Equipment`
- `Equipment Groups`
- `Interior`
- `Exterior`
- `Mechanical`

| Raw Cell Value | Normalized Availability | Output Behavior                        |
| -------------- | ----------------------- | -------------------------------------- |
| `S`            | `standard`              | Emit observation.                      |
| `□`            | `standard`              | Emit observation; preserve raw symbol. |
| `■`            | `standard`              | Emit observation; preserve raw symbol. |
| `A`            | `available`             | Emit observation.                      |
| `D`            | `available`             | Emit observation.                      |
| `*`            | `available`             | Emit observation.                      |
| `A/D`          | `available`             | Emit observation; preserve raw nuance. |
| `-`            | `not_available`         | Emit observation.                      |
| `--`           | `not_available`         | Emit observation.                      |
| `–`            | `not_available`         | Emit observation.                      |
| `—`            | `not_available`         | Emit observation.                      |
| `−`            | `not_available`         | Emit observation.                      |
| blank          | null / ignore           | Emit no availability observation.      |

Dash mapping applies only when the entire availability cell is a dash variant. Dashes inside descriptions, names, notes, or RPOs are not availability symbols.

## 11.2 Footnoted Symbols

A mapped base symbol may carry footnotes.

| Raw Cell | Base Symbol | Marker | Availability    |
| -------- | ----------- | ------ | --------------- |
| `S1`     | `S`         | `1`    | `standard`      |
| `A1,2`   | `A`         | `1,2`  | `available`     |
| `D¹`     | `D`         | `1`    | `available`     |
| `*2`     | `*`         | `2`    | `available`     |
| `□1`     | `□`         | `1`    | `standard`      |
| `■1`     | `■`         | `1`    | `standard`      |
| `--1`    | `--`        | `1`    | `not_available` |
| `A/D1`   | `A/D`       | `1`    | `available`     |

Parse order:

1. Preserve `availability_raw`.
2. Confirm base symbol is valid.
3. Extract trailing marker only after base-symbol validation.
4. Resolve marker against the sheet disclosure inventory.
5. Write marker to `footnote_markers`.
6. If disclosure body is missing, log `WARN_UNRESOLVED_FOOTNOTE`.

## 11.3 Unknown or Multi-Symbol Cells

Cells such as:

```text
A or D
S*
A - see note
P
```

are not guessed. Because this is preflight-inventoried matrix content, unknown nonblank cells are fatal:

```text
FATAL_UNMAPPED_SYMBOL
```

All unknown symbols must be reported together.

---

# 12. Color & Trim Handling

Color & Trim sheets use different dash semantics than standard variant matrices.

Source sheets:

| Sheet              | Expected Range | Role                                     |
| ------------------ | -------------- | ---------------------------------------- |
| `Color and Trim 1` | `A1:Q27`       | Recommended color/trim compatibility     |
| `Color and Trim 2` | `A1:H22`       | Custom interior color/trim compatibility |

## 12.1 Logical Merged-Cell Grid

Before parsing:

1. Build a logical grid.
2. Fill merged column headers rightward.
3. Fill merged row labels downward.
4. Preserve physical coordinates and merged ranges.
5. Do not modify the source sheet.

If merged-cell metadata is unavailable, conservative fill is allowed only in manifest-defined header zones. If more than one interpretation is possible, fail:

```text
FATAL_COLOR_TRIM_BOUNDARY
```

## 12.2 Matrix Boundary Detection

Each Color & Trim sheet must resolve into:

| Matrix       | Role                                                     |
| ------------ | -------------------------------------------------------- |
| Top Matrix   | Interior color RPOs by trim/seat/decor level             |
| Lower Matrix | Paint color X-axis × interior color Y-axis compatibility |

Boundary detection algorithm:

1. Scan for a blank separator row.
2. After the separator, locate a header row whose columns resolve to exterior paint names or paint RPOs.
3. Cross-check paint headers against the Price Schedule Paint section and/or Exterior source rows.
4. Confirm the lower matrix has paint on the X-axis and interior color on the Y-axis.
5. Confirm the top matrix has trim/seat/decor headers and interior color/code values.

If the boundary cannot be resolved exactly, fail:

```text
FATAL_COLOR_TRIM_BOUNDARY
```

## 12.3 Top Matrix Semantics

The top matrix identifies interior color RPOs for each color and trim level.

| Cell Value               | Meaning                         | Output                       |
| ------------------------ | ------------------------------- | ---------------------------- |
| Interior RPO/code/name   | Interior color/trim observation | Emit to `Ingest_Color_Trim`. |
| `-`, `--`, `–`, `—`, `−` | True blank/null                 | Emit no row.                 |
| blank                    | True blank/null                 | Emit no row.                 |

Top-matrix dashes are **not** `not_available` and are **not** D30 override rows.

## 12.4 Lower Matrix Semantics

The lower matrix uses:

```text
Paint color X-axis × Interior color Y-axis
```

| Cell Value                 | Meaning                                          | Output                                                 |
| -------------------------- | ------------------------------------------------ | ------------------------------------------------------ |
| Dash variant               | Requires option `D30` color combination override | Emit to `Ingest_Color_Combinations`.                   |
| Footnoted dash             | Requires `D30`, with footnote marker             | Emit override row plus footnote marker.                |
| blank                      | Compatible/no explicit override                  | Emit no row.                                           |
| Other explicit text/symbol | Preserve raw and flag unless manifest-mapped     | `MANUAL_REVIEW` or fatal if unmapped preflight symbol. |

Required output fields for dash cells:

| Field           | Value                                            |
| --------------- | ------------------------------------------------ |
| `compatibility` | `requires_d30_override`                          |
| `required_rpo`  | `D30`                                            |
| `override_note` | `requires option D30 color combination override` |

---

# 13. Data Preservation and Context-Aware Normalization

## 13.1 Raw vs Displayed Value Policy

| Cell Type              | Use for Raw Field                                   | Use for Normalized Field             |
| ---------------------- | --------------------------------------------------- | ------------------------------------ |
| RPO/code cells         | Raw text value, preserving leading zeros if present | Uppercase/trim only after parsing.   |
| Availability cells     | Displayed/calculated value                          | Symbol parser result.                |
| Price cells            | Displayed/calculated value                          | Decimal/status parser result.        |
| Formula cells          | Calculated displayed value                          | Capture formula in `source_formula`. |
| Description/name cells | Displayed text                                      | Context-aware text normalization.    |
| Merged cells           | Physical top-left and logical filled value          | Preserve `source_merged_range`.      |

## 13.2 Global Non-Destructive Text Normalization

Raw values are never overwritten.

Allowed only in normalized/search fields:

| Pattern                              | Normalized Handling                                                 |
| ------------------------------------ | ------------------------------------------------------------------- |
| Leading/trailing whitespace          | Trim.                                                               |
| Repeated spaces                      | Collapse for comparison fields.                                     |
| NBSP/thin spaces                     | Convert to regular space.                                           |
| Zero-width spaces                    | Remove from normalized field.                                       |
| Soft hyphen                          | Remove from normalized/search field.                                |
| CR/LF/CRLF                           | Normalize to `\n`.                                                  |
| Superscript digits                   | Convert to normal digits only for footnote markers.                 |
| Smart quotes                         | ASCII-fold only for matching fields.                                |
| Trademark/registered/degree/bullet/× | Preserve in display fields; optional removal only in `_searchable`. |
| En/em dashes                         | Preserve; only symbol parser treats whole-cell dash as a symbol.    |

## 13.3 Context Zones

| Zone               | Allowed Normalization                               | Forbidden                             |
| ------------------ | --------------------------------------------------- | ------------------------------------- |
| RPO cells          | Uppercase, trim, parse footnote only when validated | Blind truncation or digit stripping   |
| Availability cells | Symbol mapping and footnote extraction              | Treating explanatory text as a symbol |
| Descriptions/names | Whitespace normalization, footnote extraction       | Global hyphen/digit removal           |
| Prices             | Currency/status parsing                             | Dropping raw status tokens            |
| Color & Trim       | Matrix-context dash rules                           | Reusing standard matrix dash rules    |

---

# 14. Footnote and Disclosure Extraction

## 14.1 Disclosure Inventory

Before row extraction, build a disclosure inventory per sheet from:

- Bottom note rows.
- In-cell disclosures after line breaks.
- Color & Trim notes.
- Numbered, lettered, or symbolic disclosure markers.

Accepted disclosure starts include:

```text
1.
1)
1 -
1–
1—
(1)
¹
*
†
```

Line endings must be normalized to `\n` before parsing.

## 14.2 Marker Extraction Rules

A trailing digit or symbol is a footnote marker only if:

- The same sheet’s disclosure inventory contains that marker, or
- The token exceeds expected base shape and the stripped base validates against known workbook RPOs/names, or
- The context is an availability symbol with a valid mapped base symbol.

## 14.3 Protected Tokens

Never strip digits from these merely because they end with a digit:

```text
Z06
ZR1
ZR1X
1LT
2LT
3LT
1LZ
2LZ
3LZ
GT1
GT2
Z51
```

## 14.4 Locale Suffix After Footnote Marker

Special case:

```text
Sky Cool Gray1 en-us
```

Parsing result:

| Field                    | Value                        |
| ------------------------ | ---------------------------- |
| `raw_marked_value`       | `Sky Cool Gray1 en-us`       |
| `name_raw`               | `Sky Cool Gray1 en-us`       |
| `name_normalized`        | `Sky Cool Gray`              |
| `footnote_marker`        | `1`                          |
| `locale_suffix_stripped` | `en-us`                      |
| `validation_flag`        | `locale_suffix_after_marker` |

Locale suffix pattern:

```text
^[a-z]{2}-[a-z]{2}$
```

case-insensitive, after a valid footnote marker.

## 14.5 RPO Footnote Repair

Never destructively truncate RPOs.

Example handling:

| Raw RPO | Possible Parse              | Required Behavior                                                                                            |
| ------- | --------------------------- | ------------------------------------------------------------------------------------------------------------ |
| `HU7²`  | `HU7` + marker `2`          | Valid if marker exists and `HU7` is known.                                                                   |
| `HU76`  | possible `HU7` + marker `6` | Only normalize to `HU7` if `HU7` is a known workbook RPO and marker `6` exists. Otherwise preserve and flag. |
| `EL98`  | possible `EL9` + marker `8` | Same rule; never assume.                                                                                     |
| `Z06`   | protected token             | Do not strip.                                                                                                |
| `Z51`   | protected token             | Do not strip.                                                                                                |

Output fields:

| Field                  | Description                |
| ---------------------- | -------------------------- |
| `rpo_raw`              | Exact source value.        |
| `rpo_normalized`       | Parsed RPO only when safe. |
| `rpo_status`           | Parse status.              |
| `rpo_validation_flags` | Pipe-delimited flags.      |
| `footnote_markers`     | Extracted markers, if any. |

## 14.6 Multi-Marker Handling

For values like:

```text
A1,2
12
```

Rules:

- `1,2` means markers `1` and `2` only if both exist in the disclosure inventory.
- `12` is marker `12` unless markers `1` and `2` both exist and the workbook convention supports multi-marker splitting.
- Ambiguous multi-marker parsing is `MANUAL_REVIEW`.

---

# 15. RPO Treatment

## 15.1 RPO Pattern

Default standard RPO pattern:

```text
^[A-Z0-9]{3}$
```

Values outside this pattern are not rejected. They are preserved and flagged.

## 15.2 RPO Status Values

| Status                       | Meaning                                                |
| ---------------------------- | ------------------------------------------------------ |
| `valid_standard`             | Confident three-character uppercase alphanumeric code. |
| `missing_allowed`            | Blank RPO is acceptable for the row/source type.       |
| `composite`                  | Multiple RPO-like tokens appear.                       |
| `nonstandard_length`         | Code-like token is not three characters.               |
| `contains_resolved_footnote` | Marker separated and resolved.                         |
| `contains_unresolved_marker` | Possible marker cannot be resolved.                    |
| `invalid_chars`              | Unexpected characters for code field.                  |
| `manual_review`              | Cannot normalize safely.                               |

## 15.3 Composite RPOs

If a cell contains multiple clean RPOs separated by slash or comma, emit one row per RPO only if the same row clearly applies to each code.

Shared fields:

- Same source trace.
- Same availability observation.
- Same `rpo_group_id`.
- `split_from_composite = true`.

If the cell contains prose such as:

```text
requires
includes
with
without
parenthetical references
```

do not split into orderable RPOs unless the workbook explicitly presents the tokens as orderable codes.

---

# 16. Price Schedule Parsing

## 16.1 Required Price Schedule Structure

`Price Schedule` is structurally distinct from matrix sheets.

| Area                     | Required Rule                                                                                 |
| ------------------------ | --------------------------------------------------------------------------------------------- |
| Used range               | Must match `A1:J296`.                                                                         |
| Top rows                 | Must identify 2027 Corvette price schedule context.                                           |
| Base model price section | Must contain base model rows and headers at manifest-defined location, default row `5`.       |
| Option pricing section   | Must contain option pricing headers at manifest-defined location, default near row `39`.      |
| Column D                 | Must be captured as price note/context for duplicate RPO resolution.                          |
| List Price               | Must be located by exact manifest header.                                                     |
| DFC                      | Must be located by exact manifest header.                                                     |
| Non-data rows            | Section headers, disclaimers, tax rows, and note rows must not be emitted as ordinary prices. |

If required sections or price columns cannot be located uniquely:

```text
FATAL_PRICE_STRUCTURE
```

## 16.2 Base Variant Price

For base model rows:

```text
Total Variant Price = List Price + DFC
```

Output:

```text
Ingest_Variant_Prices
```

Required fields:

| Field                                       | Description                        |
| ------------------------------------------- | ---------------------------------- |
| `list_price_amount`                         | Parsed List Price.                 |
| `dfc_amount`                                | Parsed destination freight charge. |
| `total_variant_price_amount`                | `list_price_amount + dfc_amount`.  |
| `price_currency`                            | `USD`.                             |
| `price_status`                              | Parse status.                      |
| `source_sheet`, `source_row`, `source_cell` | Source trace.                      |

If either List Price or DFC cannot be parsed, leave total null and flag.

## 16.3 Option Price

For option rows:

```text
Option Price = List Price
```

DFC is never added to option prices.

Output:

```text
Ingest_Option_Prices
```

## 16.4 Price Value Normalization

| Raw Price                | `price_amount` | `price_status`   |
| ------------------------ | -------------: | ---------------- |
| `$1,295`                 |      `1295.00` | `priced`         |
| `1295`                   |      `1295.00` | `priced`         |
| `$1,295.00`              |      `1295.00` | `priced`         |
| `$0`                     |         `0.00` | `priced_zero`    |
| `N/C`, `NC`, `No Charge` |         `0.00` | `no_charge`      |
| `Included`, `INC`, `STD` |         `0.00` | `included`       |
| `TBD`                    |           null | `tbd`            |
| blank                    |           null | `missing`        |
| `-`, `--`, `–`, `—`, `−` |           null | `not_applicable` |
| `($500)`                 |      `-500.00` | `credit`         |
| `$500 credit`            |      `-500.00` | `credit`         |
| ambiguous duplicate      |           null | `ambiguous`      |
| no candidate             |           null | `not_found`      |

Preserve the raw value in `price_raw`.

## 16.5 Duplicate RPO Price Resolution

Do not match prices by RPO alone when duplicates exist.

Resolution order:

| Step | Rule                                                                                                                      |
| ---: | ------------------------------------------------------------------------------------------------------------------------- |
|    1 | Match candidate price rows by `rpo_normalized`.                                                                           |
|    2 | If zero candidates, leave price blank, set `price_status = not_found`, log warning.                                       |
|    3 | If one candidate, use it.                                                                                                 |
|    4 | If multiple candidates, parse Column D note/context for each candidate.                                                   |
|    5 | Compare parsed predicates to target context: model family, trim, body style, section, option name, detail, and footnotes. |
|    6 | If exactly one candidate matches, use it and set `price_match_status = resolved_by_column_d_note`.                        |
|    7 | If still ambiguous, leave price blank, set `price_status = ambiguous`, write all candidates, and flag `MANUAL_REVIEW`.    |

Never choose the first duplicate, average prices, or silently blank a price.

## 16.6 Column D Note Predicate Grammar

Column D notes must be parsed deterministically.

### Token Classes

| Class              | Examples                                                           |
| ------------------ | ------------------------------------------------------------------ |
| Family             | `Stingray`, `Grand Sport`, `Z06`, `ZR1`, `ZR1X`                    |
| Trim               | `1LT`, `2LT`, `3LT`, `1LZ`, `2LZ`, `3LZ`                           |
| Body               | `Coupe`, `Convertible`, `Conv`, `Cpe`                              |
| Section            | `Interior`, `Exterior`, `Mechanical`, `Paint`, `Wheels`, `Seats`   |
| RPO/package        | Three-character RPO-like tokens                                    |
| Inclusion operator | `for`, `on`, `with`, `w/`, `only`, `requires`, `included with`     |
| Exclusion operator | `except`, `excluding`, `without`, `not with`, `not available with` |

### Predicate Object

Each Column D note parses to:

| Field                 | Type                                  |
| --------------------- | ------------------------------------- |
| `include_families`    | set                                   |
| `exclude_families`    | set                                   |
| `include_trims`       | set                                   |
| `exclude_trims`       | set                                   |
| `include_body_styles` | set                                   |
| `exclude_body_styles` | set                                   |
| `include_sections`    | set                                   |
| `exclude_sections`    | set                                   |
| `include_rpos`        | set                                   |
| `exclude_rpos`        | set                                   |
| `unknown_text`        | text                                  |
| `parse_confidence`    | enum: `none`, `low`, `medium`, `high` |

### Match Rules

A candidate matches if:

1. Target context satisfies all inclusion predicates.
2. Target context violates none of the exclusion predicates.
3. Unknown free text does not decide the match.
4. If multiple candidates match, choose the one with the highest specificity only if unique.

Specificity order:

```text
family + trim + body
family + trim
family + body
family
section
generic/no selector
```

If two candidates tie at the highest specificity, the price is ambiguous.

---

# 17. Equipment Groups Handling

Equipment Groups are required source sheets and must be parsed as reference data.

## 17.1 Required Handling

| Requirement                | Handling                                                             |
| -------------------------- | -------------------------------------------------------------------- |
| Validate existence         | Required sheets `Equipment Groups 1–4`.                              |
| Validate structure         | Same row/column matrix rules as other matrix sheets.                 |
| Handle merged section bars | Logical fill and capture as `source_section`.                        |
| Preserve reference rows    | Write to `Ingest_Equipment_Groups_Reference`.                        |
| Mark as reference          | `reference_only = true`.                                             |
| Use as validation context  | May validate known RPOs, names, groups, and price context.           |
| No inferred availability   | Must not create or broaden availability observations.                |
| No package logic           | Must not infer package membership beyond explicit reference content. |

## 17.2 Equipment Group Output Rule

Equipment Group rows are not written to `Ingest_Option_Availability` unless the workbook explicitly presents them as availability observations in a non-reference source sheet.

---

# 18. Continuation Rows, Notes, and Skipped Rows

## 18.1 Continuation Rows

A row with:

- blank RPO,
- blank or continuation reference,
- nonblank description,

may be appended to the previous logical row’s description only if the manifest/source pattern indicates continuation.

Preserve:

| Field                      | Description                               |
| -------------------------- | ----------------------------------------- |
| `description_raw`          | Original previous plus continuation text. |
| `description_normalized`   | Normalized combined text.                 |
| `continuation_source_rows` | List of appended row numbers.             |

## 18.2 Sheet Notes

Note/disclaimer rows are captured to:

```text
Ingest_Sheet_Notes
```

## 18.3 Skipped Rows

Rows skipped as section headers, blank separators, notes, or malformed nonfatal rows are written to:

```text
Ingest_Skipped_Rows
```

---

# 19. Generated Outputs

## 19.1 Canonical Generated Sheets

| Sheet Name                          | Purpose                                                               |
| ----------------------------------- | --------------------------------------------------------------------- |
| `Ingest_Run_Metadata`               | Run-level metadata and workbook identifiers.                          |
| `Ingest_Source_Manifest_Audit`      | Approved manifest snapshot and checksum facts.                        |
| `Ingest_Validation_Summary`         | Aggregate validation counts.                                          |
| `Ingest_Validation_Report`          | Structured validation records.                                        |
| `Ingest_Option_Availability`        | Canonical normalized availability observations.                       |
| `Ingest_Variant_Prices`             | Base variant List Price, DFC, and total price.                        |
| `Ingest_Option_Prices`              | Parsed option List Price records.                                     |
| `Ingest_Color_Trim`                 | Interior color/trim observations from top Color & Trim matrices.      |
| `Ingest_Color_Combinations`         | D30 color-combination override rows from lower Color & Trim matrices. |
| `Ingest_Equipment_Groups_Reference` | Reference-only Equipment Groups rows.                                 |
| `Ingest_Footnotes`                  | Footnote markers, text, scope, and resolution status.                 |
| `Ingest_Sheet_Notes`                | Captured sheet-level notes and disclaimers.                           |
| `Ingest_Skipped_Rows`               | Skipped rows with reasons.                                            |

## 19.2 Required Review Projection Sheets

| Sheet Name                    | Purpose                                            |
| ----------------------------- | -------------------------------------------------- |
| `Stingray Ingest`             | Matrix-style Stingray review projection.           |
| `Grand Sport Ingest`          | Matrix-style Grand Sport review projection.        |
| `Z06 Ingest`                  | Matrix-style Z06 review projection using LZ trims. |
| `ZR1 1LZ Coupe Ingest`        | Variant-specific ZR1 review projection.            |
| `ZR1 3LZ Coupe Ingest`        | Variant-specific ZR1 review projection.            |
| `ZR1 1LZ Convertible Ingest`  | Variant-specific ZR1 review projection.            |
| `ZR1 3LZ Convertible Ingest`  | Variant-specific ZR1 review projection.            |
| `ZR1X 1LZ Coupe Ingest`       | Variant-specific ZR1X review projection.           |
| `ZR1X 3LZ Coupe Ingest`       | Variant-specific ZR1X review projection.           |
| `ZR1X 1LZ Convertible Ingest` | Variant-specific ZR1X review projection.           |
| `ZR1X 3LZ Convertible Ingest` | Variant-specific ZR1X review projection.           |

---

# 20. Canonical Schema — `Ingest_Option_Availability`

One row per source row per availability observation.

| Column                     | Type         | Required | Description                                                 |
| -------------------------- | ------------ | -------: | ----------------------------------------------------------- |
| `record_key`               | text         |      yes | Stable deterministic key.                                   |
| `run_id`                   | text         |      yes | Current run ID.                                             |
| `model_year`               | integer      |      yes | `2027`.                                                     |
| `make`                     | text         |      yes | `Chevrolet`.                                                |
| `vehicle_model`            | text         |      yes | `Corvette`.                                                 |
| `model_family`             | enum         |      yes | `Stingray`, `Grand Sport`, `Z06`, `ZR1`, `ZR1X`.            |
| `trim_code`                | text         |      yes | `1LT`, `2LT`, `3LT`, `1LZ`, `2LZ`, `3LZ`.                   |
| `body_style`               | enum         |      yes | `Coupe`, `Convertible`.                                     |
| `source_group`             | enum         |      yes | `Interior`, `Exterior`, `Mechanical`, `Standard Equipment`. |
| `row_type`                 | enum         |      yes | `option`, `standard_equipment`, `feature`.                  |
| `source_file`              | text         |      yes | Source workbook filename.                                   |
| `source_sheet`             | text         |      yes | Canonical source sheet.                                     |
| `source_sheet_raw`         | text         |      yes | Actual workbook sheet name.                                 |
| `source_row`               | integer      |      yes | 1-based source row.                                         |
| `source_column`            | text         |      yes | Availability source column.                                 |
| `source_cell`              | text         |      yes | A1 source cell.                                             |
| `source_formula`           | text/null    |       no | Formula string if applicable.                               |
| `source_merged_range`      | text/null    |       no | Merged range if applicable.                                 |
| `source_section`           | text/null    |       no | Current section/category.                                   |
| `rpo_raw`                  | text/null    |       no | Exact RPO/code source value.                                |
| `rpo_normalized`           | text/null    |       no | Parsed normalized RPO.                                      |
| `rpo_status`               | enum         |      yes | RPO parse status.                                           |
| `rpo_validation_flags`     | text/null    |       no | Pipe-delimited flags.                                       |
| `rpo_group_id`             | text/null    |       no | Shared ID for split composite RPOs.                         |
| `ref_select_raw`           | text/null    |       no | Raw reference/select value.                                 |
| `option_name_raw`          | text/null    |       no | Raw option/name value.                                      |
| `option_name_normalized`   | text/null    |       no | Normalized option/name.                                     |
| `description_raw`          | text/null    |       no | Raw description.                                            |
| `description_normalized`   | text/null    |       no | Normalized description.                                     |
| `detail_raw`               | text/null    |       no | Detail or note text.                                        |
| `availability_raw`         | text/null    |      yes | Raw availability cell.                                      |
| `availability_normalized`  | enum/null    |       no | `standard`, `available`, `not_available`, or null.          |
| `availability_symbol_base` | text/null    |       no | Parsed base symbol.                                         |
| `footnote_markers`         | text/null    |       no | Marker list.                                                |
| `footnote_keys`            | text/null    |       no | Linked footnote records.                                    |
| `price_amount`             | decimal/null |       no | Matched option List Price.                                  |
| `price_currency`           | text/null    |       no | `USD`.                                                      |
| `price_type`               | enum/null    |       no | Usually `option_list`.                                      |
| `price_status`             | enum/null    |       no | Price status.                                               |
| `price_match_status`       | enum         |      yes | `matched`, `not_found`, `ambiguous`, etc.                   |
| `price_source_key`         | text/null    |       no | Linked option price record.                                 |
| `price_candidates`         | json/null    |       no | Candidate rows when ambiguous.                              |
| `validation_flags`         | text/null    |       no | Pipe-delimited nonfatal flags.                              |

---

# 21. Stable Key Rules

`record_key` must be deterministic and exclude `run_id` and timestamps.

Use:

```text
sha256(
  model_year
  | make
  | vehicle_model
  | model_family
  | trim_code
  | body_style
  | source_group
  | source_sheet
  | source_row
  | source_column
  | rpo_normalized_or_raw
  | normalized_description_hash
  | row_type
)
```

Rows without RPOs use source coordinates and normalized description hash.

---

# 22. Other Output Schemas

## 22.1 `Ingest_Color_Trim`

| Column                     | Type      |
| -------------------------- | --------- |
| `record_key`               | text      |
| `run_id`                   | text      |
| `source_sheet`             | text      |
| `source_sheet_raw`         | text      |
| `source_row`               | integer   |
| `source_column`            | text      |
| `source_cell`              | text      |
| `model_family`             | text      |
| `trim_code`                | text/null |
| `seat`                     | text/null |
| `decor_level`              | text/null |
| `interior_code_raw`        | text/null |
| `interior_code_normalized` | text/null |
| `interior_name_raw`        | text/null |
| `interior_name_normalized` | text/null |
| `material`                 | text/null |
| `footnote_markers`         | text/null |
| `footnote_keys`            | text/null |
| `validation_flags`         | text/null |

## 22.2 `Ingest_Color_Combinations`

| Column             | Type                          |
| ------------------ | ----------------------------- |
| `record_key`       | text                          |
| `run_id`           | text                          |
| `source_sheet`     | text                          |
| `source_row`       | integer                       |
| `source_column`    | text                          |
| `source_cell`      | text                          |
| `model_family`     | text/null                     |
| `exterior_rpo`     | text                          |
| `exterior_name`    | text                          |
| `interior_rpo`     | text                          |
| `interior_name`    | text                          |
| `compatibility`    | enum: `requires_d30_override` |
| `required_rpo`     | text: `D30`                   |
| `override_note`    | text                          |
| `raw_cell_value`   | text                          |
| `footnote_markers` | text/null                     |
| `severity`         | enum                          |

## 22.3 `Ingest_Variant_Prices`

| Column                       | Type         |
| ---------------------------- | ------------ |
| `record_key`                 | text         |
| `run_id`                     | text         |
| `model_year`                 | integer      |
| `make`                       | text         |
| `vehicle_model`              | text         |
| `model_family`               | text         |
| `trim_code`                  | text         |
| `body_style`                 | text         |
| `variant_name`               | text         |
| `list_price_amount`          | decimal/null |
| `dfc_amount`                 | decimal/null |
| `total_variant_price_amount` | decimal/null |
| `price_currency`             | text         |
| `price_status`               | enum         |
| `price_raw`                  | text         |
| `source_sheet`               | text         |
| `source_row`                 | integer      |
| `source_cell`                | text         |

## 22.4 `Ingest_Option_Prices`

| Column                    | Type                |
| ------------------------- | ------------------- |
| `price_record_key`        | text                |
| `run_id`                  | text                |
| `rpo_raw`                 | text/null           |
| `rpo_normalized`          | text/null           |
| `option_name_raw`         | text/null           |
| `option_name_normalized`  | text/null           |
| `price_amount`            | decimal/null        |
| `price_currency`          | text                |
| `price_status`            | enum                |
| `price_type`              | enum: `option_list` |
| `price_raw`               | text                |
| `column_d_note_raw`       | text/null           |
| `column_d_predicate_json` | json/null           |
| `source_sheet`            | text                |
| `source_row`              | integer             |
| `source_cell`             | text                |

## 22.5 `Ingest_Equipment_Groups_Reference`

| Column                    | Type      |
| ------------------------- | --------- |
| `record_key`              | text      |
| `run_id`                  | text      |
| `source_sheet`            | text      |
| `source_row`              | integer   |
| `source_column`           | text      |
| `source_cell`             | text      |
| `model_family`            | text      |
| `source_section`          | text/null |
| `group_name`              | text/null |
| `rpo_raw`                 | text/null |
| `rpo_normalized`          | text/null |
| `description_raw`         | text/null |
| `description_normalized`  | text/null |
| `availability_raw`        | text/null |
| `availability_normalized` | text/null |
| `reference_only`          | boolean   |
| `validation_flags`        | text/null |

## 22.6 `Ingest_Footnotes`

| Column              | Type                                             |
| ------------------- | ------------------------------------------------ |
| `footnote_key`      | text                                             |
| `run_id`            | text                                             |
| `source_sheet`      | text                                             |
| `source_row`        | integer/null                                     |
| `source_column`     | text/null                                        |
| `source_cell`       | text/null                                        |
| `footnote_marker`   | text                                             |
| `footnote_text`     | text/null                                        |
| `footnote_scope`    | enum: `cell`, `row`, `sheet`, `color_trim_sheet` |
| `raw_marked_value`  | text/null                                        |
| `resolution_status` | enum: `resolved`, `unresolved`, `ambiguous`      |

---

# 23. Null and Enum Conventions

| Concept                        | Representation                                        |
| ------------------------------ | ----------------------------------------------------- |
| True null                      | Empty generated cell, with status field where needed. |
| Blank source availability cell | No emitted observation.                               |
| Standard matrix dash           | `availability_normalized = not_available`.            |
| Top Color & Trim dash          | Null/no row.                                          |
| Lower Color & Trim dash        | D30 override row.                                     |
| Unknown price                  | `price_amount = null`, status explains reason.        |
| No charge                      | `price_amount = 0.00`, `price_status = no_charge`.    |
| Included                       | `price_amount = 0.00`, `price_status = included`.     |
| True zero                      | `price_amount = 0.00`, `price_status = priced_zero`.  |
| Ambiguous price                | `price_amount = null`, `price_status = ambiguous`.    |
| Not available                  | Enum value, never null.                               |
| Not applicable                 | Status value, not the same as blank.                  |

Do not write the literal string `NULL` unless a downstream database loader explicitly requires it.

---

# 24. Validation Report

## 24.1 Persistence Rule

If preflight fails:

- Return the validation report as Markdown in the API/tool response.
- Do not write workbook output sheets.

If preflight succeeds:

- Write `Ingest_Validation_Report`.
- Write `Ingest_Validation_Summary`.
- Continue with generated outputs.

If a fatal error occurs after generation begins:

- Roll back temporary generated sheets when possible.
- Write failure metadata only if the output phase has already started and the platform supports safe write.
- Never mutate source sheets.

## 24.2 Validation Report Schema

| Column               | Type           | Description                              |
| -------------------- | -------------- | ---------------------------------------- |
| `severity`           | enum           | `FATAL`, `MANUAL_REVIEW`, `WARN`, `INFO` |
| `error_code`         | text           | Stable validation code.                  |
| `message`            | text           | Human-readable issue.                    |
| `source_sheet`       | text/null      | Source sheet if applicable.              |
| `source_row`         | integer/null   | Source row.                              |
| `source_column`      | text/null      | Source column.                           |
| `source_cell`        | text/null      | A1 reference.                            |
| `raw_value`          | text/null      | Raw problematic value.                   |
| `normalized_value`   | text/null      | Normalized value, if any.                |
| `candidate_values`   | text/json/null | Candidate sheets, symbols, or prices.    |
| `recommended_action` | text           | Manual correction guidance.              |
| `run_id`             | text/null      | Run ID if created.                       |

## 24.3 Required Validation Codes

| Code                                | Severity        | Meaning                                                        |
| ----------------------------------- | --------------- | -------------------------------------------------------------- |
| `FATAL_MISSING_OR_INVALID_MANIFEST` | `FATAL`         | Approved preflight manifest missing, invalid, or incompatible. |
| `FATAL_MANIFEST_CHECKSUM_MISMATCH`  | `FATAL`         | Manifest checksum mismatch.                                    |
| `FATAL_WORKBOOK_CHECKSUM_MISMATCH`  | `FATAL`         | Workbook checksum mismatches manifest-pinned checksum.         |
| `FATAL_MISSING_SHEET`               | `FATAL`         | Required source sheet missing.                                 |
| `FATAL_EXTRA_SOURCE_SHEET`          | `FATAL`         | Unexpected non-generated source sheet found.                   |
| `FATAL_DUPLICATE_NORMALIZED_SHEET`  | `FATAL`         | Multiple sheets normalize to same required source.             |
| `FATAL_HIDDEN_SOURCE_SHEET`         | `FATAL`         | Required source sheet hidden.                                  |
| `FATAL_HIDDEN_SOURCE_RANGE`         | `FATAL`         | Hidden required row/column.                                    |
| `FATAL_BAD_SUFFIX`                  | `FATAL`         | Invalid sheet suffix.                                          |
| `FATAL_RANGE_MISMATCH`              | `FATAL`         | Used range differs from manifest.                              |
| `FATAL_BANNER_MISMATCH`             | `FATAL`         | Row 1 banner disagrees with suffix/family.                     |
| `FATAL_BAD_HEADER_ROW`              | `FATAL`         | Row 3 headers missing, shifted, or invalid.                    |
| `FATAL_BAD_AVAILABILITY_WIDTH`      | `FATAL`         | Expected `D:I` or `D:K` layout missing.                        |
| `FATAL_UNMAPPED_SYMBOL`             | `FATAL`         | Unknown nonblank availability symbol.                          |
| `FATAL_ZR1_ZR1X_AMBIGUOUS_COLUMNS`  | `FATAL`         | Cannot split suffix-4 columns safely.                          |
| `FATAL_PRICE_STRUCTURE`             | `FATAL`         | Price Schedule sections/columns missing.                       |
| `FATAL_COLOR_TRIM_BOUNDARY`         | `FATAL`         | Cannot identify Color & Trim matrices.                         |
| `FATAL_AUTOCORRECT_CONFLICT`        | `FATAL`         | Auto-correction maps to multiple possible targets.             |
| `WARN_SHEET_NAME_AUTOCORRECTED`     | `WARN`          | Sheet auto-bound to canonical name.                            |
| `WARN_SYMBOL_USED_NOT_IN_LEGEND`    | `WARN`          | Known symbol appears but legend omits it.                      |
| `WARN_PRICE_NOT_FOUND`              | `WARN`          | No price candidate for RPO.                                    |
| `MANUAL_REVIEW_PRICE_AMBIGUOUS`     | `MANUAL_REVIEW` | Multiple price candidates unresolved.                          |
| `WARN_UNRESOLVED_FOOTNOTE`          | `WARN`          | Marker found but disclosure body missing.                      |
| `MANUAL_REVIEW_RPO_PARSE`           | `MANUAL_REVIEW` | RPO cannot be safely normalized.                               |
| `INFO_REFERENCE_SHEET_PARSED`       | `INFO`          | Equipment Groups parsed as reference data.                     |
| `INFO_ROW_SKIPPED_SECTION`          | `INFO`          | Section/header row skipped as data.                            |

## 24.4 Example Failed Preflight Report

| severity | error_code              | message                                                        | source_sheet | source_row | source_column | source_cell      | raw_value | normalized_value | candidate_values | recommended_action                                              |
| -------- | ----------------------- | -------------------------------------------------------------- | ------------ | ---------: | ------------- | ---------------- | --------- | ---------------- | ---------------- | --------------------------------------------------------------- |
| `FATAL`  | `FATAL_MISSING_SHEET`   | Required source sheet is missing.                              | `Interior 2` |            |               |                  |           |                  |                  | Restore the required sheet or update the approved manifest.     |
| `FATAL`  | `FATAL_UNMAPPED_SYMBOL` | Unknown availability symbols found during preflight inventory. | `Exterior 1` |         42 | `F`           | `Exterior 1!F42` | `P`       |                  | `["P"]`          | Add a manifest-approved symbol mapping or correct the workbook. |

---

# 25. Run Metadata

`Ingest_Run_Metadata` must contain:

| Field                    | Type     | Example                |
| ------------------------ | -------- | ---------------------- |
| `run_id`                 | text     | UUID                   |
| `skill_name`             | text     | `ingestSkillv4`        |
| `skill_version`          | text     | `corvette-ingest-v4.1` |
| `processed_at_utc`       | datetime | ISO-8601               |
| `status`                 | enum     | `SUCCEEDED`, `FAILED`  |
| `source_file`            | text     | workbook filename      |
| `source_workbook_sha256` | text     | hash                   |
| `manifest_id`            | text     | manifest ID            |
| `manifest_version`       | text     | manifest version       |
| `manifest_sha256`        | text     | manifest hash          |
| `model_year`             | integer  | `2027`                 |
| `make`                   | text     | `Chevrolet`            |
| `vehicle_model`          | text     | `Corvette`             |
| `source_sheets_found`    | integer  | `23`                   |
| `source_sheets_missing`  | json     | list                   |
| `rows_processed`         | integer  | count                  |
| `rows_skipped`           | integer  | count                  |
| `errors`                 | integer  | count                  |
| `warnings`               | integer  | count                  |
| `manual_review_items`    | integer  | count                  |
| `unmapped_symbols`       | json     | list                   |
| `duplicate_rpo_count`    | integer  | count                  |
| `price_match_failures`   | integer  | count                  |

---

# 26. Idempotent Rerun Behavior

## 26.1 Generated Sheet Lifecycle

| Case                                     | Handling                                                                   |
| ---------------------------------------- | -------------------------------------------------------------------------- |
| Preflight fails                          | Do not clear or write workbook outputs. Return Markdown validation report. |
| Preflight passes                         | Replace approved generated sheets deterministically.                       |
| Prior generated sheets exist             | Clear/replace only after preflight passes.                                 |
| Prior generated sheets have manual edits | Replace generated sheets; generated outputs are not source of truth.       |
| Source sheets                            | Never modified.                                                            |
| Write failure                            | Roll back temporary generated sheets where possible and report failure.    |

## 26.2 Transaction-Like Write Plan

When supported:

1. Run full preflight.
2. Write generated outputs to temporary sheets.
3. Post-validate headers, types, enums, row counts, and keys.
4. Atomically replace final generated sheets.
5. Delete temporary sheets.

When transactions are unavailable:

1. Run full preflight.
2. Delete approved generated sheets.
3. Recreate generated sheets in deterministic order.
4. Run post-generation validation.
5. If failure occurs, mark run failed and return validation report.

## 26.3 Deterministic Ordering

Sort generated rows by:

```text
source sheet manifest order
source_row
source_column
model_family
trim_code
body_style
rpo_normalized
record_key
```

A rerun against the same source workbook and manifest must produce identical stable keys and row ordering, except for run-specific metadata such as `run_id` and timestamps.

---

# 27. Post-Generation Validation

After writing outputs, validate:

| Check                  | Requirement                                                             |
| ---------------------- | ----------------------------------------------------------------------- |
| Generated sheets exist | All required generated sheets are present.                              |
| Headers                | Exact schema headers and order.                                         |
| Required fields        | Source trace fields are populated.                                      |
| Enums                  | Availability, severity, price, row type, and status values are valid.   |
| Prices                 | Numeric price fields are decimal or null.                               |
| Keys                   | Stable keys are nonblank and unique within table.                       |
| Source coverage        | Every source data row is emitted, skipped, or parsed as reference/note. |
| Phantom RPOs           | No normalized RPO exists without raw source support.                    |
| Footnotes              | Markers are resolved or flagged.                                        |
| Ambiguous prices       | Suppressed prices have validation records.                              |
| ZR1/ZR1X split         | Suffix-4 observations resolve exactly to required eight variant tuples. |
| Color & Trim dashes    | Top dashes emit no rows; lower dashes emit D30 override rows.           |

Any post-generation failure is fatal for the run.

---

# 28. Must Not Do

- Do not write generated workbook outputs before preflight passes.
- Do not mutate source sheets.
- Do not infer package logic.
- Do not infer availability from Equipment Groups.
- Do not force Z06 into `LT` trims.
- Do not collapse ZR1 and ZR1X into a six-column output.
- Do not treat blank availability cells as Not Available.
- Do not treat top Color & Trim dashes as Not Available or D30 overrides.
- Do not treat lower Color & Trim dashes as blanks.
- Do not globally strip digits, hyphens, superscripts, or punctuation.
- Do not create phantom RPOs from footnote-fused tokens.
- Do not silently ignore duplicate RPO price conflicts.
- Do not add DFC to option prices.
- Do not duplicate exterior colors into every variant output unless the source confirms family availability.
- Do not append generated rows on rerun.
- Do not write literal `NULL` unless the downstream loader explicitly requires it.

---

# 29. Acceptance Tests

| Scenario                                             | Expected Result                                                |
| ---------------------------------------------------- | -------------------------------------------------------------- |
| Missing approved preflight manifest                  | Fatal Markdown validation report; no workbook outputs written. |
| Manifest checksum mismatch                           | Fatal; no workbook outputs written.                            |
| Missing `Interior 2`                                 | Fatal; no workbook outputs written.                            |
| Extra copied sheet `Interior 2 Copy`                 | Fatal unless explicitly manifest-approved.                     |
| Hidden required sheet                                | Fatal.                                                         |
| Hidden row inside required range                     | Fatal.                                                         |
| Row 3 shifted to row 4                               | Fatal `FATAL_BAD_HEADER_ROW`.                                  |
| Unknown availability symbol `P`                      | Fatal preflight report listing all unknown symbols.            |
| `Color & Trim 1` instead of `Color and Trim 1`       | Auto-bind only if unique; warning; preserve raw sheet name.    |
| Z06 headers use `1LZ/2LZ/3LZ`                        | Output as LZ trims, not LT trims.                              |
| Z06 headers use `1LT/2LT/3LT`                        | Fatal banner/header conflict.                                  |
| Suffix-4 sheet has eight valid ZR1/ZR1X columns      | Split into required ZR1/ZR1X trim/body observations.           |
| Suffix-4 ZR1/ZR1X boundary ambiguous                 | Fatal manual review.                                           |
| Cell `D`                                             | Available.                                                     |
| Cell `*`                                             | Available.                                                     |
| Cell `□`                                             | Standard.                                                      |
| Cell `■`                                             | Standard.                                                      |
| Cell `--` in normal matrix                           | Not Available.                                                 |
| Blank availability cell                              | No observation; not Not Available.                             |
| Cell `D1`                                            | Available with marker `1`.                                     |
| Cell `□1`                                            | Standard with marker `1`.                                      |
| Top Color & Trim dash                                | Null/no row.                                                   |
| Lower Color & Trim dash                              | D30 override row.                                              |
| `Sky Cool Gray1 en-us`                               | Normalized to `Sky Cool Gray`, marker `1`, suffix flag.        |
| `Z51` token                                          | Not stripped.                                                  |
| `ZR1X` token                                         | Not stripped or confused with `ZR1`.                           |
| `HU76` with known `HU7` and marker `6`               | Normalize only if both validate.                               |
| `HU76` without validating context                    | Preserve raw; manual review.                                   |
| Duplicate RPO in Price Schedule resolved by Column D | Correct price assigned with match status.                      |
| Duplicate RPO unresolved by Column D                 | Price blank, `ambiguous`, candidates listed.                   |
| No price candidate                                   | Price blank, `not_found`, warning.                             |
| Option price `N/C`                                   | Amount `0.00`, status `no_charge`.                             |
| Option price `$0`                                    | Amount `0.00`, status `priced_zero`.                           |
| Option price `Included`                              | Amount `0.00`, status `included`.                              |
| Option price `TBD`                                   | Amount null, status `tbd`.                                     |
| Base variant price                                   | Total equals List Price plus DFC.                              |
| Option price                                         | Equals List Price only; DFC not added.                         |
| Equipment Groups row                                 | Written to reference table only.                               |
| Equipment Groups imply package availability          | Must not broaden availability.                                 |
| Merged Color & Trim paint header                     | Logical fill applied; trace preserved.                         |
| Exterior paint premium price                         | Sourced from Price Schedule Paint section only.                |
| Rerun same workbook and manifest                     | Same stable keys and row order; no duplicate appended rows.    |
