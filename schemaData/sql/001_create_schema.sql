BEGIN;

CREATE TABLE datasets (
  dataset_id text PRIMARY KEY,
  dataset_name text NOT NULL,
  model_family text NOT NULL,
  schema_version text NOT NULL,
  active boolean NOT NULL DEFAULT true
);

CREATE TABLE model_years (
  model_year integer PRIMARY KEY,
  active boolean NOT NULL DEFAULT true
);

CREATE TABLE models (
  model_key text PRIMARY KEY,
  model_name text NOT NULL,
  active boolean NOT NULL DEFAULT true
);

CREATE TABLE body_styles (
  body_style text PRIMARY KEY,
  body_style_label text NOT NULL,
  active boolean NOT NULL DEFAULT true
);

CREATE TABLE trims (
  trim_level text PRIMARY KEY,
  trim_label text NOT NULL,
  active boolean NOT NULL DEFAULT true
);

CREATE TABLE categories (
  category_id text PRIMARY KEY,
  category_name text NOT NULL,
  display_order integer NOT NULL,
  active boolean NOT NULL DEFAULT true
);

CREATE TABLE variants (
  variant_id text PRIMARY KEY,
  dataset_id text NOT NULL REFERENCES datasets (dataset_id),
  model_year integer NOT NULL REFERENCES model_years (model_year),
  model_key text NOT NULL REFERENCES models (model_key),
  body_style text NOT NULL REFERENCES body_styles (body_style),
  trim_level text NOT NULL REFERENCES trims (trim_level),
  display_name text NOT NULL,
  active boolean NOT NULL DEFAULT true
);

COMMENT ON TABLE variants IS 'One row per concrete build context. Broad authoring is handled by variant_scopes and resolved through scope_variants.';

CREATE TABLE variant_scopes (
  scope_id text PRIMARY KEY,
  scope_name text NOT NULL,
  dataset_id text REFERENCES datasets (dataset_id),
  year_min integer REFERENCES model_years (model_year),
  year_max integer REFERENCES model_years (model_year),
  model_key text REFERENCES models (model_key),
  body_style text REFERENCES body_styles (body_style),
  trim_level text REFERENCES trims (trim_level),
  active boolean NOT NULL DEFAULT true,
  CHECK (year_min IS NULL OR year_max IS NULL OR year_min <= year_max)
);

COMMENT ON TABLE variant_scopes IS 'Human-editable broad variant scopes. Null scope attributes are wildcards.';

CREATE TABLE scope_variants (
  scope_variant_key text PRIMARY KEY,
  scope_id text NOT NULL REFERENCES variant_scopes (scope_id),
  variant_id text NOT NULL REFERENCES variants (variant_id),
  UNIQUE (scope_id, variant_id)
);

COMMENT ON TABLE scope_variants IS 'Derived expansion of variant_scopes into concrete variant_id rows.';

CREATE TABLE options (
  option_id text PRIMARY KEY,
  rpo_code text NOT NULL,
  option_label text NOT NULL,
  option_description text,
  option_type text NOT NULL,
  option_family text,
  active boolean NOT NULL DEFAULT true
);

COMMENT ON TABLE options IS 'One row per canonical option. RPO code is a property, not the primary key.';

CREATE TABLE option_versions (
  option_version_id text PRIMARY KEY,
  option_id text NOT NULL REFERENCES options (option_id),
  rpo_code text NOT NULL,
  model_year integer REFERENCES model_years (model_year),
  model_key text REFERENCES models (model_key),
  option_label text NOT NULL,
  option_description text,
  active boolean NOT NULL DEFAULT true
);

COMMENT ON TABLE option_versions IS 'Optional RPO/version handling for year- or model-specific option definitions.';

CREATE TABLE steps (
  step_id text PRIMARY KEY,
  dataset_id text NOT NULL REFERENCES datasets (dataset_id),
  step_key text NOT NULL,
  step_label text NOT NULL,
  display_order integer NOT NULL,
  active boolean NOT NULL DEFAULT true,
  UNIQUE (dataset_id, step_key)
);

