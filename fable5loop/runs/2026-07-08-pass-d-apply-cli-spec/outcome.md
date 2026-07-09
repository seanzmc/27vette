# Outcome rubric · 2026-07-08 · Pass D approved workbook apply CLI spec

Task summary:
- Goal: write the Pass D child spec for the approved workbook apply CLI after C.2 plan approval, preserving workbook safety and keeping live `--write` as a separate explicit checkpoint.
- Changed surface: docs + loop artifacts only. No code implementation, workbook write, generated artifact refresh, runtime change, or dealer-submission change.
- Source-of-truth decision: `docs/ingest/pass-d/pass-d-approved-workbook-apply-spec.md` owns Pass D implementation detail; `docs/ingest/ingest-wizard-end-to-end-completion-spec.md` stays the program overview and points to the child spec.
- Protected boundaries: `stingray_master.xlsx`, generated runtime artifacts, `form-app/data.js`, and dealer submission untouched.

Required outcome criteria:
1. Child spec exists on disk under `docs/ingest/pass-d/` and satisfies AGENTS.md §4: diagnosis, exact expected files/sheets/artifacts, source-of-truth decision, companion-file impact, constraints, risks/non-goals, and validation plan.
2. Spec is grounded in current Pass C.2 evidence: run `20260707-193441-ea9e4c` is `plan_approved`, plan valid, 52 + 5,719 ops, dry-run clean, zero blocking gaps/gaps/uncovered decisions, no workbook write.
3. Approval boundary is explicit: approval to implement CLI/tests/docs is separate from approval to run live workbook `--write`.
4. Pass D implementation is pinned to CLI-only, dry-run-default, no server endpoint, no UI stage-7/apply button for the first apply pass.
5. Workbook safety is explicit: no `--allow-stale`, plan approval hash, decision/source/workbook fingerprints, Excel lock refusal, one combined `stage1 + stage2` batch, `editor_ops.apply_batch()`, `save_workbook_safely()`, apply report, and on-disk readback verification.
6. Generated/runtime/dealer boundaries are preserved: no generation, registry publication, runtime promotion, dealer endpoint/payload/security changes, or live dealer submission in Pass D.
7. Related docs are consistent with the child spec, especially `docs/ingest/README.md` and the Pass D section of `docs/ingest/ingest-wizard-end-to-end-completion-spec.md`.
8. Loop closeout complete: validation output recorded, independent verifier result recorded, required verifier fix applied, run receipt present, and `fable5loop/STATE.md` updated.

Stop conditions:
- Spec and related doc pointers are on disk.
- The independent verifier's required fix is applied.
- `git diff --check` and `scripts/validate_fable5_loop.py` pass.
- STATE.md last-session pointer references this receipt.
