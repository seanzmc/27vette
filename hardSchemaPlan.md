# Corvette Configurator Data Structure Review & Implementation Roadmap

## Executive Recommendation

Your current structure has the right core idea: **`variants → option_status → options` should remain the availability spine** for the configurator. That is the safest place to answer the most important runtime question:

> “For this exact Corvette year/model/body/trim, which options are available, standard, included, unavailable, priced, or locked?”

However, the current outline needs tightening in four areas before it becomes reliable as the option-list source for a form app:

1. **Normalize variant context** so year/model/body/trim exclusions do not require excessive duplicate rows.
2. **Remove denormalized display fields** from canonical tables, especially in `choice_groups`.
3. **Harden rules and dependencies** by replacing polymorphic IDs with typed references and adding deterministic rule precedence.
4. **Create derived app-facing views** so the app consumes clean, resolved tables instead of raw authoring sheets.

The guiding principle should be:

> **Author broadly, resolve concretely.**  
> Maintain human-friendly scope rules such as “2024+ Z06 Coupe” or “all E-Ray variants,” but expand them into concrete `variant_id + option_id` rows before the app consumes the data.

---

# 1. Design Positions to Use Going Forward

## 1.1 Keep `variants + option_status + options` as the runtime spine

Keep this as the core resolved structure:

```text
variants
   ↓
option_status
   ↓
options
```

This should remain the authoritative source for trim-specific and year-specific availability.

For the app, every selectable or displayable option should eventually resolve to:

```text
variant_id
option_id
status
price
default_flag
locked_flag
availability_source
```

Where `status` should clearly distinguish values such as:

| Status               | Meaning                                                                                            |
| -------------------- | -------------------------------------------------------------------------------------------------- |
| `unavailable`        | Hard excluded for that variant. Never render or select.                                            |
| `optional`           | Available for selection. Price required, even if `0`.                                              |
| `standard_choice`    | Available as part of a required choice group; usually one default applies.                         |
| `standard_fixed`     | Standard and locked for the variant.                                                               |
| `included`           | Included by model, trim, package, or another selected option.                                      |
| `requires_selection` | Available only if another dependency is satisfied. Optional if you want precomputed dynamic state. |

Important rule:

> Missing `option_status` should be treated as **unavailable by default** unless you intentionally choose an allow-by-default model. For a vehicle configurator, deny-by-default is safer.

---

## 1.2 Normalize year/model/body/trim, but resolve to concrete variants

Do not rely only on free-text fields inside `variants`.

Add lookup tables:

```text
model_years
models
body_styles
trims
datasets
categories
```

Then make `variants` reference them:

```text
variants
- variant_id
- dataset_id
- model_year
- model_key
- body_style
- trim_level
- display_name
- active
```

This allows the app and audit layer to cleanly reason about:

- 2024 Stingray Coupe
- 2025 Z06 Convertible
- 2024 E-Ray Coupe
- All Z06 variants
- All 2024+ models
- All convertibles
- All E-Ray trims except a specific year

---

## 1.3 Add `variant_scopes` for broad authoring rules

Exact `variant_id` rows are good for runtime, but they become repetitive for broad exclusions.

Add a structured scope table:

```text
variant_scopes
- scope_id
- scope_name
- year_min
- year_max
- model_key
- body_style
- trim_level
- dataset_id
- active
```

Null values can mean wildcard.

Example:

| scope_id               | scope_name       | year_min | year_max | model_key  | body_style | trim_level |
| ---------------------- | ---------------- | -------: | -------: | ---------- | ---------- | ---------- |
| `SCOPE_Z06_ALL`        | All Z06 variants |          |          |            |            | `Z06`      |
| `SCOPE_2024_PLUS_ERAY` | 2024+ E-Ray      |     2024 |          | `ERAY`     |            |            |
| `SCOPE_STINGRAY_COUPE` | Stingray Coupe   |          |          | `STINGRAY` | `Coupe`    |            |

Then create a derived expansion sheet:

```text
scope_variants
- scope_id
- variant_id
```

The app should not need to evaluate wildcard logic at runtime. It should consume already-expanded concrete rows.

A lightweight `variant_filter_tag` may be useful as a display/helper label, but it should not be the canonical dependency mechanism. Structured `variant_scopes` are safer because they can be validated.

---

## 1.4 Use derived variant-specific UI visibility

