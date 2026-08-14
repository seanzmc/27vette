# Outcome rubric — Pass 2 receipt B: delete the shadow authorities

Spec: `docs/superpowers/specs/2026-07-23-validation-single-lane-active-surface-cleanup.md` §4 Pass 2,
required behaviors **5** (move `cleanup_display_text()`'s hardcoded customer-copy correction out of
generic code) and **9** (require complete workbook-owned generation/runtime metadata for every
active/generatable model; readiness fails rather than silently filling missing step, section,
context, summary, source-role, or required presentation metadata).

Reordered ahead of requirements 2/3 at the user's direction. Rationale, same as §2.8 S1: deleting
dead Python-side authority shrinks what the single builder has to converge, and every deleted
constant is one less place where the workbook and the runtime can disagree.

## The standing rule this receipt enforces

**The workbook is the only authority for anything a workbook column can express.** What the user
sees in the workbook or the Workbook Manager is what ships to the frontend. A Python constant,
default, override map, name heuristic, or text rewrite that can change a workbook-authored value is
a defect, not a convenience — it makes the runtime unpredictable from the source of truth and forces
a code search to explain any discrepancy.

## Method

For every candidate — module-level constant map, hardcoded workbook identifier, `.get(x, fallback)`
default, or text transform on the generation lane — do all three:

1. **Prove reachability against the canonical workbook, for all six active/generatable models.**
   Instrument the actual call, do not read the code and guess.
2. **Zero hits → delete.** The artifacts must stay byte-identical; that is the proof the constant
   was inert.
3. **Non-zero hits → the workbook is the defect.** Report the exact rows. Do not fix it in Python.
   A canonical workbook write needs separate approval and is out of scope for this receipt.

A fallback that is unreachable *today* but not fail-closed is still a defect: it will fire silently
the first time a workbook row goes missing. Those become explicit failures under requirement 9
rather than silent deletions.

## Measured before-state carried in from receipt A

- `cleanup_display_text()` fires on **0 of 2,323** option-name and description strings across all six
  models — every one of its five transforms is inert.
- All 48 `section_master` rows author `step_key`, so all **24** `SECTION_STEP_OVERRIDES` entries are
  unreachable; three of them contradict the workbook (`sec_gsce_001`, `sec_gsha_001`, `sec_lpoi_001`).
- Full six-model candidate run opens the workbook **13** times (1 discovery + 12 generation).

## Measurable criteria

| # | Criterion | Result |
|---|---|---|
| 1 | Every generation-lane module is swept; the inventory names each candidate, its consumer, and its measured hit count — no candidate is dismissed by reading alone | |
| 2 | Reachability is measured by instrumenting the real call path against the canonical workbook for all six active/generatable models | |
| 3 | Every zero-hit constant, map, heuristic, and text transform is deleted, not merely deprecated | |
| 4 | Any non-zero hit is reported as a workbook defect with exact rows, and left unfixed pending approval | |
| 5 | All 44 generated artifacts across all six models stay byte-identical (ignoring `generated_at`) — the proof that what was deleted was inert | |
| 6 | Requirement 9: a missing active-model `runtime_steps`, `section_presentation`, `context_section_master`, `order_summary_sections`, or `step_order_summary_map` row fails readiness for **every** active/generatable model, not only promoted ones | |
| 7 | A RED test exists for criterion 6 — the silent fallback is demonstrated before it is closed | |
| 8 | `ModelConfig` no longer carries a field whose only purpose is to shadow a workbook column | |
| 9 | No new test failure against the recorded baseline | |
| 10 | No tracked workbook, artifact, registry, or `form-app/` change | |

## Explicitly out of scope

Builder convergence and deletion of `production.build_production_source_data()` (requirement 2), the
six-behavior characterization (requirement 3), compatibility-artifact policy (requirement 8), the
new six-model harness (requirement 10), and `asset_map_sync.py` (§2.8 S7 non-goal). Any canonical
workbook write. Any artifact publication.
