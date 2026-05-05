import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import fs from "node:fs";
import test from "node:test";

import { createRuntime, loadGeneratedData, loadShadowData } from "./runtime-harness.mjs";

const PYTHON = ".venv/bin/python";
const SCRIPT = "scripts/stingray_csv_first_slice.py";
const OWNERSHIP_MANIFEST = "data/stingray/validation/projected_slice_ownership.csv";
const REQUIRED_BADGES_RPOS = new Set(["EYK", "EYT"]);
const EYK_INBOUND_EXCLUDES = [
  ["PCX", "EYK"],
  ["R88", "EYK"],
  ["SFZ", "EYK"],
];
const CSV_OWNED_EYK_INBOUND_EXCLUDE_SOURCES = new Set(["R88", "SFZ"]);

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

function manifestHas(expected) {
  return activeManifestRows().some((row) => Object.entries(expected).every(([key, value]) => row[key] === value));
}

function projectedOwnedRpos() {
  return new Set(activeManifestRows().filter((row) => row.record_type === "selectable" && row.ownership === "projected_owned").map((row) => row.rpo));
}

function optionIdsByRpo(data, rpo) {
  return [...new Set(data.choices.filter((choice) => choice.rpo === rpo && choice.active === "True").map((choice) => choice.option_id))].sort();
}

function optionIdByRpo(data, rpo) {
  const ids = optionIdsByRpo(data, rpo);
  assert.equal(ids.length, 1, `${rpo} should map to exactly one legacy option_id`);
  return ids[0];
}

