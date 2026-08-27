# 27vette

Developer workspace for the 2027 Corvette static order-form app. The published registry contains Stingray, Grand Sport, Grand Sport X, Z06, ZR1, and ZR1X forms with customer build downloads and dealer submissions to Stingray Chevrolet. The production app is served at `order.stingraychevroletcorvette.com`. Agent conduct, source-of-truth boundaries, validation strategy, and handoff rules live in `AGENTS.md`; this file owns the overview, repository map, and commands.

## Current State

- Stingray, Grand Sport, Grand Sport X, Z06, ZR1, and ZR1X are published customer-facing forms; no frontend package install or build step.
- `form-app/data.js` exposes the multi-model registry at `window.CORVETTE_FORM_DATA` (default model `stingray`; `window.STINGRAY_FORM_DATA` remains a legacy alias for the Stingray dataset). Each model entry carries generated model data plus model-card image metadata from the workbook `asset_map` sheet.
- Runtime promotion is workbook-owned: `model_master`, `model_registry_promotion`, and `variant_master` decide which models reach the registry; `scripts/promote_model.py` applies promotion rows; registry generation embeds promoted `form-output/runtime/*-runtime-contract.json` verbatim.
- All six workbook-registered models are promoted into `form-app/data.js`; model publication changes must continue through the workbook-owned promotion path rather than direct registry edits.
- Dealer submission posts to the WordPress endpoint `https://stingraychevroletcorvette.com/wp-json/corvette-build/v1/submit` with Cloudflare Turnstile — protected boundary, see AGENTS.md §6.
- Generated artifact names no longer carry draft wording: `form-output/runtime/` holds one `<slug>-runtime-contract.json` per promoted model and `form-output/inspection/` holds opt-in derived-swap manifests. Read promotion status from `model_master` / `model_registry_promotion`, never from a filename.

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

Other dirs (`product/`, `dist_updates/`, `archive/`) are reference/archive surfaces — inspect only when a task names them.

## Local Tools and In-Progress Modules

Not yet part of the live customer path; inspect before assuming either is production-ready.

- **Workbook Manager (local workbook editor)** — `workbook-manager/`: completed local tool for reviewing and applying guarded changes to `stingray_master.xlsx`. Saving adds changes to a draft; only the reviewed **Apply and Rebuild** action changes the workbook and refreshes the affected local order-form files. For everyday use, start with the plain-language [Workbook Manager User Guide](workbook-manager/USER-GUIDE.md). See Workbook Manager Workflow below for technical details, setup, and tests.
- **Visualizer** — `visualizer/`: prototype build-and-price visual configurator (stacked exterior/interior image layers driven by selected options) plus its companion `workbook-editor/` review UI. `visualizer/workbook-editor/intentional-differences.json` is the committed allowlist of intentional cross-model option differences (`status: intentional` suppresses; `pending-review` annotates); editing it is a normal file change, not a workbook write. Full visualizer integration into the order form is tracked in `docs/roadmap_wishes.md` and is not yet wired into `form-app/`.

## Workbook Source Surfaces

Canonical workbook: `stingray_master.xlsx`.

Shared/Stingray source sheets: `model_master`, `model_registry_promotion`, `variant_master`, `section_master`, `stingray_options`, `stingray_ovs`, `rule_mapping`, `price_rules`, `rule_groups`, `rule_group_members`, `exclusive_groups`, `exclusive_group_members`, `color_overrides`, `lt_interiors`, `LZ_Interiors`, `PriceRef`, `asset_map`.

Runtime metadata/audit sheets: `model_workbook_sources`, `model_variants`, `model_interior_scope`, `interior_components`, `runtime_steps`, `context_section_master`, `context_choice_copy`, `section_presentation`, `order_summary_sections`, `step_order_summary_map`, `default_selection_rules`, `runtime_rule_exceptions`, `variant_option_overrides`, `rule_phrase_map`.

