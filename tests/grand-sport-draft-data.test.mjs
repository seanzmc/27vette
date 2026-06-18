import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import fs from "node:fs";
import test from "node:test";

const draftPath = "form-output/inspection/grand-sport-form-data-draft.json";
const draftMarkdownPath = "form-output/inspection/grand-sport-form-data-draft.md";
const appDataPath = "form-app/data.js";

function generateDraftWithoutAppMutation() {
  const beforeAppData = fs.readFileSync(appDataPath, "utf8");
  execFileSync(".venv/bin/python", ["scripts/generate_form.py", "--model", "grand_sport"], {
    encoding: "utf8",
    stdio: "pipe",
  });
  const afterAppData = fs.readFileSync(appDataPath, "utf8");
  assert.equal(afterAppData, beforeAppData, "Grand Sport draft generation must not mutate form-app/data.js");
  assert.ok(fs.existsSync(draftPath), "Grand Sport draft JSON should exist");
  assert.ok(fs.existsSync(draftMarkdownPath), "Grand Sport draft Markdown should exist");
  return JSON.parse(fs.readFileSync(draftPath, "utf8"));
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

const draft = generateDraftWithoutAppMutation();
const inspectionSource = fs.readFileSync("scripts/corvette_form_generator/inspection.py", "utf8");
const interiorsSource = fs.readFileSync("scripts/corvette_form_generator/interiors.py", "utf8");
const activeInteriorPipelineSources = [
  inspectionSource,
  interiorsSource,
  fs.readFileSync("scripts/corvette_form_generator/model_config.py", "utf8"),
  fs.readFileSync("scripts/corvette_form_generator/model_configs.py", "utf8"),
  fs.readFileSync("scripts/corvette_form_generator/production.py", "utf8"),
  fs.readFileSync("scripts/generate_form.py", "utf8"),
].join("\n");
const heritageHashOptionIds = ["opt_17a_001", "opt_20a_001", "opt_55a_001", "opt_75a_001", "opt_97a_001", "opt_dx4_001"];
const heritageCenterStripeOptionIds = ["opt_dmu_001", "opt_dmv_001", "opt_dmw_001", "opt_dmx_001", "opt_dmy_001"];
const nonCenterStripeOptionIds = [
  "opt_dpb_001", "opt_dpc_001", "opt_dpg_001", "opt_dpl_001", "opt_dpt_001", "opt_dsy_001", "opt_dsz_001", "opt_dt0_001",
  "opt_dth_001", "opt_dub_001", "opt_due_001", "opt_duk_001", "opt_duw_001", "opt_dzu_001", "opt_dzv_001", "opt_dzx_001",
  "opt_sht_001", "opt_vpo_001", "opt_pda_001", "opt_sne_001", "opt_vpw_001",
];
const fullLengthStripeOptionIds = nonCenterStripeOptionIds.slice(0, 16);
const grandSportJakeOptionIds = ["opt_pda_001", "opt_sne_001", "opt_vpw_001"];
const jakeGraphicSectionByOptionId = new Map([
  ["opt_pda_001", "sec_jake_001"],
  ["opt_sne_001", "sec_stri_001"],
  ["opt_vpw_001", "sec_hash_001"],
]);
const requiredPackagePriceRules = [
  ["gs_pr_fey_j57_001", "opt_fey_001", "opt_j57_001", "override", 0],
  ["gs_pr_fey_t0f_001", "opt_fey_001", "opt_t0f_001", "override", 0],
  ["gs_pr_fey_wub_001", "opt_fey_001", "opt_wub_001", "override", 0],
  ["gs_pr_fey_cfz_001", "opt_fey_001", "opt_cfz_001", "override", 0],
  ["gs_pr_pcq_vwe_001", "opt_pcq_001", "opt_vwe_001", "override", 0],
  ["gs_pr_pcq_vwt_001", "opt_pcq_001", "opt_vwt_001", "override", 0],
  ["gs_pr_pef_ria_001", "opt_pef_001", "opt_ria_001", "override", 0],
  ["gs_pr_pef_cav_001", "opt_pef_001", "opt_cav_001", "override", 0],
  ["gs_pr_t0f_cfz_001", "opt_t0f_001", "opt_cfz_001", "override", 0],
  ["gs_pr_bcp_d3v_001", "opt_bcp_002", "opt_d3v_001", "override", 0],
  ["gs_pr_bcs_d3v_001", "opt_bcs_002", "opt_d3v_001", "override", 0],
  ["gs_pr_bc4_d3v_001", "opt_bc4_002", "opt_d3v_001", "override", 0],
  ["gs_pr_2lt_ah2_seat_001", "opt_ah2_001", "opt_ah2_001", "override", 1695],
  ["gs_pr_2lt_ae4_seat_001", "opt_ae4_002", "opt_ae4_002", "override", 2095],
  ["gs_pr_3lt_ae4_seat_001", "opt_ae4_002", "opt_ae4_002", "override", 595],
  ["gs_pr_3lt_aup_seat_001", "opt_aup_001", "opt_aup_001", "override", 350],
  ["gs_pr_pdyryt_001", "opt_pdy_001", "opt_ryt_001", "override", 0],
  ["gs_pr_pdys08_001", "opt_pdy_001", "opt_s08_001", "override", 0],
];

const expectedGrandSportExclusiveGroups = [
  {
    group_id: "gs_excl_ls6_engine_covers",
    option_ids: ["opt_bc7_001", "opt_bcp_002", "opt_bcs_002", "opt_bc4_002"],
    selection_mode: "single_within_group",
  },
  {
    group_id: "gs_excl_center_caps",
    option_ids: ["opt_5zb_001", "opt_5zc_001", "opt_5zd_001"],
  },
  {
    group_id: "gs_excl_indoor_car_covers",
    option_ids: ["opt_rwh_001", "opt_wkr_001"],
  },
  {
    group_id: "gs_excl_rear_script_badges",
    option_ids: ["opt_rik_001", "opt_rin_001", "opt_sl8_001"],
  },
  {
    group_id: "gs_excl_suede_compartment_liners",
    option_ids: ["opt_sxb_001", "opt_sxr_001", "opt_sxt_001"],
  },
  {
    group_id: "gs_excl_ground_effects",
    option_ids: ["opt_cfl_001", "opt_cfz_001"],
  },
  {
    group_id: "gs_excl_z52_packages",
    option_ids: ["opt_feb_001", "opt_fey_001"],
  },
  {
    group_id: "gs_excl_exterior_accents",
    option_ids: ["opt_efr_001", "opt_edu_001"],
    selection_mode: "required_single_within_group",
  },
  {
    group_id: "gs_excl_seat_belts",
    option_ids: ["opt_719_001", "opt_3n9_001", "opt_379_001", "opt_3a9_001", "opt_3f9_001", "opt_3m9_001"],
  },
  {
    group_id: "gs_excl_performance_brakes",
    option_ids: ["opt_jx6_001", "opt_j56_001", "opt_j57_001"],
    selection_mode: "required_single_within_group",
  },
];

test("Grand Sport draft preserves the live generated-data top-level contract", () => {
  for (const key of [
    "dataset",
    "variants",
    "steps",
    "sections",
    "contextChoices",
    "choices",
    "standardEquipment",
    "orderSummary",
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
  assert.equal(draft.dataset.model, "Grand Sport");
  assert.deepEqual(
    draft.variants.map((variant) => variant.variant_id),
    ["1lt_e07", "2lt_e07", "3lt_e07", "1lt_e67", "2lt_e67", "3lt_e67"]
  );
});

test("Grand Sport draft includes the full variant matrix and standard equipment rows", () => {
  assert.equal(draft.variants.length, 6);
  assert.equal(draft.contextChoices.length, 8);
  assert.equal(draft.steps.length, 14);
  assert.equal(draft.orderSummary.sections.length, 11);
  assert.equal(Object.keys(draft.orderSummary.stepMap).length, 13);
  assert.equal(draft.orderSummary.stepMap.packages_performance, "performance_mechanical");
  assert.deepEqual(
    JSON.parse(JSON.stringify(draft.steps.map((step) => [step.step_key, step.step_label]))),
    [
      ["body_style", "Body Style"],
      ["trim_level", "Trim Level"],
      ["paint", "Exterior Paint"],
      ["exterior_appearance", "Exterior Appearance"],
      ["wheels", "Wheels & Brake Calipers"],
      ["packages_performance", "Performance & Aero"],
      ["aero_exhaust_stripes_accessories", "Stripes"],
      ["seat", "Seats"],
      ["base_interior", "Interior Color"],
      ["seat_belt", "Seat Belt"],
      ["interior_trim", "Interior Trim"],
      ["accessories", "Accessories"],
      ["delivery", "Custom Delivery"],
      ["summary", "Summary"],
    ]
  );
  assert.equal(draft.choices.length, 1422);
  assert.equal(draft.standardEquipment.length, 455);
  assert.equal(draft.choices.filter((choice) => choice.status === "available").length, 811);
  assert.equal(draft.choices.filter((choice) => choice.status === "standard").length, 455);
  assert.equal(draft.choices.filter((choice) => choice.status === "unavailable").length, 156);
});

test("Grand Sport standard equipment is preserved after standard mirror rows are inactive", () => {
  const expectedByVariant = {
    "1lt_e07": ["719", "AQ9", "CF7", "EFR", "EYT", "J6A", "NGA", "SWM"],
    "2lt_e07": ["719", "AQ9", "CF7", "EFR", "EYT", "J6A", "NGA", "SWM", "UQT"],
    "3lt_e07": ["719", "AH2", "CF7", "EFR", "EYT", "J6A", "NGA", "SWM", "UQT"],
    "1lt_e67": ["719", "AQ9", "CM9", "EFR", "EYT", "J6A", "NGA", "SWM"],
    "2lt_e67": ["719", "AQ9", "CM9", "EFR", "EYT", "J6A", "NGA", "SWM", "UQT"],
    "3lt_e67": ["719", "AH2", "CM9", "EFR", "EYT", "J6A", "NGA", "SWM", "UQT"],
  };

  for (const [variantId, expectedRpos] of Object.entries(expectedByVariant)) {
    const standardRpos = draft.standardEquipment
      .filter((item) => item.variant_id === variantId)
      .map((item) => item.rpo);
    for (const rpo of expectedRpos) {
      assert.ok(standardRpos.includes(rpo), `${variantId} should keep ${rpo} in standard equipment`);
    }
  }
});

test("Grand Sport trim-scoped overrides collapse AQ9 and UQT duplicate rows", () => {
  assert.equal(draft.choices.some((choice) => choice.option_id === "opt_aq9_003"), false);
  assert.equal(draft.choices.some((choice) => choice.option_id === "opt_uqt_002"), false);

  for (const variantId of ["1lt_e07", "1lt_e67", "2lt_e07", "2lt_e67"]) {
    const aq9 = draft.choices.find((choice) => choice.choice_id === `${variantId}__opt_aq9_001`);
    assert.ok(aq9, `${variantId} should emit canonical AQ9`);
    assert.equal(aq9.status, "standard");
    assert.equal(aq9.section_id, "sec_seat_002");
  }

  for (const variantId of ["1lt_e07", "1lt_e67"]) {
    const uqt = draft.choices.find((choice) => choice.choice_id === `${variantId}__opt_uqt_001`);
    assert.ok(uqt, `${variantId} should emit canonical UQT`);
    assert.equal(uqt.status, "available");
    assert.equal(uqt.selectable, "True");
    assert.equal(uqt.section_id, "sec_inte_001");
  }

  for (const [variantId, sectionId] of [
    ["2lt_e07", "sec_2lte_001"],
    ["2lt_e67", "sec_2lte_001"],
    ["3lt_e07", "sec_3lte_001"],
    ["3lt_e67", "sec_3lte_001"],
  ]) {
    const uqt = draft.choices.find((choice) => choice.choice_id === `${variantId}__opt_uqt_001`);
    assert.ok(uqt, `${variantId} should emit canonical UQT`);
    assert.equal(uqt.status, "standard");
    assert.equal(uqt.selectable, "False");
    assert.equal(uqt.section_id, sectionId);
    assert.equal(uqt.step_key, "standard_equipment");
  }
});

test("Grand Sport seat availability comes from grandSport_ovs by trim", () => {
  const seatsForVariant = (variantId) =>
    draft.choices
      .filter((choice) => choice.variant_id === variantId && choice.step_key === "seat")
      .sort((a, b) => Number(a.display_order) - Number(b.display_order))
      .map((choice) => [choice.rpo, choice.status]);

  assert.deepEqual(JSON.parse(JSON.stringify(seatsForVariant("1lt_e07"))), [
    ["AQ9", "standard"],
    ["AH2", "unavailable"],
    ["AE4", "available"],
    ["AUP", "unavailable"],
  ]);
  assert.deepEqual(JSON.parse(JSON.stringify(seatsForVariant("2lt_e07"))), [
    ["AQ9", "standard"],
    ["AH2", "available"],
    ["AE4", "available"],
    ["AUP", "unavailable"],
  ]);
  assert.deepEqual(JSON.parse(JSON.stringify(seatsForVariant("3lt_e07"))), [
    ["AQ9", "unavailable"],
    ["AH2", "standard"],
    ["AE4", "available"],
    ["AUP", "available"],
  ]);
});

test("Grand Sport draft emits color overrides and workbook-backed package price rules", () => {
  assert.equal(draft.rules.length > 0, true, "Grand Sport draft should include normalized compatibility rules");
  assert.equal(draft.priceRules.length >= requiredPackagePriceRules.length, true);
  const priceRuleKeys = new Set(
    draft.priceRules.map((rule) => [rule.price_rule_id, rule.condition_option_id, rule.target_option_id, rule.price_rule_type, rule.price_value].join("::"))
  );
  for (const expectedRule of requiredPackagePriceRules) {
    assert.ok(priceRuleKeys.has(expectedRule.join("::")), `${expectedRule[0]} should be emitted from grandSport_price_rules`);
  }
  for (const priceRuleId of ["gs_pr_bcp_d3v_001", "gs_pr_bcs_d3v_001", "gs_pr_bc4_d3v_001"]) {
    const rule = draft.priceRules.find((candidate) => candidate.price_rule_id === priceRuleId);
    assert.ok(rule, `${priceRuleId} should be emitted from grandSport_price_rules`);
    assert.equal(rule.body_style_scope, "coupe", `${priceRuleId} should be scoped to coupe like Stingray D3V pricing`);
  }
  assert.deepEqual(
    JSON.parse(
      JSON.stringify(
        draft.priceRules
          .filter((rule) => rule.price_rule_id.endsWith("_seat_001"))
          .map((rule) => [rule.price_rule_id, rule.trim_level_scope])
          .sort()
      )
    ),
    [
      ["gs_pr_2lt_ae4_seat_001", "2LT"],
      ["gs_pr_2lt_ah2_seat_001", "2LT"],
      ["gs_pr_3lt_ae4_seat_001", "3LT"],
      ["gs_pr_3lt_aup_seat_001", "3LT"],
    ]
  );
  for (const rule of draft.priceRules) {
    assert.ok(rule.price_rule_id, "price rule should have price_rule_id");
    assert.ok(rule.condition_option_id, `${rule.price_rule_id} should have condition_option_id`);
    assert.ok(rule.target_option_id, `${rule.price_rule_id} should have target_option_id`);
    assert.equal(rule.price_rule_type, "override", `${rule.price_rule_id} should use supported override type`);
    assert.equal(typeof rule.price_value, "number", `${rule.price_rule_id} should emit numeric price_value`);
  }
  assert.equal(draft.colorOverrides.length, 245);
  assert.ok(
    draft.colorOverrides.some(
      (override) =>
        override.interior_id === "3LT_R6X_AH2_HZP_N26" &&
        override.option_id === "opt_379_001" &&
        override.adds_rpo === "opt_d30_001"
    ),
    "seatbelt color override rows should auto-add D30 like Stingray"
  );
  const warnings = new Set(draft.validation.filter((row) => row.severity === "warning").map((row) => row.check_id));
  const passes = new Set(draft.validation.filter((row) => row.severity === "pass").map((row) => row.check_id));
  assert.ok(warnings.has("grand_sport_draft_status"));
  assert.equal(warnings.has("pricing_deferred"), false);
  assert.ok(passes.has("price_rules"));
  assert.equal(warnings.has("rules_deferred"), false);
  assert.equal(warnings.has("color_overrides"), false);
  assert.deepEqual(draft.draftMetadata.deferredSurfaces, []);
});

test("Grand Sport draft emits the approved model-scoped exclusive groups", () => {
  assert.equal(draft.exclusiveGroups.length, expectedGrandSportExclusiveGroups.length);
  const byId = new Map(draft.exclusiveGroups.map((group) => [group.group_id, group]));
  const choiceOptionIds = new Set(draft.choices.map((choice) => choice.option_id));

  for (const expected of expectedGrandSportExclusiveGroups) {
    const group = byId.get(expected.group_id);
    assert.ok(group, `${expected.group_id} should be generated`);
    assert.equal(group.selection_mode, expected.selection_mode || "single_within_group");
    assert.equal(group.active, "True");
    assert.deepEqual(JSON.parse(JSON.stringify(group.option_ids)), expected.option_ids);
    for (const optionId of expected.option_ids) {
      assert.equal(choiceOptionIds.has(optionId), true, `${optionId} should exist in Grand Sport choices`);
    }
  }
  assert.equal([...byId.values()].some((group) => (group.option_ids || []).includes("opt_jxa_001")), false);
  for (const legacyOptionId of ["opt_bc4_001", "opt_bcp_001", "opt_bcs_001"]) {
    assert.equal(choiceOptionIds.has(legacyOptionId), false, `${legacyOptionId} legacy engine cover row should not be emitted`);
    assert.equal([...byId.values()].some((group) => (group.option_ids || []).includes(legacyOptionId)), false, `${legacyOptionId} should not appear in generated exclusive groups`);
  }
});

test("Grand Sport draft emits deterministic option rules from copied Stingray rows and raw detail", () => {
  const ruleKeys = new Set(
    draft.rules.map((rule) => [
      rule.source_id,
      rule.rule_type,
      rule.target_id,
      rule.body_style_scope || "",
      rule.runtime_action || "",
    ].join("::"))
  );

  for (const key of [
    "opt_pda_001::includes::opt_sne_001::::active",
    "opt_pda_001::includes::opt_vpw_001::::active",
    "opt_5jr_001::includes::opt_drg_001::::active",
    "opt_j6l_001::requires::opt_j57_001::::active",
    "opt_j6d_001::requires::opt_j57_001::::active",
    "opt_nwi_001::excludes::opt_nga_001::::replace",
    "opt_t0f_001::requires::opt_j57_001::::active",
    "opt_j57_001::excludes::opt_j6a_001::::replace",
    "opt_fey_001::excludes::opt_t0e_001::::replace",
    "opt_fey_001::includes::opt_t0f_001::::active",
    "opt_fey_001::includes::opt_cfz_001::::active",
    "opt_t0f_001::includes::opt_cfz_001::::active",
    "opt_bv4_001::excludes::opt_r8c_001::::active",
    "3LT_AH2_EL9::includes::opt_3f9_001::::active",
    "3LT_AH2_HZN::includes::opt_3n9_001::::active",
    "3LT_AH2_H8T::includes::opt_3a9_001::::active",
    "3LT_AH2_HUW::includes::opt_379_001::::active",
    "opt_bc4_002::includes::opt_d3v_001::coupe::active",
    "opt_bcp_002::includes::opt_d3v_001::coupe::active",
    "opt_bcs_002::includes::opt_d3v_001::coupe::active",
  ]) {
    assert.ok(ruleKeys.has(key), `${key} should be generated`);
  }

  const groupedBlockers = new Map(draft.ruleGroups.map((group) => [group.group_id, group]));
  for (const [groupId, sourceId] of [
    ["gs_group_r88_excludes_badge_and_stripe_choices", "opt_r88_001"],
    ["gs_group_sfz_excludes_badge_and_stripe_choices", "opt_sfz_001"],
  ]) {
    const group = groupedBlockers.get(groupId);
    assert.ok(group, `${groupId} should be generated`);
    assert.equal(group.group_type, "excludes_any");
    assert.equal(group.source_id, sourceId);
    assert.ok(group.target_ids.includes("opt_eyk_001"), `${groupId} should target EYK`);
    assert.equal(ruleKeys.has(`${sourceId}::excludes::opt_eyk_001::::active`), false, `${sourceId} should use grouped EYK exclusion`);
  }

  for (const legacyOptionId of ["opt_bc4_001", "opt_bcp_001", "opt_bcs_001"]) {
    assert.equal(
      draft.rules.some((rule) => rule.source_id === legacyOptionId || rule.target_id === legacyOptionId),
      false,
      `${legacyOptionId} should not appear in generated Grand Sport rules`
    );
  }

  const groundEffectsGroup = draft.exclusiveGroups.find((group) => group.group_id === "gs_excl_ground_effects");
  assert.deepEqual(JSON.parse(JSON.stringify(groundEffectsGroup.option_ids)), ["opt_cfl_001", "opt_cfz_001"]);

  const z15Group = draft.ruleGroups.find((group) => group.group_id === "gs_group_z15_excludes_non_center_stripes");
  assert.ok(z15Group, "Z15 grouped exclusion source should be present for Pass 3 runtime wiring");
  assert.equal(z15Group.group_type, "excludes_any");
  assert.equal(z15Group.source_id, "opt_z15_001");
  assert.deepEqual(JSON.parse(JSON.stringify(z15Group.target_ids)), nonCenterStripeOptionIds);

  for (const [groupId, sourceId, expectedTargets] of [
    ["gs_group_pda_excludes_stripes_and_z15", "opt_pda_001", [...fullLengthStripeOptionIds, "opt_z15_001"]],
    ["gs_group_sne_excludes_stripes_and_z15", "opt_sne_001", [...fullLengthStripeOptionIds, "opt_z15_001", "opt_sht_001", "opt_vpo_001"]],
    ["gs_group_sht_excludes_full_length_stripes", "opt_sht_001", [...fullLengthStripeOptionIds, "opt_z15_001", "opt_pda_001", "opt_sne_001", "opt_vpw_001"]],
    ["gs_group_vpo_excludes_jake_and_z15", "opt_vpo_001", ["opt_z15_001", "opt_pda_001", "opt_sne_001", "opt_vpw_001"]],
    ["gs_group_vpw_excludes_jake_rear_hash_peers", "opt_vpw_001", ["opt_sht_001", "opt_vpo_001"]],
    ["gs_group_dpb_excludes_jake_hood_graphics", "opt_dpb_001", ["opt_sht_001", "opt_sne_001"]],
  ]) {
    const group = draft.ruleGroups.find((candidate) => candidate.group_id === groupId);
    assert.ok(group, `${groupId} should be generated`);
    assert.equal(group.group_type, "excludes_any");
    assert.equal(group.source_id, sourceId);
    assert.deepEqual(JSON.parse(JSON.stringify(group.target_ids)), expectedTargets);
  }
  assert.equal(
    [...ruleKeys].some((key) => key.startsWith("opt_z15_001::requires::")),
    false,
    "Z15 should not require every heritage hash/stripe option as separate hard requirements"
  );
  for (const hashOptionId of heritageHashOptionIds) {
    assert.ok(ruleKeys.has(`${hashOptionId}::includes::opt_z15_001::::active`), `${hashOptionId} should auto-add Z15`);
    assert.equal(ruleKeys.has(`${hashOptionId}::requires::opt_z15_001::::active`), false, `${hashOptionId} should not require manual Z15`);
    for (const targetId of nonCenterStripeOptionIds) {
      assert.equal(ruleKeys.has(`${hashOptionId}::excludes::${targetId}::::active`), false, `${hashOptionId} should use the Z15 group to block ${targetId}`);
    }
    for (const targetId of heritageCenterStripeOptionIds) {
      assert.equal(ruleKeys.has(`${hashOptionId}::excludes::${targetId}::::active`), false, `${hashOptionId} should allow ${targetId}`);
    }
  }

  for (const centerStripeOptionId of heritageCenterStripeOptionIds) {
    assert.equal(ruleKeys.has(`${centerStripeOptionId}::requires::opt_d84_001::::active`), false, `${centerStripeOptionId} should not require D84`);
    assert.equal(ruleKeys.has(`${centerStripeOptionId}::excludes::opt_d84_001::::active`), false, `${centerStripeOptionId} should not exclude D84`);
  }
  assert.equal(
    draft.rules.some(
      (rule) =>
        heritageCenterStripeOptionIds.includes(rule.source_id) &&
        (rule.source_note || rule.original_detail_raw || "").includes("Requires (D84)")
    ),
    false,
    "Grand Sport center stripe rule notes should not preserve stale D84 requirement text"
  );

  const d84Choices = draft.choices.filter((choice) => choice.option_id === "opt_d84_001");
  const centerStripeChoices = draft.choices.filter((choice) => heritageCenterStripeOptionIds.includes(choice.option_id));
  assert.ok(d84Choices.length > 0, "D84 should still be emitted as a convertible roof option");
  assert.equal(
    d84Choices.every((choice) => (choice.body_style === "convertible" ? choice.status === "available" : choice.status === "unavailable")),
    true,
    "D84 should only be available, and therefore visible, on convertible choices"
  );
  assert.equal(
    d84Choices.filter((choice) => choice.status === "available").every((choice) => choice.description === "Painted nacelles and roof"),
    true,
    "D84 should keep the roof-option description"
  );
  assert.equal(
    centerStripeChoices.every(
      (choice) => choice.description === "Only available with Z15 Heritage Hash Marks. When D84 is selected, the roof will not include stripe."
    ),
    true,
    "Grand Sport center stripes should carry the workbook-authored Z15/D84 disclosure"
  );
});

test("Grand Sport draft suppresses reviewed inactive/deferred option rows without hiding selectable seatbelts", () => {
  const optionIds = new Set(draft.choices.map((choice) => choice.option_id));
  for (const optionId of ["opt_36s_001", "opt_37s_001", "opt_38s_001", "opt_r6p_001", "opt_r9v_001", "opt_r9w_001", "opt_r9y_001", "opt_u2k_001", "opt_cfv_001"]) {
    assert.equal(optionIds.has(optionId), false, `${optionId} should not be emitted as an active Grand Sport option`);
  }
  for (const optionId of ["opt_379_001", "opt_3a9_001", "opt_3f9_001", "opt_3m9_001", "opt_3n9_001"]) {
    assert.equal(optionIds.has(optionId), true, `${optionId} should remain selectable for Grand Sport`);
  }
  const defaultSeatbelt = draft.choices.find((choice) => choice.option_id === "opt_719_001");
  assert.equal(defaultSeatbelt.display_behavior, "default_selected");
  assert.equal(defaultSeatbelt.selectable, "True");

  const defaultBrakes = draft.choices.filter((choice) => choice.option_id === "opt_jx6_001");
  assert.equal(defaultBrakes.length, 6);
  assert.equal(defaultBrakes.every((choice) => choice.rpo === "JX6" && choice.status === "standard"), true);
  assert.equal(defaultBrakes.every((choice) => choice.display_behavior === "default_selected"), true);

  const coupeBc7Defaults = draft.choices.filter((choice) => choice.option_id === "opt_bc7_001" && choice.body_style === "coupe");
  assert.equal(coupeBc7Defaults.length, 3);
  assert.equal(coupeBc7Defaults.every((choice) => choice.rpo === "BC7" && choice.status === "standard"), true);
  assert.equal(coupeBc7Defaults.every((choice) => choice.display_behavior === "default_selected"), true);

  const convertibleBc7Choices = draft.choices.filter((choice) => choice.option_id === "opt_bc7_001" && choice.body_style === "convertible");
  assert.equal(convertibleBc7Choices.length, 3);
  assert.equal(convertibleBc7Choices.every((choice) => choice.display_behavior !== "default_selected"), true);

  const grandSportNgaDefaults = draft.choices.filter((choice) => choice.option_id === "opt_nga_001");
  assert.equal(grandSportNgaDefaults.length, 6);
  assert.equal(grandSportNgaDefaults.every((choice) => choice.rpo === "NGA" && choice.status === "standard"), true);
  assert.equal(grandSportNgaDefaults.every((choice) => choice.display_behavior === "default_selected"), true);

  const performanceBrakes = draft.choices.filter((choice) => choice.option_id === "opt_j56_001");
  assert.equal(performanceBrakes.length, 6);
  assert.equal(
    performanceBrakes.every(
      (choice) =>
        choice.rpo === "J56" &&
        choice.display_behavior === "display_only" &&
        choice.status === "available" &&
        choice.active === "True" &&
        choice.selectable === "False"
    ),
    true
  );
  assert.equal(draft.rules.some((rule) => rule.source_id === "opt_feb_001" && rule.rule_type === "includes" && rule.target_id === "opt_j56_001"), true);
  assert.equal(
    draft.rules.some(
      (rule) =>
        rule.source_id === "opt_feb_001" &&
        rule.rule_type === "excludes" &&
        rule.target_id === "opt_jx6_001" &&
        rule.runtime_action === "replace"
    ),
    true
  );
  assert.equal(
    draft.rules.some(
      (rule) =>
        rule.source_id === "opt_fey_001" &&
        rule.rule_type === "excludes" &&
        rule.target_id === "opt_jx6_001" &&
        rule.runtime_action === "replace"
    ),
    true
  );
  assert.equal(
    draft.rules.some(
      (rule) =>
        rule.source_id === "opt_fey_001" &&
        rule.rule_type === "excludes" &&
        rule.target_id === "opt_j56_001" &&
        rule.runtime_action === "replace"
    ),
    true
  );
  assert.equal(draft.rules.some((rule) => rule.source_id === "opt_fey_001" && rule.rule_type === "includes" && rule.target_id === "opt_j57_001"), true);
  assert.equal(draft.rules.some((rule) => rule.source_id === "opt_fey_001" && rule.rule_type === "includes" && rule.target_id === "opt_t0f_001"), true);
  assert.equal(draft.rules.some((rule) => rule.source_id === "opt_t0f_001" && rule.rule_type === "requires" && rule.target_id === "opt_feb_001"), false);
  assert.equal(draft.rules.some((rule) => rule.source_id === "opt_t0f_001" && rule.rule_type === "requires" && rule.target_id === "opt_j57_001"), true);
  assert.deepEqual(
    draft.ruleGroups.find((group) => group.group_id === "gs_group_t0f_z52_requirement"),
    {
      group_id: "gs_group_t0f_z52_requirement",
      group_type: "requires_any",
      source_id: "opt_t0f_001",
      target_ids: ["opt_feb_001", "opt_fey_001"],
      body_style_scope: "",
      trim_level_scope: "",
      variant_scope: "",
      disabled_reason: "Requires FEB Z52 Sport Performance Package or FEY Z52 Track Performance Package.",
      active: "True",
      notes: "T0F is available with FEB plus required J57, or included by FEY.",
    }
  );
  assert.deepEqual(
    draft.ruleGroups.find((group) => group.group_id === "gs_group_j57_z52_requirement"),
    {
      group_id: "gs_group_j57_z52_requirement",
      group_type: "requires_any",
      source_id: "opt_j57_001",
      target_ids: ["opt_feb_001", "opt_fey_001"],
      body_style_scope: "",
      trim_level_scope: "",
      variant_scope: "",
      disabled_reason: "Requires FEB Z52 Sport Performance Package or FEY Z52 Track Performance Package.",
      active: "True",
      notes: "J57 is selectable with FEB, or included by FEY.",
    }
  );
  assert.equal(draft.rules.some((rule) => rule.source_id === "opt_j57_001" && rule.rule_type === "includes" && rule.target_id === "opt_j6d_001"), false);
  assert.equal(
    draft.defaultSelectionRules.some(
      (rule) =>
        rule.rule_id === "gs_default_j6d_with_j57" &&
        rule.target_option_id === "opt_j6d_001" &&
        rule.condition_type === "when_selected_unless_selected_section" &&
        rule.condition_id === "opt_j57_001"
    ),
    true,
    "J57 should soft-default J6D through workbook-authored default metadata"
  );

  const d30 = draft.choices.find((choice) => choice.option_id === "opt_d30_001");
  assert.equal(d30.active, "True");
  assert.equal(d30.selectable, "False");
  assert.equal(d30.display_behavior, "display_only");

  const z15 = draft.choices.find((choice) => choice.option_id === "opt_z15_001");
  assert.equal(z15.active, "False");
  assert.equal(z15.status, "unavailable");
  assert.equal(z15.selectable, "False");

  const r6xChoices = draft.choices.filter((choice) => choice.option_id === "opt_r6x_001");
  assert.equal(r6xChoices.length, 6);
  assert.equal(r6xChoices.every((choice) => choice.active === "False" && choice.selectable === "False" && choice.display_behavior === "auto_only"), true);
});

test("interior grouping metadata is workbook-owned for active runtime models", () => {
  const scopeRows = workbookRows("model_interior_scope").filter((row) => ["stingray", "grand_sport", "z06"].includes(row.model_key) && row.active === "True");
  const requiredFields = [
    "interior_seat_label",
    "interior_color_family",
    "interior_material_family",
    "interior_leaf_label",
    "interior_group_display_order",
    "interior_hierarchy_levels",
    "grouping_source",
  ];
  for (const modelKey of ["stingray", "grand_sport", "z06"]) {
    const rows = scopeRows.filter((row) => row.model_key === modelKey);
    assert.ok(rows.length > 0, `${modelKey} should have active interior scope rows`);
    assert.equal(
      rows.every((row) => requiredFields.every((field) => row[field] !== undefined && String(row[field]).trim() !== "")),
      true,
      `${modelKey} active interior scope rows should carry workbook-owned grouping metadata`
    );
  }
  const z06Custom = scopeRows.find((row) => row.model_key === "z06" && row.interior_id === "3LZ_R6X_AH2_HUU");
  assert.equal(z06Custom?.interior_color_family, "Custom Interior trim and seat combinations");
  assert.equal(z06Custom?.interior_leaf_label, "Adrenaline Red interior / Jet Black seats");
});

test("Grand Sport draft includes model-scoped LT interiors with EL9 launch edition metadata", () => {
  assert.equal(draft.interiors.length, 132);
  assert.equal(draft.interiors.every((interior) => interior.active_for_grand_sport === true), true);
  assert.equal(draft.interiors.every((interior) => interior.active_for_stingray === false), true);

  const scopeRows = workbookRows("model_interior_scope").filter(
    (row) => row.model_key === "grand_sport" && row.active === "True"
  );
  assert.equal(scopeRows.length, draft.interiors.length);
  assert.deepEqual(
    draft.interiors.map((interior) => interior.interior_id).sort(),
    scopeRows.map((row) => row.interior_id).sort()
  );
  const componentRows = workbookRows("interior_components").filter(
    (row) => row.model_key === "grand_sport" && row.active === "True"
  );
  assert.ok(componentRows.length > 0, "expected active Grand Sport interior component rows");
  assert.equal(
    new Set(componentRows.map((row) => `${row.model_key}::${row.interior_id}::${row.rpo}::${row.component_type}`)).size,
    componentRows.length,
    "active Grand Sport interior component keys should be unique"
  );
  assert.match(interiorsSource, /load_model_interior_scope_map/);
  assert.match(interiorsSource, /load_interior_components/);
  assert.match(interiorsSource, /build_model_interiors/);
  assert.match(interiorsSource, /config\.interior_source_sheet/);
  assert.match(inspectionSource, /build_model_interiors/);
  assert.doesNotMatch(interiorsSource, /rows_from_sheet\(wb, ["']lt_interiors["']\)/);
  assert.doesNotMatch(interiorsSource, /source_sheet["']?: ["']lt_interiors["']/);
  assert.doesNotMatch(interiorsSource, /read_interior_reference|grouping_fields_for_interior|fallback_interior_trims|interior_component_metadata/);
  assert.doesNotMatch(inspectionSource, /rows_from_sheet\(wb, ["']lt_interiors["']\)/);
  assert.doesNotMatch(inspectionSource, /source_sheet["']?: ["']lt_interiors["']/);
  assert.doesNotMatch(
    activeInteriorPipelineSources,
    /interior_reference_path|stingray_interiors_refactor\.csv|grand_sport_interiors_refactor\.csv/,
    "active interior generation must not keep stale CSV reference config surfaces"
  );

  assert.equal(draft.interiors.every((interior) => interior.source_sheet === "lt_interiors"), true);
  const byId = new Map(draft.interiors.map((interior) => [interior.interior_id, interior]));
  for (const interiorId of ["3LT_AE4_EL9", "3LT_AH2_EL9"]) {
    const interior = byId.get(interiorId);
    assert.ok(interior, `${interiorId} should be available for Grand Sport`);
    assert.equal(interior.interior_code, "EL9");
    assert.equal(interior.requires_z25, "True");
    assert.match(interior.source_note, /Z25/);
    assert.equal(interior.interior_color_family, "Santorini Blue Dipped with Torch Red accents");
  }

  const ae4El9 = byId.get("3LT_AE4_EL9");
  const ah2El9 = byId.get("3LT_AH2_EL9");
  assert.equal(ah2El9.interior_choice_display_order < byId.get("3LT_AH2_HTE").interior_choice_display_order, true);
  assert.equal(ae4El9.interior_choice_display_order < byId.get("3LT_AE4_HTE").interior_choice_display_order, true);
  assert.equal(Number(ae4El9.price), 1995);
  assert.equal(Number(ah2El9.price), 1995);
  assert.deepEqual(
    JSON.parse(JSON.stringify(ae4El9.interior_components)),
    [{ rpo: "AE4", label: "AE4 Seat Upgrade", price: 595, component_type: "seat" }]
  );
});

test("Grand Sport draft keeps normalized display fields and raw rule evidence", () => {
  const cfl = draft.choices.find((choice) => choice.choice_id === "1lt_e07__opt_cfl_001");
  assert.ok(cfl, "CFL should be present in the draft");
  assert.equal(cfl.label, "Extended Front Splitter, Carbon Flash");
  assert.equal(cfl.source_option_name, "Extended Front Splitter, Carbon Flash");
  assert.equal(cfl.source_detail_raw, "1. Not available with (CFV/CFZ) ground effects.");
  assert.equal(cfl.step_key, "packages_performance");
});

test("Grand Sport draft applies active option assets from asset_map", () => {
  const brightRedCaliperChoices = draft.choices.filter((choice) => choice.option_id === "opt_j6f_001");
  assert.equal(brightRedCaliperChoices.length, 6);
  for (const choice of brightRedCaliperChoices) {
    assert.equal(
      choice.image_url,
      "https://stingraychevroletcorvette.com/wp-content/uploads/pictures/27vette/clpr_298_j6f.png"
    );
    assert.equal(choice.image_alt, "Bright Red-Painted Calipers");
    assert.equal(choice.image_fit, "cover");
    assert.equal(choice.image_position, "center");
  }

  const unmappedChoice = draft.choices.find((choice) => choice.option_id === "opt_cfl_001");
  assert.ok(unmappedChoice, "unmapped choice should still be present");
  assert.equal(Object.hasOwn(unmappedChoice, "image_url"), false);
  assert.equal(Object.hasOwn(unmappedChoice, "image_alt"), false);
});

test("Grand Sport draft section placement follows section_master step_key", () => {
  const sectionById = new Map(draft.sections.map((section) => [section.section_id, section]));
  assert.equal(sectionById.get("sec_gsha_001")?.step_key, "aero_exhaust_stripes_accessories");
  assert.equal(sectionById.get("sec_gsha_001")?.section_display_order, 10);
  assert.equal(sectionById.get("sec_gsce_001")?.step_key, "aero_exhaust_stripes_accessories");
  assert.equal(sectionById.get("sec_gsce_001")?.section_display_order, 20);
  assert.equal(sectionById.get("sec_stri_001")?.step_key, "aero_exhaust_stripes_accessories");
  assert.equal(sectionById.get("sec_stri_001")?.section_display_order, 30);
  assert.equal(sectionById.get("sec_exha_001")?.step_key, "packages_performance");
  assert.equal(sectionById.get("sec_exha_001")?.section_display_order, 40);
  assert.equal(sectionById.get("sec_whee_001")?.step_key, "wheels");
  assert.equal(sectionById.get("sec_perf_support_001")?.step_key, "wheels");
  assert.equal(sectionById.get("sec_perf_support_001")?.section_name, "Mechanical");
  assert.equal(sectionById.get("sec_perf_ground_001")?.step_key, "packages_performance");
  assert.equal(sectionById.get("sec_perf_ground_001")?.section_display_order, 50);
  assert.equal(sectionById.get("sec_perf_z52_001")?.step_key, "packages_performance");
  assert.equal(sectionById.get("sec_perf_z52_001")?.section_display_order, 10);
  assert.equal(sectionById.get("sec_perf_aero_001")?.step_key, "packages_performance");
  assert.equal(sectionById.get("sec_perf_aero_001")?.section_display_order, 40);
  assert.equal(sectionById.get("sec_perf_brake_001")?.step_key, "packages_performance");
  assert.equal(sectionById.get("sec_perf_brake_001")?.section_display_order, 20);
  assert.equal(sectionById.get("sec_cali_001")?.step_key, "wheels");
  assert.equal(sectionById.get("sec_lpoe_001")?.step_key, "accessories");
  assert.equal(sectionById.has("sec_lpow_001"), false, "LPO Wheels has no active Grand Sport choices in the draft");
  assert.equal(sectionById.get("sec_lpoi_001")?.step_key, "accessories");
});

test("Grand Sport draft standard equipment grouping is workbook-owned", () => {
  const trimRows = draft.standardEquipment.filter((item) => item.standard_equipment_group_type === "trim_equipment");
  assert.ok(trimRows.length > 0, "trim equipment rows should be tagged by generated workbook metadata");
  assert.equal(trimRows.every((item) => ["sec_1lte_001", "sec_2lte_001", "sec_3lte_001"].includes(item.section_id)), true);
});

test("Grand Sport and Z06 workbook place rear hash graphics outside the stripe radio section", () => {
  for (const [sheetName, modelLabel] of [["grandSport_options", "Grand Sport"], ["z06_options", "Z06"]]) {
    const rowsByOptionId = new Map(workbookRows(sheetName).map((row) => [row.option_id, row]));
    assert.equal(rowsByOptionId.get("opt_vpo_001")?.section_id, "sec_hash_001", `${modelLabel} VPO should be a rear hash choice`);
    assert.equal(rowsByOptionId.get("opt_vpw_001")?.section_id, "sec_hash_001", `${modelLabel} VPW should be a rear hash choice`);
    assert.equal(rowsByOptionId.get("opt_sht_001")?.section_id, "sec_stri_001", `${modelLabel} SHT should stay in the stripe section`);
    assert.equal(rowsByOptionId.get("opt_pda_001")?.section_id, "sec_jake_001", `${modelLabel} PDA should live outside stripe/hash radio sections so its includes can auto-add`);
    assert.equal(rowsByOptionId.get("opt_sne_001")?.section_id, "sec_stri_001", `${modelLabel} SNE should stay in the stripe section`);
  }

  for (const [sheetName, ruleIds] of [
    ["grandSport_rule_mapping", ["gs_rule_opt_pda_001_includes_opt_sne_001", "gs_rule_opt_pda_001_includes_opt_vpw_001"]],
    ["z06_rule_mapping", ["z06_rule_opt_pda_001_includes_opt_sne_001", "z06_rule_opt_pda_001_includes_opt_vpw_001"]],
  ]) {
    const rowsByRuleId = new Map(workbookRows(sheetName).map((row) => [row.rule_id, row]));
    for (const ruleId of ruleIds) {
      const row = rowsByRuleId.get(ruleId);
      assert.equal(row?.rule_type, "includes", `${ruleId} should remain an include rule`);
      assert.equal("generation_action" in row, false, `${ruleId} should not rely on generation_action lifecycle metadata`);
      assert.equal("normalization_status" in row, false, `${ruleId} should not rely on normalization_status lifecycle metadata`);
    }
  }
});

test("Grand Sport wheel choices keep new aluminum wheels in the existing workbook section", () => {
  const wheels = draft.choices
    .filter((choice) => choice.variant_id === "1lt_e07" && choice.section_id === "sec_whee_002")
    .sort((a, b) => Number(a.display_order) - Number(b.display_order))
    .map((choice) => [choice.rpo, choice.base_price, choice.display_order, choice.label]);

  assert.deepEqual(JSON.parse(JSON.stringify(wheels)), [
    ["SWM", 0, 10, "Pearl Nickel 10-Spoke Forged Aluminum Wheels"],
    ["SWN", 1095, 20, "Gloss Black 10-Spoke Forged Aluminum Wheels"],
    ["SWO", 1495, 30, "High-Polished 10-Spoke Forged Aluminum Wheels"],
    ["SWP", 1495, 40, "Carbon Flash Bright Polished-Face 10-Spoke Forged Aluminum Wheels"],
    ["ROU", 995, 41, "Pearl Nickel Forged Aluminum Wheels"],
    ["SON", 1095, 42, "Gloss Black Forged Aluminum Wheels"],
    ["SOM", 1495, 43, "Bright Polished Forged Aluminum Wheels"],
    ["ROX", 995, 44, "Carbon Flash with Machined Edge Forged Aluminum Wheels"],
    ["ROY", 11995, 50, "Carbon Flash-Painted Carbon Fiber Wheels"],
    ["ROZ", 13995, 60, "Visible Carbon Fiber Wheels"],
    ["STZ", 15500, 70, "Visible Carbon Fiber Red Stripe Wheels"],
  ]);
});

test("Grand Sport Jake graphics are selectable choices with rear hash graphics in the hash section", () => {
  for (const optionId of grandSportJakeOptionIds) {
    const choices = draft.choices.filter((choice) => choice.option_id === optionId);
    assert.equal(choices.length, 6, `${optionId} should be emitted for every Grand Sport variant`);
    assert.equal(choices.every((choice) => choice.section_id === jakeGraphicSectionByOptionId.get(optionId)), true);
    assert.equal(choices.every((choice) => choice.status === "available" && choice.selectable === "True"), true);
  }

  for (const optionId of ["opt_vpo_001", "opt_vpw_001"]) {
    const choices = draft.choices.filter((choice) => choice.option_id === optionId);
    assert.equal(choices.length, 6, `${optionId} should be emitted for every Grand Sport variant`);
    assert.equal(choices.every((choice) => choice.section_id === "sec_hash_001"), true);
  }

  const pdaPriceRules = new Set(
    draft.priceRules
      .filter((rule) => rule.condition_option_id === "opt_pda_001")
      .map((rule) => `${rule.target_option_id}:${rule.price_value}`)
  );
  assert.deepEqual([...pdaPriceRules].sort(), ["opt_sne_001:0", "opt_vpw_001:0"]);
});

test("Grand Sport draft preserves rule hot spots and normalization metadata for later phases", () => {
  assert.equal(draft.draftMetadata.candidateAvailableOrStandardChoices, 1284);
  assert.equal(draft.draftMetadata.fullVariantMatrixChoices, 1422);
  assert.equal(draft.draftMetadata.ruleDetailHotSpots.rows.length, 113);
  assert.equal(draft.draftMetadata.ruleDetailHotSpots.counts.special_package_review, 27);
  assert.equal(draft.draftMetadata.normalization.unresolvedIssues.length, 0);
  assert.equal(draft.draftMetadata.priceRuleSourceRows, draft.priceRules.length);
  assert.deepEqual(draft.draftMetadata.deferredSurfaces, []);
});
