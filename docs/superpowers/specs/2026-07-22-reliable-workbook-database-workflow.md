# Reliable Workbook–Database Workflow Implementation Specification

Status: implementation in progress; Pass 1 completed 2026-07-22, Pass 2
completed 2026-07-23, Pass 3 completed 2026-07-30, Pass 4 completed
2026-08-08, Pass 5 completed 2026-08-09, and Pass 6A completed 2026-08-10 on
`db-workflow`; the remaining implementation is Pass 6B and Pass 7, neither of
which has started.
Revised 2026-08-09 to split shared-writer restoration from durable manager
apply/recovery and narrow Pass 7 to the minimal exact-artifact client and final
enablement; revised 2026-07-23 to record the completed workbook-owned Vehicle
Setup copy contract;
the final specification review previously resolved all fourteen findings: primary-
runtime-only parity, strict publication selection, current baseline, outcome-
specific lifecycle states, interrupted-apply recovery, exception evidence,
acceptance-only generated parity, single readback authority, complete writable-
column ownership, non-circular write enablement, crash-safe two-store migration,
distinct restored outcomes, stale-projection permissions, and deferred UI work.
Recommended implementation reasoning: medium. Escalate only for a specific
unresolved data-integrity, crash-recovery, or concurrency judgment.

## Working progress authority

This specification is the sole detailed progress file for this workflow. It
owns pass status, completed requirements, current blockers, validation state,
and the next implementation step. Update it in place as Passes 6A–7 proceed.

`fable5loop/STATE.md` may carry only a short program-level pointer to this file,
the current pass/blocker state, and the latest evidence receipt. Fable run
receipts are immutable closeout evidence, not parallel progress trackers; they
must not introduce a competing current status or next-step narrative.

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

The audit in `docs/archive/old-reports/db_audit-7-22.md` proved these defects against disposable
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
  projection path. New installations initialize both at the current
  `SCHEMA_VERSION` (1 as written in Pass 2; 2 since Pass 3 added the durable
  `change_history.pending_change_id` foreign key, with an in-place upgrade for
  stores built at 1).
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

Vehicle Setup presentation copy is an explicit compatibility requirement of
this workflow. The completed migration owned by
`docs/archive/completed-specs/vehicle-setup-copy-workbook-ownership-spec.md` added these seven
manager-writable free-text columns to `model_master`:
`setup_card_subtitle`, `setup_eyebrow`, `setup_title`, `setup_description`,
`setup_fact_1`, `setup_fact_2`, and `setup_fact_3`. Pass 2 includes them in the
shared registry/catalog and imports them for every active model. They remain
optional for an unpromoted model definition, while the existing shared schema
and registry-promotion validation require all seven for a promoted model. Pass
4 must preserve them through candidate import, semantic readback, and
copy-plus-overlay reconstruction. Pass 5 preview must surface the shared
validation failure if a ChangeSet would clear required promoted-model setup
copy. Pass 7 must round-trip the seven fields through schema metadata, API,
browser form, draft, ChangeSet, and immutable history without changing their
workbook ownership or moving them into SQLite-only state.

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
fallback/alias behavior, retired ingest deployment proof, publication, or deployment is
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
`runtime_contract.assert_runtime_contract()`, and writes only
`runtime_contract_artifact_path(output_root, model_key)` through the repository
JSON writer.

Corrected 2026-07-24: `runtime_contract.py` is the strict-validation owner after
Pass G1 of `docs/superpowers/specs/2026-07-23-validation-single-lane-active-surface-cleanup.md`.
The older `registry_promotion.assert_runtime_contract()` spelling still resolves
through a re-export but omits the identity binding, so it validates more weakly
than intended without failing. Pass the discovered `config` and the workbook
promotion label as `expected_model_label` so dataset identity is checked against
the candidate snapshot. Any future change to this validator's owner or signature
must update both specifications in the same pass.

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

Pass 3 result — completed 2026-07-30:

- Storage bootstrap/migration now runs in the FastAPI `lifespan` and records its
  result on `app.state.storage_bootstrap`. Entering the app lifespan with no
  request builds both stores with matching manifests; no request path bootstraps
  lazily. `TestClient` must therefore be entered as a context manager.
