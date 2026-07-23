# Reliable Workbook–Database Workflow Implementation Specification

Status: implementation in progress; Pass 1 completed 2026-07-22 and Pass 2
completed 2026-07-23 on `db-workflow`; Passes 3–7 not started. Revised
2026-07-22 after final
specification review. All fourteen review findings are resolved: primary-
runtime-only parity, strict publication selection, current baseline, outcome-
specific lifecycle states, interrupted-apply recovery, exception evidence,
acceptance-only generated parity, single readback authority, complete writable-
column ownership, non-circular write enablement, crash-safe two-store migration,
distinct restored outcomes, stale-projection permissions, and deferred UI work.
Recommended implementation reasoning: high.

## 1. Goal and authority boundary

Make the Workbook Manager a reliable editing interface around
`stingray_master.xlsx` without turning SQLite into a second source of Corvette
product behavior.

The workbook remains canonical. The manager consists of:

- a disposable, verified SQLite projection used for browsing and lookup;
- durable drafts and exact `workbook-changeset-1` lifecycle artifacts used to
  propose changes;
- the existing shared ChangeSet service as the only manager-to-workbook write
  route.

This work changes workflow reliability only. It does not change workbook
product data, generated form contracts, customer-facing form behavior,
publication decisions, deployment, or dealer submission.

Standing source-of-truth, workbook-safety, approval, validation, and handoff
requirements in `AGENTS.md` apply. This specification owns only the
Workbook Manager implementation direction.

## 2. Current evidence and baseline

The audit in `docs/db_audit-7-22.md` proved these defects against disposable
workbooks and databases:

1. Import clears and commits the active projection before the new source is
   validated.
2. Import findings do not prevent promotion; duplicate rows use first-wins.
3. Re-import ignores committed-unsynchronized work and can make stale full-row
   snapshots overwrite unrelated external workbook edits.
4. Staging validates individual rows against committed SQLite state instead of
   validating the proposed final workbook graph.
5. Sequential edits to one row become contradictory operations.
6. Failed sync work leaves the only pending queue and has no supported retry,
   requeue, or cancel path.
7. `workbook-manager/backend/app/specs.py` duplicates and disagrees with
   `scripts/corvette_form_generator/workbook_domain/registry.py`.
8. Unknown model ownership can commit and later be skipped because no target
   sheet resolves.
9. Manager sync binds mtime but not workbook SHA-256 or the reviewed operation
   set.
10. `editor_ops.apply_batch()` does not restore the backup when post-save
    readback raises an exception.
11. The FastAPI app shares a lazily initialized connection across request
    threads.
12. The API/browser lose model context for some model-key families and do not
    faithfully expose all reference metadata.

Current focused baseline, rerun on 2026-07-22:

```text
.venv/bin/python -m pytest tests/test_workbook_manager.py -q
2 failed, 26 passed, 2 skipped
```

The two existing failures are assigned before implementation:

- `TestStagingWorkflow.test_scaffold_model_rejected` belongs to Pass 2's model
  lifecycle matrix; do not change workbook lifecycle data to restore the stale
  expectation.
- `TestComparisonExport.test_export_preserves_unmanaged_and_row_counts` belongs
  to Pass 4's identity-copy-plus-overlay reconstruction. The current exporter
  removes 978 physically present trailing blank `PriceRef` rows. Pass 4 must not
  report this baseline failure as a newly introduced regression.

The 2026-07-16 relational design and plan are historical evidence only. Do not
implement their fixed three-model topology, prescribed module tree, or
SQLite-canonical direction.

## 3. Pinned architecture decisions

These decisions are not left to the implementing agent.

### 3.1 Separate disposable projection from durable workflow state

Use two physical stores:

- `workbook-manager/var/workbook_projection.sqlite3`: current verified
  workbook projection. Candidate import replaces only this file.
- `workbook-manager/var/workbook_manager.sqlite3`: durable manager state for
  drafts, immutable ChangeSet payloads, preview/approval/receipt artifacts,
  status transitions, failure detail, and legacy recovery records.

Support the same split under test/environment overrides. Add a dedicated
projection-path override rather than changing the meaning of `WBM_DB`.

The projection file must not contain the durable journal. Candidate promotion
must therefore be unable to erase drafts, approvals, receipts, retry history,
or unresolved legacy work.

The projection represents the last verified workbook import. Draft or committed
changes are overlays; they do not mutate projection rows before a proven
workbook write. After a successful workbook write, mark the projection stale
until a verified re-import succeeds.

Projection freshness has one permission matrix:

- `current`: browsing, comparison export, new drafts, preview, approval, and an
  exactly bound apply are permitted subject to lifecycle guards;
- `stale`: browsing and immutable history remain available with a persistent
  stale label; comparison export, new drafts, preview, approval, and apply are
  blocked; only verified re-import or manual recovery is permitted;
- `missing` or `unverified`: status/import and recovery evidence are available,
  but authoring and writes are blocked.

#### 3.1.1 First-start split migration

The current `WBM_DB` can contain both imported projection tables and durable
`pending_changes`/`change_history`. Split migration is the first Pass 2 action,
before any storage consumer changes.

- Keep `WBM_DB` as the durable-state path and add `WBM_PROJECTION_DB` for the
  projection path. New installations initialize both at schema version 1.
- At startup, under a Pass 2 process-local startup/migration lock and before
  any storage consumer runs,
  checkpoint and close the legacy database, hash it, and copy it to a unique
  same-directory temporary archive. Fsync and hash-verify the temporary copy,
  then atomically rename it to the hash-derived final archive name and fsync the
  parent directory. On restart, inspect only temporary files carrying this
  migration's owned prefix: if a temporary file hashes to the source hash,
  finish its atomic rename; if its hash differs or the copy is truncated, remove
  it and recopy from the still-authoritative legacy database; abort on any
  unowned/ambiguous candidate rather than deleting it. If the final archive
  already exists, verify and reuse it; never overwrite a mismatched final
  archive. Never migrate from a live WAL.
- Build both versioned target schemas in same-directory candidate files. Copy
  all current `TABLE_SPECS` family tables, `raw_sheet_rows`, `import_runs`,
  `import_issues`, and only `workbook_mtime_ns`, `workbook_sha256`, and
  `last_import_run_id` from `meta` to the projection candidate. Preserve any
  other legacy `meta` row as durable recovery evidence rather than guessing its
  ownership. Copy every `pending_changes` and `change_history` column value into
  durable read-only recovery records keyed uniquely by
  `(migration_id, source_table, source_primary_key)`; do not convert them into
  trusted ChangeSets. Each target stores one shared migration ID, source hash,
  schema version, and per-table source/destination row counts.
- Use `BEGIN IMMEDIATE` per candidate, reject duplicate migration IDs or row-
  count/fingerprint disagreement, commit/checkpoint/close, then fsync each
  candidate. Replace the disposable projection first and `WBM_DB` last. The
  durable database's completed migration marker is the commit point.
- A crash before durable replacement leaves the legacy source authoritative;
  restart rebuilds/replaces the disposable projection from the archived source.
  A crash after durable replacement verifies the matching projection marker and
  rebuilds only that disposable projection if absent or mismatched. Migration is
  therefore idempotent and never appends duplicate recovery rows.
- Retain the hashed legacy archive as read-only rollback/recovery evidence; do
  not delete it automatically. On any pre-commit failure, leave the legacy
  `WBM_DB` bytes authoritative and remove only incomplete candidates.

