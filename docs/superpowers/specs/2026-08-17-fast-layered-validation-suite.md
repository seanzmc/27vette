# Fast Layered Validation Suite Specification

Status: COMPLETE — Checkpoints 0–6 complete 2026-08-20.
Date: 2026-08-17
Branch: `claude/fast-layered-validation-suite-4c31f6` (spec authored on `main`)
Recommended implementation reasoning: medium. Escalate only for a specific
data-integrity, concurrency, protected-output, or dealer-boundary judgment.

## 1. Decision and authority

This specification owns the replacement of the current overlapping validation
inventory with one fast layered suite. It extends, but does not reopen, the
completed single-lane architecture in
`docs/superpowers/specs/2026-07-23-validation-single-lane-active-surface-cleanup.md`.
That completed specification remains authoritative for the canonical path:

```text
stingray_master.xlsx
  -> package, schema, and source-quality validation
  -> workbook-discovered six-model generation in an isolated candidate root
  -> strict runtime-contract validation
  -> complete candidate registry
  -> browser/runtime harness
  -> explicit publication only after approval
```

This specification changes how that path is tested, selected, timed, and
reported. It does not create a second generation, publication, workbook-write,
or runtime path.

The workbook remains the only source of product and business data. Test code
may contain a deliberately small, reviewed acceptance-lock inventory for
protected decisions, but must not become a parallel database of model rows,
prices, counts, URLs, relationships, or variant matrices.

`docs/superpowers/specs/2026-08-15-workbook-manager-ux-recovery.md` continues to
own the paused Manager product recovery. This suite must support that work, but
does not implement its UI checkpoints.

## 2. Goal

Build a validation system that is fast enough to use continuously and strong
enough to protect the customer runtime without turning ordinary workbook data
changes into widespread stale-test maintenance.

The finished suite must:

1. Separate structural invariants, workbook-to-output parity, runtime state
   invariants, and intentional product acceptance locks.
2. Pay each expensive canonical-workbook setup cost once per validation layer,
   then share immutable results safely.
3. Discover models, variants, promoted artifacts, source rows, and assets from
   their authoritative workbook/registry owners instead of repeating literals
   in test files.
4. Exercise every promoted model and declared variant through a generic runtime
   state matrix.
5. Keep a small named set of customer-critical behavior locks whose failure
   truly requires product review.
6. Make changed-surface selection mechanical and visible.
7. Produce a stage-timed machine-readable report and a concise human summary.
8. Preserve the canonical workbook, generated artifacts, published registry,
   dealer boundary, and live systems during every normal validation run.

## 3. Current diagnosis and evidence

### 3.1 Node readiness audit — 2026-08-17

The documented fourteen-gate Node readiness matrix was run serially against
`main` at `3a7fc52` under local Node `26.7.0`:

| Result | Evidence |
|---|---|
| Total | 298 tests in 106.38 seconds |
| Passed | 292 |
| Failed | 6 assertions across 5 files |
| Slowest gate | `workbook-schema-standardization`, 62.91 seconds |
| Next slowest | `stingray-runtime-contract`, 16.09 seconds |
| Protected tracked diff | none |

The six failures are stale expectations, not demonstrated runtime defects:

- three assertions retain the superseded included-seatbelt lock/Black-only
  behavior while the current six-model authority proves workbook-approved paid
  alternatives;
- Grand Sport pins `colorOverrides.length === 263` while the current valid
  workbook produces 281 rows;
- Grand Sport pins an obsolete J6F image URL instead of comparing with the
  active `asset_map` row;
- isolated registry publication pins three model keys although six models are
  promoted.

One intentional product change therefore produces failures across multiple
test authorities. Updating the literals again would restore green temporarily
while preserving the underlying scalability defect.

### 3.2 Duplicate and expensive work

- Full default validation runs the schema command directly and again from
  `workbook-schema-standardization.test.mjs`; the repeated invocation accounts
  for roughly one minute of the Node lane.
- Three model-specific Node contract files generate models independently even
  though `test_all_model_runtime_generation.py` and
  `verify_workbook_candidate.py` already generate and validate every discovered
  model.
- Candidate-verifier tests repeatedly build complete six-model candidates for
  cases whose actual subject is a stage mapping or failure response. The
  2026-08-09 audit measured 648.04 seconds for 16 tests, with repeated complete
  candidates costing about 61–67 seconds each.
- The default Python metadata lane was 166.55 seconds; one repeated workbook
  mutation/generation owner consumed 126.43 seconds.
- The 2026-08-10 Workbook Manager checkpoint inventory was 791.25 seconds.
  Earlier profiling showed real-workbook promotion/import/export owners near
  66–75 seconds each and changed-overlay comparison export materially slower.
- Current collection is 734 Python tests, while README still states 678. A
  manually maintained collection count is already stale.

### 3.3 Missing systematic matrices

- No single gate enumerates every promoted model x body style x trim/variant
  through runtime reconciliation and completion invariants.
- GSX, ZR1, and ZR1X depend on the composed six-model candidate lane and
  scattered targeted assertions rather than a uniform model-neutral behavior
  contract.
- Dealer-payload model scoping has explicit examples for Stingray, Grand Sport,
  and Z06 only. Generic model/variant identity propagation is not swept over
  every promoted model; live submission must remain untested.
- The current six-model seatbelt test statically sweeps many combinations, but
  still reproduces much of the product matrix in JavaScript and runs only one
  coupe/HUW behavior example per model.

## 4. Test authority classes

Every default or checkpoint gate must declare exactly one primary authority
class. A gate may supply secondary evidence, but it cannot be counted twice in
the coverage ledger.

### 4.1 Structural invariant

Structural tests do not care which particular products or values are present.
They prove rules such as:

- registered sheets and fields have valid types;
- canonical IDs and physical keys are unique;
- every reference resolves;
- model membership and variant topology are internally consistent;
- active choices resolve to valid variants, sections, and steps;
- rule and group members resolve and do not contradict their owning structure;
- exclusive groups and required selections are satisfiable;
- runtime contracts contain the required shapes and no error-severity findings;
- generation and publication respect isolated output roots and atomic
  boundaries.

Structural tests derive schema vocabulary from
`workbook_domain/registry.py`, runtime shape from `runtime_contract.py`, and
model discovery from `model_configs.py`. They must not copy workbook headers,
model-specific row counts, media URLs, or complete RPO lists.

### 4.2 Workbook-to-output parity

Parity tests compare two independent paths:

```text
expected: direct, simple read of authoritative workbook rows
actual:   generator -> runtime contract -> candidate registry/runtime
```

The expected side must not call the generator transformation under test. A
shared generator function cannot be both implementation and oracle.

Examples:

- generated model keys equal active promotion rows;
- generated variants equal workbook-declared active variant facts;
- a generated image equals the applicable active `asset_map` row;
- emitted option/rule/group/price/override identity sets equal active source
  rows after only contractually documented normalization;
- a Workbook Manager reconstruction generates the same primary runtime
  contracts as its bound source workbook.

Parity tests may compare exact values because the workbook supplies those
values at run time. They must not duplicate them as test literals.

### 4.3 Runtime state invariant

Runtime state tests exercise generic behavior over the candidate registry.
They discover cases from data, perform state transitions, and check invariants
rather than asserting one copied product matrix.

For every promoted model and declared active variant, the matrix must prove as
applicable:

1. model activation selects only that model's registry data;
2. body style and trim resolve to the intended variant;
3. reset plus reconciliation reaches a stable fixed point;
4. a second reconciliation is idempotent;
5. every selected/default/auto-added option exists and is valid in context;
6. no selected option remains disabled unless its contract explicitly marks a
   locked included/display-only state;
7. at most one peer is selected in a single-selection exclusive group;
8. required selections are either satisfied or reported by the owning section;
9. include, require, exclude, replace, default, and price rules preserve their
   generic contract after representative transitions;
10. totals equal the independently recomputed base, option, component,
    override, and charge lines exposed by the order contract;
11. model switching clears incompatible prior-model state;
12. download and stubbed dealer payload identity match the active model and
    variant.

