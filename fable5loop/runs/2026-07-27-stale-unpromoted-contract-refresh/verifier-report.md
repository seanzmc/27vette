# Independent verifier report — 2026-07-27-stale-unpromoted-contract-refresh

Separate context. Saw the rubric, the diff, and the claimed evidence; not the
maker's reasoning. Instructed to falsify.

## Verdict

**PASS.** No blocking findings. Every strong claim that was tested held. Four
documentation defects in the receipt, all since fixed.

## Criteria

| ID | Result | Proof |
|---|---|---|
| C1 every written value traces to the workbook | PASS | Independent regeneration into a temp root: exactly one differing JSON path per model, all `/dataset/generated_at`. Plus 13 field-level spot-checks against workbook cells. |
| C2 D4 satisfied on disk | PASS | EFR `selectable` on disk: zr1 `['False']`, zr1x `['False']`; workbook `zr1_options` / `zr1x_options` row 52 both author `selectable=False`. No workbook write needed. |
| C3 D1–D3 preserved | PASS | GSX J57 9000→0 (workbook row 125 `price=0`); FED 0→500 (row 129 `price=500`); NGA/T0E False→True (rows 51/123 `selectable=True`). |
| C4 blocker cleared | PASS | `verify_workbook_candidate.py --skip-harness` → exit 0, `unexpected_drift: []`, all six `unchanged`, `boundaryViolations []`. |
| C5 boundaries hold | PASS | Workbook SHA `d11674e3…60bfd`; `git diff HEAD -- form-app/data.js` empty. |
| C6 tests investigated at the workbook | PASS | Both expectations traced to workbook cells; drift tests survive a mutation test. |
| C7 gate parity | PASS (node) / unverified (full Python suite) | All 17 node tallies reproduce exactly. |
| D1 J57 $0 | PASS | `grand_sport_x_options` row 125 `price=0`; no price rule supplies 9000. |
| D2 FED $500 | PASS | row 129 `price=500`. |
| D3 selectable flips | PASS | GSX NGA×6 T0E×6; zr1 AH2/AQ9/EYT/NGA/SOJ ×4; zr1x NGA×4 — all `selectable=True` in the workbook. |
| D4 EFR not selectable on ZR1/ZR1X | PASS | EFR True→False ×4 on both. GSX EFR stays True because row 54 authors True; the exception correctly did not extend there. |

## Findings

**1 — confirmed, C1 is mechanically airtight.** Path-by-path comparison of an
independent regeneration against the committed files:

```
grand-sport-x num diff paths: 1  ('/dataset/generated_at', ...)
zr1           num diff paths: 1  ('/dataset/generated_at', ...)
zr1x          num diff paths: 1  ('/dataset/generated_at', ...)
```

The three untracked swap manifests are byte-identical to regenerated output
(`raw_equal=True`), all `emitted_count: 0`. This forecloses the hand-edited
-artifact failure mode for every field in the diff at once.

**2 — confirmed, C6(1).** Workbook `grand_sport_x_options` `sec_roof_001` by
`display_order` is 10 CF7, 20 C2Z, 30 CC3, 40 CM9, 50 CF8, 60 D84, 70 D86. The
new expectation equals that exactly; the old expectation equals the HEAD
artifact's order exactly, re-derived from `git show HEAD:`. "Pinning the stale
artifact" is literally true.

**3 — confirmed, C6(2).** `zr1_options` row 116 puts CFC in `sec_roof_001`;
`zr1x_options` row 165 puts the same option in `sec_stan_001`. The asymmetry is
workbook-authored, and flagging it as out of scope is correct.

**4 — confirmed, the re-pointed drift tests are load-bearing.** Mutation test with
`semantic_drift` stubbed to return `[]`: intact run gives
`unexpected_drift: ["zr1"]` with the other five clean and drift collections
`['choices','standardEquipment']`; stubbed, the assertion cannot hold.
`tests/test_verify_workbook_candidate.py` → 15 passed.

**5 — confirmed, C5 and "no customer-visible surface moved."** Not assumed —
`model_registry_promotion` shows `promoted_to_runtime=False` for all three, and
loading `form-app/data.js` in node yields `models: [stingray, grandSport, z06]`.
`grep -rn "form-output" form-app/` returns nothing, so the app has no other path
to these contracts.

