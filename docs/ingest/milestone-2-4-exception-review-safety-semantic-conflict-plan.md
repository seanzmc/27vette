# Milestone 2.4 — Exception Review Safety and Semantic Conflict Closure

Status: IMPLEMENTED 2026-07-15, corrected by approved Milestone 2.4.1 on 2026-07-16, and extended 2026-07-17 with an audited target-authoritative rejection path for conflicting comparator-only proposals. Milestone 3 remains blocked and unapproved.

Recommended reasoning level: high.

## Goal

Make the typed-exception browser safe and understandable enough for target-workbook authoring decisions, and prevent exact-key-safe but semantically conflicting comparator proposals from becoming canonical rows.

This pass remains read-only toward `stingray_master.xlsx`, the raw order-guide export, generated runtime artifacts, publication, deployment, and dealer submission.

## Diagnosis

Milestone 2.3 produced a deterministic 213-subject queue, but live review of fresh run `20260715-150312-eb8d08` proved that the browser and compiler do not yet provide a safe human approval boundary.

### Misleading review presentation

1. `scripts/corvette_form_generator/ingest/wizard/session.py:1516-1525` labels every manifest row sharing any evidence dependency as `Target workbook state`. Those rows can be `add`, `update`, or `noop`, can belong to an unrelated family, and can be shared context rather than an effect of the card.
2. In the live run, 106 manifest rows appear on multiple cards; one row appears on six cards. Price-rule cards display 42 `rule_mapping` occurrences and two interior occurrences as target state even though those cards do not propose writing those rows.
3. `relationship_compiler.py:432-450` stores comparator proposals as compact signatures. `wizard.js:839-878` renders those signatures under `Proposed canonical rows`, even when one confirmation will create a parent plus multiple member rows. The reviewer cannot see exact sheets, keys, IDs, actions, or companion rows before saving.
4. All 71 comparator proposal subjects carry `candidate:<signature>` dependencies, while `session.py:1502-1507` hydrates raw candidates only for IDs containing `:candidate:`. Their raw-source pane therefore omits the owning candidate evidence.
5. Queue search at `session.py:1600-1607` indexes only subject metadata, not proposed RPOs, exact rows, or evidence text.
6. The family filter names only the subject’s primary family even when one decision writes parent/member rows in multiple families.
7. `mark_not_applicable` accepts any non-empty rationale (`exceptions.py:204-206`). The rationale is audit metadata only; submitting it rejects the complete subject, emits no proposal rows, dispositions all referenced evidence `resolved_not_applicable`, and clears the blocker (`compiler.py:1830-1837`). The current label does not disclose that whole-subject effect or distinguish partial disagreement.
8. `session.py:1208-1252` correctly hides actions that lack a complete target endpoint catalog, but the UI reports only a generic source/tooling message. It does not identify the missing/ambiguous endpoint or prerequisite subject.

### Semantic conflicts not caught by physical-key guards

The current manifest has zero duplicate `(sheet, key)` pairs. That does not prove the proposed business behavior is compatible with retained target rows.

1. The saved GSX `RWH/WKR` confirmation created a new two-member `single_within_group` group while both options already belong to retained four-member `excl_indoor_car_covers`. This is a redundant subgroup constraint.
2. The saved GSX `EDU/EFR` confirmation created a new `required_single_within_group` subgroup while retained `excl_ext_accents` already contains `EDU/EFR/EFY`. The new subgroup is materially narrower because `EFY` can satisfy the retained group but not the new subgroup.
3. The unresolved `5ZB/5ZC/5ZD` proposal partially overlaps retained `excl_center_caps`.
4. Six GSX stripe proposals offer `stripe includes Z15` while current rows already encode `stripe requires Z15`, reverse `Z15 includes stripe`, and for some endpoints reverse `requires`. `compiler.py:1728-1754` matches only the same relationship type, so an incompatible parallel rule can receive a new deterministic ID.
5. Fifteen GSX rule-group proposals overlap retained groups with different member sets. `compiler.py:1996-2004` refuses projection after resolution, leaving the answer pending, but the browser still exposes a confirmation control.
6. `compiler.py:2063-2082` recognizes only exact exclusive-group member-set matches. Subsets, supersets, and partial overlaps receive a new group ID instead of a conflict.

The fresh run and its two saved resolutions are forensic evidence only. Do not recompile, reopen, or continue reviewing it during this pass. Build all mutable tests and browser proofs in disposable roots and create a new proof run after implementation.

## Source-of-truth owner

