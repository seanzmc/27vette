import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import fs from "node:fs";
import test from "node:test";
import vm from "node:vm";

const PYTHON = ".venv/bin/python";
const SCRIPT = "scripts/stingray_csv_first_slice.py";
const PASS132_EXCLUDE_PAIRS = [
  ["dep_excl_pcu_5v7", "opt_pcu_001", "opt_5v7_001", "cs_selected_5v7"],
  ["dep_excl_r88_eyk", "opt_r88_001", "opt_eyk_001", "cs_selected_eyk"],
  ["dep_excl_r88_sfz", "opt_r88_001", "opt_sfz_001", "cs_selected_sfz"],
  ["dep_excl_rnx_5zz", "opt_rnx_001", "opt_5zz_001", "cs_selected_5zz"],
  ["dep_excl_sfz_eyk", "opt_sfz_001", "opt_eyk_001", "cs_selected_eyk"],
  ["dep_excl_wkq_5zz", "opt_wkq_001", "opt_5zz_001", "cs_selected_5zz"],
];
const PASS137_EXCLUDE_PAIRS = [
  ["dep_excl_wkq_5zu", "opt_wkq_001", "opt_5zu_001", "cs_selected_5zu"],
  ["dep_excl_rnx_5zu", "opt_rnx_001", "opt_5zu_001", "cs_selected_5zu"],
];
const PASS138_EXCLUDE_PAIRS = [
  ["dep_excl_sti_5v7", "opt_sti_001", "opt_5v7_001", "cs_selected_5v7"],
];
const PASS140_EXCLUDE_PAIRS = [
  ["dep_excl_sbt_cc3", "opt_sbt_001", "opt_cc3_001", "cs_selected_cc3"],
];
const PASS142_EXCLUDE_PAIRS = [
  ["dep_excl_pcx_eyk", "opt_pcx_001", "opt_eyk_001", "cs_selected_eyk"],
];
const PASS148_EXCLUDE_PAIRS = [
  ["dep_excl_pcx_pdv", "opt_pcx_001", "opt_pdv_001", "cs_selected_pdv"],
];
const PASS143_SAFE_PCX_EXCLUDE_RPOS = [
  "SB7",
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
];
const PASS143_EXCLUDE_PAIRS = PASS143_SAFE_PCX_EXCLUDE_RPOS.map((rpo) => [
  `dep_excl_pcx_${rpo.toLowerCase()}`,
  "opt_pcx_001",
  `opt_${rpo.toLowerCase()}_001`,
  `cs_selected_${rpo.toLowerCase()}`,
]);
const PASS144_SAFE_PDV_EXCLUDE_RPOS = [
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
];
const PASS144_EXCLUDE_PAIRS = PASS144_SAFE_PDV_EXCLUDE_RPOS.map((rpo) => [
  `dep_excl_pdv_${rpo.toLowerCase()}`,
  "opt_pdv_001",
  `opt_${rpo.toLowerCase()}_001`,
  `cs_selected_${rpo.toLowerCase()}`,
]);
const PASS146_INCLUDE_PAIRS = [
  ["aa_pdv_vwd", "opt_pdv_001", "opt_vwd_001"],
  ["aa_pdv_sb7", "opt_pdv_001", "opt_sb7_001"],
];
const PASS147_INCLUDE_PAIRS = [
  ["aa_pcx_sfz", "opt_pcx_001", "opt_sfz_001"],
  ["aa_pcx_sng", "opt_pcx_001", "opt_sng_001"],
  ["aa_pcx_sht", "opt_pcx_001", "opt_sht_001"],
];
const PASS151_INCLUDE_PAIRS = [["aa_pcx_5dg", "opt_pcx_001", "opt_5dg_001"]];
const PASS149_SAFE_TARGET_RPOS = ["5DG", "R8C", "S47", "SFE", "SPY", "SPZ"];
const PASS150_SAFE_PCX_EXCLUDE_RPOS = ["R8C", "S47", "SFE", "SPY", "SPZ"];
const PASS150_EXCLUDE_PAIRS = PASS150_SAFE_PCX_EXCLUDE_RPOS.map((rpo) => [
  `dep_excl_pcx_${rpo.toLowerCase()}`,
  "opt_pcx_001",
  `opt_${rpo.toLowerCase()}_001`,
  `cs_selected_${rpo.toLowerCase()}`,
]);
const PASS149_PRESERVED_BOUNDARIES = [
  ["rule", "5DG", "R8C"],
  ["rule", "5DG", "S47"],
  ["rule", "5DG", "SFE"],
  ["rule", "5DG", "SPY"],
  ["rule", "5DG", "SPZ"],
  ["rule", "5DO", "R8C"],
  ["rule", "5DO", "S47"],
  ["rule", "5DO", "SFE"],
  ["rule", "5DO", "SPY"],
  ["rule", "5DO", "SPZ"],
  ["rule", "BV4", "R8C"],
  ["rule", "R8C", "CFX"],
  ["rule", "S47", "SPY"],
  ["rule", "SPY", "S47"],
  ["rule", "SFE", "SPY"],
  ["rule", "SPZ", "SPY"],
];
const PASS141_PACKAGE_SOURCE_OPTION_IDS = ["opt_pcx_001", "opt_pdv_001"];
const PASS139_ALREADY_CSV_OWNED_EXCLUDES = [
  ["dep_excl_5v7_sti", "5V7", "STI"],
  ["dep_excl_5v7_tvs", "5V7", "TVS"],
  ["dep_excl_pcu_5v7", "PCU", "5V7"],
  ["dep_excl_r88_eyk", "R88", "EYK"],
  ["dep_excl_r88_sfz", "R88", "SFZ"],
  ["dep_excl_sfz_eyk", "SFZ", "EYK"],
  ["dep_excl_wkq_5zz", "WKQ", "5ZZ"],
  ["dep_excl_rnx_5zz", "RNX", "5ZZ"],
];
const PASS135_FULL_LENGTH_STRIPE_RPOS = [
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
];
const PASS135_EXCLUDE_PAIRS = PASS135_FULL_LENGTH_STRIPE_RPOS.flatMap((rpo) => [
  [`dep_excl_r88_${rpo.toLowerCase()}`, "opt_r88_001", `opt_${rpo.toLowerCase()}_001`, `cs_selected_${rpo.toLowerCase()}`],
  [`dep_excl_sfz_${rpo.toLowerCase()}`, "opt_sfz_001", `opt_${rpo.toLowerCase()}_001`, `cs_selected_${rpo.toLowerCase()}`],
]);
const PASS134_STRIPE_OPTION_IDS = [
  "opt_dpb_001",
  "opt_dpc_001",
  "opt_dpg_001",
  "opt_dpl_001",
  "opt_dpt_001",
  "opt_dsy_001",
  "opt_dsz_001",
  "opt_dt0_001",
  "opt_dth_001",
  "opt_dub_001",
  "opt_due_001",
  "opt_duk_001",
  "opt_duw_001",
  "opt_dzu_001",
  "opt_dzv_001",
  "opt_dzx_001",
];

function evaluate(variantId, selectedIds) {
  const output = execFileSync(PYTHON, [SCRIPT, "--scenario-json", JSON.stringify({ variant_id: variantId, selected_ids: selectedIds })], {
    cwd: process.cwd(),
    encoding: "utf8",
  });
  return JSON.parse(output);
}

function emitCsvLegacyFragment() {
  const output = execFileSync(PYTHON, [SCRIPT, "--emit-legacy-fragment"], {
    cwd: process.cwd(),
    encoding: "utf8",
  });
  return JSON.parse(output);
}

function loadGeneratedData() {
  const context = { window: {} };
  vm.runInNewContext(fs.readFileSync("form-app/data.js", "utf8"), context);
  return context.window.STINGRAY_FORM_DATA;
}

function lineById(result, selectableId) {
  return result.selected_lines.find((line) => line.selectable_id === selectableId);
}

function lineIds(result) {
  return result.selected_lines.map((line) => line.selectable_id);
}

function plain(value) {
  return JSON.parse(JSON.stringify(value));
}

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

function fixtureRows(name) {
  return parseCsv(fs.readFileSync(`data/stingray/validation/${name}`, "utf8"));
}

test("first-slice CSV evaluator validates package references", () => {
  const result = evaluate("1lt_c07", []);
  assert.deepEqual(result.validation_errors, []);
});

test("coupe B6P auto-adds D3V and SL9 at no charge", () => {
  const result = evaluate("1lt_c07", ["opt_b6p_001"]);

  assert.deepEqual(lineById(result, "opt_b6p_001")?.provenance, ["explicit"]);
  assert.deepEqual(lineById(result, "opt_d3v_001")?.provenance, ["auto"]);
  assert.equal(lineById(result, "opt_d3v_001")?.final_price_usd, 0);
  assert.deepEqual(lineById(result, "opt_sl9_001")?.provenance, ["auto"]);
  assert.equal(lineById(result, "opt_sl9_001")?.final_price_usd, 0);
  assert.deepEqual(result.auto_added_ids, ["opt_d3v_001", "opt_sl9_001"]);
});

test("coupe BCP auto-adds D3V and keeps the 695 base price", () => {
  const result = evaluate("1lt_c07", ["opt_bcp_001"]);

  assert.deepEqual(lineById(result, "opt_bcp_001")?.provenance, ["explicit"]);
  assert.equal(lineById(result, "opt_bcp_001")?.final_price_usd, 695);
  assert.deepEqual(lineById(result, "opt_d3v_001")?.provenance, ["auto"]);
  assert.equal(lineById(result, "opt_d3v_001")?.final_price_usd, 0);
});

test("coupe BCP with B6P gets B6P pricing and package auto-adds", () => {
  const result = evaluate("1lt_c07", ["opt_bcp_001", "opt_b6p_001"]);

  assert.equal(lineById(result, "opt_bcp_001")?.final_price_usd, 595);
  assert.deepEqual(lineById(result, "opt_bcp_001")?.matched_price_rule_ids, ["pr_engine_cover_b6p_static"]);
  assert.deepEqual(lineById(result, "opt_d3v_001")?.provenance, ["auto"]);
  assert.equal(lineById(result, "opt_d3v_001")?.final_price_usd, 0);
  assert.deepEqual(lineById(result, "opt_sl9_001")?.provenance, ["auto"]);
  assert.equal(lineById(result, "opt_sl9_001")?.final_price_usd, 0);
});

test("convertible BCP without ZZ3 reports a human-readable open requirement", () => {
  const result = evaluate("1lt_c67", ["opt_bcp_001"]);

  assert.deepEqual(lineById(result, "opt_bcp_001")?.provenance, ["explicit"]);
  assert.equal(result.open_requirements.length, 1);
  assert.equal(result.open_requirements[0].required_condition_set_id, "cs_selected_zz3");
  assert.match(result.open_requirements[0].message, /Requires ZZ3 Convertible Engine Appearance Package/);
});

test("convertible BCP with ZZ3 satisfies the ZZ3 requirement and uses current 595 pricing", () => {
  const result = evaluate("1lt_c67", ["opt_bcp_001", "opt_zz3_001"]);

  assert.deepEqual(result.open_requirements, []);
  assert.equal(lineById(result, "opt_bcp_001")?.final_price_usd, 595);
});

