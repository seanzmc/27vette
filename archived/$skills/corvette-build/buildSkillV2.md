---
name: corvette-build-v2
description: Build and maintain deterministic per-variant Corvette order-flow sheets from the V2 ingest outputs. Use this replacement spec when Sean wants the build layer generated from explicit ingest contracts for options, interiors, exterior paint, equipment groups, auto-added RPOs, runtime UI fields, and context-sensitive pricing.
---

# Corvette Build V2

This skill is self-contained for single-file import environments such as the Excel ChatGPT add-in. It does not require access to any separate contract file at runtime.

It assumes the V2 ingest outputs exist and are clean enough to pass the build gate.

## Embedded shared contract

### Canonical substrate

The canonical working substrate is a single Excel workbook (`.xlsx`) per model year.

- Raw GM export sheets and generated output sheets live in the same workbook.
- Raw sheets are read-only.
- Generated sheets may be replaced on rerun.

### Run boundary

One ingest/build run operates on one workbook for one model year.

- The workbook is the isolation boundary.
- Generated IDs are namespaced by `dataset_id`.
- Cross-year joins are not allowed inside a single run.

### Model year and dataset ID

Every generated sheet carries these shared fields where relevant:

- `model_year` as a four-digit integer, e.g. `2027`
- `dataset_id` as `my<yy>`, e.g. `my27`

### Canonical model families

The supported model-family labels are:

- `Stingray`
- `Grand Sport`
- `Grand Sport X`
- `Z06`
- `ZR1`
- `ZR1X`

Do not substitute `E-Ray` for any of the six labels above.

### Scope conventions

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

### Generated sheet replace policy

The default rerun mode is full rebuild of generated sheets.

- Raw sheets are never edited or deleted.
- Generated sheets are replaced in place by name.
- Partial patch mode is not part of the default contract.

### Shared input set

This build spec consumes:

1. `Option Catalog`
2. `Availability Long`
3. `Pricing Long`
4. `Base Prices`
5. `Interior Trim Combos`
6. `Color Combination Availability`
7. `Equipment Group Membership`
8. `Ingest Exceptions`

Color and Trim derived input rules:

- `Interior Trim Combos` does not carry `model_family_scope` or `body_scope`
- `Color Combination Availability` does not carry `model_family_scope` or `body_scope`

Interior and exterior colors are treated as not model-family-specific and not body-style-specific in this contract. Trim-specific behavior may still be carried where needed.

### Build gate

Before doing any variant work:

- read `Ingest Exceptions`
- stop on any blocking exception with `blocking_scope = global`
- stop on any blocking exception that affects the target model family
- stop on any blocking exception that affects one of the target variants

Warnings do not stop the build, but they must be reported back to Sean.

### Validation floor

Use the later operational validation section in this file as the authoritative validation procedure, and ensure its sample coverage includes the standard seat path, package-dependent pricing, D30-only override, R6X plus D30 collapse, and an additive interior option gated by base interior.

## Core model

Build still does one job: turn source-preserving ingest rows into a deterministic order-flow layer.

The V2 difference is that row generation is now explicit:

- same source facts must produce the same build rows every time
- scope may collapse only when behavior stays identical
- rows must split when behavior changes in any load-bearing way
- blocking ingest exceptions stop the build before any variant sheet is written

## Canonical outputs

Each model family gets four sheets:

1. `<Variant> Options`
2. `<Variant> Interior`
3. `<Variant> Exterior`
4. `<Variant> Standard Equipment`

`Base Prices` stays shared and is not duplicated.

## Runtime order

The runtime still reads in this order:

1. body style
2. trim
3. exterior paint
4. exterior appearance
5. wheels
6. brake calipers
7. packages and major performance options
8. aero, exhaust, stripes, accessories
9. interior setup
10. delivery
11. summary and pricing

Interior setup still reads:

`seat -> base interior -> interior_style -> seat_belt -> interior_trim`

## Deterministic build algorithm

### Step 1: Establish variant scope

Build the target family only after loading its concrete variants from `Base Prices`.

This gives the canonical set of:

- `variant_id`
- `body_style`
- `trim`
- `model_code`

No other sheet is allowed to invent extra variants.

