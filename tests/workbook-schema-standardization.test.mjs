import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import fs from "node:fs";
import test from "node:test";

function pythonJson(source) {
  const output = execFileSync(".venv/bin/python", ["-c", source], { encoding: "utf8" });
  return JSON.parse(output);
}

function workbookSnapshot() {
  return pythonJson(`
import json
from openpyxl import load_workbook
wb = load_workbook('stingray_master.xlsx', read_only=True, data_only=True)

def headers(sheet):
    ws = wb[sheet]
    return [ws.cell(1, col).value for col in range(1, ws.max_column + 1) if ws.cell(1, col).value]

def column_values(sheet, column):
    ws = wb[sheet]
    header_row = [ws.cell(1, col).value for col in range(1, ws.max_column + 1)]
    idx = header_row.index(column) + 1
    return [ws.cell(row, idx).value for row in range(2, ws.max_row + 1) if ws.cell(row, idx).value is not None]

def records(sheet):
    ws = wb[sheet]
    header_row = [ws.cell(1, col).value for col in range(1, ws.max_column + 1)]
    rows = []
    for raw in ws.iter_rows(min_row=2, values_only=True):
        record = {header: value for header, value in zip(header_row, raw) if header and value is not None}
        if record:
            rows.append(record)
    return rows

def sheet_details(sheet):
    if sheet not in wb.sheetnames:
        return {'exists': False, 'headers': [], 'max_row': 0, 'state': None}
    ws = wb[sheet]
    return {'exists': True, 'headers': headers(sheet), 'max_row': ws.max_row, 'state': ws.sheet_state}

canonical_source_sheets = {
    'options': 'grandSport_options',
    'ovs': 'grandSport_ovs',
    'rule_mapping': 'grandSport_rule_mapping',
    'price_rules': 'grandSport_price_rules',
    'rule_groups': 'grandSport_rule_groups',
    'rule_group_members': 'grandSport_rule_group_members',
    'exclusive_groups': 'grandSport_exclusive_groups',
    'exclusive_members': 'grandSport_exclusive_members',
    'variant_overrides': 'grandSport_variant_overrides',
}
future_source_sheets = [
    'z06_options', 'z06_ovs', 'z06_rule_mapping', 'z06_price_rules', 'z06_rule_groups',
    'z06_rule_group_members', 'z06_exclusive_groups', 'z06_exclusive_members', 'z06_variant_overrides',
    'zr1_options', 'zr1_ovs', 'zr1_rule_mapping', 'zr1_price_rules', 'zr1_rule_groups',
    'zr1_rule_group_members', 'zr1_exclusive_groups', 'zr1_exclusive_members', 'zr1_variant_overrides',
    'zr1x_options', 'zr1x_ovs', 'zr1x_rule_mapping', 'zr1x_price_rules', 'zr1x_rule_groups',
    'zr1x_rule_group_members', 'zr1x_exclusive_groups', 'zr1x_exclusive_members', 'zr1x_variant_overrides',
]

payload = {
    'sheetnames': wb.sheetnames,
    'lt_headers': headers('lt_interiors'),
    'lz_headers': headers('LZ_Interiors'),
    'stingray_rpos': column_values('stingray_options', 'rpo'),
    'grand_sport_rpos': column_values('grandSport_options', 'rpo'),
    'price_ref_prices': column_values('PriceRef', 'Price'),
    'lt_interior_prices': column_values('lt_interiors', 'Price'),
    'lz_interior_prices': column_values('LZ_Interiors', 'Price'),
    'grand_sport_selectable': column_values('grandSport_options', 'selectable'),
    'grand_sport_variant_active': column_values('grandSport_variant_overrides', 'active'),
    'grand_sport_variant_selectable': column_values('grandSport_variant_overrides', 'selectable'),
    'rule_mapping_rows': records('rule_mapping'),
    'grand_sport_rule_mapping_rows': records('grandSport_rule_mapping'),
    'model_master_rows': records('model_master'),
    'model_variant_rows': records('model_variants'),
    'model_source_rows': records('model_workbook_sources'),
    'canonical_source_headers': {role: headers(sheet) for role, sheet in canonical_source_sheets.items()},
    'future_source_sheet_details': {sheet: sheet_details(sheet) for sheet in future_source_sheets},
}
print(json.dumps(payload))
`);
}

function liveRegistry() {
  const source = fs.readFileSync("form-app/data.js", "utf8");
  const json = source
    .split("window.CORVETTE_FORM_DATA = ", 2)[1]
    .split(";\nwindow.STINGRAY_FORM_DATA", 1)[0];
  return JSON.parse(json);
}

const snapshot = workbookSnapshot();

