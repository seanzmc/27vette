# Z Option/OVS Closure Phase 2A Report

Source command: `.venv/bin/python scripts/apply_future_model_option_review.py --dry-run --model-key all`
Status: `dry_run`; error_count: `0`

## Summary

| model | current options | approved-active emit | option delta | current OVS | approved-active OVS | OVS delta | would remove | would add | blocked counts |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| z06 | 239 | 164 | -75 | 1434 | 984 | -450 | 75 | 0 | deferred=57, inactive=170, needs_section_review=113 |
| zr1 | 201 | 141 | -60 | 804 | 564 | -240 | 60 | 0 | deferred=60, inactive=164, needs_section_review=104 |
| zr1x | 202 | 141 | -61 | 808 | 564 | -244 | 61 | 0 | deferred=60, inactive=164, needs_section_review=104 |

## Decision blockers by model

### z06

Status/active buckets:
- `deferred` / active=`False`: 57
- `needs_section_review` / active=`False`: 113
- unresolved rows with no source/orderable/ref RPO: 51
Top candidate sections among unresolved rows:
- `NO_SECTION`: 95
- `sec_stan_001`: 24
- `sec_whee_002`: 9
- `sec_inte_001`: 6
- `sec_tech_001`: 5
- `sec_lpoe_001`: 4
- `sec_perf_z52_001`: 4
- `sec_cust_002`: 3
- `sec_stri_001`: 3
- `sec_safe_001`: 2
- `sec_lpow_001`: 2
- `sec_perf_aero_001`: 2

Exact option IDs currently in `z06_options` but not eligible under approved-active contract (75):
`opt_085`, `opt_095`, `opt_096`, `opt_098`, `opt_099`, `opt_101`, `opt_103`, `opt_105`, `opt_129`, `opt_137`, `opt_162`, `opt_167`, `opt_172`, `opt_176`, `opt_179`, `opt_180`, `opt_187`, `opt_197`, `opt_203`, `opt_288`, `opt_289`, `opt_295`, `opt_319`, `opt_326`, `opt_329`, `opt_332`, `opt_36s_001`, `opt_37s_001`, `opt_38s_001`, `opt_5dh_001`, `opt_5dk_001`, `opt_5v5_001`, `opt_bcw_001`, `opt_cfv_002`, `opt_dy0_002`, `opt_efy_001`, `opt_fa6_001`, `opt_fe6_002`, `opt_fe7_001`, `opt_lt6_002`, `opt_m1m_002`, `opt_n26_001`, `opt_n2z_001`, `opt_n3w_002`, `opt_pbc_001`, `opt_pcz_001`, `opt_pda_001`, `opt_pdb_001`, `opt_pdd_001`, `opt_pdf_001`, `opt_r8e_002`, `opt_rou_001`, `opt_rox_001`, `opt_rxi_001`, `opt_ryq_001`, `opt_sg1_001`, `opt_sne_001`, `opt_soa_001`, `opt_soe_002`, `opt_som_001`, `opt_son_001`, `opt_srk_001`, `opt_srn_001`, `opt_stx_001`, `opt_t0g_001`, `opt_tu7_001`, `opt_u2k_002`, `opt_u5g_002`, `opt_ue1_002`, `opt_v8x_001`, `opt_vk3_001`, `opt_vpw_001`, `opt_vv4_002`, `opt_wks_001`, `opt_z07_001`

### zr1

Status/active buckets:
- `deferred` / active=`False`: 60
- `needs_section_review` / active=`False`: 104
- unresolved rows with no source/orderable/ref RPO: 51
Top candidate sections among unresolved rows:
- `NO_SECTION`: 102
- `sec_stan_001`: 29
- `sec_inte_001`: 5
- `sec_whee_002`: 5
- `sec_susp_001`: 4
- `sec_tech_001`: 4
- `sec_cust_002`: 3
- `sec_perf_brake_001`: 2
- `sec_cust_001`: 2
- `sec_3lte_001`: 1
- `sec_engi_001`: 1
- `sec_cali_001`: 1

