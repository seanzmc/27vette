# `schema_groveling.md`

<!-- Markdown fence audit: this document is intentionally not wrapped in one outer code block. All headers, schemas, and examples use standalone fenced blocks to avoid broken nested Markdown fences. -->

# Schema

A single-spine schema for custom build logic and rules. Everything hangs off four identifiers; no unique snowflake headers per table.

```text
Stable spine:
- variant_id
- option_id
- group_id
- rule_id
```

All entities below link through one or more of these identifiers.

```text
Core rule:
same option_id everywhere
status changes by variant
display comes from groups
rules link source and target
legacy IDs are aliases
raw weirdness stays in source rows
```

---

## 1. Core Definitions

Base entities that define the build context and the option library.

---

### 1.1 Variants

One row per build context.

```csv
variant_id,model_year,model_key,body_style,trim_level,active
```

Example:

```csv
2lt_c67,2027,stingray,convertible,2LT,true
```

The `variant_id` already tells us model/body/trim because the ID convention is stable. The extra columns are derived/display/query helpers, not competing keys.

---

### 1.2 Options

One row per real option.

```csv
option_id,rpo,label,description,option_type,active
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

---

## 2. Presentation Structure

Defines where options appear and how users make choices.

---

### 2.1 Steps

The high-level build steps.

```csv
step_key,dataset_id,step_label,display_order,active
```

Runtime/object shape observed in the source:

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

<!-- TODO: Resolve field mismatch between the CSV and runtime/object shapes. The CSV uses `display_order`; the runtime shape uses `runtime_order` and adds `source` and `section_ids`. Pick one canonical shape and treat the other as derived/export-only. -->

---

### 2.2 Sections

Where options display.

```csv
section_id,dataset_id,step_key,section_name,category_id,category_name,display_order,active
```

Example:

```csv
sec_cali_001,2027_stingray,wheels,Caliper Color,cat_exte_001,Exterior,20,true
```

Expanded/enriched section records observed in parsed data:

```json
[
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
  },
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
]
```

<!-- NOTE: The `sec_spec_001` JSON shape is a section/UI record, not an option record. If it appeared under `options.csv` in the source, it has been merged here. -->

<!-- TODO: Harmonize base section columns with expanded UI/policy fields such as `selection_mode`, `choice_mode`, `is_required`, and `standard_behavior`. These may be derived from `choice_groups`, but that needs to be confirmed. -->

---

### 2.3 Choice Groups

Defines logical decision points such as Wheels, Calipers, Paint, Interior Color, etc.

```csv
group_id,label,section_id,section_name,category_id,category_name,step_key,selection_mode,required,active
```

Example:

```csv
grp_calipers,Caliper Color,sec_cali_001,Caliper Color,cat_exte_001,Exterior,wheels,single,true,true
```

Choice group behavior:

```text
A choice group controls how a user selects from a set of options.
The option remains the same option everywhere.
Its variant-specific availability lives in option_status.
Its display placement lives in choice_group_options.
```

<!-- TODO: Normalize allowed `selection_mode` values. Observed values include `single`, `single_select_req`, and `single_select_opt`; the schema should define whether these are canonical values or derived labels. -->

<!-- TODO: Define required-selection semantics explicitly: whether `required=true` means the user must choose, the system must default one option, or the option is locked by status. -->

---

### 2.4 Choice Group Options

Links universal `options` to localized `choice_groups`.

```csv
group_id,option_id,display_order,active
```

Example:

```csv
grp_calipers,opt_j6a,10,true
grp_calipers,opt_j6f,20,true
grp_calipers,opt_j6e,30,true
```

That is the missing clean relationship.

```text
The option is the same option everywhere.
Its status changes by variant.
Its group placement is here.
```

---

## 3. State & Availability Resolution

Defines how universal options exist within specific variant contexts.

---

### 3.1 Option Status

This answers: “What is this option for this variant?”

```csv
option_id,variant_id,status,price,active
```

Allowed `status` values:

```text
optional
standard_choice
standard_fixed
included
unavailable
```

Examples:

```csv
opt_j6a,1lt_c07,standard_choice,0,true
opt_j6f,1lt_c07,optional,795,true
opt_b6p,zr1_coupe,standard_fixed,0,true
opt_b6p,1lt_c07,optional,995,true
```

This is where the “variant → body → trim → option” logic becomes concrete.

```text
Broad rows like body_style=convertible can exist in a source/import layer,
but the resolved compiled table should be by option_id + variant_id.
```

---

### 3.2 Standard Equipment

Standard equipment is a derived view/output, not an independent source of truth.

Preferred rule:

```text
standardEquipment is derived from option_status where status is:
- standard_choice
- standard_fixed
- included
```

<!-- TODO: The source also refers to `contextChoices`, but `contextChoices` is not defined as a canonical table in this schema. Treat it as a legacy or API-layer name for resolved `option_status` rows unless a distinct definition is added. -->

If a materialized export table is needed, it must reference the same `option_id`; it must not duplicate option definitions.

```csv
standard_equipment_id,dataset_id,variant_id,option_id,section_id,display_order,label_override,description_override,notes,active
```

Example export payload:

```json
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

