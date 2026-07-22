# Ingest Milestone 1 Headless Compiler and Comparator Evidence Implementation Plan

Status: COMPLETED 2026-07-13. The read-only implementation and current-export proof passed focused, broad, no-write, artifact-integrity, and independent verification gates. Receipt: `fable5loop/runs/2026-07-13-milestone1-headless-compiler/`. Completion does not authorize workbook write, plan projection, generated-artifact publication, model promotion, browser/API exception workflow, or dealer changes.

Recommended reasoning level for implementation agents: high.

Parent design: `docs/ingest/canonical-row-compiler-exception-queue-design.md`, especially §§3–9, §13 Milestone 1, and §14.2–§14.3.

## 1. Goal

Build the read-only, headless production compiler that turns one current ingest run plus the canonical workbook snapshot into deterministic compiler artifacts:

- `comparator-evidence.json` (`comparator-evidence-1`);
- `canonical-row-manifest.json` (`canonical-rows-1`);
- `exception-queue.json` (`exception-queue-1`);
- `exception-resolutions.json` plus append-only `exception-log.jsonl` contracts;
- `compile-report.json` (`compile-report-1`).

Milestone 1 ends when those artifacts are deterministic, fully fingerprinted, occurrence-aware, evidence-complete, and directly callable through `WizardSessionStore` without browser/API work. It does not build `pass-c-3`, apply editor operations, mutate `stingray_master.xlsx`, run promotion, or publish runtime data.

## 2. Diagnosis and source-of-truth decision

Change class: mixed ingest compiler, workbook read model, artifact contracts, session state, and Python tests. Browser, apply-plan, runtime, and dealer surfaces are preserved.

Risk: high. This compiler will become the only production source for later ingest apply plans, but this milestone remains read-only.

Current evidence:

- `scripts/corvette_form_generator/ingest/wizard/plan_builder.py:31-117` still owns `pass-c-2`, duplicates model/sheet-role configuration in `MODEL_PLAN_CONFIG`, `MODEL_SHEET_ROLES`, and `ROLE_SHEET_SUFFIX`, and translates broad reviewer decisions directly into operations.
- `plan_builder.py:561-566` still starts the clean-reprocess path by clearing target-family rows. That behavior is incompatible with desired-state reconciliation and stable retained IDs.
- `scripts/corvette_form_generator/ingest/wizard/hints.py:17-27` owns a second hardcoded relationship phrase vocabulary and does not use workbook-authored direction.
- `scripts/corvette_form_generator/runtime_metadata.py:571-595` already owns the active `rule_phrase_map` loader and its workbook-over-fallback behavior. The compiler must consume that loader; it must not create a third phrase taxonomy.
- `scripts/corvette_form_generator/rules.py:43-93` already defines runtime-effective active group/member filtering for rule and exclusive groups. Comparator indexing must mirror those semantics.
- `scripts/corvette_form_generator/model_configs.py:161-174` owns required and optional generation source roles. Compiler family coverage must derive from those constants rather than copy the role list.
- `scripts/corvette_form_generator/editor_ops.py:40-294` owns source-role-to-family mapping, canonical keys/types/enums/references, and fixed global families. It deliberately does not own headers; exact headers must be read from the live workbook.
- `scripts/corvette_form_generator/ingest/wizard/session.py:83-106` already reserves `pass-c-3` compiler bindings and compile-readiness fields, but it has no compiler execution path or compiled states.
- The current browser selection artifact already binds exact targets, one comparator per target, source fingerprint, and candidate fingerprint at `session.py:644-673`. Milestone 1 uses that contract and introduces no parallel model-selection schema.
- `scripts/corvette_form_generator/ingest/model_selection.py` is a separate historical artifact contract (`selected_models`, `primary_models`, `comparator_models`) and is not a production-wizard compiler input.
- `scripts/corvette_form_generator/ingest/wizard/parser.py:149-169,172-233` preserves numeric price coordinates and values, but not the header text/scope associated with each numeric column. Milestone 1 must preserve that source evidence additively or block scoped-price compilation; it may not infer scope from column position.
- Pre-approval review correction, 2026-07-12: the prior draft made every artifact bind the resolution semantic SHA while resolutions also bind queue subjects. That was circular. §4.2 now separates authority envelopes from dependency-scoped semantic evidence and pins one-way `evidence -> comparator/queue -> resolutions -> manifest -> report` dependencies.
- Pre-approval review correction, 2026-07-12: the current export is present at `2027 Chevrolet Car Corvette Export (4) (1).xlsx` with SHA-256 `6ac9538d5bb8a823ade9afea70b2654057b793e1cf27c081c088545aa3add8a1`; Task 8 now requires a fresh ignored real-source run for GSX/ZR1/ZR1X with Grand Sport/Z06 comparators.
- Approval correction, 2026-07-12: full-file authority drift always rebuilds the coherent artifact set, but subject/resolution/derivation validity is dependency-scoped. Unrelated comparator, phrase, target, or workbook evidence changes may not stale unaffected subjects or alter unaffected target-row semantics.
- Milestone 0 closed writer authority and exact readback. Its implementation remains unchanged; Milestone 1 may read its generic family/reference metadata but must not relax any refusal.

Source-of-truth decision:

- Target raw import owns target facts and coordinates.
- Existing target workbook rows own established target identities, retained target data, and canonical row shape.
- `rule_phrase_map`, `section_master`, model metadata, and the live generator/editor registries own reusable canonical metadata.
- The selected comparator is corroborating/prefill evidence only.
- Compiler artifacts are transient derivation evidence. They do not become a second product source.

