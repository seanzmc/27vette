import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import fs from "node:fs";
import test from "node:test";
import vm from "node:vm";

const PYTHON = ".venv/bin/python";
const SCRIPT = "scripts/stingray_csv_first_slice.py";
const OWNERSHIP_MANIFEST = "data/stingray/validation/projected_slice_ownership.csv";
const PAINT_RPOS = ["G8G", "GBA", "GKA", "GBK", "GTR", "GEC", "GPH", "G4Z", "G26", "GKZ"];
const PASS178_PAINT_EXCLUDES = [
  ["dep_excl_d84_gba", "D84", "GBA", "cs_selected_gba"],
  ["dep_excl_d86_gba", "D86", "GBA", "cs_selected_gba"],
  ["dep_excl_efy_gba", "EFY", "GBA", "cs_selected_gba"],
  ["dep_excl_dpb_gtr", "DPB", "GTR", "cs_selected_gtr"],
  ["dep_excl_dpc_gbk", "DPC", "GBK", "cs_selected_gbk"],
  ["dep_excl_dpg_g26", "DPG", "G26", "cs_selected_g26"],
  ["dep_excl_dpl_gkz", "DPL", "GKZ", "cs_selected_gkz"],
  ["dep_excl_dpl_gph", "DPL", "GPH", "cs_selected_gph"],
  ["dep_excl_dsy_g26", "DSY", "G26", "cs_selected_g26"],
  ["dep_excl_dsz_gkz", "DSZ", "GKZ", "cs_selected_gkz"],
  ["dep_excl_dsz_gph", "DSZ", "GPH", "cs_selected_gph"],
  ["dep_excl_dt0_gbk", "DT0", "GBK", "cs_selected_gbk"],
  ["dep_excl_due_gtr", "DUE", "GTR", "cs_selected_gtr"],
  ["dep_excl_duk_gkz", "DUK", "GKZ", "cs_selected_gkz"],
  ["dep_excl_duk_gph", "DUK", "GPH", "cs_selected_gph"],
  ["dep_excl_duw_gtr", "DUW", "GTR", "cs_selected_gtr"],
  ["dep_excl_dzu_gbk", "DZU", "GBK", "cs_selected_gbk"],
  ["dep_excl_dzx_gkz", "DZX", "GKZ", "cs_selected_gkz"],
  ["dep_excl_dzx_gph", "DZX", "GPH", "cs_selected_gph"],
];
const PRESERVED_PAINT_BOUNDARIES = [["ZYC", "GBA"]];

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

function loadProduction() {
  const context = { window: {} };
  vm.runInNewContext(fs.readFileSync("form-app/data.js", "utf8"), context);
  return context.window.STINGRAY_FORM_DATA;
}

function emitCsvLegacyFragment() {
  const output = execFileSync(PYTHON, [SCRIPT, "--emit-legacy-fragment"], {
    cwd: process.cwd(),
    encoding: "utf8",
    maxBuffer: 8 * 1024 * 1024,
  });
  return JSON.parse(output);
}

function evaluate(variantId, selectedIds) {
  const output = execFileSync(PYTHON, [SCRIPT, "--scenario-json", JSON.stringify({ variant_id: variantId, selected_ids: selectedIds })], {
    cwd: process.cwd(),
    encoding: "utf8",
  });
  return JSON.parse(output);
}

function normalizePaintChoices(rows) {
  return rows
    .filter((choice) => choice.section_id === "sec_pain_001")
    .map((choice) => ({
      choice_id: choice.choice_id,
      option_id: choice.option_id,
      rpo: choice.rpo,
      label: choice.label,
      description: choice.description,
      section_id: choice.section_id,
      section_name: choice.section_name,
      category_id: choice.category_id,
      category_name: choice.category_name,
      step_key: choice.step_key,
      variant_id: choice.variant_id,
      body_style: choice.body_style,
      trim_level: choice.trim_level,
      status: choice.status,
      status_label: choice.status_label,
      selectable: choice.selectable,
      active: choice.active,
      choice_mode: choice.choice_mode,
      selection_mode: choice.selection_mode,
      selection_mode_label: choice.selection_mode_label,
      base_price: Number(choice.base_price || 0),
      display_order: Number(choice.display_order || 0),
      source_detail_raw: choice.source_detail_raw,
    }))
    .sort((a, b) => a.choice_id.localeCompare(b.choice_id));
}

