# Milestone 2.4.1 — Decision-First Exception Review UX Correction

Status: DRAFT — SPEC ONLY, NOT APPROVED FOR IMPLEMENTATION. Exception mutation remains paused. Milestone 3 remains blocked and unapproved.

Recommended reasoning level: high.

## Goal

Make each typed-exception card understandable as one concrete product decision before exposing compiler evidence or workbook-row mechanics.

Milestone 2.4.1 is a narrow correction to the Milestone 2.4 reviewer surface. It preserves Milestone 2.4's semantic-overlap gate, finite action catalogs, side-effect-free preview service, exact preview-to-resolution equality, stale-input refusal, and whole-proposal rejection semantics.

It does not redesign the compiler, broaden target-authoring authority, introduce partial edits, or advance Milestone 3.

## Relationship to Milestone 2.4

Commit `302136b` implemented the Milestone 2.4 semantic-conflict and exact-preview machinery, but the owning Milestone 2.4 plan and production-design pointers were not closed. Live browser review of fresh run `20260715-225924-b198b4` showed that the safer display contract still does not provide a usable human approval boundary.

Milestone 2.4 and 2.4.1 must close together after one independent verification. Until then:

- run `20260715-150312-eb8d08` remains immutable forensic evidence;
- run `20260715-225924-b198b4` is GET-only observation evidence and must not be resolved, reopened, or recompiled;
- all preview/resolve/reopen proofs use disposable roots or a new proof run;
- no workbook, generated runtime, publication, deployment, promotion, or dealer authority is granted.

## Diagnosis

The latest fresh run contains 215 blockers: 179 need a reviewer decision, 10 are prerequisite-blocked, and 26 are semantic conflicts. Ten subjects concern exclusive groups: six actionable proposals and four non-actionable overlaps.

The current browser is mechanically accurate but cognitively inverted:

1. It leads with compiler state and evidence containers instead of the proposed customer behavior.
2. One card always renders Raw source evidence, Existing workbook rows, Already-derived rows, Comparator context, Proposal to evaluate, Shared context, Gate impact, and every available action.
3. Empty evidence containers remain visible and consume the same attention as relevant evidence.
4. Comparator context and the proposal signature often repeat the same RPO/member information.
5. Every available action becomes a separate full form with its own preview box and preview button. Confirm and reject therefore look like two independent tasks instead of mutually exclusive answers to one question.
6. The generic prompt `Confirm or reject this comparator-corroborated target relationship` appears for exclusive groups, rule groups, defaults, and price proposals even when it does not describe the decision.
7. Compiler phrases such as `single_within_group`, `compileReady`, sheet keys, raw cell coordinates, and stable IDs appear before the reviewer understands the rule.
8. The responsive layout prevents horizontal overflow by stacking every panel. It does not reduce the amount of information.

Measured on run `20260715-225924-b198b4` with the exclusion filter active:

- the first actionable exclusion card is 1,460 px tall in a 1,200 × 720 desktop viewport;
- the same card is 3,310 px tall in a 390 × 844 mobile viewport;
- the six-card mobile page is 21,816 px tall;
- the card's actual decision is only whether its proposed members are optional peers, required peers, or not a valid target proposal.

This pass treats those measurements as a failed usability gate, not as an acceptable consequence of safety disclosure.

## Design decision

Use a compact queue with one expandable decision card at a time.

This is preferred over two rejected alternatives:

- Keeping every card expanded and merely shortening labels would preserve the form explosion.
- A new split-pane or routed detail application would add navigation and state architecture that the local wizard does not need.

The existing filtered/paginated queue, exception lifecycle API, preview endpoint, compiler artifacts, and mutation contract remain. The correction is progressive disclosure plus one-action-form composition.

## Source-of-truth and authority boundaries

- Target raw evidence and canonical workbook rows continue to own target product behavior.
- Comparator rows remain corroborating proposal evidence only.
- Existing `availableActions`, finite `choices`, semantic conflicts, prerequisites, and preview results remain authoritative. The browser may relabel and compose them; it may not invent another action.
- Plain-language summaries must be generic projections of existing structured fields. They may not infer missing product meaning.
- Missing option descriptions display the RPO with `Description unavailable`; they are never guessed or borrowed silently.
- Exact rows remain available for audit, but they are not the primary decision surface.

## Reviewer experience contract

