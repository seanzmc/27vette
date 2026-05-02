import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import test from "node:test";

const PYTHON = process.env.PYTHON || ".venv/bin/python";
const INSPECT_SCRIPT = "scripts/inspect_order_guide_export.py";
const EXTRACT_SCRIPT = "scripts/extract_order_guide_staging.py";

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

function readCsv(filePath) {
  return parseCsv(fs.readFileSync(filePath, "utf8"));
}

function makeFixture(workbookPath) {
  execFileSync(
    PYTHON,
    [
      "-c",
      `
from openpyxl import Workbook
from pathlib import Path
wb = Workbook()
wb.remove(wb.active)

def matrix_sheet(name):
    ws = wb.create_sheet(name)
    ws.append(["Stingray", "", "", "", ""])
    ws.append(["", "", "S = Standard Equipment  A = Available  -- (dashes) = Not Available  D = ADI Available  ■ = Included in Equipment Group  □ = Included in Equipment Group but upgradeable", "", ""])
    ws.append(["Orderable RPO Code", "Ref. Only RPO Code", "Description", "Coupe\\n1YC07\\n1LT", "Convertible\\n1YC67\\n2LT"])
    ws.append(["AAA", "", "Example option requires (BBB) package", "A1", "--"])
    ws.append(["", "CCC", "Reference row", "S", "S"])
    ws.append(["", "", "", "", ""])

for name in ["Standard Equipment 1", "Interior 1", "Exterior 1", "Mechanical 1"]:
    matrix_sheet(name)

eg = wb.create_sheet("Equipment Groups 1")
eg.append(["Stingray", "", "", "", ""])
eg.append(["", "", "S = Standard Equipment  ■ = Included in Equipment Group", "", ""])
eg.append(["Orderable RPO Code", "Ref. Only RPO Code", "Description", "Coupe\\n1YC07\\n1LT", "Convertible\\n1YC67\\n2LT"])
eg.append(["Equipment Groups", "", "", "", ""])
eg.append(["", "DDD", "Derived feature unmatched to primary sheets", "■", "--"])

ct = wb.create_sheet("Color and Trim 1")
ct.append(["Recommended", "", "", "", "", ""])
ct.append(["A = Available  -- (dashes) = Not Available", "", "", "", "", ""])
ct.append(["", "", "", "", "Interior Colors", ""])
ct.append(["Decor Level", "Seat Type", "Seat Code", "Seat Trim", "Jet Black", "Sky Cool Gray1"])
ct.append(["1LT, 1LZ", "GT1 buckets", "AQ9", "Mulan leather seating surfaces", "HTA", "--"])

price = wb.create_sheet("Price Schedule")
price.append(["2027 CHEVROLET CORVETTE", "", "", "", ""])
price.append(["2027 MODEL YEAR VEHICLE PRICE SCHEDULE", "", "", "", ""])
price.append(["", "Model", "Model Description", "List", "MSRP(c)"])
price.append(["", "1YC07", "Stingray Coupe 1LT", "70000", "72000"])

unknown = wb.create_sheet("Loose Notes")
unknown.append(["Freeform note"])
unknown.append(["When ordered with (EEE), review manually"])

Path(${JSON.stringify(workbookPath)}).parent.mkdir(parents=True, exist_ok=True)
wb.save(${JSON.stringify(workbookPath)})
`,
    ],
    { cwd: process.cwd(), encoding: "utf8" },
  );
}

