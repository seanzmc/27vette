import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import test from "node:test";

const PYTHON = ".venv/bin/python";
const SCRIPT = "scripts/stingray_preserved_boundary_migration_queue.py";

const BUCKETS = new Set([
  "reference_selector_candidate",
  "hidden_rule_only_preserved",
  "keep_preserved_runtime_owned",
  "normal_catalog_projection_candidate",
  "needs_schema_design",
  "oracle_mismatch_or_ambiguous",
]);

const DECISIONS = new Set([
  "yes_reference_selector",
  "freeze_preserve_for_now",
  "no_keep_preserved",
  "manual_review",
  "normal_catalog_projection_needed",
]);

const REQUIRED_ROW_FIELDS = [
  "record_type",
  "source_rpo",
  "source_option_id",
  "target_rpo",
  "target_option_id",
  "oracle_behavior",
  "registered_reference_involved",
  "reference_role",
  "reference_type",
  "projection_policy",
  "compiler_policy",
  "current_preserved_reason",
  "candidate_selector_model",
  "recommended_handling",
  "bucket",
  "customer_facing_impact",
  "cutover_blocking",
  "preserved_classification",
  "freeze_status",
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

function rowsFor(report, reference) {
  return report.rows.filter((row) => row.registered_reference_involved.includes(reference));
}

test("registered reference selector preflight inspects all registered preserved rows", () => {
  const queue = parseJson(["--json"]);
  const report = parseJson(["--registered-reference-selector-preflight-json"]);
  const registeredQueueRows = queue.rows.filter((row) => row.registered_reference === true);

  assert.equal(report.schema_version, 1);
  assert.equal(report.status, "allowed");
  assert.equal(report.inspected_row_count, registeredQueueRows.length);
  assert.equal(report.inspected_row_count, 30);
  assert.equal(report.rows.length, registeredQueueRows.length);
  assert.equal(new Set(report.rows.map((row) => row.manifest_row_id)).size, registeredQueueRows.length);
  assert.equal(
    Object.values(report.bucket_summary).reduce((total, count) => total + count, 0),
    registeredQueueRows.length
  );

  for (const row of report.rows) {
    for (const field of REQUIRED_ROW_FIELDS) {
      assert.ok(Object.hasOwn(row, field), `${row.manifest_row_id} missing ${field}`);
    }
    assert.equal(BUCKETS.has(row.bucket), true, `${row.manifest_row_id} has unknown bucket ${row.bucket}`);
    assert.equal(DECISIONS.has(row.recommended_handling), true, `${row.manifest_row_id} has unknown decision`);
    assert.equal(row.projection_policy.includes("never_project_as_selectable"), true);
    assert.notEqual(row.bucket, "normal_catalog_projection_candidate");
  }

  assert.match(report.recommended_next_pass, /^No registered-reference migration recommended/);
  assert.equal(report.can_any_reference_migrate_without_customer_selectable_projection, false);
  assert.equal(report.compiler_schema_support_required, true);
});

test("registered reference selector preflight recommends per-reference handling", () => {
  const report = parseJson(["--registered-reference-selector-preflight-json"]);

  for (const reference of ["5VM", "5W8", "5ZW", "CF8", "RYQ", "CFX"]) {
    assert.ok(report.reference_summary[reference], `missing summary for ${reference}`);
    assert.equal(rowsFor(report, reference).length, report.reference_summary[reference].row_count);
  }

  for (const reference of ["5VM", "5W8", "5ZW"]) {
    assert.equal(report.reference_summary[reference].recommended_handling, "freeze_preserve_for_now");
    assert.equal(report.reference_summary[reference].candidate_selector_model, "preserve_hidden_rule_only_reference");
    assert.equal(rowsFor(report, reference).every((row) => row.bucket === "hidden_rule_only_preserved"), true);
    assert.deepEqual(report.reference_summary[reference].customer_facing_impact, ["none"]);
    assert.deepEqual(report.reference_summary[reference].freeze_status, ["frozen_preserve_for_now"]);
    assert.equal(report.reference_summary[reference].compiler_schema_support_required, false);
  }

  for (const reference of ["CF8", "RYQ"]) {
    assert.equal(report.reference_summary[reference].recommended_handling, "no_keep_preserved");
    assert.equal(rowsFor(report, reference).every((row) => row.bucket === "keep_preserved_runtime_owned"), true);
  }

  assert.equal(report.reference_summary.CFX.recommended_handling, "manual_review");
  assert.equal(report.reference_summary.CFX.candidate_selector_model, "non_selectable_auto_add_target");
  assert.equal(rowsFor(report, "CFX").every((row) => row.bucket === "needs_schema_design"), true);
});

test("registered reference selector preflight prints a compact human summary", () => {
  const result = runScript(["--registered-reference-selector-preflight"]);
  assert.equal(result.status, 0, result.stderr);
  assert.match(result.stdout, /Registered-reference preserved rows inspected: 30/);
  assert.match(result.stdout, /reference_selector_candidate: 0/);
  assert.match(result.stdout, /hidden_rule_only_preserved: 15/);
  assert.match(result.stdout, /keep_preserved_runtime_owned:/);
  assert.match(result.stdout, /Recommended next pass: No registered-reference migration recommended/);
  assert.match(result.stdout, /reference\s+rows\s+decision\s+classification\s+freeze status/);
  assert.match(result.stdout, /record_type\s+source\s+target\s+reference\s+role\s+bucket\s+classification\s+freeze status/);
  assert.match(result.stdout, /5VM\s+8\s+freeze_preserve_for_now/);
  assert.match(result.stdout, /frozen_preserve_for_now/);
});
