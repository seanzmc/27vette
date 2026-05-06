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
const TRANSITIONAL_BASE_PRICE_FIELDS = [
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
const FINAL_PRICE_BOOK_FIELDS = [
  "price_book_id",
  "model_year",
  "model_key",
  "currency",
  "active",
  "notes",
];
const FINAL_CANONICAL_BASE_PRICE_FIELDS = [
  "canonical_base_price_id",
  "price_book_id",
  "canonical_option_id",
  "presentation_id",
  "context_scope_id",
  "amount_usd",
  "priority",
  "active",
  "notes",
];

function tempPackage() {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), "stingray-final-canonical-pricing-"));
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

function writeCanonicalPresentationTables(packageDir, { canonicalRows = [], presentationRows = [], statusRows = [], transitionalBasePriceRows = [] } = {}) {
  writeCsv(path.join(packageDir, "catalog", "canonical_options.csv"), CANONICAL_FIELDS, canonicalRows);
  writeCsv(path.join(packageDir, "ui", "option_presentations.csv"), PRESENTATION_FIELDS, presentationRows);
  writeCsv(path.join(packageDir, "logic", "option_status_rules.csv"), STATUS_FIELDS, statusRows);
  writeCsv(path.join(packageDir, "pricing", "canonical_base_prices.csv"), TRANSITIONAL_BASE_PRICE_FIELDS, transitionalBasePriceRows);
}

