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
  const tempDir = fs.mkdtempSync(path.join(os.tmpdir(), "stingray-preserved-boundary-contract-"));
  return path.join(tempDir, filename);
}

function writeTempManifest(rows) {
  const file = tempPath("projected_slice_ownership.csv");
  const headers = Object.keys(rows[0]);
  fs.writeFileSync(file, `${headers.join(",")}\n${rows.map((row) => headers.map((header) => row[header] || "").join(",")).join("\n")}\n`);
  return file;
}

function runReport(args = []) {
  const out = tempPath("preserved-cross-boundary-contract-report.json");
  const result = spawnSync(PYTHON, [OVERLAY_SCRIPT, "--preserved-cross-boundary-contract-report", "--out", out, ...args], {
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

function runNamedReport(flag) {
  const out = tempPath(`${flag.replace(/^--/, "")}.json`);
  const result = spawnSync(PYTHON, [OVERLAY_SCRIPT, flag, "--out", out], {
    cwd: process.cwd(),
    encoding: "utf8",
    maxBuffer: 8 * 1024 * 1024,
  });
  return {
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
  const fields = ["ref_id", "manifest_status", "namespace", "source_kind", "source_id", "reference_kind", "reference_path", "field"];
  for (const field of fields) {
    const delta = String(left[field] || "").localeCompare(String(right[field] || ""));
    if (delta !== 0) return delta;
  }
  return 0;
}

function optionIdByRpo(data, rpo) {
  const ids = new Set(data.choices.filter((choice) => choice.rpo === rpo).map((choice) => choice.option_id));
  assert.equal(ids.size, 1, `${rpo} should map to exactly one option_id`);
  return [...ids][0];
}

test("preserved cross-boundary contract report proves guarded refs and preserved evidence agree", () => {
  const contract = runReport();
  const namespace = runNamedReport("--structured-reference-namespace-report");
  const triage = runNamedReport("--production-guarded-structured-reference-triage");

  assert.equal(contract.result.status, 0, contract.result.stderr);
  assert.equal(namespace.result.status, 0, namespace.result.stderr);
  assert.equal(triage.result.status, 0, triage.result.stderr);
  assert.equal(contract.report.schema_version, 1);
  assert.equal(contract.report.status, "allowed");
  assert.equal(contract.report.guarded_reference_count, 43);
  assert.equal(contract.report.guarded_reference_count, namespace.report.counts_by_namespace.production_guarded);
  assert.equal(contract.report.guarded_reference_count, triage.report.production_guarded_count);
  assert.equal(contract.report.matched_count, 43);
  assert.equal(contract.report.stale_preserved_count, 0);
  assert.equal(contract.report.unguarded_production_guarded_count, 0);
  assert.equal(contract.report.invalid_preserved_count, 0);
  assert.equal(contract.report.guarded_reference_count, contract.report.matched_count + contract.report.unguarded_production_guarded_count);

  assert.deepEqual(contract.report.matches, [...contract.report.matches].sort(compareRows));
  assert.deepEqual(contract.report.stale_preserved, []);
  assert.deepEqual(contract.report.unguarded_production_guarded, []);
  assert.deepEqual(contract.report.invalid_preserved, []);
  assert.equal(contract.report.matches.every((row) => row.manifest_status === "matched"), true);
  assert.equal(contract.report.matches.some((row) => row.ref_id.startsWith("3LT_")), false);
});

test("preserved cross-boundary contract report surfaces missing stale and invalid manifest evidence", () => {
  const production = loadGeneratedData();
  const rows = loadManifest();
  const interiorId = production.interiors.find((interior) => interior.interior_id.startsWith("3LT_")).interior_id;
  const b6p = optionIdByRpo(production, "B6P");
  const zz3 = optionIdByRpo(production, "ZZ3");
  const mutated = rows
    .filter((row) => !(row.ownership === "preserved_cross_boundary" && row.source_option_id === "opt_ryq_001" && row.target_rpo === "EFY"))
    .concat([
      {
        ...rows[0],
        record_type: "rule",
        group_id: "",
        source_rpo: "",
        source_option_id: "opt_ryq_001",
        target_rpo: "B6P",
        target_option_id: "",
        rpo: "",
        ownership: "preserved_cross_boundary",
        reason: "test stale guarded preserved row",
        active: "true",
      },
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
    ]);

  const reportRun = runReport(["--ownership-manifest", writeTempManifest(mutated)]);

  assert.notEqual(reportRun.result.status, 0);
  assert.match(reportRun.result.stderr, /preserved cross-boundary contract blocking findings/);
  assert.equal(reportRun.report.status, "blocking");
  assert.equal(reportRun.report.unguarded_production_guarded_count, 1);
  assert.equal(reportRun.report.stale_preserved_count, 1);
  assert.equal(reportRun.report.invalid_preserved_count, 3);
  assert.equal(reportRun.report.unguarded_production_guarded[0].ref_id, "opt_ryq_001");
  assert.deepEqual(
    reportRun.report.stale_preserved.map((row) => ({ ref_id: row.ref_id, manifest_status: row.manifest_status })),
    [{ ref_id: "opt_ryq_001", manifest_status: "stale_preserved" }]
  );
  assert.equal(reportRun.report.invalid_preserved.some((row) => row.ref_id === interiorId && row.namespace === "interior_source"), true);
  assert.equal(reportRun.report.invalid_preserved.some((row) => row.ref_id === b6p && row.namespace === "active_projected_owned_choice"), true);
  assert.equal(reportRun.report.invalid_preserved.some((row) => row.ref_id === zz3 && row.namespace === "active_projected_owned_choice"), true);
});

test("preserved cross-boundary contract report rejects data-js output mode and leaves default overlay output alone", () => {
  const out = tempPath("preserved-contract-data-js.json");
  const invalid = spawnSync(PYTHON, [OVERLAY_SCRIPT, "--preserved-cross-boundary-contract-report", "--as-data-js", "--out", out], {
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
