# Outcome rubric — Pass 2 receipt A: contract-derived summary and one frozen workbook snapshot

Spec: `docs/superpowers/specs/2026-07-23-validation-single-lane-active-surface-cleanup.md` §4 Pass 2,
required behaviors **1** (cut the summary's dependency on report and preview, §2.8 S1),
**4** (one loaded, frozen workbook snapshot; optional reports consume the in-memory result),
**6** (runtime cleanup/finalization owned by `runtime_contract.py`), and
**7** (fold `validation.py` into `runtime_contract.py` and delete the module, §2.8 S5).

The spec orders requirement 1 before any builder change: "This removes two workbook reconstructions
per model per run and must land before any builder change." Requirements 2/3/5 (deleting the
Stingray builder fork, characterizing the two builders' behavioral differences, moving
`cleanup_display_text()`'s hardcoded copy correction into workbook data) are explicitly **not** in
this receipt; they are the next receipt inside the same pass and require the characterization work
that requirement 3 mandates.

## Measured before-state (bound to workbook SHA-256 `8858cff4…5b2166`, commit `ed3692a`)

Traced `load_workbook` call sites during one isolated generation per model:

| Model | Workbook opens | Sites |
|---|---|---|
| stingray | 2 | `production.py:165`, `interiors.py:121` |
| grand_sport | 4 | `inspection.py:427/647/976/1091` |
| z06 | 4 | `inspection.py:427/647/976/1091` |

Pass 2 gate set before any edit: **1 failed, 55 passed, 8 subtests passed** — the single failure is
the pre-existing `test_shared_assembler_preserves_stingray_runtime_drift_surfaces`
(`display_behavior` present on `opt_uqt_002` choices). It is a genuine builder-divergence
characterization owned by requirement 3, not by this receipt.

## Measurable criteria

| # | Criterion | Result |
|---|---|---|
| 1 | RED first: a test proving normal generation still constructs the inspection report fails before the change | PASS — `test_normal_generation_never_builds_the_inspection_report` and `test_generation_summary_is_derived_from_the_validated_runtime_contract` both failed first; the verifier reproduced the RED at `ed3692a` |
| 2 | `generate_model_artifacts()`'s result summary is derived from the **validated runtime contract**, not from `assembly.report` / `assembly.preview` | PASS — verifier read the summary back against the artifact on disk for all six models; 0 mismatches |
| 3 | Normal (non-`--emit-inspection`) generation never calls `inspect_model_sources()`; proved by patching it to raise | PASS — never called for any of the six; still called for the five non-Stingray models under `--emit-inspection` |
| 4 | Workbook opens per non-Stingray model drop, measured by the same trace as the before-state | PASS — 4 → 2 normal, 4 → 3 with `--emit-inspection`; z06 wall clock 0.67-0.71s → 0.54-0.62s |
| 5 | **One loaded workbook snapshot per builder**, and every workbook handle closes deterministically including on the exception path | PASS *as restated* — see the correction below. One snapshot per *assembly* is **not** delivered by this receipt |
| 6 | `--emit-inspection` still writes byte-identical inspection/preview/draft artifacts | PASS — all 30 review artifacts identical apart from one `generated_at` line each |
| 7 | Runtime contracts for all six discoverable models are byte-identical to the before-state (ignoring `generated_at`) | PASS — 44/44 artifacts; verifier regenerated both sides from a `git worktree` of `ed3692a` rather than trusting the maker's numbers |
| 8 | `validation.py` deleted; both helpers live in `runtime_contract.py`; no importer left behind | PASS with one deliberate deviation — see below |
| 9 | Requirement 6 verified as already satisfied, or completed | PASS — `live_contract_data` already lived in `runtime_contract.py` at `ed3692a`; `registry_promotion.py` consumes it. No change needed |
| 10 | No new test failure against the recorded before-state | PASS — `6 failed, 460 passed, 2 skipped`; the verifier reproduced all five code failures verbatim at `ed3692a`, and the sixth was this receipt being incomplete mid-run |
| 11 | No tracked workbook, artifact, registry, or `form-app/` change | PASS — see the restoration note in `validation-output.txt` |

### Correction to criterion 5 (raised by the verifier, accepted)

As originally worded — "one loaded, frozen workbook snapshot per **assembly**" — the criterion was
false, and the receipt title overclaimed. A non-Stingray assembly still opens **two** handles
(`build_contract_preview`, then `build_form_data_draft`), and three under `--emit-inspection`.
Collapsing those into a single assembly-wide snapshot requires the single-builder work of
requirement 2, which this receipt does not do. Spec requirement 4's "optional inspection/report
output consumes that in-memory result; it never reopens the workbook" therefore remains **open**.

What this receipt does deliver, and what criterion 5 now claims, is one snapshot **per builder**
plus deterministic close everywhere. The verifier also found a genuine pre-existing leak the maker
had missed: `inspect_model_sources()` and `build_contract_preview()` never closed their workbooks at
all, on success or failure. Both are now wrapped in `try/finally`, and
`test_workbook_handles_close_when_a_builder_raises` injects a `RuntimeError` into each of the three
builders and asserts the handle still closes.

### Deliberate deviation on criterion 8

The spec's S5 says to fold *both* helpers into `runtime_contract.py`. `validation_error_count` was
folded. `validation_row` was **deleted instead of ported**: `git grep` at `ed3692a` confirms zero
callers anywhere outside stale `.claude/worktrees/` copies. Porting dead code into the module this
pass is trying to make authoritative would work against the pass. The verifier independently
confirmed the zero-caller claim.

The new `validation_error_count` normalizes case and whitespace and tolerates non-list input, where
the deleted one did not. The verifier built the full differential table and confirmed every
divergent input is unreachable: all 31 severity literals in the generator are exact lowercase
strings and no workbook value ever reaches a generation `validation` row.

## Summary shape change, stated exactly

The two divergent result shapes (`_compatibility_result` for Stingray, `_reviewable_result` for
everything else) collapse into one `_summary_from_runtime_contract()`. Two changes here are
semantic, not cosmetic, and the verifier was right that the first draft of this receipt did not
say so:

- **`warnings` is gone from normal-generation stdout.** It came from `assembly.report["warnings"]`.
  It is real operator signal and is now reachable only through `--emit-inspection`. Spec §2.8 S1
  sanctions removing the dependency; this records the visibility cost.
- **`validation_warnings` is a different number, not a relocated one.** The old field counted
  *draft* rows, including the `*_draft_status` warning that `live_contract_data()` strips. The new
  field counts *contract* rows. Measured on z06: `{pass: 6, warning: 1}` → `{pass: 6}`, so the
  reported count goes 1 → 0. The contract number is the correct one to publish, but it is a value
  change.

Also removed from stdout, with no consumer found anywhere in Python, `.mjs`, `workbook-manager/`,
or active docs: `workbook_backup`, top-level `json` / `csv` / `choices` / `context_choices` /
`standard_equipment` / `rules` / `price_rules` / `interiors`, `blank_section_overrides`, `preview`,
and `draft`. The paths formerly at top-level `json` / `csv` remain under `compatibility_artifacts`.
The `"workbook_backup": None` string asserted by `stingray-generator-stability.test.mjs:362` lives
in `production.generate_production_artifacts()`, which is untouched.

## Pre-existing weakness recorded, not fixed

`validation_errors` in the summary is now structurally always `0`: `build_model_runtime_contract()`
calls `assert_runtime_contract()`, which raises on any error-severity row, so a nonzero value can
never be printed. `fable5loop/STATE.md` cites "`validation_errors: 0` each" as evidence of a clean
run — that is a tautology, not evidence. Baseline had the same property by a different route, so
this is not a regression, but the STATE claim has been reworded.

## Explicitly out of scope

Builder convergence and deletion of `production.build_production_source_data()` (requirement 2),
the six-behavior characterization (requirement 3), the `cleanup_display_text()` workbook migration
(requirement 5), compatibility-artifact policy (requirement 8), workbook-owned metadata
requiredness (requirement 9), and the new six-model harness `tests/test_all_model_runtime_generation.py`
(requirement 10). Any workbook write. Any artifact publication.
