# Z Rule / Exclusive / Default Audit

Status: `rule_audit_generated`
Generated: `2026-05-31T19:38:52+00:00`

- Read-only audit: workbook was inspected but not saved.
- Audit uses the same rule/exclusive/default source-sheet concepts as Stingray and Grand Sport.
- Pricing, interiors, and runtime promotion are intentionally out of scope.

## Z06

### Summary
- activeOptions: 239
- optionRows: 239
- ovsRows: 1434
- ruleMappingRows: 94
- exclusiveGroups: 7
- exclusiveMembers: 16
- ruleGroups: 0
- ruleGroupMembers: 0
- defaultSelectionRules: 3

### Rule types
- excludes: 70
- includes: 15
- requires: 9

### Focused review counts
- duplicateSemanticRules: 0
- directExcludesCoveredByExclusiveGroups: 0
- missingOptionReferences: 0
- inactiveOptionReferences: 0
- missingRuleGroupMemberReferences: 0
- missingExclusiveMemberReferences: 0
- missingDefaultRuleTargets: 0
- optionsMissingVariantStatuses: 0
- danglingOvsRows: 0
- invalidOvsStatuses: 0
- grandSportTextHits: 0

### Hot spots
- engineAppearance: optionCount=4, ruleCount=3 (options: opt_b6p_001 | opt_d3v_001 | opt_sl9_001 | opt_zz3_001; rules: z06_rule_opt_b6p_001_includes_opt_d3v_001 | z06_copy_rule_opt_b6p_001_includes_opt_sl9_001_opt_b6p_001_includes_opt_sl9_001 | z06_copy_rule_opt_zz3_001_includes_opt_sl9_001_opt_zz3_001_includes_opt_sl9_001)
- exhaust: optionCount=3, ruleCount=1 (options: opt_nga_001 | opt_nwi_001 | opt_wub_001; rules: z06_copy_rule_opt_nwi_001_requires_opt_wub_001_opt_nwi_001_requires_opt_wub_001)
- suspension: optionCount=2, ruleCount=0 (options: opt_fe6_002 | opt_fe7_001)
- brakes: optionCount=2, ruleCount=6 (options: opt_j57_001 | opt_j6d_001; rules: z06_rule_opt_j6l_001_requires_opt_j57_001 | z06_rule_opt_t0f_001_requires_opt_j57_001 | z06_rule_opt_roy_001_requires_opt_j57_001 | z06_rule_opt_roz_001_requires_opt_j57_001 | z06_rule_opt_stz_001_requires_opt_j57_001 | z06_rule_opt_j6d_001_requires_opt_j57_001)
- performancePackages: optionCount=3, ruleCount=2 (options: opt_pcq_001 | opt_pdb_001 | opt_z07_001; rules: z06_rule_opt_pcq_001_includes_opt_vwe_001 | z06_rule_opt_pcq_001_includes_opt_vwt_001)
- wheels: optionCount=4, ruleCount=21 (options: opt_5dh_001 | opt_r88_001 | opt_roy_001 | opt_roz_001; rules: z06_copy_rule_opt_r88_001_excludes_opt_eyk_001_opt_r88_001_excludes_opt_eyk_001 | z06_copy_rule_opt_r88_001_excludes_opt_sfz_001_opt_r88_001_excludes_opt_sfz_001 | z06_rule_opt_roy_001_requires_opt_j57_001 | z06_rule_opt_roz_001_requires_opt_j57_001 | z06_copy_rule_opt_r88_001_excludes_opt_dpb_001_opt_r88_001_excludes_opt_dpb_001 | z06_copy_rule_opt_r88_001_excludes_opt_dpc_001_opt_r88_001_excludes_opt_dpc_001 | z06_copy_rule_opt_r88_001_excludes_opt_dpg_001_opt_r88_001_excludes_opt_dpg_001 | z06_copy_rule_opt_r88_001_excludes_opt_dpl_001_opt_r88_001_excludes_opt_dpl_001 | z06_copy_rule_opt_r88_001_excludes_opt_dpt_001_opt_r88_001_excludes_opt_dpt_001 | z06_copy_rule_opt_r88_001_excludes_opt_dsy_001_opt_r88_001_excludes_opt_dsy_001 | z06_copy_rule_opt_r88_001_excludes_opt_dsz_001_opt_r88_001_excludes_opt_dsz_001 | z06_copy_rule_opt_r88_001_excludes_opt_dt0_001_opt_r88_001_excludes_opt_dt0_001)
- groundEffectsAero: optionCount=6, ruleCount=4 (options: opt_5v5_001 | opt_cfv_002 | opt_cfz_001 | opt_t0f_001 | opt_t0g_001 | opt_vwe_001; rules: z06_rule_opt_pcq_001_includes_opt_vwe_001 | z06_rule_opt_t0f_001_includes_opt_cfz_001 | z06_rule_opt_t0f_001_requires_opt_j57_001 | z06_rule_opt_5zv_001_excludes_opt_t0f_001)
- stripesExteriorAccents: optionCount=17, ruleCount=55 (options: opt_dpb_001 | opt_dpc_001 | opt_dpg_001 | opt_dpl_001 | opt_dpt_001 | opt_dsy_001 | opt_dsz_001 | opt_dt0_001 | opt_dth_001 | opt_dub_001 | opt_due_001 | opt_duk_001; rules: z06_copy_rule_opt_r88_001_excludes_opt_eyk_001_opt_r88_001_excludes_opt_eyk_001 | z06_copy_rule_opt_sfz_001_excludes_opt_eyk_001_opt_sfz_001_excludes_opt_eyk_001 | z06_copy_rule_opt_r88_001_excludes_opt_sfz_001_opt_r88_001_excludes_opt_sfz_001 | z06_copy_rule_opt_r88_001_excludes_opt_dpb_001_opt_r88_001_excludes_opt_dpb_001 | z06_copy_rule_opt_r88_001_excludes_opt_dpc_001_opt_r88_001_excludes_opt_dpc_001 | z06_copy_rule_opt_r88_001_excludes_opt_dpg_001_opt_r88_001_excludes_opt_dpg_001 | z06_copy_rule_opt_r88_001_excludes_opt_dpl_001_opt_r88_001_excludes_opt_dpl_001 | z06_copy_rule_opt_r88_001_excludes_opt_dpt_001_opt_r88_001_excludes_opt_dpt_001 | z06_copy_rule_opt_r88_001_excludes_opt_dsy_001_opt_r88_001_excludes_opt_dsy_001 | z06_copy_rule_opt_r88_001_excludes_opt_dsz_001_opt_r88_001_excludes_opt_dsz_001 | z06_copy_rule_opt_r88_001_excludes_opt_dt0_001_opt_r88_001_excludes_opt_dt0_001 | z06_copy_rule_opt_r88_001_excludes_opt_dth_001_opt_r88_001_excludes_opt_dth_001)
- defaults: defaultSelectionRules=3 (defaultSelected: opt_719_001 | opt_efr_001 | opt_t0e_001)
- requiredExclusiveGroups: ['z06_excl_exterior_accents', 'z06_excl_performance_brakes']

