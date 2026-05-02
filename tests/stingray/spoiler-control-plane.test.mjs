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
const SPOILER_GUARDED_RPOS = ["T0A", "5ZZ", "5ZU", "5V7", "Z51", "ZYC", "GBA"];
const SPOILER_NOT_PROJECTED_RPOS = new Set([...SPOILER_GUARDED_RPOS, "5ZW"]);

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

function writeTempManifest(rows) {
  const tempDir = fs.mkdtempSync(path.join(os.tmpdir(), "stingray-spoiler-ownership-"));
  const tempManifest = path.join(tempDir, "projected_slice_ownership.csv");
  const headers = Object.keys(rows[0]);
  fs.writeFileSync(tempManifest, `${headers.join(",")}\n${rows.map((row) => headers.map((header) => row[header]).join(",")).join("\n")}\n`);
  return tempManifest;
}

function writeTempJson(value) {
  const tempDir = fs.mkdtempSync(path.join(os.tmpdir(), "stingray-spoiler-fragment-"));
  const tempJson = path.join(tempDir, "fragment.json");
  fs.writeFileSync(tempJson, `${JSON.stringify(value)}\n`);
  return tempJson;
}

function runOverlay(args = []) {
  return spawnSync(PYTHON, [OVERLAY_SCRIPT, ...args], {
    cwd: process.cwd(),
    encoding: "utf8",
    maxBuffer: 8 * 1024 * 1024,
  });
}

function activeManifestRows() {
  return loadManifest().filter((row) => row.active === "true");
}

