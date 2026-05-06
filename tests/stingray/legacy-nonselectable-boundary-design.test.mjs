import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import fs from "node:fs";
import test from "node:test";

const PYTHON = ".venv/bin/python";
const SCRIPT = "scripts/stingray_preserved_boundary_migration_queue.py";
const REGISTRY = "data/stingray/validation/non_selectable_references.csv";
const SELECTABLES = "data/stingray/catalog/selectables.csv";
const OWNERSHIP_MANIFEST = "data/stingray/validation/projected_slice_ownership.csv";

const SUBTYPES = new Set([
  "normal_selectable_misclassified",
  "rule_only_legacy_option_id",
  "production_structured_reference",
  "non_stingray_or_cross_variant_reference",
  "display_only_or_duplicate_reference",
  "package_control_plane_reference",
  "runtime_generated_placeholder",
  "ambiguous_needs_manual_decision",
]);

const HANDLINGS = new Set([
  "project_as_normal_selectable",
  "model_as_legacy_reference",
  "model_as_structured_non_selectable",
  "keep_preserved_runtime_owned",
  "requires_schema_design",
  "requires_manual_review",
]);

const REQUIRED_ROW_FIELDS = [
  "record_type",
  "source_rpo",
  "source_option_id",
  "target_rpo",
  "target_option_id",
  "current_reason",
  "oracle_behavior",
  "source_status",
  "target_status",
  "recommended_handling",
  "recommended_next_lane",
];

const EXPECTED_REFERENCES = new Set(["5VM", "5W8", "5ZW", "CF8", "RYQ", "CFX"]);
const EXPECTED_REGISTRY_HEADERS = [
  "reference_id",
  "reference_type",
  "rpo",
  "option_id",
  "subtype",
  "production_role",
  "projection_policy",
  "compiler_policy",
  "legacy_section_id",
  "legacy_selection_mode",
  "notes",
  "active",
];

function runScript(args = []) {
  return spawnSync(PYTHON, [SCRIPT, ...args], {
    cwd: process.cwd(),
    encoding: "utf8",
    maxBuffer: 8 * 1024 * 1024,
  });
}

