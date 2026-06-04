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
  get activeModelKey() { return activeModelKey; },
  get state() { return state; },
  get data() { return data; },
  activateModel,
  activeChoiceRows,
  resetDefaults,
  reconcileSelections,
  handleChoice,
  currentOrder,
  compactOrder,
  missingRequired,
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

function maybeChoice(runtime, rpo) {
  return runtime.activeChoiceRows().find((item) => item.rpo === rpo);
}

function selectedRpos(runtime) {
  const choices = runtime.activeChoiceRows();
  return [...runtime.state.selected].map((id) => choices.find((choice) => choice.option_id === id)?.rpo || id).sort();
}

function autoAddedRpos(runtime) {
  const choices = runtime.activeChoiceRows();
  return [...runtime.computeAutoAdded().keys()].map((id) => choices.find((choice) => choice.option_id === id)?.rpo || id).sort();
}

test("Z06 Z07 defaults T0F, allows T0G switching, and keeps J57 included at zero", () => {
  const runtime = z06Runtime();
  const z07 = choice(runtime, "Z07");

  assert.equal(runtime.disableReasonForChoice(z07), "", "Z07 should be selectable before choosing T0F/T0G");
  runtime.handleChoice(z07);
  runtime.reconcileSelections();

  assert.equal(runtime.state.selected.has(z07.option_id), true, "Z07 should be selected");
  assert.equal(autoAddedRpos(runtime).includes("J57"), true, "Z07 should auto-add J57");
  assert.equal(autoAddedRpos(runtime).includes("T0F"), true, "Z07 should default the required aero choice to T0F");
  assert.equal(autoAddedRpos(runtime).includes("CFZ"), true, "Z07 default T0F should auto-add CFZ");
  assert.equal(runtime.state.selected.has(choice(runtime, "T0E").option_id), false, "Z07 should replace the T0E default spoiler");
  assert.equal(runtime.optionPrice(choice(runtime, "J57").option_id), 0, "Z07-included J57 should price at zero");
  assert.doesNotMatch(
    runtime.missingRequirementDetails().map((item) => item.detail).join("\n"),
    /T0F|T0G|aero/i,
    "Z07 should satisfy its aero requirement with default T0F"
  );

  runtime.handleChoice(choice(runtime, "J57"));
  runtime.reconcileSelections();
  assert.equal(autoAddedRpos(runtime).includes("J57"), true, "auto-added J57 should not be removable while Z07 is selected");

  runtime.handleChoice(choice(runtime, "T0G"));
  runtime.reconcileSelections();
  assert.equal(runtime.state.selected.has(choice(runtime, "T0G").option_id), true, "T0G should be selectable as the Z07 aero alternate");
  assert.equal(autoAddedRpos(runtime).includes("T0F"), false, "T0G should suppress the T0F default");
  assert.equal(autoAddedRpos(runtime).includes("CFV"), true, "T0G should auto-add CFV");
});

test("Z06 T0F does not require J57 as a prerequisite", () => {
  const runtime = z06Runtime();
  const t0f = choice(runtime, "T0F");

  assert.equal(runtime.disableReasonForChoice(t0f), "", "T0F should be selectable without first selecting J57");
});

