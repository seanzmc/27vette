import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import test from "node:test";

import { createRuntime, loadGeneratedData, loadShadowData } from "./runtime-harness.mjs";

const PYTHON = ".venv/bin/python";
const OVERLAY_SCRIPT = "scripts/stingray_csv_shadow_overlay.py";
const OWNERSHIP_MANIFEST = "data/stingray/validation/projected_slice_ownership.csv";
const EYK_INBOUND_EXCLUDES = [
  ["PCX", "EYK"],
  ["R88", "EYK"],
  ["SFZ", "EYK"],
];

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

function manifestHas(expected) {
  return activeManifestRows().some((row) => Object.entries(expected).every(([key, value]) => row[key] === value));
}

function projectedOwnedRpos() {
  return new Set(activeManifestRows().filter((row) => row.record_type === "selectable" && row.ownership === "projected_owned").map((row) => row.rpo));
}

function optionIdsByRpo(data, rpo) {
  return [...new Set(data.choices.filter((choice) => choice.rpo === rpo).map((choice) => choice.option_id))].sort();
}

function optionIdByRpo(data, rpo) {
  const ids = optionIdsByRpo(data, rpo);
  assert.equal(ids.length, 1, `${rpo} should map to exactly one legacy option_id`);
  return ids[0];
}

