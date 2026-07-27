# Outcome rubric — Pass 4 Stage A, second slice: source-string tests → executable proof

**Process deviation, recorded rather than hidden:** this rubric was written after
the edits, not before them. The loop requires the rubric first. The edits were
made directly on Sean's "continue with the stage A chunk" instruction and the
spec's own wording for these two files; nothing here was reverse-engineered from
the result — the criteria below are the spec's requirements — but the ordering
was wrong and the verifier should weigh criteria accordingly.

Run: `2026-07-27-pass4a-executable-route-proof`
Spec: `docs/superpowers/specs/2026-07-23-validation-single-lane-active-surface-cleanup.md` §Pass 4 Stage A
Scope: the two Stage A items naming tests that assert on source text or on
themselves —

- "Replace `tests/test_model_generation_route.py` source-string assertions with
  executable call-path and isolated-filesystem proof that every discovered model
  uses the same canonical builder and output contract."
- "Rewrite `tests/test_runtime_contract_builder.py` from self-referential
  `live_contract_data()` equality/source-string checks to explicit expected
  contracts and malformed/error-contract rejection cases."

Also in scope: reporting the state of the two adjacent Stage A items —
`test_generate_form_model_discovery_cli.py` and the
`current_generation`/`draft_artifact` coverage in the promotion and schema
metadata tests — accurately, including "already delivered by an earlier pass" if
that is what the repo shows.

## Boundaries

- No production code change. Tests only.
- No workbook write; `stingray_master.xlsx` SHA-256 unchanged.
- Nothing published; every file under `form-output/` and `form-app/` unchanged.

## Criteria

C1 **No assertion in either file still reads source text to make its claim.**
No `read_text()`/`getsource` grep stands in for behavior. Reading a file to
*drive* a test is fine; asserting on its characters is not.

C2 **Every guarantee the deleted assertions carried is either re-established
executably or explicitly declared dead, with where it now lives.** The
dangerous ones are the assertions that were PASSING: the retired route-table and
retired-symbol checks, the "summary not rebuilt from review payloads" check, and
the retired `registry_promotion → live_contract_data` reverse dependency.

C3 **The route claim is proven for every workbook-discovered model, not a
sample, and the model set comes from discovery rather than a literal.** Adding
or activating a model must extend coverage without editing the test.

C4 **The route proof can fail.** Disabling the shared builder must break every
model. A test that only observes the happy path would pass against a build where
one model kept a private assembly path — state what input defeats each claim.

C5 **The contract-builder expectation is independent of the code under test.**
No expected value may be produced by `live_contract_data()` or by any helper the
builder itself calls. Every field the builder strips, rewrites, or overwrites is
named in the expectation.

C6 **Rejection cases cover the matrix, not one example.** Error severity,
invalid severity, each required-non-empty collection, a missing collection, a
malformed collection, a non-object `orderSummary`, and a non-object dataset.

C7 **No test passes for the wrong reason.** For each new test, a plausible future
narrowing of the code should break it. In particular the CLI test must fail if
`--output-root` stops being honored, and the strip test must fail if stripping
is narrowed to known row paths.

C8 **The already-delivered claim is verified, not assumed.** If
`test_generate_form_model_discovery_cli.py` and the retired-artifact-type
coverage are reported as needing no work, that is checked against the files.

C9 **Gates at or above baseline, no tracked churn.** The README Python metadata
gate set plus both rewritten files run green; `form-output/` and `form-app/`
byte-identical.