The matrix must not make live dealer requests. Turnstile, endpoint failures,
retry behavior, and payload-shape protection remain focused, stubbed acceptance
tests under the dealer protected boundary.

### 4.4 Intentional product acceptance lock

An acceptance lock names a stable, reviewed customer or safety decision whose
change must stop validation for human review. Examples include the default
model, ZR1X standard J59/no J58, and the dealer payload/security contract.

Acceptance locks are the only normal location for product-specific literals.
Each lock must record:

- the decision it protects;
- the authoritative workbook rows or protected runtime interface;
- why generic structure/parity would not detect an unintended but valid data
  change;
- its owning test;
- the approval required to change or retire it.

One decision has one lock owner. Other tests may exercise the resulting generic
behavior but must not restate its product facts.

## 5. Validation layers

### Layer 0 — fast developer loop

Purpose: deterministic feedback after ordinary code edits.

Contract:

- pure functions, compact fixtures, schema-registry unit tests, runtime state
  helpers, and targeted UI logic only;
- no canonical-workbook generation;
- no real-workbook import/export;
- no tracked output writes;
- no network or browser dependency;
- target wall time: 30 seconds or less on the reference development machine.

Layer 0 is selected by changed surface. It is not a miniature full suite.

### Layer 1 — composed workbook-to-browser candidate

Purpose: one authoritative readiness proof for workbook, generator, generated
contract, registry, and browser runtime changes.

The existing `verify_workbook_candidate.py` remains the spine and must perform
each expensive stage once:

1. copy the selected workbook to an isolated root;
2. package validation;
3. schema validation;
4. option-sheet quality;
5. model discovery;
6. generate every discovered model once;
7. strictly validate every written contract;
8. build the complete candidate registry;
9. build the independent temporary workbook-truth snapshot;
10. run source-to-output parity assertions against the candidate contracts and
    the candidate registry;
11. run the browser harness against the candidate registry, joined by the
    generated runtime state matrix;
12. report semantic drift and protected-surface hashes.

The report must include stage durations, artifact identities, discovered and
promoted model/variant sets, skipped stages, failures, and protected-boundary
results. Initial target wall time is 5 minutes or less in CI and on the
reference machine. Timing is reported before it becomes a hard gate; a hard
budget requires at least three stable baseline runs.

### Layer 2 — changed-surface acceptance

Purpose: run focused acceptance owners only when their surface changes.

The machine-readable validation catalog maps repository surfaces to commands,
including:

- workbook write/editor and ChangeSet;
- asset/media synchronization;
- runtime JavaScript and customer interactions;
- dealer modal/payload/security;
- publication/atomic write;
- Workbook Manager projection, draft, Apply/Rebuild, recovery, and frontend;
- Fable 5 loop infrastructure;
- docs-only consistency.

Each entry declares authority class, expected inputs, side effects, isolation,
serialization requirement, approximate duration, and whether it is required in
CI, at a pass checkpoint, after a canonical workbook write, or only for its
changed surface.

### Layer 3 — checkpoint and protected-boundary acceptance

Purpose: retain expensive proof where fixture substitution would weaken a real
boundary.

This layer includes exactly one real-workbook success proof for each distinct
protected behavior, plus necessary failure-path owners:

- canonical workbook package/schema and guarded-save proof;
- complete candidate generation/publication parity;
- Workbook Manager real import/promotion, unchanged and changed comparison
  exports, generated parity, Apply/Rebuild rollback, source drift, atomic
  replacement, and scratch-copy writer proof;
- browser checks for affected customer flows and responsive layout;
- dealer submission only through stubbed/local harnesses, never a live post.

Layer 3 runs after canonical workbook writes, at implementation checkpoints,
and before release when the affected protected boundary requires it. It is not
the default inner loop.

### Layer 4 — full inventory diagnostic

Purpose: scheduled/manual detection of forgotten classification, cross-surface
interference, and baseline drift.

The full pytest and Node inventories remain available, but are diagnostic until
every owner is classified and green. A full-inventory failure is reported with
its layer and authority classification; it must not silently redefine the
release gate.

## 6. Shared fixtures and isolation

### 6.1 Candidate result

Layer 1 owns one immutable candidate result per workbook hash, code revision,
and runtime/tool version tuple. Within one process/run, generation, contract
validation, registry construction, parity, and runtime matrix all consume that
result instead of regenerating it.

Cross-run caching is out of scope initially. If later added, it must be
content-addressed, disposable, and rejected when any identity component moves.

### 6.2 Independent workbook-truth snapshot

Implement a temporary, untracked JSON snapshot built from a read-only workbook
handle and shared registry metadata. It contains only the raw/normalized fields
needed by parity checks, including:

- active model and variant facts;
- promotion rows and default selection;
- registered source rows keyed by physical identity;
- option/OVS, rule/group/member, price, override, section, interior component,
  and asset identities and values needed by current runtime contracts.

The snapshot builder may normalize Boolean/cell representation and shared
physical ownership according to existing workbook-domain contracts. It may not
reimplement generation, rule derivation, runtime cleanup, or business fallback
logic.

Node receives the snapshot and candidate registry through explicit temporary
paths. No snapshot is committed or published.

### 6.3 Candidate-verifier tests

Candidate-verifier unit tests use compact fixtures and stage injection for
error mapping, unknown input, skipped-stage, and report-schema behavior. Retain
only a small named set of complete six-model end-to-end tests:

- successful full candidate;
- failure before generation;
- generation/contract failure with later stages skipped;
- protected-surface mutation detection;
- semantic drift partitioning;
- candidate browser/runtime matrix failure.

Complete candidates are module/session scoped where isolation permits. Each
test that mutates a result clones its immutable fixture first.

### 6.4 Workbook Manager fixtures

Build one verified immutable real-workbook projection/candidate fixture per
checkpoint run, then clone it into test-local directories. Compact workbooks
and SQLite fixtures own negative validation/migration cases. Preserve one real
workbook owner for every distinct acceptance boundary listed in Layer 3; fixture
sharing must not collapse those proofs into equality checks against themselves.

## 7. Validation catalog and coverage ledger

Add one machine-readable catalog under `tests/` that records every default and
checkpoint gate. The implementation may choose JSON or a Python data module,
but it must be consumable without adding a dependency.

Minimum fields:

```text
id
command
layer
primary_authority
changed_surfaces
reads
writes
isolation
serial_group
ci_policy
checkpoint_policy
approximate_seconds
acceptance_locks
```

A catalog contract test must fail when:

- a default/checkpoint test file has no catalog entry;
- two entries claim primary ownership of the same named acceptance lock;
- a generating gate lacks an isolated output declaration;
- a protected-output gate is assigned unsafe parallel execution;
- README's published commands or layer names disagree with the catalog.

The catalog owns collection descriptions and measured counts. README may show
commands and approximate timing, but must not hand-maintain a precise pytest
collection count.

## 8. Mutation canaries

The migration is not complete merely because the rewritten tests pass the
current workbook. Temporary-copy canaries must prove that each authority class
fails and adapts for the right reasons.

Required canaries:

1. Change a valid active asset URL in a copied workbook. Structural and parity
   layers remain green when generated output follows it; no literal URL test
   fails.
2. Add one valid color-override row in a compact/copied workbook. Coverage
   expands without changing a hardcoded aggregate count.
3. Add or remove a valid promoted-model fixture row. Dynamic registry/parity
   coverage follows it; a separately declared model-membership acceptance lock
   may fail deliberately if that decision is protected.
4. Introduce an unresolved reference. Structural validation fails before
   generation/runtime proof.
5. Inject a generator defect so emitted data differs from the independent
   workbook-truth snapshot. Parity fails, proving the oracle is not circular.
6. Change a valid, non-locked product relationship in a copied workbook. Generic
   runtime cases follow the new authored relationship without stale literals.
7. Change a named acceptance-lock decision. Exactly its owning lock fails; no
   unrelated structural test restates the same product fact.
8. Force a tracked-output write from an isolated generating gate. The boundary
   guard fails and reports the exact path.

