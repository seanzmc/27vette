# Workbook Manager Checkpoint 2D-A — Preserved-Sheet Inventory and Proposal

Repository: `27vette`

Read and obey `AGENTS.md` before beginning. The owning specification is
`workbook-manager/audit-spec.md`, especially §5.1, §7 Checkpoint 2D, and §10
PRES-01–05. Read `fable5loop/STATE.md` for the current operational handoff.

## Authorization and hard stop

This task authorizes **Checkpoint 2D-A only**: repository-backed discovery,
workbook inspection, consumer tracing, and an exact registry/write proposal for
the four preserved sheets below.

Implementation is explicitly forbidden. Do not add writable capability, modify
the workbook, run Apply/Rebuild, regenerate or publish artifacts, or change
application behavior. In particular, do not edit:

- `scripts/corvette_form_generator/workbook_domain/registry.py`
- `workbook-manager/backend/`
- `workbook-manager/frontend/`
- `stingray_master.xlsx`
- `form-output/`
- `form-app/data.js`
- generated runtime contracts

Read-only inspection and tests that do not mutate tracked or canonical data are
allowed. If any required fact cannot be established without a workbook write or
implementation change, record it as unresolved instead of crossing this gate.

After producing the proposal and validation evidence, **stop for explicit user
approval**. Do not begin Checkpoint 2D-B.

## Scope

Inventory and propose management for exactly these preserved sheets:

1. `PriceRef`
2. `context_choice_copy`
3. `rule_phrase_map`
4. `runtime_rule_exceptions`

Do not invent or expand product behavior. The workbook remains canonical;
registry metadata must describe proven workbook and consumer contracts rather
than creating new semantics.

## Definition of done

Checkpoint 2D-A is complete only when repository and workbook evidence supports
an exact, reviewable four-family proposal that answers every item below, names
all unresolved decisions, and can be approved or rejected without requiring the
reviewer to rediscover the implementation path.

Record the detailed proposal in the Checkpoint 2D section of
`workbook-manager/audit-spec.md`. Update only the fixed Current handoff block in
`fable5loop/STATE.md` with the proposal status, validation actually run, blockers,
and the next action. These remain the two live workflow files; do not create a
separate findings/specification document.

## Required inspection and proposal

For each family, provide a compact evidence table followed by any analysis
needed to establish the following.

### 1. Physical workbook contract

- Literal sheet name and header row, including exact casing and order.
- Observed openpyxl cell types and representative values for every column.
- Formula presence or absence and any formula-preservation requirement.
- Physical key and semantic key, including whether either is composite.
- Duplicate-key behavior and current duplicate evidence.
- Whether row order is semantic, presentation-only, or arbitrary, with consumer
  evidence for the conclusion.
- Current row count. Treat an empty sheet as an existing family, not as absent
  evidence.

### 2. Columns, references, and blank semantics

- Required, optional, writable, derived, and immutable columns.
- Inbound references: every workbook family or runtime contract that identifies
  these rows.
- Outbound references: options, RPOs, trims, variants, models, body styles,
  contexts, sections, or other registered entities identified by these rows.
- Exact reference domains, including unions or conditional references.
- Meaning of `None`, an empty string, whitespace, zero, and false wherever they
  are accepted or normalized.
- Enums, defaults, uniqueness constraints, active-state semantics, ordering, and
  delete dependencies.
- Any ambiguity that prevents safe fail-closed editing.

### 3. Consumers and preservation paths

Trace every active reader and writer from the sheet to its observable effects.
Include, where applicable:

- workbook schema/package validation;
- projection/import and unchanged export/re-import;
- pricing and interior-component readers;
- context-choice contract generation;
- rule-phrase parsing or generation;
- runtime-rule-exception loading;
- generated runtime contracts and `form-app/data.js` publication;
- affected-model derivation, preview, ChangeSet, guarded writer, dependency
  inspection, history, and rollback;
- tests and fixtures that currently encode the contract.

Use only active repository paths. Archived retired-ingest material may be cited
as history but must not be treated as architecture or authority.

### 4. Affected-model and generated-impact derivation

