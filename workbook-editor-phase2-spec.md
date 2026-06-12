# Workbook Editor Phase 2 Spec — Gated, Non-Breaking Write Path

Date: 2026-06-11
Parent: `workbook-editor-integration-spec.md` (§4.4 write design, §9.5 decisions). Phase 1 (read-only server + UI) shipped and merged.
Status: draft for approval, no implementation yet.

---

## 1. Diagnosis

**What exists after Phase 1.** A localhost server (`scripts/workbook_editor_server.py`) derives models, per-model sheet registries, schemas, and reference domains live from the workbook and serves a read-only Preact UI. `scripts/corvette_form_generator/editor_ops.py` holds `EDITOR_SHEET_META` (key columns, types, enums, reference columns for the 11 sheet families) and `SOURCE_ROLE_FAMILIES`. There is no write surface anywhere.

**What Phase 2 adds.** The edit queue and apply pipeline: structured row editing in the UI, composite guided flows (Add Option with full OVS coverage; groups with members), server-side non-breaking validation, dry-run, atomic apply through `save_workbook_safely()`, an ops-JSON export with a matching CLI, and a committed apply log.

**Risk level: high** — this creates the first programmatic write path to the canonical workbook outside the existing generator/promotion scripts. The whole design routes through the repo's existing safety machinery and refuses anything it cannot prove safe.

**Change class:** mixed — Python (op engine, server endpoints, CLI), JS/CSS (edit UI), tests, docs. The feature itself changes no workbook data, generated artifacts, or runtime behavior; it *enables* future workbook edits that will each follow the AGENTS.md Workbook Update Workflow.

**Verified facts this design relies on (inspected 2026-06-11):**

- `save_workbook_safely(wb, path, loaded_mtime_ns=...)` in `corvette_form_generator/workbook.py` already does: Excel lock-file refusal, load-mtime conflict refusal, temp-file save, `assert_valid_workbook_package()`, reopen check, timestamped backup to `backups/`, atomic replace. `excel_lock_path()` and `backup_workbook()` are importable.
- `validate_workbook_schema(path, check_live_contract=...)` and `result_payload(...)` are importable from `corvette_form_generator.schema_validation` — no subprocess needed.
- **11 sheets carry Excel tables** (all A1-anchored, single table per sheet): `variant_master`, `section_master`, `PriceRef`, `stingray_options`, `stingray_ovs`, `rule_mapping`, `price_rules`, `grandSport_options`, `grandSport_ovs`, `grandSport_rule_mapping`, `grandSport_price_rules`. Z06 sheets and all metadata sheets have none.
- **Four Grand Sport table refs are already stale** — shorter than the data they sit on: `grandSport_options` data row 274 vs ref `A1:K267`, `grandSport_ovs` 1645 vs `A1:C1597`, `grandSport_rule_mapping` 324 vs `A1:P322`, `grandSport_price_rules` 48 vs `A1:H46`. Prior edits appended rows without extending refs, and `validate_workbook_package.py` does not flag ref-vs-data drift. Phase 2's table maintenance must heal this, not merely avoid worsening it.
- **Cell types are canonical** (real ints/bools, string ids) on all three live options sheets, with one known exception: `z06_options.display_order` is mixed int/str (consistency-review blocker S-1) and `z06_exclusive_members` rows 2–17 likewise. Typed writes therefore *match* the workbook's existing shape; writing native ints/bools is correct, and any `display_order` cell this tool updates on a Z06 sheet gets fixed to int as a side effect rather than degraded.
- Primary keys in all 11 families are string ids (no numeric keys) — row location can use stripped-string comparison without numeric-tolerance complexity.

---

## 2. Design

### 2.1 Op model

All write intent is data. A **single op**:

```json
{"action": "add",    "sheet": "stingray_options", "key": {"option_id": "opt_xyz_001"}, "row": {"option_id": "opt_xyz_001", "rpo": "XYZ", "price": 500, "...": "..."}}
{"action": "update", "sheet": "stingray_options", "key": {"option_id": "opt_xyz_001"}, "row": {"price": 600}}
{"action": "delete", "sheet": "stingray_options", "key": {"option_id": "opt_xyz_001"}}
```

- `add.row` carries every header column (blanks allowed for non-key columns).
- `update.row` carries **only changed columns** — an apply against a workbook that moved underneath never silently reverts untouched cells. Key columns may not appear in `update.row`.
- Values are native JSON types (int, bool, string); `""`/`null` both mean "blank cell" and are written as empty.

A **composite** wraps ops that express one business fact and shows up as one unit in the queue, the log, and validation:

```json
{"kind": "composite", "compositeType": "add_option", "label": "Add option XYZ (stingray)", "ops": [ ...option add, ovs adds, optional rule/member adds... ]}
```

