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
const SUEDE_TRUNK_LINER_RPOS = new Set(["SXB", "SXR", "SXT"]);
const CAR_COVER_RPOS = new Set(["RWH", "SL1", "WKR", "WKQ", "RNX", "RWJ"]);

function plain(value) {
  return JSON.parse(JSON.stringify(value));
}

function runBuild() {
  const tempRoot = fs.mkdtempSync(path.join(os.tmpdir(), "stingray-experimental-app-"));
  const outDir = path.join(tempRoot, "form-app");
  execFileSync(".venv/bin/python", ["scripts/build_stingray_experimental_app.py", "--out-dir", outDir], {
    cwd: process.cwd(),
    encoding: "utf8",
  });
  return { tempRoot, outDir };
}

function directDataJsOutput() {
  return execFileSync(".venv/bin/python", ["scripts/stingray_csv_shadow_overlay.py", "--as-data-js"], {
    cwd: process.cwd(),
    encoding: "utf8",
    maxBuffer: 8 * 1024 * 1024,
  });
}

function directJsonOverlay() {
  const output = execFileSync(".venv/bin/python", ["scripts/stingray_csv_shadow_overlay.py"], {
    cwd: process.cwd(),
    encoding: "utf8",
    maxBuffer: 8 * 1024 * 1024,
  });
  return JSON.parse(output);
}

function parseDataJs(source) {
  const context = { window: {} };
  vm.runInNewContext(source, context);
  assert.ok(context.window.CORVETTE_FORM_DATA, "experimental data.js should define CORVETTE_FORM_DATA");
  assert.ok(context.window.STINGRAY_FORM_DATA, "experimental data.js should define STINGRAY_FORM_DATA");
  assert.equal(context.window.STINGRAY_FORM_DATA, context.window.CORVETTE_FORM_DATA.models.stingray.data);
  return plain(context.window.STINGRAY_FORM_DATA);
}

function runtimeFor(data, variantId, { resetDefaults = false } = {}) {
  const runtime = createRuntime(data);
  const variant = data.variants.find((item) => item.variant_id === variantId);
  assert.ok(variant, `${variantId} should exist`);
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

function suedeTrunkLinerScenarioFacts(data) {
  const runtime = runtimeFor(data, "1lt_c07");
  for (const rpo of ["SXB", "SXR", "SXT"]) {
    handleRpo(runtime, rpo);
  }
  return {
    selected_rpos: rposFromIds(runtime, runtime.state.selected, SUEDE_TRUNK_LINER_RPOS),
    line_items: runtime
      .lineItems()
      .filter((item) => SUEDE_TRUNK_LINER_RPOS.has(item.rpo))
      .map((item) => ({
        rpo: item.rpo,
        label: item.label,
        price: Number(item.price || 0),
        type: item.type,
      }))
      .sort((a, b) => `${a.rpo}:${a.type}:${a.label}`.localeCompare(`${b.rpo}:${b.type}:${b.label}`)),
  };
}

function carCoverScenarioFacts(data) {
  const indoorRuntime = runtimeFor(data, "1lt_c07");
  handleRpo(indoorRuntime, "RWH");
  handleRpo(indoorRuntime, "SL1");

  const outdoorRuntime = runtimeFor(data, "1lt_c07");
  handleRpo(outdoorRuntime, "RNX");
  handleRpo(outdoorRuntime, "RWJ");

  const wkqRuntime = runtimeFor(data, "1lt_c07");
  handleRpo(wkqRuntime, "WKQ");

  const rnxRuntime = runtimeFor(data, "1lt_c07");
  handleRpo(rnxRuntime, "RNX");

  const z51Runtime = runtimeFor(data, "1lt_c07");
  handleRpo(z51Runtime, "Z51");

  return {
    indoor_selected_rpos: rposFromIds(indoorRuntime, indoorRuntime.state.selected, CAR_COVER_RPOS),
    outdoor_selected_rpos: rposFromIds(outdoorRuntime, outdoorRuntime.state.selected, CAR_COVER_RPOS),
    wkq_5zz_reason: wkqRuntime.disableReasonForChoice(activeChoiceByRpo(wkqRuntime, "5ZZ")),
    rnx_z51_reason: rnxRuntime.disableReasonForChoice(activeChoiceByRpo(rnxRuntime, "Z51")),
    z51_rnx_reason: z51Runtime.disableReasonForChoice(activeChoiceByRpo(z51Runtime, "RNX")),
  };
}

const productionData = loadGeneratedData();
const jsonOverlayData = directJsonOverlay();
const directDataJs = directDataJsOutput();
const { tempRoot, outDir } = runBuild();

test.after(() => {
  fs.rmSync(tempRoot, { recursive: true, force: true });
});

test("experimental app shell contains copied shell files and generated data.js", () => {
  for (const filename of ["index.html", "app.js", "styles.css", "data.js"]) {
    assert.equal(fs.existsSync(path.join(outDir, filename)), true, `${filename} should exist`);
  }
});

test("experimental app shell copies production shell files byte-for-byte", () => {
  for (const filename of ["index.html", "app.js", "styles.css"]) {
    assert.equal(
      fs.readFileSync(path.join(outDir, filename), "utf8"),
      fs.readFileSync(path.join("form-app", filename), "utf8"),
      `${filename} should be copied without transformation`
    );
  }
});

test("experimental app shell data.js comes from the shadow overlay data.js output", () => {
  const builtDataJs = fs.readFileSync(path.join(outDir, "data.js"), "utf8");
  assert.notEqual(builtDataJs, fs.readFileSync("form-app/data.js", "utf8"));
  assert.equal(builtDataJs, directDataJs);
});

test("experimental app shell index keeps static app script references", () => {
  const html = fs.readFileSync(path.join(outDir, "index.html"), "utf8");
  assert.match(html, /href="\.\/styles\.css"/);
  assert.match(html, /src="\.\/data\.js\?v=6"/);
  assert.match(html, /src="\.\/app\.js\?v=6"/);
});

const experimentalData = parseDataJs(fs.readFileSync(path.join(outDir, "data.js"), "utf8"));

test("experimental app shell data.js parses to the JSON shadow overlay data", () => {
  assert.deepEqual(experimentalData, jsonOverlayData);
});

const firstSliceScenarios = [
  ["coupe B6P", "1lt_c07", ["B6P"]],
  ["coupe BCP with B6P", "1lt_c07", ["BCP", "B6P"]],
  ["convertible BCP missing ZZ3", "1lt_c67", ["BCP"]],
];

for (const [name, variantId, selectedRpos] of firstSliceScenarios) {
  test(`experimental app shell runtime behavior matches production: ${name}`, () => {
    assert.deepEqual(
      plain(firstSliceScenarioFacts(experimentalData, variantId, selectedRpos)),
      plain(firstSliceScenarioFacts(productionData, variantId, selectedRpos))
    );
  });
}

test("experimental app shell runtime behavior matches production: Z51 non-first-slice scenario", () => {
  assert.deepEqual(plain(z51ScenarioFacts(experimentalData)), plain(z51ScenarioFacts(productionData)));
});

test("experimental app shell runtime behavior matches production: suede trunk liner exclusivity", () => {
  assert.deepEqual(plain(suedeTrunkLinerScenarioFacts(experimentalData)), plain(suedeTrunkLinerScenarioFacts(productionData)));
});

test("experimental app shell runtime behavior matches production: car cover exclusivity and cross-boundary blocks", () => {
  assert.deepEqual(plain(carCoverScenarioFacts(experimentalData)), plain(carCoverScenarioFacts(productionData)));
});
