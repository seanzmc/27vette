# Validation Single-Lane and Active-Surface Cleanup Specification

Status: ACTIVE — Passes 0–3 and Pass 4 Stages A–B are complete. Stage B retired exactly the separately approved six-file boundary on 2026-07-29. Stage C remains unstarted and requires separate approval.
Date: 2026-07-23 (revised through 2026-07-29 Stage B closeout)

Consuming workflow: this specification is the structural prerequisite for the database-backed workbook editor described in `docs/superpowers/specs/2026-07-22-reliable-workbook-database-workflow.md`. The end state that both specifications must jointly deliver is one controlled repeatable pathway:

```text
editor user edit
  -> durable draft state
  -> ChangeSet (workbook-changeset-1)
  -> guarded canonical workbook write
  -> workbook package + source/schema validation (real gate)
  -> discover promoted set, generate every promoted model in an isolated candidate root
  -> strict runtime-contract validation
  -> candidate registry + browser proof
  -> explicit publication of form-app/data.js
```

This specification owns everything from the workbook write boundary rightward. The database specification owns everything leftward. Neither may invent a second lane.
Recommended implementation reasoning: high
Branch: `db-workflow`

## 1. Goal

Establish one authoritative path from the canonical workbook to customer runtime, make every readiness gate exercise that path, and remove or archive active-source scripts, tests, generated review artifacts, plans, and guidance that preserve obsolete workbook shapes or workflow routes.

This is a structural correctness and repository-convergence pass. It does not choose product behavior, repair model rules, promote models, publish a registry, deploy, or change dealer submission.

Standing constraints and handoff requirements from `AGENTS.md` apply. This specification adds only pass-specific boundaries and evidence.

## 2. Diagnosis and measured scope

The apparent scale is real but needs classification. File reachability is not viability proof:

- `scripts/` has 74 tracked files, but only 19 are top-level runnable entrypoints; 55 are package files or support modules.
- All 51 non-`__init__` Python modules under `scripts/corvette_form_generator/` have at least one Python importer in the current tree. Some importers are themselves legacy modules or retirement-candidate tests, so this proves only that mass deletion is unsafe—not that all 51 are current authorities.
- A static root-reachability probe found 47 of those 51 modules reachable from at least one then-declared release/write/ingest/report entrypoint. That did not establish necessity: `inspection.py` and `production.py` are release-reachable precisely because `source_assembly.py` retains the model fork under review, while the now-retired ingest route reaches `plan_builder.py` only because `changeset_emitter.py` imports four constants from the historical builder.
- Four modules are reachable from tests but not from any current release/write/ingest/report root: `ingest/candidate_normalizer.py`, `ingest/expert_interpreter.py`, `ingest/model_selection.py`, and `ingest/review_payload.py`. The first three are also reachable from legacy wrappers only. Their importer count is evidence of historical preservation, not current workflow need.
- `tests/` has 76 tracked files. Thirty-one tests/fixtures exist solely for the ingest wizard or its ingest-specific deployment proof and are now retirement candidates; generic ChangeSet/editor/Workbook Manager tests are separate and remain subject to their own viability proof.
- Seven tests invoke generators or registry publication against repository-default paths and can rewrite tracked artifacts; they require isolation before they can be called read-only gates.
- Several tests are not neutral coverage; they currently preserve the gaps being repaired. `test_model_generation_route.py` calls the route unified by searching for facade strings while also requiring `compatibility_artifacts` and `draft_artifacts`, without exercising the branch in `source_assembly.py`. `test_generate_form_model_discovery_cli.py` asserts only Stingray/Grand Sport/Z06 and requires Stingray's legacy JSON/CSV outputs. `test_schema_validation_metadata.py` still constructs `current_generation` and `stingray-form-data.json` freshness scenarios. `z06-runtime-promotion.test.mjs` invokes `generate_registry.py` from an assertion test. These import and pass relationships are evidence of stale-path preservation, not reasons to retain the current test shape.
- `.hermes/plans/` has 29 tracked plans: 12 have explicit completed/implemented top-level status, two are explicitly open, one has an ambiguous implementing status, and 14 have no clear top-level status.
- Three tracked `form-output/inspection/*-derived-swap-manifest.json` files are active derivation checkpoints and must not be mistaken for disposable review clutter.

The problem is not simply file count. It is that active paths do not make authority, lifecycle, side effects, and retirement status mechanically clear.

### 2.1 Confirmed false-confidence paths

1. `scripts/validate_workbook_schema.py stingray_master.xlsx` currently passes with zero issues while a bound isolated probe finds normalized retained-contract differences for five models and a `StaleDerivationAllowlistError` for Z06. §2.1.1 records the exact snapshot and diff categories; the probe does not assume every index difference is a product-semantic change.
2. `scripts/promote_model.py --model grand_sport_x --model zr1 --model zr1x` reports `validated` without generating or runtime-testing the candidate models.
3. `registry_promotion.assert_runtime_contract()` accepts `{}`, `{"dataset": {}}`, and a runtime-active payload containing an error-severity validation record.
4. `model_generation.py` writes a runtime artifact before it enforces the generation validation result; the CLI can return success with an invalid contract.
5. Workbook schema/header authority is duplicated across `workbook_domain/registry.py`, `schema_validation.py`, `registry_promotion.py`, and test-local constants.
6. `tests/test_schema_validation_metadata.py` contains stale price-rule headers that do not match the canonical workbook.
7. `editor_ops._prepare_batch()` checks update columns against physical workbook headers, permitting a rogue physical column outside the shared registry.
8. Current publication and browser switching are internally consistent for Stingray, Grand Sport, and Z06, but that proof is artifact-to-registry, not workbook-to-fresh-artifact continuity.

#### 2.1.1 Bound current-route audit receipt

- Commit: `786e9367d39563c91e6554b5e1d0d5a4b6f5b8bb`
- Workbook SHA-256: `c5f986f6793205e00124db5640248e9e8c57ebb930679a92c2b3e8c56fb62154`
- Probe: copy the workbook into a temporary directory; call `discover_generation_model_configs(temp_workbook)`; immutably rebind each config's `root`, `workbook_path`, `output_dir`, and `app_dir` below that temporary directory; call `assemble_model_source(config)`; compare the returned runtime contract to the corresponding retained contract after recursively ignoring only `generated_at`, `sourceGeneratedAt`, and `generatedAt`.
- Protected-surface result: `git diff --exit-code -- stingray_master.xlsx form-output/runtime form-output/inspection form-app/data.js` returned 0 after the probe.

Per-model normalized result:

| Model | Fresh status | Error findings | Differing top-level collections versus retained contract |
|---|---:|---:|---|
| `grand_sport` | assembled | 0 | `choices` 1002/1428 indices; `rules` 1/124; `sections` 31/37; `steps` 2/14 |
| `grand_sport_x` | assembled | 0 | `choices` 1422/1422; `rules` 92/216; `sections` 31/37; `standardEquipment` 487/487; `steps` 2/14 |
| `stingray` | assembled | 0 | `choices` 1416/1416; `sections` 41 common indices and length 49 vs 51; `standardEquipment` 467/467; `steps` 1/14; `validation` 1/3 |
| `z06` | error | n/a | `StaleDerivationAllowlistError`: `Derivation allowlist pair (z06, opt_pdd_001, opt_cbf_001) is not an includes-closure candidate in the current workbook. Remove or re-approve the stale allowlist entry.` |
| `zr1` | assembled | 0 | `choices` 592/820; `rules` 2/113; `sections` 18 common indices and length 33 vs 32; `standardEquipment` 264/336; `steps` 2/14 |
| `zr1x` | assembled | 0 | `choices` 816/820; `priceRules` 1 common index and length 11 vs 12; `rules` 1/112; `sections` 16/31; `standardEquipment` 340/340; `steps` 2/14; `validation` 1/6 |

These are normalized positional differences, not an approved drift allowlist. Pass 2 must classify differences by stable entity identity before changing source construction or retained artifacts.

### 2.2 Confirmed route split

The public entry and finalizer are shared:

`generate_form.py` → `generate_model_artifacts()` → `build_model_runtime_contract()`.

Source construction is not shared:

- Stingray uses `production.build_production_source_data()` and emits compatibility JSON/CSV.
- The other five active/generatable models build through inspection/preview/draft machinery.
- `current_generation` and `draft_artifact` remain accepted publication types even though current workbook publication rows use `runtime_contract`.

### 2.3 Active guidance drift

- `README.md` documents only `<stingray|grand_sport|z06>` as generation choices although discovery returns six active/generatable models.
- `README.md` calls ZR1/ZR1X source sheets inactive scaffolds and describes a default gate that mixes runtime authority with draft/inspection tests.
- `docs/route-map.md` hardcodes three model choices and says all active promotion rows are runtime contracts even though three active/generatable models remain unpromoted.
- Several completed `.hermes/plans` remain in the active plans directory and still contain commands and artifact names from prior shapes.
- Several source docstrings still describe active models as “draft models” or refer to a distinct “draft artifact path.”

### Pass 0B semantic findings to date

The source-level audit separates current roots from code that is merely reachable:

- Current customer release roots are `generate_form.py`, `generate_registry.py`, and `form-app/app.js` consuming `window.CORVETTE_FORM_DATA`. `promote_model.py` mutates promotion metadata safely, but does not generate candidates, validate contracts strictly, build the complete would-be-published registry, or run browser proof; it is not release-promotion authority.
- Current workbook shape/edit authority is `workbook_domain/registry.py` plus the guarded `editor_ops.apply_batch()` write boundary. `schema_validation.py` remains necessary for cross-row and semantic invariants, but its duplicated headers, required-sheet constants, role types, and artifact vocabulary are misplaced structural authority.
- The raw order-guide ingest wizard/compiler/emitter surface was retired in Pass I. It is not a current root or a candidate implementation dependency.
- `apply_workbook_changeset.py` and `workbook_domain.service` are the implemented generic ChangeSet operator boundary, but no current producer emits that contract after ingest retirement. They remain because the separately approved reliable Workbook Manager specification explicitly adopts them as its Passes 3–7 write contract; this is approved target architecture, not present-use evidence. `apply_workbook_ops.py` and the fallback editor remain transitional until that parity exists.
- The release path is still split: `production.py` independently assembles Stingray while `inspection.py` independently assembles every other model. `source_assembly.py` labels both branches with one facade but does not unify their behavior or workbook snapshot.
- Runtime finalization is inverted: `runtime_contract.py` delegates to `registry_promotion.live_contract_data()`, and the resulting validator checks only known draft-field absence plus a permissive status. Generation writes the artifact before counting error findings.
- Registry freshness is artifact-relative. It can prove `data.js` matches retained artifacts, not that those artifacts were freshly produced from the current workbook.
- Diagnostic behavior leaks into production generation: derived-rule manifests write during normal rule assembly; preview/draft builders construct non-Stingray runtime inputs; source-string and retained-artifact tests can stay green without exercising the intended end-to-end lane.
- Mixed release/editor modules still require symbol-level extraction: `registry_promotion.py`, `rules.py`, and Workbook Manager staging/sync combine current behavior with legacy or transitional behavior. Ingest-specific symbols are not preserved merely because they once appeared reusable; only independently necessary generic workbook-domain behavior may cross the retirement boundary.

This is strong semantic source evidence, but not yet full execution viability. The audit did not execute every CLI/test or characterize every retained `KEEP_*` path in an isolated current-workbook run. Pass 0B therefore remains open until the path ledger records execution or an explicit safe source-only characterization for every retained item.

### 2.4 Pass 0B generation/runtime executable receipt — 2026-07-24

This slice is bound to commit `667aad5fe433e588a7d87fcc31dbbcb476d153e1` and workbook SHA-256 `c5f986f6793205e00124db5640248e9e8c57ebb930679a92c2b3e8c56fb62154`. It used a copied workbook, immutable per-model config rebinding, temporary output/app roots, and no tracked artifact publication.

#### Exact source and path findings

| Surface | Current necessary behavior | Executed/source finding | Revised disposition |
|---|---|---|---|
| `generate_form.py` | Select a workbook-discovered model and invoke generation | The CLI delegates correctly but exposes no workbook or output-root override, so its normal path writes repository outputs and cannot itself provide isolated readiness proof. | `KEEP_CURRENT_AUTHORITY`, but add an explicit generation context/isolated output boundary before treating the CLI as a gate. |
| `model_configs.discover_generation_model_configs()` | Discover the exact active/generatable set and model metadata from a selected workbook | Passing a temporary workbook discovers six models from that copy, but every returned `ModelConfig.workbook_path` still points to the repository workbook. The caller must manually replace `root`, `workbook_path`, `output_dir`, and `app_dir` to get one frozen snapshot. | `KEEP_CURRENT_AUTHORITY`; fix path propagation before route convergence. |
| `model_generation.generate_model_artifacts()` | Orchestrate source assembly and runtime output | A synthetic error-bearing contract was written and returned successfully with `validation_errors: 1`. The runtime file is written before the function counts error findings, and `generate_form.py` does not turn returned validation errors into a nonzero exit. | `KEEP_CURRENT_AUTHORITY`; rewrite as validate-then-atomic-write and fail on any error finding. |
| `source_assembly.assemble_model_source()` | Present one model-neutral assembly API | Execution still branches to `production.build_production_source_data()` for Stingray and inspection/preview/draft construction for the other five models. One facade is not one source builder. | `CONSOLIDATE_INTO_CURRENT_OWNER`; retain only as the future model-neutral boundary. |
| `production.py` | Preserve current Stingray source semantics until parity is proven | It opens module-global `WORKBOOK_PATH`, mutates module-global `MODEL_CONFIG`, later calls helpers with `config.workbook_path`, and writes compatibility outputs through global directories. A mismatched config can therefore address two workbooks in one assembly. | `CONSOLIDATE_INTO_CURRENT_OWNER`; remove globals and migrate necessary Stingray behavior behind explicit context. |
| `inspection.py` | Provide optional inspection/report behavior and currently assemble non-Stingray data | Production source construction remains coupled to preview/draft/report structures. `inspect_model_sources()` runs during every non-Stingray generation even without `--emit-inspection`; it and `build_contract_preview()` open read-only workbooks without deterministic closure. `cleanup_display_text()` also hardcodes a customer-copy correction that belongs in the workbook. | `SPLIT_MIXED_OWNER`; optional reports may remain, but they cannot own runtime input construction, every workbook handle must close deterministically, and the copy fix must move to workbook data rather than a shared builder. |
| `runtime_contract.py` | Finalize and strictly validate a publishable runtime contract | `build_model_runtime_contract()` ignores its `config` argument and delegates finalization back into `registry_promotion.live_contract_data()`. `assert_runtime_contract()` accepted `{}`, `{"dataset": {}}`, and a runtime-active payload containing an error-severity finding; the generated Stingray payload also lacked `dataset.status` and was accepted. | `CONSOLIDATE_INTO_CURRENT_OWNER`; make this module the strict contract/finalization authority, validate model identity from config, and remove the reverse dependency. |
| `generate_registry.py` / artifact registry builder | Publish workbook-selected runtime contracts into `form-app/data.js` | Building from retained repository artifacts succeeded for Stingray, Grand Sport, and Z06. Building the same registry from freshly generated temporary artifacts failed because current-workbook Z06 generation failed. Retained-artifact success therefore does not prove workbook freshness. The current publisher writes `data.js` directly rather than atomically. | `KEEP_CURRENT_AUTHORITY`, but require a complete fresh candidate registry, strict validation, and atomic replacement before publication. |
| `promote_model.py` | Safely edit model activation and registry-selection metadata | Dry-run/preflight verifies workbook row mutations and discovery only, yet reports `status: "validated"`. It does not generate a target, validate a strict contract, build the complete candidate registry, exercise browser/runtime behavior, or run the full workbook schema gate as part of `save_workbook_safely()`. | `REWRITE_CURRENT_LANE`; treat and label this as activation-metadata editing, not promotion-readiness proof, and run the separately required schema gate after an approved write. |
| `registry_promotion.py` | Parse workbook publication rows, load contracts, build registry entries, and parse published data | The module mixes workbook metadata parsing, legacy artifact types, runtime cleanup, permissive validation, artifact loading, and registry construction. | `SPLIT_MIXED_OWNER`; retain workbook publication parsing and registry construction, move strict runtime validation/finalization to `runtime_contract.py`, and retire non-runtime promotable types. |
| `schema_validation.validate_app_registry_freshness()` | Compare the existing published registry with existing selected artifacts | It ignores generated timestamps and detects artifact-to-registry disagreement, but matching stale artifacts and stale registry pass together. | `KEEP_FOCUSED_REGRESSION`; rename/reframe as artifact-to-registry equality and add a separate workbook-to-fresh-candidate gate. |

Function-level closure inside those mixed modules is also required: `production.generate_production_artifacts()` and `production.main()` are superseded dormant routes with no current entry-point caller; `inspection.write_runtime_contract_artifact()` duplicates `model_generation._write_runtime_contract_artifact()` and has no current caller; `registry_promotion.build_registry_from_promotions()` has no production caller and survives only in fixture tests. Classify all four as `RETIRE_DEAD_LEGACY` after exact compatibility/provenance closure and deletion approval. `production.write_stingray_compatibility_artifacts()` remains only as a temporary secondary exporter until the current browser/download consumer is either proven or migrated; it is not source or promotion authority. `inspection.render_contract_preview_markdown()` and `render_form_data_draft_markdown()` also need corrected safety wording because their current claim that generation writes only inspection files is false.

#### Isolated six-model execution

| Model | Fresh isolated result | Runtime result |
|---|---|---|
| `stingray` | generated | Temporary runtime and compatibility artifacts written; zero reported errors, but `dataset.status` was absent. |
| `grand_sport` | generated | Temporary runtime artifact written; zero reported errors. |
| `grand_sport_x` | generated | Temporary runtime artifact written; zero reported errors despite the separate known row-233 option-name quality failure. |
| `z06` | failed before runtime output | `StaleDerivationAllowlistError` for `(z06, opt_pdd_001, opt_cbf_001)`. |
| `zr1` | generated | Temporary runtime artifact written with `runtime_active`; zero reported errors. |
| `zr1x` | generated | Temporary runtime artifact written with `runtime_active`; zero reported errors. |

This proves that workbook discovery currently treats all six models as generatable; the retained CLI test expecting ZR1 rejection is stale. It also proves that generation's own error count is not a complete quality/readiness gate: Grand Sport X can report zero while the separate options-quality gate rejects its source row.

The retained registry built successfully from the three tracked runtime contracts. The equivalent registry build against the isolated candidate root failed on the missing fresh Z06 contract. No browser candidate proof was possible, and the retained registry result cannot substitute for it.

#### Generation/runtime test viability

