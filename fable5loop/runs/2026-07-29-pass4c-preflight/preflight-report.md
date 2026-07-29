# Pass 4 Stage C preflight report

Date: 2026-07-29
Source commit: `3515f72` (`Complete Pass 4 Stage B retirement`)
Authority: `docs/superpowers/specs/2026-07-23-validation-single-lane-active-surface-cleanup.md`, Stage C and §§9.3–9.4

## Verdict

**READY FOR A NARROW, SEPARATELY APPROVED STAGE C IMPLEMENTATION.**

The current tree supports a docs/path-only cleanup. This preflight does not authorize or perform any move or deletion. The implementation manifest below deliberately keeps nine plans at their current paths: six explicitly open plans, one plan with contradictory completion evidence, and two completed Grand Sport plans whose paths remain canonical-workbook provenance.

## Working definition of done for implementation

- Move only the exact 19 plans and four historical documents listed below: ten plans are already top-level closed; nine must receive the exact top-level closure reconciliation in §1.1 before they move.
- Delete only the exact three redundant review/log files listed below, after appending the specified evidence-retirement note to the July 5 verifier receipt.
- Keep the nine non-move plans classified below at their current paths.
- Add the proposed compact current-state header to `fable5loop/STATE.md` without rewriting chronology.
- Update only the exact active pointers named below and close the owning specification.
- Preserve `stingray_master.xlsx`, all code/tests, generated and published artifacts, runtime/dealer behavior, standing guidance owners (`AGENTS.md`, `README.md`, and `docs/route-map.md`), pre-existing archives, and prior Fable receipts except for the single append-only evidence-retirement note.
- Validate the exact manifest mechanically; rollback is one Git revert.

## 1. Exact plan inventory

Mechanical inventory: `git ls-files '.hermes/plans/*.md'` returned **28** tracked plans.

Partition proof:

- `PROPOSE_ARCHIVE_ALREADY_CLOSED`: 10
- `PROPOSE_CLOSE_THEN_ARCHIVE`: 9
- `KEEP_OPEN`: 6
- `KEEP_HISTORICAL_INPUT`: 2
- `NEEDS_DECISION`: 1
- Total: 28
- Missing, duplicate, or extra classifications: none

### 1.1 Proposed plan moves — 19

Each destination was checked on disk and in the Git index; no collision exists.
Ten plans already carry top-level completion/implementation closure. The nine
marked `CLOSE_THEN_ARCHIVE` below have landed implementation evidence but no
top-level closeout. An approved Stage C implementation must first add a dated,
top-level archival note to each of those nine stating that the implementation
is present at the named evidence commit(s), that any trailing approval prompt is
historical, and that current commands remain owned by `README.md`; only then may
the same patch move the file. Preserve each historical body unchanged.

1. `.hermes/plans/asset-map-exterior-color-url-refresh.md`
   → `docs/archive/completed-specs/asset-map-exterior-color-url-refresh.md`
   - `CLOSE_THEN_ARCHIVE`.
   - Evidence: `bc68fdd` co-committed workbook, generated, registry, and test changes and is an ancestor of `3515f72`.
2. `.hermes/plans/asset-map-sync-legacy-retirement-pass3-spec.md`
   → `docs/archive/completed-specs/asset-map-sync-legacy-retirement-pass3-spec.md`
   - Evidence: explicit 2026-07-05 completion record; implementation commit `cb97731`.
3. `.hermes/plans/color-override-normalization-spec.md`
   → `docs/archive/completed-specs/color-override-normalization-spec.md`
   - `CLOSE_THEN_ARCHIVE`.
   - Evidence: `6e4d052` implementation and retained D30/R6X tests.
4. `.hermes/plans/cross-model-stale-gate-expectations-spec.md`
   → `docs/archive/completed-specs/cross-model-stale-gate-expectations-spec.md`
   - Evidence: explicit implementation/verifier PASS and commit `c7939f0`.
5. `.hermes/plans/fable5-source-doc-rename-pass7-spec.md`
   → `docs/archive/completed-specs/fable5-source-doc-rename-pass7-spec.md`
   - Evidence: explicit completion; current owner is `fable5loop/source-guidance.md`.
