import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";
import vm from "node:vm";

function makeElement() {
  return {
    textContent: "",
    innerHTML: "",
    value: "",
    dataset: {},
    listeners: {},
    addEventListener(type, listener) {
      this.listeners[type] = listener;
    },
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
    click() {
      this.listeners.click?.({ target: this });
    },
    change() {
      this.listeners.change?.({ target: this });
    },
  };
}

function loadDataWindow() {
  const context = { window: {} };
  vm.runInNewContext(fs.readFileSync("form-app/data.js", "utf8"), context);
  return context.window;
}

function loadRuntime() {
  const dataWindow = loadDataWindow();
  const downloads = [];
  const elements = new Map();
  const fetchCalls = [];
  const document = {
    querySelector(selector) {
      if (!elements.has(selector)) {
        const element = makeElement();
        if (selector === "#dealerSubmitModal") element.hidden = true;
        elements.set(selector, element);
      }
      return elements.get(selector);
    },
    createElement() {
      const element = makeElement();
      element.click = function () {
        downloads.push({
          filename: this.download,
          content: context.window.__lastBlobContent,
          type: context.window.__lastBlobType,
        });
      };
      return element;
    },
  };
  const context = {
    window: {
      ...dataWindow,
      __downloads: downloads,
      __lastBlobContent: "",
      __lastBlobType: "",
      scrollX: 0,
      scrollY: 0,
      scrollTo() {},
    },
    fetch: async (url, options = {}) => {
      fetchCalls.push({ url, options });
      return {
        ok: true,
        async json() {
          return { success: true, entry_id: 445566 };
        },
      };
    },
    document,
    fetchCalls,
    elements,
    Intl,
    Number,
    Set,
    Map,
    Boolean,
    Object,
    String,
    Date,
    URL: {
      createObjectURL() {
        return "";
      },
      revokeObjectURL() {},
    },
    Blob: class TestBlob {
      constructor(parts, options = {}) {
        context.window.__lastBlobContent = parts.join("");
        context.window.__lastBlobType = options.type || "";
      }
    },
  };
  const source = fs.readFileSync("form-app/app.js", "utf8").replace(
    /\ninit\(\);\s*$/,
    `
window.__testApi = {
  get activeModelKey() { return typeof activeModelKey === "undefined" ? undefined : activeModelKey; },
  get activeModelLabel() { return typeof activeModel === "undefined" ? undefined : activeModel.label; },
  get state() { return state; },
  get variants() { return typeof variants === "undefined" ? [] : variants; },
  get data() { return typeof data === "undefined" ? undefined : data; },
  activeChoiceRows,
  activateModel: typeof activateModel === "function" ? activateModel : undefined,
  resetDefaults,
  reconcileSelections,
  handleChoice,
  render,
  optionPrice,
  choiceDisplayPrice,
  currentOrder,
  compactOrder,
  plainTextOrderSummary,
    buildMarkdown,
    downloadBuild,
    openDealerSubmitModal,
    closeDealerSubmitModal,
    submitDealerBuild,
    dealerSubmissionPayload,
    fetchCalls,
    exportJson,
  exportCsv,
  downloads: window.__downloads,
  elements,
};
init();
`
  );
  vm.runInNewContext(source, context);
  return context.window.__testApi;
}

const expectedGrandSportExclusiveGroups = [
  {
    groupId: "gs_excl_ls6_engine_covers",
    optionIds: ["opt_bc7_001", "opt_bc4_002", "opt_bcp_002", "opt_bcs_002"],
  },
  {
    groupId: "gs_excl_center_caps",
    optionIds: ["opt_5zb_001", "opt_5zc_001", "opt_5zd_001"],
  },
  {
    groupId: "gs_excl_indoor_car_covers",
    optionIds: ["opt_rwh_001", "opt_wkr_001"],
  },
  {
    groupId: "gs_excl_rear_script_badges",
    optionIds: ["opt_rik_001", "opt_rin_001", "opt_sl8_001"],
  },
  {
    groupId: "gs_excl_suede_compartment_liners",
    optionIds: ["opt_sxb_001", "opt_sxr_001", "opt_sxt_001"],
  },
  {
    groupId: "gs_excl_ground_effects",
    optionIds: ["opt_cfl_001", "opt_cfz_001"],
  },
  {
    groupId: "gs_excl_z52_packages",
    optionIds: ["opt_feb_001", "opt_fey_001"],
  },
  {
    groupId: "gs_excl_exterior_accents",
    optionIds: ["opt_efr_001", "opt_edu_001"],
  },
  {
    groupId: "gs_excl_performance_brakes",
    optionIds: ["opt_j56_001", "opt_j57_001"],
  },
];

