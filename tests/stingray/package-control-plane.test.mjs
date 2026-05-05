import assert from "node:assert/strict";
import { execFileSync, spawnSync } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import test from "node:test";

import { createRuntime, loadGeneratedData, loadShadowData } from "./runtime-harness.mjs";

const PYTHON = ".venv/bin/python";
const FRAGMENT_SCRIPT = "scripts/stingray_csv_first_slice.py";
const OVERLAY_SCRIPT = "scripts/stingray_csv_shadow_overlay.py";

function emitLegacyFragment() {
  return JSON.parse(
    execFileSync(PYTHON, [FRAGMENT_SCRIPT, "--emit-legacy-fragment"], {
      cwd: process.cwd(),
      encoding: "utf8",
      maxBuffer: 8 * 1024 * 1024,
    })
  );
}

function writeJson(value, prefix) {
  const tempDir = fs.mkdtempSync(path.join(os.tmpdir(), prefix));
  const file = path.join(tempDir, "fragment.json");
  fs.writeFileSync(file, `${JSON.stringify(value)}\n`);
  return file;
}

function writeProductionData(data) {
  const tempDir = fs.mkdtempSync(path.join(os.tmpdir(), "stingray-package-production-"));
  const file = path.join(tempDir, "data.js");
  const registry = {
    defaultModelKey: "stingray",
    models: {
      stingray: {
        key: "stingray",
        label: "Stingray",
        modelName: "Corvette Stingray",
        exportSlug: "stingray",
        data,
      },
    },
  };
  fs.writeFileSync(
    file,
    `window.CORVETTE_FORM_DATA = ${JSON.stringify(registry)};\nwindow.STINGRAY_FORM_DATA = window.CORVETTE_FORM_DATA.models.stingray.data;\n`
  );
  return file;
}

function runOverlay(args = []) {
  return spawnSync(PYTHON, [OVERLAY_SCRIPT, ...args], {
    cwd: process.cwd(),
    encoding: "utf8",
    maxBuffer: 8 * 1024 * 1024,
  });
}

function optionIdByRpo(data, rpo) {
  const ids = new Set(data.choices.filter((choice) => choice.rpo === rpo).map((choice) => choice.option_id));
  assert.equal(ids.size, 1, `${rpo} should map to exactly one option_id`);
  return [...ids][0];
}

function productionRule(data, sourceRpo, targetRpo, ruleType = "includes") {
  const sourceId = optionIdByRpo(data, sourceRpo);
  const targetId = optionIdByRpo(data, targetRpo);
  const rule = data.rules.find((item) => item.source_id === sourceId && item.target_id === targetId && item.rule_type === ruleType);
  assert.ok(rule, `${sourceRpo} -> ${targetRpo} ${ruleType} rule should exist`);
  return JSON.parse(JSON.stringify(rule));
}

function productionPriceRule(data, sourceRpo, targetRpo, priceValue = 0) {
  const sourceId = optionIdByRpo(data, sourceRpo);
  const targetId = optionIdByRpo(data, targetRpo);
  const rule = data.priceRules.find(
    (item) => item.condition_option_id === sourceId && item.target_option_id === targetId && Number(item.price_value) === priceValue
  );
  assert.ok(rule, `${sourceRpo} -> ${targetRpo} priceRule should exist`);
  return JSON.parse(JSON.stringify(rule));
}

function syntheticPackageRule(data, sourceRpo, targetRpo) {
  const template = productionRule(data, "PDV", "VWD");
  const sourceId = optionIdByRpo(data, sourceRpo);
  const targetId = optionIdByRpo(data, targetRpo);
  return {
    ...template,
    rule_id: `rule_${sourceId}_includes_${targetId}`,
    source_id: sourceId,
    target_id: targetId,
  };
}

function syntheticPackagePriceRule(data, sourceRpo, targetRpo) {
  const template = productionPriceRule(data, "PDV", "VWD");
  const sourceId = optionIdByRpo(data, sourceRpo);
  const targetId = optionIdByRpo(data, targetRpo);
  return {
    ...template,
    price_rule_id: `pr_${sourceId}_${targetId}_included_zero`,
    condition_option_id: sourceId,
    target_option_id: targetId,
    price_value: 0,
  };
}

