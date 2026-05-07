## Draft 2020-12 Master Schema

**Important design position:** standard JSON Schema cannot, by itself, dynamically derive foreign-key domains from sibling arrays such as `options[*].option_id` and then validate `rules[*].target_id` against that derived set in the same pass. The standards-compliant way to make internal references strict is to **compile** this schema before validation by adding `enum` values to the `$defs.id_domains` definitions from the canonical primary-key columns.

This schema therefore uses:

- **Generated enum-backed ID domains** for strict foreign-key validation.
- **Shared `$defs` ID definitions** so every `option_id`, `variant_id`, `group_id`, and `rule_id` points to one canonical domain.
- **`x-*` metadata annotations** such as `x-primaryKey`, `x-uniqueKeys`, and `x-foreignKey` for companion validators, AJV custom keywords, or ETL checks.
- **Open CSV row posture** with `additionalProperties: true`.
- **Conditional subschemas** for status pricing, rule-type behavior, derivation rules, and validation targeting.
- **Folder/table arrays** at the top level so converted CSV files can be bundled into one master object.

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://example.com/schemas/configuration/master.schema.json",
  "title": "Configuration Master Schema",
  "description": "Master schema for a folder-based collection of CSV-derived configuration entities. Each top-level property is a table/folder of converted CSV rows. The architecture is anchored by a stable spine of variant_id, option_id, group_id, and rule_id. Canonical option_id values are reused across availability, grouping, rules, standard equipment, interiors, and staging references.",
  "$comment": "For strict foreign-key validation, compile this schema by adding enum arrays to $defs.id_domains.$defs.* from the corresponding primary-key columns before validating the full bundle.",
  "type": "object",
  "additionalProperties": true,
  "required": [
    "steps",
    "sections",
    "variants",
    "options",
    "option_status",
    "choice_groups",
    "choice_group_options",
    "interiors",
    "color_overrides",
    "rules",
    "rule_members",
    "standard_equipment",
    "source_rows",
    "validation"
  ],
  "properties": {
    "steps": {
      "description": "Folder/table of high-level build steps converted from CSV rows.",
      "$ref": "#/$defs/folders/$defs/steps"
    },
    "sections": {
      "description": "Folder/table of UI sections converted from CSV rows.",
      "$ref": "#/$defs/folders/$defs/sections"
    },
    "variants": {
      "description": "Folder/table of buildable contexts keyed by variant_id.",
      "$ref": "#/$defs/folders/$defs/variants"
    },
    "options": {
      "description": "Folder/table of canonical global options keyed by option_id.",
      "$ref": "#/$defs/folders/$defs/options"
    },
    "option_status": {
      "description": "Folder/table bridging variant_id and option_id with variant-specific availability and pricing.",
      "$ref": "#/$defs/folders/$defs/option_status"
    },
    "choice_groups": {
      "description": "Folder/table of choice/display groups keyed by group_id.",
      "$ref": "#/$defs/folders/$defs/choice_groups"
    },
    "choice_group_options": {
      "description": "Folder/table linking canonical options to choice groups.",
      "$ref": "#/$defs/folders/$defs/choice_group_options"
    },
    "interiors": {
      "description": "Folder/table of interior records collapsed onto the canonical option/group/rule spine.",
      "$ref": "#/$defs/folders/$defs/interiors"
    },
    "color_overrides": {
      "description": "Folder/table of interior/exterior pairing rules that add, include, force, remove, or override options.",
      "$ref": "#/$defs/folders/$defs/color_overrides"
    },
    "rules": {
      "description": "Folder/table of configuration rule headers and direct source-target relationships.",
      "$ref": "#/$defs/folders/$defs/rules"
    },
    "rule_members": {
      "description": "Folder/table of normalized multi-member rule participants.",
      "$ref": "#/$defs/folders/$defs/rule_members"
    },
    "standard_equipment": {
      "description": "Folder/table of derived standard equipment rows referencing canonical option_id values.",
      "$ref": "#/$defs/folders/$defs/standard_equipment"
    },
    "source_rows": {
      "description": "Folder/table of raw or staged order-guide evidence rows.",
      "$ref": "#/$defs/folders/$defs/source_rows"
    },
    "validation": {
      "description": "Folder/table of build-integrity findings.",
      "$ref": "#/$defs/folders/$defs/validation"
    }
  },
  "$defs": {
    "id_domains": {
      "$comment": "STRICT FK HOOK. Add enum arrays to these schemas before validation. For example, option_id.enum should be the distinct set of options[*].option_id. If you control ID generation, namespaced IDs such as VAR_*, OPT_*, GRP_*, and RUL_* are recommended as an additional guardrail, but this schema allows legacy codes such as D30.",
      "$defs": {
        "dataset_id": {
          "description": "Stable identifier for a source dataset, order guide, market, model year, or release.",
          "type": "string",
          "minLength": 1,
          "pattern": "^[A-Za-z0-9][A-Za-z0-9_.:-]*$"
        },
        "step_key": {
          "description": "Primary key for a build step. Compile-time enum should come from steps[*].step_key.",
          "type": "string",
          "minLength": 1,
          "pattern": "^[A-Za-z0-9][A-Za-z0-9_.:-]*$",
          "x-domainSource": {
            "folder": "steps",
            "field": "step_key"
          },
          "x-recommendedPattern": "^[a-z][a-z0-9_:-]*$"
        },

```