test("schema validation CLI accepts the standardized workbook and live app contract", () => {
  const output = execFileSync(".venv/bin/python", ["scripts/validate_workbook_schema.py", "stingray_master.xlsx"], {
    encoding: "utf8",
  });
  const result = JSON.parse(output);
  assert.equal(result.status, "valid");
  assert.equal(result.error_count, 0);
  assert.deepEqual(result.issues, []);
});

test("workbook primitive cells use canonical raw Excel types", () => {
  const numericLookingRpos = new Set(["379", "719"]);
  assert.equal(snapshot.stingray_rpos.filter((value) => numericLookingRpos.has(value)).length >= 3, true);
  assert.equal(snapshot.grand_sport_rpos.filter((value) => numericLookingRpos.has(value)).length >= 3, true);
  assert.equal(snapshot.stingray_rpos.every((value) => typeof value === "string"), true);
  assert.equal(snapshot.grand_sport_rpos.every((value) => typeof value === "string"), true);

  assert.equal(snapshot.grand_sport_selectable.every((value) => typeof value === "boolean"), true);
  assert.equal(snapshot.grand_sport_variant_active.every((value) => typeof value === "boolean"), true);
  assert.equal(snapshot.grand_sport_variant_selectable.every((value) => typeof value === "boolean"), true);

  assert.equal(snapshot.price_ref_prices.every((value) => typeof value === "number"), true);
  assert.equal(snapshot.lt_interior_prices.every((value) => typeof value === "number"), true);
  assert.equal(snapshot.lz_interior_prices.every((value) => typeof value === "number"), true);
});

test("LZ_Interiors is schema-compatible but not read by Stingray generation", () => {
  assert.deepEqual(snapshot.lz_headers, snapshot.lt_headers);
  const registry = liveRegistry();
  const stingrayInteriors = registry.models.stingray.data.interiors;
  assert.equal(stingrayInteriors.some((interior) => interior.source_sheet === "LZ_Interiors"), false);
  assert.equal(stingrayInteriors.some((interior) => interior.interior_id === "3LT_AH2_EL9"), false);
});

test("future Corvette model metadata is scaffolded against shared LZ interiors", () => {
  const expectedModels = {
    z06: { label: "Z06", registryKey: "z06", variantCount: 6, active: true },
    zr1: { label: "ZR1", registryKey: "zr1", variantCount: 4 },
    zr1x: { label: "ZR1X", registryKey: "zr1x", variantCount: 4 },
  };
  const expectedVariants = {
    z06: ["1lz_h07", "2lz_h07", "3lz_h07", "1lz_h67", "2lz_h67", "3lz_h67"],
    zr1: ["1lz_r07", "3lz_r07", "1lz_r67", "3lz_r67"],
    zr1x: ["1lz_s07", "3lz_s07", "1lz_s67", "3lz_s67"],
  };
  const sourceSheetNames = {
    z06: {
      source_option_sheet: "z06_options",
      status_sheet: "z06_ovs",
      rule_mapping_sheet: "z06_rule_mapping",
      price_rules_sheet: "z06_price_rules",
      rule_groups_sheet: "z06_rule_groups",
      rule_group_members_sheet: "z06_rule_group_members",
      exclusive_groups_sheet: "z06_exclusive_groups",
      exclusive_group_members_sheet: "z06_exclusive_members",
      variant_option_overrides_sheet: "z06_variant_overrides",
      color_overrides_sheet: "color_overrides",
      interior_source_sheet: "LZ_Interiors",
    },
    zr1: {
      source_option_sheet: "zr1_options",
      status_sheet: "zr1_ovs",
      rule_mapping_sheet: "zr1_rule_mapping",
      price_rules_sheet: "zr1_price_rules",
      rule_groups_sheet: "zr1_rule_groups",
      rule_group_members_sheet: "zr1_rule_group_members",
      exclusive_groups_sheet: "zr1_exclusive_groups",
      exclusive_group_members_sheet: "zr1_exclusive_members",
      variant_option_overrides_sheet: "zr1_variant_overrides",
      color_overrides_sheet: "color_overrides",
      interior_source_sheet: "LZ_Interiors",
    },
    zr1x: {
      source_option_sheet: "zr1x_options",
      status_sheet: "zr1x_ovs",
      rule_mapping_sheet: "zr1x_rule_mapping",
      price_rules_sheet: "zr1x_price_rules",
      rule_groups_sheet: "zr1x_rule_groups",
      rule_group_members_sheet: "zr1x_rule_group_members",
      exclusive_groups_sheet: "zr1x_exclusive_groups",
      exclusive_group_members_sheet: "zr1x_exclusive_members",
      variant_option_overrides_sheet: "zr1x_variant_overrides",
      color_overrides_sheet: "color_overrides",
      interior_source_sheet: "LZ_Interiors",
    },
  };

  for (const [modelKey, expected] of Object.entries(expectedModels)) {
    const modelRow = snapshot.model_master_rows.find((row) => row.model_key === modelKey);
    assert.ok(modelRow, `${modelKey} missing model_master row`);
    assert.equal(modelRow.registry_key, expected.registryKey);
    assert.equal(modelRow.model_label, expected.label);
    assert.equal(modelRow.model_year, "2027");
    assert.equal(modelRow.expected_variant_count, expected.variantCount);
    assert.equal(modelRow.default_model, false);
    assert.equal(modelRow.active, expected.active ?? false);

    const variantRows = snapshot.model_variant_rows.filter((row) => row.model_key === modelKey);
    assert.deepEqual(
      variantRows.map((row) => row.variant_id),
      expectedVariants[modelKey],
    );
    assert.deepEqual(
      variantRows.map((row) => row.display_order),
      expectedVariants[modelKey].map((_, index) => index + 1),
    );
    assert.equal(variantRows.every((row) => row.active === false), true);

    const sourceRows = snapshot.model_source_rows.filter((row) => row.model_key === modelKey);
    assert.equal(sourceRows.length, Object.keys(sourceSheetNames[modelKey]).length);
    for (const [sourceRole, sheetName] of Object.entries(sourceSheetNames[modelKey])) {
      const sourceRow = sourceRows.find((row) => row.source_role === sourceRole);
      assert.ok(sourceRow, `${modelKey} missing ${sourceRole}`);
      assert.equal(sourceRow.sheet_name, sheetName);
      assert.equal(sourceRow.active, false, `${modelKey}.${sourceRole} should stay inactive`);
    }
  }
});

