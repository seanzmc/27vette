# Pass 2 — Normalized ingest contract

Date: 2026-06-19
Branch: `schema-ingestion-normalization`
Status: Docs-only contract. No workbook/code/runtime implementation in this pass.

## Purpose

Define the standing contract for raw GM order-guide ingest and new-model schema normalization after the Pass 1 inventory.

This document replaces the old implicit staging-sheet mental model with a workbook-first process:

```text
official raw source
  -> transient parse/provenance artifacts
  -> candidate normalized rows + unresolved review report
  -> human/product review
  -> approved canonical workbook source sheets
  -> generate_form.py --model <model>
  -> generate_registry.py when promoted runtime data changes
  -> static app runtime
```

## User decisions incorporated

1. `Order-Guide_IngestPrompt.md` should be kept, but it is stale and needs to be rewritten around this normalized contract.
2. `docs/workbook-sheet-index.md` is stale and can be archived instead of refreshed as part of the ingest path.
3. Existing ZR1/ZR1X workbook source references should be retired/reprocessed before they are used to test the new ingest function. New ingest tests should run against a cleaner ZR1/ZR1X space rather than treating current scaffold rows as canonical truth.

## Operating boundary

Raw ingest is an edge workflow.

Use raw ingest only for:

- adding a model not already in the form;
- performing a broad GM/order-guide refresh across existing models;
- rebuilding a large source surface when the upstream order guide materially changes.

Do not use raw ingest for:

- routine row-level option fixes;
- small copy/pricing/rule corrections;
- runtime presentation polish;
- generated artifact repair;
- promotion of a model to the live registry.

Routine corrections should be made in canonical workbook source sheets, then regenerated and validated.

## Source-of-truth boundaries

| Layer | Owns | Does not own |
|---|---|---|
| Raw ingest | source extraction, row conservation, source spans, raw statuses, footnote capture, candidate IDs/sections/prices, unresolved review flags | approved product decisions or live workbook mutation |
| Review artifacts | human decision queue for ambiguous candidates | permanent source of runtime truth |
| Workbook source sheets | approved product data, schema, options, variant statuses, rules, prices, interiors, assets, runtime metadata | generated-only rows or unreviewed raw guesses |
| Generators | reading workbook rows, validating references, normalizing/emitting artifacts | hidden model/RPO-specific product knowledge when workbook rows can express it |
| Runtime | generic rendering/evaluation of generated contracts | order-guide parsing or Corvette product inference |

## Canonical target families

Future ingest code should land approved data in the existing workbook source graph. Do not add a permanent parallel staging taxonomy unless a spec proves these families cannot represent the data.

### 1. Model metadata

Canonical sheets:

- `model_master`
- `variant_master`
- `model_variants`
- `model_workbook_sources`
- `model_registry_promotion`

Required responsibilities:

| Sheet | Ingest responsibility |
|---|---|
| `model_master` | model key, runtime registry key, label/year, dataset/export slug, expected variant count, active/default flags |
| `variant_master` | canonical variant IDs, body style, trim, base price, display order, active flag |
| `model_variants` | model-to-variant membership and model-specific display order |
| `model_workbook_sources` | model-to-source-sheet registry by source role |
| `model_registry_promotion` | runtime promotion metadata only after separate promotion approval |

Rules:

- New models start inactive and unpromoted unless explicitly approved otherwise.
- Runtime promotion is a separate pass from raw ingest.
- Do not infer promotion from the presence of source sheets.
- Preserve registry-key conventions, including `grand_sport` -> `grandSport`.

### 2. Option universe

Canonical sheets:

- `stingray_options` / `<model>_options`
- `stingray_ovs` / `<model>_ovs`

Required option columns:

| Column | Contract |
|---|---|
| `option_id` | stable workbook/runtime join key |
| `rpo` | text RPO, including numeric-looking codes |
| `price` | numeric price, explicit zero, or blank unknown/not priced |
| `option_name` | approved customer-facing card/name text |
| `description` | approved customer-facing description |
| `detail_raw` | source detail/provenance text that is safe to carry in source rows |
| `section_id` | workbook-owned placement into `section_master` |
| `selectable` | real Excel boolean where schema gates require it |
| `display_order` | numeric order within section/model |
| `active` | real Excel boolean row activation |
| `display_behavior` | approved presentation behavior such as blank/default/display-only/auto-only/hidden |

Required OVS columns:

| Column | Contract |
|---|---|
| `option_id` | references canonical option row |
| `variant_id` | references canonical model variant |
| `status` | normalized availability: `standard`, `available`, or `unavailable` |

Rules:

- Raw symbols such as `S`, `A`, `--`, `D`, `A/D`, `■`, and `□` are parse evidence, not direct canonical OVS values.
- Preserve raw symbols in transient artifacts so information is not lost.
- Convert to canonical OVS values only after recording review flags for nuance such as equipment-group membership or ADI availability.
- Do not mint RPOs, option IDs, prices, or section IDs when the source is ambiguous.

### 3. Rules and relationships

Canonical sheets:

- `rule_mapping` / `<model>_rule_mapping`
- `rule_groups` / `<model>_rule_groups`
- `rule_group_members` / `<model>_rule_group_members`
- `exclusive_groups` / `<model>_exclusive_groups`
- `exclusive_group_members` / `<model>_exclusive_members`
- `default_selection_rules`
- `runtime_rule_exceptions` only when canonical rules/groups cannot express the behavior

Direct rule contract:

| Column | Contract |
|---|---|
| `rule_id` | stable unique rule key |
| `source_id` | source option/interior/etc. ID |
| `rule_type` | canonical direct relationship, currently includes/includes-like, requires, excludes |
| `target_id` | target option/interior/etc. ID |
| `original_detail_raw` | source evidence when useful and not a stale process note |
| `body_style_scope` | body-style condition when consumed |
| `runtime_action` | retained only for proven default/replacement semantics |
| `disabled_reason` | runtime-facing reason only when intentionally workbook-authored |

Grouped rule contract:

| Family | Contract |
|---|---|
| `*_rule_groups` | parent group ID, group type, source, optional scopes, active state |
| `*_rule_group_members` | group-to-target members with display order and active state |
| `*_exclusive_groups` | mutually exclusive/required-exclusive group definitions |
| `*_exclusive_members` | group-to-option members with display order and active state |

Rules:

- Prefer exclusive groups for peer replacement.
- Prefer `requires_any` / `excludes_any` group shapes for grouped dependencies/conflicts.
- Do not preserve dead duplicate direct excludes as lifecycle rows.
- Do not add RPO-specific runtime JS when workbook rules can represent the behavior.

### 4. Pricing

Canonical sheets/surfaces:

- direct `price` in option sheets
- `<model>_price_rules`
- `PriceRef`
- `interior_components`

Price-rule contract:

| Column | Contract |
|---|---|
| `price_rule_id` | stable unique price-rule key |
| `condition_option_id` | selected/source condition |
| `price_rule_type` | currently `override` where used |
| `target_option_id` | priced target option |
| `price_value` | numeric override value |
| `body_style_scope` | optional body condition |
| `trim_level_scope` | optional trim condition |
| `notes` | durable explanation only; no pass/process language |

Rules:

- Preserve blank-vs-zero semantics.
- Do not choose a price when raw source price candidates are ambiguous.
- Do not restore standard-equipment prices as selectable option prices.
- Use `PriceRef` / `interior_components` for interior component pricing instead of forcing sums in option rows.

### 5. Interiors, color, and components

Canonical sheets:

- `lt_interiors`
- `LZ_Interiors`
- `model_interior_scope`
- `interior_components`
- `color_overrides`
- `PriceRef`

Rules:

- Do not force Color and Trim order-guide tabs into option rows if they belong to interiors/color override processing.
- Use `model_interior_scope` and `interior_components` for model/interior-specific ownership.
- Keep LT and LZ interior schemas aligned unless a separate approved schema pass changes them.
- Do not delete component rows to make visual price sums match; component rows and interior total prices have separate owners.

### 6. Presentation and runtime metadata

Canonical sheets:

- `section_master`
- `section_presentation`
- `runtime_steps`
- `context_section_master`
- `context_choice_copy`
- `order_summary_sections`
- `step_order_summary_map`
- `asset_map`

Rules:

- Runtime labels, section grouping, standard-equipment grouping, order-summary metadata, and card/media URLs should be workbook-owned when possible.
- Images stay as hosted URLs in workbook metadata; local source image folders are not runtime bundles.
- Raw order-guide parsing should not bypass presentation metadata already owned by the workbook.

## Transient ingest artifacts

A future ingest implementation should emit run-scoped artifacts before any workbook write. Keep evidence artifacts separate from later candidate-normalizer artifacts so Pass 0 cannot be mistaken for an apply-ready ingest.