## 9. Migration checkpoints

### Checkpoint 0 — freeze and classify the live inventory

- Record Node 22 and Python 3.12 reference timings for current documented
  gates; keep the 2026-08-17 Node 26 audit as local evidence, not the CI
  baseline.
- Inventory every default/checkpoint Python and Node owner in the validation
  catalog.
- Classify each gate and each product-specific assertion under §4.
- Build a coverage ledger mapping behavior/invariant to its single primary
  owner and secondary evidence.
- Mark each gate keep, rewrite, merge, move-to-checkpoint, diagnostic-only, or
  retire-after-parity.
- Make no assertion deletion in this checkpoint.

Acceptance: every current default/checkpoint gate is classified; the six stale
assertions and all known expensive repeated setups have explicit dispositions.

#### Checkpoint 0 result — 2026-08-17 (COMPLETE)

Delivered:

- `tests/validation_catalog.json` — the machine-readable catalog. 59 gates (16
  Node files, 38 Python files, 5 script commands), 6 suites, 5 acceptance-lock
  records, 33 coverage-ledger entries, 7 stale assertions, 8 findings, and 8
  expensive repeated setups. Every gate carries all §7 fields plus its §4
  authority class, its §9 disposition with a stated reason, measured seconds,
  collected test count, and its baseline result.
- `tests/test_validation_catalog.py` — the §7 contract test. All five failure
  conditions are implemented and each is proved by a forced mutation, so none of
  them can be green for the wrong reason. Condition 4 is enforced at suite level
  as well as gate level: suite membership is derived from the command rather
  than trusted from `gate_ids`, so a whole-inventory command cannot be declared
  parallel-safe by leaving its membership empty. File discovery is recursive,
  and a generating gate may not declare `read_only` or `in_process` isolation.
  19 tests, 0.04 s.
- `README.md` — one ownership correction. The hand-maintained pytest collection
  count (678, measured 734) is removed and the catalog is named as the owner;
  the contract test fails if a count returns.

Measured baseline (local Node 26.7.0 / Python 3.14.7 on darwin arm64, serial;
one process per file except where noted). Raw output:
`docs/superpowers/specs/2026-08-17-fast-layered-validation-suite-checkpoint-0-baseline.md`.

| Lane | Wall time | Tests | Result |
|---|---|---|---|
| 14 documented Node readiness gates | 109.27 s | 298 | 292 pass, 6 fail in 5 files |
| All 16 Node files | 111.75 s | 305 | 298 pass, 7 fail in 6 files |
| Python metadata gate, as README publishes it | 176.60 s | 189 + 111 subtests | green |
| Workbook Manager checkpoint (9 files) | 1,123.47 s | — | green (2 skips) |
| Full Python inventory (37 files) | 2,381.46 s | 734 collected | 3 files fail alone |

The 14-gate lane reproduces §3.1 exactly: 298 tests, 292 passed, 6 failed across
5 files, slowest gate `workbook-schema-standardization`, next
`stingray-runtime-contract`.

Reference-timing gap (OPEN): Node 22 and Python 3.12 — the CI versions in
`.github/workflows/release-candidate.yml` — are not installed on the reference
machine (available: Node 23/24/25/26, Python 3.13/3.14). Every number above is
local evidence and is explicitly not the CI baseline this checkpoint asked for.
Closing it needs a CI run or an approved toolchain install; the catalog records
the gap in `baseline.ci_reference_status`.

Cost concentration measured:

- `workbook-schema-standardization` is 64.97 s, 59.5% of the Node readiness
  lane, and it re-invokes the schema command full validation already runs.
- `test_workbook_manager` (810.34 s), `test_verify_workbook_candidate`
  (694.43 s) and `test_workbook_manager_import_projection` (222.91 s) are 74.5%
  of the full Python inventory.
- The §3.2 "repeated workbook mutation/generation owner" is identified:
  `tests/test_model_config_metadata.py`, 150.33 s, 83.9% of the metadata lane.
- Two owners the specification's evidence never named:
  `test_editor_server_write_api.py` at 220.06 s for 4 tests, and
  `test_editor_ops_apply.py` at 147.75 s.

Findings beyond the documented six stale assertions — five new defects and
three stale open-failure entries proved resolved. The catalog records all eight
in `new_findings`:

1. `grand-sport-contract-preview.test.mjs:94` — stale hot-spot count (22 vs 25)
   in an optional diagnostic the fourteen-gate audit never ran.
2. `test_runtime_metadata_guards.py:303` — a hardcoded three-row
   default-selection list over a hardcoded three-model tuple; the workbook now
   has a fourth valid row. Same defect class as the documented six, on the
   Python side the audit did not cover.
3. **The candidate lane's `semantic_drift` stage has no live positive proof.**
   Its two forcing tests perturb the ZR1 `EFR` option name and expect drift in
   `choices` and `standardEquipment`; both measured empty. `zr1_options`
   `opt_efr_001` is `active=True, selectable=False`, yet appears in neither of
   the 800 choices nor the 318 standardEquipment rows of the retained ZR1
   contract, so the mutation cannot drift anything. Why an active option row
   emits nothing is a workbook/generator question this checkpoint is not
   authorized to answer (§12); it is classified, not decided.
4. `test_rule_derivation.py`, `test_source_assembly_characterization.py` and
   `test_options_sheet_quality.py` only pass with `PYTHONPATH=scripts` or beside
   their siblings. Layer 0 selects gates individually, so this must be fixed
   before those files can be selected alone.
5. Review of the first implementation found the catalog's own condition 4
   vacuous at suite level: `suite.full_python_inventory` declared no members and
   `serial_required: false` while `pytest tests/` collects
   `test_verify_workbook_candidate`, which hashes the protected roots. Fixed
   here — the same "a check only observed passing is not a check" failure mode
   the catalog exists to prevent, found in the catalog's enforcement.
6. Three failures `STATE.md` still carries as open are resolved:
   `test_editor_lints.py` (27 passed, 0 failed, against four recorded on
   2026-07-26), `test_workbook_manager_generated_parity.py` (4 passed, against
   the hardcoded three-model tuple recorded on 2026-08-14), and the
   `sec_perf_support_001` pins plus tracked-artifact churn recorded against
   `grand-sport-contract-preview.test.mjs` on 2026-07-25.

Also confirmed from the catalog, not new but now measured: the fourteen-gate
Node lane spends 59.5% of its time re-running a schema command that full default
validation already runs.

No assertion was deleted, no expectation was refreshed to match current output,
and no acceptance lock was created. The catalog records
`promoted_model_membership` as **proposed**: turning it into a lock would freeze
a business decision and needs §12 approval first.

Also recorded: three files assert `defaultModelKey === "stingray"`, which
violates the §4.4 one-decision-one-owner rule. The catalog names
`multi-model-runtime-switching` as the owner and the other two as restatements
to remove in Checkpoint 1/2.

### Checkpoint 1 — restore truth without refreshing literals

- Rewrite the six current stale assertions as structural, source-parity, or one
  intentional acceptance lock.
- Do not replace old counts, URLs, or model lists with new literals.
- Remove the duplicate schema invocation from the Node readiness path while
  retaining one schema authority.
- Update the catalog and README ownership descriptions.

Acceptance: the current default Node inventory is green, the mutation canaries
for asset URL, override count, and registry membership pass, and protected
tracked artifacts remain byte-identical.

#### Checkpoint 1 result — 2026-08-17 (COMPLETE)

All six documented stale assertions, both new stale owners from the Checkpoint 0
baseline, the duplicate schema invocation, and the three import-order-dependent
files are closed. No literal was refreshed: not one old count, URL, or model list
was replaced by its current value.

