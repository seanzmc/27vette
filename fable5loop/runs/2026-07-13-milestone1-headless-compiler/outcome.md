# Milestone 1 Headless Compiler Implementation Outcome

Started: 2026-07-13T01:50:26Z

## Task summary

- Goal: Implement the approved Milestone 1 headless canonical-row compiler and comparator-evidence pipeline in `docs/ingest/milestone-1-headless-compiler-comparator-evidence-implementation-plan.md`.
- Changed surface: ingest Python modules, parser evidence, wizard session lifecycle, Python tests, ingest docs, and Fable closeout artifacts.
- Source-of-truth decision: target raw export owns target facts; `stingray_master.xlsx` is read-only canonical identity/metadata evidence; workbook `rule_phrase_map` owns phrase direction; selected comparator data is corroborating/prefill evidence only.
- Protected boundaries: no workbook writes, no `pass-c-3`, no plan/apply/approval artifacts, no browser/API changes, no generators, no `form-output/runtime/**`, no `form-app/data.js`, no promotion, and no dealer-submission change.
- Expected implementation files: the exact new/modified file set in the approved spec §6 plus this run receipt and `fable5loop/STATE.md` closeout.
- Workflow: fan-out-and-synthesize for read-only audits, vertical TDD implementation, then independent adversarial verification.

## Required outcome criteria

1. The new deterministic compiler artifacts implement the approved acyclic authority-envelope and dependency-scoped semantic-hash contracts.
2. Stable identity and reconciliation reuse unique existing IDs, refuse ambiguous matches, retain unmatched established rows conservatively, and never use source coordinates or comparator IDs for target identity.
3. Comparator evidence uses active generation-discoverable models and runtime-equivalent filtering; comparator data never becomes target product truth.
4. Relationship compilation uses active workbook `rule_phrase_map`, preserves direction, and emits typed blockers instead of Python fallback business truth.
5. The compiler produces explicit dispositions for every source feature/comparator fact and every registered required/optional/global family; unsupported applicable data becomes typed blockers.
6. `WizardSessionStore.compile_canonical_rows()` is the only entrypoint, persists a coherent artifact set atomically, refuses legacy/downstream states, preserves selective resolution validity, and is audit-idempotent.
7. Fixture greenfield/reprocess proofs and one mandatory fresh ignored current-export run complete; `compiled_with_exceptions` is acceptable when all feature dispositions and blockers are explicit.
8. The canonical workbook SHA and mtime remain unchanged; protected generated/runtime/browser/apply/promotion surfaces remain unchanged.
9. The exact focused gate, full pytest suite, workbook package/schema validation, syntax checks, and Fable loop validator run with real output; any baseline reds are reproduced and classified rather than hidden.
10. An independent verifier returns PASS after inspecting final artifacts, diffs, proof output, and protected-boundary evidence.
11. The approved spec, parent design, ingest index, Fable receipt, and `STATE.md` close with evidence and identify Milestone 2 as next.

## Stop conditions

- Stop for user direction if implementation needs workbook structure/content changes, parser changes beyond additive price-header evidence, editor metadata changes, browser/API work, generator/runtime behavior, a new dependency, or any product/business decision.
- Stop on source-export SHA drift.
- Stop if selective invalidation cannot preserve unaffected subject/resolution/derivation semantics.
- Stop if a comparator fact would need to populate target product data.
- Stop if complete source/family disposition cannot be proven.
- Stop if the workbook or protected surfaces change and cannot be restored as validation-only churn.

## Independent verifier requirements

The verifier must inspect the approved spec, final diff, all compiler artifacts from fixture and real-source proofs, validation output, workbook before/after fingerprints, and protected-path diffs. It must grade each criterion as pass/fail/blocked and state explicitly that it edited no files.

Max maker/verifier iterations: 3.

## Implementation result

Status: complete. Exact-current independent verification passed on 2026-07-13.

- Added deterministic compiler, comparator, relationship, identity, exception, and session-lifecycle modules.
- Preserved additive parser evidence and made workbook `rule_phrase_map` the production phrase authority.
- Kept comparator facts corroborating: portable direct/group/exclusive/price/default facts become typed proposals unless target evidence independently confirms them.
- Added occurrence-aware identity, conservative retention, exact canonical-key rejection, action/disposition separation, exact-header/type validation, and dependency-bound derivation versions.
- Added strict resolution payload validation; only actually consumed row-producing resolutions can clear readiness. `choose_section` is consumed into an option row; unsupported row-producing resolutions remain blockers.
- Added atomic coherent artifact replacement, artifact-graph readback, downstream-state refusal, dependency-scoped invalidation, and append-once audit lifecycle events.
- Added exact source-feature and family coverage with retained canonical rows materialized, model modes, target-aware comparator dispositions, per-model/family/action/status counts, readiness boundaries, and a metadata-driven reverse-reference graph.
- Independent BLOCK review defects were corrected: false-ready action/disposition pairs, conflicting or invalid resolutions on producer and readback paths, fail-open artifact hash/authority checks, price/comparator row-order sensitivity, non-global occurrence stages, shared-sheet key/relationship duplication, comparator proposal/report drift, false compiled-status coverage, false comparator corroboration, vacuous evidence partitions, incomplete canonical typing/family row materialization, and stale comparator cache after source reparse.

## Proof result

- Focused compiler contracts: 68 passed, 6 subtests passed.
- Broad Milestone 1 gate: 275 passed, 6 subtests passed.
- Workbook package/schema: valid with zero issues.
- Mandatory current-export proof: `compiled_with_exceptions`; 5,101 unique rows across 19 materialized families; 800 typed subjects; 17,208 source features and 75 family entries dispositioned; graph, recomputed artifact hashes/authority, three distinct nonempty target partitions, 2,405 normalized workbook-evidence entries with an exact dependency join, subject/derivation versions, global keys, canonical integer/Boolean/enum types, relationship semantics, comparator proposal parity, and reverse references valid. The 4,250 compiled status features exactly equal source-bound ready OVS dependencies; 752 selected non-emitted status features remain open exceptions. All 66 comparator corroboration claims have exact ready manifest semantics. Grand Sport X is `greenfield`; ZR1/ZR1X are `reprocess`.
- Unchanged recompilation: all compiler artifact bytes and inodes unchanged; no duplicate audit event.
- Workbook/source: SHA, mtime, and size unchanged; no Excel lock, backup, plan, approval, apply, generation, publication, or promotion evidence.
- Final full repository suite: 561 passed, 13 subtests passed, and 5 pre-existing failures. The Milestone 1 receipt contract passed; four remaining failures were reproduced identically in an isolated `git archive HEAD` checkout during this run and the stale-pointer failure was previously reproduced at HEAD. An earlier untracked smoke-directory failure was cleaned and its guard now passes.
- Independent verification: `deleg_4b8ff2b9` returned three PASS verdicts against implementation/test digest `ce510eafc6aaa24c2841e2a036ed8132aec41db1bbdde0635e5de7790bd75ead` and the exact manifest/queue/report proof SHAs.

Detailed evidence: `validation-output.txt`, `real-source-summary.json`, `recompile-summary.json`, `artifact-audit-summary.json`, and `no-write-summary.json`.

## Residual boundary

The real run intentionally remains `compiled_with_exceptions`; all three models are not compile-ready. Milestone 2 owns browser/API exception review. Milestone 3 owns `pass-c-3` projection and temporary deployment proof. No write or deployment authority is implied.
