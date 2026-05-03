import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import test from "node:test";

const PYTHON = process.env.PYTHON || ".venv/bin/python";
const INSPECT_SCRIPT = "scripts/inspect_order_guide_export.py";
const EXTRACT_SCRIPT = "scripts/extract_order_guide_staging.py";
const AUDIT_SCRIPT = "scripts/audit_order_guide_staging.py";
const READINESS_SCRIPT = "scripts/report_order_guide_proposal_readiness.py";
const PROPOSAL_SCRIPT = "scripts/propose_order_guide_primary_matrix.py";

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
ws.append(["AAA", "", "Orderable option requires no inferred rule", "A/D2", "S"])
ws.append(["", "CCC", "Reference-only evidence", "A", "--"])
ws.append(["", "", "No RPO standard evidence", "S1", "S"])
ws.append(["CCC", "", "Same RPO orderable evidence", "A", "A"])

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

function runPipeline(tmpDir, readinessOverride = null) {
  const source = path.join(tmpDir, "fixture.xlsx");
  const profilePath = path.join(tmpDir, "source_profile.json");
  const stagingDir = path.join(tmpDir, "staging");
  const auditPath = path.join(stagingDir, "staging_audit_report.json");
  const configDir = path.join(tmpDir, "config");
  const readinessOutDir = stagingDir;
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
      AUDIT_SCRIPT,
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
      readinessOutDir,
      "--color-trim-scope",
      colorTrimScopePath,
      "--rpo-role-overlaps",
      rpoRoleOverlapsPath,
    ],
    { cwd: process.cwd(), encoding: "utf8" },
  );

  if (readinessOverride) {
    const readinessPath = path.join(stagingDir, "proposal_readiness_report.json");
    const readiness = JSON.parse(fs.readFileSync(readinessPath, "utf8"));
    Object.assign(readiness, readinessOverride);
    fs.writeFileSync(readinessPath, `${JSON.stringify(readiness, null, 2)}\n`);
  }

  return { stagingDir };
}

function runProposal(stagingDir, outDir) {
  execFileSync(PYTHON, [PROPOSAL_SCRIPT, "--staging", stagingDir, "--out", outDir], { cwd: process.cwd(), encoding: "utf8" });
}

