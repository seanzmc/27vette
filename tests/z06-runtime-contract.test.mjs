import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";

import { cell, modelSourceSheet, workbookRows, workbookTruth, workbookTruthy } from "./lib/workbook-truth.mjs";

const MODEL_KEY = "z06";

// Checkpoint 2 of the fast layered validation suite (spec §9) replaced two
// literals that opened this file. Both restated workbook rows: the six variant
// ids, and the eight sections that hold standard equipment. Neither is a
// decision this gate owns — `model_variants` owns the first and
// `section_presentation.standard_equipment_bucket` owns the second — so both
// now read through the §6.2 workbook-truth snapshot and follow a valid
// workbook change instead of failing on it.
const truth = workbookTruth();
const expectedVariantIds = truth.models[MODEL_KEY].variants.map((variant) => variant.variant_id);

const modelPresentationRows = workbookRows("section_presentation").filter(
  (row) => row.model_key === MODEL_KEY && workbookTruthy(row.active),
);
const standardSections = new Set(
  modelPresentationRows.filter((row) => workbookTruthy(row.standard_equipment_bucket)).map((row) => row.section_id),
);
const fullLengthStripeOptionIds = [
  "opt_dpb_001", "opt_dpc_001", "opt_dpg_001", "opt_dpl_001", "opt_dpt_001", "opt_dsy_001", "opt_dsz_001", "opt_dt0_001",
  "opt_dth_001", "opt_dub_001", "opt_due_001", "opt_duk_001", "opt_duw_001", "opt_dzu_001", "opt_dzv_001", "opt_dzx_001",
];

// The composed candidate lane owns fresh generation and source parity. Keep
// this file as focused retained-contract/product evidence only.
const draft = JSON.parse(fs.readFileSync("form-output/runtime/z06-runtime-contract.json", "utf8"));

test("Z06 retained runtime contract preserves the required top-level contract", () => {
  for (const key of [
    "dataset",
    "variants",
    "steps",
    "sections",
    "contextChoices",
    "choices",
    "standardEquipment",
    "orderSummary",
    "ruleGroups",
    "exclusiveGroups",
    "rules",
    "priceRules",
    "interiors",
    "colorOverrides",
    "defaultSelectionRules",
    "validation",
  ]) {
    assert.ok(Object.hasOwn(draft, key), `draft is missing ${key}`);
  }
  assert.equal(draft.dataset.status, "runtime_active");
  assert.equal(draft.dataset.model, truth.models[MODEL_KEY].model_label);
  assert.equal(draft.dataset.source_sheet, modelSourceSheet(MODEL_KEY, "source_option_sheet"));
  assert.deepEqual(
    draft.variants.map((variant) => variant.variant_id).sort(),
    [...expectedVariantIds].sort()
  );
  assert.equal(draft.steps.every((step) => step.source !== "fallback_config"), true);
  assert.deepEqual(
    draft.orderSummary.sections.map((section) => section.section_key).sort(),
    workbookRows("order_summary_sections")
      .filter((row) => row.model_key === MODEL_KEY && workbookTruthy(row.active))
      .map((row) => row.section_key)
      .sort()
  );
  assert.deepEqual(
    Object.keys(draft.orderSummary.stepMap).sort(),
    [
      ...new Set(
        workbookRows("step_order_summary_map")
          .filter((row) => row.model_key === MODEL_KEY && workbookTruthy(row.active))
          .map((row) => row.step_key)
      ),
    ].sort()
  );
  assert.ok(standardSections.size > 0, "the workbook marks no Z06 section as a standard-equipment bucket");
  assert.equal(draft.orderSummary.stepMap.packages_performance, "performance_mechanical");
  assert.equal(draft.orderSummary.stepMap.standard_equipment, "required_charges");
  assert.ok(draft.choices.length > 0, "Z06 runtime contract should include choices");
  assert.ok(draft.standardEquipment.length > 0, "Z06 runtime contract should include standard equipment rows");
});

