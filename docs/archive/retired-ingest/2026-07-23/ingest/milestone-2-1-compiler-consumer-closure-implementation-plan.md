# Ingest Milestone 2.1 Compiler-Consumer Closure Implementation Plan

Status: COMPLETED AND INDEPENDENTLY VERIFIED 2026-07-13. Sean authorized this pass with “Okay run milestone 2.1.” No Milestone 3 or write authority is implied.

Recommended reasoning level: high.

Parent design: `docs/ingest/canonical-row-compiler-exception-queue-design.md`.

## 1. Diagnosis

Milestone 2 is complete, but the retained real run `20260712-215133-64bfad` remains `compiled_with_exceptions`. It contains 800 subjects: 92 compiler-projectable and 708 actionless. The actionless set is not one problem:

- 419 target relationship endpoint/identity subjects already have enough UI vocabulary for an exact option-to-option decision but lack complete compiler consumers;
- 120 comparator proposal subjects lack family-specific row consumers, and the existing generic `confirm_proposal` payload is incomplete for target-owned price/default facts;
- 4 ambiguous option identities lack exact retained-ID consumption;
- 135 status-bearing, no-RPO standard-equipment rows are incorrectly reported as unsupported source features even though the raw-ingest contract explicitly permits no-RPO standard rows;
- 30 remaining blockers concern Color/Trim parsing or missing required/global family compilation and must remain explicit tooling blockers unless this pass proves a safe generic derivation.

`plan_builder.py` cannot repair any of these. Milestone 3 remains excluded: a `pass-c-3` projection may only consume a ready manifest and may not choose IDs, fields, or actions.

## 2. Goal

Close the production compiler’s existing typed-action gap and the proven no-RPO option-source gap so that every reviewer-resolvable current subject has a finite, server-validated action with a complete compiler effect. Re-run a fresh all-target compile and leave only genuinely unsupported source/family work actionless.

## 3. Source-of-truth decisions

- Raw status-bearing rows own no-RPO standard-equipment evidence.
- The canonical workbook owns headers, types, enums, existing identities, references, and reusable metadata.
- `exceptions.py` owns reason/action/payload contracts.
- The compiler owns all canonical row materialization and resolution consumption.
- Comparator facts remain proposal evidence only. Confirmation becomes target authority only through an exact typed resolution; comparator IDs, prices, priorities, sections, and copy are never copied silently.
- Generated/runtime artifacts and `form-app/data.js` remain outputs and are untouched.

Standing constraints from `AGENTS.md` apply, especially §§3–6 and §§8–12.

## 4. Definition of done

1. Status-bearing no-RPO source rows parse as `standard_no_rpo` candidates; narrative rows with neither RPO nor status remain explicit skipped evidence.
2. No-RPO candidates preserve raw cells/statuses, remain non-selectable, compile active standard OVS rows, reuse a unique existing copy identity, and receive deterministic collision-safe IDs only when genuinely new.
3. `retain_existing` selects only one current ambiguous candidate ID, becomes a manifest dependency, and refuses duplicate claims or invented IDs.
4. `choose_relationship` consumes exact current target option IDs into a canonical direct-rule row. `replaces` maps through the existing `excludes + runtime_action=replace` contract; no new rule type is added.
5. Relationship non-applicability updates source-feature disposition rather than merely hiding a blocker.
6. Comparator direct, rule-group, exclusive-group, price-rule, and default-selection subjects expose controls only when both confirmation and rejection have complete outcomes.
7. Group/exclusive confirmations emit exact parent/member rows with deterministic IDs or reuse one unambiguous existing semantic identity.
8. Comparator price confirmation requires a target-authored whole-dollar value and finite target scope. Comparator price is never copied.
9. Comparator default confirmation requires target-authored priority and display behavior; comparator priority/default intent is never copied silently.
10. Every consumed row-producing resolution is represented in manifest dependencies and clears its exact blocker only after row materialization.
11. Mixed action sets remain wholly actionless if any alternative is still incomplete.
12. The forward browser renders only the finite family-specific payloads accepted by the server; no generic approve/skip or arbitrary JSON is introduced.
13. A fresh ignored GSX/ZR1/ZR1X compile records the post-pass reason/action counts, confirms the 135 no-RPO unsupported-source subjects are gone or explicitly explains any residual, and classifies every remaining actionless reason.
14. No `pass-c-3`, plan approval, workbook write, generation, publication, promotion, runtime, or dealer change occurs.

