# Ingest Separation, Three-Model Integration, and Editor Consolidation Spec

Status: APPROVED 2026-07-18. Sean approved the boundaries, pathway, and written spec. Implementation remains gated by the implementation plan and its phase-specific approvals. This approval does not itself authorize a live workbook write, publication, promotion, deployment, or dealer changes.

Document ownership: `canonical-row-compiler-exception-queue-design.md` continues to own compiler semantics and the currently implemented safety contract. This spec owns the approved separation, shared ChangeSet migration, three-model workbook integration sequence, and editor consolidation destination. When implementation completes, update the existing owner documents in place; do not add another competing workflow guide.

## 1. Plain-English outcome

Finish the current work without building another overlapping system.

The completed system has:

1. One small ingest module that accepts a raw order guide, derives everything it can, asks only necessary questions, and emits a shared ChangeSet.
2. One shared workbook service that validates, previews, approves, writes, rolls back, and records every ChangeSet.
3. One workbook editor UI that uses that same service.

Grand Sport X, ZR1, and ZR1X are integrated into `stingray_master.xlsx` through that shared path before the two editor UIs are consolidated.

## 2. Current diagnosis

The canonical compiler is not the primary failure. Run `20260717-091317-470292` already compiled Grand Sport X, ZR1, and ZR1X with zero blockers and proved the proposed result against temporary workbooks.

The failure is ownership:

- The ingest wizard contains the current compiler/typed-exception path and the historical broad-decision path.
- It also owns plan building, plan approval, write approval, temporary deployment proof, and live-write continuation.
- The workbook editor exposes a separate historical Ingest Review workflow.
- The Workbook Manager introduces another schema, validation, staging, and synchronization authority.
- All three eventually depend on `editor_ops`, but they do not share one final ChangeSet contract or one declarative workbook registry.

This produces broken navigation, hidden operations, duplicated validation, and uncertainty about which system is authoritative.

## 3. Fixed boundaries

These boundaries are approved and are not implementation choices.

### 3.1 Ingest owns only five functions

The standalone ingest module owns:

1. Raw source intake.
2. Profiling and target selection.
3. Canonical compilation.
4. Typed exception resolution.
5. Emission of a shared ChangeSet.

Ingest does not own:

- workbook-write approval;
- workbook mutation;
- backup or rollback;
- generated-artifact refresh;
- registry publication;
- runtime promotion;
- deployment; or
- dealer submission.

### 3.2 The workbook remains canonical

`stingray_master.xlsx` remains the product/business source of truth. SQLite, browser state, ingest artifacts, and ChangeSets are projections, proposals, journals, or evidence. None may become a second workbook authority.

### 3.3 Historical ingest is read-only

Historical Pass B/C/D.2 decisions and plans remain available only as evidence. A current compiler session may not navigate into, copy from, complete, approve, or mutate a historical workflow state.

### 3.4 One editor survives

The existing workbook editor remains the fallback writer until replacement parity is proven. The Workbook Manager React UI is the likely final UI, but it may not retain an independent schema, validator, writer, or canonical row store.

### 3.5 Protected behavior stays unchanged

This work does not change product rules, prices, availability, generated runtime contracts, the dealer endpoint, dealer payloads, Turnstile behavior, submission UX, dependencies, or deployment paths unless a separate approved decision explicitly requires it.

## 4. Simple target architecture

```text
Raw order guide
    -> ingest: intake
    -> ingest: profile and select targets
    -> ingest: compile canonical rows
    -> ingest: resolve typed exceptions
    -> ingest: emit ChangeSet

ChangeSet
    -> shared workbook service: preview and final-state validation
    -> explicit approval
    -> guarded workbook write, rollback, and readback
    -> ChangeReceipt

Canonical workbook
    -> existing generators and validators
    -> explicit registry publication/promotion when separately approved
```

There is no direct ingest-to-workbook write path and no editor-specific writer.