test("Z06 package selections default ROY carbon wheels and make package peers consistent", () => {
  for (const rpo of ["PDB", "PDD", "PDF"]) {
    const runtime = z06Runtime();
    const packageChoice = choice(runtime, rpo);
    assert.equal(runtime.disableReasonForChoice(packageChoice), "", `${rpo} should be selectable`);
    runtime.handleChoice(packageChoice);
    runtime.reconcileSelections();

    assert.equal(runtime.state.selected.has(packageChoice.option_id), true, `${rpo} should be selected`);
    assert.equal(autoAddedRpos(runtime).includes("ROY"), true, `${rpo} should default to ROY`);
    assert.doesNotMatch(
      runtime.missingRequirementDetails().map((item) => item.detail).join("\n"),
      /ROY|ROZ|STZ|carbon fiber wheel/i,
      `${rpo} should satisfy its carbon fiber wheel requirement with default ROY`
    );
    for (const [wheelRpo, expectedDelta] of [["ROZ", 1000], ["STZ", 1500]]) {
      const carbonWheel = choice(runtime, wheelRpo);
      assert.equal(runtime.disableReasonForChoice(carbonWheel), "", `${wheelRpo} should be selectable after ${rpo}`);
      assert.equal(runtime.optionPrice(carbonWheel.option_id), expectedDelta, `${wheelRpo} should show the package-base delta when included by ${rpo}`);
    }
    runtime.handleChoice(choice(runtime, "ROZ"));
    runtime.reconcileSelections();
    assert.equal(runtime.state.selected.has(choice(runtime, "ROZ").option_id), true, `${rpo} should allow switching from ROY default to ROZ`);
    assert.equal(autoAddedRpos(runtime).includes("ROY"), false, `${rpo} should release ROY after ROZ is selected`);
    const peerRpos = ["PDB", "PDD", "PDF"].filter((peer) => peer !== rpo);
    for (const peerRpo of peerRpos) {
      assert.equal(runtime.disableReasonForChoice(choice(runtime, peerRpo)), "", `${peerRpo} should stay clickable while ${rpo} is selected`);
    }
  }
});

test("Z06 direct J57 enables carbon fiber wheels and blocks J6A", () => {
  const runtime = z06Runtime();
  runtime.handleChoice(choice(runtime, "J57"));
  runtime.reconcileSelections();

  assert.deepEqual(
    ["ROY", "ROZ", "STZ"].map((rpo) => runtime.disableReasonForChoice(choice(runtime, rpo))),
    ["", "", ""],
    "J57 should make all carbon fiber wheels selectable"
  );
  const j6a = choice(runtime, "J6A");
  assert.notEqual(runtime.disableReasonForChoice(j6a), "", "J57 should make J6A unavailable");
});

test("Z06 engine appearance, exhaust, and convertible PBC workbook rules are honored", () => {
  const coupe = z06Runtime({ bodyStyle: "coupe" });
  assert.equal(coupe.disableReasonForChoice(choice(coupe, "NWI")), "", "NWI should not require standard WUB");

  coupe.handleChoice(choice(coupe, "B6P"));
  coupe.reconcileSelections();
  assert.equal(coupe.optionPrice(choice(coupe, "D3V").option_id), 0, "B6P should zero D3V");
  assert.equal(coupe.optionPrice(choice(coupe, "SL9").option_id), 0, "B6P should zero SL9");

  const convertible = z06Runtime({ bodyStyle: "convertible" });
  const pbc = choice(convertible, "PBC");
  assert.match(convertible.disableReasonForChoice(pbc), /ZZ3/i, "PBC should require ZZ3 on convertible");
  convertible.handleChoice(choice(convertible, "ZZ3"));
  convertible.reconcileSelections();
  assert.equal(convertible.optionPrice(choice(convertible, "SL9").option_id), 0, "ZZ3 should zero SL9");
  assert.equal(convertible.disableReasonForChoice(pbc), "", "ZZ3 should satisfy PBC on convertible");
});

test("Z06 GBA paint incompatibilities and unreleased option visibility come from workbook data", () => {
  const runtime = z06Runtime();
  runtime.handleChoice(choice(runtime, "GBA"));
  runtime.reconcileSelections();

  for (const rpo of ["EFY", "ZYC", "D84", "D86"]) {
    assert.notEqual(runtime.disableReasonForChoice(choice(runtime, rpo)), "", `${rpo} should be unavailable with GBA`);
  }
  assert.equal(maybeChoice(runtime, "V8X"), undefined, "V8X should not appear as an active front-end choice");
  assert.equal(maybeChoice(runtime, "RYQ"), undefined, "RYQ should not appear as an active front-end choice");
});

test("Z06 source selectable=false standard rows are not customer-selectable", () => {
  const runtime = z06Runtime();
  const wub = choice(runtime, "WUB");
  assert.equal(wub.selectable, "False", "test fixture expects WUB to be source non-selectable");
  assert.notEqual(runtime.disableReasonForChoice(wub), "", "source non-selectable standard rows should be display-only");

  const before = selectedRpos(runtime);
  runtime.handleChoice(wub);
  runtime.reconcileSelections();
  assert.deepEqual(selectedRpos(runtime), before, "clicking source non-selectable standard row should not alter selected options");
});
