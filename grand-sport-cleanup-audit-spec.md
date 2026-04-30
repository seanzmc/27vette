# Grand Sport Cleanup Audit Spec

> Spec only. Do not implement this pass. This audit defines the concrete cleanup work needed for the active Grand Sport model in the multi-model app while preserving Stingray behavior.

## Goal

Audit the active `grandSport` runtime registry data and produce a cleanup plan for:

- option display text;
- capitalization;
- duplicate/redundant text;
- display order;
- section placement;
- choice groups / exclusive groups;
- obvious pricing gaps;
- obvious rule/compatibility gaps.

Primary constraint: preserve Stingray behavior. Do not change Stingray data, rules, pricing, exports, UI behavior, generated artifacts, or workbook source content during this audit phase.

## Diagnosis

Grand Sport is now active in `form-app/data.js` under `window.CORVETTE_FORM_DATA.models.grandSport.data`, and the app defaults to Stingray through `defaultModelKey: "stingray"`. The runtime can switch models and preserves the legacy `window.STINGRAY_FORM_DATA` alias for Stingray.

Current Grand Sport contract state from the active runtime registry:

| Surface | Grand Sport | Stingray baseline | Cleanup implication |
| --- | ---: | ---: | --- |
| Variants | 6 | 6 | Variant surface exists. |
| Steps | 14 | 14 | Step count matches Stingray, but `base_interior` has no Grand Sport sections. |
| Sections | 34 | 39 | Grand Sport omits Stingray interior sections and suspension/LPO wheel sections. |
| Choices | 1,614 | 1,548 | Choice surface exists, repeated per variant. |
| Rules | 0 | 238 | Compatibility is not implemented for Grand Sport. |
| Price rules | 0 | 43 | Included/package price adjustment is not implemented. |
| Exclusive groups | 0 | 6 | Multi-choice mutual exclusion is not implemented. |
| Rule groups | 0 | 2 | Grouped requirements such as Z15 hash marks are not implemented. |
| Interiors | 0 | 130 | Base Interior step is empty in the browser. |
| Validation warnings | 6 | 3 | Grand Sport still carries draft/deferred warning state. |

Browser evidence:

- Selecting Grand Sport shows the correct title and base model context, e.g. `Grand Sport Order Form` and `Corvette Grand Sport Coupe 1LT`.
- The `Base Interior` step displays `0 choices` and `Select a seat first.` because Grand Sport has no generated `interiors`.
- Selecting `FEY` adds only `FEY`; no `J57`, `J6D`, `WUB`, `T0F`, `CFZ`, or `XFS` auto-added/included rows appear.
- Selecting `Z15` adds only `Z15`; no required hash mark choice is enforced or auto-added.
- Grand Sport currently shows many raw draft labels/descriptions such as `New Blue LS6 engine cover`, generic `Seats`, generic `Calipers`, `Available`, and long OnStar copy.

Risk level: high for implementation, low for this audit. The cleanup touches model-specific generated data, runtime compatibility behavior, and tests if implemented later. The audit itself should remain read-only.

Behavior class: mixed for future implementation. Text/order/section cleanup is data-contract behavior; choice groups, pricing, rules, interiors, and compatibility are functional behavior. No styling work is required.

## Exact Files To Inspect

- `form-app/data.js`
  - Active multi-model registry and current Grand Sport generated runtime data.
- `form-app/app.js`
  - Runtime behavior for model switching, selection, rules, exclusive groups, price rules, interiors, export titles, and open requirements.
- `form-app/index.html`
  - Model picker and static app shell.
- `scripts/generate_stingray_form.py`
  - Live generator entrypoint that writes the multi-model registry and must preserve Stingray behavior.
- `scripts/generate_grand_sport_form.py`
  - Grand Sport inspection/draft entrypoint.
- `scripts/corvette_form_generator/model_configs.py`
  - Grand Sport section labels, section-step overrides, category overrides, special rule review RPOs, and text cleanup config.
- `scripts/corvette_form_generator/inspection.py`
  - Grand Sport contract preview and draft artifact generation.
- `form-output/inspection/grand-sport-contract-preview.json`
- `form-output/inspection/grand-sport-contract-preview.md`
- `form-output/inspection/grand-sport-form-data-draft.json`
- `form-output/inspection/grand-sport-form-data-draft.md`
- `tests/grand-sport-contract-preview.test.mjs`
- `tests/grand-sport-draft-data.test.mjs`
- `tests/multi-model-runtime-switching.test.mjs`
- `tests/stingray-form-regression.test.mjs`