### 1. Queue shell

- Preserve filters for target model, decision type, affected workbook sheet, review state, and search.
- Keep `Needs reviewer decision` as the default review state.
- Render each subject as a compact summary row showing target model, decision type, primary RPOs, a one-line behavior summary, and state.
- No summary row may render raw cells, exact workbook rows, action forms, or preview containers.
- Initial queue load has no expanded subject. The reviewer explicitly opens one summary row to begin a decision.
- At most one subject is expanded. Opening another subject collapses the prior subject.
- Resolved or actionless subjects remain reviewable but do not expose inappropriate controls.
- After a successful resolution, focus moves to the next visible unresolved summary row without changing filters.

### 2. Expanded decision card

The default expanded card contains, in this order:

1. **Decision heading** — target model plus a human decision name.
2. **Proposed behavior** — one plain-English sentence describing direction, members, selection behavior, condition, price, or section placement.
3. **Why the wizard is asking** — at most two lines from the owning target evidence and, when applicable, a clear `Comparator suggestion` label.
4. **One decision fieldset** — all available answers to this subject as mutually exclusive choices.
5. **One preview region and one primary button** — never one per action.
6. **Collapsed supporting details** — evidence, existing/derived rows, exact effects, shared context, workbook sheets/keys, and compiler identifiers.

Do not render empty supporting-detail sections. Do not render shared context when its count is zero.

The top-level card must use `Blocks <model> compilation` rather than exposing `compileReady` or internal reason codes. Exact reason codes and subject IDs remain under `Technical details`.

### 3. Decision-type copy and controls

| Decision type | Primary statement | Reviewer choices |
|---|---|---|
| Section | `Place <RPO or description> in one target section.` | Existing finite section catalog only. |
| Identity | `Match <RPO> to one existing target option.` | Existing exact identity choices only. If none is correct, leave the subject blocked. |
| Relationship | `When <source> is selected, <target> is <required/included/unavailable/replaced>.` | Existing relationship type and endpoint catalogs, plus whole-proposal rejection when authorized. |
| Rule group | `Selecting <source> applies this rule to <complete member list>.` | Confirm the complete proposal or reject the whole proposal. No member-level shortcut. |
| Exclusive group | `Choose at most one of: <members>` or `Choose exactly one of: <members>.` | `Allow at most one`, `Require exactly one`, or `Reject whole proposal — no rows`, limited to existing actions/catalogs. |
| Default | `<option> is selected by default under <condition/scope>.` | Existing priority/display choices or whole-proposal rejection. |
| Price | `When <condition> applies, <target> costs <price> for <scope>.` | Existing finite target scope and whole-dollar price fields, or whole-proposal rejection. |
| Conflict | `The proposal and target workbook describe incompatible behavior.` | No mutation control. Show the proposed fact, existing fact, exact difference, and required authoritative correction. |

RPOs must be paired with available customer-facing descriptions. Raw workbook IDs may appear only in supporting details.

### 4. One fieldset, one action path

Replace the current `availableActions.map(...)` parallel-form layout with one form per subject.

- The form first asks the reviewer to choose one available outcome.
- Choosing an outcome reveals only that outcome's required fields.
- Choosing `Reject whole proposal — no rows` reveals the existing whole-proposal acknowledgement and optional audit note inline; rejection controls are otherwise absent.
- A partial disagreement has no resolution action. Display: `Leave this blocked and correct the source or compiler proposal; rejection applies to the entire proposal.`
- Changing the selected outcome or any typed field invalidates the prior preview.
- Preview posts the exact existing `action` and typed `payload`; the API contract does not change.
- Save is unavailable until the current exact preview succeeds.
- Before preview there is no empty placeholder panel. The single primary button reads `Preview effect`; after a successful preview, the compact summary appears and the same button becomes `Save exact effect`.

### 5. Preview presentation

Preview remains mandatory, but its default presentation becomes a concise human summary:

- `Adds 1 exclusive group and 2 members (3 workbook rows).`
- `Updates 1 existing price rule.`
- `Writes no rows and suppresses the entire proposal.`
- `Cannot be saved because it conflicts with an existing target rule.`

The summary must state that the live workbook is not being written.

Exact `(sheet, key, action, values)` effects remain under an initially collapsed `Exact workbook rows` disclosure. Expanding that disclosure shows every row returned by the existing preview response without truncation.

