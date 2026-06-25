import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
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
const stylesSource = fs.readFileSync("form-app/styles.css", "utf8");

function workbookRows(sheetName) {
  const output = execFileSync(
    ".venv/bin/python",
    [
      "-c",
      [
        "import json",
        "from openpyxl import load_workbook",
        "wb = load_workbook('stingray_master.xlsx', read_only=True, data_only=True)",
        `ws = wb['${sheetName}']`,
        "headers = [ws.cell(1, col).value for col in range(1, ws.max_column + 1)]",
        "rows = []",
        "def legacy_value(value):",
        "    return 'True' if value is True else 'False' if value is False else value",
        "for raw in ws.iter_rows(min_row=2, values_only=True):",
        "    record = {header: legacy_value(value) for header, value in zip(headers, raw) if header and value is not None}",
        "    if record:",
        "        rows.append(record)",
        "print(json.dumps(rows))",
      ].join("\n"),
    ],
    { encoding: "utf8" }
  );
  return JSON.parse(output);
}

const stingrayScopeRows = workbookRows("model_interior_scope").filter((row) => row.model_key === "stingray" && row.active === "True");
const stingrayScopeIds = new Set(stingrayScopeRows.map((row) => row.interior_id));
const activeInteriors = data.interiors.filter((interior) => interior.active_for_stingray === true);

function cssOrderFor(selector, source = stylesSource) {
  const escapedSelector = selector.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  const match = source.match(new RegExp(`${escapedSelector}\\s*\\{[\\s\\S]*?order:\\s*(\\d+)`));
  return match ? Number(match[1]) : Number.NaN;
}

function cssBlock(selector, source = stylesSource) {
  const escapedSelector = selector.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  return source.match(new RegExp(`${escapedSelector}\\s*\\{[\\s\\S]*?\\}`))?.[0] || "";
}

