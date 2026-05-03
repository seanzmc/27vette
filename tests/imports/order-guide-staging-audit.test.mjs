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
ws.append(["Orderable RPO Code", "Ref. Only RPO Code", "Description", "Coupe\\n1YC07\\n1LT", "Mystery Coupe\\n9ZZ07\\n1LT"])
ws.append(["AAA", "", "Example option requires (BBB)", "A1", "S2"])
ws.append(["", "CCC", "Reference evidence", "A/D2", "--"])
ws.append(["CCC", "", "Same code appears as orderable evidence", "A", "A"])

eg = wb.create_sheet("Equipment Groups 1")
eg.append(["Stingray", "", "", "", ""])
eg.append(["", "", "S = Standard Equipment  ■ = Included in Equipment Group", "", ""])
eg.append(["Orderable RPO Code", "Ref. Only RPO Code", "Description", "Coupe\\n1YC07\\n1LT", "Mystery Coupe\\n9ZZ07\\n1LT"])
eg.append(["Equipment Groups", "", "", "", ""])
eg.append(["", "CCC", "Reference evidence", "■", "--"])

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

unknown = wb.create_sheet("Loose Notes")
unknown.append(["Meaningful unsupported note"])
unknown.append(["When ordered with (EEE), review manually"])

Path(${JSON.stringify(workbookPath)}).parent.mkdir(parents=True, exist_ok=True)
wb.save(${JSON.stringify(workbookPath)})
`,
    ],
    { cwd: process.cwd(), encoding: "utf8" },
  );
}

test("staging audit reports extraction quality without modifying staging evidence", () => {
  const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), "order-guide-audit-"));
  const source = path.join(tmpDir, "fixture.xlsx");
  const profilePath = path.join(tmpDir, "source_profile.json");
  const stagingDir = path.join(tmpDir, "staging");
  const auditPath = path.join(stagingDir, "staging_audit_report.json");
  const secondAuditPath = path.join(stagingDir, "staging_audit_report_second.json");
  const acceptedScopePath = path.join(tmpDir, "color_trim_scope_accepted.csv");
  const acceptedRpoDecisionPath = path.join(tmpDir, "rpo_role_overlaps_accepted.csv");
  const acceptedAuditPath = path.join(stagingDir, "staging_audit_report_accepted_scope.json");
  const missingScopeAuditPath = path.join(stagingDir, "staging_audit_report_missing_scope.json");
  const missingDecisionAuditPath = path.join(stagingDir, "staging_audit_report_missing_decision.json");
  makeFixture(source);

  execFileSync(PYTHON, [INSPECT_SCRIPT, "--source", source, "--out", profilePath], {
    cwd: process.cwd(),
    encoding: "utf8",
  });
  execFileSync(PYTHON, [EXTRACT_SCRIPT, "--source", source, "--out", stagingDir], {
    cwd: process.cwd(),
    encoding: "utf8",
  });

  const stagingBefore = fs.readFileSync(path.join(stagingDir, "staging_variant_matrix_rows.csv"), "utf8");
  execFileSync(PYTHON, [AUDIT_SCRIPT, "--staging", stagingDir, "--out", auditPath], {
    cwd: process.cwd(),
    encoding: "utf8",
  });
  execFileSync(PYTHON, [AUDIT_SCRIPT, "--staging", stagingDir, "--out", secondAuditPath], {
    cwd: process.cwd(),
    encoding: "utf8",
  });
  assert.equal(fs.readFileSync(path.join(stagingDir, "staging_variant_matrix_rows.csv"), "utf8"), stagingBefore);

  for (const fileName of [
    "staging_audit_report.json",
    "staging_audit_model_key_counts.csv",
    "staging_audit_status_counts.csv",
    "staging_audit_rpo_counts.csv",
    "staging_audit_rpo_role_overlaps.csv",
    "staging_audit_footnote_counts.csv",
    "staging_audit_suspicious_rows.csv",
  ]) {
    assert.ok(fs.existsSync(path.join(stagingDir, fileName)), `${fileName} should exist`);
  }

  const audit = JSON.parse(fs.readFileSync(auditPath, "utf8"));
  assert.deepEqual(
    audit.inputs.required_files,
    [
      "import_report.json",
      "staging_ignored_rows.csv",
      "staging_sheets.csv",
      "staging_status_symbols.csv",
      "staging_unresolved_rows.csv",
      "staging_variant_matrix_rows.csv",
      "staging_variants.csv",
    ],
  );
  assert.equal(audit.readiness.advisory_only, true);
  assert.equal(audit.readiness.ready_for_proposal_generation, false);
  assert.ok(audit.readiness.reasons.includes("unresolved_rows_present"));
  assert.equal(audit.readiness.primary_variant_matrix_ready, false);
  assert.equal(audit.readiness.color_trim_ready, false);
  assert.equal(audit.readiness.pricing_ready, true);
  assert.equal(audit.readiness.equipment_groups_ready, true);
  assert.equal(audit.readiness.canonical_proposal_ready, false);
  assert.equal(audit.equipment_groups.cross_check_only, true);
  assert.equal(audit.equipment_groups.variant_matrix_leak_count, 0);
  assert.equal(audit.color_trim.has_interior_and_compatibility_rows, true);
  assert.equal(audit.color_trim_scope_review.color_trim_scope_config_present, true);
  assert.equal(audit.color_trim_scope_review.ready_for_audit_domain, false);
  assert.equal(audit.color_trim_scope_review.review_status_counts.needs_review >= 1, true);
  assert.equal(audit.color_trim_scope_review.missing_section_count, 0);
  assert.ok(audit.variant_columns_by_sheet["Standard Equipment 1"].some((row) => row.body_code === "1YC07" && row.model_key === "stingray"));
  assert.ok(audit.variant_columns_by_sheet["Standard Equipment 1"].some((row) => row.body_code === "9ZZ07" && row.model_key === ""));
  assert.ok(audit.row_counts.variant_matrix_rows.total_rows >= 4);
  assert.ok(audit.model_key_counts.some((row) => row.staging_file === "variant_matrix_rows" && row.model_key === "stingray"));
  assert.ok(audit.status_counts.some((row) => row.status_symbol === "A/D" && row.canonical_status === "available"));
  assert.ok(audit.rpo_counts.some((row) => row.rpo_kind === "orderable" && row.rpo === "AAA"));
  assert.ok(audit.rpo_counts.some((row) => row.rpo_kind === "ref_only" && row.rpo === "CCC"));
  assert.ok(audit.footnote_counts.some((row) => row.footnote_scope === "status_cell" && row.footnote_refs === "1"));
  assert.ok(audit.footnote_counts.some((row) => row.footnote_scope === "interior_rpo" && row.footnote_refs === "6"));
  assert.ok(audit.unresolved_rows_by_reason.ignored_or_unknown_sheet_with_content >= 1);
  assert.ok(audit.ignored_rows_by_reason.equipment_group_label_row >= 1);
  assert.ok(audit.suspicious_rows_by_bucket.color_trim_review_only >= 1);
  assert.ok(audit.suspicious_rows_by_bucket.canonical_review_required >= 1);
  assert.ok(audit.suspicious_rows_by_bucket.import_map_gap >= 1);
  assert.ok(audit.suspicious_rows_by_type.model_scope_ambiguous >= 1);
  assert.ok(audit.suspicious_rows_by_type.rpo_role_overlap >= 1);
  assert.ok(audit.suspicious_rows_by_readiness_impact.review_required >= 1);
  assert.ok(audit.suspicious_rows_by_readiness_impact.blocking >= 1);
  assert.ok(audit.recommended_actions_by_bucket.color_trim_review_only["confirm_model_scope_or_import_map; do_not_variant_expand"] >= 1);
  assert.equal(audit.rpo_role_overlap_count >= 1, true);
  assert.equal(audit.rpo_role_overlap_summary.rpos.includes("CCC"), true);
  assert.equal(audit.rpo_role_overlap_decisions.config_present, true);
  assert.equal(audit.rpo_role_overlap_decisions.observed_overlap_count >= 1, true);
  assert.equal(audit.rpo_role_overlap_decisions.missing_rpos.includes("CCC"), true);
  assert.equal(audit.rpo_role_overlap_decisions.mapped_overlap_count, 0);
  assert.equal(audit.rpo_role_overlap_decisions.resolved_overlap_count, 0);
  assert.equal(audit.rpo_role_overlap_decisions.unused_decision_count >= 1, true);

  const rpoRoleOverlaps = readCsv(path.join(stagingDir, "staging_audit_rpo_role_overlaps.csv"));
  const cccOverlap = rpoRoleOverlaps.find((row) => row.rpo === "CCC");
  assert.ok(cccOverlap, "CCC should be surfaced in the role-overlap review CSV");
  assert.equal(Number(cccOverlap.orderable_count) >= 1, true);
  assert.equal(Number(cccOverlap.ref_only_count) >= 1, true);
  assert.match(cccOverlap.source_sheets, /Standard Equipment 1/);
  assert.match(cccOverlap.model_keys, /stingray/);
  assert.match(cccOverlap.section_families, /standard_equipment/);
  assert.match(cccOverlap.sample_descriptions, /Reference evidence/);
  assert.equal(cccOverlap.recommended_action, "review_orderable_vs_reference_usage_before_proposal");
  assert.equal(cccOverlap.decision_review_status, "");
  assert.equal(cccOverlap.decision_classification, "");
  assert.equal(cccOverlap.decision_canonical_handling, "");

  const suspiciousRows = readCsv(path.join(stagingDir, "staging_audit_suspicious_rows.csv"));
  for (const fieldName of [
    "suspicion_type",
    "review_bucket",
    "recommended_action",
    "section_family",
    "rpo",
    "raw_value",
    "classification_reason",
    "readiness_impact",
  ]) {
    assert.ok(Object.hasOwn(suspiciousRows[0], fieldName), `${fieldName} should be appended to suspicious rows`);
  }
  assert.equal(suspiciousRows.some((row) => row.reason === "variant_model_key_needs_review"), true);
  assert.equal(suspiciousRows.some((row) => row.reason === "ignored_or_unknown_sheet_with_content"), true);
  assert.equal(
    suspiciousRows.some(
      (row) =>
        row.reason === "color_trim_model_key_ambiguous" &&
        row.review_bucket === "color_trim_review_only" &&
        row.readiness_impact === "review_required",
    ),
    true,
  );
  assert.equal(
    suspiciousRows.some(
      (row) =>
        row.reason === "rpo_appears_as_orderable_and_ref_only" &&
        row.review_bucket === "canonical_review_required" &&
        row.rpo === "CCC" &&
        row.classification_reason.includes("orderable and reference-only") &&
        row.decision_review_status === "",
    ),
    true,
  );

  assert.equal(fs.existsSync(path.join(stagingDir, "proposed")), false);
  assert.equal(fs.existsSync(path.join(stagingDir, "catalog", "selectables.csv")), false);
  assert.equal(fs.existsSync(path.join(stagingDir, "logic", "dependency_rules.csv")), false);
  assert.equal(fs.existsSync(path.join(stagingDir, "pricing", "base_prices.csv")), false);

  assert.equal(
    fs.readFileSync(path.join(stagingDir, "staging_audit_model_key_counts.csv"), "utf8"),
    fs.readFileSync(path.join(stagingDir, "staging_audit_model_key_counts.csv"), "utf8"),
  );
  assert.equal(
    fs.readFileSync(auditPath, "utf8").replace(/staging_audit_report\.json/g, "staging_audit_report_second.json"),
    fs.readFileSync(secondAuditPath, "utf8"),
  );

  fs.writeFileSync(
    acceptedScopePath,
    [
      "sheet_name,section_role,guide_family,model_key,scope_type,confidence,review_status,notes",
      "Color and Trim 1,color_trim_interior_matrix,corvette,,model_global,confirmed,accepted_review_only,Accepted as review-only scope for audit domain.",
      "Color and Trim 1,color_trim_compatibility_matrix,corvette,,model_global,confirmed,accepted_review_only,Accepted as review-only scope for audit domain.",
      "Color and Trim 1,color_trim_disclosure,corvette,,model_global,confirmed,accepted_review_only,Accepted as review-only scope for audit domain.",
      "",
    ].join("\n"),
  );
  fs.writeFileSync(
    acceptedRpoDecisionPath,
    [
      "rpo,review_status,classification,canonical_handling,recommended_action,notes",
      "CCC,accepted_expected_overlap,orderable_and_ref_only_expected,keep_separate_evidence,review_orderable_vs_reference_usage_before_proposal,Accepted in synthetic audit fixture.",
      "UNUSED,accepted_expected_overlap,orderable_and_ref_only_expected,keep_separate_evidence,review_orderable_vs_reference_usage_before_proposal,Stale fixture decision row.",
      "",
    ].join("\n"),
  );
  execFileSync(
    PYTHON,
    [AUDIT_SCRIPT, "--staging", stagingDir, "--out", acceptedAuditPath, "--color-trim-scope", acceptedScopePath, "--rpo-role-overlaps", acceptedRpoDecisionPath],
    {
      cwd: process.cwd(),
      encoding: "utf8",
    },
  );
  const acceptedAudit = JSON.parse(fs.readFileSync(acceptedAuditPath, "utf8"));
  assert.equal(acceptedAudit.color_trim_scope_review.ready_for_audit_domain, true);
  assert.equal(acceptedAudit.color_trim_scope_review.canonical_import_ready, false);
  assert.equal(acceptedAudit.rpo_role_overlap_decisions.mapped_overlap_count, 1);
  assert.equal(acceptedAudit.rpo_role_overlap_decisions.resolved_overlap_count, 1);
  assert.equal(acceptedAudit.rpo_role_overlap_decisions.unused_decision_rpos.includes("UNUSED"), true);
  assert.equal(acceptedAudit.readiness.rpo_role_overlaps_ready, true);
  assert.equal(acceptedAudit.readiness.color_trim_ready, true);
  assert.equal(acceptedAudit.readiness.canonical_proposal_ready, false);
  assert.ok(acceptedAudit.readiness.reasons.includes("color_trim_scope_deferred_from_canonical_import"));

  execFileSync(PYTHON, [AUDIT_SCRIPT, "--staging", stagingDir, "--out", missingScopeAuditPath, "--color-trim-scope", path.join(tmpDir, "missing_color_trim_scope.csv")], {
    cwd: process.cwd(),
    encoding: "utf8",
  });
  const missingScopeAudit = JSON.parse(fs.readFileSync(missingScopeAuditPath, "utf8"));
  assert.equal(missingScopeAudit.color_trim_scope_review.color_trim_scope_config_present, false);
  assert.equal(missingScopeAudit.color_trim_scope_review.missing_section_count >= 1, true);
  assert.deepEqual(Object.keys(missingScopeAudit.color_trim_scope_review.missing_sections[0]).sort(), [
    "guide_family",
    "observed_model_key",
    "scope_type",
    "section_index",
    "section_role",
    "sheet_name",
  ]);

  execFileSync(
    PYTHON,
    [AUDIT_SCRIPT, "--staging", stagingDir, "--out", missingDecisionAuditPath, "--rpo-role-overlaps", path.join(tmpDir, "missing_rpo_role_overlaps.csv")],
    {
      cwd: process.cwd(),
      encoding: "utf8",
    },
  );
  const missingDecisionAudit = JSON.parse(fs.readFileSync(missingDecisionAuditPath, "utf8"));
  assert.equal(missingDecisionAudit.rpo_role_overlap_decisions.config_present, false);
  assert.equal(missingDecisionAudit.rpo_role_overlap_decisions.missing_rpos.includes("CCC"), true);
});

test("staging audit exits nonzero for missing required inputs only", () => {
  const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), "order-guide-audit-missing-"));
  assert.throws(
    () => execFileSync(PYTHON, [AUDIT_SCRIPT, "--staging", tmpDir, "--out", path.join(tmpDir, "staging_audit_report.json")], {
      cwd: process.cwd(),
      encoding: "utf8",
      stdio: "pipe",
    }),
    /Missing required staging file/,
  );
});
