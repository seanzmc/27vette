# Validation Single-Lane and Active-Surface Cleanup Specification

Status: ACTIVE — Pass 0A inventory and Pass 0C boundary complete; approved Pass I ingest retirement completed 2026-07-23. The Pass 0B generation/runtime executable slice, approved Pass G1 fail-closed generation boundary, bounded Pass G2 Z06 source repair, and option-name quality-authority correction completed 2026-07-24; semantic viability remains open for the other non-ingest surfaces. Pass 1 is the next recommended implementation pass and remains unapproved.
Date: 2026-07-23 (revised 2026-07-24 for database-workflow sufficiency and simplification)

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

Pass 1 landed 2026-07-25 (receipt below). The next pass on the critical path is **Pass 3's prerequisite**: the retained Stingray runtime contract fails strict validation, so `generate_registry.py` cannot rebuild `form-app/data.js` and no end-to-end database→form run can finish. Pass 2 is independently startable.

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
5. Move `cleanup_display_text()`'s hardcoded customer-copy correction into workbook data.
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

### Pass 3 — Make promotion and publication prove the candidate runtime

Purpose: prevent a candidate from being called validated until its exact runtime contracts and temporary registry have passed, and deliver the composed candidate lane the database workflow calls.

Blocking prerequisite inside this pass: the retained Stingray runtime contract currently fails strict validation because it lacks `dataset.model`, `dataset.model_year`, and `dataset.status`, so `generate_registry.py` exits nonzero and `form-app/data.js` cannot be rebuilt. Until this is resolved, no end-to-end database→form run can finish. Resolve it by regenerating the contract through the current strict path — never by hand-editing the retained artifact or patching only its dataset metadata. Isolated comparison shows the fresh contract preserves all 1,416 choice identities and all rules, prices, and interiors, but also applies workbook-authored section metadata changes and removes the empty `sec_perf_support_001` section. Review that exact bounded drift, record it in the receipt, and publish only from the complete validated candidate set.

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
- Rewrite `tests/workbook-schema-standardization.test.mjs` to consume registry/source-role metadata rather than hardcoded three-model/future-model structures.
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

#### Stage B (formerly Pass 4B) — Exact approved deletion

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

Pass 4 requires a separately reviewed exact deletion list; this draft is not deletion approval.

Pass 5 plan moves/deletions require the completed/no-status classification receipt from Pass 0A and the current-consumer/necessary-behavior proof from Pass 0B.

Current recommendation (revised 2026-07-24): the §2.4 fail-closed generation boundary is delivered (Pass G1) and Z06 is green (Pass G2), so the next approval should be **Pass 1**. It is the post-export gate the database workflow is blocked on, and §2.1.1 proves the current schema validator reports zero issues over real drift. Continue remaining Pass 0B viability work for non-ingest surfaces in parallel where it does not gate Pass 1 — Pass 0B evidence is required before Pass 4 deletion, not before Pass 1 authority consolidation.

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
