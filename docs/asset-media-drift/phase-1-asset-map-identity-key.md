# Spec: Phase 1 — asset_map identity-key correctness (generator/tooling fix)

Status: proposed, awaiting approval per AGENTS.md Section 4. No code changed by this document.

Parent: `docs/asset-media-drift-remediation-spec-2026-06-30.md` (Section 2, "Phase 1"). This file is the
standalone, exact spec for that phase, written for direct implementation. Phases 2-4 from the parent
spec are out of scope here and are not restated except where needed for context.

## 0. Re-validation at time of writing this phase spec

Repo state: `git status --short` shows only `docs/asset-media-drift-remediation-spec-2026-06-30.md` as
untracked; tree otherwise clean at HEAD `1e3fa242e18beaa558dd4291eb76e2a670b6b5c7`.

Re-confirmed the parent spec's Finding 3/4 claims directly against current source (line numbers have
drifted slightly since the audit; function names and keying have not):

- `scripts/corvette_form_generator/asset_map_sync.py` keys every desired/existing asset row by
  `(model_key, target_id)`, dropping `target_type`:
  - `read_option_sheets` returns `dict[tuple[str, str], dict[str, str]]` (line 371)
  - `read_model_targets` writes `desired[(model_key, target_id)] = {...}` (line 411)
  - `read_bodystyle_targets` writes `desired[(model_key, target_id)] = {...}` (line 426)
  - `existing_asset_rows` writes `rows[(model_key, target_id_key)] = values` (line 436-454)
  - `reconcile` reads/writes `desired`/`existing_rows` keyed the same two-tuple way throughout
    (lines 495, 505, 541-545, 555-562, 629-630)
- `scripts/corvette_form_generator/contract.py:load_asset_map` (line 25-42) is the canonical identity:
  `assets[(target_type, target_id)] = fields`, scoped per `model_key` by the caller. Docstring at
  line 26 states this explicitly: `"""Active asset_map rows for one model, keyed by (target_type, target_id)."""`
- `scripts/corvette_form_generator/schema_validation.py` imports `load_model_asset_map` from
  `contract.py` (line 12) for one consumer, `validate_app_registry_freshness` (line 251), and contains
  no uniqueness/duplicate-row check on raw `asset_map` rows themselves. It does, however, already own
  exactly this *shape* of check for sibling sheets: `validate_model_master_metadata` (line 440-481)
  walks active rows, tracks a `seen` dict keyed by the row's identity, and raises a
  `duplicate_active_model_master_row` `SchemaIssue` (error severity) on a repeat, via the module's
  `add_issue` helper. `validate_option_display_order_uniqueness` (line 720+) is a second instance of the
  same pattern for a different sheet. This is the established convention for "active workbook row
  uniqueness" checks in this codebase, and is read-only (the module's docstring at line 1 states
  "Read-only workbook schema validation for Corvette form source sheets").
- The three target namespaces in use today (`opt_*` option ids from `read_option_sheets`, bare
  `model_key`/registry-key model ids from `read_model_targets`, and `body_style__*` context-choice ids
  from `read_bodystyle_targets`) do not currently collide as plain `target_id` strings, so dropping
  `target_type` in `asset_map_sync.py` is latent — it does not produce a wrong result on today's data,
  only on a future `target_id` collision across types.
- `tests/test_asset_map_sync.py` currently has 19 test functions (confirmed via `grep -c '^def test_'`);
  reran `pytest tests/test_asset_map_sync.py -q` to get a current baseline before any change — see
  Section 6.
- `tests/test_schema_validation_metadata.py` is the existing test file for `schema_validation.py`'s
  metadata-shape checks (e.g. `test_model_master_asset_map_shaped_headers_are_rejected_directly` at
  line 171, which already exercises asset_map-shaped headers in a `model_master`-mistagged context).
  This is the natural home for the new duplicate-active-asset_map-row test case.

Conclusion: the parent spec's Phase 1 diagnosis holds. This document expands it into an exact,
self-contained implementation spec.

## 1. Diagnosis

`asset_map_sync.py` (the workbook-write/reconciliation path) and `contract.py` (the runtime-read path)
use two different identity models for the same `asset_map` sheet:

- `contract.py`: `(target_type, target_id)`, scoped per model — matches the sheet's actual columns and
  is the identity the runtime contract depends on.
- `asset_map_sync.py`: `(model_key, target_id)` — drops `target_type` entirely.

There is no uniqueness validation anywhere in the codebase for active `asset_map` rows under either
identity model. A duplicate active row for the same `(model_key, target_type, target_id)` is silently
last-write-wins in `contract.py`'s dict comprehension at load time, with no error and no test failure.

