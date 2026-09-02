# Workbook Manager consolidation — follow-up report

Corrects and completes `docs/wbm-governance-consolidation.md` (2026-09-01,
against `25c7234`). Read-only against application code. Task branch
`docs/wbm-consolidation-followup`; Checkpoint 2C not opened. Line numbers are
against `origin/main` `25c7234` unless a file changed in this pass.

## 1. CI classifier — result **(b)**, fixed

**Empirical run, before the fix**, exact deletion-diff paths:

```
$ printf 'workbook-manager/audit-spec.md\nAGENTS.md\n' > /tmp/cf.txt
$ .venv/bin/python scripts/plan_ci_validation.py --changed-file-list /tmp/cf.txt --output /tmp/plan.json
{ "include": [ { "name": "docs-only",
                 "command": "echo \"Documentation-only change; no product validation selected.\"", ... } ],
  "changed_paths": ["workbook-manager/audit-spec.md", "AGENTS.md"], "full": false }
```

Same paths through the catalog's own selector
(`scripts/run_layered_validation.py:50-91`): surfaces `{docs, workbook_manager}`,
23 gates, `py.test_workbook_manager_spec_governance` **selected**. So the two
classifiers disagreed on *selection*, not a label. Root cause:
`plan_ci_validation.py:540-541` `_is_documentation()` excludes every `.md`
from `layered_paths` (l.602-612), the layered shard is therefore never
emitted, and `shards` falls through to `_docs_only_shard()` (l.714-715). The
workflow (`.github/workflows/release-candidate.yml:78`) runs only this planner;
`run_layered_validation.py` runs only when the planner emits
`layered-changed-surfaces`. PR #64's Codex finding said exactly this for
`always_gate_ids`; it was recorded in the spec (§11.2 item 4) but the class was
never closed for gates whose *input* is a document.

**Fix (smallest, no catalog `ci`/`path_surfaces` edit, so no §13 approval):**
`scripts/plan_ci_validation.py` gains `_catalog_read_owner_gate_ids()` and
`_docs_read_owners_shard()` (new l.236-283). For every changed path
`_is_documentation()` accepts (excluding `fable5loop/`, which already owns
`handoff-contracts`), it selects the Layer 0-3 catalog gates that declare that
path in `reads`, skipping any gate an already-planned shard runs, and emits one
`docs-read-owners` shard (new l.761-788). Selection is catalog-derived — a new
doc-reading gate is picked up with no planner edit. `SMOKE_EXEMPT_SHARD_PREFIXES`
gains `docs-read-owners` (diff-derived command, same class as
`layered-changed-surfaces`).

RED → GREEN: `tests/test_run_layered_validation.py::
test_pr_planner_selects_catalog_gates_that_read_a_changed_governance_doc`
(new l.459-494) fails against the stashed planner with
`assert ['docs-only'] == ['docs-read-owners']` and passes after. Scenario list
`_scenario_reachable_shards` gains the two-path diff (l.815) so the smoke
guards see the new shard.

**Acceptance run over the real deletion diff, after the fix:**

```
$ .venv/bin/python scripts/plan_ci_validation.py --changed-file-list /tmp/cf.txt --output /tmp/plan.json
  "name": "docs-read-owners",
  "command": ".venv/bin/python -m pytest tests/test_workbook_manager_spec_governance.py -q",
  "description": "Run the catalog gates that read the changed documentation: py.test_workbook_manager_spec_governance"
$ .venv/bin/python scripts/finalize_ci_validation_plan.py --plan /tmp/plan.json   → {"full": false}
$ .venv/bin/python scripts/split_ci_validation_plan.py --plan /tmp/plan.json      → []
$ bash -c "<that command>"                                                          → 12 passed in 0.11s
```

Also verified: `README.md` alone now plans `docs-read-owners` running
`cmd.state_handoff_validator` + `py.test_validation_catalog` (both declare
`README.md` in `reads`); `docs/x.md` still plans `docs-only`;
`fable5loop/STATE.md` still plans exactly `handoff-contracts`; the wide
16-path diff in `test_pr_planner_keeps_manager_partitions…` is unchanged
because `ci-contracts` already runs `test_validation_catalog.py`. Contract owners:
`test_run_layered_validation` + `test_validation_catalog` +
`test_codex_finding_disposition` 80 passed; `scripts/test_finalize…` 4 OK,
`scripts/test_split…` 5 OK.