function activeManifestRows() {
  return parseCsv(fs.readFileSync(OWNERSHIP_MANIFEST, "utf8")).filter((row) => row.active === "true");
}

function manifestHas(expected, rows = activeManifestRows()) {
  return rows.some((row) => Object.entries(expected).every(([key, value]) => row[key] === value));
}

function plain(value) {
  return JSON.parse(JSON.stringify(value));
}

function optionIdForRpo(rpo) {
  return `opt_${rpo.toLowerCase()}_001`;
}

function legacyRule(rows, sourceRpo, targetRpo) {
  return rows.find(
    (rule) =>
      rule.source_id === optionIdForRpo(sourceRpo) &&
      rule.target_id === optionIdForRpo(targetRpo) &&
      rule.rule_type === "excludes"
  );
}

test("CSV Paint section emits all production sec_pain_001 choices", () => {
  const production = loadProduction();
  const projected = emitCsvLegacyFragment();
  const productionPaint = normalizePaintChoices(production.choices);
  const projectedPaint = normalizePaintChoices(projected.choices);

  assert.deepEqual(projected.validation_errors, []);
  assert.equal(productionPaint.length, 60);
  assert.equal(projectedPaint.length, 60);
  assert.deepEqual(plain(projectedPaint), plain(productionPaint));
  assert.deepEqual(
    projectedPaint.filter((choice) => choice.variant_id === "1lt_c07").sort((a, b) => a.display_order - b.display_order).map((choice) => choice.rpo),
    PAINT_RPOS
  );
  assert.deepEqual([...new Set(projectedPaint.map((choice) => choice.section_id))], ["sec_pain_001"]);
  assert.deepEqual([...new Set(projectedPaint.map((choice) => choice.choice_mode))], ["single"]);
  assert.deepEqual([...new Set(projectedPaint.map((choice) => choice.selection_mode))], ["single_select_req"]);
});

test("Paint projection owns all Paint choices and retires only the stale GBA guard", () => {
  const rows = parseCsv(fs.readFileSync(OWNERSHIP_MANIFEST, "utf8"));
  const activeRows = rows.filter((row) => row.active === "true");

  for (const rpo of PAINT_RPOS) {
    assert.equal(manifestHas({ record_type: "selectable", rpo, ownership: "projected_owned" }, activeRows), true);
  }

  assert.equal(manifestHas({ record_type: "guardedOption", rpo: "GBA", ownership: "production_guarded" }, activeRows), false);
  assert.ok(
    rows.find((row) => row.record_type === "guardedOption" && row.rpo === "GBA" && row.ownership === "production_guarded" && row.active === "false")
  );
});