const expectedStingrayExclusiveGroups = [
  {
    groupId: "grp_ls6_engine_covers",
    optionIds: ["opt_bc7_001", "opt_bcp_001", "opt_bcs_001", "opt_bc4_001"],
  },
  {
    groupId: "grp_spoiler_high_wing",
    optionIds: ["opt_t0a_001", "opt_tvs_001", "opt_5zz_001", "opt_5zu_001"],
  },
  {
    groupId: "excl_center_caps",
    optionIds: ["opt_rxj_001", "opt_vwd_001", "opt_5zd_001", "opt_5zc_001", "opt_rxh_001"],
  },
  {
    groupId: "excl_indoor_car_covers",
    optionIds: ["opt_rwh_001", "opt_sl1_001", "opt_wkr_001", "opt_wkq_001"],
  },
  {
    groupId: "excl_outdoor_car_covers",
    optionIds: ["opt_rnx_001", "opt_rwj_001"],
  },
  {
    groupId: "excl_suede_trunk_liner",
    optionIds: ["opt_sxb_001", "opt_sxr_001", "opt_sxt_001"],
  },
];

test("generated app data exposes a multi-model registry with Stingray compatibility alias", () => {
  const dataWindow = loadDataWindow();
  const registry = dataWindow.CORVETTE_FORM_DATA;

  assert.ok(registry, "CORVETTE_FORM_DATA registry should exist");
  assert.equal(registry.defaultModelKey, "stingray");
  assert.deepEqual(Object.keys(registry.models).sort(), ["grandSport", "stingray"]);
  assert.equal(registry.models.stingray.label, "Stingray");
  assert.equal(registry.models.stingray.modelName, "Corvette Stingray");
  assert.equal(registry.models.grandSport.label, "Grand Sport");
  assert.equal(registry.models.grandSport.modelName, "Corvette Grand Sport");
  assert.equal(registry.models.grandSport.data.dataset.source_sheet, "grandSport_options");
  assert.ok(
    registry.models.grandSport.data.priceRules.some((rule) => rule.price_rule_id === "gs_pr_fey_j57_001"),
    "Grand Sport packaged data should include Grand Sport price rules"
  );
  assert.equal(
    registry.models.stingray.data.priceRules.some((rule) => rule.price_rule_id === "gs_pr_fey_j57_001"),
    false,
    "Grand Sport price rules should not leak into Stingray data"
  );
  assert.deepEqual(dataWindow.STINGRAY_FORM_DATA, registry.models.stingray.data);
  assert.deepEqual(
    JSON.parse(JSON.stringify(registry.models.grandSport.data.variants.map((variant) => variant.variant_id))),
    ["1lt_e07", "2lt_e07", "3lt_e07", "1lt_e67", "2lt_e67", "3lt_e67"]
  );
});

test("Grand Sport exclusive groups are model-scoped and Stingray groups are unchanged", () => {
  const dataWindow = loadDataWindow();
  const registry = dataWindow.CORVETTE_FORM_DATA;
  const grandSportGroups = registry.models.grandSport.data.exclusiveGroups;
  const stingrayGroups = registry.models.stingray.data.exclusiveGroups;

  assert.equal(grandSportGroups.length, expectedGrandSportExclusiveGroups.length);
  for (const expected of expectedGrandSportExclusiveGroups) {
    const group = grandSportGroups.find((item) => item.group_id === expected.groupId);
    assert.ok(group, `${expected.groupId} should be generated for Grand Sport`);
    assert.equal(group.selection_mode, "single_within_group");
    assert.deepEqual(JSON.parse(JSON.stringify(group.option_ids)), expected.optionIds);
  }

  assert.equal(stingrayGroups.length, expectedStingrayExclusiveGroups.length);
  for (const expected of expectedStingrayExclusiveGroups) {
    const group = stingrayGroups.find((item) => item.group_id === expected.groupId);
    assert.ok(group, `${expected.groupId} should remain generated for Stingray`);
    assert.equal(group.selection_mode, "single_within_group");
    assert.deepEqual(JSON.parse(JSON.stringify(group.option_ids)), expected.optionIds);
  }
});

