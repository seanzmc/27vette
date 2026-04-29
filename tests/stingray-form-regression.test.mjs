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
const htmlSource = fs.readFileSync("form-app/index.html", "utf8");
const interiorReferenceSource = fs.readFileSync("architectureAudit/stingray_interiors_refactor.csv", "utf8");

function parseCsv(source) {
  const rows = [];
  let row = [];
  let field = "";
  let inQuotes = false;
  for (let index = 0; index < source.length; index++) {
    const char = source[index];
    const next = source[index + 1];
    if (char === '"' && inQuotes && next === '"') {
      field += '"';
      index++;
    } else if (char === '"') {
      inQuotes = !inQuotes;
    } else if (char === "," && !inQuotes) {
      row.push(field);
      field = "";
    } else if ((char === "\n" || char === "\r") && !inQuotes) {
      if (char === "\r" && next === "\n") index++;
      row.push(field);
      if (row.some((value) => value !== "")) rows.push(row);
      row = [];
      field = "";
    } else {
      field += char;
    }
  }
  if (field || row.length) {
    row.push(field);
    rows.push(row);
  }
  const [headers, ...records] = rows;
  return records.map((record) => Object.fromEntries(headers.map((header, index) => [header, record[index] || ""])));
}

const interiorReferenceRows = parseCsv(interiorReferenceSource);
const interiorReferenceFinalRows = interiorReferenceRows.filter((row) => row.interior_id);
const interiorReferenceIds = new Set(interiorReferenceFinalRows.map((row) => row.interior_id));
const activeInteriors = data.interiors.filter((interior) => interior.active_for_stingray === true);

function makeElement() {
  return {
    textContent: "",
    innerHTML: "",
    dataset: {},
    addEventListener() {},
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
  };
}

function loadRuntime() {
  const context = {
    window: {
      STINGRAY_FORM_DATA: data,
      scrollX: 0,
      scrollY: 0,
      scrollTo() {},
    },
    document: {
      querySelector() {
        return makeElement();
      },
      createElement() {
        return makeElement();
      },
    },
    Intl,
    Number,
    Set,
    Map,
    Boolean,
    Object,
    String,
    URL: {
      createObjectURL() {
        return "";
      },
      revokeObjectURL() {},
    },
    Blob,
  };
  const source = appSource.replace(
    /\ninit\(\);\s*$/,
    `
window.__testApi = {
  state,
  activeChoiceRows,
  resetDefaults,
  reconcileSelections,
  handleChoice,
  computeAutoAdded,
  lineItems,
  currentOrder,
  optionPrice,
};
`
  );
  vm.runInNewContext(source, context);
  return context.window.__testApi;
}

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

test("engine cover variants are consolidated with scoped B6P and ZZ3 price overrides", () => {
  for (const rpo of ["BC4", "BCP", "BCS"]) {
    const choices = uniqueChoicesByRpo(rpo);
    assert.equal(choices.length, 1, `${rpo} should be one option id`);
    assert.equal(Number(choices[0].base_price), 695, `${rpo} base price`);
    const b6pOverride = data.priceRules.find(
      (rule) => rule.condition_option_id === "opt_b6p_001" && rule.target_option_id === choices[0].option_id
    );
    const zz3Override = data.priceRules.find(
      (rule) => rule.condition_option_id === "opt_zz3_001" && rule.target_option_id === choices[0].option_id
    );
    assert.ok(b6pOverride, `${rpo} needs a coupe B6P price override`);
    assert.equal(b6pOverride.body_style_scope, "coupe", `${rpo} B6P override body scope`);
    assert.equal(Number(b6pOverride.price_value), 595, `${rpo} coupe B6P override price`);
    assert.ok(zz3Override, `${rpo} needs a convertible ZZ3 price override`);
    assert.equal(zz3Override.body_style_scope, "convertible", `${rpo} ZZ3 override body scope`);
    assert.equal(Number(zz3Override.price_value), 595, `${rpo} convertible ZZ3 override price`);
  }
});

