# Pass 8 — Direct Rule Field Classification Report

Status: Completed report-only classification on 2026-06-22.

Scope: classify current `runtime_action=replace` and nonblank `body_style_scope` direct-rule usage across `rule_mapping`, `grandSport_rule_mapping`, and `z06_rule_mapping`. This report did not change `stingray_master.xlsx`, generator code, runtime code, generated artifacts, or tests.

## Evidence collected

Preflight:

- Branch/status: `schema-ingestion-normalization`; `git status --short --branch` reported no tracked/untracked changes before this report pass.
- Excel lock: absent for `~$stingray_master.xlsx`.
- Workbook package validation: `.venv/bin/python scripts/validate_workbook_package.py stingray_master.xlsx` returned `status: valid`, `issue_count: 0`.

Runtime consumer evidence:

- `form-app/app.js:600` applies direct `rule.body_style_scope` with a literal equality check against `state.bodyStyle`.
- `form-app/app.js:1019` gives `runtime_action=replace` a replacement-specific disabled reason path.
- `form-app/app.js:1526` removes replacement rule targets selected/defaulted for the current variant.
- `form-app/app.js:613` has generic `scopeMatches()`, but direct rules do not use it today. Changing direct-rule matching to `scopeMatches()` remains a separate runtime behavior pass.

Generator / report consumer evidence:

- `scripts/corvette_form_generator/production.py` reads/emits `body_style_scope` and `runtime_action` for Stingray rule rows.
- `scripts/corvette_form_generator/rules.py` reads/emits `body_style_scope` and normalizes runtime action for Grand Sport/Z06 generated rule rows.
- The retired Grand Sport rule-audit helper used to carry both fields for optional report explainability; current consumers are the generator/runtime/editor paths listed here.
- `scripts/corvette_form_generator/editor_ops.py` exposes both fields as editable enum-backed workbook fields.

Generated artifact inventory:

| source | model | rules | runtime action counts | body scope counts |
|---|---:|---:|---|---|
| `form-output/runtime/stingray-runtime-contract.json` | Stingray | 144 | `active=139`, `replace=5` | blank=136, coupe=4, convertible=4 |
| `form-output/runtime/grand-sport-runtime-contract.json` | Grand Sport | 122 | `active=115`, `omit_redundant_same_section_exclude=1`, `replace=6` | blank=113, coupe=4, convertible=5 |
| `form-output/runtime/z06-runtime-contract.json` | Z06 | 73 | `active=72`, `replace=1` | blank=70, coupe=1, convertible=2 |
| `form-app/data.js` | Stingray | 144 | `active=139`, `replace=5` | blank=136, coupe=4, convertible=4 |
| `form-app/data.js` | Grand Sport | 122 | `active=115`, `omit_redundant_same_section_exclude=1`, `replace=6` | blank=113, coupe=4, convertible=5 |
| `form-app/data.js` | Z06 | 73 | `active=72`, `replace=1` | blank=70, coupe=1, convertible=2 |

Workbook inventory:

| sheet | rows | rule type counts | runtime action counts | body scope counts |
|---|---:|---|---|---|
| `rule_mapping` | 144 | includes=52, excludes=75, requires=17 | blank=139, replace=5 | blank=136, coupe=4, convertible=4 |
| `grandSport_rule_mapping` | 122 | excludes=50, includes=53, requires=19 | blank=116, replace=6 | blank=113, coupe=4, convertible=5 |
| `z06_rule_mapping` | 73 | excludes=12, includes=52, requires=9 | blank=72, replace=1 | blank=70, coupe=1, convertible=2 |

## Classification buckets used

`runtime_action=replace` rows:

- Keep as true direct default replacement for now: current direct replacement behavior is still the clearest owner.
- Exclusive peer replacement candidate: likely belongs in `*_exclusive_groups` / `*_exclusive_members`, but migration needs runtime replacement parity proof.
- Default-selection metadata candidate: likely belongs in `default_selection_rules` plus existing direct dependencies or groups, but selected/default target removal must be proven.
- Grouped dependency/blocker candidate: likely belongs in `*_rule_groups` / `*_rule_group_members` or package include/dependency metadata.
- Needs product decision: workbook metadata does not yet identify the safe owner.

