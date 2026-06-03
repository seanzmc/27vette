import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import fs from "node:fs";
import test from "node:test";

const draftPath = "form-output/inspection/z06-form-data-draft.json";
const draftMarkdownPath = "form-output/inspection/z06-form-data-draft.md";
const appDataPath = "form-app/data.js";
const expectedVariantIds = ["1lz_h07", "2lz_h07", "3lz_h07", "1lz_h67", "2lz_h67", "3lz_h67"];
const standardSections = new Set([
  "sec_stan_001",
  "sec_1lte_001",
  "sec_2lte_001",
  "sec_3lte_001",
  "sec_incl_001",
  "sec_safe_001",
  "sec_stan_002",
  "sec_tech_001",
]);

function generateDraftWithoutAppMutation() {
  const beforeAppData = fs.readFileSync(appDataPath, "utf8");
  execFileSync(".venv/bin/python", ["scripts/generate_z06_form.py"], {
    encoding: "utf8",
    stdio: "pipe",
  });
  const afterAppData = fs.readFileSync(appDataPath, "utf8");
  assert.equal(afterAppData, beforeAppData, "Z06 draft generation must not mutate form-app/data.js");
  assert.ok(fs.existsSync(draftPath), "Z06 draft JSON should exist");
  assert.ok(fs.existsSync(draftMarkdownPath), "Z06 draft Markdown should exist");
  return JSON.parse(fs.readFileSync(draftPath, "utf8"));
}

const draft = generateDraftWithoutAppMutation();

test("Z06 draft preserves the live generated-data top-level contract", () => {
  for (const key of [
    "dataset",
    "variants",
    "steps",
    "sections",
    "contextChoices",
    "choices",
    "standardEquipment",
    "ruleGroups",
    "exclusiveGroups",
    "rules",
    "priceRules",
    "interiors",
    "colorOverrides",
    "defaultSelectionRules",
    "validation",
  ]) {
    assert.ok(Object.hasOwn(draft, key), `draft is missing ${key}`);
  }
  assert.equal(draft.dataset.status, "draft_not_runtime_active");
  assert.equal(draft.dataset.model, "Z06");
  assert.equal(draft.dataset.source_sheet, "z06_options");
  assert.deepEqual(
    draft.variants.map((variant) => variant.variant_id),
    expectedVariantIds
  );
  assert.ok(draft.choices.length > 0, "Z06 draft should include choices");
  assert.ok(draft.standardEquipment.length > 0, "Z06 draft should include standard equipment rows");
});

test("Z06 draft emits approved package, wheel, and standalone Z07 placements", () => {
  const sectionsByRpo = new Map();
  for (const choice of draft.choices) {
    if (!sectionsByRpo.has(choice.rpo)) {
      sectionsByRpo.set(choice.rpo, new Set());
    }
    sectionsByRpo.get(choice.rpo).add(choice.section_id);
  }

  for (const rpo of ["PDB", "PDD", "PDF"]) {
    assert.deepEqual([...sectionsByRpo.get(rpo)].sort(), ["sec_z06_pkg_001"], `${rpo} should draft in the Z06 package section`);
  }
  for (const rpo of ["ROY", "ROZ", "STZ"]) {
    assert.deepEqual([...sectionsByRpo.get(rpo)].sort(), ["sec_z06_cf_whee_001"], `${rpo} should draft in the Z06 carbon fiber wheel section`);
  }
  assert.deepEqual([...sectionsByRpo.get("Z07")].sort(), ["sec_perf_z52_001"], "Z07 should stay in the adjacent Z52 package section");
});

test("Z06 draft keeps default-selected options selectable", () => {
  for (const rpo of ["EFR", "T0E", "J56", "719", "EYT", "J6A", "CF7", "CM9", "AQ9", "SOE"]) {
    const choices = draft.choices.filter((choice) => choice.rpo === rpo);
    assert.ok(choices.length > 0, `${rpo} should be emitted`);
    for (const choice of choices) {
      if (choice.status === "unavailable") {
        continue;
      }
      assert.equal(choice.display_behavior, "default_selected", `${choice.choice_id} should remain default_selected`);
      assert.equal(choice.selectable, "True", `${choice.choice_id} should remain selectable`);
    }
  }
});

