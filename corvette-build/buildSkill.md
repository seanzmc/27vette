---
name: corvette-build
description: Build and maintain per-variant Corvette stepped-form data from the sheets produced by corvette-ingest. Use this skill whenever Sean is turning `Option Catalog`, `Availability Long`, `Pricing Long`, `Base Prices`, `Interior Trim Combos`, and `Color Combination Availability` into a variant-scoped order flow with step order, compatibility logic, auto-added RPOs, and accurate pricing. Trigger on requests like "build out Stingray", "wire the order flow", "set up Z06 interior logic", "resolve option compatibility", "make pricing accurate", or "finish the variant form". Do NOT use this skill to ingest raw GM exports or price schedules.
---

# Corvette Build

Turn ingest's normalized sheets into a variant-scoped build flow that behaves like a stepped order form.

The output is not a mirror of GM's source workbook. It is a rule-bearing layer that can:

- guide a user through a Corvette order in a fixed sequence
- filter later choices based on earlier choices
- auto-add required RPOs
- suppress invalid combinations
- resolve the correct price for the active body, trim, and option context

## Core mental model

- Build one model family at a time. Stingray, Grand Sport, Z06, ZR1, and ZR1X may share patterns, but they do not share truth.
- The form is linear. Earlier steps create context. Later steps must be filtered from that context.
- Published combinations should be represented as rows. The row is the rule.
- Compatibility prose and disclosures should become structured logic only when the condition is explicit.
- The same RPO may exist on multiple variants with different price, scope, or behavior. Duplicate per-variant data instead of centralizing it.

Sean's real-world order flow is the model:

1. Variant (Stingray, Grand Sport, Z06, ZR1, ZR1X)
2. Body style (Coupe or Convertible)
3. Trim Level (1LT, 2LT, 3LT, 1LZ, 2LZ, or 3LZ depending on the variant)
4. Exterior paint (consistent across variants but also the source of some of the most complex logic due to interior color pairings, stripe color compatibility, and some package interactions)
5. Exterior Appearance sections (roof, accents, badges, engine appearance, etc. that are gated by body style, model, and sometimes trim)
6. Wheels (model-specific with some shared carbon fiber options)
7. Brake calipers (color options with some model-specific restrictions)
8. Packages and major performance options (Highly conditional on the variant)
9. Aero, exhaust, stripes, and accessories (all with various conditions, some of which are model-specific)
10. Interior setup (Most complex step with the most conditions)
    1.  Seat choice (Determined by trim level selection)
    2.  Interior Color Selection (Varies depending on the seat choice)
    3.  Additive interior styling options like suede inserts, two-tone seats, and custom stitching that are conditionally available based on interior color and seat choice.
    4.  Seat Belt Color (Some color combination restrictions exist here as well plus some 3LT/LZ interiors include a custom seat belt color for no charge.)
    5.  Interior trim options (stealth trim, carbon fiber trim, and PDR all have trim level conditions and some model specific conditions as well)
11. Custom delivery options (R8C, PIN, BV4, and PCB)
12. Summary and pricing

Build data so the form can follow that sequence without improvising logic in the UI.

## What build consumes

Always start from ingest outputs:

- `Option Catalog`
- `Availability Long`
- `Pricing Long`
- `Base Prices`
- `Interior Trim Combos`
- `Color Combination Availability`

Legacy sheets are reference material only. If they disagree with ingest, ingest wins unless Sean says otherwise.

## Canonical per-variant outputs

Each model family gets four build sheets:

1. `<Variant> Options`
2. `<Variant> Interior`
3. `<Variant> Exterior`
4. `<Variant> Standard Equipment`

`Base Prices` remains shared from ingest. Do not duplicate it into each variant unless Sean asks for that explicitly.

## 1. `<Variant> Options`

This is the main selectable-options sheet. It holds everything that behaves like an orderable line item other than the base interior and the exterior/interior pair grid.

Examples:

