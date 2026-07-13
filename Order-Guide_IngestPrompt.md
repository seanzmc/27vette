# 27vette — GM order-guide ingest prompt

Edge raw-ingest workflow only: adding a model not in the form, or a broad GM order-guide refresh. Routine option/copy/pricing/rule/image/interior/metadata corrections go directly in canonical workbook source sheets plus normal gates (AGENTS.md §8 owns the boundary summary; pass detail lives in `docs/ingest/`).

## Contract and inputs

Current workflow docs: `docs/ingest/README.md` and `docs/ingest/canonical-row-compiler-exception-queue-design.md`. Older pass specs remain implementation/history records and do not override the current production direction.

Inputs: `<raw_export>.xlsx` (official GM order-guide export), `stingray_master.xlsx` (read-only schema/example reference), optional official price schedule. Never overwrite the raw export or the master workbook during preflight.

All ingest passes write only run-scoped transient artifacts under `form-output/ingest/<run-id>/`, `form-output/ingest-wizard/<run-id>/`, or `/tmp`. No pass may write `stingray_master.xlsx`, generated `form_*` sheets, other tracked `form-output/` outputs, or `form-app/data.js` unless a later approved apply pass explicitly allows it.

## Pass sequence and artifacts

- Pass A — interactive ingest wizard (current entry path): browser-first upload/choose → sheet-card profiling → user sheet-role confirmation → deterministic option/price parse → exact 1-to-1 price joins → read-only candidate table. Artifacts under `form-output/ingest-wizard/<run-id>/`: `session.json`, `sheet-profile.json`, `sheet-roles.json`, `option-candidates.json`, `price-rows.json`, `join-report.json`. No apply planning or workbook writes. Run: `.venv/bin/python scripts/ingest_wizard_server.py`.
- Production continuation — canonical-row compiler + typed exception queue: Milestones 0–2 are implemented. After target/comparator selection, the browser compiles every currently derivable canonical row, shows separate readiness gates, and asks only for finite typed exceptions whose outcomes the compiler can project completely; unsupported source/tooling gaps remain actionless blockers. Comparator evidence is corroborating/prefill evidence only. Mechanical `pass-c-3` projection is Milestone 3 and remains unapproved. No old plan or approval is writable, and no workbook write, generation, publication, promotion, or dealer authority is implied. Owning design: `docs/ingest/canonical-row-compiler-exception-queue-design.md`.
- Pass B — historical implemented decision-capture path (2026-07-05 through 2026-07-07): target-model selection, ten broad reviewer lanes, cross-model decision copy, and `decisions.json`. It remains available for historical/debug runs but is superseded for future production implementation by the compiler/exception-queue path. Do not extend its broad lane or cross-model-copy architecture.

Passes 0–5 below are the superseded legacy entry path, kept as parsing/review libraries and reference until later passes retire them explicitly. Their artifact paths are under `form-output/ingest/<run-id>/`.

- Pass 0 — CLI evidence profiler: `source-layout.json`, `variant-matrix.json`, `raw-rows.json`, `disclosure-links.json`, `checkpoint-report.md`.
- Pass 1 — CLI candidate normalizer: `candidate-{options,ovs,rules,price-rules,summary}.json`, `unresolved-review.{json,md}`. Candidates are not approved workbook rows.
- Pass 2 — review-decision exports: transient artifacts preserving candidate/evidence fingerprints and reviewer decisions; not workbook operations, never applied directly.
- Pass 3 — CLI/report-first expert interpretation/review reduction: aggregates Pass 1 rows into model/RPO review units, matches workbook context by RPO identity only, classifies duplicate source RPO rows and sheet coverage: `interpretation-summary.json`, `interpreted-options.json`, `review-queue.json`, `duplicate-rpo-report.{json,md}`, `source-sheet-coverage.{json,md}`, `blocked-interpretation.json`.
- Pass 4 — reduced Ingest Review UI: Pass 3 artifacts become the default browser review queue; Pass 1 candidates stay as drill-down/debug; exports versioned decisions; creates no workbook operations.
- Pass 5 — focused-model workbook-build review: after Pass 0 header/variant profiling, select target models before Pass 1/3 expansion. Default controlled scope `zr1,zr1x,z06` (ZR1/ZR1X primary, Z06 comparator only). Replaces broad all-model review and abstract decisions with workbook-destination lanes (option rows, OVS rows, relationship candidates, price gaps, duplicate-source classification, blocked extractor gaps). No dry-run apply planning until this review shape is usable.

- Pass C/D.2 — historical implemented decision-to-plan/dry-run path. D.2 run `20260709-003524-650cae` is immutable evidence that the plan mechanics execute but the output is not production-ready. Its `pass-c-2` plan, broad decisions, wholesale scaffold deletes, and approval are permanently non-writable under the selected production direction.