### 6. Supporting evidence

- Show one owning source snippet at the top level, line-clamped to three lines.
- Put raw sheet names, cell coordinates, full raw copy, comparator payloads, existing workbook rows, already-derived rows, shared context, and stable IDs under labeled disclosures.
- For group decisions, render the proposed and existing member sets as labeled RPO/description lists, not JSON arrays.
- For relationship decisions, render direction as `source → behavior → target`.
- For semantic conflicts, show a compact `Existing` versus `Proposed` comparison and the overlap kind in plain language: `subset`, `superset`, `partial overlap`, `different relationship`, or `reverse relationship`.
- Do not use a generic empty-state box for absent evidence; omit the section.

## Read API presentation data

The exception GET response must add one non-authoritative `presentation` object per item:

```json
{
  "title": "ZR1 exhaust choices",
  "summary": "Choose at most one of NGA — Exhaust tips, Black and NWI — Exhaust tips, Bright.",
  "whyAsked": "The target source identifies NGA; the Z06 comparator suggests NGA and NWI are peer choices.",
  "options": [
    {"optionId": "opt_nga_001", "rpo": "NGA", "label": "Exhaust tips, Black"},
    {"optionId": "opt_nwi_001", "rpo": "NWI", "label": "Exhaust tips, Bright"}
  ]
}
```

Requirements:

- Build this object in `WizardSessionStore` from current subject, evidence, target catalogs, comparator facts, and choices.
- It is display-only and excluded from compiler artifacts, semantic hashes, authority fingerprints, resolutions, previews, and mutation payloads.
- The browser must still submit the existing subject ID/version, action, and typed payload.
- Tests must prove that changing presentation copy cannot change a subject version, artifact hash, preview effect, or resolution entry.
- If a safe summary cannot be constructed, use a conservative decision-type template with RPOs and `Description unavailable`; do not fall back to raw JSON as the primary statement.

## Layout and interaction budgets

At 1,200 × 720 and 390 × 844:

- no horizontal overflow;
- collapsed summary rows are at most 120 px desktop and 160 px mobile;
- no more than one card is expanded;
- for representative section, relationship, rule-group, exclusive-group, and price subjects, the decision heading, proposed behavior, reviewer choices, and preview button fit within one viewport when the card top is aligned to the viewport;
- opening technical evidence may exceed one viewport, but it must not expand automatically;
- no nested scrolling region is added inside a card;
- touch targets remain at least 44 px high;
- focus is visible, disclosures report `aria-expanded`, async preview/save status uses `aria-live="polite"`, and focus moves to the preview heading after preview.

## Definition of done

1. A reviewer can identify the target model, proposed customer behavior, available choices, and save effect without opening technical details.
2. Each subject has one decision fieldset, one preview region, and one primary action button.
3. Confirm and reject never appear as separate full forms.
4. Empty evidence panels are absent.
5. Comparator payload and proposal signature are not duplicated at the primary level.
6. Exclusive-group members and selection behavior appear in plain language with available descriptions.
7. Semantic conflicts show `Existing` versus `Proposed` and expose no mutation control.
8. Exact workbook rows remain complete and inspectable after preview.
9. Preview and resolution requests remain byte-for-byte compatible with Milestone 2.4.
10. Presentation data cannot affect compiler, authority, subject, resolution, or preview hashes.
11. The layout and interaction budgets pass at both required viewports.
12. The fresh proof includes representative cards for every decision type and all semantic-conflict classes present in the current run.
13. An independent verifier performs a decision-comprehension check: without opening technical details, they can state the proposed rule and the consequence of every visible choice for each representative card.
14. `stingray_master.xlsx`, raw exports, compiler semantic artifacts, generated runtime contracts, `form-app/data.js`, publication, deployment, and dealer surfaces remain byte-identical.
15. Milestone 3 remains blocked and unapproved.

## Expected implementation files

Implementation:

- `scripts/corvette_form_generator/ingest/wizard/session.py` — generic display-only presentation projection.
- `visualizer/ingest-wizard/wizard.js` — compact queue, one expanded card, decision-first rendering, one-form action composition, concise preview summary.
- `visualizer/ingest-wizard/wizard.css` — compact rows, progressive-disclosure layout, required viewport behavior.
- `visualizer/ingest-wizard/index.html` — only if static exception-stage instructions or accessibility structure must change.

