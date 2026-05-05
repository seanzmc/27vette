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

function runManifestOnlyTriageWithCsv() {
  const out = tempPath("manifest-only-preservation-triage.json");
  const csvOut = tempPath("direction-slice-rows.csv");
  const result = spawnSync(
    PYTHON,
    [OVERLAY_SCRIPT, "--manifest-only-preservation-triage", "--out", out, "--direction-slice-rows-csv-out", csvOut],
    {
      cwd: process.cwd(),
      encoding: "utf8",
      maxBuffer: 8 * 1024 * 1024,
    }
  );
  return {
    out,
    csvOut,
    result,
    report: fs.existsSync(out) ? JSON.parse(fs.readFileSync(out, "utf8")) : null,
    csv: fs.existsSync(csvOut) ? fs.readFileSync(csvOut, "utf8") : "",
  };
}

function runManifestOnlyTriageWithReviewPacket({ includeCsv = true } = {}) {
  const out = tempPath("manifest-only-preservation-triage.json");
  const csvOut = includeCsv ? tempPath("direction-slice-rows.csv") : null;
  const packetOut = tempPath("review-packet-manifest.json");
  const args = ["--manifest-only-preservation-triage", "--out", out];
  if (includeCsv) {
    args.push("--direction-slice-rows-csv-out", csvOut);
  }
  args.push("--review-packet-manifest-out", packetOut);
  const result = spawnSync(PYTHON, [OVERLAY_SCRIPT, ...args], {
    cwd: process.cwd(),
    encoding: "utf8",
    maxBuffer: 8 * 1024 * 1024,
  });
  return {
    out,
    csvOut,
    packetOut,
    result,
    report: fs.existsSync(out) ? JSON.parse(fs.readFileSync(out, "utf8")) : null,
    packet: fs.existsSync(packetOut) ? JSON.parse(fs.readFileSync(packetOut, "utf8")) : null,
    csv: csvOut && fs.existsSync(csvOut) ? fs.readFileSync(csvOut, "utf8") : "",
  };
}

function runManifestOnlyTriageWithDecisionLedger({ includeCsv = true, includePacket = true } = {}) {
  const out = tempPath("manifest-only-preservation-triage.json");
  const csvOut = includeCsv ? tempPath("direction-slice-rows.csv") : null;
  const packetOut = includePacket ? tempPath("review-packet-manifest.json") : null;
  const ledgerOut = tempPath("decision-ledger.csv");
  const args = ["--manifest-only-preservation-triage", "--out", out];
  if (includeCsv) {
    args.push("--direction-slice-rows-csv-out", csvOut);
  }
  if (includePacket) {
    args.push("--review-packet-manifest-out", packetOut);
  }
  args.push("--decision-ledger-csv-out", ledgerOut);
  const result = spawnSync(PYTHON, [OVERLAY_SCRIPT, ...args], {
    cwd: process.cwd(),
    encoding: "utf8",
    maxBuffer: 8 * 1024 * 1024,
  });
  return {
    out,
    csvOut,
    packetOut,
    ledgerOut,
    result,
    report: fs.existsSync(out) ? JSON.parse(fs.readFileSync(out, "utf8")) : null,
    packet: packetOut && fs.existsSync(packetOut) ? JSON.parse(fs.readFileSync(packetOut, "utf8")) : null,
    csv: csvOut && fs.existsSync(csvOut) ? fs.readFileSync(csvOut, "utf8") : "",
    ledger: fs.existsSync(ledgerOut) ? fs.readFileSync(ledgerOut, "utf8") : "",
  };
}

