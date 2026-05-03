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
const REVIEW_SCRIPT = "scripts/generate_confident_subset_review_packet.py";

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

function writeCsv(filePath, rows) {
  const headers = Object.keys(rows[0] || {});
  const quote = (value) => {
    const text = String(value ?? "");
    if (/[",\n\r]/.test(text)) return `"${text.replaceAll('"', '""')}"`;
    return text;
  };
  fs.writeFileSync(filePath, `${headers.join(",")}\n${rows.map((row) => headers.map((header) => quote(row[header])).join(",")).join("\n")}\n`);
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

function buildSubset(tmpDir, options = {}) {
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

  if (options.removeExcluded) fs.rmSync(path.join(subsetDir, "excluded_review_rows.csv"));
  if (options.makeCoverageGap) {
    const availabilityPath = path.join(subsetDir, "ui", "availability.csv");
    const availability = readCsv(availabilityPath);
    const aaaRows = availability.filter((row) => row.orderable_rpo === "AAA");
    if (aaaRows.length > 1) {
      const removeRef = aaaRows[0].source_ref_id;
      writeCsv(availabilityPath, availability.filter((row) => row.source_ref_id !== removeRef));
    }
  }

  return subsetDir;
}

function runReview(subsetDir, outDir) {
  execFileSync(PYTHON, [REVIEW_SCRIPT, "--subset", subsetDir, "--out", outDir], { cwd: process.cwd(), encoding: "utf8" });
}

test("confident subset review packet summarizes selectables, coverage, and source traces", () => {
  const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), "order-guide-confident-review-"));
  const subsetDir = buildSubset(tmpDir, { makeCoverageGap: true });
  const outDir = path.join(subsetDir, "review");
  const secondOutDir = path.join(tmpDir, "review-second");
  const selectablesBefore = fs.readFileSync(path.join(subsetDir, "catalog", "selectables.csv"), "utf8");

  runReview(subsetDir, outDir);
  runReview(subsetDir, secondOutDir);

  for (const fileName of [
    "confident_subset_review.md",
    "confident_subset_review_summary.json",
    "confident_subset_selectables_review.csv",
    "confident_subset_availability_matrix.csv",
    "confident_subset_model_section_counts.csv",
    "confident_subset_source_trace_samples.csv",
  ]) {
    assert.ok(fs.existsSync(path.join(outDir, fileName)), `${fileName} should exist`);
    assert.equal(fs.readFileSync(path.join(outDir, fileName), "utf8"), fs.readFileSync(path.join(secondOutDir, fileName), "utf8"));
  }
  assert.equal(fs.readFileSync(path.join(subsetDir, "catalog", "selectables.csv"), "utf8"), selectablesBefore);

  const summary = JSON.parse(fs.readFileSync(path.join(outDir, "confident_subset_review_summary.json"), "utf8"));
  assert.equal(summary.canonical_apply_ready, false);
  assert.ok(summary.retained_selectables >= 1);
  assert.ok(summary.retained_availability_rows >= 1);
  assert.ok(summary.multi_model_rpo_count >= 1);
  assert.ok(summary.source_trace_sample_count >= 1);
  assert.ok(summary.missing_coverage_count >= 1);

  const markdown = fs.readFileSync(path.join(outDir, "confident_subset_review.md"), "utf8");
  assert.match(markdown, /generated review evidence, not source-of-truth config/);
  assert.match(markdown, /canonical_apply_ready=false/);
  assert.match(markdown, /Model\/Section Summary/);
  assert.match(markdown, /Complete CSV review surfaces/);
  assert.match(markdown, /No canonical rows were applied or generated/);

  const selectablesReview = readCsv(path.join(outDir, "confident_subset_selectables_review.csv"));
  assert.ok(selectablesReview.some((row) => row.orderable_rpo === "AAA" && row.source_ref_count !== "0"));
  assert.ok(Object.hasOwn(selectablesReview[0], "source_sheets"));
  assert.ok(Object.hasOwn(selectablesReview[0], "source_rows_sample"));

  const availabilityMatrix = readCsv(path.join(outDir, "confident_subset_availability_matrix.csv"));
  const subsetSelectables = readCsv(path.join(subsetDir, "catalog", "selectables.csv"));
  assert.equal(availabilityMatrix.length, subsetSelectables.length);
  const variantColumns = Object.keys(availabilityMatrix[0]).filter((header) => header.includes("_"));
  assert.ok(variantColumns.length >= 1);
  assert.equal(availabilityMatrix.some((row) => row.coverage_status === "coverage_gap"), true);

  const modelSectionCounts = readCsv(path.join(outDir, "confident_subset_model_section_counts.csv"));
  assert.ok(modelSectionCounts.some((row) => row.model_key === "stingray" && row.retained_selectable_count !== "0"));

  const sourceSamples = readCsv(path.join(outDir, "confident_subset_source_trace_samples.csv"));
  const subsetSourceRefIds = new Set(readCsv(path.join(subsetDir, "meta", "source_refs.csv")).map((row) => row.source_ref_id));
  assert.ok(sourceSamples.length >= 1);
  assert.equal(sourceSamples.every((row) => subsetSourceRefIds.has(row.source_ref_id) && row.source_sheet && row.source_row), true);

  for (const forbiddenPath of [
    "data/stingray/catalog/selectables.csv",
    "form-app/data.js",
    "form-output/stingray-form-data.json",
    "logic/dependency_rules.csv",
    "logic/auto_adds.csv",
    "pricing/price_rules.csv",
  ]) {
    assert.equal(fs.existsSync(path.join(outDir, forbiddenPath)), false, `${forbiddenPath} must not be generated`);
  }
});

test("confident subset review tolerates missing excluded rows and refuses unsafe output", () => {
  const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), "order-guide-confident-review-optional-"));
  const subsetDir = buildSubset(tmpDir, { removeExcluded: true });
  const outDir = path.join(tmpDir, "review");
  runReview(subsetDir, outDir);
  const summary = JSON.parse(fs.readFileSync(path.join(outDir, "confident_subset_review_summary.json"), "utf8"));
  assert.equal(summary.excluded_review_rows_present, false);

  assert.throws(
    () => runReview(subsetDir, path.join(process.cwd(), "data", "corvette", "review")),
    /Refusing to write confident subset review output/,
  );
});
