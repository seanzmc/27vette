# Proposal Readiness Report

This report is not a canonical proposal and is not source-of-truth config. Use data/import_maps/corvette_2027/*.csv for review decisions.

## Audit Snapshot

- primary_variant_matrix_ready: `true`
- color_trim_ready: `true`
- pricing_ready: `true`
- equipment_groups_ready: `true`
- rpo_role_overlaps_ready: `true`
- canonical_proposal_ready: `false`
- ready_for_proposal_generation: `false`
- narrow_first_proposal_scope_ready: `true`
- readiness_reasons: `["color_trim_scope_deferred_from_canonical_import", "suspicious_review_rows_present"]`

## Included Future Proposal Inputs

| domain_key | eligibility_status | allowed_future_use | source_files | notes |
| --- | --- | --- | --- | --- |
| primary_variant_matrix_rows | eligible | Future proposal input for Standard Equipment, Interior, Exterior, and Mechanical primary variant matrix evidence. | ["staging_variant_matrix_rows.csv", "staging_audit_report.json"] | 8348 staged variant-matrix rows reported by the audit. |
| price_schedule_raw_evidence | eligible | Future proposal input as raw price evidence only; final price semantics remain out of scope. | ["staging_price_rows.csv", "staging_audit_report.json"] | 293 staged price-evidence rows reported by the audit. |
| accepted_rpo_role_overlaps_as_separate_evidence | eligible | Future proposal input may preserve accepted orderable/ref-only overlaps as separate evidence only. | ["staging_audit_rpo_role_overlaps.csv", "data/import_maps/corvette_2027/rpo_role_overlaps.csv"] | 10 RPO overlap decisions are resolved as separate evidence. |

## Excluded Or Deferred Domains

| domain_key | disposition | reason | source_of_decision | notes |
| --- | --- | --- | --- | --- |
| color_trim_canonical_import | excluded_from_first_proposal_scope | 6 Color/Trim sections are accepted_review_only. | data/import_maps/corvette_2027/color_trim_scope.csv | Color/Trim can be audit-ready while still not canonical-import-ready. |
| equipment_groups_as_selectable_source | excluded_cross_check_only | Equipment Groups remain derived/cross-check evidence and are not a source of new selectables. | staging_audit_report.json | cross_check_only=True |
| rpo_overlap_merging | excluded_keep_separate_evidence | 10 overlap decisions are resolved; canonical handling counts: {'keep_separate_evidence': 10} | data/import_maps/corvette_2027/rpo_role_overlaps.csv | Accepted overlaps are not permission to merge orderable and ref-only evidence. |
| rule_inference | excluded | This report does not infer dependency, exclusion, auto-add, or availability rules from raw text. | pass_10_scope | Future rule proposal work needs a separate explicit scope. |
| package_logic | excluded | Package membership and package behavior are outside the first proposal boundary. | pass_10_scope | No RPO business behavior is interpreted here. |
| canonical_proposal_generation_in_this_pass | excluded | Pass 10 is a report/gate only. | pass_10_scope | No proposed canonical rows or proposed output directories are written. |

## First Proposal Scope Recommendation

Recommended future inputs:
- Standard Equipment primary variant matrix rows
- Interior primary variant matrix rows
- Exterior primary variant matrix rows
- Mechanical primary variant matrix rows
- Price Schedule as raw price evidence only
- Accepted RPO overlaps as separate evidence only

Explicit exclusions:
- Color/Trim canonical import
- Equipment Groups as selectable source
- RPO overlap merging
- rule inference
- package logic
- canonical rule rows
- canonical auto-add rows
- canonical dependency rows
- canonical exclusive group rows

## Why Global Canonical Readiness Can Remain False

Global canonical proposal readiness remains false in the audit snapshot. A narrower future proposal scope can still be defined when excluded/deferred domains are intentionally outside that scope.

Audit reasons: `["color_trim_scope_deferred_from_canonical_import", "suspicious_review_rows_present"]`

Excluded/deferred domains: `["color_trim_canonical_import", "equipment_groups_as_selectable_source", "rpo_overlap_merging", "rule_inference", "package_logic", "canonical_proposal_generation_in_this_pass"]`

## Non-Goals

- no canonical proposal rows generated
- no staging mutation
- no parser changes
- no app/generator/workbook/output changes
- no RPO business-rule interpretation