The presentation chain is generally correct:

```text
steps
   ↓
sections
   ↓
choice_groups
   ↓
choice_group_options
   ↓
options
```

But `choice_group_options` is global placement, while `option_status` is variant-specific availability.

Therefore, do **not** render `choice_group_options` directly. Instead, create a derived app view:

```text
variant_choice_group_options
```

Generated by joining:

```text
variants
option_status
options
choice_group_options
choice_groups
sections
steps
```

Filter out:

- inactive steps
- inactive sections
- inactive groups
- inactive options
- `option_status.status = unavailable`
- options with no valid UI placement, unless they are intentionally non-configurable standard equipment

This prevents two common failure modes:

1. **Unavailable option renders in the form** because it exists in a choice group.
2. **Available option is buyable but unrenderable** because it exists in `option_status` but is missing from `choice_group_options`.

You may also materialize:

```text
variant_choice_groups
variant_sections
```

These should be derived views unless you have groups or sections that need to appear even when they contain no currently available options.

---

# 2. Data Connection Gaps to Close

## 2.1 Missing `datasets` parent table

If `dataset_id` appears on `steps`, `sections`, or exports, it needs a real parent table:

```text
datasets
- dataset_id
- dataset_name
- model_family
- schema_version
- active
```

Also add `dataset_id` to `variants`.

If one variant can belong to multiple datasets, use a bridge:

```text
variant_datasets
- variant_id
- dataset_id
```

But for a single Corvette configurator dataset, a direct `variants.dataset_id` is simpler.

Recommended chain:

```text
datasets
   ↓
variants

datasets
   ↓
steps
   ↓
sections
   ↓
choice_groups
```

Avoid repeating `dataset_id` on every child table if it can be reached through the parent.

---

## 2.2 Missing `categories` lookup

If `sections` has `category_id` and `category_name`, create:

```text
categories
- category_id
- category_name
- display_order
- active
```

Then keep only `category_id` on `sections`.

Do not duplicate `category_name` in `sections` or `choice_groups`.

---

## 2.3 Missing variant-to-presentation connection

The app currently has to infer whether a group or section applies to a variant by looking at the available options inside that group.

That is acceptable if you materialize derived views:

```text
variant_choice_group_options
variant_choice_groups
variant_sections
```

Recommended logic:

```text
A group is visible for a variant if:
- the group is active
- its parent section and step are active
- at least one option in the group is active
- at least one option in the group has non-unavailable option_status for that variant
```

Add an audit check for active groups that never resolve to any variant.

---

## 2.4 Missing rule payload for `price_override`

If you have a rule type such as `price_override`, the rule must contain a numeric payload.

Add fields such as:

```text
rule_action_value
price_mode
currency
priority
```

Example:

| rule_type          | target_option_id | price_mode   | rule_action_value |
| ------------------ | ---------------- | ------------ | ----------------: |
| `price_override`   | `Q9I`            | `set_price`  |             `995` |
| `price_adjustment` | `ABC`            | `add_amount` |            `-500` |
| `package_credit`   | `XYZ`            | `credit`     |            `-250` |

Do not store price logic only in a message field.

---

## 2.5 Undefined pricing precedence

Pricing needs deterministic order.

Recommended precedence:

| Priority | Pricing Source                 | Behavior                                                                    |
| -------: | ------------------------------ | --------------------------------------------------------------------------- |
|        1 | `option_status.price`          | Base resolved price for the option on the variant.                          |
|        2 | Package inclusion              | Included package members usually become `included` with no separate charge. |
|        3 | Rule-based price override      | Applies only if conditions are met and target is available.                 |
|        4 | Rule-based credit or surcharge | Adds or subtracts from the resolved price.                                  |
|        5 | Manual/admin override          | Highest priority, should be rare and audited.                               |

Add rule fields:

```text
priority
price_mode
rule_action_value
effective_scope_id
```

If two active price overrides affect the same `variant_id + option_id` with the same priority, flag it as an error.

---

## 2.6 Polymorphic rule references are too weak for Sheets

Avoid this pattern as the canonical editable structure:

```text
source_type | source_id
target_type | target_id
```

Sheets cannot enforce true foreign keys against multiple possible parent tables in one column.

Instead, use typed nullable columns:

```text
source_option_id
source_group_id
source_variant_id
source_package_id

target_option_id
target_group_id
target_variant_id
target_package_id
```

