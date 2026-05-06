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
const RULE_ONLY_IDS = ["opt_5vm_001", "opt_5w8_001"];
const RULE_ONLY_RPOS = ["5VM", "5W8"];
const CSV_OWNED_RULE_ONLY_KEYS = new Set([
  "5V7->opt_5vm_001:excludes:False:active",
  "5V7->opt_5w8_001:excludes:False:active",
  "PCU->opt_5vm_001:excludes:False:active",
  "PCU->opt_5w8_001:excludes:False:active",
  "opt_5vm_001->STI:excludes:False:active",
  "opt_5w8_001->STI:excludes:False:active",
  "STI->opt_5vm_001:excludes:False:active",
  "STI->opt_5w8_001:excludes:False:active",
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

function loadManifest() {
  return parseCsv(fs.readFileSync(OWNERSHIP_MANIFEST, "utf8"));
}

function activeManifestRows() {
  return loadManifest().filter((row) => row.active === "true");
}

function writeTempManifest(rows) {
  const tempDir = fs.mkdtempSync(path.join(os.tmpdir(), "stingray-rule-only-ground-effects-"));
  const tempManifest = path.join(tempDir, "projected_slice_ownership.csv");
  const headers = Object.keys(rows[0]);
  fs.writeFileSync(tempManifest, `${headers.join(",")}\n${rows.map((row) => headers.map((header) => row[header]).join(",")).join("\n")}\n`);
  return tempManifest;
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

function optionIdByRpo(data, rpo) {
  const ids = new Set(data.choices.filter((choice) => choice.rpo === rpo).map((choice) => choice.option_id));
  assert.equal(ids.size, 1, `${rpo} should map to exactly one production option_id`);
  return [...ids][0];
}

function rpoByOptionId(data, optionId) {
  return data.choices.find((choice) => choice.option_id === optionId)?.rpo || optionId;
}

function ruleKey(data, rule) {
  return `${rpoByOptionId(data, rule.source_id)}->${rpoByOptionId(data, rule.target_id)}:${rule.rule_type}:${rule.auto_add}:${rule.runtime_action}`;
}

function ruleOnlyRules(data) {
  const ids = new Set(RULE_ONLY_IDS);
  return data.rules.filter((rule) => ids.has(rule.source_id) || ids.has(rule.target_id)).sort((a, b) => ruleKey(data, a).localeCompare(ruleKey(data, b)));
}

function manifestSideMatches(data, rowRpo, rowOptionId, optionId) {
  if (rowOptionId) return rowOptionId === optionId;
  if (rowRpo) return optionIdByRpo(data, rowRpo) === optionId;
  return false;
}

function hasPreservedRuleRow(data, rule) {
  return activeManifestRows().some(
    (row) =>
      row.record_type === "rule" &&
      row.ownership === "preserved_cross_boundary" &&
      manifestSideMatches(data, row.source_rpo, row.source_option_id, rule.source_id) &&
      manifestSideMatches(data, row.target_rpo, row.target_option_id, rule.target_id)
  );
}

function hasGuardedOption(optionId) {
  return activeManifestRows().some(
    (row) =>
      row.record_type === "guardedOption" &&
      row.ownership === "production_guarded" &&
      row.target_option_id === optionId &&
      row.rpo === ""
  );
}

test("production keeps 5VM and 5W8 as guarded rule-only legacy option ids", () => {
  const production = loadGeneratedData();
  const fragment = emitLegacyFragment();

  for (const rpo of RULE_ONLY_RPOS) {
    assert.equal(production.choices.some((choice) => choice.rpo === rpo), false);
    assert.equal(fragment.choices.some((choice) => choice.rpo === rpo), false);
    assert.equal(activeManifestRows().some((row) => row.rpo === rpo && row.ownership === "projected_owned"), false);
  }
  for (const optionId of RULE_ONLY_IDS) {
    assert.equal(production.choices.some((choice) => choice.option_id === optionId), false);
    assert.equal(fragment.choices.some((choice) => choice.option_id === optionId), false);
    assert.equal(production.rules.some((rule) => rule.source_id === optionId || rule.target_id === optionId), true);
    assert.equal(hasGuardedOption(optionId), true);
  }
});

test("5VM and 5W8 production rules remain explicit preserved rows except CSV-owned reference rules", () => {
  const production = loadGeneratedData();

  const actualRuleKeys = JSON.parse(JSON.stringify(ruleOnlyRules(production).map((rule) => ruleKey(production, rule))));

  assert.deepEqual(actualRuleKeys, [
    "5V7->opt_5vm_001:excludes:False:active",
    "5V7->opt_5w8_001:excludes:False:active",
    "opt_5vm_001->5V7:excludes:False:active",
    "opt_5vm_001->5ZU:requires:False:active",
    "opt_5vm_001->5ZZ:requires:False:active",
    "opt_5vm_001->opt_5w8_001:excludes:False:active",
    "opt_5vm_001->opt_5zw_001:requires:False:active",
    "opt_5vm_001->STI:excludes:False:active",
    "opt_5vm_001->TVS:excludes:False:active",
    "opt_5vm_001->Z51:requires:False:active",
    "opt_5w8_001->5V7:excludes:False:active",
    "opt_5w8_001->5ZU:requires:False:active",
    "opt_5w8_001->5ZZ:requires:False:active",
    "opt_5w8_001->opt_5vm_001:excludes:False:active",
    "opt_5w8_001->opt_5zw_001:requires:False:active",
    "opt_5w8_001->STI:excludes:False:active",
    "opt_5w8_001->TVS:excludes:False:active",
    "opt_5w8_001->Z51:requires:False:active",
    "PCU->opt_5vm_001:excludes:False:active",
    "PCU->opt_5w8_001:excludes:False:active",
    "STI->opt_5vm_001:excludes:False:active",
    "STI->opt_5w8_001:excludes:False:active",
  ]);
  for (const rule of ruleOnlyRules(production)) {
    const key = ruleKey(production, rule);
    assert.equal(
      hasPreservedRuleRow(production, rule),
      !CSV_OWNED_RULE_ONLY_KEYS.has(key),
      `${rule.rule_id} should match expected preserved ownership`
    );
  }
});

test("5VM and 5W8 have no projected pricing groups or fake CSV surfaces", () => {
  const production = loadGeneratedData();
  const fragment = emitLegacyFragment();
  const ids = new Set(RULE_ONLY_IDS);

  assert.deepEqual(fragment.validation_errors, []);
  assert.equal(fragment.choices.some((choice) => RULE_ONLY_RPOS.includes(choice.rpo) || ids.has(choice.option_id)), false);
  assert.equal(production.priceRules.some((rule) => ids.has(rule.condition_option_id) || ids.has(rule.target_option_id)), false);
  assert.equal(production.ruleGroups.some((group) => ids.has(group.source_id) || (group.target_ids || []).some((targetId) => ids.has(targetId))), false);
  assert.equal(production.exclusiveGroups.some((group) => (group.option_ids || []).some((optionId) => ids.has(optionId))), false);
});

test("overlay rejects omitted guarded or preserved 5VM and 5W8 rule-only records", () => {
  const withoutGuard = loadManifest().filter(
    (row) => !(row.record_type === "guardedOption" && row.ownership === "production_guarded" && RULE_ONLY_IDS.includes(row.target_option_id))
  );
  const guardResult = runOverlay(["--ownership-manifest", writeTempManifest(withoutGuard)]);

  assert.notEqual(guardResult.status, 0);
  assert.match(guardResult.stderr, /unguarded rule-only preserved option_id/);
  assert.match(guardResult.stderr, /opt_5vm_001|opt_5w8_001/);

  const withoutInternalBoundary = loadManifest().filter(
    (row) => !(row.source_option_id === "opt_5vm_001" && row.target_option_id === "opt_5w8_001")
  );
  const preservedResult = runOverlay(["--ownership-manifest", writeTempManifest(withoutInternalBoundary)]);

  assert.notEqual(preservedResult.status, 0);
  assert.match(preservedResult.stderr, /unclassified guarded production records/);
  assert.match(preservedResult.stderr, /opt_5vm_001/);
  assert.match(preservedResult.stderr, /opt_5w8_001/);
});