| Stale owner | Replacement |
|---|---|
| `grand-sport-runtime-contract` `colorOverrides.length === 263` | identity-set comparison against the resolvable rows of the model's registered `color_overrides` sheet, plus `override_id` uniqueness |
| `grand-sport-runtime-contract` J6F PNG URL | sweep comparing every option's seven image fields against its applicable active `asset_map` row, wildcard/exact precedence resolved on the expected side |
| `stingray-form-regression` included-seatbelt lock (2 assertions) | runtime sweep whose cases, blocked peers, and added RPOs are read from the model's registered rule-mapping and colour-override sheets, with registry-vs-workbook parity asserted before the runtime is driven |
| `z06-runtime-contract` "included colour or Black" | parity between emitted interior-sourced `includes` / interior-conditioned price rules and the model's registered rule-mapping and price-rule sheets |
| `z06-runtime-rule-corrections` included-seatbelt block (2 assertions) | the same sweep, over the same workbook-read expected sets |
| `z06-registry-publication` three model keys | comparison against the active promoted rows of `model_registry_promotion`, ordered by `display_order` |
| `test_runtime_metadata_guards.py:303` three-row/three-model literal | loader output for every workbook-active model against a direct openpyxl read of the same sheet |
| dead `semantic_drift` canaries | probe selected from the retained ZR1 contract itself; raises if no option reaches both collections |

Two 22-row interior/seatbelt tables — parallel copies of workbook data in
JavaScript — were deleted with the assertions that read them.

Also delivered:

- The duplicate schema invocation is gone from the Node readiness path.
  `workbook-schema-standardization` measures **0.91 s against 64.97 s**, and the
  fourteen-gate readiness lane **52.63 s against 109.27 s**. `cmd.workbook_schema`
  is the single schema authority, named as such in README and reachable from the
  Node matrix section; no structural sweep was dropped.
- `tests/conftest.py` owns the `scripts/` path insertion for the whole test
  directory. With `PYTHONPATH` unset and run alone: `test_rule_derivation` 15
  passed, `test_source_assembly_characterization` 32 passed,
  `test_options_sheet_quality` 18 passed. Layer 0 can now select them.
- `tests/lib/workbook-rows.mjs` — the independent §4.2 expected side for Node
  parity gates: openpyxl only, no generator import, memoized per sheet.
  `tests/lib/interior-relationships.mjs` builds the interior/option include,
  exclude, and colour-override sets on top of it, so the two runtime sweeps state
  what must be true independently of the payload they exercise. Checkpoint 2
  replaces both with the persistent workbook-truth snapshot.
- Both restatements of `default_model_is_stingray` are removed;
  `multi-model-runtime-switching` is its single asserting owner.

Acceptance evidence (local Node 26.7.0 / Python 3.14.7, serial):

| Lane | Result |
|---|---|
| 14 documented Node readiness gates | all pass — 298 collected tests, 52.63 s |
| All 16 Node files | 305 collected tests, 55.44 s; only `grand-sport-contract-preview` fails, on the Checkpoint 2 hot-spot literal it already owned |
| `test_runtime_metadata_guards.py` | 11 passed, 0.25 s |
| `test_verify_workbook_candidate.py` | see the Checkpoint 1 evidence file |
| `test_validation_catalog.py` | 19 passed |
| Protected tracked artifacts | unchanged (`git status -- form-output form-app` clean) |

Mutation canaries, all run in a throwaway `git worktree` against copies — the
canonical workbook and the working tree were never mutated:

1. §8.1 valid active asset URL change → parity layers green, no literal URL test
   fails.
2. §8.2 one valid new colour-override row → emitted overrides 281 → 282, gate
   green. The retired `=== 263` literal would have failed both before and after.
3. §8.3 promoted-model membership change → before republication the publication
   parity test follows the workbook (5 models) while the tracked-registry
   comparison correctly fails as stale; after republishing, both parity gates
   follow the change and `multi-model-runtime-switching` fails 8 of 70 on its
   de-facto membership pin.
4. §8.5 injected generator defects → dropping `image_alt`, dropping one
   resolvable override row, and dropping one interior-sourced `includes` row each
   fail exactly their own new parity assertion.
5. Forced failure of the new runtime sweeps (suppressing the seat-belt disable
   reason in `app.js`) and of the rewritten metadata guard (loader drops one row
   per model) → both fail as intended.
6. Omission canaries added after PR review → dropping one interior-targeted
   `excludes` row, and dropping one resolvable colour-override row, each fail the
   registry-vs-workbook parity assertion in both runtime sweeps. Neither would
   have failed the first version of those sweeps, which derived their expected
   relationships from the payload they exercised; that is the defect review
   caught and these two canaries are the proof it is closed.

Canaries 4, 6 and 8 belong to later checkpoints and were not run.

Carried forward, unchanged by this checkpoint:

- `promoted_model_membership` stays **proposed**. Checkpoint 1 took the parity
  route, which needs no approval; declaring the lock still freezes a business
  decision and needs §12 approval.
- Why active `zr1_options.opt_efr_001` emits nothing is still **unanswered**. The
  canary no longer depends on it, but the workbook/generator question is a §12
  classification, not a test decision.
- Node 22 / Python 3.12 CI reference timings are still **uncaptured**.
- `grand-sport-contract-preview.test.mjs:94` (hot-spot count 22 vs 25) is still
  open, per its recorded Checkpoint 2 disposition. It is a Layer 4 diagnostic,
  not a readiness gate, and is the only failing Node file.

### Checkpoint 2 — build independent truth and composed parity

- Implement the temporary workbook-truth snapshot.
- Add source-to-contract and source-to-registry parity owners.
- Route existing model-specific literal assertions to the parity owner or the
  explicit acceptance-lock inventory.
- Prove oracle independence with injected mismatch tests.

Acceptance: every runtime collection with a workbook source has a documented
parity disposition; no default structural/parity gate embeds complete business
rows or mutable asset URLs.

#### Checkpoint 2 result — 2026-08-17 (COMPLETE)

**The snapshot.** `scripts/build_workbook_truth.py` builds the §6.2 document
from a read-only openpyxl handle plus `workbook_domain/registry` metadata:
registered sheets and their family key columns, model topology, promotion rows
and default selection, and `asset_map` addressing with wildcard/exact precedence
resolved. 73 sheets, 0.9 seconds, written to an explicit temporary path and
never committed.

Two properties make it usable as an oracle, and `tests/test_workbook_truth.py`
(58 tests) asserts both rather than asserting that it produces rows:

- **Independence.** A freshly launched interpreter that builds a snapshot loads
  no generation module. Checked in a subprocess, because this process is
  already polluted by sibling imports — and with a mutation proving the check
  can fail. The two cell helpers are implemented locally rather than imported
  from `corvette_form_generator.workbook`, so one representation bug cannot make
  every parity gate blind at once.
- **Agreement.** Those same two helpers are pinned to `workbook.clean` and
  `workbook.workbook_truthy` over a 22-value table. Independent must not quietly
  mean different.

Every other claim has a forced mutation behind it: dropping a registration row
narrows the snapshot, a second `default_model` row is reported rather than
resolved, duplicate `asset_map` rows are reported as conflicts rather than
adjudicated, and a registration pointing at a missing sheet is surfaced.

**The parity owners.** Two new gates, both model-neutral — the model list,
source sheets, and contract paths all come from the workbook, so promoting a
seventh model widens them with no edit:

| Gate | Proves |
|---|---|
| `source-to-contract-parity` (102 tests, 1.09 s) | variants, steps, sections, choices, standard equipment, rules, rule groups, exclusive groups, price rules, default selections, interiors, colour overrides, order summary, option media, and dataset binding, for every promoted model |
| `source-to-registry-parity` (29 tests, 1.16 s) | membership, declared order, default model, labels, slugs, composed model name, setup copy, card media, legacy aliases, and that each published payload is exactly the contract its promotion row names |

Every relationship was measured against all six promoted models, in both
directions, before it was written. Where the workbook has a suppressor it is
named from workbook columns; what is deliberately not reimplemented is
generation. Two rules are stated as transforms rather than compared loosely:
trim level is upper-cased (`inspection.py:651`), and `standardEquipment` is
exactly the emitted choices marked standard.

