# Pass 129 Pairwise Excludes Analysis Report

## Scope

This report classifies the 153 Pass 128 `pairwise_excludes_needs_model` rows into concrete rule-model buckets. It is report-only. It does not migrate data, claim CSV coverage, or approve schema changes.

## Interpretation

- `true_pairwise_conflict`: no better model was detected from current metadata; may require a direct exclusion rule.
- `exclusive_group_candidate`: both options are already in the same existing exclusive group or appear best modeled as group exclusivity.
- `replacement_or_default_behavior`: same-section single-select/default signals suggest replacement semantics.
- `availability_or_variant_behavior`: paint, roof, body, trim, status, or variant signals suggest availability semantics.
- `runtime_special_case`: exact known app-runtime behavior such as FE1/Z51, FE2/Z51, NGA/NWI, or ZYC/GBA.
- `duplicate_inverse_pair`: inverse legacy row exists; both raw rows remain in the detail CSV.
- `unclear_needs_research`: current metadata is insufficient for a concrete model bucket.

`proposed-schema-actions.csv` summarizes design candidates, not approved migrations.

## Summary By Bucket

| bucket | count | pct_of_pairwise_excludes |
| --- | --- | --- |
| availability_or_variant_behavior | 37 | 24.2 |
| duplicate_inverse_pair | 20 | 13.1 |
| true_pairwise_conflict | 89 | 58.2 |
| unclear_needs_research | 7 | 4.6 |

## Summary By Proposed Schema Action

| proposed_schema_action | count | design_candidate_note |
| --- | --- | --- |
| add_pairwise_excludes_table | 89 | Design candidate only: no better model was detected from current metadata; may require a direct exclusion rule. |
| collapse_duplicate_inverse | 20 | Design candidate: inverse pair exists; raw rows are preserved but modeling may collapse symmetry. |
| manual_research | 7 | Design candidate: current metadata is insufficient. |
| model_as_availability_rule | 37 | Design candidate: relationship appears closer to availability, paint, roof, body, or variant behavior. |

## Summary By Bucket And Action

| bucket | proposed_schema_action | count |
| --- | --- | --- |
| availability_or_variant_behavior | model_as_availability_rule | 37 |
| duplicate_inverse_pair | collapse_duplicate_inverse | 20 |
| true_pairwise_conflict | add_pairwise_excludes_table | 89 |
| unclear_needs_research | manual_research | 7 |

## Summary By Confidence

| confidence | count |
| --- | --- |
| high | 20 |
| low | 7 |
| medium | 126 |

## Top Section Patterns

| section_pattern | bucket | count |
| --- | --- | --- |
| (unknown) -> (unknown) | duplicate_inverse_pair | 2 |
| (unknown) -> Exterior Accents | availability_or_variant_behavior | 1 |
| (unknown) -> LPO Exterior | duplicate_inverse_pair | 4 |
| (unknown) -> Spoiler | unclear_needs_research | 3 |
| (unknown) -> Stripes | availability_or_variant_behavior | 13 |
| Exterior Accents -> Paint | availability_or_variant_behavior | 1 |
| Interior Trim -> Custom Delivery | true_pairwise_conflict | 1 |
| LPO Exterior -> (unknown) | duplicate_inverse_pair | 4 |
| LPO Exterior -> (unknown) | unclear_needs_research | 4 |
| LPO Exterior -> Badges | true_pairwise_conflict | 3 |
| LPO Exterior -> Custom Delivery | true_pairwise_conflict | 1 |
| LPO Exterior -> Exterior Accents | availability_or_variant_behavior | 1 |
| LPO Exterior -> LPO Exterior | duplicate_inverse_pair | 8 |
| LPO Exterior -> LPO Exterior | true_pairwise_conflict | 3 |
| LPO Exterior -> Performance | true_pairwise_conflict | 3 |
| LPO Exterior -> Roof | availability_or_variant_behavior | 1 |
| LPO Exterior -> Spoiler | availability_or_variant_behavior | 2 |
| LPO Exterior -> Spoiler | true_pairwise_conflict | 3 |
| LPO Exterior -> Stripes | true_pairwise_conflict | 59 |
| LPO Exterior -> Wheel Accessory | true_pairwise_conflict | 4 |
| LPO Wheels -> Custom Delivery | true_pairwise_conflict | 2 |
| LPO Wheels -> Wheel Accessory | true_pairwise_conflict | 8 |
| Roof -> Paint | availability_or_variant_behavior | 2 |
| Stripes -> LPO Exterior | true_pairwise_conflict | 1 |
| Stripes -> Paint | availability_or_variant_behavior | 16 |
| Wheel Accessory -> Wheel Accessory | duplicate_inverse_pair | 2 |
| Wheel Accessory -> Wheel Accessory | true_pairwise_conflict | 1 |

## Output Files

- `pairwise-excludes-by-relationship.csv`: one row per Pass 128 pairwise-exclude relationship.
- `pairwise-excludes-summary-by-bucket.csv`: bucket counts.
- `proposed-schema-actions.csv`: neutral design-candidate action counts.
