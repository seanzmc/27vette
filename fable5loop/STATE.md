# 27vette Project Memory · Operational Handoff

This file is the centralized operational handoff plus durable project memory.
Read `Current handoff` first. Overwrite every field in that block after each
substantive repository task; do not append competing current-status narratives.
Detailed requirements and acceptance evidence belong in the owning
specification. History lives in `fable5loop/STATE-archive.md`.

## Memory entry contract

Every new bullet under `Verified facts`, `General rules`, `Open failures`, and `Lessons learned` must include an ISO date and an `Evidence:` reference to a source file, validator output, command output, or reproducible investigation note. Do not record speculative claims as verified facts.

Keep this file small — it is read at the start of every session:

- `Last session` holds the five most recent entries. Move older ones to `fable5loop/STATE-archive.md`.
- When a `Verified facts` entry is superseded, fixed, or closed, replace it with the superseding entry and move the original to the archive; do not keep both.
- Close or withdraw `Open failures` rather than annotating them in place.

## Current handoff

- **Updated:** 2026-09-02
- **Owning specification:** `workbook-manager/audit-spec.md` (§7 Checkpoint 2C
  closed; §3 P2.8 checked; §14 record added). Task prompt:
  `docs/wbm-checkpoint-2c-prompt.md` (lives on branch
  `claude/fable-5-1-prompting-3cd6c7`, not on `main`).
- **Active workflow:** Workbook Manager Checkpoint 2C — draft-effective
  connected details — COMPLETE; PR #73 open, not merged. Checkpoint 2D is not
  authorized (its §5.1 registry proposal + explicit approval gate is untouched).
- **Current status:** one backend overlay adapter
  (`workbook-manager/backend/app/draft_overlay.py`) feeds option/group details,
  structure nodes/steps/placed options, and Asset Manager items with `state`,
  exact `operation`, `base`/`proposed`/`effective`, `changed_fields`,
  `direct_impact`, `conflicts`; terminal/stale drafts report `conflicted` with
  `effective: null` on connected details (previously a cancelled draft still
  rendered `modified`). One shared `components/DraftOverlay.jsx` +
  `draftOverlayModel.js` replaced four local diff/badge renderers; headings and
  fact chips show authored (struck) → proposed; Form Overview now loads the
  structure with the active draft. README Workflow step 4 and User Guide §4
  updated.
- **Branch/commit:** `feat/workbook-manager-checkpoint-2c` from `origin/main`
  `118c0894`; implementation `dab1dc26`; closeout commit follows; PR #73
  (`https://github.com/seanzmc/27vette/pull/73`).
- **Last completed:** RED (`'modified' != 'conflicted'`, `KeyError:
  'changed_fields'` / `'operation'` / `'draft_overlay'` on existing routes) →
  GREEN; isolated Chrome proof desktop + 390x844 of Save, close/reopen, hard
  reload, Back/Forward, full reversion, stale binding, add, modify, pending
  delete; spec closure.
- **Validation:** one-process catalog Manager serial group on the final tree —
  384 passed, 2 skipped, 77 subtests (94 s); governance + catalog owners 124
  passed; frontend production build; `git diff --check`; protected hashes
  (`stingray_master.xlsx`, `form-app/data.js`, six runtime contracts)
  identical. PR planner selects 12 shards for the changed paths; every file
  they name ran locally. Not run: copied-workbook Apply/Rebuild, candidate
  lane, WordPress/dealer/deployment (read-model/presentation change only; no
  catalog edit). Remote CI + Codex disposition pending.
- **Next action:** review/merge PR #73 (separate authority). Then, per the
  2026-09-02 handoff before 2C: the §6 deletion PR folding the two governance
  findings documents into `audit-spec.md`/`AGENTS.md`, and the §3.3
  ambient-binding checkpoint (four live sites) — both need a new instruction.
- **Blockers or closeout gaps:** none. Latent: catalog `owning_specification`
  (C8) still points at an archived path; `AssetManager.jsx:341` bulk button still
  keys on `draftMutable` alone (ambient-binding class, out of 2C scope).
