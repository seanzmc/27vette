# Pass 132 Existing-Selectable Excludes Migration Summary

Pass 132 bulk-migrated the safe true-pairwise dependency-rule excludes from the Pass 130 dry-run where both endpoints already exist as active CSV selectables.

## Migrated Rows

| rule_id | source_id | target_id | target_condition_set_id | message |
|---|---|---|---|---|
| dep_excl_pcu_5v7 | opt_pcu_001 | opt_5v7_001 | cs_selected_5v7 | Blocked by PCU LPO, Stingray Protection Package. |
| dep_excl_r88_eyk | opt_r88_001 | opt_eyk_001 | cs_selected_eyk | Blocked by R88 LPO, Illuminated crossed flags emblem. |
| dep_excl_r88_sfz | opt_r88_001 | opt_sfz_001 | cs_selected_sfz | Blocked by R88 LPO, Illuminated crossed flags emblem. |
| dep_excl_rnx_5zz | opt_rnx_001 | opt_5zz_001 | cs_selected_5zz | Blocked by RNX LPO, Premium outdoor car cover. |
| dep_excl_sfz_eyk | opt_sfz_001 | opt_eyk_001 | cs_selected_eyk | Blocked by SFZ LPO, Dark Stealth crossed flags emblem. |
| dep_excl_wkq_5zz | opt_wkq_001 | opt_5zz_001 | cs_selected_5zz | Blocked by WKQ LPO, Premium indoor car cover. |

## Counts

| bucket | count | status |
|---|---:|---|
| true_pairwise_conflict with active source and target, newly migrated in Pass 132 | 6 | migrated |
| true_pairwise_conflict with active source and target, already present before Pass 132 | 1 | already present: dep_excl_5v7_tvs |
| true_pairwise_conflict with missing source or target selectable | 82 | skipped; requires catalog projection first |
| duplicate_inverse_pair from dependency-rules option draft | 20 | skipped; out of Pass 132 true-pairwise scope |
| availability_or_variant_behavior from deferred file | 37 | skipped; deferred to availability/variant modeling |
| unclear_needs_research from deferred file | 7 | skipped; deferred to manual research |

Pass 131 rows were preserved. `dep_excl_5v7_tvs` is already present as a true-pairwise row. `dep_excl_5v7_sti` remains present from Pass 131 but is outside the Pass 132 true-pairwise bulk scope because it belongs to the duplicate-inverse bucket in the Pass 130 draft.

## Notes

- No catalog rows were added.
- No availability/variant rows were migrated.
- No unclear research rows were migrated.
- No runtime, generated app data, workbook, or manifest files were changed.
- The messages above were copied from production/generated `form-app/data.js`, not from the dry-run placeholder text.
