# Verifier Report — 2026-07-11 Grand Sport stripe ↔ heritage hash reverse exclusions

## Verdict

PASS (single cycle). Independent verifier in a separate context; saw rubric, artifacts, diffs, and gate output only — no maker reasoning.

## Criteria

1. **Workbook truth — PASS.** openpyxl read-only: exactly 16 groups `gs_group_<rpo>_excludes_heritage_hash_and_z15` (dpb dpc dpg dpl dpt dsy dsz dt0 dth dub due duk duw dzu dzv dzx) in `grandSport_rule_groups`, each `excludes_any`, active, `source_id=opt_<rpo>_001`; each with exactly 7 active member rows in `grandSport_rule_group_members` targeting {opt_z15_001, opt_17a_001, opt_20a_001, opt_55a_001, opt_75a_001, opt_97a_001, opt_dx4_001}. Cross-check: `gs_group_z15_excludes_non_center_stripes` has 21 targets; minus sht/vpo/pda/sne/vpw equals the 16 sources exactly.
2. **Generated-artifact purity — PASS.** `git diff -U0`: exactly 4 hunks — per file one 1-line `generated_at` replacement plus one 320-line insertion; removed lines are the two `generated_at` lines only; added `group_id` lines are exactly the 16 new names once each per file (642 added lines = 2×321). No changes to `form-app/app.js`, `form-app/styles.css`, or dealer surfaces.
3. **Runtime semantics — PASS (static).** `excludesAnyReason` (app.js:1012) + `sourceExcludesTargetViaGroup` (app.js:1002) disable a candidate when any selected option's `excludes_any` group targets it → new groups disable hash marks/Z15 when a stripe is selected. `gs_group_z15_excludes_non_center_stripes` still present (21 targets incl. `opt_dpb_001`) → reverse direction preserved. Contract JSON: 44 ruleGroups total, 16 new, all with the exact 7-target set.
4. **Gates — PASS.** node --test (grand-sport-contract-preview, grand-sport-draft-data, multi-model-runtime-switching): 72/72. pytest metadata gates: 75 passed. Post-gate `git status --porcelain -- form-output form-app` identical to pre-gate — gates introduced no churn; the entire diff is the intended change.
5. **Schema — PASS.** `validate_workbook_schema.py stingray_master.xlsx`: status valid, 0 errors, 0 warnings.

## Evidence inspected

- `stingray_master.xlsx` sheets `grandSport_rule_groups` / `grandSport_rule_group_members` (openpyxl read-only probes).
- `git diff -U0` and `git status --porcelain` for `form-app/data.js`, `form-output/runtime/grand-sport-runtime-contract.json`, `form-app/app.js`, `form-app/styles.css`.
- `form-app/app.js` grouped-exclusion code path (lines 1002–1024, 1104).
- `form-output/runtime/grand-sport-runtime-contract.json` parsed ruleGroups.
- `.hermes/plans/grand-sport-stripe-heritage-reverse-exclusions-spec.md`.

## Validation Output Inspected

- node --test 3 files: 72 tests, 72 pass, 0 fail (includes Grand Sport dealer-submission and stripe/hash runtime tests).
- pytest 4 metadata files: 75 passed in ~1s.
- `validate_workbook_schema.py`: `"status": "valid", "error_count": 0, "warning_count": 0`.
- Post-gate git status matched pre-gate state (same 3 modified files, same diff stats).

## Required Fixes Before Pass

None — single-cycle pass.

## Durable Lesson Candidates

None. The fix applied the repo's established explicit-reverse-group workbook convention and existing pipelines; the skill already encodes the relevant lessons (workbook owns rules; gate-churn hygiene; measurable rubric).

## File Edit Statement

Verifier edited no files. All inspection read-only; only the listed test gates were executed, and post-gate `git status` matched pre-gate state.

## Notes (non-blocking)

- `form-output/workbook-edit-log.jsonl` gained the expected audit line (opCount 128) — include in the commit deliberately.
- Backup `backups/stingray_master-20260711-121000.xlsx` untracked (ignored) — no action.
