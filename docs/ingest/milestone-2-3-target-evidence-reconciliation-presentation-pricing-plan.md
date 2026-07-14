# Milestone 2.3 — Target Evidence Reconciliation and Presentation Pricing

Status: IMPLEMENTING — user-authorized 2026-07-14

## Diagnosis

Milestone 2.2 safely retained 371 typed blockers, but current-source audit found that several blocker classes overstate product uncertainty:

1. comparator proposals are emitted before the final retained canonical rows are reconciled, so an exact existing target/default/price/group row can be both retained and separately queued;
2. target options with a unique designated-comparator RPO placement still require two-model section consensus, leaving Grand Sport X rows such as `DX4` falsely sectionless;
3. an ambiguous multi-row target price is not reconciled against a canonical base price plus already-authored conditional price rules;
4. target raw `standard` statuses can remain attached to inactive scaffold option rows;
5. Z25's raw product-total price is currently assigned to the option row even though the canonical Grand Sport presentation allocates that charge to the required EL9 interior. The current candidate therefore contains two `$1,995` charge rows.

Evidence:

- `grandSport_options!68`: `DX4 -> sec_gsha_001`.
- Raw `Equipment Groups 3!129`: GSX `DX4`, available on all six variants, with target text requiring `Z15`.
- Raw `Mechanical 3!6` and `!10`: GSX `J57` and `J6D` are standard on all six variants.
- Raw Price Schedule rows 166–171: `BC4`/`BCP`/`BCS` are `$595` with `B6P`/`ZZ3` and `$695` on coupes without `B6P`.
- Existing canonical `price_rules!38:43` already model those six conditional `$595` rules.
- Existing `default_selection_rules!22:23` and `zr1_options!63` / `zr1x_options!191` already own R8E defaults and prices `$3,000` / `$2,600`; the current queue nevertheless emits two comparator default proposals.
- Current run `20260714-133532-f9811b` emits both GSX EL9 interiors at `$1,995` and Z25 at `$1,995`. Grand Sport canonically uses EL9 `$1,995` plus auto-only Z25 `$0`.

## Authorized outcome

User decisions supplied 2026-07-14:

- Grand Sport X engine-cover compatibility and option-triggered pricing match Grand Sport.
- Grand Sport X `J57` is standard and `J6D` is its standard/default caliper selection.
- ZR1 R8E is `$3,000`; ZR1X R8E is `$2,600`.
- Intentional package/interior price allocation must preserve customer-visible pricing and avoid a surprise or duplicate final-summary charge.

## Definition of done

1. A comparator fact is not queued when an exact target/global canonical row already represents it. Evidence links and comparator dispositions identify the retained row.
2. A target RPO may use the selected comparator's section only when the comparator has exactly one active occurrence with one valid canonical section. Missing, duplicate, conflicting, inactive, or invalid placement fails closed.
3. GSX `DX4` compiles to `sec_gsha_001`; the other exact comparator-placement matches compile without review. No no-RPO or comparator-absent row is guessed.
4. Ambiguous target option prices compile only when one raw target price equals the selected comparator base price and every other raw price is represented by exact target/global canonical conditional price rules. Otherwise `unresolved_price_scope` remains.
5. GSX `BC4`/`BCP`/`BCS` use target-backed base `$695` plus retained `$595` `B6P`/`ZZ3` overrides. Their direct compatibility rows and LS6 exclusive group remain workbook-owned.
6. Raw available/standard status establishes an active selected-target option even when a stale inactive scaffold row exists. Unavailable-only rows are not promoted by this rule.
7. GSX J57/J6D compile active and non-selectable from standard statuses, with an approved J6D default rule and no duplicate comparator question.
8. ZR1/ZR1X R8E retain existing target prices and `always` defaults without comparator questions.
9. GSX Z25 retains raw target `$1,995` as total-price evidence while emitting auto-only Z25 at `$0` and EL9 at `$1,995`; a profile allocation guard fails closed if the target total and canonical allocation disagree.
10. Raw relationship text remains evidence. Runtime-oriented comparator semantics are accepted only when represented by an exact existing target/global row or an explicitly authorized profile; broader comparator copying remains prohibited.
11. Regenerated proof reports the new exact exception total and explains every reduction by disposition. Byte stability, graph validity, authority bindings, browser lifecycle, and protected-surface checks remain green.

## Expected files

Implementation/tests:

- `scripts/corvette_form_generator/ingest/wizard/compiler.py`
- `scripts/corvette_form_generator/ingest/wizard/profile_compiler.py`
- `scripts/corvette_form_generator/ingest/wizard/relationship_compiler.py` only if represented-fact reconciliation belongs at relationship construction
- `tests/test_ingest_wizard_canonical_compiler.py`
- `tests/test_ingest_wizard_profile_compiler.py`
- fixture updates only where a focused test needs the existing contract shape

Docs/receipts:

- this plan
- `docs/ingest/README.md`
- `docs/ingest/canonical-row-compiler-exception-queue-design.md`
- a new Fable receipt under `fable5loop/runs/`
- `fable5loop/STATE.md`

## Preserved boundaries

- No write to `stingray_master.xlsx` or the raw export.
- No `pass-c-3` plan, apply, runtime publication, registry promotion, deployment, or dealer-submission change.
- No general rule that all comparator facts are target facts.
- No direct-rule expansion for multi-interior one-of relationships.
- No suppression of independent placement, status, price, or catalog defects.

## Validation

- RED then GREEN focused tests for each reconciliation contract.
- Full ingest-wizard Python gate.
- Current-source compile to a new retained run; independent reason-count and row-value audit.
- Same-run byte-stability check and artifact graph validation.
- Workbook package/schema validation and Python compileall.
- Serialized Node gate; restore any generated protected churn.
- Desktop/mobile exception browser proof and disposable lifecycle proof if queue/browser-visible counts or cards change.
- Independent exact-current code and artifact review.
- Fable validator and contract test.

## Rollback

Revert only the scoped compiler/test/docs changes and retain Milestone 2.2 run `20260714-133532-f9811b` unchanged as the before-state. No workbook rollback is required because this pass is read-only.
