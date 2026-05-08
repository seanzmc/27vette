import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import fs from "node:fs";
import test from "node:test";

const auditPath = "form-output/inspection/grand-sport-rule-audit.json";
const auditMarkdownPath = "form-output/inspection/grand-sport-rule-audit.md";
const draftPath = "form-output/inspection/grand-sport-form-data-draft.json";

function workbookRows(sheetName) {
  const output = execFileSync(
    ".venv/bin/python",
    [
      "-c",
      [
        "import json",
        "from openpyxl import load_workbook",
        "wb = load_workbook('stingray_master.xlsx', read_only=True, data_only=True)",
        `ws = wb['${sheetName}']`,
        "headers = [ws.cell(1, col).value for col in range(1, ws.max_column + 1)]",
        "rows = [{header: value for header, value in zip(headers, raw) if header and value is not None} for raw in ws.iter_rows(min_row=2, values_only=True)]",
        "print(json.dumps(rows))",
      ].join("; "),
    ],
    { encoding: "utf8" }
  );
  return JSON.parse(output);
}

const buildOutput = JSON.parse(
  execFileSync(".venv/bin/python", ["scripts/build_grand_sport_rule_sources.py"], {
    encoding: "utf8",
  })
);
const generateOutput = JSON.parse(
  execFileSync(".venv/bin/python", ["scripts/generate_grand_sport_form.py"], {
    encoding: "utf8",
  })
);
const audit = JSON.parse(fs.readFileSync(auditPath, "utf8"));
const draft = JSON.parse(fs.readFileSync(draftPath, "utf8"));

test("Grand Sport rule audit artifacts are generated and linked", () => {
  assert.ok(fs.existsSync(auditPath), "rule audit JSON should exist");
  assert.ok(fs.existsSync(auditMarkdownPath), "rule audit Markdown should exist");
  assert.equal(buildOutput.rule_audit_artifacts.json, `${process.cwd()}/${auditPath}`);
  assert.equal(buildOutput.rule_audit_artifacts.markdown, `${process.cwd()}/${auditMarkdownPath}`);
  assert.deepEqual(generateOutput.rule_audit_artifacts, buildOutput.rule_audit_artifacts);
  assert.equal(audit.dataset.status, "rule_audit_generated");
});

test("Grand Sport rule audit reconciles builder, workbook, and draft rule counts", () => {
  const workbookRuleRows = workbookRows("grandSport_rule_mapping");
  const workbookExclusiveGroups = workbookRows("grandSport_exclusive_groups");
  const workbookExclusiveMembers = workbookRows("grandSport_exclusive_members");

  assert.equal(audit.summary.finalWorkbookRuleRows, workbookRuleRows.length);
  assert.equal(audit.summary.finalWorkbookRuleRows, buildOutput.rule_mapping_rows);
  assert.equal(audit.summary.expectedDraftRuntimeRules, draft.rules.length);
  assert.equal(
    audit.summary.omittedDuplicateExclusiveGroup,
    audit.summary.finalWorkbookRuleRows - audit.summary.expectedDraftRuntimeRules
  );
  assert.equal(audit.summary.exclusiveGroups, workbookExclusiveGroups.length);
  assert.equal(audit.summary.exclusiveGroupMembers, workbookExclusiveMembers.length);
  assert.equal(audit.summary.copiedRuleCandidates, buildOutput.copied_rule_candidates);
  assert.equal(audit.summary.rawDetailRuleCandidates, buildOutput.raw_detail_rule_candidates);
});

test("Grand Sport rule audit separates copied, parsed, omitted, and review-needed rows", () => {
  assert.ok(
    audit.copiedFromStingray.some(
      (row) =>
        row.source_stingray_rule_id === "rule_opt_5jr_001_includes_opt_drg_001" &&
        row.source_id === "opt_5jr_001" &&
        row.target_id === "opt_drg_001"
    ),
    "5JR/DRG should be listed as copied from Stingray"
  );
  assert.ok(
    audit.parsedFromDetailRaw.some(
      (row) =>
        row.option_id === "opt_cfl_001" &&
        row.matched_phrase === "not_available_with" &&
        row.source_id === "opt_cfl_001" &&
        row.target_id === "opt_cfz_001"
    ),
    "CFL/CFZ should be listed as parsed from detail_raw"
  );
  assert.ok(
    audit.omittedDuplicateExclusiveGroup.some(
      (row) => row.source_id === "opt_rik_001" && row.rule_type === "excludes" && row.target_id === "opt_rin_001"
    ),
    "exclusive-group duplicate excludes should be visible in the audit"
  );
  assert.ok(
    audit.skippedRequiresReview.every((row) => !["R6X", "D30", "PIN", "EDU", "EFR", "36S", "37S", "38S", "379", "3A9", "3F9", "3M9", "3N9"].includes(row.rpo)),
    "reviewed/deferred interior and color-override rows should not remain review-only"
  );
  assert.deepEqual(audit.unresolvedRpoMentions, []);
});

test("Grand Sport rule audit captures the approved cleanup decisions", () => {
  const workbookExclusiveMembers = workbookRows("grandSport_exclusive_members");
  const groundEffectMembers = workbookExclusiveMembers.filter((row) => row.group_id === "gs_excl_ground_effects");
  assert.deepEqual(
    groundEffectMembers.map((row) => row.option_id),
    ["opt_cfl_001", "opt_cfz_001", "opt_cfv_001"]
  );
  assert.equal(groundEffectMembers.find((row) => row.option_id === "opt_cfv_001").active, "False");

  const draftRuleKeys = new Set(draft.rules.map((rule) => `${rule.source_id}::${rule.rule_type}::${rule.target_id}`));
  for (const key of [
    "opt_bv4_001::excludes::opt_r8c_001",
    "opt_r88_001::excludes::opt_eyk_001",
    "opt_sfz_001::excludes::opt_eyk_001",
  ]) {
    assert.ok(draftRuleKeys.has(key), `${key} should be present`);
  }
});

test("Grand Sport rule audit highlights risky duplicate RPO and special package surfaces", () => {
  assert.ok(audit.reviewHotSpots.duplicateRpos.some((row) => row.rpo === "BC4"));
  assert.ok(audit.reviewHotSpots.duplicateRpos.some((row) => row.rpo === "BCP"));
  assert.ok(audit.reviewHotSpots.specialPackageMentions.some((row) => row.rpo === "FEY"));
  assert.ok(audit.reviewHotSpots.specialPackageMentions.some((row) => row.mentioned_rpos.includes("Z25")));

  const markdown = fs.readFileSync(auditMarkdownPath, "utf8");
  assert.match(markdown, /## Skipped Requires Review/);
  assert.match(markdown, /## Unresolved RPO Mentions/);
  assert.match(markdown, /## Review Hot Spots/);
});