CREATE TABLE sections (
  section_id text PRIMARY KEY,
  step_id text NOT NULL REFERENCES steps (step_id),
  category_id text NOT NULL REFERENCES categories (category_id),
  section_label text NOT NULL,
  display_order integer NOT NULL,
  active boolean NOT NULL DEFAULT true
);

CREATE TABLE choice_groups (
  group_id text PRIMARY KEY,
  section_id text NOT NULL REFERENCES sections (section_id),
  group_label text NOT NULL,
  selection_mode text NOT NULL CHECK (selection_mode IN ('single', 'multi', 'display_only')),
  required boolean NOT NULL,
  min_select integer NOT NULL DEFAULT 0,
  max_select integer,
  display_order integer NOT NULL,
  active boolean NOT NULL DEFAULT true,
  CHECK (min_select >= 0),
  CHECK (max_select IS NULL OR max_select >= min_select)
);

COMMENT ON TABLE choice_groups IS 'Normalized choice groups. Section, category, and step display values are resolved through joins.';

CREATE TABLE choice_group_options (
  group_option_key text PRIMARY KEY,
  group_id text NOT NULL REFERENCES choice_groups (group_id),
  option_id text NOT NULL REFERENCES options (option_id),
  display_order integer NOT NULL,
  active boolean NOT NULL DEFAULT true,
  UNIQUE (group_id, option_id)
);

CREATE TABLE option_availability (
  availability_id text PRIMARY KEY,
  scope_id text REFERENCES variant_scopes (scope_id),
  variant_id text REFERENCES variants (variant_id),
  option_id text NOT NULL REFERENCES options (option_id),
  status text NOT NULL CHECK (status IN ('optional', 'unavailable', 'standard_choice', 'standard_fixed', 'included', 'requires_selection')),
  base_price numeric(12, 2),
  default_flag boolean NOT NULL DEFAULT false,
  locked_flag boolean NOT NULL DEFAULT false,
  notes text,
  active boolean NOT NULL DEFAULT true,
  CHECK (num_nonnulls(scope_id, variant_id) = 1),
  CHECK (status <> 'optional' OR base_price IS NOT NULL)
);

COMMENT ON TABLE option_availability IS 'Editable scope-aware availability authoring. Exact variant_id rows override broad scope_id rows during resolution.';

CREATE TABLE option_status_resolved (
  variant_option_key text PRIMARY KEY,
  variant_id text NOT NULL REFERENCES variants (variant_id),
  option_id text NOT NULL REFERENCES options (option_id),
  resolved_status text NOT NULL CHECK (resolved_status IN ('optional', 'unavailable', 'standard_choice', 'standard_fixed', 'included', 'requires_selection')),
  resolved_price numeric(12, 2) NOT NULL DEFAULT 0,
  default_flag boolean NOT NULL DEFAULT false,
  locked_flag boolean NOT NULL DEFAULT false,
  source_availability_id text REFERENCES option_availability (availability_id),
  active boolean NOT NULL DEFAULT true,
  UNIQUE (variant_id, option_id)
);

COMMENT ON TABLE option_status_resolved IS 'Resolved concrete availability spine consumed by app-facing views.';

CREATE TABLE rules (
  rule_id text PRIMARY KEY,
  rule_name text NOT NULL,
  rule_type text NOT NULL CHECK (rule_type IN ('requires', 'requires_any', 'excludes', 'includes', 'price_override', 'price_adjustment', 'default_override')),
  scope_id text REFERENCES variant_scopes (scope_id),
  variant_id text REFERENCES variants (variant_id),
  priority integer NOT NULL DEFAULT 100,
  message text,
  active boolean NOT NULL DEFAULT true,
  CHECK (num_nonnulls(scope_id, variant_id) <= 1)
);

