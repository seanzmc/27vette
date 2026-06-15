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
    'display_order_columns': {sheet: column_values(sheet, 'display_order') for sheet in [
        'stingray_options', 'grandSport_options', 'z06_options',
        'rule_group_members', 'exclusive_group_members',
        'grandSport_rule_group_members', 'grandSport_exclusive_members',
        'z06_rule_group_members', 'z06_exclusive_members']},
    'boolean_columns': {
        'asset_map.active': column_values('asset_map', 'active'),
        'default_selection_rules.active': column_values('default_selection_rules', 'active'),
        'order_summary_sections.active': column_values('order_summary_sections', 'active'),
        'rule_phrase_map.active': column_values('rule_phrase_map', 'active'),
        'rule_phrase_map.review_flag_default': column_values('rule_phrase_map', 'review_flag_default'),
        'runtime_rule_exceptions.active': column_values('runtime_rule_exceptions', 'active'),
        'section_master.is_required': column_values('section_master', 'is_required'),
        'step_order_summary_map.active': column_values('step_order_summary_map', 'active'),
    },
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
  // LZ_Interiors price-typing intentionally not asserted: future-model interior
  // scaffold, not read by live generation. Numeric-price guard kept on live sheets.

  // display_order must be numeric on every live option/member sheet (review
  // 2026-06-11 S-1/S-2; Z06 ingest-era string cells retyped 2026-06-12).
  for (const [sheet, values] of Object.entries(snapshot.display_order_columns)) {
    assert.equal(
      values.every((value) => typeof value === "number"),
      true,
      `${sheet}: display_order cells must be integer-typed, not text`,
    );
  }

  // Boolean-like metadata cells should be real Excel booleans, not text TRUE/FALSE.
  for (const [column, values] of Object.entries(snapshot.boolean_columns)) {
    assert.equal(
      values.every((value) => typeof value === "boolean"),
      true,
      `${column}: cells must be boolean-typed, not text`,
    );
  }
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
    // z06 is a live promoted runtime model; its model_variants and
    // model_workbook_sources rows are active. ZR1/ZR1X remain inactive scaffolds.
    const expectActive = expected.active ?? false;
    assert.equal(variantRows.every((row) => row.active === expectActive), true);

    const sourceRows = snapshot.model_source_rows.filter((row) => row.model_key === modelKey);
    assert.equal(sourceRows.length, Object.keys(sourceSheetNames[modelKey]).length);
    for (const [sourceRole, sheetName] of Object.entries(sourceSheetNames[modelKey])) {
      const sourceRow = sourceRows.find((row) => row.source_role === sourceRole);
      assert.ok(sourceRow, `${modelKey} missing ${sourceRole}`);
      assert.equal(sourceRow.sheet_name, sheetName);
      assert.equal(sourceRow.active, expectActive, `${modelKey}.${sourceRole} should match promotion state`);
    }
  }
});

// RETIRED: "future Corvette normalized source sheets stay compatible ..."
// This test enforced raw future-model staging row counts (e.g. z06_rule_mapping
// == 214) from the spent future-model ingest pipeline. Those counts were
// intentionally normalized down to the authored rule sets (z06_rule_mapping now
// 53 rows: 32 includes / 12 excludes / 9 requires) and z06 is now a live
// promoted model. z06 rule correctness is guarded by tests/z06-runtime-rule-
// corrections.test.mjs and tests/z06-performance-package-interactions.test.mjs.
// The future-staging scaffold (scripts + ingest modules) was removed in the
// pre-merge cleanup, so this stale-count guard is retired with it.

