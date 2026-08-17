// Optional inspection diagnostic for the Grand Sport contract preview.
//
// Checkpoint 2 of the fast layered validation suite (spec §9) rewrote every
// aggregate literal in this file. They were pinned counts of a mutable
// workbook: the catalog recorded one of them as stale (`requires` 25 against a
// measured 22), and rewriting them found four more — `not_available` 46 against
// 52, `includes` 41 against 40, `special_package_review` 27 against 25, and two
// buckets (`not_recommended`, `except`) that no longer occur at all. That is
// the failure mode the whole checkpoint exists to remove: a count is not a
// membership check, and refreshing it would restore green while preserving the
// defect.
//
// What replaces them, per §4.1, is structure. Membership comes from the §6.2
// workbook-truth snapshot; the hot-spot summary is checked for internal
// consistency against its own rows and for provenance against the model's
// active source rows. A valid workbook edit now moves this gate instead of
// breaking it, while a classifier that miscounts, or a preview that invents a
// row, still fails.
const MODEL_KEY = "grand_sport";

import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import fs from "node:fs";
import test from "node:test";

import { assertTrackedArtifactsUnchanged, readTrackedArtifacts } from "./lib/tracked-artifacts.mjs";
import { cell, modelSourceRows, workbookRows, workbookTruth } from "./lib/workbook-truth.mjs";

const truth = workbookTruth();
const model = truth.models[MODEL_KEY];

function activeModelRows(sheetName) {
  return workbookRows(sheetName).filter((row) => row.model_key === MODEL_KEY && row.active === "True");
}

const reviewDir = "/tmp/27vette-grand-sport-contract-preview-test";
const outputRoot = `${reviewDir}/output-root`;
const previewPath = `${reviewDir}/grand-sport-contract-preview.json`;
const previewMarkdownPath = `${reviewDir}/grand-sport-contract-preview.md`;