test("coupe BCP with BC4 reports the LS6 engine-cover exclusivity conflict", () => {
  const result = evaluate("1lt_c07", ["opt_bcp_001", "opt_bc4_001"]);

  assert.equal(result.conflicts.length, 1);
  assert.equal(result.conflicts[0].exclusive_group_id, "excl_ls6_engine_covers");
  assert.deepEqual(result.conflicts[0].member_selectable_ids, ["opt_bcp_001", "opt_bc4_001"]);
  assert.match(result.conflicts[0].message, /Choose only one LS6 engine cover/);
});

test("explicit SL9 with B6P is not duplicated and is priced as included", () => {
  const result = evaluate("1lt_c07", ["opt_sl9_001", "opt_b6p_001"]);

  assert.equal(lineIds(result).filter((id) => id === "opt_sl9_001").length, 1);
  assert.deepEqual(lineById(result, "opt_sl9_001")?.provenance, ["explicit"]);
  assert.deepEqual(lineById(result, "opt_sl9_001")?.matched_auto_add_ids, ["aa_b6p_sl9"]);
  assert.equal(lineById(result, "opt_sl9_001")?.final_price_usd, 0);
  assert.deepEqual(lineById(result, "opt_d3v_001")?.provenance, ["auto"]);
  assert.equal(lineById(result, "opt_d3v_001")?.final_price_usd, 0);
  assert.deepEqual(result.auto_added_ids, ["opt_d3v_001"]);
});

test("explicit D3V with B6P is not duplicated and is priced as included", () => {
  const result = evaluate("1lt_c07", ["opt_d3v_001", "opt_b6p_001"]);

  assert.equal(lineIds(result).filter((id) => id === "opt_d3v_001").length, 1);
  assert.deepEqual(lineById(result, "opt_d3v_001")?.provenance, ["explicit"]);
  assert.deepEqual(lineById(result, "opt_d3v_001")?.matched_auto_add_ids, ["aa_b6p_d3v"]);
  assert.equal(lineById(result, "opt_d3v_001")?.final_price_usd, 0);
  assert.deepEqual(lineById(result, "opt_sl9_001")?.provenance, ["auto"]);
  assert.equal(lineById(result, "opt_sl9_001")?.final_price_usd, 0);
  assert.deepEqual(result.auto_added_ids, ["opt_sl9_001"]);
});

test("dependency_rules excludes report directional dependency conflicts", () => {
  const stiResult = evaluate("1lt_c07", ["opt_5v7_001", "opt_sti_001"]);
  const stiConflict = stiResult.conflicts.find((conflict) => conflict.rule_id === "dep_excl_5v7_sti");

  assert.equal(stiResult.validation_errors.length, 0);
  assert.equal(stiConflict?.conflict_source, "dependency_rule");
  assert.equal(stiConflict?.target_condition_set_id, "cs_selected_sti");
  assert.equal(stiConflict?.target_selectable_id, "opt_sti_001");
  assert.equal(stiConflict?.message, "Blocked by 5V7 LPO, Black Ground Effects.");

  const tvsResult = evaluate("1lt_c07", ["opt_5v7_001", "opt_tvs_001"]);
  const tvsConflict = tvsResult.conflicts.find((conflict) => conflict.rule_id === "dep_excl_5v7_tvs");

  assert.equal(tvsResult.validation_errors.length, 0);
  assert.equal(tvsConflict?.conflict_source, "dependency_rule");
  assert.equal(tvsConflict?.target_condition_set_id, "cs_selected_tvs");
  assert.equal(tvsConflict?.target_selectable_id, "opt_tvs_001");
  assert.equal(tvsConflict?.message, "Blocked by 5V7 LPO, Black Ground Effects.");

  const inverseResult = evaluate("1lt_c07", ["opt_sti_001", "opt_5v7_001"]);
  const inverseConflict = inverseResult.conflicts.find((conflict) => conflict.rule_id === "dep_excl_sti_5v7");
  assert.equal(inverseConflict?.conflict_source, "dependency_rule");
  assert.equal(inverseConflict?.target_condition_set_id, "cs_selected_5v7");
  assert.equal(inverseConflict?.target_selectable_id, "opt_5v7_001");
  assert.equal(inverseConflict?.message, "Blocked by STI LPO, Composite rocker extensions.");
});

test("dependency_rules excludes emit production-shaped legacy rules", () => {
  const production = loadGeneratedData();
  const projected = emitCsvLegacyFragment();
  const fields = [
    "source_id",
    "rule_type",
    "target_id",
    "target_type",
    "source_type",
    "source_section",
    "target_section",
    "source_selection_mode",
    "target_selection_mode",
    "body_style_scope",
    "disabled_reason",
    "auto_add",
    "active",
    "runtime_action",
    "review_flag",
  ];

  for (const targetId of ["opt_sti_001", "opt_tvs_001"]) {
    const productionRule = production.rules.find(
      (rule) => rule.source_id === "opt_5v7_001" && rule.target_id === targetId && rule.rule_type === "excludes"
    );
    const projectedRule = projected.rules.find(
      (rule) => rule.source_id === "opt_5v7_001" && rule.target_id === targetId && rule.rule_type === "excludes"
    );

    assert.ok(productionRule, `production should include 5V7 -> ${targetId}`);
    assert.ok(projectedRule, `projected CSV fragment should include 5V7 -> ${targetId}`);
    assert.deepEqual(
      Object.fromEntries(fields.map((field) => [field, projectedRule[field]])),
      Object.fromEntries(fields.map((field) => [field, productionRule[field]]))
    );
  }
});

test("pass 132 migrated dependency_rules excludes emit production-shaped legacy rules", () => {
  const production = loadGeneratedData();
  const projected = emitCsvLegacyFragment();
  const fields = [
    "source_id",
    "rule_type",
    "target_id",
    "target_type",
    "source_type",
    "source_section",
    "target_section",
    "source_selection_mode",
    "target_selection_mode",
    "body_style_scope",
    "disabled_reason",
    "auto_add",
    "active",
    "runtime_action",
    "review_flag",
  ];

  for (const [, sourceId, targetId] of PASS132_EXCLUDE_PAIRS) {
    const productionRule = production.rules.find(
      (rule) => rule.source_id === sourceId && rule.target_id === targetId && rule.rule_type === "excludes"
    );
    const projectedRule = projected.rules.find(
      (rule) => rule.source_id === sourceId && rule.target_id === targetId && rule.rule_type === "excludes"
    );

    assert.ok(productionRule, `production should include ${sourceId} -> ${targetId}`);
    assert.ok(projectedRule, `projected CSV fragment should include ${sourceId} -> ${targetId}`);
    assert.deepEqual(
      Object.fromEntries(fields.map((field) => [field, projectedRule[field]])),
      Object.fromEntries(fields.map((field) => [field, productionRule[field]]))
    );
  }
});

test("pass 132 migrated dependency_rules excludes report sample dependency conflicts", () => {
  for (const [ruleId, sourceId, targetId, conditionSetId] of [
    PASS132_EXCLUDE_PAIRS[0],
    PASS132_EXCLUDE_PAIRS[1],
    PASS132_EXCLUDE_PAIRS[3],
  ]) {
    const result = evaluate("1lt_c07", [sourceId, targetId]);
    const conflict = result.conflicts.find((item) => item.rule_id === ruleId);

    assert.equal(result.validation_errors.length, 0);
    assert.equal(conflict?.conflict_source, "dependency_rule");
    assert.equal(conflict?.target_condition_set_id, conditionSetId);
    assert.equal(conflict?.target_selectable_id, targetId);
  }
});

test("pass 135 dependency_rules CSV migrates only R88 and SFZ full-length stripe excludes", () => {
  const rules = parseCsv(fs.readFileSync("data/stingray/logic/dependency_rules.csv", "utf8"));
  const conditionSets = parseCsv(fs.readFileSync("data/stingray/logic/condition_sets.csv", "utf8"));
  const conditionTerms = parseCsv(fs.readFileSync("data/stingray/logic/condition_terms.csv", "utf8"));

  assert.equal(rules.length, 86);
  assert.equal(rules.filter((rule) => rule.rule_type === "requires").length, 2);
  assert.equal(rules.filter((rule) => rule.rule_type === "excludes").length, 84);

  for (const [ruleId, sourceId, targetId, conditionSetId] of PASS135_EXCLUDE_PAIRS) {
    const rule = rules.find((candidate) => candidate.rule_id === ruleId);
    assert.ok(rule, `${ruleId} should exist`);
    assert.equal(rule.rule_type, "excludes");
    assert.equal(rule.subject_selector_type, "selectable");
    assert.equal(rule.subject_selector_id, sourceId);
    assert.equal(rule.subject_must_be_selected, "true");
    assert.equal(rule.target_condition_set_id, conditionSetId);
    assert.equal(rule.active, "true");

    assert.ok(conditionSets.find((conditionSet) => conditionSet.condition_set_id === conditionSetId), `${conditionSetId} should exist`);
    assert.ok(
      conditionTerms.find(
        (term) =>
          term.condition_set_id === conditionSetId &&
          term.term_type === "selected" &&
          term.left_ref === targetId &&
          term.operator === "is_true"
      ),
      `${conditionSetId} should select ${targetId}`
    );
  }

  for (const rpo of ["DZU", "DZV", "DZX"]) {
    assert.equal(rules.some((rule) => rule.rule_id === `dep_excl_r88_${rpo.toLowerCase()}`), false);
    assert.equal(rules.some((rule) => rule.rule_id === `dep_excl_sfz_${rpo.toLowerCase()}`), false);
  }
});

test("pass 137 dependency_rules CSV migrates only WKQ and RNX to 5ZU excludes", () => {
  const rules = parseCsv(fs.readFileSync("data/stingray/logic/dependency_rules.csv", "utf8"));
  const conditionSets = parseCsv(fs.readFileSync("data/stingray/logic/condition_sets.csv", "utf8"));
  const conditionTerms = parseCsv(fs.readFileSync("data/stingray/logic/condition_terms.csv", "utf8"));

  for (const [ruleId, sourceId, targetId, conditionSetId] of PASS137_EXCLUDE_PAIRS) {
    const rule = rules.find((candidate) => candidate.rule_id === ruleId);
    assert.ok(rule, `${ruleId} should exist`);
    assert.equal(rule.rule_type, "excludes");
    assert.equal(rule.subject_selector_type, "selectable");
    assert.equal(rule.subject_selector_id, sourceId);
    assert.equal(rule.subject_must_be_selected, "true");
    assert.equal(rule.target_condition_set_id, conditionSetId);
    assert.equal(rule.active, "true");

    assert.ok(conditionSets.find((conditionSet) => conditionSet.condition_set_id === conditionSetId), `${conditionSetId} should exist`);
    assert.ok(
      conditionTerms.find(
        (term) =>
          term.condition_set_id === conditionSetId &&
          term.term_type === "selected" &&
          term.left_ref === targetId &&
          term.operator === "is_true"
      ),
      `${conditionSetId} should select ${targetId}`
    );
  }

  assert.equal(rules.filter((rule) => rule.rule_id === "dep_excl_wkq_5zz").length, 1);
  assert.equal(rules.filter((rule) => rule.rule_id === "dep_excl_rnx_5zz").length, 1);
  assert.equal(rules.some((rule) => rule.rule_id === "dep_excl_wkq_5zw"), false);
  assert.equal(rules.some((rule) => rule.rule_id === "dep_excl_rnx_5zw"), false);
  assert.equal(rules.some((rule) => rule.rule_id === "dep_excl_rnx_z51"), false);
});