## Non-Goals

- Do not edit code in this audit pass.
- Do not regenerate or change `form-app/data.js`.
- Do not change `stingray_master.xlsx`.
- Do not change Stingray generator behavior, rules, pricing, exports, or UI behavior.
- Do not redesign the app layout.
- Do not add dependencies.
- Do not infer final compatibility rules from wording without preserving raw `source_detail_raw` evidence.
- Do not hide raw source detail; customer-facing cleanup must preserve raw fields for audit.

## Prioritized Cleanup List

### P0: Keep Stingray Isolated

Any implementation must be Grand Sport-scoped and prove:

- `registry.defaultModelKey` remains `stingray`.
- `window.STINGRAY_FORM_DATA === registry.models.stingray.data`.
- Stingray choices, rules, price rules, exclusive groups, rule groups, interiors, exports, and UI flow remain unchanged.

Likely files:

- `scripts/corvette_form_generator/model_configs.py`
- `scripts/generate_stingray_form.py`
- `form-app/app.js`, only if runtime behavior must become model-generic.
- `tests/stingray-form-regression.test.mjs`
- `tests/multi-model-runtime-switching.test.mjs`

### P1: Restore Grand Sport Interior Contract

Problem:

- Grand Sport has `interiors: 0`, so `Base Interior` is a live empty step.
- Browser shows `0 choices` even after the default `AQ9` seat is selected.
- Special package logic for `EL9` cannot work until interiors exist.

Known RPOs / IDs:

- `EL9`: Santorini Blue Dipped with red/Torch Red accents interior, referenced in raw rule detail.
- `Z25`: Grand Sport Launch Edition, includes `EL9` and `3F9`.
- `3F9`: Torch Red seat belt color, included with `EL9` and `Z25`.
- `AE4`, `AH2`, `AQ9`, `AUP`: seat choices that must filter compatible interiors.
- `D30`, `R6X`, `36S`, `37S`, `38S`, `N26`, `TU7`: interior-related component/override pricing and compatibility candidates.

Cleanup needed:

- Add Grand Sport LT interior hierarchy, including EL9 where valid.
- Ensure Base Interior displays valid choices for each body/trim/seat.
- Preserve Stingray rule that EL9 is inactive for Stingray.

### P1: Implement Deferred Compatibility Surfaces

Problem:

- Grand Sport has zero `rules`, `priceRules`, `exclusiveGroups`, and `ruleGroups`.
- Runtime currently permits selections whose raw details say they require, exclude, include, or are only available with other choices.

High-priority rule groups and rules:

- `Z15` requires one hash mark: `17A`, `20A`, `55A`, `75A`, `97A`, `DX4`.
- Hash marks require `Z15`:
  - `17A` excludes `GKA`.
  - `20A` excludes `GTR`.
  - `55A` excludes `GBK`.
  - `75A` excludes `GKZ` and `GPH`.
  - `97A` requires `Z15`.
  - `DX4` excludes `GKZ` and `GPH`.
- Grand Sport center stripes require `Z15`:
  - `DMU`, `DMV`, `DMW`, `DMX`, `DMY`.
  - `DMV` excludes `GKA`.
  - `DMW` excludes `G8G`.
  - `DMX` excludes `GTR`.
  - `DMY` excludes `GKZ` and `GPH`.
  - `DMV`, `DMW`, `DMX`, `DMY` have conditional `D84` roof/nacelle requirements by paint.
- `FEY` includes `J57`, `J6D`, `XFS`, `WUB`, `T0F`, and `CFZ`.
- `T0F` requires `FEB` plus `J57`, or is included with `FEY`.
- `J57` includes or requires `J6D`; `J6L` requires `J57`.
- `5ZV` excludes `T0F` and `FEY`.
- `CF8` excludes full-length racing stripes and GS center stripes.
- `CFL` excludes `CFV` and `CFZ`.
- `CFV` is not available at this time.
- `CFZ` is included with `T0F`.
- `WUB` is included with `FEY`; `NWI` requires `WUB`.
- `SHT` excludes all RPO stripes and `Z15`.
- `VPO` excludes `Z15`.
- `R88` excludes `SFZ`, `EYK`, full-length stripes, and GS center stripes.
- `SFZ` excludes `EYK`, full-length stripes, and GS center stripes.
- `R8C` is not available with LPO wheels.
- `PCQ` includes `VWE` and `VWT`.
- `PDY` includes `RYT` and `S08`.
- `PEF` includes `CAV` and `RIA`.
- `SPZ` requires `SPY`; `SPY` excludes `S47`; `S47` and `SFE` exclude `SPY` and `ROY`/`ROZ`/`STZ`.
- `ROY`, `ROZ`, and `STZ` require `J57`.
- `Z25` includes `EL9`, `3F9`, unique floor mats, embossed headrests, and waterfall plaque.

