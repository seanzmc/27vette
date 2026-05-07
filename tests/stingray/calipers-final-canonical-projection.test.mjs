import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import fs from "node:fs";
import test from "node:test";

const PYTHON = ".venv/bin/python";
const FIRST_SLICE_SCRIPT = "scripts/stingray_csv_first_slice.py";
const OVERLAY_SCRIPT = "scripts/stingray_csv_shadow_overlay.py";
const PRODUCTION_DATA = "form-app/data.js";
const CALIPER_OPTION_IDS = [
  "opt_j6a_001",
  "opt_j6a_002",
  "opt_j6f_001",
  "opt_j6e_001",
  "opt_j6n_001",
  "opt_j6b_001",
];
const CALIPER_RPOS = new Set(["J6A", "J6F", "J6E", "J6N", "J6B"]);

function parseCsv(text) {
  const lines = text.trim().split(/\r?\n/);
  const headers = lines[0].split(",");
  return lines.slice(1).map((line) => {
    const values = [];
    let current = "";
    let inQuotes = false;
    for (let index = 0; index < line.length; index += 1) {
      const char = line[index];
      const next = line[index + 1];
      if (char === "\"" && inQuotes && next === "\"") {
        current += "\"";
        index += 1;
      } else if (char === "\"") {
        inQuotes = !inQuotes;
      } else if (char === "," && !inQuotes) {
        values.push(current);
        current = "";
      } else {
        current += char;
      }
    }
    values.push(current);
    return Object.fromEntries(headers.map((header, index) => [header, values[index] ?? ""]));
  });
}

function productionData() {
  const source = fs.readFileSync(PRODUCTION_DATA, "utf8");
  const match = source.match(/window\.CORVETTE_FORM_DATA\s*=\s*(\{.*\})\s*;\s*window\.STINGRAY_FORM_DATA\s*=/s);
  assert.ok(match, "production data assignment exists");
  return JSON.parse(match[1]).models.stingray.data;
}

function legacyFragment() {
  const output = execFileSync(PYTHON, [FIRST_SLICE_SCRIPT, "--emit-legacy-fragment"], {
    cwd: process.cwd(),
    encoding: "utf8",
    maxBuffer: 16 * 1024 * 1024,
  });
  return JSON.parse(output);
}

function shadowOverlay() {
  const output = execFileSync(PYTHON, [OVERLAY_SCRIPT], {
    cwd: process.cwd(),
    encoding: "utf8",
    maxBuffer: 32 * 1024 * 1024,
  });
  return JSON.parse(output);
}

function caliperChoices(data) {
  return data.choices
    .filter((row) => CALIPER_OPTION_IDS.includes(row.option_id))
    .map((row) => ({
      choice_id: row.choice_id,
      option_id: row.option_id,
      rpo: row.rpo,
      label: row.label,
      description: row.description,
      section_id: row.section_id,
      section_name: row.section_name,
      category_id: row.category_id,
      category_name: row.category_name,
      step_key: row.step_key,
      variant_id: row.variant_id,
      body_style: row.body_style,
      trim_level: row.trim_level,
      status: row.status,
      status_label: row.status_label,
      selectable: row.selectable,
      active: row.active,
      choice_mode: row.choice_mode,
      selection_mode: row.selection_mode,
      selection_mode_label: row.selection_mode_label,
      base_price: row.base_price,
      display_order: row.display_order,
      source_detail_raw: row.source_detail_raw,
    }))
    .sort((left, right) => left.choice_id.localeCompare(right.choice_id));
}