test("engine cover pricing stays base 695 with scoped coupe B6P and convertible ZZ3 595", () => {
  for (const rpo of ["BC4", "BCP", "BCS"]) {
    const optionId = uniqueChoicesByRpo(rpo)[0].option_id;

    const baseCoupeRuntime = loadRuntime();
    baseCoupeRuntime.state.bodyStyle = "coupe";
    baseCoupeRuntime.state.trimLevel = "1LT";
    assert.equal(baseCoupeRuntime.optionPrice(optionId), 695, `${rpo} base coupe price`);

    const b6pCoupeRuntime = loadRuntime();
    b6pCoupeRuntime.state.bodyStyle = "coupe";
    b6pCoupeRuntime.state.trimLevel = "1LT";
    b6pCoupeRuntime.state.selected.add("opt_b6p_001");
    assert.equal(b6pCoupeRuntime.optionPrice(optionId), 595, `${rpo} coupe B6P price`);

    const convertibleRuntime = loadRuntime();
    convertibleRuntime.state.bodyStyle = "convertible";
    convertibleRuntime.state.trimLevel = "1LT";
    convertibleRuntime.state.selected.add("opt_zz3_001");
    assert.equal(convertibleRuntime.optionPrice(optionId), 595, `${rpo} convertible ZZ3 price`);
  }
});

test("LS6 engine covers are treated as an exclusive selection group", () => {
  assert.ok(Array.isArray(data.exclusiveGroups), "exclusiveGroups should be generated");
  const group = data.exclusiveGroups.find((item) => item.group_id === "grp_ls6_engine_covers");
  assert.ok(group, "LS6 engine covers need a generated exclusive group");
  assert.deepEqual(
    JSON.parse(JSON.stringify(group.option_ids)),
    ["opt_bc7_001", "opt_bcp_001", "opt_bcs_001", "opt_bc4_001"]
  );
  assert.equal(group.selection_mode, "single_within_group");
  assert.match(appSource, /const exclusiveGroupByOption = new Map\(\)/);
  assert.match(appSource, /function optionExclusiveGroup\(optionId\)/);
  assert.match(appSource, /function removeOtherExclusiveGroupOptions\(optionId\)/);
  assert.match(appSource, /removeOtherExclusiveGroupOptions\(choice\.option_id\)/);
  assert.doesNotMatch(appSource, /LS6_ENGINE_COVER_OPTION_IDS/);
  assert.doesNotMatch(appSource, /removeOtherLs6EngineCovers/);
});

test("spoilers are treated as an exclusive selection group", () => {
  assert.ok(Array.isArray(data.exclusiveGroups), "exclusiveGroups should be generated");
  const group = data.exclusiveGroups.find((item) => item.group_id === "grp_spoiler_high_wing");
  assert.ok(group, "spoilers need a generated exclusive group");
  assert.deepEqual(
    JSON.parse(JSON.stringify(group.option_ids)),
    ["opt_t0a_001", "opt_tvs_001", "opt_5zz_001", "opt_5zu_001"]
  );
  assert.equal(group.selection_mode, "single_within_group");
});

test("spoiler exclusive group removes other selected spoiler options", () => {
  const spoilerIds = ["opt_t0a_001", "opt_tvs_001", "opt_5zz_001", "opt_5zu_001"];
  for (const targetId of spoilerIds) {
    const runtime = loadRuntime();
    runtime.state.bodyStyle = "coupe";
    runtime.state.trimLevel = "1LT";
    runtime.state.selected.add("opt_z51_001");
    runtime.state.userSelected.add("opt_z51_001");
    runtime.state.selected.add("opt_gba_001");
    runtime.state.userSelected.add("opt_gba_001");
    for (const id of spoilerIds.filter((item) => item !== targetId)) {
      runtime.state.selected.add(id);
      runtime.state.userSelected.add(id);
    }

    const targetChoice = runtime.activeChoiceRows().find((choice) => choice.option_id === targetId);
    assert.ok(targetChoice, `${targetId} should exist for the current variant`);
    runtime.handleChoice(targetChoice);

    assert.equal(runtime.state.selected.has(targetId), true, `${targetId} should be selected`);
    assert.equal(runtime.state.userSelected.has(targetId), true, `${targetId} should be user-selected`);
    for (const peerId of spoilerIds.filter((item) => item !== targetId)) {
      assert.equal(runtime.state.selected.has(peerId), false, `${peerId} should be removed from selected`);
      assert.equal(runtime.state.userSelected.has(peerId), false, `${peerId} should be removed from userSelected`);
    }
  }
});