- Target raw evidence and canonical workbook rows own target product behavior.
- Designated comparator rows are corroborating/proposal evidence only.
- Python may detect equivalence, overlap, incompatibility, and projectability. It may not choose new target business behavior.
- Reviewer choices must map to complete, concrete workbook effects. Partial disagreement stays blocked until represented by a typed edit/split or corrected source/compiler evidence.

Standing constraints from `AGENTS.md` apply, especially §§3–6 and §9. No protected dealer boundary is touched.

## Authorized outcome requiring approval

If approved, implement one read-only exception-review safety pass with these outcomes.

### 1. Semantic-overlap gate

Add a target-scoped semantic-overlap analyzer in `scripts/corvette_form_generator/ingest/wizard/compiler.py`, adjacent to `_comparator_proposal_rows()` and `_merge_manifest_rows()`.

For each comparator proposal, compare against retained and already-derived target rows before exposing a confirming action:

- `exclusive_groups`: classify exact match, subset, superset, partial overlap, or disjoint member set across both current member-family names. Exact represented facts are reconciled without review. Subset/superset/partial overlaps become non-confirmable `semantic_group_overlap` blockers carrying every conflicting group/member row. A reviewer may reject the entire comparator-only proposal and retain the target-authoritative rows; rejection emits no comparator rows and is recorded as `resolved_not_applicable`.
- `rule_groups`: compare source, group type, scopes, and complete member set. Exact represented facts reconcile. Different member sets become non-confirmable `semantic_group_overlap` blockers rather than validator-accepted/pending confirmations. The same explicit whole-proposal rejection path may retain the target-authoritative group unchanged.
- `rule_mapping`: compare the ordered endpoint pair and reverse pair across `requires`, `includes`, `excludes`, and `replaces`. Exact matches reconcile. Different or reverse semantics become non-confirmable `semantic_relationship_conflict` blockers with the existing rows attached. The reviewer may reject the conflicting comparator-only relationship while preserving the independently derived target relationship.
- `price_rules` and defaults: retain the complete existing identity checks. Surface exact existing matches separately and fail closed on incompatible same-condition/target/type/scope overlaps.

No overlap class may automatically merge, replace, delete, or broaden/narrow a target rule. Those require separate target-authoritative decisions.

A resolution may clear readiness only when its semantic preview is conflict-free and the compiler emits the exact previewed effect.

### 2. Exact decision-impact projection

Add a side-effect-free preview path owned by `WizardSessionStore`:

- Input: current `subjectId`, `subjectVersion`, typed action, and typed payload.
- Validate current inputs and finite catalogs exactly as mutation does.
- Stage the candidate resolution in memory.
- Run the compiler without replacing artifacts, writing audit entries, or changing session state.
- Diff baseline versus staged manifest by `(sheet, key)`.
- Return exact `add`, `update`, `noop`, and removed/changed blocker effects, including every parent/member companion row.
- Refuse semantic overlap and return structured conflict rows/prerequisites.

Expose one strict local endpoint before the generic session route:

`POST /api/wizard/sessions/<run-id>/exceptions/preview`

This is a local review API only. It confers no plan, write, publication, or deployment authority.

### 3. Correct display contract

Replace the current broad evidence join with four explicitly different surfaces:

1. `sourceEvidence` — all owning raw candidate rows/cells.
2. `existingWorkbookRows` — rows physically present in the current canonical workbook and relevant to the exact proposal endpoints/identity.
3. `alreadyDerivedRows` — current manifest rows independently derived without this decision.
4. `decisionEffect` — exact physical rows the selected action would add/update/noop, populated from the preview response.

Shared evidence that is not written by the decision belongs in a separately labeled collapsed context panel. Never label it target workbook state.

Each row view must show:

- target model;
- workbook sheet and family;
- action;
- stable key/ID;
- customer-relevant RPO endpoints/members;
- scopes and price where applicable;
- whether the row is existing, already derived, or conditional on this decision.

Group cards must show parent and all member rows together as one effect. Relationship cards must show direction in plain language. Price cards must show condition, target, rule type, target-owned price, and body/trim/variant scope.

### 4. Concrete controls and filters

