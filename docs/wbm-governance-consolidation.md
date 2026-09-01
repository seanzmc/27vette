# Workbook Manager governance consolidation — findings

**STATUS: DRAFT, PAUSED 2026-09-01.** Phases 1–4 complete; Phase 5 prose not yet
tightened. Final document must be shorter than the deletion list saves
(**net 12,043 B**, measured in §5). Resume from `fable5loop/STATE.md`.

Evidence base: `workbook-manager/audit-spec.md` @ `25c7234` (1,404 lines,
80,956 B), `wbookMgrAuditRpt.md`, `AGENTS.md`, both READMEs, `USER-GUIDE.md`,
`fable5loop/STATE.md`, `tests/validation_catalog.json`, both prior specs,
`git log`/`gh pr view`/`gh run view` for PRs #58–#70, `/tmp` browser-proof
artifact mtimes, and one measured local run of the Manager serial group.

## 1. Governance inventory

| Path | Claims to own | Actually read for (evidence) | Conflicts |
|---|---|---|---|
| `AGENTS.md` (122 l) | conduct, boundaries, gates, validation, handoff (l.3) | §4/§13 stops cited by spec:6–9; §12 PR rule drives every checkpoint's branch/PR | l.5 scope rule vs l.62 Manager mechanics (added `19cc9fe` 08-30); l.100 "focused gates in workbook-manager/README.md" vs l.90 "catalog is the executable owner" |
| `workbook-manager/wbookMgrAuditRpt.md` (938 l) | WM-001–011, §9 23-item backlog | ledger/§4 source; cited spec:23–24 | none |
| `workbook-manager/audit-spec.md` (1,404 l) | checkpoints, ledger, acceptance, §11–14 process (l.25–26) | every closeout: grew 938→1,404 lines (47,692→80,956 B) across 20 docs-only commits since `aae0494`; zero source lines | §14 "one concise dated record" (l.1298) vs 1A/2A having none and 1C–1E having two (inline + §14); delivery vocabulary (§2 C1) |
| `docs/superpowers/specs/2026-07-22-…` (2,016 l) | "sole detailed progress file… STATE.md may carry only a short pointer" (l.25–34) | not cited by any §14 record | vs AGENTS:82 two-file rule; vs audit-spec:32–38 "historical only" |
| `docs/superpowers/specs/2026-08-21-…` (2,662 l) | product model/IA; says 07-22 spec "remains authoritative for projection safety… rollback" (l.52–56); §19.4 "None… do not start a later checkpoint" | not cited by any §14 record | vs audit-spec:35–36 "not implementation authority"; l.2466 Add Group blocked on unresolved canonical-ID decision — carried nowhere in the audit spec |
| `docs/superpowers/specs/2026-08-15-…` (927 l) | SUPERSEDED (l.3–7) | nothing | none (self-retired) |
| `fable5loop/STATE.md` (138 l, 28.6 KB; cap 40 KB) | operational handoff | read every session; the only place 2A's PR #69 delivery is recorded | duplicates each §14 record's validation prose |
| `workbook-manager/README.md` (370 l) | Manager commands/architecture (AGENTS:62) | l.23–25 name audit-spec as authority; l.336–355 test block run as "complete README Manager checkpoint" in 1D:613, 1E:677, 2A:738, 2B:805 | block ≠ catalog suite: README includes `test_asset_map_sync.py`, omits `test_workbook_manager_form_graph.py`; l.8–30 Pass 5/6A/7 narrative |
| `README.md` (357 l) | overview, commands (AGENTS:3) | §Validation l.223 defers to catalog | l.161–173 lists 13 Manager tests (omits `form_graph`, `generated_parity`) |
| `workbook-manager/USER-GUIDE.md` (323 l) | operator guidance | updated in `a45addd`, `e6f14fb` | none |
| `tests/validation_catalog.json` (76 gates, 7 suites) | gate layer/isolation/serialization/CI selection (AGENTS:90) | `selected_gates(["workbook-manager/audit-spec.md"])` → surface `workbook_manager`, 22 gates | `owning_specification` → `docs/superpowers/specs/2026-08-17-fast-layered-validation-suite.md` **does not exist** (archived); `suite.workbook_manager_serial_group.measured_seconds` 745.31 vs 91.36 s measured today |
| `scripts/plan_ci_validation.py` | CI matrix | `_is_documentation` (l.540–541) routes `*.md` incl. the spec to `docs-only`; runner routes the same path to 22 Manager gates | second path-classifier beside catalog `ci.path_surfaces` |
| `.github/workflows/*.yml`, Codex review | merge requirement | 17 findings on 7 PRs (below) | none |

