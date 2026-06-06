# Grand Sport Rule Dedupe Audit Spec

## Diagnosis

The current Grand Sport rule audit catches exact duplicate semantic keys only when these fields all match:

- `source_id`
- `rule_type`
- `target_id`
- `body_style_scope`
- `runtime_action`

That misses the cleanup problem now visible in `grandSport_rule_mapping`: copied rows can duplicate a shorter canonical row while adding only a narrower `body_style_scope`. Example:

| rule_id | source_id | rule_type | target_id | body_style_scope |
| --- | --- | --- | --- | --- |
| `gs_rule_opt_b6p_001_includes_opt_d3v_001` | `opt_b6p_001` | `includes` | `opt_d3v_001` | blank |
| `gs_copy_rule_opt_b6p_001_includes_opt_d3v_001_opt_b6p_001_includes_opt_d3v_001_coupe` | `opt_b6p_001` | `includes` | `opt_d3v_001` | `coupe` |

The scope column itself is not junk. It contributes to runtime behavior:

- `form-app/app.js` uses `rule.body_style_scope` in `ruleAppliesToCurrentVariant()`.
- scoped rules are valid when the rule truly applies only to coupe or convertible.

The `runtime_action` column is different for Grand Sport source cleanup:

- current `grandSport_rule_mapping` has no nonblank `runtime_action` values;
- generated output fills blanks as `active`;
- Stingray still uses `runtime_action=replace`, so this is not a repo-wide removal candidate yet.

Risk level: medium. A bad dedupe could remove a scoped rule that is the only thing preventing incorrect availability. The audit must classify before workbook mutation.

## Goal

Add audit categories that separate:

1. exact duplicate Grand Sport rule rows;
2. overlapping scoped duplicate rows;
3. redundant scoped copied rows that can be safely omitted or deactivated;

then use that report to clean copied redundant rows in `grandSport_rule_mapping` while preserving scoped rows that contribute to runtime behavior.

## Non-Goals

- Do not remove `body_style_scope`.
- Do not remove `runtime_action` from shared runtime or Stingray sheets in this pass.
- Do not delete workbook rows. Prefer marking copied redundant rows with `generation_action=omit_redundant_scoped_duplicate`.
- Do not change Grand Sport runtime logic.
- Do not activate Grand Sport production generation.
- Do not dedupe price rules or exclusive groups in this pass.

## Files To Change

- `scripts/build_grand_sport_rule_sources.py`
  - Add focused rule dedupe audit categories.
  - Stop using `runtime_action` as part of Grand Sport duplicate detection while the workbook has no values in that column.

- `tests/grand-sport-rule-audit.test.mjs`
  - Add regression coverage for exact, overlapping, and redundant scoped duplicate audit categories.
  - Assert that the B6P/D3V scoped copied row is reported as redundant before cleanup.

- `stingray_master.xlsx`
  - After the audit is readable, mark redundant copied rows in `grandSport_rule_mapping` with `generation_action=omit_redundant_scoped_duplicate`.
  - Keep canonical shorter rows active when they already express the rule globally.

- Generated artifacts:
  - `form-output/inspection/grand-sport-rule-audit.json`
  - `form-output/inspection/grand-sport-rule-audit.md`
  - `form-output/inspection/grand-sport-form-data-draft.json`
  - `form-output/inspection/grand-sport-form-data-draft.md`

## Constraints

- Workbook remains the source of truth.
- No hardcoded Grand Sport business facts in runtime scripts.
- Audit classification may use workbook metadata to decide whether a scoped row is redundant:
  - `grandSport_ovs`
  - `variant_master`
  - `grandSport_options`
- Preserve scoped rows when the source option is available across both body styles and the rule only applies to one body style.
- Preserve scoped rows when there is no global duplicate.
- Preserve scoped rows if the global row is omitted/inactive.
- Keep Stingray behavior unchanged.

## Audit Categories

### 1. Exact Duplicate Rule Rows

Key:

```text
source_id + rule_type + target_id + body_style_scope
```

Ignore `runtime_action` for Grand Sport duplicate detection in this pass because the workbook source has no nonblank values.

Report fields:

- `source_id`
- `rule_type`
- `target_id`
- `body_style_scope`
- `rule_ids`
- `copied_rule_ids`
- `canonical_rule_id`
- `recommended_action`

Recommendation:

- Prefer the shortest non-`gs_copy_` `rule_id`.
- Mark copied duplicates omitted when they have the same behavior.

### 2. Overlapping Scoped Rule Rows

Key:

```text
source_id + rule_type + target_id
```

Report when this key has:

- at least one global row where `body_style_scope` is blank;
- at least one scoped row where `body_style_scope` is `coupe` or `convertible`.

Report fields:

- `source_id`
- `rule_type`
- `target_id`
- `global_rule_ids`
- `scoped_rule_ids`
- `scopes`
- `source_option_body_styles`
- `classification`
- `recommended_action`

### 3. Redundant Scoped Rule Rows

This is a subset of overlapping scoped rule rows.

A scoped row is redundant when all of these are true:

- same `source_id + rule_type + target_id` has a global active row;
- scoped row is active/runtime-authored;
- scoped row is copied or has a longer generated copy-style key;
- scoped row’s `body_style_scope` is fully covered by the source option’s availability in `grandSport_ovs`;
- removing the scoped row would not remove the only body-specific restriction.

