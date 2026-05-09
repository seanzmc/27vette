# Grand Sport Source Cleanup Audit

Generated from the saved workbook after the category-removal pass and the two safe deactivations in this pass.

## Summary

- Grand Sport option rows: 269.
- Active Grand Sport option rows: 241.
- OVS coverage: 269 option ids in `grandSport_ovs`; missing option ids: none.
- Active duplicate RPO groups remaining: 11.
- Active non-selectable rows without `display_behavior`: 96; these are standard/included equipment rows, not visible selectable cards.
- Inactive option references in active source rule/group sheets: 23 raw references; current draft generator omits inactive/unemitted rule rows.
- Sections with active Grand Sport rows: 30.
- Sections with no active Grand Sport rows: 7.

## Workbook Changes Applied In This Pass

- `opt_aup_001` / `AUP` set `active=FALSE` because it is an interior-only/asymmetrical interior row, not a normal seat option.
- `opt_t0e_001` / `T0E` set `active=FALSE` because `opt_t0e_002` remains the canonical active standard/included T0E row.
- `grandSport_ovs` rows were left intact for both inactive rows.

## Active Duplicate RPOs Remaining

| RPO | Active rows | Assessment |
| --- | --- | --- |
| `719` | `opt_719_001` `sec_seat_001` selectable=TRUE status-source-kept; `opt_719_002` `sec_stan_002` selectable=FALSE status-source-kept | Mostly selectable/standard-equipment mirror. Do not deactivate blindly until standard-equipment summary can use the selectable standard row without losing customer included-equipment output. |
| `AH2` | `opt_ah2_003` `sec_3lte_001` selectable=FALSE status-source-kept; `opt_ah2_001` `sec_seat_002` selectable=TRUE status-source-kept | Seat selectable row plus trim-equipment standard mirrors; keep until trim equipment copy is intentionally collapsed. |
| `AQ9` | `opt_aq9_004` `sec_1lte_001` selectable=FALSE status-source-kept; `opt_aq9_003` `sec_2lte_001` selectable=FALSE status-source-kept; `opt_aq9_001` `sec_seat_002` selectable=TRUE status-source-kept | Seat selectable row plus trim-equipment standard mirrors; keep until trim equipment copy is intentionally collapsed. |
| `CF7` | `opt_cf7_001` `sec_roof_001` selectable=TRUE status-source-kept; `opt_cf7_002` `sec_stan_002` selectable=FALSE status-source-kept | Mostly selectable/standard-equipment mirror. Do not deactivate blindly until standard-equipment summary can use the selectable standard row without losing customer included-equipment output. |
| `CM9` | `opt_cm9_001` `sec_roof_001` selectable=TRUE status-source-kept; `opt_cm9_002` `sec_stan_002` selectable=FALSE status-source-kept | Mostly selectable/standard-equipment mirror. Do not deactivate blindly until standard-equipment summary can use the selectable standard row without losing customer included-equipment output. |
| `EFR` | `opt_efr_001` `sec_exte_001` selectable=TRUE status-source-kept; `opt_efr_002` `sec_stan_002` selectable=FALSE status-source-kept | Mostly selectable/standard-equipment mirror. Do not deactivate blindly until standard-equipment summary can use the selectable standard row without losing customer included-equipment output. |
| `EYT` | `opt_eyt_001` `sec_badg_001` selectable=TRUE status-source-kept; `opt_eyt_002` `sec_stan_002` selectable=FALSE status-source-kept | Mostly selectable/standard-equipment mirror. Do not deactivate blindly until standard-equipment summary can use the selectable standard row without losing customer included-equipment output. |
| `J6A` | `opt_j6a_001` `sec_cali_001` selectable=TRUE status-source-kept; `opt_j6a_002` `sec_stan_002` selectable=FALSE status-source-kept | Mostly selectable/standard-equipment mirror. Do not deactivate blindly until standard-equipment summary can use the selectable standard row without losing customer included-equipment output. |
| `NGA` | `opt_nga_001` `sec_exha_001` selectable=TRUE status-source-kept; `opt_nga_002` `sec_stan_002` selectable=FALSE status-source-kept | Mostly selectable/standard-equipment mirror. Do not deactivate blindly until standard-equipment summary can use the selectable standard row without losing customer included-equipment output. |
| `SWM` | `opt_swm_002` `sec_stan_002` selectable=FALSE status-source-kept; `opt_swm_001` `sec_whee_002` selectable=TRUE status-source-kept | Mostly selectable/standard-equipment mirror. Do not deactivate blindly until standard-equipment summary can use the selectable standard row without losing customer included-equipment output. |
| `UQT` | `opt_uqt_002` `sec_2lte_001` selectable=FALSE status-source-kept; `opt_uqt_001` `sec_inte_001` selectable=TRUE status-source-kept | Selectable 1LT option plus 2LT equipment mirror; expected pending broader trim-equipment cleanup. |

