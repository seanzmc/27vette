# Workbook Consistency Review — Stingray / Grand Sport / Z06

Date: 2026-06-11
Workbook: `stingray_master.xlsx` (read-only audit; no writes performed)
Scope: `stingray_options` / `grandSport_options` / `z06_options`, `exclusive_groups(+_members)` / `grandSport_exclusive_*` / `z06_exclusive_*`, plus copy-owning metadata sheets (`context_choice_copy`, `section_master`, `section_presentation`, `order_summary_sections`, `rule_phrase_map`). ZR1/ZR1X excluded per scope.

Baseline gate: `.venv/bin/python scripts/validate_workbook_schema.py stingray_master.xlsx` → `status: valid, 0 errors, 0 warnings`. No `~$stingray_master.xlsx` lock present during the audit.

Classification key: **[ENFORCED]** = violates an already-enforced standard; **[GAP]** = real inconsistency the standardization tests don't cover; **[NEW]** = newly observed inconsistency not previously addressed.

---

## 1. Summary

| Category | Blocker | Inconsistency | Cosmetic | Needs human review |
|---|---|---|---|---|
| Structural (S) | 1 | 6 | 2 | 2 |
| Display order (D) | 0 | 5 | 2 | 1 |
| Copy (C) | 1 | 3 systemic patterns (~95 rows) | 1 systemic pattern (~40 rows) | 3 |

- **0 violations of enforced standards.** The schema validator passes and both standardization tests' assertions hold. However, one enforced test *encodes* a punctuation inconsistency rather than preventing it (see C-4).
- **Test-coverage gaps** account for most findings: cell typing on Z06 sheets, exclusive-group membership parity, cross-model copy parity, and display-order uniqueness are all unenforced.
- Affected-model skew: Z06 carries the typing drift (ingest legacy); **Stingray** is the majority deviator on copy (51 names, 91 descriptions differ from the GS+Z06 majority).

---

## 2. Structural Findings

