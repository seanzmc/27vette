# Pass 6B — Optional Inspection Artifact Emission Spec

Status: Spec only. Do not implement until approved.
Date: 2026-06-21
Recommended reasoning level for implementation agent: high.

## Goal

Make normal `generate_form.py --model <model>` runs write only artifacts needed by the live workbook-to-runtime path, while keeping Grand Sport/Z06 inspection artifacts available on explicit request.

This pass must:

1. Keep all active models writing clean runtime contracts under `form-output/runtime/`.
2. Stop default Grand Sport/Z06 generation from writing bulky `form-output/inspection/` inspection, preview, and draft artifacts.
3. Add an explicit review mode that emits the current inspection bundle when needed.
4. Move tests that need preview/draft artifacts onto explicit review output or direct builders.
5. Preserve Stingray compatibility JSON/CSV behavior for now.

This pass is output-policy cleanup only. It must not change source-row assembly, runtime behavior, workbook business data, registry promotion, or dealer submission behavior.

## Diagnosis

Risk level: medium.

Change type: generator-output policy + tests + docs. No workbook/data edits. No runtime JS/CSS behavior edits.

Current evidence:

- `form-output/inspection/` is about `8.5M`.
- Largest routine files are generated Grand Sport/Z06 review artifacts:
  - `form-output/inspection/grand-sport-form-data-draft.json`: about `2.2M`
  - `form-output/inspection/z06-form-data-draft.json`: about `2.2M`
  - `form-output/inspection/grand-sport-contract-preview.json`: about `1.7M`
  - `form-output/inspection/z06-contract-preview.json`: about `1.7M`
  - `form-output/inspection/grand-sport-inspection.json`: about `308K`
  - `form-output/inspection/z06-inspection.json`: about `304K`
- `scripts/corvette_form_generator/model_generation.py` currently always calls:
  - `write_inspection_artifacts(...)`
  - `write_contract_preview_artifacts(...)`
  - `write_form_data_draft_artifacts(...)`
  - `write_runtime_contract_artifact(...)`
- The runtime/dealer app only needs clean runtime contracts:
  - `form-output/runtime/stingray-runtime-contract.json`
  - `form-output/runtime/grand-sport-runtime-contract.json`
  - `form-output/runtime/z06-runtime-contract.json`
- `scripts/generate_registry.py` consumes promoted runtime contracts from workbook promotion metadata and writes `form-app/data.js`.
- `tests/grand-sport-contract-preview.test.mjs`, `tests/grand-sport-draft-data.test.mjs`, `tests/z06-contract-preview.test.mjs`, and `tests/z06-form-data-draft.test.mjs` currently shell out to `generate_form.py` and read `form-output/inspection/*` files.
- `tests/test_generate_form_model_discovery_cli.py` currently expects Grand Sport/Z06 default stdout to contain non-empty `inspection_artifacts`, `preview_artifacts`, and `draft_artifacts` paths.
- `form-output/inspection/grand-sport-rule-audit.json` / `.md` are produced by optional audit tooling, not by the normal `generate_form.py` route. They are outside the default-output slimming target.

Root cause:

Grand Sport/Z06 still use the historical inspection/draft assembly path. Pass 6A put one output-orchestration layer around that path, but the wrapper still writes every intermediate review artifact by default even though the live runtime consumes only the clean runtime contract.

The bulky files have review/debug/test value, not default runtime value. Writing them every normal form generation creates noisy timestamp churn and makes the default output surface look larger than the live contract actually is.

## Scope

### In scope

- Add explicit inspection emission controls to `scripts/generate_form.py`:
  - `--emit-inspection`
  - `--inspection-output <path>`
- Add an options object or equivalent explicit parameters in `scripts/corvette_form_generator/model_generation.py` so default generation builds preview/draft in memory but writes only runtime contract artifacts for Grand Sport/Z06.
- Keep stdout contract keys from Pass 6A stable:
  - `inspection_artifacts`
  - `preview_artifacts`
  - `draft_artifacts`
- Change default Grand Sport/Z06 stdout so those artifact maps are empty when `--emit-inspection` is not passed.
- Change explicit review-mode stdout so those artifact maps point to emitted files when `--emit-inspection` is passed.
- Support explicit review output outside the repo, e.g. `/tmp/27vette-pass6b-inspection-grand-sport`, so tests can avoid dirtying tracked generated artifacts.
- Remove the checked-in routine Grand Sport/Z06 inspection/preview/draft artifacts after tests/docs no longer depend on them:
  - `form-output/inspection/grand-sport-inspection.json`
  - `form-output/inspection/grand-sport-inspection.md`
  - `form-output/inspection/grand-sport-contract-preview.json`
  - `form-output/inspection/grand-sport-contract-preview.md`
  - `form-output/inspection/grand-sport-form-data-draft.json`
  - `form-output/inspection/grand-sport-form-data-draft.md`
  - `form-output/inspection/z06-inspection.json`
  - `form-output/inspection/z06-inspection.md`
  - `form-output/inspection/z06-contract-preview.json`
  - `form-output/inspection/z06-contract-preview.md`
  - `form-output/inspection/z06-form-data-draft.json`
  - `form-output/inspection/z06-form-data-draft.md`
