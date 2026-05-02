import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import fs from "node:fs";
import test from "node:test";

const PYTHON = ".venv/bin/python";
const SCRIPT = "scripts/stingray_csv_first_slice.py";

function evaluate(variantId, selectedIds) {
  const output = execFileSync(PYTHON, [SCRIPT, "--scenario-json", JSON.stringify({ variant_id: variantId, selected_ids: selectedIds })], {
    cwd: process.cwd(),
    encoding: "utf8",
  });
  return JSON.parse(output);
}

function lineById(result, selectableId) {
  return result.selected_lines.find((line) => line.selectable_id === selectableId);
}

function lineIds(result) {
  return result.selected_lines.map((line) => line.selectable_id);
}

function parseCsv(source) {
  const rows = [];
  let row = [];
  let field = "";
  let inQuotes = false;
  for (let index = 0; index < source.length; index++) {
    const char = source[index];
    const next = source[index + 1];
    if (char === '"' && inQuotes && next === '"') {
      field += '"';
      index++;
    } else if (char === '"') {
      inQuotes = !inQuotes;
    } else if (char === "," && !inQuotes) {
      row.push(field);
      field = "";
    } else if ((char === "\n" || char === "\r") && !inQuotes) {
      if (char === "\r" && next === "\n") index++;
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

function fixtureRows(name) {
  return parseCsv(fs.readFileSync(`data/stingray/validation/${name}`, "utf8"));
}

test("first-slice CSV evaluator validates package references", () => {
  const result = evaluate("1lt_c07", []);
  assert.deepEqual(result.validation_errors, []);
});

test("coupe B6P auto-adds D3V and SL9 at no charge", () => {
  const result = evaluate("1lt_c07", ["opt_b6p_001"]);

  assert.deepEqual(lineById(result, "opt_b6p_001")?.provenance, ["explicit"]);
  assert.deepEqual(lineById(result, "opt_d3v_001")?.provenance, ["auto"]);
  assert.equal(lineById(result, "opt_d3v_001")?.final_price_usd, 0);
  assert.deepEqual(lineById(result, "opt_sl9_001")?.provenance, ["auto"]);
  assert.equal(lineById(result, "opt_sl9_001")?.final_price_usd, 0);
  assert.deepEqual(result.auto_added_ids, ["opt_d3v_001", "opt_sl9_001"]);
});

test("coupe BCP auto-adds D3V and keeps the 695 base price", () => {
  const result = evaluate("1lt_c07", ["opt_bcp_001"]);

  assert.deepEqual(lineById(result, "opt_bcp_001")?.provenance, ["explicit"]);
  assert.equal(lineById(result, "opt_bcp_001")?.final_price_usd, 695);
  assert.deepEqual(lineById(result, "opt_d3v_001")?.provenance, ["auto"]);
  assert.equal(lineById(result, "opt_d3v_001")?.final_price_usd, 0);
});

test("coupe BCP with B6P gets B6P pricing and package auto-adds", () => {
  const result = evaluate("1lt_c07", ["opt_bcp_001", "opt_b6p_001"]);

  assert.equal(lineById(result, "opt_bcp_001")?.final_price_usd, 595);
  assert.deepEqual(lineById(result, "opt_bcp_001")?.matched_price_rule_ids, ["pr_engine_cover_b6p_static"]);
  assert.deepEqual(lineById(result, "opt_d3v_001")?.provenance, ["auto"]);
  assert.equal(lineById(result, "opt_d3v_001")?.final_price_usd, 0);
  assert.deepEqual(lineById(result, "opt_sl9_001")?.provenance, ["auto"]);
  assert.equal(lineById(result, "opt_sl9_001")?.final_price_usd, 0);
});

test("convertible BCP without ZZ3 reports a human-readable open requirement", () => {
  const result = evaluate("1lt_c67", ["opt_bcp_001"]);

  assert.deepEqual(lineById(result, "opt_bcp_001")?.provenance, ["explicit"]);
  assert.equal(result.open_requirements.length, 1);
  assert.equal(result.open_requirements[0].required_condition_set_id, "cs_selected_zz3");
  assert.match(result.open_requirements[0].message, /Requires ZZ3 Convertible Engine Appearance Package/);
});

test("convertible BCP with ZZ3 satisfies the ZZ3 requirement and uses current 595 pricing", () => {
  const result = evaluate("1lt_c67", ["opt_bcp_001", "opt_zz3_001"]);

  assert.deepEqual(result.open_requirements, []);
  assert.equal(lineById(result, "opt_bcp_001")?.final_price_usd, 595);
});

test("coupe BCP with BC4 reports the LS6 engine-cover exclusivity conflict", () => {
  const result = evaluate("1lt_c07", ["opt_bcp_001", "opt_bc4_001"]);

  assert.equal(result.conflicts.length, 1);
  assert.equal(result.conflicts[0].exclusive_group_id, "excl_ls6_engine_covers");
  assert.deepEqual(result.conflicts[0].member_selectable_ids, ["opt_bcp_001", "opt_bc4_001"]);
  assert.match(result.conflicts[0].message, /Choose only one LS6 engine cover/);
});

test("explicit SL9 with B6P is not duplicated and is priced as included", () => {
  const result = evaluate("1lt_c07", ["opt_sl9_001", "opt_b6p_001"]);

  assert.equal(lineIds(result).filter((id) => id === "opt_sl9_001").length, 1);
  assert.deepEqual(lineById(result, "opt_sl9_001")?.provenance, ["explicit"]);
  assert.deepEqual(lineById(result, "opt_sl9_001")?.matched_auto_add_ids, ["aa_b6p_sl9"]);
  assert.equal(lineById(result, "opt_sl9_001")?.final_price_usd, 0);
  assert.deepEqual(lineById(result, "opt_d3v_001")?.provenance, ["auto"]);
  assert.equal(lineById(result, "opt_d3v_001")?.final_price_usd, 0);
  assert.deepEqual(result.auto_added_ids, ["opt_d3v_001"]);
});

test("explicit D3V with B6P is not duplicated and is priced as included", () => {
  const result = evaluate("1lt_c07", ["opt_d3v_001", "opt_b6p_001"]);

  assert.equal(lineIds(result).filter((id) => id === "opt_d3v_001").length, 1);
  assert.deepEqual(lineById(result, "opt_d3v_001")?.provenance, ["explicit"]);
  assert.deepEqual(lineById(result, "opt_d3v_001")?.matched_auto_add_ids, ["aa_b6p_d3v"]);
  assert.equal(lineById(result, "opt_d3v_001")?.final_price_usd, 0);
  assert.deepEqual(lineById(result, "opt_sl9_001")?.provenance, ["auto"]);
  assert.equal(lineById(result, "opt_sl9_001")?.final_price_usd, 0);
  assert.deepEqual(result.auto_added_ids, ["opt_sl9_001"]);
});

test("golden first-slice scenarios are production-derived CSV fixtures", () => {
  const builds = fixtureRows("golden_builds.csv");
  const selections = fixtureRows("golden_build_selections.csv");
  const expectedLines = fixtureRows("golden_expected_lines.csv");
  const expectedRequirements = fixtureRows("golden_expected_requirements.csv");
  const expectedConflicts = fixtureRows("golden_expected_conflicts.csv");

  assert.deepEqual(builds.map((row) => row.test_id), [
    "gb_coupe_b6p",
    "gb_coupe_bcp",
    "gb_coupe_bcp_b6p",
    "gb_convertible_bcp_missing_zz3",
    "gb_convertible_bcp_with_zz3",
    "gb_exclusive_engine_covers",
    "gb_explicit_d3v_b6p",
    "gb_explicit_sl9_b6p",
  ]);

  for (const build of builds) {
    const selectedIds = selections.filter((row) => row.test_id === build.test_id).map((row) => row.selectable_id);
    const result = evaluate(build.variant_id, selectedIds);
    for (const expected of expectedLines.filter((row) => row.test_id === build.test_id)) {
      const line = lineById(result, expected.selectable_id);
      assert.ok(line, `${build.test_id} should include ${expected.selectable_id}`);
      assert.equal(line.final_price_usd, Number(expected.final_price_usd), `${build.test_id} ${expected.selectable_id} price`);
      assert.deepEqual(line.provenance, expected.provenance.split("|"), `${build.test_id} ${expected.selectable_id} provenance`);
    }
    assert.equal(result.open_requirements.length, expectedRequirements.filter((row) => row.test_id === build.test_id).length);
    assert.equal(result.conflicts.length, expectedConflicts.filter((row) => row.test_id === build.test_id).length);
  }
});

test("first-slice compiler does not hard-code RPO-specific control flow", () => {
  const source = fs.readFileSync(SCRIPT, "utf8");
  const forbiddenBranch = /\b(?:if|elif)\s+[^\n:]*\b(?:rpo|selectable_id|option)\b[^\n:]*\b(?:B6P|D3V|SL9|ZZ3|BCP|BCS|BC4|BC7|RXJ|VWD|5ZD|5ZC|RXH|opt_b6p|opt_d3v|opt_sl9|opt_zz3|opt_bcp|opt_bcs|opt_bc4|opt_bc7|opt_rxj|opt_vwd|opt_5zd|opt_5zc|opt_rxh)\b/;
  assert.equal(forbiddenBranch.test(source), false);
});
