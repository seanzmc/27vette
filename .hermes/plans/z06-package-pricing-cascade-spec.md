# Z06 Package / Pricing Cascade Spec

## Diagnosis

Change type: mixed workbook data + generated/runtime contract validation. The desired behavior is mostly workbook-owned rules, sections, price rules, exclusive groups, and option prices. Runtime code should only change if current generic mechanics cannot express package-owned locking or cascading choices without RPO-specific JavaScript.

Risk level: high. This pass touches customer-facing pricing and package-selection behavior. It should not be combined with Z model activation or live runtime promotion.

User-provided business decisions captured for this pass:

- Only active options outside the standard-equipment sections that still have blank prices need pricing review.
- Standard-equipment sections excluded from blank-price review are:
  - `sec_stan_001`
  - `sec_1lte_001`
  - `sec_2lte_001`
  - `sec_3lte_001`
  - `sec_incl_001`
  - `sec_safe_001`
  - `sec_stan_002`
  - `sec_tech_001`
- `R8E`, `RYQ`, and `V8X` are primary options that will have prices, but those prices are not released yet.
- Z06 `PDD`, `PDB`, and `PDF` should be grouped together as a package section in the Z06 form.
- The Z06 package section should sit near wheels, performance brakes, aero, and package options so the user does not have to switch steps or go backward to finish package choices.
- The package UX should be cascading:
  - the package choice establishes brakes / Z07 + T0F / Z07 + T0G requirements;
  - then the carbon-fiber wheel choice is presented;
  - package-included options are auto-added from the form;
  - alternate choices within exclusive groups are blocked while the package is selected;
  - included options are not removable unless the package itself is removed.
- If `PDD` is selected, `T0G` should not be selectable.
- `Z07` must require a selection of `T0F` or `T0G`.
- Package-included options such as `J57` must not be removable when included by the package/Z07.
- Z06 `BCW` pricing/availability:
  - normally $995;
  - coupe with `B6P` selected: $895;
  - convertible: only available with `ZZ3`, at $895.
- `T0F` includes `CFZ`, so `CFZ` becomes $0 when included by `T0F`.
- `T0G` includes `CFV`, so `CFV` becomes $0 when included by `T0G`.
- Other package includes such as `Z07` should make included options $0.

Current workbook evidence inspected:

- `z06_options`: 249 active rows.
- `z06_ovs`: 1494 rows.
- `z06_price_rules`: 0 rows.
- `z06_rule_groups`: 0 rows.
- `z06_rule_group_members`: 0 rows.
- `z06_rule_mapping`: 100 rows.
- `z06_exclusive_groups`: 7 rows.
- `z06_exclusive_members`: 16 rows.
- `section_master`: 45 rows.
- Current Z06 package/performance rows:
  - `opt_pdb_001` / `PDB`, row 126, `section_id=sec_perf_z52_001`, blank price.
  - `opt_pdd_001` / `PDD`, row 127, `section_id=sec_perf_z52_001`, blank price.
  - `opt_pdf_001` / `PDF`, row 128, `section_id=sec_perf_z52_001`, blank price.
  - `opt_z07_001` / `Z07`, row 129, `section_id=sec_perf_z52_001`, blank price.
  - `opt_j57_001` / `J57`, row 120, `section_id=sec_perf_brake_001`, price `9000`.
  - `opt_j6d_001` / `J6D`, row 31, `section_id=sec_cali_001`, price `0`.
  - `opt_t0f_001` / `T0F`, row 117, `section_id=sec_perf_aero_001`, blank price.
  - `opt_t0g_001` / `T0G`, row 118, `section_id=sec_perf_aero_001`, blank price.
  - `opt_cfz_001` / `CFZ`, row 123, `section_id=sec_perf_ground_001`, blank price.
  - `opt_cfv_002` / `CFV`, row 122, `section_id=sec_perf_ground_001`, blank price.
  - carbon-fiber wheel choices in `sec_whee_002`: `ROY`, `ROZ`, `STZ`, all blank prices.
  - `opt_bcw_001` / `BCW`, row 47, `section_id=sec_engi_001`, current direct price `995`.
  - `opt_b6p_001` / `B6P`, row 46, `section_id=sec_engi_001`, blank price.
  - `opt_zz3_001` / `ZZ3`, row 54, `section_id=sec_engi_001`, blank price.
