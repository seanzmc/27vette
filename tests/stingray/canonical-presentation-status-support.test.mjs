import assert from "node:assert/strict";
import { execFileSync, spawnSync } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import test from "node:test";

const PYTHON = ".venv/bin/python";
const SCRIPT = "scripts/stingray_csv_first_slice.py";
const PACKAGE = "data/stingray";
const CANONICAL_FIELDS = [
  "canonical_option_id",
  "rpo",
  "label",
  "description",
  "canonical_kind",
  "active",
  "notes",
];
const PRESENTATION_FIELDS = [
  "presentation_id",
  "canonical_option_id",
  "legacy_option_id",
  "rpo_override",
  "presentation_role",
  "section_id",
  "section_name",
  "category_id",
  "category_name",
  "step_key",
  "choice_mode",
  "selection_mode",
  "selection_mode_label",
  "display_order",
  "selectable",
  "active",
  "label",
  "description",
  "source_detail_raw",
  "notes",
];
const STATUS_FIELDS = [
  "status_rule_id",
  "canonical_option_id",
  "presentation_id",
  "scope_model_year",
  "scope_body_style",
  "scope_trim_level",
  "scope_variant_id",
  "condition_set_id",
  "status",
  "status_label",
  "priority",
  "active",
  "notes",
];
const CANONICAL_BASE_PRICE_FIELDS = [
  "canonical_base_price_id",
  "price_book_id",
  "canonical_option_id",
  "presentation_id",
  "scope_condition_set_id",
  "amount_usd",
  "priority",
  "active",
  "notes",
];

function tempPackage() {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), "stingray-canonical-presentations-"));
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

function writeCanonicalTables(packageDir, { canonicalRows = [], presentationRows = [], statusRows = [], canonicalBasePriceRows = [] } = {}) {
  writeCsv(path.join(packageDir, "catalog", "canonical_options.csv"), CANONICAL_FIELDS, canonicalRows);
  writeCsv(path.join(packageDir, "ui", "option_presentations.csv"), PRESENTATION_FIELDS, presentationRows);
  writeCsv(path.join(packageDir, "logic", "option_status_rules.csv"), STATUS_FIELDS, statusRows);
  writeCsv(path.join(packageDir, "pricing", "canonical_base_prices.csv"), CANONICAL_BASE_PRICE_FIELDS, canonicalBasePriceRows);
}

function qebCanonicalRows() {
  return {
    canonicalRows: [
      {
        canonical_option_id: "canonical_qeb",
        rpo: "QEB",
        label: "5-split-spoke Pearl Nickel forged aluminum wheels",
        description: '19" x 8.5" (48.3 cm x 21.6 cm) front and 20" x 11" (50.8 cm x 27.9 cm) rear',
        canonical_kind: "customer_choice",
        active: "true",
        notes: "Temp canonical QEB fixture.",
      },
    ],
    presentationRows: [
      {
        presentation_id: "pres_qeb_wheels_choice",
        canonical_option_id: "canonical_qeb",
        legacy_option_id: "opt_qeb_001",
        rpo_override: "",
        presentation_role: "choice",
        section_id: "sec_whee_002",
        section_name: "Wheels",
        category_id: "cat_exte_001",
        category_name: "Exterior",
        step_key: "wheels",
        choice_mode: "single",
        selection_mode: "single_select_req",
        selection_mode_label: "Required single choice",
        display_order: "10",
        selectable: "True",
        active: "true",
        label: "",
        description: "",
        source_detail_raw: "",
        notes: "Temp canonical QEB customer choice.",
      },
      {
        presentation_id: "pres_qeb_standard_options",
        canonical_option_id: "canonical_qeb",
        legacy_option_id: "opt_qeb_002",
        rpo_override: "",
        presentation_role: "standard_options_display",
        section_id: "sec_stan_002",
        section_name: "Standard Options",
        category_id: "cat_stan_001",
        category_name: "Standard Equipment",
        step_key: "standard_equipment",
        choice_mode: "display",
        selection_mode: "display_only",
        selection_mode_label: "Display only",
        display_order: "10",
        selectable: "False",
        active: "true",
        label: "Wheels",
        description: '19" x 8.5" (48.3 cm x 21.6 cm) front and 20" x 11" (50.8 cm x 27.9 cm) rear 5-split-spoke Pearl Nickel forged aluminum',
        source_detail_raw: "",
        notes: "Temp canonical QEB Standard Options display presentation.",
      },
    ],
    statusRows: [
      {
        status_rule_id: "status_qeb_choice",
        canonical_option_id: "canonical_qeb",
        presentation_id: "pres_qeb_wheels_choice",
        scope_model_year: "",
        scope_body_style: "",
        scope_trim_level: "",
        scope_variant_id: "",
        condition_set_id: "",
        status: "standard_choice",
        status_label: "Standard",
        priority: "10",
        active: "true",
        notes: "Temp QEB choice status.",
      },
      {
        status_rule_id: "status_qeb_standard_options",
        canonical_option_id: "canonical_qeb",
        presentation_id: "pres_qeb_standard_options",
        scope_model_year: "",
        scope_body_style: "",
        scope_trim_level: "",
        scope_variant_id: "",
        condition_set_id: "",
        status: "standard_fixed",
        status_label: "Standard",
        priority: "10",
        active: "true",
        notes: "Temp QEB display status.",
      },
    ],
  };
}

