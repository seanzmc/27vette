# Canonical Schema RFC

Status: draft for human approval

Scope: Stingray CSV projection and future Corvette order-guide ingestion.

## Purpose

This RFC freezes the target canonical schema direction before additional migration or support passes. The goal is to model vehicle configuration cleanly by source provenance, option identity, context/status, presentation, pricing, and relationships.

Legacy production data remains the oracle for facts and parity. It is not the blueprint for the target schema. The compiler must emit legacy-compatible output for shadow parity, but the human-authored target schema should not copy legacy display duplicates, runtime shortcuts, or generated option IDs as business identity.

## Principles

- Preserve raw source evidence before interpretation.
- Classify duplicate RPOs before canonical emission.
- Model option identity separately from presentation.
- Model choice group behavior separately from option identity.
- Model business status separately from display role.
- Model base price separately from price overrides.
- Keep runtime/control-plane rows out of customer-selectable catalogs until intentionally modeled.
- Compile to legacy output for parity; do not optimize authoring tables around `form-app/data.js`.

## Final Source-Of-Truth Tables

### Raw/Staging

#### `source_documents.csv`

One row per source artifact.

Required columns:

- `source_document_id`
- `source_type`
- `model_year`
- `model_key`
- `vehicle_line`
- `source_name`
- `source_path`
- `source_checksum`
- `imported_at`
- `notes`

Allowed `source_type` values:

- `order_guide`
- `workbook`
- `manual_review`
- `production_oracle_export`

#### `source_rows.csv`

One row per raw source row. This table preserves original row order and raw values. It must not collapse duplicate RPOs.

Required columns:

- `source_row_id`
- `source_document_id`
- `source_sheet`
- `source_row_number`
- `source_order`
- `legacy_option_id`
- `rpo`
- `raw_label`
- `raw_description`
- `raw_section`
- `raw_category`
- `raw_step`
- `raw_price`
- `raw_status`
- `raw_selectable`
- `raw_detail`
- `raw_payload_json`
- `active`
- `notes`

#### `source_row_classifications.csv`

One row per reviewed source row classification.

Required columns:

- `source_row_id`
- `classification`
- `canonical_option_id`
- `presentation_id`
- `control_plane_reference_id`
- `relationship_id`
- `review_status`
- `review_reason`
- `active`
- `notes`

Allowed `classification` values:

- `customer_choice`
- `display_only_duplicate`
- `standard_equipment_display`
- `included_display`
- `package_display`
- `package_source`
- `relationship_source`
- `price_rule_source`
- `replacement_default_source`
- `control_plane_reference`
- `ambiguous_requires_review`
- `ignore_not_stingray`

Allowed `review_status` values:

- `unreviewed`
- `reviewed`
- `blocked`

### Canonical Option Identity

#### `canonical_options.csv`

One row per real business option identity where appropriate.

Required columns:

- `canonical_option_id`
- `rpo`
- `label`
- `description`
- `canonical_kind`
- `duplicate_rpo_classification`
- `active`
- `notes`

Allowed `canonical_kind` values:

- `customer_choice`
- `equipment_feature`
- `package`
- `structured_reference`
- `review_required`

Allowed `duplicate_rpo_classification` values:

- `none`
- `display_only_duplicate`
- `true_separate_selectable_variant`
- `mixed_display_and_selectable_variants`
- `ambiguous_requires_review`

Rules:

- `display_only` is not a `canonical_kind`.
- Duplicate RPOs require explicit classification before projection.
- Complex duplicate RPOs such as `AE4`, `AH2`, `AQ9`, and `UQT` must not be auto-collapsed.

#### `canonical_option_aliases.csv`

Maps source and legacy identifiers to canonical options without making legacy IDs business identity.

Required columns:

- `alias_id`
- `canonical_option_id`
- `source_row_id`
- `alias_type`
- `alias_value`
- `legacy_option_id`
- `active`
- `notes`

Allowed `alias_type` values:

- `legacy_option_id`
- `source_option_id`
- `rpo`
- `marketing_label`
- `workbook_row_key`

### Presentation/Display

#### `option_presentations.csv`

One canonical option can appear in multiple surfaces.

Required columns:

- `presentation_id`
- `canonical_option_id`
- `legacy_option_id`
- `rpo_override`
- `presentation_role`
- `choice_group_id`
- `section_id`
- `section_name`
- `category_id`
- `category_name`
- `step_key`
- `choice_mode`
- `selection_mode`
- `selection_mode_label`
- `display_order`
- `selectable`
- `active`
- `label`
- `description`
- `source_detail_raw`
- `notes`

Allowed `presentation_role` values:

- `customer_choice`
- `standard_options_display`
- `standard_equipment_display`
- `included_display`
- `package_display`
- `legacy_alias`

Rules:

- Display-only Standard Options and Standard Equipment rows are presentations, not fake customer-selectable options.
- `display_only` is a selection/presentation behavior, not a business status.

### Context And Status

#### `context_scopes.csv`

Reusable predicates for status, availability, pricing, and relationships.

Required columns:

- `context_scope_id`
- `model_year`
- `model_key`
- `variant_id`
- `body_style`
- `trim_level`
- `condition_set_id`
- `priority`
- `active`
- `notes`

#### `option_status_rules.csv`

Resolves canonical option or presentation status by context.

Required columns:

- `status_rule_id`
- `canonical_option_id`
- `presentation_id`
- `context_scope_id`
- `status`
- `status_label`
- `priority`
- `active`
- `notes`

Allowed `status` values:

- `optional`
- `standard_choice`
- `standard_fixed`
- `included_auto`
- `unavailable`

Rules:

- Exactly one of `canonical_option_id` or `presentation_id` is preferred. A presentation-specific rule overrides a canonical rule.
- `display_only` must never be emitted as a business status.

### Choice Groups

#### `choice_groups.csv`

Defines group behavior such as Wheels, Caliper Color, Paint, Seats, Seat Belts, Roof, and Packages independently from option identity.

Required columns:

- `choice_group_id`
- `group_key`
- `label`
- `section_id`
- `section_name`
- `category_id`
- `category_name`
- `step_key`
- `choice_group_type`
- `min_selected`
- `max_selected`
- `default_policy`
- `active`
- `notes`

Allowed `choice_group_type` values:

- `single_required`
- `single_optional`
- `multi_optional`
- `multi_required`
- `display_only`

Allowed `default_policy` values:

- `none`
- `status_standard_choice`
- `explicit_default_rule`
- `production_runtime_preserved`

#### `choice_group_presentations.csv`

Membership and ordering for presentations inside a choice group.

Required columns:

- `choice_group_id`
- `presentation_id`
- `display_order`
- `active`
- `notes`

### Canonical Pricing

#### `canonical_base_prices.csv`

Base price by canonical option or presentation, scoped by context. Price overrides remain separate.

Required columns:

- `canonical_base_price_id`
- `price_book_id`
- `canonical_option_id`
- `presentation_id`
- `context_scope_id`
- `amount_usd`
- `priority`
- `active`
- `notes`

Rules:

- Exactly one of `canonical_option_id` or `presentation_id` is required.
- Presentation-specific base prices override canonical-option base prices.
- Existing legacy exact selectable base prices may take precedence during transition, but final authoring should use canonical targets.

#### `price_books.csv`

Required columns:

- `price_book_id`
- `model_year`
- `model_key`
- `currency`
- `active`
- `notes`

### Simple Relationships

#### `simple_dependency_rules.csv`

Narrow authoring table for simple unscoped projected selectable-to-selectable excludes/requires.

Required columns:

- `rule_id`
- `rule_type`
- `source_presentation_id`
- `target_presentation_id`
- `violation_behavior`
- `message`
- `priority`
- `active`
- `notes`

Allowed `rule_type` values:

- `excludes`
- `requires`

Allowed `violation_behavior` values:

- `disable_and_block`
- `require_and_block`

Rules:

- Only unscoped simple choice-to-choice rules belong here.
- Do not use this table for packages, price rules, replacement/default behavior, non-selectable references, runtime/control-plane rows, or context-scoped rules.

### Requires-Any Groups

#### `requires_any_groups.csv`

Required columns:

- `requires_any_group_id`
- `source_presentation_id`
- `message`
- `priority`
- `active`
- `notes`

#### `requires_any_group_members.csv`

Required columns:

- `requires_any_group_id`
- `target_presentation_id`
- `member_order`
- `active`
- `notes`

### Package Includes

#### `package_includes.csv`

Models package source to included target behavior.

Required columns:

- `package_include_id`
- `source_presentation_id`
- `target_presentation_id`
- `include_behavior`
- `target_price_policy_id`
- `context_scope_id`
- `priority`
- `active`
- `notes`

Allowed `include_behavior` values:

- `auto_add`
- `included_display_only`
- `requires_manual_selection`

### Replacement/Default Rules

#### `replacement_default_rules.csv`

Models default and replacement behavior explicitly.

Required columns:

- `replacement_default_rule_id`
- `choice_group_id`
- `trigger_presentation_id`
- `target_presentation_id`
- `rule_behavior`
- `context_scope_id`
- `priority`
- `active`
- `notes`

Allowed `rule_behavior` values:

- `default_select`
- `replace_default`
- `replace_selected`
- `suppress_default`
- `runtime_preserved`

### Price Rules

#### `price_rules.csv`

Price overrides and conditional price behavior.

Required columns:

- `price_rule_id`
- `price_book_id`
- `condition_presentation_id`
- `target_canonical_option_id`
- `target_presentation_id`
- `context_scope_id`
- `price_action`
- `amount_usd`
- `stack_mode`
- `priority`
- `active`
- `notes`

Allowed `price_action` values:

- `set_static`
- `force_zero`
- `add_delta`

Allowed `stack_mode` values:

- `exclusive`
- `stack`
- `stop_after_apply`

### Control-Plane References

#### `control_plane_references.csv`

Explicit namespace for non-selectable, hidden, runtime-only, or structured references.

Required columns:

- `control_plane_reference_id`
- `legacy_option_id`
- `rpo`
- `reference_type`
- `legacy_section_id`
- `legacy_selection_mode`
- `active`
- `notes`

Allowed `reference_type` values:

- `non_selectable_reference`
- `runtime_only`
- `structured_reference`
- `guarded_legacy_option`
- `production_preserved`

Rules:

- Control-plane references are not customer-selectable options.
- They may participate in advanced relationships only after intentionally modeled.

## Transitional Legacy-Shaped Tables

These tables remain valid during transition because they already hold migrated lanes. They should not be the default path for new customer-facing sections.

- `catalog/selectables.csv`: transitional source; eventually compiler output from canonical options and presentations.
- `ui/selectable_display.csv`: transitional source; eventually compiler output from presentations and choice groups.
- `pricing/base_prices.csv`: transitional source; eventually compiler output or retired in favor of canonical base prices.
- `logic/dependency_rules.csv`: transitional normalized source; eventually compiler output for simple rules, still possible advanced authoring until replacement tables exist.
- `logic/condition_sets.csv`: transitional normalized source; eventually compiler output for common predicates.
- `logic/condition_terms.csv`: transitional normalized source; eventually compiler output.
- `logic/auto_adds.csv`: transitional source for package includes; eventually replaced by `package_includes.csv`.
- `logic/rule_groups.csv` and `logic/rule_group_members.csv`: transitional source; eventually replaced by `requires_any_groups.csv`.
- `logic/exclusive_groups.csv` and `logic/exclusive_group_members.csv`: transitional source; eventually replaced by choice groups.
- `catalog/item_sets.csv` and `catalog/item_set_members.csv`: transitional helper source; eventually compiler output or replaced by choice groups and relationship groups.

Planned fate: compile canonical tables into equivalent legacy-shaped tables until cutover is approved. Do not churn already migrated old-style rows solely to reduce counts.

## Compiler/Generated Outputs

The compiler must emit legacy-compatible artifacts for shadow parity:

- `legacy_choices`
- `legacy_rules`
- `legacy_priceRules`
- `legacy_ruleGroups`
- `legacy_exclusiveGroups`
- `legacy_variants`

Generated outputs may be JSON or CSV, but they must preserve the production-shaped contract consumed by the shadow overlay. They are not human-authored source-of-truth.

Output contracts:

- `choices.option_id` remains the legacy option ID for compatibility.
- Canonical-managed duplicate RPOs must emit every production legacy option ID required for parity.
- Display-only presentations emit with `selectable=False`, `choice_mode=display`, and `selection_mode=display_only`.
- Business statuses emit as legacy status values:
  - `optional` -> `available`
  - `standard_choice` -> `standard`
  - `standard_fixed` -> `standard`
  - `included_auto` -> `available` plus locked/included selection behavior where applicable
  - `unavailable` -> `unavailable`
- Price output must distinguish base price from price overrides.
- Runtime/control-plane references must not appear as customer-selectable choices unless explicitly modeled as presentations.

## Validation/Audit-Only Tables

These remain validation and audit surfaces, not final business source-of-truth:

- `validation/projected_slice_ownership.csv`
- `validation/non_selectable_references.csv`
- `validation/golden_builds.csv`
- `validation/golden_build_selections.csv`
- `validation/golden_expected_lines.csv`
- `validation/golden_expected_conflicts.csv`
- `validation/golden_expected_requirements.csv`
- production inventory report artifacts
- preserved-boundary/census artifacts

## Context/Status Cascade

Status and pricing scopes resolve from broad to specific:

1. model/year default
2. variant override
3. body override
4. trim override
5. explicit option or presentation override

Precedence sort:

1. presentation-specific target over canonical-option target
2. higher scope specificity
3. higher priority
4. deterministic row ID tie-break

Rules apply after context/status resolution:

- `unavailable` choices cannot be valid explicit selections.
- `standard_choice` can satisfy required choice groups.
- `standard_fixed` emits as standard equipment and should not become selectable unless the presentation is explicitly selectable.
- `included_auto` is locked/included because a modeled package/include relationship caused it.
- `optional` is selectable when presentation role and choice group behavior allow it.

## Duplicate-RPO Classification Rules

Every duplicate RPO must be classified before projection.

Classification rules:

- `display_only_duplicate`: one real customer choice plus one or more Standard Options/Standard Equipment display-only rows.
- `true_separate_selectable_variant`: multiple selectable rows with the same RPO that represent distinct selectable variants, contexts, or interiors.
- `mixed_display_and_selectable_variants`: both display rows and multiple real selectable variants.
- `ambiguous_requires_review`: any duplicate pattern that cannot be classified mechanically.

Hard rule: do not automatically collapse complex duplicate RPOs such as `AE4`, `AH2`, `AQ9`, or `UQT`.

## Importer Requirements

Importer/staging work must:

- preserve raw source rows and source order
- preserve source provenance and raw payloads
- preserve duplicate RPO rows before classification
- classify rows before canonical emission
- emit canonical options only for reviewed business identities
- emit presentations for every display/customer surface
- emit aliases for legacy/source identifiers
- emit choice group membership separately from presentation identity
- emit package, price, replacement/default, and runtime/control-plane relationships into their own tables
- fail closed on ambiguous duplicate RPOs
- never create fake selectable rows for Standard Options or Standard Equipment display-only duplicates

## Relationship Taxonomy

Relationship classes:

- `simple_excludes`: unscoped customer choice excludes customer choice.
- `simple_requires`: unscoped customer choice requires customer choice.
- `requires_any`: source requires one member from a target member set.
- `choice_group_exclusivity`: required/single/multi choice behavior.
- `package_include`: package source includes or auto-adds target.
- `price_override`: condition modifies target price.
- `replacement_default`: default selection and replacement behavior.
- `control_plane_reference`: hidden, runtime-only, structured, or guarded references.

Relationship authoring rules:

- Use flat simple authoring only for unscoped projected choice-to-choice excludes/requires.
- Use package tables for includes and auto-adds.
- Use price tables for price behavior.
- Use replacement/default tables for runtime selection behavior.
- Keep control-plane references outside customer-selectable catalogs.

## Migration Strategy From Current Mixed State

Current old-style projected rows remain valid transitional source. The project should stop adding new customer-facing sections to old `selectables.csv`/`selectable_display.csv` by default.

Recommended migration pattern:

1. Freeze final schema contracts.
2. Add optional loaders and validation for final tables with header-only parity.
3. Add compiler support using temp fixtures.
4. Pick one small canonical-first lane.
5. Prove emitted legacy parity and shadow overlay parity.
6. Leave already migrated old-style lanes alone until their entire lane can move cleanly.

Do not run tactical option-lane migrations until the relevant canonical table support exists and the lane can be represented without fake duplicate selectables.

## Explicit Non-Goals

- No production runtime cutover.
- No generated `form-app/data.js` rewrite.
- No workbook mutation.
- No interior duplicate collapse without explicit review.
- No automatic collapse of `AE4`, `AH2`, `AQ9`, or `UQT`.
- No package/default/runtime behavior squeezed into simple dependency rules.
- No relationship migration before source and endpoint identity are modeled.
- No tactical lane migration recommendations from this RFC.

## Stop Doing List

- Stop treating legacy option IDs as canonical business identity.
- Stop modeling Standard Options display duplicates as fake customer-selectable options.
- Stop adding new customer-facing sections to legacy-shaped tables by default.
- Stop hand-authoring condition sets for simple selected-target rules when flat authoring applies.
- Stop migrating individual edges without a lane-level model.
- Stop using `display_only` as a business status.
- Stop letting hidden/runtime/control-plane rows leak into customer-selectable catalogs.
- Stop optimizing source schema around the legacy `form-app/data.js` shape.

## Open Questions Requiring Human Approval

1. Should `context_scopes.csv` support one row with multiple fields only, or also explicit boolean expression references beyond `condition_set_id`?
2. Should final simple dependency rules target `presentation_id` only, or allow canonical-option targets when all active presentations should inherit the rule?
3. Should package includes target presentations or canonical options by default?
4. Should `standard_choice` be allowed on non-selectable presentations, or should non-selectable standard rows always use `standard_fixed`?
5. Should display order live only in `choice_group_presentations.csv`, or also remain denormalized in `option_presentations.csv` for easier authoring?
6. Should `canonical_base_prices.csv` use `context_scope_id` only, or keep direct scope columns for authoring simplicity?
7. What is the first canonical-first lane after support contracts are approved: Calipers, a small duplicate-free lane, or a staging-only importer pilot?
8. When should transitional old-style lanes be converted: opportunistically by lane, or only after a full model-wide compiler can emit all legacy rows?
9. Should ownership move from RPO-based rows to canonical/presentation scoped rows before or after the first canonical-first lane?

## Next Pass Recommendation

Pass 211 should be report-only approval/editing of this RFC if needed, or support-only raw/staging and duplicate-classification loaders if the RFC is accepted as written. It should not migrate rows or project a tactical option lane.
