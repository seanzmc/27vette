# Grand Sport Phase 3 Exclusive Groups Spec

> Spec only. Do not implement this pass. This plan defines Grand Sport model-scoped single-choice cleanup using the existing `exclusiveGroups` / `single_within_group` behavior while preserving Stingray.

## Goal

Identify Grand Sport option sets where only one option should be selected at a time, then plan model-scoped `exclusiveGroups` for those sets.

This phase is intentionally narrow:

- use existing runtime behavior;
- do not add runtime branches;
- do not add broad compatibility rules;
- do not change prices;
- do not clean display text;
- do not reorder sections or options;
- do not alter Stingray exclusive groups.

## Diagnosis

Grand Sport now has a populated Base Interior contract, but the active Grand Sport model still has no rule surfaces for option conflicts:

| Surface | Current Grand Sport state | Phase 3 implication |
| --- | ---: | --- |
| `rules` | 0 | Out of scope except where the answer is "leave for rules phase." |
| `ruleGroups` | 0 | Out of scope for Z15/hash-mark requirements. |
| `exclusiveGroups` | 0 | Primary Phase 3 target. |
| `priceRules` | 0 | Out of scope. |

Stingray already uses `exclusiveGroups` for multi-select sections where the section itself cannot enforce one-of-many behavior:

| Stingray group | Current purpose |
| --- | --- |
| `grp_ls6_engine_covers` | one LS6 engine cover |
| `grp_spoiler_high_wing` | one high-wing spoiler |
| `excl_center_caps` | one center cap style |
| `excl_indoor_car_covers` | one indoor car cover |
| `excl_outdoor_car_covers` | one outdoor car cover |
| `excl_suede_trunk_liner` | one suede frunk/trunk liner |

Grand Sport should mirror that model-scoped pattern only where Grand Sport options sit in multi-select sections and represent true one-of-many choices. Sections already marked `single_select_req` or `single_select_opt` should generally be left alone because the existing section `selection_mode` already enforces same-section exclusivity.

Risk level for later implementation: medium. The intended data change is model-scoped, but it affects live selection behavior and exports because previously co-selected Grand Sport options would become mutually exclusive. Stingray regression coverage is required.

Behavior class for later implementation: functional data-contract behavior. No styling, UI layout, export schema, pricing, or broad rules work is part of this phase.

## Exact Files To Inspect Later

- `form-app/data.js`
  - Active multi-model registry and generated Grand Sport draft data.
- `form-app/app.js`
  - Existing `exclusiveGroups` runtime behavior; inspect only to understand behavior, not to branch for Grand Sport.
- `scripts/corvette_form_generator/model_config.py`
  - Add a model-config field only if needed to carry model-scoped exclusive group definitions.
- `scripts/corvette_form_generator/model_configs.py`
  - Likely home for Grand Sport group configuration.
- `scripts/corvette_form_generator/inspection.py`
  - Likely draft-data emission point for Grand Sport `exclusiveGroups`.
- `scripts/generate_stingray_form.py`
  - Required generator entrypoint that writes the multi-model runtime data.
- `tests/grand-sport-draft-data.test.mjs`
  - Add generated-data assertions for Grand Sport exclusive groups.
- `tests/multi-model-runtime-switching.test.mjs`
  - Add runtime selection assertions and Stingray isolation checks.
- `tests/stingray-form-regression.test.mjs`
  - Assert Stingray exclusive groups remain unchanged if existing coverage is not sufficient.

## Constraints

- Preserve Stingray behavior and generated output.
- Keep all Grand Sport exclusive groups model-scoped.
- Use the existing `exclusiveGroups` / `single_within_group` mechanism.
- Do not activate Grand Sport `rules`, `ruleGroups`, or `priceRules`.
- Do not implement `Z15`, `Z25`, `FEY`, or `EL9` package behavior.
- Do not change labels, descriptions, capitalization, section placement, option ordering, UI layout, export schema, or Formidable wiring.
- Preserve raw `source_detail_raw` evidence.

## Recommended Exclusive Groups

