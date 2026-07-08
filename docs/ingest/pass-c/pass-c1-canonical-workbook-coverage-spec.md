# Pass C.1 — Canonical workbook coverage gaps in dry-run apply plan

Status: draft for Sean approval (2026-07-07). No implementation yet.

## Diagnosis

Pass C already builds a deterministic dry-run apply plan and keeps the live workbook byte-identical. Sean's latest review found the review lanes are close enough to move forward, but the plan still has continuity gaps against canonical workbook surfaces.

Evidence inspected:

- `scripts/corvette_form_generator/ingest/wizard/plan_builder.py`
  - Stage 1 already creates/activates model sheet roles for `options`, `ovs`, `rule_mapping`, `price_rules`, `rule_groups`, `rule_group_members`, `exclusive_groups`, `exclusive_members`, and `variant_overrides`.
  - Stage 2 currently writes option rows, OVS rows, direct relationship rows, exclusive groups/members, and presentation metadata.
  - Option row `display_order` is currently a generated counter starting at 10, not a reviewer-visible/continuity-checked value.
  - Price-rule and rule-group/member sheets exist in the scaffolding path, but the current decisions do not fully author the canonical row sets.
  - Deferrals for interiors/colors/media are report items, not workbook row ops.
- Live workbook header probe (`stingray_master.xlsx`, read-only):
  - `grandSport_options`: `option_id`, `rpo`, `price`, `option_name`, `description`, `detail_raw`, `section_id`, `selectable`, `display_order`, `active`, `display_behavior`.
  - `grandSport_price_rules`: `price_rule_id`, `condition_option_id`, `price_rule_type`, `target_option_id`, `price_value`, `body_style_scope`, `trim_level_scope`, `notes`.
  - `grandSport_rule_groups`: `group_id`, `group_type`, `source_id`, `body_style_scope`, `trim_level_scope`, `variant_scope`, `disabled_reason`, `active`, `notes`.
  - `grandSport_rule_group_members`: `group_id`, `target_id`, `display_order`, `active`.
  - `model_interior_scope`: `model_key`, `interior_id`, `trim_level`, `active`, `requires_option_id`, `notes`, plus grouping/display columns.
  - `lt_interiors` and `LZ_Interiors` are the canonical interior row sources for LT and LZ models respectively.
- `docs/ingest/ingest-wizard-end-to-end-completion-spec.md` already states that Pass C data ops should include `*_price_rules`, `*_rule_groups`, `*_rule_group_members`, exterior paint option rows, and interior-scope links, but implementation is not complete enough for those surfaces.

Risk level: medium/high. This is still dry-run planning only, but it touches canonical workbook row families that become Pass D's write list. A hidden shortcut here would produce missing live-model behavior later.

Change class: wizard plan-builder + fixture tests + docs. No workbook writes.

## Source-of-truth decision

- Workbook sheets and headers are authoritative for row shape and valid target surfaces.
- The wizard/plan builder may derive a dry-run operation list from approved decisions and existing workbook references.
- The plan must not invent product facts that the export/reviewer did not provide. Missing coverage must be either a workbook op with explicit provenance or a named blocking/open gap.
- Generated artifacts and `form-app/` remain out of scope.

## Scope

### 1. Display-order continuity for option rows

Add plan-visible display-order handling for new option rows.

Minimum acceptable behavior:

- Preserve any explicit reviewer/reference display order when available.
- Otherwise allocate deterministic order inside each target `section_id`, not a single global counter.
- Use live workbook rows as the baseline where the model has active reference rows; for clean-reprocess sheets, still allocate stable section-local order to make the diff reviewable.
- Report rows that lack a section or collide on `(sheet, section_id, display_order)` as plan gaps before Pass D.

### 2. Price rules

Add dry-run plan support for canonical `*_price_rules` rows where the reviewed decisions imply a conditional price rather than a direct option price.

Minimum acceptable behavior:

- Do not force every ambiguous price into a price rule.
- Only emit `*_price_rules` when the reviewer decision payload has enough structured fields to identify condition option, rule type, target option, price value, and body/trim scope.
- If the UI cannot yet capture those fields, add explicit blocking/open gaps instead of writing guessed rows.

### 3. Rule groups and group members

Close the current relationship/exclusive-group continuity hole between direct rules and grouped rules.

Minimum acceptable behavior:

- Keep simple Requires / Includes / Not available with decisions in `*_rule_mapping` when that is the canonical representation.
- Emit `*_rule_groups` + `*_rule_group_members` only when a reviewed decision actually represents a group/set relationship and contains enough structured payload.
- Preserve `display_order` in group members deterministically.
- Keep unmappable relationship hints as gaps/questions, not silently approved workbook rules.

### 4. Exterior paint option rows for ingested models

Add a deliberate plan path for exterior paint option rows.

Minimum acceptable behavior:

- Use canonical workbook paint/options surfaces and headers; do not hardcode RPO lists in JS/Python.
- Prefer existing workbook reference rows when a paint RPO already exists on a comparator model.
- If the raw order guide does not include enough paint evidence for a target model, emit a named plan gap/deferral instead of fabricating rows.

### 5. Interior scope links

Add dry-run plan support for `model_interior_scope` rows for ingested models.

Minimum acceptable behavior:

- Grand Sport X links to `lt_interiors`.
- ZR1 and ZR1X link to `LZ_Interiors`.
- Use the canonical interior IDs and grouping/display columns from existing interior sheets/scope rows.
- Do not generate or edit `lt_interiors` / `LZ_Interiors` interior definitions in this pass.
- If trim/body scope cannot be determined mechanically, emit reviewable gaps rather than guessed rows.

## Exact files expected to change

Likely:

- `scripts/corvette_form_generator/ingest/wizard/plan_builder.py`
- `tests/ingest_wizard_fixtures.py`
- `tests/test_ingest_wizard_plan.py`
- this spec file

Possible if structured reviewer fields are needed before emitting rows:

- `scripts/corvette_form_generator/ingest/wizard/session.py`
- `scripts/corvette_form_generator/ingest/wizard/decisions.py`
- `scripts/ingest_wizard_server.py`
- `visualizer/ingest-wizard/wizard.js`
- `visualizer/ingest-wizard/wizard.css`
- additional focused UI/static tests

Not expected:

- `stingray_master.xlsx`
- `form-output/`
- `form-app/`
- dealer submission/runtime code
- `scripts/ingest_wizard_apply.py` / real Pass D writer

## Companion-file impact

- Workbook/generated artifacts: n/a for implementation; live workbook read-only only.
- Plan builder tests: update/add required.
- Ingest docs: update this spec and the end-to-end spec when implemented.
- Runtime/dealer: inspected-no-change unless a later generated-artifact pass explicitly starts.
- Gates/README: no command changes expected.

## Constraints and non-goals

- No workbook writes.
- No generated artifact refresh.
- No Pass D apply implementation.
- No exterior paint or interior fact invention.
- No broad UI overhaul in this pass. Only add UI controls if required to capture structured fields that the dry-run plan cannot safely infer.
- No dealer endpoint/payload/submission behavior changes.

## Validation plan

Targeted:

```sh
.venv/bin/python -m pytest \
  tests/test_ingest_wizard_plan.py \
  tests/test_ingest_wizard_decisions.py \
  tests/test_ingest_wizard_server_pass_b.py -q
node --check visualizer/ingest-wizard/wizard.js
git diff --check
```

If UI controls are added:

```sh
.venv/bin/python -m pytest tests/test_ingest_wizard_ui_*.py -q
node --check visualizer/ingest-wizard/wizard.js
```

If workbook schema assumptions are expanded, add fixture-level assertions for the exact headers and row keys instead of writing the live workbook.

## Approval question

Recommended next implementation slice: display-order continuity + interior-scope dry-run rows first, then price rules/rule groups/exterior paint only where the current decisions already contain enough structured data. That keeps the first C.1 patch reviewable and avoids guessing product rules.
