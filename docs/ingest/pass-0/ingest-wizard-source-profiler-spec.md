# Pass 0 — CLI ingest wizard source profiler spec

Date: 2026-06-27
Branch: `ingest-wizard-pass0-spec`
Status: Implemented 2026-06-27.
Recommended reasoning level for implementation agent: high.

## Purpose

Start the new raw order-guide ingest wizard with a CLI-only, read-only source profiler. The goal is reliable evidence capture before candidate normalization or workbook apply exists.

This pass creates the deterministic foundation for later interactive review: source layout, exact cell coordinates, variant matrix parsing, disclosure linkage, and checkpoint reporting. It must not guess product decisions, create permanent staging sheets, write the canonical workbook, regenerate runtime artifacts, or promote any model.

## Diagnosis

Root cause / current gap:

The current root ingest prompt and `docs/ingest/pass-2/normalized-ingest-contract.md` correctly define raw ingest as an edge workflow and correctly route approved data into the normalized workbook source graph. They do not yet define an executable, wizard-ready evidence contract for the most failure-prone parts of ingest:

- exact source column locations and row spans;
- combined-model variant matrices such as `ZR1 and ZR1X`;
- raw status cells with disclosure suffixes such as `A1`, `A/D1`, `S1`, and `■1`;
- inline detail disclosures inside description text;
- non-standard source tabs such as `Price Schedule` and `Color and Trim`;
- source-to-workbook reconciliation states that avoid guessing section IDs, option IDs, prices, rules, or presentation behavior.

Evidence inspected before this spec:

- `Order-Guide_IngestPrompt.md` — current root prompt is normalized and safe, but remains prompt-level guidance rather than an executable source-profiler contract.
- `docs/ingest/pass-2/normalized-ingest-contract.md` — standing workbook-first ingest contract; its later-pass sequence currently names Pass 3/4/5, but the wizard needs this CLI Pass 0 foundation first.
- `stingray_master.xlsx` — current workbook has 65 sheets. Relevant canonical source families include model metadata, active per-model option/OVS/rule/price/group sheets, `default_selection_rules`, interiors/component/color sheets, and presentation/media metadata.
- `scripts/corvette_form_generator/model_configs.py` — `REQUIRED_GENERATION_SOURCE_ROLES` and `OPTIONAL_GENERATION_SOURCE_ROLES` define the current source-role contract. `variant_option_overrides_sheet` is an optional source role and must be explicitly handled as review-required when candidates touch that surface.
- `scripts/corvette_form_generator/schema_validation.py` — schema validator already checks model topology, source-role headers, source booleans/prices/RPO columns, and live-contract provenance leakage.
- `scripts/workbook_editor_server.py` — existing local workbook editor already derives models, per-model sheet registries, schemas, and reference domains from the workbook. Later UI work should reuse this metadata shape rather than inventing a parallel workbook map.
- `2027 Chevrolet Car Corvette Export_RAW.xlsx` — current raw export has 23 sheets. Most order-guide tabs use a row-3 matrix shape with columns 1–3 as `Orderable RPO Code`, `Ref. Only RPO Code`, and `Description`, then variant columns from column 4 onward. `ZR1 and ZR1X` tabs carry eight variant columns in one raw sheet. `Price Schedule` and `Color and Trim` use different layouts.
- `.venv/bin/python scripts/validate_workbook_schema.py stingray_master.xlsx` — current workbook schema validates with 0 errors and 0 warnings.

Risk level: medium. This pass is read-only, but it defines the contract later writer/review passes will rely on. A weak evidence model here would recreate the prior convolution problem.

Change type: tooling/docs/tests only. No workbook data, generated runtime data, browser runtime behavior, or dealer-submission behavior changes.

## Exact files and artifacts to change after approval

Expected implementation files:

- `scripts/order_guide_ingest_profiler.py` — new CLI entry point for read-only source profiling.
- `scripts/corvette_form_generator/ingest/__init__.py` — new ingest package marker, if a package is used.
- `scripts/corvette_form_generator/ingest/source_profiler.py` — source workbook layout detection, row extraction, variant/header parsing, disclosure capture, and artifact writer.
- `tests/test_order_guide_ingest_profiler.py` — Python tests for source-layout, variant matrix, status/disclosure parsing, and write-boundary guards.
- `tests/fixtures/ingest/` — compact fixture workbook(s) or fixture-builder code that represent the relevant raw export shapes without using the live workbook as expected truth.
- `Order-Guide_IngestPrompt.md` — update the root prompt to require the new Pass 0 artifact contract and to keep candidate/apply behavior deferred.
- `docs/ingest/README.md` — add the Pass 0 spec and status.
- `docs/ingest/pass-2/normalized-ingest-contract.md` — update the allowed sequence so it explicitly reads: Pass 0 evidence profiler -> candidate normalizer -> review UI -> controlled apply. This is mandatory before implementation can be called complete.
- `docs/ingest/pass-0/ingest-wizard-source-profiler-spec.md` — update to `Implemented` during the implementation pass with changed files, artifact paths, gates, residual risks, and next pass.

Expected generated/transient artifacts from running the CLI, not checked in unless explicitly approved:

```text
form-output/ingest/<run-id>/source-layout.json
form-output/ingest/<run-id>/variant-matrix.json
form-output/ingest/<run-id>/raw-rows.json
form-output/ingest/<run-id>/disclosure-links.json
form-output/ingest/<run-id>/checkpoint-report.md
```

Optional but acceptable if it keeps the contract cleaner:

```text
form-output/ingest/<run-id>/manifest.json
form-output/ingest/<run-id>/unresolved-review.md
```

## Proposed CLI contract

Command shape:

```sh
.venv/bin/python scripts/order_guide_ingest_profiler.py \
  --raw-export "2027 Chevrolet Car Corvette Export_RAW.xlsx" \
  --workbook stingray_master.xlsx \
  --run-id <run-id> \
  --output-dir form-output/ingest/<run-id>
```

Required behavior:

1. Read the raw export and canonical workbook only.
2. Refuse any flag or path that would write `stingray_master.xlsx`, `form-app/data.js`, generated workbook `form_*` sheets, promotion metadata, or tracked generated outputs under `form-output/` outside explicitly approved run-scoped ingest artifacts.
3. Create only the run-scoped ingest output directory and JSON/Markdown evidence artifacts.
4. Exit non-zero on parser invariant failure.
5. Print a concise checkpoint summary and the artifact directory.

No `--write` mode is allowed in Pass 0. Workbook apply belongs to a later approved pass.

## Artifact contracts

### `manifest.json` if emitted

Must include:

- raw export path;
- canonical workbook path;
- run id;
- generated timestamp;
- tool version or script name;
- artifact list;
- pass/fail status;
- invariant failures if any.

### `source-layout.json`

One entry per source sheet with:

- `source_sheet`;
- `sheet_type`: `matrix`, `price_schedule`, `color_trim`, `unknown`, or another explicitly documented read-only type;
- detected model label or model group label from the raw sheet;
- header row number;
- base columns with exact indexes and labels;
- variant matrix columns with exact indexes and raw headers;
- section/context rows and their row spans when detectable;
- skipped/out-of-scope reason if not parsed;
- invariant warnings/errors.

Rules:

- Do not hardcode tab names as the only source of truth. Use header detection and report shape mismatches.
- Do not treat `Price Schedule` or `Color and Trim` as option/OVS matrix tabs.
- Unknown shapes are allowed only as skipped evidence with explicit reason.

### `variant-matrix.json`

One entry per variant column with:

- `source_sheet`;
- `source_column_index`;
- `raw_variant_header`;
- parsed body style candidate;
- parsed model code candidate;
- parsed trim candidate;
- parsed target model candidate;
- parsed variant ID candidate;
- matched workbook `variant_master` row if found;
- matched `model_variants` membership if found;
- `resolution_status`: `matched`, `unmatched`, `ambiguous`, or `out_of_scope`;
- evidence notes.

Rules:

- Combined tabs such as `ZR1 and ZR1X` must split by variant header/model code, not by sheet title alone.
- Missing or ambiguous variant reconciliation blocks clean candidate output for that source sheet.
- Existing inactive ZR1/ZR1X scaffold rows are reference evidence only; they are not canonical expected output for parser success.

### `raw-rows.json`

One entry per in-scope source row with:

- `source_sheet`;
- `source_row_index`;
- source row span / section span;
- orderable RPO raw cell and coordinate;
- ref-only RPO raw cell and coordinate;
- full raw description and coordinate;
- parsed primary RPO candidate, if safe;
- section/context label evidence;
- raw status cells by variant column, with exact cell coordinate;
- parsed base status candidate (`standard`, `available`, `unavailable`, or unresolved);
- disclosure marker(s) from status cells;
- row-level parse flags;
- candidate target family hints only, not approved canonical rows.