- Keep optional rule-audit outputs untouched:
  - `form-output/inspection/grand-sport-rule-audit.json`
  - `form-output/inspection/grand-sport-rule-audit.md`
- Update tests that consume inspection outputs so they use explicit temporary review output or direct builder calls.
- Update docs that currently say normal Grand Sport/Z06 generation writes inspection/preview/draft files by default.

### Out of scope

- No workbook edits.
- No source-row assembly unification.
- No Stingray move off `production.py`.
- No Stingray compatibility artifact retirement.
- No changes to `form-output/stingray-form-data.json` or `form-output/stingray-form-data.csv` behavior.
- No runtime JavaScript behavior changes.
- No dealer submission endpoint, payload, or Turnstile changes.
- No GBA/ZYC, `runtime_action`, `body_style_scope`, exclusive-group drift, or option-ID cleanup.
- No deletion of optional rule-audit tooling or artifacts.
- No new dependencies.

## Exact files to change

Implementation files:

- `scripts/generate_form.py`
  - Add CLI flags `--emit-inspection` and `--inspection-output`.
  - Pass explicit generation options into `generate_model_artifacts(...)`.
  - Keep unsupported/inactive model behavior unchanged.

- `scripts/corvette_form_generator/model_generation.py`
  - Add a small explicit options type, e.g. `GenerationOptions`.
  - Default `emit_inspection=False`.
  - Default `inspection_output_dir=None`, resolved only when `emit_inspection=True`.
  - Keep Grand Sport/Z06 preview and draft construction in memory for runtime contract generation.
  - Write `inspection_artifacts`, `preview_artifacts`, and `draft_artifacts` only when `emit_inspection=True`.
  - Always write `runtime_contract_artifacts` for active models.
  - Preserve `TEMPORARY_ROUTE_ENGINES` and current source-row assembly split.

- `scripts/corvette_form_generator/inspection.py`
  - Only touch if needed to support caller-supplied output directories without changing artifact contents. Existing writer functions already accept an output directory, so no edit should be required unless tests expose a path bug.

Test files:

- `tests/test_generate_form_model_discovery_cli.py`
  - Assert default Grand Sport/Z06 stdout has empty `inspection_artifacts`, `preview_artifacts`, and `draft_artifacts`.
  - Add explicit `--emit-inspection --inspection-output <tmpdir>` coverage for Grand Sport and Z06.
  - Assert explicit review mode writes inspection, preview, and draft artifacts to the requested temp directory.
  - Assert default generation does not recreate deleted routine inspection files.

- `tests/test_model_generation_route.py`
  - Update route-orchestration source guards for the new options flow.
  - Guard that default artifact emission is optional, not unconditional.

- `tests/grand-sport-contract-preview.test.mjs`
  - Stop reading `form-output/inspection/grand-sport-contract-preview.json` as a default side effect.
  - Use `--emit-inspection --inspection-output <tmpdir>` or direct `build_contract_preview()` output.
  - Preserve existing preview assertions.

- `tests/grand-sport-draft-data.test.mjs`
  - Stop reading `form-output/inspection/grand-sport-form-data-draft.json` as a default side effect.
  - Use `--emit-inspection --inspection-output <tmpdir>` or direct `build_form_data_draft()` output.
  - Preserve existing draft assertions.

- `tests/z06-contract-preview.test.mjs`
  - Same temp review-output or direct-builder pattern for Z06 preview.

- `tests/z06-form-data-draft.test.mjs`
  - Same temp review-output or direct-builder pattern for Z06 draft.

Docs/spec files:

- `docs/audit-cleanup/pass-6b-inspection-artifact-policy-spec.md`
  - This spec. Update with completion evidence when implemented.

- `docs/Audit-route-map.md`
  - Mark Pass 6B implemented after completion.
  - Update route map so Grand Sport/Z06 normal generation writes runtime contracts by default and inspection outputs only on explicit review mode.
  - Move source-row assembly unification to the next pass.

- `README.md`
  - Update generated-output description and generation workflow docs.
  - Say inspection/preview/draft artifacts are explicit review outputs, not normal generation outputs.

- `AGENTS.md`
  - Update only if current standing workflow text would otherwise imply normal Grand Sport/Z06 generation writes inspection/preview/draft files by default.
  - Keep validation gate commands current.

Generated artifacts to remove from tracked default output:

- The twelve Grand Sport/Z06 inspection/preview/draft files listed in Scope.

