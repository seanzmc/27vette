# 27vette

Developer workspace for the 2027 Corvette static order-form app. Live at `order.stingraychevroletcorvette.com`: Stingray, Grand Sport, and Z06 forms with customer build downloads and dealer submissions to Stingray Chevrolet. Agent conduct, source-of-truth boundaries, validation strategy, and handoff rules live in `AGENTS.md`; this file owns the overview, repository map, and commands.

## Current State

- Stingray, Grand Sport, and Z06 are live customer-facing forms; no frontend package install or build step.
- `form-app/data.js` exposes the multi-model registry at `window.CORVETTE_FORM_DATA` (default model `stingray`; `window.STINGRAY_FORM_DATA` remains a legacy alias for the Stingray dataset). Each model entry carries generated model data plus model-card image metadata from the workbook `asset_map` sheet.
- Runtime promotion is workbook-owned: `model_master`, `model_registry_promotion`, and `variant_master` decide which models reach the registry; `scripts/promote_model.py` applies promotion rows; registry generation embeds promoted `form-output/runtime/*-runtime-contract.json` verbatim.
- ZR1 and ZR1X have model-scoped workbook sheets but are unpromoted future models; their rows are inactive historical scaffolds needing a focused ingest reprocess before use as source truth, and they must not be promoted as part of another model's pass.
- Dealer submission posts to the WordPress endpoint `https://stingraychevroletcorvette.com/wp-json/corvette-build/v1/submit` with Cloudflare Turnstile — protected boundary, see AGENTS.md §6.
- Some Grand Sport/Z06 artifact names still carry draft/inspection wording from migration; inspect active registry data and tests before treating that wording as runtime status.

## Architecture

```text
stingray_master.xlsx -> generator/inspection scripts -> form-output/ artifacts
  -> form-app/data.js registry -> static browser runtime -> download / dealer submit
```

The workbook owns business rules and runtime metadata wherever it can represent them; scripts stay procedural and general; the runtime renders and evaluates the generated contract (boundary detail: AGENTS.md §3).

## Repository Map (agent-relevant surfaces)

```text
stingray_master.xlsx          canonical workbook (source of truth)
scripts/
  generate_form.py            model artifact generator (per --model)
  generate_registry.py        publishes promoted contracts to form-app/data.js
  promote_model.py            workbook-driven runtime promotion
  validate_workbook_schema.py schema + live-contract validation
  validate_workbook_package.py / repair_workbook_tables.py  package integrity / repair
  apply_workbook_changeset.py shared ChangeSet preview/approval/write CLI
  apply_workbook_ops.py       gated workbook writes from exported ops batches
  workbook_editor_server.py   localhost workbook review/edit UI
  ingest_wizard_server.py     localhost ingest wizard UI (raw order-guide intake)
workbook-manager/             React + FastAPI + SQLite workbook editor
                              (staged edits, SQL audit, gated sync; see its README)
  compare-generated-contracts.mjs  contract diff ignoring timestamps
  corvette_form_generator/    shared lib: config, workbook I/O, rules, pricing,
                              interiors, contract, registry, schema validation
form-output/                  generated artifacts (never hand-edit);
                              runtime/ = promoted contracts; inspection/ = opt-in review
form-app/                     index.html, styles.css, app.js + generated data.js
tests/                        node --test *.mjs + pytest gates
docs/, .hermes/plans/         active specs, reviews, ingest docs
Order-Guide_IngestPrompt.md   raw ingest workflow prompt
```

Other dirs (`product/`, `dist_updates/`, `archive/`, `backups/`, `visualizer/`) are reference/archive/visualizer surfaces — inspect only when a task names them. `visualizer/workbook-editor/intentional-differences.json` is the committed allowlist of intentional cross-model option differences (`status: intentional` suppresses; `pending-review` annotates); editing it is a normal file change, not a workbook write.

## Workbook Source Surfaces

Canonical workbook: `stingray_master.xlsx`.

Shared/Stingray source sheets: `model_master`, `model_registry_promotion`, `variant_master`, `section_master`, `stingray_options`, `stingray_ovs`, `rule_mapping`, `price_rules`, `rule_groups`, `rule_group_members`, `exclusive_groups`, `exclusive_group_members`, `color_overrides`, `lt_interiors`, `LZ_Interiors`, `PriceRef`, `asset_map`.

Runtime metadata/audit sheets: `model_workbook_sources`, `model_variants`, `model_interior_scope`, `interior_components`, `runtime_steps`, `context_section_master`, `context_choice_copy`, `section_presentation`, `order_summary_sections`, `step_order_summary_map`, `default_selection_rules`, `runtime_rule_exceptions`, `variant_option_overrides`, `rule_phrase_map`.