## 5. Test-first vertical slices

### Slice A — no-RPO canonical option evidence

RED then GREEN in parser/identity/compiler tests:

- status-bearing no-RPO row becomes a candidate;
- narrative-only row stays skipped;
- exact no-RPO copy identity reuses an existing option ID;
- new ID is deterministic and order-independent;
- compiled option is active, non-selectable, typed, and emits standard OVS rows;
- source-feature coverage joins to emitted rows instead of `unsupported_source_feature`.

### Slice B — exact identity and direct relationship consumers

RED then GREEN:

- ambiguous candidate exposes only its real existing IDs;
- `retain_existing` materializes the option and rejects duplicate/invented claims;
- unresolved endpoint/identity and comparator-direct subjects expose symmetric choose/not-applicable actions;
- exact relationship choice emits one canonical rule and updates feature disposition;
- replacement uses the existing workbook representation.

### Slice C — comparator family consumers

RED then GREEN for rule group, exclusive group, price rule, and default selection:

- exact proposal confirmation emits complete typed rows;
- existing semantic IDs are reused;
- unresolved/missing target IDs remain `resolved_pending_projection` and do not clear readiness;
- mark-not-applicable emits no row and records the correct source/comparator disposition;
- price/default payloads require target-owned values.

### Slice D — browser/API finite controls

RED then GREEN in service/UI tests:

- projectable action matrix matches actual consumers;
- choices are current target/workbook values;
- price/default proposal forms send exact typed payloads;
- server rejects invented identities, scopes, enums, priorities, and partial payloads before artifact mutation;
- resolve/reopen rollback, freshness, serialization, pagination, and historical routes remain green.

### Slice E — real-source and browser proof

- create a fresh ignored run from the current source/workbook/roles/selection;
- compile read-only and write summarized evidence only to the Fable receipt;
- use a disposable fixture root for resolve/reopen browser proof;
- use the retained real run only for GET/render comparison and hash it before/after;
- verify desktop/mobile and zero console errors;
- independently verify the frozen implementation/test/proof snapshot.

## 6. Expected files

Expected production edits:

- `scripts/corvette_form_generator/ingest/wizard/parser.py`
- `scripts/corvette_form_generator/ingest/wizard/identity.py`
- `scripts/corvette_form_generator/ingest/wizard/exceptions.py`
- `scripts/corvette_form_generator/ingest/wizard/compiler.py`
- `scripts/corvette_form_generator/ingest/wizard/session.py`
- `visualizer/ingest-wizard/wizard.js`
- `visualizer/ingest-wizard/wizard.css` only if finite controls expose a mobile overflow defect.

Expected test edits/additions:

- `tests/test_ingest_wizard_parser.py`
- `tests/test_ingest_wizard_identity.py`
- `tests/test_ingest_wizard_canonical_compiler.py`
- `tests/test_ingest_wizard_exception_flow.py`
- `tests/test_ingest_wizard_ui_milestone2.py`
- focused new consumer tests only if they keep the existing suites reviewable.

Closeout/docs:

- this plan
- `docs/ingest/README.md`
- `docs/ingest/canonical-row-compiler-exception-queue-design.md`
- `Order-Guide_IngestPrompt.md` only if the production-continuation status changes materially
- `fable5loop/STATE.md`
- `fable5loop/runs/2026-07-13-milestone21-compiler-consumer-closure/`

Inspected-no-change unless evidence forces a stop:

- `plan_builder.py`, `scripts/ingest_wizard_apply.py`, `scripts/promote_model.py`
- `stingray_master.xlsx` and raw export
- retained Milestone 1/2 proof artifacts
- tracked `form-output/runtime/**`, `form-app/**`, dealer code