test("Z06 shared forged and carbon wheel choices follow the cross-model order", () => {
  const wheels = draft.choices
    .filter((choice) => choice.variant_id === "1lz_h07" && choice.section_id === "sec_whee_002")
    .sort((a, b) => Number(a.display_order) - Number(b.display_order))
    .map((choice) => [choice.rpo, choice.base_price, choice.display_order, choice.label]);

  assert.deepEqual(JSON.parse(JSON.stringify(wheels)), [
    ["SOE", 0, 10, "Titanium Satin Spider Wheels"],
    ["SRK", 995, 11, "10-Spoke Pearl Nickel Wheels"],
    ["ROU", 995, 12, "Pearl Nickel Wheels"],
    ["SOA", 1095, 20, "Black Spider Wheels"],
    ["SRN", 1095, 21, "10-Spoke Gloss Black Wheels"],
    ["SON", 1095, 22, "Gloss Black Wheels"],
    ["SOM", 1495, 23, "Bright Polished Wheels"],
    ["ROX", 995, 30, "Carbon Flash Machined-Edge Wheels"],
    ["STX", 1995, 31, "10-Spoke Bright Polished Wheels"],
    ["ROY", 11995, 40, "Carbon Flash-Painted Carbon Fiber Wheels"],
    ["ROZ", 13995, 41, "Visible Carbon Fiber Wheels"],
    ["STZ", 15500, 42, "Visible Carbon Fiber Red Stripe Wheels"],
  ]);
});

test("Z06 standard equipment marks trim-equipment sections with LZ labels", () => {
  const trimRows = draft.standardEquipment.filter(
    (row) => row.standard_equipment_group_type === "trim_equipment"
  );
  assert.ok(trimRows.length > 0, "Z06 should emit trim equipment rows for the trim selector");

  const expectedLabelsByTrim = new Map([
    ["1LZ", "1LZ Equipment"],
    ["2LZ", "2LZ Equipment"],
    ["3LZ", "3LZ Equipment"],
  ]);

  const allowedLabels = new Set(expectedLabelsByTrim.values());
  for (const variantId of expectedVariantIds) {
    const variant = draft.variants.find((row) => row.variant_id === variantId);
    const rows = trimRows.filter((row) => row.variant_id === variantId);
    assert.ok(rows.length > 0, `${variantId} should include trim-equipment standard rows`);
    assert.equal(
      rows.some((row) => row.section_name === expectedLabelsByTrim.get(variant.trim_level)),
      true,
      `${variantId} should include the selected ${variant.trim_level} equipment group`
    );
    assert.equal(
      rows.every((row) => allowedLabels.has(row.section_name)),
      true,
      `${variantId} trim-equipment rows should use LZ labels`
    );
  }

  assert.equal(trimRows.some((row) => /^\dLT Equipment$/.test(row.section_name)), false);
});

test("Z06 trim context choices use workbook-owned LZ tooltip copy", () => {
  const tooltipsByTrim = new Map(
    draft.contextChoices
      .filter((choice) => choice.context_type === "trim_level")
      .map((choice) => [choice.value, choice.info_tooltip])
  );
  assert.match(tooltipsByTrim.get("1LZ") || "", /Head-Up Display comes standard/);
  assert.match(tooltipsByTrim.get("2LZ") || "", /comfort and convenience features/);
  assert.match(tooltipsByTrim.get("3LZ") || "", /carbon fiber steering wheel/);
  assert.equal([...tooltipsByTrim.values()].every(Boolean), true);
});

test("Z06 rear hash graphics draft outside the stripe radio section", () => {
  const sectionsByRpo = new Map();
  for (const choice of draft.choices) {
    if (!sectionsByRpo.has(choice.rpo)) sectionsByRpo.set(choice.rpo, new Set());
    sectionsByRpo.get(choice.rpo).add(choice.section_id);
  }

  assert.deepEqual([...sectionsByRpo.get("VPO")].sort(), ["sec_hash_001"]);
  assert.deepEqual([...sectionsByRpo.get("VPW")].sort(), ["sec_hash_001"]);
  assert.deepEqual([...sectionsByRpo.get("SHT")].sort(), ["sec_stri_001"]);
  assert.deepEqual([...sectionsByRpo.get("SNE")].sort(), ["sec_stri_001"]);
  assert.deepEqual([...sectionsByRpo.get("PDA")].sort(), ["sec_jake_001"]);
});

test("Z06 runtime contract unifies carbon fiber wheels into the Wheels section and keeps package/Z07 placements", () => {
  const sectionsByRpo = new Map();
  for (const choice of draft.choices) {
    if (!sectionsByRpo.has(choice.rpo)) {
      sectionsByRpo.set(choice.rpo, new Set());
    }
    sectionsByRpo.get(choice.rpo).add(choice.section_id);
  }

  for (const rpo of ["PDB", "PDD", "PDF"]) {
    assert.deepEqual([...sectionsByRpo.get(rpo)].sort(), ["sec_z06_pkg_001"], `${rpo} should draft in the Z06 wheel/brake package section`);
  }
  for (const rpo of ["ROY", "ROZ", "STZ"]) {
    assert.deepEqual([...sectionsByRpo.get(rpo)].sort(), ["sec_whee_002"], `${rpo} should draft in the unified Wheels section`);
  }
  assert.deepEqual([...sectionsByRpo.get("Z07")].sort(), ["sec_perf_z52_001"], "Z07 should stay in the adjacent Z52 package section");
});

