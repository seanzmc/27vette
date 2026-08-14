# Independent Verifier Report — Promoted Artifact Refresh

Repo: `/Users/seandm/Projects/27vette` (branch `db-workflow`)
Pre-change baseline: `2a0b1d1a7c6521267be10cccdc979ee0fdcbcc0f`
Verifier wrote no repository files except this report.

## Verdict

**PASS** — I could not refute the core claim: across all three promoted models there are **zero** additions or removals of any choice, standardEquipment row, rule, priceRule, interior, colorOverride, variant, ruleGroup, exclusiveGroup, contextChoice, or defaultSelectionRule, and every published difference traces to a row in the canonical (byte-unchanged) workbook — but the maker's change summary **understates the customer-visible surface** in two places (claims 3 and 4), which should be corrected in the run receipt.

## Criteria

| # | Claim | Result | How I checked |
|---|---|---|---|
| A | Per-collection add/remove/field-change diff, keyed by own stable identity | **PASS** | Wrote `diffcontract.py`, keying `standardEquipment` on `equipment_id`, `choices` on `choice_id`, `rules` on `rule_id`, etc. (13 collections, explicit key map; also asserted zero duplicate ids on both sides so keying is sound). Added=0 / Removed=0 for **every** product collection in all three models. Only `sections` changed cardinality. |
| 1 | No product row added or removed | **PASS** | See table below. Nothing to refute. |
| 2 | `sec_perf_support_001` → `sec_perf_001`, 12 choices move `wheels` → `packages_performance`, 1 rule `source_section` updated; Stingray had zero rows | **PASS** | Grand Sport and Z06: exactly 12 choices each change `section_id`+`step_key`; exactly 1 rule per model changes `source_section`. Stingray already carried `sec_perf_001` (18 populated choices) *and* an empty `sec_perf_support_001`; the latter was an orphan with zero rows and merely disappears. Confirmed Stingray choice field-changes = 0. |
| 3 | `sec_perf_z52_001` renamed "Z52 Packages" → "Performance Packages", order 10 → 11 | **PASS, but INCOMPLETE** | Rename and order change confirmed and workbook-authored. **Undisclosed second rename:** `sec_z06_cf_whee_001` "Z06 Carbon Fiber Wheel Selection" → "Z06 Carbon Fiber Wheel Packages" (Stingray contract). Also workbook-authored; inert for Stingray because that section has zero rows. |
| 4 | Five standard-equipment section display orders re-sequenced | **PASS, but INCOMPLETE** | All five confirmed. **Four more were omitted:** `sec_stan_001` 20→30, `sec_stan_002` 10→35, `sec_tech_001` 40→45 (all `standard_equipment` step), and `sec_susp_001` 20→25 (`packages_performance`, Stingray). Total display-order changes are 10 (Stingray), 9 (GS), 8 (Z06) — not 5. All workbook-authored. |
| 5 | Stingray `dataset` gained `model` / `model_year` / `status: runtime_active` | **PASS** | Diff shows exactly those three keys added (`Stingray`, `2027`, `runtime_active`) plus the expected `generated_at` bump. Confirmed these are precisely the fields the strict validator demanded (see F). |
| 6 / C | Stingray `choices` diff is order-only | **PASS (proved exactly)** | `Counter(json.dumps(row, sort_keys=True))` over old vs new is **equal** (multiset of full payloads identical); id set identical; id multiset identical; `sorted(serialized)` identical; array order differs. Same proof holds for Stingray `standardEquipment`. This is stronger than a per-id compare because it also rules out duplicate-row shuffling. |
| B | Every published section value traceable to the workbook | **PASS** | `openpyxl` read-only on `section_master` / `section_presentation`. Every new value matches a `section_master` row: `sec_perf_001` (Mechanical / order 10 / `locked_included` / `packages_performance`), `sec_perf_z52_001` (Performance Packages / 11), `sec_z06_cf_whee_001` (…Wheel Packages / 15), `sec_spec_001` 5, `sec_incl_001` 15, `sec_3lte_001` 25, `sec_susp_001` 25, `sec_stan_001` 30, `sec_exha_001` 35, `sec_stan_002` 35, `sec_safe_001` 40, `sec_tech_001` 45. Old values match none of these. Full-workbook string scan across all 77 sheets: **`sec_perf_support` occurs 0 times.** No published value is untraceable. |
| D | Registry `form-app/data.js` consistent | **PASS** | Wrote a brace-matching parser to extract `window.CORVETTE_FORM_DATA` from both versions. `defaultModelKey` = `stingray` (unchanged); models exactly `{stingray, grandSport, z06}` in identical order; zero wrapper-field diffs on all three; per-model `data` payload diff is **identical** to the contract diff, collection by collection. `window.STINGRAY_FORM_DATA = window.CORVETTE_FORM_DATA.models.stingray.data;` present and unchanged in both. |
| E | Workbook byte-unchanged | **PASS** | `git status --porcelain -- stingray_master.xlsx` → empty. `shasum -a 256` → `8858cff40ea7eaeda6b7921714f3697a6ee9d1bbc99c84e564d7b118e45b2166` — exact match. |
| F | Validators clean now, 1 error before | **PASS (both halves reproduced)** | Current: schema `valid`, 0 issues; package `valid`, 0 issues. I then rebuilt an isolated temp tree with the **pre-change** artifacts and re-ran the validator, reproducing the exact prior failure (see below). |
| G | No dangling references / customer-facing breakage | **PASS** | Wrote `integrity.py` checking choice→section, choice→step, choice-in-step-`section_ids`, choice `section_name` agreement, SE/interior/contextChoice/rule→section, step`section_ids`→section, section→step. Ran on OLD and NEW for all three models and categorized every problem. Category counts are **byte-identical** old vs new. Zero occurrences of "choice section NOT IN sections", "section NOT LISTED in step section_ids", "step references missing section", or section_name mismatch in either version. The 12 moved choices all resolve cleanly. |
| H | Customer-visible? Half-migrated? | **PASS with notes** | See section below. |

