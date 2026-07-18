# Milestone 3 — Canonical Plan Projection and Temporary Deployment Proof

Status: IMPLEMENTED AND PARENT-VERIFIED 2026-07-18; independent final verification is in progress. Sean authorized this milestone with “Begin Milestone 3 from run 20260717-091317-470292” and later delegated the greenfield-isolation continuation to Hermes's best judgment. This milestone does not authorize a live write to `stingray_master.xlsx`, runtime publication, model promotion, deployment, or dealer changes.

Recommended reasoning level: high.

## 1. Diagnosis and exact starting evidence

Run `20260717-091317-470292` is the exact Milestone 3 input. Current readback shows:

- session state `compiled_ready`;
- targets `grand_sport_x`, `zr1`, and `zr1x` with modes `greenfield`, `reprocess`, and `reprocess`;
- all three targets have `compileReady=true`, zero blockers, and zero deferrals;
- 6,408 ready canonical rows: 2,581 `add`, 941 `update`, 2,886 `noop`, and zero blocked rows;
- 158 typed subjects and 158 valid current resolutions, with zero queue/resolution mismatch, one retained stale historical entry, and 46 superseded entries;
- 61 whole-proposal rejections, 45 section choices, 43 typed values, six relationship choices, and three explicit inactive-option retentions;
- 11,298 source-feature dispositions in the compile report;
- canonical manifest file SHA-256 `b3e32dea5afeaf10eb6296d82283ff844403a80da1f3659b6ad20d5d0409926f` and semantic SHA `b402e0d390d139932e38952d07bfa8f09e20a1ade3bef2c5f4970b8ed3c85585` at exact-current preflight.

N26 scope provenance was rechecked before deployment proof. The retained resolution was entered by `Milestone3-preflight`; on 2026-07-18 Sean delegated continuation decisions to Hermes's best judgment. Hermes retained wildcard scope (`*`) because the source presents one `$695` N26 price without a narrower trim, body-style, or variant qualifier. The failed attempt to reopen the already planned run rolled back atomically; all five compiler-artifact hashes and the protected workbook hash remained unchanged.

The current legacy `build_apply_plan()` path is not eligible for this run. It accepts only broad-decision states and calls the `pass-c-2` builder, which still infers product meaning and performs clean-reprocess deletes. The approved production design requires the opposite: `identity.py` and the compiler already own desired-state reconciliation; Milestone 3 must translate the ready manifest without changing any key, value, or action.

Milestones 2.4/2.4.1 passed independent exact-current verification on 2026-07-18: 91 focused tests plus seven subtests passed, in-memory recompilation reproduced all compiler artifacts exactly, and the protected workbook/generated/runtime hashes remained unchanged. This closes the mechanical prerequisite; Milestone 3 deployment proof remains separately gated.

## 2. Goal

Implement and prove the mechanical path:

`compiled_ready` manifest → `pass-c-3` plan → scoped dry-run approval → exact temporary-workbook apply/readback → target activation in temporary copies → existing generation/registry/contract validation.

The retained canonical workbook and tracked generated/publication surfaces must remain byte-identical.

## 3. Source-of-truth and ownership

- `canonical-row-manifest.json` owns the complete desired workbook rows, physical keys, typed values, and `add`/`update`/`delete`/`noop` actions for this milestone.
- `compile-report.json`, `exception-resolutions.json`, `exception-queue.json`, `comparator-evidence.json`, the run authority envelope, source fingerprint, model selection, and workbook fingerprint are immutable bound evidence.
- `plan_builder.py` may validate and translate only. It may not choose an ID, infer a row, rematch identity, change a field, alter an action, or revive legacy broad decisions.
- `editor_ops.apply_batch()` remains the only operation validation/temp-write/readback path.
- Existing model discovery, source assembly, runtime-contract validation, and registry loaders remain the deployment proof authorities.

Standing boundaries from `AGENTS.md` §§3–6, 8, 10–12 apply.

## 4. Required implementation

### 4.1 Mechanical `pass-c-3` builder

