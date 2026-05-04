import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import fs from "node:fs";
import test from "node:test";

import { createRuntime, loadGeneratedData, loadShadowData } from "./runtime-harness.mjs";

const PYTHON = ".venv/bin/python";
const FRAGMENT_SCRIPT = "scripts/stingray_csv_first_slice.py";
const OWNERSHIP_MANIFEST = "data/stingray/validation/projected_slice_ownership.csv";

const ENGINE_PACKAGE_RPOS = new Set(["B6P", "D3V", "SL9", "ZZ3", "BC4", "BCP", "BCS", "BC7"]);
const OUT_OF_SCOPE_PACKAGE_RPOS = new Set(["PDV", "PCU", "PCX", "Z51"]);
const INCLUDED_EDGES = [
  ["B6P", "D3V"],
  ["B6P", "SL9"],
  ["BC4", "D3V"],
  ["BCP", "D3V"],
  ["BCS", "D3V"],
  ["ZZ3", "BC7"],
  ["ZZ3", "SL9"],
];
const INCLUDED_ZERO_EDGES = [
  ["B6P", "D3V"],
  ["B6P", "SL9"],
  ["BC4", "D3V"],
  ["BCP", "D3V"],
  ["BCS", "D3V"],
  ["ZZ3", "SL9"],
];
const COLORED_COVER_RPOS = ["BC4", "BCP", "BCS"];

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

function projectedRpos() {
  return new Set(
    activeManifestRows()
      .filter((row) => row.record_type === "selectable" && row.ownership === "projected_owned")
      .map((row) => row.rpo)
  );
}

function emitLegacyFragment() {
  return JSON.parse(
    execFileSync(PYTHON, [FRAGMENT_SCRIPT, "--emit-legacy-fragment"], {
      cwd: process.cwd(),
      encoding: "utf8",
      maxBuffer: 8 * 1024 * 1024,
    })
  );
}

function evaluate(variantId, selectedIds) {
  return JSON.parse(
    execFileSync(PYTHON, [FRAGMENT_SCRIPT, "--scenario-json", JSON.stringify({ variant_id: variantId, selected_ids: selectedIds })], {
      cwd: process.cwd(),
      encoding: "utf8",
      maxBuffer: 8 * 1024 * 1024,
    })
  );
}

function optionIdByRpo(data, rpo) {
  const ids = new Set(data.choices.filter((choice) => choice.rpo === rpo).map((choice) => choice.option_id));
  assert.equal(ids.size, 1, `${rpo} should map to exactly one option_id`);
  return [...ids][0];
}

function rpoByOptionId(data) {
  return new Map(data.choices.map((choice) => [choice.option_id, choice.rpo]));
}

function lineById(result, selectableId) {
  return result.selected_lines.find((line) => line.selectable_id === selectableId);
}