### Step 2: Build `<Variant> Interior`

Filter `Interior Trim Combos` to rows whose `trim` exists in target-family `Base Prices`.

`Interior Trim Combos` does not carry `model_family_scope` or `body_scope` in V2. Interior colors are treated as not model-family-specific and not body-style-specific.

Required columns:

| Column | Meaning |
|---|---|
| `combo_id` | From ingest |
| `trim` | Single trim |
| `seat_code` | Single seat code |
| `seat_type_name` | |
| `seat_trim_material` | |
| `interior_color_rpo` | Base interior RPO |
| `interior_color_name` | |
| `source_sheet_origin` | `recommended` or `custom_r6x` |
| `auto_added_rpos` | Blank or `R6X` unless explicit companion charge exists |
| `price_offset` | Derived from `Pricing Long` on the interior RPO |
| `source_note` | Verbatim note text |
| `notes` | Build-only caveats |

Rules:

- keep one row per legal base interior state
- do not decompose it into modifiers
- if the same `interior_color_rpo` exists on multiple trims with different offsets or notes, keep separate rows

### Step 3: Build `<Variant> Exterior` section 3b first

Filter `Color Combination Availability` to rows whose `interior_color_rpo` exists in `<Variant> Interior`.

`Color Combination Availability` does not carry `model_family_scope` or `body_scope` in V2. Exterior/interior color relationships are treated as not model-family-specific and not body-style-specific.

Required columns:

| Column | Meaning |
|---|---|
| `pair_id` | From ingest |
| `trim_scope` | Pipe-delimited trim scope |
| `exterior_color_rpo` | Paint code |
| `interior_color_rpo` | Base interior code |
| `availability_label` | Canonical pair label |
| `auto_added_rpos` | Blank, `D30`, `R6X`, or `D30|R6X` |
| `source_note` | Disclosure text |
| `notes` | Build-only caveats |

Collapse rule:

- rows may merge `trim_scope` only when `availability_label`, `auto_added_rpos`, and `source_note` stay identical

### Step 4: Build `<Variant> Exterior` section 3a

Build paint rows by merging three sources:

1. `Option Catalog` for paint identity
2. `Availability Long` for target-family availability by body/trim
3. `Pricing Long` for paint price contexts

Required columns:

| Column | Meaning |
|---|---|
| `row_id` | Stable row key |
| `exterior_color_rpo` | Paint code |
| `exterior_color_name` | |
| `body_scope` | Pipe-delimited allowed bodies |
| `trim_scope` | Pipe-delimited allowed trims |
| `requires_all` | Explicit prerequisite RPOs only |
| `excludes` | Explicit blocked RPOs only |
| `price` | Numeric paint price for this row scope |
| `source_note` | Verbatim note text |
| `notes` | Build-only caveats |

Row split rule:

- split a paint row whenever body scope, trim scope, prerequisites, exclusions, or price differ

### Step 5: Build `<Variant> Options`

Candidate RPO universe:

- all `Availability Long` rows for the target family
- all `Pricing Long` rows for target-family RPOs
- all `Equipment Group Membership` rows in target-family scope

Exclude from `<Variant> Options`:

- exterior paint RPOs
- base interior color RPOs
- pure pair-grid rows

Keep in `<Variant> Options`:

- selectable seats, including standard/default seats
- packages
- wheels
- calipers
- aero
- exhaust
- stripes
- accessories and LPOs
- additive interior styling options
- delivery options
- auto-added charge/helper codes such as `D30`, `R6X`, or `N26`

### `<Variant> Options` schema

| Column | Meaning |
|---|---|
| `row_id` | Stable row key |
| `step_key` | Runtime bucket |
| `group_key` | Mutual-choice group |
| `choice_mode` | `single` or `multi` |
| `display_order` | Stable UI order |
| `ui_mode` | `selectable`, `auto_only`, or `summary_only` |
| `rpo_code` | |
| `name` | |
| `description` | |
| `section` | Human-facing section |
| `body_scope` | Pipe-delimited allowed bodies |
| `trim_scope` | Pipe-delimited allowed trims |
| `requires_all` | Pipe-delimited prerequisites |
| `requires_any` | Pipe-delimited OR prerequisites |
| `excludes` | Pipe-delimited conflicts |
| `auto_added_rpos` | Pipe-delimited auto-adds |
| `available_with_interior_rpos` | Pipe-delimited base-interior compatibility |
| `available_with_exterior_rpos` | Pipe-delimited exterior-paint compatibility |
| `price_<trim>` | One column per actual trim on the family |
| `std_<trim>` | Standard flags by trim |
| `source_note` | Verbatim combined note text |
| `notes` | Build-only caveats |

