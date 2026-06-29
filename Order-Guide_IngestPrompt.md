# 27vette — GM order-guide ingest prompt

Use this prompt only for the edge raw-ingest workflow: adding a model that is not already in the form, or performing a broad GM/order-guide refresh across existing models.

Do not use raw ingest for routine workbook maintenance. Day-to-day option, copy, pricing, rule, image, interior, or runtime-metadata corrections belong directly in canonical workbook source sheets, followed by the normal generator and validation gates.

## Current contract

The current staged ingest workflow is documented in:

- `docs/ingest/README.md`
- `docs/ingest/pass-0/ingest-wizard-source-profiler-spec.md`
- `docs/ingest/pass-1/candidate-normalizer-spec.md`
- `docs/ingest/pass-2/interactive-review-wizard-spec.md`
- `docs/ingest/pass-3/expert-interpretation-review-reduction-spec.md`
- `docs/ingest/pass-4/reduced-review-ui-spec.md`
- `docs/ingest/pass-5/focused-model-workbook-build-review-spec.md`

Raw ingest must produce transient evidence and candidate artifacts first. Pass 0 may write run-scoped evidence artifacts under `form-output/ingest/<run-id>/` or `/tmp`, but it must not write `stingray_master.xlsx`, generated workbook `form_*` sheets, tracked generated/runtime outputs elsewhere under `form-output/`, or `form-app/data.js` unless a later approved apply pass explicitly allows that.

## Inputs

- `<raw_export>.xlsx` — official GM Corvette order-guide Excel export or equivalent official source.
- `stingray_master.xlsx` — read-only reference for current canonical workbook schemas, existing active model examples, and metadata ownership.
- Optional price schedule/source material when provided by the same official source set.

Never overwrite the raw export or the live master workbook during ingest preflight.

## Required output sequence

Pass 0 is the CLI evidence profiler. It must write only run-scoped evidence artifacts outside the workbook, for example:

```text
form-output/ingest/<run-id>/source-layout.json
form-output/ingest/<run-id>/variant-matrix.json
form-output/ingest/<run-id>/raw-rows.json
form-output/ingest/<run-id>/disclosure-links.json
form-output/ingest/<run-id>/checkpoint-report.md
```

Pass 1 is the CLI candidate normalizer. It may write only run-scoped transient candidate/review artifacts outside the workbook, for example:

```text
form-output/ingest/<run-id>/candidate-options.json
form-output/ingest/<run-id>/candidate-ovs.json
form-output/ingest/<run-id>/candidate-rules.json
form-output/ingest/<run-id>/candidate-price-rules.json
form-output/ingest/<run-id>/candidate-summary.json
form-output/ingest/<run-id>/unresolved-review.json
form-output/ingest/<run-id>/unresolved-review.md
```

Candidate-normalizer artifacts are not approved workbook rows.

Pass 2 review-decision exports are also transient review artifacts. They must preserve candidate/evidence fingerprints and reviewer decisions, but they are not workbook operations and must not be applied directly.

Pass 3 is the CLI/report-first expert interpretation/review-reduction pass. It aggregates Pass 1 rows into model/RPO review units, matches workbook context by RPO identity only, classifies duplicate source RPO rows and source-sheet coverage, and writes only transient interpretation artifacts such as:

```text
form-output/ingest/<run-id>/interpretation-summary.json
form-output/ingest/<run-id>/interpreted-options.json
form-output/ingest/<run-id>/review-queue.json
form-output/ingest/<run-id>/duplicate-rpo-report.json
form-output/ingest/<run-id>/duplicate-rpo-report.md
form-output/ingest/<run-id>/source-sheet-coverage.json
form-output/ingest/<run-id>/source-sheet-coverage.md
form-output/ingest/<run-id>/blocked-interpretation.json
```

Canonical workbook writes require separate reviewed UI/review and apply-planning/apply passes after expert interpretation and human/product review.

Pass 4 is the reduced Ingest Review UI/server pass. It makes Pass 3 interpretation artifacts the default browser review queue when configured, preserves raw Pass 1 candidates as drill-down/debug, exports versioned review decisions, and still creates no workbook operations.

Pass 5 is the corrective focused-model/workbook-build review pass. It must run after Pass 0 has identified source headers and variant/model columns, then select the target models before Pass 1/3 candidate expansion. Default controlled development scope is `zr1,zr1x,z06`: ZR1 and ZR1X as primary incoming models, Z06 as a comparator only. Pass 5 must replace broad all-model review and abstract decisions with workbook-destination lanes such as option rows, OVS rows, relationship candidates, price gaps, duplicate-source classification, and blocked extractor gaps. Do not proceed to dry-run apply planning until this focused review shape is usable.

## Hard guardrails

1. Preserve raw values.
   - Keep original source sheet names, row spans, RPO cells, descriptions, status symbols, footnotes, and price candidates.
   - Add normalized candidate fields alongside raw fields; do not replace raw evidence.

2. Do not invent data.
   - Never invent an RPO, price, option name, section, rule, variant, or availability value.
   - Blank or unresolved is better than guessed.
   - Report ambiguity explicitly.

3. Keep generated/runtime surfaces untouched.
   - Do not hand-edit generated `form_*` sheets.
   - Do not hand-edit `form-output/*` runtime contracts.
   - Do not hand-edit `form-app/data.js`.
   - Do not promote a model to runtime as part of raw ingest.