test("future Corvette normalized source sheets stay compatible and source rows stay inactive after approved source staging", () => {
  const roleBySuffix = {
    options: "options",
    ovs: "ovs",
    rule_mapping: "rule_mapping",
    price_rules: "price_rules",
    rule_groups: "rule_groups",
    rule_group_members: "rule_group_members",
    exclusive_groups: "exclusive_groups",
    exclusive_members: "exclusive_members",
    variant_overrides: "variant_overrides",
  };
  const expectedVariantCounts = { z06: 6, zr1: 4, zr1x: 4 };
  const expectedStagedRowCounts = {
    z06: {
      rule_mapping: 213,
      price_rules: 45,
      rule_groups: 4,
      rule_group_members: 11,
      exclusive_groups: 12,
      exclusive_members: 33,
      variant_overrides: 4,
    },
    zr1: {
      rule_mapping: 56,
      rule_groups: 0,
      rule_group_members: 0,
      exclusive_groups: 4,
      exclusive_members: 10,
    },
    zr1x: {
      rule_mapping: 56,
      rule_groups: 0,
      rule_group_members: 0,
      exclusive_groups: 4,
      exclusive_members: 10,
    },
  };

  for (const modelKey of ["z06", "zr1", "zr1x"]) {
    for (const [suffix, canonicalRole] of Object.entries(roleBySuffix)) {
      const sheetName = `${modelKey}_${suffix}`;
      const details = snapshot.future_source_sheet_details[sheetName];
      assert.ok(details, `${sheetName} missing from future source snapshot`);
      assert.equal(details.exists, true, `${sheetName} should exist`);
      assert.equal(details.state, "visible", `${sheetName} should be visible`);
      assert.deepEqual(details.headers, snapshot.canonical_source_headers[canonicalRole], `${sheetName} headers drifted`);
      if (!["options", "ovs"].includes(suffix)) {
        const expectedRows = expectedStagedRowCounts[modelKey]?.[suffix] ?? 0;
        assert.equal(details.max_row - 1, expectedRows, `${sheetName} staged row count drifted`);
      }
    }

    const optionRows = snapshot.future_source_sheet_details[`${modelKey}_options`].max_row - 1;
    const ovsRows = snapshot.future_source_sheet_details[`${modelKey}_ovs`].max_row - 1;
    assert.ok(optionRows >= 0, `${modelKey}_options should be readable`);
    assert.equal(
      ovsRows,
      optionRows * expectedVariantCounts[modelKey],
      `${modelKey}_ovs should have one status row per staged option and variant`,
    );
  }

  for (const row of snapshot.model_source_rows.filter((row) => ["z06", "zr1", "zr1x"].includes(row.model_key))) {
    assert.equal(row.active, false, `${row.model_key}.${row.source_role} should remain inactive after approved source staging`);
  }
});

