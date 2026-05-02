import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import fs from "node:fs";
import test from "node:test";

import { createRuntime, loadGeneratedData, loadShadowData } from "./runtime-harness.mjs";

const PYTHON = ".venv/bin/python";
const SCRIPT = "scripts/stingray_csv_first_slice.py";
const OWNERSHIP_MANIFEST = "data/stingray/validation/projected_slice_ownership.csv";
const T0A_RPOS = new Set(["T0A"]);
const NON_T0A_SPOILER_RPOS = new Set(["Z51", "5V7", "ZYC", "GBA", "5ZW"]);
const Z51_INCLUDE_TARGETS = new Set(["FE3", "G0K", "G96", "J55", "M1N", "QTU", "V08"]);

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

function optionIdsByRpo(data) {
  const byRpo = new Map();
  for (const choice of data.choices) {
    if (!choice.rpo) continue;
    byRpo.set(choice.rpo, choice.option_id);
  }
  return byRpo;
}

function t0aOptionIds(data) {
  return new Set(data.choices.filter((choice) => T0A_RPOS.has(choice.rpo)).map((choice) => choice.option_id));
}

function normalizeChoices(rows) {
  return Array.from(rows)
    .filter((choice) => T0A_RPOS.has(choice.rpo))
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

function autoAddedRpos(runtime, rpos) {
  return [...runtime.computeAutoAdded().keys()]
    .map((optionId) => runtime.activeChoiceRows().find((choice) => choice.option_id === optionId)?.rpo)
    .filter((rpo) => rpos.has(rpo))
    .sort();
}

function manifestHas(expected) {
  return activeManifestRows().some((row) => Object.entries(expected).every(([key, value]) => row[key] === value));
}

test("CSV evaluator prices direct T0A selection without projecting Z51 behavior", () => {
  const result = evaluate("1lt_c07", ["opt_t0a_001"]);
  const line = result.selected_lines.find((item) => item.selectable_id === "opt_t0a_001");

  assert.equal(line?.rpo, "T0A");
  assert.equal(line?.label, "Z51 Spoiler");
  assert.equal(line?.final_price_usd, 0);
  assert.deepEqual(result.validation_errors, []);
  assert.equal(result.selected_lines.some((item) => Z51_INCLUDE_TARGETS.has(item.rpo)), false);
});

test("CSV T0A legacy fragment matches generated T0A choices without projecting spoiler group or Z51 includes", () => {
  const production = loadGeneratedData();
  const projected = emitCsvLegacyFragment();

  assert.deepEqual(projected.validation_errors, []);
  assert.deepEqual([...t0aOptionIds(projected)].sort(), ["opt_t0a_001"]);
  assert.deepEqual(normalizeChoices(projected.choices), normalizeChoices(production.choices));
  assert.equal(projected.exclusiveGroups.some((group) => group.group_id === "grp_spoiler_high_wing"), false);
  assert.equal(projected.ruleGroups.length, 0);
  for (const rpo of NON_T0A_SPOILER_RPOS) {
    assert.equal(projected.choices.some((choice) => choice.rpo === rpo || choice.option_id === `opt_${rpo.toLowerCase()}_001`), false);
  }
  for (const rpo of Z51_INCLUDE_TARGETS) {
    assert.equal(projected.choices.some((choice) => choice.rpo === rpo), false);
    assert.equal(projected.rules.some((rule) => rule.target_id === `opt_${rpo.toLowerCase()}_001`), false);
  }
});

test("ownership manifest projects T0A and preserves every T0A-touching production boundary", () => {
  const production = loadGeneratedData();
  const byRpo = optionIdsByRpo(production);
  const t0aId = byRpo.get("T0A");
  const productionRules = production.rules
    .filter((rule) => rule.source_id === t0aId || rule.target_id === t0aId)
    .map((rule) => [rule.source_id, rule.target_id, rule.rule_type, rule.auto_add, rule.runtime_action])
    .sort();
  const productionPriceRules = production.priceRules
    .filter((rule) => rule.condition_option_id === t0aId || rule.target_option_id === t0aId)
    .map((rule) => [rule.condition_option_id, rule.target_option_id, rule.price_rule_type, Number(rule.price_value || 0)])
    .sort();
  const productionGroups = production.exclusiveGroups
    .filter((group) => group.option_ids.includes(t0aId))
    .map((group) => group.group_id)
    .sort();
  const productionRuleGroups = production.ruleGroups
    .filter((group) => group.source_id === t0aId || group.target_ids.includes(t0aId))
    .map((group) => group.group_id)
    .sort();

  assert.deepEqual(plain(productionRules), plain([
    [byRpo.get("5ZU"), t0aId, "excludes", "False", "replace"],
    ["opt_5zw_001", t0aId, "excludes", "False", "active"],
    [byRpo.get("5ZZ"), t0aId, "excludes", "False", "replace"],
    [byRpo.get("Z51"), t0aId, "includes", "True", "active"],
    [t0aId, byRpo.get("Z51"), "requires", "False", "active"],
    [byRpo.get("TVS"), t0aId, "excludes", "False", "replace"],
  ].sort()));
  assert.deepEqual(plain(productionPriceRules), []);
  assert.deepEqual(plain(productionGroups), ["grp_spoiler_high_wing"]);
  assert.deepEqual(plain(productionRuleGroups), []);

  assert.equal(manifestHas({ record_type: "selectable", rpo: "T0A", ownership: "projected_owned" }), true);
  assert.equal(manifestHas({ record_type: "exclusiveGroup", group_id: "grp_spoiler_high_wing", ownership: "preserved_cross_boundary" }), true);
  assert.equal(manifestHas({ record_type: "rule", source_rpo: "Z51", target_rpo: "T0A", ownership: "preserved_cross_boundary" }), true);
  assert.equal(manifestHas({ record_type: "rule", source_rpo: "T0A", target_rpo: "Z51", ownership: "preserved_cross_boundary" }), true);
  assert.equal(manifestHas({ record_type: "rule", source_rpo: "TVS", target_rpo: "T0A", ownership: "preserved_cross_boundary" }), true);
  assert.equal(manifestHas({ record_type: "rule", source_rpo: "5ZZ", target_rpo: "T0A", ownership: "preserved_cross_boundary" }), true);
  assert.equal(manifestHas({ record_type: "rule", source_rpo: "5ZU", target_rpo: "T0A", ownership: "preserved_cross_boundary" }), true);
  assert.equal(manifestHas({ record_type: "rule", source_option_id: "opt_5zw_001", target_rpo: "T0A", ownership: "preserved_cross_boundary" }), true);

  for (const rpo of NON_T0A_SPOILER_RPOS) {
    assert.equal(manifestHas({ record_type: "selectable", rpo, ownership: "projected_owned" }), false);
  }
});

test("shadow overlay preserves T0A production-owned rules and spoiler group", () => {
  const production = loadGeneratedData();
  const shadow = loadShadowData();
  const t0aId = optionIdByRpo(production, "T0A");
  const productionGroup = production.exclusiveGroups.find((group) => group.group_id === "grp_spoiler_high_wing");
  const shadowGroup = shadow.exclusiveGroups.find((group) => group.group_id === "grp_spoiler_high_wing");

  assert.deepEqual(plain(shadowGroup), plain(productionGroup));
  assert.deepEqual(plain(normalizeRules(shadow.rules, t0aId)), plain(normalizeRules(production.rules, t0aId)));
  assert.deepEqual(plain(shadow.priceRules.filter((rule) => rule.condition_option_id === t0aId || rule.target_option_id === t0aId)), []);
});

test("shadow T0A runtime requirements auto-add replacement and exclusivity match production", () => {
  for (const data of [loadGeneratedData(), loadShadowData()]) {
    const directRuntime = runtimeFor(data, "1lt_c07");
    handleRpo(directRuntime, "T0A");
    assert.deepEqual(selectedRpos(directRuntime, new Set(["T0A", "Z51"])), []);
    assert.match(directRuntime.disableReasonForChoice(activeChoiceByRpo(directRuntime, "T0A")), /Requires Z51/);

    const z51Runtime = runtimeFor(data, "1lt_c07");
    handleRpo(z51Runtime, "Z51");
    assert.deepEqual(selectedRpos(z51Runtime, new Set(["T0A", "Z51"])), ["Z51"]);
    assert.deepEqual(autoAddedRpos(z51Runtime, new Set(["T0A"])), ["T0A"]);

    for (const replacementRpo of ["TVS", "5ZZ", "5ZU"]) {
      const replacementRuntime = runtimeFor(data, "1lt_c07");
      if (replacementRpo === "5ZU") handleRpo(replacementRuntime, "GBA");
      handleRpo(replacementRuntime, "Z51");
      handleRpo(replacementRuntime, replacementRpo);
      assert.deepEqual(selectedRpos(replacementRuntime, new Set(["T0A", "TVS", "5ZZ", "5ZU"])), [replacementRpo]);
      assert.deepEqual(autoAddedRpos(replacementRuntime, new Set(["T0A"])), []);
    }

    const exclusiveRuntime = runtimeFor(data, "1lt_c07");
    handleRpo(exclusiveRuntime, "Z51");
    handleRpo(exclusiveRuntime, "T0A");
    handleRpo(exclusiveRuntime, "TVS");
    assert.deepEqual(selectedRpos(exclusiveRuntime, new Set(["T0A", "TVS", "5ZZ", "5ZU"])), ["TVS"]);
  }
});
