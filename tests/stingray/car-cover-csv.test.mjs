import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import test from "node:test";

import { createRuntime, loadGeneratedData, loadShadowData } from "./runtime-harness.mjs";

const PYTHON = ".venv/bin/python";
const SCRIPT = "scripts/stingray_csv_first_slice.py";
const CAR_COVER_RPOS = new Set(["RWH", "SL1", "WKR", "WKQ", "RNX", "RWJ"]);

function evaluate(variantId, selectedIds) {
  const output = execFileSync(PYTHON, [SCRIPT, "--scenario-json", JSON.stringify({ variant_id: variantId, selected_ids: selectedIds })], {
    cwd: process.cwd(),
    encoding: "utf8",
  });
  return JSON.parse(output);
}

function emitCsvLegacyFragment() {
  const output = execFileSync(PYTHON, [SCRIPT, "--emit-legacy-fragment"], {
    cwd: process.cwd(),
    encoding: "utf8",
    maxBuffer: 8 * 1024 * 1024,
  });
  return JSON.parse(output);
}

function plain(value) {
  return JSON.parse(JSON.stringify(value));
}

function carCoverOptionIds(data) {
  return new Set(data.choices.filter((choice) => CAR_COVER_RPOS.has(choice.rpo)).map((choice) => choice.option_id));
}

function lineById(result, selectableId) {
  return result.selected_lines.find((line) => line.selectable_id === selectableId);
}

function normalizeChoices(rows) {
  return Array.from(rows)
    .filter((choice) => CAR_COVER_RPOS.has(choice.rpo))
    .map((choice) => ({
      choice_id: choice.choice_id,
      option_id: choice.option_id,
      rpo: choice.rpo,
      label: choice.label,
      description: choice.description,
      section_id: choice.section_id,
      section_name: choice.section_name,
      category_id: choice.category_id,
      category_name: choice.category_name,
      step_key: choice.step_key,
      variant_id: choice.variant_id,
      body_style: choice.body_style,
      trim_level: choice.trim_level,
      status: choice.status,
      status_label: choice.status_label,
      selectable: choice.selectable,
      active: choice.active,
      choice_mode: choice.choice_mode,
      selection_mode: choice.selection_mode,
      selection_mode_label: choice.selection_mode_label,
      base_price: Number(choice.base_price || 0),
      display_order: Number(choice.display_order || 0),
      source_detail_raw: choice.source_detail_raw,
    }))
    .sort((a, b) => a.choice_id.localeCompare(b.choice_id));
}

function normalizeExclusiveGroups(rows, optionIds) {
  return Array.from(rows)
    .filter((group) => (group.option_ids || []).some((optionId) => optionIds.has(optionId)))
    .map((group) => ({
      group_id: group.group_id,
      option_ids: [...group.option_ids],
      selection_mode: group.selection_mode,
      active: group.active,
      notes: group.notes,
    }))
    .sort((a, b) => a.group_id.localeCompare(b.group_id));
}

function productionRulesTouching(data, rpos) {
  const ids = new Set(data.choices.filter((choice) => rpos.has(choice.rpo)).map((choice) => choice.option_id));
  return data.rules.filter((rule) => ids.has(rule.source_id) || ids.has(rule.target_id));
}

function ruleByEndpoints(data, sourceId, targetId) {
  return data.rules.find((rule) => rule.source_id === sourceId && rule.target_id === targetId);
}

function runtimeFor(data, variantId) {
  const runtime = createRuntime(data);
  const variant = data.variants.find((item) => item.variant_id === variantId);
  assert.ok(variant, `${variantId} should exist`);
  runtime.state.bodyStyle = variant.body_style;
  runtime.state.trimLevel = variant.trim_level;
  return runtime;
}

function activeChoiceByRpo(runtime, rpo) {
  const choice = runtime
    .activeChoiceRows()
    .find((item) => item.rpo === rpo && item.active === "True" && item.status !== "unavailable" && item.selectable === "True");
  assert.ok(choice, `${rpo} should have an active selectable choice`);
  return choice;
}

function handleRpo(runtime, rpo) {
  runtime.handleChoice(activeChoiceByRpo(runtime, rpo));
}

function selectedCarCoverRpos(runtime) {
  return [...runtime.state.selected]
    .map((optionId) => runtime.activeChoiceRows().find((choice) => choice.option_id === optionId)?.rpo)
    .filter((rpo) => CAR_COVER_RPOS.has(rpo))
    .sort();
}

