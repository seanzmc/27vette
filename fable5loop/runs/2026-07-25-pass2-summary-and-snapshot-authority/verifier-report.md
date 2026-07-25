# Independent verifier report — Pass 2 receipt A

Run in a separate context with no access to the maker's reasoning, instructed to refute rather than
confirm and to default to FAIL on anything it could not reproduce itself.

## Verdict: PASS

with one rubric overstatement and four defects the maker had not recorded. All five were accepted
and addressed; see "Disposition" below.

## Criteria

Checked against `fable5loop/runs/2026-07-25-pass2-summary-and-snapshot-authority/outcome.md`.

| # | Criterion | Verdict |
|---|---|---|
| 1 | RED first | PASS — RED reproduced at `ed3692a` |
| 2 | Summary derived from the validated runtime contract | PASS |
| 3 | Normal generation never calls `inspect_model_sources()` | PASS |
| 4 | Workbook opens per non-Stingray model drop | PASS — 4 → 2 |
| 5 | One frozen snapshot; handles close deterministically | FAIL as originally worded / PASS as restated — see D1 |
| 6 | `--emit-inspection` artifacts byte-identical | PASS — 30/30 |
| 7 | Six-model runtime contracts byte-identical | PASS — 44/44 |
| 8 | `validation.py` deleted, no importer left | PASS |
| 9 | Requirement 6 already satisfied | PASS — no change needed |
| 10 | No new test failure | PASS |
| 11 | No tracked artifact change | PASS |

## What the verifier reproduced independently

It did not trust any number in the receipt. It created `git worktree add --detach <tmp> ed3692a`
and regenerated both sides from scratch.

| Claim | Method | Outcome |
|---|---|---|
| Byte identity across six models | 6 models × {normal, `--emit-inspection`} × {`ed3692a`, working tree} into four isolated `--output-root`s | normal: 14 compared, 0 differ. review: 44 compared, 0 differ. Raw unscrubbed `diff` shows exactly one changed line per file, always `generated_at` |
| Report no longer built | Patched `inspect_model_sources` to raise, at `ed3692a` and on the working tree | `ed3692a`: **called** for all five non-Stingray models. Working tree: **never called**. Under `--emit-inspection`: called for the five, correctly not for Stingray |
| Summary derives from the contract | Read each summary back against the artifact **on disk** for all six models | 0 mismatches on `counts`, `status`, `dataset_name`, `validation_errors`, `validation_warnings` |
| Workbook opens | Traced at the `openpyxl.load_workbook` call site | grand_sport/z06 4 → 2, stingray 2 → 2, `--emit-inspection` 4 → 3. Matches the receipt exactly |
| Handle safety | Injected `RuntimeError` at four points now inside the single handler | closed on all four; the restructure is **safer** than baseline, where ~120 lines ran outside any handler |
| `validation_row` had zero callers | `git grep -E '\bvalidation_row\b' ed3692a -- '*.py'` | empty — deletion justified |
| No new failures | Full Python suite + all 16 node gates, then reproduced every failure at `ed3692a` | identical counts, identical failing test names |
| Timing | 3 in-process runs each side | z06 0.61s → 0.48s |

## Refutation attempts that failed to refute

Recorded because a negative result is evidence:

- **No programmatic consumer of the stdout summary exists.** No `.mjs`, no `workbook-manager/`
  code, and no active doc (`docs/route-map.md`, `AGENTS.md`, `README.md`) parses or documents the
  removed keys. `editor_ops.py` only emits reminder *strings*. The `"workbook_backup": None`
  assertion at `stingray-generator-stability.test.mjs:362` targets
  `production.generate_production_artifacts()`, which is untouched.
- **No caller broke on the signature change.** `assemble_model_source`'s new parameter is
  keyword-only and both remaining callers pass `(config)` only. Nothing reads the removed
  `ModelSourceAssembly.draft`.
- **Dropping `inspect_model_sources` from the normal path lost no gate.** It contains zero `raise`
  and zero `assert`, and reads no sheet `build_contract_preview` does not also read.
- **openpyxl read-only re-iteration across one shared handle is safe here** — empirically settled
  by 44/44 byte-identical artifacts.

## Defects raised

**D1 — rubric criterion 5 was false as written.** "One loaded workbook snapshot per *assembly*"
overclaims: a non-Stingray assembly opens two handles, three under `--emit-inspection`. Worse, the
verifier found `inspect_model_sources()` and `build_contract_preview()` **never closed their
workbooks at all** — at `ed3692a` and on the working tree — confirmed by
`unclosed=['inspection.py:647']` on every non-Stingray run.

**D2 — receipt miscounted the artifact breakdown**: "3 derived-swap manifests" should be 6. The
total of 44 was correct.

