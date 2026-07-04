# Pass A — Interactive Ingest Wizard: upload, sheet profiling, role confirmation, deterministic parse, candidate table

Date: 2026-07-03
Branch: `claude/epic-lumiere-585836`
Status: Proposed.
Recommended reasoning level for implementation agent: high.

## Purpose

Rewrite the ingest wizard entry path around a browser-first flow that makes the
division of responsibilities explicit and gets the reviewer to a clean,
reviewable candidate table fast. Pass A is narrowly scoped:

> Interactive Ingest Wizard Pass A: upload/choose raw file, sheet profiling,
> sheet-role confirmation, deterministic option/price parsing, and reviewable
> candidate table.

Proof of success: open the browser, choose the raw file, see friendly detected
sheet roles, run the first parse, and get a table of option candidates with
exact price matches and source evidence.

Pass A explicitly does **not** do apply planning, workbook writes, review
decision capture, or relationship suggestion. Those are later passes.

## Core principle (standing, carries into all later ingest passes)

The script owns structure-derived parsing: sheet profiling, option row
extraction, OVS status extraction, source evidence preservation, and exact
1-to-1 price joins.

The user owns business interpretation: sections, groupings, exclusive groups,
relationship meaning, ambiguous prices, vague disclosures, and any row where
the raw sheet structure does not determine the workbook destination.

## Corrected end-to-end flow (target across passes; Pass A implements 1–5 plus the read-only table of 6)

```text
1. Upload / choose raw GM order-guide xlsx.

2. Quick profiler scans workbook structure.
   It presents friendly sheet cards instead of raw sheet names:
   - detected sheet type: options matrix / price sheet / unsupported
   - detected model family: Stingray / GS / Z06 / ZR1 / ZR1X / mixed
   - detected variant columns
   - row/header confidence
   - recommended include/exclude state

3. User confirms sheet roles.
   Start with only:
   - Options sheet
   - Price sheet
   Everything else can be blocked/manual for now.

4. Parser runs on confirmed sheets.
   From options sheets:
   - RPO
   - ref-only RPO
   - name/description/details
   - raw status cells
   - model/variant OVS status
   - raw row/source evidence

   From price sheet:
   - RPO
   - price
   - raw row/source evidence

5. Script performs safe deterministic joins.
   Only exact 1-to-1 RPO price matches get auto-backfilled.
   Ambiguous/missing/multiple price matches go to review.

6. User review begins after useful candidates exist.
   User assigns:
   - workbook section/category
   - pricing backfill approval
   - exclusive groups
   - rule groups
   - requires/includes/excludes
   - vague/manual relationship decisions

7. Relationship suggestions are helper hints, not truth.
   The UI scans description/detail text for phrases like:
   - not available with
   - only available with
   - requires
   - included with
   - requires additional equipment
   - deletes/replaces
   It suggests likely relationship candidates, then you approve/edit/reject.

8. Export reviewed decisions.
   Still no workbook write until a later approved apply pass.
```

Steps 6 (decision capture), 7, and 8 are Pass B+ scope. Pass A ends at a
read-only candidate table whose rows carry the parse and join results.

## Diagnosis

Root cause / current-state evidence:

- The existing pipeline (Passes 0–5, see `docs/ingest/README.md`) is CLI-first:
  the reviewer must run `order_guide_ingest_profiler.py`, then the normalizer,
  then the interpreter with a model selection, and only then open the workbook
  editor's Ingest Review tab against pre-built artifacts. The browser is the
  last step instead of the first, there is no sheet-role confirmation gate, and
  the reviewer sees abstract decision states before any useful candidates
  exist. Pass 5's own README note records that Pass 4's broad reduced queue
  "proved technically safe but not reviewer-usable enough."
- The user-facing flow never asks the one question the reviewer can answer
  cheaply and early — "which sheets are the options sheets and which is the
  price sheet?" — so parsing scope is inferred rather than confirmed.
- Price backfill today flows through interpretation lanes rather than a simple
  deterministic exact-match join with an explicit ambiguity queue.

Evidence inspected before this spec:

- `docs/ingest/README.md` and pass 0–5 specs — current architecture and the
  Pass 4/5 usability correction history.
- `docs/roadmap_wishes.md` item 3 — the standing goal this serves: an ingest
  wizard with appropriate pausing points for user input, usable without coding.
- `scripts/corvette_form_generator/ingest/source_profiler.py` — proven
  deterministic primitives to reuse: `ORDER_GUIDE_BASE_HEADERS`, `STATUS_RE`,
  `RPO_RE`, `detect_header_row`, `classify_headers`, `parse_status`,
  `parse_variant_column`.
