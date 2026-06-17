import assert from "node:assert/strict";
import { execFileSync, spawnSync } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import test from "node:test";

const scriptPath = "scripts/seat-canonicalization-diff.mjs";

function writeJson(dir, name, value) {
  const file = path.join(dir, name);
  fs.writeFileSync(file, JSON.stringify(value, null, 2));
  return file;
}

function trimLevelStatus(trimLevel, byTrim) {
  return byTrim[trimLevel] || "unavailable";
}

function baseData() {
  const variants = ["1lt_c07", "2lt_c07", "3lt_c07", "1lt_c67", "2lt_c67", "3lt_c67"];
  const choices = [];
  for (const variant_id of variants) {
    const trim_level = variant_id.slice(0, 3).toUpperCase();
    choices.push({
      choice_id: `${variant_id}__opt_aq9_003`,
      option_id: "opt_aq9_003",
      rpo: "AQ9",
      label: "GT1 Bucket Seats",
      section_id: "sec_seat_002",
      section_name: "Seats",
      step_key: "seat",
      variant_id,
      trim_level,
      status: trim_level === "1LT" ? "standard" : "unavailable",
      selectable: "True",
      active: "True",
      base_price: 0,
    });
    choices.push({
      choice_id: `${variant_id}__opt_aq9_001`,
      option_id: "opt_aq9_001",
      rpo: "AQ9",
      label: "GT1 Bucket Seats",
      section_id: "sec_2lte_001",
      section_name: "2LT Equipment",
      step_key: "standard_equipment",
      variant_id,
      trim_level,
      status: trim_level === "2LT" ? "standard" : "unavailable",
      selectable: "False",
      active: "True",
      base_price: 0,
    });
    choices.push({
      choice_id: `${variant_id}__opt_ah2_001`,
      option_id: "opt_ah2_001",
      rpo: "AH2",
      label: "GT2 Bucket Seats",
      section_id: "sec_3lte_001",
      section_name: "3LT Equipment",
      step_key: "standard_equipment",
      variant_id,
      trim_level,
      status: trimLevelStatus(trim_level, { "1LT": "unavailable", "2LT": "available", "3LT": "standard" }),
      selectable: "False",
      active: "True",
      base_price: 1695,
    });
    choices.push({
      choice_id: `${variant_id}__${trim_level === "1LT" ? "opt_ae4_001" : trim_level === "2LT" ? "opt_ae4_002" : "opt_ae4_003"}`,
      option_id: trim_level === "1LT" ? "opt_ae4_001" : trim_level === "2LT" ? "opt_ae4_002" : "opt_ae4_003",
      rpo: "AE4",
      label: "Competition Sport Bucket Seats",
      section_id: "sec_seat_002",
      section_name: "Seats",
      step_key: "seat",
      variant_id,
      trim_level,
      status: "available",
      selectable: "True",
      active: "True",
      base_price: trim_level === "1LT" ? 1095 : trim_level === "2LT" ? 2095 : 595,
    });
    choices.push({
      choice_id: `${variant_id}__opt_aup_001`,
      option_id: "opt_aup_001",
      rpo: "AUP",
      label: "Competition Sport Driver and GT2 Passenger Bucket Seats",
      section_id: "sec_seat_002",
      section_name: "Seats",
      step_key: "seat",
      variant_id,
      trim_level,
      status: trim_level === "3LT" ? "available" : "unavailable",
      selectable: "True",
      active: "True",
      base_price: 350,
    });
  }
  const standardEquipment = choices
    .filter((choice) => choice.status === "standard")
    .map((choice) => ({
      equipment_id: `std_${choice.choice_id}`,
      variant_id: choice.variant_id,
      trim_level: choice.trim_level,
      option_id: choice.option_id,
      rpo: choice.rpo,
      label: choice.label,
      section_id: choice.section_id,
      section_name: choice.section_name,
      base_price: choice.base_price,
    }));
  return {
    dataset: { generated_at: "before" },
    choices,
    standardEquipment,
    priceRules: [],
    rules: [],
    interiors: [{ interior_id: "1LT_AQ9_HTA", price: 0 }],
    validation: [],
  };
}

