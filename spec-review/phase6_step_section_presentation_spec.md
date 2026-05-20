# Phase 6 Spec — Workbook-Owned Step, Section, and Presentation Metadata

Status: proposed; do not implement until approved.

## Green check for Phase 5

I re-ran the workbook/package and current generator/runtime gates before writing this spec.

Commands run from `/Users/seandm/Projects/27vette`:

```sh
.venv/bin/python scripts/validate_workbook_package.py stingray_master.xlsx
.venv/bin/python scripts/generate_stingray_form.py
.venv/bin/python scripts/generate_grand_sport_form.py
node --test tests/stingray-form-regression.test.mjs
node --test tests/multi-model-runtime-switching.test.mjs
node --test tests/stingray-generator-stability.test.mjs
node --test tests/grand-sport-contract-preview.test.mjs
node --test tests/grand-sport-draft-data.test.mjs
node --test tests/grand-sport-rule-audit.test.mjs
```

Result: GREEN.

Observed gate details:
- Workbook package validation: valid, 0 issues.
- Stingray generator: 1464 choices, 467 standard equipment rows, 130 interiors, 0 validation errors.
- Grand Sport generator: inspection/draft artifacts generated, draft 132 interiors, 1 expected warning about inactive Grand Sport variants in `variant_master`.
- Tests: all listed suites passed.
  - `tests/stingray-form-regression.test.mjs`: 73 passed.
  - `tests/multi-model-runtime-switching.test.mjs`: 19 passed.
  - `tests/stingray-generator-stability.test.mjs`: 11 passed, including `Stingray Phase 5 interior components are workbook-owned`.
  - `tests/grand-sport-contract-preview.test.mjs`: 6 passed.
  - `tests/grand-sport-draft-data.test.mjs`: 15 passed, including Grand Sport interior scoping checks.
  - `tests/grand-sport-rule-audit.test.mjs`: 8 passed.

Additional Phase 5 workbook/code spot checks:
- `interior_components`: 395 active rows total; 197 Stingray, 198 Grand Sport.
- `model_interior_scope`: 132 active Grand Sport rows.
- Active `interior_components` rows have no blank required `interior_id`, `rpo`, `component_type`, or `label` fields.
- Active component key duplicates: 0 for `(model_key, interior_id, rpo, component_type)`.
- Current code references the Phase 5 ownership path:
  - `scripts/corvette_form_generator/runtime_metadata.py`: `load_interior_components`.
  - `scripts/generate_stingray_form.py`: `workbook_interior_component_metadata`, `missing_workbook_components_` validation.
  - `scripts/corvette_form_generator/inspection.py`: `load_model_interior_scope_map`, `load_interior_components`.

The generator run changed only generated timestamps and workbook serialization during verification; those verification-only changes were reverted before this spec file was written.

## Diagnosis

Phase 6 migrates remaining presentation/navigation hardcodes into workbook-owned metadata while preserving generated output.

Current hardcoded or transitional sources to inspect and migrate:

1. Runtime step order and labels
   - `scripts/corvette_form_generator/model_configs.py`
     - `STEP_ORDER`
     - `STEP_LABELS`
   - `scripts/generate_stingray_form.py`
     - module copies `STEP_ORDER`, `STEP_LABELS`
     - `step_rows` currently built directly from `STEP_ORDER`/`STEP_LABELS` at lines around 746-755.

2. Synthetic body/trim context sections
   - `scripts/corvette_form_generator/model_configs.py`
     - `CONTEXT_SECTIONS`
   - `scripts/generate_stingray_form.py`
     - `section_rows` starts from `[dict(row) for row in CONTEXT_SECTIONS]` around line 723.

3. Section-to-step and standard-equipment bucket behavior
   - `scripts/corvette_form_generator/model_configs.py`
     - `SECTION_STEP_OVERRIDES`
     - `STANDARD_SECTIONS`
   - `scripts/corvette_form_generator/mapping.py`
     - `step_for_section()` still falls back through `section_step_overrides`, `standard_sections`, and section-name heuristics.
   - `scripts/corvette_form_generator/inspection.py`
     - `resolved_step_key()` and `section_step_resolution_source()` use config-level step overrides and standard section sets.