- The global `_conn`/`_state_conn`/`_storage_bootstrapped` accessors are gone.
  `projection_connection()` and `state_connection()` are request-scoped
  generator dependencies that open one connection each and close it when the
  request ends; `open_projection_connection()`/`open_state_connection()` are the
  non-request helpers. Every connection sets WAL plus an explicit
  `busy_timeout` (`WBM_BUSY_TIMEOUT_MS`, default 5000 ms).
- SQLite foreign keys are enforced only on durable manager-state connections,
  where `change_history.pending_change_id` now declares
  `REFERENCES pending_changes(id)`. Projection connections keep enforcement off,
  so an unresolved workbook reference still imports and is reported as a finding
  rather than rejected by SQL. Both directions are asserted. Because that DDL
  change is invisible to a durable store Pass 2 already created, `SCHEMA_VERSION`
  is now 2 and bootstrap upgrades a version-1 durable store in place — rebuilding
  only `change_history` with the foreign key, preserving every row under
  `BEGIN IMMEDIATE`, refusing on any row-count change, and recording the new
  version in the manifest. The upgrade is idempotent across restarts and is
  reported as `schema_upgraded` in the bootstrap result.
- `STATE_LOCK` is the one process-local lock and now covers bootstrap plus every
  durable-state mutating route (`/api/import`, stage, discard, validate, commit,
  `/api/sync`, `/api/backup`) and, by contract, candidate promotion and workbook
  apply. Two concurrency defects were found and fixed while proving it, both
  worth recording because they are invisible to ordinary request-path reasoning:
  - An `RLock` held across a *synchronous* generator dependency's `yield` cannot
    be released, because FastAPI runs that dependency's enter and exit on
    different threadpool threads. The lock is now a plain `Lock` (releasable
    from any thread) and is therefore non-reentrant.
  - Blocking on that lock from a threadpool worker parks an anyio thread token,
    and once every token is parked the lock holder can never obtain a thread to
    finish and release — a permanent, unrecoverable process wedge, reproduced
    deterministically with the thread limiter shrunk to four tokens. The lock is
    now taken in an `async` dependency that polls a non-blocking acquire on the
    event loop under a bounded deadline (`WBM_STATE_LOCK_WAIT_SECONDS`, default
    30 s), so contention degrades to `503` instead of hanging. Lock *ordering*
    (lock-then-reader) was never the risk; thread starvation was.
- `PROJECTION_GATE` blocks new readers, drains open request-scoped projection
  connections, and only then permits replacement. Both waits are bounded and
  fail closed (`ProjectionBusyError`; `WBM_READER_WAIT_SECONDS` and
  `WBM_READER_DRAIN_SECONDS`, default 10 s each). A request arriving during a
  promotion returns `503`; a promotion whose readers do not drain replaces
  nothing and re-admits readers. Lock ordering is lock-then-reader — mutating
  endpoints declare the lock dependency first — so promotion (lock, then
  quiesce) cannot deadlock against an in-flight request. No second durable
  projection-generation state machine was added: `/api/status` now reports the
  opened projection's own `storage_manifest` identity. The bootstrap projection
  swap itself now runs through the gate, so Pass 4 inherits a gated replacement
  path rather than an ungated `os.replace` to copy.
- Requests to an app whose lifespan never ran fail closed with
  `503 storage_not_bootstrapped` naming the lifespan requirement, instead of an
  opaque `no such table` error plus stray empty database files.
- `run.sh` refuses `--workers` **and** a `WEB_CONCURRENCY` other than `1`:
  uvicorn reads the worker count from the environment when the flag is absent, so
  refusing only argv would have left multi-worker serving reachable. No
  distributed locking was added. `workbook-manager/README.md` and the root README
  record the Pass 3 behavior, the new environment overrides, and the new test
  module.
- No promotion code calls `os.replace()` yet; Pass 4 owns that. The gate and its
  reader-drain proofs land first, as required.
- Gates: new `tests/test_workbook_manager_api_concurrency.py` `31 passed`. Its
  final form fails `21` of `25` against pre-implementation `fa0eee7` in a
  throwaway worktree (the first 16-criterion draft failed 16 there), and each
  later test was observed failing against the intermediate build it fixes:
  thread starvation, full lock coverage, the `WEB_CONCURRENCY` bypass, the
  lifespan guard, the gated projection swap, and the durable schema upgrade. The
  busy-timeout test is the exception and is recorded as such: it cannot fail
  against the intermediate build, because the explicit pragma there set the same
  value the driver already sets — which is why that line was deleted rather than
  defended. The four manager suites together `87 passed, 2 skipped`
  in documented and reverse order; `WBM_SLOW_GATE=1 tests/test_workbook_manager.py`
  `45 passed`; shared ChangeSet plus shared writer `76 passed, 7 subtests passed`;
  frontend build passed; workbook package and schema validation both valid with
  zero issues.