function writeFinalPricingTables(packageDir, {
  variantRows = finalVariantRows(),
  contextScopeRows = [],
  priceBookRows = finalPriceBookRows(),
  canonicalBasePriceRows = [],
  canonicalBasePriceFields = FINAL_CANONICAL_BASE_PRICE_FIELDS,
} = {}) {
  writeCsv(path.join(packageDir, "canonical", "status", "variants.csv"), FINAL_VARIANT_FIELDS, variantRows);
  writeCsv(path.join(packageDir, "canonical", "status", "context_scopes.csv"), FINAL_CONTEXT_SCOPE_FIELDS, contextScopeRows);
  writeCsv(path.join(packageDir, "canonical", "pricing", "price_books.csv"), FINAL_PRICE_BOOK_FIELDS, priceBookRows);
  writeCsv(path.join(packageDir, "canonical", "pricing", "canonical_base_prices.csv"), canonicalBasePriceFields, canonicalBasePriceRows);
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

function finalPriceBookRows() {
  return [
    {
      price_book_id: "cpb_2027_stingray",
      model_year: "2027",
      model_key: "stingray",
      currency: "USD",
      active: "true",
      notes: "Temp final canonical price book.",
    },
  ];
}

function finalCanonicalPrice(row) {
  return {
    canonical_base_price_id: row.canonical_base_price_id,
    price_book_id: row.price_book_id ?? "cpb_2027_stingray",
    canonical_option_id: row.canonical_option_id ?? "canonical_qeb",
    presentation_id: row.presentation_id ?? "",
    context_scope_id: row.context_scope_id ?? "",
    amount_usd: row.amount_usd,
    priority: row.priority ?? "10",
    active: row.active ?? "true",
    notes: row.notes ?? "Temp final canonical price.",
  };
}

function setupQebPackage() {
  const packageDir = tempPackage();
  writeCanonicalPresentationTables(packageDir, qebCanonicalRows());
  return packageDir;
}

test("absent and header-only final canonical pricing/context tables preserve current output", () => {
  const absentPackage = tempPackage();
  fs.rmSync(path.join(absentPackage, "canonical", "status"), { recursive: true, force: true });
  fs.rmSync(path.join(absentPackage, "canonical", "pricing"), { recursive: true, force: true });

  const headerOnlyPackage = tempPackage();
  writeFinalPricingTables(headerOnlyPackage, {
    variantRows: [],
    contextScopeRows: [],
    priceBookRows: [],
    canonicalBasePriceRows: [],
  });

  assert.deepEqual(emitLegacyFragment(headerOnlyPackage), emitLegacyFragment(absentPackage));
  assert.deepEqual(emitLegacyFragment(headerOnlyPackage), emitLegacyFragment(PACKAGE));
});

test("temp final namespace canonical base price emits nonzero price", () => {
  const packageDir = setupQebPackage();
  writeFinalPricingTables(packageDir, {
    canonicalBasePriceRows: [
      finalCanonicalPrice({ canonical_base_price_id: "fcbp_qeb_default", amount_usd: "1357" }),
    ],
  });

  const fragment = emitLegacyFragment(packageDir);
  assert.equal(fragment.validation_errors.length, 0);
  assert.ok(fragment.choices
    .filter((row) => row.option_id === "opt_qeb_001")
    .every((row) => row.base_price === 1357));
});

test("final presentation price overrides final canonical option price", () => {
  const packageDir = setupQebPackage();
  writeFinalPricingTables(packageDir, {
    canonicalBasePriceRows: [
      finalCanonicalPrice({ canonical_base_price_id: "fcbp_qeb_canonical", amount_usd: "1234", priority: "99" }),
      finalCanonicalPrice({
        canonical_base_price_id: "fcbp_qeb_presentation",
        canonical_option_id: "",
        presentation_id: "pres_qeb_wheels_choice",
        amount_usd: "2222",
        priority: "1",
      }),
    ],
  });

  const fragment = emitLegacyFragment(packageDir);
  assert.equal(fragment.validation_errors.length, 0);
  assert.ok(fragment.choices
    .filter((row) => row.option_id === "opt_qeb_001")
    .every((row) => row.base_price === 2222));
  assert.ok(fragment.choices
    .filter((row) => row.option_id === "opt_qeb_002")
    .every((row) => row.base_price === 1234));
});

test("variant-specific final context price overrides model default", () => {
  const packageDir = setupQebPackage();
  writeFinalPricingTables(packageDir, {
    contextScopeRows: [
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
    ],
    canonicalBasePriceRows: [
      finalCanonicalPrice({ canonical_base_price_id: "fcbp_qeb_default", amount_usd: "1000", priority: "99" }),
      finalCanonicalPrice({
        canonical_base_price_id: "fcbp_qeb_1lt_c07",
        context_scope_id: "ctx_1lt_c07",
        amount_usd: "2000",
        priority: "1",
      }),
    ],
  });

  const fragment = emitLegacyFragment(packageDir);
  assert.equal(fragment.validation_errors.length, 0);
  assert.equal(fragment.choices.find((row) => row.choice_id === "1lt_c07__opt_qeb_001").base_price, 2000);
  assert.equal(fragment.choices.find((row) => row.choice_id === "2lt_c07__opt_qeb_001").base_price, 1000);
});

test("legacy exact selectable price still wins over final canonical price", () => {
  const packageDir = setupQebPackage();
  writeFinalPricingTables(packageDir, {
    canonicalBasePriceRows: [
      finalCanonicalPrice({ canonical_base_price_id: "fcbp_qeb_default", amount_usd: "1234" }),
    ],
  });
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

test("invalid final context references and mismatches fail clearly", () => {
  const missingContextPackage = setupQebPackage();
  writeFinalPricingTables(missingContextPackage, {
    canonicalBasePriceRows: [
      finalCanonicalPrice({
        canonical_base_price_id: "fcbp_missing_context",
        context_scope_id: "ctx_missing",
        amount_usd: "1234",
      }),
    ],
  });
  const missingContextResult = runLegacyFragment(missingContextPackage);
  assert.notEqual(missingContextResult.status, 0);
  assert.match(validationErrors(missingContextResult), /references missing context scope: ctx_missing/);

  const mismatchedContextPackage = setupQebPackage();
  writeFinalPricingTables(mismatchedContextPackage, {
    contextScopeRows: [
      {
        context_scope_id: "ctx_bad_variant_body",
        model_year: "2027",
        model_key: "stingray",
        variant_id: "1lt_c07",
        body_style: "convertible",
        trim_level: "1LT",
        priority: "10",
        active: "true",
        notes: "Temp mismatch.",
      },
    ],
  });
  const mismatchedContextResult = runLegacyFragment(mismatchedContextPackage);
  assert.notEqual(mismatchedContextResult.status, 0);
  assert.match(validationErrors(mismatchedContextResult), /context_scopes ctx_bad_variant_body body_style contradicts variant 1lt_c07/);
});

test("final canonical base price rejects transitional scope_condition_set_id column", () => {
  const packageDir = setupQebPackage();
  writeFinalPricingTables(packageDir, {
    canonicalBasePriceFields: [...FINAL_CANONICAL_BASE_PRICE_FIELDS, "scope_condition_set_id"],
    canonicalBasePriceRows: [
      {
        ...finalCanonicalPrice({ canonical_base_price_id: "fcbp_qeb_default", amount_usd: "1234" }),
        scope_condition_set_id: "cs_selected_qeb",
      },
    ],
  });

  const result = runLegacyFragment(packageDir);
  assert.notEqual(result.status, 0);
  assert.match(validationErrors(result), /canonical\/pricing\/canonical_base_prices\.csv uses unsupported columns: scope_condition_set_id/);
});

test("same-priority final canonical price conflicts fail clearly", () => {
  const packageDir = setupQebPackage();
  writeFinalPricingTables(packageDir, {
    canonicalBasePriceRows: [
      finalCanonicalPrice({ canonical_base_price_id: "fcbp_qeb_conflict_a", amount_usd: "1234", priority: "10" }),
      finalCanonicalPrice({ canonical_base_price_id: "fcbp_qeb_conflict_b", amount_usd: "5678", priority: "10" }),
    ],
  });

  const result = runLegacyFragment(packageDir);
  assert.notEqual(result.status, 0);
  assert.match(
    validationErrors(result),
    /fcbp_qeb_conflict_a and fcbp_qeb_conflict_b have conflicting same-priority prices/
  );
});

test("current transitional canonical base price behavior remains unchanged", () => {
  const packageDir = setupQebPackage();
  const fixture = qebCanonicalRows();
  fixture.transitionalBasePriceRows = [
    {
      canonical_base_price_id: "cbp_qeb_transitional",
      price_book_id: "pb_2027_stingray",
      canonical_option_id: "canonical_qeb",
      presentation_id: "",
      scope_condition_set_id: "",
      amount_usd: "2468",
      priority: "10",
      active: "true",
      notes: "Temp transitional canonical price.",
    },
  ];
  writeCanonicalPresentationTables(packageDir, fixture);
  writeFinalPricingTables(packageDir, {
    variantRows: [],
    contextScopeRows: [],
    priceBookRows: [],
    canonicalBasePriceRows: [],
  });

  const fragment = emitLegacyFragment(packageDir);
  assert.equal(fragment.validation_errors.length, 0);
  assert.ok(fragment.choices
    .filter((row) => row.option_id === "opt_qeb_001")
    .every((row) => row.base_price === 2468));
});