test("pass 138 dependency_rules CSV migrates only STI to 5V7 reverse exclude", () => {
  const rules = parseCsv(fs.readFileSync("data/stingray/logic/dependency_rules.csv", "utf8"));
  const conditionSets = parseCsv(fs.readFileSync("data/stingray/logic/condition_sets.csv", "utf8"));
  const conditionTerms = parseCsv(fs.readFileSync("data/stingray/logic/condition_terms.csv", "utf8"));

  for (const [ruleId, sourceId, targetId, conditionSetId] of PASS138_EXCLUDE_PAIRS) {
    const rule = rules.find((candidate) => candidate.rule_id === ruleId);
    assert.ok(rule, `${ruleId} should exist`);
    assert.equal(rule.rule_type, "excludes");
    assert.equal(rule.subject_selector_type, "selectable");
    assert.equal(rule.subject_selector_id, sourceId);
    assert.equal(rule.subject_must_be_selected, "true");
    assert.equal(rule.target_condition_set_id, conditionSetId);
    assert.equal(rule.message, "Blocked by STI LPO, Composite rocker extensions.");
    assert.equal(rule.active, "true");

    assert.ok(conditionSets.find((conditionSet) => conditionSet.condition_set_id === "cs_selected_sti"), "cs_selected_sti should still exist");
    assert.ok(conditionSets.find((conditionSet) => conditionSet.condition_set_id === conditionSetId), `${conditionSetId} should exist`);
    assert.ok(
      conditionTerms.find(
        (term) =>
          term.condition_set_id === conditionSetId &&
          term.term_type === "selected" &&
          term.left_ref === targetId &&
          term.operator === "is_true"
      ),
      `${conditionSetId} should select ${targetId}`
    );
  }

  assert.equal(rules.filter((rule) => rule.rule_id === "dep_excl_5v7_sti").length, 1);
  assert.equal(rules.some((rule) => rule.rule_id === "dep_excl_sti_5vm"), false);
  assert.equal(rules.some((rule) => rule.rule_id === "dep_excl_sti_5w8"), false);
  assert.equal(rules.some((rule) => rule.rule_id === "dep_excl_5v7_z51"), false);
});

test("pass 138 migrated STI to 5V7 exclude emits production-shaped legacy rule", () => {
  const production = loadGeneratedData();
  const projected = emitCsvLegacyFragment();
  const fields = [
    "source_id",
    "rule_type",
    "target_id",
    "target_type",
    "source_type",
    "source_section",
    "target_section",
    "source_selection_mode",
    "target_selection_mode",
    "body_style_scope",
    "disabled_reason",
    "auto_add",
    "active",
    "runtime_action",
    "review_flag",
  ];

  for (const [, sourceId, targetId] of PASS138_EXCLUDE_PAIRS) {
    const productionRule = production.rules.find(
      (rule) => rule.source_id === sourceId && rule.target_id === targetId && rule.rule_type === "excludes"
    );
    const projectedRule = projected.rules.find(
      (rule) => rule.source_id === sourceId && rule.target_id === targetId && rule.rule_type === "excludes"
    );

    assert.ok(productionRule, `production should include ${sourceId} -> ${targetId}`);
    assert.ok(projectedRule, `projected CSV fragment should include ${sourceId} -> ${targetId}`);
    assert.deepEqual(
      Object.fromEntries(fields.map((field) => [field, projectedRule[field]])),
      Object.fromEntries(fields.map((field) => [field, productionRule[field]]))
    );
  }
});

test("pass 139 already CSV-owned excludes are not preserved as production-owned boundaries", () => {
  const rules = parseCsv(fs.readFileSync("data/stingray/logic/dependency_rules.csv", "utf8"));
  const manifestRows = parseCsv(fs.readFileSync("data/stingray/validation/projected_slice_ownership.csv", "utf8"));

  assert.equal(rules.length, 86);
  assert.equal(rules.filter((rule) => rule.rule_type === "requires").length, 2);
  assert.equal(rules.filter((rule) => rule.rule_type === "excludes").length, 84);

  for (const [ruleId, sourceRpo, targetRpo] of PASS139_ALREADY_CSV_OWNED_EXCLUDES) {
    assert.ok(
      rules.some((rule) => rule.rule_id === ruleId && rule.rule_type === "excludes" && rule.active === "true"),
      `${ruleId} should be active in dependency_rules.csv`
    );
    assert.equal(
      manifestRows.some(
        (row) =>
          row.active === "true" &&
          row.record_type === "rule" &&
          row.source_rpo === sourceRpo &&
          row.target_rpo === targetRpo &&
          row.ownership === "preserved_cross_boundary"
      ),
      false,
      `${sourceRpo} -> ${targetRpo} should not remain preserved once dependency_rules.csv owns it`
    );
  }
});

test("pass 140 dependency_rules CSV migrates only SBT to CC3 roof panel exclude", () => {
  const rules = parseCsv(fs.readFileSync("data/stingray/logic/dependency_rules.csv", "utf8"));
  const conditionSets = parseCsv(fs.readFileSync("data/stingray/logic/condition_sets.csv", "utf8"));
  const conditionTerms = parseCsv(fs.readFileSync("data/stingray/logic/condition_terms.csv", "utf8"));
  const manifestRows = parseCsv(fs.readFileSync("data/stingray/validation/projected_slice_ownership.csv", "utf8"));

  assert.equal(rules.length, 86);
  assert.equal(rules.filter((rule) => rule.rule_type === "requires").length, 2);
  assert.equal(rules.filter((rule) => rule.rule_type === "excludes").length, 84);

  for (const [ruleId, sourceId, targetId, conditionSetId] of PASS140_EXCLUDE_PAIRS) {
    const rule = rules.find((candidate) => candidate.rule_id === ruleId);
    assert.ok(rule, `${ruleId} should exist`);
    assert.equal(rule.rule_type, "excludes");
    assert.equal(rule.subject_selector_type, "selectable");
    assert.equal(rule.subject_selector_id, sourceId);
    assert.equal(rule.subject_must_be_selected, "true");
    assert.equal(rule.target_condition_set_id, conditionSetId);
    assert.equal(rule.message, "Blocked by SBT LPO, Dual roof.");
    assert.equal(rule.active, "true");

    assert.ok(conditionSets.find((conditionSet) => conditionSet.condition_set_id === conditionSetId), `${conditionSetId} should exist`);
    assert.ok(
      conditionTerms.find(
        (term) =>
          term.condition_set_id === conditionSetId &&
          term.term_type === "selected" &&
          term.left_ref === targetId &&
          term.operator === "is_true"
      ),
      `${conditionSetId} should select ${targetId}`
    );
  }

  assert.equal(rules.some((rule) => rule.rule_id === "dep_excl_cc3_sbt"), false);
  assert.equal(
    manifestRows.some(
      (row) =>
        row.active === "true" &&
        row.record_type === "rule" &&
        row.source_rpo === "SBT" &&
        row.target_rpo === "CC3" &&
        row.ownership === "preserved_cross_boundary"
    ),
    false
  );
});

test("pass 140 migrated SBT to CC3 exclude emits production-shaped legacy rule", () => {
  const production = loadGeneratedData();
  const projected = emitCsvLegacyFragment();
  const fields = [
    "source_id",
    "rule_type",
    "target_id",
    "target_type",
    "source_type",
    "source_section",
    "target_section",
    "source_selection_mode",
    "target_selection_mode",
    "body_style_scope",
    "disabled_reason",
    "auto_add",
    "active",
    "runtime_action",
    "review_flag",
  ];

  for (const [, sourceId, targetId] of PASS140_EXCLUDE_PAIRS) {
    const productionRule = production.rules.find(
      (rule) => rule.source_id === sourceId && rule.target_id === targetId && rule.rule_type === "excludes"
    );
    const projectedRule = projected.rules.find(
      (rule) => rule.source_id === sourceId && rule.target_id === targetId && rule.rule_type === "excludes"
    );

    assert.ok(productionRule, `production should include ${sourceId} -> ${targetId}`);
    assert.ok(projectedRule, `projected CSV fragment should include ${sourceId} -> ${targetId}`);
    assert.deepEqual(
      Object.fromEntries(fields.map((field) => [field, projectedRule[field]])),
      Object.fromEntries(fields.map((field) => [field, productionRule[field]]))
    );
  }
});

test("pass 140 migrated SBT to CC3 exclude reports dependency conflict", () => {
  for (const [ruleId, sourceId, targetId, conditionSetId] of PASS140_EXCLUDE_PAIRS) {
    const result = evaluate("1lt_c07", [sourceId, targetId]);
    const conflict = result.conflicts.find((item) => item.rule_id === ruleId);

    assert.equal(result.validation_errors.length, 0);
    assert.equal(conflict?.conflict_source, "dependency_rule");
    assert.equal(conflict?.target_condition_set_id, conditionSetId);
    assert.equal(conflict?.target_selectable_id, targetId);
    assert.equal(conflict?.message, "Blocked by SBT LPO, Dual roof.");
  }
});

