import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import fs from "node:fs";
import test from "node:test";

import { createRuntime, loadGeneratedData, loadShadowData } from "./runtime-harness.mjs";

const PYTHON = ".venv/bin/python";
const SCRIPT = "scripts/stingray_csv_first_slice.py";
const OWNERSHIP_MANIFEST = "data/stingray/validation/projected_slice_ownership.csv";
const LPO_INTERIOR_STANDALONE_RPOS = new Set(["RWU", "S2L", "VYW", "W2D"]);
const NEARBY_UNOWNED_LPO_INTERIOR_RPOS = new Set(["PEF", "PDY", "RYT", "S08", "SBT", "SC7"]);
const EXPECTED_PRICES = new Map([
  ["RWU", 175],
  ["S2L", 1695],
  ["VYW", 275],
  ["W2D", 125],
]);

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

function normalizeChoices(rows) {
  return Array.from(rows)
    .filter((choice) => LPO_INTERIOR_STANDALONE_RPOS.has(choice.rpo))
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

function manifestHas(expected) {
  return activeManifestRows().some((row) => Object.entries(expected).every(([key, value]) => row[key] === value));
}

function projectedOwnedRpos() {
  return new Set(activeManifestRows().filter((row) => row.record_type === "selectable" && row.ownership === "projected_owned").map((row) => row.rpo));
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

function suedeTrunkLinerGroup(data) {
  return data.exclusiveGroups.find((group) => group.group_id === "excl_suede_trunk_liner");
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

function choiceByRpo(runtime, rpo) {
  const choice = runtime.activeChoiceRows().find((item) => item.rpo === rpo && item.active === "True" && item.selectable === "True");
  assert.ok(choice, `${rpo} should have a current-variant choice`);
  return choice;
}

function availableChoiceByRpo(runtime, rpo) {
  const choice = choiceByRpo(runtime, rpo);
  assert.notEqual(choice.status, "unavailable", `${rpo} should be available`);
  return choice;
}

function handleRpo(runtime, rpo) {
  runtime.handleChoice(availableChoiceByRpo(runtime, rpo));
}

function selectedRpos(runtime, rpos) {
  return [...runtime.state.selected]
    .map((optionId) => runtime.activeChoiceRows().find((choice) => choice.option_id === optionId)?.rpo)
    .filter((rpo) => rpos.has(rpo))
    .sort();
}

test("CSV evaluator prices direct standalone LPO Interior selections", () => {
  for (const [rpo, price] of EXPECTED_PRICES.entries()) {
    const result = evaluate("1lt_c07", [optionIdByRpo(loadGeneratedData(), rpo)]);
    const line = result.selected_lines.find((item) => item.rpo === rpo);

    assert.equal(line?.final_price_usd, price);
    assert.deepEqual(result.validation_errors, []);
  }

  const result = evaluate("1lt_c07", ["opt_rwu_001", "opt_s2l_001", "opt_vyw_001", "opt_w2d_001"]);
  const selectedPrices = Object.fromEntries(result.selected_lines.filter((item) => LPO_INTERIOR_STANDALONE_RPOS.has(item.rpo)).map((item) => [item.rpo, item.final_price_usd]));

  assert.deepEqual(selectedPrices, { RWU: 175, S2L: 1695, VYW: 275, W2D: 125 });
  assert.deepEqual(result.validation_errors, []);
});

test("CSV standalone LPO Interior legacy fragment matches generated choices including W2D trim scope", () => {
  const production = loadGeneratedData();
  const projected = emitCsvLegacyFragment();

  assert.deepEqual(projected.validation_errors, []);
  assert.deepEqual(normalizeChoices(projected.choices), normalizeChoices(production.choices));

  const w2dByVariant = Object.fromEntries(projected.choices.filter((choice) => choice.rpo === "W2D").map((choice) => [choice.variant_id, choice.status]));
  assert.deepEqual(w2dByVariant, {
    "1lt_c07": "available",
    "1lt_c67": "available",
    "2lt_c07": "unavailable",
    "2lt_c67": "unavailable",
    "3lt_c07": "unavailable",
    "3lt_c67": "unavailable",
  });
});

test("ownership manifest keeps broader LPO Interior package rows outside the standalone accessory slice", () => {
  const production = loadGeneratedData();
  const shadow = loadShadowData();
  const owned = projectedOwnedRpos();

  for (const rpo of LPO_INTERIOR_STANDALONE_RPOS) {
    const optionId = optionIdByRpo(production, rpo);

    assert.deepEqual(plain(production.rules.filter((rule) => rule.source_id === optionId || rule.target_id === optionId)), []);
    assert.deepEqual(plain(production.priceRules.filter((rule) => rule.condition_option_id === optionId || rule.target_option_id === optionId)), []);
    assert.deepEqual(plain(groupIdsTouchingOption(production.exclusiveGroups, optionId)), []);
    assert.deepEqual(plain(ruleGroupIdsTouchingOption(production.ruleGroups, optionId)), []);
    assert.equal(manifestHas({ record_type: "selectable", rpo, ownership: "projected_owned" }), true);
  }

  for (const rpo of NEARBY_UNOWNED_LPO_INTERIOR_RPOS) {
    assert.equal(owned.has(rpo), false, `${rpo} should remain outside the RWU/S2L/VYW/W2D standalone slice`);
  }

  assert.deepEqual(plain(suedeTrunkLinerGroup(shadow)), plain(suedeTrunkLinerGroup(production)));
});

test("shadow runtime allows standalone LPO Interior selections on 1LT and keeps W2D unavailable on higher trims", () => {
  for (const data of [loadGeneratedData(), loadShadowData()]) {
    for (const rpo of LPO_INTERIOR_STANDALONE_RPOS) {
      const runtime = runtimeFor(data, "1lt_c07");
      assert.equal(runtime.disableReasonForChoice(availableChoiceByRpo(runtime, rpo)), "");
      handleRpo(runtime, rpo);
      assert.deepEqual(selectedRpos(runtime, LPO_INTERIOR_STANDALONE_RPOS), [rpo]);
      assert.equal(runtime.optionPrice(availableChoiceByRpo(runtime, rpo).option_id), EXPECTED_PRICES.get(rpo));
    }

    const runtime = runtimeFor(data, "1lt_c07");
    for (const rpo of LPO_INTERIOR_STANDALONE_RPOS) handleRpo(runtime, rpo);
    assert.deepEqual(selectedRpos(runtime, LPO_INTERIOR_STANDALONE_RPOS), ["RWU", "S2L", "VYW", "W2D"]);

    for (const variantId of ["2lt_c07", "2lt_c67", "3lt_c07", "3lt_c67"]) {
      const higherTrimRuntime = runtimeFor(data, variantId);
      const w2d = choiceByRpo(higherTrimRuntime, "W2D");
      assert.equal(w2d.status, "unavailable");
      assert.equal(higherTrimRuntime.disableReasonForChoice(w2d), "Not available for this body and trim.");
    }
  }
});
