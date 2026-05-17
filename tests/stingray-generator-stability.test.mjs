import assert from "node:assert/strict";
import { execFileSync, spawnSync } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import test from "node:test";
import vm from "node:vm";

function withoutGeneratedAt(data) {
  return JSON.parse(JSON.stringify({
    ...data,
    dataset: {
      ...data.dataset,
      generated_at: "<timestamp>",
    },
  }));
}

function loadAppData() {
  const context = { window: {} };
  vm.runInNewContext(fs.readFileSync("form-app/data.js", "utf8"), context);
  return context.window.STINGRAY_FORM_DATA;
}

const jsonData = JSON.parse(fs.readFileSync("form-output/stingray-form-data.json", "utf8"));
const appData = loadAppData();
const generatorSource = fs.readFileSync("scripts/generate_stingray_form.py", "utf8");
const stingrayVariantIds = ["1lt_c07", "2lt_c07", "3lt_c07", "1lt_c67", "2lt_c67", "3lt_c67"];
const grandSportVariantIds = ["1lt_e07", "2lt_e07", "3lt_e07", "1lt_e67", "2lt_e67", "3lt_e67"];
const optionSourceHeaders = [
  "option_id",
  "rpo",
  "price",
  "option_name",
  "description",
  "detail_raw",
  "section_id",
  "selectable",
  "display_order",
  "active",
  "display_behavior",
];
const optionVariantStatusHeaders = ["option_id", "variant_id", "status"];
const sectionMasterHeaders = [
  "section_id",
  "section_name",
  "selection_mode",
  "is_required",
  "display_order",
  "standard_behavior",
  "help_text",
  "step_key",
];
const optionVariantStatuses = new Set(["available", "standard", "unavailable"]);
const sectionStepKeys = new Set([
  "standard_equipment",
  "paint",
  "exterior_appearance",
  "wheels",
  "packages_performance",
  "aero_exhaust_stripes_accessories",
  "seat",
  "base_interior",
  "seat_belt",
  "interior_trim",
  "accessories",
  "delivery",
]);
const ruleMappingHeaders = [
  "rule_id",
  "source_id",
  "rule_type",
  "target_id",
  "target_type",
  "original_detail_raw",
  "review_flag",
  "source_type",
  "target_selection_mode",
  "source_selection_mode",
  "target_section",
  "source_section",
  "generation_action",
  "body_style_scope",
  "runtime_action",
  "disabled_reason",
];
const priceRuleHeaders = [
  "price_rule_id",
  "condition_option_id",
  "price_rule_type",
  "target_option_id",
  "price_value",
  "body_style_scope",
  "trim_level_scope",
  "review_flag",
  "notes",
];
const requiredGrandSportPriceRuleIds = [
  "gs_pr_fey_j57_001",
  "gs_pr_fey_t0f_001",
  "gs_pr_fey_wub_001",
  "gs_pr_fey_cfz_001",
  "gs_pr_pcq_vwe_001",
  "gs_pr_pcq_vwt_001",
  "gs_pr_pef_ria_001",
  "gs_pr_pef_cav_001",
];

function workbookHeaders(sheetName) {
  const output = execFileSync(
    ".venv/bin/python",
    [
      "-c",
      [
        "import json",
        "from openpyxl import load_workbook",
        "wb = load_workbook('stingray_master.xlsx', read_only=True, data_only=True)",
        `ws = wb['${sheetName}']`,
        "print(json.dumps([ws.cell(1, col).value for col in range(1, ws.max_column + 1) if ws.cell(1, col).value]))",
      ].join("; "),
    ],
    { encoding: "utf8" }
  );
  return JSON.parse(output);
}

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
        "for raw in ws.iter_rows(min_row=2, values_only=True):",
        "    record = {header: value for header, value in zip(headers, raw) if header and value is not None}",
        "    if record:",
        "        rows.append(record)",
        "print(json.dumps(rows))",
      ].join("\n"),
    ],
    { encoding: "utf8" }
  );
  return JSON.parse(output);
}

