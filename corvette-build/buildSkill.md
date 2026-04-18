---
name: corvette-build
description: Build and maintain per-variant Corvette configurator data — the sheets that drive Sean's order form. Use this skill whenever Sean is working on a specific model family's options, interior combinations, exterior conflicts, pricing, or form logic (Stingray, Grand Sport, Z06, Grand Sport X, ZR1, ZR1X). Trigger on phrases like "build out Stingray", "add the 2LT interior combos", "Z06 wheels and calipers", "fix the exterior color conflicts", "set up the next variant sheet", "the form logic for X", or any request where the deliverable is configurator-ready data for one model family. Also trigger when Sean asks to migrate content out of legacy sheets (Option Rules Clean, Option Price Scopes Clean, Choice Groups Clean) into per-variant sheets. Do NOT use this skill for ingesting raw GM exports or price schedules — that is corvette-ingest's job.
---

# Corvette Build

Build the per-variant sheets that the order form reads. Each model family gets its own set of sheets. Data is duplicated across variants when it differs — do not abstract it back into cross-variant rule tables.

## Core principle: enumerate over abstract

When the space of valid combinations is bounded, list every legal combination as a row. The existence of the row is the rule.

When combinations are unbounded or genuinely cross-cutting, write a rule — but only then, and only scoped to one variant.

Sean's `STINGRAY_INT` pattern from prior work was the prototype for this approach. The corvette-ingest skill now produces the equivalent data (`Interior Trim Combos`, `Color Combination Availability`) directly from GM's Color and Trim sheets, at GM's own grain: one RPO per complete interior treatment, one row per published exterior/interior pairing (with D30/R6X states for unpublished combinations). The build skill consumes those outputs as-is rather than re-decomposing them into modifier stacks. The form filters rows by current selections — no rule engine needed.

## The data model

Per model family, the canonical set is:

### 1. `<Variant> Options` — the flat options sheet

Standalone options where availability is mostly yes/no and price is usually one number per trim. Wheels, spoilers, calipers, accessories, packages, exhaust, stripes, LPOs. Pattern matches the `STINGRAY` tab in Sean's `26MY_Pre` workbook.

| Column | Meaning |
|---|---|
| `rpo_code` | |
| `name` | |
| `description` | |
| `section` | Exterior, Wheels, Spoilers, Calipers, Accessories, Packages, etc. |
| `category` | Free-text tags for grouping (`wheels, lpo`, `spoilers, carbon_fiber`) |
| `price_1lt` / `price_1lz` | Price on 1LT (or 1LZ for performance variants). Blank = not available. `0` with a `std_*` flag = standard. |
| `price_2lt` / `price_2lz` | |
| `price_3lt` / `price_3lz` | |
| `std_1lt` / `std_2lt` / `std_3lt` | Boolean — standard equipment on this trim |
| `body_restriction` | `coupe_only`, `convertible_only`, or blank |
| `requires` | Pipe-delimited RPOs that must also be selected. Only for same-sheet dependencies. |
| `excludes` | Pipe-delimited RPOs that cannot be co-selected |
| `available_with_interior_rpos` | Pipe-delimited base interior color RPOs this option is available with (used for additive interior stylings like TU7, 36S/37S/38S). Blank if this option has no interior dependency. If the compatibility differs by trim, use one row per trim or tag the list with trim prefixes (`2LT:HUK\|HU6\|HUL\|HU7\|HTN\|HTQ; 3LT:HU1\|HU9\|HU2\|HUA\|HUE\|HTG\|HMO\|HVV\|HU0\|HXO`) — document which convention the sheet uses in its column header notes. |
| `compat_note` | Plain-English compatibility note for human reference |
| `notes` | Source notes, footnotes, anything else |

Separate price columns per trim rather than separate rows. The variant's body style + trim determines which price column the form reads. A cell can hold: a number (paid price), `0` (no-charge), `"std"` marker (standard — also set `std_*` boolean), blank (not available).

### 2. `<Variant> Interior` — the enumerated interior configurations