- Current relevant rule coverage:
  - `T0F -> includes CFZ` exists in `z06_rule_mapping`.
  - `T0G -> includes CFV` is missing.
  - Only the `T0F -> CFZ` rule surfaced among direct rules involving PDB/PDD/PDF/Z07/T0F/T0G/BCW/J57/J6D/ROY/ROZ/STZ from the initial inspection.
- Current relevant exclusive coverage:
  - `z06_excl_ground_effects` includes `CFZ`; initial inspection did not show `CFV` as active member.
  - `z06_excl_performance_brakes` includes `J57`; default brake `J56` is currently default-selected in options.
  - There is no visible package-specific exclusive/locking group for `PDB/PDD/PDF`.
- Current step placement:
  - `packages_performance` step currently contains `sec_perf_z52_001`, `sec_perf_brake_001`, `sec_perf_aero_001`, `sec_perf_ground_001`, `sec_susp_001`, etc.
  - `wheels` step currently contains `sec_whee_002`, `sec_cali_001`, `sec_whee_001`, and `sec_perf_support_001`.
  - This is a UX problem for the requested package cascade: package/brake/aero choices are one step after wheel/caliper choices, so a package-driven carbon-fiber wheel decision could force users backward unless section/step placement is adjusted.
- Current price-rule/runtime mechanics:
  - `z06_price_rules` has the same header shape as current live price-rule sheets: `price_rule_id`, `condition_option_id`, `price_rule_type`, `target_option_id`, `price_value`, `body_style_scope`, `trim_level_scope`, `review_flag`, `notes`.
  - Runtime `optionPrice()` supports `price_rule_type=override` when `condition_option_id` is selected and body/trim/variant scopes match.
  - Runtime `computeAutoAdded()` auto-adds `includes` targets; `handleChoice()` refuses clicks on auto-added choices, so included options are already non-removable while their source remains selected.
  - Runtime `requires_any` rule groups exist and can block a choice unless at least one grouped target is selected.

Important current inconsistency to resolve explicitly:

- `R8E` is user-confirmed as a primary option with an unreleased future price, but it currently sits in `sec_incl_001`, one of the standard-equipment sections that the user said should be excluded from pricing review. This means the implementation must not accidentally ignore `R8E` forever. Either:
  1. leave it in `sec_incl_001` and record it as a named unreleased-price exception, or
  2. move it out of the included/standard section if product intent says it is not standard equipment.
- Do not infer this choice silently during implementation; make it an explicit decision point.

## Exact files / sheets to change after approval

Expected workbook file:

- `stingray_master.xlsx`

Likely workbook sheets:

- `z06_options`
  - price updates for reviewed non-standard blank-price rows;
  - possible section move for package rows into a Z06 package section;
  - possible direct price decisions for `BCW`, `B6P`, `ZZ3`, `T0F`, `T0G`, `CFZ`, `CFV`, `Z07`, `PDB`, `PDD`, `PDF`, `J57`, `ROY`, `ROZ`, `STZ`, `R8E`, `RYQ`, `V8X` depending approved matrix.
- `z06_price_rules`
  - BCW $895 override under `B6P` on coupe.
  - BCW $895 override under `ZZ3` on convertible.
  - include-driven zero-price overrides where needed for included components (`CFZ` with `T0F`, `CFV` with `T0G`, `J57` with package/Z07, etc.).
- `z06_rule_mapping`
  - add missing package includes/requires/excludes that can be expressed as direct one-to-one rules.
  - add `T0G includes CFV`.
  - add package includes: `PDB -> J57`, `PDB -> J6D`; `PDD -> Z07`, `PDD -> T0F`, `PDD -> CFZ`; `PDF -> Z07`, `PDF -> T0G`, `PDF -> CFV`.
  - add package-vs-alternate excludes where direct one-to-one rules are sufficient, for example `PDD excludes T0G`, `PDF excludes T0F`.
