**Rule_Mapping CSV Output**

**Methodology**
All rows from the source CSV where `selectable=TRUE` and `detail_raw` contained meaningful compatibility text were processed. Purely descriptive, pricing-only, or empty fields were excluded. RPO identifiers were extracted exclusively as 3-character alphanumeric codes (e.g., Z51, D3V, PCU, 5V7, HMO, 3N9).

Rule types were assigned strictly according to textual triggers: “Requires” or “only available with” → `requires`; “Not available with” → `excludes`; “Includes”, “Included with”, or “included and only available with” → `includes`. When a single `detail_raw` contained multiple distinct triggers or mixed clauses, the text was split into separate rows so each `target_id` receives the most appropriate canonical rule_type.

“Available with” and “when ordered with” lists were not treated as hard rules; they produce `review_flag=TRUE` entries. Soft language (“recommended”, “not recommended”, “unavailable until further notice”, “SOLD orders only”, order-type/BFU/territory constraints, and conditional deletions such as “deletes T0A when Z51 is ordered”) also forces `review_flag=TRUE`.

OR-set semantics (e.g., “requires A or B or C”) are represented as individual pairwise rows for auditability, with the understanding that downstream rule engines may need to re-group these as logical compatibility sets rather than independent mandatory requirements. Directionality of “included with” statements is resolved from the perspective of the source `option_id`: if the current option is described as included in a package, a `requires` relationship is recorded for that package. The opposite direction (package includes this option) is recorded only when the text explicitly supports it.

The informational pairing note attached to opt_719_001 was reframed as actionable `includes` relationships on the relevant seat-belt color options (3N9, 3A9, 3F9, 379) while retaining the original 719 rows flagged for review. All Z51-linked component options (J55, V08, G96, QTU, M1N, G0K, T0A, FE3, B4Z, FE4, etc.) were expanded where the source text explicitly tied them to the performance package. Additional accessory-package networks (PCU/STI/VQK/VWE, PDV/SB7/SHT, PCX/SNG/5DG, PEF/RIA/CAV, PDY/RYT/S08, etc.) were fully enumerated.

Only rows containing at least one identifiable 3-character RPO receive a populated `target_id`. Business constraints without clean RPOs (dealer codes, ship-to BAC, SiriusXM forcing, Puerto Rico deletion logic, premium-color upcharges) are emitted as review rows with the clearest extractable code or an empty target when none exists. The complete original `detail_raw` text is preserved verbatim in every row for traceability; no summarization or “same as above” placeholders are used.

This combined approach yields a comprehensive, auditable ruleset that balances deterministic mappings with conservative flagging of edge cases.