test("absent and header-only canonical presentation tables preserve current output", () => {
  const absentPackage = tempPackage();
  fs.rmSync(path.join(absentPackage, "catalog", "canonical_options.csv"), { force: true });
  fs.rmSync(path.join(absentPackage, "ui", "option_presentations.csv"), { force: true });
  fs.rmSync(path.join(absentPackage, "logic", "option_status_rules.csv"), { force: true });
  fs.rmSync(path.join(absentPackage, "pricing", "canonical_base_prices.csv"), { force: true });

  const headerOnlyPackage = tempPackage();
  writeCanonicalTables(headerOnlyPackage);

  assert.deepEqual(emitLegacyFragment(headerOnlyPackage), emitLegacyFragment(absentPackage));
});

test("absent and header-only canonical base price table preserve current repo output", () => {
  const absentPackage = tempPackage();
  fs.rmSync(path.join(absentPackage, "pricing", "canonical_base_prices.csv"), { force: true });

  const headerOnlyPackage = tempPackage();
  writeCsv(path.join(headerOnlyPackage, "pricing", "canonical_base_prices.csv"), CANONICAL_BASE_PRICE_FIELDS, []);

  assert.deepEqual(emitLegacyFragment(headerOnlyPackage), emitLegacyFragment(absentPackage));
  assert.deepEqual(emitLegacyFragment(headerOnlyPackage), emitLegacyFragment(PACKAGE));
});

test("temp QEB canonical fixture emits choice and Standard Options display presentations", () => {
  const packageDir = tempPackage();
  writeCanonicalTables(packageDir, qebCanonicalRows());

  const fragment = emitLegacyFragment(packageDir);
  assert.equal(fragment.validation_errors.length, 0);

  const qebChoiceRows = fragment.choices.filter((row) => row.option_id === "opt_qeb_001");
  const qebDisplayRows = fragment.choices.filter((row) => row.option_id === "opt_qeb_002");
  assert.equal(qebChoiceRows.length, 6);
  assert.equal(qebDisplayRows.length, 6);

  assert.ok(qebChoiceRows.every((row) =>
    row.rpo === "QEB"
    && row.section_name === "Wheels"
    && row.selection_mode === "single_select_req"
    && row.selectable === "True"
    && row.status === "standard"
    && row.status_label === "Standard"
  ));
  assert.ok(qebDisplayRows.every((row) =>
    row.rpo === "QEB"
    && row.section_name === "Standard Options"
    && row.choice_mode === "display"
    && row.selection_mode === "display_only"
    && row.selectable === "False"
    && row.status === "standard"
    && row.status_label === "Standard"
  ));
});

