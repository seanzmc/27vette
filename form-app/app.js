const data = window.STINGRAY_FORM_DATA;

const state = {
  bodyStyle: "",
  trimLevel: "",
  selected: new Set(),
  selectedInterior: "",
  activeStep: "paint",
};

const els = {
  bodySelect: document.querySelector("#bodySelect"),
  trimSelect: document.querySelector("#trimSelect"),
  basePrice: document.querySelector("#basePrice"),
  summaryBase: document.querySelector("#summaryBase"),
  summaryOptions: document.querySelector("#summaryOptions"),
  summaryTotal: document.querySelector("#summaryTotal"),
  variantName: document.querySelector("#variantName"),
  stepRail: document.querySelector("#stepRail"),
  stepContent: document.querySelector("#stepContent"),
  selectedList: document.querySelector("#selectedList"),
  autoList: document.querySelector("#autoList"),
  missingList: document.querySelector("#missingList"),
  alertRegion: document.querySelector("#alertRegion"),
  resetButton: document.querySelector("#resetButton"),
  exportJsonButton: document.querySelector("#exportJsonButton"),
  exportCsvButton: document.querySelector("#exportCsvButton"),
};

const runtimeSteps = data.steps.filter((step) => !["body_style", "trim_level", "summary"].includes(step.step_key));
const variants = [...data.variants].sort((a, b) => a.display_order - b.display_order);
const choicesByOption = new Map();
const sectionsById = new Map(data.sections.map((section) => [section.section_id, section]));
const optionsById = new Map();
const interiorsById = new Map(data.interiors.map((interior) => [interior.interior_id, interior]));
const ruleTargetsBySource = new Map();
const rulesByTarget = new Map();
const priceRulesByTarget = new Map();

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

function formatMoney(value) {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  }).format(Number(value || 0));
}

function currentVariant() {
  return variants.find((variant) => variant.body_style === state.bodyStyle && variant.trim_level === state.trimLevel);
}

function currentVariantId() {
  return currentVariant()?.variant_id || "";
}