| Test surface | Actual authority and side effects | Disposition |
|---|---|---|
| `test_generate_form_model_discovery_cli.py` | Invokes the CLI at repository-default paths, rewrites runtime/compatibility artifacts, deletes routine inspection files, hardcodes three models, and expects now-generatable ZR1 to be rejected. | `REWRITE_CURRENT_LANE` around an isolated six-model harness; remove tracked-path mutation and the stale model list. |
| `test_model_generation_route.py` | Reads source strings only. It proves facade spelling/import shape while preserving compatibility/draft keys; it never executes either source branch. | `RETIRE_STALE`; replace only necessary behavior in the isolated executable generation gate. |
| `test_source_assembly_characterization.py` | Reads the live workbook and compares fresh assembly to retained contracts. It is read-only but artifact-relative, and currently fails for both Stingray and Grand Sport section drift (`2 failed`). | `REWRITE_CURRENT_LANE`; compare stable identities under reviewed drift rules in an isolated candidate lane, not positional retained artifacts. |
| `test_runtime_contract_builder.py` | Fixture/source-string focused regression. It proves cleanup behavior but delegates expected behavior to `live_contract_data()` and has no malformed/incomplete/error-bearing rejection cases. | `KEEP_FOCUSED_REGRESSION` plus strict negative contract tests; not a release-readiness gate by itself. |
| `test_registry_promotion_metadata.py` | Uses temporary fixtures safely, but its accepted runtime fixtures are structurally minimal enough to encode the permissive validator. | `KEEP_FOCUSED_REGRESSION`; strengthen fixtures and negative cases with the strict contract. |
| `test_promote_model.py` | Uses fixture/temporary workbooks to prove metadata edits, safe-save behavior, and discovery after activation. It never generates or exercises the planned artifact. | `KEEP_FOCUSED_REGRESSION` for the metadata editor only; remove any promotion-readiness label. |
| `test_schema_validation_metadata.py` | Mostly temporary workbook fixtures; retains local schema/header authority and legacy artifact-freshness shapes. | `REWRITE_CURRENT_LANE` to consume registry metadata and runtime-contract-only publication vocabulary. |
| Grand Sport/Z06 preview and draft Node tests | Request inspection output under `/tmp`, but the invoked CLI still writes repository runtime artifacts first. They protect transitional preview/draft shapes, not the publishable lane. | `OPTIONAL_DIAGNOSTIC` after full output isolation; otherwise retire when inspection stops owning source construction. |
| `z06-runtime-promotion.test.mjs` | Most assertions read the retained published registry; one assertion invokes `generate_registry.py` and rewrites `form-app/data.js`. | Split: `KEEP_CURRENT_PUBLISHED_RUNTIME_GATE` for read-only runtime behavior; `REWRITE_CURRENT_LANE` for isolated publication. |
| `unpublished-runtime-contracts.test.mjs` | Reads retained unpublished GSX/ZR1/ZR1X artifacts only. | `RETIRE_STALE`; migrate an assertion to fresh candidate coverage only if workbook or an approved product source independently establishes that behavior. |
| `multi-model-runtime-switching.test.mjs` | Exercises `app.js` against retained `form-app/data.js` without writes. | `KEEP_CURRENT_PUBLISHED_RUNTIME_GATE`; it proves current published behavior, not workbook freshness. |
| `stingray-generator-stability.test.mjs` | Mixes live workbook assertions, retained output assertions, source-string checks, temporary workbook probes, and legacy compatibility expectations in one large file. | `CONSOLIDATE_INTO_CURRENT_GATE`; split workbook schema, fresh candidate generation, published runtime, and optional compatibility coverage. |

A safe focused Python run of the source-string/runtime-builder/source-assembly/registry/schema group returned `50 passed, 2 failed`; both failures were the retained-contract drift assertions in `test_source_assembly_characterization.py`. A separate temporary-fixture registry/promotion/schema group returned `55 passed`. The green source-string and fixture tests did not offset the drift failures and are not fresh-generation proof.

#### Resulting implementation order

The existing Pass 1 registry-authority proposal is not the first safe implementation pass. Before source unification, promotion changes, or publication, add a smaller fail-closed generation boundary:

1. Introduce one explicit generation context carrying the exact workbook snapshot, root, runtime output directory, optional report directory, and compatibility-output policy. Discovery must return configs bound to that context.
2. Make `runtime_contract.py` own strict required-shape validation, required `dataset.status == runtime_active`, and zero error-severity findings.
3. Validate before writing and publish runtime artifacts atomically; invalid generation writes nothing and exits nonzero.
4. Rewrite the CLI generation gate to execute all workbook-discovered models under a temporary root and assert no tracked changes.
5. Resolve the Z06 stale derivation separately as a model-specific blocker, then obtain a complete six-model candidate result.
6. Before source-builder convergence, explicitly characterize and resolve the two builders' differences in standard-equipment deduplication, hidden/display behavior, variant overrides, invalid-reference filtering, rule assembly, and price validation. Do not choose these semantics in generic code when the workbook can express them.
7. Only then proceed with shared workbook-registry authority, source-builder convergence, complete candidate-registry/browser proof, and atomic registry-publication cleanup as separately reviewed passes.

Pass 0B remains open for the other retained non-ingest surfaces. This receipt authorizes no implementation, workbook change, retained artifact refresh, registry publication, model promotion, or dealer change.

### 2.5 Pass G1 — Fail-closed generation boundary — completed 2026-07-24

Approved outcome: establish the smallest safe generation boundary before source-builder convergence, model-data repair, registry publication, or promotion work.

Implemented:

- `discover_generation_model_configs()` now binds every returned `ModelConfig` to the caller-selected workbook snapshot, root, output directory, and app directory. Runtime publication uses `config.output_dir` rather than reconstructing it from `config.root`, and model keys are validated before source assembly so they cannot escape the selected root. `generate_form.py` exposes `--workbook` and `--output-root`, preserving repository defaults for the release command while making the validation lane isolated.
- Stingray source assembly now opens `config.workbook_path`; both its retained production entrypoint and compatibility JSON/CSV writer use `config.output_dir`. No generation path in this slice addresses the old workbook/output globals.
- `runtime_contract.py` is now the single cleanup and strict-validation owner. It requires a complete dataset identity, `dataset.status == runtime_active`, all runtime collections with their required container and row types, no draft-only fields, and zero error-severity validation findings. Generation also verifies workbook-derived model identity from `ModelConfig`.
- Runtime JSON writes now use same-directory temporary files, flush/fsync, and `os.replace()`. A replacement failure preserves the previous destination and removes the temporary file.
- Derivation-manifest computation is now pure during source assembly. The manifest is retained in the assembly result, stripped from the browser contract, and written atomically only after the contract passes strict validation. Invalid generation therefore writes no runtime, compatibility, inspection, draft, preview, or derivation artifact.
- The executable CLI gate now copies one workbook snapshot, discovers/exercises the exact six current models under one temporary output root, verifies successful contracts, records Z06's existing `StaleDerivationAllowlistError` as the separate known model blocker, and byte-checks that `stingray_master.xlsx`, `form-output/`, and `form-app/data.js` remain unchanged.
- Registry loading consumes the same strict validator, binds `dataset.model` to the workbook promotion label, and rejects artifact paths that resolve outside the selected root. Current retained Stingray publication now fails closed because that retained contract lacks `dataset.model`, `dataset.model_year`, and `dataset.status`; the failed registry command leaves `form-app/data.js` byte-identical.
- `README.md` now owns the exact normal and isolated generation commands and includes the fail-closed generation gate in the Python validation command.

Preserved and excluded:

- No workbook row, generated repository artifact, published registry, promotion metadata, browser runtime, dealer submission boundary, schema, dependency, or deployment path changed.
- Stingray and non-Stingray source builders remain separate. Pass G1 did not choose parity semantics, repair Z06 derivation, repair Grand Sport X row 233, clean orphan rules, refresh retained artifacts, publish a registry, or activate a model.
- Compatibility JSON/CSV remains a secondary Stingray output under the explicit selected output root; its consumer/provenance retirement decision remains later work.

Validation receipt:

- RED/GREEN safety coverage proves explicit config paths, no global Stingray output escape, strict malformed/error-bearing rejection, fail-before-write behavior, pure derivation assembly, and atomic JSON replacement failure handling.
- Focused module compilation passed. The exact README Python generation/metadata gate returned `107 passed, 8 subtests passed`.
- Isolated six-model executable gate: passed; Stingray, Grand Sport, Grand Sport X, ZR1, and ZR1X generated strict contracts; Z06 failed before runtime output with the known stale derivation allowlist error; protected surfaces remained byte-identical.
- Full Python suite: `439 passed, 2 skipped, 7 failed, 15 subtests passed`. The seven failures are the already classified current-workbook/test-authority gaps: four stale editor lint/compare expectations, Grand Sport X row-233 option-name quality, and two retained-artifact-relative source-assembly assertions. No Pass G1 safety or isolated-generation test failed, and the full run left all protected surfaces unchanged.
- Direct retained registry attempt: exited `1` on strict Stingray contract validation; `form-app/data.js` SHA-256 remained `802afa1fea4e9e802f7d82635556c5569d3c73b2f4ae59267f64dd8157f9bceb` before and after.
- Final independent blocking review: `PASS`. It reproduced and confirmed closure of output-root ownership, model-key traversal, promoted-artifact traversal including symlink fallback, validation severity, promotion identity, validation-before-write, and atomic replacement concerns.
- `git diff --check`: passed. Workbook/package/schema writes were not run because the canonical workbook was not modified. Browser candidate proof remains correctly blocked because no complete fresh six-model candidate set exists.

Next bounded pass: Pass G2 should resolve only the current Z06 stale-derivation blocker from authoritative workbook/rule evidence and add its regression proof. It must not unify builders, repair unrelated model data, refresh retained artifacts, or publish the registry. After Z06 is independently green, the next structural gate must compose workbook package/schema and options-quality checks with all-six strict candidate generation before any complete candidate-registry/browser proof.

### 2.6 Pass G2 — Z06 canonical section restoration — completed 2026-07-24

Diagnosis and authority:

- Fresh Z06 assembly omitted active/selectable PDB, PDD, and PDF because `z06_options` rows 242–244 referenced `sec_z06_pkg_001`, which was absent from `section_master`. Rule assembly therefore discarded their authored includes rows as invalid references, and the derivation anti-surprise gate correctly rejected the resulting stale `(z06, opt_pdd_001, opt_cbf_001)` allowlist pair.
- The retained runtime contract was not used as authoring authority. Canonical workbook commit `43b4ecafcda86a658641ee501ca94b307ff93339` and the completed Z06 source specifications establish the exact missing `section_master` row: `Z06 Carbon Fiber Wheel and Brake Packages`, `single_select_opt`, not required, display order 15, `user_selected`, step `wheels`.

Implemented:

- Restored that one exact `section_master` row through `save_workbook_safely()`. Backup: `backups/stingray_master-20260724-155528.xlsx`.
- Removed Z06 from the isolated generation gate's known-blocker exception. Every workbook-discovered model must now generate a strict contract successfully under the isolated output root.
- No option row, rule row, generator implementation, retained runtime/inspection artifact, compatibility artifact, published registry, browser runtime, promotion metadata, or dealer boundary changed.

Validation receipt:

- TDD RED reproduced `StaleDerivationAllowlistError` after removing the test exception; GREEN passed after the canonical row restoration.
- Workbook semantic comparison against the safe-save backup found exactly seven added cells, all fields of the one restored `section_master` row; no existing cell changed. On-disk readback and backup verification passed.
- Workbook package validation: valid, zero issues. Source/schema validation with `--skip-live-contract`: valid, zero issues. The complete schema command remains red only on the already-recorded strict rejection of the retained legacy Stingray contract; G2 intentionally did not refresh or publish retained artifacts.
- Exact README Python generation/metadata gate: `107 passed, 8 subtests passed`. Its isolated six-model test now generated all six strict contracts with no model exception and no tracked output mutation.
- Focused isolated Z06 generation: zero validation errors; all 18 PDB/PDD/PDF choices remained in `sec_z06_pkg_001` under step `wheels`; the exact five approved Z06-to-CBF derived pairs emitted; manifest counts remained 12 candidates, 5 emitted, 0 shadowed, and 6 not emitted.
- Options-quality initially remained red only on the Grand Sport X SWP row-233 name-length finding. The follow-up authority correction below retired that arbitrary limit; the row and its customer-facing copy remain unchanged. `git diff --check` passed.

### 2.7 Option-name quality-authority correction — completed 2026-07-24

- Customer-facing option-name length is not a workbook defect or stable readiness invariant once copy is authored and verified in the frontend. Grand Sport X SWP matches the accepted Grand Sport presentation, and future legitimate copy changes must not be forced through an arbitrary character ceiling.
- Removed `option_name_too_long` and `MAX_OPTION_NAME_LENGTH` from the options-sheet quality evaluator, removed the three now-dead exact-value allowlist entries, and replaced the stale predicate test with explicit coverage that a 200-character authored name is accepted. Generic exact-value allowlist behavior remains covered through `standard_option_nonzero_price`.
- Focused options-quality tests passed: `18 passed`. The canonical workbook options-quality command now passes with zero issues. No workbook row, generated artifact, browser code, registry, or dealer boundary changed for this correction.

Next bounded pass: migrate the retained Stingray runtime contract through the current strict generation path, then compose workbook package/source-schema and options-quality checks with all-six strict candidate generation and candidate-registry/browser proof. Do not hand-edit the retained contract or update only its dataset metadata: isolated comparison shows the fresh contract preserves all 1,416 choice identities and all rules/prices/interiors, but it also applies workbook-authored section metadata changes and removes the empty `sec_perf_support_001` section. Review that bounded drift before promotion and publish the registry only from the complete validated candidate set.

### 2.8 Simplification audit — 2026-07-24

Read-only structural audit of the retained (post-Pass-I) surface, looking only for complexity that can be removed without losing the goal. Findings are ordered by value.

**S1 — Three source payloads are constructed where one is required.** `source_assembly.assemble_model_source()` calls `inspect_model_sources()`, `build_contract_preview()`, and `build_form_data_draft()` for every non-Stingray model on every generation. Only the draft feeds the runtime contract. `model_generation.py:119` then *requires* all three to be non-`None` and reads `report["status"]`, `report["counts"]`, `report["warnings"]`, and eleven `preview`/`draft` counts solely to build the CLI result summary. That summary is derivable from the validated runtime contract. Deriving it from the contract makes report and preview genuinely optional, removes two full workbook reconstructions per model per run, and removes the strongest remaining reason `inspection.py` (1,472 lines) owns production source construction. **Do this before builder convergence; it shrinks what has to converge.**

**S2 — Convergence is cheaper stated as deletion than as merger.** §2.4 and Pass 2 currently frame the work as unifying two builders across sixteen numbered requirements. The simpler equivalent statement: the workbook-driven builder becomes the only builder for all six models, and the preview/draft path stops producing runtime input at all. Stingray's genuinely different semantics are then a bounded list of behaviors to move into the single builder or into workbook data, not a merge negotiation. The characterization work in §2.4 item 6 is still required; only the framing and the requirement count shrink.

**S3 — Workbook Manager catalog duplication is smaller than assumed.** `workbook-manager/backend/app/catalog.py:232` already derives `WRITABLE_SPECS` from registry `WRITABLE_FAMILIES` via `_build_spec()`. Only `_SECTION_SPEC` is hand-authored. Pass 1's Manager scope is therefore one spec plus its tests, not a catalog rewrite. Do not budget a Manager migration pass for this.

**S4 — Manager full-row staging is scheduled for replacement; do not harden it.** `workbook-manager/backend/app/staging.py` (447 lines) and `sync.py:81 sync_workbook(write=True)` implement a direct full-row write path that the database specification's Pass 5 replaces with draft-to-ChangeSet emission. Every hour spent strengthening staging semantics is discarded work. Freeze staging at its current behavior with characterization tests only, and go ChangeSet-first. This removes an entire parallel write lane from the plan rather than migrating it.

**S5 — `validation.py` is a 26-line, two-function module** (`validation_row`, `validation_error_count`) with no independent authority. Fold into `runtime_contract.py` during Pass 2 and delete the module. Trivial, but it is already classified `CONSOLIDATE_INTO_CURRENT_OWNER` and costs nothing.

**S6 — Governance itself is over-complicated.** The completed work spans Passes 0A, 0B, 0C, I, G1, G2, plus a lettered correction, while the remaining work is numbered 1, 2, 3, 4A, 4B, 5, and the database specification adds Passes 1–7. Remaining work in this specification is collapsed to four passes in §4. Do not add further lettered sub-passes; use bounded receipts inside a pass instead.

**S7 — Deliberately not simplified.** `model_config.py` (the `ModelConfig` dataclass) versus `model_configs.py` (workbook discovery) is a genuinely confusing name pair, but renaming touches every importer for readability only. `editor_ops.py` (1,484 lines) and `schema_validation.py` (1,177 lines) are large but are the guarded write boundary and the semantic validator; they are targets for extraction of misplaced *authority* (Pass 1), not for size-driven splitting. `asset_map_sync.py` (1,272 lines) is outside this lane entirely. Record these as non-goals so later passes do not reopen them.

## 3. Authority model after completion

### 3.1 Workbook structure

`scripts/corvette_form_generator/workbook_domain/registry.py` owns managed workbook families, writable columns, keys, types, enum domains, references, optional columns, and requiredness metadata.

`scripts/corvette_form_generator/model_configs.py` owns the required/optional generation source-role contract and derives active/generatable models from workbook metadata.

`schema_validation.py`, editor validation, Workbook Manager catalog/import validation, and fixtures consume those authorities. They do not carry independent header or role lists.

### 3.2 Generation

Every selected model follows one conceptual and executable route:

`stingray_master.xlsx`
→ workbook-discovered `ModelConfig`
→ one model-neutral source assembler
→ strict runtime-contract validation
→ atomic runtime-contract write
→ optional secondary compatibility/report outputs
→ explicit registry publication.

A compatibility artifact may remain only when a current consumer is proven. It cannot be a promotion artifact type, source-construction authority, readiness gate, or registry fallback.

### 3.3 Publication

`runtime_contract` is the only promotable artifact type.

Promotion readiness means:

1. Candidate workbook validates against shared registry metadata.
2. Discover the complete would-be-promoted set from the exact candidate workbook and freshly generate every would-be-published model, including the existing default and unchanged promoted models, in an isolated temporary root.
3. Every generated contract passes the strict runtime contract validator with zero error-severity findings.
4. A complete temporary candidate registry is built from those exact fresh contracts; unchanged published entries are compared semantically and newly promoted targets are reported separately.
5. Browser/runtime tests exercise that candidate registry through a test-harness data-path override; production `form-app/app.js` does not gain a test-only branch.
6. No canonical workbook, tracked runtime artifact, `form-app/data.js`, or dealer endpoint is changed during preflight.

### 3.4 Tests

Tests are classified by authority and side effect:

