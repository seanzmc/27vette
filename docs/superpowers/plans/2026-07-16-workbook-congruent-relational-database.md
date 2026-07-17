# Workbook-Congruent Relational Database Implementation Plan

Status: completed and verified on 2026-07-17.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the workbook manager's conceptual shared-table SQLite schema with a workbook-traceable, hardened relational schema whose identical Stingray, Grand Sport, and Z06 table collections use `option_id` primary keys and reproduce all three current runtime contracts.

**Architecture:** Compile `stingray_master.xlsx` into typed central tables plus identical physical per-model table families, recording every source mapping and row lineage. Build and validate a candidate SQLite file atomically, serve it through registry-driven FastAPI routes, and keep workbook export/sync behind the existing guarded write path.

**Tech Stack:** Python 3.14, stdlib `sqlite3`, FastAPI/Pydantic, `openpyxl`, pytest/unittest, React 18.3 + Vite, Node's built-in test runner, existing Corvette generators and contract comparator.

## Global Constraints

- `stingray_master.xlsx` remains the import source of truth for this stage.
- Do not modify `stingray_master.xlsx`, `form-output/`, `form-app/data.js`, generated runtime contracts, or dealer-submission code.
- Do not introduce SQLAlchemy, PostgreSQL, or any new dependency.
- Use lowercase `snake_case` SQL identifiers and preserve exact workbook names through `source_table_catalog`, `schema_mapping`, and `import_lineage`.
- Build Stingray, Grand Sport, and Z06 with the identical 17-role physical table collection defined in the approved design.
- Each model options table must declare `option_id TEXT PRIMARY KEY`; no surrogate option ID and no shared conceptual `options` table may remain.
- Every model-owned table must carry a `model_key` foreign key plus a constant-model check constraint.
- Enable `PRAGMA foreign_keys=ON`; do not emulate relational integrity solely in Python.
- Use the approved model-scoped `runtime_route_keys` derived domain for visible
  runtime steps and hidden summary buckets; it is not an option activation or
  selectability dictionary.
- Represent unrestricted `price_ref.trim_level` only as `NULL`, with the
  approved NULL-safe natural-identity index and internal surrogate row key.
- Stop on unknown or ambiguous ownership, missing required source roles, contract drift, or any finding requiring a product/business decision.
- Only blank/`*` scope normalization, identifier normalization, proven shared-row splitting, and semantic field aliases may proceed without a business decision.
- Existing guarded workbook writes remain `editor_ops.apply_batch()` -> `save_workbook_safely()`.
- Use test-driven development: write and observe each failing test before production code.
- The user explicitly approved the Task 8 migration and commit of the existing
  `tests/test_workbook_manager.py` module-reset fix. The unrelated
  `fable5loop/runs/2026-07-15-workbook-manager-stage1/validation-output.txt`
  receipt remains preserved and was never staged.
- Reference design: `docs/superpowers/specs/2026-07-16-workbook-congruent-relational-database-design.md`.

---

## Planned File Structure

### Backend modules

- `workbook-manager/backend/app/catalog.py`: canonical model roles, central-table definitions, identifier mappings, and safe table resolution.
- `workbook-manager/backend/app/compile_types.py`: immutable compiler dataclasses and finding severity/status vocabulary.
- `workbook-manager/backend/app/workbook_profile.py`: read-only sheet/header/row profiling and all-65-sheet disposition coverage.
- `workbook-manager/backend/app/central_compiler.py`: model, variant, body style, trim, section, runtime, and reference-table compilation.
- `workbook-manager/backend/app/model_compiler.py`: identical direct per-model source-role compilation and relational key typing.
- `workbook-manager/backend/app/shared_compiler.py`: interiors, assets, color overrides, shared context copy, and other proven model splits.
- `workbook-manager/backend/app/export_adapter.py`: reversible canonical-SQL-to-workbook mapping into a temporary comparison workbook.
- `workbook-manager/backend/app/contract_audit.py`: three-model generation and timestamp-insensitive contract comparison.
- `workbook-manager/backend/app/migration.py`: legacy-DB safety audit, backup, candidate build, and atomic promotion.
- `workbook-manager/backend/app/db.py`: SQLite connection, canonical DDL, support tables, and transaction helpers.
- `workbook-manager/backend/app/importer.py`: orchestration of profile -> compile -> candidate load -> audit -> promotion.
- `workbook-manager/backend/app/validation.py`: registry-driven row validation and dependency inspection.
- `workbook-manager/backend/app/staging.py`: registry-driven staged changes and append-only history.
- `workbook-manager/backend/app/sync.py`: mapping-backed workbook batch/export/backup.
- `workbook-manager/backend/app/schemas.py`: typed API request/response contracts.
- `workbook-manager/backend/app/main.py`: FastAPI routes only; no workbook mapping logic.
- Delete `workbook-manager/backend/app/specs.py` only after every caller uses `catalog.py` and all tests are green.

### Tests

- `tests/workbook_manager/conftest.py`: isolated backend import path and temporary database/workbook fixtures.
- `tests/workbook_manager/test_catalog_schema.py`: physical schema, PK/FK/check, and safe resolver tests.
- `tests/workbook_manager/test_workbook_profile.py`: 65-sheet disposition and mapping coverage.
- `tests/workbook_manager/test_central_compiler.py`: central relational domains and runtime structure.
- `tests/workbook_manager/test_model_compiler.py`: identical model families and direct model relationships.
- `tests/workbook_manager/test_shared_compiler.py`: proven shared-sheet splits and fail-closed ambiguity.
- `tests/workbook_manager/test_import_promotion.py`: candidate database loading, reconciliation, migration guard, and atomic replacement.
- `tests/workbook_manager/test_contract_audit.py`: SQL-to-workbook round trip and three promoted contract comparisons.
- `tests/workbook_manager/test_staging_sync.py`: staged editing, dependency blocking, history, and safe export/sync.
- `tests/workbook_manager/test_api_v2.py`: typed FastAPI routes, safe role resolution, and error detail.
- `tests/workbook_manager/test_frontend_contract.mjs`: registry-driven frontend API and pure view-model behavior.

### Frontend and documentation

- `workbook-manager/frontend/src/api.js`: v2 import, model-table, mapping, and finding routes.
- `workbook-manager/frontend/src/tableRegistry.js`: pure table-role/view-model helpers.
- `workbook-manager/frontend/src/components/ModelOperations.jsx`: table-role navigation using canonical names and lineage.
- `workbook-manager/frontend/src/components/ImportFindings.jsx`: contract mismatch/decision-required display.
- `workbook-manager/frontend/src/App.jsx`: findings tab/status integration.
- `workbook-manager/README.md`: canonical schema, import, API, verification, and migration commands.
- `README.md`: pointer/command updates only where the repo command table owns them.

---

### Task 1: Canonical Catalog and Physical SQLite Schema

**Files:**
- Create: `workbook-manager/backend/app/catalog.py`
- Modify: `workbook-manager/backend/app/db.py`
- Create: `tests/workbook_manager/conftest.py`
- Create: `tests/workbook_manager/test_catalog_schema.py`

**Interfaces:**
- Produces: `LIVE_MODELS`, `MODEL_TABLE_ROLES`, `physical_table(model_key, role)`, `resolve_model_table(conn, model_key, role)`, `create_canonical_schema(conn)`.
- Consumes: no new task interfaces; uses only stdlib `sqlite3`.

- [x] **Step 1: Write failing schema tests**

Create these base fixtures in `conftest.py`, then add the schema tests:

```python
REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = REPO_ROOT / "workbook-manager" / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))


@pytest.fixture
def repo_root() -> Path:
    return REPO_ROOT


@pytest.fixture
def real_workbook(repo_root: Path) -> Path:
    return repo_root / "stingray_master.xlsx"


@pytest.fixture
def connection(tmp_path):
    conn = db.connect(tmp_path / "test.sqlite3")
    try:
        yield conn
    finally:
        conn.close()
```

Then write:

```python
from app import db
from app.catalog import LIVE_MODELS, MODEL_TABLE_ROLES, physical_table


def test_each_live_model_has_identical_physical_roles(connection):
    db.create_canonical_schema(connection)
    names = {
        row["name"]
        for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )
    }
    for model in LIVE_MODELS:
        assert {physical_table(model, role) for role in MODEL_TABLE_ROLES} <= names


def test_option_id_is_actual_primary_key(connection):
    db.create_canonical_schema(connection)
    for model in LIVE_MODELS:
        info = connection.execute(
            f"PRAGMA table_info({physical_table(model, 'options')})"
        ).fetchall()
        pk = [row["name"] for row in info if row["pk"]]
        assert pk == ["option_id"]


def test_model_owned_table_rejects_wrong_model(connection):
    db.create_canonical_schema(connection)
    connection.execute(
        "INSERT INTO models(model_key, registry_key, model_label, active) "
        "VALUES('stingray', 'stingray', 'Stingray', 1)"
    )
    with pytest.raises(sqlite3.IntegrityError):
        connection.execute(
            "INSERT INTO stingray_options(model_key, option_id) "
            "VALUES('z06', 'opt_x')"
        )
```

- [x] **Step 2: Run tests and observe the expected failure**

Run:

```bash
.venv/bin/python -m pytest tests/workbook_manager/test_catalog_schema.py -q
```

Expected: collection failure because `app.catalog` and `create_canonical_schema` do not exist.

- [x] **Step 3: Implement the catalog and DDL**

Define the exact role tuple and safe resolver:

```python
LIVE_MODELS = ("stingray", "grand_sport", "z06")
MODEL_TABLE_ROLES = (
    "options", "option_availability", "rule_mapping", "price_rules",
    "rule_groups", "rule_group_members", "exclusive_groups",
    "exclusive_group_members", "variant_overrides", "interiors",
    "interior_scope", "interior_components", "color_overrides",
    "option_assets", "context_choice_assets", "default_selection_rules",
    "runtime_rule_exceptions",
)


def physical_table(model_key: str, role: str) -> str:
    if model_key not in LIVE_MODELS or role not in MODEL_TABLE_ROLES:
        raise KeyError((model_key, role))
    return f"{model_key}_{role}"


def resolve_model_table(conn, model_key: str, role: str) -> str:
    row = conn.execute(
        "SELECT sql_table FROM model_table_registry "
        "WHERE model_key=? AND table_role=? AND active=1",
        (model_key, role),
    ).fetchone()
    if row is None or row["sql_table"] != physical_table(model_key, role):
        raise KeyError((model_key, role))
    return row["sql_table"]
```

In `db.connect`, execute `PRAGMA foreign_keys=ON` and assert it returns `1`.
Implement `create_canonical_schema` with explicit central/support DDL plus one
role template per model. The options template must begin with:

```sql
CREATE TABLE stingray_options (
  model_key TEXT NOT NULL REFERENCES models(model_key)
    CHECK(model_key = 'stingray'),
  option_id TEXT PRIMARY KEY,
  rpo TEXT NOT NULL,
  price INTEGER NOT NULL,
  option_name TEXT NOT NULL,
  description TEXT NOT NULL DEFAULT '',
  detail_raw TEXT NOT NULL DEFAULT '',
  section_id TEXT NOT NULL REFERENCES sections(section_id),
  selectable INTEGER NOT NULL CHECK(selectable IN (0, 1)),
  display_order INTEGER NOT NULL,
  active INTEGER NOT NULL CHECK(active IN (0, 1)),
  display_behavior TEXT
);
```

Generate equivalent DDL for the other two models and all 17 roles. Use quoted
identifier interpolation only with values returned by `physical_table`; never
interpolate request data.

- [x] **Step 4: Run schema tests**

Run the Task 1 test file. Expected: all tests pass and `PRAGMA foreign_keys`
returns `1`.

- [x] **Step 5: Commit Task 1**

```bash
git add workbook-manager/backend/app/catalog.py workbook-manager/backend/app/db.py tests/workbook_manager/conftest.py tests/workbook_manager/test_catalog_schema.py
git commit -m "feat: define canonical model database schema"
```

---

### Task 2: Workbook Profile, Source Catalog, and Mapping Coverage

**Files:**
- Create: `workbook-manager/backend/app/compile_types.py`
- Create: `workbook-manager/backend/app/workbook_profile.py`
- Create: `tests/workbook_manager/test_workbook_profile.py`

**Interfaces:**
- Produces: `Finding`, `SourceSheet`, `WorkbookProfile`, `profile_workbook(path) -> WorkbookProfile`.
- Consumes: `LIVE_MODELS` and canonical roles from Task 1.

- [x] **Step 1: Write failing profile tests against the real workbook**

```python
from app.workbook_profile import profile_workbook


def test_every_workbook_sheet_has_one_disposition(repo_root):
    profile = profile_workbook(repo_root / "stingray_master.xlsx")
    assert len(profile.sheets) == 65
    assert len({sheet.source_sheet for sheet in profile.sheets}) == 65
    assert not [sheet for sheet in profile.sheets if not sheet.disposition]


def test_live_model_sources_have_identical_roles(repo_root):
    profile = profile_workbook(repo_root / "stingray_master.xlsx")
    role_sets = {
        model: frozenset(profile.active_sources[model])
        for model in ("stingray", "grand_sport", "z06")
    }
    assert len(set(role_sets.values())) == 1


def test_generated_and_future_sources_are_explicit(repo_root):
    profile = profile_workbook(repo_root / "stingray_master.xlsx")
    by_name = {sheet.source_sheet: sheet for sheet in profile.sheets}
    assert not [name for name in by_name if name.startswith("form_")]
    assert not [
        sheet for sheet in profile.sheets
        if sheet.disposition == "generated_artifact_validation"
    ]
    assert by_name["zr1_options"].disposition == "inactive_future_source"
```

The current workbook contract contains zero retired generated `form_*` sheets.
Profile copied or legacy inputs with a `form_*` sheet as
`generated_artifact_validation` and emit the `retired_generated_sheet_present`
contract mismatch; never import those sheets as source data.

- [x] **Step 2: Run tests and verify failure**

Expected: import error for the missing profile module.

- [x] **Step 3: Implement immutable compiler types and read-only profiling**

Use these public dataclasses:

```python
@dataclass(frozen=True)
class Finding:
    severity: Literal["info", "warning", "error"]
    status: Literal["mapped", "contract_mismatch", "decision_required"]
    code: str
    message: str
    source_sheet: str = ""
    source_row: int | None = None
    source_column: str = ""
    model_key: str = ""
    value: object = None


@dataclass(frozen=True)
class SchemaMapping:
    source_sheet: str
    source_column: str
    destination_table: str
    destination_column: str
    model_key: str = ""
    transform: str = "identity"
    reverse_transform: str = "identity"


@dataclass(frozen=True)
class LineageEntry:
    destination_table: str
    destination_key: Mapping[str, object]
    source_sheet: str
    source_row: int
    mapping_role: Literal["direct", "shared_source_split", "normalized"]


@dataclass(frozen=True)
class SourceSheet:
    source_sheet: str
    disposition: str
    headers: tuple[str, ...]
    row_count: int
    destination_tables: tuple[str, ...]
    reason: str


@dataclass(frozen=True)
class WorkbookProfile:
    workbook_path: Path
    workbook_sha256: str
    sheets: tuple[SourceSheet, ...]
    active_models: tuple[str, ...]
    active_sources: Mapping[str, Mapping[str, str]]
    findings: tuple[Finding, ...]
```

