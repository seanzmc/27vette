import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import fs from "node:fs";
import test from "node:test";

import { createRuntime, loadGeneratedData, loadShadowData } from "./runtime-harness.mjs";

const PYTHON = ".venv/bin/python";
const SCRIPT = "scripts/stingray_csv_first_slice.py";
const OWNERSHIP_MANIFEST = "data/stingray/validation/projected_slice_ownership.csv";
const PEF_PACKAGE_RPOS = new Set(["PEF", "CAV", "RIA"]);
const INCLUDED_EDGES = [
  ["PEF", "CAV"],
  ["PEF", "RIA"],
];
const OUT_OF_SCOPE_RPOS = new Set(["PDY", "RYT", "S08", "SBT", "SC7"]);

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

function projectedOwnedRpos() {
  return new Set(activeManifestRows().filter((row) => row.record_type === "selectable" && row.ownership === "projected_owned").map((row) => row.rpo));
}

function emitCsvLegacyFragment() {
  const output = execFileSync(PYTHON, [SCRIPT, "--emit-legacy-fragment"], {
    cwd: process.cwd(),
    encoding: "utf8",
    maxBuffer: 8 * 1024 * 1024,
  });
  return JSON.parse(output);
}

function evaluate(variantId, selectedIds) {
  const output = execFileSync(PYTHON, [SCRIPT, "--scenario-json", JSON.stringify({ variant_id: variantId, selected_ids: selectedIds })], {
    cwd: process.cwd(),
    encoding: "utf8",
  });
  return JSON.parse(output);
}

function plain(value) {
  return JSON.parse(JSON.stringify(value));
}

function optionIdByRpo(data, rpo) {
  const ids = new Set(data.choices.filter((choice) => choice.rpo === rpo && choice.active === "True").map((choice) => choice.option_id));
  assert.equal(ids.size, 1, `${rpo} should map to exactly one active legacy option_id`);
  return [...ids][0];
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
  runtime.resetDefaults();
  runtime.reconcileSelections();
  return runtime;
}