Exact option IDs currently in `zr1_options` but not eligible under approved-active contract (60):
`opt_36s_001`, `opt_37s_001`, `opt_38s_001`, `opt_509`, `opt_529`, `opt_531`, `opt_535`, `opt_537`, `opt_541`, `opt_545`, `opt_549`, `opt_613`, `opt_663`, `opt_673`, `opt_683`, `opt_691`, `opt_697`, `opt_699`, `opt_707`, `opt_723`, `opt_731`, `opt_849`, `opt_851`, `opt_863`, `opt_911`, `opt_921`, `opt_927`, `opt_937`, `opt_cfc_002`, `opt_cfv_002`, `opt_dy0_002`, `opt_etv_001`, `opt_fa6_001`, `opt_fe8_002`, `opt_fej_001`, `opt_j58_002`, `opt_j59_002`, `opt_j6o_001`, `opt_lt7_002`, `opt_m1k_002`, `opt_n26_001`, `opt_n2z_001`, `opt_n3w_002`, `opt_pbc_001`, `opt_r8e_002`, `opt_sb9_001`, `opt_sof_001`, `opt_sog_001`, `opt_soh_001`, `opt_soj_002`, `opt_su1_001`, `opt_tom_001`, `opt_tu7_001`, `opt_u2k_002`, `opt_u5g_002`, `opt_ue1_002`, `opt_v8x_001`, `opt_vk3_001`, `opt_vv4_002`, `opt_ztk_001`

### zr1x

Status/active buckets:
- `deferred` / active=`False`: 60
- `needs_section_review` / active=`False`: 104
- unresolved rows with no source/orderable/ref RPO: 51
Top candidate sections among unresolved rows:
- `NO_SECTION`: 101
- `sec_stan_001`: 31
- `sec_inte_001`: 5
- `sec_whee_002`: 5
- `sec_susp_001`: 4
- `sec_tech_001`: 4
- `sec_cust_002`: 3
- `sec_stri_001`: 2
- `sec_cust_001`: 2
- `sec_3lte_001`: 1
- `sec_engi_001`: 1
- `sec_cali_001`: 1

Exact option IDs currently in `zr1x_options` but not eligible under approved-active contract (61):
`opt_36s_001`, `opt_37s_001`, `opt_38s_001`, `opt_510`, `opt_530`, `opt_532`, `opt_536`, `opt_538`, `opt_542`, `opt_546`, `opt_550`, `opt_614`, `opt_664`, `opt_674`, `opt_684`, `opt_692`, `opt_698`, `opt_700`, `opt_708`, `opt_724`, `opt_732`, `opt_850`, `opt_852`, `opt_864`, `opt_912`, `opt_922`, `opt_928`, `opt_938`, `opt_cfc_002`, `opt_cfv_002`, `opt_dtb_001`, `opt_dy0_002`, `opt_etv_001`, `opt_fa6_001`, `opt_feh_002`, `opt_fez_001`, `opt_hp1_002`, `opt_j59_002`, `opt_j6o_001`, `opt_lt7_002`, `opt_mlp_002`, `opt_n26_001`, `opt_n2z_001`, `opt_n3w_002`, `opt_pbc_001`, `opt_r8e_002`, `opt_sb9_001`, `opt_sof_001`, `opt_sog_001`, `opt_soh_001`, `opt_soj_002`, `opt_su1_001`, `opt_tom_002`, `opt_tu7_001`, `opt_u2k_002`, `opt_u5g_002`, `opt_ue1_002`, `opt_v8x_001`, `opt_vk3_001`, `opt_vv4_002`, `opt_ztk_001`

## Interpretation

- Phase 2A changed dry-run planning only; it did not write `stingray_master.xlsx`.
- The corrected predicate emits only `review_status=approved` and `active=True` rows with a resolved section.
- The current normalized option/OVS sheets still contain unresolved inactive review rows. Phase 2B should classify/approve/defer those rows before any write-mode regeneration.
- Under the current approved-active contract, no new option IDs would be added; the prior four ZR1/ZR1X suspension additions are now blocked as inactive `needs_section_review`.
