# Outcome rubric · 2026-07-06 · Pass B.2 implementation

Rubric = the approved spec `docs/ingest/pass-b/pass-b2-review-finetune-spec.md` (Design §1–§4 + validation plan). Graded criteria:

1. **Selection-scoped bulk + undo**: row checkboxes + select-all-filtered; bulk buttons act on checked rows only, disabled at zero; batchId on every save (decisions and copies); `delete_decisions` by ids/batch with audit-log events; per-row Clear; undo-last-bulk in UI; completed state falls back on delete.
2. **Script-owned copy split**: deterministic `propose_copy_split` (name/description/disclosure/detailRaw/flags — hints phrases extended with boilerplate patterns); copy-split queue defaults to flagged-only with show-all toggle; rows prefill proposals; bulk "accept script copy for checked".
3. **Workbook reference**: `workbook_option_reference` (live `*_options` via active `model_workbook_sources`, section names resolved, inactive sources ignored, mtime-cached); every per-candidate lane row shows reference line or "New to workbook"; section lane one-click "Use <model>'s section"; stage-4 relabeled "Reference model"; no dependency on export comparator sheets.
4. **Plain language**: display-only label maps for resolutions and actions with tooltips; per-lane help line; glossary; stored values unchanged (decisions.json schemaVersion bumped additively to pass-b-2, loaders accept both).
5. **Pass B semantics preserved**: completeness math, fingerprints, comparator exclusion, reconciliation blocker unchanged; all prior wizard tests green.
6. **Boundaries**: workbook read-only; protected surfaces clean.
7. **Validation real**: suites green; browser proof per spec (check 5 → bulk-assign exactly 5 → undo to 0; flagged-only split queue with prefills; reference line + use-section works; plain labels visible; zero console errors).
8. **Verifier PASS + closeout** (receipt, STATE, skill decision, loop validator).

Stop: criteria 1–7 gradable from artifacts; verifier pass; STATE updated. Max 3 cycles.
