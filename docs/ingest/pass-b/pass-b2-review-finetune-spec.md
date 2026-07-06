# Pass B.2 — review-stage fine-tune: selection-scoped bulk with undo, script-owned copy split, workbook reference, plain-language labels

Date: 2026-07-06
Status: Draft — awaiting Sean's approval (checkpoint: this spec closes out Pass B once implemented and verified).
Parent: `docs/ingest/ingest-wizard-end-to-end-completion-spec.md` (Pass B). Supersedes nothing; corrects the B/B.1 review stage per Sean's 2026-07-06 feedback.

## Feedback being fixed (verbatim intent)

1. Bulk actions wrong shape: reviewer must be able to **select specific rows** and assign those to a section; current bulk assigns one section to every filtered row, **with no undo**.
2. Reviewer should **not** split copy by hand; the script owns copy splitting (it did in earlier passes) and the reviewer only touches exceptions.
3. The "compare" affordance shows nothing and is aimed at the wrong source: comparison must be **modeled on data already in the workbook**, not another ingested sheet family.
4. Decision dropdowns need **layman's language** — "approved for plan", "needs product decision" etc. don't click.

## Diagnosis — current-state evidence

- Bulk bar (`visualizer/ingest-wizard/wizard.js` `renderBulkBar`/`bindBulk`) operates on *all* filtered rows without a decision; there are no row checkboxes and no decision deletion anywhere — `save_decisions` only upserts (`scripts/corvette_form_generator/ingest/wizard/session.py`), so a wrong bulk action can only be repaired by re-saving row by row.
- Copy-split lane prefills name/description from a naive `description.split(".")` in the UI and makes the reviewer own the whole split. Legacy script-owned splitting exists: `scripts/corvette_form_generator/ingest/candidate_normalizer.py:source_name_candidate()` (name = text before " / " or newline), and Pass A already preserves full raw text per candidate. Live target shape confirmed in the workbook: `*_options` sheets carry `option_name`, `description`, `detail_raw` (probe 2026-07-06: `z06_options`/`grandSport_options` headers).
- Comparator today is an export-sheet concept: selected in stage 4, stored in `model-selection.json.comparators`, used **only** for presentation-template prefill; comparator candidates are excluded from queues and no comparison data is ever rendered — hence "shows no options". The workbook-based lookup Sean wants already has a proven pattern: `candidate_normalizer.py:load_workbook_option_index()` (live `*_options` rows indexed by RPO via `model_workbook_sources`).
- Vocabulary (`approved_for_plan`, `hold_for_question`, `not_needed`, `needs_product_decision`, …) renders as raw identifiers with underscores swapped for spaces (`resolutionOptions`, `selectControl`). Values are load-bearing in artifacts (`review_payload.py` vocabulary, Pass C consumes them) — only the display layer may change.

Risk level: medium (review-stage tooling/UI/tests only; workbook stays read-only; artifact schema additions are backward-compatible). Change class: tooling/UI/tests/docs.

## Design

### 1. Selection-scoped bulk actions + undo

**Row selection.** Per-candidate lanes get a leading checkbox column plus a header "select all (filtered)" toggle. The bulk bar shows the live checked count and acts on **checked rows only**; buttons disabled at zero checked. "Select all filtered" is an explicit click, never the default. Selection survives re-render within a lane view, clears on lane/model/filter change.

**Batch identity.** Every `POST /decisions` call gets a server-assigned `batchId` (uuid) stamped on each record and returned in the response. `decisions-log.jsonl` entries carry it. Existing records without `batchId` stay valid (additive field, schema stays `pass-b-1`-compatible; bump artifact `schemaVersion` to `pass-b-2` on next write).