Model-scoped sheets, all five promoted non-Stingray models active (`grandSport_*`, `grand_sport_x_*`, `z06_*`, `zr1_*`, `zr1x_*`): `<model>_{options, ovs, rule_mapping, price_rules, rule_groups, rule_group_members, exclusive_groups, exclusive_members, variant_overrides}`. `grand_sport_x_*` is the exception to that template — it names its group-member sheet `grand_sport_x_rule_members` and adds `grand_sport_x_color_overrides`. Read the actual sheet names from the workbook rather than deriving them from the prefix.

`category_master` is not active. Historical evidence sheets live in `archive/stingray_archive.xlsx`. Workbook `form_*` generated sheets are retired from routine workflow — edit source rows and regenerate.

## Generated Data Contract

Each model dataset: `dataset`, `variants`, `steps`, `sections`, `contextChoices`, `choices`, `standardEquipment`, `ruleGroups`, `exclusiveGroups`, `rules`, `priceRules`, `interiors`, `colorOverrides`, `defaultSelectionRules`, `validation`. Stingray additionally carries `runtimeRuleExceptions`. All promoted models carry workbook-owned `orderSummary` metadata (`sections`, `stepMap`) in `data` and workbook-owned Vehicle Setup presentation copy in the registry-level `vehicleSetup` object. Registry shape:

```js
window.CORVETTE_FORM_DATA = {
  defaultModelKey: "stingray",
  models: { stingray: { key, label, modelName, exportSlug, image_url, image_alt, image_fit, image_position, vehicleSetup: { cardSubtitle, eyebrow, title, description, facts }, data }, grandSport: {...}, grand_sport_x: {...}, z06: {...}, zr1: {...}, zr1x: {...} }
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
python -m pip install -r requirements-test.txt
```

`requirements.txt` remains the minimal workbook runtime environment;
`requirements-test.txt` adds pytest and Workbook Manager backend dependencies for
the shared local/CI validation environment. Do not commit `.venv/`. Always run
Python tooling with `.venv/bin/python` or the activated venv.

## Raw Order-Guide Ingest (retired)

Retired 2026-07-23; no supported ingest command exists. See AGENTS.md §8 for boundaries and `docs/archive/retired-ingest/2026-07-23/` for historical evidence only.

## Workbook Editor Workflow

`scripts/workbook_editor_server.py` serves the fallback localhost-only UI for routine review/editing of `stingray_master.xlsx`; it derives models, sheet registries, schemas, and reference domains from the live workbook. Its obsolete embedded Ingest Review workflow remains retired.

```sh
.venv/bin/python scripts/workbook_editor_server.py [--port 8030] [--workbook <path>]
```

Open `http://127.0.0.1:8027/`. Review tab: `/api/lints` (informational structural lints; the batch validator remains the write authority) and `/api/compare` (cross-model option copy/section/order diff, majority vs deviator, ZR1/ZR1X excluded; intentional differences via the committed allowlist above).

Apply behavior: edits queue client-side as typed operations; only sheet families registered in `model_workbook_sources` are editable; adding an option requires OVS coverage for every active variant; Apply runs the full gate internally (batch validation, dry-run on temp copy, package + schema validation, `save_workbook_safely()` lock/mtime checks, backup, atomic replace, table-ref maintenance, `form-output/workbook-edit-log.jsonl` entry); warnings block until confirmed.

Shared ChangeSet operator path (preview is the default; approval never writes; write requires the exact bound preview and approval). Workbook Manager is the current producer through its single Apply and Rebuild route:

```sh
.venv/bin/python scripts/apply_workbook_changeset.py change-set.json --workbook stingray_master.xlsx --preview-out preview.json
.venv/bin/python scripts/apply_workbook_changeset.py change-set.json --workbook stingray_master.xlsx --approve <actor> --preview preview.json --approval-out approval.json
.venv/bin/python scripts/apply_workbook_changeset.py change-set.json --workbook stingray_master.xlsx --write --preview preview.json --approval approval.json --receipt-out receipt.json
```

The fallback editor retains its existing typed-operation Apply path; Workbook Manager uses the same shared writer through its separately bound durable lifecycle.