Canonical workbook writes require the compiler design's safety/readiness contract, a ready `pass-c-3` manifest projection, and a separate machine-scoped deployment-ready approval. No workbook write is approved by this prompt.

## Hard guardrails

1. Preserve raw values: original sheet names, row spans, RPO cells, descriptions, status symbols, footnotes, price candidates. Normalized fields sit alongside raw fields, never replacing them.
2. Do not invent data: never invent an RPO, price, name, section, rule, variant, or availability value. Blank/unresolved beats guessed; report ambiguity explicitly.
3. Keep generated/runtime surfaces untouched; do not promote a model to runtime as part of raw ingest.
4. Keep ZR1/ZR1X safe for reprocessing: inactive scaffold contents are not canonical product truth, but their existing IDs and incoming references are operational evidence. Never clear/recreate matched rows wholesale. Reconcile stable identities and block unresolved referenced deletes. A comparator (for example Z06) may corroborate or prefill a target relationship/group proposal, but it never independently supplies target product data, IDs, prices, defaults, copy, or scope.
5. Stop on invariant failure: no silent parser repair. Report the source tab, row/span, failing invariant, observed value, and the decision needed.

## Source layout expectations

GM exports commonly use numbered section tabs: row 1 model name; row 2 legend (`S`/`A`/`--`/`D`/`■`/`□`); row 3 headers (`Orderable RPO Code`, `Ref. Only RPO Code`, `Description`, variant columns); row 4+ data with occasional section-label rows. Do not hard-code this shape — validate each tab header before parsing and stop when it differs.

## Parsing rules

Variants: derive variant keys from source headers, never a hardcoded model set. Preserve multi-line headers and parse candidate pieces (body/model label, model code, trim). Candidate variant IDs must reconcile with `variant_master` and `model_variants` before apply.

Status: preserve every raw status cell exactly. Normalized values are limited to `standard`, `available`, `unavailable`, `unresolved`. Mapping: `S`→standard; `A`→available; `--` and dash variants→unavailable; `A/D` and spacing/case/hyphen variants→available automatically (preserve ADI nuance as evidence, not a required status-review decision); standalone `D`→available with dealer-install review; `■`→standard (flag equipment-group membership); `□`→standard or unresolved (flag upgradeable-group nuance); unknown→unresolved (stop or flag by severity). Footnote digits fused into status cells are captured separately and reconciled to disclosure text.

RPOs: preserve orderable and reference-only cells. A primary candidate RPO must appear in the source cells after known-format cleanup. RPO-like tokens longer than the valid format require review — no phantom RPOs from fused footnote digits. Standard-equipment rows may legitimately lack an RPO.

Descriptions/disclosures: preserve full raw text. The compiler may split customer-facing name, description, disclosure, and source-detail text only when the source structure/rules determine the split. Ambiguous copy becomes one typed exception before apply — never destroy source detail during preflight.

## Candidate normalized families

Emit candidates only for existing canonical families: model metadata (`model_master`, `variant_master`, `model_variants`, `model_workbook_sources`, `model_registry_promotion`); option universe (`*_options`, `*_ovs`); rules/relationships (`*_rule_mapping`, `*_rule_groups`, `*_rule_group_members`, `*_exclusive_groups`, `*_exclusive_members`, `default_selection_rules`); pricing (option `price`, `*_price_rules`, `PriceRef`, `interior_components`); interiors/color/components (`lt_interiors`, `LZ_Interiors`, `model_interior_scope`, `interior_components`, `color_overrides`); presentation/media (`section_master`, `section_presentation`, `runtime_steps`, `context_section_master`, `context_choice_copy`, `asset_map`, `order_summary_sections`, `step_order_summary_map`). Unmappable source items: report the gap, do not add a new permanent sheet or code path.

## Checkpoints

Per parsed tab: tab name, detected model-key candidates, source row span, in-scope rows read, candidate rows emitted, derived variant headers/IDs, sample raw + parsed row, flags/unresolved decisions.

Required invariants: source row conservation; no fabricated RPOs; complete variant-header parsing; raw status preservation; normalized status vocabulary limited to canonical values; footnote-marker integrity; price ambiguity preserved not guessed; skipped tabs listed with reason.

Final reconciliation: total in-scope source rows; candidate rows by family and per model; unresolved flags by type; skipped/out-of-scope tabs; pass/fail line. On fail, list the failing invariant and offending source rows — do not emit a clean apply plan.

## Canonical apply is a later pass

The approved apply path must: accept only a ready `pass-c-3` canonical manifest projection; default to temporary-workbook proof; require separate machine-readable dry-run and deployment-ready approvals; join by stable semantic IDs/keys, not row numbers; preserve existing workbook-authored values when source fields are blank; refuse blank option flags, identity churn, unresolved references, stale fingerprints, disabled schema validation, unknown warnings, or deployment blockers before live mutation; follow AGENTS.md §5; then regenerate affected model artifacts and run targeted schema/generator/runtime gates.