- **Protected boundaries:** dealer submission, deployment, workbook, generated
  artifacts, `form-app/data.js`, WordPress, catalog `ci`/`serial_groups`,
  workbook-domain registry, ChangeSet/writer — untouched.

## Verified facts

- 2026-08-27: **The candidate lane's `semantic_drift` stage is proved and its canary can no longer go inert silently.** Supersedes the 2026-08-17 open failure that recorded both forcing tests failing with empty drift. The hardcoded `zr1_options.opt_efr_001` probe was replaced by `_live_drift_probe()` in `tests/test_verify_workbook_candidate.py:75`, which selects a probe from the retained contract's `choices` ∩ `standardEquipment` and raises rather than asserting nothing when no option reaches both. Verified: `.venv/bin/python -m pytest tests/test_verify_workbook_candidate.py -q -k drift` → 4 passed, 13 deselected in 26.77s. The separate workbook/generator question behind `finding.dead_semantic_drift_canary` — why an `active=True, selectable=False` option emits nothing — is untouched and still unanswered. Evidence: the cited test source and the recorded run.

- 2026-08-24: **Reading a read-only openpyxl sheet per cell was 90%+ of workbook validation, and removing it was a 54x win.** `validate_workbook_schema` now calls `column_values()`, which streams each sheet once and returns values keyed by column in row order, preserving the original column-major issue sequence. Proved by differential over a fixed corpus — canonical with and without the live-contract check, plus injected boolean/RPO/price/combined drift — with every issue list identical including order (0, 0, 7, 3, 2, 12 issues). Canonical validation 66.54s to 1.23s; the `scripts/validate_workbook_schema.py` gate ~66s to 1.36s; verified fixture build 71.01s to 7.31s; unchanged comparison export 67.91s to 5.41s; `tests/test_workbook_manager.py` ~640s to 71.47s; candidate lane's 17 tests ~900s of CI to 35.70s local. All affected owners pass and the canonical workbook stayed byte-identical at `922de392`. Evidence: `docs/pr-workflow-cleanup.md` "The real cost was one quadratic loop — fixed".

- 2026-08-24: **Rebalancing CI shards by `-k` expression cannot fix a shard whose cost is one test.** Any partition holding `test_export_overlays_registry_owned_projection_fields` had to pay the 71s fixture plus 68s unchanged export plus 212s overlay — 351s of the shard's 356s. `manager-api-core` is 71s plus a single 213s test, exactly its 284s total. Measure the per-test distribution before proposing a split; a shard total alone will mislead. Evidence: `--durations=0` runs recorded in `docs/pr-workflow-cleanup.md`.

- 2026-08-17: **The included-seatbelt runtime contract is now data-derived and measured.** For any interior, the published registry carries the whole relationship: an `includes` rule (interior → option, `auto_add=True`) means the option auto-adds at $0; an `excludes` rule (option → interior) means the option is refused with a disable reason; a `colorOverrides` row (interior, option, `requires`, `adds_rpo`) means the option is selectable at its base price and adds that RPO. Measured on z06 `3LZ_AE4_H8T`: 719 sticks at $0 with no D30, and 3F9/3M9/379/3N9 each stick at $595 and add D30. On the asymmetrical `3LZ_AE4_HAG` and `3LZ_AE4_HVZ`, every peer but the included one is refused with copy naming the interior. Any test asserting the retired "included colour blocks every peer, only Black allowed" behaviour is stale. Evidence: `docs/archive/completed-specs/fast-layered-validation/2026-08-17-fast-layered-validation-suite-checkpoint-1-evidence.md` and the sweeps in `tests/z06-runtime-rule-corrections.test.mjs` / `tests/stingray-form-regression.test.mjs`.

