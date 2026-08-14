# Pass C.1 — Canonical workbook coverage gaps in dry-run apply plan

Status: implemented 2026-07-08 after Sean approval. C.2 follow-up completed 2026-07-08 to close the real-data dry-run row-shape blocker (`rule_mapping.active` removed; `exclusive_groups.group_name` remapped to `notes`) and rebuild run `20260707-193441-ea9e4c` to `plan_built` with `stage2.ok=true`. Dry-run plan coverage only; no workbook writes, generated artifacts, runtime promotion, or Pass D writer.

## Diagnosis

Pass C already builds a deterministic dry-run apply plan and keeps the live workbook byte-identical. Sean's latest review found the review lanes are close enough to move forward, but the plan still has continuity gaps against canonical workbook surfaces.

Evidence inspected:

- `scripts/corvette_form_generator/ingest/wizard/plan_builder.py`
  - Stage 1 already creates/activates model sheet roles for `options`, `ovs`, `rule_mapping`, `price_rules`, `rule_groups`, `rule_group_members`, `exclusive_groups`, `exclusive_members`, and `variant_overrides`.
  - Stage 2 currently writes option rows, OVS rows, direct relationship rows, exclusive groups/members, and presentation metadata.
  - Option row `display_order` is currently a generated counter starting at 10, not a reviewer-visible/continuity-checked value.
  - Price-rule and rule-group/member sheets exist in the scaffolding path, but the current decisions do not fully author the canonical row sets.
  - `default_selection_rules` is not in the current plan-builder surface even though the parent Pass C contract lists it as a data op and runtime loads it into `defaultSelectionRules` / `default_selected` behavior.
  - `blockingGaps` currently only blocks `presentation_missing`, `missing_mandatory_decision`, and `no_variants_mapped`; new C.1 canonical gaps would not block approval unless the implementation changes that classification.
  - Deferrals for interiors/colors/media are report items, not workbook row ops.
- `scripts/corvette_form_generator/editor_ops.py`
  - `GLOBAL_SHEET_FAMILIES` exposes `model_interior_scope` and presentation/global model metadata sheets, but not `default_selection_rules`. C.1 must either add editor support for it or emit a blocking gap that prevents Pass D approval.
  - `model_interior_scope` is keyed by `(model_key, interior_id, trim_level)`; it must be handled as a global keyed sheet, not a clean-reprocess model sheet.
- `scripts/corvette_form_generator/production.py`
  - Runtime contract generation loads `default_selection_rules` via `load_default_selection_rules()` and publishes the result as `defaultSelectionRules`.
- Live workbook header probe (`stingray_master.xlsx`, read-only):
  - `grandSport_options`: `option_id`, `rpo`, `price`, `option_name`, `description`, `detail_raw`, `section_id`, `selectable`, `display_order`, `active`, `display_behavior`.
  - `grandSport_price_rules`: `price_rule_id`, `condition_option_id`, `price_rule_type`, `target_option_id`, `price_value`, `body_style_scope`, `trim_level_scope`, `notes`.
  - `grandSport_rule_groups`: `group_id`, `group_type`, `source_id`, `body_style_scope`, `trim_level_scope`, `variant_scope`, `disabled_reason`, `active`, `notes`.
  - `grandSport_rule_group_members`: `group_id`, `target_id`, `display_order`, `active`.
  - `model_interior_scope`: `model_key`, `interior_id`, `trim_level`, `active`, `requires_option_id`, `notes`, plus grouping/display columns.
  - `lt_interiors` and `LZ_Interiors` are the canonical interior row sources for LT and LZ models respectively.
  - `default_selection_rules` is a canonical runtime input and has workbook schema validation for `display_behavior` values.
- `docs/ingest/ingest-wizard-end-to-end-completion-spec.md` already states that Pass C data ops should include `*_price_rules`, `*_rule_groups`, `*_rule_group_members`, `default_selection_rules`, exterior paint option rows, and interior-scope links, but implementation is not complete enough for those surfaces.

Risk level: medium/high. This is still dry-run planning only, but it touches canonical workbook row families that become Pass D's write list. A hidden shortcut here would produce missing live-model behavior later.

Change class: wizard plan-builder + editor op metadata + fixture tests + docs. No workbook writes.

## Source-of-truth decision