function rule(data, sourceRpo, targetRpo, ruleType) {
  const sourceId = optionIdByRpo(data, sourceRpo);
  const targetId = optionIdByRpo(data, targetRpo);
  return data.rules.find((item) => item.source_id === sourceId && item.target_id === targetId && item.rule_type === ruleType);
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

function selectedRpos(runtime, rpos) {
  return [...runtime.state.selected]
    .map((optionId) => runtime.activeChoiceRows().find((choice) => choice.option_id === optionId)?.rpo)
    .filter((rpo) => rpos.has(rpo))
    .sort();
}

function normalizeChoices(rows) {
  return rows
    .map((choice) => ({
      choice_id: choice.choice_id,
      option_id: choice.option_id,
      rpo: choice.rpo,
      label: choice.label,
      section_id: choice.section_id,
      section_name: choice.section_name,
      step_key: choice.step_key,
      variant_id: choice.variant_id,
      status: choice.status,
      selectable: choice.selectable,
      active: choice.active,
      choice_mode: choice.choice_mode,
      selection_mode: choice.selection_mode,
      base_price: Number(choice.base_price || 0),
      display_order: Number(choice.display_order || 0),
    }))
    .sort((a, b) => a.choice_id.localeCompare(b.choice_id));
}

function plain(value) {
  return JSON.parse(JSON.stringify(value));
}

function tempFile(name, contents) {
  const tempDir = fs.mkdtempSync(path.join(os.tmpdir(), "stingray-required-badges-"));
  const file = path.join(tempDir, name);
  fs.writeFileSync(file, contents);
  return file;
}

function writeManifest(rows) {
  const headers = ["record_type", "group_id", "source_rpo", "source_option_id", "target_rpo", "target_option_id", "rpo", "ownership", "reason", "active"];
  return tempFile(
    "projected_slice_ownership.csv",
    `${headers.join(",")}\n${rows.map((row) => headers.map((header) => row[header] || "").join(",")).join("\n")}\n`
  );
}

function writeFragment(production, choices) {
  return tempFile(
    "fragment.json",
    JSON.stringify(
      {
        variants: production.variants,
        choices,
        rules: [],
        priceRules: [],
        ruleGroups: [],
        exclusiveGroups: [],
        validation_errors: [],
      },
      null,
      2
    )
  );
}

function runOverlay(manifest, fragment) {
  return spawnSync(PYTHON, [OVERLAY_SCRIPT, "--ownership-manifest", manifest, "--fragment-json", fragment], {
    cwd: process.cwd(),
    encoding: "utf8",
    maxBuffer: 8 * 1024 * 1024,
  });
}

function eytProjectionManifestRows() {
  return [
    {
      record_type: "selectable",
      rpo: "EYT",
      ownership: "projected_owned",
      reason: "Required Badges duplicate-RPO fixture.",
      active: "true",
    },
  ];
}

test("production keeps EYT as both required Badges default and Standard Options display duplicate", () => {
  const production = loadGeneratedData();
  const eytRows = production.choices.filter((choice) => choice.rpo === "EYT" && choice.active === "True");
  const eykRows = production.choices.filter((choice) => choice.rpo === "EYK" && choice.active === "True");
  const badgesRows = eytRows.filter((choice) => choice.option_id === "opt_eyt_001");
  const standardRows = eytRows.filter((choice) => choice.option_id === "opt_eyt_002");

  assert.deepEqual(optionIdsByRpo(production, "EYT"), ["opt_eyt_001", "opt_eyt_002"]);
  assert.equal(badgesRows.length, 6);
  assert.equal(standardRows.length, 6);
  assert.equal(eykRows.length, 6);
  for (const choice of badgesRows) {
    assert.equal(choice.section_id, "sec_badg_001");
    assert.equal(choice.selection_mode, "single_select_req");
    assert.equal(choice.status, "standard");
    assert.equal(choice.selectable, "True");
  }
  for (const choice of standardRows) {
    assert.equal(choice.section_id, "sec_stan_002");
    assert.equal(choice.selection_mode, "display_only");
    assert.equal(choice.status, "standard");
    assert.equal(choice.selectable, "False");
  }
});

test("required Badges default and replacement behavior stays production-equivalent", () => {
  for (const data of [loadGeneratedData(), loadShadowData()]) {
    for (const variant of data.variants) {
      const runtime = runtimeFor(data, variant.variant_id);
      assert.deepEqual(selectedRpos(runtime, new Set(["EYK", "EYT"])), ["EYT"]);
    }

    const eykRuntime = runtimeFor(data, "1lt_c07");
    eykRuntime.handleChoice(activeChoiceByRpo(eykRuntime, "EYK"));
    assert.deepEqual(selectedRpos(eykRuntime, new Set(["EYK", "EYT"])), ["EYK"]);
    assert.equal(eykRuntime.optionPrice(activeChoiceByRpo(eykRuntime, "EYK").option_id), 395);

    eykRuntime.handleChoice(activeChoiceByRpo(eykRuntime, "EYT"));
    assert.deepEqual(selectedRpos(eykRuntime, new Set(["EYK", "EYT"])), ["EYT"]);

    for (const blockerRpo of ["SFZ", "R88", "PCX"]) {
      const runtime = runtimeFor(data, "1lt_c07");
      runtime.handleChoice(activeChoiceByRpo(runtime, blockerRpo));
      assert.match(runtime.disableReasonForChoice(activeChoiceByRpo(runtime, "EYK")), new RegExp(`Blocked by ${blockerRpo}`));
      assert.equal(runtime.disableReasonForChoice(activeChoiceByRpo(runtime, "EYT")), "");
    }
  }
});

test("overlay rejects projected duplicate-RPO EYT fragments that omit the display-only duplicate rows", () => {
  const production = loadGeneratedData();
  const manifest = writeManifest(eytProjectionManifestRows());
  const fragment = writeFragment(production, production.choices.filter((choice) => choice.option_id === "opt_eyt_001"));

  const result = runOverlay(manifest, fragment);

  assert.notEqual(result.status, 0);
  assert.match(result.stderr, /Projected RPO EYT replacement is incomplete/);
  assert.match(result.stderr, /opt_eyt_002/);
});

test("overlay accepts projected duplicate-RPO EYT only when every production choice row for the RPO is emitted", () => {
  const production = loadGeneratedData();
  const manifest = writeManifest(eytProjectionManifestRows());
  const eytChoices = production.choices.filter((choice) => choice.rpo === "EYT");
  const fragment = writeFragment(production, eytChoices);

  const result = runOverlay(manifest, fragment);

  assert.equal(result.status, 0, result.stderr);
  const shadow = JSON.parse(result.stdout);
  assert.deepEqual(plain(normalizeChoices(shadow.choices.filter((choice) => choice.rpo === "EYT"))), plain(normalizeChoices(eytChoices)));
});

test("current manifest projects required Badges choices without claiming section metadata", () => {
  const production = loadGeneratedData();
  const owned = projectedOwnedRpos();

  assert.equal(owned.has("EYK"), true);
  assert.equal(owned.has("EYT"), true);
  assert.equal(manifestHas({ record_type: "guardedOption", rpo: "EYK", ownership: "production_guarded" }), false);
  assert.equal(manifestHas({ record_type: "guardedOption", target_option_id: "opt_eyt_001", ownership: "production_guarded" }), false);
  assert.equal(manifestHas({ record_type: "guardedOption", target_option_id: "opt_eyt_002", ownership: "production_guarded" }), false);
  assert.equal(activeManifestRows().some((row) => row.record_type === "section" || row.group_id === "sec_badg_001"), false);
  for (const [sourceRpo, targetRpo] of EYK_INBOUND_EXCLUDES) {
    assert.ok(rule(production, sourceRpo, targetRpo, "excludes"), `${sourceRpo} -> ${targetRpo} should exist in production`);
    assert.equal(manifestHas({ record_type: "rule", source_rpo: sourceRpo, target_rpo: targetRpo, ownership: "preserved_cross_boundary" }), true);
  }
});