- packages like `Z51`
- seat upgrades like `AH2` and `AE4`
- additive interior stylings like `TU7`, `36S`, `37S`, `38S`
- wheels, calipers, spoilers, stripes, exhaust, trim packages, LPOs, accessories
- hidden or auto-only charge codes like `N26`, `D30`, or `R6X` when they need structured pricing

One row represents one valid option context. If the same RPO changes behavior by body, trim, package, or compatibility state, duplicate the row and scope each copy to its context.

### Required columns

| Column | Meaning |
|---|---|
| `row_id` | Stable row key. Do not use bare `rpo_code` because the same RPO may need multiple rows for different contexts. |
| `step_key` | The stepped-form bucket: `package`, `seat`, `interior_style`, `seat_belt`, `interior_trim`, `exterior_appearance`, `wheel`, `caliper`, `aero`, `exhaust`, `stripe`, `accessory`, `delivery`, etc. |
| `group_key` | Choice group within the step. Example: all wheels share one `group_key`; accessories may each have their own. |
| `choice_mode` | `single` or `multi`. |
| `display_order` | Integer order within the step/group. |
| `ui_mode` | `selectable`, `auto_only`, or `summary_only`. |
| `rpo_code` | The order code this row represents. |
| `name` | Display name. |
| `description` | Short human-facing description. |
| `section` | Exterior, Interior Styling, Wheels, Packages, Accessories, etc. |
| `body_scope` | Pipe-delimited allowed bodies, usually `Coupe|Convertible`, `Coupe`, or `Convertible`. |
| `trim_scope` | Pipe-delimited allowed trims for the variant, e.g. `1LT|2LT|3LT` or `1LZ|3LZ`. |
| `requires_all` | Pipe-delimited RPOs that must already be on the build. |
| `requires_any` | Pipe-delimited RPOs where at least one must already be on the build. Use only when the source clearly states an OR condition. |
| `excludes` | Pipe-delimited RPOs that block this row. |
| `auto_added_rpos` | Pipe-delimited RPOs automatically added when this row is selected. |
| `available_with_interior_rpos` | Pipe-delimited base interior RPOs this row may layer onto. Blank means no interior-specific restriction. |
| `available_with_exterior_rpos` | Pipe-delimited exterior paint RPOs this row may coexist with. Blank means no exterior-specific restriction. |
| `price_<trim>` | One price column per actual trim on the variant. Use real trim names like `price_1LT`, `price_2LT`, `price_3LT`. |
| `std_<trim>` | Boolean standard-equipment flags by trim. |
| `compat_note` | Short human-readable explanation of the condition. |
| `source_note` | Verbatim compatibility/disclosure text that justified the row. |
| `notes` | Build-only comments or unresolved caveats. |

### How to use this sheet

- Use one row when the option behaves the same across all valid contexts.
- Duplicate the row when the option's price or availability changes under a specific condition.
- Keep auto-only charge codes here if the form must price them but the user does not explicitly select them.

Examples:

- `E60` on Stingray should have `trim_scope = 2LT|3LT`, not a prose-only note saying "not available on 1LT".
- `TVS` with a regular price and `TVS` no-charge with `Z51` should be two rows:
  - priced row with `excludes = Z51`
  - zero-price row with `requires_all = Z51`
- chrome exhaust tips that require `WUB` should have `requires_all = WUB`
- `TU7` should stay here as an additive option, with `requires_all = AH2` and `available_with_interior_rpos` listing the eligible base interiors

## 2. `<Variant> Interior`

This is the base-interior enumeration sheet. One row per legal base interior configuration for the variant.

Build it directly from ingest's `Interior Trim Combos`. Do not decompose a published interior back into separate color, suede, dipped, asymmetrical, and trim-material modifier fields. The interior row already is the valid state.

### Required columns