The **batch** (what validate/apply/export consume) is an envelope:

```json
{"version": 1, "workbook": "stingray_master.xlsx", "workbookMtimeNs": 123, "createdAt": "...", "items": [op | composite, ...]}
```

`workbookMtimeNs` is the mtime the client loaded; the server refuses a stale batch (HTTP 409) so the UI must refresh and the user re-verify before applying. The whole batch applies atomically or not at all — composites add semantic grouping and composite-level validation, not a separate transaction boundary.

### 2.2 Coalescing (pure function in `editor_ops.py`)

Per `(sheet, key)` over the flattened batch, in order: update+update → merged update (later column values win); add+update → add with merged row; add+delete → both dropped; update+delete → delete. A delete is a barrier — a later add for the same key stays a separate sequenced op (re-key/replace), never merged across it. Composite members coalesce internally; composites are never merged with outside ops. The UI shows the coalesced view; export and apply use it.

### 2.3 Typed coercion

`coerce_value(family, column, value)` per `EDITOR_SHEET_META`:

- `int` → must be a JSON number with no fractional part (or a digit string from the CLI path); written as native int.
- `bool` → must be JSON true/false; written as native bool. (`variant_overrides.selectable` is the deliberate exception: it is a tri-state *text* enum `""/"True"/"False"` in the meta, and stays text.)
- enum → string, must be in the declared domain.
- ref → string, must exist in the reference domain (see 2.4 for batch-aware resolution).
- everything else → stripped string; empty → blank cell.

Coercion failures are validation errors, never silent conversions.

### 2.4 Non-breaking validation

`validate_batch(extract, batch) -> {errors: [...], warnings: [...]}`, shared verbatim by the server endpoints and the CLI. Reference checks resolve against the workbook extract **plus pending adds earlier in the batch** — that is what lets an Add Option composite reference the option it is itself adding.

**Errors (whole batch refused):**

| Check | Detail |
|---|---|
| sheet unknown / read-only | target must be in the editable registry (the 11 families via `model_workbook_sources`); `form_*` and unregistered sheets are never writable |
| column unknown | every `row`/`key` column must exist in the sheet's header row |
| key invalid | key columns present and non-blank; add: key must not already exist (in sheet or earlier batch adds); update/delete: key must exist |
| type/enum violation | per 2.3 |
| ref violation | referenced option/section/variant/group/interior id not found in domain ∪ batch adds |
| OVS coverage | an add to an options-family sheet requires, in the same batch, an OVS add for **every active variant of that model** (from `model_variants`) — server-enforced, not just UI-shaped |
| group integrity | a `rule_groups` add requires ≥1 member add in batch; an `exclusive_groups` add requires ≥2 member adds; a member add requires its group to exist (sheet or batch) |
| dry-run failure | the batch applied to a temp copy must pass `assert_valid_workbook_package` and `validate_workbook_schema(check_live_contract=False)` with zero errors |

**Warnings (refused unless explicitly confirmed):** each warning carries a stable id the client echoes back in `confirmedWarnings`.

| Check | Detail |
|---|---|
| display-order collision | new/changed `display_order` duplicates another row in the same `(sheet, section_id)` — or the same group for member sheets |
| referenced delete | deleting a key still referenced by known child relationships (options ← ovs/rule_mapping/members/price_rules/color_overrides; groups ← members; interiors ← color_overrides) unless the referencing rows are deleted in the same batch. Lifecycle note: for rule rows the repo convention is `normalization_status`, not deletion — the warning text says so |
| inactive-model target | writing to a sheet whose model is not promoted (zr1/zr1x scaffolds) |

### 2.5 Apply pipeline

`apply_batch(path, batch, confirmed_warnings, source)` in `editor_ops.py` — one implementation behind both the server and the CLI:

1. Refuse if `~$stingray_master.xlsx` exists (`excel_lock_path`).
2. Refuse if `path.stat().st_mtime_ns != batch.workbookMtimeNs` (409-equivalent for the CLI).
3. Load workbook (writable), build extract, run `validate_batch`; abort on errors or unconfirmed warnings.
4. **Dry-run:** copy the file to a temp path, apply the coalesced ops to the temp workbook, save, run package + schema validation on it; abort on any failure. Nothing real has been touched.
5. Apply the coalesced ops to the in-memory workbook: adds append after the last data row; updates write only the op's columns; deletes use `ws.delete_rows`.
6. **Table maintenance:** for any touched sheet with an A1-anchored table, resize the ref to exactly span header row through last data row at full header width. This both keeps refs correct for our edits and **heals the pre-existing Grand Sport drift** the first time those sheets are touched. Sheets without tables never get one.
7. `save_workbook_safely(wb, path, loaded_mtime_ns=...)` — backup, package check, atomic replace.
8. Append one JSON line to `form-output/workbook-edit-log.jsonl`: `{"ts", "source": "server"|"cli", "opCount", "composites": [labels], "sheets": [...], "backupPath", "schemaErrors": 0, "warningsConfirmed": [...]}`. The log is committed (decision §9.2 of the parent spec).
9. Return `{applied, backupPath, schemaResult, logPath, gateReminders}` where `gateReminders` lists the AGENTS.md generator/test commands for the touched model(s).