test("exclusive group selection replaces ZZ3 default BC7 engine cover", () => {
  const runtime = loadRuntime();
  runtime.state.bodyStyle = "convertible";
  runtime.state.trimLevel = "1LT";
  runtime.resetDefaults();
  runtime.reconcileSelections();

  const zz3 = runtime.activeChoiceRows().find((choice) => choice.rpo === "ZZ3");
  const bcp = runtime.activeChoiceRows().find((choice) => choice.rpo === "BCP");
  assert.ok(zz3, "ZZ3 should exist for convertible builds");
  assert.ok(bcp, "BCP should exist for convertible builds");

  runtime.handleChoice(zz3);
  assert.equal(runtime.computeAutoAdded().has("opt_bc7_001"), true, "ZZ3 should default BC7 before replacement");

  runtime.handleChoice(bcp);

  const selectedIds = [...runtime.state.selected];
  const userSelectedIds = [...runtime.state.userSelected];
  const lineItemRpos = runtime.lineItems().map((item) => item.rpo);
  assert.equal(selectedIds.includes("opt_bcp_001"), true, "new engine cover should remain selected");
  assert.equal(selectedIds.includes("opt_bc7_001"), false, "default BC7 should be removed from selected state");
  assert.equal(userSelectedIds.includes("opt_bc7_001"), false, "removed group member should not remain user-selected");
  assert.equal(runtime.computeAutoAdded().has("opt_bc7_001"), false, "BC7 should not remain auto-added after group replacement");
  assert.equal(lineItemRpos.includes("BCP"), true, "new engine cover should appear in line items");
  assert.equal(lineItemRpos.includes("BC7"), false, "replaced default BC7 should not appear in line items");
});

test("option selections preserve the current viewport instead of resetting to the page top", () => {
  assert.match(appSource, /function captureScrollPosition\(\)/);
  assert.match(appSource, /function restoreScrollPosition\(position\)/);
  assert.match(appSource, /render\(\{ preserveScroll: true \}\)/);
  assert.match(appSource, /renderStepContent\(\{ resetScroll = false \} = \{\}\)/);
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
  assert.match(choiceHandler, /deleteSelectedOption\(choice\.option_id\)/);
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
  assert.match(currentOrder, /selected_options\s*:/);
  assert.match(currentOrder, /auto_added_options\s*:/);
});

test("current order exposes the stable Formidable-ready top-level contract", () => {
  const runtime = loadRuntime();
  runtime.resetDefaults();
  runtime.reconcileSelections();

  const order = runtime.currentOrder();
  for (const key of [
    "customer",
    "vehicle",
    "pricing",
    "sections",
    "selected_options",
    "auto_added_options",
    "selected_interior",
    "standard_equipment_summary",
    "metadata",
  ]) {
    assert.ok(Object.hasOwn(order, key), `currentOrder should include ${key}`);
  }

  assert.deepEqual(Object.keys(order.customer), ["name", "address", "email", "phone", "comments"]);
  assert.deepEqual(Object.keys(order.vehicle), [
    "model_year",
    "model",
    "body_style",
    "trim_level",
    "variant_id",
    "display_name",
    "base_price",
  ]);
  assert.deepEqual(Object.keys(order.pricing), ["base_price", "selected_options_total", "total_msrp"]);
  assert.equal(order.metadata.dataset.name, data.dataset.name);
});

test("current order option lines are complete, separated, and omit standard equipment", () => {
  const runtime = loadRuntime();
  runtime.state.bodyStyle = "coupe";
  runtime.state.trimLevel = "1LT";
  runtime.resetDefaults();
  runtime.reconcileSelections();

  const z51 = runtime.activeChoiceRows().find((choice) => choice.option_id === "opt_z51_001");
  const paint = runtime.activeChoiceRows().find((choice) => choice.option_id === "opt_gba_001");
  assert.ok(z51, "Z51 should exist for the current variant");
  assert.ok(paint, "Black paint should exist for the current variant");
  runtime.handleChoice(paint);
  runtime.handleChoice(z51);

  const order = runtime.currentOrder();
  const allLines = [
    ...order.selected_options,
    ...order.auto_added_options,
    ...(order.selected_interior?.rpo ? [order.selected_interior] : []),
  ];
  assert.ok(allLines.length > 0, "order should include option lines");
  for (const line of allLines) {
    for (const key of ["rpo", "label", "description", "price", "type", "section_key", "section_label", "category_name", "step_key"]) {
      assert.ok(Object.hasOwn(line, key), `${line.rpo || line.label} should include ${key}`);
    }
  }

  assert.equal(order.selected_options.some((item) => item.type === "auto_added"), false);
  assert.equal(order.auto_added_options.every((item) => item.type === "auto_added"), true);
  assert.equal(order.auto_added_options.some((item) => item.rpo === "FE3"), true, "Z51 should keep FE3 clearly auto-added");
  assert.equal(order.selected_options.some((item) => item.step_key === "standard_equipment"), false);
  assert.equal(order.standard_equipment_summary.count > 0, true);
  assert.equal(Array.isArray(order.standard_equipment_summary.items), false, "summary should not dump standard equipment rows");
});

