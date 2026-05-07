# Pass 127 Relationship Coverage Report

## Scope

This report maps production/generated Stingray relationships from `form-app/data.js` to the requested `data/stingray` CSV-shadow relationship files. It is report-only; it does not migrate data or decide cutover.

Production source surfaces:

- `data.rules`
- `data.priceRules`
- `data.ruleGroups`
- `data.exclusiveGroups`

CSV files checked:

- `data/stingray/logic/auto_adds.csv`
- `data/stingray/logic/dependency_rules.csv`
- `data/stingray/logic/rule_groups.csv`
- `data/stingray/logic/rule_group_members.csv`
- `data/stingray/logic/exclusive_groups.csv`
- `data/stingray/logic/exclusive_group_members.csv`
- `data/stingray/pricing/base_prices.csv` (context only; not used to claim conditional price-rule coverage)
- `data/stingray/pricing/price_rules.csv`
- `data/stingray/catalog/item_sets.csv` (context only)
- `data/stingray/catalog/item_set_members.csv` (context only)

## How To Interpret coverage_status

- `covered_in_csv`: relationship appears directly represented in the requested CSV-shadow files.
- `not_found_in_csv`: schema has an apparent home, but no matching CSV row was found.
- `needs_schema_mapping`: relationship needs schema/design mapping before migration because the current CSV shape does not cleanly express the legacy relationship.

## How To Interpret coverage_confidence

- `exact`: direct source/target/type match.
- `inferred`: likely set-based or contextual match, but not direct enough to claim exact coverage.
- `none`: no matching CSV evidence found.
- `schema_gap`: current CSV schema cannot express the relationship cleanly yet.

Rows with `coverage_confidence=inferred` are intentionally not marked `covered_in_csv`.

## Reconciliation Summary

### Legacy Relationships By Type

| relationship_type | count |
| --- | --- |
| excludes | 158 |
| exclusive_group_member | 22 |
| includes | 64 |
| price_rule | 43 |
| requires | 16 |
| requires_any | 5 |

### Coverage Rows By Type And Status

| relationship_type | coverage_status | count |
| --- | --- | --- |
| excludes | needs_schema_mapping | 158 |
| exclusive_group_member | covered_in_csv | 22 |
| includes | covered_in_csv | 12 |
| includes | needs_schema_mapping | 30 |
| includes | not_found_in_csv | 22 |
| price_rule | needs_schema_mapping | 15 |
| price_rule | not_found_in_csv | 28 |
| requires_any | covered_in_csv | 2 |
| requires_any | not_found_in_csv | 3 |
| requires | needs_schema_mapping | 4 |
| requires | not_found_in_csv | 12 |

### Coverage Rows By Confidence

| coverage_confidence | count |
| --- | --- |
| exact | 36 |
| inferred | 9 |
| none | 56 |
| schema_gap | 207 |

### Uncovered Rows By Type

| relationship_type | count |
| --- | --- |
| includes | 22 |
| price_rule | 28 |
| requires | 12 |
| requires_any | 3 |

### Schema-Gap Rows By Type

| relationship_type | count |
| --- | --- |
| excludes | 158 |
| includes | 30 |
| price_rule | 15 |
| requires | 4 |

## Matching Notes

- `includes` coverage requires a direct `auto_adds.csv` selectable source and target match.
- Set-based auto-adds are recorded as `coverage_confidence=inferred` and remain `not_found_in_csv` for the legacy source/target row.
- `requires` rows are conservative because `dependency_rules.csv` currently uses condition-set targets in the requested inputs, not direct legacy `target_id` values.
- Pairwise legacy `excludes` rows are classified as `needs_schema_mapping`; `exclusive_groups.csv` covers group membership, not pairwise source/target excludes.
- `requires_any` coverage requires matching `rule_groups.csv` source/group type plus a matching `rule_group_members.csv` target.
- `exclusive_group_member` coverage accepts direct group ID matches and `legacy_group_id` aliases from `exclusive_groups.csv`.
- `price_rule` coverage is conservative and comes from `pricing/price_rules.csv`, not `base_prices.csv`, for conditional source-to-target price relationships.

## Output Files

- `legacy-relationships.csv`: one normalized row per production/generated relationship.
- `csv-relationship-coverage.csv`: one coverage row per normalized legacy relationship.
- `uncovered-relationships.csv`: subset where `coverage_status=not_found_in_csv`.
- `schema-gap-relationships.csv`: subset where `coverage_status=needs_schema_mapping`.
