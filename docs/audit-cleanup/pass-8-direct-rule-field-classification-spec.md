# Pass 8 — Direct Rule Field Classification Report/Spec

Status: Completed report-only implementation on 2026-06-22.
Date: 2026-06-22
Report: `docs/audit-cleanup/pass-8-direct-rule-field-classification-report.md`.
Recommended reasoning level for implementation agent: high.

## Goal

Run a report-only classification pass for the two direct-rule fields that still carry live behavior:

- `runtime_action`, especially `runtime_action=replace`
- `body_style_scope`

This pass must happen before deleting either column from `rule_mapping`, `grandSport_rule_mapping`, or `z06_rule_mapping`, before changing generated `rules` payload fields, and before changing browser direct-rule evaluation.

The delivered pass is a classification report with row-level recommendations and parity criteria. It is not a workbook cleanup pass.

## Diagnosis

Change type for this spec: docs-only.

Change type for the completed Pass 8 report: report-only/docs-only. It did not write `stingray_master.xlsx`, regenerate committed artifacts, or change runtime behavior.

Risk level: medium. `runtime_action=replace` and `body_style_scope` are not duplicate/lifecycle-only fields today:

- `form-app/app.js:600` currently checks direct rule `body_style_scope` in `ruleAppliesToCurrentVariant()` with a direct equality test, not the generic `scopeMatches()` helper.
- `form-app/app.js:1526` uses `runtime_action === "replace"` in `removeReplaceRuleTargets()` to delete selected/default targets when a replacement source is selected.
- `form-app/app.js:1019` gives `runtime_action=replace` a different disabled reason path than normal `excludes`.
- `scripts/corvette_form_generator/production.py:421` / `:473` and `scripts/corvette_form_generator/rules.py:160` / `:200` read and emit both fields into generated rule payloads.
- Existing tests assert current behavior and generated fields, including `tests/workbook-schema-standardization.test.mjs:348`, `tests/stingray-form-regression.test.mjs`, `tests/grand-sport-draft-data.test.mjs`, and `tests/multi-model-runtime-switching.test.mjs`.

Therefore these fields cannot be removed as part of a duplicate-column cleanup without first classifying how each row's behavior is owned by canonical workbook metadata.

## Current evidence inspected

Report implementation preflight run 2026-06-22:

```text
## schema-ingestion-normalization...origin/main
excel_lock_absent
workbook_package status=valid issue_count=0
```

Pass 8 changed only the report artifact and status documentation listed below.

Read-only workbook inventory from `stingray_master.xlsx`:

```text
rule_mapping
  rows: 144
  rule_type counts: includes=52, excludes=75, requires=17
  runtime_action counts: blank=139, replace=5
  body_style_scope counts: blank=136, coupe=4, convertible=4

grandSport_rule_mapping
  rows: 122
  rule_type counts: excludes=50, includes=53, requires=19
  runtime_action counts: blank=116, replace=6
  body_style_scope counts: blank=113, coupe=4, convertible=5

z06_rule_mapping
  rows: 73
  rule_type counts: excludes=12, includes=52, requires=9
  runtime_action counts: blank=72, replace=1
  body_style_scope counts: blank=70, coupe=1, convertible=2
```

Generated `form-app/data.js` inventory:

```text
stingray rules: 144
  runtime_action: active=139, replace=5
  body_style_scope: blank=136, coupe=4, convertible=4

grandSport rules: 122
  runtime_action: active=115, omit_redundant_same_section_exclude=1, replace=6
  body_style_scope: blank=113, coupe=4, convertible=5

z06 rules: 73
  runtime_action: active=72, replace=1
  body_style_scope: blank=70, coupe=1, convertible=2
```

The generator normalizes blank workbook `runtime_action` to generated `runtime_action: "active"` and preserves `replace` as behavior-carrying runtime metadata.

### Current `runtime_action=replace` rows

Stingray:

| workbook row | rule_id | source | target | preliminary owner signal |
|---:|---|---|---|---|
| 51 | `rule_opt_5zu_001_excludes_opt_t0a_001` | `opt_5zu_001` / 5ZU | `opt_t0a_001` / T0A | Same section spoiler replacement; source and target share `grp_spoiler_high_wing`; source has paint `requires_any` group. |
| 52 | `rule_opt_5zw_001_excludes_opt_t0a_001` | `opt_5zw_001` / 5ZW | `opt_t0a_001` / T0A | Same section spoiler replacement; no current shared exclusive group found in the quick probe. |
| 53 | `rule_opt_5zz_001_excludes_opt_t0a_001` | `opt_5zz_001` / 5ZZ | `opt_t0a_001` / T0A | Same section spoiler replacement; source and target share `grp_spoiler_high_wing`. |
| 134 | `rule_opt_zf1_001_excludes_opt_t0a_001` | `opt_zf1_001` / ZF1 | `opt_t0a_001` / T0A | Same section spoiler/default replacement; no current shared exclusive group found in the quick probe. |
| 141 | `rule_opt_tvs_001_excludes_opt_t0a_001` | `opt_tvs_001` / TVS | `opt_t0a_001` / T0A | Same section spoiler replacement; source and target share `grp_spoiler_high_wing`. |

Grand Sport:

| workbook row | rule_id | source | target | preliminary owner signal |
|---:|---|---|---|---|
| 97 | `gs_rule_opt_j57_001_excludes_opt_j6a_001_replace` | `opt_j57_001` / J57 | `opt_j6a_001` / J6A | Source has `gs_group_j57_z52_requirement` `requires_any`; cross-section brake/default replacement. |
| 98 | `gs_rule_opt_fey_001_excludes_opt_t0e_001_replace` | `opt_fey_001` / FEY | `opt_t0e_001` / T0E | Target is `default_selected`; aero/default replacement. |
| 118 | `gs_rule_opt_feb_001_excludes_opt_jx6_001_replace` | `opt_feb_001` / FEB | `opt_jx6_001` / JX6 | Target is `default_selected`; package/brake default replacement. |
| 119 | `gs_rule_opt_fey_001_excludes_opt_jx6_001_replace` | `opt_fey_001` / FEY | `opt_jx6_001` / JX6 | Target is `default_selected`; package/brake default replacement. |
| 120 | `gs_rule_opt_fey_001_excludes_opt_j56_001_replace` | `opt_fey_001` / FEY | `opt_j56_001` / J56 | Target is `display_only`; needs separate classification, not assumed redundant. |
| 121 | `gs_rule_opt_nwi_001_excludes_opt_nga_001_replace` | `opt_nwi_001` / NWI | `opt_nga_001` / NGA | Exhaust default replacement pattern; known WUB/NWI/NGA dependency distinction. |

Z06:

| workbook row | rule_id | source | target | preliminary owner signal |
|---:|---|---|---|---|
| 48 | `z06_rule_opt_j57_001_excludes_opt_j6a_001` | `opt_j57_001` / J57 | `opt_j6a_001` / J6A | Target is `default_selected`; current schema guard already allowlists this as the remaining active Z06 direct replacement. |

### Current `body_style_scope` rows

Stingray scoped direct rules:

| row | rule_id | scope | source | target | preliminary owner signal |
|---:|---|---|---|---|---|
| 54 | `rule_opt_b6p_001_includes_opt_d3v_001` | coupe | B6P | D3V | Source and target OVS are coupe-only. |
| 56 | `rule_opt_bc4_001_includes_opt_d3v_001` | coupe | BC4 | D3V | Source is coupe+convertible; target OVS is coupe-only. |
| 57 | `rule_opt_bc4_002_requires_opt_zz3_001` | convertible | BC4 | ZZ3 | Source is coupe+convertible; target OVS is convertible-only. |
| 58 | `rule_opt_bcp_001_includes_opt_d3v_001` | coupe | BCP | D3V | Source is coupe+convertible; target OVS is coupe-only. |
| 59 | `rule_opt_bcp_002_requires_opt_zz3_001` | convertible | BCP | ZZ3 | Source is coupe+convertible; target OVS is convertible-only. |
| 60 | `rule_opt_bcs_001_includes_opt_d3v_001` | coupe | BCS | D3V | Source is coupe+convertible; target OVS is coupe-only. |
| 61 | `rule_opt_bcs_002_requires_opt_zz3_001` | convertible | BCS | ZZ3 | Source is coupe+convertible; target OVS is convertible-only. |
| 142 | `rule_opt_bc7_001_requires_opt_zz3_001_convertible` | convertible | BC7 | ZZ3 | Source is coupe+convertible; target OVS is convertible-only. |

