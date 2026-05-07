BEGIN;

CREATE TABLE variants (
  variant_id text PRIMARY KEY,
  model_year integer NOT NULL,
  model_key text NOT NULL,
  body_style text NOT NULL,
  trim_level text NOT NULL,
  active boolean NOT NULL DEFAULT true
);

COMMENT ON TABLE variants IS 'One row per build context. variant_id is the canonical context key.';
COMMENT ON COLUMN variants.variant_id IS 'Stable spine identifier.';

CREATE TABLE options (
  option_id text PRIMARY KEY,
  rpo text NOT NULL,
  label text NOT NULL,
  description text,
  option_type text NOT NULL,
  active boolean NOT NULL DEFAULT true
);

COMMENT ON TABLE options IS 'One row per real option. RPO is a property; option_id is the key.';
COMMENT ON COLUMN options.option_id IS 'Stable spine identifier.';
COMMENT ON COLUMN options.rpo IS 'RPO code property. Repeated RPOs require review before separate option_ids are created.';

CREATE TABLE steps (
  step_key text NOT NULL,
  dataset_id text NOT NULL,
  step_label text NOT NULL,
  display_order integer NOT NULL,
  active boolean NOT NULL DEFAULT true,
  PRIMARY KEY (dataset_id, step_key)
);

COMMENT ON TABLE steps IS 'High-level build steps. Runtime fields such as runtime_order/source/section_ids are export concerns unless canonicalized later.';

CREATE TABLE sections (
  section_id text PRIMARY KEY,
  dataset_id text NOT NULL,
  step_key text NOT NULL,
  section_name text NOT NULL,
  category_id text NOT NULL,
  category_name text NOT NULL,
  display_order integer NOT NULL,
  active boolean NOT NULL DEFAULT true,
  FOREIGN KEY (dataset_id, step_key) REFERENCES steps (dataset_id, step_key)
);

COMMENT ON TABLE sections IS 'Display sections. Enriched UI policy fields remain unresolved and are not added here.';

CREATE TABLE choice_groups (
  group_id text PRIMARY KEY,
  label text NOT NULL,
  section_id text NOT NULL REFERENCES sections (section_id),
  section_name text NOT NULL,
  category_id text NOT NULL,
  category_name text NOT NULL,
  step_key text NOT NULL,
  selection_mode text NOT NULL CHECK (selection_mode IN ('single', 'single_select_req', 'single_select_opt')),
  required boolean NOT NULL,
  active boolean NOT NULL DEFAULT true
);

COMMENT ON TABLE choice_groups IS 'Logical decision points such as Wheels, Calipers, Paint, and Interior Color.';
COMMENT ON COLUMN choice_groups.group_id IS 'Stable spine identifier.';
COMMENT ON COLUMN choice_groups.selection_mode IS 'Constrained to values explicitly shown in newSchemaFinal.md.';

CREATE TABLE choice_group_options (
  group_id text NOT NULL REFERENCES choice_groups (group_id),
  option_id text NOT NULL REFERENCES options (option_id),
  display_order integer NOT NULL,
  active boolean NOT NULL DEFAULT true,
  PRIMARY KEY (group_id, option_id)
);

COMMENT ON TABLE choice_group_options IS 'Placement relationship between universal options and localized choice groups.';

CREATE TABLE option_status (
  option_id text NOT NULL REFERENCES options (option_id),
  variant_id text NOT NULL REFERENCES variants (variant_id),
  status text NOT NULL CHECK (status IN ('optional', 'standard_choice', 'standard_fixed', 'included', 'unavailable')),
  price numeric(12, 2) NOT NULL DEFAULT 0,
  active boolean NOT NULL DEFAULT true,
  PRIMARY KEY (option_id, variant_id)
);

COMMENT ON TABLE option_status IS 'Resolved option state per option_id + variant_id.';
COMMENT ON COLUMN option_status.status IS 'Allowed values are exactly those listed in newSchemaFinal.md.';

CREATE TABLE standard_equipment (
  standard_equipment_id text PRIMARY KEY,
  dataset_id text NOT NULL,
  variant_id text NOT NULL REFERENCES variants (variant_id),
  option_id text NOT NULL REFERENCES options (option_id),
  section_id text NOT NULL REFERENCES sections (section_id),
  display_order integer NOT NULL,
  label_override text,
  description_override text,
  notes text,
  active boolean NOT NULL DEFAULT true,
  FOREIGN KEY (option_id, variant_id) REFERENCES option_status (option_id, variant_id)
);

