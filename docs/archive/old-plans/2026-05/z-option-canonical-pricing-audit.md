# Z Option Canonical Pricing Audit

Read-only audit. No workbook cells or runtime artifacts were modified.

Classification note: direct candidates require one unique non-conditional candidate price. PDB/PDD/PDF and clear variable-combination evidence are deferred; trim/body-style/`Std on`/`Std with` evidence is conditional.

## Summary

| Model | Active option rows | Current nonblank prices | Direct candidates | Standard/zero | Conditional | Package/combo | Missing | Ambiguous |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Z06 | 239 | 0 | 107 | 0 | 22 | 3 | 107 | 0 |
| ZR1 | 203 | 0 | 81 | 0 | 18 | 0 | 104 | 0 |
| ZR1X | 204 | 0 | 82 | 0 | 18 | 0 | 104 | 0 |

## Recommended action counts

| Model | write_options_price | leave_blank_standard_or_included | defer_to_price_rules | defer_to_package_combo_design | needs_human_review |
|---|---:|---:|---:|---:|---:|
| Z06 | 107 | 0 | 22 | 3 | 107 |
| ZR1 | 81 | 0 | 18 | 0 | 104 |
| ZR1X | 82 | 0 | 18 | 0 | 104 |

## PDB / PDD / PDF check

- `opt_pdb_001` / `PDB`: `package_combo_price_candidate` → `defer_to_package_combo_design`
- `opt_pdd_001` / `PDD`: `package_combo_price_candidate` → `defer_to_package_combo_design`
- `opt_pdf_001` / `PDF`: `package_combo_price_candidate` → `defer_to_package_combo_design`

## Direct price candidates by model

### Z06 (107)

