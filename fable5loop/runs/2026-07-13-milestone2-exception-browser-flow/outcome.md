# Milestone 2 Exception Queue Browser Flow Outcome

Started: 2026-07-13

## Task summary

- Goal: Implement the approved read-only Milestone 2 browser/API flow over the Milestone 1 canonical-row compiler.
- Changed surface: wizard session display/lifecycle services, localhost HTTP routes, forward browser stages, focused tests, ingest docs, and Fable closeout artifacts.
- Source of truth: current compiler queue/resolution/report artifacts and `exceptions.py` typed contracts; workbook and raw export remain read-only display/compile evidence.
- Protected boundaries: no `pass-c-3`, workbook write, apply approval, generation, publication, promotion, runtime/dealer change, or mutation of the retained Milestone 1 proof run.
- Workflow: vertical TDD slices, fixture-backed browser proof, then bounded independent verification.

## Required outcome criteria

1. Compact compile summary API and UI expose separate compile/plan/write/deployment readiness without shipping full compiler artifacts.
2. Filtered/paginated exception API and UI default to open actionable subjects while preserving explicit actionless source blockers.
3. Cards show raw, target-workbook/manifest, comparator, gate-impact, and proposed-row evidence without inventing missing evidence.
4. Only reason-compatible, workbook-writable typed controls are rendered and accepted.
5. Resolve/reopen require exact subject/version, validate server-side, automatically recompile, preserve audit semantics, and roll back cleanly on refusal.
6. Resume restores exact production compiler state; new runs leave the historical broad review path after model selection, while legacy states/routes remain available for debug/history.
7. Desktop/mobile browser smoke passes with zero console errors and no live-write control.
8. Milestone 1 focused regressions and broad affected gates pass; any full-suite baseline reds are independently classified.
9. Workbook, raw export, Milestone 1 proof artifacts, runtime/publication, apply/promotion, and dealer surfaces remain unchanged.
10. Final independent verifier returns PASS against a bound implementation/test/proof snapshot.
11. Implementation spec, parent design, ingest index, Fable receipt, and STATE close with actual evidence and identify Milestone 3 as the next unapproved checkpoint.

## Stop conditions

- Stop for a new product/business action or payload outside `exceptions.py`.
- Stop if evidence display requires workbook/runtime schema changes.
- Stop if failed resolve/reopen cannot restore a coherent previous state.
- Stop before Milestone 3 plan projection, workbook writes, generation, publication, promotion, or dealer changes.

## Independent verifier requirements

The final verifier inspects the approved Milestone 2 plan, final diff, focused/broad validation output, fixture API/browser evidence, current protected-surface hashes, and legacy-route preservation. It grades each criterion PASS/BLOCK and states explicitly that it edited no repository files.

Maximum maker/verifier iterations: 3 bounded final-snapshot rounds. Earlier implementation review is advisory and cannot serve as final acceptance after later edits.

## Implementation result

Status: **complete and independently verified PASS** on the final post-hardening snapshot.

Changed surfaces:

- `WizardSessionStore`: compact compiler summary, deterministic exception view, finite workbook choices, input freshness, compiler-effect action filtering, aggregate resolve/reopen rollback, lifecycle audit state, and per-run read/mutation serialization.
- `scripts/ingest_wizard_server.py`: compact compile GET/POST, strict filtered exception GET, exact resolve/reopen POST contracts, and duplicate/unknown query refusal.
- `visualizer/ingest-wizard/`: forward compile/exception stages, visible saved-run resume, separate readiness gates, typed evidence cards, filtering/pagination, resolve/reopen/recompile, keyboard/status hooks, and mobile layout.
- focused service, HTTP, and UI contract tests plus current workflow documentation.

The queue's raw `allowedActions` are not treated as browser authority. The server exposes only a complete action set whose outcomes the current compiler can project. Relationship, comparator-confirmation, identity-retention, and approved-removal actions without current row consumers remain explicit actionless tooling blockers.

## Proof result

Completed evidence:

- focused Milestone 2: 23 passed on the final implementation snapshot;
- broad affected gate: 298 passed plus 6 subtests on the final implementation snapshot;
- Python syntax, JavaScript syntax, and `git diff --check`: pass;
- workbook package/schema: valid, zero issues/errors/warnings;
- safe fixture browser resolve/reopen: blocker count 25 → 24 → 25, exact reviewer attribution, one record and one reopen audit event, no workbook/source mutation;
- retained real run browser: 20-card deterministic pages, 92 compiler-complete reviewer actions, real evidence rendering, no retained-artifact mutation, zero console errors;
- mobile Chrome proof: 390 px width, one-column filters/evidence, zero stepper overflow after correction;
- retained Milestone 1 compiler artifact hashes, canonical workbook, raw source, and tracked publication remained unchanged.
- full repository before receipt closure: 584 passed plus 13 subtests; four documented pre-existing failures and one expected open-receipt Fable contract failure;
- independent verification: exact-snapshot criteria passed after one strict blank-query repair; final two-file delta passed 4 HTTP tests with matching before/after hashes.

See `browser-verification.md` and `validation-output.txt`.

The final Fable validator result is appended to `validation-output.txt` after receipt and STATE closure.

## Preserved behavior

- Historical decision/review/plan states still resume through their original debug screens.
- Compiler, plan, write, and deployment readiness remain separate.
- The canonical workbook, source export, generated runtime, registry publication, apply/promotion paths, and dealer submission are unchanged.
- No Milestone 3 plan projection or write authority was added.

## Companion-file impact

- Workbook/source: inspected and hash/mtime protected; no change.
- Compiler artifacts: read/recompiled only in temporary fixture runs; retained real proof remained byte-identical.
- Runtime/publication/dealer: inspected by status/diff; no intentional change.
- Historical ingest spec: inspected-no-change because it already labels the broad decision path historical/superseded.
- Workflow docs: updated to identify Milestones 0–2 as implemented and Milestone 3 as unapproved.

## Residual boundary

Milestone 3 remains separately unapproved. No workbook write or deployment authority is implied by Milestone 2.

Unsupported row-producing exception actions require a future compiler-consumer pass before they may become browser controls. This is an explicit tooling blocker, not hidden follow-up authority.
