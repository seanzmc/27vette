# Confident Subset Review

Generated review evidence, not source-of-truth config. canonical_apply_ready=false.

This packet is generated review evidence, not source-of-truth config. No canonical rows were applied or generated.

## Inputs

- subset: `provided --subset`
- output: `provided --out`

## Summary

- retained_selectables: `657`
- retained_availability_rows: `3530`
- multi_model_rpo_count: `138`
- missing_coverage_count: `0`
- source_trace_sample_count: `1971`
- canonical_apply_ready=false

## Model/Section Summary

| model_key | section_family | retained_selectable_count | retained_availability_count | unique_rpo_count | multi_model_rpo_count |
| --- | --- | --- | --- | --- | --- |
| grand_sport | exterior | 79 | 474 | 79 | 61 |
| grand_sport | interior | 37 | 222 | 37 | 37 |
| grand_sport | mechanical | 27 | 162 | 27 | 25 |
| grand_sport | standard_equipment | 5 | 30 | 5 | 5 |
| stingray | exterior | 81 | 486 | 81 | 51 |
| stingray | interior | 37 | 222 | 37 | 37 |
| stingray | mechanical | 26 | 156 | 26 | 23 |
| stingray | standard_equipment | 4 | 24 | 4 | 4 |
| z06 | exterior | 80 | 480 | 80 | 62 |
| z06 | interior | 40 | 240 | 40 | 39 |
| z06 | mechanical | 25 | 150 | 25 | 22 |
| z06 | standard_equipment | 6 | 36 | 6 | 5 |

Showing 12 of 18 rows. Complete evidence is in the CSV outputs.

## Multi-Model RPOs

| rpo | model_keys | selectable_count | section_families |
| --- | --- | --- | --- |
| 36S | grand_sport\|stingray\|z06\|zr1\|zr1x | 5 | interior |
| 379 | grand_sport\|stingray\|z06\|zr1\|zr1x | 5 | interior |
| 37S | grand_sport\|stingray\|z06\|zr1\|zr1x | 5 | interior |
| 38S | grand_sport\|stingray\|z06\|zr1\|zr1x | 5 | interior |
| 3A9 | grand_sport\|stingray\|z06\|zr1\|zr1x | 5 | interior |
| 3F9 | grand_sport\|stingray\|z06\|zr1\|zr1x | 5 | interior |
| 3M9 | grand_sport\|stingray\|z06\|zr1\|zr1x | 5 | interior |
| 3N9 | grand_sport\|stingray\|z06\|zr1\|zr1x | 5 | interior |
| 5JR | grand_sport\|stingray\|z06\|zr1\|zr1x | 5 | exterior |
| 5ZC | grand_sport\|stingray\|z06\|zr1\|zr1x | 5 | exterior |
| 5ZD | grand_sport\|stingray\|z06 | 3 | exterior |
| 5ZV | grand_sport\|z06 | 2 | exterior |

Showing 12 of 138 rows. Complete evidence is in the CSV outputs.

## Coverage Gaps

coverage_gap means not_observed_in_confident_subset. It is review evidence, not an error.

| proposal_selectable_id | model_key | section_family | orderable_rpo | missing_variant_count | missing_variants_sample |
| --- | --- | --- | --- | --- | --- |

## Source Traceability

- retained source refs: `3530`
- source trace samples: `1971`
- unresolved referenced source refs: `0`

## Selectables Sample

| proposal_selectable_id | model_key | section_family | orderable_rpo | proposal_label | availability_row_count | source_ref_count |
| --- | --- | --- | --- | --- | --- | --- |
| prop_grand_sport_exterior_17a | grand_sport | exterior | 17A | Blade Silver Grand Sport Heritage Hash Marks | 6 | 6 |
| prop_grand_sport_exterior_20a | grand_sport | exterior | 20A | Admiral Blue Grand Sport Heritage Hash Marks | 6 | 6 |
| prop_grand_sport_exterior_55a | grand_sport | exterior | 55A | Competition Yellow Grand Sport Heritage Hash Marks | 6 | 6 |
| prop_grand_sport_exterior_5jr | grand_sport | exterior | 5JR | LPO, Outside mirror covers in visible Carbon Fiber, includes (DRG) Carbon Flash Metallic-painted outside mirrors, Genuine Corvette Accessory | 6 | 6 |
| prop_grand_sport_exterior_5zb | grand_sport | exterior | 5ZB | LPO, Grand Sport logo wheel center caps, Genuine Corvette Accessory | 6 | 6 |
| prop_grand_sport_exterior_5zc | grand_sport | exterior | 5ZC | LPO, Jake logo wheel center caps. Genuine Corvette Accessory | 6 | 6 |
| prop_grand_sport_exterior_5zd | grand_sport | exterior | 5ZD | LPO, Carbon Flash wheel center caps with crossed flags logo, Genuine Corvette Accessory | 6 | 6 |
| prop_grand_sport_exterior_5zv | grand_sport | exterior | 5ZV | LPO, Three-Stanchion high wing spoiler, Carbon Flash Metallic-painted, Genuine Corvette Accessory | 6 | 6 |
| prop_grand_sport_exterior_75a | grand_sport | exterior | 75A | Torch Red Grand Sport Heritage Hash Marks | 6 | 6 |
| prop_grand_sport_exterior_97a | grand_sport | exterior | 97A | Carbon Flash Grand Sport Heritage Hash Marks | 6 | 6 |
| prop_grand_sport_exterior_c2z | grand_sport | exterior | C2Z | Roof panel, visible carbon fiber with body-color surround, removable | 6 | 6 |
| prop_grand_sport_exterior_cc3 | grand_sport | exterior | CC3 | Roof panel, transparent, removable | 6 | 6 |

Showing 12 of 657 rows. Complete evidence is in the CSV outputs.

## Complete CSV review surfaces

- `confident_subset_selectables_review.csv`
- `confident_subset_availability_matrix.csv`
- `confident_subset_model_section_counts.csv`
- `confident_subset_source_trace_samples.csv`

No canonical rows were applied or generated.