`body_style_scope` rows:

- Derivable from OVS availability candidate: source/target `*_ovs` rows already make the relationship impossible outside the scoped body style.
- Rule-specific conditional scope: keep explicit direct-rule scope for now.
- Runtime scope semantics candidate: only for a later runtime pass if direct rules should use `scopeMatches()`.
- Duplicate/stale row candidate: apparent duplicate behavior requiring a later workbook parity pass before deletion.

## `runtime_action=replace` row classification

### Stingray — `rule_mapping`

| row | rule_id | source -> target | current owner signal | classification | recommendation |
|---:|---|---|---|---|---|
| 51 | `rule_opt_5zu_001_excludes_opt_t0a_001` | 5ZU / `opt_5zu_001` -> T0A / `opt_t0a_001` | Same section (`sec_spoi_001`); both active/selectable; both in `grp_spoiler_high_wing` with `single_within_group`. | Exclusive peer replacement candidate. | Later workbook cleanup may be able to remove the direct replace row after proving `grp_spoiler_high_wing` peer switching removes T0A identically. Keep row now. |
| 52 | `rule_opt_5zw_001_excludes_opt_t0a_001` | 5ZW / `opt_5zw_001` -> T0A / `opt_t0a_001` | Same section; source is inactive; source has no current exclusive group membership; target is in `grp_spoiler_high_wing`. | Needs product decision / inactive-row cleanup candidate. | If 5ZW remains inactive, this is likely inert cleanup. If 5ZW can return, decide whether it should join `grp_spoiler_high_wing` or remain a direct replacement. Do not delete in Pass 8. |
| 53 | `rule_opt_5zz_001_excludes_opt_t0a_001` | 5ZZ / `opt_5zz_001` -> T0A / `opt_t0a_001` | Same section; both active/selectable; both in `grp_spoiler_high_wing` with `single_within_group`. | Exclusive peer replacement candidate. | Same migration shape as 5ZU/T0A: group-owned peer switching may replace the direct row after parity proof. |
| 134 | `rule_opt_zf1_001_excludes_opt_t0a_001` | ZF1 / `opt_zf1_001` -> T0A / `opt_t0a_001` | Same section; source active/selectable; no shared exclusive group; raw detail says ZF1 removes T0A and front splitter from Z51 Performance Package. | Needs product decision / possible grouped dependency candidate. | Do not treat as simple duplicate. Decide whether ZF1 belongs in the spoiler exclusive group, a Z51 package dependency/default rule, or a direct replacement. Keep row until that decision is made. |
| 141 | `rule_opt_tvs_001_excludes_opt_t0a_001` | TVS / `opt_tvs_001` -> T0A / `opt_t0a_001` | Same section; both active/selectable; both in `grp_spoiler_high_wing` with `single_within_group`. | Exclusive peer replacement candidate. | Same migration shape as 5ZU/5ZZ/T0A. Keep row until runtime replacement parity is proven. |

### Grand Sport — `grandSport_rule_mapping`