### 3.2 Adopt the existing ChangeSet contract; do not invent another

The manager must emit the exact immutable contract owned by:

- `workbook_domain.changeset` (`workbook-changeset-1`);
- `workbook_domain.service` (preview, approval, apply, receipt).

One user commit of the current draft emits one immutable ChangeSet. Before
emission, all edits to the same `(sheet, family, physical key)` coalesce into a
single original-to-final row change. The emitted payload may contain that
physical key only once.

Field pairs, workbook SHA-256/mtime, source sheet, family, key, provenance,
semantic fingerprint, preview fingerprint, approval fingerprint, warning
acknowledgements, and receipt must retain the meanings already defined by the
shared service. Do not create manager-specific variants of those fields.

### 3.3 Choose fail-closed staleness instead of automatic rebase

This implementation does not add field-level automatic rebase.

- Re-import is blocked while any non-cancelled draft exists or while a ChangeSet
  is in any state except the exact terminal allowlist: `applied`, `cancelled`,
  `manually_resolved_restored`, `manually_resolved_applied`, or
  `abandoned_unknown`. A `stale` ChangeSet is not terminal for this guard: its
  only verb is cancel, after which verified re-import may run and a new draft may
  be created. The three manual-resolution outcomes remain immutable history but
  explicitly permit the verified re-import they require.
- Preview/apply rejects any workbook SHA-256 or mtime drift.
- A stale ChangeSet remains visible but cannot be edited or written. The user
  may cancel it, re-import the workbook, and create a new draft.
- No stale full-row snapshot may be synchronized.

This preserves unrelated external workbook edits without adding a conflict
merge engine. Automatic field-level rebase is a separate future feature.

### 3.4 Reuse final-state validation

Draft collection may perform immediate shape/type/reference hints, but those
hints do not grant commit or write authority.

Authoritative validation is one projected-final-state run of the complete
coalesced ChangeSet through `preview_changeset()` and
`editor_ops.apply_batch(write=False)`. This is the existing shared operation
projection and validation boundary.

Parent/member additions, coordinated deletes, uniqueness, conditional and
union references, and model ownership must therefore be judged against the
complete proposed final graph. Remove `confirm_dependencies` as an integrity
bypass. Warning acknowledgement may confirm only warnings classified as
confirmable by the shared service.

### 3.5 Keep the existing SQL shape unless correctness requires less

This pass is not a relational redesign. Retain the current shared conceptual
tables unless a table must change to derive its schema from the shared registry
or to enforce verified import ownership/references. Do not create per-model
physical table families, a compiler framework, ORM layer, plugin system, or new
database dependency.

### 3.6 Keep the projection semantic and keep the workbook physical

Do not build a second cell store inside SQLite. The bound source workbook already
owns exact headers, cell values/types, formulas, formatting, and opaque columns.
Duplicating every cell in lineage tables would add storage and reconstruction
logic without making a field-level ChangeSet safer.

The projection stores only registry-owned semantic rows plus minimal lineage:
source workbook SHA-256/mtime, sheet name, source row, family, physical key, and
model context. Semantic values use the existing registry/editor coercion.

Mapping is pinned as follows:

- an allowed blank reference or optional typed value becomes SQL `NULL`;
- a required key, reference, boolean, integer, or enum with a blank value is a
  blocking import finding;
- nonblank unresolved references block promotion;
- required/optional field and reference metadata is writable contract behavior,
  so add it to `workbook_domain.registry` where currently absent;
- `editor_ops._prepare_batch()` must enforce that requiredness against each
  effective final row so import and later ChangeSet writes cannot disagree.

The shared registry owns the complete manager-writable field set for every
family, including free-text fields. It separately marks `required_on_add` and,
where applicable, `required_on_effective_active_row`; those sets may coincide
but may not be inferred by the manager. Delete operations are exempt from
after-value requiredness. Add/update validation runs after same-key edits are
coalesced and checks the effective final row. A known optional header absent
from the physical sheet cannot be synthesized by an ordinary row edit; adding a
header is a separate schema-authoring operation outside this pass. Opaque
columns are preserved by copy-plus-overlay but never appear in manager draft,
update, or ChangeSet payloads.

SQLite enforces primary/composite uniqueness only. Do not add a parallel SQL
foreign-key model. Ordinary, union, conditional, `option_rpos`, section/variant,
and model-scoped references all remain shared projected-final-state semantic
checks. This avoids encoding only a misleading subset of the workbook graph in
DDL while the shared service remains the actual write authority.

Comparison export and parity reconstruction start from a temporary copy of the
exact bound source workbook. They refuse SHA-256/mtime drift and overlay only
registry-owned projected fields or draft ChangeSet fields through the shared
editor operation path. Untouched sheets, columns, cells, formulas, and formatting
therefore remain workbook-owned without being copied into SQLite.

### 3.7 Use one complete projection/import catalog

`catalog.py` must classify every workbook sheet before import and every column on
a managed sheet. It does not copy unmanaged sheet contents into SQLite.

The current catalog classes are:

1. **Source-role writable families** from `SOURCE_ROLE_FAMILIES`:
   `options`, `ovs`, `rule_mapping`, `rule_groups`, `rule_group_members`,
   `exclusive_groups`, `exclusive_members`, `price_rules`,
   `variant_overrides`, `color_overrides`, and `interiors`. Physical sheet names
   come only from active `model_workbook_sources` rows.
2. **Fixed-sheet writable families** from `GLOBAL_SHEET_FAMILIES`:
   `model_master`, `model_variants`, `variant_master`,
   `model_workbook_sources`, `model_registry_promotion`,
   `model_interior_scope`, `default_selection_rules`, `asset_map`,
   `interior_components`, `runtime_steps_meta`,
   `section_presentation_meta`, `context_section_master_meta`,
   `order_summary_sections_meta`, and `step_order_summary_map_meta`.
3. **Managed read-only sheet**: `section_master`, used for section/step lookup
   and Form Structure fallback. It is projected but cannot emit a ChangeSet.
4. **Known workbook-preserved sheets**: `PriceRef`, `context_choice_copy`,
   `rule_phrase_map`, and `runtime_rule_exceptions`. Record their sheet
   disposition but leave their contents in the bound workbook.
5. **All remaining workbook sheets**: `workbook_preserved_unknown`. Record the
   disposition only. Encountering one is informational, not permission to
   interpret, edit, or duplicate it in SQLite.

Required sheet ownership comes from `schema_validation.REQUIRED_SHEETS` plus
active source-role registrations. Required columns, optional columns, keys, and
writable fields come from the shared registry/schema-validation owners. The
adapter assembles those sources mechanically and fails if they disagree; it
does not copy their lists by hand.

For every managed sheet, column reconciliation is name-based and deterministic:

- reordered unique known headers are accepted;
- a duplicate header is blocking because owned-cell identity is ambiguous;
- a missing required header is blocking;
- a missing optional header remains absent;
- a renamed header is treated as one missing required/optional header plus one
  unknown header; no fuzzy rename is allowed;
- an extra header is recorded as opaque and remains untouched in the workbook;
- blank trailing rows are not source rows;
- every nonblank managed row receives one import or blocking-exclusion
  disposition; workbook-preserved rows are not copied into the projection.

Candidate reconciliation must prove both the sheet and managed-row accounting:

```text
all workbook sheets
  = managed writable sheets + managed read-only sheets + workbook-preserved sheets

managed nonblank rows
  = imported managed rows + explicit blocking exclusions
```

The candidate report includes sheet dispositions, managed-row dispositions, and
opaque managed-column names. Comparison export follows Section 3.6; it never
rebuilds an unmanaged sheet or fills unknown headers from database defaults.

### 3.8 Pin primary-runtime-only generated-contract acceptance

The only customer-runtime workflow acknowledged by this specification is:

```text
canonical workbook
  -> discover_generation_model_configs()
  -> canonical source assembly and runtime-contract construction
  -> form-output/runtime/<slug>-runtime-contract.json
  -> generate_registry.py under separate publication authority
  -> form-app/data.js
  -> static customer runtime
```

For this manager pass, generation is isolated acceptance or an external
post-write gate. Registry publication remains outside the manager. No
compatibility JSON/CSV writer, current-generation/draft promotion input, legacy
fallback/alias behavior, ingest deployment proof, publication, or deployment is
part of manager execution.

Add `workbook-manager/backend/app/contract_parity.py` with one public helper:

```text
generate_contract_snapshot(workbook_path, output_root, model_key)
```

The helper calls `discover_generation_model_configs(workbook_path)`, selects the
requested discovered config, and uses `ModelConfig.with_overrides()` to set
`root=output_root`, `workbook_path=workbook_path`,
`output_dir=output_root/form-output`, and `app_dir=output_root/form-app`. It then
calls `source_assembly.assemble_model_source(config)`, takes only
`assembly.runtime_contract`, validates that contract with
`registry_promotion.assert_runtime_contract()`, and writes only
`runtime_contract_artifact_path(output_root, model_key)` through the repository
JSON writer.

Do not call `generate_model_artifacts()`,
`write_stingray_compatibility_artifacts()`, any inspection/preview/draft writer,
or `generate_registry.py`. Do not change `production.py`, patch globals, or
change cwd/environment. Assert that exactly one runtime-contract file appears
under the temporary root and that compatibility JSON/CSV, inspection, preview,
draft, registry, `form-app/data.js`, tracked output, and source-workbook hashes
are unchanged.

The acceptance parity set is stricter than `load_registry_promotions()`. Read
every workbook promotion row directly. First collect every row whose `active`
and `promoted_to_runtime` values are true; this unfiltered promoted-row set is
the complete preflight input. Fail the entire preflight if any such row lacks
`artifact_type == "runtime_contract"`, does not resolve exactly to
`runtime_contract_artifact_path(repo_root, model_key)`, or names a model absent
from `discover_generation_model_configs()`. Only after that all-row validation
passes may those rows become the acceptance parity set. Empty/header-only
promotion metadata, `current_generation`, `draft_artifact`, compatibility
JSON/CSV, noncanonical paths, fallback registry behavior, and `legacy_alias`
are not consumed or tested by this pass; an active/promoted row using one of
those historical forms is a blocking preflight error, never a silently excluded
row.

This generation is a slow acceptance/regression proof for importer and
copy-plus-overlay reconstruction, not a production projection-promotion gate.
The production gate uses exact managed semantic readback plus workbook package
and schema validation. The focused acceptance test generates source and
reconstructed contracts in separate temporary roots and compares them with
`scripts/compare-generated-contracts.mjs`; expected timestamps are ignored and
every other difference fails the test.

## 4. State and transition contract

Persist exact immutable artifacts and a small manager state machine. Status is
batch-level because the workbook write is atomic.

Legal lifecycle (the state alone determines the allowed verbs):

```text
draft
  -> cancelled
  -> changeset_emitted

changeset_emitted
  -> preview_ready
  -> preview_retryable
  -> preview_rejected
  -> stale
  -> cancelled

preview_retryable
  -> preview_ready
  -> preview_retryable
  -> preview_rejected
  -> stale
  -> cancelled

preview_rejected
  -> cancelled

stale
  -> cancelled

preview_ready
  -> approved
  -> approval_confirmation_required
  -> approval_repreview_required
  -> approval_rejected
  -> stale
  -> cancelled

approval_confirmation_required
  -> approved
  -> approval_confirmation_required
  -> approval_repreview_required
  -> approval_rejected
  -> stale
  -> cancelled

approval_repreview_required
  -> preview_ready
  -> preview_retryable
  -> preview_rejected
  -> stale
  -> cancelled

approval_rejected
  -> cancelled

approved
  -> applying
  -> stale
  -> cancelled

applying
  -> applied
  -> apply_retryable
  -> apply_rejected
  -> approval_confirmation_required
  -> approval_repreview_required
  -> stale
  -> apply_restored_retryable
  -> workbook_state_unknown

apply_retryable | apply_restored_retryable
  -> applying
  -> cancelled

apply_rejected
  -> cancelled

workbook_state_unknown
  -> manually_resolved_restored
  -> manually_resolved_applied
  -> abandoned_unknown
```

Rules:

- `draft` is mutable; emitted ChangeSets and lifecycle artifacts are immutable.
- Preview retry reuses the immutable ChangeSet but emits a new preview artifact.
  It is allowed only for a transient `locked`/read failure while the workbook
  still matches the ChangeSet identity. Invalid, stale, empty, or semantically
  failed proposals must be cancelled and recreated.
- Apply retry reuses the exact ChangeSet, preview, and approval identities. It
  is allowed only when the workbook still matches the bound SHA-256/mtime and
  the prior attempt proves `untouched` for a transient pre-save failure or a
  formal receipt proves `restored`.
- `preview_retryable` permits only retry-preview or cancel;
  `preview_rejected` permits only cancel/recreate as a new draft.
- `approval_rejected` permits only cancel/recreate as a new draft. It is the
  result of an approval exception that returned no service dictionary; returned
  approval refusals continue to use the outcome-specific states below.
- `apply_retryable` means a transient pre-save failure with base SHA/mtime and
  `untouched` proven. `apply_restored_retryable` means a formal writer result
  proves the backup was restored and hash-verified. Both permit only exact-
  artifact retry or cancel. `apply_rejected` permits only cancel/recreate.
- `workbook_state_unknown` blocks retry, import, and new write approval until a
  manual recovery step records the live workbook hash and resolves the outcome.
  `manually_resolved_restored` is terminal only when the base hash is proven;
  `manually_resolved_applied` is terminal only when exact final rows are proven;
  `abandoned_unknown` preserves unresolved evidence. All three require verified
  re-import before new authoring and are distinct from retryable restoration.
- Cancellation never deletes history. It makes the draft/ChangeSet ineligible
  for preview or write.
- A successful retry is idempotent: one workbook mutation and one terminal
  applied receipt. Repeating the request returns the existing terminal result.
- Legacy `pending_changes`/`change_history` rows are never silently converted
  into trusted ChangeSets. On migration, preserve them in a read-only recovery
  record with their original JSON and status. If any are staged or unsynced,
  keep import/write containment active until they are explicitly cancelled or
  recreated as a reviewed draft.

Every preview, approval, and apply call has one immutable manager-owned attempt
envelope. It contains phase, unique attempt ID, ChangeSet/preview/approval IDs,
started/completed timestamps, the returned dictionary verbatim when one exists,
exception class/message when no dictionary exists, independently proven
workbook state/hash evidence, resulting manager state, and allowed verbs. This
envelope is manager evidence and does not extend a public service schema.

