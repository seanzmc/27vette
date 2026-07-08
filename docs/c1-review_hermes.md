C.1 is partially successful, but not ready for Pass D.

I rechecked the repo and rebuilt the current real-data plan for run:
form-output/ingest-wizard/20260707-193441-ea9e4c

Current state:

- Branch/worktree: main, clean.
- C.1 code/tests are present and the targeted fixture suite passes.
- The real review run is decisions-complete for grand_sport_x, zr1, zr1x.
- Rebuilt plan reports:
  - Stage 1 scaffolding: 52 ops
  - Stage 2 data: 5719 ops
  - plan.valid: true
  - blockingGaps: 0
  - deferrals: 0
  - model_interior_scope: 117 add ops
- But the dry-run is not clean:
  - dryRun.ok: false
  - stage2.ok: false
  - session stays decisions_complete, not plan_built
  - plan approval is therefore blocked.

Blocking C.1 finding:

- Stage 2 dry-run has 46 validation errors from plan rows that do not match canonical workbook headers:
  - 31 rule_mapping rows include unknown column active:
    - grandSportX_rule_mapping: 19
    - zr1_rule_mapping: 5
    - zr1x_rule_mapping: 7
  - 15 exclusive_groups rows include unknown column group_name:
    - grandSportX_exclusive_groups: 7
    - zr1_exclusive_groups: 4
    - zr1x_exclusive_groups: 4
- Header probe confirms canonical sheets:
  - grandSport_rule_mapping headers are rule_id, source_id, rule_type, target_id, original_detail_raw, body_style_scope, runtime_action,
    disabled_reason. No active.
  - grandSport_exclusive_groups headers are group_id, selection_mode, active, notes. No group_name.
- Code source:
  - scripts/corvette_form_generator/ingest/wizard/plan_builder.py:1006-1012 emits active into rule_mapping rows.
  - scripts/corvette_form_generator/ingest/wizard/plan_builder.py:1050 emits group_name into exclusive_groups rows.

What C.1 did complete:

- Added default_selection_rules to editor_ops global editable families.
- Added section-local option display order planning.
- Added blocking gap kinds for required canonical workbook gaps.
- Added endpoint identity resolution against planned and retained existing option rows.
- Added model_interior_scope add/update/no-op planning.
- Kept color_overrides / interior_components / asset_map as visible non-blocking deferrals.
- Fixture validation passes:
  - .venv/bin/python -m pytest tests/test_ingest_wizard_plan.py tests/test_ingest_wizard_decisions.py tests/test_ingest_wizard_server_pass_b.py
    tests/test_editor_ops_global_families.py -q
  - Result: 71 passed in 6.58s
  - node --check visualizer/ingest-wizard/wizard.js: passed
  - git diff --check: passed

Other findings:

- docs/ingest/pass-c/pass-c1-canonical-workbook-coverage-spec.md says implemented, but the real-data plan still fails dry-run.
- docs/ingest/README.md:20 is stale; it says Pass C implemented and D-F pending, but does not mention C.1 or the current dry-run blocker.
- fable5loop/STATE.md Last session is still B.9; I found no C.1 receipt under fable5loop/runs/.
- No Pass D apply entrypoint exists yet:
  - scripts/ingest_wizard_apply.py is absent.
  - No ingest_wizard_apply tests exist.

Recommended path to complete the ingest wizard:

A. Pass C.2 — real-data plan dry-run closure, no workbook writes.
Reasoning level for Sean/Codex: high.

Scope:

- Fix row-shape mismatch:
  - Remove active from rule_mapping plan rows unless the workbook header is explicitly expanded in an approved schema pass. Do not expand the workbook
    just to preserve a useless column.
  - Replace exclusive_groups.group_name with canonical notes, or omit it; group_id + selection_mode + active + notes are the current workbook contract.
- Add regression tests that use live-like headers for:
  - rule_mapping rejects unknown active.
  - exclusive_groups rejects unknown group_name.
  - rebuilt real-data style plan dry-runs stage2 clean.
- Rebuild run 20260707-193441-ea9e4c and require:
  - dryRun.ok true
  - stage2.ok true
  - session state plan_built
  - plan.valid true
  - blockingGaps 0
  - workbook still unchanged
- Update C.1/C.2 docs and fable STATE/receipt so the route map reflects reality.

B. Checkpoint 3 / Stage-6 visual review before any write.
Scope:

- Run the wizard in browser.
- Open the real plan report.
- Verify:
  - per-sheet op counts
  - clean-reprocess delete counts
  - no blocking gaps
  - visible non-blocking/manual items
  - unreviewed script-split list is acceptable or gets reviewed before write
- Approve the plan in UI only after dry-run is clean.
- Confirm plan-approval.json exists and session is plan_approved.

C. Pass D — approved workbook apply CLI.
Scope from docs/ingest/ingest-wizard-end-to-end-completion-spec.md:173-181:

- Add scripts/ingest_wizard_apply.py.
- Dry-run by default; --write required.
- Refuse unless:
  - session is plan_approved
  - decisions fingerprint still matches
  - workbook sha/mtime still matches plan
  - no Excel lock file
- Apply through editor_ops.apply_batch(..., write=True) and save_workbook_safely().
- Write apply-report.json with:
  - backup path
  - per-sheet expected/actual row counts
  - sampled cell-exact verification
  - mismatch list
- Tests:
  - unapproved plan refusal
  - dirty/fingerprint-shift refusal
  - Excel lock refusal
  - success on fixture workbook
  - post-write readback verification

D. Real workbook apply, after explicit approval.
Scope:

- Run Pass D dry-run.
- Run Pass D --write only after approval.
- Verify on disk.
- Run workbook/package/schema gates.
- Review workbook diff against backup.
- Models remain inactive/unpromoted after D.

E. Pass E — regeneration/preview gates.
Scope:

- Because generation discovery only sees active models, generate the new models against a scratch-copy activation first, not live workbook activation.
- Add preview gates:
  - tests/grand-sport-x-contract-preview.test.mjs
  - tests/zr1-contract-preview.test.mjs
  - tests/zr1x-contract-preview.test.mjs
- Generate runtime contracts and inspection artifacts.
- Triage generator validation errors back to workbook decisions; do not patch generated output.

F. Pass F — runtime promotion, one model at a time.
Order per approved spec:

1. grand_sport_x
2. zr1
3. zr1x

Per model:

- promote_model.py --model <key> dry-run
- explicit go/no-go
- promote_model.py --model <key> --write
- generate_form.py --model <key>
- generate_registry.py
- Add/update promotion gates patterned on z06-runtime-promotion:
  - registry composition
  - default model remains stingray
  - draft provenance stripped
  - model switching
  - model-scoped order build
  - dealer payload scoping, with no live dealer submission
- Manual browser verification:
  - model switch
  - body/trim/variant
  - option select/deselect
  - exclusives/rules/defaults
  - totals/summary/download
  - dealer modal scoping
  - desktop + mobile

Bottom line:

- Do not start Pass D yet.
- Next safe pass is a narrow C.2 real-data dry-run hardening pass.
- The immediate blocker is not business interpretation; it is plan-builder rows not matching canonical workbook headers.
