# Audit cleanup overview

Clean up audit-related workbook sheets, skipped source rows, and default gate policy that are no longer needed for runtime form generation or customer-facing behavior. This is a multi-pass process: audit-only sheets and dead-end rows have been retired, default readiness gates now exclude optional audit/report tooling, and runtime metadata consolidation remains a later pass.

Current approach: keep live form/workbook-contract gates separate from optional audit/dev historical tooling. Do not add audit/report checks back to default readiness without proving a current runtime-contract failure they uniquely catch.

## Recommended cleanup strategy:

1. Define two contracts:
   - Live form contract: what the customer runtime/generators actually need.
   - Audit/dev historical contract: old one-off review tooling, parser scaffolding, special investigation sheets, one-pass writers.

   Anything in the second bucket should not be required by normal form gates.

2. The first cleanup target was narrow: retire audit-only metadata from required gates.
   It started with the cleanest junk:
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

Status: Completed. See `docs/audit-cleanup/pass-a-audit-scaffolding-retirement-spec.md`.

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

Status: Completed. See:

- `docs/audit-cleanup/pass-b-one-pass-script-retirement-spec.md`
- `docs/audit-cleanup/pass-b-script-retirement-inventory.md`

Goal: remove stale apply*, repair*, populate*, audit* scripts that are no longer workflow entrypoints.

Current result: no active tracked stale one-pass workbook writer was found. The active tree already lacks the obvious old one-off script names (`populate*.py`, `generate_*_form.py`, `promote_*runtime*.py`, `*future*review*.py`, extra `apply*.py`, extra `repair*.py`). The current `apply_workbook_ops.py`, `repair_workbook_tables.py`, `promote_model.py`, generator, validators, workbook editor server, and comparison helper are guarded workflow entrypoints and were kept. `build_rule_sources.py` remains a reusable read-only report/audit helper; whether it belongs in normal readiness gates is a Pass C question.

Method:

- Classify each script:
- current workflow entrypoint: keep
- reusable read-only report: keep or make report-only
- one-pass workbook writer: delete
- historical context: move lesson to docs/skill, delete executable
- Update tests/docs that reference deleted scripts.

### Pass C — “Workbook dead-end rule row retirement”

Status: Completed. See:

- `docs/audit-cleanup/pass-c-dead-end-rule-row-retirement-spec.md`
- `docs/audit-cleanup/pass-c-rule-row-retirement-inventory.md`

Goal: delete all workbook `rule_mapping` / `grandSport_rule_mapping` rows that current runtime generation skips, then update tests so skipped-row counts are no longer treated as protected infrastructure.

Method:

- Build an inventory for rollback/evidence, not for preserving ambiguous skipped rows.
- Delete all rows where `runtime_authored_rule(row)` is false.
- Delete any remaining runtime-authored direct rule rows skipped by grouped-rule dedupe.
- Restore only a specific deleted row whose removal changes generated runtime contracts, then document why the generator still consumed it.
- Update/remove audit tests that assert omitted-row accounting.
- Update the workbook editor referenced-delete warning so it no longer says rule convention is `normalization_status`, not deletion.
- Regenerate affected artifacts and compare runtime contracts while allowing audit artifact drift.
- Decide whether `build_rule_sources.py` still has unique read-only diagnostic value after workbook dead-end rows are retired.

Current result: 288 runtime-skipped rows were deleted (`rule_mapping`: 88, `grandSport_rule_mapping`: 200). `z06_rule_mapping` had no runtime-skipped control rows. Stingray, Grand Sport, and Z06 generated runtime contracts matched their pre-deletion snapshots, so no deleted row was restored.

### Pass D — “Required gate split”

Status: Completed. See `docs/audit-cleanup/pass-d-required-gate-split-spec.md`.

Goal: stop optional audit/report tooling from blocking normal form work after dead-end workbook rows are removed.

Create/clarify:

- default/live gate: app generation + runtime regressions
- workbook schema gate: only canonical active workbook contracts
- optional historical/audit gate: not part of normal readiness unless explicitly running old audit tooling

Current result: `AGENTS.md` and `README.md` now split default readiness from opt-in Grand Sport audit/report gates. `scripts/build_rule_sources.py`, `tests/grand-sport-rule-audit.test.mjs`, and `tests/audit-parser-metadata-loaders.test.mjs` were demoted from default readiness; no proof exception was found.

### Pass E — “Runtime metadata consolidation”

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
Pass A, Pass B, Pass C, and Pass D are complete. The next safe pass is Pass E: runtime metadata consolidation.

That keeps runtime metadata consolidation separate from rule-row cleanup and avoids deleting useful read-only diagnostics before proving whether they still have signal.
