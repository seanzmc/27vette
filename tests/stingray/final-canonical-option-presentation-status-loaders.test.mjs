import assert from "node:assert/strict";
import { execFileSync, spawnSync } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import test from "node:test";

const PYTHON = ".venv/bin/python";
const SCRIPT = "scripts/stingray_csv_first_slice.py";
const PACKAGE = "data/stingray";

const FINAL_CANONICAL_OPTION_FIELDS = [
  "canonical_option_id",
  "rpo",
  "label",
  "description",
  "canonical_kind",
  "duplicate_rpo_classification",
  "active",
  "notes",
];
const FINAL_CANONICAL_OPTION_ALIAS_FIELDS = [
  "alias_id",
  "canonical_option_id",
  "source_row_id",
  "alias_type",
  "alias_value",
  "legacy_option_id",
  "active",
  "notes",
];
const FINAL_OPTION_PRESENTATION_FIELDS = [
  "presentation_id",
  "canonical_option_id",
  "rpo_override",
  "presentation_role",
  "choice_group_id",
  "section_id",
  "section_name",
  "category_id",
  "category_name",
  "step_key",
  "selection_mode",
  "display_order",
  "selectable",
  "active",
  "label",
  "description",
  "source_detail_raw",
  "notes",
  "legacy_option_id",
  "choice_mode",
  "selection_mode_label",
];
const FINAL_OPTION_STATUS_RULE_FIELDS = [
  "status_rule_id",
  "canonical_option_id",
  "presentation_id",
  "context_scope_id",
  "status",
  "status_label",
  "priority",
  "active",
  "notes",
];
const FINAL_VARIANT_FIELDS = [
  "variant_id",
  "model_year",
  "gm_model_code",
  "model_key",
  "body_style",
  "trim_level",
  "active",
  "notes",
];
const FINAL_CONTEXT_SCOPE_FIELDS = [
  "context_scope_id",
  "model_year",
  "model_key",
  "variant_id",
  "body_style",
  "trim_level",
  "priority",
  "active",
  "notes",
];

function tempPackage() {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), "stingray-final-canonical-options-"));
  const packageDir = path.join(root, "stingray");
  fs.cpSync(PACKAGE, packageDir, { recursive: true });
  fs.rmSync(path.join(packageDir, "canonical"), { recursive: true, force: true });
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

function emitLegacyFragment(packageDir = PACKAGE) {
  const output = execFileSync(PYTHON, [SCRIPT, "--package", packageDir, "--emit-legacy-fragment"], {
    cwd: process.cwd(),
    encoding: "utf8",
    maxBuffer: 16 * 1024 * 1024,
  });
  return JSON.parse(output);
}

function runLegacyFragment(packageDir) {
  return spawnSync(PYTHON, [SCRIPT, "--package", packageDir, "--emit-legacy-fragment"], {
    cwd: process.cwd(),
    encoding: "utf8",
    maxBuffer: 16 * 1024 * 1024,
  });
}

function validationErrors(result) {
  return JSON.parse(result.stdout).validation_errors.join("\n");
}

function writeFinalOptionTables(packageDir, {
  canonicalOptionRows = [],
  aliasRows = [],
  presentationRows = [],
  statusRows = [],
} = {}) {
  writeCsv(path.join(packageDir, "canonical", "options", "canonical_options.csv"), FINAL_CANONICAL_OPTION_FIELDS, canonicalOptionRows);
  writeCsv(path.join(packageDir, "canonical", "options", "canonical_option_aliases.csv"), FINAL_CANONICAL_OPTION_ALIAS_FIELDS, aliasRows);
  writeCsv(path.join(packageDir, "canonical", "presentation", "option_presentations.csv"), FINAL_OPTION_PRESENTATION_FIELDS, presentationRows);
  writeCsv(path.join(packageDir, "canonical", "status", "option_status_rules.csv"), FINAL_OPTION_STATUS_RULE_FIELDS, statusRows);
}

function writeFinalContextTables(packageDir, { variantRows = finalVariantRows(), contextScopeRows = finalContextScopeRows() } = {}) {
  writeCsv(path.join(packageDir, "canonical", "status", "variants.csv"), FINAL_VARIANT_FIELDS, variantRows);
  writeCsv(path.join(packageDir, "canonical", "status", "context_scopes.csv"), FINAL_CONTEXT_SCOPE_FIELDS, contextScopeRows);
}

