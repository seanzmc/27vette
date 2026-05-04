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

const ROLLUP_FIELDS = {
  source_category_rollup: "source_category",
  target_category_rollup: "target_category",
  source_section_rollup: "source_section",
  target_section_rollup: "target_section",
  source_ownership_status_rollup: "source_ownership_status",
  target_ownership_status_rollup: "target_ownership_status",
  source_projection_status_rollup: "source_projection_status",
  target_projection_status_rollup: "target_projection_status",
};

const DIRECTION_ROLLUP_FIELDS = {
  ownership_direction_rollup: ["source_ownership_status", "target_ownership_status"],
  projection_direction_rollup: ["source_projection_status", "target_projection_status"],
};

const EXPECTED_OWNERSHIP_DIRECTION_COUNTS = [
  ["production_owned->production_owned", 12, 12, 12],
  ["production_owned->projected_owned", 14, 14, 9],
  ["projected_owned->production_owned", 36, 36, 36],
  ["projected_owned->projected_owned", 21, 21, 21],
];

const EXPECTED_PROJECTION_DIRECTION_COUNTS = [
  ["not_projected->not_projected", 12, 12, 12],
  ["not_projected->projected_owned", 14, 14, 9],
  ["projected_owned->not_projected", 36, 36, 36],
  ["projected_owned->projected_owned", 21, 21, 21],
];

const EXPECTED_OWNERSHIP_PROJECTION_DIRECTION_COUNTS = [
  ["production_owned/not_projected->production_owned/not_projected", 12, 12, 12],
  ["production_owned/not_projected->projected_owned/projected_owned", 14, 14, 9],
  ["projected_owned/projected_owned->production_owned/not_projected", 36, 36, 36],
  ["projected_owned/projected_owned->projected_owned/projected_owned", 21, 21, 21],
];

const SLICE_ROLLUP_FIELDS = {
  source_category_rollup: "source_category",
  target_category_rollup: "target_category",
  source_section_rollup: "source_section",
  target_section_rollup: "target_section",
  source_label_rollup: "source_label",
  target_label_rollup: "target_label",
};

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

function normalizedRollupKeys(value) {
  const values = Array.isArray(value) ? value : [value];
  const keys = values
    .filter((item) => item !== null && item !== undefined && item !== "")
    .map((item) => String(item));
  return keys.length ? [...new Set(keys)].sort() : ["__missing__"];
}

function expectedRollup(rows, field) {
  const buckets = new Map();
  for (const row of rows) {
    for (const key of normalizedRollupKeys(row[field])) {
      if (!buckets.has(key)) {
        buckets.set(key, {
          key,
          row_count: 0,
          recordIds: new Set(),
          groupKeys: new Set(),
        });
      }
      const bucket = buckets.get(key);
      bucket.row_count += 1;
      bucket.recordIds.add(row.manifest_row_id);
      bucket.groupKeys.add(row.group_key);
    }
  }
  return [...buckets.values()]
    .map((bucket) => ({
      key: bucket.key,
      row_count: bucket.row_count,
      record_count: bucket.recordIds.size,
      group_count: bucket.groupKeys.size,
      group_keys: [...bucket.groupKeys].sort(),
    }))
    .sort((left, right) => (left.key < right.key ? -1 : left.key > right.key ? 1 : 0));
}

function expectedDirectionRollup(rows, sourceField, targetField) {
  const buckets = new Map();
  for (const row of rows) {
    const sourceKeys = normalizedRollupKeys(row[sourceField]);
    const targetKeys = normalizedRollupKeys(row[targetField]);
    for (const sourceKey of sourceKeys) {
      for (const targetKey of targetKeys) {
        const key = `${sourceKey}->${targetKey}`;
        if (!buckets.has(key)) {
          buckets.set(key, {
            key,
            source_key: sourceKey,
            target_key: targetKey,
            row_count: 0,
            recordIds: new Set(),
            groupKeys: new Set(),
          });
        }
        const bucket = buckets.get(key);
        bucket.row_count += 1;
        bucket.recordIds.add(row.manifest_row_id);
        bucket.groupKeys.add(row.group_key);
      }
    }
  }
  return [...buckets.values()]
    .map((bucket) => ({
      key: bucket.key,
      source_key: bucket.source_key,
      target_key: bucket.target_key,
      row_count: bucket.row_count,
      record_count: bucket.recordIds.size,
      group_count: bucket.groupKeys.size,
      group_keys: [...bucket.groupKeys].sort(),
    }))
    .sort((left, right) => (left.key < right.key ? -1 : left.key > right.key ? 1 : 0));
}

