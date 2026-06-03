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

test("Z06 package selections default their required inner aero and wheel choices", () => {
  for (const [packageRpo, expectedAutoRpos] of [
    ["Z07", ["J57", "T0F", "CFZ"]],
    ["PDB", ["J57", "J6D", "ROY"]],
    ["PDD", ["Z07", "J57", "T0F", "CFZ", "ROY"]],
    ["PDF", ["Z07", "J57", "T0G", "CFV", "ROY"]],
  ]) {
    const runtime = z06Runtime();
    const packageChoice = choice(runtime, packageRpo);
    assert.equal(runtime.disableReasonForChoice(packageChoice), "", `${packageRpo} should be initially selectable`);

    runtime.handleChoice(packageChoice);
    runtime.reconcileSelections();

    const autoRpos = autoAddedRpos(runtime);
    assert.equal(runtime.state.selected.has(packageChoice.option_id), true, `${packageRpo} should remain selected`);
    assert.equal(runtime.disableReasonForChoice(packageChoice), "", `${packageRpo} should not become disabled by its own inner choices`);
    for (const expectedRpo of expectedAutoRpos) {
      assert.equal(autoRpos.includes(expectedRpo), true, `${packageRpo} should auto-add/default ${expectedRpo}`);
    }
    assert.doesNotMatch(missingText(runtime), /T0F|T0G|aero|ROY|ROZ|STZ|carbon fiber wheel/i, `${packageRpo} should satisfy its forced inner aero/wheel defaults`);
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

test("Z06 Z07 defaults Carbon Flash aero and lets the user switch to visible carbon aero", () => {
  const runtime = z06Runtime();
  runtime.handleChoice(choice(runtime, "Z07"));
  runtime.reconcileSelections();

  assert.equal(runtime.state.selected.has(choice(runtime, "Z07").option_id), true, "Z07 should remain selected");
  assert.equal(runtime.state.selected.has(choice(runtime, "T0E").option_id), false, "Z07 should replace the default rear spoiler");
  assert.equal(autoAddedRpos(runtime).includes("T0F"), true, "Z07 should default to T0F aero");
  assert.equal(autoAddedRpos(runtime).includes("CFZ"), true, "Z07 default T0F should auto-add CFZ");
  assert.notEqual(runtime.disableReasonForChoice(choice(runtime, "T0E")), "", "T0E should be blocked while Z07 owns the aero choice");
  assert.notEqual(runtime.disableReasonForChoice(choice(runtime, "5ZV")), "", "5ZV should be blocked while Z07 owns the aero choice");
  assert.equal(runtime.disableReasonForChoice(choice(runtime, "T0G")), "", "T0G should stay available as the Z07 alternate aero choice");

  runtime.handleChoice(choice(runtime, "T0G"));
  runtime.reconcileSelections();

  assert.equal(runtime.state.selected.has(choice(runtime, "T0G").option_id), true, "T0G should become selected as the Z07 aero alternate");
  assert.equal(autoAddedRpos(runtime).includes("T0F"), false, "T0G should suppress the Z07 T0F default");
  assert.equal(autoAddedRpos(runtime).includes("CFZ"), false, "T0G should release CFZ");
  assert.equal(autoAddedRpos(runtime).includes("CFV"), true, "T0G should auto-add CFV");
});

test("Z06 carbon wheel package ROY defaults can switch to ROZ or STZ", () => {
  for (const packageRpo of ["PDB", "PDD", "PDF"]) {
    const runtime = z06Runtime();
    runtime.handleChoice(choice(runtime, packageRpo));
    runtime.reconcileSelections();

    assert.equal(autoAddedRpos(runtime).includes("ROY"), true, `${packageRpo} should default to ROY`);
    assert.equal(runtime.state.selected.has(choice(runtime, "SOE").option_id), false, `${packageRpo} should replace the default aluminum wheel`);
    assert.equal(runtime.disableReasonForChoice(choice(runtime, "ROZ")), "", `${packageRpo} should allow switching the default wheel to ROZ`);
    assert.equal(runtime.disableReasonForChoice(choice(runtime, "STZ")), "", `${packageRpo} should allow switching the default wheel to STZ`);

    runtime.handleChoice(choice(runtime, "ROZ"));
    runtime.reconcileSelections();
    assert.equal(runtime.state.selected.has(choice(runtime, "ROZ").option_id), true, `${packageRpo} should allow ROZ selection`);
    assert.equal(autoAddedRpos(runtime).includes("ROY"), false, `${packageRpo} ROZ selection should suppress the ROY default`);
    assert.doesNotMatch(missingText(runtime), /ROY|ROZ|STZ|carbon fiber wheel/i, `${packageRpo} should remain complete after switching to ROZ`);
  }
});

test("Z06 B6P changes BCW price without auto-adding BCW", () => {
  const runtime = z06Runtime();
  const b6p = choice(runtime, "B6P");
  const bcw = choice(runtime, "BCW");

  runtime.handleChoice(b6p);
  runtime.reconcileSelections();

  assert.equal(runtime.state.selected.has(b6p.option_id), true, "B6P should be selected");
  assert.equal(runtime.optionPrice(bcw.option_id), 895, "B6P should change BCW's displayed price");
  assert.equal(autoAddedRpos(runtime).includes("BCW"), false, "B6P should not auto-add BCW");
  assert.equal(runtime.state.selected.has(bcw.option_id), false, "BCW should remain unselected until the user chooses it");
});

test("Z06 Z07 locks included J57 even when J57 was selected first", () => {
  const runtime = z06Runtime();
  const j57 = choice(runtime, "J57");
  const z07 = choice(runtime, "Z07");

  runtime.handleChoice(j57);
  runtime.handleChoice(z07);
  runtime.reconcileSelections();

  assert.equal(runtime.state.selected.has(z07.option_id), true, "Z07 should be selected");
  assert.equal(autoAddedRpos(runtime).includes("J57"), true, "Z07 should own J57 as included equipment");

  runtime.handleChoice(j57);
  runtime.reconcileSelections();

  assert.equal(autoAddedRpos(runtime).includes("J57"), true, "J57 should stay included while Z07 is selected");
  assert.equal(runtime.state.selected.has(j57.option_id), false, "J57 should not remain a user-selected removable item under Z07");
});

test("Z06 T0F/T0G included ground effects replace a prior CFL selection", () => {
  const runtime = z06Runtime();
  runtime.handleChoice(choice(runtime, "CFL"));
  runtime.reconcileSelections();
  assert.equal(runtime.state.selected.has(choice(runtime, "CFL").option_id), true, "CFL should be user-selectable before aero package selection");

  runtime.handleChoice(choice(runtime, "T0F"));
  runtime.reconcileSelections();
  assert.equal(runtime.state.selected.has(choice(runtime, "CFL").option_id), false, "T0F should remove the prior CFL selection");
  assert.equal(autoAddedRpos(runtime).includes("CFZ"), true, "T0F should auto-add CFZ");

  const visibleRuntime = z06Runtime();
  visibleRuntime.handleChoice(choice(visibleRuntime, "CFL"));
  visibleRuntime.reconcileSelections();
  visibleRuntime.handleChoice(choice(visibleRuntime, "T0G"));
  visibleRuntime.reconcileSelections();
  assert.equal(visibleRuntime.state.selected.has(choice(visibleRuntime, "CFL").option_id), false, "T0G should remove the prior CFL selection");
  assert.equal(autoAddedRpos(visibleRuntime).includes("CFV"), true, "T0G should auto-add CFV");
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