function overlayWithMutatedFragment(mutator, production = loadGeneratedData()) {
  const fragment = emitLegacyFragment();
  mutator(fragment, production);
  return runOverlay(["--production-data", writeProductionData(production), "--fragment-json", writeJson(fragment, "stingray-package-fragment-")]);
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

function plain(value) {
  return JSON.parse(JSON.stringify(value));
}

test("fully owned package fixture emits include rules and included-zero priceRules in the legacy shape", () => {
  const fragment = emitLegacyFragment();
  const b6pD3vRule = fragment.rules.find((rule) => rule.source_id === "opt_b6p_001" && rule.target_id === "opt_d3v_001");
  const b6pD3vPriceRule = fragment.priceRules.find(
    (rule) => rule.condition_option_id === "opt_b6p_001" && rule.target_option_id === "opt_d3v_001" && Number(rule.price_value) === 0
  );

  assert.deepEqual(fragment.validation_errors, []);
  assert.ok(b6pD3vRule);
  assert.equal(b6pD3vRule.rule_type, "includes");
  assert.equal(b6pD3vRule.auto_add, "True");
  assert.ok(b6pD3vPriceRule);
  assert.equal(b6pD3vPriceRule.price_rule_type, "override");
});

test("overlay rejects a projected package include with a production-owned source", () => {
  const result = overlayWithMutatedFragment((fragment, production) => {
    fragment.rules.push(productionRule(production, "Z51", "T0A"));
  });

  assert.notEqual(result.status, 0);
  assert.match(result.stderr, /projected package include source is not projected-owned/);
  assert.match(result.stderr, /opt_z51_001/);
});

test("overlay rejects a projected package include with a production-owned target", () => {
  const production = loadGeneratedData();
  const rule = syntheticPackageRule(production, "B6P", "5JR");
  production.rules.push(rule);

  const result = overlayWithMutatedFragment((fragment) => {
    fragment.rules.push(rule);
  }, production);

  assert.notEqual(result.status, 0);
  assert.match(result.stderr, /projected package include targets are not projected-owned/);
  assert.match(result.stderr, /opt_5jr_001/);
});

test("overlay rejects a projected package priceRule with a production-owned source", () => {
  const result = overlayWithMutatedFragment((fragment, production) => {
    fragment.priceRules.push(productionPriceRule(production, "Z51", "TVS"));
  });

  assert.notEqual(result.status, 0);
  assert.match(result.stderr, /projected package priceRule source is not projected-owned/);
  assert.match(result.stderr, /opt_z51_001/);
});

test("overlay rejects a projected package priceRule with a production-owned target", () => {
  const production = loadGeneratedData();
  const rule = syntheticPackagePriceRule(production, "B6P", "5JR");
  production.priceRules.push(rule);

  const result = overlayWithMutatedFragment((fragment) => {
    fragment.priceRules.push(rule);
  }, production);

  assert.notEqual(result.status, 0);
  assert.match(result.stderr, /projected package priceRule targets are not projected-owned/);
  assert.match(result.stderr, /opt_5jr_001/);
});

test("only cross-owned package examples remain production-owned and preserved", () => {
  const production = loadGeneratedData();
  const shadow = loadShadowData();
  const fragment = emitLegacyFragment();

  const preservedEdges = [
    ["Z51", "T0A"],
  ];
  for (const [sourceRpo, targetRpo] of preservedEdges) {
    const sourceId = optionIdByRpo(production, sourceRpo);
    const targetId = optionIdByRpo(production, targetRpo);
    const productionRuleRow = production.rules.find((rule) => rule.source_id === sourceId && rule.target_id === targetId && rule.rule_type === "includes");
    const shadowRuleRow = shadow.rules.find((rule) => rule.source_id === sourceId && rule.target_id === targetId && rule.rule_type === "includes");

    assert.ok(productionRuleRow, `${sourceRpo} -> ${targetRpo} production include should exist`);
    assert.deepEqual(plain(shadowRuleRow), plain(productionRuleRow));
    assert.equal(fragment.rules.some((rule) => rule.source_id === sourceId && rule.target_id === targetId), false);
  }

  for (const targetRpo of ["VWD", "SB7"]) {
    const sourceId = optionIdByRpo(production, "PDV");
    const targetId = optionIdByRpo(production, targetRpo);
    const productionRuleRow = production.rules.find((rule) => rule.source_id === sourceId && rule.target_id === targetId && rule.rule_type === "includes");
    const fragmentRuleRow = fragment.rules.find((rule) => rule.source_id === sourceId && rule.target_id === targetId && rule.rule_type === "includes");
    const productionPriceRuleRow = production.priceRules.find(
      (rule) => rule.condition_option_id === sourceId && rule.target_option_id === targetId && Number(rule.price_value) === 0
    );
    const fragmentPriceRuleRow = fragment.priceRules.find(
      (rule) => rule.condition_option_id === sourceId && rule.target_option_id === targetId && Number(rule.price_value) === 0
    );

    assert.deepEqual(plain(fragmentRuleRow), plain(productionRuleRow));
    assert.deepEqual(plain(fragmentPriceRuleRow), {
      ...plain(productionPriceRuleRow),
      price_rule_id: `pr_${sourceId}_${targetId}_included_zero`,
    });
  }
});

test("PDV to VWD runtime package behavior remains production-equivalent", () => {
  const shadow = loadShadowData();

  const directRuntime = runtimeFor(shadow, "1lt_c07");
  const directVwd = activeChoiceByRpo(directRuntime, "VWD");
  directRuntime.handleChoice(directVwd);
  assert.equal(directRuntime.optionPrice(directVwd.option_id), 250);

  const packageRuntime = runtimeFor(shadow, "1lt_c07");
  const pdv = activeChoiceByRpo(packageRuntime, "PDV");
  const packageVwd = activeChoiceByRpo(packageRuntime, "VWD");
  packageRuntime.handleChoice(pdv);
  assert.equal(packageRuntime.computeAutoAdded().has(packageVwd.option_id), true);
  assert.equal(packageRuntime.optionPrice(packageVwd.option_id), 0);

  const memberFirstRuntime = runtimeFor(shadow, "1lt_c07");
  const memberFirstVwd = activeChoiceByRpo(memberFirstRuntime, "VWD");
  const memberFirstPdv = activeChoiceByRpo(memberFirstRuntime, "PDV");
  memberFirstRuntime.handleChoice(memberFirstVwd);
  memberFirstRuntime.handleChoice(memberFirstPdv);
  assert.equal(memberFirstRuntime.state.selected.has(memberFirstVwd.option_id), true);
  assert.equal(memberFirstRuntime.computeAutoAdded().has(memberFirstVwd.option_id), false);
  assert.equal(memberFirstRuntime.optionPrice(memberFirstVwd.option_id), 0);

  memberFirstRuntime.handleChoice(memberFirstPdv);
  assert.equal(memberFirstRuntime.state.selected.has(memberFirstPdv.option_id), false);
  assert.equal(memberFirstRuntime.state.selected.has(memberFirstVwd.option_id), true);
  assert.equal(memberFirstRuntime.optionPrice(memberFirstVwd.option_id), 250);
});