test("Grand Sport exclusive group selections remove peer options without runtime branches", () => {
  for (const expected of expectedGrandSportExclusiveGroups) {
    const runtime = loadRuntime();
    runtime.activateModel("grandSport");
    runtime.state.bodyStyle = "coupe";
    runtime.state.trimLevel = "1LT";
    runtime.resetDefaults();
    runtime.reconcileSelections();

    if (expected.groupId === "gs_excl_ls6_engine_covers") {
      const coupeEngineAppearance = runtime.activeChoiceRows().find((choice) => choice.option_id === "opt_b6p_001");
      assert.ok(coupeEngineAppearance, "B6P should be active before testing Grand Sport coupe LS6 engine covers");
      runtime.handleChoice(coupeEngineAppearance);
    }

    const activeGroupChoices = expected.optionIds
      .map((optionId) => runtime.activeChoiceRows().find((choice) => choice.option_id === optionId))
      .filter(Boolean);
    assert.equal(activeGroupChoices.length >= 2, true, `${expected.groupId} should have at least two active Grand Sport choices`);
    const [firstChoice, secondChoice] = activeGroupChoices;
    const firstId = firstChoice.option_id;
    const secondId = secondChoice.option_id;
    assert.ok(firstChoice, `${firstId} should be active for Grand Sport`);
    assert.ok(secondChoice, `${secondId} should be active for Grand Sport`);

    runtime.handleChoice(firstChoice);
    runtime.handleChoice(secondChoice);

    assert.equal(runtime.state.selected.has(secondId), true, `${secondId} should remain selected`);
    assert.equal(runtime.state.userSelected.has(secondId), true, `${secondId} should remain user-selected`);
    assert.equal(runtime.state.selected.has(firstId), false, `${firstId} should be removed from selected`);
    assert.equal(runtime.state.userSelected.has(firstId), false, `${firstId} should be removed from userSelected`);
  }
});

test("Grand Sport heritage hash marks auto-add Z15 and leave only center stripes compatible", () => {
  const runtime = loadRuntime();
  runtime.activateModel("grandSport");
  runtime.state.bodyStyle = "coupe";
  runtime.state.trimLevel = "1LT";
  runtime.resetDefaults();
  runtime.reconcileSelections();

  const hashMark = runtime.activeChoiceRows().find((choice) => choice.option_id === "opt_17a_001");
  const centerStripe = runtime.activeChoiceRows().find((choice) => choice.option_id === "opt_dmu_001");
  const fullLengthStripe = runtime.activeChoiceRows().find((choice) => choice.option_id === "opt_dpb_001");
  const z15 = runtime.activeChoiceRows().find((choice) => choice.option_id === "opt_z15_001");

  assert.ok(hashMark, "17A should be active for Grand Sport");
  assert.ok(centerStripe, "DMU center stripe should be active for Grand Sport");
  assert.ok(fullLengthStripe, "DPB full length stripe should be active before compatibility filtering");
  assert.equal(z15.selectable, "False");

  runtime.handleChoice(hashMark);
  const afterHashOrder = runtime.currentOrder();
  assert.equal(afterHashOrder.auto_added_options.some((item) => item.rpo === "Z15"), true, "hash mark should auto-add Z15");

  runtime.handleChoice(fullLengthStripe);
  assert.equal(runtime.state.selected.has("opt_dpb_001"), false, "non-center stripes should be unavailable while a hash mark is selected");

  runtime.handleChoice(centerStripe);
  assert.equal(runtime.state.selected.has("opt_dmu_001"), true, "center stripes should remain selectable with a hash mark");
  const coupeD84 = runtime.activeChoiceRows().find((choice) => choice.option_id === "opt_d84_001");
  assert.equal(coupeD84.status, "unavailable", "D84 message should not display for coupe");

  runtime.state.bodyStyle = "convertible";
  runtime.state.trimLevel = "1LT";
  runtime.resetDefaults();
  runtime.reconcileSelections();
  const convertibleD84 = runtime.activeChoiceRows().find((choice) => choice.option_id === "opt_d84_001");
  assert.ok(convertibleD84, "D84 should remain visible for Grand Sport convertibles");
  assert.equal(convertibleD84.description, "Painted nacelles and roof");
  runtime.handleChoice(runtime.activeChoiceRows().find((choice) => choice.option_id === "opt_17a_001"));
  const convertibleCenterStripe = runtime.activeChoiceRows().find((choice) => choice.option_id === "opt_dmu_001");
  assert.equal(convertibleCenterStripe.description, "When D84 is selected, the roof will not include the stripe.");
  runtime.handleChoice(convertibleCenterStripe);
  assert.equal(runtime.state.selected.has("opt_dmu_001"), true, "center stripe should not require D84 on convertible");
  assert.equal(runtime.state.selected.has("opt_d84_001"), false, "center stripe should not auto-select D84");
});