| Row | Option ID | RPO | Price | Name |
|---:|---|---|---:|---|
| 2 | `opt_b6p_001` | `B6P` | 1895 | Coupe Engine Appearance Package, includes carbon fiber trim, (D3V) engine lighting and (SL9) engine specification plaque, LPO |
| 3 | `opt_pdy_001` | `PDY` | 195 | LPO, Roadside Safety Package, includes (RYT) First Aid Kit, LPO and (S08) Highway Safety Kit, LPO, Genuine Corvette Accessory |
| 4 | `opt_zz3_001` | `ZZ3` | 1195 | Convertible Engine Appearance Package, includes window under tonneau cover, engine intake and (SL9) engine specification plaque, LPO |
| 5 | `opt_ryt_001` | `RYT` | 60 | LPO, First Aid Kit, Genuine Corvette Accessory |
| 6 | `opt_s08_001` | `S08` | 150 | LPO, Highway Safety Kit, Genuine Corvette Accessory |
| 12 | `opt_d30_001` | `D30` | 1495 | Color Combination Override, provides the opportunity to individualize vehicle appearance by overriding recommended restrictions to exterior, interior and seat belt color combinations |
| 15 | `opt_dth_001` | `DTH` | 1295 | Carbon Flash Metallic Full Length Dual Racing Stripes |
| 17 | `opt_eri_001` | `ERI` | 100 | Battery Protection Package |
| 23 | `opt_r8c_001` | `R8C` | 1695 | Corvette Museum Delivery, acknowledgement form required, includes (CFX) Corvette Museum logo plaque personalized with your name and VIN |
| 24 | `opt_sda_001` | `SDA` | 150 | LPO, Black recovery hook, Genuine Corvette Accessory |
| 25 | `opt_spy_001` | `SPY` | 320 | LPO, Black lug nuts, Genuine Corvette Accessory |
| 29 | `opt_z07_001` | `Z07` | 9500 | Z07 Performance Package, includes (J57) 4-wheel antilock, 4-wheel disc, carbon ceramic brakes with (J6D) Dark Gray Metallic-painted calipers, (FE7) Z07 suspension with Magnetic Selective Ride Control and (XFS) 275/30ZR20 front and 345/25ZR21 rear Michelin Pilot Sport Cup 2 R ultra performance tires; (J6D) Dark Gray Metallic-painted calipers can be upgraded at additional cost to one of the following painted caliper colors: (J6B) Blue, (J6F) Bright Red, (J6N) Edge Red, (J6L) Orange, or (J6E) Velocity Yellow |
| 31 | `opt_sl9_001` | `SL9` | 125 | LPO, Engine specification plaque, Genuine Corvette Accessory |
| 39 | `opt_dub_001` | `DUB` | 1295 | Sterling Silver Full Length Dual Racing Stripes |
| 40 | `opt_edu_001` | `EDU` | 995 | Exterior accents, Carbon Flash and body-color; body-color side vents and front splitter, Carbon Flash-painted rockers and front/rear grille accents |
| 41 | `opt_eyk_001` | `EYK` | 395 | Chrome Exterior Badge Package |
| 44 | `opt_j6f_001` | `J6F` | 795 | Calipers, Bright Red-painted |
| 45 | `opt_pin_001` | `PIN` | 5495 | Customer VIN ending reservation |
| 48 | `opt_sfz_001` | `SFZ` | 250 | LPO, Dark Stealth crossed flags emblems, front and rear on Z06 models, front and rear on Grand Sport, Z06, ZR1 and ZR1X models, Genuine Corvette Accessory |
| 49 | `opt_spz_001` | `SPZ` | 105 | LPO, Black wheel locks, Genuine Corvette Accessory |
| 50 | `opt_t0f_001` | `T0F` | 8995 | Carbon Fiber Aero Package, Carbon Flash-painted, includes high-wing, dive planes and (CFZ) Carbon Flash-painted carbon fiber ground effects |
| 55 | `opt_wub_001` | `WUB` | 1995 | NEW!Exhaust, quad center exit |
| 56 | `opt_r88_001` | `R88` | 695 | LPO, Illuminated crossed flags emblem, front, Genuine Corvette Accessory |
| 59 | `opt_5zv_001` | `5ZV` | 2075 | LPO, Three-Stanchion high wing spoiler, Carbon Flash Metallic-painted, Genuine Corvette Accessory |
| 60 | `opt_bv4_001` | `BV4` | 395 | Plaque, personalized, custom-made with your name or up to 24-character word or phrase limit and VIN |
| 61 | `opt_cfl_001` | `CFL` | 995 | NEW!Ground effects, extended front splitter |
| 63 | `opt_dt0_001` | `DT0` | 1295 | Competition Yellow Full Length Dual Racing Stripes |
| 65 | `opt_j6e_001` | `J6E` | 795 | Calipers, Velocity Yellow-painted |
| 67 | `opt_nwi_001` | `NWI` | 395 | NEW!Exhaust tips, bright, center, quad, exposed |
| 68 | `opt_pef_001` | `PEF` | 475 | LPO, Contoured Liner Protection Package, includes (CAV) contoured cargo area liners with Jake logo and (RIA) all-weather floor liners with Jake logo, Genuine Corvette Accessory |
| 69 | `opt_s47_001` | `S47` | 275 | LPO, Chrome lug nuts, Genuine Corvette Accessory |
| 70 | `opt_sbt_001` | `SBT` | 2525 | LPO, Dual roof, adds transparent removable roof panel and includes (SC7) roof panel storage pouch, Genuine Corvette Accessories |
| 74 | `opt_zyc_001` | `ZYC` | 295 | Carbon Flash Metallic-painted outside mirrors and spoiler (when equipped), includes (DRG) Carbon Flash Metallic-painted outside mirrors |
| 75 | `opt_ria_001` | `RIA` | 265 | LPO, All-weather floor liners with Jake logo, Genuine Corvette Accessory |
| 76 | `opt_sc7_001` | `SC7` | 195 | LPO, Roof panel storage pouch, Genuine Corvette Accessory |
| 77 | `opt_cav_001` | `CAV` | 230 | LPO, Contoured cargo area liners with Jake logo, Genuine Corvette Accessory |
| 78 | `opt_cfz_001` | `CFZ` | 3495 | Ground effects, carbon fiber, Carbon Flash-painted |
| 81 | `opt_duw_001` | `DUW` | 1295 | Edge Blue Full Length Dual Racing Stripes |
| 82 | `opt_j6n_001` | `J6N` | 795 | Calipers, Edge Red-painted |
| 84 | `opt_sfe_001` | `SFE` | 125 | LPO, Chrome wheel locks, Genuine Corvette Accessory |
| 88 | `opt_vtb_001` | `VTB` | 150 | LPO, Rear fascia/roof storage protector in Black with embroidered crossed flags logo, Genuine Corvette Accessory |
| 89 | `opt_vyw_001` | `VYW` | 275 | LPO, Floor mats, premium carpeted with Z06 badge emblem on Z06 models, Genuine Corvette Accessory |
| 92 | `opt_5zd_001` | `5ZD` | 250 | LPO, Carbon Flash wheel center caps with crossed flags logo, Genuine Corvette Accessory |
| 94 | `opt_dsy_001` | `DSY` | 1295 | Edge Orange Full Length Dual Racing Stripes |
| 96 | `opt_j6b_001` | `J6B` | 795 | Calipers, Blue-painted |
| 97 | `opt_roy_001` | `ROY` | 11995 | Wheels, 20" x 10" (50.8 cm x 25.4 cm) front and 21" x 13" (53.3 cm x 33 cm) rear Carbon Flash-painted carbon fiber |
| 98 | `opt_rwu_001` | `RWU` | 175 | LPO, Cargo area organizer, collapsible, Genuine Corvette Accessory |
| 99 | `opt_slk_001` | `SLK` | 1995 | LPO, Rear hatch strut bracket, Edge Red, Genuine Corvette Accessory |
| 103 | `opt_vwt_001` | `VWT` | 795 | LPO, Insect protection grille screen, Genuine Corvette Accessory |
| 104 | `opt_3m9_001` | `3M9` | 595 | Seat belt color, Yellow |
| 105 | `opt_5jr_001` | `5JR` | 1395 | LPO, Outside mirror covers in visible Carbon Fiber, includes (DRG) Carbon Flash Metallic-painted outside mirrors, Genuine Corvette Accessory |
| 106 | `opt_5zc_001` | `5ZC` | 250 | LPO, Jake logo wheel center caps. Genuine Corvette Accessory |
| 109 | `opt_dsz_001` | `DSZ` | 1295 | Edge Red Full Length Dual Racing Stripes |
| 111 | `opt_roz_001` | `ROZ` | 13995 | Wheels, 20" x 10" (50.8 cm x 25.4 cm) front and 21" x 13" (53.3 cm x 33 cm) rear visible carbon fiber |
| 112 | `opt_sln_001` | `SLN` | 2895 | LPO, Visible carbon fiber engine cross brace with Jake logo, Genuine Corvette Accessory |
| 114 | `opt_w2d_001` | `W2D` | 125 | LPO, Cargo net set, Genuine Corvette Accessory |
| 118 | `opt_dpb_001` | `DPB` | 1295 | Carbon Flash with Blue accent Full Length Dual Racing Stripes |
| 120 | `opt_j6l_001` | `J6L` | 795 | Calipers, Orange-painted |
| 121 | `opt_rwh_001` | `RWH` | 495 | LPO, Premium indoor car cover, Black with crossed flags logo, Genuine Corvette Accessory |
| 122 | `opt_s2l_001` | `S2L` | 1695 | LPO, Set of premium leather weekend/travel bags, Genuine Corvette Accessory |
| 123 | `opt_stz_001` | `STZ` | 15500 | Wheels, 20" x 10" (50.8 cm x 25.4 cm) front and 21" x 13" (53.3 cm x 33 cm) rear visible carbon fiber with Red stripe |
| 125 | `opt_vup_001` | `VUP` | 575 | LPO, Engine Bay closeout graphics, Genuine Corvette Accessory |
| 127 | `opt_wkr_001` | `WKR` | 1275 | LPO, Premium indoor car cover, GT3.R, fully rendered, Genuine Corvette Accessory |
| 128 | `opt_rwj_001` | `RWJ` | 495 | LPO, Premium outdoor car cover, Gray with crossed flags logo and Corvette silhouette, Genuine Corvette Accessory |
| 129 | `opt_aup_001` | `AUP` | 350 | Seats, mixed, driver Competition Sport bucket, passenger GT2 bucket |
| 130 | `opt_dpg_001` | `DPG` | 1295 | Carbon Flash with Orange accent Full Length Dual Racing Stripes |
| 134 | `opt_rin_001` | `RIN` | 440 | LPO, Rear Corvette script badge in Arctic White, Genuine Corvette Accessory |
| 135 | `opt_sxb_001` | `SXB` | 2095 | LPO, Suede frunk and trunk compartment liner, Black, Genuine Corvette Accessory |
| 137 | `opt_sl8_001` | `SL8` | 495 | LPO, Rear Corvette script badge in Edge Red, Genuine Corvette Accessory |
| 138 | `opt_sxr_001` | `SXR` | 2095 | LPO, Suede frunk and trunk compartment liner, Adrenaline Red, Genuine Corvette Accessory |
| 139 | `opt_rik_001` | `RIK` | 395 | LPO, Rear Corvette script badge in Torch Red, Genuine Corvette Accessory |
| 140 | `opt_sxt_001` | `SXT` | 2695 | LPO, Suede frunk and trunk compartment liner, Natural, Genuine Corvette Accessory |
| 141 | `opt_dpl_001` | `DPL` | 1295 | Carbon Flash with Red accent Full Length Dual Racing Stripes |
| 142 | `opt_sig_001` | `SIG` | 425 | LPO, Spoiler extension, clear smoked center bridge with Jake logo, Genuine Corvette Accessory |
| 145 | `opt_dpt_001` | `DPT` | 1295 | Carbon Flash with Silver accent Full Length Dual Racing Stripes |
| 148 | `opt_dpc_001` | `DPC` | 1295 | Carbon Flash with Yellow accent Full Length Dual Racing Stripes |
| 150 | `opt_duk_001` | `DUK` | 1295 | Asymmetrical Edge Red/Carbon Flash Full Length Dual Racing Stripes |
| 154 | `opt_due_001` | `DUE` | 1295 | NEW!Asymmetrical Santorini Blue/Carbon Flash Full Length Dual Racing Stripes |
| 156 | `opt_dzu_001` | `DZU` | 595 | Carbon Flash/Competition Yellow Stinger Stripe |
| 158 | `opt_dzx_001` | `DZX` | 595 | Carbon Flash/Edge Red Stinger Stripe |
| 160 | `opt_dzv_001` | `DZV` | 595 | Carbon Flash/Midnight Silver Stinger Stripe |
| 162 | `opt_sht_001` | `SHT` | 495 | LPO, Jake hood graphic with Tech Bronze accent, Genuine Corvette Accessory |
| 164 | `opt_vpo_001` | `VPO` | 575 | LPO, Jake C8.R rear hash graphic with Tech Bronze accent, Genuine Corvette Accessory |
| 194 | `opt_36s_001` | `36S` | 495 | Competition Yellow custom leather stitch, includes seats, instrument panel, doors and console |
| 195 | `opt_37s_001` | `37S` | 495 | Santorini Blue custom leather stitch, includes seats, instrument panel, doors and console |
| 196 | `opt_38s_001` | `38S` | 495 | Adrenaline Red custom leather stitch, includes seats, instrument panel, doors and console |
| 197 | `opt_5dh_001` | `5DH` | 4450 | LPO, 20" x 10" (50.8 cm x 25.4 cm) front and 21" x 13" (53.3 cm x 33 cm) rear Spider design, Satin Graphite forged aluminum with Red stripe wheels. Includes Black lug nuts and Black wheel locks. Accessory LPO wheels are a second set of wheels. Please ensure customer desires 2 sets of wheels before ordering. Accessory wheels do not include additional wheels caps, factory wheels caps may be reused, or additional wheel caps may be purchased. Genuine Corvette Accessory |
| 198 | `opt_5dk_001` | `5DK` | 4450 | LPO, 20" x 10" (50.8 cm x 25.4 cm) front and 21" x 13" (53.3 cm x 33 cm) rear Spider design, Tech Bronze forged aluminum wheels. Includes Black lug nuts, Black wheel locks, and Tech Bronze wheel center caps. Accessory LPO wheels are a second set of wheels. Please ensure customer desires 2 sets of wheels before ordering. Genuine Corvette Accessory |
| 202 | `opt_efy_001` | `EFY` | 995 | Exterior accents, body-color, side vents, rockers, splitter and front/rear grille accents |
| 211 | `opt_pbc_001` | `PBC` | 9995 | Customer Engine Build Program |
| 212 | `opt_pcz_001` | `PCZ` | 5295 | LPO, Tech Bronze Accent Package, includes (5DK) 20" front/21" rear Spider design, Tech Bronze forged aluminum wheels LPO, (SFZ) Dark Stealth crossed flags emblem LPO, (SHT) Jake hood graphic with Tech Bronze accent LPO and (VPO) Jake C8.R rear hash graphic with Tech Bronze accent LPO , Genuine Corvette Accessories |
| 213 | `opt_pda_001` | `PDA` | 950 | LPO, Jake C8.R Graphics Package, includes (SNE) Jake hood graphic, LPO and (VPW) Jake C8.R rear hash graphic, LPO, Genuine Corvette Accessories |
| 218 | `opt_rou_001` | `ROU` | 995 | Wheels, 20" x 10" (50.8 cm x 25.4 cm) front and 21" x 13" (53.3 cm x 33 cm) rear Pearl Nickel forged aluminum |
| 219 | `opt_rox_001` | `ROX` | 995 | Wheels, 20" x 10" (50.8 cm x 25.4 cm) front and 21" x 13" (53.3 cm x 33 cm) rear Carbon Flash with machined edge forged aluminum |
| 220 | `opt_rxi_001` | `RXI` | 2495 | LPO, LT6 engine cover in visible carbon fiber, Genuine Corvette Accessory |
| 222 | `opt_sg1_001` | `SG1` | 325 | LPO, Z06 badges in Edge Red, Genuine Corvette Accessory |
| 223 | `opt_sne_001` | `SNE` | 595 | LPO, Jake hood graphic |
| 224 | `opt_soa_001` | `SOA` | 1095 | Wheels, 20" x 10" (50.8 cm x 25.4 cm) front and 21" x 13" (53.3 cm x 33 cm) rear Spider design, Black forged aluminum |
| 226 | `opt_som_001` | `SOM` | 1495 | Wheels, 20" x 10" (50.8 cm x 25.4 cm) front and 21" x 13" (53.3 cm x 33 cm) rear bright polished forged aluminum |
| 227 | `opt_son_001` | `SON` | 1095 | Wheels, 20" x 10" (50.8 cm x 25.4 cm) front and 21" x 13" (53.3 cm x 33 cm) rear Gloss Black forged aluminum |
| 228 | `opt_srk_001` | `SRK` | 995 | Wheels, 20" x 10" (50.8 cm x 25.4 cm) front and 21" x 13" (53.3 cm x 33 cm) rear 10-spoke, Pearl Nickel forged aluminum |
| 229 | `opt_srn_001` | `SRN` | 1095 | Wheels, 20" x 10" (50.8 cm x 25.4 cm) front and 21" x 13" (53.3 cm x 33 cm) rear 10-spoke, Gloss Black forged aluminum |
| 230 | `opt_stx_001` | `STX` | 1995 | Wheels, 20" x 10" (50.8 cm x 25.4 cm) front and 21" x 13" (53.3 cm x 33 cm) rear 10-spoke, Bright Polished forged aluminum with Carbon Flash-painted pockets |
| 231 | `opt_t0g_001` | `T0G` | 10995 | Carbon Fiber Aero Package, visible, includes high-wing, dive planes and (CFV) visible carbon fiber ground effects |
| 237 | `opt_vk3_001` | `VK3` | 40 | License plate bracket, front |
| 238 | `opt_vpw_001` | `VPW` | 575 | LPO, Jake C8.R rear hash graphic, Genuine Corvette Accessory |
| 240 | `opt_wks_001` | `WKS` | 495 | LPO, Premium indoor car cover, Galvanized Cool with Z06 logo, Genuine Corvette Accessory |

