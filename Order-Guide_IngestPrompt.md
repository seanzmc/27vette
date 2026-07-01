# 27vette — GM order-guide ingest prompt

Edge raw-ingest workflow only: adding a model not in the form, or a broad GM order-guide refresh. Routine option/copy/pricing/rule/image/interior/metadata corrections go directly in canonical workbook source sheets plus normal gates (AGENTS.md §8 owns the boundary summary; pass detail lives in `docs/ingest/`).

## Contract and inputs

Staged workflow docs: `docs/ingest/README.md` and `docs/ingest/pass-{0..5}/*.md`.

Inputs: `<raw_export>.xlsx` (official GM order-guide export), `stingray_master.xlsx` (read-only schema/example reference), optional official price schedule. Never overwrite the raw export or the master workbook during preflight.

All ingest passes write only run-scoped transient artifacts under `form-output/ingest/<run-id>/` (or `/tmp`). No pass may write `stingray_master.xlsx`, generated `form_*` sheets, other tracked `form-output/` outputs, or `form-app/data.js` unless a later approved apply pass explicitly allows it.

## Pass sequence and artifacts

All artifact paths below are under `form-output/ingest/<run-id>/`.

- Pass 0 — CLI evidence profiler: `source-layout.json`, `variant-matrix.json`, `raw-rows.json`, `disclosure-links.json`, `checkpoint-report.md`.
- Pass 1 — CLI candidate normalizer: `candidate-{options,ovs,rules,price-rules,summary}.json`, `unresolved-review.{json,md}`. Candidates are not approved workbook rows.
- Pass 2 — review-decision exports: transient artifacts preserving candidate/evidence fingerprints and reviewer decisions; not workbook operations, never applied directly.
- Pass 3 — CLI/report-first expert interpretation/review reduction: aggregates Pass 1 rows into model/RPO review units, matches workbook context by RPO identity only, classifies duplicate source RPO rows and sheet coverage: `interpretation-summary.json`, `interpreted-options.json`, `review-queue.json`, `duplicate-rpo-report.{json,md}`, `source-sheet-coverage.{json,md}`, `blocked-interpretation.json`.
- Pass 4 — reduced Ingest Review UI: Pass 3 artifacts become the default browser review queue; Pass 1 candidates stay as drill-down/debug; exports versioned decisions; creates no workbook operations.
- Pass 5 — focused-model workbook-build review: after Pass 0 header/variant profiling, select target models before Pass 1/3 expansion. Default controlled scope `zr1,zr1x,z06` (ZR1/ZR1X primary, Z06 comparator only). Replaces broad all-model review and abstract decisions with workbook-destination lanes (option rows, OVS rows, relationship candidates, price gaps, duplicate-source classification, blocked extractor gaps). No dry-run apply planning until this review shape is usable.

Canonical workbook writes require separate reviewed apply-planning/apply passes after expert interpretation and human/product review.

## Hard guardrails

1. Preserve raw values: original sheet names, row spans, RPO cells, descriptions, status symbols, footnotes, price candidates. Normalized fields sit alongside raw fields, never replacing them.
2. Do not invent data: never invent an RPO, price, name, section, rule, variant, or availability value. Blank/unresolved beats guessed; report ambiguity explicitly.
3. Keep generated/runtime surfaces untouched; do not promote a model to runtime as part of raw ingest.
4. Keep ZR1/ZR1X clean for reprocessing: current workbook rows are inactive historical scaffolds, not canonical expected output. Parse export ZR1/ZR1X data into fresh transient artifacts through Pass 5 model selection; compare only after a separate approved reprocess/apply spec. A comparator (e.g. Z06) verifies source structure but never supplies ZR1/ZR1X product data.
5. Stop on invariant failure: no silent parser repair. Report the source tab, row/span, failing invariant, observed value, and the decision needed.

## Source layout expectations

GM exports commonly use numbered section tabs: row 1 model name; row 2 legend (`S`/`A`/`--`/`D`/`■`/`□`); row 3 headers (`Orderable RPO Code`, `Ref. Only RPO Code`, `Description`, variant columns); row 4+ data with occasional section-label rows. Do not hard-code this shape — validate each tab header before parsing and stop when it differs.

## Parsing rules

Variants: derive variant keys from source headers, never a hardcoded model set. Preserve multi-line headers and parse candidate pieces (body/model label, model code, trim). Candidate variant IDs must reconcile with `variant_master` and `model_variants` before apply.

Status: preserve every raw status cell exactly. Normalized values are limited to `standard`, `available`, `unavailable`, `unresolved`. Mapping: `S`→standard; `A`→available; `--`→unavailable; `D`/`A/D`→available (flag ADI nuance); `■`→standard (flag equipment-group membership); `□`→standard or unresolved (flag upgradeable-group nuance); unknown→unresolved (stop or flag by severity). Footnote digits fused into status cells are captured separately and reconciled to disclosure text.

RPOs: preserve orderable and reference-only cells. A primary candidate RPO must appear in the source cells after known-format cleanup. RPO-like tokens longer than the valid format require review — no phantom RPOs from fused footnote digits. Standard-equipment rows may legitimately lack an RPO.

Descriptions/disclosures: preserve full raw text. Candidate parsing may split customer-facing name, description, disclosure, and source-detail text; the final split is a review decision before apply — never destroy source detail during preflight.

## Candidate normalized families

Emit candidates only for existing canonical families: model metadata (`model_master`, `variant_master`, `model_variants`, `model_workbook_sources`, `model_registry_promotion`); option universe (`*_options`, `*_ovs`); rules/relationships (`*_rule_mapping`, `*_rule_groups`, `*_rule_group_members`, `*_exclusive_groups`, `*_exclusive_members`, `default_selection_rules`); pricing (option `price`, `*_price_rules`, `PriceRef`, `interior_components`); interiors/color/components (`lt_interiors`, `LZ_Interiors`, `model_interior_scope`, `interior_components`, `color_overrides`); presentation/media (`section_master`, `section_presentation`, `runtime_steps`, `context_section_master`, `context_choice_copy`, `asset_map`, `order_summary_sections`, `step_order_summary_map`). Unmappable source items: report the gap, do not add a new permanent sheet or code path.

## Checkpoints

Per parsed tab: tab name, detected model-key candidates, source row span, in-scope rows read, candidate rows emitted, derived variant headers/IDs, sample raw + parsed row, flags/unresolved decisions.

Required invariants: source row conservation; no fabricated RPOs; complete variant-header parsing; raw status preservation; normalized status vocabulary limited to canonical values; footnote-marker integrity; price ambiguity preserved not guessed; skipped tabs listed with reason.

Final reconciliation: total in-scope source rows; candidate rows by family and per model; unresolved flags by type; skipped/out-of-scope tabs; pass/fail line. On fail, list the failing invariant and offending source rows — do not emit a clean apply plan.

## Canonical apply is a later pass

The approved apply pass must: default to dry-run and require `--write`; join by stable IDs/keys, not row numbers; preserve existing workbook-authored values when candidate fields are blank; follow the full workbook-safety rules in AGENTS.md §5 (lock refusal, `save_workbook_safely()`, on-disk verification); then regenerate affected model artifacts and run targeted schema/generator/runtime gates.