## 5. Shared workbook contract

### 5.1 One declarative workbook registry

Create one registry, derived from the current `editor_ops` metadata and live workbook registration tables, that owns:

- sheet-family and model-sheet resolution;
- headers, keys, types, nullability, and enums;
- model scope;
- direct, union, and conditional references;
- parent/child and delete dependencies;
- writable versus read-only surfaces; and
- final-state validation order.

The ingest ChangeSet emitter, shared workbook service, both editor UIs during transition, import/projection code, and tests consume this registry. Workbook Manager metadata may be migrated into it only when it adds a proven contract missing from the current registry. It may not remain a parallel authority.

### 5.2 ChangeSet proposal

The immutable proposal uses schema `workbook-changeset-1` and contains:

- ChangeSet ID and deterministic semantic fingerprint;
- source kind and source/run identifiers;
- selected target models;
- canonical workbook SHA-256 and mtime preconditions;
- required sheet creations, including family and exact header template;
- row changes identified by sheet, family, and canonical key;
- field-level changes rather than unrelated full-row replacement;
- exact before and after values;
- add/delete values represented as empty-before/full-after or full-before/empty-after;
- row-level provenance and evidence identifiers;
- compiler manifest and resolution fingerprints when the source is ingest;
- explicit no-op coverage receipts when the source compiler accounts for unchanged rows; and
- requested warning acknowledgements, without granting write authority.

The ChangeSet does not contain an editable copy of workbook rows and cannot approve itself.

### 5.3 Preview and execution receipts

Mutable lifecycle state does not rewrite the ChangeSet. The shared service emits receipts bound to its semantic fingerprint:

- `ChangePreview`: final-state validation, warnings, operation coverage, and temporary readback.
- `ChangeApproval`: operator, scope, accepted warning IDs, ChangeSet fingerprint, workbook fingerprint, and preview fingerprint.
- `ChangeReceipt`: applied/failed/rolled-back status, backup path, exact readback, validation results, timestamps, and post-write gate reminders.

An editor or ingest UI may display these receipts, but only the shared workbook service creates them.

## 6. Three implementation phases

This is one completion program with three phases. Do not create a new design or milestone document for each slice. Record phase status and evidence in this file.

### Phase 1 — Separate ingest and establish the shared path

#### Goal

Make the five-function ingest module real without changing the proven compiler result.

#### Work

1. Extract the shared workbook registry from the current active metadata path.
2. Implement `workbook-changeset-1`, its deterministic fingerprint, and strict parsing.
3. Add a ChangeSet adapter to `editor_ops` so the shared final-state validator remains the one validation/write engine.
4. Fix the existing writer before any live use:
   - preserve and recheck the originally reviewed workbook SHA/mtime immediately before save;
   - refuse any drift during validation;
   - restore the backup automatically if post-write readback fails; and
   - report whether a failed write was untouched or rolled back.
5. Add a pure ingest emitter that translates an exact-current ready canonical manifest into a ChangeSet without choosing IDs, values, sheets, actions, or business meaning.
6. Replace the current compiler-path “Build canonical apply plan” continuation with “Create ChangeSet.”
7. Remove write approval and apply continuation from the ingest UI/API.
8. Make historical decision, copy, complete, plan, and approval routes read-only or unavailable to current sessions.
9. Remove the existing workbook editor's normal-navigation Ingest Review tab. Historical evidence may remain available through an explicitly labeled read-only archive surface.

#### Required equivalence proof

Before implementation begins, independent verification must freeze one authoritative snapshot of run `20260717-091317-470292`. The current on-disk `apply-plan.json` was written after the Milestone 3 closeout text and its projection counts differ from that text. Do not silently choose either version or carry both forward. Reconcile the difference, update the owning Milestone 3 closeout with the verified snapshot, and bind the emitter proof to that snapshot.

