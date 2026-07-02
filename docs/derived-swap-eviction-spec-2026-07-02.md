# Spec: Derived swap exclusions + eviction toast notification

Status: DRAFT — awaiting approval (Section 10). Authored 2026-07-02.

Parent threads: remediation spec `docs/asset-media-drift-remediation-spec-2026-06-30.md` §7 follow-up 1 (the Z06 replace-rule red gate) and the 2026-07-02 design discussion confirming the intended CBF behavior is a swap, not a block. This pass supersedes the earlier "re-shelve the five rows as excludes_any" framing: the confirmed product intent is that packages evict CBF (swap mechanic with user notification), so plain-blocking re-authoring would be a behavior regression, not a fix.

Recommended reasoning level for implementation: high. This is a behavior-changing pass (generator derivation + runtime eviction notification), explicitly NOT parity-gated; the derivation step can silently mint new rules on other models if unconstrained, and the anti-surprise gate in §2 step A4 is the piece most likely to be under-thought.

## 0. Current-state evidence (probed 2026-07-02, live workbook + runtime)

- `z06_rule_mapping` rows 82–86: five `rule_type="excludes"` / `runtime_action="replace"` rows, sources T0F/T0G/Z07/PDD/PDF, all targeting `opt_cbf_001` (CBF, "Body-color painted Rockers and splitter", `sec_exte_001`, selectable, NOT a default — no `default_selection_rules` row).
- The primitive incompatibilities already exist as authored rows: `cbf excludes cfz` (Carbon Flash ground effects), `cbf excludes cfv_002`, `cbf excludes efy`.
- The includes graph already implies the five stacked rows: T0F→CFZ; T0G→CFV; Z07→{T0F, J57, FE7, XFS}; PDD→{Z07, T0F, CFZ, ROY}; PDF→{Z07, T0G, CFV, ROY}. Every one of the five stacked rows is the transitive closure of a primitive exclusion through this graph, computed by hand.
- Runtime `replace` semantics (`form-app/app.js`): `removeReplaceRuleTargets` (:1538) silently `deleteSelectedOption`s the target when the source is selected; `disableReasonForChoice` (:1030) shows "X removes this default" while the source stays selected; `:1050` exempts replace rules from ordinary exclusion handling. There is NO user notification of the eviction (no toast/notification machinery exists in app.js or styles.css).
- Generator `replace` handling (`scripts/corvette_form_generator/rules.py:160-200`): `runtime_action=="replace"` marks `replaces_default`, exempts the rule from redundant-same-section omission, and emits reason text "X removes this default." — text that is factually wrong for CBF (not a default).
- Red gate: `tests/workbook-schema-standardization.test.mjs:359` ("Z06 active replace excludes stay limited to true default-replacement rows") allowlists only `(opt_j57_001, opt_j6a_001)`; the five CBF rows fail it on every run (documented pre-existing red).
- Authored `replace` rows across models: stingray `rule_mapping` 4 (5ZW→T0A, ZF1→T0A, Z51→FE1, Z51→FE2), grand_sport 5 (J57→J6A, FEY→T0E, FEB→JX6, FEY→JX6, FEY→J56), z06 6 (J57→J6A + the five CBF rows). Whether the non-CBF rows are true default-replacements or more hand-stacked closure has NOT been classified — that audit is part of this pass (§2 A5), migration of them is not.
- Excludes enforcement is directional: `disableReasonForChoice(X)` consults only rules whose target is X with a selected source (`selectedContextIds()` does include auto-added options). Deleting the five stacked rows today with no replacement mechanism would leave Z07 selectable alongside CBF while suppressing the CFZ auto-add — a silently incomplete configuration. The stacked rows are load-bearing until derivation exists.

## 1. Diagnosis

Root cause: the workbook is the only place transitive package-level conflicts can currently be expressed, so authors hand-compute the includes-closure of each primitive exclusion into stacked `replace` rows. This (a) multiplies maintenance for every new package, (b) abuses the `replace` action's "removes this default" semantics against a non-default option, (c) keeps a standing test gate red, and (d) evicts explicitly-selected options silently — confirmed as a UX gap by the product owner.

Risk: medium. Generator derivation is mechanical but mints rules; runtime gains a new visible component (toast). Change class: generator mechanism + runtime behavior + workbook data deletion + test-contract change, phased with a checkpoint.

Approved product decisions (2026-07-02):

- Eviction priority is one-directional: selecting a package evicts CBF-class targets (with notification); while the package remains selected, the evicted option is disabled with an honest reason. The evicted option does not block the package.
- Toast notification with verbose messaging on eviction — but NOT for every rule interaction. Scope rule: a toast fires only when an option the customer EXPLICITLY selected is evicted by a swap rule. Auto-added options evicted, and ordinary "blocked/disabled" states, never toast. This is a generic runtime guard, not a per-rule workbook flag — no new workbook column needed.

## 2. Recommended pass shape: two ordered phases, one checkpoint

