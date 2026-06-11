# Workbook Editor Integration Spec

Date: 2026-06-11
Subject: `visualizer/workbook-editor.jsx` (committed 488801f) — integrate it into the repo as a working workbook review/edit tool.
Status: draft for review, no implementation yet.

---

## 1. Diagnosis

**What exists.** `visualizer/workbook-editor.jsx` is a 1,191-line React component with three tabs (Form Structure, Model Operations, Audit & Export). It renders model cards, runtime steps, per-model sheet tables with add/edit/delete forms, a pending-operations queue, and a downloadable openpyxl script that replays the queue against `stingray_master.xlsx`.

**Why it cannot run today.** The repo has no `package.json`, no React, no Tailwind, no lucide-react, and no bundler. The customer app (`form-app/`) is deliberately build-free, and `visualizer/visualizer.js` is a dependency-free IIFE. The JSX file is dead code as committed — there is no execution path.

**Why its current design conflicts with repo rules.** Three conflicts, all fixable:

1. **Hardcoded workbook duplicates.** `MODELS`, `STEPS`, `SECTION_NAMES`, `MODEL_SHEETS`, `SCHEMAS`, and `SEED_ROWS` restate content owned by workbook sheets (`model_master`, `runtime_steps`, `section_master`/`section_presentation`, `model_workbook_sources`, and the data sheets themselves). AGENTS.md: business data and runtime metadata belong in the workbook; tooling should read it, not restate it. The copies are already drifting — the editor hardcodes 14 steps vs. 29 model-scoped rows in `runtime_steps`, covers 11 sheet schemas out of ~66 active sheets, and reuses one `variant_overrides` schema for both the shared `variant_option_overrides` sheet and the model-specific `*_variant_overrides` sheets, which the sheet index documents as having different schemas.
2. **Unsafe write path.** The generated script does a bare `load_workbook()` → mutate → `wb.save()`. That bypasses everything `scripts/corvette_form_generator/workbook.py` exists to enforce: the Excel lock-file check, the load-mtime conflict check, `remove_table_sheet_auto_filters()`, `assert_valid_workbook_package()`, timestamped backup, and atomic replace. The workbook uses Excel tables (`repair_workbook_tables.py` exists because bare openpyxl saves have corrupted them before), and `ws.append()` does not extend table ranges, so added rows would land outside table definitions. No validation gate runs after the write.
3. **Type erasure.** Every cell value round-trips as a string. The 2026-06-11 consistency review's only structural Blocker (S-1) is string-typed `display_order` on `z06_options`; this editor as designed would write string-typed numbers and booleans across every sheet it touches, scaling that defect up rather than fixing it.

**Risk level:** the integration itself is medium-risk because it creates a new write path to the canonical workbook. The spec phases the work so the write path lands last, behind the same gates the existing scripts use.

**Change class:** mixed — new dev tooling (Python + static UI), one new script surface, docs. No customer-runtime changes, no generated-artifact changes, no workbook data changes.

---

## 2. Goal

A local developer tool that makes `stingray_master.xlsx` easy to **review** (browse real sheets, search, compare models, see the lint findings the consistency review had to script by hand) and makes **edits safe to implement** (typed, validated, queued, reviewable, applied through `save_workbook_safely()` with gates).

It is a dev tool. It must never ship in `form-app/`, never touch the dealer-submission path, and never become an alternate source of truth.

---

## 3. Approaches Considered

**A. Static export + script download (minimal).** A repo script dumps workbook sheets to JSON; the browser UI loads the JSON; edits still export a script the developer runs by hand.
*Pros:* no server. *Cons:* data goes stale the moment the workbook changes; the apply path stays manual and unsafe unless the developer remembers the gates; two artifacts to keep in sync.