test("canonical base price emits nonzero price for a canonical presentation choice", () => {
  const packageDir = tempPackage();
  const fixture = qebCanonicalRows();
  fixture.canonicalBasePriceRows = [
    {
      canonical_base_price_id: "cbp_qeb",
      price_book_id: "pb_2027_stingray",
      canonical_option_id: "canonical_qeb",
      presentation_id: "",
      scope_condition_set_id: "",
      amount_usd: "1234",
      priority: "10",
      active: "true",
      notes: "Temp canonical price.",
    },
  ];
  writeCanonicalTables(packageDir, fixture);

  const fragment = emitLegacyFragment(packageDir);
  assert.equal(fragment.validation_errors.length, 0);
  assert.ok(fragment.choices
    .filter((row) => row.option_id === "opt_qeb_001")
    .every((row) => row.base_price === 1234));
});

test("presentation-specific canonical base price overrides canonical option price", () => {
  const packageDir = tempPackage();
  const fixture = qebCanonicalRows();
  fixture.canonicalBasePriceRows = [
    {
      canonical_base_price_id: "cbp_qeb_canonical",
      price_book_id: "pb_2027_stingray",
      canonical_option_id: "canonical_qeb",
      presentation_id: "",
      scope_condition_set_id: "",
      amount_usd: "1234",
      priority: "99",
      active: "true",
      notes: "Temp canonical fallback price.",
    },
    {
      canonical_base_price_id: "cbp_qeb_presentation",
      price_book_id: "pb_2027_stingray",
      canonical_option_id: "",
      presentation_id: "pres_qeb_wheels_choice",
      scope_condition_set_id: "",
      amount_usd: "2222",
      priority: "1",
      active: "true",
      notes: "Temp presentation-specific price.",
    },
  ];
  writeCanonicalTables(packageDir, fixture);

  const fragment = emitLegacyFragment(packageDir);
  assert.equal(fragment.validation_errors.length, 0);
  assert.ok(fragment.choices
    .filter((row) => row.option_id === "opt_qeb_001")
    .every((row) => row.base_price === 2222));
  assert.ok(fragment.choices
    .filter((row) => row.option_id === "opt_qeb_002")
    .every((row) => row.base_price === 1234));
});

test("existing exact selectable base price keeps precedence over canonical base price", () => {
  const packageDir = tempPackage();
  const fixture = qebCanonicalRows();
  fixture.canonicalBasePriceRows = [
    {
      canonical_base_price_id: "cbp_qeb",
      price_book_id: "pb_2027_stingray",
      canonical_option_id: "canonical_qeb",
      presentation_id: "",
      scope_condition_set_id: "",
      amount_usd: "1234",
      priority: "99",
      active: "true",
      notes: "Temp canonical price.",
    },
  ];
  writeCanonicalTables(packageDir, fixture);
  const basePricePath = path.join(packageDir, "pricing", "base_prices.csv");
  const basePriceRows = fs.readFileSync(basePricePath, "utf8").trimEnd().split("\n");
  basePriceRows.push("bp_qeb_temp,pb_2027_stingray,selectable,opt_qeb_001,,42,1,true,Temp exact selectable bridge price.");
  fs.writeFileSync(basePricePath, `${basePriceRows.join("\n")}\n`);

  const fragment = emitLegacyFragment(packageDir);
  assert.equal(fragment.validation_errors.length, 0);
  assert.ok(fragment.choices
    .filter((row) => row.option_id === "opt_qeb_001")
    .every((row) => row.base_price === 42));
  assert.ok(fragment.choices
    .filter((row) => row.option_id === "opt_qeb_002")
    .every((row) => row.base_price === 1234));
});

