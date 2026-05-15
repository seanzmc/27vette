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
    value: "",
    dataset: {},
    hidden: false,
    listeners: {},
    addEventListener(type, listener) {
      this.listeners[type] = listener;
    },
    focus() {},
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

function loadRuntime({ fetchImpl } = {}) {
  const downloads = [];
  const elements = new Map();
  const fetchCalls = [];
  const context = {
    window: {
      STINGRAY_FORM_DATA: data,
      __downloads: downloads,
      __lastBlobContent: "",
      __lastBlobType: "",
      scrollX: 0,
      scrollY: 0,
      scrollTo() {},
    },
    fetch: async (url, options = {}) => {
      fetchCalls.push({ url, options });
      if (fetchImpl) return fetchImpl(url, options);
      return {
        ok: true,
        async json() {
          return { success: true, entry_id: 112233 };
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
  render,
  compactOrder: typeof compactOrder === "function" ? compactOrder : undefined,
  plainTextOrderSummary: typeof plainTextOrderSummary === "function" ? plainTextOrderSummary : undefined,
  buildMarkdown: typeof buildMarkdown === "function" ? buildMarkdown : undefined,
  downloadBuild: typeof downloadBuild === "function" ? downloadBuild : undefined,
  openDealerSubmitModal: typeof openDealerSubmitModal === "function" ? openDealerSubmitModal : undefined,
  closeDealerSubmitModal: typeof closeDealerSubmitModal === "function" ? closeDealerSubmitModal : undefined,
  submitDealerBuild: typeof submitDealerBuild === "function" ? submitDealerBuild : undefined,
  dealerSubmissionPayload: typeof dealerSubmissionPayload === "function" ? dealerSubmissionPayload : undefined,
  requestResetBuild: typeof requestResetBuild === "function" ? requestResetBuild : undefined,
  closeConfirmActionModal: typeof closeConfirmActionModal === "function" ? closeConfirmActionModal : undefined,
  confirmPendingAction: typeof confirmPendingAction === "function" ? confirmPendingAction : undefined,
  fetchCalls,
  exportJson: typeof exportJson === "function" ? exportJson : undefined,
  exportCsv: typeof exportCsv === "function" ? exportCsv : undefined,
  downloads: window.__downloads,
  optionPrice,
  elements,
};
`
  );
  vm.runInNewContext(source, context);
  return context.window.__testApi;
}

function uniqueChoicesByRpo(rpo) {
  return [...new Map(data.choices.filter((choice) => choice.rpo === rpo).map((choice) => [choice.option_id, choice])).values()];
}

const expectedAccessoryExclusiveGroups = [
  {
    groupId: "excl_center_caps",
    rpos: ["RXJ", "VWD", "5ZD", "5ZC", "RXH"],
    optionIds: ["opt_rxj_001", "opt_vwd_001", "opt_5zd_001", "opt_5zc_001", "opt_rxh_001"],
  },
  {
    groupId: "excl_indoor_car_covers",
    rpos: ["RWH", "SL1", "WKR", "WKQ"],
    optionIds: ["opt_rwh_001", "opt_sl1_001", "opt_wkr_001", "opt_wkq_001"],
  },
  {
    groupId: "excl_outdoor_car_covers",
    rpos: ["RNX", "RWJ"],
    optionIds: ["opt_rnx_001", "opt_rwj_001"],
  },
  {
    groupId: "excl_suede_trunk_liner",
    rpos: ["SXB", "SXR", "SXT"],
    optionIds: ["opt_sxb_001", "opt_sxr_001", "opt_sxt_001"],
  },
];

function activeSelectableOptionIdsForRpo(rpo) {
  return [
    ...new Set(
      data.choices
        .filter(
          (choice) =>
            choice.rpo === rpo &&
            choice.active === "True" &&
            choice.selectable === "True" &&
            choice.step_key !== "standard_equipment"
        )
        .map((choice) => choice.option_id)
    ),
  ];
}

function activeChoiceFor(runtime, rpo) {
  return runtime.activeChoiceRows().find((choice) => choice.rpo === rpo && choice.step_key === "seat");
}

function configureInteriorOrder({ trimLevel, interiorId, seatRpo, bodyStyle = "coupe", selectedOptionIds = [] }) {
  const runtime = loadRuntime();
  runtime.state.bodyStyle = bodyStyle;
  runtime.state.trimLevel = trimLevel;
  runtime.resetDefaults();
  runtime.reconcileSelections();
  if (seatRpo) {
    const seat = activeChoiceFor(runtime, seatRpo);
    assert.ok(seat, `${seatRpo} seat should exist for ${trimLevel}`);
    runtime.handleChoice(seat);
  }
  for (const optionId of selectedOptionIds) {
    runtime.state.selected.add(optionId);
    runtime.state.userSelected.add(optionId);
  }
  runtime.state.selectedInterior = interiorId;
  return runtime;
}

function compactSeatInteriorItems(runtime) {
  const section = runtime.compactOrder().sections.find((item) => item.section === "Seats & Interior");
  assert.ok(section, "compact order should include Seats & Interior");
  return section.items;
}

test("runtime steps omit customer info and interior styling", () => {
  const keys = data.steps.map((step) => step.step_key);
  assert.equal(keys.includes("customer_info"), false);
  assert.equal(keys.includes("interior_style"), false);
  assert.ok(keys.indexOf("delivery") < keys.indexOf("summary"));
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

test("accessory exclusive groups are generated from the expected active RPOs", () => {
  assert.ok(Array.isArray(data.exclusiveGroups), "exclusiveGroups should be generated");
  for (const expectedGroup of expectedAccessoryExclusiveGroups) {
    const group = data.exclusiveGroups.find((item) => item.group_id === expectedGroup.groupId);
    assert.ok(group, `${expectedGroup.groupId} should be generated`);
    assert.equal(group.selection_mode, "single_within_group", `${expectedGroup.groupId} should use generic single-choice behavior`);
    assert.deepEqual(JSON.parse(JSON.stringify(group.option_ids)), expectedGroup.optionIds);

    const resolvedIdsByRpo = expectedGroup.rpos.map((rpo) => activeSelectableOptionIdsForRpo(rpo));
    assert.deepEqual(
      resolvedIdsByRpo,
      expectedGroup.optionIds.map((optionId) => [optionId]),
      `${expectedGroup.groupId} should resolve every listed RPO to one active selectable option`
    );
    assert.deepEqual(
      expectedGroup.rpos.filter((rpo) => activeSelectableOptionIdsForRpo(rpo).length === 0),
      [],
      `${expectedGroup.groupId} should not silently miss listed RPOs`
    );
  }
});

test("accessory exclusive groups remove other selected options in the same group", () => {
  for (const expectedGroup of expectedAccessoryExclusiveGroups) {
    for (const targetId of expectedGroup.optionIds) {
      const runtime = loadRuntime();
      runtime.state.bodyStyle = "coupe";
      runtime.state.trimLevel = "1LT";
      for (const id of expectedGroup.optionIds.filter((item) => item !== targetId)) {
        runtime.state.selected.add(id);
        runtime.state.userSelected.add(id);
      }

      const targetChoice = runtime.activeChoiceRows().find((choice) => choice.option_id === targetId);
      assert.ok(targetChoice, `${targetId} should exist for the current variant`);
      runtime.handleChoice(targetChoice);

      assert.equal(runtime.state.selected.has(targetId), true, `${targetId} should be selected`);
      assert.equal(runtime.state.userSelected.has(targetId), true, `${targetId} should be user-selected`);
      for (const peerId of expectedGroup.optionIds.filter((item) => item !== targetId)) {
        assert.equal(runtime.state.selected.has(peerId), false, `${peerId} should be removed from selected`);
        assert.equal(runtime.state.userSelected.has(peerId), false, `${peerId} should be removed from userSelected`);
      }
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
  assert.equal(t0a.step_key, "packages_performance");
});

test("app runtime has the requested navigation and filtering hooks", () => {
  assert.match(appSource, /function shouldHideChoice/);
  assert.match(appSource, /data-next-step/);
  assert.match(appSource, /renderTrimStandardEquipment/);
  assert.doesNotMatch(appSource, /state\.activeStep === "customer_info"/);
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
    for (const key of ["rpo", "label", "description", "price", "type", "section_key", "section_label", "step_key"]) {
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
    "Seats & Interior",
    "Pricing Summary",
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

test("compact order output keeps customer-facing fields and omits rich internals", () => {
  const runtime = loadRuntime();
  runtime.state.bodyStyle = "coupe";
  runtime.state.trimLevel = "1LT";
  runtime.state.customer.name = "Ada Buyer";
  runtime.state.customer.email = "ada@example.com";
  runtime.state.customer.phone = "555-0100";
  runtime.state.customer.address = "1 Corvette Way";
  runtime.state.customer.comments = "Dealer follow-up requested.";
  runtime.resetDefaults();
  runtime.reconcileSelections();

  const z51 = runtime.activeChoiceRows().find((choice) => choice.option_id === "opt_z51_001");
  const paint = runtime.activeChoiceRows().find((choice) => choice.option_id === "opt_gba_001");
  assert.ok(z51, "Z51 should exist for the current variant");
  assert.ok(paint, "Black paint should exist for the current variant");
  runtime.handleChoice(paint);
  runtime.handleChoice(z51);
  runtime.state.selectedInterior = "1LT_AQ9_HTA";

  assert.equal(typeof runtime.compactOrder, "function", "compactOrder should be exposed");
  const rich = runtime.currentOrder();
  const compact = runtime.compactOrder();

  assert.deepEqual(Object.keys(compact), ["title", "submitted_at", "customer", "vehicle", "sections", "standard_equipment", "msrp"]);
  assert.equal(compact.title, "2027 Corvette Stingray");
  assert.equal(Date.parse(compact.submitted_at) > 0, true, "submitted_at should be an ISO timestamp");
  assert.deepEqual(JSON.parse(JSON.stringify(compact.customer)), {
    name: "Ada Buyer",
    email: "ada@example.com",
    phone: "555-0100",
    address: "1 Corvette Way",
    comments: "Dealer follow-up requested.",
  });
  assert.deepEqual(Object.keys(compact.vehicle), ["body_style", "trim_level", "display_name", "base_price"]);
  assert.equal(compact.standard_equipment.count, rich.standard_equipment_summary.count);
  assert.equal(compact.msrp, rich.pricing.total_msrp);

  const compactText = JSON.stringify(compact);
  for (const forbidden of [
    "metadata",
    "dataset",
    "variant",
    "selected_option_ids",
    "selected_interior_id",
    "selected_rpos",
    "auto_added_rpos",
    "option_id",
    "section_key",
    "description",
    "groups",
  ]) {
    assert.equal(compactText.includes(forbidden), false, `compact order should omit ${forbidden}`);
  }
});

test("compact order sections omit empty/admin sections and use minimal item rows", () => {
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
  runtime.state.selectedInterior = "1LT_AQ9_HTA";

  const compact = runtime.compactOrder();
  const labels = compact.sections.map((section) => section.section);
  assert.equal(labels.includes("Pricing Summary"), false);
  assert.equal(labels.includes("Customer Information"), false);
  assert.equal(labels.includes("Vehicle"), false);
  assert.equal(labels.includes("Auto-Added / Required"), true);
  assert.equal(labels.includes("Seats & Interior"), true);

  const allItems = compact.sections.flatMap((section) => section.items);
  assert.ok(allItems.length > 0, "compact order should include selected item rows");
  for (const item of allItems) {
    assert.deepEqual(Object.keys(item), ["rpo", "label", "price"]);
  }

  const interiorRows = allItems.filter((item) => item.rpo === "HTA");
  assert.equal(interiorRows.length, 1, "selected interior should appear once");
  const autoSection = compact.sections.find((section) => section.section === "Auto-Added / Required");
  assert.ok(autoSection.items.some((item) => item.rpo === "FE3"), "auto-added FE3 should be grouped as required");
});

test("download build exports customer-facing Markdown", () => {
  const runtime = loadRuntime();
  runtime.state.bodyStyle = "coupe";
  runtime.state.trimLevel = "1LT";
  runtime.resetDefaults();
  runtime.reconcileSelections();
  runtime.render();
  runtime.downloadBuild();
  assert.equal(runtime.downloads.length, 0, "incomplete build should not download");
  assert.equal(runtime.elements.get("#downloadBuildButton").disabled, true);
  assert.match(runtime.elements.get("#downloadBuildButton").title, /Complete required selections/);

  const paint = runtime.activeChoiceRows().find((choice) => choice.option_id === "opt_gba_001");
  assert.ok(paint, "Black paint should exist for the current variant");
  runtime.handleChoice(paint);
  runtime.state.selectedInterior = "1LT_AQ9_HTA";
  runtime.reconcileSelections();
  runtime.render();
  assert.equal(runtime.elements.get("#downloadBuildButton").disabled, false);

  runtime.downloadBuild();
  const markdownDownload = runtime.downloads.at(-1);
  assert.equal(markdownDownload.filename, "stingray-build.md");
  assert.equal(markdownDownload.type, "text/markdown");
  assert.match(markdownDownload.content, /^# 2027 Corvette Stingray/);
  assert.match(markdownDownload.content, /### Variant\n\n- Corvette Stingray Coupe 1LT/);
  assert.doesNotMatch(markdownDownload.content, /Body Style:/);
  assert.doesNotMatch(markdownDownload.content, /Trim Level:/);
  assert.match(markdownDownload.content, /### Exterior Paint/);
  assert.doesNotMatch(markdownDownload.content, /Standard & Included/);
  assert.doesNotMatch(markdownDownload.content, /Base MSRP/);
  assert.match(markdownDownload.content, /### MSRP/);
  assert.equal(markdownDownload.content.includes("option_id"), false);
});

test("submit to dealer modal posts a validated dealer payload", async () => {
  assert.match(htmlSource, /id="submitDealerButton"[\s\S]*Submit to Dealer/);
  assert.match(htmlSource, /id="dealerSubmitModal"/);
  assert.match(htmlSource, /id="dealerSubmitCloseButton"[\s\S]*aria-label="Close dealer submission"[\s\S]*>×<\/button>/);
  assert.match(htmlSource, /Name <span class="required-mark" aria-hidden="true">\*<\/span>/);
  assert.match(htmlSource, /Email <span class="required-mark" aria-hidden="true">\*<\/span>/);
  assert.match(htmlSource, /id="dealerSubmitCancelButton"[\s\S]*>Cancel<\/button>/);
  assert.match(htmlSource, /id="dealerSubmitConfirmButton"[\s\S]*>Submit<\/button>/);

  const runtime = loadRuntime();
  runtime.state.bodyStyle = "coupe";
  runtime.state.trimLevel = "1LT";
  runtime.resetDefaults();
  runtime.reconcileSelections();
  runtime.render();
  runtime.openDealerSubmitModal();
  assert.equal(runtime.elements.get("#dealerSubmitModal").hidden, true, "incomplete builds should not open the submit modal");
  assert.equal(runtime.elements.get("#submitDealerButton").disabled, true);

  const paint = runtime.activeChoiceRows().find((choice) => choice.option_id === "opt_gba_001");
  runtime.handleChoice(paint);
  runtime.state.selectedInterior = "1LT_AQ9_HTA";
  runtime.reconcileSelections();
  runtime.render();
  assert.equal(runtime.elements.get("#submitDealerButton").disabled, false);

  runtime.openDealerSubmitModal();
  assert.equal(runtime.elements.get("#dealerSubmitModal").hidden, false);
  assert.equal(runtime.elements.get("#dealerSubmitCancelButton").textContent, "Cancel");
  assert.equal(runtime.elements.get("#dealerSubmitConfirmButton").textContent, "Submit");
  assert.equal(await runtime.submitDealerBuild(), null, "name and email should be required");
  assert.match(runtime.elements.get("#dealerSubmitStatus").textContent, /Name is required/);
  assert.equal(runtime.fetchCalls.length, 0, "invalid submission should not call the endpoint");

  runtime.elements.get("#dealerSubmitName").value = "Ada Buyer";
  runtime.elements.get("#dealerSubmitEmail").value = "ada@example.com";
  runtime.elements.get("#dealerSubmitPhone").value = "555-0100";
  runtime.elements.get("#dealerSubmitComments").value = "Please contact me about this build.";
  const submission = await runtime.submitDealerBuild();
  assert.equal(submission.payload.model, "stingray");
  assert.equal(submission.payload.customer.name, "Ada Buyer");
  assert.equal(submission.payload.customer.email, "ada@example.com");
  assert.match(submission.payload.plain_text_summary, /Ada Buyer/);
  assert.equal(submission.result.entry_id, 112233);
  assert.equal(runtime.fetchCalls.length, 1);
  assert.equal(runtime.fetchCalls[0].url, "https://stingraychevroletcorvette.com/wp-json/corvette-build/v1/submit");
  assert.equal(runtime.fetchCalls[0].options.method, "POST");
  assert.equal(runtime.fetchCalls[0].options.headers["Content-Type"], "application/json");
  const postedBody = JSON.parse(runtime.fetchCalls[0].options.body);
  assert.equal(postedBody.customer.email, "ada@example.com");
  assert.deepEqual(Object.keys(postedBody), ["model", "customer", "vehicle", "sections", "msrp", "plain_text_summary"]);
  assert.match(postedBody.msrp, /^\$\d{1,3}(,\d{3})*$/);
  assert.equal(postedBody.plain_text_summary.includes(`<strong>Total MSRP: ${postedBody.msrp}</strong>`), true);
  assert.doesNotMatch(postedBody.plain_text_summary, /<h3/i);
  assert.match(runtime.elements.get("#dealerSubmitStatus").textContent, /Build submitted to Stingray Chevrolet\. A Corvette specialist will contact you soon\. Confirmation ID: 112233\./);
  assert.equal(runtime.elements.get("#dealerSubmitConfirmButton").hidden, true, "successful submit should remove the submit button");
  assert.equal(runtime.elements.get("#dealerSubmitConfirmButton").disabled, true, "successful submit should keep submit unavailable");
  assert.equal(runtime.elements.get("#dealerSubmitCancelButton").textContent, "Close", "successful submit should change bottom cancel action to close");
  assert.equal(await runtime.submitDealerBuild(), null, "successful submission should not be submitted twice");
  assert.equal(runtime.fetchCalls.length, 1, "duplicate successful submission should not call the endpoint again");
  runtime.closeDealerSubmitModal();
  assert.equal(runtime.elements.get("#dealerSubmitModal").hidden, true);
  runtime.openDealerSubmitModal();
  assert.equal(runtime.elements.get("#dealerSubmitConfirmButton").hidden, true, "reopened successful modal should keep submit hidden");
  assert.match(runtime.elements.get("#dealerSubmitStatus").textContent, /Build submitted to Stingray Chevrolet\. A Corvette specialist will contact you soon\./);
});

test("submit to dealer modal surfaces endpoint failures", async () => {
  const runtime = loadRuntime({
    fetchImpl: async () => ({
      ok: false,
      async json() {
        return { success: false, message: "Could not create Formidable entry." };
      },
    }),
  });
  runtime.state.bodyStyle = "coupe";
  runtime.state.trimLevel = "1LT";
  runtime.resetDefaults();
  runtime.reconcileSelections();
  runtime.handleChoice(runtime.activeChoiceRows().find((choice) => choice.option_id === "opt_gba_001"));
  runtime.state.selectedInterior = "1LT_AQ9_HTA";
  runtime.reconcileSelections();
  runtime.openDealerSubmitModal();
  runtime.elements.get("#dealerSubmitName").value = "Ada Buyer";
  runtime.elements.get("#dealerSubmitEmail").value = "ada@example.com";

  assert.equal(await runtime.submitDealerBuild(), null);
  assert.equal(runtime.fetchCalls.length, 1);
  assert.match(runtime.elements.get("#dealerSubmitStatus").textContent, /Could not create Formidable entry/);
  assert.equal(runtime.elements.get("#dealerSubmitCancelButton").textContent, "Cancel", "failed submit should keep cancel label");
  assert.equal(runtime.elements.get("#dealerSubmitConfirmButton").hidden, false, "failed submit should keep submit visible for retry");
  assert.equal(runtime.elements.get("#dealerSubmitConfirmButton").disabled, false, "failed submit should keep submit retryable");
});

test("reset button confirms dirty builds and returns to step one", () => {
  assert.match(htmlSource, /id="confirmActionModal"/);
  assert.match(htmlSource, /id="confirmActionCancelButton"[\s\S]*>No, Cancel<\/button>/);
  assert.match(htmlSource, /id="confirmActionConfirmButton"[\s\S]*>Yes, Reset<\/button>/);

  const runtime = loadRuntime();
  runtime.state.bodyStyle = "coupe";
  runtime.state.trimLevel = "1LT";
  runtime.resetDefaults();
  runtime.reconcileSelections();
  runtime.render();

  runtime.requestResetBuild();
  assert.equal(runtime.elements.get("#confirmActionModal").hidden, true, "clean reset should not prompt");

  runtime.state.selected.add("opt_z51_001");
  runtime.state.userSelected.add("opt_z51_001");
  runtime.state.activeStep = "paint";
  runtime.requestResetBuild();
  assert.equal(runtime.elements.get("#confirmActionModal").hidden, false);
  assert.equal(runtime.elements.get("#confirmActionMessage").textContent, "This will reset all selected options. Are you sure?");
  assert.equal(runtime.elements.get("#confirmActionConfirmButton").textContent, "Yes, Reset");

  runtime.closeConfirmActionModal();
  assert.equal(runtime.elements.get("#confirmActionModal").hidden, true);
  assert.equal(runtime.state.selected.has("opt_z51_001"), true, "cancel should preserve selected options");
  assert.equal(runtime.state.activeStep, "paint");

  runtime.requestResetBuild();
  runtime.confirmPendingAction();
  assert.equal(runtime.elements.get("#confirmActionModal").hidden, true);
  assert.equal(runtime.state.selected.has("opt_z51_001"), false, "confirmed reset should clear selected options");
  assert.equal(runtime.state.userSelected.size, 0);
  assert.equal(runtime.state.selectedInterior, "");
  assert.equal(runtime.state.activeStep, "body_style");
});

test("plain text order summary renders compact order data for emails and review", () => {
  const runtime = loadRuntime();
  runtime.state.bodyStyle = "coupe";
  runtime.state.trimLevel = "1LT";
  runtime.state.customer.name = "Ada Buyer";
  runtime.state.customer.email = "ada@example.com";
  runtime.state.customer.phone = "555-0100";
  runtime.state.customer.address = "1 Corvette Way";
  runtime.state.customer.comments = "Dealer follow-up requested.";
  runtime.resetDefaults();
  runtime.reconcileSelections();

  const z51 = runtime.activeChoiceRows().find((choice) => choice.option_id === "opt_z51_001");
  const paint = runtime.activeChoiceRows().find((choice) => choice.option_id === "opt_gba_001");
  assert.ok(z51, "Z51 should exist for the current variant");
  assert.ok(paint, "Black paint should exist for the current variant");
  runtime.handleChoice(paint);
  runtime.handleChoice(z51);
  runtime.state.selectedInterior = "1LT_AQ9_HTA";

  assert.equal(typeof runtime.plainTextOrderSummary, "function", "plainTextOrderSummary should be exposed");
  const summary = runtime.plainTextOrderSummary();

  assert.doesNotMatch(summary, /^<p>2027 Corvette Stingray<\/p>/);
  assert.match(summary, /^<p><strong>Name:<\/strong> Ada Buyer<br><strong>Email:<\/strong> ada@example\.com<br><strong>Phone:<\/strong> 555-0100<br><strong>Address:<\/strong> 1 Corvette Way/);
  assert.match(summary, /<strong>Comments:<\/strong> Dealer follow-up requested\./);
  assert.match(summary, /<strong>Submitted:<\/strong> .+/);
  assert.match(summary, /<p><strong><u>Variant<\/u><\/strong><\/p><ul><li>Corvette Stingray Coupe 1LT<\/li><\/ul>/);
  assert.doesNotMatch(summary, /Variant<\/u><\/strong><\/p><ul><li>coupe<\/li><li>1LT/);
  assert.doesNotMatch(summary, /Base MSRP/);
  assert.match(summary, /<p><strong><u>Exterior Paint<\/u><\/strong><\/p><ul><li>GBA Black: \$0<\/li>/);
  assert.match(summary, /<p><strong><u>Seats &amp; Interior<\/u><\/strong><\/p><ul>[\s\S]*<li>AQ9 GT1 Bucket Seats: \$0<\/li>[\s\S]*<li>HTA Jet Black: \$0<\/li>/);
  assert.match(summary, /<p><strong><u>Auto-Added \/ Required<\/u><\/strong><\/p><ul>[\s\S]*<li>FE3 Z51 performance suspension: \$0<\/li>/);
  assert.doesNotMatch(summary, /STANDARD & INCLUDED/);
  assert.match(summary, /<p><strong>Total MSRP: \$\d/);
  assert.doesNotMatch(summary, /(?:^|\n)(?:Vehicle|Exterior Paint|Seats & Interior|Auto-Added \/ Required)(?:\n|$)/);
  assert.doesNotMatch(summary, /\b(?:GBA Black|GT1 Bucket Seats|Z51 performance suspension) \d+\b/);
  assert.doesNotMatch(summary, /<li><strong>/);
  assert.doesNotMatch(summary, /<h3/i);
});

test("plain text order summary omits empty comments and internal debug fields", () => {
  const runtime = loadRuntime();
  runtime.state.bodyStyle = "coupe";
  runtime.state.trimLevel = "1LT";
  runtime.resetDefaults();
  runtime.reconcileSelections();
  runtime.state.selectedInterior = "1LT_AQ9_HTA";

  const summary = runtime.plainTextOrderSummary();
  assert.equal(summary.includes("Comments:"), false);
  assert.equal((summary.match(/HTA Jet Black/g) || []).length, 1, "selected interior should appear once");
  for (const forbidden of [
    "metadata",
    "dataset",
    "option_id",
    "selected_option_ids",
    "selected_interior_id",
    "description",
    "section_key",
    "Pricing Summary",
  ]) {
    assert.equal(summary.includes(forbidden), false, `summary should omit ${forbidden}`);
  }
});

test("generated interiors expose priced component metadata from PriceRef", () => {
  const byId = new Map(activeInteriors.map((interior) => [interior.interior_id, interior]));
  const expectations = [
    ["2LT_AQ9_H1Y_36S", [{ rpo: "36S", label: "Yellow Stitching", price: 495, component_type: "stitching" }]],
    ["2LT_AQ9_H1Y_37S", [{ rpo: "37S", label: "Blue Stitching", price: 495, component_type: "stitching" }]],
    ["2LT_AQ9_H1Y_38S", [{ rpo: "38S", label: "Red Stitching", price: 495, component_type: "stitching" }]],
    ["2LT_AH2_HTP_N26", [{ rpo: "N26", label: "Sueded Microfiber", price: 695, component_type: "suede" }]],
    ["2LT_AH2_HTN_TU7", [{ rpo: "TU7", label: "Two-Tone", price: 595, component_type: "two_tone" }]],
    ["3LT_R6X_AH2_HUU", [{ rpo: "R6X", label: "Custom Interior Trim and Seat Combination", price: 995, component_type: "r6x" }]],
    ["3LT_R6X_AE4_HUU", [{ rpo: "R6X", label: "Custom Interior Trim and Seat Combination", price: 1590, component_type: "r6x" }]],
  ];

  for (const [interiorId, expectedComponents] of expectations) {
    const interior = byId.get(interiorId);
    assert.ok(interior, `${interiorId} should be active`);
    assert.ok(Array.isArray(interior.interior_components), `${interiorId} should expose interior_components`);
    for (const expected of expectedComponents) {
      assert.deepEqual(
        JSON.parse(JSON.stringify(interior.interior_components.find((component) => component.rpo === expected.rpo))),
        expected,
        `${interiorId} should include ${expected.rpo}`
      );
    }
  }
});

test("compact and plain text order output break selected interior into priced component RPO lines", () => {
  const cases = [
    {
      trimLevel: "2LT",
      interiorId: "2LT_AQ9_H1Y_36S",
      expected: { rpo: "36S", label: "Yellow Stitching", price: 495 },
    },
    {
      trimLevel: "2LT",
      interiorId: "2LT_AQ9_H1Y_37S",
      expected: { rpo: "37S", label: "Blue Stitching", price: 495 },
    },
    {
      trimLevel: "2LT",
      interiorId: "2LT_AQ9_H1Y_38S",
      expected: { rpo: "38S", label: "Red Stitching", price: 495 },
    },
    {
      trimLevel: "2LT",
      interiorId: "2LT_AH2_HTP_N26",
      seatRpo: "AH2",
      expected: { rpo: "N26", label: "Sueded Microfiber", price: 695 },
    },
    {
      trimLevel: "2LT",
      interiorId: "2LT_AH2_HTN_TU7",
      seatRpo: "AH2",
      expected: { rpo: "TU7", label: "Two-Tone", price: 595 },
    },
  ];

  for (const item of cases) {
    const runtime = configureInteriorOrder(item);
    const compactItems = compactSeatInteriorItems(runtime);
    assert.ok(
      compactItems.some(
        (compactItem) =>
          compactItem.rpo === item.expected.rpo &&
          compactItem.label === item.expected.label &&
          compactItem.price === item.expected.price
      ),
      `${item.interiorId} should show ${item.expected.rpo} as a compact component line`
    );
    assert.equal(
      compactItems.filter((compactItem) => compactItem.rpo === data.interiors.find((interior) => interior.interior_id === item.interiorId)?.interior_code).length,
      1,
      `${item.interiorId} selected interior identity should appear once`
    );

    const summary = runtime.plainTextOrderSummary();
    assert.match(
      summary,
      new RegExp(`${item.expected.rpo} ${item.expected.label}: \\$${item.expected.price.toLocaleString("en-US")}`),
      `${item.interiorId} should show ${item.expected.rpo} in plain text`
    );
  }
});

test("R6X component order output uses PriceRef pricing and D30 only zeroes the R6X component", () => {
  const ah2Runtime = configureInteriorOrder({ trimLevel: "3LT", interiorId: "3LT_R6X_AH2_HUU", seatRpo: "AH2" });
  assert.ok(
    compactSeatInteriorItems(ah2Runtime).some((item) => item.rpo === "R6X" && item.label === "Custom Interior Trim and Seat Combination" && item.price === 995),
    "3LT R6X AH2 should show R6X at $995"
  );

  const ae4Runtime = configureInteriorOrder({ trimLevel: "3LT", interiorId: "3LT_R6X_AE4_HUU", seatRpo: "AE4" });
  assert.ok(
    compactSeatInteriorItems(ae4Runtime).some((item) => item.rpo === "R6X" && item.label === "Custom Interior Trim and Seat Combination" && item.price === 1590),
    "3LT R6X AE4 should show R6X at $1,590"
  );

  const d30Runtime = configureInteriorOrder({
    trimLevel: "3LT",
    interiorId: "3LT_R6X_AH2_HZP_N26",
    seatRpo: "AH2",
    selectedOptionIds: ["opt_g26_001"],
  });
  assert.equal(d30Runtime.computeAutoAdded().has("opt_d30_001"), true, "D30 should be triggered by selected color/interior context");
  assert.ok(
    compactSeatInteriorItems(d30Runtime).some((item) => item.rpo === "R6X" && item.label === "Custom Interior Trim and Seat Combination" && item.price === 0),
    "D30-triggered R6X should remain visible at $0"
  );
});

test("order summary helpers are exposed for browser debug inspection", () => {
  assert.match(appSource, /window\.__orderDebug\s*=\s*\{[\s\S]*currentOrder,[\s\S]*compactOrder,[\s\S]*plainTextOrderSummary,[\s\S]*buildMarkdown,[\s\S]*\}/);
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

test("Stingray workbook default-selected standard choices seed every variant", () => {
  const expectedDefaultIds = ["opt_efr_001", "opt_719_001"];

  for (const variant of data.variants) {
    for (const optionId of expectedDefaultIds) {
      const choice = data.choices.find((row) => row.variant_id === variant.variant_id && row.option_id === optionId);
      assert.ok(choice, `${variant.variant_id} should emit ${optionId}`);
      assert.equal(choice.status, "standard", `${variant.variant_id} ${choice.rpo} should remain standard`);
      assert.equal(choice.selectable, "True", `${variant.variant_id} ${choice.rpo} should remain selectable`);
      assert.equal(
        choice.display_behavior,
        "default_selected",
        `${variant.variant_id} ${choice.rpo} should be workbook-authored default_selected`
      );
    }

    const runtime = loadRuntime();
    runtime.state.bodyStyle = variant.body_style;
    runtime.state.trimLevel = variant.trim_level;
    runtime.resetDefaults();
    runtime.reconcileSelections();
    for (const optionId of expectedDefaultIds) {
      assert.equal(runtime.state.selected.has(optionId), true, `${variant.variant_id} should select ${optionId} by default`);
    }
  }
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

test("stripe sections use the requested order", () => {
  const sectionNames = data.sections
    .filter((section) => section.step_key === "aero_exhaust_stripes_accessories")
    .sort((a, b) => Number(a.section_display_order) - Number(b.section_display_order))
    .map((section) => section.section_name);

  assert.deepEqual(
    JSON.parse(JSON.stringify(sectionNames)),
    ["Stripes", "GS Hash Marks", "GS Center Stripes"]
  );
  assert.match(appSource, /section_display_order/);
});

test("Stingray section placement follows workbook step ownership", () => {
  const sectionById = new Map(data.sections.map((section) => [section.section_id, section]));
  assert.equal(sectionById.get("sec_perf_001")?.section_name, "Mechanical");
  assert.equal(sectionById.get("sec_perf_001")?.step_key, "packages_performance");
  assert.equal(sectionById.get("sec_exha_001")?.step_key, "packages_performance");
  assert.equal(sectionById.get("sec_spoi_001")?.step_key, "packages_performance");
  assert.equal(sectionById.get("sec_lpoe_001")?.step_key, "accessories");
  assert.equal(sectionById.get("sec_lpow_001")?.step_key, "accessories");
  assert.equal(sectionById.get("sec_lpoi_001")?.step_key, "accessories");
  assert.equal(data.choices.some((choice) => choice.section_id === "sec_onst_001" && choice.active === "True"), false);

  const activeSectionIds = new Set(data.choices.filter((choice) => choice.active === "True").map((choice) => choice.section_id));
  const activePerformanceSections = data.sections
    .filter((section) => section.step_key === "packages_performance" && activeSectionIds.has(section.section_id))
    .sort((a, b) => Number(a.section_display_order) - Number(b.section_display_order))
    .map((section) => section.section_name);
  assert.deepEqual(JSON.parse(JSON.stringify(activePerformanceSections)), ["Mechanical", "Suspension", "Spoiler", "Exhaust"]);

  const activeAccessorySections = data.sections
    .filter((section) => section.step_key === "accessories" && activeSectionIds.has(section.section_id))
    .sort((a, b) => Number(a.section_display_order) - Number(b.section_display_order))
    .map((section) => section.section_name);
  assert.deepEqual(JSON.parse(JSON.stringify(activeAccessorySections)), ["LPO Wheels", "LPO Exterior", "LPO Interior"]);

  assert.equal(data.steps.find((step) => step.step_key === "base_interior")?.step_label, "Interior Color");
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

  const activeSectionIds = new Set(data.choices.filter((choice) => choice.active === "True").map((choice) => choice.section_id));
  const wheelSections = data.sections
    .filter((section) => section.step_key === "wheels")
    .filter((section) => activeSectionIds.has(section.section_id))
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
  assert.equal(
    data.priceRules.some((rule) => rule.condition_option_id === "opt_d30_001" && rule.target_option_id === "opt_r6x_001"),
    false,
    "R6X pricing is carried by interior setup, not a D30 price override"
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

test("R6X keeps normal price even when D30 is present in the selected context", () => {
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
  assert.equal(d30Runtime.optionPrice("opt_r6x_001"), 995, "R6X should keep normal option price when D30 is present");
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
