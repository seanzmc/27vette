# Grand Sport Inspection

Generated: `2026-04-30T19:37:20+00:00`
Source sheet: `grandSport`
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
- Candidate choice rows with available/standard status: 1418
- Candidate standard equipment cells: 545
- Candidate standard option rows: 109
- Active option rows with available/standard status: 269
- Inactive option rows all unavailable/blank: 0
- Selectable counts: `{"False": 102, "True": 167}`
- Status counts: `{"available": 873, "standard": 545, "unavailable": 196}`
- Missing status cells: 0
- Unknown status cells: 0

## Section Mapping

- Rows still missing resolved sections: 0
- Unknown section ids: none
- Unknown category ids: none
- Section/category mismatches: 55

## Blank-Section Overrides

- `PCQ` / `opt_pcq_001`: blank source section -> `sec_lpoe_001` (configured `sec_lpoe_001`, handled by config: yes)
- `PDY` / `opt_pdy_001`: blank source section -> `sec_lpoi_001` (configured `sec_lpoi_001`, handled by config: yes)
- `PEF` / `opt_pef_001`: blank source section -> `sec_lpoi_001` (configured `sec_lpoi_001`, handled by config: yes)

## Rule/Detail Hot Spots

- Hot spot counts: `{"except": 2, "included_with": 17, "includes": 41, "not_available": 47, "not_recommended": 4, "only": 19, "requires": 36}`
- Rows requiring later rule review: 123

| RPO | Option | Section | Matched Terms | Special Mentions |
| --- | --- | --- | --- | --- |
| `379` | Seat belt color | `sec_seat_001` | included_with, not_recommended | EL9 |
| `719` | Seat belt color | `sec_seat_001` |  | EL9 |
| `719` | Seat belt color | `sec_stan_002` |  | EL9 |
| `17A` | Blade Silver Grand Sport Heritage Hash Marks | `sec_gsha_001` | requires, not_available | Z15 |
| `20A` | Admiral Blue Grand Sport Heritage Hash Marks | `sec_gsha_001` | requires, not_available | Z15 |
| `36S` | Competition Yellow custom leather stitch | `sec_cust_002` | requires, includes |  |
| `37S` | Santorini Blue custom leather stitch | `sec_cust_002` | requires, includes |  |
| `38S` | Adrenaline Red custom leather stitch | `sec_cust_002` | requires, includes |  |
| `3A9` | Seat belt color | `sec_seat_001` | included_with, not_recommended |  |
| `3F9` | Seat belt color | `sec_seat_001` | included_with, not_recommended | EL9, Z25 |
| `3M9` | Seat belt color | `sec_seat_001` | not_recommended | EL9 |
| `3N9` | Seat belt color | `sec_seat_001` | included_with |  |
| `55A` | Competition Yellow Grand Sport Heritage Hash Marks | `sec_gsha_001` | requires, not_available | Z15 |
| `5JR` | LPO, Outside mirror covers in visible Carbon Fiber | `sec_lpoe_001` | includes |  |
| `5ZV` | LPO, Three-Stanchion high wing spoiler | `sec_spoi_001` | not_available | FEY |
| `75A` | Torch Red Grand Sport Heritage Hash Marks | `sec_gsha_001` | requires, not_available | Z15 |
| `97A` | Carbon Flash Grand Sport Heritage Hash Marks | `sec_gsha_001` | requires | Z15 |
| `AQA` | Memory Driver and Passenger Convenience Package | `sec_2lte_001` | includes |  |
| `AUP` | Seats | `sec_seat_002` | requires |  |
| `B6P` | Coupe Engine Appearance Package | `sec_engi_001` | includes |  |
| `BC4` | NEW! Blue LS6 engine cover | `sec_engi_001` | requires, includes |  |
| `BC4` | NEW! Blue LS6 engine cover | `sec_engi_001` | includes |  |
| `BC7` | Black LS6 engine cover | `sec_engi_001` | only |  |
| `BCP` | Edge Red LS6 engine cover | `sec_engi_001` | requires, includes |  |
| `BCP` | Edge Red LS6 engine cover | `sec_engi_001` | includes |  |
| `BCS` | Sterling Silver LS6 engine cover | `sec_engi_001` | requires, includes |  |
| `BCS` | Sterling Silver LS6 engine cover | `sec_engi_001` | includes |  |
| `BV4` | Plaque | `sec_cust_001` | only |  |
| `CAV` | LPO, Contoured cargo area liners with Jake logo | `sec_lpoi_001` | included_with |  |
| `CF8` | Roof panel | `sec_roof_001` | not_available |  |
| `CFL` | NEW!  Ground effects | `sec_perf_001` | not_available |  |
| `CFV` | Ground effects | `sec_perf_001` | not_available |  |
| `CFX` | Plaque | `sec_incl_001` | only |  |
| `CFZ` | Ground effects | `sec_perf_001` | included_with |  |
| `CM9` | Convertible top | `sec_roof_001` | includes, only |  |
| `CM9` | Convertible top | `sec_stan_002` | includes, only |  |
| `D30` | Color Combination Override | `sec_colo_001` | only |  |
| `D3V` | Engine lighting | `sec_engi_001` | included_with |  |
| `D84` | Convertible top | `sec_roof_001` | not_available |  |
| `D86` | Convertible top | `sec_roof_001` | not_available |  |
| ... | 83 additional rows in JSON artifact |  |  |  |

## Warnings

- Configured Grand Sport variants are present but inactive in variant_master, preserving the live Stingray-only generator path: 1lt_e07, 1lt_e67, 2lt_e07, 2lt_e67, 3lt_e07, 3lt_e67.
- Section/category mismatches: 55.