### A — per-collection counts (added / removed / field-changed), old → new

| Collection | Stingray | Grand Sport | Z06 |
|---|---|---|---|
| choices | 0/0/0 (order only) | 0/0/24 | 0/0/18 |
| standardEquipment (key `equipment_id`) | 0/0/0 (order only) | 0/0/0 | 0/0/0 |
| rules | 0/0/0 | 0/0/1 (`source_section`) | 0/0/1 (`source_section`) |
| priceRules | 0/0/0 | 0/0/0 | 0/0/0 |
| interiors | 0/0/0 | 0/0/0 | 0/0/0 |
| colorOverrides | 0/0/0 | 0/0/0 | 0/0/0 |
| variants | 0/0/0 | 0/0/0 | 0/0/0 |
| ruleGroups | 0/0/0 | 0/0/0 | 0/0/0 |
| exclusiveGroups | 0/0/0 | 0/0/0 | 0/0/0 |
| contextChoices | 0/0/0 | 0/0/0 | 0/0/0 |
| defaultSelectionRules | 0/0/0 | 0/0/0 | 0/0/0 |
| orderSummary | identical | identical | identical |
| sections | 0/1/11 | 1/1/9 | 1/1/8 |
| steps | 0/0/1 | 0/0/2 | 0/0/2 |

The only Stingray `validation` delta is a Python dict-repr key-ordering difference inside one `pass` message string (`{'standard': 467, 'available': 809, 'unavailable': 140}` vs `…'unavailable': 140, 'available': 809`) — same numbers, cosmetic.

### Strongest single check: full reproducibility

I regenerated all three models into a **temp** `--output-root` and compared to the published artifacts:

```
stingray    reproducible (ignoring generated_at): True
grand-sport reproducible (ignoring generated_at): True
z06         reproducible (ignoring generated_at): True
```

The published artifacts are byte-exact what the unchanged canonical workbook produces. This is the cleanest refutation-attempt failure: there is no room for injected drift.

### H — customer-visible behavior, and one genuinely half-migrated area

