import assert from "node:assert/strict";
import { execFileSync, spawnSync } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import test from "node:test";

import { loadGeneratedData } from "./runtime-harness.mjs";

const PYTHON = ".venv/bin/python";
const FRAGMENT_SCRIPT = "scripts/stingray_csv_first_slice.py";
const OVERLAY_SCRIPT = "scripts/stingray_csv_shadow_overlay.py";
const OWNERSHIP_MANIFEST = "data/stingray/validation/projected_slice_ownership.csv";
const GUARDED_OPTION_IDS = ["opt_5vm_001", "opt_5w8_001", "opt_5zw_001", "opt_cf8_001", "opt_ryq_001"];

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

function loadManifest() {
  return parseCsv(fs.readFileSync(OWNERSHIP_MANIFEST, "utf8"));
}

function activeManifestRows() {
  return loadManifest().filter((row) => row.active === "true");
}

function writeTempManifest(rows) {
  const tempDir = fs.mkdtempSync(path.join(os.tmpdir(), "stingray-interior-source-ownership-"));
  const tempManifest = path.join(tempDir, "projected_slice_ownership.csv");
  const headers = Object.keys(rows[0]);
  fs.writeFileSync(tempManifest, `${headers.join(",")}\n${rows.map((row) => headers.map((header) => row[header]).join(",")).join("\n")}\n`);
  return tempManifest;
}

function writeProductionData(data) {
  const tempDir = fs.mkdtempSync(path.join(os.tmpdir(), "stingray-interior-source-production-"));
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

function emitLegacyFragment() {
  const output = execFileSync(PYTHON, [FRAGMENT_SCRIPT, "--emit-legacy-fragment"], {
    cwd: process.cwd(),
    encoding: "utf8",
    maxBuffer: 8 * 1024 * 1024,
  });
  return JSON.parse(output);
}

function plain(value) {
  return JSON.parse(JSON.stringify(value));
}

function structuredInteriorSourceIds(data) {
  const interiorIds = new Set(data.interiors.map((interior) => interior.interior_id));
  const sourceIds = new Set();
  for (const rule of data.rules) {
    if (interiorIds.has(rule.source_id)) sourceIds.add(rule.source_id);
    if (interiorIds.has(rule.target_id)) sourceIds.add(rule.target_id);
  }
  for (const rule of data.priceRules) {
    if (interiorIds.has(rule.condition_option_id)) sourceIds.add(rule.condition_option_id);
    if (interiorIds.has(rule.target_option_id)) sourceIds.add(rule.target_option_id);
  }
  return [...sourceIds].sort();
}

function structuredInteriorRows(data) {
  const interiorIds = new Set(structuredInteriorSourceIds(data));
  return {
    rules: data.rules.filter((rule) => interiorIds.has(rule.source_id) || interiorIds.has(rule.target_id)),
    priceRules: data.priceRules.filter((rule) => interiorIds.has(rule.condition_option_id) || interiorIds.has(rule.target_option_id)),
  };
}

function guardedOptionRow(optionId) {
  return activeManifestRows().find(
    (row) =>
      row.record_type === "guardedOption" &&
      row.ownership === "production_guarded" &&
      row.target_option_id === optionId &&
      row.rpo === ""
  );
}

test("3LT structured references resolve through the interior source namespace", () => {
  const production = loadGeneratedData();
  const interiorIds = new Set(production.interiors.map((interior) => interior.interior_id));
  const choiceIds = new Set(production.choices.map((choice) => choice.option_id));
  const sourceIds = structuredInteriorSourceIds(production);
  const rows = structuredInteriorRows(production);
  const targetRpos = new Set([
    ...rows.rules.map((rule) => production.choices.find((choice) => choice.option_id === rule.target_id)?.rpo),
    ...rows.priceRules.map((rule) => production.choices.find((choice) => choice.option_id === rule.target_option_id)?.rpo),
  ]);

  assert.equal(sourceIds.length, 30);
  assert.equal(sourceIds.every((id) => id.startsWith("3LT_")), true);
  assert.equal(sourceIds.every((id) => interiorIds.has(id)), true);
  assert.equal(sourceIds.some((id) => choiceIds.has(id)), false);
  assert.deepEqual([...targetRpos].filter(Boolean).sort(), ["379", "3A9", "3F9", "3N9", "R6X"]);
  assert.equal(rows.rules.length, 30);
  assert.equal(rows.priceRules.length, 15);
  for (const interiorId of sourceIds) {
    assert.equal(guardedOptionRow(interiorId), undefined, `${interiorId} should not need production_guarded option ownership`);
  }
});

test("interior source ids do not emit fake CSV selectables", () => {
  const production = loadGeneratedData();
  const fragment = emitLegacyFragment();
  const sourceIds = new Set(structuredInteriorSourceIds(production));

  assert.deepEqual(fragment.validation_errors, []);
  assert.equal(fragment.choices.some((choice) => sourceIds.has(choice.option_id) || sourceIds.has(choice.rpo)), false);
  assert.equal(fragment.rules.some((rule) => sourceIds.has(rule.source_id) || sourceIds.has(rule.target_id)), false);
  assert.equal(fragment.priceRules.some((rule) => sourceIds.has(rule.condition_option_id) || sourceIds.has(rule.target_option_id)), false);
});

test("existing rule-only option ids remain explicitly guarded", () => {
  const production = loadGeneratedData();
  const choiceIds = new Set(production.choices.map((choice) => choice.option_id));

  for (const optionId of GUARDED_OPTION_IDS) {
    assert.equal(choiceIds.has(optionId), false);
    assert.ok(guardedOptionRow(optionId), `${optionId} should remain production_guarded`);
  }
});

test("overlay accepts current structured interior source ids without guarded option rows", () => {
  const result = runOverlay();

  assert.equal(result.status, 0, result.stderr);
});

test("overlay rejects unknown non-choice structured references", () => {
  const production = plain(loadGeneratedData());
  const template = production.rules.find((rule) => rule.source_id.startsWith("3LT_"));
  assert.ok(template, "production should include interior-sourced structured rules");
  production.rules.push({
    ...template,
    rule_id: "rule_unknown_non_choice_source_includes_r6x",
    source_id: "UNKNOWN_NON_CHOICE_SOURCE",
  });

  const result = runOverlay(["--production-data", writeProductionData(production)]);

  assert.notEqual(result.status, 0);
  assert.match(result.stderr, /unknown structured non-choice refs/);
  assert.match(result.stderr, /UNKNOWN_NON_CHOICE_SOURCE/);
});

test("overlay rejects interior source ids declared as guarded option ids", () => {
  const production = loadGeneratedData();
  const interiorId = structuredInteriorSourceIds(production)[0];
  const rows = loadManifest();
  rows.push({
    ...rows[0],
    record_type: "guardedOption",
    group_id: "",
    source_rpo: "",
    source_option_id: "",
    target_rpo: "",
    target_option_id: interiorId,
    rpo: "",
    ownership: "production_guarded",
    reason: "test fixture invalid interior source namespace",
    active: "true",
  });

  const result = runOverlay(["--ownership-manifest", writeTempManifest(rows)]);

  assert.notEqual(result.status, 0);
  assert.match(result.stderr, /interior source ids cannot be production_guarded option refs/);
  assert.match(result.stderr, new RegExp(interiorId));
});