## Active Non-Selectable Rows Without Display Behavior

| Option | RPO | Section | Status | Assessment |
| --- | --- | --- | --- | --- |
| `opt_aq9_004` | `AQ9` | `sec_1lte_001` | standard, unavailable | standard/included equipment source row; leave blank unless we decide these should render as display cards |
| `opt_uvb_001` | `UVB` | `sec_1lte_001` | standard, unavailable | standard/included equipment source row; leave blank unless we decide these should render as display cards |
| `opt_uqs_001` | `UQS` | `sec_1lte_001` | standard, unavailable | standard/included equipment source row; leave blank unless we decide these should render as display cards |
| `opt_k7a_001` | `K7A` | `sec_1lte_001` | standard, unavailable | standard/included equipment source row; leave blank unless we decide these should render as display cards |
| `opt_dwk_001` | `DWK` | `sec_1lte_001` | standard, unavailable | standard/included equipment source row; leave blank unless we decide these should render as display cards |
| `opt_uv6_001` | `UV6` | `sec_2lte_001` | standard, unavailable | standard/included equipment source row; leave blank unless we decide these should render as display cards |
| `opt_uqt_002` | `UQT` | `sec_2lte_001` | available, standard | standard/included equipment source row; leave blank unless we decide these should render as display cards |
| `opt_uqh_001` | `UQH` | `sec_2lte_001` | standard, unavailable | standard/included equipment source row; leave blank unless we decide these should render as display cards |
| `opt_uva_001` | `UVA` | `sec_2lte_001` | standard, unavailable | standard/included equipment source row; leave blank unless we decide these should render as display cards |
| `opt_ufg_001` | `UFG` | `sec_2lte_001` | standard, unavailable | standard/included equipment source row; leave blank unless we decide these should render as display cards |
| `opt_k7b_001` | `K7B` | `sec_2lte_001` | standard, unavailable | standard/included equipment source row; leave blank unless we decide these should render as display cards |
| `opt_ug1_001` | `UG1` | `sec_2lte_001` | standard, unavailable | standard/included equipment source row; leave blank unless we decide these should render as display cards |
| `opt_ki3_001` | `KI3` | `sec_2lte_001` | standard, unavailable | standard/included equipment source row; leave blank unless we decide these should render as display cards |
| `opt_aq9_003` | `AQ9` | `sec_2lte_001` | standard, unavailable | standard/included equipment source row; leave blank unless we decide these should render as display cards |
| `opt_kqv_001` | `KQV` | `sec_2lte_001` | standard, unavailable | standard/included equipment source row; leave blank unless we decide these should render as display cards |
| `opt_al9_001` | `AL9` | `sec_2lte_001` | standard, unavailable | standard/included equipment source row; leave blank unless we decide these should render as display cards |
| `opt_at9_001` | `AT9` | `sec_2lte_001` | standard, unavailable | standard/included equipment source row; leave blank unless we decide these should render as display cards |
| `opt_ahe_001` | `AHE` | `sec_2lte_001` | standard, unavailable | standard/included equipment source row; leave blank unless we decide these should render as display cards |
| `opt_ahh_001` | `AHH` | `sec_2lte_001` | standard, unavailable | standard/included equipment source row; leave blank unless we decide these should render as display cards |
| `opt_aqa_001` | `AQA` | `sec_2lte_001` | standard, unavailable | standard/included equipment source row; leave blank unless we decide these should render as display cards |
| `opt_ap9_001` | `AP9` | `sec_2lte_001` | standard, unavailable | standard/included equipment source row; leave blank unless we decide these should render as display cards |
| `opt_dyx_001` | `DYX` | `sec_2lte_001` | standard, unavailable | standard/included equipment source row; leave blank unless we decide these should render as display cards |
| `opt_uft_001` | `UFT` | `sec_2lte_001` | standard, unavailable | standard/included equipment source row; leave blank unless we decide these should render as display cards |
| `opt_utj_001` | `UTJ` | `sec_2lte_001` | standard, unavailable | standard/included equipment source row; leave blank unless we decide these should render as display cards |
| `opt_utv_001` | `UTV` | `sec_2lte_001` | standard, unavailable | standard/included equipment source row; leave blank unless we decide these should render as display cards |
| `opt_utu_001` | `UTU` | `sec_2lte_001` | standard, unavailable | standard/included equipment source row; leave blank unless we decide these should render as display cards |
| `opt_ah2_003` | `AH2` | `sec_3lte_001` | available, standard, unavailable | standard/included equipment source row; leave blank unless we decide these should render as display cards |
| `opt_iwe_001` | `IWE` | `sec_3lte_001` | standard, unavailable | standard/included equipment source row; leave blank unless we decide these should render as display cards |
| `opt_026` | `` | `sec_3lte_001` | standard, unavailable | standard/included equipment source row; leave blank unless we decide these should render as display cards |
| `opt_drg_001` | `DRG` | `sec_incl_001` | available | standard/included equipment source row; leave blank unless we decide these should render as display cards |
| `opt_tr7_001` | `TR7` | `sec_incl_001` | available, unavailable | standard/included equipment source row; leave blank unless we decide these should render as display cards |
| `opt_cfx_001` | `CFX` | `sec_incl_001` | available | standard/included equipment source row; leave blank unless we decide these should render as display cards |
| `opt_j56_001` | `J56` | `sec_incl_001` | available | standard/included equipment source row; leave blank unless we decide these should render as display cards |
| `opt_t0e_002` | `T0E` | `sec_incl_001` | standard | standard/included equipment source row; leave blank unless we decide these should render as display cards |
| `opt_xfr_001` | `XFR` | `sec_incl_001` | available | standard/included equipment source row; leave blank unless we decide these should render as display cards |
| `opt_xfs_001` | `XFS` | `sec_incl_001` | available | standard/included equipment source row; leave blank unless we decide these should render as display cards |
| `opt_aj7_001` | `AJ7` | `sec_safe_001` | standard | standard/included equipment source row; leave blank unless we decide these should render as display cards |
| `opt_uhy_001` | `UHY` | `sec_safe_001` | standard | standard/included equipment source row; leave blank unless we decide these should render as display cards |
| `opt_ueu_001` | `UEU` | `sec_safe_001` | standard | standard/included equipment source row; leave blank unless we decide these should render as display cards |
| `opt_ukt_001` | `UKT` | `sec_safe_001` | standard | standard/included equipment source row; leave blank unless we decide these should render as display cards |
| `opt_tq5_001` | `TQ5` | `sec_safe_001` | standard | standard/included equipment source row; leave blank unless we decide these should render as display cards |
| `opt_uhx_001` | `UHX` | `sec_safe_001` | standard | standard/included equipment source row; leave blank unless we decide these should render as display cards |
| `opt_drz_001` | `DRZ` | `sec_safe_001` | standard | standard/included equipment source row; leave blank unless we decide these should render as display cards |
| `opt_ud7_001` | `UD7` | `sec_safe_001` | standard | standard/included equipment source row; leave blank unless we decide these should render as display cards |
| `opt_tdm_001` | `TDM` | `sec_safe_001` | standard | standard/included equipment source row; leave blank unless we decide these should render as display cards |
| `opt_012` | `` | `sec_safe_001` | standard | standard/included equipment source row; leave blank unless we decide these should render as display cards |
| `opt_019` | `` | `sec_safe_001` | standard | standard/included equipment source row; leave blank unless we decide these should render as display cards |
| `opt_020` | `` | `sec_safe_001` | standard | standard/included equipment source row; leave blank unless we decide these should render as display cards |
| `opt_025` | `` | `sec_safe_001` | standard | standard/included equipment source row; leave blank unless we decide these should render as display cards |
| `opt_cj2_001` | `CJ2` | `sec_stan_001` | standard | standard/included equipment source row; leave blank unless we decide these should render as display cards |
| `opt_u80_001` | `U80` | `sec_stan_001` | standard | standard/included equipment source row; leave blank unless we decide these should render as display cards |
| `opt_npp_001` | `NPP` | `sec_stan_001` | standard | standard/included equipment source row; leave blank unless we decide these should render as display cards |
| `opt_t4l_001` | `T4L` | `sec_stan_001` | standard | standard/included equipment source row; leave blank unless we decide these should render as display cards |
| `opt_ls6_001` | `LS6` | `sec_stan_001` | standard | standard/included equipment source row; leave blank unless we decide these should render as display cards |
| `opt_a2x_001` | `A2X` | `sec_stan_001` | standard | standard/included equipment source row; leave blank unless we decide these should render as display cards |
| `opt_a7k_001` | `A7K` | `sec_stan_001` | standard | standard/included equipment source row; leave blank unless we decide these should render as display cards |
| `opt_n38_001` | `N38` | `sec_stan_001` | standard | standard/included equipment source row; leave blank unless we decide these should render as display cards |
| `opt_vhm_001` | `VHM` | `sec_stan_001` | standard | standard/included equipment source row; leave blank unless we decide these should render as display cards |
| `opt_v08_001` | `V08` | `sec_stan_001` | standard | standard/included equipment source row; leave blank unless we decide these should render as display cards |
| `opt_m1n_001` | `M1N` | `sec_stan_001` | standard | standard/included equipment source row; leave blank unless we decide these should render as display cards |
| `opt_g0k_001` | `G0K` | `sec_stan_001` | standard | standard/included equipment source row; leave blank unless we decide these should render as display cards |
| `opt_b4z_001` | `B4Z` | `sec_stan_001` | standard | standard/included equipment source row; leave blank unless we decide these should render as display cards |
| `opt_jx6_001` | `JX6` | `sec_stan_001` | standard | standard/included equipment source row; leave blank unless we decide these should render as display cards |
| `opt_xft_001` | `XFT` | `sec_stan_001` | standard | standard/included equipment source row; leave blank unless we decide these should render as display cards |
| `opt_001` | `` | `sec_stan_001` | standard | standard/included equipment source row; leave blank unless we decide these should render as display cards |
| `opt_002` | `` | `sec_stan_001` | standard | standard/included equipment source row; leave blank unless we decide these should render as display cards |
| `opt_003` | `` | `sec_stan_001` | standard | standard/included equipment source row; leave blank unless we decide these should render as display cards |
| `opt_004` | `` | `sec_stan_001` | standard | standard/included equipment source row; leave blank unless we decide these should render as display cards |
| `opt_005` | `` | `sec_stan_001` | standard | standard/included equipment source row; leave blank unless we decide these should render as display cards |
| `opt_006` | `` | `sec_stan_001` | standard, unavailable | standard/included equipment source row; leave blank unless we decide these should render as display cards |
| `opt_007` | `` | `sec_stan_001` | standard | standard/included equipment source row; leave blank unless we decide these should render as display cards |
| `opt_008` | `` | `sec_stan_001` | standard | standard/included equipment source row; leave blank unless we decide these should render as display cards |
| `opt_010` | `` | `sec_stan_001` | standard | standard/included equipment source row; leave blank unless we decide these should render as display cards |
| `opt_011` | `` | `sec_stan_001` | standard | standard/included equipment source row; leave blank unless we decide these should render as display cards |
| `opt_013` | `` | `sec_stan_001` | standard, unavailable | standard/included equipment source row; leave blank unless we decide these should render as display cards |
| `opt_014` | `` | `sec_stan_001` | standard | standard/included equipment source row; leave blank unless we decide these should render as display cards |
| `opt_016` | `` | `sec_stan_001` | standard | standard/included equipment source row; leave blank unless we decide these should render as display cards |
| `opt_017` | `` | `sec_stan_001` | standard | standard/included equipment source row; leave blank unless we decide these should render as display cards |
| `opt_018` | `` | `sec_stan_001` | standard | standard/included equipment source row; leave blank unless we decide these should render as display cards |
| `opt_021` | `` | `sec_stan_001` | standard | standard/included equipment source row; leave blank unless we decide these should render as display cards |
| `opt_022` | `` | `sec_stan_001` | standard | standard/included equipment source row; leave blank unless we decide these should render as display cards |
| `opt_023` | `` | `sec_stan_001` | standard | standard/included equipment source row; leave blank unless we decide these should render as display cards |
| `opt_024` | `` | `sec_stan_001` | standard | standard/included equipment source row; leave blank unless we decide these should render as display cards |
| `opt_j6a_002` | `J6A` | `sec_stan_002` | standard | standard/included equipment source row; leave blank unless we decide these should render as display cards |
| `opt_eyt_002` | `EYT` | `sec_stan_002` | standard | standard/included equipment source row; leave blank unless we decide these should render as display cards |
| `opt_cm9_002` | `CM9` | `sec_stan_002` | standard, unavailable | standard/included equipment source row; leave blank unless we decide these should render as display cards |
| `opt_nga_002` | `NGA` | `sec_stan_002` | standard | standard/included equipment source row; leave blank unless we decide these should render as display cards |
| `opt_efr_002` | `EFR` | `sec_stan_002` | standard | standard/included equipment source row; leave blank unless we decide these should render as display cards |
| `opt_cf7_002` | `CF7` | `sec_stan_002` | standard, unavailable | standard/included equipment source row; leave blank unless we decide these should render as display cards |
| `opt_719_002` | `719` | `sec_stan_002` | standard | standard/included equipment source row; leave blank unless we decide these should render as display cards |
| `opt_nk4_001` | `NK4` | `sec_stan_002` | standard | standard/included equipment source row; leave blank unless we decide these should render as display cards |
| `opt_fea_001` | `FEA` | `sec_stan_002` | standard | standard/included equipment source row; leave blank unless we decide these should render as display cards |
| `opt_swm_002` | `SWM` | `sec_stan_002` | standard | standard/included equipment source row; leave blank unless we decide these should render as display cards |
| `opt_ive_001` | `IVE` | `sec_tech_001` | standard | standard/included equipment source row; leave blank unless we decide these should render as display cards |
| `opt_ppw_001` | `PPW` | `sec_tech_001` | standard | standard/included equipment source row; leave blank unless we decide these should render as display cards |
| `opt_015` | `` | `sec_tech_001` | standard | standard/included equipment source row; leave blank unless we decide these should render as display cards |

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
| `AUP` | `opt_aup_001` | `False` | `TRUE` | `` | `sec_seat_002` | 80 | interior-only/component-only suppressed from normal options |
| `B6P` | `opt_b6p_001` | `True` | `TRUE` | `` | `sec_engi_001` | 1 |  |
| `BC4` | `opt_bc4_001` | `False` | `TRUE` | `` | `sec_engi_001` | 45 |  |
| `BC4` | `opt_bc4_002` | `True` | `TRUE` | `` | `sec_engi_001` | 27 |  |
| `BC7` | `opt_bc7_001` | `True` | `TRUE` | `` | `sec_engi_001` | 20 |  |
| `BCP` | `opt_bcp_001` | `False` | `TRUE` | `` | `sec_engi_001` | 35 |  |
| `BCP` | `opt_bcp_002` | `True` | `TRUE` | `` | `sec_engi_001` | 25 |  |
| `BCS` | `opt_bcs_001` | `False` | `TRUE` | `` | `sec_engi_001` | 40 |  |
| `BCS` | `opt_bcs_002` | `True` | `TRUE` | `` | `sec_engi_001` | 26 |  |
| `CFL` | `opt_cfl_001` | `True` | `TRUE` | `` | `sec_perf_001` | 30 |  |
| `CFV` | `opt_cfv_001` | `False` | `TRUE` | `` | `sec_perf_001` | 40 | inactive/deferred ground effects row |
| `CFZ` | `opt_cfz_001` | `True` | `TRUE` | `` | `sec_perf_001` | 50 |  |
| `D3V` | `opt_d3v_001` | `True` | `TRUE` | `` | `sec_engi_001` | 10 |  |
| `FEB` | `opt_feb_001` | `True` | `TRUE` | `` | `sec_perf_001` | 60 |  |
| `FEY` | `opt_fey_001` | `True` | `TRUE` | `` | `sec_perf_001` | 70 |  |
| `J57` | `opt_j57_001` | `True` | `TRUE` | `` | `sec_perf_001` | 80 |  |
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
| `T0E` | `opt_t0e_001` | `False` | `FALSE` | `` | `sec_stan_002` | 110 |  |
| `T0E` | `opt_t0e_002` | `True` | `FALSE` | `` | `sec_incl_001` | 50 |  |
| `T0F` | `opt_t0f_001` | `True` | `TRUE` | `` | `sec_perf_001` | 90 |  |
| `U2K` | `opt_u2k_001` | `False` | `FALSE` | `` | `sec_onst_001` | 90 | OnStar/deferred inactive |
| `Z15` | `opt_z15_001` | `True` | `False` | `display_only` | `sec_stri_001` | 190 |  |
| `Z25` | `opt_z25_001` | `True` | `TRUE` | `` | `sec_spec_001` | 10 |  |
| `ZZ3` | `opt_zz3_001` | `True` | `TRUE` | `` | `sec_engi_001` | 5 |  |