Source option body-style coverage:

- derive body style from `variant_master.variant_id`;
- use `grandSport_ovs` rows where the option has `status=available` or `status=standard`;
- body-style set for `opt_b6p_001` should resolve to `coupe` only.

Report fields:

- `redundant_rule_id`
- `canonical_rule_id`
- `source_id`
- `source_rpo`
- `rule_type`
- `target_id`
- `target_rpo`
- `body_style_scope`
- `source_option_body_styles`
- `reason`
- `recommended_generation_action`

Recommendation:

```text
generation_action=omit_redundant_scoped_duplicate
```

## Workbook Cleanup Rules

After generating the audit:

1. For rows in `focusedReview.redundantScopedRuleRows`, set:
   - `generation_action=omit_redundant_scoped_duplicate`
   - leave `body_style_scope` unchanged for traceability
   - leave `original_detail_raw` unchanged
   - leave the row in place

2. Do not alter rows in `overlappingScopedRuleRows` unless they are also in `redundantScopedRuleRows`.

3. Do not alter scoped rows when:
   - there is no global row;
   - the source option exists on both coupe and convertible;
   - the scoped row is the only scoped restriction;
   - the scoped row uses a different `rule_type` or `target_id`.

4. Prefer canonical row IDs in this order:
   - non-`gs_copy_` rule rows;
   - shortest `rule_id`;
   - blank `body_style_scope` row when the relationship is globally valid.

## Implementation Plan

### Pass 1: Add Audit Categories Only

Modify `scripts/build_grand_sport_rule_sources.py`:

- add helper to normalize dedupe key:

```python
def grand_sport_rule_dedupe_key(row: dict[str, Any]) -> tuple[str, str, str]:
    return (
        row.get("source_id", ""),
        row.get("rule_type", "").lower(),
        row.get("target_id", ""),
    )
```

- add helper for exact key:

```python
def grand_sport_rule_exact_key(row: dict[str, Any]) -> tuple[str, str, str, str]:
    return (
        row.get("source_id", ""),
        row.get("rule_type", "").lower(),
        row.get("target_id", ""),
        clean(row.get("body_style_scope", "")),
    )
```

- add helper to derive option body-style coverage from `grandSport_ovs` and `variant_master`.
- add `exactDuplicateRuleRows`.
- add `overlappingScopedRuleRows`.
- add `redundantScopedRuleRows`.
- add summary counts:
  - `exactDuplicateRuleRows`
  - `overlappingScopedRuleRows`
  - `redundantScopedRuleRows`
- add Markdown sections:
  - `## Exact Duplicate Rule Rows`
  - `## Overlapping Scoped Rule Rows`
  - `## Redundant Scoped Rule Rows`

Update `tests/grand-sport-rule-audit.test.mjs`:

- assert summary counts match array lengths;
- assert Markdown includes the new sections;
- assert the B6P/D3V copied coupe row appears in `redundantScopedRuleRows`;
- assert the canonical row is `gs_rule_opt_b6p_001_includes_opt_d3v_001`;
- assert no workbook mutation occurs in this pass.

Validation:

```bash
.venv/bin/python scripts/build_grand_sport_rule_sources.py
node --test tests/grand-sport-rule-audit.test.mjs
git diff --check
```

Stop after Pass 1 if the redundant-row list looks unexpectedly broad.

### Pass 2: Workbook Cleanup

Use the audit output from Pass 1.

Modify `stingray_master.xlsx`:

- For each row listed in `focusedReview.redundantScopedRuleRows`, update only `generation_action`.
- Expected first row:

```text
rule_id=gs_copy_rule_opt_b6p_001_includes_opt_d3v_001_opt_b6p_001_includes_opt_d3v_001_coupe
generation_action=omit_redundant_scoped_duplicate
```

Do not delete rows.

Do not edit canonical shorter rows.

Regenerate:

```bash
.venv/bin/python scripts/generate_grand_sport_form.py
```

Expected behavior:

- draft runtime rule count decreases by the number of omitted redundant scoped rows;
- canonical global rules remain present;
- no missing references are introduced;
- no Grand Sport runtime code changes are needed.

### Pass 3: Post-Cleanup Regression

Run:

```bash
.venv/bin/python scripts/validate_workbook_package.py stingray_master.xlsx
.venv/bin/python scripts/generate_grand_sport_form.py
node --test tests/grand-sport-draft-data.test.mjs
node --test tests/grand-sport-rule-audit.test.mjs
node --test tests/multi-model-runtime-switching.test.mjs
node --test tests/stingray-generator-stability.test.mjs
node --test tests/stingray-form-regression.test.mjs
git diff --check
```

Expected:

- workbook validates with `issue_count=0`;
- `redundantScopedRuleRows` either becomes `0` or contains only rows intentionally left for review;
- exact duplicates are `0`;
- missing option references remain `0`;
- Stingray tests remain green.

## Success Criteria

- The audit identifies exact duplicate, overlapping scoped, and redundant scoped Grand Sport rules separately.
- The B6P/D3V copied coupe row is classified as redundant before cleanup.
- Redundant copied rows are omitted through workbook data, not runtime code.
- Canonical shorter rows remain active.
- Scoped rules that actually contribute to runtime behavior are preserved.
- Grand Sport draft output is cleaner and still functionally equivalent for valid scoped rules.

