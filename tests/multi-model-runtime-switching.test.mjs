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
  const turnstileCalls = [];
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
    turnstileCalls,
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
    exportJson,
  exportCsv,
  renderChoiceCard,
  renderContextCard,
  renderInteriorGroups: typeof renderInteriorGroups === "function" ? renderInteriorGroups : undefined,
  formatTooltipContent: typeof formatTooltipContent === "function" ? formatTooltipContent : undefined,
  renderStepChoiceGroups: typeof renderStepChoiceGroups === "function" ? renderStepChoiceGroups : undefined,
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
    optionIds: ["opt_cfl_001", "opt_cfz_001"],
  },
  {
    groupId: "gs_excl_z52_packages",
    optionIds: ["opt_feb_001", "opt_fey_001"],
  },
  {
    groupId: "gs_excl_exterior_accents",
    optionIds: ["opt_efr_001", "opt_edu_001"],
    selectionMode: "required_single_within_group",
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
    groupId: "excl_suede_trunk_liner",
    optionIds: ["opt_sxb_001", "opt_sxr_001", "opt_sxt_001"],
  },
  {
    groupId: "excl_ext_accents",
    optionIds: ["opt_efr_001", "opt_efy_001", "opt_edu_001"],
    selectionMode: "required_single_within_group",
  },
];

const expectedTrimTooltips = {
  "1LT": "1LT is the car for driving purists who want the lightest Corvette possible, but one that's still very well equipped.",
  "2LT": "2LT adds a number of comfort and convenience features in addition to color-matched interior options.",
  "3LT": "3LT is the utmost in luxury performance, with a leather-wrapped interior.",
};

const expectedPaintImages = {
  GEC: ["opt_gec_001", "https://stingraychevroletcorvette.com/wp-content/uploads/pictures/27vette/expt_269_gec.png", "Pitch Gray Metallic"],
  GPH: ["opt_gph_001", "https://stingraychevroletcorvette.com/wp-content/uploads/pictures/27vette/expt_268_gph.png", "Red Mist Metallic Tintcoat"],
  G26: ["opt_g26_001", "https://stingraychevroletcorvette.com/wp-content/uploads/pictures/27vette/expt_267_g26.png", "Sebring Orange Tintcoat"],
  GBK: ["opt_gbk_001", "https://stingraychevroletcorvette.com/wp-content/uploads/pictures/27vette/expt_266_gbk.png", "Competition Yellow Tintcoat Metallic"],
  G4Z: ["opt_g4z_001", "https://stingraychevroletcorvette.com/wp-content/uploads/pictures/27vette/expt_265_g4z.png", "Roswell Green Metallic"],
  GKA: ["opt_gka_001", "https://stingraychevroletcorvette.com/wp-content/uploads/pictures/27vette/expt_264_gka.png", "Blade Silver Metallic"],
  GBA: ["opt_gba_001", "https://stingraychevroletcorvette.com/wp-content/uploads/pictures/27vette/expt_263_gba.png", "Black"],
  G8G: ["opt_g8g_001", "https://stingraychevroletcorvette.com/wp-content/uploads/pictures/27vette/expt_262_g8g.png", "Arctic White"],
  GKZ: ["opt_gkz_001", "https://stingraychevroletcorvette.com/wp-content/uploads/pictures/27vette/expt_261_gkz.png", "Torch Red"],
  GTR: ["opt_gtr_001", "https://stingraychevroletcorvette.com/wp-content/uploads/pictures/27vette/expt_260_gtr.png", "Admiral Blue Metallic"],
};

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
});

