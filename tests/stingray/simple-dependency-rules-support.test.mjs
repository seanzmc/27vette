import assert from "node:assert/strict";
import { execFileSync, spawnSync } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import test from "node:test";

const PYTHON = ".venv/bin/python";
const SCRIPT = "scripts/stingray_csv_first_slice.py";
const PACKAGE = "data/stingray";
const SIMPLE_FIELDS = [
  "rule_id",
  "rule_type",
  "source_option_id",
  "target_option_id",
  "violation_behavior",
  "message",
  "priority",
  "active",
];

function tempPackage() {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), "stingray-simple-dependency-"));
  const packageDir = path.join(root, "stingray");
  fs.cpSync(PACKAGE, packageDir, { recursive: true });
  return packageDir;
}

function csvEscape(value) {
  const stringValue = String(value ?? "");
  return /[",\n]/.test(stringValue) ? `"${stringValue.replaceAll('"', '""')}"` : stringValue;
}

function writeCsv(filePath, fields, rows) {
  fs.mkdirSync(path.dirname(filePath), { recursive: true });
  const lines = [fields.join(",")];
  for (const row of rows) {
    lines.push(fields.map((field) => csvEscape(row[field] ?? "")).join(","));
  }
  fs.writeFileSync(filePath, `${lines.join("\n")}\n`);
}

function appendRows(filePath, rows) {
  const source = fs.readFileSync(filePath, "utf8").trimEnd();
  fs.writeFileSync(filePath, `${source}\n${rows.join("\n")}\n`);
}

function emitLegacyFragment(packageDir = PACKAGE) {
  const output = execFileSync(PYTHON, [SCRIPT, "--package", packageDir, "--emit-legacy-fragment"], {
    cwd: process.cwd(),
    encoding: "utf8",
  });
  return JSON.parse(output);
}

function evaluate(packageDir, selectedIds) {
  const output = execFileSync(PYTHON, [
    SCRIPT,
    "--package",
    packageDir,
    "--scenario-json",
    JSON.stringify({ variant_id: "1lt_c07", selected_ids: selectedIds }),
  ], {
    cwd: process.cwd(),
    encoding: "utf8",
  });
  return JSON.parse(output);
}

function runLegacyFragment(packageDir) {
  return spawnSync(PYTHON, [SCRIPT, "--package", packageDir, "--emit-legacy-fragment"], {
    cwd: process.cwd(),
    encoding: "utf8",
  });
}

function validationErrors(result) {
  return JSON.parse(result.stdout).validation_errors;
}

function writeSimpleRows(packageDir, rows, fields = SIMPLE_FIELDS) {
  writeCsv(path.join(packageDir, "logic", "simple_dependency_rules.csv"), fields, rows);
}

function restoreNormalizedShtPdvRule(packageDir) {
  appendRows(path.join(packageDir, "logic", "dependency_rules.csv"), [
    'dep_excl_sht_pdv,excludes,selectable,opt_sht_001,true,,cs_selected_pdv,disable_and_block,"Blocked by SHT LPO, Jake hood graphic with Tech Bronze accent.",419,true',
  ]);
}

test("absent and header-only simple_dependency_rules preserve normalized-rule fixture output", () => {
  const absentPackage = tempPackage();
  fs.rmSync(path.join(absentPackage, "logic", "simple_dependency_rules.csv"), { force: true });
  restoreNormalizedShtPdvRule(absentPackage);

  const headerOnlyPackage = tempPackage();
  restoreNormalizedShtPdvRule(headerOnlyPackage);
  writeSimpleRows(headerOnlyPackage, []);
  assert.deepEqual(emitLegacyFragment(headerOnlyPackage), emitLegacyFragment(absentPackage));
});

test("flat exclude compiles to a production-shaped dependency rule and conflict", () => {
  const packageDir = tempPackage();
  writeSimpleRows(packageDir, [
    {
      rule_id: "dep_flat_sbt_vwd",
      rule_type: "excludes",
      source_option_id: "opt_sbt_001",
      target_option_id: "opt_vwd_001",
      violation_behavior: "disable_and_block",
      message: "Blocked by SBT test flat exclude.",
      priority: "901",
      active: "true",
    },
  ]);

  const fragment = emitLegacyFragment(packageDir);
  assert.equal(fragment.validation_errors.length, 0);
  assert.ok(fragment.rules.some((rule) =>
    rule.source_id === "opt_sbt_001"
    && rule.target_id === "opt_vwd_001"
    && rule.rule_type === "excludes"
    && rule.disabled_reason === "Blocked by SBT test flat exclude."
    && rule.auto_add === "False"
    && rule.runtime_action === "active"
  ));

  const result = evaluate(packageDir, ["opt_sbt_001", "opt_vwd_001"]);
  assert.ok(result.conflicts.some((conflict) =>
    conflict.rule_id === "dep_flat_sbt_vwd"
    && conflict.target_condition_set_id === "cs_selected_vwd"
    && conflict.target_selectable_id === "opt_vwd_001"
  ));
});

test("flat require compiles to a production-shaped dependency rule and open requirement", () => {
  const packageDir = tempPackage();
  writeSimpleRows(packageDir, [
    {
      rule_id: "dep_flat_sbt_requires_vwd",
      rule_type: "requires",
      source_option_id: "opt_sbt_001",
      target_option_id: "opt_vwd_001",
      violation_behavior: "disable_and_block",
      message: "Requires VWD test flat require.",
      priority: "902",
      active: "true",
    },
  ]);

  const fragment = emitLegacyFragment(packageDir);
  assert.equal(fragment.validation_errors.length, 0);
  assert.ok(fragment.rules.some((rule) =>
    rule.source_id === "opt_sbt_001"
    && rule.target_id === "opt_vwd_001"
    && rule.rule_type === "requires"
    && rule.disabled_reason === "Requires VWD test flat require."
    && rule.auto_add === "False"
    && rule.runtime_action === "active"
  ));

  const result = evaluate(packageDir, ["opt_sbt_001"]);
  assert.ok(result.open_requirements.some((requirement) =>
    requirement.rule_id === "dep_flat_sbt_requires_vwd"
    && requirement.required_condition_set_id === "cs_selected_vwd"
  ));
});

test("flat rule reuses an existing compatible selected-target condition", () => {
  const packageDir = tempPackage();
  writeSimpleRows(packageDir, [
    {
      rule_id: "dep_flat_sbt_pdv",
      rule_type: "excludes",
      source_option_id: "opt_sbt_001",
      target_option_id: "opt_pdv_001",
      violation_behavior: "disable_and_block",
      message: "Blocked by SBT existing condition reuse.",
      priority: "903",
      active: "true",
    },
  ]);

  const result = evaluate(packageDir, ["opt_sbt_001", "opt_pdv_001"]);
  assert.equal(result.validation_errors.length, 0);
  assert.ok(result.conflicts.some((conflict) =>
    conflict.rule_id === "dep_flat_sbt_pdv"
    && conflict.target_condition_set_id === "cs_selected_pdv"
    && conflict.target_selectable_id === "opt_pdv_001"
  ));
});

test("incompatible generated selected condition collision fails clearly", () => {
  const packageDir = tempPackage();
  appendRows(path.join(packageDir, "logic", "condition_sets.csv"), [
    "cs_selected_vwd,VWD selected incompatible test,,true",
  ]);
  appendRows(path.join(packageDir, "logic", "condition_terms.csv"), [
    "cs_selected_vwd,g1,1,selected,opt_pcx_001,is_true,,false",
  ]);
  writeSimpleRows(packageDir, [
    {
      rule_id: "dep_flat_sbt_vwd",
      rule_type: "excludes",
      source_option_id: "opt_sbt_001",
      target_option_id: "opt_vwd_001",
      violation_behavior: "disable_and_block",
      message: "Blocked by SBT test flat exclude.",
      priority: "901",
      active: "true",
    },
  ]);

  const result = runLegacyFragment(packageDir);
  assert.notEqual(result.status, 0);
  assert.match(validationErrors(result).join("\n"), /simple_dependency_rules dep_flat_sbt_vwd generated condition_set_id cs_selected_vwd already exists but does not select opt_vwd_001/);
});

test("duplicate active normalized dependency rule id collision fails clearly", () => {
  const packageDir = tempPackage();
  writeSimpleRows(packageDir, [
    {
      rule_id: "dep_excl_sbt_cc3",
      rule_type: "excludes",
      source_option_id: "opt_sbt_001",
      target_option_id: "opt_vwd_001",
      violation_behavior: "disable_and_block",
      message: "Blocked by duplicate rule id.",
      priority: "904",
      active: "true",
    },
  ]);

  const result = runLegacyFragment(packageDir);
  assert.notEqual(result.status, 0);
  assert.match(validationErrors(result).join("\n"), /simple_dependency_rules dep_excl_sbt_cc3 collides with active dependency_rules row/);
});

test("non-projected source or target fails clearly", () => {
  const packageDir = tempPackage();
  const ownershipPath = path.join(packageDir, "validation", "projected_slice_ownership.csv");
  const ownership = fs.readFileSync(ownershipPath, "utf8").replace(
    "selectable,,,,,,VWD,projected_owned,Center Cap projected slice,true",
    "selectable,,,,,,VWD,production_guarded,Temp non-projected VWD fixture,true",
  );
  fs.writeFileSync(ownershipPath, ownership);
  writeSimpleRows(packageDir, [
    {
      rule_id: "dep_flat_sbt_vwd",
      rule_type: "excludes",
      source_option_id: "opt_sbt_001",
      target_option_id: "opt_vwd_001",
      violation_behavior: "disable_and_block",
      message: "Blocked by SBT test flat exclude.",
      priority: "901",
      active: "true",
    },
  ]);

  const result = runLegacyFragment(packageDir);
  assert.notEqual(result.status, 0);
  assert.match(validationErrors(result).join("\n"), /simple_dependency_rules dep_flat_sbt_vwd target_option_id is not an active projected-owned selectable: opt_vwd_001/);
});

test("non-simple flat table columns fail schema validation", () => {
  const packageDir = tempPackage();
  writeSimpleRows(
    packageDir,
    [
      {
        rule_id: "dep_flat_scoped",
        rule_type: "excludes",
        source_option_id: "opt_sbt_001",
        target_option_id: "opt_vwd_001",
        applies_when_condition_set_id: "cs_coupe",
        violation_behavior: "disable_and_block",
        message: "Blocked by scoped flat rule.",
        priority: "905",
        active: "true",
      },
    ],
    [
      "rule_id",
      "rule_type",
      "source_option_id",
      "target_option_id",
      "applies_when_condition_set_id",
      "violation_behavior",
      "message",
      "priority",
      "active",
    ],
  );

  const result = runLegacyFragment(packageDir);
  assert.notEqual(result.status, 0);
  assert.match(validationErrors(result).join("\n"), /simple_dependency_rules.csv uses unsupported columns/);
});
