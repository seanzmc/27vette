import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import fs from "node:fs";
import test from "node:test";

import { createRuntime, loadGeneratedData, loadShadowData } from "./runtime-harness.mjs";

const PYTHON = ".venv/bin/python";
const SCRIPT = "scripts/stingray_csv_first_slice.py";
const OWNERSHIP_MANIFEST = "data/stingray/validation/projected_slice_ownership.csv";
const SFZ_SOURCE_TEXT_STRIPE_RPOS = new Set([
  "DPB",
  "DPC",
  "DPG",
  "DPL",
  "DPT",
  "DSY",
  "DSZ",
  "DT0",
  "DTH",
  "DUB",
  "DUE",
  "DUK",
  "DUW",
]);
const SFZ_SOURCE_TEXT_MISSING_RPOS = new Set(["DTB"]);
const OUT_OF_SCOPE_RPOS = new Set([
  "PCX",
  "5DG",
  "S47",
  "SFE",
  "SPY",
  "SPZ",
  "R8C",
]);

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
    .filter((choice) => choice.rpo === "SFZ")
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

function rule(data, sourceRpo, targetRpo, ruleType) {
  const sourceId = optionIdByRpo(data, sourceRpo);
  const targetId = optionIdByRpo(data, targetRpo);
  return data.rules.find((item) => item.source_id === sourceId && item.target_id === targetId && item.rule_type === ruleType);
}

function priceRule(data, sourceRpo, targetRpo, priceValue) {
  const sourceId = optionIdByRpo(data, sourceRpo);
  const targetId = optionIdByRpo(data, targetRpo);
  return data.priceRules.find(
    (item) => item.condition_option_id === sourceId && item.target_option_id === targetId && Number(item.price_value) === priceValue
  );
}

function groupIdsTouchingOption(groups, optionId) {
  return groups
    .filter((group) => group.option_ids.includes(optionId))
    .map((group) => group.group_id)
    .sort();
}

function ruleGroupIdsTouchingOption(groups, optionId) {
  return groups
    .filter((group) => group.source_id === optionId || group.target_ids.includes(optionId))
    .map((group) => group.group_id)
    .sort();
}

function lineByRpo(runtime, rpo) {
  return runtime.lineItems().find((line) => line.rpo === rpo);
}

function sourceTextRpos(choice) {
  return new Set((choice.source_detail_raw.match(/\b[A-Z0-9]{2,3}\b/g) || []).filter((rpo) => !new Set(["RPO", "LPO", "PCX"]).has(rpo)));
}

test("CSV evaluator prices direct SFZ Dark Stealth badge selection", () => {
  const production = loadGeneratedData();
  const result = evaluate("1lt_c07", [optionIdByRpo(production, "SFZ")]);
  const line = result.selected_lines.find((item) => item.rpo === "SFZ");

  assert.equal(line?.final_price_usd, 250);
  assert.deepEqual(result.validation_errors, []);
});

test("CSV SFZ legacy fragment matches generated choices and all-variant availability", () => {
  const production = loadGeneratedData();
  const projected = emitCsvLegacyFragment();
  const choices = normalizeChoices(projected.choices);

  assert.deepEqual(projected.validation_errors, []);
  assert.deepEqual(choices, normalizeChoices(production.choices));
  assert.equal(choices.length, 6);
  assert.deepEqual(
    choices.map((choice) => [choice.variant_id, choice.status, choice.status_label, choice.selectable, choice.active, choice.base_price]),
    [
      ["1lt_c07", "available", "Available", "True", "True", 250],
      ["1lt_c67", "available", "Available", "True", "True", 250],
      ["2lt_c07", "available", "Available", "True", "True", 250],
      ["2lt_c67", "available", "Available", "True", "True", 250],
      ["3lt_c07", "available", "Available", "True", "True", 250],
      ["3lt_c67", "available", "Available", "True", "True", 250],
    ]
  );
});

