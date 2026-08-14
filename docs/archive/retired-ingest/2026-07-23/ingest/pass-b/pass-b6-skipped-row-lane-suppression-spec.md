# Pass B.6 — suppress skipped rows from later review lanes

Date: 2026-07-07
Status: Implemented 2026-07-07. Validation: `.venv/bin/python -m pytest tests/test_ingest_wizard_server_pass_b.py tests/test_ingest_wizard_decisions.py tests/test_ingest_wizard_plan.py -q` → 49 passed; `node --check visualizer/ingest-wizard/wizard.js` → passed; `git diff --check` → passed.
Parent: `docs/ingest/ingest-wizard-end-to-end-completion-spec.md` (Pass B review stage). Follows Pass B.5 (`docs/ingest/pass-b/pass-b5-review-filtering-and-bulk-skip-spec.md`).

## Diagnosis

Pass B.5 added decision-state filters and bulk section skip, but the skip semantics are still only partially reflected in queue display. A section decision saved as `resolution: not_needed` already means “do not carry this candidate forward”; completeness excludes that row from price/status requirements and Pass C treats it as plan-inert. The review UI still builds later lane queues from model-scoped candidates unless the user chooses the price `Needs decision` filter, so skipped rows can still appear in later review lanes such as price/copy split/relationships.

Evidence inspected:

- `scripts/corvette_form_generator/ingest/wizard/session.py` `review_queue()` filters skipped section rows only for price `decisionState=undecided`, not for the base later-lane queue.
- `scripts/corvette_form_generator/ingest/wizard/decisions.py` `completeness()` already excludes skipped IDs from price and status required counts, but per-lane decision/hold counts still read all lane records unless filtered.
- `tests/test_ingest_wizard_server_pass_b.py` covers B.5 filters but does not prove skipped rows disappear from unfiltered later lanes.
- `tests/test_ingest_wizard_decisions.py` covers price exemption for skipped rows, but not stale later-lane decisions after a row is skipped.

Risk level: low. Tooling/UI/server/test/docs only. No workbook writes, generated artifacts, customer runtime, or dealer submission changes.

## Source-of-truth decision

Tooling/review-flow behavior. Existing decision vocabulary remains canonical for skip semantics:

- lane: `section`
- action: `exclude_row`
- resolution: `not_needed`

No new decision shape, workbook schema, or generated contract field.

## Exact files to change

- `scripts/corvette_form_generator/ingest/wizard/session.py` — compute section-skipped candidate IDs once per queue and suppress them from every non-section candidate queue before source/search/decision-state filters and per-lane derived payloads.
- `scripts/corvette_form_generator/ingest/wizard/decisions.py` — ignore skipped-candidate records for later per-candidate lane progress/holds so blocker/progress reporting matches “not carried forward”.
- `tests/test_ingest_wizard_server_pass_b.py` — prove a skipped candidate disappears from unfiltered later queues, including when a stale price decision exists.
- `tests/test_ingest_wizard_decisions.py` — prove skipped candidates do not contribute later-lane blockers/holds/counts.
- `docs/ingest/README.md`, `docs/ingest/ingest-wizard-end-to-end-completion-spec.md`, `Order-Guide_IngestPrompt.md` — concise B.6 status/pointer updates after implementation.
- This spec — mark implemented with validation evidence before handoff.

## Constraints / non-goals

- Keep section lane behavior unchanged: skipped rows remain visible there as already-decided section rows.
- Do not delete existing later-lane decisions automatically; hide/ignore them while the section skip is active so undo/clear remains reversible.
- No Pass D apply work.
- No workbook writes or generated/runtime artifacts.
- No new dependencies.

## Validation plan

- `.venv/bin/python -m pytest tests/test_ingest_wizard_server_pass_b.py tests/test_ingest_wizard_decisions.py tests/test_ingest_wizard_plan.py -q`
- `node --check visualizer/ingest-wizard/wizard.js`
- `git diff --check`
- `git status --short`

## Closeout — 2026-07-07

Implemented:

- `review_queue()` now derives section-skipped candidate IDs once and removes them from every non-section candidate queue before source/search/decision-state filters and per-lane derived payloads.
- Copy-split duplicate-name analysis excludes skipped candidates from its full-model collision scan.
- `completeness()` ignores skipped candidates' later per-candidate lane records when computing decisions, holds, and blockers, so stale price/copy-split holds created before a section skip no longer keep appearing in progress reports.
- HTTP tests prove skipped rows disappear from unfiltered price/copy-split/relationship/duplicate queues and from price `Already decided` even when a stale price decision exists.
- Store tests prove skipped rows do not contribute later-lane price decisions, holds, copy-split holds, or blocker IDs.

Changed surfaces: ingest wizard tooling/server/tests/docs only. Workbook, generated artifacts, `form-app/`, and dealer submission were not changed.
