import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import fs from "node:fs";
import test from "node:test";

const previewPath = "form-output/inspection/z06-contract-preview.json";
const previewMarkdownPath = "form-output/inspection/z06-contract-preview.md";
const appDataPath = "form-app/data.js";
const expectedVariantIds = ["1lz_h07", "2lz_h07", "3lz_h07", "1lz_h67", "2lz_h67", "3lz_h67"];

function generatePreviewWithoutAppMutation() {
  const beforeAppData = fs.readFileSync(appDataPath, "utf8");
  execFileSync(".venv/bin/python", ["scripts/generate_z06_form.py"], {
    encoding: "utf8",
    stdio: "pipe",
  });
  const afterAppData = fs.readFileSync(appDataPath, "utf8");
  assert.equal(afterAppData, beforeAppData, "Z06 preview generation must not mutate form-app/data.js");
  assert.ok(fs.existsSync(previewPath), "Z06 contract preview JSON should exist");
  assert.ok(fs.existsSync(previewMarkdownPath), "Z06 contract preview Markdown should exist");
  return JSON.parse(fs.readFileSync(previewPath, "utf8"));
}

const preview = generatePreviewWithoutAppMutation();

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

test("Z06 preview unifies carbon fiber wheels into the Wheels section and keeps the package section", () => {
  const sectionsByRpo = new Map();
  for (const choice of preview.choices) {
    if (!sectionsByRpo.has(choice.rpo)) {
      sectionsByRpo.set(choice.rpo, new Set());
    }
    sectionsByRpo.get(choice.rpo).add(choice.resolved_section_id);
  }

  for (const rpo of ["PDB", "PDD", "PDF"]) {
    assert.deepEqual([...sectionsByRpo.get(rpo)].sort(), ["sec_z06_pkg_001"], `${rpo} should preview in the Z06 wheel/brake package section`);
  }
  for (const rpo of ["ROY", "ROZ", "STZ"]) {
    assert.deepEqual([...sectionsByRpo.get(rpo)].sort(), ["sec_whee_002"], `${rpo} should preview in the unified Wheels section`);
  }
  assert.deepEqual([...sectionsByRpo.get("Z07")].sort(), ["sec_perf_z52_001"], "Z07 should stay in the adjacent Z52 package section");
});