test("current order section recap has predictable labels, one interior, and correct totals", () => {
  const runtime = loadRuntime();
  runtime.state.bodyStyle = "coupe";
  runtime.state.trimLevel = "1LT";
  runtime.resetDefaults();
  runtime.reconcileSelections();

  const paint = runtime.activeChoiceRows().find((choice) => choice.option_id === "opt_gba_001");
  assert.ok(paint, "Black paint should exist for the current variant");
  runtime.handleChoice(paint);
  runtime.state.selectedInterior = "1LT_AQ9_HTA";

  const order = runtime.currentOrder();
  const sectionLabels = order.sections.map((section) => section.section_label);
  assert.deepEqual(JSON.parse(JSON.stringify(sectionLabels)), [
    "Vehicle",
    "Exterior Paint",
    "Exterior Appearance",
    "Wheels & Brakes",
    "Performance & Mechanical",
    "Aero, Exhaust, Stripes & Accessories",
    "Seats & Interior",
    "Pricing Summary",
    "Customer Information",
  ]);

  const recapInteriorLines = order.sections.flatMap((section) => section.items).filter((item) => item.type === "selected_interior");
  assert.equal(recapInteriorLines.length, 1, "selected interior should appear once in section recap");
  assert.equal(order.selected_interior.type, "selected_interior");
  assert.equal(order.selected_interior.section_label, "Seats & Interior");

  const selectedTotal = order.selected_options.reduce((sum, item) => sum + Number(item.price || 0), 0);
  const autoTotal = order.auto_added_options.reduce((sum, item) => sum + Number(item.price || 0), 0);
  const interiorTotal = Number(order.selected_interior?.price || 0);
  assert.equal(order.pricing.selected_options_total, selectedTotal + autoTotal + interiorTotal);
  assert.equal(order.pricing.total_msrp, order.pricing.base_price + order.pricing.selected_options_total);
});

test("replaceable suspension and exhaust defaults are encoded", () => {
  assert.match(appSource, /for \(const defaultRpo of \["FE1", "NGA", "BC7"\]\)/);
  assert.match(appSource, /selectedOptionByRpo\("Z51"\)/);
  assert.match(appSource, /deleteSelectedRpo\("FE1"\)/);
  assert.match(appSource, /deleteSelectedRpo\("FE2"\)/);
  assert.ok(
    data.rules.some((rule) => rule.source_id === "opt_z51_001" && rule.target_id === "opt_fe3_001" && rule.rule_type === "includes"),
    "Z51 should include FE3"
  );
  assert.ok(
    data.choices.some(
      (choice) =>
        choice.rpo === "FE3" &&
        choice.section_id === "sec_susp_001" &&
        choice.step_key === "packages_performance" &&
        choice.selectable === "False" &&
        choice.active === "True"
    ),
    "FE3 should render as an auto-only suspension tile"
  );
  assert.equal(data.choices.some((choice) => choice.rpo === "FE3" && choice.selectable === "True"), false, "FE3 should not be manually selectable");
  assert.ok(data.choices.some((choice) => choice.rpo === "FE4" && choice.status === "available"), "FE4 should be available");
  assert.ok(
    data.rules.some((rule) => rule.source_id === "opt_fe4_001" && rule.target_id === "opt_z51_001" && rule.rule_type === "requires"),
    "FE4 should require Z51"
  );
  assert.match(appSource, /selectedOptionByRpo\("NWI"\)/);
  assert.match(appSource, /deleteSelectedRpo\("NGA"\)/);
  assert.match(appSource, /addDefaultRpo\("NGA"\)/);
});

test("FE1 default selection prefers the visible suspension tile", () => {
  const fe1Rows = data.choices.filter((choice) => choice.variant_id === "1lt_c07" && choice.rpo === "FE1");
  assert.ok(
    fe1Rows.some((choice) => choice.option_id === "opt_fe1_001" && choice.section_id === "sec_susp_001" && choice.selectable === "True"),
    "FE1 should have a visible selectable suspension choice"
  );
  assert.ok(
    fe1Rows.some((choice) => choice.option_id === "opt_fe1_002" && choice.step_key === "standard_equipment"),
    "FE1 also has a standard-equipment duplicate, which must not win default lookup"
  );

  const helper = appSource.match(/function defaultChoiceForRpo\(rpo\) \{[\s\S]*?\n\}/)?.[0] || "";
  assert.match(helper, /choice\.selectable === "True"/);
  assert.match(helper, /choice\.step_key !== "standard_equipment"/);
});

