# Grand Sport Source Cleanup Audit

Generated from the saved workbook after the trim-scoped selectability pass.

## Summary

- Grand Sport option rows: 269.
- Active Grand Sport option rows: 229.
- OVS coverage: 269 option ids in `grandSport_ovs`; missing option ids: none.
- Active duplicate RPO groups remaining: 0.
- Active non-selectable rows without `display_behavior`: 84; these are standard/included equipment source rows, not visible selectable cards.
- Inactive option references in source rule/group sheets: 23 raw references; current draft generator omits inactive/unemitted rule rows.
- Sections with active Grand Sport rows: 30.
- Sections with no active Grand Sport rows: 7.
- Variant option override rows: 4 in `grandSport_variant_overrides`.

## Workbook Changes Applied

These duplicate or mirror rows are inactive now; their `grandSport_ovs` rows remain intact:

- `opt_719_002` / `719` from `sec_stan_002`: `active=False`.
- `opt_cf7_002` / `CF7` from `sec_stan_002`: `active=False`.
- `opt_cm9_002` / `CM9` from `sec_stan_002`: `active=False`.
- `opt_efr_002` / `EFR` from `sec_stan_002`: `active=False`.
- `opt_eyt_002` / `EYT` from `sec_stan_002`: `active=False`.
- `opt_j6a_002` / `J6A` from `sec_stan_002`: `active=False`.
- `opt_nga_002` / `NGA` from `sec_stan_002`: `active=False`.
- `opt_swm_002` / `SWM` from `sec_stan_002`: `active=False`.
- `opt_ah2_003` / `AH2` from `sec_3lte_001`: `active=False`.
- `opt_aq9_004` / `AQ9` from `sec_1lte_001`: `active=False`.
- `opt_aq9_003` / `AQ9` from `sec_2lte_001`: `active=False`.
- `opt_aup_001` / `AUP` from `sec_seat_002`: `active=False`.
- `opt_t0e_001` / `T0E` from `sec_stan_002`: `active=False`.
- `opt_uqt_002` / `UQT` from `sec_2lte_001`: `active=False`.

`grandSport_variant_overrides` rows now provide variant-scoped generated choice behavior:

| Option | Variant | Selectable | Display behavior | Section | Note |
| --- | --- | --- | --- | --- | --- |
| `opt_uqt_001` | `2lt_e07` | `False` | `display_only` | `sec_2lte_001` | 2LT included equipment. |
| `opt_uqt_001` | `2lt_e67` | `False` | `display_only` | `sec_2lte_001` | 2LT included equipment. |
| `opt_uqt_001` | `3lt_e07` | `False` | `display_only` | `sec_3lte_001` | 3LT included equipment. |
| `opt_uqt_001` | `3lt_e67` | `False` | `display_only` | `sec_3lte_001` | 3LT included equipment. |

## Active Duplicate RPOs Remaining

- none

## Inactive Option References From Rule/Group Sources