**B. Local Python server + browser UI (recommended).** A stdlib-only `scripts/workbook_editor_server.py` serves (a) the static UI, (b) `GET /api/workbook` — sheets, schemas, and metadata derived live from the workbook via the existing `corvette_form_generator` helpers, and (c) `POST /api/apply` — an ops payload applied through `save_workbook_safely()` with schema validation, returning gate results. The UI keeps the existing component's structure but runs without a build step (see §4.2).
*Pros:* always-current data; one write path that reuses the repo's safety machinery; validation results surface in the UI; zero new pip/npm dependencies (stdlib `http.server` + existing openpyxl). *Cons:* a long-running local process; modest server code to maintain.

**C. Full Node/Vite subproject.** A real frontend project under `visualizer/workbook-editor/` with npm dependencies.
*Pros:* keeps the JSX file nearly as-is; nicest DX. *Cons:* introduces `node_modules` and a build step into a repo that has deliberately avoided both; heaviest violation of the "no new dependencies" constraint for the least functional gain.

**Recommendation: B.** It is the only approach where review data is live and the write path is safe by construction. Approach A's ops-export survives inside B as an offline fallback (§4.4).

---

## 4. Design

### 4.1 Components

```text
stingray_master.xlsx  (canonical, unchanged role)
        │ read (openpyxl, read-only)
        ▼
scripts/workbook_editor_server.py        stdlib http.server, localhost only
  GET  /                                 serves visualizer/workbook-editor/ static UI
  GET  /api/workbook                     models, sheet registry, schemas, reference domains, lints
  GET  /api/sheet/<name>                 rows for one sheet (on demand; keeps the registry payload small)
  POST /api/validate                     dry-run: apply ops to a temp copy, run schema validation
  POST /api/apply                        apply ops via save_workbook_safely(), return gate results
        │ shared logic
        ▼
scripts/corvette_form_generator/editor_ops.py   pure functions: op schema, coalescing,
                                                typed coercion, apply-to-workbook
scripts/apply_workbook_ops.py                   CLI: apply an exported ops.json (offline path)
```

### 4.2 UI runtime — no build step

Convert `workbook-editor.jsx` into a static page under `visualizer/workbook-editor/` (`index.html`, `editor.js`, `editor.css`):

- **Preact + htm via ESM import map**, vendored into `visualizer/workbook-editor/vendor/` (two small files, committed). No npm, no bundler, works offline, and the existing component's hooks/JSX structure ports almost mechanically (`html\`...\`` instead of JSX).
- **Tailwind classes replaced by a small hand-written `editor.css`** reproducing the current dark layout. The styling is simple enough (panels, pills, table) that this is bounded work; a CDN Tailwind script is the fallback if the user prefers, at the cost of requiring network.
- **lucide-react replaced** with a handful of inline SVGs or text glyphs.

The original `visualizer/workbook-editor.jsx` is deleted once the port lands (it has no other consumer).

### 4.3 Server data contract — derive, don't restate

`GET /api/workbook` builds its payload from the workbook itself:

- **Models** from `model_master` + `model_registry_promotion` (replaces hardcoded `MODELS`).
- **Steps and sections** from `runtime_steps`, `context_section_master`, `section_master`, `section_presentation` (replaces `STEPS`/`SECTION_NAMES`).
- **Per-model sheet registry** from `model_workbook_sources`, with the known transition-state caveat (Z06 rows marked inactive there) handled the same way the generator handles it — fall back to the model config in `corvette_form_generator/model_configs.py`. (Replaces `MODEL_SHEETS`.)
- **Schemas** derived per sheet: headers from row 1; primary-key columns, enum domains, and column types from a single new `editor_sheet_meta` registry — a small Python dict in `editor_ops.py` (key columns + type per column: str/int/bool/enum), seeded from the current `SCHEMAS` constant and extended to all active source/metadata sheets. Enum domains are computed from observed column values plus the declared allowlist, so the UI dropdowns reflect reality.
- **Read-only classification**: generated `form_*` sheets and any sheet not in the editable registry are served with `readOnly: true`; the UI shows them (review value) but disables editing.
- **Reference domains** for guided editing: the pick lists structured inputs need — sections from `section_master`, variants per model from `variant_master`/`model_variants`, options per model (`option_id` + RPO + name), step keys from `runtime_steps`, group ids from the group sheets. Phase 1 serves them; Phase 2's guided forms consume them.
- **Lints** (Phase 3, §5): display-order collisions per (sheet, section), duplicate primary keys, cross-model copy/order drift for shared option_ids, orphan references — the checks the 2026-06-11 consistency review performed by hand.