The `approved -> applying` transition and creation of a unique apply-attempt row
must commit atomically before invoking the shared writer. A durable uniqueness
constraint permits at most one active apply attempt per ChangeSet. Before any
apply request invokes the writer, it returns an existing terminal receipt,
rejects an active attempt, or proves the exact retryable state. During startup,
any orphaned `applying` attempt becomes `workbook_state_unknown`; it is never
retried automatically. Manual resolution follows the hash/final-row rules above.

Only an allowlisted lock/transient read exception with unchanged base identity
maps preview to `preview_retryable`; any other exception with known unchanged
identity maps to `preview_rejected`. If preview cannot prove the current base
identity, it maps to `stale`; preview is read-only and never creates unknown
physical-write state. Only an allowlisted transient pre-save apply exception
with the base identity proven maps to `apply_retryable`; any other pre-writer
exception with unchanged identity maps to `apply_rejected`. If apply cannot
independently prove unchanged identity, it maps to `workbook_state_unknown`, not
to a retryable state.

An exception raised by `approve_changeset()` before it returns a dictionary maps
to `approval_rejected`. The manager persists the exception attempt envelope,
allows only cancel, and never fabricates an approval artifact or retries approval
from hidden exception detail.

### 4.1 Shared-service outcome mapping

Do not extend the public ChangeSet/preview/approval/receipt schemas to carry
manager status. Persist each returned dictionary unchanged, record whether it
is a formal schema artifact or an early refusal, and derive manager state with
this mapping:

| Service phase/outcome | `workbookState` | Manager state | Allowed next action |
|---|---|---|---|
| Preview `validated` and `ok=true` | n/a | `preview_ready` | approve or cancel |
| Preview `invalid_changeset`, `invalid`, `empty`, `bool_hygiene_failed`, `schema_failed`, or `warning_blocked` | n/a | `preview_rejected` | cancel and recreate |
| Preview `stale` | n/a | `stale` | cancel only |
| Preview `locked`, `readback_failed`, or transient read exception with unchanged workbook identity | n/a | `preview_retryable` | retry preview or cancel |
| Approval success | n/a | `approved` | apply or cancel |
| Approval `warning_confirmation_mismatch` | n/a | `approval_confirmation_required` | resubmit exact warning IDs or cancel |
| Approval `preview_not_validated`, `binding_mismatch`, or `warning_blocked` | n/a | `approval_repreview_required` | re-preview the exact ChangeSet or cancel |
| Approval exception with no returned dictionary | n/a | `approval_rejected` | cancel only |
| Apply `applied` | `saved` | `applied` | no further write; mark projection/generated/publication state stale |
| Apply `stale` or `stale_before_save` | `untouched` | `stale` | cancel only |
| Apply `locked` or transient pre-save exception with base SHA/mtime proven | `untouched` | `apply_retryable` | exact-artifact retry or cancel |
| Apply `warning_confirmation_mismatch` or `needs_confirmation` | `untouched` | `approval_confirmation_required` | resubmit exact warning IDs or cancel |
| Apply `approval_invalid`, `binding_mismatch`, or `warning_blocked` | `untouched` | `approval_repreview_required` | re-preview exact ChangeSet or cancel |
| Apply `invalid`, `empty`, `schema_validation_required`, `readback_failed`, `bool_hygiene_failed`, or `schema_failed` | `untouched` | `apply_rejected` | cancel/recreate; no retry |
| Apply `apply_verification_failed_rolled_back` | `restored` | `apply_restored_retryable` | exact-artifact retry if base SHA/mtime is proven, or cancel |
| Apply `workbook_restore_failed` or any uncontained exception after save may have begun | `unknown` | `workbook_state_unknown` | manual resolution only |

An exception before `apply_changeset()` reaches the shared writer is
`untouched` only when the live SHA-256 proves the original base. Otherwise it is
`workbook_state_unknown`. Early refusal dictionaries are attempt evidence, not
fabricated `workbook-change-receipt-1` artifacts.

## 5. Model and schema authority

### 5.1 Workbook family contract

`scripts/corvette_form_generator/workbook_domain/registry.py` is the only
writable family/key/type/enum/reference authority.

Add one manager adapter at
`workbook-manager/backend/app/catalog.py`. It may add database-only facts such
as SQL table name, source-role routing, fixed-sheet routing, display label, and
lineage columns. It must import key/type/enum/reference/conditional-reference
semantics from the shared registry rather than restating them.

Migrate importer, DDL, validation hints, API schema responses, UI controls,
ChangeSet emission, and comparison export to this adapter. Delete
`backend/app/specs.py` only after no production or test import remains.

Add a mechanical parity test that enumerates every writable registry family and
proves that the manager adapter exposes the same key, types, enums, ordinary
references, union references, and conditional references.

### 5.2 Model lifecycle sets

Derive and name four different sets:

- **known**: every nonblank unique `model_master.model_key`;
- **editable/importable**: a family-dependent predicate over active workbook
  model metadata and the family's routing mode;
- **generatable**: the exact result of
  `model_configs.discover_generation_model_configs()`;
- **published/current-runtime**: the strict Section 3.8 set: active
  `model_registry_promotion` rows with `promoted_to_runtime=True`,
  `artifact_type="runtime_contract"`, a canonical resolved runtime-contract
  path, and a model in the generatable set.

Do not duplicate the generation predicate. Reuse
`discover_generation_model_configs()` for the generatable set. Derive the
published/current-runtime set from raw workbook rows plus canonical path
resolution; do not use the compatibility-capable `load_registry_promotions()`
reader, legacy fallback, or `legacy_alias` for this set.

Unknown models are always rejected. A model need not be published to be a valid
editable/importable workbook model. Apply this ownership matrix; do not reduce
it to one generic `model_scoped` boolean:

| Family class | Families | Context/routing | Ownership predicate | `*` | Add/bootstrap policy |
|---|---|---|---|---|---|
| Model-scoped source-role rows | `options`, `ovs`, `rule_mapping`, `rule_groups`, `rule_group_members`, `exclusive_groups`, `exclusive_members`, `price_rules`, `variant_overrides` | request `model_key` plus exact active source-role registration and physical sheet | model is known and active; exact `(model_key, source_role)` is active; sheet exists and matches imported lineage | rejected | rows may be added only for an existing active model/role |
| Shared/physical source-role rows | `interiors`, `color_overrides` | physical source sheet and row lineage; record the set of active registrations resolving to that sheet | at least one active registration for the family's role resolves to the exact sheet; emit one physical operation even when several models share it | rejected | no manager-created source sheet or source registration |
| Model definition | `model_master` | fixed sheet; row's `model_key` | existing row defines known identity; active is not required to edit that row | rejected | adding a new `model_master` key is outside this implementation |
| Model topology | `model_workbook_sources`, `model_variants` | fixed sheet; row's `model_key` | model already exists in `model_master`; active is not required so an existing inactive scaffold can be completed; referenced sheet/variant must exist before activation | rejected | may add topology for an existing model; cannot create a new model |
| Publication metadata | `model_registry_promotion` | fixed sheet; row's `model_key` | model is known; setting an active/promoted state requires the model to be active and generatable | rejected | may add a row for an existing model only; publication remains a separate authorized decision |
| Active-model fixed-sheet content | `model_interior_scope`, `default_selection_rules`, `interior_components`, `runtime_steps_meta`, `section_presentation_meta`, `context_section_master_meta`, `order_summary_sections_meta`, `step_order_summary_map_meta` | fixed sheet; row's `model_key` | model is known and active; family references validate in that model's projected final graph | rejected | no rows for unknown/inactive models |
| Wildcard-capable assets | `asset_map` | fixed sheet; row's `model_key` | concrete key requires a known active model; `*` is a reserved shared scope, not a model | allowed only here | `*` target must resolve for at least one active imported model and may not bypass `target_type -> target_id` validation |
| Model-independent definitions | `variant_master` | fixed sheet; no model owner | family key/reference contract only | n/a | normal row add through ChangeSet |
| Managed read-only | `section_master` | fixed sheet | browse/reference target only | n/a | no ChangeSet emission |