## Deterministic row generation for `<Variant> Options`

### Candidate grouping

Process one `rpo_code` at a time.

For each `rpo_code`:

1. collect all target-family `Availability Long` rows
2. collect all target-family `Pricing Long` rows
3. collect any `Equipment Group Membership` rows where the RPO is either a group root or a member
4. collect each row's `availability_label` and any `availability_context_labels`
5. collect all explicit note texts from the ingest outputs

### Rule promotion sweep

Promote only explicit logic.

Pattern examples:

- `Requires Z51` -> `requires_all = Z51`
- `Requires AH2 or AE4` -> `requires_any = AH2|AE4`
- `Not available with FE4` -> `excludes = FE4`
- `Available with HUK, HU6, HUL` -> `available_with_interior_rpos = HUK|HU6|HUL`
- `Available with GBA only` -> `available_with_exterior_rpos = GBA`
- `Includes N26` -> `auto_added_rpos = N26`
- `No charge with Z51` -> special pricing context split

Note-source order:

1. `Availability Long.compat_note_text`
2. `Pricing Long.context_note_raw`
3. `Option Catalog.footnote_texts`
4. `Option Catalog.notes`
5. `Equipment Group Membership.notes`

### Step-key assignment

Assign `step_key` by this precedence:

1. `package` for package RPOs and selectable equipment groups
2. `seat` for all selectable seat rows, including default seats
3. `wheel` for wheel rows
4. `caliper` for caliper rows
5. `stripe` for stripe rows
6. `aero` for aero rows
7. `exhaust` for exhaust rows
8. `seat_belt` for seat-belt rows
9. `interior_trim` for stealth trim, carbon-fiber trim, PDR, and similar interior-adjacent trim rows
10. `interior_style` for additive interior styling rows such as suede inserts or stitching packs
11. `delivery` for delivery/program rows
12. `accessory` for general accessories and LPO rows
13. `exterior_appearance` for exterior items not covered above

### Group-key assignment

Use these defaults:

- all seat choices -> `seat_choice`
- all wheels -> `wheel_choice`
- all calipers -> `caliper_choice`
- all seat belts -> `seat_belt_choice`
- mutually exclusive package families -> one shared family key
- multi-select rows -> `grp_<rpo_code>` self-group

### Choice-mode assignment

Defaults:

- `single` for seat, wheel, caliper, seat_belt, and exclusive package families
- `multi` for accessory, delivery, additive interior styling, and rows that can coexist

If source text explicitly says choices are mutually exclusive, use `single` even if the default says `multi`.

### Display-order assignment

Use this deterministic order:

1. runtime step order
2. original GM source order within the primary source sheet
3. selectable rows before auto-only rows
4. alphabetical by `name` as final tie-break

### UI-mode assignment

- `selectable`: user directly chooses the row
- `auto_only`: row may never be user-clicked, but may appear in summary and pricing after another row or pair adds it
- `summary_only`: informational row that appears in summary output only

`auto_only` rows are hidden during selection and visible at summary/pricing time.

## Collapse and split rules

This is the core V2 determinism rule.

### A row may merge scope only when all non-scope behavior fields are identical:

- `step_key`
- `group_key`
- `choice_mode`
- `ui_mode`
- `requires_all`
- `requires_any`
- `excludes`
- `auto_added_rpos`
- `available_with_interior_rpos`
- `available_with_exterior_rpos`
- `source_note` after normalization
- `section`

### A row must split when any of these differ:

- base availability meaning such as `Available` versus `ADI Available`
- price behavior for any trim
- standardness behavior for any trim
- prerequisite/conflict fields
- auto-add behavior
- interior/exterior compatibility fields
- step/group/choice/ui fields