No duplicate option IDs.

<!-- TODO: Enforce that `standard_equipment` is always generated from `option_status` and never maintained manually as a separate source of truth. -->

---

## 4. Interior Construction

Interiors are the most ambiguous part of the schema. The target structure should reuse the normal option/choice/rule model wherever possible.

```text
Preferred target:
interior choices are options
interior placement comes from choice_groups and choice_group_options
interior availability and base price come from option_status
interior requirements and exclusions come from rules
```

Only keep dedicated interior tables if the extra dimensions cannot be expressed through the standard structure.

---

### 4.1 Interior Legacy Shape

Current interior records combine seat, material, suede, stitch, two-tone, hierarchy, component pricing, and display metadata.

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

<!-- TODO: Conflicting/ambiguous interior logic detected. The current interior shape stacks at least two schemas: a flat legacy record and a nested component model, plus derived display hierarchy fields. Decide whether hierarchy fields are canonical or derived/view-only. -->

---

### 4.2 Interior Normalization Target

Use the regular schema first:

```text
seat upgrade        -> option
interior color      -> option
material package    -> option
suede/stitch add-on -> option
interior group      -> choice_group
variant price       -> option_status.price
requirements        -> rules
component adds      -> rules/includes/requires where possible
```

Fallback only if interiors truly need extra dimensions:

```text
interiors parent table
interior_components child table
```

<!-- TODO: If the standard option/choice/rule model cannot express interior components cleanly, normalize interiors into a parent `interiors` table plus child `interior_components` table instead of keeping duplicated flat and nested fields in one record. -->

---

### 4.3 Color Overrides

Interior/exterior/seatbelt color combinations that automatically add another RPO.

Legacy/current shape:

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

Canonical treatment:

```text
color_overrides should be represented as rules
using rule_type = requires or includes.
```

Example canonical mapping:

```csv
rule_color_override_d30,requires,option,opt_g26_001,option,opt_d30_001,,Exterior/interior pairing requires the listed override RPO.,true
```

<!-- TODO: `color_overrides.rule_type` overlaps with `rules.rule_type`. Collapse color overrides into the generic `rules` table unless extra color-pair fields are required and cannot be represented by existing source/target IDs or rule metadata. -->

---

## 5. Rules & Conditional Logic

One relationship table handles conditional excludes, conditional requires, includes, price overrides, and default replacement.

Do not create a new table for every rule shape.

---

### 5.1 Rules

```csv
rule_id,rule_type,source_type,source_id,target_type,target_id,variant_id,message,active
```

Allowed `rule_type` values:

```text
excludes
requires
includes
requires_any
price_override
replaces_default
```

Allowed `source_type` / `target_type` values:

```text
option
group
variant
```

If a rule only applies to one variant, put `variant_id`.

If `variant_id` is blank, the rule applies wherever both source and target exist.

