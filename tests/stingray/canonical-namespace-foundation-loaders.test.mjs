import assert from "node:assert/strict";
import { execFileSync, spawnSync } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import test from "node:test";

const PYTHON = ".venv/bin/python";
const SCRIPT = "scripts/stingray_csv_first_slice.py";
const PACKAGE = "data/stingray";

const SOURCE_DOCUMENT_FIELDS = [
  "source_document_id",
  "source_type",
  "model_year",
  "model_key",
  "vehicle_line",
  "source_vehicle_line",
  "source_model_line",
  "source_name",
  "source_path",
  "source_checksum",
  "imported_at",
  "notes",
];
const SOURCE_ROW_FIELDS = [
  "source_row_id",
  "source_document_id",
  "source_sheet",
  "source_row_number",
  "source_order",
  "source_section_path",
  "source_order_path",
  "source_option_key",
  "raw_row_hash",
  "legacy_option_id",
  "rpo",
  "raw_label",
  "raw_description",
  "raw_section",
  "raw_category",
  "raw_step",
  "raw_price",
  "raw_status",
  "raw_selectable",
  "raw_detail",
  "raw_payload_json",
  "active",
  "notes",
];
const SOURCE_ROW_CLASSIFICATION_FIELDS = [
  "source_row_id",
  "classification",
  "canonical_option_id",
  "presentation_id",
  "control_plane_reference_id",
  "relationship_type",
  "relationship_id",
  "review_status",
  "review_reason",
  "active",
  "notes",
];
const DUPLICATE_RPO_REVIEW_FIELDS = [
  "duplicate_rpo_review_id",
  "rpo",
  "model_year",
  "model_key",
  "source_row_ids",
  "duplicate_rpo_classification",
  "decision_reason",
  "review_status",
  "reviewed_by",
  "reviewed_at",
  "active",
  "notes",
];

function tempPackage() {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), "stingray-canonical-namespace-"));
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