- Current source/schema gate.
- Current generation/runtime-contract gate.
- Current published-runtime gate.
- Focused behavior regression.
- Optional diagnostic/report test.
- Historical/stale test to rewrite, consolidate, or retire.

No test is part of default readiness solely because it exists. Default tests must be read-only or operate entirely in an isolated temporary root.

### 3.5 Active documentation

- `AGENTS.md` remains the conduct/boundary/validation-strategy owner.
- `README.md` remains the overview, repository map, and exact-command owner.
- `docs/route-map.md` remains a compact current-route explanation only if it adds current architecture detail without duplicating README commands.
- Completed plans leave `.hermes/plans/`; ambiguous plans are classified before move or deletion.
- Historical docs under archive remain unchanged unless an active document points to them as current authority.

### 3.6 Retired ingest boundary

The browser ingest wizard, its compiler/exception/session/ChangeSet-emitter package, raw-ingest helper libraries, ingest-specific deployment proof, UI, tests, and active guidance are removed from the supported workspace. Git history and explicitly archived reports preserve historical evidence; active executable code is not retained as an archive.

The generic `workbook-changeset-1` parser/normalizer, guarded workbook-domain service, `editor_ops.apply_batch()`, and `apply_workbook_changeset.py` remain only because they serve workbook/editor and future Workbook Manager safety independently of ingest. No ingest-produced artifact is required by those owners.

### 3.7 The composed candidate lane

Every piece below already exists or is owned by a pass in this specification, but nothing currently names their composition. The composition is itself a deliverable: one operator-invocable, read-only-by-default command that takes a candidate workbook and returns a pass/fail readiness verdict.

Owner: `scripts/verify_workbook_candidate.py` (new in Pass 3). Exact ordered stages:

1. Accept `--workbook <path>` (default: canonical) and an optional `--changed-model` list. Copy the selected workbook into a temporary candidate root; every later stage reads only that copy.
2. `validate_workbook_package` on the candidate copy. Fail closed.
3. `validate_workbook_schema` on the candidate copy, using the Pass 1 shared-registry authority. Fail closed.
4. `options_sheet_quality` on the candidate copy. Fail closed.
5. `discover_generation_model_configs(candidate_workbook)` bound to the temporary root; determine the complete promoted set plus every active/generatable model.
6. Generate **every** model in that set into the temporary root through the single builder. Changed-model scoping never reduces what is generated; see §3.7.1.
7. Validate every contract through `runtime_contract.assert_runtime_contract()` with config-bound identity. Zero error-severity findings.
8. Build a complete candidate registry from exactly those fresh contracts into the temporary root.
9. Run the browser/runtime harness against the candidate registry via a test-harness data-path override.
10. Emit one machine-readable readiness report (§3.7.1) and exit nonzero on any stage failure.
11. Assert `stingray_master.xlsx`, `form-output/`, and `form-app/data.js` are byte-identical to their pre-run state.

Publication remains a separate explicitly approved command. This verifier never writes a tracked path.

#### 3.7.1 Changed-model scoping is a reporting contract, not a generation filter

The database workflow needs to know which models a ChangeSet touched. That knowledge must not become a generation filter, because a rule, section, price, or global-family row can affect a model other than the one edited.

Required behavior:

1. The caller may supply the touched `model_key` set, derived from the applied ChangeSet's target rows via the shared registry's family-to-model mapping. Rows in global families (`GLOBAL_SHEET_FAMILIES`) mark the touched set as **all models**.
2. Generation, strict validation, and candidate-registry construction always cover the complete promoted plus active/generatable set regardless of that input.
3. The readiness report partitions results into `changed`, `unchanged`, and `unexpected_drift`. A model outside the declared touched set whose fresh contract differs semantically from its retained contract is `unexpected_drift` and fails the run. This is the check that catches a bad global-family edit.
4. The report records, per model: `model_key`, `generated`, `validation_findings`, `contract_sha256`, `declared_changed`, and `semantic_drift_vs_retained`.
5. No stage may use the touched set to skip validation, skip generation, or narrow the registry.

### 3.8 Cross-specification reconciliation

The database specification `docs/superpowers/specs/2026-07-22-reliable-workbook-database-workflow.md` §3.8 instructs its parity helper to validate via `registry_promotion.assert_runtime_contract()`. After Pass G1 the owner is `runtime_contract.assert_runtime_contract()`, and the strict identity checks require the `config` and `expected_model_label` arguments. The old spelling still resolves through a re-export, so a stale call site validates more weakly than intended without failing. That reference is corrected in the database specification; any future change to the validator's owner or signature must update both specifications in the same pass.

Standing rule: `runtime_contract.py` is the only strict runtime-contract validator. No consumer — generation, registry publication, promotion preflight, Workbook Manager parity, or candidate verification — may define, wrap, or weaken a second acceptance check.

## 4. Pass sequence

Each pass is independently reviewable. Do not start the next pass while the preceding pass has unexplained drift or retained red gates.

Remaining work after the completed Passes 0A/0B(partial)/0C/I/G1/G2 is exactly four passes. Per §2.8 S6, do not add lettered sub-passes; record bounded receipts inside a pass instead.

| Pass | Purpose | Unblocks |
|---|---|---|
| 1 | Shared registry becomes the only workbook-shape authority, so post-export validation is a real gate — **completed 2026-07-25** | Safe database→workbook export |
| 2 | One builder for all six models; result summary derived from the contract; `validation.py` folded in | "Single controlled pathway for all models" |
| 3 | Retained Stingray contract migrated; composed candidate verifier (§3.7); promotion/publication prove the candidate | End-to-end database→form runs |
| 4 | Migrate remaining guidance/tests, execute the approved deletion list, archive completed plans | Repository convergence |

Pass 1 landed 2026-07-25. Pass 3's prerequisite landed the same date: the retained runtime contracts were regenerated through the strict path and the registry republished, so the full schema gate is valid with 0 issues and an end-to-end workbook→form run now completes. Pass 2 receipts A (requirements 1, 4 partial, 6, 7) and B (requirements 5 and 9) both landed 2026-07-25. The remaining critical path is **Pass 2 receipt C** — requirements 2, 3, 8, 10, the actual builder convergence — followed by Pass 3 proper. Receipt B also surfaced Python-side values that still decide runtime content. One is a code defect (`contract.label_for()` for interiors) and is folded into receipt C; the rest need canonical workbook writes and are deferred pending separate approval.

### Pass 0A — Freeze the active-surface inventory

Purpose: bind every tracked script, test, active plan, and retained inspection artifact to a disposition before deletion.

Files:

- Modify this specification only: add complete appendices for scripts, tests, plans/guidance, and generated review artifacts.

Required classifications:

Scripts/modules:

- `KEEP_CURRENT_AUTHORITY`
- `KEEP_APPROVED_TARGET_AUTHORITY`
- `KEEP_REUSABLE_REPORT`
- `KEEP_MIGRATION_REPAIR`
- `CONSOLIDATE_INTO_CURRENT_OWNER`
- `RETIRE_ONE_PASS_EXECUTABLE`
- `RETIRE_DEAD_LEGACY`
- `NEEDS_DECISION`

Tests:

- `KEEP_CURRENT_GATE`
- `KEEP_FOCUSED_REGRESSION`
- `REWRITE_TO_CURRENT_LANE`
- `MOVE_TO_OPTIONAL_DIAGNOSTIC`
- `CONSOLIDATE_DUPLICATE`
- `RETIRE_STALE`
- `NEEDS_DECISION`

Docs/artifacts:

- `UPDATE_CURRENT_GUIDANCE`
- `ARCHIVE_COMPLETED_OR_HISTORICAL`
- `DELETE_AFTER_CONSUMER_MIGRATION`
- `KEEP_CURRENT`
- `NEEDS_DECISION`

Rules:

- Text-reference absence is not enough to delete a CLI; inspect imports, `__main__`, tests, README/AGENTS ownership, and safety behavior.
- Do not delete the current guarded entrypoints named in README/AGENTS.
- Do not classify historical archive content as active merely because search finds an old command.
- No path may be deleted while classified `NEEDS_DECISION`.

Pass 0A exit criteria:

- Every one of the 74 tracked script files and 76 tracked test files has one disposition.
- Every top-level runnable script has its current caller/operator and write behavior recorded.
- Every test that can write tracked files is named.
- Every proposed deletion has zero current consumers or a pinned consumer migration in a later pass.
- Exact deletion/rename lists are reviewed before Pass 4.

### Pass 0B — Prove semantic viability from authoritative roots

Purpose: determine whether each retained function and test is necessary to a current supported workflow, rather than treating imports, callers, or green assertions as proof of value.

This is a read-only analysis pass. It modifies only this specification's dispositions and evidence ledger.

The ledger for each path must record: `path`, `authoritative_root`, `call_path_or_invocation`, `necessary_current_behavior`, `actual_inputs`, `outputs_or_side_effects`, `duplicate_or_legacy_owner`, `execution_or_characterization_evidence`, and `revised_disposition`. A blank authoritative root or necessary behavior cannot result in `KEEP_*` merely because another file imports the path.

Authoritative roots to trace separately:

- Customer release: `scripts/generate_form.py`, strict runtime-contract validation, `scripts/promote_model.py`, `scripts/generate_registry.py`, and the browser runtime consuming `form-app/data.js`.
- Workbook mutation/service: `scripts/apply_workbook_changeset.py`, `scripts/apply_workbook_ops.py`, `scripts/repair_workbook_tables.py`, `scripts/sync_asset_map.py`, and `scripts/workbook_editor_server.py`, each subject to its current write guard.
- Retired ingest surface: trace every wizard/compiler/emitter/UI/test/doc consumer only to prove the exact deletion and cross-boundary cleanup set. It is not an authoritative current root and may not justify `KEEP_*`.
- Workbook Manager: current read-only import/catalog/projection behavior only; provisional future writes are not viability evidence.
- Explicit diagnostics/reports: retained only when a current operator command or current gate names the report and its output has a distinct non-authoritative purpose.

Required evidence for every script/module disposition:

1. Name the authoritative root and exact transitive call path that reaches the symbol.
2. Name the current product, operator, safety, migration, or diagnostic behavior that would be lost if it were removed.
3. Identify whether the symbol owns current behavior, adapts another owner, duplicates another implementation, preserves compatibility output, supports diagnostics only, or is reached only through legacy/test code.
4. For reachable legacy branches, determine whether the importer is itself the defect—for example, current generation calling inspection/preview/draft source builders or current ChangeSet code importing historical plan-builder constants.
5. Do not use importer count, README mention, or a passing test as sufficient viability evidence.

Required evidence for every test disposition:

1. Name the current contract the test protects and the authoritative source for that contract.
2. Record the actual input surface: current workbook, freshly assembled runtime contract, retained generated artifact, published registry, fixture-only data, historical preview/draft artifact, or legacy wrapper.
3. Record whether the test is read-only, temp-rooted, or writes a tracked repository path.
4. Identify assertions that preserve stale counts, headers, artifact types, model lists, filenames, preview/draft routes, or side effects.
5. A test may remain focused regression coverage without being part of release readiness; tests that only preserve obsolete behavior must be migrated or retired with that behavior.

Pass 0B exit criteria:

- Every `KEEP_CURRENT_*` script/module has a current authoritative root, named necessary behavior, and no-duplicate-owner finding. `KEEP_APPROVED_TARGET_AUTHORITY` additionally requires an explicit approved owning specification, exact future pass consumer, and no competing contract; future usefulness by itself is insufficient.
- Every `KEEP_*` test identifies a current contract and current input surface; no retained-artifact or fixture-only test is labeled fresh-generation proof.
- Every release-reachable compatibility, inspection, preview, draft, and legacy artifact branch has an explicit converge/retain/retire decision.
- Every test-only or legacy-only module chain has an exact migration or retirement decision.
- Gap-causing importers are classified as defects to remove, not evidence that their callees are viable.
- The Pass 1–5 exact file lists and sequencing are revised from this evidence before implementation approval.

### Pass 0C — Bind the ingest-retirement boundary

Purpose: convert the user's decision not to carry the harmful ingest wizard forward into an exact, independently reviewable deletion and guidance-cleanup set. This remains read-only planning; it does not delete files.

Required work:

1. Treat `changeset_emitter.py` as part of the retired ingest workflow. Do not move its four `plan_builder.py` constants merely to preserve it.
2. Prove that `workbook_domain.changeset`, `workbook_domain.service`, `editor_ops.apply_batch()`, and `apply_workbook_changeset.py` have independently necessary workbook/editor consumers and no runtime dependency on ingest-produced artifacts.
3. Remove the only non-ingest package coupling found so far: `workbook_domain.deployment_proof` imports `canonical_rows.semantic_hash`. Because that proof is target-specific, doc/test-preserved, and has no operator caller outside its own CLI, retire it with `prove_workbook_changeset.py` rather than moving ingest code into the workbook domain.
4. Enumerate every active README, AGENTS, route map, launch configuration, default test command, docs pointer, and UI link that presents ingest as current.
5. Preserve raw source files and ignored local run artifacts as evidence unless separately requested; they do not remain executable authorities.
6. Preserve historical Fable receipts and archived reports as history, but remove active guidance claims and active executable code. Git history—not an active source directory—is the code archive.

Bound active-reference cleanup:

- Remove the two ingest launch entries from `.claude/launch.json`; keep the form-app launch.
- Update `AGENTS.md`, `README.md`, `docs/route-map.md`, and `fable5loop/README.md` so ingest is not a supported workflow or protected live boundary.
- Remove the deployment-proof export from `workbook_domain/__init__.py` and revise `workbook_domain/changeset.py` producer wording so it names Workbook Manager/editor target ownership rather than the retired wizard.
- Replace the `ingest_wizard_fixtures` import in `tests/test_editor_ops_global_families.py` with a registry/editor-owned fixture.
- Archive `docs/c1-review_codex.md`, `docs/c1-review_hermes.md`, `docs/ingest-impl-grade-review.md`, and `docs/workbook-manager-v-editor-v-ingest.md` with the ingest guidance tree.
- Keep `.gitignore` coverage for `form-output/ingest-wizard/` so old local run evidence is not accidentally staged.
- Keep chronological references in `fable5loop/STATE.md`, `fable5loop/runs/**`, and existing archive trees as historical evidence; they must not be linked as current procedure.
- Archive the completed `.hermes/plans/docs-archival-pass4-spec.md` when its active pointers are replaced; do not edit it into a new authority.

Pass 0C exit criteria:

- Exact deletion/rename/archive lists cover the 5 top-level ingest/proof scripts, 25 package files, 3 browser UI files, 31 ingest/proof tests, `Order-Guide_IngestPrompt.md`, and all 36 active `docs/ingest/**/*.md` files.
- `workbook_domain/__init__.py` no longer needs the deployment-proof export after retirement.
- Generic ChangeSet parsing, preview, approval, guarded apply, rollback, and editor integration remain covered without any ingest fixture or import.
- No workbook, generated runtime artifact, registry, dealer surface, ignored ingest run, or raw source evidence file is changed by the retirement pass.

### Pass I — Retire the ingest wizard and ingest-specific proof surface

Approved and completed 2026-07-23 after review of the Pass 0C exact file list. It preceded other cleanup implementation because leaving a known harmful path executable created more risk than preserving sunk cost.

Implementation boundary:

- Delete the 5 top-level and 25 package files classified `RETIRE_INGEST_WORKFLOW` in §9.1.
- Delete `visualizer/ingest-wizard/index.html`, `wizard.css`, and `wizard.js`.
- Delete the 31 ingest/proof tests listed under `RETIRE_STALE` in §9.2; `seat-canonicalization-diff.test.mjs` remains a separate one-pass retirement.
- Remove `prove_changeset_deployment` from `workbook_domain/__init__.py`.
- Rewrite `tests/test_editor_ops_global_families.py` to use an editor/registry-owned minimal workbook fixture; it is the only retained non-ingest test that imports `ingest_wizard_fixtures.py`.
- Archive `Order-Guide_IngestPrompt.md` and the active `docs/ingest/` tree under one clearly retired archive location, preserving git rename history where practical.
- Update `AGENTS.md`, `README.md`, `docs/route-map.md`, launch surfaces, and test-command documentation so no current workflow points to the retired server, UI, compiler, emitter, profiler, or proof CLI.
- Keep `workbook_domain/changeset.py`, `workbook_domain/service.py`, `editor_ops.py`, `apply_workbook_changeset.py`, and their non-ingest tests. These own generic workbook-change safety, not raw ingest.
- Record those ChangeSet owners as the approved target contract for Workbook Manager Passes 3–7, not as proof that a current non-ingest producer already exists. The manager's owning specification at `docs/superpowers/specs/2026-07-22-reliable-workbook-database-workflow.md` explicitly adopts that contract.

Validation:

1. Static import/reference scan finds no active references to the retired scripts, package, UI, proof module, tests, or docs paths.
2. Python test collection succeeds without ingest modules or fixtures.
3. Focused generic ChangeSet, editor, registry, Workbook Manager read-only, workbook package, and workbook schema gates pass.
4. README/AGENTS/route-map consistency review reports no supported raw-ingest command.
5. Protected workbook/generated/registry/dealer surfaces remain byte-clean.

Pass I receipt — completed 2026-07-23:

- Removed all 5 top-level ingest/proof scripts, all 25 ingest/proof package files, all 3 browser UI files, and all 31 ingest/proof tests/fixtures named in the approved boundary.
- Archived `Order-Guide_IngestPrompt.md`, all 36 `docs/ingest/**/*.md` files, four active ingest review reports, and the completed docs-archival plan under explicit archive paths. Added `docs/archive/retired-ingest/2026-07-23/README.md` to prevent archived instructions from appearing current.
- Removed the deployment-proof export, changed the generic ChangeSet owner text to Workbook Manager target infrastructure, and replaced the retained editor test's ingest fixture with `tests/workbook_domain_fixtures.py`.
- Updated `AGENTS.md`, `README.md`, `docs/route-map.md`, `.claude/launch.json`, Fable guidance/state, and the reliable Workbook Manager specification. Active static reference scanning found no imports or executable pointers to removed paths; remaining active mentions explicitly identify the workflow as retired, while Fable receipts remain chronological evidence under a superseding correction.
- `compileall` passed; pytest collection found 435 tests; focused generic ChangeSet/editor/registry tests passed `68`; Workbook Manager tests passed `56` with `2` skipped; workbook package and schema validation both reported zero issues; Fable loop validation and launch JSON parsing passed.
- Full pytest executed: `423 passed, 2 skipped, 10 failed`. All ten failures are pre-existing non-ingest workbook/generation characterization gaps already identified by Pass 0B: four editor-lint/compare expectations, three Z06 stale-derivation generation failures, one stale inactive-ZR1 expectation, the GSX row-233 option-name quality finding, and one Stingray source-assembly characterization mismatch. No failure imports or calls a retired ingest surface.
- Generation tests rewrote retained artifacts during the full run as previously characterized; all test-generated runtime/compatibility artifacts and the untracked ZR1 diagnostic manifest were restored/removed. Final protected-surface diff for `stingray_master.xlsx`, `form-output/`, and `form-app/data.js` is clean.
- No workbook write, publication, promotion, dealer, ignored ingest-run, or raw-source evidence change occurred. Pass 0B remains open and Pass 1 remains unapproved.