test("pass 141 projects only PCX and PDV package source catalog rows", () => {
  const selectables = parseCsv(fs.readFileSync("data/stingray/catalog/selectables.csv", "utf8"));
  const displayRows = parseCsv(fs.readFileSync("data/stingray/ui/selectable_display.csv", "utf8"));
  const basePrices = parseCsv(fs.readFileSync("data/stingray/pricing/base_prices.csv", "utf8"));
  const ownershipRows = parseCsv(fs.readFileSync("data/stingray/validation/projected_slice_ownership.csv", "utf8"));

  assert.equal(selectables.length, 95);
  assert.equal(displayRows.length, 95);
  assert.equal(basePrices.length, 90);
  assert.equal(
    ownershipRows.filter((row) => row.record_type === "selectable" && row.ownership === "projected_owned" && row.active === "true").length,
    92
  );

  const expected = [
    ["opt_pcx_001", "PCX", "LPO, Tech Bronze Accent Package", "4595", "30"],
    ["opt_pdv_001", "PDV", "LPO, Stingray R Appearance Package", "750", "20"],
  ];

  for (const [selectableId, rpo, label, price, displayOrder] of expected) {
    const selectable = selectables.find((row) => row.selectable_id === selectableId);
    assert.ok(selectable, `${selectableId} should exist in selectables.csv`);
    assert.equal(selectable.selectable_type, "option");
    assert.equal(selectable.rpo, rpo);
    assert.equal(selectable.label, label);
    assert.equal(selectable.active, "true");
    assert.equal(selectable.availability_condition_set_id, "");
    assert.equal(selectable.notes, "Pass 141 package source catalog unlock only.");

    const display = displayRows.find((row) => row.selectable_id === selectableId);
    assert.ok(display, `${selectableId} should exist in selectable_display.csv`);
    assert.equal(display.legacy_option_id, selectableId);
    assert.equal(display.section_id, "sec_lpoe_001");
    assert.equal(display.section_name, "LPO Exterior");
    assert.equal(display.category_id, "cat_mech_001");
    assert.equal(display.category_name, "Mechanical");
    assert.equal(display.step_key, "aero_exhaust_stripes_accessories");
    assert.equal(display.choice_mode, "multi");
    assert.equal(display.selection_mode, "multi_select_opt");
    assert.equal(display.display_order, displayOrder);
    assert.equal(display.selectable, "True");
    assert.equal(display.active, "True");
    assert.equal(display.status_condition_set_id, "");
    assert.equal(display.label, label);
    assert.match(display.source_detail_raw, /Not available with/);

    const basePrice = basePrices.find((row) => row.target_selector_id === selectableId);
    assert.ok(basePrice, `${selectableId} should have a base price`);
    assert.equal(basePrice.target_selector_type, "selectable");
    assert.equal(basePrice.scope_condition_set_id, "");
    assert.equal(basePrice.amount_usd, price);
    assert.equal(basePrice.active, "true");

    assert.ok(
      ownershipRows.find(
        (row) =>
          row.record_type === "selectable" &&
          row.rpo === rpo &&
          row.ownership === "projected_owned" &&
          row.reason === "Pass 141 package source catalog unlock only" &&
          row.active === "true"
      ),
      `${rpo} should be projected-owned`
    );
  }
});

test("pass 141 PCX and PDV legacy choices match production with only approved package behavior", () => {
  const production = loadGeneratedData();
  const projected = emitCsvLegacyFragment();
  const fields = [
    "option_id",
    "rpo",
    "label",
    "description",
    "section_id",
    "section_name",
    "category_id",
    "category_name",
    "step_key",
    "choice_mode",
    "selection_mode",
    "status",
    "selectable",
    "base_price",
    "display_order",
  ];

  for (const optionId of PASS141_PACKAGE_SOURCE_OPTION_IDS) {
    for (const variantId of ["1lt_c07", "1lt_c67", "2lt_c07", "2lt_c67", "3lt_c07", "3lt_c67"]) {
      const productionChoice = production.choices.find((choice) => choice.option_id === optionId && choice.variant_id === variantId);
      const projectedChoice = projected.choices.find((choice) => choice.option_id === optionId && choice.variant_id === variantId);

      assert.ok(productionChoice, `production should include ${variantId} ${optionId}`);
      assert.ok(projectedChoice, `projected CSV fragment should include ${variantId} ${optionId}`);
      assert.deepEqual(
        Object.fromEntries(fields.map((field) => [field, projectedChoice[field]])),
        Object.fromEntries(fields.map((field) => [field, productionChoice[field]]))
      );
    }
  }

  const allowedMigratedPackageRuleKeys = new Set(
    [
      ...PASS142_EXCLUDE_PAIRS,
      ...PASS143_EXCLUDE_PAIRS,
      ...PASS144_EXCLUDE_PAIRS,
      ...PASS146_INCLUDE_PAIRS,
      ...PASS147_INCLUDE_PAIRS,
      ...PASS151_INCLUDE_PAIRS,
      ...PASS148_EXCLUDE_PAIRS,
      ...PASS150_EXCLUDE_PAIRS,
    ].map(([, sourceId, targetId]) => `${sourceId}->${targetId}`)
  );
  assert.equal(
    projected.rules.some(
      (rule) =>
        (PASS141_PACKAGE_SOURCE_OPTION_IDS.includes(rule.source_id) || PASS141_PACKAGE_SOURCE_OPTION_IDS.includes(rule.target_id)) &&
        !allowedMigratedPackageRuleKeys.has(`${rule.source_id}->${rule.target_id}`)
    ),
    false
  );
  assert.equal(
    projected.priceRules.some(
      (rule) =>
        (PASS141_PACKAGE_SOURCE_OPTION_IDS.includes(rule.condition_option_id) ||
          PASS141_PACKAGE_SOURCE_OPTION_IDS.includes(rule.target_option_id)) &&
        !allowedMigratedPackageRuleKeys.has(`${rule.condition_option_id}->${rule.target_option_id}`)
    ),
    false
  );
  assert.equal((projected.auto_adds || projected.autoAdds || []).some((rule) => PASS141_PACKAGE_SOURCE_OPTION_IDS.includes(rule.source_id)), false);
});

test("pass 141 PCX and PDV evaluate as direct priced selections only", () => {
  for (const [selectableId, expectedPrice] of [
    ["opt_pcx_001", 4595],
    ["opt_pdv_001", 750],
  ]) {
    const result = evaluate("1lt_c07", [selectableId]);

    assert.equal(result.validation_errors.length, 0);
    assert.equal(lineById(result, selectableId)?.final_price_usd, expectedPrice);
    assert.deepEqual(lineById(result, selectableId)?.provenance, ["explicit"]);
    assert.equal(result.auto_added_ids.some((id) => PASS141_PACKAGE_SOURCE_OPTION_IDS.includes(id)), false);
    assert.equal(result.conflicts.some((conflict) => conflict.rule_id?.includes("pcx") || conflict.rule_id?.includes("pdv")), false);
  }
});

test("pass 142 dependency_rules CSV migrates only PCX to EYK badge exclude", () => {
  const rules = parseCsv(fs.readFileSync("data/stingray/logic/dependency_rules.csv", "utf8"));
  const conditionSets = parseCsv(fs.readFileSync("data/stingray/logic/condition_sets.csv", "utf8"));
  const conditionTerms = parseCsv(fs.readFileSync("data/stingray/logic/condition_terms.csv", "utf8"));
  const manifestRows = parseCsv(fs.readFileSync("data/stingray/validation/projected_slice_ownership.csv", "utf8"));

  assert.equal(rules.length, 86);
  assert.equal(rules.filter((rule) => rule.rule_type === "requires").length, 2);
  assert.equal(rules.filter((rule) => rule.rule_type === "excludes").length, 84);

  for (const [ruleId, sourceId, targetId, conditionSetId] of PASS142_EXCLUDE_PAIRS) {
    const rule = rules.find((candidate) => candidate.rule_id === ruleId);
    assert.ok(rule, `${ruleId} should exist`);
    assert.equal(rule.rule_type, "excludes");
    assert.equal(rule.subject_selector_type, "selectable");
    assert.equal(rule.subject_selector_id, sourceId);
    assert.equal(rule.subject_must_be_selected, "true");
    assert.equal(rule.target_condition_set_id, conditionSetId);
    assert.equal(rule.message, "Blocked by PCX LPO, Tech Bronze Accent Package.");
    assert.equal(rule.active, "true");

    assert.ok(conditionSets.find((conditionSet) => conditionSet.condition_set_id === conditionSetId), `${conditionSetId} should exist`);
    assert.ok(
      conditionTerms.find(
        (term) =>
          term.condition_set_id === conditionSetId &&
          term.term_type === "selected" &&
          term.left_ref === targetId &&
          term.operator === "is_true"
      ),
      `${conditionSetId} should select ${targetId}`
    );
  }

  assert.equal(conditionSets.some((conditionSet) => conditionSet.condition_set_id === "cs_selected_pcx"), false);
  assert.equal(conditionTerms.some((term) => term.left_ref === "opt_pcx_001"), false);
  assert.equal(rules.some((rule) => rule.rule_id === "dep_excl_pcx_5dg"), false);
  assert.equal(rules.some((rule) => rule.rule_id === "dep_excl_pdv_vwd"), false);
  assert.equal(rules.some((rule) => rule.rule_id === "dep_excl_pdv_sb7"), false);
  assert.equal(
    manifestRows.some(
      (row) =>
        row.active === "true" &&
        row.record_type === "rule" &&
        row.source_rpo === "PCX" &&
        row.target_rpo === "EYK" &&
        row.ownership === "preserved_cross_boundary"
    ),
    false
  );
});

test("pass 142 migrated PCX to EYK exclude emits production-shaped legacy rule", () => {
  const production = loadGeneratedData();
  const projected = emitCsvLegacyFragment();
  const fields = [
    "source_id",
    "rule_type",
    "target_id",
    "target_type",
    "source_type",
    "source_section",
    "target_section",
    "source_selection_mode",
    "target_selection_mode",
    "body_style_scope",
    "disabled_reason",
    "auto_add",
    "active",
    "runtime_action",
    "review_flag",
  ];

  for (const [, sourceId, targetId] of PASS142_EXCLUDE_PAIRS) {
    const productionRule = production.rules.find(
      (rule) => rule.source_id === sourceId && rule.target_id === targetId && rule.rule_type === "excludes"
    );
    const projectedRule = projected.rules.find(
      (rule) => rule.source_id === sourceId && rule.target_id === targetId && rule.rule_type === "excludes"
    );

    assert.ok(productionRule, `production should include ${sourceId} -> ${targetId}`);
    assert.ok(projectedRule, `projected CSV fragment should include ${sourceId} -> ${targetId}`);
    assert.deepEqual(
      Object.fromEntries(fields.map((field) => [field, projectedRule[field]])),
      Object.fromEntries(fields.map((field) => [field, productionRule[field]]))
    );
  }
});

test("pass 142 migrated PCX to EYK exclude reports dependency conflict", () => {
  for (const [ruleId, sourceId, targetId, conditionSetId] of PASS142_EXCLUDE_PAIRS) {
    const result = evaluate("1lt_c07", [sourceId, targetId]);
    const conflict = result.conflicts.find((item) => item.rule_id === ruleId);

    assert.equal(result.validation_errors.length, 0);
    assert.equal(conflict?.conflict_source, "dependency_rule");
    assert.equal(conflict?.target_condition_set_id, conditionSetId);
    assert.equal(conflict?.target_selectable_id, targetId);
    assert.equal(conflict?.message, "Blocked by PCX LPO, Tech Bronze Accent Package.");
  }
});