4. Stingray display-order overrides
   - `scripts/generate_stingray_form.py`
     - `STINGRAY_SECTION_DISPLAY_ORDER_OVERRIDES` for:
       - `sec_stri_001`: 30
       - `sec_gsha_001`: 50
       - `sec_gsce_001`: 51

5. Body-style ordering
   - `scripts/corvette_form_generator/model_configs.py`
     - `BODY_STYLE_DISPLAY_ORDER`
   - `scripts/generate_stingray_form.py`
     - body context choice sorting and `display_order` still use `BODY_STYLE_DISPLAY_ORDER` around lines 762-790.

6. Grand Sport display label overrides
   - `scripts/corvette_form_generator/model_configs.py`
     - `GRAND_SPORT_SECTION_LABEL_OVERRIDES` for:
       - `sec_gsce_001`: Grand Sport Center Stripes
       - `sec_gsha_001`: Grand Sport Heritage Hash Marks
       - `sec_spec_001`: Special Edition
       - `sec_colo_001`: Color Combination Override

7. Trim-equipment grouping regex in runtime
   - `form-app/app.js`
     - `trimEquipmentRows()` filters `/LT Equipment$/` against `section_name` around lines 1453-1455.

Existing workbook substrate:
- `runtime_steps` exists but is currently empty.
- `context_section_master` exists but is currently empty.
- `section_presentation` exists with only the prior Phase 4 row for hidden `sec_cust_002`.
- `standard_equipment_groups` exists but is currently empty.
- `runtime_metadata.py` already has loader fallbacks for `load_runtime_steps()`, `load_context_sections()`, and `load_section_presentation()`.

Root cause: Phase 1/2 created metadata tables/loaders, and Phase 4 introduced one `section_presentation` use for hidden sections, but the generator/runtime still use config constants and regex presentation rules as the active source for navigation, section placement, standard-equipment bucketing, labels, ordering, body ordering, and trim-equipment grouping.

Risk level: Medium.

Change type: mixed workbook data + generator behavior + generated artifacts + runtime behavior tests. Intended customer behavior is parity-only; source of truth changes from code constants/regex to workbook metadata.

## Constraints

- Preserve visual behavior and generated app behavior exactly unless this spec calls out a metadata-only field addition.
- No runtime redesign.
- No broad refactor.
- No new dependencies.
- Workbook remains source of truth where workbook can represent the rule.
- Do not edit generated `form_*` sheets manually.
- Do not hide bad source data in Python or JavaScript; add validation errors or fix workbook rows.
- Do not change dealer submission endpoint, payload shape, or Turnstile behavior.
- Do not alter live app deployment paths.
- Keep fallbacks for one release: if metadata rows are absent, output should remain driven by existing config constants.
- Close Excel before workbook-writing scripts. Refuse to write if `~$stingray_master.xlsx` exists.
- Workbook-writing scripts must save via `save_workbook_safely()` and verify the package before replacement.

## Exact files and workbook sheets to change

Workbook source sheets to backfill in `stingray_master.xlsx`:
- `runtime_steps`
- `context_section_master`
- `section_presentation`
- `standard_equipment_groups`

Generated workbook sheets affected after regeneration:
- `form_steps`
- `form_context_choices`
- `form_choices`
- `form_standard_equipment`
- `form_validation`

Source files to modify:
- `scripts/migrations/populate_phase6_presentation_metadata.py` — create.
- `scripts/corvette_form_generator/runtime_metadata.py` — extend/adjust loaders as needed.
- `scripts/corvette_form_generator/mapping.py` — make section bucketing/presentation metadata first-class while keeping current fallbacks.
- `scripts/generate_stingray_form.py` — consume workbook runtime/context/presentation metadata.
- `scripts/corvette_form_generator/inspection.py` — consume presentation metadata for Grand Sport preview/draft step and label parity.
- `form-app/app.js` — use emitted standard-equipment grouping metadata before regex fallback.