| ID | Sheet / key | Model(s) | Description | Severity | Class |
|---|---|---|---|---|---|
| S-1 | `z06_options`, column `display_order`, 245 of 249 rows (all except rows 59, 245–247) | Z06 | `display_order` stored as **text strings** (`'50'`, `'40'`, …) while Stingray/Grand Sport store integers. Crashes naive numeric sorts (`'<' not supported between int and str` — reproduced during this audit) and makes mixed-type sheets fragile for any consumer that doesn't coerce. `rpo`/`price`/`selectable`/`active` types are clean on all three sheets. | **Blocker** (for tooling robustness; generator currently coerces) | GAP — `workbook-schema-standardization.test.mjs` "canonical raw Excel types" covers rpo strings, GS booleans, and prices, but not `display_order` typing and not `z06_options` at all |
| S-2 | `z06_exclusive_members`, column `display_order`, rows 2–17 | Z06 | Same string-typed `display_order` (`'10'`…`'30'`) on the first 16 member rows; rows 18–41 (later-authored groups) are integers. Mixed types **within one sheet**. | Inconsistency | GAP |
| S-3 | `rule_mapping` rows `rule_opt_rik_001_excludes_*` (6 pairwise excludes among RIK/RIN/SL8) vs `gs_excl_rear_script_badges` (`grandSport_exclusive_groups` row 5) and `z06_excl_rear_script_badges` (`z06_exclusive_groups` row 4) | Stingray deviates | The same business relationship (rear script badge colors mutually exclusive) is modeled as **6 pairwise `excludes` rules** on Stingray but as an **exclusive group** on GS/Z06. Pairwise excludes block selection rather than radio-replacing, so the customer interaction differs across models for the identical accessory set. | Inconsistency | GAP — the "active explicit excludes do not duplicate exclusive-group peers" test only fires when a group exists; Stingray has no group, so the alternate path is invisible to it |
| S-4 | `z06_options` rows 223 (`opt_u2k_002`/U2K), and rows for `opt_u5g_002` (U5G), `opt_ue1_002` (UE1), `opt_vv4_002` (VV4), `opt_cfv_002` (CFV) vs `opt_*_001` for the same RPOs in `stingray_options`/`grandSport_options` | Z06 deviates | Same RPO carries a **different `option_id` suffix** on Z06 (`_002` vs `_001` elsewhere, with no `_001` row present on Z06). Breaks `option_id` as a cross-model join key for these RPOs; any cross-model tooling must fall back to RPO matching. (`opt_cfv_002` exists because GS's `opt_cfv_001` is `active=False`; the others have no such excuse.) | Inconsistency | NEW |
| S-5 | `z06_options` rows 25, 145–146, 166–187, 223 (`opt_167`, `opt_289`, `opt_295`, `opt_085`…`opt_332`) vs `stingray_options`/`grandSport_options` `opt_001`–`opt_026` | Z06 deviates | No-RPO (standard-equipment text) rows use sparse ingest-era IDs (`opt_085`, `opt_329`, …) on Z06 vs compact sequential `opt_001`–`opt_026` on SR/GS. Same convention class, different numbering style. | Cosmetic | NEW |
| S-6 | `exclusive_groups` group_ids `grp_ls6_engine_covers`, `grp_spoiler_high_wing`, `excl_*` vs `gs_excl_*` vs `z06_excl_*` | Stingray | Group-ID prefix convention drift: Stingray mixes `grp_` and `excl_` (no model prefix); GS and Z06 use uniform `<model>_excl_*`. | Cosmetic | NEW |
| S-7 | `z06_options` row 98 `opt_wks_001` (WKS, "Premium Indoor Car Cover", `sec_lpoe_001`) vs `z06_exclusive_groups` row 3 `z06_excl_indoor_car_covers` (members: RWH, WKR only) | Z06 | WKS is an indoor car cover sold alongside RWH/WKR but is **not a member of the indoor-car-cover exclusive group**. Stingray's equivalent group (`excl_indoor_car_covers`) contains all four of its indoor covers (RWH, SL1, WKR, WKQ). A customer can select WKS + RWH simultaneously on Z06. | Inconsistency (likely behavior defect) | GAP |
| S-8 | `order_summary_sections` (11 rows, all `model_key=stingray`), `step_order_summary_map` (13 rows, all `stingray`) | GS, Z06 missing | Order-summary grouping metadata exists only for Stingray; generated `form-app/data.js` confirms `orderSummary` is present for Stingray and absent for grandSport/z06 (runtime falls back to defaults). Same for `runtime_rule_exceptions` (4 rows, stingray-only — may be genuinely model-specific). | Inconsistency | NEW |
| S-9 | `exclusive_groups` Stingray group set (no brake, no exterior-accent-with-EFY membership parity… see Intentional) | — | Group *presence* differences between models were checked against each model's option set; all remaining presence differences trace to genuine option-set differences (see §5). No missing-group defects beyond S-7. | — | — |
| S-10 | `order_summary_sections` column `active` stores text `'TRUE'`; `notes`-bearing metadata sheets elsewhere store real booleans | shared | Boolean-as-text drift in a workbook-owned metadata sheet (generator `truthy()` tolerates it). | Cosmetic | GAP |

Needs-human-review structural items are in §6 (R-1, R-2).

## 3. Display Order Findings

| ID | Sheet / key | Model(s) | Description | Severity | Class |
|---|---|---|---|---|---|
| D-1 | `z06_options` `sec_lpoe_001`: rows 86 (`opt_rwj_001` RWJ) and 98 (`opt_wks_001` WKS) both `display_order='72'` | Z06 | Duplicate display_order within section → nondeterministic relative order. | Inconsistency | GAP |
| D-2 | `z06_options` `sec_incl_001`: rows 61/66 (`opt_fe6_002` FE6, `opt_drg_001` DRG) both `'10'`; rows 62/67 (`opt_fe7_001` FE7, `opt_tr7_001` TR7) both `'20'`. `sec_stan_001`: rows 186/192 (`opt_329`, `opt_g0k_001` G0K) both `'120'`; rows 198/200 (`opt_u80_001` U80, `opt_wub_001` WUB) both `'20'` | Z06 | Duplicate orders in standard/included sections (display-only impact). | Inconsistency | GAP |
| D-3 | `stingray_options` `sec_cust_001`: rows 10/11 (`opt_bv4_001` BV4, `opt_r8c_001` R8C) both `10`. `sec_lpoe_001`: rows 40/41 (`opt_pcx_001` PCX, `opt_vk3_001` VK3) both `30`. `grandSport_options` `sec_engi_001`: rows 50/52 (`opt_d3v_001` D3V, `opt_bc7_001` BC7) both `10` | Stingray, GS | Duplicate orders on live selectable sections. | Inconsistency | GAP |
| D-4 | `sec_whee_002` shared carbon/forged wheels: GS order `ROU, SON, SOM, ROX, …` vs Z06 `ROU, SON, ROX, SOM, …` (`grandSport_options` vs `z06_options`, options `opt_som_001`, `opt_rox_001`) | Z06 vs GS | SOM/ROX relative order swapped between sibling models in the same section. | Inconsistency | GAP |
| D-5 | `sec_roof_001`: Stingray order `…CC3, CF8, CM9, D84, D86` vs GS/Z06 `…CC3, CM9, CF8, D84, D86` (`opt_cf8_001`, `opt_cm9_001`) | Stingray deviates | CF8 (electrochromic roof panel, coupe) vs CM9 (convertible hardtop) swapped. The visual-copy test pins CF7/C2Z/CC3 at 10/11/12 but not CF8/CM9. | Inconsistency | GAP — partially adjacent to enforced roof-panel ordering |
| D-6 | `sec_cust_001`: SR `BV4, R8C, PIN` vs GS/Z06 `R8C, PIN, BV4`; `sec_lpoe_001`: SR `…SFZ, SBT, VTB, VWE, R88…` vs GS/Z06 `…SFZ, R88, SBT, VTB, VWE…`; `sec_engi_001`: SR `BC7, B6P, ZZ3, D3V…` vs GS `B6P, ZZ3, D3V, BC7…` | Stingray deviates (mostly) | Relative-order drift for shared options within same-purpose sections. Note `sec_engi_001` GS order interacts with D-3's duplicate `10`. | Inconsistency | GAP |
| D-7 | `z06_exclusive_members` row 2: `z06_excl_center_caps` members start at `display_order='20'` (5ZC@20, 5ZD@30; no 10) | Z06 | Non-monotonic start; harmless but signals a removed first member (5ZB is GS-only). | Cosmetic | NEW |
| D-8 | `gs_excl_ls6_engine_covers` (`grandSport_exclusive_members`) member order BC7@10, **BC4@30, BCP@50, BCS@70** vs `grandSport_options` `sec_engi_001` enforced order BC7=10, BCP=20, BCS=30, BC4=40 (visual-copy test) and Stingray's group order BC7, BCP, BCS, BC4 | GS | Exclusive-group member ordering disagrees with the reviewed/enforced options-sheet ordering for the same options. Which surface drives UI ordering determines impact; the two sources should not disagree. | Cosmetic→Inconsistency (depends on consumer) | GAP |

## 4. Copy Findings

Copy owner notes: option names/descriptions are owned by the three `*_options` sheets. Trim-card tooltips are owned by `context_choice_copy`. Section labels by `section_master` with model overrides in `section_presentation`. `rule_phrase_map` owns no customer copy in scope.

### C-1 — BLOCKER: truncated description (defect)
`grandSport_options` row 31, `opt_eyt_001` (EYT), column `description`:

| Model | Text |
|---|---|
| Stingray (row 2) | "Includes Crossed Flags on nose, Stingray emblem on decklid, and Corvette lettering on rear fascia" |
| **Grand Sport (row 31)** | "Crossed flags on the nose and rear decklid, Corvette lettering on rear fascia, **and**" ← sentence cut off mid-clause |
| Z06 (row 28) | "Crossed flags on the nose and rear decklid, Corvette lettering on rear fascia and Z06 on side quarter" |

GS is the deviator; the Z06 sibling shows what the completed sentence shape should be (GS presumably needs its own model-appropriate ending). Class: **NEW**. Fix in `grandSport_options.description`.

### C-2 — Systemic: Stingray copy diverges from the GS+Z06 majority (51 names, 91 descriptions)
For shared `option_id`s (162 across all three), Grand Sport and Z06 agree with each other almost everywhere; **Stingray is the deviating model** in ~50 of 51 name mismatches. GS/Z06 copy reads as the later, reviewed generation (shorter names, qualifiers moved to descriptions per the copy-density policy); Stingray retains verbose pre-cleanup copy. Representative examples (full list reproducible via the audit method; sheet = each model's `*_options`, column `option_name`):

| option_id (RPO) | Stingray (deviator) | GS + Z06 (majority) |
|---|---|---|
| `opt_aj7_001` (AJ7) row SR209/GS161/Z147 | Driver and Passenger Frontal and Side-Impact Airbags | Frontal and Side-Impact Airbags |
| `opt_cj2_001` (CJ2) SR221/GS189/Z191 | Dual-Zone Automatic Air Conditioning | Dual-Zone Automatic Climate Control |
| `opt_dth_001` (DTH) SR129/GS233/Z210 | Carbon Flash Metallic Full-Length Dual Racing Stripes | Carbon Flash Metallic Racing Stripes |
| `opt_efr_001` (EFR) SR30/GS62/Z58 | Carbon Flash Exterior Accents | Carbon Flash Painted Accents |
| `opt_k7a_001` (K7A) SR171/GS5/Z3 | Wireless Phone Charging | Single Wireless Phone Charging Pad |
| `opt_sxb_001` (SXB) SR76/GS116/Z108 | Black Suede Frunk and Trunk Compartment Liner | Black Suede Frunk and Trunk Liner |
| `opt_drz_001` (DRZ) SR216/GS167/Z148 | Full-Camera Display Rear Camera Mirror | Auto-Dimming Rear Camera Mirror |

Description mismatches follow the same pattern (e.g. `opt_dwk_001` DWK: SR "With turn signal indicators." vs majority "Manual-folding with turn signal indicators"; stripe options DPB/DPC/DPG/DPL/DPT/DSY/DSZ/DT0/DTH/DUB/DUW: SR blank vs majority "Full-length dual design"). Note the name/description pairs are complementary — Stingray keeps the qualifier in the name, GS/Z06 moved it to the description — so per-row "fixes" must move both fields together, not just overwrite names.

Severity: Inconsistency (systemic). Class: **GAP** — `workbook-visual-copy-standardization.test.mjs` pins only specific reviewed rows (brake calipers, roof panels, GS engine covers, accessory branding) and does not compare models pairwise. Z06 sheet is entirely untested.

A handful of rows have substantive (not just stylistic) divergence and are listed in §6 instead: DRZ, EFR/EDU, NGA.

### C-3 — Z06 copy drift inside the GS/Z06 pair (small)
- `opt_nwi_001` (NWI) description: GS "Quad Center Exit. New for 2027" vs Z06 "Quad center exit" (Z06 row 56) — capitalization + dropped "New for 2027". Deviator: Z06. Owner: `z06_options.description`.
- `opt_nga_001` (NGA): GS "Standard. Corner Exit" vs Z06 "Standard" (Z06 row 55). Z06 NGA is quad-center, so dropping "Corner Exit" is plausibly intentional → cross-listed in §6.
- `opt_zz3_001` (ZZ3): Z06 correctly drops "(BC7) Black LS6 engine cover" from the includes list (no BC7 on Z06) — intentional, listed §5.

### C-4 — Systemic punctuation drift: trailing periods
~40 shared LPO/accessory descriptions end with a period on Stingray and **no period** on GS/Z06 (e.g. `opt_5zc_001` 5ZC: SR "LPO. Genuine Corvette Accessory." vs GS/Z06 "LPO. Genuine Corvette Accessory"; same for RIK, RIN, SL8, RWH, RWJ, SXB/SXR/SXT, SC7, S08, RYT, PDY, PEF, RIA, CAV, 5JR, and more). Severity: Cosmetic, but it is **encoded into the enforced test**: `workbook-visual-copy-standardization.test.mjs` expects `"…Genuine Corvette Accessory."` for `stingray_options` rows and `"…Genuine Corvette Accessory"` (no period) for `grandSport_options` rows (e.g. opt_pef_001, opt_cav_001). Any punctuation standardization must update that test in the same pass. Class: GAP/enforced-but-inconsistent.

### C-5 — Z06 trim cards have no tooltip copy
`context_choice_copy` rows 2–4 define `trim_level` tooltips only for values `1LT/2LT/3LT` (wildcard `model_key='*'`). Z06 trims are `1LZ/2LZ/3LZ`, so generated Z06 trim cards carry `info_tooltip=false` (verified in `form-app/data.js` contextChoices) while SR/GS cards have tooltips. Deviator: Z06 (by omission). Owner: `context_choice_copy` — add 1LZ/2LZ/3LZ rows (or z06-scoped rows). Severity: Inconsistency. Class: **NEW**.

### C-6 — No draft/inspection wording leaks found
Searched shared-option names/descriptions on GS and Z06 for migration-era draft phrasing; none surfaced in source-sheet copy. (Artifact *filenames* under `form-output/inspection/` still carry draft naming, as the README notes — out of scope here.)

## 5. Intentional Model Differences (retained, not defects)

- **Exclusive-group presence** tracks real option-set differences: Stingray-only groups `grp_spoiler_high_wing` (T0A/TVS/5ZZ/5ZU), `excl_center_caps` (RXJ/VWD/5ZD/5ZC/RXH), `excl_outdoor_car_covers` (RNX/RWJ — GS/Z06 carry only RWJ), `excl_ext_accents` includes EFY (EFY absent on GS); GS-only `gs_excl_z52_packages` (FEB/FEY), `gs_excl_performance_brakes` with JX6 (JX6 GS-only; Stingray's J55 is `selectable=False` standard equipment, hence no SR brake group); Z06-only `z06_excl_carbon_wheel_packages` (PDB/PDD/PDF), `z06_excl_aero_packages` (T0E/T0F/T0G/5ZV), `z06_excl_fa5_fa6_interior_trim`, `z06_excl_default_and_carbon_wheels` (12-member wheel group), `z06_excl_exhaust_tips` (NGA/NWI; the GS equivalent `gs_excl_exhaust_path` is deliberately `active=False` with an explanatory note). All verified against each model's `*_options` RPO presence.
- **No LS6 engine-cover group on Z06**: BC4/BCP/BCS don't exist in `z06_options` (different engine). Consistent with memory: Z-models omit groups whose member options don't exist.
- `opt_eyk_001`/`opt_eyt_001` names and Z06 EYT description referencing "Z06 on side quarter" — model-specific emblem content.
- `opt_vyw_001` (VYW) Z06 description "LPO. Z06 logo, …" vs SR/GS "car silhouette logo on Stingray, Grand Sport, ZR1 and ZR1X models" — matches GM's published applicability split (Z06 gets its own logo mat). The comma after "Z06 logo" should arguably be a period (cosmetic).
- `opt_wub_001` (WUB) in `sec_stan_001` on Z06 (standard equipment there) vs `sec_exha_001` selectable on SR/GS — known intentional (WUB is Z06 standard).
- `opt_zz3_001` ZZ3 includes-list difference (no BC7 on Z06).
- `opt_sfz_001` (SFZ) GS/Z06 description "Front and rear on Grand Sport, Z06, ZR1 and ZR1X models" vs SR generic — applicability-accurate.
- GS/Z06 section taxonomy (`sec_perf_support_001`, `sec_seat_002`, `sec_stan_001` for trim-standard rows) vs Stingray's older sections (`sec_perf_001`, trim sections `sec_2lte_001`/`sec_3lte_001`, `sec_incl_001`) for E60/ERI/AH2/AQ9/B4Z/G0K/UQT — these reflect the newer GS-era section model, not row-level errors. Cross-listed in §6 because the *direction* of convergence is a product decision.

## 6. Needs Human Review

| ID | Item | Rationale |
|---|---|---|
| R-1 | `opt_uv6_001` (UV6, Head-Up Display): SR/GS `sec_2lte_001` vs Z06 `sec_1lte_001` (`z06_options` row for opt_uv6_001) | Could be genuine (HUD standard from 1LZ on Z06) or a mis-sectioned row. Verify against the Z06 order guide before touching. |
| R-2 | `opt_sc7_001` (SC7 roof panel storage pouch): SR `sec_lpoi_001` (LPO interior) vs GS/Z06 `sec_lpoe_001` (LPO exterior) | Same accessory, different LPO bucket. Either could be the intended catalog placement. |
| R-3 | `opt_drz_001` (DRZ) copy: SR name "Full-Camera Display Rear Camera Mirror"/desc "Inside rearview auto-dimming." vs GS/Z06 name "Auto-Dimming Rear Camera Mirror"/desc "Inside rearview with full camera display" | The name/description content is *swapped*, not just restyled. Both renderings are defensible; pick one canonical pair before standardizing C-2. |
| R-4 | `opt_efr_001`/`opt_edu_001` (EFR/EDU accent descriptions): SR short ("Side vents and front/rear grille accents.") vs GS/Z06 long CFV/CFZ-conditional wording | The GS/Z06 long description references CFV/CFZ ground effects, which **don't exist on Stingray** — SR's short copy may be intentionally model-correct, so this is not a simple majority-wins overwrite. |
| R-5 | `opt_nga_001` (NGA) Z06 description "Standard" (vs GS "Standard. Corner Exit") | Z06's NGA is quad-center-exit, so dropping "Corner Exit" looks deliberate, but then SR/GS/Z06 descriptions should each state their exit style explicitly; currently Z06 says nothing. |
| R-6 | `sec_seat_002` ordering/multiplicity: SR `AE4, AE4, AH2, AE4, AUP` vs GS `AE4, AE4, AE4, AH2, AUP` (per-trim seat rows) | Seat rows are per-trim price variants; relative AH2 placement differs. Whether trim grouping or seat grouping should win is a presentation decision. |

## 7. Recommendations

All fixes are workbook-source changes; none belong in scripts or runtime.

1. **(S-1/S-2, mechanical)** Retype `z06_options.display_order` (245 rows) and `z06_exclusive_members.display_order` (rows 2–17) as integers via a `save_workbook_safely()` pass. Extend the "canonical raw Excel types" test in `tests/workbook-schema-standardization.test.mjs` to assert numeric `display_order` (and boolean flags) on **all three** live option sheets and both member sheets — currently `z06_options` has zero type coverage. *Recommend this as the first follow-up pass: smallest blast radius, removes the audit-crashing data shape.*
2. **(S-7 + D-1)** Add `opt_wks_001` to `z06_excl_indoor_car_covers` in `z06_exclusive_members` (display_order 30) and give WKS a unique `display_order` in `z06_options` `sec_lpoe_001` (currently `'72'` colliding with RWJ). Behavior change → needs approval + Z06 gates + browser check of the LPO Exterior section.
3. **(S-3)** Migrate Stingray RIK/RIN/SL8 pairwise excludes (`rule_mapping`, 6 rows) to a `excl_rear_script_badges` exclusive group + members, matching GS/Z06 radio behavior. Mark the old rows per the lifecycle convention (`normalization_status`), don't delete. Extend the schema-standardization duplication test or add a parity assertion that same-purpose groups exist across models where all member RPOs exist.
4. **(D-1–D-3)** Deduplicate display_order collisions in the six cited section/sheet spots. Cheap to enforce: add a "display_order unique within (sheet, section_id)" assertion to the schema-standardization test (or `validate_workbook_schema.py` if preferred as a structural rule).
5. **(D-4–D-6, D-8)** Align shared-option relative order: decide canonical order per section (GS/Z06 majority is the natural canon), fix the deviating sheet, and reconcile `gs_excl_ls6_engine_covers` member order with the test-enforced `grandSport_options` order. The wheels SOM/ROX swap (D-4) is the only GS-vs-Z06 sibling drift and is a two-cell fix in whichever sheet is wrong.
6. **(C-1)** Fix the truncated GS EYT description (`grandSport_options` row 31) — one cell, but write the correct GS-specific ending (likely "…and Grand Sport emblem/lettering" per the order guide), don't copy the Z06 text.
7. **(C-2/C-4)** Treat Stingray copy convergence as its own labeled pass: adopt the GS/Z06 majority copy for the ~50 stylistic name and ~85 description rows on `stingray_options`, moving qualifiers name→description in matched pairs, while excluding the §6 items (R-3/R-4/R-5) pending decisions. Update `workbook-visual-copy-standardization.test.mjs` in the same pass — it currently pins period/no-period drift (C-4) and only covers SR+GS; extend it to load `z06_options` and assert pairwise name/description equality for shared option_ids with an explicit allowlist for intentional model differences (§5). That allowlist-based parity test is the durable guard this audit currently substitutes for.
8. **(C-5)** Add `1LZ/2LZ/3LZ` trim tooltip rows to `context_choice_copy` (Z06-appropriate copy). Regenerate Z06 and assert `info_tooltip` presence in `tests/z06-contract-preview.test.mjs`.
9. **(S-8)** Decide whether GS/Z06 should get `order_summary_sections` / `step_order_summary_map` rows (recommended for parity — the labels are model-generic) or whether the runtime fallback is the intended contract; if the fallback is intended, document it in AGENTS.md.
10. **(S-4)** Optional normalization: re-key Z06's `opt_u2k_002/u5g_002/ue1_002/vv4_002` to `_001` so option_id is a reliable cross-model join key. Touches `z06_options`, `z06_ovs`, any rule/member/override references — verify reference integrity with the schema validator after. Low customer impact, moderate touch surface; only worth doing if cross-model tooling (like this audit) becomes routine.

---

## Handoff

**What changed:** this report file only (`workbook-consistency-review-2026-06-11.md`). Audit scratch scripts were written to `/tmp/` (outside the repo).
**What did not change:** `stingray_master.xlsx` (no writes; no lock file present), generated `form_*` sheets, `form-output/`, `form-app/data.js`, scripts, tests, runtime behavior.
**Gates run:** `validate_workbook_schema.py` → valid, 0 errors/warnings (read-only baseline). Generators and node test suites **not run** — read-only pass, nothing to regenerate.
**Pending manual verification:** §6 items R-1–R-6 need order-guide/product confirmation; S-7 (WKS co-selectable with RWH) should be reproduced in the browser before fixing.
**Suggested next pass:** Recommendation 1 (Z06 display_order/typing normalization + type-test extension) — smallest, lowest-risk, unblocks reliable tooling for the copy-convergence pass (Recommendation 7).
