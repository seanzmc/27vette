# Independent verifier report — 2026-07-27-pass3-promotion-type-closure

Separate context. Saw the rubric, the diff, and the claimed evidence; not the
maker's reasoning. Instructed to falsify. This run is a deletion, so the brief
emphasised finding a removed symbol with a live caller, or a guarantee dropped
along with a test.

## Verdict

**PASS with should-fix.** No removed symbol has a live caller and no passing
guarantee vanished. Six findings, all receipt-accuracy or coverage items — except
finding 1, a real untested behavior change the receipt claimed was untestable.
All fixed; post-fix evidence in `validation-output.txt`.

## Criteria

| # | Result | Basis |
|---|---|---|
| C1 closure exhaustive | PASS | Redone independently at HEAD including f-string and dynamic references |
| C2 external/operator answered | PASS | form-app, editor server, editor JS, workbook cells, fixtures all clean |
| C3 one vocabulary authority | PASS | A single tuple edit broke all three modules in a shadow build |
| C4 blank default retargeted | PASS | Falsifiable in the acceptance path (2 failures); cosmetic at the schema layer (F2) |
| C5 artifact_path unconditional | PASS w/ caveat | Escape gone in both files; **F1** — the admission was only half true |
| C6 dead functions gone | PASS | All four absent; `artifact_path_for_promotion` has 2 callers and no branch |
| C7 guarantees not deleted | PASS (strong) | All 33 HEAD assertions accounted for; 18/18 byte-identical in the retargeted tests |
| C8 retired type rejected | PASS w/ gap | Rejected at both layers; **F5** — messages did not name the allowed set |
| C9 publication unchanged | PASS | Byte-identical modulo `generated_at`; lane ok; schema 0 issues |
| X1 assertions name their breaker | partial | One docstring falsified by probe (**F1b**) |
| X2 negative proofs not implementation-shaped | PASS | Shadow build reproduced exactly: 6 failed / 65 passed |
| X3 gate parity | PASS | 279 pass / 3 fail, identical to the receipt; the three failures confirmed unrelated |
| X5 honest receipt | incomplete | **F6** — no `run.json`/report yet; Pass 4 handoff unrecorded |

## Findings

**F1 — should-fix, moderate. The C5 non-falsifiability admission was half wrong.**
The receipt said C5 applies "in both files" and then that it is not independently
falsifiable, citing `registry_promotion.py:120`. That reasoning holds only there.
`schema_validation.py`'s membership check does not short-circuit — it `add_issue`s
and continues — so `artifact_type` can still be `current_generation` at the path
check, and the exemption was behaviorally live:

```
working tree:  ['registry_promotion_missing_artifact_path',
                'registry_promotion_unknown_artifact_type']
exemption restored at schema_validation.py:866:
               ['registry_promotion_unknown_artifact_type']   <- silently lost
```

Both states left all 67 tests green. A test can be written; it should be.

**F1b — should-fix, minor.** `test_every_promoted_row_requires_an_artifact_path`
says it "breaks if the blank-path escape hatch ever comes back". Restoring that
exact escape hatch leaves it passing (67 passed). The receipt admits this under
C5; the test file asserts the opposite.

**F2 — should-fix, minor.** Reverting `schema_validation.py`'s blank default to
`"draft_artifact"` is undetected (67 passed). Reading lines 798-875, the defaulted
value is consumed only inside another issue's payload — a blank cell is already an
unconditional `registry_promotion_blank_artifact_type` error. C4 is real in the
acceptance path and cosmetic at the schema layer; the receipt stated it without
that distinction, the same caveat class it correctly volunteered for C5.

**F3 — should-fix, minor.** `registry_promotion.py:80-82` still described the
"legacy hardcoded registry fallback" that requirement 8 deleted.

**F4 — nit.** Line count claimed 315 → 251; `git show HEAD:… | wc -l` is 312.

**F5 — should-fix, minor.** C8 requires rejection "with a message naming the
allowed set". Neither message did; only the blank-value path named it.

**F6 — should-fix, X5.** The run directory held only `outcome.md` and
`validation-output.txt`, which is why the loop-contract test fails. The receipt
never said whether requirements 7+8 complete Pass 3, and omitted that this run
lifts the block spec line 937 records on deleting
`form-output/stingray-form-data.json`.

**F7 — note, no action.** The docs scan excluded "the specs themselves" as a
category, which skipped
`docs/superpowers/specs/2026-07-22-reliable-workbook-database-workflow.md:407`.
Read it: it lists both retired types among shapes that must be "a blocking
preflight error, never a silently excluded row" — consistent with the narrowing,
so requirement 7's stop condition is correctly not triggered. Should be named
rather than excluded by category.

