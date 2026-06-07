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
  get elements() { return elements; },
  activateModel,
  activateStep,
  activeChoiceRows,
  resetDefaults,
  reconcileSelections,
  handleChoice,
  render,
  currentOrder,
  compactOrder,
  missingRequirementDetails,
  computeAutoAdded,
  optionPrice,
  choiceDisplayPrice,
  lineItems,
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

test("Z06 PDF replaces a prior T0F selection with included T0G", () => {
  const runtime = z06Runtime();

  runtime.handleChoice(choice(runtime, "T0F"));
  runtime.reconcileSelections();
  assert.equal(runtime.state.selected.has(choice(runtime, "T0F").option_id), true, "T0F should be selectable before PDF");

  runtime.handleChoice(choice(runtime, "PDF"));
  runtime.reconcileSelections();

  assert.equal(runtime.state.selected.has(choice(runtime, "PDF").option_id), true, "PDF should be selected");
  assert.equal(runtime.state.selected.has(choice(runtime, "T0F").option_id), false, "PDF should remove the prior T0F selected state");
  assert.equal(autoAddedRpos(runtime).includes("T0G"), true, "PDF should include/default T0G");
  assert.equal(autoAddedRpos(runtime).includes("CFV"), true, "PDF/T0G should include visible-carbon ground effects");
  assert.equal(autoAddedRpos(runtime).includes("CFZ"), false, "PDF should release T0F/CFZ Carbon Flash ground effects");
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

test("Z06 carbon wheel package ROY defaults can switch to ROZ or STZ while aluminum wheels stay disabled", () => {
  const aluminumWheelRpos = ["SOE", "SRK", "ROU", "SOA", "SRN", "SON", "ROX", "SOM", "STX"];

  for (const packageRpo of ["PDB", "PDD", "PDF"]) {
    const runtime = z06Runtime();
    runtime.handleChoice(choice(runtime, packageRpo));
    runtime.reconcileSelections();

    assert.equal(autoAddedRpos(runtime).includes("ROY"), true, `${packageRpo} should default to ROY`);
    assert.equal(runtime.state.selected.has(choice(runtime, "SOE").option_id), false, `${packageRpo} should replace the default aluminum wheel`);
    assert.equal(runtime.disableReasonForChoice(choice(runtime, "ROZ")), "", `${packageRpo} should allow switching the default wheel to ROZ`);
    assert.equal(runtime.disableReasonForChoice(choice(runtime, "STZ")), "", `${packageRpo} should allow switching the default wheel to STZ`);
    for (const aluminumWheelRpo of aluminumWheelRpos) {
      assert.notEqual(
        runtime.disableReasonForChoice(choice(runtime, aluminumWheelRpo)),
        "",
        `${aluminumWheelRpo} should be disabled while ${packageRpo} owns the default ROY carbon wheel`
      );
    }

    runtime.handleChoice(choice(runtime, "ROZ"));
    runtime.reconcileSelections();
    assert.equal(runtime.state.selected.has(choice(runtime, "ROZ").option_id), true, `${packageRpo} should allow ROZ selection`);
    assert.equal(autoAddedRpos(runtime).includes("ROY"), false, `${packageRpo} ROZ selection should suppress the ROY default`);
    assert.doesNotMatch(missingText(runtime), /ROY|ROZ|STZ|carbon fiber wheel/i, `${packageRpo} should remain complete after switching to ROZ`);
    assert.equal(runtime.disableReasonForChoice(choice(runtime, "ROY")), "", `${packageRpo} should allow switching back to ROY`);
    assert.equal(runtime.disableReasonForChoice(choice(runtime, "STZ")), "", `${packageRpo} should allow switching from ROZ to STZ`);
    for (const aluminumWheelRpo of aluminumWheelRpos) {
      assert.notEqual(
        runtime.disableReasonForChoice(choice(runtime, aluminumWheelRpo)),
        "",
        `${aluminumWheelRpo} should stay disabled after ${packageRpo} switches from ROY to ROZ`
      );
    }
  }
});

test("Z06 package cards display their direct package prices", () => {
  for (const [packageRpo, basePrice] of [
    ["PDB", 16000],
    ["PDD", 25495],
    ["PDF", 26495],
  ]) {
    const runtime = z06Runtime();
    const packageChoice = choice(runtime, packageRpo);

    runtime.handleChoice(packageChoice);
    runtime.reconcileSelections();

    assert.equal(runtime.choiceDisplayPrice(packageChoice), basePrice, `${packageRpo} package card should display its direct package price`);
    assert.equal(runtime.optionPrice(packageChoice.option_id), basePrice, `${packageRpo} selected order price should carry the package base`);
  }
});

test("Z06 selecting BCW auto-adds D3V at no additional charge", () => {
  const runtime = z06Runtime();
  const bcw = choice(runtime, "BCW");
  const d3v = choice(runtime, "D3V");

  runtime.handleChoice(bcw);
  runtime.reconcileSelections();

  assert.equal(runtime.state.selected.has(bcw.option_id), true, "BCW should be selected");
  assert.equal(autoAddedRpos(runtime).includes("D3V"), true, "BCW should auto-add D3V");
  assert.equal(runtime.state.selected.has(d3v.option_id), false, "D3V should be locked as auto-added, not user-selected");
  assert.equal(runtime.optionPrice(d3v.option_id), 0, "D3V should be $0 when included by BCW");

  runtime.handleChoice(bcw);
  runtime.reconcileSelections();
  assert.equal(autoAddedRpos(runtime).includes("D3V"), false, "D3V should be released after removing BCW if no other source includes it");
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

test("Z06 Z07 locks included J57 and replaces the J56 default brake", () => {
  const runtime = z06Runtime();
  const j56 = choice(runtime, "J56");
  const j57 = choice(runtime, "J57");
  const z07 = choice(runtime, "Z07");

  assert.equal(runtime.state.selected.has(j56.option_id), true, "J56 should seed as the default brake before Z07");

  runtime.handleChoice(z07);
  runtime.reconcileSelections();

  assert.equal(runtime.state.selected.has(z07.option_id), true, "Z07 should be selected");
  assert.equal(autoAddedRpos(runtime).includes("J57"), true, "Z07 should own J57 as included equipment");
  assert.equal(runtime.optionPrice(j57.option_id), 0, "J57 should be $0 when included by Z07");
  assert.equal(runtime.state.selected.has(j56.option_id), false, "J56 should not remain the selected brake while Z07 includes J57");

  runtime.handleChoice(j57);
  runtime.reconcileSelections();

  assert.equal(autoAddedRpos(runtime).includes("J57"), true, "J57 should stay included while Z07 is selected");
  assert.equal(runtime.state.selected.has(j57.option_id), false, "J57 should not remain a user-selected removable item under Z07");
});

test("Z06 hidden source rows do not render as selectable option-step cards", () => {
  const runtime = z06Runtime();
  runtime.activateStep("interior_trim");
  runtime.render();
  const interiorTrimHtml = runtime.elements.get("#stepContent").innerHTML;
  assert.doesNotMatch(interiorTrimHtml, /data-option=\"opt_n26_001\"|>N26</, "N26 should not render as a selectable option card");

  runtime.activateStep("custom_stitch");
  runtime.render();
  const stitchHtml = runtime.elements.get("#stepContent").innerHTML;
  assert.doesNotMatch(stitchHtml, /data-option=\"opt_36s_001\"|>36S</, "36S should not render as a selectable option card");
  assert.doesNotMatch(stitchHtml, /data-option=\"opt_37s_001\"|>37S</, "37S should not render as a selectable option card");
  assert.doesNotMatch(stitchHtml, /data-option=\"opt_38s_001\"|>38S</, "38S should not render as a selectable option card");
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

test("Z06 carbon fiber wheel packages satisfy the unified Wheels requirement", () => {
  for (const pkg of ["PDB", "PDD", "PDF"]) {
    const runtime = z06Runtime();
    runtime.handleChoice(choice(runtime, pkg));
    runtime.reconcileSelections();
    const missingLabels = runtime.missingRequirementDetails().map((item) => item.label);
    assert.equal(
      missingLabels.includes("Wheels"),
      false,
      `${pkg} auto-adds a carbon fiber wheel, so the Wheels requirement must be satisfied (no stuck required selection)`,
    );
  }
});

test("Z06 carbon fiber wheels live in the unified Wheels section and step", () => {
  const runtime = z06Runtime();
  for (const rpo of ["ROY", "ROZ", "STZ"]) {
    const cfWheel = choice(runtime, rpo);
    assert.equal(cfWheel.section_id, "sec_whee_002", `${rpo} should be in the unified Wheels section`);
    assert.equal(cfWheel.step_key, "wheels", `${rpo} should render in the Wheels & Brake Calipers step`);
  }

  const direct = z06Runtime();
  direct.handleChoice(choice(direct, "ROY"));
  direct.reconcileSelections();
  assert.equal(
    direct.missingRequirementDetails().map((item) => item.label).includes("Wheels"),
    false,
    "Selecting a carbon fiber wheel directly should satisfy the Wheels requirement",
  );
});

test("Z06 carbon fiber wheel and brake packages render in the Wheels & Brake Calipers step", () => {
  const runtime = z06Runtime();
  for (const rpo of ["PDB", "PDD", "PDF"]) {
    assert.equal(
      choice(runtime, rpo).step_key,
      "wheels",
      `${rpo} package should render in the wheels/calipers step so the bundled performance choice is pre-set`,
    );
  }
});
