import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import fs from "node:fs";
import test from "node:test";
import vm from "node:vm";

const FIRST_SLICE_RPOS = new Set(["B6P", "D3V", "SL9", "ZZ3", "BCP", "BCS", "BC4", "BC7", "PEF", "CAV", "RIA"]);

function loadGeneratedData() {
  const context = { window: {} };
  vm.runInNewContext(fs.readFileSync("form-app/data.js", "utf8"), context);
  return context.window.STINGRAY_FORM_DATA;
}

function emitCsvLegacyFragment() {
  const output = execFileSync(".venv/bin/python", ["scripts/stingray_csv_first_slice.py", "--emit-legacy-fragment"], {
    cwd: process.cwd(),
    encoding: "utf8",
  });
  return JSON.parse(output);
}

function emitShadowData() {
  const output = execFileSync(".venv/bin/python", ["scripts/stingray_csv_shadow_overlay.py"], {
    cwd: process.cwd(),
    encoding: "utf8",
    maxBuffer: 8 * 1024 * 1024,
  });
  return JSON.parse(output);
}

function makeElement() {
  return {
    textContent: "",
    innerHTML: "",
    dataset: {},
    addEventListener() {},
    querySelectorAll() {
      return [];
    },
    querySelector() {
      return null;
    },
    closest() {
      return makeElement();
    },
    scrollTo() {},
  };
}

function loadRuntime(data) {
  const context = {
    window: {
      STINGRAY_FORM_DATA: data,
      scrollX: 0,
      scrollY: 0,
      scrollTo() {},
    },
    document: {
      querySelector() {
        return makeElement();
      },
      createElement() {
        return makeElement();
      },
    },
    Intl,
    Number,
    Set,
    Map,
    Boolean,
    Object,
    String,
    URL: {
      createObjectURL() {
        return "";
      },
      revokeObjectURL() {},
    },
    Blob: class TestBlob {},
  };
  const source = fs.readFileSync("form-app/app.js", "utf8").replace(
    /\ninit\(\);\s*$/,
    `
window.__testApi = {
  state,
  activeChoiceRows,
  computeAutoAdded,
  disableReasonForChoice,
  optionPrice,
};
`
  );
  vm.runInNewContext(source, context);
  return context.window.__testApi;
}

function firstSliceOptionIds(data) {
  return new Set(data.choices.filter((choice) => FIRST_SLICE_RPOS.has(choice.rpo)).map((choice) => choice.option_id));
}

