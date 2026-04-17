# Workbook roadmap

Here is the clean structure I would build toward.

## Layer 1: Raw source sheets

These are preserved quarry stones. Do not build long-term logic directly in them.

### Existing raw/source sheets

- Standard Equipment 1
- Standard Equipment 2
- Standard Equipment 3
- Standard Equipment 4
- Equipment Groups 1
- Equipment Groups 2
- Equipment Groups 3
- Equipment Groups 4
- Interior 1
- Interior 2
- Interior 3
- Interior 4
- Exterior 1
- Exterior 2
- Exterior 3
- Exterior 4
- Mechanical 1
- Mechanical 2
- Mechanical 3
- Mechanical 4
- Wheels 1
- Wheels 2
- Wheels 3
- Wheels 4
- Color and Trim 1
- Color and Trim 2
- All 1
- All 2
- All 3
- All 4
- All
- Pricing
- Dimensions
- Specs

### Role

These tabs are reference input only.

### Relationship

They feed staging sheets and canonical sheets, but nothing downstream should depend on them directly once normalized.

---

## Layer 2: Staging / transformation sheets

These are transitional cleanup tables. Some already exist and are useful.

### Existing staging sheets

- Options Master
- Options Long
- Color Trim Notes
- Color Trim Seats
- Color Trim Matrix
- Color Trim Combos
- Option Pricing

### Role

These are where messy source material gets pulled apart into useful pieces.

### Relationship

They feed canonical sheets. They are not the final truth once data has been normalized.

---

## Layer 3: Canonical normalized sheets

This is the real backbone.

---

### 1) Variant Catalog

#### Purpose

Defines every orderable vehicle context.

#### Relationship

Parent table for variant-based pricing, availability, and rules.

#### Keep / use headers

- variant_id
- model_family
- body_style
- trim
- trim_family
- variant_label
- convertible_flag
- roof_code
- drivetrain_code
- model_code
- list_price
- msrp
- dfc
- sort_model
- sort_body
- sort_trim
- active_flag
- notes

#### Notes

You already have the important bones here. I would mostly refine and extend, not rebuild.

---

### 2) Option Catalog

#### Purpose

One canonical row per option or selectable value.

#### Relationship

Parent table for rules, pricing, choice membership, package membership, and variant availability.

#### Recommended headers

- option_id
- rpo_code
- option_kind
- primary_source
- definition_status
- form_selectable_flag
- reference_only_flag
- primary_name
- primary_description
- primary_detail
- primary_section
- alternate_labels
- standard_flag
- available_flag
- package_flag
- package_only_flag
- seat_flag
- interior_flag
- exterior_flag
- wheel_flag
- aero_flag
- needs_review_flag
- source_sheet
- source_row
- notes

#### Notes

This sheet should define identity, not per-variant behavior.

---

### 3) Option Rules

#### Purpose

Stores structured logic between options and values.

#### Relationship

Links Option Catalog to itself, and sometimes to variant or choice logic.

#### Recommended headers

- rule_id
- source_option_id
- source_rpo_code
- source_catalog_row
- target_option_id
- target_rpo_code
- target_known_flag
- target_option_kind
- rule_type
- rule_subtypes
- enforcement_level
- source_fields
- source_note_refs
- source_available_variant_ids
- scope_variant_ids
- scope_models
- scope_bodies
- scope_trims
- logic_expression
- human_rule_text
- status
- review_flag
- notes

#### Notes

This is the rule engine. Keep it clean and structured.

---

### 4) Option Price Scopes

#### Purpose

Stores how option pricing changes by context.

#### Relationship

Child of Option Catalog. Resolves prices against Variant Catalog.

#### Recommended headers

- price_scope_id
- option_id
- rpo_code
- price_mode
- list_price
- scope_variant_ids
- scope_models
- scope_bodies
- scope_trims
- condition_rpos_all
- condition_rpos_any
- condition_note
- action_include_rpos
- included_with_rpos
- pricing_description
- pricing_note
- source_sheet
- source_row
- review_flag
- notes