Then add a validation rule:

> Exactly one source reference must be populated, and exactly one target reference must be populated.

You may keep computed helper columns:

```text
source_type
source_id
target_type
target_id
```

But those should be generated, not manually edited.

---

## 2.7 Rules need multi-condition support

Pairwise rules are not enough for real vehicle dependencies such as:

- exterior color × interior color
- seat type × trim
- wheel package × brake package
- convertible-only restrictions
- package requiring one of several options
- option excluded only when two other selections are both present

Add:

```text
rule_conditions
- rule_id
- condition_group
- condition_order
- condition_type
- condition_option_id
- condition_group_id
- operator
- expected_value
```

Example operators:

```text
is_selected
is_not_selected
is_available
is_unavailable
is_in_group
```

Use `condition_group` to support OR groups.

Example:

```text
Rule applies when:
(condition_group 1: option A is selected AND option B is selected)
OR
(condition_group 2: option C is selected)
```

Then the rule action fires.

---

# 3. Redundancy to Remove

## 3.1 Remove denormalized fields from `choice_groups`

`choice_groups` should not store copied section, category, or step data.

Avoid:

```text
section_name
category_id
category_name
step_key
```

Canonical `choice_groups` should be closer to:

```text
choice_groups
- group_id
- section_id
- group_label
- selection_mode
- required
- min_select
- max_select
- display_order
- active
```

Resolve step/category/section display through joins or lookup formulas.

---

## 3.2 Remove duplicated `category_name`

Use:

```text
sections.category_id → categories.category_id
```

Then derive `category_name` when needed.

---

## 3.3 Replace `standard_equipment` with a derived view

Do not maintain `standard_equipment` as an independent source table if it is derived from `option_status`.

Create:

```text
standard_equipment_view
```

Derived from:

```text
option_status
options
variants
sections
choice_groups
```

Filter statuses such as:

```text
standard_fixed
standard_choice
included
```

However, preserve non-derivable fields.

If `standard_equipment` currently contains:

```text
label_override
description_override
notes
```

move them to either:

```text
option_status
```

or a thin extension table:

```text
option_status_overrides
- variant_id
- option_id
- label_override
- description_override
- notes
```

The export can still contain those fields, but the export should be generated, not manually maintained.

---

## 3.4 Normalize `variants` instead of repeating flat text

Avoid relying on free-text `model_year`, `model_key`, `body_style`, and `trim_level` without validation.

Use lookup-backed values and named ranges.

This reduces drift such as:

```text
Z06
Z-06
Z 06
z06
```

---

## 3.5 Treat `source_rows` as staging, not runtime data

Keep raw import data isolated.

Recommended lifecycle:

1. Import raw Corvette data into `source_rows`.
2. Normalize into canonical tables.
3. Preserve `source_row_id` on canonical records for traceability.
4. Archive old raw tabs after successful normalization.
5. Do not let the app consume `source_rows`.

---

# 4. Recommended Table Structure

## 4.1 Lookup tables

```text
datasets
- dataset_id
- dataset_name
- model_family
- active

model_years
- model_year
- active

models
- model_key
- model_name
- active

body_styles
- body_style
- body_style_label
- active

trims
- trim_level
- trim_label
- active

categories
- category_id
- category_name
- display_order
- active
```

---

## 4.2 Variant tables

```text
variants
- variant_id
- dataset_id
- model_year
- model_key
- body_style
- trim_level
- display_name
- active
```

```text
variant_scopes
- scope_id
- scope_name
- dataset_id
- year_min
- year_max
- model_key
- body_style
- trim_level
- active
```

```text
scope_variants
- scope_variant_key
- scope_id
- variant_id
```

`scope_variants` should be derived from `variant_scopes`.

---

## 4.3 Option tables

Use an internal stable key for options.

Do not assume an RPO code is globally unique forever.

```text
options
- option_id
- rpo_code
- option_label
- option_description
- option_type
- option_family
- active
```

To handle RPO reuse or year-specific definitions, add either validity fields:

```text
valid_year_min
valid_year_max
model_key
```

or a dedicated version table:

```text
option_versions
- option_version_id
- option_id
- rpo_code
- model_year
- model_key
- label
- description
- active
```

This matters because the same code may be reused, renamed, redefined, or scoped differently across Corvette years.

---

## 4.4 Availability tables

For editing, use a scope-aware authoring table:

```text
option_availability
- availability_id
- scope_id
- variant_id
- option_id
- status
- base_price
- default_flag
- locked_flag
- notes
- active
```

Rules:

- Use `scope_id` for broad availability.
- Use `variant_id` for exact overrides.
- Do not populate both unless you explicitly support override precedence.
- Exact `variant_id` overrides should win over broad `scope_id` rows.

Then generate:

```text
option_status_resolved
- variant_option_key
- variant_id
- option_id
- resolved_status
- resolved_price
- default_flag
- locked_flag
- source_availability_id
```

This resolved table is what the app should consume.

---

## 4.5 Presentation tables

```text
steps
- step_id
- dataset_id
- step_key
- step_label
- display_order
- active
```

```text
sections
- section_id
- step_id
- category_id
- section_label
- display_order
- active
```

```text
choice_groups
- group_id
- section_id
- group_label
- selection_mode
- required
- min_select
- max_select
- display_order
- active
```

```text
choice_group_options
- group_option_key
- group_id
- option_id
- display_order
- active
```

Use generated views for display fields such as category name, step label, and section name.

---

## 4.6 Rules tables

Recommended structure:

```text
rules
- rule_id
- rule_name
- rule_type
- scope_id
- variant_id
- priority
- message
- active
```

Use either `scope_id` or `variant_id`. If both are blank, the rule is global.

Add condition table:

```text
rule_conditions
- rule_condition_id
- rule_id
- condition_group
- condition_order
- source_option_id
- source_group_id
- source_variant_id
- operator
- expected_value
- active
```

Add action table:

```text
rule_actions
- rule_action_id
- rule_id
- action_type
- target_option_id
- target_group_id
- target_variant_id
- price_mode
- rule_action_value
- active
```

For `requires_any`, package members, or reusable lists, keep:

```text
rule_members
- rule_member_id
- rule_id
- member_option_id
- member_group_id
- display_order
- active
```

Do not store generic `member_id` without a typed FK column.

---

## 4.7 Package and bundle tables

Vehicle configurators often need package logic. Do not force all package behavior into simple `requires` rules.

A clean pattern is to treat a selectable package as an option with `option_type = package`, then add package member tables.

```text
packages
- package_id
- package_option_id
- package_label
- active
```

```text
package_members
- package_member_id
- package_id
- member_option_id
- member_status
- member_price_mode
- member_price_value
- required
- locked
- active
```

Example `member_status` values:

```text
included
required
discounted
credit
forced
```

This allows support for:

- package includes wheel option
- package requires performance exhaust
- package discounts another option
- package gives credit for replacing a standard item
- package locks included components

Package rules should still resolve to concrete `variant_id + option_id` effects before publishing.

---

# 5. Dependency Logic and Precedence Matrix

A configurator needs explicit conflict rules. Do not let contradictory rules silently override each other.

## 5.1 Recommended dependency precedence

| Precedence | Layer                       | Rule                                                                                                                                                                      |
| ---------: | --------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
|          1 | Inactive records            | Inactive parent disables child records. Active child under inactive parent is an audit error.                                                                             |
|          2 | Variant static availability | `unavailable` wins over all positive rules. If an option is unavailable for a variant, no rule or package should make it selectable without an explicit availability row. |
|          3 | UI placement                | Available configurable options must have valid placement in an active choice group.                                                                                       |
|          4 | Standard/included state     | `standard_fixed` and `included` options are auto-selected or displayed as locked, depending on type.                                                                      |
|          5 | User selection              | User choices are applied after static availability and defaults.                                                                                                          |
|          6 | Requires/includes           | Selecting one option may require, include, or force another available option.                                                                                             |
|          7 | Excludes/conflicts          | Exclusions disable or remove conflicting selections.                                                                                                                      |
|          8 | Price overrides/credits     | Pricing is calculated after the final valid selection set is resolved.                                                                                                    |
|          9 | Manual/admin override       | Highest priority, audited, rarely used.                                                                                                                                   |

Important:

> If one rule requires an option and another excludes the same option within the same overlapping scope, that should be treated as a data error, not as a precedence decision.

---

## 5.2 Hard conflict rules

Flag these as errors:

| Conflict                                                 | Example                                                |
| -------------------------------------------------------- | ------------------------------------------------------ |
| Rule targets unavailable option                          | Z06-only option required by a Stingray rule.           |
| Package includes unavailable member                      | E-Ray package includes a Stingray-only part.           |
| A requires B while B excludes A                          | Circular contradiction.                                |
| A excludes B while B is `standard_fixed`                 | Dynamic rule conflicts with static standard equipment. |
| Two defaults in required single-select group             | Required group cannot resolve cleanly.                 |
| No default in required single-select group               | App cannot determine base configuration.               |
| Multiple price overrides with same priority              | Price result is ambiguous.                             |
| Option available but not placed in any group             | Buyable but unrenderable.                              |
| Option placed in group but unavailable for every variant | Dead UI data.                                          |

---

## 5.3 Dependency-cycle detection

Create a graph from rules:

```text
requires
includes
forces
```

These are directed edges:

```text
A → B
```

Create another graph for exclusions:

```text
A excludes B
```

These are conflict edges.

Audit for:

- `A requires A`
- `A excludes A`
- `A requires B` and `B excludes A`
- `A requires B`, `B requires C`, `C excludes A`
- circular requires loops that are not intentional bundles
- package includes itself through nested members

In Google Sheets this can be partially audited with helper tables, but full cycle detection is better handled by Apps Script, Power Query, or a publish-time validation script.

---

# 6. Choice Group Cardinality and Default Validation

This is critical for form behavior.

Add these fields to `choice_groups`:

```text
selection_mode
required
min_select
max_select
```

Recommended validation by resolved `variant_id + group_id`:

| Group Type             | Validation                                                                |
| ---------------------- | ------------------------------------------------------------------------- |
| Required single-select | Exactly one default or standard choice must resolve for the variant.      |
| Optional single-select | Zero or one default allowed.                                              |
| Required multi-select  | At least `min_select` options available.                                  |
| Limited multi-select   | Available selections cannot exceed `max_select`.                          |
| Locked standard group  | All `standard_fixed` or `included` options should be locked/display-only. |

For each variant, generate:

```text
variant_group_validation
- variant_id
- group_id
- available_option_count
- default_option_count
- standard_fixed_count
- required
- selection_mode
- validation_status
```

Example validation statuses:

```text
OK
NO_AVAILABLE_OPTIONS
MISSING_DEFAULT
MULTIPLE_DEFAULTS
MAX_LESS_THAN_MIN
REQUIRED_GROUP_EMPTY
```

---

# 7. Spreadsheet Hardening for Excel / Google Sheets

Spreadsheets cannot truly enforce relational integrity like SQL, so the goal is:

> Prevent easy mistakes during editing, and block publishing if integrity checks fail.

## 7.1 Named ranges

Create named ranges for every primary key list:

```text
DATASET_IDS
VARIANT_IDS
SCOPE_IDS
OPTION_IDS
GROUP_IDS
SECTION_IDS
STEP_IDS
CATEGORY_IDS
RULE_IDS
PACKAGE_IDS
```

Use these named ranges for Data Validation dropdowns.

Avoid high-frequency `IMPORTRANGE` validation if possible. Keep the configurator authoring tabs in one workbook to avoid latency and permission issues.

---

## 7.2 Helper keys for bridge tables

For entity tables, use single-column surrogate IDs:

```text
step_id
section_id
group_id
rule_id
```

For bridge/intersection tables, use helper keys:

```text
variant_option_key = variant_id & "|" & option_id
group_option_key = group_id & "|" & option_id
scope_variant_key = scope_id & "|" & variant_id
package_member_key = package_id & "|" & member_option_id
```

This gives Sheets a single column to check for duplicates.

---

## 7.3 Data validation rules

Use dropdown validation for:

- FK columns
- enum columns
- status values
- selection modes
- rule types
- price modes
- active flags

Example enum lists:

```text
option_status:
optional
unavailable
standard_choice
standard_fixed
included
```

```text
selection_mode:
single
multi
display_only
```

```text
rule_type:
requires
requires_any
excludes
includes
price_override
price_adjustment
default_override
```

```text
price_mode:
set_price
add_amount
credit
included_no_charge
```

---

## 7.4 Conditional formatting and audit checks

Add conditional formatting for:

- duplicate primary keys
- blank required fields
- invalid FK references
- inactive parent with active child
- optional option missing price
- price override missing `rule_action_value`
- rule with no source or no target
- rule with more than one source or target populated
- available option with no group placement
- group placement for option unavailable in all variants
- required single-select group with no default
- required single-select group with multiple defaults

