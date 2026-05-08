# Proposal Audit Report

This is an audit of generated proposal artifacts only. No canonical rows were applied.

## Input Summary

- required inputs present: `{"catalog/selectables.csv": true, "meta/source_refs.csv": true, "pricing/raw_price_evidence.csv": true, "proposal_report.json": true, "review_queue.csv": true, "ui/availability.csv": true, "ui/selectable_display.csv": true}`
- optional inputs present: `{"meta/rpo_role_overlap_evidence.csv": true}`

## Readiness

| field | value |
| --- | --- |
| selectables_ready | True |
| availability_ready | True |
| price_evidence_ready | True |
| review_queue_ready | False |
| source_refs_ready | True |
| rpo_overlap_traceability_ready | True |
| canonical_apply_ready | False |
| reasons | ['blocking_review_buckets_present'] |

## Review Queue Buckets

| review_bucket | original_reason | count | severity | recommended_action |
| --- | --- | --- | --- | --- |
| boundary_exclusion_summary | excluded_color_trim_source | 1 | info | exclude_from_primary_matrix_proposal |
| boundary_exclusion_summary | excluded_equipment_group_source | 1 | info | exclude_from_selectable_proposal |
| expected_review_only | accepted_rpo_overlap_kept_separate | 10 | info | keep_overlap_as_separate_evidence; do_not_merge |
| missing_rpo_non_standard_equipment | blank_rpo_non_standard_equipment | 676 | review | review_non_standard_row_without_rpo |
| missing_rpo_standard_equipment | standard_equipment_without_rpo | 650 | review | keep_as_review_evidence; do_not_treat_as_confirmed_selectable |
| ref_only_evidence | ref_only_only_evidence | 3438 | review | review_reference_only_usage_before_accepting_selectable |
| unsupported_status | unsupported_status | 358 | review | review_status_mapping_before_accepting_proposal |

## Selectables Quality

- total selectables: `1592`
- confident count: `666`
- review-only count: `926`
- no-RPO standard-equipment review-only count: `125`
- ref-only-only proposal count: `671`

## Availability Quality

- total availability rows: `8348`
- rows missing source_ref_id: `0`
- availability values: `{"available": 3450, "needs_review": 358, "not_available": 972, "standard": 3568}`

## Source-Ref Integrity

| check_name | status | count | sample_ids |
| --- | --- | --- | --- |
| unresolved_referenced_source_refs | pass | 0 |  |
| unused_source_refs | pass | 10 | staging_audit_rpo_role_overlaps.csv:AH2:29b8e328\|staging_audit_rpo_role_overlaps.csv:B6P:86283361\|staging_audit_rpo_role_overlaps.csv:C2Z:a07c8bc2\|staging_audit_rpo_role_overlaps.csv:CFV:8d7b7914\|staging_audit_rpo_role_overlaps.csv:D3V:66e2b9e8\|staging_audit_rpo_role_overlaps.csv:DY0:9a57579b\|staging_audit_rpo_role_overlaps.csv:SL9:f6d8ce8a\|staging_audit_rpo_role_overlaps.csv:UQT:4d73d40a\|staging_audit_rpo_role_overlaps.csv:WUB:ebfeffc2\|staging_audit_rpo_role_overlaps.csv:ZZ3:167be9a4 |
| proposal_rows_missing_source_refs | pass | 0 |  |
| source_refs_missing_traceability | pass | 0 |  |

## RPO Overlap Traceability

- optional input present: `True`
- total overlap evidence rows: `10`
- traceability level: `summary_level_only`

## Recommended Next Step

Narrow the next proposal pass to confident selectables only, excluding review-only/no-RPO/ref-only evidence, unless this audit identifies a clearer blocker.

No canonical rows were applied.
