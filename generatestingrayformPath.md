You’re right. Scratch the combined-table idea. For this repo, the clean path is:

`stingray_options shape` + `stingray status sheet`  
`grand_sport_options same shape` + `grand_sport status sheet`

Different sheets, same columns, same generator expectations.

**Stingray Form Source Map**

Production Stingray is generated in [generate_stingray_form.py](/Users/seandm/Projects/27vette/scripts/generate_stingray_form.py:445). These source sheets feed the form outputs:

| Source sheet                                                  | Columns actually used                                                                                                                                                                                                                                                                    | Feeds                                                                                   |
| ------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------- |
| `variant_master`                                              | `variant_id`, `model_year`, `trim_level`, `body_style`, `display_name`, `base_price`, `display_order`, `active`                                                                                                                                                                          | `variants`, body/trim `contextChoices`, every `choice.variant_id/body_style/trim_level` |
| `stingray_master`                                             | `option_id`, `rpo`, `price`, `option_name`, `description`, `detail_raw`, `section_id`, `selectable`, `display_order`, `active`, `display_behavior`                                                                                                                                       | `choices`, `standardEquipment`, rule/price validation                                   |
| `option_variant_status`                                       | `option_id`, `variant_id`, `status`                                                                                                                                                                                                                                                      | per-variant choice `status`, `status_label`, standard equipment                         |
| `section_master`                                              | `section_id`, `section_name`, `category_id`, `selection_mode`, `is_required`, `display_order`, `standard_behavior`                                                                                                                                                                       | `sections`, choice section metadata, choice mode, steps                                 |
| `category_master`                                             | `category_id`, `category_name`                                                                                                                                                                                                                                                           | section/choice category labels                                                          |
| `rule_mapping`                                                | `rule_id`, `source_id`, `rule_type`, `target_id`, `target_type`, `original_detail_raw`, `review_flag`, `source_type`, `target_selection_mode`, `source_selection_mode`, `target_section`, `source_section`, `generation_action`, `body_style_scope`, `runtime_action`, `disabled_reason` | `rules`                                                                                 |
| `rule_groups` + `rule_group_members`                          | group metadata + member `target_id`s                                                                                                                                                                                                                                                     | `ruleGroups`                                                                            |
| `exclusive_groups` + `exclusive_group_members`                | group metadata + member `option_id`s                                                                                                                                                                                                                                                     | `exclusiveGroups`                                                                       |
| `price_rules`                                                 | `price_rule_id`, `condition_option_id`, `price_rule_type`, `target_option_id`, `price_value`, `body_style_scope`, `trim_level_scope`, `variant_scope`, `review_flag`, `notes`                                                                                                            | `priceRules`                                                                            |
| `lt_interiors`, `LZ_Interiors`, `PriceRef`, `color_overrides` | interior-specific columns                                                                                                                                                                                                                                                                | `interiors`, `colorOverrides`                                                           |

For the **main option sheet**, Grand Sport should mirror `stingray_master`, not its current mixed-case shape.

Canonical option sheet columns to focus on:

```text
option_id
rpo
price
option_name
description
detail_raw
section_id
selectable
display_order
active
display_behavior
```

Likely clear or ignore from Stingray option source:

- `source_domain` is currently not used by the production generator.
- Any old per-variant status columns should not be on the option sheet.
- Any `Category`/category column should not be needed if `section_id -> section_master.category_id` is the source of truth.

Grand Sport should become:

```text
grandSport / grand_sport_options:
option_id, rpo, price, option_name, description, detail_raw, section_id,
selectable, display_order, active, display_behavior

gs_option_variant_status:
option_id, variant_id, status
```

The important sync rule is:

For each row in `grandSport` where `active=True`, there should be one row in `gs_option_variant_status` for each configured Grand Sport variant in `GRAND_SPORT_MODEL.variant_ids`, even while those variants remain inactive in `variant_master`.

That gives you consistency without combining model data.
