# Ingest Milestone 2.2 Typed Endpoint and Metadata Compiler Closure Implementation Plan

Status: IMPLEMENTED AND INDEPENDENTLY VERIFIED 2026-07-14. Final exact-current verifier `deleg_30b5e24d` passed the code and real-source artifact lanes without edits. Sean authorized this pass with “Time for milestone 2.2” and supplied the Color/Trim transfer rules below. No Milestone 3, workbook-write, generation, publication, promotion, deployment, or dealer authority is implied.

Recommended reasoning level: high.

Parent design: `docs/ingest/canonical-row-compiler-exception-queue-design.md`.

## 1. Diagnosis

Milestone 2.1 is complete. Fresh retained proof `20260713-181910-7dc5bb` has 5,093 canonical rows and 711 typed subjects. The current queue has 417 actionless tooling blockers:

- 396 `unresolved_relationship_endpoint` subjects across 25 tokens. The unresolved tokens are not one entity class: 10 paint RPOs, 13 interior codes, and two model-label false positives (`ZR1`, `ZR1X`). `GT2` is another non-RPO label currently interpreted as an endpoint. The relationship scanner only knows option RPOs emitted from equipment sheets; it has no typed paint/interior/model endpoint catalog.
- 19 `unsupported_global_family` subjects: all three targets lack the five model-scoped presentation profiles; Grand Sport X also lacks `model_master`, `model_workbook_sources`, `model_interior_scope`, and `interior_components` rows.
- Two `unsupported_color_trim_source` subjects because `Color and Trim 1–2` remain excluded from Pass A.
- 37 comparator proposal subjects are accepted by the typed schema but hidden by the service because one or more ready target option endpoints are absent or non-unique.

The workbook and raw export establish reusable structure:

- `Color and Trim 1` lists the same ten exterior colors and the LT/LZ interior matrix; `Color and Trim 2` lists custom R6X combinations.
- Grand Sport and Z06 both use the same ten active paint rows with shared canonical option IDs.
- `lt_interiors` has 132 rows; `LZ_Interiors` has 130 rows.
- `model_interior_scope` currently has Grand Sport 132, Z06 130, ZR1 90, ZR1X 90, and Grand Sport X zero rows. The Z targets contain exactly the existing 1LZ/3LZ subset; Grand Sport carries both 3LT EL9 rows gated by `opt_z25_001`.
- The five presentation sheets already have a proven comparator-prefill path in `decisions.presentation_prefill()`.

## 2. User-authoritative Color/Trim rules

1. Every Corvette model has the same exterior colors; the target paint profile is copied from its selected comparator.
2. Interior family is determined by target trims:
   - `1LT`, `2LT`, `3LT` use `lt_interiors`;
   - `1LZ`, `3LZ` use `LZ_Interiors`.
3. Color-combination overrides are common to every model and use the same comparator-backed canonical IDs.
4. Grand Sport’s LT-exclusive EL9 interior is also available on Grand Sport X.
5. Comparator mapping remains Grand Sport → Grand Sport X and Z06 → ZR1/ZR1X.

These decisions supersede the parent design’s general “comparator is context only” restriction only for the explicitly shared Color/Trim, interior/component, color-override, and reusable presentation-profile surfaces. Comparator option/rule prices, defaults, unrelated relationships, sections, and IDs remain nonportable unless already permitted by Milestone 2.1’s typed target-authored actions.

## 3. Goal

Compile the shared Color/Trim and target metadata profiles deterministically, introduce a typed endpoint catalog for relationship interpretation, and make every remaining reviewer action visible only when its compiler consumer is complete. A fresh GSX/ZR1/ZR1X run should have no actionless Color/Trim, typed-endpoint, metadata-family, or incomplete-catalog blocker that the supplied rules make deterministic.

## 4. Source-of-truth decisions