### Pass 1 — Make the shared registry the workbook validation authority

Purpose: remove parallel workbook-shape ownership and make validators fail when all source sheets drift together.

This is the post-export gate for the database workflow. Scope note from §2.8 S3: `catalog.py` already derives its writable specs from registry families; only `_SECTION_SPEC` is hand-authored, so the Workbook Manager side of this pass is one spec plus its tests.

Exact files:

- Modify `scripts/corvette_form_generator/workbook_domain/registry.py`
- Modify `scripts/corvette_form_generator/schema_validation.py`
- Modify `scripts/corvette_form_generator/registry_promotion.py`
- Modify `scripts/corvette_form_generator/editor_ops.py`
- Modify `workbook-manager/backend/app/catalog.py` only if its adapter must consume added registry fields; no independent metadata is permitted.
- Modify `tests/test_workbook_domain_registry.py`
- Modify `tests/test_schema_validation_metadata.py`
- Modify `tests/test_editor_ops_meta.py`
- Modify `tests/test_editor_ops_apply.py`
- Modify `tests/test_editor_ops_global_families.py` only if registry-derived global-family expectations change.
- Modify `tests/test_registry_promotion_metadata.py` only if registry ownership/import expectations change.
- Modify `tests/test_promote_model.py` only if promotion parsing behavior changes rather than only the constant owner.
- Modify `tests/workbook-schema-standardization.test.mjs` to remove independently owned structural header/model-state contracts after migrating durable checks to Python registry/schema owners.
- Modify `tests/test_workbook_manager_catalog.py` only for registry-derived parity.
- Modify `tests/test_workbook_manager_import_projection.py` only for registry-derived projection parity.
- Modify this specification for the Pass 1 receipt.

Required behavior:

1. Replace duplicated `MODEL_MASTER_HEADERS`, `MODEL_REGISTRY_PROMOTION_HEADERS`, role header contracts, artifact-type domains, and applicable type maps with imports/adapters over the shared registry.
2. Keep `REQUIRED_GENERATION_SOURCE_ROLES` and `OPTIONAL_GENERATION_SOURCE_ROLES` as the generation-role authority.
3. Require canonical columns for every active registered family; cross-sheet equality alone is insufficient.
4. Reject writes to physical columns outside the family registry, even when such a column exists in Excel.
5. Keep opaque/read-only columns importable only when explicitly classified; never make them writable by physical existence.
6. Replace hand-authored stale test headers with registry-derived fixtures.
7. Add adversarial tests proving coordinated all-sheet drift fails.
8. Prove the export gate on a mutated candidate copy, never on the canonical workbook. Required RED cases, each of which must fail `validate_workbook_schema.py`: an added physical column outside the family registry; a removed canonical column present in the registry; a renamed header matching the old spelling in every sheet at once; a reference value pointing at an absent key; and a write attempt through `editor_ops._prepare_batch()` targeting the rogue physical column.
9. Derive `catalog.py`'s remaining hand-authored `_SECTION_SPEC` from the shared registry, or record why the registry cannot express it. No new independent Manager metadata is permitted either way.
10. Add the registry's family-to-model mapping helper required by §3.7.1 changed-model derivation: given a set of `(family, sheet, model_key)` write targets, return the touched model set, returning all models for any global-family target. Cover the global-family case explicitly.

Stop conditions:

- Any current workbook column required by an active consumer but absent from the shared registry.
- Any change that would require inventing a new workbook column or product rule.
- Any write-path behavior change outside column/schema enforcement.

Pass 1 gates:

```sh
.venv/bin/python -m pytest \
  tests/test_workbook_domain_registry.py \
  tests/test_schema_validation_metadata.py \
  tests/test_editor_ops_meta.py \
  tests/test_editor_ops_apply.py \
  tests/test_editor_ops_global_families.py \
  tests/test_registry_promotion_metadata.py \
  tests/test_promote_model.py \
  tests/test_workbook_manager_catalog.py \
  tests/test_workbook_manager_import_projection.py \
  tests/test_workbook_manager.py -q
.venv/bin/python scripts/validate_workbook_package.py stingray_master.xlsx
.venv/bin/python scripts/validate_workbook_schema.py stingray_master.xlsx
node --test tests/workbook-schema-standardization.test.mjs
git diff --check
```

#### Pass 1 receipt — completed 2026-07-25

Bound to commit `d5db8bb7744097078fb0ef84b8df772fbc2e1f6f`, workbook SHA-256 `8858cff40ea7eaeda6b7921714f3697a6ee9d1bbc99c84e564d7b118e45b2166`.

Diagnosis confirmed by RED before any implementation:

- Renaming `option_name` in **every** active options sheet at once produced **zero** schema issues. Cross-sheet header equality cannot see coordinated drift, because the compared sheets still agree with each other.
- A write to a column that exists physically in Excel but is not owned by the family produced **zero** editor errors.

Implemented:

- `workbook_domain/registry.py` gained `REGISTRY_PROMOTION_ARTIFACT_TYPES`, the `model_registry_promotion.artifact_type` enum, a read-only `sections` family (`READONLY_SHEET_META`), `active_model_keys()`, and `models_for_write_targets()` for §3.7.1.
- `schema_validation.py` and `registry_promotion.py` no longer hold header, setup-copy, or artifact-type lists; all derive from the registry.
- New checks: `registry_family_columns_missing`, `registry_family_columns_unregistered`, and `registry_promotion_blank_artifact_type`. The last one exists because the write path now requires `artifact_type` on any effective-active row; without it, a blank export would validate green and then be rejected by the editor.
- `editor_ops._prepare_batch()` rejects writes to physical columns outside the family registry, in addition to the existing physical-header check.
- `workbook-manager/backend/app/catalog.py` derives `_SECTION_SPEC` from `READONLY_SHEET_META`; no hand-authored column metadata remains in the Manager.
- `workbook_domain/__init__.py` loads the guarded write service lazily to break the `registry_promotion → workbook_domain → service → editor_ops → schema_validation → registry_promotion` cycle.

Validation receipt:

- Canonical workbook required **no** change: an openpyxl probe over all 72 registered sheets found 0 missing and 0 extra columns, and all six promotion rows already carry `artifact_type=runtime_contract`.
- `validate_workbook_package.py`: valid, 0 issues. `validate_workbook_schema.py --skip-live-contract`: valid, 0 issues.
- The full schema command remains red only on the already-recorded strict rejection of the retained Stingray runtime contract. That is the Pass 3 prerequisite, not a Pass 1 regression.
- Pass 1 focused gate: `209 passed, 2 skipped, 7 subtests`. Full Python suite: `454 passed, 2 skipped`, with the same pre-existing failures (four editor lint/compare, two retained-artifact source-assembly). Both `workbook-schema-standardization.test.mjs` failures reproduce identically with the change stashed.
- Protected surfaces byte-clean; `git diff --check` clean.
- Independent verifier, cycle 1: **FAIL** on one real defect — `models_for_write_targets()` early-returned the global set and therefore *narrowed* when a global target followed a source-sheet target owned by a model inactive in `model_master`. Fixed by unioning at the end over both activeness sources; the regression test asserts the subset relation rather than an exact set.
- Independent verifier, cycle 2: **PASS** on all twelve rubric criteria. It re-graded the fix by brute force rather than by example — three adversarial extracts × every target subset of size ≤4, asserting `union(singles) ⊆ result`, with zero violations, including a hostile model that owns an active source sheet but appears nowhere in `model_master`. It also proved the lazy-import fix raises `AttributeError`/`ImportError` rather than recursing, under a reduced recursion limit and in both attribute orders.
- Cycle 2 left one non-blocking residual, closed immediately after: `registry_promotion_unknown_artifact_type` was still inside the promoted-only loop, so an active non-promoted row with a garbage artifact type validated green while the write path rejected it. The membership check now runs in the same pre-loop as the blank check for every active row, and the duplicate copy in the promoted loop was removed. Final focused gate `212 passed, 2 skipped`; full suite `455 passed, 2 skipped` with the same six pre-existing failures.

Scope note: the column gate covers writable registered families only. The read-only `sections` family is registered for Manager projection but not gated, because fixture and canonical `section_master` shapes differ in ways Pass 1 was not authorized to decide.

Not changed: no workbook row, generated artifact, published registry, promotion metadata, browser runtime, or dealer boundary. Source builders remain split (Pass 2). The retained Stingray contract was not regenerated (Pass 3).

### Pass 2 — Validate before writing and converge source assembly

Purpose: make fresh generation the authoritative form-generation proof and remove the model-based source-construction fork without mixing product-data repair into structural work.

Exact files:

- Modify `scripts/generate_form.py`
- Modify `scripts/corvette_form_generator/model_generation.py`
- Modify `scripts/corvette_form_generator/model_configs.py`
- Modify `scripts/corvette_form_generator/source_assembly.py`
- Modify `scripts/corvette_form_generator/runtime_contract.py`
- Modify `scripts/corvette_form_generator/production.py`
- Modify `scripts/corvette_form_generator/inspection.py`
- Modify `scripts/corvette_form_generator/validation.py`
- Modify `scripts/corvette_form_generator/rules.py`
- Modify `scripts/corvette_form_generator/rule_derivation.py`
- Modify `tests/test_generate_form_model_discovery_cli.py`
- Modify `tests/test_model_config_metadata.py`
- Modify `tests/test_model_generation_route.py`
- Modify `tests/test_source_assembly_characterization.py`
- Modify `tests/test_runtime_contract_builder.py`
- Modify `tests/test_rule_derivation.py`
- Create `tests/test_all_model_runtime_generation.py`
- Modify this specification for the Pass 2 receipt.

Already delivered by Passes G1/G2 and not repeated here: the strict validator, validate-before-write, atomic writes, nonzero CLI status, candidate-bound `ModelConfig` paths, pure derivation manifests, the isolated six-model gate, and Z06 green. Passes 2A/2B are collapsed; the sequencing they encoded is now the ordering of the requirements below.

Required behavior, in order:

1. **Cut the summary's dependency on report and preview first (§2.8 S1).** Derive `generate_model_artifacts()`'s result summary from the validated runtime contract instead of `assembly.report` and `assembly.preview`. Then stop constructing report and preview during normal generation; they are produced only on explicit request. This removes two workbook reconstructions per model per run and must land before any builder change.
2. **State convergence as deletion, not merger (§2.8 S2).** The workbook-driven builder becomes the only source builder for all six models. `build_form_data_draft()` and `build_contract_preview()` stop producing runtime input. `production.build_production_source_data()` is absorbed; `production.py` retains no mutable module globals (`MODEL_CONFIG`, `WORKBOOK_PATH`, `ROOT`, `OUTPUT_DIR`, `APP_DIR`) on any path that survives.
3. Before that absorption, characterize and resolve the two builders' differences in standard-equipment deduplication, hidden/display behavior, variant overrides, invalid-reference filtering, rule assembly, and price validation. Prefer expressing each difference in workbook data over encoding it in generic code. Do not hide differences behind count-only assertions.
4. The single builder operates on one loaded, frozen workbook snapshot. Optional inspection/report output consumes that in-memory result; it never reopens or reconstructs the workbook. Every workbook handle closes deterministically.
5. ~~Move `cleanup_display_text()`'s hardcoded customer-copy correction into workbook data.~~ **Corrected 2026-07-25 (receipt B): there was nothing to move.** The function fired on 0 of 2,248 calls across all six models — every one of its five transforms was inert — so it was deleted outright. Measure reachability before assuming a hardcoded value is load-bearing.
6. Move runtime cleanup/finalization out of `registry_promotion.live_contract_data()` into `runtime_contract.py`; promotion consumes and validates a completed contract rather than owning generation transformation.
7. Fold `validation.py`'s two helpers into `runtime_contract.py` and delete the module (§2.8 S5).
8. Preserve Stingray compatibility JSON/CSV only as secondary outputs while current consumers remain; compare JSON with `compare-generated-contracts.mjs` and CSV byte-for-byte.
9. Require complete workbook-owned generation/runtime metadata for every active/generatable model. Python defaults may support isolated fixtures or explicit compatibility diagnostics only; readiness fails rather than silently filling missing active-model step, section, context, summary, source-role, or required presentation metadata.
10. Exercise all workbook-discovered active/generatable models through the same executable test harness, and require a six-model-green assertion. Pass 2 is not complete, and Pass 3 cannot start, until that assertion passes.

Strict runtime-contract rejection matrix:

- Empty payload or missing/non-object `dataset`.
- Missing/blank `dataset.name`, `dataset.model`, `dataset.model_year`, or `dataset.source_workbook`; bind model/registry-key identity externally to the requested model config, promotion row, and exact artifact path rather than inventing a second key field unless separately approved.
- Dataset status other than `runtime_active`, including draft/inspection status or provenance.
- Missing, duplicate, unexpected, or wrongly counted variants relative to the workbook-discovered model variants.
- Missing or non-list required runtime collections: `variants`, `steps`, `sections`, `contextChoices`, `choices`, `standardEquipment`, `ruleGroups`, `exclusiveGroups`, `rules`, `priceRules`, `interiors`, `colorOverrides`, `defaultSelectionRules`, and `validation`; require a structurally valid `orderSummary` object; require model-specific collections such as `runtimeRuleExceptions` only when declared by canonical metadata.
- Malformed validation rows lacking valid severity/check/entity/message fields.
- Any error-severity validation finding.
- Draft/inspection metadata or an artifact/workbook/model binding that does not match the candidate snapshot.

Generation and publication must call the same validator; no second weaker assertion is permitted.

Baseline rule:

Do not use stale checked-in runtime contracts as the sole before-state. Capture fresh current-route outputs in an isolated root. If the current route cannot generate a model, record the exact blocker and stop that model's route migration; do not repair workbook business rules inside this pass.

Known current blocker and sequencing boundary:

- Resolved. Pass G2 restored the canonical `section_master` row for `sec_z06_pkg_001`, and the isolated gate now generates all six models with no model exception. Pass 2 therefore starts from a six-model-green snapshot and must require it, not reintroduce the exception. If a rebase reopens this failure, stop and treat it as a separate authorized source pass rather than suppressing it in generic generation code.

Pass 2 gates:

```sh
.venv/bin/python -m py_compile \
  scripts/generate_form.py \
  scripts/corvette_form_generator/model_generation.py \
  scripts/corvette_form_generator/source_assembly.py \
  scripts/corvette_form_generator/runtime_contract.py \
  scripts/corvette_form_generator/production.py \
  scripts/corvette_form_generator/inspection.py
PYTHONPATH=scripts .venv/bin/python -m pytest \
  tests/test_generate_form_model_discovery_cli.py \
  tests/test_model_config_metadata.py \
  tests/test_model_generation_route.py \
  tests/test_source_assembly_characterization.py \
  tests/test_runtime_contract_builder.py \
  tests/test_rule_derivation.py \
  tests/test_all_model_runtime_generation.py -q
```

Additional proof:

- Generate every discoverable model into one isolated temporary root.
- Assert no tracked workbook/artifact/registry change.
- Compare current-route and unified-route contracts with `scripts/compare-generated-contracts.mjs` where parity is required.
- Compare preserved compatibility JSON with the same comparator and CSV byte-for-byte.
- Review every non-timestamp difference; no blanket allowlist.

#### Pass 2 receipt A — requirements 1, 4 (partial), 6, 7 completed 2026-07-25

Bound to base commit `ed3692a` and workbook SHA-256 `8858cff4…5b2166`. Receipt:
`fable5loop/runs/2026-07-25-pass2-summary-and-snapshot-authority/`. Independent verifier: **PASS**.

**Requirement 1 (§2.8 S1) — done.** `_compatibility_result()` and `_reviewable_result()` are replaced
by one `_summary_from_runtime_contract()`. Counts are the validated contract's own collection
lengths over `REQUIRED_RUNTIME_LIST_FIELDS`, so the summary cannot disagree with the artifact it
describes, and every model reports the same shape. `assemble_model_source()` gained
`include_reports=`; `inspect_model_sources()` no longer runs during normal generation. Traced at the
`openpyxl.load_workbook` call site, workbook opens per non-Stingray model went **4 → 2** (0.67-0.71s
→ 0.54-0.62s); `--emit-inspection` went 4 → 3. The predicted "two workbook reconstructions per model
per run" is confirmed and removed.

**Requirement 4 — partial, and the remainder is recorded as open.** Each of the three inspection
builders now loads the workbook once inside a `try/finally`. The verifier found a genuine
pre-existing leak in the process: `inspect_model_sources()` and `build_contract_preview()` never
closed their handles at all, on success or failure. Both are fixed, with
`test_workbook_handles_close_when_a_builder_raises` injecting a `RuntimeError` into each builder.
**Still open:** a non-Stingray assembly opens two workbooks (three with `--emit-inspection`), so
"one loaded, frozen workbook snapshot" per *assembly*, and "optional report output never reopens the
workbook", are not met. They need requirement 2's single builder and belong to receipt B.

**Requirement 6 — already satisfied.** `live_contract_data()` was already defined in
`runtime_contract.py` at `ed3692a`, with `registry_promotion.py` consuming it. No change was needed;
this corrects the §2.4 disposition, which still described the reverse dependency.

**Requirement 7 (§2.8 S5) — done with one deviation.** `validation_error_count` folded into
`runtime_contract.py`; `validation.py` deleted. `validation_row` was **deleted rather than ported** —
`git grep` at `ed3692a` confirms zero callers. Porting dead code into the module this pass makes
authoritative would work against the pass.

**Proof.** All 44 generated artifacts across all six discoverable models (6 runtime contracts, 30
review files, 6 derived-swap manifests, 2 Stingray compatibility files) are byte-identical to the
`ed3692a` baseline apart from one `generated_at` line each. The verifier regenerated both sides
itself from a `git worktree` of `ed3692a` rather than trusting the maker's numbers. Pass 2 gate set
went 55 → 60 passing with the same single pre-existing failure. Full Python suite and all 16 node
gates unchanged. Full `validate_workbook_schema.py` remains valid, 0 issues. No workbook, generated
artifact, registry, or dealer write.

**Recorded, not fixed.** `validation_errors` in the summary is now structurally always `0` —
`assert_runtime_contract()` raises before a nonzero value could be printed — so it must not be cited
as evidence of a clean run. `warnings` is no longer on normal-generation stdout, and
`validation_warnings` counts contract rows rather than draft rows (z06: 1 → 0), which is a value
change rather than a relocation.

