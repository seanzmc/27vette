# Z Option/OVS Closure Phase 2B Decision Matrix

CSV: `/Users/seandm/Projects/27vette/.hermes/plans/z-option-ovs-closure-phase-2b-decision-matrix.csv`

This matrix is read-only analysis for workbook decision review. It does not write `stingray_master.xlsx`.

## Totals

- total rows classified: 196
- missing review joins: 0
- by risk: {'high': 75, 'low': 70, 'medium': 51}
- by action: {'defer_exterior_paint_or_color': 1, 'defer_interior_structure': 39, 'defer_rules_or_pricing_evidence': 65, 'exclude_informational_standard_duplicate': 70, 'needs_human_decision': 21}

## By model/action

| model | action | rows |
|---|---|---:|
| z06 | `defer_exterior_paint_or_color` | 1 |
| z06 | `defer_interior_structure` | 13 |
| z06 | `defer_rules_or_pricing_evidence` | 32 |
| z06 | `exclude_informational_standard_duplicate` | 24 |
| z06 | `needs_human_decision` | 5 |
| zr1 | `defer_interior_structure` | 13 |
| zr1 | `defer_rules_or_pricing_evidence` | 16 |
| zr1 | `exclude_informational_standard_duplicate` | 23 |
| zr1 | `needs_human_decision` | 8 |
| zr1x | `defer_interior_structure` | 13 |
| zr1x | `defer_rules_or_pricing_evidence` | 17 |
| zr1x | `exclude_informational_standard_duplicate` | 23 |
| zr1x | `needs_human_decision` | 8 |

## Recommended review sequence

1. Start with `exclude_informational_standard_duplicate` low-risk rows. These are mostly no-RPO standard/tech/safety/included disclosures that appear inappropriate as normalized option rows.
2. Review `defer_interior_structure` rows with the interiors pass in mind; custom stitch/interior rows should not be approved by option closure alone.
3. Review `defer_rules_or_pricing_evidence` rows against Z-specific rule/pricing evidence; this includes wheels, suspension, performance package, brake, aero, engine/ground-effects, and related RPOs.
4. Review remaining `needs_human_decision` rows manually before any workbook write.

## High-risk sample rows

