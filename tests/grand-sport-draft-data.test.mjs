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

const expectedGrandSportExclusiveGroups = [
  {
    group_id: "gs_excl_ls6_engine_covers",
    option_ids: ["opt_bc7_001", "opt_bc4_001", "opt_bc4_002", "opt_bcp_001", "opt_bcp_002", "opt_bcs_001", "opt_bcs_002"],
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
  assert.equal(draft.steps.length, 14);
  assert.equal(draft.choices.length, 1530);
  assert.equal(draft.standardEquipment.length, 539);
  assert.equal(draft.choices.filter((choice) => choice.status === "available").length, 809);
  assert.equal(draft.choices.filter((choice) => choice.status === "standard").length, 539);
  assert.equal(draft.choices.filter((choice) => choice.status === "unavailable").length, 182);
});

test("Grand Sport draft emits color overrides while deferring price rules", () => {
  assert.equal(draft.rules.length > 0, true, "Grand Sport draft should include normalized compatibility rules");
  assert.deepEqual(draft.priceRules, []);
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
  assert.ok(warnings.has("grand_sport_draft_status"));
  assert.ok(warnings.has("pricing_deferred"));
  assert.equal(warnings.has("rules_deferred"), false);
  assert.equal(warnings.has("color_overrides"), false);
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
      assert.equal(choiceOptionIds.has(optionId), true, `${optionId} should exist in Grand Sport choices`);
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
    "opt_j57_001::includes::opt_j6d_001::::active",
    "opt_t0f_001::requires::opt_j57_001::::active",
    "opt_fey_001::includes::opt_t0f_001::::active",
    "opt_fey_001::includes::opt_cfz_001::::active",
    "opt_t0f_001::includes::opt_cfz_001::::active",
    "opt_bv4_001::excludes::opt_r8c_001::::active",
    "opt_r88_001::excludes::opt_eyk_001::::active",
    "opt_sfz_001::excludes::opt_eyk_001::::active",
    "opt_bc4_001::requires::opt_b6p_001::coupe::active",
    "opt_bc4_001::requires::opt_zz3_001::convertible::active",
  ]) {
    assert.ok(ruleKeys.has(key), `${key} should be generated`);
  }

  const groundEffectsGroup = draft.exclusiveGroups.find((group) => group.group_id === "gs_excl_ground_effects");
  assert.deepEqual(JSON.parse(JSON.stringify(groundEffectsGroup.option_ids)), ["opt_cfl_001", "opt_cfz_001"]);

  const z15RuleGroup = draft.ruleGroups.find((group) => group.group_id === "gs_grp_z15_hash_mark_requirement");
  assert.ok(z15RuleGroup, "Z15 should use the workbook-backed requires_any group");
  assert.equal(z15RuleGroup.group_type, "requires_any");
  assert.equal(z15RuleGroup.source_id, "opt_z15_001");
  assert.deepEqual(
    JSON.parse(JSON.stringify(z15RuleGroup.target_ids)),
    ["opt_17a_001", "opt_20a_001", "opt_55a_001", "opt_75a_001", "opt_97a_001", "opt_dx4_001"]
  );
  assert.equal(
    [...ruleKeys].some((key) => key.startsWith("opt_z15_001::requires::")),
    false,
    "Z15 should not require every heritage hash/stripe option as separate hard requirements"
  );
});

test("Grand Sport draft suppresses reviewed inactive/deferred option rows without hiding selectable seatbelts", () => {
  const optionIds = new Set(draft.choices.map((choice) => choice.option_id));
  for (const optionId of ["opt_36s_001", "opt_37s_001", "opt_38s_001", "opt_aup_001", "opt_r6p_001", "opt_r9v_001", "opt_r9w_001", "opt_r9y_001", "opt_u2k_001", "opt_cfv_001"]) {
    assert.equal(optionIds.has(optionId), false, `${optionId} should not be emitted as an active Grand Sport option`);
  }
  for (const optionId of ["opt_379_001", "opt_3a9_001", "opt_3f9_001", "opt_3m9_001", "opt_3n9_001"]) {
    assert.equal(optionIds.has(optionId), true, `${optionId} should remain selectable for Grand Sport`);
  }

  const d30 = draft.choices.find((choice) => choice.option_id === "opt_d30_001");
  assert.equal(d30.active, "True");
  assert.equal(d30.selectable, "False");

  const r6xChoices = draft.choices.filter((choice) => choice.option_id === "opt_r6x_001");
  assert.equal(r6xChoices.length, 6);
  assert.equal(r6xChoices.every((choice) => choice.active === "False" && choice.selectable === "False"), true);
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
  assert.equal(Number(ae4El9.price), 595);
  assert.equal(Number(ah2El9.price), 0);
  assert.deepEqual(
    JSON.parse(JSON.stringify(ae4El9.interior_components)),
    [{ rpo: "AE4", label: "AE4 Seat Upgrade", price: 595, component_type: "seat" }]
  );
});

test("Grand Sport draft keeps normalized display fields and raw rule evidence", () => {
  const cfl = draft.choices.find((choice) => choice.choice_id === "1lt_e07__opt_cfl_001");
  assert.ok(cfl, "CFL should be present in the draft");
  assert.equal(cfl.label, "New Ground Effects");
  assert.equal(cfl.source_option_name, "NEW!  Ground effects");
  assert.equal(cfl.source_detail_raw, "1. Not available with (CFV/CFZ) ground effects.");
  assert.equal(cfl.step_key, "packages_performance");
  assert.equal(cfl.category_id, "cat_mech_001");
});

test("Grand Sport draft preserves rule hot spots and normalization metadata for later phases", () => {
  assert.equal(draft.draftMetadata.candidateAvailableOrStandardChoices, 1354);
  assert.equal(draft.draftMetadata.fullVariantMatrixChoices, 1530);
  assert.equal(draft.draftMetadata.ruleDetailHotSpots.rows.length, 123);
  assert.equal(draft.draftMetadata.ruleDetailHotSpots.counts.special_package_review, 26);
  assert.equal(draft.draftMetadata.normalization.sectionCategoryResolutions.length, 55);
  assert.equal(draft.draftMetadata.normalization.unresolvedIssues.length, 0);
  assert.deepEqual(draft.draftMetadata.deferredSurfaces, ["priceRules"]);
});
