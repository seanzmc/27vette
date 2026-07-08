**Findings**

- **P1: Current C.1 real plan is not Pass-D-ready.**
  - The newest plan says `Plan valid: True · Dry run ok: False` in [apply-plan.md](/Users/seandm/Projects/27vette/form-output/ingest-wizard/20260707-193441-ea9e4c/apply-plan.md:5).
  - Stage 2 fails with 46 validation errors: `*_rule_mapping` rows include an `active` column and `*_exclusive_groups` rows include `group_name`, but the live workbook headers do not have those columns.
    - Evidence: [apply-plan-dryrun.json](/Users/seandm/Projects/27vette/form-output/ingest-wizard/20260707-193441-ea9e4c/apply-plan-dryrun.json:18) and the emitting code in [plan_builder.py](/Users/seandm/Projects/27vette/scripts/corvette_form_generator/ingest/wizard/plan_builder.py:1006) / [plan_builder.py](/Users/seandm/Projects/27vette/scripts/corvette_form_generator/ingest/wizard/plan_builder.py:1050).
  - I reproduced the two-stage dry run in a temp copy; stage 1 passed, stage 2 failed the same way.

- **P1: C.1 fixture coverage missed the real dry-run failure.** The focused tests pass, but the relationship/exclusive test only inspects plan JSON; it does not run `apply_batch()` on a plan containing those rows. Add a regression that builds relationship/exclusive decisions and dry-runs stage 2 against live-shaped headers.

- **P2: The current run is not approved.** `form-output/ingest-wizard/20260707-193441-ea9e4c` has a valid `apply-plan.json`, but no `plan-approval.json`, and `session.json` is still `decisions_complete`, not `plan_approved`.

**Remaining Tasks**

1. Fix C.1 dry-run blocker: align planned `rule_mapping` and `exclusive_groups` rows to workbook headers, then rebuild the current plan until `dry_run.ok=true`.
2. Add the missing dry-run regression for relationship/exclusive ops.
3. Rebuild and approve the plan in the wizard. Current plan counts: 52 stage-1 ops, 5,719 stage-2 ops, no blocking gaps, but dry-run failed.
4. Decide whether the large “script splits carried unreviewed” counts are acceptable before apply: GSX 178, ZR1 155, ZR1X 156.
5. Implement Pass D: `scripts/ingest_wizard_apply.py`, fingerprint/mtime refusal, Excel lock refusal, `save_workbook_safely()`, apply report, fixture tests.
6. Run the live workbook apply only after `plan_approved`; verify workbook row counts and sampled cells, then package/schema gates.
7. Implement Pass E: scratch-copy generation for inactive models, inspection artifacts, and preview gates for `grand_sport_x`, `zr1`, and `zr1x`.
8. Implement Pass F per model: promote, generate runtime contract, publish registry, add runtime-promotion gates, verify model switching and dealer payload scoping.
9. After live models are stable, handle deferred structured surfaces: full price rules, rule groups/members, exterior paint authoring, `color_overrides`, `interior_components`, and `asset_map`.

**Validation Run**

- `pytest tests/test_ingest_wizard_plan.py tests/test_ingest_wizard_decisions.py tests/test_ingest_wizard_server_pass_b.py tests/test_editor_ops_global_families.py -q`: 71 passed.
- `node --check visualizer/ingest-wizard/wizard.js`: passed.
- `git diff --check`: passed.
- `scripts/validate_workbook_schema.py stingray_master.xlsx`: valid, 0 issues.
- `git status --short`: clean.

I made no edits.
