import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import fs from "node:fs";
import test from "node:test";

const auditPath = "form-output/inspection/grand-sport-rule-audit.json";
const auditMarkdownPath = "form-output/inspection/grand-sport-rule-audit.md";
const draftPath = "form-output/inspection/grand-sport-form-data-draft.json";
const heritageHashOptionIds = ["opt_17a_001", "opt_20a_001", "opt_55a_001", "opt_75a_001", "opt_97a_001", "opt_dx4_001"];
const heritageCenterStripeOptionIds = ["opt_dmu_001", "opt_dmv_001", "opt_dmw_001", "opt_dmx_001", "opt_dmy_001"];
const nonCenterStripeOptionIds = [
  "opt_dpb_001", "opt_dpc_001", "opt_dpg_001", "opt_dpl_001", "opt_dpt_001", "opt_dsy_001", "opt_dsz_001", "opt_dt0_001",
  "opt_dth_001", "opt_dub_001", "opt_due_001", "opt_duk_001", "opt_duw_001", "opt_dzu_001", "opt_dzv_001", "opt_dzx_001",
  "opt_sht_001", "opt_vpo_001",
];

function normalizedBool(value) {
  return String(value).toLowerCase();
}

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
        row.grand_sport_rule_id.includes("rule_opt_5jr_001_includes_opt_drg_001") &&
        row.source_id === "opt_5jr_001" &&
        row.rule_type === "includes" &&
        row.target_id === "opt_drg_001"
    ),
    "5JR/DRG should be listed as copied from Stingray"
  );
  assert.ok(
    audit.parsedFromDetailRaw.some(
      (row) =>
        row.rule_id === "gs_rule_opt_cfl_001_excludes_opt_cfz_001" &&
        row.matched_phrase === "workbook_matches_detail_raw" &&
        row.source_id === "opt_cfl_001" &&
        row.rule_type === "excludes" &&
        row.target_id === "opt_cfz_001"
    ),
    "CFL/CFZ should be listed as a workbook rule matching detail_raw"
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
  assert.ok(
    audit.skippedRequiresReview.some((row) => row.rpo === "R8C" && row.fragment.includes("LPO wheels")),
    "non-RPO LPO wheel wording should remain review-only"
  );
  assert.ok(
    audit.unresolvedRpoMentions.every((row) => row.mentioned_rpo === "DTB"),
    "only workbook-missing stripe RPO mentions should remain unresolved"
  );
  assert.equal(
    audit.unresolvedRpoMentions.some((row) => ["CFV", "36S", "37S", "38S", "379", "3A9", "3F9", "3M9", "3N9"].includes(row.mentioned_rpo)),
    false,
    "inactive ground-effects and interior/color override codes should not be reported as unresolved"
  );
});

test("Grand Sport rule audit captures the approved cleanup decisions", () => {
  const workbookOptions = workbookRows("grandSport_options");
  const workbookExclusiveMembers = workbookRows("grandSport_exclusive_members");
  const workbookRules = workbookRows("grandSport_rule_mapping");
  const workbookRuleGroups = workbookRows("grandSport_rule_groups");
  const workbookRuleGroupMembers = workbookRows("grandSport_rule_group_members");
  const groundEffectMembers = workbookExclusiveMembers.filter((row) => row.group_id === "gs_excl_ground_effects");
  assert.deepEqual(
    groundEffectMembers.map((row) => row.option_id),
    ["opt_cfl_001", "opt_cfz_001", "opt_cfv_001"]
  );
  assert.equal(normalizedBool(groundEffectMembers.find((row) => row.option_id === "opt_cfv_001").active), "false");

  const optionByRpo = new Map(workbookOptions.map((row) => [row.rpo, row]));
  assert.equal(normalizedBool(optionByRpo.get("D30").selectable), "false");
  assert.equal(optionByRpo.get("D30").display_behavior, "display_only");
  assert.equal(normalizedBool(optionByRpo.get("Z15").selectable), "false");
  assert.equal(optionByRpo.get("Z15").display_behavior, "display_only");
  assert.equal(optionByRpo.get("R6X").display_behavior, "auto_only");
  for (const rpo of ["R6P", "R9V", "R9W", "R9Y", "U2K"]) {
    assert.equal(normalizedBool(optionByRpo.get(rpo).active), "false", `${rpo} should be inactive in workbook source`);
  }

  assert.equal(
    workbookRules.some(
      (row) =>
        row.rule_type === "requires" &&
        ["sec_gsha_001", "sec_gsce_001"].includes(row.source_section) &&
        row.target_section === "sec_pain_001"
    ),
    false,
    "stripe/hash rows should not retain backwards paint-color requires rules"
  );
  assert.equal(
    workbookRules.some((row) => row.source_id === "opt_z15_001" && row.rule_type === "requires"),
    false,
    "Z15 should not retain separate hard requirements for every heritage hash/stripe option"
  );

  assert.equal(workbookRuleGroups.some((row) => row.group_id === "gs_grp_z15_hash_mark_requirement"), false);
  assert.equal(workbookRuleGroupMembers.some((row) => row.group_id === "gs_grp_z15_hash_mark_requirement"), false);

  const draftRuleKeys = new Set(draft.rules.map((rule) => `${rule.source_id}::${rule.rule_type}::${rule.target_id}`));
  for (const key of [
    "opt_bv4_001::excludes::opt_r8c_001",
    "opt_r88_001::excludes::opt_eyk_001",
    "opt_sfz_001::excludes::opt_eyk_001",
    "opt_fey_001::includes::opt_cfz_001",
  ]) {
    assert.ok(draftRuleKeys.has(key), `${key} should be present`);
  }
  for (const hashOptionId of heritageHashOptionIds) {
    assert.ok(draftRuleKeys.has(`${hashOptionId}::includes::opt_z15_001`), `${hashOptionId} should auto-add Z15`);
    assert.equal(draftRuleKeys.has(`${hashOptionId}::requires::opt_z15_001`), false, `${hashOptionId} should not require manual Z15`);
    for (const targetId of nonCenterStripeOptionIds) {
      assert.ok(draftRuleKeys.has(`${hashOptionId}::excludes::${targetId}`), `${hashOptionId} should block ${targetId}`);
    }
    for (const targetId of heritageCenterStripeOptionIds) {
      assert.equal(draftRuleKeys.has(`${hashOptionId}::excludes::${targetId}`), false, `${hashOptionId} should allow ${targetId}`);
    }
  }

  const z52Members = workbookExclusiveMembers.filter((row) => row.group_id === "gs_excl_z52_packages");
  assert.deepEqual(z52Members.map((row) => row.option_id), ["opt_feb_001", "opt_fey_001"]);
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

test("Grand Sport rule audit script does not own workbook business decisions", () => {
  const source = fs.readFileSync("scripts/build_grand_sport_rule_sources.py", "utf8");
  for (const forbidden of [
    "APPROVED_EXCLUSIVE_GROUPS",
    "INACTIVE_OPTION_RPOS",
    "DESCRIPTION_UPDATES",
    "EXPLICIT_RULE_RPOS",
    "apply_grand_sport_review_decisions",
    "write_sheet(wb",
    ".save(",
  ]) {
    assert.equal(source.includes(forbidden), false, `${forbidden} should not be in the audit-only builder`);
  }
});
