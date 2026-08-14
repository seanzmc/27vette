# Verifier report — Pass 1: shared registry as sole workbook-shape authority

Graded independently against `fable5loop/runs/2026-07-25-pass1-registry-shape-authority/outcome.md`.
The verifier had no access to the maker's reasoning; every claim below was re-derived from the diff
and from probes the verifier wrote itself.

**Cycle 2 (re-verification).** Cycle 1 returned FAIL on rubric criterion 9 (Finding F1) plus six
observations. Three items were addressed and are re-graded here from scratch; the rest are carried
forward with their cycle-1 evidence, marked in the Criteria table.

Bound to commit `d5db8bb7744097078fb0ef84b8df772fbc2e1f6f`, workbook SHA-256
`8858cff40ea7eaeda6b7921714f3697a6ee9d1bbc99c84e564d7b118e45b2166`.

## Verdict

PASS — F1 is fixed and the fix survived an exhaustive monotonicity probe, the `__getattr__`
recursion hazard is gone, and blank `artifact_type` on an active promotion row is now a schema
error; all twelve rubric criteria are met, with one residual non-blocking gap (O1-residual) and
five carried-forward observations recorded below.

## Criteria

| # | Criterion | Result | Cycle | How the verifier checked it |
|---|---|---|---|---|
| 1 | `schema_validation.py` holds no independent header/artifact-type authority | PASS | c1, spot-rechecked c2 | `scripts/corvette_form_generator/schema_validation.py:116-120` — all four constants are assignments from `WRITABLE_COLUMNS` / `REGISTRY_PROMOTION_ARTIFACT_TYPES` / `VEHICLE_SETUP_FIELDS`. Runtime check confirmed `MODEL_SETUP_COPY_FIELDS == MODEL_MASTER_HEADERS[9:16]` (the retired literal slice) and that promotion headers and the artifact-type set match the registry by value. Grep over `scripts/` for module-level `*_HEADERS`/`*_COLUMNS`/`*_FIELDS`/`*_ARTIFACT_TYPES` found no surviving hand-authored workbook header tuple in either module. c2 re-read the file: the new pre-loop check consumes `VALID_REGISTRY_PROMOTION_ARTIFACT_TYPES`, adding no new literal. |
| 2 | `registry_promotion.py` holds no independent header/artifact-type authority | PASS | c1 | `scripts/corvette_form_generator/registry_promotion.py:14-24`. The three removed literals are now derived. `VEHICLE_SETUP_FIELDS` is derived by `startswith("setup_")` over `WRITABLE_COLUMNS["model_master"]` — a derivation rule, not a second list (Observation O3). Unchanged in c2. |
| 3 | Registry owns the promotable artifact-type domain | PASS | c1 | `workbook_domain/registry.py:31-36` plus `EDITOR_SHEET_META["model_registry_promotion"]["enums"]["artifact_type"]` at `registry.py:183`. Remaining literal `current_generation` / `draft_artifact` occurrences in `scripts/` are single-value comparisons and one parse default, not a competing domain set. Unchanged in c2. |
| 4 | A registered active sheet missing a registry-owned column is an error | PASS | c1 | Verifier-built probe (`probe_missing.xlsx`): a fresh copy of `stingray_master.xlsx` with `option_name` deleted from `z06_options`. `validate_workbook_schema(path, check_live_contract=False)` → `registry_family_columns_missing z06_options option_name`. The maker's test helper was not used. |
| 5 | A rogue physical column on a registered active sheet is an error | PASS | c1 | Verifier probe (`probe_rogue.xlsx`): appended `verifier_rogue_col` to `z06_options` → `registry_family_columns_unregistered z06_options verifier_rogue_col`. |
| 6 | A rename applied to **every** active sheet at once is rejected | PASS | c1 | Verifier probe (`probe_coordinated.xlsx`): renamed `option_name` → `option_title` on all six sheets registered under `source_option_sheet` with `active=TRUE`, discovered from the workbook's own `model_workbook_sources` (`stingray_options`, `grandSport_options`, `grand_sport_x_options`, `z06_options`, `zr1_options`, `zr1x_options`). Result: 12 issues, all `registry_family_columns_*`, and **`other check_ids: []`** — no cross-sheet-equality check fired at all. Direct proof the pre-existing header-equality checks are blind to coordinated drift and only registry ownership catches it. |
| 7 | `editor_ops` rejects a write to a physical column outside the registry | PASS | c1 | Verifier probe with its own extract: `vp_options` headers include `verifier_ghost` (physically present); family `options` does not own it. `validate_batch` → `op[0] update vp_options {...}: column(s) ['verifier_ghost'] are not owned by family 'options' in the shared workbook registry`. Fires on `update`, `add`, and a mixed row; the control write to `option_name` returned `[]`. |
| 8 | Workbook Manager carries no hand-authored column metadata | PASS | c1 | `workbook-manager/backend/app/catalog.py:236-253` — `_SECTION_SPEC = _build_readonly_spec("sections", "form_sections")`, columns and types read from `READONLY_SHEET_META`. Remaining `_ROUTING` literals (`catalog.py:140-155`) are table-name/scope routing, not column metadata. |
| 9 | `models_for_write_targets()` widens, never narrows, on global families | **PASS (was FAIL)** | **re-graded c2** | See Delta 1. Exhaustive probe over three adversarial extracts × all target subsets of size ≤4: **zero** monotonicity violations. The cycle-1 counterexample now returns the widened answer. |
| 10 | Canonical workbook still validates | PASS | **re-run c2** | `validate_workbook_schema.py stingray_master.xlsx --skip-live-contract` → `valid`, 0 issues, exit 0; `validate_workbook_package.py stingray_master.xlsx` → `valid`, 0 issues, exit 0. Both re-run after the c2 code changes. In c1 an openpyxl round-trip of the *unmodified* workbook also reported 0 issues, so drift results are attributable to injected drift alone. |
| 11 | No new test failure versus the recorded baseline | PASS | **re-run c2** | `PYTHONPATH=scripts .venv/bin/python -m pytest tests/test_editor_lints.py tests/test_source_assembly_characterization.py -q` → `6 failed, 22 passed`, the identical six node IDs as the c1 run and as the c1 stashed baseline (`git stash push scripts workbook-manager tests` → same `6 failed, 22 passed`; popped cleanly). Focused suites re-run in c2 with `test_workbook_changeset_service` and `test_schema_validation_metadata` added: `185 passed`. `test_fable5_loop_contract` treated as out of scope per the coordinator. |
| 12 | No workbook, generated-artifact, registry, or dealer write | PASS | **re-checked c2** | `git status --porcelain -- stingray_master.xlsx form-output form-app` empty after all c2 probes. `shasum -a 256 stingray_master.xlsx` = `8858cff40ea7eaeda6b7921714f3697a6ee9d1bbc99c84e564d7b118e45b2166`. All probe workbooks written to the session scratchpad; no generation, promotion, or node suite run. |

