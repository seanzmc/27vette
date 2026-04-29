const data = window.STINGRAY_FORM_DATA;

const state = {
  bodyStyle: "",
  trimLevel: "",
  selected: new Set(),
  userSelected: new Set(),
  selectedInterior: "",
  activeStep: "body_style",
  customer: {
    name: "",
    address: "",
    email: "",
    phone: "",
    comments: "",
  },
};

const els = {
  currentBody: document.querySelector("#currentBody"),
  currentTrim: document.querySelector("#currentTrim"),
  basePrice: document.querySelector("#basePrice"),
  summaryBase: document.querySelector("#summaryBase"),
  summaryOptions: document.querySelector("#summaryOptions"),
  summaryTotal: document.querySelector("#summaryTotal"),
  variantName: document.querySelector("#variantName"),
  stepRail: document.querySelector("#stepRail"),
  stepContent: document.querySelector("#stepContent"),
  selectedList: document.querySelector("#selectedList"),
  selectedStandardEquipmentList: document.querySelector("#selectedStandardEquipmentList"),
  autoList: document.querySelector("#autoList"),
  missingList: document.querySelector("#missingList"),
  alertRegion: document.querySelector("#alertRegion"),
  resetButton: document.querySelector("#resetButton"),
  exportJsonButton: document.querySelector("#exportJsonButton"),
  exportCsvButton: document.querySelector("#exportCsvButton"),
};

const runtimeSteps = data.steps.filter((step) => step.step_key !== "summary");
const variants = [...data.variants].sort((a, b) => a.display_order - b.display_order);
const choicesByOption = new Map();
const sectionsById = new Map(data.sections.map((section) => [section.section_id, section]));
const optionsById = new Map();
const interiorsById = new Map(data.interiors.map((interior) => [interior.interior_id, interior]));
const ruleTargetsBySource = new Map();
const rulesByTarget = new Map();
const priceRulesByTarget = new Map();
const ruleGroupsBySource = new Map();
const exclusiveGroupByOption = new Map();
const orderSectionDefinitions = [
  ["vehicle", "Vehicle"],
  ["exterior_paint", "Exterior Paint"],
  ["exterior_appearance", "Exterior Appearance"],
  ["wheels_brakes", "Wheels & Brakes"],
  ["performance_mechanical", "Performance & Mechanical"],
  ["aero_exhaust_stripes_accessories", "Aero, Exhaust, Stripes & Accessories"],
  ["seats_interior", "Seats & Interior"],
  ["delivery", "Delivery"],
  ["auto_added_required", "Auto-Added / Required"],
  ["pricing_summary", "Pricing Summary"],
  ["customer_information", "Customer Information"],
];
const orderSectionLabels = new Map(orderSectionDefinitions);
const orderSectionOrder = new Map(orderSectionDefinitions.map(([key], index) => [key, index]));
const stepOrderSectionKeys = new Map([
  ["body_style", "vehicle"],
  ["trim_level", "vehicle"],
  ["paint", "exterior_paint"],
  ["exterior_appearance", "exterior_appearance"],
  ["wheels", "wheels_brakes"],
  ["packages_performance", "performance_mechanical"],
  ["aero_exhaust_stripes_accessories", "aero_exhaust_stripes_accessories"],
  ["seat", "seats_interior"],
  ["base_interior", "seats_interior"],
  ["seat_belt", "seats_interior"],
  ["interior_trim", "seats_interior"],
  ["delivery", "delivery"],
]);

for (const choice of data.choices) {
  if (!choicesByOption.has(choice.option_id)) choicesByOption.set(choice.option_id, []);
  choicesByOption.get(choice.option_id).push(choice);
  if (!optionsById.has(choice.option_id)) optionsById.set(choice.option_id, choice);
}

for (const rule of data.rules) {
  if (!ruleTargetsBySource.has(rule.source_id)) ruleTargetsBySource.set(rule.source_id, []);
  ruleTargetsBySource.get(rule.source_id).push(rule);
  if (!rulesByTarget.has(rule.target_id)) rulesByTarget.set(rule.target_id, []);
  rulesByTarget.get(rule.target_id).push(rule);
}

for (const rule of data.priceRules) {
  if (!priceRulesByTarget.has(rule.target_option_id)) priceRulesByTarget.set(rule.target_option_id, []);
  priceRulesByTarget.get(rule.target_option_id).push(rule);
}

for (const group of data.ruleGroups || []) {
  if (!ruleGroupsBySource.has(group.source_id)) ruleGroupsBySource.set(group.source_id, []);
  ruleGroupsBySource.get(group.source_id).push(group);
}

for (const group of data.exclusiveGroups || []) {
  if (group.active && group.active !== "True") continue;
  for (const optionId of group.option_ids || []) {
    exclusiveGroupByOption.set(optionId, group);
  }
}

function formatMoney(value) {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  }).format(Number(value || 0));
}