- Protected-path `git status` was empty for `stingray_master.xlsx`,
  `form-output/`, and `form-app/data.js`; current hashes are
  `16415b913935b6d644fd1fbdcb5f6818d119e62cb6ef1fd077cff0f4b8d870e1` and
  `7d97dba5294d09de4a622ec410810bad4c1d1955c043d5c69e6105896258b91c`. Product
  data, generated contracts, publication, deployment, customer form behavior, and
  dealer submission were unchanged. Pass 1 write containment remains active;
  `write=true` sync is still refused. Pass 4 candidate promotion is not started.

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

Pass 4 result (completed 2026-08-08): commit `e02dd0a` implemented candidate
row/sheet dispositions, fail-closed package/schema/reference/reconciliation
checks, identity-copy-plus-overlay reconstruction, semantic readback, source
identity recheck, WAL-safe candidate closure, reader-gated atomic promotion and
rollback, comparison export, generated-contract parity acceptance, and the
re-import UI/status changes. The canonical workbook delta in that commit was
separately reviewed and authorized on 2026-08-08: it removes only two already
inactive, unresolved `asset_map` rows for `c-07-1.png` and `c-07-2.png`. The
ten-stage candidate verifier was rerun without declaring any model changed;
all six models reported empty `semantic_drift_vs_retained` arrays and there
were zero boundary violations. No tracked generated artifact or published
registry changed. The complete 111-test manager acceptance inventory
was covered in two serial invocations (the first was interrupted after 98
passed / 2 expected skips; the remaining `TestApi` class then passed 11/11), the
two explicit slow scratch-copy writer gates passed, shared ChangeSet/writer
tests passed, the frontend built, and workbook package/schema validation was
clean. A copied-workbook browser smoke then confirmed honest current/unverified
status, model navigation, write containment, and a byte-identical disposable
comparison export. Evidence:
`fable5loop/runs/2026-08-08-dbpass4-verified-projection-closeout/`.

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

#### Pass 5 checkpoint 1 — durable update intent (2026-08-08)

Checkpoint 1 is complete at implementation commit `94e059e`, with closeout
evidence under
`fable5loop/runs/2026-08-08-dbpass5-durable-draft-coalescing/`. It delivers only
requirements 1–4 for update operations: the durable store owns draft intent;
authoring requires a current projection; lineage and ownership resolve before
persistence; repeated edits to one physical row coalesce from the first
projected value to the final changed field pairs; and a full reversion removes
the operation. The disposable projection and legacy staged/history rows remain
unchanged, and active drafts participate in re-import containment.

Requirements 5–8 and the full Pass 5 exit gate remain open: exact immutable
`workbook-changeset-1` emission, complete final-graph preview through the shared
service, exact approval persistence/mapping, coordinated add/delete behavior,
and removal of the dependency-confirmation bypass. The next checkpoint must
start with a failing regression in
`tests/test_workbook_manager_changeset_lifecycle.py`; it must not extend the
legacy full-row writer or enable live workbook writes.

#### Pass 5 checkpoint 2 — immutable update ChangeSet emission (2026-08-09)

Checkpoint 2 is implemented at commit `60fd263`. It completes
requirement 5 for the update-only draft surface: one nonempty mutable draft
commit emits one exact `workbook-changeset-1`, converts typed field pairs through
the shared editor coercion, validates the payload through the shared parser,
persists the exact canonical payload in the durable store, and transitions the
batch to `changeset_emitted`. Database triggers refuse artifact update or
deletion. `POST /api/drafts/{draft_id}/commit` exposes only this emission step;
it does not preview, approve, apply, mutate the projection, or write the
workbook.

The schema-5 migration regression was observed failing against detached
baseline `bef0cbb` because a version-4 durable store was not upgraded, then
passed against this implementation while preserving a draft-operation sentinel
and verified version-3 projection across first and second restart. The new
lifecycle file passes 4 tests; the focused draft/concurrency/shared-ChangeSet
inventory passes 91 tests and the complete API class passes 12 tests, each with
one third-party deprecation warning. Two broader manager inventory attempts
exceeded the 600-second foreground limit after printing progress and therefore
are not counted as green.

