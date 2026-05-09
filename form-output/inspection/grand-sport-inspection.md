# Grand Sport Inspection

Generated: `2026-05-09T05:30:05+00:00`
Source sheet: `grandSport_options`
Status: `inspection_generated`

## Variant Validation

- Configured variants: 1lt_e07, 2lt_e07, 3lt_e07, 1lt_e67, 2lt_e67, 3lt_e67
- Found in `variant_master`: 6
- Missing from `variant_master`: none
- Inactive configured variants: 1lt_e07, 1lt_e67, 2lt_e07, 2lt_e67, 3lt_e07, 3lt_e67

## Counts

- Option rows: 269
- Unique RPOs: 223
- Variant status cells: 1614
- Candidate choice rows with available/standard status: 1530
- Candidate standard equipment cells: 539
- Candidate standard option rows: 108
- Active option rows with available/standard status: 254
- Inactive option rows all unavailable/blank: 15
- Selectable counts: `{"False": 104, "True": 165}`
- Status counts: `{"available": 873, "standard": 545, "unavailable": 196}`
- Missing status cells: 0
- Unknown status cells: 0

## Section Mapping

- Rows still missing resolved sections: 0
- Unknown section ids: none
- Unknown category ids: none
- Section/category mismatches: 55

## Blank-Section Overrides


## Rule/Detail Hot Spots

- Hot spot counts: `{"except": 2, "included_with": 17, "includes": 41, "not_available": 47, "not_recommended": 4, "only": 19, "requires": 36}`
- Rows requiring later rule review: 123

| RPO | Option | Section | Matched Terms | Special Mentions |
| --- | --- | --- | --- | --- |
| `AQA` | Memory Driver and Passenger Convenience Package | `sec_2lte_001` | includes |  |
| `UG1` | Universal Home Remote | `sec_2lte_001` | includes |  |
| `IWE` | Sueded Microfiber-Wrapped Upper Interior Trim Package | `sec_3lte_001` | includes |  |
| `J6D` | Calipers | `sec_cali_001` | only |  |
| `J6L` | Calipers | `sec_cali_001` | requires |  |
| `D30` | Color Combination Override | `sec_colo_001` | only |  |
| `R6X` | Custom Interior Trim and Seat Combination | `sec_colo_001` | requires, only |  |
| `BV4` | Plaque | `sec_cust_001` | only |  |
| `PIN` | Customer VIN ending reservation | `sec_cust_001` | not_available, only |  |
| `R8C` | Corvette Museum Delivery | `sec_cust_001` | not_available, includes, only |  |
| `36S` | Competition Yellow custom leather stitch | `sec_cust_002` | requires, includes |  |
| `37S` | Santorini Blue custom leather stitch | `sec_cust_002` | requires, includes |  |
| `38S` | Adrenaline Red custom leather stitch | `sec_cust_002` | requires, includes |  |
| `B6P` | Coupe Engine Appearance Package | `sec_engi_001` | includes |  |
| `BC4` | NEW! Blue LS6 engine cover | `sec_engi_001` | requires, includes |  |
| `BC4` | NEW! Blue LS6 engine cover | `sec_engi_001` | includes |  |
| `BC7` | Black LS6 engine cover | `sec_engi_001` | only |  |
| `BCP` | Edge Red LS6 engine cover | `sec_engi_001` | requires, includes |  |
| `BCP` | Edge Red LS6 engine cover | `sec_engi_001` | includes |  |
| `BCS` | Sterling Silver LS6 engine cover | `sec_engi_001` | requires, includes |  |
| `BCS` | Sterling Silver LS6 engine cover | `sec_engi_001` | includes |  |
| `D3V` | Engine lighting | `sec_engi_001` | included_with |  |
| `SL9` | LPO, Engine specification plaque | `sec_engi_001` | included_with |  |
| `ZZ3` | Convertible Engine Appearance Package | `sec_engi_001` | includes |  |
| `NWI` | NEW!  Exhaust tips | `sec_exha_001` | requires |  |
| `WUB` | NEW!  Exhaust | `sec_exha_001` | included_with | FEY |
| `EFR` | Exterior accents | `sec_exte_001` | includes |  |
| `DMU` | Carbon Flash Grand Sport Heritage Center Stripe | `sec_gsce_001` | requires, includes | Z15 |
| `DMV` | Blade Silver Grand Sport Heritage Center Stripe | `sec_gsce_001` | requires, not_available, includes | Z15 |
| `DMW` | Arctic White Grand Sport Heritage Center Stripe | `sec_gsce_001` | requires, not_available, includes | Z15 |
| `DMX` | Admiral Blue Grand Sport Heritage Center Stripe | `sec_gsce_001` | requires, not_available, includes | Z15 |
| `DMY` | Red Mist Grand Sport Heritage Center Stripe | `sec_gsce_001` | requires, not_available, includes | Z15 |
| `17A` | Blade Silver Grand Sport Heritage Hash Marks | `sec_gsha_001` | requires, not_available | Z15 |
| `20A` | Admiral Blue Grand Sport Heritage Hash Marks | `sec_gsha_001` | requires, not_available | Z15 |
| `55A` | Competition Yellow Grand Sport Heritage Hash Marks | `sec_gsha_001` | requires, not_available | Z15 |
| `75A` | Torch Red Grand Sport Heritage Hash Marks | `sec_gsha_001` | requires, not_available | Z15 |
| `97A` | Carbon Flash Grand Sport Heritage Hash Marks | `sec_gsha_001` | requires | Z15 |
| `DX4` | Red Mist Grand Sport Heritage Hash Marks | `sec_gsha_001` | requires, not_available | Z15 |
| `CFX` | Plaque | `sec_incl_001` | only |  |
| `DRG` | Mirrors | `sec_incl_001` | only |  |
| ... | 83 additional rows in JSON artifact |  |  |  |

## Warnings

- Configured Grand Sport variants are present but inactive in variant_master, preserving the live Stingray-only generator path: 1lt_e07, 1lt_e67, 2lt_e07, 2lt_e67, 3lt_e07, 3lt_e67.
- Section/category mismatches: 55.
