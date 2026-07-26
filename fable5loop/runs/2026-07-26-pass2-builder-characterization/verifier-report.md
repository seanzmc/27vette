# Independent Verifier Report — Pass 2 receipt C: builder convergence

Run in a separate context with no access to the maker's reasoning, instructed to refute rather than
confirm and to default to FAIL on anything it could not reproduce itself.

## Verdict

**FAIL** — on completeness, not on code. Its summary: *"The engineering is sound — every approved
change is exactly what was approved, and I could not find a single behavior-changing defect. It
fails on the one thing this receipt exists to prove."*

Because merging two genuinely different builders cannot be proved by byte-identity, this receipt's
whole burden was stage-2 criterion 3: every published difference matches the stage-1 ledger,
nothing unexplained. That claim was false — eight deltas were unlisted, and one deleted test
assertion guarded a change that then happened.

All findings are addressed in `outcome.md`. No code was rolled back.

## Criteria

| # | Claim | Verdict |
|---|---|---|
| 1 | Published delta exactly as claimed | **FAIL** — 8 undisclosed deltas, all inert |
| 2 | 31 dropped rules inert | PASS — proved more strongly than the receipt did |
| 3 | 18 sections / 8 colorOverrides inert | PASS |
| 4 | `standard_equipment_group_type` loss inert | PASS |
| 5 | No validation check silently dropped | PASS — receipt understates itself |
| 6 | Tests requirement-derived, not weakened | **PARTIAL FAIL** — one assertion deleted, not replaced |
| 7 | 7 workbook opens, deterministic close | PASS — 7 opens, 7 closes; exception path verified |
| 8 | `production.py` clean, no stale callers | PASS |
| 9 | No new test failure vs HEAD | PASS — receipt's baseline number wrong, conclusion holds |
| 10 | No tracked workbook/artifact/registry/`form-app/` change | PASS |
| — | 129 `orphan_ref` are valid interior ids | PASS |
| — | z06's 22 leaks are workbook-authored | PASS |

## The failure

Generated all six models from a `git worktree` at `993d920` and from the working tree into isolated
`--output-root`s, diffed every collection on stable semantic identity. It independently confirmed
`colorOverrides.override_id` is positional — it renumbers densely after the 8 drops, which would have
manufactured ~8 phantom diffs — and keyed on the semantic tuple instead.

The three approved deltas reproduce **exactly**, as does the stage-1 endpoint table (10 / 17 / 4).

Eight deltas were not listed; the full table is in `outcome.md`. The worst is
`rules.source_selection_mode`, which stage 1 explicitly flagged as an "open item for stage 2" and
which then never reached the stage-2 delta table.

Two receipt statements were outright false, both now corrected:

1. Stage 1 axis 4 claimed the variant provenance fields are *"all stripped from the runtime contract
   by `live_contract_data()`."* They are not — `DRAFT_ONLY_LIVE_CONTRACT_FIELDS` does not contain
   them and they ship in all six contracts.
2. *"Zero rows added or removed anywhere except Stingray's three approved collections."* True of
   rows; fields were added to 130 interiors, 30 sections and 6 variants.

## The deleted assertion

The retired test contained `assert all("requires_z25" not in row for row in runtime["interiors"])`.
It **passed** at baseline — `production.py` popped the field with the comment *"Keep the existing
Stingray runtime contract byte-for-byte compatible."* The new builder emits it on all 130 rows, so
the assertion would now fail. It was deleted with the rest of the file and not replaced.

The verifier declined to waive this because it is the same class of defect the two prior receipts
failed on: a guard removed alongside the thing it guarded.

## Where the verifier did better than the maker

Its inertness proof for the 31 dropped rules is stronger. The maker argued only that a source absent
from `choices` can never be selected. But `app.js:1116-1120` also disables a choice when it is the
**source** of a `requires` rule whose target is unselected, and `computeAutoAdded` (1059-1062)
auto-adds through an `includes` rule with a live source. A dropped `requires` rule with a resolvable,
active source would have **unblocked a previously-disabled option** — customer-visible.

It enumerated all 31 and found that class empty: all 8 `requires` and the single `includes` have
unresolvable sources; the 10 `excludes` with live sources all have unresolvable targets.

## Regression simulations, all caught

Against a scratch copy:

- stop filtering dangling rules (`rules.py:152`) → `31 rules reference absent entities`
- reintroduce a model fork → `test_one_builder_serves_every_model` fails
- revert `label_for` → 5 models fail the interior-id leak test, z06 correctly exempt — independently
  corroborating the "five models corrected, z06 exempt because its leaks are authored" claim

## Evidence inspected

`git worktree` at `993d920`; six models × two trees into isolated `--output-root`s; every collection
diffed on semantic identity; `form-app/app.js` for `requires_z25`, `source_active`,
`preview_included`, `source_section_name`, `source_selection_mode`, `section_ids`,
`runtimeRuleExceptions`, `source_sheet`, `standard_equipment_group_type`, `trimEquipmentRows` and
every caller; the retired `production.py` at HEAD diffed against the current generation lane for
guards, raises and error-severity rows; instrumented open/close counting with an injected
mid-assembly exception; full Python suite and all 16 node gates in both trees.

## Validation Output Inspected

`validation-output.txt` was re-executed rather than accepted. All 16 node gate counts matched
exactly. `active explicit excludes` confirmed failing at baseline; both grand-sport failures
identical at baseline. The `workbook-schema-standardization` 7/2 result reproduced with the receipt's
stated cause — the second failure appears only after an earlier gate regenerates artifacts while
`data.js` is unpublished. Baseline Python was **6 failed** at `993d920`, not the 5 recorded; after,
5 failed / 495 passed, so one pre-existing failure was fixed and none introduced.

## Required Fixes Before Pass

1. List the eight undisclosed deltas and correct the two false statements.
2. Correct the baseline test counts.
3. Re-add a `requires_z25` assertion, or record the field addition as an accepted change.

## Durable Lesson Candidates

- When a receipt cannot be proved by byte-identity, completeness of the delta list *is* the proof.
  Diff every field, not only every row, and carry every stage-1 "open item" into the stage-2 table
  or explicitly close it.
- Deleting a test file deletes assertions you were not thinking about. Enumerate what each removed
  assertion guarded and where it now lives, before removing it.
- "Stripped by X" is a claim about code you should read, not infer. Check the actual field list.

## File Edit Statement

The verifier edited no tracked file. All generation ran under isolated `--output-root`s. Artifacts
dirtied by the gates were restored with `git checkout` and the worktree removed.

## Disposition

| Finding | Action |
|---|---|
| 8 undisclosed deltas | Listed in `outcome.md` with `app.js` reference counts, plus the measurement showing all eight align Stingray with the other five models' shape |
| Two false statements | Corrected in place |
| Deleted `requires_z25` assertion | Field **accepted** — it aligns Stingray rather than diverging it. `test_every_model_ships_the_same_contract_shape` now pins the shared field set across all six models, which is a stronger guard than the Stingray-only absence assertion it replaces |
| Baseline count wrong | Corrected to 6 failed at `993d920` |
| Two checks better than recorded | Corrected: `missing_{key}_{price_rule_id}` is covered; `redundant_{rule_id}` payload suppression survives in `rules.py` |
