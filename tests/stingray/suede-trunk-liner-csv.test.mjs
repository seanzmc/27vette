import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import test from "node:test";

import { createRuntime, loadGeneratedData, loadShadowData } from "./runtime-harness.mjs";

const PYTHON = ".venv/bin/python";
const SCRIPT = "scripts/stingray_csv_first_slice.py";
const SUEDE_TRUNK_LINER_RPOS = new Set(["SXB", "SXR", "SXT"]);

function evaluate(variantId, selectedIds) {
  const output = execFileSync(PYTHON, [SCRIPT, "--scenario-json", JSON.stringify({ variant_id: variantId, selected_ids: selectedIds })], {
    cwd: process.cwd(),
    encoding: "utf8",
  });
  return JSON.parse(output);
}

function emitCsvLegacyFragment() {
  const output = execFileSync(PYTHON, [SCRIPT, "--emit-legacy-fragment"], {
    cwd: process.cwd(),
    encoding: "utf8",
    maxBuffer: 8 * 1024 * 1024,
  });
  return JSON.parse(output);
}

function optionIdByRpo(data, rpo) {
  const ids = new Set(data.choices.filter((choice) => choice.rpo === rpo).map((choice) => choice.option_id));
  assert.equal(ids.size, 1, `${rpo} should map to exactly one legacy option_id`);
  return [...ids][0];
}

function plain(value) {
  return JSON.parse(JSON.stringify(value));
}

function suedeTrunkLinerOptionIds(data) {
  return new Set(data.choices.filter((choice) => SUEDE_TRUNK_LINER_RPOS.has(choice.rpo)).map((choice) => choice.option_id));
}

function lineById(result, selectableId) {
  return result.selected_lines.find((line) => line.selectable_id === selectableId);
}

function normalizeChoices(rows) {
  return Array.from(rows)
    .filter((choice) => SUEDE_TRUNK_LINER_RPOS.has(choice.rpo))
    .map((choice) => ({
      choice_id: choice.choice_id,
      option_id: choice.option_id,
      rpo: choice.rpo,
      label: choice.label,
      description: choice.description,
      section_id: choice.section_id,
      section_name: choice.section_name,
      category_id: choice.category_id,
      category_name: choice.category_name,
      step_key: choice.step_key,
      variant_id: choice.variant_id,
      body_style: choice.body_style,
      trim_level: choice.trim_level,
      status: choice.status,
      status_label: choice.status_label,
      selectable: choice.selectable,
      active: choice.active,
      choice_mode: choice.choice_mode,
      selection_mode: choice.selection_mode,
      selection_mode_label: choice.selection_mode_label,
      base_price: Number(choice.base_price || 0),
      display_order: Number(choice.display_order || 0),
      source_detail_raw: choice.source_detail_raw,
    }))
    .sort((a, b) => a.choice_id.localeCompare(b.choice_id));
}

function normalizeExclusiveGroups(rows, optionIds) {
  return Array.from(rows)
    .filter((group) => (group.option_ids || []).some((optionId) => optionIds.has(optionId)))
    .map((group) => ({
      group_id: group.group_id,
      option_ids: [...group.option_ids],
      selection_mode: group.selection_mode,
      active: group.active,
      notes: group.notes,
    }))
    .sort((a, b) => a.group_id.localeCompare(b.group_id));
}

function runtimeFor(data, variantId) {
  const runtime = createRuntime(data);
  const variant = data.variants.find((item) => item.variant_id === variantId);
  assert.ok(variant, `${variantId} should exist`);
  runtime.state.bodyStyle = variant.body_style;
  runtime.state.trimLevel = variant.trim_level;
  return runtime;
}

function activeChoiceByRpo(runtime, rpo) {
  const choice = runtime
    .activeChoiceRows()
    .find((item) => item.rpo === rpo && item.active === "True" && item.status !== "unavailable" && item.selectable === "True");
  assert.ok(choice, `${rpo} should have an active selectable choice`);
  return choice;
}

function handleRpo(runtime, rpo) {
  runtime.handleChoice(activeChoiceByRpo(runtime, rpo));
}

function selectedSuedeTrunkLinerRpos(runtime) {
  return [...runtime.state.selected]
    .map((optionId) => runtime.activeChoiceRows().find((choice) => choice.option_id === optionId)?.rpo)
    .filter((rpo) => SUEDE_TRUNK_LINER_RPOS.has(rpo))
    .sort();
}

function productionRulesTouching(data, rpos) {
  const ids = new Set(data.choices.filter((choice) => rpos.has(choice.rpo)).map((choice) => choice.option_id));
  return data.rules.filter((rule) => ids.has(rule.source_id) || ids.has(rule.target_id));
}

