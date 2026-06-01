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

test("Z06 draft emits approved package, wheel, and standalone Z07 placements", () => {
  const sectionsByRpo = new Map();
  for (const choice of draft.choices) {
    if (!sectionsByRpo.has(choice.rpo)) {
      sectionsByRpo.set(choice.rpo, new Set());
    }
    sectionsByRpo.get(choice.rpo).add(choice.section_id);
  }

  for (const rpo of ["PDB", "PDD", "PDF"]) {
    assert.deepEqual([...sectionsByRpo.get(rpo)].sort(), ["sec_z06_pkg_001"], `${rpo} should draft in the Z06 package section`);
  }
  for (const rpo of ["ROY", "ROZ", "STZ"]) {
    assert.deepEqual([...sectionsByRpo.get(rpo)].sort(), ["sec_z06_cf_whee_001"], `${rpo} should draft in the Z06 carbon fiber wheel section`);
  }
  assert.deepEqual([...sectionsByRpo.get("Z07")].sort(), ["sec_perf_z52_001"], "Z07 should stay in the adjacent Z52 package section");
});

test("Z06 draft keeps default-selected options selectable", () => {
  for (const rpo of ["EFR", "T0E", "J56", "719"]) {
    const choices = draft.choices.filter((choice) => choice.rpo === rpo);
    assert.ok(choices.length > 0, `${rpo} should be emitted`);
    for (const choice of choices) {
      assert.equal(choice.display_behavior, "default_selected", `${choice.choice_id} should remain default_selected`);
      assert.equal(choice.selectable, "True", `${choice.choice_id} should remain selectable`);
    }
  }
});

test("Z06 draft emits approved package/wheel and Z07 price rules", () => {
  const priceRuleById = new Map(draft.priceRules.map((rule) => [rule.price_rule_id, rule]));
  for (const [ruleId, conditionOptionId, targetOptionId, priceValue] of [
    ["z06_pr_z07_j57_zero", "opt_z07_001", "opt_j57_001", 0],
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
