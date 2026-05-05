import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import fs from "node:fs";
import test from "node:test";

import { createRuntime, loadGeneratedData, loadShadowData } from "./runtime-harness.mjs";

const PYTHON = ".venv/bin/python";
const SCRIPT = "scripts/stingray_csv_first_slice.py";
const OWNERSHIP_MANIFEST = "data/stingray/validation/projected_slice_ownership.csv";
const REAR_SCRIPT_RPOS = new Set(["RIN", "SL8", "RIK"]);
const EXPECTED_PRICES = new Map([
  ["RIN", 440],
  ["SL8", 495],
  ["RIK", 395],
]);
const EXPECTED_PEER_EXCLUDES = new Set([
  "RIK->RIN:excludes",
  "RIK->SL8:excludes",
  "RIN->RIK:excludes",
  "RIN->SL8:excludes",
  "SL8->RIK:excludes",
  "SL8->RIN:excludes",
]);
const PASS136_EXCLUDE_PAIRS = [
  ["dep_excl_rin_rik", "RIN", "RIK", "opt_rin_001", "opt_rik_001", "cs_selected_rik"],
  ["dep_excl_rin_sl8", "RIN", "SL8", "opt_rin_001", "opt_sl8_001", "cs_selected_sl8"],
  ["dep_excl_sl8_rin", "SL8", "RIN", "opt_sl8_001", "opt_rin_001", "cs_selected_rin"],
  ["dep_excl_sl8_rik", "SL8", "RIK", "opt_sl8_001", "opt_rik_001", "cs_selected_rik"],
  ["dep_excl_rik_rin", "RIK", "RIN", "opt_rik_001", "opt_rin_001", "cs_selected_rin"],
  ["dep_excl_rik_sl8", "RIK", "SL8", "opt_rik_001", "opt_sl8_001", "cs_selected_sl8"],
];
const PRODUCTION_OWNED_OUT_OF_SCOPE_RPOS = new Set([]);

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