test("pass 143 dependency_rules CSV migrates only safe PCX plain excludes", () => {
  const autoAdds = parseCsv(fs.readFileSync("data/stingray/logic/auto_adds.csv", "utf8"));
  const rules = parseCsv(fs.readFileSync("data/stingray/logic/dependency_rules.csv", "utf8"));
  const conditionSets = parseCsv(fs.readFileSync("data/stingray/logic/condition_sets.csv", "utf8"));
  const conditionTerms = parseCsv(fs.readFileSync("data/stingray/logic/condition_terms.csv", "utf8"));
  const manifestRows = parseCsv(fs.readFileSync("data/stingray/validation/projected_slice_ownership.csv", "utf8"));

  assert.equal(rules.length, 86);
  assert.equal(rules.filter((rule) => rule.rule_type === "requires").length, 2);
  assert.equal(rules.filter((rule) => rule.rule_type === "excludes").length, 84);

  for (const [ruleId, sourceId, targetId, conditionSetId] of PASS143_EXCLUDE_PAIRS) {
    const rule = rules.find((candidate) => candidate.rule_id === ruleId);
    assert.ok(rule, `${ruleId} should exist`);
    assert.equal(rule.rule_type, "excludes");
    assert.equal(rule.subject_selector_type, "selectable");
    assert.equal(rule.subject_selector_id, sourceId);
    assert.equal(rule.subject_must_be_selected, "true");
    assert.equal(rule.target_condition_set_id, conditionSetId);
    assert.equal(rule.message, "Blocked by PCX LPO, Tech Bronze Accent Package.");
    assert.equal(rule.active, "true");

    assert.ok(conditionSets.find((conditionSet) => conditionSet.condition_set_id === conditionSetId), `${conditionSetId} should exist`);
    assert.ok(
      conditionTerms.find(
        (term) =>
          term.condition_set_id === conditionSetId &&
          term.term_type === "selected" &&
          term.left_ref === targetId &&
          term.operator === "is_true"
      ),
      `${conditionSetId} should select ${targetId}`
    );
  }

  assert.equal(conditionSets.some((conditionSet) => conditionSet.condition_set_id === "cs_selected_pcx"), false);
  assert.equal(conditionTerms.some((term) => term.left_ref === "opt_pcx_001"), false);
  for (const blockedRuleId of [
    "dep_excl_pcx_5dg",
  ]) {
    assert.equal(rules.some((rule) => rule.rule_id === blockedRuleId), false, `${blockedRuleId} should remain unmigrated`);
  }
  assert.equal(rules.some((rule) => rule.rule_id === "dep_excl_pdv_vwd"), false);
  assert.equal(rules.some((rule) => rule.rule_id === "dep_excl_pdv_sb7"), false);

  for (const rpo of PASS143_SAFE_PCX_EXCLUDE_RPOS) {
    assert.equal(
      manifestRows.some(
        (row) =>
          row.active === "true" &&
          row.record_type === "rule" &&
          row.source_rpo === "PCX" &&
          row.target_rpo === rpo &&
          row.ownership === "preserved_cross_boundary"
      ),
      false,
      `PCX -> ${rpo} should not remain preserved once dependency_rules.csv owns it`
    );
  }

  assert.ok(autoAdds.find((row) => row.auto_add_id === "aa_pcx_5dg" && row.target_price_policy_id === "included_zero"));
});

test("pass 143 migrated PCX plain excludes emit production-shaped legacy rules", () => {
  const production = loadGeneratedData();
  const projected = emitCsvLegacyFragment();
  const fields = [
    "source_id",
    "rule_type",
    "target_id",
    "target_type",
    "source_type",
    "source_section",
    "target_section",
    "source_selection_mode",
    "target_selection_mode",
    "body_style_scope",
    "disabled_reason",
    "auto_add",
    "active",
    "runtime_action",
    "review_flag",
  ];

  for (const [, sourceId, targetId] of PASS143_EXCLUDE_PAIRS) {
    const productionRule = production.rules.find(
      (rule) => rule.source_id === sourceId && rule.target_id === targetId && rule.rule_type === "excludes"
    );
    const projectedRule = projected.rules.find(
      (rule) => rule.source_id === sourceId && rule.target_id === targetId && rule.rule_type === "excludes"
    );

    assert.ok(productionRule, `production should include ${sourceId} -> ${targetId}`);
    assert.ok(projectedRule, `projected CSV fragment should include ${sourceId} -> ${targetId}`);
    assert.deepEqual(
      Object.fromEntries(fields.map((field) => [field, projectedRule[field]])),
      Object.fromEntries(fields.map((field) => [field, productionRule[field]]))
    );
  }
});

test("pass 143 migrated PCX plain excludes report dependency conflicts", () => {
  for (const [ruleId, sourceId, targetId, conditionSetId] of PASS143_EXCLUDE_PAIRS) {
    const result = evaluate("1lt_c07", [sourceId, targetId]);
    const conflict = result.conflicts.find((item) => item.rule_id === ruleId);

    assert.equal(result.validation_errors.length, 0);
    assert.equal(conflict?.conflict_source, "dependency_rule");
    assert.equal(conflict?.target_condition_set_id, conditionSetId);
    assert.equal(conflict?.target_selectable_id, targetId);
    assert.equal(conflict?.message, "Blocked by PCX LPO, Tech Bronze Accent Package.");
  }
});

test("pass 144 dependency_rules CSV migrates only safe PDV to Stripe plain excludes", () => {
  const rules = parseCsv(fs.readFileSync("data/stingray/logic/dependency_rules.csv", "utf8"));
  const conditionSets = parseCsv(fs.readFileSync("data/stingray/logic/condition_sets.csv", "utf8"));
  const conditionTerms = parseCsv(fs.readFileSync("data/stingray/logic/condition_terms.csv", "utf8"));
  const manifestRows = parseCsv(fs.readFileSync("data/stingray/validation/projected_slice_ownership.csv", "utf8"));

  assert.equal(rules.length, 86);
  assert.equal(rules.filter((rule) => rule.rule_type === "requires").length, 2);
  assert.equal(rules.filter((rule) => rule.rule_type === "excludes").length, 84);

  for (const [ruleId, sourceId, targetId, conditionSetId] of PASS144_EXCLUDE_PAIRS) {
    const rule = rules.find((candidate) => candidate.rule_id === ruleId);
    assert.ok(rule, `${ruleId} should exist`);
    assert.equal(rule.rule_type, "excludes");
    assert.equal(rule.subject_selector_type, "selectable");
    assert.equal(rule.subject_selector_id, sourceId);
    assert.equal(rule.subject_must_be_selected, "true");
    assert.equal(rule.target_condition_set_id, conditionSetId);
    assert.equal(rule.message, "Blocked by PDV LPO, Stingray R Appearance Package.");
    assert.equal(rule.active, "true");

    assert.ok(conditionSets.find((conditionSet) => conditionSet.condition_set_id === conditionSetId), `${conditionSetId} should exist`);
    assert.ok(
      conditionTerms.find(
        (term) =>
          term.condition_set_id === conditionSetId &&
          term.term_type === "selected" &&
          term.left_ref === targetId &&
          term.operator === "is_true"
      ),
      `${conditionSetId} should select ${targetId}`
    );
  }

  assert.equal(rules.some((rule) => rule.rule_id === "dep_excl_pdv_vwd"), false);
  assert.equal(rules.some((rule) => rule.rule_id === "dep_excl_pdv_sb7"), false);

  for (const rpo of PASS144_SAFE_PDV_EXCLUDE_RPOS) {
    assert.equal(
      manifestRows.some(
        (row) =>
          row.active === "true" &&
          row.record_type === "rule" &&
          row.source_rpo === "PDV" &&
          row.target_rpo === rpo &&
          row.ownership === "preserved_cross_boundary"
      ),
      false,
      `PDV -> ${rpo} should not remain preserved once dependency_rules.csv owns it`
    );
  }

});

test("pass 146 auto_adds CSV migrates only PDV package includes for VWD and SB7", () => {
  const autoAdds = parseCsv(fs.readFileSync("data/stingray/logic/auto_adds.csv", "utf8"));
  const rules = parseCsv(fs.readFileSync("data/stingray/logic/dependency_rules.csv", "utf8"));
  const manifestRows = parseCsv(fs.readFileSync("data/stingray/validation/projected_slice_ownership.csv", "utf8"));
  const production = loadGeneratedData();
  const projected = emitCsvLegacyFragment();

  assert.equal(autoAdds.filter((row) => row.active === "true").length, 19);
  assert.equal(rules.length, 86);
  assert.equal(rules.filter((rule) => rule.rule_type === "requires").length, 2);
  assert.equal(rules.filter((rule) => rule.rule_type === "excludes").length, 84);

  for (const [autoAddId, sourceId, targetId] of PASS146_INCLUDE_PAIRS) {
    const row = autoAdds.find((candidate) => candidate.auto_add_id === autoAddId);
    assert.ok(row, `${autoAddId} should exist`);
    assert.equal(row.source_selector_type, "selectable");
    assert.equal(row.source_selector_id, sourceId);
    assert.equal(row.target_selectable_id, targetId);
    assert.equal(row.target_price_policy_id, "included_zero");
    assert.equal(row.active, "true");

    const productionRule = production.rules.find((rule) => rule.source_id === sourceId && rule.target_id === targetId && rule.rule_type === "includes");
    const projectedRule = projected.rules.find((rule) => rule.source_id === sourceId && rule.target_id === targetId && rule.rule_type === "includes");
    const productionPriceRule = production.priceRules.find(
      (rule) => rule.condition_option_id === sourceId && rule.target_option_id === targetId && Number(rule.price_value) === 0
    );
    const projectedPriceRule = projected.priceRules.find(
      (rule) => rule.condition_option_id === sourceId && rule.target_option_id === targetId && Number(rule.price_value) === 0
    );

    assert.ok(productionRule, `${sourceId} -> ${targetId} include should exist in production`);
    assert.ok(productionPriceRule, `${sourceId} -> ${targetId} priceRule should exist in production`);
    assert.deepEqual(plain(projectedRule), plain(productionRule));
    assert.deepEqual(projectedPriceRule, {
      ...plain(productionPriceRule),
      price_rule_id: `pr_${sourceId}_${targetId}_included_zero`,
    });
  }

  for (const [recordType, sourceRpo, targetRpo] of [
    ["rule", "PDV", "VWD"],
    ["priceRule", "PDV", "VWD"],
    ["rule", "PDV", "SB7"],
    ["priceRule", "PDV", "SB7"],
  ]) {
    assert.equal(
      manifestRows.some(
        (row) =>
          row.active === "true" &&
          row.record_type === recordType &&
          row.source_rpo === sourceRpo &&
          row.target_rpo === targetRpo &&
          row.ownership === "preserved_cross_boundary"
      ),
      false,
      `${recordType} ${sourceRpo} -> ${targetRpo} should not remain preserved`
    );
  }

  assert.ok(autoAdds.find((row) => row.auto_add_id === "aa_pcx_5dg" && row.target_price_policy_id === "included_zero"));
});

