# Workbook-Congruent Relational Database Design

Status: superseded on 2026-07-22 by
`docs/superpowers/specs/2026-07-22-reliable-workbook-database-workflow.md`. Retained as historical
design evidence; do not implement directly.

## 1. Objective

Convert the live `stingray_master.xlsx` data into a hardened SQLite relational
database served through FastAPI. The database must remain verifiably traceable
to the workbook without copying inconsistent workbook naming or ambiguous
relationship patterns into the SQL contract.

The result must satisfy these invariants:

1. Stingray, Grand Sport, and Z06 each have the same canonical collection of
   model-owned SQL tables.
2. Each model's options table uses `option_id` as its actual primary key.
3. Every model-owned row has explicit `model_key` ownership enforced by a
   foreign key and a table-specific check constraint.
4. Shared form properties—models, variants, body styles, trim levels, sections,
   and runtime structure—have one relational route and are referenced rather
   than repeated as unvalidated strings.
5. Every source-to-SQL rename, split, filter, normalization, and derived value
   is recorded and reversible.
6. No data or relationship that changes the current generation contract is
   promoted without a reported finding and, where business meaning is
   required, a user decision.
7. Workbook writes continue to use the existing guarded
   `editor_ops.apply_batch()` -> `save_workbook_safely()` path. This work does
   not change runtime or dealer-submission behavior.

## 2. Current Evidence

Read-only inspection on 2026-07-16 established:

- The workbook has 65 sheets.
- No sheet name contains spaces or characters that SQLite cannot quote.
- Sheet naming is inconsistent (`grandSport_options`, `PriceRef`,
  `LZ_Interiors`, and unprefixed Stingray relationship sheets).
- Space/case-heavy headers occur in `PriceRef`, `lt_interiors`, and
  `LZ_Interiors`, including `Interior Name`, `Detail from Disclosure`, and
  `Color Overrides`.
- The three active and promoted models are `stingray`, `grand_sport`, and
  `z06`.
- `model_workbook_sources` gives all three live models the same required source
  roles plus a variant-override role.
- Their option IDs overlap, but are unique within each model option sheet.
- All live option `section_id` values resolve to `section_master`.
- All live OVS option and variant references resolve to the corresponding
  options and `variant_master` rows.
- Current generation allows direct-rule `source_id` and price-rule
  `condition_option_id` to refer to either a model option or a model-visible
  interior. Current rule and price targets are model options.
- `color_overrides.adds_rpo` contains an option ID despite its name.
- `asset_map` supports option-only wildcard rows. Wildcards load first and an
  exact-model row overrides the same target.
- Blank and `*` both mean unrestricted in current scope matching.
- Model interiors are selected by the registered interior source plus active
  `model_interior_scope`; shared source sheets are not themselves sufficient to
  establish model ownership.
- Stingray still uses a compatibility source-assembly path while Grand Sport
  and Z06 use the shared inspection/draft path. All three finalize through the
  runtime-contract builder.

These facts are evidence for the schema. They are not permission to invent new
product rules.

## 3. Architecture

```text
stingray_master.xlsx
    -> read-only profiler and mapping validator
    -> canonical row compiler with lineage
    -> temporary SQLite database
    -> relational + contract parity gates
    -> atomic promotion to workbook_manager.sqlite3
    -> FastAPI
    -> existing React workbook-manager client

FastAPI staged changes
    -> SQL validation and audit history
    -> existing guarded workbook sync adapter
    -> stingray_master.xlsx
```

During this stage, the workbook remains the import source of truth. SQLite is
the structured query, validation, staging, and audit surface. The design does
not prevent a later canonical-source flip, but that flip is not part of this
task.

The database is built in a temporary file. The current verified database is
replaced only after import reconciliation, foreign-key validation, and runtime
contract parity pass for all three live models.

## 4. Naming and Congruency

SQL identifiers use lowercase `snake_case`. Broken or inconsistent workbook
formatting is not copied into the canonical schema.

Examples:

| Workbook source | Canonical SQL destination |
|---|---|
| `grandSport_options.option_id` | `grand_sport_options.option_id` |
| `rule_mapping` | `stingray_rule_mapping` |
| `PriceRef.OptionType` | `price_ref.option_type` |
| `LZ_Interiors.Interior Name` | `z06_interiors.interior_name` |
| `color_overrides.adds_rpo` | `<model>_color_overrides.added_option_id` |

Congruency is proved by three support tables, not by preserving weak names:

### `source_table_catalog`

Every one of the 65 workbook sheets receives exactly one disposition:

- `canonical_direct`: imported into one canonical table;
- `canonical_split`: imported into multiple model tables with proven filters;
- `generated_artifact_validation`: regenerated and compared, not treated as a
  second business-data source;
- `inactive_future_source`: retained in the import report but not promoted into
  the three live model collections;
- `decision_required`: not imported until its ownership or contract is decided.

The catalog records the source sheet, disposition, destination tables,
source-of-truth class, row count, and reason. Current `form_*` sheets are
`generated_artifact_validation`: they are checked against regenerated output
rather than duplicated as editable canonical data. ZR1/ZR1X sheets are
`inactive_future_source` unless separately promoted. No workbook sheet is
silently ignored.

### `schema_mapping`

One row per source/destination field mapping:

- `source_sheet`
- `source_column`
- `model_key` when model-scoped
- `source_role`
- `sql_table`
- `sql_column`
- `transform_type`
- `transform_parameters_json`
- `contract_status`
- `notes`

`contract_status` is one of:

- `exact`
- `identifier_normalized`
- `shared_source_split`
- `semantic_alias`
- `derived_from_contract`
- `contract_mismatch`
- `decision_required`

### `import_lineage`

One row per destination row/source row contribution:

- `import_run_id`
- `sql_table`
- `primary_key_json`
- `source_sheet`
- `source_row`
- `source_row_hash`
- `lineage_role`
- `transform_status`

One workbook row may produce rows for multiple models only when the existing
generation contract proves that sharing behavior. Every such expansion has
multiple lineage rows.

## 5. Canonical Model Collections

Each live model receives the same physical table roles. `<model>` means
`stingray`, `grand_sport`, or `z06`.

1. `<model>_options`
2. `<model>_option_availability`
3. `<model>_rule_mapping`
4. `<model>_price_rules`
5. `<model>_rule_groups`
6. `<model>_rule_group_members`
7. `<model>_exclusive_groups`
8. `<model>_exclusive_group_members`
9. `<model>_variant_overrides`
10. `<model>_interiors`
11. `<model>_interior_scope`
12. `<model>_interior_components`
13. `<model>_color_overrides`
14. `<model>_option_assets`
15. `<model>_context_choice_assets`
16. `<model>_default_selection_rules`
17. `<model>_runtime_rule_exceptions`

All tables include:

```sql
model_key TEXT NOT NULL
  REFERENCES models(model_key)
  CHECK (model_key = '<model>')
```

Each options table uses:

```sql
option_id TEXT PRIMARY KEY
```

There is no surrogate row ID in model option tables. Since tables are physical
per model, overlapping option IDs across models do not conflict.

`model_table_registry` records each model, table role, canonical table, source
sheet or sheets, source filter, and whether the mapping is exact, split, or
derived. FastAPI resolves model collections only through this registry.

## 6. Central Relational Tables

Shared form structure remains centralized:

- `models`
- `model_registry_promotion`
- `model_table_registry`
- `body_styles`
- `trim_levels`
- `variants`
- `model_variants`
- `sections`
- `section_presentation`
- `runtime_steps`
- `runtime_context_sections`
- `runtime_context_choices`
- `runtime_summary_sections`
- `runtime_step_summary_map`
- `model_assets`
- `price_ref`
- `rule_phrase_map`

`body_styles` and `trim_levels` are derived relational domains because the
workbook has no master sheets for them. Their values come only from active
`variant_master` and are not independent product-authoring sources.

Relationships include:

- `model_variants.model_key -> models.model_key`
- `model_variants.variant_id -> variants.variant_id`
- `variants.body_style -> body_styles.body_style`
- `variants.trim_level -> trim_levels.trim_level`
- model-owned option/override/interior `section_id -> sections.section_id`
- `section_presentation` references both model and section
- runtime tables reference their model and use model-scoped unique keys
- model-owned scope fields reference body style, trim, or variant when they are
  restricted

Context sections remain a distinct runtime section type because the current
generator treats them separately from option sections. They still connect to
the same model and runtime-step structure. The database must not pretend that a
context section is a `section_master` row when the workbook contract says it is
not.

## 7. Relationship Hardening

### Option relationships

- OVS, exclusive members, variant overrides, group members, rule targets,
  pricing targets, default targets, and runtime exception targets reference the
  corresponding model options table.
- OVS and variant overrides also reference `variants`.
- Deleting an option is blocked while any dependent row exists.

### Polymorphic workbook sources

A single SQL foreign key cannot honestly represent a value that may be an
option or an interior. Canonical SQL therefore uses two nullable foreign keys:

- direct rule: `source_option_id` / `source_interior_id`
- price rule: `condition_option_id` / `condition_interior_id`

