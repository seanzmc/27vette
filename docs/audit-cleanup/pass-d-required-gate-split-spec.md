# Pass D Spec — Required Gate Split

## Status

Completed. Implemented as docs/workflow-only; no tests were moved or edited.

Implementation result: `scripts/build_rule_sources.py`, `tests/grand-sport-rule-audit.test.mjs`, and `tests/audit-parser-metadata-loaders.test.mjs` were demoted from default readiness and documented as opt-in audit/report gates. No proof exception was found that they uniquely catch a current runtime-contract failure not already covered by generator/schema/runtime tests.

## User instruction

For Pass D:

- Do not treat existing tests/docs as proof of required status.
- Classify each gate by whether failure indicates live runtime/workbook-contract risk or only optional audit/report drift.
- Move `scripts/build_rule_sources.py` and Grand Sport rule-audit tests out of default readiness unless implementation can prove they catch a current runtime-contract failure not covered by generator/schema/runtime tests.
- Update `AGENTS.md` and `README.md` so normal gates are smaller and optional audit/report gates are explicitly opt-in.

## Diagnosis

Pass C removed the dead-end workbook rule rows that made skipped-row accounting look like required infrastructure. The remaining problem is gate policy: `AGENTS.md` and `README.md` still list Grand Sport rule-audit tooling beside normal model readiness gates, which makes optional report/audit drift look equivalent to live runtime or workbook-contract failure.

Root cause: historical audit/report tools were added to default command blocks while Grand Sport was still in migration. Existing documentation and tests now preserve their own inclusion, but that inclusion is not proof that they protect the live form. Pass D must classify gates from source-of-truth impact, not from current placement in docs.

Risk level: Medium. This is developer-workflow documentation and gate classification only. It does not change workbook data, generated data, runtime JS, dealer submission behavior, or deployment paths. The risk is under-testing future changes if a genuinely runtime-protective gate is demoted without evidence.

Change type: docs/workflow-only unless implementation finds a test that must be renamed or split to separate runtime-contract assertions from audit/report assertions.

## Evidence inspected

Current required/default gate references:

- `AGENTS.md:389` starts the current `Validation Gates` section.
- `AGENTS.md:409` Grand Sport source/draft refresh currently runs:
  - `.venv/bin/python scripts/generate_form.py --model grand_sport`
  - `node --test tests/grand-sport-contract-preview.test.mjs`
  - `node --test tests/grand-sport-draft-data.test.mjs`
  - `node --test tests/grand-sport-rule-audit.test.mjs`
  - `node --test tests/audit-parser-metadata-loaders.test.mjs`
- `AGENTS.md:448` full current suite includes the same Grand Sport rule-audit/parser-loader tests.
- `README.md:260` Grand Sport source/runtime-contract refresh currently includes `tests/grand-sport-rule-audit.test.mjs` and `tests/audit-parser-metadata-loaders.test.mjs`.
- `README.md:299` full model/runtime validation also includes those tests.
- `README.md:48` describes `scripts/build_rule_sources.py` as a workbook rule-source audit helper.
- `tests/grand-sport-rule-audit.test.mjs:58` shells out to `scripts/build_rule_sources.py --model grand_sport` and then asserts properties of `form-output/inspection/grand-sport-rule-audit.json` / `.md`.
- `README.md:283` states Grand Sport and Z06 promotion consume clean `*-runtime-contract.json` artifacts; draft-only provenance does not reach `form-app/data.js`.
- Pass C result: `rule_mapping`, `grandSport_rule_mapping`, and `z06_rule_mapping` now have zero runtime-skipped rows, and runtime contract comparisons matched after audit-row deletion.

Evidence standard for Pass D:

- Existing docs listing a command in a default block is not evidence.
- Existing tests passing or failing is not evidence by itself.
- A gate is default-required only if its failure means generated runtime data, live runtime behavior, workbook schema/source contract, model promotion, or dealer payload correctness may be wrong.
- A gate is optional audit/report only if it validates inspection reports, provenance reports, parser fallback metadata, historical buckets, markdown sections, or read-only reporting scripts that are not consumed by the app/runtime-contract path.

