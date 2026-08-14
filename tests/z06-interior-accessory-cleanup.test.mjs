import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import fs from "node:fs";
import test from "node:test";
import vm from "node:vm";

import { assertTrackedArtifactsUnchanged, readTrackedArtifacts } from "./lib/tracked-artifacts.mjs";

const testRoot = "/tmp/27vette-z06-interior-accessory-runtime-test";
const runtimePath = `${testRoot}/form-output/runtime/z06-runtime-contract.json`;
let cachedContract;

function makeElement() {
  return {
    textContent: "",
    innerHTML: "",
    value: "",
    dataset: {},
    listeners: {},
    hidden: false,
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
    fetch: async () => ({ ok: true, async json() { return { success: true }; } }),
    document: {
      querySelector(selector) {
        if (!elements.has(selector)) elements.set(selector, makeElement());
        return elements.get(selector);
      },
      createElement() {
        return makeElement();
      },
    },
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
      createObjectURL() { return ""; },
      revokeObjectURL() {},
    },
    Blob: class TestBlob {},
  };
  const source = fs.readFileSync("form-app/app.js", "utf8").replace(
    /\ninit\(\);\s*$/,
    `
window.__testApi = {
  get activeModelKey() { return activeModelKey; },
  get state() { return state; },
  get data() { return data; },
  activateModel,
  activeChoiceRows,
  resetDefaults,
  reconcileSelections,
  handleChoice,
  currentOrder,
  computeAutoAdded,
  optionPrice,
  disableReasonForChoice,
  adjustedInteriorDisplayPrice,
  renderInteriorCard,
};
init();
`
  );
  vm.runInNewContext(source, context);
  return context.window.__testApi;
}

function z06Runtime({ bodyStyle = "coupe", trimLevel = "1LZ" } = {}) {
  const runtime = loadRuntime();
  runtime.activateModel("z06");
  runtime.state.bodyStyle = bodyStyle;
  runtime.state.trimLevel = trimLevel;
  runtime.resetDefaults();
  runtime.reconcileSelections();
  return runtime;
}

function choice(runtime, rpo) {
  const found = runtime.activeChoiceRows().find((item) => item.rpo === rpo);
  assert.ok(found, `expected active Z06 choice ${rpo}`);
  return found;
}

function maybeChoice(runtime, rpo) {
  return runtime.activeChoiceRows().find((item) => item.rpo === rpo);
}

function autoAddedRpos(runtime) {
  const choices = runtime.activeChoiceRows();
  return [...runtime.computeAutoAdded().keys()].map((id) => choices.find((choice) => choice.option_id === id)?.rpo || id).sort();
}

function runtimeContract() {
  if (cachedContract) return cachedContract;
  fs.rmSync(testRoot, { recursive: true, force: true });
  fs.mkdirSync(testRoot, { recursive: true });
  const before = readTrackedArtifacts();
  execFileSync(
    ".venv/bin/python",
    [
      "scripts/generate_form.py",
      "--model",
      "z06",
      "--output-root",
      testRoot,
    ],
    {
      encoding: "utf8",
      stdio: "pipe",
    }
  );
  assertTrackedArtifactsUnchanged(before);
  assert.ok(
    fs.existsSync(runtimePath),
    "--output-root must receive the strict runtime contract this gate consumes"
  );
  cachedContract = JSON.parse(fs.readFileSync(runtimePath, "utf8"));
  assert.equal(cachedContract.dataset.status, "runtime_active");
  return cachedContract;
}

test("Z06 UQT follows LZ trim-scoped selectable and standard-equipment contract", () => {
  const contract = runtimeContract();
  for (const variantId of ["1lz_h07", "1lz_h67"]) {
    const uqt = contract.choices.find((choice) => choice.choice_id === `${variantId}__opt_uqt_001`);
    assert.ok(uqt, `${variantId} should emit UQT`);
    assert.equal(uqt.status, "available");
    assert.equal(uqt.selectable, "True");
    assert.equal(uqt.section_id, "sec_inte_001");
    assert.equal(uqt.step_key, "interior_trim");
  }
  for (const [variantId, sectionId] of [
    ["2lz_h07", "sec_2lte_001"],
    ["2lz_h67", "sec_2lte_001"],
    ["3lz_h07", "sec_3lte_001"],
    ["3lz_h67", "sec_3lte_001"],
  ]) {
    const uqt = contract.choices.find((choice) => choice.choice_id === `${variantId}__opt_uqt_001`);
    assert.ok(uqt, `${variantId} should emit UQT`);
    assert.equal(uqt.status, "standard");
    assert.equal(uqt.selectable, "False");
    assert.equal(uqt.display_behavior, "display_only");
    assert.equal(uqt.section_id, sectionId);
    assert.equal(uqt.step_key, "standard_equipment");
  }
});

test("Z06 runtime does not expose standard UQT or N3W as selectable front-end options", () => {
  for (const trimLevel of ["2LZ", "3LZ"]) {
    const runtime = z06Runtime({ trimLevel });
    const uqt = maybeChoice(runtime, "UQT");
    assert.ok(uqt, `${trimLevel} should still include UQT in standard-equipment data`);
    assert.equal(uqt.step_key, "standard_equipment");
    assert.equal(uqt.selectable, "False");
    assert.equal(uqt.display_behavior, "display_only");
  }
  for (const trimLevel of ["1LZ", "2LZ", "3LZ"]) {
    const runtime = z06Runtime({ trimLevel });
    assert.equal(maybeChoice(runtime, "N3W"), undefined, `${trimLevel} should not show N3W as an active choice`);
  }
});

