import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import fs from "node:fs";
import test from "node:test";

const PYTHON = ".venv/bin/python";
const SCRIPT = "scripts/stingray_preserved_boundary_migration_queue.py";
const OWNERSHIP_MANIFEST = "data/stingray/validation/projected_slice_ownership.csv";

const BUCKETS = new Set([
  "ready_plain_exclude",
  "ready_requires",
  "ready_include_zero_auto_add",
  "catalog_unlock_needed",
  "color_support_needed",
  "z51_or_package_adjacent",
  "legacy_rule_only_or_non_selectable",
  "missing_or_unprojected_endpoint",
  "paired_price_rule_needed",
  "oracle_mismatch_or_ambiguous",
  "already_csv_owned_stale_preserved",
  "blocked_needs_design",
]);

const SAFE_BUCKETS = new Set(["ready_plain_exclude", "ready_requires", "ready_include_zero_auto_add"]);
const COLOR_RPOS = new Set(["GBA", "GKZ", "GPH", "GTR", "GBK", "G26", "G8G"]);
const Z51_PACKAGE_RPOS = new Set(["Z51", "T0A", "TVS", "FE2", "FE3", "FE4", "J55", "G96", "M1N", "QTU", "V08", "ZYC"]);
const LEGACY_REFS = new Set(["5VM", "5W8", "5ZW", "CF8", "RYQ", "CFX", "opt_5vm_001", "opt_5w8_001", "opt_5zw_001", "opt_cf8_001", "opt_ryq_001", "opt_cfx_001"]);

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

function activePreservedRows() {
  return parseCsv(fs.readFileSync(OWNERSHIP_MANIFEST, "utf8")).filter(
    (row) => row.active === "true" && row.ownership === "preserved_cross_boundary"
  );
}

function runQueue(args = []) {
  const result = spawnSync(PYTHON, [SCRIPT, ...args], {
    cwd: process.cwd(),
    encoding: "utf8",
    maxBuffer: 8 * 1024 * 1024,
  });
  return result;
}

function endpointRefs(row) {
  return [row.source_rpo, row.source_option_id, row.target_rpo, row.target_option_id].filter(Boolean);
}

function rowFor(report, recordType, source, target) {
  return report.rows.find(
    (row) =>
      row.record_type === recordType &&
      (row.source_rpo === source || row.source_option_id === source) &&
      (row.target_rpo === target || row.target_option_id === target)
  );
}

test("preserved boundary migration queue classifies every active preserved row exactly once", () => {
  const result = runQueue(["--json"]);
  assert.equal(result.status, 0, result.stderr);
  const report = JSON.parse(result.stdout);
  const activeRows = activePreservedRows();

  assert.equal(report.schema_version, 1);
  assert.equal(report.active_preserved_cross_boundary_count, activeRows.length);
  assert.equal(report.classified_row_count, activeRows.length);
  assert.equal(report.rows.length, activeRows.length);
  assert.equal(new Set(report.rows.map((row) => row.manifest_row_id)).size, activeRows.length);
  assert.equal(report.rows.every((row) => BUCKETS.has(row.bucket)), true);
  assert.equal(report.rows.every((row) => row.recommended_next_lane), true);
  assert.equal(
    Object.values(report.bucket_summary).reduce((total, count) => total + count, 0),
    activeRows.length
  );

  for (const row of report.rows.filter((candidate) => SAFE_BUCKETS.has(candidate.bucket))) {
    const refs = endpointRefs(row);
    assert.equal(refs.some((ref) => COLOR_RPOS.has(ref)), false, `${row.manifest_row_id} should not put color refs in a safe bucket`);
    assert.equal(refs.some((ref) => Z51_PACKAGE_RPOS.has(ref)), false, `${row.manifest_row_id} should not put Z51/package refs in a safe bucket`);
    assert.equal(refs.some((ref) => LEGACY_REFS.has(ref)), false, `${row.manifest_row_id} should not put legacy/non-selectable refs in a safe bucket`);
  }

  assert.notEqual(rowFor(report, "rule", "R8C", "CFX")?.bucket, "ready_plain_exclude");
  assert.equal(rowFor(report, "rule", "R8C", "CFX")?.bucket, "legacy_rule_only_or_non_selectable");
});

test("preserved boundary migration queue prints a compact human summary", () => {
  const result = runQueue();
  assert.equal(result.status, 0, result.stderr);
  assert.match(result.stdout, /Remaining active preserved_cross_boundary rows: \d+/);
  assert.match(result.stdout, /ready_plain_exclude:/);
  assert.match(result.stdout, /blocked_needs_design:/);
  assert.match(result.stdout, /Recommended next migration lane:/);
  assert.match(result.stdout, /record_type\s+source\s+target\s+bucket\s+recommended next lane\s+reason/);
});