Consequence for ordering: this PR *is* the classifier fix, and because it
touches `scripts/plan_ci_validation.py` the workflow's regex (`release-candidate.yml:59`)
forces `--full` — the whole inventory runs once on this PR, which is the
correct cost for a planner change. The §6 deletion PR that follows will plan as
`catalog-read-owners` and actually run the gate.

### 1b. Review corrections (2026-09-02, PR #72 Codex P2 ×2)

**Finding 1 — Manager code bypassed the read-owner guard.** The lookup fed only
`_is_documentation()` paths, so a `catalog.py`-only diff planned
`ci-contracts` + `manager-projection` and never ran the governance gate that
imports `catalog.py` and pins its family-to-surface mapping. Fix: the lookup
now also feeds `manager_source_paths`, and the shard is renamed
`docs-read-owners` → `catalog-read-owners` (it no longer covers only docs).
Exact `reads` matches only — the wide globs (`workbook-manager/**`) the rest of
the suite declares are deliberately not expanded, because that would rebuild
the every-source-edit explosion the narrow Manager shards exist to avoid.

**Finding 2 — the gate's own generator inputs never selected it.** Its
assertions import `model_configs` / `runtime_metadata` / `schema_validation`,
but it declared only `workbook_manager` + `workbook_domain_registry` surfaces;
those three files classify to `generator` via the `scripts/` prefix. Fix:
`generator` added to the gate's `changed_surfaces` (catalog edit; committed
separately as `a9832ff`).

The generalization surfaced two more real catalog-declared dependencies the
planner had been silently skipping: `explorer.py` →
`py.test_group_display_label_contract`, `drafts.py` →
`py.test_workbook_manager_review_presentation`, and (in the wide diff)
`frontend/src/api.js` → `py.test_workbook_manager_control_metadata`. The three
pinned planner plans were updated to include `catalog-read-owners` with those
commands; `main.py`, frontend components, and `styles.css` match nothing
exactly and are unaffected.

RED → GREEN: `test_pr_planner_selects_catalog_gates_that_read_changed_manager_code`
failed against the pre-fix planner with
`['ci-contracts', 'manager-projection']`; the generator-input test failed with
the gate absent from the selected set. Both pass after. Contract owners:
`test_run_layered_validation` + `test_validation_catalog` +
`test_codex_finding_disposition` + `test_catalog_change_scope` +
`test_workbook_manager_spec_governance` 115 passed; `scripts/test_finalize…`
4 OK, `scripts/test_split…` 5 OK; `catalog_change_scope` vs `main` reports the
gate as additive.

## 2. RED rule

**Rule (now spec §11.2 item 1, l.1178-1189; §6 preamble l.350-353; §14 bullet
l.1314):** a RED counts only when the failing assertion runs against code that
already exists — the test reaches the asserted route/function/element and the
failure is a wrong value, wrong state, wrong response body, or a call
accepted/rejected against expectation. `404`, `ERR_MODULE_NOT_FOUND`, missing
import, absent selector, undefined symbol are existence failures and are not
RED evidence. A checkpoint adding a new surface must RED an *existing* surface
the new behavior changes. The closure quotes the assertion message.

