# Independent Verifier Report — Pass 5 Checkpoint 4

## Verdict

PASS — Pass 5 Checkpoint 4 satisfies all 12 outcome criteria. Cycle-1 findings are corrected, requirement 7 is independently verified, and Checkpoint 4 may close.

The loop validator’s six failures are historical receipt debt confined to older Checkpoint 1 and preview-lifecycle folders. They do not implicate the current receipt, implementation, STATE pointer, protected surfaces, or requirement-7 evidence, so they do not block this checkpoint.

Cycle 1 returned FAIL. It required current-authority/receipt reconciliation, retained execution evidence, fail-closed handling for unknown service outcomes, direct workbook byte/mtime containment assertions, and adversarial exact-preview binding. The maker addressed each finding with RED/GREEN evidence before cycle 2. Both verifiers explicitly stated they edited no files.

## Criteria

1. **PASS** — Credible retained RED evidence exists. Detached baseline `4338e52` is the direct ancestor of implementation commit `1a359af` and contains no approval service wrapper, mapping, or endpoint. Recorded result: `11 failed, 1 passed in 0.48s`.
2. **PASS** — Non-current projection approval persists a `manager_refusal` attempt as `stale` with `["cancel"]`, raises `projection_not_current`, and does not call the shared service.
3. **PASS** — Approval is limited to `preview_ready` and `approval_confirmation_required`. The query binds the formal preview by draft ID, stored ChangeSet ID, stored semantic fingerprint, artifact kind, and `preview_ready` state. Only `workbook_domain.service.approve_changeset()` receives the exact stored ChangeSet, preview, actor, and warning IDs.
4. **PASS** — Returned dictionaries are serialized without semantic modification in immutable attempt envelopes. Formal approval versus early refusal is classified solely from the shared approval schema.
5. **PASS** — §4.1 mappings are exact. Unknown outcomes now fail closed to `approval_rejected`, rather than inheriting retry-preview authority.
6. **PASS** — Allowed verbs match the specification: approved → apply/cancel; confirmation-required → approve/cancel; re-preview-required → retry-preview/cancel; rejected and stale → cancel only.
7. **PASS** — Exceptions persist class and message, leave `result` null, use `artifact_kind="exception"`, and provide no approval artifact or retry authority.
8. **PASS** — Confirmation resubmission creates a distinct attempt while reusing the exact ChangeSet and preview. Re-preview uses the immutable ChangeSet and later approval selects the newly bound formal preview.
9. **PASS** — Schema 7 migration tests preserve prior drafts, ChangeSets, preview attempts, and verified version-3 projection state. Database triggers reject approval-attempt update and deletion.
10. **PASS** — The new API route exposes approval only. It contains no apply or workbook-write call. The endpoint regression checks projection data plus exact workbook bytes and nanosecond mtime. Protected customer/workbook/generated/publication surfaces are absent from both committed and working diffs.
11. **PASS** — The specification, root README, Workbook Manager README, STATE handoff, and current receipt consistently state that requirements 1–7 are implemented and requirement 8/full Pass 5 exit-gate work remains open.
12. **PASS** — Cycle-2 independent adversarial verification returns PASS from the final code, working diff, receipt evidence, and recorded validation.

## Evidence inspected

- `AGENTS.md`
- Owning specification §4.1, Pass 5 requirement 7, and Checkpoint 4
- Entire current Checkpoint 4 receipt: `outcome.md`, `run.json`, `validation-output.txt`, and `verifier-report.md`
- Current Git status, staged rename, working diff, committed implementation diff, and commit ancestry
- `workbook-manager/backend/app/drafts.py`
- `workbook-manager/backend/app/db.py`
- `workbook-manager/backend/app/main.py`
- `workbook-manager/backend/app/schemas.py`
- `tests/test_workbook_manager_changeset_lifecycle.py`
- Root `README.md`, `workbook-manager/README.md`, and `fable5loop/STATE.md`
- Approval/apply/write call-site searches
- Protected-surface status for `stingray_master.xlsx`, `form-output/`, and `form-app/`

## Validation Output Inspected

- Detached-baseline RED: `11 failed, 1 passed in 0.48s`
- Cycle-1 hardening RED: `2 failed, 5 subtests passed in 0.31s`
- Approval lifecycle GREEN: `8 passed, 5 subtests passed in 0.31s`
- Affected inventory: `109 passed, 17 subtests passed in 5.70s`
- Final Manager inventory: `138 passed, 2 skipped, 1 warning, 17 subtests passed in 932.34s`
- The two skips are explicit slow copied-workbook writer gates outside this read-only checkpoint.
- `git diff --check`: passed.
- Protected-surface status: empty.
- Loop validator: failed only for six named artifacts missing from two older receipt folders; no current Checkpoint 4 or STATE-pointer failure was reported.

The older receipt omissions are genuine historical closeout debt, but retroactively inventing their outputs would be worse evidence. They do not block this bounded checkpoint because the current receipt is complete, directly validated, correctly referenced, and independent of those older missing artifacts.

## Required Fixes Before Pass

None.

## Durable Lesson Candidates

- Fail closed for every unrecognized shared-service outcome; never grant retry authority through a default branch.
- Artifact selection must bind through immutable identity fields, not merely “latest attempt for draft.”
- No-write endpoint tests should measure the canonical artifact’s bytes and mtime directly.
- Retained RED evidence should identify the exact baseline commit, interpreter, and result.
- Historical receipt debt should remain explicit rather than being repaired with reconstructed output.

These lessons are already represented by the specification, current regression coverage, and loaded migration procedure; no additional durable guidance change is required.

## File Edit Statement

Both independent read-only verifier cycles explicitly stated they edited no files.
