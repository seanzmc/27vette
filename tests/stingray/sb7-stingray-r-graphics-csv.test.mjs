import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import fs from "node:fs";
import test from "node:test";

import { createRuntime, loadGeneratedData, loadShadowData } from "./runtime-harness.mjs";

const PYTHON = ".venv/bin/python";
const SCRIPT = "scripts/stingray_csv_first_slice.py";
const OWNERSHIP_MANIFEST = "data/stingray/validation/projected_slice_ownership.csv";
const SB7_SOURCE_TEXT_STRIPE_RPOS = new Set([
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
  "DZU",
  "DZV",
  "DZX",
]);
const OUT_OF_SCOPE_RPOS = new Set([]);

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
    .filter((choice) => choice.rpo === "SB7")
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

function lineByRpo(runtime, rpo) {
  return runtime.lineItems().find((line) => line.rpo === rpo);
}

function sourceTextRpos(choice) {
  return new Set((choice.source_detail_raw.match(/\b[A-Z0-9]{2,3}\b/g) || []).filter((rpo) => !new Set(["RPO", "LPO", "PDV"]).has(rpo)));
}

test("CSV SB7 legacy fragment matches generated choice metadata and direct price", () => {
  const production = loadGeneratedData();
  const projected = emitCsvLegacyFragment();
  const sb7Id = optionIdByRpo(production, "SB7");
  const result = evaluate("1lt_c07", [sb7Id]);
  const line = result.selected_lines.find((item) => item.rpo === "SB7");

  assert.deepEqual(projected.validation_errors, []);
  assert.deepEqual(normalizeChoices(projected.choices), normalizeChoices(production.choices));
  assert.equal(line?.final_price_usd, 595);
  assert.deepEqual(result.validation_errors, []);
});

test("SB7 projected choice stays available across all Stingray variants", () => {
  const projected = emitCsvLegacyFragment();
  const choices = normalizeChoices(projected.choices);

  assert.equal(choices.length, 6);
  assert.deepEqual(
    choices.map((choice) => [choice.variant_id, choice.status, choice.status_label, choice.selectable, choice.active]),
    [
      ["1lt_c07", "available", "Available", "True", "True"],
      ["1lt_c67", "available", "Available", "True", "True"],
      ["2lt_c07", "available", "Available", "True", "True"],
      ["2lt_c67", "available", "Available", "True", "True"],
      ["3lt_c07", "available", "Available", "True", "True"],
      ["3lt_c67", "available", "Available", "True", "True"],
    ]
  );
});

test("SB7 source-text stripe constraints are same-section single-select peers", () => {
  const data = loadGeneratedData();
  const sb7 = data.choices.find((choice) => choice.rpo === "SB7" && choice.active === "True");
  assert.ok(sb7);
  assert.deepEqual(sourceTextRpos(sb7), SB7_SOURCE_TEXT_STRIPE_RPOS);

  const section = data.sections.find((item) => item.section_id === sb7.section_id);
  assert.equal(section?.selection_mode, "single_select_opt");

  for (const rpo of SB7_SOURCE_TEXT_STRIPE_RPOS) {
    const peer = data.choices.find((choice) => choice.rpo === rpo && choice.active === "True");
    assert.ok(peer, `${rpo} should resolve to an active generated choice`);
    assert.equal(peer.section_id, sb7.section_id, `${rpo} should remain a same-section Stripes peer of SB7`);
    assert.equal(peer.selection_mode, "single_select_opt", `${rpo} should remain covered by Stripes single-select behavior`);
  }
});

test("shadow runtime preserves SB7 Stripes single-select behavior", () => {
  for (const data of [loadGeneratedData(), loadShadowData()]) {
    for (const rpo of SB7_SOURCE_TEXT_STRIPE_RPOS) {
      const sb7First = runtimeFor(data, "1lt_c07");
      sb7First.handleChoice(activeChoiceByRpo(sb7First, "SB7"));
      sb7First.handleChoice(activeChoiceByRpo(sb7First, rpo));
      assert.deepEqual(selectedRpos(sb7First, new Set(["SB7", rpo])), [rpo]);

      const stripeFirst = runtimeFor(data, "1lt_c07");
      stripeFirst.handleChoice(activeChoiceByRpo(stripeFirst, rpo));
      stripeFirst.handleChoice(activeChoiceByRpo(stripeFirst, "SB7"));
      assert.deepEqual(selectedRpos(stripeFirst, new Set(["SB7", rpo])), ["SB7"]);
    }
  }
});

