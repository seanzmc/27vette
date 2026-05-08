# Confident Subset Schema Alignment

Generated schema-alignment report only. canonical_apply_ready=false.

This is a schema-alignment report only. It is generated review evidence, not source-of-truth config.

## Summary

- canonical_apply_ready=false
- schema_context_confidence: `partial`
- retained selectables: `657`
- retained availability rows: `3530`
- source refs: `3530`

## Schema Context Found

| file | headers |
| --- | --- |
| schema-refactor.md |  |
| safeMigrationPlan.md |  |
| orderGuideImporterScripts.md |  |
| data/stingray/catalog/selectables.csv | selectable_id\|selectable_type\|rpo\|label\|description\|active\|availability_condition_set_id\|notes |
| data/stingray/catalog/variants.csv | variant_id\|model_key\|model_year\|body_style\|body_code\|trim_level\|label\|base_price_usd\|active |
| data/stingray/catalog/item_sets.csv | set_id\|label\|set_type\|active\|notes |
| data/stingray/catalog/item_set_members.csv | set_id\|member_selectable_id\|active |
| data/stingray/ui/selectable_display.csv | selectable_id\|legacy_option_id\|section_id\|section_name\|category_id\|category_name\|step_key\|choice_mode\|selection_mode\|selection_mode_label\|display_order\|selectable\|active\|status_condition_set_id\|status_when_matched\|status_label_when_matched\|status_when_unmatched\|status_label_when_unmatched\|label\|description\|source_detail_raw |
| data/stingray/pricing/base_prices.csv | base_price_id\|price_book_id\|target_selector_type\|target_selector_id\|scope_condition_set_id\|amount_usd\|priority\|active\|notes |

## Table Alignment Summary

```json
{
  "availability": {
    "excluded_from_first_apply": 3,
    "review_required": 4,
    "target_schema_missing": 11
  },
  "display": {
    "direct_map": 4,
    "excluded_from_first_apply": 3,
    "review_required": 4,
    "transform_required": 2
  },
  "selectables": {
    "direct_map": 3,
    "excluded_from_first_apply": 7,
    "review_required": 4,
    "target_schema_missing": 2,
    "transform_required": 1
  },
  "source_refs": {
    "review_required": 11
  }
}
```

## Top Transformation Needs

| source_file | source_field | target_table | target_field | alignment_status | transformation_needed |
| --- | --- | --- | --- | --- | --- |
| catalog/selectables.csv | has_orderable_rpo | data/stingray/catalog/selectables.csv |  | excluded_from_first_apply | no |
| catalog/selectables.csv | has_ref_rpo | data/stingray/catalog/selectables.csv |  | excluded_from_first_apply | no |
| catalog/selectables.csv | model_key | data/stingray/catalog/selectables.csv | model_key | target_schema_missing | yes |
| catalog/selectables.csv | notes | data/stingray/catalog/selectables.csv | notes | review_required | yes |
| catalog/selectables.csv | proposal_filter_status | data/stingray/catalog/selectables.csv |  | excluded_from_first_apply | no |
| catalog/selectables.csv | proposal_scope | data/stingray/catalog/selectables.csv |  | excluded_from_first_apply | no |
| catalog/selectables.csv | proposal_selectable_id | data/stingray/catalog/selectables.csv | selectable_id | transform_required | yes |
| catalog/selectables.csv | proposal_status | data/stingray/catalog/selectables.csv |  | excluded_from_first_apply | no |
| catalog/selectables.csv | ref_rpo | data/stingray/catalog/selectables.csv |  | review_required | yes |
| catalog/selectables.csv | review_status | data/stingray/catalog/selectables.csv |  | excluded_from_first_apply | no |
| catalog/selectables.csv | section_family | data/stingray/catalog/selectables.csv | section_id | target_schema_missing | yes |
| catalog/selectables.csv | selectable_source | data/stingray/catalog/selectables.csv |  | excluded_from_first_apply | no |
| catalog/selectables.csv | source_ref_ids | data/stingray/catalog/selectables.csv | source_refs | review_required | yes |
| catalog/selectables.csv | source_sheet | data/stingray/catalog/selectables.csv | source_refs | review_required | yes |

Showing 14 of 52 rows. Complete evidence is in the CSV outputs.

## Blockers By Type

| blocker_key | blocker_type | affected_table | severity | notes |
| --- | --- | --- | --- | --- |
| color_trim_excluded_from_first_apply | advisory | support/color_trim | advisory | Color/Trim remains accepted_review_only and outside this first apply boundary. |
| price_evidence_excluded_from_confident_subset | advisory | pricing | advisory | Raw price evidence was intentionally excluded from the confident subset. |
| rules_packages_dependencies_excluded | advisory | logic | advisory | Rule, package, auto-add, dependency, and exclusivity inference remain out of scope. |
| canonical_apply_ready_false_by_design | apply_blocker | all | apply_blocker | Pass 15 reports alignment only; it does not imply canonical apply readiness. |
| missing_canonical_availability_schema | schema_decision_needed | ui/availability.csv | schema_decision_needed | Canonical availability target is missing in current schema context; this is distinct from excluded first-apply items. |
| missing_canonical_source_refs_schema | schema_decision_needed | meta/source_refs.csv | schema_decision_needed | Canonical source_refs target is missing; this is a canonical schema-context gap, not an importer failure. |
| no_final_canonical_selectable_id_policy | schema_decision_needed | catalog/selectables.csv | apply_blocker | proposal_selectable_id is review-only and must not be copied as final selectable_id. |
| section_family_not_final_section_id | transformation_needed | ui/selectable_display.csv | schema_decision_needed | section_family is a broad importer family and needs UI section/category mapping. |

## Recommended First Apply Boundary

- Apply only after canonical schema is stable.
- Start with selectables/display/availability from confident subset only.
- Exclude Color/Trim, Equipment Groups, price evidence, rules, packages, auto-adds, dependencies, and exclusivity.
- Preserve proposal IDs as proposal-only until a canonical ID policy is approved.

No canonical rows were generated or applied.
