# Checkpoint 4 measured evidence — fast layered validation suite

Evidence file for `docs/superpowers/specs/2026-08-17-fast-layered-validation-suite.md` §9,
Checkpoint 4. Closing acceptance output captured 2026-08-19.

Environment: darwin arm64; node v26.7.0; python 3.14.7 (`.venv`).
Canonical workbook and tracked generated/published artifacts were read-only.

## Default Node readiness lane

Command: the cataloged seventeen-file serial loop in
`suite.node_default_readiness`.

```text
all 17 files passed
NODE_WALL_SECONDS 51.34
```

Checkpoint 3 measured 57.88 s. The four default files that formerly spawned
private model generation now read retained contracts; fresh generation, strict
validation, source parity, registry publication, and browser proof remain joined
in the composed candidate lane. Only the two optional Layer 4 preview diagnostics
still invoke `generate_form.py`.

Focused post-edit proof:

```text
node --test tests/stingray-runtime-contract.test.mjs \
  tests/grand-sport-runtime-contract.test.mjs \
  tests/z06-runtime-contract.test.mjs \
  tests/z06-interior-accessory-cleanup.test.mjs
62 tests, 62 pass, duration_ms 13982.99
```

## Python metadata lane

The default lane no longer includes the separate Layer 3
`test_all_model_runtime_generation.py` owner. The runtime-step mutation hotspot
calls `load_runtime_steps()` directly against one in-memory workbook, while the
file retains representative real-generation failures for promoted and
unpromoted models.

```text
159 passed, 111 subtests passed in 34.74s
PYTHON_METADATA_WALL_SECONDS 35.0
```

The focused metadata file changed from:

```text
23 passed, 88 subtests passed in 118.48s
```

to:

```text
23 passed, 88 subtests passed in 14.97s
```

The separately retained Layer 3 all-model CLI/summary owner remains green:

```text
30 passed in 6.19s
```

## Candidate lane test consolidation

`tests/test_verify_workbook_candidate.py` now shares one canonical full run
(including the candidate browser harness) and one controlled-drift full run.
Stage order, report serialization, all-model marker behavior, temporary-registry
browser proof, and protected-boundary assertions reuse those results or compact
early-failure inputs.

```text
16 passed in 389.07s (0:06:29)
```

Checkpoint 3 inherited 684.74 s for this file. The retained end-to-end owners
still cover: successful complete candidate; pre-generation schema failure;
controlled generator/contract drift and later-stage partitioning; protected-path
mutation detection; and candidate browser/runtime matrix execution.

## Catalog and closeout

```text
.venv/bin/python -m pytest tests/test_validation_catalog.py -q
19 passed in 0.04s

git diff --check
passed
```

No workbook, generated artifact, published registry, runtime implementation,
dealer submission, deployment, dependency, or schema was changed. The
pre-existing user edits to `docs/asset-map-sync.md` were preserved. The
pre-existing `fable5loop/STATE.md` edit is updated only in its fixed Current
handoff block for this checkpoint.