One row per legal interior configuration. This is the enumeration sheet. It reads directly from ingest's `Interior Trim Combos` — each interior color RPO in that layer represents one complete, pre-combined interior (seat × seat-trim-material × color-treatment × any suede/two-tone/asymmetric styling), not a stack of composable modifiers. The build skill preserves that grain: one interior color RPO = one row.

| Column | Meaning |
|---|---|
| `combo_id` | Stable key from ingest, e.g. `ctc_3lt_ah2_htt` |
| `trim` | `1LT`, `2LT`, `3LT`, `1LZ`, `2LZ`, `3LZ` |
| `seat_code` | Single seat RPO (`AQ9`, `AH2`, `AE4`, `AUP`) — one per row, as produced by ingest |
| `seat_type_name` | "GT1 buckets", "GT2 / Competition buckets", etc. |
| `seat_trim_material` | Napa leather, Napa with sueded microfiber, Mulan leather, Performance Textile — copied from ingest |
| `interior_color_rpo` | The single RPO representing this complete interior (e.g. `HTA`, `HU1`, `HTT`) |
| `interior_color_name` | The treatment name as shown in GM's Color and Trim (e.g. "Jet Black", "Adrenaline Red Dipped", "Ultimate Suede Jet Black", "Asymmetrical Adrenaline Red / Jet Black") |
| `source_sheet_origin` | `recommended` or `custom_r6x` — from ingest |
| `auto_added_rpos` | RPOs that selecting this interior forces onto the build (e.g. `R6X` for any custom_r6x row; `N26` if the suede-material interior requires it per variant rules; pipe-delimited) |
| `price_offset` | Interior pricing relative to the variant's base-trim-included interior. Blank or `0` for trim-standard interiors. Numeric for upcharge interiors (e.g. AE4 `+$1,095` on Stingray 1LT). |
| `requires_in_variant` | Pipe-delimited RPOs the variant's own rules layer onto this interior (e.g. AE4-bearing rows may require N26 on this variant even though the ingest row doesn't say so) |
| `excludes_in_variant` | Pipe-delimited RPOs this interior cannot coexist with on this variant |
| `notes` | Source notes, variant-specific caveats, migration provenance |

If a combination is not in ingest's `Interior Trim Combos` for the variant's applicable trims, it does not appear here. The form cannot offer it because the row does not exist.

The form reads this sheet filtered by current trim selection, then by current seat selection (matching against `seat_code`), and offers the resulting distinct `interior_color_rpo` values as the color-treatment choices.

**On seat codes, one per row.** Ingest produces one row per seat code — `AH2 / AE4` in the GM source has already been expanded by ingest into two separate rows, each carrying the same interior color RPO, trim, and seat_trim. Build preserves that grain. If the seat codes price differently as line items, those prices live in `<Variant> Options` (one row per seat RPO) — the interior row does not carry the seat's line-item price, only any interior-specific upcharge in `price_offset`. If the interior price offset itself differs between AH2 and AE4 for the same color RPO, the ingest rows already carry those as distinct rows; use them as-is.

**Consuming ingest's footnote scope columns.** Ingest populates four optional columns on `Interior Trim Combos` that carry structured footnote scope: `footnote_scope_trim`, `footnote_scope_model_family`, `footnote_scope_body_style`, and `footnote_scope_fragment`. When these columns are populated on an ingest row, they represent a parsed footnote disclosure that scopes to specific trims, model families, or body styles. Build consumes them as follows:

1. If the ingest row's `footnote_scope_model_family` matches the variant being built and the fragment names an RPO (detectable as a parenthesized or standalone RPO token), that RPO goes into `auto_added_rpos` for the build row.
2. If the fragment names an RPO but the scope doesn't match (e.g. the variant is Stingray but the fragment scopes to Z06/ZR1/ZR1X), ignore that fragment — it doesn't apply to this variant.
3. If the fragment can be parsed for scope but not for an RPO, copy the full `footnote_scope_fragment` into `notes` for human review. Do not guess at RPOs.
4. When all four `footnote_scope_*` columns are blank on an ingest row, fall back to reading the full `compat_note_text` (if present) into `notes` for human review. This is the "disclosure exists but ingest couldn't parse it" case.

