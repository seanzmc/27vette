# Pass 128 Schema-Gap Triage Report

## Scope

This report classifies the 207 `needs_schema_mapping` rows from Pass 127 into actionable schema/mapping buckets. It is report-only. It does not migrate data, claim coverage, or decide cutover.

Inputs:

- `pass127-relationship-coverage-report/schema-gap-relationships.csv`
- `pass127-relationship-coverage-report/csv-relationship-coverage.csv`
- `data/stingray/logic/*.csv`
- `data/stingray/pricing/*.csv`
- `data/stingray/catalog/item_sets.csv`
- `data/stingray/catalog/item_set_members.csv`
- `form-app/data.js`
- `form-app/app.js` for exact runtime special-case evidence only

## Category Definitions

- `pairwise_excludes_needs_model`: legacy pairwise excludes are not currently represented by the CSV files checked, unless covered by exclusive-group membership or a known runtime special case.
- `condition_set_target_mapping_needed`: current dependency CSV context exists, but it uses condition-set target semantics instead of a direct legacy target ID.
- `set_based_relationship_mapper_gap`: an existing set or exclusive-group context may explain the relationship, but the row is not direct source/target coverage.
- `price_rule_mapper_gap`: set-based pricing context may explain a price relationship, but the row is not direct condition/target coverage.
- `interior_or_non_option_namespace`: a source or target uses an interior or non-`opt_*` namespace not cleanly handled by the current CSV mapper.
- `legacy_runtime_special_case`: exact known app-runtime special pair such as FE1/Z51, FE2/Z51, NGA/NWI, or ZYC/GBA.
- `unknown_needs_research`: no deterministic triage rule matched.

## Candidate File Interpretation

- `mapper-improvement-candidates.csv` contains rows where better mapping may reduce false schema gaps.
- `schema-change-candidates.csv` does not mean the schema definitely needs to change. It means the current mapper did not find a clean existing CSV home.

## Summary By Triage Reason

| triage_reason | count | pct_of_schema_gaps |
| --- | --- | --- |
| condition_set_target_mapping_needed | 4 | 1.9 |
| interior_or_non_option_namespace | 45 | 21.7 |
| legacy_runtime_special_case | 2 | 1.0 |
| pairwise_excludes_needs_model | 153 | 73.9 |
| set_based_relationship_mapper_gap | 3 | 1.4 |

## Summary By Relationship Type And Triage Reason

| relationship_type | triage_reason | count |
| --- | --- | --- |
| excludes | legacy_runtime_special_case | 2 |
| excludes | pairwise_excludes_needs_model | 153 |
| excludes | set_based_relationship_mapper_gap | 3 |
| includes | interior_or_non_option_namespace | 30 |
| price_rule | interior_or_non_option_namespace | 15 |
| requires | condition_set_target_mapping_needed | 4 |

## Summary By Triage Confidence

| triage_confidence | count |
| --- | --- |
| high | 54 |
| medium | 153 |

## Summary By Reason And Confidence

| triage_reason | triage_confidence | count |
| --- | --- | --- |
| condition_set_target_mapping_needed | high | 4 |
| interior_or_non_option_namespace | high | 45 |
| legacy_runtime_special_case | high | 2 |
| pairwise_excludes_needs_model | medium | 153 |
| set_based_relationship_mapper_gap | high | 3 |

## Output Files

- `schema-gap-triage-by-relationship.csv`: one triage row per Pass 127 schema-gap relationship.
- `schema-gap-summary-by-reason.csv`: counts by triage reason.
- `mapper-improvement-candidates.csv`: subset where mapper improvements may reduce false gaps.
- `schema-change-candidates.csv`: subset where the current mapper did not find a clean existing CSV home.