Requirements 6–8 and the full Pass 5 exit gate remain open: complete
final-graph preview and exact attempt persistence/mapping, exact approval
persistence/mapping, coordinated add/delete behavior, and removal of the legacy
dependency-confirmation bypass. The next checkpoint must start with a failing
preview lifecycle regression in
`tests/test_workbook_manager_changeset_lifecycle.py` and route the immutable
ChangeSet through `workbook_domain.service.preview_changeset()` without
reproducing its validation logic.

#### Pass 5 checkpoint 3 — durable shared-service preview lifecycle (2026-08-09)

Checkpoint 3 completes requirement 6. `POST
/api/drafts/{draft_id}/preview` accepts only an emitted or retryable immutable
ChangeSet against a current verified projection and invokes only
`workbook_domain.service.preview_changeset()`. Durable schema 6 stores one
immutable attempt envelope per call with the exact returned dictionary or the
exception class/message, independently observed workbook identity, ChangeSet
identity, timestamps, resulting Section 4.1 manager state, and exact allowed
verbs. Formal previews, early refusals, freshness refusals, retryable transient
exceptions, rejected exceptions, identity loss, and distinct retry attempts are
covered without mutating the projection or workbook.

The focused lifecycle file passes 13 tests plus 12 mapping/exception subtests;
the draft/lifecycle/concurrency inventory passes 50 tests plus 12 subtests, and
the shared ChangeSet/service inventory passes 50 tests. The remaining manager
acceptance inventory and independent verifier result are recorded in
`fable5loop/runs/2026-08-09-dbpass5-preview-lifecycle/` rather than duplicated
here.

Requirements 7–8 and the full Pass 5 exit gate remain open: exact approval
persistence/mapping, coordinated add/delete behavior, removal of the legacy
dependency-confirmation bypass, valid parent/member and coordinated-delete
final-graph proof, and proof that invalid final graphs cannot become approvable.
The next checkpoint must start with a failing approval-lifecycle regression in
`tests/test_workbook_manager_changeset_lifecycle.py` and route the exact stored
ChangeSet and formal preview through
`workbook_domain.service.approve_changeset()` without enabling apply or live
workbook writes.

#### Pass 5 checkpoint 4 — durable shared-service approval lifecycle (2026-08-09)

Checkpoint 4 completes requirement 7. `POST
/api/drafts/{draft_id}/approve` accepts only `preview_ready` or
`approval_confirmation_required` drafts against a current verified projection,
loads the exact immutable ChangeSet and its latest identity-bound formal
preview, and invokes only `workbook_domain.service.approve_changeset()`.
Durable schema 7 stores one immutable attempt envelope per call with the exact
returned dictionary or exception evidence, bound ChangeSet and preview
identities, actor and warning IDs, timestamps, resulting Section 4.1 state, and
exact allowed verbs. Unknown returned outcomes fail closed to
`approval_rejected`; competing unbound preview rows cannot acquire approval
authority. No approval path applies a ChangeSet or mutates the projection or
workbook.

The approval regression was observed failing against detached baseline
`4338e52` because the approval service and endpoint did not exist. The final
focused and affected acceptance evidence, protected-surface checks, and
independent verifier result are recorded in
`fable5loop/runs/2026-08-09-dbpass5-requirement7-approval-lifecycle/` rather than duplicated
here.

#### Pass 5 checkpoint 5 — complete final-graph draft lifecycle (2026-08-09)

Checkpoint 5 completes requirement 8 and the Pass 5 exit gate. Durable drafts
now accept update, add, and delete intent; new-row edits coalesce into the
original add and add-then-delete collapses to no operation. Add/delete intent
resolves its source sheet, ownership, key, model context, and typed field pairs
without attempting per-row relationship approval. Commit emits every operation
in one immutable ChangeSet, and the existing shared preview service judges the
complete proposed graph. Coordinated exclusive-group parent plus member adds and
coordinated parent plus dependent deletes reach `preview_ready`; an incomplete
dependent delete returns a blocking final-graph warning and maps directly to
`preview_rejected` with cancel as its only verb, so it cannot reach approval.

The legacy `confirm_dependencies` request/function/UI bypass is removed. Legacy
database columns remain only as preserved recovery evidence; new staged rows
always record false and revalidation never treats an old true value as write
authority. The contained legacy browser now reports the dependents and directs
the operator to one coordinated draft ChangeSet rather than offering “delete
anyway.” No apply route or live workbook write was enabled.

