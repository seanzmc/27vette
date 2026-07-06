# Ingest wizard end-to-end completion spec — Passes B–F (Grand Sport X, ZR1, ZR1X)

Date: 2026-07-05
Status: Approved 2026-07-05 (checkpoint 1, Sean). Open product decisions resolved same day — see "Open product decisions" at the end. Implementation may proceed pass by pass; checkpoints 2–5 remain live gates.
Recommended reasoning level for implementation agents: high.
Owner docs: this file (end-to-end program), `docs/ingest/README.md` (index), `Order-Guide_IngestPrompt.md` (contract summary).

## Purpose

Complete the raw order-guide ingest wizard from its implemented read-only entry path (Pass A) through to live runtime models. The finished system lets the reviewer, without writing code:

1. Ingest **Grand Sport X (GSX)**, **ZR1**, and **ZR1X** from the official GM order-guide export (`2027 Chevrolet Car Corvette Export (4) (1).xlsx`).
2. Review and resolve every human-owned decision (sections, groups, exclusive groups, relationships, ambiguous prices, copy splits, status nuances, presentation metadata).
3. Write approved data into `stingray_master.xlsx` through the existing workbook-safety tooling.
4. Regenerate model artifacts and run the matching gates.
5. Promote completed models into the runtime through the **same** workbook → generator → registry → runtime pipeline as Stingray, Grand Sport, and Z06 — no new pipeline, no runtime special-casing.

The standing division of responsibilities from `docs/ingest/README.md` carries through every pass: the script owns structure-derived parsing and deterministic transforms; the user owns business interpretation.

## Diagnosis — verified current state (2026-07-05)

Evidence inspected: `docs/ingest/pass-a/interactive-ingest-wizard-pass-a-spec.md` (implementation closeout), `scripts/ingest_wizard_server.py`, `scripts/corvette_form_generator/ingest/wizard/{session,profiler,parser,joiner}.py`, `scripts/corvette_form_generator/ingest/review_payload.py`, `scripts/corvette_form_generator/{registry_promotion,model_configs,model_generation,workbook,editor_ops}.py`, `scripts/{generate_form,generate_registry,promote_model,apply_workbook_ops}.py`, `tests/z06-runtime-promotion.test.mjs`, `tests/grand-sport-contract-preview.test.mjs`, `tests/test_registry_promotion_metadata.py`, read-only openpyxl probes of `stingray_master.xlsx` model-metadata sheets, and read-only probes of both raw exports.

### What exists

- **Pass A (implemented 2026-07-03)** — browser wizard at `scripts/ingest_wizard_server.py` (port 8040): choose/upload file → sheet cards → role confirmation → deterministic parse → exact 1-to-1 price join → read-only candidate table. Session states `profiled → roles_confirmed → parsed`, artifacts under `form-output/ingest-wizard/<run-id>/` (`session.json`, `sheet-profile.json`, `sheet-roles.json`, `option-candidates.json`, `price-rows.json`, `join-report.json`), all `schemaVersion: "pass-a-1"`, fail-closed transitions, source-file fingerprinting.
- **New raw export** (`2027 Chevrolet Car Corvette Export (4) (1).xlsx`, commit `dc9f442`): 28 sheets — `Equipment Groups|Interior|Exterior|Mechanical|Standard Equipment 1–5`, `Price Schedule`, `Color and Trim 1–2`. Contains Grand Sport X: `1YG07`/`1YG67` model codes in Price Schedule base-model rows and equipment-sheet variant headers, alongside `1YC` (Stingray), `1YE` (Grand Sport), `1YH` (Z06), `1YR` (ZR1), ZR1X codes. The older 23-sheet `..._RAW.xlsx` stays as reference.
- **Workbook model metadata** (read-only probe 2026-07-05):
  - `model_master`: `stingray`, `grand_sport`, `z06` active; `zr1`, `zr1x` inactive scaffolds (`expected_variant_count` 4). **No `grand_sport_x` row.**
  - `variant_master`: 6 inactive GSX variant rows already exist (`1lt_g07`…`3lt_g67`, with prices); 4 ZR1 (`1lz_r07/3lz_r07/1lz_r67/3lz_r67`) and 4 ZR1X (`1lz_s07/3lz_s07/1lz_s67/3lz_s67`) inactive rows.
  - `model_variants`, `model_workbook_sources`, `model_registry_promotion`: zr1/zr1x inactive rows present; **no GSX rows anywhere**.
  - ZR1/ZR1X sheet scaffolds exist (`zr1_options` … `zr1x_variant_overrides`) but their `model_workbook_sources` rows are **missing the required `rule_mapping_sheet` role** (and no `zr1_rule_mapping`/`zr1x_rule_mapping` sheets exist) — generation discovery (`model_configs.py`, required-role check) would fail even if activated as-is.
  - No `gsx_*`/`grandSportX_*` sheets exist.
