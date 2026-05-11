import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import fs from "node:fs";
import test from "node:test";

const draftPath = "form-output/inspection/grand-sport-form-data-draft.json";
const draftMarkdownPath = "form-output/inspection/grand-sport-form-data-draft.md";
const appDataPath = "form-app/data.js";

function generateDraftWithoutAppMutation() {
  const beforeAppData = fs.readFileSync(appDataPath, "utf8");
  execFileSync(".venv/bin/python", ["scripts/generate_grand_sport_form.py"], {
    encoding: "utf8",
    stdio: "pipe",
  });
  const afterAppData = fs.readFileSync(appDataPath, "utf8");
  assert.equal(afterAppData, beforeAppData, "Grand Sport draft generation must not mutate form-app/data.js");
  assert.ok(fs.existsSync(draftPath), "Grand Sport draft JSON should exist");
  assert.ok(fs.existsSync(draftMarkdownPath), "Grand Sport draft Markdown should exist");
  return JSON.parse(fs.readFileSync(draftPath, "utf8"));
}

const draft = generateDraftWithoutAppMutation();
const heritageHashOptionIds = ["opt_17a_001", "opt_20a_001", "opt_55a_001", "opt_75a_001", "opt_97a_001", "opt_dx4_001"];
const heritageCenterStripeOptionIds = ["opt_dmu_001", "opt_dmv_001", "opt_dmw_001", "opt_dmx_001", "opt_dmy_001"];
const nonCenterStripeOptionIds = [
  "opt_dpb_001", "opt_dpc_001", "opt_dpg_001", "opt_dpl_001", "opt_dpt_001", "opt_dsy_001", "opt_dsz_001", "opt_dt0_001",
  "opt_dth_001", "opt_dub_001", "opt_due_001", "opt_duk_001", "opt_duw_001", "opt_dzu_001", "opt_dzv_001", "opt_dzx_001",
  "opt_sht_001", "opt_vpo_001",
];
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
];

const expectedGrandSportExclusiveGroups = [
  {
    group_id: "gs_excl_ls6_engine_covers",
    option_ids: ["opt_bc7_001", "opt_bc4_002", "opt_bcp_002", "opt_bcs_002"],
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
  },
  {
    group_id: "gs_excl_performance_brakes",
    option_ids: ["opt_j56_001", "opt_j57_001"],
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
    "ruleGroups",
    "exclusiveGroups",
    "rules",
    "priceRules",
    "interiors",
    "colorOverrides",
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
  assert.equal(draft.steps.length, 15);
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
      ["base_interior", "Base Interior"],
      ["seat_belt", "Seat Belt"],
      ["interior_trim", "Interior Trim"],
      ["accessories", "Accessories"],
      ["delivery", "Custom Delivery"],
      ["customer_info", "Customer Information"],
      ["summary", "Summary"],
    ]
  );
  assert.equal(draft.choices.length, 1374);
  assert.equal(draft.standardEquipment.length, 455);
  assert.equal(draft.choices.filter((choice) => choice.status === "available").length, 761);
  assert.equal(draft.choices.filter((choice) => choice.status === "standard").length, 455);
  assert.equal(draft.choices.filter((choice) => choice.status === "unavailable").length, 158);
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
  ]);
  assert.deepEqual(JSON.parse(JSON.stringify(seatsForVariant("2lt_e07"))), [
    ["AQ9", "standard"],
    ["AH2", "available"],
    ["AE4", "available"],
  ]);
  assert.deepEqual(JSON.parse(JSON.stringify(seatsForVariant("3lt_e07"))), [
    ["AQ9", "unavailable"],
    ["AH2", "standard"],
    ["AE4", "available"],
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
    assert.equal(group.selection_mode, "single_within_group");
    assert.equal(group.active, "True");
    assert.deepEqual(JSON.parse(JSON.stringify(group.option_ids)), expected.option_ids);
    for (const optionId of expected.option_ids) {
      if (!["opt_bc4_001", "opt_bcp_001", "opt_bcs_001"].includes(optionId)) {
        assert.equal(choiceOptionIds.has(optionId), true, `${optionId} should exist in Grand Sport choices`);
      }
    }
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
    "opt_5jr_001::includes::opt_drg_001::::active",
    "opt_j6l_001::requires::opt_j57_001::::active",
    "opt_j6d_001::requires::opt_j57_001::::active",
    "opt_t0f_001::requires::opt_j57_001::::active",
    "opt_j57_001::excludes::opt_j6a_001::::replace",
    "opt_fey_001::excludes::opt_t0e_001::::replace",
    "opt_fey_001::includes::opt_t0f_001::::active",
    "opt_fey_001::includes::opt_cfz_001::::active",
    "opt_t0f_001::includes::opt_cfz_001::::active",
    "opt_bv4_001::excludes::opt_r8c_001::::active",
    "opt_r88_001::excludes::opt_eyk_001::::active",
    "opt_sfz_001::excludes::opt_eyk_001::::active",
    "3LT_AH2_EL9::includes::opt_3f9_001::::active",
    "3LT_AH2_HZN::includes::opt_3n9_001::::active",
    "3LT_AH2_H8T::includes::opt_3a9_001::::active",
    "3LT_AH2_HUW::includes::opt_379_001::::active",
  ]) {
    assert.ok(ruleKeys.has(key), `${key} should be generated`);
  }

  const groundEffectsGroup = draft.exclusiveGroups.find((group) => group.group_id === "gs_excl_ground_effects");
  assert.deepEqual(JSON.parse(JSON.stringify(groundEffectsGroup.option_ids)), ["opt_cfl_001", "opt_cfz_001"]);

  const z15Group = draft.ruleGroups.find((group) => group.group_id === "gs_group_z15_excludes_non_center_stripes");
  assert.ok(z15Group, "Z15 grouped exclusion source should be present for Pass 3 runtime wiring");
  assert.equal(z15Group.group_type, "excludes_any");
  assert.equal(z15Group.source_id, "opt_z15_001");
  assert.deepEqual(JSON.parse(JSON.stringify(z15Group.target_ids)), nonCenterStripeOptionIds);
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

  const d30 = draft.choices.find((choice) => choice.option_id === "opt_d30_001");
  assert.equal(d30.active, "False");
  assert.equal(d30.selectable, "False");
  assert.equal(d30.display_behavior, "auto_only");

  const z15 = draft.choices.find((choice) => choice.option_id === "opt_z15_001");
  assert.equal(z15.active, "False");
  assert.equal(z15.status, "unavailable");
  assert.equal(z15.selectable, "False");

  const r6xChoices = draft.choices.filter((choice) => choice.option_id === "opt_r6x_001");
  assert.equal(r6xChoices.length, 6);
  assert.equal(r6xChoices.every((choice) => choice.active === "False" && choice.selectable === "False" && choice.display_behavior === "auto_only"), true);
});

