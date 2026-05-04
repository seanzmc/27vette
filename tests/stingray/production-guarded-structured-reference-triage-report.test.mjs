import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import test from "node:test";

const PYTHON = ".venv/bin/python";
const OVERLAY_SCRIPT = "scripts/stingray_csv_shadow_overlay.py";

function tempPath(filename) {
  const tempDir = fs.mkdtempSync(path.join(os.tmpdir(), "stingray-guarded-ref-triage-"));
  return path.join(tempDir, filename);
}

function runReport(flag, filename) {
  const out = tempPath(filename);
  const result = spawnSync(PYTHON, [OVERLAY_SCRIPT, flag, "--out", out], {
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

function sortReferenceKey(row) {
  return [row.ref_id, row.source_kind, row.source_id, row.reference_kind, row.reference_path, row.field];
}

function compareReferences(left, right) {
  const leftKey = sortReferenceKey(left);
  const rightKey = sortReferenceKey(right);
  for (let index = 0; index < leftKey.length; index++) {
    const delta = String(leftKey[index]).localeCompare(String(rightKey[index]));
    if (delta !== 0) return delta;
  }
  return 0;
}

function compareGroups(left, right) {
  return left.guarded_ref_id.localeCompare(right.guarded_ref_id);
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
  return { out, result, output: fs.existsSync(out) ? fs.readFileSync(out, "utf8") : "" };
}

test("production guarded structured reference triage reports only guarded refs with grouped metadata", () => {
  const triage = runReport("--production-guarded-structured-reference-triage", "production-guarded-structured-reference-triage.json");
  const namespace = runReport("--structured-reference-namespace-report", "structured-reference-namespace-report.json");

  assert.equal(triage.result.status, 0, triage.result.stderr);
  assert.equal(namespace.result.status, 0, namespace.result.stderr);
  assert.equal(triage.report.schema_version, 1);
  assert.equal(triage.report.status, "allowed");
  assert.equal(triage.report.production_guarded_count, namespace.report.counts_by_namespace.production_guarded);
  assert.equal(triage.report.production_guarded_count, 43);
  assert.deepEqual(triage.report.references, [...triage.report.references].sort(compareReferences));
  assert.deepEqual(triage.report.groups, [...triage.report.groups].sort(compareGroups));

  assert.equal(triage.report.references.every((row) => row.namespace === "production_guarded"), true);
  assert.equal(triage.report.references.some((row) => row.ref_id.startsWith("3LT_")), false);
  assert.equal(triage.report.references.some((row) => row.namespace === "unresolved"), false);
  assert.equal(triage.report.references.every((row) => row.status === "allowed"), true);
  assert.equal(triage.report.references.every((row) => row.candidate_status === "cross_boundary_preserved"), true);
  assert.equal(triage.report.references.every((row) => row.notes.includes("active preserved_cross_boundary")), true);

  for (const row of triage.report.references) {
    assert.ok(row.ref_id, "row should include ref_id");
    assert.ok(row.source_kind, "row should include source_kind");
    assert.ok(row.source_id, "row should include source_id");
    assert.equal(row.reference_kind, "structured_ref");
    assert.ok(row.reference_path, "row should include reference_path");
    assert.ok(row.field, "row should include field");
  }

  assert.deepEqual(
    triage.report.groups.map((group) => ({
      guarded_ref_id: group.guarded_ref_id,
      referenced_by_count: group.referenced_by_count,
      candidate_status: group.candidate_status,
    })),
    [
      { guarded_ref_id: "opt_5vm_001", referenced_by_count: 12, candidate_status: "cross_boundary_preserved" },
      { guarded_ref_id: "opt_5w8_001", referenced_by_count: 12, candidate_status: "cross_boundary_preserved" },
      { guarded_ref_id: "opt_5zw_001", referenced_by_count: 5, candidate_status: "cross_boundary_preserved" },
      { guarded_ref_id: "opt_cf8_001", referenced_by_count: 13, candidate_status: "cross_boundary_preserved" },
      { guarded_ref_id: "opt_ryq_001", referenced_by_count: 1, candidate_status: "cross_boundary_preserved" },
    ]
  );
  for (const group of triage.report.groups) {
    assert.ok(group.source_kinds.length > 0);
    assert.ok(group.source_ids.length > 0);
    assert.ok(group.reference_kinds.length > 0);
    assert.ok(group.reference_paths.length > 0);
  }
});

test("production guarded triage mode rejects data-js output mode and leaves default overlay output alone", () => {
  const out = tempPath("guarded-triage-data-js.json");
  const invalid = spawnSync(PYTHON, [OVERLAY_SCRIPT, "--production-guarded-structured-reference-triage", "--as-data-js", "--out", out], {
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
  assert.deepEqual(Object.keys(JSON.parse(stdoutRun.stdout)).sort(), Object.keys(JSON.parse(outRun.output)).sort());
});