test("initial selected FE1 state is de-duped to the visible suspension choice", () => {
  const runtime = loadRuntime();
  runtime.state.bodyStyle = "coupe";
  runtime.state.trimLevel = "1LT";
  runtime.resetDefaults();
  runtime.reconcileSelections();

  const selectedFe1Choices = [...runtime.state.selected]
    .map((id) => data.choices.find((choice) => choice.option_id === id))
    .filter((choice) => choice?.rpo === "FE1");
  assert.equal(selectedFe1Choices.length, 1, "initial selected state should contain one FE1 row");
  assert.equal(selectedFe1Choices[0].option_id, "opt_fe1_001", "FE1 should retain the visible suspension tile");
  assert.equal(selectedFe1Choices[0].step_key, "packages_performance");
  assert.equal(selectedFe1Choices[0].selectable, "True");

  const fe1LineItems = runtime.lineItems().filter((item) => item.rpo === "FE1");
  assert.equal(fe1LineItems.length, 1, "Selected RPOs should render one FE1 line item");

  const z51 = runtime.activeChoiceRows().find((choice) => choice.option_id === "opt_z51_001");
  assert.ok(z51, "Z51 should exist for the current variant");
  runtime.handleChoice(z51);

  const selectedRpos = [...runtime.state.selected].map((id) => data.choices.find((choice) => choice.option_id === id)?.rpo);
  assert.equal(selectedRpos.includes("FE1"), false, "Z51 should remove FE1");
  assert.equal(selectedRpos.includes("FE2"), false, "Z51 should remove FE2");
  assert.equal(runtime.computeAutoAdded().has("opt_fe3_001"), true, "Z51 should still include FE3");
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
  assert.ok(Array.isArray(data.ruleGroups), "ruleGroups should be generated");
  const fiveV7Group = data.ruleGroups.find((group) => group.group_id === "grp_5v7_spoiler_requirement");

  assert.deepEqual(JSON.parse(JSON.stringify(fiveV7Requires)), []);
  assert.ok(fiveV7Group, "5V7 should use a generated grouped requirement");
  assert.equal(fiveV7Group.group_type, "requires_any");
  assert.deepEqual(JSON.parse(JSON.stringify(fiveV7Group.target_ids)), ["opt_5zu_001", "opt_5zz_001"]);
  assert.match(fiveV7Group.disabled_reason, /Requires 5ZU Body-Color High Wing Spoiler or 5ZZ Carbon Flash High Wing Spoiler/);
  assert.match(appSource, /const ruleGroupsBySource = new Map\(\)/);
  assert.match(appSource, /function ruleGroupAppliesToCurrentVariant\(group\)/);
  assert.match(appSource, /function requiresAnyReason\(choice, selectedIds\)/);
  assert.match(appSource, /const selectedIds = selectedContextIds\(\)/);
  assert.match(appSource, /requiresAnyReason\(choice, selectedIds\)/);
  assert.doesNotMatch(appSource, /choice\.rpo === "5V7"/);
  assert.doesNotMatch(appSource, /selectedOptionByRpo\("5ZU"\) \|\| selectedOptionByRpo\("5ZZ"\)/);
});

test("5ZU body-color spoiler can satisfy its paint requirement with any allowed body color", () => {
  const fiveZuRequires = data.rules
    .filter((rule) => rule.source_id === "opt_5zu_001" && rule.rule_type === "requires")
    .map((rule) => rule.target_id)
    .sort();
  assert.ok(Array.isArray(data.ruleGroups), "ruleGroups should be generated");
  const fiveZuGroup = data.ruleGroups.find((group) => group.group_id === "grp_5zu_paint_requirement");

  assert.equal(fiveZuRequires.some((targetId) => ["opt_g8g_001", "opt_gba_001", "opt_gkz_001"].includes(targetId)), false);
  assert.ok(fiveZuGroup, "5ZU should use a generated grouped requirement");
  assert.equal(fiveZuGroup.group_type, "requires_any");
  assert.deepEqual(JSON.parse(JSON.stringify(fiveZuGroup.target_ids)), ["opt_g8g_001", "opt_gba_001", "opt_gkz_001"]);
  assert.match(fiveZuGroup.disabled_reason, /Requires Arctic White, Black, or Torch Red exterior paint/);
  assert.doesNotMatch(appSource, /choice\.rpo === "5ZU"/);
  assert.doesNotMatch(appSource, /selectedOptionByRpo\("G8G"\) \|\| selectedOptionByRpo\("GBA"\) \|\| selectedOptionByRpo\("GKZ"\)/);
});