`profile_workbook` must open `read_only=True, data_only=True`, discover live
models from active `model_master` plus promoted `model_registry_promotion`, and
classify every sheet. Do not hardcode live source sheet names; derive them from
`model_workbook_sources` and use a finite disposition policy for generated,
inactive future, shared, and direct sources.

- [x] **Step 4: Run profile tests and workbook schema validator**

```bash
.venv/bin/python -m pytest tests/workbook_manager/test_workbook_profile.py -q
.venv/bin/python scripts/validate_workbook_schema.py stingray_master.xlsx
```

Expected: tests pass; the workbook validator exits successfully.

- [x] **Step 5: Commit Task 2**

```bash
git add workbook-manager/backend/app/compile_types.py workbook-manager/backend/app/workbook_profile.py tests/workbook_manager/test_workbook_profile.py
git commit -m "feat: profile workbook source coverage"
```

---

### Task 3: Central Model, Variant, Section, and Runtime Compiler

**Files:**
- Create: `workbook-manager/backend/app/central_compiler.py`
- Modify: `workbook-manager/backend/app/compile_types.py`
- Modify: `workbook-manager/backend/app/workbook_profile.py`
- Modify: `workbook-manager/backend/app/db.py`
- Create: `tests/workbook_manager/test_central_compiler.py`
- Modify: `tests/workbook_manager/test_catalog_schema.py`
- Modify: `docs/superpowers/specs/2026-07-16-workbook-congruent-relational-database-design.md`
- Modify: `docs/superpowers/plans/2026-07-16-workbook-congruent-relational-database.md`

**Interfaces:**
- Produces: `CompiledRow`, `CompiledTable`, `compile_central_tables(profile, workbook_path) -> tuple[CompiledTable, ...]`.
- Consumes: profile/types from Task 2 and central table names from Task 1.

- [x] **Step 1: Write failing central relationship tests**

Assert these concrete behaviors:

```python
@pytest.fixture
def compiled_central(real_workbook):
    profile = profile_workbook(real_workbook)
    return compile_central_tables(profile, real_workbook)


def test_variants_link_models_body_styles_and_trims(compiled_central):
    tables = {table.name: table for table in compiled_central}
    assert {row.values["body_style"] for row in tables["variants"].rows} == {
        "coupe", "convertible"
    }
    assert {row.values["trim_level"] for row in tables["variants"].rows} <= {
        row.values["trim_level"] for row in tables["trim_levels"].rows
    }
    assert {row.values["model_key"] for row in tables["model_variants"].rows} >= {
        "stingray", "grand_sport", "z06"
    }


def test_runtime_structure_has_one_model_aware_route(compiled_central):
    tables = {table.name: table for table in compiled_central}
    step_keys = {
        (row.values["model_key"], row.values["step_key"])
        for row in tables["runtime_steps"].rows
    }
    assert ("stingray", "body_style") in step_keys
    assert ("grand_sport", "body_style") in step_keys
    assert ("z06", "body_style") in step_keys


def test_runtime_route_keys_keep_hidden_summary_buckets_distinct(compiled_central):
    tables = {table.name: table for table in compiled_central}
    routes = {
        (row.values["model_key"], row.values["route_key"]): row.values["route_kind"]
        for row in tables["runtime_route_keys"].rows
    }
    assert routes[("z06", "standard_equipment")] == "hidden_summary_bucket"
    assert ("z06", "standard_equipment") not in {
        (row.values["model_key"], row.values["step_key"])
        for row in tables["runtime_steps"].rows
    }
```

- [x] **Step 2: Verify tests fail because the compiler is absent**

- [x] **Step 3: Implement central compilation and exact lineage**

Define:

```python
@dataclass(frozen=True)
class CompiledRow:
    values: Mapping[str, object]
    source_sheet: str
    source_row: int
    lineage_role: str = "direct"


@dataclass(frozen=True)
class CompiledTable:
    name: str
    primary_key: tuple[str, ...]
    rows: tuple[CompiledRow, ...]
    model_key: str = ""
    role: str = ""
```

Compile `models`, `model_registry_promotion`, `body_styles`, `trim_levels`,
`variants`, `model_variants`, `sections`, `section_presentation`,
`runtime_route_keys`, `runtime_steps`, `runtime_context_sections`, `runtime_context_choices`,
`runtime_summary_sections`, `runtime_step_summary_map`, `model_assets`,
`price_ref`, and `rule_phrase_map`.

Normalize case consistently (`1LT` -> `1lt`, body styles lowercase), retain the
original value in lineage mapping parameters, and use `None` for unrestricted
scope only. Context sections remain distinct from option sections but must
reference the same model/route keys.

Compile the complete runtime context-choice inventory from active model
variants, matching `contract.py::build_model_context_choices`: two body-style
choices plus six body/trim/variant choices per live model (24 total), keyed by
`(model_key, context_choice_id)`. `context_choice_copy` supplies tooltip copy
through the current wildcard/exact precedence; it does not create inventory.
Retain the choice's model route, context section, body, optional trim and
variant, price, display order, and derived/source lineage.

Populate `runtime_route_keys` from the union of active
`runtime_steps.step_key` and active `step_order_summary_map.step_key` values per
live model. Runtime-step keys are `visible_step`; summary-only keys are
`hidden_summary_bucket`. All runtime step, context-section, and step-summary
route references use the composite model/route foreign key. This
user-approved derived domain resolves the current Z06
`standard_equipment -> required_charges` summary route without adding a fake
visible runtime step and must not be interpreted as option active/selectable
state.

Fail closed on every active `model_variants` row whose normalized `model_key`
is not live, and require each live model's distinct active membership count to
equal `model_master.expected_variant_count`. The step-summary mapping identity
is `(model_key, step_key)`: one route has exactly one summary destination, with
`section_key` retained as a required summary-section foreign key.

Normalization evidence records exact pre-trim, pre-lowercase workbook text.
Derived route rows merge source mapping parameters and retain reversible
evidence for both the model and route key.

Compile blank `PriceRef.Trim` as `None`. The SQL table uses an internal
`price_ref_id INTEGER PRIMARY KEY AUTOINCREMENT` plus a NULL-safe unique
expression index on
`(option_type, COALESCE(trim_level, '<unrestricted>'), code)`. Reject empty
identity values and the reserved sentinel.

- [x] **Step 4: Run central compiler and catalog tests**

Expected: all Task 1-3 tests pass.

- [x] **Step 5: Commit Task 3**

```bash
git add workbook-manager/backend/app/central_compiler.py workbook-manager/backend/app/compile_types.py workbook-manager/backend/app/workbook_profile.py workbook-manager/backend/app/db.py tests/workbook_manager/test_central_compiler.py tests/workbook_manager/test_catalog_schema.py docs/superpowers/specs/2026-07-16-workbook-congruent-relational-database-design.md docs/superpowers/plans/2026-07-16-workbook-congruent-relational-database.md
git commit -m "feat: compile central form relationships"
```

---

### Task 4: Identical Direct Model-Source Compilation

**Files:**
- Create: `workbook-manager/backend/app/model_compiler.py`
- Create: `tests/workbook_manager/test_model_compiler.py`

