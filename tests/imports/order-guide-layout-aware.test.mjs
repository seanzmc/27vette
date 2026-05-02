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

def matrix_sheet(name, known=True):
    ws = wb.create_sheet(name)
    ws.append(["Stingray", "", "", "", ""])
    ws.append(["", "", "S = Standard Equipment  A = Available  -- (dashes) = Not Available", "", ""])
    if known:
        ws.append(["Orderable RPO Code", "Ref. Only RPO Code", "Description", "Coupe\\n1YC07\\n1LT", "Convertible\\n1YC67\\n2LT", "Mystery Coupe\\n9ZZ07\\n1LT"])
    else:
        ws.append(["Orderable RPO Code", "Ref. Only RPO Code", "Description", "Mystery Coupe\\n9ZZ07\\n1LT"])
    ws.append(["A12", "", "Description ending 2027 with HU76 outside RPO context\\n1. Keep this disclosure with the description.", "A1", "A/D2", "S2"] if known else ["A12", "", "Description ending 2027", "A1"])
    ws.append(["", "N27", "No orderable RPO row is allowed", "A/D", "S1", "--"] if known else ["", "N27", "No orderable RPO row is allowed", "A/D"])

matrix_sheet("Standard Equipment 1", True)

eg = wb.create_sheet("Equipment Groups 1")
eg.append(["Stingray", "", "", "", ""])
eg.append(["", "", "S = Standard Equipment  ■ = Included in Equipment Group", "", ""])
eg.append(["Orderable RPO Code", "Ref. Only RPO Code", "Description", "Coupe\\n1YC07\\n1LT", "Convertible\\n1YC67\\n2LT", "Mystery Coupe\\n9ZZ07\\n1LT"])
eg.append(["Equipment Groups", "", "", "", ""])
eg.append(["", "DDD", "Derived feature", "■", "--"])

ct = wb.create_sheet("Color and Trim 1")
ct.append(["Recommended", "", "", "", "", "", ""])
ct.append(["A = Available  -- (dashes) = Not Available", "", "", "", "", "", ""])
ct.append(["", "", "", "", "Interior Colors", "", ""])
ct.append(["Decor Level", "Seat Type", "Seat Code", "Seat Trim", "Jet Black", "Sky Cool Gray1", "Adrenaline Red", "Natural"])
ct.append(["1LT, 1LZ", "GT1 buckets", "AQ9", "Mulan leather seating surfaces", "HTA", "HUP", "HU76", "HUQ"])
ct.append(["1LT, 1LZ", "Competition buckets", "AE4", "Performance Textile5", "HTJ", "--", "--", "--"])
ct.append(["", "", "", "", "Interior Colors", "", ""])
ct.append(["Exterior Solid Paint", "", "Color Code", "Touch-Up Paint Number", "Jet Black / en-us", "Sky Cool Gray1\\nen-us", "Adrenaline Red / en-us", "Natural / en-us"])
ct.append(["Sebring Orange Tintcoat9", "", "G26", "WA-418C", "A1", "A", "--", "A/D"])
ct.append(["Black", "", "GBA", "WA-8555", "A", "A/D2", "A", "A"])
ct.append([""])
ct.append(["• NOTE: Requires option code (D30) Color Combination Override. 1. Requires (N26) sueded microfiber-wrapped steering wheel.", "", "", "", "", "", ""])

unknown = wb.create_sheet("Loose Notes")
unknown.append(["Meaningful unsupported note"])
unknown.append(["When ordered with (EEE), review manually"])
unknown.append([""])