COMMENT ON TABLE standard_equipment IS 'Materialized export table only. Source of truth is option_status where status is standard_choice, standard_fixed, or included.';

CREATE TABLE rules (
  rule_id text PRIMARY KEY,
  rule_type text NOT NULL CHECK (rule_type IN ('excludes', 'requires', 'includes', 'requires_any', 'price_override', 'replaces_default')),
  source_type text NOT NULL CHECK (source_type IN ('option', 'group', 'variant')),
  source_id text NOT NULL,
  target_type text NOT NULL CHECK (target_type IN ('option', 'group', 'variant')),
  target_id text NOT NULL,
  variant_id text REFERENCES variants (variant_id),
  message text,
  active boolean NOT NULL DEFAULT true
);

COMMENT ON TABLE rules IS 'Single relationship table for excludes, requires, includes, requires_any, price_override, and replaces_default.';
COMMENT ON COLUMN rules.rule_id IS 'Stable spine identifier.';
COMMENT ON COLUMN rules.source_id IS 'Polymorphic reference keyed by source_type. Enforce referential target existence in importer/application validation.';
COMMENT ON COLUMN rules.target_id IS 'Polymorphic reference keyed by target_type. Enforce referential target existence in importer/application validation.';
COMMENT ON COLUMN rules.variant_id IS 'Blank/null means the rule applies wherever both source and target exist.';

CREATE TABLE rule_members (
  rule_id text NOT NULL REFERENCES rules (rule_id),
  member_type text NOT NULL CHECK (member_type IN ('option', 'group', 'variant')),
  member_id text NOT NULL,
  member_order integer NOT NULL,
  active boolean NOT NULL DEFAULT true,
  PRIMARY KEY (rule_id, member_type, member_id)
);

COMMENT ON TABLE rule_members IS 'Authoritative satisfying-member list for multi-target rules such as requires_any.';
COMMENT ON COLUMN rule_members.member_id IS 'Polymorphic reference keyed by member_type. Enforce referential target existence in importer/application validation.';

CREATE TABLE source_rows (
  source_row_id text PRIMARY KEY,
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

COMMENT ON TABLE source_rows IS 'Raw import/staging evidence. Raw weirdness stays here instead of polluting canonical tables.';

CREATE INDEX idx_variants_active_lookup
  ON variants (model_key, body_style, trim_level)
  WHERE active = true;

CREATE INDEX idx_options_rpo
  ON options (rpo);

CREATE INDEX idx_options_active_type
  ON options (option_type)
  WHERE active = true;

CREATE INDEX idx_steps_dataset_order
  ON steps (dataset_id, display_order)
  WHERE active = true;

CREATE INDEX idx_sections_dataset_step_order
  ON sections (dataset_id, step_key, display_order)
  WHERE active = true;

CREATE INDEX idx_choice_groups_section_order
  ON choice_groups (section_id, group_id)
  WHERE active = true;

CREATE INDEX idx_choice_group_options_option
  ON choice_group_options (option_id)
  WHERE active = true;

CREATE INDEX idx_choice_group_options_group_order
  ON choice_group_options (group_id, display_order)
  WHERE active = true;

CREATE INDEX idx_option_status_variant_status
  ON option_status (variant_id, status)
  WHERE active = true;

CREATE INDEX idx_option_status_option
  ON option_status (option_id)
  WHERE active = true;

CREATE INDEX idx_standard_equipment_variant_section_order
  ON standard_equipment (variant_id, section_id, display_order)
  WHERE active = true;

CREATE INDEX idx_rules_source
  ON rules (source_type, source_id, rule_type)
  WHERE active = true;

CREATE INDEX idx_rules_target
  ON rules (target_type, target_id, rule_type)
  WHERE active = true;

CREATE INDEX idx_rules_variant_type
  ON rules (variant_id, rule_type)
  WHERE active = true;

CREATE INDEX idx_rule_members_rule_order
  ON rule_members (rule_id, member_order)
  WHERE active = true;

CREATE INDEX idx_source_rows_hash
  ON source_rows (row_hash);

CREATE INDEX idx_source_rows_variant_rpo
  ON source_rows (variant_id, raw_rpo)
  WHERE active = true;

COMMIT;
