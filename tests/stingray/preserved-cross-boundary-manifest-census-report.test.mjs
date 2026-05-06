import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import test from "node:test";

import { loadGeneratedData } from "./runtime-harness.mjs";

const PYTHON = ".venv/bin/python";
const OVERLAY_SCRIPT = "scripts/stingray_csv_shadow_overlay.py";
const OWNERSHIP_MANIFEST = "data/stingray/validation/projected_slice_ownership.csv";

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

function loadManifest() {
  return parseCsv(fs.readFileSync(OWNERSHIP_MANIFEST, "utf8"));
}

function tempPath(filename) {
  const tempDir = fs.mkdtempSync(path.join(os.tmpdir(), "stingray-preserved-boundary-census-"));
  return path.join(tempDir, filename);
}

function writeTempManifest(rows) {
  const file = tempPath("projected_slice_ownership.csv");
  const headers = Object.keys(rows[0]);
  fs.writeFileSync(file, `${headers.join(",")}\n${rows.map((row) => headers.map((header) => row[header] || "").join(",")).join("\n")}\n`);
  return file;
}

function runCensus(args = []) {
  const out = tempPath("preserved-cross-boundary-manifest-census.json");
  const result = spawnSync(PYTHON, [OVERLAY_SCRIPT, "--preserved-cross-boundary-manifest-census", "--out", out, ...args], {
    cwd: process.cwd(),
    encoding: "utf8",
    maxBuffer: 8 * 1024 * 1024,
  });
  return {
    out,
    result,
    report: fs.existsSync(out) ? JSON.parse(fs.readFileSync(out, "utf8")) : null,
  };
}

function defaultOverlayStdout() {
  return spawnSync(PYTHON, [OVERLAY_SCRIPT], {
    cwd: process.cwd(),
    encoding: "utf8",
    maxBuffer: 16 * 1024 * 1024,
  });
}

function defaultOverlayOutFile() {
  const out = tempPath("shadow-overlay.json");
  const result = spawnSync(PYTHON, [OVERLAY_SCRIPT, "--out", out], {
    cwd: process.cwd(),
    encoding: "utf8",
    maxBuffer: 16 * 1024 * 1024,
  });
  return {
    result,
    output: fs.existsSync(out) ? fs.readFileSync(out, "utf8") : "",
  };
}

function compareRows(left, right) {
  const fields = ["candidate_status", "group_key", "manifest_row_id", "ref_id", "pair_key", "source_kind", "source_id", "target_kind", "target_id"];
  for (const field of fields) {
    const delta = String(left[field] ?? "").localeCompare(String(right[field] ?? ""));
    if (delta !== 0) return delta;
  }
  return 0;
}

function compareGroups(left, right) {
  return String(left.group_key).localeCompare(String(right.group_key));
}

function optionIdByRpo(data, rpo) {
  const ids = new Set(data.choices.filter((choice) => choice.rpo === rpo).map((choice) => choice.option_id));
  assert.equal(ids.size, 1, `${rpo} should map to exactly one option_id`);
  return [...ids][0];
}

test("preserved cross-boundary manifest census reports every active row deterministically", () => {
  const run = runCensus();

  assert.equal(run.result.status, 0, run.result.stderr);
  assert.equal(run.report.schema_version, 1);
  assert.equal(run.report.status, "allowed");
  assert.equal(run.report.active_preserved_cross_boundary_count, undefined);
  assert.equal(run.report.used_by_current_guarded_structured_refs_count, undefined);
  assert.equal(run.report.not_currently_used_count, undefined);
	  assert.equal(run.report.active_preserved_cross_boundary_row_count, 52);
	  assert.equal(run.report.active_preserved_cross_boundary_record_count, 52);
  assert.equal(run.report.rows.length, run.report.active_preserved_cross_boundary_row_count);
  assert.equal(run.report.current_guarded_structured_reference_count, 33);
  assert.equal(run.report.current_guarded_manifest_row_count, 29);
  assert.equal(run.report.current_guarded_preserved_record_count, 29);
  assert.equal(run.report.current_guarded_group_membership_count, 33);
	  assert.equal(run.report.manifest_only_preservation_row_count, 23);
	  assert.equal(run.report.manifest_only_preservation_record_count, 23);
  assert.equal(run.report.invalid_preserved_count, 0);

  assert.deepEqual(run.report.rows, [...run.report.rows].sort(compareRows));
  assert.deepEqual(run.report.groups, [...run.report.groups].sort(compareGroups));
  assert.equal(run.report.rows.every((row) => /^csv_row_\d+$/.test(row.manifest_row_id)), true);

  const currentGuardedRows = run.report.rows.filter((row) => row.candidate_status === "current_guarded_dependency");
  const manifestOnlyRows = run.report.rows.filter((row) => row.candidate_status === "manifest_only_preservation");
  const invalidRows = run.report.rows.filter((row) => row.candidate_status === "invalid_preserved");
  assert.equal(currentGuardedRows.length, 29);
  assert.equal(currentGuardedRows.length, run.report.current_guarded_manifest_row_count);
  assert.equal(manifestOnlyRows.length, run.report.manifest_only_preservation_row_count);
  assert.equal(invalidRows.length, run.report.invalid_preserved_count);
  assert.equal(
    currentGuardedRows.reduce((total, row) => total + row.current_reference_count, 0),
    run.report.current_guarded_structured_reference_count
  );
  assert.equal(currentGuardedRows.every((row) => row.ref_id && row.group_key === row.ref_id), true);
  assert.equal(run.report.rows.some((row) => row.ref_id === null && row.pair_key && row.group_key === row.pair_key), true);

  const guardedIds = new Set(currentGuardedRows.map((row) => row.ref_id));
  assert.deepEqual([...guardedIds].sort(), ["opt_5vm_001", "opt_5w8_001", "opt_5zw_001", "opt_cf8_001", "opt_ryq_001"]);
  assert.equal(run.report.rows.some((row) => row.ref_id?.startsWith("3LT_") && row.candidate_status !== "invalid_preserved"), false);
  assert.equal(run.report.rows.some((row) => row.ownership_status !== "preserved_cross_boundary"), false);

  const clusterCounts = Object.fromEntries(
    run.report.groups
      .filter((group) => guardedIds.has(group.group_key))
      .map((group) => [group.group_key, group.current_guarded_structured_reference_count])
  );
  assert.deepEqual(clusterCounts, {
    opt_5vm_001: 8,
    opt_5w8_001: 8,
    opt_5zw_001: 3,
    opt_cf8_001: 13,
    opt_ryq_001: 1,
  });
  assert.equal(
    run.report.groups
      .filter((group) => guardedIds.has(group.group_key))
      .reduce((total, group) => total + group.current_guarded_group_membership_count, 0),
    run.report.current_guarded_group_membership_count
  );
});