CREATE TABLE rule_conditions (
  rule_condition_id text PRIMARY KEY,
  rule_id text NOT NULL REFERENCES rules (rule_id),
  condition_group integer NOT NULL,
  condition_order integer NOT NULL,
  source_option_id text REFERENCES options (option_id),
  source_group_id text REFERENCES choice_groups (group_id),
  source_variant_id text REFERENCES variants (variant_id),
  operator text NOT NULL CHECK (operator IN ('is_selected', 'is_not_selected', 'is_available', 'is_unavailable', 'is_in_group')),
  expected_value text,
  active boolean NOT NULL DEFAULT true,
  CHECK (num_nonnulls(source_option_id, source_group_id, source_variant_id) = 1)
);

CREATE TABLE rule_actions (
  rule_action_id text PRIMARY KEY,
  rule_id text NOT NULL REFERENCES rules (rule_id),
  action_type text NOT NULL CHECK (action_type IN ('requires', 'requires_any', 'excludes', 'includes', 'price_override', 'price_adjustment', 'default_override')),
  target_option_id text REFERENCES options (option_id),
  target_group_id text REFERENCES choice_groups (group_id),
  target_variant_id text REFERENCES variants (variant_id),
  price_mode text CHECK (price_mode IN ('set_price', 'add_amount', 'credit', 'included_no_charge')),
  rule_action_value numeric(12, 2),
  currency text,
  active boolean NOT NULL DEFAULT true,
  CHECK (num_nonnulls(target_option_id, target_group_id, target_variant_id) = 1),
  CHECK (
    action_type NOT IN ('price_override', 'price_adjustment')
    OR (price_mode IS NOT NULL AND rule_action_value IS NOT NULL)
  )
);

CREATE TABLE rule_members (
  rule_member_id text PRIMARY KEY,
  rule_id text NOT NULL REFERENCES rules (rule_id),
  member_option_id text REFERENCES options (option_id),
  member_group_id text REFERENCES choice_groups (group_id),
  display_order integer NOT NULL,
  active boolean NOT NULL DEFAULT true,
  CHECK (num_nonnulls(member_option_id, member_group_id) = 1)
);

CREATE TABLE packages (
  package_id text PRIMARY KEY,
  package_option_id text NOT NULL REFERENCES options (option_id),
  package_label text NOT NULL,
  active boolean NOT NULL DEFAULT true
);

CREATE TABLE package_members (
  package_member_id text PRIMARY KEY,
  package_id text NOT NULL REFERENCES packages (package_id),
  member_option_id text NOT NULL REFERENCES options (option_id),
  member_status text NOT NULL CHECK (member_status IN ('included', 'required', 'discounted', 'credit', 'forced')),
  member_price_mode text CHECK (member_price_mode IN ('set_price', 'add_amount', 'credit', 'included_no_charge')),
  member_price_value numeric(12, 2),
  required boolean NOT NULL DEFAULT false,
  locked boolean NOT NULL DEFAULT false,
  active boolean NOT NULL DEFAULT true,
  UNIQUE (package_id, member_option_id)
);

CREATE TABLE package_validation (
  package_validation_id text PRIMARY KEY,
  package_id text NOT NULL REFERENCES packages (package_id),
  variant_id text REFERENCES variants (variant_id),
  validation_status text NOT NULL,
  message text,
  active boolean NOT NULL DEFAULT true
);

CREATE TABLE source_rows (
  source_row_id text PRIMARY KEY,
  dataset_id text REFERENCES datasets (dataset_id),
  variant_id text REFERENCES variants (variant_id),
  raw_section text,
  raw_rpo text,
  raw_label text,
  raw_description text,
  raw_status text,
  raw_price text,
  raw_notes text,
  row_hash text NOT NULL,
  classification text,
  active boolean NOT NULL DEFAULT true
);

COMMENT ON TABLE source_rows IS 'Raw import and staging evidence. The app must not consume source_rows.';