test("Z06 runtime contract keeps default-selected options selectable", () => {
  for (const rpo of ["EFR", "T0E", "J56", "719", "EYT", "J6A", "CF7", "CM9", "AQ9", "SOE"]) {
    const choices = draft.choices.filter((choice) => choice.rpo === rpo);
    assert.ok(choices.length > 0, `${rpo} should be emitted`);
    for (const choice of choices) {
      if (choice.status === "unavailable") {
        continue;
      }
      assert.equal(choice.display_behavior, "default_selected", `${choice.choice_id} should remain default_selected`);
      assert.equal(choice.selectable, "True", `${choice.choice_id} should remain selectable`);
    }
  }
});

test("Z06 gas guzzler tax drafts as standard-equipment default charge with T0F/T0G price overrides", () => {
  const r8eChoices = draft.choices.filter((choice) => choice.option_id === "opt_r8e_002");
  assert.equal(r8eChoices.length, expectedVariantIds.length, "R8E should emit for every Z06 variant");
  assert.deepEqual(r8eChoices.map((choice) => choice.variant_id).sort(), [...expectedVariantIds].sort());
  for (const choice of r8eChoices) {
    assert.equal(choice.rpo, "R8E");
    assert.equal(choice.label, "Gas Guzzler Tax");
    assert.equal(choice.base_price, 2600);
    assert.equal(choice.status, "standard");
    assert.equal(choice.selectable, "True");
    // Receipt C decision 2026-07-26: the key is carried only when it has a value.
    assert.equal(choice.display_behavior, undefined);
    assert.equal(choice.step_key, "standard_equipment");
  }

  const defaultRule = draft.defaultSelectionRules.find((rule) => rule.rule_id === "z06_default_r8e_tax");
  assert.ok(defaultRule, "Z06 should emit a workbook-owned R8E default-selection rule");
  assert.equal(defaultRule.target_option_id, "opt_r8e_002");
  assert.equal(defaultRule.condition_type, "always");

  const priceRulesById = new Map(draft.priceRules.map((rule) => [rule.price_rule_id, rule]));
  for (const [ruleId, conditionOptionId] of [
    ["z06_pr_t0f_r8e_tax_3000", "opt_t0f_001"],
    ["z06_pr_t0g_r8e_tax_3000", "opt_t0g_001"],
  ]) {
    const rule = priceRulesById.get(ruleId);
    assert.ok(rule, `${ruleId} should be emitted`);
    assert.equal(rule.condition_option_id, conditionOptionId);
    assert.equal(rule.target_option_id, "opt_r8e_002");
    assert.equal(rule.price_rule_type, "override");
    assert.equal(rule.price_value, 3000);
  }
});

