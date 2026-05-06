import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import fs from "node:fs";
import test from "node:test";
import vm from "node:vm";

const PYTHON = ".venv/bin/python";
const SCRIPT = "scripts/stingray_csv_first_slice.py";
const OWNERSHIP_MANIFEST = "data/stingray/validation/projected_slice_ownership.csv";
const PAINT_RPOS = ["G8G", "GBA", "GKA", "GBK", "GTR", "GEC", "GPH", "G4Z", "G26", "GKZ"];
const PAINT_COMPATIBILITY_RULES = [
  ["D84", "GBA"],
  ["D86", "GBA"],
  ["DPB", "GTR"],
  ["DPC", "GBK"],
  ["DPG", "G26"],
  ["DPL", "GKZ"],
  ["DPL", "GPH"],
  ["DSY", "G26"],
  ["DSZ", "GKZ"],
  ["DSZ", "GPH"],
  ["DT0", "GBK"],
  ["DUE", "GTR"],
  ["DUK", "GKZ"],
  ["DUK", "GPH"],
  ["DUW", "GTR"],
  ["DZU", "GBK"],
  ["DZX", "GKZ"],
  ["DZX", "GPH"],
  ["EFY", "GBA"],
  ["ZYC", "GBA"],
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

function loadProduction() {
  const context = { window: {} };
  vm.runInNewContext(fs.readFileSync("form-app/data.js", "utf8"), context);
  return context.window.STINGRAY_FORM_DATA;
}

function emitCsvLegacyFragment() {
  const output = execFileSync(PYTHON, [SCRIPT, "--emit-legacy-fragment"], {
    cwd: process.cwd(),
    encoding: "utf8",
    maxBuffer: 8 * 1024 * 1024,
  });
  return JSON.parse(output);
}

function normalizePaintChoices(rows) {
  return rows
    .filter((choice) => choice.section_id === "sec_pain_001")
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

function activeManifestRows() {
  return parseCsv(fs.readFileSync(OWNERSHIP_MANIFEST, "utf8")).filter((row) => row.active === "true");
}

function manifestHas(expected, rows = activeManifestRows()) {
  return rows.some((row) => Object.entries(expected).every(([key, value]) => row[key] === value));
}

function plain(value) {
  return JSON.parse(JSON.stringify(value));
}

test("CSV Paint section emits all production sec_pain_001 choices", () => {
  const production = loadProduction();
  const projected = emitCsvLegacyFragment();
  const productionPaint = normalizePaintChoices(production.choices);
  const projectedPaint = normalizePaintChoices(projected.choices);

  assert.deepEqual(projected.validation_errors, []);
  assert.equal(productionPaint.length, 60);
  assert.equal(projectedPaint.length, 60);
  assert.deepEqual(plain(projectedPaint), plain(productionPaint));
  assert.deepEqual(
    projectedPaint.filter((choice) => choice.variant_id === "1lt_c07").sort((a, b) => a.display_order - b.display_order).map((choice) => choice.rpo),
    PAINT_RPOS
  );
  assert.deepEqual([...new Set(projectedPaint.map((choice) => choice.section_id))], ["sec_pain_001"]);
  assert.deepEqual([...new Set(projectedPaint.map((choice) => choice.choice_mode))], ["single"]);
  assert.deepEqual([...new Set(projectedPaint.map((choice) => choice.selection_mode))], ["single_select_req"]);
});

test("Paint projection owns all Paint choices and retires only the stale GBA guard", () => {
  const rows = parseCsv(fs.readFileSync(OWNERSHIP_MANIFEST, "utf8"));
  const activeRows = rows.filter((row) => row.active === "true");

  for (const rpo of PAINT_RPOS) {
    assert.equal(manifestHas({ record_type: "selectable", rpo, ownership: "projected_owned" }, activeRows), true);
  }

  assert.equal(manifestHas({ record_type: "guardedOption", rpo: "GBA", ownership: "production_guarded" }, activeRows), false);
  assert.ok(
    rows.find((row) => row.record_type === "guardedOption" && row.rpo === "GBA" && row.ownership === "production_guarded" && row.active === "false")
  );
});

test("Paint projection does not migrate preserved paint compatibility rules", () => {
  const rules = parseCsv(fs.readFileSync("data/stingray/logic/dependency_rules.csv", "utf8"));
  const conditionSets = parseCsv(fs.readFileSync("data/stingray/logic/condition_sets.csv", "utf8"));
  const conditionTerms = parseCsv(fs.readFileSync("data/stingray/logic/condition_terms.csv", "utf8"));

  assert.equal(rules.length, 111);
  assert.equal(conditionSets.length, 45);
  assert.equal(conditionTerms.length, 47);
  assert.equal(conditionSets.some((row) => row.condition_set_id === "cs_selected_gba"), false);
  assert.equal(conditionTerms.some((row) => PAINT_RPOS.some((rpo) => row.left_ref === `opt_${rpo.toLowerCase()}_001`)), false);

  for (const [sourceRpo, targetRpo] of PAINT_COMPATIBILITY_RULES) {
    assert.equal(
      manifestHas({ record_type: "rule", source_rpo: sourceRpo, target_rpo: targetRpo, ownership: "preserved_cross_boundary" }),
      true,
      `${sourceRpo} -> ${targetRpo} should remain preserved`
    );
  }
});
