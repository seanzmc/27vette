import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";
import vm from "node:vm";

const appSource = fs.readFileSync("form-app/app.js", "utf8");

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

// Pass 3 §3.7 stage 9: the candidate lane points this harness at a temporary
// registry. No fallback if the override is set but unreadable — silently
// reading the published data.js would make the candidate stage pass while
// proving nothing about the candidate.
const DATA_JS_PATH = process.env.CORVETTE_FORM_DATA_JS || "form-app/data.js";

function loadDataWindow() {
  const context = { window: {} };
  vm.runInNewContext(fs.readFileSync(DATA_JS_PATH, "utf8"), context);
  return context.window;
}

function loadRuntime() {
  const dataWindow = loadDataWindow();
  const downloads = [];
  const elements = new Map();
  const fetchCalls = [];
  const turnstileCalls = [];
  const scrollCalls = [];
  const document = {
    querySelector(selector) {
      if (!elements.has(selector)) {
        const element = makeElement();
        if (selector === "#dealerSubmitModal" || selector === "#confirmActionModal") element.hidden = true;
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
      turnstile: {
        render(selector, options) {
          turnstileCalls.push({ fn: "render", selector, options });
          options.callback?.("test-turnstile-token");
          return "test-widget-id";
        },
        reset(widgetId) {
          turnstileCalls.push({ fn: "reset", widgetId });
        },
      },
      scrollX: 0,
      scrollY: 0,
      scrollTo(position = {}) {
        scrollCalls.push(position);
        if (typeof position.left === "number") this.scrollX = position.left;
        if (typeof position.top === "number") this.scrollY = position.top;
      },
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
    turnstileCalls,
    scrollCalls,
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
  requestModelChange: typeof requestModelChange === "function" ? requestModelChange : undefined,
  resetDefaults,
  reconcileSelections,
  handleChoice,
  handleContextChoice: typeof handleContextChoice === "function" ? handleContextChoice : undefined,
  computeAutoAdded,
  disableReasonForChoice,
  missingRequirementDetails,
  missingRequired,
  render,
  optionPrice,
  choiceDisplayPrice,
  adjustedInteriorDisplayPrice,
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
    turnstileCalls,
    scrollCalls,
    setWindowScroll: (x, y) => {
      window.scrollX = x;
      window.scrollY = y;
    },
    exportJson,
  exportCsv,
  renderChoiceCard,
  renderContextCard,
  renderInteriorGroups: typeof renderInteriorGroups === "function" ? renderInteriorGroups : undefined,
  formatTooltipContent: typeof formatTooltipContent === "function" ? formatTooltipContent : undefined,
  renderStepChoiceGroups: typeof renderStepChoiceGroups === "function" ? renderStepChoiceGroups : undefined,
  currentStepSummary: typeof currentStepSummary === "function" ? currentStepSummary : undefined,
  goToNextStep: typeof goToNextStep === "function" ? goToNextStep : undefined,
  activateStep: typeof activateStep === "function" ? activateStep : undefined,
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
    optionIds: ["opt_bc7_001", "opt_bcp_002", "opt_bcs_002", "opt_bc4_002"],
    selectionMode: "single_within_group",
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
    optionIds: ["opt_cfl_001", "opt_cfz_001", "opt_cfv_001"],
  },
  {
    groupId: "gs_excl_z52_packages",
    optionIds: ["opt_feb_001", "opt_fey_001"],
  },
  {
    groupId: "gs_excl_exhaust_path",
    optionIds: ["opt_nga_001", "opt_nwi_001"],
    selectionMode: "required_single_within_group",
  },
  {
    groupId: "gs_excl_performance_aero",
    optionIds: ["opt_t0e_001", "opt_t0f_001", "opt_5zv_001"],
    selectionMode: "required_single_within_group",
  },
  {
    groupId: "gs_excl_exterior_accents",
    optionIds: ["opt_efr_001", "opt_edu_001"],
    selectionMode: "required_single_within_group",
  },
  {
    groupId: "gs_excl_seat_belts",
    optionIds: ["opt_719_001", "opt_3n9_001", "opt_379_001", "opt_3a9_001", "opt_3f9_001", "opt_3m9_001"],
  },
  {
    groupId: "gs_excl_performance_brakes",
    optionIds: ["opt_jx6_001", "opt_j56_001", "opt_j57_001"],
    selectionMode: "required_single_within_group",
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
    groupId: "excl_rear_script_badges",
    optionIds: ["opt_rik_001", "opt_rin_001", "opt_sl8_001"],
  },
  {
    groupId: "excl_suede_trunk_liner",
    optionIds: ["opt_sxb_001", "opt_sxr_001", "opt_sxt_001"],
  },
  {
    groupId: "excl_ext_accents",
    optionIds: ["opt_efr_001", "opt_efy_001", "opt_edu_001"],
    selectionMode: "required_single_within_group",
  },
  {
    groupId: "excl_seat_belts",
    optionIds: ["opt_719_001", "opt_3n9_001", "opt_379_001", "opt_3a9_001", "opt_3f9_001", "opt_3m9_001"],
  },
  {
    groupId: "excl_exhaust_path",
    optionIds: ["opt_nga_001", "opt_nwi_001"],
    selectionMode: "required_single_within_group",
  },
];

const expectedTrimTooltips = {
  "1LT": "1LT is the car for driving purists who want the lightest Corvette possible, but one that's still very well equipped.",
  "2LT": "2LT adds a number of comfort and convenience features in addition to color-matched interior options.",
  "3LT": "3LT is the utmost in luxury performance, with a leather-wrapped interior.",
};

const expectedPaintImages = {
  GEC: ["opt_gec_001", "https://stingraychevroletcorvette.com/wp-content/uploads/pictures/27vette/paint/imgi_11_gec.png", "Pitch Gray Metallic"],
  GPH: ["opt_gph_001", "https://stingraychevroletcorvette.com/wp-content/uploads/pictures/27vette/paint/imgi_17_gph.png", "Red Mist Metallic Tintcoat"],
  G26: ["opt_g26_001", "https://stingraychevroletcorvette.com/wp-content/uploads/pictures/27vette/paint/imgi_16_g26.png", "Sebring Orange Tintcoat"],
  GBK: ["opt_gbk_001", "https://stingraychevroletcorvette.com/wp-content/uploads/pictures/27vette/paint/imgi_15_gbk.png", "Competition Yellow Tintcoat Metallic"],
  G4Z: ["opt_g4z_001", "https://stingraychevroletcorvette.com/wp-content/uploads/pictures/27vette/paint/imgi_13_g4z.png", "Roswell Green Metallic"],
  GKA: ["opt_gka_001", "https://stingraychevroletcorvette.com/wp-content/uploads/pictures/27vette/paint/imgi_12_gka.png", "Blade Silver Metallic"],
  GBA: ["opt_gba_001", "https://stingraychevroletcorvette.com/wp-content/uploads/pictures/27vette/paint/imgi_10_gba.png", "Black"],
  G8G: ["opt_g8g_001", "https://stingraychevroletcorvette.com/wp-content/uploads/pictures/27vette/paint/imgi_9_g8g.png", "Arctic White"],
  GKZ: ["opt_gkz_001", "https://stingraychevroletcorvette.com/wp-content/uploads/pictures/27vette/paint/imgi_8_gkz.png", "Torch Red"],
  GTR: ["opt_gtr_001", "https://stingraychevroletcorvette.com/wp-content/uploads/pictures/27vette/paint/imgi_14_gtr.png", "Admiral Blue Metallic"],
};

function sectionRpoOrder(data, sectionId) {
  const orderByRpo = new Map();
  for (const choice of data.choices.filter((item) => item.section_id === sectionId && item.active === "True")) {
    const order = Number(choice.display_order);
    if (!orderByRpo.has(choice.rpo) || order < orderByRpo.get(choice.rpo)) {
      orderByRpo.set(choice.rpo, order);
    }
  }
  return [...orderByRpo]
    .sort((a, b) => a[1] - b[1] || a[0].localeCompare(b[0]))
    .map(([rpo]) => rpo);
}

function relativeOrder(order, expectedRpos) {
  return order.filter((rpo) => expectedRpos.includes(rpo));
}

test("generated app data exposes a multi-model registry with Stingray compatibility alias", () => {
  const dataWindow = loadDataWindow();
  const registry = dataWindow.CORVETTE_FORM_DATA;

  assert.ok(registry, "CORVETTE_FORM_DATA registry should exist");
  assert.equal(registry.defaultModelKey, "stingray");
  assert.deepEqual(Object.keys(registry.models).sort(), [
    "grandSport",
    "grand_sport_x",
    "stingray",
    "z06",
    "zr1",
    "zr1x",
  ]);
  assert.equal(registry.models.stingray.label, "Stingray");
  assert.equal(registry.models.stingray.modelName, "Corvette Stingray");
  assert.equal(registry.models.grandSport.label, "Grand Sport");
  assert.equal(registry.models.grandSport.modelName, "Corvette Grand Sport");
  assert.equal(registry.models.grandSport.data.dataset.source_sheet, "grandSport_options");
  assert.equal(registry.models.z06.label, "Z06");
  assert.equal(registry.models.z06.modelName, "Corvette Z06");
  assert.equal(registry.models.z06.data.dataset.source_sheet, "z06_options");
  assert.equal(registry.models.z06.data.dataset.status, "runtime_active");
  assert.ok(
    registry.models.grandSport.data.priceRules.some((rule) => rule.price_rule_id === "gs_pr_fey_j57_001"),
    "Grand Sport packaged data should include Grand Sport price rules"
  );
  assert.equal(
    registry.models.stingray.data.priceRules.some((rule) => rule.price_rule_id === "gs_pr_fey_j57_001"),
    false,
    "Grand Sport price rules should not leak into Stingray data"
  );
  const stingrayBc7Default = registry.models.stingray.data.defaultSelectionRules.find((rule) => rule.rule_id === "default_bc7");
  assert.ok(stingrayBc7Default, "Stingray BC7 coupe default should be emitted from workbook default_selection_rules");
  assert.equal(stingrayBc7Default.target_option_id, "opt_bc7_001");
  assert.equal(stingrayBc7Default.condition_type, "always");
  assert.equal(stingrayBc7Default.body_style_scope, "coupe");
  const grandSportBc7Default = registry.models.grandSport.data.defaultSelectionRules.find((rule) => rule.rule_id === "gs_default_bc7_coupe");
  assert.ok(grandSportBc7Default, "Grand Sport BC7 coupe default should be emitted from workbook default_selection_rules");
  assert.equal(grandSportBc7Default.target_option_id, "opt_bc7_001");
  assert.equal(grandSportBc7Default.condition_type, "always");
  assert.equal(grandSportBc7Default.body_style_scope, "coupe");
  assert.deepEqual(dataWindow.STINGRAY_FORM_DATA, registry.models.stingray.data);
  assert.deepEqual(
    JSON.parse(JSON.stringify(registry.models.grandSport.data.variants.map((variant) => variant.variant_id))),
    ["1lt_e07", "2lt_e07", "3lt_e07", "1lt_e67", "2lt_e67", "3lt_e67"]
  );
  assert.deepEqual(
    JSON.parse(JSON.stringify(registry.models.z06.data.variants.map((variant) => variant.variant_id))),
    ["1lz_h07", "2lz_h07", "3lz_h07", "1lz_h67", "2lz_h67", "3lz_h67"]
  );
});

test("active roof option order preserves the established and reviewed model contracts", () => {
  const registry = loadDataWindow().CORVETTE_FORM_DATA;
  const sharedActiveRoofOrder = ["CF7", "C2Z", "CC3", "CM9", "D84", "D86"];
  const roofOrders = Object.fromEntries(
    Object.entries(registry.models).map(([modelKey, entry]) => [modelKey, sectionRpoOrder(entry.data, "sec_roof_001")])
  );

  for (const modelKey of ["stingray", "grandSport", "z06"]) {
    const order = roofOrders[modelKey];
    assert.deepEqual(
      relativeOrder(order, sharedActiveRoofOrder),
      sharedActiveRoofOrder,
      `${modelKey} should preserve the established active shared roof option order`
    );
  }

  assert.deepEqual(
    Object.entries(roofOrders)
      .filter(([, order]) => order.includes("CF8"))
      .map(([modelKey]) => modelKey),
    ["grandSport", "grand_sport_x"],
    "CF8 should remain active in the published Grand Sport and Grand Sport X contracts"
  );
});

test("active registry models carry generated order-summary metadata without browser fallbacks", () => {
  for (const forbiddenSymbol of ["orderSectionDefinitions", "orderSectionLabels", "orderSectionOrder", "stepOrderSectionKeys"]) {
    assert.doesNotMatch(appSource, new RegExp(`\\b${forbiddenSymbol}\\b`), `${forbiddenSymbol} should not remain in app.js`);
  }
  assert.doesNotMatch(appSource, /Object\.fromEntries\(stepOrderSectionKeys\)/);
  assert.doesNotMatch(appSource, /orderSectionDefinitions\.map/);

  const registry = loadDataWindow().CORVETTE_FORM_DATA;
  const requiredChargesModels = new Set(["z06", "zr1", "zr1x"]);
  for (const [modelKey, entry] of Object.entries(registry.models)) {
    const expectsRequiredCharges = requiredChargesModels.has(modelKey);
    const expectedOrderSummarySections = expectsRequiredCharges ? 12 : 11;
    const expectedOrderSummaryStepMap = expectsRequiredCharges ? 14 : 13;
    assert.equal(entry.data.steps.length, 14, `${modelKey} should emit generated runtime steps`);
    assert.equal(entry.data.orderSummary.sections.length, expectedOrderSummarySections, `${modelKey} should emit order-summary sections`);
    assert.equal(Object.keys(entry.data.orderSummary.stepMap).length, expectedOrderSummaryStepMap, `${modelKey} should emit order-summary step map`);
    assert.equal(entry.data.orderSummary.stepMap.base_interior, "seats_interior", `${modelKey} should map interiors from generated metadata`);
    assert.equal(
      Object.hasOwn(entry.data.orderSummary.stepMap, "standard_equipment"),
      expectsRequiredCharges,
      `${modelKey} should map standard equipment exactly when its generated summary includes required charges`
    );
  }
});

test("runtime fails loudly when generated order-summary metadata is missing", () => {
  const missingSectionsRuntime = loadRuntime();
  missingSectionsRuntime.state.bodyStyle = "coupe";
  missingSectionsRuntime.state.trimLevel = "1LT";
  missingSectionsRuntime.resetDefaults();
  delete missingSectionsRuntime.data.orderSummary.sections;
  assert.throws(
    () => missingSectionsRuntime.currentOrder(),
    /Missing generated orderSummary\.sections metadata for active model stingray/
  );

  const missingStepMapRuntime = loadRuntime();
  missingStepMapRuntime.state.bodyStyle = "coupe";
  missingStepMapRuntime.state.trimLevel = "1LT";
  missingStepMapRuntime.resetDefaults();
  missingStepMapRuntime.data.orderSummary.stepMap = {};
  assert.throws(
    () => missingStepMapRuntime.currentOrder(),
    /Missing generated orderSummary\.stepMap metadata for active model stingray/
  );
});

test("Z06 trim selector and build summary render workbook-owned standard equipment", () => {
  const runtime = loadRuntime();
  runtime.activateModel("z06");
  runtime.state.bodyStyle = "coupe";
  runtime.state.trimLevel = "2LZ";
  runtime.resetDefaults();
  runtime.reconcileSelections();
  runtime.activateStep("trim_level");

  const trimHtml = runtime.elements.get("#stepContent").innerHTML;
  assert.match(trimHtml, /See what this trim includes/);
  assert.match(trimHtml, /20 included items/);
  assert.doesNotMatch(trimHtml, /No standard equipment rows for this variant/);

  const order = runtime.currentOrder();
  assert.equal(order.standard_equipment_summary.count > 0, true);
  assert.equal(
    order.standard_equipment_summary.groups.some((group) => group.section_label === "2LZ Equipment"),
    true
  );
});

test("generated app data applies active model assets from asset_map", () => {
  const dataWindow = loadDataWindow();
  const registry = dataWindow.CORVETTE_FORM_DATA;

  assert.equal(
    registry.models.stingray.image_url,
    "https://stingraychevroletcorvette.com/wp-content/uploads/pictures/27vette/stingray.png"
  );
  assert.equal(registry.models.stingray.image_alt, "Corvette Stingray");
  assert.equal(registry.models.stingray.image_fit, "cover");
  assert.equal(registry.models.stingray.image_position, "center");

  assert.equal(
    registry.models.grandSport.image_url,
    "https://stingraychevroletcorvette.com/wp-content/uploads/pictures/27vette/grandsport.png"
  );
  assert.equal(registry.models.grandSport.image_alt, "Corvette Grand Sport");
  assert.equal(registry.models.grandSport.image_fit, "cover");
  assert.equal(registry.models.grandSport.image_position, "center");
});

test("generated context choices apply workbook-owned trim tooltips to both models", () => {
  const dataWindow = loadDataWindow();
  const registry = dataWindow.CORVETTE_FORM_DATA;

  for (const modelKey of ["stingray", "grandSport"]) {
    const trimChoices = registry.models[modelKey].data.contextChoices.filter(
      (choice) => choice.context_type === "trim_level"
    );
    assert.equal(trimChoices.length, 6);
    for (const choice of trimChoices) {
      assert.equal(choice.info_tooltip, expectedTrimTooltips[choice.value]);
      assert.equal(choice.description.includes(choice.value), true);
    }
  }
});

test("generated Stingray paint choices apply active image assets from asset_map", () => {
  const dataWindow = loadDataWindow();
  const paintChoices = dataWindow.CORVETTE_FORM_DATA.models.stingray.data.choices.filter(
    (choice) => choice.variant_id === "1lt_c07" && choice.section_id === "sec_pain_001"
  );

  assert.equal(paintChoices.length, Object.keys(expectedPaintImages).length);
  for (const choice of paintChoices) {
    const [optionId, imageUrl, imageAlt] = expectedPaintImages[choice.rpo];
    assert.equal(choice.option_id, optionId);
    assert.equal(choice.image_url, imageUrl);
    assert.equal(choice.image_alt, imageAlt);
    assert.equal(choice.image_fit, "cover");
    assert.equal(choice.image_position, "center");
  }
});

test("runtime renders vehicle setup as one paced visible foundation step", () => {
  const runtime = loadRuntime();
  runtime.render();

  const railHtml = runtime.elements.get("#stepRail").innerHTML;
  const setupHtml = runtime.elements.get("#stepContent").innerHTML;

  assert.match(railHtml, /Vehicle Setup/);
  assert.doesNotMatch(railHtml, />\s*2\s*<\/span>\s*Body Style/);
  assert.doesNotMatch(railHtml, />\s*3\s*<\/span>\s*Trim Level/);
  assert.match(railHtml, /Exterior Paint/);
  assert.equal(runtime.state.vehicleSetupStage, "model");
  assert.match(setupHtml, /data-vehicle-setup-stage="model"/);
  assert.match(setupHtml, /vehicle-setup-stepper/);
  assert.match(setupHtml, /data-model-choice="stingray"/);
  assert.doesNotMatch(setupHtml, /data-context-choice="body_style__/);
  assert.doesNotMatch(setupHtml, /data-context-choice="trim_level__/);
  assert.match(setupHtml, /Continue to Body Style/);
  assert.doesNotMatch(setupHtml, /Continue to Exterior Paint/);
});

test("generated registry supplies complete workbook-authored vehicle setup copy", () => {
  const registry = loadDataWindow().CORVETTE_FORM_DATA;
  for (const model of Object.values(registry.models)) {
    assert.equal(typeof model.vehicleSetup.cardSubtitle, "string");
    assert.equal(typeof model.vehicleSetup.eyebrow, "string");
    assert.equal(typeof model.vehicleSetup.title, "string");
    assert.equal(typeof model.vehicleSetup.description, "string");
    assert.equal(model.vehicleSetup.facts.length, 3);
    assert.equal(model.vehicleSetup.facts.every(Boolean), true);
  }
  assert.equal(registry.models.grandSport.vehicleSetup.cardSubtitle, "Purist, rear-wheel-drive performance");
  assert.equal(registry.models.z06.vehicleSetup.cardSubtitle, "Track-born, street-legal supercar");
});

test("runtime progressively advances vehicle setup panels before exterior paint", () => {
  const runtime = loadRuntime();
  const convertible = runtime.data.contextChoices.find((choice) => choice.context_choice_id === "body_style__convertible");
  const trim = runtime.data.contextChoices.find((choice) => choice.context_choice_id === "trim_level__convertible__2lt");

  assert.equal(runtime.state.activeStep, "model");
  assert.equal(runtime.state.vehicleSetupStage, "model");

  runtime.requestModelChange("grandSport");
  assert.equal(runtime.activeModelKey, "grandSport");
  assert.equal(runtime.state.activeStep, "model");
  assert.equal(runtime.state.vehicleSetupStage, "model");
  assert.match(runtime.elements.get("#stepContent").innerHTML, /Purist, rear-wheel-drive performance/);
  assert.doesNotMatch(runtime.elements.get("#stepContent").innerHTML, /data-context-choice="body_style__convertible"/);

  runtime.goToNextStep();
  assert.equal(runtime.state.vehicleSetupStage, "body_style");
  assert.match(runtime.elements.get("#stepContent").innerHTML, /data-context-choice="body_style__convertible"/);
  assert.doesNotMatch(runtime.elements.get("#stepContent").innerHTML, /data-context-choice="trim_level__convertible__2lt"/);

  runtime.handleContextChoice(convertible);
  assert.equal(runtime.state.bodyStyle, "convertible");
  assert.equal(runtime.state.vehicleSetupStage, "body_style");
  assert.match(runtime.elements.get("#stepContent").innerHTML, /Hardtop convertible character/);
  assert.doesNotMatch(runtime.elements.get("#stepContent").innerHTML, /data-context-choice="trim_level__convertible__2lt"/);

  runtime.goToNextStep();
  assert.equal(runtime.state.vehicleSetupStage, "trim_level");
  assert.match(runtime.elements.get("#stepContent").innerHTML, /data-context-choice="trim_level__convertible__2lt"/);

  runtime.handleContextChoice(trim);
  assert.equal(runtime.state.trimLevel, "2LT");
  assert.equal(runtime.state.vehicleSetupStage, "trim_level");
  assert.equal(runtime.state.activeStep, "model");
  const trimSetupHtml = runtime.elements.get("#stepContent").innerHTML;
  assert.match(trimSetupHtml, /<h4>2LT adds a number of comfort and convenience features/);
  assert.match(trimSetupHtml, /<p>Trim Level defines your available interior configuration, creature comforts, and safety features\.<\/p>/);
  assert.match(trimSetupHtml, /2LT adds a number[\s\S]*Trim Level defines your available interior configuration/);
  assert.match(trimSetupHtml, /Safety features/);
  assert.doesNotMatch(trimSetupHtml, /2LT defines the cabin and included equipment/);
  assert.doesNotMatch(trimSetupHtml, /Included equipment baseline|Next: exterior paint/);
  assert.match(trimSetupHtml, /See what this trim includes/);
  assert.match(trimSetupHtml, /vehicle-setup-equipment-disclosure/);
  assert.match(trimSetupHtml, /vehicle-setup-equipment-list/);
  assert.doesNotMatch(trimSetupHtml, /vehicle-setup-equipment-body/);
  assert.doesNotMatch(trimSetupHtml, /<details class="standard-group"/);
  assert.doesNotMatch(trimSetupHtml, /<details class="vehicle-setup-equipment-disclosure" open/);
  assert.doesNotMatch(trimSetupHtml, /sets the comfort and finish level/);
  assert.match(trimSetupHtml, /Continue to Exterior Paint/);

  runtime.goToNextStep();
  assert.equal(runtime.state.activeStep, "paint");
  assert.equal(runtime.currentStepSummary().step.step_key, "paint");
  assert.equal(runtime.currentStepSummary().previous.step_key, "model");
});

test("runtime preserves viewport while switching models inside vehicle setup", () => {
  const runtime = loadRuntime();
  runtime.setWindowScroll(0, 640);
  runtime.scrollCalls.length = 0;

  runtime.requestModelChange("grandSport");

  assert.equal(runtime.activeModelKey, "grandSport");
  assert.equal(runtime.state.vehicleSetupStage, "model");
  assert.equal(runtime.scrollCalls.at(-1).top, 640);
  assert.equal(runtime.scrollCalls.at(-1).left, 0);
  assert.ok(!runtime.scrollCalls.some((call) => call.top === 0), "model switch should not reset viewport to top");
});

test("runtime preserves viewport while moving between vehicle setup stages", () => {
  const runtime = loadRuntime();
  runtime.setWindowScroll(0, 720);
  runtime.scrollCalls.length = 0;

  runtime.goToNextStep();

  assert.equal(runtime.state.vehicleSetupStage, "body_style");
  assert.equal(runtime.scrollCalls.at(-1).top, 720);
  assert.equal(runtime.scrollCalls.at(-1).left, 0);
  assert.ok(!runtime.scrollCalls.some((call) => call.top === 0), "setup stage advance should not reset viewport to top");

  runtime.setWindowScroll(0, 540);
  runtime.scrollCalls.length = 0;
  runtime.goToNextStep();

  assert.equal(runtime.state.vehicleSetupStage, "trim_level");
  assert.equal(runtime.scrollCalls.at(-1).top, 540);
  assert.ok(!runtime.scrollCalls.some((call) => call.top === 0), "second setup stage advance should not reset viewport to top");
});

test("runtime routes direct body and trim step activation back to vehicle setup", () => {
  const runtime = loadRuntime();

  runtime.activateStep("trim_level");

  assert.equal(runtime.state.activeStep, "model");
  assert.match(runtime.elements.get("#stepContent").innerHTML, /Vehicle Setup/);
});

test("runtime keeps body and trim choices functional inside vehicle setup", () => {
  const runtime = loadRuntime();
  const convertible = runtime.data.contextChoices.find((choice) => choice.context_choice_id === "body_style__convertible");
  const trim = runtime.data.contextChoices.find((choice) => choice.context_choice_id === "trim_level__convertible__2lt");

  runtime.state.activeStep = "model";
  runtime.render();
  runtime.state.bodyStyle = "coupe";
  runtime.state.trimLevel = "1LT";
  runtime.resetDefaults();
  runtime.reconcileSelections();
  runtime.handleContextChoice(convertible);
  runtime.handleContextChoice(trim);

  const order = runtime.currentOrder();
  assert.equal(runtime.state.bodyStyle, "convertible");
  assert.equal(runtime.state.trimLevel, "2LT");
  assert.equal(order.vehicle.body_style, "convertible");
  assert.equal(order.vehicle.trim_level, "2LT");
  assert.equal(order.vehicle.display_name, "Corvette Stingray Convertible 2LT");
  assert.equal(order.vehicle.base_price, 87595);
});

test("runtime renders Stingray paint image media from generated choice data", () => {
  const runtime = loadRuntime();
  const paintChoice = runtime.data.choices.find(
    (choice) => choice.variant_id === "1lt_c07" && choice.option_id === "opt_g8g_001"
  );

  const html = runtime.renderChoiceCard(paintChoice, new Map());
  assert.match(html, /choice-media/);
  assert.match(html, /imgi_9_g8g\.png/);
  assert.match(html, /Arctic White/);
});

test("runtime renders disabled media and active tooltip pills for disabled context choices", () => {
  const runtime = loadRuntime();
  const html = runtime.renderContextCard({
    context_choice_id: "disabled_trim_for_test",
    context_type: "trim_level",
    value: "3LT",
    label: "3LT",
    description: "Corvette Grand Sport Convertible 3LT",
    info_tooltip: "Trim tooltip",
    body_style: "convertible",
    trim_level: "3LT",
    base_price: 0,
    image_url: "https://example.test/trim.png",
    image_alt: "Convertible 3LT",
    image_fit: "cover",
  });

  assert.match(html, /choice-card context-choice-card has-media disabled/);
  assert.match(html, /choice-media disabled/);
  assert.match(html, /<div class="choice-availability">[\s\S]*choice-state disabled-reason info-tooltip" tabindex="0"/);
});

test("runtime renders context choice tooltips without replacing visible trim descriptions", () => {
  const runtime = loadRuntime();
  const html = runtime.renderContextCard({
    context_choice_id: "trim_level__coupe__1lt",
    context_type: "trim_level",
    value: "1LT",
    label: "1LT",
    description: "Corvette Stingray Coupe 1LT",
    info_tooltip: expectedTrimTooltips["1LT"],
    body_style: "coupe",
    trim_level: "1LT",
    variant_id: "1lt_c07",
    base_price: 73495,
    display_order: 1,
  });

  assert.match(html, /Corvette Stingray Coupe 1LT/);
  assert.match(html, /info-tooltip/);
  assert.match(html, /1LT details/);
  assert.match(html, /driving purists/);
});

test("runtime formats long includes tooltips into escaped RPO bullet lists", () => {
  const runtime = loadRuntime();
  assert.equal(typeof runtime.formatTooltipContent, "function");

  const longTooltip = "LPO. Includes (SB7) Corvette Racing Themed Graphics Package with Jake and Stingray R logos and (VWD) Stingray R logo wheel center caps. Genuine Corvette Accessory.";
  const html = runtime.formatTooltipContent(longTooltip);
  assert.match(html, /tooltip-content structured/);
  assert.match(html, /<ul class="tooltip-list">/);
  assert.match(html, /<span class="tooltip-code">SB7<\/span>/);
  assert.match(html, /Corvette Racing Themed Graphics Package/);
  assert.match(html, /<span class="tooltip-code">VWD<\/span>/);
  assert.match(html, /Stingray R logo wheel center caps/);
  assert.match(html, /Genuine Corvette Accessory/);

  assert.equal(runtime.formatTooltipContent("Short trim detail."), "Short trim detail.");
  assert.doesNotMatch(runtime.formatTooltipContent("Includes (ABC) <img src=x onerror=alert(1)> and (DEF) safe accessory details.".repeat(2)), /<img/);
});

test("runtime renders include relationship badges without exclusive or required choice pills", () => {
  const runtime = loadRuntime();
  const stingrayCover = runtime.activeChoiceRows().find((choice) => choice.option_id === "opt_bc7_001");
  let html = runtime.renderChoiceCard(stingrayCover, new Map());
  assert.doesNotMatch(html, /choice-relationship-badge exclusive/);
  assert.doesNotMatch(html, /Choose one/);
  assert.doesNotMatch(html, /data-exclusive-group="grp_ls6_engine_covers"/);

  const stingrayPackage = runtime.activeChoiceRows().find((choice) => choice.option_id === "opt_pdv_001");
  html = runtime.renderChoiceCard(stingrayPackage, new Map());
  assert.match(html, /choice-relationship-badge includes/);
  assert.doesNotMatch(html, /choice-relationship-badge includes info-tooltip/);
  assert.match(html, /Includes 2 items/);
  assert.doesNotMatch(html, /<span class="tooltip-trigger-text">Includes 2 items<\/span>/);
  assert.doesNotMatch(html, /SB7 Corvette Racing Themed Jake and Stingray R Graphics Package/);
  assert.doesNotMatch(html, /VWD Stingray R Logo Wheel Center Caps/);
  assert.doesNotMatch(html, /Workbook includes|Workbook-defined/);
  assert.doesNotMatch(html, /choice-relationship-badge includes[\s\S]*info-icon/);
  assert.doesNotMatch(html, /choice-relationship-badge includes[\s\S]*tooltip-panel/);
  assert.match(html, /choice-name[\s\S]*info-tooltip/);

  const disabledIncludesChoice = runtime.activeChoiceRows().find((choice) => choice.option_id === "opt_fe4_001");
  html = runtime.renderChoiceCard(disabledIncludesChoice, new Map());
  assert.match(html, /choice-relationship-badge includes disabled/);
  assert.doesNotMatch(html, /choice-relationship-badge includes disabled info-tooltip/);
  assert.doesNotMatch(html, /<span class="tooltip-trigger-text">Includes 1 item<\/span>/);

  runtime.activateModel("grandSport");
  const requiredBrake = runtime.activeChoiceRows().find((choice) => choice.option_id === "opt_j57_001");
  html = runtime.renderChoiceCard(requiredBrake, new Map());
  assert.doesNotMatch(html, /Required choice/);
  assert.doesNotMatch(html, /choice-relationship-badge required/);
  assert.doesNotMatch(html, /data-exclusive-group="gs_excl_performance_brakes"/);
});

test("runtime groups visible exclusive-group peers within option sections", () => {
  const runtime = loadRuntime();
  runtime.activateModel("grandSport");
  runtime.state.activeStep = "packages_performance";
  runtime.render();

  const html = runtime.elements.get("#stepContent").innerHTML;
  assert.match(html, /choice-relation-group/);
  assert.match(html, /Related options/);
  assert.doesNotMatch(html, /Choose one required option|Choose one of these related options/);
  assert.doesNotMatch(html, /choice-relation-count/);
  assert.match(html, /data-choice-relation-group="gs_excl_performance_brakes"/);
  assert.match(html, /data-option="opt_jx6_001"/);
  assert.match(html, /data-option="opt_j56_001"/);
  assert.match(html, /data-option="opt_j57_001"/);
  assert.doesNotMatch(html, /Choose one|Choose up to one|Choose any that apply/);
  assert.doesNotMatch(html, /Required choice|choice-relationship-badge required|choice-relationship-badge exclusive/);
  assert.match(html, /required-mark/);
  assert.doesNotMatch(html, /Required single choice|Optional multiple choice/);
});

test("runtime avoids duplicate Interior Color headings and keeps interior groups interactive", () => {
  const runtime = loadRuntime();
  runtime.activateModel("grandSport");
  runtime.state.bodyStyle = "convertible";
  runtime.state.trimLevel = "2LT";
  runtime.resetDefaults();
  runtime.reconcileSelections();
  runtime.state.activeStep = "base_interior";
  runtime.render();

  const html = runtime.elements.get("#stepContent").innerHTML;
  assert.match(html, /<h2>Interior Color<\/h2>/);
  assert.doesNotMatch(html, /<div class="section-title"><h3>Interior Color<\/h3>/);
  assert.match(html, /selected-seat-context/);
  assert.match(html, /interior-group/);
  assert.match(html, /interior-group-header/);
});

test("runtime renders selected RPO summary as sectioned rows matching export sections", () => {
  const runtime = loadRuntime();
  runtime.state.bodyStyle = "coupe";
  runtime.state.trimLevel = "1LT";
  runtime.resetDefaults();
  runtime.reconcileSelections();
  runtime.handleChoice(runtime.activeChoiceRows().find((choice) => choice.option_id === "opt_gba_001"));
  runtime.handleChoice(runtime.activeChoiceRows().find((choice) => choice.option_id === "opt_pdv_001"));
  runtime.state.selectedInterior = "1LT_AQ9_HTA";
  runtime.reconcileSelections();
  runtime.render();

  const selectedHtml = runtime.elements.get("#selectedList").innerHTML;
  const exportedSections = runtime.compactOrder().sections.map((section) => section.section);
  assert.ok(exportedSections.includes("Exterior Paint"));
  assert.match(selectedHtml, /summary-section-heading/);
  assert.match(selectedHtml, /Exterior Paint/);
  const sectionHeadings = [...selectedHtml.matchAll(/<div class="summary-section-heading">[\s\S]*?<\/div>/g)].map((match) => match[0]);
  assert.ok(sectionHeadings.length > 0);
  assert.ok(sectionHeadings.every((heading) => !/\$[0-9]/.test(heading)));
  assert.match(selectedHtml, /summary-rpo-code/);
  assert.match(selectedHtml, /summary-rpo-label/);
  assert.match(selectedHtml, /summary-rpo-price/);
  assert.match(selectedHtml, /GBA/);
  assert.match(selectedHtml, /SB7/);
  assert.match(selectedHtml, /VWD/);

  const autoHtml = runtime.elements.get("#autoList").innerHTML;
  assert.match(autoHtml, /No auto-added RPOs/);
  assert.doesNotMatch(autoHtml, /summary-rpo-row/);
});

test("Grand Sport exclusive groups are model-scoped and Stingray groups match workbook output", () => {
  const dataWindow = loadDataWindow();
  const registry = dataWindow.CORVETTE_FORM_DATA;
  const grandSportGroups = registry.models.grandSport.data.exclusiveGroups;
  const stingrayGroups = registry.models.stingray.data.exclusiveGroups;

  assert.equal(grandSportGroups.length, expectedGrandSportExclusiveGroups.length);
  for (const expected of expectedGrandSportExclusiveGroups) {
    const group = grandSportGroups.find((item) => item.group_id === expected.groupId);
    assert.ok(group, `${expected.groupId} should be generated for Grand Sport`);
    assert.equal(group.selection_mode, expected.selectionMode || "single_within_group");
    assert.deepEqual(JSON.parse(JSON.stringify(group.option_ids)), expected.optionIds);
  }

  assert.equal(stingrayGroups.length, expectedStingrayExclusiveGroups.length);
  for (const expected of expectedStingrayExclusiveGroups) {
    const group = stingrayGroups.find((item) => item.group_id === expected.groupId);
    assert.ok(group, `${expected.groupId} should remain generated for Stingray`);
    assert.equal(group.selection_mode, expected.selectionMode || "single_within_group");
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
    if (expected.groupId === "gs_excl_performance_aero") continue;
    if (expected.groupId === "gs_excl_performance_brakes") {
      const feb = runtime.activeChoiceRows().find((choice) => choice.option_id === "opt_feb_001");
      assert.ok(feb, "FEB should be active before testing J57 as a Grand Sport performance brake peer");
      runtime.handleChoice(feb);
    }
    if (expected.groupId === "gs_excl_exhaust_path") {
      const wub = runtime.activeChoiceRows().find((choice) => choice.option_id === "opt_wub_001");
      assert.ok(wub, "WUB should be active before testing NWI as a Grand Sport exhaust peer");
      runtime.handleChoice(wub);
    }

    const activeGroupChoices = expected.optionIds
      .map((optionId) => runtime.activeChoiceRows().find((choice) => choice.option_id === optionId))
      .filter((choice) => choice?.display_behavior !== "auto_only")
      .filter((choice) => choice?.selectable === "True")
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

test("Grand Sport Z52 packages keep direct replacement peers unavailable", () => {
  const runtime = loadRuntime();
  runtime.activateModel("grandSport");
  runtime.state.bodyStyle = "coupe";
  runtime.state.trimLevel = "1LT";
  runtime.resetDefaults();
  runtime.reconcileSelections();

  const choice = (optionId) => runtime.activeChoiceRows().find((candidate) => candidate.option_id === optionId);
  const autoAddedRpos = () => runtime.currentOrder().auto_added_options.map((item) => item.rpo).sort();

  assert.equal(runtime.state.selected.has("opt_t0e_001"), true, "T0E should start as the Grand Sport default aero choice");
  assert.equal(runtime.state.selected.has("opt_jx6_001"), true, "JX6 should start as the Grand Sport default brake choice");

  runtime.handleChoice(choice("opt_feb_001"));
  assert.equal(runtime.state.selected.has("opt_feb_001"), true, "FEB should remain selected");
  assert.equal(runtime.state.selected.has("opt_jx6_001"), false, "FEB included J56 should suppress JX6 through the brake group");
  assert.equal(autoAddedRpos().includes("J56"), true, "FEB should auto-add display-only J56");
  assert.equal(runtime.disableReasonForChoice(choice("opt_jx6_001")), "FEB includes J56 performance disc brakes.");
  assert.equal(runtime.disableReasonForChoice(choice("opt_j57_001")), "", "FEB should leave J57 optional");
  runtime.handleChoice(choice("opt_jx6_001"));
  assert.equal(runtime.state.selected.has("opt_jx6_001"), false, "blocked JX6 should not reselect while FEB is selected");

  runtime.handleChoice(choice("opt_fey_001"));
  assert.equal(runtime.state.selected.has("opt_feb_001"), false, "FEY should replace FEB in the Z52 package group");
  assert.equal(runtime.state.selected.has("opt_fey_001"), true, "FEY should remain selected");
  assert.equal(runtime.state.selected.has("opt_t0e_001"), false, "FEY included T0F should suppress T0E through the aero group");
  assert.equal(runtime.state.selected.has("opt_jx6_001"), false, "FEY included J57 should suppress JX6 through the brake group");
  assert.equal(autoAddedRpos().includes("J56"), false, "FEY should remove FEB's J56 include");
  assert.equal(autoAddedRpos().includes("J57"), true, "FEY should auto-add J57");
  assert.equal(autoAddedRpos().includes("T0F"), true, "FEY should auto-add T0F");
  assert.equal(runtime.state.selected.has("opt_j6d_001"), true, "J57 should still soft-default J6D as a selected caliper");
  assert.equal(runtime.disableReasonForChoice(choice("opt_jx6_001")), "FEY includes J57 carbon ceramic brakes.");
  assert.equal(runtime.disableReasonForChoice(choice("opt_j56_001")), "FEY includes J57 carbon ceramic brakes.");
  assert.equal(runtime.disableReasonForChoice(choice("opt_t0e_001")), "FEY replaces the low rear spoiler with the included carbon fiber aero package.");
  assert.match(runtime.disableReasonForChoice(choice("opt_cfv_001")), /included with (?:FEY|T0F)/i);
  runtime.handleChoice(choice("opt_jx6_001"));
  runtime.handleChoice(choice("opt_t0e_001"));
  runtime.handleChoice(choice("opt_cfv_001"));
  assert.equal(runtime.state.selected.has("opt_jx6_001"), false, "blocked JX6 should not reselect while FEY is selected");
  assert.equal(runtime.state.selected.has("opt_t0e_001"), false, "blocked T0E should not reselect while FEY is selected");
  assert.equal(runtime.state.selected.has("opt_cfv_001"), false, "blocked CFV should not suppress FEY-included CFZ");

  runtime.handleChoice(choice("opt_fey_001"));
  assert.equal(runtime.state.selected.has("opt_fey_001"), false, "FEY should be removable as an optional package");
  assert.equal(runtime.state.selected.has("opt_t0e_001"), true, "T0E should restore when no aero peer remains");
  assert.equal(runtime.state.selected.has("opt_jx6_001"), true, "JX6 should restore when no brake peer remains");
  assert.equal(autoAddedRpos().some((rpo) => ["J56", "J57", "T0F"].includes(rpo)), false);
});

test("Grand Sport 5ZV high wing satisfies the required aero choice", () => {
  const runtime = loadRuntime();
  runtime.activateModel("grandSport");
  runtime.state.bodyStyle = "coupe";
  runtime.state.trimLevel = "1LT";
  runtime.resetDefaults();
  runtime.reconcileSelections();

  const choice = (optionId) => runtime.activeChoiceRows().find((candidate) => candidate.option_id === optionId);
  const fiveZv = choice("opt_5zv_001");
  assert.ok(fiveZv, "5ZV should be active for Grand Sport");
  assert.equal(runtime.state.selected.has("opt_t0e_001"), true, "T0E should start as the Grand Sport default aero choice");

  runtime.handleChoice(fiveZv);
  runtime.reconcileSelections();

  assert.equal(runtime.state.selected.has("opt_5zv_001"), true, "5ZV should remain selected");
  assert.equal(runtime.state.selected.has("opt_t0e_001"), false, "5ZV should replace the T0E aero default");
  assert.equal(
    runtime.missingRequirementDetails().some((item) => item.label === "Aero Packages"),
    false,
    "5ZV should satisfy the required Grand Sport aero group"
  );
});

test("GBA paint blocks EDU but not CFL across active models", () => {
  for (const [modelKey, hasCfl] of [["stingray", false], ["grandSport", true], ["z06", true]]) {
    const runtime = loadRuntime();
    runtime.activateModel(modelKey);
    runtime.resetDefaults();
    runtime.reconcileSelections();

    const choiceByRpo = (rpo) => runtime.activeChoiceRows().find((choice) => choice.rpo === rpo);
    const gba = choiceByRpo("GBA");
    const edu = choiceByRpo("EDU");
    assert.ok(gba, `${modelKey} should expose GBA`);
    assert.ok(edu, `${modelKey} should expose EDU`);

    runtime.handleChoice(gba);
    runtime.reconcileSelections();

    assert.match(runtime.disableReasonForChoice(edu), /GBA|black paint|EDU/i, `${modelKey} GBA should block EDU`);
    runtime.handleChoice(edu);
    runtime.reconcileSelections();
    assert.equal(runtime.state.selected.has(edu.option_id), false, `${modelKey} EDU should not stick with GBA selected`);

    const cfl = choiceByRpo("CFL");
    if (hasCfl) {
      assert.ok(cfl, `${modelKey} should expose CFL`);
      assert.equal(runtime.disableReasonForChoice(cfl), "", `${modelKey} GBA should not block CFL`);
    } else {
      assert.equal(cfl, undefined, `${modelKey} has no CFL choice to block`);
    }
  }
});

test("Grand Sport required exclusive groups cannot be left empty", () => {
  const runtime = loadRuntime();
  runtime.activateModel("grandSport");
  runtime.state.bodyStyle = "coupe";
  runtime.state.trimLevel = "1LT";
  runtime.resetDefaults();
  runtime.reconcileSelections();

  for (const expected of expectedGrandSportExclusiveGroups.filter(
    (group) =>
      group.selectionMode === "required_single_within_group" &&
      !["gs_excl_performance_brakes", "gs_excl_performance_aero"].includes(group.groupId)
  )) {
    if (expected.groupId === "gs_excl_ls6_engine_covers") {
      const coupeEngineAppearance = runtime.activeChoiceRows().find((choice) => choice.option_id === "opt_b6p_001");
      assert.ok(coupeEngineAppearance, "B6P should be active before testing Grand Sport coupe LS6 engine covers");
      runtime.handleChoice(coupeEngineAppearance);
    }
    const activeGroupChoices = expected.optionIds
      .map((optionId) => runtime.activeChoiceRows().find((choice) => choice.option_id === optionId))
      .filter((choice) => choice?.selectable === "True")
      .filter(Boolean);
    assert.equal(activeGroupChoices.length >= 2, true, `${expected.groupId} should have switchable required choices`);
    const [defaultChoice, alternateChoice] = activeGroupChoices;

    runtime.handleChoice(defaultChoice);
    assert.equal(runtime.state.selected.has(defaultChoice.option_id), true, `${defaultChoice.option_id} should not unselect as the last required choice`);

    if (expected.groupId === "gs_excl_exhaust_path") {
      const wub = runtime.activeChoiceRows().find((choice) => choice.option_id === "opt_wub_001");
      assert.ok(wub, "WUB should be active before testing NWI as a Grand Sport exhaust peer");
      runtime.handleChoice(wub);
    }

    runtime.handleChoice(alternateChoice);
    assert.equal(runtime.state.selected.has(alternateChoice.option_id), true, `${alternateChoice.option_id} should be selected after switching`);
    assert.equal(runtime.state.selected.has(defaultChoice.option_id), false, `${defaultChoice.option_id} should be removed after alternate selection`);

    runtime.handleChoice(alternateChoice);
    if (expected.groupId === "gs_excl_exhaust_path") {
      assert.equal(runtime.state.selected.has(alternateChoice.option_id), false, `${alternateChoice.option_id} should be removable when workbook defaults can restore NGA`);
      assert.equal(runtime.state.selected.has(defaultChoice.option_id), true, `${defaultChoice.option_id} should restore as the required exhaust default`);
      continue;
    }
    assert.equal(runtime.state.selected.has(alternateChoice.option_id), true, `${alternateChoice.option_id} should not unselect as the last required choice`);
  }
});

test("Grand Sport required exclusive groups report missing choices when cleared", () => {
  const runtime = loadRuntime();
  runtime.activateModel("grandSport");
  runtime.state.bodyStyle = "coupe";
  runtime.state.trimLevel = "1LT";
  runtime.resetDefaults();
  runtime.reconcileSelections();

  for (const optionId of ["opt_efr_001", "opt_edu_001"]) {
    runtime.state.selected.delete(optionId);
    runtime.state.userSelected.delete(optionId);
  }

  assert.equal(runtime.missingRequired().includes("Exterior Accents"), true, "EFR/EDU should require one exterior accent choice");
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
  assert.equal(
    convertibleCenterStripe.description,
    "Only available with Z15 Heritage Hash Marks. When D84 is selected, the roof will not include stripe."
  );
  runtime.handleChoice(convertibleCenterStripe);
  assert.equal(runtime.state.selected.has("opt_dmu_001"), true, "center stripe should not require D84 on convertible");
  assert.equal(runtime.state.selected.has("opt_d84_001"), false, "center stripe should not auto-select D84");
});

test("Grand Sport X heritage hash marks use the Grand Sport one-way Z15 auto-add topology", () => {
  const runtime = loadRuntime();
  runtime.activateModel("grand_sport_x");
  runtime.state.bodyStyle = "coupe";
  runtime.state.trimLevel = "1LT";
  runtime.resetDefaults();
  runtime.reconcileSelections();

  const hashOptionIds = [
    "opt_17a_001",
    "opt_20a_001",
    "opt_55a_001",
    "opt_75a_001",
    "opt_97a_001",
    "opt_dx4_001",
  ];
  const hashSection = runtime.data.sections.find(
    (section) => section.section_id === "sec_gsha_001",
  );
  assert.ok(hashSection, "Grand Sport X should publish its Heritage Hash Marks section");
  assert.equal(hashSection.selection_mode, "single_select_opt");
  assert.equal(hashSection.is_required, "False");

  const firstHash = runtime.activeChoiceRows().find(
    (choice) => choice.option_id === "opt_17a_001",
  );
  assert.ok(firstHash, "17A should be active for Grand Sport X");
  runtime.handleChoice(firstHash);

  assert.equal(
    runtime.currentOrder().auto_added_options.some((item) => item.rpo === "Z15"),
    true,
    "a Grand Sport X heritage hash selection should auto-add Z15",
  );
  assert.deepEqual(
    JSON.parse(JSON.stringify(runtime.currentOrder().auto_added_options))
      .map((item) => item.rpo)
      .filter((rpo) => ["Z15", "SNE", "VPW"].includes(rpo))
      .sort(),
    ["Z15"],
    "Z15 should not auto-add the Jake graphics owned by PDA",
  );
  assert.deepEqual(
    hashOptionIds.filter((optionId) => runtime.state.selected.has(optionId)),
    ["opt_17a_001"],
    "Z15 must not auto-add other choices in the optional single-choice hash section",
  );

  for (const hashOptionId of hashOptionIds) {
    assert.ok(
      runtime.data.rules.some(
        (rule) =>
          rule.active === "True" &&
          rule.source_id === hashOptionId &&
          rule.rule_type === "includes" &&
          rule.target_id === "opt_z15_001" &&
          rule.auto_add === "True",
      ),
      `${hashOptionId} should auto-add Z15`,
    );
  }
  assert.deepEqual(
    JSON.parse(JSON.stringify(runtime.data.rules))
      .filter(
        (rule) =>
          rule.active === "True" &&
          rule.source_id === "opt_z15_001" &&
          ["includes", "requires"].includes(rule.rule_type),
      )
      .map((rule) => `${rule.rule_type}:${rule.target_id}`)
      .sort(),
    [],
    "Z15 must not include or require choices in the reverse direction",
  );
});

test("Grand Sport X keeps unavailable R88 out of runtime and applies SFZ canonical conflicts", () => {
  const runtime = loadRuntime();
  runtime.activateModel("grand_sport_x");
  runtime.state.bodyStyle = "coupe";
  runtime.state.trimLevel = "1LT";
  runtime.resetDefaults();
  runtime.reconcileSelections();

  assert.equal(
    runtime.data.choices.some((choice) => choice.option_id === "opt_r88_001"),
    false,
    "inactive R88 should not publish any Grand Sport X runtime choices",
  );

  const expectedTargets = [
    "opt_eyk_001",
    "opt_dpb_001",
    "opt_dpc_001",
    "opt_dpg_001",
    "opt_dpl_001",
    "opt_dpt_001",
    "opt_dsy_001",
    "opt_dsz_001",
    "opt_dt0_001",
    "opt_dtc_001",
    "opt_dth_001",
    "opt_dub_001",
    "opt_due_001",
    "opt_duk_001",
    "opt_dmu_001",
    "opt_dmv_001",
    "opt_dmw_001",
    "opt_dmx_001",
    "opt_dmy_001",
  ];
  const sfzGroup = runtime.data.ruleGroups.find(
    (group) => group.group_id === "gsx_group_sfz_excludes_badge_and_stripe_choices",
  );
  assert.ok(sfzGroup, "SFZ should publish one grouped canonical exclusion owner");
  assert.equal(sfzGroup.group_type, "excludes_any");
  assert.equal(sfzGroup.source_id, "opt_sfz_001");
  assert.deepEqual(
    JSON.parse(JSON.stringify(sfzGroup.target_ids)),
    expectedTargets,
  );
  assert.equal(
    runtime.data.rules.some(
      (rule) => rule.source_id === "opt_sfz_001" && rule.rule_type === "excludes",
    ),
    false,
    "SFZ exclusions should have one grouped owner instead of partial direct rows",
  );

  const sfz = runtime.activeChoiceRows().find((choice) => choice.option_id === "opt_sfz_001");
  assert.ok(sfz, "SFZ should remain available for Grand Sport X");
  runtime.handleChoice(sfz);
  assert.equal(runtime.state.selected.has("opt_sfz_001"), true);

  for (const optionId of ["opt_eyk_001", "opt_dtc_001", "opt_dmu_001"]) {
    const choice = runtime.activeChoiceRows().find((candidate) => candidate.option_id === optionId);
    assert.ok(choice, `${optionId} should exist for the runtime conflict proof`);
    assert.notEqual(runtime.disableReasonForChoice(choice), "", `${optionId} should be unavailable with SFZ`);
    runtime.handleChoice(choice);
    assert.equal(runtime.state.selected.has(optionId), false, `${optionId} should not be selectable with SFZ`);
  }
});

test("Grand Sport X requires ZZ3 before BC7 on Convertible", () => {
  const runtime = loadRuntime();
  runtime.activateModel("grand_sport_x");
  runtime.state.bodyStyle = "convertible";
  runtime.state.trimLevel = "1LT";
  runtime.resetDefaults();
  runtime.reconcileSelections();

  const rule = runtime.data.rules.find(
    (candidate) =>
      candidate.active === "True" &&
      candidate.source_id === "opt_bc7_001" &&
      candidate.rule_type === "requires" &&
      candidate.target_id === "opt_zz3_001",
  );
  assert.ok(rule, "BC7 should publish its canonical ZZ3 requirement");
  assert.equal(rule.auto_add, "False");

  const bc7 = runtime.activeChoiceRows().find(
    (choice) => choice.option_id === "opt_bc7_001",
  );
  assert.ok(bc7, "BC7 should be available on Grand Sport X Convertible");
  assert.equal(
    runtime.disableReasonForChoice(bc7),
    "Requires ZZ3 Convertible Engine Appearance Package.",
  );
  runtime.handleChoice(bc7);
  assert.equal(runtime.state.selected.has("opt_bc7_001"), false);

  const zz3 = runtime.activeChoiceRows().find(
    (choice) => choice.option_id === "opt_zz3_001",
  );
  assert.ok(zz3, "ZZ3 should be available on Grand Sport X Convertible");
  runtime.handleChoice(zz3);
  assert.equal(runtime.state.selected.has("opt_zz3_001"), true);
  assert.equal(
    runtime.currentOrder().auto_added_options.some((item) => item.rpo === "BC7"),
    true,
    "ZZ3 should continue to auto-add BC7",
  );
});

test("Grand Sport X does not publish unsupported DT0 or EFR auto-adds", () => {
  const cases = [
    {
      ruleId: "grand_sport_x_rule_dt0_includes_sne_f0099d7e7cb4",
      sourceId: "opt_dt0_001",
      targetId: "opt_sne_001",
      targetRpo: "SNE",
    },
    {
      ruleId: "grand_sport_x_rule_efr_includes_cfv_ea894acb4a76",
      sourceId: "opt_efr_001",
      targetId: "opt_cfv_001",
      targetRpo: "CFV",
    },
  ];

  for (const { ruleId, sourceId, targetId, targetRpo } of cases) {
    const runtime = loadRuntime();
    runtime.activateModel("grand_sport_x");
    runtime.state.bodyStyle = "coupe";
    runtime.state.trimLevel = "1LT";
    runtime.resetDefaults();
    runtime.reconcileSelections();

    assert.equal(
      runtime.data.rules.some(
        (rule) =>
          rule.rule_id === ruleId &&
          rule.source_id === sourceId &&
          rule.rule_type === "includes" &&
          rule.target_id === targetId &&
          rule.auto_add === "True",
      ),
      false,
      `${sourceId} should not publish the unsupported ${targetRpo} auto-add`,
    );

    const source = runtime.activeChoiceRows().find((choice) => choice.option_id === sourceId);
    assert.ok(source, `${sourceId} should exist for the Grand Sport X runtime proof`);
    runtime.handleChoice(source);
    assert.equal(runtime.state.selected.has(sourceId), true, `${sourceId} should remain selectable`);
    assert.equal(
      runtime.currentOrder().auto_added_options.some((item) => item.rpo === targetRpo),
      false,
      `${sourceId} should not auto-add ${targetRpo}`,
    );
  }
});

test("Grand Sport and Grand Sport X publish Jake hood graphics outside the stripe selector with GSX stripe parity", () => {
  const registry = loadDataWindow().CORVETTE_FORM_DATA;
  const namedStripeIds = [
    "opt_dpb_001",
    "opt_dpc_001",
    "opt_dpg_001",
    "opt_dpl_001",
    "opt_dpt_001",
    "opt_dsy_001",
    "opt_dsz_001",
    "opt_dt0_001",
    "opt_dtc_001",
    "opt_dth_001",
    "opt_dub_001",
    "opt_due_001",
    "opt_duk_001",
    "opt_dzu_001",
    "opt_dzv_001",
    "opt_dzx_001",
  ];

  for (const modelKey of ["grandSport", "grand_sport_x"]) {
    const data = registry.models[modelKey].data;
    const byRpo = new Map(data.choices.map((choice) => [choice.rpo, choice]));
    assert.equal(byRpo.get("PDA")?.section_id, "sec_jake_001", `${modelKey} PDA should remain in Jake Graphics`);
    assert.equal(byRpo.get("SNE")?.section_id, "sec_jake_001", `${modelKey} SNE should render in Jake Graphics`);
    assert.equal(byRpo.get("SHT")?.section_id, "sec_jake_001", `${modelKey} SHT should render in Jake Graphics`);
    assert.equal(byRpo.get("VPW")?.section_id, "sec_hash_001", `${modelKey} VPW should remain in Hash Marks`);
    assert.equal(byRpo.get("VPO")?.section_id, "sec_hash_001", `${modelKey} VPO should remain in Hash Marks`);
  }

  const runtime = loadRuntime();
  runtime.activateModel("grand_sport_x");
  runtime.state.bodyStyle = "coupe";
  runtime.state.trimLevel = "1LT";
  runtime.resetDefaults();
  runtime.reconcileSelections();
  runtime.state.selected.clear();
  runtime.state.userSelected.clear();

  const pda = runtime.activeChoiceRows().find((choice) => choice.rpo === "PDA");
  assert.ok(pda, "Grand Sport X should expose PDA");
  runtime.handleChoice(pda);
  const autoAddedRpos = [...runtime.computeAutoAdded().keys()]
    .map((optionId) => runtime.data.choices.find((choice) => choice.option_id === optionId)?.rpo)
    .filter(Boolean)
    .sort();
  assert.deepEqual(autoAddedRpos.filter((rpo) => ["SNE", "VPW"].includes(rpo)), ["SNE", "VPW"]);

  const groupTargets = (groupId) => {
    const group = runtime.data.ruleGroups.find((candidate) => candidate.group_id === groupId);
    assert.ok(group, `${groupId} should publish from the GSX workbook rule-group owner`);
    return JSON.parse(JSON.stringify(group.target_ids));
  };
  assert.deepEqual(groupTargets("gsx_group_pda_excludes_full_length_stripes"), namedStripeIds);
  assert.deepEqual(
    groupTargets("gsx_group_sne_excludes_full_length_stripes_and_jake_conflicts"),
    [...namedStripeIds, "opt_sht_001", "opt_vpo_001"],
  );
  assert.deepEqual(
    groupTargets("gsx_group_sht_excludes_full_length_stripes_and_jake_conflicts"),
    [...namedStripeIds, "opt_pda_001", "opt_sne_001", "opt_vpw_001"],
  );
  assert.deepEqual(
    groupTargets("gsx_group_dtc_excludes_jake_hood_graphics"),
    ["opt_sht_001", "opt_sne_001"],
  );
  assert.equal(
    runtime.data.choices.some((choice) => choice.rpo === "DUW"),
    false,
    "Grand Sport X must not invent the unavailable Grand Sport-only DUW stripe",
  );
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
  const ah2Interior = runtime.data.interiors.find((interior) => interior.interior_id === "2LT_AH2_HTM");
  assert.ok(ah2Interior, "2LT AH2 Jet Black interior should exist");
  assert.equal(runtime.adjustedInteriorDisplayPrice(ah2Interior), 0, "2LT AH2 interior tile should subtract the scoped AH2 seat price");
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

  for (const optionId of ["opt_efr_001", "opt_t0e_001", "opt_jx6_001", "opt_719_001", "opt_bc7_001", "opt_nga_001"]) {
    assert.equal(runtime.state.selected.has(optionId), true, `${optionId} should be selected from display_behavior=default_selected`);
  }

  const j56 = runtime.activeChoiceRows().find((choice) => choice.option_id === "opt_j56_001");
  const j57 = runtime.activeChoiceRows().find((choice) => choice.option_id === "opt_j57_001");
  assert.ok(j56, "J56 should render as a visible brake card");
  assert.ok(j57, "J57 should render as a visible brake card");
  assert.equal(j56.active, "True");
  assert.equal(j56.status, "available");
  assert.equal(j56.selectable, "False");
  assert.equal(j56.display_behavior, "display_only");
  assert.equal(runtime.disableReasonForChoice(j56), "Included with FEB Z52 Sport Performance Package.");
  assert.equal(runtime.disableReasonForChoice(j57), "Requires FEB Z52 Sport Performance Package or FEY Z52 Track Performance Package.");

  const febRuntime = loadRuntime();
  febRuntime.activateModel("grandSport");
  febRuntime.state.bodyStyle = "coupe";
  febRuntime.state.trimLevel = "1LT";
  febRuntime.resetDefaults();
  febRuntime.reconcileSelections();
  const feb = febRuntime.activeChoiceRows().find((choice) => choice.option_id === "opt_feb_001");
  febRuntime.handleChoice(feb);
  assert.equal(febRuntime.state.selected.has("opt_feb_001"), true, "FEB should be selectable");
  assert.equal(febRuntime.state.selected.has("opt_jx6_001"), false, "FEB should replace the default JX6 brake row");
  assert.equal(febRuntime.computeAutoAdded().get("opt_j56_001"), "Included with FEB Z52 Sport Performance Package.");
  assert.equal(febRuntime.disableReasonForChoice(febRuntime.activeChoiceRows().find((choice) => choice.option_id === "opt_jx6_001")), "FEB includes J56 performance disc brakes.");
  assert.equal(febRuntime.disableReasonForChoice(febRuntime.activeChoiceRows().find((choice) => choice.option_id === "opt_j57_001")), "");

  const fey = runtime.activeChoiceRows().find((choice) => choice.option_id === "opt_fey_001");
  runtime.handleChoice(fey);
  assert.equal(runtime.state.selected.has("opt_fey_001"), true, "FEY should be selectable");
  assert.equal(runtime.state.selected.has("opt_t0e_001"), false, "FEY should replace the default T0E aero row");
  assert.equal(runtime.state.selected.has("opt_jx6_001"), false, "FEY auto-added J57 should replace the default JX6 brake row");
  assert.equal(runtime.state.selected.has("opt_j56_001"), false, "FEY auto-added J57 should not leave J56 selected");
  assert.equal(runtime.disableReasonForChoice(runtime.activeChoiceRows().find((choice) => choice.option_id === "opt_jx6_001")), "FEY includes J57 carbon ceramic brakes.");
  assert.equal(runtime.disableReasonForChoice(runtime.activeChoiceRows().find((choice) => choice.option_id === "opt_j56_001")), "FEY includes J57 carbon ceramic brakes.");

  const order = runtime.currentOrder();
  assert.equal(order.auto_added_options.some((item) => item.rpo === "J57"), true, "FEY should auto-add J57");
  assert.equal(order.auto_added_options.some((item) => item.rpo === "T0F" && item.price === 0), true, "FEY should auto-add T0F at $0");
  assert.equal(order.auto_added_options.some((item) => item.rpo === "CFZ" && item.price === 0), true, "FEY should auto-add CFZ at $0 through T0F");
  assert.equal(runtime.optionPrice("opt_t0f_001"), 0, "FEY should keep the T0F price override");
  assert.equal(runtime.computeAutoAdded().has("opt_t0f_001"), true, "FEY should keep T0F in the auto-added set");
  runtime.handleChoice(runtime.activeChoiceRows().find((choice) => choice.option_id === "opt_t0f_001"));
  assert.equal(runtime.computeAutoAdded().has("opt_t0f_001"), true, "T0F should remain auto-added while FEY includes it");
  assert.equal(order.selected_options.some((item) => item.rpo === "J6D"), true, "FEY auto-added J57 should soft-default grey calipers into selected RPOs");
  assert.equal(order.auto_added_options.some((item) => item.rpo === "J6D"), false, "grey calipers should not be hard auto-added");
  assert.equal(order.selected_options.some((item) => item.rpo === "J6A"), false, "J57 should replace default black calipers");
  assert.equal(runtime.optionPrice("opt_j57_001"), 0, "FEY should keep the J57 price override");

  const redCaliperRuntime = loadRuntime();
  redCaliperRuntime.activateModel("grandSport");
  redCaliperRuntime.state.bodyStyle = "coupe";
  redCaliperRuntime.state.trimLevel = "1LT";
  redCaliperRuntime.resetDefaults();
  redCaliperRuntime.reconcileSelections();
  redCaliperRuntime.handleChoice(redCaliperRuntime.activeChoiceRows().find((choice) => choice.option_id === "opt_j6f_001"));
  redCaliperRuntime.handleChoice(redCaliperRuntime.activeChoiceRows().find((choice) => choice.option_id === "opt_fey_001"));
  const redCaliperOrder = redCaliperRuntime.currentOrder();
  assert.equal(redCaliperOrder.selected_options.some((item) => item.rpo === "J6F"), true, "User-selected non-black calipers should be preserved");
  assert.equal(redCaliperOrder.auto_added_options.some((item) => item.rpo === "J6D"), false, "Grey calipers should not override a user-selected caliper");
});

test("Grand Sport engine covers are radio peers without an open Engine Appearance requirement", () => {
  const runtime = loadRuntime();
  runtime.activateModel("grandSport");
  runtime.state.bodyStyle = "convertible";
  runtime.state.trimLevel = "1LT";
  runtime.resetDefaults();
  runtime.reconcileSelections();

  assert.equal(runtime.missingRequired().includes("Engine Appearance"), false, "Grand Sport convertible should not have an open Engine Appearance requirement");

  const zz3 = runtime.activeChoiceRows().find((choice) => choice.option_id === "opt_zz3_001");
  assert.ok(zz3, "ZZ3 should remain selectable for Grand Sport convertible");
  runtime.handleChoice(zz3);
  assert.equal(runtime.computeAutoAdded().has("opt_bc7_001"), true, "ZZ3 should still provide BC7 through workbook auto-add rules");

  runtime.state.bodyStyle = "coupe";
  runtime.resetDefaults();
  runtime.reconcileSelections();
  const b6p = runtime.activeChoiceRows().find((choice) => choice.option_id === "opt_b6p_001");
  const bc4 = runtime.activeChoiceRows().find((choice) => choice.option_id === "opt_bc4_002");
  const bcp = runtime.activeChoiceRows().find((choice) => choice.option_id === "opt_bcp_002");
  assert.ok(b6p && bc4 && bcp, "Grand Sport coupe engine appearance and cover choices should be active");
  runtime.handleChoice(b6p);
  assert.equal(runtime.state.selected.has("opt_bc7_001"), true, "B6P path should seed BC7 as the default cover");
  runtime.handleChoice(bc4);
  assert.equal(runtime.state.selected.has("opt_bc4_002"), true, "paid LS6 cover should select");
  assert.equal(runtime.state.selected.has("opt_bc7_001"), false, "paid LS6 cover should replace BC7");
  runtime.handleChoice(bcp);
  assert.equal(runtime.state.selected.has("opt_bcp_002"), true, "another paid LS6 cover should select");
  assert.equal(runtime.state.selected.has("opt_bc4_002"), false, "paid LS6 covers should remain radio peers");
  runtime.handleChoice(bcp);
  assert.equal(runtime.state.selected.has("opt_bcp_002"), false, "clicking selected paid cover should remove it");
  assert.equal(runtime.state.selected.has("opt_bc7_001"), true, "removing paid cover should restore workbook-owned BC7 coupe default");
});

test("Grand Sport WUB enables NWI without replacing NGA; NWI replaces and restores NGA", () => {
  const runtime = loadRuntime();
  runtime.activateModel("grandSport");
  runtime.state.bodyStyle = "coupe";
  runtime.state.trimLevel = "1LT";
  runtime.resetDefaults();
  runtime.reconcileSelections();

  const wub = runtime.activeChoiceRows().find((choice) => choice.option_id === "opt_wub_001");
  const nwi = runtime.activeChoiceRows().find((choice) => choice.option_id === "opt_nwi_001");
  assert.ok(wub && nwi, "WUB and NWI should be active Grand Sport exhaust choices");
  assert.equal(runtime.state.selected.has("opt_nga_001"), true, "NGA should seed as the default exhaust tip");
  assert.match(runtime.disableReasonForChoice(nwi), /WUB|Quad Center Exit/i, "NWI should require WUB before WUB is selected");

  runtime.handleChoice(wub);
  assert.equal(runtime.state.selected.has("opt_wub_001"), true, "WUB should be selected");
  assert.equal(runtime.state.selected.has("opt_nga_001"), true, "WUB alone should not remove NGA");
  assert.equal(runtime.disableReasonForChoice(nwi), "", "WUB should make NWI selectable");

  runtime.handleChoice(nwi);
  assert.equal(runtime.state.selected.has("opt_nwi_001"), true, "NWI should be selected");
  assert.equal(runtime.state.selected.has("opt_nga_001"), false, "NWI should replace NGA");

  runtime.handleChoice(nwi);
  assert.equal(runtime.state.selected.has("opt_nwi_001"), false, "NWI should be removable");
  assert.equal(runtime.state.selected.has("opt_nga_001"), true, "removing NWI should restore NGA");

  runtime.handleChoice(nwi);
  runtime.handleChoice(wub);
  runtime.reconcileSelections();
  assert.equal(runtime.state.selected.has("opt_wub_001"), false, "WUB should be removable");
  assert.equal(runtime.state.selected.has("opt_nwi_001"), false, "removing WUB should remove invalid NWI");
  assert.equal(runtime.state.selected.has("opt_nga_001"), true, "removing WUB from the NWI path should restore NGA");
});

test("Stingray WUB enables NWI without replacing NGA; NWI replaces and restores NGA", () => {
  const runtime = loadRuntime();
  runtime.activateModel("stingray");
  runtime.state.bodyStyle = "coupe";
  runtime.state.trimLevel = "1LT";
  runtime.resetDefaults();
  runtime.reconcileSelections();

  const wub = runtime.activeChoiceRows().find((choice) => choice.option_id === "opt_wub_001");
  const nwi = runtime.activeChoiceRows().find((choice) => choice.option_id === "opt_nwi_001");
  assert.ok(wub && nwi, "WUB and NWI should be active Stingray exhaust choices");
  assert.equal(runtime.state.selected.has("opt_nga_001"), true, "NGA should seed as the default exhaust tip");
  assert.match(runtime.disableReasonForChoice(nwi), /WUB|Quad Center Exit/i, "NWI should require WUB before WUB is selected");

  runtime.handleChoice(wub);
  assert.equal(runtime.state.selected.has("opt_wub_001"), true, "WUB should be selected");
  assert.equal(runtime.state.selected.has("opt_nga_001"), true, "WUB alone should not remove NGA");
  assert.equal(runtime.disableReasonForChoice(nwi), "", "WUB should make NWI selectable");

  runtime.handleChoice(nwi);
  assert.equal(runtime.state.selected.has("opt_nwi_001"), true, "NWI should be selected");
  assert.equal(runtime.state.selected.has("opt_nga_001"), false, "NWI should replace NGA");

  runtime.handleChoice(nwi);
  assert.equal(runtime.state.selected.has("opt_nwi_001"), false, "NWI should be removable");
  assert.equal(runtime.state.selected.has("opt_nga_001"), true, "removing NWI should restore NGA");

  runtime.handleChoice(nwi);
  runtime.handleChoice(wub);
  runtime.reconcileSelections();
  assert.equal(runtime.state.selected.has("opt_wub_001"), false, "WUB should be removable");
  assert.equal(runtime.state.selected.has("opt_nwi_001"), false, "removing WUB should remove invalid NWI");
  assert.equal(runtime.state.selected.has("opt_nga_001"), true, "removing WUB from the NWI path should restore NGA");
});

test("Grand Sport J57 soft-defaults J6D into selected RPOs instead of auto-added RPOs", () => {
  const runtime = loadRuntime();
  runtime.activateModel("grandSport");
  runtime.state.bodyStyle = "coupe";
  runtime.state.trimLevel = "1LT";
  runtime.resetDefaults();
  runtime.reconcileSelections();

  const j57 = runtime.activeChoiceRows().find((choice) => choice.option_id === "opt_j57_001");
  const feb = runtime.activeChoiceRows().find((choice) => choice.option_id === "opt_feb_001");
  assert.ok(j57, "J57 should render as a visible brake card");
  assert.equal(runtime.disableReasonForChoice(j57), "Requires FEB Z52 Sport Performance Package or FEY Z52 Track Performance Package.");
  runtime.handleChoice(j57);
  let order = runtime.currentOrder();
  assert.equal(order.selected_options.some((item) => item.rpo === "J57"), false, "J57 should not be selectable before FEB/FEY");

  runtime.handleChoice(feb);
  assert.equal(runtime.disableReasonForChoice(j57), "", "FEB should make J57 selectable");
  runtime.handleChoice(j57);
  order = runtime.currentOrder();
  assert.equal(order.selected_options.some((item) => item.rpo === "J57"), true, "J57 should be selected after FEB");
  assert.equal(order.selected_options.some((item) => item.rpo === "J6D"), true, "J6D should land in selected options as a soft default");
  assert.equal(order.auto_added_options.some((item) => item.rpo === "J6D"), false, "J6D should not be a hard auto-add");

  const redCaliper = runtime.activeChoiceRows().find((choice) => choice.option_id === "opt_j6f_001");
  assert.ok(redCaliper, "red calipers should be selectable");
  runtime.handleChoice(redCaliper);
  order = runtime.currentOrder();
  assert.equal(order.selected_options.some((item) => item.rpo === "J6F"), true, "user-selected caliper should replace J6D");
  assert.equal(order.selected_options.some((item) => item.rpo === "J6D"), false, "J6D soft default should not override user caliper choice");
});

test("Grand Sport 1LT interior color groups stay expanded when each group has one option", () => {
  const runtime = loadRuntime();
  runtime.activateModel("grandSport");
  runtime.state.bodyStyle = "coupe";
  runtime.state.trimLevel = "1LT";
  runtime.resetDefaults();
  runtime.reconcileSelections();
  const gt1 = runtime.activeChoiceRows().find((choice) => choice.rpo === "AQ9" && choice.step_key === "seat");
  assert.ok(gt1, "Grand Sport 1LT GT1 seat should exist");
  runtime.handleChoice(gt1);
  const interiors = runtime.data.interiors.filter((interior) => interior.trim_level === "1LT" && interior.seat_code === "AQ9");
  assert.equal(interiors.length > 1, true, "Grand Sport 1LT should expose multiple color groups");
  const html = runtime.renderInteriorGroups(interiors);
  assert.doesNotMatch(html, /<details class="interior-group"/, "single-option 1LT color groups should not be collapsed");
  assert.match(html, /<section class="interior-group"/);
  assert.match(html, /<button class="choice-card"/);
});

test("Grand Sport interior color groups render collapsed disclosure containers", () => {
  const runtime = loadRuntime();
  runtime.activateModel("grandSport");
  runtime.state.bodyStyle = "coupe";
  runtime.state.trimLevel = "2LT";
  runtime.resetDefaults();
  runtime.reconcileSelections();
  const gt2 = runtime.activeChoiceRows().find((choice) => choice.rpo === "AH2" && choice.step_key === "seat");
  assert.ok(gt2, "Grand Sport 2LT GT2 seat should exist");
  runtime.handleChoice(gt2);
  const interiors = runtime.data.interiors.filter((interior) => interior.trim_level === "2LT" && interior.seat_code === "AH2");
  assert.equal(interiors.length > 3, true, "Grand Sport 2LT GT2 should expose multiple interior colors");
  const html = runtime.renderInteriorGroups(interiors);
  assert.match(html, /<details class="interior-group"/);
  assert.match(html, /<summary class="interior-group-header">/);
  assert.doesNotMatch(html, /<details class="interior-group"[^>]*\sopen(?:\s|>)/, "Grand Sport interior groups should be collapsed by default");
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
  assert.equal(runtime.state.selected.has("opt_jx6_001"), true, "JX6 should be the default Grand Sport brake");
  assert.equal(runtime.disableReasonForChoice(j57), "Requires FEB Z52 Sport Performance Package or FEY Z52 Track Performance Package.");
  runtime.handleChoice(j57);
  assert.equal(runtime.state.selected.has("opt_j57_001"), false, "J57 should not be selectable before FEB/FEY");
  assert.equal(runtime.state.selected.has("opt_jx6_001"), true, "JX6 should remain selected when blocked J57 is clicked");
  assert.equal(runtime.state.selected.has("opt_j56_001"), false, "blocked J57 click should not select J56");

  runtime.resetDefaults();
  runtime.reconcileSelections();
  const feb = runtime.activeChoiceRows().find((choice) => choice.option_id === "opt_feb_001");
  runtime.handleChoice(feb);
  let order = runtime.currentOrder();
  assert.equal(order.auto_added_options.some((item) => item.rpo === "J56" && item.price === 0), true, "FEB should auto-add J56 at $0");
  assert.equal(runtime.state.selected.has("opt_jx6_001"), false, "FEB auto-added J56 should replace default JX6");
  runtime.handleChoice(j57);
  order = runtime.currentOrder();
  assert.equal(runtime.state.selected.has("opt_j57_001"), true, "J57 should remain selectable after FEB");
  assert.equal(order.auto_added_options.some((item) => item.rpo === "J56"), false, "J57 should replace FEB auto-added J56");
  runtime.handleChoice(j57);
  order = runtime.currentOrder();
  assert.equal(runtime.state.selected.has("opt_j57_001"), false, "J57 should be removable while FEB can refill the brake section");
  assert.equal(order.auto_added_options.some((item) => item.rpo === "J56" && item.price === 0), true, "FEB should restore J56 after J57 is removed");
  assert.equal(runtime.state.selected.has("opt_jx6_001"), false, "JX6 should remain unavailable with FEB selected");
  runtime.handleChoice(j57);
  const t0f = runtime.activeChoiceRows().find((choice) => choice.option_id === "opt_t0f_001");
  const cfl = runtime.activeChoiceRows().find((choice) => choice.option_id === "opt_cfl_001");
  const cfv = runtime.activeChoiceRows().find((choice) => choice.option_id === "opt_cfv_001");
  runtime.handleChoice(t0f);
  assert.equal(runtime.currentOrder().auto_added_options.some((item) => item.rpo === "CFZ" && item.price === 0), true, "T0F should auto-add CFZ at $0");
  runtime.handleChoice(cfl);
  assert.equal(runtime.state.selected.has("opt_cfl_001"), false, "T0F's included CFZ should keep other ground effects unavailable");
  assert.match(runtime.disableReasonForChoice(cfl), /included with T0F/i);
  runtime.handleChoice(cfv);
  assert.equal(runtime.state.selected.has("opt_cfv_001"), false, "T0F's included CFZ should also keep CFV unavailable");
  assert.match(runtime.disableReasonForChoice(cfv), /included with T0F/i);
  assert.equal(runtime.currentOrder().auto_added_options.some((item) => item.rpo === "CFZ"), true, "T0F should keep CFZ auto-added while selected");

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

  runtime.requestModelChange("grandSport");
  assert.equal(runtime.elements.get("#confirmActionModal").hidden, false, "dirty model switch should prompt");
  assert.equal(runtime.elements.get("#confirmActionMessage").textContent, "Changing models will reset all selected options. Are you sure?");
  assert.equal(runtime.elements.get("#confirmActionConfirmButton").textContent, "Yes, Change Model");
  assert.equal(runtime.activeModelKey, "stingray");

  runtime.elements.get("#confirmActionCancelButton").click();
  assert.equal(runtime.elements.get("#confirmActionModal").hidden, true);
  assert.equal(runtime.activeModelKey, "stingray");
  assert.equal(runtime.state.selected.has("opt_gba_001"), true, "canceling model switch should preserve current selections");

  runtime.requestModelChange("grandSport");
  runtime.elements.get("#confirmActionConfirmButton").click();

  assert.equal(runtime.activeModelKey, "grandSport");
  assert.equal(runtime.activeModelLabel, "Grand Sport");
  assert.deepEqual(
    JSON.parse(JSON.stringify(runtime.variants.map((variant) => variant.variant_id))),
    ["1lt_e07", "2lt_e07", "3lt_e07", "1lt_e67", "2lt_e67", "3lt_e67"]
  );
  assert.equal(runtime.state.bodyStyle, "coupe");
  assert.equal(runtime.state.trimLevel, "1LT");
  assert.equal(runtime.state.activeStep, "model");
  assert.equal(runtime.state.selected.has("opt_gba_001"), false, "Stingray selected option should not survive model switch");
  assert.equal(runtime.state.selectedInterior, "");
  assert.equal(runtime.state.customer.name, "Ada Buyer");
  assert.equal(runtime.state.customer.email, "ada@example.com");
  assert.equal(runtime.activeChoiceRows().every((choice) => choice.variant_id.endsWith("_e07")), true);

  const grandSportOrder = runtime.compactOrder();
  assert.equal(grandSportOrder.title, "2027 Corvette Grand Sport");
  assert.doesNotMatch(runtime.plainTextOrderSummary(), /^<p>2027 Corvette Grand Sport<\/p>/);

  runtime.requestModelChange("stingray");
  assert.equal(runtime.elements.get("#confirmActionModal").hidden, true, "clean model switch should not prompt");
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
  assert.doesNotMatch(submission.payload.plain_text_summary, /^<p>2027 Corvette Grand Sport<\/p>/);
  assert.match(submission.payload.plain_text_summary, /<p><strong><u>Variant<\/u><\/strong><\/p><ul><li>Corvette Grand Sport Coupe 1LT<\/li><\/ul>/);
  assert.match(submission.payload.plain_text_summary, /<strong>Email:<\/strong> ada@example\.com/);
  assert.match(submission.payload.plain_text_summary, /<strong>Total MSRP: \$\d/);
  assert.doesNotMatch(submission.payload.plain_text_summary, /Base MSRP|STANDARD & INCLUDED/);
  assert.doesNotMatch(submission.payload.plain_text_summary, /<h3/i);
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
  assert.ok(runtime.currentOrder().metadata.missing_required.includes("Interior Color"));

  runtime.state.selectedInterior = "3LT_AH2_EL9";
  runtime.reconcileSelections();
  const order = runtime.currentOrder();
  assert.equal(order.metadata.selected_interior_id, "3LT_AH2_EL9");
  assert.equal(order.selected_interior.rpo, "EL9");
  assert.equal(order.selected_interior.label, "Santorini Blue Dipped with Torch Red accents");
  assert.equal(order.metadata.missing_required.includes("Interior Color"), false);
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

  for (const [interiorId, rpo, optionId] of [
    ["3LT_AH2_EJH", "3N9", "opt_3n9_001"],
    ["3LT_AH2_EPX_N26", "3N9", "opt_3n9_001"],
    ["3LT_AH2_HZN", "3N9", "opt_3n9_001"],
    ["3LT_AH2_HNK", "3F9", "opt_3f9_001"],
    ["3LT_AH2_H8T", "3A9", "opt_3a9_001"],
    ["3LT_AH2_HUW", "379", "opt_379_001"],
  ]) {
    runtime.state.selectedInterior = interiorId;
    runtime.reconcileSelections();
    const order = runtime.currentOrder();
    assert.equal(runtime.state.selected.has("opt_719_001"), false, `${interiorId} should replace default 719`);
    assert.equal(order.auto_added_options.some((item) => item.rpo === rpo && item.price === 0), true, `${interiorId} should auto-add ${rpo} at no charge`);

    const otherSeatbelt = runtime.activeChoiceRows().find(
      (item) => item.section_id === "sec_seat_001" && item.option_id !== optionId && item.selectable === "True"
    );
    assert.ok(otherSeatbelt, "expected another selectable seatbelt for lock test");
    runtime.handleChoice(otherSeatbelt);
    runtime.reconcileSelections();
    assert.equal(runtime.state.selected.has(otherSeatbelt.option_id), false, `${interiorId} should block other seatbelts`);

    runtime.state.selected.add("opt_d30_001");
    runtime.handleChoice(otherSeatbelt);
    runtime.reconcileSelections();
    assert.equal(runtime.state.selected.has(otherSeatbelt.option_id), false, `${interiorId} should block other seatbelts even with D30`);
    runtime.state.selected.delete("opt_d30_001");
  }

  runtime.state.selectedInterior = "3LT_AH2_HTE";
  runtime.reconcileSelections();
  assert.equal(runtime.state.selected.has("opt_719_001"), true, "3LT interior without included color seatbelt should keep 719 default");
  assert.equal(runtime.currentOrder().auto_added_options.some((item) => ["3N9", "3F9", "3A9", "379"].includes(item.rpo)), false);
});

test("Grand Sport and Z06 stripe runtime allows rear hash graphics with dual stripes and PDA auto-adds package graphics", () => {
  for (const [modelKey, trimLevel] of [["grandSport", "1LT"], ["z06", "1LZ"]]) {
    const runtime = loadRuntime();
    runtime.activateModel(modelKey);
    runtime.state.bodyStyle = "coupe";
    runtime.state.trimLevel = trimLevel;
    runtime.resetDefaults();
    runtime.reconcileSelections();

    const choiceByRpo = (rpo) => runtime.activeChoiceRows().find((choice) => choice.rpo === rpo);
    const dpb = choiceByRpo("DPB");
    const vpo = choiceByRpo("VPO");
    const vpw = choiceByRpo("VPW");
    const sht = choiceByRpo("SHT");
    const pda = choiceByRpo("PDA");
    const sne = choiceByRpo("SNE");
    assert.ok(dpb && vpo && vpw && sht && pda && sne, `${modelKey} should expose target stripe choices`);
    assert.equal(vpo.section_id, "sec_hash_001", `${modelKey} VPO should render as rear hash`);
    assert.equal(vpw.section_id, "sec_hash_001", `${modelKey} VPW should render as rear hash`);

    runtime.handleChoice(dpb);
    runtime.handleChoice(vpo);
    assert.equal(runtime.state.selected.has(dpb.option_id), true, `${modelKey} dual racing stripe should remain with VPO`);
    assert.equal(runtime.state.selected.has(vpo.option_id), true, `${modelKey} VPO should remain with dual racing stripe`);

    runtime.resetDefaults();
    runtime.reconcileSelections();
    runtime.handleChoice(dpb);
    runtime.handleChoice(vpw);
    assert.equal(runtime.state.selected.has(dpb.option_id), true, `${modelKey} dual racing stripe should remain with VPW`);
    assert.equal(runtime.state.selected.has(vpw.option_id), true, `${modelKey} VPW should remain with dual racing stripe`);

    runtime.resetDefaults();
    runtime.reconcileSelections();
    runtime.handleChoice(sht);
    runtime.handleChoice(vpo);
    assert.equal(runtime.state.selected.has(sht.option_id), true, `${modelKey} SHT should remain with VPO`);
    assert.equal(runtime.state.selected.has(vpo.option_id), true, `${modelKey} VPO should remain with SHT`);

    runtime.resetDefaults();
    runtime.reconcileSelections();
    runtime.handleChoice(pda);
    const autoAdded = runtime.computeAutoAdded();
    assert.equal(autoAdded.has(sne.option_id), true, `${modelKey} PDA should auto-add SNE`);
    assert.equal(autoAdded.has(vpw.option_id), true, `${modelKey} PDA should auto-add VPW`);
  }
});