Pass 0 evidence-profiler artifact families:

```text
form-output/ingest/<run-id>/source-layout.json
form-output/ingest/<run-id>/variant-matrix.json
form-output/ingest/<run-id>/raw-rows.json
form-output/ingest/<run-id>/disclosure-links.json
form-output/ingest/<run-id>/checkpoint-report.md
```

Later candidate-normalizer artifact families:

```text
form-output/ingest/<run-id>/candidate-options.json
form-output/ingest/<run-id>/candidate-ovs.json
form-output/ingest/<run-id>/candidate-rules.json
form-output/ingest/<run-id>/candidate-price-rules.json
form-output/ingest/<run-id>/unresolved-review.md
```

These are evidence/candidate artifacts, not source of truth. They may be regenerated or discarded after canonical workbook rows are approved and applied.

Required parse invariants:

- row conservation by source tab;
- source-sheet/source-span provenance for every candidate row;
- no fabricated RPOs;
- no primary RPO longer than the valid source token permits;
- complete variant-header parsing;
- raw status preservation before normalization;
- normalized status vocabulary limited to canonical OVS values plus explicit unresolved flags;
- footnote marker integrity;
- price ambiguity preserved instead of guessed.

## ZR1/ZR1X clean-space rule

Current ZR1/ZR1X workbook rows are inactive future scaffolds and should not be treated as canonical examples for a new ingest implementation.

For future ingest work:

- retire or isolate current ZR1/ZR1X references before using them as test targets;
- test the ingest parser on clean synthetic fixtures and/or a fresh official raw export;
- keep existing ZR1/ZR1X runtime promotion disabled until a separate approval pass;
- do not let current scaffold row counts become validator truth;
- preserve useful IDs only if a reprocess spec proves they are still correct against official source data.

This is intentionally stricter than normal active-model maintenance because the goal is to validate the new ingest function in a clean space.

## Allowed implementation sequence

### Pass 0 — CLI evidence profiler

Spec first. Candidate goal: parse a raw GM export into evidence artifacts only:

- source layout and exact source cell coordinates;
- variant matrix reconciliation, including combined-model tabs such as `ZR1 and ZR1X`;
- raw rows/status cells with disclosure markers preserved;
- disclosure links and checkpoint reporting.

Must not:

- write `stingray_master.xlsx`;
- emit candidate workbook rows as approved decisions;
- regenerate model artifacts;
- promote models;
- rely on current ZR1/ZR1X workbook rows as expected output.

### Pass 1 — Candidate normalizer

Spec first. Candidate goal: convert proven evidence artifacts into reviewable candidate families such as option, OVS, rule, price-rule, interior/color/component, section/presentation, and unresolved-review artifacts.

Candidate rows remain transient. They are not canonical workbook rows and cannot be applied without later review/approval.

### Pass 2 — Review UI / interactive wizard

Spec first. Candidate goal: help a human/product reviewer approve, edit, skip, or mark unresolved candidate rows while showing exact raw source evidence, current workbook context, detail disclosures, and variant-matrix context.

Prefer reusing the workbook editor metadata/API patterns rather than creating a parallel workbook schema map.

### Pass 3 — Controlled canonical apply

Spec first. Candidate goal: convert approved candidate rows into canonical workbook edits.

Requirements:

- dry-run default;
- `--write` required for mutation;
- safe-save only;
- stable-key joins, not stale row numbers;
- preserve existing workbook-authored values when incoming candidate fields are blank;
- verify workbook on disk;
- regenerate and gate only after canonical rows are applied.

## Non-goals

- No workbook writes in this docs pass.
- No generated artifact edits in this docs pass.
- No `form-app` runtime edits in this docs pass.
- No dealer submission changes.
- No dependency additions.
- No resurrection of `future_model_source_review` or `future_model_option_review` as permanent source sheets.
- No routine-maintenance dependency on raw ingest.

## Validation for this docs pass

```sh
git diff --check -- docs/ingest Order-Guide_IngestPrompt.md README.md docs/archive/workbook-sheet-index-2026-06-12.md
```

Also search the rewritten active prompt and README for stale staging-sheet language. Historical/retirement mentions in `docs/ingest/pass-1/` and this contract are allowed when they explain what not to revive.

Expected result: docs-only changes. No workbook/generator/runtime gates are required because this pass does not change executable behavior.