### Delta 1 — F1 fix: `models_for_write_targets()` (rubric criterion 9)

`registry.py:412-448` now sets `saw_global`, `continue`s instead of returning, and after the loop
unions `active_model_keys(extract)` **and** every owner set in `models_by_sheet`.

The verifier did not test the maker's named cases only; it brute-forced the invariant. For each of
three adversarial extracts it computed the single-target result for every registered target, then
for **every subset of size 1–4** asserted `union(singles) ⊆ result`:

```
== b) zr1 active in model_workbook_sources, active=False in model_master
   single zr1_options   -> ['zr1']        single asset_map -> ['ghost','only_master','stingray','zr1']
   monotonicity violations over all subsets<=4: 0
== c) model_master sheet entirely absent
   single stingray_options -> ['stingray'] single asset_map -> ['ghost','stingray','zr1']
   monotonicity violations over all subsets<=4: 0
==    model_master present but zero rows
   monotonicity violations over all subsets<=4: 0
```

- (a) **No target set shrinks the result.** Zero violations across 3 extracts × 56 subsets each.
- (b) The cycle-1 counterexample is fixed: `[zr1_options, asset_map]` returned `{'stingray'}` before; it now returns `{'ghost','only_master','stingray','zr1'}` ⊇ `{'zr1'}`.
- (c) A missing `model_master` no longer wipes the set: `[stingray_options, asset_map]` returned `set()` before, now returns `{'ghost','stingray','zr1'}`.

