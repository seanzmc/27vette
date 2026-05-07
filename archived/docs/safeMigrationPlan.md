# Safe Phased Migration Plan: Excel/Python Stingray Generator → Schema-Driven CSV Data Package

The safest migration strategy is **data-model first, behavior frozen, performance second**. The current repository is a static, no-build customer order-form app in `form-app/`, where `app.js` consumes generated `data.js`, and the current source-of-truth workflow is `stingray_master.xlsx` plus `scripts/generate_stingray_form.py`, which regenerates `form-output/` and `form-app/data.js`. The repo also treats JSON/CSV exports, selected options, auto-added RPOs, open requirements, and pricing as part of the app’s user-facing behavior. ([github.com](https://github.com/seanzmc/27vette))

The target architecture should follow `schema-refactor.md`: make `data/stingray/**/*.csv` plus `data/stingray/datapackage.yaml` canonical, demote Excel to an optional generated editor workbook, move Corvette-specific business rules out of Python, and keep generated `form-app/data.js` compatible with the existing runtime contract during migration. ([raw.githubusercontent.com](https://raw.githubusercontent.com/seanzmc/27vette/main/schema-refactor.md))

## Guiding Decisions

1. **Do not rewrite the compiler language during the schema migration.**  
   Keep Python as a compatibility compiler while it learns to read the CSV Data Package. Once CSV parity is proven, a plain Node.js compiler may be introduced as a separate final simplification phase. This avoids combining two high-risk changes: schema migration and compiler-language migration.

2. **“Plain JavaScript” applies most strictly to the runtime.**  
   The browser app must stay dependency-light: no React, Vue, Svelte, Angular, Vite, webpack, TypeScript build chain, or framework. Build-time validation may use pinned dev-only tools such as Frictionless/Pydantic-style validation at first. A later optional Node-only compiler can reduce build dependencies after parity.

3. **Freeze the current `data.js` contract first.**  
   Existing `app.js`, export shape, option IDs, RPOs, pricing fields, rules, sections, interiors, color overrides, and metadata should remain compatible. Add optimized indexes beside the legacy arrays rather than replacing the data shape immediately.

4. **Optimize after parity, not before.**  
   Performance gains should come from generated indexes, precomputed rule structures, cached condition evaluation, and batched DOM updates. Runtime changes should be small, feature-flagged, and reversible.

5. **Excel is not canonical after cutover.**  
   After parity, `stingray_master.xlsx` should either move to `archived/` or become a generated `editor/stingray_editor.xlsx` round-tripped through import/export scripts.

6. **Parity means normalized output parity plus behavioral parity.**  
   During migration, compare legacy Excel output and CSV output structurally and behaviorally. Any intentional difference must be explicitly whitelisted with a linked change-log entry.

---

# 1. Migration Branch Setup

## 1.1 Create a dedicated migration branch

Create a long-lived integration branch and scoped phase branches:

```text
main
└── refactor/schema-csv
    ├── phase-0-workbook-inventory
    ├── phase-1-csv-package-skeleton
    ├── phase-2-logic-to-csv
    ├── phase-3-pricing-to-csv
    ├── phase-4-ui-availability-to-csv
    ├── phase-5-supporting-domains
    ├── phase-6-cutover
    └── phase-7-optional-node-compiler
```

Recommended setup:

```sh
git checkout main
git pull origin main

python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

python scripts/generate_stingray_form.py
node --test tests/stingray-form-regression.test.mjs
node --test tests/stingray-generator-stability.test.mjs

git tag stingray-excel-baseline-2026-05-01
git checkout -b refactor/schema-csv
```

The current repo already documents the generator and Node test workflow, so the branch should begin only from a clean, reproducible baseline. ([github.com](https://github.com/seanzmc/27vette))

## 1.2 Freeze the current production baseline

Commit immutable baseline artifacts under test fixtures:

```text
tests/fixtures/stingray-baseline/
  generated-from-excel/
    form-app-data.js
    stingray-form-data.json
    stingray-form-data.csv
  hashes/
    stingray_master.sha256
    data_js.sha256
```

Generate and capture:

```sh
python scripts/generate_stingray_form.py

mkdir -p tests/fixtures/stingray-baseline/generated-from-excel
cp form-app/data.js tests/fixtures/stingray-baseline/generated-from-excel/form-app-data.js
cp form-output/stingray-form-data.json tests/fixtures/stingray-baseline/generated-from-excel/
cp form-output/stingray-form-data.csv tests/fixtures/stingray-baseline/generated-from-excel/

shasum -a 256 stingray_master.xlsx > tests/fixtures/stingray-baseline/hashes/stingray_master.sha256
shasum -a 256 form-app/data.js > tests/fixtures/stingray-baseline/hashes/data_js.sha256
```

This frozen baseline becomes the parity target for every phase.

## 1.3 Add a dual-source switch

Add a single source-mode flag:

```text
STINGRAY_SOURCE=xlsx   # legacy workbook path
STINGRAY_SOURCE=csv    # new CSV package path
STINGRAY_SOURCE=both   # run both, normalize, compare
```

Example commands:

```sh
STINGRAY_SOURCE=xlsx python scripts/generate_stingray_form.py --out build/xlsx
STINGRAY_SOURCE=csv  python scripts/compile_stingray_data.py --out build/csv
STINGRAY_SOURCE=both python scripts/compare_stingray_outputs.py
```

During phases 1–5, CI should default to `STINGRAY_SOURCE=both`. Production remains on `xlsx` until cutover. If any issue appears, rollback is a one-line switch back to `STINGRAY_SOURCE=xlsx`.

## 1.4 Protect branches and artifacts

Required checks on `refactor/schema-csv`:

```text
schema-validate
semantic-validate
golden-builds
csv-vs-xlsx-output-parity
stingray-runtime-regression
export-parity
property-fuzz
generated-artifact-staleness
perf-smoke
no-framework-guard
```

Protect `main`:

- PR review required.
- All checks green.
- No direct commits.
- No change to Stingray behavior unless explicitly approved.
- No runtime/UI/export schema change unless explicitly approved.

Those boundaries align with the repo’s existing guidance: preserve Stingray behavior, avoid unapproved runtime/export schema changes, prefer source-data changes over Python patches, and keep `source_detail_raw` available for audit. ([raw.githubusercontent.com](https://raw.githubusercontent.com/seanzmc/27vette/main/codex-context.md))

## 1.5 Add deployment/cache safety immediately

Before changing the data shape, prevent users from loading mismatched static files.

Add generated build metadata:

```js
window.STINGRAY_FORM_DATA = {
  dataset: {
    model_key: "stingray",
    schema_version: 1,
    app_contract_version: 1,
    build_id: "2026-05-01T12-00-00Z-a1b2c3d",
    generated_from: "xlsx",
  },
  // existing fields...
};
```

Add an app-side compatibility check:

```js
const REQUIRED_DATA_CONTRACT_VERSION = 1;

function assertDataCompatibility(data) {
  if (!data?.dataset) throw new Error("Missing Stingray dataset metadata.");
  if (data.dataset.app_contract_version !== REQUIRED_DATA_CONTRACT_VERSION) {
    throw new Error(
      `Incompatible data.js contract: expected ${REQUIRED_DATA_CONTRACT_VERSION}, got ${data.dataset.app_contract_version}`,
    );
  }
}
```

Static deployment policy:

```text
index.html: Cache-Control: no-cache
app.js/data.js: either no-cache or generated hash/query string
deploys: atomic only; app.js and data.js from same build_id
runtime: display blocking diagnostic if data/app contract mismatch
```

If the project later uses hashed filenames, generate:

```html
<script src="./data.js?v={{build_id}}"></script>
<script src="./app.js?v={{build_id}}"></script>
```

This closes the common static-app failure mode where old `app.js` reads new `data.js`, or vice versa.

---

# 2. Architecture Transition

## 2.1 Preserve the existing frontend contract

The first target is:

```text
data/stingray CSV package
  -> loader/validator/compiler
  -> same form-output artifacts
  -> same form-app/data.js shape
  -> same app.js behavior
```

Do **not** start by rewriting `app.js`.

The current runtime already builds maps from generated data, tracks selected options in `Set`s, computes auto-adds, resolves prices, renders summaries, and exports JSON/CSV. Those behaviors should be treated as the public contract until tests prove a safer replacement. ([raw.githubusercontent.com](https://raw.githubusercontent.com/seanzmc/27vette/main/form-app/app.js))

## 2.2 Phase 0 — Workbook inventory and migration crosswalk

Add:

```text
scripts/inspect_stingray_workbook.py
data/stingray/meta/workbook_column_map.csv
form-output/inspection/workbook-inventory.csv
```

The inspector should emit:

```csv
source_workbook,source_sheet,source_column,row_count,non_null_count,sample_values,target_csv,target_column,migration_status,notes
```

Allowed `migration_status` values:

```text
mapped
mapped_do_not_parse
generated_only
ignored_with_reason
deprecated_with_reason
needs_review
```

Exit gate:

```text
No sheet or column may remain needs_review.
Every workbook-derived behavior must be mapped, intentionally ignored, generated-only, or deprecated with an explanation.
```

This phase has **no behavior change**.

## 2.3 Phase 1 — Introduce the CSV Data Package beside Excel

Create the canonical layout:

```text
data/
  stingray/
    datapackage.yaml

    meta/
      source_refs.csv
      change_log.csv
      workbook_column_map.csv
      enum_values.csv

    catalog/
      variants.csv
      selectables.csv
      options.csv
      item_sets.csv
      item_set_members.csv
      aliases.csv

    ui/
      steps.csv
      sections.csv
      selectable_display.csv
      availability.csv

    logic/
      condition_sets.csv
      condition_terms.csv
      dependency_rules.csv
      auto_adds.csv
      exclusive_groups.csv
      exclusive_group_members.csv

    pricing/
      price_books.csv
      base_prices.csv
      price_policies.csv
      price_rules.csv
      price_lookup_tables.csv
      price_lookup_rows.csv

    support/
      exterior_colors.csv
      interiors.csv
      interior_components.csv
      color_overrides.csv
      legacy_price_refs.csv

    validation/
      golden_builds.csv
      golden_build_selections.csv
      golden_expected_lines.csv
      golden_expected_requirements.csv
      golden_expected_conflicts.csv
```

Start with a narrow vertical slice:

```text
B6P
SL1
D3V
ZZ3
BCP
BCS
BC4
Coupe variants
Convertible variants
LS6 engine-cover set
B6P -> SL1 auto-add
colored engine cover -> D3V auto-add
engine-cover $695 / $595 pricing
Convertible ZZ3 requirement
LS6 engine-cover exclusivity
```

Populate only the minimum tables needed for that slice. Compile both sources and compare. The schema refactor explicitly recommends this package layout, stable IDs, item sets, condition sets, dependency rules, auto-adds, pricing tables, support tables, validation fixtures, and generated `form-app/data.js` compatibility. ([raw.githubusercontent.com](https://raw.githubusercontent.com/seanzmc/27vette/main/schema-refactor.md))

## 2.4 Phase 2 — Move hard-coded logic groups into CSV

Move Corvette-specific generator constants and branches into data rows.

The current generator contains hard-coded rule groups and exclusive groups for items such as spoiler requirements, approved body-color requirements, LS6 engine covers, spoilers, center caps, indoor/outdoor car covers, and suede trunk liners. These should become `logic/*` and `catalog/item_sets*` rows. ([github.com](https://github.com/seanzmc/27vette/blob/main/scripts/generate_stingray_form.py))

Move:

| Current concern                   | New source                                                                            |
| --------------------------------- | ------------------------------------------------------------------------------------- |
| Reusable RPO lists                | `catalog/item_sets.csv`, `catalog/item_set_members.csv`                               |
| Requires-any groups               | `logic/condition_sets.csv`, `logic/condition_terms.csv`, `logic/dependency_rules.csv` |
| Auto-adds / included options      | `logic/auto_adds.csv`, `pricing/price_policies.csv`                                   |
| Same-section or group exclusivity | `logic/exclusive_groups.csv`, `logic/exclusive_group_members.csv`                     |
| Body/trim/model-year conditions   | `logic/condition_sets.csv`, `logic/condition_terms.csv`                               |
| Legacy aliases/duplicates         | `catalog/aliases.csv`                                                                 |

Compiler rule:

```text
The compiler may understand generic concepts:
condition_set
condition_term
dependency_rule
auto_add
exclusive_group
item_set
price_rule
lookup_table

The compiler must not contain RPO-specific business branches:
if rpo == "B6P": ...
if target == "ZZ3": ...
if option in ["BCP", "BCS", "BC4"]: ...
```

## 2.5 Phase 3 — Move pricing into CSV

Populate:

```text
pricing/price_books.csv
pricing/base_prices.csv
pricing/price_policies.csv
pricing/price_rules.csv
pricing/price_lookup_tables.csv
pricing/price_lookup_rows.csv
```

Use deterministic price resolution:

```text
1. Select active price book.
2. Find most specific base price:
   selectable-level beats set-level;
   higher priority wins;
   equal-priority ambiguity fails validation.
3. Apply auto-add price policy:
   included_zero -> 0;
   suppress_line -> hidden/suppressed.
4. Apply matching static/zero/lookup replacement rules.
5. Apply explicit stackable additive/subtractive rules.
6. Emit price explanation metadata.
```

Use integer whole-dollar money fields:

```text
amount_usd: 695
amount_usd: 595
amount_usd: 0
```

Do not use floats.

For dynamic interior component pricing, use lookup tables such as:

```text
lookup key = {context.trim_level}|{selected.interior.seat_code}|{target.rpo}
example    = 3LT|AH2|N26
```

Lookup templates must use allowlisted tokens only. Do not allow arbitrary Python or JavaScript expressions in CSV.

## 2.6 Phase 4 — Move UI grouping and availability into CSV

Populate:

```text
ui/steps.csv
ui/sections.csv
ui/selectable_display.csv
ui/availability.csv
```

Move these out of Python:

```text
step assignment
section assignment
display order
selection mode
hidden/unavailable/display-only behavior
body-style scope
trim-level scope
variant scope
status/selectable flags
```

Use availability when an option is hidden/disabled by context. Use dependency rules when an option may be selected but creates an open requirement.

## 2.7 Phase 5 — Move supporting domains

Populate and validate:

```text
support/exterior_colors.csv
support/interiors.csv
support/interior_components.csv
support/color_overrides.csv
support/legacy_price_refs.csv
catalog/aliases.csv
```

This phase covers:

```text
exterior colors
interior choices
seat/interior dependencies
interior component pricing
color override auto-add behavior
legacy price references
duplicate/merged workbook rows
old IDs and aliases
```

Do not cram all of this into generic option rows. Support domains deserve explicit tables because they have their own lookup, grouping, pricing, and validation semantics.

## 2.8 Phase 6 — Cutover to CSV canonical source

Cutover only after all parity gates pass.

Steps:

1. Flip CI default to:

   ```text
   STINGRAY_SOURCE=csv
   ```

2. Keep `STINGRAY_SOURCE=xlsx` available for rollback during a soak period.

3. Make Excel non-canonical:

   ```text
   stingray_master.xlsx -> archived/stingray_master.baseline.xlsx
   ```

   or:

   ```text
   data/stingray/**/*.csv -> scripts/export_editor_workbook.py -> build/editor/stingray_editor.xlsx
   build/editor/stingray_editor.xlsx -> scripts/import_editor_workbook.py -> normalized CSV
   ```

4. Add stale artifact checks:

   ```sh
   python scripts/compile_stingray_data.py
   git diff --exit-code form-app/data.js form-output/
   ```

5. Update README:

   ```text
   CSV package is canonical.
   Excel is optional generated editor surface.
   form-output/ and form-app/data.js are generated artifacts.
   ```

6. Run one full week of CSV-default CI on `refactor/schema-csv`.

7. Rehearse rollback:

   ```sh
   STINGRAY_SOURCE=xlsx python scripts/generate_stingray_form.py
   ```

8. Merge to `main`.

## 2.9 Phase 7 — Optional plain Node compiler

Only after CSV cutover is stable, consider replacing the Python compiler with a dependency-light Node.js compiler:

```text
scripts/
  compile-stingray-data.mjs
  validate-stingray-data.mjs
  compare-stingray-outputs.mjs
```

This is optional and should be a separate PR series. The acceptance criterion is identical output and identical behavior. This phase satisfies the long-term desire for a plain-JS/Node build pipeline without risking the core migration.

## 2.10 Persisted state, saved configurations, and legacy imports

Even if the current app has limited persistence, protect future and existing saved data.

Rules:

```text
Stable internal IDs are canonical primary keys.
RPOs remain user-facing/export-facing.
Aliases map legacy IDs to canonical IDs.
Export schema remains versioned.
Saved configurations must include schema_version and app_contract_version.
Import logic must migrate old option IDs/RPOs through catalog/aliases.csv.
```

Add a migration function:

```js
function migrateSavedSelection(saved, aliases) {
  const version = saved.schema_version || 1;
  const ids = saved.selected_option_ids || [];

  return {
    ...saved,
    schema_version: 2,
    selected_option_ids: ids.map((id) => aliases[id] || id),
  };
}
```

Test:

```text
legacy exported JSON -> import/migrate -> same visible configuration
legacy selected_option_ids -> alias mapping -> canonical IDs
bookmarked/query selections -> canonical IDs
localStorage state, if added later -> versioned migration
```

---

# 3. Performance Optimization

Performance improvements should leverage the new schema, but never by changing observable Stingray behavior.

## 3.1 Measure first

Capture baseline metrics from the current Excel-generated app:

```text
data.js parse time
index-build time
first render time
body style switch time
trim switch time
option toggle time
auto-add computation time
price recomputation time
export JSON time
export CSV time
```

Add:

```text
tests/perf/stingray-runtime-benchmark.mjs
```

Use Node’s built-in test runner for logic-level timing and browser DevTools/manual smoke tests for DOM timing.

Acceptance:

```text
No phase may regress more than an approved threshold.
Final CSV build should improve startup/indexing and option-toggle performance.
```

## 3.2 Add generated indexes beside legacy arrays

The current runtime builds indexes such as choices, sections, options, rules, price rules, rule groups, and exclusive groups from generated arrays at startup. That work can be shifted to compile time while keeping compatibility. ([raw.githubusercontent.com](https://raw.githubusercontent.com/seanzmc/27vette/main/form-app/app.js))

Generated data shape:

```js
window.STINGRAY_FORM_DATA = {
  // existing contract remains
  steps: [],
  variants: [],
  sections: [],
  choices: [],
  rules: [],
  priceRules: [],
  ruleGroups: [],
  exclusiveGroups: [],
  interiors: [],
  colorOverrides: [],

  // additive optimization
  indexes: {
    choicesByVariantId: {},
    choiceByVariantAndOption: {},
    sectionsById: {},
    optionsById: {},
    rulesBySource: {},
    rulesByTarget: {},
    priceRulesByTarget: {},
    ruleGroupsBySource: {},
    exclusiveGroupByOption: {},
    itemSetMembersBySetId: {},
    conditionTermsBySetId: {},
    conditionSetsByReferencedSelectable: {},
  },
};
```

Runtime fallback:

```js
const indexes = data.indexes || buildIndexes(data);
```

This gives immediate speed improvements without breaking old generated data.

## 3.3 Precompile condition sets

Compile:

```text
logic/condition_sets.csv
logic/condition_terms.csv
```

into explicit OR-of-AND records:

```js
{
  id: "cs_coupe_with_b6p",
  orGroups: [
    [
      ["context", "body_style", "eq", "coupe"],
      ["selected", "opt_b6p_001", "is_true"]
    ]
  ]
}
```

Do not use:

```js
eval()
new Function()
string-parsed JavaScript expressions
```

Use a tiny explicit interpreter.

## 3.4 Precompute context-only conditions per variant

At compile time, evaluate conditions that depend only on:

```text
variant_id
body_style
trim_level
model_year
price_book
```

Emit:

```js
variantConditionMask: {
  "1lt_c07": {
    "cs_coupe": true,
    "cs_convertible": false
  }
}
```

Runtime then evaluates only user-selection-dependent terms.

## 3.5 Precompute prices where possible

Compile static prices and scoped price rules into per-variant records:

```js
priceByVariantAndOption: {
  "1lt_c07|opt_bcp_001": {
    base_price: 695,
    possible_rules: ["pr_engine_cover_b6p_static"]
  }
}
```

Only dynamic rules depending on selected options, selected interior, or lookup keys remain runtime-resolved.

## 3.6 Reduce payload and repeated work after parity

After the first CSV release is stable, feature-flag more aggressive generated structures:

```text
variant-sharded data slices
string interning for repeated IDs/RPOs/section IDs
integer indexes for hot rule references
precompiled item-set arrays
reverse dependency indexes
sorted/gzip-friendly emission
optional JSON.parse payload wrapper for large literals
```

Example future shape:

```js
window.STINGRAY_DATA_V2 = {
  strings: ["opt_b6p_001", "opt_sl1_001", "sec_engi_001"],
  variants: {
    "1lt_c07": {
      choices: [],
      sections: [],
      rules: [],
    },
  },
  shared: {
    conditionSets: {},
    itemSets: {},
    priceBooks: {},
  },
};
```

Do **not** make this the initial migration contract. Add it only after legacy-compatible parity is proven.

## 3.7 Extract a testable plain-JS runtime core

Create:

```text
form-app/runtime-core.js
```

Move or mirror pure logic into testable functions:

```js
evaluateConditionSet();
resolveAvailability();
computeAutoAdded();
resolveDependencyRequirements();
resolveExclusiveConflicts();
resolvePrice();
buildLineItems();
buildExportPayload();
migrateSavedSelection();
```

Keep `app.js` as the DOM/controller layer.

This enables unit tests without a browser framework.

## 3.8 Runtime optimizations, all feature-flagged

Allowed plain-JS improvements:

```text
Set-based selection state
selection-signature memoization
dirty-flag condition evaluation
reverse indexes from selected option -> affected condition sets
single-tick condition memoization
event delegation on the form container
DocumentFragment rendering for large groups
requestAnimationFrame batching for DOM updates
no repeated full-array scans in hot paths
no JSON reserialization during export
```

Example cache key:

```js
function selectionSignature(state) {
  return [
    state.bodyStyle,
    state.trimLevel,
    state.selectedInterior || "",
    [...state.selected].sort().join(","),
  ].join("|");
}
```

Runtime feature flags:

```js
window.STINGRAY_FEATURES = {
  useGeneratedIndexes: true,
  useConditionMemo: true,
  useBatchedDomUpdates: false,
  useVariantShards: false,
};
```

If any regression appears, disable the flag and fall back to legacy behavior.

## 3.9 Production observability for runtime data problems

Because this is a static app, observability can stay lightweight:

```text
Expose non-PII diagnostic metadata in window.__orderDebug.
Log schema/data compatibility errors clearly.
Render a blocking user-visible message if data.js is incompatible.
Keep data.validation warnings/errors surfaced in the app.
Add optional "Copy diagnostics" button for support.
Include build_id, schema_version, app_contract_version, active model, variant, and failed rule ID.
Never include customer PII in diagnostics by default.
```

For hosted deployments, add a simple error-reporting hook only if approved:

```js
window.addEventListener("error", (event) => {
  console.error("[stingray-runtime-error]", {
    message: event.message,
    build_id: data?.dataset?.build_id,
    schema_version: data?.dataset?.schema_version,
  });
});
```

---

# 4. Validation and Quality Assurance

Validation must be two-tiered:

```text
Tier 1: automated validation and regression tests
Tier 2: manual QA checklist
```

No cutover until both tiers pass.

---

## Tier 1 — Automated Unit, Regression, and Parity Suite

### 4.1 Schema validation

Add:

```text
scripts/validate_stingray_data.py
```

Validate `datapackage.yaml` and all CSVs for:

```text
required fields
types
enums
primary keys
foreign keys
boolean values
ISO dates
integer money fields
regex patterns
empty/null conventions
```

### 4.2 Semantic validation

Add checks that fail CI if:

1. Any referenced selectable, variant, section, item set, condition set, price book, or price policy is missing.
2. Any item set has no active members.
3. Any condition set cannot compile.
4. Any AND group contains impossible terms, such as `body_style = coupe` and `body_style = convertible`.
5. Any auto-add cycle exists without an explicit reviewed escape hatch.
6. Any auto-add target lacks a price policy.
7. Any dependency rule lacks a human-readable message.
8. Two active static price rules can both win for the same target/scope/priority.
9. Additive/subtractive price rules are not explicitly marked stackable.
10. A displayed selectable lacks availability behavior.
11. A required price behavior is missing.
12. A lookup template contains a token outside the allowlist.
13. A source note contains terms such as `Requires`, `Included with`, `Not available with`, `Deletes`, or `without`, but no structured rule exists.
14. Effective dates overlap ambiguously for the same rule/price/scope.
15. Deprecated rows are referenced by active rows without an alias or migration rule.
16. Compiler business logic contains hard-coded Stingray RPO branches.
17. Generated artifacts are stale relative to CSV source.

### 4.3 Golden build fixtures

Add normalized fixtures:

```text
data/stingray/validation/golden_builds.csv
data/stingray/validation/golden_build_selections.csv
data/stingray/validation/golden_expected_lines.csv
data/stingray/validation/golden_expected_requirements.csv
data/stingray/validation/golden_expected_conflicts.csv
```

Minimum golden scenarios:

| Scenario                          | Expected assertion                                                  |
| --------------------------------- | ------------------------------------------------------------------- |
| `gb_coupe_b6p`                    | B6P selected on Coupe auto-adds SL1 at `$0`.                        |
| `gb_coupe_bcp`                    | BCP selected on Coupe costs `$695`; D3V auto-added at `$0`.         |
| `gb_coupe_bcp_b6p`                | BCP + B6P on Coupe makes BCP `$595`; SL1 and D3V included at `$0`.  |
| `gb_convertible_bcp_missing_zz3`  | BCP on Convertible creates ZZ3 open requirement and blocks submit.  |
| `gb_convertible_bcp_with_zz3`     | Adding ZZ3 clears the requirement.                                  |
| `gb_exclusive_engine_covers`      | BCP + BC4 triggers LS6 engine-cover exclusivity conflict.           |
| `gb_sl1_then_b6p`                 | Explicit SL1 becomes included when B6P is selected.                 |
| `gb_sl1_then_b6p_then_remove_b6p` | Removing B6P restores explicit SL1 standalone price.                |
| `gb_multi_trigger_d3v`            | Multiple D3V triggers do not duplicate D3V.                         |
| `gb_b6p_on_convertible`           | B6P is unavailable/hidden on Convertible according to availability. |
| `gb_interior_component_lookup`    | Interior component price comes from lookup table.                   |
| `gb_export_json`                  | Export JSON shape and values match baseline.                        |
| `gb_export_csv`                   | Export CSV rows and ordering match baseline.                        |

### 4.4 Runtime unit tests

Use Node’s built-in runner:

```sh
node --test tests/*.mjs
```

Add:

```text
tests/stingray/
  data-shape.test.mjs
  condition-engine.test.mjs
  availability.test.mjs
  selection-basics.test.mjs
  exclusive-groups.test.mjs
  auto-adds.test.mjs
  dependencies.test.mjs
  pricing.test.mjs
  pricing-provenance.test.mjs
  interior-components.test.mjs
  color-overrides.test.mjs
  export-json-parity.test.mjs
  export-csv-parity.test.mjs
  saved-selection-migration.test.mjs
  cache-compatibility.test.mjs
  accessibility-static.test.mjs
```

Each behavior test should run against:

```text
baseline Excel-generated data.js
new CSV-generated data.js
```

The same input sequence must produce the same visible outcome.

### 4.5 Output parity tests

Normalize before diffing:

```text
sort arrays by stable ID
normalize booleans
normalize null/empty values
normalize integer prices
ignore generated_at timestamps
preserve order where user-visible order matters
```

Compare:

```text
variant count
step count
section count
choice count
rule count
price rule count
rule group count
exclusive group count
interior count
color override count
standard equipment count
choice fields used by app.js
section/order fields
status/selectable/display behavior
base prices
price rule outputs
auto-added RPOs
open requirements
export JSON
export CSV
```

During phases 1–5:

```text
Empty normalized diff required for migrated slice.
Unmigrated areas may still come from legacy path.
Any intentional diff must be in validation/allowed_diffs.yaml with a change_log row.
```

### 4.6 Generated artifact staleness check

CI command:

```sh
python scripts/compile_stingray_data.py
git diff --exit-code form-app/data.js form-output/
```

After optional Node compiler cutover:

```sh
node scripts/compile-stingray-data.mjs
git diff --exit-code form-app/data.js form-output/
```

### 4.7 Combinatorial and property-based testing

Golden tests are necessary but not enough. Add systematic fuzz/property coverage:

```text
For each variant:
  generate random valid/invalid selection sequences
  compare Excel output vs CSV output
  compare order-dependent sequences for idempotence
  test all option pairs in high-risk sections
  test all exclusive group pairs
  test all auto-add source/target combinations
  test all dependency source/target combinations
```

Core invariants:

```text
No duplicate line items.
No negative prices unless explicitly allowed.
Auto-add closure reaches fixed point.
Removing a trigger removes only auto provenance, not explicit provenance.
All conflicts are explainable.
All open requirements reference valid condition sets.
Reconcile is idempotent: reconcile(reconcile(state)) = reconcile(state).
Selection order does not change final result except where legacy behavior intentionally does.
Every exported RPO exists in catalog/selectables or aliases.
```

Use deterministic pseudo-random seeds so failures are reproducible:

```sh
node --test tests/stingray/property-fuzz.test.mjs --seed=20260501
```

### 4.8 No-framework guard

Add:

```text
scripts/check-no-frameworks.mjs
```

Fail if `package.json` or lockfiles introduce:

```text
react
vue
svelte
angular
next
nuxt
vite
webpack
parcel
rollup frontend bundle requirement
typescript runtime/build requirement
```

Allow only explicitly approved dev-only tooling.

### 4.9 Performance CI

Add:

```text
tests/perf/stingray-runtime-benchmark.mjs
```

Track:

```text
data load time
index build time
condition evaluation time
auto-add resolution time
price resolution time
export time
```

Fail on meaningful regression, for example:

```text
>10% slower than baseline without approved waiver
```

---

## Tier 2 — Manual QA Checklist

Manual QA must be run side-by-side:

```text
A. current main / Excel-generated app
B. refactor branch / CSV-generated app
```

Use the same click sequences and compare visible behavior, totals, messages, and exports.

### 4.10 Environment matrix

Test:

```text
Chrome latest
Firefox latest
Safari latest
Edge latest
desktop viewport
tablet-width viewport
mobile-width viewport
```

Variants:

```text
1LT Coupe
2LT Coupe
3LT Coupe
1LT Convertible
2LT Convertible
3LT Convertible
```

### 4.11 Initial load

- [ ] App opens directly from `form-app/index.html`.
- [ ] App works when served with `python3 -m http.server`.
- [ ] No console errors.
- [ ] No schema/data compatibility warning.
- [ ] App title/model label is correct.
- [ ] Initial body style and trim match baseline.
- [ ] Initial base price matches baseline.
- [ ] Default selections match baseline.
- [ ] Standard equipment count and grouping match baseline.
- [ ] First render feels equal or faster.

### 4.12 Body style and trim flow

For each variant:

- [ ] Body style selection works.
- [ ] Trim selection works.
- [ ] Base MSRP changes correctly.
- [ ] Switching body style removes invalid selections exactly as before.
- [ ] Switching trim reconciles selected options exactly as before.
- [ ] Default FE1/NGA/BC7-style selections behave exactly as before.
- [ ] Hidden/unavailable rows remain hidden/unavailable.

### 4.13 Step and section parity

For every step:

- [ ] Step order is unchanged.
- [ ] Section order is unchanged.
- [ ] Card order is unchanged.
- [ ] Section labels match baseline.
- [ ] Selection-mode labels match baseline.
- [ ] Single-select sections replace prior selections.
- [ ] Optional single-select sections can deselect if currently allowed.
- [ ] Multi-select sections allow multiple choices.
- [ ] Required sections still appear in open requirements when missing.

### 4.14 Critical Stingray rule parity

Engine appearance:

- [ ] Coupe + B6P auto-adds SL1 at `$0`.
- [ ] SL1 selected explicitly, then B6P selected: SL1 becomes included at `$0`.
- [ ] B6P removed after explicit SL1: SL1 returns to standalone explicit price.
- [ ] Convertible does not allow B6P if baseline hides/disables it.
- [ ] Coupe + BCP/BCS/BC4 auto-adds D3V at `$0`.
- [ ] Coupe + BCP/BCS/BC4 without B6P prices engine cover at `$695`.
- [ ] Coupe + BCP/BCS/BC4 with B6P prices engine cover at `$595`.
- [ ] Convertible + BCP/BCS/BC4 without ZZ3 shows the exact ZZ3 requirement.
- [ ] Adding ZZ3 clears the requirement.
- [ ] BCP, BCS, BC4, and BC7 remain mutually exclusive per baseline.

Other high-risk groups:

- [ ] Spoilers remain mutually exclusive.
- [ ] Center caps remain mutually exclusive.
- [ ] Indoor car covers remain mutually exclusive.
- [ ] Outdoor car covers remain mutually exclusive.
- [ ] Trunk liners remain mutually exclusive.
- [ ] Z51 still reconciles FE1/FE2 behavior.
- [ ] NWI still reconciles NGA behavior.
- [ ] GBA still reconciles ZYC behavior.
- [ ] 5ZU approved-color requirement behaves the same.
- [ ] 5V7 spoiler requirement behaves the same.
- [ ] D30/R6X interior price behavior is unchanged.

### 4.15 Pricing and summary

For each golden build:

- [ ] Base vehicle price matches.
- [ ] Every selected option price matches.
- [ ] Every auto-added option price matches.
- [ ] Included items display as `$0` where expected.
- [ ] Interior price matches.
- [ ] Interior component prices match.
- [ ] Section totals match.
- [ ] Options total matches.
- [ ] Final MSRP matches.
- [ ] Removing options recalculates totals exactly as before.

### 4.16 Export parity

For representative builds:

- [ ] Export JSON from baseline.
- [ ] Export JSON from refactor.
- [ ] Normalize and diff.
- [ ] Export CSV from baseline.
- [ ] Export CSV from refactor.
- [ ] Normalize and diff.

Verify:

- [ ] Customer name.
- [ ] Customer address.
- [ ] Customer email.
- [ ] Customer phone.
- [ ] Customer comments.
- [ ] Vehicle info.
- [ ] Selected options.
- [ ] Auto-added options.
- [ ] Interior components.
- [ ] Standard equipment summary.
- [ ] Open requirements.
- [ ] Pricing totals.
- [ ] Section ordering.
- [ ] Line-item ordering.

### 4.17 Persisted/saved/imported state

- [ ] Legacy exported JSON imports or migrates correctly.
- [ ] Legacy option IDs map through aliases.
- [ ] Legacy RPO-only selections map where supported.
- [ ] LocalStorage state, if present, is versioned and migrates.
- [ ] Bookmark/query-string state, if present, remains compatible or shows a clear migration message.
- [ ] Unknown IDs produce a clear warning, not a broken app.

### 4.18 Accessibility regression QA

Check disabled states, validation messages, and interactive cards:

- [ ] All selectable cards are keyboard reachable.
- [ ] Disabled/unavailable options are announced correctly.
- [ ] Auto-added options are distinguishable from user-selected options.
- [ ] Open requirements are announced in the alert/summary region.
- [ ] Focus is not lost after selecting/deselecting an option.
- [ ] Focus moves predictably after step changes.
- [ ] Color is not the only indicator of selected/disabled/error state.
- [ ] Contrast remains acceptable.
- [ ] Export buttons are keyboard accessible.
- [ ] Screen reader smoke test passes for one full build path.

### 4.19 Deployment/cache smoke test

- [ ] Hard refresh loads matching `app.js` and `data.js`.
- [ ] App reports matching `build_id`.
- [ ] Old cached `app.js` with new `data.js` shows a blocking compatibility error.
- [ ] New `app.js` with old `data.js` shows a blocking compatibility error.
- [ ] `index.html` cache policy prevents stale shell after deploy.
- [ ] Rollback deploy restores a working baseline.

### 4.20 Performance smoke test

- [ ] Initial render is equal or faster than baseline.
- [ ] Body/trim switching is equal or faster.
- [ ] Option toggling has no visible lag.
- [ ] Auto-add-heavy selections have no jank.
- [ ] Export JSON/CSV is equal or faster.
- [ ] DevTools shows no new long tasks over 50ms during normal interaction.

### 4.21 Manual sign-off block

```text
Tester:
Date:
Baseline SHA:
Refactor SHA:
Browsers tested:
Variants tested:
Golden builds tested:
Export parity complete: yes / no
Accessibility smoke complete: yes / no
Performance smoke complete: yes / no
Deployment/cache smoke complete: yes / no
Discrepancies: none / see attached
Approved to merge: yes / no
```

---

# CSV Authoring Governance After Cutover

After CSV becomes canonical, add governance so non-engineer edits remain safe.

## Required files

```text
data/stingray/meta/source_refs.csv
data/stingray/meta/change_log.csv
data/stingray/meta/enum_values.csv
data/stingray/meta/workbook_column_map.csv
docs/stingray-data-authoring.md
.github/CODEOWNERS
.github/pull_request_template.md
```

## Policy

```text
Business-rule CSV changes require data owner review.
Pricing changes require pricing owner review.
Schema changes require engineering owner review.
Generated artifacts must be regenerated in the same PR.
Every rule/price row needs source_ref_id and change_id.
Notes are informational only and must never drive logic.
No comma-separated lists in canonical business tables.
No formulas as source data.
CSV ordering is normalized by tooling.
```

## Editor workbook workflow

If spreadsheet editing is needed:

```text
1. Run scripts/export_editor_workbook.py.
2. Business user edits generated stingray_editor.xlsx.
3. Protected ID columns stay locked.
4. Dropdowns come from enum_values.csv and FK tables.
5. Run scripts/import_editor_workbook.py.
6. Normalize CSV.
7. Run validation, golden tests, parity tests.
8. Commit CSV only, not edited Excel as canonical source.
```

Excel safeguards:

```text
format IDs/RPOs as text
freeze headers
protect primary keys
data-validation dropdowns for enums
conditional formatting for inactive/deprecated rows
one sheet per canonical CSV
no formulas as canonical data
validator catches date/encoding/empty-cell drift
```

---

# Final Cutover Criteria

Merge `refactor/schema-csv` to `main` only when all are true:

- [ ] CSV package fully represents Stingray source data.
- [ ] Workbook inventory has zero `needs_review` rows.
- [ ] `form-app/data.js` remains contract-compatible.
- [ ] Existing Stingray regression tests pass.
- [ ] Schema validation passes.
- [ ] Semantic validation passes.
- [ ] Golden build tests pass.
- [ ] CSV-vs-Excel output parity passes.
- [ ] Export JSON/CSV parity passes.
- [ ] Property/fuzz tests pass.
- [ ] Generated artifacts are not stale.
- [ ] No modern frontend framework or bundler has been introduced.
- [ ] Accessibility smoke QA passes.
- [ ] Deployment/cache compatibility checks pass.
- [ ] Performance is equal or better than baseline.
- [ ] Manual QA is signed off for all six variants across required browsers.
- [ ] `STINGRAY_SOURCE=csv` has run as CI default for at least one full week.
- [ ] Rollback to `STINGRAY_SOURCE=xlsx` has been rehearsed successfully.
- [ ] Excel is archived or generated-only.
- [ ] CSV authoring governance is documented.

## Rollback plan

If a production issue appears after cutover:

```sh
git revert <cutover-merge-sha>
# or temporarily:
STINGRAY_SOURCE=xlsx python scripts/generate_stingray_form.py
```

Then redeploy the last known-good `form-app/data.js` and `form-output/` from the tagged baseline.

---

# Summary

This plan keeps the Stingray form safe by freezing the existing runtime/export contract, introducing the CSV Data Package beside the workbook, migrating one vertical slice at a time, validating every phase against the Excel baseline, and only optimizing after behavioral parity is proven. Performance improves through generated indexes, precompiled conditions, compile-time price resolution, memoized runtime logic, and batched DOM updates — all while keeping the browser app plain JavaScript and dependency-light.