test("SFZ source-text constraints are structured records or explicitly absent generated choices", () => {
  const data = loadGeneratedData();
  const sfz = data.choices.find((choice) => choice.rpo === "SFZ" && choice.active === "True");
  assert.ok(sfz);

  const expectedSourceTextRpos = new Set(["EYK", ...SFZ_SOURCE_TEXT_STRIPE_RPOS, ...SFZ_SOURCE_TEXT_MISSING_RPOS]);
  assert.deepEqual(sourceTextRpos(sfz), expectedSourceTextRpos);

  assert.ok(rule(data, "SFZ", "EYK", "excludes"), "SFZ should have a structured SFZ -> EYK exclude");
  for (const rpo of SFZ_SOURCE_TEXT_STRIPE_RPOS) {
    const peer = data.choices.find((choice) => choice.rpo === rpo && choice.active === "True");
    assert.ok(peer, `${rpo} should resolve to an active generated choice`);
    assert.equal(peer.section_id, "sec_stri_001", `${rpo} should remain in the Stripes section`);
    assert.equal(peer.selection_mode, "single_select_opt", `${rpo} should remain an optional Stripes peer`);
    assert.ok(rule(data, "SFZ", rpo, "excludes"), `SFZ should preserve a structured SFZ -> ${rpo} exclude`);
  }

  for (const rpo of SFZ_SOURCE_TEXT_MISSING_RPOS) {
    assert.equal(data.choices.some((choice) => choice.rpo === rpo && choice.active === "True"), false, `${rpo} should not become a fake selectable`);
  }
});

test("production has only classified structured records touching SFZ", () => {
  const data = loadGeneratedData();
  const sfzId = optionIdByRpo(data, "SFZ");
  const allowedRuleKeys = new Set([
    "PCX->SFZ:includes",
    "R88->SFZ:excludes",
    "SFZ->EYK:excludes",
    ...[...SFZ_SOURCE_TEXT_STRIPE_RPOS].map((rpo) => `SFZ->${rpo}:excludes`),
  ]);
  const ruleKeys = data.rules
    .filter((item) => item.source_id === sfzId || item.target_id === sfzId)
    .map((item) => {
      const source = data.choices.find((choice) => choice.option_id === item.source_id)?.rpo || item.source_id;
      const target = data.choices.find((choice) => choice.option_id === item.target_id)?.rpo || item.target_id;
      return `${source}->${target}:${item.rule_type}`;
    })
    .sort();

  assert.deepEqual(plain(ruleKeys), plain([...allowedRuleKeys].sort()));
  const priceRuleKeys = data.priceRules
    .filter((item) => item.condition_option_id === sfzId || item.target_option_id === sfzId)
    .map((item) => {
      const source = data.choices.find((choice) => choice.option_id === item.condition_option_id)?.rpo || item.condition_option_id;
      const target = data.choices.find((choice) => choice.option_id === item.target_option_id)?.rpo || item.target_option_id;
      return `${source}->${target}:${item.price_rule_type}:${Number(item.price_value)}`;
    });
  assert.deepEqual(plain(priceRuleKeys), ["PCX->SFZ:override:0"]);
  assert.deepEqual(plain(groupIdsTouchingOption(data.exclusiveGroups, sfzId)), []);
  assert.deepEqual(plain(ruleGroupIdsTouchingOption(data.ruleGroups, sfzId)), []);
});

test("shadow runtime preserves SFZ package pricing and badge/stripe blocks", () => {
  for (const data of [loadGeneratedData(), loadShadowData()]) {
    const directRuntime = runtimeFor(data, "1lt_c07");
    directRuntime.handleChoice(activeChoiceByRpo(directRuntime, "SFZ"));
    assert.deepEqual(selectedRpos(directRuntime, new Set(["SFZ"])), ["SFZ"]);
    assert.equal(lineByRpo(directRuntime, "SFZ")?.price, 250);
    assert.equal(lineByRpo(directRuntime, "SFZ")?.type, "selected");
    assert.match(directRuntime.disableReasonForChoice(activeChoiceByRpo(directRuntime, "R88")), /Conflicts with SFZ/);
    assert.match(directRuntime.disableReasonForChoice(activeChoiceByRpo(directRuntime, "EYK")), /Blocked by SFZ/);
    for (const rpo of SFZ_SOURCE_TEXT_STRIPE_RPOS) {
      assert.match(directRuntime.disableReasonForChoice(activeChoiceByRpo(directRuntime, rpo)), /Blocked by SFZ/);
    }

    const packageRuntime = runtimeFor(data, "1lt_c07");
    packageRuntime.handleChoice(activeChoiceByRpo(packageRuntime, "PCX"));
    assert.equal(lineByRpo(packageRuntime, "SFZ")?.type, "auto_added");
    assert.equal(lineByRpo(packageRuntime, "SFZ")?.price, 0);

    const memberFirstRuntime = runtimeFor(data, "1lt_c07");
    memberFirstRuntime.handleChoice(activeChoiceByRpo(memberFirstRuntime, "SFZ"));
    memberFirstRuntime.handleChoice(activeChoiceByRpo(memberFirstRuntime, "PCX"));
    assert.equal(lineByRpo(memberFirstRuntime, "SFZ")?.type, "selected");
    assert.equal(lineByRpo(memberFirstRuntime, "SFZ")?.price, 0);
    assert.equal(memberFirstRuntime.lineItems().filter((line) => line.rpo === "SFZ").length, 1);

    const r88Runtime = runtimeFor(data, "1lt_c07");
    r88Runtime.handleChoice(activeChoiceByRpo(r88Runtime, "R88"));
    assert.match(r88Runtime.disableReasonForChoice(activeChoiceByRpo(r88Runtime, "SFZ")), /Blocked by R88/);
  }
});