Standing constraints from `AGENTS.md` apply, especially §§3–6 and §§10–12.

## 3. Definition of done

Milestone 1 is complete only when all of the following are true:

1. A fresh run in `models_selected`, `compiled_with_exceptions`, or `compiled_ready` can invoke one headless `WizardSessionStore.compile_canonical_rows(run_id)` service method.
2. The service verifies current source, candidate, selection, workbook, comparator source-role, and active phrase-map fingerprints before writing run artifacts.
3. The same complete authority inputs produce byte-identical comparator, queue, manifest, and report artifacts and leave the current resolution file unchanged. Changes limited to fields excluded by §4.2 may change a full-file SHA but must not change any semantic hash. The append-only exception audit log may contain event time outside its deterministic `eventId`.
4. Every parsed candidate, skipped parsed row, price row, skipped price row, relationship phrase hit, status symbol, and applicable comparator fact has exactly one source-feature-ledger disposition.
5. Every registered required/optional generator role and relevant global family is either represented by ready/blocked/suppressed desired rows, explicitly retained existing data, explicitly not applicable, or an `unsupported_blocker`. Zero rows never implies coverage by itself.
6. Ready rows use exact live headers, typed values, stable semantic signatures, target evidence, derivation records, and desired actions (`add`, `update`, `delete`, `noop`).
7. ZR1/ZR1X matching reuses unique existing IDs and OVS identity; ambiguous duplicate occurrences emit blocking exceptions. No target family is cleared wholesale.
8. Comparator indexing mirrors runtime-effective active group/member semantics, distinguishes duplicate/inactive occurrences, and never transfers comparator IDs, prices, copy, sections, defaults, notes, display order, or scopes into target rows.
9. Relationship direction comes from active workbook `rule_phrase_map`; `Included with (PEF)` resolves as `PEF includes <source>`, not the reverse.
10. Comparator-only plausible facts create focused proposed exceptions, never ready target rows.
11. Empty or type-valid current resolutions can be consumed headlessly. Stale `subjectVersion` resolutions reopen the exception and cannot affect ready rows.
12. The compile report exposes per-model `compileReady`, `planReady`, `writeReady`, and `deploymentReady`, exact blockers/deferrals, family/action/status counts, feature coverage, comparator dispositions, and reference impact. Milestone 1 must keep `planReady`, `writeReady`, and `deploymentReady` false because plan projection and temporary deployment proof belong to Milestone 3.
13. An unchanged recompile is audit-idempotent: it appends no duplicate resolution/stale/supersession event.
14. Any authority change rebuilds all aggregate compiler artifacts coherently, while unchanged per-subject and per-derivation dependency sets preserve their versions and matching resolution validity.
15. A fresh ignored run from the current export completes with total feature disposition, stable identity evidence, typed blockers, and no writes. `compiled_with_exceptions` is an acceptable real-source result.
16. `stingray_master.xlsx`, `form-output/runtime/**`, `form-app/data.js`, browser assets, apply-plan artifacts, approvals, and promotion metadata remain byte-identical.

## 4. Pinned architecture and contracts

### 4.1 Canonical family registry

`canonical_rows.py` must derive the compilation registry by joining:

- `REQUIRED_GENERATION_SOURCE_ROLES` and `OPTIONAL_GENERATION_SOURCE_ROLES` from `model_configs.py`;
- `SOURCE_ROLE_FAMILIES`, `EDITOR_SHEET_META`, and `GLOBAL_SHEET_FAMILIES` from `editor_ops.py`;
- exact active/inactive target and active comparator `model_workbook_sources` rows from the workbook snapshot.

The compiler must fail closed if a generation role has no editor family, the same active model/role resolves to multiple sheets, or family key/type metadata is missing. Do not copy `MODEL_SHEET_ROLES` or `ROLE_SHEET_SUFFIX` into new code.

For target sheet identity:

1. Reuse a unique existing target `model_workbook_sources` sheet name, including an inactive scaffold registration, when its role/family is valid.
2. If no row exists, use `base_model_config(target)` only for the generic role-to-sheet-name convention; do not use a model allowlist.
3. Existing target-sheet headers are authoritative.
4. For a missing target sheet, derive the canonical header vector only when all active live sheets registered to that family agree exactly. Conflicting or absent family headers create a blocking metadata exception. `EDITOR_SHEET_META` must never be treated as a header list.

### 4.2 Deterministic serialization and fingerprints

All primary JSON artifacts use UTF-8, sorted object keys, stable sorted arrays, compact semantic hashing, and one trailing newline. No artifact binds its own hash or a downstream artifact. Authority staleness and semantic invalidation are separate contracts:

1. `runAuthorityFingerprint` contains the exact source/workbook SHA and `mtime_ns`; full-file SHAs for `sheet-roles.json`, `option-candidates.json`, `price-rows.json`, `join-report.json`, and `model-selection.json`; target/comparator source-role rows; active `rule_phrase_map`; and compiler policy/schema version. Any authority change forces one coherent rebuild of all generated compiler JSON artifacts. This fingerprint belongs to artifact envelopes and is excluded from subject, resolution-entry, derivation, row, and artifact semantic hashes.
2. The compiler partitions semantic evidence under stable evidence IDs: `targetEvidenceFingerprint[model]` for that target's inclusion/variant selection, raw candidates/status/price evidence, and existing target rows (explicitly excluding its comparator assignment); `comparatorEvidenceFingerprint[target]` for the selected comparator assignment and normalized comparator facts relevant to that target; `phraseEvidenceFingerprint[phraseKey]` for each active phrase-map row; and `workbookEvidenceFingerprint[evidenceId]` for each exact header/metadata/reference row used by a subject or derivation. Compiler policy/schema version is a dependency of every subject and derivation.
3. `comparator-evidence.json` binds `runAuthorityFingerprint` in its envelope. Its `comparatorEvidenceSemanticSha` hashes only normalized comparator facts/dispositions and their partition fingerprints.
4. `exception-queue.json` binds the current authority and comparator artifact in its envelope. Each pre-resolution subject records a sorted `evidenceDependencies` list of stable evidence ID plus semantic fingerprint. `subjectVersion` hashes the subject's stable semantic identity, that exact dependency list, and compiler policy/schema version. `queueSubjectFingerprint` hashes the sorted subject definitions. Applying a resolution does not remove or rewrite its subject definition; the queue contains no resolution SHA or resolution-derived lifecycle state.
5. `exception-resolutions.json` binds the current `queueSubjectFingerprint` in its file envelope for coherent readback, but that envelope change does not invalidate every entry. Each resolution entry is valid only when its own `subjectId` and `subjectVersion` still match a current queue subject. `resolutionSemanticSha` hashes only sorted currently valid entries consisting of `subjectId`, `subjectVersion`, typed action, canonical typed payload, and resulting disposition. Unchanged matching entries remain valid when unrelated queue subjects change; stale/superseded entries remain auditable but are excluded from `resolutionSemanticSha` and cannot affect the manifest.
6. Each manifest derivation records its own sorted `evidenceDependencies`; `derivationVersion` hashes the row's semantic signature, that exact dependency list, and compiler policy/schema version. `canonical-row-manifest.json` binds the current artifact envelopes plus `queueSubjectFingerprint` and `resolutionSemanticSha`, while its semantic hash covers reconciled rows/actions and per-row derivation versions. A context-only comparator change may update evidence/report context but may not change an unambiguous target-derived row's ID, values, action, or semantic signature.
7. `compile-report.json` binds the current authority/comparator/queue/resolution/manifest envelopes and hashes its semantic coverage, disposition, readiness, blocker, and deferral content. Nothing upstream binds the report.
8. `exception-log.jsonl` is outside the semantic artifact graph. Each event binds the relevant `queueSubjectFingerprint`, `subjectId`, `subjectVersion`, prior/next lifecycle state, and resolution-entry semantic hash when applicable.

Selective invalidation is evaluated during the required coherent rebuild; it never means keeping a mixed-generation subset of aggregate JSON files. A changed target evidence partition invalidates that target's dependent subjects/derivations. A comparator assignment/fact change invalidates only subjects/derivations listing the changed comparator evidence ID. A phrase-map row change invalidates only relationships listing that `phraseKey`. A workbook row/header/metadata change invalidates only dependents listing that evidence ID. A changed global compiler policy/schema version invalidates all subjects/derivations. If a changed input cannot be mapped safely to stable evidence partitions, fail closed and invalidate all subjects/derivations rather than claiming selective reuse.

Canonical semantic hashes exclude all self-hash fields; downstream hashes; artifact-envelope authority bindings; absolute paths; filesystem mtimes; generated/review/audit timestamps; reviewer display identity; JSON formatting/key order; transient staging filenames; session UI state; and diagnostic prose that is not part of a reason code, typed payload, proposed row, evidence reference, or gate result. They include schema/policy versions, normalized typed business values, stable IDs/signatures, evidence dependency IDs/fingerprints, dispositions, readiness fields, and canonical row/action content. Full-file SHA-256 values may still be recorded in envelopes and later approvals for byte-exact authority, but they are never inputs to the semantic hash of the same file or an upstream file.

Tests must construct the acyclic dependency graph; fail on any self-edge, reverse edge, queue-to-resolution edge, or semantic-hash change caused only by an excluded field; and prove that changing one comparator fact or phrase row leaves unrelated subject versions, resolution validity, derivation versions, and target-row semantics unchanged.

### 4.3 Stable IDs

Existing semantic matches always retain their current IDs. Every current workbook ID remains reserved even if its row is proposed for deletion.

For genuinely new rows, ID allocation is deterministic and model-local:

- option IDs follow the existing `opt_<normalized-rpo>_<three-digit occurrence>` form. Occurrence numbers are assigned by sorted durable occurrence signature against all reserved IDs, never by input row order.
- every other generated ID always ends with the first 12 lowercase hex characters of SHA-256 over the canonical semantic signature. The exact forms are `<model>_rule_<source-rpo>_<rule-type>_<target-rpo>_<digest>`, `<model>_group_<source-rpo>_<group-type>_<digest>`, `<model>_excl_<digest>`, `<model>_pr_<condition-rpo>_<target-rpo>_<digest>`, and `<model>_default_<target-rpo>_<digest>`. Tokens are lowercase `[a-z0-9_]`; blank/non-option semantic endpoints use their normalized entity type plus stable target identity, never a comparator ID.
- allocation may not contain comparator IDs, source row numbers, timestamps, iteration order, or display order.

Tests must lock the final formatter before other compiler tasks depend on it. No implementer-selected alternate ID scheme remains open after Task 2.

### 4.4 Desired-state reconciliation

`identity.py` owns all matching, allocation, desired-versus-existing comparison, incoming-reference impact, and final manifest actions. `compiler.py` may propose complete rows but may not choose workbook IDs itself.

Matching order is the parent design §6.6 contract: full occurrence signature; RPO + section + status vector + price signature; unique one-to-one remaining occurrence. More than one valid match is a blocking exception. Fuzzy text scores are forbidden.