| model | option_id | rpo | section | action | description |
|---|---|---|---|---|---|
| z06 | `opt_36s_001` | `36S` | `sec_cust_002` | `defer_interior_structure` | Competition Yellow custom leather stitch, includes seats, instrument panel, doors and console |
| z06 | `opt_37s_001` | `37S` | `sec_cust_002` | `defer_interior_structure` | Santorini Blue custom leather stitch, includes seats, instrument panel, doors and console |
| z06 | `opt_38s_001` | `38S` | `sec_cust_002` | `defer_interior_structure` | Adrenaline Red custom leather stitch, includes seats, instrument panel, doors and console |
| z06 | `opt_5dh_001` | `5DH` | `sec_lpow_001` | `defer_rules_or_pricing_evidence` | LPO, 20" x 10" (50.8 cm x 25.4 cm) front and 21" x 13" (53.3 cm x 33 cm) rear Spider design, Sa |
| z06 | `opt_5dk_001` | `5DK` | `sec_lpow_001` | `defer_rules_or_pricing_evidence` | LPO, 20" x 10" (50.8 cm x 25.4 cm) front and 21" x 13" (53.3 cm x 33 cm) rear Spider design, Te |
| z06 | `opt_5v5_001` | `5V5` | `sec_perf_aero_001` | `defer_rules_or_pricing_evidence` | LPO, Spoiler, Visible Carbon Fiber, Genuine Corvette Accessory |
| z06 | `opt_bcw_001` | `BCW` | `sec_engi_001` | `defer_rules_or_pricing_evidence` | Engine intake, Red |
| z06 | `opt_cfv_002` | `CFV` | `sec_perf_ground_001` | `defer_rules_or_pricing_evidence` | Ground effects, visible carbon fiber |
| z06 | `opt_efy_001` | `EFY` | `sec_exte_001` | `defer_exterior_paint_or_color` | Exterior accents, body-color, side vents, rockers, splitter and front/rear grille accents |
| z06 | `opt_fe6_002` | `FE6` | `sec_susp_001` | `defer_rules_or_pricing_evidence` | Suspension, performance with Magnetic Selective Ride Control |
| z06 | `opt_fe7_001` | `FE7` | `sec_susp_001` | `defer_rules_or_pricing_evidence` | Suspension, Z07 with Magnetic Selective Ride Control |
| z06 | `opt_lt6_002` | `LT6` | `sec_stan_001` | `defer_rules_or_pricing_evidence` | Engine, 5.5L V8 DI, high-output, Variable Valve Timing (VVT), (670 hp [499.6 kW] @ 8400 rpm, 46 |
| z06 | `opt_m1m_002` | `M1M` | `sec_stan_001` | `defer_rules_or_pricing_evidence` | Transmission, 8-speed dual clutch, includes manual and auto modes |
| z06 | `opt_pcz_001` | `PCZ` | `sec_lpoe_001` | `defer_rules_or_pricing_evidence` | LPO, Tech Bronze Accent Package, includes (5DK) 20" front/21" rear Spider design, Tech Bronze f |
| z06 | `opt_pda_001` | `PDA` | `sec_stri_001` | `defer_rules_or_pricing_evidence` | LPO, Jake C8.R Graphics Package, includes (SNE) Jake hood graphic, LPO and (VPW) Jake C8.R rear |
| z06 | `opt_pdb_001` | `PDB` | `sec_perf_z52_001` | `defer_rules_or_pricing_evidence` | Carbon Fiber Wheel and Brake Package, includes (J57) carbon ceramic brakes with (J6D) Dark Gray |
| z06 | `opt_pdd_001` | `PDD` | `sec_perf_z52_001` | `defer_rules_or_pricing_evidence` | Z07 Carbon Flash Aero and Wheel Package, includes (Z07) Z07 Performance Package, (T0F) Carbon F |
| z06 | `opt_pdf_001` | `PDF` | `sec_perf_z52_001` | `defer_rules_or_pricing_evidence` | Z07 Visible Carbon Aero and Wheel Package, includes (Z07) Z07 Performance Package, (T0G) Visibl |
| z06 | `opt_rou_001` | `ROU` | `sec_whee_002` | `defer_rules_or_pricing_evidence` | Wheels, 20" x 10" (50.8 cm x 25.4 cm) front and 21" x 13" (53.3 cm x 33 cm) rear Pearl Nickel f |
| z06 | `opt_rox_001` | `ROX` | `sec_whee_002` | `defer_rules_or_pricing_evidence` | Wheels, 20" x 10" (50.8 cm x 25.4 cm) front and 21" x 13" (53.3 cm x 33 cm) rear Carbon Flash w |
| z06 | `opt_rxi_001` | `RXI` | `sec_engi_001` | `defer_rules_or_pricing_evidence` | LPO, LT6 engine cover in visible carbon fiber, Genuine Corvette Accessory |
| z06 | `opt_ryq_001` | `RYQ` | `sec_lpoe_001` | `defer_rules_or_pricing_evidence` | LPO, Visible Carbon Fiber door intake trim, Genuine Corvette Accessory |
| z06 | `opt_sg1_001` | `SG1` | `sec_lpoe_001` | `defer_rules_or_pricing_evidence` | LPO, Z06 badges in Edge Red, Genuine Corvette Accessory |
| z06 | `opt_sne_001` | `SNE` | `sec_stri_001` | `defer_rules_or_pricing_evidence` | LPO, Jake hood graphic |
| z06 | `opt_soa_001` | `SOA` | `sec_whee_002` | `defer_rules_or_pricing_evidence` | Wheels, 20" x 10" (50.8 cm x 25.4 cm) front and 21" x 13" (53.3 cm x 33 cm) rear Spider design, |
| z06 | `opt_soe_002` | `SOE` | `sec_whee_002` | `defer_rules_or_pricing_evidence` | Wheels, 20" x 10" (50.8 cm x 25.4 cm) front and 21" x 13" (53.3 cm x 33 cm) rear Spider design, |
| z06 | `opt_som_001` | `SOM` | `sec_whee_002` | `defer_rules_or_pricing_evidence` | Wheels, 20" x 10" (50.8 cm x 25.4 cm) front and 21" x 13" (53.3 cm x 33 cm) rear bright polishe |
| z06 | `opt_son_001` | `SON` | `sec_whee_002` | `defer_rules_or_pricing_evidence` | Wheels, 20" x 10" (50.8 cm x 25.4 cm) front and 21" x 13" (53.3 cm x 33 cm) rear Gloss Black fo |
| z06 | `opt_srk_001` | `SRK` | `sec_whee_002` | `defer_rules_or_pricing_evidence` | Wheels, 20" x 10" (50.8 cm x 25.4 cm) front and 21" x 13" (53.3 cm x 33 cm) rear 10-spoke, Pear |
| z06 | `opt_srn_001` | `SRN` | `sec_whee_002` | `defer_rules_or_pricing_evidence` | Wheels, 20" x 10" (50.8 cm x 25.4 cm) front and 21" x 13" (53.3 cm x 33 cm) rear 10-spoke, Glos |

## Low-risk exclusion candidates

70 rows are currently classified as low-risk informational/standard duplicates. They are proposed to remain non-emitting (`review_status=deferred`, `active=False`) with explicit exclusion notes, not approved.

- z06: 24 rows
- zr1: 23 rows
- zr1x: 23 rows

## Pause point

Review the CSV before workbook writes. Per spec, Phase 2B should not edit `future_model_option_review` until these recommendations are approved or corrected.