The three required final-graph regressions were first observed failing with
`draft_action_not_implemented`; the new-row coalescing regression was then
observed failing with `record_not_found`. Final evidence: lifecycle tests `26
passed, 17 subtests passed`; complete named manager inventory `142 passed, 2
skipped, 17 subtests passed`; explicit slow copied-workbook manager inventory
`49 passed`; shared ChangeSet/service inventory `50 passed`; shared writer
inventory `59 passed, 7 subtests passed`; frontend build passed; workbook package
and schema checks both returned valid with zero issues; and `git diff --check`
passed. The canonical workbook, generated artifacts, published registry,
customer runtime, dealer submission, deployment, and dependencies are unchanged.
Pass 6A followed this checkpoint; Pass 5 itself granted no workbook-write authority.

### Pass 6A — Harden shared-writer post-save restoration

Keep this checkpoint inside the shared writer. Do not add manager apply state,
an API route, or a generalized transaction framework here.

Required changes:

1. Fix post-save exception restoration in
   `scripts/corvette_form_generator/editor_ops.py`, because the shared writer—not
   a manager wrapper—owns physical workbook recovery.
2. Enclose save, live exact-row readback, live package/schema verification,
   write-log completion, and success-result construction in one restoration
   boundary once a backup exists.
3. After any post-save returned failure or exception, restore the backup and
   hash-verify the restored workbook against that backup before returning
   `workbookState=restored`. Return `workbookState=unknown` when restoration
   cannot be proven.
4. Preserve the original failure phase/detail and any restoration failure in
   the returned result. Never replace the original cause with a generic restore
   message.
5. Keep the implementation local and narrow. A small shared restoration helper
   is permitted; a manager wrapper, new public artifact, transaction framework,
   or second write engine is not.

Pass 6A exit gate: returned and thrown failures from live readback,
package/schema verification, and write-log completion restore and hash-verify
the backup; a failed restore reports `workbookState=unknown`; and both the
original and restoration failures remain available as evidence.

#### Pass 6A completion — shared-writer restoration (2026-08-10)

Pass 6A is complete at the shared-writer boundary. After the guarded safe save
returns its backup, `editor_ops.apply_batch()` now performs live exact-row
readback, package validation, schema validation, success-result construction,
and write-log completion inside one narrow restoration boundary. Returned live
readback/schema failures and thrown readback/package/schema/log exceptions all
restore through the existing approved backup helper and independently compare
the restored live SHA-256 with the backup SHA-256. Results distinguish the
original failure phase/kind/detail from restoration attempted/verified hashes
and restoration error evidence; only a proved hash match reports
`workbookState="restored"`, while an unproved restore reports
`workbookState="unknown"` and `workbook_restore_failed` without losing the
original cause.

The first independent verification cycle found two contract defects in that
implementation: backup-hash failure could claim restoration was attempted before
the restore helper ran, and some verified rollbacks introduced an unrecognized
public receipt status. The final implementation leaves `attempted=false` until
backup hashing succeeds and restoration is about to run, and every verified
post-save rollback reuses the existing
`apply_verification_failed_rolled_back` status from Section 4.1. Both repairs
were observed RED before implementation and the independent re-verifier passed
criteria 1–8 and 10 with no new blocker.

These detailed `failure` and `restoration` fields remain internal shared-writer
result evidence. Pass 6A does not extend the public
`workbook-change-receipt-1` schema: the service receipt retains the existing
status, `workbookState`, errors, backup path, and verification fields, while
Pass 6B separately owns durable attempt evidence and independently observed
workbook identity as specified below.

The detached-parent regressions produced seven intended failures before the
implementation. The verifier-repair regressions then produced six intended
failures before their narrow repair. Final evidence: complete named manager
inventory `142 passed, 2 skipped, 17 subtests passed`; explicit slow copied-
workbook inventory `49 passed`; shared writer/service inventory `80 passed, 13
subtests passed`; frontend build passed; workbook package and schema checks both
returned valid with zero issues; protected-surface status and `git diff --check`
were clean; and the independent re-verifier returned PASS. Detailed output is
retained in `fable5loop/runs/2026-08-10-dbpass6a-shared-writer-restoration/`.
No manager apply state, API/UI route, public ChangeSet artifact, canonical
workbook, generated/publication surface, customer runtime, dealer, dependency,
deployment, commit, or push change was made. Pass 6B is the exact next action.

