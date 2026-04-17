---
name: 27vette
description: Maintain and normalize Chevrolet Corvette order-guide workbooks in Excel. Use when Codex needs to interpret raw GM export sheets, preserve a canonical workbook architecture, model options, rules, packages, price scopes, or mutually exclusive selections, reconcile staging sheets against canonical tables, or generate clean order-guide presentation sheets without embedding business logic in display tabs.
---

# Corvette Order Guide Workbook

## Goal

Treat the workbook as a small relational system inside Excel.

Preserve a four-layer architecture:

1. Raw source layer
2. Canonical normalized layer
3. Derived logic layer
4. Presentation layer

Keep business logic in canonical or derived sheets, not in human-facing guide tabs.

## Start Here

Classify the request before editing anything:

1. Determine whether the task affects raw source, canonical data, derived logic, or presentation output.
2. Inspect canonical sheets first.
3. Use staging or legacy sheets only to backfill, validate, or normalize missing information.
4. Log unresolved conflicts instead of guessing.

## Prioritize Sheets

Treat these sheets as canonical unless the user explicitly overrides them:

- `Variant Catalog`
- `Order Schema Map`
- `Option Catalog`
- `Option Rules`
- `Option Price Scopes`
- `Choice Groups`
- `Choice Group Members`

Treat these sheets as secondary reference or staging material:

- `Pricing`
- `Options Master`
- `Options Long`
- `Color Trim Notes`
- `Color Trim Seats`
- `Color Trim Matrix`
- `Color Trim Combos`
- `All`
- `All 1`
- `All 2`
- `All 3`
- `All 4`
- `Standard Equipment 1-4`
- `Equipment Groups 1-4`
- `Interior 1-4`
- `Exterior 1-4`
- `Mechanical 1-4`
- `Wheels 1-4`
- `Dimensions`
- `Specs`
- `Option Pricing`

Do not let staging or legacy sheets override canonical tables without a confirmed reason.

## Model the Workbook Explicitly

Use stable IDs for every canonical entity and relationship:

- `variant_id`
- `option_id`
- `rule_id`
- `price_scope_id`
- `choice_group_id`

Do not use labels as keys.

Represent core entities this way:

- `Variant`: Define the root order context for a buildable vehicle, including model family, body style, trim, display name, model code, and orderability flags.
- `Option`: Define one canonical row per real option or RPO-backed item; keep identity separate from pricing and availability context.
- `Rule`: Store structured relationships such as `requires`, `excludes`, `includes`, `standard_with`, `available_with`, `not_available_with`, `recommended_with`, `package_contains`, `one_of_group`, or `conditional_override`.
- `Price scope`: Store what an option costs in a specific variant or conditional context.
- `Choice group`: Store mutually exclusive selection families such as seats, interior colors, exterior colors, wheels, or aero choices.

## Apply These Rules

- Keep one canonical option row per option whenever possible.
- Separate option identity from pricing.
- Separate rules from notes.
- Convert logic-bearing notes into structured rule rows whenever the source supports it.
- Model mutually exclusive categories through `Choice Groups` and `Choice Group Members`.
- Preserve raw imports unless the user explicitly requests edits to them.
- Record ambiguity in an audit structure instead of silently inventing logic.

## Build in This Order

1. Normalize raw or staging data into canonical tables.
2. Resolve pricing, availability, package logic, and rule behavior in helper sheets.
3. Generate presentation sheets from canonical and helper layers.
4. Record any unresolved conflict in an audit or exception sheet.

Prefer creating or maintaining these derived sheets when needed:

- `Variant Option Matrix`
- `Option Rule Summary`
- `Price Resolver`
- `Package Composition`
- `Variant Choice Availability`
- `Audit Exceptions`

## Design Presentation Sheets Carefully

Make human-facing order-guide sheets:

- easy to scan
- explicit about `standard`, `optional`, `included`, and `unavailable` states
- clear about mutual exclusivity
- clear about package composition
- clear about conditional requirements without relying on hidden formula webs

Pull presentation content from canonical and derived sheets. Do not restate business logic manually in guide tabs.

## Handle Conflicts Deliberately

When sources disagree:

1. Prefer canonical sheets if they already reflect an intentional normalized decision.
2. Otherwise compare the conflicting source rows and preserve provenance.
3. Log unresolved differences in `Audit Exceptions` or another audit sheet.
4. Avoid inventing unsupported rules, pricing, or availability logic.

## Avoid These Failure Modes

- Hardcoding business rules into guide tabs
- Duplicating the same logic across multiple presentation sheets
- Treating experimental sheets as authoritative when canonical tables already exist
- Spreading pricing logic across notes, comments, formatting, and manual overrides
- Creating new semi-processed tabs unless they clearly belong to the derived logic layer

## Target Outcome

Leave the workbook in a state that supports:

- maintainable order-guide generation by model, body, and trim
- future configurator or form logic
- repeatable model-year updates
- clear separation between source data, normalized data, logic, and presentation
