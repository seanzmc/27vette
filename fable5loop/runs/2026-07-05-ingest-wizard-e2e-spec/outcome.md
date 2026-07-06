# Outcome rubric · 2026-07-05 · Ingest-wizard end-to-end development spec

## Task summary

- Goal: write the full development spec that completes the raw order-guide ingest wizard end to end — ingest Grand Sport X, ZR1, ZR1X from the official order-guide export; review/resolve human-owned decisions; write approved data into `stingray_master.xlsx` safely; regenerate artifacts; promote completed models into the runtime via the same workbook→generator→runtime pipeline as existing live models.
- Changed surface: docs only (a spec document + ingest docs index pointer). No code, workbook, generated-artifact, runtime, or dealer changes in this run.
- Source-of-truth decision: spec lives under `docs/ingest/` (owner of ingest detail per `AGENTS.md` no-redundancy rule); loop artifacts under `fable5loop/runs/`.
- Protected boundaries: `stingray_master.xlsx`, `form-output/` tracked artifacts, `form-app/data.js`, dealer submission — all untouched.
- Expected files: new spec under `docs/ingest/`, updated `docs/ingest/README.md` pointer, run receipt folder, `fable5loop/STATE.md`.

## Required outcome criteria

1. **Spec exists on disk** under `docs/ingest/` and covers the full chain: decision capture → decision export → apply planning (dry-run) → approved workbook apply with §5 safety → regeneration → validation gates → runtime promotion for GSX/ZR1/ZR1X, each as an explicitly scoped pass with entry/exit criteria.
2. **AGENTS.md §4 spec checklist satisfied**: diagnosis with current-state evidence; exact files/sheets/artifacts per pass; source-of-truth decisions; companion-file impact; constraints; risks and non-goals; validation plan matched to each pass's surface.
3. **Grounded in verified current state**: cites the implemented Pass A contract (session states, artifact schemas), the real promotion pipeline (model metadata sheets, generator commands, promotion gates) and workbook safety tooling (`save_workbook_safely()`), with real file/sheet references — no invented scripts, sheets, endpoints, or gate names.
4. **Hard guardrails preserved**: raw-value preservation, no invented data, transient candidate artifacts, ZR1/ZR1X clean-reprocess rule (existing scaffold rows are not canonical truth), stop-on-invariant-failure, apply pass dry-run-by-default with `--write`, human approval checkpoints before every workbook write and before promotion.
5. **Human-owned vs script-owned decisions explicit**: the spec enumerates the reviewer-owned decision lanes (sections, groups, exclusive groups, relationships, ambiguous prices, copy splits, interiors/colors, presentation metadata) and how the wizard captures/resolves each.
6. **Promotion parity**: the promotion pass uses the same workbook→generator→registry→runtime path and gate pattern as existing live models, with per-model gates named following the existing convention; no runtime special-casing.
7. **Independent verifier PASS** recorded in `verifier-report.md` in this run folder, grading criteria 1–6 from artifacts only.
8. **Loop closeout complete**: run receipt (`outcome.md`, `verifier-report.md`, `validation-output.txt`, `run.json`), `STATE.md` updated with evidence-backed facts and last-session pointer, skill-update decision recorded, docs-only validation performed (diff review + `validate_fable5_loop.py` if loop artifacts changed).

## Stop conditions

All of: spec on disk; verifier PASS (or human-accepted failure recorded in `run.json`); STATE.md last-session updated; run.json complete; validation run and reported.

Max iterations: 3 maker/verifier cycles.
