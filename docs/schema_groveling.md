# This is the schema

- steps
- sections
- variants
- options
- option_status
- choice_groups
- choice_group_options
- interiors
- color overrides
- rules
- rule_members
- standard_equipment
- source_rows
- validation

The schema needs one stable spine:

```text
variant_id
option_id
group_id
rule_id
```

Everything should hang off those. Not twelve folder concepts. Not unique snowflake headers in every table.

## `steps`

The high-level build steps.

```csv
step_key,dataset_id,step_label,display_order,active
```

```code
steps:{
  step_key: string;
  step_label: string;
  runtime_order: number;
  source: string;
  section_ids: string;
  }
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

```json
"sections": [
          {
            "section_id": "sec_context_body_style",
            "section_name": "Body Style",
            "category_id": "cat_context_001",
            "category_name": "Vehicle Context",
            "selection_mode": "single_select_req",
            "selection_mode_label": "Required single choice",
            "choice_mode": "single",
            "is_required": "True",
            "standard_behavior": "user_selected",
            "section_display_order": 1,
            "step_key": "body_style",
            "step_label": "Body Style"
          }
```

Example:

```csv
sec_cali_001,2027_stingray,wheels,Caliper Color,cat_exte_001,Exterior,20,true
```

## `variants.csv`

One row per build context.

```csv
variant_id,model_year,model_key,body_style,trim_level,active
```

Example:

```csv
2lt_c67,2027,stingray,convertible,2LT,true
```

You are right: `2lt_c67` already tells us model/body/trim because your ID convention is stable. The extra columns are derived/display/query helpers, not competing keys.

## `options.csv`

One row per real option.

```csv
option_id,rpo,label,description,option_type,active
```

```json
{
  "section_id": "sec_spec_001",
  "section_name": "Special Edition",
  "category_id": "cat_mech_001",
  "category_name": "Mechanical",
  "selection_mode": "single_select_opt",
  "selection_mode_label": "Optional single choice",
  "choice_mode": "single",
  "is_required": "False",
  "standard_behavior": "locked_included",
  "section_display_order": 110,
  "step_key": "packages_performance",
  "step_label": "Packages & Performance"
}
```

Example:

```csv
opt_j6a,J6A,Black painted calipers,,customer_option,true
```

Important rule:

```text
RPO is a property.
option_id is the key.
```

Most of the time one RPO maps to one option. If a repeated RPO is a display-only duplicate, it does **not** become a new option. If a repeated RPO is truly different by trim/context, then it gets separate reviewed option IDs.

## `option_status.csv`

This answers: “What is this option for this variant?”

```csv
option_id,variant_id,status,price,active
```

Allowed `status`:

```text
optional
standard_choice
standard_fixed
included
unavailable
```

Example:

```csv
opt_j6a,1lt_c07,standard_choice,0,true
opt_j6f,1lt_c07,optional,795,true
opt_b6p,zr1_coupe,standard_fixed,0,true
opt_b6p,1lt_c07,optional,995,true
```

This is where your “variant → body → trim → option” logic becomes concrete. We can later allow broad rows like `body_style=convertible`, but the resolved compiled table should be by `option_id + variant_id`.

## `choice_groups.csv`

Defines groups like Wheels, Calipers, Paint.

```csv
group_id,label,section_id,section_name,category_id,category_name,step_key,selection_mode,required,active
```

Example:

```csv
grp_calipers,Caliper Color,sec_cali_001,Caliper Color,cat_exte_001,Exterior,wheels,single,true,true
```

## `choice_group_options.csv`

Links options to groups.

```csv
group_id,option_id,display_order,active
```

Example:

```csv
grp_calipers,opt_j6a,10,true
grp_calipers,opt_j6f,20,true
grp_calipers,opt_j6e,30,true
```

That’s the missing clean relationship.

The option is the same option everywhere. Its status changes by variant. Its group placement is here.

## interiors

Example: Oh look, two different schemas stacked on top of eachother.

```json
{
  "interior_id": "1LT_AE4_HTJ_N26",
  "source_sheet": "lt_interiors",
  "active_for_stingray": true,
  "trim_level": "1LT",
  "requires_r6x": "False",
  "seat_code": "AE4",
  "interior_code": "HTJ",
  "interior_name": "Jet Black",
  "material": "Performance Textile",
  "price": 1790,
  "suede": "N26",
  "stitch": "",
  "two_tone": "",
  "section_id": "sec_intc_001",
  "color_overrides_raw": "",
  "source_note": "Requires (N26) sueded microfiber-wrapped steering wheel.",
  "interior_components": [
    {
      "rpo": "AE4",
      "label": "AE4 Seat Upgrade",
      "price": 1095,
      "component_type": "seat"
    },
    {
      "rpo": "N26",
      "label": "Sueded Microfiber",
      "price": 695,
      "component_type": "suede"
    }
  ],
  "interior_components_json": "[{\"rpo\":\"AE4\",\"label\":\"AE4 Seat Upgrade\",\"price\":1095,\"component_type\":\"seat\"},{\"rpo\":\"N26\",\"label\":\"Sueded Microfiber\",\"price\":695,\"component_type\":\"suede\"}]",
  "interior_trim_level": "1LT",
  "interior_seat_code": "AE4",
  "interior_seat_label": "AE4 Competition Seats",
  "interior_color_family": "HTJ Jet Black",
  "interior_material_family": "Performance Textile",
  "interior_variant_label": "HTJ Jet Black",
  "interior_group_display_order": 4,
  "interior_material_display_order": 4,
  "interior_choice_display_order": 4,
  "interior_hierarchy_levels": "[\"1LT\", \"AE4 Competition Seats\", \"HTJ Jet Black\"]",
  "interior_hierarchy_path": "1LT > AE4 Competition Seats > HTJ Jet Black",
  "interior_parent_group_label": "AE4 Competition Seats",
  "interior_leaf_label": "HTJ Jet Black",
  "interior_reference_order": 4
}
```

But the goal should be to collapse interior option behavior into the same choices/contextChoices/rules/priceRules structure unless interiors truly need extra dimensions.

## color_overrides

Interior exterior and seatbelt color combinations that add D30 automatically

```json
{
  "override_id": "co_001",
  "interior_id": "1LT_AQ9_HUQ",
  "option_id": "opt_g26_001",
  "rule_type": "requires",
  "adds_rpo": "opt_d30_001",
  "notes": "Exterior/interior pairing requires the listed override RPO."
}
```

## rules.csv

One relationship table for the basic rules.

```csv
rule_id,rule_type,source_type,source_id,target_type,target_id,variant_id,message,active
```

Allowed `rule_type`:

```text
excludes
requires
includes
requires_any
price_override
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
rule_efy_gba,excludes,option,opt_efy,option,opt_gba,,"Blocked by EFY Body-color accents.",true
rule_z51_tvs_price,price_override,option,opt_z51,option,opt_tvs,,TVS price set to 0 with Z51,true
```

If a rule only applies to one variant, put `variant_id`. If blank, it applies wherever both options exist.

## `rule_members.csv`

Only needed when a rule has multiple targets, like “requires any of these.”

```csv
rule_id,member_type,member_id,member_order,active
```

Example:

```csv
rule_5zu_paint_requires_any,option,opt_g8g,10,true
rule_5zu_paint_requires_any,option,opt_gba,20,true
rule_5zu_paint_requires_any,option,opt_gkz,30,true
```

So the rule is:

```csv
rule_5zu_paint_requires_any,requires_any,option,opt_5zu,group,grp_5zu_allowed_paints,,Requires Arctic White, Black, or Torch Red exterior paint.,true
```

Or use members directly. But the key idea is: **do not invent a new table for every rule shape**.

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

```json
"standardEquipment": [
    {
      "equipment_id": "std_1lt_c07__opt_aq9_002",
      "variant_id": "1lt_c07",
      "body_style": "coupe",
      "trim_level": "1LT",
      "option_id": "opt_aq9_002",
      "rpo": "AQ9",
      "label": "GT1 Bucket Seats",
      "description": "",
      "section_id": "sec_1lte_001",
      "section_name": "1LT Equipment",
      "category_name": "Equipment Groups",
      "display_order": 10,
      "source_detail_raw": ""
    }
```

## source_rows

Raw import/staging evidence. This is where messy order-guide rows belong.

```csv
source_row_id,variant_id,raw_section,raw_rpo,raw_label,raw_description,raw_status,raw_price,raw_notes,row_hash,classification,active
```

This lets the importer keep evidence without polluting the canonical schema.

## validation

Checks needed for a complete build

```json
    {
      "check_id": "active_variants",
      "severity": "pass",
      "entity_type": "variant",
      "entity_id": "",
      "message": "6 active Stingray variants exported."
    },
    {
      "check_id": "availability_rows",
      "severity": "pass",
      "entity_type": "availability",
      "entity_id": "",
      "message": "1548 choice rows exported ({'standard': 521, 'unavailable': 186, 'available': 841})."
    },
    {
      "check_id": "rules",
      "severity": "pass",
      "entity_type": "rule",
      "entity_id": "",
      "message": "238 active compatibility rules exported from 238 source rules."
    }
```

---

That is the core.

Everything links by:

```text
variant_id
option_id
group_id
rule_id
```

# Why this works

For a given variant:

1. Start with `variant_id`.
2. Load all `option_status` rows for that variant.
3. Remove `unavailable`.
4. Group remaining options by `choice_group_options`.
5. Mark selected/default based on status.
6. Apply `rules`.
7. Apply price from `option_status.price` plus price rules.
8. Render the app.

That is the full flow.

The correction is:

```text
same option_id everywhere
status changes by variant
display comes from groups
rules link source and target
legacy IDs are aliases
raw weirdness stays in source rows
```