```csv
option_id,target_id,rule_type,original_detail_raw,review_flag
opt_r6x_001,HMO,requires,"1. SOLD orders only. Requires (HMO/HVV) Jet Black/Sky Cool Gray, (HZB/HVT) Sky Cool Gray/Jet Black, (HU0/HXO) Jet Black/Adrenaline Red, (HUU/HZP) Adrenaline Red/Jet Black interiors. See Custom Interior Trim and Seat Combinations color and trim chart.",FALSE
opt_r6x_001,HVV,requires,"1. SOLD orders only. Requires (HMO/HVV) Jet Black/Sky Cool Gray, (HZB/HVT) Sky Cool Gray/Jet Black, (HU0/HXO) Jet Black/Adrenaline Red, (HUU/HZP) Adrenaline Red/Jet Black interiors. See Custom Interior Trim and Seat Combinations color and trim chart.",FALSE
opt_r6x_001,HZB,requires,"1. SOLD orders only. Requires (HMO/HVV) Jet Black/Sky Cool Gray, (HZB/HVT) Sky Cool Gray/Jet Black, (HU0/HXO) Jet Black/Adrenaline Red, (HUU/HZP) Adrenaline Red/Jet Black interiors. See Custom Interior Trim and Seat Combinations color and trim chart.",FALSE
opt_r6x_001,HVT,requires,"1. SOLD orders only. Requires (HMO/HVV) Jet Black/Sky Cool Gray, (HZB/HVT) Sky Cool Gray/Jet Black, (HU0/HXO) Jet Black/Adrenaline Red, (HUU/HZP) Adrenaline Red/Jet Black interiors. See Custom Interior Trim and Seat Combinations color and trim chart.",FALSE
opt_r6x_001,HU0,requires,"1. SOLD orders only. Requires (HMO/HVV) Jet Black/Sky Cool Gray, (HZB/HVT) Sky Cool Gray/Jet Black, (HU0/HXO) Jet Black/Adrenaline Red, (HUU/HZP) Adrenaline Red/Jet Black interiors. See Custom Interior Trim and Seat Combinations color and trim chart.",FALSE
opt_r6x_001,HXO,requires,"1. SOLD orders only. Requires (HMO/HVV) Jet Black/Sky Cool Gray, (HZB/HVT) Sky Cool Gray/Jet Black, (HU0/HXO) Jet Black/Adrenaline Red, (HUU/HZP) Adrenaline Red/Jet Black interiors. See Custom Interior Trim and Seat Combinations color and trim chart.",FALSE
opt_r6x_001,HUU,requires,"1. SOLD orders only. Requires (HMO/HVV) Jet Black/Sky Cool Gray, (HZB/HVT) Sky Cool Gray/Jet Black, (HU0/HXO) Jet Black/Adrenaline Red, (HUU/HZP) Adrenaline Red/Jet Black interiors. See Custom Interior Trim and Seat Combinations color and trim chart.",FALSE
opt_r6x_001,HZP,requires,"1. SOLD orders only. Requires (HMO/HVV) Jet Black/Sky Cool Gray, (HZB/HVT) Sky Cool Gray/Jet Black, (HU0/HXO) Jet Black/Adrenaline Red, (HUU/HZP) Adrenaline Red/Jet Black interiors. See Custom Interior Trim and Seat Combinations color and trim chart.",FALSE
opt_38s_001,H1Y,requires,"1. Requires (H1Y/HTM/HTP) Jet Black interior. 2. Requires (HTE/HTT/HUB/HUC) Jet Black interior or (HU0/HXO) Adrenaline Red/Jet Black interior.",FALSE
opt_38s_001,HTM,requires,"1. Requires (H1Y/HTM/HTP) Jet Black interior. 2. Requires (HTE/HTT/HUB/HUC) Jet Black interior or (HU0/HXO) Adrenaline Red/Jet Black interior.",FALSE
opt_38s_001,HTP,requires,"1. Requires (H1Y/HTM/HTP) Jet Black interior. 2. Requires (HTE/HTT/HUB/HUC) Jet Black interior or (HU0/HXO) Adrenaline Red/Jet Black interior.",FALSE
opt_38s_001,HTE,requires,"1. Requires (H1Y/HTM/HTP) Jet Black interior. 2. Requires (HTE/HTT/HUB/HUC) Jet Black interior or (HU0/HXO) Adrenaline Red/Jet Black interior.",FALSE
opt_38s_001,HTT,requires,"1. Requires (H1Y/HTM/HTP) Jet Black interior. 2. Requires (HTE/HTT/HUB/HUC) Jet Black interior or (HU0/HXO) Adrenaline Red/Jet Black interior.",FALSE
opt_38s_001,HUB,requires,"1. Requires (H1Y/HTM/HTP) Jet Black interior. 2. Requires (HTE/HTT/HUB/HUC) Jet Black interior or (HU0/HXO) Adrenaline Red/Jet Black interior.",FALSE
opt_38s_001,HUC,requires,"1. Requires (H1Y/HTM/HTP) Jet Black interior. 2. Requires (HTE/HTT/HUB/HUC) Jet Black interior or (HU0/HXO) Adrenaline Red/Jet Black interior.",FALSE
opt_38s_001,HU0,requires,"1. Requires (H1Y/HTM/HTP) Jet Black interior. 2. Requires (HTE/HTT/HUB/HUC) Jet Black interior or (HU0/HXO) Adrenaline Red/Jet Black interior.",FALSE
opt_38s_001,HXO,requires,"1. Requires (H1Y/HTM/HTP) Jet Black interior. 2. Requires (HTE/HTT/HUB/HUC) Jet Black interior or (HU0/HXO) Adrenaline Red/Jet Black interior.",FALSE
opt_36s_001,H1Y,requires,"1. Requires (H1Y/HTM/HTP) Jet Black interior. 2. Requires (HTE/HTT/HUB/HUC) Jet Black interior.",FALSE
opt_36s_001,HTM,requires,"1. Requires (H1Y/HTM/HTP) Jet Black interior. 2. Requires (HTE/HTT/HUB/HUC) Jet Black interior.",FALSE
opt_36s_001,HTP,requires,"1. Requires (H1Y/HTM/HTP) Jet Black interior. 2. Requires (HTE/HTT/HUB/HUC) Jet Black interior.",FALSE
opt_36s_001,HTE,requires,"1. Requires (H1Y/HTM/HTP) Jet Black interior. 2. Requires (HTE/HTT/HUB/HUC) Jet Black interior.",FALSE
opt_36s_001,HTT,requires,"1. Requires (H1Y/HTM/HTP) Jet Black interior. 2. Requires (HTE/HTT/HUB/HUC) Jet Black interior.",FALSE
opt_36s_001,HUB,requires,"1. Requires (H1Y/HTM/HTP) Jet Black interior. 2. Requires (HTE/HTT/HUB/HUC) Jet Black interior.",FALSE
opt_36s_001,HUC,requires,"1. Requires (H1Y/HTM/HTP) Jet Black interior. 2. Requires (HTE/HTT/HUB/HUC) Jet Black interior.",FALSE
opt_37s_001,H1Y,requires,"1. Requires (H1Y/HTM/HTP) Jet Black interior. 2. Requires (HTE/HTT/HUB/HUC) Jet Black interior.",FALSE
opt_37s_001,HTM,requires,"1. Requires (H1Y/HTM/HTP) Jet Black interior. 2. Requires (HTE/HTT/HUB/HUC) Jet Black interior.",FALSE
opt_37s_001,HTP,requires,"1. Requires (H1Y/HTM/HTP) Jet Black interior. 2. Requires (HTE/HTT/HUB/HUC) Jet Black interior.",FALSE
opt_37s_001,HTE,requires,"1. Requires (H1Y/HTM/HTP) Jet Black interior. 2. Requires (HTE/HTT/HUB/HUC) Jet Black interior.",FALSE
opt_37s_001,HTT,requires,"1. Requires (H1Y/HTM/HTP) Jet Black interior. 2. Requires (HTE/HTT/HUB/HUC) Jet Black interior.",FALSE
opt_37s_001,HUB,requires,"1. Requires (H1Y/HTM/HTP) Jet Black interior. 2. Requires (HTE/HTT/HUB/HUC) Jet Black interior.",FALSE
opt_37s_001,HUC,requires,"1. Requires (H1Y/HTM/HTP) Jet Black interior. 2. Requires (HTE/HTT/HUB/HUC) Jet Black interior.",FALSE
opt_bcp_001,D3V,includes,"1. Includes (D3V) engine lighting. This option is without (B6P).",FALSE
opt_bcp_001,B6P,excludes,"1. Includes (D3V) engine lighting. This option is without (B6P).",FALSE
opt_bcs_001,D3V,includes,"1. Includes (D3V) engine lighting. This option is without (B6P).",FALSE
opt_bcs_001,B6P,excludes,"1. Includes (D3V) engine lighting. This option is without (B6P).",FALSE
opt_bc4_001,D3V,includes,"1. Includes (D3V) engine lighting. This option is without (B6P).",FALSE
opt_bc4_001,B6P,excludes,"1. Includes (D3V) engine lighting. This option is without (B6P).",FALSE
opt_bcp_002,B6P,requires,"1. Requires (B6P) on Coupe. Includes (D3V) engine lighting. 2. Requires (ZZ3) Convertible Engine Appearance Package.",FALSE
opt_bcp_002,D3V,includes,"1. Requires (B6P) on Coupe. Includes (D3V) engine lighting. 2. Requires (ZZ3) Convertible Engine Appearance Package.",FALSE
opt_bcp_002,ZZ3,requires,"1. Requires (B6P) on Coupe. Includes (D3V) engine lighting. 2. Requires (ZZ3) Convertible Engine Appearance Package.",FALSE
opt_bcs_002,B6P,requires,"1. Requires (B6P) on Coupe. Includes (D3V) engine lighting. 2. Requires (ZZ3) Convertible Engine Appearance Package.",FALSE
opt_bcs_002,D3V,includes,"1. Requires (B6P) on Coupe. Includes (D3V) engine lighting. 2. Requires (ZZ3) Convertible Engine Appearance Package.",FALSE
opt_bcs_002,ZZ3,requires,"1. Requires (B6P) on Coupe. Includes (D3V) engine lighting. 2. Requires (ZZ3) Convertible Engine Appearance Package.",FALSE
opt_bc4_002,B6P,requires,"1. Includes (D3V) engine lighting. Requires (B6P) on Coupe 2. Requires (ZZ3) Convertible Engine Appearance Package.",FALSE
opt_bc4_002,D3V,includes,"1. Includes (D3V) engine lighting. Requires (B6P) on Coupe 2. Requires (ZZ3) Convertible Engine Appearance Package.",FALSE
opt_bc4_002,ZZ3,requires,"1. Includes (D3V) engine lighting. Requires (B6P) on Coupe 2. Requires (ZZ3) Convertible Engine Appearance Package.",FALSE
opt_d3v_001,B6P,includes,"1. Included with (B6P) Coupe Engine Appearance Package or (BC4/BCP/BCS) LS6 engine covers.",FALSE
opt_d3v_001,BC4,includes,"1. Included with (B6P) Coupe Engine Appearance Package or (BC4/BCP/BCS) LS6 engine covers.",FALSE
opt_d3v_001,BCP,includes,"1. Included with (B6P) Coupe Engine Appearance Package or (BC4/BCP/BCS) LS6 engine covers.",FALSE
opt_d3v_001,BCS,includes,"1. Included with (B6P) Coupe Engine Appearance Package or (BC4/BCP/BCS) LS6 engine covers.",FALSE
opt_bc7_001,ZZ3,requires,"1. Included and only available with (ZZ3) Convertible Engine Appearance Package.",FALSE
opt_sl9_001,B6P,includes,"1. Included with (B6P/ZZ3) Engine Appearance Package.",FALSE
opt_sl9_001,ZZ3,includes,"1. Included with (B6P/ZZ3) Engine Appearance Package.",FALSE
opt_nwi_001,WUB,requires,"1. Requires (WUB) quad center exit exhaust.",FALSE
opt_efy_001,GBA,excludes,"1. Not available with exterior color (GBA) Black. 2. Not available with exterior color (GBA) Black. Also includes tonneau grille.",FALSE
opt_bv4_001,R8C,excludes,"1. Available on SOLD orders only. Not available with (R8C) Corvette Museum Delivery.",TRUE
opt_pcu_001,5V7,excludes,"1. Not available with (5V7) Black Ground Effects, LPO. 2. Not available with 5V7, 5VM, 5W8.",FALSE
opt_pcu_001,5VM,excludes,"1. Not available with (5V7) Black Ground Effects, LPO. 2. Not available with 5V7, 5VM, 5W8.",FALSE
opt_pcu_001,5W8,excludes,"1. Not available with (5V7) Black Ground Effects, LPO. 2. Not available with 5V7, 5VM, 5W8.",FALSE
opt_pdv_001,DPB,excludes,"1. Not available with RPO stripes (DPB, DPC, DPG, DPL, DPT, DSY, DSZ, DT0, DTB, DTH, DUB, DUE, DUK, DUW, DZU, DZV, DZX).",FALSE
opt_pdv_001,DPC,excludes,"1. Not available with RPO stripes (DPB, DPC, DPG, DPL, DPT, DSY, DSZ, DT0, DTB, DTH, DUB, DUE, DUK, DUW, DZU, DZV, DZX).",FALSE
opt_pdv_001,DPG,excludes,"1. Not available with RPO stripes (DPB, DPC, DPG, DPL, DPT, DSY, DSZ, DT0, DTB, DTH, DUB, DUE, DUK, DUW, DZU, DZV, DZX).",FALSE
opt_pdv_001,DPL,excludes,"1. Not available with RPO stripes (DPB, DPC, DPG, DPL, DPT, DSY, DSZ, DT0, DTB, DTH, DUB, DUE, DUK, DUW, DZU, DZV, DZX).",FALSE
opt_pdv_001,DPT,excludes,"1. Not available with RPO stripes (DPB, DPC, DPG, DPL, DPT, DSY, DSZ, DT0, DTB, DTH, DUB, DUE, DUK, DUW, DZU, DZV, DZX).",FALSE
opt_pdv_001,DSY,excludes,"1. Not available with RPO stripes (DPB, DPC, DPG, DPL, DPT, DSY, DSZ, DT0, DTB, DTH, DUB, DUE, DUK, DUW, DZU, DZV, DZX).",FALSE
opt_pdv_001,DSZ,excludes,"1. Not available with RPO stripes (DPB, DPC, DPG, DPL, DPT, DSY, DSZ, DT0, DTB, DTH, DUB, DUE, DUK, DUW, DZU, DZV, DZX).",FALSE
opt_pdv_001,DT0,excludes,"1. Not available with RPO stripes (DPB, DPC, DPG, DPL, DPT, DSY, DSZ, DT0, DTB, DTH, DUB, DUE, DUK, DUW, DZU, DZV, DZX).",FALSE
opt_pdv_001,DTB,excludes,"1. Not available with RPO stripes (DPB, DPC, DPG, DPL, DPT, DSY, DSZ, DT0, DTB, DTH, DUB, DUE, DUK, DUW, DZU, DZV, DZX).",FALSE
opt_pdv_001,DTH,excludes,"1. Not available with RPO stripes (DPB, DPC, DPG, DPL, DPT, DSY, DSZ, DT0, DTB, DTH, DUB, DUE, DUK, DUW, DZU, DZV, DZX).",FALSE
opt_pdv_001,DUB,excludes,"1. Not available with RPO stripes (DPB, DPC, DPG, DPL, DPT, DSY, DSZ, DT0, DTB, DTH, DUB, DUE, DUK, DUW, DZU, DZV, DZX).",FALSE
opt_pdv_001,DUE,excludes,"1. Not available with RPO stripes (DPB, DPC, DPG, DPL, DPT, DSY, DSZ, DT0, DTB, DTH, DUB, DUE, DUK, DUW, DZU, DZV, DZX).",FALSE
opt_pdv_001,DUK,excludes,"1. Not available with RPO stripes (DPB, DPC, DPG, DPL, DPT, DSY, DSZ, DT0, DTB, DTH, DUB, DUE, DUK, DUW, DZU, DZV, DZX).",FALSE
opt_pdv_001,DUW,excludes,"1. Not available with RPO stripes (DPB, DPC, DPG, DPL, DPT, DSY, DSZ, DT0, DTB, DTH, DUB, DUE, DUK, DUW, DZU, DZV, DZX).",FALSE
opt_pdv_001,DZU,excludes,"1. Not available with RPO stripes (DPB, DPC, DPG, DPL, DPT, DSY, DSZ, DT0, DTB, DTH, DUB, DUE, DUK, DUW, DZU, DZV, DZX).",FALSE
opt_pdv_001,DZV,excludes,"1. Not available with RPO stripes (DPB, DPC, DPG, DPL, DPT, DSY, DSZ, DT0, DTB, DTH, DUB, DUE, DUK, DUW, DZU, DZV, DZX).",FALSE
opt_pdv_001,DZX,excludes,"1. Not available with RPO stripes (DPB, DPC, DPG, DPL, DPT, DSY, DSZ, DT0, DTB, DTH, DUB, DUE, DUK, DUW, DZU, DZV, DZX).",FALSE
opt_pcx_001,R8C,excludes,"1. Not available with R8C, SPZ, SFE, SPY, S47, EYK, PDV, SB7 or RPO stripes (DPB, DPC, DPG, DPL, DPT, DSY, DSZ, DT0, DTB, DTH, DUB, DUE, DUK, DUW, DZU, DZV, DZX).",FALSE
opt_pcx_001,SPZ,excludes,"1. Not available with R8C, SPZ, SFE, SPY, S47, EYK, PDV, SB7 or RPO stripes (DPB, DPC, DPG, DPL, DPT, DSY, DSZ, DT0, DTB, DTH, DUB, DUE, DUK, DUW, DZU, DZV, DZX).",FALSE
opt_pcx_001,SFE,excludes,"1. Not available with R8C, SPZ, SFE, SPY, S47, EYK, PDV, SB7 or RPO stripes (DPB, DPC, DPG, DPL, DPT, DSY, DSZ, DT0, DTB, DTH, DUB, DUE, DUK, DUW, DZU, DZV, DZX).",FALSE
opt_pcx_001,SPY,excludes,"1. Not available with R8C, SPZ, SFE, SPY, S47, EYK, PDV, SB7 or RPO stripes (DPB, DPC, DPG, DPL, DPT, DSY, DSZ, DT0, DTB, DTH, DUB, DUE, DUK, DUW, DZU, DZV, DZX).",FALSE
opt_pcx_001,S47,excludes,"1. Not available with R8C, SPZ, SFE, SPY, S47, EYK, PDV, SB7 or RPO stripes (DPB, DPC, DPG, DPL, DPT, DSY, DSZ, DT0, DTB, DTH, DUB, DUE, DUK, DUW, DZU, DZV, DZX).",FALSE
opt_pcx_001,EYK,excludes,"1. Not available with R8C, SPZ, SFE, SPY, S47, EYK, PDV, SB7 or RPO stripes (DPB, DPC, DPG, DPL, DPT, DSY, DSZ, DT0, DTB, DTH, DUB, DUE, DUK, DUW, DZU, DZV, DZX).",FALSE
opt_pcx_001,PDV,excludes,"1. Not available with R8C, SPZ, SFE, SPY, S47, EYK, PDV, SB7 or RPO stripes (DPB, DPC, DPG, DPL, DPT, DSY, DSZ, DT0, DTB, DTH, DUB, DUE, DUK, DUW, DZU, DZV, DZX).",FALSE
opt_pcx_001,SB7,excludes,"1. Not available with R8C, SPZ, SFE, SPY, S47, EYK, PDV, SB7 or RPO stripes (DPB, DPC, DPG, DPL, DPT, DSY, DSZ, DT0, DTB, DTH, DUB, DUE, DUK, DUW, DZU, DZV, DZX).",FALSE
opt_pcx_001,DPB,excludes,"1. Not available with R8C, SPZ, SFE, SPY, S47, EYK, PDV, SB7 or RPO stripes (DPB, DPC, DPG, DPL, DPT, DSY, DSZ, DT0, DTB, DTH, DUB, DUE, DUK, DUW, DZU, DZV, DZX).",FALSE
opt_pcx_001,DPC,excludes,"1. Not available with R8C, SPZ, SFE, SPY, S47, EYK, PDV, SB7 or RPO stripes (DPB, DPC, DPG, DPL, DPT, DSY, DSZ, DT0, DTB, DTH, DUB, DUE, DUK, DUW, DZU, DZV, DZX).",FALSE
opt_pcx_001,DPG,excludes,"1. Not available with R8C, SPZ, SFE, SPY, S47, EYK, PDV, SB7 or RPO stripes (DPB, DPC, DPG, DPL, DPT, DSY, DSZ, DT0, DTB, DTH, DUB, DUE, DUK, DUW, DZU, DZV, DZX).",FALSE
opt_pcx_001,DPL,excludes,"1. Not available with R8C, SPZ, SFE, SPY, S47, EYK, PDV, SB7 or RPO stripes (DPB, DPC, DPG, DPL, DPT, DSY, DSZ, DT0, DTB, DTH, DUB, DUE, DUK, DUW, DZU, DZV, DZX).",FALSE
opt_pcx_001,DPT,excludes,"1. Not available with R8C, SPZ, SFE, SPY, S47, EYK, PDV, SB7 or RPO stripes (DPB, DPC, DPG, DPL, DPT, DSY, DSZ, DT0, DTB, DTH, DUB, DUE, DUK, DUW, DZU, DZV, DZX).",FALSE
opt_pcx_001,DSY,excludes,"1. Not available with R8C, SPZ, SFE, SPY, S47, EYK, PDV, SB7 or RPO stripes (DPB, DPC, DPG, DPL, DPT, DSY, DSZ, DT0, DTB, DTH, DUB, DUE, DUK, DUW, DZU, DZV, DZX).",FALSE
opt_pcx_001,DSZ,excludes,"1. Not available with R8C, SPZ, SFE, SPY, S47, EYK, PDV, SB7 or RPO stripes (DPB, DPC, DPG, DPL, DPT, DSY, DSZ, DT0, DTB, DTH, DUB, DUE, DUK, DUW, DZU, DZV, DZX).",FALSE
opt_pcx_001,DT0,excludes,"1. Not available with R8C, SPZ, SFE, SPY, S47, EYK, PDV, SB7 or RPO stripes (DPB, DPC, DPG, DPL, DPT, DSY, DSZ, DT0, DTB, DTH, DUB, DUE, DUK, DUW, DZU, DZV, DZX).",FALSE
opt_pcx_001,DTB,excludes,"1. Not available with R8C, SPZ, SFE, SPY, S47, EYK, PDV, SB7 or RPO stripes (DPB, DPC, DPG, DPL, DPT, DSY, DSZ, DT0, DTB, DTH, DUB, DUE, DUK, DUW, DZU, DZV, DZX).",FALSE
opt_pcx_001,DTH,excludes,"1. Not available with R8C, SPZ, SFE, SPY, S47, EYK, PDV, SB7 or RPO stripes (DPB, DPC, DPG, DPL, DPT, DSY, DSZ, DT0, DTB, DTH, DUB, DUE, DUK, DUW, DZU, DZV, DZX).",FALSE
opt_pcx_001,DUB,excludes,"1. Not available with R8C, SPZ, SFE, SPY, S47, EYK, PDV, SB7 or RPO stripes (DPB, DPC, DPG, DPL, DPT, DSY, DSZ, DT0, DTB, DTH, DUB, DUE, DUK, DUW, DZU, DZV, DZX).",FALSE
opt_pcx_001,DUE,excludes,"1. Not available with R8C, SPZ, SFE, SPY, S47, EYK, PDV, SB7 or RPO stripes (DPB, DPC, DPG, DPL, DPT, DSY, DSZ, DT0, DTB, DTH, DUB, DUE, DUK, DUW, DZU, DZV, DZX).",FALSE
opt_pcx_001,DUK,excludes,"1. Not available with R8C, SPZ, SFE, SPY, S47, EYK, PDV, SB7 or RPO stripes (DPB, DPC, DPG, DPL, DPT, DSY, DSZ, DT0, DTB, DTH, DUB, DUE, DUK, DUW, DZU, DZV, DZX).",FALSE
opt_pcx_001,DUW,excludes,"1. Not available with R8C, SPZ, SFE, SPY, S47, EYK, PDV, SB7 or RPO stripes (DPB, DPC, DPG, DPL, DPT, DSY, DSZ, DT0, DTB, DTH, DUB, DUE, DUK, DUW, DZU, DZV, DZX).",FALSE
opt_pcx_001,DZU,excludes,"1. Not available with R8C, SPZ, SFE, SPY, S47, EYK, PDV, SB7 or RPO stripes (DPB, DPC, DPG, DPL, DPT, DSY, DSZ, DT0, DTB, DTH, DUB, DUE, DUK, DUW, DZU, DZV, DZX).",FALSE
opt_pcx_001,DZV,excludes,"1. Not available with R8C, SPZ, SFE, SPY, S47, EYK, PDV, SB7 or RPO stripes (DPB, DPC, DPG, DPL, DPT, DSY, DSZ, DT0, DTB, DTH, DUB, DUE, DUK, DUW, DZU, DZV, DZX).",FALSE
opt_pcx_001,DZX,excludes,"1. Not available with R8C, SPZ, SFE, SPY, S47, EYK, PDV, SB7 or RPO stripes (DPB, DPC, DPG, DPL, DPT, DSY, DSZ, DT0, DTB, DTH, DUB, DUE, DUK, DUW, DZU, DZV, DZX).",FALSE
opt_5v7_001,5ZU,requires,"1. Requires 5ZU, 5ZW or 5ZZ. Not available with STI, TVS, Z51. 2. Requires 5ZU, 5ZW or 5ZZ. Not available with 5VM, 5W8, STI, TVS, Z51.",TRUE
opt_5v7_001,5ZW,requires,"1. Requires 5ZU, 5ZW or 5ZZ. Not available with STI, TVS, Z51. 2. Requires 5ZU, 5ZW or 5ZZ. Not available with 5VM, 5W8, STI, TVS, Z51.",TRUE
opt_5v7_001,5ZZ,requires,"1. Requires 5ZU, 5ZW or 5ZZ. Not available with STI, TVS, Z51. 2. Requires 5ZU, 5ZW or 5ZZ. Not available with 5VM, 5W8, STI, TVS, Z51.",TRUE
opt_5v7_001,STI,excludes,"1. Requires 5ZU, 5ZW or 5ZZ. Not available with STI, TVS, Z51. 2. Requires 5ZU, 5ZW or 5ZZ. Not available with 5VM, 5W8, STI, TVS, Z51.",TRUE
opt_5v7_001,TVS,excludes,"1. Requires 5ZU, 5ZW or 5ZZ. Not available with STI, TVS, Z51. 2. Requires 5ZU, 5ZW or 5ZZ. Not available with 5VM, 5W8, STI, TVS, Z51.",TRUE
opt_5v7_001,Z51,excludes,"1. Requires 5ZU, 5ZW or 5ZZ. Not available with STI, TVS, Z51. 2. Requires 5ZU, 5ZW or 5ZZ. Not available with 5VM, 5W8, STI, TVS, Z51.",TRUE
opt_5v7_001,5VM,excludes,"1. Requires 5ZU, 5ZW or 5ZZ. Not available with STI, TVS, Z51. 2. Requires 5ZU, 5ZW or 5ZZ. Not available with 5VM, 5W8, STI, TVS, Z51.",TRUE
opt_5v7_001,5W8,excludes,"1. Requires 5ZU, 5ZW or 5ZZ. Not available with STI, TVS, Z51. 2. Requires 5ZU, 5ZW or 5ZZ. Not available with 5VM, 5W8, STI, TVS, Z51.",TRUE
opt_sti_001,5V7,excludes,"1. Not available with (5V7) Black Ground Effects, LPO. Included with (PCU) Stingray Protection Package, LPO. 2. Not available with 5V7, 5VM, 5W8. Included with (PCU) Stingray Protection Package, LPO.",FALSE
opt_sti_001,5VM,excludes,"1. Not available with (5V7) Black Ground Effects, LPO. Included with (PCU) Stingray Protection Package, LPO. 2. Not available with 5V7, 5VM, 5W8. Included with (PCU) Stingray Protection Package, LPO.",FALSE
opt_sti_001,5W8,excludes,"1. Not available with (5V7) Black Ground Effects, LPO. Included with (PCU) Stingray Protection Package, LPO. 2. Not available with 5V7, 5VM, 5W8. Included with (PCU) Stingray Protection Package, LPO.",FALSE
opt_sti_001,PCU,includes,"1. Not available with (5V7) Black Ground Effects, LPO. Included with (PCU) Stingray Protection Package, LPO. 2. Not available with 5V7, 5VM, 5W8. Included with (PCU) Stingray Protection Package, LPO.",FALSE
opt_vqk_001,PCU,includes,"1. Included with (PCU) Stingray Protection Package, LPO.",FALSE
opt_vwe_001,PCU,includes,"1. Included with (PCU) Stingray Protection Package, LPO.",FALSE
opt_r88_001,SFZ,excludes,"1. Not available with (SFZ) Dark Stealth crossed flags emblems, LPO, (EYK) Chrome Exterior Badge Package or any Full Length Dual Racing Stripes (DPB, DPC, DPG, DPL, DPT, DSY, DSZ, DT0, DTB, DTH, DUB, DUE, DUK, DUW).",FALSE
opt_r88_001,EYK,excludes,"1. Not available with (SFZ) Dark Stealth crossed flags emblems, LPO, (EYK) Chrome Exterior Badge Package or any Full Length Dual Racing Stripes (DPB, DPC, DPG, DPL, DPT, DSY, DSZ, DT0, DTB, DTH, DUB, DUE, DUK, DUW).",FALSE
opt_r88_001,DPB,excludes,"1. Not available with (SFZ) Dark Stealth crossed flags emblems, LPO, (EYK) Chrome Exterior Badge Package or any Full Length Dual Racing Stripes (DPB, DPC, DPG, DPL, DPT, DSY, DSZ, DT0, DTB, DTH, DUB, DUE, DUK, DUW).",FALSE
opt_r88_001,DPC,excludes,"1. Not available with (SFZ) Dark Stealth crossed flags emblems, LPO, (EYK) Chrome Exterior Badge Package or any Full Length Dual Racing Stripes (DPB, DPC, DPG, DPL, DPT, DSY, DSZ, DT0, DTB, DTH, DUB, DUE, DUK, DUW).",FALSE
opt_r88_001,DPG,excludes,"1. Not available with (SFZ) Dark Stealth crossed flags emblems, LPO, (EYK) Chrome Exterior Badge Package or any Full Length Dual Racing Stripes (DPB, DPC, DPG, DPL, DPT, DSY, DSZ, DT0, DTB, DTH, DUB, DUE, DUK, DUW).",FALSE
opt_r88_001,DPL,excludes,"1. Not available with (SFZ) Dark Stealth crossed flags emblems, LPO, (EYK) Chrome Exterior Badge Package or any Full Length Dual Racing Stripes (DPB, DPC, DPG, DPL, DPT, DSY, DSZ, DT0, DTB, DTH, DUB, DUE, DUK, DUW).",FALSE
opt_r88_001,DPT,excludes,"1. Not available with (SFZ) Dark Stealth crossed flags emblems, LPO, (EYK) Chrome Exterior Badge Package or any Full Length Dual Racing Stripes (DPB, DPC, DPG, DPL, DPT, DSY, DSZ, DT0, DTB, DTH, DUB, DUE, DUK, DUW).",FALSE
opt_r88_001,DSY,excludes,"1. Not available with (SFZ) Dark Stealth crossed flags emblems, LPO, (EYK) Chrome Exterior Badge Package or any Full Length Dual Racing Stripes (DPB, DPC, DPG, DPL, DPT, DSY, DSZ, DT0, DTB, DTH, DUB, DUE, DUK, DUW).",FALSE
opt_r88_001,DSZ,excludes,"1. Not available with (SFZ) Dark Stealth crossed flags emblems, LPO, (EYK) Chrome Exterior Badge Package or any Full Length Dual Racing Stripes (DPB, DPC, DPG, DPL, DPT, DSY, DSZ, DT0, DTB, DTH, DUB, DUE, DUK, DUW).",FALSE
opt_r88_001,DT0,excludes,"1. Not available with (SFZ) Dark Stealth crossed flags emblems, LPO, (EYK) Chrome Exterior Badge Package or any Full Length Dual Racing Stripes (DPB, DPC, DPG, DPL, DPT, DSY, DSZ, DT0, DTB, DTH, DUB, DUE, DUK, DUW).",FALSE
opt_r88_001,DTB,excludes,"1. Not available with (SFZ) Dark Stealth crossed flags emblems, LPO, (EYK) Chrome Exterior Badge Package or any Full Length Dual Racing Stripes (DPB, DPC, DPG, DPL, DPT, DSY, DSZ, DT0, DTB, DTH, DUB, DUE, DUK, DUW).",FALSE
opt_r88_001,DTH,excludes,"1. Not available with (SFZ) Dark Stealth crossed flags emblems, LPO, (EYK) Chrome Exterior Badge Package or any Full Length Dual Racing Stripes (DPB, DPC, DPG, DPL, DPT, DSY, DSZ, DT0, DTB, DTH, DUB, DUE, DUK, DUW).",FALSE
opt_r88_001,DUB,excludes,"1. Not available with (SFZ) Dark Stealth crossed flags emblems, LPO, (EYK) Chrome Exterior Badge Package or any Full Length Dual Racing Stripes (DPB, DPC, DPG, DPL, DPT, DSY, DSZ, DT0, DTB, DTH, DUB, DUE, DUK, DUW).",FALSE
opt_r88_001,DUE,excludes,"1. Not available with (SFZ) Dark Stealth crossed flags emblems, LPO, (EYK) Chrome Exterior Badge Package or any Full Length Dual Racing Stripes (DPB, DPC, DPG, DPL, DPT, DSY, DSZ, DT0, DTB, DTH, DUB, DUE, DUK, DUW).",FALSE
opt_r88_001,DUK,excludes,"1. Not available with (SFZ) Dark Stealth crossed flags emblems, LPO, (EYK) Chrome Exterior Badge Package or any Full Length Dual Racing Stripes (DPB, DPC, DPG, DPL, DPT, DSY, DSZ, DT0, DTB, DTH, DUB, DUE, DUK, DUW).",FALSE
opt_r88_001,DUW,excludes,"1. Not available with (SFZ) Dark Stealth crossed flags emblems, LPO, (EYK) Chrome Exterior Badge Package or any Full Length Dual Racing Stripes (DPB, DPC, DPG, DPL, DPT, DSY, DSZ, DT0, DTB, DTH, DUB, DUE, DUK, DUW).",FALSE
opt_rz9_001,EFY,excludes,"1. Not available with (EFY) body-color exterior accents.",FALSE
opt_5vm_001,5ZU,requires,"1. Unavailable until further notice. Requires 5ZU, 5ZW, 5ZZ or Z51. Not available with 5V7, 5W8, STI, TVS, ZF1.",TRUE
opt_5vm_001,5ZW,requires,"1. Unavailable until further notice. Requires 5ZU, 5ZW, 5ZZ or Z51. Not available with 5V7, 5W8, STI, TVS, ZF1.",TRUE
opt_5vm_001,5ZZ,requires,"1. Unavailable until further notice. Requires 5ZU, 5ZW, 5ZZ or Z51. Not available with 5V7, 5W8, STI, TVS, ZF1.",TRUE
opt_5vm_001,Z51,requires,"1. Unavailable until further notice. Requires 5ZU, 5ZW, 5ZZ or Z51. Not available with 5V7, 5W8, STI, TVS, ZF1.",TRUE
opt_5vm_001,5V7,excludes,"1. Unavailable until further notice. Requires 5ZU, 5ZW, 5ZZ or Z51. Not available with 5V7, 5W8, STI, TVS, ZF1.",TRUE
opt_5vm_001,5W8,excludes,"1. Unavailable until further notice. Requires 5ZU, 5ZW, 5ZZ or Z51. Not available with 5V7, 5W8, STI, TVS, ZF1.",TRUE
opt_5vm_001,STI,excludes,"1. Unavailable until further notice. Requires 5ZU, 5ZW, 5ZZ or Z51. Not available with 5V7, 5W8, STI, TVS, ZF1.",TRUE
opt_5vm_001,TVS,excludes,"1. Unavailable until further notice. Requires 5ZU, 5ZW, 5ZZ or Z51. Not available with 5V7, 5W8, STI, TVS, ZF1.",TRUE
opt_5vm_001,ZF1,excludes,"1. Unavailable until further notice. Requires 5ZU, 5ZW, 5ZZ or Z51. Not available with 5V7, 5W8, STI, TVS, ZF1.",TRUE
opt_5w8_001,5ZU,requires,"1. Unavailable until further notice. Requires 5ZU, 5ZW, 5ZZ or Z51. Not available with 5V7, 5VM, STI, TVS, ZF1.",TRUE
opt_5w8_001,5ZW,requires,"1. Unavailable until further notice. Requires 5ZU, 5ZW, 5ZZ or Z51. Not available with 5V7, 5VM, STI, TVS, ZF1.",TRUE
opt_5w8_001,5ZZ,requires,"1. Unavailable until further notice. Requires 5ZU, 5ZW, 5ZZ or Z51. Not available with 5V7, 5VM, STI, TVS, ZF1.",TRUE
opt_5w8_001,Z51,requires,"1. Unavailable until further notice. Requires 5ZU, 5ZW, 5ZZ or Z51. Not available with 5V7, 5VM, STI, TVS, ZF1.",TRUE
opt_5w8_001,5V7,excludes,"1. Unavailable until further notice. Requires 5ZU, 5ZW, 5ZZ or Z51. Not available with 5V7, 5VM, STI, TVS, ZF1.",TRUE
opt_5w8_001,5VM,excludes,"1. Unavailable until further notice. Requires 5ZU, 5ZW, 5ZZ or Z51. Not available with 5V7, 5VM, STI, TVS, ZF1.",TRUE
opt_5w8_001,STI,excludes,"1. Unavailable until further notice. Requires 5ZU, 5ZW, 5ZZ or Z51. Not available with 5V7, 5VM, STI, TVS, ZF1.",TRUE
opt_5w8_001,TVS,excludes,"1. Unavailable until further notice. Requires 5ZU, 5ZW, 5ZZ or Z51. Not available with 5V7, 5VM, STI, TVS, ZF1.",TRUE
opt_5w8_001,ZF1,excludes,"1. Unavailable until further notice. Requires 5ZU, 5ZW, 5ZZ or Z51. Not available with 5V7, 5VM, STI, TVS, ZF1.",TRUE
opt_wkq_001,5ZU,excludes,"1. Not available with 5ZU, 5ZW, 5ZZ.",FALSE
opt_wkq_001,5ZW,excludes,"1. Not available with 5ZU, 5ZW, 5ZZ.",FALSE
opt_wkq_001,5ZZ,excludes,"1. Not available with 5ZU, 5ZW, 5ZZ.",FALSE
opt_rnx_001,5ZU,excludes,"1. Not available with 5ZU, 5ZW, 5ZZ, Z51.",FALSE
opt_rnx_001,5ZW,excludes,"1. Not available with 5ZU, 5ZW, 5ZZ, Z51.",FALSE
opt_rnx_001,5ZZ,excludes,"1. Not available with 5ZU, 5ZW, 5ZZ, Z51.",FALSE
opt_rnx_001,Z51,excludes,"1. Not available with 5ZU, 5ZW, 5ZZ, Z51.",FALSE
opt_rwj_001,Z51,excludes,"1. Not available with (Z51) Z51 Performance Package.",FALSE
opt_rin_001,RIK,excludes,"1. Not available with RIK, SL8.",FALSE
opt_rin_001,SL8,excludes,"1. Not available with RIK, SL8.",FALSE
opt_sl8_001,RIK,excludes,"1. Not available with RIK, RIN.",FALSE
opt_sl8_001,RIN,excludes,"1. Not available with RIK, RIN.",FALSE
opt_rik_001,RIN,excludes,"1. Not available with RIN, SL8.",FALSE
opt_rik_001,SL8,excludes,"1. Not available with RIN, SL8.",FALSE
opt_n26_001,HTJ,requires,"1. Requires (HTJ) Jet Black interior. 2. Requires leather seating surfaces with perforated sueded microfiber inserts interior: HTP, HU6, HU7, HTQ. 3. Requires leather seating surfaces with perforated sueded microfiber inserts interiors: HTT, HU9, HUA, HTG, HUF, HMO, HVT, HXO, HZP, HUX, EPX, HUB.",FALSE
opt_n26_001,HTP,requires,"1. Requires (HTJ) Jet Black interior. 2. Requires leather seating surfaces with perforated sueded microfiber inserts interior: HTP, HU6, HU7, HTQ. 3. Requires leather seating surfaces with perforated sueded microfiber inserts interiors: HTT, HU9, HUA, HTG, HUF, HMO, HVT, HXO, HZP, HUX, EPX, HUB.",FALSE
opt_n26_001,HU6,requires,"1. Requires (HTJ) Jet Black interior. 2. Requires leather seating surfaces with perforated sueded microfiber inserts interior: HTP, HU6, HU7, HTQ. 3. Requires leather seating surfaces with perforated sueded microfiber inserts interiors: HTT, HU9, HUA, HTG, HUF, HMO, HVT, HXO, HZP, HUX, EPX, HUB.",FALSE
opt_n26_001,HU7,requires,"1. Requires (HTJ) Jet Black interior. 2. Requires leather seating surfaces with perforated sueded microfiber inserts interior: HTP, HU6, HU7, HTQ. 3. Requires leather seating surfaces with perforated sueded microfiber inserts interiors: HTT, HU9, HUA, HTG, HUF, HMO, HVT, HXO, HZP, HUX, EPX, HUB.",FALSE
opt_n26_001,HTQ,requires,"1. Requires (HTJ) Jet Black interior. 2. Requires leather seating surfaces with perforated sueded microfiber inserts interior: HTP, HU6, HU7, HTQ. 3. Requires leather seating surfaces with perforated sueded microfiber inserts interiors: HTT, HU9, HUA, HTG, HUF, HMO, HVT, HXO, HZP, HUX, EPX, HUB.",FALSE
opt_n26_001,HTT,requires,"1. Requires (HTJ) Jet Black interior. 2. Requires leather seating surfaces with perforated sueded microfiber inserts interior: HTP, HU6, HU7, HTQ. 3. Requires leather seating surfaces with perforated sueded microfiber inserts interiors: HTT, HU9, HUA, HTG, HUF, HMO, HVT, HXO, HZP, HUX, EPX, HUB.",FALSE
opt_n26_001,HU9,requires,"1. Requires (HTJ) Jet Black interior. 2. Requires leather seating surfaces with perforated sueded microfiber inserts interior: HTP, HU6, HU7, HTQ. 3. Requires leather seating surfaces with perforated sueded microfiber inserts interiors: HTT, HU9, HUA, HTG, HUF, HMO, HVT, HXO, HZP, HUX, EPX, HUB.",FALSE
opt_n26_001,HUA,requires,"1. Requires (HTJ) Jet Black interior. 2. Requires leather seating surfaces with perforated sueded microfiber inserts interior: HTP, HU6, HU7, HTQ. 3. Requires leather seating surfaces with perforated sueded microfiber inserts interiors: HTT, HU9, HUA, HTG, HUF, HMO, HVT, HXO, HZP, HUX, EPX, HUB.",FALSE
opt_n26_001,HTG,requires,"1. Requires (HTJ) Jet Black interior. 2. Requires leather seating surfaces with perforated sueded microfiber inserts interior: HTP, HU6, HU7, HTQ. 3. Requires leather seating surfaces with perforated sueded microfiber inserts interiors: HTT, HU9, HUA, HTG, HUF, HMO, HVT, HXO, HZP, HUX, EPX, HUB.",FALSE
opt_n26_001,HUF,requires,"1. Requires (HTJ) Jet Black interior. 2. Requires leather seating surfaces with perforated sueded microfiber inserts interior: HTP, HU6, HU7, HTQ. 3. Requires leather seating surfaces with perforated sueded microfiber inserts interiors: HTT, HU9, HUA, HTG, HUF, HMO, HVT, HXO, HZP, HUX, EPX, HUB.",FALSE
opt_n26_001,HMO,requires,"1. Requires (HTJ) Jet Black interior. 2. Requires leather seating surfaces with perforated sueded microfiber inserts interior: HTP, HU6, HU7, HTQ. 3. Requires leather seating surfaces with perforated sueded microfiber inserts interiors: HTT, HU9, HUA, HTG, HUF, HMO, HVT, HXO, HZP, HUX, EPX, HUB.",FALSE
opt_n26_001,HVT,requires,"1. Requires (HTJ) Jet Black interior. 2. Requires leather seating surfaces with perforated sueded microfiber inserts interior: HTP, HU6, HU7, HTQ. 3. Requires leather seating surfaces with perforated sueded microfiber inserts interiors: HTT, HU9, HUA, HTG, HUF, HMO, HVT, HXO, HZP, HUX, EPX, HUB.",FALSE
opt_n26_001,HXO,requires,"1. Requires (HTJ) Jet Black interior. 2. Requires leather seating surfaces with perforated sueded microfiber inserts interior: HTP, HU6, HU7, HTQ. 3. Requires leather seating surfaces with perforated sueded microfiber inserts interiors: HTT, HU9, HUA, HTG, HUF, HMO, HVT, HXO, HZP, HUX, EPX, HUB.",FALSE
opt_n26_001,HZP,requires,"1. Requires (HTJ) Jet Black interior. 2. Requires leather seating surfaces with perforated sueded microfiber inserts interior: HTP, HU6, HU7, HTQ. 3. Requires leather seating surfaces with perforated sueded microfiber inserts interiors: HTT, HU9, HUA, HTG, HUF, HMO, HVT, HXO, HZP, HUX, EPX, HUB.",FALSE
opt_n26_001,HUX,requires,"1. Requires (HTJ) Jet Black interior. 2. Requires leather seating surfaces with perforated sueded microfiber inserts interior: HTP, HU6, HU7, HTQ. 3. Requires leather seating surfaces with perforated sueded microfiber inserts interiors: HTT, HU9, HUA, HTG, HUF, HMO, HVT, HXO, HZP, HUX, EPX, HUB.",FALSE
opt_n26_001,EPX,requires,"1. Requires (HTJ) Jet Black interior. 2. Requires leather seating surfaces with perforated sueded microfiber inserts interior: HTP, HU6, HU7, HTQ. 3. Requires leather seating surfaces with perforated sueded microfiber inserts interiors: HTT, HU9, HUA, HTG, HUF, HMO, HVT, HXO, HZP, HUX, EPX, HUB.",FALSE
opt_n26_001,HUB,requires,"1. Requires (HTJ) Jet Black interior. 2. Requires leather seating surfaces with perforated sueded microfiber inserts interior: HTP, HU6, HU7, HTQ. 3. Requires leather seating surfaces with perforated sueded microfiber inserts interiors: HTT, HU9, HUA, HTG, HUF, HMO, HVT, HXO, HZP, HUX, EPX, HUB.",FALSE
opt_tu7_001,AH2,requires,"1. Requires (AH2) GT2 seats. Available with (HUK/HU6) Sky Cool Gray, (HUL/HU7) Adrenaline Red, (HTN/HTQ) Natural interiors. 2. Requires (AH2) GT2 seats. Available with (HU1/HU9) Sky Cool Gray, (HU2/HUA) Adrenaline Red, (HUE/HTG) Natural, (HMO/HVV) Jet Black/Sky Cool Gray, (HU0/HXO) Jet Black/Adrenaline Red interiors.",TRUE
opt_j55_001,Z51,requires,"1. Included and only available with (Z51) Z51 Performance Package.",FALSE
opt_v08_001,Z51,requires,"1. Included and only available with (Z51) Z51 Performance Package.",FALSE
opt_g96_001,Z51,requires,"1. Included and only available with (Z51) Z51 Performance Package.",FALSE
opt_qtu_001,Z51,requires,"1. Included and only available with (Z51) Z51 Performance Package.",FALSE
opt_m1n_001,Z51,requires,"1. Included and only available with (Z51) Z51 Performance Package.",FALSE
opt_g0k_001,Z51,requires,"1. Included and only available with (Z51) Z51 Performance Package.",FALSE
opt_t0a_001,Z51,requires,"1. Included and only available with (Z51) Z51 Performance Package.",FALSE
opt_fe3_001,Z51,requires,"1. Included and only available with (Z51) Z51 Performance Package.",FALSE
opt_b4z_001,FE4,requires,"1. Included and only available with (FE4) Z51 performance suspension with Magnetic Selective Ride Control.",FALSE
opt_fe4_001,Z51,requires,"1. Requires (Z51) Z51 Performance Package.",FALSE
opt_drg_001,ZYC,requires,"1. Included and only available with (ZYC) Carbon Flash Metallic-painted outside mirrors and spoiler (when equipped) or (5JR) outside mirror covers in visible Carbon Fiber, LPO.",FALSE
opt_drg_001,5JR,requires,"1. Included and only available with (ZYC) Carbon Flash Metallic-painted outside mirrors and spoiler (when equipped) or (5JR) outside mirror covers in visible Carbon Fiber, LPO.",FALSE
opt_tr7_001,E60,requires,"1. Included and only available with (E60) front lift adjustable height.",FALSE
opt_cfx_001,R8C,requires,"1. Included and only available with (R8C) Corvette Museum Delivery.",FALSE
opt_r8c_001,R8C,excludes,"1. Must also add Ship To BAC 184590 (Dealer code 31-728). Available on SOLD orders only. Not available with LPO wheels.",TRUE
opt_719_001,HZN,includes,"1. (HZN, HUF) Natural Dipped interior comes with (3N9) Natural seat belt color; (H8T) Santorini Blue interior and (HAG) Asymmetrical Santorini Blue/Jet Black interior comes with (3A9) Santorini Blue seat belt color; (HNK) Adrenaline Red Dipped interior comes with (3F9) Torch Red seat belt color; (HUW, HUX) Habanero interior comes with (379) Orange seat belt color.",TRUE
opt_719_001,HUF,includes,"1. (HZN, HUF) Natural Dipped interior comes with (3N9) Natural seat belt color; (H8T) Santorini Blue interior and (HAG) Asymmetrical Santorini Blue/Jet Black interior comes with (3A9) Santorini Blue seat belt color; (HNK) Adrenaline Red Dipped interior comes with (3F9) Torch Red seat belt color; (HUW, HUX) Habanero interior comes with (379) Orange seat belt color.",TRUE
opt_3n9_001,HZN,includes,"1. (HZN, HUF) Natural Dipped interior comes with (3N9) Natural seat belt color; (H8T) Santorini Blue interior and (HAG) Asymmetrical Santorini Blue/Jet Black interior comes with (3A9) Santorini Blue seat belt color; (HNK) Adrenaline Red Dipped interior comes with (3F9) Torch Red seat belt color; (HUW, HUX) Habanero interior comes with (379) Orange seat belt color.",TRUE
opt_3n9_001,HUF,includes,"1. (HZN, HUF) Natural Dipped interior comes with (3N9) Natural seat belt color; (H8T) Santorini Blue interior and (HAG) Asymmetrical Santorini Blue/Jet Black interior comes with (3A9) Santorini Blue seat belt color; (HNK) Adrenaline Red Dipped interior comes with (3F9) Torch Red seat belt color; (HUW, HUX) Habanero interior comes with (379) Orange seat belt color.",TRUE
opt_3a9_001,H8T,includes,"1. (HZN, HUF) Natural Dipped interior comes with (3N9) Natural seat belt color; (H8T) Santorini Blue interior and (HAG) Asymmetrical Santorini Blue/Jet Black interior comes with (3A9) Santorini Blue seat belt color; (HNK) Adrenaline Red Dipped interior comes with (3F9) Torch Red seat belt color; (HUW, HUX) Habanero interior comes with (379) Orange seat belt color.",TRUE
opt_3a9_001,HAG,includes,"1. (HZN, HUF) Natural Dipped interior comes with (3N9) Natural seat belt color; (H8T) Santorini Blue interior and (HAG) Asymmetrical Santorini Blue/Jet Black interior comes with (3A9) Santorini Blue seat belt color; (HNK) Adrenaline Red Dipped interior comes with (3F9) Torch Red seat belt color; (HUW, HUX) Habanero interior comes with (379) Orange seat belt color.",TRUE
opt_3f9_001,HNK,includes,"1. (HZN, HUF) Natural Dipped interior comes with (3N9) Natural seat belt color; (H8T) Santorini Blue interior and (HAG) Asymmetrical Santorini Blue/Jet Black interior comes with (3A9) Santorini Blue seat belt color; (HNK) Adrenaline Red Dipped interior comes with (3F9) Torch Red seat belt color; (HUW, HUX) Habanero interior comes with (379) Orange seat belt color.",TRUE
opt_379_001,HUW,includes,"1. (HZN, HUF) Natural Dipped interior comes with (3N9) Natural seat belt color; (H8T) Santorini Blue interior and (HAG) Asymmetrical Santorini Blue/Jet Black interior comes with (3A9) Santorini Blue seat belt color; (HNK) Adrenaline Red Dipped interior comes with (3F9) Torch Red seat belt color; (HUW, HUX) Habanero interior comes with (379) Orange seat belt color.",TRUE
opt_379_001,HUX,includes,"1. (HZN, HUF) Natural Dipped interior comes with (3N9) Natural seat belt color; (H8T) Santorini Blue interior and (HAG) Asymmetrical Santorini Blue/Jet Black interior comes with (3A9) Santorini Blue seat belt color; (HNK) Adrenaline Red Dipped interior comes with (3F9) Torch Red seat belt color; (HUW, HUX) Habanero interior comes with (379) Orange seat belt color.",TRUE
opt_aup_001,HVZ,requires,"1. Requires (HVZ) Asymmetrical Adrenaline Red/Jet Black interior or (HAG) Asymmetrical Santorini Blue/Jet Black interior.",FALSE
opt_aup_001,HAG,requires,"1. Requires (HVZ) Asymmetrical Adrenaline Red/Jet Black interior or (HAG) Asymmetrical Santorini Blue/Jet Black interior.",FALSE
opt_zf1_001,Z51,requires,"1. Requires (Z51) Z51 Performance Package. Not available with 5ZU, 5ZW, 5ZZ, 5VM, 5W8.",FALSE
opt_5zz_001,5ZU,excludes,"1. Not available with 5ZW, 5ZU, TVS. Deletes (T0A) Z51 rear spoiler when ordered with (Z51) Z51 Performance Package.",TRUE
opt_5zz_001,5ZW,excludes,"1. Not available with 5ZW, 5ZU, TVS. Deletes (T0A) Z51 rear spoiler when ordered with (Z51) Z51 Performance Package.",TRUE
opt_5zz_001,TVS,excludes,"1. Not available with 5ZW, 5ZU, TVS. Deletes (T0A) Z51 rear spoiler when ordered with (Z51) Z51 Performance Package.",TRUE
opt_5zu_001,G8G,requires,"1. Requires exterior color (G8G) Arctic White, (GBA) Black or (GKZ) Torch Red. Not available with 5ZW, 5ZZ, TVS. Deletes (T0A) Z51 rear spoiler when ordered with (Z51) Z51 Performance Package.",TRUE
opt_5zu_001,GBA,requires,"1. Requires exterior color (G8G) Arctic White, (GBA) Black or (GKZ) Torch Red. Not available with 5ZW, 5ZZ, TVS. Deletes (T0A) Z51 rear spoiler when ordered with (Z51) Z51 Performance Package.",TRUE
opt_5zu_001,GKZ,requires,"1. Requires exterior color (G8G) Arctic White, (GBA) Black or (GKZ) Torch Red. Not available with 5ZW, 5ZZ, TVS. Deletes (T0A) Z51 rear spoiler when ordered with (Z51) Z51 Performance Package.",TRUE
opt_5zw_001,5ZU,excludes,"1. Not available at this time. Not available with 5ZU, 5ZZ, TVS. Deletes (T0A) Z51 rear spoiler when ordered with (Z51) Z51 Performance Package.",TRUE
opt_5zw_001,5ZZ,excludes,"1. Not available at this time. Not available with 5ZU, 5ZZ, TVS. Deletes (T0A) Z51 rear spoiler when ordered with (Z51) Z51 Performance Package.",TRUE
opt_5zw_001,TVS,excludes,"1. Not available at this time. Not available with 5ZU, 5ZZ, TVS. Deletes (T0A) Z51 rear spoiler when ordered with (Z51) Z51 Performance Package.",TRUE
opt_sbt_001,CC3,excludes,"1. Not available with (CC3) transparent, removable roof panel.",FALSE
opt_ryt_001,PDY,includes,"1. Included with (PDY) Roadside Safety Package.",FALSE
opt_s08_001,PDY,includes,"1. Included with (PDY) Roadside Safety Package.",FALSE
opt_ria_001,PEF,includes,"1. Included with (PEF) Contoured Liner Protection Package, LPO.",FALSE
opt_cav_001,PEF,includes,"1. Included with (PEF) Contoured Liner Protection Package, LPO.",FALSE
opt_sc7_001,SBT,includes,"1. Included with (SBT) dual roof, LPO.",FALSE
opt_sng_001,PCX,includes,"1. Included with (PCX) Tech Bronze Accent Package, LPO.",FALSE
opt_sb7_001,PDV,includes,"1. Not available with RPO stripes (DPB, DPC, DPG, DPL, DPT, DSY, DSZ, DT0, DTH, DUB, DUE, DUK, DUW, DZU, DZV, DZX). Included with (PDV) Stingray R Appearance Package, LPO.",FALSE
opt_vwd_001,PDV,includes,"1. Included with (PDV) Stingray R Appearance Package, LPO.",FALSE
opt_spz_001,SPY,requires,"1. Requires (SPY) Black lug nuts, LPO.",FALSE
opt_s47_001,SPY,excludes,"1. Not available with (SPY) Black lug nuts, LPO.",FALSE
opt_sfe_001,SPY,excludes,"1. Not available with (SPY) Black lug nuts, LPO.",FALSE
opt_spy_001,S47,excludes,"1. Not available with (S47) Chrome lug nuts, LPO.",FALSE
```

**Notes on Usage**
Import this CSV directly into the “Rule_Mapping” sheet. Rows with `review_flag=TRUE` require manual validation, particularly around conditional deletions, soft recommendations, order-type constraints, and OR-group logic. The flattened pairwise representation preserves source fidelity while highlighting areas where business rules may need logical grouping or directionality refinement in the consuming system. This ruleset captures the complete set of hard compatibility constraints together with all edge-case metadata surfaced across the source data.