function escapeHtml(value) {
  return String(value || "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function currentVariant() {
  return variants.find((variant) => variant.body_style === state.bodyStyle && variant.trim_level === state.trimLevel);
}

function currentVariantId() {
  return currentVariant()?.variant_id || "";
}

function currentStepIndex() {
  return runtimeSteps.findIndex((step) => step.step_key === state.activeStep);
}

function nextStep() {
  const index = currentStepIndex();
  return index >= 0 ? runtimeSteps[index + 1] : null;
}

function goToNextStep() {
  const step = nextStep();
  if (!step) return;
  state.activeStep = step.step_key;
  render({ resetScroll: true });
}

function activeChoiceRows() {
  const variantId = currentVariantId();
  return data.choices.filter((choice) => choice.variant_id === variantId);
}

function choiceForCurrentVariant(optionId) {
  return activeChoiceRows().find((choice) => choice.option_id === optionId);
}

function ruleAppliesToCurrentVariant(rule) {
  if (rule.body_style_scope && rule.body_style_scope !== state.bodyStyle) return false;
  const sourceChoice = choiceForCurrentVariant(rule.source_id);
  const targetChoice = choiceForCurrentVariant(rule.target_id);
  if (sourceChoice && (sourceChoice.active !== "True" || sourceChoice.status === "unavailable")) return false;
  if (targetChoice && (targetChoice.active !== "True" || targetChoice.status === "unavailable")) return false;
  return true;
}

function scopeMatches(scope, value) {
  if (!scope) return true;
  return String(scope).split("|").includes(value);
}

function ruleGroupAppliesToCurrentVariant(group) {
  if (group.active && group.active !== "True") return false;
  if (!scopeMatches(group.body_style_scope, state.bodyStyle)) return false;
  if (!scopeMatches(group.trim_level_scope, state.trimLevel)) return false;
  if (!scopeMatches(group.variant_scope, currentVariantId())) return false;
  const sourceChoice = choiceForCurrentVariant(group.source_id);
  if (sourceChoice && (sourceChoice.active !== "True" || sourceChoice.status === "unavailable")) return false;
  return true;
}

function selectedOptionByRpo(rpo) {
  return [...state.selected].some((id) => optionsById.get(id)?.rpo === rpo);
}

function selectedSeatChoice() {
  return [...state.selected].map((id) => optionsById.get(id)).find((choice) => choice?.step_key === "seat");
}

function optionSectionId(optionId) {
  return optionsById.get(optionId)?.section_id || choiceForCurrentVariant(optionId)?.section_id || "";
}

function selectedOptionIdsInSection(sectionId, ids = state.selected) {
  return [...ids].filter((id) => optionSectionId(id) === sectionId);
}

function userSelectedInSection(sectionId, exceptId = "") {
  return [...state.userSelected].some((id) => id !== exceptId && optionSectionId(id) === sectionId);
}

function adjustedInteriorPrice(interior) {
  const seat = selectedSeatChoice();
  return Math.max(0, Number(interior.price || 0) - Number(seat?.base_price || 0));
}

function shouldHideChoice(choice) {
  return choice.active !== "True" || choice.status === "unavailable";
}

function optionIsSelectedOrAuto(choice, autoAdded) {
  return state.selected.has(choice.option_id) || autoAdded.has(choice.option_id);
}

function selectedContextIds() {
  const ids = new Set(state.selected);
  if (state.selectedInterior) ids.add(state.selectedInterior);
  for (const id of computeAutoAdded().keys()) ids.add(id);
  return ids;
}

function getOptionLabel(optionId) {
  const option = optionsById.get(optionId);
  if (!option) return optionId;
  return `${option.rpo || option.option_id} ${option.label || ""}`.trim();
}

function getEntityLabel(id) {
  if (optionsById.has(id)) return getOptionLabel(id);
  const interior = interiorsById.get(id);
  if (interior) return `${interior.interior_id} ${interior.interior_name}`.trim();
  return id;
}

function selectedExcludesTarget(targetId, selectedIds) {
  for (const sourceId of selectedIds) {
    const rules = ruleTargetsBySource.get(sourceId) || [];
    if (rules.some((rule) => rule.rule_type === "excludes" && rule.target_id === targetId && ruleAppliesToCurrentVariant(rule))) {
      return true;
    }
  }
  return false;
}

function shouldSuppressIncludedDefault(rule) {
  const sectionId = optionSectionId(rule.target_id);
  const section = sectionsById.get(sectionId);
  return section?.choice_mode === "single" && userSelectedInSection(sectionId, rule.target_id);
}

function selectedExclusiveGroupPeer(optionId, selectedIds) {
  const group = optionExclusiveGroup(optionId);
  if (!group || group.selection_mode !== "single_within_group") return false;
  return (group.option_ids || []).some((id) => id !== optionId && selectedIds.has(id));
}

function sameExclusiveGroupPeer(optionId, peerId) {
  const group = optionExclusiveGroup(optionId);
  if (!group || group.selection_mode !== "single_within_group") return false;
  return (group.option_ids || []).includes(peerId);
}

function requiresAnyReason(choice, selectedIds) {
  const groups = ruleGroupsBySource.get(choice.option_id) || [];
  for (const group of groups) {
    if (group.group_type !== "requires_any" || !ruleGroupAppliesToCurrentVariant(group)) continue;
    if ((group.target_ids || []).some((targetId) => selectedIds.has(targetId))) continue;
    return group.disabled_reason || `Requires one of ${(group.target_ids || []).map(getEntityLabel).join(", ")}.`;
  }
  return "";
}

function computeAutoAdded() {
  const autoAdded = new Map();
  const selectedIds = new Set(state.selected);
  if (state.selectedInterior) selectedIds.add(state.selectedInterior);

  for (const sourceId of selectedIds) {
    const rules = ruleTargetsBySource.get(sourceId) || [];
    for (const rule of rules) {
      if (
        rule.rule_type === "includes" &&
        ruleAppliesToCurrentVariant(rule) &&
        !state.userSelected.has(rule.target_id) &&
        !selectedExcludesTarget(rule.target_id, selectedIds) &&
        !shouldSuppressIncludedDefault(rule) &&
        !selectedExclusiveGroupPeer(rule.target_id, selectedIds)
      ) {
        autoAdded.set(rule.target_id, rule.disabled_reason || `Included with ${getEntityLabel(sourceId)}.`);
      }
    }
  }

  if (state.selectedInterior) {
    for (const override of data.colorOverrides) {
      if (override.interior_id === state.selectedInterior && state.selected.has(override.option_id) && override.adds_rpo) {
        autoAdded.set(
          override.adds_rpo,
          `${getEntityLabel(state.selectedInterior)} with ${getOptionLabel(override.option_id)} requires the override RPO.`
        );
      }
    }
  }

  return autoAdded;
}

function disableReasonForChoice(choice) {
  if (choice.active !== "True") return "Inactive in the source workbook.";
  if (choice.status === "unavailable") return "Not available for this body and trim.";
  if (choice.rpo === "FE1" && selectedOptionByRpo("Z51")) return "Replaced by FE3 Z51 performance suspension.";
  if (choice.rpo === "FE2" && selectedOptionByRpo("Z51")) return "Not available with Z51 Performance Package.";
  if (choice.rpo === "NGA" && selectedOptionByRpo("NWI")) return "Replaced by NWI center exhaust.";

  const selectedIds = selectedContextIds();
  const groupedReason = requiresAnyReason(choice, selectedIds);
  if (groupedReason) return groupedReason;
  const targetRules = rulesByTarget.get(choice.option_id) || [];
  for (const rule of targetRules) {
    if (rule.rule_type === "excludes" && selectedIds.has(rule.source_id) && ruleAppliesToCurrentVariant(rule)) {
      if (sameExclusiveGroupPeer(choice.option_id, rule.source_id)) continue;
      if (choice.rpo === "GBA" && rule.source_id === "opt_zyc_001") continue;
      if (rule.runtime_action === "replace") return rule.disabled_reason || `${getEntityLabel(rule.source_id)} removes this default.`;
      return rule.disabled_reason || `Blocked by ${getEntityLabel(rule.source_id)}.`;
    }
  }

  const sourceRules = ruleTargetsBySource.get(choice.option_id) || [];
  for (const rule of sourceRules) {
    if (!ruleAppliesToCurrentVariant(rule)) continue;
    if (rule.rule_type === "requires" && !selectedIds.has(rule.target_id)) {
      return rule.disabled_reason || `Requires ${getEntityLabel(rule.target_id)}.`;
    }
    if (rule.rule_type === "excludes" && selectedIds.has(rule.target_id)) {
      if (rule.runtime_action === "replace") continue;
      return `Conflicts with ${getEntityLabel(rule.target_id)}.`;
    }
  }

  if (choice.selectable !== "True" && choice.status !== "standard") return "Display-only source row.";

  return "";
}

function disableReasonForInterior(interior) {
  const selectedIds = selectedContextIds();
  const rules = ruleTargetsBySource.get(interior.interior_id) || [];
  for (const rule of rules) {
    if (!ruleAppliesToCurrentVariant(rule)) continue;
    if (rule.rule_type === "requires" && !selectedIds.has(rule.target_id)) {
      return rule.disabled_reason || `Requires ${getEntityLabel(rule.target_id)}.`;
    }
    if (rule.rule_type === "excludes" && selectedIds.has(rule.target_id)) {
      return `Conflicts with ${getEntityLabel(rule.target_id)}.`;
    }
  }
  return "";
}

function optionPrice(optionId) {
  const selectedIds = selectedContextIds();
  const priceRules = priceRulesByTarget.get(optionId) || [];
  for (const rule of priceRules) {
    if (!scopeMatches(rule.body_style_scope, state.bodyStyle)) continue;
    if (!scopeMatches(rule.trim_level_scope, state.trimLevel)) continue;
    if (!scopeMatches(rule.variant_scope, currentVariantId())) continue;
    if (rule.price_rule_type === "override" && selectedIds.has(rule.condition_option_id)) {
      return Number(rule.price_value || 0);
    }
  }
  return Number(optionsById.get(optionId)?.base_price || 0);
}

function sectionKeyForStep(stepKey, type = "") {
  if (type === "auto_added") return "auto_added_required";
  return stepOrderSectionKeys.get(stepKey) || stepKey || "vehicle";
}

function sectionLabelForKey(sectionKey) {
  return orderSectionLabels.get(sectionKey) || sectionKey;
}

function lineItemFromOption(option, type, price, extra = {}) {
  const sectionKey = sectionKeyForStep(option.step_key, type);
  return {
    id: option.option_id,
    rpo: option.rpo || "",
    label: option.label || "",
    description: option.description || "",
    price,
    type,
    section_key: sectionKey,
    section_label: sectionLabelForKey(sectionKey),
    category_name: option.category_name || "",
    step_key: option.step_key || "",
    ...extra,
  };
}

function lineItemFromInterior(interior) {
  return {
    id: interior.interior_id,
    rpo: interior.interior_code || "",
    label: interior.interior_name || "",
    description: interior.interior_hierarchy_path || interior.interior_variant_label || interior.material || "",
    price: adjustedInteriorPrice(interior),
    type: "selected_interior",
    section_key: "seats_interior",
    section_label: sectionLabelForKey("seats_interior"),
    category_name: interior.interior_seat_label || "Base Interior",
    step_key: "base_interior",
  };
}

function lineItems() {
  const autoAdded = computeAutoAdded();
  const rows = [];
  for (const id of state.selected) {
    if (autoAdded.has(id)) continue;
    const option = optionsById.get(id);
    if (option) {
      rows.push(lineItemFromOption(option, "selected", optionPrice(id)));
    }
  }
  if (state.selectedInterior) {
    const interior = interiorsById.get(state.selectedInterior);
    if (interior) rows.push(lineItemFromInterior(interior));
  }
  for (const [id, reason] of autoAdded) {
    const option = optionsById.get(id);
    if (option) {
      rows.push(lineItemFromOption(option, "auto_added", optionPrice(id), { reason }));
    }
  }
  return rows;
}

function missingRequired() {
  const rows = activeChoiceRows();
  const sections = new Map();
  const selectedIds = selectedContextIds();
  for (const choice of rows) {
    const section = sectionsById.get(choice.section_id);
    if (!section || section.selection_mode !== "single_select_req") continue;
    if (choice.step_key === "base_interior") continue;
    if (shouldHideChoice(choice)) continue;
    if (!sections.has(choice.section_id)) sections.set(choice.section_id, section);
  }
  const missing = [];
  for (const [sectionId, section] of sections) {
    const hasSelection = [...selectedIds].some((id) => optionSectionId(id) === sectionId);
    if (!hasSelection) missing.push(section.section_name);
  }
  if (!state.selectedInterior) missing.push("Base Interior");
  return missing;
}

function resetDefaults() {
  state.selected.clear();
  state.userSelected.clear();
  state.selectedInterior = "";
  const rows = activeChoiceRows();
  const bySection = new Map();
  for (const choice of rows) {
    if (choice.status !== "standard" || choice.selectable !== "True") continue;
    const section = sectionsById.get(choice.section_id);
    if (!section || section.selection_mode !== "single_select_req") continue;
    if (!bySection.has(choice.section_id)) bySection.set(choice.section_id, []);
    bySection.get(choice.section_id).push(choice);
  }
  for (const choices of bySection.values()) {
    if (choices.length === 1) state.selected.add(choices[0].option_id);
  }
  for (const defaultRpo of ["FE1", "NGA", "BC7"]) {
    const defaultChoice = rows.find((choice) => choice.rpo === defaultRpo && choice.active === "True" && choice.status !== "unavailable");
    if (defaultRpo === "BC7") {
      if (defaultChoice && defaultChoice.body_style === "coupe") state.selected.add(defaultChoice.option_id);
      continue;
    }
    if (defaultChoice) state.selected.add(defaultChoice.option_id);
  }
}

function deleteSelectedOption(optionId) {
  state.selected.delete(optionId);
  state.userSelected.delete(optionId);
}

function deleteSelectedRpo(rpo) {
  for (const id of [...state.selected]) {
    if (optionsById.get(id)?.rpo === rpo) deleteSelectedOption(id);
  }
}

function selectedChoiceRank(choice) {
  if (choice?.selectable === "True" && choice.step_key !== "standard_equipment") return 0;
  if (choice?.step_key !== "standard_equipment") return 1;
  return 2;
}

function dedupeSelectedRpos() {
  const byRpo = new Map();
  for (const id of state.selected) {
    const choice = optionsById.get(id);
    if (!choice?.rpo) continue;
    if (!byRpo.has(choice.rpo)) byRpo.set(choice.rpo, []);
    byRpo.get(choice.rpo).push(id);
  }
  for (const ids of byRpo.values()) {
    if (ids.length < 2) continue;
    const keepId = ids.reduce((bestId, currentId) => {
      const bestChoice = optionsById.get(bestId);
      const currentChoice = optionsById.get(currentId);
      return selectedChoiceRank(currentChoice) < selectedChoiceRank(bestChoice) ? currentId : bestId;
    });
    for (const id of ids) {
      if (id !== keepId) deleteSelectedOption(id);
    }
  }
}

function optionExclusiveGroup(optionId) {
  return exclusiveGroupByOption.get(optionId) || null;
}

function removeOtherExclusiveGroupOptions(optionId) {
  const group = optionExclusiveGroup(optionId);
  if (!group || group.selection_mode !== "single_within_group") return;
  for (const id of group.option_ids || []) {
    if (id !== optionId) deleteSelectedOption(id);
  }
}

function defaultChoiceForRpo(rpo) {
  const choices = activeChoiceRows().filter((choice) => choice.rpo === rpo && choice.active === "True" && choice.status !== "unavailable");
  return choices.find((choice) => choice.selectable === "True" && choice.step_key !== "standard_equipment") || choices[0];
}

function addDefaultRpo(rpo) {
  const choice = defaultChoiceForRpo(rpo);
  if (choice && !disableReasonForChoice(choice)) state.selected.add(choice.option_id);
}

function removeReplaceRuleTargets(sourceId) {
  const rules = ruleTargetsBySource.get(sourceId) || [];
  for (const rule of rules) {
    if (rule.runtime_action === "replace" && ruleAppliesToCurrentVariant(rule)) {
      deleteSelectedOption(rule.target_id);
    }
  }
}

function selectedOrAutoInSection(sectionId, autoAdded = computeAutoAdded()) {
  return (
    selectedOptionIdsInSection(sectionId).length > 0 ||
    [...autoAdded.keys()].some((id) => optionSectionId(id) === sectionId)
  );
}

function validInteriorsForSelectedSeat() {
  const selectedSeat = selectedSeatChoice();
  return data.interiors.filter((interior) => {
    if (interior.trim_level !== state.trimLevel) return false;
    if (selectedSeat?.rpo && interior.seat_code !== selectedSeat.rpo) return false;
    return true;
  });
}

function reconcileInteriorSelection() {
  const interiors = validInteriorsForSelectedSeat();
  if (state.selectedInterior && !interiors.some((interior) => interior.interior_id === state.selectedInterior)) {
    state.selectedInterior = "";
  }
  if (!state.selectedInterior && interiors.length === 1) {
    state.selectedInterior = interiors[0].interior_id;
  }
}

function removeAutoDefaultDuplicates(autoAdded) {
  for (const id of autoAdded.keys()) {
    deleteSelectedOption(id);
    const sectionId = optionSectionId(id);
    const section = sectionsById.get(sectionId);
    if (section?.choice_mode !== "single") continue;
    for (const selectedId of selectedOptionIdsInSection(sectionId)) {
      if (!state.userSelected.has(selectedId)) deleteSelectedOption(selectedId);
    }
  }
}

function reconcileSelections() {
  if (selectedOptionByRpo("Z51")) {
    deleteSelectedRpo("FE1");
    deleteSelectedRpo("FE2");
  }
  if (selectedOptionByRpo("NWI")) {
    deleteSelectedRpo("NGA");
  }
  if (selectedOptionByRpo("GBA")) {
    deleteSelectedRpo("ZYC");
  }
  for (const id of [...state.selected]) {
    removeReplaceRuleTargets(id);
  }
  for (const id of [...state.selected]) {
    const choice = choiceForCurrentVariant(id);
    if (!choice || shouldHideChoice(choice) || disableReasonForChoice(choice)) deleteSelectedOption(id);
  }
  reconcileInteriorSelection();
  const autoAdded = computeAutoAdded();
  removeAutoDefaultDuplicates(autoAdded);
  const refreshedAutoAdded = computeAutoAdded();
  if (!selectedOptionByRpo("Z51") && !selectedOrAutoInSection("sec_susp_001", refreshedAutoAdded)) addDefaultRpo("FE1");
  if (!selectedOptionByRpo("NWI") && !selectedOptionByRpo("NGA")) addDefaultRpo("NGA");
  if (!selectedOrAutoInSection("sec_seat_001", refreshedAutoAdded)) addDefaultRpo("719");
  dedupeSelectedRpos();
}

function setBodyAndTrim(bodyStyle, trimLevel) {
  state.bodyStyle = bodyStyle;
  state.trimLevel = trimLevel;
  resetDefaults();
  reconcileSelections();
  render();
}

function handleContextChoice(choice) {
  if (choice.context_type === "body_style") {
    const nextTrim = variants.find((variant) => variant.body_style === choice.value)?.trim_level;
    setBodyAndTrim(choice.value, nextTrim);
    return;
  }
  if (choice.context_type === "trim_level") {
    setBodyAndTrim(choice.body_style, choice.trim_level);
  }
}

function handleChoice(choice) {
  const autoAdded = computeAutoAdded();
  if (autoAdded.has(choice.option_id)) return;
  const reason = disableReasonForChoice(choice);
  if (reason) return;
  const section = sectionsById.get(choice.section_id);
  if (section?.choice_mode === "single") {
    if (section.selection_mode === "single_select_opt" && state.selected.has(choice.option_id)) {
      deleteSelectedOption(choice.option_id);
      reconcileSelections();
      render();
      return;
    }
    for (const id of [...state.selected]) {
      if (optionSectionId(id) === choice.section_id) deleteSelectedOption(id);
    }
    state.selected.add(choice.option_id);
    state.userSelected.add(choice.option_id);
  } else if (state.selected.has(choice.option_id)) {
    deleteSelectedOption(choice.option_id);
  } else {
    removeOtherExclusiveGroupOptions(choice.option_id);
    state.selected.add(choice.option_id);
    state.userSelected.add(choice.option_id);
  }
  removeReplaceRuleTargets(choice.option_id);
  if (choice.rpo === "GBA") deleteSelectedRpo("ZYC");
  reconcileSelections();
  render({ preserveScroll: true });
}

function handleInterior(interior) {
  const reason = disableReasonForInterior(interior);
  if (reason) return;
  state.selectedInterior = state.selectedInterior === interior.interior_id ? "" : interior.interior_id;
  reconcileSelections();
  render({ preserveScroll: true });
}

function renderVehicleContext() {
  els.currentBody.textContent = state.bodyStyle ? state.bodyStyle[0].toUpperCase() + state.bodyStyle.slice(1) : "";
  els.currentTrim.textContent = state.trimLevel || "";
}

function renderStepRail() {
  els.stepRail.innerHTML = runtimeSteps
    .map(
      (step, index) => `
        <button class="step-link ${state.activeStep === step.step_key ? "active" : ""}" data-step="${step.step_key}" type="button">
          <span class="step-index">${index + 1}</span>
          <span>${step.step_label}</span>
        </button>
      `
    )
    .join("");
  els.stepRail.querySelectorAll(".step-link").forEach((button) => {
    button.addEventListener("click", () => {
      state.activeStep = button.dataset.step;
      render({ resetScroll: true });
    });
  });
}

function renderChoiceCard(choice, autoAdded) {
  const selected = optionIsSelectedOrAuto(choice, autoAdded);
  const autoReason = autoAdded.get(choice.option_id);
  const disabledReason = autoReason ? "" : disableReasonForChoice(choice);
  const disabled = Boolean(disabledReason || autoReason);
  const classes = ["choice-card"];
  if (selected) classes.push("selected");
  if (disabledReason) classes.push("disabled");
  if (autoReason) classes.push("auto");
  return `
    <button class="${classes.join(" ")}" type="button" data-option="${choice.option_id}" ${disabled ? "aria-disabled=\"true\" disabled" : ""}>
      <span class="topline"><span class="rpo">${choice.rpo || choice.option_id}</span><span class="price">${formatMoney(optionPrice(choice.option_id))}</span></span>
      <p class="choice-name">${choice.label}</p>
      <p class="choice-note">${choice.description || choice.status_label}</p>
      ${disabledReason ? `<p class="disabled-reason">${disabledReason}</p>` : ""}
      ${autoReason ? `<p class="auto-reason">${autoReason}</p>` : ""}
    </button>
  `;
}

function renderModeLabel(section) {
  return section?.selection_mode_label || section?.selection_mode || "";
}

function renderInteriorCard(interior) {
  const selected = state.selectedInterior === interior.interior_id;
  const disabledReason = disableReasonForInterior(interior);
  const classes = ["choice-card"];
  if (selected) classes.push("selected");
  if (disabledReason) classes.push("disabled");
  const detail = [interior.interior_material_family || interior.material, interior.source_note].filter(Boolean).join(" ");
  return `
    <button class="${classes.join(" ")}" type="button" data-interior="${interior.interior_id}" ${disabledReason ? "aria-disabled=\"true\"" : ""}>
      <span class="topline"><span class="rpo">${interior.interior_code}</span><span class="price">${formatMoney(adjustedInteriorPrice(interior))}</span></span>
      <p class="choice-name">${escapeHtml(interior.interior_leaf_label || interior.interior_name)}</p>
      <p class="choice-note">${escapeHtml(detail || interior.interior_id)}</p>
      ${disabledReason ? `<p class="disabled-reason">${disabledReason}</p>` : ""}
    </button>
  `;
}

function sortInteriorsByDisplayOrder(a, b) {
  return (
    Number(a.interior_group_display_order || 0) - Number(b.interior_group_display_order || 0) ||
    Number(a.interior_material_display_order || 0) - Number(b.interior_material_display_order || 0) ||
    Number(a.interior_choice_display_order || 0) - Number(b.interior_choice_display_order || 0) ||
    a.interior_name.localeCompare(b.interior_name)
  );
}

function groupInteriorsBy(interiors, key) {
  const groups = new Map();
  for (const interior of interiors) {
    const label = interior[key] || "Interior Choices";
    if (!groups.has(label)) groups.set(label, []);
    groups.get(label).push(interior);
  }
  return [...groups.entries()].map(([label, rows]) => ({ label, rows: rows.sort(sortInteriorsByDisplayOrder) }));
}

function renderInteriorGroups(interiors) {
  if (!interiors.length) return "<p class=\"empty\">Select a seat first.</p>";
  return `
    <div class="interior-layout">
      ${groupInteriorsBy(interiors.slice().sort(sortInteriorsByDisplayOrder), "interior_color_family")
        .map((group) => {
          const materialGroups = groupInteriorsBy(group.rows, "interior_material_family");
          const materialSummary = [...new Set(group.rows.map((interior) => interior.interior_material_family).filter(Boolean))].join(" / ");
          return `
            <section class="interior-group">
              <div class="interior-group-header">
                <div>
                  <h4>${escapeHtml(group.label)}</h4>
                  ${materialSummary ? `<p>${escapeHtml(materialSummary)}</p>` : ""}
                </div>
                <span>${group.rows.length === 1 ? "1 choice" : `${group.rows.length} choices`}</span>
              </div>
              ${materialGroups
                .map(
                  (materialGroup) => `
                    <div class="interior-material-group">
                      ${materialGroups.length > 1 ? `<h5>${escapeHtml(materialGroup.label)}</h5>` : ""}
                      <div class="choice-grid interior-choice-grid">
                        ${materialGroup.rows.map(renderInteriorCard).join("")}
                      </div>
                    </div>
                  `
                )
                .join("")}
            </section>
          `;
        })
        .join("")}
    </div>
  `;
}

function renderContextCard(choice) {
  const selected =
    (choice.context_type === "body_style" && choice.value === state.bodyStyle) ||
    (choice.context_type === "trim_level" && choice.body_style === state.bodyStyle && choice.trim_level === state.trimLevel);
  const disabled = choice.context_type === "trim_level" && choice.body_style !== state.bodyStyle;
  const classes = ["choice-card", "context-choice-card"];
  if (selected) classes.push("selected");
  if (disabled) classes.push("disabled");
  const price = choice.base_price ? formatMoney(choice.base_price) : "";
  return `
    <button class="${classes.join(" ")}" type="button" data-context-choice="${choice.context_choice_id}" ${disabled ? "aria-disabled=\"true\"" : ""}>
      <span class="topline"><span class="rpo">${choice.label}</span><span class="price">${price}</span></span>
      <p class="choice-name">${choice.description}</p>
      <p class="choice-note">${selected ? "Current selection" : "Select to continue"}</p>
      ${disabled ? `<p class="disabled-reason">Choose ${choice.body_style[0].toUpperCase() + choice.body_style.slice(1)} body style first.</p>` : ""}
    </button>
  `;
}

function renderCustomerForm() {
  return `
    <form id="customerForm" class="customer-step-form">
      <div class="customer-field-grid">
        <label>
          Name
          <input id="customerName" name="name" type="text" autocomplete="name" value="${escapeHtml(state.customer.name)}">
        </label>
        <label>
          Address
          <input id="customerAddress" name="address" type="text" autocomplete="street-address" value="${escapeHtml(state.customer.address)}">
        </label>
        <label>
          Email
          <input id="customerEmail" name="email" type="email" autocomplete="email" value="${escapeHtml(state.customer.email)}">
        </label>
        <label>
          Phone Number
          <input id="customerPhone" name="phone" type="tel" autocomplete="tel" value="${escapeHtml(state.customer.phone)}">
        </label>
        <label class="full-field">
          Comments
          <textarea id="customerComments" name="comments" rows="5">${escapeHtml(state.customer.comments)}</textarea>
        </label>
      </div>
    </form>
  `;
}

function bindCustomerForm() {
  const form = document.querySelector("#customerForm");
  if (!form) return;
  form.addEventListener("submit", (event) => event.preventDefault());
  form.addEventListener("input", (event) => {
    if (!event.target.name || !(event.target.name in state.customer)) return;
    state.customer[event.target.name] = event.target.value;
  });
}

function renderStandardEquipmentGroups(rows, initiallyOpen = false, openGroupName = "") {
  const grouped = new Map();
  for (const item of rows) {
    const groupName = item.section_name || "Included";
    if (!grouped.has(groupName)) grouped.set(groupName, []);
    grouped.get(groupName).push(item);
  }
  return (
    [...grouped.entries()]
      .map(
        ([group, items]) => `
          <details class="standard-group" ${initiallyOpen || group === openGroupName ? "open" : ""}>
            <summary>${group} <span>${items.length}</span></summary>
            <ul class="summary-list">
              ${items
                .map(
                  (item) =>
                    `<li><span>${escapeHtml(item.label)}</span>${item.description ? `<small>${escapeHtml(item.description)}</small>` : ""}</li>`
                )
                .join("")}
            </ul>
          </details>
        `
      )
      .join("") || "<p class=\"empty\">No standard equipment rows for this variant.</p>"
  );
}

function standardEquipmentRows() {
  const variantId = currentVariantId();
  return data.standardEquipment
    .filter((item) => item.variant_id === variantId)
    .sort((a, b) => a.section_name.localeCompare(b.section_name) || Number(a.display_order || 0) - Number(b.display_order || 0));
}

function trimEquipmentRows() {
  return standardEquipmentRows().filter((item) => /LT Equipment$/.test(item.section_name || ""));
}

function renderTrimStandardEquipment() {
  const openGroupName = `${state.trimLevel} Equipment`;
  return `
    <section class="section-block trim-standard-equipment">
      <div class="section-title"><h3>Standard & Included</h3><span>Trim equipment</span></div>
      <div class="standard-equipment-list">${renderStandardEquipmentGroups(trimEquipmentRows(), false, openGroupName)}</div>
    </section>
  `;
}

function resetStepScroll() {
  els.stepContent.scrollTo({ top: 0, left: 0 });
  els.stepContent.closest(".choice-panel")?.scrollTo({ top: 0, left: 0 });
  window.scrollTo({ top: 0, left: 0 });
}

function captureScrollPosition() {
  return {
    stepTop: els.stepContent.scrollTop,
    panelTop: els.stepContent.closest(".choice-panel")?.scrollTop || 0,
    windowX: window.scrollX,
    windowY: window.scrollY,
  };
}

function restoreScrollPosition(position) {
  if (!position) return;
  els.stepContent.scrollTo({ top: position.stepTop, left: 0 });
  els.stepContent.closest(".choice-panel")?.scrollTo({ top: position.panelTop, left: 0 });
  window.scrollTo({ top: position.windowY, left: position.windowX });
}

function renderStepContent({ resetScroll = false } = {}) {
  const step = runtimeSteps.find((item) => item.step_key === state.activeStep);
  const autoAdded = computeAutoAdded();
  let body = "";

  if (state.activeStep === "body_style" || state.activeStep === "trim_level") {
    const contextChoices = data.contextChoices
      .filter((choice) => choice.step_key === state.activeStep)
      .filter((choice) => choice.context_type !== "trim_level" || choice.body_style === state.bodyStyle)
      .sort((a, b) => Number(a.display_order || 0) - Number(b.display_order || 0));
    const section = sectionsById.get(state.activeStep === "body_style" ? "sec_context_body_style" : "sec_context_trim_level");
    body = `
      <section class="section-block">
        <div class="section-title"><h3>${section?.section_name || step?.step_label}</h3><span>${renderModeLabel(section)}</span></div>
        <div class="choice-grid">${contextChoices.map(renderContextCard).join("")}</div>
      </section>
      ${state.activeStep === "trim_level" ? renderTrimStandardEquipment() : ""}
    `;
  } else if (state.activeStep === "base_interior") {
    const interiors = validInteriorsForSelectedSeat();
    const selectedSeat = selectedSeatChoice();
    body = `
      <section class="section-block">
        <div class="section-title"><h3>Base Interior</h3><span>${interiors.length} choices</span></div>
        ${selectedSeat ? `<p class="selected-seat-context">${escapeHtml(selectedSeat.rpo)} ${escapeHtml(selectedSeat.label)}</p>` : ""}
        ${renderInteriorGroups(interiors)}
      </section>
    `;
  } else if (state.activeStep === "customer_info") {
    body = `
      <section class="section-block">
        <div class="section-title"><h3>Customer Information</h3><span>Optional order details</span></div>
        ${renderCustomerForm()}
      </section>
    `;
  } else {
    const rows = activeChoiceRows()
      .filter((choice) => choice.step_key === state.activeStep)
      .filter((choice) => !shouldHideChoice(choice))
      .sort((a, b) => {
        const sectionA = sectionsById.get(a.section_id);
        const sectionB = sectionsById.get(b.section_id);
        return (
          Number(sectionA?.section_display_order || 0) - Number(sectionB?.section_display_order || 0) ||
          a.display_order - b.display_order ||
          a.label.localeCompare(b.label)
        );
      });
    const bySection = new Map();
    for (const choice of rows) {
      if (!bySection.has(choice.section_id)) bySection.set(choice.section_id, []);
      bySection.get(choice.section_id).push(choice);
    }
    body = [...bySection.entries()]
      .map(([sectionId, choices]) => {
        const section = sectionsById.get(sectionId);
        return `
          <section class="section-block">
            <div class="section-title"><h3>${section?.section_name || sectionId}</h3><span>${renderModeLabel(section)}</span></div>
            <div class="choice-grid">${choices.map((choice) => renderChoiceCard(choice, autoAdded)).join("")}</div>
          </section>
        `;
      })
      .join("");
    if (!body) body = "<p class=\"empty\">No choices are mapped to this step for the active body and trim.</p>";
  }

  const next = nextStep();
  els.stepContent.innerHTML = `
    <header class="step-header">
      <div>
        <p class="eyebrow">Step</p>
        <h2>${step?.step_label || "Step"}</h2>
      </div>
      <span class="step-meta">${currentVariant()?.display_name || ""}</span>
    </header>
    ${body}
    ${
      next
        ? `<footer class="step-footer"><button type="button" data-next-step="${next.step_key}">Next: ${next.step_label}</button></footer>`
        : ""
    }
  `;
  if (resetScroll) resetStepScroll();
  bindCustomerForm();
  els.stepContent.querySelectorAll("[data-option]").forEach((button) => {
    button.addEventListener("click", () => {
      const choice = activeChoiceRows().find((item) => item.option_id === button.dataset.option);
      if (choice) handleChoice(choice);
    });
  });
  els.stepContent.querySelectorAll("[data-interior]").forEach((button) => {
    button.addEventListener("click", () => {
      const interior = interiorsById.get(button.dataset.interior);
      if (interior) handleInterior(interior);
    });
  });
  els.stepContent.querySelectorAll("[data-context-choice]").forEach((button) => {
    button.addEventListener("click", () => {
      const choice = data.contextChoices.find((item) => item.context_choice_id === button.dataset.contextChoice);
      if (choice && !(choice.context_type === "trim_level" && choice.body_style !== state.bodyStyle)) handleContextChoice(choice);
    });
  });
  els.stepContent.querySelector("[data-next-step]")?.addEventListener("click", goToNextStep);
}

function renderSummary() {
  const variant = currentVariant();
  const items = lineItems();
  const base = Number(variant?.base_price || 0);
  const optionsTotal = items.reduce((sum, item) => sum + Number(item.price || 0), 0);
  const total = base + optionsTotal;
  els.basePrice.textContent = formatMoney(base);
  els.summaryBase.textContent = formatMoney(base);
  els.summaryOptions.textContent = formatMoney(optionsTotal);
  els.summaryTotal.textContent = formatMoney(total);
  els.variantName.textContent = variant?.display_name || "Stingray";

  const selectedItems = items.filter((item) => item.type !== "auto_added");
  const autoItems = items.filter((item) => item.type === "auto_added");
  els.selectedList.innerHTML =
    selectedItems.map((item) => `<li><strong>${item.rpo || item.id}</strong> ${item.label} - ${formatMoney(item.price)}</li>`).join("") ||
    "<li class=\"empty\">No selections yet.</li>";
  els.autoList.innerHTML =
    autoItems.map((item) => `<li><strong>${item.rpo || item.id}</strong> ${item.label} - ${formatMoney(item.price)}<br>${item.reason || ""}</li>`).join("") ||
    "<li class=\"empty\">No auto-added RPOs.</li>";
  const missing = missingRequired();
  els.missingList.innerHTML = missing.map((item) => `<li>${item}</li>`).join("") || "<li class=\"empty\">No open required choices.</li>";
  renderStandardEquipment();

  const dataWarnings = data.validation.filter((item) => item.severity === "error");
  els.alertRegion.innerHTML = dataWarnings.map((item) => `<div class="alert">${item.message}</div>`).join("");
}

function customerInformation() {
  return {
    name: state.customer.name.trim(),
    address: state.customer.address.trim(),
    email: state.customer.email.trim(),
    phone: state.customer.phone.trim(),
    comments: state.customer.comments.trim(),
  };
}

function resetCustomerInformation() {
  for (const key of Object.keys(state.customer)) {
    state.customer[key] = "";
  }
}

function renderStandardEquipment() {
  const rows = standardEquipmentRows();
  els.selectedStandardEquipmentList.innerHTML = `
    <details class="standard-group">
      <summary>Standard & Included <span>${rows.length}</span></summary>
      <div class="nested-standard-equipment">${renderStandardEquipmentGroups(rows)}</div>
    </details>
  `;
}

function vehicleInformation(variant) {
  return {
    model_year: variant?.model_year || "",
    model: "Corvette Stingray",
    body_style: variant?.body_style || state.bodyStyle,
    trim_level: variant?.trim_level || state.trimLevel,
    variant_id: variant?.variant_id || currentVariantId(),
    display_name: variant?.display_name || "",
    base_price: Number(variant?.base_price || 0),
  };
}

function standardEquipmentSummary(variant) {
  const rows = standardEquipmentRows();
  const groups = new Map();
  for (const row of rows) {
    const label = row.section_name || "Standard Equipment";
    groups.set(label, (groups.get(label) || 0) + 1);
  }
  return {
    variant_id: variant?.variant_id || currentVariantId(),
    count: rows.length,
    groups: [...groups.entries()].map(([section_label, count]) => ({ section_label, count })),
  };
}

function sectionedOrderRecap(items, pricing) {
  const sections = new Map(
    orderSectionDefinitions.map(([section_key, section_label]) => [
      section_key,
      {
        section_key,
        section_label,
        items: [],
        section_total: 0,
      },
    ])
  );
  for (const item of items) {
    const sectionKey = item.section_key || sectionKeyForStep(item.step_key, item.type);
    const section =
      sections.get(sectionKey) ||
      {
        section_key: sectionKey,
        section_label: item.section_label || sectionLabelForKey(sectionKey),
        items: [],
        section_total: 0,
      };
    section.items.push(item);
    section.section_total += Number(item.price || 0);
    sections.set(sectionKey, section);
  }
  sections.get("vehicle").section_total = pricing.base_price;
  sections.get("pricing_summary").section_total = pricing.total_msrp;
  return [...sections.values()]
    .filter(
      (section) =>
        section.items.length ||
        ["vehicle", "pricing_summary", "customer_information"].includes(section.section_key)
    )
    .sort((a, b) => (orderSectionOrder.get(a.section_key) ?? 999) - (orderSectionOrder.get(b.section_key) ?? 999));
}

function currentOrder() {
  const variant = currentVariant();
  const items = lineItems();
  const base = Number(variant?.base_price || 0);
  const optionsTotal = items.reduce((sum, item) => sum + Number(item.price || 0), 0);
  const pricing = {
    base_price: base,
    selected_options_total: optionsTotal,
    total_msrp: base + optionsTotal,
  };
  const selectedOptions = items.filter((item) => item.type === "selected");
  const autoAddedOptions = items.filter((item) => item.type === "auto_added");
  const selectedInterior = items.find((item) => item.type === "selected_interior") || {};
  return {
    customer: customerInformation(),
    vehicle: vehicleInformation(variant),
    pricing,
    sections: sectionedOrderRecap(items, pricing),
    selected_options: selectedOptions,
    auto_added_options: autoAddedOptions,
    selected_interior: selectedInterior,
    standard_equipment_summary: standardEquipmentSummary(variant),
    metadata: {
      dataset: data.dataset,
      export_schema_version: 1,
      selected_option_ids: [...state.selected],
      selected_interior_id: state.selectedInterior,
      selected_rpos: items.filter((item) => item.type !== "auto_added").map((item) => item.rpo || item.id),
      auto_added_rpos: autoAddedOptions.map((item) => item.rpo || item.id),
      missing_required: missingRequired(),
    },
  };
}

function compactOrderItem(item) {
  return {
    rpo: item.rpo || "",
    label: item.label || item.description || "",
    price: Number(item.price || 0),
  };
}

function compactOrder() {
  const order = currentOrder();
  const customer = {
    name: order.customer.name,
    email: order.customer.email,
    phone: order.customer.phone,
    address: order.customer.address,
  };
  if (order.customer.comments) customer.comments = order.customer.comments;

  return {
    title: `${order.vehicle.model_year} ${order.vehicle.model}`,
    submitted_at: new Date().toISOString(),
    customer,
    vehicle: {
      body_style: order.vehicle.body_style,
      trim_level: order.vehicle.trim_level,
      display_name: order.vehicle.display_name,
      base_price: order.vehicle.base_price,
    },
    sections: order.sections
      .filter((section) => !["vehicle", "pricing_summary", "customer_information"].includes(section.section_key))
      .filter((section) => section.items.length)
      .map((section) => ({
        section: section.section_label,
        items: section.items.map(compactOrderItem),
      })),
    standard_equipment: {
      count: order.standard_equipment_summary.count,
    },
    msrp: order.pricing.total_msrp,
  };
}

function plainTextOrderSummary(order = compactOrder()) {
  const lines = [
    order.title,
    "",
    `Name: ${order.customer.name || ""}`,
    `Email: ${order.customer.email || ""}`,
    `Phone: ${order.customer.phone || ""}`,
    `Address: ${order.customer.address || ""}`,
  ];
  if (order.customer.comments) lines.push(`Comments: ${order.customer.comments}`);
  lines.push(
    `Submitted: ${order.submitted_at}`,
    "",
    "Vehicle",
    order.vehicle.body_style || "",
    order.vehicle.trim_level || "",
    order.vehicle.display_name || "",
    `Base MSRP: ${formatMoney(order.vehicle.base_price)}`,
    ""
  );

  for (const section of order.sections) {
    lines.push(section.section);
    for (const item of section.items) {
      lines.push(`${item.rpo} ${item.label} ${formatMoney(item.price)}`.trim());
    }
    lines.push("");
  }

  if (Number.isFinite(Number(order.standard_equipment?.count))) {
    lines.push(`Standard & Included: ${Number(order.standard_equipment.count)} items`, "");
  }
  lines.push(`MSRP: ${formatMoney(order.msrp)}`);
  return lines.join("\n").replace(/\n{3,}/g, "\n\n");
}

function download(filename, content, type) {
  const blob = new Blob([content], { type });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.click();
  URL.revokeObjectURL(url);
}

function exportJson() {
  download("stingray-order-summary.json", JSON.stringify(compactOrder(), null, 2), "application/json");
}

function exportCsv() {
  const order = compactOrder();
  const rows = ["section,rpo,label,price"];
  for (const section of order.sections) {
    for (const item of section.items) {
      rows.push([section.section, item.rpo, item.label, item.price].map((value) => JSON.stringify(value ?? "")).join(","));
    }
  }
  rows.push(["MSRP", "", "", order.msrp].map((value) => JSON.stringify(value)).join(","));
  download("stingray-order-summary.csv", rows.join("\n"), "text/csv");
}

function render({ resetScroll = false, preserveScroll = false } = {}) {
  const scrollPosition = preserveScroll ? captureScrollPosition() : null;
  renderVehicleContext();
  renderStepRail();
  renderStepContent({ resetScroll });
  renderSummary();
  restoreScrollPosition(scrollPosition);
}

function init() {
  const first = variants[0];
  state.bodyStyle = first.body_style;
  state.trimLevel = first.trim_level;
  resetDefaults();
  reconcileSelections();
  els.resetButton.addEventListener("click", () => {
    resetDefaults();
    resetCustomerInformation();
    reconcileSelections();
    render({ resetScroll: true });
  });
  els.exportJsonButton.addEventListener("click", exportJson);
  els.exportCsvButton.addEventListener("click", exportCsv);
  render();
}

init();