test("generated app data applies active model assets from asset_map", () => {
  const dataWindow = loadDataWindow();
  const registry = dataWindow.CORVETTE_FORM_DATA;

  assert.equal(
    registry.models.stingray.image_url,
    "https://stingraychevroletcorvette.com/wp-content/uploads/pictures/27vette/st-copy.png"
  );
  assert.equal(registry.models.stingray.image_alt, "Corvette Stingray");
  assert.equal(registry.models.stingray.image_fit, "cover");
  assert.equal(registry.models.stingray.image_position, "center");

  assert.equal(
    registry.models.grandSport.image_url,
    "https://stingraychevroletcorvette.com/wp-content/uploads/pictures/27vette/gs-copy.png"
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

test("runtime renders Stingray paint image media from generated choice data", () => {
  const runtime = loadRuntime();
  const paintChoice = runtime.data.choices.find(
    (choice) => choice.variant_id === "1lt_c07" && choice.option_id === "opt_g8g_001"
  );

  const html = runtime.renderChoiceCard(paintChoice, new Map());
  assert.match(html, /choice-media/);
  assert.match(html, /expt_262_g8g\.png/);
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
  assert.match(html, /choice-state disabled-reason info-tooltip" tabindex="0"/);
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
  assert.match(html, /choice-relationship-badge includes info-tooltip/);
  assert.match(html, /Includes 2 items/);
  assert.match(html, /<span class="tooltip-trigger-text">Includes 2 items<\/span>/);
  assert.match(html, /SB7 Corvette Racing Themed Jake and Stingray R Graphics Package/);
  assert.match(html, /VWD Stingray R Logo Wheel Center Caps/);
  assert.doesNotMatch(html, /Workbook includes|Workbook-defined/);
  assert.doesNotMatch(html, /choice-relationship-badge includes[\s\S]*info-icon/);

  const disabledIncludesChoice = runtime.activeChoiceRows().find((choice) => choice.option_id === "opt_fe4_001");
  html = runtime.renderChoiceCard(disabledIncludesChoice, new Map());
  assert.match(html, /choice-relationship-badge includes disabled info-tooltip/);

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

  const autoHtml = runtime.elements.get("#autoList").innerHTML;
  assert.match(autoHtml, /summary-rpo-row/);
  assert.match(autoHtml, /info-tooltip/);
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

test("Grand Sport required exclusive groups cannot be left empty", () => {
  const runtime = loadRuntime();
  runtime.activateModel("grandSport");
  runtime.state.bodyStyle = "coupe";
  runtime.state.trimLevel = "1LT";
  runtime.resetDefaults();
  runtime.reconcileSelections();

  for (const expected of expectedGrandSportExclusiveGroups.filter((group) => group.selectionMode === "required_single_within_group")) {
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

    runtime.handleChoice(alternateChoice);
    assert.equal(runtime.state.selected.has(alternateChoice.option_id), true, `${alternateChoice.option_id} should be selected after switching`);
    assert.equal(runtime.state.selected.has(defaultChoice.option_id), false, `${defaultChoice.option_id} should be removed after alternate selection`);

    runtime.handleChoice(alternateChoice);
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
  assert.ok(j57, "J57 should render as a selectable brake card");
  assert.equal(j56.active, "True");
  assert.equal(j56.status, "available");
  assert.equal(j56.selectable, "False");
  assert.equal(j56.display_behavior, "display_only");
  assert.equal(runtime.disableReasonForChoice(j56), "Included with FEB Z52 Sport Performance Package.");
  assert.equal(runtime.disableReasonForChoice(j57), "");

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

test("Grand Sport J57 soft-defaults J6D into selected RPOs instead of auto-added RPOs", () => {
  const runtime = loadRuntime();
  runtime.activateModel("grandSport");
  runtime.state.bodyStyle = "coupe";
  runtime.state.trimLevel = "1LT";
  runtime.resetDefaults();
  runtime.reconcileSelections();

  const j57 = runtime.activeChoiceRows().find((choice) => choice.option_id === "opt_j57_001");
  assert.ok(j57, "J57 should be selectable");
  runtime.handleChoice(j57);
  let order = runtime.currentOrder();
  assert.equal(order.selected_options.some((item) => item.rpo === "J57"), true, "J57 should be selected");
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
  runtime.handleChoice(j57);
  assert.equal(runtime.state.selected.has("opt_j57_001"), true, "J57 should be selected");
  assert.equal(runtime.state.selected.has("opt_jx6_001"), false, "J57 should replace JX6");
  assert.equal(runtime.state.selected.has("opt_j56_001"), false, "J57 should not leave J56 selected");

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
