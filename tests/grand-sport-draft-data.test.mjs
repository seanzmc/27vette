import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import fs from "node:fs";
import test from "node:test";

const draftPath = "form-output/inspection/grand-sport-form-data-draft.json";
const draftMarkdownPath = "form-output/inspection/grand-sport-form-data-draft.md";
const appDataPath = "form-app/data.js";

function generateDraftWithoutAppMutation() {
  const beforeAppData = fs.readFileSync(appDataPath, "utf8");
  execFileSync(".venv/bin/python", ["scripts/generate_grand_sport_form.py"], {
    encoding: "utf8",
    stdio: "pipe",
  });
  const afterAppData = fs.readFileSync(appDataPath, "utf8");
  assert.equal(afterAppData, beforeAppData, "Grand Sport draft generation must not mutate form-app/data.js");
  assert.ok(fs.existsSync(draftPath), "Grand Sport draft JSON should exist");
  assert.ok(fs.existsSync(draftMarkdownPath), "Grand Sport draft Markdown should exist");
  return JSON.parse(fs.readFileSync(draftPath, "utf8"));
}

const draft = generateDraftWithoutAppMutation();

test("Grand Sport draft preserves the live generated-data top-level contract", () => {
  for (const key of [
    "dataset",
    "variants",
    "steps",
    "sections",
    "contextChoices",
    "choices",
    "standardEquipment",
    "ruleGroups",
    "exclusiveGroups",
    "rules",
    "priceRules",
    "interiors",
    "colorOverrides",
    "validation",
  ]) {
    assert.ok(Object.hasOwn(draft, key), `draft is missing ${key}`);
  }
  assert.equal(draft.dataset.status, "draft_not_runtime_active");
  assert.equal(draft.dataset.model, "Grand Sport");
  assert.deepEqual(
    draft.variants.map((variant) => variant.variant_id),
    ["1lt_e07", "2lt_e07", "3lt_e07", "1lt_e67", "2lt_e67", "3lt_e67"]
  );
});

test("Grand Sport draft includes the full variant matrix and standard equipment rows", () => {
  assert.equal(draft.variants.length, 6);
  assert.equal(draft.contextChoices.length, 8);
  assert.equal(draft.steps.length, 14);
  assert.equal(draft.choices.length, 1614);
  assert.equal(draft.standardEquipment.length, 545);
  assert.equal(draft.choices.filter((choice) => choice.status === "available").length, 873);
  assert.equal(draft.choices.filter((choice) => choice.status === "standard").length, 545);
  assert.equal(draft.choices.filter((choice) => choice.status === "unavailable").length, 196);
});

test("Grand Sport draft defers non-normalized surfaces with explicit validation warnings", () => {
  assert.deepEqual(draft.ruleGroups, []);
  assert.deepEqual(draft.exclusiveGroups, []);
  assert.deepEqual(draft.rules, []);
  assert.deepEqual(draft.priceRules, []);
  assert.deepEqual(draft.interiors, []);
  assert.deepEqual(draft.colorOverrides, []);
  const warnings = new Set(draft.validation.filter((row) => row.severity === "warning").map((row) => row.check_id));
  assert.ok(warnings.has("grand_sport_draft_status"));
  assert.ok(warnings.has("rules_deferred"));
  assert.ok(warnings.has("interiors_deferred"));
  assert.ok(warnings.has("pricing_deferred"));
});

test("Grand Sport draft keeps normalized display fields and raw rule evidence", () => {
  const cfl = draft.choices.find((choice) => choice.choice_id === "1lt_e07__opt_cfl_001");
  assert.ok(cfl, "CFL should be present in the draft");
  assert.equal(cfl.label, "New Ground Effects");
  assert.equal(cfl.source_option_name, "NEW!  Ground effects");
  assert.equal(cfl.source_detail_raw, "1. Not available with (CFV/CFZ) ground effects.");
  assert.equal(cfl.step_key, "packages_performance");
  assert.equal(cfl.category_id, "cat_mech_001");
});

test("Grand Sport draft preserves rule hot spots and normalization metadata for later phases", () => {
  assert.equal(draft.draftMetadata.candidateAvailableOrStandardChoices, 1418);
  assert.equal(draft.draftMetadata.fullVariantMatrixChoices, 1614);
  assert.equal(draft.draftMetadata.ruleDetailHotSpots.rows.length, 123);
  assert.equal(draft.draftMetadata.ruleDetailHotSpots.counts.special_package_review, 26);
  assert.equal(draft.draftMetadata.normalization.sectionCategoryResolutions.length, 55);
  assert.equal(draft.draftMetadata.normalization.unresolvedIssues.length, 0);
  assert.deepEqual(draft.draftMetadata.deferredSurfaces, [
    "ruleGroups",
    "exclusiveGroups",
    "rules",
    "priceRules",
    "interiors",
    "colorOverrides",
  ]);
});