test("SFZ boundaries remain production-owned and preserved", () => {
  const production = loadGeneratedData();
  const shadow = loadShadowData();
  const fragment = emitCsvLegacyFragment();
  const sfzId = optionIdByRpo(production, "SFZ");

  assert.deepEqual(plain(rule(shadow, "PCX", "SFZ", "includes")), plain(rule(production, "PCX", "SFZ", "includes")));
  assert.deepEqual(plain(priceRule(shadow, "PCX", "SFZ", 0)), plain(priceRule(production, "PCX", "SFZ", 0)));
  assert.deepEqual(plain(rule(shadow, "R88", "SFZ", "excludes")), plain(rule(production, "R88", "SFZ", "excludes")));
  assert.deepEqual(plain(rule(shadow, "SFZ", "EYK", "excludes")), plain(rule(production, "SFZ", "EYK", "excludes")));
  for (const rpo of SFZ_SOURCE_TEXT_STRIPE_RPOS) {
    assert.deepEqual(plain(rule(shadow, "SFZ", rpo, "excludes")), plain(rule(production, "SFZ", rpo, "excludes")));
  }

  assert.deepEqual(plain(rule(fragment, "R88", "SFZ", "excludes")), plain(rule(production, "R88", "SFZ", "excludes")));
  assert.deepEqual(plain(rule(fragment, "SFZ", "EYK", "excludes")), plain(rule(production, "SFZ", "EYK", "excludes")));
  const migratedSfzRuleKeys = new Set([
    `${optionIdByRpo(production, "R88")}->${sfzId}`,
    `${sfzId}->${optionIdByRpo(production, "EYK")}`,
  ]);
  assert.equal(
    fragment.rules.some((item) => (item.source_id === sfzId || item.target_id === sfzId) && !migratedSfzRuleKeys.has(`${item.source_id}->${item.target_id}`)),
    false
  );
  assert.equal(fragment.priceRules.some((item) => item.condition_option_id === sfzId || item.target_option_id === sfzId), false);

  assert.equal(manifestHas({ record_type: "selectable", rpo: "SFZ", ownership: "projected_owned" }), true);
  assert.equal(manifestHas({ record_type: "rule", source_rpo: "PCX", target_rpo: "SFZ", ownership: "preserved_cross_boundary" }), true);
  assert.equal(manifestHas({ record_type: "priceRule", source_rpo: "PCX", target_rpo: "SFZ", ownership: "preserved_cross_boundary" }), true);
  assert.equal(manifestHas({ record_type: "rule", source_rpo: "R88", target_rpo: "SFZ", ownership: "preserved_cross_boundary" }), true);
  assert.equal(manifestHas({ record_type: "rule", source_rpo: "SFZ", target_rpo: "EYK", ownership: "preserved_cross_boundary" }), true);
  for (const rpo of SFZ_SOURCE_TEXT_STRIPE_RPOS) {
    assert.equal(manifestHas({ record_type: "rule", source_rpo: "SFZ", target_rpo: rpo, ownership: "preserved_cross_boundary" }), true);
  }
});

test("SFZ projection does not claim PCX badges wheels stripes or missing DTB", () => {
  const production = loadGeneratedData();
  const owned = projectedOwnedRpos();

  assert.equal(owned.has("SFZ"), true);
  for (const rpo of OUT_OF_SCOPE_RPOS) {
    assert.equal(owned.has(rpo), false, `${rpo} should remain outside the SFZ Dark Stealth badge member slice`);
  }
  for (const rpo of SFZ_SOURCE_TEXT_MISSING_RPOS) {
    assert.equal(production.choices.some((choice) => choice.rpo === rpo || choice.option_id === `opt_${rpo.toLowerCase()}_001`), false);
    assert.equal(owned.has(rpo), false);
  }
});