| Sheet | Row | Field | Option | RPO | Note |
| --- | --- | --- | --- | --- | --- |
| `grandSport_rule_mapping` | `gs_rule_opt_bc4_001_includes_opt_d3v_001` | `source_id` | `opt_bc4_001` | `BC4` | omitted by inactive/unemitted runtime filter |
| `grandSport_rule_mapping` | `gs_copy_rule_opt_bc4_001_includes_opt_d3v_001_opt_bc4_001_includes_opt_d3v_001_coupe` | `source_id` | `opt_bc4_001` | `BC4` | omitted by inactive/unemitted runtime filter |
| `grandSport_rule_mapping` | `gs_rule_opt_bcp_001_includes_opt_d3v_001` | `source_id` | `opt_bcp_001` | `BCP` | omitted by inactive/unemitted runtime filter |
| `grandSport_rule_mapping` | `gs_copy_rule_opt_bcp_001_includes_opt_d3v_001_opt_bcp_001_includes_opt_d3v_001_coupe` | `source_id` | `opt_bcp_001` | `BCP` | omitted by inactive/unemitted runtime filter |
| `grandSport_rule_mapping` | `gs_rule_opt_bcs_001_includes_opt_d3v_001` | `source_id` | `opt_bcs_001` | `BCS` | omitted by inactive/unemitted runtime filter |
| `grandSport_rule_mapping` | `gs_copy_rule_opt_bcs_001_includes_opt_d3v_001_opt_bcs_001_includes_opt_d3v_001_coupe` | `source_id` | `opt_bcs_001` | `BCS` | omitted by inactive/unemitted runtime filter |
| `grandSport_rule_mapping` | `gs_rule_opt_009_requires_opt_ue1_001` | `source_id` | `opt_009` | `` | omitted by inactive/unemitted runtime filter |
| `grandSport_rule_mapping` | `gs_rule_opt_009_requires_opt_ue1_001` | `target_id` | `opt_ue1_001` | `UE1` | omitted by inactive/unemitted runtime filter |
| `grandSport_rule_mapping` | `gs_rule_opt_bc4_001_requires_opt_b6p_001_coupe` | `source_id` | `opt_bc4_001` | `BC4` | omitted by inactive/unemitted runtime filter |
| `grandSport_rule_mapping` | `gs_copy_rule_opt_bc4_002_requires_opt_zz3_001_opt_bc4_001_requires_opt_zz3_001_convertible` | `source_id` | `opt_bc4_001` | `BC4` | omitted by inactive/unemitted runtime filter |
| `grandSport_rule_mapping` | `gs_rule_opt_bcp_001_requires_opt_b6p_001_coupe` | `source_id` | `opt_bcp_001` | `BCP` | omitted by inactive/unemitted runtime filter |
| `grandSport_rule_mapping` | `gs_rule_opt_bcp_001_requires_opt_d3v_001_coupe` | `source_id` | `opt_bcp_001` | `BCP` | omitted by inactive/unemitted runtime filter |
| `grandSport_rule_mapping` | `gs_copy_rule_opt_bcp_002_requires_opt_zz3_001_opt_bcp_001_requires_opt_zz3_001_convertible` | `source_id` | `opt_bcp_001` | `BCP` | omitted by inactive/unemitted runtime filter |
| `grandSport_rule_mapping` | `gs_rule_opt_bcs_001_requires_opt_b6p_001_coupe` | `source_id` | `opt_bcs_001` | `BCS` | omitted by inactive/unemitted runtime filter |
| `grandSport_rule_mapping` | `gs_rule_opt_bcs_001_requires_opt_d3v_001_coupe` | `source_id` | `opt_bcs_001` | `BCS` | omitted by inactive/unemitted runtime filter |
| `grandSport_rule_mapping` | `gs_copy_rule_opt_bcs_002_requires_opt_zz3_001_opt_bcs_001_requires_opt_zz3_001_convertible` | `source_id` | `opt_bcs_001` | `BCS` | omitted by inactive/unemitted runtime filter |
| `grandSport_rule_mapping` | `gs_rule_opt_prb_001_requires_opt_ue1_001` | `source_id` | `opt_prb_001` | `PRB` | omitted by inactive/unemitted runtime filter |
| `grandSport_rule_mapping` | `gs_rule_opt_prb_001_requires_opt_ue1_001` | `target_id` | `opt_ue1_001` | `UE1` | omitted by inactive/unemitted runtime filter |
| `grandSport_rule_mapping` | `gs_rule_opt_sig_001_requires_opt_t0e_001` | `target_id` | `opt_t0e_001` | `T0E` | omitted by inactive/unemitted runtime filter |
| `grandSport_exclusive_members` | `gs_excl_ls6_engine_covers` | `option_id` | `opt_bc4_001` | `BC4` | omitted by inactive/unemitted runtime filter |
| `grandSport_exclusive_members` | `gs_excl_ls6_engine_covers` | `option_id` | `opt_bcp_001` | `BCP` | omitted by inactive/unemitted runtime filter |
| `grandSport_exclusive_members` | `gs_excl_ls6_engine_covers` | `option_id` | `opt_bcs_001` | `BCS` | omitted by inactive/unemitted runtime filter |
| `grandSport_exclusive_members` | `gs_excl_ground_effects` | `option_id` | `opt_cfv_001` | `CFV` | omitted by inactive/unemitted runtime filter |

## Special Surface Review

