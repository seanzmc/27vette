Build an interactive React workbook management module backed by a FastAPI server. The initial implementation must support `stingray_master.xlsx` through `openpyxl`, while establishing a normalized SQL database layer that can eventually become the canonical data source.

## Primary Objective

Create a form-based editor for investigating, adding, editing, validating, and removing records currently stored in `stingray_master.xlsx`.

Use the following architecture:

```text
React interface
    ↓
FastAPI API and validation layer
    ↓
SQLite database
    ↕
openpyxl workbook import/export adapter
    ↓
stingray_master.xlsx
```

During the first phase, the workbook remains authoritative. Import its data into SQLite for structured querying, relationship validation, editing, and audit history. Changes must not be committed back to the workbook until they pass validation.

Design the SQL schema and API so SQLite can later become the canonical source without requiring the React interface to be rewritten.

## Interface Structure

Organize the module into two primary workspaces.

### 1. Form Structure

Manage the activation sequence and hierarchy of:

- Models
- Steps
- Interface sections
- Section ordering
- Conditional activation
- Model-specific visibility

The interface must make the sequence easy to inspect and edit without requiring direct spreadsheet manipulation.

### 2. Model-Specific Operations

For each model, expose the relevant data collections, including:

- Master key data
- Options
- Exclusive groups
- Rule mapping
- Rule groups
- Rule group members
- Group rules
- Pricing
- Assets or supporting metadata where present

Do not hard-code one universal list of sheets unless the workbook proves that all models share the same structure. Determine each model’s applicable sheets from the workbook and existing application logic.

## SQL Data Architecture

Create a normalized SQLite database from the workbook structure.

Each model must have a clearly identified master-key source. Use that source to establish model records and relationships.

Use stable identifiers rather than row positions.

At minimum:

- `model_id` identifies a model
- `option_id` uniquely identifies an option within its intended scope
- Related records reference options through foreign keys
- Group membership references valid group and option records
- Rule records reference valid source and target entities
- Pricing records reference valid models, trims, and options as applicable

Do not assume `option_id` is globally unique until the workbook is inspected. If uniqueness is model-scoped, use a composite constraint such as:

```text
UNIQUE(model_id, option_id)
```

Create explicit relational tables rather than copying every worksheet into an unstructured database table.

The schema should support tables conceptually similar to:

```text
models
form_steps
form_sections
options
option_availability
exclusive_groups
exclusive_group_members
rule_mappings
rule_groups
rule_group_members
group_rules
pricing
assets
change_history
```

Adjust the final schema to match the actual workbook rather than forcing the workbook into this example structure.

## Workbook Integration

Use `openpyxl` only inside the FastAPI backend.

Provide an adapter layer responsible for:

- Reading workbook sheets
- Mapping workbook columns into normalized database records
- Detecting duplicate or missing identifiers
- Reporting unresolved relationships
- Applying validated database changes back to the workbook
- Creating a backup before every workbook write
- Exporting a regenerated workbook for comparison
- Preserving workbook structures that are not yet managed by the editor

Do not expose workbook coordinates as the primary identity of records. Store source sheet, row, and cell information only as traceability metadata.

## Editing Workflow

Use a staged editing process:

```text
Load workbook
    ↓
Import and validate into SQLite
    ↓
Edit through React
    ↓
Validate proposed changes
    ↓
Commit database transaction
    ↓
Optionally synchronize to workbook
```

Support:

- Add
- Edit
- Delete
- Undo before commit
- Batch validation
- Relationship checks
- Conflict detection
- Workbook export
- Clear reporting of every affected record

Deletion must be blocked when dependent records exist unless the user explicitly resolves or confirms those dependencies.

## Naming and Display Normalization

Normalization must affect display values only unless a deliberate migration is approved.

For human-readable labels:

- Convert `snake_case` sheet names and `uses` values to Title Case
- Replace underscores with spaces
- Preserve acronyms and known Corvette terminology where possible
- Strip repetitive prefixes from displayed Row IDs and Option IDs

For example:

```text
stingray_exterior_options → Stingray Exterior Options
stingray_exterior_color_01 → Exterior Color 01
```

Do not automatically alter canonical IDs stored in the workbook or database. Maintain separate fields such as:

```text
canonical_id
display_id
display_name
```

Prefix removal must be deterministic and reversible. Never strip text merely because it appears repetitive without confirming the prefix pattern.

## Audit History

Store audit history in the SQL database, not only in local React state or a standalone JSON file.

Each change-history record should include:

- Timestamp
- User or session identifier
- Entity type
- Entity identifier
- Model identifier
- Operation type
- Previous value
- New value
- Source sheet and row when applicable
- Validation result
- Commit or rollback status

Use an append-only `change_history` table.

A JSON audit log may also be generated as an export or backup artifact, but it must not be the sole authoritative history source.

## API Responsibilities

FastAPI should expose endpoints for:

- Workbook import
- Import validation
- Models and form structure
- Model-specific records
- Record creation
- Record updates
- Record deletion
- Dependency inspection
- Batch validation
- Change history
- Workbook synchronization
- Workbook export
- Database backup

Use typed Pydantic request and response models. Return validation errors with exact entity IDs, field names, sheet references, and actionable messages.

## React Responsibilities

React should provide:

- Form-oriented editing
- Model navigation
- Section and step navigation
- Search and filtering
- Record comparison
- Validation feedback
- Unsaved-change tracking
- Audit-history viewing
- Dependency warnings
- Explicit save and synchronization actions

Keep uncommitted changes in frontend state until the user validates and commits them.

## Migration Strategy

Implement the project in two stages.

### Stage 1

- `stingray_master.xlsx` remains canonical
- SQLite is populated from the workbook
- React edits are validated through the database
- Approved changes can be synchronized back to Excel
- Generated outputs are compared against the existing pipeline

### Stage 2

- SQLite becomes canonical
- Excel becomes an import, export, and human-review format
- Runtime JSON and other artifacts are generated from the database
- PostgreSQL remains a future migration option if hosting or multi-user editing is required

## Constraints

- Inspect the workbook and existing application before defining final table relationships.
- Reuse relevant components and patterns from the example React application where appropriate.
- Do not carry forward poor data structures merely because they exist in Excel.
- Do not rename canonical identifiers without an explicit migration plan.
- Do not write to the primary workbook without validation and backup.
- Avoid unnecessary dependencies or architectural abstraction.
- Preserve current runtime output until equivalence is verified.

## Success Criteria

The implementation is successful when:

1. Workbook data can be imported into SQLite without silent data loss.
2. Every unresolved relationship or duplicate identifier is reported.
3. Users can add, edit, and remove supported records through React.
4. All changes are validated before commit.
5. Every committed change appears in the SQL audit trail.
6. A backup is created before workbook synchronization.
7. The regenerated workbook preserves unmanaged content.
8. Existing runtime artifacts can be reproduced or intentionally migrated with documented differences.
9. The database can later become canonical without replacing the React interface or public API.