| row | rule_id | source -> target | current owner signal | classification | recommendation |
|---:|---|---|---|---|---|
| 97 | `gs_rule_opt_j57_001_excludes_opt_j6a_001_replace` | J57 / `opt_j57_001` -> J6A / `opt_j6a_001` | Cross-section brake/caliper replacement; source in `gs_excl_performance_brakes`; target has no current group/default-selection owner. | Keep as true direct default replacement for now. | Leave direct replacement unless a future brake/caliper default owner is added and parity proves selected/default J6A removal is unchanged. |
| 98 | `gs_rule_opt_fey_001_excludes_opt_t0e_001_replace` | FEY / `opt_fey_001` -> T0E / `opt_t0e_001` | Package/aero replacement; source in `gs_excl_z52_packages`; target `display_behavior=default_selected`; target has Z-family default-selection rules but no Grand Sport-specific default rule in the current sheet. | Default-selection metadata candidate / grouped dependency candidate. | Future pass should decide whether Grand Sport needs an explicit T0E default-selection rule and FEY package group ownership. Keep direct replacement until proven. |
| 118 | `gs_rule_opt_feb_001_excludes_opt_jx6_001_replace` | FEB / `opt_feb_001` -> JX6 / `opt_jx6_001` | Package/brake default replacement; source in `gs_excl_z52_packages`; target `display_behavior=default_selected` and in `gs_excl_performance_brakes`. | Default-selection metadata candidate. | Candidate for default-selection/brake group ownership, but direct selected/default target removal must be parity-tested before removing the row. |
| 119 | `gs_rule_opt_fey_001_excludes_opt_jx6_001_replace` | FEY / `opt_fey_001` -> JX6 / `opt_jx6_001` | Same target/default brake pattern as FEB/JX6; source is the track package. | Default-selection metadata candidate / grouped dependency candidate. | Candidate for package-owned brake default behavior. Keep direct row until parity proof. |
| 120 | `gs_rule_opt_fey_001_excludes_opt_j56_001_replace` | FEY / `opt_fey_001` -> J56 / `opt_j56_001` | Source package replacement; target is `display_behavior=display_only`, `selectable=False`, and in `gs_excl_performance_brakes`. | Needs product decision. | Do not fold into the JX6/default-selection cleanup automatically. Decide whether J56 is a display-only component, package include/component line, or direct replacement target. |
| 121 | `gs_rule_opt_nwi_001_excludes_opt_nga_001_replace` | NWI / `opt_nwi_001` -> NGA / `opt_nga_001` | Same-section exhaust replacement; target has active default-selection rules `default_nga` and `gs_default_nga_unless_nwi`; source has no current exhaust exclusive group membership. | Default-selection metadata candidate / exclusive peer candidate. | Likely redundant with `gs_default_nga_unless_nwi` for default add behavior, but direct replacement also removes an already selected/default NGA. Later pass should test whether default-selection plus exhaust grouping can replace the row. |

### Z06 — `z06_rule_mapping`

| row | rule_id | source -> target | current owner signal | classification | recommendation |
|---:|---|---|---|---|---|
| 48 | `z06_rule_opt_j57_001_excludes_opt_j6a_001` | J57 / `opt_j57_001` -> J6A / `opt_j6a_001` | Cross-section brake/caliper replacement; source in `z06_excl_performance_brakes`; target `display_behavior=default_selected`; no default-selection row owns J6A. | Keep as true direct default replacement for now. | Current schema guard already treats this as the remaining active Z06 replacement. Keep until a future brake/caliper default owner is designed and parity-tested. |

## `body_style_scope` row classification

### Stingray — `rule_mapping`

| row | rule_id | scope | source -> target | OVS/body signal | classification | recommendation |
|---:|---|---|---|---|---|---|
| 54 | `rule_opt_b6p_001_includes_opt_d3v_001` | coupe | B6P -> D3V | Source and target are coupe-only. | Derivable from OVS availability candidate. | Candidate for later body-scope deletion after proving generated/runtime parity. |
| 56 | `rule_opt_bc4_001_includes_opt_d3v_001` | coupe | BC4 -> D3V | Source is coupe+convertible; target is coupe-only. | Derivable from target OVS availability candidate. | Candidate for later body-scope deletion after parity proof. |
| 57 | `rule_opt_bc4_002_requires_opt_zz3_001` | convertible | BC4 -> ZZ3 | Source is coupe+convertible; target is convertible-only. | Derivable from target OVS availability candidate. | Candidate for later body-scope deletion after parity proof. |
| 58 | `rule_opt_bcp_001_includes_opt_d3v_001` | coupe | BCP -> D3V | Source is coupe+convertible; target is coupe-only. | Derivable from target OVS availability candidate. | Candidate for later body-scope deletion after parity proof. |
| 59 | `rule_opt_bcp_002_requires_opt_zz3_001` | convertible | BCP -> ZZ3 | Source is coupe+convertible; target is convertible-only. | Derivable from target OVS availability candidate. | Candidate for later body-scope deletion after parity proof. |
| 60 | `rule_opt_bcs_001_includes_opt_d3v_001` | coupe | BCS -> D3V | Source is coupe+convertible; target is coupe-only. | Derivable from target OVS availability candidate. | Candidate for later body-scope deletion after parity proof. |
| 61 | `rule_opt_bcs_002_requires_opt_zz3_001` | convertible | BCS -> ZZ3 | Source is coupe+convertible; target is convertible-only. | Derivable from target OVS availability candidate. | Candidate for later body-scope deletion after parity proof. |
| 142 | `rule_opt_bc7_001_requires_opt_zz3_001_convertible` | convertible | BC7 -> ZZ3 | Source is coupe+convertible; target is convertible-only. | Derivable from target OVS availability candidate. | Candidate for later body-scope deletion after parity proof. |