function runDecisionLedgerValidation(ledgerPath, extraArgs = []) {
  const out = tempPath("manifest-only-preservation-triage.json");
  const validationOut = tempPath("decision-ledger-validation-report.json");
  const summaryOut = extraArgs.includes("--decision-ledger-validation-summary-out")
    ? extraArgs[extraArgs.indexOf("--decision-ledger-validation-summary-out") + 1]
    : null;
  const checkpointOut = extraArgs.includes("--manual-review-readiness-checkpoint-out")
    ? extraArgs[extraArgs.indexOf("--manual-review-readiness-checkpoint-out") + 1]
    : null;
  const result = spawnSync(
    PYTHON,
    [
      OVERLAY_SCRIPT,
      "--manifest-only-preservation-triage",
      "--out",
      out,
      "--validate-decision-ledger-csv",
      ledgerPath,
      "--decision-ledger-validation-report-out",
      validationOut,
      ...extraArgs,
    ],
    {
      cwd: process.cwd(),
      encoding: "utf8",
      maxBuffer: 8 * 1024 * 1024,
    }
  );
  return {
    out,
    validationOut,
    result,
    report: fs.existsSync(out) ? JSON.parse(fs.readFileSync(out, "utf8")) : null,
    validationReport: fs.existsSync(validationOut) ? JSON.parse(fs.readFileSync(validationOut, "utf8")) : null,
    summaryOut,
    summary: summaryOut && fs.existsSync(summaryOut) ? JSON.parse(fs.readFileSync(summaryOut, "utf8")) : null,
    checkpointOut,
    checkpoint: checkpointOut && fs.existsSync(checkpointOut) ? JSON.parse(fs.readFileSync(checkpointOut, "utf8")) : null,
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
  ["production_owned->projected_owned", 2, 2, 2],
  ["projected_owned->production_owned", 26, 26, 26],
  ["projected_owned->projected_owned", 10, 10, 10],
];

const EXPECTED_PROJECTION_DIRECTION_COUNTS = [
  ["not_projected->not_projected", 12, 12, 12],
  ["not_projected->projected_owned", 2, 2, 2],
  ["projected_owned->not_projected", 26, 26, 26],
  ["projected_owned->projected_owned", 10, 10, 10],
];

const EXPECTED_OWNERSHIP_PROJECTION_DIRECTION_COUNTS = [
  ["production_owned/not_projected->production_owned/not_projected", 12, 12, 12],
  ["production_owned/not_projected->projected_owned/projected_owned", 2, 2, 2],
  ["projected_owned/projected_owned->production_owned/not_projected", 26, 26, 26],
  ["projected_owned/projected_owned->projected_owned/projected_owned", 10, 10, 10],
];

const SLICE_ROLLUP_FIELDS = {
  source_category_rollup: "source_category",
  target_category_rollup: "target_category",
  source_section_rollup: "source_section",
  target_section_rollup: "target_section",
  source_label_rollup: "source_label",
  target_label_rollup: "target_label",
};

const DIRECTION_SLICE_ROW_FIELDS = [
  "direction_key",
  "manifest_row_id",
  "group_key",
  "ref_id",
  "pair_key",
  "source_id",
  "source_label",
  "source_category",
  "source_section",
  "source_ownership_status",
  "source_projection_status",
  "target_id",
  "target_label",
  "target_category",
  "target_section",
  "target_ownership_status",
  "target_projection_status",
  "candidate_status",
];

const DECISION_LEDGER_FIELDS = [
  "group_key",
  "direction_key",
  "manifest_only_preservation_row_count",
  "manifest_only_preservation_record_count",
  "source_ids",
  "source_labels",
  "source_categories",
  "source_sections",
  "source_ownership_statuses",
  "source_projection_statuses",
  "target_ids",
  "target_labels",
  "target_categories",
  "target_sections",
  "target_ownership_statuses",
  "target_projection_statuses",
  "manifest_row_ids",
  "review_status",
  "reviewer",
  "reviewed_at",
  "decision",
  "decision_reason",
  "followup_action",
  "notes",
];

const DECISION_LEDGER_REVIEW_FIELDS = [
  "review_status",
  "reviewer",
  "reviewed_at",
  "decision",
  "decision_reason",
  "followup_action",
  "notes",
];

const DECISION_LEDGER_CONTEXT_FIELDS = DECISION_LEDGER_FIELDS.filter(
  (field) => !DECISION_LEDGER_REVIEW_FIELDS.includes(field)
);

const LEDGER_FORBIDDEN_PACKET_KEYS = [
  "decision_ledger",
  "ledger",
  "review_status",
  "decision",
];

const LEDGER_ADVICE_TERMS = /\b(stale|cleanup|candidate|recommendation|migrate|future)\b/i;

const DECISION_LEDGER_VALIDATION_REPORT_KEYS = [
  "current_group_count",
  "duplicate_group_count",
  "duplicate_groups",
  "errors",
  "groups",
  "ledger_row_count",
  "matched_group_count",
  "missing_group_count",
  "missing_groups",
  "review_value_error_count",
  "review_value_errors",
  "schema_error_count",
  "schema_errors",
  "schema_version",
  "status",
  "unknown_group_count",
  "unknown_groups",
];

const DECISION_LEDGER_VALIDATION_GROUP_KEYS = [
  "decision",
  "decision_reason",
  "direction_key",
  "followup_action",
  "group_key",
  "matched",
  "notes",
  "review_status",
  "reviewed_at",
  "reviewer",
];

const DECISION_LEDGER_VALIDATION_ERROR_KEYS = [
  "actual",
  "error_type",
  "expected",
  "field",
  "group_key",
  "message",
];

const DECISION_LEDGER_VALIDATION_SUMMARY_KEYS = [
  "current_group_count",
  "error_counts",
  "ledger_row_count",
  "matched_group_count",
  "review_field_counts",
  "schema_version",
  "status",
];

const DECISION_LEDGER_VALIDATION_SUMMARY_ERROR_COUNT_KEYS = [
  "duplicate_group_count",
  "missing_group_count",
  "review_value_error_count",
  "schema_error_count",
  "unknown_group_count",
];

const DECISION_LEDGER_VALIDATION_SUMMARY_REVIEW_FIELDS = [
  "decision",
  "followup_action",
  "review_status",
];

const MANUAL_REVIEW_CHECKPOINT_KEYS = [
  "counts",
  "inputs",
  "not_migration_ready",
  "required_next_step",
  "schema_version",
  "status",
];

const MANUAL_REVIEW_CHECKPOINT_INPUT_KEYS = [
  "manifest_only_report_status",
  "validation_report_status",
];

const MANUAL_REVIEW_CHECKPOINT_COUNT_KEYS = [
  "current_group_count",
  "error_count",
  "group_count",
  "invalid_preserved_count",
  "ledger_row_count",
  "manifest_only_preservation_row_count",
  "matched_group_count",
];

const VALIDATION_REPORT_FORBIDDEN_KEYS = [
  "recommended_action",
  "migration_ready",
  "apply",
  "patch",
  "manifest_update",
  "cleanup",
  "future_candidate",
];

const MANUAL_REVIEW_CHECKPOINT_FORBIDDEN_TERMS =
  /\b(ready_for_migration|auto_migrate|recommended_action|apply_patch|manifest_update)\b/i;

const PACKET_TOP_LEVEL_KEYS = [
  "csv",
  "direction_counts",
  "generated_outputs",
  "multi_row_groups",
  "schema_version",
  "status",
  "summary",
];

const PACKET_GENERATED_OUTPUT_KEYS = [
  "direction_slice_rows_csv",
  "manifest_only_preservation_triage_json",
];

const PACKET_SUMMARY_KEYS = [
  "group_count",
  "invalid_preserved_count",
  "manifest_only_preservation_record_count",
  "manifest_only_preservation_row_count",
  "multi_row_group_count",
  "single_row_group_count",
];

const PACKET_DIRECTION_COUNT_KEYS = ["group_count", "key", "record_count", "row_count"];
const PACKET_MULTI_ROW_GROUP_KEYS = ["group_key", "manifest_only_preservation_row_count", "manifest_row_ids"];
const PACKET_CSV_KEYS = ["header", "row_count", "written"];
const PACKET_ADVICE_TERMS = /\b(stale|cleanup|candidate|recommendation|migrate|future)\b/i;

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

function directionKeyForGroup(group) {
  const sourceOwnershipKeys = normalizedRollupKeys(group.source_ownership_statuses);
  const sourceProjectionKeys = normalizedRollupKeys(group.source_projection_statuses);
  const targetOwnershipKeys = normalizedRollupKeys(group.target_ownership_statuses);
  const targetProjectionKeys = normalizedRollupKeys(group.target_projection_statuses);
  if (
    sourceOwnershipKeys.length === 1 &&
    sourceProjectionKeys.length === 1 &&
    targetOwnershipKeys.length === 1 &&
    targetProjectionKeys.length === 1
  ) {
    return `${sourceOwnershipKeys[0]}/${sourceProjectionKeys[0]}->${targetOwnershipKeys[0]}/${targetProjectionKeys[0]}`;
  }
  return [
    sourceOwnershipKeys.join(" | "),
    sourceProjectionKeys.join(" | "),
    targetOwnershipKeys.join(" | "),
    targetProjectionKeys.join(" | "),
  ].join("__mixed__");
}

function joinedValues(value) {
  return normalizedRollupKeys(value).filter((item) => item !== "__missing__").join(" | ");
}

function publicDirectionSliceRow(row) {
  return Object.fromEntries(DIRECTION_SLICE_ROW_FIELDS.map((field) => [field, row[field]]));
}

function compareDirectionSliceRows(left, right) {
  const fields = ["direction_key", "group_key", "manifest_row_id", "source_id", "target_id"];
  for (const field of fields) {
    const delta = String(left[field] ?? "").localeCompare(String(right[field] ?? ""));
    if (delta !== 0) return delta;
  }
  return 0;
}

function expectedDirectionSliceRows(rows) {
  return rows
    .map((row) => ({
      direction_key: combinedDirectionKeyForRow(row),
      manifest_row_id: row.manifest_row_id,
      group_key: row.group_key,
      ref_id: row.ref_id,
      pair_key: row.pair_key,
      source_id: row.source_id,
      source_label: row.source_label,
      source_category: row.source_category,
      source_section: row.source_section,
      source_ownership_status: row.source_ownership_status,
      source_projection_status: row.source_projection_status,
      target_id: row.target_id,
      target_label: row.target_label,
      target_category: row.target_category,
      target_section: row.target_section,
      target_ownership_status: row.target_ownership_status,
      target_projection_status: row.target_projection_status,
      candidate_status: row.candidate_status,
    }))
    .sort(compareDirectionSliceRows);
}

function parseCsv(text) {
  const rows = [];
  let row = [];
  let field = "";
  let quoted = false;
  for (let index = 0; index < text.length; index += 1) {
    const char = text[index];
    if (quoted) {
      if (char === "\"" && text[index + 1] === "\"") {
        field += "\"";
        index += 1;
      } else if (char === "\"") {
        quoted = false;
      } else {
        field += char;
      }
    } else if (char === "\"") {
      quoted = true;
    } else if (char === ",") {
      row.push(field);
      field = "";
    } else if (char === "\n") {
      row.push(field);
      rows.push(row);
      row = [];
      field = "";
    } else if (char !== "\r") {
      field += char;
    }
  }
  if (field || row.length) {
    row.push(field);
    rows.push(row);
  }
  return rows;
}

function formatCsvCell(value) {
  const text = value === null || value === undefined ? "" : String(value);
  return /[",\r\n]/.test(text) ? `"${text.replaceAll("\"", "\"\"")}"` : text;
}

function writeCsv(pathname, header, rows) {
  const lines = [header, ...rows].map((row) => row.map(formatCsvCell).join(","));
  fs.writeFileSync(pathname, `${lines.join("\n")}\n`, "utf8");
}

function assertNoPacketAdviceLanguage(value, path = []) {
  if (Array.isArray(value)) {
    value.forEach((item, index) => assertNoPacketAdviceLanguage(item, [...path, String(index)]));
    return;
  }
  if (value && typeof value === "object") {
    for (const [key, child] of Object.entries(value)) {
      assert.equal(PACKET_ADVICE_TERMS.test(key), false, `advice-like packet key: ${[...path, key].join(".")}`);
      if (path.length === 0 && key === "generated_outputs") {
        continue;
      }
      assertNoPacketAdviceLanguage(child, [...path, key]);
    }
    return;
  }
  if (typeof value === "string") {
    assert.equal(PACKET_ADVICE_TERMS.test(value), false, `advice-like packet value: ${path.join(".")}`);
  }
}

function assertPacketSchema(packet) {
  assert.deepEqual(Object.keys(packet), PACKET_TOP_LEVEL_KEYS);
  assert.deepEqual(Object.keys(packet.generated_outputs), PACKET_GENERATED_OUTPUT_KEYS);
  assert.deepEqual(Object.keys(packet.summary), PACKET_SUMMARY_KEYS);
  assert.deepEqual(Object.keys(packet.csv), PACKET_CSV_KEYS);
  assert.equal(packet.direction_counts.length > 0, true);
  assert.equal(Array.isArray(packet.multi_row_groups), true);
  for (const item of packet.direction_counts) {
    assert.deepEqual(Object.keys(item), PACKET_DIRECTION_COUNT_KEYS);
  }
  for (const item of packet.multi_row_groups) {
    assert.deepEqual(Object.keys(item), PACKET_MULTI_ROW_GROUP_KEYS);
  }
  assertNoPacketAdviceLanguage(packet);
}

function collectObjectKeys(value, keys = []) {
  if (Array.isArray(value)) {
    for (const item of value) {
      collectObjectKeys(item, keys);
    }
    return keys;
  }
  if (value && typeof value === "object") {
    for (const [key, child] of Object.entries(value)) {
      keys.push(key);
      collectObjectKeys(child, keys);
    }
  }
  return keys;
}

function ledgerRowsToObjects(dataRows) {
  return dataRows.map((row) => Object.fromEntries(DECISION_LEDGER_FIELDS.map((field, index) => [field, row[index]])));
}

function ledgerObjectsToCsvRows(rows, fields = DECISION_LEDGER_FIELDS) {
  return rows.map((row) => fields.map((field) => row[field] ?? ""));
}

function assertNoValidationAdviceFields(value) {
  if (Array.isArray(value)) {
    for (const item of value) {
      assertNoValidationAdviceFields(item);
    }
    return;
  }
  if (!value || typeof value !== "object") {
    return;
  }
  for (const [key, child] of Object.entries(value)) {
    assert.equal(VALIDATION_REPORT_FORBIDDEN_KEYS.includes(key), false, `validation report advice-like key: ${key}`);
    if (DECISION_LEDGER_REVIEW_FIELDS.includes(key)) {
      continue;
    }
    assertNoValidationAdviceFields(child);
  }
}

function assertValidationReportSchema(report) {
  assert.deepEqual(Object.keys(report), DECISION_LEDGER_VALIDATION_REPORT_KEYS);
  for (const field of [
    "ledger_row_count",
    "current_group_count",
    "matched_group_count",
    "missing_group_count",
    "unknown_group_count",
    "duplicate_group_count",
    "schema_error_count",
    "review_value_error_count",
  ]) {
    assert.equal(typeof report[field], "number", field);
  }
  for (const field of [
    "groups",
    "errors",
    "missing_groups",
    "unknown_groups",
    "duplicate_groups",
    "schema_errors",
    "review_value_errors",
  ]) {
    assert.equal(Array.isArray(report[field]), true, field);
  }
  for (const group of report.groups) {
    assert.deepEqual(Object.keys(group), DECISION_LEDGER_VALIDATION_GROUP_KEYS);
  }
  for (const collection of [
    report.errors,
    report.missing_groups,
    report.unknown_groups,
    report.duplicate_groups,
    report.schema_errors,
    report.review_value_errors,
  ]) {
    for (const error of collection) {
      assert.deepEqual(Object.keys(error), DECISION_LEDGER_VALIDATION_ERROR_KEYS);
      assert.equal(typeof error.error_type, "string");
      assert.equal(typeof error.message, "string");
    }
  }
  assertNoValidationAdviceFields(report);
}

function sortedCountEntries(counts) {
  return Object.entries(counts).sort(([left], [right]) => {
    if (left === "") return -1;
    if (right === "") return 1;
    return left.localeCompare(right);
  });
}

function expectedValidationSummary(validationReport) {
  const reviewFieldCounts = {};
  for (const field of DECISION_LEDGER_VALIDATION_SUMMARY_REVIEW_FIELDS) {
    const counts = new Map();
    for (const group of validationReport.groups) {
      const value = group[field] ?? "";
      counts.set(value, (counts.get(value) || 0) + 1);
    }
    reviewFieldCounts[field] = Object.fromEntries(sortedCountEntries(Object.fromEntries(counts)));
  }
  return {
    schema_version: 1,
    status: validationReport.status,
    ledger_row_count: validationReport.ledger_row_count,
    current_group_count: validationReport.current_group_count,
    matched_group_count: validationReport.matched_group_count,
    error_counts: {
      missing_group_count: validationReport.missing_group_count,
      unknown_group_count: validationReport.unknown_group_count,
      duplicate_group_count: validationReport.duplicate_group_count,
      schema_error_count: validationReport.schema_error_count,
      review_value_error_count: validationReport.review_value_error_count,
    },
    review_field_counts: reviewFieldCounts,
  };
}

function assertValidationSummarySchema(summary) {
  assert.deepEqual(Object.keys(summary), DECISION_LEDGER_VALIDATION_SUMMARY_KEYS);
  assert.deepEqual(Object.keys(summary.error_counts), DECISION_LEDGER_VALIDATION_SUMMARY_ERROR_COUNT_KEYS);
  assert.deepEqual(Object.keys(summary.review_field_counts), DECISION_LEDGER_VALIDATION_SUMMARY_REVIEW_FIELDS);
  for (const field of DECISION_LEDGER_VALIDATION_SUMMARY_REVIEW_FIELDS) {
    assert.deepEqual(Object.keys(summary.review_field_counts[field]), Object.keys(summary.review_field_counts[field]).sort((left, right) => {
      if (left === "") return -1;
      if (right === "") return 1;
      return left.localeCompare(right);
    }));
  }
  assertNoValidationAdviceFields(summary);
}

function assertValidationSummaryParity(summary, validationReport) {
  assert.equal(summary.status, validationReport.status);
  assert.equal(summary.ledger_row_count, validationReport.ledger_row_count);
  assert.equal(summary.current_group_count, validationReport.current_group_count);
  assert.equal(summary.matched_group_count, validationReport.matched_group_count);
  assert.deepEqual(summary.error_counts, {
    missing_group_count: validationReport.missing_group_count,
    unknown_group_count: validationReport.unknown_group_count,
    duplicate_group_count: validationReport.duplicate_group_count,
    schema_error_count: validationReport.schema_error_count,
    review_value_error_count: validationReport.review_value_error_count,
  });
  assert.deepEqual(summary.review_field_counts, expectedValidationSummary(validationReport).review_field_counts);
  for (const field of DECISION_LEDGER_VALIDATION_SUMMARY_REVIEW_FIELDS) {
    assert.equal(
      Object.values(summary.review_field_counts[field]).reduce((total, count) => total + count, 0),
      validationReport.groups.length,
      field
    );
    const hasBlank = validationReport.groups.some((group) => (group[field] ?? "") === "");
    assert.equal(Object.hasOwn(summary.review_field_counts[field], ""), hasBlank, field);
  }
}

function validationErrorCount(validationReport) {
  return (
    validationReport.missing_group_count +
    validationReport.unknown_group_count +
    validationReport.duplicate_group_count +
    validationReport.schema_error_count +
    validationReport.review_value_error_count
  );
}

function expectedManualReviewCheckpoint(report, validationReport) {
  const readyForManualReview =
    report.status === "allowed" &&
    report.invalid_preserved_count === 0 &&
    validationReport.status === "allowed" &&
    validationReport.matched_group_count === validationReport.current_group_count &&
    validationReport.ledger_row_count === validationReport.current_group_count;
  return {
    schema_version: 1,
    status: readyForManualReview ? "ready_for_manual_review" : "blocked",
    not_migration_ready: true,
    inputs: {
      manifest_only_report_status: report.status,
      validation_report_status: validationReport.status,
    },
    counts: {
      manifest_only_preservation_row_count: report.manifest_only_preservation_row_count,
      group_count: report.group_count,
      invalid_preserved_count: report.invalid_preserved_count,
      ledger_row_count: validationReport.ledger_row_count,
      current_group_count: validationReport.current_group_count,
      matched_group_count: validationReport.matched_group_count,
      error_count: validationErrorCount(validationReport),
    },
    required_next_step: "manual_review",
  };
}

function assertNoCheckpointForbiddenTerms(value) {
  if (Array.isArray(value)) {
    for (const item of value) {
      assertNoCheckpointForbiddenTerms(item);
    }
    return;
  }
  if (value && typeof value === "object") {
    for (const [key, child] of Object.entries(value)) {
      assert.equal(MANUAL_REVIEW_CHECKPOINT_FORBIDDEN_TERMS.test(key), false, `checkpoint forbidden key: ${key}`);
      assertNoCheckpointForbiddenTerms(child);
    }
    return;
  }
  if (typeof value === "string") {
    assert.equal(MANUAL_REVIEW_CHECKPOINT_FORBIDDEN_TERMS.test(value), false, `checkpoint forbidden value: ${value}`);
  }
}

function assertManualReviewCheckpointSchema(checkpoint) {
  assert.deepEqual(Object.keys(checkpoint), MANUAL_REVIEW_CHECKPOINT_KEYS);
  assert.deepEqual(Object.keys(checkpoint.inputs), MANUAL_REVIEW_CHECKPOINT_INPUT_KEYS);
  assert.deepEqual(Object.keys(checkpoint.counts), MANUAL_REVIEW_CHECKPOINT_COUNT_KEYS);
  assert.equal(checkpoint.schema_version, 1);
  assert.equal(["ready_for_manual_review", "blocked"].includes(checkpoint.status), true);
  assert.equal(checkpoint.not_migration_ready, true);
  assert.equal(checkpoint.required_next_step, "manual_review");
  for (const field of MANUAL_REVIEW_CHECKPOINT_COUNT_KEYS) {
    assert.equal(typeof checkpoint.counts[field], "number", field);
  }
  assertNoCheckpointForbiddenTerms(checkpoint);
}

function expectedDecisionLedgerRows(report) {
  const rowsByGroup = new Map(report.rows.map((row) => [row.group_key, []]));
  for (const row of report.rows) {
    rowsByGroup.get(row.group_key).push(row.manifest_row_id);
  }
  return report.groups
    .map((group) => ({
      group_key: group.group_key,
      direction_key: directionKeyForGroup(group),
      manifest_only_preservation_row_count: String(group.manifest_only_preservation_row_count),
      manifest_only_preservation_record_count: String(group.manifest_only_preservation_record_count),
      source_ids: joinedValues(group.source_ids),
      source_labels: joinedValues(group.source_labels),
      source_categories: joinedValues(group.source_categories),
      source_sections: joinedValues(group.source_sections),
      source_ownership_statuses: joinedValues(group.source_ownership_statuses),
      source_projection_statuses: joinedValues(group.source_projection_statuses),
      target_ids: joinedValues(group.target_ids),
      target_labels: joinedValues(group.target_labels),
      target_categories: joinedValues(group.target_categories),
      target_sections: joinedValues(group.target_sections),
      target_ownership_statuses: joinedValues(group.target_ownership_statuses),
      target_projection_statuses: joinedValues(group.target_projection_statuses),
      manifest_row_ids: [...rowsByGroup.get(group.group_key)].sort().join(" | "),
      review_status: "",
      reviewer: "",
      reviewed_at: "",
      decision: "",
      decision_reason: "",
      followup_action: "",
      notes: "",
    }))
    .sort((left, right) => {
      const directionDelta = left.direction_key.localeCompare(right.direction_key);
      return directionDelta || left.group_key.localeCompare(right.group_key);
    });
}

test("manifest-only preservation triage reports exactly the census manifest-only rows", () => {
  const triage = runReport("--manifest-only-preservation-triage");
  const census = runReport("--preserved-cross-boundary-manifest-census");

  assert.equal(triage.result.status, 0, triage.result.stderr);
  assert.equal(census.result.status, 0, census.result.stderr);
  assert.equal(triage.report.schema_version, 1);
  assert.equal(triage.report.status, "allowed");
  assert.equal(triage.report.manifest_only_preservation_row_count, 50);
  assert.equal(triage.report.manifest_only_preservation_record_count, 50);
  assert.equal(triage.report.invalid_preserved_count, 0);
  assert.equal(triage.report.rows.length, triage.report.manifest_only_preservation_row_count);
  assert.equal(triage.report.group_count, 50);
  assert.equal(triage.report.single_row_group_count, 50);
  assert.equal(triage.report.multi_row_group_count, 0);
  assert.equal(triage.report.max_group_row_count, 1);
  assert.deepEqual(triage.report.group_row_count_distribution, { "1": 50 });

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
    []
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

  assert.equal(Object.hasOwn(triage.report, "direction_slice_rows"), true);
  assert.equal(Array.isArray(triage.report.direction_slice_rows), true);
  assert.equal(triage.report.direction_slice_rows.length, triage.report.rows.length);
  assert.equal(triage.report.direction_slice_rows.length, triage.report.manifest_only_preservation_row_count);
  assert.deepEqual(
    new Set(triage.report.direction_slice_rows.map((row) => row.direction_key)),
    new Set(triage.report.ownership_projection_direction_slices.map((slice) => slice.key))
  );
  assert.deepEqual(
    triage.report.direction_slice_rows.map(publicDirectionSliceRow),
    expectedDirectionSliceRows(triage.report.rows)
  );
  assert.deepEqual(
    triage.report.direction_slice_rows,
    [...triage.report.direction_slice_rows].sort(compareDirectionSliceRows)
  );
  const directionSliceRowsByKey = new Map();
  for (const row of triage.report.direction_slice_rows) {
    assert.deepEqual(Object.keys(row).sort(), [...DIRECTION_SLICE_ROW_FIELDS].sort());
    assert.equal(row.direction_key, combinedDirectionKeyForRow(row));
    assert.equal(row.candidate_status, "manifest_only_preservation");
    directionSliceRowsByKey.set(row.direction_key, (directionSliceRowsByKey.get(row.direction_key) || 0) + 1);
    const matchingRows = triage.report.rows.filter(
      (candidate) => candidate.manifest_row_id === row.manifest_row_id && candidate.group_key === row.group_key
    );
    assert.equal(matchingRows.length, 1);
    assert.deepEqual(publicDirectionSliceRow(row), {
      ...publicDirectionSliceRow(matchingRows[0]),
      direction_key: combinedDirectionKeyForRow(matchingRows[0]),
    });
  }
  assert.deepEqual(
    [...directionSliceRowsByKey.entries()].sort(([left], [right]) => left.localeCompare(right)),
    EXPECTED_OWNERSHIP_PROJECTION_DIRECTION_COUNTS.map(([key, rowCount]) => [key, rowCount])
  );
  assert.deepEqual(
    [...directionSliceRowsByKey.entries()].sort(([left], [right]) => left.localeCompare(right)),
    triage.report.ownership_projection_direction_slices.map((slice) => [slice.key, slice.row_count])
  );
});

test("manifest-only preservation triage exports direction slice rows as a CSV sidecar", () => {
  const triage = runManifestOnlyTriageWithCsv();
  assert.equal(triage.result.status, 0, triage.result.stderr);
  assert.ok(fs.existsSync(triage.out));
  assert.ok(fs.existsSync(triage.csvOut));
  assert.equal(triage.report.status, "allowed");

  const csvRows = parseCsv(triage.csv);
  const [header, ...dataRows] = csvRows;
  assert.deepEqual(header, DIRECTION_SLICE_ROW_FIELDS);
  assert.equal(dataRows.length, triage.report.direction_slice_rows.length);
  assert.equal(dataRows.length, 50);

  const expectedRows = triage.report.direction_slice_rows.map((row) =>
    DIRECTION_SLICE_ROW_FIELDS.map((field) => (row[field] === null || row[field] === undefined ? "" : String(row[field])))
  );
  assert.deepEqual(dataRows, expectedRows);
  assert.equal(dataRows.flat().includes("null"), false);

  const directionCounts = new Map();
  for (const row of dataRows) {
    directionCounts.set(row[0], (directionCounts.get(row[0]) || 0) + 1);
  }
  assert.deepEqual(
    [...directionCounts.entries()].sort(([left], [right]) => left.localeCompare(right)),
    EXPECTED_OWNERSHIP_PROJECTION_DIRECTION_COUNTS.map(([key, rowCount]) => [key, rowCount])
  );
});

test("manifest-only preservation triage writes a review packet manifest sidecar", () => {
  const triage = runManifestOnlyTriageWithReviewPacket();
  assert.equal(triage.result.status, 0, triage.result.stderr);
  assert.ok(fs.existsSync(triage.out));
  assert.ok(fs.existsSync(triage.csvOut));
  assert.ok(fs.existsSync(triage.packetOut));

  assertPacketSchema(triage.packet);
  assert.equal(triage.packet.schema_version, 1);
  assert.equal(triage.packet.status, triage.report.status);
  assert.deepEqual(triage.packet.generated_outputs, {
    manifest_only_preservation_triage_json: triage.out,
    direction_slice_rows_csv: triage.csvOut,
  });
  assert.deepEqual(triage.packet.summary, {
    manifest_only_preservation_row_count: triage.report.manifest_only_preservation_row_count,
    manifest_only_preservation_record_count: triage.report.manifest_only_preservation_record_count,
    group_count: triage.report.group_count,
    single_row_group_count: triage.report.single_row_group_count,
    multi_row_group_count: triage.report.multi_row_group_count,
    invalid_preserved_count: triage.report.invalid_preserved_count,
  });
  assert.deepEqual(
    triage.packet.direction_counts,
    triage.report.ownership_projection_direction_rollup.map(({ key, row_count, record_count, group_count }) => ({
      key,
      row_count,
      record_count,
      group_count,
    }))
  );
  assert.deepEqual(
    triage.packet.multi_row_groups,
    triage.report.multi_row_groups.map(({ group_key, manifest_only_preservation_row_count, manifest_row_ids }) => ({
      group_key,
      manifest_only_preservation_row_count,
      manifest_row_ids,
    }))
  );
  assert.deepEqual(triage.packet.csv, {
    written: true,
    row_count: triage.report.direction_slice_rows.length,
    header: DIRECTION_SLICE_ROW_FIELDS,
  });
  const csvRows = parseCsv(triage.csv);
  const [csvHeader, ...csvDataRows] = csvRows;
  assert.deepEqual(triage.packet.csv.header, csvHeader);
  assert.equal(triage.packet.csv.row_count, csvDataRows.length);

  const noCsv = runManifestOnlyTriageWithReviewPacket({ includeCsv: false });
  assert.equal(noCsv.result.status, 0, noCsv.result.stderr);
  assert.ok(fs.existsSync(noCsv.out));
  assert.ok(fs.existsSync(noCsv.packetOut));
  assert.equal(noCsv.csvOut, null);
  assertPacketSchema(noCsv.packet);
  assert.deepEqual(noCsv.packet.generated_outputs, {
    manifest_only_preservation_triage_json: noCsv.out,
    direction_slice_rows_csv: null,
  });
  assert.deepEqual(noCsv.packet.csv, {
    written: false,
    row_count: null,
    header: null,
  });
  assert.deepEqual(noCsv.packet.summary, {
    manifest_only_preservation_row_count: noCsv.report.manifest_only_preservation_row_count,
    manifest_only_preservation_record_count: noCsv.report.manifest_only_preservation_record_count,
    group_count: noCsv.report.group_count,
    single_row_group_count: noCsv.report.single_row_group_count,
    multi_row_group_count: noCsv.report.multi_row_group_count,
    invalid_preserved_count: noCsv.report.invalid_preserved_count,
  });
  assert.deepEqual(
    noCsv.packet.direction_counts,
    noCsv.report.ownership_projection_direction_rollup.map(({ key, row_count, record_count, group_count }) => ({
      key,
      row_count,
      record_count,
      group_count,
    }))
  );
  assert.deepEqual(
    noCsv.packet.multi_row_groups,
    noCsv.report.multi_row_groups.map(({ group_key, manifest_only_preservation_row_count, manifest_row_ids }) => ({
      group_key,
      manifest_only_preservation_row_count,
      manifest_row_ids,
    }))
  );
});

test("manifest-only preservation triage writes a blank decision ledger template", () => {
  const triage = runManifestOnlyTriageWithDecisionLedger();
  assert.equal(triage.result.status, 0, triage.result.stderr);
  assert.ok(fs.existsSync(triage.out));
  assert.ok(fs.existsSync(triage.csvOut));
  assert.ok(fs.existsSync(triage.packetOut));
  assert.ok(fs.existsSync(triage.ledgerOut));
  assertPacketSchema(triage.packet);
  assert.equal(LEDGER_FORBIDDEN_PACKET_KEYS.some((key) => collectObjectKeys(triage.packet).includes(key)), false);
  const [directionCsvHeader, ...directionCsvDataRows] = parseCsv(triage.csv);
  assert.deepEqual(directionCsvHeader, DIRECTION_SLICE_ROW_FIELDS);
  assert.equal(directionCsvDataRows.length, triage.report.direction_slice_rows.length);

  const ledgerRows = parseCsv(triage.ledger);
  const [header, ...dataRows] = ledgerRows;
  assert.deepEqual(header, DECISION_LEDGER_FIELDS);
  assert.equal(dataRows.length, triage.report.groups.length);
  assert.equal(dataRows.length, triage.report.group_count);
  assert.equal(dataRows.length, 50);
  assert.equal(joinedValues([]), "");
  assert.equal(joinedValues(null), "");
  assert.equal(joinedValues(["beta", "alpha", "beta"]), "alpha | beta");

  const actualRows = ledgerRowsToObjects(dataRows);
  const expectedRows = expectedDecisionLedgerRows(triage.report);
  assert.deepEqual(actualRows, expectedRows);
  assert.deepEqual(
    actualRows,
    [...actualRows].sort((left, right) => left.direction_key.localeCompare(right.direction_key) || left.group_key.localeCompare(right.group_key))
  );
  assert.equal(DECISION_LEDGER_FIELDS.every((field) => !LEDGER_ADVICE_TERMS.test(field)), true);

  const groupsByKey = new Map();
  for (const group of triage.report.groups) {
    assert.equal(groupsByKey.has(group.group_key), false);
    groupsByKey.set(group.group_key, group);
  }
  const expectedRowsByGroupKey = new Map();
  for (const row of expectedRows) {
    assert.equal(expectedRowsByGroupKey.has(row.group_key), false);
    expectedRowsByGroupKey.set(row.group_key, row);
  }
  const actualRowsByGroupKey = new Map();
  for (const row of actualRows) {
    assert.equal(actualRowsByGroupKey.has(row.group_key), false);
    assert.equal(groupsByKey.has(row.group_key), true);
    assert.equal(expectedRowsByGroupKey.has(row.group_key), true);
    actualRowsByGroupKey.set(row.group_key, row);
    const expectedRow = expectedRowsByGroupKey.get(row.group_key);
    for (const field of DECISION_LEDGER_CONTEXT_FIELDS) {
      assert.equal(row[field], expectedRow[field]);
    }
    for (const field of DECISION_LEDGER_REVIEW_FIELDS) {
      assert.equal(row[field], "");
      assert.equal(LEDGER_ADVICE_TERMS.test(row[field]), false);
    }
  }
  assert.equal(actualRowsByGroupKey.size, triage.report.group_count);

  const groupDirectionCounts = new Map();
  for (const row of actualRows) {
    groupDirectionCounts.set(row.direction_key, (groupDirectionCounts.get(row.direction_key) || 0) + 1);
  }
  assert.deepEqual(
    [...groupDirectionCounts.entries()].sort(([left], [right]) => left.localeCompare(right)),
    [
      ["production_owned/not_projected->production_owned/not_projected", 12],
      ["production_owned/not_projected->projected_owned/projected_owned", 2],
      ["projected_owned/projected_owned->production_owned/not_projected", 26],
      ["projected_owned/projected_owned->projected_owned/projected_owned", 10],
    ]
  );
  assert.equal(actualRows.some((row) => row.manifest_row_ids.includes(" | ")), false);

  const ledgerOnly = runManifestOnlyTriageWithDecisionLedger({ includeCsv: false, includePacket: false });
  assert.equal(ledgerOnly.result.status, 0, ledgerOnly.result.stderr);
  assert.ok(fs.existsSync(ledgerOnly.out));
  assert.ok(fs.existsSync(ledgerOnly.ledgerOut));
  assert.equal(ledgerOnly.csvOut, null);
  assert.equal(ledgerOnly.packetOut, null);
  const [ledgerOnlyHeader, ...ledgerOnlyRows] = parseCsv(ledgerOnly.ledger);
  assert.deepEqual(ledgerOnlyHeader, DECISION_LEDGER_FIELDS);
  assert.equal(ledgerOnlyRows.length, 50);
});

test("manifest-only preservation full review bundle command writes the canonical outputs", () => {
  const bundle = runManifestOnlyTriageWithDecisionLedger();
  assert.equal(bundle.result.status, 0, bundle.result.stderr);
  assert.ok(fs.existsSync(bundle.out));
  assert.ok(fs.existsSync(bundle.csvOut));
  assert.ok(fs.existsSync(bundle.packetOut));
  assert.ok(fs.existsSync(bundle.ledgerOut));

  assert.equal(bundle.report.status, "allowed");
  assert.equal(bundle.report.manifest_only_preservation_row_count, 50);
  assert.equal(bundle.report.group_count, 50);
  assert.equal(bundle.report.invalid_preserved_count, 0);

  const [directionHeader, ...directionDataRows] = parseCsv(bundle.csv);
  assert.deepEqual(directionHeader, DIRECTION_SLICE_ROW_FIELDS);
  assert.equal(directionDataRows.length, bundle.report.direction_slice_rows.length);
  assert.equal(directionDataRows.length, 50);

  assertPacketSchema(bundle.packet);
  assert.equal(bundle.packet.status, "allowed");
  assert.equal(bundle.packet.csv.written, true);

  const [ledgerHeader, ...ledgerDataRows] = parseCsv(bundle.ledger);
  assert.deepEqual(ledgerHeader, DECISION_LEDGER_FIELDS);
  assert.equal(ledgerDataRows.length, bundle.report.groups.length);
  assert.equal(ledgerDataRows.length, 50);
});

test("manifest-only preservation validates a completed decision ledger read-only", () => {
  const bundle = runManifestOnlyTriageWithDecisionLedger();
  assert.equal(bundle.result.status, 0, bundle.result.stderr);
  const [ledgerHeader, ...ledgerDataRows] = parseCsv(bundle.ledger);
  const ledgerRows = ledgerRowsToObjects(ledgerDataRows);
  ledgerRows[0].review_status = "reviewed";
  ledgerRows[0].reviewer = "Sean";
  ledgerRows[0].reviewed_at = "2026-05-04";
  ledgerRows[0].decision = "preserve";
  ledgerRows[0].decision_reason = "manual review";
  ledgerRows[0].followup_action = "none";
  ledgerRows[1].review_status = "pending";
  ledgerRows[1].decision = "needs_research";
  ledgerRows[1].followup_action = "open_question";
  const filledLedger = tempPath("filled-decision-ledger.csv");
  writeCsv(filledLedger, ledgerHeader, ledgerObjectsToCsvRows(ledgerRows));

  const validation = runDecisionLedgerValidation(filledLedger);
  assert.equal(validation.result.status, 0, validation.result.stderr);
  assert.ok(fs.existsSync(validation.out));
  assert.ok(fs.existsSync(validation.validationOut));
  assert.equal(validation.report.status, "allowed");
  assertValidationReportSchema(validation.validationReport);
  assert.equal(validation.validationReport.schema_version, 1);
  assert.equal(validation.validationReport.status, "allowed");
  assert.equal(validation.validationReport.ledger_row_count, 50);
  assert.equal(validation.validationReport.current_group_count, 50);
  assert.equal(validation.validationReport.matched_group_count, 50);
  assert.equal(validation.validationReport.missing_group_count, 0);
  assert.equal(validation.validationReport.unknown_group_count, 0);
  assert.equal(validation.validationReport.duplicate_group_count, 0);
  assert.equal(validation.validationReport.schema_error_count, 0);
  assert.equal(validation.validationReport.review_value_error_count, 0);
  assert.deepEqual(validation.validationReport.errors, []);
  assert.deepEqual(validation.validationReport.missing_groups, []);
  assert.deepEqual(validation.validationReport.unknown_groups, []);
  assert.deepEqual(validation.validationReport.duplicate_groups, []);
  assert.deepEqual(validation.validationReport.schema_errors, []);
  assert.deepEqual(validation.validationReport.review_value_errors, []);
  assert.equal(validation.validationReport.groups.length, 50);
  assert.deepEqual(
    validation.validationReport.groups.map((group) => group.group_key),
    ledgerRows.map((row) => row.group_key)
  );
  assert.equal(validation.validationReport.groups[0].matched, true);
  assert.equal(validation.validationReport.groups[0].review_status, "reviewed");
  assert.equal(validation.validationReport.groups[0].decision, "preserve");
  assert.equal(validation.validationReport.groups[1].review_status, "pending");
  assert.equal(validation.validationReport.groups[1].decision, "needs_research");
});

test("manifest-only preservation writes a compact decision ledger validation summary", () => {
  const bundle = runManifestOnlyTriageWithDecisionLedger();
  assert.equal(bundle.result.status, 0, bundle.result.stderr);
  const [ledgerHeader, ...ledgerDataRows] = parseCsv(bundle.ledger);
  const ledgerRows = ledgerRowsToObjects(ledgerDataRows);
  ledgerRows[0].review_status = "reviewed";
  ledgerRows[0].decision = "preserve";
  ledgerRows[0].followup_action = "none";
  ledgerRows[1].review_status = "pending";
  ledgerRows[1].decision = "needs_research";
  ledgerRows[1].followup_action = "open_question";
  const filledLedger = tempPath("filled-decision-ledger.csv");
  writeCsv(filledLedger, ledgerHeader, ledgerObjectsToCsvRows(ledgerRows));
  const summaryOut = tempPath("decision-ledger-validation-summary.json");

  const validation = runDecisionLedgerValidation(filledLedger, [
    "--decision-ledger-validation-summary-out",
    summaryOut,
  ]);
  assert.equal(validation.result.status, 0, validation.result.stderr);
  assert.ok(fs.existsSync(validation.validationOut));
  assert.ok(fs.existsSync(summaryOut));
  assertValidationReportSchema(validation.validationReport);
  assertValidationSummarySchema(validation.summary);
  assert.deepEqual(validation.summary, expectedValidationSummary(validation.validationReport));
  assertValidationSummaryParity(validation.summary, validation.validationReport);
  assert.equal(validation.summary.status, "allowed");
  assert.deepEqual(validation.summary.error_counts, {
    missing_group_count: 0,
    unknown_group_count: 0,
    duplicate_group_count: 0,
    schema_error_count: 0,
    review_value_error_count: 0,
  });
  assert.deepEqual(validation.summary.review_field_counts.review_status, {
    "": 48,
    pending: 1,
    reviewed: 1,
  });

  const blockingRows = [{ ...ledgerRows[0], decision: "migrate_now" }, ...ledgerRows.slice(1)];
  const blockingLedger = tempPath("blocking-decision-ledger.csv");
  const blockingSummaryOut = tempPath("blocking-decision-ledger-validation-summary.json");
  writeCsv(blockingLedger, ledgerHeader, ledgerObjectsToCsvRows(blockingRows));
  const blocking = runDecisionLedgerValidation(blockingLedger, [
    "--decision-ledger-validation-summary-out",
    blockingSummaryOut,
  ]);
  assert.notEqual(blocking.result.status, 0);
  assert.ok(fs.existsSync(blocking.validationOut));
  assert.ok(fs.existsSync(blockingSummaryOut));
  assertValidationReportSchema(blocking.validationReport);
  assertValidationSummarySchema(blocking.summary);
  assert.deepEqual(blocking.summary, expectedValidationSummary(blocking.validationReport));
  assertValidationSummaryParity(blocking.summary, blocking.validationReport);
  assert.equal(blocking.summary.status, "blocking");
  assert.equal(blocking.summary.error_counts.review_value_error_count, 1);
});

test("manifest-only preservation writes a manual review readiness checkpoint", () => {
  const bundle = runManifestOnlyTriageWithDecisionLedger();
  assert.equal(bundle.result.status, 0, bundle.result.stderr);
  const [ledgerHeader, ...ledgerDataRows] = parseCsv(bundle.ledger);
  const ledgerRows = ledgerRowsToObjects(ledgerDataRows);
  ledgerRows[0].review_status = "reviewed";
  ledgerRows[0].decision = "preserve";
  ledgerRows[0].followup_action = "none";
  ledgerRows[1].review_status = "pending";
  ledgerRows[1].decision = "needs_research";
  ledgerRows[1].followup_action = "open_question";
  const filledLedger = tempPath("filled-decision-ledger-checkpoint.csv");
  writeCsv(filledLedger, ledgerHeader, ledgerObjectsToCsvRows(ledgerRows));
  const summaryOut = tempPath("decision-ledger-validation-summary-checkpoint.json");
  const checkpointOut = tempPath("manual-review-readiness-checkpoint.json");

  const validation = runDecisionLedgerValidation(filledLedger, [
    "--decision-ledger-validation-summary-out",
    summaryOut,
    "--manual-review-readiness-checkpoint-out",
    checkpointOut,
  ]);
  assert.equal(validation.result.status, 0, validation.result.stderr);
  assert.ok(fs.existsSync(validation.validationOut));
  assert.ok(fs.existsSync(summaryOut));
  assert.ok(fs.existsSync(checkpointOut));
  assertValidationReportSchema(validation.validationReport);
  assertValidationSummarySchema(validation.summary);
  assertManualReviewCheckpointSchema(validation.checkpoint);
  assert.deepEqual(validation.checkpoint, expectedManualReviewCheckpoint(validation.report, validation.validationReport));
  assert.equal(validation.checkpoint.status, "ready_for_manual_review");
  assert.equal(validation.checkpoint.not_migration_ready, true);
  assert.equal(validation.checkpoint.required_next_step, "manual_review");
  assert.equal(validation.checkpoint.counts.error_count, 0);

  const blockingRows = [{ ...ledgerRows[0], decision: "migrate_now" }, ...ledgerRows.slice(1)];
  const blockingLedger = tempPath("blocking-decision-ledger-checkpoint.csv");
  const blockingSummaryOut = tempPath("blocking-decision-ledger-validation-summary-checkpoint.json");
  const blockingCheckpointOut = tempPath("blocking-manual-review-readiness-checkpoint.json");
  writeCsv(blockingLedger, ledgerHeader, ledgerObjectsToCsvRows(blockingRows));
  const blocking = runDecisionLedgerValidation(blockingLedger, [
    "--decision-ledger-validation-summary-out",
    blockingSummaryOut,
    "--manual-review-readiness-checkpoint-out",
    blockingCheckpointOut,
  ]);
  assert.notEqual(blocking.result.status, 0);
  assert.ok(fs.existsSync(blocking.validationOut));
  assert.ok(fs.existsSync(blockingSummaryOut));
  assert.ok(fs.existsSync(blockingCheckpointOut));
  assertValidationReportSchema(blocking.validationReport);
  assertValidationSummarySchema(blocking.summary);
  assertManualReviewCheckpointSchema(blocking.checkpoint);
  assert.deepEqual(blocking.checkpoint, expectedManualReviewCheckpoint(blocking.report, blocking.validationReport));
  assert.equal(blocking.checkpoint.status, "blocked");
  assert.equal(blocking.checkpoint.not_migration_ready, true);
  assert.equal(blocking.checkpoint.required_next_step, "manual_review");
  assert.equal(blocking.checkpoint.counts.error_count, 1);
});

test("manifest-only preservation blocks malformed decision ledgers", () => {
  const bundle = runManifestOnlyTriageWithDecisionLedger();
  assert.equal(bundle.result.status, 0, bundle.result.stderr);
  const [ledgerHeader, ...ledgerDataRows] = parseCsv(bundle.ledger);
  const baseRows = ledgerRowsToObjects(ledgerDataRows);
  const cases = [
    {
      name: "missing group",
      header: ledgerHeader,
      rows: baseRows.slice(1),
      expected: { missing_group_count: 1 },
      errorTypes: ["missing_group"],
    },
    {
      name: "duplicate group",
      header: ledgerHeader,
      rows: [baseRows[0], baseRows[0], ...baseRows.slice(1)],
      expected: { duplicate_group_count: 1 },
      errorTypes: ["duplicate_group"],
    },
    {
      name: "unknown group",
      header: ledgerHeader,
      rows: [{ ...baseRows[0], group_key: "unknown_group" }, ...baseRows.slice(1)],
      expected: { unknown_group_count: 1, missing_group_count: 1 },
      errorTypes: ["missing_group", "unknown_group"],
    },
    {
      name: "bad header",
      header: ledgerHeader.filter((field) => field !== "notes"),
      rows: baseRows,
      fields: ledgerHeader.filter((field) => field !== "notes"),
      expected: { schema_error_count: 1 },
      errorTypes: ["bad_header"],
    },
    {
      name: "context mismatch",
      header: ledgerHeader,
      rows: [{ ...baseRows[0], source_ids: "changed_source" }, ...baseRows.slice(1)],
      expected: { schema_error_count: 1 },
      errorTypes: ["context_mismatch"],
    },
    {
      name: "direction mismatch",
      header: ledgerHeader,
      rows: [{ ...baseRows[0], direction_key: "wrong->direction" }, ...baseRows.slice(1)],
      expected: { schema_error_count: 1 },
      errorTypes: ["direction_mismatch"],
    },
    {
      name: "invalid review status",
      header: ledgerHeader,
      rows: [{ ...baseRows[0], review_status: "done" }, ...baseRows.slice(1)],
      expected: { review_value_error_count: 1 },
      errorTypes: ["invalid_review_status"],
    },
    {
      name: "invalid decision",
      header: ledgerHeader,
      rows: [{ ...baseRows[0], decision: "migrate_now" }, ...baseRows.slice(1)],
      expected: { review_value_error_count: 1 },
      errorTypes: ["invalid_decision"],
    },
    {
      name: "invalid followup action",
      header: ledgerHeader,
      rows: [{ ...baseRows[0], followup_action: "ship_it" }, ...baseRows.slice(1)],
      expected: { review_value_error_count: 1 },
      errorTypes: ["invalid_followup_action"],
    },
    {
      name: "invalid reviewed date",
      header: ledgerHeader,
      rows: [{ ...baseRows[0], reviewed_at: "05/04/2026" }, ...baseRows.slice(1)],
      expected: { review_value_error_count: 1 },
      errorTypes: ["invalid_reviewed_at"],
    },
  ];

  for (const fixture of cases) {
    const ledgerPath = tempPath(`${fixture.name.replaceAll(" ", "-")}.csv`);
    writeCsv(ledgerPath, fixture.header, ledgerObjectsToCsvRows(fixture.rows, fixture.fields ?? DECISION_LEDGER_FIELDS));
    const validation = runDecisionLedgerValidation(ledgerPath);
    assert.notEqual(validation.result.status, 0, fixture.name);
    assert.ok(fs.existsSync(validation.validationOut), fixture.name);
    assertValidationReportSchema(validation.validationReport);
    assert.equal(validation.validationReport.status, "blocking", fixture.name);
    for (const [field, count] of Object.entries(fixture.expected)) {
      assert.equal(validation.validationReport[field], count, fixture.name);
    }
    assert.equal(validation.validationReport.errors.length > 0, true, fixture.name);
    assert.deepEqual(
      [...new Set(validation.validationReport.errors.map((error) => error.error_type))].sort(),
      fixture.errorTypes,
      fixture.name
    );
    assert.equal(
      validation.validationReport.errors.length,
      validation.validationReport.missing_groups.length +
        validation.validationReport.unknown_groups.length +
        validation.validationReport.duplicate_groups.length +
        validation.validationReport.schema_errors.length +
        validation.validationReport.review_value_errors.length,
      fixture.name
    );
    assert.equal(validation.validationReport.missing_group_count, validation.validationReport.missing_groups.length, fixture.name);
    assert.equal(validation.validationReport.unknown_group_count, validation.validationReport.unknown_groups.length, fixture.name);
    assert.equal(validation.validationReport.duplicate_group_count, validation.validationReport.duplicate_groups.length, fixture.name);
    assert.equal(validation.validationReport.schema_error_count, validation.validationReport.schema_errors.length, fixture.name);
    assert.equal(validation.validationReport.review_value_error_count, validation.validationReport.review_value_errors.length, fixture.name);
  }
});

test("manifest-only preservation triage rejects data-js mode and leaves default overlay output alone", () => {
  const out = tempPath("manifest-only-triage-data-js.json");
  const csvOut = tempPath("manifest-only-triage-data-js.csv");
  const packetOut = tempPath("manifest-only-triage-data-js-packet.json");
  const ledgerOut = tempPath("manifest-only-triage-data-js-ledger.csv");
  const validationOut = tempPath("manifest-only-triage-data-js-ledger-validation.json");
  const summaryOut = tempPath("manifest-only-triage-data-js-ledger-validation-summary.json");
  const checkpointOut = tempPath("manifest-only-triage-data-js-manual-review-checkpoint.json");
  const invalid = spawnSync(PYTHON, [OVERLAY_SCRIPT, "--manifest-only-preservation-triage", "--as-data-js", "--out", out, "--direction-slice-rows-csv-out", csvOut, "--review-packet-manifest-out", packetOut, "--decision-ledger-csv-out", ledgerOut, "--validate-decision-ledger-csv", ledgerOut, "--decision-ledger-validation-report-out", validationOut, "--decision-ledger-validation-summary-out", summaryOut, "--manual-review-readiness-checkpoint-out", checkpointOut], {
    cwd: process.cwd(),
    encoding: "utf8",
    maxBuffer: 8 * 1024 * 1024,
  });
  assert.notEqual(invalid.status, 0);
  assert.match(invalid.stderr, /cannot be combined with --as-data-js/);
  assert.equal(fs.existsSync(out), false);
  assert.equal(fs.existsSync(csvOut), false);
  assert.equal(fs.existsSync(packetOut), false);
  assert.equal(fs.existsSync(ledgerOut), false);
  assert.equal(fs.existsSync(validationOut), false);
  assert.equal(fs.existsSync(summaryOut), false);
  assert.equal(fs.existsSync(checkpointOut), false);

  const csvWithoutOwningMode = spawnSync(PYTHON, [OVERLAY_SCRIPT, "--direction-slice-rows-csv-out", tempPath("direction-slice-rows.csv")], {
    cwd: process.cwd(),
    encoding: "utf8",
    maxBuffer: 8 * 1024 * 1024,
  });
  assert.notEqual(csvWithoutOwningMode.status, 0);
  assert.match(csvWithoutOwningMode.stderr, /--direction-slice-rows-csv-out requires --manifest-only-preservation-triage/);

  const packetWithoutOwningMode = spawnSync(PYTHON, [OVERLAY_SCRIPT, "--review-packet-manifest-out", tempPath("review-packet-manifest.json")], {
    cwd: process.cwd(),
    encoding: "utf8",
    maxBuffer: 8 * 1024 * 1024,
  });
  assert.notEqual(packetWithoutOwningMode.status, 0);
  assert.match(packetWithoutOwningMode.stderr, /--review-packet-manifest-out requires --manifest-only-preservation-triage/);

  const ledgerWithoutOwningMode = spawnSync(PYTHON, [OVERLAY_SCRIPT, "--decision-ledger-csv-out", tempPath("decision-ledger.csv")], {
    cwd: process.cwd(),
    encoding: "utf8",
    maxBuffer: 8 * 1024 * 1024,
  });
  assert.notEqual(ledgerWithoutOwningMode.status, 0);
  assert.match(ledgerWithoutOwningMode.stderr, /--decision-ledger-csv-out requires --manifest-only-preservation-triage/);

  const validateWithoutOwningMode = spawnSync(PYTHON, [OVERLAY_SCRIPT, "--validate-decision-ledger-csv", tempPath("decision-ledger.csv")], {
    cwd: process.cwd(),
    encoding: "utf8",
    maxBuffer: 8 * 1024 * 1024,
  });
  assert.notEqual(validateWithoutOwningMode.status, 0);
  assert.match(validateWithoutOwningMode.stderr, /--validate-decision-ledger-csv requires --manifest-only-preservation-triage/);

  const validationReportWithoutLedger = spawnSync(PYTHON, [OVERLAY_SCRIPT, "--decision-ledger-validation-report-out", tempPath("decision-ledger-validation.json")], {
    cwd: process.cwd(),
    encoding: "utf8",
    maxBuffer: 8 * 1024 * 1024,
  });
  assert.notEqual(validationReportWithoutLedger.status, 0);
  assert.match(validationReportWithoutLedger.stderr, /--decision-ledger-validation-report-out requires --validate-decision-ledger-csv/);

  const validationSummaryWithoutLedger = spawnSync(PYTHON, [OVERLAY_SCRIPT, "--decision-ledger-validation-summary-out", tempPath("decision-ledger-validation-summary.json")], {
    cwd: process.cwd(),
    encoding: "utf8",
    maxBuffer: 8 * 1024 * 1024,
  });
  assert.notEqual(validationSummaryWithoutLedger.status, 0);
  assert.match(validationSummaryWithoutLedger.stderr, /--decision-ledger-validation-summary-out requires --validate-decision-ledger-csv/);

  const manualReviewCheckpointWithoutLedger = spawnSync(PYTHON, [OVERLAY_SCRIPT, "--manual-review-readiness-checkpoint-out", tempPath("manual-review-readiness-checkpoint.json")], {
    cwd: process.cwd(),
    encoding: "utf8",
    maxBuffer: 8 * 1024 * 1024,
  });
  assert.notEqual(manualReviewCheckpointWithoutLedger.status, 0);
  assert.match(manualReviewCheckpointWithoutLedger.stderr, /--manual-review-readiness-checkpoint-out requires --validate-decision-ledger-csv/);

  const stdoutRun = defaultOverlayStdout();
  const outRun = defaultOverlayOutFile();
  assert.equal(stdoutRun.status, 0, stdoutRun.stderr);
  assert.equal(outRun.result.status, 0, outRun.result.stderr);
  assert.equal(outRun.output, stdoutRun.stdout.endsWith("\n") ? stdoutRun.stdout : `${stdoutRun.stdout}\n`);
});
