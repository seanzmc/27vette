# Workbook Editor Phase 3 Spec — Lint Panel & Cross-Model Comparison

Date: 2026-06-12
Parent: `workbook-editor-integration-spec.md` §5 Phase 3. Phases 1–2 shipped and merged (Phase 2: fe7ab79 and prior, full suite green).
Status: draft for approval, no implementation yet.

---

## 1. Diagnosis

**What exists after Phase 2.** The editor server derives all metadata live from
the workbook; `editor_ops.py` already implements, for *pending batches*, most
of the checks Phase 3 needs for the *existing workbook*: duplicate-key
detection, reference-domain resolution (`_registry_maps`, `_ref_domain`),
display-order collision detection (`_DORDER_GROUP_COL`), OVS coverage, and
group integrity. The 2026-06-11 consistency review
(`workbook-consistency-review-2026-06-11.md`) produced its findings with
throwaway `/tmp/` scripts; none of that method is durable.

**What Phase 3 adds.** Two read-only review surfaces that make the
consistency-review method permanent:

1. **Lint panel** — structural checks against the current workbook state
   (not pending ops), per sheet and as a summary.
2. **Cross-model comparison view** — `*_options` joined across
   Stingray/GS/Z06 by `option_id` with RPO fallback for the known Z06 `_002`
   keys (review S-4), highlighting name/description/section/display-order
   divergence, majority-vs-deviator labeled, filtered through an
   intentional-differences allowlist seeded from review §5.

The integration spec's third Phase 3 item — sheet-level old→new diff of
pending ops — **already shipped in Phase 2** (Pending Changes tab,
`editor.js` `PendingTab` diff cells). Phase 3 drops it from scope.

**Risk level: low.** Read-only throughout — no write surface changes, no
workbook data changes, no generated artifacts, no runtime changes. The op
engine and apply pipeline are untouched.

**Change class:** mixed dev tooling — new Python lint module, two new GET
endpoints, UI tab work, one committed allowlist data file, tests, docs.

**Evidence inspected:** `editor_ops.py` validation helpers (lines 308–600),
`workbook_editor_server.py` `WorkbookCache`/`build_payload`/`do_GET`,
`editor.js` tab shell + `PendingTab`, consistency review §2–§6,
`option_audit_groups`/`rule_review_groups` headers (verified: they own
rule-audit focus groups, not a per-option per-field cross-model allowlist —
no existing sheet owns that relationship).

---

## 2. Design

### 2.1 Lint module — `scripts/corvette_form_generator/editor_lints.py` (new)

Pure functions over the existing `extract_workbook()` dict. Reuses
`editor_ops` helpers (`_registry_maps`, `_sheet_key_index`,
`_DORDER_GROUP_COL`, `EDITOR_SHEET_META`) rather than duplicating them —
where a helper needs to be shared, it is imported, not copied.

Checks (each tagged with the consistency-review finding class it makes
durable):

| Lint id | Check | Review precedent |
|---|---|---|
| `duplicate_key` | duplicate primary key within a sheet family | §2 baseline |
| `display_order_collision` | duplicate `display_order` within (sheet, section_id) for options; within (sheet, group_id) for member sheets | D-1, D-2, D-3 |
| `display_order_type` | non-integer-typed `display_order` cells (string `'72'` vs `72`) | S-1, S-2 |
| `orphan_ref` | reference columns pointing at unknown option/section/variant/group ids, per `EDITOR_SHEET_META` refkinds | §2 baseline |
| `ovs_coverage` | active selectable option lacking an OVS status row for an active variant of its model | Phase 2 add-rule, applied to existing rows |
| `group_integrity` | exclusive group with <2 active members; rule group with 0 members; member row whose option is inactive/missing | S-7 class |
| `boolean_text` | text `'TRUE'`/`'FALSE'` in boolean-typed columns | S-10 |