These groups are true one-of-many choices in multi-select Grand Sport sections. They should become Grand Sport-only `exclusiveGroups`.

| group_id | Group label | RPO members | Option IDs | Section | Mirrors Stingray group? | Variant/body/trim scope | Existing section handles it? | Recommendation |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `gs_excl_ls6_engine_covers` | Grand Sport LS6 Engine Covers | `BC7`, `BC4`, `BCP`, `BCS` | `opt_bc7_001`, `opt_bc4_001`, `opt_bc4_002`, `opt_bcp_001`, `opt_bcp_002`, `opt_bcs_001`, `opt_bcs_002` | `sec_engi_001` / Engine Appearance | Yes, mirrors `grp_ls6_engine_covers` concept. Grand Sport has duplicated price-scope rows for `BC4`, `BCP`, and `BCS`. | All listed option IDs are active across the six Grand Sport variants in the current draft. Package/pricing detail remains out of scope. | No. Section is `multi_select_opt`. | Add as `exclusiveGroup`. |
| `gs_excl_center_caps` | Grand Sport Wheel Center Caps | `5ZB`, `5ZC`, `5ZD` | `opt_5zb_001`, `opt_5zc_001`, `opt_5zd_001` | `sec_whee_001` / Wheel Accessory | Yes, partial counterpart to Stingray `excl_center_caps`. | Active across the six Grand Sport variants. | No. Section is `multi_select_opt`. | Add as `exclusiveGroup`. |
| `gs_excl_indoor_car_covers` | Grand Sport Indoor Car Covers | `RWH`, `WKR` | `opt_rwh_001`, `opt_wkr_001` | `sec_lpoe_001` / LPO Exterior | Yes, partial counterpart to Stingray `excl_indoor_car_covers`. | Active across the six Grand Sport variants. | No. Section is `multi_select_opt`. | Add as `exclusiveGroup`. |
| `gs_excl_rear_script_badges` | Rear Corvette Script Badge Colors | `RIK`, `RIN`, `SL8` | `opt_rik_001`, `opt_rin_001`, `opt_sl8_001` | `sec_lpoe_001` / LPO Exterior | No direct current Stingray group. | Active across the six Grand Sport variants. | No. Section is `multi_select_opt`. | Add as `exclusiveGroup`. |
| `gs_excl_suede_compartment_liners` | Suede Frunk/Trunk Compartment Liners | `SXB`, `SXR`, `SXT` | `opt_sxb_001`, `opt_sxr_001`, `opt_sxt_001` | `sec_lpoi_001` / LPO Interior | Yes, mirrors Stingray `excl_suede_trunk_liner` concept. | Active across the six Grand Sport variants. | No. Section is `multi_select_opt`. | Add as `exclusiveGroup`. |

## Candidate Groups To Leave Alone

These option sets were inspected but should not become Phase 3 `exclusiveGroups`.

