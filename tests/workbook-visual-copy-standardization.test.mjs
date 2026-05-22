import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import test from "node:test";

function workbookRows(sheetName) {
  const output = execFileSync(
    ".venv/bin/python",
    [
      "-c",
      [
        "import json",
        "from openpyxl import load_workbook",
        "wb = load_workbook('stingray_master.xlsx', read_only=True, data_only=True)",
        `ws = wb['${sheetName}']`,
        "headers = [ws.cell(1, col).value for col in range(1, ws.max_column + 1)]",
        "rows = []",
        "def legacy_value(value):",
        "    return 'True' if value is True else 'False' if value is False else value",
        "for row_number, raw in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):",
        "    record = {header: legacy_value(value) for header, value in zip(headers, raw) if header}",
        "    if any(value is not None for value in raw):",
        "        record['_row'] = row_number",
        "        rows.append(record)",
        "print(json.dumps(rows))",
      ].join("\n"),
    ],
    { encoding: "utf8" }
  );
  return JSON.parse(output);
}

const rowsBySheet = new Map([
  ["stingray_options", workbookRows("stingray_options")],
  ["grandSport_options", workbookRows("grandSport_options")],
]);

function rowFor(sheetName, optionId) {
  const row = rowsBySheet.get(sheetName).find((candidate) => candidate.option_id === optionId);
  assert.ok(row, `${sheetName} is missing ${optionId}`);
  return row;
}

test("source sheets use concise section-aware brake caliper labels", () => {
  const expectedByOptionId = {
    opt_j6a_001: "Black Painted Calipers",
    opt_j6a_002: "Black Painted Calipers",
    opt_j6f_001: "Bright Red-Painted Calipers",
    opt_j6e_001: "Velocity Yellow-Painted Calipers",
    opt_j6n_001: "Edge Red-Painted Calipers",
    opt_j6b_001: "Blue-Painted Calipers",
  };

  for (const sheetName of ["stingray_options", "grandSport_options"]) {
    for (const [optionId, expectedName] of Object.entries(expectedByOptionId)) {
      const matchingRows = rowsBySheet.get(sheetName).filter((row) => row.option_id === optionId);
      if (sheetName === "grandSport_options" || optionId !== "opt_j6a_002") {
        assert.equal(matchingRows.length, 1, `${sheetName} should contain ${optionId}`);
      }
      for (const row of matchingRows) {
        assert.equal(row.option_name, expectedName, `${sheetName} ${optionId}`);
      }
    }
  }
});

test("source sheets use concise removable-roof labels with consistent order", () => {
  const expectedRoofRows = {
    opt_cf7_001: ["Body-Color Roof Panel", "Removable", 10],
    opt_c2z_001: ["Visible Carbon Fiber Roof Panel", "Removable with body-color surround", 11],
    opt_cc3_001: ["Transparent Roof Panel", "Removable", 12],
  };

  for (const sheetName of ["stingray_options", "grandSport_options"]) {
    for (const [optionId, [expectedName, expectedDescription, expectedOrder]] of Object.entries(expectedRoofRows)) {
      const row = rowFor(sheetName, optionId);
      assert.equal(row.option_name, expectedName, `${sheetName} ${optionId} name`);
      assert.equal(row.description, expectedDescription, `${sheetName} ${optionId} description`);
      assert.equal(Number(row.display_order), expectedOrder, `${sheetName} ${optionId} display order`);
    }

    const standardMirror = rowFor(sheetName, "opt_cf7_002");
    assert.equal(standardMirror.option_name, "Body-Color Roof Panel", `${sheetName} CF7 standard mirror name`);
  }
});

test("Grand Sport engine cover order and customer descriptions match reviewed source copy", () => {
  const expectedEngineRows = {
    opt_bc7_001: [10, null],
    opt_bcp_002: [20, "Includes engine lighting"],
    opt_bcs_002: [30, "Includes engine lighting"],
    opt_bc4_002: [40, "New for 2027. Includes engine lighting"],
  };

  for (const [optionId, [expectedOrder, expectedDescription]] of Object.entries(expectedEngineRows)) {
    const row = rowFor("grandSport_options", optionId);
    assert.equal(Number(row.display_order), expectedOrder, `grandSport_options ${optionId} display order`);
    assert.equal(row.description ?? null, expectedDescription, `grandSport_options ${optionId} description`);
  }
});
