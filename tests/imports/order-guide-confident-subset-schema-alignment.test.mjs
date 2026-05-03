import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import test from "node:test";

const PYTHON = process.env.PYTHON || ".venv/bin/python";
const INSPECT_SCRIPT = "scripts/inspect_order_guide_export.py";
const EXTRACT_SCRIPT = "scripts/extract_order_guide_staging.py";
const STAGING_AUDIT_SCRIPT = "scripts/audit_order_guide_staging.py";
const READINESS_SCRIPT = "scripts/report_order_guide_proposal_readiness.py";
const PROPOSAL_SCRIPT = "scripts/propose_order_guide_primary_matrix.py";
const PROPOSAL_AUDIT_SCRIPT = "scripts/audit_order_guide_proposal.py";
const SUBSET_SCRIPT = "scripts/filter_order_guide_confident_proposal.py";
const ALIGNMENT_SCRIPT = "scripts/report_confident_subset_schema_alignment.py";

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

price = wb.create_sheet("Price Schedule")
price.append(["EFFECTIVE WITH START OF 2027 MODEL YEAR PRODUCTION", "", "", "", "", ""])
price.append(["Base Model Prices", "", "", "", "", ""])
price.append(["", "Model", "Model Description", "List", "Factory", "MSRP(c)"])
price.append(["", "1YC07", "Corvette Stingray Coupe 1LT", "71000", "0", "71000"])

ws = wb.create_sheet("Standard Equipment 1")
ws.append(["Stingray", "", "", "", ""])
ws.append(["", "", "S = Standard Equipment  A = Available  -- (dashes) = Not Available", "", ""])
ws.append(["Orderable RPO Code", "Ref. Only RPO Code", "Description", "Coupe\\n1YC07\\n1LT", "Convertible\\n1YC67\\n2LT"])
ws.append(["AAA", "", "Orderable evidence", "A/D2", "S"])
ws.append(["BBB", "", "Second orderable evidence", "A", "--"])
ws.append(["", "CCC", "Reference-only evidence", "A", "--"])
ws.append(["", "", "No RPO standard evidence", "S1", "S"])
ws.append(["CCC", "", "Same RPO orderable evidence", "A", "A"])

ws2 = wb.create_sheet("Standard Equipment 2")
ws2.append(["Grand Sport", "", "", "", ""])
ws2.append(["", "", "S = Standard Equipment  A = Available  -- (dashes) = Not Available", "", ""])
ws2.append(["Orderable RPO Code", "Ref. Only RPO Code", "Description", "Coupe\\n1YE07\\n1LT", "Convertible\\n1YE67\\n1LT"])
ws2.append(["AAA", "", "Orderable evidence", "A", "S"])

eg = wb.create_sheet("Equipment Groups 1")
eg.append(["Stingray", "", "", ""])
eg.append(["", "", "S = Standard Equipment  ■ = Included in Equipment Group", ""])
eg.append(["Orderable RPO Code", "Ref. Only RPO Code", "Description", "Coupe\\n1YC07\\n1LT"])
eg.append(["", "EG1", "Derived feature", "■"])

ct = wb.create_sheet("Color and Trim 1")
ct.append(["Recommended", "", "", "", "", ""])
ct.append(["A = Available  -- (dashes) = Not Available", "", "", "", "", ""])
ct.append(["", "", "", "", "Interior Colors", ""])
ct.append(["Decor Level", "Seat Type", "Seat Code", "Seat Trim", "Jet Black", "Sky Cool Gray1"])
ct.append(["1LT", "GT1 buckets", "AQ9", "Performance Textile5", "HTA", "HU76"])
ct.append(["", "", "", "", "Interior Colors", ""])
ct.append(["Exterior Solid Paint", "", "Color Code", "Touch-Up Paint Number", "Jet Black / en-us", "Sky Cool Gray1\\nen-us"])
ct.append(["Black", "", "GBA", "WA-8555", "A", "A/D2"])