6. `.hermes/plans/form-mobile-ux-consistency-spec.md`
   → `docs/archive/completed-specs/form-mobile-ux-consistency-spec.md`
   - Evidence: explicit implementation/verifier PASS; `1b21c77` is in current history.
7. `.hermes/plans/generator-simplification-pass2-runtime-payload-trim.md`
   → `docs/archive/completed-specs/generator-simplification-pass2-runtime-payload-trim.md`
   - `CLOSE_THEN_ARCHIVE`.
   - Evidence: plan marks itself historical pending archival; `3d41f6b` implementation and current path-aware trim coverage.
8. `.hermes/plans/grand-sport-z06-stripe-workbook-rule-fix.md`
   → `docs/archive/completed-specs/grand-sport-z06-stripe-workbook-rule-fix.md`
   - `CLOSE_THEN_ARCHIVE`.
   - Evidence: `ee2bf7c` co-committed the plan, workbook correction, and regenerated artifacts.
9. `.hermes/plans/live-deltas-into-local-spec.md`
   → `docs/archive/completed-specs/live-deltas-into-local-spec.md`
   - `CLOSE_THEN_ARCHIVE`.
   - Evidence: `0b116da` committed the J57 generated/runtime/test half; `b42ce5e` committed the `requires_any` selection/runtime fix. Both are ancestors of `3515f72`.
10. `.hermes/plans/live-runtime-merge-readiness-no-behavior-change-spec.md`
    → `docs/archive/completed-specs/live-runtime-merge-readiness-no-behavior-change-spec.md`
    - `CLOSE_THEN_ARCHIVE`.
    - Evidence: plan is explicitly historical pending archival; `54062da` implementation.
11. `.hermes/plans/paint-accent-progress-checkmarks-spec.md`
    → `docs/archive/completed-specs/paint-accent-progress-checkmarks-spec.md`
    - Evidence: explicit completion and implementation commit `1564361`.
12. `.hermes/plans/r6x-interior-components-spec.md`
    → `docs/archive/completed-specs/r6x-interior-components-spec.md`
    - `CLOSE_THEN_ARCHIVE`.
    - Evidence: body records completion; `bc61572` and current `$995` component/D30-independence tests.
13. `.hermes/plans/route-map-condensation-pass6-spec.md`
    → `docs/archive/completed-specs/route-map-condensation-pass6-spec.md`
    - Evidence: explicit completion and implementation commit `f8c07bc`.
14. `.hermes/plans/rule-audit-orphan-retirement-pass2-spec.md`
    → `docs/archive/completed-specs/rule-audit-orphan-retirement-pass2-spec.md`
    - Evidence: explicit completion and implementation commit `cb97731`.
15. `.hermes/plans/src-images-retirement-pass5-spec.md`
    → `docs/archive/completed-specs/src-images-retirement-pass5-spec.md`
    - Evidence: explicit completion; `cb97731` removed the tracked image inventory.
16. `.hermes/plans/stingray-engine-appearance-display-order-match-grand-sport.md`
    → `docs/archive/completed-specs/stingray-engine-appearance-display-order-match-grand-sport.md`
    - `CLOSE_THEN_ARCHIVE`.
    - Evidence: `8e6b406` co-committed workbook order, generated output, and tests.
17. `.hermes/plans/superpowers-untrack-pass1-spec.md`
    → `docs/archive/completed-specs/superpowers-untrack-pass1-spec.md`
    - Evidence: explicit completion and implementation commit `ab21031`.
18. `.hermes/plans/vehicle-setup-copy-workbook-ownership-spec.md`
    → `docs/archive/completed-specs/vehicle-setup-copy-workbook-ownership-spec.md`
    - Evidence: explicit 2026-07-22 completion receipt and commit `e397389`.
19. `.hermes/plans/z06-runtime-rule-correction-spec.md`
    → `docs/archive/completed-specs/z06-runtime-rule-correction-spec.md`
    - `CLOSE_THEN_ARCHIVE`.
    - Evidence: `ef9769e` implemented the writer/workbook/generated/test changes; the later Pass 2 plan records Pass 1 complete and green.