function normalizeChoices(rows) {
  return Array.from(rows)
    .filter((choice) => choice.rpo === "PEF")
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

function packageRuleKeys(data, sourceRpo, targetRpos) {
  const sourceId = optionIdByRpo(data, sourceRpo);
  const targetIds = new Set(targetRpos.map((rpo) => optionIdByRpo(data, rpo)));
  return data.rules
    .filter((rule) => rule.source_id === sourceId && targetIds.has(rule.target_id))
    .map((rule) => {
      const target = data.choices.find((choice) => choice.option_id === rule.target_id)?.rpo || rule.target_id;
      return `${sourceRpo}->${target}:${rule.rule_type}:${rule.auto_add}`;
    })
    .sort();
}

function packagePriceRuleKeys(data, sourceRpo, targetRpos) {
  const sourceId = optionIdByRpo(data, sourceRpo);
  const targetIds = new Set(targetRpos.map((rpo) => optionIdByRpo(data, rpo)));
  return data.priceRules
    .filter((rule) => rule.condition_option_id === sourceId && targetIds.has(rule.target_option_id))
    .map((rule) => {
      const target = data.choices.find((choice) => choice.option_id === rule.target_option_id)?.rpo || rule.target_option_id;
      return `${sourceRpo}->${target}:${rule.price_rule_type}:${Number(rule.price_value)}`;
    })
    .sort();
}

function ruleKeysTouching(data, rpos) {
  const ids = new Set(data.choices.filter((choice) => rpos.has(choice.rpo)).map((choice) => choice.option_id));
  return data.rules
    .filter((rule) => ids.has(rule.source_id) || ids.has(rule.target_id))
    .map((rule) => {
      const source = data.choices.find((choice) => choice.option_id === rule.source_id)?.rpo || rule.source_id;
      const target = data.choices.find((choice) => choice.option_id === rule.target_id)?.rpo || rule.target_id;
      return `${source}->${target}:${rule.rule_type}:${rule.auto_add}`;
    })
    .sort();
}

function priceRuleKeysTouching(data, rpos) {
  const ids = new Set(data.choices.filter((choice) => rpos.has(choice.rpo)).map((choice) => choice.option_id));
  return data.priceRules
    .filter((rule) => ids.has(rule.condition_option_id) || ids.has(rule.target_option_id))
    .map((rule) => {
      const source = data.choices.find((choice) => choice.option_id === rule.condition_option_id)?.rpo || rule.condition_option_id;
      const target = data.choices.find((choice) => choice.option_id === rule.target_option_id)?.rpo || rule.target_option_id;
      return `${source}->${target}:${rule.price_rule_type}:${Number(rule.price_value)}`;
    })
    .sort();
}

function groupIdsTouching(data, rpos) {
  const ids = new Set(data.choices.filter((choice) => rpos.has(choice.rpo)).map((choice) => choice.option_id));
  return {
    exclusiveGroups: data.exclusiveGroups
      .filter((group) => (group.option_ids || []).some((optionId) => ids.has(optionId)))
      .map((group) => group.group_id)
      .sort(),
    ruleGroups: data.ruleGroups
      .filter((group) => ids.has(group.source_id) || (group.target_ids || []).some((optionId) => ids.has(optionId)))
      .map((group) => group.group_id)
      .sort(),
  };
}

function preservedPefRows() {
  return activeManifestRows()
    .filter(
      (row) =>
        row.ownership === "preserved_cross_boundary" &&
        row.source_rpo === "PEF" &&
        ["CAV", "RIA"].includes(row.target_rpo) &&
        ["rule", "priceRule"].includes(row.record_type)
    )
    .map((row) => `${row.record_type}:${row.source_rpo}->${row.target_rpo}`)
    .sort();
}

function lineByRpo(runtime, rpo) {
  return runtime.lineItems().find((line) => line.rpo === rpo);
}

test("CSV evaluator prices direct PEF Contoured Liner package selection", () => {
  const production = loadGeneratedData();
  const result = evaluate("1lt_c07", [optionIdByRpo(production, "PEF")]);

  assert.deepEqual(result.validation_errors, []);
  assert.equal(result.selected_lines.find((line) => line.rpo === "PEF")?.final_price_usd, 475);
  assert.equal(result.selected_lines.find((line) => line.rpo === "CAV")?.final_price_usd, 0);
  assert.equal(result.selected_lines.find((line) => line.rpo === "RIA")?.final_price_usd, 0);
});

test("CSV PEF legacy fragment matches generated choices and all-variant availability", () => {
  const production = loadGeneratedData();
  const projected = emitCsvLegacyFragment();
  const choices = normalizeChoices(projected.choices);

  assert.deepEqual(projected.validation_errors, []);
  assert.deepEqual(choices, normalizeChoices(production.choices));
  assert.equal(choices.length, 6);
  assert.deepEqual(
    choices.map((choice) => [choice.variant_id, choice.status, choice.status_label, choice.selectable, choice.active, choice.base_price]),
    [
      ["1lt_c07", "available", "Available", "True", "True", 475],
      ["1lt_c67", "available", "Available", "True", "True", 475],
      ["2lt_c07", "available", "Available", "True", "True", 475],
      ["2lt_c67", "available", "Available", "True", "True", 475],
      ["3lt_c07", "available", "Available", "True", "True", 475],
      ["3lt_c67", "available", "Available", "True", "True", 475],
    ]
  );
});

test("PEF package cluster satisfies projected-owned source and target policy", () => {
  const owned = projectedOwnedRpos();

  for (const rpo of PEF_PACKAGE_RPOS) {
    assert.equal(owned.has(rpo), true, `${rpo} should be projected-owned`);
  }
  for (const rpo of OUT_OF_SCOPE_RPOS) {
    assert.equal(owned.has(rpo), false, `${rpo} should remain outside the PEF package slice`);
  }
  assert.deepEqual(preservedPefRows(), [], "PEF package records should no longer be preserved cross-boundary rows");
});

test("CSV PEF legacy fragment emits package include rules and included-zero priceRules", () => {
  const production = loadGeneratedData();
  const projected = emitCsvLegacyFragment();

  assert.deepEqual(projected.validation_errors, []);
  for (const [sourceRpo, targetRpo] of INCLUDED_EDGES) {
    const sourceId = optionIdByRpo(production, sourceRpo);
    const targetId = optionIdByRpo(production, targetRpo);
    const rule = projected.rules.find((item) => item.source_id === sourceId && item.target_id === targetId);
    const priceRule = projected.priceRules.find(
      (item) => item.condition_option_id === sourceId && item.target_option_id === targetId && Number(item.price_value) === 0
    );

    assert.ok(rule, `${sourceRpo} -> ${targetRpo} include rule should be projected`);
    assert.equal(rule.rule_type, "includes");
    assert.equal(rule.auto_add, "True");
    assert.ok(priceRule, `${sourceRpo} -> ${targetRpo} included-zero priceRule should be projected`);
    assert.equal(priceRule.price_rule_type, "override");
  }
});

test("production has only PEF package records touching the fully owned liner cluster", () => {
  const production = loadGeneratedData();

  assert.deepEqual(plain(ruleKeysTouching(production, PEF_PACKAGE_RPOS)), ["PEF->CAV:includes:True", "PEF->RIA:includes:True"]);
  assert.deepEqual(plain(priceRuleKeysTouching(production, PEF_PACKAGE_RPOS)), ["PEF->CAV:override:0", "PEF->RIA:override:0"]);
  assert.deepEqual(plain(groupIdsTouching(production, PEF_PACKAGE_RPOS)), {
    exclusiveGroups: [],
    ruleGroups: [],
  });
});

test("shadow overlay projects PEF package records instead of preserving them", () => {
  const production = loadGeneratedData();
  const shadow = loadShadowData();

  assert.deepEqual(plain(packageRuleKeys(shadow, "PEF", ["CAV", "RIA"])), plain(packageRuleKeys(production, "PEF", ["CAV", "RIA"])));
  assert.deepEqual(plain(packagePriceRuleKeys(shadow, "PEF", ["CAV", "RIA"])), plain(packagePriceRuleKeys(production, "PEF", ["CAV", "RIA"])));
  assert.deepEqual(plain(preservedPefRows()), []);
});

test("shadow PEF runtime package behavior matches production", () => {
  for (const data of [loadGeneratedData(), loadShadowData()]) {
    const directRuntime = runtimeFor(data, "1lt_c07");
    const directCav = activeChoiceByRpo(directRuntime, "CAV");
    const directRia = activeChoiceByRpo(directRuntime, "RIA");
    directRuntime.handleChoice(directCav);
    directRuntime.handleChoice(directRia);
    assert.equal(lineByRpo(directRuntime, "CAV")?.price, 230);
    assert.equal(lineByRpo(directRuntime, "RIA")?.price, 265);

    const packageRuntime = runtimeFor(data, "1lt_c07");
    const pef = activeChoiceByRpo(packageRuntime, "PEF");
    const cav = activeChoiceByRpo(packageRuntime, "CAV");
    const ria = activeChoiceByRpo(packageRuntime, "RIA");
    packageRuntime.handleChoice(pef);
    assert.equal(lineByRpo(packageRuntime, "PEF")?.price, 475);
    assert.equal(packageRuntime.computeAutoAdded().has(cav.option_id), true);
    assert.equal(packageRuntime.computeAutoAdded().has(ria.option_id), true);
    assert.equal(packageRuntime.optionPrice(cav.option_id), 0);
    assert.equal(packageRuntime.optionPrice(ria.option_id), 0);

    const memberFirstRuntime = runtimeFor(data, "1lt_c07");
    const memberFirstCav = activeChoiceByRpo(memberFirstRuntime, "CAV");
    const memberFirstRia = activeChoiceByRpo(memberFirstRuntime, "RIA");
    const memberFirstPef = activeChoiceByRpo(memberFirstRuntime, "PEF");
    memberFirstRuntime.handleChoice(memberFirstCav);
    memberFirstRuntime.handleChoice(memberFirstRia);
    memberFirstRuntime.handleChoice(memberFirstPef);
    assert.equal(memberFirstRuntime.lineItems().filter((line) => line.rpo === "CAV").length, 1);
    assert.equal(memberFirstRuntime.lineItems().filter((line) => line.rpo === "RIA").length, 1);
    assert.equal(memberFirstRuntime.computeAutoAdded().has(memberFirstCav.option_id), false);
    assert.equal(memberFirstRuntime.computeAutoAdded().has(memberFirstRia.option_id), false);
    assert.equal(memberFirstRuntime.optionPrice(memberFirstCav.option_id), 0);
    assert.equal(memberFirstRuntime.optionPrice(memberFirstRia.option_id), 0);

    memberFirstRuntime.handleChoice(memberFirstPef);
    assert.equal(memberFirstRuntime.state.selected.has(memberFirstPef.option_id), false);
    assert.equal(memberFirstRuntime.optionPrice(memberFirstCav.option_id), 230);
    assert.equal(memberFirstRuntime.optionPrice(memberFirstRia.option_id), 265);
  }
});