## Exact files to change

Primary docs:

- `AGENTS.md`
  - Rewrite the `Validation Gates` section so default readiness is smaller and risk-classified.
  - Remove `tests/grand-sport-rule-audit.test.mjs` and `tests/audit-parser-metadata-loaders.test.mjs` from default Grand Sport refresh and full default readiness unless proof is found that they catch current runtime-contract failures not covered elsewhere.
  - Add an explicit opt-in `Optional audit/report gates` block for `scripts/build_rule_sources.py`, `tests/grand-sport-rule-audit.test.mjs`, and `tests/audit-parser-metadata-loaders.test.mjs` if they remain report-only.

- `README.md`
  - Mirror the smaller normal gate set in `Workbook And Generator Workflows`.
  - Label rule-source audit generation as optional/reporting, not default readiness.
  - Keep `scripts/build_rule_sources.py` in repository structure as a helper if still useful, but describe it as opt-in audit/report tooling.

Cleanup overview:

- `docs/audit-cleanup-overview.md`
  - Mark Pass D as proposed/linked to this spec.
  - After implementation, update status and next-step guidance.

Spec artifact:

- `docs/audit-cleanup/pass-d-required-gate-split-spec.md`

Only if classification reveals mixed concerns inside a test:

- `tests/grand-sport-rule-audit.test.mjs`
- `tests/audit-parser-metadata-loaders.test.mjs`

Do not edit these tests merely to make the docs pass. Split or rename only if a current runtime-contract assertion is embedded in an otherwise optional audit/report test and needs to move to a default test file.

## Gate classification policy

Classify every documented gate into one of these buckets.

## Implementation classification result

| Gate | Classification | Reason |
| --- | --- | --- |
| `.venv/bin/python scripts/generate_form.py --model grand_sport` | Default readiness | Generates the Grand Sport inspection/draft/runtime-contract artifacts consumed by contract and runtime tests. |
| `node --test tests/grand-sport-contract-preview.test.mjs` | Default readiness | Validates generated Grand Sport contract-preview shape and workbook-to-contract section/source mapping. |
| `node --test tests/grand-sport-draft-data.test.mjs` | Default readiness | Validates generated Grand Sport draft/runtime-contract data, including rule groups, rule rows, pricing, sections, interiors, and workbook-owned runtime metadata. |
| `node --test tests/multi-model-runtime-switching.test.mjs` | Default when runtime registry/model switching can be affected | Validates active runtime behavior, model switching, exports, and dealer payload surfaces. |
| `.venv/bin/python scripts/build_rule_sources.py --model grand_sport` | Optional audit/report | Writes `grand-sport-rule-audit.json` / `.md`; these reports are not consumed by `form-app/data.js` or the clean Grand Sport runtime contract. |
| `node --test tests/grand-sport-rule-audit.test.mjs` | Optional audit/report | Tests rule-audit report generation, audit buckets, markdown sections, parser provenance, and read-only script behavior. Runtime-like assertions in this file are covered by default `grand-sport-draft-data` and/or `multi-model-runtime-switching` tests, so no proof exception was documented. |
| `node --test tests/audit-parser-metadata-loaders.test.mjs` | Optional audit/report | Unit-tests parser phrase fallback/override behavior used by `build_rule_sources.py`; it does not validate a generated runtime contract or live app path. |

Proof exception result: none. No Grand Sport audit/report gate remains in default readiness.

### Default readiness — live runtime/workbook-contract risk

A gate belongs here if failure indicates one of:

- workbook package or schema invalidity;
- generated runtime contract differs from workbook-owned source rules unexpectedly;
- `form-app/data.js` / promoted runtime registry can be wrong;
- active model runtime behavior can be wrong;
- dealer submission payload shape/model scoping can be wrong;
- workbook metadata used by generation/promotion/schema validation is wrong.

Expected default candidates, subject to implementation read-through:

- `.venv/bin/python scripts/validate_workbook_package.py stingray_master.xlsx` when a pass writes the workbook.
- `.venv/bin/python scripts/validate_workbook_schema.py stingray_master.xlsx` for workbook/generated/schema passes.
- `.venv/bin/python scripts/generate_form.py --model <affected_model>` for affected model data refresh.
- `node --test tests/stingray-form-regression.test.mjs`
- `node --test tests/stingray-generator-stability.test.mjs`
- `node --test tests/grand-sport-contract-preview.test.mjs`
- `node --test tests/grand-sport-draft-data.test.mjs`
- `node --test tests/z06-contract-preview.test.mjs`
- `node --test tests/z06-form-data-draft.test.mjs`
- `node --test tests/z06-runtime-promotion.test.mjs` when promotion/live registry can be affected.
- `node --test tests/z06-interior-accessory-cleanup.test.mjs`
- `node --test tests/z06-performance-package-interactions.test.mjs`
- `node --test tests/z06-runtime-rule-corrections.test.mjs`
- `node --test tests/multi-model-runtime-switching.test.mjs`
- `node --test tests/workbook-schema-standardization.test.mjs` when workbook source contracts, canonical typing, or retired-source guarantees can be affected.
- `node --test tests/workbook-visual-copy-standardization.test.mjs` only if the pass touches workbook copy/visual-copy standardization inputs.
- `.venv/bin/python -m pytest tests/test_model_config_metadata.py tests/test_registry_promotion_metadata.py tests/test_schema_validation_metadata.py -q` when model config, promotion metadata, or schema validation paths can be affected.

### Optional audit/report gates — opt-in only

A gate belongs here if failure indicates report drift, markdown/report shape drift, parser-audit metadata drift, historical audit bucket drift, or read-only diagnostic mismatch without proving a generated runtime-contract or workbook schema failure.

Expected optional candidates unless proven otherwise:

- `.venv/bin/python scripts/build_rule_sources.py --model grand_sport`
- `node --test tests/grand-sport-rule-audit.test.mjs`
- `node --test tests/audit-parser-metadata-loaders.test.mjs`

These should be documented as opt-in for:

- auditing parser/report behavior;
- refreshing `form-output/inspection/grand-sport-rule-audit.json` / `.md`;
- investigating rule provenance or historical parser decisions;
- maintaining `build_rule_sources.py` itself.

They should not block normal model readiness unless the implementation finds a concrete current assertion that uniquely catches a runtime-contract failure.

### Proof burden for keeping audit gates default-required

To keep `build_rule_sources.py` or Grand Sport rule-audit tests in default readiness, implementation must document all of:

1. The exact assertion and file/line.
2. The generated runtime artifact, workbook source contract, or live runtime behavior it protects.
3. Why the same failure is not covered by `generate_form.py`, schema validation, `grand-sport-contract-preview`, `grand-sport-draft-data`, or multi-model runtime tests.
4. Whether that assertion can be moved to a default runtime/contract test, leaving the audit/report test opt-in.

If that proof is absent, demote the gate.

## Proposed normal gate shape after Pass D

### Docs-only changes

Keep as docs-only:

```sh
git diff -- README.md AGENTS.md codex-context.md docs/audit-cleanup-overview.md docs/audit-cleanup/pass-d-required-gate-split-spec.md
rg -n "grand-sport-rule-audit|audit-parser-metadata-loaders|build_rule_sources.py" README.md AGENTS.md docs/audit-cleanup-overview.md docs/audit-cleanup/pass-d-required-gate-split-spec.md
```

The `rg` check should verify those names only appear in optional audit/report contexts unless the spec documents a proven exception.

### Grand Sport source/runtime-contract refresh

Default readiness should become:

```sh
.venv/bin/python scripts/generate_form.py --model grand_sport
node --test tests/grand-sport-contract-preview.test.mjs
node --test tests/grand-sport-draft-data.test.mjs
```

Add `node --test tests/multi-model-runtime-switching.test.mjs` only when promoted runtime registry/model switching behavior can be affected.

### Optional Grand Sport audit/report refresh

Opt-in, not default readiness:

```sh
.venv/bin/python scripts/build_rule_sources.py --model grand_sport
node --test tests/grand-sport-rule-audit.test.mjs
node --test tests/audit-parser-metadata-loaders.test.mjs
```

