# Chat Pickup

We are continuing the **27vette `schema_refactor` CSV/shadow migration** on `https://github.com/seanzmc/27vette/tree/schema_refactor`.

Workflow rules for next chat:

- Use disciplined pass workflow.
- Spec first.
- Provide Codex prompts with recommended reasoning level.
- Report-only vs migration scope must be explicit.
- Production/generated `form-app/data.js` remains the oracle.
- No runtime cutover unless explicitly approved.
- No generated app/workbook edits unless explicitly approved.
- Keep migration lanes explicit.
- Challenge bad assumptions.

What we were working on:
We accelerated the Stingray CSV migration by grouping safe rows into behavior lanes instead of one-row passes. We migrated many proven `excludes`, `requires`, and package include/`included_zero` behaviors into CSV-owned tables while maintaining shadow parity.

Key decisions:

- Safe migration lanes are now:
  - Plain excludes → `dependency_rules.csv`
  - Simple requires → `dependency_rules.csv`
  - Includes + priceRule 0 → `auto_adds.csv` with `target_price_policy_id=included_zero`
  - Catalog unlocks → catalog/display/base-price/ownership only
  - Legacy/non-selectable references → registry + selector support, not normal selectables

- `5VM`, `5W8`, and `5ZW` must **not** be projected into `selectables.csv`; they are registered non-selectable references.
- `CF8` and `RYQ` remain runtime-owned structured references.
- `CFX` is a non-selectable auto-add target needing separate design later.

Current status:

- Last completed pass: **Pass 161**.
- Pass 161 implemented compiler/validator support for `subject_selector_type=non_selectable_reference` and `term_type=reference_selected`, using `non_selectable_references.csv`.
- No real data migration happened in Pass 161.
- Counts after Pass 161:
  - `dependency_rules.csv`: 101 rows total
  - `requires`: 3
  - `excludes`: 98
  - `auto_adds.csv`: 19 active rows
  - `condition_sets.csv`: 42
  - `condition_terms.csv`: 44
  - `selectables.csv`: 97
  - active `preserved_cross_boundary`: 83
  - `non_selectable_references.csv`: 6 active references

- Full ladder after Pass 161: **445/445 passing**.
- Remaining queue before Pass 162:
  - 25 `5VM/5W8/5ZW` registered-reference candidate rows
  - 14 `CF8/RYQ` keep-preserved runtime-owned rows
  - 1 `CFX` non-selectable auto-add-target design row
  - 23 color-support-needed rows
  - 20 Z51/package-adjacent rows

Direction:
Next we are moving from support into migration for the `5VM/5W8/5ZW` registered-reference dependency rows. This should use the new Pass 161 support without projecting those references as customer-selectable options.

Next pass:
**Pass 162 — migrate all safe `5VM/5W8/5ZW` registered-reference dependency rows only.**

Pass 162 scope:

- Migration scope, not report-only.
- Migrate up to 25 oracle-confirmed rows involving registered references `5VM`, `5W8`, and `5ZW`.
- Use:
  - `subject_selector_type=non_selectable_reference`
  - `subject_selector_id=ref_5vm/ref_5w8/ref_5zw`
  - target conditions using `term_type=reference_selected` where needed.

- Add condition sets/terms only for reference targets actually used.
- Remove only the matching migrated preserved rows.
- Do not touch `selectables.csv`, catalog/display/base-price, `auto_adds.csv`, price rules, runtime, generated output, workbook, or `form-app/data.js`.
- `CF8`, `RYQ`, and `CFX` rows remain preserved.
- Recommended Codex reasoning level: **High**.