Grand Sport scoped direct rules:

| row | rule_id | scope | source | target | preliminary owner signal |
|---:|---|---|---|---|---|
| 3 | `gs_rule_opt_b6p_001_includes_opt_d3v_001` | coupe | B6P | D3V | Source and target OVS are coupe-only. |
| 5 | `gs_copy_rule_opt_bc4_002_requires_opt_zz3_001_opt_bc4_002_requires_opt_zz3_001_convertible` | convertible | BC4 | ZZ3 | Source is coupe+convertible; target OVS is convertible-only. |
| 6 | `gs_rule_opt_bc4_002_includes_opt_d3v_001` | coupe | BC4 | D3V | Source is coupe+convertible; target OVS is coupe-only. |
| 7 | `gs_copy_rule_opt_bc7_001_requires_opt_zz3_001_convertible_opt_bc7_001_requires_opt_zz3_001_convertible` | convertible | BC7 | ZZ3 | Source is coupe+convertible; target OVS is convertible-only. |
| 8 | `gs_copy_rule_opt_bcp_002_requires_opt_zz3_001_opt_bcp_002_requires_opt_zz3_001_convertible` | convertible | BCP | ZZ3 | Source is coupe+convertible; target OVS is convertible-only. |
| 9 | `gs_rule_opt_bcp_002_includes_opt_d3v_001` | coupe | BCP | D3V | Source is coupe+convertible; target OVS is coupe-only. |
| 10 | `gs_copy_rule_opt_bcs_002_requires_opt_zz3_001_opt_bcs_002_requires_opt_zz3_001_convertible` | convertible | BCS | ZZ3 | Source is coupe+convertible; target OVS is convertible-only. |
| 11 | `gs_rule_opt_bcs_002_includes_opt_d3v_001` | coupe | BCS | D3V | Source is coupe+convertible; target OVS is coupe-only. |
| 95 | `gs_rule_opt_bc4_002_requires_opt_zz3_001_convertible` | convertible | BC4 | ZZ3 | Source is coupe+convertible; target OVS is convertible-only; appears duplicative with row 5 and must be classified before edits. |

Z06 scoped direct rules:

| row | rule_id | scope | source | target | preliminary owner signal |
|---:|---|---|---|---|---|
| 3 | `z06_rule_opt_b6p_001_includes_opt_d3v_001` | coupe | B6P | D3V | Source and target OVS are coupe-only. |
| 47 | `z06_rule_opt_bcw_001_requires_opt_zz3_001_convertible` | convertible | BCW | ZZ3 | Source is coupe+convertible; target OVS is convertible-only. |
| 49 | `z06_rule_opt_pbc_001_requires_opt_zz3_001_convertible` | convertible | PBC | ZZ3 | Source is coupe+convertible; target OVS is convertible-only. |

Important caveat: these are preliminary owner signals, not deletion decisions. A future implementation must prove generated/runtime parity before removing workbook columns, changing values, changing app scope matching, or relying only on OVS availability.

## Ownership questions for Pass 8 report

### `runtime_action=replace`

Classify every current replacement row into one of these buckets:

1. **True direct default replacement**
   - Keep as direct replacement for now.
   - Criteria: selected source must remove a generated/default selected target, and no existing exclusive group/default-selection rule cleanly owns the behavior without changing UX.

2. **Exclusive peer replacement candidate**
   - Candidate owner: `*_exclusive_groups` + `*_exclusive_members`.
   - Criteria: source and target are peer choices, especially same-section options that should switch like radio peers.
   - Required proof before migration: runtime replacement test and generated contract comparison showing no behavior drift beyond approved row/group changes.

3. **Default-selection metadata candidate**
   - Candidate owner: `default_selection_rules` plus existing direct dependencies.
   - Criteria: target is a soft/default-selected row that should be restored when the source/peer is absent, and suppressed when a replacement peer is selected.