// Checkpoint 1 of the fast layered validation suite (spec §9) rewrote this
// test. It used to walk a 22-row interior/seatbelt table copied into this file
// and require, for every non-asymmetrical interior, a `requires_any` group
// pairing the included colour with Black — the retired "included colour or
// Black only" behaviour. PR #19 replaced that with the Seatbelt_Rules.txt
// authority, where an alternative colour is available and adds D30 plus its own
// charge, so the group is gone and the table was a parallel copy of workbook
// data. Both sides are read from their owners now: the expected side is a
// direct read of the model's rule-mapping and price-rule sheets, the actual
// side is the generated contract.
test("interior-included options and their price overrides match the workbook source rows", () => {
  const interiorIds = new Set(draft.interiors.map((interior) => interior.interior_id));
  const optionIds = new Set(draft.choices.map((choice) => choice.option_id));

  const ruleRows = workbookRows(modelSourceSheet(MODEL_KEY, "rule_mapping_sheet"));
  const expectedIncludes = ruleRows
    .filter(
      (row) =>
        cell(row.rule_type).toLowerCase() === "includes" &&
        interiorIds.has(cell(row.source_id)) &&
        optionIds.has(cell(row.target_id)),
    )
    .map((row) => `${cell(row.source_id)}::${cell(row.target_id)}`)
    .sort();

  const actualIncludes = draft.rules
    .filter((rule) => rule.rule_type === "includes" && interiorIds.has(rule.source_id))
    .map((rule) => `${rule.source_id}::${rule.target_id}`)
    .sort();

  assert.ok(expectedIncludes.length > 0, "no interior-sourced includes row resolves into the contract");
  assert.deepEqual(
    actualIncludes,
    expectedIncludes,
    "emitted interior-sourced includes rules drifted from their workbook rows",
  );

  // Every emitted interior include must carry the source row's customer copy
  // and auto-add flag; a dropped disabled_reason is invisible to the set
  // comparison above and reaches the browser.
  const sourceById = new Map(ruleRows.map((row) => [cell(row.rule_id), row]));
  for (const rule of draft.rules.filter((row) => row.rule_type === "includes" && interiorIds.has(row.source_id))) {
    const source = sourceById.get(rule.rule_id);
    assert.ok(source, `${rule.rule_id} is not a workbook-authored rule row`);
    assert.equal(rule.disabled_reason, cell(source.disabled_reason), `${rule.rule_id} disabled_reason drifted`);
    assert.equal(rule.auto_add, "True", `${rule.rule_id} should auto-add its included option`);
    assert.equal(rule.active, "True", `${rule.rule_id} should be emitted active`);
  }

  const priceRows = workbookRows(modelSourceSheet(MODEL_KEY, "price_rules_sheet"));
  const priceIdentity = (conditionId, targetId, type, value) =>
    `${conditionId}::${targetId}::${type}::${Number(value)}`;
  const expectedInteriorPrices = priceRows
    .filter(
      (row) =>
        interiorIds.has(cell(row.condition_option_id)) && optionIds.has(cell(row.target_option_id)),
    )
    .map((row) =>
      priceIdentity(
        cell(row.condition_option_id),
        cell(row.target_option_id),
        cell(row.price_rule_type).toLowerCase(),
        row.price_value,
      ),
    )
    .sort();
  const actualInteriorPrices = draft.priceRules
    .filter((rule) => interiorIds.has(rule.condition_option_id))
    .map((rule) =>
      priceIdentity(rule.condition_option_id, rule.target_option_id, rule.price_rule_type, rule.price_value),
    )
    .sort();

  assert.ok(expectedInteriorPrices.length > 0, "no interior-conditioned price rule resolves into the contract");
  assert.deepEqual(
    actualInteriorPrices,
    expectedInteriorPrices,
    "emitted interior-conditioned price rules drifted from their workbook rows",
  );
});

test("Z06 GBA excludes CBF and EDU, not CFL, through workbook group metadata", () => {
  const group = draft.ruleGroups.find((row) => row.group_id === "z06_group_gba_excludes_accent_and_roof_choices");
  assert.ok(group, "GBA blocker group should exist");
  assert.equal(group.source_id, "opt_gba_001");
  assert.equal(group.group_type, "excludes_any");
  assert.ok(group.target_ids.includes("opt_cbf_001"), "GBA should block CBF");
  assert.ok(group.target_ids.includes("opt_edu_001"), "GBA should block EDU");
  assert.equal(group.target_ids.includes("opt_cfl_001"), false, "GBA should not block CFL");
});