Hardcoding is eliminated except for the one thing the workbook genuinely doesn't own: which columns form each sheet's primary key and their types (`editor_sheet_meta`). That lives in Python next to the generator, in one place, not in the UI.

### 4.4 Edit and apply path

**Non-breaking writes are a hard rule.** The tool may only produce edits that leave the workbook referentially intact and schema-valid. That is enforced at both ends:

- **Guided structure in the UI — no free text for schema-constrained fields.** Enum columns render as selects from the served domain; reference columns (`section_id`, `option_id`, `variant_id`, `group_id`, `target_id`, step keys, interior ids) render as pickers fed by the reference domains in §4.3; numeric columns are numeric inputs. Free text is reserved for genuinely free-text columns: names, descriptions, notes, raw-detail copy.
- **Composite guided flows for multi-sheet facts.** Some business facts span sheets, and a partial write is a broken write. "Add Option" is a wizard, not a row form: the option row, plus a required OVS status (from the `status` enum) for **every active variant of the model** — no partial OVS coverage — plus optional rule rows, rule-group memberships, and exclusive-group memberships attached in the same flow with picker-driven fields. The queue stores the result as one grouped op set; it applies atomically or not at all. The same pattern covers "add rule group" (group + at least one member) and "add exclusive group" (group + ≥2 members).
- **Server-side non-breaking validation.** Apply runs the dry-run pipeline internally and refuses the whole batch on any error: unknown sheet/column, unknown reference (option, section, variant, group), duplicate primary key, missing OVS coverage for a new option, type violation, or schema-validator failure on the temp copy. Display-order collisions and deletes of still-referenced keys surface as warnings requiring explicit confirmation. The server is the authority; a hand-edited ops.json fed to the CLI passes through the identical checks in `editor_ops.py`.

Mechanics:

- The UI keeps the queue model: edits accumulate as ops `{action: add|update|delete, sheet, key, row}` — optionally grouped into composite sets — and nothing touches the workbook until apply.
- **Typed values end-to-end.** The server emits cell values with their types; the UI edits ints as ints, booleans as real booleans (checkbox/select), enums from the served domain; ops carry JSON types; `editor_ops.py` coerces per `editor_sheet_meta` before writing. This makes the tool fix-shaped, not S-1-shaped.
- **Queue coalescing** in `editor_ops.py` (shared by server and CLI): multiple updates to one key collapse to the last; add+update collapses into the add; add+delete cancels; update+delete collapses to delete.
- **Update semantics:** ops carry only changed columns (not the full row) so an apply against a workbook that moved under you doesn't silently revert other cells; key columns stay immutable on update (the UI already enforces this).
- **Apply** (`POST /api/apply` and `scripts/apply_workbook_ops.py` sharing `editor_ops.apply()`):
  1. refuse if `~$stingray_master.xlsx` lock exists (reuse `excel_lock_path`);
  2. load, record mtime;
  3. apply ops — adds must extend the sheet's Excel table range (`ws.tables`) in addition to appending; updates/deletes locate rows by key columns with typed comparison; delete also warns (not blocks) if the key is referenced by known child sheets (e.g. deleting a `rule_groups` row that still has `rule_group_members`);
  4. `save_workbook_safely(wb, path, loaded_mtime_ns=...)` — backup, package check, atomic replace;
  5. run `scripts/validate_workbook_schema.py`; return its result to the caller. A failed validation is reported loudly with the backup path; the tool does not auto-rollback (the backup makes recovery a copy).
- **Dry-run** (`POST /api/validate`): same pipeline against a temp copy, no backup, no replace — the UI offers "Validate" before "Apply".
- **Ops export stays** — but as `workbook-ops-<date>.json` (reviewable, diffable, applyable later via the CLI), replacing the bespoke generated Python script. The script generator (`buildOpenpyxlScript`) is deleted: it duplicates apply logic in a second language with none of the safety.
- **Apply log:** each successful apply appends a line to `form-output/workbook-edit-log.jsonl` (timestamp, op count, sheets touched, backup path, validation status) so handoff reports have evidence.