Model-scoped sheets (`grandSport_*`, `z06_*` active; `zr1_*`/`zr1x_*` inactive scaffolds): `<model>_{options, ovs, rule_mapping, price_rules, rule_groups, rule_group_members, exclusive_groups, exclusive_members, variant_overrides}`.

`category_master` is not active. Historical evidence sheets live in `archive/stingray_archive.xlsx`. Workbook `form_*` generated sheets are retired from routine workflow — edit source rows and regenerate.

## Generated Data Contract

Each model dataset: `dataset`, `variants`, `steps`, `sections`, `contextChoices`, `choices`, `standardEquipment`, `ruleGroups`, `exclusiveGroups`, `rules`, `priceRules`, `interiors`, `colorOverrides`, `defaultSelectionRules`, `validation`. Stingray additionally carries `runtimeRuleExceptions`. All promoted models carry workbook-owned `orderSummary` metadata (`sections`, `stepMap`) that the runtime reads instead of hardcoded grouping. Registry shape:

```js
window.CORVETTE_FORM_DATA = {
  defaultModelKey: "stingray",
  models: { stingray: { key, label, modelName, exportSlug, image_url, image_alt, image_fit, image_position, data }, grandSport: {...}, z06: {...} }
};
```

## Local App Run

Open `form-app/index.html` directly, or serve:

```sh
cd <repo-root>/form-app
../.venv/bin/python -m http.server 8000
```

When runtime behavior changes, manually verify: model switching, body/trim selection, required-step completion, option select/deselect, standard/included summaries, selected/auto-added RPO summaries, totals, build download, dealer modal validation, payload model scoping.

## Dependency Setup

```sh
cd <repo-root>
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Do not commit `.venv/`. Always run Python tooling with `.venv/bin/python` or the activated venv.

## Ingest Wizard Workflow

`scripts/ingest_wizard_server.py` serves the localhost-only five-function path for raw order-guide intake: intake/profile, target selection, canonical compilation, typed exception resolution, and immutable `workbook-changeset-1` emission. Saved current runs resume at their current stage. Historical broad-review and plan artifacts are GET-only evidence; their mutation routes return HTTP 410. The browser cannot approve or apply a ChangeSet and cannot run generation, publication, promotion, deployment, or dealer work. Run artifacts stay under `form-output/ingest-wizard/<run-id>/`; detail lives in `docs/ingest/`.

```sh
.venv/bin/python scripts/ingest_wizard_server.py [--port 8040]
```

The approved 2026-07-20 compounded-repair Deliverable 4.1 projection is a separate read-only report command; its scope and Checkpoint 1 stop are owned by `docs/ingest/7-20_compounded-repair-spec.md`:

```sh
PYTHONPATH=scripts .venv/bin/python -m corvette_form_generator.ingest.options_recovery_projection
```

After explicit Checkpoint 1 bulk approval, bind the approval to the existing reports and current workbook without regenerating either:

```sh
PYTHONPATH=scripts .venv/bin/python -m corvette_form_generator.ingest.options_recovery_projection --approve-checkpoint-1 --reviewer <name> --reviewed-at <ISO-8601>
```

## Workbook Editor Workflow

`scripts/workbook_editor_server.py` serves the fallback localhost-only UI for routine review/editing of `stingray_master.xlsx`; it derives models, sheet registries, schemas, and reference domains from the live workbook. Its obsolete embedded Ingest Review workflow is retired; raw ingest uses the separate wizard above.

```sh
.venv/bin/python scripts/workbook_editor_server.py [--port 8030] [--workbook <path>]
```

Open `http://127.0.0.1:8027/`. Review tab: `/api/lints` (informational structural lints; the batch validator remains the write authority) and `/api/compare` (cross-model option copy/section/order diff, majority vs deviator, ZR1/ZR1X excluded; intentional differences via the committed allowlist above).

Apply behavior: edits queue client-side as typed operations; only sheet families registered in `model_workbook_sources` are editable; adding an option requires OVS coverage for every active variant; Apply runs the full gate internally (batch validation, dry-run on temp copy, package + schema validation, `save_workbook_safely()` lock/mtime checks, backup, atomic replace, table-ref maintenance, `form-output/workbook-edit-log.jsonl` entry); warnings block until confirmed.

Shared ChangeSet operator path (preview is the default; approval never writes; write requires the exact bound preview and approval):

```sh
.venv/bin/python scripts/apply_workbook_changeset.py change-set.json --workbook stingray_master.xlsx --preview-out preview.json
.venv/bin/python scripts/apply_workbook_changeset.py change-set.json --workbook stingray_master.xlsx --approve <actor> --preview preview.json --approval-out approval.json
.venv/bin/python scripts/apply_workbook_changeset.py change-set.json --workbook stingray_master.xlsx --write --preview preview.json --approval approval.json --receipt-out receipt.json
```