**Undo / clear.**
- New store method `delete_decisions(run_id, *, decision_ids=None, batch_id=None)` — removes matching records from `decisions.json`, appends `{"deleted": [...], "batchId"?, "at"}` events to the log (audit trail preserved), returns deleted count. Completeness recomputes automatically on next `progress` read.
- New endpoint `POST /api/wizard/sessions/<id>/decisions/delete`.
- UI: per-row "Clear" button next to Save on decided rows; bulk bar shows "Undo last bulk (n rows)" for the most recent batch created in this lane/model view (client keeps the returned `batchId`; server-side delete-by-batch works for any batch).
- Guard: deleting decisions can drop a model out of `decisions_complete`; session state falls back to `decisions_in_progress` when a delete touches a completed run.

Bulk actions themselves (section assign, accept-exact-price, status confirm, SE include/exclude) keep their existing decision shapes — only the target set changes (checked rows) and every bulk response surfaces its `batchId` for undo.

### 2. Script-owned copy split

**Splitter (deterministic, script-owned).** New `propose_copy_split(candidate)` in `scripts/corvette_form_generator/ingest/wizard/` (reusing/upgrading `source_name_candidate`):

- `name`: text before the first sentence break, " / ", or newline; trimmed of trailing footnote digits.
- `description`: remaining sentences minus disclosure sentences.
- `disclosure`: sentences matching disclosure patterns — the `hints.py` relationship phrases ("Not available with…", "Requires…", "Included with…") **extended with new** subscription/legal-boilerplate patterns owned by the splitter — plus any text tied to a footnote marker.
- `detailRaw`: the full raw description, always preserved verbatim.
- `flags`: reasons the split needs human eyes — `no_sentence_break`, `name_over_60_chars`, `unmatched_footnote_marker`, `all_text_matched_disclosure`. Zero flags = clean split.

Proposals are computed server-side and attached to every candidate in the copy-split queue (`proposedSplit` field). Pure function of candidate text — deterministic, tested against real-export shapes.

**Lane becomes exception-first.** Copy-split queue defaults to a "needs review" filter (flagged candidates only) with a toggle to see all. Rows prefill from `proposedSplit`; reviewer edits only what's wrong. Bulk action: "Accept script split for checked rows" (records `split_copy` decisions with the proposed payload). Candidates with no copy-split decision fall back to the script proposal at Pass C plan time — the reviewer owns exceptions, not the whole surface (this matches the standing division of responsibilities in `docs/ingest/README.md`). Completeness stays non-mandatory for this lane.

### 3. Workbook reference (replaces the export-comparator concept)

**Reference index.** New `workbook_option_reference(workbook_path)` in `decisions.py`, modeled on `load_workbook_option_index()`: read-only index of live `*_options` rows (via active `model_workbook_sources` `source_option_sheet` roles) keyed by RPO → `{modelKey, optionName, sectionId, sectionName, price, description}` (section name resolved through `section_master`). Cached per server process; workbook never written.

**Surfacing.** `review_queue` attaches `workbookReference[rpo]` for every queue candidate. UI renders a compact reference line under the description on every per-candidate lane row — e.g. `In workbook: Z06 “Carbon Ceramic Brakes” · Wheels · $9,995` — and the evidence drawer shows all matching live rows. Section lane gets a per-row "Use Z06's section" one-click that fills the section select from the reference (reviewer still saves). Rows whose RPO has no live match show "New to workbook — no reference" so silence is explicit, not broken.

**Comparator retirement.** Stage-4 comparator selects are relabeled **"Reference model"** (defaults unchanged per resolved decision 3: `grand_sport` for GSX, `z06` for ZR1/ZR1X). The stored key `comparators` keeps its name for artifact compatibility; it now drives (a) presentation-template prefill (unchanged) and (b) which reference model sorts first when several live models match an RPO. Nothing depends on the export's comparator sheets anymore; export-sheet comparator copy is removed from UI text and docs.

### 4. Plain-language decision vocabulary (display layer only)

Stored values unchanged (artifact/Pass C compatibility). UI label + help map, e.g.:

