import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import test from "node:test";

const PYTHON = ".venv/bin/python";
const SCRIPT = "scripts/stingray_preserved_boundary_migration_queue.py";

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

test("non-selectable reference selector design freezes hidden 5VM/5W8/5ZW rows", () => {
  const report = parseJson(["--non-selectable-reference-selector-design-json"]);

  assert.equal(report.schema_version, 1);
  assert.equal(report.status, "allowed");
  assert.equal(report.proposed_selector_model, "Lane closed - preserve hidden rule-only references");
  assert.equal(report.candidate_row_count, 0);
  assert.equal(report.frozen_preserved_row_count, 15);
  assert.equal(report.covered_row_count, 0);
  assert.equal(report.ambiguous_row_count, 0);
  assert.equal(report.compiler_support_needed, false);
  assert.equal(report.validator_support_needed, false);
  assert.equal(report.data_migration_performed, false);
  assert.match(report.model_decision, /No remaining 5VM\/5W8\/5ZW rows are customer-facing or cutover-blocking/);

  assert.equal(report.representation_summary.subject_reference_count, 0);
  assert.equal(report.representation_summary.target_reference_condition_count, 0);
  assert.equal(report.representation_summary.both_subject_and_target_reference_count, 0);
  assert.equal(report.representation_summary.ambiguous_count, 0);

  assert.equal(report.rows.length, 0);
  assert.equal(report.frozen_rows.length, 15);
  assert.equal(new Set(report.frozen_rows.map((row) => row.manifest_row_id)).size, 15);
  for (const row of report.frozen_rows) {
    assert.equal(row.freeze_status, "frozen_preserve_for_now");
    assert.equal(
      ["hidden_production_control_plane_only", "future_schema_completeness_only"].includes(row.preserved_classification),
      true,
      `${row.manifest_row_id} has unexpected classification ${row.preserved_classification}`
    );
  }
});

test("non-selectable reference selector design states safety rules and future implementation files", () => {
  const report = parseJson(["--non-selectable-reference-selector-design-json"]);

  assert.equal(report.safety_rules.length, 7);
  assert.match(report.safety_rules[0], /must exist in non_selectable_references\.csv/);
  assert.match(report.safety_rules[1], /must not exist in selectables\.csv/);
  assert.match(report.safety_rules[6], /cannot be converted to a normal selectable/);

  assert.deepEqual(report.future_implementation_files, []);

  assert.equal(report.future_implementation_files.includes("data/stingray/catalog/selectables.csv"), false);
  assert.equal(report.future_implementation_files.includes("data/stingray/ui/selectable_display.csv"), false);
});

test("non-selectable reference selector design prints a compact human summary", () => {
  const result = runScript(["--non-selectable-reference-selector-design"]);
  assert.equal(result.status, 0, result.stderr);
  assert.match(result.stdout, /Non-selectable reference selector design candidates: 0/);
  assert.match(result.stdout, /Frozen hidden rule-only preserved rows: 15/);
  assert.match(result.stdout, /Proposed selector model: Lane closed - preserve hidden rule-only references/);
  assert.match(result.stdout, /Ambiguous rows: 0/);
  assert.match(result.stdout, /Future implementation files:\s+none/s);
  assert.match(result.stdout, /Frozen rows:/);
  assert.match(result.stdout, /frozen_preserve_for_now/);
  assert.match(result.stdout, /Safety rules:/);
  assert.match(result.stdout, /record_type\s+source\s+target\s+rule_id\s+subject_selector\s+target_condition\s+risk notes/);
});