Add a manifest projection entry point in `scripts/corvette_form_generator/ingest/wizard/plan_builder.py`.

It must:

1. Accept the exact loaded compiler artifact set, selected targets, workbook path, source/candidate fingerprints, and run authority.
2. Revalidate the compiler artifact graph before projection.
3. Require the selected target set to equal manifest `modelModes`, compile-report models, comparator targets, and model selection.
4. Require every selected target `compileReady=true`, no blockers, no deferrals outside the closed policy, and every manifest row `status=ready`.
5. Validate every manifest family against `EDITOR_SHEET_META`, every key against that family’s canonical key columns, every value key against the exact live canonical header vector, and every typed value through the existing artifact validator/editor metadata.
6. Add only deterministic `create_sheet` operations for absent manifest target sheets, using an existing active same-family sheet with the exact consensus header vector as `headersFrom`.
7. Translate each manifest `add`, `update`, or `delete` to one editor operation with byte/JSON-equivalent `sheet`, `key`, and `values` (`values` becomes `row`).
8. Record each `noop` as an explicit covered no-op; do not send it to `editor_ops` as a mutation.
9. Place sheet creation in stage 1 and row operations in deterministic dependency-safe stage 2 order. Ordering may not change semantic content.
10. Emit exact manifest-row coverage: every mutation row maps to one operation; every no-op maps to one no-op receipt; no operation lacks one manifest row except named sheet-creation scaffolding.
11. Bind the exact compiler artifacts, authority envelope, model selection, source/candidate/workbook fingerprints, and manifest semantic hash in `apply-plan.json`.
12. Emit schema `pass-c-3`; never relabel or upgrade a legacy plan.

### 4.2 Readiness ownership without circular hashes

Compiler artifacts remain immutable after plan creation. Readiness is stage-owned:

- `compile-report.json` proves `compileReady` and an empty compiler blocker set;
- `apply-plan.json` proves `planReady` through exact projection and coverage;
- `apply-dry-run-report.json` proves `writeReady`/`deploymentReady` through the bound temporary-workbook result and per-target deployment evidence.

The writer must not require post-compile readiness flags in the immutable compile report to become true after its SHA has already been bound into the plan. It must require `compileReady=true` plus empty compiler blockers, exact plan readiness, and the current dry-run deployment/write gates. This is a contract clarification, not a weakening: later-stage readiness must come from the artifact that actually performed that stage.

### 4.3 Session/API/browser path

Update `WizardSessionStore.build_apply_plan()` so:

- `compiled_ready` uses only the manifest projection path;
- historical `decisions_complete` and related legacy states keep the existing `pass-c-2` diagnostic path unchanged;
- `compiled_with_exceptions` refuses plan projection;
- current-input/artifact drift refuses before writing plan artifacts;
- rebuilding an existing current `pass-c-3` plan is deterministic;
- successful projection writes `apply-plan.json`, `apply-plan-dryrun.json`, and `apply-plan.md`, then enters `plan_built`;
- compiler mutation/recompile remains refused once downstream plan evidence exists.

Reuse the existing strict plan GET/POST/approval routes. Add a compiler-summary action that appears only for fresh `compiled_ready` runs and opens the existing plan stage. Relabel that stage for the forward compiler path as a canonical plan; preserve historical plan wording/routes for legacy runs. Do not add a workbook-apply button.

### 4.4 Temporary deployment proof

After `plan-approval-2` with `scope=dry_run_evidence`, the existing dry-run CLI/service path must:

1. Revalidate every plan/compiler/selection/source/workbook binding.
2. Apply the exact combined stage-1 + stage-2 batch to a temporary workbook through `editor_ops.apply_batch(write=True)` only in the temporary directory.
3. Require raw-operation coverage, prepared-operation readback, workbook package validation, schema validation, and Boolean hygiene.
4. Activate only the target models/variants/source registrations/promotion metadata in the temporary workbook.
5. Run existing discovery and `assemble_model_source()` with every config path overridden to the temporary workbook/root/output/app directories.
6. Validate every in-memory runtime contract with `assert_runtime_contract()`.
7. Write runtime-contract files only under the temporary root, bind promotion rows there, and prove `build_registry_from_artifacts()` loads the candidate targets without writing `form-app/data.js`.
8. Compare generated direct rules, rule groups/members, exclusive groups/members, defaults, and price rules to the manifest’s target semantic signatures. Set equality is required for target-authored material rows; unmatched manifest or generated signatures block deployment readiness.
9. Require zero generated validation errors, nonzero customer-selectable choices, exact target variants, and source-feature coverage agreement.
10. Report per-target counts, signature mismatches, validation results, and registry loadability.

