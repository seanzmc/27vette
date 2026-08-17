// Independent workbook row reader for parity gates.
//
// Spec `docs/superpowers/specs/2026-08-17-fast-layered-validation-suite.md` §4.2:
// a parity test compares two independent paths, and the expected side must be a
// direct, simple read of the authoritative workbook rows. It may not call the
// generator transformation under test — a shared generator function cannot be
// both implementation and oracle.
//
// So this reads cells with openpyxl and nothing else. No import of
// `corvette_form_generator`, no filtering, no normalization beyond the one
// documented representation fix: openpyxl returns real booleans for cells the
// generator reads back as the legacy "True"/"False" strings, so booleans are
// rendered in that legacy form and every other value is passed through raw.
//
// Checkpoint 2 replaces this with the persistent workbook-truth snapshot of §6.2.
// Until then, callers read the exact sheets their assertion needs.
import { execFileSync } from "node:child_process";

const READER_PROGRAM = `
import json
import sys

from openpyxl import load_workbook

sheet_names = json.loads(sys.argv[1])
workbook_path = sys.argv[2]

wb = load_workbook(workbook_path, read_only=True, data_only=True)
try:
    result = {}
    for sheet_name in sheet_names:
        if sheet_name not in wb.sheetnames:
            result[sheet_name] = None
            continue
        ws = wb[sheet_name]
        headers = [ws.cell(1, col).value for col in range(1, ws.max_column + 1)]
        rows = []
        for raw in ws.iter_rows(min_row=2, values_only=True):
            record = {}
            for header, value in zip(headers, raw):
                if not header or value is None:
                    continue
                if value is True:
                    value = "True"
                elif value is False:
                    value = "False"
                record[header] = value
            if record:
                rows.append(record)
        result[sheet_name] = rows
    print(json.dumps(result))
finally:
    wb.close()
`;

// One python process per read is the dominant cost of these gates, and a gate
// never writes the workbook it is reading, so completed reads are memoized per
// (workbook, sheet) for the life of the process.
const cache = new Map();

/**
 * Raw rows for one or more workbook sheets, keyed by sheet name.
 * A sheet the workbook does not contain reads back as `null`, so a caller can
 * tell "sheet absent" apart from "sheet present and empty".
 */
export function workbookSheets(sheetNames, { workbookPath = "stingray_master.xlsx" } = {}) {
  const wanted = [...new Set(sheetNames)];
  const missing = wanted.filter((name) => !cache.has(`${workbookPath}::${name}`));
  if (missing.length > 0) {
    const output = execFileSync(
      ".venv/bin/python",
      ["-c", READER_PROGRAM, JSON.stringify(missing), workbookPath],
      { encoding: "utf8", maxBuffer: 256 * 1024 * 1024 },
    );
    for (const [name, rows] of Object.entries(JSON.parse(output))) {
      cache.set(`${workbookPath}::${name}`, rows);
    }
  }
  return Object.fromEntries(wanted.map((name) => [name, cache.get(`${workbookPath}::${name}`)]));
}

/** Raw rows for a single sheet that must exist. */
export function workbookRows(sheetName, options = {}) {
  const rows = workbookSheets([sheetName], options)[sheetName];
  if (rows === null) {
    throw new Error(`workbook sheet ${sheetName} is missing`);
  }
  return rows;
}

/** The workbook's own truthiness convention, matching `workbook.workbook_truthy`. */
export function workbookTruthy(value) {
  return ["true", "yes", "1", "y"].includes(cell(value).toLowerCase());
}

/**
 * The sheet a model registers for one generation source role, read from the
 * workbook's own `model_workbook_sources` rows. Keeps a parity test from
 * naming a sheet literally — the role is the contract, the sheet name is data.
 */
export function modelSourceSheet(modelKey, sourceRole, options = {}) {
  const row = workbookRows("model_workbook_sources", options).find(
    (candidate) =>
      cell(candidate.model_key) === modelKey &&
      cell(candidate.source_role) === sourceRole &&
      workbookTruthy(candidate.active),
  );
  if (!row) {
    throw new Error(`${modelKey} registers no active ${sourceRole}`);
  }
  return cell(row.sheet_name);
}

/** Trim to string, matching the `workbook.clean` representation of a cell. */
export function cell(value) {
  if (value === undefined || value === null) return "";
  if (typeof value === "number" && Number.isInteger(value)) return String(value);
  return String(value).trim();
}
