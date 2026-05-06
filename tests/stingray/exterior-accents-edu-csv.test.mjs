import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import fs from "node:fs";
import test from "node:test";

import { createRuntime, loadGeneratedData, loadShadowData } from "./runtime-harness.mjs";

const PYTHON = ".venv/bin/python";
const SCRIPT = "scripts/stingray_csv_first_slice.py";
const OWNERSHIP_MANIFEST = "data/stingray/validation/projected_slice_ownership.csv";
const EDU_RPO = "EDU";
const EFY_RPO = "EFY";
const EXTERIOR_ACCENTS_PRODUCTION_RPOS = new Set(["EFR"]);
const PAINT_ROOF_AND_CLEANUP_RPOS = new Set(["ZYC", "DRG", "RYQ", "RZ9"]);

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

function normalizeEduChoices(rows) {
  return Array.from(rows)
    .filter((choice) => choice.rpo === EDU_RPO)
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

function normalizeEfyChoices(rows) {
  return Array.from(rows)
    .filter((choice) => choice.rpo === EFY_RPO)
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

test("CSV evaluator prices direct EDU exterior accent selection", () => {
  const production = loadGeneratedData();
  const result = evaluate("1lt_c07", [optionIdByRpo(production, EDU_RPO)]);
  const line = result.selected_lines.find((item) => item.rpo === EDU_RPO);

  assert.equal(line?.final_price_usd, 995);
  assert.deepEqual(result.validation_errors, []);
});

test("CSV EDU legacy fragment matches generated required-section choice rows", () => {
  const production = loadGeneratedData();
  const projected = emitCsvLegacyFragment();

  assert.deepEqual(projected.validation_errors, []);
  assert.deepEqual(normalizeEduChoices(projected.choices), normalizeEduChoices(production.choices));
});

test("CSV EFY legacy fragment emits exact customer-facing production choice rows", () => {
  const production = loadGeneratedData();
  const projected = emitCsvLegacyFragment();
  const projectedEfy = normalizeEfyChoices(projected.choices);

  assert.deepEqual(projected.validation_errors, []);
  assert.equal(projectedEfy.length, 6);
  assert.deepEqual(projectedEfy, normalizeEfyChoices(production.choices));
  assert.deepEqual(
    projectedEfy.map((choice) => [choice.variant_id, choice.body_style, choice.trim_level, choice.status, choice.selectable, choice.active, choice.base_price]),
    [
      ["1lt_c07", "coupe", "1LT", "available", "True", "True", 995],
      ["1lt_c67", "convertible", "1LT", "available", "True", "True", 995],
      ["2lt_c07", "coupe", "2LT", "available", "True", "True", 995],
      ["2lt_c67", "convertible", "2LT", "available", "True", "True", 995],
      ["3lt_c07", "coupe", "3LT", "available", "True", "True", 995],
      ["3lt_c67", "convertible", "3LT", "available", "True", "True", 995],
    ]
  );
  assert.deepEqual(
    [...new Set(projectedEfy.map((choice) => `${choice.section_id}:${choice.section_name}:${choice.category_id}:${choice.category_name}:${choice.step_key}`))],
    ["sec_exte_001:Exterior Accents:cat_exte_001:Exterior:exterior_appearance"]
  );
  assert.deepEqual([...new Set(projectedEfy.map((choice) => `${choice.choice_mode}:${choice.selection_mode}`))], ["single:single_select_req"]);
  assert.deepEqual([...new Set(projectedEfy.map((choice) => choice.display_order))], [20]);
});

test("ownership manifest projects EDU and EFY while preserving EFY dependency boundaries", () => {
  const production = loadGeneratedData();
  const owned = projectedOwnedRpos();
  const eduOptionId = optionIdByRpo(production, EDU_RPO);
  const efyOptionId = optionIdByRpo(production, EFY_RPO);

  assert.deepEqual(plain(production.rules.filter((rule) => rule.source_id === eduOptionId || rule.target_id === eduOptionId)), []);
  assert.deepEqual(
    plain(production.rules.filter((rule) => rule.source_id === efyOptionId || rule.target_id === efyOptionId).map((rule) => rule.rule_id).sort()),
    ["rule_opt_efy_001_excludes_opt_gba_001", "rule_opt_ryq_001_excludes_opt_efy_001", "rule_opt_rz9_001_excludes_opt_efy_001"]
  );
  assert.deepEqual(plain(production.priceRules.filter((rule) => rule.condition_option_id === eduOptionId || rule.target_option_id === eduOptionId)), []);
  assert.deepEqual(plain(groupIdsTouchingOption(production.exclusiveGroups, eduOptionId)), []);
  assert.deepEqual(plain(ruleGroupIdsTouchingOption(production.ruleGroups, eduOptionId)), []);
  assert.equal(manifestHas({ record_type: "selectable", rpo: EDU_RPO, ownership: "projected_owned" }), true);
  assert.equal(manifestHas({ record_type: "selectable", rpo: EFY_RPO, ownership: "projected_owned" }), true);

  assert.equal(activeManifestRows().some((row) => row.record_type === "section" || row.group_id === "sec_exte_001"), false);
  for (const rpo of [...EXTERIOR_ACCENTS_PRODUCTION_RPOS, ...PAINT_ROOF_AND_CLEANUP_RPOS]) {
    assert.equal(owned.has(rpo), false, `${rpo} should remain outside the EDU standalone Exterior Accents slice`);
  }
  for (const expected of [
    { record_type: "rule", source_rpo: "EFY", target_rpo: "GBA", ownership: "preserved_cross_boundary" },
    { record_type: "rule", source_rpo: "RZ9", target_rpo: "EFY", ownership: "preserved_cross_boundary" },
    { record_type: "rule", source_rpo: "", source_option_id: "opt_ryq_001", target_rpo: "EFY", ownership: "preserved_cross_boundary" },
  ]) {
    assert.equal(manifestHas(expected), true, `${JSON.stringify(expected)} should remain preserved`);
  }
});

test("shadow runtime preserves required Exterior Accents replacement and EFY paint block", () => {
  for (const data of [loadGeneratedData(), loadShadowData()]) {
    const initialRuntime = runtimeFor(data, "1lt_c07");
    assert.deepEqual(selectedRpos(initialRuntime, new Set(["EFR", "EFY", "EDU"])), ["EFR"]);

    const eduRuntime = runtimeFor(data, "1lt_c07");
    assert.equal(eduRuntime.disableReasonForChoice(activeChoiceByRpo(eduRuntime, EDU_RPO)), "");
    handleRpo(eduRuntime, EDU_RPO);
    assert.deepEqual(selectedRpos(eduRuntime, new Set(["EFR", "EFY", "EDU"])), ["EDU"]);
    assert.equal(eduRuntime.optionPrice(activeChoiceByRpo(eduRuntime, EDU_RPO).option_id), 995);

    const efyRuntime = runtimeFor(data, "1lt_c07");
    handleRpo(efyRuntime, EDU_RPO);
    handleRpo(efyRuntime, "EFY");
    assert.deepEqual(selectedRpos(efyRuntime, new Set(["EFR", "EFY", "EDU"])), ["EFY"]);
    assert.match(efyRuntime.disableReasonForChoice(activeChoiceByRpo(efyRuntime, "GBA")), /Blocked by EFY Body-color accents/);
  }
});