Deletion is conservative. An unmatched existing target row defaults to `retained_existing`; it becomes `delete` only when target source evidence proves removal or a current typed retention/removal resolution says so. A delete with a surviving incoming reference remains blocked and carries the full reference preview.

### 4.5 Exception contract in this milestone

Milestone 1 builds exception schemas, validators, deterministic queue generation, subject/version invalidation, and direct Python resolution consumption. It does not add browser cards, HTTP routes, resume UI, bulk controls, or generic approval/skip actions.

Allowed nonblocking deferral remains only `asset_map_media_missing`, using the existing `ALLOWED_WRITE_DEFERRAL_KINDS` policy. All other applicable unsupported families are blocking.

Legacy `decisions.json` is not compiler input. `compile_canonical_rows()` must refuse `decisions_in_progress`, `decisions_complete`, and historical plan/apply states rather than silently migrate old decisions. A later explicit migration pass may convert validated non-copied decisions into proposed exception resolutions. Milestone 1 validates and consumes resolution artifacts through the compiler API, but session-level resolve/reopen persistence methods and their HTTP/UI workflow belong to Milestone 2.

### 4.6 Milestone boundary

The following stay unchanged in Milestone 1:

- `plan_builder.py` and all `pass-c-2` operation projection;
- `scripts/ingest_wizard_server.py` routes;
- `visualizer/ingest-wizard/**`;
- `scripts/ingest_wizard_apply.py` and Milestone 0 writer authority;
- `scripts/promote_model.py`;
- runtime generators, runtime JavaScript, registry publication, and dealer submission.

The compiler may emit a ready manifest, but it must not call `editor_ops.apply_batch()`, `build_plan()`, generation, registry publication, or promotion.

## 5. Implementation tasks

### Task 1: Add compiler artifact and exception contracts

Files:

- Create `scripts/corvette_form_generator/ingest/wizard/canonical_rows.py`.
- Create `scripts/corvette_form_generator/ingest/wizard/exceptions.py`.
- Create `tests/test_ingest_wizard_canonical_rows.py`.
- Create `tests/test_ingest_wizard_exceptions.py`.
- Modify `tests/ingest_wizard_fixtures.py`.

Steps:

- Write failing tests for all schema names, the exact acyclic dependency order in §4.2, authority-envelope versus semantic-dependency separation, required top-level fingerprints, semantic-hash field inclusion/exclusion, canonical row shape, exact headers, typed values, allowed actions/statuses/dispositions, readiness fields, and deterministic serialization. Include negative assertions that `exception-queue.json` cannot contain/hash `resolutionSemanticSha` and that `runAuthorityFingerprint` cannot enter a subject, resolution-entry, derivation, row, or artifact semantic hash.
- Add artifact constructors/validators for `canonical-rows-1`, `exception-queue-1`, resolution state, and `compile-report-1` support types. Validation must reject unknown actions/statuses/dispositions, duplicate stable IDs, incomplete row values, missing evidence, invalid Boolean storage, and unresolved ready-row keys.
- Add deterministic `subjectId`, `exceptionId`, and `subjectVersion` construction. `subjectId` excludes mutable evidence; `subjectVersion` includes only the sorted stable evidence IDs/fingerprints actually listed in that subject's `evidenceDependencies` plus compiler policy/schema version.
- Add resolution validation and stale-resolution classification. Resolution payloads are typed by exception kind; there is no unrestricted JSON payload or generic approve/skip action.
- Add the closed deferral allowlist and a test proving arbitrary blockers cannot be relabeled as deferrals.
- Add fixture tables for `rule_phrase_map` and the complete role/global header surface needed by later tasks.

Focused gate:

```sh
.venv/bin/python -m pytest \
  tests/test_ingest_wizard_canonical_rows.py \
  tests/test_ingest_wizard_exceptions.py -q
```

### Task 2: Implement occurrence-aware identity and desired-state reconciliation

Files:

- Create `scripts/corvette_form_generator/ingest/wizard/identity.py`.
- Create `tests/test_ingest_wizard_identity.py`.
- Modify `tests/ingest_wizard_fixtures.py`.

Steps:

- Write failing tests for unique RPO matching, duplicate-RPO occurrence signatures, exact staged matching order, stable existing-ID reuse, deterministic new IDs, reserved retired IDs, and input reorder invariance.
- Implement normalized option occurrence signatures using role, resolved section, normalized copy identity, variant status vector, price signature, and distinguishing relationship/group role. Exclude source coordinates/order, display order, comparator values, and timestamps.
- Lock the ID format from §4.3 with fixture tests covering options, direct rules, rule groups, exclusive groups, price rules, and defaults.
- Build desired-versus-existing diffing with exact canonical key/type comparison and `add`, `update`, `delete`, `noop`, `retained_existing`, and blocked outcomes.
- Reuse the Milestone 0 canonical reference metadata from `editor_ops.py` to construct incoming-reference impact. Do not duplicate typed conditional-reference rules in `identity.py`.
- Add tests for OVS reuse by `(option_id, variant_id)`, ambiguous duplicate refusal, conservative unmatched-existing retention, same-plan reference remap, and unresolved referenced-delete exceptions.

Focused gate:

```sh
.venv/bin/python -m pytest \
  tests/test_ingest_wizard_identity.py \
  tests/test_editor_ops_global_families.py \
  tests/test_editor_ops_meta.py -q
```

### Task 3: Build the active comparator evidence index

Files:

- Create `scripts/corvette_form_generator/ingest/wizard/comparator_evidence.py`.
- Create `tests/test_ingest_wizard_comparator_evidence.py`.
- Modify `tests/ingest_wizard_fixtures.py`.

Steps:

- Write failing tests for exact selected-comparator loading, rejection of inactive comparator scaffolds, active source-role registration, occurrence-aware ID-to-RPO resolution, and stable evidence IDs/signatures.
- Establish comparator eligibility through `discover_generation_model_configs(workbook_path)`, then use that resolved comparator `ModelConfig`. Do not treat `load_model_config_overrides()` or an isolated active option-sheet row as proof of complete comparator registration.
- Load direct rules and price rules as structurally valid authored rows while retaining endpoint activity in evidence. Mirror `rules.load_rule_groups()` and `rules.load_exclusive_groups()` active group/member filtering exactly; do not broaden runtime topology.
- Index direct rules, rule groups, exclusive groups, defaults, and price rules under the signatures in parent design §7.3. Normalize blank scopes to `*`; make member order irrelevant; invalidate exact matches with duplicate/unresolved members.
- Preserve active and inactive duplicate RPO occurrences separately. More than one runtime-active occurrence makes portable RPO matching ambiguous.
- Mark option-to-interior and other nonportable entities `context_only_nonportable_entity`; never resolve them through target option IDs.
- Emit target endpoint/member presence and one explicit disposition for every applicable comparator fact. Comparator prices are context fields only and never enter target row proposals.
- Prove that swapping comparator inputs cannot alter an unambiguous target-derived canonical row signature.
- Prove that changing one comparator fact changes only dependency-linked subject/derivation versions; an unrelated target subject's existing resolution remains valid after the coherent rebuild.

Focused gate:

```sh
.venv/bin/python -m pytest tests/test_ingest_wizard_comparator_evidence.py -q
```

### Task 4: Replace phrase hints with workbook-directed relationship compilation

Files:

- Create `scripts/corvette_form_generator/ingest/wizard/relationship_compiler.py`.
- Create `tests/test_ingest_wizard_relationship_compiler.py`.
- Modify `scripts/corvette_form_generator/ingest/wizard/hints.py`.
- Modify `tests/test_ingest_wizard_hints.py`.

Steps:

- Write failing tests for active phrase-map loading/fingerprinting, stop phrases, target syntax, endpoint resolution, direction, scope, and all comparator evidence tiers.
- Make `hints.py` a legacy advisory adapter over the same normalized phrase scanner used by `relationship_compiler.py`. Remove `PHRASE_PATTERNS` as business truth; legacy hint labels may remain output compatibility only.
- Use `runtime_metadata.load_rule_phrase_map()` with no Python fallback phrases on the production compiler path. A missing/header-only map is a blocking metadata exception; fallback behavior remains available only to existing non-compiler consumers.
- Compile explicit unambiguous target direct/group relationships without comparator support. Record exact comparator agreement as corroboration and explicit disagreement as `not_applicable_target_diff` when target evidence is clear.
- Emit one prefilled exception for Tier D comparator-backed direct/group/exclusive proposals. Comparator-only facts never become ready rows.
- Prove `Included with (PEF)` maps to `PEF includes <source>`, no implicit reverse/symmetric rule is added, partial groups do not auto-accept, and `replaces` without active workbook representation becomes an exception.
- Prove that changing one phrase-map row stales only relationship subjects/derivations listing that `phraseKey`; an unused phrase-row change leaves all existing subject versions and resolutions valid.
- Classify non-product prose as `resolved_not_a_workbook_fact` only when no product endpoint/relationship semantics exist. Product-like prose with unresolved endpoints remains a blocking exception.

Focused gate:

```sh
.venv/bin/python -m pytest \
  tests/test_ingest_wizard_relationship_compiler.py \
  tests/test_ingest_wizard_hints.py -q
```

### Task 5: Compile target metadata, variants, options, OVS, sections, and prices

Files:

- Create `scripts/corvette_form_generator/ingest/wizard/compiler.py`.
- Create `tests/test_ingest_wizard_canonical_compiler.py`.
- Modify `scripts/corvette_form_generator/ingest/wizard/parser.py`.
- Modify `tests/test_ingest_wizard_parser.py`.
- Modify `tests/ingest_wizard_fixtures.py`.

Steps:

- Write failing tests for workbook snapshot/family registry validation, exact live headers, model metadata, variants/base prices, options, OVS, section derivation, display order, base prices, conditional price rules, and explicit option Booleans.
- Additively preserve each numeric price cell's source header text/coordinate in `price-rows.json` and base-price evidence. Keep all existing keys and joins stable. Compiler scope derivation may use only explicit qualifier/header/model-code evidence; missing or ambiguous scope becomes a typed price exception, never a column-position inference.
- Consume existing `option-candidates.json`, `price-rows.json`, `join-report.json`, `sheet-roles.json`, and model selection. Do not reparse or modify the raw workbook.
- Implement parent design §6.6 exactly:
  - retain compatible target section identity;
  - require two independent agreeing active non-target precedents for automatic precedent-based section derivation;
  - allow the selected comparator as only one corroborator;
  - resolve an explicit source heading only through one live `section_master` row;
  - otherwise emit one finite section exception;
  - retain matched display order unless target evidence explicitly changes it;
  - give new rows deterministic section-local source order without using that order for identity;
  - compile uniform target prices to option base price;
  - compile only fully resolved target conditional price rows to `override` rules;
  - emit typed exceptions for conflicts, prose-only qualifiers, missing conditions, or unresolved scopes;
  - resolve variant identity by model/trim/body semantics and require target-derived year/label/base price;
  - keep new `variant_master`, `model_variants`, model metadata, source-role, and registry-promotion rows explicitly inactive/unpromoted.
