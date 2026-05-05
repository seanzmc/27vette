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
  assert.equal(
    inverseResult.conflicts.some((conflict) => conflict.rule_id === "dep_excl_sti_5v7"),
    false
  );
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

  assert.equal(rules.length, 36);
  assert.equal(rules.filter((rule) => rule.rule_type === "requires").length, 2);
  assert.equal(rules.filter((rule) => rule.rule_type === "excludes").length, 34);

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
  const migratedKeys = new Set(PASS135_EXCLUDE_PAIRS.map(([, sourceId, targetId]) => `${sourceId}->${targetId}`));
  const stripeIds = new Set(PASS134_STRIPE_OPTION_IDS);
  const stripeRules = projected.rules.filter((rule) => stripeIds.has(rule.source_id) || stripeIds.has(rule.target_id));

  assert.equal(stripeRules.length, PASS135_EXCLUDE_PAIRS.length);
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