For manager-writable families, no wildcard or blank model key is accepted
except the exact `asset_map` `*` case above. A concrete model key and `*` remain
distinct physical keys. Wildcard semantic validation evaluates the target
against the union of active imported model domains; it does not invent one
target model or require the target in every model. Workbook-preserved sheets such
as `context_choice_copy` may contain `*`; those tokens remain workbook-owned and
do not grant manager write authority.

New-model bootstrap is deliberately not implemented by this reliability pass.
Creating a new `model_master` key, its source sheets, source-role rows, variant
memberships, and publication metadata remains an existing workbook-tooling task
with separate business/source approval. The manager may complete or edit rows
for an already-known inactive scaffold according to the matrix, but it may not
create the defining model identity. This avoids both circular unknown-model
guards and a new bootstrap workflow.

Replace the stale scaffold test with matrix-derived fixture assertions:
unknown rejected, inactive model content rejected, inactive topology editable,
inactive source role rejected, active source-backed unpublished model accepted,
shared physical rows emitted once, fixed-sheet model-key families accepted
without invented source-role rows, `asset_map` `*` accepted only under its
special rule, and publication state does not grant edit ownership.

## 6. Implementation passes

Implement in order. Keep containment active until Pass 7 explicitly re-enables
the reviewed ChangeSet write path. Each pass is a reviewable vertical slice;
do not reorganize the repository first.

### Pass 1 — Contain unsafe paths

Required changes:

1. Refuse `POST /api/sync` when `write=true` with an explicit provisional/read-
   only response. Remove or disable the browser write control; do not hide a
   still-callable write route behind CSS.
2. Refuse re-import when an active projection exists until candidate promotion
   is implemented. A first import into a new empty projection is allowed, but
   must not be reported as verified when blocking findings exist.
3. Independently refuse import while any unresolved legacy staged,
   committed-unsynchronized, or failed row exists, or while any manager draft/
   ChangeSet falls outside Section 3.3's exact terminal allowlist. Do not treat
   `manually_resolved_restored`, `manually_resolved_applied`, or
   `abandoned_unknown` as import blockers; verified re-import is their required
   recovery action.
4. Keep browsing and, where the Section 3.1 freshness matrix permits it,
   comparison export available. Clearly label exported files disposable and
   keep them outside tracked workbook/generated paths.
5. Show a persistent `Read-only / provisional` banner and report projection,
   draft, workbook, generated-artifact, and publication states separately.
6. Update `workbook-manager/README.md` and the root README pointer so neither
   describes live manager sync as currently safe.

Pass 1 exit gate: no API or browser path can mutate `stingray_master.xlsx` or
destructively replace an existing projection database.

Pass 1 result — completed 2026-07-22:

- Added seven disposable containment regressions and observed all seven fail
  against the pre-pass implementation before production edits. They now pass.
- `POST /api/sync` returns `409 read_only_provisional` for every `write=true`
  payload, including a fully populated legacy confirmation payload. The browser
  write control was removed; only `write=false` dry-run remains callable.
- Initial import into an empty projection remains available. Replacement import
  returns `409` before importer invocation whenever a projection is active or
  unresolved staged, committed-unsynchronized, or failed legacy work exists.
  The existing projection row/import-run counts remain unchanged on refusal.
- `/api/status` now reports `projection`, `draft`, `workbook`,
  `generated_artifacts`, and `publication` separately. The current canonical
  first import has 34 blocking findings and is therefore labeled `unverified`,
  not verified/current. Comparison export is refused in that state; direct
  current-projection exports are labeled `DISPOSABLE-comparison-*.xlsx` and
  remain under the configured untracked export directory.
- The built browser was smoked against a copied workbook and temporary database.
  It showed the persistent `Read-only / provisional` banner, separate state
  labels, disabled replacement-import/export controls, `WRITE DISABLED`, and no
  live write control. Browser console: zero errors. Direct copied-workbook API
  probes returned 409 for write and re-import; copied-workbook SHA-256 remained
  `5d133540769ea5c2e744a1402ef9d4d49e8bd110a9772ff50a6031ed0fc89850`.
- Gates: focused containment `7 passed`; shared ChangeSet/writer
  `75 passed, 7 subtests passed`; frontend build passed; Python compile passed;
  workbook package and schema validation both passed with zero issues. The
  normal manager suite remained at its assigned baseline (`2 failed, 32 passed,
  2 skipped`); the slow scratch-copy run remained at the same two assigned
  failures (`2 failed, 34 passed`). No new failure was introduced.
- Canonical workbook and `form-app/data.js` hashes remained respectively
  `5d133540769ea5c2e744a1402ef9d4d49e8bd110a9772ff50a6031ed0fc89850` and
  `a34d1fdc80b04fe48f7ef2e77e37f67da038017bcaaca21ff1425767a4381a59`.
  Tracked generated/runtime artifacts, publication, deployment, customer form,
  and dealer submission were unchanged. Pass 1 temporary test-log churn was
  restored before closeout.

### Pass 2 — Split storage and adopt the shared backend contract

Required changes:

1. Implement the versioned, restart-safe, idempotent first-start migration in
   Section 3.1.1 before changing any storage consumer. Preserve unresolved
   legacy workflow rows as read-only recovery evidence.
2. Add the projection-path override and startup/migration lock, and run the
   migration/bootstrap before the existing connection accessor can serve any
   consumer. Initialize both schemas before serving; keep containment active
   when legacy recovery work is unresolved.
3. Extend the shared registry with the complete writable-field,
   required-on-add, required-on-effective-active-row, optional-column, and reference
   metadata needed by Section 3.6; do not add SQL-specific policy there.
4. Add the registry/schema-validation-derived `catalog.py` adapter, the complete
   sheet/column classifications in Section 3.7, and parity tests.
5. Implement the pinned blank/NULL mapping and minimal row lineage. Do not add
   per-cell physical-value tables or copy workbook-preserved sheets into SQLite.
6. Move current `specs.py` backend consumers to the adapter without changing product
   behavior or SQL naming merely for cleanup.
7. Carry model context for both physically model-scoped tables and families
   whose key includes `model_key`.
8. Enforce the Section 5.2 family ownership matrix before a draft can be
   created.
9. Define the final backend schema-metadata payload for ordinary, union,
   conditional, derived, finite, and free-text fields; do not render new UI
   controls in this pass.
10. Correct the stale lifecycle test using matrix-derived workbook predicates.
11. Delete `specs.py` only after the mechanical no-consumer and parity gates
    pass.

