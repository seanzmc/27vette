# Z06 display_order Retype Spec — S-1/S-2 Typing Normalization

Date: 2026-06-12
Parent: consistency review 2026-06-11 recommendation 1 (S-1, S-2); editor Phase 3 lint evidence (`display_order_type`, 318 errors). Phase 3 shipped and green.
Status: draft for approval, no implementation yet.

---

## 1. Diagnosis

**Root cause.** Z06 ingest-era rows store `display_order` as text (`'50'`, `'72'`, …) while every other live sheet stores integers. Verified live counts (2026-06-12, via `editor_lints` and direct extract):

| Sheet | string-typed `display_order` cells | Review finding |
|---|---|---|
| `z06_options` | 245 of 249 rows | S-1 (Blocker class) |
| `z06_rule_group_members` | 57 of 176 rows | S-1 class (surfaced by Phase 3 lint, not named in review) |
| `z06_exclusive_members` | 16 of 41 rows (rows 2–17) | S-2 |
| all other live option/member sheets | 0 | — |

All 318 values are clean digit strings (verified: no non-numeric, no floats, no stray whitespace). The fix is type-only — `'50'` → `50` — no value, row, or ordering changes. The generator already coerces, so **no contract or runtime behavior changes**; this removes the data shape that crashes naive numeric sorts and made the consistency audit fragile.

**Risk level: low-medium** (any workbook write is medium by policy; the change itself is mechanical and value-preserving).

**Change class:** data-only workbook pass + test extension (one node test, one Python test updated).

**Mechanism.** The Phase 2 editor op pipeline, not a new script: generate a 318-op update batch and apply via `scripts/apply_workbook_ops.py ops.json --write`. `coerce_value` types `display_order` as int for all three families; every apply runs batch validation, dry-run package+schema validation on a temp copy, `save_workbook_safely()` (lock/mtime checks, backup, atomic replace), Excel-table ref maintenance, and a committed edit-log line. No new module, no hand openpyxl script.

**Known warnings to confirm.** The batch validator flags pre-existing display-order collisions on updated rows (D-1/D-2 class: RWJ/WKS @72, FE6/DRG @10, FE7/TR7 @20, 329/G0K @120, U80/WUB @20, plus member-sheet duplicates if any). These collisions exist today and are unchanged by retyping; they will be explicitly confirmed via `--confirm-warnings`, not resolved here (resolving D-1 is review rec 2, a separate behavior-affecting pass).

## 2. Exact Files

| File | Action |
|---|---|
| `stingray_master.xlsx` | 318 cells retyped across `z06_options`, `z06_rule_group_members`, `z06_exclusive_members` — values unchanged |
| `form-output/workbook-edit-log.jsonl` | one apply-log line (committed by design) |
| `tests/workbook-schema-standardization.test.mjs` | extend "canonical raw Excel types": numeric `display_order` on all three live `*_options` sheets and all six live member sheets (review rec 1) |
| `tests/test_editor_lints.py` | S-1/S-2 real-workbook expectations flip from 245/16 string-typed rows to zero `display_order_type` errors workbook-wide |
| ops.json | transient, not committed (per "do not stage temporary output") |

## 3. Constraints (repeated back)

- Values, row order, and all other columns untouched; type-only change. No fixes to collisions (D-1…D-3), copy, or group membership in this pass.
- Write goes through `save_workbook_safely()` via the existing apply pipeline; Excel must be closed (no `~$stingray_master.xlsx` — verified absent).
- After the write, the saved workbook is re-inspected on disk before claiming success.
- No new dependencies, no new helper modules, no generator/runtime/form-app changes.
- ZR1/ZR1X scaffold sheets untouched (out of review scope).

## 4. Risks and Non-Goals

- *Mid-write interruption*: `save_workbook_safely` validates a temp package then atomically replaces; a backup is taken first. Residual risk acceptable.
- *Hidden type dependence*: any consumer relying on string `display_order` would shift — none exists (generator coerces; visual-copy/schema tests don't assert string typing on these columns; verified by running the full affected suites below).
- Non-goals: D-1/D-2/D-3 collision dedup (rec 2/4), boolean-as-text retype (S-10 class, 153 info lints), `_002` option-id re-keying (rec 10), copy convergence (rec 7).

## 5. Validation Plan

1. Pre-apply: `apply_workbook_ops.py ops.json` (validate + dry-run only) — expect 0 errors, only known collision warnings.
2. Apply with `--write --confirm-warnings <ids>`; verify on disk: re-extract, expect 0 string-typed `display_order` cells in the three sheets and identical values/ordering (full before/after value comparison).
3. `validate_workbook_schema.py stingray_master.xlsx` → 0/0.
4. Phase 3 lints: `display_order_type` errors 318 → 0; collision warnings unchanged at 16; no new findings.
5. Z06 gates: `generate_form.py --model z06`; `compare-generated-contracts.mjs` on before/after `z06-runtime-contract.json` → no contract change; `node --test tests/z06-contract-preview.test.mjs tests/z06-form-data-draft.test.mjs`.
6. Extended node suite: `workbook-schema-standardization.test.mjs` (with new display_order assertions), `workbook-visual-copy-standardization.test.mjs`.
7. Python editor suite (`test_editor_*.py`, including updated `test_editor_lints.py`).

## 6. Approval Questions

1. Approve scope: all 318 string cells (S-1 + S-2 **plus** the 57 `z06_rule_group_members` cells the lint found — same defect class, same mechanical fix)?
2. Approve mechanism: editor op pipeline via `apply_workbook_ops.py` (recommended) — collisions confirmed explicitly, apply logged?
