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
  get state() { return state; },
  get data() { return data; },
  activateModel,
  activeChoiceRows,
  resetDefaults,
  reconcileSelections,
  handleChoice,
  currentOrder,
  compactOrder,
  missingRequirementDetails,
  computeAutoAdded,
  optionPrice,
  disableReasonForChoice,
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

function selectedRpos(runtime) {
  const choices = runtime.activeChoiceRows();
  return [...runtime.state.selected].map((id) => choices.find((choice) => choice.option_id === id)?.rpo || id).sort();
}

function autoAddedRpos(runtime) {
  const choices = runtime.activeChoiceRows();
  return [...runtime.computeAutoAdded().keys()].map((id) => choices.find((choice) => choice.option_id === id)?.rpo || id).sort();
}

function missingText(runtime) {
  return runtime.missingRequirementDetails().map((item) => item.detail).join("\n");
}

test("Z06 packages stay selectable after selection while inner requirements remain visible", () => {
  for (const [packageRpo, expectedRequirement] of [
    ["Z07", /T0F|T0G|aero/i],
    ["PDB", /ROY|ROZ|STZ|carbon fiber wheel/i],
    ["PDD", /ROY|ROZ|STZ|carbon fiber wheel/i],
    ["PDF", /ROY|ROZ|STZ|carbon fiber wheel/i],
  ]) {
    const runtime = z06Runtime();
    const packageChoice = choice(runtime, packageRpo);
    assert.equal(runtime.disableReasonForChoice(packageChoice), "", `${packageRpo} should be initially selectable`);

    runtime.handleChoice(packageChoice);
    runtime.reconcileSelections();

    assert.equal(runtime.state.selected.has(packageChoice.option_id), true, `${packageRpo} should remain selected`);
    assert.equal(runtime.disableReasonForChoice(packageChoice), "", `${packageRpo} should not become disabled by its own inner requirement`);
    assert.match(missingText(runtime), expectedRequirement, `${packageRpo} should still report its unresolved inner requirement`);
  }
});

test("Z06 carbon wheel/brake package peers switch instead of disabling one another", () => {
  const runtime = z06Runtime();
  runtime.handleChoice(choice(runtime, "PDB"));
  runtime.reconcileSelections();

  assert.equal(runtime.disableReasonForChoice(choice(runtime, "PDD")), "", "PDD should stay clickable while PDB is selected");
  assert.equal(runtime.disableReasonForChoice(choice(runtime, "PDF")), "", "PDF should stay clickable while PDB is selected");

  runtime.handleChoice(choice(runtime, "PDD"));
  runtime.reconcileSelections();

  assert.equal(runtime.state.selected.has(choice(runtime, "PDD").option_id), true, "PDD should be selected after switching package peers");
  assert.equal(runtime.state.selected.has(choice(runtime, "PDB").option_id), false, "PDB should be removed by package peer replacement");
  assert.equal(runtime.disableReasonForChoice(choice(runtime, "PDB")), "", "PDB should remain clickable after switching to PDD");
});

test("Z06 aero choices switch consistently from the default without greyed-out peers", () => {
  const runtime = z06Runtime();
  assert.equal(runtime.state.selected.has(choice(runtime, "T0E").option_id), true, "T0E should seed as the default aero choice");

  runtime.handleChoice(choice(runtime, "T0F"));
  runtime.reconcileSelections();
  assert.equal(runtime.state.selected.has(choice(runtime, "T0F").option_id), true, "T0F should replace the default aero choice");
  assert.equal(runtime.state.selected.has(choice(runtime, "T0E").option_id), false, "T0E should be removed after selecting T0F");
  assert.equal(runtime.disableReasonForChoice(choice(runtime, "5ZV")), "", "5ZV should not be greyed out by T0F");
  assert.equal(runtime.disableReasonForChoice(choice(runtime, "T0G")), "", "T0G should not be greyed out by T0F");

  runtime.handleChoice(choice(runtime, "5ZV"));
  runtime.reconcileSelections();
  assert.equal(runtime.state.selected.has(choice(runtime, "5ZV").option_id), true, "5ZV should be selectable as an aero peer");
  assert.equal(runtime.state.selected.has(choice(runtime, "T0F").option_id), false, "5ZV should replace T0F instead of being disabled by it");

  runtime.handleChoice(choice(runtime, "T0G"));
  runtime.reconcileSelections();
  assert.equal(runtime.state.selected.has(choice(runtime, "T0G").option_id), true, "T0G should replace 5ZV consistently");
  assert.equal(runtime.state.selected.has(choice(runtime, "5ZV").option_id), false, "T0G should remove 5ZV through the same peer replacement path");
});

test("Z06 package-included aero ground effects stay locked until the aero peer changes", () => {
  const runtime = z06Runtime();
  runtime.handleChoice(choice(runtime, "T0F"));
  runtime.reconcileSelections();

  assert.equal(autoAddedRpos(runtime).includes("CFZ"), true, "T0F should auto-add CFZ");
  assert.equal(runtime.optionPrice(choice(runtime, "CFZ").option_id), 0, "T0F-included CFZ should price at zero");
  assert.notEqual(runtime.disableReasonForChoice(choice(runtime, "CFV")), "", "CFV should be locked out while T0F includes CFZ");
  assert.notEqual(runtime.disableReasonForChoice(choice(runtime, "CFL")), "", "CFL should be locked out while T0F includes CFZ");

  runtime.handleChoice(choice(runtime, "CFV"));
  runtime.reconcileSelections();
  assert.equal(autoAddedRpos(runtime).includes("CFZ"), true, "clicking CFV should not suppress T0F-included CFZ");
  assert.equal(runtime.state.selected.has(choice(runtime, "CFV").option_id), false, "CFV should not become selected while CFZ is locked by T0F");

  runtime.handleChoice(choice(runtime, "T0G"));
  runtime.reconcileSelections();
  assert.equal(autoAddedRpos(runtime).includes("CFV"), true, "switching to T0G should lock CFV instead");
  assert.equal(autoAddedRpos(runtime).includes("CFZ"), false, "switching away from T0F should release CFZ");
});

test("Z06 exhaust tips are mutually exclusive and NWI does not require WUB", () => {
  const runtime = z06Runtime();
  const nwi = choice(runtime, "NWI");
  const nga = choice(runtime, "NGA");

  assert.equal(runtime.disableReasonForChoice(nwi), "", "NWI should not require WUB before selection");
  assert.equal(runtime.state.selected.has(nga.option_id), true, "NGA should seed as the default exhaust tip");

  runtime.handleChoice(nwi);
  runtime.reconcileSelections();
  assert.equal(runtime.state.selected.has(nwi.option_id), true, "NWI should be selected after clicking it");
  assert.equal(runtime.state.selected.has(nga.option_id), false, "NWI should replace default NGA");

  runtime.handleChoice(nwi);
  runtime.reconcileSelections();
  assert.equal(runtime.state.selected.has(nwi.option_id), false, "NWI should be removable as an optional exhaust-tip upgrade");
  assert.equal(runtime.state.selected.has(nga.option_id), true, "NGA should restore when NWI is removed");
});
