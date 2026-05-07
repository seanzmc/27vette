You’re right. That previous schema was exactly the wrong direction: too many folders, too many special-purpose tables, and no obvious spine. Scrap it.

The schema should come from the shape of `stingray-form-data.json`, but cleaned up so it does **not** preserve legacy duplicate artifacts.

The stable spine should be:

```text
variant_id
option_id
section_id
group_id
rule_id
```

Everything links through those. Same `option_id` everywhere. No duplicate display-only option IDs. No alias table.

# Final schema v1

Use these tables. Keep the names close to the existing data object.

```text
dataset
variants
steps
sections
choices
contextChoices
standardEquipment
ruleGroups
exclusiveGroups
rules
priceRules
interiors
colorOverrides
validation
```

That is the schema tree. Not twelve folders. Not a new table for every behavior.

## `dataset`

Metadata about the model/year build.

```csv
dataset_id,model_year,model_key,source_name,source_version,created_at,notes
```

Example:

```csv
2027_stingray,2027,stingray,2027 Corvette Stingray,,,
```

## `variants`

One row per exact build context.

```csv
variant_id,dataset_id,model_code,body_style,trim_level,display_name,base_price,active
```

Example:

```csv
2lt_c67,2027_stingray,C67,convertible,2LT,Stingray Convertible 2LT,78595,true
```

Your rule is the rule:

```text
variant_id tells model + body + trim.
```

The extra fields are not competing keys. They are readable metadata derived from the ID / GM code.

## `steps`

The high-level build steps.

```csv
step_key,dataset_id,step_label,display_order,active
```

Example:

```csv
wheels,2027_stingray,Wheels,4,true
```

## `sections`

Where options display.

```csv
section_id,dataset_id,step_key,section_name,category_id,category_name,display_order,active
```

Example:

```csv
sec_cali_001,2027_stingray,wheels,Caliper Color,cat_exte_001,Exterior,20,true
```

## `choices`

One row per real option. Not per legacy duplicate. Not per variant.

```csv
option_id,dataset_id,rpo,label,description,section_id,group_id,display_order,choice_mode,selection_mode,active,notes
```

Example:

```csv
opt_j6a,2027_stingray,J6A,Black painted calipers,,sec_cali_001,grp_calipers,10,single,single_select_req,true,
```

This is where your point matters:

```text
J6A is one option.
QEB is one option.
A Standard Options duplicate is not another option.
```

If production has `opt_j6a_001` and `opt_j6a_002`, the final schema still has only:

```text
opt_j6a
```

If a duplicate source row has useful notes, those notes go into `validation` or importer/source review, not into a second canonical choice.

## `contextChoices`

This is the per-context status/price layer.

```csv
context_choice_id,dataset_id,option_id,variant_id,status,status_label,price,availability_note,disclosure_note,active
```

Allowed `status`:

```text
optional
standard_choice
standard_fixed
included
unavailable
```

Examples:

```csv
ctx_j6a_1lt_c07,2027_stingray,opt_j6a,1lt_c07,standard_choice,Standard,0,,,
ctx_j6f_1lt_c07,2027_stingray,opt_j6f,1lt_c07,optional,Available,795,,,
ctx_b6p_zr1_coupe,2027_zr1,opt_b6p,1lz_r07,standard_fixed,Standard,0,,,
```

This table is the answer to:

```text
What is this option in this exact variant?
```

This is where standard/optional/unavailable lives.

## `standardEquipment`

This should be generated from `contextChoices`, not manually duplicated from legacy display-only rows.

If we keep a table for output/export, it should reference the same `option_id`.

```csv
standard_equipment_id,dataset_id,variant_id,option_id,section_id,display_order,label_override,description_override,notes,active
```

But the preferred rule is:

```text
standardEquipment is a view/output derived from contextChoices where status is standard_choice, standard_fixed, or included.
```

No duplicate option IDs.

## `ruleGroups`

For rules like “requires any of these.”

```csv
rule_group_id,dataset_id,group_type,source_type,source_id,member_type,member_ids,message,active,notes
```

Allowed `group_type`:

```text
requires_any
```

Example:

```csv
rg_5zu_paint,2027_stingray,requires_any,option,opt_5zu,option,opt_g8g|opt_gba|opt_gkz,"Requires Arctic White, Black, or Torch Red exterior paint.",true,
```

This keeps it simple. Ordered list in one field. If we later need member-level metadata, then we can split members. Do not start split unless needed.

## `exclusiveGroups`

For choice exclusivity beyond basic section/group behavior.

```csv
exclusive_group_id,dataset_id,group_id,member_option_ids,max_selected,message,active,notes
```

Example:

```csv
ex_roof,2027_stingray,grp_roof,opt_cf7|opt_cc3|opt_c2z,1,,true,
```

## `rules`

General option relationships.

```csv
rule_id,dataset_id,rule_type,source_type,source_id,target_type,target_id,variant_id,message,action,active,notes
```

Allowed `rule_type`:

```text
excludes
requires
includes
replaces_default
```

Allowed `source_type` / `target_type`:

```text
option
group
variant
```

Examples:

```csv
rule_efy_gba,2027_stingray,excludes,option,opt_efy,option,opt_gba,,"Blocked by EFY Body-color accents.",block,true,
rule_z51_t0a,2027_stingray,includes,option,opt_z51,option,opt_t0a,,Included with Z51 Performance Package,auto_add,true,
rule_tvs_t0a,2027_stingray,replaces_default,option,opt_tvs,option,opt_t0a,,Removes T0A when TVS selected,remove_default,true,
```

No separate `dependency_rules`, `simple_dependency_rules`, `package_includes`, and `replacement_rules` for v1 unless this table fails. Same structure, different `rule_type/action`.

## `priceRules`

Conditional price behavior.

```csv
price_rule_id,dataset_id,source_type,source_id,target_option_id,variant_id,price_action,amount,message,active,notes
```

Allowed `price_action`:

```text
set_static
add_amount
included_zero
```

Example:

```csv
price_z51_tvs,2027_stingray,option,opt_z51,opt_tvs,,set_static,0,Z51 selected sets TVS price to 0,true,
```

## `interiors`

Keep this only if interiors need a richer structure than normal choices. Otherwise, interiors should eventually become choices + contextChoices.

For now:

```csv
interior_id,dataset_id,option_id,variant_id,trim_level,seat_type,interior_color,material,status,price,active,notes
```

But the goal should be to collapse interior option behavior into the same `choices/contextChoices/rules/priceRules` structure unless interiors truly need extra dimensions.

## `colorOverrides`

For color/image/UI override behavior, not option compatibility rules.

```csv
color_override_id,dataset_id,option_id,variant_id,asset_type,override_key,override_value,active,notes
```

## `validation`

Everything weird or review-required goes here instead of spawning a new schema table.

```csv
validation_id,dataset_id,entity_type,entity_id,issue_type,severity,message,recommended_action,status,notes,active
```

Allowed `entity_type`:

```text
variant
option
context_choice
rule
price_rule
source_row
duplicate_rpo
```

This is where duplicate display-only rows get reviewed.

Example:

```csv
val_qeb_dup,2027_stingray,duplicate_rpo,QEB,standard_display_duplicate,info,"Production has display-only Standard Options duplicate. Do not create second option_id.",ignore_duplicate,approved,,true
```

# How rows link

```text
dataset_id links everything to the model/year dataset.
variant_id links context rows to variants.
option_id links choices, status, rules, prices, equipment, colors.
section_id organizes choices for display.
group_id organizes choices into selection groups.
rule_id links rule behavior.
```

That is the whole spine.

# How J6A works

Production has:

```text
opt_j6a_001 = real Caliper choice
opt_j6a_002 = Standard Options duplicate
```

Final schema has:

```csv
choices.csv
opt_j6a,2027_stingray,J6A,Black painted calipers,,sec_cali_001,grp_calipers,10,single,single_select_req,true,

contextChoices.csv
ctx_j6a_1lt_c07,2027_stingray,opt_j6a,1lt_c07,standard_choice,Standard,0,,,
...
```

No `opt_j6a_002`.

If the UI needs Standard Equipment, it derives it from `contextChoices.status=standard_choice`.

# How QEB works

Same thing.

```csv
choices.csv
opt_qeb,2027_stingray,QEB,5-split-spoke Pearl Nickel forged aluminum wheels,,sec_whee_002,grp_wheels,10,single,single_select_req,true,

contextChoices.csv
ctx_qeb_1lt_c07,2027_stingray,opt_qeb,1lt_c07,standard_choice,Standard,0,,,
```

No `opt_qeb_002`.

# Why the schema should have come from `stingray-form-data.json`

It should have.

The top-level arrays in the JSON are already close to the app’s real shape:

```text
variants
steps
sections
choices
standardEquipment
ruleGroups
exclusiveGroups
rules
priceRules
interiors
colorOverrides
validation
```

The mistake was treating the emitted JSON as canonical instead of **deduplicating and normalizing it into this smaller spine**.

The final schema should be the JSON shape cleaned up:

```text
choices = unique real options
contextChoices = variant-specific status/price
standardEquipment = generated view
rules = relationships
priceRules = price relationships
validation = weird stuff/review
```

# What to do now

Do not create more support tables.

Do not project more lanes.

Next pass should replace the bloated RFC with this v1 schema.

Use this:

```text
Pass 228 schema reset RFC patch. Documentation only. No implementation.

Replace the current target canonical schema direction with a simplified v1 schema based on the stingray-form-data.json top-level objects.

Freeze these final tables and headers:
- dataset
- variants
- steps
- sections
- choices
- contextChoices
- standardEquipment
- ruleGroups
- exclusiveGroups
- rules
- priceRules
- interiors
- colorOverrides
- validation

Rules:
- option_id is the stable canonical option key.
- RPO is a property, not the key.
- same option_id is used everywhere.
- no display-only duplicate option_ids in final schema.
- Standard Equipment is generated from contextChoices/status, not duplicate rows.
- duplicate production RPOs are reviewed in validation, not modeled as fake options.
- no new tables without explicit v2 approval.

Document how J6A, QEB, B6P, Z51 includes, 5ZU requires-any paint, and Z51->TVS price override fit into these tables.

No code changes.
No CSV migration.
No loaders.
No generated/runtime/workbook/form-app changes.
```

This is the line. This is the simple schema. This is what I should have given you earlier.