An Apply is only the workbook-write step — afterwards regenerate affected model artifacts, run the relevant gates below, and review diffs.

## Workbook Manager Workflow

For everyday use, start with the plain-language
[Workbook Manager User Guide](workbook-manager/USER-GUIDE.md).

`workbook-manager/` is a React (Vite) + FastAPI + SQLite editor for
`stingray_master.xlsx`. Draft editing is provisional: a first
import into an empty projection is allowed, replacement re-import is contained,
and durable update/add/delete plus Asset Manager decisions emit, preview, and
approve one immutable ChangeSet through the shared service. The shared writer
restores and SHA-256-verifies its backup after post-save validation/log failure.
Only the typed-confirmation `POST /api/drafts/{draft_id}/apply-rebuild` route may
write: it binds the exact approved artifacts, prepares a verified rollback set,
regenerates ownership-derived affected models in an isolated root, publishes a
complete local registry candidate, and restores/hash-verifies workbook and
outputs on downstream failure. Every legacy `POST /api/sync` request with
`write=true` remains refused. Draft Save does not write or regenerate.
Browsing, history, and verified-projection disposable comparison export remain
available; generated-artifact and publication status is reported current only
while its successful Apply and Rebuild hashes still match. The
workbook remains canonical. Storage bootstrap runs in the FastAPI lifespan,
every request opens and closes its own projection and durable-state connection,
and one process-local lock plus a projection reader gate serialize durable
mutations and any future candidate promotion — so supported serving is
**single-process only** and `run.sh` refuses `--workers`. Setup, current
containment behavior, and test commands: `workbook-manager/README.md`. Focused
tests: `tests/test_group_display_label_contract.py`,
`tests/test_workbook_manager_control_metadata.py`,
`tests/test_workbook_manager_connected_editing.py`,
`tests/test_workbook_manager_review_presentation.py`,
`tests/test_workbook_manager_catalog.py`,
`tests/test_workbook_manager_import_projection.py`,
`tests/test_workbook_manager_fixtures.py`,
`tests/test_workbook_manager_api_concurrency.py`,
`tests/test_workbook_manager_drafts.py`,
`tests/test_workbook_manager_changeset_lifecycle.py`,
`tests/test_workbook_manager_apply_rebuild.py`, and
`tests/test_workbook_manager.py`.

## Workbook And Generator Workflows

Model refresh (from repo root, venv python):

```sh
.venv/bin/python scripts/generate_form.py --model <model_key>
.venv/bin/python scripts/generate_registry.py
```

Asset URL reconciliation and workbook-owned card presentation:

```sh
.venv/bin/python scripts/sync_asset_map.py --complete
.venv/bin/python scripts/sync_asset_map.py
.venv/bin/python scripts/set_asset_display.py --rpo <RPO> --fit contain
```

`sync_asset_map.py --complete` is the routine operator path: it requires a
stable uncached live inventory, applies every unambiguous match through guarded
workbook save, validates, regenerates affected models, republishes the registry,
and bumps the browser data cache version. Bare `sync_asset_map.py` remains a
read-only diagnostic report. Card-presentation edits preview by default and
require `--write`. Detailed matching, exception, report, and presentation
semantics: `docs/asset-map-sync.md`.

`<model_key>` must be active and complete in workbook-owned `model_master`, `model_workbook_sources`, and `model_variants` metadata. All models write one strictly validated runtime contract under `form-output/runtime/`. Add `--emit-inspection --inspection-output <dir>` for optional review artifacts. Generator runs never mutate `form-app/data.js` directly; `generate_registry.py` validates every selected retained contract before publishing the promoted registry.

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

Pull requests targeting `main` run the required `release-candidate` GitHub check from `.github/workflows/release-candidate.yml`. The catalog-driven runner executes the catalog/oracle Layer 0 core plus the composed Layer 1 candidate on every PR, selects directly changed test owners and affected Layer 0–3 gates, co-selects the complete `workbook_manager` serial group when its shared fixture is needed, and uses a conservative validation/generator fallback for unclassified paths. That group no longer runs in one pytest process: `scripts/plan_ci_validation.py` splits its main owner into five disjoint partitions on every plan, not only on full runs, because unsplit it measured close to the job timeout. `tests/test_run_layered_validation.py` proves by collection that the five own every test in that file exactly once. Layer 4 remains diagnostic-only. It uploads one stage-timed JSON report:

```sh
python scripts/run_layered_validation.py \
  --report layered-validation-report.json \
  --changed-file <repo-relative-path>
```

Repeat `--changed-file` for each changed path, or pass a newline-delimited file
with `--changed-file-list changed-files.txt` (the CI path). The runner reads
commands and surface ownership from `tests/validation_catalog.json`; it does not
sum member timings for shared-setup serial groups. This PR gate intentionally
does not run the Layer 4 full inventory, access the live asset library, or submit
a dealer build. Choose any additional local gates by changed surface as
described below.

When a pull request edits `tests/validation_catalog.json`, the plan job first
classifies that edit with `scripts/catalog_change_scope.py`. Adding a gate entry
is additive: the plan runs the CI contract owners plus the newly declared gate's
own command. Removing a gate, retargeting an existing gate's command, layer,
test files, changed surfaces, or serial group, editing `ci`/`serial_groups`, or
changing suite membership beyond the added gate still selects the complete
inventory, as does an unreadable or missing base catalog. Focused local
contract:

```sh
.venv/bin/python -m pytest tests/test_catalog_change_scope.py -q
```

A full run also smokes every shard that only change-aware plans produce. Those
shards are unreachable from a full plan, and any edit to the planner forces a
full plan, so without this their command and dependency wiring is only ever
executed by unrelated pull requests. `tests/test_run_layered_validation.py`
derives the shard universe by reflection over the planner's factories, requires
each narrow-only shard to be smoked or justified in `SMOKE_EXEMPT_SHARDS`, and
parses the planner with `ast` to reject a shard built outside a factory, where
reflection could not see it.

`.github/workflows/codex-finding-disposition.yml` maintains the
`codex-finding-disposition` commit status from GitHub review threads. A current,
unresolved structured Codex P0 or P1 finding fails the status; resolved or
outdated findings and P2/P3 findings do not block. Review events refresh it
immediately, while a 15-minute reconciliation schedule picks up thread
resolution because GitHub Actions exposes no review-thread-resolution trigger.
The workflow checks out and executes only the trusted default-branch evaluator,
never pull-request head code. Focused local contract:

```sh
.venv/bin/python -m pytest tests/test_codex_finding_disposition.py -q
```

Read-only live inspection (requires an authenticated `gh` session):

```sh
GH_TOKEN="$(gh auth token)" python .github/scripts/codex_finding_disposition.py \
  --repository <owner>/<repo> --pr-number <number> --dry-run
```

After the workflow lands on `main` and publishes the status at least once, add
`codex-finding-disposition` to the `Release candidate gate` ruleset's required
status contexts. Do not register it before the default branch can publish the
context, or every open PR will be blocked by a missing status.

Every validation job has a 15-minute hard limit. A Workbook Manager source
change runs the composed candidate lane and the shared-fixture Manager
acceptance group, which is why that group is split across parallel partitions
rather than given a longer timeout. Selection remains catalog-driven; the
partitions do not add the Layer 4 full inventory. The frontend install explicitly includes
lockfile-pinned development dependencies because Vite is the production build
tool, even when the invoking environment sets `NODE_ENV=production`.

Workbook Manager frontend changes also run the cataloged production build:

```sh
npm --prefix workbook-manager/frontend ci --include=dev && npm --prefix workbook-manager/frontend run build
```

The Layer 1 spine the runner invokes remains available directly:

```sh
python scripts/verify_workbook_candidate.py \
  --workbook stingray_master.xlsx \
  --changed-model '*' \
  --report candidate-report.json
```

Operational handoff gate:

```sh
.venv/bin/python scripts/validate_state_handoff.py
```

`fable5loop/STATE.md` is the centralized operational handoff read at the start of every session; `fable5loop/STATE-archive.md` holds retired detail. Use this gate after any change to either file. The retired Fable 5 loop scaffold is archived under `docs/archive/fable5-loop/`.

