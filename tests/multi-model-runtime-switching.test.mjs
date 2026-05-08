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
  const document = {
    querySelector(selector) {
      if (!elements.has(selector)) elements.set(selector, makeElement());
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
    document,
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
  currentOrder,
  compactOrder,
  plainTextOrderSummary,
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
    optionIds: ["opt_bc7_001", "opt_bc4_001", "opt_bc4_002", "opt_bcp_001", "opt_bcp_002", "opt_bcs_001", "opt_bcs_002"],
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

    const [firstId, secondId] = expected.optionIds;
    const firstChoice = runtime.activeChoiceRows().find((choice) => choice.option_id === firstId);
    const secondChoice = runtime.activeChoiceRows().find((choice) => choice.option_id === secondId);
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

test("model-specific exports keep the compact schema and Stingray filenames", () => {
  const runtime = loadRuntime();

  runtime.exportJson();
  let jsonDownload = runtime.downloads.at(-1);
  assert.equal(jsonDownload.filename, "stingray-order-summary.json");
  assert.deepEqual(Object.keys(JSON.parse(jsonDownload.content)), [
    "title",
    "submitted_at",
    "customer",
    "vehicle",
    "sections",
    "standard_equipment",
    "msrp",
  ]);

  runtime.exportCsv();
  let csvDownload = runtime.downloads.at(-1);
  assert.equal(csvDownload.filename, "stingray-order-summary.csv");
  assert.equal(csvDownload.content.split("\n")[0], "section,rpo,label,price");

  runtime.activateModel("grandSport");
  runtime.exportJson();
  jsonDownload = runtime.downloads.at(-1);
  assert.equal(jsonDownload.filename, "grand-sport-order-summary.json");
  assert.equal(JSON.parse(jsonDownload.content).title, "2027 Corvette Grand Sport");

  runtime.exportCsv();
  csvDownload = runtime.downloads.at(-1);
  assert.equal(csvDownload.filename, "grand-sport-order-summary.csv");
  assert.equal(csvDownload.content.split("\n")[0], "section,rpo,label,price");
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
  const order = runtime.currentOrder();
  assert.equal(order.metadata.selected_interior_id, "3LT_AH2_EL9");
  assert.equal(order.selected_interior.rpo, "EL9");
  assert.equal(order.selected_interior.label, "Santorini Blue Dipped with Torch Red accents");
  assert.equal(order.metadata.missing_required.includes("Base Interior"), false);

  const compact = runtime.compactOrder();
  const seatsInterior = compact.sections.find((section) => section.section === "Seats & Interior");
  assert.ok(seatsInterior, "compact Grand Sport order should include Seats & Interior");
  assert.ok(
    seatsInterior.items.some((item) => item.rpo === "EL9" && item.label === "Santorini Blue Dipped with Torch Red accents"),
    "compact order should include selected Grand Sport interior"
  );
  assert.match(runtime.plainTextOrderSummary(compact), /EL9 Santorini Blue Dipped with Torch Red accents/);
});
