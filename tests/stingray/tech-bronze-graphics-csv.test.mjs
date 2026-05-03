import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import fs from "node:fs";
import test from "node:test";

import { createRuntime, loadGeneratedData, loadShadowData } from "./runtime-harness.mjs";

const PYTHON = ".venv/bin/python";
const SCRIPT = "scripts/stingray_csv_first_slice.py";
const OWNERSHIP_MANIFEST = "data/stingray/validation/projected_slice_ownership.csv";
const TECH_BRONZE_GRAPHICS_RPOS = new Set(["SHT", "SNG"]);
const EXPECTED_PRICES = new Map([
  ["SHT", 495],
  ["SNG", 320],
]);
const SHT_SOURCE_TEXT_STRIPE_RPOS = new Set([
  "DPB",
  "DPC",
  "DPG",
  "DPL",
  "DPT",
  "DSY",
  "DSZ",
  "DT0",
  "DTH",
  "DUB",
  "DUE",
  "DUK",
  "DUW",
  "DZU",
  "DZV",
  "DZX",
]);
const SHT_SOURCE_TEXT_MISSING_RPOS = new Set(["DTB"]);
const OUT_OF_SCOPE_RPOS = new Set([
  "PCX",
  "SFZ",
  "5DG",
  "PDV",
  "EYK",
  "R8C",
  "S47",
  "SFE",
  "SPY",
  "SPZ",
  ...SHT_SOURCE_TEXT_STRIPE_RPOS,
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
  const ids = new Set(data.choices.filter((item) => item.rpo === rpo && item.active === "True").map((item) => item.option_id));
  assert.equal(ids.size, 1, `${rpo} should map to exactly one legacy option_id`);
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

function selectedRpos(runtime, rpos) {
  return [...runtime.state.selected]
    .map((optionId) => runtime.activeChoiceRows().find((choice) => choice.option_id === optionId)?.rpo)
    .filter((rpo) => rpos.has(rpo))
    .sort();
}

function normalizeChoices(rows) {
  return Array.from(rows)
    .filter((choice) => TECH_BRONZE_GRAPHICS_RPOS.has(choice.rpo))
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

function projectedOwnedRpos() {
  return new Set(activeManifestRows().filter((row) => row.record_type === "selectable" && row.ownership === "projected_owned").map((row) => row.rpo));
}

function manifestHas(expected) {
  return activeManifestRows().some((row) => Object.entries(expected).every(([key, value]) => row[key] === value));
}

function rule(data, sourceRpo, targetRpo, ruleType) {
  const sourceId = optionIdByRpo(data, sourceRpo);
  const targetId = optionIdByRpo(data, targetRpo);
  return data.rules.find((item) => item.source_id === sourceId && item.target_id === targetId && item.rule_type === ruleType);
}

function priceRule(data, sourceRpo, targetRpo, priceValue) {
  const sourceId = optionIdByRpo(data, sourceRpo);
  const targetId = optionIdByRpo(data, targetRpo);
  return data.priceRules.find(
    (item) => item.condition_option_id === sourceId && item.target_option_id === targetId && Number(item.price_value) === priceValue
  );
}

function lineByRpo(runtime, rpo) {
  return runtime.lineItems().find((line) => line.rpo === rpo);
}

function sourceTextRpos(choice) {
  return new Set((choice.source_detail_raw.match(/\b[A-Z0-9]{2,3}\b/g) || []).filter((rpo) => !new Set(["RPO", "LPO", "PCX"]).has(rpo)));
}

test("CSV evaluator prices direct Tech Bronze graphics selections", () => {
  const production = loadGeneratedData();

  for (const [rpo, price] of EXPECTED_PRICES.entries()) {
    const result = evaluate("1lt_c07", [optionIdByRpo(production, rpo)]);
    const line = result.selected_lines.find((item) => item.rpo === rpo);

    assert.equal(line?.final_price_usd, price);
    assert.deepEqual(result.validation_errors, []);
  }
});

test("CSV Tech Bronze graphics legacy fragment matches generated choices", () => {
  const production = loadGeneratedData();
  const projected = emitCsvLegacyFragment();

  assert.deepEqual(projected.validation_errors, []);
  assert.deepEqual(normalizeChoices(projected.choices), normalizeChoices(production.choices));
});

test("SHT source-text constraints are structured records or same-section single-select peers", () => {
  const data = loadGeneratedData();
  const sht = data.choices.find((choice) => choice.rpo === "SHT" && choice.active === "True");
  assert.ok(sht);

  const expectedSourceTextRpos = new Set(["PDV", "SB7", ...SHT_SOURCE_TEXT_STRIPE_RPOS, ...SHT_SOURCE_TEXT_MISSING_RPOS]);
  assert.deepEqual(sourceTextRpos(sht), expectedSourceTextRpos);
  assert.ok(rule(data, "SHT", "PDV", "excludes"), "SHT should have a structured SHT -> PDV exclude");

  const section = data.sections.find((item) => item.section_id === sht.section_id);
  assert.equal(section?.selection_mode, "single_select_opt");

  for (const rpo of ["SB7", ...SHT_SOURCE_TEXT_STRIPE_RPOS]) {
    const peer = data.choices.find((choice) => choice.rpo === rpo && choice.active === "True");
    assert.ok(peer, `${rpo} should resolve to an active generated choice`);
    assert.equal(peer.section_id, sht.section_id, `${rpo} should remain a same-section Stripes peer of SHT`);
    assert.equal(peer.selection_mode, "single_select_opt", `${rpo} should remain covered by Stripes single-select behavior`);
  }

  for (const rpo of SHT_SOURCE_TEXT_MISSING_RPOS) {
    assert.equal(data.choices.some((choice) => choice.rpo === rpo && choice.active === "True"), false, `${rpo} should not become a fake selectable`);
  }
});

test("shadow runtime preserves Tech Bronze graphics single-select behavior with SB7 and named stripe peers", () => {
  const peerRpos = new Set(["SB7", ...SHT_SOURCE_TEXT_STRIPE_RPOS]);

  for (const data of [loadGeneratedData(), loadShadowData()]) {
    for (const techBronzeRpo of TECH_BRONZE_GRAPHICS_RPOS) {
      for (const peerRpo of peerRpos) {
        const techFirst = runtimeFor(data, "1lt_c07");
        techFirst.handleChoice(activeChoiceByRpo(techFirst, techBronzeRpo));
        techFirst.handleChoice(activeChoiceByRpo(techFirst, peerRpo));
        assert.deepEqual(selectedRpos(techFirst, new Set([techBronzeRpo, peerRpo])), [peerRpo]);

        const peerFirst = runtimeFor(data, "1lt_c07");
        peerFirst.handleChoice(activeChoiceByRpo(peerFirst, peerRpo));
        peerFirst.handleChoice(activeChoiceByRpo(peerFirst, techBronzeRpo));
        assert.deepEqual(selectedRpos(peerFirst, new Set([techBronzeRpo, peerRpo])), [techBronzeRpo]);
      }
    }
  }
});

test("shadow runtime preserves PCX package behavior for Tech Bronze graphics", () => {
  for (const data of [loadGeneratedData(), loadShadowData()]) {
    const packageRuntime = runtimeFor(data, "1lt_c07");
    packageRuntime.handleChoice(activeChoiceByRpo(packageRuntime, "PCX"));
    for (const rpo of TECH_BRONZE_GRAPHICS_RPOS) {
      assert.equal(lineByRpo(packageRuntime, rpo)?.type, "auto_added");
      assert.equal(lineByRpo(packageRuntime, rpo)?.price, 0);
    }

    for (const rpo of TECH_BRONZE_GRAPHICS_RPOS) {
      const memberFirstRuntime = runtimeFor(data, "1lt_c07");
      memberFirstRuntime.handleChoice(activeChoiceByRpo(memberFirstRuntime, rpo));
      memberFirstRuntime.handleChoice(activeChoiceByRpo(memberFirstRuntime, "PCX"));
      assert.equal(lineByRpo(memberFirstRuntime, rpo)?.type, "selected");
      assert.equal(lineByRpo(memberFirstRuntime, rpo)?.price, 0);
      assert.equal(memberFirstRuntime.lineItems().filter((line) => line.rpo === rpo).length, 1);
    }
  }
});

test("Tech Bronze graphics package boundaries remain production-owned and preserved", () => {
  const production = loadGeneratedData();
  const shadow = loadShadowData();
  const fragment = emitCsvLegacyFragment();
  const pcxId = optionIdByRpo(production, "PCX");

  for (const rpo of TECH_BRONZE_GRAPHICS_RPOS) {
    assert.deepEqual(plain(rule(shadow, "PCX", rpo, "includes")), plain(rule(production, "PCX", rpo, "includes")));
    assert.deepEqual(plain(priceRule(shadow, "PCX", rpo, 0)), plain(priceRule(production, "PCX", rpo, 0)));

    const targetId = optionIdByRpo(production, rpo);
    assert.equal(fragment.rules.some((item) => item.source_id === pcxId && item.target_id === targetId), false);
    assert.equal(fragment.priceRules.some((item) => item.condition_option_id === pcxId && item.target_option_id === targetId), false);

    assert.equal(manifestHas({ record_type: "selectable", rpo, ownership: "projected_owned" }), true);
    assert.equal(manifestHas({ record_type: "rule", source_rpo: "PCX", target_rpo: rpo, ownership: "preserved_cross_boundary" }), true);
    assert.equal(manifestHas({ record_type: "priceRule", source_rpo: "PCX", target_rpo: rpo, ownership: "preserved_cross_boundary" }), true);
  }

  assert.deepEqual(plain(rule(shadow, "SHT", "PDV", "excludes")), plain(rule(production, "SHT", "PDV", "excludes")));
  const shtId = optionIdByRpo(production, "SHT");
  const pdvId = optionIdByRpo(production, "PDV");
  assert.equal(fragment.rules.some((item) => item.source_id === shtId && item.target_id === pdvId), false);
  assert.equal(manifestHas({ record_type: "rule", source_rpo: "SHT", target_rpo: "PDV", ownership: "preserved_cross_boundary" }), true);
});

test("Tech Bronze graphics projection does not claim broader graphics, badge, wheel, or package rows", () => {
  const owned = projectedOwnedRpos();

  for (const rpo of TECH_BRONZE_GRAPHICS_RPOS) {
    assert.equal(owned.has(rpo), true);
  }
  for (const rpo of OUT_OF_SCOPE_RPOS) {
    assert.equal(owned.has(rpo), false, `${rpo} should remain outside the SHT/SNG Tech Bronze graphics slice`);
  }
});
