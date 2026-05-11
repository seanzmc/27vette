import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import fs from "node:fs";
import test from "node:test";

const previewPath = "form-output/inspection/grand-sport-contract-preview.json";
const previewMarkdownPath = "form-output/inspection/grand-sport-contract-preview.md";
const appDataPath = "form-app/data.js";

function generatePreviewWithoutAppMutation() {
  const beforeAppData = fs.readFileSync(appDataPath, "utf8");
  execFileSync(".venv/bin/python", ["scripts/generate_grand_sport_form.py"], {
    encoding: "utf8",
    stdio: "pipe",
  });
  const afterAppData = fs.readFileSync(appDataPath, "utf8");
  assert.equal(afterAppData, beforeAppData, "Grand Sport preview generation must not mutate form-app/data.js");
  assert.ok(fs.existsSync(previewPath), "contract preview JSON should exist");
  assert.ok(fs.existsSync(previewMarkdownPath), "contract preview Markdown should exist");
  return JSON.parse(fs.readFileSync(previewPath, "utf8"));
}

const preview = generatePreviewWithoutAppMutation();

test("Grand Sport contract preview has the expected read-only contract shape", () => {
  assert.equal(preview.dataset.status, "read_only_preview");
  assert.equal(preview.dataset.model, "Grand Sport");
  assert.deepEqual(
    preview.variants.map((variant) => variant.variant_id),
    ["1lt_e07", "2lt_e07", "3lt_e07", "1lt_e67", "2lt_e67", "3lt_e67"]
  );
  assert.equal(preview.variants.every((variant) => variant.preview_included === true), true);
  assert.equal(preview.variants.every((variant) => variant.source_active === "False"), true);
  assert.equal(preview.contextChoices.length, 8);
  assert.equal(preview.steps.length, 15);
  assert.equal(preview.choices.length, 1240);
  assert.equal(preview.candidateStandardEquipment.length, 455);
});

test("all Grand Sport preview choices resolve section, step, and raw detail fields", () => {
  for (const choice of preview.choices) {
    assert.ok(choice.resolved_section_id, `${choice.choice_id} missing resolved_section_id`);
    assert.ok(choice.step_key, `${choice.choice_id} missing step_key`);
    assert.equal(typeof choice.source_detail_raw, "string", `${choice.choice_id} should preserve source_detail_raw`);
    assert.equal(typeof choice.source_option_name, "string", `${choice.choice_id} should preserve source_option_name`);
    assert.equal(typeof choice.source_description, "string", `${choice.choice_id} should preserve source_description`);
  }
  assert.equal(preview.normalization.unresolvedIssues.length, 0);
  assert.equal(preview.validation.length, 0);
});

test("Grand Sport section placement is owned by section_master step_key", () => {
  const sectionById = new Map(preview.sections.map((section) => [section.section_id, section]));
  assert.equal(sectionById.get("sec_gsha_001")?.step_key, "aero_exhaust_stripes_accessories");
  assert.equal(sectionById.get("sec_gsce_001")?.step_key, "aero_exhaust_stripes_accessories");
  assert.equal(sectionById.get("sec_exha_001")?.step_key, "packages_performance");
  assert.equal(sectionById.get("sec_whee_001")?.step_key, "wheels");
  assert.equal(sectionById.get("sec_perf_support_001")?.step_key, "wheels");
  assert.equal(sectionById.get("sec_perf_support_001")?.section_name, "Mechanical");
  assert.equal(sectionById.get("sec_perf_brake_001")?.step_key, "wheels");
  assert.equal(sectionById.get("sec_perf_z52_001")?.step_key, "packages_performance");
  assert.equal(sectionById.get("sec_perf_aero_001")?.step_key, "packages_performance");
  assert.equal(sectionById.get("sec_perf_ground_001")?.step_key, "packages_performance");
  assert.equal(sectionById.get("sec_cali_001")?.step_key, "wheels");
  assert.equal(sectionById.get("sec_lpoe_001")?.step_key, "accessories");
  assert.equal(sectionById.has("sec_lpow_001"), false, "LPO Wheels has no active Grand Sport preview choices");
  assert.equal(sectionById.get("sec_lpoi_001")?.step_key, "accessories");
});

test("filled Grand Sport source sections do not require blank-section config", () => {
  assert.deepEqual(preview.normalization.blankSectionOverrides, []);
  const choicesByRpo = new Map(preview.choices.map((choice) => [choice.rpo, choice]));
  assert.equal(choicesByRpo.get("PCQ")?.resolved_section_id, "sec_lpoe_001");
  assert.equal(choicesByRpo.get("PDY")?.resolved_section_id, "sec_lpoi_001");
  assert.equal(choicesByRpo.get("PEF")?.resolved_section_id, "sec_lpoi_001");
});

test("customer-facing text is cleaned while raw source fields stay intact", () => {
  const cfl = preview.choices.find((choice) => choice.option_id === "opt_cfl_001");
  assert.ok(cfl, "CFL should be present in Grand Sport preview choices");
  assert.equal(cfl.label, "New Extended Front Splitter Ground Effects");
  assert.equal(cfl.source_option_name, "NEW! Extended Front Splitter Ground Effects");
  assert.deepEqual(cfl.text_cleanup_notes, ["label:normalized_new_prefix"]);
});

test("rule/detail hot spot buckets are preserved for later phases", () => {
  assert.equal(preview.ruleDetailHotSpots.rows.length, 129);
  assert.equal(preview.ruleDetailHotSpots.counts.requires, 36);
  assert.equal(preview.ruleDetailHotSpots.counts.not_available, 49);
  assert.equal(preview.ruleDetailHotSpots.counts.included_with, 17);
  assert.equal(preview.ruleDetailHotSpots.counts.includes, 53);
  assert.equal(preview.ruleDetailHotSpots.counts.only, 19);
  assert.equal(preview.ruleDetailHotSpots.counts.not_recommended, 4);
  assert.equal(preview.ruleDetailHotSpots.counts.except, 2);
  assert.equal(preview.ruleDetailHotSpots.counts.special_package_review, 26);
});
