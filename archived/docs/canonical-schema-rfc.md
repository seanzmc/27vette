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

## Current Support vs Final Schema

The repository already has optional support for several canonical-adjacent CSV files. Those current files are compatibility contracts for the shadow compiler, not approved final schema contracts. Do not treat their current headers as final just because the filenames overlap with this RFC.

Current implemented optional tables:

- `catalog/canonical_options.csv`
  - Current header: `canonical_option_id,rpo,label,description,canonical_kind,active,notes`
  - Current enums: `canonical_kind` allows `customer_choice`, `equipment_feature`, `structured_reference`, `review_required`
  - Final direction: add duplicate-RPO review linkage/classification, support `package`, and keep business identity separate from legacy display aliases.
  - Status: transitional compatibility contract.
- `ui/option_presentations.csv`
  - Current header: `presentation_id,canonical_option_id,legacy_option_id,rpo_override,presentation_role,section_id,section_name,category_id,category_name,step_key,choice_mode,selection_mode,selection_mode_label,display_order,selectable,active,label,description,source_detail_raw,notes`
  - Current enums: `presentation_role` allows `choice`, `standard_options_display`, `standard_equipment_display`, `included_display`, `package_display`, `legacy_alias`, `display_only`
  - Final direction: use canonical presentation roles such as `customer_choice`, preserve display-only rows as presentations, and split canonical authoring fields from legacy output compatibility fields.
  - Status: transitional compatibility contract.
- `logic/option_status_rules.csv`
  - Current header: `status_rule_id,canonical_option_id,presentation_id,scope_model_year,scope_body_style,scope_trim_level,scope_variant_id,condition_set_id,status,status_label,priority,active,notes`
  - Current enums: `status` allows `optional`, `standard_choice`, `standard_fixed`, `included_auto`, `unavailable`
  - Final direction: status should resolve through reusable `context_scopes.csv` unless direct scope columns are explicitly approved for final authoring.
  - Status: transitional compatibility contract.
- `pricing/canonical_base_prices.csv`
  - Current header: `canonical_base_price_id,price_book_id,canonical_option_id,presentation_id,scope_condition_set_id,amount_usd,priority,active,notes`
  - Final direction: pricing should target exactly one canonical option or presentation and use final `context_scope_id` scoping. Current `scope_condition_set_id` is transitional compatibility only.
  - Status: transitional compatibility contract.
- `logic/simple_dependency_rules.csv`
  - Current header: `rule_id,rule_type,source_option_id,target_option_id,violation_behavior,message,priority,active`
  - Current semantics: unscoped active projected selectable-to-selectable `excludes`/`requires`, generating selected-target condition sets and normalized dependency rows.
  - Final direction: simple relationships should target final presentation identity unless canonical-target inheritance is explicitly approved.
  - Status: transitional compatibility contract.

Approved transition strategy: introduce a new final canonical namespace under `data/stingray/canonical/` while keeping current optional files as transitional compatibility bridges.

Final-schema support must not mutate the current optional file headers or enum contracts in place. Any pass that changes current optional file behavior must be support-only and prove header-only/current-data parity. New final-schema loaders and validators should target `data/stingray/canonical/...`, not the current transitional paths.

Current transitional compatibility bridge paths:

- `data/stingray/catalog/canonical_options.csv`
- `data/stingray/ui/option_presentations.csv`
- `data/stingray/logic/option_status_rules.csv`
- `data/stingray/pricing/canonical_base_prices.csv`
- `data/stingray/logic/simple_dependency_rules.csv`

## Final Path Convention

Final source-of-truth tables live under `data/stingray/canonical/`:

- `canonical/source/source_documents.csv`
- `canonical/source/source_rows.csv`
- `canonical/source/source_row_classifications.csv`
- `canonical/options/duplicate_rpo_reviews.csv`
- `canonical/options/canonical_options.csv`
- `canonical/options/canonical_option_aliases.csv`
- `canonical/options/control_plane_references.csv`
- `canonical/presentation/option_presentations.csv`
- `canonical/presentation/choice_groups.csv`
- `canonical/presentation/choice_group_presentations.csv`
- `canonical/status/variants.csv`
- `canonical/status/context_scopes.csv`
- `canonical/status/option_status_rules.csv`
- `canonical/pricing/price_books.csv`
- `canonical/pricing/canonical_base_prices.csv`
- `canonical/pricing/price_rules.csv`
- `canonical/relationships/simple_dependency_rules.csv`
- `canonical/relationships/requires_any_groups.csv`
- `canonical/relationships/requires_any_group_members.csv`
- `canonical/relationships/package_includes.csv`
- `canonical/relationships/replacement_default_rules.csv`
- `canonical/ownership/projection_ownership.csv`
- `canonical/ownership/preserved_boundaries.csv`

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
- `source_vehicle_line`
- `source_model_line`
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
- `source_section_path`
- `source_order_path`
- `source_option_key`
- `raw_row_hash`
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
- `relationship_type`
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