The frozen authoritative snapshot of run `20260717-091317-470292` is verified and recorded in the Milestone 3 closeout. The canonical manifest (`canonical-row-manifest.json` SHA-256 `b3e32dea5afeaf10eb6296d82283ff844403a80da1f3659b6ad20d5d0409926f`) contains 6,408 rows: 2,581 `add`, 941 `update`, and 2,886 `noop`. The frozen projection binds `apply-plan.json` SHA-256 `0b91bffdfc8643bdbfc31ffcb40695601d6d721ae122652ba95598cad30dd5fe`: 3,719 operations (50 stage-1, 3,669 stage-2) comprising 3,710 row operations (2,765 `add`, 945 `update`) and nine `create_sheet` operations naming the Grand Sport X isolated target sheets `grand_sport_x_exclusive_groups`, `grand_sport_x_exclusive_members`, `grand_sport_x_options`, `grand_sport_x_ovs`, `grand_sport_x_price_rules`, `grand_sport_x_rule_groups`, `grand_sport_x_rule_mapping`, `grand_sport_x_rule_members`, and `grand_sport_x_variant_overrides`. Of the row operations, 3,709 are manifest-backed and one is the separately identified inactive Grand Sport X promotion scaffold `op-03718` (non-manifest `add` to `model_registry_promotion` with `active=false`, `promoted_to_runtime=false`). Coverage: 6,408/6,408 manifest rows covered, 2,699 explicit no-op receipts, zero uncovered rows. Companion artifact hashes: `apply-plan-dryrun.json` SHA-256 `097579feaa83ff515fd9edeb132c1aeb4d19440d22ed45a4c30cf0846f3b0a00` (3,719/3,719 operations prepared and read back exactly), `compile-report.json` SHA-256 `ffa8215adab91d903bed70999b2f3951d291d1946784935714e622cdcf9d4e4d`, and `exception-resolutions.json` SHA-256 `c47335d13fccddf0248bb777eba8cb684888f32921daa95c591d3e37e8a09c65` (158 entries, `queueSubjectFingerprint` `0634e4e0ba2b628e02b88d6325e2ea2aa3d5cfa5eb32aba7e4a69b05f647cf79`). Task 5's equivalence test must reproduce this same semantic projection from the manifest — identical row coverage, the nine named sheet creations, the one named scaffold, and the no-op receipts — against these frozen hashes. These are characterization facts, not permanent contract constants.

For the frozen authoritative snapshot, the new emitter must preserve the already-reviewed result:

- every manifest row covered exactly once by a row change or no-op receipt;
- every non-manifest sheet creation or inactive scaffold separately named and justified;
- zero uncovered rows;
- zero changed keys, values, stable IDs, actions, or semantic signatures; and
- byte-identical protected workbook, raw source, generated artifacts, and runtime publication files.

The existing `pass-c-3` plan remains immutable evidence. It is not relabeled as a ChangeSet and is not production write authority after this phase.

#### Phase 1 completion gate

Phase 1 is complete only when:

- the current ingest path exposes exactly the five owned functions;
- ingest code cannot call `apply_batch()`, `save_workbook_safely()`, generation, publication, or promotion;
- a current session cannot enter or mutate legacy workflow state;
- the shared service rejects stale, malformed, partial, or off-target ChangeSets;
- injected writer drift is refused before save;
- injected post-write verification failure restores the backup and verifies restoration; and
- the Milestone 3 closeout and frozen run artifacts describe the same authoritative snapshot; and
- the frozen-run equivalence proof passes.

No live canonical-workbook write occurs in Phase 1.

### Phase 2 — Integrate Grand Sport X, ZR1, and ZR1X

#### Goal

Use the shared ChangeSet path to write the three proven models into the canonical workbook safely.

#### Preconditions