#### Validation-efficiency checkpoint between Pass 6A and Pass 6B (2026-08-10)

This bounded test-only checkpoint is complete; Pass 6B remains unstarted. The
historical pre-Pass-6A timing audit was 932.51 seconds at `138 passed, 2 skipped,
17 subtests passed`; it is context only, not the optimization baseline. The
same-version Pass 6A receipt records the actual pre-optimization inventory as
`142 passed, 2 skipped, 17 subtests passed` in 966.50 seconds.

The manager behavior tests now import the canonical workbook once into an
immutable SQLite base, clone that base per behavior class, and assert both the
base projection and canonical workbook SHA-256 remain unchanged. One complete
unchanged comparison export owns disposable labeling, byte identity, unmanaged
sheet preservation, managed row counts, Vehicle Setup copy round-trip, and the
explicit absence of generated-parity authority. One complete successful
projection promotion owns package/schema validation, semantic readback,
manifest reopening, row-disposition reconciliation, and durable-state-store
isolation. No unique assertion was removed.

Distinct complete acceptance owners remain for changed-overlay reconstruction,
comparison source drift, projection atomic-replace failure, projection source
drift, API lifespan import/re-import/export, and generated-contract parity. The
generated-parity gate still reconstructs from a real imported projection and
compares source/reconstruction contracts for all three promoted models. Focused
blocking-import and low-level atomic replacement cases remain separate; no
production validator or claimed behavior is mocked or bypassed.

The documented seven-module inventory ran exactly once after the slice with
`--durations=30`: `139 passed, 2 skipped, 17 subtests passed` in 791.25 seconds.
That is 175.25 seconds and 18.13% below the same-version 966.50-second Pass 6A
baseline. The 25% target time is 724.88 seconds; this result remains 66.37 seconds
above it. The checkpoint stops here rather than broadening scope or weakening a
distinct proof. The slowest retained owners were changed-overlay export 213.42
seconds, generated parity 74.87 seconds, API setup/import 71.45 seconds, API
re-import 69.69 seconds, unchanged export 69.47 seconds, API export 68.78
seconds, promotion success 68.44 seconds, promotion source drift 67.92 seconds,
and atomic-replace failure 67.86 seconds.

Focused editing evidence passed (`6 passed` in 348.78 seconds), and the isolated
post-review unchanged-export owner passed in 70.74 seconds. Protected-surface
and final diff evidence is retained in
`fable5loop/runs/2026-08-10-workbook-manager-validation-efficiency/`. Remaining
risk is runtime only: the complete checkpoint still takes about 13 minutes, but
further reduction requires a separately bounded design over retained acceptance
owners. Pass 6B is still the exact next implementation action.

### Pass 6B — Add durable manager apply, idempotency, and recovery

Build on the proven Pass 6A writer and the immutable preview/approval attempt
pattern already established in Pass 5. Do not make the apply path browser- or
live-route reachable in this checkpoint; Pass 7 owns final enablement.

Required changes:

1. Drive manager apply only through
   `workbook_domain.service.apply_changeset()` with the exact stored ChangeSet,
   identity-bound formal preview, and identity-bound formal approval artifacts.
2. Add one durable immutable apply-attempt owner containing the unique attempt
   ID, exact ChangeSet/preview/approval identities, timestamps, returned
   dictionary or exception evidence, independently observed workbook identity,
   resulting manager state, and exact allowed verbs. Do not redesign or merge
   the existing preview and approval tables merely for symmetry.
3. Persist `applying` plus its unique active-attempt identity atomically before
   invoking the shared service. Enforce at most one active apply attempt per
   ChangeSet and return an existing terminal result or reject an active attempt
   before any replay can reach the writer.
4. Persist every early refusal, formal receipt, and attempt envelope unchanged.
   Map service outcomes through one explicit fail-closed allowlist matching
   Section 4.1; unknown or malformed outcomes grant no retry or write authority.
   Do not mark individual operations applied after an atomic batch failure.
5. Permit exact-artifact retry only from `apply_retryable` or
   `apply_restored_retryable`, under the identity proofs in Section 4. Support
   lifecycle cancellation without deleting history.
6. During startup, convert any orphaned `applying` attempt to
   `workbook_state_unknown`; never retry it automatically. Add the minimum
   manager-owned manual-resolution record/operation required by Section 4 to
   prove restored, prove applied, or preserve an abandoned unknown outcome.
