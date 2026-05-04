import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import fs from "node:fs";
import test from "node:test";

import { createRuntime, loadGeneratedData, loadShadowData } from "./runtime-harness.mjs";

const PYTHON = ".venv/bin/python";
const SCRIPT = "scripts/stingray_csv_first_slice.py";
const OWNERSHIP_MANIFEST = "data/stingray/validation/projected_slice_ownership.csv";
const C2Z_RPO = "C2Z";
const ROOF_PRODUCTION_RPOS = new Set(["CF7", "CM9"]);

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

function normalizeC2zChoices(rows) {
  return Array.from(rows)
    .filter((choice) => choice.rpo === C2Z_RPO)
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

test("CSV evaluator prices direct C2Z carbon fiber Roof selection", () => {
  const production = loadGeneratedData();
  const result = evaluate("1lt_c07", [optionIdByRpo(production, C2Z_RPO)]);

  assert.deepEqual(result.validation_errors, []);
  assert.equal(result.selected_lines.find((line) => line.rpo === C2Z_RPO)?.final_price_usd, 2595);
});

test("CSV C2Z legacy fragment matches generated required Roof choice rows", () => {
  const production = loadGeneratedData();
  const projected = emitCsvLegacyFragment();
  const choices = normalizeC2zChoices(projected.choices);

  assert.deepEqual(projected.validation_errors, []);
  assert.deepEqual(choices, normalizeC2zChoices(production.choices));
  assert.equal(choices.length, 6);
  assert.deepEqual(
    choices.map((choice) => [choice.variant_id, choice.status, choice.status_label, choice.selectable, choice.active, choice.base_price]),
    [
      ["1lt_c07", "available", "Available", "True", "True", 2595],
      ["1lt_c67", "unavailable", "Not Available", "True", "True", 2595],
      ["2lt_c07", "available", "Available", "True", "True", 2595],
      ["2lt_c67", "unavailable", "Not Available", "True", "True", 2595],
      ["3lt_c07", "available", "Available", "True", "True", 2595],
      ["3lt_c67", "unavailable", "Not Available", "True", "True", 2595],
    ]
  );
});

test("C2Z projection claims only the carbon fiber Roof row and preserves Roof model boundaries", () => {
  const owned = projectedOwnedRpos();

  assert.equal(owned.has(C2Z_RPO), true);
  assert.equal(owned.has("CC3"), true);
  for (const rpo of ROOF_PRODUCTION_RPOS) {
    assert.equal(owned.has(rpo), false, `${rpo} should remain outside the C2Z slice`);
  }
  assert.equal(activeManifestRows().some((row) => row.record_type === "section" || row.group_id === "sec_roof_001" || row.group_id === "sec_stan_002"), false);
  assert.equal(manifestHas({ record_type: "rule", source_rpo: "SBT", target_rpo: "CC3", ownership: "preserved_cross_boundary" }), true);
});

test("production has no structured records touching C2Z", () => {
  const production = loadGeneratedData();

  assert.deepEqual(plain(rulesTouching(production, new Set([C2Z_RPO]))), []);
  assert.deepEqual(plain(priceRulesTouching(production, new Set([C2Z_RPO]))), []);
  assert.deepEqual(plain(groupIdsTouching(production, C2Z_RPO)), {
    exclusiveGroups: [],
    ruleGroups: [],
  });
});

test("shadow overlay does not emit owned C2Z rule surfaces", () => {
  const production = loadGeneratedData();
  const fragment = emitCsvLegacyFragment();
  const c2zId = optionIdByRpo(production, C2Z_RPO);

  assert.equal(fragment.rules.some((item) => item.source_id === c2zId || item.target_id === c2zId), false);
  assert.equal(fragment.priceRules.some((item) => item.condition_option_id === c2zId || item.target_option_id === c2zId), false);
});

test("shadow runtime preserves required Roof defaults C2Z replacement and SBT compatibility", () => {
  const roofRpos = new Set(["CF7", "CM9", "C2Z", "CC3", "D84", "D86"]);
  for (const data of [loadGeneratedData(), loadShadowData()]) {
    const coupeDefault = runtimeFor(data, "1lt_c07");
    assert.deepEqual(selectedRpos(coupeDefault, roofRpos), ["CF7"]);

    const convertibleDefault = runtimeFor(data, "1lt_c67");
    assert.deepEqual(selectedRpos(convertibleDefault, roofRpos), ["CM9"]);
    assert.equal(convertibleDefault.disableReasonForChoice(choiceByRpo(convertibleDefault, C2Z_RPO)), "Not available for this body and trim.");

    const c2zRuntime = runtimeFor(data, "1lt_c07");
    const c2z = activeChoiceByRpo(c2zRuntime, C2Z_RPO);
    c2zRuntime.handleChoice(c2z);
    assert.deepEqual(selectedRpos(c2zRuntime, roofRpos), ["C2Z"]);
    assert.equal(c2zRuntime.optionPrice(c2z.option_id), 2595);

    c2zRuntime.handleChoice(activeChoiceByRpo(c2zRuntime, "CC3"));
    assert.deepEqual(selectedRpos(c2zRuntime, roofRpos), ["CC3"]);
    c2zRuntime.handleChoice(activeChoiceByRpo(c2zRuntime, C2Z_RPO));
    assert.deepEqual(selectedRpos(c2zRuntime, roofRpos), ["C2Z"]);

    const sbtRuntime = runtimeFor(data, "1lt_c07");
    const sbt = activeChoiceByRpo(sbtRuntime, "SBT");
    const compatibleC2z = activeChoiceByRpo(sbtRuntime, C2Z_RPO);
    const blockedCc3 = activeChoiceByRpo(sbtRuntime, "CC3");
    sbtRuntime.handleChoice(sbt);
    assert.equal(sbtRuntime.disableReasonForChoice(compatibleC2z), "");
    assert.equal(sbtRuntime.disableReasonForChoice(blockedCc3), "Blocked by SBT LPO, Dual roof.");
    sbtRuntime.handleChoice(compatibleC2z);
    assert.equal(sbtRuntime.state.selected.has(sbt.option_id), true);
    assert.equal(sbtRuntime.state.selected.has(compatibleC2z.option_id), true);
  }
});
