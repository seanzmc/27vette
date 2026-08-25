# Open PR review-finding triage

Working tracker for the Codex review findings on the open pull requests, plus
the branch/workflow cleanup that came out of the same review. Delete this file
once every row is closed; it is a scratch tracker, not durable guidance.

Owning specification for the Workbook Manager rows:
`docs/superpowers/specs/2026-08-21-workbook-manager-ux-recovery.md`.

## Codex findings

| # | PR | Finding | Verdict | Status |
|---|----|---------|---------|--------|
| 1 | 40 | P1 — control checks applied to read-only schemas | Real, blocking | **Done** — commit `8765851` |
| 2 | 40 | P2 — reference choices not scoped to the selected model | Real in part; stated cause wrong | **Done** — see below |
| 3 | 40 | P2 — blank labels accepted on active exclusive groups | Real | **Done** — see below |
| 4 | 39 | P2 — blank labels (duplicate of #3) | Duplicate | **Closed by #3** |
| 5 | 39 | P2 — sync rewrites CSV but not JSON for non-decision fields | Real, low | **Done** — see below |
| 6 | 39 | P2 — review artifact records a placeholder fallback label | Real in code; artifact left as-is | **Done** — see below |
| 7 | 38 | P2 — AGENTS.md omits planner-triggered full runs | Real, doc accuracy | **Done** — commit `13acd7f` |

### Finding 2 — corrections to the report

Codex justified this as "the reference API offers cross-model values that the
workbook write path does not consider valid." That is **not accurate**: for a
`global` RefSpec the write path checks existence only, with no model filter
(`workbook-manager/backend/app/validation.py:37`). API and writer agree today,
so nothing was offering values the writer rejects.

The real defect is narrower — a picker offering another model's rows is wrong
on its own terms. Fixed only where the data proves it is safe:

| Reference | Before | After | Cross-model rows in canonical data |
|---|---|---|---|
| `option_availability.variant_id` | 32 | 6 | 0 |
| `variant_option_overrides.variant_id` | 32 | 6 | 0 |
| `model_interior_scope.interior_id` | 262 | 130 | 0 |
| `interior_components.interior_id` | 262 | 132 | 0 |

Deliberately **not** narrowed:

- **All `section_id` references.** The projected `form_sections.model_context`
  is empty for all 48 rows, so the filter Codex points at matches zero sections
  for every model. Enabling it would empty the section picker rather than scope
  it. Tracked as an open projection/contract gap, not a query fix.
- **`color_overrides.interior_id`.** That table has neither `model_id` nor
  `model_key`, so its rows are not owned by a model; narrowing could block
  legitimate shared authoring.

Narrowing applies only when a model is supplied, so no field newly *requires*
one and no existing caller changes behavior.

### Finding 3 — scope

Spec §7.1 already establishes the outcome: active customer-rendered exclusive
groups require an approved nonblank label, while rule-group labels stay
Manager-facing. Enforced in two places:

- `schema_validation.validate_group_display_labels()` raises
  `group_display_label_missing` for a blank label on an active
  `exclusive_groups` row;
- `registry.ACTIVE_ROW_REQUIRED_COLUMNS` adds `display_label` to
  `required_on_effective_active_row` for `exclusive_groups`, so `editor_ops`
  rejects clearing it on an active row.

Two guards keep the tightening from over-reaching: the requirement applies only
once the sheet actually carries the column (pre-migration sheets are
distinguished by column absence, per Codex's own note), and never on a delete —
removing a row must not require filling in its copy first.

The canonical workbook already has labels on all 220 group rows across every
sheet, so the schema gate stays clean.

### Findings 5 and 6 — review tooling

Both fixed in `workbook-manager/review/`. Note these live on the cp2 branch's
files but were committed on cp3 (PR 40), which is stacked on top of cp2 and
contains it. If PR 39 is merged and PR 40 abandoned, these fixes go with it.

**Finding 5.** `sync_group_display_label_review.py` copied only the four
decision fields plus `customer_visible`, so an edit to an evidence column was
written back to the CSV while the JSON kept the generated value. Sync now
rejects any change to a non-decision field and tells the operator to
regenerate instead. Booleans compare by value, not text: a spreadsheet
round-trip rewrites `true` as `TRUE`, and the artifact contract already reads
them case-insensitively. Verified idempotent against the committed artifacts,
and verified to reject a tampered `notes` value.

**Finding 6.** `current_fallback_label` recorded
`Label pending workbook review` for all 15 hash-suffixed exclusive groups,
where the Manager's `_exclusive_group_label` would render
`Exclusive group · <section_name>`. The generator mirrored only
`_group_fallback`. It now mirrors the full pre-label path.

The committed artifacts are deliberately **not** regenerated. All 224
decisions are already `approved` and their labels are migrated into the
canonical workbook, so these files are the historical record of a completed
review — the generator's own guard exists to protect exactly that. Rewriting
`current_fallback_label` now would misstate what reviewers actually saw when
they decided. The code fix applies to any future inventory.

## Branch cleanup — done 2026-08-24

Remote went from 48 branches to 6; local from 69 to 9. Nothing was discarded:
every branch carrying commits not already in `main` was tagged `archive/<branch>`
and the tags were pushed, so all 21 are recoverable from the remote.

Restore any of them with:

```bash
git checkout -b <branch> archive/<branch>
```

**Kept:** `main`, the five open PR heads (`cloudflare/workers-autoconfig`,
`codex/workbook-relational-db`, `codex/update-agents-md-validation-workflow`,
`hermes/workbook-manager-ux-recovery-cp2`,
`hermes/workbook-manager-ux-recovery-cp3`), and four local-only branches still
checked out in worktrees.

**Deleted:** 41 remote branches (18 tagged first, 23 already contained in
`main`) and 60 local branches (3 local-only ones tagged first). A stale
`refs/remotes/origin/origin` ref that never existed on the remote was also
removed.

### Archive tags

| Branch | Commit |
|---|---|
| `claude/checkpoint-2-pr27-9f6332` | `7bd73740` |
| `claude/fast-layered-validation-checkpoint-1-55546e` | `2eb33f15` |
| `claude/fast-layered-validation-suite-4c31f6` | `cacc9f35` |
| `claude/pr28-assertion-comment-updates-08f007` | `e5592c26` |
| `codex/gsx-ah2-c2z-standard` | `5dfd7580` |
| `codex/workbook-manager-closeout` | `8f9c756b` |
| `codex/workbook-manager-guide-closeout` | `df367ba3` |
| `codex/workbook-manager-user-guide` | `8cc69e0f` |
| `codex/zr1x-j58-closeout` | `dc369e80` |
| `db-workflow` | `dde3e2b1` |
| `docs/pr-only-delivery` | `4c6fa7f7` |
| `hermes/checkpoint-3-runtime-state-matrix` | `a22b0e6e` |
| `hermes/checkpoint-4-validation-and-asset-docs` | `4afe298a` |
| `hermes/hermes-62195f2e` | `cd95f9dc` |
| `ingest-wizard` | `b78d7bf2` |
| `interior-media-pass1` | `2ba26913` |
| `newSchemaData` | `1066b744` |
| `pr31` | `4afe298a` |
| `revert-36-hermes/workbook-manager-ux-recovery-cp1` | `64f393f8` |
| `safety/main-before-tree-repair-20260609-211401` | `3099c4de` |
| `schema_refactor` | `d08fec19` |

## Old pull requests — closed 2026-08-24

Both were checked for salvageable work before closing, and both branches were
tagged first, so the code is recoverable from the remote.

**#1 `cloudflare/workers-autoconfig`** — closed as unadopted. Cloudflare
Workers was never taken up: `main` has no `wrangler` config, and the
documented deploy path is the WordPress endpoint (README, AGENTS.md §6). Its
two files also conflict, because `main` has long had its own `.gitignore`.
At 676 behind, the `compatibility_date` and `form-app` layout would both need
rewriting anyway.

**#8 `codex/workbook-relational-db`** — closed as superseded. Nothing needed
harvesting: the architecture was absorbed through a different structure, not
this implementation. None of its compiler stack exists on `main`
(`central_compiler`, `model_compiler`, `shared_compiler`, `migration`,
`export_adapter`, `workbook_profile`, `contract_audit`, `compile_types`);
`main` uses `catalog`, `drafts`, `apply_rebuild`, `contract_parity`, and the
asset modules instead. The `specs.py` consolidation it proposed did happen.
Both of its stated follow-ups are resolved: six models are live where it
targeted three, and the ingest wizard was deliberately retired on 2026-07-23
(AGENTS.md §8) rather than left pending.

Both branches were deleted after closing — remote and local, plus the stale
`.worktrees/codex-workbook-relational-db` worktree, which was clean and held
no commits beyond its archive tag. Restore either with
`git checkout -b <branch> archive/<branch>`.

## Candidate workflow automation

1. Repo setting: automatically delete head branches on merge.
2. Weekly branch reaper for merged branches untouched 30+ days.
3. ~~Required check that fails while an unresolved Codex P1 comment is open.~~ Done 2026-08-24, PR #41.
4. Stale-PR bot: comment at 30 days, close at 45.
5. Fail a PR that is more than ~20 commits behind `main`.

## Validation-gate efficiency audit — 2026-08-24

Audited the `release-candidate` gates for redundant or over-broad selection.
No test-level redundancy exists: the full plan schedules every repository test
exactly once (938 unique tests, 938 scheduled executions, 0 duplicated, 0
unowned), and `finalize_ci_validation_plan.py` already proves that invariant.
Cost is concentrated instead — the six slowest shards were 3,195 s of 4,451 s
for 90 tests, while 664 tests ran in 192 s.

The waste was in *when* the full suite fired, not in what it contained. All six
runs sampled went full; PRs #39 and #40 did so solely because they touched
`tests/validation_catalog.json` to add one gate entry.

| Fix | Effect |
|---|---|
| `scripts/catalog_change_scope.py` classifies catalog edits | Adding a gate entry runs the CI contract owners plus that gate instead of the full inventory; removals, retargeting, and `ci`/`serial_groups`/suite edits still escalate, as does an unreadable base catalog |
| `workbook-manager/review/**` owns `test_group_display_label_contract.py` | Editing review tooling or its reviewed CSV/JSON no longer escalates to the complete Manager suite |
| Removed the `focused_main_test_covered` carve-out | Coverage fix: editing `tests/test_workbook_manager.py` alongside a frontend file used to *drop* all three Manager partitions |
| `fable5loop/` edits no longer select `ci-contracts` | A Fable state edit cannot break catalog, planner, or workflow contracts |
| `py.test_codex_finding_disposition` added to `always_gate_ids` | The layered path and the `ci-contracts` shard now agree on that owner |

Measured on the historical diffs, PR #39 drops from 4,451 s to roughly 1,925 s
and PR #40 to roughly 2,800 s. Those figures reuse per-shard timings from run
`32754913746` and estimate shards that run did not execute.

Not changed, and still open if you want them: the shard balance is lopsided
(`manager-drafts` 20 s against `manager-projection` 647 s), and
`manager-non-api-sync-and-export` at 584 s sits close enough to the 900 s
timeout that one slow test would time out rather than fail. Rebalancing needs
per-test `--durations` profiling first.

## Shard rebalancing — 2026-08-24

Profiling replaced the audit's guess. Per-shard totals came from PR #43's green
run; per-test durations were measured locally, where the whole suite runs about
2.3x faster than CI but the proportions hold.

### The unit costs

```
verified fixture build (first call in a process) :  71.01s
verified fixture (cached)                        :   0.00s
clone_combined_projection                        :   0.03s
unchanged_export_result (first)                  :  67.91s
workbook 0.6 MB   projection 6.0 MB
```

Every shard pays the 71s fixture build once. The 830s sync/export shard was
71s fixture + 68s unchanged export + 212s changed-overlay export + ~5s for the
other eight tests.

### Rebalancing by itself returns nothing

Any shard containing `test_export_overlays_registry_owned_projection_fields`
had to pay 71 + 68 + 212 = 351s, which is 99% of the 356s the whole shard cost.
`manager-api-core` is the same shape: 71s fixture + 213s for
`test_zz_apply_rebuild_copied_workbook_mixed_draft_and_replay` equals its full
284s. Partitioning `-k` expressions cannot help when one test is the shard.

### A latent timeout, found while measuring

The split only ran on full plans, so narrow plans used the monolithic
`manager-non-api` owner. It measures **372.77s locally, roughly 810-890s in CI
against a 900s job timeout** — ordinary pull requests were running within
seconds of a hard timeout, which reads as infrastructure flake rather than a
test failure. The partitions now apply to every plan.

### What was changed

`TestComparisonExport.setUpClass` built the 68s unchanged export eagerly, but
only `test_acceptance_export_is_disposable_and_preserves_unchanged_workbook`
reads it. It is now a lazy property, still process-cached, so a shard that does
not run the acceptance test no longer pays for an export it never opens. The
overlay proof then moved into its own partition.

| | before | after |
|---|---|---|
| `manager-non-api` unsplit (narrow plans) | 372.77s | n/a — partitioned |
| `manager-non-api-sync-and-export` | 356s | 154.16s |
| `manager-non-api-export-overlay` | — | 311.63s |
| local critical path for the owner | 372.77s | 311.63s |

Roughly 850s to 730s in CI; timeout headroom moves from about 95% to about 80%.
The five Manager partitions are proven disjoint and exhaustive by collection
(70 tests, 70 owned, 0 duplicated) in
`tests/test_run_layered_validation.py::test_manager_main_partitions_are_disjoint_and_exhaustive`.

### The real cost was one quadratic loop — fixed

Both slow paths profile to the same place.
`schema_validation.validate_workbook_schema` opens the workbook with
`load_workbook(..., read_only=True)` at
`scripts/corvette_form_generator/schema_validation.py:1145`, then does random
access with `ws.cell(row, column)` at lines 1232, 1256, and 1280. On a
read-only openpyxl worksheet every `.cell()` restarts the streaming row
parser, so those loops are quadratic.

| profiled call | total | `validate_workbook_schema` | `.cell()` calls | cells parsed |
|---|---|---|---|---|
| `promote_verified_projection` (the 71s build) | 205s | 188s (92%) | 9,303 | 14.1M |
| `export_comparison_workbook` (the 212s test) | 655s | 595s (91%) | 216,713 | 42.6M |

The real import work was 14.5s of that 205s.

`column_values()` now reads each sheet in one streaming pass and returns values
keyed by column in row order, so the three checks still emit issues column-major
in exactly the original sequence.

Because this is the fail-closed schema gate, the change was proved by
differential rather than by inspection. A fixed corpus — the canonical workbook
with and without the live-contract check, plus four mutated copies injecting
boolean, RPO, price, and combined drift — was validated before and after, and
every issue list matched exactly, order included.

| case | issues | identical | before | after |
|---|---|---|---|---|
| canonical | 0 | yes | 66.54s | 1.23s |
| canonical-no-live | 0 | yes | 67.36s | 0.89s |
| boolean-drift | 7 | yes | 67.82s | 0.76s |
| rpo-drift | 3 | yes | 67.31s | 0.76s |
| price-drift | 2 | yes | 63.88s | 0.77s |
| all-drift | 12 | yes | 64.65s | 0.79s |

Measured downstream, all passing:

| | before | after |
|---|---|---|
| `scripts/validate_workbook_schema.py` (the gate) | ~66s | 1.36s |
| verified fixture build (per Manager shard) | 71.01s | 7.31s |
| unchanged comparison export | 67.91s | 5.41s |
| `manager-non-api` unsplit | 372.77s | 38.35s |
| `manager-non-api-export-overlay` | 311.63s | 38.73s |
| `manager-api-core` | 284.49s | 40.27s |
| `manager-projection` | 290.33s | 42.25s |
| whole `tests/test_workbook_manager.py` | ~640s | 71.47s |
| `test_editor_ops_apply.py` | 361s (CI) | 24.76s |
| `test_editor_server_write_api.py` | 486s (CI) | 28.43s |
| `test_verify_workbook_candidate.py` (all 17) | ~900s (CI, 2 shards) | 35.70s |

### Measured in CI

Full inventory, run `32777596688` before against run `32792294585` after. Both
green.

| shard | before | after | factor |
|---|---|---|---|
| manager-non-api-sync-and-export | 851s | 41s | 20.8x |
| manager-api-core | 654s | 79s | 8.3x |
| manager-projection | 627s | 102s | 6.1x |
| full-python-editor-server | 486s | 82s | 5.9x |
| full-python-candidate-canonical | 454s | 62s | 7.3x |
| full-python-candidate-drift-and-fast | 452s | 40s | 11.3x |
| full-python-editor-ops | 351s | 58s | 6.1x |
| manager-non-api-core | 216s | 32s | 6.8x |
| manager-api-assets | 212s | 31s | 6.8x |
| full-product-readiness | 279s | 144s | 1.9x |
| full-python-core | 230s | 173s | 1.3x |
| manager-non-api-export-overlay | — | 88s | new shard |
| **total billable job-seconds** | **4,899s** | **1,000s** | **4.9x** |
| **critical path** | **851s** | **173s** | **4.9x** |
| timeout headroom used | 95% | 19% | |

### Two consequences worth deciding on

The shard partitioning is now optional rather than protective. Unsplit, the
non-API owner is 38.35s locally and would be roughly 80s in CI including setup,
against a 900s timeout. The three partitions cost 32 + 41 + 88 = 161s billable
with an 88s critical path, because each job pays its own setup. Collapsing them
back to one shard would save roughly 80s billable per full run and about 10s of
wall clock — real but small, and it trades away per-partition failure isolation.
An earlier note here called the collapse plainly cheaper; that was extrapolated
from local timings before the CI numbers above existed.

`approximate_seconds` in `tests/validation_catalog.json` was a baseline captured
2026-08-17 and had gone stale by up to 47x. Re-baselining used to mean a 33
minute serial run, which is why it was left alone; after the fix the same run is
6.4 minutes, so it was redone under the catalog's documented method — each gate
once, serially, one process each — on matching runtimes (Node 26.7.0, Python
3.14.7, darwin arm64), directly comparable to Checkpoints 0 and 1.

**All 71 gates in 385.2s against 1,970.1s, a 5.1x reduction, and every gate
exited zero.** That is the first recorded clean run of the complete inventory:
Checkpoint 0 recorded 7 node failures across 6 files plus 3 Python files failing
when run alone, and Checkpoint 1 still had `node.grand-sport-contract-preview`
failing on its own count literal.

| gate | 8-17 | now | factor |
|---|---|---|---|
| `cmd.workbook_schema` | 62.0s | 1.31s | 47.3x |
| `cmd.options_sheet_quality` | 6.0s | 0.24s | 25.0x |
| `py.test_verify_workbook_candidate` | 457.5s | 38.19s | 12.0x |
| `py.test_workbook_manager_import_projection` | 205.2s | 23.98s | 8.6x |
| `py.test_editor_server_write_api` | 220.1s | 27.90s | 7.9x |
| `py.test_workbook_manager` | 574.3s | 74.52s | 7.7x |
| `py.test_editor_ops_apply` | 147.8s | 23.54s | 6.3x |
| `py.test_workbook_manager_generated_parity` | 147.7s | 26.40s | 5.6x |

One gate got slower and should stay that way: `py.test_run_layered_validation`
went 0.6s to 4.51s because this branch added planner contracts to it, including
one that shells out to `pytest --collect-only` to prove the Manager partitions
are disjoint and exhaustive.

The 2026-08-17 and Checkpoint 1 records are preserved; this run is recorded
alongside them as `baseline.schema_read_pattern_fix`.