test("presentation-specific status rules resolve by specificity and priority", () => {
  const packageDir = tempPackage();
  const fixture = qebCanonicalRows();
  fixture.statusRows.push({
    status_rule_id: "status_qeb_choice_1lt_c07_unavailable",
    canonical_option_id: "canonical_qeb",
    presentation_id: "pres_qeb_wheels_choice",
    scope_model_year: "",
    scope_body_style: "",
    scope_trim_level: "",
    scope_variant_id: "1lt_c07",
    condition_set_id: "",
    status: "unavailable",
    status_label: "Not Available",
    priority: "1",
    active: "true",
    notes: "Temp specificity check.",
  });
  writeCanonicalTables(packageDir, fixture);

  const fragment = emitLegacyFragment(packageDir);
  assert.equal(fragment.validation_errors.length, 0);
  const unavailableRow = fragment.choices.find((row) => row.choice_id === "1lt_c07__opt_qeb_001");
  const standardRow = fragment.choices.find((row) => row.choice_id === "2lt_c07__opt_qeb_001");
  assert.equal(unavailableRow.status, "unavailable");
  assert.equal(standardRow.status, "standard");
});

test("duplicate canonical legacy_option_id collisions fail clearly", () => {
  const packageDir = tempPackage();
  const fixture = qebCanonicalRows();
  fixture.presentationRows[1].legacy_option_id = "opt_qeb_001";
  writeCanonicalTables(packageDir, fixture);

  const result = runLegacyFragment(packageDir);
  assert.notEqual(result.status, 0);
  assert.match(validationErrors(result), /duplicate legacy_option_id opt_qeb_001/);
});

test("canonical presentation legacy aliases cannot collide with old selectables rows", () => {
  const packageDir = tempPackage();
  const fixture = qebCanonicalRows();
  fixture.presentationRows[0].legacy_option_id = "opt_eyt_001";
  writeCanonicalTables(packageDir, fixture);

  const result = runLegacyFragment(packageDir);
  assert.notEqual(result.status, 0);
  assert.match(validationErrors(result), /legacy_option_id collides with active selectables.csv row: opt_eyt_001/);
});

test("review-required duplicate RPOs are not auto-collapsed into canonical presentations", () => {
  const packageDir = tempPackage();
  const fixture = qebCanonicalRows();
  fixture.canonicalRows[0].canonical_option_id = "canonical_ae4";
  fixture.canonicalRows[0].rpo = "AE4";
  fixture.presentationRows[0].canonical_option_id = "canonical_ae4";
  fixture.presentationRows[1].canonical_option_id = "canonical_ae4";
  fixture.statusRows[0].canonical_option_id = "canonical_ae4";
  fixture.statusRows[1].canonical_option_id = "canonical_ae4";
  writeCanonicalTables(packageDir, fixture);

  const result = runLegacyFragment(packageDir);
  assert.notEqual(result.status, 0);
  assert.match(validationErrors(result), /duplicate RPO AE4, which requires explicit review and cannot be auto-collapsed/);
});

test("missing canonical option and missing status references fail clearly", () => {
  const missingCanonicalPackage = tempPackage();
  const fixture = qebCanonicalRows();
  fixture.presentationRows[0].canonical_option_id = "canonical_missing";
  writeCanonicalTables(missingCanonicalPackage, fixture);

  const missingCanonicalResult = runLegacyFragment(missingCanonicalPackage);
  assert.notEqual(missingCanonicalResult.status, 0);
  assert.match(validationErrors(missingCanonicalResult), /references missing canonical option: canonical_missing/);

  const missingStatusPackage = tempPackage();
  const statusFixture = qebCanonicalRows();
  statusFixture.statusRows[0].presentation_id = "pres_missing";
  writeCanonicalTables(missingStatusPackage, statusFixture);

  const missingStatusResult = runLegacyFragment(missingStatusPackage);
  assert.notEqual(missingStatusResult.status, 0);
  assert.match(validationErrors(missingStatusResult), /option_status_rules status_qeb_choice references missing presentation: pres_missing/);
});

