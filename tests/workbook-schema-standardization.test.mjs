import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import fs from "node:fs";
import test from "node:test";

function pythonJson(source) {
  const output = execFileSync(".venv/bin/python", ["-c", source], { encoding: "utf8" });
  return JSON.parse(output);
}

function workbookSnapshot() {
  return pythonJson(`
import json
from openpyxl import load_workbook
wb = load_workbook('stingray_master.xlsx', read_only=True, data_only=True)

def headers(sheet):
    ws = wb[sheet]
    return [ws.cell(1, col).value for col in range(1, ws.max_column + 1) if ws.cell(1, col).value]

def column_values(sheet, column):
    ws = wb[sheet]
    header_row = [ws.cell(1, col).value for col in range(1, ws.max_column + 1)]
    idx = header_row.index(column) + 1
    return [ws.cell(row, idx).value for row in range(2, ws.max_row + 1) if ws.cell(row, idx).value is not None]

def records(sheet):
    ws = wb[sheet]
    header_row = [ws.cell(1, col).value for col in range(1, ws.max_column + 1)]
    rows = []
    for raw in ws.iter_rows(min_row=2, values_only=True):
        record = {header: value for header, value in zip(header_row, raw) if header and value is not None}
        if record:
            rows.append(record)
    return rows

payload = {
    'sheetnames': wb.sheetnames,
    'lt_headers': headers('lt_interiors'),
    'lz_headers': headers('LZ_Interiors'),
    'stingray_rpos': column_values('stingray_options', 'rpo'),
    'grand_sport_rpos': column_values('grandSport_options', 'rpo'),
    'price_ref_prices': column_values('PriceRef', 'Price'),
    'lt_interior_prices': column_values('lt_interiors', 'Price'),
    'lz_interior_prices': column_values('LZ_Interiors', 'Price'),
    'grand_sport_selectable': column_values('grandSport_options', 'selectable'),
    'grand_sport_variant_active': column_values('grandSport_variant_overrides', 'active'),
    'grand_sport_variant_selectable': column_values('grandSport_variant_overrides', 'selectable'),
    'rule_mapping_rows': records('rule_mapping'),
    'grand_sport_rule_mapping_rows': records('grandSport_rule_mapping'),
}
print(json.dumps(payload))
`);
}

function liveRegistry() {
  const source = fs.readFileSync("form-app/data.js", "utf8");
  const json = source
    .split("window.CORVETTE_FORM_DATA = ", 2)[1]
    .split(";\nwindow.STINGRAY_FORM_DATA", 1)[0];
  return JSON.parse(json);
}

const snapshot = workbookSnapshot();

test("schema validation CLI accepts the standardized workbook and live app contract", () => {
  const output = execFileSync(".venv/bin/python", ["scripts/validate_workbook_schema.py", "stingray_master.xlsx"], {
    encoding: "utf8",
  });
  const result = JSON.parse(output);
  assert.equal(result.status, "valid");
  assert.equal(result.error_count, 0);
  assert.deepEqual(result.issues, []);
});

test("workbook primitive cells use canonical raw Excel types", () => {
  const numericLookingRpos = new Set(["379", "719"]);
  assert.equal(snapshot.stingray_rpos.filter((value) => numericLookingRpos.has(value)).length >= 3, true);
  assert.equal(snapshot.grand_sport_rpos.filter((value) => numericLookingRpos.has(value)).length >= 3, true);
  assert.equal(snapshot.stingray_rpos.every((value) => typeof value === "string"), true);
  assert.equal(snapshot.grand_sport_rpos.every((value) => typeof value === "string"), true);

  assert.equal(snapshot.grand_sport_selectable.every((value) => typeof value === "boolean"), true);
  assert.equal(snapshot.grand_sport_variant_active.every((value) => typeof value === "boolean"), true);
  assert.equal(snapshot.grand_sport_variant_selectable.every((value) => typeof value === "boolean"), true);

  assert.equal(snapshot.price_ref_prices.every((value) => typeof value === "number"), true);
  assert.equal(snapshot.lt_interior_prices.every((value) => typeof value === "number"), true);
  assert.equal(snapshot.lz_interior_prices.every((value) => typeof value === "number"), true);
});

test("LZ_Interiors is schema-compatible but not read by Stingray generation", () => {
  assert.deepEqual(snapshot.lz_headers, snapshot.lt_headers);
  const registry = liveRegistry();
  const stingrayInteriors = registry.models.stingray.data.interiors;
  assert.equal(stingrayInteriors.some((interior) => interior.source_sheet === "LZ_Interiors"), false);
  assert.equal(stingrayInteriors.some((interior) => interior.interior_id === "3LT_AH2_EL9"), false);
});

test("rule lifecycle metadata keeps retained source rows auditable", () => {
  for (const [sheetName, rows] of [
    ["rule_mapping", snapshot.rule_mapping_rows],
    ["grandSport_rule_mapping", snapshot.grand_sport_rule_mapping_rows],
  ]) {
    assert.ok(rows.length > 0, `${sheetName} should have rule rows`);
    for (const row of rows) {
      assert.ok("normalization_status" in row, `${sheetName}.${row.rule_id} missing normalization_status`);
      if (String(row.generation_action || "").startsWith("omit")) {
        assert.ok(["omitted", "replaced"].includes(row.normalization_status), `${sheetName}.${row.rule_id} bad status`);
        assert.ok(row.normalization_reason, `${sheetName}.${row.rule_id} missing reason`);
      }
    }
  }
});

test("category_master is retired from the active source graph and draft provenance is not live app data", () => {
  assert.equal(snapshot.sheetnames.includes("category_master"), false);
  assert.equal(snapshot.sheetnames.includes("archive_category_master"), true);

  const registry = liveRegistry();
  for (const [modelKey, entry] of Object.entries(registry.models)) {
    assert.equal("draftMetadata" in entry.data, false, `${modelKey} leaked draftMetadata`);
    for (const choice of entry.data.choices) {
      assert.equal("source_option_name" in choice, false, `${modelKey} ${choice.choice_id} leaked source_option_name`);
      assert.equal("source_description" in choice, false, `${modelKey} ${choice.choice_id} leaked source_description`);
      assert.equal("text_cleanup_notes" in choice, false, `${modelKey} ${choice.choice_id} leaked text_cleanup_notes`);
    }
  }
});