- Workbook sheets and headers are authoritative for row shape and valid target surfaces.
- The wizard/plan builder may derive a dry-run operation list from approved decisions and existing workbook references.
- The plan must not invent product facts that the export/reviewer did not provide. Missing coverage must be either a workbook op with explicit provenance or a named blocking/open gap.
- `build_plan().valid` / `plan_approved` must be fail-closed for required runtime behavior. C.1 cannot add soft gaps for required canonical surfaces and still allow approval.
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
- Resolve `condition_option_id` and `target_option_id` against both newly planned options and existing live workbook option rows for the target model.
- If the UI cannot yet capture those fields, add explicit blocking/open gaps instead of writing guessed rows.

### 3. Rule groups and group members

Close the current relationship/exclusive-group continuity hole between direct rules and grouped rules.

Minimum acceptable behavior:

- Keep simple Requires / Includes / Not available with decisions in `*_rule_mapping` when that is the canonical representation.
- Emit `*_rule_groups` + `*_rule_group_members` only when a reviewed decision actually represents a group/set relationship and contains enough structured payload.
- Preserve `display_order` in group members deterministically.
- Resolve relationship/group endpoints against both newly planned option rows and existing live workbook option rows for the same target model. Decisions must store either canonical `option_id` or an RPO plus model/reference context sufficient to resolve a stable `option_id`; do not rely only on newly planned `option_id_by_rpo`.
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
- Treat `model_interior_scope` as a global keyed sheet, not a clean-reprocess model sheet. Key rows by `(model_key, interior_id, trim_level)` to match `editor_ops.py`.
- Existing ZR1/ZR1X scope rows must be read and compared before emitting operations:
  - identical desired row: no-op;
  - existing row differs in C.1-owned fields: emit an update with explicit before/after context;
  - desired row missing: emit an add;
  - existing row that should be removed/deactivated: emit a named blocking/open gap unless the pass explicitly approves deactivation semantics.
- Do not generate or edit `lt_interiors` / `LZ_Interiors` interior definitions in this pass.
- If trim/body scope cannot be determined mechanically, emit reviewable gaps rather than guessed rows.

### 6. Default selection rules

Add C.1 handling for `default_selection_rules`, or explicitly block Pass D approval when required default-selection behavior cannot be represented.

Minimum acceptable behavior:

- Inspect the canonical sheet headers and runtime loader contract before implementation.
- Add `default_selection_rules` to `editor_ops.py` global editable families if dry-run ops will target the sheet.
- Emit default-selection rows only from explicit reviewer decisions or safe workbook-reference carry-forward. Do not derive defaults from status alone.
- Preserve `display_behavior` semantics, especially `default_selected`, because runtime schema validation already treats this as a constrained workbook-authored value.
- If the current review lanes cannot capture the default-selection decision cleanly, emit a blocking gap such as `default_selection_rules_missing` rather than allowing `plan_approved`.

### 7. Remaining color/component/media deferrals

Carry forward unresolved workbook surfaces from the existing `interior_media_deferral` lane instead of letting them disappear when C.1 adds only interior scope and paint rows.

Minimum acceptable behavior:

- `color_overrides` deferrals remain named open items unless C.1 implements structured ops for that sheet.
- `interior_components` / component pricing deferrals remain named open items unless C.1 implements structured ops for that sheet.
- `asset_map` / media deferrals remain named open items; they are not go-live blocking unless an explicit C.1 validation rule says a required image is missing.
- The plan report must separate implemented ops from carried-forward open items so Pass D reviewers can see what is still manual.

## Blocking gap policy

C.1 must update `build_plan()` so new gap kinds are intentionally classified as blocking or non-blocking. The current implementation only blocks `presentation_missing`, `missing_mandatory_decision`, and `no_variants_mapped`; that is insufficient once C.1 adds canonical workbook coverage checks.

Required blocking gaps before `plan_approved`:

- `option_display_order_missing`
- `option_display_order_collision`
- `price_rule_unresolved_required`
- `rule_group_unresolved_required`
- `relationship_option_identity_unresolved`
- `exterior_paint_rows_missing_required`
- `model_interior_scope_missing_required`
- `model_interior_scope_conflict`
- `default_selection_rules_missing`
- `default_selection_rule_unresolved_required`
- any gap where a required target workbook sheet is absent or not editable by `editor_ops.py`