## 7. Validation

- per-slice RED/GREEN targeted tests;
- focused parser/identity/exceptions/compiler/session/server/UI suites;
- `PYTHONPATH=scripts .venv/bin/python -m py_compile` for changed Python;
- `node --check visualizer/ingest-wizard/wizard.js`;
- broad affected ingest/editor metadata gate;
- workbook package/schema read-only validators;
- fresh current-source compiler artifact audit;
- disposable fixture browser resolve/reopen and retained-run GET-only browser proof at desktop/mobile widths;
- protected-surface hashes/diff before and after;
- full repository suite with independently reproduced baseline-red classification;
- `git diff --check`;
- Fable validator and repository Fable contract after receipt closure;
- bounded independent verifier on the final exact snapshot.

## 8. Stop conditions and non-goals

Stop rather than guess if a proposed row requires target price, priority, default, section, availability, relationship, or group membership not supplied by target evidence or an explicit typed resolution. Stop if a workbook schema/public interface/new dependency would be needed.

Non-goals: `pass-c-3`, apply planning/approval, workbook mutation, generation/publication/promotion, dealer changes, legacy-route retirement, or broad Color/Trim/presentation compiler implementation beyond classification.

## 9. Approval record

Sean approved execution on 2026-07-13 with “Okay run milestone 2.1.” No additional approval is needed for the bounded read-only compiler/browser/test/docs work above. Protected boundaries remain separately gated.

## 10. Implementation checkpoint — 2026-07-13

Implemented surfaces:

- status-bearing no-RPO standard rows now survive parsing, reuse one normalized existing-copy identity when unique, allocate deterministic new identities otherwise, and compile active/non-selectable option plus OVS rows;
- exact `retain_existing`, direct relationship, comparator group/exclusive/price/default, and explicit no-row dispositions now have compiler consumers;
- `replaces` uses canonical `excludes` plus `runtime_action=replace`;
- readiness clears only when the compiler records an exact materialized or explicit no-row effect;
- comparator price confirmation requires reviewer-authored price, body scope, trim scope, and variant scope; comparator defaults require reviewer-authored priority/display behavior;
- browser/API choices are finite and exclude blocked or incomplete option catalogs; typed color/interior/model endpoints remain source/tooling blockers rather than being coerced into option identities.
- long typed-exception reason/subject IDs wrap within the exception-card header; final 390px CDP proof has zero document, queue, card, or control overflow.

Fresh proof `20260713-181910-7dc5bb` contains 5,093 canonical rows and 711 exception subjects. Of those, 257 are compiler-projectable and 454 remain actionless: 396 typed color/interior/model relationship endpoints awaiting dedicated endpoint compilers, 37 comparator proposals with incomplete ready option catalogs, 19 global/target metadata-family blockers, and 2 Color/Trim parser blockers. Grand Sport X, ZR1, and ZR1X remain `compileReady=false`; this is the correct fail-closed state and Milestone 3 remains blocked.

Final validation is green: focused gate 84 passed plus 12 subtests; broad affected gate 307 passed plus 16 subtests; Fable contract 13 passed; Python/JavaScript syntax, Fable loop validation, workbook package/schema validation, deterministic artifact recompile, protected-surface hashes, disposable desktop browser resolve/recompile/reopen proof, and corrected 390px mobile proof passed. Exact verifier `deleg_db6d9493` passed the prior compiler findings but found a final mutation-vs-GET projectability mismatch; the repair rejects hidden/incomplete comparator actions with 409 before artifact mutation and preserves duplicate-RPO identity multiplicity. Mobile CSS final-delta verifier `deleg_7a565068` and session final-delta verifier `deleg_37da6841` both returned PASS with no edits. Milestone 2.1 is closed; Milestone 3 remains blocked until a separately approved follow-up compiles the residual typed endpoints, Color/Trim sheets, and target metadata families into a ready manifest.