function activeChoiceByRpo(runtime, rpo) {
  const choice = runtime
    .activeChoiceRows()
    .find((item) => item.rpo === rpo && item.active === "True" && item.status !== "unavailable" && item.selectable === "True");
  assert.ok(choice, `${rpo} should have an active selectable choice`);
  return choice;
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

function selectedRpos(runtime, rpos) {
  return [...runtime.state.selected]
    .map((optionId) => runtime.activeChoiceRows().find((choice) => choice.option_id === optionId)?.rpo)
    .filter((rpo) => rpos.has(rpo))
    .sort();
}

function normalizeChoices(rows) {
  return Array.from(rows)
    .filter((choice) => REQUIRED_BADGES_RPOS.has(choice.rpo))
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

function rule(data, sourceRpo, targetRpo, ruleType) {
  const sourceId = optionIdByRpo(data, sourceRpo);
  const targetId = optionIdByRpo(data, targetRpo);
  return data.rules.find((item) => item.source_id === sourceId && item.target_id === targetId && item.rule_type === ruleType);
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

test("CSV required Badges fragment emits EYK and both EYT production option IDs", () => {
  const production = loadGeneratedData();
  const projected = emitCsvLegacyFragment();
  const choices = normalizeChoices(projected.choices);

  assert.deepEqual(projected.validation_errors, []);
  assert.deepEqual(choices, normalizeChoices(production.choices));
  assert.equal(choices.length, 18);
  assert.deepEqual(optionIdsByRpo(projected, "EYK"), ["opt_eyk_001"]);
  assert.deepEqual(optionIdsByRpo(projected, "EYT"), ["opt_eyt_001", "opt_eyt_002"]);
  assert.equal(choices.filter((choice) => choice.option_id === "opt_eyk_001").length, 6);
  assert.equal(choices.filter((choice) => choice.option_id === "opt_eyt_001").length, 6);
  assert.equal(choices.filter((choice) => choice.option_id === "opt_eyt_002").length, 6);
});

test("CSV evaluator preserves direct EYK and EYT required Badges pricing", () => {
  const eyk = evaluate("1lt_c07", ["opt_eyk_001"]);
  const eykLine = eyk.selected_lines.find((line) => line.rpo === "EYK");
  assert.equal(eykLine?.final_price_usd, 395);
  assert.deepEqual(eyk.validation_errors, []);

  const eyt = evaluate("1lt_c07", ["opt_eyt_001"]);
  const eytLine = eyt.selected_lines.find((line) => line.rpo === "EYT" && line.selectable_id === "opt_eyt_001");
  assert.equal(eytLine?.final_price_usd, 0);
  assert.deepEqual(eyt.validation_errors, []);
});

test("shadow runtime preserves required Badges default and replacement behavior", () => {
  for (const data of [loadGeneratedData(), loadShadowData()]) {
    for (const variant of data.variants) {
      const runtime = runtimeFor(data, variant.variant_id);
      assert.deepEqual(selectedRpos(runtime, REQUIRED_BADGES_RPOS), ["EYT"]);
    }

    const runtime = runtimeFor(data, "1lt_c07");
    runtime.handleChoice(activeChoiceByRpo(runtime, "EYK"));
    assert.deepEqual(selectedRpos(runtime, REQUIRED_BADGES_RPOS), ["EYK"]);
    assert.equal(runtime.optionPrice(activeChoiceByRpo(runtime, "EYK").option_id), 395);

    runtime.handleChoice(activeChoiceByRpo(runtime, "EYT"));
    assert.deepEqual(selectedRpos(runtime, REQUIRED_BADGES_RPOS), ["EYT"]);
    assert.equal(runtime.optionPrice(activeChoiceByRpo(runtime, "EYT").option_id), 0);
  }
});

test("EYT display-only Standard Options duplicate remains production-equivalent", () => {
  for (const data of [loadGeneratedData(), loadShadowData()]) {
    const standardRows = data.choices.filter((choice) => choice.rpo === "EYT" && choice.option_id === "opt_eyt_002");
    assert.equal(standardRows.length, 6);
    for (const choice of standardRows) {
      assert.equal(choice.section_id, "sec_stan_002");
      assert.equal(choice.section_name, "Standard Options");
      assert.equal(choice.category_id, "cat_stan_001");
      assert.equal(choice.category_name, "Standard Equipment");
      assert.equal(choice.step_key, "standard_equipment");
      assert.equal(choice.choice_mode, "display");
      assert.equal(choice.selection_mode, "display_only");
      assert.equal(choice.status, "standard");
      assert.equal(choice.status_label, "Standard");
      assert.equal(choice.selectable, "False");
      assert.equal(Number(choice.base_price), 0);
      assert.equal(Number(choice.display_order), 2);
    }
    assert.deepEqual(
      plain(standardRows.map((choice) => `${choice.variant_id}:${choice.option_id}:${choice.section_id}`).sort()),
      plain(data.standardEquipment.filter((item) => item.rpo === "EYT").map((item) => `${item.variant_id}:${item.option_id}:${item.section_id}`).sort())
    );
  }
});

test("required Badges projection preserves inbound EYK rules and emits only migrated excludes", () => {
  const production = loadGeneratedData();
  const shadow = loadShadowData();
  const fragment = emitCsvLegacyFragment();
  const eykId = optionIdByRpo(production, "EYK");
  const eytIds = optionIdsByRpo(production, "EYT");

  for (const [sourceRpo, targetRpo] of EYK_INBOUND_EXCLUDES) {
    assert.deepEqual(plain(rule(shadow, sourceRpo, targetRpo, "excludes")), plain(rule(production, sourceRpo, targetRpo, "excludes")));
    assert.equal(
      manifestHas({ record_type: "rule", source_rpo: sourceRpo, target_rpo: targetRpo, ownership: "preserved_cross_boundary" }),
      !CSV_OWNED_EYK_INBOUND_EXCLUDE_SOURCES.has(sourceRpo)
    );
  }

  assert.deepEqual(plain(rule(fragment, "R88", "EYK", "excludes")), plain(rule(production, "R88", "EYK", "excludes")));
  assert.deepEqual(plain(rule(fragment, "SFZ", "EYK", "excludes")), plain(rule(production, "SFZ", "EYK", "excludes")));
  const migratedBadgeRuleKeys = new Set([
    `${optionIdByRpo(production, "R88")}->${eykId}`,
    `${optionIdByRpo(production, "SFZ")}->${eykId}`,
  ]);
  assert.equal(
    fragment.rules.some(
      (item) =>
        (item.source_id === eykId || item.target_id === eykId || eytIds.includes(item.source_id) || eytIds.includes(item.target_id)) &&
        !migratedBadgeRuleKeys.has(`${item.source_id}->${item.target_id}`)
    ),
    false
  );
  assert.equal(
    fragment.priceRules.some(
      (item) => item.condition_option_id === eykId || item.target_option_id === eykId || eytIds.includes(item.condition_option_id) || eytIds.includes(item.target_option_id)
    ),
    false
  );
  assert.deepEqual(plain(groupIdsTouchingOption(fragment.exclusiveGroups, [eykId, ...eytIds])), []);
  assert.deepEqual(plain(ruleGroupIdsTouchingOption(fragment.ruleGroups, [eykId, ...eytIds])), []);
});

test("required Badges projection claims only EYK EYT choices, not section metadata or neighboring package behavior", () => {
  const owned = projectedOwnedRpos();
  assert.equal(owned.has("EYK"), true);
  assert.equal(owned.has("EYT"), true);
  assert.equal(activeManifestRows().some((row) => row.record_type === "section" || row.group_id === "sec_badg_001" || row.group_id === "sec_stan_002"), false);
  assert.equal(manifestHas({ record_type: "guardedOption", rpo: "EYK", ownership: "production_guarded" }), false);
  assert.equal(manifestHas({ record_type: "guardedOption", target_option_id: "opt_eyt_001", ownership: "production_guarded" }), false);
  assert.equal(manifestHas({ record_type: "guardedOption", target_option_id: "opt_eyt_002", ownership: "production_guarded" }), false);

  for (const rpo of ["PCX", "PDV", "GBA", "ZYC"]) {
    assert.equal(owned.has(rpo), false, `${rpo} should remain outside the required Badges slice`);
  }
});