Rules:

- Preserve raw values exactly alongside normalized candidates.
- RPO-like tokens longer than valid source tokens must be unresolved, not silently accepted.
- Standard-equipment rows with no RPO are valid raw evidence.
- Blank source cells remain blank; do not backfill from sibling rows or sibling models.

### `disclosure-links.json`

Must link raw status markers and detail text to source evidence:

- source sheet;
- source row;
- marker, e.g. `1`, `2`, `3`;
- status cells carrying the marker;
- description fragment or disclosure text carrying the marker;
- parsed phrase hints such as includes/requires/not-available/included-only-available, if detected;
- candidate relationship hint, if any;
- confidence/review state.

Rules:

- Disclosure parsing may suggest candidate rule families, but may not emit approved `rule_mapping`, rule group, exclusive group, default rule, price rule, or runtime exception rows.
- Multiple disclosures in one description must stay separate where possible.
- Ambiguous disclosure markers become review blockers.

### `checkpoint-report.md`

Must summarize:

- raw export path;
- workbook schema reference path;
- sheet count and parsed/skipped sheet counts;
- per-sheet row counts, variant column counts, and raw status vocabularies;
- combined-model sheet detection;
- unmatched/ambiguous variant headers;
- disclosure marker counts;
- unresolved flag counts by type;
- invariant pass/fail line;
- explicit statement that no workbook/generated/runtime files were written.

## Source-of-truth and ownership decisions

Decision: tooling/docs/tests for Pass 0.

Raw ingest owns only source extraction, evidence preservation, and read-only candidate hints. The canonical workbook remains the source of truth for approved product/runtime decisions. Generators remain the only path from workbook rows to runtime artifacts. Runtime JavaScript remains out of scope.

Workbook-owned target families must come from the current schema graph rather than a new permanent staging taxonomy:

- Model metadata: `model_master`, `variant_master`, `model_variants`, `model_workbook_sources`, `model_registry_promotion`.
- Option universe: `<model>_options`, `<model>_ovs`.
- Rules/relationships: `<model>_rule_mapping`, `<model>_rule_groups`, `<model>_rule_group_members`, `<model>_exclusive_groups`, `<model>_exclusive_members`, `default_selection_rules`, and rarely `runtime_rule_exceptions`.
- Variant presentation/availability overrides: `<model>_variant_overrides` / `variant_option_overrides_sheet`, review-required and not auto-expanded.
- Pricing: direct option `price`, `<model>_price_rules`, `PriceRef`, `interior_components`.
- Interiors/color/components: `lt_interiors`, `LZ_Interiors`, `model_interior_scope`, `interior_components`, `color_overrides`.
- Presentation/media: `section_master`, `section_presentation`, `runtime_steps`, `context_section_master`, `context_choice_copy`, `asset_map`, `order_summary_sections`, `step_order_summary_map`.

If a raw source item cannot map to an existing family, Pass 0 reports the gap. It does not create a new permanent workbook surface.

## Companion-file impact check

| Surface | Status for Pass 0 implementation | Notes |
|---|---|---|
| Workbook source sheets | inspected-no-change | CLI must read `stingray_master.xlsx` only. No workbook writes. |
| Tracked generated outputs under `form-output/` | not applicable | Pass 0 must not regenerate or edit any tracked generated outputs, including runtime contracts, root model data JSON/CSV, inspection output, or workbook edit logs. Run-scoped ingest smoke output should go to `/tmp` unless checked-in `form-output/ingest/<run-id>/` artifacts are explicitly approved. |
| `form-app/data.js` | not applicable | Registry publication is out of scope. |
| Runtime JS/CSS/HTML | not applicable | No browser behavior changes. |
| Dealer submission endpoint/payload | not applicable | No runtime/dealer path touched. |
| `Order-Guide_IngestPrompt.md` | update | Mandatory: replace the current preflight candidate-output list with the Pass 0 evidence-artifact list and defer candidate outputs to the later candidate-normalizer pass. |
| `docs/ingest/README.md` | update | Add Pass 0 spec/status and artifact overview. |
| `docs/ingest/pass-2/normalized-ingest-contract.md` | update | Mandatory: make the sequence explicit as Pass 0 evidence profiler -> candidate normalizer -> review UI -> controlled apply. Avoid rewriting historical diagnosis. |
| Tests | update | Add focused Python tests for profiler behavior and write-boundary guards. |
| Gate reminders / `AGENTS.md` | inspected-no-change | Current guidance already says raw ingest is transient and no workbook/generated writes without apply pass. Update only if implementation discovers contradictory guidance. |
| Profile/Codex/Hermes guidance | not applicable | No agent-guide behavior change required for CLI profiler. |