- `scripts/workbook_editor_server.py` — stdlib `ThreadingHTTPServer` pattern
  and ingest review endpoints welded to Pass 1/3/5 artifacts (fail-closed on
  model-selection and fingerprint checks); reused as a server-shape template,
  not extended.
- `2027 Chevrolet Car Corvette Export_RAW.xlsx` — 23 sheets. Deterministic
  signals verified by direct scan on 2026-07-03:
  - Options-matrix sheets (`Equipment Groups|Interior|Exterior|Mechanical 1–4`)
    carry the model family name in cell A1 (`Stingray`, `Grand Sport`, `Z06`,
    `ZR1 and ZR1X`), the base headers `Orderable RPO Code` / `Ref. Only RPO
    Code` / `Description` on row 3, and variant columns from column 4 with
    `<body>\n<model code>\n<trim>` headers.
  - `Standard Equipment 1–4` share the options-matrix shape but are almost
    entirely ref-only/no-RPO standard rows (0–7 orderable rows per sheet).
  - `Price Schedule` has a `Base Model Prices` section (model code + trim
    pricing) and an `Additional Options` section (option code, description,
    optional text qualifier, then numeric price columns). Repeated option
    codes with different qualifiers exist (e.g. `PDB`, `PDD`, `PDF` appear 3×
    each for Z06 wheel variants) — the canonical ambiguous-price case.
  - `Color and Trim 1–2` use unrelated layouts (unsupported in Pass A).

Risk level: medium. All new code is read-only toward the canonical workbook
and runtime; risk concentrates in contract quality (this wizard becomes the
entry path later passes build on) and in the new upload endpoint (constrained
to a dedicated directory).

Change type: tooling/UI/tests/docs. No workbook data, generated runtime data,
`form-app/` behavior, or dealer-submission changes.

## Design

### Architecture

New, self-contained wizard surface. The existing workbook editor and Pass 0–5
code paths are left untouched; the wizard reuses `source_profiler` parsing
primitives as a library.

```text
browser (visualizer/ingest-wizard/)
  → scripts/ingest_wizard_server.py (stdlib http server, JSON API + static UI)
    → scripts/corvette_form_generator/ingest/wizard/
        profiler.py   step 2: sheet cards
        parser.py     step 4: option/price row extraction
        joiner.py      step 5: exact 1-to-1 price joins
        session.py    run-state store under form-output/ingest-wizard/<run-id>/
```

Session state machine: `created → profiled → roles_confirmed → parsed`.
Each transition persists JSON artifacts so a run can be reopened and later
passes can consume the output:

```text
form-output/ingest-wizard/<run-id>/session.json         state + chosen file + fingerprint
form-output/ingest-wizard/<run-id>/sheet-profile.json   step 2 sheet cards
form-output/ingest-wizard/<run-id>/sheet-roles.json     step 3 confirmed roles
form-output/ingest-wizard/<run-id>/option-candidates.json  step 4/5 candidates with joins
form-output/ingest-wizard/<run-id>/price-rows.json      step 4 price sheet extraction
form-output/ingest-wizard/<run-id>/join-report.json     step 5 join summary + ambiguity queue
```

Uploads land in `form-output/ingest-wizard/uploads/` only; path traversal is
rejected; only `.xlsx` accepted. The raw source file is never modified.

### Step 1 — choose/upload

- `GET /api/wizard/files` — lists `.xlsx` in the repo root and in
  `form-output/ingest-wizard/uploads/`, excluding `stingray_master.xlsx`
  (canonical workbook, never an ingest source) and Excel lock files.
- `POST /api/wizard/upload?filename=<name>` — raw body upload into the uploads
  directory; sanitized basename only.
- `POST /api/wizard/sessions` `{file}` — creates a run id, fingerprints the
  file (sha256 + size + mtime), runs the profiler, persists
  `session.json` + `sheet-profile.json`, returns the sheet cards.

### Step 2 — profiler output: friendly sheet cards

Per sheet, deterministic detection only (no product guessing):

- `sheetType`: `options_matrix` (base headers found + ≥1 parseable variant
  column), `price_sheet` (Base Model Prices / Additional Options section
  markers with option-code price rows), else `unsupported`.
- `contentSubtype` for options matrices: `orderable_options` vs
  `standard_equipment` (derived from the orderable-RPO row share, not the
  sheet name; name is displayed but not trusted for classification).