Pass 2 exit gate: migration restart probes preserve exact durable rows without
duplicates, both stores carry matching version/migration markers, every
manager-writable family has one
key/type/enum/reference/requiredness definition, every sheet and managed column
has one catalog disposition, shared preview rejects blank required fields, and
unknown or unowned models cannot create drafts.

Pass 2 result — completed 2026-07-23:

- Split storage now keeps `WBM_DB` as durable workflow/recovery state and uses
  `WBM_PROJECTION_DB` for the disposable workbook projection. Startup runs the
  locked bootstrap before either connection accessor can serve a consumer.
- First-start migration checkpoints and hashes the legacy database, verifies a
  same-directory hash-derived archive, builds both stores under
  `BEGIN IMMEDIATE`, records matching schema/migration/source markers plus
  per-table row-count/fingerprint evidence, replaces the disposable projection
  first and durable state last, and fsyncs files/directories. Restart probes
  cover partial and ambiguous archive temporaries and interruption before,
  between, and after replacements. Exact legacy pending/history payloads remain
  read-only recovery records; unresolved records continue to block import.
- The shared workbook-domain registry now owns complete writable columns,
  keys, scalar types, finite domains, ordinary/union/conditional/derived
  references, optional columns, and both requiredness sets. The manager-only
  `catalog.py` adapter owns SQL routing, labels, collection placement, and
  display prefixes. Optional blanks project to SQL `NULL`; required blanks are
  blocking findings and shared preview errors.
- Every live sheet and managed column receives one catalog disposition. Shared
  physical interiors/color rows are projected once per physical key with all
  registered model contexts. Preserved-known and preserved-unknown sheets stay
  workbook-owned; their cells are not copied into SQLite.
- Projection reads and imports now use the projection connection; staged/
  committed legacy workflow state, blockers, sync evidence, and backups use the
  durable connection. Model context is retained for physically scoped and
  `model_key`-keyed families.
- Staging enforces workbook-derived known/active/generatable/source-ownership
  predicates, fixed-sheet topology exceptions, publication preflight, and the
  sole writable `asset_map` wildcard. Runtime publication does not grant edit
  ownership. The stale scaffold rejection test was replaced by matrix-derived
  active, inactive, fixed, source-backed, publication, wildcard, and unknown-model
  coverage.
- All production/test consumers moved from duplicate `app/specs.py` metadata to
  the catalog; the no-consumer search passed and `specs.py` was deleted. The
  backend schema payload now reports model context, requiredness, optionality,
  finite/free-text kind, and ordinary/union/conditional/derived references.
- Gates: focused manager/catalog/migration `56 passed, 2 skipped`; slow copied-
  workbook manager `45 passed`; shared writer `83 passed, 7 subtests passed`;
  shared ChangeSet `50 passed`; Python compile and `git diff --check` passed;
  frontend build passed; workbook package and schema validation both passed
  with zero issues. The only warning was the existing FastAPI/Starlette
  `httpx` deprecation warning.
- Disposable browser smoke imported a copied workbook into temporary split
  stores, retained the persistent read-only/provisional and unverified state,
  loaded Stingray and ZR1 model-specific options plus shared collections, and
  produced zero browser console errors. No canonical workbook write occurred.
- Protected-path diff was empty for `stingray_master.xlsx`, `form-output/`, and
  `form-app/data.js`. Current hashes are respectively
  `c5f986f6793205e00124db5640248e9e8c57ebb930679a92c2b3e8c56fb62154` and
  `802afa1fea4e9e802f7d82635556c5569d3c73b2f4ae59267f64dd8157f9bceb` for the
  workbook and runtime registry. Product data, generated contracts,
  publication, deployment, customer form behavior, and dealer submission were
  unchanged. Pass 1 write containment remains active; Pass 3 connection/
  promotion coordination is still not started.

### Pass 3 — Establish request connections and promotion coordination

Required changes:

1. Move the already-tested Pass 2 migration/bootstrap invocation into FastAPI
   lifespan so it completes before serving requests.
2. Replace the global `_conn` with request-scoped projection and durable-state
   connections. Keep WAL and a bounded busy timeout on every connection; use
   SQLite foreign keys only for durable manager-state tables whose relationships
   are database-owned, never as a second workbook reference model.
3. Extend the Pass 2 process-local lock to cover durable-state mutations,
   candidate promotion, and workbook apply. Add a projection reader gate that
   blocks new readers and waits for current request-scoped projection
   connections to close before replacement. Do not add a second durable
   projection-generation state machine; the promoted projection's own import
   manifest and source fingerprint identify the current snapshot.
4. Keep the supported deployment single-process through `run.sh`. Document
   multi-worker serving as unsupported; do not add distributed locking.
5. Add concurrent first-load and reader-drain tests before candidate promotion
   code is allowed to call `os.replace()`.

Pass 3 exit gate: concurrent first-load/status requests use independent
connections without lock errors, promotion can quiesce readers deterministically,
and subsequent requests open the promoted projection manifest.

### Pass 4 — Build and atomically promote a verified projection

Required changes:

1. Open the source workbook read-only and record its SHA-256 and mtime before
   candidate work begins.
2. Build a new candidate projection file in the same filesystem as the active
   projection. Never clear or mutate the active file during compilation.
3. Enforce primary/composite uniqueness in SQLite and validate all workbook
   references through the shared semantic contract from Section 3.6.
4. Record the source workbook identity plus exact sheet, row, family, physical
   key, model ownership, and source disposition for every managed nonblank row.
5. Reconcile each managed source row to exactly one disposition: `imported` or
   `excluded`. Record one disposition for every workbook-preserved sheet without
   copying or counting its rows. An exclusion must include sheet, row, field,
   value, reason token, and contract impact.
6. Treat missing required sheets/columns, blank or duplicate keys, unresolved or
   ambiguous references, unproved model ownership, incomplete row
   reconciliation, semantic readback drift, or workbook package/schema failure
   as blocking. Do not promote an
   `imported_with_issues` candidate.
7. Apply the complete catalog and column-reconciliation rules in Section 3.7.
   Leave workbook-preserved sheets and opaque columns in the workbook; do not
   duplicate or interpret them in SQLite.
8. Reconstruct a comparison workbook from an identity-verified temporary copy
   of the source workbook by overlaying projected managed values through the
   shared editor operation path. Emit operations only for semantic differences;
   a no-op reconstruction remains the byte-for-byte source copy. After any
   overlay, verify every workbook-preserved sheet retains its values, formulas,
   dimensions, and physical row/column extent, including trailing blank rows;
   fail rather than promote/export if the workbook library trims or rewrites
   preserved physical content.
9. Validate the copied workbook package/schema and read every managed field back
   semantically after overlay; require equality with the candidate projection.
   Generated runtime parity is the separate slow acceptance test in Section 3.8
   and is not executed by production import.
10. Recheck the source workbook SHA-256/mtime. Checkpoint and close the candidate
    so promotion does not depend on candidate `-wal` or `-shm` sidecars.
11. Under the projection-promotion lock, block new projection requests and drain
    existing projection connections. Atomically replace the projection file,
    fsync the file and parent directory as supported, remove only proven-stale
    projection sidecars, then reopen subsequent requests against the promoted
    projection manifest. Durable-state connections remain independent.
12. On any exception or blocking finding, delete/quarantine the candidate and
    leave the prior projection bytes unchanged.

Do not make exact row counts part of the contract. Tests should derive counts
from their fixture/source workbook.

