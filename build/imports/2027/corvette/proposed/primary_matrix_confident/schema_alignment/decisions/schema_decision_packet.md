# Schema Decision Packet

Generated decision packet, not source-of-truth config. canonical_apply_ready=false.

This is a generated decision packet, not source-of-truth config. It turns Pass 15 alignment evidence into human decisions only.

## Inputs

- alignment: `provided --alignment`
- output: `provided --out`

## Alignment Summary

- canonical_apply_ready=false
- alignment counts: `{"direct_map": 7, "excluded_from_first_apply": 13, "review_required": 23, "target_schema_missing": 13, "transform_required": 3}`
- blocker counts: `{"advisory": 3, "apply_blocker": 1, "schema_decision_needed": 3, "transformation_needed": 1}`

proposal_selectable_id is not canonical selectable_id.

section_family is not final section_id.

Color/Trim, Equipment Groups, rules, packages, and prices remain excluded from the first apply boundary.

No apply is authorized by this packet.

## Decision Items

| decision_id | decision_area | decision_status | readiness_impact | recommended_default |
| --- | --- | --- | --- | --- |
| selectable_id_policy | canonical_selectable_id_policy | needs_decision | apply_blocker | conservative_starting_point: keep proposal_selectable_id as review-only until a canonical ID policy is approved. |
| section_mapping_policy | ui_section_step_category_mapping | needs_decision | schema_decision_needed | conservative_starting_point: use an explicit import map for section_family to UI taxonomy before apply. |
| availability_schema_policy | canonical_availability_shape | needs_decision | schema_decision_needed | conservative_starting_point: preserve one row per selectable plus variant_id in first prototype. |
| source_refs_policy | source_refs_governance_shape | needs_decision | schema_decision_needed | conservative_starting_point: keep source refs as import evidence until governance shape is approved. |
| proposal_metadata_policy | proposal_only_metadata_disposition | needs_decision | transformation_needed | conservative_starting_point: preserve metadata in generated archive/import audit only. |
| first_apply_boundary | first_apply_boundary_confirmation | accepted_boundary | boundary_confirmation | conservative_starting_point: produce a reconciliation report against canonical CSV before apply. |

## Decision Options Summary

| decision_id | option_id | option_label | recommended_default | blocks_apply_if_unresolved |
| --- | --- | --- | --- | --- |
| selectable_id_policy | selectable_id_model_rpo | derive from model_key + rpo + disambiguator | conservative_starting_point | yes |
| selectable_id_policy | selectable_id_source_hash | derive from stable source hash |  | yes |
| selectable_id_policy | selectable_id_manual | manually assign IDs during apply |  | yes |
| selectable_id_policy | selectable_id_reconcile_existing | use existing canonical IDs when reconciling against data/stingray |  | yes |
| section_mapping_policy | section_broad_placeholder | map section_family to broad placeholder sections |  | yes |
| section_mapping_policy | section_import_map | use import map for section_family to section_id/step_id | conservative_starting_point | yes |
| section_mapping_policy | section_defer | defer finer UI mapping until app schema is stable |  | yes |
| availability_schema_policy | availability_selectable_variant | one row per selectable + variant_id | conservative_starting_point | yes |
| availability_schema_policy | availability_condition_set | one row per selectable + condition_set_id |  | yes |
| availability_schema_policy | availability_hybrid | hybrid variant matrix compiled into condition sets later |  | yes |
| source_refs_policy | source_refs_canonical_rows | canonical meta/source_refs.csv row per source cell/field |  | yes |
| source_refs_policy | source_refs_member_table | source_ref member table linking canonical rows to source refs | conservative_starting_point | yes |
| source_refs_policy | source_refs_import_only | keep proposal source refs as import-only evidence |  | yes |
| proposal_metadata_policy | metadata_drop_after_apply | drop after apply |  | no |
| proposal_metadata_policy | metadata_import_audit | preserve in import audit metadata | conservative_starting_point | no |
| proposal_metadata_policy | metadata_change_log | preserve in change_log/provenance table |  | yes |
| proposal_metadata_policy | metadata_archive_only | keep only in generated proposal archive |  | no |
| first_apply_boundary | boundary_confident_apply_prototype | proceed later with confident subset apply prototype |  | yes |

Showing 18 of 20 rows. Complete evidence is in the CSV outputs.

## First Apply Boundary

The future first apply boundary, if later authorized, should remain limited to selectables/display/availability from the confident subset only. It should exclude Color/Trim canonical import, Equipment Groups as selectable source, price evidence, rule inference, package logic, auto-adds, dependencies, and exclusivity.

## Additional Alignment Notes

- No unexpected alignment notes.

No canonical rows were generated or applied.
