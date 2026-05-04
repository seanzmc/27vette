import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import fs from "node:fs";
import test from "node:test";

import { createRuntime, loadGeneratedData, loadShadowData } from "./runtime-harness.mjs";

const PYTHON = ".venv/bin/python";
const SCRIPT = "scripts/stingray_csv_first_slice.py";
const OWNERSHIP_MANIFEST = "data/stingray/validation/projected_slice_ownership.csv";
const REQUIRED_ROOF_DEFAULT_RPOS = new Set(["CF7", "CM9"]);
const ROOF_RPOS = new Set(["CF7", "CM9", "C2Z", "CC3", "D84", "D86"]);

function parseCsv(source) {
  const rows = [];
  let row = [];
  let field = "";
  let inQuotes = false;
  for (let index = 0; index < source.length; index++) {
    const char = source[index];
    const next = source[index + 1];
    if (char === '"' && inQuotes && next === '"') {
      field += '"';
      index++;
    } else if (char === '"') {
      inQuotes = !inQuotes;
    } else if (char === "," && !inQuotes) {
      row.push(field);
      field = "";
    } else if ((char === "\n" || char === "\r") && !inQuotes) {
      if (char === "\r" && next === "\n") index++;
      row.push(field);
      if (row.some((value) => value !== "")) rows.push(row);
      row = [];
      field = "";
    } else {
      field += char;
    }
  }
  if (field || row.length) {
    row.push(field);
    rows.push(row);
  }
  const [headers, ...records] = rows;
  return records.map((record) => Object.fromEntries(headers.map((header, index) => [header, record[index] || ""])));
}

function activeManifestRows() {
  return parseCsv(fs.readFileSync(OWNERSHIP_MANIFEST, "utf8")).filter((row) => row.active === "true");
}

function projectedOwnedRpos() {
  return new Set(activeManifestRows().filter((row) => row.record_type === "selectable" && row.ownership === "projected_owned").map((row) => row.rpo));
}

function emitCsvLegacyFragment() {
  const output = execFileSync(PYTHON, [SCRIPT, "--emit-legacy-fragment"], {
    cwd: process.cwd(),
    encoding: "utf8",
    maxBuffer: 8 * 1024 * 1024,
  });
  return JSON.parse(output);
}

function evaluate(variantId, selectedIds) {
  const output = execFileSync(PYTHON, [SCRIPT, "--scenario-json", JSON.stringify({ variant_id: variantId, selected_ids: selectedIds })], {
    cwd: process.cwd(),
    encoding: "utf8",
  });
  return JSON.parse(output);
}

function plain(value) {
  return JSON.parse(JSON.stringify(value));
}

function optionIdsByRpo(data, rpo) {
  return [...new Set(data.choices.filter((choice) => choice.rpo === rpo && choice.active === "True").map((choice) => choice.option_id))].sort();
}