test("Z06 CBF drafts with availability, direct blockers, and package/aero replacement rules", () => {
  const cbfChoices = draft.choices.filter((choice) => choice.option_id === "opt_cbf_001");
  assert.equal(cbfChoices.length, expectedVariantIds.length, "CBF should emit for every Z06 variant");
  assert.deepEqual(cbfChoices.map((choice) => choice.variant_id).sort(), [...expectedVariantIds].sort());
  for (const choice of cbfChoices) {
    assert.equal(choice.rpo, "CBF");
    assert.equal(choice.label, "Body-color painted Rockers and splitter");
    assert.equal(choice.base_price, 495);
    assert.equal(choice.section_id, "sec_exte_001");
    assert.equal(choice.status, "available");
    assert.equal(choice.selectable, "True");
    assert.equal(choice.active, "True");
    assert.equal(choice.display_order, 25);
  }

  const exteriorAccentGroup = draft.exclusiveGroups.find((row) => row.group_id === "z06_excl_exterior_accents");
  assert.equal(exteriorAccentGroup.option_ids.includes("opt_cbf_001"), false, "CBF should not be an exterior-accent exclusive peer");

  const ruleById = new Map(draft.rules.map((rule) => [rule.rule_id, rule]));
  for (const [ruleId, targetId] of [
    ["z06_rule_opt_cbf_001_excludes_opt_cfv_002", "opt_cfv_002"],
    ["z06_rule_opt_cbf_001_excludes_opt_cfz_001", "opt_cfz_001"],
    ["z06_rule_opt_cbf_001_excludes_opt_efy_001", "opt_efy_001"],
  ]) {
    const rule = ruleById.get(ruleId);
    assert.ok(rule, `${ruleId} should emit`);
    assert.equal(rule.source_id, "opt_cbf_001");
    assert.equal(rule.rule_type, "excludes");
    assert.equal(rule.target_id, targetId);
    assert.equal(rule.runtime_action, "active");
  }

  // The five package/aero swap rules are generation-derived (rule_derivation.py,
  // allowlist-gated) since the Phase B deletion of the hand-stacked workbook rows
  // (docs/archive/completed-specs/derived-swap-eviction-spec-2026-07-02.md). Copy is generated verbose text.
  for (const [ruleId, sourceId, reasonPattern] of [
    ["derived_opt_t0f_001_replaces_opt_cbf_001", "opt_t0f_001", /CBF.*removed.*T0F.*includes.*CFZ.*replaces it/i],
    ["derived_opt_t0g_001_replaces_opt_cbf_001", "opt_t0g_001", /CBF.*removed.*T0G.*includes.*CFV.*replaces it/i],
    ["derived_opt_z07_001_replaces_opt_cbf_001", "opt_z07_001", /CBF.*removed.*Z07.*includes.*CFZ.*replaces it/i],
    ["derived_opt_pdd_001_replaces_opt_cbf_001", "opt_pdd_001", /CBF.*removed.*PDD.*includes.*CFZ.*replaces it/i],
    ["derived_opt_pdf_001_replaces_opt_cbf_001", "opt_pdf_001", /CBF.*removed.*PDF.*includes.*CFV.*replaces it/i],
  ]) {
    const rule = ruleById.get(ruleId);
    assert.ok(rule, `${ruleId} should emit`);
    assert.equal(rule.source_id, sourceId);
    assert.equal(rule.rule_type, "excludes");
    assert.equal(rule.target_id, "opt_cbf_001");
    assert.equal(rule.runtime_action, "replace");
    assert.match(rule.disabled_reason, reasonPattern);
  }
});

test("Z06 seatbelt colors are exclusive peers for interior-included locks", () => {
  const group = draft.exclusiveGroups.find((row) => row.group_id === "z06_excl_seat_belts");
  assert.ok(group, "Z06 seatbelt exclusive group should exist");
  assert.equal(group.selection_mode, "single_within_group");
  assert.deepEqual(group.option_ids, ["opt_719_001", "opt_3n9_001", "opt_379_001", "opt_3a9_001", "opt_3f9_001", "opt_3m9_001"]);
});


test("Z06 runtime contract emits approved package/wheel, Z07, and engine-lighting price rules", () => {
  const priceRuleById = new Map(draft.priceRules.map((rule) => [rule.price_rule_id, rule]));
  for (const [ruleId, conditionOptionId, targetOptionId, priceValue] of [
    ["z06_pr_z07_j57_zero", "opt_z07_001", "opt_j57_001", 0],
    ["z06_pr_bcw_d3v_zero", "opt_bcw_001", "opt_d3v_001", 0],
    ["z06_pr_roy_pdb_16000", "opt_roy_001", "opt_pdb_001", 16000],
    ["z06_pr_roz_pdb_17000", "opt_roz_001", "opt_pdb_001", 17000],
    ["z06_pr_stz_pdb_17500", "opt_stz_001", "opt_pdb_001", 17500],
    ["z06_pr_roy_pdd_25495", "opt_roy_001", "opt_pdd_001", 25495],
    ["z06_pr_roy_pdf_26495", "opt_roy_001", "opt_pdf_001", 26495],
    ["z06_pr_t0f_r8e_tax_3000", "opt_t0f_001", "opt_r8e_002", 3000],
    ["z06_pr_t0g_r8e_tax_3000", "opt_t0g_001", "opt_r8e_002", 3000],
    ["z06_pr_pda_sne_001", "opt_pda_001", "opt_sne_001", 0],
    ["z06_pr_pda_vpw_001", "opt_pda_001", "opt_vpw_001", 0],
  ]) {
    const rule = priceRuleById.get(ruleId);
    assert.ok(rule, `${ruleId} should be emitted`);
    assert.equal(rule.condition_option_id, conditionOptionId);
    assert.equal(rule.target_option_id, targetOptionId);
    assert.equal(rule.price_rule_type, "override");
    assert.equal(rule.price_value, priceValue);
  }
});

