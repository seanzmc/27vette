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

test("non-selectable reference selector design covers all 5VM/5W8/5ZW candidates", () => {
  const report = parseJson(["--non-selectable-reference-selector-design-json"]);

  assert.equal(report.schema_version, 1);
  assert.equal(report.status, "allowed");
  assert.equal(report.proposed_selector_model, "Option A - non_selectable_reference selector");
  assert.equal(report.candidate_row_count, 15);
  assert.equal(report.covered_row_count, 15);
  assert.equal(report.ambiguous_row_count, 0);
  assert.equal(report.compiler_support_needed, true);
  assert.equal(report.validator_support_needed, true);
  assert.equal(report.data_migration_performed, false);

  assert.equal(report.representation_summary.subject_reference_count, 15);
  assert.equal(report.representation_summary.target_reference_condition_count, 4);
  assert.equal(report.representation_summary.both_subject_and_target_reference_count, 4);
  assert.equal(report.representation_summary.ambiguous_count, 0);

  assert.equal(report.rows.length, 15);
  assert.equal(new Set(report.rows.map((row) => row.manifest_row_id)).size, 15);
  for (const row of report.rows) {
    assert.ok(row.current_preserved_row, `${row.manifest_row_id} missing preserved row`);
    assert.ok(row.oracle_behavior, `${row.manifest_row_id} missing oracle behavior`);
    assert.ok(row.proposed_dependency_rule, `${row.manifest_row_id} missing dependency rule`);
    assert.ok(row.proposed_condition_set, `${row.manifest_row_id} missing condition set`);
    assert.ok(row.proposed_condition_term, `${row.manifest_row_id} missing condition term`);
    assert.equal(row.compiler_support_needed, true);
    assert.equal(row.validator_support_needed, true);
    assert.notEqual(
      row.proposed_dependency_rule.subject_selector_type,
      "selectable_reference",
      `${row.manifest_row_id} should not invent a selectable-reference hybrid`
    );
    if (row.proposed_dependency_rule.subject_selector_id.startsWith("ref_")) {
      assert.equal(row.proposed_dependency_rule.subject_selector_type, "non_selectable_reference");
    }
    if (row.proposed_condition_term.left_ref.startsWith("ref_")) {
      assert.equal(row.proposed_condition_term.term_type, "reference_selected");
    }
  }
});

test("non-selectable reference selector design states safety rules and future implementation files", () => {
  const report = parseJson(["--non-selectable-reference-selector-design-json"]);

  assert.equal(report.safety_rules.length, 7);
  assert.match(report.safety_rules[0], /must exist in non_selectable_references\.csv/);
  assert.match(report.safety_rules[1], /must not exist in selectables\.csv/);
  assert.match(report.safety_rules[6], /cannot be converted to a normal selectable/);

  for (const file of [
    "data/stingray/logic/dependency_rules.csv",
    "data/stingray/logic/condition_sets.csv",
    "data/stingray/logic/condition_terms.csv",
    "scripts/stingray_csv_first_slice.py",
  ]) {
    assert.ok(report.future_implementation_files.includes(file), `missing future file ${file}`);
  }

  assert.equal(report.future_implementation_files.includes("data/stingray/catalog/selectables.csv"), false);
  assert.equal(report.future_implementation_files.includes("data/stingray/ui/selectable_display.csv"), false);
});

test("non-selectable reference selector design prints a compact human summary", () => {
  const result = runScript(["--non-selectable-reference-selector-design"]);
  assert.equal(result.status, 0, result.stderr);
  assert.match(result.stdout, /Non-selectable reference selector design candidates: 15/);
  assert.match(result.stdout, /Proposed selector model: Option A - non_selectable_reference selector/);
  assert.match(result.stdout, /Ambiguous rows: 0/);
  assert.match(result.stdout, /Safety rules:/);
  assert.match(result.stdout, /record_type\s+source\s+target\s+rule_id\s+subject_selector\s+target_condition\s+risk notes/);
});