- `modelFamily`: mapped from the A1 title — `Stingray`, `Grand Sport`, `Z06`,
  or `mixed (ZR1 + ZR1X)`; `unknown` when unmapped. The variant-column model
  codes (1YC/1YE/1YH/1YR/1YS…) are recorded as corroborating evidence.
- `variantColumns`: parsed `<body>\n<model code>\n<trim>` headers with column
  letters.
- `confidence`: `high` when header row, base headers, and all variant columns
  parse; `medium` when the sheet parses with skipped columns/rows (reasons
  listed); `low` otherwise.
- `recommendedRole`: `options` (orderable options matrices), `price` (price
  sheet), `exclude` (standard-equipment subtypes, unsupported sheets). The
  recommendation is a default, never enforced.
- Row stats (orderable / ref-only / section / blank counts) so the card can say
  "147 orderable options, 20 ref-only rows" instead of raw coordinates.

### Step 3 — role confirmation

- `POST /api/wizard/sessions/<id>/roles` — body maps sheet name →
  `options | price | exclude`. Validation is fail-closed:
  - at least one `options` sheet and exactly one `price` sheet;
  - `options`/`price` roles are only accepted on sheets whose detected type
    supports them (`options_matrix` / `price_sheet`); `unsupported` sheets can
    only be `exclude`. Overriding a *recommendation* (e.g. including a
    standard-equipment sheet as options) is allowed; overriding a *detected
    type* is not — that is a parser gap to fix, not a reviewer decision.
- Confirmed roles persist to `sheet-roles.json`; re-confirmation resets any
  previous parse output for the run.

### Step 4 — deterministic parse of confirmed sheets

From each confirmed options sheet, one candidate per RPO-bearing row:

- `rpo` (orderable) and/or `refOnlyRpo`;
- `name`/`description` plus detail lines (rows are folded per source row; no
  cross-row merging in Pass A — dedup across sheets is later-pass review work);
- raw status cells exactly as printed (`S1`, `A/D1`, `■`, `--`, …);
- parsed per-variant OVS status (`standard | available | unavailable |
  unresolved`) with disclosure numbers preserved;
- `sourceEvidence`: sheet name, row number, cell coordinates, section header
  text (e.g. `Equipment Groups`), and the raw cell values.

From the confirmed price sheet:

- Additional Options section rows: `rpo`, optional `qualifier` text, first
  numeric price column as `listPrice`, all numeric columns preserved as
  evidence, plus row coordinates.
- Base Model Prices section rows are extracted and persisted as evidence
  (`price-rows.json`) but produce no option candidates in Pass A.

Rows that fail deterministic parsing are recorded per sheet as `skippedRows`
with reasons — never silently dropped.

### Step 5 — safe deterministic join

- Exactly one price row for an RPO that appears as an orderable candidate →
  `priceMatch: exact`, price auto-backfilled onto the candidate.
- Multiple price rows for the RPO (qualifiers) → `priceMatch: ambiguous`,
  all matching price rows attached, no backfill.
- No price row → `priceMatch: none`.
- Price rows whose RPO matches no candidate are reported as
  `unmatchedPriceRows` in `join-report.json`.
- Join keys are exact normalized RPO strings only. No fuzzy matching, no
  qualifier interpretation, no price selection heuristics — per the core
  principle those are user decisions in a later pass.

### Step 6 (Pass A slice) — reviewable candidate table

- `GET /api/wizard/sessions/<id>/candidates` — filterable by sheet, model
  family, price-match state, and RPO/description text.
- UI: single-page wizard with four stages (Choose file → Sheet cards →
  Confirm roles → Candidates). The table shows RPO, ref-only RPO, name,
  model family/sheet, per-variant status chips, price + match state, and an
  expandable evidence drawer with the raw cells and coordinates.
- Read-only: no decision capture, no editing, no export in Pass A.

### Error handling

- Server fails closed on: missing/renamed source file, fingerprint mismatch on
  reopen (stale run), role submissions violating the validation above, parse
  requests before roles are confirmed, and candidate requests before parse.
- Profiler/parser never raise on malformed sheets — malformed structure is
  reported as `unsupported`/`skippedRows` so the reviewer sees it on the card.

## Exact files and artifacts to change after approval

- `scripts/corvette_form_generator/ingest/wizard/__init__.py` — new package.
- `scripts/corvette_form_generator/ingest/wizard/profiler.py` — sheet cards.
- `scripts/corvette_form_generator/ingest/wizard/parser.py` — option/price
  extraction.
