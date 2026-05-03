import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import test from "node:test";

const PYTHON = process.env.PYTHON || ".venv/bin/python";
const REPORT_SCRIPT = "scripts/report_order_guide_proposal_readiness.py";

function writeFixture(stagingDir, configDir) {
  fs.mkdirSync(stagingDir, { recursive: true });
  fs.mkdirSync(configDir, { recursive: true });
  fs.writeFileSync(
    path.join(stagingDir, "staging_audit_report.json"),
    `${JSON.stringify(
      {
        readiness: {
          primary_variant_matrix_ready: true,
          color_trim_ready: true,
          pricing_ready: true,
          equipment_groups_ready: true,
          rpo_role_overlaps_ready: true,
          canonical_proposal_ready: false,
          ready_for_proposal_generation: false,
          reasons: ["color_trim_scope_deferred_from_canonical_import"],
        },
        row_counts: {
          variant_matrix_rows: { total_rows: 12 },
          price_rows: { total_rows: 3 },
        },
        color_trim_scope_review: {
          accepted_review_only_count: 2,
          canonical_import_ready: false,
          ready_for_audit_domain: true,
          review_status_counts: { accepted_review_only: 2 },
        },
        equipment_groups: {
          cross_check_only: true,
        },
        rpo_role_overlap_decisions: {
          resolved_overlap_count: 1,
          canonical_handling_counts: { keep_separate_evidence: 1 },
        },
        unresolved_rows_by_reason: {},
      },
      null,
      2,
    )}\n`,
  );
  fs.writeFileSync(
    path.join(stagingDir, "staging_audit_rpo_role_overlaps.csv"),
    [
      "rpo,orderable_count,ref_only_count,source_sheets,model_keys,section_families,sample_descriptions,recommended_action,decision_review_status,decision_classification,decision_canonical_handling,decision_recommended_action,decision_notes",
      "CCC,2,1,Standard Equipment 1,stingray,standard_equipment,Reference evidence,review_orderable_vs_reference_usage_before_proposal,accepted_expected_overlap,orderable_and_ref_only_expected,keep_separate_evidence,review_orderable_vs_reference_usage_before_proposal,Accepted fixture overlap.",
      "",
    ].join("\n"),
  );
  const colorTrimScopePath = path.join(configDir, "color_trim_scope.csv");
  const rpoOverlapsPath = path.join(configDir, "rpo_role_overlaps.csv");
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
    rpoOverlapsPath,
    [
      "rpo,review_status,classification,canonical_handling,recommended_action,notes",
      "CCC,accepted_expected_overlap,orderable_and_ref_only_expected,keep_separate_evidence,review_orderable_vs_reference_usage_before_proposal,Accepted fixture overlap.",
      "",
    ].join("\n"),
  );
  return { colorTrimScopePath, rpoOverlapsPath };
}

function runReport(stagingDir, outDir, colorTrimScopePath, rpoOverlapsPath) {
  const args = [REPORT_SCRIPT, "--staging", stagingDir, "--out", outDir];
  if (colorTrimScopePath) args.push("--color-trim-scope", colorTrimScopePath);
  if (rpoOverlapsPath) args.push("--rpo-role-overlaps", rpoOverlapsPath);
  execFileSync(PYTHON, args, { cwd: process.cwd(), encoding: "utf8" });
}