test("Z06 indoor car cover exclusive group includes WKS", () => {
  const group = draft.exclusiveGroups.find((item) => item.group_id === "z06_excl_indoor_car_covers");
  assert.ok(group, "Z06 indoor car cover exclusive group should be emitted");
  assert.equal(group.selection_mode, "single_within_group");
  assert.deepEqual(group.option_ids, ["opt_rwh_001", "opt_wkr_001", "opt_wks_001"]);
});

test("Z06 runtime contract emits forced Z07 aero and package wheel defaults", () => {
  const activeIncludePairs = new Set(
    draft.rules
      .filter((rule) => rule.rule_type === "includes" && rule.active === "True")
      .map((rule) => `${rule.source_id}->${rule.target_id}`)
  );
  for (const [sourceId, targetId] of [
    ["opt_bcw_001", "opt_d3v_001"],
    ["opt_z07_001", "opt_t0f_001"],
    ["opt_t0f_001", "opt_cfz_001"],
    ["opt_t0g_001", "opt_cfv_002"],
    ["opt_pdb_001", "opt_roy_001"],
    ["opt_pdd_001", "opt_roy_001"],
    ["opt_pdf_001", "opt_roy_001"],
  ]) {
    assert.equal(activeIncludePairs.has(`${sourceId}->${targetId}`), true, `${sourceId} should include/default ${targetId}`);
  }

  const matchingRequiredGroup = (sourceId, targetIds) => draft.ruleGroups.find((group) => (
    group.source_id === sourceId
    && group.group_type === "requires_any"
    && JSON.stringify(group.target_ids) === JSON.stringify(targetIds)
  ));
  assert.ok(matchingRequiredGroup("opt_z07_001", ["opt_t0f_001", "opt_t0g_001"]), "Z07 should require one of T0F/T0G");
  for (const sourceId of ["opt_pdb_001", "opt_pdd_001", "opt_pdf_001"]) {
    assert.ok(matchingRequiredGroup(sourceId, ["opt_roy_001", "opt_roz_001", "opt_stz_001"]), `${sourceId} should require one of ROY/ROZ/STZ`);
  }
});

test("Z06 runtime contract emits workbook-owned Jake graphic stripe conflict groups", () => {
  const groupsById = new Map(draft.ruleGroups.map((group) => [group.group_id, group]));
  for (const [groupId, sourceId, targetIds] of [
    ["z06_group_pda_excludes_dual_racing_stripes", "opt_pda_001", fullLengthStripeOptionIds],
    ["z06_group_sne_excludes_stripes_and_tech_bronze_jake", "opt_sne_001", [...fullLengthStripeOptionIds, "opt_sht_001", "opt_vpo_001"]],
    ["z06_group_sht_excludes_full_length_stripes", "opt_sht_001", [...fullLengthStripeOptionIds, "opt_sne_001", "opt_vpw_001"]],
    ["z06_group_vpw_excludes_tech_bronze_jake", "opt_vpw_001", ["opt_sht_001", "opt_vpo_001"]],
    ["z06_group_vpo_excludes_jake_graphics", "opt_vpo_001", ["opt_sne_001", "opt_vpw_001"]],
    ["z06_group_dpb_excludes_jake_hood_graphics", "opt_dpb_001", ["opt_sht_001", "opt_sne_001"]],
  ]) {
    const group = groupsById.get(groupId);
    assert.ok(group, `${groupId} should be emitted`);
    assert.equal(group.group_type, "excludes_any");
    assert.equal(group.source_id, sourceId);
    assert.deepEqual(group.target_ids, targetIds);
  }

  const activeIncludePairs = new Set(
    draft.rules
      .filter((rule) => rule.rule_type === "includes" && rule.active === "True")
      .map((rule) => `${rule.source_id}->${rule.target_id}`)
  );
  assert.equal(activeIncludePairs.has("opt_pda_001->opt_sne_001"), true);
  assert.equal(activeIncludePairs.has("opt_pda_001->opt_vpw_001"), true);
});

test("Z06 runtime contract emits strict Z07/PDB blocker groups for invalid brake and aero peers", () => {
  const groupsById = new Map(draft.ruleGroups.map((group) => [group.group_id, group]));
  for (const [groupId, sourceId, targetIds, reasonPattern] of [
    ["z06_group_z07_excludes_non_z07_aero", "opt_z07_001", ["opt_t0e_001", "opt_5zv_001"], /Z07|T0F|T0G|aero/i],
    ["z06_group_z07_excludes_j56_brakes", "opt_z07_001", ["opt_j56_001"], /Z07|J57|carbon ceramic/i],
    ["z06_group_pdb_excludes_j56_brakes", "opt_pdb_001", ["opt_j56_001"], /PDB|J57|carbon ceramic/i],
  ]) {
    const group = groupsById.get(groupId);
    assert.ok(group, `${groupId} should be emitted`);
    assert.equal(group.group_type, "excludes_any");
    assert.equal(group.source_id, sourceId);
    assert.deepEqual(group.target_ids, targetIds);
    assert.match(group.disabled_reason || "", reasonPattern);
  }
});