Proof order is explicit:

- first Grand Sport X plus ZR1 on one temporary copy;
- then ZR1X through the same reprocess implementation on a separate temporary copy;
- finally the exact all-target atomic plan proof used by `writeEligibility`.

No target-specific product exception or RPO allowlist may be added.

## 5. TDD sequence

### Slice A — RED/GREEN mechanical projection

Add failing tests for:

- exact add/update/delete mapping;
- explicit no-op coverage;
- deterministic missing-sheet creation from exact family headers;
- refusal on altered key/value/action, unknown family, missing header, non-ready row, duplicate manifest mapping, and target-set drift;
- byte-stable rebuild.

Then implement only the projection helper.

### Slice B — RED/GREEN compiled-ready session path

Add failing session/server tests proving:

- `compiled_ready` builds `pass-c-3` without reading legacy decisions as authority;
- `compiled_with_exceptions` refuses;
- all compiler bindings are present and stale bindings refuse;
- the plan and dry-run build do not mutate the canonical workbook;
- historical `pass-c-2` behavior remains available only for legacy states.

### Slice C — RED/GREEN temporary generation/registry proof

Add failing fixture tests for:

- GSX greenfield + ZR1 reprocess phase;
- ZR1X repeatability phase;
- all-target atomic eligibility;
- target-only temp activation;
- config path override;
- runtime contract and registry loading;
- exact rule/group/exclusive/default/price signature parity;
- mismatch, zero selectable choices, generated validation errors, and discovery failure blocking readiness.

### Slice D — browser contract

Add failing UI/server assertions for the `compiled_ready` plan action, canonical-plan wording, and absence of any live-apply button. Preserve existing strict route payloads.

## 6. Expected files

Implementation:

- `scripts/corvette_form_generator/ingest/wizard/plan_builder.py`
- `scripts/corvette_form_generator/ingest/wizard/session.py`
- `scripts/ingest_wizard_server.py` only if the existing plan route needs a response distinction
- `visualizer/ingest-wizard/index.html`
- `visualizer/ingest-wizard/wizard.js`
- `visualizer/ingest-wizard/wizard.css` only if the added action needs scoped layout support

Tests:

- `tests/test_ingest_wizard_plan.py`
- `tests/test_ingest_wizard_apply.py`
- `tests/test_ingest_wizard_compiler_session.py`
- `tests/test_ingest_wizard_server_milestone2.py` or the existing plan-route server suite
- `tests/test_ingest_wizard_ui_milestone2.py`
- focused generator/registry tests only if a generic seam must be corrected

Docs/closure:

- this plan
- `docs/ingest/README.md`
- `docs/ingest/canonical-row-compiler-exception-queue-design.md`
- `Order-Guide_IngestPrompt.md`
- Milestone 2.4/2.4.1 status owners if the prerequisite verifier passes
- one Fable receipt and `fable5loop/STATE.md` after independent Milestone 3 verification

Expansion into workbook schema, generator business logic, runtime form behavior, or dealer code requires a stop and scope review.

## 7. Acceptance criteria