- 2026-08-17: **The node readiness lane cost was one duplicated command, not the gates.** Removing the `scripts/validate_workbook_schema.py` invocation from `tests/workbook-schema-standardization.test.mjs` took that file from 64.97 s to 0.91 s and the fourteen-gate lane from 109.27 s to 52.63 s. Everything else in that file — the whole registry-derived structural sweep — costs under a second. Before optimizing a slow gate, measure whether its cost is a subprocess another gate already runs. Evidence: `docs/archive/completed-specs/fast-layered-validation/2026-08-17-fast-layered-validation-suite-checkpoint-1-evidence.md` §1.

- 2026-08-17: `tests/conftest.py` owns the `scripts/` `sys.path` insertion for the whole test directory, so no pytest command needs `PYTHONPATH=scripts` and every `tests/test_*.py` file runs standalone. The options-sheet quality CLI still needs it, because it is a module invocation rather than a pytest run. Evidence: `env -u PYTHONPATH .venv/bin/python -m pytest <file> -q` for the three previously order-dependent files — 15, 32 and 18 passed.

- 2026-08-17: The validation inventory now has a machine-readable owner. `tests/validation_catalog.json` holds 76 gates, 7 suites, 5 acceptance-lock records, 55 coverage-ledger entries, 7 stale assertions, 10 findings, and 8 expensive setups (counts current as of 2026-09-01 and enforced against the catalog by `scripts/validate_state_handoff.py`; the 2026-08-17 baseline recorded 59/6/33/8 and had gone stale unnoticed); `tests/test_validation_catalog.py` enforces the five §7 conditions with a forced mutation behind each, at gate and suite level. Read counts, timings, layer, authority class, isolation, serialization, and disposition from the catalog rather than re-measuring or re-deriving them. Measured serial baseline on Node 26.7.0 / Python 3.14.7: Node readiness lane 109.27 s / 298 tests / 292 pass; all 16 Node files 111.75 s / 305 tests; Python metadata gate 176.60 s; Manager checkpoint 1,123.47 s; full Python inventory 2,381.46 s / 734 collected. Evidence: `docs/archive/completed-specs/fast-layered-validation/2026-08-17-fast-layered-validation-suite-checkpoint-0-baseline.md`.

- 2026-08-13: The focused GSX/ZR1/ZR1X hotfix now present on `origin/main` corrected workbook-owned GSX 3LT AH2 pricing to `$0` while retaining the 2LT `$1,695` charge, activated ZR1/ZR1X C2Z as non-selectable Standard Equipment with coupe-only `standard` ownership and convertible `unavailable` ownership, regenerated and published the three affected runtime contracts, advanced the data-bundle cache token from 31 to 32, and added focused runtime regression coverage. Its guarded workbook batches, package/schema gates, 67-case runtime switching gate, composed six-model candidate lane, and local browser proof passed before PR #11 merged as `c34f584`. Evidence: `form-output/workbook-edit-log.jsonl`, `tests/multi-model-runtime-switching.test.mjs`, and commit `c34f584`.

- 2026-07-23: CORRECTION superseding every prior entry that calls raw ingest live, approved, or a next action: the ingest wizard, compiler/exception queue, ChangeSet emitter, ingest-specific deployment proof, browser UI, helper package, and their tests were retired because their imported data was not trustworthy enough to remain executable. Historical guidance moved to `docs/archive/retired-ingest/2026-07-23/`; it is evidence only. The generic `workbook-changeset-1` parser/service remains solely as approved target infrastructure for later reliable Workbook Manager writes. Evidence: `AGENTS.md` §8 and `docs/superpowers/specs/2026-07-23-validation-single-lane-active-surface-cleanup.md` Pass I.

## General rules

- 2026-08-26: A memory file that is read at the start of every session must be capped, not appended to forever. `fable5loop/STATE.md` reached 154 KB (~38k tokens per session) with 82% of it in two append-only chronological sections nothing read. Keep the live file under the validator's size budget, hold at most five `Last session` entries, and replace superseded entries instead of annotating them in place. Evidence: `scripts/validate_state_handoff.py`, `fable5loop/STATE-archive.md`.