Examples:

```csv
rule_efy_gba,excludes,option,opt_efy,option,opt_gba,,"Blocked by EFY Body-color accents.",true
rule_z51_tvs_price,price_override,option,opt_z51,option,opt_tvs,,TVS price set to 0 with Z51,true
```

---

### 5.2 Rule Members

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

Canonical rule-member policy:

```text
For requires_any, rule_members is the authoritative list of acceptable satisfying members.
A parent rule may point to a group for scope/display, but the member rows define the actual allowed set.
Do not infer the allowed set from a group unless explicitly marked as legacy behavior.
```

Parent rule example:

```csv
rule_5zu_paint_requires_any,requires_any,option,opt_5zu,group,grp_5zu_allowed_paints,,Requires Arctic White, Black, or Torch Red exterior paint.,true
```

<!-- TODO: The source allows `requires_any` to be represented either by a group target or by direct member rows. Canonicalize on `rule_members` as the authoritative list to avoid ambiguity. -->

---

### 5.3 Conditional Excludes

Blocking relationships.

```text
rule_type = excludes
```

Meaning:

```text
When source is selected/present, target is disabled or unavailable.
```

Example:

```csv
rule_efy_gba,excludes,option,opt_efy,option,opt_gba,,"Blocked by EFY Body-color accents.",true
```

<!-- TODO: Define whether excludes are directional or bidirectional. Current schema should be treated as directional unless an inverse rule is explicitly present. -->

---

### 5.4 Conditional Requires

Mandatory dependency relationships.

```text
rule_type = requires
```

Meaning:

```text
When source is selected/present, target must also be selected/present.
```

Single-target example:

```csv
rule_r6x_n26,requires,option,opt_r6x,option,opt_n26,,Requires sueded microfiber-wrapped steering wheel.,true
```

Any-of example:

```csv
rule_5zu_paint_requires_any,requires_any,option,opt_5zu,group,grp_5zu_allowed_paints,,Requires Arctic White, Black, or Torch Red exterior paint.,true
```

Members for the any-of example:

```csv
rule_5zu_paint_requires_any,option,opt_g8g,10,true
rule_5zu_paint_requires_any,option,opt_gba,20,true
rule_5zu_paint_requires_any,option,opt_gkz,30,true
```

<!-- TODO: Current `rules` only supports one source condition. It does not fully express multi-condition logic like “if option A and option B are both selected, require C.” If needed, add a generic condition structure such as `rule_conditions`, or define a synthetic source group convention. Do not create one-off tables per rule shape. -->

---

### 5.5 Includes

Automatic inclusion relationships.

```text
rule_type = includes
```

Meaning:

```text
When source is selected/present, target is automatically included.
```

Example:

```csv
rule_color_override_d30,includes,option,opt_g26_001,option,opt_d30_001,,Exterior/interior pairing adds D30 automatically.,true
```

Use `includes` when the target should be added automatically. Use `requires` when the target must be present but may require user/system resolution.

---

### 5.6 Price Rules

Base prices live on `option_status.price`.

Price adjustments are modeled as rules, usually with:

```text
rule_type = price_override
```

Example:

```csv
rule_z51_tvs_price,price_override,option,opt_z51,option,opt_tvs,,TVS price set to 0 with Z51,true
```

Resolution order:

```text
1. option_status.price
2. price_override rules
3. replaces_default rules
4. final rendered price
```

Current meaning:

```text
When source is selected/present, target option price is modified.
```

<!-- TODO: Price rules are under-specified. The current `rules` schema identifies source, target, and message, but does not include explicit fields for override value, calculation type, currency, priority, or stacking behavior. Do not infer production pricing from `message` text alone. -->

Possible future metadata, if required:

```csv
rule_id,price_action,price_value,currency,priority,stacking_behavior
```

Example future detail row:

```csv
rule_z51_tvs_price,set_price,0,USD,100,last_wins
```

