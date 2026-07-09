# Outcome rubric · 2026-07-08 · Pass D apply CLI implementation

Task summary:
- Goal: implement the approved Pass D CLI/tests/docs path without running the live workbook `--write`.
- Source spec: `docs/ingest/pass-d/pass-d-approved-workbook-apply-spec.md`.
- Target approved run for real dry-run proof: `20260707-193441-ea9e4c`.

Pass criteria:
1. CLI-only apply entrypoint exists at `scripts/ingest_wizard_apply.py`; default mode is dry-run and JSON output.
2. Store method refuses unsafe states: unapproved, approval hash mismatch, decision/source/workbook fingerprint mismatch, stale workbook, Excel lock via `apply_batch`, and already-applied mutation attempts.
3. Apply executes one combined `stage1.items + stage2.items` batch through `editor_ops.apply_batch()`; no parallel workbook writer.
4. Fixture write path exercises `save_workbook_safely()`, backup/log/report creation, on-disk readback verification, and `applied` state locking.
5. Real approved run is exercised in dry-run mode only; no live workbook write.
6. Generated runtime, `form-app/data.js`, runtime JS/CSS/HTML, and dealer-submission surfaces remain untouched.
7. Scoped tests, syntax checks, workbook package/schema validation, diff check, Fable validator, and independent verifier pass or required fixes are applied.

Result: pending independent verifier at initial receipt creation; parent validation passed before verifier dispatch.