test("Z06 runtime contract emits carbon-wheel package blockers for aluminum wheel peers", () => {
  const groupsById = new Map(draft.ruleGroups.map((group) => [group.group_id, group]));
  const aluminumWheelIds = [
    "opt_soe_002",
    "opt_srk_001",
    "opt_rou_001",
    "opt_soa_001",
    "opt_srn_001",
    "opt_son_001",
    "opt_rox_001",
    "opt_som_001",
    "opt_stx_001",
  ];
  const carbonWheelIds = ["opt_roy_001", "opt_roz_001", "opt_stz_001"];

  for (const [groupId, sourceId, reasonPattern] of [
    ["z06_group_pdb_excludes_aluminum_wheels", "opt_pdb_001", /PDB|ROY|ROZ|STZ|carbon fiber wheels/i],
    ["z06_group_pdd_excludes_aluminum_wheels", "opt_pdd_001", /PDD|ROY|ROZ|STZ|carbon fiber wheels/i],
    ["z06_group_pdf_excludes_aluminum_wheels", "opt_pdf_001", /PDF|ROY|ROZ|STZ|carbon fiber wheels/i],
  ]) {
    const group = groupsById.get(groupId);
    assert.ok(group, `${groupId} should be emitted`);
    assert.equal(group.group_type, "excludes_any");
    assert.equal(group.source_id, sourceId);
    assert.deepEqual(group.target_ids, aluminumWheelIds);
    assert.match(group.disabled_reason || "", reasonPattern);
    for (const carbonWheelId of carbonWheelIds) {
      assert.equal(group.target_ids.includes(carbonWheelId), false, `${groupId} should not block ${carbonWheelId}`);
    }
  }
});

test("Z06 runtime contract keeps BCW price override without auto-adding BCW from B6P", () => {
  const b6pBcwPrice = draft.priceRules.find((rule) => rule.price_rule_id === "z06_pr_b6p_bcw_895_coupe");
  assert.ok(b6pBcwPrice, "B6P should still own the BCW price override");
  assert.equal(b6pBcwPrice.condition_option_id, "opt_b6p_001");
  assert.equal(b6pBcwPrice.target_option_id, "opt_bcw_001");
  assert.equal(b6pBcwPrice.price_rule_type, "override");
  assert.equal(b6pBcwPrice.price_value, 895);

  const autoBcwRules = draft.rules.filter(
    (rule) => rule.rule_type === "includes" && rule.target_id === "opt_bcw_001" && rule.active === "True"
  );
  assert.deepEqual(
    autoBcwRules.map((rule) => `${rule.source_id}->${rule.target_id}`),
    [],
    "BCW should not be auto-added by B6P/D3V; it should remain a selectable priced choice"
  );
});

test("Z06 runtime contract keeps suspension out of customer choice sections and in equipment summaries", () => {
  const visibleSuspensionChoices = draft.choices.filter(
    (choice) => choice.section_id === "sec_susp_001" && choice.step_key !== "standard_equipment"
  );
  assert.deepEqual(
    visibleSuspensionChoices.map((choice) => `${choice.choice_id}:${choice.rpo}:${choice.status}:${choice.step_key}`),
    [],
    "Z06 suspension rows should not render as customer choice cards"
  );

  const equipmentRpos = new Set(draft.standardEquipment.map((row) => row.rpo));
  assert.equal(equipmentRpos.has("FE6"), true, "standard FE6 suspension should be listed in standard equipment");

  const fe7Choices = draft.choices.filter((choice) => choice.rpo === "FE7");
  assert.ok(fe7Choices.length > 0, "FE7 should still be emitted as Z07-included equipment");
  assert.equal(fe7Choices.every((choice) => choice.step_key === "standard_equipment"), true);
  assert.equal(fe7Choices.every((choice) => choice.display_behavior === "auto_only"), true);
  assert.ok(
    draft.rules.some((rule) => rule.source_id === "opt_z07_001" && rule.rule_type === "includes" && rule.target_id === "opt_fe7_001"),
    "Z07 should continue to include FE7 suspension"
  );
});