- **Promotion pipeline (live, proven for Z06/Grand Sport)**:
  - `.venv/bin/python scripts/generate_form.py --model <key>` → `form-output/runtime/<export_slug>-runtime-contract.json`.
  - `.venv/bin/python scripts/promote_model.py --model <key> [--write]` — dry-run by default; write mode flips `model_master.active`, `model_registry_promotion.{promoted_to_runtime,artifact_path,artifact_type,active}`, `variant_master.active`, then re-reads and verifies on disk; refuses on Excel lock file; saves via `save_workbook_safely()`.
  - `.venv/bin/python scripts/generate_registry.py` — sole writer of `form-app/data.js`; validates exactly one default model, registry-key match with `model_master`, `runtime_contract`/`draft_artifact` need `artifact_path`; strips draft provenance via `assert_runtime_contract`/`live_contract_data`.
  - Gates: `tests/grand-sport-contract-preview.test.mjs` (preview shape, no `data.js` side effects), `tests/z06-runtime-promotion.test.mjs` (registry composition, draft-field stripping, model switching, model-scoped dealer payload), `tests/multi-model-runtime-switching.test.mjs`, `tests/test_registry_promotion_metadata.py`.
- **Workbook safety tooling**: `save_workbook_safely()` (`scripts/corvette_form_generator/workbook.py`) — lock-file refusal, mtime-change refusal, temp-file package validation + reload check, bool-type migration guard, timestamped backup, atomic move. Batch apply machinery exists: `scripts/apply_workbook_ops.py` → `editor_ops.apply_batch(workbook_path, batch, write=...)` (validate + dry-run default, `--write` to apply), already used by the workbook editor UI with edit logging to `form-output/workbook-edit-log.jsonl`.
- **Decision vocabulary (implemented, reusable)**: `review_payload.py` Pass 5 workbook-build actions (`create_option_row`, `verify_existing_option_row`, `create_ovs_rows`, `verify_status_matrix`, `create_relationship_candidate`, `classify_duplicate_source`, `defer_price_extractor`, `needs_product_decision`, …) and resolutions (`approved_for_plan`, `hold_for_question`, `not_needed`).

### Root cause / gap

Pass A ends at a read-only candidate table. Corrected-flow steps 6–8 (decision capture, relationship hints, decision export) and the apply/regenerate/promote chain exist only as vocabulary, legacy Pass 0–5 libraries, and manual CLI workflows. There is no wizard path from candidates to an approved workbook write, and GSX has no workbook scaffolding at all. ZR1/ZR1X scaffolds are explicitly non-canonical (`docs/ingest/README.md` current decisions; `Order-Guide_IngestPrompt.md` guardrail 4) and structurally incomplete (missing rule-mapping role).

Risk level: high overall (workbook writes + registry publication + runtime change), decomposed per pass below. Change class: mixed — tooling/UI/tests/docs (Passes B–C), workbook/data (Pass D), generated artifacts (Pass E), registry/runtime (Pass F).

## Model identity decisions (proposed; confirm at the Pass D approval gate)

| Model | `model_key` | `registry_key` | `export_slug` | sheet prefix | variants | interiors |
|---|---|---|---|---|---|---|
| Grand Sport X | `grand_sport_x` | `grandSportX` | `grand-sport-x` | `grandSportX_` | 6 (`1lt_g07`…`3lt_g67`, already in `variant_master`) | `lt_interiors` (LT trims) + `model_interior_scope` rows |
| ZR1 | `zr1` (existing) | `zr1` | `zr1` | `zr1_` | 4 (`1lz_r*`) — **must reconcile against export headers** | `LZ_Interiors` |
| ZR1X | `zr1x` (existing) | `zr1x` | `zr1x` | `zr1x_` | 4 (`1lz_s*`) — **must reconcile against export headers** | `LZ_Interiors` |

Naming follows the existing `grandSport_*`/`zr1_*` conventions. `expected_variant_count` must be set from reconciled export variant headers, not assumed; if the export shows a different trim/body matrix (e.g. 2LZ rows), that is a reviewer decision surfaced in Pass B, and `variant_master`/`model_variants` scaffolds are corrected in Pass D — never silently.

## Architecture

Extend the Pass A wizard surface in place. One server (`scripts/ingest_wizard_server.py`), one UI (`visualizer/ingest-wizard/`), new modules under `scripts/corvette_form_generator/ingest/wizard/`. Session state machine grows monotonically:

```text
profiled → roles_confirmed → parsed          (Pass A, unchanged)
  → models_selected                          (Pass B)
  → decisions_in_progress → decisions_complete   (Pass B)
  → plan_built → plan_approved               (Pass C)
  → applied                                  (Pass D)
  → regenerated                              (Pass E)
  → promoted                                 (Pass F, per model)
```

Every transition persists versioned JSON artifacts under `form-output/ingest-wizard/<run-id>/` (new `schemaVersion: "pass-b-1"`, `"pass-c-1"` etc.), each embedding the Pass A source fingerprint plus the fingerprint of the upstream artifact it derives from. Fail closed on any fingerprint mismatch, on state skips, and — for Pass D+ — on workbook mtime drift between plan and apply.

Legacy Pass 0–5 modules stay as libraries; Pass B reuses `review_payload.py` vocabulary and `model_selection.py` concepts rather than reinventing them. Retiring the legacy CLI entry points is an explicit non-goal here (candidate cleanup item after Pass F ships).

Hard guardrails from `Order-Guide_IngestPrompt.md` apply to every pass: preserve raw values alongside normalized fields; never invent an RPO, price, name, rule, variant, or availability value; blank/unresolved beats guessed; stop on invariant failure with source coordinates; keep ZR1/ZR1X scaffold rows non-canonical until the approved Pass D apply replaces them.

---

## Pass B — model scoping + decision capture (corrected-flow steps 6–7)

**Status: implemented 2026-07-05.** Changed files: `scripts/corvette_form_generator/ingest/wizard/{decisions,hints}.py` (new), `session.py` (states `models_selected → decisions_in_progress → decisions_complete`, Pass B store methods), `scripts/ingest_wizard_server.py` (7 new endpoints), `visualizer/ingest-wizard/*` (stages 4–5), `tests/{test_ingest_wizard_decisions,test_ingest_wizard_hints,test_ingest_wizard_server_pass_b}.py` + fixture master-workbook builder, `.claude/launch.json` (`ingest-wizard-dev` on 8041). Validation: 21 new tests green; full pytest 323 passed / 6 failed — all 6 pre-existing or receipt-in-progress, none from Pass B surfaces; browser proof against the 28-sheet export (1,915 candidates; GSX/ZR1/ZR1X selection with decided comparators; variant reconciliation GSX 6 export-only + ZR1/ZR1X 4=4 agree; all 10 lanes; section + presentation decisions saved; server-restart resume; zero console errors). Receipt: `fable5loop/runs/2026-07-05-pass-b-decision-capture/`.

