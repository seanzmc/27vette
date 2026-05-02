import assert from "node:assert/strict";
import test from "node:test";

import { createRuntime, loadGeneratedData, loadShadowData } from "./runtime-harness.mjs";

const FIRST_SLICE_RPOS = new Set(["B6P", "D3V", "SL9", "ZZ3", "BCP", "BCS", "BC4", "BC7"]);
const CAR_COVER_RPOS = new Set(["RWH", "SL1", "WKR", "WKQ", "RNX", "RWJ"]);

const productionData = loadGeneratedData();
const shadowData = loadShadowData();

function variantFor(data, variantId) {
  const variant = data.variants.find((item) => item.variant_id === variantId);
  assert.ok(variant, `${variantId} should exist`);
  return variant;
}

function plain(value) {
  return JSON.parse(JSON.stringify(value));
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

function activeChoiceByRpo(runtime, rpo, { stepKey = "", selectable = true } = {}) {
  const choices = runtime
    .activeChoiceRows()
    .filter((choice) => choice.rpo === rpo && choice.active === "True" && choice.status !== "unavailable")
    .filter((choice) => !stepKey || choice.step_key === stepKey)
    .filter((choice) => !selectable || choice.selectable === "True");
  assert.ok(choices.length > 0, `${rpo} should have an active choice in the current variant`);
  return choices[0];
}

function selectedChoiceByOptionId(runtime, optionId) {
  return runtime.activeChoiceRows().find((choice) => choice.option_id === optionId);
}

function addSelectedRpo(runtime, rpo, options = {}) {
  const choice = activeChoiceByRpo(runtime, rpo, options);
  runtime.state.selected.add(choice.option_id);
  runtime.state.userSelected.add(choice.option_id);
  return choice;
}

function handleRpo(runtime, rpo, options = {}) {
  const choice = activeChoiceByRpo(runtime, rpo, options);
  runtime.handleChoice(choice);
  return choice;
}

function rposFromIds(runtime, optionIds, allowedRpos = null) {
  return [...optionIds]
    .map((optionId) => selectedChoiceByOptionId(runtime, optionId)?.rpo)
    .filter((rpo) => rpo && (!allowedRpos || allowedRpos.has(rpo)))
    .sort();
}

function autoAddedRpos(runtime, allowedRpos = null) {
  return rposFromIds(runtime, runtime.computeAutoAdded().keys(), allowedRpos);
}

function lineItemFacts(runtime, allowedRpos = null) {
  return runtime
    .lineItems()
    .filter((item) => !allowedRpos || allowedRpos.has(item.rpo))
    .map((item) => ({
      rpo: item.rpo,
      label: item.label,
      price: Number(item.price || 0),
      type: item.type,
      section_label: item.section_label,
    }))
    .sort((a, b) => `${a.rpo}:${a.type}:${a.label}`.localeCompare(`${b.rpo}:${b.type}:${b.label}`));
}

function firstSliceFacts(data, runtime, selectedRpos) {
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

  const ls6Ids = new Set(
    runtime
      .activeChoiceRows()
      .filter((choice) => FIRST_SLICE_RPOS.has(choice.rpo))
      .map((choice) => choice.option_id)
  );
  const ls6Group = data.exclusiveGroups.find((group) => (group.option_ids || []).some((optionId) => ls6Ids.has(optionId)));
  const selectedLs6Rpos = selectedChoices
    .filter((choice) => ls6Group?.option_ids?.includes(choice.option_id))
    .map((choice) => choice.rpo)
    .sort();

  return {
    selected_lines: selectedLines.sort((a, b) => `${a.rpo}:${a.provenance}`.localeCompare(`${b.rpo}:${b.provenance}`)),
    auto_added_rpos: autoAddedRpos(runtime, FIRST_SLICE_RPOS),
    open_requirements: openRequirements,
    conflicts: selectedLs6Rpos.length > 1 ? [{ member_rpos: selectedLs6Rpos }] : [],
  };
}

function normalizedCompactOrder(runtime) {
  const compact = runtime.compactOrder();
  return {
    ...compact,
    submitted_at: "<timestamp>",
    sections: compact.sections.map((section) => ({
      section: section.section,
      items: section.items.map((item) => ({
        rpo: item.rpo,
        label: item.label,
        price: Number(item.price || 0),
      })),
    })),
  };
}

function normalizedExportJson(runtime) {
  runtime.exportJson();
  const download = runtime.downloads.at(-1);
  assert.equal(download.filename, "stingray-order-summary.json");
  const parsed = JSON.parse(download.content);
  return {
    ...parsed,
    submitted_at: "<timestamp>",
  };
}

function exportCsvFacts(runtime) {
  runtime.exportCsv();
  const download = runtime.downloads.at(-1);
  assert.equal(download.filename, "stingray-order-summary.csv");
  return {
    type: download.type,
    lines: download.content.trim().split("\n"),
  };
}

function orderOutputScenario(data) {
  const runtime = runtimeFor(data, "1lt_c07", { resetDefaults: true });
  runtime.state.customer.name = "Ada Buyer";
  runtime.state.customer.email = "ada@example.com";
  runtime.state.customer.phone = "555-0100";
  runtime.state.customer.address = "1 Corvette Way";
  runtime.state.customer.comments = "Dealer follow-up requested.";
  handleRpo(runtime, "GBA");
  handleRpo(runtime, "Z51");
  runtime.state.selectedInterior = "1LT_AQ9_HTA";

  const order = runtime.currentOrder();
  return {
    pricing: order.pricing,
    selected_options: order.selected_options.map((item) => ({
      rpo: item.rpo,
      label: item.label,
      price: Number(item.price || 0),
      type: item.type,
      step_key: item.step_key,
    })),
    auto_added_options: order.auto_added_options.map((item) => ({
      rpo: item.rpo,
      label: item.label,
      price: Number(item.price || 0),
      type: item.type,
      step_key: item.step_key,
    })),
    selected_interior: {
      rpo: order.selected_interior.rpo,
      label: order.selected_interior.label,
      price: Number(order.selected_interior.price || 0),
      type: order.selected_interior.type,
    },
    section_labels: order.sections.map((section) => section.section_label),
    compact: normalizedCompactOrder(runtime),
    export_json: normalizedExportJson(runtime),
    export_csv: exportCsvFacts(runtime),
  };
}

function z51Scenario(data) {
  const runtime = runtimeFor(data, "1lt_c07", { resetDefaults: true });
  handleRpo(runtime, "Z51");
  return {
    selected_rpos: rposFromIds(runtime, runtime.state.selected, new Set(["FE1", "FE2", "FE3", "Z51"])),
    auto_added_rpos: autoAddedRpos(runtime, new Set(["FE1", "FE2", "FE3", "Z51"])),
    line_items: lineItemFacts(runtime, new Set(["FE1", "FE2", "FE3", "Z51"])),
  };
}

function zz3DefaultReplacementScenario(data) {
  const runtime = runtimeFor(data, "1lt_c67", { resetDefaults: true });
  handleRpo(runtime, "ZZ3");
  const beforeReplacement = autoAddedRpos(runtime, FIRST_SLICE_RPOS);
  handleRpo(runtime, "BCP");
  return {
    before_replacement_auto_added_rpos: beforeReplacement,
    selected_rpos: rposFromIds(runtime, runtime.state.selected, FIRST_SLICE_RPOS),
    user_selected_rpos: rposFromIds(runtime, runtime.state.userSelected, FIRST_SLICE_RPOS),
    auto_added_rpos: autoAddedRpos(runtime, FIRST_SLICE_RPOS),
    line_items: lineItemFacts(runtime, FIRST_SLICE_RPOS),
  };
}

function spoilerExclusiveScenario(data) {
  const spoilerRpos = new Set(["T0A", "TVS", "5ZZ", "5ZU"]);
  const runtime = runtimeFor(data, "1lt_c07", { resetDefaults: true });
  handleRpo(runtime, "GBA");
  handleRpo(runtime, "Z51");
  for (const rpo of ["T0A", "5ZZ", "5ZU"]) {
    addSelectedRpo(runtime, rpo);
  }
  handleRpo(runtime, "TVS");
  return {
    selected_rpos: rposFromIds(runtime, runtime.state.selected, spoilerRpos),
    user_selected_rpos: rposFromIds(runtime, runtime.state.userSelected, spoilerRpos),
    line_items: lineItemFacts(runtime, spoilerRpos),
  };
}

function accessoryExclusiveScenario(data) {
  const centerCapRpos = new Set(["RXJ", "VWD", "5ZD", "5ZC", "RXH"]);
  const runtime = runtimeFor(data, "1lt_c07");
  for (const rpo of ["RXJ", "5ZD", "5ZC", "RXH"]) {
    addSelectedRpo(runtime, rpo);
  }
  handleRpo(runtime, "VWD");
  return {
    selected_rpos: rposFromIds(runtime, runtime.state.selected, centerCapRpos),
    user_selected_rpos: rposFromIds(runtime, runtime.state.userSelected, centerCapRpos),
    line_items: lineItemFacts(runtime, centerCapRpos),
  };
}

function suedeTrunkLinerExclusiveScenario(data) {
  const suedeTrunkLinerRpos = new Set(["SXB", "SXR", "SXT"]);
  const runtime = runtimeFor(data, "1lt_c07");
  for (const rpo of ["SXB", "SXR"]) {
    addSelectedRpo(runtime, rpo);
  }
  handleRpo(runtime, "SXT");
  return {
    selected_rpos: rposFromIds(runtime, runtime.state.selected, suedeTrunkLinerRpos),
    user_selected_rpos: rposFromIds(runtime, runtime.state.userSelected, suedeTrunkLinerRpos),
    line_items: lineItemFacts(runtime, suedeTrunkLinerRpos),
  };
}

function carCoverScenario(data) {
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

function groupedRequirementScenario(data) {
  const runtime = runtimeFor(data, "1lt_c07", { resetDefaults: true });
  handleRpo(runtime, "Z51");
  const fiveV7 = activeChoiceByRpo(runtime, "5V7");
  const before = runtime.disableReasonForChoice(fiveV7);
  handleRpo(runtime, "5ZZ");
  const after = runtime.disableReasonForChoice(fiveV7);
  return {
    requirement_before: before,
    requirement_after: after,
  };
}

const firstSliceScenarios = [
  ["coupe B6P", "1lt_c07", ["B6P"]],
  ["coupe BCP", "1lt_c07", ["BCP"]],
  ["coupe BCP with B6P", "1lt_c07", ["BCP", "B6P"]],
  ["convertible BCP missing ZZ3", "1lt_c67", ["BCP"]],
  ["convertible BCP with ZZ3", "1lt_c67", ["BCP", "ZZ3"]],
  ["coupe BCP with BC4", "1lt_c07", ["BCP", "BC4"]],
];

test("shadow data keeps the production-shaped top-level contract", () => {
  assert.deepEqual(Object.keys(shadowData).sort(), Object.keys(productionData).sort());
});

for (const [name, variantId, selectedRpos] of firstSliceScenarios) {
  test(`shadow regression matches production first-slice behavior: ${name}`, () => {
    assert.deepEqual(
      plain(firstSliceFacts(shadowData, runtimeFor(shadowData, variantId), selectedRpos)),
      plain(firstSliceFacts(productionData, runtimeFor(productionData, variantId), selectedRpos))
    );
  });
}

const broadScenarios = [
  ["ZZ3 default BC7 replacement by BCP", zz3DefaultReplacementScenario],
  ["Z51 default replacement and FE3 auto-add", z51Scenario],
  ["spoiler exclusive group replacement", spoilerExclusiveScenario],
  ["center cap accessory exclusive group replacement", accessoryExclusiveScenario],
  ["suede trunk liner exclusive group replacement", suedeTrunkLinerExclusiveScenario],
  ["car cover exclusivity and cross-boundary blocks", carCoverScenario],
  ["5V7 grouped spoiler requirement", groupedRequirementScenario],
  ["current order, compact order, and exports", orderOutputScenario],
];

for (const [name, scenario] of broadScenarios) {
  test(`shadow regression matches production: ${name}`, () => {
    assert.deepEqual(plain(scenario(shadowData)), plain(scenario(productionData)));
  });
}