test("preserved cross-boundary manifest census classifies invalid temp rows as blocking", () => {
  const production = loadGeneratedData();
  const rows = loadManifest();
  const interiorId = production.interiors.find((interior) => interior.interior_id.startsWith("3LT_")).interior_id;
  const b6p = optionIdByRpo(production, "B6P");
  const zz3 = optionIdByRpo(production, "ZZ3");
  const mutated = rows.concat([
    {
      ...rows[0],
      record_type: "rule",
      group_id: "",
      source_rpo: "",
      source_option_id: interiorId,
      target_rpo: "R6X",
      target_option_id: "",
      rpo: "",
      ownership: "preserved_cross_boundary",
      reason: "test invalid interior preserved row",
      active: "true",
    },
    {
      ...rows[0],
      record_type: "rule",
      group_id: "",
      source_rpo: "",
      source_option_id: b6p,
      target_rpo: "",
      target_option_id: zz3,
      rpo: "",
      ownership: "preserved_cross_boundary",
      reason: "test invalid projected-owned preserved row",
      active: "true",
    },
    {
      ...rows[0],
      record_type: "rule",
      group_id: "",
      source_rpo: "",
      source_option_id: "opt_unknown_pass106_001",
      target_rpo: "R6X",
      target_option_id: "",
      rpo: "",
      ownership: "preserved_cross_boundary",
      reason: "test invalid unknown preserved row",
      active: "true",
    },
  ]);

  const run = runCensus(["--ownership-manifest", writeTempManifest(mutated)]);

  assert.notEqual(run.result.status, 0);
  assert.match(run.result.stderr, /preserved cross-boundary manifest census blocking findings/);
  assert.equal(run.report.status, "blocking");
	  assert.equal(run.report.active_preserved_cross_boundary_row_count, 55);
	  assert.equal(run.report.active_preserved_cross_boundary_record_count, 55);
  assert.equal(run.report.invalid_preserved_count, 3);
  assert.equal(run.report.rows.filter((row) => row.candidate_status === "invalid_preserved").length, 3);
  assert.equal(run.report.rows.some((row) => row.ref_id === interiorId && row.candidate_status === "invalid_preserved"), true);
  assert.equal(run.report.rows.some((row) => row.pair_key === `${b6p}->${zz3}` && row.candidate_status === "invalid_preserved"), true);
  assert.equal(run.report.rows.some((row) => row.ref_id === "opt_unknown_pass106_001" && row.candidate_status === "invalid_preserved"), true);
});

test("preserved cross-boundary manifest census rejects data-js mode and leaves default overlay output alone", () => {
  const out = tempPath("preserved-census-data-js.json");
  const invalid = spawnSync(PYTHON, [OVERLAY_SCRIPT, "--preserved-cross-boundary-manifest-census", "--as-data-js", "--out", out], {
    cwd: process.cwd(),
    encoding: "utf8",
    maxBuffer: 8 * 1024 * 1024,
  });
  assert.notEqual(invalid.status, 0);
  assert.match(invalid.stderr, /cannot be combined with --as-data-js/);
  assert.equal(fs.existsSync(out), false);

  const stdoutRun = defaultOverlayStdout();
  const outRun = defaultOverlayOutFile();
  assert.equal(stdoutRun.status, 0, stdoutRun.stderr);
  assert.equal(outRun.result.status, 0, outRun.result.stderr);
  assert.equal(outRun.output, stdoutRun.stdout.endsWith("\n") ? stdoutRun.stdout : `${stdoutRun.stdout}\n`);
});
