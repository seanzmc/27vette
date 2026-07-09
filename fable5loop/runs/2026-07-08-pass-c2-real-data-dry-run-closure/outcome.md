# Outcome rubric · 2026-07-08 · Pass C.2 — real-data dry-run row-shape closure

Task summary:
- Goal: close the C.1 real-data dry-run blocker by making planned relationship/exclusive rows match canonical workbook headers, then verify and approve the clean stage-6 plan for run `20260707-193441-ea9e4c`.
- Changed surface: ingest wizard plan-builder/tests/docs plus loop receipt/STATE closeout. Run-scoped approval artifact written under ignored `form-output/ingest-wizard/20260707-193441-ea9e4c/`.
- Source-of-truth decision: workbook headers are authoritative for `*_rule_mapping` and `*_exclusive_groups`; plan rows must omit non-canonical fields rather than expanding workbook schema.
- Protected boundaries: no `stingray_master.xlsx` writes; no generated runtime artifacts; no `form-app/`; no dealer submission; no Pass D writer or real workbook apply.
- Expected files/artifacts: committed C.2 code/docs/tests at `a25d714`; this receipt folder; `fable5loop/STATE.md`; ignored `plan-approval.json` for the reviewed run.

Required outcome criteria:
1. C.2 plan rows match canonical headers: `*_rule_mapping` add rows contain only `rule_id`, `rule_type`, `source_id`, `target_id`; `*_exclusive_groups` add rows contain `active`, `group_id`, `notes`, `selection_mode` and no `group_name`.
2. Real run `20260707-193441-ea9e4c` is dry-run clean: `plan.valid=true`, `blockingGaps=0`, `gaps=0`, `uncoveredApprovedDecisions=0`, stage 1 = 52 ops, stage 2 = 5,719 ops, `dryRun.ok=true`, stage2 errors = 0, schemaErrors = 0.
3. Stage-6 review evidence reconciles: script-split carry-forwards remain visible (GSX 178, ZR1 155, ZR1X 156), presentation quintet counts are present, `model_interior_scope` = 117.
4. Approval gate is explicitly recorded: `plan-approval.json` exists, session state is `plan_approved`, and approval was made only after artifact/endpoint checks.
5. Validation is real: targeted wizard/plan/editor tests, `node --check visualizer/ingest-wizard/wizard.js`, `git diff --check`, and Fable loop validator are run with recorded outputs.
6. Loop closeout is complete: receipt files exist, `STATE.md` Last session points here, and the skill-update decision is recorded.

Stop condition:
- Stop after plan approval and receipt/STATE closeout. Do not start Pass D or mutate the workbook in this run.