### Full default readiness suite

Remove optional audit/report tests from the default full suite unless the proof burden above is met. Keep schema/generator/runtime tests that protect active model contracts.

## Constraints

- Do not alter workbook data.
- Do not regenerate artifacts except if a validation command in implementation incidentally rewrites timestamps; if that happens, inspect and restore unrelated generated churn before handoff unless the pass explicitly approves retaining it.
- Do not change runtime JS, CSS, dealer endpoint, dealer payload shape, Turnstile behavior, or deployment paths.
- Do not add dependencies.
- Do not delete `scripts/build_rule_sources.py` in Pass D. This pass is gate classification, not tool retirement.
- Do not use current test/docs placement as proof of required status.
- Preserve workbook source-of-truth rules: if a future gate catches a real workbook business-rule problem, prefer moving that assertion to a schema/generator/runtime-contract test over keeping an audit/report gate as default.

## Non-goals

- No workbook row cleanup.
- No runtime metadata consolidation.
- No retirement of `build_rule_sources.py`.
- No test deletion unless a test is proven obsolete and separately approved.
- No changes to generated `form-output/` or `form-app/data.js` as committed outputs.
- No change to model promotion state.

## Implementation plan

1. Re-read the current `AGENTS.md`, `README.md`, `tests/grand-sport-rule-audit.test.mjs`, `tests/audit-parser-metadata-loaders.test.mjs`, and `scripts/build_rule_sources.py` sections that determine default gate status.
2. Build a short classification table for each documented command:
   - command;
   - current location;
   - consumed artifact/path;
   - failure class: runtime/workbook-contract vs optional audit/report;
   - default or opt-in decision;
   - proof note.
3. For `build_rule_sources.py`, `tests/grand-sport-rule-audit.test.mjs`, and `tests/audit-parser-metadata-loaders.test.mjs`, apply the proof burden above. If no unique runtime-contract protection is found, classify them as optional.
4. Patch `AGENTS.md` validation gates:
   - make the normal/default blocks smaller;
   - add an explicit optional audit/report block;
   - state that existing docs/tests are not proof of default status.
5. Patch `README.md` workflow section with the same split:
   - normal refresh/readiness commands;
   - optional audit/report commands.
6. Patch `docs/audit-cleanup-overview.md` to record Pass D status/result.
7. Do not touch workbook or generated runtime artifacts.

## Validation plan

Because Pass D is docs/workflow-only unless implementation discovers test refactoring is needed:

```sh
git diff -- AGENTS.md README.md docs/audit-cleanup-overview.md docs/audit-cleanup/pass-d-required-gate-split-spec.md
rg -n "grand-sport-rule-audit|audit-parser-metadata-loaders|build_rule_sources.py" AGENTS.md README.md docs/audit-cleanup-overview.md docs/audit-cleanup/pass-d-required-gate-split-spec.md
rg -n "Full current suite|default gates|default readiness|optional audit|Grand Sport source" AGENTS.md README.md docs/audit-cleanup-overview.md
```

Expected validation result:

- `tests/grand-sport-rule-audit.test.mjs`, `tests/audit-parser-metadata-loaders.test.mjs`, and `scripts/build_rule_sources.py` appear only in optional audit/report contexts unless a documented proof exception is added.
- Normal Grand Sport readiness blocks omit Grand Sport rule-audit/parser-loader gates.
- Full default readiness blocks omit optional audit/report gates.
- Historical completed pass specs may still mention the old audit commands as evidence of earlier work; those files are not current readiness instructions.

If implementation changes tests, also run the changed tests and any default test that receives moved runtime-contract assertions.

## Handoff requirements

Report:

- Which gates were classified as default-required.
- Which gates were classified as optional audit/report.
- Whether any proof was found to keep Grand Sport rule-audit tooling in default readiness.
- Exact docs changed.
- Commands run.
- Gates not run and why.
- Next step guidance: if Pass D lands cleanly, the next logical pass remains Pass E, runtime metadata consolidation, unless the user wants a separate `build_rule_sources.py` usefulness review.