function canonicalizedData() {
  const data = baseData();
  const canonicalChoices = [];
  const variants = ["1lt_c07", "2lt_c07", "3lt_c07", "1lt_c67", "2lt_c67", "3lt_c67"];
  for (const variant_id of variants) {
    const trim_level = variant_id.slice(0, 3).toUpperCase();
    for (const row of [
      ["opt_aq9_001", "AQ9", 0, trim_level === "3LT" ? "unavailable" : "standard"],
      ["opt_ah2_001", "AH2", 1695, trim_level === "1LT" ? "unavailable" : trim_level === "3LT" ? "standard" : "available"],
      ["opt_ae4_002", "AE4", 2095, "available"],
      ["opt_aup_001", "AUP", 350, trim_level === "3LT" ? "available" : "unavailable"],
    ]) {
      const [option_id, rpo, base_price, status] = row;
      canonicalChoices.push({
        choice_id: `${variant_id}__${option_id}`,
        option_id,
        rpo,
        label: rpo === "AQ9" ? "GT1 Bucket Seats" : rpo === "AH2" ? "GT2 Bucket Seats" : rpo === "AE4" ? "Competition Sport Bucket Seats" : "Competition Sport Driver and GT2 Passenger Bucket Seats",
        section_id: "sec_seat_002",
        section_name: "Seats",
        step_key: "seat",
        variant_id,
        trim_level,
        status,
        selectable: "True",
        active: "True",
        base_price,
      });
    }
  }
  data.choices = canonicalChoices;
  data.standardEquipment = canonicalChoices
    .filter((choice) => choice.status === "standard")
    .map((choice) => ({
      equipment_id: `std_${choice.choice_id}`,
      variant_id: choice.variant_id,
      trim_level: choice.trim_level,
      option_id: choice.option_id,
      rpo: choice.rpo,
      label: choice.label,
      section_id: choice.section_id,
      section_name: choice.section_name,
      base_price: choice.base_price,
    }));
  data.priceRules = [
    { price_rule_id: "sr_pr_1lt_ae4_seat_001", condition_option_id: "opt_ae4_002", target_option_id: "opt_ae4_002", price_rule_type: "override", price_value: 1095, trim_level_scope: "1LT" },
    { price_rule_id: "sr_pr_3lt_ae4_seat_001", condition_option_id: "opt_ae4_002", target_option_id: "opt_ae4_002", price_rule_type: "override", price_value: 595, trim_level_scope: "3LT" },
    { price_rule_id: "sr_pr_3lt_ah2_seat_001", condition_option_id: "opt_ah2_001", target_option_id: "opt_ah2_001", price_rule_type: "override", price_value: 0, trim_level_scope: "3LT" },
  ];
  data.dataset.generated_at = "after";
  return data;
}

test("seat canonicalization diff accepts approved Stingray seat-only drift", () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "seat-diff-"));
  const before = writeJson(dir, "before.json", baseData());
  const after = writeJson(dir, "after.json", canonicalizedData());
  const output = execFileSync("node", [scriptPath, before, after], { encoding: "utf8" });
  assert.match(output, /seat canonicalization diff ok/);
});

test("seat canonicalization diff rejects non-seat drift", () => {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "seat-diff-"));
  const beforeData = baseData();
  const afterData = canonicalizedData();
  afterData.interiors[0].price = 99;
  const before = writeJson(dir, "before.json", beforeData);
  const after = writeJson(dir, "after.json", afterData);
  const result = spawnSync("node", [scriptPath, before, after], { encoding: "utf8" });
  assert.notEqual(result.status, 0);
  assert.match(result.stderr + result.stdout, /non-seat drift/i);
});
