import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import fs from "node:fs";
import test from "node:test";

import { assertTrackedArtifactsUnchanged, readTrackedArtifacts } from "./lib/tracked-artifacts.mjs";

const reviewDir = "/tmp/27vette-z06-contract-preview-test";
const outputRoot = `${reviewDir}/output-root`;
const previewPath = `${reviewDir}/z06-contract-preview.json`;
const previewMarkdownPath = `${reviewDir}/z06-contract-preview.md`;
const expectedVariantIds = ["1lz_h07", "2lz_h07", "3lz_h07", "1lz_h67", "2lz_h67", "3lz_h67"];

function generatePreviewWithoutTrackedMutation() {
  fs.rmSync(reviewDir, { recursive: true, force: true });
  fs.mkdirSync(outputRoot, { recursive: true });
  const before = readTrackedArtifacts();
  execFileSync(
    ".venv/bin/python",
    [
      "scripts/generate_form.py",
      "--model",
      "z06",
      "--output-root",
      outputRoot,
      "--emit-inspection",
      "--inspection-output",
      reviewDir,
    ],
    {
      encoding: "utf8",
      stdio: "pipe",
    }
  );
  assertTrackedArtifactsUnchanged(before);
  assert.ok(
    fs.existsSync(`${outputRoot}/form-output/runtime/z06-runtime-contract.json`),
    "--output-root must receive the runtime contract this gate would otherwise write over the tracked one"
  );
  assert.ok(fs.existsSync(previewPath), "Z06 contract preview JSON should exist");
  assert.ok(fs.existsSync(previewMarkdownPath), "Z06 contract preview Markdown should exist");
  return JSON.parse(fs.readFileSync(previewPath, "utf8"));
}

const preview = generatePreviewWithoutTrackedMutation();

test("Z06 contract preview has the expected read-only contract shape", () => {
  assert.equal(preview.dataset.status, "read_only_preview");
  assert.equal(preview.dataset.model, "Z06");
  assert.equal(preview.dataset.source_sheet, "z06_options");
  assert.deepEqual(
    preview.variants.map((variant) => variant.variant_id),
    expectedVariantIds
  );
  assert.equal(preview.variants.every((variant) => variant.preview_included === true), true);
  assert.equal(preview.variants.every((variant) => variant.source_active === "True"), true);
  assert.equal(preview.contextChoices.length, 8);
  assert.equal(preview.steps.length, 14);
  assert.equal(preview.steps.every((step) => step.source !== "fallback_config"), true);
  assert.equal(preview.orderSummary.sections.length, 12);
  assert.equal(Object.keys(preview.orderSummary.stepMap).length, 14);
  assert.equal(preview.orderSummary.stepMap.packages_performance, "performance_mechanical");
  assert.equal(preview.orderSummary.stepMap.standard_equipment, "required_charges");
  assert.ok(preview.choices.length > 0, "Z06 preview should include choices");
  assert.ok(preview.candidateStandardEquipment.length > 0, "Z06 preview should include candidate standard equipment");
});

test("all Z06 preview choices resolve section, step, and raw detail fields", () => {
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