### P1: Choice Groups / Exclusive Groups

Problem:

- Sections with `single_select_*` already enforce one choice within that section, but cross-section and multi-choice groups are missing.
- `Wheel Accessory`, `LPO Exterior`, `LPO Interior`, `Performance`, and `Exhaust` allow incompatible combinations today.

Proposed groups:

| Proposed group | Type | RPO members |
| --- | --- | --- |
| GS hash marks | single within group / Z15 requirement target | `17A`, `20A`, `55A`, `75A`, `97A`, `DX4` |
| GS center stripes | single within group | `DMU`, `DMV`, `DMW`, `DMX`, `DMY` |
| Full-length stripes and stingers | single within group, already section-scoped but needs cross-section excludes | `DPB`, `DPC`, `DPG`, `DPL`, `DPT`, `DSY`, `DSZ`, `DT0`, `DTH`, `DUB`, `DUE`, `DUK`, `DUW`, `DZU`, `DZV`, `DZX` |
| Wheel center caps | likely single within multi-select accessory section | `5ZB`, `5ZC`, `5ZD` |
| Lug nuts / locks | requires/excludes rather than pure exclusive | `S47`, `SFE`, `SPY`, `SPZ` |
| Carbon fiber wheels | prerequisite group | `ROY`, `ROZ`, `STZ` require `J57` |
| Calipers | section single-select plus package-driven replacement | `J6A`, `J6B`, `J6D`, `J6E`, `J6F`, `J6L`, `J6N` |
| Ground effects / aero | package compatibility group | `CFL`, `CFV`, `CFZ`, `T0F`, `5ZV` |
| Car covers | likely single cover choice | `RWH`, `RWJ`, `WKR` |
| LPO package children | include/zero-price groups | `PCQ` -> `VWE`, `VWT`; `PDY` -> `RYT`, `S08`; `PEF` -> `CAV`, `RIA` |
| OnStar/mobile services | mutual exclusions/requirements | `PRB`, `R9L`, `R9V`, `R9W`, `R9Y`, `U2K`, `UE1` |

### P2: Text Cleanup

Problem examples visible in active Grand Sport:

- Marketing prefix still appears in labels:
  - `BC4` `New Blue LS6 engine cover`
  - `CFL` `New Ground Effects`
  - `GEC` `New Pitch Gray Metallic`
  - `GTR` `New Admiral Blue Metallic`
  - `LS6` `New Engine`
  - `M1N` `New Transmission`
  - `NWI` `New Exhaust tips`
  - `WUB` `New Exhaust`
- Generic labels hide the actual choice in the description:
  - `AQ9`, `AH2`, `AUP`: `Seats`
  - `J6A`, `J6B`, `J6D`, `J6E`, `J6F`, `J6L`, `J6N`: `Calipers`
  - `NGA`, `NPP`, `WUB`: `Exhaust` / `Exhaust tips`
  - `CF7`, `CC3`, `C2Z`, `CF8`: `Roof panel`
  - `D84`, `D86`, `CM9`: `Convertible top`
  - `BC4`, `BCP`, `BCS` duplicates with different prices.
- Capitalization and punctuation issues:
  - `5ZC`: `LPO, Jake logo wheel center caps.`
  - `SWM` appears once as `wheels` and once as `Wheels`.
  - `36S`, `37S`, `38S` labels use lowercase `custom leather stitch`.
  - Descriptions often start lowercase, e.g. `includes seats...`, `premium carpeted...`, `driver 8-way power`.
- Duplicative display text:
  - `V8X`: `LPO, Visible Carbon Fiber sill plates Genuine Corvette Accessory` has the accessory phrase in the label instead of the description.
  - Many LPO labels repeat `LPO,` and descriptions repeat `Genuine Corvette Accessory`; preserve raw text, but normalize display fields.