- Independent final verification of Milestone 3 passes.
- Phase 1 is complete.
- The current branch is reconciled with `main` while preserving `main`'s canonical workbook, generated artifacts, and real edit-log history.
- The compiler run and ChangeSet are rebuilt against the exact current workbook fingerprint. Old plans and approvals remain stale by design.
- Sean explicitly ratifies the live-write interpretation already used in temporary proof:
  - Grand Sport X uses isolated target sheets for the 369 migrated rows;
  - N26's `$695` price uses wildcard scope because the source gives no narrower qualifier; and
  - the Grand Sport X promotion record remains inactive until a separate publication step.

#### Work

1. Recompile the three targets from current source/workbook inputs.
2. Resolve only newly produced typed exceptions; do not revive superseded broad review.
3. Emit one atomic all-target ChangeSet.
4. Preview it through the shared service on a temporary workbook.
5. Require exact row-operation coverage, package/schema validation, Boolean hygiene, final-state relationship validation, and readback.
6. Run the existing Grand Sport X + ZR1, ZR1X repeatability, and all-target generation/registry/runtime-contract proofs against temporary copies.
7. Present the exact ChangeSet summary, warnings, backup/rollback behavior, and affected sheets for explicit live-write approval.
8. Apply once to `stingray_master.xlsx` through the shared service.
9. Reopen the saved workbook, verify exact readback, package/schema integrity, and the backup on disk.
10. Regenerate all affected artifacts through the normal workbook-to-generator path and review every workbook/generated diff.

#### Task 8 approval checkpoint (2026-07-19)

The approved bounded recovery resolved both prior Task 8 blockers and stopped
at the required approval boundary. Exact-current run
`20260719-174505-0085ca` used raw-source SHA-256
`6ac9538d5bb8a823ade9afea70b2654057b793e1cf27c081c088545aa3add8a1`
against canonical-workbook SHA-256
`646f58e7c951963a43045b6cb5d351d7ff8e1b2460299bdf9b8cfa7d741b8379`.
Its final run-authority fingerprint is
`34c9356abf4dba0e8509378d3a42ae8823fe1124c93e3544eb3991811b372826`.

The changed queue was reconciled without bypassing its fingerprint or subject
version protections. Of the initial 206 subjects, 131 frozen valid resolutions
were reused only on exact `(subjectId, subjectVersion)` matches, eight
changed-version entries and 19 removed subjects were omitted, and all 75 new or
changed-version subjects were reviewed against current source/workbook and
approved comparator authority. One later derived price-scope subject reused an
exact frozen valid resolution only after reprojection emitted the same subject
and version. The final queue contains 203 resolved subjects, zero stale or
superseded entries, and zero deferrals. Its fingerprint is
`ce9ec6060b14be9fa0aac53b6d7d34c45fb920cbafc90bd000bab835c9564e56`;
the resolution semantic SHA is
`6ee7c1215bd476866b75f813ad68f2327df5c6303676899e22df7455793a137b`.
Current review confirmed eight exclusive-group, 17 price-rule, three
relationship, and 35 rule-group proposals, while retaining the eight
target-authoritative semantic-conflict rejections.

The final 6,691-row manifest contains 3,286 add, 891 update, and 2,514 noop
rows and has semantic SHA
`f9b3b2ddb0d9c08b0da56cdf6664722ee0f9e1d87f18fb17c6ef0edd8b77342a`.
The emitted `workbook-changeset-1` is
`5f108f09bb09d4dddafa18a6` with semantic fingerprint
`5f108f09bb09d4dddafa18a6a8eef97c6d3712d491701ca9d029d415e9421746`;
it creates 12 sheets, carries 4,204 row changes, and accounts for 2,488
noops. Shared preview passed with fingerprint
`03ecd79f2fbad407e41ec289868625ab7620a0000dc3ea0873e718069d51e8de`,
zero blocking or unknown warnings, and 21 confirmable greenfield scaffold
warnings.