<!-- TODO: Decide whether price metadata belongs as extra columns on `rules`, a generic `rule_payload`, or a dedicated `price_rule_details` child table. Keep the current structural cleanup separate from that schema expansion. -->

---

### 5.7 Replaces Default

Default replacement relationships.

```text
rule_type = replaces_default
```

Meaning:

```text
When source is selected/present, target replaces an otherwise standard/default option.
```

Example shape:

```csv
rule_perf_seat_replaces_base,replaces_default,option,opt_ae4,option,opt_aq9,,Performance seat replaces base bucket seat.,true
```

<!-- TODO: Define whether `replaces_default` removes the target, swaps source for target, or marks target as no longer selected while preserving availability. -->

---

### 5.8 Rule Evaluation Semantics

Current structural rule flow:

```text
1. Start with available option_status rows for the variant.
2. Apply selected/default state from status.
3. Apply excludes.
4. Apply requires/includes.
5. Resolve requires_any through rule_members.
6. Apply price overrides.
7. Apply default replacements.
8. Validate final state.
```

<!-- TODO: Rule evaluation semantics are not fully defined. Open items include conflict resolution, circular requires/excludes, rule priority, bidirectionality, multiple simultaneous price rules, and whether requires/includes can auto-select locked or unavailable options. -->

---

## 6. Source, Import, and Validation

Raw and derived operational data should stay separate from canonical schema tables.

---

### 6.1 Source Rows

Raw import/staging evidence. This is where messy order-guide rows belong.

```csv
source_row_id,variant_id,raw_section,raw_rpo,raw_label,raw_description,raw_status,raw_price,raw_notes,row_hash,classification,active
```

This lets the importer keep evidence without polluting the canonical schema.

```text
legacy IDs are aliases
raw weirdness stays in source rows
```

---

### 6.2 Validation

Checks needed for a complete build.

Example records:

```json
[
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
]
```

Validation shape:

```json
{
  "check_id": "string",
  "severity": "string",
  "entity_type": "string",
  "entity_id": "string",
  "message": "string"
}
```

---

## 7. Application Resolution Flow

For a given variant:

```text
1. Start with variant_id.
2. Load all option_status rows for that variant.
3. Remove unavailable.
4. Group remaining options by choice_group_options.
5. Mark selected/default based on status.
6. Apply rules.
7. Apply price from option_status.price plus price rules.
8. Render the app.
```

Expanded flow:

```text
1. Request a target context via variant_id.
2. Load all option_status rows specific to that variant.
3. Remove all mapped items flagged as unavailable.
4. Group active options through choice_group_options.
5. Resolve UI placement through choice_groups, sections, and steps.
6. Designate preset selections/defaults based on status.
7. Process conditional excludes.
8. Process conditional requires/includes/requires_any.
9. Resolve finalized financials using option_status.price plus price_override rules.
10. Apply default replacements.
11. Validate final build state.
12. Render compiled application state.
```

---

## 8. Global TODOs / Ambiguities

```text
- Confirm all original descriptions have been preserved after structural reorganization.
- Resolve `steps` CSV vs runtime/object field mismatch.
- Normalize enriched `sections` fields and decide which are canonical vs derived.
- Define allowed `selection_mode` values and required/default behavior.
- Treat option_id as canonical and RPO as an attribute everywhere.
- Keep standardEquipment derived from option_status; do not duplicate option definitions.
- Replace undefined `contextChoices` terminology or define it explicitly.
- Collapse color_overrides into rules unless extra color-pair fields justify a separate structure.
- Collapse interiors into options/choice_groups/option_status/rules wherever possible.
- If interiors need extra dimensions, normalize into parent interiors plus child interior_components.
- Canonicalize requires_any around rule_members as the authoritative member list.
- Add explicit price-rule metadata before relying on price overrides in production.
- Define rule evaluation order, priority, circular-dependency handling, and conflict resolution.
- Define support for multi-condition sources if needed.
- Keep source_rows as staging/import evidence only.
```

Final spine:

```text
variant_id
option_id
group_id
rule_id
```
