import assert from "node:assert/strict";
import { execFileSync, spawnSync } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import test from "node:test";

import { createRuntime, loadGeneratedData, loadShadowData } from "./runtime-harness.mjs";

const PYTHON = ".venv/bin/python";
const OVERLAY_SCRIPT = "scripts/stingray_csv_shadow_overlay.py";
const FRAGMENT_SCRIPT = "scripts/stingray_csv_first_slice.py";
const OWNERSHIP_MANIFEST = "data/stingray/validation/projected_slice_ownership.csv";
const EXPECTED_OWNED_RPOS = [
  "5ZC",
  "5ZD",
  "B6P",
  "BC4",
  "BC7",
  "BCP",
  "BCS",
  "D3V",
  "RNX",
  "RWH",
  "RWJ",
  "RXH",
  "RXJ",
  "SL1",
  "SL9",
  "SXB",
  "SXR",
  "SXT",
  "T0A",
  "TVS",
  "VWD",
  "WKQ",
  "WKR",
  "ZZ3",
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

function loadManifest(file = OWNERSHIP_MANIFEST) {
  return parseCsv(fs.readFileSync(file, "utf8"));
}

function emitLegacyFragment() {
  const output = execFileSync(PYTHON, [FRAGMENT_SCRIPT, "--emit-legacy-fragment"], {
    cwd: process.cwd(),
    encoding: "utf8",
    maxBuffer: 8 * 1024 * 1024,
  });
  return JSON.parse(output);
}

function runOverlay(args = []) {
  return spawnSync(PYTHON, [OVERLAY_SCRIPT, ...args], {
    cwd: process.cwd(),
    encoding: "utf8",
    maxBuffer: 8 * 1024 * 1024,
  });
}

function writeTempManifest(rows) {
  const tempDir = fs.mkdtempSync(path.join(os.tmpdir(), "stingray-ownership-"));
  const tempManifest = path.join(tempDir, "projected_slice_ownership.csv");
  const headers = Object.keys(rows[0]);
  fs.writeFileSync(tempManifest, `${headers.join(",")}\n${rows.map((row) => headers.map((header) => row[header]).join(",")).join("\n")}\n`);
  return tempManifest;
}

function activeManifestRows() {
  return loadManifest().filter((row) => row.active === "true");
}

function projectedOwnedRpos(rows = activeManifestRows()) {
  return rows.filter((row) => row.ownership === "projected_owned").map((row) => row.rpo).sort();
}

function preservedRows(rows = activeManifestRows()) {
  return rows
    .filter((row) => row.ownership === "preserved_cross_boundary")
    .map((row) => ({
      record_type: row.record_type,
      group_id: row.group_id || "",
      source_rpo: row.source_rpo,
      source_option_id: row.source_option_id || "",
      target_rpo: row.target_rpo,
      target_option_id: row.target_option_id || "",
      ownership: row.ownership,
    }))
    .sort((a, b) =>
      `${a.record_type}:${a.source_rpo}:${a.source_option_id}:${a.target_rpo}:${a.target_option_id}`.localeCompare(
        `${b.record_type}:${b.source_rpo}:${b.source_option_id}:${b.target_rpo}:${b.target_option_id}`
      )
    );
}

function optionIdByRpo(data, rpo) {
  const ids = new Set(data.choices.filter((choice) => choice.rpo === rpo).map((choice) => choice.option_id));
  assert.equal(ids.size, 1, `${rpo} should map to exactly one legacy option_id`);
  return [...ids][0];
}

function hasPdvVwdRule(data) {
  const pdv = optionIdByRpo(data, "PDV");
  const vwd = optionIdByRpo(data, "VWD");
  return data.rules.some((rule) => rule.source_id === pdv && rule.rule_type === "includes" && rule.target_id === vwd);
}

function hasPdvVwdPriceRule(data) {
  const pdv = optionIdByRpo(data, "PDV");
  const vwd = optionIdByRpo(data, "VWD");
  return data.priceRules.some((rule) => rule.condition_option_id === pdv && rule.target_option_id === vwd && Number(rule.price_value) === 0);
}

function rulesById(data, sourceId, targetId) {
  return data.rules.filter((rule) => rule.source_id === sourceId && rule.target_id === targetId);
}

function plain(value) {
  return JSON.parse(JSON.stringify(value));
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

function hasPreservedRow(rows, expected) {
  return rows.some((row) => Object.entries(expected).every(([key, value]) => row[key] === value));
}

function groupOwnershipRows(rows = activeManifestRows()) {
  return rows
    .filter((row) => (row.record_type === "exclusiveGroup" || row.record_type === "ruleGroup") && row.group_id)
    .map((row) => ({
      record_type: row.record_type,
      group_id: row.group_id || "",
      ownership: row.ownership,
    }))
    .sort((a, b) => `${a.record_type}:${a.group_id}:${a.ownership}`.localeCompare(`${b.record_type}:${b.group_id}:${b.ownership}`));
}

test("projected ownership manifest declares the current multi-slice control scope", () => {
  const rows = activeManifestRows();
  const preserved = preservedRows(rows);
  const guardedRows = rows
    .filter((row) => row.ownership === "production_guarded" && row.record_type === "guardedOption")
    .map((row) => ({
      record_type: row.record_type,
      rpo: row.rpo,
      target_option_id: row.target_option_id || "",
      ownership: row.ownership,
    }))
    .sort((a, b) => `${a.record_type}:${a.rpo}:${a.target_option_id}`.localeCompare(`${b.record_type}:${b.rpo}:${b.target_option_id}`));

  assert.deepEqual(projectedOwnedRpos(rows), EXPECTED_OWNED_RPOS);
  assert.equal(projectedOwnedRpos(rows).includes("PDV"), false);
  assert.equal(projectedOwnedRpos(rows).includes("PEF"), false);
  assert.equal(projectedOwnedRpos(rows).includes("CAV"), false);
  assert.equal(projectedOwnedRpos(rows).includes("RIA"), false);
  assert.deepEqual(guardedRows, [
    {
      record_type: "guardedOption",
      rpo: "",
      target_option_id: "opt_5zw_001",
      ownership: "production_guarded",
    },
    ...["5V7", "5ZU", "5ZZ", "GBA", "Z51", "ZYC"].map((rpo) => ({
      record_type: "guardedOption",
      rpo,
      target_option_id: "",
      ownership: "production_guarded",
    })),
  ]);
  assert.deepEqual(groupOwnershipRows(rows), [
    {
      record_type: "exclusiveGroup",
      group_id: "grp_spoiler_high_wing",
      ownership: "preserved_cross_boundary",
    },
    {
      record_type: "ruleGroup",
      group_id: "grp_5v7_spoiler_requirement",
      ownership: "production_guarded",
    },
    {
      record_type: "ruleGroup",
      group_id: "grp_5zu_paint_requirement",
      ownership: "production_guarded",
    },
  ]);
  for (const expected of [
    {
      record_type: "priceRule",
      group_id: "",
      source_rpo: "PDV",
      source_option_id: "",
      target_rpo: "VWD",
      target_option_id: "",
      ownership: "preserved_cross_boundary",
    },
    { record_type: "rule", group_id: "", source_rpo: "PDV", source_option_id: "", target_rpo: "VWD", target_option_id: "", ownership: "preserved_cross_boundary" },
    { record_type: "rule", group_id: "", source_rpo: "WKQ", source_option_id: "", target_rpo: "", target_option_id: "opt_5zw_001", ownership: "preserved_cross_boundary" },
    { record_type: "rule", group_id: "", source_rpo: "RNX", source_option_id: "", target_rpo: "", target_option_id: "opt_5zw_001", ownership: "preserved_cross_boundary" },
    { record_type: "rule", group_id: "", source_rpo: "TVS", source_option_id: "", target_rpo: "T0A", target_option_id: "", ownership: "preserved_cross_boundary" },
    { record_type: "rule", group_id: "", source_rpo: "5ZZ", source_option_id: "", target_rpo: "T0A", target_option_id: "", ownership: "preserved_cross_boundary" },
    { record_type: "rule", group_id: "", source_rpo: "5ZU", source_option_id: "", target_rpo: "T0A", target_option_id: "", ownership: "preserved_cross_boundary" },
    { record_type: "rule", group_id: "", source_rpo: "", source_option_id: "opt_5zw_001", target_rpo: "T0A", target_option_id: "", ownership: "preserved_cross_boundary" },
    { record_type: "priceRule", group_id: "", source_rpo: "Z51", source_option_id: "", target_rpo: "TVS", target_option_id: "", ownership: "preserved_cross_boundary" },
    { record_type: "ruleGroup", group_id: "", source_rpo: "5V7", source_option_id: "", target_rpo: "5ZZ", target_option_id: "", ownership: "preserved_cross_boundary" },
    { record_type: "ruleGroup", group_id: "", source_rpo: "5ZU", source_option_id: "", target_rpo: "GBA", target_option_id: "", ownership: "preserved_cross_boundary" },
  ]) {
    assert.equal(hasPreservedRow(preserved, expected), true, `missing preserved row ${JSON.stringify(expected)}`);
  }
});

test("legacy fragment projected RPO scope equals the ownership manifest", () => {
  const production = loadGeneratedData();
  const fragment = emitLegacyFragment();
  const fragmentRpos = [...new Set(fragment.choices.map((choice) => choice.rpo))].sort();
  const pdv = optionIdByRpo(production, "PDV");
  const vwd = optionIdByRpo(production, "VWD");

  assert.deepEqual(fragment.validation_errors, []);
  assert.deepEqual(fragmentRpos, projectedOwnedRpos());
  assert.equal(fragmentRpos.includes("PDV"), false);
  assert.equal(fragmentRpos.includes("5ZW"), false);
  assert.equal(fragment.rules.some((rule) => rule.source_id === pdv && rule.target_id === vwd), false);
  assert.equal(fragment.priceRules.some((rule) => rule.condition_option_id === pdv && rule.target_option_id === vwd), false);
});

test("production keeps 5ZW as a rule-only legacy option id", () => {
  const production = loadGeneratedData();

  assert.equal(production.choices.some((choice) => choice.rpo === "5ZW" || choice.option_id === "opt_5zw_001"), false);
  assert.equal(production.rules.some((rule) => rule.target_id === "opt_5zw_001"), true);
  assert.equal(production.rules.some((rule) => rule.source_id === "opt_5zw_001"), true);
  assert.equal(projectedOwnedRpos().includes("5ZW"), false);
});

test("shadow overlay preserves manifest-declared PDV to VWD production-owned behavior", () => {
  const production = loadGeneratedData();
  const shadow = loadShadowData();

  assert.deepEqual(Object.keys(shadow).sort(), Object.keys(production).sort());
  assert.equal(hasPdvVwdRule(production), true);
  assert.equal(hasPdvVwdRule(shadow), true);
  assert.equal(hasPdvVwdPriceRule(production), true);
  assert.equal(hasPdvVwdPriceRule(shadow), true);
  assert.equal(rulesById(shadow, "opt_wkq_001", "opt_5zw_001").length, 1);
  assert.equal(rulesById(shadow, "opt_rnx_001", "opt_5zw_001").length, 1);
  assert.deepEqual(plain(rulesById(shadow, "opt_wkq_001", "opt_5zw_001")), plain(rulesById(production, "opt_wkq_001", "opt_5zw_001")));
  assert.deepEqual(plain(rulesById(shadow, "opt_rnx_001", "opt_5zw_001")), plain(rulesById(production, "opt_rnx_001", "opt_5zw_001")));

  const directRuntime = runtimeFor(shadow, "1lt_c07");
  const vwd = activeChoiceByRpo(directRuntime, "VWD");
  directRuntime.state.selected.add(vwd.option_id);
  directRuntime.state.userSelected.add(vwd.option_id);
  assert.equal(directRuntime.optionPrice(vwd.option_id), 250);

  const packageRuntime = runtimeFor(shadow, "1lt_c07");
  const pdv = activeChoiceByRpo(packageRuntime, "PDV");
  const packageVwd = activeChoiceByRpo(packageRuntime, "VWD");
  packageRuntime.state.selected.add(pdv.option_id);
  packageRuntime.state.userSelected.add(pdv.option_id);
  assert.equal(packageRuntime.computeAutoAdded().has(packageVwd.option_id), true);
  assert.equal(packageRuntime.optionPrice(packageVwd.option_id), 0);
});

test("overlay rejects a manifest that omits a projected fragment RPO", () => {
  const rows = loadManifest().filter((row) => row.rpo !== "RXH");
  const tempManifest = writeTempManifest(rows);

  const result = runOverlay(["--ownership-manifest", tempManifest]);

  assert.notEqual(result.status, 0);
  assert.match(result.stderr, /Projected fragment RPO scope changed/);
});

test("overlay rejects an unclassified cross-boundary production record", () => {
  const rows = loadManifest().filter((row) => !(row.ownership === "preserved_cross_boundary" && row.source_rpo === "PDV" && row.target_rpo === "VWD"));
  const tempManifest = writeTempManifest(rows);

  const result = runOverlay(["--ownership-manifest", tempManifest]);

  assert.notEqual(result.status, 0);
  assert.match(result.stderr, /unclassified cross-boundary/);
});

test("overlay rejects omitted id-based 5ZW preserved records", () => {
  const rows = loadManifest().filter((row) => row.target_option_id !== "opt_5zw_001");
  const tempManifest = writeTempManifest(rows);

  const result = runOverlay(["--ownership-manifest", tempManifest]);

  assert.notEqual(result.status, 0);
  assert.match(result.stderr, /unclassified cross-boundary/);
  assert.match(result.stderr, /opt_5zw_001/);
});

const validationCases = [
  [
    "duplicate active projected-owned RPO",
    (rows) => [...rows, { ...rows.find((row) => row.rpo === "B6P") }],
    /duplicate active projected_owned RPO B6P/,
  ],
  [
    "duplicate active preserved cross-boundary row",
    (rows) => [...rows, { ...rows.find((row) => row.record_type === "rule" && row.source_rpo === "PDV" && row.target_rpo === "VWD") }],
    /duplicate active preserved_cross_boundary row/,
  ],
  [
    "unsupported ownership value",
    (rows) => rows.map((row) => (row.rpo === "B6P" ? { ...row, ownership: "external_source" } : row)),
    /unsupported ownership value/,
  ],
  [
    "unsupported record type",
    (rows) => rows.map((row) => (row.rpo === "B6P" ? { ...row, record_type: "dependency" } : row)),
    /unsupported record_type value/,
  ],
  [
    "unsupported active value",
    (rows) => rows.map((row) => (row.rpo === "B6P" ? { ...row, active: "yes" } : row)),
    /unsupported active value/,
  ],
  [
    "projected-owned row missing rpo",
    (rows) => rows.map((row) => (row.rpo === "B6P" ? { ...row, rpo: "" } : row)),
    /projected_owned row is missing rpo/,
  ],
  [
    "preserved cross-boundary row missing source",
    (rows) => rows.map((row) => (row.record_type === "rule" && row.source_rpo === "PDV" && row.target_rpo === "VWD" ? { ...row, source_rpo: "" } : row)),
    /preserved_cross_boundary row is missing source_rpo\/source_option_id or target_rpo\/target_option_id/,
  ],
  [
    "group record missing group_id",
    (rows) => rows.map((row) => (row.record_type === "exclusiveGroup" && row.group_id === "grp_spoiler_high_wing" ? { ...row, group_id: "" } : row)),
    /group ownership row is missing group_id/,
  ],
  [
    "group record mixed with RPO refs",
    (rows) => rows.map((row) => (row.record_type === "exclusiveGroup" && row.group_id === "grp_spoiler_high_wing" ? { ...row, source_rpo: "TVS" } : row)),
    /group ownership row should not set rpo or source\/target refs/,
  ],
  [
    "duplicate active group ownership row",
    (rows) => [...rows, { ...rows.find((row) => row.record_type === "exclusiveGroup" && row.group_id === "grp_spoiler_high_wing") }],
    /duplicate active group ownership row/,
  ],
  [
    "preserved group_id missing from production",
    (rows) => rows.map((row) => (row.record_type === "exclusiveGroup" && row.group_id === "grp_spoiler_high_wing" ? { ...row, group_id: "grp_missing_spoiler" } : row)),
    /Preserved or guarded production groups do not exist/,
  ],
];

for (const [name, mutateRows, messagePattern] of validationCases) {
  test(`overlay validates ownership manifest: ${name}`, () => {
    const tempManifest = writeTempManifest(mutateRows(loadManifest()));

    const result = runOverlay(["--ownership-manifest", tempManifest]);

    assert.notEqual(result.status, 0);
    assert.match(result.stderr, messagePattern);
  });
}