Path(${JSON.stringify(workbookPath)}).parent.mkdir(parents=True, exist_ok=True)
wb.save(${JSON.stringify(workbookPath)})
`,
    ],
    { cwd: process.cwd(), encoding: "utf8" },
  );
}

function buildSubset(tmpDir) {
  const source = path.join(tmpDir, "fixture.xlsx");
  const profilePath = path.join(tmpDir, "source_profile.json");
  const stagingDir = path.join(tmpDir, "staging");
  const proposalDir = path.join(tmpDir, "proposal");
  const subsetDir = path.join(tmpDir, "subset");
  const auditPath = path.join(stagingDir, "staging_audit_report.json");
  const configDir = path.join(tmpDir, "config");
  const colorTrimScopePath = path.join(configDir, "color_trim_scope.csv");
  const rpoRoleOverlapsPath = path.join(configDir, "rpo_role_overlaps.csv");

  makeFixture(source);
  fs.mkdirSync(configDir, { recursive: true });
  fs.writeFileSync(
    colorTrimScopePath,
    [
      "sheet_name,section_role,guide_family,model_key,scope_type,confidence,review_status,notes",
      "Color and Trim 1,color_trim_interior_matrix,corvette,,model_global,confirmed,accepted_review_only,Accepted review-only fixture row.",
      "Color and Trim 1,color_trim_compatibility_matrix,corvette,,model_global,confirmed,accepted_review_only,Accepted review-only fixture row.",
      "",
    ].join("\n"),
  );
  fs.writeFileSync(
    rpoRoleOverlapsPath,
    [
      "rpo,review_status,classification,canonical_handling,recommended_action,notes",
      "CCC,accepted_expected_overlap,orderable_and_ref_only_expected,keep_separate_evidence,review_orderable_vs_reference_usage_before_proposal,Accepted fixture overlap.",
      "",
    ].join("\n"),
  );

  execFileSync(PYTHON, [INSPECT_SCRIPT, "--source", source, "--out", profilePath], { cwd: process.cwd(), encoding: "utf8" });
  execFileSync(PYTHON, [EXTRACT_SCRIPT, "--source", source, "--out", stagingDir], { cwd: process.cwd(), encoding: "utf8" });
  execFileSync(
    PYTHON,
    [
      STAGING_AUDIT_SCRIPT,
      "--staging",
      stagingDir,
      "--out",
      auditPath,
      "--color-trim-scope",
      colorTrimScopePath,
      "--rpo-role-overlaps",
      rpoRoleOverlapsPath,
    ],
    { cwd: process.cwd(), encoding: "utf8" },
  );
  execFileSync(
    PYTHON,
    [
      READINESS_SCRIPT,
      "--staging",
      stagingDir,
      "--out",
      stagingDir,
      "--color-trim-scope",
      colorTrimScopePath,
      "--rpo-role-overlaps",
      rpoRoleOverlapsPath,
    ],
    { cwd: process.cwd(), encoding: "utf8" },
  );
  execFileSync(PYTHON, [PROPOSAL_SCRIPT, "--staging", stagingDir, "--out", proposalDir], { cwd: process.cwd(), encoding: "utf8" });
  execFileSync(PYTHON, [PROPOSAL_AUDIT_SCRIPT, "--proposal", proposalDir, "--out", proposalDir], { cwd: process.cwd(), encoding: "utf8" });
  execFileSync(PYTHON, [SUBSET_SCRIPT, "--proposal", proposalDir, "--out", subsetDir], { cwd: process.cwd(), encoding: "utf8" });

  return subsetDir;
}

function runAlignment(subsetDir, outDir) {
  execFileSync(PYTHON, [ALIGNMENT_SCRIPT, "--subset", subsetDir, "--out", outDir], { cwd: process.cwd(), encoding: "utf8" });
}

test("confident subset schema alignment reports mappings and blockers without canonical output", () => {
  const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), "order-guide-schema-alignment-"));
  const subsetDir = buildSubset(tmpDir);
  const outDir = path.join(subsetDir, "schema_alignment");
  const secondOutDir = path.join(tmpDir, "schema-alignment-second");
  const selectablesBefore = fs.readFileSync(path.join(subsetDir, "catalog", "selectables.csv"), "utf8");

  runAlignment(subsetDir, outDir);
  runAlignment(subsetDir, secondOutDir);

  for (const fileName of [
    "schema_alignment_report.json",
    "schema_alignment_report.md",
    "schema_alignment_selectables.csv",
    "schema_alignment_display.csv",
    "schema_alignment_availability.csv",
    "schema_alignment_source_refs.csv",
    "schema_alignment_unmapped_fields.csv",
    "schema_alignment_transformations.csv",
    "schema_alignment_blockers.csv",
  ]) {
    assert.ok(fs.existsSync(path.join(outDir, fileName)), `${fileName} should exist`);
    assert.equal(fs.readFileSync(path.join(outDir, fileName), "utf8"), fs.readFileSync(path.join(secondOutDir, fileName), "utf8"));
  }
  assert.equal(fs.readFileSync(path.join(subsetDir, "catalog", "selectables.csv"), "utf8"), selectablesBefore);

  const report = JSON.parse(fs.readFileSync(path.join(outDir, "schema_alignment_report.json"), "utf8"));
  assert.equal(report.canonical_apply_ready, false);
  assert.ok(["partial", "sufficient_for_field_mapping", "incomplete"].includes(report.schema_context_summary.schema_context_confidence));
  assert.equal(report.schema_context_summary.files["data/stingray/catalog/selectables.csv"].present, true);
  assert.ok(report.schema_context_summary.files["data/stingray/catalog/selectables.csv"].headers.includes("selectable_id"));

  const selectables = readCsv(path.join(outDir, "schema_alignment_selectables.csv"));
  assert.ok(
    selectables.some(
      (row) =>
        row.source_field === "orderable_rpo" &&
        row.target_field === "rpo" &&
        row.alignment_status === "direct_map",
    ),
  );
  assert.ok(
    selectables.some(
      (row) =>
        row.source_field === "proposal_selectable_id" &&
        row.target_field === "selectable_id" &&
        row.alignment_status === "transform_required",
    ),
  );

  const display = readCsv(path.join(outDir, "schema_alignment_display.csv"));
  assert.ok(
    display.some(
      (row) =>
        row.source_field === "section_family" &&
        row.target_field === "section_id" &&
        ["transform_required", "schema_decision_needed"].includes(row.alignment_status),
    ),
  );

  const availability = readCsv(path.join(outDir, "schema_alignment_availability.csv"));
  assert.ok(
    availability.some(
      (row) =>
        row.source_field === "availability_value" &&
        row.target_field === "status" &&
        row.source_values.includes("available") &&
        row.source_values.includes("standard") &&
        row.source_values.includes("not_available"),
    ),
  );

  const sourceRefs = readCsv(path.join(outDir, "schema_alignment_source_refs.csv"));
  assert.ok(sourceRefs.some((row) => row.source_field === "source_sheet" && row.alignment_status === "review_required"));
  assert.ok(sourceRefs.some((row) => row.source_field === "source_ref_id"));

  const unmapped = readCsv(path.join(outDir, "schema_alignment_unmapped_fields.csv"));
  assert.ok(unmapped.some((row) => row.source_field === "proposal_filter_status" && row.alignment_status === "excluded_from_first_apply"));
  assert.ok(unmapped.some((row) => row.source_field === "raw_status"));

  const blockers = readCsv(path.join(outDir, "schema_alignment_blockers.csv"));
  assert.ok(blockers.some((row) => row.blocker_key === "no_final_canonical_selectable_id_policy"));
  assert.ok(blockers.some((row) => row.blocker_key === "canonical_apply_ready_false_by_design"));
  assert.ok(blockers.some((row) => row.blocker_key === "missing_canonical_source_refs_schema" && row.blocker_type === "schema_decision_needed"));

  const markdown = fs.readFileSync(path.join(outDir, "schema_alignment_report.md"), "utf8");
  assert.match(markdown, /schema-alignment report only/);
  assert.match(markdown, /canonical_apply_ready=false/);
  assert.match(markdown, /No canonical rows were generated or applied/);

  for (const forbiddenPath of [
    "data/stingray/catalog/selectables.csv",
    "data/corvette/catalog/selectables.csv",
    "form-app/data.js",
    "form-output/stingray-form-data.json",
    "logic/dependency_rules.csv",
    "logic/auto_adds.csv",
    "pricing/price_rules.csv",
  ]) {
    assert.equal(fs.existsSync(path.join(outDir, forbiddenPath)), false, `${forbiddenPath} must not be generated`);
  }
});

test("schema alignment fails clearly for missing inputs and unsafe output", () => {
  const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), "order-guide-schema-alignment-failures-"));
  const subsetDir = buildSubset(tmpDir);
  fs.rmSync(path.join(subsetDir, "ui", "availability.csv"));

  assert.throws(
    () => runAlignment(subsetDir, path.join(tmpDir, "schema_alignment")),
    /Missing required confident subset input/,
  );
  assert.throws(
    () => runAlignment(path.join(tmpDir, "subset"), path.join(process.cwd(), "data", "corvette", "schema_alignment")),
    /Refusing to write schema alignment output/,
  );
});
