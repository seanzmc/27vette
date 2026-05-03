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
const REVIEW_SCRIPT = "scripts/generate_order_guide_review_packet.py";

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

ws = wb.create_sheet("Standard Equipment 1")
ws.append(["Stingray", "", "", "", ""])
ws.append(["", "", "S = Standard Equipment  A = Available  -- (dashes) = Not Available", "", ""])
ws.append(["Orderable RPO Code", "Ref. Only RPO Code", "Description", "Coupe\\n1YC07\\n1LT", "Convertible\\n1YC67\\n2LT"])
ws.append(["AAA", "", "Orderable evidence", "A1", "S"])
ws.append(["", "CCC", "Reference-only evidence", "A/D2", "--"])
ws.append(["CCC", "", "Same RPO orderable evidence", "A", "A"])

ct = wb.create_sheet("Color and Trim 1")
ct.append(["Recommended", "", "", "", "", ""])
ct.append(["A = Available  -- (dashes) = Not Available", "", "", "", "", ""])
ct.append(["", "", "", "", "Interior Colors", ""])
ct.append(["Decor Level", "Seat Type", "Seat Code", "Seat Trim", "Jet Black", "Sky Cool Gray1"])
ct.append(["1LT, 1LZ", "GT1 buckets", "AQ9", "Performance Textile5", "HTA", "HU76"])
ct.append(["", "", "", "", "Interior Colors", ""])
ct.append(["Exterior Solid Paint", "", "Color Code", "Touch-Up Paint Number", "Jet Black / en-us", "Sky Cool Gray1\\nen-us"])
ct.append(["Black", "", "GBA", "WA-8555", "A", "A/D2"])
ct.append(["• NOTE: Requires option code (D30) Color Combination Override.", "", "", "", "", ""])