- Set `selectable` and `active` explicitly on every option row. If target evidence and canonical presentation semantics cannot determine them, block the row; never use blank runtime fallback.
- Send all candidate rows through `identity.py`; `compiler.py` may not allocate IDs directly.
- Prove same-input determinism, source-row reorder invariance, ZR1/ZR1X existing ID reuse, no wholesale clear, no comparator price/section/default transfer, and no model-specific branch.

Focused gate:

```sh
.venv/bin/python -m pytest \
  tests/test_ingest_wizard_canonical_compiler.py \
  tests/test_ingest_wizard_identity.py \
  tests/test_ingest_wizard_parser.py \
  tests/test_ingest_wizard_joiner.py -q
```

### Task 6: Close all family and source-feature coverage

Files:

- Modify `scripts/corvette_form_generator/ingest/wizard/compiler.py`.
- Modify `scripts/corvette_form_generator/ingest/wizard/canonical_rows.py`.
- Modify `tests/test_ingest_wizard_canonical_compiler.py`.
- Modify `tests/ingest_wizard_fixtures.py`.

Steps:

- Write failing tests proving no parsed/skipped source feature and no registered generator/global family can disappear between input and report.
- Compile relationship rows through `relationship_compiler.py`, then reconcile direct rules, groups/members, exclusive groups/members, price rules, defaults, and variant overrides through `identity.py`.
- For interiors, `model_interior_scope`, `interior_components`, `color_overrides`, presentation families, and media:
  - retain compatible established target rows only when target identity/scope remains valid;
  - compile a reusable presentation profile only when one exact workbook-owned profile validates against the target section/variant set;
  - emit a typed blocking exception when applicable source is unparsed, ambiguous, or target-specific facts are missing;
  - use `allowed_deferral` only for `asset_map_media_missing`;
  - never copy comparator product rows to fill coverage.
- Build the source-feature ledger with exactly one allowed disposition per candidate, skipped row, price row, skipped price row, relationship phrase, status symbol, group candidate, and applicable comparator fact.
- Fail compilation on duplicate/missing ledger entries or on any required family whose zero-row state is not proven complete/not applicable.
- Build per-model readiness: `compileReady` is true only with zero blocking exceptions and complete coverage. `planReady`, `writeReady`, and `deploymentReady` remain false with milestone-boundary reasons.
- Prove new/unsupported Color and Trim source cannot silently disappear, presentation copied from a lone comparator is refused, and no non-media blocker can be downgraded to a deferral.

Focused gate:

```sh
.venv/bin/python -m pytest \
  tests/test_ingest_wizard_canonical_compiler.py \
  tests/test_ingest_wizard_relationship_compiler.py \
  tests/test_ingest_wizard_comparator_evidence.py \
  tests/test_ingest_wizard_exceptions.py -q
```

### Task 7: Add the headless session lifecycle and artifact invalidation

Files:

- Modify `scripts/corvette_form_generator/ingest/wizard/session.py`.
- Modify `tests/test_ingest_wizard_session.py`.
- Create `tests/test_ingest_wizard_compiler_session.py`.

Steps:

- Add `STATE_COMPILED_WITH_EXCEPTIONS` and `STATE_COMPILED_READY` to the production state machine without making either state plan/write authority.
- Add `WizardSessionStore.compile_canonical_rows(run_id)` as the only Milestone 1 orchestration entrypoint. It must load/verify all bound artifacts, invoke the compiler, validate all outputs in memory, write every JSON through a same-directory temporary file plus `os.replace()`, and update `session.json` last. A crash-partial artifact set must fail cross-binding validation and be safely rebuildable; it may never appear as a compiled session. The service may initialize an empty `exception-resolutions.json`; it must not fabricate reviewer resolutions.
- Refuse compile from legacy decision/plan/apply states. Permit idempotent recompile from `models_selected` and both compiled states.
- Add a direct Python method to load compiler detail. Resolution validation/consumption is tested through the compiler API; do not add session resolve/reopen persistence, change `session_detail()` response shape, or add HTTP routes in this milestone.
- Add one `_invalidate_compiler_artifacts()` helper and call it from `confirm_roles()`, `run_parse()`, and `select_models()` before persisting changed upstream authority. It evicts the generated comparator/manifest/queue/report aggregate cache and resets compiled state to the correct upstream state so no mixed-generation file set can be served. It preserves `exception-resolutions.json` plus `exception-log.jsonl`; the next coherent compile revalidates each resolution entry by its own `subjectId`/`subjectVersion` dependency contract rather than marking the whole file stale because its queue envelope changed. It must not touch legacy decision/plan/apply runs.
- On recompile, classify stale resolutions and regenerate queue/report/manifest. Append an audit event only when a subject actually changes lifecycle state (`open`, `resolved`, `stale`, or `superseded`) or a distinct typed resolution is recorded. Compute `eventId = sha256(canonical(eventType, subjectId, subjectVersion, priorState, nextState, resolutionEntrySemanticSha, causeFingerprint))`; timestamps and reviewer display identity are excluded. Before append, reject an `eventId` already present in `exception-log.jsonl`. An unchanged recompile therefore appends nothing, and a replayed transition cannot duplicate the log event.
- If any downstream `apply-plan*`, plan/write approval, dry-run, or apply-report artifact exists, refuse compilation and require an explicit fresh run; do not delete or rewrite ambiguous historical evidence.
- Add tests for crash-safe artifact replacement, aggregate-cache eviction without mixed files, selective resolution reuse after an unrelated authority change, dependency-linked stale transitions, unchanged-recompile audit idempotency, duplicate-`eventId` suppression, downstream-artifact refusal, state transitions, and preservation of legacy runs.