function normalizeChoices(rows) {
  return Array.from(rows)
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

function normalizeVariants(rows) {
  return Array.from(rows)
    .map((variant) => ({
      variant_id: variant.variant_id,
      model_year: Number(variant.model_year || 0),
      trim_level: variant.trim_level,
      body_style: variant.body_style,
      display_name: variant.display_name,
      base_price: Number(variant.base_price || 0),
      display_order: Number(variant.display_order || 0),
    }))
    .sort((a, b) => a.display_order - b.display_order);
}

function normalizeRules(rows) {
  return Array.from(rows)
    .map((rule) => ({
      source_id: rule.source_id,
      rule_type: rule.rule_type,
      target_id: rule.target_id,
      target_type: rule.target_type,
      source_type: rule.source_type,
      source_section: rule.source_section,
      target_section: rule.target_section,
      source_selection_mode: rule.source_selection_mode,
      target_selection_mode: rule.target_selection_mode,
      body_style_scope: rule.body_style_scope,
      disabled_reason: rule.disabled_reason,
      auto_add: rule.auto_add,
      active: rule.active,
      runtime_action: rule.runtime_action,
      review_flag: rule.review_flag,
    }))
    .sort((a, b) => `${a.source_id}:${a.rule_type}:${a.target_id}:${a.body_style_scope}`.localeCompare(`${b.source_id}:${b.rule_type}:${b.target_id}:${b.body_style_scope}`));
}

function normalizePriceRules(rows) {
  return Array.from(rows)
    .map((rule) => ({
      condition_option_id: rule.condition_option_id,
      target_option_id: rule.target_option_id,
      price_rule_type: rule.price_rule_type,
      price_value: Number(rule.price_value || 0),
      body_style_scope: rule.body_style_scope,
      trim_level_scope: rule.trim_level_scope,
      variant_scope: rule.variant_scope,
      review_flag: rule.review_flag,
    }))
    .sort((a, b) => `${a.condition_option_id}:${a.target_option_id}:${a.body_style_scope}:${a.price_value}`.localeCompare(`${b.condition_option_id}:${b.target_option_id}:${b.body_style_scope}:${b.price_value}`));
}

function normalizeExclusiveGroups(rows) {
  return Array.from(rows)
    .map((group) => ({
      group_id: group.group_id,
      option_ids: [...(group.option_ids || [])],
      selection_mode: group.selection_mode,
      active: group.active,
      notes: group.notes,
    }))
    .sort((a, b) => a.group_id.localeCompare(b.group_id));
}

function nonFirstSliceSlices(data, firstSliceIds) {
  return {
    choices: normalizeChoices(data.choices.filter((choice) => !FIRST_SLICE_RPOS.has(choice.rpo))),
    rules: normalizeRules(data.rules.filter((rule) => !firstSliceIds.has(rule.source_id) && !firstSliceIds.has(rule.target_id))),
    priceRules: normalizePriceRules(
      data.priceRules.filter((rule) => !firstSliceIds.has(rule.condition_option_id) && !firstSliceIds.has(rule.target_option_id))
    ),
    exclusiveGroups: normalizeExclusiveGroups(
      data.exclusiveGroups.filter((group) => !(group.option_ids || []).some((optionId) => firstSliceIds.has(optionId)))
    ),
  };
}

function activeOptionIdForRpo(runtime, rpo) {
  const choice = runtime.activeChoiceRows().find(
    (item) => item.rpo === rpo && item.active === "True" && item.status !== "unavailable"
  );
  assert.ok(choice, `${rpo} should have an active generated choice for the scenario variant`);
  return choice.option_id;
}

function choiceForOptionId(runtime, optionId) {
  return runtime.activeChoiceRows().find((choice) => choice.option_id === optionId);
}

function runScenario(data, scenario) {
  const runtime = loadRuntime(data);
  const variant = data.variants.find((item) => item.variant_id === scenario.variantId);
  assert.ok(variant, `${scenario.variantId} should exist`);
  runtime.state.bodyStyle = variant.body_style;
  runtime.state.trimLevel = variant.trim_level;

  const selectedIds = scenario.rpos.map((rpo) => activeOptionIdForRpo(runtime, rpo));
  for (const optionId of selectedIds) {
    runtime.state.selected.add(optionId);
    runtime.state.userSelected.add(optionId);
  }

  const autoAdded = runtime.computeAutoAdded();
  const selectedLines = [];
  for (const optionId of selectedIds) {
    const choice = choiceForOptionId(runtime, optionId);
    selectedLines.push({
      rpo: choice.rpo,
      provenance: ["explicit"],
      final_price_usd: runtime.optionPrice(optionId),
    });
  }
  for (const optionId of autoAdded.keys()) {
    const choice = choiceForOptionId(runtime, optionId);
    if (choice && FIRST_SLICE_RPOS.has(choice.rpo)) {
      selectedLines.push({
        rpo: choice.rpo,
        provenance: ["auto"],
        final_price_usd: runtime.optionPrice(optionId),
      });
    }
  }

  const openRequirements = selectedIds
    .map((optionId) => choiceForOptionId(runtime, optionId))
    .filter(Boolean)
    .map((choice) => runtime.disableReasonForChoice(choice))
    .filter((message) => message.includes("Requires ZZ3"));

  const firstSliceIds = firstSliceOptionIds(data);
  const ls6Group = data.exclusiveGroups.find((group) => (group.option_ids || []).some((optionId) => firstSliceIds.has(optionId)));
  const selectedLs6Ids = selectedIds.filter((optionId) => ls6Group?.option_ids?.includes(optionId));

  return {
    selected_lines: selectedLines
      .filter((line) => FIRST_SLICE_RPOS.has(line.rpo))
      .sort((a, b) => a.rpo.localeCompare(b.rpo)),
    auto_added_rpos: [...autoAdded.keys()]
      .map((optionId) => choiceForOptionId(runtime, optionId)?.rpo)
      .filter((rpo) => FIRST_SLICE_RPOS.has(rpo))
      .sort(),
    open_requirements: openRequirements,
    conflicts:
      selectedLs6Ids.length > 1
        ? [
            {
              member_rpos: selectedLs6Ids.map((optionId) => choiceForOptionId(runtime, optionId)?.rpo),
            },
          ]
        : [],
  };
}

const productionData = loadGeneratedData();
const csvFragment = emitCsvLegacyFragment();
const shadowData = emitShadowData();

test("shadow assembly preserves all non-first-slice legacy records", () => {
  const productionIds = firstSliceOptionIds(productionData);
  const shadowIds = firstSliceOptionIds(shadowData);
  assert.deepEqual(nonFirstSliceSlices(shadowData, shadowIds), nonFirstSliceSlices(productionData, productionIds));
  assert.deepEqual(normalizeVariants(shadowData.variants), normalizeVariants(productionData.variants));
  assert.deepEqual(JSON.parse(JSON.stringify(shadowData.ruleGroups)), JSON.parse(JSON.stringify(productionData.ruleGroups)));
});

test("shadow assembly substitutes first-slice records from CSV fragment", () => {
  const shadowIds = firstSliceOptionIds(shadowData);
  assert.deepEqual(
    normalizeChoices(shadowData.choices.filter((choice) => FIRST_SLICE_RPOS.has(choice.rpo))),
    normalizeChoices(csvFragment.choices.filter((choice) => FIRST_SLICE_RPOS.has(choice.rpo)))
  );
  assert.deepEqual(
    normalizeRules(shadowData.rules.filter((rule) => shadowIds.has(rule.source_id) || shadowIds.has(rule.target_id))),
    normalizeRules(csvFragment.rules)
  );
  assert.deepEqual(
    normalizePriceRules(
      shadowData.priceRules.filter((rule) => shadowIds.has(rule.condition_option_id) || shadowIds.has(rule.target_option_id))
    ),
    normalizePriceRules(csvFragment.priceRules)
  );
  assert.deepEqual(
    normalizeExclusiveGroups(shadowData.exclusiveGroups.filter((group) => (group.option_ids || []).some((optionId) => shadowIds.has(optionId)))),
    normalizeExclusiveGroups(csvFragment.exclusiveGroups.filter((group) => (group.option_ids || []).some((optionId) => shadowIds.has(optionId))))
  );
});

const scenarios = [
  ["coupe B6P", "1lt_c07", ["B6P"]],
  ["coupe BCP", "1lt_c07", ["BCP"]],
  ["coupe BCP with B6P", "1lt_c07", ["BCP", "B6P"]],
  ["convertible BCP missing ZZ3", "1lt_c67", ["BCP"]],
  ["convertible BCP with ZZ3", "1lt_c67", ["BCP", "ZZ3"]],
  ["coupe BCP with BC4", "1lt_c07", ["BCP", "BC4"]],
  ["explicit D3V with B6P", "1lt_c07", ["D3V", "B6P"]],
  ["explicit SL9 with B6P", "1lt_c07", ["SL9", "B6P"]],
];

for (const [name, variantId, rpos] of scenarios) {
  test(`shadow first-slice runtime behavior matches production: ${name}`, () => {
    assert.deepEqual(
      runScenario(shadowData, { variantId, rpos }),
      runScenario(productionData, { variantId, rpos })
    );
  });
}
