# Sheet/header audit for Z models

All expected Z model source sheets exist and their headers match the Grand Sport-compatible canonical headers:

- z06_options / zr1_options / zr1x_options
- z06_ovs / zr1_ovs / zr1x_ovs
- z06_rule_mapping / zr1_rule_mapping / zr1x_rule_mapping
- z06_price_rules / zr1_price_rules / zr1x_price_rules
- z06_rule_groups / zr1_rule_groups / zr1x_rule_groups
- z06_rule_group_members / zr1_rule_group_members / zr1x_rule_group_members
- z06_exclusive_groups / zr1_exclusive_groups / zr1x_exclusive_groups
- z06_exclusive_members / zr1_exclusive_members / zr1x_exclusive_members
- z06_variant_overrides / zr1_variant_overrides / zr1x_variant_overrides

The Z model workbook-source metadata also exists, but all Z source-role rows remain inactive, which is consistent with the current “not promoted yet” safety boundary.

# Interior setup: Stingray vs Grand Sport

## Stingray currently works like this:

- model_workbook_sources points Stingray’s interior_source_sheet to lt_interiors, active=True.
- lt_interiors has 132 rows:
  - 1LT: 4
  - 2LT: 40
  - 3LT: 73
  - 3LT_R6X: 15
- lt_interiors has populated section_id values:
  - sec_intc_001: 4
  - sec_intc_002: 40
  - sec_intc_003: 88
- 130 of 132 rows have active_for_stingray=True.
- 15 rows have requires_r6x=True.
- Stingray has 197 active interior_components rows.
- There are no Stingray model_interior_scope rows. The live Stingray generator still largely uses legacy lt_interiors fields directly: active_for_stingray, Trim, requires_r6x, included_option_id, plus workbook-owned interior_components.

## Grand Sport currently works like this:

- Grand Sport uses the newer metadata-driven draft path:
- model_workbook_sources points Grand Sport’s interior_source_sheet to lt_interiors, active=True.
  - generate_grand_sport_form.py loads model config overrides from workbook metadata.
  - inspection.build_model_interiors reads config.interior_source_sheet.
  - It filters interiors through model_interior_scope.
  - It loads components through interior_components scoped to model_key=grand_sport.
- model_interior_scope has 132 active rows, all for grand_sport.
- interior_components has 198 active rows for grand_sport.
- So Grand Sport uses the same lt_interiors source rows as Stingray, but model scoping and component ownership are workbook-owned per Grand Sport.

## Z model implication:

- z06, zr1, and zr1x metadata already point their interior_source_sheet rows to LZ_Interiors, but those rows are inactive.
- LZ_Interiors exists and has matching headers with lt_interiors.
- LZ_Interiors has 132 rows:
  - 1LZ: 4
  - 2LZ: 40
  - 3LZ: 73
  - 3LZ_R6X: 15
- But LZ_Interiors currently has blank section_id for all 132 rows.
- There are currently no model_interior_scope rows for z06, zr1, or zr1x.
- There are currently no interior_components rows for z06, zr1, or zr1x.

So the Z models do not yet have the same runtime-ready interior setup that Grand Sport has. To match the Grand Sport pattern, Z models need LZ interior section ids plus model-specific scope/component rows before promotion:

- z06 should scope 1LZ / 2LZ / 3LZ interiors.
- zr1 and zr1x should scope 1LZ / 3LZ interiors only, not 2LZ.
- Components need model_key-specific rows for z06, zr1, zr1x, not just shared LT/LZ source rows.