function finalVariantRows() {
  return [
    ["1lt_c07", "C07", "coupe", "1LT"],
    ["2lt_c07", "C07", "coupe", "2LT"],
    ["3lt_c07", "C07", "coupe", "3LT"],
    ["1lt_c67", "C67", "convertible", "1LT"],
    ["2lt_c67", "C67", "convertible", "2LT"],
    ["3lt_c67", "C67", "convertible", "3LT"],
  ].map(([variant_id, gm_model_code, body_style, trim_level]) => ({
    variant_id,
    model_year: "2027",
    gm_model_code,
    model_key: "stingray",
    body_style,
    trim_level,
    active: "true",
    notes: "Temp final variant fixture.",
  }));
}

function finalContextScopeRows() {
  return [
    {
      context_scope_id: "ctx_2027_stingray",
      model_year: "2027",
      model_key: "stingray",
      variant_id: "",
      body_style: "",
      trim_level: "",
      priority: "1",
      active: "true",
      notes: "Temp model default scope.",
    },
    {
      context_scope_id: "ctx_1lt_c07",
      model_year: "2027",
      model_key: "stingray",
      variant_id: "1lt_c07",
      body_style: "coupe",
      trim_level: "1LT",
      priority: "10",
      active: "true",
      notes: "Temp exact variant scope.",
    },
  ];
}

function j6aRows() {
  return {
    canonicalOptionRows: [
      {
        canonical_option_id: "canonical_j6a",
        rpo: "J6A",
        label: "Bright Red-painted brake calipers",
        description: "Temp J6A-like caliper description.",
        canonical_kind: "customer_choice",
        duplicate_rpo_classification: "display_only_duplicate",
        active: "true",
        notes: "Temp final canonical J6A-like option.",
      },
    ],
    aliasRows: [
      {
        alias_id: "alias_j6a_legacy_choice",
        canonical_option_id: "canonical_j6a",
        source_row_id: "",
        alias_type: "legacy_option_id",
        alias_value: "opt_j6a_001",
        legacy_option_id: "opt_j6a_001",
        active: "true",
        notes: "Temp final alias.",
      },
    ],
    presentationRows: [
      {
        presentation_id: "pres_j6a_caliper_choice",
        canonical_option_id: "canonical_j6a",
        rpo_override: "",
        presentation_role: "customer_choice",
        choice_group_id: "cg_calipers",
        section_id: "sec_cali_001",
        section_name: "Caliper Color",
        category_id: "cat_exte_001",
        category_name: "Exterior",
        step_key: "calipers",
        selection_mode: "single_select_req",
        display_order: "10",
        selectable: "True",
        active: "true",
        label: "",
        description: "",
        source_detail_raw: "",
        notes: "Temp final customer choice presentation.",
        legacy_option_id: "opt_j6a_001",
        choice_mode: "single",
        selection_mode_label: "Required single choice",
      },
      {
        presentation_id: "pres_j6a_standard_options",
        canonical_option_id: "canonical_j6a",
        rpo_override: "",
        presentation_role: "standard_options_display",
        choice_group_id: "",
        section_id: "sec_stan_002",
        section_name: "Standard Options",
        category_id: "cat_stan_001",
        category_name: "Standard Equipment",
        step_key: "standard_equipment",
        selection_mode: "display_only",
        display_order: "20",
        selectable: "False",
        active: "true",
        label: "Calipers",
        description: "Bright Red-painted brake calipers",
        source_detail_raw: "",
        notes: "Temp final Standard Options presentation.",
        legacy_option_id: "opt_j6a_002",
        choice_mode: "display",
        selection_mode_label: "Display only",
      },
    ],
    statusRows: [
      {
        status_rule_id: "status_j6a_choice_default",
        canonical_option_id: "",
        presentation_id: "pres_j6a_caliper_choice",
        context_scope_id: "ctx_2027_stingray",
        status: "standard_choice",
        status_label: "Standard",
        priority: "10",
        active: "true",
        notes: "Temp final choice status.",
      },
      {
        status_rule_id: "status_j6a_choice_variant",
        canonical_option_id: "",
        presentation_id: "pres_j6a_caliper_choice",
        context_scope_id: "ctx_1lt_c07",
        status: "unavailable",
        status_label: "Not Available",
        priority: "1",
        active: "true",
        notes: "Temp final variant-specific status.",
      },
      {
        status_rule_id: "status_j6a_display_default",
        canonical_option_id: "",
        presentation_id: "pres_j6a_standard_options",
        context_scope_id: "ctx_2027_stingray",
        status: "standard_fixed",
        status_label: "Standard",
        priority: "10",
        active: "true",
        notes: "Temp final display status.",
      },
    ],
  };
}

