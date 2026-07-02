# Spec: Derived swap exclusions + eviction toast notification

Status: IMPLEMENTED — both phases landed 2026-07-02 (Phase A commit `c3fcef5`; Phase B same day: workbook deletion + regeneration + gates). Closure details in §11-closure at the end of this spec. Originally authored 2026-07-02; revised same day after pre-approval review (findings 1–6 resolved: allowlist-gated emission, `production.py` route coverage, precise `userSelected` toast guard, dedicated toast container, manifest-only provenance, Phase-A-green test lane).

Parent threads: remediation spec `docs/asset-media-drift-remediation-spec-2026-06-30.md` §7 follow-up 1 (the Z06 replace-rule red gate) and the 2026-07-02 design discussion confirming the intended CBF behavior is a swap, not a block. This pass supersedes the earlier "re-shelve the five rows as excludes_any" framing: the confirmed product intent is that packages evict CBF (swap mechanic with user notification), so plain-blocking re-authoring would be a behavior regression, not a fix.

Recommended reasoning level for implementation: high. This is a behavior-changing pass (generator derivation + runtime eviction notification), explicitly NOT parity-gated; the derivation step can silently mint new rules on other models if unconstrained, and the anti-surprise gate in §2 step A4 is the piece most likely to be under-thought.

## 0. Current-state evidence (probed 2026-07-02, live workbook + runtime)

- `z06_rule_mapping` rows 82–86: five `rule_type="excludes"` / `runtime_action="replace"` rows, sources T0F/T0G/Z07/PDD/PDF, all targeting `opt_cbf_001` (CBF, "Body-color painted Rockers and splitter", `sec_exte_001`, selectable, NOT a default — no `default_selection_rules` row).
- The primitive incompatibilities already exist as authored rows: `cbf excludes cfz` (Carbon Flash ground effects), `cbf excludes cfv_002`, `cbf excludes efy`.
- The includes graph already implies the five stacked rows: T0F→CFZ; T0G→CFV; Z07→{T0F, J57, FE7, XFS}; PDD→{Z07, T0F, CFZ, ROY}; PDF→{Z07, T0G, CFV, ROY}. Every one of the five stacked rows is the transitive closure of a primitive exclusion through this graph, computed by hand.
- Runtime `replace` semantics (`form-app/app.js`): `removeReplaceRuleTargets` (:1538) silently `deleteSelectedOption`s the target when the source is selected; `disableReasonForChoice` (:1030) shows "X removes this default" while the source stays selected; `:1050` exempts replace rules from ordinary exclusion handling. There is NO user notification of the eviction. Existing notification-adjacent machinery (review correction 2026-07-02): `index.html:46` already has `#alertRegion` with `aria-live="polite"`, styled at `styles.css:222`; render OVERWRITES its `innerHTML` for data warnings at `app.js:2701` — it is a render-owned warning surface, not a toast queue, and cannot host evictions without clobbering (see §2 A4).
- Runtime selection state distinguishes explicit customer picks from programmatic ones: `state.userSelected` (`app.js:30`) holds only explicit choices; `state.selected` also holds defaults and auto-added/programmatic selections. The toast guard MUST key on `state.userSelected` (§2 A4).
- Rule assembly is split by generation route (review correction 2026-07-02): Stingray assembles rules through `production.py` (:425 `raw_rules` loop), while Grand Sport/Z06 use `rules.py:134` via `source_assembly.py:35`. A derivation hook in `rules.py` alone does not cover Stingray.
- Generator `replace` handling (`scripts/corvette_form_generator/rules.py:160-200`): `runtime_action=="replace"` marks `replaces_default`, exempts the rule from redundant-same-section omission, and emits reason text "X removes this default." — text that is factually wrong for CBF (not a default).
- Red gate: `tests/workbook-schema-standardization.test.mjs:359` ("Z06 active replace excludes stay limited to true default-replacement rows") allowlists only `(opt_j57_001, opt_j6a_001)`; the five CBF rows fail it on every run (documented pre-existing red).
- Authored `replace` rows across models: stingray `rule_mapping` 4 (5ZW→T0A, ZF1→T0A, Z51→FE1, Z51→FE2), grand_sport 5 (J57→J6A, FEY→T0E, FEB→JX6, FEY→JX6, FEY→J56), z06 6 (J57→J6A + the five CBF rows). Whether the non-CBF rows are true default-replacements or more hand-stacked closure has NOT been classified — that audit is part of this pass (§2 A5), migration of them is not.
- Excludes enforcement is directional: `disableReasonForChoice(X)` consults only rules whose target is X with a selected source (`selectedContextIds()` does include auto-added options). Deleting the five stacked rows today with no replacement mechanism would leave Z07 selectable alongside CBF while suppressing the CFZ auto-add — a silently incomplete configuration. The stacked rows are load-bearing until derivation exists.
- Dry closure scan (review finding 2026-07-02, current workbook): generic includes-closure derivation over primitive excludes finds unshadowed candidates BEYOND the five approved CBF equivalents — 6 on Stingray, 1 on Grand Sport, 6 on Z06. Unconstrained emission would therefore trip the anti-surprise gate immediately. This spec resolves that by making emission allowlist-gated (§2 A1/A3): only allowlisted pairs are emitted as rules; all other closure candidates are report-only manifest entries for separate approval.