## Confirmed under adversarial testing

- **Closure.** Every HEAD consumer of the six symbols is removed or retargeted;
  every surviving mention in the working tree is a comment, docstring, or a
  negative-proof literal. Runtime check: all four functions absent from the module.
- **Constructed and dynamic references.** The f-string route is gone from
  `artifact_path_for_promotion`; a `getattr`/`importlib`/`globals()[` sweep found
  one unrelated hit; workbook cells across all sheets contain no retired value
  (`Counter({'runtime_contract': 6})`, blank `artifact_path` count 0).
- **The editor can no longer offer a retired value**, proven end to end:
  `EDITOR_SHEET_META -> workbook_editor_server.py:92 -> editor.js:133-137`, no
  hardcoded list in the chain, offered enum `('runtime_contract',)`.
- **`draft_artifacts` / `draft_artifact_prefix` were not conflated** with the
  promotion type; the five generation-side hits are untouched and the
  generation/inspection tests give 72 passed, 8 subtests.
- **C7 assertion audit.** 33 assertions enumerated by AST at HEAD. The two
  retargeted tests are byte-identical in all 18 assertion expressions
  (`ONLY IN HEAD: none / ONLY IN WORKTREE: none`). The only deleted assertion is
  `assertIsNone(build_registry_from_promotions(...))`, whose guarantee is now
  stronger (the surviving builder raises). The retargeted draft-fields test is
  *more* meaningful: at HEAD the raise could have come from either row; now it
  provably fails on grand-sport's actual draft artifact.
- **X2 shadow build reproduced exactly**: widening the vocabulary gives
  `6 failed, 65 passed`, the same two named tests plus four subtests.
  `artifact_path_for_promotion` rewired to the legacy f-string: 4 failed.
- **C9.** Registry byte-identical modulo `generated_at` (`lens 6310574 6310574`);
  candidate lane exit 0 with `boundaryViolations: []`; schema gate 0 issues.
- **Gate parity.** All 17 node gates line-for-line identical to the receipt.

## Could not verify

1. The full Python suite (bounded run). The single claimed failure was reproduced
   in isolation with its exact stated cause, and the arithmetic checks out.
2. The candidate lane's browser harness stage (`--skip-harness`). Stage 8 ran.
3. The previous run's baselines, having no independent pre-run snapshot.

## Evidence inspected

`git show HEAD:` for all six changed files and the HEAD test module; `git grep` at
HEAD and in the working tree for six symbols plus dynamic-dispatch patterns;
`stingray_master.xlsx` all sheets; `form-app/data.js`; `workbook_editor_server.py`
and `visualizer/workbook-editor/editor.js`; six shadow builds; an AST assertion
enumerator.

## Validation Output Inspected

`fable5loop/runs/2026-07-27-pass3-promotion-type-closure/validation-output.txt`,
re-executed rather than read: the closure, the shadow builds, the negative proofs,
the registry parity, the candidate lane, the schema gate, and all 17 node gates.

## Required Fixes Before Pass

1. Test the schema-layer `artifact_path` exemption, or narrow the C5 admission to
   name only `registry_promotion.py`.
2. Correct the docstring that claims a breaker it does not catch.
3. Add the C4 schema-layer caveat.
4. Remove the stale "legacy hardcoded registry fallback" docstring.
5. Correct the line count.
6. Make both rejection messages name the allowed set.
7. Answer X5: say whether Pass 3 is complete and record the compat-JSON unblock.

All applied; post-fix evidence in `validation-output.txt`.

## Durable Lesson Candidates

1. "This guard is unreachable, so it cannot be tested" is a per-call-site claim,
   not a per-concept one. The same exemption was dead in the module that *raises*
   on the dominating check and live in the module that *accumulates* issues and
   continues. Trace each site's control flow before writing the admission — an
   untestability claim is itself a claim requiring evidence.
2. A rubric criterion that names a message's content ("rejects with a message
   naming the allowed set") is not satisfied by rejecting. Re-read criteria for
   the specific artifact they demand before marking them met.

## File Edit Statement

The verifier mutated tracked files during six shadow builds and restored every
one, verified by SHA-256 comparison against pre-verification baselines. Its own
node gate run rewrote `form-output/runtime/{grand-sport,z06}-runtime-contract.json`
by `generated_at`; restored with `git checkout --`. Final state: exactly the
maker's six files plus the untracked run directory, all bit-identical to their
pre-verification hashes; `stingray_master.xlsx` `d11674e3…`, `form-app/data.js`
`1d90db74…`.