function productionPriceRulesTouching(data, rpos) {
  const ids = new Set(data.choices.filter((choice) => rpos.has(choice.rpo)).map((choice) => choice.option_id));
  return data.priceRules.filter((rule) => ids.has(rule.condition_option_id) || ids.has(rule.target_option_id));
}

function productionRuleGroupsTouching(data, rpos) {
  const ids = new Set(data.choices.filter((choice) => rpos.has(choice.rpo)).map((choice) => choice.option_id));
  return data.ruleGroups.filter((group) => ids.has(group.source_id) || (group.target_ids || []).some((optionId) => ids.has(optionId)));
}

function pefPackageRecords(data) {
  const pef = optionIdByRpo(data, "PEF");
  const cav = optionIdByRpo(data, "CAV");
  const ria = optionIdByRpo(data, "RIA");
  return {
    rules: data.rules
      .filter((rule) => rule.source_id === pef && rule.rule_type === "includes" && [cav, ria].includes(rule.target_id))
      .map((rule) => rule.target_id)
      .sort(),
    priceRules: data.priceRules
      .filter((rule) => rule.condition_option_id === pef && [cav, ria].includes(rule.target_option_id) && Number(rule.price_value) === 0)
      .map((rule) => rule.target_option_id)
      .sort(),
  };
}

test("CSV evaluator prices direct suede trunk liner selections and reports exclusivity", () => {
  const result = evaluate("1lt_c07", ["opt_sxb_001", "opt_sxt_001"]);

  assert.equal(lineById(result, "opt_sxb_001")?.final_price_usd, 2095);
  assert.equal(lineById(result, "opt_sxt_001")?.final_price_usd, 2695);
  assert.equal(result.conflicts.length, 1);
  assert.equal(result.conflicts[0].exclusive_group_id, "excl_suede_trunk_liner");
  assert.deepEqual(result.conflicts[0].member_selectable_ids, ["opt_sxb_001", "opt_sxt_001"]);
});

test("CSV suede trunk liner legacy fragment matches generated choices and exclusive group", () => {
  const production = loadGeneratedData();
  const projected = emitCsvLegacyFragment();
  const productionOptionIds = suedeTrunkLinerOptionIds(production);

  assert.deepEqual(projected.validation_errors, []);
  assert.deepEqual([...suedeTrunkLinerOptionIds(projected)].sort(), [...productionOptionIds].sort());
  assert.deepEqual(normalizeChoices(projected.choices), normalizeChoices(production.choices));
  assert.deepEqual(normalizeExclusiveGroups(projected.exclusiveGroups, productionOptionIds), normalizeExclusiveGroups(production.exclusiveGroups, productionOptionIds));
});

test("production has no hidden rules priceRules or ruleGroups touching suede trunk liners", () => {
  const production = loadGeneratedData();

  assert.deepEqual(plain(productionRulesTouching(production, SUEDE_TRUNK_LINER_RPOS)), []);
  assert.deepEqual(plain(productionPriceRulesTouching(production, SUEDE_TRUNK_LINER_RPOS)), []);
  assert.deepEqual(plain(productionRuleGroupsTouching(production, SUEDE_TRUNK_LINER_RPOS)), []);
});

test("shadow overlay preserves nearby PEF CAV RIA package-liner production records", () => {
  const production = loadGeneratedData();
  const shadow = loadShadowData();

  assert.deepEqual(plain(pefPackageRecords(shadow)), plain(pefPackageRecords(production)));
  assert.deepEqual(plain(pefPackageRecords(shadow)), {
    rules: [optionIdByRpo(production, "CAV"), optionIdByRpo(production, "RIA")],
    priceRules: [optionIdByRpo(production, "CAV"), optionIdByRpo(production, "RIA")],
  });
});

test("shadow suede trunk liner runtime exclusivity matches production", () => {
  const production = loadGeneratedData();
  const shadow = loadShadowData();
  const productionRuntime = runtimeFor(production, "1lt_c07");
  const shadowRuntime = runtimeFor(shadow, "1lt_c07");

  for (const rpo of ["SXB", "SXR", "SXT"]) {
    handleRpo(productionRuntime, rpo);
    handleRpo(shadowRuntime, rpo);
  }

  assert.deepEqual(selectedSuedeTrunkLinerRpos(shadowRuntime), ["SXT"]);
  assert.deepEqual(selectedSuedeTrunkLinerRpos(shadowRuntime), selectedSuedeTrunkLinerRpos(productionRuntime));
});