### Phase A — derivation mechanism + eviction toast (code + tests, no workbook write)

1. `rules.py` (or a sibling helper in `corvette_form_generator/`): derive swap rules at generation time. For each selectable option S, compute its includes-closure I(S) (recursive walk of active `includes` rules, cycle-guarded, deterministic ordering). For each active primitive excludes rule (A excludes B) with B ∈ I(S) and S ≠ A: emit a derived rule S-evicts-A with `runtime_action="replace"`, provenance fields (suggested: `derived="True"`, `derived_via` = the includes path + primitive rule_id), and generated verbose reason text built from option labels, e.g. "Body-color painted Rockers and splitter (CBF) was removed: Z07 Performance Package includes Carbon Flash Carbon Fiber Ground Effects (CFZ), which replaces it." No model-specific knowledge in Python — pure graph mechanics over workbook rows.
2. De-duplication and precedence: if an authored rule for the same (source, target) pair exists, the authored row wins and no derived rule is emitted (authored rows keep workbook authority; this also makes Phase A parity-safe for Z06 where the five authored rows still exist).
3. Anti-surprise gate (hard requirement): generation emits a derivation manifest per model (derived rules with provenance, plus authored replace rows shadowing would-be derivations). In this pass, the ONLY approved net-new derived rules after Phase B deletes the five Z06 rows are the five CBF equivalents. Any other derived rule on any model is a hard stop → report for separate approval, never silently shipped. Implementation lane: either an allowlist asserted in tests or a generation-time check — implementer picks, tests pin it.
4. Runtime toast (`form-app/app.js` + `form-app/styles.css` + `form-app/index.html` if a container element is needed): when `removeReplaceRuleTargets` evicts a target that is in `state.selected` (explicit customer selection), enqueue a toast using the rule's verbose reason text. Auto-added evictions stay silent. Vanilla JS/CSS, no dependencies; dismissable + auto-timeout; `aria-live="polite"`; stacks safely if multiple evictions fire in one action; mobile-first layout per AGENTS §7.
5. Reason-text correction: derived rules and any authored replace rows whose target is NOT a workbook default must not say "removes this default"; generic copy is "X removes Y" with the includes-path detail. True default-replacements (e.g. J57→J6A) keep their default-flavored copy.
6. Tests (Phase A):
   - Python: derivation unit tests (closure walk incl. multi-hop PDD→Z07→T0F→CFZ, cycle guard, authored-shadowing, determinism, verbose-copy assembly, anti-surprise manifest).
   - Node: `workbook-schema-standardization.test.mjs` replace-allowlist test REWRITTEN to the new contract: authored replace rows must be true default-replacements (allowlist), and stacked-closure rows are forbidden BECAUSE derivation owns them — with the five CBF rows exempted until Phase B deletes them (or the test lands red-until-Phase-B; implementer picks, checkpoint documents it). New/extended runtime tests: eviction fires from derived rule; toast renders for explicitly-selected eviction; NO toast for auto-added eviction or plain blocks; evicted option shows disabled reason while source selected.

Checkpoint (stop, report before Phase B): mechanism tests green; regeneration of all three models produces contracts where the ONLY rule-surface diffs are the approved provenance/copy fields (authored rows still shadow derivations, so no net-new behavior yet); derivation manifest reviewed; replace-row classification report for stingray/grand_sport (§2 A5 audit: true default-replacement vs hand-stacked closure) delivered with a recommendation but no migration.

### Phase B — workbook deletion + regeneration (data pass, AGENTS §5)

1. Delete the five Z06 CBF stacked rows (`z06_rule_mapping` rows re-resolved at apply time by rule_id, not row number) via a one-shot temp script through `save_workbook_safely()`; manifest printed before apply; backup + on-disk read-back.
2. Regenerate all three models + registry. Expected diff (NOT parity): the five authored Z06 rules disappear and exactly five derived equivalents appear (same source/target pairs, `derived="True"`, new verbose copy); stingray/grand_sport contracts unchanged except approved copy/provenance fields from Phase A; CSV reviewed for the same bounded diff. Anything beyond the bounded expectation is a hard stop.
3. Full gates per §8, including browser smoke — REQUIRED this pass (runtime behavior + new UI component; parity proof is not available as a substitute).

## 3. Exact files expected to change

