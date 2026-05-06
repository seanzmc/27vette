import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import fs from "node:fs";
import test from "node:test";

import { createRuntime, loadGeneratedData, loadShadowData } from "./runtime-harness.mjs";

const PYTHON = ".venv/bin/python";
const SCRIPT = "scripts/stingray_csv_first_slice.py";
const OWNERSHIP_MANIFEST = "data/stingray/validation/projected_slice_ownership.csv";
const TVS_RPOS = new Set(["TVS"]);
const NON_TVS_SPOILER_RPOS = new Set(["Z51", "ZYC", "5ZW"]);

function parseCsv(source) {
  const rows = [];
  let row = [];
  let field = "";
  let inQuotes = false;
  for (let index = 0; index < source.length; index++) {
    const char = source[index];
    const next = source[index + 1];
    if (char === '"' && inQuotes && next === '"') {
      field += '"';
      index++;
    } else if (char === '"') {
      inQuotes = !inQuotes;
    } else if (char === "," && !inQuotes) {
      row.push(field);
      field = "";
    } else if ((char === "\n" || char === "\r") && !inQuotes) {
      if (char === "\r" && next === "\n") index++;
      row.push(field);
      if (row.some((value) => value !== "")) rows.push(row);
      row = [];
      field = "";
    } else {
      field += char;
    }
  }
  if (field || row.length) {
    row.push(field);
    rows.push(row);
  }
  const [headers, ...records] = rows;
  return records.map((record) => Object.fromEntries(headers.map((header, index) => [header, record[index] || ""])));
}

function activeManifestRows() {
  return parseCsv(fs.readFileSync(OWNERSHIP_MANIFEST, "utf8")).filter((row) => row.active === "true");
}

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

function plain(value) {
  return JSON.parse(JSON.stringify(value));
}

function optionIdByRpo(data, rpo) {
  const choice = data.choices.find((item) => item.rpo === rpo && item.active === "True");
  assert.ok(choice, `${rpo} should exist in production data`);
  return choice.option_id;
}

function tvsOptionIds(data) {
  return new Set(data.choices.filter((choice) => TVS_RPOS.has(choice.rpo)).map((choice) => choice.option_id));
}

