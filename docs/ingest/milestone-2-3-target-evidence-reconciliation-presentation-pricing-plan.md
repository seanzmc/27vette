# Milestone 2.3 — Target Evidence Reconciliation and Presentation Pricing

Status: COMPLETED AND INDEPENDENTLY VERIFIED 2026-07-15

## Diagnosis

Milestone 2.2 safely retained 371 typed blockers, but current-source audit found that several blocker classes overstate product uncertainty:

1. comparator proposals are emitted before the final retained canonical rows are reconciled, so an exact existing target/default/price/group row can be both retained and separately queued;
2. target options with a unique designated-comparator RPO placement still require two-model section consensus, leaving Grand Sport X rows such as `DX4` falsely sectionless;
3. an ambiguous multi-row target price is not reconciled against a canonical base price plus already-authored conditional price rules;
4. target raw `standard` statuses can remain attached to inactive scaffold option rows;
5. Z25's raw product-total price is currently assigned to the option row even though the canonical Grand Sport presentation allocates that charge to the required EL9 interior. The current candidate therefore contains two `$1,995` charge rows;
6. the run incorrectly classified `Equipment Groups 1–5` as canonical option sources. Those sheets duplicate Interior/Exterior/Mechanical rows and add ambiguous variant-status symbols without adding canonical output;
7. raw interior ancillary-option prose was incorrectly translated toward direct `rule_mapping` rows. The existing LT/LZ interior tables already own compatibility through unique `interior_id` rows and their `Seat`, `Suede`, `Stitch`, `Two Tone`, and `included_option_id` fields;
8. source `standard` status was incorrectly treated as non-selectable even when the canonical section is required and single-select.

Evidence:

- `grandSport_options!68`: `DX4 -> sec_gsha_001`.
- Raw `Mechanical 3!6` and `!10`: GSX `J57` and `J6D` are standard on all six variants.
- Raw Price Schedule rows 166–171: `BC4`/`BCP`/`BCS` are `$595` with `B6P`/`ZZ3` and `$695` on coupes without `B6P`.
- Existing canonical `price_rules!38:43` already model those six conditional `$595` rules.
- Existing `default_selection_rules!22:23` and `zr1_options!63` / `zr1x_options!191` already own R8E defaults and prices `$3,000` / `$2,600`; the current queue nevertheless emits two comparator default proposals.
- Current run `20260714-133532-f9811b` emits both GSX EL9 interiors at `$1,995` and Z25 at `$1,995`. Grand Sport canonically uses EL9 `$1,995` plus auto-only Z25 `$0`.
- Rebaseline `20260714-164519-b3adb9` proves that excluding Equipment Groups removes 39 exceptions without changing the 5,993-row canonical manifest.
- The remaining 39 `unresolved_relationship_identity` subjects all trace to `Interior 3` / `Interior 5` ancillary rows (`R6X`, `AUP`, `TU7`, `N26`/`N2Z`, `36S`/`37S`/`38S`). Grand Sport and Z06 contain no corresponding direct `rule_mapping` rows; LT/LZ interior metadata contains the exact seat/suede/stitch/two-tone/included-option representation.

## Authorized outcome

User decisions supplied 2026-07-14:

- Grand Sport X engine-cover compatibility and option-triggered pricing match Grand Sport.
- Grand Sport X `J57` is standard and `J6D` is its standard/default caliper selection.
- ZR1 R8E is `$3,000`; ZR1X R8E is `$2,600`.
- Intentional package/interior price allocation must preserve customer-visible pricing and avoid a surprise or duplicate final-summary charge.
- Canonical raw candidate processing uses only `Interior N`, `Exterior N`, and `Mechanical N`, plus `Price Schedule` for price evidence. Equipment Groups, Standard Equipment, and Color and Trim are excluded.
- A standard/default-selected option in a required single-select section remains selectable; GSX `J6D` must emit `selectable=true`.
- This milestone is an explicitly targeted intake profile for Grand Sport X, ZR1, and ZR1X using the approved Grand Sport/Z06 comparator sources. It is not represented as a generally model-agnostic compiler.

## Definition of done