function writeFoundationTables(packageDir, {
  sourceDocumentFields = SOURCE_DOCUMENT_FIELDS,
  sourceRowFields = SOURCE_ROW_FIELDS,
  sourceRowClassificationFields = SOURCE_ROW_CLASSIFICATION_FIELDS,
  duplicateRpoReviewFields = DUPLICATE_RPO_REVIEW_FIELDS,
  sourceDocumentRows = [],
  sourceRows = [],
  sourceRowClassificationRows = [],
  duplicateRpoReviewRows = [],
} = {}) {
  writeCsv(path.join(packageDir, "canonical", "source", "source_documents.csv"), sourceDocumentFields, sourceDocumentRows);
  writeCsv(path.join(packageDir, "canonical", "source", "source_rows.csv"), sourceRowFields, sourceRows);
  writeCsv(path.join(packageDir, "canonical", "source", "source_row_classifications.csv"), sourceRowClassificationFields, sourceRowClassificationRows);
  writeCsv(path.join(packageDir, "canonical", "options", "duplicate_rpo_reviews.csv"), duplicateRpoReviewFields, duplicateRpoReviewRows);
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

function validFoundationRows() {
  return {
    sourceDocumentRows: [
      {
        source_document_id: "src_doc_stingray_fixture",
        source_type: "production_oracle_export",
        model_year: "2027",
        model_key: "stingray",
        vehicle_line: "corvette",
        source_vehicle_line: "Corvette",
        source_model_line: "Stingray",
        source_name: "Temp production oracle fixture",
        source_path: "tmp/oracle.json",
        source_checksum: "sha256:fixture",
        imported_at: "2026-05-06T00:00:00Z",
        notes: "Temp foundation loader fixture.",
      },
    ],
    sourceRows: [
      {
        source_row_id: "src_row_qeb_choice",
        source_document_id: "src_doc_stingray_fixture",
        source_sheet: "choices",
        source_row_number: "42",
        source_order: "10",
        source_section_path: "Exterior > Wheels",
        source_order_path: "Exterior/Wheels/10",
        source_option_key: "QEB",
        raw_row_hash: "hash_qeb_choice",
        legacy_option_id: "opt_qeb_001",
        rpo: "QEB",
        raw_label: "5-split-spoke Pearl Nickel forged aluminum wheels",
        raw_description: "Temp raw wheel description",
        raw_section: "Wheels",
        raw_category: "Exterior",
        raw_step: "wheels",
        raw_price: "0",
        raw_status: "standard",
        raw_selectable: "True",
        raw_detail: "",
        raw_payload_json: "{\"option_id\":\"opt_qeb_001\"}",
        active: "true",
        notes: "Temp raw row.",
      },
    ],
    sourceRowClassificationRows: [
      {
        source_row_id: "src_row_qeb_choice",
        classification: "customer_choice",
        canonical_option_id: "",
        presentation_id: "",
        control_plane_reference_id: "",
        relationship_type: "",
        relationship_id: "",
        review_status: "reviewed",
        review_reason: "Temp fixture classification.",
        active: "true",
        notes: "",
      },
    ],
    duplicateRpoReviewRows: [
      {
        duplicate_rpo_review_id: "dup_qeb_fixture",
        rpo: "QEB",
        model_year: "2027",
        model_key: "stingray",
        source_row_ids: "src_row_qeb_choice",
        duplicate_rpo_classification: "display_only_duplicate",
        decision_reason: "Temp fixture duplicate-RPO review.",
        review_status: "reviewed",
        reviewed_by: "test",
        reviewed_at: "2026-05-06T00:00:00Z",
        active: "true",
        notes: "",
      },
    ],
  };
}

test("absent and header-only canonical namespace foundation tables preserve output when no final rows are authored", () => {
  const absentPackage = tempPackage();
  fs.rmSync(path.join(absentPackage, "canonical"), { recursive: true, force: true });

  const headerOnlyPackage = tempPackage();
  writeFoundationTables(headerOnlyPackage);

  assert.deepEqual(emitLegacyFragment(headerOnlyPackage), emitLegacyFragment(absentPackage));
});

test("valid canonical namespace foundation rows validate without changing legacy output", () => {
  const absentPackage = tempPackage();
  fs.rmSync(path.join(absentPackage, "canonical"), { recursive: true, force: true });

  const packageDir = tempPackage();
  writeFoundationTables(packageDir, validFoundationRows());

  const fragment = emitLegacyFragment(packageDir);
  assert.equal(fragment.validation_errors.length, 0);
  assert.deepEqual(fragment, emitLegacyFragment(absentPackage));
});

test("canonical namespace foundation tables reject missing required headers", () => {
  const packageDir = tempPackage();
  writeFoundationTables(packageDir, {
    ...validFoundationRows(),
    sourceRowFields: SOURCE_ROW_FIELDS.filter((field) => field !== "raw_row_hash"),
  });

  const result = runLegacyFragment(packageDir);
  assert.notEqual(result.status, 0);
  assert.match(validationErrors(result), /canonical\/source\/source_rows\.csv uses missing columns: raw_row_hash/);
});

test("canonical namespace foundation loaders validate source and classification enums", () => {
  const packageDir = tempPackage();
  const rows = validFoundationRows();
  rows.sourceDocumentRows[0].source_type = "spreadsheet_guess";
  rows.sourceRowClassificationRows[0].classification = "maybe_customer_choice";
  rows.sourceRowClassificationRows[0].review_status = "maybe_reviewed";
  writeFoundationTables(packageDir, rows);

  const result = runLegacyFragment(packageDir);
  assert.notEqual(result.status, 0);
  assert.match(validationErrors(result), /canonical\/source\/source_documents src_doc_stingray_fixture uses unsupported source_type: spreadsheet_guess/);
  assert.match(validationErrors(result), /canonical\/source\/source_row_classifications src_row_qeb_choice uses unsupported classification: maybe_customer_choice/);
  assert.match(validationErrors(result), /canonical\/source\/source_row_classifications src_row_qeb_choice uses unsupported review_status: maybe_reviewed/);
});

test("duplicate RPO review loader rejects missing RPO and invalid classification", () => {
  const packageDir = tempPackage();
  const rows = validFoundationRows();
  rows.duplicateRpoReviewRows[0].rpo = "";
  rows.duplicateRpoReviewRows[0].duplicate_rpo_classification = "collapse_by_rpo";
  writeFoundationTables(packageDir, rows);

  const result = runLegacyFragment(packageDir);
  assert.notEqual(result.status, 0);
  assert.match(validationErrors(result), /canonical\/options\/duplicate_rpo_reviews dup_qeb_fixture is missing rpo/);
  assert.match(validationErrors(result), /canonical\/options\/duplicate_rpo_reviews dup_qeb_fixture uses unsupported duplicate_rpo_classification: collapse_by_rpo/);
});
