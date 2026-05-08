# Pass 126 Migration Status Report

Generated from the current Stingray shadow/control-plane data. This is an audit artifact only; it does not switch sources, apply ledger decisions, migrate rows, or change runtime behavior.

## Definitions

- CSV-owned/projected = currently emitted/owned by the shadow CSV migration package.
- Production-owned/not-projected = still coming from the old generated production data.
- Production-owned/not-projected does not mean missing or wrong. It means the item has not been moved into CSV ownership yet; it may be intentionally deferred, out of current scope, or still waiting for review.
- Current guarded dependencies = active structured references currently protected by the manifest.
- Manifest-only preservation = preservation rows that are valid but not currently part of the active structured-reference guarded set.

## Summary
| Metric | Count |
| --- | --- |
| CSV-owned/projected RPO rows | 68 |
| Production-owned/not-projected RPO rows | 147 |
| Active production choice RPO rows | 215 |
| Active preserved cross-boundary manifest rows | 122 |
| Current guarded structured-reference dependencies | 43 |
| Current guarded manifest rows backing them | 39 |
| Manifest-only preservation rows | 83 |
| Manifest-only preservation groups | 78 |
| Invalid preserved rows | 0 |

## CSV-Owned / Projected By Category And Section

| Category | Section | RPO count | Example labels |
| --- | --- | --- | --- |
| Exterior | Badges | 1 | EYK — Chrome Exterior Badge Package |
| Exterior | Exterior Accents | 1 | EDU — Carbon Flash and body-color accents |
| Exterior | Roof | 4 | C2Z — Roof panel; CC3 — Roof panel; D84 — Convertible top; D86 — Convertible top |
| Exterior | Stripes | 5 | SB7 — LPO, Corvette Racing Themed Graphics Package with Jake and Stingray R logos; SHQ — LPO, Fender hash stripes; SHT — LPO, Jake hood graphic with Tech Bronze accent; SHW — LPO, Fender hash stripes; SNG — LPO, Fender hash stripes |
| Exterior \| Standard Equipment | Badges \| Standard Options | 1 | EYT — Carbon Flash Exterior Badge Package |
| Exterior \| Standard Equipment | Roof \| Standard Options | 2 | CF7 — Roof panel; CM9 — Convertible top |
| Interior | LPO Interior | 14 | CAV — LPO, Contoured cargo area liners with Jake logo; PDY — LPO, Roadside Safety Package; PEF — LPO, Contoured Liner Protection Package; RIA — LPO, All-weather floor liners with Jake logo; RWU — LPO, Cargo area organizer; RYT — LPO, First Aid Kit |
| Mechanical | Engine Appearance | 11 | B6P — Coupe Engine Appearance Package; BC4 — NEW! Blue LS6 engine cover; BC7 — Black LS6 engine cover; BCP — Edge Red LS6 engine cover; BCS — Sterling Silver LS6 engine cover; D3V — Engine lighting |
| Mechanical | LPO Exterior | 19 | 5V7 — LPO, Black Ground Effects; PCU — LPO, Stingray Protection Package; R88 — LPO, Illuminated crossed flags emblem; RIK — LPO, Rear Corvette script badge in Torch Red; RIN — LPO, Rear Corvette script badge in Arctic White; RNX — LPO, Premium outdoor car cover |
| Mechanical | Performance | 1 | ERI — Battery Protection Package |
| Mechanical | Spoiler | 4 | 5ZU — LPO, High wing spoiler, Body color; 5ZZ — LPO, High wing spoiler; T0A — Z51 Spoiler; TVS — Low-profile rear spoiler and front splitter |
| Mechanical | Wheel Accessory | 5 | 5ZC — LPO, Jake logo wheel center caps; 5ZD — LPO, Carbon Flash wheel center caps with crossed flags logo; RXH — LPO, Silver wheel center caps with Stingray logo and Red outline; RXJ — LPO, Black wheel center caps with Gray Stingray logo; VWD — LPO, Stingray R logo wheel center caps |

Full row-level details are in `csv-owned-projected.csv`.

## Production-Owned / Not-Projected By Category And Section