Pass 4 exit gate: malformed or incomplete imports leave the prior projection
byte-for-byte unchanged; only a reconciled, semantically read-back,
package/schema-valid candidate becomes current. The slow primary-runtime-only
source/reconstruction acceptance regression is also green.

### Pass 5 — Replace staged full rows with draft-to-ChangeSet emission

Required changes:

1. Store draft intent in the durable state database, not the projection.
   Refuse draft creation unless projection freshness is `current`.
2. Build draft rows from the projection plus earlier edits to the same physical
   key. Record only changed field pairs for updates.
3. Coalesce sequential edits and eliminate no-op reversions before ChangeSet
   emission.
4. Resolve source sheet and model ownership before accepting a draft operation;
   no operation may be committed with an empty target sheet.
5. Emit one exact immutable `workbook-changeset-1` payload per commit.
6. Preview the complete ChangeSet through `workbook_domain.service`. Persist the
   exact preview artifact or exception attempt envelope and status; refuse
   preview unless projection freshness is `current`; do not reproduce its
   validation logic.
7. Submit approval only through `workbook_domain.service.approve_changeset()`
   against the exact ChangeSet and preview. Persist the returned approval or
   exception attempt envelope unchanged, map it through Section 4.1, and refuse
   approval unless projection freshness is `current`.
8. Remove the dependency-confirmation bypass. Coordinated deletes and
   parent/member additions pass or fail as one final graph.
9. Keep legacy full-row history visible as read-only recovery evidence, not
   write authority.

Pass 5 exit gate: sequential same-row edits emit one operation; valid
parent/member additions and coordinated deletes preview together; invalid final
graphs cannot produce an approvable preview.

### Pass 6 — Harden the shared write boundary and recovery

Required changes:

1. Fix post-save exception restoration in
   `scripts/corvette_form_generator/editor_ops.py`, because the shared writer—not
   a manager wrapper—owns physical workbook recovery.
2. Enclose save, live readback, schema/package verification, and write-log
   completion in one restoration boundary.
3. After any post-save returned failure or exception, restore the backup and
   hash-verify it before returning `workbookState=restored`. Return
   `workbookState=unknown` when restoration cannot be proven.
4. Preserve the original failure and any restoration failure in the result.
5. Drive manager apply only through `workbook_domain.service.apply_changeset()`
   with the exact ChangeSet, preview, and approval artifacts.
6. Persist every early refusal, formal artifact, attempt envelope, and receipt unchanged.
   Map service outcomes and expose retry/cancel verbs exactly as Section 4.1
   defines; do not mark individual operations applied after an atomic batch
   failure.
7. Persist `applying` plus its unique active-attempt identity atomically before
   the writer call; enforce durable idempotency and startup orphan handling from
   Section 4.
8. Mark terminal `applied` only from a formally bound
   `workbook-change-receipt-1` with `status="applied"`,
   `workbookState="saved"`, passing receipt verification, and exact ChangeSet,
   preview, and approval identities. Do not implement a second manager readback;
   the shared writer/service receipt owns exact affected-row verification. Mark
   the projection stale after success.

Pass 6 exit gate: injected failures after physical save restore and hash-verify
the backup; every failure remains visible with exactly the recovery verb allowed
by Section 4.1; an orphaned `applying` attempt becomes unknown on restart; and
repeated requests cannot duplicate a workbook mutation.

### Pass 7 — Make the API and UI a thin client

Required changes:

1. Resolve API resources only from the allowlisted catalog; never accept a raw
   SQL table name outside it.
2. Fix Form Structure section-to-step fallback using the workbook master
   section metadata already imported by the manager.
3. Carry model context through schema response, form payload, draft, ChangeSet,
   preview, history, and receipt for every model-owned family.
4. Show projected values, source row lineage, blocking findings, exact
   ChangeSet/preview identity, warnings,
   failure detail, retry/cancel controls, and separate workflow statuses.
   Render finite controls from the final Pass 2 metadata and free text only for
   registry-declared free-text fields.
5. Do not report generated artifacts or runtime publication current after a
   workbook write. This pass does not run or publish generators; report those
   states as stale/unverified until separately proven outside the manager.
6. Keep the route disabled while implementing Pass 7 and run every non-write
   Pass 7 gate first. As the final code change, enable only the action bound to
   the exact approved artifacts, not a typed `SYNC` string plus mtime. Then run
   the disposable end-to-end copied-workbook write proof and close Pass 7 only
   after that proof passes.

Pass 7 exit gate: a real unchanged model-owned row round-trips through the
API/browser payload without losing model context or blank/reference meaning;
only the bound ChangeSet service can reach a live write.

A manager `applied` receipt means only that the workbook write and exact
readback were proven. It is not repository or customer-runtime completion. The
enclosing operational workflow must then run the affected package/schema,
generation, generated-contract comparison, and registry-verification gates from
the README before reporting the overall workflow current. That post-write work
remains outside automatic manager execution and must not publish or deploy
without the normal repository authority.

## 7. Expected implementation surfaces

Expected existing owners:

- `workbook-manager/backend/app/config.py`
- `workbook-manager/backend/app/db.py`
- `workbook-manager/backend/app/importer.py`
- `workbook-manager/backend/app/validation.py`
- `workbook-manager/backend/app/staging.py`
- `workbook-manager/backend/app/sync.py`
- `workbook-manager/backend/app/main.py`
- `workbook-manager/backend/app/schemas.py`
- `workbook-manager/frontend/src/api.js`
- `workbook-manager/frontend/src/App.jsx`
- `workbook-manager/frontend/src/components/RecordForm.jsx`
- `workbook-manager/frontend/src/components/ChangesSync.jsx`
- `workbook-manager/frontend/src/components/FormStructure.jsx`
- `tests/test_workbook_manager.py`
- `tests/test_workbook_changeset_service.py`
- `tests/test_editor_ops_apply.py`
- `scripts/corvette_form_generator/workbook_domain/registry.py`
- `scripts/corvette_form_generator/editor_ops.py`
- `workbook-manager/README.md`
- `README.md`
- this specification

Expected new owner:

- `workbook-manager/backend/app/catalog.py`
- `workbook-manager/backend/app/contract_parity.py`
- `tests/test_workbook_manager_catalog.py`
- `tests/test_workbook_manager_import_projection.py`
- `tests/test_workbook_manager_generated_parity.py`
- `tests/test_workbook_manager_changeset_lifecycle.py`
- `tests/test_workbook_manager_api_concurrency.py`

State/import helpers may be added only when required to implement these pinned
owners. Do not create the broad module tree from the superseded plan, move all
current tests preemptively, or refactor unrelated generator/runtime code.

## 8. Acceptance matrix

Implementation is complete only when these named owners prove:

| Audit risk | Required proof | Owning test module |
|---|---|---|
| Unsafe legacy path | live sync and destructive re-import remain refused until final enablement | `tests/test_workbook_manager.py` |
| Registry drift | every writable family matches shared key/type/enum/reference/requiredness metadata | `tests/test_workbook_manager_catalog.py` |
| Blank/NULL drift | optional SQL `NULL` and required-blank behavior follow Section 3.6 | `tests/test_workbook_manager_catalog.py` |
| Reference mismatch | ordinary/union/conditional/derived references all validate through the shared semantic contract | `tests/test_workbook_manager_catalog.py` |
| Ownership ambiguity | every matrix row, writable `asset_map` `*`, workbook-preserved wildcard, shared physical family, inactive scaffold, and bootstrap refusal is enforced | `tests/test_workbook_manager_catalog.py` |
| Column safety | reordered/extra/missing/duplicate/renamed managed headers follow Section 3.7 while opaque workbook columns remain untouched | `tests/test_workbook_manager_import_projection.py` |
| Destructive import | malformed candidate preserves the prior projection SHA-256 | `tests/test_workbook_manager_import_projection.py` |
| Import with issues | blocking findings prevent promotion and current-status claims | `tests/test_workbook_manager_import_projection.py` |
| Row reconciliation | every nonblank row has one catalog/import disposition | `tests/test_workbook_manager_import_projection.py` |
| Store-split migration | first start, interruption during temporary archive copy and before/after each database replacement, archive hash/atomic-rename recovery, and restart preserve exact journal/recovery rows without duplicates | `tests/test_workbook_manager_import_projection.py` |
| Journal loss on projection swap | drafts/artifacts remain unchanged across WAL-safe candidate promotion | `tests/test_workbook_manager_import_projection.py` |
| Isolated generated parity | every active/promoted row is preflighted and any historical artifact type/noncanonical path fails the run; canonical source/reconstruction contracts match; exactly one temporary runtime contract is written; compatibility/inspection/draft/registry/tracked outputs remain unchanged | `tests/test_workbook_manager_generated_parity.py` |
| Connection race | concurrent first-load/status requests and reader-draining promotion succeed without lock errors | `tests/test_workbook_manager_api_concurrency.py` |
| Stale overwrite | workbook SHA/mtime drift maps to `stale`; no external field is overwritten | `tests/test_workbook_manager_changeset_lifecycle.py` |
| Per-row validation | parent/member adds and coordinated deletes pass as one valid final graph | `tests/test_workbook_manager_changeset_lifecycle.py` |
| Sequential edits | one physical row appears once with original-to-final field pairs | `tests/test_workbook_manager_changeset_lifecycle.py` |
| Service mapping | every Section 4.1 returned outcome and a thrown approval exception maps to one state and exact allowed verbs; its attempt envelope persists and reopens unchanged | `tests/test_workbook_manager_changeset_lifecycle.py` |
| Failed/interrupted sync | failures expose only state-authorized verbs; one active attempt is durable; orphaned applying becomes unknown; retry/request replay is idempotent | `tests/test_workbook_manager_changeset_lifecycle.py` |
| Weak write binding | tampered ChangeSet, preview, approval, SHA, or mtime is rejected by the shared service | `tests/test_workbook_changeset_service.py` |
| Readback/log exception | every post-save exception restores and hash-verifies backup or reports unknown | `tests/test_editor_ops_apply.py` |
| UI context loss | unchanged real model-key rows round-trip with correct model/reference/source-lineage metadata | `tests/test_workbook_manager.py` plus disposable browser smoke |
| False readiness | workbook save leaves projection/generated/publication status stale or unverified | `tests/test_workbook_manager_changeset_lifecycle.py` |
| Stale projection authority | stale ChangeSet permits cancel only; after cancellation, stale projection permits labeled browse/history and verified re-import but blocks export/draft/preview/approval/apply until that import succeeds | `tests/test_workbook_manager_changeset_lifecycle.py` |

## 9. Validation and execution rules

For every pass:

1. Add a failing disposable regression before changing the implementation.
2. Run the focused test and observe the intended failure.
3. Make the smallest change through the owners above.
4. Run the focused test, then the current manager suite.
5. Recheck `git status` and prove the canonical workbook, tracked generated
   artifacts, runtime registry, deployment, and dealer code did not change.
6. Record the pass result in this specification before moving to the next pass.

The README owns exact commands. Add any new focused modules from Section 8 to its
Workbook Manager validation table, then run the current documented manager,
shared ChangeSet service, shared writer, slow copied-workbook, frontend build,
workbook package/schema, and diff checks. The named modules in Section 8 own the
acceptance proofs; do not substitute an unnamed smoke test for them.

Generated-contract acceptance runs only through the primary-runtime-only helper
against temporary workbooks/output roots; it is not part of production import.
Do not refresh tracked `form-output/` or `form-app/data.js` as implementation
output.

Browser-smoke the built manager against a copied workbook and temporary state/
projection databases. Cover model navigation, structure mapping, an unchanged
real-row edit, coordinated batch validation, stale workbook display, preview
binding, forced failure, retry/cancel, and post-write stale status. No live
dealer submission and no write to the canonical workbook are validation steps.

## 10. Scope control and stop conditions

The implementing agent may proceed through these passes without intermediate
approval when repository evidence supports the pinned design and all work stays
inside this specification.

Stop and request direction only if implementation would require:

- choosing or changing workbook product/business behavior;
- changing a shared public ChangeSet contract rather than using it as written;
- adding a dependency or supporting multi-process/distributed manager writes;
- changing generated/runtime contracts, publication, deployment, or dealer
  submission;
- discarding or guessing how to convert real legacy staged/unsynced work;
- accepting a candidate despite a blocking reconciliation finding, or reporting
  the slow acceptance parity test successful when it failed;
- materially expanding beyond reliability of the current manager workflow.

Do not stop merely because a pass spans several files or needs new focused
tests. Do not “solve” reliability by suppressing findings, weakening workbook
validation, editing workbook rows, or hiding unsafe actions only in the UI.

## 11. Non-goals

- Automatic field-level rebase or conflict merge.
- SQLite as canonical business-data storage.
- Per-model physical SQL table families.
- A new workbook compiler framework, ORM, API version, frontend framework, or
  dependency.
- Rewriting the fallback workbook editor or ingest workflow.
- Changing canonical option availability, pricing, defaults, relationships,
  copy, ordering, lifecycle, or publication decisions as implementation data.
  The manager may support already-authorized future edits through the matrix;
  this reliability implementation does not make those business decisions.
- Automatic generation, registry publication, deployment, or dealer submission
  inside the manager. The enclosing approved workbook workflow still performs
  the required post-write generation and verification before overall completion.

## 12. Companion impact and completion handoff

Companion disposition:

- Workbook source data: unchanged; hash/status proof required.
- Generated artifacts and `form-app/data.js`: inspected-no-change; temporary
  parity outputs only.
- Customer form and dealer submission: unchanged.
- Shared registry: reused; only generic metadata needed by existing writable
  families may be added.
- Shared ChangeSet contract/service: reused; no parallel contract.
- Shared writer: consumes registry-requiredness and is hardened for post-save
  restoration correctness.
- Model generation: implementation and output contracts unchanged. Acceptance
  calls canonical source assembly and writes only a temporary canonical runtime
  contract; no compatibility writer or publication path is changed or exercised.
- Workbook Manager docs and root README pointer: updated to match actual safety
  state and commands.
- Superseded relational design/plan: retained as historical, not edited back
  into active instructions.

Follow `AGENTS.md` handoff requirements. Also report:

- projection candidate/promotion evidence;
- durable-state preservation evidence;
- exact ChangeSet/preview/approval/receipt identities from the disposable test;
- conflict/staleness and retry probes;
- post-save restoration hash proof;
- concurrent API result;
- browser-smoke result;
- proof that the canonical workbook and tracked generated/runtime surfaces were
  unchanged.