- 2026-08-19: When making a validation gate cheaper, re-derive whether each surviving assertion can still fail. A shared fixture that widens an input can silently make an assertion unreachable while every test stays green — `changed_models=["*"]` in the candidate lane makes `unexpected_drift` (defined as "drifted AND not declared") permanently empty, so the stale-retained-artifact and generation-filter proofs both became tautologies without failing. Evidence: `tests/test_verify_workbook_candidate.py`, `scripts/verify_workbook_candidate.py`.

- 2026-08-19: A validation-catalog invariant that branches on a self-declared flag is bypassed by declaring that flag false. The isolation checks all guard on `generates`, so three Node gates claimed `read_only` while writing temp workbook copies. Assertions about a gate's declarations must also hold in the negative branch. Evidence: `tests/test_validation_catalog.py::test_no_output_isolation_kinds_declare_no_writes`.

## Open failures

- 2026-08-27: **`assert_runtime_contract()` still does not implement the rejection matrix's variant and workbook-binding clauses.** Carried forward from the 2026-07-26 Pass 3 requirement-8 scan, whose promotion-requirement half closed while this half did not. `scripts/corvette_form_generator/runtime_contract.py:117-175` validates `dataset.name` / `model` / `model_year` / `status` but never `dataset.source_workbook`, and implements no variant drop, duplicate, or rename clause, so a contract generated from one workbook and written into another candidate's root passes the strict validator. `tests/test_all_model_runtime_generation.py:199-206` holds the check in its place and says so in its own docstring: "the strict validator does not yet enforce it… Checked here until the validator owns it." The companion sub-clause is resolved — `promotion_requires_runtime_contract_assertion()` has zero occurrences in `scripts/`, `tests/`, and `workbook-manager/`. Evidence: the cited source and test lines, plus `fable5loop/runs/2026-07-26-pass3-candidate-lane/validation-output.txt` for the original finding.


- 2026-08-17: `tests/test_runtime_metadata_guards.py::RuntimeMetadataGuardTests::test_live_workbook_default_selection_display_behavior_rows_are_explicit` fails: it pins a hardcoded three-row default-selection display list over a hardcoded three-model tuple, and the workbook now also carries `('z06', 'z06_default_nga_unless_nwi', 'default_selected')`. Fails identically with and without `PYTHONPATH=scripts`, so it is not an import artifact. Fix as parity against the active `default_selection_rules` rows for every promoted model; do not refresh the literal to four rows. Owned by the fast-suite specification, Checkpoint 1. Evidence: `docs/archive/completed-specs/fast-layered-validation/2026-08-17-fast-layered-validation-suite-checkpoint-0-baseline.md`.

- 2026-07-28: **`app.js` treats exclusive-group peers asymmetrically and nothing guards it.** `disableReasonForChoice` skips same-group peers in the loop over rules that TARGET the choice (`app.js:1101`, `sameExclusiveGroupPeer`) but not in the loop over rules the choice is the SOURCE of (`app.js:1122`). A redundant workbook row is therefore not merely noisy — it silently disables one direction of a choose-one swap. The nine offending rows are deleted and the new gate blocks re-adding them, so no live defect remains, but the runtime is still one bad authoring row away from the same class of bug. Closing it means adding the peer guard to the source-side loop, with a test that fails against today's `app.js`. Not done here: it is a runtime behavior change outside the owning cleanup spec's scope. Evidence: 2026-07-28 Verified facts entry.

- 2026-07-28: Generation's `active: "False"` / `runtime_action: "omit_redundant_same_section_exclude"` marking on redundant excludes rows is **inert**. `rules.py` computes it and ships it into the contract, and `app.js` never consults either field on the disable path — it filters on `rule_type`/`source_id`/`target_id` only. Either the runtime should honor the flag or generation should stop emitting the row. Recorded, not resolved. Evidence: `rules.py:163,201-202` vs `app.js:1100-1122`.

- 2026-07-27: `tests/z06-registry-publication.test.mjs` now doubles as a staleness gate — its parity test compares an isolated rebuild against the tracked `form-app/data.js`, so regenerating a promoted artifact without republishing turns it red. That overlaps `schema_validation`'s `app_registry_stale` check. Deliberate, but recorded so the failure mode is not a surprise. Evidence: `fable5loop/runs/2026-07-27-pass3-atomic-registry-write/verifier-report.md`.