Ingest-parsed footnote scope is authoritative when present. Hand-authored `requires_in_variant` / `excludes_in_variant` / `auto_added_rpos` values fill the gaps ingest couldn't reach — typically variant-specific rules that aren't in GM's disclosure prose at all (e.g. allocation rules, dealer policies). When both sources apply to the same row, concatenate: pipe-delimited RPOs from both ingest-parsed scope and hand-authored rules.

**TU7 two-tone and similar additive stylings.** Some styling options are separately orderable RPOs that apply on top of an already-selected base interior. These stay in `<Variant> Options`, not in the Interior sheet. TU7 is the canonical example: it requires AH2 seats and is only available with a specific set of base interior RPOs that depends on trim:

- On 2LT: TU7 is available with interiors `HUK`, `HU6` (Sky Cool Gray), `HUL`, `HU7` (Adrenaline Red), `HTN`, `HTQ` (Natural).
- On 3LT: TU7 is available with interiors `HU1`, `HU9` (Sky Cool Gray), `HU2`, `HUA` (Adrenaline Red), `HUE`, `HTG` (Natural), `HMO`, `HVV` (Jet Black / Sky Cool Gray), `HU0`, `HXO` (Jet Black / Adrenaline Red).

Record TU7's row in `<Variant> Options` with `requires = AH2` and its trim-specific compatible interiors in the `available_with_interior_rpos` field (pipe-delimited), scoped by trim. If a single options-sheet row can't carry the trim split cleanly, use two rows (one per trim) or split the compatibility list with trim tags — but do not attempt to encode TU7 combinations as expanded rows in the Interior sheet. The Interior sheet enumerates base interiors; TU7 is additive.

The same pattern applies to any other GM styling RPO that is described in option-detail notes with a "Requires X seats. Available with [list of interiors]" structure.

**Custom stitching (36S, 37S, 38S)** follows the same pattern: additive RPO in `<Variant> Options` with `requires` pointing at the compatible base interior RPOs. Do not expand stitching variants into the Interior sheet.

### 3. `<Variant> Exterior` — exterior paints and color-combination availability

Two kinds of information live here:

**3a. The exterior paint list.** One row per exterior paint RPO available on this variant. Identity comes from Option Catalog (Color and Trim is the authoritative source there per ingest). Per-variant price and availability come from Availability Long filtered to the variant's model family.

| Column | Meaning |
|---|---|
| `exterior_color_rpo` | From Option Catalog |
| `exterior_color_name` | From Option Catalog |
| `touch_up_paint_number` | From Option Catalog notes |
| `price_coupe` / `price_convertible` | Paint price per body style. Blank = not available on that body. |
| `body_restriction` | `coupe_only`, `convertible_only`, or blank (available on both) |
| `requires_in_variant` | Pipe-delimited RPOs this paint forces on this variant (e.g. some colors only with specific packages) |
| `excludes_in_variant` | Pipe-delimited RPOs this paint cannot coexist with on this variant |
| `notes` | |

**3b. The exterior/interior combination grid.** Consumes ingest's `Color Combination Availability` filtered to interior color RPOs that appear in this variant's `<Variant> Interior` sheet. One row per (exterior_color_rpo × interior_color_rpo) pair present in the ingest layer.

| Column | Meaning |
|---|---|
| `pair_id` | From ingest |
| `exterior_color_rpo` | |
| `interior_color_rpo` | |
| `availability_label` | Copied from ingest: `Published Available`, `Requires D30 Override`, `Requires R6X`, `Requires R6X and D30 (one charge collapses per disclosure)` |
| `auto_added_rpos` | The option codes the combination forces onto the build: `D30`, `R6X`, or `D30\|R6X` (pipe-delimited). For the `Requires R6X and D30 (one charge collapses)` case, both codes are recorded — the pricing collapse is resolved at form-total time, not by dropping a code from the build. |
| `notes` | |

This section only includes combinations whose interior_color_rpo is present in this variant's `<Variant> Interior` sheet — don't carry over pairs for interiors the variant can't select.

**Exterior → interior conflict shortcut.** If the grid in 3b is dense (most pairs `Published Available`), the form can default-allow and flag the exceptions. If conflicts are significant (Z06, ZR1 with many packages that gate colors), the grid is worth keeping fully enumerated.

