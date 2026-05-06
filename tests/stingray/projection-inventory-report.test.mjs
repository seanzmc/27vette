import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import test from "node:test";

const PYTHON = ".venv/bin/python";
const SCRIPT = "scripts/stingray_projection_inventory_report.py";
const ARTIFACTS = [
  "production_selectable_inventory.csv",
  "production_relationship_inventory.csv",
  "csv_projection_matrix.csv",
  "projection_summary.json",
];
const SOURCE_CSVS = [
  "data/stingray/catalog/selectables.csv",
  "data/stingray/ui/selectable_display.csv",
  "data/stingray/pricing/base_prices.csv",
  "data/stingray/logic/dependency_rules.csv",
  "data/stingray/logic/condition_sets.csv",
  "data/stingray/logic/condition_terms.csv",
  "data/stingray/logic/auto_adds.csv",
  "data/stingray/pricing/price_rules.csv",
  "data/stingray/validation/projected_slice_ownership.csv",
];

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

function runReport() {
  const outDir = fs.mkdtempSync(path.join(os.tmpdir(), "stingray-projection-inventory-"));
  const before = Object.fromEntries(SOURCE_CSVS.map((file) => [file, fs.readFileSync(file, "utf8")]));
  const result = spawnSync(PYTHON, [SCRIPT, "--out-dir", outDir], {
    cwd: process.cwd(),
    encoding: "utf8",
    maxBuffer: 16 * 1024 * 1024,
  });
  const after = Object.fromEntries(SOURCE_CSVS.map((file) => [file, fs.readFileSync(file, "utf8")]));
  return { outDir, result, before, after };
}

test("projection inventory report emits all artifacts and current summary counts", () => {
  const { outDir, result } = runReport();

  assert.equal(result.status, 0, result.stderr);
  for (const artifact of ARTIFACTS) {
    assert.equal(fs.existsSync(path.join(outDir, artifact)), true, `${artifact} should be emitted`);
  }

  const summary = JSON.parse(fs.readFileSync(path.join(outDir, "projection_summary.json"), "utf8"));
  assert.equal(summary.schema_version, 1);
  assert.equal(summary.production_selectables.customer_facing_count, 153);
  assert.equal(summary.production_selectables.csv_projected_customer_facing_count, 106);
  assert.equal(summary.production_selectables.customer_facing_missing_count, 47);
  assert.equal(summary.production_relationships.rules.total, 238);
  assert.deepEqual(summary.production_relationships.rules.by_rule_type, { excludes: 158, includes: 64, requires: 16 });
  assert.deepEqual(summary.production_relationships.rules.by_runtime_action, { active: 235, replace: 3 });
  assert.deepEqual(summary.production_relationships.rules.by_auto_add, { False: 174, True: 64 });
  assert.equal(summary.production_relationships.price_rules.total, 43);
  assert.equal(summary.production_relationships.exclusive_groups.total, 6);
  assert.equal(summary.production_relationships.rule_groups.total, 2);
});

test("projection inventory report writes required fields and does not mutate source CSVs", () => {
  const { outDir, result, before, after } = runReport();

  assert.equal(result.status, 0, result.stderr);
  assert.deepEqual(after, before);

  const selectableRows = parseCsv(fs.readFileSync(path.join(outDir, "production_selectable_inventory.csv"), "utf8"));
  const relationshipRows = parseCsv(fs.readFileSync(path.join(outDir, "production_relationship_inventory.csv"), "utf8"));
  const matrixRows = parseCsv(fs.readFileSync(path.join(outDir, "csv_projection_matrix.csv"), "utf8"));

  assert.equal(selectableRows.length, summaryCount(outDir, "customer_facing_count"));
  assert.ok(selectableRows.find((row) => row.option_id === "opt_z51_001" && row.projection_status === "customer-facing projected"));
  assert.ok(selectableRows.find((row) => row.option_id === "opt_zyc_001" && row.projection_status === "customer-facing missing"));

  for (const field of [
    "option_id",
    "rpo",
    "label",
    "description",
    "section_id",
    "section_name",
    "category_id",
    "category_name",
    "step_key",
    "choice_mode",
    "selection_mode",
    "display_order",
    "base_price",
    "variant_count",
    "available_variant_ids",
    "statuses",
    "is_customer_facing",
    "is_csv_projected",
    "projection_status",
    "notes",
  ]) {
    assert.equal(Object.hasOwn(selectableRows[0], field), true, `selectable field ${field}`);
  }

  for (const field of [
    "relationship_key",
    "surface",
    "production_id",
    "relationship_type",
    "source_id",
    "source_rpo",
    "source_label",
    "source_section",
    "source_mode",
    "target_id",
    "target_rpo",
    "target_label",
    "target_section",
    "target_mode",
    "runtime_action",
    "auto_add",
    "message",
    "price_rule_type",
    "price_value",
    "group_id",
    "group_type",
    "member_order",
    "endpoint_classification",
  ]) {
    assert.equal(Object.hasOwn(relationshipRows[0], field), true, `relationship field ${field}`);
  }

  for (const field of [
    "relationship_key",
    "production_surface",
    "csv_surface",
    "production_status",
    "csv_status",
    "ownership_status",
    "source_projection_status",
    "target_projection_status",
    "representable_now",
    "requires_new_selectable",
    "requires_support_change",
    "recommended_lane",
    "hard_stop_reason",
    "next_action",
  ]) {
    assert.equal(Object.hasOwn(matrixRows[0], field), true, `matrix field ${field}`);
  }

  assert.ok(matrixRows.find((row) => row.csv_status === "CSV-owned relationship"));
  assert.ok(matrixRows.find((row) => row.ownership_status === "active preserved relationship"));
  assert.ok(matrixRows.find((row) => row.csv_status === "outside projected boundary"));
});

function summaryCount(outDir, field) {
  const summary = JSON.parse(fs.readFileSync(path.join(outDir, "projection_summary.json"), "utf8"));
  return summary.production_selectables[field];
}