1. A comparator fact is not queued when an exact target/global canonical row already represents it. Evidence links and comparator dispositions identify the retained row.
2. A target RPO may use the selected comparator's section only when the comparator has exactly one active occurrence with one valid canonical section. Missing, duplicate, conflicting, inactive, or invalid placement fails closed.
3. GSX `DX4` compiles to `sec_gsha_001`; the other exact comparator-placement matches compile without review. No no-RPO or comparator-absent row is guessed.
4. Ambiguous target option prices compile only when either (a) explicit target-model/trim qualification leaves one exact target-owned price, or (b) one raw target price equals the selected comparator base price and every other target-applicable raw price is represented by exact target/global canonical conditional price rules. Target-inapplicable price rows are dispositioned but never become target-owned values. Otherwise `unresolved_price_scope` remains.
5. GSX `BC4`/`BCP`/`BCS` use target-backed base `$695` plus retained `$595` `B6P`/`ZZ3` overrides. Their direct compatibility rows and LS6 exclusive group remain workbook-owned.
6. Raw available/standard status establishes an active selected-target option even when a stale inactive scaffold row exists. Unavailable-only rows are not promoted by this rule.
7. GSX J57/J6D compile active from standard statuses. J6D compiles `selectable=true` because its canonical caliper section is required and single-select; J57 remains governed by its own section contract. The approved J6D default emits with no duplicate comparator question.
8. ZR1/ZR1X R8E retain existing target prices and `always` defaults without comparator questions.
9. GSX Z25 retains raw target `$1,995` as total-price evidence while emitting auto-only Z25 at `$0` and EL9 at `$1,995`; a profile allocation guard fails closed if the target total and canonical allocation disagree.
10. Raw relationship text remains evidence. Runtime-oriented comparator semantics are accepted only when represented by an exact existing target/global row or an explicitly authorized profile; broader comparator copying remains prohibited.
11. Regenerated proof reports the new exact exception total and explains every reduction by disposition. Byte stability, graph validity, authority bindings, browser lifecycle, and protected-surface checks remain green.
12. The profiler recommends `exclude` for every options matrix except `Interior N`, `Exterior N`, and `Mechanical N`; the session API rejects attempts to assign another matrix the Options role, and the browser does not offer that writable choice.
13. Interior ancillary compatibility represented by LT/LZ metadata emits `compiled_profile_effect`, no direct relationship rows, and no one-of/group blockers. Unrepresented interior prose still fails closed.
14. Existing canonical price rules with a broader scope represent narrower comparator proposals only when condition RPO, target RPO, rule type, and price are exact.

## Expected files

Implementation/tests:

- `scripts/corvette_form_generator/ingest/wizard/compiler.py`
- `scripts/corvette_form_generator/ingest/wizard/profile_compiler.py`
- `scripts/corvette_form_generator/ingest/wizard/relationship_compiler.py` only if represented-fact reconciliation belongs at relationship construction
- `scripts/corvette_form_generator/ingest/wizard/profiler.py`
- `scripts/corvette_form_generator/ingest/wizard/session.py`
- `visualizer/ingest-wizard/wizard.js`
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
- No one-of relationship compiler for metadata-owned interior compatibility; LT/LZ interior rows remain the sole canonical representation.
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

## Completion evidence — 2026-07-15

- Exact-current retained run: `form-output/ingest-wizard/20260715-035235-12e239`.
- Manifest: 5,999 rows (5,994 ready, 5 blocked), with zero duplicate physical keys, invalid action/status values, malformed dependency fingerprints, or conflicting evidence identities.
- Queue: 213 unique open subjects; the API projects 203 as reviewer-answerable and 10 as missing-source/tooling. Five GSX `unresolved_price_scope` subjects remain: `CFV` and `VPW` have only other-model-qualified price evidence; `ROY`, `ROZ`, and `STZ` retain unallocated GSX adjustments plus generic prices. `unresolved_relationship_identity` is now zero.
- Source ledger: 11,297 target-scoped features partitioned into 3,970 compiled, 906 exception-open, 508 resolved non-workbook facts, and 5,913 not applicable.
- Relationship and price-accounting proof: all 447 compiled relationship features have a material manifest row carrying every declared target candidate and phrase dependency. Shared interior-code prose binds only to exact LT/LZ `interior_id` rows whose Seat/Suede/Stitch/Two Tone metadata carries the source RPO and fails closed when no row matches. All 330 compiled target-price features have a material target row carrying their raw price dependency. Comparator price reconciliation requires complete condition RPO, target RPO, numeric price, override rule type, body, trim, and variant identity per source qualifier clause; same-valued applicable target price rows no longer become false ambiguities.
- Target outcomes: GSX J57/J6D standard; J6D selectable/default; ZR1/ZR1X J6D/719/EFR/T0E defaults; R8E 3000/2600; target-owned N2Z 895/selectable on both Z targets; GSX Z25 price 0, `selectable=false`, `display_behavior=auto_only`; both EL9 interiors price 1995 and require `opt_z25_001`.
- Same-run recompilation is byte-identical across the manifest, queue, resolutions, comparator evidence, compile report, and session artifacts.
- Third-repair affected gate: 71 passed plus 7 subtests; complete ingest gate: 314 passed plus 18 subtests. Workbook package/schema validation, Python compileall, JavaScript syntax, 267 mapped Node tests, 80 metadata Python tests, browser resume/role/filter proof, and protected-surface hashes passed.
- Final exact-current verifier `deleg_fa5626eb` passed both source-boundary and artifact lanes with frozen implementation/test/artifact sentinels and no edits.
- Detailed evidence: `fable5loop/runs/2026-07-15-milestone23-target-evidence-presentation-pricing/`.
- Preserved boundary: no workbook/source mutation, `pass-c-3`, runtime publication, registry promotion, deployment, or dealer change.
- Residual risk: none implied for Milestone 2.3. The 213 retained subjects remain explicit next-pass inputs; Milestone 3 remains blocked and unapproved.