CREATE TABLE _manifest (
  sheet_name text PRIMARY KEY,
  primary_key_column text NOT NULL,
  named_range text,
  description text NOT NULL,
  source_type text NOT NULL,
  editable boolean NOT NULL,
  published boolean NOT NULL
);

CREATE TABLE _integrity (
  check_id text PRIMARY KEY,
  check_name text NOT NULL,
  severity text NOT NULL CHECK (severity IN ('info', 'warning', 'error', 'critical')),
  error_count integer NOT NULL DEFAULT 0,
  publish_blocker boolean NOT NULL DEFAULT false,
  notes text
);

CREATE TABLE _validation_lists (
  list_name text NOT NULL,
  value text NOT NULL,
  display_order integer NOT NULL,
  active boolean NOT NULL DEFAULT true,
  PRIMARY KEY (list_name, value)
);

CREATE TABLE variant_group_validation (
  variant_id text NOT NULL REFERENCES variants (variant_id),
  group_id text NOT NULL REFERENCES choice_groups (group_id),
  available_option_count integer NOT NULL DEFAULT 0,
  default_option_count integer NOT NULL DEFAULT 0,
  standard_fixed_count integer NOT NULL DEFAULT 0,
  required boolean NOT NULL,
  selection_mode text NOT NULL,
  validation_status text NOT NULL,
  PRIMARY KEY (variant_id, group_id)
);

CREATE TABLE _releases (
  release_id text PRIMARY KEY,
  schema_version text NOT NULL,
  data_version text NOT NULL,
  status text NOT NULL CHECK (status IN ('draft', 'validated', 'published', 'archived', 'rolled_back')),
  created_at timestamptz NOT NULL,
  published_at timestamptz,
  published_by text,
  checksum text,
  rollback_to_release_id text REFERENCES _releases (release_id),
  notes text
);

CREATE VIEW app_variants AS
SELECT
  variant_id,
  display_name,
  model_year,
  model_key,
  body_style,
  trim_level,
  active
FROM variants
WHERE active = true;

CREATE VIEW app_ui_render AS
SELECT
  st.dataset_id,
  v.variant_id,
  st.step_id,
  st.step_label,
  st.display_order AS step_order,
  se.section_id,
  se.section_label,
  se.display_order AS section_order,
  cg.group_id,
  cg.group_label,
  cg.display_order AS group_order,
  cg.selection_mode,
  cg.required,
  cg.min_select,
  cg.max_select,
  o.option_id,
  o.rpo_code,
  o.option_label,
  o.option_description,
  osr.resolved_status AS status,
  osr.resolved_price AS price,
  osr.default_flag,
  osr.locked_flag,
  cgo.display_order
FROM option_status_resolved osr
JOIN variants v ON v.variant_id = osr.variant_id
JOIN options o ON o.option_id = osr.option_id
JOIN choice_group_options cgo ON cgo.option_id = osr.option_id
JOIN choice_groups cg ON cg.group_id = cgo.group_id
JOIN sections se ON se.section_id = cg.section_id
JOIN steps st ON st.step_id = se.step_id
WHERE osr.active = true
  AND osr.resolved_status <> 'unavailable'
  AND v.active = true
  AND o.active = true
  AND cgo.active = true
  AND cg.active = true
  AND se.active = true
  AND st.active = true;

CREATE VIEW app_standard_equipment AS
SELECT
  osr.variant_id,
  o.option_id,
  o.rpo_code,
  o.option_label AS label,
  o.option_description AS description,
  osr.resolved_status AS status,
  oa.notes
FROM option_status_resolved osr
JOIN options o ON o.option_id = osr.option_id
LEFT JOIN option_availability oa ON oa.availability_id = osr.source_availability_id
WHERE osr.active = true
  AND o.active = true
  AND osr.resolved_status IN ('standard_fixed', 'standard_choice', 'included');