- Replace `Record not applicable` with `Reject entire proposal — write no rows`.
- Before submission, state the complete rejected effect. Rationale remains optional audit detail or a finite concrete reason plus optional note; it is never interpreted as a partial edit.
- If only one member, direction, scope, or field is disputed, offer no reject-as-partial shortcut. Keep the subject blocked and identify the required typed correction/source change.
- Replace raw family/reason filters with reviewer-facing filters for target model, decision type, exact affected workbook sheet(s), resolution/prerequisite state, and RPO search.
- Keep internal reason/family values available only in an advanced/debug detail.
- Search proposed RPOs, exact row values, raw evidence copy, and stable IDs.
- For non-actionable cards, name every missing/ambiguous endpoint and link or identify the prerequisite subject where one exists.

### 5. Existing resolutions and historical runs

- Do not mutate run `20260715-150312-eb8d08`.
- Add fixture coverage proving old overlapping confirmations cannot be silently consumed under the new compiler policy.
- A copied historical run may report the old resolution as pending/conflicted; it must not add a parallel subgroup or incompatible direct rule.
- Generate a new run ID for all final current-source proof.

## Definition of done

1. No card displays broad evidence fan-out as existing workbook state.
2. Comparator cards hydrate the owning raw source rows.
3. Every actionable card can produce an exact, side-effect-free physical-row preview before save.
4. Previewed physical effects equal post-resolution compiler effects by `(sheet, key, action, values)`.
5. Whole-proposal rejection explicitly writes zero rows and cannot be mistaken for a partial correction.
6. Subset/superset/partial exclusive-group overlaps are non-confirmable blockers.
7. Conflicting or reverse relationship semantics are non-confirmable blockers.
8. Rule-group member-set mismatches are non-confirmable before mutation, not saved-and-pending afterward.
9. Exact represented comparator facts reconcile without duplicate review.
10. Search finds cards by RPO and source/effect text.
11. The fresh current-source queue explains every changed subject count/disposition relative to Milestone 2.3.
12. `stingray_master.xlsx`, raw source, generated runtime contracts, `form-app/data.js`, publication, deployment, and dealer surfaces remain byte-identical.
13. Milestone 3 remains blocked and unapproved.

## Exact files expected to change

Implementation:

- `scripts/corvette_form_generator/ingest/wizard/compiler.py`
- `scripts/corvette_form_generator/ingest/wizard/session.py`
- `scripts/ingest_wizard_server.py`
- `visualizer/ingest-wizard/index.html`
- `visualizer/ingest-wizard/wizard.js`
- `visualizer/ingest-wizard/wizard.css`

Tests:

- `tests/test_ingest_wizard_canonical_compiler.py`
- `tests/test_ingest_wizard_exception_flow.py`
- `tests/test_ingest_wizard_server_milestone2.py`
- `tests/test_ingest_wizard_ui_milestone2.py`

Docs/closure:

- `docs/ingest/milestone-2-4-exception-review-safety-semantic-conflict-plan.md`
- `docs/ingest/README.md`
- `docs/ingest/canonical-row-compiler-exception-queue-design.md`
- a new Fable receipt only after implementation and independent verification
- `fable5loop/STATE.md` only after implementation

No new dependency or workbook schema is approved.

## TDD implementation sequence

### Task 1 — RED semantic-overlap fixtures

Add failing canonical-compiler tests for:

- subset, superset, partial-overlap, and exact-match exclusive groups;
- the retained `RWH/WKR` and `EDU/EFR/EFY` shapes;
- `5ZB/5ZC/5ZD` versus retained center-cap members;
- same-direction different-type and reverse-direction relationship conflicts;
- stripe `includes Z15` versus retained `requires`/reverse rows;
- rule-group same-source/scope with differing member sets;
- exact represented facts reconciling without a queue subject.

Run the focused tests and require RED on the current behavior.

### Task 2 — GREEN semantic-overlap gate

Implement the analyzer in `compiler.py`. Keep it model-general and driven by workbook rows, emitted rows, proposal semantics, and existing metadata. Do not add RPO allowlists or GSX-specific exceptions.

Require conflict subjects to include structured conflicting rows, overlap kind, affected sheets, and non-projectable action state.

Run Task 1 tests to GREEN, then the complete canonical-compiler and relationship-compiler suites.

### Task 3 — RED display and preview contracts

Add failing session/server tests requiring:

- separate existing/derived/shared/effect fields;
- correct candidate hydration for `candidate:<signature>` dependencies;
- RPO/evidence search;
- exact affected-sheet metadata;
- structured prerequisite blockers;
- strict preview request fields;
- preview byte-preservation of every run artifact and audit file;
- preview/current-input freshness and subject-version refusal;
- preview effect equality with a subsequent disposable resolve/recompile.

### Task 4 — GREEN side-effect-free preview service

