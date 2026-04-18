---
name: corvette-build
description: Build and maintain per-variant Corvette order-flow framework from the ingested intermediate layer. Use this skill whenever Sean is shaping Stingray, Grand Sport, Z06, Grand Sport X, ZR1, or ZR1X configurator data, defining valid interior or exterior relationships, pricing options by trim and body style, or preparing variant sheets for the interactive order form. Trigger on phrases like "build out Stingray", "set up Z06 interior framework", "wire exterior color conflicts", "price the 2LT options", or "finish the next variant sheet". Do NOT use this skill for flattening raw GM exports or ingesting price schedules — that is corvette-ingest's job.
---

# Corvette Build

Build the per-variant order-flow framework that the configurator reads.

The goal is not to split ingest back into model-specific copies of GM's source tabs. The goal is to turn ingest's flattened layer into variant-scoped sheets that can:

- price a full vehicle order
- enumerate legal interior selections
- constrain invalid option combinations
- auto-add required RPOs like `D30` and `R6X`
- expose clean relationships for JSON/schema export

## Core principle: enumerate valid states

When GM has already published a bounded list of valid configurations, represent each valid state as a row. The row is the rule.

Only use explicit `requires`, `excludes`, or `auto_added_rpos` when the relationship is truly additive or cannot be expressed by row existence alone.

Do not:

- rebuild cross-variant abstractions to avoid duplication
- decompose complete interiors back into seat/color/suede modifier stacks
- recreate ingest's source-oriented tables just because they already exist upstream

## The per-variant framework

Each model family has four canonical sheets:

1. `<Variant> Options`
2. `<Variant> Interior`
3. `<Variant> Exterior`
4. `<Variant> Standard Equipment`

Body style stays in columns where needed. Do not create separate Coupe and Convertible sheet families.

### 1. `<Variant> Options`

This is the selectable-options sheet for the variant. It holds standalone options and additive stylings: wheels, packages, spoilers, calipers, stripes, exhaust, LPOs, seat upgrades, two-tone treatments, stitching packages, and other line items that behave like orderable options.

| Column | Meaning |
|---|---|
| `rpo_code` | |
| `name` | |
| `description` | |
| `section` | Exterior, Wheels, Spoilers, Calipers, Accessories, Packages, Interior Styling, etc. |
| `category` | Free-text tags for grouping (`wheels, lpo`, `packages, performance`) |
| `price_1lt` / `price_1lz` | Price on 1LT or 1LZ. Blank = not available. `0` = no-charge or standard when paired with the corresponding `std_*` flag. |
| `price_2lt` / `price_2lz` | |
| `price_3lt` / `price_3lz` | |
| `std_1lt` / `std_2lt` / `std_3lt` | Boolean standard-equipment flags by trim |
| `body_restriction` | `coupe_only`, `convertible_only`, or blank |
| `requires` | Pipe-delimited RPOs that must also be selected |
| `excludes` | Pipe-delimited RPOs that cannot be co-selected |
| `available_with_interior_rpos` | Pipe-delimited base interior RPOs this option may be layered onto. Use for additive interior stylings such as `TU7`, `36S`, `37S`, `38S`, or any option note that says "Available with [specific interiors]". If compatibility differs by trim, either use one row per trim context or tag the list with trim prefixes. This column belongs here, not in `<Variant> Interior`, because it describes an additive option's compatibility against an already-selected base interior. |
| `compat_note` | Plain-English compatibility note for human reference |
| `notes` | Source notes and build notes |

Separate price columns per trim rather than separate rows. A cell may hold a number, `0`, or blank. If something is standard, also set the matching `std_*` flag.

### 2. `<Variant> Interior`

This is the base-interior enumeration sheet. One row per legal interior configuration for the variant.

Build this sheet directly from ingest's `Interior Trim Combos`. Each ingest row already represents one complete interior treatment at GM's published grain: trim + seat + seat-trim-material + interior treatment + interior-color RPO. Preserve that grain.

