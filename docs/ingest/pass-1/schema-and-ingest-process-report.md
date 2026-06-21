# Pass 1 — Schema and raw ingest process report

Date: 2026-06-19
Branch: `schema-ingestion-normalization`
Status: Report/spec only. No implementation approval implied by this document.

## Goal

Refine the workbook schema and raw-data processing workflow so new model ingestion is accurate, comprehensible, and aligned with the current normalized workbook contract.

Important operating boundary from Sean: raw data ingest is an edge task, not routine model maintenance. It should normally happen only when adding a model that is not already in the form, or when a broad GM/order-guide update requires refreshing existing model data at scale. Day-to-day corrections should continue to happen directly in canonical workbook source sheets and then regenerate artifacts.

## Executive conclusion

The current repo has a usable normalized workbook-to-runtime contract for promoted models, but it does not have an active raw order-guide ingestion pipeline on `main`.

Evidence:

- `stingray_master.xlsx` contains normalized model source sheets for Stingray, Grand Sport, and Z06.
- Runtime registry contains promoted models `stingray`, `grandSport`, and `z06` only.
- ZR1/ZR1X metadata and source sheets exist as inactive future scaffolds, but they are not runtime-promoted.
- Active scripts/tests do not reference `future_model_source_review`, `future_model_option_review`, `source_review`, or `option_review` as an executable current pipeline.
- `Order-Guide_IngestPrompt.md` exists, but it describes an older first-pass staging schema whose workbook sheets are not present in the current workbook.
- The archived ingest skill/files live under `archive-2026-05-29/...` and should not be treated as current workflow.

So the correct next move is not to resurrect the older review-sheet workflow wholesale. The smaller safe path is to document and guard the current normalized target schema first, then add a deliberately edge-scoped ingest workflow that emits auditable draft artifacts or a working-copy review sheet before any safe-save write to `stingray_master.xlsx`.

## Change type and risk

- Change type for this pass: docs/report only.
- Risk level for this pass: low. It writes only this Markdown report under `docs/ingest/pass-1/`.
- Risk level for the future implementation path: medium/high, because raw ingest can mass-write option, OVS, pricing, rules, and metadata rows if not constrained.

## Evidence inspected

### Git/worktree

- Branch: `schema-ingestion-normalization`
- Base tracking: `origin/main`
- Initial status: clean.

### Files inspected

- `AGENTS.md` project instructions already loaded in session context.
- `README.md`
- `Order-Guide_IngestPrompt.md`
- `docs/workbook-sheet-index.md`
- `docs/archive/completed-specs/model-metadata-schema-gate-repair-spec.md`
- `scripts/generate_form.py`
- `scripts/promote_model.py`
- `scripts/corvette_form_generator/model_configs.py`
- `scripts/corvette_form_generator/runtime_metadata.py`
- `scripts/corvette_form_generator/schema_validation.py`
- `scripts/corvette_form_generator/editor_ops.py`
- `tests/workbook-schema-standardization.test.mjs`
- `tests/test_model_config_metadata.py`
- `tests/test_registry_promotion_metadata.py`
- `tests/test_schema_validation_metadata.py`

### Searches performed

- Active script search for ingest/review staging symbols:
  - `future_model_source_review`
  - `future_model_option_review`
  - `source_review`
  - `option_review`
  - `price_sched_raw`
  - `raw_export`
- Result: no active Python script references in `scripts/`.
- Active test search for model source sheet coverage found current guards around normalized sheets and metadata, not an active raw ingest path.
- File search found archived ingest materials only under `archive-2026-05-29/...`, plus the root `Order-Guide_IngestPrompt.md`.

### Workbook/read-only probes

Workbook package and schema gates were run read-only:

```sh
.venv/bin/python scripts/validate_workbook_package.py stingray_master.xlsx
# status: valid, issue_count: 0

.venv/bin/python scripts/validate_workbook_schema.py stingray_master.xlsx
# status: valid, error_count: 0, warning_count: 0
```

No Excel lock file was present at probe time.

Current workbook summary from read-only `openpyxl` inspection:

- Sheet count: 76.
- Raw/review-like sheets present by name search: only `model_workbook_sources`; no `future_model_source_review`, no `future_model_option_review`, no `source_review`, no `option_review`.
- Runtime registry from `form-app/data.js`:
  - default model: `stingray`
  - model keys: `stingray`, `grandSport`, `z06`

Current `model_master` rows:

| model_key | registry_key | active | default_model | expected_variant_count | role |
|---|---|---:|---:|---:|---|
| `stingray` | `stingray` | true | true | 6 | promoted runtime model |
| `grand_sport` | `grandSport` | true | false | 6 | promoted runtime model |
| `z06` | `z06` | true | false | 6 | promoted runtime model |
| `zr1` | `zr1` | false | false | 4 | inactive future scaffold |
| `zr1x` | `zr1x` | false | false | 4 | inactive future scaffold |

Current `model_registry_promotion` rows:

| model_key | registry_key | promoted_to_runtime | artifact_path | active |
|---|---|---:|---|---:|
| `stingray` | `stingray` | true | `form-output/runtime/stingray-runtime-contract.json` | true |
| `grand_sport` | `grandSport` | true | `form-output/runtime/grand-sport-runtime-contract.json` | true |
| `z06` | `z06` | true | `form-output/runtime/z06-runtime-contract.json` | true |
| `zr1` | `zr1` | false | blank | false |
| `zr1x` | `zr1x` | false | blank | false |

Current `model_workbook_sources` role counts:

| model_key | role rows | active state |
|---|---:|---|
| `stingray` | 10 | active |
| `grand_sport` | 11 | active |
| `z06` | 11 | active |
| `zr1` | 10 | inactive |
| `zr1x` | 10 | inactive |

Current variant counts:

| model_key | total variants | active variants |
|---|---:|---:|
| `stingray` | 6 | 6 |
| `grand_sport` | 6 | 6 |
| `z06` | 6 | 6 |
| `zr1` | 4 | 0 |
| `zr1x` | 4 | 0 |

Current normalized model sheet row counts:

| Model | Options | OVS | Direct rules | Price rules | Rule groups | Rule group members | Exclusive groups | Exclusive members | Variant overrides |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Stingray | 243 | 1458 | 144 | 45 | 26 | 154 | 9 | 34 | 7 |
| Grand Sport | 242 | 1452 | 122 | 47 | 28 | 177 | 11 | 33 | 13 |
| Z06 | 243 | 1458 | 73 | 68 | 35 | 177 | 13 | 48 | 4 |
| ZR1 | 213 | 852 | no sheet | 0 | 2 | 29 | 4 | 10 | 0 |
| ZR1X | 214 | 856 | no sheet | 0 | 2 | 29 | 4 | 10 | 0 |

Note: `README.md` currently says each future model has the same nine-sheet shape, but this probe found no `zr1_rule_mapping` or `zr1x_rule_mapping` sheets on the current branch. That is not a runtime issue because ZR1/ZR1X are inactive; it is a documentation/process consistency item to address before using them as examples for a new-model ingest path.

## Current authoritative schema contract

The current normalized target is not a raw review matrix. It is the workbook source graph consumed by `generate_form.py --model <model>` and `generate_registry.py`.

### Model registry and promotion metadata

Owned sheets:

- `model_master`
- `model_registry_promotion`
- `model_workbook_sources`
- `model_variants`
- `variant_master`

Current code consumers:

- `runtime_metadata.load_model_metadata()` reads `model_master`, `model_workbook_sources`, and `model_variants`.
- `runtime_metadata.load_model_config_overrides()` applies workbook source/variant/model metadata over Python base config and fails fast on duplicate roles, unknown roles, registry-key drift, or variant-count mismatch.
- `registry_promotion` reads promotion rows to build `form-app/data.js` from current generation or runtime-contract artifacts.
- `promote_model.py` mutates promotion/model/variant metadata only with `--write` and safe-save behavior.

### Per-model source sheet families

The active normalized source shape is:

- `<model>_options` or Stingray `stingray_options`
- `<model>_ovs` or Stingray `stingray_ovs`
- `<model>_rule_mapping` or Stingray `rule_mapping`
- `<model>_price_rules` or Stingray `price_rules`
- `<model>_rule_groups` or Stingray `rule_groups`
- `<model>_rule_group_members` or Stingray `rule_group_members`
- `<model>_exclusive_groups` or Stingray `exclusive_groups`
- `<model>_exclusive_members` or Stingray `exclusive_group_members`
- `<model>_variant_overrides` or Stingray `variant_option_overrides`

The editor-side family metadata in `editor_ops.py` treats those as schema families with keys, basic types, enum domains, and references. That is useful as the current workbook schema map and should be preferred over inventing a second review taxonomy.

### Shared metadata/source sheets

Raw ingest should not bypass these existing owners:

- `section_master` owns section IDs, labels, selection modes, required flags, display order, standard behavior, and step keys.
- `section_presentation`, `runtime_steps`, `context_section_master`, `context_choice_copy`, `order_summary_sections`, and `step_order_summary_map` own runtime presentation metadata where workbook rows exist.
- `asset_map` owns runtime image/media URLs.
- `lt_interiors`, `LZ_Interiors`, `model_interior_scope`, `interior_components`, `PriceRef`, and `color_overrides` own interiors/component/color override data.
- `default_selection_rules`, `runtime_rule_exceptions`, `rule_phrase_map`, and variant override sheets own specific non-option-row behavior.

## Diagnosis

Root cause of current ingestion ambiguity: the repo has two different concepts with similar names:

1. The current normalized workbook source graph used by generation/runtime.
2. The older raw order-guide staging concept described by `Order-Guide_IngestPrompt.md` and archived ingest materials.

The current branch should treat (1) as authoritative. Raw ingest can be rebuilt as an edge workflow that lands into (1), but it should not become a parallel ongoing schema or a default maintenance route.

The most important design correction is process ownership:

- Raw import owns only source extraction, provenance, candidate parsing, and review evidence.
- Canonical workbook source sheets own approved product/runtime decisions.
- Generators own normalization/emission from canonical sheets.
- Runtime owns generic rendering/evaluation only.

## Recommended process contract

### Normal day-to-day workflow

Use this for routine corrections, visual/copy/rule fixes, and small model updates:

1. Identify the canonical workbook source sheet/row that owns the decision.
2. Edit that canonical sheet through the approved safe-save path or workbook editor.
3. Regenerate affected artifacts with `scripts/generate_form.py --model <model>` and `scripts/generate_registry.py` when promoted runtime data changes.
4. Run targeted gates.

Do not invoke raw ingest for routine row-level cleanup.

### Edge raw-ingest workflow

Use this only for:

- Adding a new model not already in the form.
- Performing a broad GM/order-guide refresh across existing models.
- Rebuilding a large model surface when the upstream source has materially changed.

Recommended stages:

1. **Raw source capture / provenance**
   - Input: GM order-guide Excel export or equivalent official source.
   - Output: run-scoped evidence artifacts under a dedicated output folder, not direct changes to `stingray_master.xlsx`.
   - Preserve raw values, variant headers, source sheets/spans, status symbols, footnotes, and price candidates.
   - Stop on parser invariants rather than guessing.

2. **Candidate normalization report**
   - Map raw rows to candidate canonical outputs:
     - model metadata
     - variants
     - option rows
     - OVS/status rows
     - direct rules
     - grouped rules
     - exclusive groups
     - price rules
     - interior/color/component data candidates
     - assets/presentation candidates if source-supported
   - Report unresolved items distinctly; do not write unresolved data into canonical sheets as if approved.

3. **Human/product review**
   - Review only the decisions raw parsing cannot own:
     - section placement
     - option ID stability
     - customer-facing copy split
     - display order
     - selectability/display behavior
     - pricing ambiguity
     - package/rule semantics
     - interior/component ownership
   - Keep the review output as a transient decision artifact unless a column already belongs in canonical workbook source sheets.

4. **Canonical workbook apply**
   - Produce a dry-run plan against the current workbook.
   - Use stable IDs/keys, not row numbers alone.
   - Preserve existing workbook-authored values when incoming raw/candidate values are blank.
   - Require `--write` for workbook changes.
   - Save only through `save_workbook_safely()` and refuse writes when Excel lock exists.