Specifically flag:

```text
status = optional AND price is blank
```

A valid free option should have price `0`, not blank.

---

## 7.5 `_integrity` dashboard

Create a dedicated `_integrity` tab.

Each row should test one relation or rule.

Example checks:

| Check                                          | Error Count |
| ---------------------------------------------- | ----------: |
| Duplicate `variant_id`                         |           0 |
| Duplicate `option_id`                          |           0 |
| Orphan `option_status.variant_id`              |           0 |
| Orphan `option_status.option_id`               |           0 |
| Orphan `choice_group_options.group_id`         |           0 |
| Orphan `choice_group_options.option_id`        |           0 |
| Available options with no UI placement         |           0 |
| Active choice groups with no available options |           0 |
| Invalid rule source references                 |           0 |
| Invalid rule target references                 |           0 |
| Price overrides missing numeric value          |           0 |
| Optional options missing price                 |           0 |
| Required groups missing default                |           0 |
| Required groups with multiple defaults         |           0 |
| Package members unavailable in scope           |           0 |
| Rule dependency cycles                         |           0 |
| Active children under inactive parents         |           0 |

Publishing should be blocked unless all critical counts are zero.

---

## 7.6 `_manifest` tab

Add a `_manifest` tab that documents every sheet:

```text
sheet_name
primary_key_column
named_range
description
source_type
editable
published
```

This becomes the living data dictionary for both humans and import scripts.

---

## 7.7 Audit metadata

For active canonical tables, add:

```text
created_at
created_by
last_updated
last_updated_by
source_row_id
notes
```

This is especially useful when Corvette data is imported from multiple sources or revised over time.

---

## 7.8 Active cascade consistency

If a parent is inactive, children should not remain active.

Examples:

- inactive step → sections should not be active
- inactive section → groups should not be active
- inactive group → group options should not be active
- inactive option → option status rows should not be active
- inactive package → package members should not be active

You can enforce this with formulas, conditional formatting, or Apps Script.

---

# 8. App-Facing Derived Views

The form app should not read raw normalized authoring tabs directly.

Create clean published views.

## 8.1 Variant selector view

```text
app_variants
- variant_id
- display_name
- model_year
- model_key
- body_style
- trim_level
- active
```

---

## 8.2 UI render view

```text
app_ui_render
- dataset_id
- variant_id
- step_id
- step_label
- step_order
- section_id
- section_label
- section_order
- group_id
- group_label
- group_order
- selection_mode
- required
- min_select
- max_select
- option_id
- rpo_code
- option_label
- option_description
- status
- price
- default_flag
- locked_flag
- display_order
```

This is the main table the configurator should use to draw the form.

---

## 8.3 Standard equipment view

```text
app_standard_equipment
- variant_id
- option_id
- rpo_code
- label
- description
- status
- notes
```

Generated from `option_status_resolved` where:

```text
status IN ('standard_fixed', 'standard_choice', 'included')
```

---

## 8.4 Rules view

```text
app_rules_resolved
- rule_id
- variant_id
- rule_type
- priority
- source_type
- source_id
- target_type
- target_id
- action_type
- price_mode
- rule_action_value
- message
```

This should already be expanded by `scope_id` into concrete `variant_id` rows.

---

## 8.5 Package view

```text
app_packages_resolved
- variant_id
- package_option_id
- member_option_id
- member_status
- member_price_mode
- member_price_value
- required
- locked
```

---

# 9. Publishing, Versioning, Cache, and Rollback

Do not let the app depend on live editable tabs.

Add a release workflow.

## 9.1 Release manifest

```text
_releases
- release_id
- schema_version
- data_version
- status
- created_at
- published_at
- published_by
- checksum
- rollback_to_release_id
- notes
```

Recommended statuses:

```text
draft
validated
published
archived
rolled_back
```

The app should consume only the latest `published` release.

---

## 9.2 Immutable publish snapshots

At publish time, copy or export the app-facing views to immutable tabs/files:

```text
published_app_variants
published_app_ui_render
published_app_rules_resolved
published_app_standard_equipment
published_app_packages_resolved
```

or export them as versioned CSV/JSON files.

---

## 9.3 Cache invalidation

Include `release_id` in the app payload.

The app can cache aggressively, but it should refresh when `release_id` changes.

Example:

```text
current_release_id = 2026.05.07-001
```

If rollback is needed, switch the active published release pointer back to the previous release.

---

# 10. End-to-End Corvette Test Matrix

Before publishing real data, create a test matrix that proves the dependency model works.

At minimum, test these variant families:

| Model    | Body        | Trim/Type   | Purpose                                             |
| -------- | ----------- | ----------- | --------------------------------------------------- |
| Stingray | Coupe       | 1LT/2LT/3LT | Base availability, common options, standard choices |
| Stingray | Convertible | 1LT/2LT/3LT | Convertible exclusions and body-specific options    |
| Z06      | Coupe       | 1LZ/2LZ/3LZ | Z06-only performance options                        |
| Z06      | Convertible | 1LZ/2LZ/3LZ | Z06 plus convertible constraints                    |
| E-Ray    | Coupe       | 1LZ/2LZ/3LZ | Hybrid/AWD-specific options                         |
| E-Ray    | Convertible | 1LZ/2LZ/3LZ | E-Ray plus convertible restrictions                 |

Also test year boundaries:

| Scenario                                      | Expected Result                    |
| --------------------------------------------- | ---------------------------------- |
| 2023-only option selected on 2024 variant     | Not rendered or marked unavailable |
| 2024+ feature on 2023 variant                 | Excluded                           |
| Z06-only option on Stingray                   | Excluded                           |
| E-Ray-only option on Z06                      | Excluded                           |
| Convertible-only option on Coupe              | Excluded                           |
| Coupe-only option on Convertible              | Excluded                           |
| Package includes unavailable option           | Integrity error                    |
| Required single-select group has no default   | Integrity error                    |
| Required single-select group has two defaults | Integrity error                    |
| A requires B while B excludes A               | Integrity error                    |
| Optional option missing price                 | Integrity error                    |
| Available option missing group placement      | Integrity error                    |

---

# 11. Implementation Roadmap

## Phase 0 — Freeze and document the current schema

Before restructuring:

1. Freeze the existing workbook or CSV set.
2. Create `_manifest`.
3. Identify current primary keys and composite keys.
4. Mark which tabs are canonical, derived, staging, or export-only.
5. Add `source_row_id` to normalized records where traceability is needed.

Deliverables:

```text
_manifest
_current_schema_snapshot
_source_rows_archive
```

---

## Phase 1 — Create canonical lookup tables

Add and populate:

```text
datasets
model_years
models
body_styles
trims
categories
```

Then update `variants` and `sections` to use validated lookup values.

Deliverables:

```text
datasets
model_years
models
body_styles
trims
categories
cleaned variants
cleaned sections
```

---

## Phase 2 — Normalize the presentation spine

Clean the UI structure.

Update:

```text
steps
sections
choice_groups
choice_group_options
```

Actions:

1. Add `step_id` if steps currently rely on composite keys.
2. Keep `dataset_id` on `steps`.
3. Keep `step_id` on `sections`.
4. Keep `section_id` on `choice_groups`.
5. Remove copied fields from `choice_groups`:
   - `section_name`
   - `category_id`
   - `category_name`
   - `step_key`
6. Use derived display views for labels.

Deliverables:

```text
steps
sections
choice_groups
choice_group_options
choice_group_display_view
```

---

## Phase 3 — Add variant scopes and resolved availability

Create:

```text
variant_scopes
scope_variants
option_availability
option_status_resolved
```

Actions:

1. Convert broad trim/year/model rules into `variant_scopes`.
2. Use `scope_variants` to expand scopes to exact variants.
3. Use `option_availability` for authoring.
4. Generate `option_status_resolved` for app use.
5. Treat missing resolved availability as unavailable.

Deliverables:

```text
variant_scopes
scope_variants
option_availability
option_status_resolved
```

---

## Phase 4 — Harden the rules engine

Replace generic polymorphic references with typed columns.

Create or refactor:

```text
rules
rule_conditions
rule_actions
rule_members
```

Actions:

1. Add typed source and target columns.
2. Add `rule_action_value` for price overrides.
3. Add `priority`.
4. Add `scope_id` support.
5. Add multi-condition support.
6. Add dependency-cycle validation.
7. Add contradiction checks.

Deliverables:

```text
rules
rule_conditions
rule_actions
rule_members
rules_resolved_by_variant
```

---

## Phase 5 — Add packages and bundles