#### Notes

This becomes the real pricing engine. Option Pricing can remain the staging quarry.

---

### 5) Choice Groups

#### Purpose

Defines mutually exclusive sets.

#### Relationship

Parent to Choice Group Members. Used by display sheets and logic sheets.

#### Recommended headers

- choice_group_id
- group_name
- selection_mode
- scope_models
- scope_bodies
- scope_trims
- scope_variant_ids
- context_rpos_all
- context_rpos_any
- member_count
- display_section
- display_order
- status
- notes

#### Notes

One thing already waving a little red flag: your current sheet appears to have a “Body Selection” row without a proper id. Fix that early before it breeds.

---

### 6) Choice Group Members

#### Purpose

Lists the members of each mutually exclusive set.

#### Relationship

Bridge table between Choice Groups and Option Catalog.

#### Recommended headers

- choice_group_id
- member_option_id
- member_rpo_code
- member_label
- member_option_kind
- source_basis
- display_order
- default_flag
- scope_variant_ids
- scope_models
- scope_bodies
- scope_trims
- active_flag
- notes

#### Notes

This should eventually carry more scoped availability info than it does now.

---

### 7) Order Schema Map

#### Purpose

Documents the architecture and tells future-you what each table is for.

#### Relationship

Metadata sheet for humans and AI helpers.

#### Recommended headers

- build_order
- target_table
- primary_key
- purpose
- current_source
- status
- next_processing
- downstream_dependents
- owner_decision
- notes

#### Notes

This is your map legend. Keep it current.

---

## Layer 4: New helper sheets I recommend adding

These are the missing engine-room sheets that will make the workbook much easier to use.

---

### 8) Variant Option Matrix

#### Purpose

One row per variant_id + option_id.

This is the single most important helper sheet to add.

#### Relationship

Built from Variant Catalog + Option Catalog + rules + scoped pricing.

#### Recommended headers

- variant_option_id
- variant_id
- option_id
- rpo_code
- model_family
- body_style
- trim
- primary_section
- option_kind
- primary_name
- display_label
- standard_flag
- available_flag
- orderable_flag
- package_only_flag
- included_flag
- base_included_flag
- choice_group_id
- resolved_price
- price_mode
- requires_count
- excludes_count
- includes_count
- conditional_flag
- display_status
- sort_section
- sort_order
- review_flag
- notes

#### Why it matters

This is the sheet that turns the workbook from “interesting archive” into “usable system.”

---

### 9) Package Composition

#### Purpose

Explicitly shows package-to-component relationships.

#### Relationship

Usually derived from rules and package options in Option Catalog.

#### Recommended headers

- package_option_id
- package_rpo_code
- package_name
- member_option_id
- member_rpo_code
- member_name
- relationship_type
- scope_variant_ids
- source_rule_id
- notes

#### Why it matters

Packages are one of the places spreadsheet logic goes feral. This tames it.

---

### 10) Variant Choice Availability

#### Purpose

Shows which members of a choice group are available in a specific variant.

#### Relationship

Derived from Choice Groups, Choice Group Members, Variant Catalog, and rules.

#### Recommended headers

- variant_choice_id
- variant_id
- choice_group_id
- member_option_id
- member_rpo_code
- available_flag
- default_flag
- blocked_by_rules
- blocked_by_trim
- blocked_by_body
- blocked_by_model
- blocked_by_context
- resolved_label
- display_order
- notes

#### Why it matters

This is gold for seats, interior colors, wheels, and paint.

---

### 11) Rule Summary

#### Purpose

Human-readable flattened view of option logic.

#### Relationship

Derived from Option Rules.

#### Recommended headers

- option_id
- rpo_code
- requires_rpos
- excludes_rpos
- includes_rpos
- recommended_with_rpos
- package_contains_rpos
- scoped_variants
- rule_summary
- review_flag

#### Why it matters

It gives you a readable sanity-check layer.

---

### 12) Price Resolver

#### Purpose

Shows the resolved final price for every option in every variant context.

#### Relationship