Output shape: `{lints: [{id, severity, sheet, model, key, message, cells}]}`
with `severity ∈ {error, warning, info}` mapped from the review's
Blocker/Inconsistency/Cosmetic scale. Lints are informational — they never
block applies (pending-batch validation already gates writes independently).

### 2.2 Cross-model comparison — same module

`compare_options(extract, allowlist)`:

- Join rows of `stingray_options` / `grandSport_options` / `z06_options` by
  `option_id`; for ids with no cross-model match, fall back to RPO join (the
  S-4 `_002` keys: U2K, U5G, UE1, VV4, CFV). Rows with neither match are
  listed as model-only (single-model options — expected, not flagged).
- For each shared option, diff `option_name`, `description`, `section_id`,
  `display_order` (relative order within section, not absolute value).
- Label majority vs deviator when 2-of-3 agree (the review's method: GS+Z06
  majority, Stingray deviator for C-2).
- Suppress rows matched by the allowlist; suppressed rows remain visible
  behind a "show intentional" toggle with the allowlist reason attached.

### 2.3 Intentional-differences allowlist — decision point

The allowlist entries are business judgments ("Z06 VYW copy intentionally
differs — Z06 gets its own logo mat"). Seed content: review §5 plus the §6
R-items marked `pending-review` (R-1…R-6 surface as flagged-but-annotated,
not suppressed, until each is decided).

Options for where it lives:

- **(a) Committed JSON file** `visualizer/workbook-editor/intentional-differences.json`,
  schema `{option_id|rpo, field|"*", models, reason, status: intentional|pending-review}`.
  Consumed by the server and, later, by the review-rec-7 parity test —
  one allowlist, two consumers. Zero workbook changes; Phase 3 stays
  fully read-only. Editing it is a normal code-reviewed file change.
- **(b) New workbook sheet** (e.g. `option_copy_intent`). Workbook-first by
  philosophy, and editable through the tool itself — but it adds a new
  review taxonomy alongside `option_audit_groups`/`rule_review_groups`,
  requires schema-validator + `model_workbook_sources` registration, and
  makes Phase 3 a workbook-writing pass.
- **(c) Python constant** in `editor_lints.py`. Smallest, but couples test
  and tool to code internals and is the least reviewable as data.

**Recommendation: (a).** The workbook-can-represent-it argument is real, but
(b) creates exactly the parallel review taxonomy you've asked to avoid, for
metadata whose only consumers are dev tooling and tests. If the allowlist
later proves business-shaped (e.g. generators need it), migrating JSON → sheet
is a clean follow-up pass.

### 2.4 Server + UI

- `GET /api/lints` and `GET /api/compare` — computed on demand, cached in the
  existing `WorkbookCache` keyed by workbook mtime (full-workbook copy
  comparison over ~700 option rows is sub-second; no precomputation needed).
- UI: one new **Review** tab with two panels (Lints, Cross-Model Compare),
  matching the existing tab shell. Lints panel: summary counts by severity,
  filter by sheet/model/lint id, click-through to the sheet browser row.
  Compare panel: per-option diff rows, majority/deviator badges,
  intentional toggle, filter by field/model. No edit affordances and no
  "queue fix" buttons in this pass (see non-goals).

### 2.5 What this deliberately does not change

`editor_ops.py` apply/validate behavior, `apply_workbook_ops.py`, the write
API, `form-app/`, generators, generated artifacts, the workbook.

---

## 3. Exact Files

| File | Action |
|---|---|
| `scripts/corvette_form_generator/editor_lints.py` | new — lint + compare functions |
| `scripts/workbook_editor_server.py` | edit — two GET endpoints, cache wiring |
| `visualizer/workbook-editor/editor.js`, `editor.css` | edit — Review tab |
| `visualizer/workbook-editor/intentional-differences.json` | new (pending decision §2.3) |
| `tests/test_editor_lints.py` | new — see §6 |
| `README.md`, `AGENTS.md` | edit — document the Review tab and allowlist |

## 4. Constraints (repeated back)

- Read-only pass: no workbook writes, no generated-artifact changes, nothing
  in `form-app/`, dealer-submission path untouched.
- No new dependencies (stdlib + existing openpyxl; vendored Preact only).
- No model/RPO-specific exceptions in lint code — checks are generic over
  `EDITOR_SHEET_META`; model-specific knowledge lives only in the allowlist
  data file with per-entry reasons.
- Lints never gate applies; the Phase 2 batch validator remains the write
  authority.
- Server stays localhost-only dev tooling.
- Spec-first: implementation waits for approval, including the §2.3 decision.

## 5. Risks and Non-Goals

**Risks**

- *False positives eroding trust* — e.g. flagging per-trim seat-row
  multiplicity (review R-6) as duplicate keys. Mitigated by building the
  lint expectations directly from the review's verified findings (§6) and
  by the pending-review annotation channel for §6 items.
- *Allowlist staleness* — entries outliving the divergence they excuse.
  Mitigated: compare output flags allowlist entries that no longer match any
  divergence (`stale_allowlist` info lint).
- *Payload size* — compare view is per-option rows for ~162 shared options;
  trivially small. No risk to the existing payload contract.

**Non-goals**

- Fixing any finding (S-1 retyping, WKS group membership, Stingray copy
  convergence are their own approved passes; this tool is how they get
  easier).
- "Queue fix from lint" one-click affordances — write-path coupling deferred
  until the panel has been used in anger, same posture as Phase 1→2.
- Parity-test extension of `workbook-visual-copy-standardization.test.mjs`
  (review rec 7) — separate pass; Phase 3 only makes the allowlist it will
  consume.
- ZR1/ZR1X comparison columns (scaffold-only models stay excluded, matching
  the review's scope).

## 6. Validation Plan

- `tests/test_editor_lints.py` — lint and compare functions run against the
  real workbook and must reproduce named, already-verified review findings:
  - `display_order_collision`: z06_options sec_lpoe_001 RWJ/WKS @ '72' (D-1)
  - `display_order_type`: z06_options string-typed rows (S-1),
    z06_exclusive_members rows 2–17 (S-2)
  - `boolean_text`: order_summary_sections `active='TRUE'` (S-10)
  - compare: opt_eyt_001 GS description flagged as deviator (C-1);
    opt_cj2_001 Stingray name deviator vs GS+Z06 majority (C-2);
    S-4 `_002` keys joined via RPO fallback
  - allowlist: opt_zz3_001 includes-difference suppressed with reason (§5)
  - negative: zero `duplicate_key` and zero `orphan_ref` errors on the
    current workbook (schema validator baseline says it's clean)
- `tests/test_editor_server_payload.py` — extended: `/api/lints` and
  `/api/compare` return well-formed payloads; `GET /api/workbook` unchanged.
- Browser checks (named): Review tab renders both panels; D-1 collision
  visible and click-through lands on the z06_options row; intentional toggle
  reveals opt_zz3_001 with its reason; pending-review badge on R-3 (DRZ).
- Read-only proof: workbook mtime unchanged after a full Review-tab session.
- Regression evidence before merge: `validate_workbook_schema.py` (0/0),
  Python editor test files
  (`test_editor_ops_meta.py`, `test_editor_ops_apply.py`,
  `test_editor_server_payload.py`, `test_editor_server_write_api.py`,
  `test_editor_lints.py`), and the node schema suite
  (`workbook-schema-standardization.test.mjs`,
  `workbook-visual-copy-standardization.test.mjs`). Generators not run —
  no generator code or workbook data changes.

## 7. Approval Questions

1. Approve Phase 3 scope as specced (lint panel + compare view, diff view
   dropped as already-shipped)?
2. Allowlist home — (a) committed JSON [recommended], (b) workbook sheet,
   (c) Python constant?