Risk: this is the only finding in the parent audit/spec that degrades to **silently wrong generated
output** with zero error signal, rather than a maintenance-burden or workflow-noise cost. It is latent
today (no real `target_id` collisions across `target_type`s) but becomes active the moment a future
model, option, or context-choice naming convention produces a same-string `target_id` under a different
`target_type` — which `asset_map_sync.py`'s current keying cannot distinguish.

## 2. Exact files expected to change

1. `scripts/corvette_form_generator/asset_map_sync.py`
   - `read_option_sheets` — return type and dict keys change from `(model_key, target_id)` to
     `(model_key, target_type, target_id)`. `target_type` is already known at this call site (it's
     hardcoded/derived per-sheet, e.g. `"option"`); thread it into the key explicitly.
   - `read_model_targets` — same key-shape change; `target_type` is `"model"` for every row here.
   - `read_bodystyle_targets` — same key-shape change; `target_type` is `"context_choice"`.
   - `existing_asset_rows` — read `target_type` from the workbook row (the column already exists per
     the audit's confirmed schema) and include it in the key.
   - `reconcile` — update every `desired[...]` / `existing_rows[...]` lookup and write to use the
     three-tuple key; update `add_report` and any other helper that destructures these dict keys.
   - No change to the `image_url`/media-matching heuristics, the report CSV row content, or the CLI
     surface — this is a pure key-shape change.

2. `scripts/corvette_form_generator/contract.py`
   - `load_asset_map` (line 25-42) already keys correctly — **no change**, included here only so the
     duplicate-row guard (next item) has an obvious, already-correct home if that's where it lands.

3. `scripts/corvette_form_generator/schema_validation.py` — add a duplicate-active-row check on
   `(model_key, target_type, target_id)` for `asset_map` rows, modeled directly on the existing
   `validate_model_master_metadata` pattern (line 440-481): walk active asset_map rows, track a `seen`
   dict keyed by the three-tuple identity, and raise an error-severity `SchemaIssue` (e.g.
   `duplicate_active_asset_map_row`) via `add_issue` on a repeat, mirroring the
   `duplicate_active_model_master_row` issue shape (row references for both the first and duplicate
   row, in the `value` dict). This is the established convention for active-row uniqueness checks in
   this module and keeps `contract.py` unchanged, matching Section 2 item 2. Wire the new check into
   `validate_workbook_schema` (line 797) alongside the other per-sheet validators it already calls.

4. `tests/test_asset_map_sync.py`
   - Add a case with the same `target_id` string used under two different `target_type` values (e.g. a
     synthetic option and context-choice sharing a string) and assert no collision/overwrite occurs in
     `reconcile`'s desired/existing maps.
   - Add a duplicate-active-row test: two active `asset_map` rows with identical
     `(model_key, target_type, target_id)` should fail validation loudly, not silently keep the
     last-read row.

5. `tests/test_schema_validation_metadata.py` — add the duplicate-active-asset_map-row test case here
   (this is the existing, confirmed test file for `schema_validation.py`'s metadata-shape checks, e.g.
   `test_model_master_asset_map_shaped_headers_are_rejected_directly` at line 171). Build a minimal
   workbook fixture (via this file's existing `minimal_schema_workbook`/`append_sheet` helpers) with two
   active `asset_map` rows sharing `(model_key, target_type, target_id)` and assert
   `validate_temp_workbook` returns a `duplicate_active_asset_map_row` `SchemaIssue` with `error`
   severity. Follow the same structure as the existing `model_master` duplicate-row coverage in this
   file if such a test already exists for that sheet (confirm during implementation) — match its
   fixture-construction and assertion style rather than inventing a new test pattern.

## 3. Source-of-truth decision

Generator/tooling fix only. No workbook rows change and no workbook schema change. The `asset_map`
sheet's `target_type` column already carries the correct information — `asset_map_sync.py` is failing
to use a column that already exists. `contract.py` is already correct and is the reference
implementation for the key shape.

## 4. Companion-file impact check

- `contract.py` — inspected, no change required (already correct keying); does not gain the
  duplicate-row guard — that lands in `schema_validation.py` per Section 2 item 3, keeping `contract.py`
  untouched.
- `schema_validation.py` — gains the duplicate-active-asset_map-row check per Section 2 item 3, modeled
  on the existing `validate_model_master_metadata` pattern and wired into `validate_workbook_schema`.
- `form-app/app.js`, `form-app/data.js` — not applicable. No generated-data shape change; this phase
  only changes an internal reconciliation key used during workbook sync, not anything exposed in the
  generated runtime contract.
- Report CSV emitted by the asset_map sync CLI — must stay additive-only. If the duplicate-row guard or
  the key-shape change surfaces new report fields (e.g. `target_type` becoming visible in a report row
  that previously only showed `target_id`), confirm those are new columns or unchanged existing columns,
  not renames, so any existing report consumers don't break. Inspect the current report row-building
  code in `asset_map_sync.py` before changing it to confirm what's already emitted.
- README/AGENTS.md — not applicable; this does not change a documented workflow, CLI flag, or
  invocation pattern.
- `tests/test_asset_map_sync.py` — updated per Section 2 item 4 (in scope, this phase's test surface).

## 5. Constraints

- No workbook writes as part of this phase — this is a pure code change to the reconciliation/validation
  logic, not a data correction (current data has zero active duplicates, confirmed in Section 0).
- No change to `contract.py`'s already-correct `(target_type, target_id)` keying — Phase 1 brings
  `asset_map_sync.py` into alignment with `contract.py`, not the other way around.
- No unrelated refactor of `asset_map_sync.py` beyond the key-shape change and the duplicate-row guard.
  Do not touch the media-matching heuristics, CLI argument parsing, or report formatting beyond what's
  needed to carry `target_type` through.
- Preserve current report CSV columns; additive changes only.
- No new dependencies.
- No new validation taxonomy — the duplicate-row check follows `validate_model_master_metadata`'s
  existing pattern (active-row walk, `seen` dict, `add_issue` with error severity) exactly; do not
  invent a new issue-shape or check-registration mechanism in `schema_validation.py`.

## 6. Risks and non-goals

- **Risk**: not fixing this does not break today's data — zero active duplicates exist currently
  (confirmed against current workbook state implicitly via the parent audit's report counts, not
  re-verified by opening the workbook in this pass since no workbook inspection was needed to write
  this code-only spec). This phase is a guard against *future* drift, not a live-bug fix. If the user
  wants the zero-duplicate claim re-confirmed against the current workbook before implementation,
  flag that as a pre-implementation check, not part of this phase's validation plan.
- **Non-goal**: this phase does not add wildcard/shared asset_map rows (parent spec's Phase 4 /
  Finding 5) — do not build wildcard-matching logic on top of this key-shape change in the same pass.
- **Non-goal**: this phase does not change media-coverage policy or the `flag_missing` classification
  (parent spec's Phase 4 / Finding 6).
- **Non-goal**: this phase does not converge `production.py`/`inspection.py` assembly logic (parent
  spec's Phase 2) — that is a separate, larger phase with its own spec.

## 7. Validation plan

Run in this order; report every command and its actual result, not an assumed pass:

1. `.venv/bin/python -m pytest tests/test_asset_map_sync.py -q` — must pass, including the two new
   cases from Section 2 item 4.
2. `.venv/bin/python -m pytest tests/test_schema_validation_metadata.py -q` — must pass, including the
   new duplicate-active-asset_map-row case from Section 2 item 5, and must not regress existing coverage
   (e.g. `test_model_master_asset_map_shaped_headers_are_rejected_directly`).
3. Run the asset_map sync CLI in report-only/dry-run mode (confirm exact flag via current `--help`
   output, do not assume) and confirm `keep`/`flag_missing`/`writes`/`inserts` counts are unchanged
   from the current baseline, since this phase is a pure identity-key correctness fix with no intended
   behavior change on current data. Re-capture the current baseline counts as part of this validation
   run rather than trusting the parent audit's stated 192/268/0/0 numbers, since those were captured
   2026-06-30 and the workbook may have changed since.
4. `.venv/bin/python scripts/validate_workbook_schema.py stingray_master.xlsx` (confirm exact script
   name/invocation via current `--help` or README before running — do not assume the flag-free
   invocation works without checking).
5. Use the project `.venv` on the host for all of the above; if running in a sandboxed/container
   environment without a working host `.venv` (as the parent audit's investigator hit), system Python
   plus pip-installed pytest/openpyxl is an acceptable substitute for the test run only — flag this
   explicitly in the handoff and recommend re-running on the host `.venv` before merge.

## 8. Handoff requirements for this phase

On completion, report per AGENTS.md Section 15:
- Exact diff in `asset_map_sync.py`, the duplicate-row guard's final location and shape, and the new
  test cases added.
- Confirmation that report CSV columns are unchanged or additive-only, with the specific diff shown.
- Validation results from Section 7, including the freshly re-captured baseline counts (not the stale
  192/268/0/0 figures) and a note on whether `.venv` or system Python was used.
- Confirmation that zero workbook writes occurred.
- Explicit statement that Phases 2-4 of the parent spec remain unstarted and unapproved.
