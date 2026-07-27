# Independent verifier report — 2026-07-27-pass4a-executable-route-proof

Separate context. Saw the rubric, the diff, the base commit, and the repo; not
the maker's reasoning. Instructed to weigh the recorded process deviation (the
rubric was written after the edits) and to say whether any criterion looked
shaped to the result. One cycle.

## Verdict

**PASS with should-fix.** The rewrite is real: the source-string assertions are
gone, the route claim is per-model and genuinely breakable, the contract
expectation is genuinely hand-written, and four of seven injected weakenings
were caught with precise failures. Two substantive holes — an incomplete strip
expectation the whole Python suite was blind to, and three guarantees from the
deleted assertions that were neither re-established nor declared dead. All
fixed; post-fix mutation results in `validation-output.txt`.

On the deviation: the verifier judged the rubric **not** shaped to the result —
C5's second clause and C2 both failed the delivered work, and C4's "state what
input defeats each claim" was unanswered.

## Criteria

| # | Verdict | Evidence the verifier produced |
|---|---|---|
| C1 | PASS | Grepped both files for `read_text`/`getsource`/`glob`. One hit, and it reads the *generated artifact* to drive assertions, which the rubric permits. No character-level assertion survives. |
| C2 | **PARTIAL → fixed** | Enumerated all 27 deleted assertions individually and located each guarantee. Three were gone, proven by mutations f, g, i surviving green. See findings 2 and 3. |
| C3 | PASS (note) | Confirmed 6 params collected from discovery at collection time and that discovery has no write side effects. Silent-shrink risk noted and located to its Pass 2 owner. |
| C4 | PASS | Gave `zr1x` a private assembly path; both parametrized route tests failed naming the model. |
| C5 | **FAIL on the second clause → fixed** | First clause holds — no expected value comes from the code under test. Second clause failed: two of six provenance strip fields were never exercised. See finding 1. |
| C6 | PASS | All seven matrix items present and green, 11 subtests. |
| C7 | PASS with should-fix | 4 of 7 injected weakenings caught; the three misses are findings 1–3. |
| C8 | PASS with should-fix | Both "already delivered" claims verified true by reading the files. One omission, finding 5. |
| C9 | **FAIL (receipt) → fixed** | Both files 29 passed / 11 subtests; README metadata gate set 153 passed; full suite 567 passed / 2 skipped; `form-output`/`form-app` clean; workbook unmodified. But the loop contract test failed on this run's own incomplete receipt folder. Finding 6. |

## Findings and resolutions

**1. blocker for C5 — two strip fields never exercised, and the whole suite was blind to them.**
`draft_payload()` covered `draftMetadata`, `_derivationManifest`, all three
draft-only choice fields, both runtime trim classes, and 4 of 6
`DRAFT_ONLY_PROVENANCE_FIELDS` — missing `copy_from_model_key` and
`raw_source_sheets`. Deleting both names from that tuple left `567 passed, 2
skipped`: the entire Python suite. `copy_from_model_key` is covered elsewhere,
but against `schema_validation.py`'s own duplicate list, a different module.
**Resolved:** both added to the draft payload and deliberately absent from the
expectation. Re-measured — the same deletion now fails
`test_builder_output_matches_the_expected_contract_exactly`.

**2. should-fix — the retired-symbol guard was not replaced, and the CLI test was single-model.**
The CLI test drove only `--model z06`, so a legacy branch keyed to any other
model passed it. Proven: `generate_form.py` regrowing a stingray-only
`PRODUCTION_MODEL_KEYS` branch left both rewritten files green.
**Resolved:** the CLI test is parametrized over `discovered_model_keys()` —
generation is faked, so the cost is argument parsing. The same mutation now
fails `[stingray]`.

**3. should-fix — two guarantees the rubric called "the dangerous ones" quietly vanished.**
Adding a second `build_model_runtime_contract` caller to `production.py`, and
re-adding `from ...registry_promotion import live_contract_data` to it, were
both caught by nothing. The identity check that replaced the reverse-dependency
grep is defeated by exactly that mutation: a re-export leaves
`registry_promotion.live_contract_data is runtime_contract.live_contract_data`
true. **Resolved:** both restored as AST checks — an `ast.Call` walk for the
caller set and an `ast.ImportFrom` walk for the import edge. Structural, not
textual, so C1 still holds. Applying both mutations together now fails both
tests. The AST check also exposed that the retired text version was passing for
the wrong reason: it counted the defining module as a caller because a substring
search matches the `def` line and the docstring. The real caller set is one
module.