test("Z06 3LZ seat pricing is trim-scoped in generated data and runtime", () => {
  const contract = runtimeContract();
  const priceRules = new Map(contract.priceRules.map((rule) => [rule.price_rule_id, rule]));
  for (const [ruleId, targetOptionId, priceValue] of [
    ["z06_pr_3lz_ah2_seat_001", "opt_ah2_001", 0],
    ["z06_pr_3lz_ae4_seat_001", "opt_ae4_002", 595],
  ]) {
    const rule = priceRules.get(ruleId);
    assert.ok(rule, `${ruleId} should be emitted`);
    assert.equal(rule.condition_option_id, targetOptionId);
    assert.equal(rule.target_option_id, targetOptionId);
    assert.equal(rule.price_rule_type, "override");
    assert.equal(rule.trim_level_scope, "3LZ");
    assert.equal(rule.price_value, priceValue);
  }
  const runtime = z06Runtime({ trimLevel: "3LZ" });
  assert.equal(runtime.optionPrice(choice(runtime, "AH2").option_id), 0);
  assert.equal(runtime.optionPrice(choice(runtime, "AE4").option_id, [choice(runtime, "AE4").option_id]), 595);
});

test("Z06 FA5 and FA6 are mutually exclusive workbook-generated peers", () => {
  const runtime = z06Runtime({ trimLevel: "3LZ" });
  runtime.handleChoice(choice(runtime, "FA5"));
  runtime.reconcileSelections();
  assert.equal(runtime.state.selected.has(choice(runtime, "FA5").option_id), true, "FA5 should be selected first");

  runtime.handleChoice(choice(runtime, "FA6"));
  runtime.reconcileSelections();
  assert.equal(runtime.state.selected.has(choice(runtime, "FA6").option_id), true, "FA6 should be selected after switching peers");
  assert.equal(runtime.state.selected.has(choice(runtime, "FA5").option_id), false, "FA5 should be removed after selecting FA6");
});

test("Z06 accessory packages auto-add included components at zero price", () => {
  for (const [packageRpo, includedRpos] of [
    ["PCQ", ["VWE", "VWT"]],
    ["PDY", ["RYT", "S08"]],
    ["PEF", ["CAV", "RIA"]],
  ]) {
    const runtime = z06Runtime();
    runtime.handleChoice(choice(runtime, packageRpo));
    runtime.reconcileSelections();
    assert.equal(runtime.state.selected.has(choice(runtime, packageRpo).option_id), true, `${packageRpo} should be selected`);
    for (const rpo of includedRpos) {
      assert.equal(autoAddedRpos(runtime).includes(rpo), true, `${packageRpo} should auto-add ${rpo}`);
      assert.equal(runtime.optionPrice(choice(runtime, rpo).option_id), 0, `${packageRpo}-included ${rpo} should price at zero`);
    }
  }
});

test("Z06 chargeable interior cards and selected component line items agree", () => {
  const runtime = z06Runtime({ trimLevel: "3LZ" });
  const interior = runtime.data.interiors.find((item) => item.interior_id === "3LZ_AE4_HTT_N2Z");
  assert.ok(interior, "test expects a 3LZ AE4 suede interior fixture");
  assert.equal(runtime.adjustedInteriorDisplayPrice(interior), 1490, "3LZ AE4 suede interior card should show its incremental charge before AE4 is selected");
  assert.match(runtime.renderInteriorCard(interior), /\$1,490/, "rendered interior card should display the actual charge before AE4 is selected");

  runtime.handleChoice(choice(runtime, "AE4"));
  runtime.reconcileSelections();
  assert.equal(runtime.adjustedInteriorDisplayPrice(interior), 895, "after AE4 seat selection, the same card should show the suede-only incremental charge");
  runtime.state.selectedInterior = interior.interior_id;
  runtime.reconcileSelections();
  const order = runtime.currentOrder();
  assert.ok(order.interior_components.some((item) => item.rpo === "AE4" && Number(item.price) === 595));
  assert.ok(order.interior_components.some((item) => item.rpo === "N2Z" && Number(item.price) === 895));
  assert.equal(order.pricing.selected_options_total >= 1490, true);
});

test("Z06 3LZ R6X AH2 interior summary does not re-add the raw AH2 seat price", () => {
  const runtime = z06Runtime({ trimLevel: "3LZ" });
  const ah2 = choice(runtime, "AH2");
  const interior = runtime.data.interiors.find((item) => item.interior_id === "3LZ_R6X_AH2_HUU");
  assert.ok(interior, "test expects the reported 3LZ R6X AH2 interior fixture");
  assert.equal(Number(ah2.base_price), 1695, "fixture should preserve the raw AH2 source price that caused the regression");
  assert.equal(runtime.optionPrice(ah2.option_id), 0, "3LZ AH2 should resolve to its trim-scoped zero-price override");
  assert.equal(Number(interior.price), 995);
  assert.ok(interior.interior_components.some((item) => item.rpo === "R6X" && Number(item.price) === 995));

  runtime.handleChoice(ah2);
  runtime.reconcileSelections();
  runtime.state.selectedInterior = interior.interior_id;
  runtime.reconcileSelections();

  const order = runtime.currentOrder();
  assert.equal(order.selected_interior.rpo, "HUU");
  assert.equal(Number(order.selected_interior.price), 0, "interior identity line should not carry the old $700 AH2 remainder");
  const r6xLines = order.interior_components.filter((item) => item.rpo === "R6X");
  assert.equal(r6xLines.length, 1, "R6X should appear once for the selected custom interior");
  assert.equal(Number(r6xLines[0].price), 995, "R6X should remain the only priced line for the selected custom interior");
  assert.equal(
    order.selected_options.some((item) => item.rpo === "AH2"),
    false,
    "the replaced AH2 seat line should stay suppressed when the selected interior replaces the seat"
  );
});
