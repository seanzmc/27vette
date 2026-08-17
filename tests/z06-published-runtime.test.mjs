import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";
import vm from "node:vm";

import { cell, workbookRows, workbookTruthy } from "./lib/workbook-rows.mjs";

const expectedZ06VariantIds = ["1lz_h07", "2lz_h07", "3lz_h07", "1lz_h67", "2lz_h67", "3lz_h67"];
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
  };
}

function loadDataWindow() {
  const context = { window: {} };
  vm.runInNewContext(fs.readFileSync("form-app/data.js", "utf8"), context);
  return context.window;
}

function loadRuntime() {
  const dataWindow = loadDataWindow();
  const elements = new Map();
  const fetchCalls = [];
  const context = {
    window: {
      ...dataWindow,
      turnstile: {
        render(selector, options) {
          options.callback?.("test-turnstile-token");
          return "test-widget-id";
        },
        reset() {},
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
    document: {
      querySelector(selector) {
        if (!elements.has(selector)) {
          const element = makeElement();
          if (selector === "#dealerSubmitModal" || selector === "#confirmActionModal") element.hidden = true;
          elements.set(selector, element);
        }
        return elements.get(selector);
      },
      createElement() {
        return makeElement();
      },
    },
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
    Blob: class TestBlob {},
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
  activateModel,
  activeChoiceRows,
  resetDefaults,
  reconcileSelections,
  handleChoice,
  compactOrder,
  plainTextOrderSummary,
  openDealerSubmitModal,
  submitDealerBuild,
  dealerSubmissionPayload,
  missingRequired,
  fetchCalls,
  elements,
};
init();
`
  );
  vm.runInNewContext(source, context);
  return context.window.__testApi;
}

test("the published registry carries every promoted model and the full Z06 runtime", () => {
  const registry = loadDataWindow().CORVETTE_FORM_DATA;

  // Checkpoint 1 of the fast layered validation suite (spec §9) removed two
  // restatements from this gate: `defaultModelKey === "stingray"`, which is the
  // default_model_is_stingray acceptance lock owned by
  // tests/multi-model-runtime-switching.test.mjs, and the six-key membership
  // literal. §4.4 allows one owner per decision. Membership is compared here
  // against the workbook's own promotion rows instead.
  const promotedRegistryKeys = workbookRows("model_registry_promotion")
    .filter((row) => workbookTruthy(row.active) && workbookTruthy(row.promoted_to_runtime))
    .map((row) => cell(row.registry_key))
    .sort();
  assert.ok(promotedRegistryKeys.length > 0, "model_registry_promotion promotes no model");
  assert.deepEqual(Object.keys(registry.models).sort(), promotedRegistryKeys);

  assert.equal(registry.models.z06.key, "z06");
  assert.equal(registry.models.z06.label, "Z06");
  assert.equal(registry.models.z06.modelName, "Corvette Z06");
  assert.equal(registry.models.z06.exportSlug, "z06");
  assert.equal(registry.models.z06.data.dataset.status, "runtime_active");
  assert.doesNotMatch(registry.models.z06.data.dataset.name, /draft/i);
  assert.deepEqual(
    JSON.parse(JSON.stringify(registry.models.z06.data.variants.map((variant) => variant.variant_id))),
    expectedZ06VariantIds
  );
});

test("promoted Z06 runtime data strips draft-only provenance and protects source-data cleanup", () => {
  const z06Data = loadDataWindow().CORVETTE_FORM_DATA.models.z06.data;

  assert.equal(Object.hasOwn(z06Data, "draftMetadata"), false);
  assert.equal(z06Data.choices.some((choice) => Object.hasOwn(choice, "source_option_name")), false);
  assert.equal(z06Data.choices.some((choice) => Object.hasOwn(choice, "review_flags")), false);
  for (const field of ["source_detail_raw", "choice_mode", "selection_mode", "selection_mode_label"]) {
    assert.equal(z06Data.choices.some((choice) => Object.hasOwn(choice, field)), false, `Z06 choices leaked ${field}`);
  }
  assert.equal(
    z06Data.standardEquipment.some((row) => Object.hasOwn(row, "source_detail_raw")),
    false,
    "Z06 standard equipment leaked source_detail_raw"
  );
  assert.ok(z06Data.sections.some((section) => section.selection_mode), "Z06 keeps section selection_mode");
  assert.ok(z06Data.sections.some((section) => section.choice_mode), "Z06 keeps section choice_mode");
  assert.ok(z06Data.sections.some((section) => section.selection_mode_label), "Z06 keeps section selection_mode_label");
  assert.ok(z06Data.exclusiveGroups.some((group) => group.selection_mode), "Z06 keeps exclusive group selection_mode");

  const pricedStandardChoices = z06Data.choices.filter(
    (choice) => choice.option_id !== "opt_r8e_002" && standardSections.has(choice.section_id) && Number(choice.base_price || 0) > 0
  );
  assert.deepEqual(JSON.parse(JSON.stringify(pricedStandardChoices)), []);

  const nonSelectableDefaults = z06Data.choices.filter(
    (choice) => choice.display_behavior === "default_selected" && choice.selectable !== "True"
  );
  assert.deepEqual(JSON.parse(JSON.stringify(nonSelectableDefaults)), []);

  const missingDisplayOrder = z06Data.choices.filter((choice) => choice.display_order === "" || choice.display_order == null);
  assert.deepEqual(JSON.parse(JSON.stringify(missingDisplayOrder)), []);
});

test("runtime can switch to Z06 and build a model-scoped order", () => {
  const runtime = loadRuntime();

  assert.equal(runtime.activeModelKey, "stingray");
  runtime.activateModel("z06");

  assert.equal(runtime.activeModelKey, "z06");
  assert.equal(runtime.activeModelLabel, "Z06");
  assert.deepEqual(
    JSON.parse(JSON.stringify(runtime.variants.map((variant) => variant.variant_id))),
    expectedZ06VariantIds
  );

  runtime.state.bodyStyle = "coupe";
  runtime.state.trimLevel = "1LZ";
  runtime.resetDefaults();
  runtime.reconcileSelections();

  assert.equal(runtime.activeChoiceRows().every((choice) => choice.variant_id === "1lz_h07"), true);
  assert.equal(runtime.compactOrder().title, "2027 Corvette Z06");
  assert.match(runtime.plainTextOrderSummary(), /Corvette Z06 Coupe 1LZ/);
});

test("Z06 dealer submission payload stays model-scoped when posted", async () => {
  const runtime = loadRuntime();
  runtime.activateModel("z06");
  runtime.state.bodyStyle = "coupe";
  runtime.state.trimLevel = "1LZ";
  runtime.resetDefaults();
  runtime.reconcileSelections();
  for (const sectionName of ["Paint", "Wheels", "Badges", "Caliper Color", "Roof", "Seats"]) {
    const choice = runtime.activeChoiceRows().find(
      (item) => item.section_name === sectionName && item.selectable === "True" && item.active === "True" && item.status === "available"
    );
    assert.ok(choice, `Z06 dealer submission test should find a selectable ${sectionName} choice`);
    runtime.handleChoice(choice);
  }
  const selectedSeat = runtime.activeChoiceRows().find((choice) => runtime.state.selected.has(choice.option_id) && choice.section_name === "Seats");
  const interior = runtime.data.interiors.find(
    (item) => item.trim_level === "1LZ" && (!selectedSeat || item.seat_code === selectedSeat.rpo)
  );
  assert.ok(interior, "Z06 dealer submission test should find a matching 1LZ interior");
  runtime.state.selectedInterior = interior.interior_id;
  runtime.reconcileSelections();
  assert.deepEqual(
    JSON.parse(JSON.stringify(runtime.missingRequired())),
    [],
    "Z06 dealer submission test build should satisfy required selections"
  );
  runtime.openDealerSubmitModal();

  runtime.elements.get("#dealerSubmitName").value = "Ada Buyer";
  runtime.elements.get("#dealerSubmitEmail").value = "ada@example.com";
  const submission = await runtime.submitDealerBuild();

  assert.equal(submission.payload.model, "z06");
  assert.match(submission.payload.plain_text_summary, /Corvette Z06 Coupe 1LZ/);
  assert.equal(submission.payload.customer.email, "ada@example.com");
  assert.match(submission.payload.msrp, /^\$\d{1,3}(,\d{3})*$/);
  assert.equal(submission.result.entry_id, 445566);
  assert.equal(JSON.parse(runtime.fetchCalls[0].options.body).model, "z06");
  assert.equal(JSON.parse(runtime.fetchCalls[0].options.body).msrp, submission.payload.msrp);
});