Implement one shared resolution-validation/staging helper so preview and mutation cannot drift. Preview must call the production compiler in memory and diff physical workbook rows; it must not duplicate product logic in `session.py` or JavaScript.

Add the strict preview route before the generic session route. Unknown keys and stale inputs fail closed.

### Task 5 — RED then GREEN browser rewrite

Replace the four ambiguous panels and raw reason/family controls. Add source-level assertions only as supplemental tests; the main proof must use an executable browser against a disposable root.

Require:

- exact physical-row preview before confirm/reject submission;
- explicit whole-proposal rejection copy;
- no partial-reject implication;
- conflict/prerequisite cards with no mutation controls;
- human-readable decision/sheet filters;
- RPO search;
- desktop and 390px layouts with no overflow;
- keyboard operation, focus preservation, live status, and zero console/network errors.

### Task 6 — Fresh real-source proof

Create a new run from the current source and current workbook. Do not overwrite Milestone 2.3 or the fresh forensic run.

Mechanically audit:

- every proposal against retained and derived semantic effects;
- exact-key uniqueness and semantic-overlap classifications;
- changed queue counts/reasons with an explained migration ledger;
- complete raw evidence and decision impact on representative section, identity, relationship, rule-group, exclusive-group, and price cards;
- preview-to-resolve equality in a disposable copy only;
- retained real run GET-only resume/filter/search smoke;
- deterministic recompilation and graph validation;
- protected-surface hashes.

### Task 7 — Independent verification and closure

Run an independent exact-current code/artifact/UI review. Close this plan, `docs/ingest/README.md`, the production design, Fable receipt, and `STATE.md` only after the verifier passes without edits.

No commits, pushes, or history rewrites unless the user separately requests them.

## Validation plan

Targeted first:

```sh
PYTHONPATH=scripts .venv/bin/python -m pytest \
  tests/test_ingest_wizard_canonical_compiler.py \
  tests/test_ingest_wizard_exception_flow.py \
  tests/test_ingest_wizard_server_milestone2.py \
  tests/test_ingest_wizard_ui_milestone2.py -q
node --check visualizer/ingest-wizard/wizard.js
```

Then run the complete ingest-wizard Python gate from the repository README, Python compilation checks for changed modules, JavaScript syntax, workbook package/schema validation, and the serialized Node gate selected by `27vette-gate`.

Browser proof:

- disposable-root preview → resolve → recompile → reopen for every live action family;
- retained-real-run GET-only resume/filter/pagination/search/evidence smoke;
- desktop and 390px geometry/overflow checks;
- zero console/network errors;
- no mutation of retained proof or forensic runs.

Protected surfaces:

- hash `stingray_master.xlsx`, the raw source export, `form-app/data.js`, and current runtime contracts before implementation/proof;
- require identical hashes afterward;
- finish with `git diff --check` and `git status --short --branch`.

## Allowed drift

Allowed only after implementation:

- new conflict reason codes and structured preview/display fields;
- exception totals/actionability changing because exact represented facts reconcile and semantic conflicts become non-confirmable;
- new run-scoped proof artifacts under a new run ID;
- browser copy/layout needed for the approved review contract.

Not allowed:

- workbook, raw-source, generated runtime, registry, publication, deployment, or dealer changes;
- hidden model/RPO allowlists;
- automatic group merge/replacement;
- target business decisions derived solely from comparator evidence;
- old proof-run mutation;
- plan/write readiness.

## Companion-file impact

- Generated contracts: inspected; no change allowed.
- Count/reason-sensitive ingest tests and docs: update to the new exact queue with a reasoned migration ledger.
- Runtime consumers: not applicable; no runtime artifact or browser form behavior changes.
- Workbook schema/data: not applicable; byte-identical requirement.
- Dealer submission: untouched.
- README/design/Fable route map: update on implementation so Milestone 3 cannot be reached through the unsafe review path.

## Rollback

Revert only the scoped code/test/docs changes. Remove only the new disposable proof run after preserving its receipt if implementation had reached verification. Historical and forensic runs remain unchanged. No workbook rollback is required because this milestone is read-only.

## Approval gate

Milestone 2.4's semantic-conflict and exact-preview machinery was implemented in commit `302136b`; Sean approved the Milestone 2.4.1 decision-first correction on 2026-07-15 and authorized execution on 2026-07-16. The combined work still requires one independent closure review. It does not authorize Milestone 3, `pass-c-3`, workbook writes, generation, publication, promotion, deployment, or dealer changes.
