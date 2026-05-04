import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import fs from "node:fs";
import test from "node:test";

import { createRuntime, loadGeneratedData, loadShadowData } from "./runtime-harness.mjs";

const PYTHON = ".venv/bin/python";
const SCRIPT = "scripts/stingray_csv_first_slice.py";
const OWNERSHIP_MANIFEST = "data/stingray/validation/projected_slice_ownership.csv";
const PROTECTION_MEMBER_RPOS = new Set(["VQK", "VWE"]);

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

function manifestHas(expected) {
  return activeManifestRows().some((row) => Object.entries(expected).every(([key, value]) => row[key] === value));
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

function optionIdsByRpo(data, rpo) {
  return [...new Set(data.choices.filter((choice) => choice.rpo === rpo && choice.active === "True").map((choice) => choice.option_id))].sort();
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

function normalizeChoices(rows) {
  return Array.from(rows)
    .filter((choice) => PROTECTION_MEMBER_RPOS.has(choice.rpo))
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

function pcuMemberRecords(data) {
  const pcu = optionIdByRpo(data, "PCU");
  const targets = ["VQK", "VWE"].map((rpo) => optionIdByRpo(data, rpo)).sort();
  return {
    rules: data.rules
      .filter((rule) => rule.source_id === pcu && rule.rule_type === "includes" && targets.includes(rule.target_id))
      .map((rule) => rule.target_id)
      .sort(),
    priceRules: data.priceRules
      .filter((rule) => rule.condition_option_id === pcu && targets.includes(rule.target_option_id) && Number(rule.price_value) === 0)
      .map((rule) => rule.target_option_id)
      .sort(),
  };
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

function lineByRpo(runtime, rpo) {
  return runtime.lineItems().find((line) => line.rpo === rpo);
}

test("CSV evaluator prices direct VQK and VWE protection member selections", () => {
  const production = loadGeneratedData();
  const result = evaluate("1lt_c07", [optionIdByRpo(production, "VQK"), optionIdByRpo(production, "VWE")]);

  assert.deepEqual(result.validation_errors, []);
  assert.equal(result.selected_lines.find((line) => line.rpo === "VQK")?.final_price_usd, 395);
  assert.equal(result.selected_lines.find((line) => line.rpo === "VWE")?.final_price_usd, 695);
});

test("CSV VQK and VWE legacy fragment matches generated choices and all-variant availability", () => {
  const production = loadGeneratedData();
  const projected = emitCsvLegacyFragment();
  const choices = normalizeChoices(projected.choices);

  assert.deepEqual(projected.validation_errors, []);
  assert.deepEqual(choices, normalizeChoices(production.choices));
  assert.equal(choices.length, 12);
  assert.deepEqual(
    choices.map((choice) => [choice.rpo, choice.variant_id, choice.status, choice.status_label, choice.selectable, choice.active, choice.base_price]),
    [
      ["VQK", "1lt_c07", "available", "Available", "True", "True", 395],
      ["VWE", "1lt_c07", "available", "Available", "True", "True", 695],
      ["VQK", "1lt_c67", "available", "Available", "True", "True", 395],
      ["VWE", "1lt_c67", "available", "Available", "True", "True", 695],
      ["VQK", "2lt_c07", "available", "Available", "True", "True", 395],
      ["VWE", "2lt_c07", "available", "Available", "True", "True", 695],
      ["VQK", "2lt_c67", "available", "Available", "True", "True", 395],
      ["VWE", "2lt_c67", "available", "Available", "True", "True", 695],
      ["VQK", "3lt_c07", "available", "Available", "True", "True", 395],
      ["VWE", "3lt_c07", "available", "Available", "True", "True", 695],
      ["VQK", "3lt_c67", "available", "Available", "True", "True", 395],
      ["VWE", "3lt_c67", "available", "Available", "True", "True", 695],
    ]
  );
});

test("ownership projects VQK and VWE with the PCU package source", () => {
  const owned = projectedOwnedRpos();
  const production = loadGeneratedData();

  assert.equal(owned.has("VQK"), true);
  assert.equal(owned.has("VWE"), true);
  assert.equal(owned.has("PCU"), true);
  assert.equal(optionIdsByRpo(production, "5VM").length, 0);
  assert.equal(optionIdsByRpo(production, "5W8").length, 0);

  assert.equal(manifestHas({ record_type: "selectable", rpo: "PCU", ownership: "projected_owned" }), true);
  for (const rpo of PROTECTION_MEMBER_RPOS) {
    assert.equal(manifestHas({ record_type: "selectable", rpo, ownership: "projected_owned" }), true);
  }
});

test("production has only classified PCU package records touching VQK and VWE", () => {
  const production = loadGeneratedData();

  assert.deepEqual(plain(ruleKeysTouching(production, PROTECTION_MEMBER_RPOS)), ["PCU->VQK:includes:True", "PCU->VWE:includes:True"]);
  assert.deepEqual(plain(priceRuleKeysTouching(production, PROTECTION_MEMBER_RPOS)), ["PCU->VQK:override:0", "PCU->VWE:override:0"]);
  assert.deepEqual(plain(groupIdsTouching(production, PROTECTION_MEMBER_RPOS)), {
    exclusiveGroups: [],
    ruleGroups: [],
  });
});

test("shadow overlay projects PCU package include and included-zero priceRules for VQK and VWE", () => {
  const production = loadGeneratedData();
  const shadow = loadShadowData();

  assert.deepEqual(plain(pcuMemberRecords(shadow)), plain(pcuMemberRecords(production)));
  assert.deepEqual(plain(pcuMemberRecords(shadow)), {
    rules: [optionIdByRpo(production, "VQK"), optionIdByRpo(production, "VWE")],
    priceRules: [optionIdByRpo(production, "VQK"), optionIdByRpo(production, "VWE")],
  });
});

test("shadow VQK and VWE runtime package behavior matches production", () => {
  const production = loadGeneratedData();
  const shadow = loadShadowData();

  const directRuntime = runtimeFor(shadow, "1lt_c07");
  const directVqk = activeChoiceByRpo(directRuntime, "VQK");
  const directVwe = activeChoiceByRpo(directRuntime, "VWE");
  directRuntime.handleChoice(directVqk);
  directRuntime.handleChoice(directVwe);
  assert.equal(lineByRpo(directRuntime, "VQK")?.price, 395);
  assert.equal(lineByRpo(directRuntime, "VWE")?.price, 695);

  for (const data of [production, shadow]) {
    const packageRuntime = runtimeFor(data, "1lt_c07");
    const pcu = activeChoiceByRpo(packageRuntime, "PCU");
    const vqk = activeChoiceByRpo(packageRuntime, "VQK");
    const vwe = activeChoiceByRpo(packageRuntime, "VWE");
    packageRuntime.handleChoice(pcu);
    assert.equal(packageRuntime.computeAutoAdded().has(vqk.option_id), true);
    assert.equal(packageRuntime.computeAutoAdded().has(vwe.option_id), true);
    assert.equal(packageRuntime.optionPrice(vqk.option_id), 0);
    assert.equal(packageRuntime.optionPrice(vwe.option_id), 0);

    const memberFirstRuntime = runtimeFor(data, "1lt_c07");
    const memberFirstVqk = activeChoiceByRpo(memberFirstRuntime, "VQK");
    const memberFirstVwe = activeChoiceByRpo(memberFirstRuntime, "VWE");
    const memberFirstPcu = activeChoiceByRpo(memberFirstRuntime, "PCU");
    memberFirstRuntime.handleChoice(memberFirstVqk);
    memberFirstRuntime.handleChoice(memberFirstVwe);
    memberFirstRuntime.handleChoice(memberFirstPcu);
    assert.equal(memberFirstRuntime.state.selected.has(memberFirstVqk.option_id), true);
    assert.equal(memberFirstRuntime.state.selected.has(memberFirstVwe.option_id), true);
    assert.equal(memberFirstRuntime.computeAutoAdded().has(memberFirstVqk.option_id), false);
    assert.equal(memberFirstRuntime.computeAutoAdded().has(memberFirstVwe.option_id), false);
    assert.equal(memberFirstRuntime.optionPrice(memberFirstVqk.option_id), 0);
    assert.equal(memberFirstRuntime.optionPrice(memberFirstVwe.option_id), 0);

    memberFirstRuntime.handleChoice(memberFirstPcu);
    assert.equal(memberFirstRuntime.state.selected.has(memberFirstPcu.option_id), false);
    assert.equal(memberFirstRuntime.optionPrice(memberFirstVqk.option_id), 395);
    assert.equal(memberFirstRuntime.optionPrice(memberFirstVwe.option_id), 695);
  }
});
