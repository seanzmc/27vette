import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import fs from "node:fs";
import test from "node:test";

import { createRuntime, loadGeneratedData, loadShadowData } from "./runtime-harness.mjs";

const PYTHON = ".venv/bin/python";
const SCRIPT = "scripts/stingray_csv_first_slice.py";
const OWNERSHIP_MANIFEST = "data/stingray/validation/projected_slice_ownership.csv";
const SBT_PACKAGE_RPOS = new Set(["SBT", "SC7"]);
const INCLUDED_EDGES = [["SBT", "SC7"]];
const ROOF_MODEL_RPOS = new Set(["CF7", "CM9", "C2Z", "D84", "D86"]);

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

function choiceByRpo(runtime, rpo) {
  const choice = runtime.activeChoiceRows().find((item) => item.rpo === rpo && item.active === "True");
  assert.ok(choice, `${rpo} should have an active choice row`);
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
    .filter((choice) => SBT_PACKAGE_RPOS.has(choice.rpo))
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

function preservedSbtSc7Rows() {
  return activeManifestRows()
    .filter(
      (row) =>
        row.ownership === "preserved_cross_boundary" &&
        row.source_rpo === "SBT" &&
        row.target_rpo === "SC7" &&
        ["rule", "priceRule"].includes(row.record_type)
    )
    .map((row) => `${row.record_type}:${row.source_rpo}->${row.target_rpo}`)
    .sort();
}

function preservedSbtCc3Rows() {
  return activeManifestRows()
    .filter((row) => row.ownership === "preserved_cross_boundary" && row.source_rpo === "SBT" && row.target_rpo === "CC3" && row.record_type === "rule")
    .map((row) => `${row.record_type}:${row.source_rpo}->${row.target_rpo}`)
    .sort();
}

function lineByRpo(runtime, rpo) {
  return runtime.lineItems().find((line) => line.rpo === rpo);
}

test("CSV evaluator prices direct SBT Dual roof package selection", () => {
  const production = loadGeneratedData();
  const result = evaluate("1lt_c07", [optionIdByRpo(production, "SBT")]);

  assert.deepEqual(result.validation_errors, []);
  assert.equal(result.selected_lines.find((line) => line.rpo === "SBT")?.final_price_usd, 2525);
  assert.equal(result.selected_lines.find((line) => line.rpo === "SC7")?.final_price_usd, 0);
});

test("CSV SBT legacy fragment matches generated choices and coupe-only availability", () => {
  const production = loadGeneratedData();
  const projected = emitCsvLegacyFragment();
  const choices = normalizeChoices(projected.choices);

  assert.deepEqual(projected.validation_errors, []);
  assert.deepEqual(choices, normalizeChoices(production.choices));
  assert.equal(choices.length, 12);
  assert.deepEqual(
    choices.map((choice) => [choice.rpo, choice.variant_id, choice.status, choice.status_label, choice.selectable, choice.active, choice.base_price]),
    [
      ["SBT", "1lt_c07", "available", "Available", "True", "True", 2525],
      ["SC7", "1lt_c07", "available", "Available", "True", "True", 195],
      ["SBT", "1lt_c67", "unavailable", "Not Available", "True", "True", 2525],
      ["SC7", "1lt_c67", "unavailable", "Not Available", "True", "True", 195],
      ["SBT", "2lt_c07", "available", "Available", "True", "True", 2525],
      ["SC7", "2lt_c07", "available", "Available", "True", "True", 195],
      ["SBT", "2lt_c67", "unavailable", "Not Available", "True", "True", 2525],
      ["SC7", "2lt_c67", "unavailable", "Not Available", "True", "True", 195],
      ["SBT", "3lt_c07", "available", "Available", "True", "True", 2525],
      ["SC7", "3lt_c07", "available", "Available", "True", "True", 195],
      ["SBT", "3lt_c67", "unavailable", "Not Available", "True", "True", 2525],
      ["SC7", "3lt_c67", "unavailable", "Not Available", "True", "True", 195],
    ]
  );
});

test("SBT package cluster satisfies projected-owned package policy without claiming Roof", () => {
  const owned = projectedOwnedRpos();

  for (const rpo of SBT_PACKAGE_RPOS) {
    assert.equal(owned.has(rpo), true, `${rpo} should be projected-owned`);
  }
  for (const rpo of ROOF_MODEL_RPOS) {
    assert.equal(owned.has(rpo), false, `${rpo} should remain outside the SBT package slice`);
  }
  assert.deepEqual(preservedSbtSc7Rows(), [], "SBT -> SC7 package records should not be preserved cross-boundary rows");
  assert.deepEqual(preservedSbtCc3Rows(), ["rule:SBT->CC3"], "SBT -> CC3 roof exclude should remain preserved");
});

test("CSV SBT legacy fragment emits package include rule and included-zero priceRule", () => {
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

test("production has only classified records touching SBT and SC7", () => {
  const production = loadGeneratedData();

  assert.deepEqual(plain(ruleKeysTouching(production, SBT_PACKAGE_RPOS)), ["SBT->CC3:excludes:False", "SBT->SC7:includes:True"]);
  assert.deepEqual(plain(priceRuleKeysTouching(production, SBT_PACKAGE_RPOS)), ["SBT->SC7:override:0"]);
  assert.deepEqual(plain(groupIdsTouching(production, SBT_PACKAGE_RPOS)), {
    exclusiveGroups: [],
    ruleGroups: [],
  });
});

test("shadow overlay projects SBT package records and preserves SBT to CC3", () => {
  const production = loadGeneratedData();
  const shadow = loadShadowData();
  const fragment = emitCsvLegacyFragment();
  const sbtId = optionIdByRpo(production, "SBT");
  const sc7Id = optionIdByRpo(production, "SC7");
  const cc3Id = optionIdByRpo(production, "CC3");

  assert.deepEqual(plain(packageRuleKeys(shadow, "SBT", ["SC7"])), plain(packageRuleKeys(production, "SBT", ["SC7"])));
  assert.deepEqual(plain(packagePriceRuleKeys(shadow, "SBT", ["SC7"])), plain(packagePriceRuleKeys(production, "SBT", ["SC7"])));
  assert.deepEqual(plain(preservedSbtSc7Rows()), []);

  const productionRoofRule = production.rules.find((rule) => rule.source_id === sbtId && rule.target_id === cc3Id && rule.rule_type === "excludes");
  const shadowRoofRule = shadow.rules.find((rule) => rule.source_id === sbtId && rule.target_id === cc3Id && rule.rule_type === "excludes");
  assert.deepEqual(plain(shadowRoofRule), plain(productionRoofRule));
  assert.equal(fragment.rules.some((rule) => rule.source_id === sbtId && rule.target_id === cc3Id), false);
  assert.equal(fragment.rules.some((rule) => rule.source_id === sbtId && rule.target_id === sc7Id), true);
});

test("shadow SBT runtime package and Roof boundary behavior matches production", () => {
  for (const data of [loadGeneratedData(), loadShadowData()]) {
    const directRuntime = runtimeFor(data, "1lt_c07");
    const directSc7 = activeChoiceByRpo(directRuntime, "SC7");
    directRuntime.handleChoice(directSc7);
    assert.equal(lineByRpo(directRuntime, "SC7")?.price, 195);

    const packageRuntime = runtimeFor(data, "1lt_c07");
    const sbt = activeChoiceByRpo(packageRuntime, "SBT");
    const sc7 = activeChoiceByRpo(packageRuntime, "SC7");
    const cc3 = activeChoiceByRpo(packageRuntime, "CC3");
    packageRuntime.handleChoice(sbt);
    assert.equal(lineByRpo(packageRuntime, "SBT")?.price, 2525);
    assert.equal(packageRuntime.computeAutoAdded().has(sc7.option_id), true);
    assert.equal(packageRuntime.optionPrice(sc7.option_id), 0);
    assert.equal(packageRuntime.disableReasonForChoice(cc3), "Blocked by SBT LPO, Dual roof.");
    packageRuntime.handleChoice(cc3);
    assert.equal(packageRuntime.state.selected.has(cc3.option_id), false);

    const memberFirstRuntime = runtimeFor(data, "1lt_c07");
    const memberFirstSc7 = activeChoiceByRpo(memberFirstRuntime, "SC7");
    const memberFirstSbt = activeChoiceByRpo(memberFirstRuntime, "SBT");
    memberFirstRuntime.handleChoice(memberFirstSc7);
    memberFirstRuntime.handleChoice(memberFirstSbt);
    assert.equal(memberFirstRuntime.lineItems().filter((line) => line.rpo === "SC7").length, 1);
    assert.equal(memberFirstRuntime.computeAutoAdded().has(memberFirstSc7.option_id), false);
    assert.equal(memberFirstRuntime.optionPrice(memberFirstSc7.option_id), 0);
    memberFirstRuntime.handleChoice(memberFirstSbt);
    assert.equal(memberFirstRuntime.state.selected.has(memberFirstSbt.option_id), false);
    assert.equal(memberFirstRuntime.optionPrice(memberFirstSc7.option_id), 195);

    const cc3FirstRuntime = runtimeFor(data, "1lt_c07");
    const cc3First = activeChoiceByRpo(cc3FirstRuntime, "CC3");
    const blockedSbt = activeChoiceByRpo(cc3FirstRuntime, "SBT");
    cc3FirstRuntime.handleChoice(cc3First);
    assert.equal(cc3FirstRuntime.disableReasonForChoice(blockedSbt), "Conflicts with CC3 Roof panel.");
    cc3FirstRuntime.handleChoice(blockedSbt);
    assert.equal(cc3FirstRuntime.state.selected.has(blockedSbt.option_id), false);

    const convertibleRuntime = runtimeFor(data, "1lt_c67");
    assert.equal(convertibleRuntime.disableReasonForChoice(choiceByRpo(convertibleRuntime, "SBT")), "Not available for this body and trim.");
    assert.equal(convertibleRuntime.disableReasonForChoice(choiceByRpo(convertibleRuntime, "SC7")), "Not available for this body and trim.");
  }
});