## 1. Diagnosis

Root cause: the workbook is the only place transitive package-level conflicts can currently be expressed, so authors hand-compute the includes-closure of each primitive exclusion into stacked `replace` rows. This (a) multiplies maintenance for every new package, (b) abuses the `replace` action's "removes this default" semantics against a non-default option, (c) keeps a standing test gate red, and (d) evicts explicitly-selected options silently — confirmed as a UX gap by the product owner.

Risk: medium. Generator derivation is mechanical but mints rules; runtime gains a new visible component (toast). Change class: generator mechanism + runtime behavior + workbook data deletion + test-contract change, phased with a checkpoint.

Approved product decisions (2026-07-02):

- Eviction priority is one-directional: selecting a package evicts CBF-class targets (with notification); while the package remains selected, the evicted option is disabled with an honest reason. The evicted option does not block the package.
- Toast notification with verbose messaging on eviction — but NOT for every rule interaction. Scope rule: a toast fires only when an option the customer EXPLICITLY selected is evicted by a swap rule. Auto-added options evicted, and ordinary "blocked/disabled" states, never toast. This is a generic runtime guard, not a per-rule workbook flag — no new workbook column needed.

## 2. Recommended pass shape: two ordered phases, one checkpoint

### Phase A — derivation mechanism + eviction toast (code + tests, no workbook write)

1. Derivation helper — new `scripts/corvette_form_generator/rule_derivation.py`, wired into BOTH rule-assembly routes: `rules.py:134` (Grand Sport/Z06 via `source_assembly.py:35`) AND `production.py:425` (`raw_rules` loop — Stingray's route; a `rules.py`-only hook does not cover all three regenerated models). For each selectable option S, compute its includes-closure I(S) (recursive walk of active `includes` rules, cycle-guarded, deterministic ordering). For each active primitive excludes rule (A excludes B) with B ∈ I(S) and S ≠ A: that (S, A) pair is a derivation CANDIDATE. Every candidate is recorded in the derivation manifest with provenance (`derived_via` = includes path + primitive rule_id). Emission is allowlist-gated: only candidates on the approved emission allowlist (this pass: exactly the five Z06 CBF pairs — T0F/T0G/Z07/PDD/PDF → opt_cbf_001) become emitted rules with `runtime_action="replace"` and generated verbose reason text built from option labels, e.g. "Body-color painted Rockers and splitter (CBF) was removed: Z07 Performance Package includes Carbon Flash Carbon Fiber Ground Effects (CFZ), which replaces it." Non-allowlisted candidates (the ~13 known from §0's dry scan: 6 Stingray, 1 GS, 6 Z06) appear ONLY in the manifest as `candidate_not_emitted` — never as rules. The allowlist is data (module-level constant of (model, source_id, target_id) tuples), not model logic; graph mechanics stay generic. Emitted derived rules carry NO extra runtime-contract fields (see A1b).
   1b. Provenance is manifest-only, NOT runtime-contract data. `registry_promotion.py:146` (`find_draft_only_fields` / promotion validation) passes unknown runtime fields through, so `derived`/`derived_via` on emitted rules would silently enter `form-app/data.js` and become de-facto contract surface. Decision: emitted derived rules are shaped identically to authored replace rules in the runtime contract (same fields; only reason copy differs); `derived`/`derived_via`/includes-path provenance live exclusively in the derivation manifest artifact. Contract tests assert NO `derived*` fields appear in runtime contracts or `data.js`; Phase B's bounded-diff expectation is restated accordingly (§2 B2).