- `z06_rule_groups`
  - add `Z07 requires_any T0F/T0G`.
  - evaluate whether `PDB/PDD/PDF` require a carbon-fiber wheel choice through a grouped requirement over `ROY/ROZ/STZ`, or whether that is better expressed by placing those wheels in a required exclusive group with package-scoped availability.
- `z06_rule_group_members`
  - members for `Z07 -> {T0F,T0G}` requires-any.
  - possible package-to-wheel group members for `PDB/PDD/PDF -> {ROY,ROZ,STZ}` if approved.
- `z06_exclusive_groups`
  - add or extend exclusive groups for package choices and carbon-fiber wheel choices only if existing section single-select behavior is insufficient.
- `z06_exclusive_members`
  - package group members (`PDB`, `PDD`, `PDF`) if needed.
  - carbon-fiber wheel group members (`ROY`, `ROZ`, `STZ`) if needed in a package-scoped group.
  - ground-effects group should include both `CFZ` and `CFV` if both are active runtime choices and intended as peers.
- `section_master`
  - likely add a Z06-specific section such as `sec_z06_pkg_001` or rename/re-scope `sec_perf_z52_001` only if safe for other models.
  - The safer default is a new section for the Z06 package cluster because `sec_perf_z52_001` is currently shared by Grand Sport (`FEB`/`FEY`), Z06 (`PDB`/`PDD`/`PDF`/`Z07`), and ZR1/ZR1X (`ZTK`).
- Possibly `form_steps` / workbook step metadata if the package section and wheel choices must be in the same visible step.

Possible test files if runtime contract support must be proven or extended:

- Existing runtime test surface:
  - `tests/multi-model-runtime-switching.test.mjs`
  - `tests/stingray-form-regression.test.mjs`
- New or extended Z draft/runtime contract tests, if the repo has or needs a Z non-live preview path.
- If generic runtime behavior changes are needed, add behavior tests for:
  - included package components are auto-added and non-removable;
  - selecting package blocks alternate package/aero/ground/wheel peers;
  - `Z07` cannot remain selected without `T0F` or `T0G`;
  - `BCW` displays correct scoped price.

Do not change in this pass unless explicitly expanded:

- `form-app/data.js` live registry.
- Z model/variant activation flags.
- dealer submission endpoint, payload shape, or Turnstile behavior.
- generated `form_*` sheets by hand.
- ZR1/ZR1X sheets, except read-only comparison if necessary.

## Proposed implementation sequence

### Step 1 — Pricing review matrix for blank non-standard Z06 options

Build a read-only matrix of active Z06 options where:

- `price` is blank; and
- `section_id` is not one of the standard-equipment sections.

Current count from inspection: 139 active Z06 non-standard blank-price rows.

Columns should include:

- workbook row;
- `option_id`;
- `rpo`;
- `option_name`;
- `section_id`;
- source/review price evidence from `future_model_source_review` and `z-option-canonical-pricing-matrix.csv` if available;
- recommended price action:
  - direct option price;
  - named unreleased-price placeholder (`R8E`, `RYQ`, `V8X`);
  - included/zero via package rule;
  - conditional price rule;
  - package/cascade behavior;
  - needs human price decision.

Important guard:

- Exclude the standard-equipment sections from the review by default.
- Still surface named exceptions `R8E`, `RYQ`, and `V8X` in an explicit exception block, because the user identified them as primary unreleased-price options.

Pause if the matrix exposes many unknown prices that are not among the named unreleased-price or package/conditional cases.

### Step 2 — Package section / step placement design

Decide the UX placement before writes.

Preferred design to evaluate first:

- Add a Z06-specific package cluster section, for example `sec_z06_pkg_001`, with section name like `Z06 Performance Packages` or `Z06 Carbon Fiber Packages`.
- Place it in the `packages_performance` step near existing `sec_perf_brake_001`, `sec_perf_aero_001`, and `sec_perf_ground_001`.
- Move `PDB`, `PDD`, and `PDF` into that section.
- Keep `Z07` either in that section or adjacent in `sec_perf_z52_001`, depending whether user-facing semantics treat it as part of the package cascade or a standalone performance package.

UX risk:

- The carbon-fiber wheel choices `ROY`, `ROZ`, and `STZ` currently live in `sec_whee_002` under the `wheels` step. If the package cascade needs those wheel choices presented immediately after selecting `PDB/PDD/PDF`, keeping them in the separate `wheels` step may violate the user’s no-step-switch requirement.
- Options to resolve that:
  1. move carbon-fiber wheel choices into a package-scoped subsection in `packages_performance` for Z06;
  2. duplicate presentation is not allowed unless generator/runtime supports one option appearing in multiple sections without duplicate selection state;
  3. move the entire Z06 wheels/calipers step adjacent before/after performance packages, but that affects broader runtime step order;
  4. create a generic conditional follow-up section concept if current workbook/runtime cannot present package-specific wheel choices in the same step.

Do not choose among these silently; the implementation spec should surface the tradeoff and use the smallest approved approach.

### Step 3 — Workbook-owned package behavior rows

Use existing generic row types first:

Direct includes:

- `PDB includes J57`.
- `PDB includes J6D`.
- `PDD includes Z07`.
- `PDD includes T0F`.
- `PDD includes CFZ`.
- `PDF includes Z07`.
- `PDF includes T0G`.
- `PDF includes CFV`.
- `T0G includes CFV`.
- Confirm/keep existing `T0F includes CFZ`.
- Add/confirm `Z07 includes J57` and other Z07-included rows if source detail supports them and the user approves them as non-removable package components.

Requires-any group:

- `Z07 requires_any {T0F, T0G}`.

Package wheel requirement:

- `PDB/PDD/PDF` require one of `{ROY, ROZ, STZ}`.
- Implement as `requires_any` rule groups if current runtime supports one source requiring any one of several target IDs.

Package peer blocking:

- Package section should be single-select or package options should be in a single-within-group exclusive group so only one of `PDB/PDD/PDF` can be selected.
- `PDD` should block `T0G` and `PDF` should block `T0F` through either direct excludes or an approved aero package exclusive group.
- Package-included options should be auto-added by `includes`; current runtime makes auto-added choices non-clickable/non-removable while included.

### Step 4 — Price modeling

Direct option prices:

- Keep `BCW` direct price at $995.
- `R8E`, `RYQ`, `V8X`: leave blank with explicit notes/metadata as unreleased prices, unless a price is provided later.

Price-rule rows:

- `BCW` override to $895 when `B6P` selected and body style is coupe.
- `BCW` override to $895 when `ZZ3` selected and body style is convertible.
- `CFZ` override to $0 when `T0F` selected.
- `CFV` override to $0 when `T0G` selected.
- `J57` override to $0 when included by `Z07`, `PDB`, `PDD`, or `PDF` as approved.
- Add zero-price overrides for any other package-included options with direct/base prices.

Availability/rule row for BCW:

- Need a rule/availability expression for convertible-only-with-`ZZ3` and coupe-with-`B6P` behavior.
- Current direct `requires` rules can express `BCW requires ZZ3`, but that would incorrectly block coupe `BCW` if coupe `B6P` is the alternate enabler.
- This likely needs either:
  - a `requires_any {B6P, ZZ3}` group scoped by body style; or
  - body-style-scoped direct rules if the generator/runtime supports them; or
  - a generic conditional availability extension.
- Do not hardcode `BCW` in JavaScript.

### Step 5 — Generate non-live proof and tests

Because Z is not active in `form-app/data.js`, do not promote live data in this pass. Instead:

- Run workbook validators after write.
- Run `scripts/build_future_z_rule_audit.py --model-key z06 --format markdown` and confirm no missing/inactive references.
- If a Z draft/generated contract path exists, generate a non-live preview and test:
  - selecting `PDB` auto-adds `J57/J6D` and requires/presents one carbon-fiber wheel choice;
  - selecting `PDD` auto-adds `Z07/T0F/CFZ` and blocks `T0G`;
  - selecting `PDF` auto-adds `Z07/T0G/CFV` and blocks `T0F`;
  - selected included components cannot be removed while package remains selected;
  - removing the package releases included components and alternate choices;
  - `Z07` requires one of `T0F/T0G`;
  - `BCW` price is $995 normally and $895 under approved scoped conditions.

## Constraints repeated back

- Spec-first: no workbook/runtime edits before approval.
- Workbook source-of-truth: encode product behavior in workbook sheets where possible.
- No hardcoded RPO-specific JavaScript or Python unless a generic workbook expression cannot represent the behavior and the user approves a runtime extension.
- No live runtime promotion.
- No `form-app/data.js` registry update.
- No dealer submission changes.
- No new dependencies.
- Preserve Stingray and Grand Sport behavior.
- Do not let standard-equipment rows back into pricing review.
- Keep ZR1/ZR1X out of scope unless read-only comparison is needed.

## Approved answers / implementation decisions

1. `R8E` stays in `sec_incl_001` as a named unreleased-price exception for now. Do not move it out of the standard/included section in this pass; it may later need conditional pricing once released.
2. `Z07` remains adjacent as its own performance package in `sec_perf_z52_001`. `PDB`, `PDD`, and `PDF` move into their own Z06 package cluster section so `Z07` can be included by `PDD`/`PDF` without being a peer selection conflict.
3. Move Z06 carbon-fiber wheel choices `ROY`, `ROZ`, and `STZ` into the performance package flow. This requires preserving wheel replacement behavior across sections with workbook-authored replacement/exclusion rules so selecting a carbon-fiber wheel can replace the current wheel choice from the normal wheels section.
4. `PDB`, `PDD`, and `PDF` have real package prices in the raw price schedule, with separate rows per package/wheel combination under the same package RPO. Model these as package target price rules keyed by selected carbon-fiber wheel:
   - `PDB`: `ROY=$16000`, `ROZ=$17000`, `STZ=$17500`.
   - `PDD`: `ROY=$25495`, `ROZ=$26495`, `STZ=$26995`.
   - `PDF`: `ROY=$26495`, `ROZ=$27495`, `STZ=$27995`.
5. `Z07` selection should auto-add `J57`, `FE7`, and `XFS`, then require selection of `T0F` or `T0G`. Only `J57` should become zero-priced when included by `Z07`; `FE7` and `XFS` already have no direct prices, and `T0F`/`T0G` must keep their prices. `PDB`/`PDD`/`PDF` include package-level prices, so their included component price overrides must prevent double-counting while preserving the standalone prices for `Z07`, `T0F`, and `T0G` outside those packages.

## Validation plan after approval

Read-only/dry-run first:

```sh
.venv/bin/python scripts/build_future_z_rule_audit.py --model-key z06 --format markdown
.venv/bin/python scripts/apply_z_option_sheet_repairs.py
.venv/bin/python scripts/validate_workbook_package.py stingray_master.xlsx
.venv/bin/python scripts/validate_workbook_schema.py stingray_master.xlsx
```

After any workbook write:

```sh
.venv/bin/python scripts/validate_workbook_package.py stingray_master.xlsx
.venv/bin/python scripts/validate_workbook_schema.py stingray_master.xlsx
.venv/bin/python scripts/build_future_z_rule_audit.py --model-key z06 --format markdown
```

If generated/runtime contract code is touched or a Z draft contract is generated, add/run targeted tests proving package auto-add, non-removable included choices, exclusive blocking, `Z07` requires-any behavior, and `BCW` scoped pricing.

## Approval needed

Approve this spec before I write workbook data or runtime/generator code. The first implementation subpass should be the read-only pricing/package matrix plus explicit answers to the open questions, unless you want to answer the questions now and approve direct workbook implementation.
