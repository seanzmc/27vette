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
    load_audit_group_members,
    load_rule_phrase_map,
    load_rule_review_rpos,
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

test("audit group fallback applies only when workbook group metadata is absent", () => {
  const absentResult = runPythonJson(`${pythonPrefix}
wb = empty_workbook()
print(json.dumps(load_audit_group_members(wb, "engine_cover", ["BC7", "B6P"]), default=sorted))
`);
  assert.deepEqual(absentResult, { rpos: ["B6P", "BC7"], option_ids: [] });

  const inactiveResult = runPythonJson(`${pythonPrefix}
wb = Workbook()
ws = wb.active
ws.title = "option_audit_groups"
ws.append(["group_id", "group_label", "active", "notes"])
ws.append(["engine_cover", "Engine cover options", "FALSE", "test disabled"])
ws_members = wb.create_sheet("option_audit_group_members")
ws_members.append(["group_id", "rpo", "option_id", "active", "notes"])
ws_members.append(["engine_cover", "BC7", "opt_bc7_001", "TRUE", "would be active if group were active"])
print(json.dumps(load_audit_group_members(wb, "engine_cover", ["B6P"]), default=sorted))
`);
  assert.deepEqual(inactiveResult, { rpos: [], option_ids: [] });
});

test("rule review RPOs are workbook-owned when metadata rows exist", () => {
  const workbookOwned = runPythonJson(`${pythonPrefix}
wb = workbook_with_sheet(
    "rule_review_groups",
    ["model_key", "group_id", "rpo", "review_reason", "active", "notes"],
    [{
        "model_key": "grand_sport",
        "group_id": "special_package_review",
        "rpo": "ABC",
        "review_reason": "test",
        "active": "TRUE",
    }],
)
print(json.dumps(sorted(load_rule_review_rpos(wb, "grand_sport", ["EL9", "Z25"]))))
`);
  assert.deepEqual(workbookOwned, ["ABC"]);

  const disabled = runPythonJson(`${pythonPrefix}
wb = workbook_with_sheet(
    "rule_review_groups",
    ["model_key", "group_id", "rpo", "review_reason", "active", "notes"],
    [{
        "model_key": "grand_sport",
        "group_id": "special_package_review",
        "rpo": "ABC",
        "active": "FALSE",
    }],
)
print(json.dumps(sorted(load_rule_review_rpos(wb, "grand_sport", ["EL9", "Z25"]))))
`);
  assert.deepEqual(disabled, []);

  const absent = runPythonJson(`${pythonPrefix}
wb = empty_workbook()
print(json.dumps(sorted(load_rule_review_rpos(wb, "grand_sport", ["EL9", "Z25"]))))
`);
  assert.deepEqual(absent, ["EL9", "Z25"]);
});