2. De-duplication and precedence: if an authored rule for the same (source, target) pair exists, the authored row wins and no derived rule is emitted (authored rows keep workbook authority; this also makes Phase A parity-safe for Z06 where the five authored rows still exist).
3. Anti-surprise gate (hard requirement): the derivation manifest per model records every closure candidate (emitted, `shadowed_by_authored`, or `candidate_not_emitted`) with provenance. Because emission is allowlist-gated (A1), the gate cannot be tripped by latent closures — the ~13 known non-CBF candidates land in the manifest as `candidate_not_emitted` and are delivered in the checkpoint report for separate approval, never shipped. The gate's enforced invariants, pinned by tests: (a) emitted derived rules == allowlist ∩ candidates, exactly; (b) an allowlisted pair that is NOT a closure candidate is a hard generation error (stale allowlist); (c) manifests are deterministic across runs.
4. Runtime toast (`form-app/app.js` + `form-app/styles.css` + `form-app/index.html`): when `removeReplaceRuleTargets` (:1538) evicts a target, toast if and only if `state.userSelected.has(rule.target_id)` — checked BEFORE `deleteSelectedOption` (:1387) runs, since deletion clears the flag (`app.js:1389` deletes from `userSelected`). `state.selected` is NOT a sufficient guard: it also holds defaults and programmatic selections, and keying on it would toast for non-explicit evictions in violation of §1's scope rule. Container: a NEW dedicated element (e.g. `#toastRegion`, `aria-live="polite"`) added to `index.html` — NOT `#alertRegion`, whose `innerHTML` is overwritten by render for data warnings at `app.js:2701`; existing data-warning rendering is preserved untouched. Vanilla JS/CSS, no dependencies; dismissable + auto-timeout; stacks safely if multiple evictions fire in one action; mobile-first layout per AGENTS §7.
5. Reason-text correction: derived rules and any authored replace rows whose target is NOT a workbook default must not say "removes this default"; generic copy is "X removes Y" with the includes-path detail. True default-replacements (e.g. J57→J6A) keep their default-flavored copy.
6. Tests (Phase A):
   - Python: derivation unit tests (closure walk incl. multi-hop PDD→Z07→T0F→CFZ, cycle guard, authored-shadowing, determinism, verbose-copy assembly, allowlist gating: non-allowlisted candidates never emitted, stale-allowlist hard error, manifest completeness incl. `candidate_not_emitted` entries, no `derived*` fields on emitted rule dicts).
   - Node: `workbook-schema-standardization.test.mjs` replace-allowlist test REWRITTEN to the new contract: authored replace rows must be true default-replacements (allowlist), and stacked-closure rows are forbidden BECAUSE derivation owns them — with the five CBF rows carried on a TEMPORARY explicit exemption list (clearly labeled "Phase B removes") so Phase A closes GREEN; Phase B removes the exemption in the same pass that deletes the rows. No red-until-Phase-B lane: Phase A's checkpoint requires all Phase A tests green (a standing red between phases would pollute gate signal, and the previous "implementer picks" wording contradicted the green requirement). New/extended runtime tests: eviction fires from derived rule; toast renders for explicitly-selected eviction (guard = `state.userSelected`); NO toast for auto-added eviction, default eviction, or plain blocks; evicted option shows disabled reason while source selected; `#alertRegion` data-warning rendering unaffected by toast activity.