**The lane.** `verify_workbook_candidate.py` grew stages 9 and 10,
`workbook_truth` and `source_parity`. The snapshot is built from the
**candidate** workbook and both gates run against the candidate contracts and
candidate registry through explicit temporary paths, so Layer 1 pays the build
once and proves the candidate rather than the retained artifacts. Full lane:
`ok: true`, twelve stages run, `unexpected_drift: []`, no boundary violation.

**Literals routed.**

| Owner | Was | Now |
|---|---|---|
| `grand-sport-contract-preview` | 9 aggregate counts, one of them the recorded stale `requires: 25` | membership from the snapshot; hot-spot counts recomputed from the rows they summarize; every bucketed row traced to an active source row |
| `workbook-visual-copy-standardization` | `OPTION_SHEETS` hardcoded to three sheets | derived from each model's own registration — the generic sweeps now cover six models; named decisions discover their scope with `sheetsCarrying` |
| same file, R-6 seats and roof labels | per-model option ids and absolute `display_order` | keyed by RPO with a relative-order rule, which covers six models instead of three and still fails on a reorder, rename, addition, or removal |
| `nonruntime-option-source-purge` | 57 deleted ids, 21 deferred ids, per-model component RPO lists | four source-hygiene rules over every active model; the "deferred rows remain" half moved to `source-to-contract-parity` |
| `z06-runtime-contract` | six variant ids, an eight-section standard set, two order-summary counts | `model_variants`, `section_presentation.standard_equipment_bucket`, and membership comparisons |
| `tests/lib/workbook-rows.mjs` | the interim per-sheet reader | retired; its four callers read the snapshot |

Rewriting the preview counts found four more stale literals than the catalog
recorded: `not_available` 46 against 52, `includes` 41 against 40,
`special_package_review` 27 against 25, and two buckets the current workbook
produces none of. The fourteen-gate readiness lane never ran the diagnostics, so
none of them was visible.

**Oracle independence proved by injected mismatch (§8 canary 5).** Thirteen
canaries in a throwaway `git worktree`; the canonical workbook, the working
tree, and the tracked artifacts were never mutated. The bar was not "something
fails" but "its own assertion fails and no unrelated one does" — a parity suite
where one defect fails six tests localizes nothing.

- Six injected generator defects — a corrupted choice label, a silently dropped
  choice, a dropped authored rule, a dropped price rule, a dropped colour
  override, a dropped variant — each failed exactly one assertion, its own.
- Three registry defects — a payload no longer equal to its promoted contract, a
  missing promoted model, a reordered registry — each failed exactly the
  assertion that owns it.
- De-promoting a model in a workbook copy moved the **expected** side: the
  snapshot promoted five models and the unchanged six-model registry was
  reported as carrying an unpromoted model. The oracle follows the workbook,
  not the artifact.
- §8 canary 1 was re-run against the widened media sweep: the stale artifact
  fails, and after regeneration all 102 assertions are green with no literal URL
  anywhere to fail.

**Acceptance evidence** (local Node 26.7.0 / Python 3.14.7, serial):

| Lane | Result |
|---|---|
| 16 node readiness gates (14 documented + 2 parity owners) | all pass, 54.88 s |
| All 18 node files | 437 tests, all pass, 60.0 s — against 16 files / 305 tests / 111.75 s and six failures at the Checkpoint 0 baseline |
| `test_workbook_truth.py` | 58 passed, 7.93 s |
| `test_validation_catalog.py` | 19 passed |
| Composed candidate lane, all six models | `ok: true`, 12 stages, no unexpected drift, no boundary violation |
| Protected tracked artifacts | unchanged |

`node --test tests/*.test.mjs` — the concurrent form — failed
`z06-contract-preview` while every file passed alone. That is the collision the
catalog's `serial_group` exists to prevent, and it is why the inventory command
is the serial loop.

**One carried question answered, with evidence.** Why active
`zr1_options.opt_efr_001` emits nothing is no longer open, and it is not a
defect. The row carries `display_behavior='hidden'`;
`inspection.display_behavior_status` (`inspection.py:223`) maps `hidden` to
status `unavailable`, and `inspection.py:777` drops any choice whose resolved
status is neither `available` nor `standard`. It emits nothing because the
workbook authored it hidden. Measured across all six models: with `hidden` named
as a suppressor, emitted choices equal the emittable OVS rows exactly — zero
unexplained drops, zero unexplained keeps. ZR1 is the only model with an active
hidden row. No product decision was made in test code; the suppressor is a
documented term of the parity rule.

**One new finding, left for a workbook-owned cleanup.**
`section_presentation` has two active rows scoping Grand Sport sections
(`sec_gsha_001`, `sec_gsce_001`) to Stingray, which emits neither. Deleting them
is a workbook write §11 does not authorize, so the gate asserts the general rule
instead: an orphaned presentation row may exist, but it may not carry
`step_key`, `display_label`, `display_behavior`, or any bucket value — that
would be a section the workbook expects to present and the contract does not
have.

**Carried forward, unchanged by this checkpoint:**

- `promoted_model_membership` stays **proposed**. Checkpoint 2 took the parity
  route again, which needs no approval; declaring the lock still freezes a
  business decision and needs §12 approval. The literal in
  `multi-model-runtime-switching` remains the de-facto pin.
- Node 22 / Python 3.12 CI reference timings are still **uncaptured**.
- `grand-sport-runtime-contract`'s Checkpoint 1 asset and colour-override parity
  tests are now also covered model-neutrally. The duplication is deliberate
  until the `retire_after_parity` pass in Checkpoint 4.
- `stingray-runtime-contract` keeps its own private workbook reader. It is on
  the Checkpoint 4 retirement path and was left alone rather than migrated
  mid-checkpoint.

#### Checkpoint 2 review response — 2026-08-18

Pull request review of #28 found one defect that would have made Layer 1 reject
a correct candidate, plus four narrower problems. All are fixed on the same
branch; the parity owners' shape is unchanged.

**Blocking: inactive variant overrides shaped the expected side.**
`variant_overrides` carries an `active` column and
`runtime_metadata.load_variant_option_overrides` reads the sheet through
`active_rows`, so a deactivated override restates nothing. The parity owner
indexed every override row, then used that map for section membership, `hidden`
suppression, and authored status. Deactivating an override — an ordinary
authoring edit — would have left the gate resolving through a dead row and
failing correct output. That is a false red on the composed readiness lane,
which is the failure class this checkpoint exists to remove.

Three changes, together:

- The override index filters on `active`.
- Emitted-section membership is derived from the resolved section of the
  emittable source rows plus the two synthesized context sections, matching
  `inspection.py`'s `section_ids_with_choices`. It previously unioned every
  active option row's section with every override's section, which could
  conjure a section no emitted choice uses. The emittable set is now stated once
  from workbook columns and is no longer filtered by the contract's own emitted
  sections — the expected side may not read the actual side.
- Each emitted choice's `section_id` is compared to the section its source row
  resolves to. Membership alone cannot see a choice landing in the wrong section
  while both sections stay populated by other rows, which is exactly what a
  mis-resolved override looks like.

`tests/test_source_parity_canaries.py` is the forced mutation behind it:
deactivate one override on a workbook copy, regenerate that model into a
temporary root, assert `source-to-contract-parity` still passes — and assert
first that the edit is observable in generated output, so the canary cannot pass
vacuously. Verified to fail (`sec_inte_001` where the dead override said
`sec_2lte_001`) with the `active` filter removed. Every override row in the
tracked workbook is currently active, so a green parity run could not have ruled
this out on its own. 3.5 s.

**Four narrower fixes.**

- *One truthiness convention.* Seventeen assertions re-checked snapshot rows
  with `active === "True"` while the snapshot's own `workbookTruthy` accepts
  `true|yes|1|y`; `workbook-visual-copy-standardization` had a third, wider
  spelling with a dead `=== true` arm. All snapshot-row checks now call
  `workbookTruthy`, including `z06-runtime-contract`'s
  `standard_equipment_bucket` filter, where the non-empty string `"False"` read
  as true. Assertions about values in *generated* artifacts keep the literal:
  that is the emitted representation, not the authored one.
