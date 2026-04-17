# Workbook roadmap

This roadmap reflects the **simplified clean schema**, the current workbook strategy, and the transition plan from legacy sheets into the new normalized structure.

The workbook should now be treated as a system with five layers:

1. Raw source layer
2. Staging / legacy processing layer
3. Clean canonical layer
4. Derived helper layer
5. Presentation layer

The immediate goal is **not** to perfect every legacy sheet. The goal is to migrate real logic into the clean canonical layer in a controlled way, validate the schema with worked examples, then build helper sheets and presentation sheets from there.

---

## Layer 1: Raw source sheets

These sheets are preserved source material. They should not be treated as the long-term home for business logic.

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

These tabs are source reference only.

### Relationship

They feed staging sheets and clean canonical sheets indirectly. Nothing downstream should depend on them directly once the data has been normalized.

### Status

**Keep as-is. Do not rebuild. Do not use as final truth.**

---

## Layer 2: Staging / legacy processing sheets

These sheets contain useful extraction work, partial normalization, or older processing logic. They still matter, but they are no longer the target architecture.

### Existing staging / legacy sheets

- Options Master
- Options Long
- Color Trim Notes
- Color Trim Seats
- Color Trim Matrix
- Color Trim Combos
- Option Pricing
- Option Catalog
- Option Rules
- Option Price Scopes
- Choice Groups
- Choice Group Members
- Order Schema Map
- Variant Catalog

### Role

These sheets currently serve one or more of these purposes:

- source extraction
- partial normalization
- rule discovery
- pricing discovery
- staging for migration into the clean sheets
- architecture reference

### Important distinction

Some of these sheets were previously treated as canonical. Going forward, they should be split into two subcategories:

#### Legacy canonical reference
These still contain important structured work and should be mined carefully:

- Variant Catalog
- Order Schema Map
- Option Catalog
- Option Rules
- Option Price Scopes
- Choice Groups
- Choice Group Members

#### Legacy staging / transformation
These are source-processing sheets and should not be treated as final truth:

- Options Master
- Options Long
- Color Trim Notes
- Color Trim Seats
- Color Trim Matrix
- Color Trim Combos
- Option Pricing

### Status

- **Variant Catalog**: keep active for now; still an important structured source
- **Order Schema Map**: keep active as architecture reference; update later to reflect the clean schema
- **Option Catalog / Option Rules / Option Price Scopes / Choice Groups / Choice Group Members**: treat as **legacy structured sheets that need migration or selective reprocessing**, not as the final target
- **Options Master / Options Long / Color Trim* / Option Pricing**: treat as **staging-only**

### Migration guidance

Do not bulk-copy all legacy rows into the clean sheets. Instead:

1. migrate one fact type at a time
2. preserve provenance in notes
3. reprocess ambiguous rows instead of forcing them through
4. use pilots and category-by-category passes

---

## Layer 3: Clean canonical sheets

These are now the target schema.

These sheets should stay intentionally lean. They are meant to hold the normalized facts, not every possible interpretation of the source material.

---

### 1) Option Catalog Clean

#### Purpose

Stores **option identity** only.

This sheet answers:
**What is this option?**

#### Recommended headers

- option_id
- rpo_code
- option_kind
- primary_name
- primary_description
- primary_section
- form_selectable_flag
- package_flag
- reference_only_flag
- notes

#### Relationship

Parent table for pricing, rules, and choice membership.

#### What belongs here

- one canonical row per real option whenever possible
- option identity
- option naming
- option classification
- whether the option is selectable, package-like, or reference-only

#### What does not belong here

- trim-specific pricing
- rule logic
- package membership rows
- variant-specific availability behavior
- mutually exclusive group logic

#### Status

**Active target sheet. Migrate into this next.**

#### Migration notes

- migrate only identity-level facts
- avoid duplicate rows created only because of pricing or trim differences
- preserve ambiguity in notes rather than widening the schema too early

---

### 2) Option Price Scopes Clean

#### Purpose

Stores **normalized pricing by context**.

This sheet answers:
**What does this option cost in this context?**

#### Recommended headers

- price_scope_id
- option_id
- rpo_code
- scope_type
- scope_value
- price
- price_mode
- condition_rpos_all
- condition_rpos_any
- notes

#### Relationship

Child of Option Catalog Clean.

#### What belongs here

- trim-scoped pricing
- variant-scoped pricing
- body-style pricing differences
- no-charge options
- included-standard pricing facts
- conditional pricing when supported by the source

#### Clarifying terms

- **scope_type** = the base context type, such as `trim`, `variant`, `model_family`, or `body_style`
- **scope_value** = the specific context value, such as `1LT`, `z06_3lz`, or `convertible`
- **condition_rpos_all** = extra RPOs that must all be true for the row to apply
- **condition_rpos_any** = extra RPOs where at least one must be true for the row to apply

#### What does not belong here

- option identity
- required-option logic
- exclusions
- package composition
- soft pricing commentary that has not been normalized

#### Status

**Active target sheet. Pilot tested and structurally viable.**

#### Migration notes