Apply never runs generators or tests — regeneration stays a deliberate, separate step per the Workbook Update Workflow. A failed schema validation after a real save cannot happen by construction (step 4 validated the identical end state), but if `save_workbook_safely` itself throws, nothing was replaced and the temp file is cleaned up by that helper.

### 2.6 Server endpoints

```text
POST /api/validate  {batch}                       -> 200 {ok, errors, warnings, coalesced}
POST /api/apply     {batch, confirmedWarnings}    -> 200 {applied, backupPath, schemaResult, gateReminders}
                                                  -> 409 stale workbook | 422 validation errors/unconfirmed warnings
```

Write-request hardening (the server writes files, so cross-site POST matters even on localhost): non-GET requests must carry `Origin` matching the server's own origin (or no Origin, for the CLI/curl case) and a `Content-Type: application/json`; anything else is 403. Server stays bound to 127.0.0.1.

After a successful apply the workbook mtime changes, the `WorkbookCache` re-extracts on the next request, and the UI re-fetches `/api/workbook` plus the open sheet.

### 2.7 CLI — `scripts/apply_workbook_ops.py`

```sh
.venv/bin/python scripts/apply_workbook_ops.py ops.json            # validate + dry-run only (default)
.venv/bin/python scripts/apply_workbook_ops.py ops.json --write    # full apply
.venv/bin/python scripts/apply_workbook_ops.py ops.json --write --confirm-warnings W1,W2
```

Same `editor_ops` code path; `--write` mirrors `promote_model.py`'s flag convention. This is the review-then-apply route: export ops.json from the UI, read it in a PR or spec discussion, apply later — and the identical validation runs regardless of which door the batch comes through.

### 2.8 UI

**Row editing (Sheet Browser).** Editable sheets get Add Row / Edit / Delete. The edit form is fully structured per the served meta: enums → selects, refs → searchable pickers fed by `referenceDomains` (options pickers show `RPO — name` and store the id), ints → number inputs, bools → checkboxes, key columns immutable on edit, free text only for name/description/notes/detail columns. Delete asks for a real confirmation (the Phase 1 spec already removed the dead `window.confirm` stub).

**Guided composite flows** (the §4.4 wizards):

- **Add Option** (per model): step 1 option fields — section picker, `display_order` prefilled to (max in section + 10) with live collision warning; step 2 an **OVS grid with one status select per active variant of the model, every cell starting blank and required** (with a "set all to…" bulk control for convenience — explicit selection is still required, prefilled defaults are not); step 3 optional rule rows, rule-group memberships, exclusive-group memberships via pickers. Emits one composite.
- **Add Rule Group**: group fields + a member picker grid (≥1 member enforced in-form and server-side).
- **Add Exclusive Group**: group fields + member grid (≥2 members), `display_order` auto-stepped by 10.

**Pending Changes tab** (the third tab returns): coalesced queue with per-op old→new cell diff, composite grouping with labels, remove-from-queue, **Validate** (calls `/api/validate`, renders errors/warnings inline), warning confirmation checkboxes, **Apply**, **Export ops.json**, and a result panel showing backup path, schema status, and the gate-reminder commands. The tab badge shows the queued-op count like the original component did.

### 2.9 Editable surface — deliberately narrow

Phase 2 writes only to the 11 model-scoped families registered through `model_workbook_sources`. Metadata sheets (`section_master`, `runtime_steps`, `section_presentation`, `model_variants`, …) remain read-only: they have cross-cutting runtime impact, no `source_role` registration, and editing them safely needs its own guided flows. Extending the editable registry later is additive — a meta entry plus validation rules — and should arrive as its own approved pass.

---

## 3. Exact Files