## 2. Conflict register (ranked by measured decision cost)

**C1 — three meanings of "closed" (largest).** 1B spec:1319–1320 "current-head CI is pending"; 1C spec:1361–1362 "merged to `main` as `d0ad7cc`"; 1E spec:1380–1382 "PR #68 … open for review… CI … passed"; 2B spec:1402–1403 "delivered; … CI … pending"; 1A (l.378–426) and 2A (l.727–745) name no PR at all (they shipped as PR #60 and #69 per `gh pr view`). What the exit gate actually requires: acceptance scenarios (e.g. l.374, 458, 553) + "closed in this specification, and stopped before the next begins" (l.350–352) + "deliver through a task branch and PR; do not merge without separate authority" (l.1264; AGENTS:118). Merge and CI are **not** closure conditions, so all three closures are valid; the *vocabulary* is inconsistent. Cost: PR #66 (`ec18ae2`, `51a46ee`; +22/−13; open 05:08→13:59 UTC) existed solely to rewrite 1C's record from pending to merged, plus `d09ad5f`, `3b20359` "record … ci" commits. Resolution: spec wins on the gate; GitHub wins on delivery state; delete §14 delivery prose (§5 D11); closure names its PR and stops. Enforced by `test_every_closed_checkpoint_names_its_pr_with_consistent_delivery_state`.

**C2 — 1C "still coalesces away" + "none implied" (spec:1323, 1347–1348; inline 557–558).** Not a contradiction: Required work 2 (l.536–537) *asks* for reuse of coalescing so "full reversion removes effective intent"; DRAFT-02 (l.1024) accepts exactly that; `tests/test_workbook_manager_drafts.py:296` has covered it since `94e059e` (08-08). "Still" describes preserved required behavior, not a deferral. Cost: 0 decisions. It is not the largest conflict; it is a false positive that shows the honesty rule cannot be read reliably from prose. Resolution: reword l.557–558/1323 to "full reversion coalesces to no operation (DRAFT-02)"; enforce deferral vocabulary mechanically (`check_residual_risk_is_not_contradicted`).

**C3 — which "complete Manager gate" (AGENTS:100 vs AGENTS:90 vs README:336–355 vs catalog suite).** Records 1D–2B each cite two counts (README block 371/379/416/398 and catalog group 347/355/—/377) because README ⊃ `asset_map_sync` (50 tests) and ⊅ `form_graph` (29). Cost: two ~90 s runs per checkpoint × 4 checkpoints; two numbers to reconcile per record. Resolution: catalog wins; retarget AGENTS:100 (§5 A2); make README:336–355 equal the suite command.

**C4 — AGENTS:5 vs AGENTS:62.** l.5 forbids module mechanics in AGENTS; l.62's second sentence lists Manager mechanics that duplicate README wm:114–118, 251–261 and spec §5.4. Cost: none measured (no record cites it). Resolution: delete the clause (§5 A1).

**C5 — prior-spec authority (07-22:25–34; 08-21:52–56 vs audit-spec:32–38).** Cost: none in §14. Latent. Resolution: audit-spec wins; shorten l.32–38 to one sentence (§5 D2); no edit to archived specs.

**C6 — §14 vs inline closures (spec:1298 vs 1A/2A absent, 1C–1E doubled; 1C l.562–567 is a paragraph explaining the duplication).** Cost: PR #66; 6 lines of meta-prose. Resolution: inline closure is the record; delete §14 bullets (§5 D11).

**C7 — §11.2 item 3 (l.1179–1183) duplicates README wm:328–334, catalog `serial_groups.workbook_manager`, and `plan_ci_validation.py` comments.** Cost: PR #64 (`19cc9fe`, `425ea15`, +116/−40) spent aligning spec prose with the gate method. Resolution: catalog wins (§5 D7–D9).

**C8 — catalog `owning_specification` points at a moved file.** Cost: none. Latent. Resolution: fix pointer in a catalog-only commit (descriptive field; additive scope).

## 3. Obligation cost table

Measured sources: commit timestamps (`git log --date=iso-strict`), `gh run view` job times, `/tmp` proof artifact mtimes, one local run today.

| Obligation | Measured cost per checkpoint | Class | Evidence | Action |
|---|---|---|---|---|
| Catalog-selected layered run | 21–22 gates 117–123 s (1C:1334, 1D:614, 1E:678); 42 gates 223.5 s (2B:807). Serial group alone today: **91.36 s**, 377 passed/2 skipped/77 subtests | load-bearing | only regression net for closed items (STRUCT-04 synthetic, `test_reverting_to_projection…`) | keep; fix stale catalog `measured_seconds` 745.31 |
| "Complete README Manager checkpoint" run | second ~90 s run, 4/7 records | miscalibrated | duplicates the catalog suite ±2 files (C3) | drop; README block := catalog command |
| RED proof | unknown wall-clock (not separately timestamped) | miscalibrated | cited REDs are existence failures: 1A:415 `404`, 1B:505 "absent … selector", 1D:603 `ERR_MODULE_NOT_FOUND`; none of the 17 post-gate Codex findings was caught by a RED | retarget: RED must fail on the *assertion* against existing code (mutation canary), not on a missing module |
| Real browser desktop | 2A: chrome profile 23:58:42→00:22:47 (≈24 min incl. 2 probe scripts, 203 lines); 2B: 09:22:35→09:26:57 (≈4.5 min); 2B review fix 11:51:38→11:59:11 (7.5 min) | load-bearing | only proof of visible behavior; verified the 1B CDP-delay fix | keep for changed interactions |
| 390×844 check | included above; result "390=390"/"no overflow" in 7/7 records | miscalibrated | never failed; the one known overflow (Advanced 1183 px, audit §2) is P3.6, deliberately open | run only for 3C/styling checkpoints |
| Protected-hash comparison | seconds; identical `3127e663…/3794c9cd…/370de000…` 7/7 | load-bearing but already automated | `test_workbook_manager_generated_parity.py:120,174` and `form_graph` (catalog notes) assert the same hashes | delete the manual step from §11.2 item 8; keep gates |
| Nine-state drift table | 3 tables (1A, 1B, 2B) ≈ 4.2 KB; 1C/1D/1E/2A skipped it | ceremonial | every cell "Inspected, no change" or restates the implementation; never changed an outcome | delete rule + tables (§5 D3); registry/projection/editor cells now executable |
| Closeout record | spec +466 lines/+33 KB in 20 docs commits; 2–4 docs commits per checkpoint (1D: `a45addd` 10:25, `44470a6` 10:27, `d09ad5f` 10:30); ≈20k tokens of spec + 7k STATE read per session | mixed | "Residual risk: none implied" 7/7 → ceremonial; "checks not run and why" (2B:1397–1399; STATE 2B fix) → load-bearing; dated-count disclaimers (l.419–421, 516–517) → ceremonial | keep inline closure + not-run list; delete the rest (§5) |
| Companion-file inspection | README/USER-GUIDE edited in 2/7 checkpoints (`a45addd`, `e6f14fb`) | load-bearing for docs; ceremonial for "generated inspected-no-change" | hash gates already prove the latter | record only companions actually updated |
| Branch/PR delivery | CI 2.5–10 min per push; Codex review in ≤5 min; remediation 44 min (#62), 50 min (#69), 2 h 11 m (#70); PR lifetimes 32 min (#65) … 6 h 26 m (#68) | load-bearing | **17 findings on 7 PRs** (P1×5, P2×12) after all local gates were green: #60 4P1+1P2, #62 2P2, #65 1P1+2P2, #67 2P2, #68 1P1, #69 4P2, #70 1P2 | keep |

**Bottleneck finding.** The gates are not the bottleneck: local layered run ≈2 min, CI ≤10 min, browser ≤24 min. Time goes to (a) closeout prose and its rewrites (20 docs commits, PR #64, PR #66), (b) post-review remediation of defects local gates do not detect (17 findings; 6 of them one class — an action bound to an ambient selector/table/selection that changed underneath: #62 stale table, #68 bulk model scope, #69 undo identity and shared-root `model_id`, #60 stale history response, #70 stale selection), and (c) per-session reading of ~123 KB of governance text.

## 4. Mechanical enforcement (done)

`tests/test_workbook_manager_spec_governance.py` (10 tests, 0.37 s, read-only; cataloged as `py.test_workbook_manager_spec_governance`, layer 0, `changed_surfaces` `workbook_manager` + `workbook_domain_registry`; `scripts/catalog_change_scope.py` classifies the edit `"full": false, "gate(s) added"`; `test_catalog_change_scope.py` + `test_validation_catalog.py` 57 passed). Checks: ledger == audit §9 in order (23); every WM finding → ≥1 item and ≥1 defined scenario; §4 items appear literally in checkpoint objectives; `[x]` ⇔ inline `**Closed … — implementation <sha>.**`; `— closed` scenario labels only on closed exit gates, all-or-none; "none implied" never beside deferral vocabulary; every closed checkpoint names a PR with no pending/passed contradiction (documented exceptions `{1A, 2A}` pinned so they must be removed when fixed); registry family-by-surface matrix fully classified.

RED evidence on the real file (three seeds, then reverted, `git diff --quiet` clean): deleting `P3.8` → `Right contains one more item: 'P3.8'` + `('WM-011', {'P3.8'})` + owned-set mismatch (3 tests); ticking `P2.8` → `P2.8 is checked but Checkpoint 2C is open`; appending "not fixed here" to a none-implied record → `'none implied' beside a carried limitation: [('1B', 'not fixed here')]`. 5 failed / 5 passed, then 10 passed after revert. Eleven further seeds are in-file (`test_checks_fail_on_seeded_violations`), including shrinking `MODEL_COLLECTIONS`, dropping a generator role, and widening `HEADER_MATCH_ROLES`.

## 5. Structural finding

Hypothesis is **partly wrong**. Registry authority holds for projection, editor, ChangeSet and writer: `catalog._build_spec` (catalog.py:235–268) indexes `_ROUTING[family]` for every `EDITOR_SHEET_META` family, so an unrouted family raises at import; `WRITABLE_FAMILIES = tuple(EDITOR_SHEET_META)` (l.271); `changeset.py:19,133,278` and `service.py` derive through `family_spec`; `test_workbook_manager_catalog.py:88–89,113–130` and `test_workbook_domain_registry.py:153` already enumerate. Verified today: 25 = 25 families; every writable table is reachable via `MODEL_COLLECTIONS ∪ SHARED_TABLES` (l.332–347) or `structure_specs()` (l.379–391).

The separate representations that *can* drift silently are smaller than claimed: (1) `MODEL_COLLECTIONS`/`SHARED_TABLES` — dropping a table silently reclassifies it as a structure family (no test pins per-family surface; **my matrix does not yet pin this either — resume item**); (2) three hand copies of the 11 source roles — `model_configs.py:51–63`, `runtime_metadata.py:18–30`, `schema_validation.HEADER_MATCH_ROLES:72–82` (the last covers 9/11: `color_overrides_sheet`, `variant_option_overrides_sheet` get no cross-sheet header check; headers verified identical today across 2 and 6 sheets — latent); (3) `schema_validation.REQUIRED_SHEETS:84–96` and `catalog.KNOWN_PRESERVED_SHEETS:25–31`, neither registry-derived.

The 23 items are not 23 surfaces of one cause: only P1.2/P2.9 (WM-002) are family-universe defects. The class that actually cost review cycles (6/17 findings) is ambient scope/identity binding in the UI, which no test owner and no matrix addresses. A per-family-per-surface pinned matrix would subsume STRUCT-04 and the PRES-01/05 completeness half of P2.9 and protect P1.2; cost ≈ +30 lines on the existing `family_surface_matrix` (~1 h, no app code). A generated-consumer column (which contract keys each family feeds) requires per-family generator tracing: cost **unknown**.

## 6. Deletion list (measured: −12,577 B, +534 B, **net −12,043 B**)

`workbook-manager/audit-spec.md`: D1 l.3 sentence "Status: Checkpoint 2A closed 2026-09-01." (−41; stale — 2B is closed); D2 l.35–38 after "historical delivery evidence only." (−268); D3 l.401–413, 491–503, 811–823 drift tables and l.967–979 drift rule (−4,740); D4 l.419–421, 516–517 dated-count disclaimers (−372; catalog owns counts once, l.1128–1132); D5 l.562–567 → "Acceptance evidence: §14 record; PR #65." (−421/+41); D6 l.1136–1141 four-README-checks claim (−425; `test_validation_catalog.py:564–634` owns it); D7 l.1179–1183 → "3. current catalog-selected Manager serial group in one process locally;" (−362/+73); D8 l.1184–1192 → one line naming the runner (−626/+91); D9 l.1198–1204 → one line (−525/+135); D10 l.981–983 (−232; now `family_surface_matrix`); D11 §14 l.1298–1320 → two-line pointer, l.1365–1404 deleted, add " PR #60." / " PR #69." to 1A/2A closures (−4,248/+149).

`AGENTS.md`: A1 l.62 clause from "workflow history is a read-only model" through "precedes any write, and " (−268; owned by README wm:114–118, 251–261, spec §5.4); A2 l.100 "the focused gates in `workbook-manager/README.md`" → "the catalog's `workbook_manager` serial group" (−49/+45).

## 7. Recommended next action

TBD on resume — candidate: one docs-only PR applying §6 exactly (the governance shrink) with the new gate as its guard, before any 2C work; reasoning vs alternatives (matrix-first, 2C-first) to be written.