## ZR1

### Summary
- activeOptions: 203
- optionRows: 203
- ovsRows: 812
- ruleMappingRows: 50
- exclusiveGroups: 4
- exclusiveMembers: 10
- ruleGroups: 0
- ruleGroupMembers: 0
- defaultSelectionRules: 4

### Rule types
- excludes: 33
- includes: 14
- requires: 3

### Focused review counts
- duplicateSemanticRules: 0
- directExcludesCoveredByExclusiveGroups: 0
- missingOptionReferences: 0
- inactiveOptionReferences: 0
- missingRuleGroupMemberReferences: 0
- missingExclusiveMemberReferences: 0
- missingDefaultRuleTargets: 0
- optionsMissingVariantStatuses: 0
- danglingOvsRows: 0
- invalidOvsStatuses: 0
- grandSportTextHits: 0

### Hot spots
- engineAppearance: optionCount=4, ruleCount=3 (options: opt_b6p_001 | opt_d3v_001 | opt_sl9_001 | opt_zz3_001; rules: zr1_rule_opt_b6p_001_includes_opt_d3v_001 | zr1_copy_rule_opt_b6p_001_includes_opt_sl9_001_opt_b6p_001_includes_opt_sl9_001 | zr1_copy_rule_opt_zz3_001_includes_opt_sl9_001_opt_zz3_001_includes_opt_sl9_001)
- exhaust: optionCount=3, ruleCount=1 (options: opt_nga_001 | opt_nwi_001 | opt_wub_001; rules: zr1_copy_rule_opt_nwi_001_requires_opt_wub_001_opt_nwi_001_requires_opt_wub_001)
- suspension: optionCount=1, ruleCount=0 (options: opt_fe8_002)
- brakes: optionCount=3, ruleCount=0 (options: opt_j58_002 | opt_j59_002 | opt_j6d_001)
- performancePackages: optionCount=2, ruleCount=2 (options: opt_pcq_001 | opt_ztk_001; rules: zr1_rule_opt_pcq_001_includes_opt_vwe_001 | zr1_rule_opt_pcq_001_includes_opt_vwt_001)
- wheels: optionCount=1, ruleCount=15 (options: opt_r88_001; rules: zr1_copy_rule_opt_r88_001_excludes_opt_eyk_001_opt_r88_001_excludes_opt_eyk_001 | zr1_copy_rule_opt_r88_001_excludes_opt_sfz_001_opt_r88_001_excludes_opt_sfz_001 | zr1_copy_rule_opt_r88_001_excludes_opt_dpb_001_opt_r88_001_excludes_opt_dpb_001 | zr1_copy_rule_opt_r88_001_excludes_opt_dpc_001_opt_r88_001_excludes_opt_dpc_001 | zr1_copy_rule_opt_r88_001_excludes_opt_dpg_001_opt_r88_001_excludes_opt_dpg_001 | zr1_copy_rule_opt_r88_001_excludes_opt_dpl_001_opt_r88_001_excludes_opt_dpl_001 | zr1_copy_rule_opt_r88_001_excludes_opt_dpt_001_opt_r88_001_excludes_opt_dpt_001 | zr1_copy_rule_opt_r88_001_excludes_opt_dsy_001_opt_r88_001_excludes_opt_dsy_001 | zr1_copy_rule_opt_r88_001_excludes_opt_dsz_001_opt_r88_001_excludes_opt_dsz_001 | zr1_copy_rule_opt_r88_001_excludes_opt_dt0_001_opt_r88_001_excludes_opt_dt0_001 | zr1_copy_rule_opt_r88_001_excludes_opt_dth_001_opt_r88_001_excludes_opt_dth_001 | zr1_copy_rule_opt_r88_001_excludes_opt_dub_001_opt_r88_001_excludes_opt_dub_001)
- groundEffectsAero: optionCount=2, ruleCount=1 (options: opt_cfv_002 | opt_vwe_001; rules: zr1_rule_opt_pcq_001_includes_opt_vwe_001)
- stripesExteriorAccents: optionCount=16, ruleCount=29 (options: opt_dpb_001 | opt_dpc_001 | opt_dpg_001 | opt_dpl_001 | opt_dpt_001 | opt_dsy_001 | opt_dsz_001 | opt_dt0_001 | opt_dth_001 | opt_dub_001 | opt_due_001 | opt_duk_001; rules: zr1_copy_rule_opt_r88_001_excludes_opt_eyk_001_opt_r88_001_excludes_opt_eyk_001 | zr1_copy_rule_opt_sfz_001_excludes_opt_eyk_001_opt_sfz_001_excludes_opt_eyk_001 | zr1_copy_rule_opt_r88_001_excludes_opt_sfz_001_opt_r88_001_excludes_opt_sfz_001 | zr1_copy_rule_opt_r88_001_excludes_opt_dpb_001_opt_r88_001_excludes_opt_dpb_001 | zr1_copy_rule_opt_r88_001_excludes_opt_dpc_001_opt_r88_001_excludes_opt_dpc_001 | zr1_copy_rule_opt_r88_001_excludes_opt_dpg_001_opt_r88_001_excludes_opt_dpg_001 | zr1_copy_rule_opt_r88_001_excludes_opt_dpl_001_opt_r88_001_excludes_opt_dpl_001 | zr1_copy_rule_opt_r88_001_excludes_opt_dpt_001_opt_r88_001_excludes_opt_dpt_001 | zr1_copy_rule_opt_r88_001_excludes_opt_dsy_001_opt_r88_001_excludes_opt_dsy_001 | zr1_copy_rule_opt_r88_001_excludes_opt_dsz_001_opt_r88_001_excludes_opt_dsz_001 | zr1_copy_rule_opt_r88_001_excludes_opt_dt0_001_opt_r88_001_excludes_opt_dt0_001 | zr1_copy_rule_opt_r88_001_excludes_opt_dth_001_opt_r88_001_excludes_opt_dth_001)
- defaults: defaultSelectionRules=4 (defaultSelected: opt_719_001 | opt_efr_001 | opt_j6d_001 | opt_t0e_001)
- requiredExclusiveGroups: []