Rules:

- `relationship_type` is required when `relationship_id` is populated so package, price, rule, replacement/default, and control-plane namespaces cannot collide.
- `source_row_id` plus `raw_row_hash` must provide stable identity for repeated imports and diffing.

### Canonical Option Identity

#### `duplicate_rpo_reviews.csv`

One durable RPO-level review row per duplicate-RPO decision. This table records the reviewed decision before canonical options or presentations are emitted.

Required columns:

- `duplicate_rpo_review_id`
- `rpo`
- `model_year`
- `model_key`
- `source_row_ids`
- `duplicate_rpo_classification`
- `decision_reason`
- `review_status`
- `reviewed_by`
- `reviewed_at`
- `active`
- `notes`

Allowed `duplicate_rpo_classification` values:

- `display_only_duplicate`
- `true_separate_selectable_variant`
- `mixed_display_and_selectable_variants`
- `ambiguous_requires_review`

Allowed `review_status` values:

- `unreviewed`
- `reviewed`
- `blocked`

Rules:

- Duplicate RPOs require an active reviewed row before projection unless the importer can prove the RPO is not duplicated in the active source set.
- `canonical_options.csv` may repeat the classification for local readability, but the durable RPO-level decision lives here.
- Complex duplicate RPOs such as `AE4`, `AH2`, `AQ9`, and `UQT` must remain `ambiguous_requires_review` until explicitly approved.

#### `canonical_options.csv`

One row per real business option identity where appropriate.

Required columns:

- `canonical_option_id`
- `rpo`
- `duplicate_rpo_review_id`
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

Final canonical authoring columns:

- `presentation_id`
- `canonical_option_id`
- `rpo_override`
- `presentation_role`
- `choice_group_id`
- `section_id`
- `section_name`
- `category_id`
- `category_name`
- `step_key`
- `selection_mode`
- `display_order`
- `selectable`
- `active`
- `label`
- `description`
- `source_detail_raw`
- `notes`

Compatibility/output columns:

- `legacy_option_id`
- `choice_mode`
- `selection_mode_label`

Rules for compatibility/output columns:

- `legacy_option_id` remains required while the compiler must emit legacy-compatible `choices.option_id`, but it is not business identity.
- `choice_mode` is a legacy output compatibility field unless final choice-group support explicitly adopts it as authoring syntax.
- `selection_mode_label` is legacy/display output metadata unless a later UI-copy contract explicitly makes it author-authored canonical copy.
- Final presentation authoring should derive choice behavior from `choice_groups.csv` and membership, not from duplicated legacy mode fields.

Allowed `presentation_role` values:

- `customer_choice`
- `standard_options_display`
- `standard_equipment_display`
- `included_display`
- `package_display`
- `legacy_alias`
- `display_only`

Rules:

- Display-only Standard Options and Standard Equipment rows are presentations, not fake customer-selectable options.
- Use surface-specific display roles when known. Use `display_only` only when the source row is known to be display-only but the display surface still needs review.
- `display_only` is a presentation role, not a business status.

### Context And Status

#### `variants.csv`

Canonical registry of supported Corvette build contexts.

Final path: `data/stingray/canonical/status/variants.csv`

Required columns:

- `variant_id`
- `model_year`
- `gm_model_code`
- `model_key`
- `body_style`
- `trim_level`
- `active`
- `notes`

Rules:

- `variant_id` is the atomic build context.
- `variant_id` is intentionally constructed as `<trim>_<model/body-code>`, for example `2lt_c67`, `1lz_h07`, and `3lz_s67`.
- `variant_id` determines `model_key`, `body_style`, and `trim_level` through this registry.
- `gm_model_code` is the GM Corvette model/body code:
  - `C07` / `C67`: Stingray coupe / convertible
  - `E07` / `E67`: Grand Sport coupe / convertible
  - `H07` / `H67`: Z06 coupe / convertible
  - `R07` / `R67`: ZR1 coupe / convertible
  - `S07` / `S67`: ZR1X coupe / convertible