| Candidate | RPO members | Section | Existing section handles it? | Recommendation | Reason |
| --- | --- | --- | --- | --- | --- |
| Wheels | `ROY`, `ROZ`, `STZ`, `SWM`, `SWN`, `SWO`, `SWP` | `sec_whee_002` / Wheels | Yes. Section is `single_select_req`. | Leave alone. | Same-section one-of-many behavior already exists. `ROY`/`ROZ`/`STZ` prerequisites belong to a later rules phase. |
| Calipers | `J6A`, `J6B`, `J6D`, `J6E`, `J6F`, `J6L`, `J6N` | `sec_cali_001` / Caliper Color | Yes. Section is `single_select_req`. | Leave alone. | Same-section exclusivity already exists. `J6D`/`J6L` package or brake eligibility belongs to rules. |
| Roof panels and convertible tops | `C2Z`, `CC3`, `CF7`, `CF8`, `CM9`, `D84`, `D86` | `sec_roof_001` / Roof | Yes. Section is `single_select_req`. | Leave alone. | Same-section exclusivity already exists, and body-style availability is already variant-scoped. |
| Spoilers | `5ZV`, `ZYC` | `sec_spoi_001` / Spoiler | Yes. Section is `single_select_opt`. | Leave alone. | Same-section exclusivity already exists. `5ZV` conflicts with `T0F`/`FEY` are broad rules, not a pure one-of-many group. |
| Full-length stripes and stingers | `DPB`, `DPC`, `DPG`, `DPL`, `DPT`, `DSY`, `DSZ`, `DT0`, `DTH`, `DUB`, `DUE`, `DUK`, `DUW`, `DZU`, `DZV`, `DZX`, `SHT`, `VPO`, `Z15` | `sec_stri_001` / Stripes | Yes. Section is `single_select_opt`. | Leave alone. | Same-section exclusivity already exists. Cross-section conflicts with center stripes, hash marks, `CF8`, `R88`, `SFZ`, `SHT`, and `VPO` belong to rules. |
| Grand Sport center stripes | `DMU`, `DMV`, `DMW`, `DMX`, `DMY` | `sec_gsce_001` / Grand Sport Center Stripes | Yes. Section is `single_select_opt`. | Leave alone. | Same-section exclusivity already exists. `Z15` dependencies and paint/roof constraints belong to rules. |
| Grand Sport heritage hash marks | `17A`, `20A`, `55A`, `75A`, `97A`, `DX4` | `sec_gsha_001` / Grand Sport Heritage Hash Marks | Yes. Section is `single_select_opt`. | Leave alone for Phase 3. | Same-section exclusivity already exists. `Z15` requiring one hash mark is a later `ruleGroup`, not an `exclusiveGroup`. |
| Lug nuts and wheel locks | `S47`, `SFE`, `SPY`, `SPZ` | `sec_whee_001` / Wheel Accessory | No. Section is `multi_select_opt`. | Leave for rules. | Relationships include requires/excludes such as `SPZ` requiring `SPY` and `SPY` excluding `S47`; this is not a simple one-of-many group. |
| Outdoor car covers | `RWJ` | `sec_lpoe_001` / LPO Exterior | No. Section is `multi_select_opt`. | Leave alone. | Grand Sport currently has only one outdoor cover candidate, so there is no group to enforce. |
| LPO exterior package children | `PCQ`, `VWE`, `VWT` | `sec_lpoe_001` / LPO Exterior | No. Section is `multi_select_opt`. | Leave for rules/price rules. | `PCQ` includes child items and likely needs package pricing behavior, not mutual exclusion. |
| LPO interior package children | `PDY`, `RYT`, `S08`, `PEF`, `CAV`, `RIA` | `sec_lpoi_001` / LPO Interior | No. Section is `multi_select_opt`. | Leave for rules/price rules. | These are package include relationships. `CAV` and `RIA` are not mutually exclusive liners. |
| Interior accessories | `RWU`, `S2L`, `SC7`, `V8X`, `VYW`, `W2D` | `sec_lpoi_001` / LPO Interior | No. Section is `multi_select_opt`. | Leave alone. | Standalone accessories or variant-scoped accessories, not one-of-many. |
| Interior trim options | `BAZ`, `FA5`, `N26`, `TU7`, `UQT` | `sec_inte_001` / Interior Trim | No. Section is `multi_select_opt`. | Leave for rules if needed. | These are packages, seat dependencies, steering wheel, or recorder options, not a single-choice set. |
| Exhaust | `NGA`, `NWI`, `WUB` | `sec_exha_001` / Exhaust | No. Section is `multi_select_opt`. | Leave for rules. | Relationships are replacement/requires/includes behavior, not simple exclusivity. |
| Performance and aero | `CFL`, `CFV`, `CFZ`, `E60`, `ERI`, `FEB`, `FEY`, `J57`, `T0F` | `sec_perf_001` / Performance | No. Section is `multi_select_opt`. | Leave for rules/price rules. | Ground effects, Z52, brakes, lift, and aero package behavior requires requires/excludes/includes logic. |

## Recommended Implementation Phases

### Phase 3A: Data Contract Tests First

Add failing tests that assert Grand Sport has only the proposed model-scoped `exclusiveGroups` and that each group has exact membership.