Workbook schema gate — the single schema authority. No test re-runs it; the
`workbook-schema-standardization` node gate owns only the structural conformance
this command does not check:

```sh
.venv/bin/python scripts/validate_workbook_schema.py stingray_master.xlsx
```

Customer-facing option-sheet quality gate (all configured option sheets):

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

Node gate matrix (run each with `node --test tests/<name>.test.mjs`):

| Authority / purpose | Default readiness gates |
|---|---|
| Workbook source and schema | `workbook-schema-standardization`, `workbook-visual-copy-standardization`, `nonruntime-option-source-purge` |
| Retained contract and focused product assertions | `stingray-runtime-contract`, `grand-sport-runtime-contract`, `z06-runtime-contract`, `z06-interior-accessory-cleanup` |
| Published registry and browser runtime | `stingray-form-regression`, `z06-published-runtime`, `multi-model-runtime-switching`, `runtime-state-matrix`, `z06-performance-package-interactions`, `z06-runtime-rule-corrections` |
| Isolated registry publication | `z06-registry-publication` |
| Workbook-to-output parity, all promoted models | `source-to-contract-parity`, `source-to-registry-parity` |
| Generated-artifact boundary helper | `tracked-artifacts-guard` |

This matrix does not run the workbook schema gate. It used to, inside `workbook-schema-standardization`, and that one duplicated call was more than half the lane's wall time. Run the schema gate above alongside the node files: full default validation is the schema gate **plus** this matrix **plus** the Python metadata gate, never the matrix alone.

Optional inspection diagnostics (not readiness gates): `grand-sport-contract-preview`, `z06-contract-preview`. They retain raw-source/provenance evidence for investigations; customer/runtime assertions belong in the strict runtime-contract gates above.

Those tables are the complete set of `tests/*.test.mjs`; a new node gate must be added here and assigned one authority. Default gates are read-only or write only below a temporary root. Publication verification is explicit and isolated from the published `form-app/data.js` path.

Two optional inspection diagnostics invoke `scripts/generate_form.py`: `grand-sport-contract-preview` and `z06-contract-preview`. Each generates into a temporary `--output-root` and asserts every file under `form-output/` and `form-app/` is byte-identical afterwards. Fresh all-model generation, strict validation, parity, registry publication, and browser proof belong to the composed candidate lane above; the model runtime-contract files read retained artifacts and do not regenerate them.

The two parity gates compare the emitted contracts and the published registry
against the workbook rows behind them, for every promoted model. Their expected
side is a snapshot built from a read-only workbook handle:

```sh
.venv/bin/python scripts/build_workbook_truth.py --out /tmp/workbook-truth.json
```

Each gate builds its own snapshot when run standalone (about a second). Set
`CORVETTE_WORKBOOK_TRUTH` to an already-built one to skip that, and
`CORVETTE_CONTRACT_ROOT` / `CORVETTE_FORM_DATA_JS` to point them at a candidate
tree instead of the tracked artifacts — which is what `verify_workbook_candidate.py`
does in its `workbook_truth` and `source_parity` stages. The snapshot is
temporary and untracked; nothing reads a committed copy of it.

`runtime-state-matrix` is the §4.3 runtime owner. It discovers every promoted
model and declared active variant from that same snapshot, then exercises
activation, variant resolution, reset/idempotence, exclusive groups, required
selections, representative rule transitions, totals, model switching, and
stubbed dealer/download identity against the published or candidate registry.
No live dealer request is made. The candidate lane's `browser_harness` stage
runs it beside `multi-model-runtime-switching`.

Python metadata gate — the default for generation/contract/promotion changes:

```sh
.venv/bin/python -m pytest tests/test_generation_safety.py tests/test_generate_form_model_discovery_cli.py tests/test_runtime_contract_builder.py tests/test_model_config_metadata.py tests/test_promote_model.py tests/test_registry_promotion_metadata.py tests/test_schema_validation_metadata.py tests/test_rule_derivation.py tests/test_model_generation_route.py -q
```

