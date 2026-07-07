# Pass B.7 — ref-only rows in section assignment

Date: 2026-07-07
Status: DRAFT — awaiting Sean approval before implementation.
Parent: `docs/ingest/ingest-wizard-end-to-end-completion-spec.md` Pass B review stage.

## Diagnosis

Current wizard behavior incorrectly routes `rowKind == "ref_only"` rows:

- `WizardSessionStore.review_queue()` only sends `rowKind == "orderable"` candidates to the Section assignment lane (`session.py`).
- The Standard equipment lane is the only lane that currently surfaces most ref-only rows, and it can only save `include_standard_equipment` / `exclude_row` decisions.
- `decisions.completeness()` only counts orderable candidates for mandatory Section/Price blockers.
- `plan_builder.py` has two separate write paths:
  - orderable rows are written from Section + Price decisions and can carry reviewer section/selectable/active flags;
  - ref-only Standard equipment inclusions become non-selectable rows with `section_id: None`.

That means ref-only RPO rows cannot currently be assigned to real workbook sections, cannot be made selectable through the section controls, and cannot express the case Sean identified: ref-only rows that are real option rows and not necessarily standard equipment.

Evidence inspected:

- `scripts/corvette_form_generator/ingest/wizard/session.py` `review_queue()` lines 490-513.
- `scripts/corvette_form_generator/ingest/wizard/decisions.py` `candidate_is_availability_row()` and `completeness()` lines 144-151 and 578-667.
- `scripts/corvette_form_generator/ingest/wizard/plan_builder.py` stage-2 option and standard-equipment paths lines 505-675.
- `visualizer/ingest-wizard/wizard.js` Section controls already support section assignment plus `not selectable` / `inactive` flags; Standard equipment controls only support include/exclude.
- Existing tests in `tests/test_ingest_wizard_plan.py`, `tests/test_ingest_wizard_decisions.py`, and `tests/test_ingest_wizard_session.py` cover the current orderable-only and standard-equipment-only behavior.

Risk: medium for Pass B/C review correctness; tooling-only. No workbook write, generated artifact, `form-app/`, or dealer-submission change.

## Source-of-truth decision

This is wizard review/planning logic, not a workbook data correction.

Workbook source remains authoritative for the final section IDs and selectable flags, but the wizard must let the reviewer author those decisions for ref-only rows before Pass C/D planning.

## Exact files expected to change

- `scripts/corvette_form_generator/ingest/wizard/session.py`
- `scripts/corvette_form_generator/ingest/wizard/decisions.py`
- `scripts/corvette_form_generator/ingest/wizard/plan_builder.py`
- `visualizer/ingest-wizard/wizard.js` only if label/help text needs to stop saying ref-only rows are only Standard equipment.
- `tests/test_ingest_wizard_decisions.py`
- `tests/test_ingest_wizard_plan.py`
- possibly `tests/test_ingest_wizard_server_pass_b.py` or `tests/test_ingest_wizard_session.py` for HTTP/session coverage.
- This spec file, for closeout.
- Route-map docs if wording would otherwise stay stale:
  - `docs/ingest/README.md`
  - `docs/ingest/ingest-wizard-end-to-end-completion-spec.md`
  - `Order-Guide_IngestPrompt.md`

## Implementation plan

1. Define a shared predicate/name in wizard logic for candidates that need section review:
   - `orderable` rows;
   - `ref_only` rows in the selected model scope.

2. Change Section assignment queue:
   - include both orderable and ref-only scoped rows;
   - preserve existing skip behavior (`exclude_row` + `not_needed`);
   - keep skipped rows suppressed from later non-section lanes per B.6.

3. Change Standard equipment queue:
   - stop treating Standard equipment as the only owner for all ref-only rows;
   - show only rows that still need a Standard-equipment-specific decision, if any, after section assignment (for example rows assigned to workbook sections with `standardBehavior`), or keep the lane as compatibility-only for existing standard-equipment decisions without making it the primary route.

4. Change completeness:
   - Section blockers count ref-only candidates as requiring a section decision.
   - Price blockers stay orderable-only; ref-only rows do not owe a price decision in this pass.
   - Status nuance can remain orderable-only unless a ref-only row has status ambiguity that must be modeled in a later pass.

5. Change plan building:
   - Ref-only rows with approved Section assignment write normal option rows using `refOnlyRpo` as `rpo`.
   - Section payload owns `section_id`, `selectable`, and `active` just like orderable rows.
   - No price decision is required; price writes as blank/`None` unless a future pass adds explicit price review for ref-only rows.
   - Existing Standard equipment include decisions remain backward-compatible for rows without section decisions, but section decisions should be the preferred source.

6. Update UI copy so reviewers understand:
   - Section assignment includes orderable and ref-only RPO rows.
   - Use `not selectable` for display/reference-only rows.
   - Use `Skip — don't carry over` only for rows not intended to become workbook rows.

## Companion-file impact

- Workbook: inspected/no-change; no workbook write in this pass.
- Generated artifacts: not applicable; no regeneration expected.
- Runtime app/dealer: not applicable; wizard-only.
- Tests: update focused Pass B/C wizard tests.
- Docs/specs: update this spec at closeout; update route-map wording if stale.
- Skills: update the ingest wizard review skill if implementation discovers a durable pitfall.

## Constraints

Standing constraints from `AGENTS.md` apply, especially source-of-truth boundaries, generated artifacts not being source, and dealer-submission protection.

Pass-specific constraints:

- Do not start Pass D workbook apply.
- Do not write `stingray_master.xlsx`.
- Do not touch `form-output/` or `form-app/data.js`.
- Do not invent a new decision lane or new vocabulary if Section assignment can own the decision.
- Keep existing section skip reversible and non-destructive.

## Validation plan

Run after implementation:

```sh
.venv/bin/python -m pytest \
  tests/test_ingest_wizard_decisions.py \
  tests/test_ingest_wizard_server_pass_b.py \
  tests/test_ingest_wizard_plan.py \
  tests/test_ingest_wizard_session.py -q
node --check visualizer/ingest-wizard/wizard.js
git diff --check
git status --short --branch
```

If `wizard.js` text only changes, `node --check` is enough; no browser smoke required unless controls/rendering code changes.

## Approval question

Approve Pass B.7 as scoped above?

Recommendation: approve. It is the smallest tooling-only correction that makes ref-only rows section-authorable without changing the workbook, generated runtime data, or Pass D boundaries.