| Stored value | UI label | Tooltip |
|---|---|---|
| `approved_for_plan` | "Approve — write to workbook" | Goes into the apply plan in Pass C. |
| `hold_for_question` | "Hold — I have a question" | Counts as reviewed; listed in the holds report until resolved. |
| `not_needed` | "Skip — don't carry over" | Recorded so it never comes back as missing. |
| `needs_product_decision` | "Flag for product call" | Blocks nothing by itself; shows in the flags list. |
| `defer_price_extractor` | "Defer — fix price source later" | Price stays empty in the plan until decided. |
| `create_option_row` / etc. | verb-first plain labels | one-line effect description |

Plus: a one-line lane header under the lane picker ("Section assignment — pick where each option lives in the form"), and a collapsible "What do these buttons mean?" glossary on the review stage. All labels live in one JS map so copy edits never touch logic.

## Exact files to change after approval

- `scripts/corvette_form_generator/ingest/wizard/decisions.py` — `batchId` stamping, `workbook_option_reference()`, `propose_copy_split()` (or a small new `copy_split.py` module), delete support in decision-state helpers.
- `scripts/corvette_form_generator/ingest/wizard/session.py` — `delete_decisions()`, reference/proposal attachment in `review_queue`, batch id in `save_decisions`/`copy_model_decisions`.
- `scripts/ingest_wizard_server.py` — `/decisions/delete` endpoint.
- `visualizer/ingest-wizard/{wizard.js,index.html,wizard.css}` — row checkboxes + select-all, checked-count bulk bar, undo/clear controls, copy-split exception queue, reference lines + "use reference section", label/glossary map, reference-model relabel.
- `tests/test_ingest_wizard_decisions.py` — delete/undo (by ids and batch), completion fallback on delete, batch stamping.
- `tests/test_ingest_wizard_copy_split.py` (new) — splitter determinism, flag cases, real-export shape samples.
- `tests/test_ingest_wizard_server_pass_b.py` — delete endpoint, reference payload presence.
- Docs: this spec closeout; `docs/ingest/README.md` pointer; parent spec Pass B status ("closed after B.2"); `Order-Guide_IngestPrompt.md` Pass B bullet (reference model wording).

## Source-of-truth decision

Workbook stays the only product source and stays read-only; the reference index is a display of existing workbook truth. Split proposals are script-derived candidates, never applied without a decision or the explicit Pass C fallback rule (which the plan report must label "script split, unreviewed"). Stored decision vocabulary unchanged; language changes are UI-only.

## Companion-file impact

Workbook editor, `form-app/`, generated artifacts, dealer submission: untouched. Legacy pass modules: `source_name_candidate` logic reused/ported, module untouched. Parent spec + ingest README updated as above.

## Constraints

No new dependencies. No schema-breaking artifact changes (additive fields; version bump to `pass-b-2` on new writes, loaders accept both). No changes to completeness semantics except state fallback on delete. Protected boundaries per AGENTS.md unchanged.

## Risks and non-goals

Risks: splitter quality on messy GM text (mitigated: flags + exception queue + full raw always preserved); reference index size (~2k rows, trivial); undo semantics confusion (mitigated: audit log keeps deletions, per-row Clear always available).

Non-goals: multi-level undo history UI (single last-batch undo + per-row clear + delete-by-batch API is enough); editing live workbook rows from the reference panel; changing stored decision vocabulary; Pass C scope.

## Validation plan

- New/updated pytest suites (delete/undo/batch, splitter incl. flag cases on real-export text samples, reference payload, endpoint errors); all existing wizard suites stay green.
- Browser proof on the real export: check 5 specific rows → bulk-assign a section to exactly those 5 → undo restores 0/5; copy-split queue shows flagged-only by default with prefilled proposals; a candidate with a live Z06 RPO shows the workbook reference line and "use reference section" works; dropdowns show plain-language labels; zero console errors.
- Protected surfaces clean (`git status` on workbook/form-output/form-app).
- Independent verifier per the Fable loop, then Pass B declared closed in the parent spec.

## Definition of "Pass B closed"

B.2 implemented and verifier-passed → Sean runs a real review session and signs off decision sets (checkpoint 2 of the parent spec) → Pass B status set to closed; Pass C (decision export + dry-run apply plan) becomes the active pass.