**Interfaces:**
- Produces: `compile_direct_model_tables(profile, workbook_path, central) -> tuple[CompiledTable, ...]`.
- Consumes: Tasks 1-3 compiler types, source registry, and central domains.

- [x] **Step 1: Write failing tests for all direct model roles**

```python
@pytest.fixture
def compiled_models(real_workbook, compiled_central):
    profile = profile_workbook(real_workbook)
    return compile_direct_model_tables(
        profile, real_workbook, compiled_central
    )


def test_model_collections_have_identical_roles(compiled_models):
    roles = {
        model: {table.role for table in compiled_models if table.model_key == model}
        for model in ("stingray", "grand_sport", "z06")
    }
    assert roles["stingray"] == roles["grand_sport"] == roles["z06"]


def test_options_and_availability_reconcile_real_workbook(compiled_models):
    by_name = {table.name: table for table in compiled_models}
    assert len(by_name["stingray_options"].rows) == 242
    assert len(by_name["grand_sport_options"].rows) == 241
    assert len(by_name["z06_options"].rows) == 244
    assert len(by_name["stingray_option_availability"].rows) == 1452


def test_polymorphic_sources_are_typed_without_prefix_guessing(compiled_models):
    table = next(t for t in compiled_models if t.name == "stingray_rule_mapping")
    for row in table.rows:
        values = row.values
        assert bool(values.get("source_option_id")) ^ bool(values.get("source_interior_id"))
```

- [x] **Step 2: Verify red failures**

Expected: missing `model_compiler` or missing `role`/`model_key` fields on
`CompiledTable`.

- [x] **Step 3: Implement direct role compilation**

Use the `CompiledTable.model_key` and `CompiledTable.role` fields defined in
Task 3. Resolve exact workbook sources only through `profile.active_sources`.

Compile direct roles first: options, OVS, rule mapping, price rules, rule
groups/members, exclusive groups/members, and variant overrides. Use exact
workbook row identities and these hardening rules:

```python
def typed_entity_reference(entity_id, option_ids, interior_ids):
    in_options = entity_id in option_ids
    in_interiors = entity_id in interior_ids
    if in_options == in_interiors:
        raise DecisionRequired(
            "entity_reference_ambiguous_or_missing", value=entity_id
        )
    return {
        "option_id": entity_id if in_options else None,
        "interior_id": entity_id if in_interiors else None,
    }
```

Targets must resolve to the model options set. Normalize body/trim/variant
unrestricted scopes to `None`; preserve restricted values through central
domain keys. Emit a `schema_mapping` entry for every renamed column.

- [x] **Step 4: Run Tasks 1-4 tests**

Expected: exact current row counts and no unresolved live option/OVS reference.

- [x] **Step 5: Commit Task 4**

```bash
git add workbook-manager/backend/app/model_compiler.py workbook-manager/backend/app/compile_types.py tests/workbook_manager/test_model_compiler.py
git commit -m "feat: compile identical live model table families"
```

---

### Task 5: Proven Shared-Source Splitting

**Files:**
- Create: `workbook-manager/backend/app/shared_compiler.py`
- Modify: `tests/workbook_manager/conftest.py`
- Create: `tests/workbook_manager/test_shared_compiler.py`

**Interfaces:**
- Produces: `compile_shared_model_tables(profile, workbook_path, central, direct) -> SharedCompilation`.
- Consumes: registered interior sources, compiled model options, runtime wildcard behavior, and compiler types.

- [x] **Step 1: Write failing split and dead-end tests**

Cover real-workbook model interiors, wildcard asset overlay, `adds_rpo` aliasing,
and ambiguous IDs:

```python
@pytest.fixture
def shared(real_workbook):
    profile = profile_workbook(real_workbook)
    central = compile_central_tables(profile, real_workbook)
    direct = compile_direct_model_tables(profile, real_workbook, central)
    return compile_shared_model_tables(profile, real_workbook, central, direct)


def test_shared_interiors_are_split_by_registered_scope(shared):
    by_name = {table.name: table for table in shared.tables}
    assert by_name["stingray_interiors"].rows
    assert by_name["grand_sport_interiors"].rows
    assert by_name["z06_interiors"].rows
    assert all(r.lineage_role == "shared_source_split" for r in by_name["z06_interiors"].rows)


def test_color_override_added_option_is_a_foreign_key(shared):
    row = shared.table("grand_sport_color_overrides").rows[0].values
    assert row["added_option_id"].startswith("opt_")
    assert "adds_rpo" not in row


def test_completed_model_families_have_all_17_roles(shared):
    roles = {
        model: {
            table.role for table in shared.tables if table.model_key == model
        }
        for model in LIVE_MODELS
    }
    assert all(model_roles == set(MODEL_TABLE_ROLES) for model_roles in roles.values())


def test_unowned_shared_row_requires_decision(unowned_shared_row_workbook):
    profile = profile_workbook(unowned_shared_row_workbook)
    central = compile_central_tables(profile, unowned_shared_row_workbook)
    direct = compile_direct_model_tables(
        profile, unowned_shared_row_workbook, central
    )
    result = compile_shared_model_tables(
        profile, unowned_shared_row_workbook, central, direct
    )
    assert any(
        finding.status == "decision_required"
        and finding.code == "shared_row_owner_unresolved"
        for finding in result.findings
    )
```

The `unowned_shared_row_workbook` fixture must copy the real workbook, append
`int_unowned_test` to `lt_interiors`, append a `color_overrides` row referencing
that interior and two real Stingray option IDs, and intentionally add no
`model_interior_scope` row. The compiler must report the row; it must not guess
Stingray ownership from the option IDs.

- [x] **Step 2: Run and observe expected failures**

- [x] **Step 3: Implement shared splitters with current contract semantics**

Implement:

```python
@dataclass(frozen=True)
class SharedCompilation:
    tables: tuple[CompiledTable, ...]
    mappings: tuple[SchemaMapping, ...]
    findings: tuple[Finding, ...]

    def table(self, name: str) -> CompiledTable:
        return next(table for table in self.tables if table.name == name)
```

`SharedCompilation.tables` is the completed direct-plus-shared model table set,
not only the newly split subset; this makes missing roles visible before load.

Split interiors by registered source plus active `model_interior_scope`; split
components/scope by exact `model_key`; split color overrides only when interior,
option, and added option all resolve for that model. Split assets by target type,
apply wildcard option rows first, and let exact-model rows replace the same
target. Expand wildcard context copy only where current runtime metadata accepts
it. Never assign a shared row based solely on an ID collision.

Context-choice assets map `asset_map.target_id` directly to the canonical
`context_choice_id` and reference `(model_key, context_choice_id)`; wildcard
context-choice assets remain unsupported.

- [x] **Step 4: Run shared compiler plus existing workbook schema tests**

```bash
.venv/bin/python -m pytest tests/workbook_manager/test_shared_compiler.py tests/test_schema_validation_metadata.py -q
```

Expected: pass; shared rows have complete one-to-many lineage.

- [x] **Step 5: Commit Task 5**

```bash
git add workbook-manager/backend/app/shared_compiler.py tests/workbook_manager/conftest.py tests/workbook_manager/test_shared_compiler.py
git commit -m "feat: split shared workbook sources by model"
```

---

### Task 6: Candidate Database Import, Reconciliation, and Atomic Promotion

**Files:**
- Modify: `workbook-manager/backend/app/importer.py`
- Create: `workbook-manager/backend/app/migration.py`
- Modify: `workbook-manager/backend/app/db.py`
- Modify: `tests/workbook_manager/conftest.py`
- Create: `tests/workbook_manager/test_import_promotion.py`

