import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import fs from "node:fs";
import test from "node:test";
import vm from "node:vm";

const FIRST_SLICE_RPOS = new Set(["B6P", "D3V", "SL9", "ZZ3", "BCP", "BCS", "BC4", "BC7"]);

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

function firstSliceOptionIds(data) {
  return new Set(data.choices.filter((choice) => FIRST_SLICE_RPOS.has(choice.rpo)).map((choice) => choice.option_id));
}

function normalizeChoices(rows) {
  return Array.from(rows)
    .filter((choice) => FIRST_SLICE_RPOS.has(choice.rpo))
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

function normalizeRules(rows, optionIds) {
  return Array.from(rows)
    .filter((rule) => optionIds.has(rule.source_id) || optionIds.has(rule.target_id))
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

function normalizePriceRules(rows, optionIds) {
  return Array.from(rows)
    .filter((rule) => optionIds.has(rule.condition_option_id) || optionIds.has(rule.target_option_id))
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

function normalizeExclusiveGroups(rows, optionIds) {
  return Array.from(rows)
    .filter((group) => (group.option_ids || []).some((optionId) => optionIds.has(optionId)))
    .map((group) => ({
      option_ids: [...group.option_ids].filter((optionId) => optionIds.has(optionId)).sort(),
      selection_mode: group.selection_mode,
      active: group.active,
      notes: group.notes,
    }))
    .sort((a, b) => a.option_ids.join("|").localeCompare(b.option_ids.join("|")));
}

test("CSV first-slice legacy fragment matches generated first-slice contract records", () => {
  const production = loadGeneratedData();
  const projected = emitCsvLegacyFragment();
  const productionOptionIds = firstSliceOptionIds(production);
  const projectedOptionIds = firstSliceOptionIds(projected);

  assert.deepEqual(projected.validation_errors, []);
  assert.deepEqual(normalizeVariants(projected.variants), normalizeVariants(production.variants));
  assert.deepEqual([...projectedOptionIds].sort(), [...productionOptionIds].sort());
  assert.deepEqual(normalizeChoices(projected.choices), normalizeChoices(production.choices));
  assert.deepEqual(normalizeRules(projected.rules, productionOptionIds), normalizeRules(production.rules, productionOptionIds));
  assert.deepEqual(normalizePriceRules(projected.priceRules, productionOptionIds), normalizePriceRules(production.priceRules, productionOptionIds));
  assert.deepEqual(normalizeExclusiveGroups(projected.exclusiveGroups, productionOptionIds), normalizeExclusiveGroups(production.exclusiveGroups, productionOptionIds));
  assert.equal(
    projected.ruleGroups.some((group) => group.source_id && productionOptionIds.has(group.source_id)),
    false
  );
  assert.deepEqual(projected.documented_mismatches, []);
});