test("CSV evaluator prices direct car-cover selections and reports car-cover exclusivity", () => {
  const result = evaluate("1lt_c07", ["opt_rwh_001", "opt_sl1_001", "opt_rnx_001", "opt_rwj_001"]);

  assert.equal(lineById(result, "opt_rwh_001")?.final_price_usd, 495);
  assert.equal(lineById(result, "opt_sl1_001")?.final_price_usd, 475);
  assert.equal(lineById(result, "opt_rnx_001")?.final_price_usd, 495);
  assert.equal(lineById(result, "opt_rwj_001")?.final_price_usd, 495);
  assert.deepEqual(
    result.conflicts.map((conflict) => ({
      exclusive_group_id: conflict.exclusive_group_id,
      member_selectable_ids: conflict.member_selectable_ids,
    })),
    [
      {
        exclusive_group_id: "excl_indoor_car_covers",
        member_selectable_ids: ["opt_rwh_001", "opt_sl1_001"],
      },
      {
        exclusive_group_id: "excl_outdoor_car_covers",
        member_selectable_ids: ["opt_rnx_001", "opt_rwj_001"],
      },
    ]
  );
});

test("CSV car-cover legacy fragment matches generated choices and exclusive groups", () => {
  const production = loadGeneratedData();
  const projected = emitCsvLegacyFragment();
  const productionOptionIds = carCoverOptionIds(production);

  assert.deepEqual(projected.validation_errors, []);
  assert.deepEqual([...carCoverOptionIds(projected)].sort(), [...productionOptionIds].sort());
  assert.deepEqual(normalizeChoices(projected.choices), normalizeChoices(production.choices));
  assert.deepEqual(normalizeExclusiveGroups(projected.exclusiveGroups, productionOptionIds), normalizeExclusiveGroups(production.exclusiveGroups, productionOptionIds));
});

test("CSV car-cover legacy fragment emits migrated 5ZW reference-target excludes", () => {
  const projected = emitCsvLegacyFragment();

  assert.deepEqual(projected.validation_errors, []);
  assert.equal(projected.choices.some((choice) => choice.rpo === "5ZW" || choice.option_id === "opt_5zw_001"), false);

  for (const [sourceId, expectedReason] of [
    ["opt_rnx_001", "Blocked by RNX LPO, Premium outdoor car cover."],
    ["opt_wkq_001", "Blocked by WKQ LPO, Premium indoor car cover."],
  ]) {
    const rule = ruleByEndpoints(projected, sourceId, "opt_5zw_001");
    assert.ok(rule, `${sourceId} should exclude opt_5zw_001`);
    assert.equal(rule.rule_type, "excludes");
    assert.equal(rule.target_section, "sec_spoi_001");
    assert.equal(rule.target_selection_mode, "multi_select_opt");
    assert.equal(rule.disabled_reason, expectedReason);
    assert.equal(rule.auto_add, "False");
    assert.equal(rule.runtime_action, "active");
  }
});

test("shadow overlay preserves production-owned car-cover cross-boundary excludes", () => {
  const production = loadGeneratedData();
  const shadow = loadShadowData();

  assert.deepEqual(plain(productionRulesTouching(shadow, CAR_COVER_RPOS)), plain(productionRulesTouching(production, CAR_COVER_RPOS)));
  assert.equal(shadow.choices.some((choice) => choice.rpo === "5ZW" || choice.option_id === "opt_5zw_001"), false);
});

test("shadow car-cover runtime exclusivity and cross-boundary blocks match production", () => {
  const production = loadGeneratedData();
  const shadow = loadShadowData();

  for (const data of [production, shadow]) {
    const indoorRuntime = runtimeFor(data, "1lt_c07");
    handleRpo(indoorRuntime, "RWH");
    handleRpo(indoorRuntime, "SL1");
    assert.deepEqual(selectedCarCoverRpos(indoorRuntime), ["SL1"]);

    const outdoorRuntime = runtimeFor(data, "1lt_c07");
    handleRpo(outdoorRuntime, "RNX");
    handleRpo(outdoorRuntime, "RWJ");
    assert.deepEqual(selectedCarCoverRpos(outdoorRuntime), ["RWJ"]);

    const wkqRuntime = runtimeFor(data, "1lt_c07");
    handleRpo(wkqRuntime, "WKQ");
    assert.match(wkqRuntime.disableReasonForChoice(activeChoiceByRpo(wkqRuntime, "5ZZ")), /Blocked by WKQ/);

    const rnxRuntime = runtimeFor(data, "1lt_c07");
    handleRpo(rnxRuntime, "RNX");
    assert.match(rnxRuntime.disableReasonForChoice(activeChoiceByRpo(rnxRuntime, "Z51")), /Blocked by RNX/);

    const z51Runtime = runtimeFor(data, "1lt_c07");
    handleRpo(z51Runtime, "Z51");
    assert.match(z51Runtime.disableReasonForChoice(activeChoiceByRpo(z51Runtime, "RNX")), /Conflicts with Z51/);
  }
});