function normalizeChoices(rows) {
  return Array.from(rows)
    .filter((choice) => TVS_RPOS.has(choice.rpo))
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

function normalizeRules(rows, optionId) {
  return rows
    .filter((rule) => rule.source_id === optionId || rule.target_id === optionId)
    .map((rule) => ({
      source_id: rule.source_id,
      target_id: rule.target_id,
      rule_type: rule.rule_type,
      auto_add: rule.auto_add,
      runtime_action: rule.runtime_action,
      disabled_reason: rule.disabled_reason,
      body_style_scope: rule.body_style_scope || "",
      trim_level_scope: rule.trim_level_scope || "",
      variant_scope: rule.variant_scope || "",
      active: rule.active,
    }))
    .sort((a, b) => `${a.source_id}:${a.rule_type}:${a.target_id}`.localeCompare(`${b.source_id}:${b.rule_type}:${b.target_id}`));
}

function normalizePriceRules(rows, optionId) {
  return rows
    .filter((rule) => rule.condition_option_id === optionId || rule.target_option_id === optionId)
    .map((rule) => ({
      condition_option_id: rule.condition_option_id,
      target_option_id: rule.target_option_id,
      price_rule_type: rule.price_rule_type,
      price_value: Number(rule.price_value || 0),
      body_style_scope: rule.body_style_scope || "",
      trim_level_scope: rule.trim_level_scope || "",
      variant_scope: rule.variant_scope || "",
      review_flag: rule.review_flag,
      notes: rule.notes,
    }))
    .sort((a, b) => `${a.condition_option_id}:${a.target_option_id}:${a.price_value}`.localeCompare(`${b.condition_option_id}:${b.target_option_id}:${b.price_value}`));
}

function optionIdsByRpo(data) {
  const byRpo = new Map();
  for (const choice of data.choices) {
    if (!choice.rpo) continue;
    byRpo.set(choice.rpo, choice.option_id);
  }
  return byRpo;
}

function runtimeFor(data, variantId) {
  const runtime = createRuntime(data);
  const variant = data.variants.find((item) => item.variant_id === variantId);
  assert.ok(variant, `${variantId} should exist`);
  runtime.state.bodyStyle = variant.body_style;
  runtime.state.trimLevel = variant.trim_level;
  runtime.resetDefaults();
  runtime.reconcileSelections();
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

function selectedRpos(runtime, rpos) {
  return [...runtime.state.selected]
    .map((optionId) => runtime.activeChoiceRows().find((choice) => choice.option_id === optionId)?.rpo)
    .filter((rpo) => rpos.has(rpo))
    .sort();
}

function manifestHas(expected) {
  return activeManifestRows().some((row) => Object.entries(expected).every(([key, value]) => row[key] === value));
}

test("CSV evaluator prices direct TVS selection", () => {
  const result = evaluate("1lt_c07", ["opt_tvs_001"]);
  const line = result.selected_lines.find((item) => item.selectable_id === "opt_tvs_001");

  assert.equal(line?.final_price_usd, 995);
  assert.deepEqual(result.conflicts, []);
});

test("CSV TVS legacy fragment matches generated TVS choices and projected spoiler ruleGroups", () => {
  const production = loadGeneratedData();
  const projected = emitCsvLegacyFragment();
  const projectedGroup = projected.exclusiveGroups.find((group) => group.group_id === "grp_spoiler_high_wing");
  const productionGroup = production.exclusiveGroups.find((group) => group.group_id === "grp_spoiler_high_wing");

  assert.deepEqual(projected.validation_errors, []);
  assert.deepEqual([...tvsOptionIds(projected)].sort(), ["opt_tvs_001"]);
  assert.deepEqual(normalizeChoices(projected.choices), normalizeChoices(production.choices));
  assert.deepEqual(plain(projectedGroup), plain(productionGroup));
	  assert.deepEqual(projected.ruleGroups.map((group) => group.group_id), [
	    "grp_5v7_spoiler_requirement",
	    "grp_5zu_paint_requirement",
	  ]);
  for (const rpo of NON_TVS_SPOILER_RPOS) {
    assert.equal(projected.choices.some((choice) => choice.rpo === rpo || choice.option_id === `opt_${rpo.toLowerCase()}_001`), false);
  }
});

test("ownership manifest projects TVS and preserves every TVS-touching production boundary", () => {
  const production = loadGeneratedData();
  const byRpo = optionIdsByRpo(production);
  const tvsId = byRpo.get("TVS");
  const productionRules = production.rules
    .filter((rule) => rule.source_id === tvsId || rule.target_id === tvsId)
    .map((rule) => [rule.source_id, rule.target_id, rule.rule_type, rule.runtime_action])
    .sort();
  const productionPriceRules = production.priceRules
    .filter((rule) => rule.condition_option_id === tvsId || rule.target_option_id === tvsId)
    .map((rule) => [rule.condition_option_id, rule.target_option_id, rule.price_rule_type, Number(rule.price_value || 0)])
    .sort();
  const productionGroups = production.exclusiveGroups
    .filter((group) => group.option_ids.includes(tvsId))
    .map((group) => group.group_id)
    .sort();
  const productionRuleGroups = production.ruleGroups
    .filter((group) => group.source_id === tvsId || group.target_ids.includes(tvsId))
    .map((group) => group.group_id)
    .sort();

  assert.deepEqual(plain(productionRules), plain([
    [byRpo.get("5V7"), tvsId, "excludes", "active"],
    ["opt_5vm_001", tvsId, "excludes", "active"],
    ["opt_5w8_001", tvsId, "excludes", "active"],
    [tvsId, byRpo.get("T0A"), "excludes", "replace"],
  ].sort()));
  assert.deepEqual(plain(productionPriceRules), plain([[byRpo.get("Z51"), tvsId, "override", 0]]));
  assert.deepEqual(plain(productionGroups), ["grp_spoiler_high_wing"]);
  assert.deepEqual(plain(productionRuleGroups), []);

  assert.equal(manifestHas({ record_type: "selectable", rpo: "TVS", ownership: "projected_owned" }), true);
  assert.equal(manifestHas({ record_type: "exclusiveGroup", group_id: "grp_spoiler_high_wing", ownership: "projected_owned" }), true);
  assert.equal(manifestHas({ record_type: "rule", source_rpo: "TVS", target_rpo: "T0A", ownership: "preserved_cross_boundary" }), true);
  assert.equal(manifestHas({ record_type: "priceRule", source_rpo: "Z51", target_rpo: "TVS", ownership: "preserved_cross_boundary" }), true);
  assert.equal(manifestHas({ record_type: "rule", source_rpo: "5V7", target_rpo: "TVS", ownership: "preserved_cross_boundary" }), false);
  assert.equal(manifestHas({ record_type: "rule", source_option_id: "opt_5vm_001", target_rpo: "TVS", ownership: "preserved_cross_boundary" }), true);
  assert.equal(manifestHas({ record_type: "rule", source_option_id: "opt_5w8_001", target_rpo: "TVS", ownership: "preserved_cross_boundary" }), true);

  for (const rpo of NON_TVS_SPOILER_RPOS) {
    assert.equal(manifestHas({ record_type: "selectable", rpo, ownership: "projected_owned" }), false);
  }
});

test("shadow overlay preserves TVS production-owned rules priceRules and spoiler group", () => {
  const production = loadGeneratedData();
  const shadow = loadShadowData();
  const tvsId = optionIdByRpo(production, "TVS");
  const productionGroup = production.exclusiveGroups.find((group) => group.group_id === "grp_spoiler_high_wing");
  const shadowGroup = shadow.exclusiveGroups.find((group) => group.group_id === "grp_spoiler_high_wing");

  assert.deepEqual(plain(shadowGroup), plain(productionGroup));
  assert.deepEqual(plain(normalizeRules(shadow.rules, tvsId)), plain(normalizeRules(production.rules, tvsId)));
  assert.deepEqual(plain(normalizePriceRules(shadow.priceRules, tvsId)), plain(normalizePriceRules(production.priceRules, tvsId)));
});

test("shadow TVS runtime pricing replacement conflicts and exclusivity match production", () => {
  for (const data of [loadGeneratedData(), loadShadowData()]) {
    const directRuntime = runtimeFor(data, "1lt_c07");
    const tvs = activeChoiceByRpo(directRuntime, "TVS");
    handleRpo(directRuntime, "TVS");
    assert.equal(directRuntime.optionPrice(tvs.option_id), 995);

    const z51Runtime = runtimeFor(data, "1lt_c07");
    const t0a = activeChoiceByRpo(z51Runtime, "T0A");
    handleRpo(z51Runtime, "Z51");
    assert.equal(z51Runtime.computeAutoAdded().has(t0a.option_id), true);
    handleRpo(z51Runtime, "TVS");
    assert.equal(z51Runtime.optionPrice(activeChoiceByRpo(z51Runtime, "TVS").option_id), 0);
    assert.equal(z51Runtime.computeAutoAdded().has(t0a.option_id), false);
    assert.deepEqual(selectedRpos(z51Runtime, new Set(["T0A", "TVS"])), ["TVS"]);

    const fiveV7Runtime = runtimeFor(data, "1lt_c07");
    handleRpo(fiveV7Runtime, "5ZZ");
    handleRpo(fiveV7Runtime, "5V7");
    assert.match(fiveV7Runtime.disableReasonForChoice(activeChoiceByRpo(fiveV7Runtime, "TVS")), /Blocked by 5V7/);

    const exclusiveRuntime = runtimeFor(data, "1lt_c07");
    handleRpo(exclusiveRuntime, "5ZZ");
    handleRpo(exclusiveRuntime, "TVS");
    assert.deepEqual(selectedRpos(exclusiveRuntime, new Set(["T0A", "TVS", "5ZZ", "5ZU"])), ["TVS"]);
  }
});
