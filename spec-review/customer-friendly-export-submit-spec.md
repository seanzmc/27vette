# Customer-Friendly Export And Dealer Submit Spec

## Diagnosis

The current generated form still exposes internal/admin export actions and keeps customer data as a full form step.

Current evidence:

- `form-app/index.html` renders two toolbar buttons:
  - `#exportJsonButton` with text `Export JSON`
  - `#exportCsvButton` with text `Export CSV`
- `form-app/app.js` wires those buttons to:
  - `exportJson()`
  - `exportCsv()`
- `form-app/app.js` already has customer-facing order helpers:
  - `currentOrder()`
  - `compactOrder()`
  - `plainTextOrderSummary()`
  - `download()`
- `scripts/corvette_form_generator/model_configs.py` still includes `customer_info` in `STEP_ORDER` and `STEP_LABELS`.
- `form-app/app.js` renders `customer_info` as a full step via `renderCustomerForm()`.
- `currentOrder()` and `compactOrder()` already carry `customer`, so customer fields can move from the form flow into a submit modal without removing the order contract.
- The app is currently static. There is no visible backend/API route for a real dealer submission, so a real `Submit to dealer` action needs either:
  - a configured endpoint;
  - a mailto/dealer email fallback;
  - or a front-end-only modal that prepares/downloads the build until submission transport exists.

Risk level: medium. This touches runtime navigation, generated step contracts, export behavior, and tests for both Stingray and Grand Sport. It is mostly front-end/runtime shell work, not workbook business-rule work.

## Goal

Replace internal export/customer-info UX with customer-friendly actions:

1. Remove visible `Export JSON` and `Export CSV` buttons.
2. Add customer-facing `Download Build` action.
3. Add customer-facing `Submit to Dealer` action that opens a modal for name/email and optional message.
4. Remove `Customer Information` as a step in the form flow.
5. Keep the internal compact JSON/CSV helpers available for tests/debug only if useful, but do not expose them as primary customer buttons.
6. Make sure Grand Sport output sections are included cleanly in the customer-facing download/submit payload.

## Constraints

- Do not change workbook business logic.
- Do not activate Grand Sport production runtime as part of this pass.
- Preserve Stingray behavior except for the shared export/customer-info UX.
- Do not add a backend dependency unless the submit destination is explicitly chosen.
- Do not add a heavy PDF generation dependency in this pass.
- Keep generated order output customer-facing and compact.
- Preserve existing debug/export helpers only behind code/test access, not visible UI buttons.

## Files To Change

Runtime/front end:

- `form-app/index.html`
- `form-app/app.js`
- `form-app/styles.css`
- `scripts/corvette_form_generator/model_configs.py`

Tests:

- `tests/stingray-form-regression.test.mjs`
- `tests/multi-model-runtime-switching.test.mjs`
- `tests/grand-sport-draft-data.test.mjs`
- `tests/grand-sport-contract-preview.test.mjs` if step counts change there.

Generated artifacts:

- `form-output/stingray-form-data.json`
- `form-app/data.js`
- `form-output/inspection/grand-sport-*.json`
- `form-output/inspection/grand-sport-*.md`

## Pass 1: Customer-Friendly Download

Runtime changes:

- Replace toolbar buttons:
  - `Export JSON` -> remove from visible UI.
  - `Export CSV` -> remove from visible UI.
  - Add `Download Build`.
- Add `buildMarkdown(order = compactOrder())`.
- Add `downloadBuild()` that downloads:
  - filename: `{activeModel.exportSlug || model}-build.md`
  - MIME type: `text/markdown`
  - content: clean customer-facing Markdown.

Markdown sections should include:

- Title: `2027 Corvette Stingray` or `2027 Corvette Grand Sport`
- Submitted/generated timestamp
- Vehicle:
  - model
  - body style
  - trim
  - base MSRP
- Selected build sections:
  - Exterior Paint
  - Exterior Appearance
  - Wheels & Brakes
  - Performance & Aero / Performance & Mechanical label as currently grouped
  - Stripes
  - Seats & Interior
  - Accessories
  - Auto-added / Required
- Standard & Included summary:
  - grouped summary/count only, not the full flat dump unless current compact output already includes grouped detail intentionally.
- MSRP summary.

PDF note:

- Do not add PDF generation in this pass unless explicitly approved.
- After Markdown is stable, PDF can be added either through browser print styles or a small client-side generator, but that should be its own small spec because visual PDF quality matters.

Expected tests:

- Visible toolbar no longer contains `Export JSON` or `Export CSV`.
- Visible toolbar contains `Download Build`.
- `downloadBuild()` downloads `.md`.
- Grand Sport download filename uses `grand-sport-build.md`.
- Markdown includes Grand Sport-specific sections and auto-added RPOs.
- Existing `exportJson()` and `exportCsv()` may remain exposed to test/debug APIs if needed, but no visible buttons.

## Pass 2: Remove Customer Information Step

Config/runtime changes:

- Remove `customer_info` from `STEP_ORDER`.
- Remove `customer_info` from `STEP_LABELS` if no longer needed as a runtime step.
- Remove `customer_info` handling from step rendering.
- Remove or archive `renderCustomerForm()` and `bindCustomerForm()` if no longer used outside the modal.
- Keep `state.customer` and `customerInformation()` because submit modal still writes to the same order contract.

Expected tests:

- Runtime steps no longer include `customer_info`.
- `customer_info` does not appear between delivery and summary.
- Order recap and compact output do not create a visible `Customer Information` section unless populated by modal submission.
- Existing `compactOrder().customer` still exists.

## Pass 3: Submit To Dealer Modal

UI behavior:

- Add visible `Submit to Dealer` button in the toolbar or summary panel.
- Clicking opens a modal with:
  - name
  - email
  - optional phone
  - optional message
  - cancel/close
  - submit action
- Modal writes fields into `state.customer`.
- The modal should not be part of the step rail.

Submission transport decision:

- If no endpoint is configured, first implementation should be front-end-only:
  - validate name and email;
  - generate the same compact order/Markdown payload;
  - show a clear non-network confirmation such as `Build prepared for dealer submission`;
  - optionally trigger `Download Build`.
- If a dealer endpoint is available, add a small config constant and submit JSON:
  - `POST <endpoint>`
  - payload: `compactOrder()`
  - visible success/error state in the modal.

Non-negotiable:

- Do not silently pretend the order was submitted to a dealer if no endpoint exists.

Expected tests:

- `Submit to Dealer` button opens modal.
- Name/email validation blocks empty/invalid submit.
- Modal updates `state.customer`.
- Front-end-only submit produces a deterministic prepared/submitted state without network.
- If endpoint is configured later, tests should mock success/error.

## Pass 4: Grand Sport Export Section Audit

Verify `compactOrder()` and Markdown include Grand Sport sections correctly:

- Performance & Aero
- Stripes
- Accessories
- Auto-added / Required
- Seats & Interior with selected interior and included seatbelt behavior
- Standard & Included summary

Expected tests:

- Grand Sport build with EL9 includes:
  - selected EL9 interior
  - auto-added Z25
  - auto-added 3F9 when applicable
- Grand Sport build with hash marks includes:
  - selected hash mark
  - auto-added Z15
- Grand Sport build with T0F includes:
  - selected T0F
  - auto-added CFZ at `$0`
- Markdown does not include empty sections.

## Validation Plan

Run:

```bash
.venv/bin/python scripts/validate_workbook_package.py stingray_master.xlsx
.venv/bin/python scripts/generate_grand_sport_form.py
.venv/bin/python scripts/generate_stingray_form.py
node --test tests/grand-sport-draft-data.test.mjs
node --test tests/grand-sport-contract-preview.test.mjs
node --test tests/grand-sport-rule-audit.test.mjs
node --test tests/multi-model-runtime-switching.test.mjs
node --test tests/stingray-generator-stability.test.mjs
node --test tests/stingray-form-regression.test.mjs
git diff --check
```

Manual browser checks:

- JSON/CSV buttons are gone.
- `Download Build` downloads a readable `.md` file for Stingray and Grand Sport.
- Grand Sport Markdown includes the sections expected from the current build.
- `Submit to Dealer` opens a modal.
- Customer name/email entry works from the modal.
- Closing/canceling the modal does not reset the build.
- No `Customer Information` step appears in the step rail.

## Non-Goals

- Do not build a backend unless submit endpoint details are provided.
- Do not add payment/deposit flow.
- Do not add image/asset support.
- Do not change option availability, pricing, or business rules.
- Do not activate Grand Sport live in this pass.

## Open Decision

Before implementing Pass 3 network behavior, decide the dealer submission transport:

1. Front-end-only for now: modal captures contact details and downloads/prepares the build.
2. Mailto fallback: opens dealer email with Markdown/plain-text build body.
3. Real endpoint: provide URL, method, and required payload/auth expectations.

Recommendation for the next implementation pass:

- Do Pass 1 and Pass 2 first.
- Implement Pass 3 as front-end-only unless a real endpoint is ready.
- Defer PDF until Markdown export is approved in the browser.