**B.2 fine-tune (2026-07-06, Sean-directed, spec `docs/ingest/pass-b/pass-b2-review-finetune-spec.md`):** selection-scoped bulk actions (row checkboxes, checked-only buttons, explicit select-all) with batch-ID undo, per-row Clear, and audited decision deletion (`POST /decisions/delete`); script-owned copy splitting (`copy_split.py` `propose_copy_split`, flagged-exception queue, bulk accept, Pass C fallback rule); workbook reference index replacing the export-comparator concept (`workbook_option_reference`, per-row "In workbook …" lines, one-click use-reference-section, stage-4 "Reference model" relabel); plain-language label layer (stored vocabulary unchanged; decisions.json schemaVersion additively bumped to `pass-b-2`). Receipt: `fable5loop/runs/2026-07-06-pass-b2-implementation/`. **Pass B implementation is complete; Pass B closes at checkpoint 2 (Sean's real review-session sign-off).**

**B.1 usability correction (2026-07-06, Sean-directed):** raw-JSON payload inputs removed — every lane has purpose-built controls (price checkboxes/pickers, copy-split fields, relationship/exclusive/deferral forms, per-column editable presentation tables); bulk actions (section bulk-assign with source-section filter, accept-all-exact prices, bulk status confirm, bulk standard-equipment include/exclude); one-click relationship-hint prefill; cross-model decision copy (`POST /copy-decisions`: same-candidate on shared mixed sheets, RPO-identity otherwise, skip-don't-overwrite by default, `copiedFrom` provenance, presentation `model_key` swap). Receipt: `fable5loop/runs/2026-07-06-pass-b1-review-ux/`.

**Surface:** tooling/UI/tests/docs. Read-only toward workbook, generated artifacts, `form-app/`. Risk: medium (contract quality).

After `parsed`, the reviewer selects target models, then works decision lanes until every candidate in scope has a resolution.

### B1 — model selection

- New stage between candidates and review: detected model families (from sheet cards + variant headers) presented with per-family candidate counts; reviewer picks targets (`grand_sport_x`, `zr1`, `zr1x`) and optionally comparators (defaults per resolved decision 3: `grand_sport` for GSX, `z06` for ZR1/ZR1X; structure-check only — comparator candidates are never editable and never exported).
- Persists `model-selection.json` (mirrors Pass 5 semantics: fail closed on selection mismatch downstream).
- Variant reconciliation report per selected model: export variant headers vs `variant_master`/`model_variants` scaffold rows (match / missing-in-workbook / missing-in-export). Disagreements become mandatory `needs_product_decision` items.

### B2 — decision lanes (human-owned; the wizard presents, the reviewer decides)

Per selected model, lanes over the scoped candidates:

1. **Section assignment** — assign each orderable candidate to a `section_master` `section_id` (picker fed from the live workbook read-only; shows section → step mapping from `runtime_steps`/`step_key`). Bulk-assign by source section label (e.g. all rows under `Equipment Groups`) with per-row override.
2. **Price resolution** — ambiguous-join queue (`priceMatch: ambiguous`): pick one qualified price row, enter a reviewed value, or mark `defer_price_extractor`; missing-price queue (`priceMatch: none`): confirm zero-price/included, enter value with source note, or defer. Every resolution records the chosen source row's evidence.
3. **Exclusive groups** — create/name exclusive groups and assign members; suggested groupings from shared source-section + mutually-exclusive status patterns are hints only.
4. **Rule groups / relationships** — capture requires / includes / excludes / auto-add relations between candidates (and existing workbook options by RPO). Phrase-scan hints from description/disclosure text ("not available with", "requires", "included with", "deletes/replaces", …) rank suggestions; reviewer approves/edits/rejects each. Unresolvable text → `needs_product_decision`.
5. **Copy split** — split raw description into customer-facing name / description / disclosure / source-detail. Raw text always preserved verbatim in evidence.
6. **Status nuances** — flagged `A/D` (ADI), `■`/`□` group membership, unresolved status cells: confirm normalized value or mark unresolved-blocked.
7. **Duplicates / cross-sheet** — same RPO appearing across equipment sheets for one model: classify (same option / distinct by context) per `classify_duplicate_source`.
8. **Standard equipment** — ref-only/no-RPO rows: include as standard-equipment entries or exclude, per row or bulk.
9. **Interiors / colors / media** — the wizard does not parse `Color and Trim` sheets (unsupported in Pass A). Lane captures explicit deferrals: interiors scope rows to author manually in Pass C/D forms (`model_interior_scope`, `interior_components` references), `asset_map` needs, `color_overrides` needs. Nothing is invented; each deferral becomes a named checklist item that Pass C must either carry as a manual workbook op or explicitly leave open.
10. **Presentation metadata** — mandatory lane, per model, for the five model-scoped presentation sheets: `runtime_steps`, `section_presentation`, `context_section_master`, `order_summary_sections`, `step_order_summary_map`. All three target models currently have **zero rows** in all five (read-only probe 2026-07-05: per-`model_key` counts are stingray/grand_sport/z06 only), and `scripts/corvette_form_generator/runtime_metadata.py` `_require_workbook_metadata` **rejects fallback metadata for promoted models** (enforced for `runtime_steps` and `context_section_master`) — so `generate_form.py` fails after promotion for any model missing these rows. The wizard prefills each sheet's rows from a reviewer-chosen live template model (default `grand_sport` for GSX, `z06` for ZR1/ZR1X), shows them as editable per-row proposals, and the reviewer approves/edits/deletes each row. Prefill copies structure and copy text from existing workbook-authored rows (labeled as template-derived, source model recorded); it never fabricates product facts. Completeness for this lane means every one of the five sheets has an approved row set per model.

Decision records: `{candidateFingerprint, lane, action (Pass 5 vocabulary, extended only if a lane has no fit), payload, evidence, reviewer note, resolution (approved_for_plan | hold_for_question | not_needed), decidedAt}`; persisted incrementally to `decisions.json` (append-log + current-state snapshot) so a session survives restarts and re-parses invalidate decisions via fingerprints rather than silently keeping them.

### B3 — completeness gate

`decisions_complete` requires: every in-scope orderable candidate has section + price + status resolution or an explicit hold/defer; lane 10 has an approved row set in all five presentation sheets per model; every hold is listed in a blocking report. The UI shows per-lane progress. Export of an incomplete decision set is allowed only as an explicitly-labeled draft.

**Exit criteria:** decisions for all three models reach `decisions_complete` (holds allowed but enumerated); artifacts validate; no workbook/generated-surface diffs (`git status` clean for `stingray_master.xlsx`, `form-output/` tracked files, `form-app/`).

**Files:** `scripts/corvette_form_generator/ingest/wizard/decisions.py` (new), `scripts/corvette_form_generator/ingest/wizard/hints.py` (phrase-scan, new), `session.py` (states), `scripts/ingest_wizard_server.py` (endpoints: selection, lanes, decisions CRUD, progress), `visualizer/ingest-wizard/{index.html,wizard.js,wizard.css}` (stages 4–5), tests `tests/test_ingest_wizard_decisions.py`, `tests/test_ingest_wizard_hints.py`, server-test extensions; docs: this spec's status, `docs/ingest/README.md`, `Order-Guide_IngestPrompt.md` pass list.

**Validation:** new pytest suites (state machine extensions, fingerprint invalidation, lane completeness math, hint determinism — hints must be pure functions of candidate text); full `pytest tests/`; browser proof against the new export: select GSX+ZR1+ZR1X (+Z06 comparator), resolve a representative slice of every lane, restart server mid-session and resume, complete one model to `decisions_complete`.

---

## Pass C — decision export + apply plan (dry-run only)

**Status: implemented 2026-07-06.** Changed files: `scripts/corvette_form_generator/editor_ops.py` (additive: 11 global sheet families — model metadata + the five presentation sheets — reachable only via `GLOBAL_SHEET_FAMILIES`, plus a `create_sheet` op whose batch-created sheets validate later ops in the same batch; model registry and editor UI/lints resolution untouched, 69 editor regression tests green), `scripts/corvette_form_generator/ingest/wizard/plan_builder.py` (new: deterministic two-stage plan, coverage, report, markdown), `session.py` (`build_apply_plan`/`plan_detail`/`approve_plan`, states `plan_built`/`plan_approved`, plan invalidation on decision changes), server plan routes, UI stage 6 (plan report + approval), suites `test_ingest_wizard_plan.py` + `test_editor_ops_global_families.py`. Real-data proof (run `20260706-130958-1ea3ca`): all three models' decisions completed programmatically → plan 52 scaffolding + 4,473 data ops, zr1/zr1x clean-reprocess deletes recorded (213+852 / 214+856 rows), dry-run green incl. **schemaErrors=0** on the scratch workbook carrying all three models, 0 uncovered decisions, live workbook byte-identical, approval gate → `plan_approved`. Receipt: `fable5loop/runs/2026-07-06-pass-c-plan-builder/`. Known residual: stage-6 UI render verified via API payload + suites, not a full visual browser walk — cover in the next real review session.

**Surface:** tooling/UI/tests/docs. Still read-only toward the workbook. Risk: medium-high (this is where decisions become concrete workbook rows; errors here become Pass D writes).

### C1 — plan builder

Deterministic translation of `decisions.json` into an ordered workbook operation plan, `apply-plan.json`:

- **Model scaffolding ops (GSX):** create sheets `grandSportX_{options,ovs,rule_mapping,price_rules,rule_groups,rule_group_members,exclusive_groups,exclusive_members,variant_overrides}` cloned from the Grand Sport sheets' header rows (headers only, no data); add `model_master` row (`grand_sport_x`, inactive, `expected_variant_count` from reconciled variants); add `model_variants` rows (inactive); add `model_workbook_sources` rows for **all required roles** incl. `rule_mapping_sheet`, `color_overrides_sheet` → `color_overrides`, `interior_source_sheet` → `lt_interiors`; add `model_registry_promotion` row (unpromoted, inactive, next `display_order`); `model_interior_scope` rows per the Pass B interiors lane.
- **Scaffold repair ops (ZR1/ZR1X):** create missing `zr1_rule_mapping`/`zr1x_rule_mapping` sheets + `model_workbook_sources` `rule_mapping_sheet` rows; correct `variant_master`/`model_variants`/`expected_variant_count` per the Pass B variant reconciliation decisions.
- **Clean-reprocess ops (ZR1/ZR1X):** clear existing data rows in `zr1_*`/`zr1x_*` sheets (headers preserved) and rebuild entirely from approved decisions — scaffold rows are never merged with, only replaced. The plan records the cleared-row count and a snapshot reference for the diff report.
- **Data ops (all three):** `*_options` rows (RPO, name/description/disclosure from copy-split, section_id, price from price resolution), `*_ovs` rows per variant status, `*_rule_mapping`/`*_rule_groups`/`*_rule_group_members`/`*_exclusive_groups`/`*_exclusive_members` from relationship/exclusive decisions, `*_price_rules` from price-rule decisions, `default_selection_rules` rows where decided.
- **Presentation-metadata ops (all three):** approved lane-10 row sets written into `runtime_steps`, `section_presentation`, `context_section_master`, `order_summary_sections`, `step_order_summary_map` keyed by `model_key`. A plan with zero rows in any of these five sheets for a target model fails Pass C validation — this is the `runtime_metadata.py` promoted-model requirement, enforced at plan time instead of discovered at Pass F.
- Join identity is RPO + variant_id + sheet destination — never row numbers. Ops carry the decision fingerprint they derive from. Blank decision fields never overwrite non-blank existing workbook values (relevant to shared sheets like `model_interior_scope`, `color_overrides`).

### C2 — plan validation + dry run

- Structural validation against the live workbook read-only: referenced sections exist in `section_master`; referenced RPOs in relationships resolve within the plan or the workbook; variant_ids resolve to `variant_master`; no duplicate keys; every `approved_for_plan` decision maps to ≥1 op and every op maps back to a decision (bidirectional coverage report).
- Dry-run through `editor_ops.apply_batch(..., write=False)` (extended for sheet-creation ops if unsupported today — extension lands in `editor_ops` with its own tests, not a parallel writer).
- Reviewer-facing plan report in the wizard: per-sheet row counts, cleared-row counts, sample rows, unresolved holds carried over, and the exact op list export (`apply-plan.json` + human-readable `apply-plan.md`).
- `plan_approved` requires an explicit reviewer action in the UI recording who/when, stored in `plan-approval.json`. This is the product-approval gate for Pass D.

**Exit criteria:** plan builds deterministically from decisions (same input → same plan, no timestamps inside op payloads); dry-run passes with zero validation failures or the failures are listed and block approval; bidirectional coverage 100%; workbook still untouched.

**Files:** `scripts/corvette_form_generator/ingest/wizard/plan_builder.py` (new), `editor_ops.py` (sheet-creation/clear-rows op types if needed), `session.py`, `scripts/ingest_wizard_server.py` (plan endpoints), UI stage 6, `tests/test_ingest_wizard_plan_builder.py`, `tests/test_editor_ops_sheet_ops.py`; docs updates as in Pass B.

**Validation:** pytest suites incl. determinism and coverage invariants; full `pytest tests/`; dry-run against the live workbook with the real GSX/ZR1/ZR1X decision sets; `git status` clean on protected surfaces.

---

## Pass D — approved workbook apply

**Surface:** workbook/data (protected — AGENTS.md §5). Risk: high. **Human approval checkpoint: explicit approval of this spec's Pass D plus the in-wizard `plan_approved` record are both required before any `--write`.**

- Apply path: `apply_workbook_ops.py`-style invocation of `editor_ops.apply_batch(..., write=True)` wrapped by a new wizard endpoint/CLI `scripts/ingest_wizard_apply.py --run <run-id> [--write]`; dry-run by default, `--write` required, refuses unless session is `plan_approved` and the plan's workbook fingerprint (mtime_ns + sha256 captured at plan build) still matches the live file.
- All writes flow through `save_workbook_safely()`: Excel-lock refusal (`~$stingray_master.xlsx`), mtime-change refusal, temp-copy package validation, timestamped backup, atomic replace.
- Post-write verification (scripted, not claimed): reload workbook read-only; assert per-sheet row counts match the plan; assert a sampled set of ops landed cell-exact; write `apply-report.json` (+ append to `form-output/workbook-edit-log.jsonl`).
- Models remain **inactive/unpromoted** after apply — `model_master.active` stays False for all three; activation is Pass F's `promote_model.py` job. This keeps generation/registry behavior unchanged until promotion is explicitly run.
- Failure handling: any invariant failure aborts before `--write`; a failed safe-save leaves the original file untouched (temp-file protocol); the run stays in `plan_approved` for retry after cause analysis. Restoring from the timestamped backup is the rollback path and is documented in the apply report.

**Exit criteria:** `applied` state with `apply-report.json` showing zero mismatches; workbook verified on disk; backup exists; no `form-output/` or `form-app/` changes yet.

**Files:** `scripts/ingest_wizard_apply.py` (new), `session.py`, server endpoint + UI stage 7 (apply is allowed to be CLI-only if the UI button adds risk — decision at implementation, both paths must enforce the same gates), `tests/test_ingest_wizard_apply.py` (fixture workbooks, never the live one); docs updates.

**Validation:** apply tests on fixture workbooks (refusal cases: lock file, mtime drift, unapproved plan, fingerprint mismatch; success case: counts + cell samples); then the real apply, followed immediately by `pytest tests/test_editor_lints.py`-class schema/package validation and a manual diff review of the workbook (openpyxl-based sheet diff against the pre-apply backup, included in `apply-report.json`).

---

## Pass E — regeneration + model gates

**Surface:** generated artifacts + tests. Risk: medium. Uses only existing generator commands.

- Per model: `.venv/bin/python scripts/generate_form.py --model grand_sport_x` (then `zr1`, `zr1x`). Generation discovery only sees active models — `discover_generation_model_configs` iterates `_active_model_master_rows` (`scripts/corvette_form_generator/model_configs.py`), so with `model_master.active=False` these models are invisible to the generator. Pre-promotion verification therefore **must** run against a temporary activation in a **scratch copy of the workbook** (never the live file); the live activation happens only via `promote_model.py --write` in Pass F.
- Emit inspection artifacts (`--emit-inspection --inspection-output <scratch>`) for reviewer QA in the wizard: per-model counts (sections, steps, choices, variants), validation errors, unresolved notes.
- New node gates following the existing naming pattern, one per model, modeled on `tests/grand-sport-contract-preview.test.mjs`: `tests/grand-sport-x-contract-preview.test.mjs`, `tests/zr1-contract-preview.test.mjs`, `tests/zr1x-contract-preview.test.mjs` — assert contract shape, variant list, `read_only_preview` status, and **no `form-app/data.js` side effects**. Expected counts in these gates come from the applied workbook data, written after the first verified generation (same re-anchoring discipline as the 2026-07-05 stale-gate fix).
- Python gates: `pytest tests/test_registry_promotion_metadata.py` plus the generator/schema suites mapped in README's validation table for workbook writes.
- Diff review of `form-output/` changes; timestamp-only churn restored per the known gate-churn rule (`fable5loop/STATE.md`).

**Exit criteria:** three runtime contracts generate cleanly with zero validation errors (or errors triaged back to Pass B/C as decision gaps — loop, don't patch generated output); new preview gates green; no registry change yet.

**Files:** three new `*.test.mjs` gates, possible fixture updates, README validation-map rows, `session.py` `regenerated` state fed by a wizard "generation report" page; docs updates.

---

## Pass F — runtime promotion

**Surface:** workbook metadata + registry + runtime (protected: registry publication; dealer boundary must be re-verified). Risk: high. **Human approval checkpoint: per-model go/no-go before each `promote_model.py --write`.**

Per model, in the decided order (resolved decision 4: GSX first, then ZR1, then ZR1X):

1. `.venv/bin/python scripts/promote_model.py --model <key>` (dry-run) — review the reported plan in the wizard.
2. `.venv/bin/python scripts/promote_model.py --model <key> --write` — flips `model_master.active`, `variant_master.active`, `model_registry_promotion` (promoted, `artifact_path: form-output/runtime/<slug>-runtime-contract.json`, `artifact_type: runtime_contract`, `active`, existing `display_order`), verified on disk by the script.
3. `.venv/bin/python scripts/generate_form.py --model <key>` (fresh contract from the now-active model) then `.venv/bin/python scripts/generate_registry.py` (publishes `form-app/data.js`).
4. Gates: new `tests/grand-sport-x-runtime-promotion.test.mjs` / `tests/zr1-runtime-promotion.test.mjs` / `tests/zr1x-runtime-promotion.test.mjs` patterned exactly on `tests/z06-runtime-promotion.test.mjs` — registry composition (default model stays `stingray`), draft-provenance stripping, model switching + model-scoped order build, **model-scoped dealer submission payload**; update `tests/multi-model-runtime-switching.test.mjs` expectations; `pytest tests/test_registry_promotion_metadata.py`; full README validation map before declaring a model live.
5. Manual customer-workflow verification per AGENTS.md §7 (model switch, body/trim selection, option select/deselect incl. new exclusive groups and rules, summaries, totals, download, dealer modal scoping — no live dealer submission), desktop + mobile viewport.

Runtime JS/CSS changes are expected to be **zero** — the runtime is data-driven. Any point where the runtime appears to need GSX/ZR1/ZR1X-specific code is a workbook-data gap: loop back to Pass B/C. (Known watch item: model-family styling/assets via `asset_map` — media gaps are workbook data, handled as follow-up workbook edits, not JS.)

**Exit criteria (per model):** promotion gates green, registry contains the model with correct variants, dealer payload scoped, default model unchanged, manual verification recorded. **Program done when all three models are live** — or a model is explicitly deferred by the reviewer with its blocking decisions enumerated.

---

## Human approval checkpoints (summary)

| # | Gate | What is approved | Blocking |
|---|---|---|---|
| 1 | This spec | Passes B–F scope and boundaries | all implementation |
| 2 | Pass B completeness | decision sets per model (holds enumerated) | plan build |
| 3 | Pass C `plan_approved` | exact workbook op list (recorded in `plan-approval.json`) | any write |
| 4 | Pass D `--write` | the actual apply against the live workbook | apply |
| 5 | Pass F per-model go/no-go | promotion of each model to live runtime | registry publication |

## Source-of-truth decisions

- Product/business data: workbook only. Wizard artifacts are transient evidence and decision records, never a second source of truth; after Pass D the workbook rows are canonical and re-running ingest requires a fresh run-id and fresh decisions.
- Parsing/transform logic: Python under `scripts/corvette_form_generator/ingest/wizard/`; no model-specific business exceptions in code — GSX/ZR1/ZR1X differences must be expressible as workbook data.
- Apply machinery: extend `editor_ops` (one writer family), all saves via `save_workbook_safely()`.
- Runtime: consumes generated data unchanged.
- Docs: this file owns the B–F program; `docs/ingest/README.md` indexes it; `Order-Guide_IngestPrompt.md` gets a short pass-list update only (no duplicated prose).

## Companion-file impact

- `docs/ingest/README.md`, `Order-Guide_IngestPrompt.md` — updated per pass (status + pass list).
- `README.md` — command-table rows for new CLI entry points (`ingest_wizard_apply.py`) and new validation-map rows for the six new node gates.
- `AGENTS.md` §8 — inspected; summary stays valid (preflight read-only; apply is a separate approved pass). Update only if pass names/artifact paths in its pointer sentence go stale.
- Workbook editor server/UI — inspected-no-change expected (legacy Ingest Review tab untouched); `editor_ops` extensions must keep existing editor apply behavior green (`tests/test_editor_*`).
- `form-app/` runtime + dealer submission — untouched until Pass F, where changes are data-only (`data.js` via `generate_registry.py`); dealer endpoint/payload shape/security untouched, re-verified by promotion gates.
- `.claude/launch.json` — inspected; wizard server entry already exists.

## Constraints

No unrelated refactors. No new dependencies (stdlib server + openpyxl remain sufficient). Generated files never hand-edited. Workbook expresses all product rules. Dealer boundary preserved. Legacy Pass 0–5 retirement out of scope. Raw exports never modified. All transient artifacts stay under ignored `form-output/ingest-wizard/**` paths.

## Risks and non-goals

Risks:

- **Decision-to-op fidelity** (highest): a wrong translation writes wrong workbook rows. Mitigations: deterministic plan builder with bidirectional coverage checks, dry-run + human-readable plan review, post-apply cell verification, timestamped backup rollback.
- **Export drift**: the 28-sheet export's GSX/ZR1/ZR1X shapes may deviate from encoded expectations; Pass A confidence/skipped-row reporting surfaces drift; variant reconciliation makes disagreements explicit decisions.
- **Discovery/activation coupling** (Pass E): generating unpromoted models requires scratch-copy activation; must never leak activation into the live workbook outside `promote_model.py`.
- **Gate churn**: new preview/promotion gates join the known `generated_at`-churn class; restore discipline applies.
- **Review fatigue**: three models × 10 lanes is a large decision surface; per-lane progress, bulk actions with row-level override, and resumable sessions are required, not nice-to-have.

Non-goals: Color and Trim sheet parsing (deferral lane only); visualizer/media pipeline work; dealer-submission changes; legacy pass retirement; Stingray/Grand Sport/Z06 data refresh from this export (separate run); automated price-schedule refresh for existing models; any scheduled/cloud automation.

## Validation plan (roll-up)

Per pass as specified above; program-level before "done": full README validation map (node gates incl. three new preview + three new promotion gates, pytest suites, schema validation), manual multi-model customer-workflow verification, dealer boundary reported as preserved with evidence, and workbook backup + edit-log trail for every write. Every gate result reported with real output; gates not run listed with reasons.

## Open product decisions — resolved 2026-07-05 (Sean)

1. GSX naming set: **confirmed** — `grand_sport_x` / `grandSportX` / `grand-sport-x` / `grandSportX_*` prefix.
2. ZR1/ZR1X variant matrices: **confirmed 4 each** — 1LZ and 3LZ, coupe and convertible (matches existing `variant_master`/`model_variants` scaffolds). Pass B variant reconciliation still runs; any export-header disagreement still surfaces as a blocking decision rather than silently trusting either side.
3. Comparator model: **per target** — `grand_sport` for GSX, `z06` for ZR1/ZR1X (matches lane-10 template defaults).
4. Promotion order: **GSX first, then ZR1, then ZR1X** (staggered, per-model go/no-go at checkpoint 5 unchanged).
5. Media/`asset_map`: **not a go-live blocker** — placeholders acceptable, media filled in after promotion as routine workbook edits.