### 1.2 Keep open — 6

1. `.hermes/plans/layered-visualizer-integration-spec.md`
   - Status: awaiting approval; no approved implementation closure.
2. `.hermes/plans/rule-normalization-pass1-redundant-exclusive-excludes.md`
   - Status: approval spec; related normalization commits do not prove the complete stated pass.
3. `.hermes/plans/rule-normalization-pass2-grouped-excludes.md`
   - Status: proposed only; related grouped-exclusion work does not override the explicit unapproved state.
4. `.hermes/plans/rule-normalization-pass7b-failed-fix-correction.md`
   - Status: proposed only. Current tests cover several reported behaviors, but the plan required complete browser proof and has no closeout.
5. `.hermes/plans/z06-carbon-wheel-package-disabled-state-spec.md`
   - Status: approval request with no closeout. Current tests cover the reported disabled state, but the plan required workbook/generator/browser closure.
6. `.hermes/plans/z06-interior-accessory-cleanup-pass2-spec.md`
   - Status: implementation approval request with no closeout. Current tests cover major acceptance points, but no complete nineteen-point closure receipt exists.

These files stay current so Stage C does not silently convert unclosed product/runtime work into completed history.

### 1.3 Keep at current path as canonical historical input — 2

1. `.hermes/plans/grand-sport-stripe-heritage-reverse-exclusions-spec.md`
2. `.hermes/plans/grand-sport-jake-heritage-hash-reverse-exclusions-spec.md`

Both are completed, but their exact current paths are embedded in canonical `stingray_master.xlsx` cells (`grandSport_rule_groups!I30:I50`) and emitted into `form-output/runtime/grand-sport-runtime-contract.json` and `form-app/data.js`. Moving them under Stage C would create dangling current provenance and would require an unauthorized workbook write/regeneration/publication pass. They therefore remain stable historical-input paths.

### 1.4 Needs decision — 1

- `.hermes/plans/z06-package-pricing-cascade-spec.md`
  - The file contains approved implementation decisions but ends with an approval request.
  - `c555377` added workbook/script changes, while the later runtime-rule plan says that script was incomplete and did not prove all intended runtime behavior.
  - Stage C must leave it in place. A separate product/runtime closure audit may later classify it.

## 2. Historical documents and review clutter

### 2.1 Proposed historical-document moves — 4

1. `docs/db_audit-7-22.md`
   → `docs/archive/old-reports/db_audit-7-22.md`
2. `docs/superpowers/plans/2026-07-16-workbook-congruent-relational-database.md`
   → `docs/archive/completed-specs/workbook-manager/2026-07-16-workbook-congruent-relational-database.md`
3. `docs/superpowers/specs/2026-07-16-workbook-congruent-relational-database-design.md`
   → `docs/archive/completed-specs/workbook-manager/2026-07-16-workbook-congruent-relational-database-design.md`
4. `docs/react-editor prompt.md`
   → `docs/archive/completed-specs/workbook-manager/react-editor-prompt.md`

All four contain unique historical evidence and must be moved, not deleted. All destinations are free.

### 2.2 Proposed exact deletions — 3

1. `docs/claude_output-workbookEditor.md`
   - Its implementation claims and skipped-gate notes are retained more precisely by `fable5loop/runs/2026-07-15-workbook-manager-stage1/{outcome.md,validation-output.txt,verifier-report.md,run.json}` and current commands in `workbook-manager/README.md`.
2. `fable5loop/runs/2026-07-05-cross-model-regression-hardening/multi-model-runtime-switching-full.log`
3. `fable5loop/runs/2026-07-05-cross-model-regression-hardening/stingray-form-regression-full.log`
   - Decisive counts/classifications are retained in that run's `validation-output.txt`, `outcome.md`, and `verifier-report.md`.
   - Before deletion, append a dated retirement note to the verifier report preserving the fact that the independent verifier originally inspected both raw logs and stating where the distilled evidence remains. Do not rewrite its original criteria table.

Retain every other file in both Fable receipt directories.

## 3. Exact active-reference updates

Implementation must update only current/navigation references; chronological receipts may preserve original paths.