- 2026-07-27: The candidate lane's byte-identity boundary check cannot run concurrently with the node gates. A parallel gate run rewriting `grand-sport-runtime-contract.json` made `tests/test_verify_workbook_candidate.py` report three spurious `boundaryViolations` failures. Serial runs pass. Either serialize these in any harness that runs both, or teach the check to ignore paths a sibling process owns. Evidence: `fable5loop/runs/2026-07-27-stale-unpromoted-contract-refresh/verifier-report.md`.

- 2026-07-26: Convergence dropped three of the retired builder's conditional validation checks with no equivalent: `redundant_{rule_id}` (info row only — the payload suppression survives in `rules.py:163,201-202`), the `active_variant_count`/`availability_row_count` mismatch guards, and `missing_{key}_{rule_id}` for rules referencing unknown entities. The last is a change in *reporting*: the new builder silently filters dangling rules where the old one flagged them. `missing_r6x_included_option_` was ported to `interiors._require_r6x_included_options` as a hard failure (latent-live: 15 interiors carry `requires_r6x`, 0 violate). `heuristic_section_step_key_` is now structurally impossible. Evidence: `fable5loop/runs/2026-07-26-pass2-builder-characterization/validation-output.txt`.

- 2026-07-25: The runtime-step completeness check has one disclosed hole: dropping a step from EVERY active model passes, because the cross-model union has nothing left to compare against. `summary` is the only exposed key — `step_order_summary_map` gives the other 13 a model-scoped workbook reference. The retired Python `STEP_ORDER` tuple caught this for promoted models. Closing it needs a model-scoped workbook reference to the summary step. Repro: delete the `summary` row from all six models in `runtime_steps`, then generate. Evidence: `fable5loop/runs/2026-07-25-pass2-shadow-authority-purge/validation-output.txt`.

- 2026-07-13: `tests/test_source_assembly_characterization.py::test_shared_assembler_preserves_stingray_runtime_drift_surfaces` has a pre-existing expectation that UQT choices omit `display_behavior`, while the current assembled choice includes it. This is outside Milestone 2 and remains a separate source-assembly/display-behavior characterization pass. **Now owned by Pass 2 receipt B (spec requirement 3) — it is a live instance of a genuine Stingray-vs-workbook builder divergence and must be resolved by the characterization work, not suppressed.** Evidence: `fable5loop/runs/2026-07-13-milestone2-exception-browser-flow/validation-output.txt`.

- 2026-07-25: Spec requirement 4 ("the single builder operates on one loaded, frozen workbook snapshot… optional inspection/report output consumes that in-memory result; it never reopens or reconstructs the workbook") is only partly met. Each builder now loads once and closes deterministically, but a non-Stingray assembly still opens two workbooks (three under `--emit-inspection`) because `build_contract_preview` and `build_form_data_draft` are separate builders. Closing this needs the single-builder work of requirement 2. Evidence: `fable5loop/runs/2026-07-25-pass2-summary-and-snapshot-authority/verifier-report.md`.

## Lessons learned


- 2026-07-30: A concurrency primitive held across a FastAPI dependency's `yield` has two distinct failure modes, and neither is visible from ordinary request-path reasoning. First, a synchronous generator dependency's enter and exit run on *different* anyio threadpool threads, so an `RLock` acquired before the yield can never be released — every later request wedges. Second, even a thread-agnostic `Lock` must not be *blocked on* from a threadpool worker: each waiter parks a thread token, and once all tokens are parked the lock holder cannot obtain a thread to finish and release, which is an unrecoverable process wedge (reproduced deterministically with the limiter shrunk to four tokens). Take cross-request locks in an `async` dependency polling a non-blocking acquire under a bounded deadline, and prove the fix by shrinking `anyio.to_thread.current_default_thread_limiter().total_tokens` through the TestClient portal. Evidence: `fable5loop/runs/2026-07-30-dbpass3-request-connections/verifier-report.md`.