**Customer-visible (all workbook-authored, all intended):**
1. **12 options move step** on Grand Sport and Z06 — e.g. `Front Lift Adjustable Height` (E60, $2,995) and `Battery Protection Package` (ERI, $100) now render under **Performance & Aero** instead of **Wheels & Brake Calipers**. This is a real relocation of priced options in the customer flow.
2. **Section rename** "Z52 Packages" → "Performance Packages" — visible on Grand Sport (12 choices) and Z06 (6 choices). Not visible on Stingray (section is empty there).
3. **Section reordering** within the Standard Equipment and Performance & Aero steps: `app.js:2630-2638` sorts choices by `sectionsById.get(...).section_display_order`, so the re-sequencing changes on-screen block order. Most notable: `sec_spec_001` (Special Edition) 110 → 5 moves it from last to first in Performance & Aero.
4. `sec_z06_cf_whee_001` rename — **not** customer-visible today (zero rows in the only contract carrying it).

**Not customer-visible / inert:** I grepped `form-app/` and `app.js` reads neither `step.section_ids` nor `section.standard_behavior` — both appear only as inert payload in `data.js`. So (a) the Stingray `wheels.section_ids` shrink is harmless, and (b) the `standard_behavior` shift `user_selected` → `locked_included` that comes with `sec_perf_support_001` → `sec_perf_001` has **no runtime effect in the form app** (worth knowing, since on paper it reads like a selectability change). This is the one place the maker's summary was silent where I initially suspected drift; it checks out as inert.

**Half-migrated (pre-existing, not caused by this change):** three retained non-promoted contracts still carry the removed section — `form-output/runtime/grand-sport-x-runtime-contract.json` (15 hits), `zr1-runtime-contract.json` (11), `zr1x-runtime-contract.json` (11) all still reference `sec_perf_support_001`, which exists nowhere in the workbook. They are not in the published registry and the validators do not flag them, so this is not blocking — but the retained-contract set is now internally inconsistent, and this is exactly the staleness class that caused the original Pass G1 failure. Same latent trap, different files.

**Stale test assertions (pre-existing):** `tests/grand-sport-contract-preview.test.mjs:67-68` and `tests/grand-sport-draft-data.test.mjs:826-827` assert `sectionById.get("sec_perf_support_001")?.step_key === "wheels"` / `?.section_name === "Mechanical"`. Both tests regenerate the preview fresh from the workbook, where that section does not exist — I confirmed this by generating the preview into a temp dir (`sec_perf_support_001 present in fresh preview: False`), so `?.` yields `undefined` and both assertions fail. Because the workbook is unchanged, **these were already failing before the refresh**; the refresh neither caused nor fixed them. I did not run the tests themselves, since they invoke `generate_form.py` without `--output-root` and would rewrite tracked artifacts.

## Evidence inspected

- `git show 2a0b1d1:form-output/runtime/{stingray,grand-sport,z06}-runtime-contract.json` vs working tree.
- `git show 2a0b1d1:form-app/data.js` vs `/Users/seandm/Projects/27vette/form-app/data.js`.
- `/Users/seandm/Projects/27vette/stingray_master.xlsx` — sheets `section_master` (48 rows), `section_presentation` (57 rows), plus a full-string scan of all 77 sheets.
- `/Users/seandm/Projects/27vette/form-app/app.js` — `renderStepContent` (2595-2653), the section sort (2630-2638), `renderSectionTitle` (2020-2027), `sectionsById` build (136).
- `/Users/seandm/Projects/27vette/scripts/corvette_form_generator/schema_validation.py` (live-contract freshness path, 235-270 / 1198-1224).
- `/Users/seandm/Projects/27vette/tests/grand-sport-contract-preview.test.mjs`, `/Users/seandm/Projects/27vette/tests/grand-sport-draft-data.test.mjs`.
- Also-modified working-tree artifacts, checked for drift beyond the claimed scope:
  - `form-output/stingray-form-data.json` — diff identical in kind to the Stingray contract; zero product add/remove.
  - `form-output/stingray-form-data.csv` — 662 changed lines, but `diff <(sort old) <(sort new)` is **0 lines**: pure row reordering, zero content drift.
  - `form-output/inspection/{stingray,grand-sport,z06}-derived-swap-manifest.json` — recursively flattened and compared leaf-by-leaf: **zero differing leaves** (trailing-whitespace only).
- Verifier probes (temp, not in repo): `scratchpad/diffcontract.py`, `scratchpad/integrity.py`, `scratchpad/parse_datajs.py`.

## Validation Output Inspected

Current tree:

```
$ .venv/bin/python scripts/validate_workbook_schema.py stingray_master.xlsx
{ "workbook": "stingray_master.xlsx", "status": "valid",
  "issue_count": 0, "error_count": 0, "warning_count": 0, "issues": [] }        exit 0

$ .venv/bin/python scripts/validate_workbook_package.py stingray_master.xlsx
{ "workbook": "stingray_master.xlsx", "status": "valid",
  "issue_count": 0, "issues": [] }                                             exit 0
```

Pre-change reproduction (isolated temp tree: copy of the unchanged workbook + `HEAD` versions of `form-app/data.js` and the three runtime contracts). Control run with current artifacts in the same tree returned `valid`, 0 issues, confirming the tree itself is not the variable:

```
{ "status": "invalid", "issue_count": 1, "error_count": 1,
  "issues": [ { "severity": "error",
    "check_id": "app_registry_freshness_check_failed",
    "sheet": "form-app/data.js",
    "message": "Could not validate app registry freshness: Runtime contract
       .../stingray-runtime-contract.json is not publishable
       (dataset.model must be a non-empty string;
        dataset.model_year must be a non-empty string;
        dataset.status is None, expected 'runtime_active';
        dataset.model is None, expected 'Stingray').
       Correct the workbook/source generation error and regenerate it." } ] }
```

This confirms both the "1 error → 0 errors" claim and the stated root cause exactly.

Not run, deliberately: `z06-runtime-promotion` and the two `grand-sport-*` node tests, all of which invoke `generate_form.py` / `generate_registry.py` against repository paths and would rewrite tracked artifacts.

## Required Fixes Before Pass

None.

Non-blocking follow-ups (none of these are regressions from this change):

1. Correct the run receipt: claim 3 omits the `sec_z06_cf_whee_001` rename, and claim 4 lists 5 of the 9 display-order changes. The summary understates the customer-visible surface even though the underlying work is sound.
2. `tests/grand-sport-contract-preview.test.mjs:67-68` and `tests/grand-sport-draft-data.test.mjs:826-827` assert on `sec_perf_support_001`, which the workbook no longer defines. Already failing pre-change; should be retargeted to `sec_perf_001` / `packages_performance`.
3. `grand-sport-x`, `zr1`, `zr1x` retained contracts still carry `sec_perf_support_001`. Consider regenerating or explicitly marking them stale-by-design.

## Durable Lesson Candidates

1. **Key every collection by its own identity before claiming "no drift."** `standardEquipment` keys on `equipment_id`, not `section_id`; keying on the wrong column manufactures false "changed" counts and can mask real ones. Assert zero duplicate ids on both sides, or the keying itself is unverified.
2. **Prove "order-only" with a multiset of serialized payloads, not a per-id compare.** `Counter(json.dumps(row, sort_keys=True))` equality rules out duplicate-row shuffling that a per-id diff silently tolerates.
3. **Regenerate into a temp `--output-root` and compare to the published artifact.** Byte-reproducibility from the canonical source is a stronger claim than any hand-enumerated diff, and it is cheap. It leaves no room for undisclosed drift.
4. **Reproduce the "before" failure, don't just assert the "after" pass.** Rebuilding a temp tree with `HEAD` artifacts turned "previously 1 error" from a claim into evidence, and confirmed the stated root cause rather than merely a coincident fix.
5. **Artifact staleness recurs wherever generated files are committed.** The Pass G1 failure was stale promoted contracts; the same class still sits in the non-promoted retained contracts and in two test files. A freshness check that covers only promoted artifacts will keep letting this through.
6. **Check whether a changed field is actually read before calling it a behavior change.** `standard_behavior` and `step.section_ids` both changed and both look alarming; neither is consumed by `app.js`. Grep the consumer before escalating.

## File Edit Statement

I edited exactly one file: `fable5loop/runs/2026-07-25-promoted-artifact-refresh/verifier-report.md` (this report).

I modified no source, artifact, workbook, or test file. `stingray_master.xlsx` is byte-unchanged (SHA-256 verified). All generation I ran used `--output-root` / `--inspection-output` pointed at the scratchpad; `git status --porcelain -- form-output form-app` after my runs lists exactly the same nine maker-modified files as before them, with no additions. I ran no node tests.
