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
    'dep_test_ref_target_5v7_5vm,excludes,selectable,opt_5v7_001,true,,cs_ref_selected_5vm_test,disable_and_block,"Blocked by 5V7 test reference.",901,true',
    'dep_test_ref_both_5vm_5w8,excludes,non_selectable_reference,ref_5vm,true,,cs_ref_selected_5w8_test,disable_and_block,"Blocked by both test references.",902,true',
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
    assert.equal(subjectRule.target_id, "opt_5v7_001");
    assert.equal(subjectRule.rule_type, "excludes");
    assert.equal(subjectRule.disabled_reason, "Blocked by 5VM test reference.");
    assert.equal(subjectRule.auto_add, "False");
    assert.equal(subjectRule.runtime_action, "active");

    const targetRule = fragment.rules.find((rule) => rule.rule_id === "rule_opt_5v7_001_excludes_opt_5vm_001");
    assert.ok(targetRule, "missing non-selectable target rule");
    assert.equal(targetRule.source_id, "opt_5v7_001");
    assert.equal(targetRule.target_id, "opt_5vm_001");
    assert.equal(targetRule.disabled_reason, "Blocked by 5V7 test reference.");

    const bothRule = fragment.rules.find((rule) => rule.rule_id === "rule_opt_5vm_001_excludes_opt_5w8_001");
    assert.ok(bothRule, "missing both-reference rule");
    assert.equal(bothRule.source_id, "opt_5vm_001");
    assert.equal(bothRule.target_id, "opt_5w8_001");
    assert.equal(bothRule.disabled_reason, "Blocked by both test references.");
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
