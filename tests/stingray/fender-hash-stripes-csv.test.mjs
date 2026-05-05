import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import fs from "node:fs";
import test from "node:test";

import { createRuntime, loadGeneratedData, loadShadowData } from "./runtime-harness.mjs";

const PYTHON = ".venv/bin/python";
const SCRIPT = "scripts/stingray_csv_first_slice.py";
const OWNERSHIP_MANIFEST = "data/stingray/validation/projected_slice_ownership.csv";
const FENDER_HASH_STRIPE_RPOS = new Set(["SHQ", "SHW"]);
const NEARBY_PACKAGE_RPOS = new Set(["PDV", "PCX"]);
const EXPECTED_PRICES = new Map([
  ["SHQ", 295],
  ["SHW", 295],
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
  const ids = new Set(data.choices.filter((item) => item.rpo === rpo && item.active === "True").map((item) => item.option_id));
  assert.equal(ids.size, 1, `${rpo} should map to exactly one legacy option_id`);
  return [...ids][0];
}

function normalizeChoices(rows) {
  return Array.from(rows)
    .filter((choice) => FENDER_HASH_STRIPE_RPOS.has(choice.rpo))
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

test("CSV evaluator prices direct fender hash stripe selections", () => {
  for (const [rpo, price] of EXPECTED_PRICES.entries()) {
    const result = evaluate("1lt_c07", [optionIdByRpo(loadGeneratedData(), rpo)]);
    const line = result.selected_lines.find((item) => item.rpo === rpo);

    assert.equal(line?.final_price_usd, price);
    assert.deepEqual(result.validation_errors, []);
  }
});

test("CSV fender hash stripe legacy fragment matches generated choices", () => {
  const production = loadGeneratedData();
  const projected = emitCsvLegacyFragment();

  assert.deepEqual(projected.validation_errors, []);
  assert.deepEqual(normalizeChoices(projected.choices), normalizeChoices(production.choices));
});

test("ownership manifest projects SHQ and SHW without claiming nearby package sources", () => {
  const production = loadGeneratedData();
  const owned = projectedOwnedRpos();

  for (const rpo of FENDER_HASH_STRIPE_RPOS) {
    const optionId = optionIdByRpo(production, rpo);

    assert.deepEqual(plain(production.rules.filter((rule) => rule.source_id === optionId || rule.target_id === optionId)), []);
    assert.deepEqual(plain(production.priceRules.filter((rule) => rule.condition_option_id === optionId || rule.target_option_id === optionId)), []);
    assert.deepEqual(plain(groupIdsTouchingOption(production.exclusiveGroups, optionId)), []);
    assert.deepEqual(plain(ruleGroupIdsTouchingOption(production.ruleGroups, optionId)), []);
    assert.equal(manifestHas({ record_type: "selectable", rpo, ownership: "projected_owned" }), true);
  }

  for (const rpo of NEARBY_PACKAGE_RPOS) {
    assert.equal(owned.has(rpo), false, `${rpo} should remain outside the SHQ/SHW fender hash stripe slice`);
  }
});

test("shadow runtime preserves single-select stripe behavior with projected and production-owned stripes", () => {
  for (const data of [loadGeneratedData(), loadShadowData()]) {
    for (const [rpo, price] of EXPECTED_PRICES.entries()) {
      const runtime = runtimeFor(data, "1lt_c07");
      assert.equal(runtime.disableReasonForChoice(activeChoiceByRpo(runtime, rpo)), "");
      handleRpo(runtime, rpo);
      assert.deepEqual(selectedRpos(runtime, new Set([...FENDER_HASH_STRIPE_RPOS, "DTH"])), [rpo]);
      assert.equal(runtime.optionPrice(activeChoiceByRpo(runtime, rpo).option_id), price);
    }

    const projectedPairRuntime = runtimeFor(data, "1lt_c07");
    handleRpo(projectedPairRuntime, "SHQ");
    handleRpo(projectedPairRuntime, "SHW");
    assert.deepEqual(selectedRpos(projectedPairRuntime, FENDER_HASH_STRIPE_RPOS), ["SHW"]);

    const productionStripeRuntime = runtimeFor(data, "1lt_c07");
    handleRpo(productionStripeRuntime, "SHQ");
    handleRpo(productionStripeRuntime, "DTH");
    assert.deepEqual(selectedRpos(productionStripeRuntime, new Set(["SHQ", "DTH"])), ["DTH"]);

    const projectedAfterProductionRuntime = runtimeFor(data, "1lt_c07");
    handleRpo(projectedAfterProductionRuntime, "DTH");
    handleRpo(projectedAfterProductionRuntime, "SHW");
    assert.deepEqual(selectedRpos(projectedAfterProductionRuntime, new Set(["SHW", "DTH"])), ["SHW"]);
  }
});