Tests to modify/add:
- `tests/stingray-generator-stability.test.mjs`
- `tests/stingray-form-regression.test.mjs`
- `tests/grand-sport-contract-preview.test.mjs`
- `tests/grand-sport-draft-data.test.mjs`
- `tests/multi-model-runtime-switching.test.mjs` if generated runtime contract coverage is clearer there.

Generated artifacts to review, not hand-edit:
- `form-output/stingray-form-data.json`
- `form-output/stingray-form-data.csv`
- `form-app/data.js`
- `form-output/inspection/grand-sport-inspection.json`
- `form-output/inspection/grand-sport-inspection.md`
- `form-output/inspection/grand-sport-contract-preview.json`
- `form-output/inspection/grand-sport-contract-preview.md`
- `form-output/inspection/grand-sport-form-data-draft.json`
- `form-output/inspection/grand-sport-form-data-draft.md`

## Non-goals

- Do not remove `STEP_ORDER`, `STEP_LABELS`, `CONTEXT_SECTIONS`, `SECTION_STEP_OVERRIDES`, `STANDARD_SECTIONS`, `BODY_STYLE_DISPLAY_ORDER`, or `GRAND_SPORT_SECTION_LABEL_OVERRIDES` yet. They remain fallback constants for one release.
- Do not migrate model registry/sheet ownership; that is Phase 7.
- Do not migrate rule parser/audit phrase/group constants; that is Phase 8.
- Do not change Grand Sport production activation status.
- Do not change section names, labels, step order, option availability, selected RPOs, prices, exports, or dealer payload shape.

## Implementation plan

### 1. Add Phase 6 workbook backfill migration

Create `scripts/migrations/populate_phase6_presentation_metadata.py`.

Behavior:
- Refuse to run if `~$stingray_master.xlsx` exists.
- Load `stingray_master.xlsx` with `openpyxl`.
- Preserve existing rows by upserting deterministic keys.
- Use `save_workbook_safely()`.
- Print counts by target sheet.

Upsert keys:
- `runtime_steps`: `(model_key, step_key)`.
- `context_section_master`: `(model_key, section_id)`.
- `section_presentation`: `(model_key, section_id)`.
- `standard_equipment_groups`: `(model_key, section_id)`.

Rows to backfill:

`runtime_steps`:
- For both `stingray` and `grand_sport`, copy the current ordered `STEP_ORDER`/`STEP_LABELS` exactly.
- `source`: `workbook_phase6`
- `active`: `True`
- `notes`: `Backfilled from model_configs.STEP_ORDER/STEP_LABELS for Phase 6 parity.`

`context_section_master`:
- For both `stingray` and `grand_sport`, copy current `CONTEXT_SECTIONS` exactly:
  - `sec_context_body_style`
  - `sec_context_trim_level`
- `context_type`: `body_style` / `trim_level`
- `active`: `True`
- `notes`: `Backfilled from model_configs.CONTEXT_SECTIONS for Phase 6 parity.`

`section_presentation`:
- Preserve existing Stingray `sec_cust_002` hidden row.
- Add Stingray display-order rows:
  - `stingray | sec_stri_001 | | | | | 30 | | | True | Backfilled from STINGRAY_SECTION_DISPLAY_ORDER_OVERRIDES.`
  - `stingray | sec_gsha_001 | | | | | 50 | | | True | Backfilled from STINGRAY_SECTION_DISPLAY_ORDER_OVERRIDES.`
  - `stingray | sec_gsce_001 | | | | | 51 | | | True | Backfilled from STINGRAY_SECTION_DISPLAY_ORDER_OVERRIDES.`
- Add Grand Sport label rows:
  - `grand_sport | sec_gsce_001 | Grand Sport Center Stripes | | | | | | | True | Backfilled from GRAND_SPORT_SECTION_LABEL_OVERRIDES.`
  - `grand_sport | sec_gsha_001 | Grand Sport Heritage Hash Marks | | | | | | | True | Backfilled from GRAND_SPORT_SECTION_LABEL_OVERRIDES.`
  - `grand_sport | sec_spec_001 | Special Edition | | | | | | | True | Backfilled from GRAND_SPORT_SECTION_LABEL_OVERRIDES.`
  - `grand_sport | sec_colo_001 | Color Combination Override | | | | | | | True | Backfilled from GRAND_SPORT_SECTION_LABEL_OVERRIDES.`