**4. note — C3's discovery-driven set can shrink silently within this run's gate set.**
Deactivating a model removes a parametrization with no failure here. It is
caught by `test_all_model_runtime_generation.py::test_named_models_are_active_and_green`,
whose named `EXPECTED_MODEL_KEYS` exists for precisely that reason. A second
named set here would duplicate that owner. The real gap is that neither file
appears in the README gate matrix — **carried forward**, as Stage A owns that
rewrite; the gate set recorded in `validation-output.txt` includes the six-model
gate explicitly.

**5. note — the "already delivered" claim omitted one thing.**
Both claims verified true. But the spec bullet forbade "a permanent six-model
literal," and one now exists at `tests/test_all_model_runtime_generation.py:44`,
added deliberately in Pass 2 on a verifier finding. Defensible, but it should be
stated. **Resolved:** stated in `validation-output.txt` under C8.

**6. should-fix — C9 was red on the repo's own loop gate.**
`test_repository_fable5_loop_contract_passes` failed: the run directory held
only `outcome.md`. **Resolved:** receipt completed; loop validator green.

**7. note — modest duplication, no flakiness.**
The per-model route test generates all six models in-process (~5s of 16s) while
`test_all_model_runtime_generation.py` already generates all six by subprocess.
The unique value here is the call-count proof, which one model would establish;
the break-one genuinely needs all six and is nearly free. Accepted at 18s.
Nothing flaky across four green runs.

## Evidence inspected

`git show ed75b54:` for both files; `git diff`; the spec's Pass 4 Stage A
bullets; `scripts/corvette_form_generator/runtime_contract.py` strip-field
tuples; `model_configs.py` discovery; `tests/test_all_model_runtime_generation.py`;
`tests/test_generate_form_model_discovery_cli.py`;
`tests/test_registry_promotion_metadata.py`; `tests/test_schema_validation_metadata.py`;
README/AGENTS/route-map for gate-matrix membership; seven injected mutations of
four production modules.

## Validation Output Inspected

`fable5loop/runs/2026-07-27-pass4a-executable-route-proof/validation-output.txt`
— the mutation matrix was re-executed rather than read, and the full Python
suite was run once against the pre-fix state to establish what nothing caught.

## Required Fixes Before Pass

1. Exercise `copy_from_model_key` and `raw_source_sheets` in the draft payload.
2. Parametrize the CLI delegation test over every discovered model.
3. Re-establish the one-caller and reverse-dependency guarantees executably, or
   declare them dead with reasoning.
4. State the six-model-literal deviation rather than leaving it implied.
5. Complete the receipt so the loop gate passes.

All applied; post-fix evidence in `validation-output.txt`.

## Durable Lesson Candidates

1. A text search for a function name matches its own `def` line and its
   docstring, so a "who calls this" guard written as a grep counts the defining
   module as a caller and is green for the wrong reason. Walk the AST for
   `ast.Call`; the expected set usually shrinks by one, and that difference is
   the bug the grep was hiding.
2. Function identity cannot police an import direction. Re-exporting a symbol
   leaves `a.f is b.f` true, so an identity assertion passes over exactly the
   dependency edge it was meant to forbid. Assert the edge — `ast.ImportFrom` —
   not the object.
3. A CLI test that drives one model cannot see a per-model legacy branch, which
   is the historical shape of every route split this repo has retired.
   Parametrize over discovery; when the callee is patched out, extra models cost
   argument parsing.
4. When replacing a text-grep guard with a behavioral one, the replacement
   usually proves the *forward* direction (this path reaches that function) and
   silently drops the *negative* one (nothing else calls it). Patching one path
   says nothing about a second path. Name both halves before deleting the grep.

## File Edit Statement

The verifier edited `scripts/generate_form.py`,
`scripts/corvette_form_generator/{runtime_contract,model_generation,production}.py`
for seven mutations and restored every one with `git checkout --`, verified by
SHA-256 against a pre-verification baseline. It wrote no file into the repo. Its
only artifact was a checksum file in the session scratchpad. Final state at
hand-back: the maker's two modified test files plus the untracked run directory;
workbook `d11674e3…60bfd` unmodified; `form-output/` and `form-app/` clean.