## Constraints repeated back

- CLI first; no UI/wizard tab in this pass.
- No workbook writes.
- No generated workbook `form_*` writes.
- No tracked `form-output/*` changes outside explicitly approved run-scoped ingest artifacts; prefer `/tmp` for manual-smoke output.
- No `form-app/data.js` writes.
- No model promotion.
- No runtime/dealer-submission changes.
- No new dependencies unless separately approved. Prefer Python standard library plus existing project dependencies already in `requirements.txt`.
- Do not guess product data, option IDs, section IDs, rules, prices, or variant membership.
- Use workbook metadata and schema as the reference for reconciliation, but do not treat inactive ZR1/ZR1X scaffold row counts/content as canonical expected output.
- Preserve detail disclosures, raw statuses, source coordinates, and variant headers as evidence.
- Existing workbook source graph is the target; do not resurrect `future_model_source_review`, `future_model_option_review`, `source_review`, or `option_review` as permanent sheets.
- Keep implementation small and reversible.

## Non-goals

- No interactive browser UI.
- No candidate apply manifest yet unless only emitted as a placeholder/read-only summary.
- No workbook mutation.
- No generation or registry publication.
- No price/rule/section auto-decision.
- No cleanup or retirement of existing ZR1/ZR1X workbook scaffold rows.
- No visualizer/image workflow changes.
- No routine-maintenance workflow changes.

## Risks

1. Parser overconfidence.
   - Mitigation: every parsed field carries raw source coordinates and a resolution status; unresolved beats guessed.

2. ZR1/ZR1X combined-sheet misrouting.
   - Mitigation: split by variant header/model code, not sheet title; test combined raw sheet fixtures.

3. Disclosure markers losing context.
   - Mitigation: separate `disclosure-links.json` with status-cell and description-fragment evidence.

4. New staging taxonomy creep.
   - Mitigation: artifacts are transient, run-scoped JSON/Markdown. Canonical workbook families stay unchanged.

5. Fixture brittleness against real GM export quirks.
   - Mitigation: use compact fixtures that encode shape classes, plus an optional manual smoke against `2027 Chevrolet Car Corvette Export_RAW.xlsx`.

6. Accidentally producing generated/runtime churn.
   - Mitigation: tests and handoff must include a guard over all tracked `form-output` files, `form-app/data.js`, and `stingray_master.xlsx`. Do not limit the guard to `form-output/runtime`.

## Validation plan

Before implementation edits:

```sh
git status --short --branch
.venv/bin/python scripts/validate_workbook_schema.py stingray_master.xlsx
```

During implementation:

```sh
.venv/bin/python -m pytest tests/test_order_guide_ingest_profiler.py
.venv/bin/python scripts/order_guide_ingest_profiler.py \
  --raw-export "2027 Chevrolet Car Corvette Export_RAW.xlsx" \
  --workbook stingray_master.xlsx \
  --run-id manual-smoke \
  --output-dir /tmp/27vette-ingest-manual-smoke
```

Post-implementation guards:

```sh
.venv/bin/python scripts/validate_workbook_schema.py stingray_master.xlsx
git diff --check -- scripts tests docs Order-Guide_IngestPrompt.md
git diff --exit-code -- stingray_master.xlsx form-app/data.js
git diff --exit-code -- $(git ls-files form-output)
git status --short -- form-output
```

The `git status --short -- form-output` output must be empty unless the pass explicitly approves checked-in `form-output/ingest/<run-id>/` evidence artifacts. Manual smoke output should normally use `/tmp` so the generated-output guard stays clean.

No Node runtime tests are required unless implementation unexpectedly touches generated/runtime/browser files, which should be treated as scope violation.

## Approval question

Approve Pass 0 implementation as scoped above: a CLI-only, read-only source profiler that emits run-scoped evidence artifacts and updates the ingest prompt/docs/tests, with no workbook/generated/runtime writes?

Recommended approval: yes, as the safest foundation before any candidate normalizer, review wizard, or canonical apply pass.

