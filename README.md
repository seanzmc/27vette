# 27vette

Developer workspace for the 2027 Corvette static order-form app. Live at `order.stingraychevroletcorvette.com`: Stingray, Grand Sport, and Z06 forms with customer build downloads and dealer submissions to Stingray Chevrolet. Agent conduct, source-of-truth boundaries, validation strategy, and handoff rules live in `AGENTS.md`; this file owns the overview, repository map, and commands.

## Current State

- Stingray, Grand Sport, and Z06 are live customer-facing forms; no frontend package install or build step.
- `form-app/data.js` exposes the multi-model registry at `window.CORVETTE_FORM_DATA` (default model `stingray`; `window.STINGRAY_FORM_DATA` remains a legacy alias for the Stingray dataset). Each model entry carries generated model data plus model-card image metadata from the workbook `asset_map` sheet.
- Runtime promotion is workbook-owned: `model_master`, `model_registry_promotion`, and `variant_master` decide which models reach the registry; `scripts/promote_model.py` applies promotion rows; registry generation embeds promoted `form-output/runtime/*-runtime-contract.json` verbatim.
- Grand Sport X, ZR1, and ZR1X are unpromoted future models. Their active workbook registrations and retained runtime contracts remain available for focused rehabilitation, but they are not published in `form-app/data.js` and must not be promoted as part of another model's pass.
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
workbook-manager/             React + FastAPI + SQLite workbook editor
                              (staged edits, SQL audit, gated sync; see its README)
  compare-generated-contracts.mjs  contract diff ignoring timestamps
  corvette_form_generator/    shared lib: config, workbook I/O, rules, pricing,
                              interiors, contract, registry, schema validation
form-output/                  generated artifacts (never hand-edit);
                              runtime/ = retained contracts; registry publication is promotion-controlled;
                              inspection/ = opt-in review
