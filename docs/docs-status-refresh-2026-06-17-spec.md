# Docs Status Refresh Spec — 2026-06-17

Recommended reasoning level: medium.

## Status

Approved and implemented 2026-06-17.

Implementation result: the three stale specs now have completed status notes, and `docs/persisting-audit-findings-2026-06-14.md` now separates completed source-cleanup passes from the remaining action-plan queue.

## Diagnosis

Three recent docs under `docs/` still read as unimplemented specs even though current workbook/source probes show their scoped work has already landed. A standing audit handoff also still lists or frames some of that completed work as pending. This makes the next-pass queue harder to trust and risks re-running already-completed workbook/data cleanup instead of moving to the actual remaining architecture cleanup.

Current evidence inspected:

- Active branch/status: `generator-simplification-pass1`, clean worktree at inspection time.
- Recent-doc inventory: `docs/**/*.md` modified in the last three days.
- `docs/active-model-nonruntime-option-row-purge-spec.md`
  - Still says `Spec only. Do not implement until approved.`
  - Current workbook probe shows every approved purge-list option row is absent from the matching active model option sheet and matching OVS sheet:
    - `stingray_options` / `stingray_ovs`
    - `grandSport_options` / `grandSport_ovs`
    - `z06_options` / `z06_ovs`
  - Current workbook probe shows active-model `section_presentation` rows for `sec_cust_002` are absent.
  - Deferred active emitted standard-tech / connected-service rows remain active, as the spec required.
- `docs/active-seat-standard-equipment-ownership-spec.md`
  - Still says `Spec only. Do not implement until approved.`
  - Current workbook probe shows Stingray now has exactly four active canonical seat rows in `sec_seat_002`:
    - `opt_aq9_001`
    - `opt_ah2_001`
    - `opt_ae4_002`
    - `opt_aup_001`
  - Current workbook probe shows the three required Stingray seat price rules exist:
    - `sr_pr_1lt_ae4_seat_001`
    - `sr_pr_3lt_ae4_seat_001`
    - `sr_pr_3lt_ah2_seat_001`
  - Deferred active `sec_tech_001` rows remain active, as intended.
- `docs/rule-mapping-column-cleanup-pass1-spec.md`
  - Still says `Spec only. Do not implement until approved.`
  - Current workbook probe shows the retired columns are absent from all promoted rule-mapping sheets:
    - `rule_mapping`
    - `grandSport_rule_mapping`
    - `z06_rule_mapping`
  - Current kept headers are:
    - `rule_id`
    - `source_id`
    - `rule_type`
    - `target_id`
    - `original_detail_raw`
    - `body_style_scope`
    - `runtime_action`
    - `disabled_reason`
  - Current workbook probe shows `zr1_rule_mapping` and `zr1x_rule_mapping` sheets are absent, and future-model rule-mapping source registrations are absent.
- `docs/persisting-audit-findings-2026-06-14.md`
  - Still has the right broad structure for remaining audit items, but should be refreshed so the summary/recommended passes do not imply the completed nonruntime purge, seat canonicalization, or rule-mapping column cleanup are still pending.
  - It should keep truly persisting items visible: fallback retirement/boundary narrowing, optional audit tooling status, Stingray rear-script badges, display-order guard/scaffold decision, cross-model order/copy drift, Z06 ID drift, Stingray group-ID cosmetic drift, and interior CSV/config remnants.

Root cause:

The implementation passes moved faster than the repo docs that track their status. The source of truth is now the workbook/source tree and generated tests, not the stale `Status` sections in those planning docs.

Risk level: low. This is a docs/status pass only. It should not change workbook data, generated artifacts, runtime JavaScript, tests, or dealer-submission behavior.

Change type: docs-only.

## Exact Files to Change

Update these existing docs:

- `docs/active-model-nonruntime-option-row-purge-spec.md`
  - Change status from spec-only to completed.
  - Add a concise implementation-result note naming the workbook/source state now verified.
  - Preserve the original approved scope and constraints as historical record.
  - Keep the deferred active standard-tech / connected-service row note visible as a non-goal / future ownership pass.

- `docs/active-seat-standard-equipment-ownership-spec.md`
  - Change status from spec-only to completed.
  - Add a concise implementation-result note naming the four canonical Stingray seat rows and the three price rules now present.
  - Preserve the original migration map as historical record.
  - Keep active `sec_tech_001` / connected-service rows explicitly deferred.

- `docs/rule-mapping-column-cleanup-pass1-spec.md`
  - Change status from spec-only to completed.
  - Add a concise implementation-result note naming the final promoted rule-mapping headers and the removed future-model rule-mapping sheets/source registrations.
  - Preserve `body_style_scope` and `runtime_action` as intentionally retained columns / future cleanup candidates.

- `docs/persisting-audit-findings-2026-06-14.md`
  - Refresh the summary so completed nonruntime purge, Stingray seat canonicalization, and rule-mapping column cleanup are not listed or implied as pending.
  - Add completed-status bullets for those three items with source-of-truth evidence.
  - Reclassify remaining work into current categories:
    - still persisting / needs new spec,
    - intentionally deferred / non-goal,
    - optional tooling only,
    - cosmetic/tooling-low-priority.
  - Update `Recommended next passes` so the first implementation recommendation remains fallback-retirement/boundary-narrowing, not a repeat of the completed specs.
  - Update the evidence footer with the probes run for this refresh.

No workbook sheets, generated artifacts, runtime files, tests, or config files should change in this pass.