For each possible row mutation, explain how affected models are derived. Do not
default to a global wildcard without evidence. Distinguish direct `model_key`
scope from scope inferred through an option, RPO, trim, variant, context, or a
truly global consumer.

State the expected generated and published impact of representative add,
update, delete, and reorder operations. Identify at least one proven
no-runtime-impact case where the family permits one. If impact cannot be derived
unambiguously, make that an approval blocker.

### 5. Exact registry and Manager proposal

Propose, without implementing, the exact additions needed in the shared
workbook-domain registry and the Manager adapter. For each family include:

- canonical family name and physical sheet routing;
- collection/shared/structure classification;
- key fields;
- writable and read-only columns;
- types, enums, references, reference unions, and conditional references;
- requiredness, optionality, defaults, active semantics, and blank handling;
- add, update, delete, and reorder capabilities, including exact blocked
  reasons where a capability is unsafe;
- source-lineage requirements;
- browse/search and truthful empty-state behavior;
- projection table shape only where it is necessarily derived from the registry
  contract;
- how existing versioned schema responses and shared `RecordForm`/`EditorShell`
  reach the family without a custom write path.

Do not create a parallel writable-column, key, enum, reference, or capability
registry in Python or React.

### 6. Operation and regression matrix

Specify concrete tests and fixtures for each family. Cover:

- unchanged import/export/re-import preserving exact values, cell types,
  formulas, unrelated sheets, and semantically owned row order;
- one isolated copied-workbook add, update, and delete where supported;
- duplicate keys, invalid references, illegal blanks, immutable-key changes,
  unknown controls, and stale workbook bindings failing closed;
- two operations affecting the same key or dependent scope;
- mixed add/update/delete operations in one draft;
- full reversion and operation coalescing;
- dependency refusal and delete behavior;
- preview, ChangeSet, guarded apply, history, rollback evidence, and exact-cell
  verification;
- fresh isolated generation/publication matching the predicted affected models
  and contracts;
- `runtime_rule_exceptions` remaining visible and add-capable when it has zero
  rows.

The matrix must test behavior and persisted results, not merely source imports,
component presence, or string literals.

### 7. Cross-family and ownership review

Explicitly inspect interactions among the four proposed families and existing
registered families. Include:

- keys or references with different names across physical owners;
- parent/child or indirect operations that must be composed when details reload;
- multiple operations whose effects must accumulate from the authored baseline;
- projected rows that may already contain effective values while authored
  values remain separately required;
- sheet-classification changes when a family moves out of
  `KNOWN_PRESERVED_SHEETS` and into the registry;
- completeness behavior if one proposed family is accidentally omitted;
- `PriceRef` remaining a required sheet while becoming managed.

### 8. Approval decisions

End the proposal with an explicit decision table containing:

- the exact proposed contract for each family;
- evidence supporting it;
- residual risk;
- unresolved product, schema, deletion, ordering, blank, reference, or
  affected-model decisions;
- the recommended disposition: approve, approve with a named constraint, or
  block pending a specific decision.

Do not resolve ambiguous product or business semantics on the user's behalf.

## Validation for 2D-A

Run the smallest read-only checks needed to prove the proposal is consistent
with the live repository. At minimum:

- inspect `git status` before and after;
- run `git diff --check`;
- run the state-handoff validator after updating `STATE.md`;
- run the focused governance/spec tests affected by edits to the owning spec;
- confirm the canonical workbook and protected generated/publication artifacts
  are unchanged.

Do not claim PRES-01–05 have passed during 2D-A; this phase proposes how they
will be proven during implementation. Report every check actually run and every
relevant check intentionally not run with the reason.

## Final handoff

Report:

- files changed;
- the four proposed family contracts;
- unresolved decisions and approval blockers;
- validation results;
- confirmation that no implementation, workbook write, regeneration,
  publication, dealer submission, deployment, or cache purge occurred;
- the exact approval requested before Checkpoint 2D-B can begin.

Stop after delivering the proposal. Approval of 2D-A does not itself authorize
implementation unless the user explicitly authorizes Checkpoint 2D-B.