- 2026-07-30: "Refuse the flag" is not "refuse the capability." A `run.sh` guard that rejected `--workers` still allowed `WEB_CONCURRENCY=4`, because uvicorn reads the worker count from the environment when the flag is absent. Any guard that claims a deployment mode is unsupported must cover argv *and* every environment variable the tool consults, and the test must exercise the environment path. Same class: a coverage test that samples four of seven mutating routes cannot fail for the three it skips — enumerate the full route set. Evidence: `fable5loop/runs/2026-07-30-dbpass3-request-connections/verifier-report.md`.

- 2026-07-30: An assertion that a value is merely nonzero can be satisfied by a library default. `PRAGMA busy_timeout > 0` passed with the explicit pragma deleted, because `sqlite3.connect(timeout=...)` already sets 5000 ms. Assert the *configured* value and prove it moves with its override. Evidence: `fable5loop/runs/2026-07-30-dbpass3-request-connections/validation-output.txt`.

- 2026-07-30: A test module that purges `sys.modules['app*']` to re-read environment config must restore the original module objects, not leave the package purged. Sibling test modules hold references to the first `app.sync`, and a later re-import gives them a second `app.config` whose paths disagree — surfacing as an unrelated export-path failure only when the modules run in the same process. Evidence: `fable5loop/runs/2026-07-30-dbpass3-request-connections/validation-output.txt`.

- 2026-07-29: Protected-root hashers must distinguish exact OS metadata from generated outputs without turning ignored files into a general exemption. On macOS, Finder can recreate `.DS_Store` inside `form-output/` during an 11-minute gate. Exclude only that exact basename, prove a near-name and arbitrary untracked file remain visible, and rerun the long lane while the metadata is actually present; merely deleting the file before a run does not prove the branch. Evidence: `fable5loop/runs/2026-07-29-pass4a-macos-boundary-hardening/verifier-report.md`.

- 2026-07-29: An acceptance fingerprint over `git diff` is incomplete when `git mv` records are staged and subsequent edits are unstaged; it hashes only the worktree side. Use `git diff HEAD` for the complete staged-plus-unstaged patch, and exclude concurrent files explicitly. Also preserve command names in explicitly superseded plans: historical prose is evidence, not an active-guidance defect. Evidence: `fable5loop/runs/2026-07-28-pass4a-gate-authority-closeout/verifier-report.md`.

- 2026-07-27: "This guard is unreachable, so it cannot be tested" is a claim about one call site, not about a concept. The same `!= "current_generation"` exemption was genuinely dead in the module that *raises* on the dominating vocabulary check, and fully live in the module that *accumulates* issues and keeps going — where restoring it silently dropped a schema error while every test stayed green. Trace each site's control flow before writing an untestability admission; the admission is itself a claim needing evidence. Evidence: `fable5loop/runs/2026-07-27-pass3-promotion-type-closure/verifier-report.md`.

- 2026-07-26: A test whose expected set is derived from the same sheet the code under test reads cannot detect a change to that sheet — both sides move together. Deactivating a model left the "discovery matches the workbook" assertion green while the per-model parametrized coverage silently shrank from 22 cases to 19. Pair every derived-vs-derived comparison with a named expected set, pin `parametrize` to the named set, and say in the docstring which direction of change each assertion can catch. A count assertion is not a membership assertion. Evidence: `fable5loop/runs/2026-07-26-pass2-compat-scope-and-six-model-gate/verifier-report.md`.

- 2026-07-26: "No consumer" concluded from a filename grep is unsound when paths are constructed. `f"{export_slug(model_key)}-form-data.json"` is a real reader that no search for `stingray-form-data` can find; the false negative surfaced only by deleting the supposedly-dead fixture line and watching a test fail. Resolve paths through the real resolver over the real rows, and treat delete-and-rerun as the confirmation step. Evidence: `fable5loop/runs/2026-07-26-pass2-compat-scope-and-six-model-gate/validation-output.txt`.

## Last session