test("Z06 interiors group by customer-facing color family instead of interior code", () => {
  const byId = new Map(draft.interiors.map((interior) => [interior.interior_id, interior]));
  assert.equal(byId.get("1LZ_AQ9_HTA")?.interior_color_family, "Jet Black");
  assert.equal(byId.get("1LZ_AE4_HTJ_N26")?.interior_color_family, "Jet Black");

  const groupsForTrim = (trimLevel) => new Set(
    draft.interiors
      .filter((interior) => interior.trim_level === trimLevel)
      .map((interior) => interior.interior_color_family)
  );

  assert.deepEqual(groupsForTrim("3LZ"), new Set([
    "Jet Black",
    "Sky Cool Gray",
    "Adrenaline Red",
    "Adrenaline Red Dipped",
    "Natural",
    "Natural Dipped",
    "Santorini Blue",
    "Very Dark Atmosphere",
    "Ultimate Suede Jet Black",
    "Habanero",
    "Asymmetrical Santorini Blue / Jet Black",
    "Asymmetrical Adrenaline Red / Jet Black",
    "Custom Interior trim and seat combinations",
  ]));
  assert.equal(byId.get("3LZ_R6X_AH2_HZB")?.interior_color_family, "Custom Interior trim and seat combinations");
  assert.equal(byId.has("3LZ_AH2_EL9"), false, "EL9 Santorini Blue Dipped is Grand Sport-only and should not emit for Z06");
  assert.equal(byId.has("3LZ_AE4_EL9"), false, "EL9 Santorini Blue Dipped is Grand Sport-only and should not emit for Z06");
  assert.match(byId.get("1LZ_AQ9_HTA")?.interior_hierarchy_path || "", /AQ9 Seats/);
  assert.match(byId.get("1LZ_AE4_HTJ_N26")?.interior_hierarchy_path || "", /AE4 Seats/);
  assert.match(byId.get("1LZ_AQ9_HTA")?.interior_parent_group_label || "", /AQ9 Seats/);
  assert.match(byId.get("1LZ_AE4_HTJ_N26")?.interior_parent_group_label || "", /AE4 Seats/);
});

test("Z06 N26, suede, two-tone, and custom stitch source rows do not render as selectable option-step cards", () => {
  for (const rpo of ["N26", "N2Z", "TU7", "36S", "37S", "38S"]) {
    const choices = draft.choices.filter((choice) => choice.rpo === rpo);
    assert.equal(
      choices.every((choice) => choice.selectable !== "True" || choice.step_key === "standard_equipment"),
      true,
      `${rpo} should not remain a selectable option-step choice`
    );
    assert.equal(
      choices.every((choice) => choice.display_behavior === "hidden" || choice.step_key === "standard_equipment"),
      true,
      `${rpo} should be hidden from selectable customer option steps`
    );
  }

  const componentRpos = new Set(
    draft.interiors.flatMap((interior) => (interior.interior_components || []).map((component) => component.rpo))
  );
  assert.equal(componentRpos.has("N26"), true, "N26 should still auto-add through applicable interior component data");
  for (const rpo of ["36S", "37S", "38S"]) {
    assert.equal(
      draft.interiors.some((interior) => String(interior.interior_id).includes(`_${rpo}`) || interior.stitch === rpo || componentRpos.has(rpo)),
      true,
      `${rpo} should remain represented by interior/component source evidence`
    );
  }
});

test("Z06 runtime contract does not emit priced standard-equipment choices", () => {
  const pricedStandardChoices = draft.choices.filter(
    (choice) => choice.option_id !== "opt_r8e_002" && standardSections.has(choice.section_id) && Number(choice.base_price || 0) > 0
  );
  assert.deepEqual(
    pricedStandardChoices.map((choice) => `${choice.choice_id}:${choice.rpo}:${choice.section_id}:${choice.base_price}`),
    []
  );
});

test("Z06 runtime contract keeps source-data rows canonical", () => {
  const missingDisplayOrder = draft.choices.filter((choice) => choice.display_order === "" || choice.display_order == null);
  assert.deepEqual(
    missingDisplayOrder.map((choice) => `${choice.choice_id}:${choice.rpo}:${choice.section_id}`),
    []
  );

  const nonSelectableDefaults = draft.choices.filter(
    (choice) => choice.display_behavior === "default_selected" && choice.selectable !== "True"
  );
  assert.deepEqual(
    nonSelectableDefaults.map((choice) => `${choice.choice_id}:${choice.rpo}:${choice.section_id}:${choice.selectable}`),
    []
  );
});