test("final canonical Calipers projection emits production-equivalent legacy presentations", () => {
  const fragment = legacyFragment();
  assert.deepEqual(fragment.validation_errors, []);

  const projected = caliperChoices(fragment);
  const production = caliperChoices(productionData());
  assert.deepEqual(projected, production);
  assert.equal(projected.length, 36);
  assert.equal(projected.filter((row) => row.section_id === "sec_cali_001" && row.selectable === "True").length, 30);
  assert.equal(projected.filter((row) => row.option_id === "opt_j6a_002" && row.selection_mode === "display_only").length, 6);

  const expected = new Map([
    ["opt_j6a_001", ["J6A", 10, 0, "standard", "Standard", "Caliper Color", "single_select_req", "True"]],
    ["opt_j6a_002", ["J6A", 1, 0, "standard", "Standard", "Standard Options", "display_only", "False"]],
    ["opt_j6f_001", ["J6F", 20, 795, "available", "Available", "Caliper Color", "single_select_req", "True"]],
    ["opt_j6e_001", ["J6E", 30, 795, "available", "Available", "Caliper Color", "single_select_req", "True"]],
    ["opt_j6n_001", ["J6N", 40, 795, "available", "Available", "Caliper Color", "single_select_req", "True"]],
    ["opt_j6b_001", ["J6B", 50, 795, "available", "Available", "Caliper Color", "single_select_req", "True"]],
  ]);
  for (const [optionId, [rpo, order, price, status, statusLabel, section, mode, selectable]] of expected) {
    const rows = projected.filter((row) => row.option_id === optionId);
    assert.equal(rows.length, 6);
    assert.ok(rows.every((row) =>
      row.rpo === rpo
      && row.display_order === order
      && row.base_price === price
      && row.status === status
      && row.status_label === statusLabel
      && row.section_name === section
      && row.selection_mode === mode
      && row.selectable === selectable
    ));
  }
});

test("Calipers are authored only through final canonical tables", () => {
  const oldSelectables = parseCsv(fs.readFileSync("data/stingray/catalog/selectables.csv", "utf8"));
  const oldDisplay = parseCsv(fs.readFileSync("data/stingray/ui/selectable_display.csv", "utf8"));
  const oldBasePrices = parseCsv(fs.readFileSync("data/stingray/pricing/base_prices.csv", "utf8"));
  assert.equal(oldSelectables.some((row) => CALIPER_RPOS.has(row.rpo) || CALIPER_OPTION_IDS.includes(row.selectable_id)), false);
  assert.equal(oldDisplay.some((row) => CALIPER_OPTION_IDS.includes(row.selectable_id)), false);
  assert.equal(oldBasePrices.some((row) => CALIPER_OPTION_IDS.includes(row.target_selector_id)), false);

  const canonicalOptions = parseCsv(fs.readFileSync("data/stingray/canonical/options/canonical_options.csv", "utf8"));
  const presentations = parseCsv(fs.readFileSync("data/stingray/canonical/presentation/option_presentations.csv", "utf8"));
  const prices = parseCsv(fs.readFileSync("data/stingray/canonical/pricing/canonical_base_prices.csv", "utf8"));
  const ownership = parseCsv(fs.readFileSync("data/stingray/canonical/ownership/projection_ownership.csv", "utf8"));
  assert.equal(canonicalOptions.filter((row) => CALIPER_RPOS.has(row.rpo)).length, 5);
  assert.deepEqual(presentations.map((row) => row.legacy_option_id).sort(), [...CALIPER_OPTION_IDS].sort());
  assert.equal(prices.filter((row) => row.canonical_option_id.startsWith("canonical_j6")).length, 5);
  assert.deepEqual(ownership.map((row) => row.legacy_option_id).sort(), [...CALIPER_OPTION_IDS].sort());
});

test("Calipers have no migrated relationship rows and shadow overlay preserves parity", () => {
  const relationshipFiles = [
    "data/stingray/logic/dependency_rules.csv",
    "data/stingray/logic/simple_dependency_rules.csv",
    "data/stingray/logic/auto_adds.csv",
    "data/stingray/pricing/price_rules.csv",
    "data/stingray/logic/rule_groups.csv",
    "data/stingray/logic/exclusive_groups.csv",
  ];
  for (const file of relationshipFiles) {
    const rows = parseCsv(fs.readFileSync(file, "utf8"));
    assert.equal(JSON.stringify(rows).includes("opt_j6"), false, `${file} should not reference Calipers`);
  }

  assert.deepEqual(caliperChoices(shadowOverlay()), caliperChoices(productionData()));
});