| Column | Meaning |
|---|---|
| `combo_id` | Stable key from ingest, e.g. `ctc_3lt_ah2_htt` |
| `trim` | `1LT`, `2LT`, `3LT`, `1LZ`, `2LZ`, `3LZ` |
| `seat_code` | Single seat RPO (`AQ9`, `AH2`, `AE4`, `AUP`) |
| `seat_type_name` | "GT1 buckets", "GT2 buckets", etc. |
| `seat_trim_material` | Material description from ingest |
| `interior_color_rpo` | The single RPO representing the complete interior treatment |
| `interior_color_name` | Display name of the treatment |
| `source_sheet_origin` | `recommended` or `custom_r6x` |
| `auto_added_rpos` | RPOs that selecting this interior forces onto the build, such as `R6X` for any `custom_r6x` row |
| `price_offset` | Interior pricing relative to the trim's base included interior |
| `requires_in_variant` | Pipe-delimited RPOs layered on by variant-specific order rules |
| `excludes_in_variant` | Pipe-delimited RPOs this interior cannot coexist with on this variant |
| `notes` | Human-readable caveats only |

Rules for this sheet:

- If a combo is not present in ingest's `Interior Trim Combos` for the trims this variant supports, do not create it.
- Keep one seat code per row. If GM showed `AH2 / AE4` upstream, ingest already expanded it. Build keeps those as separate rows.
- Keep additive interior stylings out of this sheet. `TU7`, custom stitching, and similar "available with these interiors" options stay in `<Variant> Options`.
- If ingest carries human-readable disclosure prose in `notes` or related fields, treat it as reference only unless Sean explicitly turns it into a structured build rule.

The configurator reads this sheet by trim, then by seat, then offers the remaining `interior_color_rpo` values as valid base interior choices.

### 3. `<Variant> Exterior`

This sheet has two sections.

**3a. Exterior paint list**

One row per exterior paint available on this variant.

| Column | Meaning |
|---|---|
| `exterior_color_rpo` | |
| `exterior_color_name` | |
| `touch_up_paint_number` | |
| `price_coupe` / `price_convertible` | Price per body style. Blank = not available on that body. |
| `body_restriction` | `coupe_only`, `convertible_only`, or blank |
| `requires_in_variant` | Pipe-delimited RPOs this paint forces on this variant |
| `excludes_in_variant` | Pipe-delimited RPOs this paint cannot coexist with on this variant |
| `notes` | |

**3b. Exterior/interior compatibility grid**

This section comes from ingest's `Color Combination Availability`, filtered to interior RPOs that actually exist in this variant's `<Variant> Interior` sheet.

| Column | Meaning |
|---|---|
| `pair_id` | Stable key from ingest |
| `exterior_color_rpo` | |
| `interior_color_rpo` | |
| `availability_label` | `Published Available`, `Requires D30 Override`, `Requires R6X`, or `Requires R6X and D30 (one charge collapses per disclosure)` |
| `auto_added_rpos` | Blank, `D30`, `R6X`, or `D30\|R6X` |
| `notes` | |

Rules for this sheet:

- Only include pairs whose `interior_color_rpo` exists in this variant's `<Variant> Interior` sheet.
- Preserve `D30` and `R6X` as separate auto-added codes even when pricing collapses to one charge.
- Do not collapse this grid back into compact "incompatible colors" text fields. The row-level matrix is the order-flow artifact.

### 4. `<Variant> Standard Equipment`

This is presentation content, not logic. One row per standard-equipment item with trim inclusion flags.

Suggested columns: `section`, `rpo_code`, `name`, `description`, `trim_1_included`, `trim_2_included`, `trim_3_included`.

## Shared inputs from ingest

Build reads from ingest's canonical intermediate layer:

- `Option Catalog`
- `Availability Long`
- `Pricing Long`
- `Base Prices`
- `Interior Trim Combos`
- `Color Combination Availability`

Build does not rewrite those sheets. It projects them into variant-specific order-flow sheets.