Allowed non-blocking/open items only when explicitly reported:

- `color_overrides_deferred`
- `interior_components_deferred`
- `asset_map_deferred`
- optional paint/interior media gaps that do not affect runtime option/rule/default behavior

Tests must assert both sides: required gaps make `plan["valid"]` false and appear in `report.blockingGaps`; open deferrals remain visible in `report.deferrals` or non-blocking `report.gaps` without pretending they were written.

## Exact files expected to change

Likely:

- `scripts/corvette_form_generator/ingest/wizard/plan_builder.py`
- `scripts/corvette_form_generator/editor_ops.py` if `default_selection_rules` ops are emitted instead of blocked
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
- No duplicate/colliding `model_interior_scope` adds for existing ZR1/ZR1X rows; use read/compare/no-op/update/add semantics.
- No relationship/price/rule-group endpoint resolution that only sees newly planned rows when a canonical existing workbook option row should resolve the identity.
- No silent approval of required default-selection behavior; write `default_selection_rules` rows or block.
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

Specific regression expectations:

- `default_selection_rules` missing/uneditable required behavior blocks approval.
- New C.1 required gap kinds populate `blockingGaps` and make `valid` false.
- `model_interior_scope` existing rows are no-op/update, not duplicate adds.
- Relationship/group endpoints resolve against planned and existing option IDs.
- `color_overrides`, `interior_components`, and `asset_map` deferrals remain visible if not implemented.

## Implementation closeout — 2026-07-08

Implemented in the approved first C.1 slice:

- `scripts/corvette_form_generator/ingest/wizard/plan_builder.py`
  - Loads global workbook rows needed for planning: `default_selection_rules`, `model_interior_scope`, `color_overrides`, `interior_components`, `asset_map`, and the target model's canonical interior source sheet.
  - Uses section-local option display-order allocation with collision/missing-order blocking gaps.
  - Expands `blockingGaps` classification to fail closed for required canonical surfaces instead of allowing approval with ordinary soft gaps.
  - Resolves relationship/exclusive endpoints against planned options and retained existing target option rows; existing option rows referenced by a relationship are not deleted during the dry-run clean-reprocess plan.
  - Emits `default_selection_rules` rows from explicit reviewed exclusive-group default payloads, and blocks when a default is required but not supplied/resolvable.
  - Adds `model_interior_scope` add/update/no-op behavior keyed by `(model_key, interior_id, trim_level)`; existing matching rows are no-op, differing rows update only changed fields, missing desired rows add.
  - Carries forward named non-blocking `color_overrides_deferred`, `interior_components_deferred`, and `asset_map_deferred` gaps from interior/media deferrals.
- `scripts/corvette_form_generator/editor_ops.py`
  - Exposes `default_selection_rules` as an editable global family keyed by `(model_key, rule_id)`, with typed `priority`/`active` fields and constrained `condition_type` / `display_behavior` values.
- `tests/ingest_wizard_fixtures.py`
  - Adds canonical fixture sheets/headers for C.1: `default_selection_rules`, `LZ_Interiors`, `model_interior_scope`, and missing Z06 template row families used by dry-run sheet creation.
- `tests/test_ingest_wizard_plan.py`
  - Adds regression coverage for default-selection rule ops, required-default blocking, existing-option identity retention, and keyed interior-scope no-op/add behavior.
- `tests/test_editor_ops_global_families.py`
  - Adds editor-op coverage for `default_selection_rules` add and display-behavior enum rejection.

Still intentionally deferred / open for later passes:

- Full structured price-rule authoring beyond existing direct option-price decisions.
- Full `*_rule_groups` / `*_rule_group_members` authoring beyond existing relationship/exclusive decisions.
- Exterior paint row authoring when the current review payload lacks structured paint evidence.
- Actual structured ops for `color_overrides`, `interior_components`, and `asset_map`; C.1 keeps those visible as non-blocking open items.
- Any Pass D real workbook writer or workbook mutation.

Validation run:

```sh
.venv/bin/python -m pytest tests/test_ingest_wizard_plan.py tests/test_ingest_wizard_decisions.py tests/test_ingest_wizard_server_pass_b.py tests/test_editor_ops_global_families.py -q
# 71 passed in 5.51s
node --check visualizer/ingest-wizard/wizard.js
# passed
git diff --check
# passed
```