Create:

```text
packages
package_members
app_packages_resolved
```

Actions:

1. Model package RPOs as selectable options.
2. Map package member options.
3. Define included, required, discounted, credited, and locked behavior.
4. Validate that package members are available within the package scope.
5. Resolve packages to concrete variant-level effects.

Deliverables:

```text
packages
package_members
package_validation
app_packages_resolved
```

---

## Phase 6 — Replace `standard_equipment` with a derived view

Actions:

1. Stop editing `standard_equipment` manually.
2. Generate it from `option_status_resolved`.
3. Move overrides and notes into `option_status` or `option_status_overrides`.
4. Protect the derived standard equipment tab.

Deliverables:

```text
standard_equipment_view
app_standard_equipment
option_status_overrides
```

---

## Phase 7 — Build the integrity layer

Create:

```text
_integrity
_manifest
_validation_lists
```

Add checks for:

- duplicate keys
- orphan FKs
- invalid enums
- inactive parent/active child conflicts
- unplaced available options
- dead UI group placements
- missing prices
- missing price override payloads
- invalid package members
- rule contradictions
- rule cycles
- group default/cardinality errors
- overlapping RPO version definitions

Deliverables:

```text
_integrity dashboard
publish_blocker flag
```

---

## Phase 8 — Build app-facing resolved views

Create protected/read-only views:

```text
app_variants
app_ui_render
app_standard_equipment
app_rules_resolved
app_packages_resolved
```

The app should consume these views only.

Deliverables:

```text
app_variants
app_ui_render
app_standard_equipment
app_rules_resolved
app_packages_resolved
```

---

## Phase 9 — Test with a Corvette matrix

Run test cases across:

- Stingray Coupe
- Stingray Convertible
- Z06 Coupe
- Z06 Convertible
- E-Ray Coupe
- E-Ray Convertible
- year-specific exclusions
- trim-specific parts
- package inclusions
- pricing overrides
- default selections
- contradictory rules
- dependency cycles

Deliverables:

```text
test_matrix
test_results
known_issues
```

---

## Phase 10 — Publish, version, cache, and rollback

Actions:

1. Add `_releases`.
2. Validate all integrity checks.
3. Snapshot app-facing views.
4. Mark one release as `published`.
5. Have the app read only the published release.
6. Use `release_id` for cache invalidation.
7. Support rollback by switching the active published release.

Deliverables:

```text
_releases
published_app_variants
published_app_ui_render
published_app_rules_resolved
published_app_standard_equipment
published_app_packages_resolved
```

---

# Final Priority List

| Priority | Change                                                          | Why It Matters                                                       |
| -------- | --------------------------------------------------------------- | -------------------------------------------------------------------- |
| P0       | Add `datasets`, `categories`, and normalized variant lookups    | Eliminates free-text drift and closes parent namespace gaps.         |
| P0       | Keep `option_status` as the concrete runtime availability spine | Ensures exact trim/year/model option filtering.                      |
| P0       | Add `variant_scopes` and scope expansion                        | Prevents duplicate rows for broad year/model/trim exclusions.        |
| P0       | Remove denormalized fields from `choice_groups`                 | Prevents section/category/step drift.                                |
| P1       | Replace `standard_equipment` with a derived view                | Preserves single source of truth.                                    |
| P1       | Split polymorphic rule IDs into typed FK columns                | Makes Sheets validation practical.                                   |
| P1       | Add `rule_action_value`, pricing mode, and priority             | Makes price overrides deterministic.                                 |
| P1       | Add `rule_conditions`                                           | Supports real multi-condition Corvette dependencies.                 |
| P1       | Add group cardinality/default validation                        | Prevents broken required dropdowns and ambiguous defaults.           |
| P2       | Add package/bundle modeling                                     | Required for realistic vehicle packages, credits, and included sets. |
| P2       | Add RPO/version handling                                        | Prevents cross-year option-code ambiguity.                           |
| P2       | Add `_integrity` and `_manifest` tabs                           | Gives you publish-time relational safety.                            |
| P3       | Add release/version/cache workflow                              | Prevents the app from reading unstable draft data.                   |

The end state should be a workbook where humans edit normalized, validated authoring sheets, while the configurator reads only resolved, protected, published views. This keeps the Corvette option data manageable while still supporting strict trim-specific parts, year/model exclusions, packages, pricing, and dependency logic.