test("invalid canonical base price references fail clearly", () => {
  const missingCanonicalPackage = tempPackage();
  const missingCanonicalFixture = qebCanonicalRows();
  missingCanonicalFixture.canonicalBasePriceRows = [
    {
      canonical_base_price_id: "cbp_missing_canonical",
      price_book_id: "pb_2027_stingray",
      canonical_option_id: "canonical_missing",
      presentation_id: "",
      scope_condition_set_id: "",
      amount_usd: "123",
      priority: "10",
      active: "true",
      notes: "Temp missing canonical check.",
    },
  ];
  writeCanonicalTables(missingCanonicalPackage, missingCanonicalFixture);

  const missingCanonicalResult = runLegacyFragment(missingCanonicalPackage);
  assert.notEqual(missingCanonicalResult.status, 0);
  assert.match(validationErrors(missingCanonicalResult), /canonical_base_prices cbp_missing_canonical references missing canonical option: canonical_missing/);

  const missingPresentationPackage = tempPackage();
  const missingPresentationFixture = qebCanonicalRows();
  missingPresentationFixture.canonicalBasePriceRows = [
    {
      canonical_base_price_id: "cbp_missing_presentation",
      price_book_id: "pb_2027_stingray",
      canonical_option_id: "",
      presentation_id: "pres_missing",
      scope_condition_set_id: "",
      amount_usd: "123",
      priority: "10",
      active: "true",
      notes: "Temp missing presentation check.",
    },
  ];
  writeCanonicalTables(missingPresentationPackage, missingPresentationFixture);

  const missingPresentationResult = runLegacyFragment(missingPresentationPackage);
  assert.notEqual(missingPresentationResult.status, 0);
  assert.match(validationErrors(missingPresentationResult), /canonical_base_prices cbp_missing_presentation references missing presentation: pres_missing/);
});

test("canonical base price rows must target exactly one canonical option or presentation", () => {
  const bothPackage = tempPackage();
  const bothFixture = qebCanonicalRows();
  bothFixture.canonicalBasePriceRows = [
    {
      canonical_base_price_id: "cbp_both",
      price_book_id: "pb_2027_stingray",
      canonical_option_id: "canonical_qeb",
      presentation_id: "pres_qeb_wheels_choice",
      scope_condition_set_id: "",
      amount_usd: "123",
      priority: "10",
      active: "true",
      notes: "Temp both-targets check.",
    },
  ];
  writeCanonicalTables(bothPackage, bothFixture);

  const bothResult = runLegacyFragment(bothPackage);
  assert.notEqual(bothResult.status, 0);
  assert.match(validationErrors(bothResult), /canonical_base_prices cbp_both must reference exactly one of canonical_option_id or presentation_id/);

  const neitherPackage = tempPackage();
  const neitherFixture = qebCanonicalRows();
  neitherFixture.canonicalBasePriceRows = [
    {
      canonical_base_price_id: "cbp_neither",
      price_book_id: "pb_2027_stingray",
      canonical_option_id: "",
      presentation_id: "",
      scope_condition_set_id: "",
      amount_usd: "123",
      priority: "10",
      active: "true",
      notes: "Temp neither-target check.",
    },
  ];
  writeCanonicalTables(neitherPackage, neitherFixture);

  const neitherResult = runLegacyFragment(neitherPackage);
  assert.notEqual(neitherResult.status, 0);
  assert.match(validationErrors(neitherResult), /canonical_base_prices cbp_neither must reference exactly one of canonical_option_id or presentation_id/);
});

test("display_only is rejected as a canonical business status", () => {
  const packageDir = tempPackage();
  const fixture = qebCanonicalRows();
  fixture.statusRows[0].status = "display_only";
  writeCanonicalTables(packageDir, fixture);

  const result = runLegacyFragment(packageDir);
  assert.notEqual(result.status, 0);
  assert.match(validationErrors(result), /cannot use display_only as a business status/);
});