test("aero exhaust accessories sections use the requested order", () => {
  const sectionNames = data.sections
    .filter((section) => section.step_key === "aero_exhaust_stripes_accessories")
    .sort((a, b) => Number(a.section_display_order) - Number(b.section_display_order))
    .map((section) => section.section_name);

  assert.deepEqual(
    JSON.parse(JSON.stringify(sectionNames)),
    ["Exhaust", "Spoiler", "Stripes", "LPO Exterior", "LPO Wheels"]
  );
  assert.match(appSource, /section_display_order/);
});

test("exterior appearance, engine appearance, and wheel sections use QA-4 ordering", () => {
  const exteriorSections = data.sections
    .filter((section) => section.step_key === "exterior_appearance")
    .sort((a, b) => Number(a.section_display_order) - Number(b.section_display_order))
    .map((section) => section.section_name)
    .slice(0, 4);
  assert.deepEqual(JSON.parse(JSON.stringify(exteriorSections)), ["Roof", "Exterior Accents", "Badges", "Engine Appearance"]);

  const engineOrder = data.choices
    .filter((choice) => choice.section_id === "sec_engi_001" && choice.variant_id === "1lt_c07" && choice.active === "True")
    .sort((a, b) => Number(a.display_order) - Number(b.display_order))
    .map((choice) => choice.rpo);
  assert.deepEqual(JSON.parse(JSON.stringify(engineOrder)), ["BC7", "BCP", "BCS", "BC4", "B6P", "ZZ3", "D3V", "SL9", "SLK", "SLN", "VUP"]);

  const wheelSections = data.sections
    .filter((section) => section.step_key === "wheels")
    .sort((a, b) => Number(a.section_display_order) - Number(b.section_display_order))
    .map((section) => section.section_name);
  assert.deepEqual(JSON.parse(JSON.stringify(wheelSections)), ["Wheels", "Caliper Color", "Wheel Accessory"]);
  assert.equal(data.steps.some((step) => step.step_key === "calipers"), false);
});

test("BC7 has a convertible-only ZZ3 requirement", () => {
  const bc7Rule = data.rules.find(
    (rule) => rule.source_id === "opt_bc7_001" && rule.target_id === "opt_zz3_001" && rule.rule_type === "requires"
  );
  assert.ok(bc7Rule, "BC7 should have a ZZ3 requirement rule");
  assert.equal(bc7Rule.body_style_scope, "convertible");
  assert.match(bc7Rule.disabled_reason, /Requires ZZ3 Convertible Engine Appearance Package/);
});

test("spoiler replacement rules preserve ZYC and replace T0A without blocking TVS/5ZZ/5ZU", () => {
  const spoilerSection = data.sections.find((section) => section.section_id === "sec_spoi_001");
  assert.equal(spoilerSection.selection_mode, "multi_select_opt");
  for (const sourceId of ["opt_tvs_001", "opt_5zz_001", "opt_5zu_001"]) {
    const rule = data.rules.find((item) => item.source_id === sourceId && item.target_id === "opt_t0a_001");
    assert.ok(rule, `${sourceId} should remove T0A`);
    assert.equal(rule.runtime_action, "replace");
    assert.match(rule.disabled_reason, /Removes T0A when Z51 is selected/);
  }
  assert.ok(data.rules.some((rule) => rule.source_id === "opt_zyc_001" && rule.target_id === "opt_gba_001"));
  assert.equal(data.rules.some((rule) => rule.source_id === "opt_zyc_001" && ["opt_tvs_001", "opt_5zz_001", "opt_5zu_001"].includes(rule.target_id)), false);
  assert.match(appSource, /if \(choice\.rpo === "GBA"\) deleteSelectedRpo\("ZYC"\)/);
});

