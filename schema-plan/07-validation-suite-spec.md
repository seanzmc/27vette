# Spec 07: Workbook Schema Drift Validation Suite

## Diagnosis

Root cause: after schema normalization lands, no single gate guarantees workbook source graph remains standardized across Stingray and Grand Sport. Need validation checks that catch future header drift, type drift, key reference issues, and generated contract regressions.

Evidence:
- Audit found primitive type drift, interior header drift, category_master stale reference, lifecycle enum drift, and generated/draft contract differences.
- Action plan calls for later validation suite after schema decisions.

Risk level: medium-high.
Change type: scripts/tests only, no workbook data change unless validation fixtures require approved setup.

## Exact Files / Sheets To Inspect

Potential new/modified files:
- scripts/validate_workbook_schema.py or scripts/corvette_form_generator/schema_validation.py
- tests/workbook-schema-validation.test.mjs or Python test if project pattern supports it
- AGENTS.md/README only if adding command to documented gates

Workbook sheets checked:
- stingray_options / grandSport_options
- stingray_ovs / grandSport_ovs
- rule_mapping / grandSport_rule_mapping
- price_rules / grandSport_price_rules
- rule_groups / grandSport_rule_groups
- rule_group_members / grandSport_rule_group_members
- exclusive_groups / grandSport_exclusive_groups
- exclusive_group_members / grandSport_exclusive_members
- grandSport_variant_overrides
- lt_interiors / LZ_Interiors
- color_overrides
- variant_master
- section_master
- PriceRef
- model_interior_scope
- interior_components

Generated evidence checked:
- form_rules
- form_rule_groups
- form_exclusive_groups
- form_interiors
- form_color_overrides
- form_validation
- form-output/stingray-form-data.json
- form-output/inspection/grand-sport-form-data-draft.json

## Constraints

- Validation only; do not auto-fix workbook data.
- No new dependencies.
- Use .venv/bin/python.
- Do not require category_master as active sheet.
- Do not require shared model_key columns.
- Allow model-specific grandSport_variant_overrides.

## Proposed Checks

1. Header drift
- Compare equivalent sheet pairs to approved headers.
- Verify LZ_Interiors matches lt_interiors after Spec 02.
- Verify category_master is not required.

2. Boolean type drift
- Known boolean columns contain real booleans only after Spec 01.

3. RPO type drift
- *_options.rpo values are strings, including "719" and "379".

4. Price/null drift
- Price fields numeric or blank only.
- Blank not coerced to 0.
- No string price placeholders.

5. Key references
- OVS option_id exists in model options sheet.
- OVS variant_id exists in variant_master.
- section_id exists in section_master when nonblank.
- price rule condition/target IDs resolve.
- rule source/target IDs resolve to approved option/interior/virtual IDs.

6. Group integrity
- rule_group_members have parent rule_groups.
- exclusive_group_members have parent exclusive_groups.
- Active groups have active members.
- Inactive groups with active members warn unless explicitly allowed.

7. Rule lifecycle
- generation_action in allowed enum.
- normalization_status in allowed enum.
- omitted/replaced rows have reason.
- replacement IDs resolve when populated.

8. Color override integrity
- color_overrides option_id resolves to color option.
- adds_rpo resolves to option_id.
- Color Overrides raw list has normalized row coverage where applicable.

9. Interior integrity
- Active model interiors have model_interior_scope where required.
- Component-bearing interiors have interior_components rows.
- requires_r6x/requires_z25 maps to requires_option_id.
- PriceRef joins resolve expected component prices.

10. Generated contract checks
- Generated form_rules count/source count reported.
- Draft-only fields do not leak into live runtime unless approved.
- Generated validation has no error severity.

## Implementation Outline

1. Add read-only schema validation script.
2. Start with report mode: list errors/warnings with sheet, row, column, value.
3. Add tests for validator against current workbook after Specs 01-06 land.
4. Add command to validation gates if approved.
5. Keep messages concrete and row-specific.

## Validation Plan

Run validator:
```sh
.venv/bin/python scripts/validate_workbook_schema.py stingray_master.xlsx
```

Run existing package/generator gates:
```sh
.venv/bin/python scripts/validate_workbook_package.py stingray_master.xlsx
.venv/bin/python scripts/generate_stingray_form.py
.venv/bin/python scripts/generate_grand_sport_form.py
node --test tests/stingray-generator-stability.test.mjs
node --test tests/grand-sport-draft-data.test.mjs
node --test tests/grand-sport-rule-audit.test.mjs
```

## Risks

- Validator may be too strict during transition if run before Specs 01-06 land.
- Row-specific checks may need explicit allowlists for intentional legacy/source-retention rows.
- If validator imports generator modules with side effects, it may accidentally mutate artifacts; avoid this.

## Non-goals

- No workbook edits.
- No generator/runtime behavior changes.
- No NoSQL validation.
- No automatic repair script in this pass.