test("pass 147 auto_adds CSV migrates only PCX package includes for SFZ SNG and SHT", () => {
  const autoAdds = parseCsv(fs.readFileSync("data/stingray/logic/auto_adds.csv", "utf8"));
  const rules = parseCsv(fs.readFileSync("data/stingray/logic/dependency_rules.csv", "utf8"));
  const manifestRows = parseCsv(fs.readFileSync("data/stingray/validation/projected_slice_ownership.csv", "utf8"));
  const production = loadGeneratedData();
  const projected = emitCsvLegacyFragment();

  assert.equal(autoAdds.filter((row) => row.active === "true").length, 19);
  assert.equal(rules.length, 86);
  assert.equal(rules.filter((rule) => rule.rule_type === "requires").length, 2);
  assert.equal(rules.filter((rule) => rule.rule_type === "excludes").length, 84);

  for (const [autoAddId, sourceId, targetId] of PASS147_INCLUDE_PAIRS) {
    const row = autoAdds.find((candidate) => candidate.auto_add_id === autoAddId);
    assert.ok(row, `${autoAddId} should exist`);
    assert.equal(row.source_selector_type, "selectable");
    assert.equal(row.source_selector_id, sourceId);
    assert.equal(row.target_selectable_id, targetId);
    assert.equal(row.target_price_policy_id, "included_zero");
    assert.equal(row.quantity, "1");
    assert.equal(row.if_target_already_selected, "convert_existing_to_included");
    assert.equal(row.removal_policy, "remove_when_no_triggers");
    assert.equal(row.conflict_policy, "lowest_price_wins");
    assert.equal(row.cascade, "true");
    assert.equal(row.active, "true");

    const productionRule = production.rules.find((rule) => rule.source_id === sourceId && rule.target_id === targetId && rule.rule_type === "includes");
    const projectedRule = projected.rules.find((rule) => rule.source_id === sourceId && rule.target_id === targetId && rule.rule_type === "includes");
    const productionPriceRule = production.priceRules.find(
      (rule) => rule.condition_option_id === sourceId && rule.target_option_id === targetId && Number(rule.price_value) === 0
    );
    const projectedPriceRule = projected.priceRules.find(
      (rule) => rule.condition_option_id === sourceId && rule.target_option_id === targetId && Number(rule.price_value) === 0
    );

    assert.ok(productionRule, `${sourceId} -> ${targetId} include should exist in production`);
    assert.ok(productionPriceRule, `${sourceId} -> ${targetId} priceRule should exist in production`);
    assert.deepEqual(plain(projectedRule), plain(productionRule));
    assert.deepEqual(projectedPriceRule, {
      ...plain(productionPriceRule),
      price_rule_id: `pr_${sourceId}_${targetId}_included_zero`,
    });
  }

  for (const [recordType, sourceRpo, targetRpo] of [
    ["rule", "PCX", "SFZ"],
    ["priceRule", "PCX", "SFZ"],
    ["rule", "PCX", "SNG"],
    ["priceRule", "PCX", "SNG"],
    ["rule", "PCX", "SHT"],
    ["priceRule", "PCX", "SHT"],
  ]) {
    assert.equal(
      manifestRows.some(
        (row) =>
          row.active === "true" &&
          row.record_type === recordType &&
          row.source_rpo === sourceRpo &&
          row.target_rpo === targetRpo &&
          row.ownership === "preserved_cross_boundary"
      ),
      false,
      `${recordType} ${sourceRpo} -> ${targetRpo} should not remain preserved`
    );
  }

  assert.ok(autoAdds.find((row) => row.auto_add_id === "aa_pcx_5dg" && row.target_price_policy_id === "included_zero"));
});

test("pass 148 dependency_rules CSV migrates only PCX to PDV package conflict", () => {
  const autoAdds = parseCsv(fs.readFileSync("data/stingray/logic/auto_adds.csv", "utf8"));
  const rules = parseCsv(fs.readFileSync("data/stingray/logic/dependency_rules.csv", "utf8"));
  const conditionSets = parseCsv(fs.readFileSync("data/stingray/logic/condition_sets.csv", "utf8"));
  const conditionTerms = parseCsv(fs.readFileSync("data/stingray/logic/condition_terms.csv", "utf8"));
  const manifestRows = parseCsv(fs.readFileSync("data/stingray/validation/projected_slice_ownership.csv", "utf8"));
  const production = loadGeneratedData();
  const projected = emitCsvLegacyFragment();
  const fields = [
    "source_id",
    "rule_type",
    "target_id",
    "target_type",
    "source_type",
    "source_section",
    "target_section",
    "source_selection_mode",
    "target_selection_mode",
    "body_style_scope",
    "disabled_reason",
    "auto_add",
    "active",
    "runtime_action",
    "review_flag",
  ];

  assert.equal(autoAdds.filter((row) => row.active === "true").length, 19);
  assert.equal(rules.length, 86);
  assert.equal(rules.filter((rule) => rule.rule_type === "requires").length, 2);
  assert.equal(rules.filter((rule) => rule.rule_type === "excludes").length, 84);

  for (const [ruleId, sourceId, targetId, conditionSetId] of PASS148_EXCLUDE_PAIRS) {
    const rule = rules.find((candidate) => candidate.rule_id === ruleId);
    assert.ok(rule, `${ruleId} should exist`);
    assert.equal(rule.rule_type, "excludes");
    assert.equal(rule.subject_selector_type, "selectable");
    assert.equal(rule.subject_selector_id, sourceId);
    assert.equal(rule.subject_must_be_selected, "true");
    assert.equal(rule.target_condition_set_id, conditionSetId);
    assert.equal(rule.violation_behavior, "disable_and_block");
    assert.equal(rule.message, "Blocked by PCX LPO, Tech Bronze Accent Package.");
    assert.equal(rule.active, "true");

    assert.ok(conditionSets.find((conditionSet) => conditionSet.condition_set_id === conditionSetId), `${conditionSetId} should exist`);
    assert.ok(
      conditionTerms.find(
        (term) =>
          term.condition_set_id === conditionSetId &&
          term.term_type === "selected" &&
          term.left_ref === targetId &&
          term.operator === "is_true"
      ),
      `${conditionSetId} should select ${targetId}`
    );

    const productionRule = production.rules.find(
      (candidate) => candidate.source_id === sourceId && candidate.target_id === targetId && candidate.rule_type === "excludes"
    );
    const projectedRule = projected.rules.find(
      (candidate) => candidate.source_id === sourceId && candidate.target_id === targetId && candidate.rule_type === "excludes"
    );

    assert.ok(productionRule, `${sourceId} -> ${targetId} exclude should exist in production`);
    assert.ok(projectedRule, `${sourceId} -> ${targetId} exclude should exist in projected CSV fragment`);
    assert.deepEqual(
      Object.fromEntries(fields.map((field) => [field, projectedRule[field]])),
      Object.fromEntries(fields.map((field) => [field, productionRule[field]]))
    );
  }

  assert.equal(conditionSets.some((conditionSet) => conditionSet.condition_set_id === "cs_selected_pcx"), false);
  assert.equal(conditionTerms.some((term) => term.left_ref === "opt_pcx_001"), false);
  assert.equal(production.priceRules.some((rule) => rule.condition_option_id === "opt_pcx_001" && rule.target_option_id === "opt_pdv_001"), false);
  assert.equal(projected.priceRules.some((rule) => rule.condition_option_id === "opt_pcx_001" && rule.target_option_id === "opt_pdv_001"), false);

  assert.equal(
    manifestRows.some(
      (row) =>
        row.active === "true" &&
        row.record_type === "rule" &&
        row.source_rpo === "PCX" &&
        row.target_rpo === "PDV" &&
        row.ownership === "preserved_cross_boundary"
    ),
    false,
    "PCX -> PDV should not remain preserved"
  );

  assert.ok(autoAdds.find((row) => row.auto_add_id === "aa_pcx_5dg" && row.target_price_policy_id === "included_zero"));
});

test("pass 149 projects only safe missing PCX target catalog rows", () => {
  const selectables = parseCsv(fs.readFileSync("data/stingray/catalog/selectables.csv", "utf8"));
  const displayRows = parseCsv(fs.readFileSync("data/stingray/ui/selectable_display.csv", "utf8"));
  const basePrices = parseCsv(fs.readFileSync("data/stingray/pricing/base_prices.csv", "utf8"));
  const ownershipRows = parseCsv(fs.readFileSync("data/stingray/validation/projected_slice_ownership.csv", "utf8"));
  const rules = parseCsv(fs.readFileSync("data/stingray/logic/dependency_rules.csv", "utf8"));
  const autoAdds = parseCsv(fs.readFileSync("data/stingray/logic/auto_adds.csv", "utf8"));
  const production = loadGeneratedData();
  const projected = emitCsvLegacyFragment();
  const fields = [
    "option_id",
    "rpo",
    "label",
    "description",
    "section_id",
    "section_name",
    "category_id",
    "category_name",
    "step_key",
    "choice_mode",
    "selection_mode",
    "status",
    "selectable",
    "base_price",
    "display_order",
  ];

  assert.equal(selectables.length, 95);
  assert.equal(displayRows.length, 95);
  assert.equal(basePrices.length, 90);
  assert.equal(rules.length, 86);
  assert.equal(rules.filter((rule) => rule.rule_type === "requires").length, 2);
  assert.equal(rules.filter((rule) => rule.rule_type === "excludes").length, 84);
  assert.equal(autoAdds.filter((row) => row.active === "true").length, 19);

  for (const rpo of PASS149_SAFE_TARGET_RPOS) {
    const optionId = `opt_${rpo.toLowerCase()}_001`;
    const productionChoice = production.choices.find((choice) => choice.option_id === optionId && choice.variant_id === "1lt_c07");
    assert.ok(productionChoice, `production should include ${optionId}`);

    const selectable = selectables.find((row) => row.selectable_id === optionId);
    assert.ok(selectable, `${optionId} should exist in selectables.csv`);
    assert.equal(selectable.selectable_type, "option");
    assert.equal(selectable.rpo, rpo);
    assert.equal(selectable.label, productionChoice.label);
    assert.equal(selectable.description, productionChoice.description);
    assert.equal(selectable.active, "true");
    assert.equal(selectable.availability_condition_set_id, "");
    assert.equal(selectable.notes, "Pass 149 missing PCX target catalog projection only.");

    const display = displayRows.find((row) => row.selectable_id === optionId);
    assert.ok(display, `${optionId} should exist in selectable_display.csv`);
    assert.equal(display.legacy_option_id, optionId);
    assert.equal(display.section_id, productionChoice.section_id);
    assert.equal(display.section_name, productionChoice.section_name);
    assert.equal(display.category_id, productionChoice.category_id);
    assert.equal(display.category_name, productionChoice.category_name);
    assert.equal(display.step_key, productionChoice.step_key);
    assert.equal(display.choice_mode, productionChoice.choice_mode);
    assert.equal(display.selection_mode, productionChoice.selection_mode);
    assert.equal(display.display_order, String(productionChoice.display_order));
    assert.equal(display.selectable, "True");
    assert.equal(display.active, "True");
    assert.equal(display.label, productionChoice.label);
    assert.equal(display.description, productionChoice.description);
    assert.equal(display.source_detail_raw, productionChoice.source_detail_raw || "");

    const basePrice = basePrices.find((row) => row.target_selector_id === optionId);
    assert.ok(basePrice, `${optionId} should have a base price`);
    assert.equal(basePrice.target_selector_type, "selectable");
    assert.equal(basePrice.scope_condition_set_id, "");
    assert.equal(basePrice.amount_usd, String(productionChoice.base_price));
    assert.equal(basePrice.active, "true");

    assert.ok(
      ownershipRows.find(
        (row) =>
          row.record_type === "selectable" &&
          row.rpo === rpo &&
          row.ownership === "projected_owned" &&
          row.reason === "Pass 149 missing PCX target catalog projection only" &&
          row.active === "true"
      ),
      `${rpo} should be projected-owned`
    );

    for (const variantId of ["1lt_c07", "1lt_c67", "2lt_c07", "2lt_c67", "3lt_c07", "3lt_c67"]) {
      const productionVariantChoice = production.choices.find((choice) => choice.option_id === optionId && choice.variant_id === variantId);
      const projectedChoice = projected.choices.find((choice) => choice.option_id === optionId && choice.variant_id === variantId);

      assert.ok(productionVariantChoice, `production should include ${variantId} ${optionId}`);
      assert.ok(projectedChoice, `projected CSV fragment should include ${variantId} ${optionId}`);
      assert.deepEqual(
        Object.fromEntries(fields.map((field) => [field, projectedChoice[field]])),
        Object.fromEntries(fields.map((field) => [field, productionVariantChoice[field]]))
      );
    }
  }

  for (const [recordType, sourceRpo, targetRpo] of PASS149_PRESERVED_BOUNDARIES) {
    assert.equal(
      ownershipRows.some(
        (row) =>
          row.active === "true" &&
          row.record_type === recordType &&
          row.source_rpo === sourceRpo &&
          row.target_rpo === targetRpo &&
          row.ownership === "preserved_cross_boundary"
      ),
      true,
      `${recordType} ${sourceRpo} -> ${targetRpo} should remain preserved`
    );
  }

  assert.equal(rules.some((rule) => rule.rule_id === "dep_excl_pcx_5dg"), false);
  assert.ok(autoAdds.find((row) => row.auto_add_id === "aa_pcx_5dg" && row.target_price_policy_id === "included_zero"));
});

