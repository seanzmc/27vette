# Workbook Manager Rebaseline Correction Pass

Date: 2026-07-22
Status: ready for implementation after PR #8 rebaseline
Recommended reasoning level: high

## Goal

Make PR #8 accept the stabilized workbook without expanding unpublished-model rehabilitation, and remove Workbook Manager copies of workbook-domain metadata now owned by `scripts/corvette_form_generator/workbook_domain/registry.py`.

This is a correction pass on `codex/workbook-relational-db`. It is not a workbook-data pass, runtime-publication pass, ingest pass, deployment pass, or dealer-submission pass.

## Current diagnosis

PR #8 has been merged locally with stabilized `origin/main` without rewriting PR history. Conflict resolution kept current `main` for shared ingest, workbook-domain, writer-safety, promotion, instruction, and runtime surfaces, while retaining PR #8's Workbook Manager implementation.

The current workbook state is authoritative:

- `model_master` has six active and source-registered models: Stingray, Grand Sport, Z06, Grand Sport X, ZR1, and ZR1X.
- `model_registry_promotion` publishes only Stingray, Grand Sport, and Z06.
- Grand Sport X, ZR1, and ZR1X remain active/generatable and retain runtime contracts, but are deliberately unpublished pending rehabilitation.
- Workbook Manager's current `workbook_profile._discover_active_models()` defines “active” as active **and promoted**. It therefore reports three active models and treats all rows for the other three as inactive-future exclusions.
- `central_compiler.compile_central_tables()` then iterates every active `model_variants` row but validates it only against the three promoted model rows. The first Grand Sport X row fails with `model_variant_model_reference_missing` at `model_variants` row 8.
- A direct profile/import probe on the merged snapshot returned 77 workbook sheets, six known models, three promoted models, 949 informational unpublished-row exclusions, and one blocking Grand Sport X model-variant finding.

Fresh gates on that snapshot:

- Workbook Manager backend: `44 failed, 46 passed, 107 errors`.
- Legacy Workbook Manager suite: `16 failed, 2 passed, 10 errors`.
- Frontend contract: `14 passed`.
- Frontend Vite build: passed.
- Shared editor/writer gate after removing the dead React prototype: `83 passed, 7 subtests passed`.

The backend failure fan-out is setup fallout from the one population-boundary defect plus stale fixed snapshot assertions. It is not evidence for 151 independent defects.

## Decisions

### 1. Distinguish three model populations

Use explicit internal meanings:

- **Known models**: every model key declared in `model_master`.
- **Importable models**: active `model_master` rows with active source registrations. On the current workbook this is all six models.
- **Published models**: importable models whose active `model_registry_promotion` row has `promoted_to_runtime=True`. On the current workbook this is Stingray, Grand Sport, and Z06.

Workbook Manager continues to materialize, contract-audit, expose for editing, and synchronize only the **published** three-model set in this pass. It must recognize the other three as valid registered-but-unpublished workbook data and exclude them deterministically without treating them as unknown or malformed.

Do not compile or validate Grand Sport X, ZR1, or ZR1X runtime correctness here. That is the separate rehabilitation work already deferred by `nextSteps_v2.md`.

### 2. Derive model population from the workbook snapshot

Remove the hardcoded `LIVE_MODELS` model-population authority from `workbook-manager/backend/app/catalog.py`.

The read-only profile owns discovery for a specific workbook snapshot. Downstream schema creation, compilers, migration, audit, query allowlists, and sync validation receive the profiled published-model tuple explicitly or derive it from the promoted canonical database. No component may silently substitute a module-level three-model literal.

Keep the existing public `ImportReport.live_models` and API response field for compatibility; its value remains the published model tuple. Internal code and messages should use `published_models` where ambiguity matters.

### 3. Keep unpublished data visible as evidence, not as an error

Profile and reconciliation output must preserve row-level evidence for active registered but unpublished models. Those rows receive one explicit nonblocking disposition such as `registered_unpublished`, not `inactive_future` and not `decision_required`.

Central shared sheets must filter model-scoped rows to the published compile target before reference validation. A row for a known importable but unpublished model is reconciled as excluded evidence; a row for a model absent from `model_master` remains a blocking unknown-model finding.

### 4. Consolidate workbook-domain metadata without hiding SQL contracts

`scripts/corvette_form_generator/workbook_domain/registry.py` remains the canonical owner of workbook family keys, scalar types, booleans, enums, references, and editor families.

Workbook Manager may retain only manager-specific relational metadata:

- SQL physical role names and table naming;
- SQL-only destination-column aliases/splits;
- SQLite primary/foreign-key structure read from the canonical database;
- migration/load order;
- API presentation metadata that is not a workbook business-rule copy.

Replace the duplicated `ROLE_KEYS`, `ROLE_BOOLEAN_COLUMNS`, `ROLE_ENUMS`, and `ROLE_EDITOR_FAMILY` literals in `workbook-manager/backend/app/catalog.py` with a narrow adapter over the shared registry plus explicit SQL alias mappings where workbook and relational column names differ.

Audit `workbook-manager/backend/app/specs.py` on the same rule. Do not delete SQL table definitions merely because some fields resemble workbook headers; remove or derive only literals whose authority already exists in the shared registry. Add contract tests that compare the adapter to the shared registry so drift fails immediately.

## Expected implementation surface

Primary backend files:

- `workbook-manager/backend/app/catalog.py`
- `workbook-manager/backend/app/compile_types.py`
- `workbook-manager/backend/app/workbook_profile.py`
- `workbook-manager/backend/app/central_compiler.py`
- `workbook-manager/backend/app/model_compiler.py`
- `workbook-manager/backend/app/shared_compiler.py`
- `workbook-manager/backend/app/db.py`
- `workbook-manager/backend/app/importer.py`
- `workbook-manager/backend/app/migration.py`
- `workbook-manager/backend/app/contract_audit.py`
- `workbook-manager/backend/app/export_adapter.py`
- `workbook-manager/backend/app/staging.py`
- `workbook-manager/backend/app/sync.py`
- `workbook-manager/backend/app/specs.py` only where the audit proves duplicated workbook authority

Tests and owner docs:

- `tests/workbook_manager/test_workbook_profile.py`
- `tests/workbook_manager/test_catalog_schema.py`
- compiler, import, migration, API, staging, and completion tests that currently import `LIVE_MODELS` or assert stale snapshot totals
- `tests/test_workbook_manager.py`
- `workbook-manager/README.md`
- `docs/superpowers/specs/2026-07-16-workbook-congruent-relational-database-design.md`
- `docs/superpowers/plans/2026-07-16-workbook-congruent-relational-database.md`
- this correction plan, closed with an implementation receipt

No frontend source change is expected unless the unchanged API contract cannot be preserved. Stop for approval before adding or changing a public response field.

## Implementation sequence

### Task 1 — Add failing population-boundary tests

1. Assert the real workbook profile discovers six known/importable models and exactly three published models.
2. Assert active source registrations for Grand Sport X, ZR1, and ZR1X are retained as registered-unpublished evidence.
3. Assert a real-workbook import validates and materializes only the published three-model relational families.
4. Assert an active model-scoped row for a known unpublished model is nonblocking.
5. Assert the same row with a model absent from `model_master` remains blocking.

Run the focused profile/central-compiler tests and confirm the new assertions fail for the current root cause.

### Task 2 — Make the published compile target explicit

1. Extend the immutable workbook profile with unambiguous importable and published model tuples while preserving compatibility at external report/API boundaries.
2. Derive both tuples from `model_master`, `model_registry_promotion`, and active source registrations.
3. Pass the published tuple through schema creation, central/direct/shared compilation, migration, contract audit, and export comparison instead of importing a module-level model list.
4. Filter known unpublished rows before published-model reference validation and retain their source disposition/lineage evidence.
5. Keep unknown-model and incomplete-source-registration failures fail-closed.

Run focused profile, compiler, import, and completion tests.

### Task 3 — Remove duplicate workbook registry literals

1. Add one manager adapter from relational role names to shared workbook registry families.
2. Derive workbook keys, booleans, enums, and editor-family bindings from `workbook_domain.registry`.
3. Keep explicit, tested aliases only where relational destination columns intentionally differ from workbook columns.
4. Remove redundant copies from `catalog.py` and any proven duplicates in `specs.py`.
5. Add tests covering every editable role and proving shared-registry drift is detected.

Run catalog/schema and staging/sync tests.

### Task 4 — Refresh stale expectations without weakening invariants

1. Replace fixed 65-sheet and five-model assumptions with assertions against the authoritative workbook inventory and explicit six-importable/three-published split.
2. Recompute exact row/mapping/lineage totals only after the corrected compiler succeeds. Keep exact totals only where they protect a deliberate canonical snapshot; otherwise assert one-to-one reconciliation and relational invariants.
3. Keep the three-model completion contract, 17 physical roles per published model, foreign-key checks, lineage coverage, audit authorization, atomic promotion, rollback, and guarded sync assertions.
4. Update owner docs to say published rather than active/live where publication is the actual boundary.

### Task 5 — Run the correction acceptance gate

Run in this order:

1. `PYTHONPATH="$PWD/scripts" WBM_SLOW_GATE=1 /Users/seandm/Projects/27vette/.venv/bin/python -m pytest tests/workbook_manager -q`
2. `PYTHONPATH="$PWD/scripts" WBM_SLOW_GATE=1 /Users/seandm/Projects/27vette/.venv/bin/python -m pytest tests/test_workbook_manager.py -q`
3. `PYTHONPATH="$PWD/scripts" /Users/seandm/Projects/27vette/.venv/bin/python -m pytest tests/test_editor_ops_apply.py tests/test_editor_ops_global_families.py tests/test_editor_ops_meta.py -q`
4. `node --test tests/workbook_manager/test_frontend_contract.mjs`
5. `npm run build` from `workbook-manager/frontend/`
6. Workbook package and schema validation, read-only.
7. `git diff --check` and protected-surface diff review.

Acceptance requires:

- one successful real-workbook import;
- exactly three published model families in the canonical database;
- six known/importable workbook models represented in profile evidence;
- no decision finding for registered unpublished model rows;
- unknown model rows still blocked;
- shared registry adapter coverage for every editable role;
- rollback and guarded writer tests green;
- no workbook, runtime contract, registry publication, dealer, dependency, or deployment change.

## Preserved boundaries

- `stingray_master.xlsx` remains unchanged.
- `form-output/runtime/*` and `form-app/data.js` remain unchanged.
- Published runtime models remain Stingray, Grand Sport, and Z06.
- Grand Sport X, ZR1, and ZR1X remain unpublished and are not rehabilitated here.
- Workbook writes still route through the shared ChangeSet/workbook service and guarded editor path.
- `scripts/ingest_wizard_apply.py` stays retired.
- The dead `visualizer/workbook-editor/workbook-editor.js` prototype stays absent.
- Dealer submission, public payloads, Turnstile behavior, dependencies, build system, and deployment are untouched.

## Rollback

The pass is code/tests/docs only. Revert its correction commit(s) to return to the rebaselined PR snapshot. No workbook or generated artifact restoration should be necessary.