**6 — confirmed, C7 node gates.** All 17 tallies identical to the receipt,
including `unpublished-runtime-contracts 2/0`. Churn reproduced and restored:
`generated_at` only, 4 changed lines, and the three target contracts untouched.

**7 — minor, fixed.** The "WRITTEN ARTIFACTS" table's last column was labeled
`selectable-true flips` but listed RPOs currently `selectable=True`. AH2/AQ9/EYT
were already True on GSX at HEAD and T0E was already True on zr1x. The states
reported were accurate; the header was wrong, and it contradicted the correct
flip table three sections earlier.

**8 — minor, fixed.** The diff summary omitted the second-largest bucket: 1242
GSX choice-level `display_order` changes, plus `standard_equipment_group_type`
(0/36/36) and `auto_added_summary_required` (6/0/0). Spot-checked and all
workbook-authored (UQH 220→20 row 7, DSZ 280→70 row 203, K7A →30 row 4, zr1x CJ2
10→11 row 130). Incompleteness in the summary, not an unsupported change — C1
covers every field regardless.

**9 — minor, fixed.** "An inactive ingest-era override" is imprecise: the row was
deleted from `zr1x_price_rules`, which has 11 rows and no `active` column at all.

**10 — note, fixed.** "Nothing is generator-side" reads stronger than intended.
The largest bucket, `display_behavior` omission, *is* generator serialization
behavior — just not a new adjustment made this run.

**11 — confirmed, supporting claims spot-checked.** `sec_perf_ground_001` =
"Ground Effects" (`section_master` row 34) with `zr1_options` row 113 CFV
pointing at it; `sec_2lte_001` = "2LT Equipment" (row 41); GSX UQH
"Audio system feature" → "Bose Performance Series Audio System" (row 7); WUB
`sec_stan_001`→`sec_exha_001` (row 52); ERI `sec_perf_support_001`→`sec_perf_001`
(row 121).

**Process note.** The lane's byte-identity boundary check is not safe to run
concurrently with the node gates: a parallel gate run rewriting
`grand-sport-runtime-contract.json` produced three spurious `boundaryViolations`
failures. Serial runs pass.

## Could not verify

1. The full Python suite tally (546 passed) — bounded run. The changed file was
   run (15 passed) and the +4 arithmetic is consistent with the diff.
2. The `browser_harness` stage — skipped via `--skip-harness`; 9 of 10 stages run.
3. The pre-existing status of the three node failures — argued from their content
   (none read the target contracts, none of their inputs changed) rather than
   measured, since measuring would have required reverting tracked files.
4. Whether D1/D2 are correct as *product* decisions — out of scope by the
   rubric's own boundary. Only workbook authorship was verified.

## Evidence inspected

The rubric and validation output; `git status`/`git diff`; `git show HEAD:` for
the three contracts; `stingray_master.xlsx` sheets `grand_sport_x_options`,
`zr1_options`, `zr1x_options`, `zr1x_price_rules`, `section_master`,
`model_registry_promotion`; `form-app/data.js` loaded in node; both changed test
files; independent regeneration and a mutation test in temporary directories.

## Validation Output Inspected

`fable5loop/runs/2026-07-27-stale-unpromoted-contract-refresh/validation-output.txt`,
re-executed rather than read: the regeneration, the candidate lane, all 17 node
gates, the changed test file, and every workbook citation.

## Required Fixes Before Pass

None blocking. Four documentation corrections (findings 7–10), all applied.

## Durable Lesson Candidates

1. When a test that asserts on generated output fails after a legitimate
   regeneration, read the workbook cell that owns the value before touching the
   expectation. Two expectations here looked like ordering noise; one was a
   stale-artifact pin and the other was a genuine new workbook row.
2. A byte-identity boundary check cannot run concurrently with gates that rewrite
   tracked artifacts. Serialize them, or the boundary check reports the other
   run's writes as its own violation.

## File Edit Statement

The verifier modified no tracked file. It restored `generated_at`-only churn from
its own node gate run with `git checkout --` on `form-app/data.js`,
`grand-sport-runtime-contract.json`, and `z06-runtime-contract.json` only; the
three target contracts' SHAs were identical before and after. Tree state on exit
is byte-identical to the maker's.