`workbook_domain.deployment_proof.prove_changeset_deployment()` and
`scripts/prove_workbook_changeset.py` now provide the missing ChangeSet-aware
temporary proof path without restoring retired `pass-c-3` authority. The
GSX+ZR1, ZR1X repeatability, and all-target atomic phases all passed package,
schema, Boolean hygiene, exact readback, generation, runtime-contract,
registry-load, and semantic-signature checks. Proof fingerprint
`0e2a72e256668d3be13628cba613341e9ddf85722efe6ad53ddc2f91c6bc7a32`
has zero blockers and zero deferrals. An independent second temporary apply
covered all 4,216 prepared operations, checked 21,063 field pairs, preserved
all formulas across 65 existing sheets, and reproduced zero runtime semantic
mismatches for all targets.

The exact approval packet is
`/private/tmp/27vette-changeset-proof-20260719-174505-0085ca/task8-approval-packet.json`
(SHA-256
`8b1574dd5622643d7820bff35fe7813792d4fec147980a9cc04f33355f10827a`).
Independent workbook inspection also records that the generic `create_sheet`
writer copies exact headers but not template header font/style; 10 of the 12
new sheets therefore differ from their named header templates on that
workbook-authoring presentation detail. This does not affect package/schema,
runtime, registry, or dealer behavior, but remains visible for explicit Task 9
approval review.

The protected workbook, `form-app/data.js`, and real edit log remain
byte-identical to their recorded hashes. No `ChangeApproval`, canonical write,
publication, promotion, deployment, or dealer change was created. Task 8 is
complete; Task 9 remains blocked on Sean's explicit approval of this exact
packet.

#### Task 9 completion record (2026-07-19)

Sean approved the exact Task 8 packet and then separately approved the narrow
scratch-activation generation path required by the intentionally inactive
target metadata. ChangeSet `5f108f09bb09d4dddafa18a6` was applied once through
the shared service. ChangeReceipt SHA-256
`75095a18e240789ca06c9b333fafa1482328ebd444e270138dd39cdb4663141d`
records `status=applied`, 4,216/4,216 prepared operations read back exactly,
zero schema/Boolean errors, and backup
`backups/stingray_master-20260719-224756.xlsx`. The backup retains the approved
pre-write SHA-256 `646f58e7c951963a43045b6cb5d351d7ff8e1b2460299bdf9b8cfa7d741b8379`;
the integrated workbook SHA-256 is
`1c9bb513b147f6b3c5d91625719b04d6f297ddfd98d75072e8f8b3771a0a3219`.
Package and schema validation passed with zero issues, errors, or warnings.

The ordinary production CLI correctly continued to reject inactive models.
For pre-promotion artifact generation only, the existing deployment-proof
activator copied the saved workbook to `/private/tmp`, activated only
`grand_sport_x`, `zr1`, and `zr1x` in that scratch copy, passed package/schema,
Boolean hygiene, and 124-field exact activation readback, then supplied the
scratch-discovered configs to the normal generator. The canonical workbook was
byte-identical before/after that generation step. The resulting unpromoted
runtime contracts have SHA-256 values
`86c29263a73756404c26178f483a26448d870d6e592af7f89d7620732f0b3470`
(Grand Sport X),
`17fb57e18b59d472f6c3785887fef2e277209fdeb5b96483621a457551df24a5`
(ZR1), and
`12bf977278cb7b939ae098e415a1a1f8664149d83dd7fa0adf80bb0baca6667f`
(ZR1X), each with zero generated validation errors.

Affected gates passed: 75 Python tests; Stingray 89/89; Grand Sport 19/19;
Z06 24/24; multi-model runtime switching 47/47; workbook package/schema
validation; and `git diff --check`. Existing-model timestamp-only generator
churn and optional scratch inspection manifests were removed. `form-app/data.js`
remained at SHA-256
`565d22859292b3f514dfc177a7392402afc897c3e080be945b4d068995093230`.
The three targets remain inactive and unpromoted; no public registry,
deployment, runtime application code, or dealer-submission behavior changed.
Residual risk is the already-approved header font/style difference on 10 of 12
new sheets; no additional follow-up is implied before the separately approved
promotion phase.