**Mechanically checkable?** Half. What *is* checkable: that a closure does not
*cite* an existence failure as its RED. Shipped as
`check_red_evidence_is_not_an_existence_failure`
(`tests/test_workbook_manager_spec_governance.py:295-323`), regex over each
closed checkpoint's body and §14 record; the three pre-rule records (1A `404`
l.415, 1B "absent registry selector" l.505, 1D `ERR_MODULE_NOT_FOUND` l.603)
are pinned in `RED_EXISTENCE_FAILURE_RECORDS` so the set can only shrink by
re-pinning. Seeded RED on the real file: appending "RED tests first failed with
`404` on the absent lookup endpoint." to the 2B closure →
`now ['1A','1B','1D','2B'], pinned ['1A','1B','1D']`; reverted, `git diff`
shows only the intended spec edits; 12 passed. Two further in-file seeds
(2B gains a 404; 1A's 404 is rewritten away). What is **not** checkable and
stays review: that the RED ran at all, that it ran against the unmodified
tree, and that the quoted assertion was the decisive one. I am not faking
those.

**Retroactive test against the 17 findings.** "Plausibly caught" means: a RED
written to the rule, for the surface the checkpoint changed, exercising the
existing route/state with the assertion the rule demands, would have failed on
the shipped code. Findings are keyed `PR:path:line` from the review comments.

| # | Finding | New-rule RED plausibly catches? | Why |
|---|---|---|---|
| 1 | #58 spec:6 blanket approval rule | no | prose |
| 2 | #58 spec:198 P3.5 POLISH mapping | no (governance gate catches now) | prose; `check_every_finding_traces…` is the owner |
| 3 | #58 spec:351 rollback-failure vs HIST-02 | no | prose |
| 4 | #59 STATE:24 wrong handoff SHA | no | prose |
| 5 | #60 App.jsx:358 `refreshDraft` 50-row gate | **yes** | existing `api.drafts()` path; RED = open a record at offset >50 and assert lifecycle loads — fails with `null` on the *existing* list-gated code, not a 404 |
| 6 | #60 drafts.py:52 status allowlist omits `apply_retryable` | **yes** | rule's worked example: RED = assert the existing history list *contains* a retryable draft; fails on the allowlist |
| 7 | #60 drafts.py:609 "Cancelled before workbook write" after restore | **yes** | existing summary function; RED = cancel from `apply_restored_retryable`, assert summary mentions the write |
| 8 | #60 drafts.py:770 manual resolution derived from failed attempt | **yes** | existing outcome derivation; RED = assert `next_action != resolve_manually` after resolution |
| 9 | #60 HistoryView.jsx:35 stale response overwrites | plausible, weak | interleaving needs a deterministic harness; the existing `requestRef` pattern in AssetManager shows it is testable, but "plausibly written" is a stretch — count ½ |
| 10 | #62 ModelOperations.jsx:50 stale schema/rows actionable during transition | **yes** (state, not race) | RED = switch `table`, assert Add is disabled until `loadedIdentity` matches; fails on shipped code where `dataReady` did not exist — but the button *did* exist, so the assertion is against existing UI state, not an absent selector |
| 11 | #62 main.py:833 `models` advertises create | **yes** | existing `structure_specs()` response; RED = assert `capabilities.create.allowed is False` for `model_master` |
| 12 | #63 validate_state_handoff.py:146 catalog missing from `reads` | no | catalog metadata; `test_validation_catalog` isolation contract is the owner class |
| 13 | #64 spec:1008 always-gates claim | no | prose — and it is §1 of this report |
| 14 | #65 drafts.py:2067 evidence wrapper nesting | **yes** | existing `list_asset_resolutions()` shape; RED = copy a correction, assert `evidence_json` has no extra level |
| 15 | #65 drafts.py:1933 FK failure on last-op discard | **yes** | existing `discard_operation`; RED = draft with one op + one ignore, discard, assert 200 |
| 16 | #65 drafts.py:904 `OR … fetchone()` hides one link | **yes** | existing query; RED = chain two corrections, assert both links |
| 17 | #66 STATE:44 undelivered docs commit | no | prose |
| 18 | #67 reviewPresentation.js:110 rollback errors doubled | **yes** | existing adapter; RED = assert `len(errors) == len(set(errors))` |
| 19 | #67 reviewPresentation.js:91 stale "manual recovery" next action | **yes** | existing adapter; same shape as #8 |
| 20 | #68 AssetManager.jsx:170 bulk safe action unscoped | **yes** | existing `save_all_safe()`; RED = two-model snapshot, scoped call, assert one model's items staged (this is the test the fix added) |
| 21 | #69 graph_operations.py:65 shared root loses model context | **yes** | existing `dependency_plan()`; RED = `interiors` root, assert dependents > 0 |
| 22 | #69 graph_operations.py:139 conditional refs not traversed | **yes** | existing traversal; RED = delete an option with an `assets.target_id` dependent, assert classified |
| 23 | #69 drafts.py:2841 add-plan retry not idempotent | **yes** | existing `save_operation`; RED = replay plan, assert no `duplicate_record` |
| 24 | #69 ModelOperations.jsx:191 undo matches wrong model | **yes** | existing `priorOperation` find; RED = two models, same key, assert restored op has the current `model_id` |
| 25 | #70 AssetManager.jsx:808 lookup action enabled on hidden ID | **yes** | existing button; RED = select target, page, assert button disabled |

The prior document said "17 Codex findings on 7 PRs". Counting the API today
gives **25 inline/review findings across 13 PRs (#58–#70)**; the 17 are the
ones on the 7 implementation PRs (#60, #62, #65, #67, #68, #69, #70 = 5+2+3+2+1+4+1 = 18,
of which #60's App.jsx:358 was re-raised verbatim on #61 — so 17 distinct on
code). The 8 others are prose/metadata findings on docs PRs. Correcting my own
count: the table above has 25 rows; 17 are code findings.

**Count:** of the 17 code findings, **16 yes + 1 half** (#9, the race). Of all
25, 8 are prose/metadata and out of scope for any test rule. The rule is not
wrong: the class it excludes (existence failures) is precisely the class none
of the 17 fell into, and the class it requires (assert on existing state) is
the class 16 of 17 fell into. What it does not do is *pick* the assertion —
every "yes" above is "a RED for this behavior would have caught it," and the
implementer still has to think of the behavior. The 6 ambient-binding findings
(§3) are the ones where that thinking is hardest, because the wrong state is
only reachable through an ordering the happy path never takes.

## 3. Ambient-binding class

### 3.1 The six, side by side

| Finding | Ambient state | Action bound to it | Invalidating event | Surface |
|---|---|---|---|---|
| #62 ModelOperations:50 | `schema`, `rows` from the previous table | Add / Edit / Delete built from `schema.key` + `table` | `table`/`modelKey` changed; new load in flight | Advanced browser, Form Overview structure index |
| #68 AssetManager:170 | header `modelKey` (visible scope) | "Add all safe matches" sends `fingerprints` only | payload never carried the scope; snapshot has other models' safe items | Images |
| #69 graph_operations:65 | UI's empty `model_id` for shared roots | `dependency_plan` scans with `WHERE model_id=''` | root is shared (`interiors`) so the scope predicate is vacuous | Advanced delete plan |
| #69 ModelOperations:191 | draft's operation list | Undo restores `priorOperation` matched by `table` + key | another model's op with the same key precedes it | Advanced undo |
| #60 HistoryView:35 | `rows`/`total`/`statuses` | render of the filter controls | slower response for previous filter resolves last | History |
| #70 AssetManager:808 | `targetItemId` / `inventoryUrl` | "Assign" / "Use this image" enabled on nonempty ID | page, re-search, stale fingerprint replaced the visible list | Images inspector |

### 3.2 Mechanism — one, with two presentations

All six are the same defect: **a mutating action reads its scope or identity
from component state that was populated for a different context than the one
the operator sees, and nothing re-derives or fail-closes that state at the
moment of the action.** The two presentations:

- **Temporal** (#62, #60, #70): the state was correct once; an async load,
  page, or filter change made it stale and the action did not re-check.
- **Structural** (#68, #69×2): the state was never sufficient — the action's
  payload omitted the model dimension (`fingerprints` only; empty `model_id`;
  `table`+key without `model_id`), so the ambient header model was the only
  thing scoping it, and only by coincidence.

Name: **action-scope binding drift**. Spec §5.3 l.266-267 already names the
structural half ("never from an ambient global selector"). Spec §5.3 l.276 and
§5.7 l.341-346 name the temporal half only for *responses* ("cancels or ignores
stale in-flight responses"), not for *actions* — there is no rule that an
action must re-derive its scope at click time. That is the gap the six fell
through.

### 3.3 Unfixed instances of the same shape in current code

Read-only enumeration, each opened and traced. "Guard" = what currently
prevents the drift; "none" means the action reads ambient state with no
identity check at action time.

| # | File:line | Ambient state | Action | Guard today | §5.3/§5.7 covers in prose? |
|---|---|---|---|---|---|
| U1 | `ModelOperations.jsx:110-114` `saveDraft` → `RecordForm.jsx:283-291` | `schema.model_context.value` and `modelKey` captured when the editor opened (`openEditor` l.129-158) | Save of add/update | `RecordForm` is keyed on `${table}-${mode}-${id}` (l.513) so a *table* change remounts it; a **`modelKey` change does not** — `useEffect [table, modelKey]` l.74-90 sets `setEditing(null)`, which unmounts the form. Effective guard exists, by side effect of the reset, not by an identity check. | §5.3 yes (ownership-derived scope); code complies indirectly |
| U2 | `ModelOperations.jsx:225-245` `saveDependencyPlan` | `deps.root.model_id` frozen at `inspectDelete` l.207-223 | Saves plan operations | `setDeps(null)` on table/model change (l.85). **No check that `draftId` is unchanged** between inspect and save; the plan was computed against `draftId` at l.214 and saved to whatever `draftId` prop is current at l.235 | §5.3 partial; draft identity not addressed |
| U3 | `ModelOperations.jsx:247-270` `saveGuidedOption` | `guidedOption.variants` from `api.guidedOptionContext(modelKey)` at l.146 | Saves option + OVS plan | `setGuidedOption(null)` on table/model change (l.86). Same `draftId` gap as U2 (l.257) | same |
| U4 | `ModelOperations.jsx:272-296` `undoRawDelete` | `undoDelete.priorOperation` captured at l.187-191 | Discard + re-save | **Not cleared on table/model change** (l.84-88 clears editing/deps/guided/rawConfirm but not `undoDelete`); button renders whenever `undoDelete?.id` l.588. After switching table, "Undo delete" still targets the previous table's operation. `api.discardDraftOperation(draftId, undoDelete.id)` at l.276 will 404 if the draft changed (`drafts.py:1966-1974` `draft_operation_not_found`) — fails closed *by accident of the backend*, not by UI design. #69's fix added `model_id` to the match (l.189) but not the lifetime of the state | §5.7 no (not navigation state); §5.3 no |
| U5 | `AssetManager.jsx:260-265` `boundPayload` | `data.fingerprints` | every resolution incl. bulk (l.340-344) and inspector (l.442-445) | Server-side `_check_fingerprints` (`asset_resolutions.py:390`) rejects stale — **fail-closed on the server**. But `data` here is the raw state, not `scopedData` (l.191); after a model switch and before the new load resolves, `data.fingerprints` belongs to the old scope. The button at l.339 is not disabled on `dataScope !== modelKey`, only on `!data.status_counts.safe_proposal` — the *old* counts. Server refuses; UI shows the error. Fail-closed, but the enabled button is a #70-shape lie | §5.3 l.273-276 yes; code diverges on the UI half |
| U6 | `AssetManager.jsx:233, 419-432` `selectedInScope` | `selected` from previous scope | inspector actions | **Guarded** (1E fix): out-of-scope selection renders the switch-scope notice instead of the inspector | covered, complies |
| U7 | `GroupEditor.jsx:239-277` `requestGroupRemoval` | `detail.model_key`, `desired` | dependency check then delete | `api.dependencies(detail.editor.group_table, detail.model_key, …)` — scope comes from the entity, not the header ✓. But `desired` (local member edits) is consulted for the dependency count at l.253 while the *server* check ran against projected rows; the "plan.length" guard at l.244 only prevents removal with unsaved edits, it does not re-fetch after `onChanged`. Low risk (single-user); shape matches | §5.3 yes (entity-derived) |
| U8 | `GroupEditor.jsx:153-168, 200-207` `loadReferences` / `addSelected` | `referenceOptions` | Add member by `selectedMember` value | `referenceOptions` is replaced wholesale on each search; `selectedMember` is **not** cleared when a new search result omits it (`<select>` value falls back visually but state keeps the ID). `addSelected` l.201 does `referenceOptions.find(...)` — if absent, `option?.label` is undefined and the member is added with no label. Same shape as #70 (hidden ID survives a re-search), lower stakes (label only; the ID is still a valid reference) | §5.7 no; #70 fix pattern (l.518, 532 in AssetManager) not applied here |
| U9 | `ConnectedExplorer.jsx:280-317` detail load | `selected` | edit buttons in `OptionDetail`/`GroupDetail` | **Guarded** (1B fix): `setSelected(current => current?.model_key === modelKey ? current : null)` l.290 and generation token l.307. Editors receive `modelKey={detail.model_key}` (l.121, 202) — entity-derived ✓ | covered, complies |
| U10 | `SectionsLayout.jsx:114-143` `startEdit` → `RecordForm` l.326-339 | `modelKey` captured into `initial.model_key` for add (l.122) and passed as prop (l.331) | Save section change | `useEffect [modelKey, draftId, draftRevision]` l.83-87 does `setEditing(null)` → form unmounts on model switch ✓. `api.schema(table, modelKey)` l.130 and the eventual save use the same `modelKey` only because the reset unmounts first | §5.3 indirectly |
| U11 | `FormStructure.jsx:107-112, 114-126` `startEdit` | same as U10 | Save step/section change | Same reset-by-effect pattern (l.110). ✓ by side effect | same |
| U12 | `ChangesSync.jsx:268-285` `createCorrection` | `selectedOperationIds` | `api.createCorrectionDraft` | `useEffect [draftId, draftState]` l.196-202 resets the selection when the draft changes ✓; server rejects IDs not in the draft (`drafts.py:2098-2102`) ✓. Fail-closed both sides | n/a (draft-scoped) |
| U13 | `ChangesSync.jsx:530-562` approve / apply / cancel | `draftId` prop, `acceptedWarnings` | lifecycle mutations | `acceptedWarnings` filtered on `preview.previewFingerprint` change (l.212-216) ✓; server binds approval to the preview fingerprint ✓ | covered |
| U14 | `App.jsx:246-257` header model `<select>` | `modelKey` | every workspace | `refreshStatus` l.65-71 coerces an invalid `modelKey` to `models[0]` **except** when `tab === "assets"` and `modelKey === "*"`. Switching *off* the Images tab with `*` selected leaves `modelKey === "*"` for one render until the next `refreshStatus`; `ModelOperations`/`ConnectedExplorer` would request `model=*`. Not observed to produce a write; flagged as a scope-carry seam | §5.3 l.273-275 names this exact "All models" constraint |

**Live divergences from the prose (not merely "guarded by accident"):** U4
(undo lifetime), U5 (bulk button enabled on old-scope counts), U8 (hidden
member ID survives re-search), U14 (`*` leaks off Images). U2/U3 carry a
`draftId` seam nothing in §5 names. U1/U10/U11 comply only because an unrelated
`useEffect` reset happens to unmount the form — remove that reset and the shape
reappears; there is no check at save time.

Why the code diverges where prose covers it (U4, U5, U8, U14): the prose in
§5.3 is stated about *scope derivation* and *responses*; every fix landed as a
point patch on the surface the reviewer named (token here, `dataReady` there,
`model_id` in one `find`) rather than as a component-level rule "an action
button is enabled only when the state it will read carries the identity the
operator sees." The Codex reviewer found six instances by reading each PR's
diff; the shape is present in files those PRs did not touch.

### 3.4 Detectability

- **Test owner:** yes for the structural presentation — a source test in the
  style of `test_workbook_manager_form_graph.py:887-892` (asserts `loadToken`,
  `dataReady`, `disabled={!dataReady` are present) can pin each fix, and already
  does for three files. It cannot find *new* instances.
- **Lint:** partially. A custom rule "an `onClick` handler that calls `api.*`
  with a `model`/`model_id`/`draftId` argument must derive it from the same
  object the handler reads its key from" is expressible over the JSX AST but
  would false-positive on every entity-derived call (U7, U9). Not worth it
  at 14 candidate sites.
- **Browser scenario:** yes for the temporal presentation, and it is the only
  proof that the button is actually disabled. The 1B CDP-delay technique
  (`STATE.md` 2026-08-29 entry) is the harness; each instance is one
  scenario: switch scope, delay the load, assert the action is disabled and
  the payload (if fired) carries the visible scope.
- **Only by review:** the structural half in *new* code. Whether a payload
  should carry a model dimension is a design fact about the endpoint; no
  static rule knows that `save_all_safe` needed `model` until someone says so.

Honest answer: the six known ones were found by review; U4/U5/U8/U14 above
were also found by review (this one). The class is bounded by a per-action
checklist, not by a gate.

### 3.5 Next authorized action

Under AGENTS §4 this is a **stop**: closing U4/U5/U8/U14 is new UI behavior
(disabling actions, clearing state) in a customer-adjacent operator tool, and
choosing the rule ("actions re-derive scope at click time" vs "state is cleared
on every identity change") is an architectural choice with a real tradeoff
(the former is robust, the latter is what every existing fix did). Recommended:
add the rule as one sentence to §5.3 and open it as a small checkpoint after
the §6 deletion PR, scoped to the four live divergences plus a source-pin test
for each — *not* a sweep of the eleven compliant sites.

## 4. Loose ends

### 4.1 `REQUIRED_SHEETS` / `KNOWN_PRESERVED_SHEETS` — pinned now

Cost of pinning now: 25 lines in the governance test
(`test_workbook_manager_spec_governance.py:459-504` + three seeds), 0.01 s, no
application change. Done: `PINNED_PRESERVED_SHEETS` (4) and
`PINNED_REQUIRED_SHEETS` (11) plus a dual-ownership assertion that no preserved
sheet is addressed by a Manager `TableSpec.sheet` (verified false today over
`catalog.TABLE_SPECS`). Seeds: drop `PriceRef` from preserved → fails; rename
`LZ_Interiors` → fails; give a spec `sheet=("PriceRef",)` → fails.

Risk of entering 2D unpinned: 2D's first act is to move four sheets out of
`KNOWN_PRESERVED_SHEETS` (`catalog.py:25-31`) into the registry. Without a pin,
`classify_workbook_sheets` (`catalog.py:437-441`) silently flips any sheet
that is dropped-but-not-registered from `workbook_preserved_known` to
`workbook_preserved_unknown`, the importer warns `unmanaged_sheet`
(`importer.py:185-189`) and continues, and `PriceRef` — which is *also* in
`REQUIRED_SHEETS` (`schema_validation.py:95`) and consumed by pricing
(`docs/wbm-governance-consolidation.md` §5 item 3) — could become a preserved
sheet the Manager both requires and does not project. The pin turns that into a
red test at the first 2D commit. **Recommendation: pinned (done).** The pin
will fail exactly once, deliberately, when 2D lands, which is the point.

### 4.2 Findings document — fold and delete

`docs/wbm-governance-consolidation.md` is 12,021 B against a §6 deletion of
12,077 B: net −56 B if both survive. Its durable content is already elsewhere
or becomes so with the §6 PR: the conflict resolutions become spec edits; the
cost table's one load-bearing conclusion (RED rule) is now spec §11.2; the
matrix and pins are tests; the deletion list is the PR diff; §7 is superseded
by this report's §1. What would be lost: the inventory table (§1) and the
measured numbers (§3). Those belong in the §6 PR description, where `gh pr
view` keeps them retrievable, and in one `STATE.md` `Verified facts` entry.

**Recommendation: fold into the §6 PR description and delete both findings
documents in that PR.** This report survives only until the §6 PR merges; its
§3.3 enumeration should be copied into the §5.3 checkpoint's spec text when
that checkpoint is authorized, and the rest deleted with it. Keeping analysis
prose in `docs/` is how the spec grew 938→1,404 lines.

## Validation run

- `tests/test_workbook_manager_spec_governance.py` 12 passed (was 10); real-file
  RED for the existence-failure check shown above and reverted.
- `tests/test_run_layered_validation.py` + `test_validation_catalog.py` +
  `test_codex_finding_disposition.py` 80 passed; new planner test RED against
  the stashed planner (1 failed) then GREEN.
- `scripts/test_finalize_ci_validation_plan.py` 4 OK; `scripts/test_split_ci_validation_plan.py` 5 OK.
- `tests/test_state_handoff.py` + `test_catalog_change_scope.py` + `test_validation_catalog.py` 61 passed.
- `scripts/catalog_change_scope.py` base `0da6f9a` → head: `descriptive catalog
  fields only` (collected_tests 10→12, disposition_reason). Against
  `origin/main`: `gate(s) added` (unchanged from PR #71).
- `scripts/validate_state_handoff.py` passed.
- Not run: Manager serial group (no Manager source, fixture, or catalog `ci`
  change; the only Manager-surface file touched is the read-only governance
  test, which the catalog says selects nothing else). Browser: no UI change.

## Not changed

Application code (`workbook-manager/backend`, `frontend`), workbook, generated
artifacts, `form-app/`, dealer submission, `tests/validation_catalog.json`
`ci`/`path_surfaces`/`serial_groups`, `AGENTS.md`, `README.md`. The §6
deletion list is not applied here.