Tests:

- `tests/test_ingest_wizard_exception_flow.py` — presentation data and authority/hash isolation.
- `tests/test_ingest_wizard_server_milestone2.py` — response compatibility and strict mutation payload preservation.
- `tests/test_ingest_wizard_ui_milestone2.py` — one-form source contract and removal of duplicate top-level panels.
- A browser test or proof harness using disposable run data for structure, keyboard, preview, save, and geometry checks.

Docs and closure:

- this spec;
- `docs/ingest/milestone-2-4-exception-review-safety-semantic-conflict-plan.md`;
- `docs/ingest/README.md`;
- `docs/ingest/canonical-row-compiler-exception-queue-design.md`;
- a new Fable receipt and `fable5loop/STATE.md` only after independent verification.

No compiler semantic file, workbook schema, dependency, endpoint, or runtime consumer is expected to change. Any discovered need to change those surfaces requires a separate scope review before implementation continues.

## TDD implementation sequence

### Task 1 — RED presentation and authority-isolation contracts

Add failing session/server tests for decision-type presentation objects, option descriptions, conservative missing-description copy, and proof that presentation fields do not enter semantic or authority hashes.

### Task 2 — GREEN generic presentation projection

Implement the smallest session-layer projection needed by the seven actionable decision types plus conflict presentation. Use structured compiler/session data only; add no model/RPO allowlists and no business-rule inference.

### Task 3 — RED one-card/one-form browser contract

Replace source-string assertions with executable DOM requirements for compact summaries, single expansion, one fieldset, conditional action fields, one preview region, omitted empty evidence, and actionless conflict cards.

### Task 4 — GREEN decision-first renderer

Implement compact queue summaries, one expanded subject, per-decision-type primary statements, conditional controls, collapsed evidence, concise preview summaries, and exact-row disclosures. Preserve the current preview and resolution payload builders.

### Task 5 — Browser behavior and geometry proof

Against a disposable root, prove filter/search, expand/collapse, keyboard operation, preview invalidation, preview/save, rejection acknowledgement, focus movement, one-card advancement, and zero console/network errors. Record exact dimensions at 1,200 × 720 and 390 × 844.

### Task 6 — Fresh proof and independent closure review

Create a new current-source proof run. Review every decision type and conflict class, run the decision-comprehension check, compare protected hashes, run the full ingest gates, and close Milestones 2.4/2.4.1 only after the independent verifier passes without edits.

## Validation plan

Targeted automated gates:

```sh
PYTHONPATH=scripts .venv/bin/python -m pytest \
  tests/test_ingest_wizard_exception_flow.py \
  tests/test_ingest_wizard_server_milestone2.py \
  tests/test_ingest_wizard_ui_milestone2.py -q
node --check visualizer/ingest-wizard/wizard.js
```

Then run the complete ingest-wizard Python gate from `README.md`, Python compilation checks for changed modules, workbook package/schema validation, the serialized Node gate selected by `27vette-gate`, `git diff --check`, and `git status --short --branch`.

Browser proof must cover:

- desktop 1,200 × 720 and mobile 390 × 844;
- section, identity, relationship, rule-group, exclusive-group, default, price, prerequisite-blocked, and semantic-conflict cards;
- all current action types through disposable preview/resolve/reopen flows;
- retained observation runs through GET-only resume/filter/search;
- protected-surface hashes before and after proof.

## Preserved behavior and non-goals

- No change to semantic-overlap classification or conflict policy.
- No change to compiler row projection, action catalogs, subject lifecycle, or preview equality.
- No partial group/member/relationship editing.
- No batch approval, bulk rejection, or automatic decision.
- No new dependency, route, URL-state system, or split-pane application.
- No workbook write, plan projection, generation, registry publication, promotion, deployment, or dealer change.
- No mutation of historical, forensic, or observation runs.

## Rollback

Revert only the display projection, browser renderer/styles, scoped tests, and documentation changes. Remove only disposable proof artifacts created for this pass. Historical and observation runs remain unchanged. No workbook rollback is required because this milestone is read-only.

## Approval gate

Writing this spec does not approve implementation. Approval must explicitly authorize Milestone 2.4.1's presentation/session changes and its disposable proof only. It does not authorize Milestone 3, `pass-c-3`, live workbook writes, generation, publication, promotion, deployment, or dealer changes.
