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

function buildProposal(tmpDir) {
  const source = path.join(tmpDir, "fixture.xlsx");
  const profilePath = path.join(tmpDir, "source_profile.json");
  const stagingDir = path.join(tmpDir, "staging");
  const proposalDir = path.join(tmpDir, "proposal");
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
  return proposalDir;
}

function runProposalAudit(proposalDir, outDir) {
  execFileSync(PYTHON, [PROPOSAL_AUDIT_SCRIPT, "--proposal", proposalDir, "--out", outDir], { cwd: process.cwd(), encoding: "utf8" });
}

test("proposal audit classifies review queue and verifies traceability without mutating proposal inputs", () => {
  const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), "order-guide-proposal-audit-"));
  const proposalDir = buildProposal(tmpDir);
  const secondOutDir = path.join(tmpDir, "proposal-audit-second");
  const selectablesBefore = fs.readFileSync(path.join(proposalDir, "catalog", "selectables.csv"), "utf8");

  runProposalAudit(proposalDir, proposalDir);
  runProposalAudit(proposalDir, secondOutDir);

  for (const fileName of [
    "proposal_audit_report.json",
    "proposal_audit_report.md",
    "proposal_review_queue_summary.csv",
    "proposal_selectable_counts.csv",
    "proposal_availability_counts.csv",
    "proposal_source_ref_integrity.csv",
    "proposal_suspicious_rows.csv",
    "proposal_rpo_overlap_traceability.csv",
  ]) {
    assert.ok(fs.existsSync(path.join(proposalDir, fileName)), `${fileName} should exist`);
    assert.equal(fs.readFileSync(path.join(proposalDir, fileName), "utf8"), fs.readFileSync(path.join(secondOutDir, fileName), "utf8"));
  }
  assert.equal(fs.readFileSync(path.join(proposalDir, "catalog", "selectables.csv"), "utf8"), selectablesBefore);

  const report = JSON.parse(fs.readFileSync(path.join(proposalDir, "proposal_audit_report.json"), "utf8"));
  assert.equal(report.readiness.canonical_apply_ready, false);
  assert.equal(report.readiness.source_refs_ready, true);
  assert.equal(report.rpo_overlap_traceability.optional_input_present, true);
  assert.equal(report.source_ref_integrity.unresolved_source_ref_count, 0);
  assert.ok(report.proposal_counts.selectables_count >= 1);
  assert.ok(report.selectables_quality.no_rpo_standard_equipment_review_only_count >= 1);
  assert.ok(report.selectables_quality.ref_only_only_proposal_count >= 1);
  assert.ok(report.availability_quality.counts_by_availability_value.available >= 1);
  assert.ok(report.recommended_next_step.includes("confident selectables"));

  const queueSummary = readCsv(path.join(proposalDir, "proposal_review_queue_summary.csv"));
  assert.ok(queueSummary.some((row) => row.review_bucket === "missing_rpo_standard_equipment" && row.original_reason === "standard_equipment_without_rpo"));
  assert.ok(queueSummary.some((row) => row.review_bucket === "ref_only_evidence" && row.original_reason === "ref_only_only_evidence"));
  assert.ok(queueSummary.some((row) => row.review_bucket === "expected_review_only" && row.original_reason === "accepted_rpo_overlap_kept_separate"));
  assert.ok(queueSummary.some((row) => row.review_bucket === "boundary_exclusion_summary" && row.original_reason === "excluded_color_trim_source"));

  const sourceIntegrity = readCsv(path.join(proposalDir, "proposal_source_ref_integrity.csv"));
  assert.ok(sourceIntegrity.some((row) => row.check_name === "unresolved_referenced_source_refs" && row.status === "pass" && row.count === "0"));
  assert.ok(sourceIntegrity.some((row) => row.check_name === "source_refs_missing_traceability" && row.status === "pass"));

  const overlapTraceability = readCsv(path.join(proposalDir, "proposal_rpo_overlap_traceability.csv"));
  assert.ok(overlapTraceability.some((row) => row.rpo === "CCC" && row.traceability_status === "summary_level_only"));

  const markdown = fs.readFileSync(path.join(proposalDir, "proposal_audit_report.md"), "utf8");
  assert.match(markdown, /# Proposal Audit Report/);
  assert.match(markdown, /audit of generated proposal artifacts only/);
  assert.match(markdown, /canonical_apply_ready/);
  assert.match(markdown, /No canonical rows were applied/);

  for (const forbiddenPath of [
    "logic/dependency_rules.csv",
    "logic/auto_adds.csv",
    "logic/exclusive_groups.csv",
    "pricing/base_prices.csv",
    "pricing/price_rules.csv",
    "form-app/data.js",
  ]) {
    assert.equal(fs.existsSync(path.join(proposalDir, forbiddenPath)), false, `${forbiddenPath} must not be generated`);
  }
});

test("proposal audit reports broken source refs and optional RPO absence without command failure", () => {
  const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), "order-guide-proposal-audit-broken-"));
  const proposalDir = buildProposal(tmpDir);

  const availabilityPath = path.join(proposalDir, "ui", "availability.csv");
  const availability = readCsv(availabilityPath);
  availability[0].source_ref_id = "missing_source_ref_id";
  writeCsv(availabilityPath, availability);
  fs.rmSync(path.join(proposalDir, "meta", "rpo_role_overlap_evidence.csv"));

  runProposalAudit(proposalDir, proposalDir);

  const report = JSON.parse(fs.readFileSync(path.join(proposalDir, "proposal_audit_report.json"), "utf8"));
  assert.equal(report.readiness.source_refs_ready, false);
  assert.equal(report.readiness.canonical_apply_ready, false);
  assert.ok(report.readiness.reasons.includes("source_ref_integrity_failures"));
  assert.equal(report.rpo_overlap_traceability.optional_input_present, false);
  assert.equal(report.readiness.rpo_overlap_traceability_ready, false);

  const sourceIntegrity = readCsv(path.join(proposalDir, "proposal_source_ref_integrity.csv"));
  const unresolved = sourceIntegrity.find((row) => row.check_name === "unresolved_referenced_source_refs");
  assert.equal(unresolved.status, "fail");
  assert.equal(unresolved.count, "1");
  assert.match(unresolved.sample_ids, /missing_source_ref_id/);

  const suspicious = readCsv(path.join(proposalDir, "proposal_suspicious_rows.csv"));
  assert.ok(suspicious.some((row) => row.suspicion_type === "unresolved_source_ref" && row.raw_value === "missing_source_ref_id"));
  assert.equal(fs.existsSync(path.join(proposalDir, "proposal_rpo_overlap_traceability.csv")), false);
});

test("proposal audit fails for missing required inputs and unsafe output paths", () => {
  const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), "order-guide-proposal-audit-failure-"));
  const proposalDir = buildProposal(tmpDir);
  fs.rmSync(path.join(proposalDir, "proposal_report.json"));
  assert.throws(
    () => runProposalAudit(proposalDir, proposalDir),
    /Missing required proposal input: proposal_report\.json/,
  );

  const safeProposalDir = buildProposal(fs.mkdtempSync(path.join(os.tmpdir(), "order-guide-proposal-audit-unsafe-")));
  assert.throws(
    () => runProposalAudit(safeProposalDir, path.join(process.cwd(), "data", "stingray", "proposal-audit")),
    /Refusing to write proposal audit output/,
  );
});