## Active Sections And Step Placement

| Section | Name | Step | Section order | Active rows | Option order range | Duplicate option orders |
| --- | --- | --- | ---: | ---: | --- | --- |
| `sec_1lte_001` | 1LT Equipment | `standard_equipment` | 10 | 5 | 10-50 | none |
| `sec_incl_001` | Included | `standard_equipment` | 10 | 7 | 10-70 | none |
| `sec_pain_001` | Paint | `paint` | 10 | 10 | 10-100 | none |
| `sec_perf_001` | Performance | `packages_performance` | 10 | 8 | 10-90 | none |
| `sec_roof_001` | Roof | `exterior_appearance` | 10 | 7 | 10-70 | none |
| `sec_seat_002` | Seats | `seat` | 10 | 3 | 10-40 | none |
| `sec_stan_002` | Standard Options | `standard_equipment` | 10 | 10 | 10-100 | none |
| `sec_whee_002` | Wheels | `wheels` | 10 | 7 | 10-70 | none |
| `sec_2lte_001` | 2LT Equipment | `standard_equipment` | 20 | 21 | 10-210 | none |
| `sec_cali_001` | Caliper Color | `wheels` | 20 | 7 | 10-70 | none |
| `sec_exte_001` | Exterior Accents | `exterior_appearance` | 20 | 3 | 10-30 | none |
| `sec_seat_001` | Seat Belt | `seat_belt` | 20 | 6 | 10-60 | none |
| `sec_stan_001` | Standard Equipment | `standard_equipment` | 20 | 34 | 10-340 | none |
| `sec_3lte_001` | 3LT Equipment | `standard_equipment` | 30 | 3 | 10-30 | none |
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

