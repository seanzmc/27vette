# Pass 5 Checkpoint 4 Outcome Rubric — Durable Approval Lifecycle

Started: 2026-08-09T20:22:59-04:00
Owning specification: `docs/superpowers/specs/2026-07-22-reliable-workbook-database-workflow.md`

## Task summary

- **Goal:** Complete Pass 5 requirement 7 as one bounded checkpoint: submit the exact immutable ChangeSet and validated preview only through the shared approval service, persist exact immutable approval-attempt evidence, and map every outcome through specification §4.1.
- **Changed surface:** Workbook Manager durable schema, draft lifecycle service/API, focused tests, owning workflow documentation, and Fable closeout artifacts.
- **Source-of-truth decision:** `workbook_domain.service.approve_changeset()` exclusively owns approval validation and formal artifact construction. The immutable stored ChangeSet and formal preview attempt are the exact inputs. `WBM_DB` owns manager lifecycle and immutable attempt evidence only.
- **Protected boundaries:** No workbook or projection mutation; no apply implementation; no add/delete implementation; no generated artifact, publication, browser enablement, dealer, deployment, dependency, commit, or push change.
- **Pattern:** TDD plus independent adversarial verification; maximum three maker/verifier cycles.

## Required outcome criteria

1. A focused approval-lifecycle regression fails against the pre-checkpoint production code before implementation.
2. Approval is refused unless projection freshness is `current`, with durable refusal evidence and no shared-service call.
3. Approval is accepted only from `preview_ready` or `approval_confirmation_required`, loads the exact immutable ChangeSet and exact bound formal preview, and invokes only `workbook_domain.service.approve_changeset()` with actor and warning IDs.
4. Every returned dictionary is persisted semantically unchanged in an immutable attempt envelope and classified as formal approval versus early refusal.
5. §4.1 mappings are exact: success → `approved`; warning-confirmation mismatch → `approval_confirmation_required`; preview/binding/warning refusal → `approval_repreview_required`; exception with no dictionary → `approval_rejected`.
6. Resulting allowed verbs are exact and fail closed: approved permits apply/cancel; confirmation-required permits approve/cancel; re-preview-required permits retry-preview/cancel; rejected and stale permit cancel only.
7. Approval exceptions persist class/message without fabricating an approval artifact or hidden retry authority.
8. Re-submission from confirmation-required reuses the same ChangeSet and preview and creates a distinct attempt; re-preview-required can run the existing exact ChangeSet preview path and bind later approval to the new preview.
9. Durable schema migration preserves existing drafts, ChangeSets, preview attempts, and verified version-3 projection; approval attempts reject update/delete at the database.
10. The API exposes only approval, does not apply or write, and the focused plus checkpoint acceptance gates pass with protected surfaces unchanged.
11. Owning specification, Workbook Manager guidance, fixed STATE handoff, and complete run receipt agree on remaining Pass 5 requirement 8 and exit-gate work.
12. An independent verifier returns PASS from the final diff and recorded execution evidence.

## Stop condition

Stop after requirement 7 is independently verified. Requirement 8, coordinated add/delete behavior, dependency-bypass removal, the full Pass 5 exit gate, apply/write hardening, and browser enablement remain later work.
