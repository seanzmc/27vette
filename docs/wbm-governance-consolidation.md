# Workbook Manager governance consolidation — findings

Findings document, not a specification. 2026-09-01, against `25c7234`.
Evidence: `workbook-manager/audit-spec.md` (1,404 l), `wbookMgrAuditRpt.md`,
`AGENTS.md`, both READMEs, `USER-GUIDE.md`, `fable5loop/STATE.md`,
`tests/validation_catalog.json`, prior specs, `git log`/`gh pr view`/`gh run
view` for PRs #58–#70, `/tmp` proof-artifact mtimes, one local serial-group run.

## 1. Governance inventory

| Path | Claims to own | Read for (evidence) | Conflicts |
|---|---|---|---|
| `AGENTS.md` | conduct, boundaries, gates, handoff (l.3) | §4/§13 stops (spec:6–9); §12 PR rule every checkpoint | l.5 vs l.62 Manager mechanics; l.100 README gates vs l.90 catalog owner |
| `wbookMgrAuditRpt.md` | WM-001–011, §9 backlog | ledger source (spec:23–24) | none |
| `audit-spec.md` | checkpoints, ledger, §11–14 process | every closeout; 938→1,404 l in 20 docs-only commits since `aae0494`, zero source lines | §14 "one record" (l.1298) vs 1A/2A none, 1C–1E two; delivery vocabulary (C1) |
| specs `2026-07-22`, `08-21` | "sole progress file" (07-22:25–34); 08-21:52–56 keeps 07-22 authoritative | cited by no §14 record | vs audit-spec:32–38; 08-21:2466 Add Group blocker carried nowhere |
| spec `2026-08-15` | superseded (l.3–7) | nothing | none |
| `fable5loop/STATE.md` | handoff | every session; sole record of 2A's PR #69 | duplicates §14 validation prose |
| `workbook-manager/README.md` | commands (AGENTS:62) | l.336–355 block run in 1D:613, 1E:677, 2A:738, 2B:805 | block ≠ catalog suite (+`asset_map_sync`, −`form_graph`) |
| `README.md` | overview, commands | l.223 defers to catalog | l.161–173 omit `form_graph`, `generated_parity` |
| `USER-GUIDE.md` | operator guidance | `a45addd`, `e6f14fb` | none |
| `validation_catalog.json` (76 gates) | gate layer/CI selection (AGENTS:90) | spec path → surface `workbook_manager`, 22 gates | `owning_specification` file missing (archived); serial group `measured_seconds` 745.31 vs 91.36 s today |
| `plan_ci_validation.py` l.540–541 | CI matrix | routes `*.md` to `docs-only` while runner routes spec to 22 gates | second classifier beside `ci.path_surfaces` |

## 2. Conflict register (ranked by measured cost)

