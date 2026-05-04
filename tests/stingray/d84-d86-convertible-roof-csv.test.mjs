import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import fs from "node:fs";
import test from "node:test";

import { createRuntime, loadGeneratedData, loadShadowData } from "./runtime-harness.mjs";

const PYTHON = ".venv/bin/python";
const SCRIPT = "scripts/stingray_csv_first_slice.py";
const OWNERSHIP_MANIFEST = "data/stingray/validation/projected_slice_ownership.csv";
const ROOF_RPOS = new Set(["CF7", "CM9", "C2Z", "CC3", "D84", "D86"]);
const CONVERTIBLE_ROOF_RPOS = new Set(["D84", "D86"]);
const ROOF_DEFAULT_RPOS = new Set(["CF7", "CM9"]);

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

function normalizeConvertibleRoofChoices(rows) {
  return Array.from(rows)
    .filter((choice) => CONVERTIBLE_ROOF_RPOS.has(choice.rpo))
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

function choiceByRpo(runtime, rpo) {
  const choice = runtime.activeChoiceRows().find((item) => item.rpo === rpo && item.active === "True");
  assert.ok(choice, `${rpo} should have an active choice row`);
  return choice;
}

function selectedRpos(runtime, rpos) {
  return [...runtime.state.selected]
    .map((optionId) => runtime.activeChoiceRows().find((choice) => choice.option_id === optionId)?.rpo)
    .filter((rpo) => rpos.has(rpo))
    .sort();
}

function linePrice(runtime, rpo) {
  return runtime.lineItems().find((line) => line.rpo === rpo)?.price;
}

function rule(data, sourceRpo, targetRpo, ruleType) {
  const sourceId = optionIdByRpo(data, sourceRpo);
  const targetId = optionIdByRpo(data, targetRpo);
  return data.rules.find((item) => item.source_id === sourceId && item.target_id === targetId && item.rule_type === ruleType);
}

function rulesTouching(data, rpos) {
  const ids = new Set(data.choices.filter((choice) => rpos.has(choice.rpo)).map((choice) => choice.option_id));
  return data.rules
    .filter((item) => ids.has(item.source_id) || ids.has(item.target_id))
    .map((item) => {
      const source = data.choices.find((choice) => choice.option_id === item.source_id)?.rpo || item.source_id;
      const target = data.choices.find((choice) => choice.option_id === item.target_id)?.rpo || item.target_id;
      return `${source}->${target}:${item.rule_type}:${item.auto_add}`;
    })
    .sort();
}

function priceRulesTouching(data, rpos) {
  const ids = new Set(data.choices.filter((choice) => rpos.has(choice.rpo)).map((choice) => choice.option_id));
  return data.priceRules
    .filter((item) => ids.has(item.condition_option_id) || ids.has(item.target_option_id))
    .map((item) => {
      const source = data.choices.find((choice) => choice.option_id === item.condition_option_id)?.rpo || item.condition_option_id;
      const target = data.choices.find((choice) => choice.option_id === item.target_option_id)?.rpo || item.target_option_id;
      return `${source}->${target}:${item.price_rule_type}:${Number(item.price_value)}`;
    })
    .sort();
}

function groupIdsTouching(data, rpo) {
  const ids = new Set(data.choices.filter((choice) => choice.rpo === rpo).map((choice) => choice.option_id));
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

test("CSV evaluator prices direct D84 and D86 convertible Roof selections", () => {
  const production = loadGeneratedData();

  for (const rpo of CONVERTIBLE_ROOF_RPOS) {
    const result = evaluate("1lt_c67", [optionIdByRpo(production, rpo)]);
    assert.deepEqual(result.validation_errors, []);
    assert.equal(result.selected_lines.find((line) => line.rpo === rpo)?.final_price_usd, 1295);
  }
});

test("CSV D84 and D86 legacy fragment matches generated convertible Roof choice rows", () => {
  const production = loadGeneratedData();
  const projected = emitCsvLegacyFragment();
  const choices = normalizeConvertibleRoofChoices(projected.choices);

  assert.deepEqual(projected.validation_errors, []);
  assert.deepEqual(choices, normalizeConvertibleRoofChoices(production.choices));
  assert.equal(choices.length, 12);
  assert.deepEqual(
    choices.map((choice) => [choice.rpo, choice.variant_id, choice.status, choice.status_label, choice.selectable, choice.active, choice.base_price]),
    [
      ["D84", "1lt_c07", "unavailable", "Not Available", "True", "True", 1295],
      ["D86", "1lt_c07", "unavailable", "Not Available", "True", "True", 1295],
      ["D84", "1lt_c67", "available", "Available", "True", "True", 1295],
      ["D86", "1lt_c67", "available", "Available", "True", "True", 1295],
      ["D84", "2lt_c07", "unavailable", "Not Available", "True", "True", 1295],
      ["D86", "2lt_c07", "unavailable", "Not Available", "True", "True", 1295],
      ["D84", "2lt_c67", "available", "Available", "True", "True", 1295],
      ["D86", "2lt_c67", "available", "Available", "True", "True", 1295],
      ["D84", "3lt_c07", "unavailable", "Not Available", "True", "True", 1295],
      ["D86", "3lt_c07", "unavailable", "Not Available", "True", "True", 1295],
      ["D84", "3lt_c67", "available", "Available", "True", "True", 1295],
      ["D86", "3lt_c67", "available", "Available", "True", "True", 1295],
    ]
  );
});

test("D84 and D86 projection preserves paint and Roof model boundaries", () => {
  const owned = projectedOwnedRpos();

  for (const rpo of CONVERTIBLE_ROOF_RPOS) {
    assert.equal(owned.has(rpo), true);
  }
  for (const rpo of ["GBA", "ZYC", ...ROOF_DEFAULT_RPOS]) {
    assert.equal(owned.has(rpo), false, `${rpo} should remain outside the D84/D86 slice`);
  }
  assert.equal(activeManifestRows().some((row) => row.record_type === "section" || row.group_id === "sec_roof_001" || row.group_id === "sec_stan_002"), false);
  assert.equal(manifestHas({ record_type: "rule", source_rpo: "D84", target_rpo: "GBA", ownership: "preserved_cross_boundary" }), true);
  assert.equal(manifestHas({ record_type: "rule", source_rpo: "D86", target_rpo: "GBA", ownership: "preserved_cross_boundary" }), true);
});

test("production has only classified GBA excludes touching D84 and D86", () => {
  const production = loadGeneratedData();

  assert.deepEqual(plain(rulesTouching(production, CONVERTIBLE_ROOF_RPOS)), ["D84->GBA:excludes:False", "D86->GBA:excludes:False"]);
  assert.deepEqual(plain(priceRulesTouching(production, CONVERTIBLE_ROOF_RPOS)), []);
  for (const rpo of CONVERTIBLE_ROOF_RPOS) {
    assert.deepEqual(plain(groupIdsTouching(production, rpo)), {
      exclusiveGroups: [],
      ruleGroups: [],
    });
  }
});

test("shadow overlay preserves D84 and D86 paint excludes and does not emit owned paint rules", () => {
  const production = loadGeneratedData();
  const shadow = loadShadowData();
  const fragment = emitCsvLegacyFragment();
  const d84Id = optionIdByRpo(production, "D84");
  const d86Id = optionIdByRpo(production, "D86");

  assert.deepEqual(plain(rule(shadow, "D84", "GBA", "excludes")), plain(rule(production, "D84", "GBA", "excludes")));
  assert.deepEqual(plain(rule(shadow, "D86", "GBA", "excludes")), plain(rule(production, "D86", "GBA", "excludes")));
  assert.equal(fragment.rules.some((item) => [d84Id, d86Id].includes(item.source_id) || [d84Id, d86Id].includes(item.target_id)), false);
  assert.equal(fragment.priceRules.some((item) => [d84Id, d86Id].includes(item.condition_option_id) || [d84Id, d86Id].includes(item.target_option_id)), false);
});

test("shadow runtime preserves convertible Roof replacement and GBA/ZYC behavior", () => {
  for (const data of [loadGeneratedData(), loadShadowData()]) {
    const coupeDefault = runtimeFor(data, "1lt_c07");
    assert.deepEqual(selectedRpos(coupeDefault, ROOF_RPOS), ["CF7"]);
    assert.equal(coupeDefault.disableReasonForChoice(choiceByRpo(coupeDefault, "D84")), "Not available for this body and trim.");
    assert.equal(coupeDefault.disableReasonForChoice(choiceByRpo(coupeDefault, "D86")), "Not available for this body and trim.");

    const convertibleDefault = runtimeFor(data, "1lt_c67");
    assert.deepEqual(selectedRpos(convertibleDefault, ROOF_RPOS), ["CM9"]);

    const d84Runtime = runtimeFor(data, "1lt_c67");
    const d84 = activeChoiceByRpo(d84Runtime, "D84");
    d84Runtime.handleChoice(d84);
    assert.deepEqual(selectedRpos(d84Runtime, ROOF_RPOS), ["D84"]);
    assert.equal(linePrice(d84Runtime, "D84"), 1295);
    assert.equal(d84Runtime.disableReasonForChoice(activeChoiceByRpo(d84Runtime, "GBA")), "Blocked by D84 Convertible top.");

    const d86 = activeChoiceByRpo(d84Runtime, "D86");
    d84Runtime.handleChoice(d86);
    assert.deepEqual(selectedRpos(d84Runtime, ROOF_RPOS), ["D86"]);
    assert.equal(linePrice(d84Runtime, "D86"), 1295);
    assert.equal(d84Runtime.disableReasonForChoice(activeChoiceByRpo(d84Runtime, "GBA")), "Blocked by D86 Convertible top.");

    d84Runtime.handleChoice(activeChoiceByRpo(d84Runtime, "CM9"));
    assert.deepEqual(selectedRpos(d84Runtime, ROOF_RPOS), ["CM9"]);

    const zycRuntime = runtimeFor(data, "1lt_c67");
    zycRuntime.handleChoice(activeChoiceByRpo(zycRuntime, "ZYC"));
    zycRuntime.handleChoice(activeChoiceByRpo(zycRuntime, "GBA"));
    assert.deepEqual(selectedRpos(zycRuntime, new Set(["GBA", "ZYC"])), ["GBA"]);
  }
});
