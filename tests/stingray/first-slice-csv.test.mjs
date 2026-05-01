import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import test from "node:test";

const PYTHON = ".venv/bin/python";
const SCRIPT = "scripts/stingray_csv_first_slice.py";

function evaluate(variantId, selectedIds) {
  const output = execFileSync(PYTHON, [SCRIPT, "--variant-id", variantId, "--selected", selectedIds.join("|")], {
    cwd: process.cwd(),
    encoding: "utf8",
  });
  return JSON.parse(output);
}

function lineById(result, selectableId) {
  return result.lines.find((line) => line.selectable_id === selectableId);
}

function lineIds(result) {
  return result.lines.map((line) => line.selectable_id);
}

test("first-slice CSV evaluator validates package references", () => {
  const result = evaluate("1lt_c07", []);
  assert.deepEqual(result.validation_errors, []);
});

test("coupe B6P auto-adds D3V and SL9 at no charge", () => {
  const result = evaluate("1lt_c07", ["opt_b6p_001"]);

  assert.equal(lineById(result, "opt_b6p_001")?.provenance, "explicit");
  assert.equal(lineById(result, "opt_d3v_001")?.provenance, "auto");
  assert.equal(lineById(result, "opt_d3v_001")?.price_usd, 0);
  assert.equal(lineById(result, "opt_sl9_001")?.provenance, "auto");
  assert.equal(lineById(result, "opt_sl9_001")?.price_usd, 0);
});

test("coupe BCP auto-adds D3V and keeps the 695 base price", () => {
  const result = evaluate("1lt_c07", ["opt_bcp_001"]);

  assert.equal(lineById(result, "opt_bcp_001")?.provenance, "explicit");
  assert.equal(lineById(result, "opt_bcp_001")?.price_usd, 695);
  assert.equal(lineById(result, "opt_d3v_001")?.provenance, "auto");
  assert.equal(lineById(result, "opt_d3v_001")?.price_usd, 0);
});

test("coupe BCP with B6P gets B6P pricing and package auto-adds", () => {
  const result = evaluate("1lt_c07", ["opt_bcp_001", "opt_b6p_001"]);

  assert.equal(lineById(result, "opt_bcp_001")?.price_usd, 595);
  assert.equal(lineById(result, "opt_d3v_001")?.provenance, "auto");
  assert.equal(lineById(result, "opt_d3v_001")?.price_usd, 0);
  assert.equal(lineById(result, "opt_sl9_001")?.provenance, "auto");
  assert.equal(lineById(result, "opt_sl9_001")?.price_usd, 0);
});

test("convertible BCP without ZZ3 reports a human-readable open requirement", () => {
  const result = evaluate("1lt_c67", ["opt_bcp_001"]);

  assert.equal(lineById(result, "opt_bcp_001")?.provenance, "explicit");
  assert.equal(result.requirements.length, 1);
  assert.equal(result.requirements[0].required_condition_set_id, "cs_selected_zz3");
  assert.match(result.requirements[0].message, /Requires ZZ3 Convertible Engine Appearance Package/);
});

test("convertible BCP with ZZ3 satisfies the ZZ3 requirement and uses current 595 pricing", () => {
  const result = evaluate("1lt_c67", ["opt_bcp_001", "opt_zz3_001"]);

  assert.deepEqual(result.requirements, []);
  assert.equal(lineById(result, "opt_bcp_001")?.price_usd, 595);
});

test("coupe BCP with BC4 reports the LS6 engine-cover exclusivity conflict", () => {
  const result = evaluate("1lt_c07", ["opt_bcp_001", "opt_bc4_001"]);

  assert.equal(result.conflicts.length, 1);
  assert.equal(result.conflicts[0].exclusive_group_id, "excl_ls6_engine_covers");
  assert.deepEqual(result.conflicts[0].member_ids, ["opt_bcp_001", "opt_bc4_001"]);
  assert.match(result.conflicts[0].message, /Choose only one LS6 engine cover/);
});

test("explicit SL9 with B6P is not duplicated and is priced as included", () => {
  const result = evaluate("1lt_c07", ["opt_sl9_001", "opt_b6p_001"]);

  assert.equal(lineIds(result).filter((id) => id === "opt_sl9_001").length, 1);
  assert.equal(lineById(result, "opt_sl9_001")?.provenance, "explicit+auto");
  assert.equal(lineById(result, "opt_sl9_001")?.price_usd, 0);
  assert.equal(lineById(result, "opt_d3v_001")?.provenance, "auto");
  assert.equal(lineById(result, "opt_d3v_001")?.price_usd, 0);
});