test("Pass 178 migrates only approved paint compatibility rules", () => {
  const rules = parseCsv(fs.readFileSync("data/stingray/logic/dependency_rules.csv", "utf8"));
  const conditionSets = parseCsv(fs.readFileSync("data/stingray/logic/condition_sets.csv", "utf8"));
  const conditionTerms = parseCsv(fs.readFileSync("data/stingray/logic/condition_terms.csv", "utf8"));

  assert.equal(rules.length, 130);
  assert.equal(conditionSets.length, 51);
  assert.equal(conditionTerms.length, 53);

  for (const conditionSetId of ["cs_selected_gba", "cs_selected_gtr", "cs_selected_gbk", "cs_selected_g26", "cs_selected_gkz", "cs_selected_gph"]) {
    assert.ok(conditionSets.find((row) => row.condition_set_id === conditionSetId && row.active === "true"), `${conditionSetId} should exist`);
  }

  for (const [ruleId, sourceRpo, targetRpo, conditionSetId] of PASS178_PAINT_EXCLUDES) {
    const rule = rules.find((row) => row.rule_id === ruleId);
    assert.ok(rule, `${ruleId} should exist`);
    assert.equal(rule.rule_type, "excludes");
    assert.equal(rule.subject_selector_type, "selectable");
    assert.equal(rule.subject_selector_id, optionIdForRpo(sourceRpo));
    assert.equal(rule.subject_must_be_selected, "true");
    assert.equal(rule.target_condition_set_id, conditionSetId);
    assert.equal(rule.violation_behavior, "disable_and_block");
    assert.equal(rule.active, "true");
    assert.ok(conditionTerms.find((row) => row.condition_set_id === conditionSetId && row.left_ref === optionIdForRpo(targetRpo)));
  }

  for (const [sourceRpo, targetRpo] of PASS178_PAINT_EXCLUDES.map(([, sourceRpo, targetRpo]) => [sourceRpo, targetRpo])) {
    assert.equal(
      manifestHas({ record_type: "rule", source_rpo: sourceRpo, target_rpo: targetRpo, ownership: "preserved_cross_boundary" }),
      false,
      `${sourceRpo} -> ${targetRpo} should not remain preserved`
    );
  }

  for (const [sourceRpo, targetRpo] of PRESERVED_PAINT_BOUNDARIES) {
    assert.equal(
      manifestHas({ record_type: "rule", source_rpo: sourceRpo, target_rpo: targetRpo, ownership: "preserved_cross_boundary" }),
      true,
      `${sourceRpo} -> ${targetRpo} should remain preserved`
    );
  }
  assert.equal(
    manifestHas({ record_type: "rule", source_rpo: "EFY", target_rpo: "GBA", ownership: "preserved_cross_boundary" }),
    false,
    "EFY -> GBA should not remain preserved"
  );
	  assert.equal(manifestHas({ record_type: "ruleGroup", source_rpo: "5ZU", target_rpo: "G8G", ownership: "preserved_cross_boundary" }), false);
	  assert.equal(manifestHas({ record_type: "ruleGroup", source_rpo: "5ZU", target_rpo: "GBA", ownership: "preserved_cross_boundary" }), false);
	  assert.equal(manifestHas({ record_type: "ruleGroup", source_rpo: "5ZU", target_rpo: "GKZ", ownership: "preserved_cross_boundary" }), false);
	});

test("Pass 178 paint compatibility excludes emit production-shaped legacy rules", () => {
  const production = loadProduction();
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

  assert.deepEqual(projected.validation_errors, []);
  for (const [, sourceRpo, targetRpo] of PASS178_PAINT_EXCLUDES) {
    const productionRule = legacyRule(production.rules, sourceRpo, targetRpo);
    const projectedRule = legacyRule(projected.rules, sourceRpo, targetRpo);
    assert.ok(productionRule, `production should include ${sourceRpo} -> ${targetRpo}`);
    assert.ok(projectedRule, `projected CSV should include ${sourceRpo} -> ${targetRpo}`);
    assert.deepEqual(
      Object.fromEntries(fields.map((field) => [field, projectedRule[field]])),
      Object.fromEntries(fields.map((field) => [field, productionRule[field]]))
    );
  }
});

test("Pass 178 paint compatibility excludes report dependency conflicts", () => {
  const production = loadProduction();

  for (const [ruleId, sourceRpo, targetRpo, conditionSetId] of PASS178_PAINT_EXCLUDES) {
    const sourceId = optionIdForRpo(sourceRpo);
    const targetId = optionIdForRpo(targetRpo);
    const variantId = ["D84", "D86"].includes(sourceRpo) ? "1lt_c67" : "1lt_c07";
    const result = evaluate(variantId, [sourceId, targetId]);
    const conflict = result.conflicts.find((item) => item.rule_id === ruleId);
    const productionRule = legacyRule(production.rules, sourceRpo, targetRpo);

    assert.deepEqual(result.validation_errors, []);
    assert.equal(conflict?.conflict_source, "dependency_rule");
    assert.equal(conflict?.target_condition_set_id, conditionSetId);
    assert.equal(conflict?.target_selectable_id, targetId);
    assert.equal(conflict?.message, productionRule.disabled_reason);
  }
});