- Add section step ownership rows only for section IDs that still require config fallback because `section_master.step_key` is blank. Use the exact `SECTION_STEP_OVERRIDES` value in `step_key` and leave labels/display orders blank unless separately specified.
- Add standard-equipment rows for each `STANDARD_SECTIONS` entry for both models:
  - `standard_equipment_bucket`: `True`
  - `standard_equipment_group_type`: `trim_equipment` for `sec_1lte_001`, `sec_2lte_001`, `sec_3lte_001`; blank for other standard buckets unless tests establish another current behavior.
- Add `presentation_bucket` only where needed by tests; otherwise leave blank to avoid inventing new semantics.

`standard_equipment_groups`:
- Add rows for each `STANDARD_SECTIONS` entry for both models.
- `group_type`: `trim_equipment` for `sec_1lte_001`, `sec_2lte_001`, `sec_3lte_001`; otherwise blank.
- `default_open`: `True` for trim-equipment sections if it matches existing runtime behavior; otherwise blank.
- `canonical_rank` and `duplicate_group_key` may stay blank unless needed to preserve standard-equipment dedupe semantics.
- `active`: `True`.

Important: before writing migration constants, inspect current `section_master` rows. Do not duplicate step mappings already owned by `section_master.step_key` unless the row is needed for explicit presentation fields.

### 2. Extend metadata loaders with validated maps

Modify `scripts/corvette_form_generator/runtime_metadata.py`.

Add or adjust helpers:

```python
def keyed_section_presentation(wb, model_key: str) -> dict[str, dict[str, Any]]:
    return {row["section_id"]: row for row in load_section_presentation(wb, model_key)}


def presentation_bool(row: dict[str, Any], key: str, default: bool = False) -> bool:
    value = clean(row.get(key))
    if not value:
        return default
    return value.lower() in {"true", "yes", "1", "y"}


def load_body_style_display_order(
    wb,
    model_key: str,
    fallback_order: Mapping[str, int],
) -> dict[str, int]:
    # Preferred: use context_choice_copy or a future workbook table only if already present.
    # For this phase, keep fallback unless a workbook-owned source already exists.
```

Do not add a new workbook sheet for body style ordering in Phase 6 unless inspection shows an existing appropriate source. If no existing workbook-owned row can represent it cleanly, keep `BODY_STYLE_DISPLAY_ORDER` as fallback and document it as a residual Phase 6 risk.

Validation behaviors:
- Duplicate active `(model_key, section_id)` rows in `section_presentation` should produce a generator validation error or deterministic last-row refusal, not silent drift.
- Unknown `section_presentation.step_key` should produce a validation error if it is not in loaded runtime steps plus `standard_equipment`.
- Unknown standard-equipment section IDs should produce a validation warning/error depending on whether the section is referenced by source data.

### 3. Consume workbook runtime/context rows in Stingray generator

Modify `scripts/generate_stingray_form.py`.

Load metadata after workbook load:

```python
from corvette_form_generator.runtime_metadata import (
    load_context_sections,
    load_runtime_steps,
    load_section_presentation,
    presentation_bool,
)

runtime_steps = load_runtime_steps(
    wb,
    MODEL_CONFIG.model_key,
    MODEL_CONFIG.step_order,
    MODEL_CONFIG.step_labels,
)
context_sections = load_context_sections(
    wb,
    MODEL_CONFIG.model_key,
    MODEL_CONFIG.context_sections,
)
section_presentation_rows = load_section_presentation(wb, MODEL_CONFIG.model_key)
section_presentation = {row["section_id"]: row for row in section_presentation_rows}
```

Replace direct use of `CONTEXT_SECTIONS` for generated sections:

```python
section_rows = [dict(row) for row in context_sections]
```

Replace direct `STEP_ORDER`/`STEP_LABELS` step row generation:

```python
step_rows = [dict(row) for row in runtime_steps]
```

Then populate `section_ids` as today.

Replace `STINGRAY_SECTION_DISPLAY_ORDER_OVERRIDES` lookup with:

```python
presentation = section_presentation.get(section_id, {})
section_display_order = (
    intish(presentation.get("section_display_order"))
    if clean(presentation.get("section_display_order"))
    else intish(section.get("display_order"))
)
```

Replace section label source with presentation label fallback:

```python
section_name = clean(presentation.get("display_label")) or section.get("section_name", "")
```

Use `section_name` consistently in section rows, option rows, choices, and standard-equipment rows.

Replace `step_for_section()` calls so workbook `section_presentation.step_key` can override config fallback:

```python
presentation_step_key = clean(section_presentation.get(section_id, {}).get("step_key"))
section_step_key = presentation_step_key or section.get("step_key", "")
step_key = step_for_section(section_id, section_name, section_step_key)
```

Add `is_standard_section(section_id)`:

```python
def is_standard_section(section_id: str) -> bool:
    presentation = section_presentation.get(section_id, {})
    value = clean(presentation.get("standard_equipment_bucket"))
    if value:
        return value.lower() in {"true", "yes", "1", "y"}
    return section_id in STANDARD_SECTIONS
```

Use it for standard-equipment bucketing and `step_for_section` fallback. If `mapping.step_for_section()` remains shared, update its signature to accept a predicate or precomputed `standard_section_ids` from workbook presentation.

Emit `standard_equipment_group_type` on standard equipment rows:

```python
"standard_equipment_group_type": clean(
    section_presentation.get(section_id, {}).get("standard_equipment_group_type")
),
```

Keep generated field blank when metadata is absent so runtime fallback stays compatible.

### 4. Consume workbook presentation in Grand Sport inspection/draft path

Modify `scripts/corvette_form_generator/inspection.py`.

Load:

```python
section_presentation = keyed_section_presentation(wb, config.model_key)
runtime_steps = load_runtime_steps(wb, config.model_key, config.step_order, config.step_labels)
```

Apply in:
- `resolved_step_key()` by preferring `section_presentation[section_id].step_key` before `section_master.step_key` and config fallback.
- Section label generation by preferring `display_label` before `config.section_label_overrides` before `section_master.section_name`.
- Standard-equipment bucketing by preferring `standard_equipment_bucket` before `config.standard_sections`.
- Draft standard equipment rows by emitting `standard_equipment_group_type`.

Keep `config.section_label_overrides`, `config.section_step_overrides`, and `config.standard_sections` as fallbacks.

### 5. Runtime trim-equipment grouping uses generated metadata first

Modify `form-app/app.js`:

```js
function trimEquipmentRows() {
  return standardEquipmentRows().filter(
    (item) =>
      item.standard_equipment_group_type === "trim_equipment" ||
      (!item.standard_equipment_group_type && /LT Equipment$/.test(item.section_name || ""))
  );
}
```

This preserves legacy runtime behavior if older generated data lacks the new field.

### 6. Tests

Add/update tests in `tests/stingray-generator-stability.test.mjs`:
- Workbook headers exist for `runtime_steps`, `context_section_master`, `section_presentation`, `standard_equipment_groups`.
- Active `runtime_steps` rows exist for Stingray and Grand Sport for every current step in order.
- Active `context_section_master` rows exist for both body and trim context sections for both models.
- Active `section_presentation` rows own the three Stingray display-order overrides.
- Active `section_presentation` rows own the four Grand Sport label overrides.
- Active `section_presentation` rows own standard-equipment bucket metadata for every current `STANDARD_SECTIONS` ID.
- Generator source uses `load_runtime_steps()` and `load_context_sections()` and does not build `step_rows` directly from `STEP_ORDER`.
- Generator source uses `standard_equipment_group_type` in generated standard-equipment rows.

Add/update tests in `tests/stingray-form-regression.test.mjs`:
- Generated `form_steps`/`data.steps` order exactly matches current pre-Phase-6 order.
- Generated context sections/body and trim choices are unchanged.
- Stingray stripe/heritage-hash/center-stripe section display order remains unchanged.
- Trim standard equipment renders from `standard_equipment_group_type === "trim_equipment"` when present.
- A fixture or synthetic data test proves removing the metadata field falls back to the existing `/LT Equipment$/` regex.