**D3 — dead code left behind**: `_runtime_contract_json()` lost its only caller, and the
`REQUIRED_RESULT_KEYS` guard became statically unreachable — a miss on a receipt whose theme is
surface cleanup.

**D4 — two unrecorded semantic changes to the summary**: `warnings` disappeared from
normal-generation stdout, and `validation_warnings` counts contract rows rather than draft rows
(z06: 1 → 0), which is a value change rather than a relocation.

**D5 — pre-existing weakness worth flagging**: `validation_errors` in the summary is structurally
always `0`, because `assert_runtime_contract()` raises before it can be printed. STATE.md cited it
as evidence of a clean run; it is a tautology.

## Evidence inspected

- `git worktree add --detach <tmp> ed3692a` — a real second checkout, so both sides of every
  comparison were generated, not read from the receipt.
- `scripts/generate_form.py` across all six discoverable models into four isolated
  `--output-root`s (normal and `--emit-inspection`, each side).
- `scripts/corvette_form_generator/{model_generation,source_assembly,runtime_contract,inspection,production}.py`
  working-tree diff against `ed3692a`.
- `git grep` for every removed summary key across `*.py`, `*.mjs`, `workbook-manager/`,
  `docs/`, `AGENTS.md`, `README.md`.
- `git grep -E '\bvalidation_row\b' ed3692a -- '*.py'`.
- Traced `openpyxl.load_workbook` call sites and wrapped `wb.close` to detect leaks.
- Injected `RuntimeError` into `build_model_interiors`, `build_color_overrides`,
  `build_draft_rules`, `build_draft_price_rules`, and `rows_from_sheet`.

## Validation Output Inspected

`fable5loop/runs/2026-07-25-pass2-summary-and-snapshot-authority/validation-output.txt` was read and
re-executed rather than accepted. The full Python suite reproduced `6 failed, 460 passed, 2 skipped,
15 subtests passed` exactly, and all five code failures reproduce verbatim at `ed3692a`; the sixth
(`test_fable5_loop_contract`) failed only on the receipt being incomplete at the time of that run.
All 16 node gate pass/fail counts matched, and the three failures reproduce at `ed3692a` with
identical failing test names. Workbook SHA-256 `8858cff4…5b2166` in both trees. The receipt's own
disclosure that the two grand-sport tests rewrote tracked artifacts, and that `git diff` showed
`generated_at` as the only changed line, was confirmed and the restoration verified by SHA-256.

## Required Fixes Before Pass

1. Restate criterion 5 — one snapshot per **builder**, not per assembly — and record spec
   requirement 4 as still open.
2. Close the two leaking workbook handles in `inspect_model_sources()` and
   `build_contract_preview()`.
3. Correct "3 derived-swap manifests" to 6.
4. Delete `_runtime_contract_json()` and the unreachable `REQUIRED_RESULT_KEYS` guard.
5. Record the `warnings` removal and the `validation_warnings` value change in the receipt.

## Durable Lesson Candidates

- A count that a validator makes structurally impossible to be nonzero is not evidence of a clean
  run. Before citing a number as proof, check whether any code path could have produced a different
  one.
- When a receipt collapses two output shapes into one, enumerate the dropped keys explicitly and
  say which are relocations and which are value changes. "Derived from X instead of Y" hides both.
- Re-indenting a body under a new `try/finally` is worth auditing in both directions: it can fix
  leaks the receipt never claimed, and it can overclaim scope the change did not reach.

## File Edit Statement

The verifier edited no tracked file. All generation ran under isolated `--output-root`s in the
session scratchpad. The `git worktree` was removed and artifacts dirtied by the node gates were
restored with `git checkout --`, confirmed by SHA-256. The maker's stash was untouched.

## Disposition

| Defect | Action |
|---|---|
| D1 | Both leaking builders wrapped in `try/finally`. Criterion 5 restated as **per builder**, and spec requirement 4 recorded as still open. Two new tests: one snapshot per builder, and close-on-injected-`RuntimeError` for all three builders |
| D2 | Corrected in `validation-output.txt` |
| D3 | `_runtime_contract_json()` deleted; the unreachable guard removed and `REQUIRED_RESULT_KEYS` asserted in `tests/test_model_generation_route.py` instead |
| D4 | Both changes written into `outcome.md` under "Summary shape change, stated exactly" |
| D5 | Recorded in `outcome.md`; the STATE.md claim reworded |

Every gate was re-run after these corrections: Pass 2 gate `1 failed, 60 passed` (same single
pre-existing failure, up from 55 passing), 44/44 artifacts still byte-identical, node gates
unchanged, tracked surface clean.