function activeChoiceRows() {
  const variantId = currentVariantId();
  return data.choices.filter((choice) => choice.variant_id === variantId);
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

function computeAutoAdded() {
  const autoAdded = new Map();
  const selectedIds = new Set(state.selected);
  if (state.selectedInterior) selectedIds.add(state.selectedInterior);

  for (const sourceId of selectedIds) {
    const rules = ruleTargetsBySource.get(sourceId) || [];
    for (const rule of rules) {
      if (rule.rule_type === "includes") {
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
  if (choice.selectable !== "True" && choice.status !== "standard") return "Display-only source row.";

  const selectedIds = selectedContextIds();
  const targetRules = rulesByTarget.get(choice.option_id) || [];
  for (const rule of targetRules) {
    if (rule.rule_type === "excludes" && selectedIds.has(rule.source_id)) {
      return rule.disabled_reason || `Blocked by ${getEntityLabel(rule.source_id)}.`;
    }
  }

  const sourceRules = ruleTargetsBySource.get(choice.option_id) || [];
  for (const rule of sourceRules) {
    if (rule.rule_type === "requires" && !selectedIds.has(rule.target_id)) {
      return rule.disabled_reason || `Requires ${getEntityLabel(rule.target_id)}.`;
    }
    if (rule.rule_type === "excludes" && selectedIds.has(rule.target_id)) {
      return `Conflicts with ${getEntityLabel(rule.target_id)}.`;
    }
  }

  return "";
}

function disableReasonForInterior(interior) {
  const selectedIds = selectedContextIds();
  const rules = ruleTargetsBySource.get(interior.interior_id) || [];
  for (const rule of rules) {
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
    if (rule.price_rule_type === "override" && selectedIds.has(rule.condition_option_id)) {
      return Number(rule.price_value || 0);
    }
  }
  return Number(optionsById.get(optionId)?.base_price || 0);
}

function lineItems() {
  const autoAdded = computeAutoAdded();
  const rows = [];
  for (const id of state.selected) {
    const option = optionsById.get(id);
    if (option) {
      rows.push({
        id,
        rpo: option.rpo,
        label: option.label,
        type: "selected",
        price: optionPrice(id),
      });
    }
  }
  if (state.selectedInterior) {
    const interior = interiorsById.get(state.selectedInterior);
    rows.push({
      id: state.selectedInterior,
      rpo: interior.interior_code,
      label: interior.interior_name,
      type: "selected_interior",
      price: Number(interior.price || 0),
    });
  }
  for (const [id, reason] of autoAdded) {
    const option = optionsById.get(id);
    if (option) {
      rows.push({
        id,
        rpo: option.rpo,
        label: option.label,
        type: "auto_added",
        price: optionPrice(id),
        reason,
      });
    }
  }
  return rows;
}

function missingRequired() {
  const rows = activeChoiceRows();
  const sections = new Map();
  for (const choice of rows) {
    const section = sectionsById.get(choice.section_id);
    if (!section || section.selection_mode !== "single_select_req") continue;
    if (choice.step_key === "base_interior") continue;
    if (choice.status === "unavailable") continue;
    if (!sections.has(choice.section_id)) sections.set(choice.section_id, section);
  }
  const missing = [];
  for (const [sectionId, section] of sections) {
    const hasSelection = [...state.selected].some((id) => optionsById.get(id)?.section_id === sectionId);
    if (!hasSelection) missing.push(section.section_name);
  }
  if (!state.selectedInterior) missing.push("Base Interior");
  return missing;
}

function resetDefaults() {
  state.selected.clear();
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
}

function setBodyAndTrim(bodyStyle, trimLevel) {
  state.bodyStyle = bodyStyle;
  state.trimLevel = trimLevel;
  resetDefaults();
  render();
}

function handleChoice(choice) {
  const reason = disableReasonForChoice(choice);
  if (reason) return;
  const section = sectionsById.get(choice.section_id);
  if (section?.choice_mode === "single") {
    for (const id of [...state.selected]) {
      if (optionsById.get(id)?.section_id === choice.section_id) state.selected.delete(id);
    }
    state.selected.add(choice.option_id);
  } else if (state.selected.has(choice.option_id)) {
    state.selected.delete(choice.option_id);
  } else {
    state.selected.add(choice.option_id);
  }
  render();
}

function handleInterior(interior) {
  const reason = disableReasonForInterior(interior);
  if (reason) return;
  state.selectedInterior = state.selectedInterior === interior.interior_id ? "" : interior.interior_id;
  render();
}

function renderSelectors() {
  const bodies = [...new Set(variants.map((variant) => variant.body_style))];
  els.bodySelect.innerHTML = bodies
    .map((body) => `<option value="${body}" ${body === state.bodyStyle ? "selected" : ""}>${body[0].toUpperCase() + body.slice(1)}</option>`)
    .join("");
  const trims = variants
    .filter((variant) => variant.body_style === state.bodyStyle)
    .map((variant) => variant.trim_level);
  els.trimSelect.innerHTML = trims.map((trim) => `<option value="${trim}" ${trim === state.trimLevel ? "selected" : ""}>${trim}</option>`).join("");
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
      render();
    });
  });
}

function renderChoiceCard(choice, autoAdded) {
  const selected = state.selected.has(choice.option_id);
  const autoReason = autoAdded.get(choice.option_id);
  const disabledReason = autoReason ? "" : disableReasonForChoice(choice);
  const classes = ["choice-card"];
  if (selected) classes.push("selected");
  if (disabledReason) classes.push("disabled");
  if (autoReason) classes.push("auto");
  return `
    <button class="${classes.join(" ")}" type="button" data-option="${choice.option_id}" ${disabledReason ? "aria-disabled=\"true\"" : ""}>
      <span class="topline"><span class="rpo">${choice.rpo || choice.option_id}</span><span class="price">${formatMoney(optionPrice(choice.option_id))}</span></span>
      <p class="choice-name">${choice.label}</p>
      <p class="choice-note">${choice.description || choice.status_label}</p>
      ${disabledReason ? `<p class="disabled-reason">${disabledReason}</p>` : ""}
      ${autoReason ? `<p class="auto-reason">${autoReason}</p>` : ""}
    </button>
  `;
}

function renderInteriorCard(interior) {
  const selected = state.selectedInterior === interior.interior_id;
  const disabledReason = disableReasonForInterior(interior);
  const classes = ["choice-card"];
  if (selected) classes.push("selected");
  if (disabledReason) classes.push("disabled");
  const detail = [interior.material, interior.source_note].filter(Boolean).join(" ");
  return `
    <button class="${classes.join(" ")}" type="button" data-interior="${interior.interior_id}" ${disabledReason ? "aria-disabled=\"true\"" : ""}>
      <span class="topline"><span class="rpo">${interior.interior_code}</span><span class="price">${formatMoney(interior.price)}</span></span>
      <p class="choice-name">${interior.interior_name}</p>
      <p class="choice-note">${detail || interior.interior_id}</p>
      ${disabledReason ? `<p class="disabled-reason">${disabledReason}</p>` : ""}
    </button>
  `;
}