function runtimeFor(data, variantId) {
  const runtime = createRuntime(data);
  const variant = data.variants.find((item) => item.variant_id === variantId);
  assert.ok(variant, `${variantId} should exist`);
  runtime.state.bodyStyle = variant.body_style;
  runtime.state.trimLevel = variant.trim_level;
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

function engineFacts(data, variantId, actions) {
  const runtime = runtimeFor(data, variantId);
  for (const rpo of actions) handleRpo(runtime, rpo);
  const byId = rpoByOptionId(data);
  const autoAdded = runtime.computeAutoAdded();
  return {
    selected: [...runtime.state.selected].map((id) => byId.get(id)).filter((rpo) => ENGINE_PACKAGE_RPOS.has(rpo)).sort(),
    userSelected: [...runtime.state.userSelected].map((id) => byId.get(id)).filter((rpo) => ENGINE_PACKAGE_RPOS.has(rpo)).sort(),
    autoAdded: [...autoAdded.keys()].map((id) => byId.get(id)).filter((rpo) => ENGINE_PACKAGE_RPOS.has(rpo)).sort(),
    lines: runtime
      .lineItems()
      .filter((line) => ENGINE_PACKAGE_RPOS.has(line.rpo))
      .map((line) => ({ rpo: line.rpo, type: line.type, price: line.price }))
      .sort((a, b) => `${a.type}:${a.rpo}`.localeCompare(`${b.type}:${b.rpo}`)),
  };
}

function plain(value) {
  return JSON.parse(JSON.stringify(value));
}

test("Engine Appearance package include cluster satisfies projected-owned source and target policy", () => {
  const owned = projectedRpos();

  for (const [sourceRpo, targetRpo] of INCLUDED_EDGES) {
    assert.equal(owned.has(sourceRpo), true, `${sourceRpo} package source should be projected-owned`);
    assert.equal(owned.has(targetRpo), true, `${targetRpo} package target should be projected-owned`);
  }
  for (const rpo of OUT_OF_SCOPE_PACKAGE_RPOS) {
    assert.equal(owned.has(rpo), false, `${rpo} should remain outside the Engine Appearance package formalization`);
  }
});

test("Engine Appearance legacy fragment emits stable include rules and included-zero priceRules", () => {
  const production = loadGeneratedData();
  const fragment = emitLegacyFragment();

  assert.deepEqual(fragment.validation_errors, []);
  for (const [sourceRpo, targetRpo] of INCLUDED_EDGES) {
    const sourceId = optionIdByRpo(production, sourceRpo);
    const targetId = optionIdByRpo(production, targetRpo);
    const rule = fragment.rules.find((item) => item.source_id === sourceId && item.target_id === targetId);
    assert.ok(rule, `${sourceRpo} -> ${targetRpo} include rule should be projected`);
    assert.equal(rule.rule_type, "includes");
    assert.equal(rule.auto_add, "True");
  }

  for (const [sourceRpo, targetRpo] of INCLUDED_ZERO_EDGES) {
    const sourceId = optionIdByRpo(production, sourceRpo);
    const targetId = optionIdByRpo(production, targetRpo);
    const priceRule = fragment.priceRules.find(
      (item) => item.condition_option_id === sourceId && item.target_option_id === targetId && Number(item.price_value) === 0
    );
    assert.ok(priceRule, `${sourceRpo} -> ${targetRpo} included-zero priceRule should be projected`);
    assert.equal(priceRule.price_rule_type, "override");
  }

  const zz3 = optionIdByRpo(production, "ZZ3");
  const bc7 = optionIdByRpo(production, "BC7");
  assert.equal(
    fragment.priceRules.some((item) => item.condition_option_id === zz3 && item.target_option_id === bc7 && Number(item.price_value) === 0),
    false,
    "ZZ3 -> BC7 should not force an included-zero priceRule because BC7 direct base price is already zero"
  );
});

test("Engine Appearance package price overrides keep B6P and ZZ3 scoped colored-cover pricing", () => {
  const production = loadGeneratedData();
  const fragment = emitLegacyFragment();

  for (const targetRpo of COLORED_COVER_RPOS) {
    const targetId = optionIdByRpo(production, targetRpo);
    const b6pRule = fragment.priceRules.find(
      (item) => item.condition_option_id === optionIdByRpo(production, "B6P") && item.target_option_id === targetId
    );
    const zz3Rule = fragment.priceRules.find(
      (item) => item.condition_option_id === optionIdByRpo(production, "ZZ3") && item.target_option_id === targetId
    );

    assert.equal(Number(b6pRule?.price_value), 595, `${targetRpo} should be 595 with B6P`);
    assert.equal(b6pRule?.body_style_scope, "coupe");
    assert.equal(Number(zz3Rule?.price_value), 595, `${targetRpo} should be 595 with ZZ3`);
    assert.equal(zz3Rule?.body_style_scope, "convertible");
  }
});

test("CSV evaluator preserves direct member package included and convergence pricing", () => {
  const directD3v = evaluate("1lt_c07", ["opt_d3v_001"]);
  assert.equal(lineById(directD3v, "opt_d3v_001")?.final_price_usd, 195);

  const directSl9 = evaluate("1lt_c07", ["opt_sl9_001"]);
  assert.equal(lineById(directSl9, "opt_sl9_001")?.final_price_usd, 125);

  const b6p = evaluate("1lt_c07", ["opt_b6p_001"]);
  assert.equal(lineById(b6p, "opt_d3v_001")?.final_price_usd, 0);
  assert.equal(lineById(b6p, "opt_sl9_001")?.final_price_usd, 0);

  const memberFirst = evaluate("1lt_c07", ["opt_d3v_001", "opt_b6p_001"]);
  assert.deepEqual(lineById(memberFirst, "opt_d3v_001")?.provenance, ["explicit"]);
  assert.deepEqual(lineById(memberFirst, "opt_d3v_001")?.matched_auto_add_ids, ["aa_b6p_d3v"]);
  assert.equal(lineById(memberFirst, "opt_d3v_001")?.final_price_usd, 0);

  const convergedD3v = evaluate("1lt_c07", ["opt_b6p_001", "opt_bcp_001"]);
  assert.equal(convergedD3v.selected_lines.filter((line) => line.selectable_id === "opt_d3v_001").length, 1);
  assert.equal(lineById(convergedD3v, "opt_d3v_001")?.final_price_usd, 0);
});

test("shadow runtime preserves Engine Appearance package source member and deselect parity", () => {
  const production = loadGeneratedData();
  const shadow = loadShadowData();

  for (const [name, variantId, actions] of [
    ["direct member alone", "1lt_c07", ["D3V"]],
    ["package source alone", "1lt_c07", ["B6P"]],
    ["member first then package", "1lt_c07", ["D3V", "B6P"]],
    ["multiple includes converge on D3V", "1lt_c07", ["BCP", "B6P"]],
    ["convertible package source alone", "1lt_c67", ["ZZ3"]],
    ["package deselect restores explicit member price", "1lt_c07", ["D3V", "B6P", "B6P"]],
  ]) {
    assert.deepEqual(plain(engineFacts(shadow, variantId, actions)), plain(engineFacts(production, variantId, actions)), name);
  }

  const restored = engineFacts(shadow, "1lt_c07", ["D3V", "B6P", "B6P"]);
  assert.deepEqual(plain(restored.lines), [{ rpo: "D3V", type: "selected", price: 195 }]);
});