**Interfaces:**
- Produces: `compile_workbook(path) -> CompiledWorkbook`, `load_candidate(compiled, path)`, `promote_candidate(candidate, destination)`, `import_workbook(db_path, workbook_path) -> ImportReport`.
- Consumes: all compiler output from Tasks 2-5 and DDL from Task 1.

- [x] **Step 1: Write failing candidate/promotion tests**

Create `broken_fk_workbook` by copying the real workbook, deleting the first
`stingray_options` row whose `option_id` is referenced by `stingray_ovs`, and
leaving the OVS row intact. Create `legacy_db_path` with the current
`pending_changes` DDL and one exact staged row. Then write:

```sql
CREATE TABLE pending_changes (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ts TEXT NOT NULL,
  session_id TEXT NOT NULL DEFAULT '',
  table_name TEXT NOT NULL,
  model_id TEXT NOT NULL DEFAULT '',
  entity_key_json TEXT NOT NULL,
  op TEXT NOT NULL,
  old_json TEXT,
  new_json TEXT,
  status TEXT NOT NULL DEFAULT 'staged',
  validation_json TEXT NOT NULL DEFAULT '{}',
  confirmed_dependencies INTEGER NOT NULL DEFAULT 0
);
```

```python
def test_failed_candidate_does_not_replace_verified_database(
    tmp_path, broken_fk_workbook
):
    destination = tmp_path / "workbook.sqlite3"
    conn = db.connect(destination)
    db.create_canonical_schema(conn)
    db.set_meta(conn, "verification_marker", "keep")
    conn.commit()
    conn.close()
    before = hashlib.sha256(destination.read_bytes()).hexdigest()
    report = importer.import_workbook(
        destination, broken_fk_workbook, audit_contracts=False
    )
    assert report.status == "decision_required"
    assert hashlib.sha256(destination.read_bytes()).hexdigest() == before


def test_successful_candidate_has_complete_lineage(tmp_path, real_workbook):
    destination = tmp_path / "workbook.sqlite3"
    report = importer.import_workbook(destination, real_workbook, audit_contracts=False)
    assert report.status == "validated"
    conn = db.connect(destination)
    assert conn.execute("PRAGMA foreign_key_check").fetchall() == []
    assert conn.execute("SELECT COUNT(*) FROM import_lineage").fetchone()[0] > 0


def test_legacy_pending_changes_block_replacement(legacy_db_path, real_workbook):
    conn = sqlite3.connect(legacy_db_path)
    conn.execute(
        "INSERT INTO pending_changes("
        "ts, session_id, table_name, model_id, entity_key_json, op, old_json, "
        "new_json, status, validation_json, confirmed_dependencies"
        ") VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            "2026-07-16T12:00:00+00:00", "migration-test", "options",
            "stingray", '{"option_id":"opt_pending"}', "add", None,
            '{"option_id":"opt_pending"}', "staged", "{}", 0,
        ),
    )
    conn.commit()
    conn.close()
    report = importer.import_workbook(
        legacy_db_path, real_workbook, audit_contracts=False
    )
    assert report.status == "decision_required"
    assert report.finding_codes == ("legacy_pending_changes",)
```

The fixture DDL must reproduce all current `pending_changes` columns from
`workbook-manager/backend/app/db.py`; it must not import the new schema helper
to manufacture a false non-legacy database.

- [x] **Step 2: Verify failures against the current destructive clear/import path**

Expected: tests fail because current importer accepts a connection, clears live
tables, and lacks candidate promotion.

- [x] **Step 3: Implement compile/load/audit/promotion orchestration**

Define the orchestration result types exactly:

```python
@dataclass(frozen=True)
class CompiledWorkbook:
    tables: tuple[CompiledTable, ...]
    source_catalog: tuple[SourceSheet, ...]
    schema_mappings: tuple[SchemaMapping, ...]
    lineage: tuple[LineageEntry, ...]
    findings: tuple[Finding, ...]


@dataclass(frozen=True)
class ImportReport:
    status: Literal["validated", "decision_required", "contract_mismatch"]
    live_models: tuple[str, ...]
    findings: tuple[Finding, ...]
    decision_required: tuple[Finding, ...]
    contract_differences: tuple[Finding, ...]
    candidate_path: Path | None
    promoted_path: Path | None

    @property
    def finding_codes(self) -> tuple[str, ...]:
        return tuple(finding.code for finding in self.findings)
```

Load `CompiledWorkbook.tables` in dependency order inside one transaction.
Before promotion:

```python
def candidate_integrity_errors(conn):
    errors = [dict(row) for row in conn.execute("PRAGMA foreign_key_check")]
    errors.extend(reconcile_source_counts(conn))
    errors.extend(validate_mapping_coverage(conn))
    return errors
```

Back up an existing destination with `sqlite3.Connection.backup`, write the
candidate beside the destination, run `PRAGMA wal_checkpoint(TRUNCATE)`, close
all candidate connections, `fsync` the candidate file and its parent directory,
then replace with `os.replace`. Remove failed candidate/WAL/SHM files. Audit
legacy staged and unsynced changes before building. Do not copy ambiguous
legacy history.

`audit_contracts=False` is an internal test-only transition used solely in this task
before Task 7 exists. Task 7 must delete that bypass and make the real contract
auditor mandatory before any production candidate can be promoted.

- [x] **Step 4: Run import tests against a temporary destination**

Expected: real workbook imports without touching the repo database or workbook;
failure cases leave sentinel destination bytes unchanged.

- [x] **Step 5: Commit Task 6**

```bash
git add workbook-manager/backend/app/importer.py workbook-manager/backend/app/migration.py workbook-manager/backend/app/db.py tests/workbook_manager/conftest.py tests/workbook_manager/test_import_promotion.py
git commit -m "feat: promote validated workbook database atomically"
```

---

### Task 7: SQL-to-Workbook Adapter and Runtime Contract Audit

**Files:**
- Create: `workbook-manager/backend/app/export_adapter.py`
- Create: `workbook-manager/backend/app/contract_audit.py`
- Modify: `tests/workbook_manager/conftest.py`
- Create: `tests/workbook_manager/test_contract_audit.py`

**Interfaces:**
- Produces: `export_comparison_workbook(conn, source, destination)`, `audit_runtime_contracts(conn, source_workbook, temp_dir) -> ContractAudit`.
- Consumes: schema mapping/lineage, current generators, `discover_generation_model_configs`, and `generate_model_artifacts`.

- [x] **Step 1: Write failing reversible mapping and contract tests**

Declare these shared imported-database fixtures in `conftest.py`; they are
expected to fail until the real contract auditor is implemented in Step 3:

```python
@pytest.fixture
def imported_db_path(tmp_path, real_workbook):
    database_path = tmp_path / "imported.sqlite3"
    report = importer.import_workbook(database_path, real_workbook)
    assert report.status == "validated"
    return database_path


@pytest.fixture
def imported_db(imported_db_path):
    conn = db.connect(imported_db_path)
    try:
        yield conn
    finally:
        conn.close()
```

Define `load_rows` in the test module rather than relying on an implicit helper:

```python
def load_rows(path: Path, sheet_name: str) -> tuple[dict[str, object], ...]:
    workbook = load_workbook(path, read_only=True, data_only=False)
    worksheet = workbook[sheet_name]
    values = worksheet.iter_rows(values_only=True)
    headers = tuple(str(value) if value is not None else "" for value in next(values))
    rows = tuple(
        {header: value for header, value in zip(headers, row) if header}
        for row in values
        if any(value is not None and value != "" for value in row)
    )
    workbook.close()
    return rows


def test_scope_and_semantic_aliases_round_trip(imported_db, real_workbook, tmp_path):
    output = tmp_path / "roundtrip.xlsx"
    export_adapter.export_comparison_workbook(imported_db, real_workbook, output)
    original = load_rows(real_workbook, "color_overrides")
    rebuilt = load_rows(output, "color_overrides")
    assert rebuilt == original


@pytest.mark.slow
def test_all_promoted_contracts_match_except_timestamps(imported_db, real_workbook, tmp_path):
    audit = contract_audit.audit_runtime_contracts(
        imported_db, real_workbook, tmp_path
    )
    assert audit.models == ("stingray", "grand_sport", "z06")
    assert audit.differences == ()
```

- [x] **Step 2: Run the focused tests and confirm missing adapter failures**

- [x] **Step 3: Implement reversible export and isolated generation**

Copy the workbook to a temporary path, rewrite canonical source sheets through
`schema_mapping`, reconstruct original aliases (`added_option_id` ->
`adds_rpo`), restore model-specific blank/`*` scope representation, and preserve
generated/unmanaged sheets until generation runs.

Define the audit result exactly:

```python
@dataclass(frozen=True)
class ContractDifference:
    model_key: str
    json_path: str
    baseline_value: object
    candidate_value: object


@dataclass(frozen=True)
class ContractAudit:
    models: tuple[str, ...]
    differences: tuple[ContractDifference, ...]
    generated_paths: Mapping[str, Path]
```

For each model:

```python
configs = discover_generation_model_configs(comparison_workbook)
config = configs[model_key].with_overrides(
    root=temp_dir / model_key,
    workbook_path=comparison_workbook,
    output_dir=temp_dir / model_key / "output",
    app_dir=temp_dir / model_key / "app",
)
result = generate_model_artifacts(config)
```

Load the baseline promoted contract path from workbook promotion metadata.
Recursively remove only `generated_at`, `sourceGeneratedAt`, and `generatedAt`
before comparison. Emit exact JSON paths for every difference. Any difference
is `contract_mismatch` and blocks promotion.

Finish Task 7 by removing the Task 6 `audit_contracts` argument entirely.
`import_workbook(db_path, workbook_path)` must always run
`audit_runtime_contracts` and may call `promote_candidate` only when
`differences == ()`.

- [x] **Step 4: Run contract audit and existing model contract tests**

```bash
.venv/bin/python -m pytest tests/workbook_manager/test_contract_audit.py -q
node --test tests/stingray-form-regression.test.mjs
node --test tests/grand-sport-draft-data.test.mjs
node --test tests/z06-form-data-draft.test.mjs
```

Expected: SQL round trip matches all three contracts; no repo artifact changes.

- [x] **Step 5: Commit Task 7**

```bash
git add workbook-manager/backend/app/export_adapter.py workbook-manager/backend/app/contract_audit.py tests/workbook_manager/conftest.py tests/workbook_manager/test_contract_audit.py
git commit -m "feat: audit SQL data against runtime contracts"
```

---

### Task 8: Registry-Driven Validation, Staging, History, and Safe Sync

**Files:**
- Modify: `workbook-manager/backend/app/validation.py`
- Modify: `workbook-manager/backend/app/staging.py`
- Modify: `workbook-manager/backend/app/sync.py`
- Modify: `workbook-manager/backend/app/catalog.py`
- Delete: `workbook-manager/backend/app/specs.py`
- Modify with explicit approval: `tests/test_workbook_manager.py`
- Create: `tests/workbook_manager/test_staging_sync.py`

**Interfaces:**
- Produces: `validate_record(conn, model_key, role, record, op, original_key)`, `find_dependents(conn, model_key, role, key)`, unchanged staged-change verbs using `table_role` rather than conceptual table names.
- Consumes: safe physical-table resolution, schema mappings, and export adapter.

- [x] **Step 0: Resolve the dirty legacy-test gate before editing**

`tests/test_workbook_manager.py` has a user-owned unstaged module-reset fix, but
the rest of that file asserts the Stage 1 shared `options` table and legacy
connection-based importer. Those assertions cannot pass against the approved
physical per-model schema. Stop and obtain explicit authorization to migrate
the file while preserving and including the module-reset fix. Do not create
shared conceptual SQL views or a second compatibility data path to avoid this
gate.

- [x] **Step 1: Write failing staging/dependency/sync tests**

Cover add/update/delete per physical model table, cross-model rejection,
dependent-delete blocking across all model relations, append-only history, and
dry-run batch field reversal:

```python
def valid_option_record(conn) -> dict[str, object]:
    section_id = conn.execute(
        "SELECT section_id FROM sections ORDER BY section_id LIMIT 1"
    ).fetchone()["section_id"]
    return {
        "option_id": "opt_test_901",
        "rpo": "T901",
        "price": 0,
        "option_name": "Migration Test Option",
        "description": "",
        "detail_raw": "",
        "section_id": section_id,
        "selectable": 1,
        "display_order": 9999,
        "active": 1,
        "display_behavior": None,
    }


def dependent_option_id(conn, model_key: str) -> str:
    table_prefix = physical_table(model_key, "options").removesuffix("_options")
    row = conn.execute(
        f"SELECT a.option_id FROM {table_prefix}_option_availability a "
        f"JOIN {table_prefix}_exclusive_group_members e "
        "ON e.option_id=a.option_id ORDER BY a.option_id LIMIT 1"
    ).fetchone()
    assert row is not None
    return row["option_id"]


def commit_added_option_change(conn) -> None:
    staging.stage_change(
        conn, model_key="stingray", table_role="options", op="add",
        key={"option_id": "opt_test_901"}, record=valid_option_record(conn),
    )
    result = staging.commit_staged(conn, actor="test")
    assert result["status"] == "committed"


def test_staged_option_uses_model_physical_table(imported_db):
    change = staging.stage_change(
        imported_db, model_key="stingray", table_role="options", op="add",
        key={"option_id": "opt_test_901"},
        record=valid_option_record(imported_db),
    )
    assert change["sql_table"] == "stingray_options"


def test_delete_finds_all_option_dependents(imported_db):
    option_id = dependent_option_id(imported_db, "stingray")
    dependents = validation.find_dependents(
        imported_db, "stingray", "options", {"option_id": option_id}
    )
    assert {item["table_role"] for item in dependents} >= {
        "option_availability", "exclusive_group_members"
    }


def test_sync_batch_restores_workbook_field_names(imported_db, real_workbook):
    commit_added_option_change(imported_db)
    batch = sync.build_batch(imported_db, real_workbook)
    assert batch["items"][0]["sheet"] == "stingray_options"
    assert "option_id" in batch["items"][0]["row"]
```

- [x] **Step 2: Run tests and observe conceptual-spec failures**

- [x] **Step 3: Replace `TableSpec` lookups with catalog/registry metadata**

All public staging payloads use `model_key` and `table_role`; `sql_table` is
resolved internally. Validate types, enums, FKs, immutable keys, and dependency
checks against catalog metadata. Continue using parameterized values and
allowlisted physical identifiers.

Build workbook sync operations through `schema_mapping`. Dry run still calls
`editor_ops.apply_batch(write=False)`; live write still requires matching mtime,
warning confirmation, and `confirm='SYNC'` at the API boundary.

