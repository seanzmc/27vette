#!/usr/bin/env node
import assert from "node:assert/strict";
import fs from "node:fs";

const SEAT_RPOS = new Set(["AQ9", "AH2", "AE4", "AUP"]);
const ADDED_PRICE_RULE_IDS = new Set([
  "sr_pr_1lt_ae4_seat_001",
  "sr_pr_3lt_ae4_seat_001",
  "sr_pr_3lt_ah2_seat_001",
]);
const EXPECTED_AFTER_STANDARD_SEATS = new Map([
  ["1lt_c07::AQ9", ["opt_aq9_001", "sec_seat_002", "Seats"]],
  ["1lt_c67::AQ9", ["opt_aq9_001", "sec_seat_002", "Seats"]],
  ["2lt_c07::AQ9", ["opt_aq9_001", "sec_seat_002", "Seats"]],
  ["2lt_c67::AQ9", ["opt_aq9_001", "sec_seat_002", "Seats"]],
  ["3lt_c07::AH2", ["opt_ah2_001", "sec_seat_002", "Seats"]],
  ["3lt_c67::AH2", ["opt_ah2_001", "sec_seat_002", "Seats"]],
]);
const RETIRED_SEAT_OPTION_IDS = new Set([
  "opt_aq9_002",
  "opt_aq9_003",
  "opt_aq9_004",
  "opt_ah2_002",
  "opt_ah2_003",
  "opt_ae4_001",
  "opt_ae4_003",
]);
const CANONICAL_SEAT_OPTION_IDS = new Set(["opt_aq9_001", "opt_ah2_001", "opt_ae4_002", "opt_aup_001"]);

function usage() {
  console.error("usage: node scripts/seat-canonicalization-diff.mjs before.json after.json [--model stingray]");
  process.exit(2);
}

const args = process.argv.slice(2);
if (args.length < 2) usage();
const [beforePath, afterPath] = args;
const modelIndex = args.indexOf("--model");
const modelKey = modelIndex >= 0 ? args[modelIndex + 1] : null;

function readJson(path) {
  return JSON.parse(fs.readFileSync(path, "utf8"));
}

function modelData(payload) {
  if (!modelKey) return payload;
  const registryKey = modelKey === "stingray" ? "stingray" : modelKey;
  return payload.models?.[registryKey]?.data ?? payload;
}

function stable(value) {
  if (Array.isArray(value)) return value.map(stable);
  if (value && typeof value === "object") {
    return Object.fromEntries(Object.keys(value).sort().map((key) => [key, stable(value[key])]));
  }
  return value;
}

function bestStatus(statuses) {
  if (statuses.includes("standard")) return "standard";
  if (statuses.includes("available")) return "available";
  if (statuses.includes("unavailable")) return "unavailable";
  return "";
}

function seatStatusSummary(data) {
  const byKey = new Map();
  for (const choice of data.choices || []) {
    if (!SEAT_RPOS.has(choice.rpo)) continue;
    const key = `${choice.variant_id}::${choice.rpo}`;
    const statuses = byKey.get(key) || [];
    statuses.push(choice.status);
    byKey.set(key, statuses);
  }
  return Object.fromEntries([...byKey].sort().map(([key, statuses]) => [key, bestStatus(statuses)]));
}

function standardSeatSummary(data) {
  return Object.fromEntries(
    (data.standardEquipment || [])
      .filter((row) => SEAT_RPOS.has(row.rpo))
      .map((row) => [
        `${row.variant_id}::${row.rpo}`,
        [row.option_id, row.section_id, row.section_name],
      ])
      .sort(([a], [b]) => a.localeCompare(b))
  );
}

function afterStandardSeatSummaryIsApproved(summary) {
  assert.deepEqual(Object.keys(summary).sort(), [...EXPECTED_AFTER_STANDARD_SEATS.keys()].sort());
  for (const [key, expected] of EXPECTED_AFTER_STANDARD_SEATS) {
    assert.deepEqual(summary[key], expected, `${key} standard seat grouping drift not approved`);
  }
}

function canonicalSeatChoicesAreApproved(data) {
  const seen = new Set();
  for (const choice of data.choices || []) {
    if (!SEAT_RPOS.has(choice.rpo)) continue;
    assert.equal(RETIRED_SEAT_OPTION_IDS.has(choice.option_id), false, `${choice.choice_id} uses retired seat option_id`);
    seen.add(choice.option_id);
  }
  assert.deepEqual([...seen].sort(), [...CANONICAL_SEAT_OPTION_IDS].sort());
}

function normalizedForNonSeatCompare(data) {
  const clone = JSON.parse(JSON.stringify(data));
  if (clone.dataset) clone.dataset.generated_at = "<timestamp>";
  clone.choices = (clone.choices || []).filter((row) => !SEAT_RPOS.has(row.rpo));
  clone.standardEquipment = (clone.standardEquipment || []).filter((row) => !SEAT_RPOS.has(row.rpo));
  clone.priceRules = (clone.priceRules || []).filter((row) => !ADDED_PRICE_RULE_IDS.has(row.price_rule_id));
  for (const row of clone.validation || []) {
    if (typeof row.message === "string") {
      row.message = row.message
        .replace(/\d+ active price rules exported/g, "<count> active price rules exported")
        .replace(/\d+ active compatibility rules exported/g, "<count> active compatibility rules exported")
        .replace(/\d+ draft choice rows exported/g, "<count> draft choice rows exported")
        .replace(/\d+ choice rows exported \([^)]*\)/g, "<count> choice rows exported (<status-counts>)");
    }
  }
  return stable(clone);
}

function main() {
  const before = modelData(readJson(beforePath));
  const after = modelData(readJson(afterPath));

  assert.deepEqual(seatStatusSummary(after), seatStatusSummary(before), "seat availability/default status drift");
  afterStandardSeatSummaryIsApproved(standardSeatSummary(after));
  canonicalSeatChoicesAreApproved(after);

  try {
    assert.deepEqual(normalizedForNonSeatCompare(after), normalizedForNonSeatCompare(before));
  } catch (error) {
    throw new Error(`non-seat drift: ${error.message}`);
  }

  console.log("seat canonicalization diff ok");
}

main();
