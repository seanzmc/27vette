"""SQLite connection handling and canonical relational schema."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from .catalog import LIVE_MODELS, MODEL_TABLE_ROLES, physical_table
from .specs import TABLE_SPECS, TableSpec


def connect(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    if conn.execute("PRAGMA foreign_keys").fetchone()[0] != 1:
        conn.close()
        raise RuntimeError("SQLite foreign key enforcement could not be enabled")
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


CENTRAL_DDL = (
    """CREATE TABLE models (
      model_key TEXT PRIMARY KEY,
      registry_key TEXT NOT NULL UNIQUE,
      model_label TEXT NOT NULL,
      model_year INTEGER,
      dataset_name TEXT,
      export_slug TEXT,
      expected_variant_count INTEGER,
      default_model INTEGER NOT NULL DEFAULT 0 CHECK(default_model IN (0, 1)),
      active INTEGER NOT NULL CHECK(active IN (0, 1)),
      notes TEXT NOT NULL DEFAULT ''
    )""",
    """CREATE TABLE model_registry_promotion (
      model_key TEXT PRIMARY KEY REFERENCES models(model_key),
      registry_key TEXT NOT NULL,
      promoted_to_runtime INTEGER NOT NULL CHECK(promoted_to_runtime IN (0, 1)),
      default_model INTEGER NOT NULL CHECK(default_model IN (0, 1)),
      artifact_path TEXT NOT NULL,
      artifact_type TEXT NOT NULL,
      legacy_alias TEXT NOT NULL DEFAULT '',
      active INTEGER NOT NULL CHECK(active IN (0, 1)),
      display_order INTEGER NOT NULL,
      notes TEXT NOT NULL DEFAULT ''
    )""",
    """CREATE TABLE model_table_registry (
      model_key TEXT NOT NULL REFERENCES models(model_key),
      table_role TEXT NOT NULL,
      sql_table TEXT NOT NULL UNIQUE,
      source_sheets_json TEXT NOT NULL DEFAULT '[]',
      source_filter TEXT NOT NULL DEFAULT '',
      mapping_type TEXT NOT NULL CHECK(mapping_type IN ('exact', 'split', 'derived')),
      active INTEGER NOT NULL CHECK(active IN (0, 1)),
      PRIMARY KEY(model_key, table_role)
    )""",
    """CREATE TABLE body_styles (
      body_style TEXT PRIMARY KEY
    )""",
    """CREATE TABLE trim_levels (
      trim_level TEXT PRIMARY KEY
    )""",
    """CREATE TABLE variants (
      variant_id TEXT PRIMARY KEY,
      model_year INTEGER NOT NULL,
      trim_level TEXT NOT NULL REFERENCES trim_levels(trim_level),
      body_style TEXT NOT NULL REFERENCES body_styles(body_style),
      display_name TEXT NOT NULL,
      base_price INTEGER NOT NULL,
      display_order INTEGER NOT NULL,
      active INTEGER NOT NULL CHECK(active IN (0, 1))
    )""",
    """CREATE TABLE model_variants (
      model_key TEXT NOT NULL REFERENCES models(model_key),
      variant_id TEXT NOT NULL REFERENCES variants(variant_id),
      display_order INTEGER NOT NULL,
      active INTEGER NOT NULL CHECK(active IN (0, 1)),
      notes TEXT NOT NULL DEFAULT '',
      PRIMARY KEY(model_key, variant_id)
    )""",
    """CREATE TABLE sections (
      section_id TEXT PRIMARY KEY,
      section_name TEXT NOT NULL,
      selection_mode TEXT,
      is_required INTEGER NOT NULL DEFAULT 0 CHECK(is_required IN (0, 1)),
      display_order INTEGER,
      standard_behavior TEXT,
      step_key TEXT
    )""",
    """CREATE TABLE section_presentation (
      model_key TEXT NOT NULL REFERENCES models(model_key),
      section_id TEXT NOT NULL REFERENCES sections(section_id),
      display_label TEXT NOT NULL,
      step_key TEXT NOT NULL,
      display_behavior TEXT,
      section_display_order INTEGER NOT NULL,
      standard_equipment_bucket TEXT NOT NULL DEFAULT '',
      standard_equipment_group_type TEXT NOT NULL DEFAULT '',
      auto_added_bucket TEXT NOT NULL DEFAULT '',
      active INTEGER NOT NULL CHECK(active IN (0, 1)),
      notes TEXT NOT NULL DEFAULT '',
      PRIMARY KEY(model_key, section_id)
    )""",
    """CREATE TABLE runtime_route_keys (
      model_key TEXT NOT NULL REFERENCES models(model_key),
      route_key TEXT NOT NULL,
      route_kind TEXT NOT NULL
        CHECK(route_kind IN ('visible_step', 'hidden_summary_bucket')),
      PRIMARY KEY(model_key, route_key)
    )""",
    """CREATE TABLE runtime_steps (
      model_key TEXT NOT NULL REFERENCES models(model_key),
      step_key TEXT NOT NULL,
      step_label TEXT NOT NULL,
      runtime_order INTEGER NOT NULL,
      source TEXT NOT NULL,
      active INTEGER NOT NULL CHECK(active IN (0, 1)),
      notes TEXT NOT NULL DEFAULT '',
      PRIMARY KEY(model_key, step_key),
      FOREIGN KEY(model_key, step_key)
        REFERENCES runtime_route_keys(model_key, route_key)
    )""",
    """CREATE TABLE runtime_context_sections (
      model_key TEXT NOT NULL REFERENCES models(model_key),
      context_type TEXT NOT NULL,
      section_id TEXT NOT NULL,
      section_name TEXT NOT NULL,
      selection_mode TEXT NOT NULL,
      choice_mode TEXT NOT NULL,
      is_required INTEGER NOT NULL CHECK(is_required IN (0, 1)),
      standard_behavior TEXT NOT NULL,
      section_display_order INTEGER NOT NULL,
      step_key TEXT NOT NULL,
      step_label TEXT NOT NULL,
      active INTEGER NOT NULL CHECK(active IN (0, 1)),
      notes TEXT NOT NULL DEFAULT '',
      PRIMARY KEY(model_key, context_type, section_id),
      FOREIGN KEY(model_key, step_key)
        REFERENCES runtime_route_keys(model_key, route_key)
    )""",
    """CREATE TABLE runtime_context_choices (
      model_key TEXT NOT NULL REFERENCES models(model_key),
      context_type TEXT NOT NULL,
      value TEXT NOT NULL,
      body_style TEXT REFERENCES body_styles(body_style),
      info_tooltip TEXT NOT NULL DEFAULT '',
      active INTEGER NOT NULL CHECK(active IN (0, 1)),
      notes TEXT NOT NULL DEFAULT '',
      PRIMARY KEY(model_key, context_type, value)
    )""",
    """CREATE TABLE runtime_summary_sections (
      model_key TEXT NOT NULL REFERENCES models(model_key),
      section_key TEXT NOT NULL,
      section_label TEXT NOT NULL,
      display_order INTEGER NOT NULL,
      active INTEGER NOT NULL CHECK(active IN (0, 1)),
      notes TEXT NOT NULL DEFAULT '',
      PRIMARY KEY(model_key, section_key)
    )""",
    """CREATE TABLE runtime_step_summary_map (
      model_key TEXT NOT NULL REFERENCES models(model_key),
      step_key TEXT NOT NULL,
      section_key TEXT NOT NULL,
      active INTEGER NOT NULL CHECK(active IN (0, 1)),
      notes TEXT NOT NULL DEFAULT '',
      PRIMARY KEY(model_key, step_key, section_key),
      FOREIGN KEY(model_key, step_key)
        REFERENCES runtime_route_keys(model_key, route_key),
      FOREIGN KEY(model_key, section_key)
        REFERENCES runtime_summary_sections(model_key, section_key)
    )""",
    """CREATE TABLE model_assets (
      model_key TEXT PRIMARY KEY REFERENCES models(model_key),
      image_url TEXT NOT NULL,
      image_alt TEXT NOT NULL DEFAULT '',
      image_fit TEXT NOT NULL DEFAULT '',
      image_position TEXT NOT NULL DEFAULT '',
      hover_image_url TEXT NOT NULL DEFAULT '',
      hover_image_alt TEXT NOT NULL DEFAULT '',
      hover_image_position TEXT NOT NULL DEFAULT '',
      active INTEGER NOT NULL CHECK(active IN (0, 1)),
      notes TEXT NOT NULL DEFAULT ''
    )""",
    """CREATE TABLE price_ref (
      price_ref_id INTEGER PRIMARY KEY AUTOINCREMENT,
      option_type TEXT NOT NULL
        CHECK(option_type <> '' AND option_type <> '<unrestricted>'),
      trim_level TEXT
        CHECK(trim_level IS NULL OR (
          trim_level <> '' AND trim_level <> '<unrestricted>'
        )),
      code TEXT NOT NULL CHECK(code <> '' AND code <> '<unrestricted>'),
      price INTEGER NOT NULL
    )""",
    """CREATE TABLE rule_phrase_map (
      phrase TEXT PRIMARY KEY,
      rule_type TEXT NOT NULL,
      direction TEXT NOT NULL,
      stop_phrases TEXT NOT NULL DEFAULT '',
      review_flag_default INTEGER NOT NULL CHECK(review_flag_default IN (0, 1)),
      active INTEGER NOT NULL CHECK(active IN (0, 1)),
      notes TEXT NOT NULL DEFAULT ''
    )""",
)


CANONICAL_SUPPORT_DDL = (
    """CREATE TABLE source_table_catalog (
      source_sheet TEXT PRIMARY KEY,
      disposition TEXT NOT NULL,
      destination_tables_json TEXT NOT NULL DEFAULT '[]',
      source_of_truth_class TEXT NOT NULL,
      row_count INTEGER NOT NULL,
      reason TEXT NOT NULL
    )""",
    """CREATE TABLE schema_mapping (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      source_sheet TEXT NOT NULL,
      source_column TEXT NOT NULL,
      model_key TEXT REFERENCES models(model_key),
      source_role TEXT NOT NULL DEFAULT '',
      sql_table TEXT NOT NULL,
      sql_column TEXT NOT NULL,
      transform_type TEXT NOT NULL,
      transform_parameters_json TEXT NOT NULL DEFAULT '{}',
      contract_status TEXT NOT NULL,
      notes TEXT NOT NULL DEFAULT '',
      UNIQUE(source_sheet, source_column, model_key, sql_table, sql_column)
    )""",
    """CREATE TABLE import_runs (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      ts TEXT NOT NULL,
      workbook_path TEXT NOT NULL,
      workbook_mtime_ns TEXT NOT NULL,
      workbook_sha256 TEXT NOT NULL,
      status TEXT NOT NULL,
      row_counts_json TEXT NOT NULL DEFAULT '{}',
      issue_counts_json TEXT NOT NULL DEFAULT '{}'
    )""",
    """CREATE TABLE import_lineage (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      import_run_id INTEGER NOT NULL REFERENCES import_runs(id),
      sql_table TEXT NOT NULL,
      primary_key_json TEXT NOT NULL,
      source_sheet TEXT NOT NULL,
      source_row INTEGER NOT NULL,
      source_row_hash TEXT NOT NULL,
      lineage_role TEXT NOT NULL,
      transform_status TEXT NOT NULL
    )""",
    """CREATE TABLE import_issues (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      run_id INTEGER NOT NULL REFERENCES import_runs(id),
      severity TEXT NOT NULL,
      category TEXT NOT NULL,
      sheet TEXT NOT NULL DEFAULT '',
      src_row INTEGER,
      table_name TEXT NOT NULL DEFAULT '',
      model_id TEXT NOT NULL DEFAULT '',
      entity_key TEXT NOT NULL DEFAULT '',
      field TEXT NOT NULL DEFAULT '',
      message TEXT NOT NULL
    )""",
    """CREATE TABLE raw_sheet_rows (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      sheet TEXT NOT NULL,
      src_row INTEGER NOT NULL,
      data_json TEXT NOT NULL,
      UNIQUE(sheet, src_row)
    )""",
    """CREATE TABLE pending_changes (
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
    )""",
    """CREATE TABLE change_history (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      ts TEXT NOT NULL,
      actor TEXT NOT NULL DEFAULT '',
      entity_type TEXT NOT NULL,
      entity_id TEXT NOT NULL,
      model_id TEXT NOT NULL DEFAULT '',
      op TEXT NOT NULL,
      old_json TEXT,
      new_json TEXT,
      src_sheet TEXT NOT NULL DEFAULT '',
      src_row INTEGER,
      validation_result TEXT NOT NULL DEFAULT '',
      status TEXT NOT NULL,
      sync_status TEXT NOT NULL DEFAULT 'pending',
      sync_detail TEXT NOT NULL DEFAULT '',
      pending_change_id INTEGER REFERENCES pending_changes(id)
    )""",
    """CREATE TABLE meta (
      key TEXT PRIMARY KEY,
      value TEXT NOT NULL
    )""",
)


def _model_key_column(model_key: str) -> str:
    return (
        "model_key TEXT NOT NULL REFERENCES models(model_key) "
        f"CHECK(model_key = '{model_key}')"
    )


def _quote_identifier(identifier: str) -> str:
    return '"' + identifier.replace('"', '""') + '"'


def _quoted_physical_table(model_key: str, role: str) -> str:
    return _quote_identifier(physical_table(model_key, role))


def _model_table_ddl(model_key: str, role: str) -> str:
    table = _quoted_physical_table(model_key, role)
    model_column = _model_key_column(model_key)
    options = _quoted_physical_table(model_key, "options")
    interiors = _quoted_physical_table(model_key, "interiors")
    groups = _quoted_physical_table(model_key, "rule_groups")
    exclusive_groups = _quoted_physical_table(model_key, "exclusive_groups")

    bodies = {
        "options": f"""{model_column},
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
          display_behavior TEXT""",
        "option_availability": f"""{model_column},
          option_id TEXT NOT NULL REFERENCES {options}(option_id),
          variant_id TEXT NOT NULL,
          status TEXT NOT NULL,
          PRIMARY KEY(option_id, variant_id),
          FOREIGN KEY(model_key, variant_id)
            REFERENCES model_variants(model_key, variant_id)""",
        "rule_mapping": f"""{model_column},
          rule_id TEXT PRIMARY KEY,
          source_option_id TEXT REFERENCES {options}(option_id),
          source_interior_id TEXT REFERENCES {interiors}(interior_id),
          rule_type TEXT NOT NULL,
          target_option_id TEXT NOT NULL REFERENCES {options}(option_id),
          original_detail_raw TEXT NOT NULL DEFAULT '',
          body_style_scope TEXT REFERENCES body_styles(body_style),
          trim_level_scope TEXT REFERENCES trim_levels(trim_level),
          variant_scope TEXT,
          runtime_action TEXT,
          disabled_reason TEXT NOT NULL DEFAULT '',
          CHECK((source_option_id IS NOT NULL) != (source_interior_id IS NOT NULL)),
          FOREIGN KEY(model_key, variant_scope)
            REFERENCES model_variants(model_key, variant_id)""",
        "price_rules": f"""{model_column},
          price_rule_id TEXT PRIMARY KEY,
          condition_option_id TEXT REFERENCES {options}(option_id),
          condition_interior_id TEXT REFERENCES {interiors}(interior_id),
          price_rule_type TEXT NOT NULL,
          target_option_id TEXT NOT NULL REFERENCES {options}(option_id),
          price_value INTEGER NOT NULL,
          body_style_scope TEXT REFERENCES body_styles(body_style),
          trim_level_scope TEXT REFERENCES trim_levels(trim_level),
          variant_scope TEXT,
          notes TEXT NOT NULL DEFAULT '',
          CHECK((condition_option_id IS NOT NULL) != (condition_interior_id IS NOT NULL)),
          FOREIGN KEY(model_key, variant_scope)
            REFERENCES model_variants(model_key, variant_id)""",
        "rule_groups": f"""{model_column},
          group_id TEXT PRIMARY KEY,
          group_type TEXT NOT NULL,
          source_option_id TEXT NOT NULL REFERENCES {options}(option_id),
          body_style_scope TEXT REFERENCES body_styles(body_style),
          trim_level_scope TEXT REFERENCES trim_levels(trim_level),
          variant_scope TEXT,
          disabled_reason TEXT NOT NULL DEFAULT '',
          active INTEGER NOT NULL CHECK(active IN (0, 1)),
          notes TEXT NOT NULL DEFAULT '',
          FOREIGN KEY(model_key, variant_scope)
            REFERENCES model_variants(model_key, variant_id)""",
        "rule_group_members": f"""{model_column},
          group_id TEXT NOT NULL REFERENCES {groups}(group_id),
          target_option_id TEXT NOT NULL REFERENCES {options}(option_id),
          display_order INTEGER NOT NULL,
          active INTEGER NOT NULL CHECK(active IN (0, 1)),
          PRIMARY KEY(group_id, target_option_id)""",
        "exclusive_groups": f"""{model_column},
          group_id TEXT PRIMARY KEY,
          selection_mode TEXT NOT NULL,
          active INTEGER NOT NULL CHECK(active IN (0, 1)),
          notes TEXT NOT NULL DEFAULT ''""",
        "exclusive_group_members": f"""{model_column},
          group_id TEXT NOT NULL REFERENCES {exclusive_groups}(group_id),
          option_id TEXT NOT NULL REFERENCES {options}(option_id),
          display_order INTEGER NOT NULL,
          active INTEGER NOT NULL CHECK(active IN (0, 1)),
          PRIMARY KEY(group_id, option_id)""",
        "variant_overrides": f"""{model_column},
          option_id TEXT NOT NULL REFERENCES {options}(option_id),
          variant_id TEXT NOT NULL,
          selectable INTEGER CHECK(selectable IN (0, 1)),
          display_behavior TEXT,
          section_id TEXT REFERENCES sections(section_id),
          active INTEGER NOT NULL CHECK(active IN (0, 1)),
          note TEXT NOT NULL DEFAULT '',
          PRIMARY KEY(option_id, variant_id),
          FOREIGN KEY(model_key, variant_id)
            REFERENCES model_variants(model_key, variant_id)""",
        "interiors": f"""{model_column},
          interior_id TEXT PRIMARY KEY,
          interior_name TEXT NOT NULL,
          material TEXT NOT NULL DEFAULT '',
          price INTEGER NOT NULL,
          detail_from_disclosure TEXT NOT NULL DEFAULT '',
          color_overrides TEXT NOT NULL DEFAULT '',
          trim TEXT NOT NULL DEFAULT '',
          seat TEXT NOT NULL DEFAULT '',
          interior_code TEXT NOT NULL DEFAULT '',
          suede TEXT NOT NULL DEFAULT '',
          stitch TEXT NOT NULL DEFAULT '',
          two_tone TEXT NOT NULL DEFAULT '',
          section_id TEXT NOT NULL REFERENCES sections(section_id),
          requires_r6x INTEGER NOT NULL DEFAULT 0 CHECK(requires_r6x IN (0, 1)),
          included_option_id TEXT REFERENCES {options}(option_id),
          active INTEGER NOT NULL CHECK(active IN (0, 1))""",
        "interior_scope": f"""{model_column},
          interior_id TEXT NOT NULL REFERENCES {interiors}(interior_id),
          trim_level TEXT REFERENCES trim_levels(trim_level),
          body_style TEXT REFERENCES body_styles(body_style),
          variant_id TEXT,
          active INTEGER NOT NULL CHECK(active IN (0, 1)),
          requires_option_id TEXT REFERENCES {options}(option_id),
          notes TEXT NOT NULL DEFAULT '',
          interior_seat_label TEXT NOT NULL DEFAULT '',
          interior_color_family TEXT NOT NULL DEFAULT '',
          interior_material_family TEXT NOT NULL DEFAULT '',
          interior_variant_label TEXT NOT NULL DEFAULT '',
          interior_group_display_order INTEGER,
          interior_material_display_order INTEGER,
          interior_choice_display_order INTEGER,
          interior_hierarchy_levels TEXT NOT NULL DEFAULT '',
          interior_parent_group_label TEXT NOT NULL DEFAULT '',
          interior_leaf_label TEXT NOT NULL DEFAULT '',
          interior_reference_order INTEGER,
          grouping_source TEXT NOT NULL DEFAULT '',
          FOREIGN KEY(model_key, variant_id)
            REFERENCES model_variants(model_key, variant_id)""",
        "interior_components": f"""{model_column},
          interior_id TEXT NOT NULL REFERENCES {interiors}(interior_id),
          rpo TEXT NOT NULL,
          component_type TEXT NOT NULL,
          label TEXT NOT NULL,
          price_ref_type TEXT NOT NULL DEFAULT '',
          price_ref_code TEXT NOT NULL DEFAULT '',
          price_trim_scope TEXT NOT NULL DEFAULT '',
          display_order INTEGER NOT NULL,
          active INTEGER NOT NULL CHECK(active IN (0, 1)),
          notes TEXT NOT NULL DEFAULT '',
          PRIMARY KEY(interior_id, rpo, component_type)""",
        "color_overrides": f"""{model_column},
          interior_id TEXT NOT NULL REFERENCES {interiors}(interior_id),
          option_id TEXT NOT NULL REFERENCES {options}(option_id),
          rule_type TEXT NOT NULL,
          added_option_id TEXT NOT NULL REFERENCES {options}(option_id),
          PRIMARY KEY(interior_id, option_id)""",
        "option_assets": f"""{model_column},
          option_id TEXT PRIMARY KEY REFERENCES {options}(option_id),
          image_url TEXT NOT NULL,
          image_alt TEXT NOT NULL DEFAULT '',
          image_fit TEXT NOT NULL DEFAULT '',
          image_position TEXT NOT NULL DEFAULT '',
          hover_image_url TEXT NOT NULL DEFAULT '',
          hover_image_alt TEXT NOT NULL DEFAULT '',
          hover_image_position TEXT NOT NULL DEFAULT '',
          active INTEGER NOT NULL CHECK(active IN (0, 1)),
          notes TEXT NOT NULL DEFAULT ''""",
        "context_choice_assets": f"""{model_column},
          context_type TEXT NOT NULL,
          choice_value TEXT NOT NULL,
          image_url TEXT NOT NULL,
          image_alt TEXT NOT NULL DEFAULT '',
          image_fit TEXT NOT NULL DEFAULT '',
          image_position TEXT NOT NULL DEFAULT '',
          hover_image_url TEXT NOT NULL DEFAULT '',
          hover_image_alt TEXT NOT NULL DEFAULT '',
          hover_image_position TEXT NOT NULL DEFAULT '',
          active INTEGER NOT NULL CHECK(active IN (0, 1)),
          notes TEXT NOT NULL DEFAULT '',
          PRIMARY KEY(context_type, choice_value),
          FOREIGN KEY(model_key, context_type, choice_value)
            REFERENCES runtime_context_choices(model_key, context_type, value)""",
        "default_selection_rules": f"""{model_column},
          rule_id TEXT PRIMARY KEY,
          target_option_id TEXT NOT NULL REFERENCES {options}(option_id),
          condition_type TEXT NOT NULL,
          condition_id TEXT,
          body_style_scope TEXT REFERENCES body_styles(body_style),
          trim_level_scope TEXT REFERENCES trim_levels(trim_level),
          variant_scope TEXT,
          priority INTEGER NOT NULL,
          active INTEGER NOT NULL CHECK(active IN (0, 1)),
          notes TEXT NOT NULL DEFAULT '',
          display_behavior TEXT,
          FOREIGN KEY(model_key, variant_scope)
            REFERENCES model_variants(model_key, variant_id)""",
        "runtime_rule_exceptions": f"""{model_column},
          exception_id TEXT PRIMARY KEY,
          source_option_id TEXT NOT NULL REFERENCES {options}(option_id),
          target_option_id TEXT NOT NULL REFERENCES {options}(option_id),
          exception_type TEXT NOT NULL,
          body_style_scope TEXT REFERENCES body_styles(body_style),
          trim_level_scope TEXT REFERENCES trim_levels(trim_level),
          variant_scope TEXT,
          disabled_reason TEXT NOT NULL DEFAULT '',
          active INTEGER NOT NULL CHECK(active IN (0, 1)),
          notes TEXT NOT NULL DEFAULT '',
          FOREIGN KEY(model_key, variant_scope)
            REFERENCES model_variants(model_key, variant_id)""",
    }
    return f"CREATE TABLE {table} (\n  {bodies[role]}\n)"


def create_canonical_schema(conn: sqlite3.Connection) -> None:
    """Create the central, support, and identical per-model table families."""
    if conn.execute("PRAGMA foreign_keys").fetchone()[0] != 1:
        raise RuntimeError("canonical schema requires PRAGMA foreign_keys=ON")
    with conn:
        for ddl in CENTRAL_DDL:
            conn.execute(ddl)
        conn.execute(
            "CREATE UNIQUE INDEX price_ref_null_safe_identity_unique "
            "ON price_ref("
            "option_type, COALESCE(trim_level, '<unrestricted>'), code"
            ")"
        )
        for model_key in LIVE_MODELS:
            # Interiors must exist before rules with typed interior references.
            ordered_roles = ("options", "interiors") + tuple(
                role
                for role in MODEL_TABLE_ROLES
                if role not in {"options", "interiors"}
            )
            for role in ordered_roles:
                conn.execute(_model_table_ddl(model_key, role))
            scope_table_name = physical_table(model_key, "interior_scope")
            scope_table = _quote_identifier(scope_table_name)
            scope_index = _quote_identifier(
                f"{scope_table_name}_null_safe_scope_unique"
            )
            conn.execute(
                f"CREATE UNIQUE INDEX {scope_index} ON {scope_table} ("
                "interior_id, COALESCE(trim_level, ''), "
                "COALESCE(body_style, ''), COALESCE(variant_id, '')"
                ")"
            )
        for ddl in CANONICAL_SUPPORT_DDL:
            conn.execute(ddl)
        conn.execute(
            "CREATE INDEX idx_import_lineage_source "
            "ON import_lineage(source_sheet, source_row)"
        )
        conn.execute(
            "CREATE INDEX idx_import_issues_run ON import_issues(run_id)"
        )
        conn.execute(
            "CREATE INDEX idx_history_entity "
            "ON change_history(entity_type, entity_id)"
        )


def _table_ddl(spec: TableSpec) -> str:
    cols = ["id INTEGER PRIMARY KEY AUTOINCREMENT"]
    if spec.model_scoped:
        cols.append("model_id TEXT NOT NULL")
    for c in spec.columns:
        cols.append(f'"{c.sql_name()}" TEXT NOT NULL DEFAULT \'\'')
    cols.append("src_sheet TEXT NOT NULL DEFAULT ''")
    cols.append("src_row INTEGER")
    key_cols = list(spec.key)
    if spec.model_scoped:
        key_cols = ["model_id", *key_cols]
    quoted = ", ".join(f'"{k}"' for k in key_cols)
    cols.append(f"UNIQUE({quoted})")
    for ref in spec.refs:
        if ref.scope == "global":
            cols.append(
                f'FOREIGN KEY("{ref.column}") REFERENCES '
                f'{ref.target_table}("{ref.target_column}")'
            )
    body = ",\n  ".join(cols)
    return f"CREATE TABLE IF NOT EXISTS {spec.table} (\n  {body}\n)"


SUPPORT_DDL = [
    """CREATE TABLE IF NOT EXISTS raw_sheet_rows (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      sheet TEXT NOT NULL,
      src_row INTEGER NOT NULL,
      data_json TEXT NOT NULL,
      UNIQUE(sheet, src_row)
    )""",
    """CREATE TABLE IF NOT EXISTS import_runs (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      ts TEXT NOT NULL,
      workbook_path TEXT NOT NULL,
      workbook_mtime_ns TEXT NOT NULL,
      workbook_sha256 TEXT NOT NULL,
      status TEXT NOT NULL,
      row_counts_json TEXT NOT NULL DEFAULT '{}',
      issue_counts_json TEXT NOT NULL DEFAULT '{}'
    )""",
    """CREATE TABLE IF NOT EXISTS import_issues (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      run_id INTEGER NOT NULL REFERENCES import_runs(id),
      severity TEXT NOT NULL,          -- error | warning
      category TEXT NOT NULL,          -- duplicate_id | unresolved_ref | ...
      sheet TEXT NOT NULL DEFAULT '',
      src_row INTEGER,
      table_name TEXT NOT NULL DEFAULT '',
      model_id TEXT NOT NULL DEFAULT '',
      entity_key TEXT NOT NULL DEFAULT '',
      field TEXT NOT NULL DEFAULT '',
      message TEXT NOT NULL
    )""",
    """CREATE TABLE IF NOT EXISTS pending_changes (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      ts TEXT NOT NULL,
      session_id TEXT NOT NULL DEFAULT '',
      table_name TEXT NOT NULL,
      model_id TEXT NOT NULL DEFAULT '',
      entity_key_json TEXT NOT NULL,
      op TEXT NOT NULL,                -- add | update | delete
      old_json TEXT,
      new_json TEXT,
      status TEXT NOT NULL DEFAULT 'staged',  -- staged | committed | discarded
      validation_json TEXT NOT NULL DEFAULT '{}',
      confirmed_dependencies INTEGER NOT NULL DEFAULT 0
    )""",
    """CREATE TABLE IF NOT EXISTS change_history (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      ts TEXT NOT NULL,
      actor TEXT NOT NULL DEFAULT '',
      entity_type TEXT NOT NULL,
      entity_id TEXT NOT NULL,
      model_id TEXT NOT NULL DEFAULT '',
      op TEXT NOT NULL,
      old_json TEXT,
      new_json TEXT,
      src_sheet TEXT NOT NULL DEFAULT '',
      src_row INTEGER,
      validation_result TEXT NOT NULL DEFAULT '',
      status TEXT NOT NULL,            -- committed | rolled_back
      sync_status TEXT NOT NULL DEFAULT 'pending',  -- pending | synced | sync_failed | n/a
      sync_detail TEXT NOT NULL DEFAULT '',
      pending_change_id INTEGER
    )""",
    """CREATE TABLE IF NOT EXISTS meta (
      key TEXT PRIMARY KEY,
      value TEXT NOT NULL
    )""",
]


def init_schema(conn: sqlite3.Connection) -> None:
    for spec in TABLE_SPECS:
        conn.execute(_table_ddl(spec))
    for ddl in SUPPORT_DDL:
        conn.execute(ddl)
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_history_entity "
        "ON change_history(entity_type, entity_id)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_issues_run ON import_issues(run_id)"
    )
    conn.commit()


def clear_imported_data(conn: sqlite3.Connection) -> None:
    """Remove imported rows (not staged changes / history) before re-import."""
    for spec in TABLE_SPECS:
        conn.execute(f"DELETE FROM {spec.table}")
    conn.execute("DELETE FROM raw_sheet_rows")
    conn.commit()


def get_meta(conn: sqlite3.Connection, key: str, default: str = "") -> str:
    row = conn.execute("SELECT value FROM meta WHERE key=?", (key,)).fetchone()
    return row["value"] if row else default


def set_meta(conn: sqlite3.Connection, key: str, value: str) -> None:
    conn.execute(
        "INSERT INTO meta(key, value) VALUES(?, ?) "
        "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
        (key, value),
    )