Migrate `tests/test_workbook_manager.py` from shared-table SQL to physical
model-role assertions: use `create_canonical_schema`, path-based atomic import,
`ImportReport` attributes, `physical_table(model, role)`, registry/source
catalog coverage, and the new staging/dependency signatures. Preserve the
existing full-`app` module reset and its 422 regression assertion exactly.

Delete `specs.py` only after
`rg "from .*specs|import specs|SPEC_BY_TABLE|TABLE_SPECS" workbook-manager tests/test_workbook_manager.py`
returns no callers. Do not replace it with compatibility views or duplicate
catalog definitions.

- [x] **Step 4: Run staging/sync tests and a scratch-copy slow gate**

```bash
.venv/bin/python -m pytest tests/workbook_manager/test_staging_sync.py -q
WBM_SLOW_GATE=1 .venv/bin/python -m pytest tests/workbook_manager/test_staging_sync.py -q
```

Expected: both pass; scratch copy gets a backup, real workbook hash is unchanged.

- [x] **Step 5: Commit Task 8**

```bash
git add workbook-manager/backend/app/catalog.py workbook-manager/backend/app/validation.py workbook-manager/backend/app/staging.py workbook-manager/backend/app/sync.py workbook-manager/backend/app/specs.py tests/workbook_manager/test_staging_sync.py tests/test_workbook_manager.py
git commit -m "refactor: route workbook edits through canonical tables"
```

Stage `tests/test_workbook_manager.py` only after the Step 0 authorization; the
Fable validation receipt remains unstaged.

---

### Task 9: Typed FastAPI v2 Routes

**Files:**
- Modify: `workbook-manager/backend/app/schemas.py`
- Modify: `workbook-manager/backend/app/main.py`
- Create: `tests/workbook_manager/test_api_v2.py`

**Interfaces:**
- Produces: approved `/api/imports`, findings, mappings, model-table, variants,
  runtime, stage/commit/history/sync/export/backup routes, plus
  `create_app(db_path: Path | None = None) -> FastAPI` for isolated tests.
- Consumes: Tasks 1-8 backend services; route functions contain no compiler SQL.

- [x] **Step 1: Write failing API tests**

```python
@pytest.fixture
def client(imported_db_path):
    with TestClient(create_app(imported_db_path)) as test_client:
        yield test_client


def test_model_tables_expose_physical_name_and_lineage(client):
    response = client.get("/api/models/grand_sport/tables")
    assert response.status_code == 200
    options = next(t for t in response.json()["tables"] if t["role"] == "options")
    assert options["sql_table"] == "grand_sport_options"
    assert options["source_sheets"] == ["grandSport_options"]


def test_arbitrary_model_or_role_is_rejected(client):
    assert client.get("/api/models/bad/tables").status_code == 404
    assert client.get("/api/models/stingray/tables/sqlite_master").status_code == 404


def test_decision_finding_has_actionable_source_detail(
    client, broken_fk_workbook
):
    response = client.post(
        "/api/imports", json={"workbook_path": str(broken_fk_workbook)}
    )
    assert response.status_code == 409
    finding = response.json()["detail"]["findings"][0]
    assert {"source_sheet", "source_row", "source_column", "code"} <= finding
```

- [x] **Step 2: Verify red 404/route failures**

- [x] **Step 3: Implement typed request/response models and routes**

Add `ImportReportOut`, `FindingOut`, `SchemaMappingOut`, `ModelTableOut`,
`ModelRuntimeOut`, and revise `StageChangeRequest` to accept `model_key` and
`table_role`. Use dependency-injected `get_conn`; translate domain exceptions to
422, decision/contract blockers to 409, missing allowlisted resources to 404.

Keep existing `/api/import`, `/api/models/{model}/collections`, and
`/api/records/...` routes as thin calls to the same service functions until the
frontend switches in Task 10. They must not retain conceptual-table SQL. Task
10 removes these transitional aliases after the React callers use v2, leaving
one supported API route per operation.

- [x] **Step 4: Run API and existing workbook-manager tests**

```bash
.venv/bin/python -m pytest tests/workbook_manager/test_api_v2.py -q
.venv/bin/python -m pytest tests/test_workbook_manager.py -q
```

Expected: v2 tests pass; the user's module-reset fix keeps the legacy API
validation test at 422 rather than 500.

- [x] **Step 5: Commit Task 9 without staging the user-owned legacy test change**

```bash
git add workbook-manager/backend/app/main.py workbook-manager/backend/app/schemas.py tests/workbook_manager/test_api_v2.py
git commit -m "feat: expose canonical workbook database API"
```

---

### Task 10: Registry-Driven React Navigation and Findings UI

**Files:**
- Modify: `workbook-manager/backend/app/main.py`
- Modify: `workbook-manager/frontend/src/api.js`
- Create: `workbook-manager/frontend/src/tableRegistry.js`
- Modify: `workbook-manager/frontend/src/components/ModelOperations.jsx`
- Create: `workbook-manager/frontend/src/components/ImportFindings.jsx`
- Modify: `workbook-manager/frontend/src/App.jsx`
- Create: `tests/workbook_manager/test_frontend_contract.mjs`
- Modify: `tests/workbook_manager/test_api_v2.py`

**Interfaces:**
- Produces: frontend calls to v2 model/table roles and visible import/contract findings.
- Consumes: typed Task 9 response shapes; no SQL table-name construction in React.

- [x] **Step 1: Write failing pure frontend contract tests**

```javascript
import test from "node:test";
import assert from "node:assert/strict";
import { tableViewModel, blockingFindings } from "../../workbook-manager/frontend/src/tableRegistry.js";

test("uses server supplied canonical and source names", () => {
  const table = tableViewModel({
    role: "options",
    sql_table: "grand_sport_options",
    source_sheets: ["grandSport_options"],
    count: 241,
  });
  assert.equal(table.key, "options");
  assert.equal(table.sqlTable, "grand_sport_options");
  assert.equal(table.sourceLabel, "grandSport_options");
});

test("decision and contract findings are blocking", () => {
  const findings = blockingFindings([
    { status: "mapped" },
    { status: "contract_mismatch" },
    { status: "decision_required" },
  ]);
  assert.equal(findings.length, 2);
});
```

- [x] **Step 2: Run Node test and verify module-not-found failure**

```bash
node --test tests/workbook_manager/test_frontend_contract.mjs
```

- [x] **Step 3: Implement v2 API calls and UI components**

`tableRegistry.js` must remain pure. `api.js` calls server routes with encoded
model/role values. `ModelOperations` stores the role as selection state and uses
the server-supplied `sql_table`/`source_sheets` only for display. Add a Findings
tab/panel showing severity, status, model, source sheet/row/column, code, and
message; do not offer an automatic fix for `decision_required`.

After all React calls use v2, remove `/api/import`,
`/api/models/{model}/collections`, and `/api/records/...`. Add API assertions
that those three legacy surfaces return 404 and that their handlers no longer
appear in the FastAPI route registry.

- [x] **Step 4: Run Node test and Vite build**

```bash
node --test tests/workbook_manager/test_frontend_contract.mjs
cd workbook-manager/frontend && npm run build
```

Expected: tests and build pass without adding dependencies.

- [x] **Step 5: Commit Task 10**

```bash
git add workbook-manager/backend/app/main.py workbook-manager/frontend/src/api.js workbook-manager/frontend/src/tableRegistry.js workbook-manager/frontend/src/App.jsx workbook-manager/frontend/src/components/ModelOperations.jsx workbook-manager/frontend/src/components/ImportFindings.jsx tests/workbook_manager/test_api_v2.py tests/workbook_manager/test_frontend_contract.mjs
git commit -m "feat: show canonical tables and import findings"
```

