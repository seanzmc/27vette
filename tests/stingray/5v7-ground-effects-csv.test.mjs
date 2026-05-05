import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import fs from "node:fs";
import test from "node:test";

import { createRuntime, loadGeneratedData, loadShadowData } from "./runtime-harness.mjs";

const PYTHON = ".venv/bin/python";
const SCRIPT = "scripts/stingray_csv_first_slice.py";
const OWNERSHIP_MANIFEST = "data/stingray/validation/projected_slice_ownership.csv";
const FIVE_V7_RPOS = new Set(["5V7"]);
const EXTERNAL_RPOS = new Set(["Z51", "5VM", "5W8", "5ZW"]);

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

function fiveV7OptionIds(data) {
  return new Set(data.choices.filter((choice) => FIVE_V7_RPOS.has(choice.rpo)).map((choice) => choice.option_id));
}

function normalizeChoices(rows) {
  return Array.from(rows)
    .filter((choice) => FIVE_V7_RPOS.has(choice.rpo))
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

function manifestHas(expected) {
  return activeManifestRows().some((row) => Object.entries(expected).every(([key, value]) => row[key] === value));
}

function groupIdsTouchingOption(groups, optionId) {
  return groups
    .filter((group) => group.option_ids.includes(optionId))
    .map((group) => group.group_id)
    .sort();
}

function ruleGroupIdsTouchingOption(groups, optionId) {
  return groups
    .filter((group) => group.source_id === optionId || group.target_ids.includes(optionId))
    .map((group) => group.group_id)
    .sort();
}

test("CSV evaluator prices direct 5V7 selection", () => {
  const result = evaluate("1lt_c07", ["opt_5zz_001", "opt_5v7_001"]);
  const line = result.selected_lines.find((item) => item.selectable_id === "opt_5v7_001");

  assert.equal(line?.rpo, "5V7");
  assert.equal(line?.label, "LPO, Black Ground Effects");
  assert.equal(line?.final_price_usd, 650);
  assert.deepEqual(result.validation_errors, []);
});

test("CSV 5V7 legacy fragment matches generated 5V7 choices and projected generated ruleGroup", () => {
  const production = loadGeneratedData();
  const projected = emitCsvLegacyFragment();
  const projectedGroup = projected.ruleGroups.find((group) => group.group_id === "grp_5v7_spoiler_requirement");
  const productionGroup = production.ruleGroups.find((group) => group.group_id === "grp_5v7_spoiler_requirement");
  const targetRpos = projectedGroup.target_ids.map((optionId) => production.choices.find((choice) => choice.option_id === optionId)?.rpo || optionId);

  assert.deepEqual(projected.validation_errors, []);
  assert.deepEqual([...fiveV7OptionIds(projected)].sort(), ["opt_5v7_001"]);
  assert.deepEqual(normalizeChoices(projected.choices), normalizeChoices(production.choices));
  assert.deepEqual(plain(projectedGroup), plain(productionGroup));
  assert.deepEqual(targetRpos, ["5ZU", "5ZZ"]);
  assert.equal(projectedGroup.target_ids.includes("opt_5zw_001"), false);
  for (const rpo of EXTERNAL_RPOS) {
    assert.equal(projected.choices.some((choice) => choice.rpo === rpo || choice.option_id === `opt_${rpo.toLowerCase()}_001`), false);
  }
});

test("ownership manifest projects 5V7 and keeps only unmigrated 5V7-touching production boundaries preserved", () => {
  const production = loadGeneratedData();
  const byRpo = optionIdsByRpo(production);
  const fiveV7 = byRpo.get("5V7");
  const productionRules = production.rules
    .filter((rule) => rule.source_id === fiveV7 || rule.target_id === fiveV7)
    .map((rule) => [rule.source_id, rule.target_id, rule.rule_type, rule.auto_add, rule.runtime_action])
    .sort();
  const productionPriceRules = production.priceRules
    .filter((rule) => rule.condition_option_id === fiveV7 || rule.target_option_id === fiveV7)
    .map((rule) => [rule.condition_option_id, rule.target_option_id, rule.price_rule_type, Number(rule.price_value || 0)])
    .sort();

  assert.deepEqual(plain(productionRules), plain([
    [fiveV7, "opt_5vm_001", "excludes", "False", "active"],
    [fiveV7, "opt_5w8_001", "excludes", "False", "active"],
    [fiveV7, byRpo.get("STI"), "excludes", "False", "active"],
    [fiveV7, byRpo.get("TVS"), "excludes", "False", "active"],
    [fiveV7, byRpo.get("Z51"), "excludes", "False", "active"],
    ["opt_5vm_001", fiveV7, "excludes", "False", "active"],
    ["opt_5w8_001", fiveV7, "excludes", "False", "active"],
    [byRpo.get("PCU"), fiveV7, "excludes", "False", "active"],
    [byRpo.get("STI"), fiveV7, "excludes", "False", "active"],
  ].sort()));
  assert.deepEqual(plain(productionPriceRules), []);
  assert.deepEqual(plain(groupIdsTouchingOption(production.exclusiveGroups, fiveV7)), []);
  assert.deepEqual(plain(ruleGroupIdsTouchingOption(production.ruleGroups, fiveV7)), ["grp_5v7_spoiler_requirement"]);

  assert.equal(manifestHas({ record_type: "selectable", rpo: "5V7", ownership: "projected_owned" }), true);
  assert.equal(manifestHas({ record_type: "ruleGroup", group_id: "grp_5v7_spoiler_requirement", ownership: "projected_owned" }), true);
  assert.equal(manifestHas({ record_type: "rule", source_rpo: "5V7", target_rpo: "TVS", ownership: "preserved_cross_boundary" }), false);
  assert.equal(manifestHas({ record_type: "rule", source_rpo: "5V7", target_rpo: "Z51", ownership: "preserved_cross_boundary" }), true);
  assert.equal(manifestHas({ record_type: "rule", source_rpo: "5V7", target_rpo: "STI", ownership: "preserved_cross_boundary" }), false);
  assert.equal(manifestHas({ record_type: "rule", source_rpo: "5V7", target_option_id: "opt_5vm_001", ownership: "preserved_cross_boundary" }), true);
  assert.equal(manifestHas({ record_type: "rule", source_rpo: "5V7", target_option_id: "opt_5w8_001", ownership: "preserved_cross_boundary" }), true);
  assert.equal(manifestHas({ record_type: "rule", source_option_id: "opt_5vm_001", target_rpo: "5V7", ownership: "preserved_cross_boundary" }), true);
  assert.equal(manifestHas({ record_type: "rule", source_option_id: "opt_5w8_001", target_rpo: "5V7", ownership: "preserved_cross_boundary" }), true);
  assert.equal(manifestHas({ record_type: "rule", source_rpo: "PCU", target_rpo: "5V7", ownership: "preserved_cross_boundary" }), false);
  assert.equal(manifestHas({ record_type: "rule", source_rpo: "STI", target_rpo: "5V7", ownership: "preserved_cross_boundary" }), false);
  assert.equal(manifestHas({ record_type: "ruleGroup", source_rpo: "5V7", target_rpo: "5ZU", ownership: "preserved_cross_boundary" }), false);
  assert.equal(manifestHas({ record_type: "ruleGroup", source_rpo: "5V7", target_rpo: "5ZZ", ownership: "preserved_cross_boundary" }), false);

  for (const rpo of EXTERNAL_RPOS) {
    assert.equal(manifestHas({ record_type: "selectable", rpo, ownership: "projected_owned" }), false);
  }
  assert.equal(manifestHas({ record_type: "guardedOption", rpo: "5V7", ownership: "production_guarded" }), false);
});

test("shadow overlay preserves 5V7 production-owned rules and projects the generated ruleGroup", () => {
  const production = loadGeneratedData();
  const shadow = loadShadowData();
  const fiveV7 = optionIdByRpo(production, "5V7");

  assert.deepEqual(plain(normalizeRules(shadow.rules, fiveV7)), plain(normalizeRules(production.rules, fiveV7)));
  assert.deepEqual(plain(groupIdsTouchingOption(shadow.exclusiveGroups, fiveV7)), []);
  assert.deepEqual(plain(ruleGroupIdsTouchingOption(shadow.ruleGroups, fiveV7)), ["grp_5v7_spoiler_requirement"]);
  assert.deepEqual(
    plain(shadow.ruleGroups.find((group) => group.group_id === "grp_5v7_spoiler_requirement")),
    plain(production.ruleGroups.find((group) => group.group_id === "grp_5v7_spoiler_requirement"))
  );
});

test("shadow 5V7 runtime requirements and external conflicts match production", () => {
  for (const data of [loadGeneratedData(), loadShadowData()]) {
    const directRuntime = runtimeFor(data, "1lt_c07");
    assert.match(directRuntime.disableReasonForChoice(activeChoiceByRpo(directRuntime, "5V7")), /Requires 5ZU|Requires 5ZZ/);

    const fiveZzRuntime = runtimeFor(data, "1lt_c07");
    handleRpo(fiveZzRuntime, "5ZZ");
    assert.equal(fiveZzRuntime.disableReasonForChoice(activeChoiceByRpo(fiveZzRuntime, "5V7")), "");
    handleRpo(fiveZzRuntime, "5V7");
    assert.deepEqual(selectedRpos(fiveZzRuntime, new Set(["5V7", "5ZZ"])), ["5V7", "5ZZ"]);

    const fiveZuRuntime = runtimeFor(data, "1lt_c07");
    handleRpo(fiveZuRuntime, "GBA");
    handleRpo(fiveZuRuntime, "5ZU");
    assert.equal(fiveZuRuntime.disableReasonForChoice(activeChoiceByRpo(fiveZuRuntime, "5V7")), "");
    handleRpo(fiveZuRuntime, "5V7");
    assert.deepEqual(selectedRpos(fiveZuRuntime, new Set(["5V7", "5ZU"])), ["5V7", "5ZU"]);

    const tvsRuntime = runtimeFor(data, "1lt_c07");
    handleRpo(tvsRuntime, "5ZZ");
    handleRpo(tvsRuntime, "5V7");
    assert.match(tvsRuntime.disableReasonForChoice(activeChoiceByRpo(tvsRuntime, "TVS")), /Blocked by 5V7/);

    const z51Runtime = runtimeFor(data, "1lt_c07");
    handleRpo(z51Runtime, "5ZZ");
    handleRpo(z51Runtime, "5V7");
    assert.match(z51Runtime.disableReasonForChoice(activeChoiceByRpo(z51Runtime, "Z51")), /Blocked by 5V7/);

    const pcuRuntime = runtimeFor(data, "1lt_c07");
    handleRpo(pcuRuntime, "5ZZ");
    handleRpo(pcuRuntime, "PCU");
    assert.match(pcuRuntime.disableReasonForChoice(activeChoiceByRpo(pcuRuntime, "5V7")), /Blocked by PCU/);

    const stiRuntime = runtimeFor(data, "1lt_c07");
    handleRpo(stiRuntime, "5ZZ");
    handleRpo(stiRuntime, "STI");
    assert.match(stiRuntime.disableReasonForChoice(activeChoiceByRpo(stiRuntime, "5V7")), /Blocked by STI/);
  }
});
