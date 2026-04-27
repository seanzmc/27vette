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

test("body style choices put coupe before convertible", () => {
  const bodyChoices = data.contextChoices
    .filter((choice) => choice.context_type === "body_style")
    .sort((a, b) => Number(a.display_order) - Number(b.display_order));

  assert.deepEqual(
    JSON.parse(JSON.stringify(bodyChoices.map((choice) => [choice.value, Number(choice.display_order)]))),
    [
      ["coupe", 1],
      ["convertible", 2],
    ]
  );
});

test("body and trim selection do not auto-advance past the current context step", () => {
  const contextHandler = appSource.match(/function handleContextChoice\(choice\) \{[\s\S]*?\n\}/)?.[0] || "";
  assert.doesNotMatch(contextHandler, /state\.activeStep\s*=\s*"trim_level"/);
  assert.doesNotMatch(contextHandler, /state\.activeStep\s*=\s*"paint"/);
});

test("optional single-select sections can be unselected", () => {
  const choiceHandler = appSource.match(/function handleChoice\(choice\) \{[\s\S]*?\n\}/)?.[0] || "";
  assert.match(choiceHandler, /selection_mode\s*===\s*"single_select_opt"/);
  assert.match(choiceHandler, /state\.selected\.has\(choice\.option_id\)/);
  assert.match(choiceHandler, /state\.selected\.delete\(choice\.option_id\)/);
});

test("UQT is selectable only on 1LT and included-only on higher trims", () => {
  const uqtSelectable = data.choices.filter((choice) => choice.rpo === "UQT" && choice.selectable === "True");
  assert.ok(uqtSelectable.length > 0, "UQT should remain selectable for 1LT");
  assert.ok(uqtSelectable.every((choice) => choice.trim_level === "1LT"), "UQT should not be selectable on 2LT/3LT");

  const uqtIncluded = data.standardEquipment.filter((item) => item.rpo === "UQT");
  assert.ok(uqtIncluded.some((item) => item.trim_level === "2LT"));
  assert.ok(uqtIncluded.some((item) => item.trim_level === "3LT"));
});

test("custom stitch choices are removed from the selectable runtime", () => {
  assert.equal(
    data.choices.some((choice) => choice.section_id === "sec_cust_002" && choice.active === "True"),
    false
  );
});

test("auto-added included options render as locked selections without duplicate manual selection", () => {
  assert.match(appSource, /const disabled = Boolean\(disabledReason \|\| autoReason\)/);
  assert.match(appSource, /aria-disabled=\\"true\\" disabled/);
  assert.match(appSource, /if \(autoAdded\.has\(choice\.option_id\)\) return/);
});

test("order export omits the full standard equipment dump", () => {
  const currentOrder = appSource.match(/function currentOrder\(\) \{[\s\S]*?\n\}/)?.[0] || "";
  assert.doesNotMatch(currentOrder, /standard_equipment\s*:/);
  assert.match(currentOrder, /line_items\s*:/);
  assert.match(currentOrder, /auto_added_rpos\s*:/);
});

test("replaceable suspension and exhaust defaults are encoded", () => {
  assert.match(appSource, /for \(const defaultRpo of \["FE1", "NGA", "BC7"\]\)/);
  assert.match(appSource, /selectedOptionByRpo\("Z51"\)/);
  assert.match(appSource, /option\?\.rpo === "FE1" \|\| option\?\.rpo === "FE2"/);
  assert.ok(
    data.rules.some((rule) => rule.source_id === "opt_z51_001" && rule.target_id === "opt_fe3_001" && rule.rule_type === "includes"),
    "Z51 should include FE3"
  );
  assert.ok(data.choices.some((choice) => choice.rpo === "FE4" && choice.status === "available"), "FE4 should be available");
  assert.match(appSource, /selectedOptionByRpo\("NWI"\)/);
  assert.match(appSource, /option\?\.rpo === "NGA"/);
});

test("coupe defaults include BC7 engine appearance", () => {
  assert.match(appSource, /defaultRpo of \["FE1", "NGA", "BC7"\]/);
  assert.match(appSource, /defaultChoice\.body_style === "coupe"/);
});

test("5V7 can satisfy spoiler requirement with either 5ZU or 5ZZ", () => {
  const fiveV7Requires = data.rules
    .filter((rule) => rule.source_id === "opt_5v7_001" && rule.rule_type === "requires")
    .map((rule) => rule.target_id)
    .sort();

  assert.deepEqual(JSON.parse(JSON.stringify(fiveV7Requires)), []);
  assert.match(appSource, /choice\.rpo === "5V7"/);
  assert.match(appSource, /selectedOptionByRpo\("5ZU"\) \|\| selectedOptionByRpo\("5ZZ"\)/);
});

test("5ZU body-color spoiler can satisfy its paint requirement with any allowed body color", () => {
  const fiveZuRequires = data.rules
    .filter((rule) => rule.source_id === "opt_5zu_001" && rule.rule_type === "requires")
    .map((rule) => rule.target_id)
    .sort();

  assert.equal(fiveZuRequires.some((targetId) => ["opt_g8g_001", "opt_gba_001", "opt_gkz_001"].includes(targetId)), false);
  assert.match(appSource, /choice\.rpo === "5ZU"/);
  assert.match(appSource, /selectedOptionByRpo\("G8G"\) \|\| selectedOptionByRpo\("GBA"\) \|\| selectedOptionByRpo\("GKZ"\)/);
});

test("aero exhaust accessories sections use the requested order", () => {
  const sectionNames = data.sections
    .filter((section) => section.step_key === "aero_exhaust_stripes_accessories")
    .sort((a, b) => Number(a.section_display_order) - Number(b.section_display_order))
    .map((section) => section.section_name);

  assert.deepEqual(
    JSON.parse(JSON.stringify(sectionNames)),
    ["Exhaust", "Spoiler", "Stripes", "LPO Exterior", "LPO Wheels", "Wheel Accessory"]
  );
  assert.match(appSource, /section_display_order/);
});

test("step rendering resets scroll to the top after content replacement", () => {
  assert.match(appSource, /scrollTo\(\{ top: 0/);
});

test("interior pricing subtracts the selected seat price", () => {
  assert.match(appSource, /function selectedSeatChoice/);
  assert.match(appSource, /function adjustedInteriorPrice/);
  assert.match(appSource, /Math\.max\(0, Number\(interior\.price \|\| 0\) - Number\(seat\?\.base_price \|\| 0\)\)/);
  assert.match(appSource, /price: adjustedInteriorPrice\(interior\)/);
});

test("D30 is auto-added only and not directly selectable", () => {
  assert.equal(
    data.choices.some((choice) => choice.rpo === "D30" && choice.active === "True"),
    false
  );
  assert.ok(
    data.colorOverrides.some((override) => override.adds_rpo === "opt_d30_001"),
    "D30 should remain available to color override auto-add rules"
  );
});