## ZR1X

### Summary
- activeOptions: 204
- optionRows: 204
- ovsRows: 816
- ruleMappingRows: 50
- exclusiveGroups: 4
- exclusiveMembers: 10
- ruleGroups: 0
- ruleGroupMembers: 0
- defaultSelectionRules: 4

### Rule types
- excludes: 33
- includes: 14
- requires: 3

### Focused review counts
- duplicateSemanticRules: 0
- directExcludesCoveredByExclusiveGroups: 0
- missingOptionReferences: 0
- inactiveOptionReferences: 0
- missingRuleGroupMemberReferences: 0
- missingExclusiveMemberReferences: 0
- missingDefaultRuleTargets: 0
- optionsMissingVariantStatuses: 0
- danglingOvsRows: 0
- invalidOvsStatuses: 0
- grandSportTextHits: 0

### Hot spots
- engineAppearance: optionCount=4, ruleCount=3 (options: opt_b6p_001 | opt_d3v_001 | opt_sl9_001 | opt_zz3_001; rules: zr1x_rule_opt_b6p_001_includes_opt_d3v_001 | zr1x_copy_rule_opt_b6p_001_includes_opt_sl9_001_opt_b6p_001_includes_opt_sl9_001 | zr1x_copy_rule_opt_zz3_001_includes_opt_sl9_001_opt_zz3_001_includes_opt_sl9_001)
- exhaust: optionCount=3, ruleCount=1 (options: opt_nga_001 | opt_nwi_001 | opt_wub_001; rules: zr1x_copy_rule_opt_nwi_001_requires_opt_wub_001_opt_nwi_001_requires_opt_wub_001)
- suspension: optionCount=1, ruleCount=0 (options: opt_fe8_002)
- brakes: optionCount=2, ruleCount=0 (options: opt_j59_002 | opt_j6d_001)
- performancePackages: optionCount=2, ruleCount=2 (options: opt_pcq_001 | opt_ztk_001; rules: zr1x_rule_opt_pcq_001_includes_opt_vwe_001 | zr1x_rule_opt_pcq_001_includes_opt_vwt_001)
- wheels: optionCount=1, ruleCount=15 (options: opt_r88_001; rules: zr1x_copy_rule_opt_r88_001_excludes_opt_eyk_001_opt_r88_001_excludes_opt_eyk_001 | zr1x_copy_rule_opt_r88_001_excludes_opt_sfz_001_opt_r88_001_excludes_opt_sfz_001 | zr1x_copy_rule_opt_r88_001_excludes_opt_dpb_001_opt_r88_001_excludes_opt_dpb_001 | zr1x_copy_rule_opt_r88_001_excludes_opt_dpc_001_opt_r88_001_excludes_opt_dpc_001 | zr1x_copy_rule_opt_r88_001_excludes_opt_dpg_001_opt_r88_001_excludes_opt_dpg_001 | zr1x_copy_rule_opt_r88_001_excludes_opt_dpl_001_opt_r88_001_excludes_opt_dpl_001 | zr1x_copy_rule_opt_r88_001_excludes_opt_dpt_001_opt_r88_001_excludes_opt_dpt_001 | zr1x_copy_rule_opt_r88_001_excludes_opt_dsy_001_opt_r88_001_excludes_opt_dsy_001 | zr1x_copy_rule_opt_r88_001_excludes_opt_dsz_001_opt_r88_001_excludes_opt_dsz_001 | zr1x_copy_rule_opt_r88_001_excludes_opt_dt0_001_opt_r88_001_excludes_opt_dt0_001 | zr1x_copy_rule_opt_r88_001_excludes_opt_dth_001_opt_r88_001_excludes_opt_dth_001 | zr1x_copy_rule_opt_r88_001_excludes_opt_dub_001_opt_r88_001_excludes_opt_dub_001)
- groundEffectsAero: optionCount=2, ruleCount=1 (options: opt_cfv_002 | opt_vwe_001; rules: zr1x_rule_opt_pcq_001_includes_opt_vwe_001)
- stripesExteriorAccents: optionCount=17, ruleCount=29 (options: opt_dpb_001 | opt_dpc_001 | opt_dpg_001 | opt_dpl_001 | opt_dpt_001 | opt_dsy_001 | opt_dsz_001 | opt_dt0_001 | opt_dtb_001 | opt_dth_001 | opt_dub_001 | opt_due_001; rules: zr1x_copy_rule_opt_r88_001_excludes_opt_eyk_001_opt_r88_001_excludes_opt_eyk_001 | zr1x_copy_rule_opt_sfz_001_excludes_opt_eyk_001_opt_sfz_001_excludes_opt_eyk_001 | zr1x_copy_rule_opt_r88_001_excludes_opt_sfz_001_opt_r88_001_excludes_opt_sfz_001 | zr1x_copy_rule_opt_r88_001_excludes_opt_dpb_001_opt_r88_001_excludes_opt_dpb_001 | zr1x_copy_rule_opt_r88_001_excludes_opt_dpc_001_opt_r88_001_excludes_opt_dpc_001 | zr1x_copy_rule_opt_r88_001_excludes_opt_dpg_001_opt_r88_001_excludes_opt_dpg_001 | zr1x_copy_rule_opt_r88_001_excludes_opt_dpl_001_opt_r88_001_excludes_opt_dpl_001 | zr1x_copy_rule_opt_r88_001_excludes_opt_dpt_001_opt_r88_001_excludes_opt_dpt_001 | zr1x_copy_rule_opt_r88_001_excludes_opt_dsy_001_opt_r88_001_excludes_opt_dsy_001 | zr1x_copy_rule_opt_r88_001_excludes_opt_dsz_001_opt_r88_001_excludes_opt_dsz_001 | zr1x_copy_rule_opt_r88_001_excludes_opt_dt0_001_opt_r88_001_excludes_opt_dt0_001 | zr1x_copy_rule_opt_r88_001_excludes_opt_dth_001_opt_r88_001_excludes_opt_dth_001)
- defaults: defaultSelectionRules=4 (defaultSelected: opt_719_001 | opt_efr_001 | opt_j6d_001 | opt_t0e_001)
- requiredExclusiveGroups: []