1. `docs/superpowers/specs/2026-07-22-reliable-workbook-database-workflow.md`
   - `docs/db_audit-7-22.md` → `docs/archive/old-reports/db_audit-7-22.md`
   - `.hermes/plans/vehicle-setup-copy-workbook-ownership-spec.md` → `docs/archive/completed-specs/vehicle-setup-copy-workbook-ownership-spec.md`
2. `.hermes/plans/z06-interior-accessory-cleanup-pass2-spec.md`
   - `.hermes/plans/z06-runtime-rule-correction-spec.md` → `docs/archive/completed-specs/z06-runtime-rule-correction-spec.md`
3. The moved July 16 plan/design
   - Repair their top current-owner pointer to `docs/superpowers/specs/2026-07-22-reliable-workbook-database-workflow.md`.
   - Point plan references to the archived design destination.
   - Preserve all substantive historical payload prose.
4. `fable5loop/runs/2026-07-05-cross-model-regression-hardening/verifier-report.md`
   - Append only the dated raw-log retirement note described above.
5. `docs/superpowers/specs/2026-07-23-validation-single-lane-active-surface-cleanup.md`
   - Replace stale Pass 5/Pass 0B language with Stage C status.
   - Record the live 28-plan partition, the two workbook-referenced keep decisions, the exact move/delete manifest, current 42 script `.py/.mjs` and 47 Python/Node test entry counts, 16 Node files, and six derived-swap manifests.
   - Keep future generated-contract migrations outside Stage C.

Historical `fable5loop/STATE.md` entries and prior receipts that name original paths remain chronological evidence and are not rewritten merely to modernize links.

## 4. `STATE.md` navigation decision

**Add a compact authoritative current-state header during implementation.**

The file is 229 physical lines / 117,367 bytes and its chronological `Open failures` section contains claims superseded by later verified facts. Do not rewrite chronology in Stage C. Add this schema immediately below the memory-entry contract:

- As of: date and Stage C source/commit
- Program status: completed stages and current unapproved stage
- Next approval boundary: one exact action
- Current open blockers: exact paths/receipt or none
- Protected boundaries: workbook, generated/published artifacts, runtime/dealer
- Latest authoritative receipt
- Supersession rule: the header governs current status; lower sections remain chronological evidence

This is navigation metadata, not a second architecture or command owner.

## 5. Protected boundaries and gates

### Hard protected surfaces

Byte-identical before/after implementation:

- `stingray_master.xlsx`
- `scripts/`
- `tests/`
- `form-output/`
- `form-app/`
- `AGENTS.md`, `README.md`, `docs/route-map.md`
- all pre-existing `docs/archive/**` payloads
- all prior Fable receipt payloads except the exact append-only July 5 verifier note

No workbook, generator, registry, browser, runtime, or dealer gate should run for the docs/path-only implementation. Any protected-surface drift is a hard failure.

### Required implementation gates

- Exact approved source/destination/deletion assertions.
- Destination-collision assertion before moves.
- Complete/non-overlapping 28-plan partition assertion.
- Active-reference scan; old paths may remain only in archives, chronological `STATE.md`, prior receipts, and the Stage C receipt.
- Read back every moved file and current pointer update.
- `git diff --check` and `git diff --cached --check`.
- `.venv/bin/python scripts/validate_fable5_loop.py`.
- `.venv/bin/python -m pytest tests/test_fable5_loop_contract.py -q`.
- Protected-surface hash/byte comparison against `3515f72`.
- Independent verification against an implementation rubric.

### Rollback

Use one Stage C commit so rollback is `git revert <stage-c-commit>`. Before commit, reverse only the exact approved manifest; never broad-reset concurrent or untracked work.

## 6. Approval boundary

This preflight authorizes no implementation. Recommended next decision:

**Approve the exact narrowed manifest in this report as Stage C implementation.**

Approval would authorize only the 23 moves, three deletions, exact pointer/receipt/spec updates, compact `STATE.md` header, validation, independent verification, and one commit. It would not authorize workbook/product decisions, resolving the seven open/ambiguous plans, moving the two workbook-referenced plans, generation/publication, or Stage D/future cleanup.