- this should become the canonical home for all normalized option pricing
- do not force messy pricing notes into structured rows prematurely
- the old `Option Pricing` and `Pricing` sheets remain source material

---

### 3) Option Rules Clean

#### Purpose

Stores **hard structured logic** between options and contexts.

This sheet answers:
**What must, cannot, includes, or changes because of this option?**

#### Recommended headers

- rule_id
- source_option_id
- source_rpo_code
- rule_type
- target_option_id
- target_rpo_code
- scope_type
- scope_value
- condition_rpos_all
- condition_rpos_any
- notes

#### Relationship

Links Option Catalog Clean rows to other options or contexts.

#### Recommended controlled rule types

- requires
- excludes
- includes
- not_available_with
- default_with (only if genuinely needed later)

#### What belongs here

- hard dependencies
- hard exclusions
- package includes relationships when modeled as rules
- contextual unavailability
- other structured rule logic supported by the source

#### What does not belong here

- base mutual exclusivity that is already defined by choice groups
- pricing
- soft phrases like “available with” unless clearly a hard dependency
- vague source commentary that should remain in notes

#### Status

**Active target sheet. Pilot tested and structurally viable, but should be used selectively.**

#### Migration notes

- avoid flooding this sheet with rows that are really choice-group structure
- use notes for soft or ambiguous source language
- if a fact is true because options belong to the same one-of-many family, it usually belongs in choice groups, not here

---

### 4) Choice Groups Clean

#### Purpose

Defines the **selection family** for mutually exclusive or otherwise grouped choices.

This sheet answers:
**What category is the user choosing from?**

#### Recommended headers

- choice_group_id
- group_name
- selection_mode
- scope_type
- scope_value
- parent_context_option_id
- notes

#### Relationship

Parent table for Choice Group Members Clean.

#### What belongs here

- seat selection groups
- interior color groups
- exterior color groups
- wheel groups
- other single-select or multi-select families
- seat-context-specific or trim-specific groups when member sets differ

#### Clarifying terms

- **selection_mode** is usually `single` or `multi`
- **parent_context_option_id** is useful when the group exists only because a specific option is selected, such as an interior color group tied to a seat type

#### What does not belong here

- individual group members
- pricing
- hard dependency rules
- pairwise exclusion rows for options that are already mutually exclusive by group design

#### Status

**Active target sheet. Needs substantial buildout.**

#### Migration notes

- this is where base one-selection-per-category logic should live
- if overlapping codes appear in different seat or trim contexts, separate scoped groups are acceptable and often correct

---

### 5) Choice Group Members Clean

#### Purpose

Lists the members of each clean choice group.

This sheet answers:
**Which options are selectable within that family?**

#### Recommended headers

- choice_group_id
- member_option_id
- member_rpo_code
- display_order
- default_flag
- notes

#### Relationship

Bridge table between Choice Groups Clean and Option Catalog Clean.

#### What belongs here

- the option members of each group
- display order
- default member flags where appropriate

#### What does not belong here

- group-level scope logic
- pricing
- rule logic

#### Status

**Active target sheet. Needs substantial buildout.**

#### Migration notes

- a single option may appear in multiple groups if those groups are scoped differently and do not represent the same simultaneous selection context

---

### 6) Data Dictionary Clean

#### Purpose

Documents the clean schema in plain English.

#### Relationship

Human reference sheet for workbook maintenance, migration decisions, and future GPT work.

#### Status

**Active support sheet. Keep current. Expand when a field meaning changes or a schema clarification is discovered.**

---

## Layer 4: Derived helper sheets

These sheets should be built only after the clean canonical layer is sufficiently populated.

They should be generated from the clean sheets, not from raw tabs directly.

---

### 7) Variant Option Matrix

#### Purpose

One row per `variant_id + option_id`.

This is still the most important helper sheet to build.

#### Relationship

Built from:

- Variant Catalog
- Option Catalog Clean
- Option Price Scopes Clean
- Option Rules Clean
- Choice Groups Clean
- Choice Group Members Clean

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

#### Status

**Planned. Do not build until the clean canonical layer is populated enough to support it.**

---

### 8) Package Composition

#### Purpose

Shows package-to-component relationships in a clear helper structure.

#### Relationship

Usually derived from Option Rules Clean and package rows in Option Catalog Clean.

#### Recommended headers

- package_option_id
- package_rpo_code
- package_name
- member_option_id
- member_rpo_code
- member_name
- relationship_type
- source_rule_id
- notes

#### Status

**Planned. Build after package logic in the clean sheets is trustworthy.**

---

### 9) Variant Choice Availability

#### Purpose

Shows which members of a choice group are available in a specific variant context.

#### Relationship

Built from:

- Variant Catalog
- Choice Groups Clean
- Choice Group Members Clean
- Option Rules Clean

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

#### Status

**Planned. Build after core choice groups are populated.**

---

### 10) Price Resolver

#### Purpose

Shows the resolved price for every option in every relevant variant context.

#### Relationship

Built from:

- Variant Catalog
- Option Price Scopes Clean
- package and inclusion logic

#### Recommended headers