Focused gate:

```sh
.venv/bin/python -m pytest \
  tests/test_ingest_wizard_compiler_session.py \
  tests/test_ingest_wizard_session.py \
  tests/test_ingest_wizard_plan.py \
  tests/test_ingest_wizard_apply.py -q
```

### Task 8: Run the Milestone 1 proof and close the checkpoint

Files:

- Modify `docs/ingest/milestone-1-headless-compiler-comparator-evidence-implementation-plan.md`.
- Modify `docs/ingest/canonical-row-compiler-exception-queue-design.md`.
- Modify `docs/ingest/README.md`.
- Modify `Order-Guide_IngestPrompt.md` only if its current route/status pointer becomes false.
- Inspect `README.md`; update only if a stable user-facing command or validation owner actually changes.
- Transient only: fresh fixture/ignored compiler runs under `form-output/ingest-wizard/`.

Steps:

- Syntax-check the new module boundary before the test run:

  ```sh
  PYTHONPATH=scripts .venv/bin/python -m py_compile \
    scripts/corvette_form_generator/ingest/wizard/canonical_rows.py \
    scripts/corvette_form_generator/ingest/wizard/comparator_evidence.py \
    scripts/corvette_form_generator/ingest/wizard/identity.py \
    scripts/corvette_form_generator/ingest/wizard/relationship_compiler.py \
    scripts/corvette_form_generator/ingest/wizard/compiler.py \
    scripts/corvette_form_generator/ingest/wizard/exceptions.py \
    scripts/corvette_form_generator/ingest/wizard/session.py
  ```

- Run the full focused Milestone 1 gate:

  ```sh
  .venv/bin/python -m pytest \
    tests/test_ingest_wizard_canonical_rows.py \
    tests/test_ingest_wizard_canonical_compiler.py \
    tests/test_ingest_wizard_comparator_evidence.py \
    tests/test_ingest_wizard_relationship_compiler.py \
    tests/test_ingest_wizard_exceptions.py \
    tests/test_ingest_wizard_identity.py \
    tests/test_ingest_wizard_compiler_session.py \
    tests/test_ingest_wizard_parser.py \
    tests/test_ingest_wizard_joiner.py \
    tests/test_ingest_wizard_hints.py \
    tests/test_ingest_wizard_session.py \
    tests/test_ingest_wizard_decisions.py \
    tests/test_ingest_wizard_plan.py \
    tests/test_ingest_wizard_apply.py \
    tests/test_model_config_metadata.py \
    tests/test_runtime_metadata_guards.py \
    tests/test_editor_ops_apply.py \
    tests/test_editor_ops_global_families.py \
    tests/test_editor_ops_meta.py -q
  ```

- Run the full Python suite with `.venv/bin/python -m pytest -q`. Classify any red separately as new regression or reproduced baseline; do not rewrite unrelated tests/data to force green.
- Run workbook package and schema validation read-only:

  ```sh
  .venv/bin/python scripts/validate_workbook_package.py stingray_master.xlsx
  .venv/bin/python scripts/validate_workbook_schema.py stingray_master.xlsx
  ```

- Build one fresh fixture-backed greenfield run and one fixture-backed reprocess run through `WizardSessionStore.compile_canonical_rows()`. Require all five primary artifacts, exact ledger coverage, comparator dispositions, stable IDs, and byte-identical artifacts after an unchanged recompile.
- Create one mandatory fresh ignored wizard run from `2027 Chevrolet Car Corvette Export (4) (1).xlsx`. Verify its source SHA-256 is still `6ac9538d5bb8a823ade9afea70b2654057b793e1cf27c081c088545aa3add8a1`; if it differs, stop and report source drift rather than substituting an older run or export. Profile and confirm roles, run the current parser/joiner, then select targets `grand_sport_x`, `zr1`, and `zr1x` with comparators `grand_sport`, `z06`, and `z06` respectively. Do not clone decisions, plans, approvals, or compiler outputs from D.2.
- Invoke `WizardSessionStore.compile_canonical_rows()` on that fresh run against the current read-only `stingray_master.xlsx`. `compiled_with_exceptions` is an acceptable result. Closure requires: every parsed/skipped/source/comparator feature has exactly one disposition; all exceptions/blockers are typed; existing target identity matches are stable or explicitly ambiguous; the acyclic artifact bindings validate; an unchanged second compile preserves all semantic hashes and appends no audit event; and no plan, approval, apply, backup, generation, publication, or promotion artifact is created.
- Capture `shasum -a 256 stingray_master.xlsx` before and after. Require identical SHA and mtime, no `~$stingray_master.xlsx` interaction, no backup/edit log, and no apply/approval artifacts.
- Require `git diff --quiet -- form-output/runtime form-app/data.js visualizer/ingest-wizard scripts/ingest_wizard_apply.py scripts/promote_model.py` after restoring any test-created churn. Inspect `git status --short` and preserve unrelated pre-existing work.
- Update this plan and the parent design with implementation date, exact changed files/artifacts, gate output, residual risks, and Milestone 2 as the next checkpoint. Follow `AGENTS.md` §12 for the handoff.

## 6. Exact implementation file set

Expected new files:

- `scripts/corvette_form_generator/ingest/wizard/canonical_rows.py`
- `scripts/corvette_form_generator/ingest/wizard/comparator_evidence.py`
- `scripts/corvette_form_generator/ingest/wizard/identity.py`
- `scripts/corvette_form_generator/ingest/wizard/relationship_compiler.py`
- `scripts/corvette_form_generator/ingest/wizard/compiler.py`
- `scripts/corvette_form_generator/ingest/wizard/exceptions.py`
- `tests/test_ingest_wizard_canonical_rows.py`
- `tests/test_ingest_wizard_canonical_compiler.py`
- `tests/test_ingest_wizard_comparator_evidence.py`
- `tests/test_ingest_wizard_relationship_compiler.py`
- `tests/test_ingest_wizard_exceptions.py`
- `tests/test_ingest_wizard_identity.py`
- `tests/test_ingest_wizard_compiler_session.py`

Expected modified files:

- `scripts/corvette_form_generator/ingest/wizard/parser.py`
- `scripts/corvette_form_generator/ingest/wizard/hints.py`
- `scripts/corvette_form_generator/ingest/wizard/session.py`
- `tests/ingest_wizard_fixtures.py`
- `tests/test_ingest_wizard_parser.py`
- `tests/test_ingest_wizard_hints.py`
- `tests/test_ingest_wizard_session.py`
- `docs/ingest/milestone-1-headless-compiler-comparator-evidence-implementation-plan.md`
- `docs/ingest/canonical-row-compiler-exception-queue-design.md`
- `docs/ingest/README.md`

Inspected-no-change unless evidence contradicts this spec:

- `scripts/corvette_form_generator/ingest/wizard/decisions.py`
- `scripts/corvette_form_generator/ingest/wizard/plan_builder.py`
- `scripts/corvette_form_generator/editor_ops.py`
- `scripts/corvette_form_generator/model_configs.py`
- `scripts/corvette_form_generator/runtime_metadata.py`
- `scripts/corvette_form_generator/rules.py`
- `scripts/ingest_wizard_server.py`
- `scripts/ingest_wizard_apply.py`
- `scripts/promote_model.py`
- `visualizer/ingest-wizard/**`
- `form-output/runtime/**`
- `form-app/data.js`
- `README.md`
- `Order-Guide_IngestPrompt.md`

Expansion beyond the expected file set requires review because it likely exceeds the pinned additive price-header evidence change or crosses into Milestone 2 browser/API work, Milestone 3 plan/apply proof, generator behavior, or workbook schema.

## 7. Companion-file impact

| Surface | Milestone 1 disposition |
|---|---|
| Canonical workbook | Read-only input; hash/mtime proof required; no backup or write log expected |
| Raw import | Read-only evidence; source fingerprint bound into artifacts |
| Existing parser/join artifacts | Consumed and fully dispositioned; no schema rewrite in this milestone |
| `plan_builder.py` / `pass-c-2` | Preserved historical/debug path; never called by compiler |
| Apply CLI / writer | Milestone 0 behavior preserved and covered by regression tests |
| Generated contracts / `form-app/data.js` | Untouched; no generation/publication gate in this milestone |
| Browser/server | No new route or UI; Milestone 2 owns compile/exception browser flow |
| Runtime/dealer | Inspected-no-change; no live submission or runtime smoke needed |
| Docs | Plan, parent status, and ingest index close together after implementation |
| Profile/Codex guidance | Not applicable unless implementation discovers a durable workflow correction |

## 8. Risks and stop conditions

- Stop if any artifact depends on itself or a downstream artifact, if queue subjects depend on resolutions, or if an excluded audit/filesystem field changes a semantic hash.
- Stop if an unrelated comparator, phrase, target, or workbook evidence change alters an unaffected `subjectVersion`, invalidates an unaffected resolution, or changes an unambiguous unaffected target row.
- Stop if the mandatory fresh current-export run cannot be created and compiled. Fixture proof cannot substitute for this gate; report the exact reproducibility blocker.
- Stop if a target fact can only be supplied by comparator product data. Emit an exception; do not copy it.
- Stop if active family sheets disagree on canonical headers for a missing target sheet. Do not invent a header schema.
- Stop if a semantic identity has more than one valid existing match. Do not use fuzzy copy similarity or source row order.
- Stop if phrase direction cannot be represented by active `rule_phrase_map`. Do not fall back to `hints.py` truth.
- Stop if any parsed/skipped feature or applicable comparator fact lacks exactly one disposition.
- Stop if making `compileReady=true` would require broadening the closed deferral policy.
- Stop and request scope approval if implementation requires parser changes beyond the additive price-header evidence defined in Task 5, editor metadata changes, generator/runtime behavior, a public API, or workbook structure.
- Do not use a hardcoded minimum row count as proof of completeness. Coverage is ledger/evidence based.

## 9. Non-goals

- Browser exception cards, resume UI, compile/readiness screens, or new server routes (Milestone 2).
- `pass-c-3` projection, `plan_builder.py` replacement, scratch apply/generation, registry discovery proof, or write eligibility (Milestone 3).
- Fresh all-target production closure or deployment-ready report (Milestone 4).
- Live workbook write, runtime publication, registry publication, or model promotion.
- Migrating or deleting historical D.2 decisions/runs.
- Retiring legacy Pass 0–5/debug routes.
- Filling missing colors, interiors, assets, prices, defaults, or relationships from comparator data.
- New dependencies, workbook columns, schemas, model-specific branches, or runtime/dealer changes.

## 10. Approval record

Sean approved this Milestone 1 spec on 2026-07-12 after the selective-invalidation contract and parent-design heading typo were corrected. Approval authorizes Milestone 1 implementation and its read-only fixture plus mandatory current-export compiler proofs on `ingest-wizard`.

It does not authorize Milestone 2 browser/API implementation, Milestone 3 plan projection or temporary deployment proof, Milestone 4 real-data closure, `--write`, workbook mutation, runtime/registry publication, or model promotion.