function optionIdByRpo(data, rpo) {
  const ids = new Set(data.choices.filter((item) => item.rpo === rpo && item.active === "True").map((item) => item.option_id));
  assert.equal(ids.size, 1, `${rpo} should map to exactly one legacy option_id`);
  return [...ids][0];
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
    .filter((choice) => REAR_SCRIPT_RPOS.has(choice.rpo))
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

function projectedOwnedRpos() {
  return new Set(activeManifestRows().filter((row) => row.record_type === "selectable" && row.ownership === "projected_owned").map((row) => row.rpo));
}

function manifestHas(expected) {
  return activeManifestRows().some((row) => Object.entries(expected).every(([key, value]) => row[key] === value));
}

function rpoByOptionId(data) {
  return new Map(data.choices.filter((choice) => choice.active === "True").map((choice) => [choice.option_id, choice.rpo]));
}

function ruleKeysTouchingRearScripts(data) {
  const optionRpos = rpoByOptionId(data);
  return data.rules
    .filter((item) => REAR_SCRIPT_RPOS.has(optionRpos.get(item.source_id)) || REAR_SCRIPT_RPOS.has(optionRpos.get(item.target_id)))
    .map((item) => `${optionRpos.get(item.source_id) || item.source_id}->${optionRpos.get(item.target_id) || item.target_id}:${item.rule_type}`)
    .sort();
}

function priceRulesTouchingRearScripts(data) {
  const optionRpos = rpoByOptionId(data);
  return data.priceRules.filter((item) => REAR_SCRIPT_RPOS.has(optionRpos.get(item.condition_option_id)) || REAR_SCRIPT_RPOS.has(optionRpos.get(item.target_option_id)));
}

function groupIdsTouchingRearScripts(groups, data) {
  const optionRpos = rpoByOptionId(data);
  return groups
    .filter((group) => group.option_ids.some((optionId) => REAR_SCRIPT_RPOS.has(optionRpos.get(optionId))))
    .map((group) => group.group_id)
    .sort();
}

function ruleGroupIdsTouchingRearScripts(groups, data) {
  const optionRpos = rpoByOptionId(data);
  return groups
    .filter((group) => REAR_SCRIPT_RPOS.has(optionRpos.get(group.source_id)) || group.target_ids.some((optionId) => REAR_SCRIPT_RPOS.has(optionRpos.get(optionId))))
    .map((group) => group.group_id)
    .sort();
}

function rule(data, sourceRpo, targetRpo, ruleType) {
  const sourceId = optionIdByRpo(data, sourceRpo);
  const targetId = optionIdByRpo(data, targetRpo);
  return data.rules.find((item) => item.source_id === sourceId && item.target_id === targetId && item.rule_type === ruleType);
}

function lineByRpo(runtime, rpo) {
  return runtime.lineItems().find((line) => line.rpo === rpo);
}

function assertNoRearScriptExclusiveGroup(data) {
  const groupIds = data.exclusiveGroups.map((group) => group.group_id);
  assert.equal(groupIds.some((groupId) => /rear.*script|script.*badge/i.test(groupId)), false);
  assert.equal(groupIds.includes("gs_excl_rear_script_badges"), false);
}

test("CSV evaluator prices direct rear script badge selections", () => {
  const production = loadGeneratedData();
  for (const [rpo, price] of EXPECTED_PRICES.entries()) {
    const result = evaluate("1lt_c07", [optionIdByRpo(production, rpo)]);
    const line = result.selected_lines.find((item) => item.rpo === rpo);

    assert.equal(line?.final_price_usd, price);
    assert.deepEqual(result.validation_errors, []);
  }
});

test("CSV rear script badge legacy fragment matches generated choices and all-variant availability", () => {
  const production = loadGeneratedData();
  const projected = emitCsvLegacyFragment();
  const choices = normalizeChoices(projected.choices);

  assert.deepEqual(projected.validation_errors, []);
  assert.deepEqual(choices, normalizeChoices(production.choices));
  assert.equal(choices.length, 18);
  for (const [rpo, price] of EXPECTED_PRICES.entries()) {
    assert.equal(choices.filter((choice) => choice.rpo === rpo).length, 6);
    assert.deepEqual(
      choices
        .filter((choice) => choice.rpo === rpo)
        .map((choice) => [choice.variant_id, choice.status, choice.status_label, choice.selectable, choice.active, choice.base_price]),
      [
        ["1lt_c07", "available", "Available", "True", "True", price],
        ["1lt_c67", "available", "Available", "True", "True", price],
        ["2lt_c07", "available", "Available", "True", "True", price],
        ["2lt_c67", "available", "Available", "True", "True", price],
        ["3lt_c07", "available", "Available", "True", "True", price],
        ["3lt_c67", "available", "Available", "True", "True", price],
      ]
    );
  }
});

test("production has only six peer excludes touching rear script badges", () => {
  const data = loadGeneratedData();

  assert.deepEqual(plain(ruleKeysTouchingRearScripts(data)), plain([...EXPECTED_PEER_EXCLUDES].sort()));
  assert.deepEqual(plain(priceRulesTouchingRearScripts(data)), []);
  assert.deepEqual(plain(groupIdsTouchingRearScripts(data.exclusiveGroups, data)), []);
  assert.deepEqual(plain(ruleGroupIdsTouchingRearScripts(data.ruleGroups, data)), []);
  assertNoRearScriptExclusiveGroup(data);
});

test("shadow runtime preserves rear script badge peer blocking", () => {
  for (const data of [loadGeneratedData(), loadShadowData()]) {
    for (const selectedRpo of REAR_SCRIPT_RPOS) {
      const runtime = runtimeFor(data, "1lt_c07");
      runtime.handleChoice(activeChoiceByRpo(runtime, selectedRpo));
      assert.deepEqual(selectedRpos(runtime, REAR_SCRIPT_RPOS), [selectedRpo]);
      assert.equal(lineByRpo(runtime, selectedRpo)?.price, EXPECTED_PRICES.get(selectedRpo));

      for (const peerRpo of REAR_SCRIPT_RPOS) {
        if (peerRpo === selectedRpo) continue;
        assert.match(runtime.disableReasonForChoice(activeChoiceByRpo(runtime, peerRpo)), new RegExp(`Blocked by ${selectedRpo}`));
        runtime.handleChoice(activeChoiceByRpo(runtime, peerRpo));
        assert.deepEqual(selectedRpos(runtime, REAR_SCRIPT_RPOS), [selectedRpo]);
      }
    }
  }
});

test("rear script badge dependency rules migrate the six production peer excludes", () => {
  const rules = parseCsv(fs.readFileSync("data/stingray/logic/dependency_rules.csv", "utf8"));
  const conditionSets = parseCsv(fs.readFileSync("data/stingray/logic/condition_sets.csv", "utf8"));
  const conditionTerms = parseCsv(fs.readFileSync("data/stingray/logic/condition_terms.csv", "utf8"));

  assert.equal(rules.length, 95);
  assert.equal(rules.filter((item) => item.rule_type === "requires").length, 3);
  assert.equal(rules.filter((item) => item.rule_type === "excludes").length, 92);

  for (const [ruleId, , , sourceId, targetId, conditionSetId] of PASS136_EXCLUDE_PAIRS) {
    const dependencyRule = rules.find((item) => item.rule_id === ruleId);
    assert.ok(dependencyRule, `${ruleId} should exist`);
    assert.equal(dependencyRule.rule_type, "excludes");
    assert.equal(dependencyRule.subject_selector_type, "selectable");
    assert.equal(dependencyRule.subject_selector_id, sourceId);
    assert.equal(dependencyRule.subject_must_be_selected, "true");
    assert.equal(dependencyRule.target_condition_set_id, conditionSetId);
    assert.equal(dependencyRule.violation_behavior, "disable_and_block");
    assert.equal(dependencyRule.active, "true");

    assert.ok(conditionSets.find((item) => item.condition_set_id === conditionSetId), `${conditionSetId} should exist`);
    assert.ok(
      conditionTerms.find(
        (item) =>
          item.condition_set_id === conditionSetId &&
          item.term_type === "selected" &&
          item.left_ref === targetId &&
          item.operator === "is_true"
      ),
      `${conditionSetId} should select ${targetId}`
    );
  }
});

test("rear script badge peer excludes compile as production-shaped dependency rules", () => {
  const production = loadGeneratedData();
  const shadow = loadShadowData();
  const fragment = emitCsvLegacyFragment();
  const rearScriptIds = new Set([...REAR_SCRIPT_RPOS].map((rpo) => optionIdByRpo(production, rpo)));

  for (const [ruleId, sourceRpo, targetRpo, sourceId, targetId, conditionSetId] of PASS136_EXCLUDE_PAIRS) {
    const ruleType = "excludes";
    assert.deepEqual(plain(rule(shadow, sourceRpo, targetRpo, ruleType)), plain(rule(production, sourceRpo, targetRpo, ruleType)));
    assert.deepEqual(plain(rule(fragment, sourceRpo, targetRpo, ruleType)), plain(rule(production, sourceRpo, targetRpo, ruleType)));
    assert.equal(manifestHas({ record_type: "rule", source_rpo: sourceRpo, target_rpo: targetRpo, ownership: "preserved_cross_boundary" }), false);

    const result = evaluate("1lt_c07", [sourceId, targetId]);
    const conflict = result.conflicts.find((item) => item.rule_id === ruleId);
    assert.equal(result.validation_errors.length, 0);
    assert.equal(conflict?.conflict_source, "dependency_rule");
    assert.equal(conflict?.target_condition_set_id, conditionSetId);
  }

  assert.deepEqual(
    fragment.rules
      .filter((item) => rearScriptIds.has(item.source_id) || rearScriptIds.has(item.target_id))
      .map((item) => `${rpoByOptionId(production).get(item.source_id)}->${rpoByOptionId(production).get(item.target_id)}:${item.rule_type}`)
      .sort(),
    [...EXPECTED_PEER_EXCLUDES].sort()
  );
  assert.equal(fragment.priceRules.some((item) => rearScriptIds.has(item.condition_option_id) || rearScriptIds.has(item.target_option_id)), false);
  assert.deepEqual(plain(groupIdsTouchingRearScripts(fragment.exclusiveGroups, production)), []);
  assertNoRearScriptExclusiveGroup(fragment);
  assertNoRearScriptExclusiveGroup(shadow);

  for (const rpo of REAR_SCRIPT_RPOS) {
    assert.equal(manifestHas({ record_type: "selectable", rpo, ownership: "projected_owned" }), true);
  }
});

test("rear script badge projection does not claim badges packages stripes paint or broader badge behavior", () => {
  const owned = projectedOwnedRpos();

  for (const rpo of REAR_SCRIPT_RPOS) {
    assert.equal(owned.has(rpo), true);
  }
  for (const rpo of PRODUCTION_OWNED_OUT_OF_SCOPE_RPOS) {
    assert.equal(owned.has(rpo), false, `${rpo} should remain outside the rear script badge member slice`);
  }
});
