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

`tests/test_verify_workbook_candidate.py` shares the three full runs it needs:
the canonical workbook with nothing declared changed (including the candidate
browser harness), and one controlled-drift workbook read once undeclared and
once declared. Stage order, report serialization, all-model marker behavior,
temporary-registry browser proof, and protected-boundary assertions reuse those
results or compact early-failure inputs.

```text
17 passed in 457.54s (0:07:37)
```

Checkpoint 3 inherited 684.74 s for this file. The retained end-to-end owners
still cover: successful complete candidate; pre-generation schema failure;
controlled generator/contract drift and later-stage partitioning; declared-drift
suppression; protected-path mutation detection; and candidate browser/runtime
matrix execution.

### Review correction to the first Checkpoint 4 consolidation

The first version of this consolidation ran its shared canonical fixture with
`changed_models=["*"]` and measured 389.07 s over 16 tests. That is cheaper but
unsound. `verify_candidate` computes `unexpected_drift` as "drifted AND not
declared", and `declared_changed_set(["*"], …)` returns every model, so
declaring `*` makes that set unreachable. Three proofs went quiet at once:

- `test_the_canonical_workbook_has_no_undeclared_drift` could no longer fail on
  a stale retained artifact — the defect class it exists for, and the one the
  four de-generated Node gates now depend on being absent.
- `test_declaring_a_changed_model_does_not_reduce_the_generated_set` could no
  longer catch a generation filter keyed on the touched set, because the
  filtered and unfiltered sets are identical when everything is declared.
- `test_declaring_drift_moves_it_out_of_unexpected_and_passes` had been deleted,
  leaving no run at all that pairs real drift with a declaration.

The fixture now declares nothing, which makes the first two assertions load
bearing again and, with an empty declared set, proves the generation set is not
filtered more strongly than the `*` run did. The deleted test is restored
against a third full run. The `*` marker keeps a direct unit proof over
`declared_changed_set`. Net cost of the correction: +68.47 s, still 227.20 s
below the Checkpoint 3 inheritance.

## Catalog and closeout

```text
.venv/bin/python -m pytest tests/test_validation_catalog.py -q
20 passed in 0.03s

git diff --check
passed
```

The catalog contract gained `test_no_output_isolation_kinds_declare_no_writes`.
Every other isolation assertion branches on `generates`, so a gate declaring
`generates: false` escaped all of them. That is how three Node gates came to be
declared `read_only` with no writes while still writing:

| Gate | What it actually writes | Corrected isolation |
|---|---|---|
| `node.stingray-runtime-contract` | mkdtemp copies of `stingray_master.xlsx`, mutated and read back | `temp_workbook_copy` |
| `node.grand-sport-runtime-contract` | workbook-truth snapshot via `tests/lib/workbook-truth.mjs` | `tmp_path_fixture` |
| `node.z06-runtime-contract` | workbook-truth snapshot via `tests/lib/workbook-truth.mjs` | `tmp_path_fixture` |

`node.z06-interior-accessory-cleanup` is genuinely read-only and is unchanged.

No workbook, generated artifact, published registry, runtime implementation,
dealer submission, deployment, dependency, or schema was changed. The
pre-existing user edits to `docs/asset-map-sync.md` were preserved. The
pre-existing `fable5loop/STATE.md` edit is updated only in its fixed Current
handoff block for this checkpoint.