function generatePreviewWithoutTrackedMutation() {
  fs.rmSync(reviewDir, { recursive: true, force: true });
  fs.mkdirSync(outputRoot, { recursive: true });
  const before = readTrackedArtifacts();
  execFileSync(
    ".venv/bin/python",
    [
      "scripts/generate_form.py",
      "--model",
      "grand_sport",
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
    fs.existsSync(`${outputRoot}/form-output/runtime/grand-sport-runtime-contract.json`),
    "--output-root must receive the runtime contract this gate would otherwise write over the tracked one"
  );
  assert.ok(fs.existsSync(previewPath), "contract preview JSON should exist");
  assert.ok(fs.existsSync(previewMarkdownPath), "contract preview Markdown should exist");
  return JSON.parse(fs.readFileSync(previewPath, "utf8"));
}

const preview = generatePreviewWithoutTrackedMutation();

test("Grand Sport contract preview has the expected read-only contract shape", () => {
  assert.equal(preview.dataset.status, "read_only_preview");
  assert.equal(preview.dataset.model, model.model_label);

  assert.deepEqual(
    preview.variants.map((variant) => variant.variant_id).sort(),
    model.variants.map((variant) => variant.variant_id).sort(),
    "preview variants drifted from the model's active variant rows"
  );
  assert.equal(preview.variants.every((variant) => variant.preview_included === true), true);
  assert.equal(preview.variants.every((variant) => variant.source_active === "True"), true);

  assert.deepEqual(
    preview.steps.map((step) => step.step_key).sort(),
    activeModelRows("runtime_steps").map((row) => row.step_key).sort(),
    "preview steps drifted from the model's active runtime_steps rows"
  );
  assert.deepEqual(
    preview.orderSummary.sections.map((section) => section.section_key).sort(),
    activeModelRows("order_summary_sections").map((row) => row.section_key).sort(),
    "preview order summary drifted from order_summary_sections"
  );
  assert.deepEqual(
    Object.keys(preview.orderSummary.stepMap).sort(),
    [...new Set(activeModelRows("step_order_summary_map").map((row) => row.step_key))].sort(),
    "preview step map drifted from step_order_summary_map"
  );

  const contextSectionIds = new Set(activeModelRows("context_section_master").map((row) => row.section_id));
  assert.ok(contextSectionIds.size > 0, "the model declares no active context section");
  for (const choice of preview.contextChoices) {
    assert.equal(
      contextSectionIds.has(choice.section_id),
      true,
      `${choice.context_choice_id} names a section the model does not declare`
    );
  }
});

test("preview choices and candidate standard equipment trace to active source rows", () => {
  // Counts replaced by provenance in both directions: nothing is emitted
  // without an active source row, and standard equipment is exactly the
  // preview's own standard choices rather than a separately pinned total.
  const optionRows = new Map(modelSourceRows(MODEL_KEY, "source_option_sheet").map((row) => [row.option_id, row]));
  const variantIds = new Set(model.variants.map((variant) => variant.variant_id));

  assert.ok(preview.choices.length > 0, "preview emitted no choice");
  for (const choice of preview.choices) {
    const row = optionRows.get(choice.option_id);
    assert.ok(row, `${choice.choice_id} has no row in the model's option sheet`);
    assert.equal(row.active, "True", `${choice.choice_id} traces to an inactive option row`);
    assert.equal(variantIds.has(choice.variant_id), true, `${choice.choice_id} names an inactive variant`);
    assert.equal(cell(choice.rpo), cell(row.rpo), `${choice.choice_id} rpo`);
  }

  const pair = (choice) => `${choice.option_id}::${choice.variant_id}`;
  assert.equal(new Set(preview.choices.map(pair)).size, preview.choices.length, "duplicate preview choice");
  assert.deepEqual(
    preview.candidateStandardEquipment.map(pair).sort(),
    preview.choices.filter((choice) => choice.status === "standard").map(pair).sort(),
    "candidate standard equipment drifted from the preview's own standard choices"
  );
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
  assert.equal(cfl.label, "Extended Front Splitter, Carbon Flash");
  assert.equal(cfl.source_option_name, "Extended Front Splitter, Carbon Flash");
  assert.deepEqual(cfl.text_cleanup_notes, []);
});

test("rule/detail hot spot buckets summarize exactly the rows they classify", () => {
  const hotSpots = preview.ruleDetailHotSpots;
  assert.ok(hotSpots.rows.length > 0, "the classifier bucketed nothing, so its summary proves nothing");

  // The counts are a summary of `rows`. Recomputing them from those rows is not
  // circular — it is the only thing a count can be checked against without
  // reimplementing the classifier's own patterns, and it fails for the two
  // defects a pinned number cannot distinguish: a counter that drifts from the
  // rows, and a bucket dropped from one side only.
  const recomputed = new Map();
  for (const row of hotSpots.rows) {
    for (const term of row.matched_terms) {
      recomputed.set(term, (recomputed.get(term) ?? 0) + 1);
    }
  }
  assert.deepEqual(
    Object.fromEntries([...recomputed].sort()),
    Object.fromEntries(Object.entries(hotSpots.counts).sort()),
    "hot-spot counts drifted from the rows they summarize"
  );

  // Every bucketed row is a row of this model, and it is bucketed for a reason
  // the record itself carries.
  const optionRows = new Map(modelSourceRows(MODEL_KEY, "source_option_sheet").map((row) => [row.option_id, row]));
  for (const row of hotSpots.rows) {
    const source = optionRows.get(row.option_id);
    assert.ok(source, `${row.option_id} is bucketed but absent from the model's option sheet`);
    assert.equal(cell(row.rpo), cell(source.rpo), `${row.option_id} rpo`);
    assert.equal(
      row.matched_terms.length > 0 || row.special_mentions.length > 0,
      true,
      `${row.option_id} is bucketed with neither a matched term nor a special mention`
    );
  }

  // The one behavioral expectation left: the D84 detail text those five DM*
  // wheel RPOs used to carry was corrected in the workbook, and nothing should
  // reintroduce it. This is an authored-copy statement, not an aggregate.
  assert.equal(
    hotSpots.rows.some(
      (row) => ["DMU", "DMV", "DMW", "DMX", "DMY"].includes(row.rpo) && /Requires \(D84\)/.test(row.detail_raw)
    ),
    false
  );
});
