# Outcome rubric · 2026-07-05 · Pass B — model scoping + decision capture

## Task summary

- Goal: implement Pass B of the approved `docs/ingest/ingest-wizard-end-to-end-completion-spec.md` — model selection (B1), ten decision lanes (B2), completeness gate (B3) — in the ingest wizard.
- Changed surface: tooling/UI/tests/docs. Read-only toward `stingray_master.xlsx`, tracked `form-output/`, `form-app/`, dealer submission.
- Source-of-truth decision: parsing/decision tooling in Python under `scripts/corvette_form_generator/ingest/wizard/`; transient artifacts under `form-output/ingest-wizard/<run-id>/`; docs own workflow description.
- Protected boundaries: no workbook writes; no generated-artifact or registry changes; hints are suggestions only; nothing invented.
- Expected files: `decisions.py`, `hints.py` (new); `session.py`, `ingest_wizard_server.py`, `visualizer/ingest-wizard/*` (extended); new/extended tests; `docs/ingest/README.md`, `Order-Guide_IngestPrompt.md`, spec status.

## Required outcome criteria

1. **B1 model selection works**: after `parsed`, reviewer selects targets from detected families with per-family candidate counts; comparator defaults per resolved decision 3 (`grand_sport` for GSX, `z06` for ZR1/ZR1X); `model-selection.json` persisted; downstream fails closed on selection mismatch; comparator candidates read-only and excluded from export/completeness.
2. **Variant reconciliation** report per selected model (export headers vs `variant_master`/`model_variants`, read-only) with disagreements becoming mandatory decisions.
3. **All ten lanes implemented** per spec B2, including lane 10 presentation-metadata with template prefill from the decided live model, per-row approve/edit/delete, template provenance recorded; decisions persist incrementally (append log + snapshot), survive server restart, and are invalidated by fingerprint mismatch rather than silently kept.
4. **Completeness gate (B3)**: `decisions_complete` requires section+price+status resolution (or explicit hold/defer) for every in-scope orderable candidate and approved lane-10 row sets in all five presentation sheets per model; holds enumerated in a blocking report; per-lane progress visible.
5. **Hints deterministic and advisory**: phrase-scan suggestions are pure functions of candidate text, never auto-applied.
6. **Boundaries preserved**: `git status` clean for `stingray_master.xlsx`, tracked `form-output/`, `form-app/`; workbook opened read-only everywhere; artifacts carry `schemaVersion: "pass-b-1"` and upstream fingerprints.
7. **Validation real**: new pytest suites green; full `pytest tests/` run with pre-existing failures identified as pre-existing by evidence; browser proof against the 28-sheet export covering selection, a representative slice of every lane, restart-resume, and one model reaching `decisions_complete` (fixture-scale acceptable for full completion if real-export full completion is impractical in-session — state exactly what was proven).
8. **Independent verifier PASS** in this folder's `verifier-report.md`; loop closeout complete (receipt, STATE, skill decision, loop validator if loop artifacts changed).

## Stop conditions

All of: implementation on disk; criteria 1–7 gradable from artifacts/tool output; verifier pass or human-accepted failure in `run.json`; STATE last-session updated. Max 3 maker/verifier cycles.