The extract included a deliberately hostile `ghost` model that owns an active source sheet and does
**not** appear in `model_master` at all. It is retained in every global result, confirming the union
covers the source-registration side and not only `model_master`. Attempts to construct a narrowing
input failed: once `saw_global` is set the result is a fixed superset of every per-target truth, and
a non-global target can only add. A sheet reachable solely through an inactive
`model_workbook_sources` row raises `KeyError` from `registered_sheet_families` rather than silently
contributing nothing — a hard failure, not a narrowing.

### Delta 2 — lazy `__getattr__` recursion (Observation O2, closed)

`workbook_domain/__init__.py:24-38` now accepts `"service"` and resolves via `import_module(...)`,
with an in-code comment naming the `from ... import` recursion trap. Five fresh interpreters, each
with `sys.setrecursionlimit(200)` so any recursion fails loudly rather than hanging:

| Probe | Result |
|---|---|
| `import ...workbook_domain as wd; wd.service` **first** | `corvette_form_generator.workbook_domain.service` — no recursion |
| `wd.apply_changeset` / `preview_changeset` / `approve_changeset` first, then `wd.service` | all resolve — no recursion |
| `import corvette_form_generator.workbook_domain.service` directly | ok |
| `from corvette_form_generator.workbook_domain import service, apply_changeset` (the `_handle_fromlist` path) | ok |
| `wd.definitely_not_here` | `AttributeError` (correct), **not** `RecursionError` |
| `from ...workbook_domain import nope` | `ImportError` (correct), **not** `RecursionError` |
| `from ...workbook_domain import *` | every `__all__` name bound; none missing |

Both attribute orders were tested specifically because the fix is order-sensitive in principle. The
underlying cycle the laziness exists to break is real and re-confirmed: `schema_validation` →
`registry_promotion` → `workbook_domain.registry` triggers the package `__init__`, whose old eager
`service` import reaches `editor_ops`, which imports `schema_validation` (`editor_ops.py:23`). All
four modules import standalone.

### Delta 3 — `registry_promotion_blank_artifact_type` (Observation O1, half closed)

`schema_validation.py:757-777`, a pre-loop over `records(wb["model_registry_promotion"])` gated on
`truthy(row.get("active"), default=True)`.

| Probe (canonical workbook mutated, temp copy) | Result |
|---|---|
| blank `artifact_type` on **zr1** — `active=True`, `promoted_to_runtime=False` (the row the promoted-only loop skips) | `total=1`, `error registry_promotion_blank_artifact_type` row 6, `other check_ids: []` — **fires** |
| blank `artifact_type` on **stingray** — `active=True`, `promoted_to_runtime=True` | `total=1`, same check, row 2 — fires |
| blank `artifact_type` on **zr1x** with `active=False` | `total=0`, no issues — correctly silent on inactive rows |
| blank `artifact_type` on **zr1x** with `active` **blank** | `total=1`, fires — `default=True` treats blank activeness as active, matching `editor_ops`' effective-active-row rule |
| unmodified canonical workbook | 0 issues (criterion 10) — **does not fire** |

The non-promoted case is the important one and it is covered: before this check, `zr1` /
`grand_sport_x` / `zr1x` (all `active=True, promoted_to_runtime=False` in the canonical workbook)
were skipped entirely by the promoted-only loop.

**O1-residual (still open, non-blocking).** Only the *blank* half of the gap is closed. The
domain-membership check `registry_promotion_unknown_artifact_type` remains inside the promoted-only
loop at `schema_validation.py:781-782` (`if not truthy(active) or not truthy(promoted_to_runtime): continue`).
So an active, non-promoted row with a *garbage* artifact type still validates green while the write
path rejects it — the same "passes the gate, then the write path refuses it" shape O1 named:

```
zr1 row 6: artifact_type='verifier_not_a_real_type'  (active=True, promoted_to_runtime=False)
  validate_workbook_schema  -> total issues: 0   check_ids: []
  editor_ops.validate_batch -> "artifact_type: 'verifier_not_a_real_type' not in enum
                                ['current_generation','draft_artifact','runtime_contract']"
```

One-line fix: validate membership in the same pre-loop that now catches blanks, rather than only for
promoted rows. Not blocking — no rubric criterion covers artifact-type *values*, and the canonical
workbook carries `runtime_contract` on all six rows.

## Evidence inspected

Cycle-2 diff surface (`git diff` on the working tree, `git diff --cached` for staged docs):