4. Keep ZR1/ZR1X clean for reprocessing.
   - Current ZR1/ZR1X workbook rows are inactive historical scaffolds and should not be treated as canonical expected output.
   - If the raw export contains ZR1/ZR1X data, parse it into fresh transient artifacts through the focused Pass 5 model-selection workflow and compare only after a separate reprocess/apply spec approves the target mapping.
   - A comparator model such as Z06 may be used to verify source structure, but must not be used to invent ZR1/ZR1X product data.

5. Stop on invariant failure.
   - Do not silently repair parser failures.
   - Stop and report the source tab, source row/span, failing invariant, observed value, and the unresolved decision needed.

## Source layout expectations

The GM export may use numbered section tabs. A common tab shape is:

- Row 1: model name.
- Row 2: legend, such as `S = Standard`, `A = Available`, `-- = Not Available`, `D = ADI Available`, `■ = Included in Equipment Group`, `□ = Included in Equipment Group but upgradeable`.
- Row 3: headers such as `Orderable RPO Code`, `Ref. Only RPO Code`, `Description`, then one or more variant columns.
- Row 4+: data rows, with occasional section/context label rows.

Do not hard-code this shape as the only possible future input. Validate each tab header before parsing and stop when the shape differs.

## Variant parsing

Derive variant keys from source headers rather than hard-coding a model's complete set.

When a source header is multi-line, preserve the original header and parse candidate pieces:

```text
<body/model label>
<model code>
<trim>
```

Candidate variant IDs must later reconcile with `variant_master` and `model_variants` before canonical workbook apply.

## Status parsing

Preserve every raw status cell exactly before normalization.

Candidate normalized status values may only map to canonical OVS values or explicit unresolved review state:

- `standard`
- `available`
- `unavailable`
- `unresolved`

Common source mapping guidance:

| Raw symbol | Candidate normalized value | Required note |
|---|---|---|
| `S` | `standard` | none unless footnoted |
| `A` | `available` | none unless footnoted |
| `--` | `unavailable` | none unless footnoted |
| `D` / `A/D` | `available` | flag ADI/source nuance |
| `■` | `standard` | flag equipment-group membership |
| `□` | `standard` or unresolved candidate | flag upgradeable equipment-group nuance |
| unknown | unresolved | stop or flag based on severity |

Footnote digits fused into status cells must be captured separately and reconciled to source disclosure text.

## RPO parsing

Rules:

- Preserve orderable and reference-only source cells.
- Use a primary candidate RPO only when it appears in the source cells after known source-format cleanup.
- RPO-like tokens longer than the valid source RPO format require review; do not silently accept phantom RPOs caused by fused footnote digits.
- Standard-equipment rows may legitimately have no RPO.

## Description and disclosure parsing

Preserve the full raw description text.

Candidate parsing may split:

- customer-facing option name;
- customer-facing description;
- disclosure text;
- source detail/provenance text.

The final name/description/detail split is a review decision before canonical workbook apply. Do not destroy source detail during preflight.

## Candidate normalized families

A preflight run should emit candidates for the existing canonical source families only:

- model metadata: `model_master`, `variant_master`, `model_variants`, `model_workbook_sources`, `model_registry_promotion`;
- option universe: `*_options`, `*_ovs`;
- rules and relationships: `*_rule_mapping`, `*_rule_groups`, `*_rule_group_members`, `*_exclusive_groups`, `*_exclusive_members`, `default_selection_rules`;
- pricing: direct option `price`, `*_price_rules`, `PriceRef`, `interior_components`;
- interiors/color/components: `lt_interiors`, `LZ_Interiors`, `model_interior_scope`, `interior_components`, `color_overrides`;
- presentation/media: `section_master`, `section_presentation`, `runtime_steps`, `context_section_master`, `context_choice_copy`, `asset_map`, `order_summary_sections`, `step_order_summary_map`.

If a source item cannot be mapped to an existing canonical family, report the gap instead of adding a new permanent sheet or code path.

## Checkpoints

Emit a checkpoint after each parsed source tab and a final reconciliation report.

Per-tab checkpoint should include:

- tab name;
- detected model key candidates;
- source row span;
- number of in-scope rows read;
- number of candidate rows emitted;
- derived variant headers/IDs;
- sample raw row and parsed candidate row;
- flags and unresolved decisions.

Required invariants:

- source row conservation;
- no fabricated RPOs;
- complete variant-header parsing;
- raw status preservation;
- normalized status vocabulary limited to canonical values;
- footnote marker integrity;
- price ambiguity preserved rather than guessed;
- skipped tabs listed with reason.

Final reconciliation should include:

- total source rows in scope;
- total candidate rows by family;
- per-model candidate row counts;
- unresolved flag counts by type;
- skipped/out-of-scope tabs;
- pass/fail line.

On fail, list the failing invariant and offending source rows. Do not emit a clean apply plan.

## Canonical apply is a later pass

A later apply pass may convert approved candidates into workbook source edits only after review.

That apply pass must:

- default to dry-run;
- require `--write` for mutation;
- join by stable IDs/keys, not stale row numbers;
- preserve existing workbook-authored values when candidate fields are blank;
- refuse to write when Excel lock files exist;
- save through `save_workbook_safely()`;
- reopen and verify saved workbook cells on disk;
- regenerate affected model artifacts;
- run targeted schema/generator/runtime gates.
