# Grand Sport Inspection

Generated: `2026-05-11T03:29:32+00:00`
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
- Candidate choice rows with available/standard status: 1374
- Candidate standard equipment cells: 455
- Candidate standard option rows: 90
- Active option rows with available/standard status: 225
- Inactive option rows all unavailable/blank: 44
- Selectable counts: `{"False": 107, "True": 162}`
- Status counts: `{"available": 879, "standard": 547, "unavailable": 188}`
- Missing status cells: 0
- Unknown status cells: 0

## Section Mapping

- Rows still missing resolved sections: 0
- Unknown section ids: none

## Blank-Section Overrides


## Rule/Detail Hot Spots

- Hot spot counts: `{"except": 2, "included_with": 17, "includes": 53, "not_available": 49, "not_recommended": 4, "only": 19, "requires": 36}`
- Rows requiring later rule review: 129

| RPO | Option | Section | Matched Terms | Special Mentions |
| --- | --- | --- | --- | --- |
| `UQH` | Bose Performance Series Audio System | `sec_2lte_001` | includes |  |
| `UG1` | Universal Home Remote | `sec_2lte_001` | includes |  |
| `AQA` | Memory Driver and Passenger Convenience Package | `sec_2lte_001` | includes |  |
| `IWE` | Sueded Microfiber-Wrapped Upper Interior Trim Package | `sec_3lte_001` | includes |  |
| `J6D` | Dark Gray Metallic-Painted Calipers | `sec_cali_001` | only |  |
| `J6L` | Orange-Painted Calipers | `sec_cali_001` | requires |  |
| `D30` | Color Combination Override | `sec_colo_001` | only |  |
| `R6X` | Custom Interior Trim and Seat Combination | `sec_colo_001` | requires, only |  |
| `R8C` | Corvette Museum Delivery | `sec_cust_001` | not_available, includes, only |  |
| `PIN` | Customer VIN ending reservation | `sec_cust_001` | not_available, only |  |
| `BV4` | Personalized Specification Plaque | `sec_cust_001` | only |  |
| `B6P` | Coupe Engine Appearance Package | `sec_engi_001` | includes |  |
| `ZZ3` | Convertible Engine Appearance Package | `sec_engi_001` | includes |  |
| `D3V` | Engine lighting | `sec_engi_001` | included_with |  |
| `SL9` | LPO, Engine specification plaque | `sec_engi_001` | included_with |  |
| `BC7` | Black LS6 Engine Cover | `sec_engi_001` | only |  |
| `BCP` | Edge Red LS6 Engine Cover | `sec_engi_001` | includes |  |
| `BCS` | Sterling Silver LS6 Engine Cover | `sec_engi_001` | includes |  |
| `BC4` | NEW! Blue LS6 Engine Cover | `sec_engi_001` | includes |  |
| `WUB` | NEW! Quad Center Exit Exhaust | `sec_exha_001` | included_with | FEY |
| `NWI` | NEW! Exhaust tips | `sec_exha_001` | requires |  |
| `EFR` | Carbon Flash Exterior Accents | `sec_exte_001` | includes |  |
| `ZYC` | Carbon Flash Mirrors and Spoiler | `sec_exte_001` | not_available, includes |  |
| `DMU` | Carbon Flash Grand Sport Heritage Center Stripe | `sec_gsce_001` | requires, includes | Z15 |
| `DMV` | Blade Silver Grand Sport Heritage Center Stripe | `sec_gsce_001` | requires, not_available, includes | Z15 |
| `DMW` | Arctic White Grand Sport Heritage Center Stripe | `sec_gsce_001` | requires, not_available, includes | Z15 |
| `DMX` | Admiral Blue Grand Sport Heritage Center Stripe | `sec_gsce_001` | requires, not_available, includes | Z15 |
| `DMY` | Red Mist Grand Sport Heritage Center Stripe | `sec_gsce_001` | requires, not_available, includes | Z15 |
| `17A` | Blade Silver Grand Sport Heritage Hash Marks | `sec_gsha_001` | requires, not_available, includes | Z15 |
| `20A` | Admiral Blue Grand Sport Heritage Hash Marks | `sec_gsha_001` | requires, not_available, includes | Z15 |
| `55A` | Competition Yellow Grand Sport Heritage Hash Marks | `sec_gsha_001` | requires, not_available, includes | Z15 |
| `75A` | Torch Red Grand Sport Heritage Hash Marks | `sec_gsha_001` | requires, not_available, includes | Z15 |
| `97A` | Carbon Flash Grand Sport Heritage Hash Marks | `sec_gsha_001` | requires, includes | Z15 |
| `DX4` | Red Mist Grand Sport Heritage Hash Marks | `sec_gsha_001` | requires, not_available, includes | Z15 |
| `DRG` | Carbon Flash Outside Mirrors | `sec_incl_001` | only |  |
| `TR7` | Automatic Leveling Headlamp Control | `sec_incl_001` | only |  |
| `CFX` | Personalized Corvette Museum Plaque | `sec_incl_001` | includes, only |  |
| `J56` | Performance Disc Brakes | `sec_perf_brake_001` | includes, only |  |
| `XFR` | High Performance Tires | `sec_incl_001` | only |  |
| `XFS` | Michelin Pilot Sport Cup 2 R Tires | `sec_incl_001` | only | FEY |
| ... | 89 additional rows in JSON artifact |  |  |  |

## Warnings

- Configured Grand Sport variants are present but inactive in variant_master, preserving the live Stingray-only generator path: 1lt_e07, 1lt_e67, 2lt_e07, 2lt_e67, 3lt_e07, 3lt_e67.