test("shadow runtime preserves PDV package behavior for SB7", () => {
  for (const data of [loadGeneratedData(), loadShadowData()]) {
    const packageRuntime = runtimeFor(data, "1lt_c07");
    packageRuntime.handleChoice(activeChoiceByRpo(packageRuntime, "PDV"));
    assert.equal(lineByRpo(packageRuntime, "SB7")?.type, "auto_added");
    assert.equal(lineByRpo(packageRuntime, "SB7")?.price, 0);

    const memberFirstRuntime = runtimeFor(data, "1lt_c07");
    memberFirstRuntime.handleChoice(activeChoiceByRpo(memberFirstRuntime, "SB7"));
    memberFirstRuntime.handleChoice(activeChoiceByRpo(memberFirstRuntime, "PDV"));
    assert.equal(lineByRpo(memberFirstRuntime, "SB7")?.type, "selected");
    assert.equal(lineByRpo(memberFirstRuntime, "SB7")?.price, 0);
  }
});

test("shadow runtime preserves PCX and SB7 mutual blocking", () => {
  for (const data of [loadGeneratedData(), loadShadowData()]) {
    const pcxFirst = runtimeFor(data, "1lt_c07");
    pcxFirst.handleChoice(activeChoiceByRpo(pcxFirst, "PCX"));
    assert.match(pcxFirst.disableReasonForChoice(activeChoiceByRpo(pcxFirst, "SB7")), /Blocked by PCX/);
    pcxFirst.handleChoice(activeChoiceByRpo(pcxFirst, "SB7"));
    assert.deepEqual(selectedRpos(pcxFirst, new Set(["PCX", "SB7"])), ["PCX"]);

    const sb7First = runtimeFor(data, "1lt_c07");
    sb7First.handleChoice(activeChoiceByRpo(sb7First, "SB7"));
    assert.match(sb7First.disableReasonForChoice(activeChoiceByRpo(sb7First, "PCX")), /Conflicts with SB7/);
    sb7First.handleChoice(activeChoiceByRpo(sb7First, "PCX"));
    assert.deepEqual(selectedRpos(sb7First, new Set(["PCX", "SB7"])), ["SB7"]);
  }
});

test("SB7 package boundaries remain production-owned while PCX conflict is dependency-owned", () => {
  const production = loadGeneratedData();
  const shadow = loadShadowData();
  const fragment = emitCsvLegacyFragment();

  assert.deepEqual(plain(rule(shadow, "PDV", "SB7", "includes")), plain(rule(production, "PDV", "SB7", "includes")));
  assert.deepEqual(plain(priceRule(shadow, "PDV", "SB7", 0)), plain(priceRule(production, "PDV", "SB7", 0)));
  assert.deepEqual(plain(rule(shadow, "PCX", "SB7", "excludes")), plain(rule(production, "PCX", "SB7", "excludes")));

  const pdvId = optionIdByRpo(production, "PDV");
  const sb7Id = optionIdByRpo(production, "SB7");
  assert.equal(fragment.rules.some((item) => item.source_id === pdvId && item.target_id === sb7Id), false);
  assert.deepEqual(plain(rule(fragment, "PCX", "SB7", "excludes")), plain(rule(production, "PCX", "SB7", "excludes")));
  assert.equal(fragment.priceRules.some((item) => item.condition_option_id === pdvId && item.target_option_id === sb7Id), false);

  assert.equal(manifestHas({ record_type: "selectable", rpo: "SB7", ownership: "projected_owned" }), true);
  assert.equal(manifestHas({ record_type: "rule", source_rpo: "PDV", target_rpo: "SB7", ownership: "preserved_cross_boundary" }), true);
  assert.equal(manifestHas({ record_type: "priceRule", source_rpo: "PDV", target_rpo: "SB7", ownership: "preserved_cross_boundary" }), true);
  assert.equal(manifestHas({ record_type: "rule", source_rpo: "PCX", target_rpo: "SB7", ownership: "preserved_cross_boundary" }), false);
});

test("SB7 projection does not claim broader graphics or package rows", () => {
  const owned = projectedOwnedRpos();

  assert.equal(owned.has("SB7"), true);
  for (const rpo of OUT_OF_SCOPE_RPOS) {
    assert.equal(owned.has(rpo), false, `${rpo} should remain outside the SB7 Stingray R graphics slice`);
  }
});
