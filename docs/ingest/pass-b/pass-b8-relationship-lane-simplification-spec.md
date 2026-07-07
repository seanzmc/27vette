# Pass B.8 — relationship lane simplification

Date: 2026-07-07
Status: Implemented and verified 2026-07-07.
Parent: `docs/ingest/ingest-wizard-end-to-end-completion-spec.md` Pass B review stage.

## Diagnosis

The Relationships review lane is harder to use than the workbook rule surface requires:

- `visualizer/ingest-wizard/wizard.js` exposes ten relationship-kind choices in the dropdown.
- `scripts/corvette_form_generator/ingest/wizard/plan_builder.py` maps those choices into only three workbook rule types: `requires`, `includes`, and `excludes`.
- Four UI choices (`deletes`, `replaces`, `upgradeable_to`, `other`) are not currently mappable by Pass C and can create `relationship_unmappable` plan gaps if approved.
- The generic group-lane resolution dropdown (`Approve / Hold / Skip`) appears in Relationships even though normal relationship authoring should mean "save this rule for the plan".
- The normal relationship form shows `record as business question`; that is useful for special reconciliation/open-question records, but it creates uncertainty when the reviewer is trying to author rules.

Evidence inspected:

- `visualizer/ingest-wizard/wizard.js` relationship kind constants, group form, hint prefill, and `collectGroupDecision()`.
- `scripts/corvette_form_generator/ingest/wizard/plan_builder.py` `RELATIONSHIP_KIND_TO_RULE_TYPE` and rule_mapping emission.
- `scripts/corvette_form_generator/ingest/wizard/hints.py` phrase scanner labels.
- Existing tests in `tests/test_ingest_wizard_plan.py` for relationship-to-rule emission.

Risk: low/medium; wizard-review UX only. The change is intended to reduce false choices without changing workbook rule semantics.

## Source-of-truth decision

Workbook rule mapping remains the source of truth for what the apply plan can write: `requires`, `includes`, and `excludes` rule rows.

The wizard UI should present only those workbook-safe authoring choices for new relationship decisions. Existing/stored alias values should remain readable and normalizable so old decisions and phrase hints do not break.

## Exact files expected to change

- `visualizer/ingest-wizard/wizard.js`
- `visualizer/ingest-wizard/wizard.css` if needed for clearer rule-choice controls
- Focused test(s) for UI contract/static behavior
- This spec file at closeout
- Route-map docs if stale:
  - `docs/ingest/README.md`
  - `docs/ingest/ingest-wizard-end-to-end-completion-spec.md`
  - `Order-Guide_IngestPrompt.md`

No workbook, generated artifact, runtime app, or dealer-submission file should change.

## Implementation plan

1. Replace the relationship-kind dropdown with three explicit workbook-safe choices:
   - Requires (`kind: "requires"`)
   - Includes / auto-adds (`kind: "includes"`)
   - Not available with (`kind: "not_available_with"`)

2. Hide/remove the normal relationship-lane resolution dropdown. New relationship saves default to:
   - `action: "create_relationship_candidate"`
   - `resolution: "approved_for_plan"`

3. Remove `record as business question` from the normal relationship authoring form. Existing `needs_product_decision` records must remain displayable/edit-safe where they already exist, but the normal relationship flow should focus on rule authoring.

4. Normalize hint/legacy kinds before prefill/save:
   - `only_available_with`, `requires_additional_equipment` -> `requires`
   - `included_with` -> `includes`
   - `not_available_with` -> `not_available_with`
   - unmappable kinds should not become approved rules by accident.

5. Make hints easier to use:
   - keep hint rows clickable/prefillable;
   - labels should use customer/workbook-authoring language rather than raw internal enum names.

6. Add focused verification that the UI exposes only the three rule-authoring kinds and does not show the generic relationship resolution/business-question controls in the normal form.

## Companion-file impact

- Workbook: n/a; no workbook write.
- Generated artifacts: n/a; no regeneration.
- Runtime app/dealer: n/a; wizard-only.
- Plan builder: inspected/no-change expected unless normalization needs backend support.
- Tests: add/update focused UI contract check; run relevant existing relationship plan tests.
- Docs/specs: close this spec and update route-map wording if stale.

## Constraints

- Do not add Pass D apply behavior.
- Do not write `stingray_master.xlsx`.
- Do not touch `form-output/`, `form-app/data.js`, or dealer-submission behavior.
- Do not introduce new relationship vocabularies that the workbook cannot write.
- Keep existing stored decisions readable; this pass simplifies new authoring.

## Validation plan

Run after implementation:

```sh
.venv/bin/python -m pytest tests/test_ingest_wizard_plan.py tests/test_ingest_wizard_ui_relationships.py -q
node --check visualizer/ingest-wizard/wizard.js
git diff --check
git status --short --branch
```

If docs beyond this spec change, review those diffs directly.

## Closeout

Implemented behavior:

- Relationship authoring now shows three explicit workbook-safe choices: Requires, Includes / auto-adds, and Not available with.
- New relationship saves default to `resolution: "approved_for_plan"`; the normal relationship form no longer shows the generic Approve/Hold/Skip dropdown.
- The normal relationship form no longer shows `record as business question`; existing/open-question relationship records remain displayable as report-only decisions.
- Hint and legacy aliases normalize before save: `only_available_with` and `requires_additional_equipment` become `requires`; `included_with` becomes `includes`.
- Unmappable hint kinds no longer become approved rules by accident; the reviewer must choose one of the three rule types before save.

Validation:

```sh
.venv/bin/python -m pytest tests/test_ingest_wizard_ui_relationships.py tests/test_ingest_wizard_plan.py tests/test_ingest_wizard_hints.py tests/test_ingest_wizard_decisions.py tests/test_ingest_wizard_server_pass_b.py -q && node --check visualizer/ingest-wizard/wizard.js && git diff --check && git status --short --branch
# 59 passed in 3.43s; node syntax and diff whitespace checks passed; git status showed only expected B.8 files.
```

Preserved surfaces: no workbook writes, no generated artifacts, no `form-app/` runtime changes, no dealer-submission changes, and no Pass D apply path.