| Column | Meaning |
|---|---|
| `combo_id` | Stable key from ingest. |
| `trim` | `1LT`, `2LT`, `3LT`, `1LZ`, `2LZ`, `3LZ`, etc. |
| `seat_code` | The seat RPO tied to this base interior row. |
| `seat_type_name` | Human label for the seat. |
| `seat_trim_material` | Material description from ingest. |
| `interior_color_rpo` | The complete interior-treatment RPO for this row. |
| `interior_color_name` | Human label for the treatment. |
| `source_sheet_origin` | Usually `recommended` or `custom_r6x`. |
| `auto_added_rpos` | RPOs forced by selecting this interior, such as `R6X` or a hidden required companion charge. |
| `requires_all` | Variant-specific prerequisites if they are explicit and row-scoped. |
| `excludes` | Variant-specific conflicts if they are explicit and row-scoped. |
| `price_offset` | Upcharge relative to the trim's included base interior. Blank or `0` means no interior-specific upcharge. |
| `source_note` | Verbatim disclosure text carried from ingest when it matters. |
| `notes` | Build-only caveats. |

### How to use this sheet

- Filter by active trim first.
- Filter by selected seat second.
- Present the remaining distinct `interior_color_rpo` values as the base interior choices.
- If a row does not exist, the form cannot offer it.
- Additive interior options like `TU7` or stitching packages do not belong here. They stay in `<Variant> Options`.

Use this sheet to model cases like:

- 1LT with standard `AQ9` and a small color set
- 1LT `AE4` only with a specific base interior
- 2LT and 3LT interiors that branch heavily by seat, material, and color treatment
- custom interiors that automatically force `R6X` in 3LT only

## 3. `<Variant> Exterior`

This sheet has two sections.

### 3a. Exterior paint list

One row per exterior paint context available on the variant.

| Column | Meaning |
|---|---|
| `row_id` | Stable row key. Duplicate when the same paint behaves differently under different contexts. |
| `exterior_color_rpo` | Paint code. |
| `exterior_color_name` | Paint label. |
| `excludes` | Pipe-delimited blocked RPOs. (ex. ZYC on GBA)|
| `price` | Paint price. 4 out of 10 paint colors have an upcharge. |
| `compat_note` | Short human explanation. |
| `source_note` | Verbatim disclosure text justifying the row. |
| `notes` | Build-only caveats. |

### 3b. Exterior/interior pair grid

Consume ingest's `Color Combination Availability` after filtering to the `interior_color_rpo` values that actually exist in this variant's `<Variant> Interior` sheet.

| Column | Meaning |
|---|---|
| `pair_id` | Stable key from ingest. |
| `exterior_color_rpo` | Paint code. |
| `interior_color_rpo` | Base interior code. |
| `availability_label` | `Published Available`, `Requires D30 Override`, `Requires R6X`, or `Requires R6X and D30`. |
| `auto_added_rpos` | Blank, `D30`, `R6X`, or `D30|R6X`. |
| `source_note` | Disclosure text from ingest when present. |
| `notes` | Build-only caveats. |

Rules:

- Keep every valid pair row that ingest produced for this variant's interiors.
- Do not compact this back into prose like "not available with red interiors".
- Preserve both `D30` and `R6X` in `auto_added_rpos` even if later pricing collapses to one charge.

## 4. `<Variant> Standard Equipment`

This is presentation content, not filtering logic.

One row per standard-equipment item with inclusion flags by trim. Use ingest's `Availability Long` rows where the item is standard.

Suggested columns:

- `section`
- `rpo_code`
- `name`
- `description`
- `included_1`
- `included_2`
- `included_3`
- `notes`

Use actual trim labels if the variant does not use 1/2/3.

## Step order and runtime behavior

The form should consume the build layer in this order. This matches the tested real-world order flow, not a pure dependency-topology order, so some earlier selections are provisional and must be revalidated later.

1. **Variant**
   Build skill works one variant at a time, so this choice usually happens before the variant sheets are read.
2. **Body style**
   Establish body context first. This gates roof options, engine appearance items, some accessories, and body-scoped pricing.
3. **Trim**
   Trim is the strongest early filter. It determines base vehicle price and most of the interior surface area.
