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
const DECISION_SCRIPT = "scripts/generate_schema_decision_packet.py";

const REQUIRED_DECISIONS = [
  "selectable_id_policy",
  "section_mapping_policy",
  "availability_schema_policy",
  "source_refs_policy",
  "proposal_metadata_policy",
  "first_apply_boundary",
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

function buildAlignment(tmpDir) {
  const source = path.join(tmpDir, "fixture.xlsx");
  const profilePath = path.join(tmpDir, "source_profile.json");
  const stagingDir = path.join(tmpDir, "staging");
  const proposalDir = path.join(tmpDir, "proposal");
  const subsetDir = path.join(tmpDir, "subset");
  const alignmentDir = path.join(subsetDir, "schema_alignment");
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
  execFileSync(PYTHON, [ALIGNMENT_SCRIPT, "--subset", subsetDir, "--out", alignmentDir], { cwd: process.cwd(), encoding: "utf8" });

  return alignmentDir;
}

function runDecisionPacket(alignmentDir, outDir) {
  execFileSync(PYTHON, [DECISION_SCRIPT, "--alignment", alignmentDir, "--out", outDir], { cwd: process.cwd(), encoding: "utf8" });
}

test("schema decision packet groups alignment blockers into fixed human decisions", () => {
  const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), "order-guide-schema-decisions-"));
  const alignmentDir = buildAlignment(tmpDir);
  const outDir = path.join(alignmentDir, "decisions");
  const secondOutDir = path.join(tmpDir, "decisions-second");
  const alignmentBefore = fs.readFileSync(path.join(alignmentDir, "schema_alignment_report.json"), "utf8");

  runDecisionPacket(alignmentDir, outDir);
  runDecisionPacket(alignmentDir, secondOutDir);

  for (const fileName of ["schema_decision_packet.md", "schema_decision_items.csv", "schema_decision_options.csv"]) {
    assert.ok(fs.existsSync(path.join(outDir, fileName)), `${fileName} should exist`);
    assert.equal(fs.readFileSync(path.join(outDir, fileName), "utf8"), fs.readFileSync(path.join(secondOutDir, fileName), "utf8"));
  }
  assert.equal(fs.readFileSync(path.join(alignmentDir, "schema_alignment_report.json"), "utf8"), alignmentBefore);

  const items = readCsv(path.join(outDir, "schema_decision_items.csv"));
  assert.deepEqual(items.map((row) => row.decision_id).sort(), [...REQUIRED_DECISIONS].sort());
  assert.equal(items.every((row) => row.related_blocker_ids || row.related_transformation_ids || row.related_unmapped_fields), true);
  assert.ok(items.some((row) => row.decision_id === "selectable_id_policy" && row.current_evidence_summary.includes("proposal_selectable_id")));
  assert.ok(items.some((row) => row.decision_id === "first_apply_boundary" && row.required_human_decision.includes("Confirm")));

  const options = readCsv(path.join(outDir, "schema_decision_options.csv"));
  for (const decisionId of REQUIRED_DECISIONS) {
    assert.ok(options.filter((row) => row.decision_id === decisionId).length >= 2, `${decisionId} should have options`);
  }
  assert.equal(Object.hasOwn(options[0], "recommended_default"), true);
  assert.equal(Object.hasOwn(options[0], "recommended"), false);
  assert.ok(options.some((row) => row.decision_id === "selectable_id_policy" && row.option_label.includes("model_key")));

  const markdown = fs.readFileSync(path.join(outDir, "schema_decision_packet.md"), "utf8");
  assert.match(markdown, /generated decision packet, not source-of-truth config/);
  assert.match(markdown, /canonical_apply_ready=false/);
  assert.match(markdown, /proposal_selectable_id is not canonical selectable_id/);
  assert.match(markdown, /section_family is not final section_id/);
  assert.match(markdown, /Color\/Trim, Equipment Groups, rules, packages, and prices remain excluded/);
  assert.match(markdown, /No canonical rows were generated or applied/);
  assert.match(markdown, /No apply is authorized by this packet/);

  for (const forbiddenPath of [
    "data/stingray/catalog/selectables.csv",
    "data/corvette/catalog/selectables.csv",
    "form-app/data.js",
    "form-output/stingray-form-data.json",
    "logic/dependency_rules.csv",
    "logic/auto_adds.csv",
    "logic/exclusive_groups.csv",
    "pricing/price_rules.csv",
  ]) {
    assert.equal(fs.existsSync(path.join(outDir, forbiddenPath)), false, `${forbiddenPath} must not be generated`);
  }
});

test("schema decision packet fails clearly for missing required inputs and unsafe output", () => {
  const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), "order-guide-schema-decisions-failures-"));
  const alignmentDir = buildAlignment(tmpDir);
  fs.rmSync(path.join(alignmentDir, "schema_alignment_transformations.csv"));

  assert.throws(
    () => runDecisionPacket(alignmentDir, path.join(tmpDir, "decisions")),
    /Missing required schema alignment input/,
  );
  assert.throws(
    () => runDecisionPacket(alignmentDir, path.join(process.cwd(), "data", "corvette", "decisions")),
    /Refusing to write schema decision packet output/,
  );
});