- `scripts/corvette_form_generator/ingest/wizard/joiner.py` — price joins.
- `scripts/corvette_form_generator/ingest/wizard/session.py` — session store.
- `scripts/ingest_wizard_server.py` — new CLI/server entry point.
- `visualizer/ingest-wizard/index.html`, `wizard.js`, `wizard.css` — UI.
- `tests/test_ingest_wizard_profiler.py`, `tests/test_ingest_wizard_parser.py`,
  `tests/test_ingest_wizard_server.py` — Python tests with compact fixture
  workbooks (fixture-builder style, not the live raw export as truth).
- `docs/ingest/README.md` — record the corrected flow, core principle, Pass A
  status, and that Passes 0–5 remain implemented but are superseded as the
  wizard *entry path* (their modules stay as parsing/review libraries and
  reference until later passes retire them explicitly).
- `Order-Guide_IngestPrompt.md` — add Pass A to the pass sequence as the
  wizard entry path (artifacts under `form-output/ingest-wizard/<run-id>/`),
  marking the Pass 0→5 sequence as the superseded legacy entry path.
- `README.md` — add the wizard server run command to the command table.
- `docs/ingest/pass-a/interactive-ingest-wizard-pass-a-spec.md` — this spec;
  close out with status/validation on completion.

Transient artifacts (not checked in): `form-output/ingest-wizard/**`.

## Source-of-truth decision

Tooling + docs + transient artifacts only. The canonical workbook stays
untouched; candidate artifacts are transient evidence, never source. No new
workbook sheets/columns. No new dependencies (stdlib http server + existing
`openpyxl`).

## Companion-file impact

- `form-app/`, `form-output/` generated runtime data, dealer submission: n/a —
  untouched.
- `scripts/workbook_editor_server.py` + editor UI: inspected, no change; the
  legacy Ingest Review tab keeps working against Pass 1/3/5 artifacts.
- `Order-Guide_IngestPrompt.md`: inspected — its "Pass sequence and artifacts"
  section names Pass 0 as the entry; will be updated (see files list). Its hard
  guardrails (preserve raw values, invent nothing, transient artifacts only,
  stop on invariant failure) carry over to Pass A unchanged.
- `AGENTS.md` §8: inspected, no change — Pass A stays within the read-only
  evidence-gathering boundary it describes.

## Constraints

No unrelated refactors. No new dependencies. Generated files are not source.
Workbook owns product rules — the wizard records evidence and defers
interpretation. Dealer boundaries preserved. Existing Pass 0–5 modules are not
deleted or rewired in Pass A.

## Risks and non-goals

Risks:

- Contract risk: later passes (decision capture, relationship hints, export,
  apply planning) build on these artifacts; mitigated by explicit versioned
  artifact schemas (`schemaVersion: "pass-a-1"`) and fail-closed state checks.
- Upload endpoint risk: mitigated by basename sanitization, `.xlsx`-only,
  dedicated uploads directory, and local-only default bind (127.0.0.1).
- Heuristic drift on future GM exports: mitigated by confidence + skipped-row
  reporting instead of hard failure, and fixture-based tests encoding the
  observed 2027 export shapes.

Non-goals (deferred to later passes): apply planning or any workbook write;
review decision capture (sections, groups, exclusive groups, relationships,
pricing approvals); relationship phrase-scan suggestions; decision export;
Color and Trim parsing; standard-equipment interpretation; dedup/merge of the
same RPO across model-family sheets; integration into the workbook editor UI.

## Validation plan

- `pytest tests/test_ingest_wizard_profiler.py tests/test_ingest_wizard_parser.py tests/test_ingest_wizard_server.py` — new coverage: sheet-type/family/confidence detection, role validation (fail-closed cases), options/price extraction incl. status parsing and skipped rows, join exact/ambiguous/none/unmatched cases, session state machine, upload sanitization.
- Full `pytest tests/` to prove no regression in existing ingest/editor suites.
- Manual proof of success in the browser against
  `2027 Chevrolet Car Corvette Export_RAW.xlsx`: choose file → sheet cards
  (23 sheets: 16 options matrices incl. 4 standard-equipment subtypes, 1 price
  sheet, 2 unsupported Color and Trim) → confirm roles → parse → candidate
  table shows candidates with exact price matches (e.g. `BV4` at 395) and an
  ambiguous queue (e.g. `PDB`/`PDD`/`PDF`), each with source evidence.
- Workbook untouched check: `git status` shows no `stingray_master.xlsx`
  change; no gate regeneration needed (no generated-surface change).