What apply deliberately does **not** do: run generators or regenerate `form-app/data.js`. Workbook writes and artifact regeneration stay separate, exactly as the AGENTS.md workflows define them. The UI instead shows a post-apply reminder listing the relevant gate commands for the touched model(s).

### 4.5 What is removed from the current component

| Item | Why |
|---|---|
| `SEED_ROWS` | replaced by live data |
| `MODELS`, `STEPS`, `SECTION_NAMES`, `MODEL_SHEETS` constants | derived from the workbook (§4.3) |
| `SCHEMAS` constant in JS | moves to `editor_sheet_meta` in Python, served via API |
| `buildOpenpyxlScript` + "Download .py" | replaced by ops-JSON export + `apply_workbook_ops.py` |
| dead `if (!window.confirm)` block in `removeRow` | dead code; replace with a real confirm on delete |
| separate Audit Trail list | redundant with the pending-ops queue pre-apply and the persisted apply log post-apply; one history surface, not two |
| `humanize()` heuristics (`grandSport`→`grand_sport`, acronym list) | display labels come from workbook metadata where they exist; raw sheet names otherwise |

The **Form Structure tab survives** but becomes a read-only rendering of served `runtime_steps`/section metadata per model — useful review surface, no longer a drift hazard.

### 4.6 What is kept as-is

The overall three-tab shape, the queue-then-apply mental model, key-field requiredness, key immutability on edit, enum dropdowns, and the visual design. The component's UX instincts are right; the spec replaces its data and write plumbing, not its shape.

---

## 5. Phasing

**Phase 1 — Read-only review tool.** Server with `GET /api/workbook` only; UI port (Preact/htm/CSS) with browse, full-column view (expandable row detail instead of the current 6-column truncation), text search/filter per sheet, and pagination or windowing for the 1,600-row OVS sheets. No write surface at all. *This already replaces ad-hoc scripting for review work and carries zero workbook risk.*

**Phase 2 — Edit queue + safe apply.** `editor_ops.py` op logic, typed editing, coalescing, the guided forms and composite flows from §4.4 (Add Option with full OVS coverage, group + members), server-side non-breaking validation, dry-run validate, apply endpoint, `apply_workbook_ops.py` CLI, ops-JSON export, apply log, delete-reference warnings.

**Phase 3 — Review enhancements (each independently shippable).**
- **Lint panel:** display-order collisions, duplicate keys, orphan `option_id`/`section_id`/group references — surfaced per sheet and as a summary.
- **Cross-model comparison view:** join `*_options` rows by `option_id` (RPO fallback for the known `_002` Z06 keys), highlight name/description/order/section divergence with an intentional-differences allowlist — this is the durable version of the consistency review's §3–§4 method, and directly supports the planned Stingray copy-convergence pass.
- **Sheet-level diff view:** pending ops rendered as old→new per cell before apply.

Phases 2 and 3 each get their own approval per spec-first rules; this spec authorizes designing toward them, not building past Phase 1 without sign-off.

---

## 6. Exact Files

| File | Phase | Action |
|---|---|---|
| `visualizer/workbook-editor/index.html`, `editor.js`, `editor.css`, `vendor/preact.mjs`, `vendor/htm.mjs` | 1 | new — ported UI |
| `visualizer/workbook-editor.jsx` | 1 | delete after port |
| `scripts/workbook_editor_server.py` | 1 (GET) / 2 (POST) | new |
| `scripts/corvette_form_generator/editor_ops.py` | 1 (`editor_sheet_meta`) / 2 (op logic) | new — sheet meta registry in Phase 1; op schema, coalesce, typed apply, non-breaking validation in Phase 2 |
| `scripts/apply_workbook_ops.py` | 2 | new CLI |
| `tests/test_editor_ops.py` | 2 | new — coalescing, typed coercion, apply-to-temp-workbook round-trip, table-range extension, lock/mtime refusal |
| `tests/test_editor_server_payload.py` | 1 | new — payload derivation matches workbook metadata (models, steps, schemas, read-only flags) |
| `form-output/workbook-edit-log.jsonl` | 2 | new generated log, committed (workbook edits affect runtime and must be traceable — §9) |
| `README.md`, `AGENTS.md` | 1–2 | document the tool, its boundaries, and the apply workflow |

