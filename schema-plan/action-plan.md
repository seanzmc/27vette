    Ranked action items: workbook schema standardization, both models. No NoSQL migration assumed.

    1. Normalize boolean fields across model-specific sheets
    Urgency: blocker
    Why: current mixed bool/string values create parser drift.
    Scope:
    - grandSport_options.selectable
    - grandSport_rule_mapping.review_flag
    - grandSport_price_rules.review_flag
    - rule_groups.active
    - rule_group_members.active
    - exclusive_groups.active
    - exclusive_group_members.active
    - grandSport_variant_overrides.active/selectable
    Canonical:
    - real Excel booleans TRUE/FALSE
    - parser output booleans
    Validation:
    - reject "TRUE"/"FALSE"/"True"/"False" strings in boolean columns after cleanup.

    2. Force numeric-looking RPOs to text
    Urgency: blocker
    Why: 719/379 become ints; RPO joins unstable.
    Scope:
    - stingray_options.rpo
    - grandSport_options.rpo
    - any future model-specific *_options.rpo
    Canonical:
    - text string always: "719", "379"
    Validation:
    - all rpo values type string
    - uppercase/string normalization
    - no numeric cell types in RPO columns.

    3. Normalize LZ_Interiors headers to lt_interiors shape
    Urgency: high
    Why: same interior concept, two schemas. Biggest source schema drift.
    Approved direction:
    - LZ_Interiors should match lt_interiors headers.
    Canonical headers:
    - interior_id, Interior Name, Material, Price, Detail from Disclosure, Color Overrides, Trim, Seat, Interior Code, Suede, Stitch, Two Tone, section_id, active_for_stingray, requires_r6x, included_option_id
    Specific renames:
    - ID -> interior_id
    - Cost -> Price
    Needed decisions during spec:
    - active_for_stingray default for LZ rows likely FALSE if not Stingray-compatible.
    - section_id probably blank unless scoped by model_interior_scope.
    Validation:
    - lt_interiors and LZ_Interiors same header set/order or explicit approved delta.

    4. Clarify why Stingray generator reads LZ_Interiors
    Urgency: high
    Why: Sean flags LZ interiors not compatible. Current Stingray generator reads them and emits active_for_stingray False rows.
    Current evidence:
    - scripts/generate_stingray_form.py reads LZ_Interiors rows 994-1019 into interiors with active_for_stingray False.
    Action:
    - inspect generated/runtime consumers.
    - determine if LZ rows are harmless reference/provenance, legacy artifact, or wrong source inclusion.
    Likely outcome:
    - keep as inactive reference only if contract needs it, else remove from Stingray generation in approved pass.
    Classification:
    - needs human review before behavior edit.

    5. Keep model-specific source sheets; standardize contracts per pair
    Urgency: high
    Approved direction:
    - model-specific sheets stay.
    - grandSport_variant_overrides remains model-specific.
    Action:
    - define per-model sheet contract templates:
      - {model}_options
      - {model}_ovs
      - {model}_rule_mapping
      - {model}_price_rules
      - {model}_rule_groups
      - {model}_rule_group_members
      - {model}_exclusive_groups
      - {model}_exclusive_members
      - {model}_variant_overrides if model needs it
    Validation:
    - pairwise header drift report.
    - no shared model_key column migration.

    6. Remove category_master from active source graph references
    Urgency: high
    Why: requested/current docs mention category_master, workbook lacks live sheet; archive_category_master only.
    Approved direction:
    - remove category_master references.
    Action:
    - update docs/spec references later.
    - verify generator/runtime do not require category_master.
    Validation:
    - no active workflow docs list category_master.
    - no source graph check expects category_master.

    7. Add controlled generation_action enum plus lifecycle fields
    Urgency: medium-high
    Why: Grand Sport uses semi-freeform generation_action; auditability required.
    Approved direction:
    - yes, but preserve current behavior.
    Canonical pattern:
    - generation_action enum remains or becomes controlled:
      - omit_grouped_requirement
      - omit_grouped_exclusion
      - omit_replaced_by_d3v_include
      - omit_soft_defaulted_caliper
      - omit_redundant_scoped_duplicate
      - preserve_runtime_exclude
      - omit_replaced_by_brake_exclusive_group
    - add/standardize lifecycle fields:
      - normalization_status: active|omitted|replaced|preserved|review
      - normalization_reason
      - replacement_group_id
      - replacement_rule_id
    Validation:
    - every omitted/replaced rule has reason.
    - grouped rules still generate same runtime output.
    - omitted binary rows stay in source for troubleshooting.

    8. Preserve runtime-used provenance fields only; keep draft-only fields out of live contract
    Urgency: medium
    Sean answer:
    - fields used in runtime should be preserved; risk uncertain.
    Action:
    - classify Grand Sport draft fields:
      - source_option_name
      - source_description
      - text_cleanup_notes
    - inspect runtime consumers before deciding.
    Recommended rule:
    - if runtime reads it, keep in final contract.
    - if audit-only, move under draft/provenance artifact, not live choices.
    Risk:
    - bloated runtime data
    - unstable public contract
    - hidden dependency on draft cleanup notes
    Validation:
    - runtime consumer grep/test.
    - JSON schema diff Stingray vs Grand Sport.

    9. Preserve blank price vs zero semantics
    Urgency: medium
    Approved direction:
    - blank = null/not-priced
    - 0 = explicit zero-price
    Action:
    - document in workbook schema.
    - validation check:
      - price cells numeric or blank
      - no string "$0", "N/A", "-"
      - blank not coerced to 0
    Affected:
    - *_options.price
    - *_price_rules.price_value
    - interiors Price
    - PriceRef.Price

    10. Standardize raw source-detail field aliases
    Urgency: medium
    Why: same concept named many ways.
    Current names:
    - detail_raw
    - original_detail_raw
    - Detail from Disclosure
    - source_detail_raw/generated
    Recommended canonical by sheet type:
    - options: detail_raw OK
    - rules: original_detail_raw OK if meaning is “rule source text”
    - interiors: Detail from Disclosure acceptable only if both lt/LZ share it
    - generated output: source_detail_raw
    Action:
    - avoid forced rename if generator contracts depend on current names.
    - define alias map in schema docs/checks.
    Validation:
    - every source sheet has exactly one raw detail/source disclosure field.

    11. Keep color_overrides normalized table as canonical
    Urgency: medium-low
    Why: already strong relationship pattern.
    Action:
    - keep Color Overrides comma list as raw evidence only.
    - color_overrides owns generated/runtime rule rows.
    Validation:
    - every Color Overrides raw RPO can map to normalized color_overrides rows.
    - every color_overrides option_id/adds_rpo resolves.

    12. Standardize option/variant override precedence
    Urgency: medium-low
    Why: Grand Sport has model-specific overrides; Stingray mostly option-level display_behavior/default rules.
    Canonical precedence:
    1. model-specific variant override row
    2. option row default fields
    3. default_selection_rules
    4. generated/runtime generic fallback
    Action:
    - document precedence.
    - add validation for conflicting default_selected/display_only/selectable overrides.
    Validation:
    - no two active default_selected options in same required exclusive group unless intended.

    13. Keep grouped-rule audit rows in source
    Urgency: medium-low
    Approved direction:
    - auditability important; keep omitted binary rows with normalization_status.
    Action:
    - do not delete omitted rule_mapping rows during cleanup.
    - add status/reason instead.
    Validation:
    - source count can exceed generated count.
    - generated validation reports active exported vs source retained.

    14. Add later validation script suite
    Urgency: after schema decisions approved
    Checks:
    - header drift
    - boolean type drift
    - RPO type drift
    - price/null drift
    - missing option_id/variant_id/section_id refs
    - orphaned rule groups/exclusive groups
    - invalid generation_action/normalization_status
    - unnormalized LZ_Interiors headers
    - category_master references
    - generated contract parity by model

    Suggested execution order:
    1. Spec: schema standardization only, report+approval.
    2. Fix booleans/RPO text + validation.
    3. Normalize LZ_Interiors headers.
    4. Resolve Stingray reading LZ_Interiors.
    5. Controlled generation_action/status.
    6. Provenance/runtime field decision.
    7. Add validation scripts/tests.