- Trim conventions:
  - Stingray and Grand Sport use `1LT`, `2LT`, `3LT`.
  - Z06 uses `1LZ`, `2LZ`, `3LZ`.
  - ZR1 and ZR1X use `1LZ`, `3LZ`.

Validation:

- Unknown or malformed `gm_model_code` values fail.
- Malformed `variant_id` values fail if they do not match the trim plus GM model/body-code convention.
- `variant_id` values whose trim or model/body-code component contradicts `trim_level` or `gm_model_code` fail.
- Duplicate active `variant_id` values fail.

#### `context_scopes.csv`

Reusable vehicle/build predicates for status, availability, pricing, and relationships.

Final path: `data/stingray/canonical/status/context_scopes.csv`

Required columns:

- `context_scope_id`
- `model_year`
- `model_key`
- `variant_id`
- `body_style`
- `trim_level`
- `priority`
- `active`
- `notes`

Rules:

- Empty context fields mean "all" within the enclosing table target.
- `model_year` and `model_key` are required for active production rows once multi-model data exists.
- `variant_id` is the atomic exact build context.
- `model_key`, `body_style`, and `trim_level` are reusable predicates resolved against the canonical variant registry.
- If `variant_id` is set, any provided `model_key`, `body_style`, or `trim_level` must match the registry-derived values for that variant exactly.
- `body_code` is not a context-scope field; it lives in `variants.csv` as `gm_model_code`.
- `vehicle_line` is not needed for Corvette-only canonical scopes unless a future multi-line GM schema is approved.
- No selected-option, package, rule, arbitrary condition-set, or boolean-expression predicates belong in this table.
- Transitional `condition_sets.csv` and `condition_terms.csv` remain separate normalized compatibility tables and are not the final context scope model.

Validation:

- Unknown `model_key` and `model_year` combinations fail.
- Unknown `variant_id` values fail.
- Malformed `variant_id` values fail if they do not match the trim plus model/body-code convention.
- A `variant_id` with contradictory `model_key`, `body_style`, or `trim_level` predicates fails.
- Unsupported `body_style` or `trim_level` values for the declared model/year fail.
- Broad `model_key`, `body_style`, or `trim_level` scopes resolve to matching active `variant_id` values.
- Broad scopes resolving to no active variants fail.
- Duplicate active `context_scope_id` values fail.
- Negative or invalid `priority` values fail.
- Overlapping active scopes with the same effective specificity and same priority fail unless they are identical no-op duplicates.

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

- Exactly one of `canonical_option_id` or `presentation_id` is required for final authoring.
- Use `canonical_option_id` for inherited baseline status that applies to every active presentation for the canonical option within the same resolved context.
- Use `presentation_id` for a surface-specific status, such as a Standard Options display row that differs from the customer-choice presentation.
- A presentation-specific rule overrides a canonical rule.
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
- Use `canonical_option_id` for inherited baseline base price that applies to every priced customer-choice presentation for the canonical option within the same resolved context.
- Use `presentation_id` when one presentation has a different emitted base price or must preserve a legacy price surface independently.
- Presentation-specific base prices override canonical-option base prices.
- `context_scope_id` is the final pricing scope field and references `canonical/status/context_scopes.csv`.
- Blank `context_scope_id` means the row is the price-book default for all active variants covered by `price_book_id`.
- A populated `context_scope_id` must resolve to active variants compatible with the `price_book_id` model/year.
- Price rows use the shared context specificity cascade: exact variant, body plus trim, body only or trim only, then model/year default.
- Same-target, same-effective-context active rows with the same priority and conflicting amounts are validation errors.
- Final canonical base prices must not reference legacy `condition_sets.csv` or `condition_terms.csv`.
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

Narrow authoring table for simple unscoped customer choice-to-customer choice excludes/requires.

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
- Final simple rules target presentations. The current implemented table is transitional and targets legacy option IDs via `source_option_id` and `target_option_id`.
- During transition, current flat rows compile into normalized `condition_sets.csv`, `condition_terms.csv`, and `dependency_rules.csv` equivalents using the emitted legacy option IDs.
- A future final compiler may generate selected-target conditions from `source_presentation_id` and `target_presentation_id`; it must preserve the same legacy emitted dependency rule shape for parity.
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

