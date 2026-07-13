# Milestone 2 Browser Verification

Date: 2026-07-13

## Safe fixture run

Root: `/tmp/27vette-m2-browser`
Run: `20260713-131308-d814f9`
Server: temporary localhost process on port 8042; stopped after verification.

Verified in the browser:

- the saved run was visible and resumed directly to `stage-exceptions`;
- raw evidence rendered source workbook coordinates and values;
- canonical section choices were finite values loaded from the canonical workbook;
- one `missing_section` resolution selected `sec_whee_001` with reviewer `Browser QA`;
- automatic recompilation changed the model blocker count from 25 to 24;
- the resolved filter showed exactly that resolution and reviewer;
- reopen automatically recompiled and returned the blocker count to 25;
- `exception-log.jsonl` contained one `resolution_recorded` and one `resolution_reopened` event;
- the fixture `exception-resolutions.json` returned to zero valid/current entries after reopen;
- the fixture workbook and source export hashes, sizes, and mtimes remained unchanged;
- no browser console or JavaScript errors remained.

A live smoke initially found `(evidence.cells || []).map is not a function` because real source evidence stores cells as a coordinate/value object. `sourceEvidenceView()` was corrected to normalize both object and list forms, then the same flow passed with no console errors.

## Retained real Milestone 1 run — read-only

Run: `form-output/ingest-wizard/20260712-215133-64bfad`
Server: temporary localhost process on port 8043; stopped after verification.

Verified without any resolve/reopen request:

- the run appeared first in the visible saved-run list as `compiled_with_exceptions`;
- Resume routed directly to the typed exception stage;
- the default queue rendered 20 evidence-backed cards;
- the default reviewer-answerable set was 92 subjects after server-side compiler-effect filtering: 75 section choices and 17 finite price-scope choices;
- pagination moved deterministically from `Showing 1–20 of 92` to `Showing 21–40 of 92`;
- model readiness showed Grand Sport X 540 blockers, ZR1 269, and ZR1X 269;
- unsupported comparator/relationship/identity/removal actions were not presented as partial choices; the first actionable subject was a concrete `missing_section` card;
- no console or JavaScript errors occurred.

Post-verifier correction smoke additionally proved:

- the 17 price subjects rendered `<select>` controls with 9 or 12 target/canonical scope choices, never free-text body/trim scope inputs;
- combined `q=missing_section` and severity filtering returned exactly 75 matching subjects;
- comparator relationship cards rendered actual signature fields (`ruleType`, source/target RPO, and scopes) with zero empty proposal previews;
- unsupported identity, relationship, comparator-confirmation, and removal actions remained absent from the 92 projectable subjects.

The six retained compiler artifacts exactly matched the SHA-256 values in the Milestone 1 `recompile-summary.json` after the browser read-only smoke.

## Desktop and mobile layout

Desktop browser viewport: 1280 × 633. The saved-run list, compile summary, separate readiness gates, exception filters, evidence cards, typed forms, and pagination rendered without overlap.

Mobile proof used installed headless Chrome with CDP device metrics. Final measured state:

- inner width: 390 px;
- `(max-width: 720px)` media query: true;
- active stage: typed exceptions;
- rendered cards: 20;
- exception filters: one column;
- evidence panels: one column (`302px` measured width);
- progress stepper: three wrapped columns (`105px 105px 105px`);
- stepper horizontal overflow: `0`;
- error banner: empty.

The first mobile capture exposed horizontal stepper clipping. The mobile CSS was corrected to a three-column grid and the repeated Chrome measurement confirmed zero overflow.

## Protected boundaries

No live workbook write, source write, `pass-c-3` projection, generation, publication, promotion, dealer submission, or retained-real-run resolution mutation was performed. All temporary browser/server/Chrome processes were stopped.