test("pass 150 dependency_rules CSV migrates only newly unblocked PCX plain excludes", () => {
  const rules = parseCsv(fs.readFileSync("data/stingray/logic/dependency_rules.csv", "utf8"));
  const conditionSets = parseCsv(fs.readFileSync("data/stingray/logic/condition_sets.csv", "utf8"));
  const conditionTerms = parseCsv(fs.readFileSync("data/stingray/logic/condition_terms.csv", "utf8"));
  const manifestRows = parseCsv(fs.readFileSync("data/stingray/validation/projected_slice_ownership.csv", "utf8"));
  const selectables = parseCsv(fs.readFileSync("data/stingray/catalog/selectables.csv", "utf8"));
  const autoAdds = parseCsv(fs.readFileSync("data/stingray/logic/auto_adds.csv", "utf8"));
  const priceRules = parseCsv(fs.readFileSync("data/stingray/pricing/price_rules.csv", "utf8"));
  const production = loadGeneratedData();
  const projected = emitCsvLegacyFragment();
  const fields = [
    "source_id",
    "rule_type",
    "target_id",
    "target_type",
    "source_type",
    "source_section",
    "target_section",
    "source_selection_mode",
    "target_selection_mode",
    "body_style_scope",
    "disabled_reason",
    "auto_add",
    "active",
    "runtime_action",
    "review_flag",
  ];

  assert.equal(rules.length, 86);
  assert.equal(rules.filter((rule) => rule.rule_type === "requires").length, 2);
  assert.equal(rules.filter((rule) => rule.rule_type === "excludes").length, 84);
  assert.equal(conditionSets.length, 42);
  assert.equal(conditionTerms.length, 44);
  assert.equal(autoAdds.filter((row) => row.active === "true").length, 19);

  for (const [ruleId, sourceId, targetId, conditionSetId] of PASS150_EXCLUDE_PAIRS) {
    const targetRpo = targetId.replace(/^opt_/, "").replace(/_001$/, "").toUpperCase();
    const rule = rules.find((candidate) => candidate.rule_id === ruleId);
    assert.ok(rule, `${ruleId} should exist`);
    assert.equal(rule.rule_type, "excludes");
    assert.equal(rule.subject_selector_type, "selectable");
    assert.equal(rule.subject_selector_id, sourceId);
    assert.equal(rule.subject_must_be_selected, "true");
    assert.equal(rule.applies_when_condition_set_id, "");
    assert.equal(rule.target_condition_set_id, conditionSetId);
    assert.equal(rule.violation_behavior, "disable_and_block");
    assert.equal(rule.message, "Blocked by PCX LPO, Tech Bronze Accent Package.");
    assert.equal(rule.active, "true");

    assert.ok(selectables.find((selectable) => selectable.selectable_id === targetId && selectable.active === "true"), `${targetId} should exist`);
    assert.ok(
      manifestRows.find(
        (row) => row.active === "true" && row.record_type === "selectable" && row.rpo === targetRpo && row.ownership === "projected_owned"
      ),
      `${targetRpo} should be projected-owned before migration`
    );
    assert.ok(conditionSets.find((conditionSet) => conditionSet.condition_set_id === conditionSetId), `${conditionSetId} should exist`);
    assert.ok(
      conditionTerms.find(
        (term) =>
          term.condition_set_id === conditionSetId &&
          term.or_group === "g1" &&
          term.term_type === "selected" &&
          term.left_ref === targetId &&
          term.operator === "is_true" &&
          term.negate === "false"
      ),
      `${conditionSetId} should select ${targetId}`
    );

    const productionRule = production.rules.find(
      (candidate) => candidate.source_id === sourceId && candidate.target_id === targetId && candidate.rule_type === "excludes"
    );
    const projectedRule = projected.rules.find(
      (candidate) => candidate.source_id === sourceId && candidate.target_id === targetId && candidate.rule_type === "excludes"
    );

    assert.ok(productionRule, `${sourceId} -> ${targetId} exclude should exist in production`);
    assert.ok(projectedRule, `${sourceId} -> ${targetId} exclude should exist in projected CSV fragment`);
    assert.deepEqual(
      Object.fromEntries(fields.map((field) => [field, projectedRule[field]])),
      Object.fromEntries(fields.map((field) => [field, productionRule[field]]))
    );
    assert.equal(production.priceRules.some((priceRule) => priceRule.condition_option_id === sourceId && priceRule.target_option_id === targetId), false);

    assert.equal(
      manifestRows.some(
        (row) =>
          row.active === "true" &&
          row.record_type === "rule" &&
          row.source_rpo === "PCX" &&
          row.target_rpo === targetRpo &&
          row.ownership === "preserved_cross_boundary"
      ),
      false,
      `PCX -> ${targetRpo} should not remain preserved`
    );
  }

  for (const [recordType, sourceRpo, targetRpo] of PASS149_PRESERVED_BOUNDARIES) {
    assert.equal(
      manifestRows.some(
        (row) =>
          row.active === "true" &&
          row.record_type === recordType &&
          row.source_rpo === sourceRpo &&
          row.target_rpo === targetRpo &&
          row.ownership === "preserved_cross_boundary"
      ),
      true,
      `${recordType} ${sourceRpo} -> ${targetRpo} should remain preserved`
    );
  }

  assert.equal(rules.some((rule) => rule.rule_id === "dep_excl_pcx_5dg"), false);
  assert.equal(conditionSets.some((conditionSet) => conditionSet.condition_set_id === "cs_selected_pcx"), false);
  assert.equal(conditionTerms.some((term) => term.left_ref === "opt_pcx_001"), false);
  assert.ok(autoAdds.find((row) => row.auto_add_id === "aa_pcx_5dg" && row.target_price_policy_id === "included_zero"));
  assert.equal(priceRules.some((row) => row.condition_selector_id === "opt_pcx_001"), false);
});

test("pass 151 auto_adds CSV migrates only PCX package include for 5DG", () => {
  const autoAdds = parseCsv(fs.readFileSync("data/stingray/logic/auto_adds.csv", "utf8"));
  const rules = parseCsv(fs.readFileSync("data/stingray/logic/dependency_rules.csv", "utf8"));
  const conditionSets = parseCsv(fs.readFileSync("data/stingray/logic/condition_sets.csv", "utf8"));
  const conditionTerms = parseCsv(fs.readFileSync("data/stingray/logic/condition_terms.csv", "utf8"));
  const manifestRows = parseCsv(fs.readFileSync("data/stingray/validation/projected_slice_ownership.csv", "utf8"));
  const production = loadGeneratedData();
  const projected = emitCsvLegacyFragment();

  assert.equal(autoAdds.filter((row) => row.active === "true").length, 19);
  assert.equal(rules.length, 86);
  assert.equal(rules.filter((rule) => rule.rule_type === "requires").length, 2);
  assert.equal(rules.filter((rule) => rule.rule_type === "excludes").length, 84);
  assert.equal(conditionSets.length, 42);
  assert.equal(conditionTerms.length, 44);

  for (const [autoAddId, sourceId, targetId] of PASS151_INCLUDE_PAIRS) {
    const row = autoAdds.find((candidate) => candidate.auto_add_id === autoAddId);
    assert.ok(row, `${autoAddId} should exist`);
    assert.equal(row.source_selector_type, "selectable");
    assert.equal(row.source_selector_id, sourceId);
    assert.equal(row.target_selectable_id, targetId);
    assert.equal(row.target_price_policy_id, "included_zero");
    assert.equal(row.quantity, "1");
    assert.equal(row.if_target_already_selected, "convert_existing_to_included");
    assert.equal(row.removal_policy, "remove_when_no_triggers");
    assert.equal(row.conflict_policy, "lowest_price_wins");
    assert.equal(row.cascade, "true");
    assert.equal(row.priority, "20");
    assert.equal(row.active, "true");

    const productionRule = production.rules.find((rule) => rule.source_id === sourceId && rule.target_id === targetId && rule.rule_type === "includes");
    const projectedRule = projected.rules.find((rule) => rule.source_id === sourceId && rule.target_id === targetId && rule.rule_type === "includes");
    const productionPriceRule = production.priceRules.find(
      (rule) => rule.condition_option_id === sourceId && rule.target_option_id === targetId && Number(rule.price_value) === 0
    );
    const projectedPriceRule = projected.priceRules.find(
      (rule) => rule.condition_option_id === sourceId && rule.target_option_id === targetId && Number(rule.price_value) === 0
    );

    assert.ok(productionRule, `${sourceId} -> ${targetId} include should exist in production`);
    assert.ok(productionPriceRule, `${sourceId} -> ${targetId} priceRule 0 should exist in production`);
    assert.deepEqual(plain(projectedRule), plain(productionRule));
    assert.deepEqual(projectedPriceRule, {
      ...plain(productionPriceRule),
      price_rule_id: `pr_${sourceId}_${targetId}_included_zero`,
    });
  }

  for (const [recordType, sourceRpo, targetRpo] of [
    ["rule", "PCX", "5DG"],
    ["priceRule", "PCX", "5DG"],
  ]) {
    assert.equal(
      manifestRows.some(
        (row) =>
          row.active === "true" &&
          row.record_type === recordType &&
          row.source_rpo === sourceRpo &&
          row.target_rpo === targetRpo &&
          row.ownership === "preserved_cross_boundary"
      ),
      false,
      `${recordType} ${sourceRpo} -> ${targetRpo} should not remain preserved`
    );
  }

  for (const [recordType, sourceRpo, targetRpo] of PASS149_PRESERVED_BOUNDARIES.filter(([, sourceRpo]) => sourceRpo !== "PCX")) {
    assert.equal(
      manifestRows.some(
        (row) =>
          row.active === "true" &&
          row.record_type === recordType &&
          row.source_rpo === sourceRpo &&
          row.target_rpo === targetRpo &&
          row.ownership === "preserved_cross_boundary"
      ),
      true,
      `${recordType} ${sourceRpo} -> ${targetRpo} should remain preserved`
    );
  }

  assert.equal(rules.some((rule) => rule.rule_id === "dep_excl_pcx_5dg"), false);
});