| RPO | Option | Active | Selectable | Display behavior | Section | Order | Notes |
| --- | --- | --- | --- | --- | --- | ---: | --- |
| `36S` | `opt_36s_001` | `False` | `False` | `` | `sec_cust_002` | 20 | interior-only/component-only suppressed from normal options |
| `37S` | `opt_37s_001` | `False` | `False` | `` | `sec_cust_002` | 30 | interior-only/component-only suppressed from normal options |
| `38S` | `opt_38s_001` | `False` | `False` | `` | `sec_cust_002` | 10 | interior-only/component-only suppressed from normal options |
| `5ZV` | `opt_5zv_001` | `True` | `TRUE` | `` | `sec_spoi_001` | 20 |  |
| `719` | `opt_719_001` | `True` | `TRUE` | `` | `sec_seat_001` | 10 |  |
| `719` | `opt_719_002` | `False` | `FALSE` | `` | `sec_stan_002` | 70 | inactive after cleanup pass |
| `AH2` | `opt_ah2_001` | `True` | `TRUE` | `` | `sec_seat_002` | 25 |  |
| `AH2` | `opt_ah2_002` | `False` | `TRUE` | `` | `sec_seat_002` | 70 |  |
| `AH2` | `opt_ah2_003` | `False` | `FALSE` | `` | `sec_3lte_001` | 10 | inactive after cleanup pass |
| `AQ9` | `opt_aq9_001` | `True` | `TRUE` | `` | `sec_seat_002` | 10 | canonical row; standard for 1LT/2LT via OVS |
| `AQ9` | `opt_aq9_002` | `False` | `TRUE` | `` | `sec_seat_002` | 20 |  |
| `AQ9` | `opt_aq9_003` | `False` | `FALSE` | `` | `sec_2lte_001` | 90 | inactive after cleanup pass |
| `AQ9` | `opt_aq9_004` | `False` | `FALSE` | `` | `sec_1lte_001` | 10 | inactive after cleanup pass |
| `AUP` | `opt_aup_001` | `False` | `TRUE` | `` | `sec_seat_002` | 80 | interior-only/component-only suppressed from normal options |
| `B6P` | `opt_b6p_001` | `True` | `TRUE` | `` | `sec_engi_001` | 1 |  |
| `BC4` | `opt_bc4_001` | `False` | `TRUE` | `` | `sec_engi_001` | 45 |  |
| `BC4` | `opt_bc4_002` | `True` | `TRUE` | `` | `sec_engi_001` | 27 |  |
| `BC7` | `opt_bc7_001` | `True` | `TRUE` | `` | `sec_engi_001` | 20 |  |
| `BCP` | `opt_bcp_001` | `False` | `TRUE` | `` | `sec_engi_001` | 35 |  |
| `BCP` | `opt_bcp_002` | `True` | `TRUE` | `` | `sec_engi_001` | 25 |  |
| `BCS` | `opt_bcs_001` | `False` | `TRUE` | `` | `sec_engi_001` | 40 |  |
| `BCS` | `opt_bcs_002` | `True` | `TRUE` | `` | `sec_engi_001` | 26 |  |
| `CF7` | `opt_cf7_001` | `True` | `TRUE` | `` | `sec_roof_001` | 10 |  |
| `CF7` | `opt_cf7_002` | `False` | `FALSE` | `` | `sec_stan_002` | 60 | inactive after cleanup pass |
| `CFL` | `opt_cfl_001` | `True` | `TRUE` | `` | `sec_perf_001` | 30 |  |
| `CFV` | `opt_cfv_001` | `False` | `TRUE` | `` | `sec_perf_001` | 40 | inactive/deferred ground effects row |
| `CFZ` | `opt_cfz_001` | `True` | `TRUE` | `` | `sec_perf_001` | 50 |  |
| `CM9` | `opt_cm9_001` | `True` | `TRUE` | `` | `sec_roof_001` | 20 |  |
| `CM9` | `opt_cm9_002` | `False` | `FALSE` | `` | `sec_stan_002` | 30 | inactive after cleanup pass |
| `D3V` | `opt_d3v_001` | `True` | `TRUE` | `` | `sec_engi_001` | 10 |  |
| `EFR` | `opt_efr_001` | `True` | `TRUE` | `` | `sec_exte_001` | 10 |  |
| `EFR` | `opt_efr_002` | `False` | `FALSE` | `` | `sec_stan_002` | 50 | inactive after cleanup pass |
| `EYT` | `opt_eyt_001` | `True` | `TRUE` | `` | `sec_badg_001` | 10 |  |
| `EYT` | `opt_eyt_002` | `False` | `FALSE` | `` | `sec_stan_002` | 20 | inactive after cleanup pass |
| `FEB` | `opt_feb_001` | `True` | `TRUE` | `` | `sec_perf_001` | 60 |  |
| `FEY` | `opt_fey_001` | `True` | `TRUE` | `` | `sec_perf_001` | 70 |  |
| `J57` | `opt_j57_001` | `True` | `TRUE` | `` | `sec_perf_001` | 80 |  |
| `J6A` | `opt_j6a_001` | `True` | `TRUE` | `` | `sec_cali_001` | 10 |  |
| `J6A` | `opt_j6a_002` | `False` | `FALSE` | `` | `sec_stan_002` | 10 | inactive after cleanup pass |
| `NGA` | `opt_nga_001` | `True` | `TRUE` | `` | `sec_exha_001` | 10 |  |
| `NGA` | `opt_nga_002` | `False` | `FALSE` | `` | `sec_stan_002` | 40 | inactive after cleanup pass |
| `PCQ` | `opt_pcq_001` | `True` | `TRUE` | `` | `sec_lpoe_001` | 45 |  |
| `PEF` | `opt_pef_001` | `True` | `TRUE` | `` | `sec_lpoi_001` | 30 |  |
| `R6P` | `opt_r6p_001` | `False` | `TRUE` | `` | `sec_onst_001` | 20 | OnStar/deferred inactive |
| `R6X` | `opt_r6x_001` | `True` | `False` | `display_only` | `sec_colo_001` | 20 | display-only row retained |
| `R88` | `opt_r88_001` | `True` | `TRUE` | `` | `sec_lpoe_001` | 21 |  |
| `R9V` | `opt_r9v_001` | `False` | `TRUE` | `` | `sec_onst_001` | 50 | OnStar/deferred inactive |
| `R9W` | `opt_r9w_001` | `False` | `TRUE` | `` | `sec_onst_001` | 10 | OnStar/deferred inactive |
| `R9Y` | `opt_r9y_001` | `False` | `TRUE` | `` | `sec_onst_001` | 40 | OnStar/deferred inactive |
| `SFZ` | `opt_sfz_001` | `True` | `TRUE` | `` | `sec_lpoe_001` | 20 |  |
| `SL9` | `opt_sl9_001` | `True` | `TRUE` | `` | `sec_engi_001` | 11 |  |
| `SWM` | `opt_swm_001` | `True` | `TRUE` | `` | `sec_whee_002` | 10 |  |
| `SWM` | `opt_swm_002` | `False` | `FALSE` | `` | `sec_stan_002` | 100 | inactive after cleanup pass |
| `T0E` | `opt_t0e_001` | `False` | `FALSE` | `` | `sec_stan_002` | 110 | inactive after cleanup pass |
| `T0E` | `opt_t0e_002` | `True` | `FALSE` | `` | `sec_incl_001` | 50 |  |
| `T0F` | `opt_t0f_001` | `True` | `TRUE` | `` | `sec_perf_001` | 90 |  |
| `U2K` | `opt_u2k_001` | `False` | `FALSE` | `` | `sec_onst_001` | 90 | OnStar/deferred inactive |
| `UQT` | `opt_uqt_001` | `True` | `TRUE` | `` | `sec_inte_001` | 10 | canonical row; trim-scoped overrides make 2LT/3LT included equipment |
| `UQT` | `opt_uqt_002` | `False` | `FALSE` | `` | `sec_2lte_001` | 20 | inactive after cleanup pass |
| `Z15` | `opt_z15_001` | `True` | `False` | `display_only` | `sec_stri_001` | 190 |  |
| `Z25` | `opt_z25_001` | `True` | `TRUE` | `` | `sec_spec_001` | 10 |  |
| `ZZ3` | `opt_zz3_001` | `True` | `TRUE` | `` | `sec_engi_001` | 5 |  |