test("primary matrix proposal writes narrow proposal artifacts under the requested output only", () => {
  const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), "order-guide-primary-proposal-"));
  const { stagingDir } = runPipeline(tmpDir);
  const outDir = path.join(tmpDir, "proposed", "primary_matrix");
  const secondOutDir = path.join(tmpDir, "proposed-second", "primary_matrix");
  const stagingBefore = fs.readFileSync(path.join(stagingDir, "staging_variant_matrix_rows.csv"), "utf8");

  runProposal(stagingDir, outDir);
  runProposal(stagingDir, secondOutDir);

  for (const fileName of [
    "catalog/selectables.csv",
    "ui/selectable_display.csv",
    "ui/availability.csv",
    "pricing/raw_price_evidence.csv",
    "meta/source_refs.csv",
    "meta/rpo_role_overlap_evidence.csv",
    "proposal_report.json",
    "review_queue.csv",
  ]) {
    assert.ok(fs.existsSync(path.join(outDir, fileName)), `${fileName} should exist`);
    assert.equal(fs.readFileSync(path.join(outDir, fileName), "utf8"), fs.readFileSync(path.join(secondOutDir, fileName), "utf8"));
  }

  assert.equal(fs.readFileSync(path.join(stagingDir, "staging_variant_matrix_rows.csv"), "utf8"), stagingBefore);

  const selectables = readCsv(path.join(outDir, "catalog", "selectables.csv"));
  assert.equal(selectables.some((row) => row.source_sheet.startsWith("Equipment Groups")), false);
  assert.equal(selectables.some((row) => row.source_sheet.startsWith("Color and Trim")), false);
  assert.ok(selectables.some((row) => row.orderable_rpo === "AAA" && row.review_status === "proposal_only"));
  const noRpoStandard = selectables.find((row) => row.description === "No RPO standard evidence");
  assert.ok(noRpoStandard, "no-RPO Standard Equipment should remain visible as review evidence");
  assert.equal(noRpoStandard.orderable_rpo, "");
  assert.equal(noRpoStandard.ref_rpo, "");
  assert.equal(noRpoStandard.proposal_scope, "standard_equipment_review_only");
  assert.equal(noRpoStandard.review_status, "needs_review");

  const availability = readCsv(path.join(outDir, "ui", "availability.csv"));
  const adAvailability = availability.find((row) => row.orderable_rpo === "AAA" && row.body_code === "1YC07");
  assert.equal(adAvailability.raw_status, "A/D2");
  assert.equal(adAvailability.status_symbol, "A/D");
  assert.equal(adAvailability.footnote_refs, "2");
  assert.equal(adAvailability.canonical_status, "available");
  assert.equal(adAvailability.availability_value, "available");
  assert.equal(adAvailability.proposal_status, "proposal_only");

  const display = readCsv(path.join(outDir, "ui", "selectable_display.csv"));
  assert.ok(display.some((row) => row.display_label === "Orderable option requires no inferred rule" && row.proposal_status === "proposal_only"));

  const priceEvidence = readCsv(path.join(outDir, "pricing", "raw_price_evidence.csv"));
  assert.ok(priceEvidence.length >= 1);
  assert.equal(priceEvidence.every((row) => row.review_status === "raw_price_evidence_only"), true);
  assert.equal(priceEvidence.some((row) => /1YC07|Base Model Prices/.test(row.raw_values)), true);

  const overlapEvidence = readCsv(path.join(outDir, "meta", "rpo_role_overlap_evidence.csv"));
  const cccOverlap = overlapEvidence.find((row) => row.rpo === "CCC");
  assert.ok(cccOverlap, "accepted RPO overlap should be preserved as separate evidence");
  assert.equal(cccOverlap.decision_canonical_handling, "keep_separate_evidence");
  assert.equal(cccOverlap.review_status, "accepted_expected_overlap");

  const sourceRefs = readCsv(path.join(outDir, "meta", "source_refs.csv"));
  assert.ok(sourceRefs.some((row) => row.source_sheet === "Standard Equipment 1" && row.raw_status === "A/D2" && row.raw_value.includes("Orderable option")));
  assert.ok(sourceRefs.some((row) => row.source_file === "staging_price_rows.csv"));

  const reviewQueue = readCsv(path.join(outDir, "review_queue.csv"));
  assert.ok(reviewQueue.some((row) => row.reason === "standard_equipment_without_rpo"));
  assert.ok(reviewQueue.some((row) => row.reason === "ref_only_only_evidence" && row.rpo === "CCC"));
  assert.ok(reviewQueue.some((row) => row.reason === "accepted_rpo_overlap_kept_separate" && row.rpo === "CCC"));
  assert.ok(reviewQueue.some((row) => row.reason === "excluded_equipment_group_source"));
  assert.ok(reviewQueue.some((row) => row.reason === "excluded_color_trim_source"));

  const report = JSON.parse(fs.readFileSync(path.join(outDir, "proposal_report.json"), "utf8"));
  assert.equal(report.proposal_only, true);
  assert.match(report.warning, /must not be copied blindly into data\/stingray/);
  assert.equal(report.input_readiness.narrow_first_proposal_scope_ready, true);
  assert.equal(report.input_readiness.canonical_proposal_ready, false);
  assert.ok(report.forbidden_outputs_verified_absent.includes("logic/dependency_rules.csv"));
  assert.ok(report.forbidden_outputs_verified_absent.includes("pricing/price_rules.csv"));
  assert.ok(report.forbidden_outputs_verified_absent.includes("support/color_trim*.csv"));

  for (const forbiddenPath of [
    "logic/dependency_rules.csv",
    "logic/auto_adds.csv",
    "logic/exclusive_groups.csv",
    "logic/exclusive_group_members.csv",
    "pricing/base_prices.csv",
    "pricing/price_rules.csv",
    "support/color_trim_rows.csv",
  ]) {
    assert.equal(fs.existsSync(path.join(outDir, forbiddenPath)), false, `${forbiddenPath} must not be generated`);
  }

  assert.equal(fs.existsSync(path.join(outDir, "data", "stingray", "catalog", "selectables.csv")), false);
});

test("primary matrix proposal fails for missing readiness, unsafe output, and unready narrow scope", () => {
  const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), "order-guide-primary-proposal-failures-"));
  const { stagingDir } = runPipeline(tmpDir);
  fs.rmSync(path.join(stagingDir, "proposal_readiness_report.json"));
  assert.throws(
    () => runProposal(stagingDir, path.join(tmpDir, "out")),
    /Run scripts\/report_order_guide_proposal_readiness\.py before generating primary matrix proposals\./,
  );

  const secondTmpDir = fs.mkdtempSync(path.join(os.tmpdir(), "order-guide-primary-proposal-unready-"));
  const { stagingDir: unreadyStagingDir } = runPipeline(secondTmpDir, { narrow_first_proposal_scope_ready: false });
  assert.throws(() => runProposal(unreadyStagingDir, path.join(secondTmpDir, "out")), /narrow_first_proposal_scope_ready=false/);

  const thirdTmpDir = fs.mkdtempSync(path.join(os.tmpdir(), "order-guide-primary-proposal-unsafe-"));
  const { stagingDir: safeStagingDir } = runPipeline(thirdTmpDir);
  assert.throws(() => runProposal(safeStagingDir, path.join(process.cwd(), "data", "stingray", "proposal-test")), /Refusing to write proposal output/);
});