test("Grand Sport draft includes model-scoped LT interiors with EL9 launch edition metadata", () => {
  assert.equal(draft.interiors.length, 132);
  assert.equal(draft.interiors.every((interior) => interior.active_for_grand_sport === true), true);
  assert.equal(draft.interiors.every((interior) => interior.active_for_stingray === false), true);

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
  assert.equal(cfl.label, "New Extended Front Splitter Ground Effects");
  assert.equal(cfl.source_option_name, "NEW! Extended Front Splitter Ground Effects");
  assert.equal(cfl.source_detail_raw, "1. Not available with (CFV/CFZ) ground effects.");
  assert.equal(cfl.step_key, "packages_performance");
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
  assert.equal(sectionById.get("sec_exha_001")?.section_display_order, 30);
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

test("Grand Sport wheel choices use workbook display order by ascending price", () => {
  const wheels = draft.choices
    .filter((choice) => choice.variant_id === "1lt_e07" && choice.section_id === "sec_whee_002")
    .sort((a, b) => Number(a.display_order) - Number(b.display_order))
    .map((choice) => [choice.rpo, choice.base_price, choice.display_order]);

  assert.deepEqual(JSON.parse(JSON.stringify(wheels)), [
    ["SWM", 0, 10],
    ["SWN", 1095, 20],
    ["SWO", 1495, 30],
    ["SWP", 1495, 40],
    ["ROY", 11995, 50],
    ["ROZ", 13995, 60],
    ["STZ", 15500, 70],
  ]);
});

test("Grand Sport draft preserves rule hot spots and normalization metadata for later phases", () => {
  assert.equal(draft.draftMetadata.candidateAvailableOrStandardChoices, 1240);
  assert.equal(draft.draftMetadata.fullVariantMatrixChoices, 1374);
  assert.equal(draft.draftMetadata.ruleDetailHotSpots.rows.length, 129);
  assert.equal(draft.draftMetadata.ruleDetailHotSpots.counts.special_package_review, 26);
  assert.equal(draft.draftMetadata.normalization.unresolvedIssues.length, 0);
  assert.equal(draft.draftMetadata.priceRuleSourceRows, draft.priceRules.length);
  assert.deepEqual(draft.draftMetadata.deferredSurfaces, []);
});
