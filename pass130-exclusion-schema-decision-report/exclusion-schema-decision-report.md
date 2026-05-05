# Pass 130 Exclusion Schema Decision Report

## Scope

This report makes a dry-run schema decision for legacy pairwise excludes. It creates draft rows only. It does not edit source CSVs, compiler code, app/runtime/generated files, workbook files, manifests, or tests.

## Decision

Prefer `dependency_rules.csv` for pairwise excludes by extending it to support `rule_type=excludes`.

### Why dependency_rules.csv is preferred

- Existing table already models `rule_type`, subject selector, scope, target condition, violation behavior, message, priority, and active state.
- Avoids adding another near-duplicate logic table.
- Requires compiler support for `rule_type=excludes`.
- Keeps requires/excludes under one dependency/conflict rule surface.

### Current limitation

This is not implemented yet. Current `CsvSlice` only evaluates `dependency_rules` where `rule_type == "requires"`, and current legacy emission writes dependency rows as `rule_type: "requires"`. A later compiler pass would need to emit app-shaped `data.rules[]` rows with `rule_type="excludes"`.

## Option Comparison

### Option A: add logic/exclusion_rules.csv

The dedicated-table draft is included in `exclusion-rules-option-draft.csv` for comparison. It is not preferred now because it duplicates the selector/scope/message/priority/lifecycle shape that already exists in `dependency_rules.csv`.

### Option B: extend logic/dependency_rules.csv

This is preferred for the dry run. Required compile-back fields for legacy `data.rules[]` are:

- source selector: `subject_selector_type`, `subject_selector_id`
- target selected condition: `target_condition_set_id` resolvable to one target selectable
- `rule_type=excludes`
- `message` for legacy `disabled_reason`
- `applies_when_condition_set_id` for scope/body-style metadata when needed
- `violation_behavior`, `priority`, and `active`
- legacy trace fields in the dry run: `legacy_rule_id`, `normalized_pair_key`

The draft `target_condition_set_id` values are dry-run IDs. A later migration pass must create matching `condition_sets.csv` / `condition_terms.csv` rows or reuse existing selected-option condition sets before validation/compiler support can be enabled.

### Option C: model through groups or availability/status structures

Pass 129 already removed existing exclusive-group candidates from this unresolved set. Availability-style rows are deferred in this pass rather than forced into pairwise conflict schema.

## Duplicate Inverse Handling

The current `dependency_rules.csv` shape is directional. Collapsing inverse pairs into one bidirectional row would require a new directionality compiler semantic, so this dry run preserves directional rows.

The 20 duplicate-inverse rows share 10 `normalized_pair_key` values. Both raw directions are preserved in the dry-run and draft files. Together with the 89 true pairwise conflicts, this produces 109 directional draft rows.

## Deferred Rows

- `availability_or_variant_behavior` rows are deferred to availability/variant modeling.
- `unclear_needs_research` rows are deferred for manual research.

## Reconciliation

### Pass 129 Rows By Bucket

| bucket | count |
| --- | --- |
| availability_or_variant_behavior | 37 |
| duplicate_inverse_pair | 20 |
| true_pairwise_conflict | 89 |
| unclear_needs_research | 7 |

### Dry-Run Rows By Original Bucket

| original_bucket | count |
| --- | --- |
| duplicate_inverse_pair | 20 |
| true_pairwise_conflict | 89 |

### Deferred Rows By Original Bucket

| original_bucket | count |
| --- | --- |
| availability_or_variant_behavior | 37 |
| unclear_needs_research | 7 |

### Rows By Proposed Schema Target

| proposed_schema_target | count |
| --- | --- |
| availability_model_deferred | 37 |
| dependency_rules_excludes | 109 |
| research_deferred | 7 |

## Output Files

- `dry-run-exclusion-migration-map.csv`: directional dry-run canonical mapping for 89 true pairwise conflicts and 20 duplicate-inverse rows.
- `dependency-rules-option-draft.csv`: preferred draft representation using `dependency_rules.csv` with `rule_type=excludes`.
- `exclusion-rules-option-draft.csv`: non-preferred dedicated-table comparison draft.
- `deferred-availability-or-research.csv`: 37 availability/variant rows and 7 unclear rows deferred out of pairwise schema.
