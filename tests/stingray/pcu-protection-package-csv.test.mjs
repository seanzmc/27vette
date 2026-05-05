import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import fs from "node:fs";
import test from "node:test";

import { createRuntime, loadGeneratedData, loadShadowData } from "./runtime-harness.mjs";

const PYTHON = ".venv/bin/python";
const SCRIPT = "scripts/stingray_csv_first_slice.py";
const OWNERSHIP_MANIFEST = "data/stingray/validation/projected_slice_ownership.csv";
const PCU_PACKAGE_RPOS = new Set(["PCU", "STI", "VQK", "VWE"]);
const PCU_MEMBER_RPOS = ["STI", "VQK", "VWE"];
const INCLUDED_EDGES = PCU_MEMBER_RPOS.map((targetRpo) => ["PCU", targetRpo]);

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

function manifestHas(expected) {
  return activeManifestRows().some((row) => Object.entries(expected).every(([key, value]) => row[key] === value));
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
  const ids = new Set(data.choices.filter((choice) => choice.rpo === rpo && choice.active === "True").map((choice) => choice.option_id));
  assert.equal(ids.size, 1, `${rpo} should map to exactly one active legacy option_id`);
  return [...ids][0];
}

function optionIdsByRpo(data, rpo) {
  return [...new Set(data.choices.filter((choice) => choice.rpo === rpo && choice.active === "True").map((choice) => choice.option_id))].sort();
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

function normalizeChoices(rows) {
  return Array.from(rows)
    .filter((choice) => PCU_PACKAGE_RPOS.has(choice.rpo))
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

function packageRuleKeys(data, sourceRpo, targetRpos) {
  const sourceId = optionIdByRpo(data, sourceRpo);
  const targetIds = new Set(targetRpos.map((rpo) => optionIdByRpo(data, rpo)));
  return data.rules
    .filter((rule) => rule.source_id === sourceId && targetIds.has(rule.target_id))
    .map((rule) => {
      const target = data.choices.find((choice) => choice.option_id === rule.target_id)?.rpo || rule.target_id;
      return `${sourceRpo}->${target}:${rule.rule_type}:${rule.auto_add}`;
    })
    .sort();
}

function packagePriceRuleKeys(data, sourceRpo, targetRpos) {
  const sourceId = optionIdByRpo(data, sourceRpo);
  const targetIds = new Set(targetRpos.map((rpo) => optionIdByRpo(data, rpo)));
  return data.priceRules
    .filter((rule) => rule.condition_option_id === sourceId && targetIds.has(rule.target_option_id))
    .map((rule) => {
      const target = data.choices.find((choice) => choice.option_id === rule.target_option_id)?.rpo || rule.target_option_id;
      return `${sourceRpo}->${target}:${rule.price_rule_type}:${Number(rule.price_value)}`;
    })
    .sort();
}

function ruleKeysTouching(data, rpos) {
  const ids = new Set(data.choices.filter((choice) => rpos.has(choice.rpo)).map((choice) => choice.option_id));
  ids.add("opt_5vm_001");
  ids.add("opt_5w8_001");
  return data.rules
    .filter((rule) => ids.has(rule.source_id) || ids.has(rule.target_id))
    .map((rule) => {
      const source = data.choices.find((choice) => choice.option_id === rule.source_id)?.rpo || rule.source_id;
      const target = data.choices.find((choice) => choice.option_id === rule.target_id)?.rpo || rule.target_id;
      return `${source}->${target}:${rule.rule_type}:${rule.auto_add}`;
    })
    .sort();
}

function priceRuleKeysTouching(data, rpos) {
  const ids = new Set(data.choices.filter((choice) => rpos.has(choice.rpo)).map((choice) => choice.option_id));
  return data.priceRules
    .filter((rule) => ids.has(rule.condition_option_id) || ids.has(rule.target_option_id))
    .map((rule) => {
      const source = data.choices.find((choice) => choice.option_id === rule.condition_option_id)?.rpo || rule.condition_option_id;
      const target = data.choices.find((choice) => choice.option_id === rule.target_option_id)?.rpo || rule.target_option_id;
      return `${source}->${target}:${rule.price_rule_type}:${Number(rule.price_value)}`;
    })
    .sort();
}

function groupIdsTouching(data, rpos) {
  const ids = new Set(data.choices.filter((choice) => rpos.has(choice.rpo)).map((choice) => choice.option_id));
  return {
    exclusiveGroups: data.exclusiveGroups
      .filter((group) => (group.option_ids || []).some((optionId) => ids.has(optionId)))
      .map((group) => group.group_id)
      .sort(),
    ruleGroups: data.ruleGroups
      .filter((group) => ids.has(group.source_id) || (group.target_ids || []).some((optionId) => ids.has(optionId)))
      .map((group) => group.group_id)
      .sort(),
  };
}

function stalePreservedPcuPackageRows() {
  return activeManifestRows()
    .filter(
      (row) =>
        row.ownership === "preserved_cross_boundary" &&
        row.source_rpo === "PCU" &&
        PCU_MEMBER_RPOS.includes(row.target_rpo) &&
        ["rule", "priceRule"].includes(row.record_type)
    )
    .map((row) => `${row.record_type}:${row.source_rpo}->${row.target_rpo}`)
    .sort();
}

function lineByRpo(runtime, rpo) {
  return runtime.lineItems().find((line) => line.rpo === rpo);
}

test("CSV evaluator prices direct PCU protection package selection", () => {
  const production = loadGeneratedData();
  const result = evaluate("1lt_c07", [optionIdByRpo(production, "PCU")]);

  assert.deepEqual(result.validation_errors, []);
  assert.equal(result.selected_lines.find((line) => line.rpo === "PCU")?.final_price_usd, 1575);
  for (const rpo of PCU_MEMBER_RPOS) {
    assert.equal(result.selected_lines.find((line) => line.rpo === rpo)?.final_price_usd, 0);
  }
});

test("CSV PCU package legacy fragment matches generated choices and all-variant availability", () => {
  const production = loadGeneratedData();
  const projected = emitCsvLegacyFragment();
  const choices = normalizeChoices(projected.choices);

  assert.deepEqual(projected.validation_errors, []);
  assert.deepEqual(choices, normalizeChoices(production.choices));
  assert.equal(choices.length, 24);
  assert.deepEqual(
    choices
      .filter((choice) => choice.rpo === "PCU")
      .map((choice) => [choice.rpo, choice.variant_id, choice.status, choice.status_label, choice.selectable, choice.active, choice.base_price]),
    [
      ["PCU", "1lt_c07", "available", "Available", "True", "True", 1575],
      ["PCU", "1lt_c67", "available", "Available", "True", "True", 1575],
      ["PCU", "2lt_c07", "available", "Available", "True", "True", 1575],
      ["PCU", "2lt_c67", "available", "Available", "True", "True", 1575],
      ["PCU", "3lt_c07", "available", "Available", "True", "True", 1575],
      ["PCU", "3lt_c67", "available", "Available", "True", "True", 1575],
    ]
  );
});

test("PCU package cluster satisfies projected-owned source and target policy", () => {
  const owned = projectedOwnedRpos();
  const production = loadGeneratedData();

  for (const rpo of PCU_PACKAGE_RPOS) {
    assert.equal(owned.has(rpo), true, `${rpo} should be projected-owned`);
  }
  assert.equal(optionIdsByRpo(production, "5VM").length, 0);
  assert.equal(optionIdsByRpo(production, "5W8").length, 0);
  assert.deepEqual(stalePreservedPcuPackageRows(), [], "PCU package records should not remain preserved cross-boundary rows");

  assert.equal(manifestHas({ record_type: "rule", source_rpo: "PCU", target_rpo: "5V7", ownership: "preserved_cross_boundary" }), false);
  assert.equal(manifestHas({ record_type: "rule", source_rpo: "PCU", target_option_id: "opt_5vm_001", ownership: "preserved_cross_boundary" }), true);
  assert.equal(manifestHas({ record_type: "rule", source_rpo: "PCU", target_option_id: "opt_5w8_001", ownership: "preserved_cross_boundary" }), true);
});

test("CSV PCU legacy fragment emits package include rules and included-zero priceRules", () => {
  const production = loadGeneratedData();
  const projected = emitCsvLegacyFragment();

  assert.deepEqual(projected.validation_errors, []);
  for (const [sourceRpo, targetRpo] of INCLUDED_EDGES) {
    const sourceId = optionIdByRpo(production, sourceRpo);
    const targetId = optionIdByRpo(production, targetRpo);
    const rule = projected.rules.find((item) => item.source_id === sourceId && item.target_id === targetId);
    const priceRule = projected.priceRules.find(
      (item) => item.condition_option_id === sourceId && item.target_option_id === targetId && Number(item.price_value) === 0
    );

    assert.ok(rule, `${sourceRpo} -> ${targetRpo} include rule should be projected`);
    assert.equal(rule.rule_type, "includes");
    assert.equal(rule.auto_add, "True");
    assert.ok(priceRule, `${sourceRpo} -> ${targetRpo} included-zero priceRule should be projected`);
    assert.equal(priceRule.price_rule_type, "override");
  }
});

test("production has only classified records touching the PCU package cluster", () => {
  const production = loadGeneratedData();

  assert.deepEqual(plain(ruleKeysTouching(production, PCU_PACKAGE_RPOS)), [
    "5V7->STI:excludes:False",
    "5V7->opt_5vm_001:excludes:False",
    "5V7->opt_5w8_001:excludes:False",
    "PCU->5V7:excludes:False",
    "PCU->STI:includes:True",
    "PCU->VQK:includes:True",
    "PCU->VWE:includes:True",
    "PCU->opt_5vm_001:excludes:False",
    "PCU->opt_5w8_001:excludes:False",
    "STI->5V7:excludes:False",
    "STI->opt_5vm_001:excludes:False",
    "STI->opt_5w8_001:excludes:False",
    "opt_5vm_001->5V7:excludes:False",
    "opt_5vm_001->5ZU:requires:False",
    "opt_5vm_001->5ZZ:requires:False",
    "opt_5vm_001->STI:excludes:False",
    "opt_5vm_001->TVS:excludes:False",
    "opt_5vm_001->Z51:requires:False",
    "opt_5vm_001->opt_5w8_001:excludes:False",
    "opt_5vm_001->opt_5zw_001:requires:False",
    "opt_5w8_001->5V7:excludes:False",
    "opt_5w8_001->5ZU:requires:False",
    "opt_5w8_001->5ZZ:requires:False",
    "opt_5w8_001->STI:excludes:False",
    "opt_5w8_001->TVS:excludes:False",
    "opt_5w8_001->Z51:requires:False",
    "opt_5w8_001->opt_5vm_001:excludes:False",
    "opt_5w8_001->opt_5zw_001:requires:False",
  ]);
  assert.deepEqual(plain(priceRuleKeysTouching(production, PCU_PACKAGE_RPOS)), [
    "PCU->STI:override:0",
    "PCU->VQK:override:0",
    "PCU->VWE:override:0",
  ]);
  assert.deepEqual(plain(groupIdsTouching(production, PCU_PACKAGE_RPOS)), {
    exclusiveGroups: [],
    ruleGroups: [],
  });
});

test("shadow overlay projects PCU package records and preserves external ground-effects boundaries", () => {
  const production = loadGeneratedData();
  const shadow = loadShadowData();

  assert.deepEqual(plain(packageRuleKeys(shadow, "PCU", PCU_MEMBER_RPOS)), plain(packageRuleKeys(production, "PCU", PCU_MEMBER_RPOS)));
  assert.deepEqual(plain(packagePriceRuleKeys(shadow, "PCU", PCU_MEMBER_RPOS)), plain(packagePriceRuleKeys(production, "PCU", PCU_MEMBER_RPOS)));
  assert.deepEqual(stalePreservedPcuPackageRows(), []);
  assert.deepEqual(plain(ruleKeysTouching(shadow, PCU_PACKAGE_RPOS)), plain(ruleKeysTouching(production, PCU_PACKAGE_RPOS)));
});

test("shadow PCU runtime package and 5V7 boundary behavior matches production", () => {
  for (const data of [loadGeneratedData(), loadShadowData()]) {
    const directRuntime = runtimeFor(data, "1lt_c07");
    for (const [rpo, price] of [
      ["STI", 675],
      ["VQK", 395],
      ["VWE", 695],
    ]) {
      directRuntime.handleChoice(activeChoiceByRpo(directRuntime, rpo));
      assert.equal(lineByRpo(directRuntime, rpo)?.price, price);
    }

    const packageRuntime = runtimeFor(data, "1lt_c07");
    const pcu = activeChoiceByRpo(packageRuntime, "PCU");
    packageRuntime.handleChoice(pcu);
    assert.equal(lineByRpo(packageRuntime, "PCU")?.price, 1575);
    for (const rpo of PCU_MEMBER_RPOS) {
      const member = activeChoiceByRpo(packageRuntime, rpo);
      assert.equal(packageRuntime.computeAutoAdded().has(member.option_id), true);
      assert.equal(packageRuntime.optionPrice(member.option_id), 0);
    }

    const memberFirstRuntime = runtimeFor(data, "1lt_c07");
    for (const rpo of PCU_MEMBER_RPOS) memberFirstRuntime.handleChoice(activeChoiceByRpo(memberFirstRuntime, rpo));
    memberFirstRuntime.handleChoice(activeChoiceByRpo(memberFirstRuntime, "PCU"));
    for (const rpo of PCU_MEMBER_RPOS) {
      assert.equal(memberFirstRuntime.lineItems().filter((line) => line.rpo === rpo).length, 1);
      assert.equal(memberFirstRuntime.computeAutoAdded().has(activeChoiceByRpo(memberFirstRuntime, rpo).option_id), false);
      assert.equal(memberFirstRuntime.optionPrice(activeChoiceByRpo(memberFirstRuntime, rpo).option_id), 0);
    }

    memberFirstRuntime.handleChoice(activeChoiceByRpo(memberFirstRuntime, "PCU"));
    assert.equal(memberFirstRuntime.state.selected.has(activeChoiceByRpo(memberFirstRuntime, "PCU").option_id), false);
    assert.equal(memberFirstRuntime.optionPrice(activeChoiceByRpo(memberFirstRuntime, "STI").option_id), 675);
    assert.equal(memberFirstRuntime.optionPrice(activeChoiceByRpo(memberFirstRuntime, "VQK").option_id), 395);
    assert.equal(memberFirstRuntime.optionPrice(activeChoiceByRpo(memberFirstRuntime, "VWE").option_id), 695);

    const pcuFirstRuntime = runtimeFor(data, "1lt_c07");
    pcuFirstRuntime.handleChoice(activeChoiceByRpo(pcuFirstRuntime, "PCU"));
    pcuFirstRuntime.handleChoice(activeChoiceByRpo(pcuFirstRuntime, "5ZZ"));
    assert.match(pcuFirstRuntime.disableReasonForChoice(activeChoiceByRpo(pcuFirstRuntime, "5V7")), /Blocked by PCU/);

    const fiveV7FirstRuntime = runtimeFor(data, "1lt_c07");
    fiveV7FirstRuntime.handleChoice(activeChoiceByRpo(fiveV7FirstRuntime, "5ZZ"));
    fiveV7FirstRuntime.handleChoice(activeChoiceByRpo(fiveV7FirstRuntime, "5V7"));
    assert.match(fiveV7FirstRuntime.disableReasonForChoice(activeChoiceByRpo(fiveV7FirstRuntime, "PCU")), /Conflicts with 5V7/);
  }
});