Phase A:
1. `scripts/corvette_form_generator/rules.py` (+ possibly a new `rule_derivation.py` helper) — derivation, shadowing, manifest, copy assembly.
2. `form-app/app.js`, `form-app/styles.css` (+ `form-app/index.html` if a toast container is added) — eviction toast, explicit-selection guard.
3. `tests/workbook-schema-standardization.test.mjs` — new replace-rule contract.
4. `tests/z06-performance-package-interactions.test.mjs`, `tests/multi-model-runtime-switching.test.mjs` — eviction/toast runtime assertions (whichever layer fabricates selections; extend, don't fork).
5. New/extended Python test module for derivation (co-locate with existing rules tests; if none exist, `tests/test_rule_derivation.py`).
6. `README.md` test-to-surface table if a new test module lands.

Phase B:
7. `stingray_master.xlsx` — delete 5 `z06_rule_mapping` rows (§5 safety).
8. `form-output/runtime/*-runtime-contract.json`, `form-output/stingray-form-data.{json,csv}`, `form-app/data.js` — regenerated; bounded-diff proven.
9. `docs/asset-media-drift-remediation-spec-2026-06-30.md` — follow-up 1 status flip.
10. This spec — close per AGENTS §11.

Explicitly NOT changing: dealer submission surfaces (untouched/preserved, AGENTS §6); `default_selection_rules` (CBF stays a non-default selectable option); stingray/grand_sport authored replace rows (audited and classified in the checkpoint report, migrated only under a separate approval); excludes_any group machinery (the jake-graphics-style clusters are a candidate future derivation lane, out of scope); workbook schema/columns (no new columns — notification scoping is runtime-generic).

## 4. Source-of-truth decision

Workbook authors only primitive facts: real incompatibilities (CBF excludes CFZ/CFV/EFY), the includes graph, and true default-replacements. The generator owns transitive derivation — generic graph mechanics, no RPO knowledge — and stamps provenance so every derived rule is auditable back to its primitives. Runtime stays a consumer: it executes the same `replace` action it already knows, plus a generic notify-on-explicit-eviction rule. No product knowledge moves into JS.

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
- Anti-surprise gate: net-new derived rules beyond the five approved CBF equivalents are a hard stop, per model, enforced by test/manifest — no "looks reasonable" judgment inside the pass.
- Toast fires only for explicit-selection evictions; no per-rule workbook flag; no new dependencies; vanilla implementation.
- Sync/asset surfaces untouched; no interaction with the 4D wildcard lanes.

## 7. Risks and non-goals

Risks:

- Derivation minting unexpected rules on stingray/grand_sport (latent closures never hand-authored) — mitigated by the anti-surprise gate; surfaced in the checkpoint manifest for human decision.
- Reason-copy churn breaking pinned test expectations — mitigated by §5 inspection lane; every expectation change reviewed against product copy intent.
- Toast noise if a package evicts multiple explicit selections at once — mitigated by stacking design (§2 A4) and the explicit-selection guard; verified in runtime tests.
- Eviction + dealer payload interaction — mitigated by §5 dealer verification lane.
- The pre-existing `test_source_assembly_characterization` red (flagged in 4D §12) touches rule/choice surfaces; triage it BEFORE this pass lands so its signal is clean, or explicitly re-reproduce it unchanged pre/post.

Non-goals: migrating stingray/grand_sport replace rows (classification report only); deriving from excludes_any clusters; two-directional eviction; per-rule notification flags; toast for auto-added changes (a broader "what changed" summary UX is a separate idea); the editor-lints and Z06-CBF-unrelated documented reds beyond the schema-standardization test this pass rewrites.

## 8. Validation plan

Phase A (run in order, report exact output):

1. Python: derivation unit suite + existing rules/contract suites (`.venv/bin/python -m pytest -q` targeted modules).
2. Regenerate all three models + registry: assert bounded diff (authored shadowing ⇒ provenance/copy-only changes); derivation manifests reviewed and attached to checkpoint.
3. Node: rewritten `workbook-schema-standardization` + extended runtime suites green (or documented red-until-Phase-B lane per §2 A6).
4. `git diff --check`; workbook and generated artifacts unchanged on disk at Phase A close except regeneration churn restored.

Checkpoint report (mechanism proof + stingray/GS replace-row classification + derivation manifests), then Phase B:

5. §5 evidence: lock check, `save_workbook_safely()` backup, on-disk read-back (5 rows absent by rule_id, all others untouched), deletion manifest.
6. `validate_workbook_package.py` + `validate_workbook_schema.py` — valid/0 issues.
7. Regenerate all three models + registry; bounded-diff proof (five authored → five derived equivalents; nothing else).
8. Full Node suite per README table; full pytest; the remaining documented pre-existing reds byte-identical to pre-pass reproductions.
9. Browser smoke — REQUIRED: Z06 flow — select CBF, select Z07 → CBF evicted + toast with verbose copy; CBF disabled with honest reason while Z07 selected; deselect Z07 → CBF selectable again; PDD/PDF/T0F/T0G variants spot-checked; no toast when CFZ auto-adds without CBF selected; summary/totals/download/dealer modal reflect post-eviction state; mobile viewport check.

## 9. Handoff requirements

AGENTS.md §11, plus: derivation manifests per model; the stingray/GS replace-row classification report with recommendation; bounded-diff proof for both phases; toast UX evidence (screenshots or DOM assertions); disposition of deferred lanes (other-model migrations, excludes_any derivation).

## 10. Approval question

Approve this pass as spec'd?

a. Approve both phases, checkpoint report between them (recommended).
b. Approve Phase A (mechanism + toast + tests) only; Phase B deletion approved separately after the checkpoint.
c. Changes to scope first.