function normalizeRequiredRoofDefaultChoices(rows) {
  return Array.from(rows)
    .filter((choice) => REQUIRED_ROOF_DEFAULT_RPOS.has(choice.rpo))
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

function runtimeFor(data, variantId) {
  const runtime = createRuntime(data);
  const variant = data.variants.find((item) => item.variant_id === variantId);
  assert.ok(variant, `${variantId} should exist`);
  runtime.state.bodyStyle = variant.body_style;
  runtime.state.trimLevel = variant.trim_level;
  runtime.resetDefaults();
  runtime.reconcileSelections();
  return runtime;
}

function activeChoiceByRpo(runtime, rpo) {
  const choice = runtime
    .activeChoiceRows()
    .find((item) => item.rpo === rpo && item.active === "True" && item.status !== "unavailable" && item.selectable === "True");
  assert.ok(choice, `${rpo} should have an active selectable choice`);
  return choice;
}

function choiceByRpo(runtime, rpo) {
  const choice = runtime.activeChoiceRows().find((item) => item.rpo === rpo && item.active === "True" && item.selectable === "True");
  assert.ok(choice, `${rpo} should have an active selectable choice row`);
  return choice;
}

function selectedRpos(runtime, rpos) {
  return [...runtime.state.selected]
    .map((optionId) => runtime.activeChoiceRows().find((choice) => choice.option_id === optionId)?.rpo)
    .filter((rpo) => rpos.has(rpo))
    .sort();
}

function rulesTouching(data, rpos) {
  const ids = new Set(data.choices.filter((choice) => rpos.has(choice.rpo)).map((choice) => choice.option_id));
  return data.rules
    .filter((item) => ids.has(item.source_id) || ids.has(item.target_id))
    .map((item) => {
      const source = data.choices.find((choice) => choice.option_id === item.source_id)?.rpo || item.source_id;
      const target = data.choices.find((choice) => choice.option_id === item.target_id)?.rpo || item.target_id;
      return `${source}->${target}:${item.rule_type}:${item.auto_add}`;
    })
    .sort();
}

function priceRulesTouching(data, rpos) {
  const ids = new Set(data.choices.filter((choice) => rpos.has(choice.rpo)).map((choice) => choice.option_id));
  return data.priceRules
    .filter((item) => ids.has(item.condition_option_id) || ids.has(item.target_option_id))
    .map((item) => {
      const source = data.choices.find((choice) => choice.option_id === item.condition_option_id)?.rpo || item.condition_option_id;
      const target = data.choices.find((choice) => choice.option_id === item.target_option_id)?.rpo || item.target_option_id;
      return `${source}->${target}:${item.price_rule_type}:${Number(item.price_value)}`;
    })
    .sort();
}

function groupIdsTouchingOption(groups, optionIds) {
  return groups
    .filter((group) => optionIds.some((optionId) => group.option_ids.includes(optionId)))
    .map((group) => group.group_id)
    .sort();
}

function ruleGroupIdsTouchingOption(groups, optionIds) {
  return groups
    .filter((group) => optionIds.some((optionId) => group.source_id === optionId || group.target_ids.includes(optionId)))
    .map((group) => group.group_id)
    .sort();
}

test("CSV required Roof defaults fragment emits both production option IDs for CF7 and CM9", () => {
  const production = loadGeneratedData();
  const projected = emitCsvLegacyFragment();
  const choices = normalizeRequiredRoofDefaultChoices(projected.choices);

  assert.deepEqual(projected.validation_errors, []);
  assert.deepEqual(choices, normalizeRequiredRoofDefaultChoices(production.choices));
  assert.equal(choices.length, 24);
  assert.deepEqual(optionIdsByRpo(projected, "CF7"), ["opt_cf7_001", "opt_cf7_002"]);
  assert.deepEqual(optionIdsByRpo(projected, "CM9"), ["opt_cm9_001", "opt_cm9_002"]);
  for (const optionId of ["opt_cf7_001", "opt_cf7_002", "opt_cm9_001", "opt_cm9_002"]) {
    assert.equal(choices.filter((choice) => choice.option_id === optionId).length, 6);
  }
});

test("CSV evaluator preserves CF7 and CM9 zero-price defaults", () => {
  const cf7 = evaluate("1lt_c07", ["opt_cf7_001"]);
  assert.deepEqual(cf7.validation_errors, []);
  assert.equal(cf7.selected_lines.find((line) => line.rpo === "CF7")?.final_price_usd, 0);

  const cm9 = evaluate("1lt_c67", ["opt_cm9_001"]);
  assert.deepEqual(cm9.validation_errors, []);
  assert.equal(cm9.selected_lines.find((line) => line.rpo === "CM9")?.final_price_usd, 0);
});

test("required Roof defaults projection claims CF7 and CM9 without section ownership", () => {
  const owned = projectedOwnedRpos();

  assert.equal(owned.has("CF7"), true);
  assert.equal(owned.has("CM9"), true);
  assert.equal(activeManifestRows().some((row) => row.record_type === "section" || row.group_id === "sec_roof_001" || row.group_id === "sec_stan_002"), false);
});

test("production has no structured records touching CF7 or CM9", () => {
  const production = loadGeneratedData();
  const optionIds = ["CF7", "CM9"].flatMap((rpo) => optionIdsByRpo(production, rpo));

  assert.deepEqual(plain(rulesTouching(production, REQUIRED_ROOF_DEFAULT_RPOS)), []);
  assert.deepEqual(plain(priceRulesTouching(production, REQUIRED_ROOF_DEFAULT_RPOS)), []);
  assert.deepEqual(plain(groupIdsTouchingOption(production.exclusiveGroups, optionIds)), []);
  assert.deepEqual(plain(ruleGroupIdsTouchingOption(production.ruleGroups, optionIds)), []);
});

test("shadow runtime preserves body-style Roof defaults and replacement behavior", () => {
  for (const data of [loadGeneratedData(), loadShadowData()]) {
    for (const variant of data.variants) {
      const runtime = runtimeFor(data, variant.variant_id);
      const expected = variant.body_style === "coupe" ? ["CF7"] : ["CM9"];
      assert.deepEqual(selectedRpos(runtime, ROOF_RPOS), expected);
    }

    const coupeRuntime = runtimeFor(data, "1lt_c07");
    assert.equal(coupeRuntime.disableReasonForChoice(choiceByRpo(coupeRuntime, "CM9")), "Not available for this body and trim.");
    coupeRuntime.handleChoice(activeChoiceByRpo(coupeRuntime, "C2Z"));
    assert.deepEqual(selectedRpos(coupeRuntime, ROOF_RPOS), ["C2Z"]);
    coupeRuntime.handleChoice(activeChoiceByRpo(coupeRuntime, "CF7"));
    assert.deepEqual(selectedRpos(coupeRuntime, ROOF_RPOS), ["CF7"]);
    coupeRuntime.handleChoice(activeChoiceByRpo(coupeRuntime, "CC3"));
    assert.deepEqual(selectedRpos(coupeRuntime, ROOF_RPOS), ["CC3"]);
    coupeRuntime.handleChoice(activeChoiceByRpo(coupeRuntime, "CF7"));
    assert.deepEqual(selectedRpos(coupeRuntime, ROOF_RPOS), ["CF7"]);

    const convertibleRuntime = runtimeFor(data, "1lt_c67");
    assert.equal(convertibleRuntime.disableReasonForChoice(choiceByRpo(convertibleRuntime, "CF7")), "Not available for this body and trim.");
    convertibleRuntime.handleChoice(activeChoiceByRpo(convertibleRuntime, "D84"));
    assert.deepEqual(selectedRpos(convertibleRuntime, ROOF_RPOS), ["D84"]);
    convertibleRuntime.handleChoice(activeChoiceByRpo(convertibleRuntime, "CM9"));
    assert.deepEqual(selectedRpos(convertibleRuntime, ROOF_RPOS), ["CM9"]);
    convertibleRuntime.handleChoice(activeChoiceByRpo(convertibleRuntime, "D86"));
    assert.deepEqual(selectedRpos(convertibleRuntime, ROOF_RPOS), ["D86"]);
    convertibleRuntime.handleChoice(activeChoiceByRpo(convertibleRuntime, "CM9"));
    assert.deepEqual(selectedRpos(convertibleRuntime, ROOF_RPOS), ["CM9"]);
  }
});

test("CF7 and CM9 display-only Standard Options duplicates remain production-equivalent", () => {
  for (const data of [loadGeneratedData(), loadShadowData()]) {
    for (const [rpo, optionId, displayOrder] of [
      ["CF7", "opt_cf7_002", 6],
      ["CM9", "opt_cm9_002", 3],
    ]) {
      const standardRows = data.choices.filter((choice) => choice.rpo === rpo && choice.option_id === optionId);
      assert.equal(standardRows.length, 6);
      for (const choice of standardRows) {
        assert.equal(choice.section_id, "sec_stan_002");
        assert.equal(choice.section_name, "Standard Options");
        assert.equal(choice.category_id, "cat_stan_001");
        assert.equal(choice.category_name, "Standard Equipment");
        assert.equal(choice.step_key, "standard_equipment");
        assert.equal(choice.choice_mode, "display");
        assert.equal(choice.selection_mode, "display_only");
        assert.equal(choice.selectable, "False");
        assert.equal(Number(choice.base_price), 0);
        assert.equal(Number(choice.display_order), displayOrder);
      }
      assert.deepEqual(
        plain(standardRows.filter((choice) => choice.status === "standard").map((choice) => `${choice.variant_id}:${choice.option_id}:${choice.section_id}`).sort()),
        plain(data.standardEquipment.filter((item) => item.rpo === rpo).map((item) => `${item.variant_id}:${item.option_id}:${item.section_id}`).sort())
      );
    }
  }
});
