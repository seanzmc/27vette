# Grand Sport Cleanup Audit

Generated: `2026-04-30T17:58:48.725Z`
Status: `read_only_audit`
Source: active `window.CORVETTE_FORM_DATA.models.grandSport.data` in `form-app/data.js`

## Preservation Boundary

- No runtime behavior changes are part of this artifact.
- No rules, price rules, interiors, label cleanup, display-order changes, section-placement changes, or UI changes are implemented here.
- Raw `source_detail_raw` values are preserved in the JSON artifact.
- Stingray remains the default model in the active registry.

## Counts

| Surface | Grand Sport | Stingray |
| --- | --- | --- |
| Variants | 6 | 6 |
| Steps | 14 | 14 |
| Sections | 34 | 39 |
| Choices | 1614 | 1548 |
| Active choice rows | 1418 | 1362 |
| Unique active options | 269 | 257 |
| Rules | 0 | 238 |
| Price rules | 0 | 43 |
| Exclusive groups | 0 | 6 |
| Rule groups | 0 | 2 |
| Interiors | 0 | 130 |

## Top Findings

- Grand Sport active registry has 269 unique active option rows across 1418 active choice rows.
- Grand Sport has 0 rules, 0 price rules, 0 exclusive groups, 0 rule groups, and 0 interiors.
- Base Interior has no Grand Sport section choices in the active runtime data.
- 237 unique active options have text-cleanup review candidates by conservative heuristics.
- 4 shared RPO rows have Grand Sport price sets that differ from Stingray.
- 123 rule/detail hot spot rows are preserved from draft metadata.

## Browser Smoke Notes

- Grand Sport model switch renders the Grand Sport title and model context.
- Base Interior step shows 0 choices and prompts to select a seat first.
- Selecting FEY adds FEY only; included/required components are not auto-added.
- Selecting Z15 adds Z15 only; hash-mark requirement is not enforced or auto-added.
- Open requirements still include Base Interior after FEY/Z15 selections.

## Section / Step Placement

| Step | Section | Selection | Choices |
| --- | --- | --- | --- |
| body_style | sec_context_body_style / Body Style | single_select_req | 0 |
| trim_level | sec_context_trim_level / Trim Level | single_select_req | 0 |
| paint | sec_pain_001 / Paint | single_select_req | 10 |
| exterior_appearance | sec_engi_001 / Engine Appearance | multi_select_opt | 14 |
| exterior_appearance | sec_roof_001 / Roof | single_select_req | 7 |
| exterior_appearance | sec_gsce_001 / Grand Sport Center Stripes | single_select_opt | 5 |
| exterior_appearance | sec_gsha_001 / Grand Sport Heritage Hash Marks | single_select_opt | 6 |
| exterior_appearance | sec_exte_001 / Exterior Accents | single_select_req | 2 |
| exterior_appearance | sec_badg_001 / Badges | single_select_req | 2 |
| wheels | sec_whee_002 / Wheels | single_select_req | 7 |
| wheels | sec_cali_001 / Caliper Color | single_select_req | 7 |
| wheels | sec_whee_001 / Wheel Accessory | multi_select_opt | 7 |
| packages_performance | sec_perf_001 / Performance | multi_select_opt | 9 |
| packages_performance | sec_spec_001 / Special Edition | single_select_opt | 1 |
| aero_exhaust_stripes_accessories | sec_exha_001 / Exhaust | multi_select_opt | 3 |
| aero_exhaust_stripes_accessories | sec_stri_001 / Stripes | single_select_opt | 19 |
| aero_exhaust_stripes_accessories | sec_spoi_001 / Spoiler | single_select_opt | 2 |
| aero_exhaust_stripes_accessories | sec_lpoe_001 / LPO Exterior | multi_select_opt | 18 |
| seat | sec_seat_002 / Seats | single_select_req | 8 |
| seat_belt | sec_seat_001 / Seat Belt | single_select_req | 6 |
| interior_trim | sec_inte_001 / Interior Trim | multi_select_opt | 5 |
| interior_trim | sec_lpoi_001 / LPO Interior | multi_select_opt | 15 |
| interior_trim | sec_colo_001 / Color Combination Override | multi_select_opt | 2 |
| interior_trim | sec_cust_002 / Custom Stitch | single_select_opt | 3 |
| interior_trim | sec_onst_001 / OnStar | single_select_opt | 11 |
| delivery | sec_cust_001 / Custom Delivery | multi_select_opt | 3 |
| standard_equipment | sec_1lte_001 / 1LT Equipment | display_only | 5 |
| standard_equipment | sec_incl_001 / Included | display_only | 7 |
| standard_equipment | sec_stan_002 / Standard Options | display_only | 11 |
| standard_equipment | sec_2lte_001 / 2LT Equipment | display_only | 21 |
| standard_equipment | sec_stan_001 / Standard Equipment | display_only | 34 |
| standard_equipment | sec_3lte_001 / 3LT Equipment | display_only | 3 |
| standard_equipment | sec_safe_001 / Safety Features | display_only | 13 |
| standard_equipment | sec_tech_001 / Technology | display_only | 3 |

## Price Differences Versus Stingray

| RPO | Grand Sport | GS Prices | Stingray Prices | Section |
| --- | --- | --- | --- | --- |
| BC4 | New Blue LS6 engine cover | 595 | 695 | Engine Appearance |
| BCP | Edge Red LS6 engine cover | 595 | 695 | Engine Appearance |
| BCS | Sterling Silver LS6 engine cover | 595 | 695 | Engine Appearance |
| VWE | LPO, Front radiator grille screens | 950 | 695 | LPO Exterior |

## Text Cleanup Candidate Summary