## Active Sections And Step Placement

| Section | Name | Step | Section order | Active rows | Option order range | Duplicate option orders |
| --- | --- | --- | ---: | ---: | --- | --- |
| `sec_1lte_001` | 1LT Equipment | `standard_equipment` | 10 | 4 | 20-50 | none |
| `sec_incl_001` | Included | `standard_equipment` | 10 | 7 | 10-70 | none |
| `sec_pain_001` | Paint | `paint` | 10 | 10 | 10-100 | none |
| `sec_perf_001` | Performance | `packages_performance` | 10 | 8 | 10-90 | none |
| `sec_roof_001` | Roof | `exterior_appearance` | 10 | 7 | 10-70 | none |
| `sec_seat_002` | Seats | `seat` | 10 | 3 | 10-40 | none |
| `sec_stan_002` | Standard Options | `standard_equipment` | 10 | 2 | 80-90 | none |
| `sec_whee_002` | Wheels | `wheels` | 10 | 7 | 10-70 | none |
| `sec_2lte_001` | 2LT Equipment | `standard_equipment` | 20 | 19 | 10-210 | none |
| `sec_cali_001` | Caliper Color | `wheels` | 20 | 7 | 10-70 | none |
| `sec_exte_001` | Exterior Accents | `exterior_appearance` | 20 | 3 | 10-30 | none |
| `sec_seat_001` | Seat Belt | `seat_belt` | 20 | 6 | 10-60 | none |
| `sec_stan_001` | Standard Equipment | `standard_equipment` | 20 | 34 | 10-340 | none |
| `sec_3lte_001` | 3LT Equipment | `standard_equipment` | 30 | 2 | 20-30 | none |
| `sec_badg_001` | Badges | `exterior_appearance` | 30 | 2 | 10-20 | none |
| `sec_exha_001` | Exhaust | `aero_exhaust_stripes_accessories` | 30 | 3 | 10-30 | none |
| `sec_safe_001` | Safety Features | `standard_equipment` | 30 | 13 | 10-130 | none |
| `sec_whee_001` | Wheel Accessory | `wheels` | 30 | 7 | 10-70 | none |
| `sec_engi_001` | Engine Appearance | `exterior_appearance` | 40 | 11 | 1-70 | none |
| `sec_inte_001` | Interior Trim | `interior_trim` | 40 | 3 | 10-30 | none |
| `sec_tech_001` | Technology | `standard_equipment` | 40 | 3 | 10-30 | none |
| `sec_lpoi_001` | LPO Interior | `interior_trim` | 45 | 13 | 5-82 | none |
| `sec_colo_001` | Color Override | `interior_trim` | 50 | 2 | 10-20 | none |
| `sec_stri_001` | Stripes | `aero_exhaust_stripes_accessories` | 50 | 19 | 10-190 | none |
| `sec_gsce_001` | GS Center Stripes | `exterior_appearance` | 51 | 5 | 10-50 | none |
| `sec_gsha_001` | GS Hash Marks | `exterior_appearance` | 52 | 6 | 10-60 | none |
| `sec_spoi_001` | Spoiler | `aero_exhaust_stripes_accessories` | 80 | 1 | 20-20 | none |
| `sec_lpoe_001` | LPO Exterior | `aero_exhaust_stripes_accessories` | 90 | 18 | 10-90 | none |
| `sec_spec_001` | Special Edition | `packages_performance` | 110 | 1 | 10-10 | none |
| `sec_cust_001` | Custom Delivery | `delivery` | 120 | 3 | 10-30 | none |

## Sections With No Active Grand Sport Choices

| Section | Name | Step | Section order |
| --- | --- | --- | ---: |
| `sec_intc_001` | 1LT Interior | `base_interior` | 15 |
| `sec_intc_002` | 2LT Interior | `base_interior` | 16 |
| `sec_intc_003` | 3LT Interior | `base_interior` | 17 |
| `sec_susp_001` | Suspension | `packages_performance` | 20 |
| `sec_cust_002` | Custom Stitch | `interior_trim` | 55 |
| `sec_onst_001` | OnStar | `interior_trim` | 70 |
| `sec_lpow_001` | LPO Wheels | `aero_exhaust_stripes_accessories` | 100 |

## Remaining Notes

- Active duplicate RPO cleanup is closed for this pass.
- Some inactive rule/group source references remain as source evidence; generated runtime rules omit inactive/unemitted rows.
- Broader section/display-order cleanup remains separate from this trim-scoped selectability pass.

## Display Order Anomalies

- No duplicate active option display_order values found within active Grand Sport sections.
