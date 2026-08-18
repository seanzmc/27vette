// The independent workbook-truth snapshot, as node gates consume it.
//
// Spec `docs/superpowers/specs/2026-08-17-fast-layered-validation-suite.md` §6.2:
// the snapshot is a temporary, untracked JSON document built from a read-only
// workbook handle and shared registry metadata, and "node receives the snapshot
// and candidate registry through explicit temporary paths".
//
// So this module resolves the snapshot in one of two ways:
//
//  1. `CORVETTE_WORKBOOK_TRUTH` names an already-built snapshot. Layer 1 sets
//     it, so the composed candidate lane pays the build once for the whole run
//     and every gate underneath it reads the same immutable document.
//  2. Otherwise the gate builds its own into a fresh temporary directory. That
//     costs about a second per process, which is the honest price of running a
//     parity gate standalone. Cross-run caching is deliberately absent — spec
//     §6.1 puts it out of scope until it can be content-addressed properly.
//
// Nothing is committed, and nothing is written outside `os.tmpdir()`.
//
// This module replaces `tests/lib/workbook-rows.mjs`, the interim per-sheet
// reader Checkpoint 1 introduced. The exported row accessors keep the same
// shape, so a caller states which sheet it needs and gets raw authored rows —
// the difference is that one python process now serves every sheet and every
// gate instead of one process per sheet per gate.
import { execFileSync } from "node:child_process";
import { mkdtempSync, readFileSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import process from "node:process";

const DEFAULT_WORKBOOK = "stingray_master.xlsx";
export const TRUTH_PATH_ENV = "CORVETTE_WORKBOOK_TRUTH";

const cache = new Map();

function buildSnapshot(workbookPath) {
  const directory = mkdtempSync(join(tmpdir(), "workbook-truth-"));
  const target = join(directory, "workbook-truth.json");
  try {
    execFileSync(
      ".venv/bin/python",
      ["scripts/build_workbook_truth.py", "--workbook", workbookPath, "--out", target],
      { encoding: "utf8" },
    );
    return JSON.parse(readFileSync(target, "utf8"));
  } finally {
    rmSync(directory, { recursive: true, force: true });
  }
}

/**
 * The snapshot for one workbook. Memoized per path for the life of the process.
 *
 * `CORVETTE_WORKBOOK_TRUTH` is honoured only for the default workbook: a gate
 * that explicitly asks for some other workbook must not be silently handed the
 * lane's snapshot of a different file.
 */
export function workbookTruth({ workbookPath = DEFAULT_WORKBOOK } = {}) {
  if (!cache.has(workbookPath)) {
    const provided = workbookPath === DEFAULT_WORKBOOK ? process.env[TRUTH_PATH_ENV] : "";
    const snapshot = provided ? JSON.parse(readFileSync(provided, "utf8")) : buildSnapshot(workbookPath);
    if (snapshot.schemaVersion !== "workbook-truth-1") {
      throw new Error(`unexpected workbook-truth schema: ${snapshot.schemaVersion}`);
    }
    cache.set(workbookPath, snapshot);
  }
  return cache.get(workbookPath);
}

/** Raw authored rows for a single sheet that must be registered and present. */
export function workbookRows(sheetName, options = {}) {
  const entry = workbookTruth(options).sheets[sheetName];
  if (!entry) {
    throw new Error(`workbook sheet ${sheetName} is not registered or not present`);
  }
  return entry.rows;
}

/**
 * Raw rows for several sheets at once, keyed by sheet name. A sheet the
 * snapshot does not carry reads back as `null`, so a caller can tell "absent"
 * apart from "present and empty".
 */
export function workbookSheets(sheetNames, options = {}) {
  const truth = workbookTruth(options);
  return Object.fromEntries(
    [...new Set(sheetNames)].map((name) => [name, truth.sheets[name]?.rows ?? null]),
  );
}

/**
 * The sheet a model registers for one generation source role. Keeps a parity
 * test from naming a sheet literally — the role is the contract, the sheet name
 * is data.
 */
export function modelSourceSheet(modelKey, sourceRole, options = {}) {
  const sheet = workbookTruth(options).models[modelKey]?.source_sheets?.[sourceRole];
  if (!sheet) {
    throw new Error(`${modelKey} registers no active ${sourceRole}`);
  }
  return sheet;
}

/** Rows of the sheet a model registers for one source role. */
export function modelSourceRows(modelKey, sourceRole, options = {}) {
  return workbookRows(modelSourceSheet(modelKey, sourceRole, options), options);
}

/** Model keys `model_master` declares active, sorted. */
export function activeModelKeys(options = {}) {
  const truth = workbookTruth(options);
  return Object.values(truth.models)
    .filter((model) => model.active)
    .map((model) => model.model_key)
    .sort();
}

/** The workbook's own truthiness convention, matching `workbook.workbook_truthy`. */
export function workbookTruthy(value) {
  return ["true", "yes", "1", "y"].includes(cell(value).toLowerCase());
}

/**
 * Trim to string, matching the `workbook.clean` representation of a cell.
 *
 * Snapshot rows arrive already cleaned, so this is for values that came from a
 * generated artifact rather than from the snapshot.
 */
export function cell(value) {
  if (value === undefined || value === null) return "";
  if (typeof value === "number" && Number.isInteger(value)) return String(value);
  return String(value).trim();
}