Candidates: `237` unique active options. Full table is in the JSON artifact at `text_cleanup_candidates`.

| RPO | Label | Reasons | Section |
| --- | --- | --- | --- |
| CFL | New Ground Effects | new_prefix_review, description_starts_lowercase, generic_label | Performance |
| NWI | New Exhaust tips | new_prefix_review, description_starts_lowercase, generic_label | Exhaust |
| opt_009 | OnStar Basics (OnStar Fleet Basics for Fleet) Drive with confidence and convenience using core OnStar services | description_starts_lowercase, long_label, long_description | OnStar |
| PRB | 3 Years OnStar One (Standalone) Elevate your everyday drives with OnStar One. Have peace of mind with 24/7 access to Emergency Advisors and Stolen Vehicle Assistance. Plus | description_starts_lowercase, long_label, long_description | OnStar |
| U2K | SiriusXM with 360L Trial Subscription. SiriusXM with 360L transforms your customers' ride with our most extensive and personalized radio experience on the road. | label_trailing_period, missing_description, long_label | OnStar |
| V8X | LPO, Visible Carbon Fiber sill plates Genuine Corvette Accessory | lpo_prefix_review, missing_description, accessory_phrase_in_label | LPO Interior |
| WUB | New Exhaust | new_prefix_review, description_starts_lowercase, generic_label | Exhaust |
| 5JR | LPO, Outside mirror covers in visible Carbon Fiber | lpo_prefix_review, description_starts_lowercase | LPO Exterior |
| 5ZC | LPO, Jake logo wheel center caps. | lpo_prefix_review, label_trailing_period | Wheel Accessory |
| AUP | Seats | description_starts_lowercase, generic_label | Seats |
| BV4 | Plaque | description_starts_lowercase, generic_label | Custom Delivery |
| C2Z | Roof panel | description_starts_lowercase, generic_label | Roof |
| CC3 | Roof panel | description_starts_lowercase, generic_label | Roof |
| CF7 | Roof panel | description_starts_lowercase, generic_label | Roof |
| CF7 | Roof panel | description_starts_lowercase, generic_label | Standard Options |
| CF8 | Roof panel | description_starts_lowercase, generic_label | Roof |
| CFV | Ground effects | description_starts_lowercase, generic_label | Performance |
| CFX | Plaque | description_starts_lowercase, generic_label | Included |
| CFZ | Ground effects | description_starts_lowercase, generic_label | Performance |
| CM9 | Convertible top | description_starts_lowercase, generic_label | Roof |
| CM9 | Convertible top | description_starts_lowercase, generic_label | Standard Options |
| DRG | Mirrors | description_starts_lowercase, generic_label | Included |
| DUE | New Asymmetrical Santorini Blue/Carbon Flash Full Length Dual Racing Stripes | new_prefix_review, missing_description | Stripes |
| DWK | Mirrors | description_starts_lowercase, generic_label | 1LT Equipment |
| DYX | Mirrors | description_starts_lowercase, generic_label | 2LT Equipment |
| FEY | Z52 Track Performance Package | description_starts_lowercase, long_description | Performance |
| KI3 | Steering wheel | description_starts_lowercase, generic_label | 2LT Equipment |
| KQV | Seats | description_starts_lowercase, generic_label | 2LT Equipment |
| N26 | Steering wheel | description_starts_lowercase, generic_label | Interior Trim |
| NK4 | Steering wheel | description_starts_lowercase, generic_label | Standard Options |
| NPP | Exhaust | description_starts_lowercase, generic_label | Standard Equipment |
| opt_020 | New Intersection Automatic Emergency Braking | new_prefix_review, missing_description | Safety Features |
| PCQ | LPO, Grille Screen Protection Package | lpo_prefix_review, description_starts_lowercase | LPO Exterior |
| PDY | LPO, Roadside Safety Package | lpo_prefix_review, description_starts_lowercase | LPO Interior |
| PEF | LPO, Contoured Liner Protection Package | lpo_prefix_review, description_starts_lowercase | LPO Interior |
| R88 | LPO, Illuminated crossed flags emblem | lpo_prefix_review, description_starts_lowercase | LPO Exterior |
| R9V | Mobile Service Plus. MobileService+ is a suite of service conveniences for 3 years - Mobile Service | long_label, long_description | OnStar |
| R9W | Deleted Mobile Service Plus. Delete MobileService+ service conveniences - Mobile Service | long_label, long_description | OnStar |
| R9Y | Mobile Service Plus. MobileService+ is a suite of service conveniences for 1 year - Mobile Service | long_label, long_description | OnStar |
| RWU | LPO, Cargo area organizer | lpo_prefix_review, description_starts_lowercase | LPO Interior |

## Rule Hot Spot Summary

Rows: `123`

| Bucket | Count |
| --- | --- |
| except | 2 |
| included_with | 17 |
| includes | 41 |
| not_available | 47 |
| not_recommended | 4 |
| only | 19 |
| requires | 36 |
| special_package_review | 26 |

## Recommended Phase 2 Scope

- Implement Grand Sport interior contract first so Base Interior is no longer an empty runtime step.
- Keep EL9/Z25 handling model-scoped and preserve Stingray EL9 inactivity.
- Add focused tests for Grand Sport interior availability before adding broad rules or price rules.
- Do not clean labels/descriptions or reorder sections until the interior contract is stable.

## Artifact Contents

The JSON artifact includes:

- `unique_active_options` by RPO/option ID, including raw source fields and `source_detail_raw_values`.
- `section_step_placement` table.
- `text_cleanup_candidates` table.
- `price_differences_vs_stingray` table.
- `rule_hot_spots` from `draftMetadata.ruleDetailHotSpots`.
- `browser_smoke_notes`.
