import assert from "node:assert/strict";
import { execFileSync, spawnSync } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import test from "node:test";

const PYTHON = ".venv/bin/python";
const SCRIPT = "scripts/stingray_csv_first_slice.py";

function makeTempPackage() {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), "stingray-ref-selector-"));
  const packageDir = path.join(root, "stingray");
  fs.cpSync("data/stingray", packageDir, { recursive: true });
  return { root, packageDir };
}

function appendRows(filePath, rows) {
  fs.appendFileSync(filePath, `${rows.join("\n")}\n`, "utf8");
}

function parseCsv(source) {
  const rows = [];
  let row = [];
  let field = "";
  let inQuotes = false;
  for (let index = 0; index < source.length; index += 1) {
    const char = source[index];
    const next = source[index + 1];
    if (char === '"' && inQuotes && next === '"') {
      field += '"';
      index += 1;
    } else if (char === '"') {
      inQuotes = !inQuotes;
    } else if (char === "," && !inQuotes) {
      row.push(field);
      field = "";
    } else if ((char === "\n" || char === "\r") && !inQuotes) {
      if (char === "\r" && next === "\n") index += 1;
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

function csvCell(value) {
  return /[",\n\r]/.test(value) ? `"${value.replaceAll('"', '""')}"` : value;
}

function writeCsv(filePath, rows) {
  const headers = Object.keys(rows[0]);
  const source = [
    headers.join(","),
    ...rows.map((row) => headers.map((header) => csvCell(row[header] || "")).join(",")),
  ].join("\n");
  fs.writeFileSync(filePath, `${source}\n`, "utf8");
}

function setReferenceLegacyMetadata(packageDir, referenceId, legacySectionId, legacySelectionMode) {
  const filePath = path.join(packageDir, "validation", "non_selectable_references.csv");
  const rows = parseCsv(fs.readFileSync(filePath, "utf8")).map((row) => ({
    ...row,
    legacy_section_id: row.legacy_section_id || "",
    legacy_selection_mode: row.legacy_selection_mode || "",
  }));
  const row = rows.find((item) => item.reference_id === referenceId);
  assert.ok(row, `${referenceId} should exist`);
  row.legacy_section_id = legacySectionId;
  row.legacy_selection_mode = legacySelectionMode;
  writeCsv(filePath, rows);
}

function emitLegacyFragment(packageDir) {
  const output = execFileSync(PYTHON, [SCRIPT, "--package", packageDir, "--emit-legacy-fragment"], {
    cwd: process.cwd(),
    encoding: "utf8",
  });
  return JSON.parse(output);
}

function runFragment(packageDir) {
  return spawnSync(PYTHON, [SCRIPT, "--package", packageDir, "--emit-legacy-fragment"], {
    cwd: process.cwd(),
    encoding: "utf8",
    maxBuffer: 8 * 1024 * 1024,
  });
}

function addReferenceSupportFixtureRows(packageDir) {
  appendRows(path.join(packageDir, "logic", "condition_sets.csv"), [
    "cs_ref_selected_5vm_test,5VM reference selected,Test-only non-selectable reference condition,true",
    "cs_ref_selected_5w8_test,5W8 reference selected,Test-only non-selectable reference condition,true",
  ]);
  appendRows(path.join(packageDir, "logic", "condition_terms.csv"), [
    "cs_ref_selected_5vm_test,g1,1,reference_selected,ref_5vm,is_true,,false",
    "cs_ref_selected_5w8_test,g1,1,reference_selected,ref_5w8,is_true,,false",
  ]);
  appendRows(path.join(packageDir, "logic", "dependency_rules.csv"), [
    'dep_test_ref_subject_5vm_5v7,excludes,non_selectable_reference,ref_5vm,true,,cs_selected_5v7,disable_and_block,"Blocked by 5VM test reference.",900,true',
    'dep_test_ref_subject_5w8_5v7,excludes,non_selectable_reference,ref_5w8,true,,cs_selected_5v7,disable_and_block,"Blocked by 5W8 test reference.",901,true',
    'dep_test_ref_target_5v7_5vm,excludes,selectable,opt_5v7_001,true,,cs_ref_selected_5vm_test,disable_and_block,"Blocked by 5V7 test reference.",902,true',
    'dep_test_ref_target_5v7_5w8,excludes,selectable,opt_5v7_001,true,,cs_ref_selected_5w8_test,disable_and_block,"Blocked by 5V7 test reference.",903,true',
    'dep_test_ref_both_5vm_5w8,excludes,non_selectable_reference,ref_5vm,true,,cs_ref_selected_5w8_test,disable_and_block,"Blocked by both test references.",904,true',
  ]);
}

function add5zwReferenceTargetFixtureRows(packageDir) {
  appendRows(path.join(packageDir, "logic", "condition_sets.csv"), [
    "cs_ref_selected_5zw_test,5ZW reference selected,Test-only non-selectable 5ZW reference condition,true",
  ]);
  appendRows(path.join(packageDir, "logic", "condition_terms.csv"), [
    "cs_ref_selected_5zw_test,g1,1,reference_selected,ref_5zw,is_true,,false",
  ]);
  appendRows(path.join(packageDir, "logic", "dependency_rules.csv"), [
    'dep_test_ref_target_5v7_5zw,excludes,selectable,opt_5v7_001,true,,cs_ref_selected_5zw_test,disable_and_block,"Blocked by 5V7 test reference.",904,true',
  ]);
}

test("non-selectable references compile as dependency subjects targets and both", () => {
  const { root, packageDir } = makeTempPackage();
  try {
    addReferenceSupportFixtureRows(packageDir);

    const fragment = emitLegacyFragment(packageDir);
    assert.deepEqual(fragment.validation_errors, []);

    const subjectRule = fragment.rules.find((rule) => rule.rule_id === "rule_opt_5vm_001_excludes_opt_5v7_001");
    assert.ok(subjectRule, "missing non-selectable subject rule");
    assert.equal(subjectRule.source_id, "opt_5vm_001");
    assert.equal(subjectRule.source_section, "sec_lpoe_001");
    assert.equal(subjectRule.source_selection_mode, "multi_select_opt");
    assert.equal(subjectRule.target_id, "opt_5v7_001");
    assert.equal(subjectRule.rule_type, "excludes");
    assert.equal(subjectRule.disabled_reason, "Blocked by 5VM test reference.");
    assert.equal(subjectRule.auto_add, "False");
    assert.equal(subjectRule.runtime_action, "active");

    const subject5w8Rule = fragment.rules.find((rule) => rule.rule_id === "rule_opt_5w8_001_excludes_opt_5v7_001");
    assert.ok(subject5w8Rule, "missing 5W8 non-selectable subject rule");
    assert.equal(subject5w8Rule.source_id, "opt_5w8_001");
    assert.equal(subject5w8Rule.source_section, "sec_lpoe_001");
    assert.equal(subject5w8Rule.source_selection_mode, "multi_select_opt");
    assert.equal(subject5w8Rule.target_id, "opt_5v7_001");
    assert.equal(subject5w8Rule.rule_type, "excludes");
    assert.equal(subject5w8Rule.disabled_reason, "Blocked by 5W8 test reference.");

    const target5vmRule = fragment.rules.find((rule) => rule.rule_id === "rule_opt_5v7_001_excludes_opt_5vm_001");
    assert.ok(target5vmRule, "missing 5VM non-selectable target rule");
    assert.equal(target5vmRule.source_id, "opt_5v7_001");
    assert.equal(target5vmRule.target_id, "opt_5vm_001");
    assert.equal(target5vmRule.target_section, "sec_lpoe_001");
    assert.equal(target5vmRule.target_selection_mode, "multi_select_opt");
    assert.equal(target5vmRule.disabled_reason, "Blocked by 5V7 test reference.");

    const target5w8Rule = fragment.rules.find((rule) => rule.rule_id === "rule_opt_5v7_001_excludes_opt_5w8_001");
    assert.ok(target5w8Rule, "missing 5W8 non-selectable target rule");
    assert.equal(target5w8Rule.source_id, "opt_5v7_001");
    assert.equal(target5w8Rule.target_id, "opt_5w8_001");
    assert.equal(target5w8Rule.target_section, "sec_lpoe_001");
    assert.equal(target5w8Rule.target_selection_mode, "multi_select_opt");
    assert.equal(target5w8Rule.disabled_reason, "Blocked by 5V7 test reference.");

    const bothRule = fragment.rules.find((rule) => rule.rule_id === "rule_opt_5vm_001_excludes_opt_5w8_001");
    assert.ok(bothRule, "missing both-reference rule");
    assert.equal(bothRule.source_id, "opt_5vm_001");
    assert.equal(bothRule.target_id, "opt_5w8_001");
    assert.equal(bothRule.disabled_reason, "Blocked by both test references.");
    assert.equal(fragment.choices.some((choice) => choice.option_id === "opt_5vm_001" || choice.option_id === "opt_5w8_001"), false);
  } finally {
    fs.rmSync(root, { recursive: true, force: true });
  }
});

test("5ZW reference target emits production-shaped legacy metadata without becoming a choice", () => {
  const { root, packageDir } = makeTempPackage();
  try {
    add5zwReferenceTargetFixtureRows(packageDir);

    const fragment = emitLegacyFragment(packageDir);
    assert.deepEqual(fragment.validation_errors, []);

    const rule = fragment.rules.find((item) => item.rule_id === "rule_opt_5v7_001_excludes_opt_5zw_001");
    assert.ok(rule, "missing 5ZW reference target rule");
    assert.equal(rule.target_id, "opt_5zw_001");
    assert.equal(rule.target_section, "sec_spoi_001");
    assert.equal(rule.target_selection_mode, "multi_select_opt");
    assert.equal(fragment.choices.some((choice) => choice.rpo === "5ZW" || choice.option_id === "opt_5zw_001"), false);
  } finally {
    fs.rmSync(root, { recursive: true, force: true });
  }
});

test("emitted non-selectable reference rules require legacy metadata", () => {
  const { root, packageDir } = makeTempPackage();
  try {
    setReferenceLegacyMetadata(packageDir, "nsref_5zw", "", "");
    add5zwReferenceTargetFixtureRows(packageDir);

    const result = runFragment(packageDir);
    assert.notEqual(result.status, 0);
    const fragment = JSON.parse(result.stdout);
    assert.ok(
      fragment.validation_errors.some(
        (error) =>
          error.includes("dep_test_ref_target_5v7_5zw") &&
          error.includes("opt_5zw_001") &&
          error.includes("missing legacy_section_id") &&
          error.includes("missing legacy_selection_mode")
      ),
      fragment.validation_errors.join("\n")
    );
  } finally {
    fs.rmSync(root, { recursive: true, force: true });
  }
});

test("unknown non-selectable references fail validation", () => {
  const { root, packageDir } = makeTempPackage();
  try {
    appendRows(path.join(packageDir, "logic", "condition_sets.csv"), [
      "cs_ref_selected_unknown_test,Unknown reference selected,Test-only invalid reference condition,true",
    ]);
    appendRows(path.join(packageDir, "logic", "condition_terms.csv"), [
      "cs_ref_selected_unknown_test,g1,1,reference_selected,ref_missing,is_true,,false",
    ]);
    appendRows(path.join(packageDir, "logic", "dependency_rules.csv"), [
      'dep_test_ref_unknown_subject,excludes,non_selectable_reference,ref_missing,true,,cs_selected_5v7,disable_and_block,"Blocked by missing reference.",903,true',
    ]);

    const result = runFragment(packageDir);
    assert.notEqual(result.status, 0);
    const fragment = JSON.parse(result.stdout);
    assert.ok(
      fragment.validation_errors.some((error) => error.includes("references unknown non-selectable reference: ref_missing")),
      fragment.validation_errors.join("\n")
    );
  } finally {
    fs.rmSync(root, { recursive: true, force: true });
  }
});

test("registered non-selectable references stay out of the customer selectable catalog", () => {
  const selectables = fs.readFileSync("data/stingray/catalog/selectables.csv", "utf8");
  for (const id of ["opt_5vm_001", "opt_5w8_001", "opt_5zw_001"]) {
    assert.equal(selectables.includes(id), false, `${id} should not be projected as a selectable`);
  }
});