### Ownership

Final ownership is explicit and identity-scoped. It must not be inferred from RPO alone.

#### `projection_ownership.csv`

Records canonical projection ownership for options, presentations, and relationships.

Required columns:

- `projection_ownership_id`
- `owner_scope`
- `canonical_option_id`
- `presentation_id`
- `relationship_type`
- `relationship_id`
- `ownership`
- `reason`
- `active`
- `notes`

Allowed `owner_scope` values:

- `canonical_option`
- `presentation`
- `relationship`

Allowed `ownership` values:

- `projected_owned`
- `production_guarded`
- `external_owned`

Rules:

- `canonical_option` rows require `canonical_option_id` and must not set `presentation_id` or relationship fields.
- `presentation` rows require `presentation_id` and may carry `canonical_option_id` for readability, but `presentation_id` is the ownership identity.
- `relationship` rows require `relationship_type` and `relationship_id`.
- `legacy_option_id` is compatibility metadata from presentations or aliases; it is not primary ownership identity.

#### `preserved_boundaries.csv`

Records production-owned or preserved boundaries using typed source/target identifiers.

Required columns:

- `preserved_boundary_id`
- `relationship_type`
- `source_ref_type`
- `source_ref_id`
- `target_ref_type`
- `target_ref_id`
- `ownership`
- `reason`
- `active`
- `notes`

Allowed `source_ref_type` and `target_ref_type` values:

- `canonical_option`
- `presentation`
- `legacy_option`
- `control_plane_reference`
- `relationship`
- `choice_group`
- `rpo_reference`

Allowed `ownership` values:

- `preserved_cross_boundary`
- `production_guarded`
- `production_owned`

Rules:

- Use `legacy_option` only when the production boundary is truly legacy-option-specific.
- Use `rpo_reference` only as a reviewed fallback when no canonical, presentation, legacy option, control-plane, relationship, or choice-group identity exists yet.
- Preserved boundary classification must avoid RPO-scoped false failures for duplicate-RPO cases.

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

Compiler ownership expectations:

- Final canonical inputs under `data/stingray/canonical/` compile to generated legacy-compatible outputs.
- Transitional bridge inputs outside `data/stingray/canonical/` remain supported until their lanes are deliberately converted.
- `canonical/options/canonical_options.csv`, `canonical/options/duplicate_rpo_reviews.csv`, `canonical/options/canonical_option_aliases.csv`, `canonical/presentation/option_presentations.csv`, `canonical/presentation/choice_groups.csv`, `canonical/presentation/choice_group_presentations.csv`, and `canonical/status/option_status_rules.csv` generate legacy-shaped choice/display rows.
- `canonical/pricing/canonical_base_prices.csv` and `canonical/pricing/price_books.csv` generate legacy-shaped base price fragments; `canonical/pricing/price_rules.csv` generates legacy price rule fragments.
- `canonical/relationships/simple_dependency_rules.csv` and `canonical/relationships/requires_any_groups.csv` generate normalized `condition_sets.csv`, `condition_terms.csv`, `dependency_rules.csv`, and legacy rule/ruleGroup fragments as needed for parity.
- `canonical/relationships/package_includes.csv` generates legacy include/auto-add fragments only after package include behavior is intentionally modeled.
- `canonical/relationships/replacement_default_rules.csv` generates replacement/default legacy fragments only after runtime selection behavior is intentionally modeled.
- `canonical/options/control_plane_references.csv` generates validation/control-plane references, not customer choice rows, unless another final table intentionally presents them.
- `canonical/ownership/projection_ownership.csv` and `canonical/ownership/preserved_boundaries.csv` generate ownership and preserved-boundary validation surfaces.
- Transitional `selectables.csv`, `selectable_display.csv`, `base_prices.csv`, `dependency_rules.csv`, `condition_sets.csv`, `condition_terms.csv`, `auto_adds.csv`, `rule_groups.csv`, `rule_group_members.csv`, `exclusive_groups.csv`, item-set tables, and current optional compatibility bridge tables remain hand-authored only for lanes not yet converted.

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

Ownership expectations:

- Current `projected_slice_ownership.csv` remains a transitional shadow-overlay and census contract.
- Final ownership lives in `canonical/ownership/projection_ownership.csv` and `canonical/ownership/preserved_boundaries.csv`.
- Final ownership is canonical-option scoped, presentation scoped, or relationship scoped. `legacy_option_id` is compatibility metadata, not primary ownership identity.
- Preserved boundary checks must avoid RPO-scoped false failures when one RPO has multiple reviewed presentations or aliases.
- `validation/projected_slice_ownership.csv` must not become the final ownership model.

## Context/Status Cascade

Status and pricing scopes resolve from broad to specific after the consuming table has chosen the matching target. Presentation-targeted rows beat canonical-option-targeted rows.

1. model/year default
2. body + trim pair
3. body only or trim only
4. exact variant

Precedence sort:

1. presentation-specific target over canonical-option target
2. higher scope specificity
3. higher priority
4. deterministic row ID tie-break
5. duplicate effective winners with conflicting outcomes are validation errors

Scope rules:

- `variant_id` is the atomic build context and resolves through `canonical/status/variants.csv`.
- `model_key`, `body_style`, and `trim_level` remain independent reusable predicates over active canonical variants.
- The GM model/body code is `gm_model_code` in `variants.csv`, not a context-scope field.
- Final `context_scopes.csv` uses direct vehicle/build dimensions only; it does not reference selected options, packages, rules, arbitrary boolean expressions, `condition_sets.csv`, or `condition_terms.csv`.
- Final `canonical_base_prices.csv` uses `context_scope_id` for scoped prices; the current `scope_condition_set_id` field exists only on transitional bridge pricing files.
- Transitional `condition_sets.csv` and `condition_terms.csv` remain compatibility tables for already-authored legacy-shaped rules until their lanes are deliberately converted.
- Rules and relationships apply after the status cascade has removed or marked unavailable options.

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
- preserve source vehicle/model line
- preserve raw section/order path
- preserve source option key when present
- compute and persist `raw_row_hash`
- provide stable source row identity for repeated imports and source diffing

## Relationship Taxonomy

Relationship classes:

- `simple_excludes`: unscoped customer choice excludes customer choice.
- `simple_requires`: unscoped customer choice requires customer choice.
- `scoped_dependency`: context-scoped customer choice excludes/requires customer choice.
- `requires_any`: source requires one member from a target member set.
- `choice_group_exclusivity`: required/single/multi choice behavior.
- `package_include`: package source includes or auto-adds target.
- `price_override`: condition modifies target price.
- `replacement_default`: default selection and replacement behavior.
- `control_plane_reference`: hidden, runtime-only, structured, or guarded references.

Relationship authoring rules:

- Use flat simple authoring only for unscoped projected choice-to-choice excludes/requires.
- Keep scoped/context dependency rules in transitional normalized condition tables until a final scoped dependency table is approved.
- Use package tables for includes and auto-adds.
- Use price tables for price behavior.
- Use replacement/default tables for runtime selection behavior.
- Keep control-plane references outside customer-selectable catalogs.

## Migration Strategy From Current Mixed State

Current old-style projected rows remain valid transitional source. The project should stop adding new customer-facing sections to old `selectables.csv`/`selectable_display.csv` by default.

Recommended migration pattern:

1. Freeze final schema contracts.
2. Keep current optional files as transitional compatibility bridges.
3. Add optional loaders and validation for final tables under `data/stingray/canonical/` with header-only parity.
4. Add compiler support using temp fixtures.
5. Pick one small canonical-first lane.
6. Prove emitted legacy parity and shadow overlay parity.
7. Leave already migrated old-style lanes alone until their entire lane can move cleanly.

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

1. Should final simple dependency rules target `presentation_id` only, or allow canonical-option targets when all active presentations should inherit the rule?
2. Should package includes target presentations or canonical options by default?
3. Should `standard_choice` be allowed on non-selectable presentations, or should non-selectable standard rows always use `standard_fixed`?
4. Should display order live only in `choice_group_presentations.csv`, or also remain denormalized in `option_presentations.csv` for easier authoring?
5. What is the first canonical-first lane after support contracts are approved: Calipers, a small duplicate-free lane, or a staging-only importer pilot?
6. When should transitional old-style lanes be converted: opportunistically by lane, or only after a full model-wide compiler can emit all legacy rows?

## Next Pass Recommendation

The next implementation pass should be support-only loaders and validators for the new `data/stingray/canonical/` namespace. It should not target the existing optional/transitional file paths for new final-schema support, migrate rows, or project a tactical option lane.