test("proposal readiness report defines narrow future scope without creating proposal outputs", () => {
  const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), "order-guide-proposal-readiness-"));
  const stagingDir = path.join(tmpDir, "staging");
  const configDir = path.join(tmpDir, "config");
  const outDir = path.join(tmpDir, "out");
  const secondOutDir = path.join(tmpDir, "out-second");
  const { colorTrimScopePath, rpoOverlapsPath } = writeFixture(stagingDir, configDir);

  runReport(stagingDir, outDir, colorTrimScopePath, rpoOverlapsPath);
  runReport(stagingDir, secondOutDir, colorTrimScopePath, rpoOverlapsPath);

  for (const fileName of ["proposal_readiness_report.json", "proposal_readiness_report.md"]) {
    assert.ok(fs.existsSync(path.join(outDir, fileName)), `${fileName} should exist`);
    assert.equal(fs.readFileSync(path.join(outDir, fileName), "utf8"), fs.readFileSync(path.join(secondOutDir, fileName), "utf8"));
  }

  const report = JSON.parse(fs.readFileSync(path.join(outDir, "proposal_readiness_report.json"), "utf8"));
  assert.equal(report.audit_snapshot.canonical_proposal_ready, false);
  assert.equal(report.narrow_first_proposal_scope_ready, true);
  assert.equal(report.config_inputs.color_trim_scope_config_present, true);
  assert.equal(report.config_inputs.rpo_role_overlap_config_present, true);

  const includedKeys = report.included_for_future_narrow_proposal.map((row) => row.domain_key);
  assert.deepEqual(includedKeys, [
    "primary_variant_matrix_rows",
    "price_schedule_raw_evidence",
    "accepted_rpo_role_overlaps_as_separate_evidence",
  ]);

  const excludedKeys = report.excluded_or_deferred_domains.map((row) => row.domain_key);
  for (const domainKey of [
    "color_trim_canonical_import",
    "equipment_groups_as_selectable_source",
    "rpo_overlap_merging",
    "rule_inference",
    "package_logic",
    "canonical_proposal_generation_in_this_pass",
  ]) {
    assert.ok(excludedKeys.includes(domainKey), `${domainKey} should be excluded or deferred`);
  }

  assert.match(report.why_global_canonical_ready_is_false.summary, /Global canonical proposal readiness remains false/);
  assert.ok(report.why_global_canonical_ready_is_false.excluded_or_deferred_domain_keys.includes("color_trim_canonical_import"));
  assert.ok(report.first_proposal_scope_recommendation.recommended_future_inputs.includes("Price Schedule as raw price evidence only"));
  assert.ok(report.first_proposal_scope_recommendation.explicit_exclusions.includes("RPO overlap merging"));

  const markdown = fs.readFileSync(path.join(outDir, "proposal_readiness_report.md"), "utf8");
  assert.match(markdown, /# Proposal Readiness Report/);
  assert.match(markdown, /This report is not a canonical proposal/);
  assert.match(markdown, /narrow_first_proposal_scope_ready: `true`/);
  assert.match(markdown, /Color\/Trim canonical import/);
  assert.match(markdown, /Global canonical proposal readiness remains false/);

  assert.equal(fs.existsSync(path.join(outDir, "proposed")), false);
  assert.equal(fs.existsSync(path.join(outDir, "catalog", "selectables.csv")), false);
  assert.equal(fs.existsSync(path.join(outDir, "logic", "dependency_rules.csv")), false);
  assert.equal(fs.existsSync(path.join(outDir, "pricing", "base_prices.csv")), false);
});

test("proposal readiness report treats optional config files as visible enrichment only", () => {
  const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), "order-guide-proposal-readiness-optional-"));
  const stagingDir = path.join(tmpDir, "staging");
  const configDir = path.join(tmpDir, "config");
  const outDir = path.join(tmpDir, "out");
  writeFixture(stagingDir, configDir);

  runReport(stagingDir, outDir, path.join(tmpDir, "missing_color_trim_scope.csv"), path.join(tmpDir, "missing_rpo_role_overlaps.csv"));

  const report = JSON.parse(fs.readFileSync(path.join(outDir, "proposal_readiness_report.json"), "utf8"));
  assert.equal(report.config_inputs.color_trim_scope_config_present, false);
  assert.equal(report.config_inputs.rpo_role_overlap_config_present, false);
  assert.equal(report.narrow_first_proposal_scope_ready, true);
});

test("proposal readiness report fails clearly when audit output is missing", () => {
  const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), "order-guide-proposal-readiness-missing-"));
  assert.throws(
    () =>
      execFileSync(PYTHON, [REPORT_SCRIPT, "--staging", tmpDir, "--out", path.join(tmpDir, "out")], {
        cwd: process.cwd(),
        encoding: "utf8",
        stdio: "pipe",
      }),
    /Run scripts\/audit_order_guide_staging\.py before generating the proposal readiness report\./,
  );
});