---

### Task 11: Full Completion Audit, Browser Verification, and Documentation

**Files:**
- Create: `tests/workbook_manager/test_completion_audit.py`
- Modify: `workbook-manager/README.md`
- Modify: `README.md` only for command-table/pointer ownership
- Modify: `docs/superpowers/specs/2026-07-16-workbook-congruent-relational-database-design.md`
- Modify: this plan only to check completed steps and record results during execution

**Interfaces:**
- Produces: final requirement-by-requirement evidence and closed owning spec.
- Consumes: the complete system from Tasks 1-10.

- [x] **Step 1: Add a failing completion-audit test before docs**

Create `tests/workbook_manager/test_completion_audit.py` that builds a temporary
database from the real workbook and asserts:

```python
def primary_key(conn, table_name: str) -> tuple[str, ...]:
    return tuple(
        row["name"]
        for row in conn.execute(f"PRAGMA table_info({table_name})")
        if row["pk"]
    )


def table_roles(conn, model_key: str) -> tuple[str, ...]:
    return tuple(
        row["table_role"]
        for row in conn.execute(
            "SELECT table_role FROM model_table_registry "
            "WHERE model_key=? AND active=1 ORDER BY table_role",
            (model_key,),
        )
    )


def table_exists(conn, table_name: str) -> bool:
    return conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
        (table_name,),
    ).fetchone() is not None


@pytest.fixture
def audited_database(tmp_path, real_workbook):
    database_path = tmp_path / "audited.sqlite3"
    report = importer.import_workbook(database_path, real_workbook)
    conn = db.connect(database_path)
    try:
        yield conn, report
    finally:
        conn.close()


def test_objective_completion(audited_database):
    conn, report = audited_database
    assert report.status == "validated"
    assert report.live_models == ("stingray", "grand_sport", "z06")
    assert report.decision_required == ()
    assert report.contract_differences == ()
    assert conn.execute("PRAGMA foreign_key_check").fetchall() == []
    for model in report.live_models:
        assert primary_key(conn, f"{model}_options") == ("option_id",)
        assert table_roles(conn, model) == tuple(sorted(MODEL_TABLE_ROLES))
    assert not table_exists(conn, "options")
```

- [x] **Step 2: Run the complete automated gate set**

```bash
.venv/bin/python -m pytest tests/workbook_manager -q
.venv/bin/python -m pytest tests/test_workbook_manager.py -q
.venv/bin/python scripts/validate_workbook_package.py stingray_master.xlsx
.venv/bin/python scripts/validate_workbook_schema.py stingray_master.xlsx
node --test tests/workbook_manager/test_frontend_contract.mjs
node --test tests/stingray-form-regression.test.mjs
node --test tests/grand-sport-draft-data.test.mjs
node --test tests/z06-form-data-draft.test.mjs
cd workbook-manager/frontend && npm run build
git diff --check
```

Expected: all commands pass. Record exact counts and any environment skips.

- [x] **Step 3: Run manual FastAPI and browser verification**

Start `./workbook-manager/run.sh` with `WBM_DB` and `WBM_VAR_DIR` pointing to a
temporary directory. Verify at desktop and mobile widths:

- all three live models appear;
- each shows the identical 17 table roles;
- canonical and workbook source names are both visible;
- options load/search by `option_id`;
- sections, variants, body styles, trims, and runtime structure resolve;
- contract/decision findings display source evidence;
- no live sync is triggered.

Save screenshots under `/private/tmp`; do not add them to the repository.

- [x] **Step 4: Audit preserved boundaries and update owning docs**

Compare hashes for `stingray_master.xlsx`, `form-app/data.js`, and promoted
runtime contracts against pre-implementation values. Confirm no dealer files
changed. Update the workbook-manager README with exact setup/run/import/audit
commands and close the design spec with completion date, changed surfaces,
validation results, residual risks, and `none implied` follow-up when true.

- [x] **Step 5: Commit documentation and completion audit**

```bash
git add tests/workbook_manager/test_completion_audit.py workbook-manager/README.md README.md docs/superpowers/specs/2026-07-16-workbook-congruent-relational-database-design.md docs/superpowers/plans/2026-07-16-workbook-congruent-relational-database.md
git commit -m "docs: verify relational workbook database migration"
```

Do not stage the user's pre-existing modified files unless the user separately
authorizes including them.

### Task 11 execution result

- The completion-audit test was added before documentation. Its first valid
  behavior run passed because it audits the already-completed Tasks 1-10; the
  initial linked-worktree invocation exposed only missing local environment
  setup (`.venv`/`PYTHONPATH`), not an objective defect. No artificial failure
  or production change was introduced.
- Final combined Python gate: 223 passed, 2 skipped. It emitted only the
  existing FastAPI/Starlette TestClient deprecation warning.
- Package/schema validators were valid with zero issues, errors, or warnings.
  Node gates passed 14, 89, 19, and 24 tests; the Vite build transformed 1,521
  modules; `git diff --check` passed.
- The Grand Sport and Z06 Node generator gates refreshed only tracked
  `generated_at` timestamps. Those exact two files were restored from `HEAD`;
  workbook, registry, and tracked `form-output` hashes then matched their
  pre-implementation values.
- Read-only temporary FastAPI verification and Playwright desktop/mobile
  verification passed. No UI import, edit, commit, sync, export, backup, live
  workbook write, or dealer submission was triggered. Screenshots remain only
  under `/private/tmp`.
- Final integrated review hardening added transaction-time optimistic
  concurrency for staged update/delete batches, persisted the approved
  schema-mapping status/source-role/transform evidence, typed malformed-source
  import failures, retained lineage for empty model roles, removed the final
  legacy structure route, and typed the dependencies endpoint. A guarded
  scratch import/dry-sync/live-sync proof passed without touching the canonical
  workbook or generated/dealer surfaces.
- Final compatibility review additionally typed corrupt OOXML XML parsing,
  fail-closed prior canonical databases with an actionable re-import gate, and
  verified successful versus failed atomic re-import behavior. The focused API
  and import regressions passed, the frontend contract gate increased to 14,
  and the production build still transformed 1,521 modules.
- The design spec and workbook-manager README are closed with exact commands,
  results, preserved boundaries, residual fail-closed limitation, and no stale
  approval prompt. Follow-up: none implied.

---

## Final Requirement Matrix

| Requirement | Proving task/evidence |
|---|---|
| `option_id` is each model options PK | Tasks 1 and 11 schema introspection |
| Three live models | Tasks 2, 4, and 11 active/promotion discovery |
| Unique but identical model table collections | Tasks 1, 4, 5, and 11 role equality |
| Explicit model/table ownership | Tasks 1 and 9 registry/check/FK/API evidence |
| Variants linked to models/body styles/trims | Task 3 central FKs and Task 11 FK check |
| Runtime/sections use one connected route | Task 3 compiler tests and Task 9 runtime API |
| Workbook congruency is verifiable | Tasks 2, 5, 6, and 7 catalog/mapping/lineage/round trip |
| Workbook inadequacies are hardened and marked | Tasks 4, 5, 6, and 9 typed aliases/findings API |
| Generation contract mismatches are marked | Task 7 exact path diff and Task 9 findings |
| Business decisions stop work | Tasks 4-6 fail-closed tests and Task 9 HTTP 409 |
| FastAPI serves and edits relational data | Tasks 8-10 API/staging/UI tests |
| Workbook writes remain safely gated | Task 8 scratch sync gate |
| Runtime/dealer/workbook preserved | Task 11 hashes, diffs, and no-live-write proof |
