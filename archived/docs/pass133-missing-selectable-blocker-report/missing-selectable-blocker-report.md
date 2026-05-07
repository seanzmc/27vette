# Pass 133 Missing-Selectable Blocker Report

## Scope

This report maps the true-pairwise dependency-rule exclude rows that remain blocked after Pass 132 because one or both endpoints are not active in `data/stingray/catalog/selectables.csv`.

No migration was performed. No source CSV, compiler, runtime, generated app, workbook, manifest, or test files were edited.

## Reconciliation

| metric | count |
|---|---:|
| True-pairwise dependency-rule exclude rows in Pass 130 dry-run | 89 |
| Blocked by missing source and/or target selectable | 82 |
| Unique missing selectable IDs | 27 |
| Blocked rows with both endpoints missing | 50 |
| Missing endpoint appearances as source | 52 |
| Missing endpoint appearances as target | 80 |

The blocked relationship count reconciles to 82. Blocker endpoint counts exceed 82 because 50 relationship rows have both source and target missing and therefore count under two missing selectables.

## Blocker Types

| blocker_type | missing_selectable_count |
|---|---:|
| missing_selectable | 27 |

All 27 missing selectable IDs exist in production choices. No blockers were classified as duplicate-display or standard-equipment surfaces; production presents them as active selectable choices.

## Top Missing Selectables

| missing_selectable_id | rpo | label | missing_as_source_count | missing_as_target_count | total_blocked_relationships | suggested_catalog_slice |
|---|---|---|---:|---:|---:|---|
| opt_pcx_001 | PCX | LPO, Tech Bronze Accent Package | 24 | 0 | 24 | LPO Exterior packages |
| opt_pdv_001 | PDV | LPO, Stingray R Appearance Package | 16 | 2 | 18 | LPO Exterior packages |
| opt_5dg_001 | 5DG | LPO, 20-spoke Tech Bronze aluminum wheels | 5 | 0 | 5 | LPO Wheels |
| opt_5do_001 | 5DO | LPO, 15-spoke bright polished aluminum wheels | 5 | 0 | 5 | LPO Wheels |
| opt_dpb_001 | DPB | Carbon Flash with Blue accent Full Length Dual Racing Stripes | 0 | 4 | 4 | Stripes |
| opt_dpc_001 | DPC | Carbon Flash with Yellow accent Full Length Dual Racing Stripes | 0 | 4 | 4 | Stripes |
| opt_dpg_001 | DPG | Carbon Flash with Orange accent Full Length Dual Racing Stripes | 0 | 4 | 4 | Stripes |
| opt_dpl_001 | DPL | Carbon Flash with Red accent Full Length Dual Racing Stripes | 0 | 4 | 4 | Stripes |
| opt_dpt_001 | DPT | Carbon Flash with Silver accent Full Length Dual Racing Stripes | 0 | 4 | 4 | Stripes |
| opt_dsy_001 | DSY | Edge Orange Full Length Dual Racing Stripes | 0 | 4 | 4 | Stripes |

## Catalog Slice Candidates

Rows are sorted mechanically by `blocked_relationship_count desc`, then `missing_selectable_count desc`, then slice name. `blocked_relationship_count` means the slice touches that many blocked rows; the rationale notes how many rows would have all missing endpoints covered by that slice alone.

| suggested_catalog_slice | missing_selectable_count | blocked_relationship_count | example_rpos | rationale |
|---|---:|---:|---|---|
| Stripes | 16 | 58 | DPB, DPC, DPG, DPL, DPT, DSY, DSZ, DT0 | Touches 58 blocked relationship(s); 26 would have all missing endpoints covered by this slice alone. |
| LPO Exterior packages | 2 | 41 | PCX, PDV | Touches 41 blocked relationship(s); 4 would have all missing endpoints covered by this slice alone. |
| Wheel Accessory | 4 | 13 | S47, SFE, SPY, SPZ | Touches 13 blocked relationship(s); 1 would have all missing endpoints covered by this slice alone. |
| LPO Wheels | 2 | 10 | 5DG, 5DO | Touches 10 blocked relationship(s); 0 would have all missing endpoints covered by this slice alone. |
| Custom Delivery | 1 | 4 | R8C | Touches 4 blocked relationship(s); 0 would have all missing endpoints covered by this slice alone. |
| Performance packages | 1 | 3 | Z51 | Touches 3 blocked relationship(s); 3 would have all missing endpoints covered by this slice alone. |
| Interior Trim | 1 | 1 | BV4 | Touches 1 blocked relationship(s); 0 would have all missing endpoints covered by this slice alone. |

## Interpretation

- The largest blocker by individual selectable is `opt_pcx_001` / PCX, followed by `opt_pdv_001` / PDV.
- The highest-touch slice is Stripes because many already-projected sources exclude missing stripe targets, and PCX/PDV also point into stripe targets.
- LPO Exterior packages are high-leverage but many of their blocked rows also require Stripes or Wheel Accessory targets before the relationship can be fully migrated.
- Standard/display-only review did not identify a separate blocker set in this pass; the missing IDs found here are active selectable production choices rather than display-only standard-equipment duplicates.