function parseJson(args) {
  const result = runScript(args);
  assert.equal(result.status, 0, result.stderr);
  return JSON.parse(result.stdout);
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

function registryRows() {
  assert.equal(fs.existsSync(REGISTRY), true, `${REGISTRY} should exist`);
  const source = fs.readFileSync(REGISTRY, "utf8");
  const headers = source.split(/\r?\n/, 1)[0].split(",");
  assert.deepEqual(headers, EXPECTED_REGISTRY_HEADERS);
  return parseCsv(source).filter((row) => row.active === "true");
}

function rowsForIdentifier(report, identifier) {
  return report.rows.filter((row) => row.legacy_identifiers.includes(identifier));
}

test("legacy/non-selectable design report sub-classifies every Pass 156 legacy row", () => {
  const queue = parseJson(["--json"]);
  const report = parseJson(["--legacy-nonselectable-design-json"]);
  const queueRows = queue.rows.filter((row) => row.bucket === "legacy_rule_only_or_non_selectable");

  assert.equal(report.schema_version, 1);
  assert.equal(report.status, "allowed");
  assert.equal(report.source_bucket, "legacy_rule_only_or_non_selectable");
  assert.equal(report.source_row_count, queueRows.length);
  assert.equal(report.classified_row_count, queueRows.length);
  assert.equal(report.rows.length, queueRows.length);
  assert.equal(new Set(report.rows.map((row) => row.manifest_row_id)).size, queueRows.length);
  assert.equal(
    Object.values(report.subtype_summary).reduce((total, count) => total + count, 0),
    queueRows.length
  );
  assert.equal(
    Object.values(report.recommended_handling_summary).reduce((total, count) => total + count, 0),
    queueRows.length
  );

  for (const row of report.rows) {
    for (const field of REQUIRED_ROW_FIELDS) {
      assert.ok(Object.hasOwn(row, field), `${row.manifest_row_id} missing ${field}`);
    }
    assert.equal(SUBTYPES.has(row.subtype), true, `${row.manifest_row_id} has unknown subtype ${row.subtype}`);
    assert.equal(
      HANDLINGS.has(row.recommended_handling),
      true,
      `${row.manifest_row_id} has unknown handling ${row.recommended_handling}`
    );
    assert.ok(row.recommended_next_lane, `${row.manifest_row_id} missing recommended lane`);
    assert.ok(row.should_be_normal_selectable, `${row.manifest_row_id} missing selectable decision`);
    assert.equal(row.registered_reference, true, `${row.manifest_row_id} should be registry-backed`);
    assert.ok(row.reference_type, `${row.manifest_row_id} missing reference_type`);
    assert.ok(row.projection_policy, `${row.manifest_row_id} missing projection_policy`);
    assert.ok(row.compiler_policy, `${row.manifest_row_id} missing compiler_policy`);
  }

  assert.match(report.recommended_next_lane, /^LANE H:/);
});

test("non-selectable registry covers every unique Pass 157 reference exactly once", () => {
  const report = parseJson(["--legacy-nonselectable-design-json"]);
  const rows = registryRows();
  const activeReferenceIds = new Set(rows.map((row) => row.rpo || row.option_id));
  const reportReferences = new Set(report.rows.flatMap((row) => row.legacy_identifiers));

  assert.deepEqual(reportReferences, EXPECTED_REFERENCES);
  assert.deepEqual(activeReferenceIds, EXPECTED_REFERENCES);
  assert.equal(rows.length, EXPECTED_REFERENCES.size);

  for (const row of rows) {
    assert.equal(row.projection_policy, "never_project_as_selectable");
    assert.ok(row.compiler_policy);
    assert.ok(row.production_role);
    assert.ok(row.notes);
  }
});

test("registered non-selectable references are not normal projected-owned selectables", () => {
  const rows = registryRows();
  const selectables = parseCsv(fs.readFileSync(SELECTABLES, "utf8")).filter((row) => row.active === "true");
  const projectedOwned = parseCsv(fs.readFileSync(OWNERSHIP_MANIFEST, "utf8")).filter(
    (row) => row.active === "true" && row.record_type === "selectable" && row.ownership === "projected_owned"
  );

  for (const row of rows) {
    assert.equal(
      selectables.some((selectable) => selectable.selectable_id === row.option_id || selectable.rpo === row.rpo),
      false,
      `${row.reference_id} should not be in selectables.csv`
    );
    assert.equal(
      projectedOwned.some((owned) => owned.option_id === row.option_id || owned.rpo === row.rpo),
      false,
      `${row.reference_id} should not be projected-owned as a selectable`
    );
  }
});

test("legacy/non-selectable design report explicitly groups known legacy and structured references", () => {
  const report = parseJson(["--legacy-nonselectable-design-json"]);
  const expectedIdentifiers = ["5VM", "5W8", "5ZW", "CF8", "RYQ", "CFX"];

  for (const identifier of expectedIdentifiers) {
    assert.ok(report.identifier_groups[identifier], `missing identifier group for ${identifier}`);
    assert.ok(report.identifier_groups[identifier].count > 0, `identifier group ${identifier} should have rows`);
    assert.equal(rowsForIdentifier(report, identifier).length, report.identifier_groups[identifier].count);
  }

  for (const identifier of ["5VM", "5W8", "5ZW"]) {
    assert.equal(
      rowsForIdentifier(report, identifier).every((row) => row.subtype === "rule_only_legacy_option_id"),
      true,
      `${identifier} rows should remain legacy-reference design work`
    );
  }

  for (const identifier of ["CF8", "RYQ"]) {
    assert.equal(
      rowsForIdentifier(report, identifier).every((row) => row.subtype === "production_structured_reference"),
      true,
      `${identifier} rows should be structured non-selectable design work`
    );
  }

  assert.equal(
    rowsForIdentifier(report, "CFX").every((row) => row.subtype === "display_only_or_duplicate_reference"),
    true,
    "CFX rows should be treated as display-only/duplicate reference design work"
  );
});

test("legacy/non-selectable design report prints a compact human summary", () => {
  const result = runScript(["--legacy-nonselectable-design"]);
  assert.equal(result.status, 0, result.stderr);
  assert.match(result.stdout, /Legacy\/non-selectable preserved rows: \d+/);
  assert.match(result.stdout, /rule_only_legacy_option_id:/);
  assert.match(result.stdout, /production_structured_reference:/);
  assert.match(result.stdout, /Recommended next action:/);
  assert.match(result.stdout, /record_type\s+source\s+target\s+subtype\s+handling\s+next lane\s+oracle behavior/);
});
