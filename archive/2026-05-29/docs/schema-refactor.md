# Recommendation

Replace the root `stingray_master.xlsx` with a **CSV Data Package**: a directory of normalized CSV files plus a strict machine-readable manifest, preferably `datapackage.yaml` using **Frictionless Table Schema**. Keep `.xlsx` only as an optional generated editor/review workbook, not the canonical source.

Your repo currently treats `stingray_master.xlsx` as the active source and `scripts/generate_stingray_form.py` as the generator for workbook form sheets, `form-output/`, and `form-app/data.js`. The runtime app consumes embedded data from `form-app/data.js`, and exports selected options, auto-added RPOs, open requirements, and pricing. ([github.com](https://github.com/seanzmc/27vette)) The current generator also contains hard-coded rule groups and exclusive groups, including LS6 engine covers, spoilers, center caps, car covers, and trunk liners; those should become rows in CSV tables. ([github.com](https://github.com/seanzmc/27vette/blob/main/scripts/generate_stingray_form.py))

Use CSV because it is easy to edit in spreadsheet tools, easy to diff in Git, and easy to validate. Use a Data Package/Table Schema manifest because it is designed for tabular datasets with typed fields, constraints, primary keys, and foreign keys. ([specs.frictionlessdata.io](https://specs.frictionlessdata.io//table-schema/))

The Python script should become a **generic loader / validator / compiler**:

```text
CSV package
  -> table/schema validation
  -> semantic validation
  -> generic condition/rule/pricing evaluation
  -> generated form-output/*.json, form-output/*.csv, form-app/data.js
```

No Corvette-specific logic such as “if B6P then SL1 is free,” “BCP requires ZZ3 on Convertible,” or “BCP/BCS/BC4 drop to $595 with B6P” should remain in Python.

---

# Clear design positions

## 1. Canonical format

Use:

```text
data/stingray/**/*.csv
data/stingray/datapackage.yaml
```

Do **not** use the `.xlsx` workbook as source of truth. If business users want a spreadsheet interface, generate an `editor.xlsx` from the CSV package and import/export it through a controlled script.

## 2. Validation technology

Use **Frictionless Data Package / Table Schema** as the primary contract.

Then add:

- **Pydantic** or plain Python dataclasses for semantic validation.
- Optional generated **JSON Schema** if you want editor tooling or API validation.
- Optional compiled **SQLite** artifact for fast joins, SQL checks, and inspection.

The important rule: one canonical schema contract. Do not maintain competing hand-written schema definitions that can drift.

## 3. Normalization

Do **not** store comma-separated lists in canonical CSV cells.

Use member tables:

```text
item_sets.csv
item_set_members.csv
exclusive_groups.csv
exclusive_group_members.csv
price_rule_targets.csv if needed
```

This avoids cells like:

```csv
target_option_ids
BCP,BCS,BC4
```

Those are convenient but brittle. If an editor-facing workbook wants a comma-list helper column, make it generated and non-canonical.

## 4. Identifiers

Use stable internal IDs as primary keys, not RPO codes.

Example:

```text
selectable_id = opt_bcp_001
rpo           = BCP
```

RPOs are user-facing and may collide, be reused, have aliases, or need canonicalization. The generated output can continue to expose the current `option_id`/RPO fields, but the source data should use stable IDs.

## 5. Money representation

Use integer whole-dollar fields such as:

```text
amount_usd
base_price_usd
```

Do not use floats. Current vehicle pricing is whole-dollar MSRP-style pricing, so `695`, `595`, and `0` are more editor-friendly than `69500`. If cents ever become necessary, introduce `amount_minor`/`amount_cents` in a controlled migration.

## 6. Rule model

Use a reusable **condition-set engine** with explicit **OR-of-AND** semantics:

```text
condition_set is true if any OR group is true.
OR group is true if all terms in that group are true.
```

This handles:

```text
A AND B
A OR B
(A AND B) OR (C AND NOT D)
body_style = convertible AND selected option in engine-cover set
```

The same condition sets should be reused by availability, UI visibility, dependency rules, auto-adds, and pricing.

## 7. Pricing model

Use separate tables for:

- base prices,
- included/zero-price policies,
- price rules,
- dynamic lookup tables,
- lookup rows.

Do not collapse all pricing into one override table. A single `pricing_overrides.csv` is tempting, but it becomes underpowered once you need dynamic lookup keys, stackable modifiers, included-zero policies, priority resolution, and traceable price explanations.

---

# Proposed repository layout

```text
data/
  stingray/
    datapackage.yaml

    meta/
      source_refs.csv
      change_log.csv
      workbook_column_map.csv
      enum_values.csv

    catalog/
      variants.csv
      selectables.csv
      options.csv
      item_sets.csv
      item_set_members.csv
      aliases.csv

    ui/
      steps.csv
      sections.csv
      selectable_display.csv
      availability.csv

    logic/
      condition_sets.csv
      condition_terms.csv
      dependency_rules.csv
      auto_adds.csv
      exclusive_groups.csv
      exclusive_group_members.csv

    pricing/
      price_books.csv
      base_prices.csv
      price_policies.csv
      price_rules.csv
      price_lookup_tables.csv
      price_lookup_rows.csv

    support/
      exterior_colors.csv
      interiors.csv
      interior_components.csv
      color_overrides.csv
      legacy_price_refs.csv

    validation/
      golden_builds.csv
      golden_expected_lines.csv
      semantic_checks.csv

build/
  stingray.sqlite              # optional generated artifact
  editor/stingray_editor.xlsx  # optional generated editing workbook

form-output/                   # generated
form-app/data.js               # generated
```

---

# Global CSV conventions

Use these conventions across all CSV files:

| Concern             | Rule                                                                                 |
| ------------------- | ------------------------------------------------------------------------------------ |
| Encoding            | UTF-8                                                                                |
| Header row          | Required                                                                             |
| Boolean values      | `true` / `false` only                                                                |
| Null                | Empty cell means null / not applicable                                               |
| IDs                 | Stable snake-case IDs; never row numbers                                             |
| Lists               | No comma-separated canonical list cells                                              |
| Prices              | Integer `amount_usd`; no floats                                                      |
| Notes               | Notes are informational only; Python must never parse them for behavior              |
| Effective dates     | Use ISO dates: `YYYY-MM-DD`                                                          |
| Source traceability | Use `source_ref_id` and raw source columns                                           |
| Generated files     | `form-output/*`, `form-app/data.js`, SQLite, and editor workbook are build artifacts |

---

# Core catalog schemas

## `catalog/variants.csv`

One row per orderable model/trim/body variant.

```csv
variant_id,model_key,model_year,body_style,body_code,trim_level,label,base_price_usd,active
1lt_c07,stingray,2027,coupe,C07,1LT,1LT Coupe,,true
2lt_c07,stingray,2027,coupe,C07,2LT,2LT Coupe,,true
3lt_c07,stingray,2027,coupe,C07,3LT,3LT Coupe,,true
1lt_c67,stingray,2027,convertible,C67,1LT,1LT Convertible,,true
2lt_c67,stingray,2027,convertible,C67,2LT,2LT Convertible,,true
3lt_c67,stingray,2027,convertible,C67,3LT,3LT Convertible,,true
```

Validation:

- `variant_id` primary key.
- `body_style` enum: `coupe`, `convertible`.
- `trim_level` enum: `1LT`, `2LT`, `3LT`.

---

## `catalog/selectables.csv`

Registry of anything that can be selected, priced, required, included, displayed, or exported.

```csv
selectable_id,selectable_type,rpo,label,description,canonical_selectable_id,source_ref_id,source_detail_raw,active,effective_start,effective_end
opt_b6p_001,option,B6P,Coupe Engine Appearance Package,,,src_2027_stingray_order_guide,,true,2026-01-01,
opt_sl1_001,option,SL1,"LPO, Premium indoor car cover","Red with Stingray logo",,src_2027_stingray_order_guide,,true,2026-01-01,
opt_d3v_001,option,D3V,Engine lighting,,,src_2027_stingray_order_guide,,true,2026-01-01,
opt_zz3_001,option,ZZ3,Convertible Engine Appearance Package,,,src_2027_stingray_order_guide,,true,2026-01-01,
opt_bcp_001,option,BCP,Edge Red LS6 engine cover,,,src_2027_stingray_order_guide,"Legacy workbook note retained here.",true,2026-01-01,
opt_bcs_001,option,BCS,Sterling Silver LS6 engine cover,,,src_2027_stingray_order_guide,,true,2026-01-01,
opt_bc4_001,option,BC4,Blue LS6 engine cover,,,src_2027_stingray_order_guide,,true,2026-01-01,
```

`source_detail_raw` preserves legacy workbook text for traceability, but it must not drive logic.

---

## `catalog/options.csv`

Option-specific metadata. The key can match `selectable_id`.

```csv
selectable_id,option_family,lpo,default_selection_mode,default_status,default_display_behavior,display_order
opt_b6p_001,engine_appearance,false,multi_select_opt,available,selectable,10
opt_sl1_001,lpo_exterior,true,multi_select_opt,available,selectable,151
opt_d3v_001,engine_appearance,false,multi_select_opt,available,selectable,70
opt_zz3_001,engine_appearance,false,multi_select_opt,available,selectable,80
opt_bcp_001,engine_cover,false,multi_select_opt,available,selectable,20
opt_bcs_001,engine_cover,false,multi_select_opt,available,selectable,30
opt_bc4_001,engine_cover,false,multi_select_opt,available,selectable,40
```

Validation:

- `selectable_id` primary key and FK to `selectables.selectable_id`.
- `default_selection_mode` enum.
- `default_status` enum: `standard`, `available`, `unavailable`, `hidden`.

---

## `catalog/item_sets.csv`

Reusable named sets prevent repeated groups of RPOs across pricing, dependency rules, auto-adds, and exclusivity.

```csv
set_id,label,set_type,active,notes
set_ls6_engine_covers_colored,"BCP/BCS/BC4 LS6 engine covers",selectable_set,true,"Colored LS6 engine covers"
set_ls6_engine_covers_all,"All LS6 engine covers",selectable_set,true,"Includes BC7 plus colored covers"
```

## `catalog/item_set_members.csv`

```csv
set_id,member_selectable_id,active
set_ls6_engine_covers_colored,opt_bcp_001,true
set_ls6_engine_covers_colored,opt_bcs_001,true
set_ls6_engine_covers_colored,opt_bc4_001,true
set_ls6_engine_covers_all,opt_bc7_001,true
set_ls6_engine_covers_all,opt_bcp_001,true
set_ls6_engine_covers_all,opt_bcs_001,true
set_ls6_engine_covers_all,opt_bc4_001,true
```

This is how you avoid duplicating `BCP`, `BCS`, and `BC4` in every rule.

---

## `catalog/aliases.csv`

Use this for duplicate labels, legacy workbook IDs, RPO aliases, or merged choices.

```csv
alias_id,alias_selectable_id,canonical_selectable_id,alias_type,merge_behavior,suppress_display,active,notes
alias_bcp_legacy,opt_bcp_legacy,opt_bcp_001,legacy_id,merge,true,true,"Old workbook identifier mapped to canonical BCP."
```

This lets you preserve old workbook references while compiling everything to canonical IDs.

---

# UI and availability schemas

## `ui/steps.csv`

```csv
step_id,step_key,label,display_order,active
step_exterior_appearance,exterior_appearance,Exterior Appearance,30,true
step_accessories,aero_exhaust_stripes_accessories,"Aero, Exhaust, Stripes & Accessories",70,true
```

## `ui/sections.csv`

```csv
section_id,step_id,label,category_key,display_order,selection_group_default,active
sec_engi_001,step_exterior_appearance,Engine Appearance,mechanical,10,multi_select_opt,true
sec_lpoe_001,step_accessories,LPO Exterior,mechanical,40,multi_select_opt,true
```

## `ui/selectable_display.csv`

Assigns selectables to sections without duplicating rows per variant unless necessary.

```csv
display_id,selectable_id,section_id,scope_condition_set_id,visible_when_condition_set_id,display_order,active
disp_b6p,opt_b6p_001,sec_engi_001,cs_coupe,,10,true
disp_bcp,opt_bcp_001,sec_engi_001,,,20,true
disp_bcs,opt_bcs_001,sec_engi_001,,,30,true
disp_bc4,opt_bc4_001,sec_engi_001,,,40,true
disp_sl1,opt_sl1_001,sec_lpoe_001,,,151,true
```

## `ui/availability.csv`

Availability belongs in data, not in Python.

```csv
availability_id,target_selector_type,target_selector_id,scope_condition_set_id,status,selectable,display_behavior,priority,message,active
av_b6p_coupe,selectable,opt_b6p_001,cs_coupe,available,true,selectable,10,,true
av_b6p_convertible,selectable,opt_b6p_001,cs_convertible,unavailable,false,hidden,10,"Only available on Coupe.",true
av_zz3_convertible,selectable,opt_zz3_001,cs_convertible,available,true,selectable,10,,true
```

Use availability when an option should be disabled/hidden based on variant context. Use dependency rules when an option may be selected but creates an open requirement.

---

# Condition engine

This is the most important part of the design.

## `logic/condition_sets.csv`

```csv
condition_set_id,label,description,active
cs_coupe,Coupe body style,,true
cs_convertible,Convertible body style,,true
cs_selected_b6p,B6P selected,,true
cs_coupe_with_b6p,Coupe with B6P selected,,true
cs_selected_zz3,ZZ3 selected,,true
cs_selected_colored_engine_cover,Any colored LS6 engine cover selected,,true
cs_a_and_b,A and B selected,Generic compound example,true
cs_selected_c,C selected,Generic compound target,true
```

## `logic/condition_terms.csv`

```csv
condition_set_id,or_group,term_order,term_type,left_ref,operator,right_value,negate
cs_coupe,g1,1,context,body_style,eq,coupe,false
cs_convertible,g1,1,context,body_style,eq,convertible,false
cs_selected_b6p,g1,1,selected,opt_b6p_001,is_true,,false
cs_coupe_with_b6p,g1,1,context,body_style,eq,coupe,false
cs_coupe_with_b6p,g1,2,selected,opt_b6p_001,is_true,,false
cs_selected_zz3,g1,1,selected,opt_zz3_001,is_true,,false
cs_selected_colored_engine_cover,g1,1,selected_any_in_set,set_ls6_engine_covers_colored,is_true,,false
cs_a_and_b,g1,1,selected,opt_a_001,is_true,,false
cs_a_and_b,g1,2,selected,opt_b_001,is_true,,false
cs_selected_c,g1,1,selected,opt_c_001,is_true,,false
```

Recommended `term_type` enum:

| `term_type`           | Meaning                                                                        |
| --------------------- | ------------------------------------------------------------------------------ |
| `context`             | Runtime context such as `body_style`, `trim_level`, `variant_id`, `model_year` |
| `selected`            | A specific selectable is selected                                              |
| `selected_any_in_set` | Any member of an item set is selected                                          |
| `selected_all_in_set` | All members of an item set are selected                                        |
| `attribute`           | Attribute of target/current item                                               |
| `pricebook`           | Active price book or model-year context                                        |

Recommended `operator` enum:

```text
eq
neq
in
not_in
is_true
is_false
gte
lte
exists
not_exists
```

---

# Dependency rules

## `logic/dependency_rules.csv`

```csv
rule_id,rule_type,subject_selector_type,subject_selector_id,subject_must_be_selected,applies_when_condition_set_id,target_condition_set_id,violation_behavior,message,priority,active
dep_a_b_requires_c,requires,global,,false,cs_a_and_b,cs_selected_c,block_submit,"A and B require C.",10,true
dep_colored_cover_requires_zz3_convertible,requires,selectable_set,set_ls6_engine_covers_colored,true,cs_convertible,cs_selected_zz3,disable_and_block,"Requires ZZ3 Convertible Engine Appearance Package.",10,true
```

The second row means:

```text
IF any member of set_ls6_engine_covers_colored is selected
AND body_style = convertible
THEN selected ZZ3 must be true.
```

That handles the “specific engine covers require ZZ3 only on Convertible body styles” requirement without a Python branch.

The current generated data already contains rule-like records for engine-cover inclusions and convertible-scoped ZZ3 requirements, so the migration target is to make those rows source data rather than generated or patched data. ([github.com](https://github.com/seanzmc/27vette/raw/refs/heads/main/form-output/stingray-form-data.json))

---

# Auto-added options

Auto-adds should be separate from dependency rules. A dependency says “you must also have X.” An auto-add says “the system adds X for you.”

## `logic/auto_adds.csv`

```csv
auto_add_id,source_selector_type,source_selector_id,trigger_condition_set_id,scope_condition_set_id,target_selectable_id,target_price_policy_id,quantity,if_target_already_selected,removal_policy,conflict_policy,cascade,priority,reason,active
aa_b6p_sl1,selectable,opt_b6p_001,,cs_coupe,opt_sl1_001,included_zero,1,convert_existing_to_included,remove_when_no_triggers,lowest_price_wins,true,10,"Selecting B6P includes SL1 at no charge.",true
aa_cover_d3v,selectable_set,set_ls6_engine_covers_colored,,cs_coupe,opt_d3v_001,included_zero,1,convert_existing_to_included,remove_when_no_triggers,lowest_price_wins,true,10,"Colored LS6 engine covers include D3V on Coupe.",true
```

## Auto-add lifecycle semantics

The compiler/runtime should track each selected line with provenance:

```text
explicit: user selected it
auto: one or more auto_add_id rules included it
```

Rules:

1. If a trigger is selected, add the target if absent.
2. If the target was already explicitly selected, do not duplicate it.
3. If `if_target_already_selected = convert_existing_to_included`, keep the line but apply the included price policy while the trigger remains active.
4. If a trigger is deselected:
   - remove the target only if it has no explicit provenance and no other active trigger;
   - if it was explicit before the trigger, restore the standalone price;
   - if multiple triggers include the same target, keep it until all triggers are inactive.
5. If auto-adds cascade, evaluate until fixed point.
6. Detect cycles and fail validation unless an explicit `allow_cycle` escape hatch exists.

This is important for cases like:

```text
User selects SL1 at $475.
User then selects B6P.
SL1 becomes included at $0.
User later deselects B6P.
SL1 returns to explicit $475.
```

---

# Exclusivity schemas

## `logic/exclusive_groups.csv`

```csv
exclusive_group_id,label,scope_condition_set_id,max_selected,conflict_policy,message,priority,active
excl_ls6_engine_covers,LS6 engine covers,,1,block_new_selection,"Choose only one LS6 engine cover.",10,true
excl_indoor_car_covers,Indoor car covers,,1,block_new_selection,"Choose only one indoor car cover.",10,true
```

## `logic/exclusive_group_members.csv`

```csv
exclusive_group_id,member_selectable_id,active
excl_ls6_engine_covers,opt_bc7_001,true
excl_ls6_engine_covers,opt_bcp_001,true
excl_ls6_engine_covers,opt_bcs_001,true
excl_ls6_engine_covers,opt_bc4_001,true
excl_indoor_car_covers,opt_rwh_001,true
excl_indoor_car_covers,opt_sl1_001,true
excl_indoor_car_covers,opt_wkr_001,true
excl_indoor_car_covers,opt_wkq_001,true
```

This directly replaces hard-coded exclusive group arrays in the generator.

---

# Pricing schemas

## `pricing/price_books.csv`

```csv
price_book_id,model_key,model_year,currency,effective_start,effective_end,source_ref_id,active,notes
pb_2027_stingray,stingray,2027,USD,2026-01-01,,src_2027_stingray_order_guide,true,2027 Stingray pricing
```

## `pricing/base_prices.csv`

Base prices can target individual selectables or sets. Set-level pricing reduces redundancy.

```csv
base_price_id,price_book_id,target_selector_type,target_selector_id,scope_condition_set_id,amount_usd,priority,active,notes
bp_engine_covers_coupe,pb_2027_stingray,selectable_set,set_ls6_engine_covers_colored,cs_coupe,695,10,true,"BCP/BCS/BC4 Coupe base price"
bp_sl1_standalone,pb_2027_stingray,selectable,opt_sl1_001,,475,10,true,"Standalone SL1 price"
bp_d3v_standalone,pb_2027_stingray,selectable,opt_d3v_001,,195,10,true,"Standalone D3V price if available"
```

If one member of a set later has a different price, add a more specific selectable-level row with higher priority.

---

## `pricing/price_policies.csv`

```csv
price_policy_id,policy_type,amount_usd,display_label,notes
normal,normal,,,
included_zero,force_amount,0,Included,"Auto-added or included at no charge"
suppress_line,suppress,,,"Do not show as a separate priced line"
```

---

## `pricing/price_rules.csv`

```csv
price_rule_id,price_book_id,target_selector_type,target_selector_id,applies_when_condition_set_id,price_action,amount_usd,lookup_table_id,lookup_key_template,stack_mode,priority,active,explanation
pr_engine_cover_b6p_static,pb_2027_stingray,selectable_set,set_ls6_engine_covers_colored,cs_coupe_with_b6p,set_static,595,,,exclusive,100,true,"BCP/BCS/BC4 are $595 on Coupe when B6P is selected."
```

Supported `price_action` values:

| Action                 | Meaning                          |
| ---------------------- | -------------------------------- |
| `set_static`           | Replace price with `amount_usd`  |
| `zero`                 | Force price to zero              |
| `add_static`           | Add `amount_usd`                 |
| `subtract_static`      | Subtract `amount_usd`            |
| `set_from_lookup`      | Replace price using lookup table |
| `add_from_lookup`      | Add lookup amount                |
| `subtract_from_lookup` | Subtract lookup amount           |

Recommended `stack_mode` values:

| `stack_mode`       | Meaning                                                             |
| ------------------ | ------------------------------------------------------------------- |
| `exclusive`        | Highest-priority matching set rule wins                             |
| `stack`            | Can combine with other additive/subtractive rules                   |
| `stop_after_apply` | Apply this rule and stop evaluating lower-priority rules for target |

For the engine-cover case, prefer:

```text
set_static = 595
```

over:

```text
subtract_static = 100
```

because the business rule says the price is `$595`, not necessarily “subtract `$100` from whatever the future base price is.”

---

## Dynamic lookup pricing

## `pricing/price_lookup_tables.csv`

```csv
lookup_table_id,label,key_template_schema,currency,active
lt_interior_component_prices,Interior component prices,"{context.trim_level}|{selected.interior.seat_code}|{target.rpo}",USD,true
```

## `pricing/price_lookup_rows.csv`

```csv
lookup_table_id,lookup_key,amount_usd,label,active
lt_interior_component_prices,3LT|AH2|N26,695,"3LT AH2 N26 suede component",true
lt_interior_component_prices,3LT|AE4|R6X,1500,"3LT AE4 R6X component",true
```

Example dynamic rule:

```csv
price_rule_id,price_book_id,target_selector_type,target_selector_id,applies_when_condition_set_id,price_action,amount_usd,lookup_table_id,lookup_key_template,stack_mode,priority,active,explanation
pr_interior_component_lookup,pb_2027_stingray,selectable_set,set_priced_interior_components,,set_from_lookup,,lt_interior_component_prices,"{context.trim_level}|{selected.interior.seat_code}|{target.rpo}",exclusive,50,true,"Interior component price is looked up dynamically."
```

Allowed lookup-template tokens should be strictly allowlisted:

```text
{context.body_style}
{context.trim_level}
{context.variant_id}
{context.model_year}
{price_book.model_year}
{selected.interior.seat_code}
{selected.interior.trim_level}
{target.rpo}
{target.attribute.<name>}
```

Do not allow arbitrary Python or JavaScript expressions in CSV.

---

# Deterministic price resolution order

Use this order everywhere:

1. Select active price book.
2. Find the most specific matching base price:
   - selectable-level beats set-level,
   - higher priority wins,
   - ambiguity at same priority is a validation error.
3. Apply auto-add price policy:
   - `included_zero` forces price to `0`;
   - `suppress_line` hides/suppresses the line;
   - explicit user provenance can be retained for explanation.
4. Apply matching `set_static`, `zero`, or `set_from_lookup` rules:
   - highest priority wins for `exclusive`;
   - same-priority conflicts fail validation.
5. Apply stackable additive/subtractive modifiers.
6. Emit price explanation metadata:

```json
{
  "base_price": 695,
  "matched_base_price_id": "bp_engine_covers_coupe",
  "matched_price_rules": ["pr_engine_cover_b6p_static"],
  "final_price": 595,
  "explanation": "BCP/BCS/BC4 are $595 on Coupe when B6P is selected."
}
```

---

# Worked examples

## A. “If A and B, then C”

```csv
# logic/condition_terms.csv
condition_set_id,or_group,term_order,term_type,left_ref,operator,right_value,negate
cs_a_and_b,g1,1,selected,opt_a_001,is_true,,false
cs_a_and_b,g1,2,selected,opt_b_001,is_true,,false
cs_selected_c,g1,1,selected,opt_c_001,is_true,,false
```

```csv
# logic/dependency_rules.csv
rule_id,rule_type,subject_selector_type,subject_selector_id,subject_must_be_selected,applies_when_condition_set_id,target_condition_set_id,violation_behavior,message,priority,active
dep_a_b_requires_c,requires,global,,false,cs_a_and_b,cs_selected_c,block_submit,"A and B require C.",10,true
```

No Python branch is needed.

---

## B. “B6P auto-adds SL1 at $0”

```csv
# logic/auto_adds.csv
auto_add_id,source_selector_type,source_selector_id,trigger_condition_set_id,scope_condition_set_id,target_selectable_id,target_price_policy_id,quantity,if_target_already_selected,removal_policy,conflict_policy,cascade,priority,reason,active
aa_b6p_sl1,selectable,opt_b6p_001,,cs_coupe,opt_sl1_001,included_zero,1,convert_existing_to_included,remove_when_no_triggers,lowest_price_wins,true,10,"Selecting B6P includes SL1 at no charge.",true
```

```csv
# pricing/price_policies.csv
price_policy_id,policy_type,amount_usd,display_label,notes
included_zero,force_amount,0,Included,"Auto-added or included at no charge"
```

SL1 can still have a normal standalone price in `base_prices.csv`; the inclusion policy overrides it only while the inclusion is active.

---

## C. Engine covers: `$695` on Coupe, include D3V at `$0`, drop to `$595` with B6P

```csv
# catalog/item_sets.csv
set_id,label,set_type,active,notes
set_ls6_engine_covers_colored,"BCP/BCS/BC4 LS6 engine covers",selectable_set,true,
```

```csv
# catalog/item_set_members.csv
set_id,member_selectable_id,active
set_ls6_engine_covers_colored,opt_bcp_001,true
set_ls6_engine_covers_colored,opt_bcs_001,true
set_ls6_engine_covers_colored,opt_bc4_001,true
```

```csv
# pricing/base_prices.csv
base_price_id,price_book_id,target_selector_type,target_selector_id,scope_condition_set_id,amount_usd,priority,active,notes
bp_engine_covers_coupe,pb_2027_stingray,selectable_set,set_ls6_engine_covers_colored,cs_coupe,695,10,true,"Base Coupe price"
```

```csv
# logic/auto_adds.csv
auto_add_id,source_selector_type,source_selector_id,trigger_condition_set_id,scope_condition_set_id,target_selectable_id,target_price_policy_id,quantity,if_target_already_selected,removal_policy,conflict_policy,cascade,priority,reason,active
aa_cover_d3v,selectable_set,set_ls6_engine_covers_colored,,cs_coupe,opt_d3v_001,included_zero,1,convert_existing_to_included,remove_when_no_triggers,lowest_price_wins,true,10,"Colored LS6 engine covers include D3V on Coupe.",true
```

```csv
# pricing/price_rules.csv
price_rule_id,price_book_id,target_selector_type,target_selector_id,applies_when_condition_set_id,price_action,amount_usd,lookup_table_id,lookup_key_template,stack_mode,priority,active,explanation
pr_engine_cover_b6p_static,pb_2027_stingray,selectable_set,set_ls6_engine_covers_colored,cs_coupe_with_b6p,set_static,595,,,exclusive,100,true,"Colored LS6 engine covers are $595 when B6P is selected."
```

---

## D. Engine covers require ZZ3 only on Convertible

```csv
# logic/dependency_rules.csv
rule_id,rule_type,subject_selector_type,subject_selector_id,subject_must_be_selected,applies_when_condition_set_id,target_condition_set_id,violation_behavior,message,priority,active
dep_colored_cover_requires_zz3_convertible,requires,selectable_set,set_ls6_engine_covers_colored,true,cs_convertible,cs_selected_zz3,disable_and_block,"Requires ZZ3 Convertible Engine Appearance Package.",10,true
```

This single row means:

```text
IF selected option is one of BCP/BCS/BC4
AND body_style = convertible
THEN ZZ3 must be selected.
```

---

# Supporting domains

Do not cram interiors, colors, and legacy price references into generic option rows. Add domain-specific tables as needed.

## `support/exterior_colors.csv`

```csv
color_id,selectable_id,rpo,color_name,color_family,active
color_gba,opt_gba_001,GBA,Black,black,true
color_g8g,opt_g8g_001,G8G,Arctic White,white,true
color_gkz,opt_gkz_001,GKZ,Torch Red,red,true
```

## `support/interiors.csv`

```csv
interior_id,selectable_id,trim_level,seat_code,color_code,requires_r6x,active
int_3lt_ah2,opt_ah2_001,3LT,AH2,,false,true
```

## `support/interior_components.csv`

```csv
component_id,interior_id,component_selectable_id,component_role,default_price_lookup_key,active
comp_ah2_n26,int_3lt_ah2,opt_n26_001,steering_wheel,3LT|AH2|N26,true
```

## `support/color_overrides.csv`

```csv
override_id,subject_selectable_id,scope_condition_set_id,effect_type,target_selectable_id,message,active
co_5zu_approved_colors,opt_5zu_001,cs_exterior_color_g8g_gba_gkz,available_when,,Requires approved body color.,true
```

## `support/legacy_price_refs.csv`

```csv
legacy_price_ref_id,source_ref_id,legacy_key,description,amount_usd,notes
lpr_r6x_delta,src_legacy_workbook,R6X_DELTA,R6X price delta,1500,Used during migration only
```

---

# Source, governance, and audit metadata

## `meta/source_refs.csv`

```csv
source_ref_id,source_type,title,model_year,version,published_date,imported_at,path_or_url,notes
src_2027_stingray_order_guide,order_guide,2027 Stingray Order Guide,2027,v1,2026-01-01,2026-05-01,docs/source/2027-stingray-order-guide.pdf,Primary source
src_stingray_master_xlsx,workbook,Legacy stingray_master.xlsx,2027,legacy,2026-04-01,2026-05-01,stingray_master.xlsx,Migration source
```

## `meta/change_log.csv`

```csv
change_id,changed_table,row_id,change_type,reason,source_ref_id,approved_by,approved_at
chg_0001,pricing.price_rules,pr_engine_cover_b6p_static,create,"Move B6P engine-cover price nuance out of Python.",src_stingray_master_xlsx,sean,2026-05-01
```

Recommended governance columns for business-rule tables:

```text
source_ref_id
effective_start
effective_end
status: active|deprecated|superseded|draft
approved_by
approved_at
change_id
```

Git history gives you technical auditability; row-level metadata gives you business auditability.

---

# Workbook-to-CSV migration crosswalk

A blind migration from workbook to CSV is risky. Before deleting `stingray_master.xlsx`, add a one-time inventory and crosswalk.

## `meta/workbook_column_map.csv`

```csv
source_workbook,source_sheet,source_column,source_semantic,target_csv,target_column,transform,required,migration_status,notes
stingray_master.xlsx,Options,RPO,rpo,catalog/selectables.csv,rpo,copy,true,mapped,
stingray_master.xlsx,Options,Description,description,catalog/selectables.csv,description,copy,false,mapped,
stingray_master.xlsx,Options,Price,amount_usd,pricing/base_prices.csv,amount_usd,parse_integer_usd,true,mapped,
stingray_master.xlsx,Options,Detail,source_detail_raw,catalog/selectables.csv,source_detail_raw,copy,false,mapped_do_not_parse,
```

Also create:

```text
scripts/inspect_stingray_workbook.py
```

Output:

```csv
source_sheet,column_name,row_count,non_null_count,sample_values,guessed_target_table,review_status
```

Migration gate:

```text
Every source workbook sheet/column must be:
  mapped,
  intentionally ignored,
  generated-only,
  or deprecated with explanation.
```

This addresses the biggest practical gap: the exact row-by-row workbook migration cannot be safely specified until the actual sheet inventory and column semantics are dumped and reviewed.

---

# Generated front-end contract mapping

Keep the current front-end contract stable while changing the source data. The compiler should adapt the new normalized CSVs into the existing generated shape.

The repo already uses `form-app/data.js` as embedded data and `form-output/` as generated inspection/handoff artifacts. ([github.com](https://github.com/seanzmc/27vette)) Existing generated choice records include fields like `choice_id`, `option_id`, `rpo`, `label`, `section_id`, `variant_id`, `body_style`, `trim_level`, `status`, `selectable`, `base_price`, `display_order`, and raw source detail. ([github.com](https://github.com/seanzmc/27vette/raw/refs/heads/main/form-output/stingray-form-data.json))

Recommended adapter mapping:

| Runtime/generated field                    | Source tables                                        |
| ------------------------------------------ | ---------------------------------------------------- |
| `choice_id`                                | `${variant_id}__${selectable_id}`                    |
| `option_id`                                | `catalog/selectables.selectable_id`                  |
| `rpo`                                      | `catalog/selectables.rpo`                            |
| `label`, `description`                     | `catalog/selectables`                                |
| `section_id`, `section_name`               | `ui/selectable_display` + `ui/sections`              |
| `step_key`                                 | `ui/sections` + `ui/steps`                           |
| `variant_id`, `body_style`, `trim_level`   | `catalog/variants`                                   |
| `status`, `selectable`, `display_behavior` | `ui/availability` resolved by condition sets         |
| `base_price`                               | `pricing/base_prices` resolved by price book/context |
| `priceRules` / price metadata              | `pricing/price_rules` + lookup tables                |
| `rules` / open requirements                | `logic/dependency_rules`                             |
| `autoAddedRpos`                            | `logic/auto_adds` + `pricing/price_policies`         |
| `exclusiveGroups`                          | `logic/exclusive_groups` + members                   |
| `source_detail_raw`                        | `catalog/selectables.source_detail_raw`              |

This lets you migrate the data model without rewriting the front-end all at once.

---

# Runtime processing order

The generic processor should do this:

```text
1. Load CSV package.
2. Validate table schemas.
3. Validate semantic constraints.
4. Normalize aliases to canonical selectable IDs.
5. Resolve variant context.
6. Load explicit user selections.
7. Check explicit selections against availability.
8. Apply exclusive groups and collect conflicts.
9. Apply auto-add closure.
10. Evaluate dependency rules and collect open requirements.
11. Price all selected and auto-added lines.
12. Emit:
    - normalized selected lines,
    - auto-added lines,
    - open requirements,
    - conflicts,
    - price explanations,
    - generated data.js/form-output artifacts.
```

The Python code should understand generic concepts:

```text
condition_set
selector
selectable_set
dependency_rule
auto_add
price_rule
lookup_table
exclusive_group
```

It should not know Corvette-specific concepts like B6P, ZZ3, BCP, SL1, or D3V.

---

# Validation strategy

Use two layers.

## Layer 1: table/schema validation

Handled by `datapackage.yaml`.

Validate:

- required columns,
- types,
- enum values,
- missing values,
- primary keys,
- foreign keys,
- regex patterns,
- integer money fields,
- booleans,
- dates.

Example manifest fragment:

```yaml
resources:
  - name: condition_terms
    path: logic/condition_terms.csv
    schema:
      primaryKey:
        - condition_set_id
        - or_group
        - term_order
      fields:
        - name: condition_set_id
          type: string
          constraints:
            required: true
            pattern: "^cs_[a-z0-9_]+$"
        - name: or_group
          type: string
          constraints:
            required: true
        - name: term_order
          type: integer
          constraints:
            required: true
            minimum: 1
        - name: term_type
          type: string
          constraints:
            required: true
            enum:
              - context
              - selected
              - selected_any_in_set
              - selected_all_in_set
              - attribute
              - pricebook
        - name: left_ref
          type: string
          constraints:
            required: true
        - name: operator
          type: string
          constraints:
            required: true
            enum:
              - eq
              - neq
              - in
              - not_in
              - is_true
              - is_false
              - exists
              - not_exists
        - name: right_value
          type: string
        - name: negate
          type: boolean
          constraints:
            required: true
      foreignKeys:
        - fields: condition_set_id
          reference:
            resource: condition_sets
            fields: condition_set_id
```

## Layer 2: semantic validation

Custom Python validation should fail CI if:

1. Any referenced selectable, set, condition set, variant, price book, or policy does not exist.
2. Any item set has no active members.
3. Any condition set cannot compile.
4. A condition set has impossible terms, such as `body_style = coupe` and `body_style = convertible` in the same AND group.
5. Any auto-add cycle exists unless explicitly allowed.
6. Any auto-add target lacks a price policy.
7. Any dependency rule lacks a human-readable message.
8. Two active static price rules can both win for the same target/scope/priority.
9. Additive/subtractive price rules are not explicitly stackable.
10. A displayed selectable has no availability behavior.
11. A selectable has no price behavior where one is required.
12. A `lookup_key_template` contains a token outside the allowlist.
13. A source note contains terms like `Requires`, `Included with`, `Not available with`, `Deletes`, or `without`, but no corresponding structured rule exists.
14. Effective dates overlap ambiguously for the same rule/price/scope.
15. Deprecated rows are still referenced by active rows without an explicit migration rule.

Practical Pydantic-style validation can sit on top of the table-schema validation:

```python
from pydantic import BaseModel, Field, model_validator
from typing import Literal

class AutoAddRow(BaseModel):
    auto_add_id: str
    source_selector_type: Literal["selectable", "selectable_set"]
    source_selector_id: str
    target_selectable_id: str
    target_price_policy_id: str
    quantity: int = Field(ge=1)
    active: bool

    @model_validator(mode="after")
    def validate_references(self):
        if self.source_selector_type == "selectable":
            assert self.source_selector_id in SELECTABLE_IDS, self.source_selector_id
        if self.source_selector_type == "selectable_set":
            assert self.source_selector_id in ITEM_SET_IDS, self.source_selector_id
        assert self.target_selectable_id in SELECTABLE_IDS, self.target_selectable_id
        assert self.target_price_policy_id in PRICE_POLICY_IDS, self.target_price_policy_id
        return self
```

---

# Spreadsheet editing workflow

CSV is the source, but spreadsheet editing should still be comfortable.

Recommended workflow:

```text
1. Edit CSV directly for simple changes.
2. Or run scripts/export_editor_workbook.py.
3. Business user edits generated stingray_editor.xlsx.
4. Protected ID columns stay locked.
5. Dropdowns come from enum_values.csv and referenced tables.
6. Run scripts/import_editor_workbook.py.
7. Run validation and golden tests.
8. Commit normalized CSV only.
```

Add safeguards:

- Format all ID/RPO columns as **Text** in the editor workbook.
- Use data-validation dropdowns for enums.
- Protect primary key columns unless explicitly unlocked.
- Add conditional formatting for inactive/deprecated rows.
- Freeze header rows.
- Generate one sheet per canonical CSV.
- Avoid formulas as source data.
- Normalize CSV ordering on save.
- Add pre-commit hooks:

```text
python scripts/validate_stingray_data.py
python scripts/compile_stingray_data.py --check
node --test tests/stingray-form-regression.test.mjs
```

Excel risks to guard against:

- auto-converting IDs,
- changing empty strings,
- trimming leading zeros,
- reformatting dates,
- sorting only one table region,
- saving with platform-specific encoding.

The validator should catch all of these before a PR is merged.

---

# Golden test matrix

Add golden build fixtures. This is essential before removing Python overrides.

## `validation/golden_builds.csv`

```csv
test_id,variant_id,explicit_selected_ids,description
gb_coupe_bcp,1lt_c07,opt_bcp_001,Coupe with BCP
gb_coupe_bcp_b6p,1lt_c07,"opt_bcp_001|opt_b6p_001",Coupe with BCP and B6P
gb_convertible_bcp_missing_zz3,1lt_c67,opt_bcp_001,Convertible BCP without ZZ3
gb_convertible_bcp_with_zz3,1lt_c67,"opt_bcp_001|opt_zz3_001",Convertible BCP with ZZ3
gb_exclusive_engine_covers,1lt_c07,"opt_bcp_001|opt_bc4_001",Two LS6 engine covers selected
gb_sl1_then_b6p,1lt_c07,"opt_sl1_001|opt_b6p_001",Explicit SL1 converted to included by B6P
```

Use a delimiter like `|` only in validation fixture convenience files if you choose; for canonical business logic, prefer child rows. Better normalized version:

## `validation/golden_build_selections.csv`

```csv
test_id,selectable_id
gb_coupe_bcp,opt_bcp_001
gb_coupe_bcp_b6p,opt_bcp_001
gb_coupe_bcp_b6p,opt_b6p_001
gb_convertible_bcp_missing_zz3,opt_bcp_001
```

## `validation/golden_expected_lines.csv`

```csv
test_id,line_selectable_id,expected_final_price_usd,expected_provenance,expected_status
gb_coupe_bcp,opt_bcp_001,695,explicit,selected
gb_coupe_bcp,opt_d3v_001,0,auto,auto_added
gb_coupe_bcp_b6p,opt_bcp_001,595,explicit,selected
gb_coupe_bcp_b6p,opt_d3v_001,0,auto,auto_added
gb_coupe_bcp_b6p,opt_sl1_001,0,auto,auto_added
gb_sl1_then_b6p,opt_sl1_001,0,explicit+auto,included
```

## `validation/golden_expected_requirements.csv`

```csv
test_id,required_condition_set_id,expected_behavior,message
gb_convertible_bcp_missing_zz3,cs_selected_zz3,block_submit,"Requires ZZ3 Convertible Engine Appearance Package."
```

## `validation/golden_expected_conflicts.csv`

```csv
test_id,conflict_type,conflict_id,message
gb_exclusive_engine_covers,exclusive_group,excl_ls6_engine_covers,"Choose only one LS6 engine cover."
```

At minimum, add golden tests for:

- B6P auto-adds SL1 at $0.
- Engine covers add D3V at $0 on Coupe.
- Engine covers are $695 on Coupe without B6P.
- Engine covers are $595 on Coupe with B6P.
- Engine covers require ZZ3 on Convertible.
- Deselecting B6P restores/removes SL1 correctly.
- Multiple triggers for the same target do not duplicate lines.
- Exclusive groups block conflicting selections.
- Generated `form-app/data.js` remains contract-compatible.

---

# Migration plan

## Phase 0 — Inventory the workbook

Add the workbook inspector and `workbook_column_map.csv`.

Do not delete or replace `stingray_master.xlsx` until every sheet/column has an explicit migration decision.

## Phase 1 — Introduce CSV package beside workbook

Add:

```text
data/stingray/datapackage.yaml
data/stingray/catalog/*
data/stingray/logic/*
data/stingray/pricing/*
```

Start with a narrow slice: engine appearance only.

Seed:

- B6P,
- SL1,
- D3V,
- ZZ3,
- BCP,
- BCS,
- BC4,
- Coupe/Convertible variants,
- engine-cover set,
- B6P → SL1 auto-add,
- engine cover → D3V auto-add,
- engine cover $695/$595 pricing,
- Convertible ZZ3 requirement.

Compile both old and new output and compare.

## Phase 2 — Move hard-coded groups into CSV

Move current hard-coded structures out of `generate_stingray_form.py`:

- rule groups,
- exclusive groups,
- same-section exclusion behavior,
- manually patched inclusions,
- body-style/trim/variant scopes.

The script should load those from CSV.

## Phase 3 — Move pricing into CSV

Add:

- `price_books.csv`,
- `base_prices.csv`,
- `price_policies.csv`,
- `price_rules.csv`,
- lookup tables.

Remove hard-coded price overrides and manual price transformations from Python.

## Phase 4 — Move availability/UI grouping into CSV

Move:

- steps,
- sections,
- display order,
- per-variant availability,
- body/trim scope,
- hidden/display-only behavior.

## Phase 5 — Migrate supporting domains

Move:

- interiors,
- exterior colors,
- color overrides,
- interior component pricing,
- aliases,
- legacy price references.

## Phase 6 — Make workbook generated only

After parity tests pass:

```text
stingray_master.xlsx -> archived or generated editor workbook
CSV package          -> canonical source
form-output/*        -> generated
form-app/data.js     -> generated
```

CI should fail if generated artifacts are stale.

---

# Minimal implementation path

If you want the smallest useful first cut, start with these files only:

```text
catalog/variants.csv
catalog/selectables.csv
catalog/options.csv
catalog/item_sets.csv
catalog/item_set_members.csv

logic/condition_sets.csv
logic/condition_terms.csv
logic/dependency_rules.csv
logic/auto_adds.csv
logic/exclusive_groups.csv
logic/exclusive_group_members.csv

pricing/price_books.csv
pricing/base_prices.csv
pricing/price_policies.csv
pricing/price_rules.csv

ui/steps.csv
ui/sections.csv
ui/selectable_display.csv
ui/availability.csv

datapackage.yaml
```

That is enough to remove the hard-coded business logic for the examples you listed.

---

# Final blueprint summary

Use **modular CSV files governed by a strict Data Package/Table Schema manifest**.

The core design is:

```text
Catalog:
  selectables, options, variants, item sets, aliases

UI:
  steps, sections, display, availability

Logic:
  condition sets, condition terms, dependency rules, auto-adds, exclusive groups

Pricing:
  price books, base prices, price policies, price rules, lookup tables

Validation:
  table schema, semantic checks, golden builds

Governance:
  source refs, change log, effective dates, workbook column map
```

This design supports:

- compound logic: `condition_sets.csv` + `condition_terms.csv`;
- “If A and B, then C”: `dependency_rules.csv`;
- auto-added options: `auto_adds.csv`;
- B6P → SL1 at `$0`: auto-add + included-zero price policy;
- BCP/BCS/BC4 → D3V at `$0`: auto-add scoped to Coupe;
- engine covers `$695` on Coupe: set-level base price;
- engine covers `$595` with B6P: scoped static price rule;
- Convertible ZZ3 dependency: condition-scoped dependency rule;
- static price overrides;
- dynamic lookup-key pricing;
- additive/subtractive price modifiers;
- exclusive groups;
- body/trim/variant availability;
- source traceability;
- strict validation;
- spreadsheet-style editing;
- generated `form-app/data.js` compatibility.

The result is a maintainable data-first architecture: Python interprets validated rows, while all Corvette business rules live in the CSV package.