5. **Regeneration and validation**
   - Regenerate only affected model artifacts first.
   - Regenerate registry only when promoted runtime models change.
   - Run targeted tests and schema gates.
   - Diff-review generated artifacts for unintended churn.

## Required normalized output contract for any future ingest writer

A future ingest writer should produce/apply to the existing source graph, not invent another permanent workbook taxonomy.

Minimum canonical writes by layer:

### Model activation/scaffold layer

- `model_master`
- `model_variants`
- `variant_master`
- `model_workbook_sources`
- `model_registry_promotion`

Rules:

- New models start inactive/unpromoted unless explicitly approved for runtime promotion.
- Runtime promotion is separate from raw ingestion.
- Registry keys must match current `registry_model_key()` behavior, including `grand_sport` -> `grandSport`.

### Option universe layer

- `<model>_options`
- `<model>_ovs`

Rules:

- `option_id` is the stable join key.
- `rpo` remains text, including numeric-looking RPOs.
- blank price means not priced/unknown; numeric `0` means explicit zero.
- `selectable` and `active` are real Excel booleans where schema gates require them.
- `display_order` is numeric and unique per active section where guarded.
- OVS must have exactly the model variants expected for each active option unless intentionally scoped by approved metadata.

### Rule/relationship layer

- `<model>_rule_mapping`
- `<model>_rule_groups`
- `<model>_rule_group_members`
- `<model>_exclusive_groups`
- `<model>_exclusive_members`
- `default_selection_rules`
- `runtime_rule_exceptions` only when the behavior cannot fit canonical rules/groups.

Rules:

- Prefer exclusive groups, `requires_any`, and `excludes_any` for grouped behavior.
- Do not preserve dead duplicate direct excludes as long-term lifecycle rows.
- Avoid model/RPO-specific runtime exceptions when workbook rules can represent the behavior.
- Keep `runtime_action=replace` only for true default/replacement semantics until a separate modeling pass proves it can move.

### Pricing layer

- `<model>_price_rules`
- source option direct `price`
- `PriceRef` for interior/component references
- `interior_components` for component pricing linkage

Rules:

- Do not flatten ambiguous source prices into a single price.
- Do not restore standard-equipment prices as selectable option prices.
- Preserve zero-vs-blank semantics.
- Join candidate price rows by stable option identity/RPO and verify the current target row before writing.

### Interior/color/component layer

- `lt_interiors`
- `LZ_Interiors`
- `model_interior_scope`
- `interior_components`
- `color_overrides`

Rules:

- Do not force Color and Trim matrix tabs into option rows if they belong to interiors/color override processing.
- Use model scope rows rather than duplicating interior schemas.
- Do not delete component rows to make prices visually sum; component and interior total pricing have distinct owners.

### Presentation/media layer

- `section_master`
- `section_presentation`
- `runtime_steps`
- `context_section_master`
- `context_choice_copy`
- `asset_map`
- `order_summary_sections`
- `step_order_summary_map`

Rules:

- Runtime/presentation metadata should be workbook-owned for promoted models.
- Image URLs belong in `asset_map` and should continue using the approved hosted URL workflow, not direct bundling from raw source files.

## Proposed implementation sequence

### Pass 2 — Ingest contract and schema map doc

Change type: docs-only.

Exact files to add/change:

- Add `docs/ingest/pass-2/normalized-ingest-contract.md`.
- Optionally add/update `docs/ingest/README.md` as an index.

Scope:

- Turn this report into a concise standing contract.
- Include canonical column tables for each source family.
- Define raw-ingest edge triggers and non-goals.
- Document allowed transient artifacts versus canonical workbook sheets.

Validation:

```sh
git diff --check -- docs/ingest
rg -n "future_model_source_review|future_model_option_review|source_review|option_review" docs/ingest README.md AGENTS.md
```

Expected result: docs only; no workbook, generated artifact, runtime, or test changes.

### Pass 3 — Read-only schema inventory/validator plan

Change type: tests/validator spec first, then implementation after approval.

Candidate files:

- `scripts/corvette_form_generator/schema_validation.py`
- `tests/workbook-schema-standardization.test.mjs`
- `tests/test_schema_validation_metadata.py`
- possibly a small new read-only helper under `scripts/` if existing validator shape becomes too crowded.