**Receipt B is next and owns requirements 2, 3, 5, 8, 9, 10.**
`tests/test_source_assembly_characterization.py::test_shared_assembler_preserves_stingray_runtime_drift_surfaces`
(`display_behavior` present on `opt_uqt_002` choices) is a live instance of exactly the
builder divergence requirement 3 must characterize. Resolve it there; do not suppress it.

#### Pass 2 receipt B — requirements 5 and 9 completed 2026-07-25

Bound to base commit `bdf6690` and workbook SHA-256 `8858cff4…5b2166`. Receipt:
`fable5loop/runs/2026-07-25-pass2-shadow-authority-purge/`. Independent verifier: **FAIL on both
cycles**, all findings fixed and re-validated; no cycle-3 verification was run.

Reordered ahead of requirements 2/3 at the user's direction, under one standing rule that now
governs this lane: **the workbook is the only authority for anything a workbook column can express.**
What the user sees in the workbook or the Workbook Manager is what ships. A Python constant, override
map, default, name heuristic, or text rewrite that can change a workbook-authored value is a defect,
because it makes the shipped runtime impossible to predict from the source of truth.

**Method.** Every candidate on the generation lane was measured by instrumenting the real call path
against the canonical workbook for all six active/generatable models. Zero hits → deleted, with the
44 byte-identical artifacts as the proof it was inert. Non-zero hits → reported as a workbook defect,
not fixed in Python.

**Requirement 5 — done, and larger than the spec assumed.** `cleanup_display_text()` did not need its
hardcoded `"New Ground effects"` correction *moved* to the workbook: the entire function fired on
**0 of 2,248** calls. All five transforms were inert and are deleted. The spec text said "move into
workbook data"; there was nothing to move.

**Requirement 9 — done, and stronger than written.** Missing presentation metadata now fails for
every active/generatable model, not only promoted ones. The promoted-only completeness check against
the Python `STEP_ORDER` tuple is replaced by a workbook-derived one: step keys referenced by the
model's own `section_presentation`, `context_section_master`, and `step_order_summary_map` rows,
unioned with steps any other active model authors. Dropping any one of a model's 14 steps now fails
for all six models — 84 of 84 cases, versus 14/14 promoted and 0/14 unpromoted at baseline.

**Also deleted** (all zero-hit): `SECTION_STEP_OVERRIDES` (24 entries), `STANDARD_SECTIONS` (8), the
section-name substring heuristic, `STATUS_ALIASES`, `_LEGACY_RULE_PHRASE_FALLBACKS` and
`load_rule_phrase_map` (zero callers; the `rule_phrase_map` sheet already authors all six rows), the
`runtime_steps`/`context_section_master` Python fallbacks, the rule-derived z25 interior set, the
`or set(STANDARD_SECTIONS)` and `or trim.replace("_R6X","")` fallbacks, and the `step_order`,
`step_labels`, `context_sections`, `standard_sections`, `section_step_overrides`, and `text_cleanup`
`ModelConfig` fields. Net **−221 lines** of generator code.

**Verifier cycles.** Cycle 1 proved the replacement completeness check was *weaker* than the Python
list it replaced — `section_presentation` authors zero `step_key` values, so it saw 2 of 14 keys and
z06's `summary` could be dropped silently — and that the accompanying test had been shaped to the
implementation. Cycle 2 proved the fix used an intersection across peers, defeated by dropping a step
from two models or by one `active=False` cell, and found a label/exemption set conflation plus a new
blank-`step_label` fallback shipping raw snake_case keys as customer-visible labels. All fixed.

**Python-side values that still decide runtime content, with the 2026-07-25 disposition:**

| Python-side value | Scale | Actually rendered? | Disposition |
|---|---|---|---|
| `contract.label_for()` for interiors | 21 strings | Yes | **Defect — folded into receipt C.** See below. |
| `production.py` composes `disabled_reason` | 298 composed / 56 authored across the 3 published models (excludes 131, includes 125, requires 42) | Only when the rule fires against current selections — an "Unavailable" pill (`app.js:1999`), an eviction toast (`:1620`), or auto-add/requirement copy (`:853`, `:870`). Not ambient. | Optional authoring pass over the 131 excludes, at the user's discretion. No obligation; the generic sentence is accurate. |
| `mapping.status_to_label` display strings | 867 tooltips, not the 1,434 first reported | Only as a tooltip fallback when a choice has no `description`, and `descriptiveTooltipText` (`app.js:331`) discards `"Available"` — so only `Standard` (720) and `Not Available` (147) ever render | Deferred. A new sheet to own three cells is the wrong shape; the 867 affected choices have no description at all, which is a content question rather than a schema one. |
| `SELECTION_MODE_LABELS` | 4 strings | Yes — `app.js:2009` | Deferred; needs a new column. |
| `BODY_STYLE_DISPLAY_ORDER` | 2 entries | Ordering only | Deferred; needs a new column. |
| `presentation_bool(..., default=False)` | 11/57 and 51/57 blank cells | Bucket membership | Deferred; columns exist, so this is a data fill plus making the default fail-closed. |
| `STEP_LABELS["standard_equipment"]` | 48 | No — lands in `sections[].step_label`, which nothing reads | Deferred; lowest value. |

**`contract.label_for()` interior defect — folded into receipt C.** For an option it returns
`f"{rpo} {label}"`, which is correct because the RPO is customer-facing. For an interior it returns
`f"{interior_id} {interior_name}"`, leaking the internal key: *"Included with 3LT_AE4_HUF_N26 Natural
Dipped Suede."* All 21 occurrences are `includes` rules; zero are excludes.

`form-app/app.js` already does this correctly — `getInteriorCustomerLabel()` (`app.js:832`) prefers
`interior_leaf_label || interior_name`. But the browser reads `rule.disabled_reason || <compose>`, so
the baked Python string **overrides** the correct label the browser would have produced. Fixing
`label_for` therefore also removes a third authority: the same sentence is composed in Python at
generation time and in JavaScript at render time. Receipt C must reconcile both, and the 21 changed
strings need review before publication because they alter customer-visible copy.

**Deliberately kept**, because they are generation *logic* rather than shadowed values, and belong to
requirement 3's characterization: `production.standard_equipment_preference`'s hardcoded
`sec_stan_002` ranking, and `interiors.py`'s `opt_z25_001` (the comparison value is workbook-owned;
only the constant and the field name are Python — renaming the field is a runtime-contract shape
change that touches `app.js`).

**Open.** One disclosed hole: dropping a step from *every* active model passes, because the
cross-model union has nothing left to compare against. `summary` is the only exposed key.

**Receipt C is next and owns requirements 2, 3, 8, 10** — the builder convergence — plus the
`contract.label_for()` interior defect above, folded in at the user's direction 2026-07-25.

#### Pass 2 receipt C — requirements 2 and 3 completed 2026-07-26

Base `993d920`, committed `8c005a8`. Receipt: `fable5loop/runs/2026-07-26-pass2-builder-characterization/`.
Independent verifier: **FAIL on completeness, PASS on every behavioral claim** — all findings fixed,
no code rolled back.

**Requirement 2 — done.** `assemble_model_source()` has no model-keyed source fork; one builder
assembles all six models. `production.py` went 731 → 62 lines and retains no mutable module globals
and no workbook access — it is the Stingray compatibility JSON/CSV export only. Workbook opens for a
six-model run: **13 → 7**, one frozen snapshot per assembly, closed deterministically including on
exception paths. This also completes requirement 4, left partial by receipt A.

**Requirement 3 — done, via a read-only ledger first.** Every difference between the builders traced
to one cause: the retired builder shipped rows referencing entities outside Stingray's scope.
Standard-equipment deduplication, price validation and variant overrides had **zero** difference;
`display_behavior` differed only as absent-vs-empty. The user approved dropping the dangling rows and
chose "omit when blank" for `display_behavior`.

**Folded-in fix.** `contract.label_for()` named interiors by internal key and, because the browser
prefers a baked `disabled_reason` over its own composition, that string overrode the correct label.
71 composed reasons corrected across five models; z06's 22 are workbook-authored and untouched.

**What the verifier caught.** Because this receipt could not be proved by byte-identity, its whole
burden was delta completeness — and eight published deltas were unlisted, including
`rules.source_selection_mode`, which stage 1 had explicitly flagged as an open item for stage 2. Two
receipt statements were false. A *passing* test assertion (`requires_z25 not in row`) was deleted
along with the file and not replaced. All eight deltas proved browser-inert and all eight align
Stingray with the field set the other five models already shipped; that shared shape is now pinned by
`test_every_model_ships_the_same_contract_shape`.

**Open.** Three of the retired builder's conditional validation checks have no equivalent; the new
builder filters dangling rules where the old one flagged them, which is a change in reporting as well
as payload.

**Not published.** Requirements 8 and 10 and the republication of `form-app/data.js` remain.

#### Pass 2 receipt D — requirements 8 and 10 completed 2026-07-26; Pass 2 complete

**Requirement 10.** `tests/test_all_model_runtime_generation.py` is the six-model executable gate.
Every model the workbook activates is generated through `scripts/generate_form.py` — the real
operator entrypoint, as a subprocess — into one isolated `--output-root`. Each written artifact is
then re-read from disk and passed through `runtime_contract.assert_runtime_contract()` bound to its
config: the same validator generation uses, no second weaker check. The set is asserted from both
directions, because neither alone is sufficient — against `model_master` read directly from the
workbook, which catches a discovery regression, and against the six named keys, which catches a model
leaving the workbook and shrinking the gate's own coverage with it. The three per-model parametrized
tests are pinned to the named keys for the same reason. Variant counts and uniqueness are checked
against `model_master.expected_variant_count`; `dataset.source_workbook` is checked against the
snapshot; every protected surface is SHA-256 hashed before and after and asserted unchanged. A
negative proof pins the strict validator's necessity: a payload with `runtime_active` status and zero
error-severity rows — which the previous gate accepted — is rejected for empty `steps` and a missing
`orderSummary`.

The duplicate six-model loop in `tests/test_generate_form_model_discovery_cli.py` was removed;
requirement 10 asks for one harness, not two. That file now covers CLI-argument behavior only:
`--output-root` confinement over the whole write set, unknown model, and the `--inspection-output`
guard. The Pass 2 gate command block above runs green as written for the first time — the block
previously failed at collection because `tests/test_all_model_runtime_generation.py` did not exist.
104 passed / 88 subtests.

**Requirement 8.** Parity of the compatibility export against the collapsed builder is clean:
regenerating Stingray from the unchanged canonical workbook into an isolated root gives
`compare-generated-contracts.mjs` exit 0 and a byte-identical CSV. Zero non-timestamp differences, no
allowlist. The isolated snapshot must keep the canonical filename or `dataset.source_workbook` alone
manufactures one spurious difference.

Consumer disposition, corrected during the run. A filename grep is not a sufficient consumer scan
here: `registry_promotion.current_generation_artifact_path()` constructs
`form-output/{export_slug}-form-data.json` by f-string, so it is a real reader that no search for
that string finds. It is reached from `generate_registry.py:49` whenever a promotion row declares
`artifact_type=current_generation`. Resolving all six `model_registry_promotion` rows through the real
resolver shows every one declares `runtime_contract` with an explicit `artifact_path`, so nothing
resolves to the compatibility JSON today — but the branch is live code, not documentation.

- `stingray-form-data.json` — **retained.** One test consumer
  (`tests/stingray-generator-stability.test.mjs:25`) plus the dormant registry fallback above.
  Deletion is blocked until Pass 3 requirement 7 removes `current_generation` as an accepted
  artifact type.
- `stingray-form-data.csv` — **retained, zero consumers.** No reader, no constructed path, no code
  branch. Recorded as an explicit Pass 4 Stage B deletion candidate; Stage B owns approved deletion.

**Found and recorded, not fixed here.** `assert_runtime_contract()` does not implement two clauses of
the rejection matrix above. Probed with the real config against a real contract: dropping a variant,
duplicating a variant, renaming a `variant_id`, dropping a choice, and a wrong `dataset.source_workbook`
are all accepted. The gate compensates for both today, but the validator should own them. Separately,
`registry_promotion.promotion_requires_runtime_contract_assertion()` returns False for
`current_generation` — a switch that skips the strict assertion, which §3.8's standing rule forbids —
and has **zero callers**. Both belong to Pass 3 requirement 7.

**Independent verifier: PASS with should-fix**, all fixed. It reproduced every number and found no
false claim, but proved by workbook mutation that the discovery comparison could not fail on any
workbook change while its docstring claimed otherwise, and that named membership — one of eleven
assertions in the removed CLI loop, and the only one not carried over — had been silently dropped.
Two receipt phrasings were imprecise. Receipt:
`fable5loop/runs/2026-07-26-pass2-compat-scope-and-six-model-gate/`.

**Boundaries.** Tests only. No generator source changed, no workbook write, nothing published;
`stingray_master.xlsx` SHA-256 unchanged. Python 523 passed (baseline 501); all 16 node gates at
baseline, with the three known failures unchanged (two Pass 4A grand-sport tests, one
`active explicit excludes`).

**Pass 2 is complete.** The requirement-10 six-model-green assertion passes, so Pass 3 may start.

### Pass 3 — Make promotion and publication prove the candidate runtime

Purpose: prevent a candidate from being called validated until its exact runtime contracts and temporary registry have passed, and deliver the composed candidate lane the database workflow calls.