**Dropped from the old schema.** The previous `<Variant> Exterior` schema had single-row `incompatible_interior_colors` / `incompatible_packages` / `required_packages` columns that tried to compact conflicts per exterior color. That representation loses the R6X/D30 distinction and the pricing-collapse rule. The two-section structure above replaces it.

### 4. `<Variant> Standard Equipment`

The list of standard equipment that comes with this variant/trim, for presentation. One row per item. Columns: section, rpo_code, name, description, trim_1_included (bool), trim_2_included, trim_3_included.

This is content, not logic — the form shows it, it doesn't filter on it.

## What `<Variant>` means

One set of the four sheets above per model family. Body style is a column within the sheets, not a separate set. So:

- `Stingray Options`, `Stingray Interior`, `Stingray Exterior`, `Stingray Standard Equipment`
- `Grand Sport Options`, `Grand Sport Interior`, `Grand Sport Exterior`, `Grand Sport Standard Equipment`
- `Z06 Options`, `Z06 Interior`, `Z06 Exterior`, `Z06 Standard Equipment`
- etc.

Shared across all variants (from the corvette-ingest layer):
- `Option Catalog` — identity only
- `Variant Catalog` — one row per (model × body × trim) combo, with model_code and base pricing
- `Availability Long`, `Pricing Long`, `Interior Trim Combos`, `Color Combination Availability` — ingest's canonical intermediate sheets that build reads from. Not edited by build.

## How to work

### Step 1: Confirm scope

Ask Sean which variant and which of the four sheets is in scope for this session. Don't try to do all four sheets for a variant in one pass — they have different source material and different gotchas.

### Step 2: Identify sources

The corvette-ingest skill produces the canonical intermediate layer. Build always consults ingest outputs first; legacy Clean sheets are migration material only.

Sources per sheet being built:

- **Options sheet**: primary sources are `Availability Long` filtered to this model family (availability per variant) and `Pricing Long` (per-option, per-context pricing). Old `STINGRAY` tab from 26MY_Pre is a strong reference for column layout and compatibility-note phrasing but is prior-year and non-authoritative.
- **Interior sheet**: primary source is `Interior Trim Combos` from ingest, filtered to trims in this variant (e.g. for Stingray: `1LT`, `2LT`, `3LT`). Each ingest row becomes one build row. Variant-specific layered requirements (like "AE4 rows on Stingray require N26") are added in `requires_in_variant` using Sean's configuration knowledge. `Pricing Long` supplies any interior price offsets.
- **Exterior sheet**: primary sources are Option Catalog (for paint identity — Color and Trim was authoritative in ingest), Availability Long filtered to this model family (for per-variant paint availability and pricing), and `Color Combination Availability` from ingest (for the exterior/interior grid with D30/R6X semantics).
- **Standard Equipment sheet**: primary source is `Availability Long` filtered to this variant with `availability_label = Standard Equipment`. The raw Standard Equipment matrix sheets from the GM export are ingest's inputs, not build's.

### Step 3: Migration from legacy Clean sheets

If Sean has `Option Rules Clean`, `Option Price Scopes Clean`, `Choice Groups Clean`, or `Choice Group Members Clean` from a prior pass, treat those as migration sources:

- **Option Price Scopes Clean** → populate the per-trim price columns in `<Variant> Options`. Each price scope row tells you the price for (option × trim). Move it, then mark that row as migrated.
- **Option Rules Clean** `requires` rows → `requires` column in `<Variant> Options`, scoped to the variants named in `scope_value`. If a rule's scope is `variant_set` spanning multiple variants, duplicate the rule into each variant's sheet. Do not preserve the abstract scope string.
- **Choice Groups Clean** + **Members Clean** → do not create a dedicated choice group sheet. Seat choice groups become the seat dimension in `<Variant> Interior`. Exterior color groups become `<Variant> Exterior`. The "pick one" behavior is enforced by the form reading the distinct values of a column, not by a group table.
- Any Clean sheet that has been fully migrated gets renamed with an `_archived` suffix. Do not delete.