function writeJ6aFixture(packageDir, rows = j6aRows()) {
  writeFinalContextTables(packageDir);
  writeFinalOptionTables(packageDir, rows);
}

test("absent and header-only final canonical option presentation status tables preserve output when no final rows are authored", () => {
  const absentPackage = tempPackage();
  fs.rmSync(path.join(absentPackage, "canonical", "options", "canonical_options.csv"), { force: true });
  fs.rmSync(path.join(absentPackage, "canonical", "options", "canonical_option_aliases.csv"), { force: true });
  fs.rmSync(path.join(absentPackage, "canonical", "presentation", "option_presentations.csv"), { force: true });
  fs.rmSync(path.join(absentPackage, "canonical", "status", "option_status_rules.csv"), { force: true });

  const headerOnlyPackage = tempPackage();
  writeFinalOptionTables(headerOnlyPackage);

  assert.deepEqual(emitLegacyFragment(headerOnlyPackage), emitLegacyFragment(absentPackage));
});

test("temp final J6A-like fixture emits customer choice and Standard Options display presentations", () => {
  const packageDir = tempPackage();
  writeJ6aFixture(packageDir);

  const fragment = emitLegacyFragment(packageDir);
  assert.equal(fragment.validation_errors.length, 0);

  const choiceRows = fragment.choices.filter((row) => row.option_id === "opt_j6a_001");
  const displayRows = fragment.choices.filter((row) => row.option_id === "opt_j6a_002");
  assert.equal(choiceRows.length, 6);
  assert.equal(displayRows.length, 6);

  const unavailableChoice = fragment.choices.find((row) => row.choice_id === "1lt_c07__opt_j6a_001");
  const standardChoice = fragment.choices.find((row) => row.choice_id === "2lt_c07__opt_j6a_001");
  assert.equal(unavailableChoice.status, "unavailable");
  assert.equal(unavailableChoice.status_label, "Not Available");
  assert.equal(standardChoice.status, "standard");
  assert.equal(standardChoice.status_label, "Standard");

  assert.ok(choiceRows.every((row) =>
    row.rpo === "J6A"
    && row.section_name === "Caliper Color"
    && row.selection_mode === "single_select_req"
    && row.selectable === "True"
  ));
  assert.ok(displayRows.every((row) =>
    row.rpo === "J6A"
    && row.section_name === "Standard Options"
    && row.choice_mode === "display"
    && row.selection_mode === "display_only"
    && row.selectable === "False"
    && row.status === "standard"
    && row.status_label === "Standard"
  ));
});

test("final canonical presentation rejects missing canonical refs and duplicate legacy IDs", () => {
  const missingCanonicalPackage = tempPackage();
  const missingCanonicalRows = j6aRows();
  missingCanonicalRows.presentationRows[0].canonical_option_id = "canonical_missing";
  writeJ6aFixture(missingCanonicalPackage, missingCanonicalRows);
  const missingCanonicalResult = runLegacyFragment(missingCanonicalPackage);
  assert.notEqual(missingCanonicalResult.status, 0);
  assert.match(validationErrors(missingCanonicalResult), /option_presentations pres_j6a_caliper_choice references missing canonical option: canonical_missing/);

  const duplicateLegacyPackage = tempPackage();
  const duplicateLegacyRows = j6aRows();
  duplicateLegacyRows.presentationRows[1].legacy_option_id = "opt_j6a_001";
  writeJ6aFixture(duplicateLegacyPackage, duplicateLegacyRows);
  const duplicateLegacyResult = runLegacyFragment(duplicateLegacyPackage);
  assert.notEqual(duplicateLegacyResult.status, 0);
  assert.match(validationErrors(duplicateLegacyResult), /duplicate legacy_option_id opt_j6a_001/);
});

