import assert from "node:assert/strict";
import fs from "node:fs";
import test from "node:test";
import vm from "node:vm";

function loadData() {
  const context = { window: {} };
  vm.runInNewContext(fs.readFileSync("form-app/data.js", "utf8"), context);
  return context.window.STINGRAY_FORM_DATA;
}

const data = loadData();
const appSource = fs.readFileSync("form-app/app.js", "utf8");

function uniqueChoicesByRpo(rpo) {
  return [...new Map(data.choices.filter((choice) => choice.rpo === rpo).map((choice) => [choice.option_id, choice])).values()];
}

test("runtime steps include customer info and omit interior styling", () => {
  const keys = data.steps.map((step) => step.step_key);
  assert.ok(keys.includes("customer_info"));
  assert.equal(keys.includes("interior_style"), false);
  assert.ok(keys.indexOf("customer_info") > keys.indexOf("delivery"));
  assert.ok(keys.indexOf("customer_info") < keys.indexOf("summary"));
});

test("selection modes have friendly display labels", () => {
  for (const section of data.sections) {
    if (!section.selection_mode) continue;
    assert.ok(section.selection_mode_label, `${section.section_id} is missing a display label`);
    assert.equal(section.selection_mode_label.includes("_"), false, section.selection_mode_label);
  }
  for (const choice of data.choices) {
    if (!choice.selection_mode) continue;
    assert.ok(choice.selection_mode_label, `${choice.choice_id} is missing a display label`);
  }
});

test("engine cover variants are consolidated with B6P price overrides", () => {
  for (const rpo of ["BC4", "BCP", "BCS"]) {
    const choices = uniqueChoicesByRpo(rpo);
    assert.equal(choices.length, 1, `${rpo} should be one option id`);
    assert.equal(Number(choices[0].base_price), 695, `${rpo} base price`);
    const override = data.priceRules.find(
      (rule) => rule.condition_option_id === "opt_b6p_001" && rule.target_option_id === choices[0].option_id
    );
    assert.ok(override, `${rpo} needs a B6P price override`);
    assert.equal(Number(override.price_value), 595, `${rpo} B6P override price`);
  }
});

test("BC7, N26/TU7, and ZF1/T0A visibility follow the QA contract", () => {
  assert.equal(uniqueChoicesByRpo("BC7").length, 1, "BC7 should be one body-style-neutral option id");

  for (const rpo of ["N26", "TU7"]) {
    assert.equal(
      data.choices.some((choice) => choice.rpo === rpo && choice.step_key === "interior_trim"),
      false,
      `${rpo} should not appear in Interior Trim`
    );
  }

  assert.equal(data.choices.some((choice) => choice.rpo === "ZF1" && choice.active === "True"), false, "ZF1 should not render");
  const t0a = uniqueChoicesByRpo("T0A")[0];
  assert.ok(t0a, "T0A should exist");
  assert.equal(t0a.selectable, "True");
  assert.equal(t0a.step_key, "aero_exhaust_stripes_accessories");
});

test("app runtime has the requested navigation and filtering hooks", () => {
  assert.match(appSource, /function shouldHideChoice/);
  assert.match(appSource, /data-next-step/);
  assert.match(appSource, /renderTrimStandardEquipment/);
  assert.match(appSource, /customer_info/);
});
