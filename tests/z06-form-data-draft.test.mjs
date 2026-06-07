import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import fs from "node:fs";
import test from "node:test";

const draftPath = "form-output/inspection/z06-form-data-draft.json";
const draftMarkdownPath = "form-output/inspection/z06-form-data-draft.md";
const appDataPath = "form-app/data.js";
const expectedVariantIds = ["1lz_h07", "2lz_h07", "3lz_h07", "1lz_h67", "2lz_h67", "3lz_h67"];
const standardSections = new Set([
  "sec_stan_001",
  "sec_1lte_001",
  "sec_2lte_001",
  "sec_3lte_001",
  "sec_incl_001",
  "sec_safe_001",
  "sec_stan_002",
  "sec_tech_001",
]);

function generateDraftWithoutAppMutation() {
  const beforeAppData = fs.readFileSync(appDataPath, "utf8");
  execFileSync(".venv/bin/python", ["scripts/generate_z06_form.py"], {
    encoding: "utf8",
    stdio: "pipe",
  });
  const afterAppData = fs.readFileSync(appDataPath, "utf8");
  assert.equal(afterAppData, beforeAppData, "Z06 draft generation must not mutate form-app/data.js");
  assert.ok(fs.existsSync(draftPath), "Z06 draft JSON should exist");
  assert.ok(fs.existsSync(draftMarkdownPath), "Z06 draft Markdown should exist");
  return JSON.parse(fs.readFileSync(draftPath, "utf8"));
}

const draft = generateDraftWithoutAppMutation();

test("Z06 draft preserves the live generated-data top-level contract", () => {
  for (const key of [
    "dataset",
    "variants",
    "steps",
    "sections",
    "contextChoices",
    "choices",
    "standardEquipment",
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
  assert.equal(draft.dataset.status, "draft_not_runtime_active");
  assert.equal(draft.dataset.model, "Z06");
  assert.equal(draft.dataset.source_sheet, "z06_options");
  assert.deepEqual(
    draft.variants.map((variant) => variant.variant_id),
    expectedVariantIds
  );
  assert.ok(draft.choices.length > 0, "Z06 draft should include choices");
  assert.ok(draft.standardEquipment.length > 0, "Z06 draft should include standard equipment rows");
});

test("Z06 draft unifies carbon fiber wheels into the Wheels section and keeps package/Z07 placements", () => {
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

test("Z06 draft keeps default-selected options selectable", () => {
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


test("Z06 draft emits approved package/wheel, Z07, and engine-lighting price rules", () => {
  const priceRuleById = new Map(draft.priceRules.map((rule) => [rule.price_rule_id, rule]));
  for (const [ruleId, conditionOptionId, targetOptionId, priceValue] of [
    ["z06_pr_z07_j57_zero", "opt_z07_001", "opt_j57_001", 0],
    ["z06_pr_bcw_d3v_zero", "opt_bcw_001", "opt_d3v_001", 0],
    ["z06_pr_roy_pdb_16000", "opt_roy_001", "opt_pdb_001", 16000],
    ["z06_pr_roz_pdb_17000", "opt_roz_001", "opt_pdb_001", 17000],
    ["z06_pr_stz_pdb_17500", "opt_stz_001", "opt_pdb_001", 17500],
    ["z06_pr_roy_pdd_25495", "opt_roy_001", "opt_pdd_001", 25495],
    ["z06_pr_roy_pdf_26495", "opt_roy_001", "opt_pdf_001", 26495],
  ]) {
    const rule = priceRuleById.get(ruleId);
    assert.ok(rule, `${ruleId} should be emitted`);
    assert.equal(rule.condition_option_id, conditionOptionId);
    assert.equal(rule.target_option_id, targetOptionId);
    assert.equal(rule.price_rule_type, "override");
    assert.equal(rule.price_value, priceValue);
  }
});

test("Z06 draft emits forced Z07 aero and package wheel defaults", () => {
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

test("Z06 draft emits strict Z07/PDB blocker groups for invalid brake and aero peers", () => {
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

test("Z06 draft emits carbon-wheel package blockers for aluminum wheel peers", () => {
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

test("Z06 draft keeps BCW price override without auto-adding BCW from B6P", () => {
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

test("Z06 draft keeps suspension out of customer choice sections and in equipment summaries", () => {
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

test("Z06 draft does not emit priced standard-equipment choices", () => {
  const pricedStandardChoices = draft.choices.filter(
    (choice) => standardSections.has(choice.section_id) && Number(choice.base_price || 0) > 0
  );
  assert.deepEqual(
    pricedStandardChoices.map((choice) => `${choice.choice_id}:${choice.rpo}:${choice.section_id}:${choice.base_price}`),
    []
  );
});

test("Z06 draft source-data guards keep runtime-review rows canonical", () => {
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
