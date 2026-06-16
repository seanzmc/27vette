# Rule Mapping Cleanup Candidates

## Prompt:

- So in the interest of my main goal of cleaning up the data rows in the workbook so that columns are not just processed so they validate a test, what columns in
  the rule-mapping sheets could be safely retired because they do not contribute to the logic in the final runtime of the form? Being included in a validation gate
  test does not equate to contributing to the form logic. I am looking at normalization_status, target_type, source_type, target_section, source_section,
  target_selection_mode, source_selection_mode, and then I am confused about why some rules have the body_style_scope like zz3 since that option is only ever
  available on convertible per the ovs of each model, I also do not understand the generation_action which is only used one time on one model, and runtime_action
  since the standard excludes behavior deactivates the target option on selection of the source, so it does not really make sense that there is an additional column
  for a seemingly standard behavior. Justify a tangible reason to keep any of those columns that is not "because it is required for a test to pass" or "a script
  takes it then writes it to a different place where it never gets used past that".

## Evidence checked:

- Workbook source sheets: rule_mapping, grandSport_rule_mapping, z06_rule_mapping
- Generator paths:
  - scripts/corvette_form_generator/production.py:399-477
  - scripts/corvette_form_generator/rules.py:119-198
- Runtime:
  - form-app/app.js:199-204 indexes generated rules by source_id / target_id
  - form-app/app.js:583-593 applies body_style_scope
  - form-app/app.js:877-927 auto-adds includes
  - form-app/app.js:945-991 computes direct disable/conflict reasons
  - form-app/app.js:1456-1462 removes runtime_action=replace targets
  - form-app/app.js:1577-1587 calls that replacement cleanup during reconciliation

### Current classification for the columns you named:

**Column: source_type**
Keep?: No, runtime-safe retire candidate
Why / cleanup path: It is copied into generated rules[*].source_type, but current browser runtime does not read it. The generator does not need it to resolve
labels or behavior; source identity is already encoded by source_id and checked against option/interior IDs. If audit tooling wants it, infer it or keep it
out of runtime source sheets.
────────────────────────────────────────
**Column: target_type**
Keep?: No, runtime-safe retire candidate
Why / cleanup path: Same as source_type. It is emitted but not behavior-carrying in form-app/app.js.
────────────────────────────────────────
**Column: source_section**
Keep?: No, but remove carefully
Why / cleanup path: It is not browser runtime logic. Generator uses it only as duplicate metadata to derive/supplement selection mode and detect same-section
redundant excludes. That information already exists via the option row’s section_id and section_master. Better cleanup: derive section from source_id at
generation time or delete redundant rows.
────────────────────────────────────────
**Column: target_section**
Keep?: No, but remove carefully
Why / cleanup path: Same as source_section. It duplicates target option/interior section ownership.
────────────────────────────────────────
**Column: source_selection_mode**
Keep?: No
Why / cleanup path: This duplicates section_master.selection_mode through source_section. It is only a generator helper/fallback, not runtime form logic. If
needed, derive from source option section.
────────────────────────────────────────
**Column: target_selection_mode**
Keep?: No
Why / cleanup path: Same as source_selection_mode.
────────────────────────────────────────
**Column: normalization_status**
Keep?: No, retire candidate
Why / cleanup path: Current values are effectively lifecycle metadata: Stingray all active, Z06 all active, Grand Sport 122 active + 1 preserved. No current
row uses omitted/replaced. This should not be a long-lived runtime-source column. If a row should not generate, delete it or model the real rule elsewhere.
────────────────────────────────────────
**Column: generation_action**
Keep?: No, but one row blocks direct deletion
Why / cleanup path: Only one current row uses it: grandSport_rule_mapping.gs_rule_opt_cfl_001_excludes_opt_cfz_001 with preserve_runtime_exclude. That is not
final form logic; it is a generator escape hatch to keep a row from group-dedupe. Clean path: decide whether that CFL/CFZ row is genuinely needed. If yes,
keep it as a normal explicit rule without a special column. If no, delete it.
────────────────────────────────────────
**Column: body_style_scope**
Keep?: Probably no for current rows
Why / cleanup path: The browser does use it, but current scoped rules appear redundant with OVS availability. I checked scoped rows: in the opposite body
style, source or target availability already makes the rule inapplicable. Example: ZZ3 is unavailable on coupe, so convertible-scoped requires ZZ3 rows are
already naturally blocked by target availability. I would treat current body_style_scope values as cleanup candidates, but verify by contract/browser
comparison before removing.
────────────────────────────────────────
**Column: runtime_action**
Keep?: Keep for now; remodel later if desired
Why / cleanup path: This one is tangibly behavior-carrying today. It is not just test scaffolding. runtime_action=replace lets a source remove a
selected/default target during reconciliation (removeReplaceRuleTargets()), and disableReasonForChoice() treats replace differently from a normal conflict.
A plain excludes does not fully model “selecting source replaces/removes default target”; it can block the source if the target/default is already
selected.

    Why runtime_action=replace is different from standard excludes:

    - Standard direct exclude:
      - If source is selected, target is disabled/blocked.
      - If target is already selected, selecting source can be blocked as a conflict.
    - Replace exclude:
      - Source is allowed to win.
      - Runtime deletes the target: form-app/app.js:1456-1462.
      - This matters for default-selected or restored options such as calipers/spoilers/exhaust tips.

    So I agree with your broader instinct, but not with deleting runtime_action cold. It currently carries real behavior. The better cleanup is to remodel each runtime_action=replace row into the canonical workbook shape, then remove the column after behavior parity is proven.

    Current runtime_action=replace rows:
    - Stingray: 5 rows, all removing T0A when Z51-related aero/spoiler choices are selected.
    - Grand Sport: 6 rows:
      - J57 replaces J6A
      - FEY replaces T0E
      - FEB replaces JX6
      - FEY replaces JX6
      - FEY replaces J56
      - NWI replaces NGA
    - Z06: 1 row:
      - J57 replaces J6A

    My recommended cleanup sequence:

    1. Retire pure duplicate/debug columns first:
       - source_type
       - target_type
       - source_selection_mode
       - target_selection_mode
       - probably source_section
       - probably target_section

    2. Retire lifecycle/escape-hatch columns next:
       - normalization_status
       - generation_action
       - Resolve the one Grand Sport preserve_runtime_exclude row directly before removing generation_action.

    3. Audit/remove body_style_scope:
       - For current rows, OVS availability appears to already carry the body-style boundary.
       - Remove only after proving generated contracts and browser behavior are unchanged.
       - Longer-term rule: if a relationship is body-specific because availability is body-specific, OVS should own it. Keep rule scope only for relationships where both options are available in both bodies but the relationship itself differs by body.

    4. Defer runtime_action until replacement behavior is remodeled:
       - Convert each replace case to workbook-owned exclusive/default/include semantics where possible.
       - Then remove runtime_action only after runtime tests prove source-can-replace-target behavior still works.

    Bottom line:
    - Safe retirement candidates: source_type, target_type, source_selection_mode, target_selection_mode, source_section, target_section, normalization_status.
    - Conditional retirement candidates: generation_action, body_style_scope.
    - Keep for now because it changes live form behavior: runtime_action.