Path(${JSON.stringify(workbookPath)}).parent.mkdir(parents=True, exist_ok=True)
wb.save(${JSON.stringify(workbookPath)})
`,
    ],
    { cwd: process.cwd(), encoding: "utf8" },
  );
}

function runPipeline(tmpDir) {
  const source = path.join(tmpDir, "fixture.xlsx");
  const profilePath = path.join(tmpDir, "source_profile.json");
  const stagingDir = path.join(tmpDir, "staging");
  const auditPath = path.join(stagingDir, "staging_audit_report.json");
  const colorTrimScopePath = path.join(tmpDir, "color_trim_scope.csv");
  const rpoRoleOverlapsPath = path.join(tmpDir, "rpo_role_overlaps.csv");

  makeFixture(source);
  fs.writeFileSync(
    colorTrimScopePath,
    [
      "sheet_name,section_role,guide_family,model_key,scope_type,confidence,review_status,notes",
      "Color and Trim 1,color_trim_interior_matrix,corvette,,model_global,needs_review,needs_review,Synthetic interior scope needs review.",
      "Color and Trim 1,color_trim_compatibility_matrix,corvette,,model_global,needs_review,needs_review,Synthetic compatibility scope needs review.",
      "Color and Trim 1,color_trim_disclosure,corvette,,model_global,needs_review,needs_review,Synthetic disclosure evidence needs review.",
      "",
    ].join("\n"),
  );
  fs.writeFileSync(
    rpoRoleOverlapsPath,
    [
      "rpo,review_status,classification,canonical_handling,recommended_action,notes",
      "CCC,needs_review,canonical_review_required,needs_manual_mapping,review_orderable_vs_reference_usage_before_proposal,Synthetic overlap needs review.",
      "",
    ].join("\n"),
  );

  execFileSync(PYTHON, [INSPECT_SCRIPT, "--source", source, "--out", profilePath], {
    cwd: process.cwd(),
    encoding: "utf8",
  });
  execFileSync(PYTHON, [EXTRACT_SCRIPT, "--source", source, "--out", stagingDir], {
    cwd: process.cwd(),
    encoding: "utf8",
  });
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
    {
      cwd: process.cwd(),
      encoding: "utf8",
    },
  );

  return { stagingDir, colorTrimScopePath, rpoRoleOverlapsPath };
}

function generateReview(stagingDir, outDir, colorTrimScopePath, rpoRoleOverlapsPath) {
  execFileSync(
    PYTHON,
    [
      REVIEW_SCRIPT,
      "--staging",
      stagingDir,
      "--out",
      outDir,
      "--color-trim-scope",
      colorTrimScopePath,
      "--rpo-role-overlaps",
      rpoRoleOverlapsPath,
    ],
    {
      cwd: process.cwd(),
      encoding: "utf8",
    },
  );
}

test("review packet generator creates human review files without mutating staging or canonical outputs", () => {
  const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), "order-guide-review-packet-"));
  const { stagingDir, colorTrimScopePath, rpoRoleOverlapsPath } = runPipeline(tmpDir);
  const reviewDir = path.join(tmpDir, "review");
  const secondReviewDir = path.join(tmpDir, "review-second");
  const stagingBefore = fs.readFileSync(path.join(stagingDir, "staging_variant_matrix_rows.csv"), "utf8");

  generateReview(stagingDir, reviewDir, colorTrimScopePath, rpoRoleOverlapsPath);
  generateReview(stagingDir, secondReviewDir, colorTrimScopePath, rpoRoleOverlapsPath);

  for (const fileName of [
    "color_trim_scope_review.md",
    "color_trim_scope_review.csv",
    "rpo_role_overlap_review.md",
    "rpo_role_overlap_review.csv",
  ]) {
    assert.ok(fs.existsSync(path.join(reviewDir, fileName)), `${fileName} should exist`);
    assert.equal(fs.readFileSync(path.join(reviewDir, fileName), "utf8"), fs.readFileSync(path.join(secondReviewDir, fileName), "utf8"));
  }

  assert.equal(fs.readFileSync(path.join(stagingDir, "staging_variant_matrix_rows.csv"), "utf8"), stagingBefore);

  const colorMarkdown = fs.readFileSync(path.join(reviewDir, "color_trim_scope_review.md"), "utf8");
  assert.match(
    colorMarkdown,
    /Do not edit this generated review packet as source of truth\. Transfer approved decisions into data\/import_maps\/corvette_2027\/\*\.csv\./,
  );
  assert.match(colorMarkdown, /The CSV is the complete review surface\./);
  assert.match(colorMarkdown, /accepted_review_only/);
  assert.match(colorMarkdown, /canonical_proposal_ready/);

  const rpoMarkdown = fs.readFileSync(path.join(reviewDir, "rpo_role_overlap_review.md"), "utf8");
  assert.match(rpoMarkdown, /accepted_expected_overlap/);
  assert.match(rpoMarkdown, /The CSV is the complete review surface\./);

  const colorRows = readCsv(path.join(reviewDir, "color_trim_scope_review.csv"));
  for (const fieldName of ["source_sheet", "section_role", "section_index", "start_row", "end_row"]) {
    assert.ok(Object.hasOwn(colorRows[0], fieldName), `${fieldName} should be present for source traceability`);
  }
  const interiorReview = colorRows.find((row) => row.source_sheet === "Color and Trim 1" && row.section_role === "color_trim_interior_matrix");
  assert.ok(interiorReview, "Color/Trim interior section should be reviewed");
  assert.equal(interiorReview.current_review_status, "needs_review");
  assert.match(interiorReview.sample_interior_rpos, /HTA/);
  assert.match(interiorReview.sample_interior_rpos, /HU7/);
  assert.equal(interiorReview.recommended_decision_options, "approved|accepted_review_only|deferred|needs_review");

  const compatibilityReview = colorRows.find(
    (row) => row.source_sheet === "Color and Trim 1" && row.section_role === "color_trim_compatibility_matrix",
  );
  assert.match(compatibilityReview.sample_exterior_colors, /Black/);

  const rpoRows = readCsv(path.join(reviewDir, "rpo_role_overlap_review.csv"));
  const ccc = rpoRows.find((row) => row.rpo === "CCC");
  assert.ok(ccc, "CCC should be included as role-overlap review evidence");
  assert.equal(Number(ccc.orderable_count) >= 1, true);
  assert.equal(Number(ccc.ref_only_count) >= 1, true);
  assert.match(ccc.source_sheets, /Standard Equipment 1/);
  assert.match(ccc.model_keys, /stingray/);
  assert.match(ccc.section_families, /standard_equipment/);
  assert.match(ccc.sample_descriptions, /Reference-only evidence/);
  assert.equal(ccc.current_review_status, "needs_review");
  assert.equal(ccc.current_canonical_handling, "needs_manual_mapping");
  assert.equal(ccc.recommended_decision_options, "approved|accepted_expected_overlap|deferred|needs_review");

  assert.equal(fs.existsSync(path.join(reviewDir, "proposed")), false);
  assert.equal(fs.existsSync(path.join(reviewDir, "catalog", "selectables.csv")), false);
  assert.equal(fs.existsSync(path.join(reviewDir, "logic", "dependency_rules.csv")), false);
  assert.equal(fs.existsSync(path.join(reviewDir, "pricing", "base_prices.csv")), false);
});

test("review packet generator fails clearly when audit prerequisites are missing", () => {
  const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), "order-guide-review-packet-missing-"));
  assert.throws(
    () =>
      execFileSync(PYTHON, [REVIEW_SCRIPT, "--staging", tmpDir, "--out", path.join(tmpDir, "review")], {
        cwd: process.cwd(),
        encoding: "utf8",
        stdio: "pipe",
      }),
    /Run scripts\/audit_order_guide_staging\.py before generating the review packet\./,
  );
});
