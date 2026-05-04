import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import test from "node:test";

const PYTHON = ".venv/bin/python";
const OVERLAY_SCRIPT = "scripts/stingray_csv_shadow_overlay.py";

function tempPath(filename) {
  const tempDir = fs.mkdtempSync(path.join(os.tmpdir(), "stingray-manifest-only-triage-"));
  return path.join(tempDir, filename);
}

function runReport(flag, args = []) {
  const out = tempPath(`${flag.replace(/^--/, "")}.json`);
  const result = spawnSync(PYTHON, [OVERLAY_SCRIPT, flag, "--out", out, ...args], {
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
  const fields = ["group_key", "pair_key", "ref_id"];
  for (const field of fields) {
    const delta = String(left[field] ?? "").localeCompare(String(right[field] ?? ""));
    if (delta !== 0) return delta;
  }
  return 0;
}

const ROW_DETAIL_FIELDS = [
  "source_label",
  "target_label",
  "source_category",
  "target_category",
  "source_section",
  "target_section",
  "source_ownership_status",
  "target_ownership_status",
  "source_projection_status",
  "target_projection_status",
  "source_exists",
  "target_exists",
];

const GROUP_DETAIL_FIELDS = [
  "source_labels",
  "target_labels",
  "source_categories",
  "target_categories",
  "source_sections",
  "target_sections",
  "source_ownership_statuses",
  "target_ownership_statuses",
  "source_projection_statuses",
  "target_projection_statuses",
];

function publicTriageRow(row) {
  return {
    manifest_row_id: row.manifest_row_id,
    ref_id: row.ref_id,
    pair_key: row.pair_key,
    group_key: row.group_key,
    source_kind: row.source_kind,
    source_id: row.source_id,
    target_kind: row.target_kind,
    target_id: row.target_id,
    manifest_status: row.manifest_status,
    ownership_status: row.ownership_status,
    candidate_status: row.candidate_status,
    notes: row.notes,
  };
}

test("manifest-only preservation triage reports exactly the census manifest-only rows", () => {
  const triage = runReport("--manifest-only-preservation-triage");
  const census = runReport("--preserved-cross-boundary-manifest-census");

  assert.equal(triage.result.status, 0, triage.result.stderr);
  assert.equal(census.result.status, 0, census.result.stderr);
  assert.equal(triage.report.schema_version, 1);
  assert.equal(triage.report.status, "allowed");
  assert.equal(triage.report.manifest_only_preservation_row_count, 83);
  assert.equal(triage.report.manifest_only_preservation_record_count, 83);
  assert.equal(triage.report.invalid_preserved_count, 0);
  assert.equal(triage.report.rows.length, triage.report.manifest_only_preservation_row_count);
  assert.equal(triage.report.group_count, 78);
  assert.equal(triage.report.single_row_group_count, 73);
  assert.equal(triage.report.multi_row_group_count, 5);
  assert.equal(triage.report.max_group_row_count, 2);
  assert.deepEqual(triage.report.group_row_count_distribution, { "1": 73, "2": 5 });

  const expectedRows = census.report.rows
    .filter((row) => row.candidate_status === "manifest_only_preservation")
    .map(publicTriageRow);
  assert.deepEqual(triage.report.rows.map(publicTriageRow), expectedRows);
  assert.deepEqual(triage.report.rows, [...triage.report.rows].sort(compareRows));
  assert.deepEqual(triage.report.groups, [...triage.report.groups].sort(compareGroups));

  assert.equal(triage.report.rows.every((row) => row.candidate_status === "manifest_only_preservation"), true);
  assert.equal(triage.report.rows.some((row) => row.candidate_status === "current_guarded_dependency"), false);
  assert.equal(triage.report.rows.some((row) => row.candidate_status === "invalid_preserved"), false);
  assert.equal(triage.report.rows.some((row) => row.ref_id?.startsWith("3LT_")), false);
  assert.equal(triage.report.rows.some((row) => row.source_kind === "unknown" || row.target_kind === "unknown"), false);
  assert.equal(
    triage.report.rows.every((row) => ROW_DETAIL_FIELDS.every((field) => Object.hasOwn(row, field))),
    true
  );
  assert.equal(triage.report.rows.every((row) => typeof row.source_exists === "boolean"), true);
  assert.equal(triage.report.rows.every((row) => typeof row.target_exists === "boolean"), true);

  const rowGroupKeys = new Set(triage.report.rows.map((row) => row.group_key));
  assert.equal(triage.report.groups.length, rowGroupKeys.size);
  assert.equal(
    triage.report.groups.reduce((total, group) => total + group.manifest_only_preservation_row_count, 0),
    triage.report.manifest_only_preservation_row_count
  );
  assert.equal(
    triage.report.groups.reduce((total, group) => total + group.manifest_only_preservation_record_count, 0),
    triage.report.manifest_only_preservation_record_count
  );
  assert.equal(triage.report.groups.every((group) => group.candidate_status === "manifest_only_preservation"), true);
  assert.equal(
    triage.report.groups.every((group) => GROUP_DETAIL_FIELDS.every((field) => Object.hasOwn(group, field))),
    true
  );
  assert.equal(
    triage.report.groups.every((group) => GROUP_DETAIL_FIELDS.every((field) => Array.isArray(group[field]))),
    true
  );
  assert.equal(
    triage.report.groups.every((group) => GROUP_DETAIL_FIELDS.every((field) => group[field].every((value) => value !== null))),
    true
  );

  const groupRowCounts = triage.report.groups.map((group) => group.manifest_only_preservation_row_count);
  const distribution = groupRowCounts.reduce((counts, rowCount) => {
    counts[String(rowCount)] = (counts[String(rowCount)] || 0) + 1;
    return counts;
  }, {});
  assert.equal(triage.report.group_count, triage.report.groups.length);
  assert.equal(
    triage.report.single_row_group_count,
    triage.report.groups.filter((group) => group.manifest_only_preservation_row_count === 1).length
  );
  assert.equal(
    triage.report.multi_row_group_count,
    triage.report.groups.filter((group) => group.manifest_only_preservation_row_count > 1).length
  );
  assert.equal(triage.report.max_group_row_count, Math.max(...groupRowCounts));
  assert.deepEqual(triage.report.group_row_count_distribution, distribution);
  assert.equal(
    Object.values(triage.report.group_row_count_distribution).reduce((total, count) => total + count, 0),
    triage.report.group_count
  );
  assert.equal(
    triage.report.groups.reduce((total, group) => total + group.manifest_only_preservation_row_count, 0),
    triage.report.manifest_only_preservation_row_count
  );
  assert.equal(triage.report.multi_row_groups.length, triage.report.multi_row_group_count);
  assert.equal(triage.report.multi_row_groups.every((group) => group.manifest_only_preservation_row_count === 2), true);
  assert.deepEqual(
    triage.report.multi_row_groups.map((group) => group.group_key),
    [
      "opt_pcx_001->opt_sfz_001",
      "opt_pcx_001->opt_sht_001",
      "opt_pcx_001->opt_sng_001",
      "opt_pdv_001->opt_sb7_001",
      "opt_pdv_001->opt_vwd_001",
    ]
  );
  assert.equal(triage.report.multi_row_groups.every((group) => group.candidate_status === "manifest_only_preservation"), true);
  assert.equal(triage.report.multi_row_groups.every((group) => !/stale|cleanup|migration/i.test(group.notes)), true);
  assert.equal(
    triage.report.multi_row_groups.every((group) => GROUP_DETAIL_FIELDS.every((field) => Object.hasOwn(group, field))),
    true
  );
});

test("manifest-only preservation triage rejects data-js mode and leaves default overlay output alone", () => {
  const out = tempPath("manifest-only-triage-data-js.json");
  const invalid = spawnSync(PYTHON, [OVERLAY_SCRIPT, "--manifest-only-preservation-triage", "--as-data-js", "--out", out], {
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
