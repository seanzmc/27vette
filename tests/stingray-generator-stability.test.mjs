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
const generatorSource = fs.readFileSync("scripts/corvette_form_generator/production.py", "utf8");
const generateFormSource = fs.readFileSync("scripts/generate_form.py", "utf8");
const runtimeMetadataSource = fs.readFileSync("scripts/corvette_form_generator/runtime_metadata.py", "utf8");
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
  "original_detail_raw",
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
  "notes",
];
const interiorComponentHeaders = [
  "model_key",
  "interior_id",
  "rpo",
  "component_type",
  "label",
  "price_ref_type",
  "price_ref_code",
  "price_trim_scope",
  "display_order",
  "active",
  "notes",
];
const modelInteriorScopeHeaders = [
  "model_key",
  "interior_id",
  "trim_level",
  "active",
  "requires_option_id",
  "notes",
  "interior_seat_label",
  "interior_color_family",
  "interior_material_family",
  "interior_variant_label",
  "interior_group_display_order",
  "interior_material_display_order",
  "interior_choice_display_order",
  "interior_hierarchy_levels",
  "interior_parent_group_label",
  "interior_leaf_label",
  "interior_reference_order",
  "grouping_source",
];
const runtimeStepHeaders = ["model_key", "step_key", "step_label", "runtime_order", "source", "active", "notes"];
const contextSectionHeaders = [
  "model_key",
  "context_type",
  "section_id",
  "section_name",
  "selection_mode",
  "choice_mode",
  "is_required",
  "standard_behavior",
  "section_display_order",
  "step_key",
  "step_label",
  "active",
  "notes",
];
const sectionPresentationHeaders = [
  "model_key",
  "section_id",
  "display_label",
  "step_key",
  "display_behavior",
  "section_display_order",
  "standard_equipment_bucket",
  "standard_equipment_group_type",
  "active",
  "notes",
];
const expectedRuntimeStepKeys = [
  "body_style",
  "trim_level",
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
  "summary",
];
const expectedStandardSectionIds = [
  "sec_1lte_001",
  "sec_2lte_001",
  "sec_3lte_001",
  "sec_incl_001",
  "sec_safe_001",
  "sec_stan_001",
  "sec_stan_002",
  "sec_tech_001",
];
const expectedOrderSummarySections = [
  ["vehicle", "Model", 1],
  ["exterior_paint", "Exterior Paint", 2],
  ["exterior_appearance", "Exterior Appearance", 3],
  ["wheels_brakes", "Wheels & Brakes", 4],
  ["performance_mechanical", "Performance & Mechanical", 5],
  ["stripes", "Stripes", 6],
  ["seats_interior", "Seats & Interior", 7],
  ["accessories", "Accessories", 8],
  ["delivery", "Delivery", 9],
  ["auto_added_required", "Auto-Added / Required", 10],
  ["pricing_summary", "Pricing Summary", 11],
];
const expectedZ06OrderSummarySections = [
  ...expectedOrderSummarySections,
  ["required_charges", "Required Charges", 15],
];
const expectedStepOrderSummaryMap = [
  ["body_style", "vehicle"],
  ["trim_level", "vehicle"],
  ["paint", "exterior_paint"],
  ["exterior_appearance", "exterior_appearance"],
  ["wheels", "wheels_brakes"],
  ["packages_performance", "performance_mechanical"],
  ["aero_exhaust_stripes_accessories", "stripes"],
  ["seat", "seats_interior"],
  ["base_interior", "seats_interior"],
  ["seat_belt", "seats_interior"],
  ["interior_trim", "seats_interior"],
  ["accessories", "accessories"],
  ["delivery", "delivery"],
];
const expectedZ06StepOrderSummaryMap = [
  ...expectedStepOrderSummaryMap,
  ["standard_equipment", "required_charges"],
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

function workbookRows(sheetName, { optional = false } = {}) {
  const output = execFileSync(
    ".venv/bin/python",
    [
      "-c",
      [
        "import json",
        "from openpyxl import load_workbook",
        "wb = load_workbook('stingray_master.xlsx', read_only=True, data_only=True)",
        `optional = ${optional ? "True" : "False"}`,
        `sheet_name = '${sheetName}'`,
        "if sheet_name not in wb.sheetnames:",
        "    if optional:",
        "        print(json.dumps([]))",
        "        raise SystemExit(0)",
        "    raise KeyError(sheet_name)",
        `ws = wb['${sheetName}']`,
        "headers = [ws.cell(1, col).value for col in range(1, ws.max_column + 1)]",
        "rows = []",
        "def legacy_value(value):",
        "    return 'True' if value is True else 'False' if value is False else value",
        "for raw in ws.iter_rows(min_row=2, values_only=True):",
        "    record = {header: legacy_value(value) for header, value in zip(headers, raw) if header and value is not None}",
        "    if record:",
        "        rows.append(record)",
        "print(json.dumps(rows))",
      ].join("\n"),
    ],
    { encoding: "utf8" }
  );
  return JSON.parse(output);
}

function promotedRuntimeModelKeys() {
  return workbookRows("model_registry_promotion")
    .filter((row) => row.active === "True" && row.promoted_to_runtime === "True")
    .map((row) => row.model_key)
    .sort();
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
        "with ZipFile(path, 'r') as probe:",
        "    target_sheet = next(name for name in probe.namelist() if name.startswith('xl/worksheets/sheet') and b'<tableParts' in probe.read(name))",
        "with ZipFile(path, 'r') as source, ZipFile(tmp, 'w', ZIP_DEFLATED) as target:",
        "    for item in source.infolist():",
        "        data = source.read(item.filename)",
        "        if item.filename == target_sheet:",
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

test("Stingray generator no longer performs routine workbook generated-sheet writes", () => {
  assert.doesNotMatch(generatorSource, /save_workbook_safely/);
  assert.doesNotMatch(generatorSource, /write_sheet\(/);
  assert.doesNotMatch(generatorSource, /workbook_backup_path/);
  assert.match(generatorSource, /"workbook_backup": None/);
  assert.doesNotMatch(generatorSource, /\bwb\.save\(WORKBOOK_PATH\)/);
  assert.doesNotMatch(generatorSource, /write_app_data_registry/);
});

test("generate_form model discovery is workbook-owned, not a hardcoded active-model map", () => {
  assert.doesNotMatch(generateFormSource, /MODEL_CONFIGS\s*[:=]/);
  assert.doesNotMatch(generateFormSource, /choices\s*=\s*sorted\(MODEL_CONFIGS\)/);
  assert.doesNotMatch(generateFormSource, /STINGRAY_MODEL|GRAND_SPORT_MODEL|Z06_MODEL/);
  assert.match(generateFormSource, /discover_generation_model_configs/);
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
  assert.equal(jsonData.choices.length, 1416);
  assert.equal(jsonData.standardEquipment.length, 467);
  assert.equal(jsonData.rules.length, 145);
  assert.equal(jsonData.priceRules.length, 49);
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

test("Stingray production applies model-scoped variant override section placement generically", () => {
  const tempDir = fs.mkdtempSync(path.join(os.tmpdir(), "vette-stingray-variant-override-"));
  const workbookCopy = path.join(tempDir, "stingray-variant-override.xlsx");
  fs.copyFileSync("stingray_master.xlsx", workbookCopy);

  const output = execFileSync(
    ".venv/bin/python",
    [
      "-c",
      String.raw`
import json
import sys
from pathlib import Path
from openpyxl import load_workbook

workbook_path = Path(sys.argv[1])
wb = load_workbook(workbook_path)

if "variant_option_overrides" in wb.sheetnames:
    global_sheet = wb["variant_option_overrides"]
else:
    global_sheet = wb.create_sheet("variant_option_overrides")
    global_sheet.append(["model_key", "option_id", "variant_id", "status", "selectable", "active", "display_behavior", "notes"])
if global_sheet.max_row > 1:
    global_sheet.delete_rows(2, global_sheet.max_row - 1)
global_sheet.append(["stingray", "opt_uqt_002", "2lt_c07", "unavailable", "False", "False", "", "Global row should not shadow model-scoped override."])

for sheet_name in ["stingray_options", "stingray_ovs"]:
    sheet = wb[sheet_name]
    for row_idx in range(sheet.max_row, 1, -1):
        if sheet.cell(row_idx, 1).value == "opt_uqt_001":
            sheet.delete_rows(row_idx, 1)

if "stingray_variant_overrides" in wb.sheetnames:
    del wb["stingray_variant_overrides"]
variant_sheet = wb.create_sheet("stingray_variant_overrides")
variant_sheet.append(["option_id", "variant_id", "selectable", "display_behavior", "section_id", "active", "note"])
variant_sheet.append(["opt_uqt_002", "2lt_c07", "False", "display_only", "sec_2lte_001", "True", "Test display-only trim placement."])

sources = wb["model_workbook_sources"]
headers = [sources.cell(1, col).value for col in range(1, sources.max_column + 1)]
source_cols = {header: index + 1 for index, header in enumerate(headers)}
source_row = None
for row_idx in range(2, sources.max_row + 1):
    if sources.cell(row_idx, source_cols["model_key"]).value == "stingray" and sources.cell(row_idx, source_cols["source_role"]).value == "variant_option_overrides_sheet":
        source_row = row_idx
        break
if source_row is None:
    sources.append(["stingray", "variant_option_overrides_sheet", "stingray_variant_overrides", True, "Test model-scoped Stingray override sheet."])
else:
    sources.cell(source_row, source_cols["sheet_name"]).value = "stingray_variant_overrides"
    sources.cell(source_row, source_cols["active"]).value = True
wb.save(workbook_path)

sys.path.insert(0, "scripts")
from corvette_form_generator import production

production.WORKBOOK_PATH = workbook_path
data = production.build_production_source_data()
choice = next(row for row in data["choices"] if row["choice_id"] == "2lt_c07__opt_uqt_002")
standard = next((row for row in data["standardEquipment"] if row["equipment_id"] == "std_2lt_c07__opt_uqt_002"), None)
print(json.dumps({
    "status": choice.get("status"),
    "selectable": choice.get("selectable"),
    "active": choice.get("active"),
    "display_behavior": choice.get("display_behavior"),
    "section_id": choice.get("section_id"),
    "step_key": choice.get("step_key"),
    "standard_equipment_group_type": choice.get("standard_equipment_group_type"),
    "standard_equipment_present": standard is not None,
}))
      `,
      workbookCopy,
    ],
    { encoding: "utf8" }
  );

  assert.deepEqual(JSON.parse(output), {
    status: "standard",
    selectable: "False",
    active: "True",
    display_behavior: "display_only",
    section_id: "sec_2lte_001",
    step_key: "standard_equipment",
    standard_equipment_group_type: "trim_equipment",
    standard_equipment_present: true,
  });
});

test("Stingray Phase 4 availability rules are workbook-owned", () => {
  const activeGlobalOverrideSources = workbookRows("model_workbook_sources").filter(
    (row) =>
      row.active === "True" &&
      row.source_role === "variant_option_overrides_sheet" &&
      row.sheet_name === "variant_option_overrides"
  );
  assert.equal(activeGlobalOverrideSources.length, 0, "active models should not point at the retired global variant_option_overrides sheet");

  const uqtOverrides = workbookRows("variant_option_overrides", { optional: true }).filter(
    (row) => row.model_key === "stingray" && row.option_id === "opt_uqt_002"
  );
  assert.equal(uqtOverrides.length, 0, "Stingray UQT should no longer depend on global emitted-value overrides");

  const stingrayVariantOverrides = workbookRows("stingray_variant_overrides").filter(
    (row) => row.option_id === "opt_uqt_002"
  );
  assert.deepEqual(
    stingrayVariantOverrides.map((row) => row.variant_id).sort(),
    ["2lt_c07", "2lt_c67", "3lt_c07", "3lt_c67"]
  );
  assert.equal(
    stingrayVariantOverrides.every(
      (row) =>
        row.selectable === "False" &&
        row.active === "True" &&
        row.display_behavior === "display_only" &&
        ["sec_2lte_001", "sec_3lte_001"].includes(row.section_id)
    ),
    true
  );

  const uqtChoices = jsonData.choices.filter((choice) => choice.option_id === "opt_uqt_002");
  assert.equal(uqtChoices.length, 6);
  assert.equal(
    uqtChoices
      .filter((choice) => choice.trim_level === "1LT")
      .every((choice) => choice.status === "available" && choice.selectable === "True" && choice.step_key === "interior_trim"),
    true
  );
  assert.equal(
    uqtChoices
      .filter((choice) => choice.trim_level !== "1LT")
      .every(
        (choice) =>
          choice.status === "standard" &&
          choice.selectable === "False" &&
          choice.display_behavior === "display_only" &&
          choice.step_key === "standard_equipment"
      ),
    true
  );

  const bc7Overrides = workbookRows("variant_option_overrides", { optional: true }).filter(
    (row) => row.model_key === "stingray" && row.option_id === "opt_bc7_001"
  );
  assert.equal(bc7Overrides.length, 0, "Stingray BC7 default-selected display metadata should derive from default rules");
  const coupeBc7Defaults = jsonData.choices.filter((choice) => choice.option_id === "opt_bc7_001" && choice.body_style === "coupe");
  assert.equal(coupeBc7Defaults.length, 3);
  assert.equal(coupeBc7Defaults.every((choice) => choice.status === "standard" && choice.display_behavior === "default_selected"), true);
  const stingrayNgaDefaults = jsonData.choices.filter((choice) => choice.option_id === "opt_nga_001");
  assert.equal(stingrayNgaDefaults.length, 6);
  assert.equal(stingrayNgaDefaults.every((choice) => choice.display_behavior !== "default_selected"), true);

  const stitchPresentation = workbookRows("section_presentation").find(
    (row) => row.model_key === "stingray" && row.section_id === "sec_cust_002" && row.active === "True"
  );
  assert.equal(stitchPresentation, undefined, "Stingray custom-stitch suppression should no longer require source option rows");

  const r6xInteriors = workbookRows("lt_interiors").filter(
    (row) => row.active_for_stingray === "True" && row.requires_r6x === "True"
  );
  assert.ok(r6xInteriors.length > 0, "expected active Stingray R6X interiors");
  assert.equal(r6xInteriors.every((row) => row.included_option_id === "opt_r6x_001"), true);

  assert.match(generatorSource, /load_variant_option_overrides/);
  assert.match(generatorSource, /load_section_presentation/);
  assert.doesNotMatch(runtimeMetadataSource, /optional_rows\(wb, ["']variant_option_overrides["']\)/);
  assert.doesNotMatch(generatorSource, /option_id\s*==\s*["']opt_uqt_002["']/);
  assert.doesNotMatch(generatorSource, /HIDDEN_SECTION_IDS/);
  assert.doesNotMatch(generatorSource, /opt_r6x_001["']\s+if\s+active_for_stingray\s+and\s+requires_r6x/);
  assert.match(generatorSource, /missing_r6x_included_option_/);
});

test("Stingray Phase 5 interior components are workbook-owned", () => {
  assert.deepEqual(workbookHeaders("interior_components"), interiorComponentHeaders);
  assert.deepEqual(workbookHeaders("model_interior_scope"), modelInteriorScopeHeaders);

  const activeComponents = workbookRows("interior_components").filter(
    (row) => row.model_key === "stingray" && row.active === "True"
  );
  assert.ok(activeComponents.length > 0, "expected active Stingray interior component rows");
  assert.equal(
    new Set(activeComponents.map((row) => `${row.model_key}::${row.interior_id}::${row.rpo}::${row.component_type}`)).size,
    activeComponents.length,
    "active Stingray interior component keys should be unique"
  );
  for (const row of activeComponents) {
    assert.ok(row.interior_id, "active component row should include interior_id");
    assert.ok(row.rpo, "active component row should include rpo");
    assert.ok(row.component_type, "active component row should include component_type");
    assert.ok(row.label, "active component row should include label");
    assert.ok(row.price_ref_type, `${row.interior_id} ${row.rpo} should include price_ref_type`);
    assert.ok(row.price_ref_code, `${row.interior_id} ${row.rpo} should include price_ref_code`);
  }

  const componentsByInterior = new Map();
  for (const row of activeComponents) {
    const rows = componentsByInterior.get(row.interior_id) || [];
    rows.push(row);
    componentsByInterior.set(row.interior_id, rows);
  }
  const activeGeneratedInteriors = jsonData.interiors.filter((interior) => interior.active_for_stingray === true);
  const componentBearingInteriors = activeGeneratedInteriors.filter((interior) => interior.interior_components.length > 0);
  assert.ok(componentBearingInteriors.length > 0, "expected component-bearing generated interiors");
  for (const interior of componentBearingInteriors) {
    const workbookRowsForInterior = componentsByInterior.get(interior.interior_id) || [];
    assert.ok(workbookRowsForInterior.length > 0, `${interior.interior_id} should have active workbook component rows`);
    const workbookLabels = new Map(workbookRowsForInterior.map((row) => [`${row.rpo}::${row.component_type}`, row.label]));
    for (const component of interior.interior_components) {
      assert.equal(
        component.label,
        workbookLabels.get(`${component.rpo}::${component.component_type}`),
        `${interior.interior_id} ${component.rpo} label should come from interior_components`
      );
    }
  }

  assert.match(generatorSource, /build_model_interiors\(MODEL_CONFIG\)/);
  assert.doesNotMatch(generatorSource, /workbook_interior_component_metadata/);
  assert.doesNotMatch(generatorSource, /missing_workbook_components_/);
});

test("section_master owns section step placement without category", () => {
  assert.deepEqual(workbookHeaders("section_master"), sectionMasterHeaders);
  for (const row of workbookRows("section_master")) {
    assert.ok(row.step_key, `${row.section_id} is missing step_key`);
    assert.ok(sectionStepKeys.has(row.step_key), `${row.section_id} has invalid step_key ${row.step_key}`);
    assert.equal(Object.hasOwn(row, "category"), false);
  }
});

test("Phase 6 step and presentation metadata are workbook-owned", () => {
  assert.deepEqual(workbookHeaders("runtime_steps"), runtimeStepHeaders);
  assert.deepEqual(workbookHeaders("context_section_master"), contextSectionHeaders);
  assert.deepEqual(workbookHeaders("section_presentation"), sectionPresentationHeaders);

  const promotedModels = promotedRuntimeModelKeys();
  assert.deepEqual(promotedModels, ["grand_sport", "stingray", "z06"]);

  for (const modelKey of promotedModels) {
    const runtimeRows = workbookRows("runtime_steps")
      .filter((row) => row.model_key === modelKey && row.active === "True")
      .sort((a, b) => Number(a.runtime_order) - Number(b.runtime_order));
    assert.deepEqual(runtimeRows.map((row) => row.step_key), expectedRuntimeStepKeys, `${modelKey} runtime_steps should own current step order`);

    const contextRows = workbookRows("context_section_master").filter((row) => row.model_key === modelKey && row.active === "True");
    assert.deepEqual(
      contextRows.map((row) => row.section_id).sort(),
      ["sec_context_body_style", "sec_context_trim_level"],
      `${modelKey} context sections should be workbook-owned`
    );

    const summaryRows = workbookRows("order_summary_sections")
      .filter((row) => row.model_key === modelKey && row.active === "True")
      .sort((a, b) => Number(a.display_order) - Number(b.display_order));
    const expectedSummarySections = modelKey === "z06" ? expectedZ06OrderSummarySections : expectedOrderSummarySections;
    assert.deepEqual(
      summaryRows.map((row) => [row.section_key, row.section_label, Number(row.display_order)]),
      expectedSummarySections,
      `${modelKey} order summary sections should be workbook-owned`
    );

    const expectedStepMap = modelKey === "z06" ? expectedZ06StepOrderSummaryMap : expectedStepOrderSummaryMap;
    const stepSummaryRows = workbookRows("step_order_summary_map")
      .filter((row) => row.model_key === modelKey && row.active === "True")
      .sort((a, b) => expectedStepMap.findIndex(([stepKey]) => stepKey === a.step_key) - expectedStepMap.findIndex(([stepKey]) => stepKey === b.step_key));
    assert.deepEqual(
      stepSummaryRows.map((row) => [row.step_key, row.section_key]),
      expectedStepMap,
      `${modelKey} step-to-summary map should be workbook-owned`
    );

    const standardRows = workbookRows("section_presentation").filter(
      (row) => row.model_key === modelKey && row.active === "True" && row.standard_equipment_bucket === "True"
    );
    assert.deepEqual(
      standardRows.map((row) => row.section_id).sort(),
      expectedStandardSectionIds,
      `${modelKey} standard-equipment buckets should be workbook-owned`
    );
    assert.deepEqual(
      standardRows.filter((row) => row.standard_equipment_group_type === "trim_equipment").map((row) => row.section_id).sort(),
      ["sec_1lte_001", "sec_2lte_001", "sec_3lte_001"],
      `${modelKey} trim-equipment grouping should be workbook-owned`
    );
  }

  const presentationByKey = new Map(workbookRows("section_presentation").map((row) => [`${row.model_key}::${row.section_id}`, row]));
  assert.equal(presentationByKey.get("stingray::sec_stri_001")?.section_display_order, 30);
  assert.equal(presentationByKey.get("stingray::sec_gsha_001")?.section_display_order, 50);
  assert.equal(presentationByKey.get("stingray::sec_gsce_001")?.section_display_order, 51);
  assert.equal(presentationByKey.get("grand_sport::sec_gsce_001")?.display_label, "Grand Sport Center Stripes");
  assert.equal(presentationByKey.get("grand_sport::sec_gsha_001")?.display_label, "Grand Sport Heritage Hash Marks");
  assert.equal(presentationByKey.get("grand_sport::sec_spec_001")?.display_label, "Special Edition");
  assert.equal(presentationByKey.get("grand_sport::sec_colo_001")?.display_label, "Color Combination Override");

  assert.match(generatorSource, /load_runtime_steps/);
  assert.match(generatorSource, /load_context_sections/);
  assert.match(generatorSource, /standard_equipment_group_type/);
  assert.doesNotMatch(generatorSource, /STINGRAY_SECTION_DISPLAY_ORDER_OVERRIDES\s*=\s*\{/);
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