## Section-To-Step Overrides Still Required

Because `category` was removed and `section_master` does not yet have `step_key`, these overrides are still code-owned runtime structure. The clean workbook-owned alternative is a future `section_master.step_key` column, but that was not added in this pass.

| Section | Name | Step override | Name-only fallback | Active GS rows | Classification |
| --- | --- | --- | --- | ---: | --- |
| `sec_pain_001` | Paint | `paint` | `standard_equipment` | 10 | required until workbook owns step_key |
| `sec_whee_002` | Wheels | `wheels` | `standard_equipment` | 7 | required until workbook owns step_key |
| `sec_cali_001` | Caliper Color | `wheels` | `standard_equipment` | 7 | required until workbook owns step_key |
| `sec_roof_001` | Roof | `exterior_appearance` | `standard_equipment` | 7 | required until workbook owns step_key |
| `sec_exte_001` | Exterior Accents | `exterior_appearance` | `standard_equipment` | 3 | required until workbook owns step_key |
| `sec_badg_001` | Badges | `exterior_appearance` | `standard_equipment` | 2 | required until workbook owns step_key |
| `sec_engi_001` | Engine Appearance | `exterior_appearance` | `standard_equipment` | 11 | required until workbook owns step_key |
| `sec_perf_001` | Performance | `packages_performance` | `standard_equipment` | 8 | required until workbook owns step_key |
| `sec_susp_001` | Suspension | `packages_performance` | `standard_equipment` | 0 | required until workbook owns step_key |
| `sec_seat_002` | Seats | `seat` | `standard_equipment` | 3 | required until workbook owns step_key |
| `sec_intc_001` | 1LT Interior | `base_interior` | `standard_equipment` | 0 | required until workbook owns step_key |
| `sec_intc_002` | 2LT Interior | `base_interior` | `standard_equipment` | 0 | required until workbook owns step_key |
| `sec_intc_003` | 3LT Interior | `base_interior` | `standard_equipment` | 0 | required until workbook owns step_key |
| `sec_seat_001` | Seat Belt | `seat_belt` | `standard_equipment` | 6 | required until workbook owns step_key |
| `sec_inte_001` | Interior Trim | `interior_trim` | `standard_equipment` | 3 | required until workbook owns step_key |
| `sec_lpoi_001` | LPO Interior | `interior_trim` | `aero_exhaust_stripes_accessories` | 13 | required until workbook owns step_key |
| `sec_whee_001` | Wheel Accessory | `wheels` | `aero_exhaust_stripes_accessories` | 7 | required until workbook owns step_key |
| `sec_gsce_001` | GS Center Stripes | `exterior_appearance` | `aero_exhaust_stripes_accessories` | 5 | required until workbook owns step_key |
| `sec_gsha_001` | GS Hash Marks | `exterior_appearance` | `standard_equipment` | 6 | required until workbook owns step_key |
| `sec_colo_001` | Color Override | `interior_trim` | `standard_equipment` | 2 | required until workbook owns step_key |
| `sec_onst_001` | OnStar | `interior_trim` | `standard_equipment` | 0 | required until workbook owns step_key |
| `sec_cust_002` | Custom Stitch | `interior_trim` | `standard_equipment` | 0 | required until workbook owns step_key |
| `sec_spec_001` | Special Edition | `packages_performance` | `standard_equipment` | 1 | required until workbook owns step_key |
| `sec_cust_001` | Custom Delivery | `delivery` | `standard_equipment` | 3 | required until workbook owns step_key |

## Display Order Anomalies

- No duplicate active option display_order values found within active Grand Sport sections.

Known subjective order review still needed: standard/default rows first inside some sections, and whether GS hash marks/center stripes should remain in exterior appearance or move to the stripes step after final Z15 UX review.

## Remaining Decisions / Non-Goals For This Pass

- Do not deactivate the remaining standard-equipment mirror duplicates until the generator standard-equipment summary can be proven not to lose included-equipment rows.
- Do not add `section_master.step_key` in this pass; current placement remains explicit code-owned runtime structure.
- Do not activate Grand Sport variants in `variant_master`.
- Do not delete inactive option rows; inactive rows preserve source evidence and OVS coverage.