Derived from Variant Catalog + Option Price Scopes + packages/inclusion logic.

#### Recommended headers

- variant_id
- option_id
- rpo_code
- price_scope_id
- price_mode
- raw_list_price
- resolved_price
- included_with_rpos
- conditional_rpos
- source_reason
- review_flag
- notes

#### Why it matters

This is where pricing ambiguity gets dragged into the light.

---

### 13) Audit Exceptions

#### Purpose

Catch contradictions, missing mappings, orphan data, and weirdness.

#### Relationship

Fed by checks across the whole workbook.

#### Recommended headers

- audit_id
- issue_type
- severity
- sheet_name
- key_value
- related_key
- description
- suggested_fix
- status
- owner
- notes

#### Example issue types

- missing_option_id
- duplicate_rpo
- conflicting_price_scope
- orphan_choice_member
- rule_target_missing
- missing_choice_group_id
- ambiguous_package_logic
- variant_scope_missing

#### Why it matters

This becomes your bug list instead of hiding bugs in plain sight.

---

## Layer 5: Presentation sheets

These are the polished guide tabs people actually use.

I would not build these until the helper sheets above exist.

---

### 14) Guide sheets by variant family

You can decide whether these are:

- one per exact variant, or
- one per model family with trim/body filters

#### Option A: One sheet per family

- Stingray Guide
- Grand Sport Guide
- Z06 Guide
- ZR1 Guide
- ZR1X Guide

#### Option B: One sheet per exact variant

- Stingray Coupe 1LT Guide
- Stingray Coupe 2LT Guide
- Stingray Convertible 1LT Guide
- etc.

For manageability, I would start with family-level guide sheets plus filter controls.

#### Recommended headers for display sheets

- section
- subsection
- display_order
- rpo_code
- option_name
- description
- status
- price
- requires
- excludes
- package_info
- notes

#### Status values

Keep these standardized:

- Standard
- Included
- Optional
- Package Only
- Conditional
- Not Available
- Reference Only

---

## Relationship map

Here is the workbook ecosystem in plain English:

### Raw/source feeds staging

- Pricing → Option Pricing
- Options Master / Options Long → Option Catalog and Option Rules
- Color Trim Seats / Matrix / Combos → Choice Groups, Choice Group Members, Option Rules
- Raw category tabs → fill gaps, validate labels, backstop missing sections

### Staging feeds canonical

- Option Pricing → Option Price Scopes
- Options Master / Options Long → Option Catalog
- Color Trim tabs → Choice Groups / Members / Rules

### Canonical feeds helper logic

Variant Catalog + Option Catalog + Option Rules + Option Price Scopes + Choice Groups / Members
build:

- Variant Option Matrix
- Variant Choice Availability
- Package Composition
- Rule Summary
- Price Resolver
- Audit Exceptions

### Helper logic feeds presentation

- Guide sheets
- future configurator exports
- cleaner order forms
- filtered customer-facing sheets

---

## My recommended build order

This is the path I would follow so you do not drown in your own tabs.

### Phase 1

Lock the architecture.

- Keep raw tabs
- mark staging tabs
- commit canonical tabs
- stop inventing new semi-random middle sheets

### Phase 2

Refine the canonical sheets.

- clean ids
- fix missing choice group ids
- confirm option kinds
- confirm price scope structure

### Phase 3

Build helper sheets.

- Variant Option Matrix first
- then Price Resolver
- then Variant Choice Availability
- then Package Composition
- then Audit Exceptions

### Phase 4

Build presentation sheets.

- start with one model family
- prove the system works
- then replicate

---

## My strongest recommendation from looking at your workbook

If you do only one major next step, make it:

### Build Variant Option Matrix

That sheet is the bridge between the abstract schema and the clean order guide you actually want.

Without it, the workbook is still a cluster of smart ingredients.
With it, the workbook becomes a machine.

If you want, next I can give you:

1. the exact header list and purpose for Variant Option Matrix in final form, and
2. the formulas / logic plan for how each column should be populated from your existing sheets.