#### Workbook integration definition

The three models are integrated when their approved canonical rows and registrations exist in `stingray_master.xlsx`, the workbook and generated contracts pass, and no unintended source/runtime changes exist.

Workbook integration does not itself activate the models publicly. Registry publication and runtime promotion remain a separate explicit approval and validation step.

#### Phase 2 completion gate

- One approved ChangeSet and one successful ChangeReceipt cover the full write.
- Backup, disk reopen, exact readback, package/schema, Boolean, and relationship gates pass.
- Grand Sport X, ZR1, and ZR1X generation and registry-load proofs pass from the saved workbook.
- Generated diffs match the approved ChangeSet's intended model scope.
- Existing Stingray, Grand Sport, Z06, and dealer behavior remain unchanged.
- The owning Milestone 3 and this spec record exact completion evidence and residual risk.

### Phase 3 — Consolidate to one workbook editor

#### Goal

Replace two competing editors with one UI over the shared registry and ChangeSet service.

#### Work

1. Keep the existing editor available as the fallback while parity is built.
2. Retain the Workbook Manager React UI as the likely destination.
3. Remove or bypass its independent schema, validation, full-row sync translation, and direct canonical-row authority.
4. Make every edit produce `workbook-changeset-1` field deltas against an exact workbook fingerprint.
5. Use SQLite only for:
   - a disposable read projection;
   - ChangeSet drafts;
   - append-only approvals and receipts; and
   - query/history views.
6. Block re-import while any approved ChangeSet is unsynchronized.
7. Provide retry, cancel, and rebase for failed or stale ChangeSets.
8. Validate parent/child changes against the proposed final batch state.
9. Show post-write state explicitly: workbook synchronized, generated artifacts stale/current, registry publication pending/current, and exact next gates.
10. Remove dead duplicate editor code and correct stale editor tests/copy only when the shared replacement path covers them.

Do not merge either Workbook Manager implementation wholesale. Reuse proven UI, database, lineage, audit, and contract-test work selectively after it is made subordinate to the shared registry and ChangeSet service.

#### Parity gate

The final editor must prove every writable collection and relationship supported by the existing editor, including:

- add/update/delete and field-level conflict detection;
- atomic parent/member changes;
- direct, union, and conditional references;
- stale workbook refusal;
- warning confirmation;
- failed-write rollback;
- failed-sync retry/cancel/rebase;
- exact preview/readback;
- model and shared-sheet scoping; and
- browser behavior at desktop and mobile widths.

Only after parity passes may the existing editor be retired and the Manager UI become the sole supported editor.

## 7. Scope controls that keep this simple

The implementation must not:

- redesign the compiler or repeat already resolved model review;
- invent a new workbook schema or business-rule taxonomy;
- create a second ChangeSet format;
- keep `pass-c-3` as a permanent parallel write contract;
- add a dependency without separate approval;
- combine workbook integration with public runtime promotion;
- rewrite the React UI before the shared service contract exists;
- rewrite the existing editor before replacement parity exists;
- retain writable legacy ingest routes for convenience;
- create additional pass/spec documents unless a genuinely new user decision blocks this owner spec; or
- merge unrelated branch cleanup, generated drift, workbook changes, or dealer work.

If code cannot fit these boundaries, stop and report the exact contradiction rather than adding another compatibility layer.

## 8. Stop conditions requiring Sean's decision

Stop before continuing if:

- source evidence requires a new price, availability, default, relationship, or other product decision;
- the new ChangeSet cannot represent an existing safe editor operation without changing workbook behavior;
- the frozen manifest-to-ChangeSet equivalence proof changes a reviewed key, value, action, or semantic signature;
- current `main` workbook changes create a real three-model reconciliation conflict;
- final-state validation disagrees with a current generator/runtime contract;
- a new dependency, workbook schema, generated contract, public interface, deployment path, or security boundary is required;
- rollback cannot prove the workbook was restored after an injected failure; or
- editor consolidation would remove a supported editing capability before parity exists.