Add/update tests in `tests/grand-sport-contract-preview.test.mjs` and/or `tests/grand-sport-draft-data.test.mjs`:
- Grand Sport display labels remain unchanged and are backed by workbook `section_presentation` rows.
- Grand Sport section placement remains unchanged.
- Grand Sport draft standard-equipment rows include `standard_equipment_group_type` for LT equipment rows.

If the existing tests already cover an assertion, prefer tightening them rather than adding redundant broad tests.

### 7. Regenerate and review diffs

Run:

```sh
.venv/bin/python scripts/migrations/populate_phase6_presentation_metadata.py
.venv/bin/python scripts/validate_workbook_package.py stingray_master.xlsx
.venv/bin/python scripts/generate_stingray_form.py
.venv/bin/python scripts/generate_grand_sport_form.py
```

Review:

```sh
git diff --stat
git diff -- scripts/generate_stingray_form.py scripts/corvette_form_generator/inspection.py scripts/corvette_form_generator/runtime_metadata.py scripts/corvette_form_generator/mapping.py form-app/app.js
git diff -- form-output/stingray-form-data.json form-app/data.js form-output/inspection/grand-sport-form-data-draft.json
```

Expected generated-data drift:
- Timestamps will change.
- `standard_equipment_group_type` may appear on standard-equipment rows.
- Otherwise generated order, choices, prices, rules, selections, context choices, and labels should remain behaviorally identical.

If generated choices, selected RPO behavior, prices, or dealer payload shape differ unexpectedly, stop and diagnose before proceeding.

## Validation plan

Targeted gates:

```sh
.venv/bin/python scripts/validate_workbook_package.py stingray_master.xlsx
.venv/bin/python scripts/generate_stingray_form.py
.venv/bin/python scripts/generate_grand_sport_form.py
node --test tests/stingray-generator-stability.test.mjs
node --test tests/stingray-form-regression.test.mjs
node --test tests/grand-sport-contract-preview.test.mjs
node --test tests/grand-sport-draft-data.test.mjs
node --test tests/multi-model-runtime-switching.test.mjs
```

Full current suite before handoff:

```sh
.venv/bin/python scripts/validate_workbook_package.py stingray_master.xlsx
.venv/bin/python scripts/generate_stingray_form.py
.venv/bin/python scripts/generate_grand_sport_form.py
node --test tests/stingray-form-regression.test.mjs
node --test tests/multi-model-runtime-switching.test.mjs
node --test tests/stingray-generator-stability.test.mjs
node --test tests/grand-sport-contract-preview.test.mjs
node --test tests/grand-sport-draft-data.test.mjs
node --test tests/grand-sport-rule-audit.test.mjs
```

Manual verification still required after implementation:
- Stingray model switch/default model.
- Body style order: coupe then convertible.
- Trim step and trim standard-equipment block.
- Paint and exterior appearance section order.
- Stripe/heritage hash/center stripe ordering.
- Wheels/calipers step.
- Interior color, seat belt, interior trim steps.
- Build download.
- Dealer submission modal validation and payload shape.
- Grand Sport model switch, display labels, and draft export labels.

## Rollback

Preferred rollback:
1. Revert Phase 6 source/runtime/test commit.
2. Restore workbook backup produced by `save_workbook_safely()` or set new Phase 6 workbook rows inactive.
3. Regenerate:
   ```sh
   .venv/bin/python scripts/generate_stingray_form.py
   .venv/bin/python scripts/generate_grand_sport_form.py
   ```
4. Run the full current suite.

Static deployment rollback if already deployed:
- Redeploy previous `form-app/index.html`, `form-app/app.js`, `form-app/styles.css`, and `form-app/data.js` artifact set.

## Handoff requirements after implementation

Report:
- What changed: source files, workbook sheets, generated artifacts, and behavior impact.
- What did not change: app behavior, visual structure, prices, selected RPO/export/dealer payload schemas, and Grand Sport production activation status.
- Gate results: every command above, or `not run` with reason.
- Manual verification still pending.
- Residual risks, especially any hardcode intentionally retained as a fallback for one release.