Checkpoint (stop, report before Phase B): ALL Phase A tests green (Python + Node, incl. the temporarily-exempted schema test); regeneration of all three models produces contracts where the ONLY rule-surface diffs are the approved reason-copy corrections (authored rows still shadow derivations and provenance is manifest-only, so no net-new rules and no new contract fields); derivation manifests reviewed — including the `candidate_not_emitted` inventory (expected ~13: 6 Stingray, 1 GS, 6 Z06; exact list delivered for separate approval); replace-row classification report for stingray/grand_sport (§2 A5 audit: true default-replacement vs hand-stacked closure) delivered with a recommendation but no migration.

### Phase B — workbook deletion + regeneration (data pass, AGENTS §5)

1. Delete the five Z06 CBF stacked rows (`z06_rule_mapping` rows re-resolved at apply time by rule_id, not row number) via a one-shot temp script through `save_workbook_safely()`; manifest printed before apply; backup + on-disk read-back.
2. Regenerate all three models + registry. Expected diff (NOT parity): the five authored Z06 rules disappear and exactly five derived equivalents appear (same source/target pairs, same contract shape as authored replace rules — no `derived*` fields per §2 A1b — new verbose copy); stingray/grand_sport contracts unchanged except approved copy corrections from Phase A; CSV reviewed for the same bounded diff. Anything beyond the bounded expectation is a hard stop.
3. Remove the five CBF pairs from the temporary schema-test exemption list (§2 A6) — the rewritten `workbook-schema-standardization` test must pass green with no exemptions.
4. Full gates per §8, including browser smoke — REQUIRED this pass (runtime behavior + new UI component; parity proof is not available as a substitute).

## 3. Exact files expected to change