Path(${JSON.stringify(workbookPath)}).parent.mkdir(parents=True, exist_ok=True)
wb.save(${JSON.stringify(workbookPath)})
`,
    ],
    { cwd: process.cwd(), encoding: "utf8" },
  );
}

test("layout-aware importer preserves Color and Trim field context and model-key evidence", () => {
  const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), "order-guide-layout-"));
  const source = path.join(tmpDir, "fixture.xlsx");
  const profilePath = path.join(tmpDir, "source_profile.json");
  const stagingDir = path.join(tmpDir, "staging");
  makeFixture(source);

  execFileSync(PYTHON, [INSPECT_SCRIPT, "--source", source, "--out", profilePath], {
    cwd: process.cwd(),
    encoding: "utf8",
  });
  execFileSync(PYTHON, [EXTRACT_SCRIPT, "--source", source, "--out", stagingDir], {
    cwd: process.cwd(),
    encoding: "utf8",
  });

  for (const fileName of [
    "staging_sheet_sections.csv",
    "staging_color_trim_interior_rows.csv",
    "staging_color_trim_compatibility_rows.csv",
    "staging_color_trim_disclosures.csv",
  ]) {
    assert.ok(fs.existsSync(path.join(stagingDir, fileName)), `${fileName} should exist`);
  }

  const sections = readCsv(path.join(stagingDir, "staging_sheet_sections.csv"));
  assert.equal(sections.some((row) => row.source_sheet === "Color and Trim 1" && row.section_role === "color_trim_interior_matrix"), true);
  assert.equal(sections.some((row) => row.source_sheet === "Color and Trim 1" && row.section_role === "color_trim_compatibility_matrix"), true);
  assert.equal(sections.some((row) => row.source_sheet === "Color and Trim 1" && row.section_role === "color_trim_disclosure"), true);

  const interiorRows = readCsv(path.join(stagingDir, "staging_color_trim_interior_rows.csv"));
  const hta = interiorRows.find((row) => row.interior_rpo_raw === "HTA");
  assert.ok(hta, "HTA should be preserved as an interior RPO");
  assert.equal(hta.interior_rpo, "HTA");
  assert.equal(hta.footnote_refs, "");
  assert.equal(hta.scope_type, "model_global");
  assert.equal(
    interiorRows.some((row) => row.interior_rpo_raw === "HTA" && row.raw_status === "HTA" && row.status_symbol === "H" && row.footnote_refs === "TA"),
    false,
    "HTA must not be staged as status H plus footnote TA",
  );
  assert.ok(interiorRows.find((row) => row.interior_rpo_raw === "HUP"), "HUP should be preserved as an interior RPO");
  assert.ok(interiorRows.find((row) => row.interior_rpo_raw === "HUQ"), "HUQ should be preserved as an interior RPO");

  const hu76 = interiorRows.find((row) => row.interior_rpo_raw === "HU76");
  assert.equal(hu76.interior_rpo, "HU7");
  assert.equal(hu76.footnote_refs, "6");
  assert.equal(hu76.footnote_scope, "interior_rpo");
  assert.match(hu76.confidence, /medium|needs_review|high/);

  const performanceTextile = interiorRows.find((row) => row.seat_trim_raw === "Performance Textile5" && row.interior_rpo_raw === "HTJ");
  assert.equal(performanceTextile.seat_trim, "Performance Textile");
  assert.equal(performanceTextile.footnote_refs, "5");
  assert.equal(performanceTextile.footnote_scope, "seat_trim");

  const compatibilityRows = readCsv(path.join(stagingDir, "staging_color_trim_compatibility_rows.csv"));
  const sebringJetBlack = compatibilityRows.find((row) => row.exterior_color_rpo === "G26" && row.interior_rpo_raw === "Jet Black / en-us");
  assert.equal(sebringJetBlack.raw_status, "A1");
  assert.equal(sebringJetBlack.status_symbol, "A");
  assert.equal(sebringJetBlack.footnote_refs, "1");
  assert.equal(sebringJetBlack.scope_type, "model_global");
  assert.equal(sebringJetBlack.model_key, "");
  assert.equal(sebringJetBlack.model_key_confidence, "needs_review");

  const sebringSkyCoolGray = compatibilityRows.find((row) => row.exterior_color_rpo === "G26" && row.interior_rpo_raw === "Sky Cool Gray1\nen-us");
  assert.equal(sebringSkyCoolGray.interior_rpo, "Sky Cool Gray");
  assert.equal(sebringSkyCoolGray.interior_footnote_refs, "1");
  assert.equal(sebringSkyCoolGray.interior_footnote_scope, "interior_color_header");

  const blackSkyCoolGray = compatibilityRows.find((row) => row.exterior_color_rpo === "GBA" && row.interior_rpo_raw === "Sky Cool Gray1\nen-us");
  assert.equal(blackSkyCoolGray.raw_status, "A/D2");
  assert.equal(blackSkyCoolGray.status_symbol, "A/D");
  assert.equal(blackSkyCoolGray.canonical_status, "available");
  assert.equal(blackSkyCoolGray.footnote_refs, "2");

  const sebringNatural = compatibilityRows.find((row) => row.exterior_color_rpo === "G26" && row.interior_rpo_raw === "Natural / en-us");
  assert.equal(sebringNatural.raw_status, "A/D");
  assert.equal(sebringNatural.status_symbol, "A/D");
  assert.equal(sebringNatural.canonical_status, "available");
  assert.equal(sebringNatural.footnote_refs, "");

  const variantRows = readCsv(path.join(stagingDir, "staging_variant_matrix_rows.csv"));
  const knownVariant = variantRows.find((row) => row.body_code === "1YC07");
  assert.equal(knownVariant.model_key, "stingray");
  assert.equal(knownVariant.raw_status, "A1");
  assert.equal(knownVariant.status_symbol, "A");
  assert.equal(knownVariant.footnote_refs, "1");
  assert.equal(knownVariant.orderable_rpo, "A12");
  assert.match(knownVariant.description, /Description ending 2027 with HU76 outside RPO context/);
  assert.match(knownVariant.source_detail_raw, /1\. Keep this disclosure with the description/);

  const adVariant = variantRows.find((row) => row.body_code === "1YC67" && row.orderable_rpo === "A12");
  assert.equal(adVariant.model_key, "stingray");
  assert.equal(adVariant.raw_status, "A/D2");
  assert.equal(adVariant.status_symbol, "A/D");
  assert.equal(adVariant.canonical_status, "available");
  assert.equal(adVariant.footnote_refs, "2");

  const noOrderableRpo = variantRows.find((row) => row.ref_rpo === "N27" && row.body_code === "1YC07");
  assert.equal(noOrderableRpo.orderable_rpo, "");
  assert.equal(noOrderableRpo.ref_rpo, "N27");
  assert.equal(noOrderableRpo.raw_status, "A/D");
  assert.equal(noOrderableRpo.canonical_status, "available");

  const unknownVariant = variantRows.find((row) => row.body_code === "9ZZ07");
  assert.equal(unknownVariant.model_key, "");
  assert.equal(unknownVariant.model_key_confidence, "needs_review");

  const variants = readCsv(path.join(stagingDir, "staging_variants.csv"));
  assert.equal(variants.find((row) => row.body_code === "1YC07").model_key, "stingray");
  assert.equal(variants.find((row) => row.body_code === "9ZZ07").model_key, "");
  assert.equal(variants.find((row) => row.body_code === "9ZZ07").confidence, "needs_review");

  const equipmentGroupRows = readCsv(path.join(stagingDir, "staging_equipment_group_rows.csv"));
  assert.equal(equipmentGroupRows[0].row_kind, "derived_cross_check");
  assert.equal(equipmentGroupRows[0].model_key, "stingray");
  assert.equal(equipmentGroupRows[0].model_key_confidence, "needs_review");
  assert.equal(readCsv(path.join(stagingDir, "staging_variant_matrix_rows.csv")).some((row) => row.source_sheet === "Equipment Groups 1"), false);

  const disclosures = readCsv(path.join(stagingDir, "staging_color_trim_disclosures.csv"));
  assert.equal(disclosures.some((row) => row.extracted_rpos.includes("D30") && row.phrase_type === "requires"), true);

  const report = JSON.parse(fs.readFileSync(path.join(stagingDir, "import_report.json"), "utf8"));
  assert.equal(report.section_role_counts.color_trim_interior_matrix, 1);
  assert.equal(report.section_role_counts.color_trim_compatibility_matrix, 1);
  assert.ok(report.status_parse_rejections.HTA >= 1);
  assert.ok(report.footnote_scope_counts.seat_trim >= 1);
  assert.ok(report.ad_statuses_parsed >= 2);
  assert.ok(report.color_trim_locale_suffix_cleanups >= 1);
  assert.ok(report.color_trim_header_footnotes_after_locale_cleanup >= 1);
  assert.ok(report.ignored_rows_by_reason.blank_row >= 1);
  assert.ok(report.unresolved_rows_by_reason.ignored_or_unknown_sheet_with_content >= 1);

  const unresolvedRows = readCsv(path.join(stagingDir, "staging_unresolved_rows.csv"));
  assert.equal(unresolvedRows.some((row) => row.source_sheet === "Loose Notes" && row.reason === "ignored_or_unknown_sheet_with_content"), true);

  const ignoredRows = readCsv(path.join(stagingDir, "staging_ignored_rows.csv"));
  assert.equal(ignoredRows.some((row) => row.reason === "blank_row"), true);

  const profile = JSON.parse(fs.readFileSync(profilePath, "utf8"));
  assert.ok(profile.detected.sheet_section_role_counts.color_trim_interior_matrix >= 1);
  assert.equal(profile.detected.model_key_confidence_counts.needs_review >= 1, true);
});