| Category | Section | RPO count | Example labels |
| --- | --- | --- | --- |
| Equipment Groups | 1LT Equipment | 4 | DWK — Mirrors; K7A — Wireless Phone Charging; UQS — Audio system feature; UVB — HD Rear Vision Camera |
| Equipment Groups | 2LT Equipment | 19 | AHE — Seat adjuster, driver power bolster; AHH — Seat adjuster, passenger power bolster; AL9 — Seat adjuster, power driver lumbar control; AP9 — Cargo nets, 2; AQA — Memory Driver and Passenger Convenience Package; AT9 — Seat adjuster, power passenger lumbar control |
| Equipment Groups | 3LT Equipment | 1 | IWE — Sueded Microfiber-Wrapped Upper Interior Trim Package |
| Equipment Groups \| Interior | 1LT Equipment \| 2LT Equipment \| Seats | 1 | AQ9 — GT1 Bucket Seats |
| Equipment Groups \| Interior | 2LT Equipment \| Interior Trim | 1 | UQT — Performance data and video recorder |
| Equipment Groups \| Interior | 3LT Equipment \| Seats | 1 | AH2 — GT2 Bucket Seats |
| Exterior | Caliper Color | 4 | J6B — Blue-painted calipers; J6E — Velocity Yellow-painted calipers; J6F — Bright Red-painted calipers; J6N — Edge Red-painted calipers |
| Exterior | Exterior Accents | 1 | EFY — Body-color accents |
| Exterior | Paint | 10 | G26 — Sebring Orange Tintcoat; G4Z — Roswell Green Metallic; G8G — Arctic White; GBA — Black; GBK — Competition Yellow Tintcoat Metallic; GEC — NEW! Pitch Gray Metallic |
| Exterior | Stripes | 16 | DPB — Carbon Flash with Blue accent Full Length Dual Racing Stripes; DPC — Carbon Flash with Yellow accent Full Length Dual Racing Stripes; DPG — Carbon Flash with Orange accent Full Length Dual Racing Stripes; DPL — Carbon Flash with Red accent Full Length Dual Racing Stripes; DPT — Carbon Flash with Silver accent Full Length Dual Racing Stripes; DSY — Edge Orange Full Length Dual Racing Stripes |
| Exterior | Wheels | 5 | Q99 — 20-spoke bright machined-face forged aluminum wheels; Q9A — 20-spoke Midnight Gray forged aluminum with Red stripe wheels; Q9I — 20-spoke Gloss Black forged aluminum wheels; Q9O — 5-split-spoke Satin Graphite with machined edge forged aluminum wheels; QE6 — NEW! 10-spoke Gloss Black forged aluminum wheels |
| Exterior \| Standard Equipment | Caliper Color \| Standard Options | 1 | J6A — Black painted calipers \| Calipers |
| Exterior \| Standard Equipment | Exterior Accents \| Standard Options | 1 | EFR — Carbon Flash accents \| Exterior accents |
| Exterior \| Standard Equipment | Standard Options \| Wheels | 1 | QEB — 5-split-spoke Pearl Nickel forged aluminum wheels \| Wheels |
| Interior | Color Override | 2 | D30 — Color Combination Override; R6X — Custom Interior Trim and Seat Combination |
| Interior | Interior Trim | 3 | BAZ — Stealth Interior Trim Package; BV4 — Personalized Plaque; FA5 — Carbon Fiber trim |
| Interior | OnStar | 6 | PRB — 3 Years OnStar One (Standalone); R6P — 3 Years SiriusXM; R9L — Removes OnStar Basics (OnStar Fleet Basics for Fleet); R9V — Mobile Service Plus; R9W — Deleted Mobile Service Plus; R9Y — Mobile Service Plus |
| Interior | Seat Belt | 5 | 379 — Orange Seat belt color; 3A9 — Santorini Blue Seat belt color; 3F9 — Torch Red Seat belt color; 3M9 — Yellow Seat belt color; 3N9 — Natural Seat belt color |
| Interior | Seats | 2 | AE4 — Competition Sport Bucket Seats; AUP — Mixed seats, driver Competition Sport bucket, passenger GT2 bucket |
| Interior \| Standard Equipment | Seat Belt \| Standard Options | 1 | 719 — Black Seat belt color \| Seat belt color |
| Mechanical | Custom Delivery | 3 | PIN — Customer VIN ending reservation; R8C — Corvette Museum Delivery; VK3 — Front License plate bracket |
| Mechanical | Exhaust | 2 | NWI — NEW! Exhaust tips; WUB — NEW! Exhaust |
| Mechanical | LPO Exterior | 4 | 5JR — LPO, Outside mirror covers in visible Carbon Fiber; PCX — LPO, Tech Bronze Accent Package; PDV — LPO, Stingray R Appearance Package; RZ9 — LPO, Visible Carbon Fiber grille insert |
| Mechanical | LPO Wheels | 2 | 5DG — LPO, 20-spoke Tech Bronze aluminum wheels; 5DO — LPO, 15-spoke bright polished aluminum wheels |
| Mechanical | Performance | 2 | E60 — Front lift adjustable height with memory; Z51 — Z51 Performance Package |
| Mechanical | Spoiler | 1 | ZYC — Carbon Flash Metallic-painted outside mirrors and spoiler (when equipped) |
| Mechanical | Suspension | 3 | FE2 — Suspension; FE3 — Z51 performance suspension; FE4 — Suspension |
| Mechanical | Wheel Accessory | 4 | S47 — LPO, Chrome lug nuts; SFE — LPO, Chrome wheel locks; SPY — LPO, Black lug nuts; SPZ — LPO, Black wheel locks |
| Mechanical \| Standard Equipment | Exhaust \| Standard Options | 1 | NGA — Exhaust tips |
| Mechanical \| Standard Equipment | Standard Options \| Suspension | 1 | FE1 — Suspension |
| Standard Equipment | Included | 10 | B4Z — Performance Traction Management; CFX — Plaque; DRG — Carbon Flash painted mirrors; G0K — Rear axle; G96 — Differential; J55 — Brakes |
| Standard Equipment | Safety Features | 9 | AJ7 — Airbags; DRZ — Rear Camera Mirror; TDM — Teen Driver; TQ5 — IntelliBeam; UD7 — Rear Park Assist; UEU — Forward Collision Alert |
| Standard Equipment | Standard Equipment | 13 | A2X — Seat adjuster; A7K — Seat adjuster; CJ2 — Air conditioning; G0J — Differential; JL9 — Brakes; LS6 — NEW! Engine |
| Standard Equipment | Standard Options | 1 | NK4 — Steering wheel |
| Standard Equipment | Technology | 6 | IVE — Infotainment system with Google Built-In; PPW — Wireless Apple CarPlay/Wireless Android Auto; U2K — SiriusXM with 360L Trial Subscription; U5G — 5G vehicle connectivity; UE1 — OnStar services capable; VV4 — Wi-Fi Hotspot capable |

