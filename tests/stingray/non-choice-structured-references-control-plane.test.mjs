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
const NON_CHOICE_OPTION_IDS = ["opt_cf8_001", "opt_ryq_001"];
const CF8_STRIPE_TARGET_RPOS = ["DPB", "DPC", "DPG", "DPL", "DPT", "DSY", "DSZ", "DT0", "DTH", "DUB", "DUE", "DUK", "DUW"];

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
  const tempDir = fs.mkdtempSync(path.join(os.tmpdir(), "stingray-non-choice-references-"));
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
  assert.equal(ids.size, 1, `${rpo} should map to exactly one Stingray production option_id`);
  return [...ids][0];
}

function rpoByOptionId(data, optionId) {
  return data.choices.find((choice) => choice.option_id === optionId)?.rpo || optionId;
}

function ruleKey(data, rule) {
  return `${rpoByOptionId(data, rule.source_id)}->${rpoByOptionId(data, rule.target_id)}:${rule.rule_type}:${rule.auto_add}:${rule.runtime_action}`;
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

function nonChoiceStructuredRules(data) {
  const ids = new Set(NON_CHOICE_OPTION_IDS);
  return data.rules.filter((rule) => ids.has(rule.source_id) || ids.has(rule.target_id)).sort((a, b) => ruleKey(data, a).localeCompare(ruleKey(data, b)));
}

function interiorSourceIds(data) {
  const interiorIds = new Set(data.interiors.map((interior) => interior.interior_id));
  const structuredIds = new Set();
  for (const rule of data.rules) {
    structuredIds.add(rule.source_id);
    structuredIds.add(rule.target_id);
  }
  for (const rule of data.priceRules) {
    structuredIds.add(rule.condition_option_id);
    structuredIds.add(rule.target_option_id);
  }
  return [...structuredIds].filter((id) => interiorIds.has(id)).sort();
}

test("CF8 and RYQ are guarded non-choice Stingray structured option references", () => {
  const production = loadGeneratedData();
  const fragment = emitLegacyFragment();

  for (const optionId of NON_CHOICE_OPTION_IDS) {
    assert.equal(production.choices.some((choice) => choice.option_id === optionId), false);
    assert.equal(fragment.choices.some((choice) => choice.option_id === optionId), false);
    assert.equal(activeManifestRows().some((row) => row.rpo === optionId && row.ownership === "projected_owned"), false);
    assert.equal(production.rules.some((rule) => rule.source_id === optionId || rule.target_id === optionId), true);
    assert.equal(hasGuardedOption(optionId), true);
  }
});

test("CF8 and RYQ structured rules are exact and explicitly preserved", () => {
  const production = loadGeneratedData();

  const actualRuleKeys = JSON.parse(JSON.stringify(nonChoiceStructuredRules(production).map((rule) => ruleKey(production, rule))));

  assert.deepEqual(actualRuleKeys, [
    ...CF8_STRIPE_TARGET_RPOS.map((rpo) => `opt_cf8_001->${rpo}:excludes:False:active`),
    "opt_ryq_001->EFY:excludes:False:active",
  ]);
  for (const rule of nonChoiceStructuredRules(production)) {
    assert.equal(hasPreservedRuleRow(production, rule), true, `${rule.rule_id} should be preserved by explicit RPO or option_id`);
  }
});

test("CF8 and RYQ have no projected pricing groups or fake CSV surfaces", () => {
  const production = loadGeneratedData();
  const fragment = emitLegacyFragment();
  const ids = new Set(NON_CHOICE_OPTION_IDS);

  assert.deepEqual(fragment.validation_errors, []);
  assert.equal(fragment.choices.some((choice) => ids.has(choice.option_id) || ["CF8", "RYQ"].includes(choice.rpo)), false);
  assert.equal(production.priceRules.some((rule) => ids.has(rule.condition_option_id) || ids.has(rule.target_option_id)), false);
  assert.equal(production.ruleGroups.some((group) => ids.has(group.source_id) || (group.target_ids || []).some((targetId) => ids.has(targetId))), false);
  assert.equal(production.exclusiveGroups.some((group) => (group.option_ids || []).some((optionId) => ids.has(optionId))), false);
});

test("interior source ids are not treated as rule-only option ids", () => {
  const production = loadGeneratedData();
  const interiorIds = interiorSourceIds(production);

  assert.equal(interiorIds.length > 0, true);
  assert.equal(interiorIds.every((id) => id.startsWith("3LT_")), true);
  for (const interiorId of interiorIds) {
    assert.equal(production.interiors.some((interior) => interior.interior_id === interiorId), true);
    assert.equal(hasGuardedOption(interiorId), false);
  }
});

test("overlay rejects omitted guarded or preserved CF8 and RYQ non-choice records", () => {
  const withoutGuard = loadManifest().filter(
    (row) => !(row.record_type === "guardedOption" && row.ownership === "production_guarded" && NON_CHOICE_OPTION_IDS.includes(row.target_option_id))
  );
  const guardResult = runOverlay(["--ownership-manifest", writeTempManifest(withoutGuard)]);

  assert.notEqual(guardResult.status, 0);
  assert.match(guardResult.stderr, /unguarded rule-only preserved option_id/);
  assert.match(guardResult.stderr, /opt_cf8_001|opt_ryq_001/);

  const withoutCf8Boundary = loadManifest().filter(
    (row) => !(row.source_option_id === "opt_cf8_001" && row.target_rpo === "DPB")
  );
  const preservedResult = runOverlay(["--ownership-manifest", writeTempManifest(withoutCf8Boundary)]);

  assert.notEqual(preservedResult.status, 0);
  assert.match(preservedResult.stderr, /unclassified (guarded production|cross-boundary) records/);
  assert.match(preservedResult.stderr, /opt_cf8_001/);
});