- The supplied rules own the cross-model Color/Trim transfer decision.
- Selected comparator mapping in `model-selection.json` owns the source profile per target.
- Target `variant_master`/`model_variants` trims own LT-vs-LZ interior filtering.
- Comparator workbook rows own the reusable paint, interior scope/component, color-override, and presentation row shape.
- Existing target rows and shared canonical option/interior IDs are reconciled, not deleted or renumbered.
- `exceptions.py` continues to own typed action/payload contracts.
- The compiler owns canonical materialization and source-feature dispositions.
- Generated/runtime artifacts remain outputs and are untouched.

Standing constraints from `AGENTS.md` apply, especially §§3–6 and §§8–12.

## 5. Definition of done

1. The compiler builds a target-local profile from the selected comparator, never from a hardcoded target→comparator table.
2. Every target receives the comparator’s active `sec_pain_001` paint rows with shared canonical paint option IDs; target-existing rows are reused and new GSX rows are complete/typed.
3. Paint OVS rows are emitted for every target variant as `available`, with exact target variant IDs.
4. Interior source family derives only from target trim names. Unknown/mixed trim families fail closed.
5. `model_interior_scope` and `interior_components` copy only comparator rows whose trim/interior IDs belong to the target family. GSX includes the two EL9 rows and their `opt_z25_001` requirement.
6. Shared `color_overrides` rows remain exact canonical rows and every referenced paint/interior/override option identity resolves in the target desired state.
7. The two excluded Color/Trim source sheets retain content-bound evidence from their real authority-bound `sheet-profile.json` entries plus the raw-source SHA and receive explicit `resolved_not_a_workbook_fact` ledger dispositions because the approved comparator profile—not those layouts—owns the canonical output. A missing sheet profile, missing source authority, nonexistent sheet role, or role other than exact `exclude` remains `exception_open` with `unsupported_color_trim_source`.
8. Relationship scanning uses a finite typed catalog: target options by RPO, interiors by source interior code, and explicit non-RPO labels. Model names and seat labels such as `ZR1`, `ZR1X`, and `GT2` do not become workbook relationships.
9. Paint endpoints compile through ordinary option relationships. Interior endpoint evidence is consumed only through a canonical target interior effect or a proven comparator-profile relationship; it is never coerced into an option ID.
10. Duplicate interior-code matches expand only where the canonical direct-rule effect is semantically valid. Any unsupported one-of/group semantics remain one explicit tooling blocker rather than emitting impossible AND requirements.
11. Comparator proposals become visible only when all ready target endpoint identities are complete and unique; mutation and GET continue sharing the same projectability decision.
12. The five presentation sheets copy the selected comparator’s active exact-model profile with only `model_key` changed, and section references are validated against the target desired section set/live `section_master`.
13. Grand Sport X receives complete inactive `model_master` and `model_workbook_sources` desired rows through existing headers/conventions; ZR1/ZR1X retain their established metadata identities.
14. Fresh real-source proof reports exact row/subject/actionable/actionless counts, zero physical duplicate keys, deterministic same-run recompilation, exact source-feature coverage, and protected-surface byte identity.
15. No `pass-c-3`, plan approval, workbook mutation, generation/publication/promotion, runtime, or dealer change occurs.

## 6. Test-first vertical slices

### Slice A — shared paint profile

RED then GREEN:

- selected comparator paint rows produce target paint option rows with shared IDs;
- target-existing rows reconcile without ID churn;
- every target variant receives available OVS rows;
- absent/duplicate comparator paint identities fail closed;
- no unrelated comparator option is copied.

### Slice B — interior family and component profile

RED then GREEN:

- LT and LZ family selection comes only from target trims;
- mixed/unknown trims fail closed;
- Z targets receive exact 1LZ/3LZ subsets;
- GSX receives full LT scope including both EL9 rows and `opt_z25_001` gates;
- component rows match the selected interior set exactly;
- color-override references close against target desired identities.

### Slice C — typed relationship endpoints

RED then GREEN:

- paint RPOs resolve as options;
- interior codes resolve to exact target interior IDs;
- model/seat labels are classified as non-RPO text;
- comparator-profile interior effects consume matching raw relationship evidence;
- unresolved one-of semantics remain fail-closed;
- endpoint dispositions and manifest dependencies are exact and order-invariant.

### Slice D — model/presentation metadata

RED then GREEN:

- missing GSX model/source-role rows materialize from selected target, registry, and target variants;
- five comparator presentation profiles copy with exact headers/types and target model key;
- invalid target section references or incomplete comparator profiles block;
- Z target metadata is reused without duplicate keys.

### Slice E — service/browser and real-source proof

RED then GREEN:

- newly complete catalogs expose the existing finite controls;
- invented typed endpoint identities remain rejected before mutation;
- disposable resolve/recompile/reopen and retained-run GET-only browser paths remain stable at desktop/mobile widths;
- fresh current-source artifacts satisfy the Definition of Done and protected hashes.

## 7. Expected files

Expected production edits:

- `scripts/corvette_form_generator/ingest/wizard/compiler.py`
- `scripts/corvette_form_generator/ingest/wizard/relationship_compiler.py`
- a focused compiler helper such as `scripts/corvette_form_generator/ingest/wizard/profile_compiler.py` only if extraction keeps `compiler.py` reviewable
- `scripts/corvette_form_generator/ingest/wizard/session.py` only if service catalogs need typed endpoint hydration
- `visualizer/ingest-wizard/wizard.js` only if a new finite typed control is required

Expected tests:

- `tests/test_ingest_wizard_canonical_compiler.py`
- `tests/test_ingest_wizard_relationship_compiler.py`
- `tests/test_ingest_wizard_exception_flow.py`
- `tests/test_ingest_wizard_ui_milestone2.py` only if UI behavior changes
- focused new profile-compiler tests if a helper is added

Closeout/docs:

- this plan
- `docs/ingest/README.md`
- `docs/ingest/canonical-row-compiler-exception-queue-design.md`
- `fable5loop/STATE.md`
- `fable5loop/runs/2026-07-14-milestone22-typed-endpoint-metadata-closure/`

Inspected-no-change unless evidence forces a stop:

- `plan_builder.py`, `scripts/ingest_wizard_apply.py`, `scripts/promote_model.py`
- `stingray_master.xlsx` and the raw export
- retained Milestone 1/2/2.1 proof artifacts
- tracked `form-output/runtime/**`, `form-app/**`, dealer code

## 8. Validation

- per-slice RED/GREEN targeted tests;
- focused compiler/relationship/exception/session/server/UI suites;
- Python compilation and JavaScript syntax for changed files;
- broad affected ingest/editor metadata gate;
- workbook package/schema read-only validators;
- fresh current-source compiler artifact audit;
- disposable fixture browser resolve/reopen plus retained-real-run GET-only desktop/mobile smoke when browser/API surfaces change;
- protected-surface hashes/diff before and after;
- full repository suite with baseline-red classification;
- `git diff --check`;
- Fable contract/loop validator;
- bounded independent verifier on the frozen implementation/test/proof snapshot.

## 9. Stop conditions and non-goals

Stop rather than guess if the selected comparator profile is missing, duplicated, internally inconsistent, references a target-unavailable identity, or target trims do not map wholly to LT or LZ. Stop if relationship semantics would require unsupported interior group-member contracts. Stop before changing workbook schema, public interfaces, dependencies, runtime behavior, or protected write/deployment boundaries.

Non-goals: `pass-c-3`, exception resolution on Sean’s behalf, plan/apply approval, workbook mutation, generator/runtime publication, promotion, dealer changes, deletion/remap consumers, or generalizing arbitrary comparator product-rule transfer beyond the explicitly authorized shared profiles.

## 10. Rollback

All implementation changes are source/test/docs edits and are reversible with a normal git restore. Fresh run artifacts remain ignored evidence. No canonical workbook or generated runtime artifact is mutated.
