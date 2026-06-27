# Future Model Compatibility Preview

Generated: 2026-05-31T19:40:03+00:00

Dry-run only: workbook and runtime app data were not written.

## z06
- Target options: `z06_options`
- Active option RPO matches: 164 / 230 Grand Sport active options
- Proposed row counts:
  - `z06_rule_mapping`: 100 proposed (currently 100)
  - `z06_rule_groups`: 0 proposed (currently 0)
  - `z06_rule_group_members`: 0 proposed (currently 0)
  - `z06_exclusive_groups`: 7 proposed (currently 7)
  - `z06_exclusive_members`: 16 proposed (currently 16)
- Skipped/unresolved reasons:
  - rule_mapping deferred_source_type_interior: 19
  - rule_mapping inactive_or_replaced_source_rule: 120
  - rule_mapping source_id:source_option_id_not_found: 2
  - rule_mapping source_id:target_rpo_not_found: 40
  - rule_mapping target_id:source_option_id_not_found: 1
  - rule_mapping target_id:target_rpo_not_found: 39
  - rule_groups no_resolved_members: 1
  - rule_groups source_id:target_rpo_not_found: 1
  - rule_group_members target_id:target_rpo_not_found: 2
  - exclusive_groups fewer_than_two_resolved_members: 2
  - exclusive_groups inactive_group: 1
  - exclusive_members inactive_member: 1
  - exclusive_members option_id:target_rpo_not_found: 8

## zr1
- Target options: `zr1_options`
- Active option RPO matches: 141 / 230 Grand Sport active options
- Proposed row counts:
  - `zr1_rule_mapping`: 56 proposed (currently 56)
  - `zr1_rule_groups`: 0 proposed (currently 0)
  - `zr1_rule_group_members`: 0 proposed (currently 0)
  - `zr1_exclusive_groups`: 4 proposed (currently 4)
  - `zr1_exclusive_members`: 10 proposed (currently 10)
- Skipped/unresolved reasons:
  - rule_mapping deferred_source_type_interior: 19
  - rule_mapping inactive_or_replaced_source_rule: 120
  - rule_mapping source_id:source_option_id_not_found: 2
  - rule_mapping source_id:target_rpo_not_found: 89
  - rule_mapping target_id:source_option_id_not_found: 1
  - rule_mapping target_id:target_rpo_not_found: 34
  - rule_groups source_id:target_rpo_not_found: 2
  - exclusive_groups fewer_than_two_resolved_members: 5
  - exclusive_groups inactive_group: 1
  - exclusive_members inactive_member: 1
  - exclusive_members option_id:target_rpo_not_found: 13

## zr1x
- Target options: `zr1x_options`
- Active option RPO matches: 141 / 230 Grand Sport active options
- Proposed row counts:
  - `zr1x_rule_mapping`: 56 proposed (currently 56)
  - `zr1x_rule_groups`: 0 proposed (currently 0)
  - `zr1x_rule_group_members`: 0 proposed (currently 0)
  - `zr1x_exclusive_groups`: 4 proposed (currently 4)
  - `zr1x_exclusive_members`: 10 proposed (currently 10)
- Skipped/unresolved reasons:
  - rule_mapping deferred_source_type_interior: 19
  - rule_mapping inactive_or_replaced_source_rule: 120
  - rule_mapping source_id:source_option_id_not_found: 2
  - rule_mapping source_id:target_rpo_not_found: 89
  - rule_mapping target_id:source_option_id_not_found: 1
  - rule_mapping target_id:target_rpo_not_found: 34
  - rule_groups source_id:target_rpo_not_found: 2
  - exclusive_groups fewer_than_two_resolved_members: 5
  - exclusive_groups inactive_group: 1
  - exclusive_members inactive_member: 1
  - exclusive_members option_id:target_rpo_not_found: 13

Notes:
- Dry-run only: stingray_master.xlsx was read but not saved.
- Grand Sport compatibility source rows are rebased by unique active RPO matches, not raw option_id equality.
- source_type=interior rule_mapping rows are deferred and not proposed.
- Exclusive groups are proposed only when at least two members survive rebasing.