- `scripts/corvette_form_generator/workbook_domain/registry.py` — `saw_global` accumulation and post-loop union in `models_for_write_targets`; unchanged `REGISTRY_PROMOTION_ARTIFACT_TYPES`, `artifact_type` enum, `READONLY_SHEET_META`, `active_model_keys`.
- `scripts/corvette_form_generator/workbook_domain/__init__.py` — `from importlib import import_module`; `__getattr__` accepting `"service"`.
- `scripts/corvette_form_generator/schema_validation.py` — new `registry_promotion_blank_artifact_type` pre-loop inside `validate_registry_promotion_metadata`; the cycle-1 derived constants, `registered_family_sheets()`, and `validate_registry_family_columns()` unchanged.
- `scripts/corvette_form_generator/editor_ops.py:712-722`, `scripts/corvette_form_generator/registry_promotion.py:14-24`, `workbook-manager/backend/app/catalog.py:236-253` — unchanged since cycle 1.
- `tests/test_workbook_domain_registry.py` — adds `test_models_for_write_targets_never_narrows_when_a_global_target_is_added` (asserts `source_only == {"grand_sport_x"}` and `source_only <= with_global`); `tests/test_schema_validation_metadata.py` — adds `test_blank_artifact_type_on_an_active_promotion_row_is_rejected`; `tests/test_editor_ops_apply.py` unchanged.

Verifier-authored probes this cycle (session scratchpad, none reusing a maker helper):

1. Inline brute-force monotonicity probe over `models_for_write_targets` — 3 extracts × every target subset of size ≤4, asserting `union(singles) ⊆ result`.
2. Six fresh-interpreter recursion probes against `workbook_domain.__getattr__`, each with `sys.setrecursionlimit(200)`.
3. `probe2.py` / `probe3.py` — blank `artifact_type` on promoted, non-promoted, inactive, and blank-active rows of temp copies of the canonical workbook.
4. `probe4.py` — invalid (non-blank, non-domain) `artifact_type` on an active non-promoted row, checked through both `validate_workbook_schema` and `editor_ops.validate_batch` (O1-residual).

Carried forward from cycle 1: `probe1.py` (baseline / dropped column / rogue column / coordinated
rename across every active options sheet), the `editor_ops` rogue-column probe with control, the
requiredness probe, and direct reads of the canonical `model_master`, `model_registry_promotion`,
and `model_workbook_sources` rows.

## Validation Output Inspected

`validation-output.txt` predates this cycle's code changes and was not re-recorded by the maker.
The verifier re-derived every load-bearing line rather than trusting it:

- Protected-surface block, workbook SHA, and both `valid`/0-issue CLI results: **re-run and reproduced after the cycle-2 changes** (criteria 10 and 12).
- The recorded `7 failed, 452 passed, 2 skipped` full-suite line: the six code failures were reproduced this cycle (`6 failed, 22 passed` on the focused pair) and were proven pre-existing in cycle 1 by the stash comparison. The seventh, `tests/test_fable5_loop_contract.py`, is loop-receipt bookkeeping and is **out of scope for this verdict** per the coordinator; the count discrepancy against `outcome.md` criterion 11 ("6 pre-existing") is a receipt-text matter, not a code matter.
- The single full-schema (live-contract) error `app_registry_freshness_check_failed` is the retained Stingray runtime contract, explicitly a Pass 3 prerequisite in the spec and outside Pass 1 scope. Accepted as recorded.
- Node results were **not** re-run, per the instruction not to run the node suite (its promotion gate rewrites `data.js`). The file's claim that both node failures reproduce with the change stashed remains recorded-but-unverified by this verifier.
- Because the source changed after `validation-output.txt` was written, the file should be re-recorded before the receipt is closed so it describes the code actually being accepted.

## Required Fixes Before Pass

None.

The following are recorded for Pass 2/3 and do not block acceptance:

- **O1-residual — `registry_promotion_unknown_artifact_type` is still promoted-only** (`schema_validation.py:781-782`). An active, non-promoted row with a non-blank invalid artifact type validates green and is then rejected by `editor_ops` (probe output in Delta 3). Move the membership check into the same pre-loop that now catches blanks.
- **O3 — `VEHICLE_SETUP_FIELDS` is a naming heuristic.** `registry_promotion.py:23` derives the customer-facing setup-copy contract from `startswith("setup_")` over `model_master`'s columns. It reproduces the retired literal exactly today, but any future `model_master` column named `setup_*` silently joins that contract with no test to notice.
- **O4 — the column gate is membership-only and active-only.** `validate_registry_family_columns` compares sets, so a pure column *reorder* is not an error there and duplicate physical headers are invisible. It visits only `GLOBAL_SHEET_FAMILIES` plus the *active* source graph, so an inactive scaffold sheet can drift ungated. Defensible active-surface scoping; state it rather than assume it.
- **O5 — `READONLY_SHEET_META["sections"]` is the sole authority for `section_master`'s shape, and nothing validates it against the physical sheet.** Not a regression (`catalog.py` hand-authored the same list before), but the pass's thesis — one authority plus a gate proving the workbook matches it — is only half-applied to read-only families.
- **O6 — test fixtures still hand-author workbook headers.** `tests/test_runtime_metadata_guards.py:26` (`PROMOTION_HEADERS`), `tests/test_promote_model.py:42,71`, and `tests/test_registry_promotion_metadata.py:96` each re-type the `model_master` / `model_registry_promotion` header lists. Out of rubric scope and fixture duplication is not authority, but these will drift silently the next time a registry column is added.
- **Receipt hygiene** — re-record `validation-output.txt` against the post-fix source, and reconcile its 7-failure line with `outcome.md`'s "6 pre-existing". STATE.md and `run.json` `verifier.*` fields are being closed separately by the coordinator.

O2 (lazy-import recursion / unresolvable `service`) is **closed**; O1 is **half closed**, with the
residual tracked above.

## Durable Lesson Candidates

1. **Cross-sheet equality is not a shape gate.** The coordinated-rename probe produced twelve registry errors and *zero* issues from any other check. Any validator that proves sheets agree with each other, rather than with a declared contract, reports green on exactly the drift a bulk export produces. When a generated writer replaces a hand editor, every "these agree" check must be re-derived as a "this matches the declared contract" check.
2. **Verify a monotonicity claim by brute force, not by example.** F1 survived cycle 1's targeted tests; the fix now survives 3 extracts × 56 target subsets with zero violations. When code claims "never narrows"/"always widens", the cheap proof is to enumerate subsets and assert the superset relation — and to include an input where the candidate answers actually differ (a model active in one activeness source and inactive in the other).
3. **An early `return` inside an accumulation loop is a narrowing-bug pattern.** Substituting a computed set for an accumulated one is safe only if the substitute is provably a superset. The fix's shape — set a flag, finish the loop, union at the end — is the general remedy.
4. **A lazy `__getattr__` must not use `from . import X`.** The from-import form calls `getattr` on the package, re-entering `__getattr__` and recursing. `importlib.import_module` is the correct primitive, and the regression probe must set a low recursion limit and exercise both attribute orders plus an unknown name — otherwise the bug presents as a hang, not a failure.
5. **Consolidating an authority silently promotes optionality into requiredness — close the loop in both directions.** Moving `artifact_type` into `enums` flipped a column to required across every write path while the read path kept its permissive default. Fixing the *blank* half without the *invalid-value* half leaves the same class of hole (O1-residual). When a write-path constraint is added, enumerate every read-path branch that can accept what the write path now refuses, and gate all of them.
6. **When source changes after a receipt's validation output is recorded, the receipt is stale evidence.** This cycle's canonical-workbook results and test counts had to be re-derived because `validation-output.txt` described the pre-fix source. Re-record validation output as the last step before closing a receipt.

## File Edit Statement

The verifier edited exactly one file: `fable5loop/runs/2026-07-25-pass1-registry-shape-authority/verifier-report.md` (this file), overwritten completely, in both cycles.

No source, test, spec, workbook, or generated file was modified by the verifier in either cycle. In
cycle 1, `git stash push scripts workbook-manager tests` was used for the baseline regression
comparison and `git stash pop` restored the working tree to the identical modified-file list
(verified with `git status --porcelain` before and after); cycle 2 required no stash. All probe
workbooks and scripts were written to the session scratchpad at
`/private/tmp/claude-501/-Users-seandm-Projects-27vette/13c042a1-48ae-4444-b00a-5d226ef33a66/scratchpad`,
never to the repository. No generation, promotion, publication, or node suite was run. Working-tree
modifications to `fable5loop/STATE.md` and `fable5loop/skills/27vette-fable5-compounding.md` present
at the end of this cycle were not made by the verifier.