4. **Exterior paint**
   Read `<Variant> Exterior` paint rows filtered by body and trim. Treat the chosen paint as provisional until packages/performance and the final interior are known.
5. **Exterior appearance**
   Read `<Variant> Options` rows with `step_key = exterior_appearance`. This includes roof, accents, badges, engine appearance, and similar body- or trim-gated items.
6. **Wheels**
   Read `<Variant> Options` rows with `step_key = wheel`. Because some package logic lands later, wheel selections must be revalidated after step 8.
7. **Brake calipers**
   Read `<Variant> Options` rows with `step_key = caliper`. These are also provisional until package/performance context is complete.
8. **Packages and major performance options**
   Read `<Variant> Options` rows with `step_key = package` or equivalent. After this step, revalidate paint, exterior appearance, wheel, and caliper selections against the newly active package context.
9. **Aero, exhaust, stripes, and accessories**
   Read the remaining `<Variant> Options` groups in display order, filtered by the current body, trim, package, and paint context.
10. **Interior setup**
   Process this as an ordered subflow:
   `seat` -> `base interior` -> `interior_style` -> `seat_belt` -> `interior_trim`

   Runtime behavior inside this step:
   - Read `<Variant> Options` seat rows first. Seat choice filters `<Variant> Interior`.
   - Read `<Variant> Interior` next, filtered by trim and seat.
   - Read additive interior styling rows from `<Variant> Options`, filtered by selected base interior and current package context.
   - Read seat belt color rows from `<Variant> Options`, filtered by current interior and any explicit restrictions.
   - Read interior trim rows from `<Variant> Options` for stealth trim, carbon fiber trim, PDR, and similar interior-adjacent selections.

   After the interior subflow completes, revalidate the current exterior paint against `<Variant> Exterior` section 3b. If the selected paint/interior pair requires `D30`, `R6X`, or both, add those codes automatically. If the pair is invalid, clear the paint choice and force reselection.
11. **Custom delivery options**
   Read `<Variant> Options` rows with `step_key = delivery` for `R8C`, `PIN`, `BV4`, `PCB`, and similar delivery/program choices.
12. **Summary**
   Recompute auto-adds, validate the final selection set, and resolve pricing.

Runtime invalidation rules:

- When an upstream step changes, clear and rebuild any downstream selections that are no longer valid.
- Because this tested order includes backward dependencies, later steps must also revalidate certain earlier provisional selections:
  - packages/performance revalidate paint, exterior appearance, wheels, and calipers
  - completed interior setup revalidates exterior paint through the pair grid
- Do not preserve stale choices by guesswork. Keep them only if they still match the active scoped row.

## Turning notes and disclosures into structured logic

Build must actively use the compatibility notes and disclosures carried through ingest. These notes are the source for conditional logic when the logic is explicit.

Promote prose into fields using these example patterns:

- `Requires Z51` -> `requires_all = Z51`
- `Requires AH2 or AE4` -> `requires_any = AH2|AE4`
- `Not available with FE4` -> `excludes = FE4`
- `Available with HUK, HU6, HUL, HU7` -> `available_with_interior_rpos = HUK|HU6|HUL|HU7`
- `Coupe only` -> `body_scope = Coupe`
- `2LT/3LT only` -> `trim_scope = 2LT|3LT`
- `Includes N26` or `adds suede wheel charge` -> `auto_added_rpos = N26`
- `No charge with Z51` -> duplicate a zero-price row scoped with `requires_all = Z51`, and make the priced row exclude `Z51`
- `Requires D30` or `Requires R6X` on an exterior/interior pair -> keep that on the pair row's `auto_added_rpos`

Use these note sources in this order:

1. `Availability Long.compat_note_text`
2. `Option Catalog.footnote_texts`
3. `Option Catalog.notes`
4. `Pricing Long.context_note_raw`
5. `Interior Trim Combos` and `Color Combination Availability` notes/disclosures

