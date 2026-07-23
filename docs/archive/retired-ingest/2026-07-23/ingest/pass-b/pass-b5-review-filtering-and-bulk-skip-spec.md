# Pass B.5 — review filtering and bulk section skip

Date: 2026-07-07
Status: Implemented 2026-07-07. Validation: `.venv/bin/python -m pytest tests/test_ingest_wizard_server_pass_b.py tests/test_ingest_wizard_decisions.py tests/test_ingest_wizard_plan.py -q` → 49 passed; `node --check visualizer/ingest-wizard/wizard.js` → passed; `git diff --check` → passed.
Parent: `docs/ingest/ingest-wizard-end-to-end-completion-spec.md` (Pass B review stage).

## Diagnosis

The Pass B/B.4 review UI has row checkboxes and several bulk actions, but section assignment still lacks two reviewer controls Sean needs during real review:

- a way to show only rows that still need a section decision;
- a bulk `Skip — don't carry over` action for checked section rows.

Price resolution has price-state filtering (`exact` / `ambiguous` / `none`) and bulk accept-exact, but lacks the same decision-state filter needed to focus on unresolved price rows. Rows skipped in section assignment are already exempt from price completeness and plan output, so the price unresolved filter must not show those rows as still needing price work.

Evidence inspected:

- `visualizer/ingest-wizard/index.html` review filters currently expose source group, price state, and search only.
- `visualizer/ingest-wizard/wizard.js` current queue key and request params do not carry decision-state filtering; section bulk controls only assign a section or use the reference section.
- `scripts/corvette_form_generator/ingest/wizard/session.py` `review_queue()` filters by source group, price match, and search, but not decision state.
- `scripts/corvette_form_generator/ingest/wizard/decisions.py` already defines skip semantics: section `not_needed` rows are exempt from price/status completeness.

Risk level: low-medium. Tooling/UI/server/test only; no workbook writes, generated runtime artifacts, runtime app, or dealer submission changes.

## Scope / source-of-truth decision

Tooling/UI behavior only. The workbook remains source of truth for product data. This pass changes reviewer queue filtering and decision capture ergonomics; it does not alter plan semantics beyond using existing section-skip decisions.

## Exact files to change

- `scripts/corvette_form_generator/ingest/wizard/session.py` — add `decision_state` filtering to `review_queue()`.
- `scripts/ingest_wizard_server.py` — pass `decisionState` query parameter into the store.
- `visualizer/ingest-wizard/index.html` — add a decision-state filter select for section/price lanes.
- `visualizer/ingest-wizard/wizard.js` — wire the filter, reset it on lane/model changes, include it in queue keys, and add section bulk skip for checked rows.
- `tests/test_ingest_wizard_server_pass_b.py` — focused HTTP coverage for section/price decision-state filters and invalid values.
- `docs/ingest/README.md`, `docs/ingest/ingest-wizard-end-to-end-completion-spec.md`, `Order-Guide_IngestPrompt.md` — concise status/pointer updates after implementation.
- This spec — mark implemented with validation evidence before handoff.

## Constraints and non-goals

- No workbook writes.
- No generated `form-output/*` tracked artifact or `form-app/data.js` changes.
- No new dependencies.
- No runtime/dealer behavior changes.
- No broad review-lane redesign.
- Bulk skip must use the existing reviewed decision shape: section lane, action `exclude_row`, resolution `not_needed`.
- Price unresolved filter must exclude candidates already skipped in the section lane.

## Validation plan

- `.venv/bin/python -m pytest tests/test_ingest_wizard_server_pass_b.py tests/test_ingest_wizard_decisions.py tests/test_ingest_wizard_plan.py -q`
- `node --check visualizer/ingest-wizard/wizard.js`
- `git diff --check`
- `git status --short` and diff review confirming protected surfaces remain untouched.

## Closeout — 2026-07-07

Implemented:

- Server/store `decisionState` filtering for section and price review queues.
- Price `Needs decision` excludes rows already skipped in section (`resolution: not_needed`) because those rows are intentionally not carried forward and no price decision is owed.
- UI decision-state filter for section and price lanes; lane/model switches clear it with the other lane-specific filters.
- Section bulk `Skip — don't carry over` for checked rows, using existing audited decisions: lane `section`, action `exclude_row`, resolution `not_needed`.
- HTTP coverage for section undecided/decided filters, price undecided/decided filters, section-skip price exemption, and invalid filter values.

Changed surfaces: ingest wizard tooling/UI/tests/docs only. Workbook, generated artifacts, `form-app/`, and dealer submission were not changed.