function expectedOwnershipProjectionDirectionRollup(rows) {
  return expectedDirectionRollup(
    rows.map((row) => ({
      ...row,
      source_ownership_projection_status: `${normalizedRollupKeys(row.source_ownership_status)[0]}/${normalizedRollupKeys(row.source_projection_status)[0]}`,
      target_ownership_projection_status: `${normalizedRollupKeys(row.target_ownership_status)[0]}/${normalizedRollupKeys(row.target_projection_status)[0]}`,
    })),
    "source_ownership_projection_status",
    "target_ownership_projection_status"
  );
}

function rollupCounts(rollup) {
  return rollup.map((item) => [item.key, item.row_count, item.record_count, item.group_count]);
}

function combinedDirectionKeyForRow(row) {
  const sourceKey = `${normalizedRollupKeys(row.source_ownership_status)[0]}/${normalizedRollupKeys(row.source_projection_status)[0]}`;
  const targetKey = `${normalizedRollupKeys(row.target_ownership_status)[0]}/${normalizedRollupKeys(row.target_projection_status)[0]}`;
  return `${sourceKey}->${targetKey}`;
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

  const reportGroupKeys = new Set(triage.report.groups.map((group) => group.group_key));
  for (const [rollupField, rowField] of Object.entries(ROLLUP_FIELDS)) {
    assert.equal(Object.hasOwn(triage.report, rollupField), true);
    assert.equal(Array.isArray(triage.report[rollupField]), true);
    assert.deepEqual(triage.report[rollupField], expectedRollup(triage.report.rows, rowField));
    assert.equal(
      triage.report[rollupField].reduce((total, item) => total + item.row_count, 0),
      triage.report.manifest_only_preservation_row_count
    );
    for (const item of triage.report[rollupField]) {
      assert.deepEqual(Object.keys(item).sort(), ["group_count", "group_keys", "key", "record_count", "row_count"]);
      assert.deepEqual(item.group_keys, [...item.group_keys].sort());
      assert.equal(item.group_count, new Set(item.group_keys).size);
      assert.equal(item.group_keys.every((groupKey) => reportGroupKeys.has(groupKey)), true);
    }
    const hasMissingRows = triage.report.rows.some((row) => normalizedRollupKeys(row[rowField]).includes("__missing__"));
    assert.equal(triage.report[rollupField].some((item) => item.key === "__missing__"), hasMissingRows);
  }

  for (const [rollupField, [sourceField, targetField]] of Object.entries(DIRECTION_ROLLUP_FIELDS)) {
    assert.equal(Object.hasOwn(triage.report, rollupField), true);
    assert.equal(Array.isArray(triage.report[rollupField]), true);
    assert.deepEqual(triage.report[rollupField], expectedDirectionRollup(triage.report.rows, sourceField, targetField));
    assert.equal(
      triage.report[rollupField].reduce((total, item) => total + item.row_count, 0),
      triage.report.manifest_only_preservation_row_count
    );
    for (const item of triage.report[rollupField]) {
      assert.deepEqual(Object.keys(item).sort(), ["group_count", "group_keys", "key", "record_count", "row_count", "source_key", "target_key"]);
      assert.match(item.key, /->/);
      assert.equal(item.key, `${item.source_key}->${item.target_key}`);
      assert.deepEqual(item.group_keys, [...item.group_keys].sort());
      assert.equal(item.group_count, new Set(item.group_keys).size);
      assert.equal(item.group_keys.every((groupKey) => reportGroupKeys.has(groupKey)), true);
    }
  }
  assert.deepEqual(rollupCounts(triage.report.ownership_direction_rollup), EXPECTED_OWNERSHIP_DIRECTION_COUNTS);
  assert.deepEqual(rollupCounts(triage.report.projection_direction_rollup), EXPECTED_PROJECTION_DIRECTION_COUNTS);

  assert.equal(Object.hasOwn(triage.report, "ownership_projection_direction_rollup"), true);
  assert.equal(Array.isArray(triage.report.ownership_projection_direction_rollup), true);
  assert.deepEqual(
    triage.report.ownership_projection_direction_rollup,
    expectedOwnershipProjectionDirectionRollup(triage.report.rows)
  );
  assert.deepEqual(
    rollupCounts(triage.report.ownership_projection_direction_rollup),
    EXPECTED_OWNERSHIP_PROJECTION_DIRECTION_COUNTS
  );
  assert.equal(
    triage.report.ownership_projection_direction_rollup.reduce((total, item) => total + item.row_count, 0),
    triage.report.manifest_only_preservation_row_count
  );

  assert.equal(Object.hasOwn(triage.report, "ownership_projection_direction_slices"), true);
  assert.equal(Array.isArray(triage.report.ownership_projection_direction_slices), true);
  assert.equal(
    triage.report.ownership_projection_direction_slices.length,
    triage.report.ownership_projection_direction_rollup.length
  );
  assert.deepEqual(
    triage.report.ownership_projection_direction_slices.map((slice) => slice.key),
    triage.report.ownership_projection_direction_rollup.map((item) => item.key)
  );
  assert.deepEqual(
    triage.report.ownership_projection_direction_slices.map((slice) => slice.key),
    [
      "production_owned/not_projected->production_owned/not_projected",
      "production_owned/not_projected->projected_owned/projected_owned",
      "projected_owned/projected_owned->production_owned/not_projected",
      "projected_owned/projected_owned->projected_owned/projected_owned",
    ]
  );
  for (const slice of triage.report.ownership_projection_direction_slices) {
    const directionRow = triage.report.ownership_projection_direction_rollup.find((item) => item.key === slice.key);
    const sliceRows = triage.report.rows.filter((row) => combinedDirectionKeyForRow(row) === slice.key);
    assert.ok(directionRow);
    assert.equal(slice.source_key, directionRow.source_key);
    assert.equal(slice.target_key, directionRow.target_key);
    assert.equal(slice.row_count, directionRow.row_count);
    assert.equal(slice.record_count, directionRow.record_count);
    assert.equal(slice.group_count, directionRow.group_count);
    assert.deepEqual(slice.group_keys, directionRow.group_keys);
    assert.equal(slice.row_count, sliceRows.length);
    assert.equal(slice.record_count, new Set(sliceRows.map((row) => row.manifest_row_id)).size);
    assert.equal(slice.group_count, new Set(sliceRows.map((row) => row.group_key)).size);
    assert.equal(slice.group_keys.length, slice.group_count);
    assert.deepEqual(slice.group_keys, [...slice.group_keys].sort());
    assert.equal(slice.group_keys.every((groupKey) => reportGroupKeys.has(groupKey)), true);
    for (const [rollupField, rowField] of Object.entries(SLICE_ROLLUP_FIELDS)) {
      assert.equal(Object.hasOwn(slice, rollupField), true);
      assert.deepEqual(slice[rollupField], expectedRollup(sliceRows, rowField));
      assert.equal(
        slice[rollupField].reduce((total, item) => total + item.row_count, 0),
        slice.row_count
      );
      for (const item of slice[rollupField]) {
        assert.deepEqual(Object.keys(item).sort(), ["group_count", "group_keys", "key", "record_count", "row_count"]);
        assert.equal(item.group_keys.every((groupKey) => slice.group_keys.includes(groupKey)), true);
      }
    }
  }
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