If a note is ambiguous, keep it in `source_note` and flag it for Sean. Do not invent a rule.

## Pricing resolution

Pricing must resolve from active context, not from one static row per RPO.

### Base vehicle price

Read the active body + trim from ingest's `Base Prices`.

### Option price

For every selected or auto-added RPO:

1. Find all rows for that RPO on `<Variant> Options` or the relevant build sheet.
2. Keep only rows whose `body_scope`, `trim_scope`, `requires_all`, `requires_any`, `excludes`, `available_with_interior_rpos`, and `available_with_exterior_rpos` all match the current build state.
3. From the remaining rows, choose the most specific one.

Specificity is determined by how many context filters the row uses. A row scoped to `Z51` and `Convertible` beats a row scoped only to `Convertible`.

### Practical result

This handles cases like:

- same RPO, different price by model family
- same RPO, no-charge when paired with a package
- seat upgrades whose compatible interiors depend on the selected seat
- `D30` and `R6X` both landing on the build while only one charge survives in context

If no row matches a selected or auto-added RPO, that is a build error and must be reported.

## How to build

### Step 1: Pick the variant

Work one model family at a time. Even if the frontend will eventually unify variants, the build layer stays variant-scoped.

### Step 2: Build the step groups

Populate `<Variant> Options`, `<Variant> Interior`, `<Variant> Exterior`, and `<Variant> Standard Equipment` so they support the runtime step order above.

### Step 3: Translate explicit note logic

Read ingest's note and disclosure fields and promote only the explicit conditions into structured fields.

### Step 4: Duplicate rows where context changes behavior

Do not overload a single row with prose like "no charge with Z51" or "convertible only at this price". Split those into separate scoped rows.

### Step 5: Validate the full order path

The build is not done when the sheets look complete. It is done when a realistic order can move through the steps and always land on the correct availability and price.

## Validation gates

Before handing back a variant build:

- Every RPO referenced in `requires_all`, `requires_any`, `excludes`, `auto_added_rpos`, `available_with_interior_rpos`, and `available_with_exterior_rpos` exists in `Option Catalog`
- Every price cell is numeric, blank, or `0`
- Every `row_id` and `combo_id` is unique
- Every `interior_color_rpo` in `<Variant> Exterior` section 3b exists in `<Variant> Interior`
- Every pair row's `availability_label` matches its `auto_added_rpos`
- At least three end-to-end sample builds can be read back as plain English and still be true

Example checks:

- On Stingray 1LT, `AE4` is selectable, filters interior to the allowed `AE4` rows, and auto-adds the correct suede-wheel charge if the selected interior requires it.
- On Stingray, `T0A` prices correctly both with and without `Z51`.
- A custom interior/exterior pair that requires `R6X` and `D30` lands both codes on the build and resolves the correct net charge.

## Two-phase execution

For any non-trivial build task:

**Phase 1 — Plan**

- identify the variant
- list the ingest sheets that will be read
- state which build sheets will be produced or changed
- show 3-5 representative rule translations from notes into structured fields
- show 2-3 representative pricing cases
- stop for approval

**Phase 2 — Build**

- write the variant sheets
- validate them against the runtime order path
- report row counts, unresolved notes, and any pricing exceptions

## What this skill does NOT do

- Does not re-ingest raw GM exports or price schedules
- Does not treat prior legacy sheets as source of truth
- Does not build one giant cross-variant pricing engine
- Does not leave critical logic buried in prose when the condition is explicit
- Does not invent rules from ambiguous disclosures

## Failure modes to avoid

- Building data that mirrors the workbook instead of the order flow
- Treating trim restrictions as human notes instead of structured fields
- Re-decomposing published interiors into modifier stacks
- Hiding `D30`, `R6X`, `N26`, or similar forced-charge behavior in notes
- Keeping one row for an RPO whose price changes by package or body context
- Letting downstream selections survive after an upstream change invalidates them
- Assuming a rule on one model family applies unchanged to another