If the build runtime does not expose `ADI Available` as its own selectable status, preserve that distinction in `source_note` or `notes`. Do not silently flatten it into ordinary `Available`.

### `std_<trim>` and `price_<trim>` interaction

One row may hold both standard and priced behavior across different trims if every other behavior field stays identical.

Example:

- `std_1LT = true`
- `price_2LT = 1495`
- `price_3LT = 1495`

This stays one row unless some other field differs.

## Pricing population

### For `<Variant> Options`

Populate `price_<trim>` by matching each candidate row to `Pricing Long` records whose:

- model scope matches the target family
- body scope matches the row body scope
- trim scope matches the target trim
- prerequisites/conflicts match the row rule fields

If the same trim has two different prices under different prerequisites, split the row.

### For `<Variant> Interior`

`price_offset` comes from the interior RPO's matched price rows after trim filtering.

### For `<Variant> Exterior` section 3a

Use row-specific `price`, not per-trim columns.

If body or trim pricing differs, split rows by scope until one row has one resolved price.

## Standard-seat rule

Seat rows are mandatory for every selectable seat state, including the default seat on each trim.

- if a trim includes only one seat by default, that seat still gets a row
- if a seat upgrade exists, both the default seat and the upgrade seat must appear

The runtime may not derive a seat choice implicitly from the interior sheet alone.

## Equipment Groups in build

V2 makes equipment groups explicit.

Rules:

- selectable package/group RPOs become `step_key = package` rows
- trim-implied groups do not become selectable rows unless the source makes them separately orderable
- when a member RPO is only available through a group, add an `auto_only` row scoped with `requires_all = <group_rpo>`
- when a member is standard because of a trim-implied group, reflect that in the member row's `std_<trim>` fields
- treat `availability_context_labels = Included in Equipment Group` as corroborating evidence that the feature may be satisfied by a group and should not be surfaced as its own standalone selectable row unless separate ingest evidence says it is independently selectable
- treat `availability_context_labels = Included in Equipment Group but upgradeable` as corroborating evidence that the feature has a group-included baseline plus an allowed upgrade path; only surface the upgrade as a separate selectable row when ingest provides a distinct upgrade RPO, price context, or explicit note
- treat `availability_context_labels = Indicates availability of feature on multiple models` as scope/reference metadata only, not as a prerequisite, exclusion, or auto-add rule

## D30 and R6X pricing rule

When a build state activates both `D30` and `R6X` from a pair row labeled `Requires R6X and D30 (one charge collapses per disclosure)`:

- keep both codes on the build
- resolve both matched price rows
- charge only the higher priced applicable row unless a source note explicitly assigns precedence differently
- suppress the lower-priced companion row from the net total

This rule applies only to the collapsed-pricing pair state. It does not remove either code from the build state.

## `<Variant> Standard Equipment`

Populate from:

- `Availability Long` rows marked `Standard Equipment`
- `Equipment Group Membership` rows that make a feature standard for a trim

Suggested columns:

- `section`
- `rpo_code`
- `name`
- `description`
- one included flag per actual trim
- `notes`

## Validation gates

Before handing back a variant build:

- no blocking ingest exception may remain in scope
- every referenced RPO resolves in `Option Catalog`
- every `row_id` and `combo_id` is unique
- every `interior_color_rpo` used in pair rows exists in `<Variant> Interior`
- every `auto_added_rpos` reference resolves
- every price cell is numeric, blank, or `0`
- the validation set covers the five required shared-contract scenarios

## Two-phase execution

### Phase 1: Plan

Report:

- target family
- exact ingest inputs used
- expected row counts by output sheet
- representative row-generation examples
- representative price-resolution examples
- any warning exceptions still in scope

Stop for approval.

### Phase 2: Build

After approval:

- replace the generated variant sheets in place
- validate all four outputs
- report actual row counts
- report unresolved warnings

## Failure modes V2 explicitly avoids

- ad hoc row splitting
- missing default seat rows
- implicit paint-source fusion
- undefined `step_key` or `display_order`
- build-through on blocking ingest defects
- undocumented D30/R6X charge collapse
- package logic that depends on memory instead of `Equipment Group Membership`