7. Mark terminal `applied` only from a formally bound
   `workbook-change-receipt-1` with `status="applied"`,
   `workbookState="saved"`, passing receipt verification, and exact ChangeSet,
   preview, and approval identities. Do not implement a second manager readback;
   the shared writer/service receipt owns exact affected-row verification.
8. Do not add a second stored projection-staleness flag. A successful workbook
   write changes the live SHA-256/mtime, so the existing workbook/projection
   identity comparison must naturally report the projection stale until a
   verified re-import succeeds.

Pass 6B exit gate: every service outcome exposes only its Section 4.1 recovery
verbs; an orphaned `applying` attempt becomes unknown on restart; cancellation
and manual resolution preserve immutable history; exact request replay cannot
duplicate a workbook mutation; and a successful receipt makes the existing
status calculation report the projection stale without a second readback or
parallel freshness state.

### Pass 7 — Make the API and UI a thin client

Required changes:

1. Preserve and characterize the existing catalog allowlist on schema, record,
   and dependency endpoints; never accept a raw SQL table name outside it. This
   is a regression proof, not a new resource-routing layer.
2. Fix Form Structure section-to-step fallback using the workbook master
   section metadata already imported by the manager.
3. Preserve model context through the schema response, form payload, durable
   draft operation, and manager-owned lifecycle/history view for every
   model-owned family. Do not extend or rewrite the immutable shared ChangeSet,
   preview, approval, or receipt schemas merely to add manager presentation
   fields: expose their exact stored artifacts alongside manager-owned source
   row, physical identity, and model-context metadata.
4. Replace the active legacy staged-row browser workflow with one minimal
   durable-draft lifecycle workspace. It must show projected values, source row
   lineage, model context, blocking findings, exact ChangeSet/preview/approval
   identities, warnings, failure detail, allowed retry/cancel/manual-recovery
   controls, and separate workflow statuses. It must support operation capture,
   commit, preview, approval, and the exact bound apply action without creating
   a parallel workflow engine.
5. Render finite controls from the final Pass 2 `field_kind`/`finite_values`
   metadata and free text only for registry-declared free-text fields. Preserve
   optional blank/SQL `NULL` and reference meaning through unchanged-row and
   edited-row round trips, including the seven workbook-owned Vehicle Setup
   copy fields.
6. Preserve the existing separate status behavior: after a workbook write the
   workbook/projection identity is stale, while generated artifacts and runtime
   publication remain stale/unverified until separately proven outside the
   manager. This pass does not run or publish generators.
7. Keep legacy `POST /api/sync` permanently read-only: every `write=true`
   request remains refused. While implementing Pass 7, keep the dedicated bound
   apply action unreachable and run every non-write gate first. As the final
   code change, enable only that dedicated action over the exact approved
   artifacts. Then run the disposable end-to-end copied-workbook write proof and
   close Pass 7 only after it passes.

Pass 7 exit gate: a real unchanged model-owned row round-trips through the
API/browser payload without losing model context, source lineage, or
blank/reference meaning; the legacy staged/sync browser workflow grants no
write authority; `POST /api/sync write=true` remains refused; and only the
dedicated exact-artifact action can reach the bound ChangeSet service write.

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
- `workbook-manager/backend/app/drafts.py`
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
| Unsafe legacy path | legacy live sync remains permanently refused; destructive re-import remains fail-closed | `tests/test_workbook_manager.py` |
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
| Failed/interrupted apply | failures expose only state-authorized verbs; one active attempt is durable; orphaned applying becomes unknown; retry/request replay is idempotent | `tests/test_workbook_manager_changeset_lifecycle.py` |
| Weak write binding | tampered ChangeSet, preview, approval, SHA, or mtime is rejected by the shared service | `tests/test_workbook_changeset_service.py` |
| Post-save exception | live readback, package/schema, and log failures restore and hash-verify the backup or report unknown while preserving original and restoration evidence | `tests/test_editor_ops_apply.py` |
| UI context loss | unchanged real model-key rows round-trip through the manager lifecycle view with correct model/reference/source-lineage metadata while shared artifacts remain unchanged | `tests/test_workbook_manager.py` plus disposable browser smoke |
| Vehicle Setup copy loss | all seven workbook-owned `model_master` setup-copy fields survive import/reconstruction and API/browser/ChangeSet round-trip; clearing one for a promoted model fails shared preview validation | `tests/test_workbook_manager.py`, `tests/test_workbook_manager_import_projection.py`, and `tests/test_workbook_manager_changeset_lifecycle.py` |
| False readiness | workbook save leaves projection/generated/publication status stale or unverified | `tests/test_workbook_manager_changeset_lifecycle.py` |
| Stale projection authority | stale ChangeSet permits cancel only; after cancellation, stale projection permits labeled browse/history and verified re-import but blocks export/draft/preview/approval/apply until that import succeeds | `tests/test_workbook_manager_changeset_lifecycle.py` |

