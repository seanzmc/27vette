import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import fs from "node:fs";
import test from "node:test";

import { loadGeneratedData, loadShadowData } from "./runtime-harness.mjs";

const PYTHON = ".venv/bin/python";
const FRAGMENT_SCRIPT = "scripts/stingray_csv_first_slice.py";
const OWNERSHIP_MANIFEST = "data/stingray/validation/projected_slice_ownership.csv";

function parseCsv(source) {
  const rows = [];
  let row = [];
  let field = "";
  let inQuotes = false;
  for (let index = 0; index < source.length; index += 1) {
    const char = source[index];
    const next = source[index + 1];
    if (char === '"' && inQuotes && next === '"') {
      field += '"';
      index += 1;
    } else if (char === '"') {
      inQuotes = !inQuotes;
    } else if (char === "," && !inQuotes) {
      row.push(field);
      field = "";
    } else if ((char === "\n" || char === "\r") && !inQuotes) {
      if (char === "\r" && next === "\n") index += 1;
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

function emitCsvLegacyFragment() {
  const output = execFileSync(PYTHON, [FRAGMENT_SCRIPT, "--emit-legacy-fragment"], {
    cwd: process.cwd(),
    encoding: "utf8",
    maxBuffer: 16 * 1024 * 1024,
  });
  return JSON.parse(output);
}

function activeManifestRows() {
  return parseCsv(fs.readFileSync(OWNERSHIP_MANIFEST, "utf8")).filter((row) => row.active === "true");
}

function normalizeQebChoices(data) {
  return data.choices
    .filter((choice) => choice.rpo === "QEB")
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

const WHEEL_CHOICE_EXPECTATIONS = [
  {
    option_id: "opt_qeb_001",
    rpo: "QEB",
    display_order: 10,
    base_price: 0,
    source: "canonical",
  },
  {
    option_id: "opt_q9o_001",
    rpo: "Q9O",
    display_order: 20,
    base_price: 995,
    source: "selectables",
  },
  {
    option_id: "opt_qe6_001",
    rpo: "QE6",
    display_order: 30,
    base_price: 1095,
    source: "selectables",
  },
  {
    option_id: "opt_q9i_001",
    rpo: "Q9I",
    display_order: 40,
    base_price: 1095,
    source: "selectables",
  },
  {
    option_id: "opt_q9a_001",
    rpo: "Q9A",
    display_order: 50,
    base_price: 1495,
    source: "selectables",
  },
  {
    option_id: "opt_q99_001",
    rpo: "Q99",
    display_order: 60,
    base_price: 1995,
    source: "selectables",
  },
];

function normalizeWheelChoices(data) {
  const wheelOptionIds = new Set(WHEEL_CHOICE_EXPECTATIONS.map((choice) => choice.option_id));
  return data.choices
    .filter((choice) => wheelOptionIds.has(choice.option_id))
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

function rowsFor(file) {
  return parseCsv(fs.readFileSync(file, "utf8"));
}

function plain(value) {
  return JSON.parse(JSON.stringify(value));
}

test("QEB canonical projection emits both production option IDs exactly", () => {
  const production = loadGeneratedData();
  const projected = emitCsvLegacyFragment();
  const qebChoices = normalizeQebChoices(projected);

  assert.deepEqual(projected.validation_errors, []);
  assert.deepEqual(plain(qebChoices), plain(normalizeQebChoices(production)));
  assert.equal(qebChoices.length, 12);
  assert.equal(qebChoices.filter((choice) => choice.option_id === "opt_qeb_001").length, 6);
  assert.equal(qebChoices.filter((choice) => choice.option_id === "opt_qeb_002").length, 6);

  assert.ok(qebChoices.every((choice) => choice.base_price === 0));
  assert.ok(qebChoices.filter((choice) => choice.option_id === "opt_qeb_001").every((choice) =>
    choice.section_id === "sec_whee_002"
    && choice.section_name === "Wheels"
    && choice.category_id === "cat_exte_001"
    && choice.category_name === "Exterior"
    && choice.step_key === "wheels"
    && choice.choice_mode === "single"
    && choice.selection_mode === "single_select_req"
    && choice.selectable === "True"
    && choice.status === "standard"
    && choice.status_label === "Standard"
  ));
  assert.ok(qebChoices.filter((choice) => choice.option_id === "opt_qeb_002").every((choice) =>
    choice.section_id === "sec_stan_002"
    && choice.section_name === "Standard Options"
    && choice.category_id === "cat_stan_001"
    && choice.category_name === "Standard Equipment"
    && choice.step_key === "standard_equipment"
    && choice.choice_mode === "display"
    && choice.selection_mode === "display_only"
    && choice.selectable === "False"
    && choice.status === "standard"
    && choice.status_label === "Standard"
  ));
});

test("Wheels projection emits QEB canonical choice and five regular CSV choices", () => {
  const production = loadGeneratedData();
  const projected = emitCsvLegacyFragment();
  const wheelChoices = normalizeWheelChoices(projected);

  assert.deepEqual(projected.validation_errors, []);
  assert.deepEqual(plain(wheelChoices), plain(normalizeWheelChoices(production)));
  assert.equal(wheelChoices.length, 36);

  for (const expected of WHEEL_CHOICE_EXPECTATIONS) {
    const choices = wheelChoices.filter((choice) => choice.option_id === expected.option_id);
    assert.equal(choices.length, 6, `${expected.option_id} should emit once per Stingray variant`);
    assert.ok(choices.every((choice) =>
      choice.rpo === expected.rpo
      && choice.section_id === "sec_whee_002"
      && choice.section_name === "Wheels"
      && choice.category_id === "cat_exte_001"
      && choice.category_name === "Exterior"
      && choice.step_key === "wheels"
      && choice.choice_mode === "single"
      && choice.selection_mode === "single_select_req"
      && choice.selection_mode_label === "Required single choice"
      && choice.selectable === "True"
      && choice.active === "True"
      && choice.base_price === expected.base_price
      && choice.display_order === expected.display_order
    ), `${expected.option_id} should match production Wheels shape`);
  }

  assert.equal(normalizeQebChoices(projected).filter((choice) => choice.option_id === "opt_qeb_002").length, 6);
});

test("QEB is authored only through canonical presentation rows", () => {
  assert.deepEqual(rowsFor("data/stingray/catalog/selectables.csv").filter((row) => row.rpo === "QEB" || row.selectable_id.startsWith("opt_qeb_")), []);
  assert.deepEqual(rowsFor("data/stingray/ui/selectable_display.csv").filter((row) => row.selectable_id.startsWith("opt_qeb_") || row.legacy_option_id.startsWith("opt_qeb_")), []);
  assert.deepEqual(rowsFor("data/stingray/pricing/base_prices.csv").filter((row) => row.target_selector_id.startsWith("opt_qeb_")), []);

  const canonicalRows = rowsFor("data/stingray/catalog/canonical_options.csv").filter((row) => row.canonical_option_id === "canonical_qeb");
  const presentationRows = rowsFor("data/stingray/ui/option_presentations.csv").filter((row) => row.canonical_option_id === "canonical_qeb");
  const statusRows = rowsFor("data/stingray/logic/option_status_rules.csv").filter((row) => row.canonical_option_id === "canonical_qeb");

  assert.equal(canonicalRows.length, 1);
  assert.deepEqual(presentationRows.map((row) => row.legacy_option_id).sort(), ["opt_qeb_001", "opt_qeb_002"]);
  assert.deepEqual(statusRows.map((row) => row.status_rule_id).sort(), [
    "status_qeb_standard_options_standard",
    "status_qeb_wheels_choice_standard",
  ]);
});

test("five non-QEB Wheels choices are authored through regular projection rows", () => {
  const selectables = rowsFor("data/stingray/catalog/selectables.csv");
  const displayRows = rowsFor("data/stingray/ui/selectable_display.csv");
  const basePrices = rowsFor("data/stingray/pricing/base_prices.csv");
  const ownershipRows = activeManifestRows();

  for (const expected of WHEEL_CHOICE_EXPECTATIONS.filter((choice) => choice.source === "selectables")) {
    const selectable = selectables.find((row) => row.selectable_id === expected.option_id);
    assert.ok(selectable, `${expected.option_id} should be authored in selectables.csv`);
    assert.equal(selectable.selectable_type, "option");
    assert.equal(selectable.rpo, expected.rpo);
    assert.equal(selectable.active, "true");

    const display = displayRows.find((row) => row.selectable_id === expected.option_id);
    assert.ok(display, `${expected.option_id} should be authored in selectable_display.csv`);
    assert.equal(display.legacy_option_id, expected.option_id);
    assert.equal(display.section_id, "sec_whee_002");
    assert.equal(display.section_name, "Wheels");
    assert.equal(display.category_id, "cat_exte_001");
    assert.equal(display.category_name, "Exterior");
    assert.equal(display.step_key, "wheels");
    assert.equal(display.choice_mode, "single");
    assert.equal(display.selection_mode, "single_select_req");
    assert.equal(display.display_order, String(expected.display_order));

    const basePrice = basePrices.find((row) => row.target_selector_id === expected.option_id);
    assert.ok(basePrice, `${expected.option_id} should have a base price`);
    assert.equal(basePrice.target_selector_type, "selectable");
    assert.equal(basePrice.amount_usd, String(expected.base_price));
    assert.equal(basePrice.active, "true");

    assert.ok(ownershipRows.some((row) =>
      row.record_type === "selectable"
      && row.rpo === expected.rpo
      && row.ownership === "projected_owned"
    ), `${expected.rpo} should be projected-owned`);
  }
});

test("QEB projection owns only the selectable replacement and no relationships", () => {
  assert.equal(activeManifestRows().some((row) =>
    row.record_type === "selectable"
    && row.rpo === "QEB"
    && row.ownership === "projected_owned"
  ), true);

  for (const data of [loadGeneratedData(), loadShadowData()]) {
    const qebIds = new Set(data.choices.filter((choice) => choice.rpo === "QEB").map((choice) => choice.option_id));
    assert.deepEqual(plain(data.rules.filter((rule) => qebIds.has(rule.source_id) || qebIds.has(rule.target_id))), []);
    assert.deepEqual(plain(data.priceRules.filter((rule) => qebIds.has(rule.condition_option_id) || qebIds.has(rule.target_option_id))), []);
    assert.deepEqual(plain(data.exclusiveGroups.filter((group) => group.option_ids.some((optionId) => qebIds.has(optionId)))), []);
    assert.deepEqual(plain(data.ruleGroups.filter((group) =>
      qebIds.has(group.source_id) || group.target_ids.some((optionId) => qebIds.has(optionId))
    )), []);
  }
});

test("five non-QEB Wheels choices have no production or shadow relationships", () => {
  const wheelOptionIds = new Set(WHEEL_CHOICE_EXPECTATIONS
    .filter((choice) => choice.source === "selectables")
    .map((choice) => choice.option_id));

  for (const data of [loadGeneratedData(), loadShadowData()]) {
    assert.deepEqual(plain(data.rules.filter((rule) => wheelOptionIds.has(rule.source_id) || wheelOptionIds.has(rule.target_id))), []);
    assert.deepEqual(plain(data.priceRules.filter((rule) => wheelOptionIds.has(rule.condition_option_id) || wheelOptionIds.has(rule.target_option_id))), []);
    assert.deepEqual(plain(data.exclusiveGroups.filter((group) => group.option_ids.some((optionId) => wheelOptionIds.has(optionId)))), []);
    assert.deepEqual(plain(data.ruleGroups.filter((group) =>
      wheelOptionIds.has(group.source_id) || group.target_ids.some((optionId) => wheelOptionIds.has(optionId))
    )), []);
  }
});

test("shadow overlay preserves QEB canonical projection parity", () => {
  assert.deepEqual(plain(normalizeQebChoices(loadShadowData())), plain(normalizeQebChoices(loadGeneratedData())));
});