| File | Action |
|---|---|
| `scripts/corvette_form_generator/editor_ops.py` | extend — op schema, `coerce_value`, `coalesce_batch`, `validate_batch`, `apply_batch`, table-ref maintenance, edit-log append |
| `scripts/workbook_editor_server.py` | extend — POST handlers, origin/content-type checks, stale-mtime guard |
| `scripts/apply_workbook_ops.py` | new CLI |
| `visualizer/workbook-editor/editor.js`, `editor.css` | extend — edit forms, wizards, Pending Changes tab |
| `tests/test_editor_ops_apply.py` | new — coercion matrix, coalescing rules, validation matrix (each error/warning class), apply round-trip on a temp workbook copy, table-ref healing (incl. the stale-GS-ref fixture case), lock/mtime refusal, log-line shape |
| `tests/test_editor_server_write_api.py` | new — endpoint tests against a `ThreadingHTTPServer` on an ephemeral port with a temp workbook: 409 stale, 422 errors, warning confirmation flow, 403 bad origin, successful apply + cache refresh |
| `form-output/workbook-edit-log.jsonl` | created by first real apply; committed thereafter |
| `README.md`, `AGENTS.md` | update the review-tool sections: write path, CLI, the rule that editor applies still require the per-model gates before the change is "done" |
| `workbook-editor-integration-spec.md` | one-line pointer from §5 Phase 2 to this spec |

## 4. Constraints (repeated back)

All parent-spec §7 constraints hold, plus the Phase 2 specifics:

- Every write goes through `save_workbook_safely()`; no other save call may exist in the new code.
- Non-breaking only: server-side validation refuses the whole batch on any error; warnings require explicit confirmation; the dry-run end state must pass package + schema validation before anything real is touched.
- No free text in the UI for schema-constrained fields; pickers/enums/typed inputs only.
- Editable surface limited to the 11 registered families; `form_*` and metadata sheets stay read-only.
- No new dependencies (stdlib + openpyxl; no npm).
- Scripts stay generic — no model-specific business branches; the workbook expresses the rules.
- Apply never regenerates artifacts or runs tests; it reminds.
- Localhost only; write endpoints origin-checked.

## 5. Risks and Non-Goals

**Risks**

- *Table-ref maintenance* is the riskiest mechanical piece. Mitigations: resize-to-data-extent strategy (idempotent, self-healing), `assert_valid_workbook_package` inside the save, dedicated unit tests including a stale-ref fixture, and a manual Excel-open check in the validation plan.
- *Healing the Grand Sport refs* changes table XML beyond the edited rows on the first GS-sheet apply. Mitigation: called out in the handoff of that first apply; regenerate GS inspection artifacts and diff with `scripts/compare-generated-contracts.mjs` to prove generated output is unchanged (table refs are invisible to `rows_from_sheet`, so no change is expected).
- *Dry-run cost*: one temp-copy save + schema validation per validate/apply (seconds). Acceptable for a deliberate edit tool; not a perf surface.
- *Concurrent edits*: covered by the mtime guard at batch level and `save_workbook_safely`'s lock/mtime refusals at save time. Two browser tabs racing produce a 409 for the loser, never interleaved writes.
- *CSRF toward a file-writing localhost server*: origin + content-type checks on non-GET (above).

**Non-goals**

- Phase 3 surfaces (lint panel, cross-model comparison, whole-sheet diff beyond the queue's per-op diff).
- Undo of applied batches — `backups/` plus the apply log are the recovery path.
- Editing metadata sheets, generated sheets, or `archive/stingray_archive.xlsx`.
- Running generators/tests from the tool; multi-user; deployment.
- Fixing existing data findings (S-1 retyping, copy convergence) — the tool makes those passes easier; they remain their own approved passes.

## 6. Validation Plan

- **Unit:** `test_editor_ops_apply.py` covers every validation class with positive/negative cases, the full coalescing table from §2.2, typed round-trips (int/bool/enum/blank), table-ref healing against a fixture that reproduces the GS drift, and lock/mtime refusal.
- **API:** `test_editor_server_write_api.py` covers 409/422/403 paths, the warning-confirmation handshake, and a successful apply asserting the workbook mtime advanced, a backup landed, and the next `GET /api/workbook` reflects the change.
- **End-to-end on a scratch copy** (`--workbook` flag points the server at a copy): run the Add Option wizard for stingray → validate → apply → `validate_workbook_schema.py` and `validate_workbook_package.py` green → open the copy in Excel and confirm the table ranges include the new rows → CLI-apply the exported ops.json to a second copy and diff the two copies for equality.
- **Repo gates before merge:** full Python unittest discovery; `node --test` suites untouched by this work but run once as regression evidence; canonical workbook untouched during development (`git status stingray_master.xlsx` clean — all write tests run on temp copies).
- **First real apply after merge** (whenever a real edit happens): follows the AGENTS.md Workbook Update Workflow — regenerate affected model, run its gates, review diffs — exactly as if the edit had been made by hand, with the apply-log line as evidence.

## 7. Open Questions

None blocking. Two decisions made in this spec that you can veto cheaply now:

1. **OVS grid starts blank and forces a choice per variant** (with a bulk "set all to…" helper) rather than prefilling a default status. Rationale: §4.4's "the user sets" + a wrong prefilled `available` is a silent business error.
2. **Editable surface stays at the 11 families** (no metadata-sheet editing) for this phase — §2.9.
