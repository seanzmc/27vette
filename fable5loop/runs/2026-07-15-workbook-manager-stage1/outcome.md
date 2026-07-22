# Outcome Rubric · Workbook Manager Stage 1 (React + FastAPI + SQLite)

Task source: `docs/react-editor prompt.md` (user-provided spec, implementation
requested 2026-07-15). Sean approved: Vite + real React frontend; gated live
sync through the existing `save_workbook_safely()`/`apply_batch` pipeline.

## Measurable criteria (verifier grades each PASS/FAIL with evidence)

1. **Lossless import.** For each active options sheet, DB rows + reported
   duplicate/missing-identifier issues == workbook data rows; every workbook
   sheet is either normalized or preserved verbatim in `raw_sheet_rows`.
   Evidence: `tests/test_workbook_manager.py::TestImportFidelity` green.
2. **Every unresolved relationship / duplicate id reported.** Orphan OVS
   references equal reported `unresolved_ref` issues; duplicates recorded
   with sheet/row/key. Evidence: TestImportFidelity green.
3. **Model-scoped identity.** `UNIQUE(model_id, option_id)` enforced
   (verified overlap: 144–186 shared option_ids across models); rule/group/
   price ids model-scoped; `interior_id` global. Evidence: specs.py DDL +
   uniqueness tests.
4. **Staged editing.** add/update/delete stage → validate → commit; undo
   before commit leaves no trace; delete blocked on dependents unless
   confirmed; read-only tables (section_master, raw sheets) and inactive
   scaffolds (zr1/zr1x) rejected with actionable messages. Evidence:
   TestStagingWorkflow green.
5. **Append-only SQL audit.** Every committed change appears in
   `change_history` with ts/actor/entity/model/op/old/new/src sheet+row/
   validation/status/sync_status. Evidence: staging tests + schema DDL.
6. **Sync only through the gated pipeline.** No openpyxl write to
   `stingray_master.xlsx` outside `editor_ops.apply_batch` →
   `save_workbook_safely()` (backup, lock, mtime, schema validation
   enforced there); live write additionally requires confirm token +
   dry-run-matching mtime. Evidence: sync.py review + TestSyncBatch.
7. **Comparison export preserves unmanaged content.** Regenerated workbook
   keeps all 65 sheets; PriceRef byte-identical; managed sheet row counts
   preserved. Evidence: TestComparisonExport green.
8. **Display-only normalization.** Canonical ids never rewritten; Title
   Case + confirmed-prefix stripping derived at display time, reversible.
   Evidence: TestNaming green.
9. **Stage-2 ready.** React talks only to the API; schema/validation are
   table-spec-driven; flipping canonical source changes sync direction,
   not the interface. Evidence: architecture review (api.js has no
   workbook/sqlite knowledge; specs.py is single source).
10. **No repo boundary violations.** `stingray_master.xlsx`, `form-output/`,
    `form-app/`, dealer surfaces untouched; only new files added.
    Evidence: git status in validation-output.txt.

## Gates not runnable in this sandbox (documented, not waived)

- FastAPI API tests (PyPI blocked): auto-skip until
  `workbook-manager/backend/requirements.txt` installed; command in README.
- Vite/React build (npm registry blocked): `npm install && npm run build`.
- Full `apply_batch` dry-run/live-write gate tests: `WBM_SLOW_GATE=1`
  (schema-validation stage exceeds the sandbox 42s process cap; all other
  gate stages verified piecewise — see validation-output.txt).