2026-08-29 (repository hygiene — fixture mutation audit, PR #63): **Merged to `main` as `a59208e`.** Mutation-audited the two shared Python fixture modules; 4 of 5 mutations discriminate, and `build_master_workbook`'s `zr1_options` collision row was proved blind — its comment cited a plan builder retired with raw ingest in `667aad5`, so the comment now records the proven active-flag property instead. Also declared `tests/validation_catalog.json` in the `reads` sets of `cmd.state_handoff_validator` and `py.test_state_handoff` (`6c29cf9`). Evidence: `test_editor_ops_global_families`, `test_validation_catalog`, `test_workbook_manager_fixtures` 48 passed; `scripts/validate_state_handoff.py` passed. Node helpers under `tests/lib/` remain unaudited.

2026-08-29 (Workbook Manager — Checkpoint 1B, registered structure management): **Merged to `main` as `3c6b0cc` via PR #62.** Form Overview derives its structure-family index from registered fixed-sheet specs; loaded table/model identity fail-closes stale actions during transitions, and action capabilities delegate to the durable mutation ownership guard rather than table editability. Both PR #62 P2 findings remediated in `3c37031`. STRUCT-01–04 pass. Evidence: focused catalog/form-graph owners 33 passed; catalog-selected Manager serial group 335 passed, 2 skipped, 74 subtests; canonical workbook, published data/cache HTML and all six runtime-contract SHA-256 values matched preflight. Checkpoint 1C remains unauthorized.

2026-08-27 (repository token-pit audit and state-handoff cleanup): **Docs and validator-constant only; no source, workbook, generator, registry, or runtime change.** Audited the per-task mandatory read chain, which PR #49 had already cut from 220,827 B to 58,144 B. Corrected seven stale factual claims in `README.md`, each checked against `model_master`, `model_registry_promotion`, the live `window.CORVETTE_FORM_DATA` keys, the workbook sheet list, and the `form-output/` tree: the Roadmap still described three live models and gated ZR1/ZR1X behind a pending review, `zr1_*`/`zr1x_*` were labeled inactive scaffolds, the `grand_sport_x_*` sheets were undocumented, `backups/` did not exist, the registry example showed three models, a caveat claimed draft-worded artifact names that no longer exist, and a cross-reference named a missing heading. Closed four `Open failures` proved done against the merged tree, archived five retired-surface `Lessons learned`, added the missing entries for PRs #48/#49/#50, and lowered `MAX_STATE_BYTES` from 60,000 to 40,000. The node gate matrix was confirmed to list exactly the 19 files in `tests/*.test.mjs`. Evidence: `tests/test_validation_catalog.py` + `tests/test_state_handoff.py` 38 passed, `scripts/validate_state_handoff.py` passed, `node --test tests/z06-registry-publication.test.mjs` 2 passed with `form-app/data.js` sha256 unchanged, `tests/test_atomic_registry_write.py` 9 passed.

2026-08-26 (Workbook Manager UX recovery — Checkpoint 3F, persistent draft navigation): **Checkpoint 3F merged to `main` as `0245528` via PR #50.** Added a persistent draft tray plus dependency-free URL/navigation state (`workbook-manager/frontend/src/navigationState.js`), preserved the current navigation when a draft starts, and dropped stale cross-model detail before its replacement loads. 12 files, +842/-71, with backend draft and connected-editing test coverage extended. Evidence: `git log 0245528` and `docs/superpowers/specs/2026-08-21-workbook-manager-ux-recovery.md`.

2026-08-26 (retire the Fable 5 loop and cap the state handoff): **Merged to `main` as `dca3605` via PR #49.** Moved the loop scaffold to `docs/archive/fable5-loop/` and 120 KB of history to `fable5loop/STATE-archive.md`, replaced `scripts/validate_fable5_loop.py` with `scripts/validate_state_handoff.py`, and replaced `tests/test_fable5_loop_contract.py` with `tests/test_state_handoff.py`. 39 files, +705/-945. The mandatory per-task read chain fell from 220,827 B to 58,144 B. Evidence: `git log dca3605`.