### Grand Sport — `grandSport_rule_mapping`

| row | rule_id | scope | source -> target | OVS/body signal | classification | recommendation |
|---:|---|---|---|---|---|---|
| 3 | `gs_rule_opt_b6p_001_includes_opt_d3v_001` | coupe | B6P -> D3V | Source and target are coupe-only. | Derivable from OVS availability candidate. | Candidate for later body-scope deletion after parity proof. |
| 5 | `gs_copy_rule_opt_bc4_002_requires_opt_zz3_001_opt_bc4_002_requires_opt_zz3_001_convertible` | convertible | BC4 -> ZZ3 | Source is coupe+convertible; target is convertible-only. Same source/type/target/scope as row 95. | Duplicate/stale row candidate plus derivable from target OVS availability. | Later workbook cleanup should compare rows 5 and 95, delete only one if parity proves no generated/runtime behavior drift. |
| 6 | `gs_rule_opt_bc4_002_includes_opt_d3v_001` | coupe | BC4 -> D3V | Source is coupe+convertible; target is coupe-only. | Derivable from target OVS availability candidate. | Candidate for later body-scope deletion after parity proof. |
| 7 | `gs_copy_rule_opt_bc7_001_requires_opt_zz3_001_convertible_opt_bc7_001_requires_opt_zz3_001_convertible` | convertible | BC7 -> ZZ3 | Source is coupe+convertible; target is convertible-only. | Derivable from target OVS availability candidate. | Candidate for later body-scope deletion after parity proof. |
| 8 | `gs_copy_rule_opt_bcp_002_requires_opt_zz3_001_opt_bcp_002_requires_opt_zz3_001_convertible` | convertible | BCP -> ZZ3 | Source is coupe+convertible; target is convertible-only. | Derivable from target OVS availability candidate. | Candidate for later body-scope deletion after parity proof. |
| 9 | `gs_rule_opt_bcp_002_includes_opt_d3v_001` | coupe | BCP -> D3V | Source is coupe+convertible; target is coupe-only. | Derivable from target OVS availability candidate. | Candidate for later body-scope deletion after parity proof. |
| 10 | `gs_copy_rule_opt_bcs_002_requires_opt_zz3_001_opt_bcs_002_requires_opt_zz3_001_convertible` | convertible | BCS -> ZZ3 | Source is coupe+convertible; target is convertible-only. | Derivable from target OVS availability candidate. | Candidate for later body-scope deletion after parity proof. |
| 11 | `gs_rule_opt_bcs_002_includes_opt_d3v_001` | coupe | BCS -> D3V | Source is coupe+convertible; target is coupe-only. | Derivable from target OVS availability candidate. | Candidate for later body-scope deletion after parity proof. |
| 95 | `gs_rule_opt_bc4_002_requires_opt_zz3_001_convertible` | convertible | BC4 -> ZZ3 | Source is coupe+convertible; target is convertible-only. Same source/type/target/scope as row 5. | Duplicate/stale row candidate plus derivable from target OVS availability. | Treat row 5/95 as a paired cleanup candidate. Deletion requires a separate workbook parity pass. |

### Z06 — `z06_rule_mapping`