test("Grand Sport UQT is selectable on 1LT and included on higher trims from workbook overrides", () => {
  const runtime = loadRuntime();
  runtime.activateModel("grandSport");
  runtime.state.bodyStyle = "coupe";
  runtime.state.trimLevel = "1LT";
  runtime.resetDefaults();
  runtime.reconcileSelections();

  let uqt = runtime.activeChoiceRows().find((choice) => choice.rpo === "UQT");
  assert.ok(uqt, "Grand Sport UQT should exist for 1LT");
  assert.equal(uqt.option_id, "opt_uqt_001");
  assert.equal(uqt.status, "available");
  assert.equal(uqt.selectable, "True");
  assert.equal(uqt.step_key, "interior_trim");

  runtime.handleChoice(uqt);
  let order = runtime.currentOrder();
  assert.equal(order.selected_options.some((item) => item.rpo === "UQT" && item.price === 1495), true);

  runtime.state.trimLevel = "2LT";
  runtime.resetDefaults();
  runtime.reconcileSelections();
  uqt = runtime.activeChoiceRows().find((choice) => choice.rpo === "UQT");
  assert.ok(uqt, "Grand Sport UQT should exist for 2LT");
  assert.equal(uqt.option_id, "opt_uqt_001");
  assert.equal(uqt.status, "standard");
  assert.equal(uqt.selectable, "False");
  assert.equal(uqt.step_key, "standard_equipment");

  order = runtime.currentOrder();
  assert.equal(order.selected_options.some((item) => item.rpo === "UQT"), false);
  assert.equal(runtime.data.standardEquipment.some((item) => item.variant_id === "2lt_e07" && item.rpo === "UQT"), true);
});

test("Grand Sport seat prices are workbook-scoped by trim", () => {
  const runtime = loadRuntime();
  runtime.activateModel("grandSport");
  runtime.state.bodyStyle = "coupe";
  runtime.state.trimLevel = "2LT";
  runtime.resetDefaults();
  runtime.reconcileSelections();

  const ah2 = runtime.activeChoiceRows().find((choice) => choice.option_id === "opt_ah2_001");
  const ae4 = runtime.activeChoiceRows().find((choice) => choice.option_id === "opt_ae4_002");
  assert.ok(ah2, "2LT AH2 seat should exist");
  assert.ok(ae4, "2LT AE4 seat should exist");
  assert.equal(runtime.choiceDisplayPrice(ah2), 1695, "2LT AH2 tile should preview the scoped price before selection");
  assert.equal(runtime.choiceDisplayPrice(ae4), 2095, "2LT AE4 tile should preview the scoped price before selection");
  runtime.handleChoice(ah2);
  assert.equal(runtime.optionPrice("opt_ah2_001"), 1695);
  runtime.handleChoice(ae4);
  assert.equal(runtime.optionPrice("opt_ae4_002"), 2095);

  runtime.state.trimLevel = "3LT";
  runtime.resetDefaults();
  runtime.reconcileSelections();
  const ae4ThreeLt = runtime.activeChoiceRows().find((choice) => choice.option_id === "opt_ae4_002");
  const aup = runtime.activeChoiceRows().find((choice) => choice.option_id === "opt_aup_001");
  assert.ok(ae4ThreeLt, "3LT AE4 seat should exist");
  assert.ok(aup, "3LT AUP seat should exist");
  assert.equal(runtime.choiceDisplayPrice(ae4ThreeLt), 595, "3LT AE4 tile should preview the scoped price before selection");
  assert.equal(runtime.choiceDisplayPrice(aup), 350, "3LT AUP tile should preview the scoped price before selection");
  runtime.handleChoice(ae4ThreeLt);
  assert.equal(runtime.optionPrice("opt_ae4_002"), 595);
  runtime.handleChoice(aup);
  assert.equal(runtime.optionPrice("opt_aup_001"), 350);
});