form-app/                     index.html, styles.css, app.js + generated data.js
tests/                        node --test *.mjs + pytest gates
docs/, .hermes/plans/         active specs, reviews, and plans
```

Other dirs (`product/`, `dist_updates/`, `archive/`, `backups/`, `visualizer/`) are reference/archive/visualizer surfaces — inspect only when a task names them. `visualizer/workbook-editor/intentional-differences.json` is the committed allowlist of intentional cross-model option differences (`status: intentional` suppresses; `pending-review` annotates); editing it is a normal file change, not a workbook write.

## Workbook Source Surfaces

Canonical workbook: `stingray_master.xlsx`.

Shared/Stingray source sheets: `model_master`, `model_registry_promotion`, `variant_master`, `section_master`, `stingray_options`, `stingray_ovs`, `rule_mapping`, `price_rules`, `rule_groups`, `rule_group_members`, `exclusive_groups`, `exclusive_group_members`, `color_overrides`, `lt_interiors`, `LZ_Interiors`, `PriceRef`, `asset_map`.

Runtime metadata/audit sheets: `model_workbook_sources`, `model_variants`, `model_interior_scope`, `interior_components`, `runtime_steps`, `context_section_master`, `context_choice_copy`, `section_presentation`, `order_summary_sections`, `step_order_summary_map`, `default_selection_rules`, `runtime_rule_exceptions`, `variant_option_overrides`, `rule_phrase_map`.

Model-scoped sheets (`grandSport_*`, `z06_*` active; `zr1_*`/`zr1x_*` inactive scaffolds): `<model>_{options, ovs, rule_mapping, price_rules, rule_groups, rule_group_members, exclusive_groups, exclusive_members, variant_overrides}`.

`category_master` is not active. Historical evidence sheets live in `archive/stingray_archive.xlsx`. Workbook `form_*` generated sheets are retired from routine workflow — edit source rows and regenerate.

## Generated Data Contract

Each model dataset: `dataset`, `variants`, `steps`, `sections`, `contextChoices`, `choices`, `standardEquipment`, `ruleGroups`, `exclusiveGroups`, `rules`, `priceRules`, `interiors`, `colorOverrides`, `defaultSelectionRules`, `validation`. Stingray additionally carries `runtimeRuleExceptions`. All promoted models carry workbook-owned `orderSummary` metadata (`sections`, `stepMap`) in `data` and workbook-owned Vehicle Setup presentation copy in the registry-level `vehicleSetup` object. Registry shape:

```js
window.CORVETTE_FORM_DATA = {
  defaultModelKey: "stingray",
  models: { stingray: { key, label, modelName, exportSlug, image_url, image_alt, image_fit, image_position, vehicleSetup: { cardSubtitle, eyebrow, title, description, facts }, data }, grandSport: {...}, z06: {...} }
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

## Raw Order-Guide Ingest

The prior ingest wizard/compiler workflow is retired and has no supported command. Its code was removed because its imported data was not trustworthy enough to remain an executable workspace path. Historical prompts, plans, and reports are archived under `docs/archive/retired-ingest/2026-07-23/`; they are evidence, not current procedure. A future raw-source intake workflow requires a new approved design.

## Workbook Editor Workflow

`scripts/workbook_editor_server.py` serves the fallback localhost-only UI for routine review/editing of `stingray_master.xlsx`; it derives models, sheet registries, schemas, and reference domains from the live workbook. Its obsolete embedded Ingest Review workflow remains retired.

```sh
.venv/bin/python scripts/workbook_editor_server.py [--port 8030] [--workbook <path>]
```

Open `http://127.0.0.1:8027/`. Review tab: `/api/lints` (informational structural lints; the batch validator remains the write authority) and `/api/compare` (cross-model option copy/section/order diff, majority vs deviator, ZR1/ZR1X excluded; intentional differences via the committed allowlist above).

Apply behavior: edits queue client-side as typed operations; only sheet families registered in `model_workbook_sources` are editable; adding an option requires OVS coverage for every active variant; Apply runs the full gate internally (batch validation, dry-run on temp copy, package + schema validation, `save_workbook_safely()` lock/mtime checks, backup, atomic replace, table-ref maintenance, `form-output/workbook-edit-log.jsonl` entry); warnings block until confirmed.

Shared ChangeSet operator path (preview is the default; approval never writes; write requires the exact bound preview and approval). This is the approved target write contract for Workbook Manager; there is no current non-ingest producer until the Manager implements its later passes:

```sh
.venv/bin/python scripts/apply_workbook_changeset.py change-set.json --workbook stingray_master.xlsx --preview-out preview.json
.venv/bin/python scripts/apply_workbook_changeset.py change-set.json --workbook stingray_master.xlsx --approve <actor> --preview preview.json --approval-out approval.json
.venv/bin/python scripts/apply_workbook_changeset.py change-set.json --workbook stingray_master.xlsx --write --preview preview.json --approval approval.json --receipt-out receipt.json
```

The fallback editor still uses its existing typed-operation Apply path until Workbook Manager parity is proven in Phase 3; `scripts/apply_workbook_ops.py` remains only for that transition.

An Apply is only the workbook-write step — afterwards regenerate affected model artifacts, run the relevant gates below, and review diffs.

## Workbook Manager Workflow

`workbook-manager/` is a React (Vite) + FastAPI + SQLite editor for
`stingray_master.xlsx`. It is currently **read-only / provisional**: a first
import into an empty projection is allowed, replacement re-import is contained,
and every `POST /api/sync` request with `write=true` is refused. Dry-run sync,
browsing, history, and verified-projection disposable comparison export remain
available; generated-artifact and publication state are not inferred. The
workbook remains canonical. Setup, current containment behavior, and test
commands: `workbook-manager/README.md`. Focused tests:
`tests/test_workbook_manager_catalog.py`,
`tests/test_workbook_manager_import_projection.py`, and
`tests/test_workbook_manager.py`.

## Workbook And Generator Workflows

Model refresh (from repo root, venv python):

```sh
.venv/bin/python scripts/generate_form.py --model <model_key>
.venv/bin/python scripts/generate_registry.py
```

`<model_key>` must be active and complete in workbook-owned `model_master`, `model_workbook_sources`, and `model_variants` metadata. The Stingray run also writes compatibility outputs (`form-output/stingray-form-data.json/.csv`); all models write strictly validated runtime contracts under `form-output/runtime/`. Add `--emit-inspection --inspection-output <dir>` for optional review artifacts. Generator runs never mutate `form-app/data.js` directly; `generate_registry.py` validates every selected retained contract before publishing the promoted registry.

For isolated candidate validation, copy/freeze the workbook first and bind every output to a temporary root:

```sh
.venv/bin/python scripts/generate_form.py --model <model_key> \
  --workbook /tmp/stingray_master.snapshot.xlsx \
  --output-root /tmp/27vette-candidate
```

This command exits nonzero and writes no model artifacts when source assembly or strict runtime-contract validation fails. A successful single-model run is not registry or browser release-readiness proof.

Promotion verify/reapply (workbook-owned; repeat `--model` to validate and write one atomic multi-model batch):

```sh
.venv/bin/python scripts/promote_model.py --model <key> [--model <key> ...]
.venv/bin/python scripts/promote_model.py --model <key> [--model <key> ...] --write
```

The first command is the no-write preflight/proposal. Run `--write` only after the exact promotion is approved; the writer validates a scratch candidate before replacement and restores its backup if post-save verification fails. Then regenerate each promoted model + registry and run those models' tests plus `multi-model-runtime-switching`.

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

The gate is required green on the canonical workbook. During a reviewed pre-write repair, point the command or `OPTIONS_SHEET_QUALITY_WORKBOOK` pytest variable at the repaired temporary workbook first; never weaken the gate to force a pass.

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
.venv/bin/python -m pytest tests/test_generation_safety.py tests/test_generate_form_model_discovery_cli.py tests/test_runtime_contract_builder.py tests/test_model_config_metadata.py tests/test_promote_model.py tests/test_registry_promotion_metadata.py tests/test_schema_validation_metadata.py tests/test_rule_derivation.py -q
```

Full default validation = schema gate + all rows of the table + the pytest gate. Choose gates by changed surface per AGENTS.md §10.

## Workbook Safety

Close Excel before any script that writes `stingray_master.xlsx`; treat `~$stingray_master.xlsx` as a lock signal. Writes go through `save_workbook_safely()` and must be verified on disk — full rules in AGENTS.md §5.

## Roadmap

Keep moving model rules/defaults/pricing/presentation into workbook-authored tables; keep the three live models structurally consistent source-to-contract; complete ZR1/ZR1X source review before any promotion; retire draft/inspection naming once the promotion path is proven; manage image assets via workbook asset maps; simplify customer UX without losing ordering accuracy or dealer detail; strengthen promotion gates; reduce monolithic runtime logic as rules become fully data-owned.