4. **Grouped dependency/blocker candidate**
   - Candidate owner: `*_rule_groups` / `*_rule_group_members` using `requires_any` or `excludes_any`.
   - Criteria: one source affects a family of targets, or a package enables/defaults/blocks a set where direct pairwise replacement rows are only scaffolding.

5. **Needs product decision**
   - Criteria: current workbook metadata does not clearly identify whether the row is default replacement, peer switching, blocker, or include/default behavior.
   - These rows must remain unchanged until the user makes a product-rule decision.

### `body_style_scope`

Classify every scoped direct rule into one of these buckets:

1. **Derivable from target/source OVS availability**
   - Candidate owner: `*_ovs` option/variant availability rows.
   - Criteria: source and/or target active availability already makes the rule impossible outside the scoped body style, and generated/runtime parity proves the explicit direct-rule scope is redundant.

2. **Rule-specific conditional scope**
   - Keep as direct rule scope for now.
   - Criteria: source and target availability alone does not express why the relation applies only to coupe or convertible.

3. **Runtime-scope semantics cleanup candidate**
   - Candidate code change: make direct-rule evaluation use `scopeMatches()` instead of direct equality.
   - This is not approved by Pass 8. It would need a separate runtime pass because literal `*` currently behaves differently in direct rules than in `runtimeRuleExceptions`, default rules, rule groups, and price rules.

4. **Duplicate/stale row candidate**
   - Criteria: duplicate rule rows express the same source/type/target/scope behavior, such as the apparent Grand Sport BC4/ZZ3 convertible duplication.
   - The report should identify these, but deletion requires a separate approved workbook/source cleanup with contract parity proof.

## Exact files for this report/spec pass

Completed Pass 8 report-only implementation changed:

- `docs/audit-cleanup/pass-8-direct-rule-field-classification-report.md`
- `docs/audit-cleanup/pass-8-direct-rule-field-classification-spec.md`
- `docs/Audit-route-map.md`

Do not change these in Pass 8 report-only implementation:

- `stingray_master.xlsx`
- `form-app/app.js`
- `form-app/data.js`
- `form-output/*`
- `scripts/corvette_form_generator/*`
- `tests/*`

A later implementation pass may touch those surfaces only after the classification report is reviewed and approved.

## Constraints

- No workbook writes in the report/spec pass.
- No generator changes.
- No runtime JS changes.
- No generated artifact changes.
- No dependency additions.
- No visual/UI changes.
- No dealer submission endpoint, payload, or Turnstile changes.
- Do not normalize blank direct-rule scope cells to literal `*`; direct-rule runtime matching does not currently use generic `scopeMatches()`.
- Do not delete or suppress `runtime_action=replace` rows without replacing their behavior through workbook-owned metadata and proving parity.
- Do not treat validator/test references as proof a field belongs in the workbook; classify by final generated/runtime behavior first.

## Completed Pass 8 report procedure

1. Preflight.

   ```sh
   cd /Users/seandm/Projects/27vette
   git status --short --branch
   test ! -e './~$stingray_master.xlsx'
   .venv/bin/python scripts/validate_workbook_package.py stingray_master.xlsx
   ```

2. Re-run the read-only workbook inventory.

   - Count rows by rule sheet, rule type, `runtime_action`, and `body_style_scope`.
   - Enumerate every `runtime_action=replace` row.
   - Enumerate every nonblank `body_style_scope` row.
   - Join each row to source/target option RPO, section, status, `display_behavior`, OVS body-style availability, exclusive groups, and rule groups.

3. Re-run the generated artifact inventory.

   - Inspect `form-output/runtime/*-runtime-contract.json` and `form-app/data.js`.
   - Count emitted `rules`, `runtime_action`, and `body_style_scope` by promoted model.
   - Verify whether generated contracts and registry agree before making conclusions.

4. Trace active consumers.

   - Runtime: `form-app/app.js` direct-rule helpers and replacement reconciliation.
   - Generators: `production.py`, `rules.py`, `inspection.py`, and `runtime_contract.py` if relevant.
   - Tests: generated-field guards and runtime behavior tests in Stingray, Grand Sport, Z06, and multi-model suites.
   - Optional audit/report path: `scripts/build_rule_sources.py` and `tests/grand-sport-rule-audit.test.mjs`.