## Constraints

- Docs-only pass.
- No workbook writes.
- No generator runs unless a validation command unexpectedly requires them; they should not be needed.
- No generated artifact edits.
- No runtime JavaScript edits.
- No test edits.
- No new dependencies.
- No visual/runtime/dealer behavior changes.
- Preserve workbook source-of-truth framing: docs should report that workbook/source probes verified completion; they should not invent new behavior or expand cleanup scope.
- Do not rewrite the historical specs into implementation reports so heavily that the approved scope is lost. Add status/results at the top and leave the original plan readable.
- Do not mark deferred work as done:
  - active standard-tech / connected-service ownership is still deferred,
  - fallback constants still need a later pass,
  - optional audit tooling remains intentionally opt-in,
  - body_style_scope/runtime_action cleanup remains future/parity work.

## Required Preflight Before Editing

1. Confirm clean branch/status:

```sh
git status --short --branch
```

2. Re-run a read-only workbook probe immediately before patching docs to verify the status claims are still true:

```sh
.venv/bin/python - <<'PY'
from openpyxl import load_workbook
wb = load_workbook('stingray_master.xlsx', read_only=True, data_only=True)
# Probe:
# - active Stingray canonical seat rows and price rules
# - nonruntime purge-list rows absent from active option/OVS sheets
# - promoted rule_mapping headers reduced
# - zr1/zr1x rule_mapping sheets and registrations absent
# - promoted runtime metadata coverage if cited in persisting-audit refresh
wb.close()
PY
```

3. Re-run code-symbol probes for items still listed as persisting:

```sh
rg -n "orderSectionDefinitions|stepOrderSectionKeys|STEP_ORDER|STEP_LABELS|CONTEXT_SECTIONS|interior_reference_path" form-app scripts docs/persisting-audit-findings-2026-06-14.md
```

4. Stop and revise the spec before implementation if the live probes contradict any completion claim above.

## Implementation Plan

1. Patch the three completed specs first.
   - Keep edits small and near each file's `## Status` / top matter.
   - Add `Completed` status with date and a short implementation result.
   - Do not delete the original approval question or implementation plan unless it is actively misleading; prefer adding a clear historical note.

2. Patch `docs/persisting-audit-findings-2026-06-14.md`.
   - Move completed items out of the still-persisting list.
   - Add a refreshed completed-items block for:
     - active-model nonruntime option-row purge,
     - Stingray seat canonicalization,
     - rule-mapping column cleanup pass 1.
   - Keep the actual remaining action plans, but update wording so they point to the next real pass.
   - Keep fallback-retirement/boundary-narrowing as the recommended first implementation pass after this docs refresh.

3. Run docs-only validation.

4. Review the docs diff for accidental scope expansion.

## Validation Plan

Docs diff review:

```sh
git diff -- docs/active-model-nonruntime-option-row-purge-spec.md \
  docs/active-seat-standard-equipment-ownership-spec.md \
  docs/rule-mapping-column-cleanup-pass1-spec.md \
  docs/persisting-audit-findings-2026-06-14.md
```

Stale-status scan:

```sh
rg -n "Spec only\. Do not implement until approved|Approve this pass|Approve Pass 1|Approve a Stingray-first" \
  docs/active-model-nonruntime-option-row-purge-spec.md \
  docs/active-seat-standard-equipment-ownership-spec.md \
  docs/rule-mapping-column-cleanup-pass1-spec.md \
  docs/persisting-audit-findings-2026-06-14.md
```

Expected scan result:

- The three completed specs should no longer present themselves as unimplemented.
- Historical approval questions may remain only if clearly labeled as historical/pre-implementation text, not current action required.
- `persisting-audit-findings-2026-06-14.md` should not list completed seat/nonruntime/rule-mapping work as still pending.

Whitespace/syntax guard:

```sh
git diff --check
```

No workbook/schema/generator/runtime gates are required because this pass is docs-only and must not touch workbook, generated, runtime, or test files. If implementation accidentally changes any non-doc file, stop and revert that accidental change or revise this spec before proceeding.

## Risks

- Overstating completion from stale memory instead of current workbook/source probes. Mitigation: re-run read-only probes before editing.
- Removing useful historical context from specs. Mitigation: add status/results without deleting the approved scope.
- Hiding real deferred work. Mitigation: keep deferred `sec_tech_001`, fallback constants, optional audit tooling, and future rule-mapping cleanup explicitly listed.
- Making `persisting-audit-findings` too broad. Mitigation: only refresh items affected by current source evidence and the next-pass queue.

## Non-Goals

- No fallback-retirement implementation.
- No connected-service / `sec_tech_001` ownership redesign.
- No workbook row changes.
- No generated artifact refresh.
- No runtime JS cleanup.
- No test changes.
- No optional audit tooling retirement.
- No copy/order/product-decision cleanup.
- No body_style_scope or runtime_action cleanup.

## Handoff Requirements

The implementation handoff must report:

- What changed: exact docs touched and status wording updated.
- What did not change: workbook, generated artifacts, runtime JS, tests, dealer boundaries.
- Gate results: docs diff review, stale-status scan, `git diff --check`; any gates not run and why.
- Manual verification pending: none expected beyond reviewing the docs diff.
- Next step guidance: after this docs status refresh, the next recommended implementation pass is fallback-retirement/boundary-narrowing for promoted-model runtime/order-summary fallback constants.

## Approval Result

Approved by the user as `approved` and implemented on 2026-06-17.
