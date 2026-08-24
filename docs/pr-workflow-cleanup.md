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

## Branch cleanup

48 remote branches; roughly 40 are dead.

- 3 live (the open PR heads)
- ~10 merged/superseded checkpoints from 2026-08-13..22
- ~28 stale from 2026-04..07, 145-676 commits behind
- 4 with large unmerged divergence and no PR — tag before deleting:
  `newSchemaData` (160 ahead), `schema_refactor` (154), `ingest-wizard` (88),
  `db-workflow` (12)

## Old pull requests

- **#1 `cloudflare/workers-autoconfig`** — 2026-04-26, 20 lines, 676 behind,
  conflicting. Close; re-add fresh if Workers are ever wanted.
- **#8 `codex/workbook-relational-db`** — 2026-07-17, draft, 20,970 additions,
  142 behind, conflicting. Harvest anything not yet reimplemented, note it in
  `fable5loop/STATE.md`, then close pointing at the successor branches.

## Candidate workflow automation

1. Repo setting: automatically delete head branches on merge.
2. Weekly branch reaper for merged branches untouched 30+ days.
3. Required check that fails while an unresolved Codex P1 comment is open.
4. Stale-PR bot: comment at 30 days, close at 45.
5. Fail a PR that is more than ~20 commits behind `main`.
