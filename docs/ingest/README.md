# 27vette ingest docs

This folder owns the current schema and raw order-guide ingest planning docs.

Raw GM order-guide ingest is an edge workflow, not routine maintenance. Use it only for:

- adding a model that is not already in the form; or
- performing a broad GM/order-guide refresh across existing models.

Routine corrections belong in canonical workbook source sheets, followed by normal regeneration and gates.

## Standing division of responsibilities

The script owns structure-derived parsing: sheet profiling, option row extraction, OVS status extraction, source evidence preservation, and exact 1-to-1 price joins.

The user owns business interpretation: sections, groupings, exclusive groups, relationship meaning, ambiguous prices, vague disclosures, and any row where the raw sheet structure does not determine the workbook destination.

## Current docs

- `ingest-wizard-end-to-end-completion-spec.md` — approved 2026-07-05 (checkpoint 1; open product decisions resolved same day) program spec for Passes B–F: model scoping + decision capture, decision export + dry-run apply plan, approved workbook apply, regeneration + model gates, and runtime promotion of Grand Sport X, ZR1, and ZR1X through the same workbook→generator→registry→runtime pipeline as live models. Pass B implemented 2026-07-05 (+ B.1/B.2/B.3/B.4 review-ergonomics corrections, 2026-07-06; B.5 review filtering/bulk skip, B.6 skipped-row suppression, B.7 ref-only section assignment, B.8 relationship-lane simplification, and B.9 blocker panel + richer review filters, 2026-07-07); Pass C (dry-run apply plan + approval gate) implemented 2026-07-06; Passes D–F pending, gated by checkpoints 2–5.
- `pass-b/pass-b2-review-finetune-spec.md` — implemented (2026-07-06) correction spec for the review stage per Sean's feedback: selection-scoped bulk actions with undo/clear, script-owned copy splitting with an exception-only queue, workbook-based reference display replacing the export-comparator concept, and plain-language decision labels. Later B.3/B.4 field-note fixes are summarized in `ingest-wizard-end-to-end-completion-spec.md`.
- `pass-b/pass-b5-review-filtering-and-bulk-skip-spec.md` — implemented (2026-07-07) small reviewer-ergonomics correction: decision-state filtering for section/price queues and checked-row bulk `Skip — don't carry over` for section assignment.
- `pass-b/pass-b6-skipped-row-lane-suppression-spec.md` — implemented (2026-07-07) follow-up: section-skipped rows are hidden from later candidate review lanes and ignored in later-lane progress/hold counts.
- `pass-b/pass-b7-ref-only-section-assignment-spec.md` — implemented (2026-07-07) follow-up: ref-only RPO rows now enter Section assignment, can be assigned/selectable/not-selectable/skipped there, and only orderable rows owe price review.
- `pass-b/pass-b8-relationship-lane-simplification-spec.md` — implemented (2026-07-07) follow-up: Relationship authoring now exposes only workbook-safe Requires / Includes / Not available with rule choices, hides generic approve/skip and business-question controls from the normal form, and normalizes hint aliases before save.
- `pass-b/pass-b9-blocker-ux-and-filters-spec.md` — implemented (2026-07-07) follow-up: the Standard Equipment queue excludes priced rows; decision-state filtering extends to all per-candidate lanes plus new price-presence, workbook-reference, and section-assigned filters; and an always-visible blocker panel links every completion blocker to its model/lane/row and refreshes as decisions save.
- `pass-a/interactive-ingest-wizard-pass-a-spec.md` — implemented (2026-07-03) rewrite of the wizard entry path: browser-first upload/choose → friendly sheet-card profiling → sheet-role confirmation → deterministic option/price parsing → exact 1-to-1 price joins → read-only reviewable candidate table. Explicitly no apply planning, decision capture, or workbook writes. Records the corrected end-to-end flow later passes follow.
- `pass-0/ingest-wizard-source-profiler-spec.md` — implemented CLI-first, read-only source profiler that emits source-layout, variant-matrix, raw-row, disclosure-link, manifest, and checkpoint artifacts before any candidate normalization or workbook apply exists.
- `pass-1/candidate-normalizer-spec.md` — implemented CLI-first, read-only candidate normalizer over Pass 0 evidence artifacts; emits transient candidate and unresolved-review artifacts only.
- `pass-2/interactive-review-wizard-spec.md` — implemented read-only Ingest Review tab over Pass 1 candidate artifacts; captures/export review decisions without workbook apply.
- `pass-3/expert-interpretation-review-reduction-spec.md` — implemented CLI/report-first read-only expert interpretation/review-reduction pass; aggregates raw candidates into model/RPO review units, matches workbook context by RPO identity only, classifies duplicate source RPO rows, and reports source-sheet coverage before any UI/default-view or apply-planning pass.
- `pass-4/reduced-review-ui-spec.md` — implemented read-only workbook-editor server/UI pass that makes Pass 3 interpretation artifacts the default reduced Ingest Review view when configured while preserving raw Pass 1 drill-down/debug.
- `pass-5/focused-model-workbook-build-review-spec.md` — implemented corrective pass. Ingest now selects target models immediately after Pass 0 header/model profiling (`--models zr1,zr1x,z06`; ZR1/ZR1X primary, one comparator), persists the selection as `model-selection.json`, filters Pass 1/3 to that scope, and reviews concrete workbook-destination lanes (option rows, OVS rows, relationships, pricing, duplicates/source coverage, blocked extractor gaps) with workbook-build actions instead of abstract decision states. Server/UI fail closed on missing selection artifacts, selection mismatch, evidence-fingerprint mismatch, and comparator or non-selected model leakage.

## Current decisions

- Keep `Order-Guide_IngestPrompt.md`, but treat the old content as replaced by the rewritten normalized prompt.
- Continue ingest work on the single `ingest-wizard` branch after merging Pass 0/1 into local `main`; do not create a new branch per pass unless explicitly requested.
- Pass 3 intentionally superseded the older Pass 2 next-step note that pointed directly to apply planning. Pass 4 proved the broad reduced queue was technically safe but not reviewer-usable enough. Pass 5 implemented the required correction: select target models early and review concrete workbook-build lanes. Dry-run apply planning stays a separate future pass, allowed only after the focused ZR1/ZR1X workbook-build review proves usable in real review sessions.
- `docs/workbook-sheet-index.md` was stale and has been archived to `docs/archive/workbook-sheet-index-2026-06-12.md`.
- Existing ZR1/ZR1X workbook source scaffolds should not be used as canonical ingest truth. They need a focused clean reprocess path through Pass 5 before future apply planning relies on them.
- 2026-07-03: the CLI-first Pass 0→1→3→5 sequence proved confusing and ineffective at reaching a clean reviewable candidate table. Pass A supersedes it as the wizard entry path: the browser comes first, sheet roles are confirmed by the user before parsing, and price backfill is a deterministic exact-match join with an explicit ambiguity queue. Pass 0–5 modules stay in place as parsing/review libraries and reference (the workbook editor's legacy Ingest Review tab still reads their artifacts) until later passes retire them explicitly.
