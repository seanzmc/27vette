import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import fs from "node:fs";
import test from "node:test";
import vm from "node:vm";

const FIRST_SLICE_RPOS = new Set(["B6P", "D3V", "SL9", "ZZ3", "BCP", "BCS", "BC4", "BC7"]);

function parseCsv(source) {
  const rows = [];
  let row = [];
  let field = "";
  let inQuotes = false;
  for (let index = 0; index < source.length; index++) {
    const char = source[index];
    const next = source[index + 1];
    if (char === '"' && inQuotes && next === '"') {
      field += '"';
      index++;
    } else if (char === '"') {
      inQuotes = !inQuotes;
    } else if (char === "," && !inQuotes) {
      row.push(field);
      field = "";
    } else if ((char === "\n" || char === "\r") && !inQuotes) {
      if (char === "\r" && next === "\n") index++;
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

function loadGeneratedData() {
  const context = { window: {} };
  vm.runInNewContext(fs.readFileSync("form-app/data.js", "utf8"), context);
  return context.window.STINGRAY_FORM_DATA;
}

function makeElement() {
  return {
    textContent: "",
    innerHTML: "",
    dataset: {},
    addEventListener() {},
    querySelectorAll() {
      return [];
    },
    querySelector() {
      return null;
    },
    closest() {
      return makeElement();
    },
    scrollTo() {},
  };
}

function loadRuntime(data) {
  const context = {
    window: {
      STINGRAY_FORM_DATA: data,
      scrollX: 0,
      scrollY: 0,
      scrollTo() {},
    },
    document: {
      querySelector() {
        return makeElement();
      },
      createElement() {
        return makeElement();
      },
    },
    Intl,
    Number,
    Set,
    Map,
    Boolean,
    Object,
    String,
    URL: {
      createObjectURL() {
        return "";
      },
      revokeObjectURL() {},
    },
    Blob: class TestBlob {},
  };
  const source = fs.readFileSync("form-app/app.js", "utf8").replace(
    /\ninit\(\);\s*$/,
    `
window.__testApi = {
  state,
  activeChoiceRows,
  computeAutoAdded,
  disableReasonForChoice,
  optionPrice,
};
`
  );
  vm.runInNewContext(source, context);
  return context.window.__testApi;
}

const generatedData = loadGeneratedData();
const csvSelectables = parseCsv(fs.readFileSync("data/stingray/catalog/selectables.csv", "utf8"));
const csvRpoBySelectableId = new Map(csvSelectables.map((row) => [row.selectable_id, row.rpo]));

function evaluateCsv(variantId, selectedIds) {
  const output = execFileSync(
    ".venv/bin/python",
    ["scripts/stingray_csv_first_slice.py", "--scenario-json", JSON.stringify({ variant_id: variantId, selected_ids: selectedIds })],
    { cwd: process.cwd(), encoding: "utf8" }
  );
  return JSON.parse(output);
}

function variantContext(variantId) {
  const variant = generatedData.variants.find((item) => item.variant_id === variantId);
  assert.ok(variant, `${variantId} should exist in generated data`);
  return variant;
}

function productionOptionIdForRpo(runtime, rpo) {
  const choice = runtime.activeChoiceRows().find(
    (item) => item.rpo === rpo && item.active === "True" && item.status !== "unavailable"
  );
  assert.ok(choice, `${rpo} should have an active generated choice for the scenario variant`);
  return choice.option_id;
}

function productionFacts(variantId, csvSelectedIds) {
  const variant = variantContext(variantId);
  const runtime = loadRuntime(generatedData);
  runtime.state.bodyStyle = variant.body_style;
  runtime.state.trimLevel = variant.trim_level;

  const selectedProductionIds = csvSelectedIds.map((selectableId) => productionOptionIdForRpo(runtime, csvRpoBySelectableId.get(selectableId)));
  for (const optionId of selectedProductionIds) {
    runtime.state.selected.add(optionId);
    runtime.state.userSelected.add(optionId);
  }

  const autoAdded = runtime.computeAutoAdded();
  const selectedLines = [];
  for (const optionId of selectedProductionIds) {
    const choice = generatedData.choices.find((item) => item.option_id === optionId);
    if (FIRST_SLICE_RPOS.has(choice?.rpo)) {
      selectedLines.push({
        rpo: choice.rpo,
        provenance: ["explicit"],
        final_price_usd: runtime.optionPrice(optionId),
      });
    }
  }
  for (const optionId of autoAdded.keys()) {
    const choice = generatedData.choices.find((item) => item.option_id === optionId);
    if (FIRST_SLICE_RPOS.has(choice?.rpo)) {
      selectedLines.push({
        rpo: choice.rpo,
        provenance: ["auto"],
        final_price_usd: runtime.optionPrice(optionId),
      });
    }
  }

  const openRequirements = selectedProductionIds
    .map((optionId) => runtime.activeChoiceRows().find((choice) => choice.option_id === optionId))
    .filter(Boolean)
    .map((choice) => runtime.disableReasonForChoice(choice))
    .filter((message) => message.includes("Requires ZZ3"));

  const ls6Group = generatedData.exclusiveGroups.find((group) => group.group_id === "grp_ls6_engine_covers");
  const selectedLs6Ids = selectedProductionIds.filter((optionId) => ls6Group?.option_ids?.includes(optionId));
  const conflicts =
    selectedLs6Ids.length > 1
      ? [
          {
            member_rpos: selectedLs6Ids.map((optionId) => generatedData.choices.find((choice) => choice.option_id === optionId)?.rpo),
          },
        ]
      : [];

  return {
    selected_lines: selectedLines.sort((a, b) => a.rpo.localeCompare(b.rpo)),
    auto_added_rpos: [...autoAdded.keys()]
      .map((optionId) => generatedData.choices.find((choice) => choice.option_id === optionId)?.rpo)
      .filter((rpo) => FIRST_SLICE_RPOS.has(rpo))
      .sort(),
    open_requirements: openRequirements,
    conflicts,
  };
}

function csvFacts(result) {
  return {
    selected_lines: result.selected_lines
      .filter((line) => FIRST_SLICE_RPOS.has(line.rpo))
      .map((line) => ({
        rpo: line.rpo,
        provenance: line.provenance,
        final_price_usd: line.final_price_usd,
      }))
      .sort((a, b) => a.rpo.localeCompare(b.rpo)),
    auto_added_rpos: result.auto_added_ids
      .map((selectableId) => result.selected_lines.find((line) => line.selectable_id === selectableId)?.rpo)
      .filter((rpo) => FIRST_SLICE_RPOS.has(rpo))
      .sort(),
    open_requirements: result.open_requirements.map((item) => item.message),
    conflicts: result.conflicts.map((conflict) => ({
      member_rpos: conflict.member_selectable_ids.map((selectableId) => csvRpoBySelectableId.get(selectableId)),
    })),
  };
}

const scenarios = [
  ["coupe B6P", "1lt_c07", ["opt_b6p_001"]],
  ["coupe BCP", "1lt_c07", ["opt_bcp_001"]],
  ["coupe BCP with B6P", "1lt_c07", ["opt_bcp_001", "opt_b6p_001"]],
  ["convertible BCP missing ZZ3", "1lt_c67", ["opt_bcp_001"]],
  ["convertible BCP with ZZ3", "1lt_c67", ["opt_bcp_001", "opt_zz3_001"]],
  ["coupe BCP with BC4", "1lt_c07", ["opt_bcp_001", "opt_bc4_001"]],
  ["explicit D3V with B6P", "1lt_c07", ["opt_d3v_001", "opt_b6p_001"]],
  ["explicit SL9 with B6P", "1lt_c07", ["opt_sl9_001", "opt_b6p_001"]],
];

for (const [name, variantId, selectedIds] of scenarios) {
  test(`CSV first-slice parity with generated runtime: ${name}`, () => {
    const csv = csvFacts(evaluateCsv(variantId, selectedIds));
    const production = productionFacts(variantId, selectedIds);
    assert.deepEqual(csv, production);
  });
}