## 9. Validation and execution rules

For every pass:

1. Add a failing disposable regression before changing the implementation.
2. Run the focused test and observe the intended failure.
3. Make the smallest change through the owners above.
4. Run the focused test, then the current manager suite.
5. Recheck `git status` and prove the canonical workbook, tracked generated
   artifacts, runtime registry, deployment, and dealer code did not change. If
   a separately authorized workbook cleanup shares the implementation commit,
   enumerate that exact delta and run its normal workbook/runtime gates instead
   of calling the workbook unchanged.
6. Record the pass result in this specification before moving to the next pass.

The README owns exact commands. Add any new focused modules from Section 8 to its
Workbook Manager validation table, then run the current documented manager,
shared ChangeSet service, shared writer, slow copied-workbook, frontend build,
workbook package/schema, and diff checks. The named modules in Section 8 own the
acceptance proofs; do not substitute an unnamed smoke test for them.

Use those checks in tiers rather than rerunning every real-workbook acceptance
case after every edit. During implementation, run the exact affected test or
class; at a pass checkpoint, run the complete named acceptance inventory once.
The end-to-end promotion, comparison export, scratch-copy write, and generated-
parity cases remain required because they prove distinct protected boundaries.
Passes 6A–7 may reduce runtime by cloning a verified imported-projection fixture
and using compact workbooks for negative cases, provided at least one real-
workbook success and one real-workbook fail-closed case continue to exercise
each complete boundary. Runtime reduction must not replace package/schema,
semantic-readback, atomic-rollback, or generated-contract acceptance.

Generated-contract acceptance runs only through the primary-runtime-only helper
against temporary workbooks/output roots; it is not part of production import.
Do not refresh tracked `form-output/` or `form-app/data.js` as implementation
output.

Browser-smoke the built manager against a copied workbook and temporary state/
projection databases. Cover model navigation, structure mapping, an unchanged
real-row edit, coordinated batch validation, stale workbook display, preview
binding, forced failure, retry/cancel/manual-recovery display, and post-write
stale status. No live
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
- Rewriting the fallback workbook editor or restoring the retired ingest workflow.
- Changing canonical option availability, pricing, defaults, relationships,
  copy, ordering, lifecycle, or publication decisions as implementation data.
  The manager may support already-authorized future edits through the matrix;
  this reliability implementation does not make those business decisions.
- Automatic generation, registry publication, deployment, or dealer submission
  inside the manager. The enclosing approved workbook workflow still performs
  the required post-write generation and verification before overall completion.

## 12. Companion impact and completion handoff

Companion disposition:

- Workbook source data: no Pass 4 behavior depends on a product-data change.
  Commit `e02dd0a` also removed two inactive unresolved `asset_map` rows; that
  exact cleanup was separately reviewed, authorized, and proven runtime-neutral
  during the 2026-08-08 closeout.
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
- Post-export gate: once Pass 3 of the single-lane specification lands
  `scripts/verify_workbook_candidate.py`, this workflow calls that one command
  after an approved workbook write and consumes its JSON readiness report. It
  does not reimplement the package/schema/quality/generation/registry stage
  sequence, and it does not use touched-model information to narrow what is
  generated or validated — see §3.7.1 of that specification.
- Legacy staging/sync: Pass 5 replaced their write authority with durable
  draft-to-ChangeSet emission. Keep `staging.py` and
  `sync_workbook(write=True)` characterization-only during Passes 6A–6B; Pass 7
  removes the legacy staged-row browser workflow and keeps
  `POST /api/sync write=true` permanently refused. Do not harden or re-enable
  that superseded write lane.
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
- proof that the canonical workbook was unchanged or carries only an exact
  separately authorized delta, and that tracked generated/runtime surfaces were
  unchanged.