Generated artifacts to keep:

- `form-output/runtime/*.json`
- `form-output/stingray-form-data.json`
- `form-output/stingray-form-data.csv`
- `form-app/data.js`
- `form-output/inspection/grand-sport-rule-audit.json`
- `form-output/inspection/grand-sport-rule-audit.md`

## Implementation plan

1. Preflight and current baseline.
   - Verify branch/status.
   - Verify no Excel lock.
   - Run normal generation for `stingray`, `grand_sport`, and `z06`, then `generate_registry.py`.
   - Copy baseline runtime contracts and Stingray compatibility outputs to `/tmp/27vette-pass6b-before`.
   - Classify any pre-existing generated diffs before editing.

2. Add RED tests.
   - Update/add CLI tests so Grand Sport/Z06 default generation is expected not to emit inspection artifacts.
   - Add review-mode tests using temporary output dirs.
   - Run the focused tests and confirm they fail against current behavior.

3. Implement optional inspection emission.
   - Add `GenerationOptions` or equivalent in `model_generation.py`.
   - Add CLI flags in `generate_form.py`.
   - Ensure default Grand Sport/Z06 path still builds the draft in memory and writes only runtime contract JSON.
   - Ensure `--emit-inspection` writes the same inspection/preview/draft content as before, just to the requested output directory when supplied.

4. Move tests off default `form-output/inspection` side effects.
   - Update preview/draft tests to use temp explicit review output or direct builders.
   - Keep assertions unchanged where possible.

5. Remove routine tracked inspection/preview/draft files.
   - Delete only the twelve Grand Sport/Z06 routine inspection files listed above.
   - Keep `grand-sport-rule-audit.*` intact.

6. Regenerate and verify parity.
   - Run default generation for all active models plus registry.
   - Compare runtime contracts and Stingray compatibility outputs against baseline.
   - Confirm default Grand Sport/Z06 generation does not recreate deleted inspection files.
   - Run explicit review generation to temp dirs and confirm expected files are emitted there.

7. Update docs and close spec.
   - Update `docs/Audit-route-map.md` and `README.md`; update `AGENTS.md` only if stale.
   - Mark this spec implemented with changed files, gates, artifact deletion list, parity evidence, and residual follow-up.

## Expected CLI behavior

Default runtime generation:

```sh
.venv/bin/python scripts/generate_form.py --model grand_sport
.venv/bin/python scripts/generate_form.py --model z06
```

Expected default behavior:

- Writes:
  - `form-output/runtime/grand-sport-runtime-contract.json`
  - `form-output/runtime/z06-runtime-contract.json`
- Does not write:
  - `form-output/inspection/grand-sport-inspection.*`
  - `form-output/inspection/grand-sport-contract-preview.*`
  - `form-output/inspection/grand-sport-form-data-draft.*`
  - `form-output/inspection/z06-inspection.*`
  - `form-output/inspection/z06-contract-preview.*`
  - `form-output/inspection/z06-form-data-draft.*`
- Stdout keeps `inspection_artifacts`, `preview_artifacts`, and `draft_artifacts`, but each is `{}`.

Explicit review output:

```sh
.venv/bin/python scripts/generate_form.py \
  --model grand_sport \
  --emit-inspection \
  --inspection-output /tmp/27vette-grand-sport-inspection

.venv/bin/python scripts/generate_form.py \
  --model z06 \
  --emit-inspection \
  --inspection-output /tmp/27vette-z06-inspection
```

Expected review behavior:

- Still writes clean runtime contract under `form-output/runtime/`.
- Writes inspection, preview, and draft artifacts to the requested output directory.
- Stdout artifact maps point to the requested output directory.
- Artifact payloads are equivalent to current review artifacts except generated timestamp fields and output paths.

Stingray default generation:

```sh
.venv/bin/python scripts/generate_form.py --model stingray
```

Expected Stingray behavior in this pass:

- Unchanged.
- Still writes clean runtime contract.
- Still writes compatibility JSON/CSV.
- Still returns empty inspection/preview/draft artifact maps.

## Validation plan

Preflight:

```sh
git status --short --branch
test ! -e '~$stingray_master.xlsx'
.venv/bin/python scripts/validate_workbook_schema.py stingray_master.xlsx
```

RED/focused Python tests:

```sh
.venv/bin/python -m pytest \
  tests/test_generate_form_model_discovery_cli.py \
  tests/test_model_generation_route.py \
  -q
```

Syntax/focused implementation tests:

```sh
.venv/bin/python -m py_compile \
  scripts/generate_form.py \
  scripts/corvette_form_generator/model_generation.py \
  scripts/corvette_form_generator/inspection.py \
  scripts/corvette_form_generator/production.py

.venv/bin/python -m pytest \
  tests/test_generate_form_model_discovery_cli.py \
  tests/test_model_generation_route.py \
  tests/test_runtime_contract_builder.py \
  tests/test_model_config_metadata.py \
  -q
```