## Expected next pass after Pass 0

Pass 1 should be a candidate normalizer spec only after the source profiler artifacts are proven against the real raw export and compact fixtures. That pass should convert raw evidence into reviewable candidate families while still avoiding workbook writes.

A later Pass 2 can add an interactive review surface, preferably by reusing the workbook editor metadata/API patterns. Controlled workbook apply should remain a separate later pass with dry-run default and safe-save requirements.

## Implementation completion — 2026-06-27

Implemented on branch `ingest-wizard-pass0-spec` after approval and the final wording fixes.

Changed files:

- `scripts/order_guide_ingest_profiler.py` — new CLI entry point for the read-only source profiler.
- `scripts/corvette_form_generator/ingest/__init__.py` — new ingest package marker.
- `scripts/corvette_form_generator/ingest/source_profiler.py` — source-layout detection, variant reconciliation, raw-row/status preservation, disclosure-link extraction, output path guard, JSON/Markdown artifact writer.
- `tests/test_order_guide_ingest_profiler.py` — focused fixture tests for layout/variant/disclosure artifacts and generated-output path guards.
- `Order-Guide_IngestPrompt.md` — clarified Pass 0 may write run-scoped evidence under `form-output/ingest/<run-id>/` or `/tmp`, while tracked generated/runtime outputs remain blocked.
- `docs/ingest/README.md` — indexed the Pass 0 spec.
- `docs/ingest/pass-2/normalized-ingest-contract.md` — updated the sequence to Pass 0 evidence profiler -> Pass 1 candidate normalizer -> Pass 2 review UI -> Pass 3 controlled apply, and split evidence artifacts from later candidate artifacts.
- `docs/ingest/pass-0/ingest-wizard-source-profiler-spec.md` — closed this spec with implementation evidence.

Implemented behavior:

- CLI command:

```sh
.venv/bin/python scripts/order_guide_ingest_profiler.py \
  --raw-export "2027 Chevrolet Car Corvette Export_RAW.xlsx" \
  --workbook stingray_master.xlsx \
  --run-id manual-smoke \
  --output-dir /tmp/27vette-ingest-manual-smoke
```

- Emits:
  - `source-layout.json`
  - `variant-matrix.json`
  - `raw-rows.json`
  - `disclosure-links.json`
  - `manifest.json`
  - `checkpoint-report.md`
- Refuses output paths under tracked `form-output/` except `form-output/ingest/<run-id>/`.
- Treats `Price Schedule` and `Color and Trim` as non-matrix evidence-only layouts.
- Splits matrix variants by raw variant header/model code, including combined `ZR1 and ZR1X` sheets.
- Preserves raw status values, parsed base status, status disclosure markers, source coordinates, description disclosure markers, and phrase-level relationship hints.

Gate results:

```sh
.venv/bin/python -m pytest tests/test_order_guide_ingest_profiler.py
# 3 passed

.venv/bin/python scripts/order_guide_ingest_profiler.py \
  --raw-export "2027 Chevrolet Car Corvette Export_RAW.xlsx" \
  --workbook stingray_master.xlsx \
  --run-id manual-smoke \
  --output-dir /tmp/27vette-ingest-manual-smoke
# status: passed
# source_sheet_count: 23
# parsed_matrix_sheet_count: 20
# raw_row_count: 1964
# variant_column_count: 130
# disclosure_link_count: 1088
# invariant_failures: []

.venv/bin/python scripts/validate_workbook_schema.py stingray_master.xlsx
# status: valid, error_count: 0, warning_count: 0

git diff --exit-code -- stingray_master.xlsx form-app/data.js
git diff --exit-code -- $(git ls-files form-output)
git status --short -- form-output
# no output / no tracked generated-output changes
```

Residual risks:

- Pass 0 only emits evidence and lightweight relationship hints. It does not decide canonical option IDs, section IDs, prices, rules, or workbook rows.
- `Price Schedule` and `Color and Trim` are classified and preserved as layout evidence only; deeper price/interior candidate normalization belongs to Pass 1.
- Manual smoke output was written to `/tmp/27vette-ingest-manual-smoke`, not checked in.

Next pass:

Spec Pass 1 as a candidate normalizer over the Pass 0 artifacts. Keep it read-only, with candidate rows and unresolved review output only; no workbook apply or UI until the candidate artifact contract is reviewed.