A check constraint requires exactly one source/condition field. Targets remain
`target_option_id` because the current generation contract accepts model-option
targets.

If a source ID resolves to neither type, or resolves to both, import stops with
`decision_required`. Type is never inferred from the identifier prefix.

### Color overrides

Per-model color override rows use:

- `interior_id` -> model interiors
- `option_id` -> model options
- `added_option_id` -> model options

The adapter maps workbook `adds_rpo` to canonical `added_option_id` and back.

### Assets

`asset_map` is split by target type:

- option targets -> `<model>_option_assets`
- context choice targets -> `<model>_context_choice_assets`
- model-card targets remain centralized and reference `models`

Wildcard option assets are expanded into applicable models first. Exact-model
rows replace the matching wildcard-derived row, matching the current generator.
Wildcard model/context-choice targets are rejected because the current contract
does not support them. Model-card targets are written to `model_assets`.

### Scopes

SQL uses `NULL` for unrestricted body-style, trim, and variant scope. Workbook
blank and `*` values map to `NULL`. The outbound contract adapter reconstructs
the representation required by the destination source/contract so generation
output does not drift merely because storage was normalized.

## 8. Shared-Source Splitting

Shared workbook sheets are split only through proven generator behavior:

- `lt_interiors` -> `stingray_interiors` and `grand_sport_interiors` using the
  registered source plus active `model_interior_scope`.
- `LZ_Interiors` -> `z06_interiors` using the same rule.
- `model_interior_scope` and `interior_components` -> their model collections by
  exact `model_key`.
- `color_overrides` -> each model only when the interior and both referenced
  options resolve for that model.
- `asset_map` -> target-specific model tables using wildcard-first/exact-overlay
  behavior.
- `default_selection_rules` and runtime exceptions -> model tables by exact
  model ownership.
- shared context copy -> explicit model runtime rows using the current
  wildcard/exact matching contract.

No row is assigned to a model merely because its identifier happens to exist
there. Ownership must be proved by model scope, registered source, and current
generator behavior.

## 9. Known Hardening Findings

The first import report must explicitly record:

1. Inconsistent sheet and header naming.
2. Shared-sheet ownership that requires model-aware splitting.
3. Polymorphic fields whose workbook names imply option-only references.
4. `color_overrides.adds_rpo` containing option IDs.
5. Legacy `active_for_stingray` naming on shared interior sources.
6. Mixed blank/`*` unrestricted scope representation.
7. Stingray's legacy compatibility source-assembly path versus the shared Grand
   Sport/Z06 path.
8. Any source role, row, or relationship that does not reproduce the current
   promoted runtime contract.

These are findings and mappings, not authorization to rewrite workbook business
data or retire a generator path.

## 10. Import and Promotion Flow

1. Read the workbook without mutation.
2. Discover active/promoted models from workbook metadata.
3. Validate identical required source roles across the three models.
4. Profile headers, keys, row counts, data types, and relationship domains.
5. Compile central and per-model canonical rows with lineage.
6. Collect all findings before writing the candidate database.
7. Stop if any finding is `decision_required` or blocks contract parity.
8. Create a candidate SQLite database with `PRAGMA foreign_keys=ON`.
9. Load parents before dependents in one transaction.
10. Run `PRAGMA foreign_key_check`, uniqueness checks, row reconciliation, and
    mapping completeness checks.
11. Reconstruct source payloads through the outbound adapter.
12. Generate all three runtime contracts and compare them to the promoted
    current contracts, ignoring generated timestamps only.
13. Back up the existing database and atomically promote the candidate only when
    every gate passes.

Row reconciliation for every source is:

```text
source rows = imported destination rows + explicitly excluded rows
```

Every excluded row requires an issue with sheet, row, field, value, reason, and
contract impact. There is no silent quarantine or silent first-row-wins logic.

## 11. Existing Database Migration Safety

The current Stage 1 database uses conceptual shared tables and surrogate IDs.
It is not migrated in place.

- Back up the database before schema replacement.
- Re-import canonical business rows from the workbook into a candidate database.
- Preserve audit history only when its table/key mapping is unambiguous.
- Stop if staged changes or unsynced committed changes exist; the user must
  resolve, sync, discard, or explicitly authorize their migration.
- Never guess how a pending conceptual-table edit maps into a split model table.

## 12. FastAPI Contract

Primary endpoints:

```text
POST /api/imports
GET  /api/imports/{import_run_id}
GET  /api/imports/{import_run_id}/findings
GET  /api/schema/mappings
GET  /api/models
GET  /api/models/{model_key}/tables
GET  /api/models/{model_key}/tables/{table_role}
GET  /api/models/{model_key}/variants
GET  /api/models/{model_key}/runtime
POST /api/changes
GET  /api/changes
POST /api/changes/validate
POST /api/changes/commit
GET  /api/history
POST /api/sync
POST /api/export
POST /api/backup
```