## What `<Variant>` means

One set of the four sheets above per model family:

- `Stingray Options`, `Stingray Interior`, `Stingray Exterior`, `Stingray Standard Equipment`
- `Grand Sport Options`, `Grand Sport Interior`, `Grand Sport Exterior`, `Grand Sport Standard Equipment`
- `Z06 Options`, `Z06 Interior`, `Z06 Exterior`, `Z06 Standard Equipment`
- `E-Ray Options`, `E-Ray Interior`, `E-Ray Exterior`, `E-Ray Standard Equipment`
- `ZR1 Options`, `ZR1 Interior`, `ZR1 Exterior`, `ZR1 Standard Equipment`
- `ZR1X Options`, `ZR1X Interior`, `ZR1X Exterior`, `ZR1X Standard Equipment`

## How to work

### Step 1: Confirm the exact build target

Confirm one model family and one sheet. If Sean asks for a broad variant build, still execute one sheet at a time so the sources and validation stay clear.

### Step 2: Pull only the relevant ingest inputs

- **Options sheet**: `Option Catalog`, `Availability Long`, `Pricing Long`
- **Interior sheet**: `Interior Trim Combos`, `Pricing Long`
- **Exterior sheet**: `Option Catalog`, `Availability Long`, `Pricing Long`, `Color Combination Availability`
- **Standard Equipment sheet**: `Availability Long`

Use Sean's prior workbook patterns only as layout references. They are not source of truth.

### Step 3: Shape the variant's order-flow logic

Build toward a full valid order path, not toward a mirrored source workbook.

For the variant in scope:

- enumerate the base selectable states first
- attach prices by trim and body style
- add explicit `requires`, `excludes`, and `auto_added_rpos` only where the row model cannot express the relationship
- keep additive styling options tied to the eligible base interiors through `available_with_interior_rpos`
- preserve exterior/interior compatibility at the pair level

### Step 4: Validate

Before calling a sheet done:

- Every referenced RPO resolves in `Option Catalog`
- Every price cell is numeric, `0`, or blank
- Every `requires`, `excludes`, `requires_in_variant`, `excludes_in_variant`, and `auto_added_rpos` value resolves to a real RPO
- In `<Variant> Interior`, every `combo_id` is unique
- In `<Variant> Options`, every `available_with_interior_rpos` value resolves to an `interior_color_rpo` present in this variant's `<Variant> Interior` sheet
- In `<Variant> Exterior` section 3b, every pair's `availability_label` matches `auto_added_rpos`
- Spot-check at least three full order paths as plain English statements

### Step 5: Report

Tell Sean:

- what sheet was built
- what sources were used
- row counts by section
- what required judgment
- what was left unresolved

## Two-phase execution

For any non-trivial build task:

**Phase 1 — Plan**

- identify the exact sheet
- list the ingest inputs to be used
- estimate row count
- show 3-5 representative rows
- flag any decisions Sean needs to make

Stop and wait for approval.

**Phase 2 — Build**

After approval, build the sheet, validate it, and report actual row counts plus any deviations from plan.

## What this skill does NOT do

- Does not re-ingest raw GM exports or price schedules
- Does not recreate ingest's source-oriented sheets inside the variant workbook
- Does not build a unified cross-variant rules engine
- Does not infer structured rules from prose unless Sean explicitly wants that rule authored
- Does not treat legacy workbook artifacts as source of truth
- Does not modify multiple variants as a side effect of one task

## Failure modes to avoid

- Reversing ingest by splitting the intermediate layer back into source-like sheets
- Putting additive interior options into `<Variant> Interior` instead of relating them to base interiors through `<Variant> Options`
- Dropping `D30` or `R6X` from a valid exterior/interior pair because pricing later collapses one of the charges
- Rebuilding complete interiors as modifier stacks when GM already published them as complete interior RPOs
- Extending the sheet schema without Sean's approval
- Skipping Phase 1 on a non-trivial task
