# RPO Role-Overlap Review

Do not edit this generated review packet as source of truth. Transfer approved decisions into data/import_maps/corvette_2027/*.csv.

This review packet is generated evidence only. It does not update staging CSVs, import maps, or canonical CSVs.

## Readiness Snapshot

- primary_variant_matrix_ready: `true`
- color_trim_ready: `false`
- pricing_ready: `true`
- equipment_groups_ready: `true`
- rpo_role_overlaps_ready: `false`
- canonical_proposal_ready: `false`
- color_trim_review_status_counts: `{"needs_review": 6}`
- resolved_overlap_count: `0`
- mapped_overlap_count: `10`
- observed_overlap_count: `10`

## Decision Options

- `approved`: explicitly reviewed and eligible for later proposal handling.
- `accepted_expected_overlap`: explicitly accepted as expected orderable/ref-only overlap.
- `deferred`: known not ready yet.
- `needs_review`: unresolved.

## Review Rows

| rpo | orderable_count | ref_only_count | source_sheets | model_keys | section_families | sample_descriptions | current_review_status | current_canonical_handling |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| AH2 | 18 | 8 | Interior 1\|Interior 2\|Interior 3\|Interior 4 | grand_sport\|stingray\|z06\|zr1\|zr1x | interior | Seats, GT2 bucket | accepted_expected_overlap | keep_separate_evidence |
| B6P | 18 | 16 | Mechanical 1\|Mechanical 2\|Mechanical 3\|Mechanical 4\|Standard Equipment 4 | grand_sport\|stingray\|z06\|zr1\|zr1x | mechanical\|standard_equipment | Coupe Engine Appearance Package, includes carbon fiber trim and (SL9) engine specification plaque, LPO \| Coupe Engine Appearance Package, includes carbon fiber trim, (D3V) engine lighting and (SL9) engine specification plaque, LPO | accepted_expected_overlap | keep_separate_evidence |
| C2Z | 36 | 16 | Exterior 1\|Exterior 2\|Exterior 3\|Exterior 4\|Standard Equipment 1\|Standard Equipment 2\|Standard Equipment 3\|Standard Equipment 4 | grand_sport\|stingray\|z06\|zr1\|zr1x | exterior\|standard_equipment | Roof panel, visible carbon fiber with body-color surround, removable | accepted_expected_overlap | keep_separate_evidence |
| CFV | 24 | 16 | Exterior 2\|Exterior 3\|Exterior 4\|Standard Equipment 2\|Standard Equipment 3\|Standard Equipment 4 | grand_sport\|z06\|zr1\|zr1x | exterior\|standard_equipment | Ground effects, visible carbon fiber \| Ground effects, visible carbon fiber 1. Included with (T0G) Visible Carbon Fiber Aero Package. \| Ground effects, visible carbon fiber 1. Not available at this time. | accepted_expected_overlap | keep_separate_evidence |
| D3V | 36 | 16 | Mechanical 1\|Mechanical 2\|Mechanical 3\|Mechanical 4\|Standard Equipment 1\|Standard Equipment 2\|Standard Equipment 3\|Standard Equipment 4 | grand_sport\|stingray\|z06\|zr1\|zr1x | mechanical\|standard_equipment | Engine lighting \| Engine lighting 1. Included with (B6P) Coupe Engine Appearance Package or (BC4/BCP/BCS) LS6 engine covers. \| Engine lighting 1. Included with (B6P) Coupe Engine Appearance Package or (BCW) Red engine intake. | accepted_expected_overlap | keep_separate_evidence |
| DY0 | 12 | 16 | Interior 3\|Interior 4\|Standard Equipment 3\|Standard Equipment 4 | z06\|zr1\|zr1x | interior\|standard_equipment | Display hood, Carbon Fiber, located above the Driver Information Center display | accepted_expected_overlap | keep_separate_evidence |
| SL9 | 36 | 16 | Mechanical 1\|Mechanical 2\|Mechanical 3\|Mechanical 4\|Standard Equipment 1\|Standard Equipment 2\|Standard Equipment 3\|Standard Equipment 4 | grand_sport\|stingray\|z06\|zr1\|zr1x | mechanical\|standard_equipment | LPO, Engine specification plaque, Genuine Corvette Accessory 1. Included with (B6P/ZZ3) Engine Appearance Package. | accepted_expected_overlap | keep_separate_evidence |
| UQT | 36 | 16 | Interior 1\|Interior 2\|Interior 3\|Interior 4\|Standard Equipment 1\|Standard Equipment 2\|Standard Equipment 3\|Standard Equipment 4 | grand_sport\|stingray\|z06\|zr1\|zr1x | interior\|standard_equipment | Performance data and video recorder | accepted_expected_overlap | keep_separate_evidence |
| WUB | 24 | 28 | Mechanical 1\|Mechanical 2\|Mechanical 3\|Mechanical 4\|Standard Equipment 1\|Standard Equipment 2\|Standard Equipment 3\|Standard Equipment 4 | grand_sport\|stingray\|z06\|zr1\|zr1x | mechanical\|standard_equipment | NEW!  Exhaust, quad center exit \| NEW!  Exhaust, quad center exit 1. Included with (FEY) Z52 Track Performance Package. | accepted_expected_overlap | keep_separate_evidence |
| ZZ3 | 24 | 16 | Mechanical 1\|Mechanical 2\|Mechanical 3\|Mechanical 4\|Standard Equipment 3\|Standard Equipment 4 | grand_sport\|stingray\|z06\|zr1\|zr1x | mechanical\|standard_equipment | Convertible Engine Appearance Package, includes window under tonneau cover, (BC7) Black LS6 engine cover and (SL9) engine specification plaque, LPO \| Convertible Engine Appearance Package, includes window under tonneau cover, engine intake and (SL9) engine specification plaque, LPO | accepted_expected_overlap | keep_separate_evidence |

The CSV is the complete review surface.
