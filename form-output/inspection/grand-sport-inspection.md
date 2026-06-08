# Grand Sport Inspection

Generated: `2026-06-08T02:17:32+00:00`
Source sheet: `grandSport_options`
Status: `inspection_generated`

## Variant Validation

- Configured variants: 1lt_e07, 2lt_e07, 3lt_e07, 1lt_e67, 2lt_e67, 3lt_e67
- Found in `variant_master`: 6
- Missing from `variant_master`: none
- Inactive configured variants: 1lt_e07, 1lt_e67, 2lt_e07, 2lt_e67, 3lt_e07, 3lt_e67

## Counts

- Option rows: 273
- Unique RPOs: 230
- Variant status cells: 1638
- Candidate choice rows with available/standard status: 1422
- Candidate standard equipment cells: 455
- Candidate standard option rows: 90
- Active option rows with available/standard status: 233
- Inactive option rows all unavailable/blank: 40
- Selectable counts: `{"False": 107, "True": 166}`
- Status counts: `{"available": 903, "standard": 547, "unavailable": 188}`
- Missing status cells: 0
- Unknown status cells: 0

## Section Mapping

- Rows still missing resolved sections: 0
- Unknown section ids: none

## Blank-Section Overrides


## Rule/Detail Hot Spots

- Hot spot counts: `{"except": 2, "included_with": 19, "includes": 44, "not_available": 51, "not_recommended": 4, "only": 26, "requires": 33}`
- Rows requiring later rule review: 129

| RPO | Option | Section | Matched Terms | Special Mentions |
| --- | --- | --- | --- | --- |
| `UQH` | Bose Performance Series Audio System | `sec_2lte_001` | includes |  |
| `AQA` | Memory Driver and Passenger Convenience Package | `sec_2lte_001` | includes |  |
| `IWE` | Sueded Microfiber-Wrapped Upper Interior Trim Package | `sec_3lte_001` | includes |  |
| `J6D` | Dark Gray Metallic-Painted Calipers | `sec_cali_001` | only |  |
| `J6L` | Orange-Painted Calipers | `sec_cali_001` | requires |  |
| `D30` | Color Combination Override | `sec_colo_001` | only |  |
| `R6X` | Custom Interior Trim and Seat Combination | `sec_colo_001` | requires, only |  |
| `R8C` | Corvette Museum Delivery | `sec_cust_001` | not_available, includes, only |  |
| `PIN` | Customer VIN Ending Reservation | `sec_cust_001` | not_available, only |  |
| `BV4` | Personalized Specification Plaque | `sec_cust_001` | only |  |
| `38S` | Adrenaline Red Custom Leather Stitching | `sec_cust_002` | requires |  |
| `36S` | Competition Yellow Custom Leather Stitching | `sec_cust_002` | requires |  |
| `37S` | Santorini Blue Custom Leather Stitching | `sec_cust_002` | requires |  |
| `B6P` | Coupe Engine Appearance Package | `sec_engi_001` | includes |  |
| `ZZ3` | Convertible Engine Appearance Package | `sec_engi_001` | includes |  |
| `D3V` | Engine Lighting | `sec_engi_001` | included_with |  |
| `SL9` | Engine Specification Plaque | `sec_engi_001` | included_with |  |
| `BC7` | Black LS6 Engine Cover | `sec_engi_001` | only |  |
| `BCP` | Edge Red LS6 Engine Cover | `sec_engi_001` | includes |  |
| `BCS` | Sterling Silver LS6 Engine Cover | `sec_engi_001` | includes |  |
| `BC4` | Blue LS6 Engine Cover | `sec_engi_001` | includes |  |
| `WUB` | Quad Center Exit Exhaust | `sec_exha_001` | included_with | FEY |
| `NWI` | Bright Chrome Exhaust Tips | `sec_exha_001` | requires |  |
| `EFR` | Carbon Flash Painted Accents | `sec_exte_001` | includes |  |
| `ZYC` | Carbon Flash Mirrors and Spoiler | `sec_exte_001` | not_available, includes |  |
| `DMU` | Carbon Flash Center Stripe | `sec_gsce_001` | requires, includes, only | Z15 |
| `DMV` | Blade Silver Center Stripe | `sec_gsce_001` | requires, not_available, includes, only | Z15 |
| `DMW` | Arctic White Center Stripe | `sec_gsce_001` | requires, not_available, includes, only | Z15 |
| `DMX` | Admiral Blue Center Stripe | `sec_gsce_001` | requires, not_available, includes, only | Z15 |
| `DMY` | Red Mist Center Stripe | `sec_gsce_001` | requires, not_available, includes, only | Z15 |
| `17A` | Blade Silver Hash Marks | `sec_gsha_001` | requires, not_available | Z15 |
| `20A` | Admiral Blue Hash Marks | `sec_gsha_001` | requires, not_available | Z15 |
| `55A` | Competition Yellow Hash Marks. | `sec_gsha_001` | requires, not_available | Z15 |
| `75A` | Torch Red Hash Marks | `sec_gsha_001` | requires, not_available | Z15 |
| `97A` | Carbon Flash Hash Marks | `sec_gsha_001` | requires | Z15 |
| `DX4` | Red Mist Hash Marks | `sec_gsha_001` | requires, not_available | Z15 |
| `DRG` | Carbon Flash Outside Mirrors | `sec_incl_001` | only |  |
| `TR7` | Automatic Leveling Headlamp Control | `sec_incl_001` | only |  |
| `CFX` | Personalized Corvette Museum Plaque | `sec_incl_001` | includes, only |  |
| `XFR` | High Performance Tires | `sec_incl_001` | only |  |
| ... | 89 additional rows in JSON artifact |  |  |  |

## Warnings

- Configured Grand Sport variants are present but inactive in variant_master, preserving the live active-model generator path: 1lt_e07, 1lt_e67, 2lt_e07, 2lt_e67, 3lt_e07, 3lt_e67.