- Overly long labels/descriptions:
  - `PRB`, `R9V`, `R9W`, `R9Y`, and blank-RPO OnStar rows are too long for customer-facing cards.
  - `FEY` and `IVE` descriptions are long but may be acceptable if the layout handles them; audit should decide whether to summarize display text while preserving raw detail.
- Missing descriptions:
  - GS hash marks `17A`, `20A`, `55A`, `75A`, `97A`, `DX4`.
  - GS center stripes `DMU`, `DMV`, `DMW`, `DMX`, `DMY`.
  - Several stripe choices show `Available`, which is low-value customer copy.

Text cleanup requirements:

- Preserve raw `source_option_name`, `source_description`, and `source_detail_raw`.
- Clean customer-facing `label` and `description` only.
- Keep RPOs, package names, and compatibility meaning exact.
- Add text cleanup notes for every changed display field.

### P2: Display Order

Problem examples:

- Grand Sport `Exterior Appearance` currently renders `Engine Appearance` before `Roof`, GS center stripes, GS hash marks, exterior accents, and badges. Stingray’s working model puts Roof and exterior accent/badge choices earlier.
- Grand Sport `Aero, Exhaust, Stripes & Accessories` puts `Exhaust` and `Stripes` before `Spoiler` and `LPO Exterior`. That may be acceptable, but GS-specific graphics are split into `Exterior Appearance` while `Z15` lives in `Stripes`, creating a separated package-and-dependent-choice experience.
- Wheels render high-cost carbon fiber wheels before the standard wheel `SWM`; Stingray generally keeps default/standard choices easy to find.
- `Grand Sport Center Stripes` renders before `Grand Sport Heritage Hash Marks`, but `Z15` requires hash marks and only allows center stripes as additional graphics.
- `Wheel Accessory` mixes center caps, lug nuts, and locks. It likely needs internal ordering: center caps, lug nuts, locks.
- `LPO Exterior` mixes mirror covers, grille packages, badges, covers, roof/accessory items, screens, and car covers.
- `LPO Interior` mixes protection packages with package children and standalone accessories.

Recommended order cleanup:

- Preserve top-level Stingray step order.
- Keep body style order: Coupe, Convertible.
- Keep trim order: 1LT, 2LT, 3LT.
- In Wheels:
  - show standard wheel `SWM` first, then paid aluminum wheels `SWN`, `SWO`, `SWP`, then carbon-fiber wheels `ROY`, `ROZ`, `STZ`.
  - show standard caliper `J6A` first, package-only/included `J6D` last or disabled until `J57`.
  - order wheel accessories by center caps, lug nuts, locks.
- In GS graphics:
  - keep `Z15` near its required hash marks, or move GS hash marks/center stripes into the same customer flow section.
  - hash marks should appear before center stripes because `Z15` requires a hash mark.
- In Performance:
  - order packages first (`FEB`, `FEY`, `T0F`), then dependent components (`J57`, `CFZ`, `WUB`), then standalone options (`E60`, `ERI`, `CFL`, `CFV`).
- In accessories:
  - group LPO exterior by badges, mirrors, grille/screens, covers, roof/storage/protection, car covers.
  - group LPO interior packages before package child items or suppress included children when package-selected.

### P2: Section / Category Placement

Problem examples:

- `base_interior` step has no sections for Grand Sport.
- `Z15` sits in `sec_stri_001` under `aero_exhaust_stripes_accessories`, while dependent `17A`/`20A`/`55A`/`75A`/`97A`/`DX4` and `DMU`/`DMV`/`DMW`/`DMX`/`DMY` sit in `exterior_appearance`.
- `sec_gsce_001` and `sec_gsha_001` are labeled well for Grand Sport, but their flow relation to `Z15` is poor.
- `Z25` in `Special Edition` under `packages_performance` is reasonable, but its included interior/seat-belt content must connect to Base Interior and Seat Belt.
- `V8X` is in LPO Interior with a zero price and `Not available at this time`; decide whether unavailable rows should be hidden or shown disabled.
- `PCQ`, `PDY`, and `PEF` are already explicit blank-section overrides and must remain explicit.

Recommended placement cleanup:

- Add Grand Sport interior sections equivalent to Stingray base interior flow.
- Decide whether GS graphics should remain split by section or be grouped into one step experience. Prefer existing Stingray step order, with section placement adjusted rather than adding a new top-level step.
- Keep `sec_spec_001` as `Special Edition` in `packages_performance`.
- Keep `sec_colo_001` in `interior_trim`, but validate whether D30/R6X should be hidden until an eligible interior context exists.
- Review OnStar rows currently under `interior_trim`; they may belong in a delivery/services or standard/options group, but changing step placement is non-goal unless it improves customer flow without affecting Stingray.

### P2: Pricing

Obvious pricing gaps / review items:

- Grand Sport has no `priceRules`, so package-included items remain independently priced if selected separately.
- `FEY` should zero/include `J57`, `J6D`, `XFS`, `WUB`, `T0F`, and `CFZ` when appropriate.
- `T0F` should include/zero `CFZ` and enforce its prerequisites.
- `J57` should include or force `J6D`.
- `PCQ`, `PDY`, and `PEF` package children should be included/zeroed when package-selected.
- `Z25` should handle included `EL9`, `3F9`, floor mats/headrest/plaque content if represented as separate selectable/standard rows.
- Grand Sport active data has price differences versus Stingray for shared RPOs:
  - `BC4`: Grand Sport has `$595` and `$695`; Stingray has `$695`.
  - `BCP`: Grand Sport has `$595` and `$695`; Stingray has `$695`.
  - `BCS`: Grand Sport has `$595` and `$695`; Stingray has `$695`.
  - `VWE`: Grand Sport `$950`; Stingray `$695`.
- Zero-price review:
  - `V8X` is `$0` but marked not available at this time.
  - `17A`, `20A`, `55A`, `75A`, `97A`, `DX4` are `$0` but should likely be included/required under paid `Z15`, not standalone free customer choices.
  - `J6D` is `$0` and only available with `J57`; it should not behave as a free standalone caliper.
  - `XFS`, `J56`, `XFR`, `T0E`, `TR7`, `CFX`, `DRG` are included-only rows and should not be customer-selectable as normal paid/free options.

### P3: Customer-Facing Wording Polish

After functional cleanup is scoped, do a narrower copy pass:

- Replace `Available` descriptions with meaningful display descriptions or blank descriptions.
- Decide whether `New` should stay customer-facing for new model-year colors/options.
- Normalize title case for labels without changing raw fields.
- Shorten OnStar and Mobile Service display labels while keeping raw detail.
- Expand generic labels where the description carries the actual choice, e.g. `Black Painted Calipers` instead of `Calipers`.

## Recommended Implementation Phases

### Phase 1: Audit Artifact Only

Create or extend a read-only Grand Sport cleanup report from active registry data:

- Unique active option list by RPO/option ID.
- Section/step placement table.
- Text cleanup candidate table.
- Price-difference table versus Stingray for shared RPOs.
- Rule hot spot table from `draftMetadata.ruleDetailHotSpots`.
- Browser smoke notes for visible gaps.

No generated data writes.

### Phase 2: Interior Contract Repair

Add Grand Sport interiors and EL9 handling in model-scoped data generation. Validate Base Interior browser flow before touching rules broadly.

### Phase 3: Rules, Rule Groups, Exclusive Groups

Add Z15/hash-mark, FEY/T0F/J57/WUB/CFZ, package-child, wheel accessory, stripe/graphics, spoiler/aero, and OnStar compatibility rules.

### Phase 4: Price Rules

Add package-driven zeroing and component price adjustments for included children, EL9/Z25, FEY/T0F/J57, and LPO packages.

### Phase 5: Text, Order, Placement Cleanup

Apply display label/description cleanup, display ordering, and section placement improvements after functional dependencies are stable.

### Phase 6: Browser QA And Export Check

Smoke the active Grand Sport model end to end and verify Stingray still passes unchanged.

## Files Likely To Change Later

- `scripts/corvette_form_generator/model_config.py`
  - If cleanup needs new model-scoped config fields for display order, text overrides, rule extraction, or grouping.
- `scripts/corvette_form_generator/model_configs.py`
  - Grand Sport-specific text/order/section/rule config.
- `scripts/corvette_form_generator/inspection.py`
  - If read-only cleanup reports or draft audit artifacts are added.
- `scripts/generate_grand_sport_form.py`
  - If Grand Sport draft generation expands beyond current inspection artifacts.