1. The exact authorized run projects to a valid `pass-c-3` plan with complete manifest/operation/no-op coverage.
2. Projection changes no manifest key, value, stable ID, or source disposition. The approved greenfield-isolation correction may mechanically remap a reviewed Grand Sport X row to an isolated target sheet and convert its physical `noop`/`update` to `add` only when the target sheet is absent; the original manifest action and semantic signature remain in the migration receipt.
3. Reprojection from identical inputs is byte-identical.
4. No legacy broad decision supplies a production row.
5. Every compiler and workbook/source binding is current and fail-closed.
6. Every operation passes exact editor preparation/readback on a temporary workbook.
7. Package, schema, and Boolean-hygiene validation pass on each temporary proof.
8. Grand Sport X and ZR1 pass the first discovery/generation/registry/signature proof.
9. ZR1X passes the same reprocess path separately.
10. The all-target atomic dry-run is `validated_write_eligible` only if every target passes; otherwise it is accurately `validated_write_blocked` with exact evidence.
11. Generated direct-rule, group, exclusive, default, and price signatures equal the target manifest signatures.
12. Customer-selectable choices and target variants are nonempty/exact; generated validation errors are zero.
13. `stingray_master.xlsx`, the raw export, tracked `form-output/`, and `form-app/data.js` remain byte-identical.
14. No `write-approval.json`, live workbook write, publication, promotion, deployment, or dealer change occurs.
15. Browser exposure is review/approval for temporary dry-run evidence only and contains no apply button.
16. Independent exact-current verifier returns PASS against frozen code, tests, plan artifacts, deployment proof, and protected-surface hashes.

## 8. Validation plan

Run targeted RED/GREEN tests first, then:

```sh
PYTHONPATH=scripts .venv/bin/python -m pytest \
  tests/test_ingest_wizard_plan.py \
  tests/test_ingest_wizard_apply.py \
  tests/test_ingest_wizard_compiler_session.py \
  tests/test_ingest_wizard_exception_flow.py \
  tests/test_ingest_wizard_server_milestone2.py \
  tests/test_ingest_wizard_ui_milestone2.py -q
node --check visualizer/ingest-wizard/wizard.js
.venv/bin/python scripts/validate_workbook_package.py stingray_master.xlsx
.venv/bin/python scripts/validate_workbook_schema.py stingray_master.xlsx
```

Then run the complete ingest-wizard Python gate from `README.md`, the relevant serialized generator/registry contract gates, real-run deterministic projection, temporary GSX+ZR1 proof, separate ZR1X proof, all-target atomic dry-run, protected-surface hashes, `git diff --check`, and `.venv/bin/python scripts/validate_fable5_loop.py`.

Generator-writing gates must run serially. Restore only tracked timestamp churn proven absent from the pre-gate snapshot, then rerun protected hashes as a separate failing-fast command.

## 9. Rollback and stop conditions

Rollback is limited to the scoped code/tests/docs and run-scoped Milestone 3 plan/proof artifacts. The canonical workbook needs no rollback because this milestone may not write it.

Stop before continuing when:

- the Milestone 2.4/2.4.1 prerequisite verifier returns BLOCK;
- projection needs to choose or alter product data;
- manifest/header/editor contracts disagree;
- temporary proof produces a generated/runtime mismatch that cannot be fixed generically within the approved surfaces;
- any protected tracked surface changes unexpectedly;
- a new dependency, schema, public runtime contract, promotion action, or live write would be required.

A blocked temporary deployment proof is an honest Milestone 3 result and must be reported with exact evidence; it is not permission to weaken readiness.

## 10. Implementation closeout evidence

The original reviewed manifest encoded Grand Sport X rule families against comparator/shared sheets. Correcting the greenfield family registry exposed 51 fresh diagnostic exceptions because those shared-sheet rows no longer appeared physically present. Under Sean's delegated best-judgment authority, Milestone 3 preserved the reviewed manifest semantics through one bounded projection migration rather than treating the diagnostic recompile as new product authority:

- 369 reviewed Grand Sport X rows were routed to isolated Excel-safe target sheets;
- action transitions were 161 `noop→add`, 186 `add→add`, and 22 `update→add`;
- 116 existing shared-sheet no-ops outside the Grand Sport X option/interior reference domain remained explicit out-of-domain no-op receipts and were not copied;
- non-noop rows outside the target domain fail projection;
- rule groups require a valid target source and member; exclusive groups require at least two valid target members;
- one inactive, unpromoted Grand Sport X `model_registry_promotion` scaffold was added so temporary phased registry proof can exercise the same registry loader without authorizing promotion.

