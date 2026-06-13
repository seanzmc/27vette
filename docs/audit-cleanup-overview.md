# Audit cleanup overview

Clean up audit-related workbook sheets and scripts that are no longer needed for runtime form generation or customer-facing behavior. This is a multi-pass process that should start with retiring audit-only metadata from required gates, then deleting the workbook sheets, and finally consolidating runtime metadata.

Best approach: gate-first retirement, then workbook cleanup. Do not start by deleting sheets.

## Recommended cleanup strategy:

1. Define two contracts:
   - Live form contract: what the customer runtime/generators actually need.
   - Audit/dev historical contract: old one-off review tooling, parser scaffolding, special investigation sheets, one-pass writers.

   Anything in the second bucket should not be required by normal form gates.

2. First pass should be narrow: retire audit-only metadata from required gates.
   Start with the cleanest junk:
   - option_audit_groups
   - option_audit_group_members
   - rule_review_groups

   These are not live runtime form data. They are used by rule-audit/source-review tooling and tests. That makes them the right first target because removing them should not affect the customer form if done correctly.

3. For that first pass, change tests before workbook deletion:
   - Remove/update tests that assert these sheets must exist.
   - Remove/update schema-standardization checks that include their boolean columns.
   - Remove docs that list them as active workbook runtime metadata.
   - Either retire the scripts that consume them, or make those scripts report-only/optional and not part of required form gates.

   Likely touched areas:
   - tests/audit-parser-metadata-loaders.test.mjs
   - tests/grand-sport-rule-audit.test.mjs
   - tests/workbook-schema-standardization.test.mjs
   - scripts/corvette_form_generator/runtime_metadata.py
   - scripts/build_rule_sources.py
   - README.md
   - AGENTS.md

4. Then delete the workbook sheets.
   Only after the required gates no longer protect them should the workbook be cleaned. Otherwise you are fighting the test suite instead of using it.

5. Keep runtime-used metadata separate from audit junk.
   These are messy/partial, but not safe first deletions:
   - section_presentation
   - runtime_steps
   - context_section_master
   - context_choice_copy
   - runtime_rule_exceptions
   - variant_option_overrides
   - order_summary_sections
   - step_order_summary_map

   Some of these are annoying, but they currently drive generated output or runtime behavior. They need a separate consolidation pass, not the same cleanup as audit junk.

## The practical plan I would use:

### Pass A — “Audit scaffolding retirement”

Goal: remove audit-only workbook sheets and their required-gate expectations without changing form runtime behavior.

Scope:

- Retire option_audit_groups, option_audit_group_members, rule_review_groups.
- Remove their required-test/schema/doc references.
- Delete or quarantine consumers if they are one-off historical audit tooling.
- Remove the sheets from stingray_master.xlsx.
- Do not touch runtime behavior, generated form behavior, Z06 rules, pricing, interiors, or model promotion.

Validation:

- Run workbook schema validation after updating expectations.
- Run live form/runtime gates:
- node --test tests/stingray-form-regression.test.mjs
- node --test tests/multi-model-runtime-switching.test.mjs
- Run any remaining Grand Sport/Z06 draft tests only if their expected contract no longer requires the retired audit sheets.
- Confirm generated form-app/data.js is unchanged except timestamps if generation is run.

### Pass B — “One-pass writer/script retirement”

Goal: remove stale apply*, repair*, populate*, audit* scripts that are no longer workflow entrypoints.

Method:

- Classify each script:
- current workflow entrypoint: keep
- reusable read-only report: keep or make report-only
- one-pass workbook writer: delete
- historical context: move lesson to docs/skill, delete executable
- Update tests/docs that reference deleted scripts.

### Pass C — “Required gate split”

Goal: stop one-off audit tooling from blocking normal form work.

Create/clarify:

- default/live gate: app generation + runtime regressions
- workbook schema gate: only canonical active workbook contracts
- optional historical/audit gate: not part of normal readiness unless explicitly running old audit tooling

This is the step that prevents the problem from coming back.

### Pass D — “Runtime metadata consolidation”

Goal: address the real architectural frustration: each model taking a different path.

This is where we decide what to do with:

- runtime_steps
- context_section_master
- section_presentation
- order_summary_sections
- step_order_summary_map
- runtime_rule_exceptions
- variant_option_overrides

But do not mix this with audit-junk deletion. Some of these are actually useful attempts to move hardcoded behavior out of Python/JS. The problem is partial adoption and inconsistent model coverage, not necessarily that every sheet is junk.

My recommendation:
Start with Pass A only.

It gives you an immediate reduction in workbook/test clutter without risking customer runtime behavior. It also breaks the bad pattern where historical audit scaffolding is treated as required app infrastructure.

If you approve, I would write the spec for Pass A as:
“Retire audit-only workbook metadata sheets and required-gate expectations: option_audit_groups, option_audit_group_members, rule_review_groups; no runtime behavior changes.”