test("Z06 future option review replay preserves selectable default rows", () => {
  const plannedRows = JSON.parse(
    execFileSync(
      ".venv/bin/python",
      [
        "-c",
        `import json, sys
from openpyxl import load_workbook
sys.path.insert(0, 'scripts')
from apply_future_model_option_review import rows_from_sheet, build_future_option_population_plan
wb = load_workbook('stingray_master.xlsx', data_only=False, read_only=False)
try:
    rows = rows_from_sheet(wb, 'future_model_option_review')
    plan = build_future_option_population_plan(wb, rows, ['z06'])
    target = {'EYT', 'J6A', 'CF7', 'CM9', 'AQ9', 'SOE'}
    print(json.dumps([row for row in plan['models']['z06']['option_rows'] if row.get('rpo') in target], sort_keys=True))
finally:
    wb.close()
`,
      ],
      { encoding: "utf8", stdio: "pipe" }
    )
  );

  const sourceRows = JSON.parse(
    execFileSync(
      ".venv/bin/python",
      [
        "-c",
        `import json, sys
from openpyxl import load_workbook
sys.path.insert(0, 'scripts')
from corvette_form_generator.workbook import clean
wb = load_workbook('stingray_master.xlsx', data_only=True, read_only=True)
try:
    ws = wb['future_model_source_review']
    headers = [clean(cell.value) for cell in next(ws.iter_rows(min_row=1, max_row=1))]
    idx = {header: offset for offset, header in enumerate(headers)}
    target = {'EYT', 'J6A', 'CF7', 'CM9', 'AQ9', 'SOE'}
    rows = []
    for row in ws.iter_rows(min_row=2, values_only=True):
        if clean(row[idx['model_key']]) == 'z06' and clean(row[idx['approved_rpo']]) in target:
            rows.append({
                'rpo': clean(row[idx['approved_rpo']]),
                'option_id': clean(row[idx['approved_option_id']]),
                'selectable': clean(row[idx['approved_selectable']]),
                'display_behavior': clean(row[idx['approved_display_behavior']]),
                'review_status': clean(row[idx['review_status']]),
                'active': clean(row[idx['active']]),
            })
    print(json.dumps(rows, sort_keys=True))
finally:
    wb.close()
`,
      ],
      { encoding: "utf8", stdio: "pipe" }
    )
  );

  const targetRpos = new Set(["EYT", "J6A", "CF7", "CM9", "AQ9", "SOE"]);
  assert.equal(plannedRows.length, targetRpos.size);
  assert.equal(sourceRows.length, targetRpos.size);
  for (const row of plannedRows) {
    assert.equal(row.selectable, "True", `${row.option_id} should replay as selectable`);
    assert.equal(row.display_behavior, "default_selected", `${row.option_id} should replay as default_selected`);
  }
  for (const row of sourceRows) {
    assert.equal(row.selectable, "True", `${row.option_id} source review should stay selectable`);
    assert.equal(row.display_behavior, "default_selected", `${row.option_id} source review should stay default_selected`);
    assert.equal(row.review_status, "approved", `${row.option_id} source review should stay approved`);
    assert.equal(row.active, "True", `${row.option_id} source review should stay active`);
  }
});

test("Z06 draft emits approved package/wheel and Z07 price rules", () => {
  const priceRuleById = new Map(draft.priceRules.map((rule) => [rule.price_rule_id, rule]));
  for (const [ruleId, conditionOptionId, targetOptionId, priceValue] of [
    ["z06_pr_z07_j57_zero", "opt_z07_001", "opt_j57_001", 0],
    ["z06_pr_roy_pdb_16000", "opt_roy_001", "opt_pdb_001", 16000],
    ["z06_pr_roz_pdb_17000", "opt_roz_001", "opt_pdb_001", 17000],
    ["z06_pr_stz_pdb_17500", "opt_stz_001", "opt_pdb_001", 17500],
    ["z06_pr_roy_pdd_25495", "opt_roy_001", "opt_pdd_001", 25495],
    ["z06_pr_roy_pdf_26495", "opt_roy_001", "opt_pdf_001", 26495],
  ]) {
    const rule = priceRuleById.get(ruleId);
    assert.ok(rule, `${ruleId} should be emitted`);
    assert.equal(rule.condition_option_id, conditionOptionId);
    assert.equal(rule.target_option_id, targetOptionId);
    assert.equal(rule.price_rule_type, "override");
    assert.equal(rule.price_value, priceValue);
  }
});