5. Produced `docs/audit-cleanup/pass-8-direct-rule-field-classification-report.md`.

   The report must include:

   - row-level classification table for every replacement row;
   - row-level classification table for every body-scoped direct rule;
   - proposed canonical owner for each row;
   - rows safe to leave as-is;
   - rows requiring product decision;
   - rows that appear redundant but need parity proof;
   - exact later-pass candidates, split by workbook cleanup, generator/runtime scope semantics, and test updates.

6. Stopped after the report.

   Do not edit workbook columns, rule rows, generator behavior, runtime behavior, tests, or generated artifacts in Pass 8.

## Validation for this docs/report pass

Docs-only validation run after implementation:

```sh
git diff --check
pattern="$(printf 'Status: Spec %s|Approve Pass %s as a report-only classification implementation' only 8)"
if rg -n "$pattern" docs/audit-cleanup/pass-8-direct-rule-field-classification-spec.md docs/Audit-route-map.md docs/audit-cleanup/pass-8-direct-rule-field-classification-report.md; then exit 1; fi
```

Report completeness validation run after implementation:

```sh
.venv/bin/python - <<'PY'
# Read-only assertion for the report implementation:
# - every runtime_action=replace row from rule_mapping/grandSport_rule_mapping/z06_rule_mapping appears in the report
# - every nonblank body_style_scope row from those sheets appears in the report
# - every report row has a classification bucket and proposed owner / decision state
PY
```

No generators or runtime tests are required for the report-only pass because it must not change workbook, generated, or runtime behavior. If any implementation goes beyond report/docs, stop and write a separate implementation spec with model-specific gates.

## Completion summary

Completed on 2026-06-22 as a report-only/docs-only pass.

Changed files:

- `docs/audit-cleanup/pass-8-direct-rule-field-classification-report.md`
- `docs/audit-cleanup/pass-8-direct-rule-field-classification-spec.md`
- `docs/Audit-route-map.md`

Changed workbook sheets/artifacts/runtime behavior: none. `stingray_master.xlsx`, `form-output/*`, `form-app/data.js`, generator code, runtime code, and tests were not changed.

Report findings:

- `runtime_action=replace` remains live behavior and is split into direct-default, exclusive-peer, default-selection, grouped-dependency, and product-decision candidates.
- Most nonblank `body_style_scope` direct rules appear OVS-derivable, but deletion needs a workbook parity pass.
- Grand Sport BC4/ZZ3 rows 5 and 95 are the only duplicate/stale direct-rule pair identified in the scoped inventory.

Recommended next pass: Candidate A from the report — a body-style scope retirement parity pass that deletes only reviewed OVS-derivable scope values / the Grand Sport duplicate candidate after safe workbook write, regeneration, contract comparison, and targeted runtime gates. Do not bundle runtime `scopeMatches()` semantics or replacement-rule migration into that pass.

## Risks

- Treating OVS availability as a substitute for `body_style_scope` without proving parity could silently change when `includes`, `requires`, or `excludes` rows apply.
- Deleting `runtime_action=replace` without an owner migration can reintroduce default rows into selected/order output or disable valid peer selections.
- Changing direct-rule scope matching to `scopeMatches()` is likely safe in principle, but it is a runtime behavior change and must be scoped separately.
- Grand Sport row duplication around BC4/ZZ3 convertible may be real cleanup candidate, but deletion should be a workbook parity pass, not a report-only pass.
- Optional audit/report consumers may need derived fields for explainability even if the live runtime can eventually stop carrying workbook duplicate columns.

## Non-goals

- No workbook column deletion.
- No rule row deletion.
- No runtime-action behavior migration.
- No direct-rule scope matcher change.
- No generated payload trim.
- No optional audit/report artifact refresh.
- No ZR1/ZR1X rule cleanup.
- No price-rule semantic classification; that remains a separate price-rule pass.

## Historical approval prompt

The historical approval question was whether to run Pass 8 as a report-only classification implementation.

Approval of Pass 8 authorized only the report artifact and route/spec status updates. It did not authorize workbook edits, generated artifact changes, runtime code changes, or deletion of `runtime_action` / `body_style_scope`.