- variant_id
- option_id
- rpo_code
- price_scope_id
- price_mode
- raw_price
- resolved_price
- source_reason
- review_flag
- notes

#### Status

**Planned. Build after pricing migration is mature enough.**

---

### 11) Rule Summary

#### Purpose

Provides a human-readable flattened view of structured rule logic.

#### Relationship

Derived from Option Rules Clean.

#### Recommended headers

- option_id
- rpo_code
- requires_rpos
- excludes_rpos
- includes_rpos
- not_available_with_rpos
- rule_summary
- review_flag

#### Status

**Planned. Useful after rules migration grows.**

---

### 12) Audit Exceptions

#### Purpose

Logs contradictions, missing mappings, ambiguous rows, orphan members, and other cleanup issues.

#### Relationship

Fed by checks across both legacy and clean layers during migration.

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

#### Status

**Recommended immediately if migration ambiguity starts to pile up.**

---

## Layer 5: Presentation sheets

These are the polished guide tabs people actually use.

They should be built from the helper layer, not from legacy sheets.

### Candidate guide strategy

Start with family-level guide sheets plus filters rather than one sheet per exact variant.

Examples:

- Stingray Guide
- Grand Sport Guide
- Z06 Guide
- ZR1 Guide
- ZR1X Guide

### Recommended display headers

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

### Standardized status values

- Standard
- Included
- Optional
- Package Only
- Conditional
- Not Available
- Reference Only

### Status

**Deferred until helper sheets exist.**

---

## Deprecated, migrate, and reprocess guidance

This is the practical triage list.

### Keep as raw reference

- Standard Equipment 1-4
- Equipment Groups 1-4
- Interior 1-4
- Exterior 1-4
- Mechanical 1-4
- Wheels 1-4
- Color and Trim 1-2
- All / All 1-4
- Pricing
- Dimensions
- Specs

### Keep as staging / extraction only

- Options Master
- Options Long
- Color Trim Notes
- Color Trim Seats
- Color Trim Matrix
- Color Trim Combos
- Option Pricing

### Keep active for migration support

- Variant Catalog
- Order Schema Map

### Needs migration into clean schema

- Option Catalog
- Option Rules
- Option Price Scopes
- Choice Groups
- Choice Group Members

### Likely needs selective reprocessing, not blind migration

- Option Rules
- Option Price Scopes
- Choice Groups
- Choice Group Members
- Option Pricing
- Color Trim Matrix
- Color Trim Combos

### Deprecated as final target architecture

The following are **not** deprecated as evidence, but **are deprecated as the final workbook destination for logic**:

- legacy Option Catalog
- legacy Option Rules
- legacy Option Price Scopes
- legacy Choice Groups
- legacy Choice Group Members
- Option Pricing as the final pricing engine
- any semi-processed temporary tabs created during earlier experiments

---

## Relationship map

### Raw/source feeds staging and migration work

- Pricing → Option Pricing → Option Price Scopes Clean
- Options Master / Options Long → Option Catalog Clean and Option Rules Clean
- Color Trim Seats / Matrix / Combos → Choice Groups Clean and Choice Group Members Clean
- raw category tabs → validation, gap-filling, and provenance

### Legacy structured sheets feed clean migration

- legacy Option Catalog → Option Catalog Clean
- legacy Option Rules → Option Rules Clean
- legacy Option Price Scopes → Option Price Scopes Clean
- legacy Choice Groups / Members → clean choice sheets

### Clean canonical feeds helper logic

- Variant Catalog
- Option Catalog Clean
- Option Price Scopes Clean
- Option Rules Clean
- Choice Groups Clean
- Choice Group Members Clean

These build:

- Variant Option Matrix
- Variant Choice Availability
- Package Composition
- Rule Summary
- Price Resolver
- Audit Exceptions

### Helper logic feeds presentation

- guide sheets
- future configurator exports
- cleaner order forms
- customer-facing filtered views

---

## Recommended build order

### Phase 1

Lock the architecture.

- keep raw tabs
- stop inventing new semi-random middle sheets
- use the clean schema as the target
- use legacy sheets as source, not destiny

### Phase 2

Populate and validate the clean canonical layer.

Recommended order:

1. Option Catalog Clean
2. Option Price Scopes Clean
3. Option Rules Clean
4. Choice Groups Clean
5. Choice Group Members Clean

Use category-by-category migration, not one giant pass.

### Phase 3

Pressure-test the clean schema with hard worked examples.

- AE4 / AH2 interior logic is the current proof of concept
- continue with adjacent families only after the pattern is trusted

### Phase 4

Build helper sheets.

1. Variant Option Matrix
2. Price Resolver
3. Variant Choice Availability
4. Package Composition
5. Rule Summary
6. Audit Exceptions

### Phase 5

Build presentation sheets.

- start with one model family
- prove the system works
- then replicate

---

## Current strongest recommendation

The workbook now has a clearer target architecture than before.

The most important thing is to **continue migrating into the clean canonical sheets without widening them prematurely**.

The next meaningful milestone after clean migration is still:

### Build Variant Option Matrix

That remains the bridge between abstract normalized data and the clean order guide you actually want.