test("step rendering resets scroll to the top after content replacement", () => {
  assert.match(appSource, /function resetStepScroll/);
  assert.match(appSource, /closest\("\.choice-panel"\)\?\.scrollTo\(\{ top: 0, left: 0 \}\)/);
  assert.match(appSource, /window\.scrollTo\(\{ top: 0, left: 0 \}\)/);
});

test("interior pricing subtracts the selected seat price", () => {
  assert.match(appSource, /function selectedSeatChoice/);
  assert.match(appSource, /function adjustedInteriorPrice/);
  assert.match(appSource, /Math\.max\(0, Number\(interior\.price \|\| 0\) - Number\(seat\?\.base_price \|\| 0\)\)/);
  assert.match(appSource, /price: adjustedInteriorPrice\(interior\)/);
});

test("interior reference maps every final CSV id and active Stingray interior", () => {
  for (const row of interiorReferenceFinalRows) {
    assert.ok(data.interiors.some((interior) => interior.interior_id === row.interior_id), `${row.interior_id} should map to generated interiors`);
  }
  for (const interior of activeInteriors) {
    assert.ok(
      interiorReferenceIds.has(interior.interior_id) || interior.interior_color_family === "Other Interior Choices",
      `${interior.interior_id} should be represented by the CSV hierarchy or explicit fallback group`
    );
  }
});

test("Grand Sport EL9 interiors are inactive for Stingray and H8T is in the AE4 Santorini hierarchy", () => {
  for (const interiorId of ["3LT_AE4_EL9", "3LT_AH2_EL9"]) {
    assert.equal(
      data.interiors.some((interior) => interior.interior_id === interiorId && interior.active_for_stingray === true),
      false,
      `${interiorId} should not be active for Stingray`
    );
  }

  const h8tReference = interiorReferenceFinalRows.find((row) => row.interior_id === "3LT_AE4_H8T");
  assert.ok(h8tReference, "3LT_AE4_H8T should be represented in the reference CSV");
  const h8tInterior = data.interiors.find((interior) => interior.interior_id === "3LT_AE4_H8T");
  assert.equal(h8tInterior?.interior_trim_level, "3LT");
  assert.equal(h8tInterior?.interior_seat_label, "AE4 Competition Seats");
  assert.equal(h8tInterior?.interior_color_family, "Santorini Blue");
});

test("active interiors have stable CSV-derived grouping fields", () => {
  const requiredFields = [
    "interior_trim_level",
    "interior_seat_code",
    "interior_seat_label",
    "interior_color_family",
    "interior_material_family",
    "interior_variant_label",
    "interior_group_display_order",
    "interior_material_display_order",
    "interior_choice_display_order",
    "interior_hierarchy_levels",
    "interior_hierarchy_path",
    "interior_parent_group_label",
    "interior_leaf_label",
    "interior_reference_order",
  ];
  for (const interior of activeInteriors) {
    for (const field of requiredFields) {
      assert.notEqual(interior[field], undefined, `${interior.interior_id} is missing ${field}`);
      assert.notEqual(interior[field], "", `${interior.interior_id} has blank ${field}`);
    }
  }
});

test("interior grouping preserves required 1LT, 2LT, and 3LT examples", () => {
  const byId = new Map(activeInteriors.map((interior) => [interior.interior_id, interior]));

  assert.deepEqual(
    JSON.parse(
      JSON.stringify(
        activeInteriors
          .filter((interior) => interior.trim_level === "1LT" && interior.seat_code === "AQ9")
          .map((interior) => interior.interior_code)
          .sort()
      )
    ),
    ["HTA", "HUP", "HUQ"]
  );
  assert.equal(byId.get("1LT_AE4_HTJ_N26")?.interior_color_family, "HTJ Jet Black");

  assert.equal(byId.get("2LT_AH2_HTM")?.interior_color_family, "Jet Black");
  assert.match(byId.get("2LT_AH2_HTM")?.interior_material_family || "", /Napa leather/i);
  assert.match(byId.get("2LT_AH2_HTP_N26")?.interior_material_family || "", /Sueded microfiber/i);
  assert.equal(byId.get("2LT_AE4_HTN")?.interior_color_family, "Natural");

  for (const interiorId of [
    "3LT_AH2_HNK",
    "3LT_AH2_H8T",
    "3LT_AH2_HUW",
    "3LT_AH2_EJH",
    "3LT_AH2_HUC",
    "3LT_AH2_HVZ",
    "3LT_R6X_AH2_HVV",
  ]) {
    assert.ok(byId.has(interiorId), `${interiorId} should remain active in the grouped source`);
  }

  assert.deepEqual(
    JSON.parse(
      JSON.stringify(
        activeInteriors
          .filter((interior) => interior.trim_level === "3LT" && interior.seat_code === "AUP")
          .map((interior) => interior.interior_id)
          .sort()
      )
    ),
    ["3LT_AUP_HAG", "3LT_AUP_HVZ"]
  );
});