The remaining `tests/test_*.py` files are not in that gate and are chosen by changed surface:

| Surface | Tests |
|---|---|
| Workbook write path / editor | `test_editor_ops_apply`, `test_editor_ops_meta`, `test_editor_ops_global_families`, `test_editor_lints`, `test_editor_server_payload`, `test_editor_server_write_api` |
| Workbook domain / ChangeSet | `test_workbook_domain_registry`, `test_workbook_changeset`, `test_workbook_changeset_service`, `test_workbook_bool_hygiene` |
| Workbook Manager | `test_group_display_label_contract`, `test_workbook_manager_control_metadata`, `test_workbook_manager_connected_editing`, `test_workbook_manager_review_presentation`, `test_workbook_manager`, `test_workbook_manager_catalog`, `test_workbook_manager_import_projection`, `test_workbook_manager_generated_parity`, `test_workbook_manager_api_concurrency`, `test_workbook_manager_drafts`, `test_workbook_manager_changeset_lifecycle`, `test_workbook_manager_apply_rebuild`, `test_workbook_manager_form_graph` |
| Source assembly / runtime metadata | `test_source_assembly_characterization`, `test_runtime_metadata_guards`, `test_corvette_form_generator_contract` |
| Composed candidate / real all-model generation | `test_verify_workbook_candidate`, `test_all_model_runtime_generation` |
| Publication | `test_atomic_registry_write` |
| Asset map | `test_asset_map_sync`, `test_set_asset_display` |
| Options-sheet quality | `test_options_sheet_quality` |
| Operational handoff | `test_state_handoff` |
| Validation catalog | `test_validation_catalog` |
| Workbook-truth snapshot | `test_workbook_truth` |
| Source-parity canaries | `test_source_parity_canaries` |

Every `tests/test_*.py` file runs standalone: `tests/conftest.py` puts `scripts/`
on `sys.path` for the whole directory, so no pytest command needs
`PYTHONPATH=scripts`. The options-sheet quality CLI above still does, because it
is a module invocation rather than a pytest run.

`tests/validation_catalog.json` is the machine-readable inventory of every gate above: its layer, authority class, isolation, serialization requirement, measured duration, and collection counts. `test_validation_catalog` enforces it and fails when a test file is missing from the catalog, when two gates claim one named acceptance lock, when a generating gate lacks an isolated output declaration, when a protected-output gate is not serialized, or when this README disagrees with the catalog. Read counts and timings from the catalog rather than adding them here.

`.venv/bin/python -m pytest tests/ -q` runs everything (~18 min). Three tests in `test_verify_workbook_candidate.py` are ~63s each because each runs the full twelve-stage candidate lane over six models; everything outside the slowest ~15 tests is sub-second. Reserve the full run for canonical-workbook writes and publication, per AGENTS.md §10.

Full default validation = schema gate + every default-readiness row of the node matrix + the Python metadata gate. Optional inspection diagnostics run only when their raw-source evidence is relevant. Choose additional gates by changed surface per AGENTS.md §10.

## Workbook Safety

Close Excel before any script that writes `stingray_master.xlsx`; treat `~$stingray_master.xlsx` as a lock signal. Writes go through `save_workbook_safely()` and must be verified on disk — full rules in AGENTS.md §5.

## Roadmap

Keep moving model rules/defaults/pricing/presentation into workbook-authored tables; keep the six promoted models structurally consistent source-to-contract; manage image assets via workbook asset maps; simplify customer UX without losing ordering accuracy or dealer detail; strengthen promotion gates; reduce monolithic runtime logic as rules become fully data-owned.

Larger candidate initiatives (not yet scoped/approved, see `docs/roadmap_wishes.md`):

- Site restyle to the new homepage design system, replacing Elementor while keeping Formidable Forms and wpDataTables.
- Visualizer integration into the order form (see Local Tools and In-Progress Modules above) — grouped exterior/interior option presentation feeding a real-time build-and-price view, no change to rule/pricing/submission behavior.
