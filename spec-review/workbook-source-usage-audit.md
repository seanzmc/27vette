# Workbook Source Usage Audit

Generated for the Grand Sport workbook cleanup pass.

## Current Principles

- Workbook source sheets own model data and business rules.
- `form_*` sheets are generated outputs from the Stingray generator and should not be edited by hand.
- Grand Sport draft artifacts are generated under `form-output/inspection/` and do not activate Grand Sport production runtime.
- Header or sheet deletion should happen only after the consuming script path is removed or rewritten.

## Active Source Sheets

| Sheet | Current role | Consumed by | Cleanup notes |
| --- | --- | --- | --- |
| `variant_master` | Model/trim/body-style matrix and activation gate | `scripts/generate_stingray_form.py`, `scripts/corvette_form_generator/inspection.py` | Keep. Grand Sport rows must stay inactive until promotion. |
| `category_master` | Category labels and ordering | Stingray generator, Grand Sport inspection/draft | Keep. |
| `section_master` | Section labels, selection modes, required flags, section display order | Stingray generator, Grand Sport inspection/draft | Keep. This is the current workbook-owned section order source. |
| `stingray_options` | Stingray option source | Stingray generator | Keep. Same normalized option headers as Grand Sport. |
| `stingray_ovs` | Stingray option/variant statuses | Stingray generator | Keep. |
| `rule_mapping` | Stingray compatibility rules | Stingray generator | Keep until all Stingray rule consumers are migrated. |
| `price_rules` | Stingray price overrides | Stingray generator | Keep. Grand Sport price rules are not wired to this sheet yet. |
| `rule_groups` | Stingray grouped requirements | Stingray generator | Keep. |
| `rule_group_members` | Stingray grouped requirement members | Stingray generator | Keep. |
| `exclusive_groups` | Stingray exclusive groups | Stingray generator | Keep. |
| `exclusive_group_members` | Stingray exclusive group members | Stingray generator | Keep. |
| `grandSport_options` | Grand Sport option source | Grand Sport inspection/draft and rule audit | Keep. Same normalized option headers as Stingray. |
| `grandSport_ovs` | Grand Sport option/variant statuses | Grand Sport inspection/draft | Keep. Must have one row per Grand Sport `option_id` and variant. |
| `grandSport_rule_mapping` | Grand Sport compatibility rules | Grand Sport inspection/draft and rule audit | Keep for now. Audit-only columns can be removed only with script/test updates. |
| `grandSport_rule_groups` | Grand Sport grouped requirements | Grand Sport inspection/draft | Keep as an empty source table with headers. |
| `grandSport_rule_group_members` | Grand Sport grouped requirement members | Grand Sport inspection/draft | Keep as an empty source table with headers. |
| `grandSport_exclusive_groups` | Grand Sport exclusive groups | Grand Sport inspection/draft and rule audit | Keep. |
| `grandSport_exclusive_members` | Grand Sport exclusive group members | Grand Sport inspection/draft and rule audit | Keep. |
| `color_overrides` | Interior/exterior override auto-adds | Stingray generator and Grand Sport draft | Keep. Should be normalized after active model behavior is stable. |
| `lt_interiors` | LT interior source for Stingray and Grand Sport | Stingray generator and Grand Sport draft | Keep. Interior headers are still non-normalized. |
| `LZ_Interiors` | LZ/Z06-family interior source for Stingray generation | Stingray generator | Keep until Stingray generator no longer reads it. |
| `PriceRef` | Interior component price reference | Stingray generator and Grand Sport draft | Keep. |

## Generated Output Sheets

These sheets are written by `scripts/generate_stingray_form.py` and should not be manually edited:

- `form_steps`
- `form_context_choices`
- `form_choices`
- `form_standard_equipment`
- `form_rule_groups`
- `form_exclusive_groups`
- `form_rules`
- `form_price_rules`
- `form_interiors`
- `form_color_overrides`
- `form_validation`

## Legacy Or Unused Sheets

| Sheet | Evidence | Recommendation |
| --- | --- | --- |
| `asset_map` | No current script references found. | Candidate to clear or archive after visual asset needs are confirmed. |
| `IDs` | No current script references found. Hidden sheet. | Candidate to clear/archive. |
| `stingray` | No current script references found. Hidden legacy ingest-style sheet. | Candidate to clear/archive after confirming no manual workflow depends on it. |
| `Z06 Ingest` | No current script references found. Hidden ingest sheet. | Candidate to keep archived/hidden until Z06 work starts, or move out of source workbook. |
| `ZR1 Ingest` | No current script references found. Hidden ingest sheet. | Candidate to keep archived/hidden until ZR1 work starts, or move out of source workbook. |
| `ZR1X Ingest` | No current script references found. Hidden ingest sheet. | Candidate to keep archived/hidden until ZR1X work starts, or move out of source workbook. |

## Header Cleanup Candidates

Do not delete these immediately; they need paired script/test cleanup.

| Sheet | Header | Current use | Cleanup path |
| --- | --- | --- | --- |
| `grandSport_rule_mapping` | `review_flag` | Preserved in audit rows and runtime rule output. | Remove only after audit/runtime output no longer needs review metadata. |
| `grandSport_rule_mapping` | `original_detail_raw` | Audit evidence and disabled/source notes. | Keep until rule extraction is fully stable. |
| `grandSport_rule_mapping` | `source_type`, `target_type` | Runtime rule output metadata. | Candidate if all rules are option-to-option and code stops emitting these fields. |
| `grandSport_rule_mapping` | `source_selection_mode`, `target_selection_mode`, `source_section`, `target_section` | Used for redundant same-section rule handling and labels. | Keep until section/mode lookup can fully derive these values. |
| `grandSport_rule_mapping` | `generation_action` | Used to omit grouped requirements. | Candidate only after grouped requirement handling is simplified. |
| `grandSport_rule_mapping` | `runtime_action` | Used for replace/default behavior. | Keep. This expresses runtime behavior from workbook rows. |
| `grandSport_rule_mapping` | `disabled_reason` | User-facing block/include reason override. | Keep unless reasons become generated only. |
| `price_rules` | `review_flag` | Source metadata. | Candidate when Stingray price rules are stable and review metadata is no longer emitted. |
| `color_overrides` | `Index` | Not used by current generator output. | Candidate to remove after verifying no Excel workflow depends on it. |
| `lt_interiors` | mixed title-case headers | Actively consumed but not normalized. | Normalize only in a dedicated interior pass. |

## Immediate Technical Follow-Ups

1. Move Grand Sport price rules into a workbook-owned source using the existing `price_rules` shape or a model-scoped equivalent.
2. Move step placement out of `SECTION_STEP_OVERRIDES` only if an existing workbook shape can express it cleanly.
3. Mark exclusive-group member rows inactive when their option rows are inactive, or teach the generator to filter inactive member option IDs.
4. Add cross-sheet workbook validation for:
   - OVS option coverage.
   - rule source/target option IDs.
   - group member option IDs.
   - section IDs.
   - allowed enum values.