Scope:

- Add explicit current-source-family invariants that are useful before any ingest writer exists:
  - model source role completeness for active promoted models.
  - option/OVS shape parity for active model source sheets.
  - no dangling OVS rows.
  - no active option without required OVS coverage.
  - inactive future scaffold checks kept separate from active runtime readiness checks.
- Consider a targeted warning/error for README/process drift such as missing inactive future rule-mapping sheets only if those sheets are intended to be part of future scaffold completeness. Do not infer this from stale docs alone.

Validation:

```sh
.venv/bin/python scripts/validate_workbook_schema.py stingray_master.xlsx
node --test tests/workbook-schema-standardization.test.mjs
.venv/bin/python -m pytest tests/test_schema_validation_metadata.py -q
```

### Pass 4 — Edge ingest preflight design

Change type: spec-only first; implementation only after approval.

Candidate outputs:

- A read-only preflight script or report generator that accepts a raw GM export and emits JSON/Markdown evidence without touching `stingray_master.xlsx`.
- It should not write canonical workbook sheets in its first implementation.

Required behavior:

- Parse source tabs and variant headers.
- Preserve raw status symbols and footnotes.
- Detect model/series layout, including mixed ZR1/ZR1X style sheets if present.
- Produce row-conservation and source-span reports.
- Emit candidate normalized rows as artifacts, not workbook writes.
- Stop on ambiguous headers/status symbols/price schedule structure.

Validation:

- Unit tests with synthetic workbook fixtures.
- No real workbook writes.
- No generated runtime artifacts.

### Pass 5 — Controlled canonical apply path

Change type: workbook writer/spec first; implementation only after raw preflight is proven.

Scope:

- Convert approved candidate rows into canonical workbook source edits.
- Default dry-run.
- Require `--write`.
- Safe-save only.
- Verify workbook on disk.
- Regenerate model artifacts.
- Keep promotion separate.

Validation depends on target model and whether promoted runtime data changes.

## Explicit non-goals for the ingest/schema path

- Do not promote ZR1/ZR1X to runtime as part of raw ingest.
- Do not recreate or edit retired workbook `form_*` generated sheets as ingest outputs.
- Do not hand-edit `form-output/*` or `form-app/data.js`.
- Do not create a permanent parallel review taxonomy when canonical workbook sheets already own the data.
- Do not use archived ingest skills/scripts as current source of truth.
- Do not derive row-level product data from press releases, hero cards, or sibling models when an order-guide export lacks the model.
- Do not change dealer submission endpoint, payload shape, or Turnstile behavior.
- Do not make raw ingest a routine maintenance requirement.

## Residual risks and open questions

1. `Order-Guide_IngestPrompt.md` is not aligned with the current workbook state because it references `future_model_source_review` and `future_model_option_review`, which are not active workbook sheets now. It should either be archived, rewritten, or replaced by a current `docs/ingest` contract in a follow-up docs pass.
2. `docs/workbook-sheet-index.md` appears stale against the current workbook probe: it says 81 sheets and lists row counts that differ from current read-only inspection. That is a documentation drift issue, not an ingest blocker, but it can confuse schema work.
3. README says ZR1/ZR1X have the full nine-sheet model-scoped shape, but current workbook lacks `zr1_rule_mapping` and `zr1x_rule_mapping` sheets. Decide whether future inactive scaffolds should remain minimal or be completed for comprehension before using them as new-model examples.
4. There is no current official raw GM export path/file named in the active workflow beyond the old prompt. A future preflight spec needs an explicit fixture/source path before implementation.
5. Existing validators are strong for current promoted runtime schema, but they are not yet an ingest preflight contract for raw source artifacts.

## Approval recommendation

Recommended next action: approve Pass 2 as a docs-only contract pass.

Recommended reasoning level for Sean/Codex prompt: high. The risk is not code complexity; it is source-of-truth drift. The next spec should be strict about keeping raw ingest edge-scoped and landing only into canonical workbook source families after review.

Pass 2 should not touch workbook data, generators, runtime files, or tests. Its job is to replace the old implicit ingest prompt with a current, normalized, workbook-first contract under `docs/ingest/`.