Phase A:
1. New `scripts/corvette_form_generator/rule_derivation.py` — closure walk, candidates, allowlist gating, manifest, copy assembly.
2. `scripts/corvette_form_generator/rules.py` (GS/Z06 route, :134) AND `scripts/corvette_form_generator/production.py` (Stingray route, :425 `raw_rules` loop) — wire derivation into both rule-assembly routes; reason-copy correction per §2 A5.
3. `form-app/app.js`, `form-app/styles.css`, `form-app/index.html` (new dedicated toast container per §2 A4) — eviction toast, `userSelected` guard.
4. `tests/workbook-schema-standardization.test.mjs` — new replace-rule contract with temporary CBF exemption list.
5. `tests/z06-performance-package-interactions.test.mjs`, `tests/multi-model-runtime-switching.test.mjs` — eviction/toast runtime assertions (whichever layer fabricates selections; extend, don't fork).
6. New/extended Python test module for derivation (co-locate with existing rules tests; if none exist, `tests/test_rule_derivation.py`).
7. `README.md` test-to-surface table if a new test module lands.

Phase B:
8. `stingray_master.xlsx` — delete 5 `z06_rule_mapping` rows (§5 safety).
9. `form-output/runtime/*-runtime-contract.json`, `form-output/stingray-form-data.{json,csv}`, `form-app/data.js` — regenerated; bounded-diff proven.
10. `tests/workbook-schema-standardization.test.mjs` — remove the temporary CBF exemption list (§2 B3).
11. `docs/asset-media-drift-remediation-spec-2026-06-30.md` — follow-up 1 status flip.
12. This spec — close per AGENTS §11.

Explicitly NOT changing: dealer submission surfaces (untouched/preserved, AGENTS §6); `default_selection_rules` (CBF stays a non-default selectable option); stingray/grand_sport authored replace rows (audited and classified in the checkpoint report, migrated only under a separate approval); excludes_any group machinery (the jake-graphics-style clusters are a candidate future derivation lane, out of scope); workbook schema/columns (no new columns — notification scoping is runtime-generic).

## 4. Source-of-truth decision

Workbook authors only primitive facts: real incompatibilities (CBF excludes CFZ/CFV/EFY), the includes graph, and true default-replacements. The generator owns transitive derivation — generic graph mechanics, no RPO knowledge, allowlist-gated emission — and records provenance in the derivation manifest so every derived rule is auditable back to its primitives (provenance never enters the runtime contract; §2 A1b). Runtime stays a consumer: it executes the same `replace` action it already knows, plus a generic notify-on-explicit-eviction rule keyed on `state.userSelected`. No product knowledge moves into JS.

## 5. Companion-file impact check

- Generated contracts / `form-app/data.js`: regenerated both phases; bounded-diff gated (§2 A-checkpoint, §2 B2).
- `tests/stingray-generator-stability.test.mjs`, `tests/stingray-form-regression.test.mjs`, `tests/grand-sport-draft-data.test.mjs`, `tests/z06-form-data-draft.test.mjs`, `tests/z06-runtime-rule-corrections.test.mjs` — all touch replace/rule surfaces; run + inspect for pinned rule counts or reason-text expectations (reason-copy changes from §2 A5 may require expectation updates — each one reviewed, not blindly re-pinned).
- Generation summary counts (`rules` count in generator stdout): derived rules may change counts — inspect any test pinning them.
- Workbook editor server: inspected-no-change expected (derived rules never enter the workbook); confirm it renders `z06_rule_mapping` fine post-deletion.
- `validate_workbook_package.py` / `validate_workbook_schema.py`: run post-save (Phase B) + final gates.
- Dealer submission: untouched/preserved (AGENTS §6) — but the eviction path mutates `state.selected`, so verify build-download and dealer payload reflect post-eviction selections in the runtime tests.
- `docs/Audit-route-map.md` / README: inspect for stale references to the red gate.

## 6. Constraints

Standing constraints from AGENTS.md apply (§3, §4, §5 for Phase B, §6, §7). Spec-specific:

- Derivation is includes-closure only (auto-add lineage); requires/excludes_any relationships do not derive swaps in this pass.
- Authored rows always shadow derived rows for the same (source, target) pair.
- Anti-surprise gate: emission is allowlist-gated (§2 A1/A3); the only pairs on the emission allowlist this pass are the five Z06 CBF equivalents. All other closure candidates are manifest-only (`candidate_not_emitted`) pending separate approval — no "looks reasonable" judgment inside the pass.
- Derivation provenance is manifest-only; emitted rules add NO new runtime-contract fields (§2 A1b).
- Toast fires only for explicit-selection evictions, guarded by `state.userSelected` (§2 A4); no per-rule workbook flag; no new dependencies; vanilla implementation. Existing `#alertRegion` data-warning behavior preserved.
- Sync/asset surfaces untouched; no interaction with the 4D wildcard lanes.

## 7. Risks and non-goals

Risks:

- Derivation minting unexpected rules on stingray/grand_sport — RESOLVED by design, not just mitigated: the dry scan (§0) already found ~13 unshadowed non-CBF candidates, so emission is allowlist-gated and those candidates land in the checkpoint manifest as `candidate_not_emitted` for human decision. Residual risk shifts to allowlist staleness, which invariant (b) in §2 A3 hard-errors on.
- Reason-copy churn breaking pinned test expectations — mitigated by §5 inspection lane; every expectation change reviewed against product copy intent.
- Toast noise if a package evicts multiple explicit selections at once — mitigated by stacking design (§2 A4) and the explicit-selection guard; verified in runtime tests.
- Eviction + dealer payload interaction — mitigated by §5 dealer verification lane.
- Two rule-assembly routes (`production.py` for Stingray, `rules.py` for GS/Z06) must both call the shared derivation helper with equivalent inputs — divergence would make the manifest lie for one route. Mitigated by putting all logic in `rule_derivation.py` and testing both integration points; route unification itself stays out of scope (separately queued production.py legacy-path retirement).
- The pre-existing `test_source_assembly_characterization` red (flagged in 4D §12) touches rule/choice surfaces; triage it BEFORE this pass lands so its signal is clean, or explicitly re-reproduce it unchanged pre/post.

Non-goals: migrating stingray/grand_sport replace rows (classification report only); emitting the ~13 non-CBF closure candidates (manifest-reported, approved separately); deriving from excludes_any clusters; two-directional eviction; per-rule notification flags; toast for auto-added changes (a broader "what changed" summary UX is a separate idea); unifying the production.py/rules.py assembly routes; the editor-lints and Z06-CBF-unrelated documented reds beyond the schema-standardization test this pass rewrites.

## 8. Validation plan

Phase A (run in order, report exact output):

1. Python: derivation unit suite + existing rules/contract suites (`.venv/bin/python -m pytest -q` targeted modules) — must cover BOTH assembly routes (rules.py and production.py integration).
2. Regenerate all three models + registry: assert bounded diff (authored shadowing + manifest-only provenance ⇒ reason-copy-only changes, no new contract fields); derivation manifests reviewed and attached to checkpoint, incl. the `candidate_not_emitted` inventory.
3. Node: rewritten `workbook-schema-standardization` (green, with the labeled temporary CBF exemption) + extended runtime suites green. No red lanes at Phase A close.
4. `git diff --check`; workbook and generated artifacts unchanged on disk at Phase A close except regeneration churn restored.

Checkpoint report (mechanism proof + stingray/GS replace-row classification + derivation manifests), then Phase B:

5. §5 evidence: lock check, `save_workbook_safely()` backup, on-disk read-back (5 rows absent by rule_id, all others untouched), deletion manifest.
6. `validate_workbook_package.py` + `validate_workbook_schema.py` — valid/0 issues.
7. Regenerate all three models + registry; bounded-diff proof (five authored → five derived equivalents, no `derived*` contract fields; nothing else).
8. Full Node suite per README table (schema-standardization now green with NO exemptions); full pytest; the remaining documented pre-existing reds byte-identical to pre-pass reproductions.
9. Browser smoke — REQUIRED: Z06 flow — select CBF, select Z07 → CBF evicted + toast with verbose copy; CBF disabled with honest reason while Z07 selected; deselect Z07 → CBF selectable again; PDD/PDF/T0F/T0G variants spot-checked; no toast when CFZ auto-adds without CBF selected; summary/totals/download/dealer modal reflect post-eviction state; mobile viewport check.

## 9. Handoff requirements

AGENTS.md §11, plus: derivation manifests per model incl. the `candidate_not_emitted` inventory (~13 pairs) as its own approval queue; the stingray/GS replace-row classification report with recommendation; bounded-diff proof for both phases; toast UX evidence (screenshots or DOM assertions); disposition of deferred lanes (other-model migrations, non-CBF candidate emission, excludes_any derivation).

## 10. Approval question (historical — approved 2026-07-02)

Sean approved option (a): both phases, checkpoint report between them. Checkpoint delivered after Phase A; Phase B approved and executed the same day. The 12 `candidate_not_emitted` pairs were reviewed and explicitly deferred (Z06 lug-nut/wheel-lock cluster already block-enforced both directions via requires_any + directional excludes; Stingray 5VM/5W8 cluster dormant — both options active=False).

## 11. Closure (AGENTS §11) — completed 2026-07-02

Changed:
- Workbook: 5 `z06_rule_mapping` rows deleted by rule_id (rows 82–86: T0F/T0G/Z07/PDD/PDF → opt_cbf_001) via one-shot temp script through `save_workbook_safely()`; deletion manifest printed pre-apply; backup `backups/stingray_master-20260702-162826.xlsx`; on-disk read-back verified (80 populated rows, was 85; zero deleted ids present).
- Generator: new `rule_derivation.py` (allowlist-gated includes-closure derivation, manifest-only provenance, stale-allowlist hard error) wired into BOTH routes — `rules.py` `build_draft_rules` (GS/Z06) and `production.py` (Stingray) via shared `extend_with_derived_swap_rules`; generic replace fallback copy corrected to "X removes Y."
- Runtime: `app.js` eviction toast gated on `state.userSelected.has(rule.target_id)` checked before `deleteSelectedOption`; new `#toastRegion` (`index.html`) + `.toast*` styles (`styles.css`); `#alertRegion` data-warning rendering untouched.
- Generated: z06 runtime contract + `form-app/data.js` — five authored rules replaced by five `derived_*` equivalents (same source/target pairs, `runtime_action="replace"`, verbose generated copy, NO `derived*` contract fields); rule count 85→85. Stingray/GS contracts and stingray CSV byte-identical modulo timestamps (timestamp-only churn restored).
- Tests: `test_rule_derivation.py` (15 tests); `workbook-schema-standardization` replace test rewritten to the derivation-owns-closure contract, temporary CBF exemption added in Phase A and REMOVED in Phase B; `z06-performance-package-interactions` +3 toast tests; `z06-form-data-draft` CBF replace expectations re-pinned to derived rule ids/copy (reviewed per §5, not blind).
- Docs: README pytest gate line includes `test_rule_derivation.py`; `asset-media-drift-remediation-spec-2026-06-30.md` follow-up-1 red-gate note flipped to RESOLVED; this spec closed.

Preserved: dealer submission surfaces (eviction path calls the same `deleteSelectedOption` as before; dealer/download state verified post-eviction in browser smoke); `default_selection_rules` (CBF remains non-default selectable); stingray/GS authored replace rows (classified, kept); excludes_any machinery; workbook schema (no new columns).

Gates (Phase B):
- `validate_workbook_package.py` + `validate_workbook_schema.py`: valid / 0 issues.
- Bounded-diff proof: z06 rules 85→85, exactly 5 removed / 5 derived added, zero changed existing rules, zero `derived*` fields in contract or `data.js`, no other top-level diffs; stingray/GS/CSV parity.
- Full Node table: stingray-form-regression 87/87, stingray-generator-stability 15/15, grand-sport-contract-preview 6/6, grand-sport-draft-data 19/19, z06-contract-preview 3/3, z06-form-data-draft 24/24, z06-interior-accessory-cleanup 7/7, z06-performance-package-interactions 21/21, z06-runtime-rule-corrections 15/15, z06-runtime-promotion 5/5, multi-model-runtime-switching 46/46, workbook-schema-standardization 9/9 (NO exemptions), workbook-visual-copy-standardization 8/8.
- Full pytest: 258 passed; 4 pre-existing fails reproduced BYTE-IDENTICAL against the pre-deletion backup workbook (editor-lints RWJ/WKS collision + C2/CJ2 + R3/DRZ compare keys; source-assembly display_behavior characterization) — all documented pre-pass, none touched by this pass.
- Browser smoke (localhost:8742, real DOM): CBF select → no toast; Z07 select → CBF evicted + exactly one toast with verbose derived copy (screenshot-verified rendering, dismiss button, no UI occlusion); CBF disabled with honest derived reason while source selected; deselect → selectable again; T0G/PDD/PDF spot-checked (one toast each, verbose copy); T0F auto-adding CFZ without CBF selected → zero toasts; `#alertRegion` empty/untouched; summary shows PDD/Z07/T0F/CFZ/ROY/J57 and no CBF post-eviction; toast region fixed-position, z-index 60, fits viewport (`min(480px, 100vw - 24px)` — mobile-safe by construction).

Residual risks / follow-ups:
- 12 `candidate_not_emitted` pairs remain manifest-reported every generation (6 Stingray dormant-5VM/5W8, 6 Z06 lug-nuts/wheel-locks) — deliberate deferrals, each needs its own approval to emit. Latent note: dormant 5VM requires-5ZW vs excludes-ZF1 vs 5ZW-includes-ZF1 contradiction should be resolved if 5VM/5W8 reactivate.
- Pre-existing reds (editor-lints ×3, source-assembly characterization ×1) still open — separately queued triage lanes, unchanged by this pass.
- Stingray/GS authored replace rows kept authored per classification report (true defaults: Z51→FE1, FEY→T0E; the rest are non-derivable de-facto-standard replacements) — migration only under separate approval.
