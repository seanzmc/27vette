import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import test from "node:test";

import { loadGeneratedData } from "./runtime-harness.mjs";

const PYTHON = ".venv/bin/python";
const OVERLAY_SCRIPT = "scripts/stingray_csv_shadow_overlay.py";
const NAMESPACE_ORDER = ["active_choice", "production_guarded", "interior_source", "unresolved"];

function plain(value) {
  return JSON.parse(JSON.stringify(value));
}

function writeProductionData(data) {
  const tempDir = fs.mkdtempSync(path.join(os.tmpdir(), "stingray-structured-ref-production-"));
  const file = path.join(tempDir, "data.js");
  const registry = {
    defaultModelKey: "stingray",
    models: {
      stingray: {
        key: "stingray",
        label: "Stingray",
        modelName: "Corvette Stingray",
        exportSlug: "stingray",
        data,
      },
    },
  };
  fs.writeFileSync(
    file,
    `window.CORVETTE_FORM_DATA = ${JSON.stringify(registry)};\nwindow.STINGRAY_FORM_DATA = window.CORVETTE_FORM_DATA.models.stingray.data;\n`
  );
  return file;
}

function reportPath() {
  const tempDir = fs.mkdtempSync(path.join(os.tmpdir(), "stingray-structured-ref-report-"));
  return path.join(tempDir, "structured-reference-namespace-report.json");
}

function runReport(args = []) {
  const out = reportPath();
  const result = spawnSync(PYTHON, [OVERLAY_SCRIPT, "--structured-reference-namespace-report", "--out", out, ...args], {
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

function runOverlay(args = []) {
  return spawnSync(PYTHON, [OVERLAY_SCRIPT, ...args], {
    cwd: process.cwd(),
    encoding: "utf8",
    maxBuffer: 8 * 1024 * 1024,
  });
}

function sortKey(row) {
  return [
    NAMESPACE_ORDER.indexOf(row.namespace),
    row.ref_id,
    row.source_kind,
    row.source_id,
    row.reference_kind,
    row.reference_path,
    row.field,
  ];
}

function compareRows(left, right) {
  const leftKey = sortKey(left);
  const rightKey = sortKey(right);
  for (let index = 0; index < leftKey.length; index++) {
    const delta = String(leftKey[index]).localeCompare(String(rightKey[index]));
    if (delta !== 0) return delta;
  }
  return 0;
}

test("structured reference namespace report classifies current production refs deterministically", () => {
  const { result, report } = runReport();

  assert.equal(result.status, 0, result.stderr);
  assert.equal(report.schema_version, 1);
  assert.equal(report.status, "allowed");
  assert.equal(report.unresolved_count, 0);
  assert.equal(report.counts_by_namespace.unresolved, 0);
  assert.ok(report.counts_by_namespace.active_choice > 0);
  assert.ok(report.counts_by_namespace.production_guarded > 0);
  assert.ok(report.counts_by_namespace.interior_source > 0);
  assert.deepEqual(report.references, [...report.references].sort(compareRows));

  const interiorRows = report.references.filter((row) => row.namespace === "interior_source");
  const interiorIds = [...new Set(interiorRows.map((row) => row.ref_id))].sort();
  assert.equal(interiorIds.length, 30);
  assert.equal(interiorIds.every((id) => id.startsWith("3LT_")), true);
  assert.equal(interiorRows.every((row) => row.status === "allowed"), true);
  assert.equal(report.references.some((row) => interiorIds.includes(row.ref_id) && row.namespace === "production_guarded"), false);
  assert.equal(report.references.some((row) => interiorIds.includes(row.ref_id) && row.namespace === "unresolved"), false);

  const guardedRefs = new Set(report.references.filter((row) => row.namespace === "production_guarded").map((row) => row.ref_id));
  assert.equal(guardedRefs.has("opt_cf8_001"), true);
  assert.equal(guardedRefs.has("opt_ryq_001"), true);

  const r6xRows = report.references.filter((row) => row.ref_id === "opt_r6x_001");
  assert.ok(r6xRows.length > 0);
  assert.equal(r6xRows.every((row) => row.namespace === "active_choice" && row.status === "allowed"), true);
});

test("structured reference namespace report writes blocking unresolved refs without quieting validation", () => {
  const production = plain(loadGeneratedData());
  const template = production.rules.find((rule) => rule.source_id.startsWith("3LT_"));
  assert.ok(template, "production should include interior-sourced structured rules");
  production.rules.push({
    ...template,
    rule_id: "rule_unknown_non_choice_source_includes_r6x",
    source_id: "UNKNOWN_NON_CHOICE_SOURCE",
  });
  const productionPath = writeProductionData(production);

  const reportRun = runReport(["--production-data", productionPath]);

  assert.notEqual(reportRun.result.status, 0);
  assert.match(reportRun.result.stderr, /blocking unresolved structured refs/);
  assert.ok(reportRun.report, "blocking report should still be written for inspection");
  assert.equal(reportRun.report.status, "blocking");
  assert.equal(reportRun.report.unresolved_count, 1);
  assert.deepEqual(
    reportRun.report.references.filter((row) => row.ref_id === "UNKNOWN_NON_CHOICE_SOURCE"),
    [
      {
        ref_id: "UNKNOWN_NON_CHOICE_SOURCE",
        namespace: "unresolved",
        source_kind: "rule",
        source_id: "rule_unknown_non_choice_source_includes_r6x",
        reference_kind: "structured_ref",
        reference_path: "rules[].source_id",
        field: "source_id",
        status: "blocking",
        notes: "Structured reference does not resolve to an active choice, production_guarded option, or interior source.",
      },
    ]
  );

  const overlayRun = runOverlay(["--production-data", productionPath]);
  assert.notEqual(overlayRun.status, 0);
  assert.match(overlayRun.stderr, /unknown structured non-choice refs/);
});

test("structured reference namespace report rejects data-js output mode", () => {
  const out = reportPath();
  const result = spawnSync(PYTHON, [OVERLAY_SCRIPT, "--structured-reference-namespace-report", "--as-data-js", "--out", out], {
    cwd: process.cwd(),
    encoding: "utf8",
    maxBuffer: 8 * 1024 * 1024,
  });

  assert.notEqual(result.status, 0);
  assert.match(result.stderr, /cannot be combined with --as-data-js/);
  assert.equal(fs.existsSync(out), false);
});