test("rule lifecycle metadata keeps retained source rows auditable", () => {
  for (const [sheetName, rows] of [
    ["rule_mapping", snapshot.rule_mapping_rows],
    ["grandSport_rule_mapping", snapshot.grand_sport_rule_mapping_rows],
  ]) {
    assert.ok(rows.length > 0, `${sheetName} should have rule rows`);
    for (const row of rows) {
      assert.ok("normalization_status" in row, `${sheetName}.${row.rule_id} missing normalization_status`);
      if (String(row.generation_action || "").startsWith("omit")) {
        assert.ok(["omitted", "replaced"].includes(row.normalization_status), `${sheetName}.${row.rule_id} bad status`);
        assert.ok(row.normalization_reason, `${sheetName}.${row.rule_id} missing reason`);
      }
    }
  }
});

test("active explicit excludes do not duplicate active exclusive-group peers", () => {
  const duplicates = pythonJson(`
import json
from collections import defaultdict
from openpyxl import load_workbook

wb = load_workbook('stingray_master.xlsx', read_only=True, data_only=True)

def clean(value):
    return '' if value is None else str(value).strip()

def rows(sheet):
    ws = wb[sheet]
    raw_rows = list(ws.iter_rows(values_only=True))
    headers = [clean(value) for value in raw_rows[0]]
    result = []
    for row_number, raw in enumerate(raw_rows[1:], start=2):
        record = {header: raw[index] if index < len(raw) else '' for index, header in enumerate(headers) if header}
        if any(clean(value) for value in record.values()):
            record['_row'] = row_number
            result.append(record)
    return result

def active(row):
    value = clean(row.get('active'))
    return value.lower() not in {'false', '0', 'no', 'inactive'}

def runtime_authored_rule(row):
    status = clean(row.get('normalization_status')).lower()
    if status in {'omitted', 'replaced'}:
        return False
    if status == 'preserved':
        return True
    return not clean(row.get('generation_action')).lower().startswith('omit')

models = {
    'stingray': ('rule_mapping', 'exclusive_groups', 'exclusive_group_members'),
    'grandSport': ('grandSport_rule_mapping', 'grandSport_exclusive_groups', 'grandSport_exclusive_members'),
    'z06': ('z06_rule_mapping', 'z06_exclusive_groups', 'z06_exclusive_members'),
    'zr1': ('zr1_rule_mapping', 'zr1_exclusive_groups', 'zr1_exclusive_members'),
    'zr1x': ('zr1x_rule_mapping', 'zr1x_exclusive_groups', 'zr1x_exclusive_members'),
}

duplicates = []
for model_key, (rule_sheet, group_sheet, member_sheet) in models.items():
    active_group_ids = {clean(row.get('group_id')) for row in rows(group_sheet) if active(row)}
    group_by_option = {}
    for row in rows(member_sheet):
        if not active(row):
            continue
        group_id = clean(row.get('group_id'))
        option_id = clean(row.get('option_id'))
        if group_id in active_group_ids and option_id:
            group_by_option[option_id] = group_id
    for row in rows(rule_sheet):
        if not runtime_authored_rule(row) or clean(row.get('rule_type')) != 'excludes':
            continue
        source_id = clean(row.get('source_id'))
        target_id = clean(row.get('target_id'))
        source_group = group_by_option.get(source_id)
        if not source_group or source_group != group_by_option.get(target_id):
            continue
        if clean(row.get('runtime_action')) == 'replace':
            continue
        if clean(row.get('generation_action')) == 'preserve_runtime_exclude':
            continue
        duplicates.append({
            'model': model_key,
            'sheet': rule_sheet,
            'row': row['_row'],
            'rule_id': clean(row.get('rule_id')),
            'group_id': source_group,
            'source_id': source_id,
            'target_id': target_id,
        })

wb.close()
print(json.dumps(duplicates))
`);
  assert.deepEqual(duplicates, []);
});

test("category_master is retired from the active source graph and draft provenance is not live app data", () => {
  assert.equal(snapshot.sheetnames.includes("category_master"), false);
  assert.equal(snapshot.sheetnames.includes("archive_category_master"), true);

  const registry = liveRegistry();
  for (const [modelKey, entry] of Object.entries(registry.models)) {
    assert.equal("draftMetadata" in entry.data, false, `${modelKey} leaked draftMetadata`);
    for (const choice of entry.data.choices) {
      assert.equal("source_option_name" in choice, false, `${modelKey} ${choice.choice_id} leaked source_option_name`);
      assert.equal("source_description" in choice, false, `${modelKey} ${choice.choice_id} leaked source_description`);
      assert.equal("text_cleanup_notes" in choice, false, `${modelKey} ${choice.choice_id} leaked text_cleanup_notes`);
    }
  }
});