**C1 — "closed" has three meanings (largest).** 1B spec:1319 "CI is pending"; 1C spec:1361 "merged to `main` as `d0ad7cc`"; 1E spec:1380 "PR #68 open… CI passed"; 2B spec:1402 "CI pending"; 1A (l.378–426) and 2A (l.727–745) name no PR (shipped as #60, #69). Exit gate = acceptance scenarios (l.374, 458, 553) + "closed in this specification, stopped before the next" (l.350–352) + "task branch and PR; do not merge without separate authority" (l.1264; AGENTS:118). Merge and CI are not closure conditions, so all three closures are valid; only vocabulary drifts. Cost: PR #66 (`ec18ae2`, `51a46ee`, +22/−13) existed solely to rewrite 1C from pending to merged; `d09ad5f`, `3b20359` likewise. Resolution: spec owns the gate, GitHub owns delivery state; delete §14 delivery prose (D11). Enforced by `test_every_closed_checkpoint_names_its_pr_with_consistent_delivery_state`.

**C2 — 1C "still coalesces away" + "none implied" (spec:1323, 1347; inline 557).** Not a contradiction: Required work 2 (l.536–537) asks for coalescing so "full reversion removes effective intent"; DRAFT-02 (l.1024) accepts it; `tests/test_workbook_manager_drafts.py:296` covers it since `94e059e` (08-08). Cost: 0. Not the largest — a false positive proving the honesty rule cannot be read reliably from prose. Resolution: reword l.557/1323 to "coalesces to no operation (DRAFT-02)"; deferral vocabulary checked mechanically.

**C3 — which "complete Manager gate" (AGENTS:100 vs :90; README wm:336–355 vs catalog).** 1D–2B each report two counts (371/379/416/398 vs 347/355/—/377). Cost: second ~90 s run × 4, two numbers reconciled per record. Resolution: catalog wins (A2; README block := suite command).

**C4 — AGENTS:5 vs :62.** l.5 bans module mechanics; l.62 lists Manager mechanics duplicating README wm:114–118, 251–261. Cost: none measured. Resolution: A1.

**C5 — prior-spec authority (07-22:25–34; 08-21:52–56 vs audit-spec:32–38).** Latent, cost 0. Resolution: D2; archived specs untouched.

**C6 — §14 vs inline closures (spec:1298; 1C l.562–567 explains its own duplication).** Cost: PR #66, 6 lines meta-prose. Resolution: inline closure is the record (D5, D11).

**C7 — §11.2 item 3 (l.1179–1183) vs README wm:328–334 vs catalog `serial_groups`.** Cost: PR #64 (`19cc9fe`, `425ea15`, +116/−40) aligning prose to the gate method. Resolution: catalog wins (D7–D9).

**C8 — catalog `owning_specification` → moved file.** Cost 0. Fix pointer (descriptive field, additive).

## 3. Obligation cost table

| Obligation | Measured per checkpoint | Class | Evidence | Action |
|---|---|---|---|---|
| Catalog layered run | 21–22 gates 117–123 s (1C:1334, 1D:614, 1E:678); 42 gates 223.5 s (2B:807); serial group today 91.36 s, 377 passed | load-bearing | sole regression net for closed items (STRUCT-04, `test_reverting_to_projection…`) | keep; refresh `measured_seconds` |
| README "complete checkpoint" run | second ~90 s run, 4/7 records | miscalibrated | duplicates suite ±2 files (C3) | drop |
| RED proof | unknown (not timestamped) | miscalibrated | cited REDs are existence failures: 1A:415 `404`, 1B:505 absent selector, 1D:603 `ERR_MODULE_NOT_FOUND`; caught 0/17 Codex findings | RED must fail an assertion against existing code |
| Browser desktop | 2A ≈24 min (profile 23:58→00:22, 2 probe scripts); 2B ≈4.5 min; 2B review fix 7.5 min | load-bearing | only proof of visible behavior; verified 1B CDP-delay fix | keep for changed interactions |
| 390×844 | in above; "390=390" 7/7 | miscalibrated | never failed; known overflow (Advanced 1183 px) is P3.6, open | 3C/styling only |
| Protected-hash comparison | seconds; identical 7/7 | automated already | `generated_parity.py:120,174`, `form_graph` | delete manual step (D6) |
| Nine-state drift table | 3 tables ≈4.2 KB; skipped 4/7 | ceremonial | every cell "no change"/restates impl | delete (D3) |
| Closeout record | +466 l/+33 KB, 20 docs commits; 2–4 per checkpoint (1D 10:25/10:27/10:30) | mixed | "none implied" 7/7 ceremonial; "not run and why" (2B:1397) load-bearing | keep inline closure + not-run list |
| Companion inspection | README/USER-GUIDE edited 2/7 | load-bearing for docs; ceremonial for "generated no change" | hash gates own the latter | record updated companions only |
| Branch/PR | CI 2.5–10 min; Codex ≤5 min; remediation 44 min (#62), 50 (#69), 2 h 11 (#70) | load-bearing | **17 findings on 7 PRs after green local gates** (P1×5, P2×12) | keep |

**Bottleneck.** Gates are not it (local ≈2 min, CI ≤10 min, browser ≤24 min). Time goes to (a) closeout prose and its rewrites (20 docs commits, PRs #64/#66), (b) post-review fixes for a class no gate detects — 6/17 findings are an action bound to an ambient selector/table/selection that changed underneath (#62, #68, #69×2, #60, #70), (c) reading ~123 KB of governance per session.

## 4. Mechanical enforcement (shipped)

`tests/test_workbook_manager_spec_governance.py`, 10 tests, 0.11 s, read-only; catalog gate `py.test_workbook_manager_spec_governance` (layer 0; `catalog_change_scope`: `full: false, gate(s) added`; catalog contract tests 71 passed). Checks: ledger == audit §9 in order; every WM finding → item + scenario; §4 items literal in objectives; `[x]` ⇔ inline closure; `— closed` labels only on closed gates; "none implied" never beside deferral vocabulary; closed checkpoints name a PR without pending/passed contradiction (exceptions `{1A, 2A}` pinned); registry family × surface matrix fully classified and **pinned per family** (26 = 15 Advanced + 10 structure + 1 read-only).

RED on the real file, then reverted (`git diff --quiet`): drop `P3.8` → `Right contains one more item: 'P3.8'` (3 tests); tick `P2.8` → `P2.8 is checked but Checkpoint 2C is open`; append "not fixed here" → `'none implied' beside a carried limitation: [('1B', …)]`. 5 failed / 5 passed → 10 passed. Twelve further seeds in-file (`test_checks_fail_on_seeded_violations`) incl. shrinking `MODEL_COLLECTIONS`, dropping a generator role, moving `pricing` to structure → `family moved between Manager surfaces`.

## 5. Structural finding

Hypothesis **partly wrong**. Registry authority holds for projection, editor, ChangeSet, writer: `catalog._build_spec` (catalog.py:235–268) indexes `_ROUTING` for every `EDITOR_SHEET_META` family, so an unrouted family fails at import; `WRITABLE_FAMILIES = tuple(EDITOR_SHEET_META)` (l.271); `changeset.py:19,133,278` derives via `family_spec`; `test_workbook_manager_catalog.py:88–130`, `test_workbook_domain_registry.py:153` enumerate. Verified 25/25 families reachable via `MODEL_COLLECTIONS ∪ SHARED_TABLES` (l.332–347) or `structure_specs()` (l.379–391).

Real silent-drift surfaces are smaller: (1) `MODEL_COLLECTIONS`/`SHARED_TABLES` reclassify a dropped table as structure — **now pinned**; (2) three hand copies of 11 source roles (`model_configs.py:51–63`, `runtime_metadata.py:18–30`, `schema_validation.HEADER_MATCH_ROLES:72–82` covering 9/11; headers verified identical today) — now cross-checked; (3) `REQUIRED_SHEETS:84–96`, `KNOWN_PRESERVED_SHEETS:25–31` not registry-derived — unpinned.

The 23 items are not one cause: only P1.2/P2.9 (WM-002) are family-universe defects. The class that cost review cycles (6/17) is ambient scope/identity binding in the UI, which no matrix addresses. Matrix cost: **done** (+60 l, ~1 h, no app code); it subsumes STRUCT-04 and the PRES-01/05 completeness half of P2.9. A generated-consumer column needs per-family generator tracing: cost unknown.

## 6. Deletion list (measured −12,611 B, +534 B, **net −12,077 B**; this document is 11,994 B)

`workbook-manager/audit-spec.md`: D1 l.3 "Status: Checkpoint 2A closed 2026-09-01." (−41, stale); D2 l.35–38 after "historical delivery evidence only." (−268); D3 drift tables l.401–413, 491–503, 811–823 and rule l.967–979 (−4,740); D4 l.419–421, 516–517 dated-count disclaimers (−372; l.1128–1132 owns counts); D5 l.562–567 → "Acceptance evidence: PR #65." (−421/+41); D6 l.1136–1141 four-README claim (−425; `test_validation_catalog.py:564–634`); D7 l.1179–1183 → "3. current catalog-selected Manager serial group in one process locally;" (−362/+73); D8 l.1184–1192 → one line naming the runner (−626/+91); D9 l.1198–1204 → one line (−525/+135); D10 l.981–983 (−232; `family_surface_matrix`); D11 §14 l.1298–1320 → two-line pointer, l.1365–1404 deleted, add " PR #60." / " PR #69." to 1A/2A closures (−4,248/+149).

`AGENTS.md`: A1 l.62 from "workflow history is a read-only model" through "precedes any write, and " (−268; README wm:114–118, 251–261); A2 l.100 "the focused gates in `workbook-manager/README.md`" → "the catalog's `workbook_manager` serial group" (−49/+45).

## 7. Recommended next action

One docs-only PR applying §6 verbatim, with `py.test_workbook_manager_spec_governance` as its guard (it must stay green through the edit and will force the 1A/2A PR additions and the `{1A, 2A}` exception removal). Reasons it beats the alternatives: (a) *2C first* — inherits the closeout cost measured in §3 and would add a 21st docs commit; §6 removes that cost before the next checkpoint pays it. (b) *Generated-consumer matrix column first* — cost unknown, addresses a defect class (WM-002) already closed, and misses the class that actually cost review cycles. (c) *Fix the ambient-binding class* — real, but it is application work outside this read-only task and needs a stop under AGENTS §4 (new UI behavior). The §6 PR is reversible, validatable by the new gate plus `test_state_handoff`, and shrinks per-session reading by 12 KB before anyone opens 2C.