test("final canonical status rules reject missing presentation refs and invalid context scope", () => {
  const missingPresentationPackage = tempPackage();
  const missingPresentationRows = j6aRows();
  missingPresentationRows.statusRows[0].presentation_id = "pres_missing";
  writeJ6aFixture(missingPresentationPackage, missingPresentationRows);
  const missingPresentationResult = runLegacyFragment(missingPresentationPackage);
  assert.notEqual(missingPresentationResult.status, 0);
  assert.match(validationErrors(missingPresentationResult), /option_status_rules status_j6a_choice_default references missing final presentation: pres_missing/);

  const invalidContextPackage = tempPackage();
  const invalidContextRows = j6aRows();
  invalidContextRows.statusRows[0].context_scope_id = "ctx_missing";
  writeJ6aFixture(invalidContextPackage, invalidContextRows);
  const invalidContextResult = runLegacyFragment(invalidContextPackage);
  assert.notEqual(invalidContextResult.status, 0);
  assert.match(validationErrors(invalidContextResult), /option_status_rules status_j6a_choice_default references missing context scope: ctx_missing/);
});

test("final canonical status rows cannot reference transitional canonical or presentation IDs", () => {
  const packageDir = tempPackage();
  writeFinalContextTables(packageDir);
  writeFinalOptionTables(packageDir, {
    statusRows: [
      {
        status_rule_id: "status_transitional_canonical",
        canonical_option_id: "canonical_qeb",
        presentation_id: "",
        context_scope_id: "ctx_2027_stingray",
        status: "standard_choice",
        status_label: "Standard",
        priority: "10",
        active: "true",
        notes: "Temp invalid final status target.",
      },
      {
        status_rule_id: "status_transitional_presentation",
        canonical_option_id: "",
        presentation_id: "pres_qeb_wheels_choice",
        context_scope_id: "ctx_2027_stingray",
        status: "standard_choice",
        status_label: "Standard",
        priority: "10",
        active: "true",
        notes: "Temp invalid final status target.",
      },
    ],
  });

  const result = runLegacyFragment(packageDir);
  assert.notEqual(result.status, 0);
  assert.match(validationErrors(result), /status_transitional_canonical references missing final canonical option: canonical_qeb/);
  assert.match(validationErrors(result), /status_transitional_presentation references missing final presentation: pres_qeb_wheels_choice/);
});

test("final canonical status rejects display_only as business status and conflicting same-priority winners", () => {
  const displayOnlyPackage = tempPackage();
  const displayOnlyRows = j6aRows();
  displayOnlyRows.statusRows[0].status = "display_only";
  writeJ6aFixture(displayOnlyPackage, displayOnlyRows);
  const displayOnlyResult = runLegacyFragment(displayOnlyPackage);
  assert.notEqual(displayOnlyResult.status, 0);
  assert.match(validationErrors(displayOnlyResult), /cannot use display_only as a business status/);

  const conflictPackage = tempPackage();
  const conflictRows = j6aRows();
  conflictRows.statusRows.push({
    ...conflictRows.statusRows[0],
    status_rule_id: "status_j6a_choice_default_conflict",
    status: "optional",
    status_label: "Available",
  });
  writeJ6aFixture(conflictPackage, conflictRows);
  const conflictResult = runLegacyFragment(conflictPackage);
  assert.notEqual(conflictResult.status, 0);
  assert.match(validationErrors(conflictResult), /status_j6a_choice_default and status_j6a_choice_default_conflict have conflicting same-priority statuses/);
});

test("final canonical presentations reject ambiguous duplicate-RPO auto-collapse", () => {
  const packageDir = tempPackage();
  const rows = j6aRows();
  rows.presentationRows.push({
    ...rows.presentationRows[0],
    presentation_id: "pres_j6a_second_customer_choice",
    legacy_option_id: "opt_j6a_003",
    display_order: "30",
  });
  writeJ6aFixture(packageDir, rows);

  const result = runLegacyFragment(packageDir);
  assert.notEqual(result.status, 0);
  assert.match(validationErrors(result), /would auto-collapse multiple selectable choices for RPO J6A/);
});

test("final canonical legacy option IDs cannot collide with transitional presentation output", () => {
  const packageDir = tempPackage();
  const rows = j6aRows();
  rows.presentationRows[0].legacy_option_id = "opt_qeb_001";
  writeJ6aFixture(packageDir, rows);

  const result = runLegacyFragment(packageDir);
  assert.notEqual(result.status, 0);
  assert.match(validationErrors(result), /legacy_option_id collides with existing legacy output: opt_qeb_001/);
});