function assertOptionVariantStatusCoverage(optionSheetName, statusSheetName, variantIds) {
  const optionIds = workbookRows(optionSheetName).map((row) => row.option_id).filter(Boolean);
  const statusRows = workbookRows(statusSheetName);
  const expectedPairs = new Set(optionIds.flatMap((optionId) => variantIds.map((variantId) => `${optionId}::${variantId}`)));
  const actualPairs = new Set(statusRows.map((row) => `${row.option_id}::${row.variant_id}`));

  assert.equal(actualPairs.size, statusRows.length, `${statusSheetName} should not contain duplicate option/variant rows`);
  assert.equal(actualPairs.size, expectedPairs.size, `${statusSheetName} should have one row per option/variant pair`);
  for (const pair of expectedPairs) {
    assert.ok(actualPairs.has(pair), `${statusSheetName} missing ${pair}`);
  }
  for (const row of statusRows) {
    assert.ok(optionVariantStatuses.has(String(row.status).toLowerCase()), `${statusSheetName} has invalid status ${row.status}`);
  }
}

test("workbook package tables validate before Excel opens the file", () => {
  const validation = JSON.parse(
    execFileSync(".venv/bin/python", ["scripts/validate_workbook_package.py", "stingray_master.xlsx"], {
      encoding: "utf8",
    })
  );
  assert.equal(validation.status, "valid");
  assert.equal(validation.issue_count, 0);
});

test("workbook package validation rejects duplicate worksheet AutoFilters on table sheets", () => {
  const tempDir = fs.mkdtempSync(path.join(os.tmpdir(), "vette-workbook-package-"));
  const workbookCopy = path.join(tempDir, "duplicate-autofilter.xlsx");
  fs.copyFileSync("stingray_master.xlsx", workbookCopy);

  execFileSync(
    ".venv/bin/python",
    [
      "-c",
      [
        "from pathlib import Path",
        "from zipfile import ZipFile, ZIP_DEFLATED",
        "from xml.etree import ElementTree as ET",
        `path = Path(${JSON.stringify(workbookCopy)})`,
        "tmp = path.with_suffix('.tmp.xlsx')",
        "ns = '{http://schemas.openxmlformats.org/spreadsheetml/2006/main}'",
        "ET.register_namespace('', 'http://schemas.openxmlformats.org/spreadsheetml/2006/main')",
        "with ZipFile(path, 'r') as source, ZipFile(tmp, 'w', ZIP_DEFLATED) as target:",
        "    for item in source.infolist():",
        "        data = source.read(item.filename)",
        "        if item.filename == 'xl/worksheets/sheet29.xml':",
        "            root = ET.fromstring(data)",
        "            if root.find(ns + 'autoFilter') is None:",
        "                auto_filter = ET.Element(ns + 'autoFilter', {'ref': 'A1:G5'})",
        "                page_margins = root.find(ns + 'pageMargins')",
        "                root.insert(list(root).index(page_margins), auto_filter)",
        "            data = ET.tostring(root, encoding='utf-8', xml_declaration=False)",
        "        target.writestr(item, data)",
        "tmp.replace(path)",
      ].join("\n"),
    ],
    { encoding: "utf8" }
  );

  const validationResult = spawnSync(".venv/bin/python", ["scripts/validate_workbook_package.py", workbookCopy], {
    encoding: "utf8",
  });
  const validation = JSON.parse(validationResult.stdout);

  assert.equal(validationResult.status, 1);
  assert.equal(validation.status, "invalid");
  assert.ok(
    validation.issues.some((issue) => issue.issue === "worksheet_auto_filter_conflicts_with_table"),
    "expected duplicate worksheet AutoFilter issue"
  );
});

test("Stingray generator uses the hardened workbook save path", () => {
  assert.match(generatorSource, /save_workbook_safely/);
  assert.match(fs.readFileSync("scripts/corvette_form_generator/workbook.py", "utf8"), /remove_table_sheet_auto_filters/);
  assert.doesNotMatch(generatorSource, /\bwb\.save\(WORKBOOK_PATH\)/);
});

test("generated JSON and static app data stay synchronized apart from timestamp", () => {
  assert.deepEqual(withoutGeneratedAt(appData), withoutGeneratedAt(jsonData));
});

test("Stingray generated contract keeps the closed-out shape", () => {
  assert.equal(jsonData.dataset.name, "2027 Corvette Stingray operational form");
  assert.deepEqual(
    jsonData.variants.map((variant) => variant.variant_id),
    ["1lt_c07", "2lt_c07", "3lt_c07", "1lt_c67", "2lt_c67", "3lt_c67"]
  );
  assert.equal(jsonData.variants.length, 6);
  assert.equal(jsonData.contextChoices.length, 8);
  assert.equal(jsonData.choices.length, 1464);
  assert.equal(jsonData.standardEquipment.length, 467);
  assert.equal(jsonData.rules.length, 238);
  assert.equal(jsonData.priceRules.length, 42);
  assert.equal(jsonData.interiors.length, 130);
  assert.equal(jsonData.validation.filter((row) => row.severity === "error").length, 0);
});