test("Grand Sport workbook default_selected rows seed and reconcile defaults generically", () => {
  const runtime = loadRuntime();
  runtime.activateModel("grandSport");
  runtime.state.bodyStyle = "coupe";
  runtime.state.trimLevel = "1LT";
  runtime.resetDefaults();
  runtime.reconcileSelections();

  for (const optionId of ["opt_efr_001", "opt_t0e_001", "opt_j56_001", "opt_719_001"]) {
    assert.equal(runtime.state.selected.has(optionId), true, `${optionId} should be selected from display_behavior=default_selected`);
  }

  const fey = runtime.activeChoiceRows().find((choice) => choice.option_id === "opt_fey_001");
  runtime.handleChoice(fey);
  assert.equal(runtime.state.selected.has("opt_fey_001"), true, "FEY should be selectable");
  assert.equal(runtime.state.selected.has("opt_t0e_001"), false, "FEY should replace the default T0E aero row");
  assert.equal(runtime.state.selected.has("opt_j56_001"), false, "FEY auto-added J57 should replace the default J56 brake row");

  const order = runtime.currentOrder();
  assert.equal(order.auto_added_options.some((item) => item.rpo === "J57"), true, "FEY should auto-add J57");
});

test("Grand Sport Pass 1 workbook rules drive engine, brake, ground-effect, and launch edition behavior", () => {
  const runtime = loadRuntime();
  runtime.activateModel("grandSport");
  runtime.state.bodyStyle = "coupe";
  runtime.state.trimLevel = "1LT";
  runtime.resetDefaults();
  runtime.reconcileSelections();

  for (const optionId of ["opt_bcp_002", "opt_bcs_002", "opt_bc4_002"]) {
    const cover = runtime.activeChoiceRows().find((choice) => choice.option_id === optionId);
    assert.ok(cover, `${optionId} should exist for Grand Sport`);
    runtime.handleChoice(cover);
    const order = runtime.currentOrder();
    assert.equal(order.auto_added_options.some((item) => item.rpo === "D3V" && item.price === 0), true, `${optionId} should auto-add D3V at $0`);
    assert.equal(order.auto_added_options.some((item) => item.rpo === "B6P"), false, `${optionId} should not auto-add B6P`);
  }

  const j57 = runtime.activeChoiceRows().find((choice) => choice.option_id === "opt_j57_001");
  const j56 = runtime.activeChoiceRows().find((choice) => choice.option_id === "opt_j56_001");
  runtime.handleChoice(j57);
  assert.equal(runtime.state.selected.has("opt_j57_001"), true, "J57 should be selected");
  assert.equal(runtime.state.selected.has("opt_j56_001"), false, "J57 should replace J56");
  runtime.handleChoice(j56);
  assert.equal(runtime.state.selected.has("opt_j56_001"), true, "J56 should be selectable again");
  assert.equal(runtime.state.selected.has("opt_j57_001"), false, "J56 should replace J57");

  const feb = runtime.activeChoiceRows().find((choice) => choice.option_id === "opt_feb_001");
  runtime.handleChoice(feb);
  runtime.handleChoice(j57);
  const t0f = runtime.activeChoiceRows().find((choice) => choice.option_id === "opt_t0f_001");
  const cfl = runtime.activeChoiceRows().find((choice) => choice.option_id === "opt_cfl_001");
  runtime.handleChoice(t0f);
  assert.equal(runtime.currentOrder().auto_added_options.some((item) => item.rpo === "CFZ" && item.price === 0), true, "T0F should auto-add CFZ at $0");
  runtime.handleChoice(cfl);
  assert.equal(runtime.state.selected.has("opt_cfl_001"), false, "CFL should remain blocked when T0F auto-adds CFZ");

  runtime.state.trimLevel = "3LT";
  runtime.resetDefaults();
  runtime.reconcileSelections();
  runtime.state.selectedInterior = "3LT_AH2_EL9";
  const launchOrder = runtime.currentOrder();
  assert.equal(launchOrder.selected_interior.price, 1995, "EL9 should own the Launch Edition price");
  assert.equal(launchOrder.auto_added_options.some((item) => item.rpo === "Z25" && item.price === 0), true, "Z25 should auto-add at $0");
});