- *Representation independence is now asserted.* The subprocess boundary test
  cannot see this failure: `corvette_form_generator.workbook` is loaded in
  process regardless, because the shared `workbook_domain.registry` metadata
  imports it. Re-exporting `workbook.clean` or `workbook.workbook_truthy` from
  the snapshot builder would leave every parity gate reading cells through the
  same code generation reads them through, and one representation bug would
  blind all of them while every test stayed green. The agreement table keeps the
  two definitions equal; two new assertions keep them two.
- *Promotion topology no longer resolves silently.* `model_registry_promotion`
  by `model_key` and `variant_master` by `variant_id` were indexed
  last-write-wins. A duplicate row is as unadjudicable as a duplicate
  `asset_map` row, so it is now reported in `topologyConflicts` and asserted
  empty by the parity gate, with a forced mutation behind it.
- *`variant_overrides` has no `status` column.* The writable contract is
  `option_id, variant_id, selectable, display_behavior, section_id, active,
  note`, and the loader hardcodes an empty status. The parity gate no longer
  lets an override win the authored-status comparison, and the `resolved()`
  contract names the three columns an override may actually restate.

**Left deliberately, with reasons.**

- **First residual risk.** `rules.py` drops an authored `requires` already
  expressed by a `requires_any` group, and parity expects every resolvable
  `rule_mapping` id. This holds on today's workbook — 59 authored `requires`
  rows, 8 active `requires_any` groups, no overlap that `rules.py` currently
  suppresses — so it is latent, not live. It goes live the moment an authoring
  pass starts collapsing `requires` rows into `requires_any` groups: the first
  collapsed pair makes `source-to-contract-parity` reject a correct candidate.
  Naming the suppressor or accepting grouped-requires as derived is a rule
  decision, not a test edit, and is the first thing to settle when such a pass
  is scheduled.
- `standardEquipment` parity was renamed, not re-derived. Both sides come from
  the artifact under test, so it is a contract-internal invariant; a generator
  that mis-derived status into both collections would stay green. Authored
  status is covered separately on the rows where the workbook states it.
  Driving expected membership from OVS instead would duplicate the status
  derivation this gate deliberately does not reimplement.
- The Grand Sport preview hot-spot counts recompute from `hotSpots.rows`, which
  catches a counter disagreeing with its own list but not a classifier moving
  rows between buckets — what the retired `requires: 25` literal incidentally
  detected. Restoring source-side classifier coverage needs a decision about
  whether that diagnostic still owns classifier behavior; Checkpoint 4 owns the
  diagnostics.
- `test_model_topology_matches_the_workbook_metadata_rows` requires every active
  membership to be declared and active in `variant_master`. The snapshot already
  records `declared_in_variant_master` / `active_in_variant_master`, so a
  dangling membership could be a gate finding instead of an oracle invariant.
  Left as-is; it is the same §12 territory as `promoted_model_membership`.
- `workbook-truth.mjs`'s `cell()` does not mirror Python `clean()` on booleans
  (`"true"` vs `"True"`). Snapshot rows arrive pre-cleaned, so this is only
  reachable if a generated boolean is passed through it.
- `stingray-form-regression` keeps its private per-sheet reader and now imports
  only `workbookTruthy` from the snapshot module. Migrating the reader is on the
  Checkpoint 4 path.

### Checkpoint 3 — generate the runtime state matrix

- Parameterize candidate runtime checks over every promoted model and declared
  variant.
- Implement the §4.3 invariants and bounded representative transitions.
- Keep focused dealer security/error tests; add generic model/variant payload
  identity coverage without live submission.
- Replace duplicated model-specific generic behavior tests only after the
  matrix demonstrates equivalent or stronger failure detection.

Acceptance: all promoted models and active variants appear in the report; each
state invariant has a forced-failure test; model switching and payload identity
are covered uniformly.

#### Checkpoint 3 result — 2026-08-18 (COMPLETE)

The generated runtime state matrix is `tests/runtime-state-matrix.test.mjs`,
backed by `tests/lib/runtime-state-matrix.mjs` and the shared harness in
`tests/lib/runtime-harness.mjs`. Cases come from the §6.2 workbook-truth
snapshot, not from the payload under test: six promoted models, 32 declared
active variants. Each variant is activated, reset, reconciled, and checked
against the twelve §4.3 invariants. One representative transition sequence per
model covers include / exclude / replace / require / exclusive-group swap /
priced-line behavior. Model switching is swept over every adjacent promoted
pair. Download and stubbed dealer payload identity are checked for every
variant; no live dealer request is made.

Each invariant has a forced-failure test. 27 collected tests, 27 passed in
2.67 s against the published registry. The candidate lane's `browser_harness`
stage now runs the matrix beside `multi-model-runtime-switching` through the
same `CORVETTE_FORM_DATA_JS` override.

Named model-specific generic tests were **not** retired. Spec Checkpoint 3
says they move only after the matrix demonstrates equivalent or stronger
failure detection; that retirement canary belongs to Checkpoint 4.

Raw output: `docs/superpowers/specs/2026-08-17-fast-layered-validation-suite-checkpoint-3-evidence.md`.

Carried forward, unchanged by this checkpoint:

- `promoted_model_membership` stays **proposed**. The literal in
  `multi-model-runtime-switching` remains the de-facto pin.
- `section_presentation` still carries two inert Stingray-scoped Grand Sport
  rows. Deleting them is a workbook write no specification authorizes.
- Node 22 / Python 3.12 CI reference timings remain uncaptured.

### Checkpoint 4 — consolidate the candidate and Python lanes

- Make the composed candidate the single expensive workbook-to-browser lane.
- Share one generated candidate within the run.
- Convert candidate report/stage tests to compact fixtures where end-to-end
  generation is not their subject.
- Refactor the metadata mutation hotspot to use compact workbooks or a shared
  base while retaining representative real-workbook mutation proof.
- Remove model-specific regeneration from default Node gates once equivalent
  candidate coverage is proven.

Acceptance: no default layer pays the same schema, model generation, or
candidate-registry cost twice; retained end-to-end owners still fail when their
protected stage is broken.

#### Checkpoint 4 result — 2026-08-19 (COMPLETE)

The composed candidate is now the single default expensive
workbook-to-browser lane. Four default Node files
(`stingray-runtime-contract`, `grand-sport-runtime-contract`,
`z06-runtime-contract`, and `z06-interior-accessory-cleanup`) no longer spawn
private `generate_form.py` runs; they retain focused contract/product assertions
against tracked contracts. Fresh all-model generation, strict validation,
workbook-truth parity, candidate registry publication, and runtime/browser proof
remain joined in `verify_workbook_candidate.py`. Only the two optional Layer 4
preview diagnostics still generate models independently.

The default Python metadata suite no longer includes the separate
`test_all_model_runtime_generation.py` real-workbook CLI/summary proof. That file
remains green as a Layer 3 workbook-write/checkpoint owner. The metadata mutation
hotspot now runs its 84 runtime-step mutations through the owning
`load_runtime_steps()` function on one in-memory workbook, while representative
promoted and unpromoted real-generation failures remain. The focused file fell
from 118.48 s to 14.97 s; the complete default metadata lane is 159 tests plus
111 subtests in 35.0 s.

Candidate verifier tests share the three complete runs the file genuinely needs:
the canonical workbook with nothing declared changed (including the candidate
browser harness), and one controlled-drift workbook read once undeclared and
once declared. Stage order, report schema, all-model marker behavior,
temporary-registry browser proof, and protected-boundary tests reuse those runs
or stop on compact early-stage failures. The file fell from the inherited
684.74 s to 457.54 s while retaining successful complete-candidate,
pre-generation failure, controlled drift, declared-drift suppression,
protected-write, and browser/runtime-matrix owners.