function makeElement() {
  return {
    textContent: "",
    innerHTML: "",
    value: "",
    dataset: {},
    hidden: false,
    scrollTop: 0,
    scrollLeft: 0,
    clientHeight: 0,
    scrollHeight: 0,
    style: {},
    attributes: {},
    listeners: {},
    addEventListener(type, listener) {
      this.listeners[type] = listener;
    },
    setAttribute(name, value) {
      this.attributes[name] = String(value);
    },
    getAttribute(name) {
      return this.attributes[name];
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

function loadRuntime({ fetchImpl, turnstileAvailable = true } = {}) {
  const downloads = [];
  const elements = new Map();
  const docListeners = {};
  const fetchCalls = [];
  const turnstileCalls = [];
  let turnstileToken = "test-turnstile-token";
  const turnstileApi = {
    render(selector, options) {
      turnstileCalls.push({ fn: "render", selector, options });
      options.callback?.(turnstileToken);
      return "test-widget-id";
    },
    reset(widgetId) {
      turnstileCalls.push({ fn: "reset", widgetId });
    },
    remove(widgetId) {
      turnstileCalls.push({ fn: "remove", widgetId });
    },
  };
  const context = {
    window: {
      STINGRAY_FORM_DATA: data,
      __downloads: downloads,
      __lastBlobContent: "",
      __lastBlobType: "",
      turnstile: turnstileAvailable ? turnstileApi : undefined,
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
      addEventListener(type, listener, options) {
        docListeners[type] = { listener, options };
      },
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
    docListeners,
    elements,
    turnstileCalls,
    turnstileApi,
    setTurnstileToken(value) {
      turnstileToken = value;
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
  get data() { return data; },
  activeChoiceRows,
  resetDefaults,
  reconcileSelections,
  handleChoice,
  computeAutoAdded,
  disableReasonForChoice,
  missingRequired,
  lineItems,
  currentOrder,
  render,
  renderChoiceCard,
  renderInteriorGroups: typeof renderInteriorGroups === "function" ? renderInteriorGroups : undefined,
  activateStep: typeof activateStep === "function" ? activateStep : undefined,
  setMobileDrawer: typeof setMobileDrawer === "function" ? setMobileDrawer : undefined,
  closeMobileDrawers: typeof closeMobileDrawers === "function" ? closeMobileDrawers : undefined,
  currentStepSummary: typeof currentStepSummary === "function" ? currentStepSummary : undefined,
  renderMobileProgress: typeof renderMobileProgress === "function" ? renderMobileProgress : undefined,
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
  handleDrawerWheel: typeof handleDrawerWheel === "function" ? handleDrawerWheel : undefined,
  fetchCalls,
  docListeners,
  turnstileCalls,
  setTurnstileToken: typeof setTurnstileToken === "function" ? setTurnstileToken : undefined,
  setWindowTurnstile: () => {
    window.turnstile = ${"turnstileApi"};
  },
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
    groupId: "excl_rear_script_badges",
    rpos: ["RIK", "RIN", "SL8"],
    optionIds: ["opt_rik_001", "opt_rin_001", "opt_sl8_001"],
  },
  {
    groupId: "excl_suede_trunk_liner",
    rpos: ["SXB", "SXR", "SXT"],
    optionIds: ["opt_sxb_001", "opt_sxr_001", "opt_sxt_001"],
  },
  {
    groupId: "excl_ext_accents",
    rpos: ["EFR", "EFY", "EDU"],
    optionIds: ["opt_efr_001", "opt_efy_001", "opt_edu_001"],
    selectionMode: "required_single_within_group",
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
});

test("runtime payload trims choice-row duplicates while preserving consumed metadata", () => {
  const strippedChoiceFields = ["source_detail_raw", "choice_mode", "selection_mode", "selection_mode_label"];
  for (const choice of data.choices) {
    for (const field of strippedChoiceFields) {
      assert.equal(Object.hasOwn(choice, field), false, `${choice.choice_id} leaked ${field}`);
    }
  }
  for (const row of data.standardEquipment) {
    assert.equal(Object.hasOwn(row, "source_detail_raw"), false, `${row.equipment_id} leaked source_detail_raw`);
  }

  assert.ok(data.choices.some((choice) => Object.hasOwn(choice, "status_label")), "runtime keeps choice status_label");
  assert.ok(Array.isArray(data.validation), "runtime keeps validation rows");
  assert.ok(data.interiors.some((interior) => Object.hasOwn(interior, "source_note")), "runtime keeps interior source_note");
  assert.ok(data.ruleGroups.some((group) => Object.hasOwn(group, "notes")), "runtime keeps group notes");
  assert.ok(data.sections.some((section) => section.choice_mode), "runtime keeps section choice_mode");
  assert.ok(data.sections.some((section) => section.selection_mode), "runtime keeps section selection_mode");
  assert.ok(data.sections.some((section) => section.selection_mode_label), "runtime keeps section selection_mode_label");
  assert.ok(data.exclusiveGroups.some((group) => group.selection_mode), "runtime keeps exclusive group selection_mode");
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
  const defaultBc7 = data.defaultSelectionRules.find((rule) => rule.rule_id === "default_bc7");
  assert.ok(defaultBc7, "BC7 coupe default should be workbook-owned through default_selection_rules");
  assert.equal(defaultBc7.target_option_id, "opt_bc7_001");
  assert.equal(defaultBc7.condition_type, "always");
  assert.equal(defaultBc7.body_style_scope, "coupe");
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
  for (const targetId of ["opt_tvs_001", "opt_5zz_001", "opt_5zu_001"]) {
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
    assert.equal(
      group.selection_mode,
      expectedGroup.selectionMode || "single_within_group",
      `${expectedGroup.groupId} should use expected workbook-owned single-choice behavior`
    );
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

test("Stingray rear script badge replacement is owned by an exclusive group, not pairwise rules", () => {
  const scriptOptionIds = ["opt_rik_001", "opt_rin_001", "opt_sl8_001"];
  const pairwiseScriptRules = data.rules.filter(
    (rule) => scriptOptionIds.includes(rule.source_id) || scriptOptionIds.includes(rule.target_id)
  );

  assert.equal(pairwiseScriptRules.length, 0);
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

test("Stingray required exterior accents cannot be cleared but can be switched", () => {
  const runtime = loadRuntime();
  runtime.state.bodyStyle = "coupe";
  runtime.state.trimLevel = "1LT";
  runtime.resetDefaults();
  runtime.reconcileSelections();

  const efr = runtime.activeChoiceRows().find((choice) => choice.option_id === "opt_efr_001");
  const efy = runtime.activeChoiceRows().find((choice) => choice.option_id === "opt_efy_001");
  const edu = runtime.activeChoiceRows().find((choice) => choice.option_id === "opt_edu_001");
  assert.ok(efr && efy && edu, "Stingray exterior accent choices should be active");
  assert.equal(runtime.state.selected.has("opt_efr_001"), true, "EFR should seed as the default exterior accent");

  runtime.handleChoice(efr);
  assert.equal(runtime.state.selected.has("opt_efr_001"), true, "clicking the only selected required accent should not clear it");

  runtime.handleChoice(efy);
  assert.equal(runtime.state.selected.has("opt_efy_001"), true, "EFY should be selectable");
  assert.equal(runtime.state.selected.has("opt_efr_001"), false, "EFY should replace EFR");

  runtime.handleChoice(edu);
  assert.equal(runtime.state.selected.has("opt_edu_001"), true, "EDU should be selectable");
  assert.equal(runtime.state.selected.has("opt_efy_001"), false, "EDU should replace EFY");
});

test("Stingray coupe engine covers switch BC7 and paid covers as radio peers", () => {
  const runtime = loadRuntime();
  runtime.state.bodyStyle = "coupe";
  runtime.state.trimLevel = "1LT";
  runtime.resetDefaults();
  runtime.reconcileSelections();

  const bc7 = runtime.activeChoiceRows().find((choice) => choice.option_id === "opt_bc7_001");
  const bcp = runtime.activeChoiceRows().find((choice) => choice.option_id === "opt_bcp_001");
  assert.ok(bc7 && bcp, "BC7 and BCP should be active on Stingray coupe");
  assert.equal(runtime.state.selected.has("opt_bc7_001"), true, "BC7 should seed as the coupe default cover");

  runtime.handleChoice(bc7);
  assert.equal(runtime.state.selected.has("opt_bc7_001"), true, "clicking selected BC7 should restore the workbook-owned coupe default");

  runtime.handleChoice(bcp);
  assert.equal(runtime.state.selected.has("opt_bcp_001"), true, "BCP should select");
  assert.equal(runtime.state.selected.has("opt_bc7_001"), false, "BCP should remove default BC7");

  runtime.handleChoice(bcp);
  assert.equal(runtime.state.selected.has("opt_bcp_001"), false, "clicking selected BCP should remove the paid cover");
  assert.equal(runtime.state.selected.has("opt_bc7_001"), true, "removing a paid cover should restore the workbook-owned BC7 coupe default");

  runtime.handleChoice(bcp);
  runtime.handleChoice(bc7);
  assert.equal(runtime.state.selected.has("opt_bc7_001"), true, "BC7 should be selectable again");
  assert.equal(runtime.state.selected.has("opt_bcp_001"), false, "BC7 should replace BCP");
});

test("Engine Appearance is not an open requirement for Stingray convertible without ZZ3", () => {
  const runtime = loadRuntime();
  runtime.state.bodyStyle = "convertible";
  runtime.state.trimLevel = "1LT";
  runtime.resetDefaults();
  runtime.reconcileSelections();

  assert.equal(runtime.missingRequired?.().includes("Engine Appearance"), false, "Engine Appearance should not block a convertible build by itself");
  const zz3 = runtime.activeChoiceRows().find((choice) => choice.option_id === "opt_zz3_001");
  assert.ok(zz3, "ZZ3 should be active for convertible builds");
  runtime.handleChoice(zz3);
  assert.equal(runtime.computeAutoAdded().has("opt_bc7_001"), true, "ZZ3 should provide the required BC7 cover path");
  assert.equal(runtime.missingRequired?.().includes("Engine Appearance"), false, "ZZ3 cover behavior should not create an Engine Appearance open requirement");
});

test("1LT interior color groups stay expanded when each group has one option", () => {
  const runtime = loadRuntime();
  runtime.state.bodyStyle = "coupe";
  runtime.state.trimLevel = "1LT";
  runtime.resetDefaults();
  runtime.reconcileSelections();
  const gt1 = runtime.activeChoiceRows().find((choice) => choice.rpo === "AQ9" && choice.step_key === "seat");
  assert.ok(gt1, "GT1 seat should exist for 1LT");
  runtime.handleChoice(gt1);
  const interiors = runtime.data.interiors.filter((interior) => interior.trim_level === "1LT" && interior.seat_code === "AQ9");
  assert.equal(interiors.length > 1, true, "1LT should expose multiple color groups");

  const html = runtime.renderInteriorGroups(interiors);
  assert.doesNotMatch(html, /<details class="interior-group"/, "single-option 1LT color groups should not be collapsed");
  assert.match(html, /<section class="interior-group"/);
  assert.match(html, /<button class="choice-card"/);
});

test("interior color groups render as collapsed disclosure containers without the rejected restyle", () => {
  const runtime = loadRuntime();
  runtime.state.bodyStyle = "coupe";
  runtime.state.trimLevel = "2LT";
  runtime.resetDefaults();
  runtime.reconcileSelections();
  const gt2 = runtime.activeChoiceRows().find((choice) => choice.rpo === "AH2" && choice.step_key === "seat");
  assert.ok(gt2, "GT2 seat should exist for 2LT");
  runtime.handleChoice(gt2);
  const interiors = runtime.data.interiors.filter((interior) => interior.trim_level === "2LT" && interior.seat_code === "AH2");
  assert.equal(interiors.length > 3, true, "2LT GT2 should expose multiple interior colors");

  const html = runtime.renderInteriorGroups(interiors);
  assert.match(html, /<details class="interior-group"/);
  assert.match(html, /<summary class="interior-group-header">/);
  assert.doesNotMatch(html, /<details class="interior-group"[^>]*\sopen(?:\s|>)/, "groups should be collapsed by default without a selection");
  assert.doesNotMatch(stylesSource, /\.interior-color-section\s*\{[\s\S]*background:\s*linear-gradient/);
  assert.doesNotMatch(stylesSource, /\.interior-group\s*\{[\s\S]*background:\s*#fbfaf7/);
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

  const zf1Rows = uniqueChoicesByRpo("ZF1");
  assert.equal(zf1Rows.length, 1, "ZF1 should use one body-style-neutral option id");
  assert.equal(zf1Rows[0].selectable, "True");
  assert.equal(zf1Rows[0].step_key, "packages_performance");
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

test("mobile shell exposes compact progress and summary targets", () => {
  assert.doesNotMatch(htmlSource, /id="mobileSummaryToggle"/);
  assert.doesNotMatch(appSource, /download\/send/);
  assert.doesNotMatch(htmlSource, /class="vehicle-bar"/);
  assert.doesNotMatch(htmlSource, /id="currentBody"/);
  assert.doesNotMatch(htmlSource, /id="currentTrim"/);
  assert.doesNotMatch(htmlSource, /id="basePrice"/);
  assert.doesNotMatch(appSource, /renderVehicleContext/);
  assert.doesNotMatch(htmlSource, /Current Build/);
  assert.match(htmlSource, /<small class="mobile-summary-label">Build Summary<\/small>/);
  assert.match(htmlSource, /id="mobileSummaryButton"/);
  assert.match(htmlSource, /id="openSummaryDrawerButton"/);
  assert.match(htmlSource, /id="downloadBuildButton"[\s\S]*aria-label="Download Build"[\s\S]*<svg class="download-icon"[\s\S]*<path d="M12 3v11/);
  assert.match(htmlSource, /class="toolbar-action-group toolbar-build-group"[\s\S]*id="openSummaryDrawerButton"[\s\S]*id="submitDealerButton"/);
  assert.doesNotMatch(htmlSource, /summary-drawer-icon/);
  assert.doesNotMatch(appSource, /summaryIcon/);
  assert.match(htmlSource, /Build Summary/);
  assert.doesNotMatch(htmlSource, /<span aria-hidden="true">\$<\/span>/);
  assert.match(htmlSource, /id="mobileSummaryTotal"/);
  assert.match(htmlSource, /id="mobileSummaryMissing"/);
  assert.match(htmlSource, /id="mobileProgress"/);
  assert.match(htmlSource, /id="mobilePrevStep"/);
  assert.match(htmlSource, /id="mobileNextStep"/);
  assert.match(htmlSource, /id="openStepDrawerButton"/);
  assert.match(htmlSource, /id="openSummaryDrawerButton"/);
  assert.match(htmlSource, /id="resetButton"[\s\S]*aria-label="Reset build"[\s\S]*title="Reset build"[\s\S]*<svg class="reset-icon"/);
  assert.doesNotMatch(htmlSource, /class="reset-icon" aria-hidden="true">↻/);
  assert.doesNotMatch(htmlSource, /id="modelSelect"/);
  assert.match(htmlSource, /class="reset-icon"/);
  assert.match(htmlSource, /id="mobileDrawerBackdrop"/);
  assert.match(htmlSource, /id="stepRailDrawer"/);
  assert.match(htmlSource, /id="summaryDrawer"/);
  assert.match(htmlSource, /<h3 id="variantName">Stingray<\/h3>/);
  assert.doesNotMatch(htmlSource, /<h2 id="variantName"/);
  assert.match(stylesSource, /\.summary-panel\s*\{[\s\S]*padding:\s*8px;/);
  assert.match(stylesSource, /\.summary-card\s*\{[\s\S]*margin-bottom:\s*8px;[\s\S]*padding:\s*14px;/);
  assert.equal(cssOrderFor("#summaryOverviewCard"), 1);
  assert.equal(cssOrderFor("#requirementsCard"), 2);
  assert.equal(cssOrderFor("#selectedRposCard"), 3);
  assert.equal(cssOrderFor("#autoAddedCard"), 4);
});

test("shell containers share one spacing and radius rhythm", () => {
  assert.match(stylesSource, /--shell-gap:\s*12px/);
  assert.match(stylesSource, /--shell-radius:\s*8px/);
  assert.match(stylesSource, /\.app-shell\s*\{[\s\S]*display:\s*grid;[\s\S]*gap:\s*var\(--shell-gap\)/);
  assert.match(stylesSource, /\.topbar,\n\.workspace\s*\{[\s\S]*border-radius:\s*var\(--shell-radius\)/);
  assert.match(stylesSource, /\.alert-region:empty\s*\{\s*display:\s*none;\s*\}/);
  assert.doesNotMatch(stylesSource, /\.vehicle-bar/);
  assert.doesNotMatch(stylesSource, /border-radius:\s*8px 8px 0 0/);
  assert.doesNotMatch(stylesSource, /border-radius:\s*0 0 8px 8px/);
});

test("summary drawer is callable from desktop and condensed at smaller breakpoints", () => {
  const baseStyles = stylesSource.slice(0, stylesSource.indexOf("@media (max-width: 1120px)"));
  const middleStart = stylesSource.indexOf("@media (max-width: 1120px)");
  const narrowDesktopStart = stylesSource.indexOf("@media (min-width: 761px) and (max-width: 887px)");
  const mobileStart = stylesSource.indexOf("@media (max-width: 760px)");
  const reducedMotionStart = stylesSource.indexOf("@media (prefers-reduced-motion: reduce)");
  const middleBreakpoint = stylesSource.slice(middleStart, narrowDesktopStart);
  const narrowDesktopBreakpoint = stylesSource.slice(narrowDesktopStart, mobileStart);
  const mobileBreakpoint = stylesSource.slice(mobileStart, reducedMotionStart);

  assert.match(baseStyles, /grid-template-columns:\s*240px minmax\(0, 1fr\)/);
  assert.doesNotMatch(baseStyles, /grid-template-columns:\s*240px minmax\(0, 1fr\) 340px/);
  assert.match(baseStyles, /\.toolbar \.mobile-drawer-button-right\s*\{[\s\S]*display:\s*inline-flex/);
  assert.match(baseStyles, /\.reset-icon-button,\n\.download-icon-button\s*\{[\s\S]*width:\s*42px/);
  assert.match(baseStyles, /\.reset-icon,\n\.download-icon\s*\{[\s\S]*stroke-linecap:\s*round/);
  assert.match(baseStyles, /\.toolbar-build-group\s*\{[\s\S]*border-left:\s*1px/);
  assert.match(baseStyles, /\.summary-panel\s*\{[\s\S]*position:\s*fixed;[\s\S]*transform:\s*translateX\(100%\)/);
  assert.match(baseStyles, /\.app-shell\[data-mobile-drawer="summary"\] \.summary-panel\s*\{[\s\S]*transform:\s*none/);
  assert.doesNotMatch(stylesSource, /\.app-shell\[data-mobile-drawer="summary"\] \.summary-panel\s*\{[\s\S]*transform:\s*translateX\(0\)/);
  assert.match(baseStyles, /body:has\(\.app-shell\[data-mobile-drawer\]\)\s*\{[\s\S]*overflow:\s*hidden/);
  assert.match(baseStyles, /\.mobile-drawer-backdrop:not\(\[hidden\]\)/);
  assert.match(middleBreakpoint, /grid-template-columns:\s*180px minmax\(0, 1fr\)/);
  assert.match(middleBreakpoint, /\.toolbar\s*\{[\s\S]*flex-wrap:\s*nowrap/);
  assert.match(middleBreakpoint, /\.toolbar \.mobile-drawer-button-right\s*\{[\s\S]*display:\s*inline-flex/);
  assert.match(middleBreakpoint, /\.summary-drawer-label\s*\{[\s\S]*display:\s*inline/);
  assert.match(narrowDesktopBreakpoint, /grid-template-columns:\s*minmax\(200px, 1fr\) minmax\(0, 360px\)/);
  assert.match(narrowDesktopBreakpoint, /\.toolbar\s*\{[\s\S]*grid-template-columns:\s*1fr/);
  assert.match(narrowDesktopBreakpoint, /\.toolbar-utility-group\s*\{[\s\S]*justify-self:\s*end;[\s\S]*width:\s*auto/);
  assert.match(narrowDesktopBreakpoint, /\.toolbar-build-group\s*\{[\s\S]*grid-template-columns:\s*minmax\(132px, 0\.9fr\) minmax\(158px, 1\.1fr\)/);
  assert.match(narrowDesktopBreakpoint, /\.toolbar button\s*\{[\s\S]*white-space:\s*normal/);
  assert.match(narrowDesktopBreakpoint, /\.toolbar \.mobile-drawer-button-right\s*\{[\s\S]*width:\s*100%/);
  assert.match(middleBreakpoint, /\.mobile-summary-bar\s*\{[\s\S]*display:\s*none/);
  assert.doesNotMatch(middleBreakpoint, /\.step-rail\s*\{[\s\S]*position:\s*fixed/);
  assert.match(mobileBreakpoint, /\.mobile-summary-bar\s*\{[\s\S]*display:\s*grid/);
  assert.match(mobileBreakpoint, /\.toolbar \.mobile-drawer-button-right\s*\{[\s\S]*display:\s*none/);
  assert.match(mobileBreakpoint, /\.mobile-summary-bar\s*\{[\s\S]*grid-template-columns:\s*minmax\(0, 1fr\) auto/);
  assert.match(mobileBreakpoint, /\.mobile-summary-bar > span:last-child\s*\{[\s\S]*white-space:\s*nowrap/);
  assert.match(mobileBreakpoint, /\.mobile-summary-bar > span:last-child\s*\{[\s\S]*width:\s*36px/);
  assert.doesNotMatch(mobileBreakpoint, /\.mobile-summary-bar > span:last-child::after/);
  assert.match(mobileBreakpoint, /\.mobile-progress\[data-has-next="false"\]\s*\{[\s\S]*grid-template-columns:\s*minmax\(0, 1fr\)/);
  assert.match(mobileBreakpoint, /\.toolbar\s*\{[\s\S]*grid-template-columns:\s*42px 42px minmax\(0, 1fr\)/);
  assert.match(mobileBreakpoint, /\.toolbar #downloadBuildButton\s*\{[\s\S]*grid-column:\s*2/);
  assert.match(mobileBreakpoint, /\.toolbar #submitDealerButton\s*\{[\s\S]*grid-column:\s*3/);
  assert.match(mobileBreakpoint, /\.setup-choice-grid,\n\s*\.trim-setup-group \.setup-choice-grid\s*\{[\s\S]*grid-template-columns:\s*1fr/);
  assert.match(mobileBreakpoint, /\.setup-choice-card,\n\s*\.model-choice-card\s*\{[\s\S]*min-width:\s*0/);
  assert.match(mobileBreakpoint, /\.vehicle-setup-stepper\s*\{[\s\S]*display:\s*grid;[\s\S]*grid-template-columns:\s*repeat\(3, minmax\(0, 1fr\)\)/);
  assert.match(mobileBreakpoint, /\.vehicle-setup-chip\s*\{[\s\S]*padding:\s*6px 4px/);
  assert.match(mobileBreakpoint, /\.vehicle-setup-chip em\s*\{[\s\S]*display:\s*none/);
  assert.match(mobileBreakpoint, /\.step-rail\s*\{[\s\S]*position:\s*fixed/);
});

test("summary drawer redirects page wheel scrolling and lets standard equipment tooltips escape", () => {
  const runtime = loadRuntime();
  assert.match(appSource, /document\.addEventListener\?\.\("wheel", handleDrawerWheel, \{ passive: false \}\)/);
  assert.match(appSource, /function handleDrawerWheel/);
  assert.match(appSource, /dataset\?\.mobileDrawer !== "summary"/);
  assert.match(appSource, /summaryDrawer\.scrollTop \+= deltaY/);
  assert.match(appSource, /summaryDrawer\.scrollLeft \+= deltaX/);
  assert.match(appSource, /function tooltipShouldFloat/);
  assert.match(appSource, /tooltipShouldFloat\(trigger\)/);
  assert.match(appSource, /dataset\.floating = "viewport"/);
  assert.match(stylesSource, /\.tooltip-panel\[data-floating="viewport"\]\s*\{[\s\S]*position:\s*fixed;[\s\S]*z-index:\s*120/);
  assert.match(stylesSource, /\.app-shell\[data-mobile-drawer="summary"\] \.summary-panel\s*\{[\s\S]*transform:\s*none/);
  assert.match(appSource, /standard-equipment-summary/);
  assert.doesNotMatch(appSource, /nested-standard-equipment/);
  assert.doesNotMatch(stylesSource, /\.nested-standard-equipment/);

  const summaryDrawer = runtime.elements.get("#summaryDrawer");
  runtime.handleDrawerWheel({ deltaY: 120, deltaX: 7, preventDefault() { this.prevented = true; } });
  assert.equal(summaryDrawer.scrollTop, 0, "closed drawer should not intercept wheel scrolling");
  runtime.setMobileDrawer("summary");
  const event = { deltaY: 120, deltaX: 7, prevented: false, preventDefault() { this.prevented = true; } };
  runtime.handleDrawerWheel(event);
  assert.equal(event.prevented, true);
  assert.equal(summaryDrawer.scrollTop, 120);
  assert.equal(summaryDrawer.scrollLeft, 7);
});

test("mobile progress and compact summary update from runtime state", () => {
  const runtime = loadRuntime();
  runtime.render();

  assert.equal(runtime.elements.get("#mobileStepCount").textContent, "Step 1 of 12");
  assert.equal(runtime.elements.get("#mobileStepName").textContent, "Vehicle Setup");
  assert.equal(runtime.elements.get("#mobilePrevStep").disabled, true);
  assert.equal(runtime.elements.get("#mobilePrevStep").hidden, true);
  assert.equal(runtime.elements.get("#mobileProgress").dataset.hasPrevious, "false");
  assert.equal(runtime.elements.get("#mobileProgress").dataset.hasNext, "true");
  assert.equal(runtime.elements.get("#mobileNextStep").hidden, false);
  assert.equal(runtime.elements.get("#mobileNextStep").disabled, false);
  assert.equal(runtime.elements.get("#mobileNextStep").textContent, "Next");
  assert.equal(runtime.elements.get("#mobileNextStep").title, "Next: Body Style");
  assert.match(runtime.elements.get("#mobileSummaryTotal").textContent, /^\$/);
  assert.match(runtime.elements.get("#mobileSummarySelected").textContent, /selected item/);
  assert.equal(runtime.elements.get("#mobileSummaryMissing").textContent, "›");
  assert.match(runtime.elements.get("#mobileSummaryButton").getAttribute("aria-label"), /View build summary: .*required choices left/);

  runtime.state.activeStep = "paint";
  runtime.render();
  assert.equal(runtime.elements.get("#mobileStepCount").textContent, "Step 2 of 12");
  assert.equal(runtime.elements.get("#mobileStepName").textContent, "Exterior Paint");
  assert.equal(runtime.elements.get("#mobilePrevStep").hidden, false);
  assert.equal(runtime.elements.get("#mobilePrevStep").textContent, "Back");
  assert.equal(runtime.elements.get("#mobilePrevStep").title, "Back: Vehicle Setup");
  assert.equal(runtime.elements.get("#mobileProgress").dataset.hasPrevious, "true");
});

test("vehicle setup exposes paced readability hooks without changing option step content", () => {
  const runtime = loadRuntime();
  runtime.render();

  const setupHtml = runtime.elements.get("#stepContent").innerHTML;
  assert.equal(runtime.elements.get("#stepContent").dataset.activeStep, "model");
  assert.equal(runtime.elements.get("#stepContent").dataset.stepKind, "model");
  assert.match(setupHtml, /vehicle-setup-section/);
  assert.match(setupHtml, /vehicle-setup-stepper compact/);
  assert.doesNotMatch(setupHtml, /role="list"/);
  assert.doesNotMatch(setupHtml, /role="listitem"/);
  assert.match(setupHtml, /<button class="vehicle-setup-chip active" type="button"/);
  assert.doesNotMatch(setupHtml, /vehicle-setup-current/);
  assert.doesNotMatch(setupHtml, /<div class="vehicle-setup-intro">/);
  assert.doesNotMatch(setupHtml, /vehicle-setup-summary/);
  assert.doesNotMatch(setupHtml, /Build starts as/);
  assert.match(setupHtml, /data-setup-chip-state="active"/);
  assert.match(setupHtml, /<h3>Choose your model<\/h3>/);
  assert.doesNotMatch(setupHtml, /<h3>Body Style<\/h3>/);
  assert.doesNotMatch(setupHtml, /<h3>Trim Level<\/h3>/);
  assert.match(setupHtml, /<span class="rpo">Stingray<\/span>/);
  assert.match(setupHtml, /Next-generation LS6 power for the everyday supercar/);
  assert.match(setupHtml, /LS6 6\.7L V8/);
  assert.match(setupHtml, /535 hp \/ 520 lb-ft/);
  assert.match(appSource, /cardSubtitle: "Purist, rear-wheel-drive performance"/);
  assert.match(appSource, /eyebrow: "PURIST, REAR-WHEEL-DRIVE PERFORMANCE"/);
  assert.match(appSource, /The reborn legend, tuned for a pure rear-drive sweet spot/);
  assert.match(appSource, /Available quad center exhaust/);
  assert.match(appSource, /cardSubtitle: "Track-born, street-legal supercar"/);
  assert.match(appSource, /eyebrow: "TRACK-BORN, STREET-LEGAL SUPERCAR"/);
  assert.match(appSource, /The most powerful naturally aspirated V8 ever built/);
  assert.match(appSource, /LT6 5\.5L V8/);
  assert.match(appSource, /670 hp \/ 8,600 rpm/);
  assert.match(appSource, /highlight\.cardSubtitle \|\| highlight\.eyebrow/);
  assert.match(appSource, /When this starting point looks right, continue with/);
  assert.doesNotMatch(appSource, /When this foundation feels right, continue with/);
  assert.doesNotMatch(setupHtml, /Grand Sport X|eAWD|721-hp/);
  assert.match(setupHtml, /Continue to Body Style/);
  assert.doesNotMatch(appSource, /Clear trim path|Same trim path/);
  assert.match(appSource, /Choose trim next/);
  assert.match(appSource, /Power retractable hardtop/);
  assert.doesNotMatch(appSource, /Open Requirements|Build requirements complete/);
  assert.match(htmlSource, /Required Selections/);
  assert.match(appSource, /All required selections are complete/);
  assert.match(setupHtml, /vehicle-setup-next-action/);
  assert.doesNotMatch(setupHtml, /<footer class="step-footer"><button type="button" data-next-step="model">Continue to Body Style/);
  assert.match(stylesSource, /#stepContent\[data-step-kind="model"\] > \.step-header\s*\{[\s\S]*display:\s*none/);
  assert.match(stylesSource, /\.vehicle-setup-stepper\s*\{[\s\S]*display:\s*grid;[\s\S]*grid-template-columns:\s*repeat\(3, minmax\(0, 1fr\)\);[\s\S]*width:\s*100%/);
  assert.doesNotMatch(stylesSource.match(/\.vehicle-setup-stepper\s*\{[\s\S]*?\}/)?.[0] || "", /width:\s*fit-content/);
  assert.match(stylesSource, /\.vehicle-setup-chip\s*\{[\s\S]*justify-self:\s*center;[\s\S]*width:\s*max-content;[\s\S]*max-width:\s*100%;[\s\S]*min-width:\s*0/);
  assert.match(cssBlock(".choice-card"), /outline:\s*2px solid transparent/);
  assert.match(cssBlock(".choice-card"), /outline-offset:\s*3px/);
  assert.match(cssBlock(".choice-card"), /outline-color 140ms ease/);
  assert.match(cssBlock(".choice-card.selected"), /outline-color:\s*var\(--accent\)/);
  assert.doesNotMatch(cssBlock(".choice-card.selected"), /border-color|background-image|box-shadow|inset/);
  assert.match(cssBlock(".choice-card.selected:hover"), /outline-color:\s*var\(--accent-dark\)/);
  assert.doesNotMatch(cssBlock(".choice-card.selected:hover"), /background-image|inset/);
  assert.match(cssBlock(".choice-card.auto"), /outline-color:\s*var\(--ok\)/);
  assert.doesNotMatch(cssBlock(".choice-card.selected.auto"), /background-image|box-shadow|inset/);
  assert.match(cssBlock(".choice-card:focus-visible"), /outline-color:\s*transparent/);
  assert.match(cssBlock(".choice-card:focus-visible"), /box-shadow:\s*0 0 0 3px rgba\(178, 34, 52, 0\.35\)/);
  assert.match(cssBlock(".choice-availability"), /min-height:\s*24px/);
  assert.match(stylesSource, /\.vehicle-setup-equipment-disclosure\s*\{/);
  assert.match(stylesSource, /\.vehicle-setup-next-action\s*\{[\s\S]*justify-content:\s*space-between/);
  assert.doesNotMatch(setupHtml, /Coupe \/ Convertible \| 1LT \/ 2LT \/ 3LT/);
  assert.doesNotMatch(setupHtml, /Available with 1LT, 2LT, 3LT/);
  assert.doesNotMatch(setupHtml, /Corvette Stingray Coupe 1LT 1LT details/);

  runtime.state.bodyStyle = "coupe";
  runtime.state.trimLevel = "1LT";
  runtime.state.vehicleSetupStage = "trim_level";
  runtime.render();
  const trimSetupHtml = runtime.elements.get("#stepContent").innerHTML;
  const trimEquipmentCount = runtime.data.standardEquipment.filter(
    (item) => item.variant_id === "1lt_c07" && item.standard_equipment_group_type === "trim_equipment"
  ).length;
  assert.match(trimSetupHtml, /<h4>1LT is the car for driving purists who want the lightest Corvette possible, but one that&#39;s still very well equipped\.<\/h4>/);
  assert.match(trimSetupHtml, /<p>Trim Level defines your available interior configuration, creature comforts, and safety features\.<\/p>/);
  assert.match(trimSetupHtml, /1LT is the car[\s\S]*Trim Level defines your available interior configuration/);
  assert.match(trimSetupHtml, /Interior configuration/);
  assert.match(trimSetupHtml, /Comfort and technology/);
  assert.match(trimSetupHtml, /Safety features/);
  assert.doesNotMatch(trimSetupHtml, /1LT defines the cabin and included equipment/);
  assert.doesNotMatch(trimSetupHtml, /Included equipment baseline|Interior and technology content|Next: exterior paint/);
  assert.doesNotMatch(trimSetupHtml, /vehicle-setup-layout|vehicle-setup-choices|vehicle-setup-trim-detail/);
  assert.match(trimSetupHtml, /vehicle-setup-highlight compact/);
  assert.match(trimSetupHtml, /Choose the comfort, technology, and interior-content level for your Coupe\./);
  assert.match(trimSetupHtml, /See what this trim includes/);
  assert.match(trimSetupHtml, new RegExp(`${trimEquipmentCount} included items`));
  assert.match(trimSetupHtml, /vehicle-setup-equipment-disclosure/);
  assert.match(trimSetupHtml, /vehicle-setup-equipment-list/);
  assert.doesNotMatch(trimSetupHtml, /vehicle-setup-equipment-body/);
  assert.doesNotMatch(trimSetupHtml, /<details class="standard-group"/);
  assert.match(trimSetupHtml, /vehicle-setup-next-action/);
  assert.doesNotMatch(trimSetupHtml, /<footer class="step-footer"><button type="button" data-next-step="model">Review Vehicle Setup/);
  assert.doesNotMatch(trimSetupHtml, /<details class="vehicle-setup-equipment-disclosure" open/);
  assert.doesNotMatch(trimSetupHtml, /sets the comfort and finish level/);

  runtime.state.vehicleSetupStage = "ready";
  runtime.render();
  const readySetupHtml = runtime.elements.get("#stepContent").innerHTML;
  assert.match(readySetupHtml, /data-setup-stage="trim_level" data-setup-chip-state="complete"/);
  assert.match(readySetupHtml, /<span>✓<\/span>\s*<strong>Trim<\/strong>/);
  assert.doesNotMatch(readySetupHtml, /class="vehicle-setup-chip active" type="button" data-setup-stage="trim_level"/);

  runtime.activateStep("body_style");
  assert.equal(runtime.elements.get("#stepContent").dataset.activeStep, "model");
  assert.equal(runtime.elements.get("#stepContent").dataset.stepKind, "model");
  assert.match(runtime.elements.get("#stepContent").innerHTML, /vehicle-setup-section/);

  runtime.state.activeStep = "paint";
  runtime.render();
  assert.equal(runtime.elements.get("#stepContent").dataset.activeStep, "paint");
  assert.equal(runtime.elements.get("#stepContent").dataset.stepKind, "option");
});

test("card media support is optional and data-driven", () => {
  const runtime = loadRuntime();
  runtime.render();
  assert.doesNotMatch(runtime.elements.get("#stepContent").innerHTML, /choice-media/);
  assert.match(appSource, /function renderCardMedia/);
  assert.match(stylesSource, /\.choice-media\s*\{[\s\S]*aspect-ratio:\s*16 \/ 9/);

  runtime.state.bodyStyle = "coupe";
  runtime.state.trimLevel = "1LT";
  runtime.resetDefaults();
  runtime.reconcileSelections();
  const paint = runtime.activeChoiceRows().find((choice) => choice.step_key === "paint" && choice.selectable === "True");
  assert.ok(paint, "paint choice should exist for synthetic card media test");
  paint.image_url = "./assets/cards/black&trim.webp";
  paint.image_alt = "Black \"paint\" preview";
  paint.image_fit = "contain";
  paint.image_position = "50% 40%";

  runtime.state.activeStep = "paint";
  runtime.render();
  let html = runtime.elements.get("#stepContent").innerHTML;
  assert.match(html, /class="choice-card has-media/);
  assert.match(html, /<span class="choice-media" data-fit="contain">/);
  assert.match(html, /src="\.\/assets\/cards\/black&amp;trim\.webp"/);
  assert.match(html, /alt="Black &quot;paint&quot; preview"/);
  assert.match(html, /object-position: 50% 40%;/);

  paint.image_fit = "stretch";
  paint.image_position = "url(javascript:bad)";
  runtime.render();
  html = runtime.elements.get("#stepContent").innerHTML;
  assert.match(html, /<span class="choice-media" data-fit="cover">/);
  assert.match(html, /object-position: center;/);
});

test("choice cards reserve availability slot and move disabled reason into tooltip pill", () => {
  const runtime = loadRuntime();
  runtime.state.bodyStyle = "coupe";
  runtime.state.trimLevel = "1LT";
  runtime.resetDefaults();
  runtime.reconcileSelections();
  const paint = runtime.activeChoiceRows().find((choice) => choice.step_key === "paint" && choice.selectable === "True");
  assert.ok(paint, "paint choice should exist for availability-slot test");
  const mediaPaint = {
    ...paint,
    image_url: "./assets/cards/availability-test.webp",
    image_alt: "Availability test image",
  };

  const availableHtml = runtime.renderChoiceCard(mediaPaint, new Map());
  assert.match(availableHtml, /<div class="choice-availability"><\/div>/);
  assert.doesNotMatch(availableHtml, /choice-state disabled-reason/);
  assert.match(availableHtml, /<span class="choice-media" data-fit="cover">/);
  assert.doesNotMatch(availableHtml, /choice-media disabled/);

  const unavailableHtml = runtime.renderChoiceCard({ ...mediaPaint, status: "unavailable" }, new Map());
  assert.match(unavailableHtml, /<div class="choice-availability">[\s\S]*choice-state disabled-reason info-tooltip/);
  assert.match(unavailableHtml, /tooltip-panel" role="tooltip">Not available for this body and trim\./);
  assert.doesNotMatch(unavailableHtml, /<p class="disabled-reason"/);
  assert.match(unavailableHtml, /choice-media disabled/);

  const autoHtml = runtime.renderChoiceCard(mediaPaint, new Map([[mediaPaint.option_id, "Included with package."]]));
  assert.match(autoHtml, /aria-disabled="true"/);
  assert.match(autoHtml, /<span class="choice-media" data-fit="cover">/);
  assert.doesNotMatch(autoHtml, /choice-media disabled/);
  assert.match(autoHtml, /<div class="choice-availability">[\s\S]*choice-state auto-reason info-tooltip/);
});

test("tooltips use mobile-safe touch handlers without selecting parent cards", () => {
  assert.match(appSource, /function toggleTooltip\(trigger, event\)/);
  assert.match(appSource, /trigger\.addEventListener\("pointerup"/);
  assert.match(appSource, /trigger\.addEventListener\("touchend"/);
  assert.match(appSource, /event\?\.stopPropagation\?\.\(\)/);
  assert.match(appSource, /function tooltipShouldFloat\(trigger\)/);
  assert.match(appSource, /isMobileViewport\(\)/);
  assert.match(appSource, /function recentlyHandledAnyTooltipTouch\(\)/);
  assert.match(appSource, /function stopEventAfterTooltipTouch\(event\)/);
  assert.match(appSource, /document\.addEventListener\("click", \(event\) => \{\n\s*if \(stopEventAfterTooltipTouch\(event\)\) return;/);
  assert.match(appSource, /button\.addEventListener\("click", \(event\) => \{\n\s*if \(stopEventAfterTooltipTouch\(event\)\) return;\n\s*const choice = activeChoiceRows/);
  assert.match(stylesSource, /\.info-tooltip\s*\{[\s\S]*touch-action:\s*manipulation/);
  assert.match(stylesSource, /\.tooltip-panel\[data-floating="viewport"\]/);
});

test("mobile drawers expose route and summary state without changing form logic", () => {
  const runtime = loadRuntime();
  runtime.render();

  runtime.setMobileDrawer("steps");
  assert.equal(runtime.elements.get(".app-shell").dataset.mobileDrawer, "steps");
  assert.equal(runtime.elements.get("#mobileDrawerBackdrop").hidden, false);
  assert.equal(runtime.elements.get("#openStepDrawerButton").getAttribute("aria-expanded"), "true");

  runtime.activateStep("trim_level", { closeDrawer: true });
  assert.equal(runtime.state.activeStep, "model");
  assert.equal(runtime.elements.get(".app-shell").dataset.mobileDrawer, undefined);
  assert.equal(runtime.elements.get("#mobileDrawerBackdrop").hidden, true);

  runtime.setMobileDrawer("summary");
  assert.equal(runtime.elements.get(".app-shell").dataset.mobileDrawer, "summary");
  assert.equal(runtime.elements.get("#openSummaryDrawerButton").getAttribute("aria-expanded"), "true");
  assert.equal(runtime.elements.get("#mobileSummaryButton").getAttribute("aria-expanded"), "true");
  assert.equal(runtime.elements.get("#openSummaryDrawerButton").getAttribute("aria-label"), "Hide build summary");
  assert.equal(runtime.elements.get("#mobileSummaryButton").getAttribute("aria-label"), "Hide build summary");
  runtime.closeMobileDrawers();
  assert.equal(runtime.elements.get(".app-shell").dataset.mobileDrawer, undefined);
  assert.equal(runtime.elements.get("#openSummaryDrawerButton").getAttribute("aria-label"), "View build summary");
  assert.equal(runtime.elements.get("#mobileSummaryButton").getAttribute("aria-label"), "View build summary");
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
  assert.match(appSource, /const mediaDisabled = Boolean\(disabledReason\)/);
  assert.match(appSource, /renderCardMedia\(choice, choice\.label, \{ disabled: mediaDisabled \}\)/);
  assert.match(appSource, /aria-disabled=\\"true\\"/);
  assert.doesNotMatch(appSource, /data-option="\$\{choice\.option_id\}" \$\{disabled \? "aria-disabled=\\"true\\" disabled"/);
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
  const autoByRpo = new Map(order.auto_added_options.map((item) => [item.rpo, item]));
  assert.equal(autoByRpo.get("FE3")?.section_key, "performance_mechanical", "non-included auto-added FE3 should recap in its normal section");
  assert.equal(autoByRpo.get("T0A")?.section_key, "performance_mechanical", "non-included auto-added T0A should recap in its normal section");
  assert.equal(autoByRpo.get("G0K")?.section_key, "auto_added_required", "sec_incl auto-added package rows should stay in Auto-Added / Required");
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
  assert.deepEqual(
    JSON.parse(JSON.stringify(data.orderSummary.sections.map((section) => [section.section_key, section.section_label]))),
    [
      ["vehicle", "Model"],
      ["exterior_paint", "Exterior Paint"],
      ["exterior_appearance", "Exterior Appearance"],
      ["wheels_brakes", "Wheels & Brakes"],
      ["performance_mechanical", "Performance & Mechanical"],
      ["stripes", "Stripes"],
      ["seats_interior", "Seats & Interior"],
      ["accessories", "Accessories"],
      ["delivery", "Delivery"],
      ["auto_added_required", "Auto-Added / Required"],
      ["pricing_summary", "Pricing Summary"],
    ]
  );
  assert.equal(data.orderSummary.stepMap.paint, "exterior_paint");
  assert.equal(data.orderSummary.stepMap.base_interior, "seats_interior");
  const sectionLabels = order.sections.map((section) => section.section_label);
  assert.deepEqual(JSON.parse(JSON.stringify(sectionLabels)), [
    "Model",
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
  const pcx = runtime.activeChoiceRows().find((choice) => choice.option_id === "opt_pcx_001");
  const paint = runtime.activeChoiceRows().find((choice) => choice.option_id === "opt_gba_001");
  assert.ok(z51, "Z51 should exist for the current variant");
  assert.ok(pcx, "PCX should exist for the current variant");
  assert.ok(paint, "Black paint should exist for the current variant");
  runtime.handleChoice(paint);
  runtime.handleChoice(z51);
  runtime.handleChoice(pcx);
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
  const performanceSection = compact.sections.find((section) => section.section === "Performance & Mechanical");
  assert.ok(performanceSection.items.some((item) => item.rpo === "FE3"), "auto-added FE3 should be grouped with performance content");
  assert.ok(performanceSection.items.some((item) => item.rpo === "T0A"), "auto-added T0A should be grouped with performance content");
  const accessoriesSection = compact.sections.find((section) => section.section === "Accessories");
  assert.ok(accessoriesSection.items.some((item) => item.rpo === "5DG"), "PCX auto-added 5DG should be grouped with accessories");
  assert.ok(accessoriesSection.items.some((item) => item.rpo === "SFZ"), "PCX auto-added SFZ should be grouped with accessories");
  const stripesSection = compact.sections.find((section) => section.section === "Stripes");
  assert.ok(stripesSection.items.some((item) => item.rpo === "SHT"), "PCX auto-added SHT should be grouped with stripes");
  assert.ok(stripesSection.items.some((item) => item.rpo === "SNG"), "PCX auto-added SNG should be grouped with stripes");
  const autoSection = compact.sections.find((section) => section.section === "Auto-Added / Required");
  assert.ok(autoSection.items.some((item) => item.rpo === "G0K"), "sec_incl auto-added package rows should remain grouped as required");
  assert.equal(autoSection.items.some((item) => item.rpo === "FE3"), false, "non-included auto-added FE3 should not remain in Auto-Added / Required");
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

test("final step mirrors customer action buttons", () => {
  assert.match(appSource, /function renderFinalStepActions/);
  assert.match(appSource, /data-final-download/);
  assert.match(appSource, /data-final-submit/);
  assert.match(appSource, /querySelector\("\[data-final-download\]"\)\?\.addEventListener\("click", downloadBuild\)/);
  assert.match(appSource, /querySelector\("\[data-final-submit\]"\)\?\.addEventListener\("click", openDealerSubmitModal\)/);

  const runtime = loadRuntime();
  runtime.state.bodyStyle = "coupe";
  runtime.state.trimLevel = "1LT";
  runtime.resetDefaults();
  runtime.reconcileSelections();
  runtime.state.activeStep = "delivery";
  runtime.render();

  const stepContent = runtime.elements.get("#stepContent").innerHTML;
  assert.match(stepContent, /class="step-footer final-step-actions"/);
  assert.match(stepContent, /data-final-download disabled title="Complete required selections before downloading your build\."/);
  assert.match(stepContent, /data-final-submit disabled title="Complete required selections before submitting your build\."/);
  assert.doesNotMatch(stepContent, /data-next-step/);

  const paint = runtime.activeChoiceRows().find((choice) => choice.option_id === "opt_gba_001");
  runtime.handleChoice(paint);
  runtime.state.selectedInterior = "1LT_AQ9_HTA";
  runtime.reconcileSelections();
  runtime.state.activeStep = "delivery";
  runtime.render();

  const completedStepContent = runtime.elements.get("#stepContent").innerHTML;
  assert.match(completedStepContent, /data-final-download\s+ title="">Download Build<\/button>/);
  assert.match(completedStepContent, /data-final-submit\s+ title="">Submit to Dealer<\/button>/);
  assert.doesNotMatch(completedStepContent, /data-final-download disabled/);
  assert.doesNotMatch(completedStepContent, /data-final-submit disabled/);
});

test("submit to dealer modal posts a validated dealer payload", async () => {
  assert.match(htmlSource, /id="submitDealerButton"[\s\S]*Submit to Dealer/);
  assert.match(htmlSource, /id="dealerSubmitModal"/);
  assert.match(htmlSource, /id="dealerSubmitCloseButton"[\s\S]*aria-label="Close dealer submission"[\s\S]*>×<\/button>/);
  assert.match(htmlSource, /Name <span class="required-mark" aria-hidden="true">\*<\/span>/);
  assert.match(htmlSource, /Email <span class="required-mark" aria-hidden="true">\*<\/span>/);
  assert.match(htmlSource, /https:\/\/challenges\.cloudflare\.com\/turnstile\/v0\/api\.js/);
  assert.match(htmlSource, /id="dealerTurnstile"/);
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
  assert.equal(runtime.turnstileCalls.some((call) => call.fn === "render" && call.selector === "#dealerTurnstile"), true);
  assert.equal(
    runtime.elements.get("#dealerSubmitStatus").textContent,
    "Form will be submitted to Stingray Chevrolet in Plant City, FL."
  );
  assert.equal(await runtime.submitDealerBuild(), null, "name and email should be required");
  assert.match(runtime.elements.get("#dealerSubmitStatus").textContent, /Name is required/);
  assert.equal(runtime.fetchCalls.length, 0, "invalid submission should not call the endpoint");

  runtime.elements.get("#dealerSubmitName").value = "Ada Buyer";
  runtime.elements.get("#dealerSubmitEmail").value = "ada@example.com";
  runtime.elements.get("#dealerSubmitPhone").value = "555-0100";
  runtime.elements.get("#dealerSubmitComments").value = "Please contact me about this build.";
  runtime.setTurnstileToken("test-turnstile-token");
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
  assert.deepEqual(Object.keys(postedBody), ["model", "customer", "vehicle", "sections", "msrp", "plain_text_summary", "turnstile_token"]);
  assert.equal(postedBody.turnstile_token, "test-turnstile-token");
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

test("submit to dealer modal requires a Turnstile token before posting", async () => {
  const runtime = loadRuntime();
  runtime.state.bodyStyle = "coupe";
  runtime.state.trimLevel = "1LT";
  runtime.resetDefaults();
  runtime.reconcileSelections();
  runtime.handleChoice(runtime.activeChoiceRows().find((choice) => choice.option_id === "opt_gba_001"));
  runtime.state.selectedInterior = "1LT_AQ9_HTA";
  runtime.reconcileSelections();
  runtime.openDealerSubmitModal();
  runtime.setTurnstileToken("");
  runtime.elements.get("#dealerSubmitName").value = "Ada Buyer";
  runtime.elements.get("#dealerSubmitEmail").value = "ada@example.com";

  assert.equal(await runtime.submitDealerBuild(), null, "missing Turnstile token should block submission");
  assert.equal(runtime.fetchCalls.length, 0);
  assert.match(runtime.elements.get("#dealerSubmitStatus").textContent, /Security check is required/);
  assert.equal(runtime.turnstileCalls.some((call) => call.fn === "reset"), true);
});

test("submit to dealer modal renders Turnstile when the async API arrives after opening", async () => {
  const runtime = loadRuntime({ turnstileAvailable: false });
  runtime.state.bodyStyle = "coupe";
  runtime.state.trimLevel = "1LT";
  runtime.resetDefaults();
  runtime.reconcileSelections();
  runtime.handleChoice(runtime.activeChoiceRows().find((choice) => choice.option_id === "opt_gba_001"));
  runtime.state.selectedInterior = "1LT_AQ9_HTA";
  runtime.reconcileSelections();
  runtime.openDealerSubmitModal();
  assert.equal(runtime.elements.get("#dealerSubmitModal").hidden, false);
  assert.equal(runtime.turnstileCalls.length, 0, "modal open should not render before Turnstile is available");

  runtime.setWindowTurnstile();
  runtime.elements.get("#dealerSubmitName").value = "Ada Buyer";
  runtime.elements.get("#dealerSubmitEmail").value = "ada@example.com";
  const submission = await runtime.submitDealerBuild();

  assert.equal(runtime.turnstileCalls.some((call) => call.fn === "render" && call.selector === "#dealerTurnstile"), true);
  assert.equal(runtime.fetchCalls.length, 1);
  assert.equal(submission.payload.turnstile_token, "test-turnstile-token");
});

test("Stingray workbook option placement keeps VK3 and BV4 in customer-facing sections", () => {
  const vk3 = uniqueChoicesByRpo("VK3")[0];
  const bv4 = uniqueChoicesByRpo("BV4")[0];
  assert.ok(vk3, "VK3 should exist");
  assert.ok(bv4, "BV4 should exist");
  assert.equal(vk3.section_id, "sec_lpoe_001");
  assert.equal(vk3.section_name, "LPO Exterior");
  assert.equal(vk3.step_key, "accessories");
  assert.equal(bv4.section_id, "sec_cust_001");
  assert.equal(bv4.section_name, "Custom Delivery");
  assert.equal(bv4.step_key, "delivery");
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
  assert.equal(runtime.state.activeStep, "model");
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
  assert.match(summary, /^<p><strong>Name:<\/strong> Ada Buyer<br><strong>Email:<\/strong> ada@example\.com<br><strong>Phone:<\/strong> 555-0100/);
  assert.doesNotMatch(summary, /<strong>Address:<\/strong>/);
  assert.match(summary, /<strong>Comments:<\/strong> Dealer follow-up requested\./);
  assert.match(summary, /<strong>Submitted:<\/strong> .+/);
  assert.match(summary, /<p><strong><u>Variant<\/u><\/strong><\/p><ul><li>Corvette Stingray Coupe 1LT<\/li><\/ul>/);
  assert.doesNotMatch(summary, /Variant<\/u><\/strong><\/p><ul><li>coupe<\/li><li>1LT/);
  assert.doesNotMatch(summary, /Base MSRP/);
  assert.match(summary, /<p><strong><u>Exterior Paint<\/u><\/strong><\/p><ul><li>GBA Black: \$0<\/li>/);
  assert.match(summary, /<p><strong><u>Seats &amp; Interior<\/u><\/strong><\/p><ul>[\s\S]*<li>AQ9 GT1 Bucket Seats: \$0<\/li>[\s\S]*<li>HTA Jet Black: \$0<\/li>/);
  assert.match(summary, /<p><strong><u>Performance &amp; Mechanical<\/u><\/strong><\/p><ul>[\s\S]*<li>FE3 Z51 Performance Suspension: \$0<\/li>/);
  assert.match(summary, /<p><strong><u>Auto-Added \/ Required<\/u><\/strong><\/p><ul>[\s\S]*<li>G0K Rear Axle 5\.56 Ratio: \$0<\/li>/);
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
    ["3LT_R6X_AE4_HUU", [{ rpo: "R6X", label: "Custom Interior Trim and Seat Combination", price: 995, component_type: "r6x" }]],
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

test("R6X component order output uses PriceRef pricing and D30 does not alter it", () => {
  const ah2Runtime = configureInteriorOrder({ trimLevel: "3LT", interiorId: "3LT_R6X_AH2_HUU", seatRpo: "AH2" });
  assert.ok(
    compactSeatInteriorItems(ah2Runtime).some((item) => item.rpo === "R6X" && item.label === "Custom Interior Trim and Seat Combination" && item.price === 995),
    "3LT R6X AH2 should show R6X at $995"
  );

  const ae4Runtime = configureInteriorOrder({ trimLevel: "3LT", interiorId: "3LT_R6X_AE4_HUU", seatRpo: "AE4" });
  assert.ok(
    compactSeatInteriorItems(ae4Runtime).some((item) => item.rpo === "R6X" && item.label === "Custom Interior Trim and Seat Combination" && item.price === 995),
    "3LT R6X AE4 should show R6X at its flat $995 PriceRef component price"
  );

  const d30Runtime = configureInteriorOrder({
    trimLevel: "3LT",
    interiorId: "3LT_R6X_AH2_HZP_N26",
    seatRpo: "AH2",
    selectedOptionIds: ["opt_g26_001"],
  });
  assert.equal(d30Runtime.computeAutoAdded().has("opt_d30_001"), true, "D30 should be triggered by selected color/interior context");
  assert.ok(
    compactSeatInteriorItems(d30Runtime).some((item) => item.rpo === "R6X" && item.label === "Custom Interior Trim and Seat Combination" && item.price === 995),
    "D30-triggered R6X should remain visible at its PriceRef component price"
  );
});

test("order summary helpers are exposed for browser debug inspection", () => {
  assert.match(appSource, /window\.__orderDebug\s*=\s*\{[\s\S]*currentOrder,[\s\S]*compactOrder,[\s\S]*plainTextOrderSummary,[\s\S]*buildMarkdown,[\s\S]*\}/);
});

test("runtime defaults and RPO exceptions are workbook-generated metadata", () => {
  assert.deepEqual(
    JSON.parse(JSON.stringify(data.defaultSelectionRules.map((rule) => rule.rule_id).sort())),
    ["default_719", "default_bc7", "default_fe1", "default_nga"]
  );
  assert.deepEqual(
    JSON.parse(JSON.stringify(data.runtimeRuleExceptions.map((exception) => exception.exception_id).sort())),
    []
  );
  assert.equal(data.runtimeRuleExceptions.length, 0, "Stingray runtime-rule exception sheet should no longer own active behavior");
  assert.equal(
    data.runtimeRuleExceptions.some((exception) => exception.exception_id === "ex_gba_zyc"),
    false,
    "Stingray GBA/ZYC conflict should be owned by grouped exclusion metadata"
  );
  assert.equal(
    data.runtimeRuleExceptions.some((exception) => exception.exception_id === "ex_nwi_nga"),
    false,
    "Stingray NGA/NWI replacement should be owned by the exhaust exclusive group plus NGA default metadata"
  );
  const exhaustGroup = data.exclusiveGroups.find((group) => group.group_id === "excl_exhaust_path");
  assert.ok(exhaustGroup, "Stingray NGA/NWI exhaust peer group should be generated");
  assert.equal(exhaustGroup.selection_mode, "required_single_within_group");
  assert.deepEqual(JSON.parse(JSON.stringify(exhaustGroup.option_ids)), ["opt_nga_001", "opt_nwi_001"]);
  assert.equal(exhaustGroup.option_ids.includes("opt_wub_001"), false, "WUB enables NWI but should not be an exhaust-tip peer");
  assert.ok(
    data.rules.some((rule) => rule.source_id === "opt_nwi_001" && rule.target_id === "opt_wub_001" && rule.rule_type === "requires"),
    "NWI should keep its WUB prerequisite after ex_nwi_nga retirement"
  );
  const gbaZycGroup = data.ruleGroups.find((group) => group.group_id === "grp_gba_excludes_zyc");
  assert.ok(gbaZycGroup, "Stingray GBA/ZYC conflict should be generated as a grouped exclusion");
  assert.equal(gbaZycGroup.source_id, "opt_gba_001");
  assert.equal(gbaZycGroup.group_type, "excludes_any");
  assert.deepEqual(JSON.parse(JSON.stringify(gbaZycGroup.target_ids)), ["opt_zyc_001"]);
  assert.equal(gbaZycGroup.disabled_reason, "ZYC Carbon Flash painted mirrors and spoiler package is not available with Black exterior paint.");
  assert.equal(
    data.rules.some((rule) => rule.rule_id === "rule_opt_zyc_001_excludes_opt_gba_001"),
    false,
    "Reverse ZYC -> GBA direct rule should not remain after GBA -> ZYC grouped ownership"
  );
  assert.ok(
    data.rules.some((rule) => rule.rule_id === "rule_opt_zyc_001_includes_opt_drg_001"),
    "ZYC should keep its DRG include rule after GBA/ZYC conflict migration"
  );
  const fe1Default = data.defaultSelectionRules.find((rule) => rule.rule_id === "default_fe1");
  assert.equal(fe1Default.condition_type, "unless_selected_section");
  assert.equal(fe1Default.condition_id, "sec_susp_001");
  const z51ExcludesFe1 = data.rules.find((rule) => rule.rule_id === "rule_opt_z51_001_excludes_opt_fe1_001");
  assert.ok(z51ExcludesFe1, "Z51 should remove FE1 through workbook-owned direct rule metadata");
  assert.equal(z51ExcludesFe1.source_id, "opt_z51_001");
  assert.equal(z51ExcludesFe1.target_id, "opt_fe1_001");
  assert.equal(z51ExcludesFe1.rule_type, "excludes");
  assert.equal(z51ExcludesFe1.runtime_action, "replace");
  assert.equal(z51ExcludesFe1.disabled_reason, "Replaced by FE3 Z51 performance suspension.");
  const z51ExcludesFe2 = data.rules.find((rule) => rule.rule_id === "rule_opt_z51_001_excludes_opt_fe2_001");
  assert.ok(z51ExcludesFe2, "Z51 should remove FE2 through workbook-owned direct rule metadata");
  assert.equal(z51ExcludesFe2.source_id, "opt_z51_001");
  assert.equal(z51ExcludesFe2.target_id, "opt_fe2_001");
  assert.equal(z51ExcludesFe2.rule_type, "excludes");
  assert.equal(z51ExcludesFe2.runtime_action, "replace");
  assert.equal(z51ExcludesFe2.disabled_reason, "Not available with Z51 Performance Package.");
  assert.equal(
    data.rules.some((rule) => rule.rule_id === "rule_opt_fe2_001_excludes_opt_z51_001"),
    false,
    "Reverse FE2 -> Z51 rule should not remain after Z51-owned suspension exclusion migration"
  );
  assert.equal(
    data.ruleGroups.some((group) => (group.target_ids || []).some((id) => ["opt_fe1_001", "opt_fe2_001", "opt_fe3_001", "opt_fe4_001"].includes(id))),
    false,
    "Pass 15 should not introduce suspension rule groups"
  );
  assert.equal(
    data.exclusiveGroups.some((group) => (group.option_ids || []).some((id) => ["opt_fe1_001", "opt_fe2_001", "opt_fe3_001", "opt_fe4_001"].includes(id))),
    false,
    "Pass 15 should not introduce suspension exclusive groups"
  );
  assert.doesNotMatch(appSource, /for \(const defaultRpo of \["FE1", "NGA", "BC7"\]\)/);
  assert.doesNotMatch(appSource, /deleteSelectedRpo\("FE1"\)/);
  assert.doesNotMatch(appSource, /deleteSelectedRpo\("FE2"\)/);
  assert.doesNotMatch(appSource, /deleteSelectedRpo\("NGA"\)/);
  assert.doesNotMatch(appSource, /if \(choice\.rpo === "GBA"\) deleteSelectedRpo\("ZYC"\)/);
  assert.doesNotMatch(appSource, /choice\.rpo\s*===\s*["']GBA["']/);
  assert.doesNotMatch(appSource, /rule\.source_id\s*===\s*["']opt_zyc_001["']/);
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
});

test("GBA replaces selected ZYC through workbook-owned grouped exclusion metadata", () => {
  const runtime = loadRuntime();
  runtime.state.bodyStyle = "coupe";
  runtime.state.trimLevel = "1LT";
  runtime.resetDefaults();
  runtime.reconcileSelections();

  const gba = runtime.activeChoiceRows().find((choice) => choice.option_id === "opt_gba_001");
  const zyc = runtime.activeChoiceRows().find((choice) => choice.option_id === "opt_zyc_001");
  assert.ok(gba, "GBA should exist for the current variant");
  assert.ok(zyc, "ZYC should exist for the current variant");

  runtime.state.selected.add(zyc.option_id);
  runtime.state.userSelected.add(zyc.option_id);
  assert.equal(runtime.disableReasonForChoice(gba), "", "GBA should stay selectable while ZYC is selected");

  runtime.handleChoice(gba);
  runtime.reconcileSelections();
  assert.equal(runtime.state.selected.has(gba.option_id), true, "GBA should be selected");
  assert.equal(runtime.state.selected.has(zyc.option_id), false, "ZYC should be removed by runtime exception metadata");
  assert.equal(runtime.state.userSelected.has(zyc.option_id), false, "ZYC should be removed from user selections");

  assert.match(runtime.disableReasonForChoice(zyc), /ZYC Carbon Flash painted mirrors and spoiler package is not available with Black exterior paint/i);
  runtime.handleChoice(zyc);
  runtime.reconcileSelections();
  assert.equal(runtime.state.selected.has(zyc.option_id), false, "ZYC should not stick while GBA is selected");

  const nonGbaRuntime = loadRuntime();
  nonGbaRuntime.state.bodyStyle = "coupe";
  nonGbaRuntime.state.trimLevel = "1LT";
  nonGbaRuntime.resetDefaults();
  nonGbaRuntime.reconcileSelections();
  const zycWithoutGba = nonGbaRuntime.activeChoiceRows().find((choice) => choice.option_id === "opt_zyc_001");
  assert.equal(nonGbaRuntime.disableReasonForChoice(zycWithoutGba), "", "ZYC should remain selectable without GBA selected");
  nonGbaRuntime.handleChoice(zycWithoutGba);
  nonGbaRuntime.reconcileSelections();
  assert.equal(nonGbaRuntime.state.selected.has("opt_zyc_001"), true, "ZYC should remain selected on a non-GBA path");
  assert.equal(nonGbaRuntime.computeAutoAdded().has("opt_drg_001"), true, "ZYC should still include DRG after conflict migration");
});

test("FE3 disabled tile explains that Z51 includes it without duplicating the RPO", () => {
  const runtime = loadRuntime();
  runtime.state.bodyStyle = "coupe";
  runtime.state.trimLevel = "1LT";

  const fe3 = runtime.activeChoiceRows().find((choice) => choice.option_id === "opt_fe3_001");
  assert.ok(fe3, "FE3 should exist for the current variant");
  assert.equal(runtime.disableReasonForChoice(fe3), "Included with Z51 Performance Package.");

  const fe4 = runtime.activeChoiceRows().find((choice) => choice.option_id === "opt_fe4_001");
  assert.ok(fe4, "FE4 should exist for the current variant");
  assert.equal(runtime.disableReasonForChoice(fe4), "Requires Z51 Performance Package.");

  const t0a = runtime.activeChoiceRows().find((choice) => choice.option_id === "opt_t0a_001");
  assert.ok(t0a, "T0A should exist for the current variant");
  assert.equal(runtime.disableReasonForChoice(t0a), "Requires Z51 Performance Package.");

  const z51 = runtime.activeChoiceRows().find((choice) => choice.option_id === "opt_z51_001");
  assert.ok(z51, "Z51 should exist for the current variant");
  runtime.handleChoice(z51);
  assert.equal(runtime.computeAutoAdded().get("opt_fe3_001"), "Included with Z51 Performance Package.");
});

test("ZF1 requires Z51, replaces T0A, and is auto-added by high wing spoilers only with Z51", () => {
  for (const sourceId of ["opt_5zz_001", "opt_5zu_001", "opt_5zw_001"]) {
    const rule = data.rules.find((item) => item.source_id === sourceId && item.target_id === "opt_zf1_001");
    assert.ok(rule, `${sourceId} should include ZF1`);
    assert.equal(rule.rule_type, "includes");
    assert.equal(rule.auto_add, "True");
  }

  const zf1RequiresZ51 = data.rules.find((rule) => rule.source_id === "opt_zf1_001" && rule.target_id === "opt_z51_001");
  assert.ok(zf1RequiresZ51, "ZF1 should require Z51");
  assert.equal(zf1RequiresZ51.rule_type, "requires");

  const zf1ReplacesT0a = data.rules.find((rule) => rule.source_id === "opt_zf1_001" && rule.target_id === "opt_t0a_001");
  assert.ok(zf1ReplacesT0a, "ZF1 should remove T0A");
  assert.equal(zf1ReplacesT0a.runtime_action, "replace");

  const runtime = loadRuntime();
  runtime.state.bodyStyle = "coupe";
  runtime.state.trimLevel = "1LT";
  runtime.resetDefaults();
  runtime.reconcileSelections();

  const zf1 = runtime.activeChoiceRows().find((choice) => choice.option_id === "opt_zf1_001");
  const z51 = runtime.activeChoiceRows().find((choice) => choice.option_id === "opt_z51_001");
  const fiveZz = runtime.activeChoiceRows().find((choice) => choice.option_id === "opt_5zz_001");
  assert.ok(zf1, "ZF1 should exist for the current variant");
  assert.ok(z51, "Z51 should exist for the current variant");
  assert.ok(fiveZz, "5ZZ should exist for the current variant");

  assert.equal(runtime.disableReasonForChoice(zf1), "Requires Z51 Performance Package.");

  runtime.handleChoice(fiveZz);
  assert.equal(runtime.computeAutoAdded().has("opt_zf1_001"), false, "5ZZ should not auto-add ZF1 without Z51");

  runtime.handleChoice(z51);
  assert.equal(runtime.disableReasonForChoice(zf1), "");
  assert.equal(runtime.computeAutoAdded().get("opt_zf1_001"), "Included with 5ZZ Carbon Flash Metallic High Wing Spoiler.");
  assert.equal(runtime.computeAutoAdded().has("opt_t0a_001"), false, "5ZZ should replace the Z51 T0A default");

  const manualRuntime = loadRuntime();
  manualRuntime.state.bodyStyle = "coupe";
  manualRuntime.state.trimLevel = "1LT";
  manualRuntime.resetDefaults();
  manualRuntime.reconcileSelections();
  manualRuntime.handleChoice(manualRuntime.activeChoiceRows().find((choice) => choice.option_id === "opt_z51_001"));
  manualRuntime.handleChoice(manualRuntime.activeChoiceRows().find((choice) => choice.option_id === "opt_zf1_001"));
  assert.equal(manualRuntime.state.selected.has("opt_zf1_001"), true, "ZF1 should be manually selectable once Z51 is selected");
  assert.equal(manualRuntime.computeAutoAdded().has("opt_t0a_001"), false, "selected ZF1 should keep T0A removed");
});

test("FE1 default selection prefers the visible suspension tile", () => {
  const fe1Rows = data.choices.filter((choice) => choice.variant_id === "1lt_c07" && choice.rpo === "FE1");
  assert.ok(
    fe1Rows.some((choice) => choice.option_id === "opt_fe1_001" && choice.section_id === "sec_susp_001" && choice.selectable === "True"),
    "FE1 should have a visible selectable suspension choice"
  );
  assert.equal(
    fe1Rows.some((choice) => choice.option_id === "opt_fe1_002"),
    false,
    "FE1 standard-equipment mirror should no longer be emitted"
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
  const fe1 = runtime.activeChoiceRows().find((choice) => choice.option_id === "opt_fe1_001");
  assert.equal(runtime.disableReasonForChoice(fe1), "Replaced by FE3 Z51 performance suspension.");
  runtime.handleChoice(fe1);
  runtime.reconcileSelections();
  assert.equal(runtime.state.selected.has("opt_fe1_001"), false, "FE1 should not be selectable while Z51 is selected");

  runtime.handleChoice(z51);
  runtime.reconcileSelections();
  assert.equal(runtime.state.selected.has("opt_z51_001"), false, "Z51 should be removable from the selected package path");
  assert.equal(runtime.computeAutoAdded().has("opt_fe3_001"), false, "Removing Z51 should remove FE3 auto-add");
  assert.equal(runtime.state.selected.has("opt_fe1_001"), true, "FE1 default should restore after Z51 is removed");

  const fe2Runtime = loadRuntime();
  fe2Runtime.state.bodyStyle = "coupe";
  fe2Runtime.state.trimLevel = "1LT";
  fe2Runtime.resetDefaults();
  fe2Runtime.reconcileSelections();
  const fe2Z51 = fe2Runtime.activeChoiceRows().find((choice) => choice.option_id === "opt_z51_001");
  const fe2 = fe2Runtime.activeChoiceRows().find((choice) => choice.option_id === "opt_fe2_001");
  fe2Runtime.handleChoice(fe2);
  const fe2SelectedRpos = [...fe2Runtime.state.selected].map((id) => data.choices.find((choice) => choice.option_id === id)?.rpo);
  assert.equal(fe2SelectedRpos.includes("FE2"), true, "FE2 should remain selected");
  assert.equal(fe2SelectedRpos.includes("FE1"), false, "FE2 should suppress the FE1 default");
  assert.equal(fe2Runtime.disableReasonForChoice(fe2Z51), "", "Z51 should stay selectable after FE2 is selected");
  fe2Runtime.handleChoice(fe2Z51);
  fe2Runtime.reconcileSelections();
  assert.equal(fe2Runtime.state.selected.has("opt_z51_001"), true, "Z51 should be selectable after FE2");
  assert.equal(fe2Runtime.state.selected.has("opt_fe2_001"), false, "Z51 should remove FE2");
  assert.equal(fe2Runtime.disableReasonForChoice(fe2), "Not available with Z51 Performance Package.");
  fe2Runtime.handleChoice(fe2);
  fe2Runtime.reconcileSelections();
  assert.equal(fe2Runtime.state.selected.has("opt_fe2_001"), false, "FE2 should not be selectable while Z51 is selected");
  assert.equal(fe2Runtime.computeAutoAdded().has("opt_fe3_001"), true, "Z51 should include FE3 after replacing FE2");

  const fe4Runtime = loadRuntime();
  fe4Runtime.state.bodyStyle = "coupe";
  fe4Runtime.state.trimLevel = "1LT";
  fe4Runtime.resetDefaults();
  fe4Runtime.reconcileSelections();
  const fe4 = fe4Runtime.activeChoiceRows().find((choice) => choice.option_id === "opt_fe4_001");
  assert.equal(fe4Runtime.disableReasonForChoice(fe4), "Requires Z51 Performance Package.");
  fe4Runtime.handleChoice(fe4Runtime.activeChoiceRows().find((choice) => choice.option_id === "opt_z51_001"));
  fe4Runtime.reconcileSelections();
  assert.equal(fe4Runtime.disableReasonForChoice(fe4), "");
  fe4Runtime.handleChoice(fe4);
  fe4Runtime.reconcileSelections();
  assert.equal(fe4Runtime.state.selected.has("opt_fe4_001"), true, "FE4 should remain selectable once Z51 is selected");
  assert.equal(fe4Runtime.computeAutoAdded().has("opt_b4z_001"), true, "FE4 should still include B4Z");
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

test("standard equipment is sourced from canonical standard-status choices", () => {
  const expectedByVariant = new Map([
    ["1lt_c07", ["opt_719_001", "opt_cf7_001", "opt_efr_001", "opt_eyt_001", "opt_fe1_001", "opt_j6a_001", "opt_nga_001", "opt_qeb_001"]],
    ["2lt_c07", ["opt_719_001", "opt_cf7_001", "opt_efr_001", "opt_eyt_001", "opt_fe1_001", "opt_j6a_001", "opt_nga_001", "opt_qeb_001"]],
    ["3lt_c07", ["opt_719_001", "opt_cf7_001", "opt_efr_001", "opt_eyt_001", "opt_fe1_001", "opt_j6a_001", "opt_nga_001", "opt_qeb_001"]],
    ["1lt_c67", ["opt_719_001", "opt_cm9_001", "opt_efr_001", "opt_eyt_001", "opt_fe1_001", "opt_j6a_001", "opt_nga_001", "opt_qeb_001"]],
    ["2lt_c67", ["opt_719_001", "opt_cm9_001", "opt_efr_001", "opt_eyt_001", "opt_fe1_001", "opt_j6a_001", "opt_nga_001", "opt_qeb_001"]],
    ["3lt_c67", ["opt_719_001", "opt_cm9_001", "opt_efr_001", "opt_eyt_001", "opt_fe1_001", "opt_j6a_001", "opt_nga_001", "opt_qeb_001"]],
  ]);

  for (const [variantId, optionIds] of expectedByVariant) {
    const rows = data.standardEquipment.filter((item) => item.variant_id === variantId);
    for (const optionId of optionIds) {
      assert.ok(
        rows.some((item) => item.option_id === optionId),
        `${variantId} standard equipment should include canonical ${optionId}`
      );
    }
  }
});

test("standard equipment dedupes mirrored RPO rows and does not require default_selected", () => {
  for (const variant of data.variants) {
    const byRpo = new Map();
    for (const item of data.standardEquipment.filter((row) => row.variant_id === variant.variant_id && row.rpo)) {
      assert.equal(byRpo.has(item.rpo), false, `${variant.variant_id} should emit one standard row for ${item.rpo}`);
      byRpo.set(item.rpo, item);
    }

    assert.equal(byRpo.get("EFR")?.option_id, "opt_efr_001");
    assert.equal(byRpo.get("719")?.option_id, "opt_719_001");
    assert.equal(byRpo.get("J6A")?.option_id, "opt_j6a_001", "J6A has no default_selected flag but is standard");
    assert.equal(byRpo.get("QEB")?.option_id, "opt_qeb_001", "QEB has no default_selected flag but is standard");
    assert.equal(byRpo.get("FE1")?.option_id, "opt_fe1_001");
  }
});

test("coupe defaults include BC7 engine appearance from workbook-authored choice metadata and default rules", () => {
  const bc7Rule = data.defaultSelectionRules.find((rule) => rule.rule_id === "default_bc7");
  assert.ok(bc7Rule, "BC7 should use a workbook-authored default selection rule for coupe restoration");
  assert.equal(bc7Rule.target_option_id, "opt_bc7_001");
  assert.equal(bc7Rule.condition_type, "always");
  assert.equal(bc7Rule.body_style_scope, "coupe");

  const coupeBc7Choices = data.choices.filter((choice) => choice.option_id === "opt_bc7_001" && choice.body_style === "coupe");
  assert.equal(coupeBc7Choices.length, 3);
  assert.equal(coupeBc7Choices.every((choice) => choice.status === "standard"), true);
  assert.equal(coupeBc7Choices.every((choice) => choice.display_behavior === "default_selected"), true);

  const convertibleBc7Choices = data.choices.filter((choice) => choice.option_id === "opt_bc7_001" && choice.body_style === "convertible");
  assert.equal(convertibleBc7Choices.length, 3);
  assert.equal(convertibleBc7Choices.every((choice) => choice.display_behavior !== "default_selected"), true);

  const runtime = loadRuntime();
  runtime.state.bodyStyle = "coupe";
  runtime.state.trimLevel = "1LT";
  runtime.resetDefaults();
  runtime.reconcileSelections();
  assert.equal(runtime.state.selected.has("opt_bc7_001"), true, "coupe builds should default BC7 from workbook metadata");
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
    ["Stripes", "Jake Graphics Package", "Hash Marks", "GS Hash Marks", "GS Center Stripes"]
  );
  assert.match(appSource, /section_display_order/);
});

test("Stingray hash marks are independent from dual racing and Jake stripe choices", () => {
  const sectionById = new Map(data.sections.map((section) => [section.section_id, section]));
  assert.equal(sectionById.get("sec_hash_001")?.section_name, "Hash Marks");
  assert.equal(sectionById.get("sec_hash_001")?.selection_mode, "single_select_opt");

  const hashChoices = data.choices.filter((choice) => ["opt_shq_001", "opt_shw_001", "opt_sng_001"].includes(choice.option_id));
  assert.equal(hashChoices.length, 18);
  assert.equal(hashChoices.every((choice) => choice.section_id === "sec_hash_001"), true);

  const runtime = loadRuntime();
  runtime.state.bodyStyle = "coupe";
  runtime.state.trimLevel = "1LT";
  runtime.resetDefaults();
  runtime.reconcileSelections();

  const choiceByRpo = (rpo) => runtime.activeChoiceRows().find((choice) => choice.rpo === rpo);
  const shq = choiceByRpo("SHQ");
  const dpb = choiceByRpo("DPB");
  const sht = choiceByRpo("SHT");
  assert.ok(shq, "SHQ should be active");
  assert.ok(dpb, "DPB should be active");
  assert.ok(sht, "SHT should be active");

  runtime.handleChoice(shq);
  runtime.handleChoice(dpb);
  assert.equal(runtime.state.selected.has(shq.option_id), true, "hash mark should remain selected with dual racing stripe");
  assert.equal(runtime.state.selected.has(dpb.option_id), true, "dual racing stripe should remain selected with hash mark");
  assert.match(runtime.disableReasonForChoice(sht), /DPB blocks Stingray Jake graphics/);
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
  assert.deepEqual(JSON.parse(JSON.stringify(engineOrder)), ["B6P", "ZZ3", "D3V", "SL9", "BC7", "BCP", "BCS", "BC4", "SLK", "SLN", "VUP"]);

  const activeSectionIds = new Set(data.choices.filter((choice) => choice.active === "True").map((choice) => choice.section_id));
  const wheelSections = data.sections
    .filter((section) => section.step_key === "wheels")
    .filter((section) => activeSectionIds.has(section.section_id))
    .sort((a, b) => Number(a.section_display_order) - Number(b.section_display_order))
    .map((section) => section.section_name);
  assert.deepEqual(JSON.parse(JSON.stringify(wheelSections)), ["Wheels", "Caliper Color", "Wheel Accessory"]);
  assert.equal(data.steps.some((step) => step.step_key === "calipers"), false);
});

test("BC7 ZZ3 requirement is constrained by OVS availability", () => {
  const bc7Rule = data.rules.find(
    (rule) => rule.source_id === "opt_bc7_001" && rule.target_id === "opt_zz3_001" && rule.rule_type === "requires"
  );
  assert.ok(bc7Rule, "BC7 should have a ZZ3 requirement rule");
  assert.equal(bc7Rule.body_style_scope || "", "");
  assert.match(bc7Rule.disabled_reason, /Requires ZZ3 Convertible Engine Appearance Package/);
  const variantsById = new Map(data.variants.map((variant) => [variant.variant_id, variant]));
  const zz3Bodies = new Set(
    data.choices
      .filter((choice) => choice.option_id === "opt_zz3_001" && choice.active === "True" && choice.status !== "unavailable")
      .map((choice) => variantsById.get(choice.variant_id)?.body_style)
  );
  assert.deepEqual([...zz3Bodies].sort(), ["convertible"]);
});

test("spoiler replacement ownership preserves ZYC and keeps T0A replacement behavior", () => {
  const spoilerSection = data.sections.find((section) => section.section_id === "sec_spoi_001");
  assert.equal(spoilerSection.selection_mode, "multi_select_opt");
  for (const sourceId of ["opt_tvs_001", "opt_5zz_001", "opt_5zu_001"]) {
    const rule = data.rules.find((item) => item.source_id === sourceId && item.target_id === "opt_t0a_001");
    assert.equal(rule, undefined, `${sourceId} should use grp_spoiler_high_wing instead of a direct T0A replace row`);
  }
  for (const sourceId of ["opt_5zw_001", "opt_zf1_001"]) {
    const rule = data.rules.find((item) => item.source_id === sourceId && item.target_id === "opt_t0a_001");
    assert.ok(rule, `${sourceId} should preserve direct T0A replacement`);
    assert.equal(rule.runtime_action, "replace");
    assert.match(rule.disabled_reason, /Removes T0A when Z51 is selected/);
  }

  for (const sourceId of ["opt_tvs_001", "opt_5zz_001", "opt_5zu_001"]) {
    const runtime = loadRuntime();
    runtime.state.bodyStyle = "coupe";
    runtime.state.trimLevel = "1LT";
    runtime.resetDefaults();
    runtime.reconcileSelections();
    runtime.handleChoice(runtime.activeChoiceRows().find((choice) => choice.option_id === "opt_gba_001"));
    runtime.handleChoice(runtime.activeChoiceRows().find((choice) => choice.option_id === "opt_z51_001"));
    runtime.state.selected.add("opt_t0a_001");
    runtime.state.userSelected.add("opt_t0a_001");
    assert.equal(runtime.state.selected.has("opt_t0a_001"), true, "T0A should be selectable after Z51");
    runtime.handleChoice(runtime.activeChoiceRows().find((choice) => choice.option_id === sourceId));
    assert.equal(runtime.state.selected.has(sourceId), true, `${sourceId} should be selected`);
    assert.equal(runtime.state.selected.has("opt_t0a_001"), false, `${sourceId} should remove selected T0A through grp_spoiler_high_wing`);
    assert.equal(runtime.computeAutoAdded().has("opt_t0a_001"), false, `${sourceId} should keep T0A out of auto-added options`);
  }

  const zycExclusionGroup = data.ruleGroups.find(
    (group) => group.group_id === "grp_gba_excludes_zyc" && group.source_id === "opt_gba_001"
  );
  assert.ok(zycExclusionGroup, "GBA should remove ZYC through workbook-owned grouped exclusion metadata");
  assert.equal(zycExclusionGroup.group_type, "excludes_any");
  assert.deepEqual(JSON.parse(JSON.stringify(zycExclusionGroup.target_ids)), ["opt_zyc_001"]);
  assert.match(zycExclusionGroup.disabled_reason, /ZYC Carbon Flash painted mirrors and spoiler package is not available with Black exterior paint/);

  const runtime = loadRuntime();
  runtime.state.bodyStyle = "coupe";
  runtime.state.trimLevel = "1LT";
  runtime.resetDefaults();
  runtime.reconcileSelections();
  runtime.handleChoice(runtime.activeChoiceRows().find((choice) => choice.option_id === "opt_gba_001"));
  const zyc = runtime.activeChoiceRows().find((choice) => choice.option_id === "opt_zyc_001");
  assert.equal(runtime.disableReasonForChoice(zyc), "ZYC Carbon Flash painted mirrors and spoiler package is not available with Black exterior paint.");
});

test("step rendering resets scroll to the top after content replacement", () => {
  assert.match(appSource, /function resetStepScroll/);
  assert.match(appSource, /closest\("\.choice-panel"\)\?\.scrollTo\(\{ top: 0, left: 0 \}\)/);
  assert.match(appSource, /window\.scrollTo\(\{ top: 0, left: 0 \}\)/);
});

test("interior pricing subtracts the resolved selected seat price", () => {
  assert.match(appSource, /function selectedSeatChoice/);
  assert.match(appSource, /function selectedSeatResolvedPrice/);
  assert.match(appSource, /seat \? optionPrice\(seat\.option_id\) : 0/);
  assert.match(appSource, /function adjustedInteriorPrice/);
  assert.match(appSource, /Math\.max\(0, Number\(interior\.price \|\| 0\) - selectedSeatResolvedPrice\(\)\)/);
  assert.match(appSource, /price: adjustedInteriorPrice\(interior\)/);
});

test("model_interior_scope maps every active Stingray interior", () => {
  assert.equal(stingrayScopeRows.length, activeInteriors.length);
  for (const row of stingrayScopeRows) {
    assert.ok(data.interiors.some((interior) => interior.interior_id === row.interior_id), `${row.interior_id} should map to generated interiors`);
  }
  for (const interior of activeInteriors) {
    assert.ok(stingrayScopeIds.has(interior.interior_id), `${interior.interior_id} should be represented by model_interior_scope`);
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

  const h8tScope = stingrayScopeRows.find((row) => row.interior_id === "3LT_AE4_H8T");
  assert.ok(h8tScope, "3LT_AE4_H8T should be represented in model_interior_scope");
  const h8tInterior = data.interiors.find((interior) => interior.interior_id === "3LT_AE4_H8T");
  assert.equal(h8tInterior?.interior_trim_level, "3LT");
  assert.equal(h8tInterior?.interior_seat_label, "AE4 Competition Seats");
  assert.equal(h8tInterior?.interior_color_family, "Santorini Blue");
});

test("active interiors have stable workbook-owned grouping fields", () => {
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

test("R6X is component-priced and D30 is the only visible disabled color override card", () => {
  assert.equal(data.choices.some((choice) => choice.rpo === "R6X" && choice.active === "True"), false);
  assert.equal(
    data.rules.some((rule) => rule.target_id === "opt_r6x_001" && rule.rule_type === "includes" && rule.active === true),
    false,
    "R6X should be charged only as an interior component, not as an auto-added include rule"
  );
  assert.equal(
    data.priceRules.some(
      (rule) =>
        (rule.condition_option_id === "opt_d30_001" && rule.target_option_id === "opt_r6x_001") ||
        (rule.condition_option_id === "opt_r6x_001" && rule.target_option_id === "opt_d30_001")
    ),
    false,
    "R6X pricing is carried by interior setup, not a direct D30/R6X price override in either direction"
  );
  assert.equal(
    data.rules.some(
      (rule) =>
        (rule.source_id === "opt_d30_001" && rule.target_id === "opt_r6x_001") ||
        (rule.source_id === "opt_r6x_001" && rule.target_id === "opt_d30_001")
    ),
    false,
    "R6X and D30 should not have direct include/require/exclude rules in either direction"
  );
  assert.doesNotMatch(
    appSource,
    /if\s*\(\s*component\.rpo\s*===\s*["']R6X["']\s*&&\s*autoAdded\.has\(\s*["']opt_d30_001["']\s*\)\s*\)\s*return\s+0\s*;/,
    "runtime should not contain an R6X/D30 hardcoded component-pricing branch"
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
  assert.equal(
    r6xInteriors.every((interior) => interior.interior_components.some((component) => component.rpo === "R6X" && Number(component.price) > 0)),
    true,
    "active R6X interiors should carry R6X as a priced interior component"
  );
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
  const autoAdded = d30Runtime.computeAutoAdded();
  assert.equal(autoAdded.has("opt_d30_001"), true, "D30 should be auto-added by selected color/interior context");
  assert.equal(autoAdded.has("opt_r6x_001"), false, "R6X should not be auto-added when it is an interior component");
  assert.equal(d30Runtime.optionPrice("opt_r6x_001"), 995, "R6X should keep normal option price when D30 is present");

  const order = d30Runtime.currentOrder();
  const r6xLineItems = d30Runtime.lineItems().filter((item) => item.rpo === "R6X");
  assert.equal(r6xLineItems.length, 1, "R6X should appear once in selected line items");
  assert.equal(r6xLineItems[0].type, "interior_component", "R6X should be carried by the interior component row");
  assert.equal(Number(r6xLineItems[0].price), 995, "R6X should be charged once at its component price");
  assert.equal(order.metadata.selected_rpos.includes("R6X"), true, "selected RPO metadata should retain the R6X component");
  assert.equal(order.metadata.auto_added_rpos.includes("R6X"), false, "auto-added RPO metadata should not duplicate R6X");
});

test("single interior and included seatbelt defaults are handled in runtime", () => {
  const ae4Interiors = data.interiors.filter((interior) => interior.trim_level === "1LT" && interior.seat_code === "AE4");
  assert.deepEqual(JSON.parse(JSON.stringify(ae4Interiors.map((interior) => interior.interior_code))), ["HTJ"]);
  assert.match(appSource, /function reconcileInteriorSelection/);
  assert.match(appSource, /interiors\.length === 1/);
  assert.match(appSource, /function shouldSuppressIncludedDefault/);
  const seatbeltDefault = data.defaultSelectionRules.find((rule) => rule.rule_id === "default_719");
  assert.equal(seatbeltDefault?.target_option_id, "opt_719_001");
  assert.equal(seatbeltDefault?.condition_type, "unless_selected_section");
  assert.equal(seatbeltDefault?.condition_id, "sec_seat_001");
});

test("Stingray 3LT interiors lock included color seatbelts against other seatbelt choices", () => {
  const group = data.exclusiveGroups.find((item) => item.group_id === "excl_seat_belts");
  assert.ok(group, "Stingray seatbelt exclusive group should be generated");
  assert.equal(group.selection_mode, "single_within_group");
  assert.deepEqual(JSON.parse(JSON.stringify(group.option_ids)), ["opt_719_001", "opt_3n9_001", "opt_379_001", "opt_3a9_001", "opt_3f9_001", "opt_3m9_001"]);

  const runtime = configureInteriorOrder({ trimLevel: "3LT", seatRpo: "AE4", interiorId: "3LT_AE4_H8T" });
  runtime.reconcileSelections();
  assert.equal(runtime.computeAutoAdded().has("opt_3a9_001"), true, "3LT_AE4_H8T should auto-add 3A9");
  assert.equal(runtime.optionPrice("opt_3a9_001"), 0, "included 3A9 should price at zero");

  const redSeatbelt = runtime.activeChoiceRows().find((choice) => choice.option_id === "opt_3f9_001");
  assert.ok(redSeatbelt, "red seatbelt should exist for lock test");
  runtime.handleChoice(redSeatbelt);
  runtime.reconcileSelections();
  assert.equal(runtime.state.selected.has("opt_3f9_001"), false, "included 3A9 should block other seatbelt choices");

  runtime.state.selected.add("opt_d30_001");
  runtime.handleChoice(redSeatbelt);
  runtime.reconcileSelections();
  assert.equal(runtime.state.selected.has("opt_3f9_001"), false, "D30 should not unlock a 3LT included seatbelt peer");

  for (const interiorId of ["3LT_AE4_EJH", "3LT_AE4_EPX_N26", "3LT_AH2_EJH", "3LT_AH2_EPX_N26"]) {
    const seatRpo = interiorId.includes("_AE4_") ? "AE4" : "AH2";
    const vdaRuntime = configureInteriorOrder({ trimLevel: "3LT", seatRpo, interiorId });
    vdaRuntime.reconcileSelections();
    assert.equal(vdaRuntime.computeAutoAdded().has("opt_3n9_001"), true, `${interiorId} should auto-add 3N9`);
    assert.equal(vdaRuntime.optionPrice("opt_3n9_001"), 0, `${interiorId} should zero-price 3N9`);

    const otherSeatbelt = vdaRuntime.activeChoiceRows().find(
      (choice) => choice.section_id === "sec_seat_001" && choice.option_id !== "opt_3n9_001" && choice.selectable === "True"
    );
    assert.ok(otherSeatbelt, "expected another selectable seatbelt for VDA lock test");
    vdaRuntime.handleChoice(otherSeatbelt);
    vdaRuntime.reconcileSelections();
    assert.equal(vdaRuntime.state.selected.has(otherSeatbelt.option_id), false, `${interiorId} should block other seatbelt colors`);

    vdaRuntime.state.selected.add("opt_d30_001");
    vdaRuntime.handleChoice(otherSeatbelt);
    vdaRuntime.reconcileSelections();
    assert.equal(vdaRuntime.state.selected.has(otherSeatbelt.option_id), false, `${interiorId} should keep other seatbelts blocked even with D30`);
  }

  const dippedRuntime = configureInteriorOrder({ trimLevel: "3LT", seatRpo: "AH2", interiorId: "3LT_AH2_HNK" });
  dippedRuntime.reconcileSelections();
  const autoAdded = dippedRuntime.computeAutoAdded();
  assert.equal(autoAdded.get("opt_3f9_001"), "Included with Adrenaline Red Dipped.");
  dippedRuntime.state.activeStep = "seat_belt";
  const blackSeatbelt = dippedRuntime.activeChoiceRows().find((choice) => choice.option_id === "opt_719_001");
  const blackSeatbeltHtml = dippedRuntime.renderChoiceCard(blackSeatbelt, autoAdded);
  assert.match(
    blackSeatbeltHtml,
    /Torch Red Seat Belt Color is included with Adrenaline Red Dipped, so other seat belt colors are unavailable\./
  );
  assert.doesNotMatch(blackSeatbeltHtml, /3LT_AH2_HNK|3lt_ah2_hnk/);
});

test("sidebar keeps one Standard & Included surface inside Selected RPOs", () => {
  assert.match(htmlSource, /selectedStandardEquipmentList/);
  assert.doesNotMatch(htmlSource, /standardEquipmentList/);
  assert.doesNotMatch(htmlSource, /standard-card/);
});

test("standard equipment grouping is data-driven by workbook metadata", () => {
  const trimRows = data.standardEquipment.filter((item) => item.standard_equipment_group_type === "trim_equipment");
  assert.ok(trimRows.length > 0, "trim equipment rows should be tagged by generated workbook metadata");
  assert.equal(trimRows.every((item) => ["sec_1lte_001", "sec_2lte_001", "sec_3lte_001"].includes(item.section_id)), true);
  assert.doesNotMatch(appSource, /LT Equipment\$\.test/);
  assert.match(appSource, /standard_equipment_group_type === "trim_equipment"/);
});
