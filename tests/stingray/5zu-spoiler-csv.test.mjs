import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import fs from "node:fs";
import test from "node:test";

import { createRuntime, loadGeneratedData, loadShadowData } from "./runtime-harness.mjs";

const PYTHON = ".venv/bin/python";
const SCRIPT = "scripts/stingray_csv_first_slice.py";
const OWNERSHIP_MANIFEST = "data/stingray/validation/projected_slice_ownership.csv";
const FIVE_ZU_RPOS = new Set(["5ZU"]);
const NON_5ZU_RPOS = new Set(["Z51", "ZYC", "GBA", "G8G", "GKZ", "5ZW", "5VM", "5W8"]);

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

function fiveZuOptionIds(data) {
  return new Set(data.choices.filter((choice) => FIVE_ZU_RPOS.has(choice.rpo)).map((choice) => choice.option_id));
}

function normalizeChoices(rows) {
  return Array.from(rows)
    .filter((choice) => FIVE_ZU_RPOS.has(choice.rpo))
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

test("CSV evaluator prices direct 5ZU selection", () => {
  const result = evaluate("1lt_c07", ["opt_5zu_001"]);
  const line = result.selected_lines.find((item) => item.selectable_id === "opt_5zu_001");

  assert.equal(line?.rpo, "5ZU");
  assert.equal(line?.label, "LPO, High wing spoiler, Body color");
  assert.equal(line?.final_price_usd, 1395);
  assert.deepEqual(result.validation_errors, []);
});

test("CSV 5ZU legacy fragment matches generated 5ZU choices and projected spoiler group without ruleGroups", () => {
  const production = loadGeneratedData();
  const projected = emitCsvLegacyFragment();
  const projectedGroup = projected.exclusiveGroups.find((group) => group.group_id === "grp_spoiler_high_wing");
  const productionGroup = production.exclusiveGroups.find((group) => group.group_id === "grp_spoiler_high_wing");

  assert.deepEqual(projected.validation_errors, []);
  assert.deepEqual([...fiveZuOptionIds(projected)].sort(), ["opt_5zu_001"]);
  assert.deepEqual(normalizeChoices(projected.choices), normalizeChoices(production.choices));
  assert.deepEqual(plain(projectedGroup), plain(productionGroup));
  assert.deepEqual(projected.ruleGroups.map((group) => group.group_id), ["grp_5v7_spoiler_requirement"]);
  for (const rpo of NON_5ZU_RPOS) {
    assert.equal(projected.choices.some((choice) => choice.rpo === rpo || choice.option_id === `opt_${rpo.toLowerCase()}_001`), false);
  }
});

test("ownership manifest projects 5ZU and keeps only unmigrated 5ZU-touching production boundaries preserved", () => {
  const production = loadGeneratedData();
  const byRpo = optionIdsByRpo(production);
  const fiveZU = byRpo.get("5ZU");
  const t0a = byRpo.get("T0A");
  const productionRules = production.rules
    .filter((rule) => rule.source_id === fiveZU || rule.target_id === fiveZU)
    .map((rule) => [rule.source_id, rule.target_id, rule.rule_type, rule.auto_add, rule.runtime_action])
    .sort();
  const productionPriceRules = production.priceRules
    .filter((rule) => rule.condition_option_id === fiveZU || rule.target_option_id === fiveZU)
    .map((rule) => [rule.condition_option_id, rule.target_option_id, rule.price_rule_type, Number(rule.price_value || 0)])
    .sort();

  assert.deepEqual(plain(productionRules), plain([
    [byRpo.get("WKQ"), fiveZU, "excludes", "False", "active"],
    [byRpo.get("RNX"), fiveZU, "excludes", "False", "active"],
    ["opt_5vm_001", fiveZU, "requires", "False", "active"],
    ["opt_5w8_001", fiveZU, "requires", "False", "active"],
    [fiveZU, t0a, "excludes", "False", "replace"],
  ].sort()));
  assert.deepEqual(plain(productionPriceRules), []);
  assert.deepEqual(plain(groupIdsTouchingOption(production.exclusiveGroups, fiveZU)), ["grp_spoiler_high_wing"]);
  assert.deepEqual(plain(ruleGroupIdsTouchingOption(production.ruleGroups, fiveZU)), [
    "grp_5v7_spoiler_requirement",
    "grp_5zu_paint_requirement",
  ]);

  assert.equal(manifestHas({ record_type: "selectable", rpo: "5ZU", ownership: "projected_owned" }), true);
  assert.equal(manifestHas({ record_type: "exclusiveGroup", group_id: "grp_spoiler_high_wing", ownership: "projected_owned" }), true);
  assert.equal(manifestHas({ record_type: "ruleGroup", group_id: "grp_5v7_spoiler_requirement", ownership: "projected_owned" }), true);
  assert.equal(manifestHas({ record_type: "ruleGroup", group_id: "grp_5zu_paint_requirement", ownership: "production_guarded" }), true);
  assert.equal(manifestHas({ record_type: "rule", source_rpo: "5ZU", target_rpo: "T0A", ownership: "preserved_cross_boundary" }), true);
  assert.equal(manifestHas({ record_type: "rule", source_rpo: "WKQ", target_rpo: "5ZU", ownership: "preserved_cross_boundary" }), false);
  assert.equal(manifestHas({ record_type: "rule", source_rpo: "RNX", target_rpo: "5ZU", ownership: "preserved_cross_boundary" }), false);
  assert.equal(manifestHas({ record_type: "rule", source_option_id: "opt_5vm_001", target_rpo: "5ZU", ownership: "preserved_cross_boundary" }), true);
  assert.equal(manifestHas({ record_type: "rule", source_option_id: "opt_5w8_001", target_rpo: "5ZU", ownership: "preserved_cross_boundary" }), true);
  assert.equal(manifestHas({ record_type: "ruleGroup", source_rpo: "5V7", target_rpo: "5ZU", ownership: "preserved_cross_boundary" }), false);
  for (const paintRpo of ["G8G", "GBA", "GKZ"]) {
    assert.equal(manifestHas({ record_type: "ruleGroup", source_rpo: "5ZU", target_rpo: paintRpo, ownership: "preserved_cross_boundary" }), true);
    assert.equal(manifestHas({ record_type: "selectable", rpo: paintRpo, ownership: "projected_owned" }), false);
  }

  for (const rpo of NON_5ZU_RPOS) {
    assert.equal(manifestHas({ record_type: "selectable", rpo, ownership: "projected_owned" }), false);
  }
  assert.equal(manifestHas({ record_type: "guardedOption", rpo: "5ZU", ownership: "production_guarded" }), false);
});

test("shadow overlay preserves 5ZU production-owned rules and groups", () => {
  const production = loadGeneratedData();
  const shadow = loadShadowData();
  const fiveZU = optionIdByRpo(production, "5ZU");

  assert.deepEqual(plain(normalizeRules(shadow.rules, fiveZU)), plain(normalizeRules(production.rules, fiveZU)));
  assert.deepEqual(plain(groupIdsTouchingOption(shadow.exclusiveGroups, fiveZU)), ["grp_spoiler_high_wing"]);
  assert.deepEqual(plain(ruleGroupIdsTouchingOption(shadow.ruleGroups, fiveZU)), [
    "grp_5v7_spoiler_requirement",
    "grp_5zu_paint_requirement",
  ]);
  assert.deepEqual(
    plain(shadow.exclusiveGroups.find((group) => group.group_id === "grp_spoiler_high_wing")),
    plain(production.exclusiveGroups.find((group) => group.group_id === "grp_spoiler_high_wing"))
  );
  for (const groupId of ["grp_5v7_spoiler_requirement", "grp_5zu_paint_requirement"]) {
    assert.deepEqual(
      plain(shadow.ruleGroups.find((group) => group.group_id === groupId)),
      plain(production.ruleGroups.find((group) => group.group_id === groupId))
    );
  }
});

test("shadow 5ZU runtime paint requirement replacement cleanup and 5V7 behavior match production", () => {
  for (const data of [loadGeneratedData(), loadShadowData()]) {
    const directRuntime = runtimeFor(data, "1lt_c07");
    assert.match(directRuntime.disableReasonForChoice(activeChoiceByRpo(directRuntime, "5ZU")), /Requires Arctic White|Requires Black|Requires Torch Red/);

    for (const paintRpo of ["G8G", "GBA", "GKZ"]) {
      const paintRuntime = runtimeFor(data, "1lt_c07");
      handleRpo(paintRuntime, paintRpo);
      assert.equal(paintRuntime.disableReasonForChoice(activeChoiceByRpo(paintRuntime, "5ZU")), "");
      handleRpo(paintRuntime, "5ZU");
      assert.equal(paintRuntime.optionPrice(activeChoiceByRpo(paintRuntime, "5ZU").option_id), 1395);
      assert.deepEqual(selectedRpos(paintRuntime, new Set([paintRpo, "5ZU"])), ["5ZU", paintRpo].sort());
    }

    const zycRuntime = runtimeFor(data, "1lt_c07");
    handleRpo(zycRuntime, "ZYC");
    handleRpo(zycRuntime, "GBA");
    assert.deepEqual(selectedRpos(zycRuntime, new Set(["GBA", "ZYC"])), ["GBA"]);

    const z51Runtime = runtimeFor(data, "1lt_c07");
    handleRpo(z51Runtime, "GBA");
    handleRpo(z51Runtime, "Z51");
    assert.deepEqual(autoAddedRpos(z51Runtime, new Set(["T0A"])), ["T0A"]);
    handleRpo(z51Runtime, "5ZU");
    assert.deepEqual(selectedRpos(z51Runtime, new Set(["T0A", "TVS", "5ZZ", "5ZU", "Z51"])), ["5ZU", "Z51"]);
    assert.deepEqual(autoAddedRpos(z51Runtime, new Set(["T0A"])), []);

    const fiveV7Runtime = runtimeFor(data, "1lt_c07");
    assert.match(fiveV7Runtime.disableReasonForChoice(activeChoiceByRpo(fiveV7Runtime, "5V7")), /Requires 5ZU|Requires 5ZZ/);
    handleRpo(fiveV7Runtime, "GBA");
    handleRpo(fiveV7Runtime, "5ZU");
    assert.equal(fiveV7Runtime.disableReasonForChoice(activeChoiceByRpo(fiveV7Runtime, "5V7")), "");
    handleRpo(fiveV7Runtime, "5V7");
    assert.deepEqual(selectedRpos(fiveV7Runtime, new Set(["5V7", "5ZU"])), ["5V7", "5ZU"]);
  }
});