test("order guide importer scaffold profiles and extracts staging evidence without canonical output", () => {
  const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), "order-guide-import-"));
  const source = path.join(tmpDir, "fixture.xlsx");
  const profilePath = path.join(tmpDir, "source_profile.json");
  const stagingDir = path.join(tmpDir, "staging");
  const stagingDirSecondRun = path.join(tmpDir, "staging-second");
  makeFixture(source);

  execFileSync(PYTHON, [INSPECT_SCRIPT, "--source", source, "--out", profilePath], {
    cwd: process.cwd(),
    encoding: "utf8",
  });
  execFileSync(PYTHON, [EXTRACT_SCRIPT, "--source", source, "--out", stagingDir], {
    cwd: process.cwd(),
    encoding: "utf8",
  });
  execFileSync(PYTHON, [EXTRACT_SCRIPT, "--source", source, "--out", stagingDirSecondRun], {
    cwd: process.cwd(),
    encoding: "utf8",
  });

  const profile = JSON.parse(fs.readFileSync(profilePath, "utf8"));
  assert.equal(profile.sheets.find((sheet) => sheet.sheet_name === "Equipment Groups 1").sheet_role, "derived_equipment_summary");
  assert.equal(profile.sheets.find((sheet) => sheet.sheet_name === "Color and Trim 1").sheet_role, "model_global_matrix");
  assert.equal(profile.sheets.find((sheet) => sheet.sheet_name === "Color and Trim 1").model_group_index, "");
  assert.equal(profile.sheets.find((sheet) => sheet.sheet_name === "Standard Equipment 1").scope_type, "variant_scoped");

  for (const fileName of [
    "staging_sheets.csv",
    "staging_variants.csv",
    "staging_variant_matrix_rows.csv",
    "staging_color_trim_rows.csv",
    "staging_equipment_group_rows.csv",
    "staging_price_rows.csv",
    "staging_status_symbols.csv",
    "staging_rule_phrase_candidates.csv",
    "staging_unresolved_rows.csv",
    "staging_ignored_rows.csv",
    "import_report.json",
  ]) {
    assert.ok(fs.existsSync(path.join(stagingDir, fileName)), `${fileName} should exist`);
  }

  const sheets = readCsv(path.join(stagingDir, "staging_sheets.csv"));
  assert.equal(sheets.find((row) => row.sheet_name === "Equipment Groups 1").creates_canonical_candidates, "false");
  assert.equal(sheets.find((row) => row.sheet_name === "Color and Trim 1").scope_type, "model_global");
  assert.equal(sheets.find((row) => row.sheet_name === "Standard Equipment 1").scope_type, "variant_scoped");

  const matrixRows = readCsv(path.join(stagingDir, "staging_variant_matrix_rows.csv"));
  assert.equal(matrixRows.some((row) => row.source_sheet === "Standard Equipment 1" && row.raw_status === "A1" && row.status_symbol === "A" && row.footnote_refs === "1"), true);
  assert.equal(matrixRows.some((row) => row.source_sheet === "Equipment Groups 1"), false);
  assert.equal(matrixRows.some((row) => row.source_sheet === "Color and Trim 1"), false);

  const colorTrimRows = readCsv(path.join(stagingDir, "staging_color_trim_rows.csv"));
  assert.equal(colorTrimRows[0].scope_type, "model_global");
  assert.equal(colorTrimRows[0].interior_code, "HTA");

  const equipmentGroupRows = readCsv(path.join(stagingDir, "staging_equipment_group_rows.csv"));
  assert.equal(equipmentGroupRows[0].match_status, "unmatched_primary_review");

  const priceRows = readCsv(path.join(stagingDir, "staging_price_rows.csv"));
  assert.match(priceRows[0].notes, /staging evidence only/);

  const ruleCandidates = readCsv(path.join(stagingDir, "staging_rule_phrase_candidates.csv"));
  assert.equal(ruleCandidates.some((row) => row.phrase_type === "requires" && row.extracted_rpos === "BBB"), true);
  assert.equal(ruleCandidates.some((row) => row.source_sheet === "Loose Notes" && row.extracted_rpos === "EEE"), true);

  const unresolvedRows = readCsv(path.join(stagingDir, "staging_unresolved_rows.csv"));
  assert.equal(unresolvedRows.some((row) => row.source_sheet === "Loose Notes" && row.reason === "ignored_or_unknown_sheet_with_content"), true);

  const ignoredRows = readCsv(path.join(stagingDir, "staging_ignored_rows.csv"));
  assert.equal(ignoredRows.some((row) => row.reason === "blank_row"), true);

  assert.equal(fs.existsSync(path.join(stagingDir, "proposed")), false);
  assert.equal(fs.existsSync(path.join(stagingDir, "catalog", "selectables.csv")), false);
  assert.equal(fs.existsSync(path.join(stagingDir, "logic", "dependency_rules.csv")), false);
  assert.equal(fs.existsSync(path.join(stagingDir, "pricing", "base_prices.csv")), false);

  for (const fileName of [
    "staging_sheets.csv",
    "staging_variants.csv",
    "staging_variant_matrix_rows.csv",
    "staging_color_trim_rows.csv",
    "staging_equipment_group_rows.csv",
    "staging_price_rows.csv",
    "staging_status_symbols.csv",
    "staging_rule_phrase_candidates.csv",
    "staging_unresolved_rows.csv",
    "staging_ignored_rows.csv",
    "import_report.json",
  ]) {
    assert.equal(
      fs.readFileSync(path.join(stagingDir, fileName), "utf8"),
      fs.readFileSync(path.join(stagingDirSecondRun, fileName), "utf8"),
      `${fileName} should be deterministic`,
    );
  }
});
