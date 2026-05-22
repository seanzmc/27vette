# Spec 04: Model-Specific Sheet Contracts and category_master Cleanup

## Diagnosis

Root cause: model-specific source sheets are the approved direction, but active source graph references still include category_master even though current workbook lacks a live category_master sheet. Need explicit sheet contract documentation/checks without migrating to shared model_key sheets.

Evidence:
- Primary model sheets are mostly header-compatible.
- category_master requested/referenced, but workbook has archive_category_master only.
- Sean approved removing category_master references.
- Sean approved model-specific sheets and model-specific grandSport_variant_overrides.

Risk level: medium.
Change type: docs/schema contract + validation; no workbook business-data or runtime behavior changes intended.

## Exact Files / Sheets To Inspect

Workbook:
- stingray_master.xlsx
  - stingray_options
  - grandSport_options
  - stingray_ovs
  - grandSport_ovs
  - rule_mapping
  - grandSport_rule_mapping
  - price_rules
  - grandSport_price_rules
  - rule_groups
  - grandSport_rule_groups
  - rule_group_members
  - grandSport_rule_group_members
  - exclusive_groups
  - grandSport_exclusive_groups
  - exclusive_group_members
  - grandSport_exclusive_members
  - grandSport_variant_overrides
  - section_master
  - archive_category_master as retired evidence only

Docs/code:
- AGENTS.md
- README.md if it mentions category_master
- codex-context.md if present/relevant
- scripts/corvette_form_generator/model_config.py
- scripts/corvette_form_generator/model_configs.py
- scripts/corvette_form_generator/runtime_metadata.py
- tests/audit-parser-metadata-loaders.test.mjs if schema metadata involved

## Constraints

- Keep model-specific source sheets.
- Do not introduce shared model_key columns.
- grandSport_variant_overrides remains model-specific.
- Remove category_master only from active source graph references; do not delete archive_category_master unless separately approved.
- No generated artifact hand edits.
- No new dependencies.

## Proposed Model-Specific Contract Pattern

Required per-model sheet families:
- {model}_options equivalent
- {model}_ovs equivalent
- {model}_rule_mapping equivalent
- {model}_price_rules equivalent
- {model}_rule_groups equivalent
- {model}_rule_group_members equivalent
- {model}_exclusive_groups equivalent
- {model}_exclusive_members equivalent
- {model}_variant_overrides optional, model-specific when needed

Current mappings:
- Stingray keeps legacy unprefixed rule/price/group/exclusive names.
- Grand Sport uses grandSport_* names.
- ModelConfig owns exact mapping.

Reference sheets:
- section_master active.
- variant_master active.
- PriceRef active.
- category_master retired/removed from active graph.

## Implementation Outline

1. Search active docs/code for category_master.
2. Classify each hit:
   - active source graph reference: remove/update.
   - archive/history reference: keep if clearly marked archived.
3. Add schema contract doc or update existing schema-plan spec docs with sheet mappings.
4. Add or plan validation that category_master is not required as active sheet.
5. Verify ModelConfig sheet mapping remains model-specific.

## Validation Plan

Docs-only/category cleanup gates:
```sh
git diff -- README.md AGENTS.md codex-context.md schema-plan
```

Search checks:
```sh
rg -n "category_master" README.md AGENTS.md codex-context.md scripts tests schema-plan
rg -n "archive_category_master" README.md AGENTS.md codex-context.md scripts tests schema-plan
```

If code validation added:
```sh
node --test tests/audit-parser-metadata-loaders.test.mjs
node --test tests/grand-sport-draft-data.test.mjs
```

## Risks

- Removing category_master docs could hide legacy context if archive status not clear.
- Tests or loader metadata may still expect category_master as active sheet.
- Sheet-name contract may be confused by Stingray legacy unprefixed names.

## Non-goals

- Do not delete archive_category_master from workbook.
- Do not rename current model-specific sheets.
- Do not add model_key columns.
- Do not modify runtime behavior.