Default generation and parity:

```sh
BASE=/tmp/27vette-pass6b-before
.venv/bin/python scripts/generate_form.py --model stingray > /tmp/pass6b-stingray-default.json
.venv/bin/python scripts/generate_form.py --model grand_sport > /tmp/pass6b-grand-sport-default.json
.venv/bin/python scripts/generate_form.py --model z06 > /tmp/pass6b-z06-default.json
.venv/bin/python scripts/generate_registry.py > /tmp/pass6b-registry.json

node scripts/compare-generated-contracts.mjs "$BASE/stingray-runtime-contract.json" form-output/runtime/stingray-runtime-contract.json
node scripts/compare-generated-contracts.mjs "$BASE/grand-sport-runtime-contract.json" form-output/runtime/grand-sport-runtime-contract.json
node scripts/compare-generated-contracts.mjs "$BASE/z06-runtime-contract.json" form-output/runtime/z06-runtime-contract.json
node scripts/compare-generated-contracts.mjs "$BASE/stingray-form-data.json" form-output/stingray-form-data.json
cmp -s "$BASE/stingray-form-data.csv" form-output/stingray-form-data.csv
```

Explicit review output smoke:

```sh
rm -rf /tmp/27vette-pass6b-grand-sport-inspection /tmp/27vette-pass6b-z06-inspection
.venv/bin/python scripts/generate_form.py --model grand_sport --emit-inspection --inspection-output /tmp/27vette-pass6b-grand-sport-inspection
.venv/bin/python scripts/generate_form.py --model z06 --emit-inspection --inspection-output /tmp/27vette-pass6b-z06-inspection
ls /tmp/27vette-pass6b-grand-sport-inspection
ls /tmp/27vette-pass6b-z06-inspection
```

Node model tests:

```sh
node --test tests/grand-sport-contract-preview.test.mjs
node --test tests/grand-sport-draft-data.test.mjs
node --test tests/z06-contract-preview.test.mjs
node --test tests/z06-form-data-draft.test.mjs
node --test tests/grand-sport-contract-preview.test.mjs
node --test tests/grand-sport-draft-data.test.mjs
node --test tests/z06-contract-preview.test.mjs
node --test tests/z06-form-data-draft.test.mjs
node --test tests/multi-model-runtime-switching.test.mjs
```

Final docs/diff checks:

```sh
git diff --check
git status --short
```

## Risks and mitigations

Risk: tests accidentally keep depending on stale checked-in inspection files.

Mitigation: delete routine checked-in files and make tests read temp explicit output or direct builder results.

Risk: default Grand Sport/Z06 generation stops writing files a developer used manually.

Mitigation: provide `--emit-inspection` and document it in README and route map.

Risk: review-mode artifact payload drifts while runtime parity passes.

Mitigation: compare review-mode output shape and preserve current preview/draft assertions in existing tests.

Risk: removing tracked inspection files hides useful review state.

Mitigation: keep review mode, keep optional rule audit outputs, and keep runtime contracts as the source of live generated data.

Risk: this pass looks like source-route unification.

Mitigation: explicitly preserve `TEMPORARY_ROUTE_ENGINES`, `production.py`, and the Grand Sport/Z06 inspection/draft assembly path. This pass only changes when intermediate artifacts are written.

## Non-goals

- Do not reduce `form-output/runtime/*` content.
- Do not change runtime contract schema.
- Do not change active model promotion metadata.
- Do not remove Stingray compatibility JSON/CSV.
- Do not change source workbook rows.
- Do not change customer-facing model behavior.

## Completion requirements

When implementing this spec, update this file before final handoff with:

- final status and date;
- changed files;
- deleted generated inspection artifacts;
- default-generation stdout contract evidence;
- explicit review-mode stdout/artifact evidence;
- runtime contract parity evidence;
- Stingray compatibility JSON/CSV parity evidence;
- tests/gates run;
- generated artifact diff review;
- docs updated;
- residual risks and recommended next pass.

## Recommended next pass after Pass 6B

Pass 6C should address source-row assembly unification: remove the temporary `production` vs `inspection_draft` assembly split while preserving runtime-contract parity.

After Pass 6C is proven, handle business-rule cleanup as separate workbook/runtime passes:

1. GBA / `opt_zyc_001` runtime hardcode removal if workbook `runtime_rule_exceptions` fully covers behavior.
2. `runtime_action=replace` classification.
3. `body_style_scope` classification.
4. Stingray exclusive-group ID/style drift.
5. Z06 option-ID suffix / no-RPO drift.
6. residual copy allowlist decisions.

## Approval prompt

Approve Pass 6B implementation as scoped above?