### ZR1 (81)

| Row | Option ID | RPO | Price | Name |
|---:|---|---|---:|---|
| 2 | `opt_b6p_001` | `B6P` | 1895 | Coupe Engine Appearance Package, includes carbon fiber trim and (SL9) engine specification plaque, LPO |
| 3 | `opt_pdy_001` | `PDY` | 195 | LPO, Roadside Safety Package, includes (RYT) First Aid Kit, LPO and (S08) Highway Safety Kit, LPO, Genuine Corvette Accessory |
| 4 | `opt_zz3_001` | `ZZ3` | 1195 | Convertible Engine Appearance Package, includes window under tonneau cover, engine intake and (SL9) engine specification plaque, LPO |
| 5 | `opt_ryt_001` | `RYT` | 60 | LPO, First Aid Kit, Genuine Corvette Accessory |
| 6 | `opt_s08_001` | `S08` | 150 | LPO, Highway Safety Kit, Genuine Corvette Accessory |
| 11 | `opt_d30_001` | `D30` | 1495 | Color Combination Override, provides the opportunity to individualize vehicle appearance by overriding recommended restrictions to exterior, interior and seat belt color combinations |
| 14 | `opt_dth_001` | `DTH` | 1295 | Carbon Flash Metallic Full Length Dual Racing Stripes |
| 16 | `opt_eri_001` | `ERI` | 100 | Battery Protection Package |
| 20 | `opt_r8c_001` | `R8C` | 1695 | Corvette Museum Delivery, acknowledgement form required, includes (CFX) Corvette Museum logo plaque personalized with your name and VIN |
| 21 | `opt_sda_001` | `SDA` | 150 | LPO, Black recovery hook, Genuine Corvette Accessory |
| 22 | `opt_spy_001` | `SPY` | 320 | LPO, Black lug nuts, Genuine Corvette Accessory |
| 28 | `opt_sl9_001` | `SL9` | 125 | LPO, Engine specification plaque, Genuine Corvette Accessory |
| 33 | `opt_dub_001` | `DUB` | 1295 | Sterling Silver Full Length Dual Racing Stripes |
| 34 | `opt_eyk_001` | `EYK` | 395 | Chrome Exterior Badge Package |
| 36 | `opt_j6f_001` | `J6F` | 795 | Calipers, Bright Red-painted |
| 37 | `opt_pin_001` | `PIN` | 5495 | Customer VIN ending reservation |
| 40 | `opt_sfz_001` | `SFZ` | 250 | LPO, Dark Stealth crossed flags emblems, front and rear on Z06 models, front and rear on Grand Sport, Z06, ZR1 and ZR1X models, Genuine Corvette Accessory |
| 41 | `opt_spz_001` | `SPZ` | 105 | LPO, Black wheel locks, Genuine Corvette Accessory |
| 46 | `opt_wub_001` | `WUB` | 1995 | NEW!Exhaust, quad center exit |
| 47 | `opt_r88_001` | `R88` | 695 | LPO, Illuminated crossed flags emblem, front, Genuine Corvette Accessory |
| 50 | `opt_bv4_001` | `BV4` | 395 | Plaque, personalized, custom-made with your name or up to 24-character word or phrase limit and VIN |
| 52 | `opt_dt0_001` | `DT0` | 1295 | Competition Yellow Full Length Dual Racing Stripes |
| 54 | `opt_j6e_001` | `J6E` | 795 | Calipers, Velocity Yellow-painted |
| 56 | `opt_nwi_001` | `NWI` | 395 | NEW!Exhaust tips, bright, center, quad, exposed |
| 57 | `opt_pef_001` | `PEF` | 475 | LPO, Contoured Liner Protection Package, includes (CAV) contoured trunk cargo area liner with Jake logo and (RIA) all-weather floor liners with Jake logo, Genuine Corvette Accessory |
| 58 | `opt_s47_001` | `S47` | 275 | LPO, Chrome lug nuts, Genuine Corvette Accessory |
| 59 | `opt_sbt_001` | `SBT` | 2525 | LPO, Dual roof, adds transparent removable roof panel and includes (SC7) roof panel storage pouch, Genuine Corvette Accessories |
| 63 | `opt_zyc_001` | `ZYC` | 295 | Carbon Flash Metallic-painted outside mirrors and spoiler (when equipped with T0E standard spoiler), includes (DRG) Carbon Flash Metallic-painted outside mirrors |
| 64 | `opt_ria_001` | `RIA` | 265 | LPO, All-weather floor liners with Jake logo, Genuine Corvette Accessory |
| 65 | `opt_sc7_001` | `SC7` | 195 | LPO, Roof panel storage pouch, Genuine Corvette Accessory |
| 66 | `opt_cav_001` | `CAV` | 230 | LPO, Contoured cargo area liner with Jake logo, Genuine Corvette Accessory |
| 69 | `opt_duw_001` | `DUW` | 1295 | Edge Blue Full Length Dual Racing Stripes |
| 70 | `opt_j6n_001` | `J6N` | 795 | Calipers, Edge Red-painted |
| 72 | `opt_sfe_001` | `SFE` | 125 | LPO, Chrome wheel locks, Genuine Corvette Accessory |
| 76 | `opt_vtb_001` | `VTB` | 150 | LPO, Rear fascia/roof storage protector in Black with embroidered crossed flags logo, Genuine Corvette Accessory |
| 77 | `opt_vyw_001` | `VYW` | 275 | LPO, Floor mats, premium carpeted with car silhouette logo on Stingray, Grand Sport, ZR1 and ZR1X models, Genuine Corvette Accessory |
| 80 | `opt_5zd_001` | `5ZD` | 250 | LPO, Carbon Flash wheel center caps with crossed flags logo, Genuine Corvette Accessory |
| 81 | `opt_dsy_001` | `DSY` | 1295 | Edge Orange Full Length Dual Racing Stripes |
| 83 | `opt_j6b_001` | `J6B` | 795 | Calipers, Blue-painted |
| 84 | `opt_rwu_001` | `RWU` | 175 | LPO, Cargo area organizer, collapsible, Genuine Corvette Accessory |
| 85 | `opt_slk_001` | `SLK` | 1995 | LPO, Rear hatch strut bracket, Edge Red, Genuine Corvette Accessory |
| 89 | `opt_vwt_001` | `VWT` | 795 | LPO, Insect protection grille screen, Genuine Corvette Accessory |
| 90 | `opt_3m9_001` | `3M9` | 595 | Seat belt color, Yellow |
| 91 | `opt_5jr_001` | `5JR` | 1395 | LPO, Outside mirror covers in visible Carbon Fiber, includes (DRG) Carbon Flash Metallic-painted outside mirrors, Genuine Corvette Accessory |
| 92 | `opt_5zc_001` | `5ZC` | 250 | LPO, Jake logo wheel center caps. Genuine Corvette Accessory |
| 94 | `opt_dsz_001` | `DSZ` | 1295 | Edge Red Full Length Dual Racing Stripes |
| 96 | `opt_sln_001` | `SLN` | 2895 | LPO, Visible carbon fiber engine cross brace with Jake logo, Genuine Corvette Accessory |
| 98 | `opt_w2d_001` | `W2D` | 125 | LPO, Cargo net set, Genuine Corvette Accessory |
| 101 | `opt_dpb_001` | `DPB` | 1295 | Carbon Flash with Blue accent Full Length Dual Racing Stripes |
| 103 | `opt_j6l_001` | `J6L` | 795 | Calipers, Orange-painted |
| 104 | `opt_rwh_001` | `RWH` | 495 | LPO, Premium indoor car cover, Black with crossed flags logo, Genuine Corvette Accessory |
| 105 | `opt_s2l_001` | `S2L` | 1695 | LPO, Set of premium leather weekend/travel bags, Genuine Corvette Accessory |
| 108 | `opt_wkr_001` | `WKR` | 1275 | LPO, Premium indoor car cover, GT3.R, fully rendered, Genuine Corvette Accessory |
| 109 | `opt_rwj_001` | `RWJ` | 495 | LPO, Premium outdoor car cover, Gray with crossed flags logo and Corvette silhouette, Genuine Corvette Accessory |
| 110 | `opt_aup_001` | `AUP` | 350 | Seats, mixed, driver Competition Sport bucket, passenger GT2 bucket |
| 111 | `opt_dpg_001` | `DPG` | 1295 | Carbon Flash with Orange accent Full Length Dual Racing Stripes |
| 115 | `opt_rin_001` | `RIN` | 440 | LPO, Rear Corvette script badge in Arctic White, Genuine Corvette Accessory |
| 116 | `opt_sxb_001` | `SXB` | 2095 | LPO, Suede trunk compartment liner, Black, Genuine Corvette Accessory |
| 118 | `opt_sl8_001` | `SL8` | 495 | LPO, Rear Corvette script badge in Edge Red, Genuine Corvette Accessory |
| 119 | `opt_sxr_001` | `SXR` | 2095 | LPO, Suede trunk compartment liner, Adrenaline Red, Genuine Corvette Accessory |
| 120 | `opt_rik_001` | `RIK` | 395 | LPO, Rear Corvette script badge in Torch Red, Genuine Corvette Accessory |
| 121 | `opt_sxt_001` | `SXT` | 2695 | LPO, Suede trunk compartment liner, Natural, Genuine Corvette Accessory |
| 122 | `opt_dpl_001` | `DPL` | 1295 | Carbon Flash with Red accent Full Length Dual Racing Stripes |
| 123 | `opt_sig_001` | `SIG` | 425 | LPO, Spoiler extension, clear smoked center bridge with Jake logo, Genuine Corvette Accessory |
| 126 | `opt_dpt_001` | `DPT` | 1295 | Carbon Flash with Silver accent Full Length Dual Racing Stripes |
| 129 | `opt_dpc_001` | `DPC` | 1295 | Carbon Flash with Yellow accent Full Length Dual Racing Stripes |
| 131 | `opt_duk_001` | `DUK` | 1295 | Asymmetrical Edge Red/Carbon Flash Full Length Dual Racing Stripes |
| 135 | `opt_due_001` | `DUE` | 1295 | NEW!Asymmetrical Santorini Blue/Carbon Flash Full Length Dual Racing Stripes |
| 144 | `opt_36s_001` | `36S` | 495 | Competition Yellow custom leather stitch, includes seats, instrument panel, doors and console |
| 145 | `opt_37s_001` | `37S` | 495 | Santorini Blue custom leather stitch, includes seats, instrument panel, doors and console |
| 146 | `opt_38s_001` | `38S` | 495 | Adrenaline Red custom leather stitch, includes seats, instrument panel, doors and console |
| 175 | `opt_etv_001` | `ETV` | 995 | Exterior trim, carbon fiber split window trim, painted body-color |
| 183 | `opt_j6o_001` | `J6O` | 795 | Calipers, Bronze-painted |
| 189 | `opt_pbc_001` | `PBC` | 9995 | Customer Engine Build Program |
| 191 | `opt_sb9_001` | `SB9` | 895 | NEW!LPO, Hood and Roof Decal Package, Genuine Corvette Accessory |
| 192 | `opt_sof_001` | `SOF` | 1495 | Wheels, 20" x 10" (50.8 cm x 25.4 cm) front and 21" x 13" (53.3 cm x 33 cm) rear 20-spoke, Edge Blue-painted forged aluminum |
| 193 | `opt_sog_001` | `SOG` | 1995 | Wheels, 20" x 10" (50.8 cm x 25.4 cm) front and 21" x 13" (53.3 cm x 33 cm) rear 20-spoke, Carbon Flash-painted forged aluminum |
| 194 | `opt_soh_001` | `SOH` | 1995 | Wheels, 20" x 10" (50.8 cm x 25.4 cm) front and 21" x 13" (53.3 cm x 33 cm) rear 20-spoke, Bright machined forged aluminum |
| 196 | `opt_su1_001` | `SU1` | 15995 | Wheels, 20" x 10" (50.8 cm x 25.4 cm) front and 21" x 13" (53.3 cm x 33 cm) rear 10-spoke, visible carbon fiber |
| 197 | `opt_tom_001` | `TOM` | 12995 | ZR1 Carbon Fiber Aero Package, visible carbon fiber, includes carbon fiber high-wing spoiler, dive planes, and tall hood spoiler |
| 203 | `opt_vk3_001` | `VK3` | 40 | License plate bracket, front |

