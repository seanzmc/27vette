# Spec 05: Controlled Rule Lifecycle and Auditability Metadata

## Diagnosis

Root cause: Grand Sport rule normalization uses semi-freeform generation_action values and omitted binary rows. Sean approved controlled lifecycle fields, but proper functionality and auditability must remain. Omitted/grouped binary rule rows should stay in source with normalization_status.

Evidence:
- rule_mapping and grandSport_rule_mapping have same headers today.
- Grand Sport generation_action values include:
  - omit_grouped_exclusion
  - omit_replaced_by_d3v_include
  - omit_soft_defaulted_caliper
  - omit_redundant_scoped_duplicate
  - preserve_runtime_exclude
  - omit_replaced_by_brake_exclusive_group
- Stingray generation_action mostly omit_grouped_requirement.
- Grand Sport source has 321 rule rows; draft exports fewer active runtime rules.
- Auditability required for troubleshooting.

Risk level: high.
Change type: workbook schema + generator rule filtering/validation; runtime output should remain behavior-equivalent.

## Exact Files / Sheets To Inspect

Workbook:
- stingray_master.xlsx
  - rule_mapping
  - grandSport_rule_mapping
  - rule_groups
  - grandSport_rule_groups
  - rule_group_members
  - grandSport_rule_group_members
  - form_rules generated evidence only
  - form_rule_groups generated evidence only
  - form_validation generated evidence only

Code:
- scripts/generate_stingray_form.py
- scripts/corvette_form_generator/inspection.py
- scripts/build_grand_sport_rule_sources.py
- scripts/corvette_form_generator/validation.py if relevant

Artifacts/tests:
- form-output/stingray-form-data.json
- form-output/inspection/grand-sport-rule-audit.json
- form-output/inspection/grand-sport-form-data-draft.json
- tests/grand-sport-rule-audit.test.mjs
- tests/grand-sport-draft-data.test.mjs
- tests/stingray-form-regression.test.mjs

## Constraints

- Preserve current runtime behavior.
- Keep omitted binary rows in source for troubleshooting.
- Do not hide workbook source issues in generator/runtime logic.
- No deletion of audit rows.
- No generated artifact hand edits.
- No NoSQL scope.

## Proposed Workbook Columns

Keep existing:
- generation_action

Add/standardize optional lifecycle fields:
- normalization_status
- normalization_reason
- replacement_group_id
- replacement_rule_id

Controlled normalization_status values:
- active
- omitted
- replaced
- preserved
- review

Controlled generation_action values initially allowed:
- blank
- omit_grouped_requirement
- omit_grouped_exclusion
- omit_replaced_by_d3v_include
- omit_soft_defaulted_caliper
- omit_redundant_scoped_duplicate
- preserve_runtime_exclude
- omit_replaced_by_brake_exclusive_group

Rules:
- Blank generation_action + blank normalization_status means active until migration complete.
- Omitted/replaced actions require normalization_status and normalization_reason.
- replacement_group_id required when rule is replaced by group.
- replacement_rule_id required when rule is replaced by specific rule.
- preserve_runtime_exclude maps to normalization_status preserved.

## Implementation Outline

1. Inventory current generation_action values in both rule sheets.
2. Add failing validation for unknown generation_action/status values.
3. Add lifecycle columns to rule_mapping and grandSport_rule_mapping through safe workbook migration.
4. Populate lifecycle fields based on existing generation_action values.
5. Update generator rule loading to use controlled lifecycle fields while preserving fallback to generation_action during transition.
6. Ensure grouped rules still suppress duplicate generated runtime rules.
7. Ensure source/audit artifacts still report omitted rows.
8. Regenerate and compare behavior counts.

## Validation Plan

Commands:
```sh
.venv/bin/python scripts/validate_workbook_package.py stingray_master.xlsx
.venv/bin/python scripts/generate_stingray_form.py
.venv/bin/python scripts/generate_grand_sport_form.py
node --test tests/grand-sport-rule-audit.test.mjs
node --test tests/grand-sport-draft-data.test.mjs
node --test tests/stingray-form-regression.test.mjs
node --test tests/multi-model-runtime-switching.test.mjs
```

Manual verification:
- Grand Sport grouped Z15 source rows remain in grandSport_rule_mapping.
- Generated Grand Sport ruleGroups still include gs_group_z15_excludes_non_center_stripes.
- Omitted binary rows do not reappear as duplicate runtime rules.
- Audit artifact still exposes omitted/replaced rows and reasons.

## Risks

- Adding columns may require generator/header updates.
- Misclassifying preserved vs omitted rules could change runtime behavior.
- Tests may assume exact rule counts.

## Non-goals

- No new rule business decisions.
- No deletion of source rows.
- No runtime special cases.
- No NoSQL migration.