Ordinary implementation difficulty, file size, or test count is not a reason to widen scope or create another workflow.

## 9. Validation ownership

Each phase runs only the gates relevant to its changed surface, followed by the full affected-path gate at phase close.

### Phase 1

- ChangeSet schema, fingerprint, malformed-input, stale-input, coverage, and equivalence tests.
- Shared registry contract tests against every active workbook family.
- Final-state relationship tests, including atomic parent/member changes.
- Writer race and rollback fault-injection tests.
- Current ingest compiler/session/API/UI tests.
- Static assertions that the current ingest path exposes no write/apply/promotion authority.
- Workbook package/schema validators and protected-surface hashes.

### Phase 2

- Fresh exact-current compiler and ChangeSet proof.
- Temporary apply/readback and all three deployment-proof phases.
- Approved live-write backup, reopen, package/schema, Boolean, final-state, and exact readback gates.
- Affected generator, registry, and runtime-contract tests.
- Existing-model regression gates.
- Generated diff and clean-tree/idempotency review.
- No live dealer submission.

### Phase 3

- Shared service and editor API contract tests.
- Frontend behavior tests for every writable family.
- Concurrency, re-import, stale edit, failed sync, retry/cancel/rebase, and rollback tests.
- Desktop/mobile browser parity.
- Existing editor comparison until retirement.
- Workbook package/schema and affected runtime regression gates.

All tests must isolate temporary workbooks, databases, receipts, and edit logs. Validation may not contaminate tracked audit history or generated artifacts.

## 10. Rollback

- Phase 1 changes no canonical product data. Roll back code/docs and retain the frozen compiler evidence.
- Phase 2 creates a verified backup before the single live write. Any failed post-write gate restores that backup automatically and proves the restored workbook fingerprint before returning failure.
- Phase 3 retains the existing editor until replacement parity passes. The Manager UI is not advertised as the supported writer before that gate.

## 11. Completion record

This section is updated in place as work completes. It is not a prompt to create another closure document.

- Phase 1 — complete on 2026-07-19. Tasks 1–5 established the frozen
  projection evidence, shared registry, strict `workbook-changeset-1`
  contract, guarded service/rollback path, and equivalent compiler emitter.
  Task 6 commits `c0c92fd` and `59f5e7a` narrowed the current browser/API to
  the five owned functions, retired the ingest apply CLI and historical
  mutation routes, and moved temporary deployment proof out of ingest. Task 7
  commit `9da2757` removed the fallback editor's embedded Ingest Review UI/API and dead React
  prototype while preserving Form Structure, Sheet Browser, Review, Pending
  Changes, typed operation payloads, and Apply behavior. The complete Phase 1
  gate passed `486 tests and 36 subtests`; both JavaScript syntax checks,
  workbook package validation, workbook schema validation, and `git diff
  --check` passed. The package/schema validators reported zero issues, errors,
  or warnings. The separately run `tests/test_editor_lints.py` produced only
  the three previously documented real-workbook reds (`d1_rwj_wks_collision`,
  `c2_cj2_stingray_name_deviator`, and `r3_drz_pending_review`), with 23 other
  tests passing. No canonical workbook, generated artifact, registry,
  promotion, deployment, runtime, or dealer surface changed.
- Phase 2 — complete on 2026-07-19. Task 8 rebuilt and proved the exact-current
  all-target ChangeSet; Task 9 applied it once, verified the backup and saved
  workbook, and generated the three inactive target contracts through the
  approved scratch-activation path. Publication and promotion remain separate.
- Phase 3 — blocked by successful three-model workbook integration and shared-service stability.
- Runtime publication/promotion — separate approval after Phase 2.
- Dealer submission changes — not authorized and not implied.
