import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import fs from "node:fs";
import test from "node:test";
import vm from "node:vm";

import { createRuntime, loadShadowData } from "./runtime-harness.mjs";

const PYTHON = ".venv/bin/python";
const SCRIPT = "scripts/stingray_csv_first_slice.py";
const CENTER_CAP_RPOS = new Set(["RXJ", "VWD", "5ZD", "5ZC", "RXH"]);

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
  });
  return JSON.parse(output);
}

function loadGeneratedData() {
  const context = { window: {} };
  vm.runInNewContext(fs.readFileSync("form-app/data.js", "utf8"), context);
  return context.window.STINGRAY_FORM_DATA;
}

function activeChoiceByRpo(runtime, rpo) {
  const choice = runtime
    .activeChoiceRows()
    .find((item) => item.rpo === rpo && item.active === "True" && item.status !== "unavailable" && item.selectable === "True");
  assert.ok(choice, `${rpo} should have an active selectable choice`);
  return choice;
}

function runtimeFor(data, variantId) {
  const runtime = createRuntime(data);
  const variant = data.variants.find((item) => item.variant_id === variantId);
  assert.ok(variant, `${variantId} should exist`);
  runtime.state.bodyStyle = variant.body_style;
  runtime.state.trimLevel = variant.trim_level;
  return runtime;
}

function centerCapOptionIds(data) {
  return new Set(data.choices.filter((choice) => CENTER_CAP_RPOS.has(choice.rpo)).map((choice) => choice.option_id));
}

function lineById(result, selectableId) {
  return result.selected_lines.find((line) => line.selectable_id === selectableId);
}

function plain(value) {
  return JSON.parse(JSON.stringify(value));
}

function normalizeChoices(rows) {
  return Array.from(rows)
    .filter((choice) => CENTER_CAP_RPOS.has(choice.rpo))
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

test("CSV evaluator prices direct center cap selections and reports center cap exclusivity", () => {
  const result = evaluate("1lt_c07", ["opt_rxj_001", "opt_vwd_001"]);

  assert.equal(lineById(result, "opt_rxj_001")?.final_price_usd, 275);
  assert.equal(lineById(result, "opt_vwd_001")?.final_price_usd, 250);
  assert.equal(result.conflicts.length, 1);
  assert.equal(result.conflicts[0].exclusive_group_id, "excl_center_caps");
  assert.deepEqual(result.conflicts[0].member_selectable_ids, ["opt_rxj_001", "opt_vwd_001"]);
});

test("CSV center cap legacy fragment matches generated center cap choices and exclusive group", () => {
  const production = loadGeneratedData();
  const projected = emitCsvLegacyFragment();
  const productionOptionIds = centerCapOptionIds(production);

  assert.deepEqual(projected.validation_errors, []);
  assert.deepEqual([...centerCapOptionIds(projected)].sort(), [...productionOptionIds].sort());
  assert.deepEqual(normalizeChoices(projected.choices), normalizeChoices(production.choices));
  assert.deepEqual(normalizeExclusiveGroups(projected.exclusiveGroups, productionOptionIds), normalizeExclusiveGroups(production.exclusiveGroups, productionOptionIds));
});

test("CSV-owned PDV to VWD include and pricing behavior remains production-equivalent", () => {
  const production = loadGeneratedData();
  const fragment = emitCsvLegacyFragment();
  const shadow = loadShadowData();
  const pdvId = "opt_pdv_001";
  const vwdId = "opt_vwd_001";
  const productionRule = production.rules.find((rule) => rule.source_id === pdvId && rule.rule_type === "includes" && rule.target_id === vwdId);
  const productionPriceRule = production.priceRules.find(
    (rule) => rule.condition_option_id === pdvId && rule.target_option_id === vwdId && Number(rule.price_value) === 0
  );
  const fragmentRule = fragment.rules.find((rule) => rule.source_id === pdvId && rule.rule_type === "includes" && rule.target_id === vwdId);
  const fragmentPriceRule = fragment.priceRules.find(
    (rule) => rule.condition_option_id === pdvId && rule.target_option_id === vwdId && Number(rule.price_value) === 0
  );
  const pdvVwdRule = shadow.rules.find(
    (rule) => rule.source_id === pdvId && rule.rule_type === "includes" && rule.target_id === vwdId
  );
  const pdvVwdPriceRule = shadow.priceRules.find(
    (rule) => rule.condition_option_id === pdvId && rule.target_option_id === vwdId && Number(rule.price_value) === 0
  );

  assert.deepEqual(fragment.validation_errors, []);
  assert.deepEqual(plain(fragmentRule), plain(productionRule));
  assert.deepEqual(fragmentPriceRule, {
    ...plain(productionPriceRule),
    price_rule_id: "pr_opt_pdv_001_opt_vwd_001_included_zero",
  });
  assert.deepEqual(plain(pdvVwdRule), plain(productionRule));
  assert.deepEqual(pdvVwdPriceRule, {
    ...plain(productionPriceRule),
    price_rule_id: "pr_opt_pdv_001_opt_vwd_001_included_zero",
  });

  const directRuntime = runtimeFor(shadow, "1lt_c07");
  const vwd = activeChoiceByRpo(directRuntime, "VWD");
  directRuntime.state.selected.add(vwd.option_id);
  directRuntime.state.userSelected.add(vwd.option_id);
  assert.equal(directRuntime.optionPrice(vwd.option_id), 250);

  const packageRuntime = runtimeFor(shadow, "1lt_c07");
  const pdv = activeChoiceByRpo(packageRuntime, "PDV");
  const packageVwd = activeChoiceByRpo(packageRuntime, "VWD");
  packageRuntime.state.selected.add(pdv.option_id);
  packageRuntime.state.userSelected.add(pdv.option_id);
  assert.equal(packageRuntime.computeAutoAdded().has(packageVwd.option_id), true);
  assert.equal(packageRuntime.optionPrice(packageVwd.option_id), 0);
});