FastAPI accepts logical model/table roles and resolves physical names through
`model_table_registry`; callers cannot inject table identifiers. Responses
identify both canonical SQL names and workbook lineage.

Pydantic request/response models must expose exact validation errors with model,
table role, canonical key, workbook source location, field, and actionable
message.

The existing React client remains API-only. Its data access is adapted to the
new model/table registry; no workbook or SQL knowledge moves into React.

## 13. Editing, Audit, and Workbook Sync

- Adds, updates, and deletes remain staged until batch validation succeeds.
- Canonical keys are immutable in updates; rename is delete plus add so
  dependents are visible.
- Delete is blocked while dependents exist.
- Every committed change is appended to SQL `change_history`.
- Sync maps canonical SQL fields back through `schema_mapping` and submits
  workbook operations through the existing guarded write pipeline.
- A sync dry run must prove the reconstructed workbook passes package/schema
  validation and regenerates equivalent runtime contracts before a live write.
- This task performs no live workbook write as implementation validation.

## 14. Failure and Decision Policy

The import or sync must stop when it encounters:

- missing or duplicate canonical keys;
- unknown or ambiguous option/interior ownership;
- missing required model source roles;
- incompatible role schemas across live models;
- unknown model, section, variant, body style, trim, runtime step, or target
  type;
- shared rows whose model ownership cannot be proved;
- a proposed normalization that changes generated behavior;
- staged or unsynced legacy DB changes without an unambiguous migration;
- any availability, pricing, default, grouping, relationship, or runtime rule
  that requires a new business decision.

The report must label each stopped item `contract_mismatch` or
`decision_required`. Implementation may fix format-only mapping defects, but it
must not choose business meaning.

## 15. Validation Strategy

Test-driven implementation must prove:

### Schema

- all three model collections exist and have the identical role set;
- every model options table reports `option_id` as the SQLite primary key;
- model checks and foreign keys reject cross-model rows;
- central model/variant/body/trim/section/runtime relationships are enforced;
- no conceptual shared `options` table or surrogate option ID remains.

### Import and congruency

- every workbook sheet has an explicit catalog disposition and every imported
  header has an explicit mapping;
- source and destination row counts reconcile;
- lineage covers every imported or expanded row;
- identifier and type normalization is deterministic and reversible;
- shared interior, color, asset, and context-copy splitting matches current
  generator behavior;
- unresolved or ambiguous relationships fail closed.

### Runtime contract

- SQL-derived Stingray, Grand Sport, and Z06 contracts match current promoted
  contracts except timestamps;
- every difference creates a blocking contract finding with a field path;
- the Stingray compatibility path is reported rather than silently treated as
  equivalent architecture.

### API and editing

- model routes cannot cross model boundaries;
- arbitrary table names are rejected;
- validation errors preserve SQL key and workbook lineage;
- stage, undo, batch validation, commit, history, backup, export, and safe sync
  continue to work;
- the existing API validation-error regression is corrected test-first.

### Repository boundaries

- `stingray_master.xlsx`, `form-output/`, `form-app/data.js`, and dealer
  submission code remain unchanged;
- no live dealer submission or live workbook write is used for validation;
- generated comparison artifacts and temporary databases stay untracked.

## 16. Non-Goals

- Choosing or changing product availability, price, defaults, grouping, copy,
  or ordering behavior.
- Editing the workbook to match the SQL schema during this pass.
- Retiring the Stingray compatibility generator path.
- Promoting ZR1 or ZR1X.
- Changing runtime JSON contracts, the browser application, download behavior,
  or dealer submission.
- Adding PostgreSQL or another database dependency.

## 17. Completion Evidence

Completion requires all of the following current-state evidence:

1. Schema introspection showing identical model table roles and `option_id`
   primary keys.
2. A successful full-workbook import report with complete mappings, lineage,
   row reconciliation, and zero unresolved decision findings.
3. `PRAGMA foreign_key_check` with zero rows.
4. Passing targeted and full workbook-manager tests.
5. Passing SQL-to-runtime contract comparisons for all three live models.
6. A successful FastAPI smoke test against the generated database.
7. A frontend build and browser verification of the model/table navigation and
   validation-report surfaces if the API adaptation changes rendered behavior.
8. Git evidence proving workbook, generated runtime artifacts, and dealer
   boundaries are untouched.

Only this evidence—not implementation intent or a narrow test—can close the
objective.
