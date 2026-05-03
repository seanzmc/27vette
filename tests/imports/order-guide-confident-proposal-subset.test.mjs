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

function buildBroadProposal(tmpDir) {
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
  execFileSync(PYTHON, [PROPOSAL_AUDIT_SCRIPT, "--proposal", proposalDir, "--out", proposalDir], { cwd: process.cwd(), encoding: "utf8" });
  return proposalDir;
}

function runSubset(proposalDir, outDir) {
  execFileSync(PYTHON, [SUBSET_SCRIPT, "--proposal", proposalDir, "--out", outDir], { cwd: process.cwd(), encoding: "utf8" });
}

test("confident subset keeps only source-traceable orderable primary matrix rows", () => {
  const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), "order-guide-confident-subset-"));
  const proposalDir = buildBroadProposal(tmpDir);
  const outDir = path.join(tmpDir, "primary_matrix_confident");
  const secondOutDir = path.join(tmpDir, "primary_matrix_confident_second");
  const unrelatedPath = path.join(outDir, "keep-me.txt");
  fs.mkdirSync(outDir, { recursive: true });
  fs.writeFileSync(unrelatedPath, "unrelated file should remain\n");
  const broadSelectablesBefore = fs.readFileSync(path.join(proposalDir, "catalog", "selectables.csv"), "utf8");

  runSubset(proposalDir, outDir);
  runSubset(proposalDir, secondOutDir);

  for (const fileName of [
    "catalog/selectables.csv",
    "ui/selectable_display.csv",
    "ui/availability.csv",
    "meta/source_refs.csv",
    "proposal_subset_report.json",
    "excluded_review_rows.csv",
  ]) {
    assert.ok(fs.existsSync(path.join(outDir, fileName)), `${fileName} should exist`);
    assert.equal(fs.readFileSync(path.join(outDir, fileName), "utf8"), fs.readFileSync(path.join(secondOutDir, fileName), "utf8"));
  }
  assert.equal(fs.readFileSync(unrelatedPath, "utf8"), "unrelated file should remain\n");
  assert.equal(fs.readFileSync(path.join(proposalDir, "catalog", "selectables.csv"), "utf8"), broadSelectablesBefore);

  const selectables = readCsv(path.join(outDir, "catalog", "selectables.csv"));
  assert.ok(selectables.length >= 1);
  assert.equal(
    selectables.every(
      (row) =>
        row.proposal_scope === "primary_matrix_selectable_candidate" &&
        row.review_status === "proposal_only" &&
        row.proposal_filter_status === "confident_subset" &&
        row.orderable_rpo &&
        row.model_key &&
        row.model_key !== "corvette",
    ),
    true,
  );
  assert.equal(selectables.some((row) => row.proposal_scope === "standard_equipment_review_only"), false);
  assert.equal(selectables.some((row) => !row.orderable_rpo), false);
  assert.equal(selectables.some((row) => row.ref_rpo && !row.orderable_rpo), false);

  const retainedIds = new Set(selectables.map((row) => row.proposal_selectable_id));
  const display = readCsv(path.join(outDir, "ui", "selectable_display.csv"));
  assert.equal(display.every((row) => retainedIds.has(row.proposal_selectable_id) && row.proposal_filter_status === "confident_subset"), true);

  const availability = readCsv(path.join(outDir, "ui", "availability.csv"));
  assert.ok(availability.length >= 1);
  assert.equal(
    availability.every(
      (row) =>
        retainedIds.has(row.proposal_selectable_id) &&
        ["available", "standard", "not_available"].includes(row.availability_value) &&
        row.model_key &&
        row.variant_id &&
        row.source_ref_id &&
        row.proposal_filter_status === "confident_subset",
    ),
    true,
  );

  const sourceRefs = readCsv(path.join(outDir, "meta", "source_refs.csv"));
  const sourceRefIds = new Set(sourceRefs.map((row) => row.source_ref_id));
  for (const row of selectables) {
    for (const refId of row.source_ref_ids.split("|").filter(Boolean)) assert.ok(sourceRefIds.has(refId), `${refId} should resolve`);
  }
  for (const row of availability) assert.ok(sourceRefIds.has(row.source_ref_id), `${row.source_ref_id} should resolve`);

  const excludedRows = readCsv(path.join(outDir, "excluded_review_rows.csv"));
  assert.ok(excludedRows.some((row) => row.exclusion_reason === "review_bucket_ref_only_evidence"));
  assert.ok(excludedRows.some((row) => row.exclusion_reason === "review_bucket_missing_rpo_standard_equipment"));
  assert.ok(excludedRows.some((row) => row.exclusion_reason === "review_bucket_boundary_exclusion_summary"));

  const report = JSON.parse(fs.readFileSync(path.join(outDir, "proposal_subset_report.json"), "utf8"));
  assert.equal(report.readiness.canonical_apply_ready, false);
  assert.equal(report.readiness.source_refs_ready, true);
  assert.equal(report.readiness.confident_subset_ready, true);
  assert.ok(report.confident_subset_counts.retained_selectables >= 1);
  assert.ok(report.confident_subset_counts.excluded_selectables >= 1);
  assert.ok(report.blocking_review_buckets_used.includes("ref_only_evidence"));
  assert.ok(report.nonblocking_review_buckets_observed.includes("expected_review_only"));
  assert.ok(report.review_rows_without_selectable_id_count >= 1);
  assert.ok(report.forbidden_outputs_verified_absent.includes("pricing/price_rules.csv"));
  assert.ok(report.forbidden_outputs_verified_absent.includes("logic/dependency_rules.csv"));

  assert.equal(fs.existsSync(path.join(outDir, "pricing", "raw_price_evidence.csv")), false);
  assert.equal(fs.existsSync(path.join(outDir, "pricing", "base_prices.csv")), false);
  assert.equal(fs.existsSync(path.join(outDir, "pricing", "price_rules.csv")), false);
  assert.equal(fs.existsSync(path.join(outDir, "logic", "dependency_rules.csv")), false);
  assert.equal(fs.existsSync(path.join(outDir, "logic", "auto_adds.csv")), false);
  assert.equal(fs.existsSync(path.join(outDir, "logic", "exclusive_groups.csv")), false);
  assert.equal(fs.existsSync(path.join(outDir, "support", "color_trim_rows.csv")), false);
});

test("confident subset refuses unsafe output and requires proposal audit", () => {
  const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), "order-guide-confident-subset-failure-"));
  const proposalDir = buildBroadProposal(tmpDir);
  fs.rmSync(path.join(proposalDir, "proposal_audit_report.json"));
  assert.throws(
    () => runSubset(proposalDir, path.join(tmpDir, "out")),
    /Missing required proposal input: proposal_audit_report\.json/,
  );

  const safeProposalDir = buildBroadProposal(fs.mkdtempSync(path.join(os.tmpdir(), "order-guide-confident-subset-unsafe-")));
  assert.throws(
    () => runSubset(safeProposalDir, path.join(process.cwd(), "data", "stingray", "confident-subset")),
    /Refusing to write confident proposal subset output/,
  );
});