- `scripts/generate_stingray_form.py`
  - Only if registry writing or shared generation needs model-generic support; keep Stingray output stable.
- `form-app/app.js`
  - Only for runtime support of model-generic rules/interiors/price rules where current code is Stingray-specific.
- `form-app/data.js`
  - Generated output only after approval; never hand-edit.
- `form-output/inspection/*.json`
- `form-output/inspection/*.md`
- `tests/grand-sport-contract-preview.test.mjs`
- `tests/grand-sport-draft-data.test.mjs`
- `tests/multi-model-runtime-switching.test.mjs`
- `tests/stingray-form-regression.test.mjs`

## Tests Needed

Generator / artifact tests:

- Grand Sport active registry contains six variants: `1lt_e07`, `2lt_e07`, `3lt_e07`, `1lt_e67`, `2lt_e67`, `3lt_e67`.
- Grand Sport has nonzero interiors after Phase 2.
- Grand Sport `Base Interior` has choices for every valid body/trim/seat combination.
- EL9 is active only for Grand Sport and only in the valid Z25 context.
- Raw `source_detail_raw` is preserved for every cleaned display row.
- Text cleanup notes are emitted when label/description fields are changed.

Runtime tests:

- Switching Stingray -> Grand Sport -> Stingray clears model-specific selections without changing customer fields.
- Grand Sport export title is `2027 Corvette Grand Sport`; Stingray export title remains `2027 Corvette Stingray`.
- `Z15` requires one of `17A`, `20A`, `55A`, `75A`, `97A`, `DX4`.
- Hash mark paint exclusions work for `GKA`, `GTR`, `GBK`, `GKZ`, and `GPH`.
- GS center stripes require `Z15` and enforce paint/D84 conditions where supported.
- `FEY` auto-adds/includes or otherwise locks `J57`, `J6D`, `XFS`, `WUB`, `T0F`, and `CFZ` according to the chosen rule model.
- `T0F` requires `FEY` or the approved `FEB` + `J57` path.
- `J6D` is not a free standalone caliper.
- `PCQ` includes `VWE` and `VWT`.
- `PDY` includes `RYT` and `S08`.
- `PEF` includes `CAV` and `RIA`.
- `SPZ` requires `SPY`; `SPY` excludes `S47`.
- `ROY`, `ROZ`, and `STZ` require `J57`.
- Existing Stingray regression test still passes.

Required validation commands after implementation approval:

```sh
.venv/bin/python scripts/generate_stingray_form.py
node --test tests/stingray-form-regression.test.mjs
node --test tests/grand-sport-contract-preview.test.mjs
node --test tests/grand-sport-draft-data.test.mjs
node --test tests/multi-model-runtime-switching.test.mjs
```

## Manual Browser Checks Needed

Use the active multi-model app:

1. Confirm app defaults to Stingray.
2. Switch to Grand Sport and confirm title, base price, body style order, and trim order.
3. Walk every step and confirm no empty step remains, especially `Base Interior`.
4. Select a paint, then verify hash mark and center stripe exclusions by paint:
   - `GKA` with `17A` / `DMV`
   - `GTR` with `20A` / `DMX`
   - `GBK` with `55A`
   - `GKZ` and `GPH` with `75A`, `DX4`, `DMY`
5. Select `Z15`; verify one hash mark is required and only valid GS center stripes remain additionally available.
6. Select `FEY`; verify included components and pricing behavior.
7. Select `T0F` without prerequisites; verify requirements appear.
8. Select `J57`; verify `J6D` behavior.
9. Test `5ZV` with `T0F` and `FEY`.
10. Test wheel accessories:
    - `5ZB`, `5ZC`, `5ZD`
    - `S47`, `SFE`, `SPY`, `SPZ`
    - `ROY`, `ROZ`, `STZ`
11. Test LPO packages:
    - `PCQ` with `VWE`, `VWT`
    - `PDY` with `RYT`, `S08`
    - `PEF` with `CAV`, `RIA`
12. Test `Z25`; verify `EL9` and `3F9` behavior.
13. Export Grand Sport JSON and CSV; verify schema is unchanged and title/model are correct.
14. Switch back to Stingray; confirm Stingray baseline behavior still works.

## Approval Boundary

This document is the audit/spec deliverable. Implementation should not begin until a specific phase is approved. The safest first implementation step is Phase 1, because it can add a read-only audit artifact without changing app behavior or generated runtime data.