Final plan evidence for run `20260717-091317-470292`, re-verified against the on-disk artifacts and frozen as the one authoritative snapshot (the earlier characterization recorded here predates the final on-disk plan and is superseded):

- canonical-row-manifest.json SHA-256 `b3e32dea5afeaf10eb6296d82283ff844403a80da1f3659b6ad20d5d0409926f`;
- apply-plan.json SHA-256 `0b91bffdfc8643bdbfc31ffcb40695601d6d721ae122652ba95598cad30dd5fe`;
- apply-plan-dryrun.json SHA-256 `097579feaa83ff515fd9edeb132c1aeb4d19440d22ed45a4c30cf0846f3b0a00`;
- compile-report.json SHA-256 `ffa8215adab91d903bed70999b2f3951d291d1946784935714e622cdcf9d4e4d`;
- exception-resolutions.json SHA-256 `c47335d13fccddf0248bb777eba8cb684888f32921daa95c591d3e37e8a09c65`, carrying 158 entries and envelope `queueSubjectFingerprint` `0634e4e0ba2b628e02b88d6325e2ea2aa3d5cfa5eb32aba7e4a69b05f647cf79`;
- 6,408/6,408 manifest rows covered and zero uncovered rows;
- 3,719 plan operations (50 stage-1 and 3,669 stage-2): 2,765 `add`, 945 `update`, and nine `create_sheet`;
- 2,699 explicit no-op receipts;
- nine sheet creations, all Grand Sport X isolated target sheets: `grand_sport_x_exclusive_groups`, `grand_sport_x_exclusive_members`, `grand_sport_x_options`, `grand_sport_x_ovs`, `grand_sport_x_price_rules`, `grand_sport_x_rule_groups`, `grand_sport_x_rule_mapping`, `grand_sport_x_rule_members`, and `grand_sport_x_variant_overrides` (the first eight with scaffold rule `canonical_manifest_missing_sheet`; `grand_sport_x_variant_overrides` with `canonical_manifest_source_sheet`);
- one separately identified non-manifest scaffold, operation `op-03718`: an `add` to sheet `model_registry_promotion` (family `model_registry_promotion`, key `model_key=grand_sport_x`, scaffold rule `pass_c3_greenfield_registry_promotion`, zero manifest refs) whose row carries `promoted_to_runtime=false`, `default_model=false`, `active=false`, `display_order=6`, `artifact_path=form-output/runtime/grand-sport-x-runtime-contract.json`, `artifact_type=runtime_contract`, and notes "Inactive greenfield deployment-proof scaffold.";
- deterministic reprojection is object-identical;
- 3,719/3,719 operations prepared and read back exactly (dry-run `operationCoverage`: raw 3,719, covered 3,719, prepared 3,719).

Final temporary-workbook report SHA-256 `eaf105124604487767f31574739f7b5cd0c5cc18996b8992bec942a1e13685ad` has `write=false`, `status=validated_write_eligible`, and `writeEligibility.eligible=true`. Grand Sport X + ZR1, ZR1X repeatability, and all-target atomic phases all passed with registry loading, zero generated validation errors, zero semantic-signature mismatches, zero deployment blockers, and zero deferrals. The 18 accepted warnings are only the expected inactive target-sheet scaffold warnings.

Parent gates: 254 focused tests plus 18 subtests passed; Node passed 275/275; workbook package/schema validators passed with zero issues; the full Python suite passed 706 tests plus 25 subtests with two skips and the four separately owned failures already recorded in `fable5loop/STATE.md`. Protected workbook, raw source, publication bundle, and live runtime-contract hashes remained unchanged after generated timestamp churn was restored. No `write-approval.json`, live workbook write, runtime publication, model promotion, deployment, or dealer change occurred.

Task 1 snapshot reconciliation was independently verified on 2026-07-18 with
`121 tests and 4 subtests passed`. Full Milestone 3 independent final acceptance
remains open; this Task 1 verification does not authorize or begin Task 2.