### Step 4: Populate and validate

Write the sheet. Then run quick sanity checks:

- Every RPO referenced has a row in Option Catalog
- Every price column value is a number, blank, or the `std` marker — nothing else
- Every `requires` / `excludes` entry names an RPO that exists in Option Catalog
- In Interior sheet: every `combo_id` is unique
- In Interior sheet: if a seat_rpo has `requires` (like AE4 requires N26), either N26 is in `auto_added_rpos` for every row using that seat, or the form is expected to handle it at selection time — but one of these must be true and documented

### Step 5: Report

Tell Sean what was populated, what was migrated, what was skipped, and what needs his judgment. A row count per section is useful. Flag anything that looked ambiguous.

## Two-phase execution

For any non-trivial build task:

**Phase 1 — Plan.** Write a plan describing:
- Which sheet (exactly one)
- Which sources will be consulted
- Expected row count and a sample of 3-5 rows
- Any decisions needed from Sean (new RPOs discovered, conflicting prices between sources, ambiguous compatibility notes)

Stop and wait for approval.

**Phase 2 — Build.** Only after Phase 1 approval. Produce the sheet, validate, report actual row counts and any deviations.

## Validation gates

Before handing a sheet back as done:

- Run in Python: load the workbook, check every `requires` / `excludes` / `requires_in_variant` / `excludes_in_variant` / `auto_added_rpos` / `available_with_interior_rpos` RPO resolves in Option Catalog, check price columns are numeric-or-blank-or-std, check Interior `combo_id` uniqueness.
- For the Interior sheet: check every `interior_color_rpo` appears in ingest's `Interior Trim Combos` for at least one trim scope that matches this variant's trims. No phantom RPOs.
- For the Exterior sheet section 3b: check every pair's `availability_label` and `auto_added_rpos` are consistent. `Published Available` → blank auto_added. `Requires D30 Override` → `D30`. `Requires R6X` → `R6X`. `Requires R6X and D30` → `R6X|D30`. Any mismatch is an error.
- Spot-check three rows by reading them back as plain English: "On Stingray 2LT, AE4 seats cost $1,995, require N26 suede steering wheel (auto-added, +$695), and are available in Jet Black Performance Textile only." If that sentence is true per Sean's knowledge, the row is right.

## What this skill does NOT do

- Does not re-ingest raw GM exports. That is corvette-ingest.
- Does not build a unified cross-variant rule table. Duplication across variants is expected.
- Does not build empty "derived" placeholder sheets like Variant Option Matrix, Price Resolver, Package Composition, or Variant Choice Availability. If those sheets exist from prior work, treat them as migration sources or archive them. The per-variant sheets replace them.
- Does not extract rules from compatibility notes automatically. If Sean wants a rule, Sean writes it into the `requires` / `excludes` / `auto_added_rpos` column explicitly.
- Does not modify another variant's sheet as a side effect. One session, one variant, one sheet.

## Failure modes to avoid

- Building an abstract cross-variant "rules" sheet to DRY up duplication. Duplication is the point.
- Re-decomposing interiors into separate seat / color / suede / stitching / two-tone RPO columns when ingest already treats the full interior as a single RPO. If GM's Color and Trim publishes `HXO3` as a complete (AH2/AE4 + Napa with sueded microfiber + Adrenaline Red interior / Jet Black seats + asymmetric) interior, it's one row with one RPO — not five columns of modifiers to stack at form time.
- Dropping the D30 or R6X auto-add on exterior/interior grid rows. Those codes must land on the order even when the form-displayed price shows only one of them due to the disclosure collapse. Ingest recorded both; build must preserve both.
- Skipping the enumeration in Interior because "it's too many rows". A variant's Interior sheet typically sits around 30-60 rows on Stingray and scales from there on variants with more 3LT/3LZ coverage. That is not too many.
- Treating legacy Clean sheets as source of truth instead of migration sources. They were the prior architecture; the ingest outputs and per-variant sheets supersede them.
- Extending a sheet's schema without asking Sean. Column additions propagate across variants and compound over time.
- Producing the sheet in Phase 2 without Phase 1 approval.