function renderStepContent() {
  const step = runtimeSteps.find((item) => item.step_key === state.activeStep);
  const autoAdded = computeAutoAdded();
  let body = "";

  if (state.activeStep === "base_interior") {
    const selectedSeat = [...state.selected].map((id) => optionsById.get(id)).find((choice) => choice?.step_key === "seat");
    const interiors = data.interiors.filter((interior) => {
      if (interior.trim_level !== state.trimLevel) return false;
      if (selectedSeat?.rpo && interior.seat_code !== selectedSeat.rpo) return false;
      return true;
    });
    body = `
      <section class="section-block">
        <div class="section-title"><h3>Base Interior</h3><span>${interiors.length} choices</span></div>
        <div class="choice-grid">${interiors.map(renderInteriorCard).join("") || "<p class=\"empty\">Select a seat first.</p>"}</div>
      </section>
    `;
  } else {
    const rows = activeChoiceRows()
      .filter((choice) => choice.step_key === state.activeStep)
      .sort((a, b) => a.section_name.localeCompare(b.section_name) || a.display_order - b.display_order || a.label.localeCompare(b.label));
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
            <div class="section-title"><h3>${section?.section_name || sectionId}</h3><span>${section?.selection_mode || ""}</span></div>
            <div class="choice-grid">${choices.map((choice) => renderChoiceCard(choice, autoAdded)).join("")}</div>
          </section>
        `;
      })
      .join("");
    if (!body) body = "<p class=\"empty\">No choices are mapped to this step for the active body and trim.</p>";
  }

  els.stepContent.innerHTML = `
    <header class="step-header">
      <div>
        <p class="eyebrow">Step</p>
        <h2>${step?.step_label || "Step"}</h2>
      </div>
      <span class="step-meta">${currentVariant()?.display_name || ""}</span>
    </header>
    ${body}
  `;
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

  const dataWarnings = data.validation.filter((item) => item.severity === "error");
  els.alertRegion.innerHTML = dataWarnings.map((item) => `<div class="alert">${item.message}</div>`).join("");
}

function currentOrder() {
  const variant = currentVariant();
  const items = lineItems();
  const base = Number(variant?.base_price || 0);
  const optionsTotal = items.reduce((sum, item) => sum + Number(item.price || 0), 0);
  return {
    dataset: data.dataset,
    variant,
    selected_option_ids: [...state.selected],
    selected_interior_id: state.selectedInterior,
    selected_rpos: items.filter((item) => item.type !== "auto_added").map((item) => item.rpo || item.id),
    auto_added_rpos: items.filter((item) => item.type === "auto_added").map((item) => item.rpo || item.id),
    line_items: items,
    missing_required: missingRequired(),
    pricing: {
      base_msrp: base,
      options_total: optionsTotal,
      total_msrp: base + optionsTotal,
    },
  };
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
  download("stingray-order.json", JSON.stringify(currentOrder(), null, 2), "application/json");
}

function exportCsv() {
  const order = currentOrder();
  const headers = ["type", "id", "rpo", "label", "price"];
  const rows = order.line_items.map((item) => headers.map((key) => JSON.stringify(item[key] ?? "")).join(","));
  rows.unshift(headers.join(","));
  rows.push(["total", "", "", "Total MSRP", order.pricing.total_msrp].map((value) => JSON.stringify(value)).join(","));
  download("stingray-order.csv", rows.join("\n"), "text/csv");
}

function render() {
  renderSelectors();
  renderStepRail();
  renderStepContent();
  renderSummary();
}

function init() {
  const first = variants[0];
  state.bodyStyle = first.body_style;
  state.trimLevel = first.trim_level;
  resetDefaults();
  els.bodySelect.addEventListener("change", () => {
    const nextBody = els.bodySelect.value;
    const nextTrim = variants.find((variant) => variant.body_style === nextBody)?.trim_level;
    setBodyAndTrim(nextBody, nextTrim);
  });
  els.trimSelect.addEventListener("change", () => setBodyAndTrim(state.bodyStyle, els.trimSelect.value));
  els.resetButton.addEventListener("click", () => {
    resetDefaults();
    render();
  });
  els.exportJsonButton.addEventListener("click", exportJson);
  els.exportCsvButton.addEventListener("click", exportCsv);
  render();
}

init();