**Prerequisite receipt — completed 2026-07-25.** The three promoted models were regenerated through the strict path (`generate_form.py`, `validation_errors: 0` each) and the registry republished. Drift was reviewed first in an isolated `--output-root` and is exactly one workbook-authored section change the artifacts predated: `sec_perf_support_001` → `sec_perf_001` ("Mechanical") moving from step `wheels` to `packages_performance` (12 choices per model for grand_sport/z06, 1 rule's `source_section`; Stingray had zero rows there); two section renames (`sec_perf_z52_001` "Z52 Packages" → "Performance Packages" with order 10→11, and the inert `sec_z06_cf_whee_001` "…Wheel Selection" → "…Wheel Packages"); nine display-order changes (`sec_spec_001` 110→5, `sec_incl_001` 10→15, `sec_3lte_001` 30→25, `sec_susp_001` 20→25, `sec_stan_001` 20→30, `sec_exha_001` 40→35, `sec_stan_002` 10→35, `sec_safe_001` 30→40, `sec_tech_001` 40→45); and the Stingray `dataset` gaining `model`/`model_year`/`status`. Zero choices, standard equipment, rules, prices, or interiors were added or removed for any model; Stingray's large `choices` diff is array order only. `sec_perf_support_001` has zero references anywhere in the workbook. The full schema gate went from 1 error to **valid, 0 issues**, and `workbook-schema-standardization` improved 7/2 → 8/1. Browser/runtime gates all pass: multi-model switching 48, stingray regression 90, z06 promotion 5, z06 package interactions 21, z06 rule corrections 15, z06 interior cleanup 7, nonruntime purge 6, unpublished contracts 2, generator stability 15, visual copy 8. The canonical workbook was not modified. Independent verifier: **PASS**; it proved byte-reproducibility of all three published artifacts from the unchanged workbook in a temporary root, reproduced the prior failure from `HEAD` artifacts to confirm the stated root cause, and proved the order-only claim by multiset equality of serialized payloads rather than a per-id compare. It corrected two understatements in the first receipt (the second rename and four omitted display-order changes), now fixed above. Receipt: `fable5loop/runs/2026-07-25-promoted-artifact-refresh/`.

Two staleness items the verifier surfaced, neither a regression, both feeding later passes: the unpromoted `grand-sport-x`, `zr1`, and `zr1x` retained contracts still reference the removed `sec_perf_support_001` and no gate flags them — the same class as the original blocker, which is precisely why §3.7 requires the candidate lane to generate the **complete** promoted-plus-generatable set rather than only published models. And `tests/grand-sport-contract-preview.test.mjs:67-68` and `tests/grand-sport-draft-data.test.mjs:826-827` assert on that removed section while invoking `generate_form.py` without `--output-root`; Pass 4A already owns retargeting and isolating them.

The remaining Pass 3 work — promotion preflight and `verify_workbook_candidate.py` — is unchanged and still open.

Original diagnosis (resolved above): the retained Stingray runtime contract failed strict validation because it lacked `dataset.model`, `dataset.model_year`, and `dataset.status`, so `generate_registry.py` exited nonzero and `form-app/data.js` could not be rebuilt. The prescribed remedy — regenerate through the strict path rather than hand-edit the artifact, review the bounded drift first, then publish — was followed exactly.

Exact files:

- Create `scripts/verify_workbook_candidate.py` per §3.7
- Create `tests/test_verify_workbook_candidate.py`
- Modify `scripts/promote_model.py`
- Modify `scripts/generate_registry.py`
- Modify `scripts/corvette_form_generator/registry_promotion.py`
- Modify `scripts/corvette_form_generator/schema_validation.py`
- Modify `tests/test_promote_model.py`
- Modify `tests/test_registry_promotion_metadata.py`
- Modify `tests/test_schema_validation_metadata.py`
- Modify `tests/z06-runtime-promotion.test.mjs`
- Modify `tests/multi-model-runtime-switching.test.mjs`
- Modify `tests/unpublished-runtime-contracts.test.mjs`
- Modify this specification for the Pass 3 receipt.

Required behavior:

1. Promotion preflight discovers the complete post-promotion promoted set from the exact scratch candidate workbook and generates every would-be-published model—not only newly targeted models—into an isolated root.
2. It validates each exact runtime contract through the Pass 2 validator.
3. It builds a complete temporary candidate registry from those contracts, preserving exactly one promoted default and reporting semantic drift for existing published entries separately from new targets.
4. It runs registry identity/default/selection checks and customer-runtime model switching against that temporary registry by pointing the existing Node harness at a temporary `data.js` path.
5. Preflight never mutates the canonical workbook, tracked runtime artifacts, or `form-app/data.js`.
6. Split `z06-runtime-promotion.test.mjs` so read-only assertions do not run `generate_registry.py` against the tracked app.
7. After fixture, active-code, active-doc, and external/operator compatibility closure is recorded, restrict promotion artifact metadata to `runtime_contract` and remove acceptance/production consumers of `current_generation` and `draft_artifact`. If external compatibility remains, stop for a separate explicit decision rather than silently preserving the fallback as release authority.
8. Remove `build_registry_from_promotions()` and old artifact-resolution fallbacks after the consumer scan is empty.
9. `generate_registry.py` remains the only real `form-app/data.js` writer and operates only after separately approved promotion/artifact changes. Its write becomes atomic.
10. Implement `scripts/verify_workbook_candidate.py` as the single composed entrypoint defined in §3.7, including the §3.7.1 changed-model reporting contract. Promotion preflight and the database workflow's post-export gate both call this one command; neither reimplements the stage sequence.
11. Emit the readiness report as JSON to a caller-selected path, with a stable schema version. The database workflow consumes this report; it does not scrape console output.
12. The verifier's own test proves: all stages run in order against a candidate copy; a workbook defect fails at the earliest applicable stage; an undeclared model's semantic drift is reported as `unexpected_drift` and fails; a declared changed model does not reduce the generated set; and the canonical workbook, `form-output/`, and `form-app/data.js` are byte-identical afterward.

#### Pass 3 receipt — stage 1: requirements 1–6 and 10–12 completed 2026-07-27

**Pass 3 is NOT complete.** Requirements 7, 8, and 9 are open and are listed again below.

`scripts/verify_workbook_candidate.py` is the composed lane of §3.7: one operator-invocable command
that copies the candidate workbook into a temporary root and runs ten stages in order —
`copy_candidate`, `workbook_package`, `workbook_schema`, `options_sheet_quality`, `discover_models`,
`generate_models`, `validate_contracts`, `candidate_registry`, `browser_harness`, `semantic_drift` —
failing closed at the earliest stage that can see a defect. Stages after a failure genuinely do not
run: a deleted `section_master` stops at `workbook_schema` with `generate_models` in `stagesNotRun`
and `models` empty. A caller-skipped stage is reported separately from an unreached one.

Requirements 1–5 are delivered through `promote_model.py`, which now calls the lane on the exact
post-promotion scratch workbook before the canonical write, declaring the promoted models changed.
`--model z06` now exits 1 with `candidate_lane_failed` where the same command on `HEAD` reported
`validated` — the §2.1 item 2 false-confidence path, closed. An exception escaping the lane aborts
before `save_workbook_safely` rather than writing.

Requirement 6 is delivered: the one assertion that ran `generate_registry.py` against the tracked app
moved to `tests/z06-registry-publication.test.mjs`. `tests/z06-runtime-promotion.test.mjs` is now
read-only — 4/0, and running it no longer dirties `form-app/data.js`.

Requirement 11's readiness report is versioned JSON (`workbook-candidate-readiness-1`) at a
caller-selected path, carrying per model exactly the §3.7.1.4 field set. §3.7.1's scoping contract is
enforced, not merely intended: the declared set is read at one site plus report assembly, and a run
declaring one model generates, validates, and registers the identical set as a run declaring none.
`'*'` marks every model touched. Drift is keyed on stable entity identity, falls back to a
content-sensitive multiset when that identity is not unique, and recurses into nested lists, so a
section reorder is not drift while a duplicated row is.

**The lane's first real run found something no gate had caught.** With nothing declared changed it
exits 1 on `unexpected_drift` for `grand_sport_x`, `zr1`, and `zr1x`, whose retained contracts differ
from fresh generation in `choices`, `rules`, `sections`, `standardEquipment`, and `steps`. That is the
staleness §Pass 3's prerequisite receipt recorded as unflagged precisely because those models are
unpublished — which is why §3.7 requires generating the complete promoted-plus-generatable set. Any
promotion is blocked until those three are regenerated or explicitly declared.

Requirement 4's harness override is `CORVETTE_FORM_DATA_JS`, read by
`tests/multi-model-runtime-switching.test.mjs` with **no fallback** when set. Independently measured:
env unset 48/48, empty registry 0/48, nonexistent path 0/48, byte-identical copy 48/48, copy missing
`z06` 42/6. A silent fallback would have let stage 9 pass while proving nothing about the candidate.

**Independent verifier: FAIL on cycle 1**, six findings, all fixed and re-proved. Requirement 6 was
inside the claimed scope, undelivered, and its damage misattributed to Pass 4A. Stage 10 ran after a
stage-7 failure. The byte-identity assertion did not cover exception or interrupt paths. Two of
requirement 12's proofs caught nothing — against a weakened lane, hardcoding `boundaryViolations` and
deleting stage 9 outright were both invisible, because every assertion only ever observed the check
passing and every test disabled the browser stage for speed. Drift collapsed duplicate identities and
compared `orderSummary.sections` positionally. One duplicate acceptance check was unreachable. The
verifier confirmed under adversarial testing that scoping never narrows, the harness has no fallback,
promotion is genuinely gated, and the drift failure is real rather than synthetic. Receipt:
`fable5loop/runs/2026-07-26-pass3-candidate-lane/`.

**Still open in Pass 3:** requirement 7 (restrict promotion artifact metadata; remove the
`current_generation` and `draft_artifact` consumers), requirement 8 (remove
`build_registry_from_promotions()` and the artifact-resolution fallbacks), requirement 9 (atomic
`generate_registry.py` write, which is also what will let `z06-registry-publication.test.mjs` stop
rewriting a tracked artifact). Two findings from Pass 2 receipt D feed requirement 7 directly:
`promotion_requires_runtime_contract_assertion()` is a zero-caller switch that skips the strict
assertion, and `assert_runtime_contract()` still does not implement the rejection matrix's variant and
workbook-binding clauses.

**Boundaries.** No workbook write, no model promoted, nothing published; `stingray_master.xlsx`,
`form-output/`, and `form-app/data.js` byte-identical throughout. Python 542 passed (baseline 523);
all 16 node gates at baseline.

#### Pass 3 receipt — stage 2: requirement 9 completed 2026-07-27

**Pass 3 is still NOT complete.** Requirements 7 and 8 remain open.

`write_app_data_registry()` was a bare `path.write_text()`. It now routes through a
shared `write_text_atomic()` that stages a temp file beside the target, fsyncs the
payload, sets the destination's own mode, `os.replace()`s, and fsyncs the parent
directory. `write_json_output()` already had the staging pattern and now shares the
same helper. `generate_registry.py` gained `--workbook` / `--root` / `--output`;
`--root` moves both sides at once, so a caller cannot read a candidate's contracts
and publish them over the tracked app by forgetting a flag, and an empty `--root`
fails closed rather than falling back to the repository.

**The practical payoff is measured, not asserted.** `tests/z06-registry-publication.test.mjs`
now publishes to a temporary path, so hashing `form-app/data.js` around all 17
`tests/*.test.mjs` files gives an identical digest. The same gate at `HEAD` in a
detached worktree does rewrite it. Running the gates no longer dirties the
published registry. The two runtime contracts still churn — five node files invoke
`generate_form.py` without `--output-root` (`grand-sport-contract-preview`,
`grand-sport-draft-data`, `z06-contract-preview`, `z06-form-data-draft`,
`z06-interior-accessory-cleanup`) — which is Pass 4A's scope.

Atomicity is proven by failure injection, not by reading the code: an `OSError`
raised inside `os.replace` — after the temp file is complete, before it lands —
leaves the destination byte-identical with no temp file remaining. Five weakened
builds are each caught by at least one test: plain `write_text`, staging in the
system temp directory, fsync removed, chmod removed, and the stale-temp sweep
removed. The first version of the suite caught only the first two.

**Independent verifier: FAIL on cycle 1**, ten findings, all fixed. The important
one was a regression the change introduced: `os.replace` swaps the inode, so the
destination inherited `tempfile`'s 0600 and `form-app/data.js` silently went from
0644 to 0600 — invisible to git, and surfacing only on the machine that publishes.
Also fixed: no directory fsync (so the rename was not durable); a fsync no test
covered; SIGKILL debris nothing reaped; two near-vacuous tests; a misattribution of
the remaining gate churn; and a wrong claim, repeated in three places, that a
cross-filesystem `os.replace` silently copies — it raises `EXDEV`. The verifier
independently confirmed the isolation flags, the byte-identity of the default path,
that no second writer of `form-app/data.js` exists (including constructed paths and
the editor server), and that the candidate lane's stage-8 registry still lands
inside its temporary root. Receipt: `fable5loop/runs/2026-07-27-pass3-atomic-registry-write/`.

**Boundaries.** No workbook write, no model promoted, nothing published;
`stingray_master.xlsx` and `form-app/data.js` byte-identical, and the registry's
file mode preserved. Python 555 passed / 0 failed; all 17 node gates at baseline.

#### Pass 3 receipt — stage 3: requirements 7 and 8 completed 2026-07-27; **Pass 3 complete**

**The closure first, because requirement 7 gates the deletion on it.** Every consumer of
`current_generation`, `draft_artifact`, and `build_registry_from_promotions()` was enumerated and
classified. Active code: ten sites across `registry_promotion.py`, `schema_validation.py`, and the
shared vocabulary. Fixtures: three test modules, updated rather than deleted. Active docs: none
instructing use of either type; the one non-archive mention outside this spec is the database
workflow spec's §407, which lists both among shapes that must be "a blocking preflight error, never a
silently excluded row" — consistent with the narrowing. **External/operator: none.** No form-app code
references `artifact_type`; the editor's dropdown derives from `REGISTRY_PROMOTION_ARTIFACT_TYPES`
through `workbook_editor_server.py` to `editor.js` with no hardcoded list anywhere in the chain; and
all six canonical promotion rows already declare `runtime_contract` with an explicit `artifact_path`.
Requirement 7's stop condition was therefore never triggered.

`REGISTRY_PROMOTION_ARTIFACT_TYPES` is now `("runtime_contract",)`. A blank `artifact_type` means
`runtime_contract` instead of `draft_artifact` — a review artifact was previously promoted to
production by omission. `artifact_path` is unconditionally required. Deleted:
`current_generation_artifact_path()`, `promotion_requires_runtime_contract_assertion()` (already
zero-caller), `load_promotion_data()`, and `build_registry_from_promotions()`.
`registry_promotion.py` went 312 → 251 lines. `artifact_path_for_promotion()` survives with two real
callers and no branch — it is now the single place a promoted row becomes a file.

Every retargeted test was audited assertion by assertion rather than rewritten. The verifier
AST-enumerated all 33 assertions in the prior version: the two retargeted tests are byte-identical in
all 18 of their assertion expressions, and the only genuinely deleted assertion —
`assertIsNone(build_registry_from_promotions(...))` — is replaced by a stronger one, since the
surviving builder raises on an empty promotion set rather than answering `None`. New coverage names
both retired types explicitly at both layers, because the pre-existing "unknown type" test would keep
passing if either were put back in the vocabulary.

**Independent verifier: PASS with should-fix**, six findings, all fixed. The important one corrected a
false claim in the receipt itself: the removed `!= "current_generation"` artifact-path exemption was
described as untestable, which held for `registry_promotion.py` — where the vocabulary check raises
first — but not for `schema_validation.py`, which accumulates issues and continues. The exemption was
live there, and restoring it silently dropped `registry_promotion_missing_artifact_path` while every
test stayed green. Now covered by a test proven to fail against the restored exemption. Also fixed: a
docstring claiming a breaker it does not catch, an overstated C4, a stale docstring describing the
deleted registry fallback, and two rejection messages that did not name the allowed set. Receipt:
`fable5loop/runs/2026-07-27-pass3-promotion-type-closure/`.

**This lifts the block on `form-output/stingray-form-data.json`.** Pass 2 receipt D retained it partly
because the `current_generation` fallback could resolve to it. That fallback is gone, so the JSON has
one consumer left (`tests/stingray-generator-stability.test.mjs:25`) and no code path; with the
zero-consumer CSV, both are now unblocked Pass 4 Stage B deletion candidates. Neither is deleted here.

**Boundaries.** No workbook write, no model promoted, nothing published; `stingray_master.xlsx`,
`form-output/`, and `form-app/data.js` byte-identical. Python 558 passed; all 17 node gates at
baseline, with `form-app/data.js` still unchanged by the full set.

**Pass 3 is complete.** Pass 4 inherits: retargeting the five node files that invoke
`generate_form.py` without `--output-root` (the last tracked-artifact churn), the approved deletion
list, and `assert_runtime_contract()`'s unimplemented variant and workbook-binding rejection clauses.

Pass 3 gates:

- Focused Python promotion/registry/schema tests.
- Candidate-registry Node tests in a temporary root.
- Existing published three-model switching test unchanged unless publication is separately approved.
- Final `git diff --quiet -- form-app/data.js form-output/runtime stingray_master.xlsx` for preflight-only work.

### Pass 4 — Migrate consumers/guidance, then retire stale executable surfaces

Purpose: first move current behavior, provenance, tests, and active guidance to authoritative owners; only then delete the exact separately approved zero-consumer list.

Pass 4 runs as three ordered stages in one pass. Former Pass 5 is Stage C; it is no longer a separate pass. References elsewhere in this document to "Pass 4A", "Pass 4B", and "Pass 5" mean Stages A, B, and C.

#### Stage A (formerly Pass 4A) — Consumer, provenance, test, and guidance migration

Pinned active-guidance owners:

- Modify `README.md`
- Modify `docs/route-map.md`
- Modify `AGENTS.md` only if its durable class-level boundaries require a pointer correction beyond the ingest retirement already completed in Pass I; do not duplicate README commands.
- Modify `docs/superpowers/specs/2026-07-22-reliable-workbook-database-workflow.md` only where it names retired artifact types or stale validator behavior.
- Update the stale source docstrings/comments listed under `UPDATE_CURRENT_GUIDANCE` in §9.3 in their owning earlier pass or in Pass 4A if still present; do not mix behavior changes into comment cleanup.

Initial rewrite/consolidation set already supported by audit evidence:

- Rewrite `tests/test_generate_form_model_discovery_cli.py` to discover and exercise every workbook-generatable model (six in the bound snapshot) without an inactive-ZR1 assertion or a permanent six-model literal.
- Replace `tests/test_model_generation_route.py` source-string assertions with executable call-path and isolated-filesystem proof that every discovered model uses the same canonical builder and output contract.
- Rewrite `tests/test_runtime_contract_builder.py` from self-referential `live_contract_data()` equality/source-string checks to explicit expected contracts and malformed/error-contract rejection cases.
- Rewrite `tests/test_registry_promotion_metadata.py` to remove `current_generation`, `draft_artifact`, header-only fallback, and obsolete `build_registry_from_promotions()` coverage after compatibility closure; retain ordering/default/setup-copy/duplicate-key behavior against strict runtime contracts.
- Rewrite `tests/test_schema_validation_metadata.py` fixtures from the shared registry.
- Rewrite `tests/workbook-schema-standardization.test.mjs` to consume registry/source-role metadata rather than hardcoded three-model/future-model structures. **Completed 2026-07-28** — see the Stage A slice receipt below.
- Split/rewrite `tests/stingray-generator-stability.test.mjs`: retain package-integrity and focused workbook invariants, but move retained-artifact counts and JSON-to-published-registry checks out of fresh-generation authority.
- Rewrite/split `tests/z06-runtime-promotion.test.mjs` into explicit publication and read-only verification surfaces.
- Move unique runtime assertions out of `tests/grand-sport-contract-preview.test.mjs`, `tests/grand-sport-draft-data.test.mjs`, `tests/z06-contract-preview.test.mjs`, and `tests/z06-form-data-draft.test.mjs`; then delete or reclassify those files as optional diagnostics.
- Update `tests/z06-interior-accessory-cleanup.test.mjs` to consume current runtime-contract data rather than a draft artifact.
- Replace `editor_ops.py` hardcoded post-write reminder commands that point at draft/preview-era tests with current gate ownership from README.
- Keep Workbook Manager staging/sync tests as labeled characterization/recovery coverage only until the reliable-workflow ChangeSet migration replaces those semantics; do not promote direct full-row staging or `sync_workbook(write=True)` into current Manager authority merely because scratch tests reach them.

Required README result:

- One parameterized current model-generation command driven by workbook discovery.
- One exact gate matrix separated into source/schema, generation/runtime contract, candidate verification (§3.7), publication, browser/runtime, optional diagnostics, editor/manager, and Fable surfaces. No ingest row: that workflow is retired.
- Every default command is read-only or explicitly temp-rooted.
- No “all tests” formulation that mixes publication writers and optional diagnostic suites.
- Promotion instructions name candidate generation/runtime proof as part of preflight.

Required route-map result:

- No hardcoded three-model generation list.
- Clear distinction between active/generatable and promoted/published.
- No claim that all active models are promoted.
- No legacy artifact type as a supported route.
- No completed migration edge presented as active architecture.

Pass 4A exit criteria:

- Every proposed Pass 4B deletion has zero current code, test, active-doc, current-provenance, or operator-command consumer.
- Current guidance names only the post-migration path and remains accurate before deletion.
- Re-run the bound inventory and publish the exact Pass 4B `git rm` list for separate approval.

#### Stage A slice receipt — `workbook-schema-standardization`, completed 2026-07-28

**Scope deviation, approved in-session.** §6 of this specification withholds workbook-write and publication authority. Sean granted both explicitly ("You may edit the workbook to fix the grand sport rows when you get to a logical point to do so") after the diagnosis below. The write and republish are recorded here rather than in a separate spec because they are the direct remedy for the defect this gate exposed.

**The baseline failure was a live bug, not a stale expectation.** The retired gate's one known failure — `active explicit excludes`, carried since 2026-07-26 — was flagging `gs_rule_opt_5zv_001_excludes_opt_t0f_001`, an explicit `excludes` between two members of the active `gs_excl_performance_aero` group (`required_single_within_group`). It is not redundant decoration: `app.js` skips same-group peers in the loop over rules that TARGET a choice (`:1101`) but not in the loop over rules the choice is the SOURCE of (`:1122`), so the row disables one direction of the swap. Measured against the published registry, Grand Sport coupe 1LT — select FEB + J57 + T0F, click 5ZV, aero stays T0F; delete the row, the same click swaps. It read as inert under casual checking because T0F is normally gated behind `Requires FEB … or FEY` and the FEY path blocks 5ZV for an unrelated reason.

Generation had already marked the row `active: "False"` / `omit_redundant_same_section_exclude`. Neither field is consulted on that path, so the marking suppressed nothing. Confirmed by isolating the input: forcing `active: "True"`, and dropping 5ZV from the group, each left behavior unchanged; only deleting the rule row changed it.

**The hardcoded gate saw one instance; the registry-derived sweep found nine.** 1 `grand_sport` (published), 2 `grand_sport_x`, 3 `zr1`, 3 `zr1x`. The other eight were invisible to the browser only because those three models are unpromoted. All nine deleted via `apply_workbook_ops.py` (dry-run first: 9 ops, 9 covered, 0 errors, 3 expected scaffold warnings); the four affected models regenerated and the registry republished. Generated diffs are exactly the nine rule rows plus their `generated_at` and active-rule-count lines — no other drift.

Rewritten:

- New `tests/lib/workbook-registry-snapshot.mjs` derives every sheet, family, typed column, and model from `registered_sheet_families()` / `model_sheet_registry()` plus `model_master`. One Python launch. The retired file hardcoded 9 canonical source sheets, a 25-entry future-model sheet list, and a three-model block naming z06/zr1/zr1x with literal variant ids and eleven literal sheet names each — every one a stale subset once six models went active.
- 9 tests → 11. Coverage widened from 3 models to 6 and from 2 named rule sheets to all 73 registered sheets.
- Each derived sweep is paired with a named expectation (`EXPECTED_MODEL_KEYS`, `EXPECTED_SOURCE_ROLES`, `BLOCKER_CLUSTER_RPOS`, `KNOWN_TYPE_DRIFT`), so no assertion compares a derived set only against itself.

**Found by widening, recorded not fixed:** nine registry-declared typed columns hold text where the registry declares bool/int. Generation reads them through `workbook.clean()` so they are tolerated today, but the editor's coercion path expects the declared type. Pinned exactly as `KNOWN_TYPE_DRIFT`; a tenth entry fails the gate. Fixing them is a separate workbook write.

**One assertion of mine was wrong and the workbook was right:** `grand_sport_x` stores `model_variants` body-style-interleaved (display_order 1,4,2,5,3,6 in row order) where the others are trim-major. Both are dense 1..N. Compared as a sorted set — physical row order is not a contract.

**Validation.** 10 mutations injected into real workbook copies, all 10 caught: duplicate group-peer excludes, bool cell retyped to text, source role pointed at a missing sheet, source role deactivated, retired column reintroduced, variant display_order duplicated, `variant_master` fact deactivated, interior header divergence, stacked replace between group peers, ungrouped blocker-cluster excludes. Gate 11/11. Companion node gates 204 passed / 0 failed across `multi-model-runtime-switching` (48), `stingray-form-regression` (91), `z06-runtime-promotion` (4), `z06-runtime-rule-corrections` (15), `z06-performance-package-interactions` (21), `grand-sport-contract-preview` (6), `grand-sport-draft-data` (19). Workbook package and schema gates both valid, 0 issues. Backup at `backups/stingray_master-20260727-221721.xlsx`.

**Still open:** the `app.js` peer-guard asymmetry itself is unfixed — the nine rows are gone and the gate blocks re-adding them, but the runtime remains one bad authoring row away from the same class of defect. Recorded in `fable5loop/STATE.md` under Open failures; closing it is a runtime behavior change needing its own approval.

#### Stage A closeout receipt — gate-authority migration, completed 2026-07-29

The remaining gate split is complete. Fresh strict runtime contracts now own Stingray, Grand Sport, and Z06 generation assertions; Grand Sport/Z06 preview tests are optional provenance diagnostics; Z06 published-runtime verification and isolated registry publication are separate; `z06-interior-accessory-cleanup` reads the strict runtime contract; editor reminders invoke package, schema, composed candidate, affected-model generation, and publication in executable order. The compatibility exporter is disconnected from generation and current tests, and the retained unpublished-artifact assertions moved to fresh all-model generation. README and `docs/route-map.md` now describe the same authority split.

Validation: after the final zero-consumer migration, all 18 Node gates passed serially with tracked `form-output/` and `form-app/` hashes unchanged; workbook package/schema were valid with zero issues; the Python metadata/route/all-model set passed 189 tests plus 111 subtests; editor apply passed 59 tests plus 7 subtests; and one real composed candidate run completed all ten stages for all six changed models with no boundary violation, validation finding, or unexpected drift. No workbook, generated runtime contract, published registry, runtime app, or dealer boundary changed in this slice. Receipt: `fable5loop/runs/2026-07-28-pass4a-gate-authority-closeout/`.

Exact Stage B `git rm` list, separately approved and executed on 2026-07-29:

- `form-output/stingray-form-data.json`
- `form-output/stingray-form-data.csv`
- `scripts/corvette_form_generator/production.py`
- `scripts/seat-canonicalization-diff.mjs`
- `tests/seat-canonicalization-diff.test.mjs`
- `tests/unpublished-runtime-contracts.test.mjs`

Stage A already removed the compatibility writer/import/result wiring and current test consumers. Stage B is deletion-only for the exact files above plus removal of their candidate wording from active guidance.

#### Stage A verification follow-up — macOS candidate boundary, completed 2026-07-29

Sean's completion check found one remaining Stage A exit-gate defect before any Stage B deletion began. During two fresh full candidate-suite runs, macOS recreated ignored `form-output/.DS_Store` metadata. `protected_surface_hashes()` recursively included every file below `form-output/`, so both runs failed with a false boundary violation despite all 18 serial Node gates passing and tracked `form-output/` / `form-app/` hashes remaining identical.

The repaired hasher excludes only the exact `.DS_Store` basename. A focused test was observed RED before the source edit, a temporary-root probe proves arbitrary untracked files remain visible, and the full candidate suite then passed 16/16 while Finder metadata was recreated during the run. Package/schema remained clean; the fresh unaffected Stage A gates remained 189 Python tests plus 111 subtests, 59 editor tests plus 7 subtests, and all 18 Node files. Independent verifier `deleg_982c3aa8` returned PASS. Receipt: `fable5loop/runs/2026-07-29-pass4a-macos-boundary-hardening/`.

Per Sean's conditional instruction, finding this incomplete Stage A gate stopped the sequence. The exact six Stage B candidates remain tracked; Stage B did not start.

#### Stage A verification follow-up — late zero-reference correction, completed 2026-07-29

The first independent verifier dispatched before the macOS failure was found completed later and returned FAIL on C9. Its code/test/gate grades were otherwise green, but it found one stale active source docstring (`rules.py` still described Stingray as using `production.py`) and ten `.hermes/plans` files whose old compatibility paths or executable commands lacked an explicit superseded/historical classification.

The source comment now describes the actual one-route call through `build_draft_rules`. Each affected plan carries a top-of-file execution-status notice: old compatibility paths, `production.py` routes, artifact types, and retired test names are historical evidence and must not be executed; `README.md` and this Stage A section own current commands. This preserves Stage C's archive/classification boundary without leaving the files as operator-command consumers. The underlying open product/data decisions in plans marked `SUPERSEDED FOR COMMANDS` remain undecided.

This correction changes comments/guidance only. It does not delete or alter any Stage B candidate, workbook row, generated artifact, publication output, runtime behavior, or dealer path. The zero-reference verifier was rerun after the correction; see the amended Stage A receipt.

#### Stage B (formerly Pass 4B) — Exact approved deletion, completed 2026-07-29

Sean separately approved Stage B after the Stage A hardening commit `2bb1e76`. `git rm` removed exactly the six listed compatibility artifacts, exporter/tool files, and retired tests; no other file was deleted. README and the current route map no longer describe those files or Stage B as pending.

Post-deletion active scans found zero retired artifact names, exporter symbols, or stale test filenames in tracked `scripts/`, `tests/`, README, and `docs/route-map.md`. The unpublished roof-order and order-summary assertions remain owned by fresh isolated all-model generation; the seat-diff pair contained only its retired one-use tool's self-tests.

Validation: package/schema valid with zero issues; Python metadata/route/all-model 189 tests plus 111 subtests; all 16 remaining Node files and 281 tests passed serially; retained tracked-artifact hashes remained identical; full candidate lane 16 passed in 661.20s. Initial verifier `deleg_93c5c1ec` found two stale pending-guidance lines; both were removed, and final verifier `deleg_6140e07e` passed C1–C7 with no blockers. Workbook, retained generated artifacts, publication, runtime, dealer submission, and Stage C remained untouched. Receipt: `fable5loop/runs/2026-07-29-pass4b-exact-retirement/`.

Initial retirement candidates requiring final Pass 0B semantic confirmation:

- `scripts/seat-canonicalization-diff.mjs` and `tests/seat-canonicalization-diff.test.mjs`: apparent completed one-use comparison pair with only archived-spec ownership.
- The complete ingest wizard/compiler/emitter/proof surface is retired in Pass I. Do not preserve isolated helper modules, constants, historical readers, or tests merely because a retired ingest file imports them.
- `inspection.write_runtime_contract_artifact()`: duplicate unused writer after Pass 2/3 caller scan.

Explicitly retained diagnostics/artifacts:

- `scripts/compare_workbook_bool_hygiene.py` remains a reusable read-only before/after report over the actively enforced bool-hygiene module.
- `form-output/inspection/{stingray,grand-sport,z06}-derived-swap-manifest.json` remain derivation diagnostics until Pass 2 separates their writer from normal generation. They are not source authority and must no longer be rewritten as an undeclared routine-generation side effect.

Protected from name-based deletion:

- `scripts/apply_workbook_changeset.py`
- `scripts/apply_workbook_ops.py`
- `scripts/repair_workbook_tables.py`
- `scripts/promote_model.py`
- `scripts/generate_form.py`
- `scripts/generate_registry.py`
- `scripts/sync_asset_map.py`
- `scripts/workbook_editor_server.py`
- Current workbook-domain ChangeSet/service, editor, and Workbook Manager modules/tests that have independent non-ingest behavior.

Pass 4B deletion requirements:

- Use `git rm` only for the exact approved list.
- Do not begin until Pass 4A has already removed or migrated every active reference.
- Preserve durable regression assertions by moving them to current owners before file deletion.
- Do not edit archived historical prose merely to erase old command names.
- Do not delete an executable because it lacks README documentation if an active API, service, test, or ingest design consumes it.

Pass 4 gates:

- Run the gate belonging to every retired or consolidated surface.
- Before deletion, prove every exact candidate has zero active references. After deletion, prove retired artifact types, functions, and stale test filenames are absent from active `scripts/`, `tests/`, README, and route map.
- Run the new canonical all-model generation and candidate-promotion gates.
- Confirm default gates do not write tracked files.

#### Stage C (formerly Pass 5) — Archive historical inputs, clear generated review clutter, and close

Purpose: after active guidance and executable cleanup are complete, leave future agents with no active completed-plan pile or redundant generated-review outputs.

Pinned owners; the bound Pass 0 plan disposition appears in §9.4 and must be rebased before Pass 5 approval:

- Move explicit completed `.hermes/plans/*.md` files to `docs/archive/completed-specs/` after reference updates.
- Review the two explicitly open plans and keep them active only if still intended.
- Resolve the one ambiguous plan and 14 no-status plans individually; do not mass-delete them.
- The active ingest documentation tree is archived as retired in Pass I. Pass 5 must not retain a canonical compiler design or consolidation plan as current architecture.
- Decide whether `fable5loop/STATE.md` needs a compact authoritative current-state header above its chronological history; do not delete required receipts or history.
- Delete the exact generated-review/log list in §9.3 only after its unique evidence has been migrated to retained receipts.
- Modify this specification to `Completed` with per-pass receipts.

Pass 5 gates:

- `git diff --check`
- Targeted stale-reference scan over active non-archive files.
- Read-back of every moved/updated current guidance file.
- Final repo status showing only approved code/test/docs/deletion changes and no generated churn.

## 5. Companion-file impact matrix

| Surface | Required treatment |
|---|---|
| Canonical workbook | Inspected only; no write in this specification. Business-data blockers become separate authorized passes. |
| `form-output/runtime/` | Temp generation/parity evidence during Passes 2–3; tracked changes only under a separately approved artifact refresh. |
| `form-app/data.js` | Preserved during cleanup/preflight; only explicit publication may change it. |
| Runtime JS | Inspected and exercised; no product behavior change expected. Candidate-registry injection belongs in the Node test harness, not production `app.js`. |
| Dealer submission | Preserved. Candidate runtime tests must remain local and must not submit live dealer requests. |
| Workbook Manager | Registry consumers updated for parity only; Passes 3–7 of its owning spec remain separately scoped. Per §2.8 S4, `staging.py` and `sync_workbook(write=True)` are frozen with characterization tests only — do not harden a write lane the ChangeSet migration replaces. |
| Database workflow | Consumes Pass 1's validators and Pass 3's `verify_workbook_candidate.py` report; it does not reimplement validation, generation, or registry construction. |
| Ingest | Entire wizard/compiler/emitter/proof surface retired in Pass I; generic workbook-domain ChangeSet parsing/service remains independent. |
| README/route map | Must be updated to the final single lane. |
| `.hermes/plans` | Explicit completed plans archived; open/ambiguous plans classified individually. |
| Profile/Codex guidance | Inspect for stale command/path references; update only current repo-owned guidance. |

## 6. Rollback and safety

- Code/test/docs passes are ordinary Git-reversible changes.
- No canonical workbook write is authorized.
- No generated artifact publication is authorized.
- Any test that writes tracked artifacts must run in a temporary root or with explicit snapshot/restore and final diff proof until rewritten.
- If a proposed deletion has a current consumer or necessary behavior, restore it and revise the Pass 0B viability classification before continuing.
- If unification changes a runtime contract outside approved volatile fields, stop for model-specific drift review; do not normalize the difference away.

## 7. Non-goals

- Fixing GSX/ZR1/ZR1X product rules, groups, pricing, or copy.
- Promoting or publishing any model.
- Renaming `model_config.py`/`model_configs.py`, splitting `editor_ops.py` or `schema_validation.py` for size, or touching `asset_map_sync.py` (§2.8 S7).
- Building the database editor's UI, draft state, or ChangeSet emission; that is the database specification's scope.
- Completing Workbook Manager Passes 3–7.
- Redesigning the customer form or visualizer.
- Deleting historical archives merely because they mention retired paths.
- Reducing file counts to an arbitrary target.

## 8. Approval boundaries

Pass 0A is complete as a read-only file inventory. Pass 0B is still required to prove semantic viability; Pass 1 implementation approval is premature until that evidence revises the downstream file lists.

Passes 2–3 require review of fresh route-characterization evidence before source-route or promotion changes.

Pass 4 Stage B's exact six-file deletion list was separately reviewed, approved, and completed on 2026-07-29. This does not authorize Stage C.

Pass 5 plan moves/deletions require the completed/no-status classification receipt from Pass 0A and the current-consumer/necessary-behavior proof from Pass 0B.

Current recommendation (revised 2026-07-29): Stage C is the next cleanup stage. It requires separate approval and must use the bound plan classification before moving completed plans or deleting generated review clutter; Stage B authorizes none of those changes.

Pass 1 must not unify source builders, repair model semantics, refresh retained artifacts, or publish a registry.

Database-workflow readiness checkpoints, in order: Pass 1 makes export validation real; Pass 2 makes one pathway serve all six models; Pass 3 makes an end-to-end candidate run possible and gives the editor a machine-readable readiness report. The database specification's Passes 3–7 may proceed in parallel up to the point where they need a trustworthy post-export gate; they must not ship a write path that depends on today's permissive schema validation.

## 9. Bound audit inventory

Sections 9.1–9.4 preserve the commit-`786e936` baseline and approved dispositions as an audit/deletion receipt. After Pass I, the active filesystem contains 44 script files and 46 test files; the 30 retired script files and 31 retired tests remain listed below only to show the reviewed boundary. The completed docs-archival plan is likewise listed at its original path as a rename receipt.

This inventory is the draft Pass 0A evidence at commit `786e936`. It binds all 74 tracked script files and all 76 tracked test files, but does not by itself prove semantic viability. Rebase it against the current tree and apply the Pass 0B criteria before approving implementation or deletion if the commit changes.

### 9.1 Scripts — 74

Top-level `KEEP_CURRENT_AUTHORITY`:

- `scripts/generate_form.py`
- `scripts/generate_registry.py`
- `scripts/sync_asset_map.py`
- `scripts/validate_workbook_package.py`
- `scripts/validate_workbook_schema.py`

Top-level `KEEP_APPROVED_TARGET_AUTHORITY`:

- `scripts/apply_workbook_changeset.py` — implemented generic operator for the ChangeSet contract explicitly adopted by the approved reliable Workbook Manager specification; no current non-ingest producer exists yet.

Top-level `KEEP_REUSABLE_REPORT`:

- `scripts/compare-generated-contracts.mjs`
- `scripts/compare_workbook_bool_hygiene.py`
- `scripts/validate_fable5_loop.py`

Top-level `KEEP_MIGRATION_REPAIR`:

- `scripts/repair_workbook_tables.py` — explicit workbook-package repair with backup behavior; never a routine release or schema-authoring authority.

Top-level `CONSOLIDATE_INTO_CURRENT_OWNER`:

- `scripts/apply_workbook_ops.py` — guarded fallback-editor transition path until shared ChangeSet/UI parity is proven.
- `scripts/promote_model.py` — metadata activation/rollback utility only; it is not a viable release-promotion gate and must be renamed or absorbed into a proof-bound promotion owner.
- `scripts/workbook_editor_server.py` — retain until Workbook Manager/shared-service parity is complete.

Top-level `RETIRE_INGEST_WORKFLOW` — 5:

- `scripts/ingest_wizard_server.py`
- `scripts/order_guide_ingest_profiler.py`
- `scripts/order_guide_candidate_normalizer.py`
- `scripts/order_guide_ingest_interpreter.py`
- `scripts/prove_workbook_changeset.py`

Top-level `RETIRE_ONE_PASS_EXECUTABLE`:

- `scripts/seat-canonicalization-diff.mjs`

Package `KEEP_CURRENT_AUTHORITY`:

- `scripts/corvette_form_generator/__init__.py`
- `scripts/corvette_form_generator/asset_map_sync.py`
- `scripts/corvette_form_generator/contract.py`
- `scripts/corvette_form_generator/editor_ops.py`
- `scripts/corvette_form_generator/interiors.py`
- `scripts/corvette_form_generator/mapping.py`
- `scripts/corvette_form_generator/model_config.py`
- `scripts/corvette_form_generator/model_configs.py`
- `scripts/corvette_form_generator/model_generation.py`
- `scripts/corvette_form_generator/options_sheet_quality.py`
- `scripts/corvette_form_generator/output.py`
- `scripts/corvette_form_generator/pricing.py`
- `scripts/corvette_form_generator/registry_promotion.py`
- `scripts/corvette_form_generator/rule_derivation.py`
- `scripts/corvette_form_generator/rules.py`
- `scripts/corvette_form_generator/runtime_contract.py`
- `scripts/corvette_form_generator/runtime_metadata.py`
- `scripts/corvette_form_generator/schema_validation.py`
- `scripts/corvette_form_generator/source_assembly.py`
- `scripts/corvette_form_generator/workbook.py`
- `scripts/corvette_form_generator/workbook_bool_hygiene.py`
- `scripts/corvette_form_generator/workbook_domain/__init__.py`
- `scripts/corvette_form_generator/workbook_domain/registry.py`
- `scripts/corvette_form_generator/workbook_package.py`

Package `KEEP_APPROVED_TARGET_AUTHORITY`:

- `scripts/corvette_form_generator/workbook_domain/changeset.py`
- `scripts/corvette_form_generator/workbook_domain/service.py`

Package `KEEP_REUSABLE_REPORT`:

- `scripts/corvette_form_generator/editor_lints.py`

Package `CONSOLIDATE_INTO_CURRENT_OWNER`:

- `scripts/corvette_form_generator/inspection.py`
- `scripts/corvette_form_generator/production.py`
- `scripts/corvette_form_generator/validation.py`

Package `RETIRE_INGEST_WORKFLOW` after the exact cross-boundary cleanup — 25:

- `scripts/corvette_form_generator/ingest/__init__.py`
- `scripts/corvette_form_generator/ingest/candidate_normalizer.py`
- `scripts/corvette_form_generator/ingest/expert_interpreter.py`
- `scripts/corvette_form_generator/ingest/model_selection.py`
- `scripts/corvette_form_generator/ingest/review_payload.py`
- `scripts/corvette_form_generator/ingest/source_profiler.py`
- `scripts/corvette_form_generator/ingest/wizard/__init__.py`
- `scripts/corvette_form_generator/ingest/wizard/canonical_rows.py`
- `scripts/corvette_form_generator/ingest/wizard/changeset_emitter.py`
- `scripts/corvette_form_generator/ingest/wizard/comparator_evidence.py`
- `scripts/corvette_form_generator/ingest/wizard/compiler.py`
- `scripts/corvette_form_generator/ingest/wizard/copy_split.py`
- `scripts/corvette_form_generator/ingest/wizard/decisions.py`
- `scripts/corvette_form_generator/ingest/wizard/exceptions.py`
- `scripts/corvette_form_generator/ingest/wizard/hints.py`
- `scripts/corvette_form_generator/ingest/wizard/identity.py`
- `scripts/corvette_form_generator/ingest/wizard/joiner.py`
- `scripts/corvette_form_generator/ingest/wizard/legacy_reader.py`
- `scripts/corvette_form_generator/ingest/wizard/parser.py`
- `scripts/corvette_form_generator/ingest/wizard/plan_builder.py`
- `scripts/corvette_form_generator/ingest/wizard/profile_compiler.py`
- `scripts/corvette_form_generator/ingest/wizard/profiler.py`
- `scripts/corvette_form_generator/ingest/wizard/relationship_compiler.py`
- `scripts/corvette_form_generator/ingest/wizard/session.py`
- `scripts/corvette_form_generator/workbook_domain/deployment_proof.py`

Top-level side-effect boundary:

- Workbook writers: `apply_workbook_changeset.py` only with its exact bound write mode; `apply_workbook_ops.py` only with its gated write mode; `promote_model.py` only with `--write`; `sync_asset_map.py` only with explicit apply; `repair_workbook_tables.py` always replaces workbook package metadata and creates a backup by default; `workbook_editor_server.py` writes only through its guarded Apply path.
- Generated-output writers: `generate_form.py` writes generated artifacts; `generate_registry.py` writes `form-app/data.js`. The retired ingest server and deployment-proof CLI are absent.
- Read-only gates/reports: both workbook validators, both comparison reports, and `validate_fable5_loop.py`.
- The ingest/proof retirement surface was removed in Pass I. The seat one-pass executable remains a separate retirement candidate with no current authority.

### 9.2 Tests — 76

`KEEP_CURRENT_GATE` after the named rewrites in Passes 1–3 — 8. These are current workbook or browser-behavior gates, but retained-artifact browser tests are not fresh-generation proof:

- `tests/fixtures/options-sheet-quality-allowlist.json`
- `tests/multi-model-runtime-switching.test.mjs`
- `tests/stingray-form-regression.test.mjs`
- `tests/test_model_config_metadata.py`
- `tests/test_options_sheet_quality.py`
- `tests/test_rule_derivation.py`
- `tests/z06-performance-package-interactions.test.mjs`
- `tests/z06-runtime-rule-corrections.test.mjs`

`KEEP_FOCUSED_REGRESSION` — 22:

- `tests/fixtures/asset-map-sync-media-urls.txt`
- `tests/test_asset_map_sync.py`
- `tests/test_corvette_form_generator_contract.py`
- `tests/test_editor_lints.py`
- `tests/test_editor_ops_apply.py`
- `tests/test_editor_ops_global_families.py`
- `tests/test_editor_ops_meta.py`
- `tests/test_editor_server_payload.py`
- `tests/test_editor_server_write_api.py`
- `tests/test_fable5_loop_contract.py`
- `tests/test_promote_model.py` — metadata activation and rollback only; not customer-release readiness.
- `tests/test_registry_promotion_metadata.py` — workbook publication metadata/registry construction fixtures; strengthen strict-contract cases before using them as runtime validation evidence.
- `tests/test_runtime_contract_builder.py` — runtime finalization regression; add malformed, incomplete, and error-bearing rejection cases.
- `tests/test_runtime_metadata_guards.py`
- `tests/test_workbook_bool_hygiene.py`
- `tests/test_workbook_changeset.py`
- `tests/test_workbook_changeset_service.py`
- `tests/test_workbook_domain_registry.py`
- `tests/test_workbook_manager.py`
- `tests/test_workbook_manager_catalog.py`
- `tests/test_workbook_manager_import_projection.py`
- `tests/workbook-visual-copy-standardization.test.mjs`

`REWRITE_TO_CURRENT_LANE` — 7:

- `tests/grand-sport-draft-data.test.mjs`
- `tests/test_generate_form_model_discovery_cli.py`
- `tests/test_schema_validation_metadata.py`
- `tests/test_source_assembly_characterization.py`
- `tests/z06-form-data-draft.test.mjs`
- `tests/z06-interior-accessory-cleanup.test.mjs`
- `tests/z06-runtime-promotion.test.mjs`

`MOVE_TO_OPTIONAL_DIAGNOSTIC` — 2:

- `tests/grand-sport-contract-preview.test.mjs`
- `tests/z06-contract-preview.test.mjs`

`CONSOLIDATE_DUPLICATE` — 3:

- `tests/nonruntime-option-source-purge.test.mjs`
- `tests/stingray-generator-stability.test.mjs`
- `tests/workbook-schema-standardization.test.mjs`

`RETIRE_STALE` — 34 after the Pass 0B generation/runtime reclassification; 31 ingest/proof entries were removed in Pass I, while the seat, source-string route, and retained-unpublished-contract tests remain pending exact deletion approval:

- `tests/ingest_wizard_fixtures.py`
- `tests/seat-canonicalization-diff.test.mjs`
- `tests/test_model_generation_route.py`
- `tests/unpublished-runtime-contracts.test.mjs`
- `tests/test_ingest_wizard_canonical_compiler.py`
- `tests/test_ingest_wizard_canonical_rows.py`
- `tests/test_ingest_wizard_changeset.py`
- `tests/test_ingest_wizard_comparator_evidence.py`
- `tests/test_ingest_wizard_compiler_session.py`
- `tests/test_ingest_wizard_copy_split.py`
- `tests/test_ingest_wizard_decisions.py`
- `tests/test_ingest_wizard_exception_flow.py`
- `tests/test_ingest_wizard_exceptions.py`
- `tests/test_ingest_wizard_hints.py`
- `tests/test_ingest_wizard_identity.py`
- `tests/test_ingest_wizard_joiner.py`
- `tests/test_ingest_wizard_parser.py`
- `tests/test_ingest_wizard_plan.py`
- `tests/test_ingest_wizard_profile_compiler.py`
- `tests/test_ingest_wizard_profiler.py`
- `tests/test_ingest_wizard_relationship_compiler.py`
- `tests/test_ingest_wizard_server.py`
- `tests/test_ingest_wizard_server_milestone2.py`
- `tests/test_ingest_wizard_server_pass_b.py`
- `tests/test_ingest_wizard_session.py`
- `tests/test_ingest_wizard_ui_blockers.py`
- `tests/test_ingest_wizard_ui_milestone2.py`
- `tests/test_ingest_wizard_ui_reference.py`
- `tests/test_ingest_wizard_ui_relationships.py`
- `tests/test_ingest_review_payload.py`
- `tests/test_order_guide_candidate_normalizer.py`
- `tests/test_order_guide_ingest_interpreter.py`
- `tests/test_order_guide_ingest_profiler.py`
- `tests/test_workbook_changeset_deployment_proof.py`

Tests known to rewrite tracked artifacts until isolated:

- `tests/grand-sport-contract-preview.test.mjs`
- `tests/grand-sport-draft-data.test.mjs`
- `tests/test_generate_form_model_discovery_cli.py`
- `tests/z06-contract-preview.test.mjs`
- `tests/z06-form-data-draft.test.mjs`
- `tests/z06-interior-accessory-cleanup.test.mjs`
- `tests/z06-runtime-promotion.test.mjs`

### 9.3 Active guidance and historical-input disposition

`UPDATE_CURRENT_GUIDANCE`:

- `AGENTS.md`
- `README.md`
- `docs/route-map.md`
- `.claude/launch.json`
- `scripts/generate_form.py`
- `scripts/promote_model.py`
- `scripts/corvette_form_generator/runtime_contract.py`
- `scripts/corvette_form_generator/production.py`
- `scripts/corvette_form_generator/rules.py`
- `scripts/corvette_form_generator/workbook_domain/__init__.py`
- `scripts/corvette_form_generator/workbook_domain/changeset.py`
- `tests/test_editor_ops_global_families.py`
- `workbook-manager/backend/app/staging.py`

`ARCHIVE_RETIRED_INGEST_GUIDANCE` in Pass I:

- `Order-Guide_IngestPrompt.md`
- `docs/ingest/` — all 36 tracked Markdown files as one retired historical tree.
- `docs/c1-review_codex.md`
- `docs/c1-review_hermes.md`
- `docs/ingest-impl-grade-review.md`
- `docs/workbook-manager-v-editor-v-ingest.md`

`ARCHIVE_COMPLETED_OR_HISTORICAL` after pointer review:

- `docs/db_audit-7-22.md`
- `docs/superpowers/plans/2026-07-16-workbook-congruent-relational-database.md`
- `docs/superpowers/specs/2026-07-16-workbook-congruent-relational-database-design.md`
- `docs/react-editor prompt.md`
- `.hermes/plans/docs-archival-pass4-spec.md`
- `.hermes/plans/route-map-condensation-pass6-spec.md`
- `.hermes/plans/rule-audit-orphan-retirement-pass2-spec.md`
- `.hermes/plans/src-images-retirement-pass5-spec.md`
- `.hermes/plans/superpowers-untrack-pass1-spec.md`
- `.hermes/plans/fable5-source-doc-rename-pass7-spec.md`
- `.hermes/plans/cross-model-stale-gate-expectations-spec.md`
- `.hermes/plans/grand-sport-stripe-heritage-reverse-exclusions-spec.md`
- `.hermes/plans/vehicle-setup-copy-workbook-ownership-spec.md`

`DELETE_AFTER_CONSUMER_MIGRATION`:

- `docs/claude_output-workbookEditor.md`
- `fable5loop/runs/2026-07-05-cross-model-regression-hardening/multi-model-runtime-switching-full.log`
- `fable5loop/runs/2026-07-05-cross-model-regression-hardening/stingray-form-regression-full.log`

`KEEP_CURRENT` includes `AGENTS.md`, the 2026-07-22 reliable-workflow spec, current Workbook Manager README, current Codex/Claude configuration after ingest launch removal, required Fable receipts, generic workbook-domain ChangeSet/service owners, and all three tracked derived-swap manifests. No ingest compiler, emitter, deployment proof, or active ingest design remains current.

`NEEDS_DECISION`:

- Legacy `artifact_type` support in `registry_promotion.py` and `schema_validation.py` — remove after fixture/external-consumer closure.
- Draft-prefixed generated filenames — rename only with coordinated consumer migration.
- `.hermes/plans/` entries without explicit completed/open state — classify individually.
- `.hermes/plans/form-mobile-ux-consistency-spec.md` — status says implemented on another branch but pending Sean's device check/push direction; verify whether its behavior landed here before archiving.
- `.hermes/plans/grand-sport-jake-heritage-hash-reverse-exclusions-spec.md` — top status still says implementing although a closeout exists; reconcile status with current workbook/runtime evidence before archiving.
- `fable5loop/STATE.md` — retain; decide whether to add a compact authoritative current-state header above chronological history.

### 9.4 `.hermes/plans` — 29 at audit baseline; 28 active after Pass I

`ARCHIVE_COMPLETED_OR_HISTORICAL` after pointer review:

- `.hermes/plans/asset-map-sync-legacy-retirement-pass3-spec.md`
- `.hermes/plans/cross-model-stale-gate-expectations-spec.md`
- `.hermes/plans/docs-archival-pass4-spec.md`
- `.hermes/plans/fable5-source-doc-rename-pass7-spec.md`
- `.hermes/plans/grand-sport-stripe-heritage-reverse-exclusions-spec.md`
- `.hermes/plans/paint-accent-progress-checkmarks-spec.md`
- `.hermes/plans/route-map-condensation-pass6-spec.md`
- `.hermes/plans/rule-audit-orphan-retirement-pass2-spec.md`
- `.hermes/plans/src-images-retirement-pass5-spec.md`
- `.hermes/plans/superpowers-untrack-pass1-spec.md`
- `.hermes/plans/vehicle-setup-copy-workbook-ownership-spec.md`

`KEEP_OPEN`:

- `.hermes/plans/layered-visualizer-integration-spec.md`
- `.hermes/plans/rule-normalization-pass7b-failed-fix-correction.md`

`NEEDS_DECISION` before archive or deletion:

Pass 4 Stage A execution-guidance override (2026-07-29): the following files may retain historical mentions of compatibility artifacts or retiring filenames, but their top-of-file notices explicitly supersede every such command/path as operator guidance: `asset-map-exterior-color-url-refresh.md`, `generator-simplification-pass2-runtime-payload-trim.md`, `live-runtime-merge-readiness-no-behavior-change-spec.md`, `r6x-interior-components-spec.md`, `route-map-condensation-pass6-spec.md`, `rule-audit-orphan-retirement-pass2-spec.md`, `rule-normalization-pass1-redundant-exclusive-excludes.md`, `rule-normalization-pass2-grouped-excludes.md`, `stingray-engine-appearance-display-order-match-grand-sport.md`, and `z06-interior-accessory-cleanup-pass2-spec.md`. Their underlying archival or still-open product/data status remains governed by the lists below; they are no longer current generation guidance.

- `.hermes/plans/asset-map-exterior-color-url-refresh.md`
- `.hermes/plans/color-override-normalization-spec.md`
- `.hermes/plans/form-mobile-ux-consistency-spec.md`
- `.hermes/plans/generator-simplification-pass2-runtime-payload-trim.md`
- `.hermes/plans/grand-sport-jake-heritage-hash-reverse-exclusions-spec.md`
- `.hermes/plans/grand-sport-z06-stripe-workbook-rule-fix.md`
- `.hermes/plans/live-deltas-into-local-spec.md`
- `.hermes/plans/live-runtime-merge-readiness-no-behavior-change-spec.md`
- `.hermes/plans/r6x-interior-components-spec.md`
- `.hermes/plans/rule-normalization-pass1-redundant-exclusive-excludes.md`
- `.hermes/plans/rule-normalization-pass2-grouped-excludes.md`
- `.hermes/plans/stingray-engine-appearance-display-order-match-grand-sport.md`
- `.hermes/plans/z06-carbon-wheel-package-disabled-state-spec.md`
- `.hermes/plans/z06-interior-accessory-cleanup-pass2-spec.md`
- `.hermes/plans/z06-package-pricing-cascade-spec.md`
- `.hermes/plans/z06-runtime-rule-correction-spec.md`

## 10. Completion record

Pass 0A and approved Pass I completed 2026-07-23; the Pass 0B generation/runtime executable slice completed 2026-07-24 and Pass 0B remains open for other non-ingest surfaces:

- Classified all 74 tracked script files and all 76 tracked test files at commit `786e936`.
- Classified all 29 tracked `.hermes/plans` entries without treating ambiguous/no-status plans as completed.
- Identified seven tests that can rewrite tracked generated artifacts.
- Classified active guidance, historical-input, generated-review, and plan cleanup candidates.
- Verified the script and test categories are complete partitions with no missing, extra, or duplicate paths.
- Bound the current-route audit to commit `786e9367d39563c91e6554b5e1d0d5a4b6f5b8bb`, workbook SHA-256 `c5f986f6793205e00124db5640248e9e8c57ebb930679a92c2b3e8c56fb62154`, isolated outputs, exact per-model diff categories, and a clean protected-surface diff.
- Independent review's ten initial plan blockers were amended. Re-review found only missing Pass 1 regression gates; `test_editor_ops_global_families.py`, `test_registry_promotion_metadata.py`, and conditional `test_promote_model.py` coverage are now explicit alongside Workbook Manager projection gates.
- Correction after semantic-viability challenge: importer/caller coverage is only a reachability guard. It does not prove a module, function, route, output, or test remains necessary. Pass 0B must trace authoritative roots and revise every keep/retire decision before implementation approval.
- Pass 0B source-level subaudit traced customer release, workbook schema/write, promotion/publication, ingest/ChangeSet, fallback editor, and Workbook Manager roots. It reclassified `promote_model.py`, `apply_workbook_ops.py`, deployment proof, migration/repair, mixed ingest session/decision modules, legacy importer libraries, and false-green/compatibility-preserving tests by actual behavior rather than importer count.
- Pass 0B generation/runtime execution at commit `667aad5` proved six-model discovery, five successful isolated generations, the Z06 stale-derivation failure, split source construction, incomplete config path binding, permissive runtime validation, write-before-validation behavior, retained-artifact registry false confidence, and tracked-path test hazards. The evidence and revised implementation ordering are recorded in §2.4; no protected artifact changed.
- After the Pass 0B generation/runtime reclassification, the revised test partition is 8 current gates, 22 focused regressions, 7 current-lane rewrites, 2 optional diagnostics, 3 duplicate consolidations, and 34 stale retirements. Thirty-one retirements belong to ingest or its ingest-specific proof; the seat canonicalization, source-string route, and retained unpublished-contract tests are separate pending retirement candidates. The 74-script and 76-test inventories remain exact complete partitions with no missing, extra, or duplicate paths.
- User decision: the ingest wizard's data-import behavior caused enough harm that the workspace should not carry the wizard/compiler/exception/emitter chain forward. `changeset_emitter.py` and `plan_builder.py` therefore retire together; no constant migration is justified solely to preserve the emitter. Generic workbook-domain ChangeSet/service safety remains independent.
- Pass I executed the exact reviewed retirement boundary and produced the receipt in §2. The active inventory is now 44 scripts and 46 tests; no retired ingest import, launcher, UI, or active documentation path remains.
- Pass 0B is not complete: the subaudit was read-only source/API/UI tracing and did not execute every retained CLI/test. Per-path execution or an explicit safe source-only characterization is still required before a `KEEP_*` disposition becomes final implementation/deletion authority.
- No workbook, generated runtime contract, registry, runtime JS, dealer surface, promotion row, or deployment path changed.
- 2026-07-24 revision: added the database-workflow end-state lane at the head of this document, the §2.8 simplification audit, the §3.7 composed candidate lane with its §3.7.1 changed-model reporting contract, the §3.8 single-validator rule and cross-specification reconciliation, Pass 1 export-gate RED cases and the family-to-model mapping helper, the Pass 3 retained-Stingray-contract prerequisite, and the collapse of remaining work to four passes. Corrected the database specification's stale validator-owner reference.
- Next boundary: approve Pass 1. Continue remaining Pass 0B viability work in parallel; its evidence gates Pass 4 deletion, not Pass 1 authority consolidation.