test("Z06 draft keeps BCW price override without auto-adding BCW from B6P", () => {
  const b6pBcwPrice = draft.priceRules.find((rule) => rule.price_rule_id === "z06_pr_b6p_bcw_895_coupe");
  assert.ok(b6pBcwPrice, "B6P should still own the BCW price override");
  assert.equal(b6pBcwPrice.condition_option_id, "opt_b6p_001");
  assert.equal(b6pBcwPrice.target_option_id, "opt_bcw_001");
  assert.equal(b6pBcwPrice.price_rule_type, "override");
  assert.equal(b6pBcwPrice.price_value, 895);

  const autoBcwRules = draft.rules.filter(
    (rule) => rule.rule_type === "includes" && rule.target_id === "opt_bcw_001" && rule.active === "True"
  );
  assert.deepEqual(
    autoBcwRules.map((rule) => `${rule.source_id}->${rule.target_id}`),
    [],
    "BCW should not be auto-added by B6P/D3V; it should remain a selectable priced choice"
  );
});

test("Z06 draft keeps suspension out of customer choice sections and in equipment summaries", () => {
  const visibleSuspensionChoices = draft.choices.filter(
    (choice) => choice.section_id === "sec_susp_001" && choice.step_key !== "standard_equipment"
  );
  assert.deepEqual(
    visibleSuspensionChoices.map((choice) => `${choice.choice_id}:${choice.rpo}:${choice.status}:${choice.step_key}`),
    [],
    "Z06 suspension rows should not render as customer choice cards"
  );

  const equipmentRpos = new Set(draft.standardEquipment.map((row) => row.rpo));
  assert.equal(equipmentRpos.has("FE6"), true, "standard FE6 suspension should be listed in standard equipment");

  const fe7Choices = draft.choices.filter((choice) => choice.rpo === "FE7");
  assert.ok(fe7Choices.length > 0, "FE7 should still be emitted as Z07-included equipment");
  assert.equal(fe7Choices.every((choice) => choice.step_key === "standard_equipment"), true);
  assert.equal(fe7Choices.every((choice) => choice.display_behavior === "auto_only"), true);
  assert.ok(
    draft.rules.some((rule) => rule.source_id === "opt_z07_001" && rule.rule_type === "includes" && rule.target_id === "opt_fe7_001"),
    "Z07 should continue to include FE7 suspension"
  );
});

test("Z06 interiors group by broad color family instead of one container per stitched variant", () => {
  const byId = new Map(draft.interiors.map((interior) => [interior.interior_id, interior]));
  for (const interiorId of ["2LZ_AQ9_H1Y", "2LZ_AQ9_H1Y_38S", "2LZ_AQ9_H1Y_36S", "2LZ_AQ9_H1Y_37S"]) {
    assert.equal(byId.get(interiorId)?.interior_color_family, "Jet Black", `${interiorId} should group under Jet Black`);
  }
  assert.equal(byId.get("2LZ_AQ9_HUN")?.interior_color_family, "Sky Cool Gray");
  assert.equal(byId.get("2LZ_AQ9_HUR")?.interior_color_family, "Adrenaline Red");
});

test("Z06 draft does not emit priced standard-equipment choices", () => {
  const pricedStandardChoices = draft.choices.filter(
    (choice) => standardSections.has(choice.section_id) && Number(choice.base_price || 0) > 0
  );
  assert.deepEqual(
    pricedStandardChoices.map((choice) => `${choice.choice_id}:${choice.rpo}:${choice.section_id}:${choice.base_price}`),
    []
  );
});

test("Z06 draft source-data guards keep runtime-review rows canonical", () => {
  const missingDisplayOrder = draft.choices.filter((choice) => choice.display_order === "" || choice.display_order == null);
  assert.deepEqual(
    missingDisplayOrder.map((choice) => `${choice.choice_id}:${choice.rpo}:${choice.section_id}`),
    []
  );

  const nonSelectableDefaults = draft.choices.filter(
    (choice) => choice.display_behavior === "default_selected" && choice.selectable !== "True"
  );
  assert.deepEqual(
    nonSelectableDefaults.map((choice) => `${choice.choice_id}:${choice.rpo}:${choice.section_id}:${choice.selectable}`),
    []
  );
});