test("rule source sheets do not retain runtime-skipped lifecycle rows", () => {
  for (const [sheetName, rows] of [
    ["rule_mapping", snapshot.rule_mapping_rows],
    ["grandSport_rule_mapping", snapshot.grand_sport_rule_mapping_rows],
  ]) {
    assert.ok(rows.length > 0, `${sheetName} should have rule rows`);
    for (const row of rows) {
      assert.ok("normalization_status" in row, `${sheetName}.${row.rule_id} missing normalization_status`);
      assert.equal(
        String(row.generation_action || "").startsWith("omit"),
        false,
        `${sheetName}.${row.rule_id} should be deleted instead of retained with generation_action=${row.generation_action}`,
      );
      assert.equal(
        ["omitted", "replaced"].includes(String(row.normalization_status || "").toLowerCase()),
        false,
        `${sheetName}.${row.rule_id} should be deleted instead of retained with normalization_status=${row.normalization_status}`,
      );
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

test("Z06 active replace excludes stay limited to true default-replacement rows", () => {
  const offenders = pythonJson(`
import json
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

options = {clean(row.get('option_id')): row for row in rows('z06_options')}
active_group_ids = {clean(row.get('group_id')) for row in rows('z06_exclusive_groups') if active(row)}
group_by_option = {}
for row in rows('z06_exclusive_members'):
    if not active(row):
        continue
    group_id = clean(row.get('group_id'))
    option_id = clean(row.get('option_id'))
    if group_id in active_group_ids and option_id:
        group_by_option.setdefault(option_id, set()).add(group_id)

requires_any_sources = {clean(row.get('source_id')): clean(row.get('group_id')) for row in rows('z06_rule_groups') if active(row) and clean(row.get('group_type')) == 'requires_any'}
allowed_pairs = {('opt_j57_001', 'opt_j6a_001')}
offenders = []
for row in rows('z06_rule_mapping'):
    if not runtime_authored_rule(row):
        continue
    if clean(row.get('rule_type')) != 'excludes' or clean(row.get('runtime_action')) != 'replace':
        continue
    source_id = clean(row.get('source_id'))
    target_id = clean(row.get('target_id'))
    if (source_id, target_id) in allowed_pairs:
        continue
    shared_groups = sorted(group_by_option.get(source_id, set()) & group_by_option.get(target_id, set()))
    offenders.append({
        'row': row['_row'],
        'rule_id': clean(row.get('rule_id')),
        'source_rpo': clean(options.get(source_id, {}).get('rpo')),
        'source_id': source_id,
        'target_rpo': clean(options.get(target_id, {}).get('rpo')),
        'target_id': target_id,
        'shared_exclusive_groups': shared_groups,
        'source_requires_any_group': requires_any_sources.get(source_id, ''),
    })

wb.close()
print(json.dumps(offenders))
`);
  assert.deepEqual(offenders, []);
});

test("approved one-source blocker clusters use excludes_any groups instead of direct excludes", () => {
  const ungrouped = pythonJson(`
import json
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
    'stingray': {
        'rule_sheet': 'rule_mapping',
        'group_sheet': 'rule_groups',
        'member_sheet': 'rule_group_members',
        'option_sheet': 'stingray_options',
        'source_rpos': ['PCX', 'PDV', 'R88', 'SFZ', 'CF8'],
    },
    'grandSport': {
        'rule_sheet': 'grandSport_rule_mapping',
        'group_sheet': 'grandSport_rule_groups',
        'member_sheet': 'grandSport_rule_group_members',
        'option_sheet': 'grandSport_options',
        'source_rpos': ['R88', 'SFZ', 'CF8', 'SHT'],
    },
    'z06': {
        'rule_sheet': 'z06_rule_mapping',
        'group_sheet': 'z06_rule_groups',
        'member_sheet': 'z06_rule_group_members',
        'option_sheet': 'z06_options',
        'source_rpos': ['R88', 'SFZ', 'CF8', 'SHT', 'GBA'],
    },
    'zr1': {
        'rule_sheet': 'zr1_rule_mapping',
        'group_sheet': 'zr1_rule_groups',
        'member_sheet': 'zr1_rule_group_members',
        'option_sheet': 'zr1_options',
        'source_rpos': ['R88', 'SFZ'],
    },
    'zr1x': {
        'rule_sheet': 'zr1x_rule_mapping',
        'group_sheet': 'zr1x_rule_groups',
        'member_sheet': 'zr1x_rule_group_members',
        'option_sheet': 'zr1x_options',
        'source_rpos': ['R88', 'SFZ'],
    },
}

issues = []
for model_key, config in models.items():
    option_by_id = {row.get('option_id'): row for row in rows(config['option_sheet'])}
    option_ids_by_rpo = {}
    for option in option_by_id.values():
        option_ids_by_rpo.setdefault(clean(option.get('rpo')), []).append(clean(option.get('option_id')))
    grouped_pairs = set()
    active_groups = [row for row in rows(config['group_sheet']) if active(row) and clean(row.get('group_type')) == 'excludes_any']
    members = rows(config['member_sheet'])
    for group in active_groups:
        source_id = clean(group.get('source_id'))
        for member in members:
            if active(member) and clean(member.get('group_id')) == clean(group.get('group_id')):
                grouped_pairs.add((source_id, clean(member.get('target_id'))))
    for source_rpo in config['source_rpos']:
        source_ids = set(option_ids_by_rpo.get(source_rpo, []))
        for rule in rows(config['rule_sheet']):
            if not runtime_authored_rule(rule):
                continue
            if clean(rule.get('rule_type')) != 'excludes':
                continue
            if clean(rule.get('runtime_action')) == 'replace':
                continue
            if clean(rule.get('generation_action')) == 'preserve_runtime_exclude':
                continue
            source_id = clean(rule.get('source_id'))
            target_id = clean(rule.get('target_id'))
            if source_id not in source_ids:
                continue
            if (source_id, target_id) in grouped_pairs:
                continue
            issues.append({
                'model': model_key,
                'sheet': config['rule_sheet'],
                'row': rule['_row'],
                'source_rpo': source_rpo,
                'source_id': source_id,
                'target_rpo': clean(option_by_id.get(target_id, {}).get('rpo')),
                'target_id': target_id,
                'rule_id': clean(rule.get('rule_id')),
            })

wb.close()
print(json.dumps(issues))
`);
  assert.deepEqual(ungrouped, []);
});

// RETIRED: "price rule source sheets classify override semantics explicitly".
// The price_semantic review column was removed in the Phase 2 workbook cleanup
// (workbook-cleanup-spec.md Tier A); it was never consumed by generation or the
// runtime app. Price-rule typing remains guarded by the numeric price_value
// checks in validate_workbook_schema.

test("category_master is retired from the active source graph and draft provenance is not live app data", () => {
  assert.equal(snapshot.sheetnames.includes("category_master"), false);
  // Historical evidence sheets (including archive_category_master) were
  // extracted to archive/stingray_archive.xlsx in the workbook cleanup.
  assert.equal(snapshot.sheetnames.includes("archive_category_master"), false);

  const registry = liveRegistry();
  for (const [modelKey, entry] of Object.entries(registry.models)) {
    assert.equal("draftMetadata" in entry.data, false, `${modelKey} leaked draftMetadata`);
    for (const choice of entry.data.choices) {
      assert.equal("source_option_name" in choice, false, `${modelKey} ${choice.choice_id} leaked source_option_name`);
      assert.equal("source_description" in choice, false, `${modelKey} ${choice.choice_id} leaked source_description`);
      assert.equal("text_cleanup_notes" in choice, false, `${modelKey} ${choice.choice_id} leaked text_cleanup_notes`);
      assert.equal("source_detail_raw" in choice, false, `${modelKey} ${choice.choice_id} leaked source_detail_raw`);
      assert.equal("choice_mode" in choice, false, `${modelKey} ${choice.choice_id} leaked choice_mode`);
      assert.equal("selection_mode" in choice, false, `${modelKey} ${choice.choice_id} leaked selection_mode`);
      assert.equal("selection_mode_label" in choice, false, `${modelKey} ${choice.choice_id} leaked selection_mode_label`);
    }
    for (const row of entry.data.standardEquipment) {
      assert.equal("source_detail_raw" in row, false, `${modelKey} ${row.equipment_id} leaked source_detail_raw`);
    }
    assert.ok(entry.data.sections.some((section) => section.selection_mode), `${modelKey} keeps section selection_mode`);
    assert.ok(entry.data.sections.some((section) => section.choice_mode), `${modelKey} keeps section choice_mode`);
    assert.ok(entry.data.sections.some((section) => section.selection_mode_label), `${modelKey} keeps section selection_mode_label`);
    assert.ok(entry.data.exclusiveGroups.some((group) => group.selection_mode), `${modelKey} keeps group selection_mode`);
  }
});