Test targets:

- `tests/grand-sport-draft-data.test.mjs`
  - Assert `data.exclusiveGroups.length === 5`.
  - Assert group IDs and labels match this spec.
  - Assert exact option IDs for each group.
  - Assert all member option IDs exist in Grand Sport `choices`.
  - Assert groups do not include any Stingray-only members.

### Phase 3B: Runtime Behavior Tests

Use existing runtime selection behavior without adding Grand Sport branches.

Test targets:

- `tests/multi-model-runtime-switching.test.mjs`
  - Select one member of each Grand Sport group, then select another member and assert the previous member is removed.
  - Assert selections outside the group remain selected.
  - Switch back to Stingray and assert Stingray exclusive groups still behave as before.
  - Assert Stingray exclusive group definitions are unchanged.

### Phase 3C: Generator/Data Emission

Implement the smallest model-scoped path that emits these Grand Sport groups into draft data.

Likely files:

- `scripts/corvette_form_generator/model_config.py`
- `scripts/corvette_form_generator/model_configs.py`
- `scripts/corvette_form_generator/inspection.py`

Avoid editing `form-app/app.js` unless testing proves the current generic `exclusiveGroups` runtime behavior cannot consume model-scoped generated groups. If that happens, stop and write a smaller follow-up spec before changing runtime behavior.

### Phase 3D: Generated Artifacts

After approval, regenerate with the project venv:

```bash
.venv/bin/python scripts/generate_stingray_form.py
```

Expected generated-file churn may include:

- `form-app/data.js`
- `form-output/stingray-form-data.json`
- `form-output/inspection/grand-sport-form-data-draft.json`
- `form-output/inspection/grand-sport-form-data-draft.md`
- `form-output/inspection/grand-sport-contract-preview.json`
- `form-output/inspection/grand-sport-contract-preview.md`
- `form-output/inspection/grand-sport-inspection.json`
- `form-output/inspection/grand-sport-inspection.md`
- `stingray_master.xlsx` timestamp churn from validation, if the generator touches it.

## Validation Plan For Later Implementation

Run the existing required gates:

```bash
.venv/bin/python scripts/generate_stingray_form.py
node --test tests/stingray-form-regression.test.mjs
node --test tests/grand-sport-contract-preview.test.mjs
node --test tests/grand-sport-draft-data.test.mjs
node --test tests/multi-model-runtime-switching.test.mjs
```

Additional assertions to add before implementation:

- Grand Sport `exclusiveGroups` are generated with exact group IDs and option IDs from this spec.
- Selecting one Grand Sport group member removes prior selected members from that same group.
- Selecting one group member does not remove unrelated options in the same multi-select section.
- Existing single-select sections continue to rely on `selection_mode`, not duplicate `exclusiveGroups`.
- Stingray `exclusiveGroups` remain unchanged in IDs, labels, and members.
- Stingray runtime behavior, generated output, and exports remain unchanged.

## Manual Browser Checks For Later Implementation

After tests pass:

- Switch to Grand Sport.
- Select body style, trim, seat, and Base Interior.
- In Engine Appearance, select two LS6 engine covers and confirm only the latest remains selected.
- In Wheel Accessory, select two center cap options and confirm only the latest remains selected.
- In LPO Exterior, select both indoor car covers and confirm only the latest remains selected.
- In LPO Exterior, select multiple rear Corvette script badge colors and confirm only the latest remains selected.
- In LPO Interior, select multiple suede frunk/trunk compartment liners and confirm only the latest remains selected.
- Confirm unrelated options in the same sections remain selectable together.
- Switch to Stingray and verify existing Stingray exclusive groups still behave correctly.

## Non-Goals

- Do not activate broad Grand Sport rules.
- Do not implement `Z15`, `Z25`, `FEY`, or `EL9` behavior.
- Do not add price rules.
- Do not alter Stingray exclusive groups.
- Do not change app runtime behavior unless a separately approved runtime spec is created.
- Do not change UI or export schema.
- Do not wire Formidable.