CREATE VIEW app_rules_resolved AS
SELECT
  r.rule_id,
  COALESCE(r.variant_id, sv.variant_id) AS variant_id,
  r.rule_type,
  r.priority,
  CASE
    WHEN rc.source_option_id IS NOT NULL THEN 'option'
    WHEN rc.source_group_id IS NOT NULL THEN 'group'
    WHEN rc.source_variant_id IS NOT NULL THEN 'variant'
  END AS source_type,
  COALESCE(rc.source_option_id, rc.source_group_id, rc.source_variant_id) AS source_id,
  CASE
    WHEN ra.target_option_id IS NOT NULL THEN 'option'
    WHEN ra.target_group_id IS NOT NULL THEN 'group'
    WHEN ra.target_variant_id IS NOT NULL THEN 'variant'
  END AS target_type,
  COALESCE(ra.target_option_id, ra.target_group_id, ra.target_variant_id) AS target_id,
  ra.action_type,
  ra.price_mode,
  ra.rule_action_value,
  r.message
FROM rules r
LEFT JOIN scope_variants sv ON sv.scope_id = r.scope_id
JOIN rule_conditions rc ON rc.rule_id = r.rule_id AND rc.active = true
JOIN rule_actions ra ON ra.rule_id = r.rule_id AND ra.active = true
WHERE r.active = true;

CREATE VIEW app_packages_resolved AS
SELECT
  osr.variant_id,
  p.package_option_id,
  pm.member_option_id,
  pm.member_status,
  pm.member_price_mode,
  pm.member_price_value,
  pm.required,
  pm.locked
FROM packages p
JOIN package_members pm ON pm.package_id = p.package_id
JOIN option_status_resolved osr ON osr.option_id = p.package_option_id
WHERE p.active = true
  AND pm.active = true
  AND osr.active = true
  AND osr.resolved_status <> 'unavailable';

CREATE INDEX idx_variants_active_lookup
  ON variants (dataset_id, model_year, model_key, body_style, trim_level)
  WHERE active = true;

CREATE INDEX idx_variant_scopes_lookup
  ON variant_scopes (dataset_id, year_min, year_max, model_key, body_style, trim_level)
  WHERE active = true;

CREATE INDEX idx_scope_variants_variant
  ON scope_variants (variant_id);

CREATE INDEX idx_options_rpo
  ON options (rpo_code);

CREATE INDEX idx_steps_dataset_order
  ON steps (dataset_id, display_order)
  WHERE active = true;

CREATE INDEX idx_sections_step_order
  ON sections (step_id, display_order)
  WHERE active = true;

CREATE INDEX idx_choice_groups_section_order
  ON choice_groups (section_id, display_order)
  WHERE active = true;

CREATE INDEX idx_choice_group_options_group_order
  ON choice_group_options (group_id, display_order)
  WHERE active = true;

CREATE INDEX idx_choice_group_options_option
  ON choice_group_options (option_id)
  WHERE active = true;

CREATE INDEX idx_option_availability_scope
  ON option_availability (scope_id, option_id)
  WHERE active = true;

CREATE INDEX idx_option_availability_variant
  ON option_availability (variant_id, option_id)
  WHERE active = true;

CREATE INDEX idx_option_status_resolved_variant_status
  ON option_status_resolved (variant_id, resolved_status)
  WHERE active = true;

CREATE INDEX idx_rules_scope_variant
  ON rules (scope_id, variant_id, priority)
  WHERE active = true;

CREATE INDEX idx_rule_conditions_rule_order
  ON rule_conditions (rule_id, condition_group, condition_order)
  WHERE active = true;

CREATE INDEX idx_rule_actions_rule
  ON rule_actions (rule_id, action_type)
  WHERE active = true;

CREATE INDEX idx_package_members_package
  ON package_members (package_id)
  WHERE active = true;

CREATE INDEX idx_source_rows_hash
  ON source_rows (row_hash);

CREATE INDEX idx_source_rows_dataset_variant_rpo
  ON source_rows (dataset_id, variant_id, raw_rpo)
  WHERE active = true;

COMMIT;