test("runtime defaults to Stingray and switches models with a clean build reset", () => {
  const runtime = loadRuntime();
  assert.equal(runtime.activeModelKey, "stingray");
  assert.equal(runtime.activeModelLabel, "Stingray");
  assert.deepEqual(
    JSON.parse(JSON.stringify(runtime.variants.map((variant) => variant.variant_id))),
    ["1lt_c07", "2lt_c07", "3lt_c07", "1lt_c67", "2lt_c67", "3lt_c67"]
  );

  runtime.state.customer.name = "Ada Buyer";
  runtime.state.customer.email = "ada@example.com";
  runtime.state.bodyStyle = "coupe";
  runtime.state.trimLevel = "1LT";
  runtime.resetDefaults();
  runtime.reconcileSelections();
  const stingrayPaint = runtime.activeChoiceRows().find((choice) => choice.option_id === "opt_gba_001");
  assert.ok(stingrayPaint, "Stingray Black paint should exist before switching");
  runtime.handleChoice(stingrayPaint);
  assert.equal(runtime.state.selected.has("opt_gba_001"), true);

  const modelSelect = runtime.elements.get("#modelSelect");
  assert.ok(modelSelect, "model picker element should be wired");
  modelSelect.value = "grandSport";
  modelSelect.change();

  assert.equal(runtime.activeModelKey, "grandSport");
  assert.equal(runtime.activeModelLabel, "Grand Sport");
  assert.deepEqual(
    JSON.parse(JSON.stringify(runtime.variants.map((variant) => variant.variant_id))),
    ["1lt_e07", "2lt_e07", "3lt_e07", "1lt_e67", "2lt_e67", "3lt_e67"]
  );
  assert.equal(runtime.state.bodyStyle, "coupe");
  assert.equal(runtime.state.trimLevel, "1LT");
  assert.equal(runtime.state.activeStep, "body_style");
  assert.equal(runtime.state.selected.has("opt_gba_001"), false, "Stingray selected option should not survive model switch");
  assert.equal(runtime.state.selectedInterior, "");
  assert.equal(runtime.state.customer.name, "Ada Buyer");
  assert.equal(runtime.state.customer.email, "ada@example.com");
  assert.equal(runtime.activeChoiceRows().every((choice) => choice.variant_id.endsWith("_e07")), true);

  const grandSportOrder = runtime.compactOrder();
  assert.equal(grandSportOrder.title, "2027 Corvette Grand Sport");
  assert.match(runtime.plainTextOrderSummary(), /^2027 Corvette Grand Sport\n\n/);

  modelSelect.value = "stingray";
  modelSelect.change();
  assert.equal(runtime.activeModelKey, "stingray");
  assert.equal(runtime.state.selected.has("opt_gba_001"), false, "Grand Sport reset should not recreate prior user selections");
  assert.equal(runtime.activeChoiceRows().every((choice) => choice.variant_id.endsWith("_c07")), true);
  assert.equal(runtime.compactOrder().title, "2027 Corvette Stingray");
});