| row | rule_id | scope | source -> target | OVS/body signal | classification | recommendation |
|---:|---|---|---|---|---|---|
| 3 | `z06_rule_opt_b6p_001_includes_opt_d3v_001` | coupe | B6P -> D3V | Source and target are coupe-only. | Derivable from OVS availability candidate. | Candidate for later body-scope deletion after parity proof. |
| 47 | `z06_rule_opt_bcw_001_requires_opt_zz3_001_convertible` | convertible | BCW -> ZZ3 | Source is coupe+convertible; target is convertible-only. | Derivable from target OVS availability candidate. | Candidate for later body-scope deletion after parity proof. |
| 49 | `z06_rule_opt_pbc_001_requires_opt_zz3_001_convertible` | convertible | PBC -> ZZ3 | Source is coupe+convertible; target is convertible-only. | Derivable from target OVS availability candidate. | Candidate for later body-scope deletion after parity proof. |

## Later-pass candidates

### Candidate A — Body-style scope retirement parity pass

Recommended next implementation pass.

Scope:

- Workbook-only source cleanup for nonblank `body_style_scope` direct-rule rows that this report classified as OVS-derivable.
- Include the Grand Sport row 5/95 duplicate pair as an explicitly reviewed deletion candidate.
- No runtime `scopeMatches()` behavior change in this pass.

Required proof:

- Snapshot current runtime contracts.
- Remove only approved body-scope values/duplicate rows through safe workbook write.
- Regenerate affected models and registry.
- Compare generated contracts with timestamp-only tolerance where row deletion is not intended to alter behavior; for any intentionally deleted duplicate row, assert the specific expected count/key change and verify runtime behavior remains equivalent.
- Run targeted Stingray, Grand Sport, Z06, and multi-model runtime tests.

### Candidate B — Stingray spoiler replacement ownership pass

Scope:

- Decide whether 5ZU, 5ZZ, TVS, and possibly 5ZW/ZF1 should be owned by `grp_spoiler_high_wing`, default-selection/package metadata, or remain direct `runtime_action=replace` rows.
- Do not bundle with Grand Sport/Z06 brake/package replacement cleanup.

Required proof:

- Runtime tests for selecting each candidate spoiler source while T0A is selected/defaulted.
- Generated/runtime contract comparison showing only approved row/group changes.

### Candidate C — Grand Sport package/default replacement ownership pass

Scope:

- Classify FEY/FEB package relationships to T0E, JX6, and J56.
- Decide whether Grand Sport needs explicit default-selection rules for T0E/JX6/J56 or whether direct replacement should remain.
- Keep row 120 (`FEY` -> display-only `J56`) separate until product ownership is clear.

Required proof:

- Runtime tests for FEY/FEB selected package behavior, default target removal, and selectable peer behavior.
- Generated contract comparison and targeted Grand Sport test updates.

### Candidate D — Exhaust default replacement pass

Scope:

- Decide whether `gs_rule_opt_nwi_001_excludes_opt_nga_001_replace` can be owned by `gs_default_nga_unless_nwi` plus exhaust exclusive-group/default metadata.
- Add NWI to an exhaust group only if product behavior confirms NWI/NGA are true peers.

Required proof:

- Runtime tests for NGA default add, NWI replacing selected/default NGA, and reselect behavior.

### Candidate E — Direct-rule scope semantics runtime pass

Scope:

- If direct rules should support `*`/pipe scope syntax like price rules, default rules, rule groups, and runtime exceptions, change `ruleAppliesToCurrentVariant()` to use `scopeMatches()`.
- This is a runtime behavior pass, not a workbook cleanup pass.

Required proof:

- Focused tests for blank, literal `*`, single body, and pipe-separated body scopes.
- Multi-model runtime switching tests.

## Decisions and non-decisions

Decisions made by this report:

- `runtime_action` and `body_style_scope` are still live behavior fields and should not be deleted as generic cleanup.
- Most body-scoped direct rules are plausible OVS-derived cleanup candidates, but deletion must be parity-proven.
- Grand Sport BC4/ZZ3 rows 5 and 95 are the only apparent duplicate/stale direct-rule pair found in the scoped inventory.
- Several replacement rows need product ownership decisions before migration.

Non-decisions:

- No workbook columns or rows were deleted.
- No generated rule fields were trimmed.
- No runtime matching semantics changed.
- No optional audit/report artifact was refreshed.
- No ZR1/ZR1X rule cleanup or price-rule semantic classification was attempted.
