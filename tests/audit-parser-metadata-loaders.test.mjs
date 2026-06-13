import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import fs from "node:fs";
import test from "node:test";

const pythonBin = process.env.PYTHON || (fs.existsSync(".venv/bin/python") ? ".venv/bin/python" : "/Users/seandm/Projects/27vette/.venv/bin/python");

function runPython(source) {
  return execFileSync(pythonBin, ["-c", source], {
    cwd: process.cwd(),
    encoding: "utf8",
  }).trim();
}

function runPythonJson(source) {
  return JSON.parse(runPython(source));
}

const pythonPrefix = String.raw`
import json
import sys
from openpyxl import Workbook
sys.path.insert(0, "scripts")
from corvette_form_generator.runtime_metadata import (
    load_rule_phrase_map,
)
from build_rule_sources import RULE_PHRASES, candidate_rule_keys

def workbook_with_sheet(sheet_name, headers, rows):
    wb = Workbook()
    ws = wb.active
    ws.title = sheet_name
    ws.append(headers)
    for row in rows:
        ws.append([row.get(header, "") for header in headers])
    return wb

def empty_workbook():
    wb = Workbook()
    wb.active.title = "placeholder"
    return wb
`;

test("rule phrase fallback preserves legacy parsed rule behavior", () => {
  const result = runPythonJson(`${pythonPrefix}
wb = empty_workbook()
phrase_rows = load_rule_phrase_map(wb, RULE_PHRASES)
options = [{
    "option_id": "opt_src_001",
    "rpo": "SRC",
    "detail_raw": "Not available with (TGT).",
}]
option_ids_by_rpo = {"SRC": ["opt_src_001"], "TGT": ["opt_tgt_001"]}
candidates, review_rows, unresolved = candidate_rule_keys(options, option_ids_by_rpo, set(), phrase_rows)
print(json.dumps({
    "phrase_rows": phrase_rows,
    "candidates": sorted([list(item) for item in candidates]),
    "review_rows": review_rows,
    "unresolved": unresolved,
}))
`);

  assert.deepEqual(result.candidates, [["opt_src_001", "excludes", "opt_tgt_001"]]);
  assert.equal(result.review_rows.length, 0);
  assert.equal(result.unresolved.length, 0);
  assert.ok(result.phrase_rows.every((row) => row.notes === "fallback_config"));
});

test("workbook rule phrase rows override fallback parser metadata", () => {
  const result = runPythonJson(`${pythonPrefix}
wb = workbook_with_sheet(
    "rule_phrase_map",
    ["phrase", "rule_type", "direction", "stop_phrases", "review_flag_default", "active", "notes"],
    [{
        "phrase": "not available with",
        "rule_type": "requires",
        "direction": "source_to_mentioned",
        "stop_phrases": "",
        "review_flag_default": "TRUE",
        "active": "TRUE",
        "notes": "test override",
    }],
)
phrase_rows = load_rule_phrase_map(wb, RULE_PHRASES)
options = [{
    "option_id": "opt_src_001",
    "rpo": "SRC",
    "detail_raw": "Not available with (TGT).",
}]
option_ids_by_rpo = {"SRC": ["opt_src_001"], "TGT": ["opt_tgt_001"]}
candidates, review_rows, unresolved = candidate_rule_keys(options, option_ids_by_rpo, set(), phrase_rows)
print(json.dumps({
    "phrase_rows": phrase_rows,
    "candidates": sorted([list(item) for item in candidates]),
}))
`);

  assert.deepEqual(result.candidates, [["opt_src_001", "requires", "opt_tgt_001"]]);
  assert.equal(result.phrase_rows[0].notes, "test override");
});

test("inactive workbook phrase metadata disables parser rows instead of falling back", () => {
  const result = runPythonJson(`${pythonPrefix}
wb = workbook_with_sheet(
    "rule_phrase_map",
    ["phrase", "rule_type", "direction", "stop_phrases", "review_flag_default", "active", "notes"],
    [{
        "phrase": "not available with",
        "rule_type": "excludes",
        "direction": "source_to_mentioned",
        "active": "FALSE",
    }],
)
phrase_rows = load_rule_phrase_map(wb, RULE_PHRASES)
print(json.dumps({"phrase_rows": phrase_rows}))
`);

  assert.deepEqual(result.phrase_rows, []);
});