test("pass 144 migrated PDV to Stripe plain excludes emit production-shaped legacy rules", () => {
  const production = loadGeneratedData();
  const projected = emitCsvLegacyFragment();
  const fields = [
    "source_id",
    "rule_type",
    "target_id",
    "target_type",
    "source_type",
    "source_section",
    "target_section",
    "source_selection_mode",
    "target_selection_mode",
    "body_style_scope",
    "disabled_reason",
    "auto_add",
    "active",
    "runtime_action",
    "review_flag",
  ];

  for (const [, sourceId, targetId] of PASS144_EXCLUDE_PAIRS) {
    const productionRule = production.rules.find(
      (rule) => rule.source_id === sourceId && rule.target_id === targetId && rule.rule_type === "excludes"
    );
    const projectedRule = projected.rules.find(
      (rule) => rule.source_id === sourceId && rule.target_id === targetId && rule.rule_type === "excludes"
    );

    assert.ok(productionRule, `production should include ${sourceId} -> ${targetId}`);
    assert.ok(projectedRule, `projected CSV fragment should include ${sourceId} -> ${targetId}`);
    assert.deepEqual(
      Object.fromEntries(fields.map((field) => [field, projectedRule[field]])),
      Object.fromEntries(fields.map((field) => [field, productionRule[field]]))
    );
  }
});

test("pass 144 migrated PDV to Stripe plain excludes report dependency conflicts", () => {
  for (const [ruleId, sourceId, targetId, conditionSetId] of PASS144_EXCLUDE_PAIRS) {
    const result = evaluate("1lt_c07", [sourceId, targetId]);
    const conflict = result.conflicts.find((item) => item.rule_id === ruleId);

    assert.equal(result.validation_errors.length, 0);
    assert.equal(conflict?.conflict_source, "dependency_rule");
    assert.equal(conflict?.target_condition_set_id, conditionSetId);
    assert.equal(conflict?.target_selectable_id, targetId);
    assert.equal(conflict?.message, "Blocked by PDV LPO, Stingray R Appearance Package.");
  }
});

test("pass 137 migrated car-cover to 5ZU excludes emit production-shaped legacy rules", () => {
  const production = loadGeneratedData();
  const projected = emitCsvLegacyFragment();
  const fields = [
    "source_id",
    "rule_type",
    "target_id",
    "target_type",
    "source_type",
    "source_section",
    "target_section",
    "source_selection_mode",
    "target_selection_mode",
    "body_style_scope",
    "disabled_reason",
    "auto_add",
    "active",
    "runtime_action",
    "review_flag",
  ];

  for (const [, sourceId, targetId] of PASS137_EXCLUDE_PAIRS) {
    const productionRule = production.rules.find(
      (rule) => rule.source_id === sourceId && rule.target_id === targetId && rule.rule_type === "excludes"
    );
    const projectedRule = projected.rules.find(
      (rule) => rule.source_id === sourceId && rule.target_id === targetId && rule.rule_type === "excludes"
    );

    assert.ok(productionRule, `production should include ${sourceId} -> ${targetId}`);
    assert.ok(projectedRule, `projected CSV fragment should include ${sourceId} -> ${targetId}`);
    assert.deepEqual(
      Object.fromEntries(fields.map((field) => [field, projectedRule[field]])),
      Object.fromEntries(fields.map((field) => [field, productionRule[field]]))
    );
  }
});

test("pass 137 migrated car-cover to 5ZU excludes report dependency conflicts", () => {
  for (const [ruleId, sourceId, targetId, conditionSetId] of PASS137_EXCLUDE_PAIRS) {
    const result = evaluate("1lt_c07", [sourceId, targetId]);
    const conflict = result.conflicts.find((item) => item.rule_id === ruleId);

    assert.equal(result.validation_errors.length, 0);
    assert.equal(conflict?.conflict_source, "dependency_rule");
    assert.equal(conflict?.target_condition_set_id, conditionSetId);
    assert.equal(conflict?.target_selectable_id, targetId);
  }
});

test("pass 135 migrated R88 and SFZ stripe excludes emit production-shaped legacy rules", () => {
  const production = loadGeneratedData();
  const projected = emitCsvLegacyFragment();
  const fields = [
    "source_id",
    "rule_type",
    "target_id",
    "target_type",
    "source_type",
    "source_section",
    "target_section",
    "source_selection_mode",
    "target_selection_mode",
    "body_style_scope",
    "disabled_reason",
    "auto_add",
    "active",
    "runtime_action",
    "review_flag",
  ];

  for (const [, sourceId, targetId] of PASS135_EXCLUDE_PAIRS) {
    const productionRule = production.rules.find(
      (rule) => rule.source_id === sourceId && rule.target_id === targetId && rule.rule_type === "excludes"
    );
    const projectedRule = projected.rules.find(
      (rule) => rule.source_id === sourceId && rule.target_id === targetId && rule.rule_type === "excludes"
    );

    assert.ok(productionRule, `production should include ${sourceId} -> ${targetId}`);
    assert.ok(projectedRule, `projected CSV fragment should include ${sourceId} -> ${targetId}`);
    assert.deepEqual(
      Object.fromEntries(fields.map((field) => [field, projectedRule[field]])),
      Object.fromEntries(fields.map((field) => [field, productionRule[field]]))
    );
  }
});

test("pass 135 migrated R88 and SFZ stripe excludes report sample dependency conflicts", () => {
  for (const [ruleId, sourceId, targetId, conditionSetId] of [
    PASS135_EXCLUDE_PAIRS[0],
    PASS135_EXCLUDE_PAIRS[6],
    PASS135_EXCLUDE_PAIRS[13],
    PASS135_EXCLUDE_PAIRS[24],
  ]) {
    const result = evaluate("1lt_c07", [sourceId, targetId]);
    const conflict = result.conflicts.find((item) => item.rule_id === ruleId);

    assert.equal(result.validation_errors.length, 0);
    assert.equal(conflict?.conflict_source, "dependency_rule");
    assert.equal(conflict?.target_condition_set_id, conditionSetId);
    assert.equal(conflict?.target_selectable_id, targetId);
  }
});

test("pass 134 Stripes catalog slice emits production-equivalent choices", () => {
  const production = loadGeneratedData();
  const projected = emitCsvLegacyFragment();
  const fields = [
    "option_id",
    "rpo",
    "label",
    "description",
    "section_id",
    "section_name",
    "category_id",
    "category_name",
    "step_key",
    "choice_mode",
    "selection_mode",
    "status",
    "selectable",
    "base_price",
    "display_order",
  ];

  for (const optionId of PASS134_STRIPE_OPTION_IDS) {
    const productionChoice = production.choices.find((choice) => choice.option_id === optionId && choice.variant_id === "1lt_c07");
    const projectedChoice = projected.choices.find((choice) => choice.option_id === optionId && choice.variant_id === "1lt_c07");

    assert.ok(productionChoice, `production should include ${optionId}`);
    assert.ok(projectedChoice, `projected CSV fragment should include ${optionId}`);
    assert.deepEqual(
      Object.fromEntries(fields.map((field) => [field, projectedChoice[field]])),
      Object.fromEntries(fields.map((field) => [field, productionChoice[field]]))
    );
  }
});

test("pass 134 and 135 Stripes projection keeps package paint and stinger-stripe boundaries production-owned", () => {
  const projected = emitCsvLegacyFragment();
  const migratedKeys = new Set(
    [
      ...PASS135_EXCLUDE_PAIRS,
      ...PASS143_EXCLUDE_PAIRS.filter(([, , targetId]) => PASS134_STRIPE_OPTION_IDS.includes(targetId)),
      ...PASS144_EXCLUDE_PAIRS,
    ].map(([, sourceId, targetId]) => `${sourceId}->${targetId}`)
  );
  const stripeIds = new Set(PASS134_STRIPE_OPTION_IDS);
  const stripeRules = projected.rules.filter((rule) => stripeIds.has(rule.source_id) || stripeIds.has(rule.target_id));

  assert.equal(stripeRules.length, migratedKeys.size);
  assert.deepEqual(
    stripeRules.map((rule) => `${rule.source_id}->${rule.target_id}`).sort(),
    [...migratedKeys].sort()
  );
});

test("golden first-slice scenarios are production-derived CSV fixtures", () => {
  const builds = fixtureRows("golden_builds.csv");
  const selections = fixtureRows("golden_build_selections.csv");
  const expectedLines = fixtureRows("golden_expected_lines.csv");
  const expectedRequirements = fixtureRows("golden_expected_requirements.csv");
  const expectedConflicts = fixtureRows("golden_expected_conflicts.csv");

  assert.deepEqual(builds.map((row) => row.test_id), [
    "gb_coupe_b6p",
    "gb_coupe_bcp",
    "gb_coupe_bcp_b6p",
    "gb_convertible_bcp_missing_zz3",
    "gb_convertible_bcp_with_zz3",
    "gb_exclusive_engine_covers",
    "gb_explicit_d3v_b6p",
    "gb_explicit_sl9_b6p",
  ]);

  for (const build of builds) {
    const selectedIds = selections.filter((row) => row.test_id === build.test_id).map((row) => row.selectable_id);
    const result = evaluate(build.variant_id, selectedIds);
    for (const expected of expectedLines.filter((row) => row.test_id === build.test_id)) {
      const line = lineById(result, expected.selectable_id);
      assert.ok(line, `${build.test_id} should include ${expected.selectable_id}`);
      assert.equal(line.final_price_usd, Number(expected.final_price_usd), `${build.test_id} ${expected.selectable_id} price`);
      assert.deepEqual(line.provenance, expected.provenance.split("|"), `${build.test_id} ${expected.selectable_id} provenance`);
    }
    assert.equal(result.open_requirements.length, expectedRequirements.filter((row) => row.test_id === build.test_id).length);
    assert.equal(result.conflicts.length, expectedConflicts.filter((row) => row.test_id === build.test_id).length);
  }
});

test("first-slice compiler does not hard-code RPO-specific control flow", () => {
  const source = fs.readFileSync(SCRIPT, "utf8");
  const forbiddenBranch = /\b(?:if|elif)\s+[^\n:]*\b(?:rpo|selectable_id|option)\b[^\n:]*\b(?:B6P|D3V|SL9|ZZ3|BCP|BCS|BC4|BC7|RXJ|VWD|5ZD|5ZC|RXH|SXB|SXR|SXT|opt_b6p|opt_d3v|opt_sl9|opt_zz3|opt_bcp|opt_bcs|opt_bc4|opt_bc7|opt_rxj|opt_vwd|opt_5zd|opt_5zc|opt_rxh|opt_sxb|opt_sxr|opt_sxt)\b/;
  assert.equal(forbiddenBranch.test(source), false);
});