function optionIdByRpo(data, rpo) {
  const ids = new Set(data.choices.filter((choice) => choice.rpo === rpo).map((choice) => choice.option_id));
  assert.equal(ids.size, 1, `${rpo} should map to exactly one generated option_id`);
  return [...ids][0];
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

function handleRpo(runtime, rpo) {
  const choice = activeChoiceByRpo(runtime, rpo);
  runtime.handleChoice(choice);
  return choice;
}

function selectedRpos(runtime, allowedRpos) {
  return [...runtime.state.selected]
    .map((optionId) => runtime.activeChoiceRows().find((choice) => choice.option_id === optionId)?.rpo)
    .filter((rpo) => rpo && allowedRpos.has(rpo))
    .sort();
}

function plain(value) {
  return JSON.parse(JSON.stringify(value));
}

function preservedRowExists(rows, expected) {
  return rows.some((row) =>
    Object.entries(expected).every(([key, value]) => row[key] === value)
  );
}

function groupRows(rows = activeManifestRows()) {
  return rows
    .filter((row) => (row.record_type === "exclusiveGroup" || row.record_type === "ruleGroup") && row.group_id)
    .map((row) => ({
      record_type: row.record_type,
      group_id: row.group_id,
      ownership: row.ownership,
    }))
    .sort((a, b) => `${a.record_type}:${a.group_id}:${a.ownership}`.localeCompare(`${b.record_type}:${b.group_id}:${b.ownership}`));
}

function emitFragment() {
  return JSON.parse(execFileSync(PYTHON, [FRAGMENT_SCRIPT, "--emit-legacy-fragment"], {
    cwd: process.cwd(),
    encoding: "utf8",
    maxBuffer: 8 * 1024 * 1024,
  }));
}

test("Pass 23 projects only TVS while other spoiler-adjacent options stay guarded", () => {
  const production = loadGeneratedData();
  const rows = activeManifestRows();
  const projectedRpos = rows.filter((row) => row.ownership === "projected_owned").map((row) => row.rpo);
  const guardedRpos = rows.filter((row) => row.ownership === "production_guarded" && row.record_type === "guardedOption").map((row) => row.rpo).filter(Boolean).sort();

  assert.deepEqual(guardedRpos, [...SPOILER_GUARDED_RPOS].sort());
  assert.equal(projectedRpos.includes("TVS"), true);
  for (const rpo of SPOILER_NOT_PROJECTED_RPOS) {
    assert.equal(projectedRpos.includes(rpo), false, `${rpo} should not be projected-owned in Pass 23`);
  }
  assert.equal(rows.some((row) => row.ownership === "production_guarded" && row.target_option_id === "opt_5zw_001"), true);
  assert.equal(production.choices.some((choice) => choice.rpo === "5ZW" || choice.option_id === "opt_5zw_001"), false);
});

test("Pass 23 preserves mixed-boundary spoiler group identities without projecting them", () => {
  assert.deepEqual(groupRows(), [
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
});

test("spoiler requires_any ruleGroups are production-owned and preserved in shadow data", () => {
  const production = loadGeneratedData();
  const shadow = loadShadowData();
  const rows = activeManifestRows();
  const fiveV7 = optionIdByRpo(production, "5V7");
  const fiveZU = optionIdByRpo(production, "5ZU");
  const fiveZZ = optionIdByRpo(production, "5ZZ");
  const fiveZuPaintTargets = ["G8G", "GBA", "GKZ"].map((rpo) => optionIdByRpo(production, rpo)).sort();

  assert.deepEqual(plain(shadow.ruleGroups), plain(production.ruleGroups));

  const fiveV7Group = shadow.ruleGroups.find((group) => group.group_id === "grp_5v7_spoiler_requirement");
  assert.equal(fiveV7Group.group_type, "requires_any");
  assert.equal(fiveV7Group.source_id, fiveV7);
  assert.deepEqual([...fiveV7Group.target_ids].sort(), [fiveZU, fiveZZ].sort());
  assert.equal(fiveV7Group.target_ids.includes("opt_5zw_001"), false);
  assert.equal(preservedRowExists(rows, { record_type: "ruleGroup", source_rpo: "5V7", target_rpo: "5ZU" }), true);
  assert.equal(preservedRowExists(rows, { record_type: "ruleGroup", source_rpo: "5V7", target_rpo: "5ZZ" }), true);

  const fiveZuGroup = shadow.ruleGroups.find((group) => group.group_id === "grp_5zu_paint_requirement");
  assert.equal(fiveZuGroup.group_type, "requires_any");
  assert.equal(fiveZuGroup.source_id, fiveZU);
  assert.deepEqual([...fiveZuGroup.target_ids].sort(), fiveZuPaintTargets);
});

test("spoiler exclusive group is production-owned and preserved in shadow data", () => {
  const production = loadGeneratedData();
  const shadow = loadShadowData();
  const group = shadow.exclusiveGroups.find((item) => item.group_id === "grp_spoiler_high_wing");
  const productionGroup = production.exclusiveGroups.find((item) => item.group_id === "grp_spoiler_high_wing");
  const expectedMembers = ["T0A", "TVS", "5ZZ", "5ZU"].map((rpo) => optionIdByRpo(production, rpo)).sort();

  assert.deepEqual(plain(group), plain(productionGroup));
  assert.deepEqual([...group.option_ids].sort(), expectedMembers);
});

test("spoiler replace rules and 5ZW asymmetry remain production-owned", () => {
  const production = loadGeneratedData();
  const shadow = loadShadowData();
  const t0a = optionIdByRpo(production, "T0A");

  for (const rpo of ["TVS", "5ZZ", "5ZU"]) {
    const source = optionIdByRpo(production, rpo);
    const productionRule = production.rules.find((rule) => rule.source_id === source && rule.target_id === t0a);
    const shadowRule = shadow.rules.find((rule) => rule.source_id === source && rule.target_id === t0a);
    assert.equal(productionRule.runtime_action, "replace");
    assert.deepEqual(plain(shadowRule), plain(productionRule));
  }

  const fiveZwRule = shadow.rules.find((rule) => rule.source_id === "opt_5zw_001" && rule.target_id === t0a);
  assert.equal(fiveZwRule.runtime_action, "active");
  assert.equal(fiveZwRule.rule_type, "excludes");
});

test("Z51 to TVS price override remains classified and production-owned", () => {
  const production = loadGeneratedData();
  const shadow = loadShadowData();
  const z51 = optionIdByRpo(production, "Z51");
  const tvs = optionIdByRpo(production, "TVS");
  const productionRule = production.priceRules.find((rule) => rule.condition_option_id === z51 && rule.target_option_id === tvs);
  const shadowRule = shadow.priceRules.find((rule) => rule.condition_option_id === z51 && rule.target_option_id === tvs);

  assert.equal(Number(productionRule.price_value), 0);
  assert.deepEqual(plain(shadowRule), plain(productionRule));
  assert.equal(preservedRowExists(activeManifestRows(), { record_type: "priceRule", source_rpo: "Z51", target_rpo: "TVS" }), true);
});

test("spoiler-adjacent runtime cleanup boundaries remain production-runtime-owned and parity-guarded", () => {
  const production = runtimeFor(loadGeneratedData(), "1lt_c07");
  const shadow = runtimeFor(loadShadowData(), "1lt_c07");

  for (const runtime of [production, shadow]) {
    handleRpo(runtime, "ZYC");
    const gba = activeChoiceByRpo(runtime, "GBA");
    assert.equal(runtime.disableReasonForChoice(gba), "");
    runtime.handleChoice(gba);
    assert.deepEqual(selectedRpos(runtime, new Set(["GBA", "ZYC"])), ["GBA"]);
  }

  for (const data of [loadGeneratedData(), loadShadowData()]) {
    const runtime = runtimeFor(data, "1lt_c07");
    for (const rpo of ["FE2", "Z51"]) {
      const choice = activeChoiceByRpo(runtime, rpo);
      runtime.state.selected.add(choice.option_id);
      runtime.state.userSelected.add(choice.option_id);
    }
    runtime.reconcileSelections();
    assert.equal(selectedRpos(runtime, new Set(["FE1", "FE2", "FE3", "Z51"])).includes("FE1"), false);
    assert.equal(selectedRpos(runtime, new Set(["FE1", "FE2", "FE3", "Z51"])).includes("FE2"), false);
    assert.equal(runtime.computeAutoAdded().has(optionIdByRpo(data, "FE3")), true);
  }
});

test("overlay rejects missing preserved TVS replace record", () => {
  const rows = loadManifest().filter(
    (row) =>
      !(row.record_type === "rule" && row.source_rpo === "TVS" && row.target_rpo === "T0A")
  );
  const result = runOverlay(["--ownership-manifest", writeTempManifest(rows)]);

  assert.notEqual(result.status, 0);
  assert.match(result.stderr, /unclassified cross-boundary records/);
  assert.match(result.stderr, /opt_tvs_001/);
});

test("overlay rejects missing preserved 5ZW rule-only asymmetry record", () => {
  const rows = loadManifest().filter(
    (row) =>
      !(row.record_type === "rule" && row.source_option_id === "opt_5zw_001" && row.target_rpo === "T0A")
  );
  const result = runOverlay(["--ownership-manifest", writeTempManifest(rows)]);

  assert.notEqual(result.status, 0);
  assert.match(result.stderr, /unclassified guarded production records/);
  assert.match(result.stderr, /opt_5zw_001/);
});

test("overlay rejects missing preserved spoiler ruleGroup classifications", () => {
  const rows = loadManifest().filter(
    (row) =>
      !(row.record_type === "ruleGroup" && row.source_rpo === "5V7" && row.target_rpo === "5ZZ")
  );
  const result = runOverlay(["--ownership-manifest", writeTempManifest(rows)]);

  assert.notEqual(result.status, 0);
  assert.match(result.stderr, /unclassified guarded production records/);
  assert.match(result.stderr, /opt_5v7_001/);
});

test("overlay rejects missing guarded spoiler exclusiveGroup classification", () => {
  const rows = loadManifest().filter((row) => row.group_id !== "grp_spoiler_high_wing");
  const result = runOverlay(["--ownership-manifest", writeTempManifest(rows)]);

  assert.notEqual(result.status, 0);
  assert.match(result.stderr, /unclassified guarded production groups/);
  assert.match(result.stderr, /grp_spoiler_high_wing/);
});

test("overlay validates projected exclusiveGroup replacement from controlled fragments", () => {
  const production = loadGeneratedData();
  const fragment = emitFragment();
  const group = production.exclusiveGroups.find((item) => item.group_id === "grp_spoiler_high_wing");
  fragment.exclusiveGroups = [...fragment.exclusiveGroups, group];
  const rows = loadManifest()
    .filter((row) => row.group_id !== "grp_spoiler_high_wing")
    .concat({
      record_type: "exclusiveGroup",
      group_id: "grp_spoiler_high_wing",
      source_rpo: "",
      source_option_id: "",
      target_rpo: "",
      target_option_id: "",
      rpo: "",
      ownership: "projected_owned",
      reason: "Controlled test fragment projects spoiler exclusive group identity",
      active: "true",
    });
  const result = runOverlay(["--ownership-manifest", writeTempManifest(rows), "--fragment-json", writeTempJson(fragment)]);

  assert.equal(result.status, 0, result.stderr);
  const shadow = JSON.parse(result.stdout);
  assert.deepEqual(plain(shadow.exclusiveGroups.find((item) => item.group_id === "grp_spoiler_high_wing")), plain(group));
});

test("overlay rejects projected ruleGroup ownership when the fragment does not provide it", () => {
  const rows = loadManifest()
    .filter((row) => row.group_id !== "grp_5v7_spoiler_requirement")
    .concat({
      record_type: "ruleGroup",
      group_id: "grp_5v7_spoiler_requirement",
      source_rpo: "",
      source_option_id: "",
      target_rpo: "",
      target_option_id: "",
      rpo: "",
      ownership: "projected_owned",
      reason: "Controlled test expects projected ruleGroup replacement",
      active: "true",
    });
  const result = runOverlay(["--ownership-manifest", writeTempManifest(rows)]);

  assert.notEqual(result.status, 0);
  assert.match(result.stderr, /ruleGroups projected group is missing from fragment/);
  assert.match(result.stderr, /grp_5v7_spoiler_requirement/);
});

test("overlay validates projected ruleGroup replacement from controlled fragments", () => {
  const production = loadGeneratedData();
  const fragment = emitFragment();
  const group = production.ruleGroups.find((item) => item.group_id === "grp_5v7_spoiler_requirement");
  fragment.ruleGroups = [...fragment.ruleGroups, group];
  const rows = loadManifest()
    .filter((row) => row.group_id !== "grp_5v7_spoiler_requirement")
    .concat({
      record_type: "ruleGroup",
      group_id: "grp_5v7_spoiler_requirement",
      source_rpo: "",
      source_option_id: "",
      target_rpo: "",
      target_option_id: "",
      rpo: "",
      ownership: "projected_owned",
      reason: "Controlled test fragment projects spoiler ruleGroup identity",
      active: "true",
    });
  const result = runOverlay(["--ownership-manifest", writeTempManifest(rows), "--fragment-json", writeTempJson(fragment)]);

  assert.equal(result.status, 0, result.stderr);
  const shadow = JSON.parse(result.stdout);
  assert.deepEqual(plain(shadow.ruleGroups.find((item) => item.group_id === "grp_5v7_spoiler_requirement")), plain(group));
});

test("overlay rejects missing preserved spoiler priceRule classifications", () => {
  const rows = loadManifest().filter(
    (row) =>
      !(row.record_type === "priceRule" && row.source_rpo === "Z51" && row.target_rpo === "TVS")
  );
  const result = runOverlay(["--ownership-manifest", writeTempManifest(rows)]);

  assert.notEqual(result.status, 0);
  assert.match(result.stderr, /unclassified cross-boundary records/);
  assert.match(result.stderr, /opt_z51_001/);
});
