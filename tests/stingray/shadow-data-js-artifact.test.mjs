import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import test from "node:test";
import vm from "node:vm";

import { createRuntime, loadGeneratedData } from "./runtime-harness.mjs";

const FIRST_SLICE_RPOS = new Set(["B6P", "D3V", "SL9", "ZZ3", "BCP", "BCS", "BC4", "BC7"]);
const Z51_RPOS = new Set(["FE1", "FE2", "FE3", "Z51"]);

function plain(value) {
  return JSON.parse(JSON.stringify(value));
}

function emitJsonOverlay() {
  const output = execFileSync(".venv/bin/python", ["scripts/stingray_csv_shadow_overlay.py"], {
    cwd: process.cwd(),
    encoding: "utf8",
    maxBuffer: 8 * 1024 * 1024,
  });
  return JSON.parse(output);
}

function emitDataJsArtifact() {
  const tempDir = fs.mkdtempSync(path.join(os.tmpdir(), "stingray-shadow-data-js-"));
  const outputPath = path.join(tempDir, "form-app", "data.js");
  execFileSync(".venv/bin/python", ["scripts/stingray_csv_shadow_overlay.py", "--as-data-js", "--out", outputPath], {
    cwd: process.cwd(),
    encoding: "utf8",
  });
  const source = fs.readFileSync(outputPath, "utf8");
  fs.rmSync(tempDir, { recursive: true, force: true });
  return source;
}

function parseDataJs(source) {
  const context = { window: {} };
  vm.runInNewContext(source, context);
  assert.ok(context.window.CORVETTE_FORM_DATA, "artifact should define the production registry alias");
  assert.ok(context.window.STINGRAY_FORM_DATA, "artifact should define STINGRAY_FORM_DATA");
  assert.equal(
    context.window.STINGRAY_FORM_DATA,
    context.window.CORVETTE_FORM_DATA.models.stingray.data,
    "STINGRAY_FORM_DATA should point at the Stingray registry data"
  );
  return plain(context.window.STINGRAY_FORM_DATA);
}

function variantFor(data, variantId) {
  const variant = data.variants.find((item) => item.variant_id === variantId);
  assert.ok(variant, `${variantId} should exist`);
  return variant;
}

function runtimeFor(data, variantId, { resetDefaults = false } = {}) {
  const runtime = createRuntime(data);
  const variant = variantFor(data, variantId);
  runtime.state.bodyStyle = variant.body_style;
  runtime.state.trimLevel = variant.trim_level;
  if (resetDefaults) {
    runtime.resetDefaults();
    runtime.reconcileSelections();
  }
  return runtime;
}

function activeChoiceByRpo(runtime, rpo) {
  const choice = runtime
    .activeChoiceRows()
    .find((item) => item.rpo === rpo && item.active === "True" && item.status !== "unavailable" && item.selectable === "True");
  assert.ok(choice, `${rpo} should have an active selectable choice`);
  return choice;
}

function selectedChoiceByOptionId(runtime, optionId) {
  return runtime.activeChoiceRows().find((choice) => choice.option_id === optionId);
}

function addSelectedRpo(runtime, rpo) {
  const choice = activeChoiceByRpo(runtime, rpo);
  runtime.state.selected.add(choice.option_id);
  runtime.state.userSelected.add(choice.option_id);
  return choice;
}

function handleRpo(runtime, rpo) {
  const choice = activeChoiceByRpo(runtime, rpo);
  runtime.handleChoice(choice);
  return choice;
}

function rposFromIds(runtime, optionIds, allowedRpos) {
  return [...optionIds]
    .map((optionId) => selectedChoiceByOptionId(runtime, optionId)?.rpo)
    .filter((rpo) => rpo && allowedRpos.has(rpo))
    .sort();
}

function firstSliceScenarioFacts(data, variantId, selectedRpos) {
  const runtime = runtimeFor(data, variantId);
  const selectedChoices = selectedRpos.map((rpo) => addSelectedRpo(runtime, rpo));
  const selectedLines = selectedChoices.map((choice) => ({
    rpo: choice.rpo,
    provenance: "explicit",
    final_price_usd: runtime.optionPrice(choice.option_id),
  }));
  for (const optionId of runtime.computeAutoAdded().keys()) {
    const choice = selectedChoiceByOptionId(runtime, optionId);
    if (choice && FIRST_SLICE_RPOS.has(choice.rpo)) {
      selectedLines.push({
        rpo: choice.rpo,
        provenance: "auto",
        final_price_usd: runtime.optionPrice(optionId),
      });
    }
  }

  const openRequirements = selectedChoices
    .map((choice) => runtime.disableReasonForChoice(choice))
    .filter((message) => message.includes("Requires ZZ3"));

  return {
    selected_lines: selectedLines.sort((a, b) => `${a.rpo}:${a.provenance}`.localeCompare(`${b.rpo}:${b.provenance}`)),
    auto_added_rpos: rposFromIds(runtime, runtime.computeAutoAdded().keys(), FIRST_SLICE_RPOS),
    open_requirements: openRequirements,
  };
}

function z51ScenarioFacts(data) {
  const runtime = runtimeFor(data, "1lt_c07", { resetDefaults: true });
  handleRpo(runtime, "Z51");
  return {
    selected_rpos: rposFromIds(runtime, runtime.state.selected, Z51_RPOS),
    auto_added_rpos: rposFromIds(runtime, runtime.computeAutoAdded().keys(), Z51_RPOS),
    line_items: runtime
      .lineItems()
      .filter((item) => Z51_RPOS.has(item.rpo))
      .map((item) => ({
        rpo: item.rpo,
        label: item.label,
        price: Number(item.price || 0),
        type: item.type,
      }))
      .sort((a, b) => `${a.rpo}:${a.type}:${a.label}`.localeCompare(`${b.rpo}:${b.type}:${b.label}`)),
  };
}

const productionData = loadGeneratedData();
const jsonOverlayData = emitJsonOverlay();
const artifactData = parseDataJs(emitDataJsArtifact());

test("shadow data.js artifact parses into the production-shaped Stingray data object", () => {
  assert.deepEqual(Object.keys(artifactData).sort(), Object.keys(productionData).sort());
});

test("shadow data.js artifact data matches the default JSON overlay output", () => {
  assert.deepEqual(artifactData, jsonOverlayData);
});

const firstSliceScenarios = [
  ["coupe B6P", "1lt_c07", ["B6P"]],
  ["coupe BCP with B6P", "1lt_c07", ["BCP", "B6P"]],
  ["convertible BCP missing ZZ3", "1lt_c67", ["BCP"]],
];

for (const [name, variantId, selectedRpos] of firstSliceScenarios) {
  test(`shadow data.js artifact runtime behavior matches production: ${name}`, () => {
    assert.deepEqual(
      plain(firstSliceScenarioFacts(artifactData, variantId, selectedRpos)),
      plain(firstSliceScenarioFacts(productionData, variantId, selectedRpos))
    );
  });
}

test("shadow data.js artifact runtime behavior matches production: Z51 non-first-slice scenario", () => {
  assert.deepEqual(plain(z51ScenarioFacts(artifactData)), plain(z51ScenarioFacts(productionData)));
});