test("model option source sheets use the same normalized contract", () => {
  assert.deepEqual(workbookHeaders("stingray_options"), optionSourceHeaders);
  assert.deepEqual(workbookHeaders("grandSport_options"), optionSourceHeaders);
  assert.deepEqual(workbookHeaders("stingray_ovs"), optionVariantStatusHeaders);
  assert.deepEqual(workbookHeaders("grandSport_ovs"), optionVariantStatusHeaders);
  assertOptionVariantStatusCoverage("stingray_options", "stingray_ovs", stingrayVariantIds);
  assertOptionVariantStatusCoverage("grandSport_options", "grandSport_ovs", grandSportVariantIds);
});

test("section_master owns section step placement without category", () => {
  assert.deepEqual(workbookHeaders("section_master"), sectionMasterHeaders);
  for (const row of workbookRows("section_master")) {
    assert.ok(row.step_key, `${row.section_id} is missing step_key`);
    assert.ok(sectionStepKeys.has(row.step_key), `${row.section_id} has invalid step_key ${row.step_key}`);
    assert.equal(Object.hasOwn(row, "category"), false);
  }
});

test("Grand Sport draft rule source sheets use workbook-backed contracts", () => {
  assert.deepEqual(workbookHeaders("grandSport_rule_mapping"), ruleMappingHeaders);
  assert.deepEqual(workbookHeaders("price_rules"), priceRuleHeaders);
  assert.deepEqual(workbookHeaders("grandSport_price_rules"), priceRuleHeaders);
  assert.deepEqual(workbookHeaders("grandSport_rule_groups"), [
    "group_id",
    "group_type",
    "source_id",
    "body_style_scope",
    "trim_level_scope",
    "variant_scope",
    "disabled_reason",
    "active",
    "notes",
  ]);
  assert.deepEqual(workbookHeaders("grandSport_rule_group_members"), ["group_id", "target_id", "display_order", "active"]);
  assert.deepEqual(workbookHeaders("grandSport_exclusive_groups"), ["group_id", "selection_mode", "active", "notes"]);
  assert.deepEqual(workbookHeaders("grandSport_exclusive_members"), ["group_id", "option_id", "display_order", "active"]);
  assert.ok(workbookRows("grandSport_rule_mapping").length > 0);
  const grandSportPriceRuleIds = new Set(workbookRows("grandSport_price_rules").map((row) => row.price_rule_id));
  assert.equal(grandSportPriceRuleIds.size >= requiredGrandSportPriceRuleIds.length, true);
  for (const priceRuleId of requiredGrandSportPriceRuleIds) {
    assert.ok(grandSportPriceRuleIds.has(priceRuleId), `${priceRuleId} should remain authored in grandSport_price_rules`);
  }
  assert.ok(workbookRows("grandSport_exclusive_groups").length > 0);
});

test("generator-owned compatibility groups are authored in workbook source sheets", () => {
  assert.deepEqual(workbookHeaders("rule_groups"), [
    "group_id",
    "group_type",
    "source_id",
    "body_style_scope",
    "trim_level_scope",
    "variant_scope",
    "disabled_reason",
    "active",
    "notes",
  ]);
  assert.deepEqual(workbookHeaders("rule_group_members"), ["group_id", "target_id", "display_order", "active"]);
  assert.deepEqual(workbookHeaders("exclusive_groups"), ["group_id", "selection_mode", "active", "notes"]);
  assert.deepEqual(workbookHeaders("exclusive_group_members"), ["group_id", "option_id", "display_order", "active"]);
  assert.doesNotMatch(generatorSource, /^RULE_GROUPS = \[/m);
  assert.doesNotMatch(generatorSource, /^EXCLUSIVE_GROUPS = \[/m);
  assert.doesNotMatch(generatorSource, /^FIVE_V7_OR_REQUIREMENT_TARGET_IDS = /m);
  assert.doesNotMatch(generatorSource, /^FIVE_ZU_OR_REQUIREMENT_TARGET_IDS = /m);
  assert.doesNotMatch(generatorSource, /^T0A_REPLACEMENT_OPTION_IDS = /m);
  assert.doesNotMatch(generatorSource, /^def rule_body_style_scope\(/m);
});
