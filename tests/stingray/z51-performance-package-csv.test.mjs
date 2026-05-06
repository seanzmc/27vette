import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import fs from "node:fs";
import test from "node:test";

import { loadGeneratedData, loadShadowData } from "./runtime-harness.mjs";

const PYTHON = ".venv/bin/python";
const SCRIPT = "scripts/stingray_csv_first_slice.py";
const OWNERSHIP_MANIFEST = "data/stingray/validation/projected_slice_ownership.csv";
const Z51_RPO = "Z51";
const Z51_OPTION_ID = "opt_z51_001";
const Z51_PRESERVED_BOUNDARIES = [
  { record_type: "rule", source_rpo: "5V7", target_rpo: "Z51" },
  { record_type: "rule", source_rpo: "", source_option_id: "opt_5vm_001", target_rpo: "Z51" },
  { record_type: "rule", source_rpo: "", source_option_id: "opt_5w8_001", target_rpo: "Z51" },
  { record_type: "rule", source_rpo: "FE2", target_rpo: "Z51" },
  { record_type: "rule", source_rpo: "FE4", target_rpo: "Z51" },
  { record_type: "rule", source_rpo: "RNX", target_rpo: "Z51" },
  { record_type: "rule", source_rpo: "RWJ", target_rpo: "Z51" },
  { record_type: "rule", source_rpo: "T0A", target_rpo: "Z51" },
  { record_type: "rule", source_rpo: "Z51", target_rpo: "FE3" },
  { record_type: "rule", source_rpo: "Z51", target_rpo: "G0K" },
  { record_type: "rule", source_rpo: "Z51", target_rpo: "G96" },
  { record_type: "rule", source_rpo: "Z51", target_rpo: "J55" },
  { record_type: "rule", source_rpo: "Z51", target_rpo: "M1N" },
  { record_type: "rule", source_rpo: "Z51", target_rpo: "QTU" },
  { record_type: "rule", source_rpo: "Z51", target_rpo: "T0A" },
  { record_type: "rule", source_rpo: "Z51", target_rpo: "V08" },
  { record_type: "priceRule", source_rpo: "Z51", target_rpo: "TVS" },
];

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

function normalizeZ51Choices(rows) {
  return Array.from(rows)
    .filter((choice) => choice.rpo === Z51_RPO)
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

function manifestHas(expected, rows = activeManifestRows()) {
  return rows.some((row) => Object.entries(expected).every(([key, value]) => row[key] === value));
}

function optionIdByRpo(data, rpo) {
  const ids = new Set(data.choices.filter((item) => item.rpo === rpo && item.active === "True").map((item) => item.option_id));
  assert.equal(ids.size, 1, `${rpo} should map to exactly one legacy option_id`);
  return [...ids][0];
}

function rulesTouchingOption(data, optionId) {
  return data.rules
    .filter((rule) => rule.source_id === optionId || rule.target_id === optionId)
    .map((rule) => ({
      rule_id: rule.rule_id,
      rule_type: rule.rule_type,
      source_id: rule.source_id,
      target_id: rule.target_id,
      runtime_action: rule.runtime_action,
      message: rule.message,
      auto_add: rule.auto_add,
    }))
    .sort((a, b) => `${a.rule_type}:${a.source_id}:${a.target_id}`.localeCompare(`${b.rule_type}:${b.source_id}:${b.target_id}`));
}

function priceRulesTouchingOption(data, optionId) {
  return data.priceRules
    .filter((rule) => rule.condition_option_id === optionId || rule.target_option_id === optionId)
    .map((rule) => ({
      price_rule_id: rule.price_rule_id,
      condition_option_id: rule.condition_option_id,
      target_option_id: rule.target_option_id,
      price_value: Number(rule.price_value),
      active: rule.active,
      notes: rule.notes,
    }))
    .sort((a, b) => `${a.condition_option_id}:${a.target_option_id}`.localeCompare(`${b.condition_option_id}:${b.target_option_id}`));
}

test("CSV evaluator prices direct Z51 Performance Package selection", () => {
  const result = evaluate("1lt_c07", [Z51_OPTION_ID]);
  const line = result.selected_lines.find((item) => item.rpo === Z51_RPO);

  assert.equal(line?.final_price_usd, 5395);
  assert.deepEqual(result.validation_errors, []);
});

test("CSV Z51 legacy fragment emits exact customer-facing production choice rows", () => {
  const production = loadGeneratedData();
  const projected = emitCsvLegacyFragment();
  const projectedZ51 = normalizeZ51Choices(projected.choices);

  assert.deepEqual(projected.validation_errors, []);
  assert.equal(projectedZ51.length, 6);
  assert.deepEqual(projectedZ51, normalizeZ51Choices(production.choices));
  assert.deepEqual(
    projectedZ51.map((choice) => [choice.variant_id, choice.body_style, choice.trim_level, choice.status, choice.selectable, choice.active, choice.base_price]),
    [
      ["1lt_c07", "coupe", "1LT", "available", "True", "True", 5395],
      ["1lt_c67", "convertible", "1LT", "available", "True", "True", 5395],
      ["2lt_c07", "coupe", "2LT", "available", "True", "True", 5395],
      ["2lt_c67", "convertible", "2LT", "available", "True", "True", 5395],
      ["3lt_c07", "coupe", "3LT", "available", "True", "True", 5395],
      ["3lt_c67", "convertible", "3LT", "available", "True", "True", 5395],
    ]
  );
  assert.deepEqual(
    [...new Set(projectedZ51.map((choice) => `${choice.section_id}:${choice.section_name}:${choice.category_id}:${choice.category_name}:${choice.step_key}`))],
    ["sec_perf_001:Performance:cat_mech_001:Mechanical:packages_performance"]
  );
  assert.deepEqual([...new Set(projectedZ51.map((choice) => `${choice.choice_mode}:${choice.selection_mode}`))], ["multi:multi_select_opt"]);
  assert.deepEqual([...new Set(projectedZ51.map((choice) => choice.display_order))], [30]);
});

test("ownership manifest projects Z51 while preserving all Z51 production boundaries", () => {
  const rows = activeManifestRows();

  assert.equal(manifestHas({ record_type: "selectable", rpo: Z51_RPO, ownership: "projected_owned" }, rows), true);
  assert.equal(manifestHas({ record_type: "guardedOption", rpo: Z51_RPO, ownership: "production_guarded" }, rows), false);
  assert.equal(
    parseCsv(fs.readFileSync(OWNERSHIP_MANIFEST, "utf8")).some(
      (row) => row.record_type === "guardedOption" && row.rpo === Z51_RPO && row.ownership === "production_guarded" && row.active === "false"
    ),
    true
  );
  for (const expected of Z51_PRESERVED_BOUNDARIES) {
    assert.equal(
      manifestHas({ ...expected, ownership: "preserved_cross_boundary" }, rows),
      true,
      `${expected.record_type} ${expected.source_rpo || expected.source_option_id} -> ${expected.target_rpo} should remain preserved`
    );
  }
});

test("shadow overlay preserves Z51 package rules and priceRule behavior", () => {
  const production = loadGeneratedData();
  const shadow = loadShadowData();
  const z51 = optionIdByRpo(production, Z51_RPO);

  assert.deepEqual(plain(rulesTouchingOption(shadow, z51)), plain(rulesTouchingOption(production, z51)));
  assert.deepEqual(plain(priceRulesTouchingOption(shadow, z51)), plain(priceRulesTouchingOption(production, z51)));
});