Full row-level details are in `production-owned-not-projected.csv`.

## Cross-Boundary Relationships

These rows explain where preserved relationships cross between CSV-owned/projected and production-owned/not-projected surfaces. They are not migration decisions.

| Relationship type | Direction | Rows |
| --- | --- | --- |
| current_guarded_dependency_manifest_row | production_guarded/not_projected->production_guarded/not_projected | 4 |
| current_guarded_dependency_manifest_row | production_guarded/not_projected->production_owned/not_projected | 16 |
| current_guarded_dependency_manifest_row | production_guarded/not_projected->projected_owned/projected_owned | 11 |
| current_guarded_dependency_manifest_row | projected_owned/projected_owned->production_guarded/not_projected | 8 |
| manifest_only_preservation | production_owned/not_projected->production_owned/not_projected | 12 |
| manifest_only_preservation | production_owned/not_projected->projected_owned/projected_owned | 14 |
| manifest_only_preservation | projected_owned/projected_owned->production_owned/not_projected | 36 |
| manifest_only_preservation | projected_owned/projected_owned->projected_owned/projected_owned | 21 |

### Current Guarded Dependencies

Current guarded structured-reference dependencies: 43. These are represented by 39 active preserved manifest rows because some manifest rows back multiple structured references.

| Guarded ref | Structured refs | Candidate status |
| --- | --- | --- |
| opt_5vm_001 | 12 | cross_boundary_preserved |
| opt_5w8_001 | 12 | cross_boundary_preserved |
| opt_5zw_001 | 5 | cross_boundary_preserved |
| opt_cf8_001 | 13 | cross_boundary_preserved |
| opt_ryq_001 | 1 | cross_boundary_preserved |

### Manifest-Only Preservation

Manifest-only preservation rows: 83; groups: 78. These rows are valid preservation evidence but are not currently part of the active structured-reference guarded set.

| Direction | Rows | Groups |
| --- | --- | --- |
| production_owned/not_projected->production_owned/not_projected | 12 | 12 |
| production_owned/not_projected->projected_owned/projected_owned | 14 | 9 |
| projected_owned/projected_owned->production_owned/not_projected | 36 | 36 |
| projected_owned/projected_owned->projected_owned/projected_owned | 21 | 21 |

Full row-level relationship details are in `cross-boundary-relationships.csv`.

## Reconciliation Checks

| Check | Result |
| --- | --- |
| CSV-owned/projected count equals active projected selectable ownership manifest rows | pass (68 == 68) |
| Production-owned/not-projected count equals active production choice RPOs minus projected active choice RPOs | pass (147 == 215 - 68) |
| Cross-boundary relationship rows equal active preserved cross-boundary census rows | pass (122 == 122) |
| Manifest-only rows | pass (83) |
| Manifest-only groups | pass (78) |
| Current guarded dependencies | pass (43) |
| Invalid preserved rows | pass (0) |

## How To Use This

1. Use this report to understand migration status by category and section.
2. Use the decision ledger only after reviewing this status map.
3. The ledger is for recording human review decisions, not applying changes.
4. Treat cross-boundary rows as boundary evidence, not as instructions to migrate or remove anything.

## Non-Goals

- No source switch or runtime cutover.
- No automatic migration decision.
- No manifest update.
- No production artifact rewrite.