Review correction. The first version of this consolidation shared a canonical
run declaring `*` and measured 389.07 s over 16 tests. Because `unexpected_drift`
is "drifted AND not declared", declaring every model made that set unreachable,
which silently voided the stale-retained-artifact proof, voided the
generation-filter proof, and — with one test deleted — left declared-drift
suppression unproven. The canonical fixture now declares nothing, the deleted
test is restored on a third full run, and the `*` marker keeps a direct unit
proof over `declared_changed_set`. This matters at this checkpoint specifically,
because Checkpoint 4 is what makes four default Node gates read retained
artifacts rather than regenerate them.

The catalog contract also gained
`test_no_output_isolation_kinds_declare_no_writes`. Every other isolation
assertion branches on `generates`, so gates declaring `generates: false` escaped
all of them; `node.stingray-runtime-contract`,
`node.grand-sport-runtime-contract`, and `node.z06-runtime-contract` are
corrected from `read_only` to `temp_workbook_copy` / `tmp_path_fixture` with
their real temporary writes declared.

Closing results: the seventeen-file default Node lane passed in 51.34 s (52 s on
the review re-run); the Python metadata lane passed 159 tests plus 111 subtests
in 35.0 s (36.99 s on the review re-run); the Layer 3 all-model CLI owner passed
30 tests in 6.19 s; the candidate verifier passed 17 tests in 457.54 s; the
catalog contract passed 20 tests; `git diff --check` passed. Raw output and
disposition details:
`docs/superpowers/specs/2026-08-17-fast-layered-validation-suite-checkpoint-4-evidence.md`.

No workbook, generated artifact, published registry, runtime implementation,
dealer boundary, deployment path, dependency, or schema changed. Checkpoint 5
remains the next authorized slice. The proposed promoted-model membership lock,
two inert `section_presentation` rows, and Node 22 / Python 3.12 reference
timings remain open and unchanged.

### Checkpoint 5 — optimize Workbook Manager checkpoint fixtures

- Implement the immutable verified projection/candidate fixture and safe clones.
- Move negative cases to compact fixtures.
- Retain the distinct real-workbook acceptance boundaries from §5 Layer 3.
- Measure isolated, combined, and order-sensitive runs to prevent shared-module
  or mutable-fixture contamination.

Acceptance: Manager fast tests are suitable for Layer 0/2 selection; checkpoint
runtime materially improves from the 791.25-second baseline without removing a
distinct protected-boundary proof.

#### Checkpoint 5 result — 2026-08-20 (COMPLETE)

`tests/workbook_manager_fixtures.py` now owns one process-wide, lazily built,
verified real-workbook projection/candidate. Consumers receive byte copies of
the workbook, projection, or lazy unchanged comparison export, and the helper
hash-checks every shared source after use. Missing-identifier,
unresolved-reference, and missing-required-sheet cases now use compact
self-contained workbooks that do not read the canonical workbook. The six-test
Layer 0 helper contract passed in 0.28 s.

The retained Layer 3 owners remain distinct: verified promotion and complete
row dispositions, atomic replacement, source-identity drift, changed and
unchanged comparison exports, generated-contract parity, Apply/Rebuild, and the
opt-in scratch-copy writer. API integration tests now consume verified clones
or compact service artifacts where the real workbook boundary is already owned
elsewhere; they still prove route binding and durable lifecycle behavior.

Measured on local Node 26.7.0 / Python 3.14.7, serial:

| Run | Result |
|---|---|
| Fixture contract alone | 6 passed, 0.28 s |
| `test_workbook_manager.py` | 63 passed, 2 skipped, 574.26 s (catalog baseline 810.34 s) |
| Manager checkpoint, documented order | 230 passed, 2 skipped, 36 subtests, 745.31 s |
| Manager checkpoint, reverse order | 230 passed, 2 skipped, 36 subtests, 742.62 s |
| Catalog + fixture closeout | 26 passed, 0.26 s |

Measurement correction recorded during Checkpoint 6. The 791.25-second
2026-08-10 baseline and the 745.31-second Checkpoint 5 run are not directly
comparable per-gate measurements. The later run shares one process-wide verified
projection/candidate; isolated `test_workbook_manager_generated_parity.py` now
pays that full setup and measures 147.68 s, while the setup is already warm when
that file runs inside the checkpoint. Its former 82.22-second isolated result is
therefore only the best available estimate of incremental parity work, not a
post-change in-suite measurement. For every gate in catalog serial group
`workbook_manager`, `approximate_seconds` is a standalone observation and is
non-additive: scheduling and budget logic must use the suite measurement and run
the group in one process, never sum member values. The observed isolated deltas
(`test_workbook_manager` -236.08 s, import/projection -17.66 s, generated parity
+65.46 s, fixture contract +0.28 s) net to -188.00 s, while the two suite totals
differ by only -45.94 s. Roughly 142.06 s is unattributed because the baseline
and closing runs did not capture comparable per-file stage timings. Checkpoint 6
does not re-time the full Manager checkpoint; the catalog records the shared
setup and this comparison gap instead of attributing it speculatively.

The reverse-order run initially exposed two generated-parity mocks patching a
stale module object after `TestApi` deliberately reloaded the `app` package.
Both now patch the imported functions' actual globals; the focused canary passed
2 tests and the complete reverse-order run passed. The closing checkpoint run is
45.94 s shorter than the earlier 791.25-second run, but that difference is not
claimed as an attributable performance improvement because the measurements are
not comparable as described above. All named Layer 3 boundaries remain. The
existing FastAPI/Starlette deprecation warning remains; no dependency change is
authorized by this checkpoint.

No canonical workbook, generated artifact, published registry, runtime
implementation, dealer boundary, deployment path, dependency, or schema
changed.

### Checkpoint 6 — CI, documentation, and retirement

- Wire CI to the cataloged layers: Layer 0 plus Layer 1 on every PR, affected
  Layer 2 gates by changed surface or explicit conservative fallback, and Layer
  3 when a protected boundary requires it.
- Run all generating/protected-output gates serially unless their roots are
  proven disjoint.
- Upload the stage-timed report.
- Update README and Workbook Manager guidance from the catalog.
- Retire obsolete test files/helpers only after the coverage ledger shows their
  primary protections moved and mutation canaries prove the replacement.
- Run the full inventory as the final diagnostic and classify every remaining
  failure.

Acceptance: required CI proves the documented release path; local and CI
commands agree; no stale gate remains silently outside the catalog; all retired
owners have explicit replacement evidence.

#### Checkpoint 6 result — 2026-08-20 (COMPLETE, corrected 2026-08-20)

CI now runs `scripts/run_layered_validation.py`, which reads commands and
changed-surface ownership from `tests/validation_catalog.json`. Layer 0 oracle,
catalog, and runner contracts plus the composed Layer 1 candidate run on every
pull request. Directly changed cataloged tests select their owners, cataloged
Layer 0–3 owners join for changed surfaces, and Layer 4 remains diagnostic-only;
unclassified paths take a conservative validation/generator fallback. Selecting one
`workbook_manager` member co-selects and executes its entire serial group in one
pytest process. The original Checkpoint 6 commit had co-selected those gates but
still launched each as a separate process, defeating the shared fixture; it also
omitted changed-surface Layer 0 gates. The corrected runner selects affected
Layer 0–3 gates, collapses shared groups to a cataloged suite command, and
orders execution by layer. CI now fetches complete history, includes deleted
paths in classification, transports changed paths without shell word-splitting,
and allows 30 minutes for the measured Layer 1 plus changed-surface work. The
uploaded report records selected files, surfaces, gates, stage durations,
outputs, exit statuses, and the overall result. Local and CI use the same runner.

The final review correction makes ownership automatic rather than adding broad
exceptions. `requirements-test.txt` composes the minimal workbook, pytest, and
Workbook Manager backend environments for local and CI use. The first exact-head
CI run exposed Node gates invoking the documented `.venv/bin/python` path while
the workflow had installed into the hosted interpreter; CI now creates the same
repo-local virtual environment and runs installation plus the runner through it. Narrow
asset/editor/write-path mappings accumulate with generic `scripts/` ownership.
Every executable cataloged `test_files` path resolves back to its owning gate,
with mutation proof. A `form-app/` path selects the focused Layer 1 dealer and
runtime owners. A Workbook Manager frontend path selects the shared Manager
group plus the lockfile-driven production build; browser UX proof remains manual
until a browser-test dependency is separately approved. The next authorized
work is Workbook Manager UX Recovery Checkpoint 1; it is not part of this pass.