test("R6X is auto-only and D30 is the only visible disabled color override card", () => {
  assert.equal(data.choices.some((choice) => choice.rpo === "R6X" && choice.active === "True"), false);
  assert.ok(data.rules.some((rule) => rule.target_id === "opt_r6x_001" && rule.rule_type === "includes"), "R6X needs interior include rules");
  assert.ok(
    data.priceRules.some((rule) => rule.condition_option_id === "opt_d30_001" && rule.target_option_id === "opt_r6x_001" && Number(rule.price_value) === 0),
    "R6X should price at $0 only when D30 is present"
  );
  assert.ok(
    data.choices.some((choice) => choice.rpo === "D30" && choice.active === "True" && choice.selectable === "False"),
    "D30 should be visible but disabled"
  );
  assert.ok(
    data.colorOverrides.some((override) => override.adds_rpo === "opt_d30_001"),
    "D30 should remain available to color override auto-add rules"
  );
});

test("generated R6X interiors include the PriceRef R6X price component", () => {
  const byId = new Map(activeInteriors.map((interior) => [interior.interior_id, interior]));
  const r6xInteriors = activeInteriors.filter((interior) => interior.interior_id.includes("R6X"));
  assert.ok(r6xInteriors.length > 0, "active R6X interiors should exist");
  assert.equal(r6xInteriors.every((interior) => Number(interior.price) >= 995), true, "R6X interiors should include the $995 R6X component");

  assert.equal(Number(byId.get("3LT_R6X_AH2_HVV")?.price), 995);
  assert.equal(Number(byId.get("3LT_R6X_AH2_HVV_TU7")?.price), 1590);
  assert.equal(Number(byId.get("3LT_R6X_AH2_HMO_N26")?.price), 1690);
  assert.equal(Number(byId.get("3LT_R6X_AE4_HUU")?.price), 995);

  assert.equal(Number(byId.get("3LT_AH2_HUW")?.price), 0, "non-R6X interiors should not receive the R6X component");
  assert.equal(Number(byId.get("3LT_AE4_HUW")?.price), 595, "non-R6X AE4 interiors should keep their existing seat component only");
});

test("R6X keeps normal price unless D30 is present in the selected context", () => {
  const runtime = loadRuntime();
  runtime.state.trimLevel = "3LT";
  runtime.state.bodyStyle = "coupe";
  runtime.state.selectedInterior = "3LT_R6X_AH2_HMO_N26";
  assert.equal(runtime.optionPrice("opt_r6x_001"), 995, "R6X should keep normal price without D30");

  const d30Runtime = loadRuntime();
  d30Runtime.state.trimLevel = "3LT";
  d30Runtime.state.bodyStyle = "coupe";
  d30Runtime.state.selectedInterior = "3LT_R6X_AH2_HZP_N26";
  d30Runtime.state.selected.add("opt_g26_001");
  assert.equal(d30Runtime.computeAutoAdded().has("opt_d30_001"), true, "D30 should be auto-added by selected color/interior context");
  assert.equal(d30Runtime.optionPrice("opt_r6x_001"), 0, "R6X should price at $0 when D30 is present");
});

test("single interior and included seatbelt defaults are handled in runtime", () => {
  const ae4Interiors = data.interiors.filter((interior) => interior.trim_level === "1LT" && interior.seat_code === "AE4");
  assert.deepEqual(JSON.parse(JSON.stringify(ae4Interiors.map((interior) => interior.interior_code))), ["HTJ"]);
  assert.match(appSource, /function reconcileInteriorSelection/);
  assert.match(appSource, /interiors\.length === 1/);
  assert.match(appSource, /function shouldSuppressIncludedDefault/);
  assert.match(appSource, /removeAutoDefaultDuplicates/);
  assert.match(appSource, /addDefaultRpo\("719"\)/);
});

test("sidebar keeps one Standard & Included surface inside Selected RPOs", () => {
  assert.match(htmlSource, /selectedStandardEquipmentList/);
  assert.doesNotMatch(htmlSource, /standardEquipmentList/);
  assert.doesNotMatch(htmlSource, /standard-card/);
});