The fallback editor still uses its existing typed-operation Apply path until Workbook Manager parity is proven in Phase 3; `scripts/apply_workbook_ops.py` remains only for that transition and is not an ingest continuation.

An Apply is only the workbook-write step — afterwards regenerate affected model artifacts, run the relevant gates below, and review diffs.

## Workbook Manager Workflow

`workbook-manager/` is a React (Vite) + FastAPI + SQLite editor for
`stingray_master.xlsx`: import into a normalized database with full
duplicate/unresolved-reference reporting, staged form-based edits with
batch validation and an append-only SQL audit trail, and workbook
synchronization exclusively through the existing
`editor_ops.apply_batch` → `save_workbook_safely()` gate (dry-run first,
explicit confirmation, automatic backup). Setup, run, and test commands:
`workbook-manager/README.md`. Tests: `tests/test_workbook_manager.py`
(add `WBM_SLOW_GATE=1` for the full dry-run/live-write gate tests).

## Workbook And Generator Workflows

Model refresh (from repo root, venv python):

```sh
.venv/bin/python scripts/generate_form.py --model <stingray|grand_sport|z06>
.venv/bin/python scripts/generate_registry.py
```

The Stingray run also writes compatibility outputs (`form-output/stingray-form-data.json/.csv`); all models write clean runtime contracts under `form-output/runtime/`. Add `--emit-inspection --inspection-output <dir>` for optional review artifacts. Generator runs never mutate `form-app/data.js` directly; `generate_registry.py` publishes the promoted registry.

Promotion verify/reapply (workbook-owned; only when promotion metadata changes):

```sh
.venv/bin/python scripts/promote_model.py --model <key> --write
```

then regenerate the model + registry and run that model's tests plus `multi-model-runtime-switching`.

## Validation

Fable 5 compounding loop scaffold:

```sh
.venv/bin/python scripts/validate_fable5_loop.py
```

The operating entrypoint is `fable5loop/README.md`. Use this gate after any change to the loop scaffold, run receipts, state file, or compounding skill.

Workbook schema gate:

```sh
.venv/bin/python scripts/validate_workbook_schema.py stingray_master.xlsx
```

Customer-facing option-sheet quality gate (all configured option sheets, including inactive scaffolds):

```sh
PYTHONPATH=scripts .venv/bin/python -m corvette_form_generator.options_sheet_quality \
  --workbook stingray_master.xlsx \
  --allowlist tests/fixtures/options-sheet-quality-allowlist.json
```

This gate is intentionally red on the unrepaired GSX/ZR1/ZR1X workbook. For the required pre-write proof, point the command or `OPTIONS_SHEET_QUALITY_WORKBOOK` pytest variable at the repaired temporary workbook; do not weaken the gate against the canonical source.

Workbook package integrity / repair (also run if Excel reports recovery):

```sh
.venv/bin/python scripts/validate_workbook_package.py stingray_master.xlsx
.venv/bin/python scripts/repair_workbook_tables.py stingray_master.xlsx
```

Test-to-surface map (run each with `node --test tests/<name>.test.mjs`):

| Surface | Tests |
|---|---|
| Stingray | `stingray-form-regression`, `stingray-generator-stability` |
| Grand Sport | `grand-sport-contract-preview`, `grand-sport-draft-data` |
| Z06 | `z06-contract-preview`, `z06-form-data-draft`, `z06-interior-accessory-cleanup`, `z06-performance-package-interactions`, `z06-runtime-rule-corrections` |
| Promotion / switching | `z06-runtime-promotion`, `multi-model-runtime-switching` |
| Workbook standardization | `workbook-schema-standardization`, `workbook-visual-copy-standardization` |

Python metadata gates:

```sh
.venv/bin/python -m pytest tests/test_model_config_metadata.py tests/test_promote_model.py tests/test_registry_promotion_metadata.py tests/test_schema_validation_metadata.py tests/test_rule_derivation.py -q
```

Full default validation = schema gate + all rows of the table + the pytest gate. Choose gates by changed surface per AGENTS.md §10.

## Workbook Safety

Close Excel before any script that writes `stingray_master.xlsx`; treat `~$stingray_master.xlsx` as a lock signal. Writes go through `save_workbook_safely()` and must be verified on disk — full rules in AGENTS.md §5.

## Roadmap

Keep moving model rules/defaults/pricing/presentation into workbook-authored tables; keep the three live models structurally consistent source-to-contract; complete ZR1/ZR1X source review before any promotion; retire draft/inspection naming once the promotion path is proven; manage image assets via workbook asset maps; simplify customer UX without losing ordering accuracy or dealer detail; strengthen promotion gates; reduce monolithic runtime logic as rules become fully data-owned.