The Checkpoint 5 correction is recorded above and in catalog `serial_groups`.
Shared-build cost and non-additive timing are explicit, isolated parity cost is
distinct from its estimated shared-fixture increment, and the arithmetic gap is
quantified. No full Manager checkpoint re-timing was performed: 142.06 seconds
remains unattributed and the 791.25/745.31 totals are explicitly non-comparable.

No complete gate file was retired. Distinct named locks, focused product cases,
atomic publication, and diagnostic owners still lack equivalent retirement
canaries, so deletion would reduce proof. The first full Node run found a live
Finder-created `form-output/.DS_Store`; the protected-artifact helper now excludes
only that gitignored basename, with an explicit canary. All other untracked files
remain failures.

Final local diagnostics (Node 26.7.0 / Python 3.14.7): all 19 Node files passed
serially; full Python inventory passed 827, skipped 2 documented scratch-writer
tests, and passed 160 subtests in 1672.16 s. The existing FastAPI/Starlette
deprecation warning remains. Catalog/runner contracts passed 36 tests after the
final Checkpoint 6 correction, the frontend production build passed, and the
composed test-requirements install resolved locally. Exact-head Node 22/Python
3.12 GitHub CI remains the final closeout gate. No
workbook, generated artifact, published registry, customer runtime, dealer
boundary, deployment path, dependency, or schema changed. Residual risks are the
Manager timing gap, uncaptured Node 22/Python 3.12 CI timing until GitHub runs the
workflow, the approval-gated promoted-model lock, and the inert workbook rows.

## 10. Files and surfaces expected to change during implementation

Expected owners, subject to Checkpoint 0 confirmation:

- `scripts/verify_workbook_candidate.py` — stage timing, shared candidate,
  temporary truth path, and composed report.
- `scripts/corvette_form_generator/runtime_contract.py` and
  `workbook_domain/registry.py` — consumed as authorities; changed only if a
  missing generic invariant is proven to belong there.
- `tests/test_verify_workbook_candidate.py` — compact stage tests plus bounded
  full-candidate acceptance.
- `tests/test_all_model_runtime_generation.py` — merge/retire overlap only after
  candidate parity.
- `tests/multi-model-runtime-switching.test.mjs` — generated state matrix and
  explicit candidate/truth inputs.
- current model-specific Node contract/regression/publication files — rewrite,
  narrow, move to acceptance, or retire according to the coverage ledger.
- `tests/lib/` — independent workbook-truth and runtime-matrix helpers.
- a new dependency-free validation catalog under `tests/`.
- Workbook Manager test fixtures and the focused files named in its README.
- `.github/workflows/release-candidate.yml` — layered commands/report upload only
  after local acceptance.
- `README.md`, `workbook-manager/README.md`, and `fable5loop/STATE.md` — owned
  operator guidance and handoff.

The implementation must not assume every listed file requires edits. Each
checkpoint uses the smallest confirmed manifest.

## 11. Preserved boundaries

- `stingray_master.xlsx` remains canonical and is not changed merely to make a
  test easier.
- No new workbook sheet, column, taxonomy, or business-rule store is introduced
  by this specification.
- Generated artifacts remain outputs and are never hand-edited as fixes.
- Runtime behavior, pricing, defaults, product availability, model promotion,
  and customer copy do not change unless a separately approved defect is found.
- Dealer endpoint, payload shape, model scoping, Turnstile/security behavior,
  modal UX, and live submission remain protected.
- No test performs a live dealer submission, deployment, WordPress upload,
  production cache purge, or production verification.
- No new dependency or build-system assumption is authorized.
- Workbook Manager draft/apply/recovery semantics remain unchanged.
- Raw ingest remains retired.

## 12. Failure handling and approval gates

During implementation:

- A stale literal may be rewritten without product approval when the workbook
  and current approved runtime agree and the replacement preserves or improves
  coverage.
- If workbook, retained contract, candidate output, and runtime behavior
  disagree, stop and classify the defect; do not choose product truth in test
  code.
- If a proposed acceptance lock would invent or freeze a new business decision,
  request approval.
- If removing a test would reduce a protected boundary or customer behavior
  proof, stop until an equivalent replacement is demonstrated by a forced
  failure/mutation canary.
- Any new dependency, workbook schema, public interface, CI/build assumption,
  dealer change, or deployment change requires explicit approval.
- Performance improvements must not depend on unsafe shared mutable workbooks,
  databases, temporary roots, module reload state, or parallel protected-output
  checks.

After two repeated no-progress attempts on one fixture/isolation problem, stop
at a clean checkpoint and report the evidence rather than weakening the gate.

## 13. Validation of this documentation checkpoint

This spec-writing task is complete when:

- this file exists as the owning fast-suite specification;
- the current baseline, authority classes, layers, state matrix, mutation
  canaries, checkpoints, approval gates, and preserved boundaries are explicit;
- the handoff points to Checkpoint 0 and says implementation has not started;
- README is inspected but unchanged because no operator command has changed;
- `scripts/validate_fable5_loop.py` and `git diff --check` pass;
- final status shows only this specification, the required handoff update, and
  pre-existing user-owned files.

## 14. Definition of done for the implemented suite

The implementation is complete only when all of the following are true:

1. Every default/checkpoint gate is cataloged and has one primary authority.
2. The canonical workbook passes package, schema, and source-quality validation.
3. Every workbook-discovered model generates once into an isolated candidate
   and passes strict contract validation.
4. Candidate registry and independent workbook-truth parity pass.
5. Every promoted model and active variant passes the runtime state matrix.
6. Acceptance locks are few, named, singly owned, and approval-bound.
7. All §8 mutation canaries prove the layers fail or adapt for the intended
   reason.
8. Layer 0 and Layer 1 meet their measured budgets or document an approved,
   evidence-backed exception.
9. Workbook Manager checkpoint time materially improves without losing any
   distinct Layer 3 boundary.
10. Required CI, local commands, catalog, and README agree.
11. Full Python and Node inventories are green or contain only explicitly
    documented environment skips; no baseline failure is hidden behind the
    layered release result.
12. Canonical workbook, tracked generated artifacts, dealer boundary, and
    deployment surfaces remain unchanged by validation itself.
13. The owning specification records final timings, coverage disposition,
    retired owners, residual risks, and closeout date before it is marked
    complete.

## 15. Next action

Checkpoints 0–4 are complete (see their result blocks in §9). The
catalog, coverage ledger, and contract test are in place; every documented stale
assertion is closed with no literal refreshed; the workbook-truth snapshot
exists and is proved independent of the generator; source-to-contract and
source-to-registry parity own every runtime collection that has a workbook
source; and every promoted model and declared active variant now passes the
generated runtime state matrix, with a forced-failure behind each §4.3
invariant. The candidate lane's browser stage runs that matrix against the
candidate registry.

Checkpoints 5 and 6 are complete. Workbook Manager tests share one immutable
verified projection/candidate, negative cases use compact fixtures, every
distinct Layer 3 real-workbook boundary remains, and both documented-order and
reverse-order checkpoint runs are green. CI now runs catalog-driven layered
selection, executes shared-setup groups through their one-process suite,
publishes the composed report, and has aligned operator documentation. No later
implementation checkpoint is authorized by this specification.

Two items still carry approval or classification gates:

- promoting `promoted_model_membership` from a proposed record to a real
  acceptance lock freezes a business decision and needs approval (§12).
  Checkpoints 1–3 all took the parity route; the literal in
  `multi-model-runtime-switching` remains the de-facto pin until approval;
- `section_presentation` carries two active Stingray-scoped rows for Grand Sport
  sections that Stingray never emits. Inert today, and the parity gate now
  enforces that they stay inert, but removing them is a workbook write no
  specification authorizes yet.

Still open from Checkpoint 0: the Node 22 / Python 3.12 CI reference timings.