---

## 7. Constraints (repeated back)

- `stingray_master.xlsx` remains the single source of truth; the editor derives, never restates, and never caches across sessions.
- No new pip dependencies (stdlib + existing openpyxl); no npm/node_modules/build step (vendored Preact+htm are static files, not a toolchain).
- Nothing in `form-app/` changes; the dealer-submission endpoint, payload, and Turnstile behavior are untouched.
- All workbook writes go through `save_workbook_safely()` with lock and mtime checks; no write path may bypass it.
- Writes are non-breaking only: server-side referential/coverage validation gates every apply (whole batch refused on error), and schema-constrained fields are never free text in the UI (§4.4).
- Generated `form_*` sheets are never editable through the tool.
- Scripts stay procedural and generic — no model-specific business exceptions in the server or ops code.
- Server binds to localhost only; it is a dev tool, never deployed.
- Spec-first: Phases 2 and 3 require approval before implementation.

## 8. Risks and Non-Goals

**Risks**
- *A second write path to the canonical workbook.* Mitigated by routing through the same helpers and gates as `promote_model.py`/`production.py`, dry-run validation, backups, and the apply log — but it is still new surface; Phase 2 lands only after Phase 1 has been used in anger.
- *Excel-table range handling on `ws.append`* is the trickiest apply detail; covered by a dedicated round-trip test plus `validate_workbook_package.py` in the apply pipeline.
- *Concurrent editing* (Excel open while the server holds stale rows): mitigated by the lock-file refusal and mtime check at apply time; the UI also re-fetches and re-verifies keyed rows still match before queueing an apply.
- *UI port fidelity* — Preact/htm port could introduce subtle behavior differences; mitigated by Phase 1 being read-only and visually checkable.

**Non-goals**
- Editing `archive/stingray_archive.xlsx` or any backup.
- Triggering generators, tests, or promotion from the tool (it reminds; the developer runs gates per AGENTS.md).
- Multi-user or remote use, auth, or deployment.
- Fixing the consistency-review findings themselves (the tool is how those passes get easier, not the pass).
- Visualizer (`visualizer.js`) integration — separate concern, shared folder only.

## 9. Decisions (resolved 2026-06-11)

1. **UI runtime:** vendored Preact+htm, as recommended.
2. **Apply log:** committed — workbook edits affect runtime, so the trail must be traceable in history.
3. **Scope:** master workbook only; the server never reads `archive/stingray_archive.xlsx`.
4. **Form Structure tab:** kept as a simple read-only reference.
5. **Write posture (added requirement):** non-breaking writes only, with guided structure — composite Add Option flow with full OVS coverage, picker/enum inputs for all schema-constrained fields, server-side batch validation. Folded into §4.4 and §7.

## 10. Validation Plan

- **Phase 1:** `tests/test_editor_server_payload.py` (payload vs. workbook ground truth); manual browser check against known workbook facts (row counts from `workbook-sheet-index.md`, Z06 promoted, ZR1/ZR1X scaffold); confirm zero writes (workbook mtime unchanged after a full review session).
- **Phase 2:** `tests/test_editor_ops.py` (coalescing, typing, table extension, lock/mtime refusal, round-trip on a temp workbook copy); end-to-end on a scratch copy: queue add/update/delete → dry-run → apply → `validate_workbook_schema.py` → `validate_workbook_package.py` → open in Excel to confirm table integrity; verify a backup landed in `backups/`.
- **Always:** existing gates stay green — `validate_workbook_schema.py`, Stingray/GS/Z06 generator runs and their `node --test` suites are untouched by Phases 1–2 (no generator code changes) but run once before merge as regression evidence.