test("model-specific build downloads keep customer-facing Markdown and filenames", () => {
  const runtime = loadRuntime();

  runtime.state.bodyStyle = "coupe";
  runtime.state.trimLevel = "1LT";
  runtime.resetDefaults();
  runtime.reconcileSelections();
  runtime.handleChoice(runtime.activeChoiceRows().find((choice) => choice.option_id === "opt_gba_001"));
  runtime.state.selectedInterior = "1LT_AQ9_HTA";
  runtime.reconcileSelections();
  runtime.downloadBuild();
  let markdownDownload = runtime.downloads.at(-1);
  assert.equal(markdownDownload.filename, "stingray-build.md");
  assert.match(markdownDownload.content, /^# 2027 Corvette Stingray/);
  assert.match(markdownDownload.content, /### Variant\n\n- Corvette Stingray Coupe 1LT/);
  assert.doesNotMatch(markdownDownload.content, /Body Style:/);
  assert.doesNotMatch(markdownDownload.content, /Trim Level:/);
  assert.doesNotMatch(markdownDownload.content, /Standard & Included/);
  assert.doesNotMatch(markdownDownload.content, /Base MSRP/);

  runtime.activateModel("grandSport");
  runtime.state.bodyStyle = "coupe";
  runtime.state.trimLevel = "1LT";
  runtime.resetDefaults();
  runtime.reconcileSelections();
  runtime.handleChoice(runtime.activeChoiceRows().find((choice) => choice.option_id === "opt_gba_001"));
  runtime.state.selectedInterior = "1LT_AQ9_HTA";
  runtime.reconcileSelections();
  runtime.downloadBuild();
  markdownDownload = runtime.downloads.at(-1);
  assert.equal(markdownDownload.filename, "grand-sport-build.md");
  assert.match(markdownDownload.content, /^# 2027 Corvette Grand Sport/);
  assert.match(markdownDownload.content, /### Variant\n\n- Corvette Grand Sport Coupe 1LT/);
  assert.doesNotMatch(markdownDownload.content, /Standard & Included/);
  assert.doesNotMatch(markdownDownload.content, /Base MSRP/);
});

test("Grand Sport dealer submission payload stays model-scoped when posted", async () => {
  const runtime = loadRuntime();
  runtime.activateModel("grandSport");
  runtime.state.bodyStyle = "coupe";
  runtime.state.trimLevel = "1LT";
  runtime.resetDefaults();
  runtime.reconcileSelections();
  runtime.handleChoice(runtime.activeChoiceRows().find((choice) => choice.option_id === "opt_gba_001"));
  runtime.state.selectedInterior = "1LT_AQ9_HTA";
  runtime.reconcileSelections();
  runtime.render();

  runtime.openDealerSubmitModal();
  assert.equal(runtime.elements.get("#dealerSubmitModal").hidden, false);
  runtime.elements.get("#dealerSubmitName").value = "Ada Buyer";
  runtime.elements.get("#dealerSubmitEmail").value = "ada@example.com";
  const submission = await runtime.submitDealerBuild();
  assert.equal(submission.payload.model, "grandSport");
  assert.match(submission.payload.plain_text_summary, /^2027 Corvette Grand Sport\n\n/);
  assert.match(submission.payload.plain_text_summary, /VARIANT\nCorvette Grand Sport Coupe 1LT/);
  assert.doesNotMatch(submission.payload.plain_text_summary, /Base MSRP|STANDARD & INCLUDED/);
  assert.equal(submission.payload.customer.email, "ada@example.com");
  assert.match(submission.payload.msrp, /^\$\d{1,3}(,\d{3})*$/);
  assert.equal(submission.result.entry_id, 445566);
  assert.equal(JSON.parse(runtime.fetchCalls[0].options.body).model, "grandSport");
  assert.equal(JSON.parse(runtime.fetchCalls[0].options.body).msrp, submission.payload.msrp);
  assert.equal(runtime.elements.get("#dealerSubmitConfirmButton").hidden, true);
  assert.equal(await runtime.submitDealerBuild(), null);
  assert.equal(runtime.fetchCalls.length, 1, "Grand Sport dealer submission should not post duplicates after success");
});

test("Grand Sport Markdown export includes audited sections and auto-added options", () => {
  const runtime = loadRuntime();
  runtime.activateModel("grandSport");
  runtime.state.bodyStyle = "coupe";
  runtime.state.trimLevel = "3LT";
  runtime.resetDefaults();
  runtime.reconcileSelections();

  runtime.handleChoice(runtime.activeChoiceRows().find((choice) => choice.option_id === "opt_gba_001"));
  runtime.handleChoice(runtime.activeChoiceRows().find((choice) => choice.option_id === "opt_17a_001"));
  runtime.handleChoice(runtime.activeChoiceRows().find((choice) => choice.option_id === "opt_feb_001"));
  runtime.handleChoice(runtime.activeChoiceRows().find((choice) => choice.option_id === "opt_j57_001"));
  runtime.handleChoice(runtime.activeChoiceRows().find((choice) => choice.option_id === "opt_t0f_001"));
  runtime.state.selectedInterior = "3LT_AH2_EL9";
  runtime.reconcileSelections();

  const markdown = runtime.buildMarkdown();
  assert.match(markdown, /^# 2027 Corvette Grand Sport/);
  assert.match(markdown, /### Variant\n\n- Corvette Grand Sport Coupe 3LT/);
  for (const heading of ["Performance & Mechanical", "Stripes", "Seats & Interior", "Auto-Added / Required", "MSRP"]) {
    assert.match(markdown, new RegExp(`### ${heading}`), `${heading} should be present`);
  }
  assert.match(markdown, /- EL9 Santorini Blue Dipped with Torch Red accents: \$1,995/);
  assert.match(markdown, /- 17A .*: \$0/);
  assert.match(markdown, /- T0F .*: \$8,995/);
  assert.match(markdown, /- Z15 .*: \$995/);
  assert.match(markdown, /- Z25 .*: \$0/);
  assert.match(markdown, /- CFZ .*: \$0/);
  assert.match(markdown, /- 3F9 .*: \$0/);
  assert.doesNotMatch(markdown, /### [^\n]+\n\n### /, "empty sections should not be emitted");
  assert.doesNotMatch(markdown, /^## /m, "export sections should use h3 headings");
  assert.doesNotMatch(markdown, /Body Style:|Trim Level:|Standard & Included|Base MSRP|option_id/);
});

test("Grand Sport interiors are model-scoped and export selected interior identity", () => {
  const dataWindow = loadDataWindow();
  const registry = dataWindow.CORVETTE_FORM_DATA;
  const grandSportData = registry.models.grandSport.data;
  const stingrayData = registry.models.stingray.data;

  assert.equal(grandSportData.interiors.length, 132);
  assert.equal(
    grandSportData.interiors.some((interior) => interior.interior_id === "3LT_AH2_EL9" && interior.requires_z25 === "True"),
    true
  );
  assert.equal(
    stingrayData.interiors.some((interior) => interior.interior_id === "3LT_AH2_EL9"),
    false,
    "Stingray data must not reactivate Grand Sport-only EL9"
  );

  const runtime = loadRuntime();
  runtime.activateModel("grandSport");
  runtime.state.bodyStyle = "coupe";
  runtime.state.trimLevel = "3LT";
  runtime.resetDefaults();
  runtime.reconcileSelections();

  const ah2Seat = runtime.activeChoiceRows().find((choice) => choice.rpo === "AH2" && choice.step_key === "seat");
  assert.ok(ah2Seat, "Grand Sport AH2 seat should exist for 3LT");
  runtime.handleChoice(ah2Seat);
  assert.ok(runtime.currentOrder().metadata.missing_required.includes("Base Interior"));

  runtime.state.selectedInterior = "3LT_AH2_EL9";
  runtime.reconcileSelections();
  const order = runtime.currentOrder();
  assert.equal(order.metadata.selected_interior_id, "3LT_AH2_EL9");
  assert.equal(order.selected_interior.rpo, "EL9");
  assert.equal(order.selected_interior.label, "Santorini Blue Dipped with Torch Red accents");
  assert.equal(order.metadata.missing_required.includes("Base Interior"), false);
  assert.equal(runtime.state.selected.has("opt_719_001"), false, "EL9 included seatbelt should replace default 719");
  assert.equal(order.auto_added_options.some((item) => item.rpo === "3F9" && item.price === 0), true, "EL9 should auto-add 3F9 at no charge");

  const compact = runtime.compactOrder();
  const seatsInterior = compact.sections.find((section) => section.section === "Seats & Interior");
  assert.ok(seatsInterior, "compact Grand Sport order should include Seats & Interior");
  assert.ok(
    seatsInterior.items.some((item) => item.rpo === "EL9" && item.label === "Santorini Blue Dipped with Torch Red accents"),
    "compact order should include selected Grand Sport interior"
  );
  assert.match(runtime.plainTextOrderSummary(compact), /EL9 Santorini Blue Dipped with Torch Red accents/);
});

test("Grand Sport 3LT interiors auto-add included color seatbelts from workbook rules", () => {
  const runtime = loadRuntime();
  runtime.activateModel("grandSport");
  runtime.state.bodyStyle = "coupe";
  runtime.state.trimLevel = "3LT";
  runtime.resetDefaults();
  runtime.reconcileSelections();

  const ah2Seat = runtime.activeChoiceRows().find((choice) => choice.rpo === "AH2" && choice.step_key === "seat");
  runtime.handleChoice(ah2Seat);

  for (const [interiorId, rpo] of [
    ["3LT_AH2_HZN", "3N9"],
    ["3LT_AH2_HNK", "3F9"],
    ["3LT_AH2_H8T", "3A9"],
    ["3LT_AH2_HUW", "379"],
  ]) {
    runtime.state.selectedInterior = interiorId;
    runtime.reconcileSelections();
    const order = runtime.currentOrder();
    assert.equal(runtime.state.selected.has("opt_719_001"), false, `${interiorId} should replace default 719`);
    assert.equal(order.auto_added_options.some((item) => item.rpo === rpo && item.price === 0), true, `${interiorId} should auto-add ${rpo} at no charge`);
  }

  runtime.state.selectedInterior = "3LT_AH2_HTE";
  runtime.reconcileSelections();
  assert.equal(runtime.state.selected.has("opt_719_001"), true, "3LT interior without included color seatbelt should keep 719 default");
  assert.equal(runtime.currentOrder().auto_added_options.some((item) => ["3N9", "3F9", "3A9", "379"].includes(item.rpo)), false);
});