### ZR1X (82)

| Row | Option ID | RPO | Price | Name |
|---:|---|---|---:|---|
| 2 | `opt_b6p_001` | `B6P` | 1895 | Coupe Engine Appearance Package, includes carbon fiber trim and (SL9) engine specification plaque, LPO |
| 3 | `opt_pdy_001` | `PDY` | 195 | LPO, Roadside Safety Package, includes (RYT) First Aid Kit, LPO and (S08) Highway Safety Kit, LPO, Genuine Corvette Accessory |
| 4 | `opt_zz3_001` | `ZZ3` | 1195 | Convertible Engine Appearance Package, includes window under tonneau cover, engine intake and (SL9) engine specification plaque, LPO |
| 5 | `opt_ryt_001` | `RYT` | 60 | LPO, First Aid Kit, Genuine Corvette Accessory |
| 6 | `opt_s08_001` | `S08` | 150 | LPO, Highway Safety Kit, Genuine Corvette Accessory |
| 11 | `opt_d30_001` | `D30` | 1495 | Color Combination Override, provides the opportunity to individualize vehicle appearance by overriding recommended restrictions to exterior, interior and seat belt color combinations |
| 14 | `opt_dth_001` | `DTH` | 1295 | Carbon Flash Metallic Full Length Dual Racing Stripes |
| 16 | `opt_eri_001` | `ERI` | 100 | Battery Protection Package |
| 20 | `opt_r8c_001` | `R8C` | 1695 | Corvette Museum Delivery, acknowledgement form required, includes (CFX) Corvette Museum logo plaque personalized with your name and VIN |
| 21 | `opt_sda_001` | `SDA` | 150 | LPO, Black recovery hook, Genuine Corvette Accessory |
| 22 | `opt_spy_001` | `SPY` | 320 | LPO, Black lug nuts, Genuine Corvette Accessory |
| 28 | `opt_sl9_001` | `SL9` | 125 | LPO, Engine specification plaque, Genuine Corvette Accessory |
| 33 | `opt_dub_001` | `DUB` | 1295 | Sterling Silver Full Length Dual Racing Stripes |
| 34 | `opt_eyk_001` | `EYK` | 395 | Chrome Exterior Badge Package |
| 36 | `opt_j6f_001` | `J6F` | 795 | Calipers, Bright Red-painted |
| 37 | `opt_pin_001` | `PIN` | 5495 | Customer VIN ending reservation |
| 40 | `opt_sfz_001` | `SFZ` | 250 | LPO, Dark Stealth crossed flags emblems, front and rear on Z06 models, front and rear on Grand Sport, Z06, ZR1 and ZR1X models, Genuine Corvette Accessory |
| 41 | `opt_spz_001` | `SPZ` | 105 | LPO, Black wheel locks, Genuine Corvette Accessory |
| 46 | `opt_wub_001` | `WUB` | 1995 | NEW!Exhaust, quad center exit |
| 47 | `opt_r88_001` | `R88` | 695 | LPO, Illuminated crossed flags emblem, front, Genuine Corvette Accessory |
| 50 | `opt_bv4_001` | `BV4` | 395 | Plaque, personalized, custom-made with your name or up to 24-character word or phrase limit and VIN |
| 52 | `opt_dt0_001` | `DT0` | 1295 | Competition Yellow Full Length Dual Racing Stripes |
| 54 | `opt_j6e_001` | `J6E` | 795 | Calipers, Velocity Yellow-painted |
| 56 | `opt_nwi_001` | `NWI` | 395 | NEW!Exhaust tips, bright, center, quad, exposed |
| 57 | `opt_pef_001` | `PEF` | 475 | LPO, Contoured Liner Protection Package, includes (CAV) contoured trunk cargo area liner with Jake logo and (RIA) all-weather floor liners with Jake logo, Genuine Corvette Accessory |
| 58 | `opt_s47_001` | `S47` | 275 | LPO, Chrome lug nuts, Genuine Corvette Accessory |
| 59 | `opt_sbt_001` | `SBT` | 2525 | LPO, Dual roof, adds transparent removable roof panel and includes (SC7) roof panel storage pouch, Genuine Corvette Accessories |
| 63 | `opt_zyc_001` | `ZYC` | 295 | Carbon Flash Metallic-painted outside mirrors and spoiler (when equipped with T0E standard spoiler), includes (DRG) Carbon Flash Metallic-painted outside mirrors |
| 64 | `opt_ria_001` | `RIA` | 265 | LPO, All-weather floor liners with Jake logo, Genuine Corvette Accessory |
| 65 | `opt_sc7_001` | `SC7` | 195 | LPO, Roof panel storage pouch, Genuine Corvette Accessory |
| 66 | `opt_cav_001` | `CAV` | 230 | LPO, Contoured cargo area liner with Jake logo, Genuine Corvette Accessory |
| 69 | `opt_duw_001` | `DUW` | 1295 | Edge Blue Full Length Dual Racing Stripes |
| 70 | `opt_j6n_001` | `J6N` | 795 | Calipers, Edge Red-painted |
| 72 | `opt_sfe_001` | `SFE` | 125 | LPO, Chrome wheel locks, Genuine Corvette Accessory |
| 76 | `opt_vtb_001` | `VTB` | 150 | LPO, Rear fascia/roof storage protector in Black with embroidered crossed flags logo, Genuine Corvette Accessory |
| 77 | `opt_vyw_001` | `VYW` | 275 | LPO, Floor mats, premium carpeted with car silhouette logo on Stingray, Grand Sport, ZR1 and ZR1X models, Genuine Corvette Accessory |
| 80 | `opt_5zd_001` | `5ZD` | 250 | LPO, Carbon Flash wheel center caps with crossed flags logo, Genuine Corvette Accessory |
| 81 | `opt_dsy_001` | `DSY` | 1295 | Edge Orange Full Length Dual Racing Stripes |
| 83 | `opt_j6b_001` | `J6B` | 795 | Calipers, Blue-painted |
| 84 | `opt_rwu_001` | `RWU` | 175 | LPO, Cargo area organizer, collapsible, Genuine Corvette Accessory |
| 85 | `opt_slk_001` | `SLK` | 1995 | LPO, Rear hatch strut bracket, Edge Red, Genuine Corvette Accessory |
| 89 | `opt_vwt_001` | `VWT` | 795 | LPO, Insect protection grille screen, Genuine Corvette Accessory |
| 90 | `opt_3m9_001` | `3M9` | 595 | Seat belt color, Yellow |
| 91 | `opt_5jr_001` | `5JR` | 1395 | LPO, Outside mirror covers in visible Carbon Fiber, includes (DRG) Carbon Flash Metallic-painted outside mirrors, Genuine Corvette Accessory |
| 92 | `opt_5zc_001` | `5ZC` | 250 | LPO, Jake logo wheel center caps. Genuine Corvette Accessory |
| 94 | `opt_dsz_001` | `DSZ` | 1295 | Edge Red Full Length Dual Racing Stripes |
| 96 | `opt_sln_001` | `SLN` | 2895 | LPO, Visible carbon fiber engine cross brace with Jake logo, Genuine Corvette Accessory |
| 98 | `opt_w2d_001` | `W2D` | 125 | LPO, Cargo net set, Genuine Corvette Accessory |
| 101 | `opt_dpb_001` | `DPB` | 1295 | Carbon Flash with Blue accent Full Length Dual Racing Stripes |
| 103 | `opt_j6l_001` | `J6L` | 795 | Calipers, Orange-painted |
| 104 | `opt_rwh_001` | `RWH` | 495 | LPO, Premium indoor car cover, Black with crossed flags logo, Genuine Corvette Accessory |
| 105 | `opt_s2l_001` | `S2L` | 1695 | LPO, Set of premium leather weekend/travel bags, Genuine Corvette Accessory |
| 108 | `opt_wkr_001` | `WKR` | 1275 | LPO, Premium indoor car cover, GT3.R, fully rendered, Genuine Corvette Accessory |
| 109 | `opt_rwj_001` | `RWJ` | 495 | LPO, Premium outdoor car cover, Gray with crossed flags logo and Corvette silhouette, Genuine Corvette Accessory |
| 110 | `opt_aup_001` | `AUP` | 350 | Seats, mixed, driver Competition Sport bucket, passenger GT2 bucket |
| 111 | `opt_dpg_001` | `DPG` | 1295 | Carbon Flash with Orange accent Full Length Dual Racing Stripes |
| 115 | `opt_rin_001` | `RIN` | 440 | LPO, Rear Corvette script badge in Arctic White, Genuine Corvette Accessory |
| 116 | `opt_sxb_001` | `SXB` | 2095 | LPO, Suede trunk compartment liner, Black, Genuine Corvette Accessory |
| 118 | `opt_sl8_001` | `SL8` | 495 | LPO, Rear Corvette script badge in Edge Red, Genuine Corvette Accessory |
| 119 | `opt_sxr_001` | `SXR` | 2095 | LPO, Suede trunk compartment liner, Adrenaline Red, Genuine Corvette Accessory |
| 120 | `opt_rik_001` | `RIK` | 395 | LPO, Rear Corvette script badge in Torch Red, Genuine Corvette Accessory |
| 121 | `opt_sxt_001` | `SXT` | 2695 | LPO, Suede trunk compartment liner, Natural, Genuine Corvette Accessory |
| 122 | `opt_dpl_001` | `DPL` | 1295 | Carbon Flash with Red accent Full Length Dual Racing Stripes |
| 123 | `opt_sig_001` | `SIG` | 425 | LPO, Spoiler extension, clear smoked center bridge with Jake logo, Genuine Corvette Accessory |
| 126 | `opt_dpt_001` | `DPT` | 1295 | Carbon Flash with Silver accent Full Length Dual Racing Stripes |
| 129 | `opt_dpc_001` | `DPC` | 1295 | Carbon Flash with Yellow accent Full Length Dual Racing Stripes |
| 131 | `opt_duk_001` | `DUK` | 1295 | Asymmetrical Edge Red/Carbon Flash Full Length Dual Racing Stripes |
| 135 | `opt_due_001` | `DUE` | 1295 | NEW!Asymmetrical Santorini Blue/Carbon Flash Full Length Dual Racing Stripes |
| 144 | `opt_36s_001` | `36S` | 495 | Competition Yellow custom leather stitch, includes seats, instrument panel, doors and console |
| 145 | `opt_37s_001` | `37S` | 495 | Santorini Blue custom leather stitch, includes seats, instrument panel, doors and console |
| 146 | `opt_38s_001` | `38S` | 495 | Adrenaline Red custom leather stitch, includes seats, instrument panel, doors and console |
| 174 | `opt_dtb_001` | `DTB` | 1295 | Electric Blue Full Length Dual Racing Stripes |
| 176 | `opt_etv_001` | `ETV` | 995 | Exterior trim, carbon fiber split window trim, painted body-color |
| 184 | `opt_j6o_001` | `J6O` | 795 | Calipers, Bronze-painted |
| 190 | `opt_pbc_001` | `PBC` | 9995 | Customer Engine Build Program |
| 192 | `opt_sb9_001` | `SB9` | 895 | NEW!LPO, Hood and Roof Decal Package, Genuine Corvette Accessory |
| 193 | `opt_sof_001` | `SOF` | 1495 | Wheels, 20" x 10" (50.8 cm x 25.4 cm) front and 21" x 13" (53.3 cm x 33 cm) rear 20-spoke, Edge Blue-painted forged aluminum |
| 194 | `opt_sog_001` | `SOG` | 1995 | Wheels, 20" x 10" (50.8 cm x 25.4 cm) front and 21" x 13" (53.3 cm x 33 cm) rear 20-spoke, Carbon Flash-painted forged aluminum |
| 195 | `opt_soh_001` | `SOH` | 1995 | Wheels, 20" x 10" (50.8 cm x 25.4 cm) front and 21" x 13" (53.3 cm x 33 cm) rear 20-spoke, Bright machined forged aluminum |
| 197 | `opt_su1_001` | `SU1` | 15995 | Wheels, 20" x 10" (50.8 cm x 25.4 cm) front and 21" x 13" (53.3 cm x 33 cm) rear 10-spoke, visible carbon fiber |
| 198 | `opt_tom_002` | `TOM` | 12995 | ZR1X Carbon Fiber Aero Package, visible carbon fiber, includes carbon fiber high-wing spoiler, dive planes, and tall hood spoiler |
| 204 | `opt_vk3_001` | `VK3` | 40 | License plate bracket, front |


## Artifacts

- Matrix CSV: `.hermes/plans/z-option-canonical-pricing-matrix.csv`
- Full JSON: `.hermes/plans/z-option-canonical-pricing-audit.json`
