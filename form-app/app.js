function formDataRegistry() {
  return (
    window.CORVETTE_FORM_DATA || {
      defaultModelKey: "stingray",
      models: {
        stingray: {
          key: "stingray",
          label: "Stingray",
          modelName: "Corvette Stingray",
          exportSlug: "stingray",
          data: window.STINGRAY_FORM_DATA,
        },
      },
    }
  );
}

const registry = formDataRegistry();
const DEALER_SUBMIT_ENDPOINT = "https://stingraychevroletcorvette.com/wp-json/corvette-build/v1/submit";
const DEALER_SUBMIT_HELPER_TEXT = "Form will be submitted to Stingray Chevrolet in Plant City, FL.";
const TURNSTILE_SITE_KEY = "0x4AAAAAADQDIWu6RmhF8_wH";
let activeModelKey = registry.defaultModelKey || "stingray";
let activeModel = registry.models[activeModelKey] || registry.models.stingray;
let data = activeModel.data;

const state = {
  bodyStyle: "",
  trimLevel: "",
  selected: new Set(),
  userSelected: new Set(),
  selectedInterior: "",
  activeStep: "model",
  vehicleSetupStage: "model",
  customer: {
    name: "",
    address: "",
    email: "",
    phone: "",
    comments: "",
  },
  dealerSubmissionComplete: false,
  dealerSubmissionEntryId: "",
  turnstileToken: "",
  turnstileWidgetId: "",
};

const els = {
  appShell: document.querySelector(".app-shell"),
  summaryBase: document.querySelector("#summaryBase"),
  summaryOptions: document.querySelector("#summaryOptions"),
  summaryTotal: document.querySelector("#summaryTotal"),
  variantName: document.querySelector("#variantName"),
  stepRail: document.querySelector("#stepRail"),
  stepContent: document.querySelector("#stepContent"),
  mobileProgress: document.querySelector("#mobileProgress"),
  mobileStepCount: document.querySelector("#mobileStepCount"),
  mobileStepName: document.querySelector("#mobileStepName"),
  mobilePrevStep: document.querySelector("#mobilePrevStep"),
  mobileNextStep: document.querySelector("#mobileNextStep"),
  openStepDrawerButton: document.querySelector("#openStepDrawerButton"),
  closeStepDrawerButton: document.querySelector("#closeStepDrawerButton"),
  openSummaryDrawerButton: document.querySelector("#openSummaryDrawerButton"),
  closeSummaryDrawerButton: document.querySelector("#closeSummaryDrawerButton"),
  mobileDrawerBackdrop: document.querySelector("#mobileDrawerBackdrop"),
  mobileSummaryButton: document.querySelector("#mobileSummaryButton"),
  mobileSummaryTotal: document.querySelector("#mobileSummaryTotal"),
  mobileSummarySelected: document.querySelector("#mobileSummarySelected"),
  mobileSummaryMissing: document.querySelector("#mobileSummaryMissing"),
  selectedList: document.querySelector("#selectedList"),
  selectedStandardEquipmentList: document.querySelector("#selectedStandardEquipmentList"),
  autoList: document.querySelector("#autoList"),
  missingList: document.querySelector("#missingList"),
  summaryDrawer: document.querySelector("#summaryDrawer"),
  requirementsCard: document.querySelector("#requirementsCard"),
  alertRegion: document.querySelector("#alertRegion"),
  toastRegion: document.querySelector("#toastRegion"),
  resetButton: document.querySelector("#resetButton"),
  downloadBuildButton: document.querySelector("#downloadBuildButton"),
  submitDealerButton: document.querySelector("#submitDealerButton"),
  dealerSubmitModal: document.querySelector("#dealerSubmitModal"),
  dealerSubmitForm: document.querySelector("#dealerSubmitForm"),
  dealerSubmitName: document.querySelector("#dealerSubmitName"),
  dealerSubmitEmail: document.querySelector("#dealerSubmitEmail"),
  dealerSubmitPhone: document.querySelector("#dealerSubmitPhone"),
  dealerSubmitComments: document.querySelector("#dealerSubmitComments"),
  dealerSubmitStatus: document.querySelector("#dealerSubmitStatus"),
  dealerTurnstile: document.querySelector("#dealerTurnstile"),
  dealerSubmitCloseButton: document.querySelector("#dealerSubmitCloseButton"),
  dealerSubmitCancelButton: document.querySelector("#dealerSubmitCancelButton"),
  dealerSubmitConfirmButton: document.querySelector("#dealerSubmitConfirmButton"),
  confirmActionModal: document.querySelector("#confirmActionModal"),
  confirmActionTitle: document.querySelector("#confirmActionTitle"),
  confirmActionMessage: document.querySelector("#confirmActionMessage"),
  confirmActionCancelButton: document.querySelector("#confirmActionCancelButton"),
  confirmActionConfirmButton: document.querySelector("#confirmActionConfirmButton"),
  appTitle: document.querySelector("#appTitle"),
};

const modelStep = {
  step_key: "model",
  step_label: "Vehicle Setup",
};
const vehicleSetupStepKeys = new Set(["model", "body_style", "trim_level"]);
const vehicleSetupStages = ["model", "body_style", "trim_level", "ready"];
const vehicleSetupHighlights = {
  stingray: {
    eyebrow: "Refreshed everyday supercar",
    title: "Next-generation LS6 power for the everyday supercar",
    description:
      "The 2027 Stingray moves to Corvette’s next-generation LS6 6.7L V8, pairing 535 horsepower with the familiar rear-drive Stingray foundation before you choose colors and options.",
    facts: ["LS6 6.7L V8", "535 hp / 520 lb-ft", "Available center-exit exhaust"],
  },
  grandSport: {
    cardSubtitle: "Purist, rear-wheel-drive performance",
    eyebrow: "PURIST, REAR-WHEEL-DRIVE PERFORMANCE",
    title: "The reborn legend, tuned for a pure rear-drive sweet spot",
    description:
      "The 2027 Grand Sport pairs Corvette's next-generation LS6 6.7L V8 with a wide-body stance and heritage styling for a focused rear-drive balance of street and track.",
    facts: ["LS6 6.7L V8", "535 hp / 520 lb-ft", "Available quad center exhaust"],
  },
  z06: {
    cardSubtitle: "Track-born, street-legal supercar",
    eyebrow: "TRACK-BORN, STREET-LEGAL SUPERCAR",
    title: "The most powerful naturally aspirated V8 ever built",
    description:
      "The Z06 pairs the hand-built LT6 5.5L flat-plane V8 — 670 horsepower to an 8,600 rpm redline — with a wide-body stance, aggressive aero and quad center exhaust.",
    facts: ["LT6 5.5L V8", "670 hp / 8,600 rpm", "Quad center exhaust"],
  },
};
let runtimeSteps = [];
let variants = [];
let pendingConfirmationAction = null;
const choicesByOption = new Map();
const sectionsById = new Map();
const optionsById = new Map();
const interiorsById = new Map();
const ruleTargetsBySource = new Map();
const rulesByTarget = new Map();
const priceRulesByTarget = new Map();
const ruleGroupsBySource = new Map();
const exclusiveGroupByOption = new Map();

function rebuildDataIndexes() {
  runtimeSteps = [modelStep, ...(data.steps || []).filter((step) => step.step_key !== "summary")];
  variants = [...(data.variants || [])].sort((a, b) => a.display_order - b.display_order);
  choicesByOption.clear();
  sectionsById.clear();
  optionsById.clear();
  interiorsById.clear();
  ruleTargetsBySource.clear();
  rulesByTarget.clear();
  priceRulesByTarget.clear();
  ruleGroupsBySource.clear();
  exclusiveGroupByOption.clear();

  for (const section of data.sections || []) {
    sectionsById.set(section.section_id, section);
  }

  for (const interior of data.interiors || []) {
    interiorsById.set(interior.interior_id, interior);
  }

  for (const choice of data.choices || []) {
    if (!choicesByOption.has(choice.option_id)) choicesByOption.set(choice.option_id, []);
    choicesByOption.get(choice.option_id).push(choice);
    if (!optionsById.has(choice.option_id)) optionsById.set(choice.option_id, choice);
  }

  for (const rule of data.rules || []) {
    if (!ruleTargetsBySource.has(rule.source_id)) ruleTargetsBySource.set(rule.source_id, []);
    ruleTargetsBySource.get(rule.source_id).push(rule);
    if (!rulesByTarget.has(rule.target_id)) rulesByTarget.set(rule.target_id, []);
    rulesByTarget.get(rule.target_id).push(rule);
  }

  for (const rule of data.priceRules || []) {
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
}

rebuildDataIndexes();

function formatMoney(value) {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  }).format(Number(value || 0));
}

function renderPriceSpan(value, className = "price") {
  const amount = Number(value || 0);
  if (amount === 0) return `<span class="${className} included">Included</span>`;
  return `<span class="${className}">${formatMoney(amount)}</span>`;
}

/* ---- 1a "Full Carbon": dynamic accent follows the selected exterior paint (SPEC §2) ---- */
const ACCENT_FOLLOWS_PAINT = true;
const DEFAULT_PAINT_ACCENT = { accent: "#d0425a", accentDark: "#b22234", onAccent: "#ffffff", accentGlow: "rgba(208,66,90,.40)" };
const PAINT_ACCENTS = {
  GKZ: DEFAULT_PAINT_ACCENT,
  G4Z: { accent: "#4fae6e", accentDark: "#2e7d4f", onAccent: "#06210f", accentGlow: "rgba(79,174,110,.36)" },
  GTR: { accent: "#3f73ff", accentDark: "#1d4ed8", onAccent: "#ffffff", accentGlow: "rgba(63,115,255,.40)" },
  GBK: { accent: "#ffc81f", accentDark: "#e0a400", onAccent: "#1c1606", accentGlow: "rgba(255,200,31,.36)" },
  G26: { accent: "#ff6a1a", accentDark: "#d8480a", onAccent: "#1c0d04", accentGlow: "rgba(255,106,26,.38)" },
  GPH: { accent: "#cf3e5e", accentDark: "#8a1a2c", onAccent: "#ffffff", accentGlow: "rgba(207,62,94,.38)" },
};

function formAssetBase() {
  return typeof window !== "undefined" && window.SC_FORM_ASSET_BASE ? window.SC_FORM_ASSET_BASE : "./assets/";
}

function selectedPaintChoice() {
  const candidateIds = new Set([...state.selected, ...computeAutoAdded().keys()]);
  for (const optionId of candidateIds) {
    const option = optionsById.get(optionId);
    if (option?.step_key === "paint") return option;
  }
  return null;
}

function applyAccentForPaint() {
  if (!ACCENT_FOLLOWS_PAINT || typeof document === "undefined") return;
  const paint = selectedPaintChoice();
  const theme = (paint && PAINT_ACCENTS[String(paint.rpo || "").toUpperCase()]) || DEFAULT_PAINT_ACCENT;
  const rootStyle = document.documentElement.style;
  rootStyle.setProperty("--accent", theme.accent);
  rootStyle.setProperty("--accent-dark", theme.accentDark);
  rootStyle.setProperty("--on-accent", theme.onAccent);
  rootStyle.setProperty("--accent-glow", theme.accentGlow);
}

function renderVehicleStage() {
  const paint = selectedPaintChoice();
  const rpo = String(paint?.rpo || "GKZ").toUpperCase();
  const name = paint?.label || "Torch Red";
  return `
    <div class="vehicle-stage">
      <div class="vehicle-stage-glow"></div>
      <img src="${formAssetBase()}vehicle/${rpo.toLowerCase()}.png" alt="${escapeHtml(name)}">
      <div class="vehicle-stage-pill"><span class="rpo">${escapeHtml(rpo)}</span><span>${escapeHtml(name)}</span></div>
    </div>
  `;
}

function escapeHtml(value) {
  return String(value || "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function truthyValue(value) {
  return ["true", "1", "yes", "y"].includes(String(value || "").trim().toLowerCase());
}

function plainTooltipText(content) {
  return String(content || "").replace(/\s+/g, " ").trim();
}

function cleanTooltipFragment(value) {
  return String(value || "")
    .replace(/^\s*(?:,|;|\.|and\b|or\b|with\b)+\s*/i, "")
    .replace(/\s+/g, " ")
    .trim();
}

function formatTooltipContent(content) {
  const text = plainTooltipText(content);
  if (!text) return "";
  const codeMatches = [...text.matchAll(/\(([A-Z0-9]{2,4})\)/g)];
  const shouldStructure = text.length >= 120 && codeMatches.length >= 2 && /\bincludes?\b/i.test(text);
  if (!shouldStructure) return escapeHtml(text);

  const firstMatch = codeMatches[0];
  const includesIndex = text.search(/\bincludes?\b/i);
  const leadEnd = includesIndex >= 0 ? Math.min(firstMatch.index, includesIndex + text.slice(includesIndex).match(/\bincludes?\b/i)[0].length) : firstMatch.index;
  const lead = cleanTooltipFragment(text.slice(0, leadEnd));
  const bullets = codeMatches.map((match, index) => {
    const next = codeMatches[index + 1];
    const start = match.index + match[0].length;
    const end = next ? next.index : text.length;
    return {
      code: match[1],
      text: cleanTooltipFragment(text.slice(start, end)),
    };
  }).filter((item) => item.text);

  if (bullets.length < 2) return escapeHtml(text);
  return `
    <span class="tooltip-content structured">
      ${lead ? `<span class="tooltip-lead">${escapeHtml(lead)}</span>` : ""}
      <ul class="tooltip-list">
        ${bullets.map((item) => `<li><span class="tooltip-code">${escapeHtml(item.code)}</span><span>${escapeHtml(item.text)}</span></li>`).join("")}
      </ul>
    </span>
  `;
}

function renderInfoTooltip(content, label = "More information", { focusable = true, icon = true, triggerText = "" } = {}) {
  if (!content) return "";
  const safeContent = formatTooltipContent(content);
  const safeLabel = escapeHtml(label);
  const ariaContent = escapeHtml(plainTooltipText(content));
  return `
    <span class="info-tooltip" ${focusable ? "tabindex=\"0\"" : ""} aria-label="${safeLabel}: ${ariaContent}">
      ${triggerText ? `<span class="tooltip-trigger-text">${escapeHtml(triggerText)}</span>` : ""}
      ${icon ? `<span class="info-icon" aria-hidden="true">i</span>` : ""}
      <span class="tooltip-panel" role="tooltip">${safeContent}</span>
    </span>
  `;
}

function descriptiveTooltipText(value) {
  const text = String(value || "").trim();
  if (!text) return "";
  const normalized = text.toLowerCase().replace(/[.。]+$/g, "");
  if (["available", "selected", "current selection", "select to continue"].includes(normalized)) return "";
  return text;
}

function renderStatePill(label, className, tooltip) {
  if (tooltip) {
    const safeLabel = escapeHtml(label);
    const safeTooltip = escapeHtml(plainTooltipText(tooltip));
    const tooltipContent = formatTooltipContent(tooltip);
    return `
      <span class="choice-state ${className} info-tooltip" tabindex="0" aria-label="${safeLabel} details: ${safeTooltip}">
        <span class="tooltip-trigger-text">${safeLabel}</span>
        <span class="tooltip-panel" role="tooltip">${tooltipContent}</span>
      </span>
    `;
  }
  return `
    <span class="choice-state ${className}"><span>${escapeHtml(label)}</span></span>
  `;
}

function renderChoiceAvailability(content = "") {
  return `<div class="choice-availability">${content}</div>`;
}

function cardImageFit(value) {
  return ["cover", "contain", "swatch"].includes(value) ? value : "cover";
}

function cardImagePosition(value) {
  const position = String(value || "center").trim();
  if (!position || !/^[\w\s.%/-]+$/.test(position)) return "center";
  return position;
}

function cardHasMedia(row = {}) {
  return Boolean(String(row.image_url || "").trim());
}

function cardSupportsHoverMedia(row = {}) {
  return row.context_type === "body_style" || String(row.context_choice_id || "").startsWith("body_style__");
}

function renderCardMedia(row = {}, fallbackAlt = "", { disabled = false } = {}) {
  const imageUrl = String(row.image_url || "").trim();
  if (!imageUrl) return "";
  const imageAlt = String(row.image_alt || fallbackAlt || "").trim();
  const hoverImageUrl = cardSupportsHoverMedia(row) ? String(row.hover_image_url || "").trim() : "";
  const hoverImageAlt = String(row.hover_image_alt || imageAlt || fallbackAlt || "").trim();
  const imageFit = cardImageFit(row.image_fit);
  const imagePosition = cardImagePosition(row.image_position);
  const hoverImagePosition = cardImagePosition(row.hover_image_position || row.image_position);
  const loading = hoverImageUrl ? "eager" : "lazy";
  const fetchPriority = hoverImageUrl ? "high" : "auto";
  const classes = ["choice-media"];
  if (disabled) classes.push("disabled");
  if (hoverImageUrl) classes.push("has-hover-media");
  return `
    <span class="${classes.join(" ")}" data-fit="${escapeHtml(imageFit)}">
      <img class="choice-media-base" src="${escapeHtml(imageUrl)}" alt="${escapeHtml(imageAlt)}" loading="${loading}" decoding="async" fetchpriority="${fetchPriority}" draggable="false" style="object-position: ${escapeHtml(imagePosition)};">
      ${hoverImageUrl ? `<img class="choice-media-hover" src="${escapeHtml(hoverImageUrl)}" alt="${escapeHtml(hoverImageAlt)}" loading="eager" decoding="async" fetchpriority="high" draggable="false" style="object-position: ${escapeHtml(hoverImagePosition)};">` : ""}
    </span>
  `;
}

function tooltipPanelForTrigger(trigger) {
  return trigger?._floatingTooltipPanel || trigger?.querySelector?.(".tooltip-panel") || null;
}

let lastTooltipTouchHandledAt = 0;

function hideTooltip(trigger) {
  const panel = tooltipPanelForTrigger(trigger);
  if (panel?.dataset?.floating === "viewport") delete panel.dataset.open;
}

function tooltipShouldFloat(trigger) {
  return Boolean(trigger.closest?.("#summaryDrawer") || isMobileViewport());
}

function closeTooltips(exceptTrigger = null) {
  if (!document?.querySelectorAll) return;
  document.querySelectorAll(".info-tooltip.is-open").forEach((trigger) => {
    if (trigger !== exceptTrigger) {
      trigger.classList?.remove("is-open");
      hideTooltip(trigger);
    }
  });
  document.querySelectorAll('.tooltip-panel[data-floating="viewport"][data-open="true"]').forEach((panel) => {
    if (panel.__tooltipTrigger !== exceptTrigger) delete panel.dataset.open;
  });
}

function positionTooltip(trigger) {
  const panel = tooltipPanelForTrigger(trigger);
  if (!panel) return;
  const margin = 10;
  const floatsToViewport = tooltipShouldFloat(trigger);
  if (floatsToViewport && document.body && panel.parentElement !== document.body) {
    trigger._floatingTooltipPanel = panel;
    panel.__tooltipTrigger = trigger;
    document.body.appendChild(panel);
  }
  panel.style.left = "";
  panel.style.right = "";
  panel.style.top = "";
  panel.style.bottom = "";
  if (panel.dataset) {
    if (floatsToViewport) {
      panel.dataset.floating = "viewport";
      panel.dataset.open = "true";
    } else {
      delete panel.dataset.floating;
      delete panel.dataset.open;
    }
  }
  if (!trigger.getBoundingClientRect || !panel.getBoundingClientRect) return;
  const triggerRect = trigger.getBoundingClientRect();
  const panelRect = panel.getBoundingClientRect();
  const viewportWidth = window.innerWidth || document.documentElement?.clientWidth || 360;
  const viewportHeight = window.innerHeight || document.documentElement?.clientHeight || 640;

  let left = triggerRect.right - panelRect.width;
  left = Math.min(Math.max(left, margin), viewportWidth - panelRect.width - margin);
  let top = triggerRect.bottom + 8;
  if (top + panelRect.height > viewportHeight - margin) {
    top = triggerRect.top - panelRect.height - 8;
  }
  top = Math.min(Math.max(top, margin), viewportHeight - panelRect.height - margin);

  panel.style.left = `${Math.round(floatsToViewport ? left : left - triggerRect.left)}px`;
  panel.style.top = `${Math.round(floatsToViewport ? top : top - triggerRect.top)}px`;
}

function toggleTooltip(trigger, event) {
  event?.preventDefault?.();
  event?.stopPropagation?.();
  const shouldOpen = !trigger.classList?.contains("is-open");
  closeTooltips(trigger);
  trigger.classList?.toggle("is-open", shouldOpen);
  if (shouldOpen) positionTooltip(trigger);
  else hideTooltip(trigger);
}

function markTooltipTouchHandled(trigger) {
  lastTooltipTouchHandledAt = Date.now();
  trigger._tooltipTouchHandledAt = lastTooltipTouchHandledAt;
}

function recentlyHandledTooltipTouch(trigger) {
  return Date.now() - Number(trigger._tooltipTouchHandledAt || 0) < 500;
}

function recentlyHandledAnyTooltipTouch() {
  return Date.now() - lastTooltipTouchHandledAt < 500;
}

function stopEventAfterTooltipTouch(event) {
  if (!recentlyHandledAnyTooltipTouch()) return false;
  event?.preventDefault?.();
  event?.stopPropagation?.();
  return true;
}

function bindTooltips(root = document) {
  if (!root?.querySelectorAll) return;
  root.querySelectorAll(".info-tooltip").forEach((trigger) => {
    if (trigger.dataset?.tooltipBound === "true") return;
    if (trigger.dataset) trigger.dataset.tooltipBound = "true";
    trigger.addEventListener("mouseenter", () => positionTooltip(trigger));
    trigger.addEventListener("mouseleave", () => {
      if (!trigger.classList?.contains("is-open")) hideTooltip(trigger);
    });
    trigger.addEventListener("focus", () => positionTooltip(trigger));
    trigger.addEventListener("blur", () => {
      if (!trigger.classList?.contains("is-open")) hideTooltip(trigger);
    });
    trigger.addEventListener("pointerup", (event) => {
      if (!event.pointerType || event.pointerType === "mouse") return;
      markTooltipTouchHandled(trigger);
      toggleTooltip(trigger, event);
    });
    trigger.addEventListener("touchend", (event) => {
      if (recentlyHandledTooltipTouch(trigger)) return;
      markTooltipTouchHandled(trigger);
      toggleTooltip(trigger, event);
    });
    trigger.addEventListener("click", (event) => {
      if (recentlyHandledTooltipTouch(trigger)) {
        event.preventDefault();
        event.stopPropagation();
        return;
      }
      toggleTooltip(trigger, event);
    });
    trigger.addEventListener("keydown", (event) => {
      if (event.key !== "Escape") return;
      trigger.classList?.remove("is-open");
      hideTooltip(trigger);
      event.stopPropagation();
    });
  });
}

if (document?.addEventListener) {
  document.addEventListener("click", (event) => {
    if (stopEventAfterTooltipTouch(event)) return;
    if (!event.target?.closest?.(".info-tooltip")) closeTooltips();
  });
}

function currentVariant() {
  return variants.find((variant) => variant.body_style === state.bodyStyle && variant.trim_level === state.trimLevel);
}

function currentVariantId() {
  return currentVariant()?.variant_id || "";
}

function normalizeStepKey(stepKey) {
  return vehicleSetupStepKeys.has(stepKey) ? "model" : stepKey;
}

function visibleRuntimeSteps() {
  return runtimeSteps.filter((step) => step.step_key === "model" || !vehicleSetupStepKeys.has(step.step_key));
}

function normalizeVehicleSetupStage(stage) {
  return vehicleSetupStages.includes(stage) ? stage : "model";
}

function setVehicleSetupStage(stage, { shouldRender = true, preserveScroll = true, resetScroll = false } = {}) {
  state.vehicleSetupStage = normalizeVehicleSetupStage(stage);
  if (shouldRender) render(preserveScroll ? { preserveScroll: true } : { resetScroll });
}

function advanceVehicleSetupStage() {
  const stage = normalizeVehicleSetupStage(state.vehicleSetupStage);
  const nextStage = stage === "model" ? "body_style" : stage === "body_style" ? "trim_level" : stage === "trim_level" ? "ready" : "ready";
  setVehicleSetupStage(nextStage);
}

function previousVehicleSetupStage() {
  const stage = normalizeVehicleSetupStage(state.vehicleSetupStage);
  const previousStage = stage === "ready" ? "trim_level" : stage === "trim_level" ? "body_style" : stage === "body_style" ? "model" : "model";
  setVehicleSetupStage(previousStage);
}

function currentStepIndex() {
  const activeStepKey = normalizeStepKey(state.activeStep);
  return visibleRuntimeSteps().findIndex((step) => step.step_key === activeStepKey);
}

function nextStep() {
  const steps = visibleRuntimeSteps();
  const index = currentStepIndex();
  return index >= 0 ? steps[index + 1] : null;
}

function setButtonExpanded(button, expanded) {
  button?.setAttribute?.("aria-expanded", expanded ? "true" : "false");
}

function updateSummaryDrawerControls(isOpen) {
  const summaryLabel = els.openSummaryDrawerButton?.querySelector(".summary-drawer-label");
  if (summaryLabel) summaryLabel.textContent = isOpen ? "Hide Build Summary" : "Build Summary";
  els.openSummaryDrawerButton?.setAttribute("aria-label", isOpen ? "Hide build summary" : "View build summary");
  els.mobileSummaryButton?.setAttribute("aria-label", isOpen ? "Hide build summary" : "View build summary");
}

function setMobileDrawer(drawerName = "") {
  const summaryOpen = drawerName === "summary";
  if (els.appShell) {
    if (drawerName) {
      els.appShell.dataset.mobileDrawer = drawerName;
    } else {
      delete els.appShell.dataset.mobileDrawer;
    }
  }
  if (els.mobileDrawerBackdrop) els.mobileDrawerBackdrop.hidden = !drawerName;
  setButtonExpanded(els.openStepDrawerButton, drawerName === "steps");
  setButtonExpanded(els.openSummaryDrawerButton, summaryOpen);
  setButtonExpanded(els.mobileSummaryButton, summaryOpen);
  updateSummaryDrawerControls(summaryOpen);
}

function closeMobileDrawers() {
  setMobileDrawer("");
}

function handleDrawerWheel(event) {
  if (els.appShell?.dataset?.mobileDrawer !== "summary" || !els.summaryDrawer) return;
  const deltaY = Number(event.deltaY || 0);
  const deltaX = Number(event.deltaX || 0);
  if (!deltaY && !deltaX) return;
  event.preventDefault?.();
  els.summaryDrawer.scrollTop += deltaY;
  els.summaryDrawer.scrollLeft += deltaX;
}

function handleMobileDrawerKeydown(event) {
  if (event.key === "Escape") closeMobileDrawers();
}

function activateStep(stepKey, { closeDrawer = false } = {}) {
  const normalizedStepKey = normalizeStepKey(stepKey);
  if (!normalizedStepKey) return;
  if (vehicleSetupStepKeys.has(stepKey) && stepKey !== "model") {
    state.vehicleSetupStage = stepKey;
  }
  state.activeStep = normalizedStepKey;
  render({ resetScroll: true });
  if (closeDrawer) closeMobileDrawers();
}

function goToNextStep() {
  if (state.activeStep === "model" && normalizeVehicleSetupStage(state.vehicleSetupStage) !== "ready") {
    advanceVehicleSetupStage();
    return;
  }
  const step = nextStep();
  if (!step) return;
  activateStep(step.step_key);
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
  if (
    targetChoice &&
    targetChoice.display_behavior !== "auto_only" &&
    (targetChoice.active !== "True" || targetChoice.status === "unavailable")
  ) return false;
  return true;
}

function scopeMatches(scope, value) {
  const entries = String(scope || "")
    .split("|")
    .map((entry) => entry.trim())
    .filter(Boolean);
  if (!entries.length || entries.includes("*")) return true;
  return entries.includes(value);
}

function generatedDefaultRules() {
  return Array.isArray(data.defaultSelectionRules) ? data.defaultSelectionRules : [];
}

function generatedRuleExceptions() {
  return Array.isArray(data.runtimeRuleExceptions) ? data.runtimeRuleExceptions : [];
}

function exceptionApplies(exception) {
  if (!scopeMatches(exception.body_style_scope, state.bodyStyle)) return false;
  if (!scopeMatches(exception.trim_level_scope, state.trimLevel)) return false;
  if (!scopeMatches(exception.variant_scope, currentVariantId())) return false;
  return true;
}

function selectedOptionForException(optionId) {
  return state.selected.has(optionId);
}

function runtimeExceptionForTarget(targetOptionId) {
  return generatedRuleExceptions().find(
    (exception) =>
      exception.exception_type === "remove_target_when_source_selected" &&
      exception.target_option_id === targetOptionId &&
      exceptionApplies(exception) &&
      selectedOptionForException(exception.source_option_id)
  );
}

function runtimeExceptionAllowsCandidateOverSelectedTarget(candidateOptionId, selectedTargetOptionId) {
  return generatedRuleExceptions().some(
    (exception) =>
      exception.exception_type === "remove_target_when_source_selected" &&
      exception.source_option_id === candidateOptionId &&
      exception.target_option_id === selectedTargetOptionId &&
      exceptionApplies(exception) &&
      state.selected.has(selectedTargetOptionId)
  );
}

function removeRuntimeExceptionTargets(sourceOptionId = "") {
  for (const exception of generatedRuleExceptions()) {
    if (exception.exception_type !== "remove_target_when_source_selected") continue;
    if (!exceptionApplies(exception)) continue;
    if (sourceOptionId && exception.source_option_id !== sourceOptionId) continue;
    if (state.selected.has(exception.source_option_id)) deleteSelectedOption(exception.target_option_id);
  }
}

function ruleGroupAppliesToCurrentVariant(group) {
  if (group.active && group.active !== "True") return false;
  if (!scopeMatches(group.body_style_scope, state.bodyStyle)) return false;
  if (!scopeMatches(group.trim_level_scope, state.trimLevel)) return false;
  if (!scopeMatches(group.variant_scope, currentVariantId())) return false;
  const sourceChoice = choiceForCurrentVariant(group.source_id);
  if (
    sourceChoice &&
    sourceChoice.display_behavior !== "auto_only" &&
    (sourceChoice.active !== "True" || sourceChoice.status === "unavailable")
  ) return false;
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

function selectedSeatResolvedPrice() {
  const seat = selectedSeatChoice();
  return seat ? optionPrice(seat.option_id) : 0;
}

function adjustedInteriorPrice(interior) {
  return Math.max(0, Number(interior.price || 0) - selectedSeatResolvedPrice());
}

function adjustedInteriorDisplayPrice(interior) {
  return adjustedInteriorPrice(interior);
}

function shouldHideChoice(choice) {
  return choice.active !== "True" || choice.status === "unavailable" || choice.display_behavior === "hidden";
}

function optionIsSelectedOrAuto(choice, autoAdded) {
  return state.selected.has(choice.option_id) || autoAdded.has(choice.option_id);
}

function selectedContextIds(extraIds = []) {
  const ids = new Set(state.selected);
  if (state.selectedInterior) ids.add(state.selectedInterior);
  for (const id of extraIds) {
    if (id) ids.add(id);
  }
  for (const id of computeAutoAdded().keys()) ids.add(id);
  return ids;
}

function getOptionLabel(optionId) {
  const option = optionsById.get(optionId);
  if (!option) return optionId;
  return `${option.rpo || option.option_id} ${option.label || ""}`.trim();
}

function getOptionCustomerLabel(optionId) {
  const option = optionsById.get(optionId);
  if (!option) return optionId;
  return String(option.label || option.rpo || option.option_id || "").trim();
}

function getInteriorCustomerLabel(interior) {
  return String(interior?.interior_leaf_label || interior?.interior_name || interior?.interior_code || interior?.interior_id || "").trim();
}

function getEntityLabel(id) {
  if (optionsById.has(id)) return getOptionLabel(id);
  const interior = interiorsById.get(id);
  if (interior) return getInteriorCustomerLabel(interior);
  return id;
}

function removeDuplicatedEntityRpo(reason, entityId) {
  const option = optionsById.get(entityId);
  const rpo = option?.rpo?.trim();
  const label = option?.label?.trim();
  if (!reason || !rpo || !label || !label.toLowerCase().startsWith(`${rpo.toLowerCase()} `)) return reason;
  return reason.split(`${rpo} ${label}`).join(label);
}

function includedWithReason(rule) {
  if (interiorsById.has(rule.source_id)) return `Included with ${getEntityLabel(rule.source_id)}.`;
  const reason = rule.disabled_reason || `Included with ${getEntityLabel(rule.source_id)}.`;
  return removeDuplicatedEntityRpo(reason, rule.source_id);
}

function includedWithSourceLabel(rule) {
  const reason = includedWithReason(rule);
  const match = String(reason || "").match(/^Included with\s+(.+?)\.?$/i);
  return match ? match[1] : getEntityLabel(rule.source_id);
}

function peerUnavailableGroupLabel(optionId) {
  const sectionName = sectionsById.get(optionSectionId(optionId))?.section_name || "related option";
  if (/seat\s*belt/i.test(sectionName)) return "seat belt colors";
  return `${sectionName.toLowerCase()} choices`;
}

function requiresReason(rule) {
  const reason = rule.disabled_reason || `Requires ${getEntityLabel(rule.target_id)}.`;
  return removeDuplicatedEntityRpo(reason, rule.target_id);
}

function selectedExcludesTarget(targetId, selectedIds) {
  for (const sourceId of selectedIds) {
    const rules = ruleTargetsBySource.get(sourceId) || [];
    if (rules.some((rule) => rule.rule_type === "excludes" && rule.target_id === targetId && ruleAppliesToCurrentVariant(rule))) {
      return true;
    }
    if (sourceExcludesTargetViaGroup(sourceId, targetId)) return true;
  }
  return false;
}

function shouldSuppressIncludedDefault(rule) {
  const sectionId = optionSectionId(rule.target_id);
  const section = sectionsById.get(sectionId);
  return section?.choice_mode === "single" && userSelectedInSection(sectionId, rule.target_id);
}

function includedTargetRequirementsMet(targetId, selectedIds) {
  const rules = ruleTargetsBySource.get(targetId) || [];
  return rules.every(
    (rule) =>
      rule.rule_type !== "requires" ||
      !ruleAppliesToCurrentVariant(rule) ||
      selectedIds.has(rule.target_id)
  );
}

function selectedExclusiveGroupPeer(optionId, selectedIds) {
  const group = optionExclusiveGroup(optionId);
  if (!exclusiveGroupAllowsSingleSelection(group)) return false;
  return (group.option_ids || []).some((id) => id !== optionId && selectedIds.has(id));
}

function selectedOrAutoExclusiveGroupPeer(optionId, selectedIds, autoAdded = computeAutoAdded()) {
  const group = optionExclusiveGroup(optionId);
  if (!exclusiveGroupAllowsSingleSelection(group)) return false;
  return (group.option_ids || []).some((id) => id !== optionId && (selectedIds.has(id) || autoAdded.has(id)));
}

function userSelectedExclusiveGroupPeer(optionId, selectedIds) {
  const group = optionExclusiveGroup(optionId);
  if (!exclusiveGroupAllowsSingleSelection(group)) return false;
  return (group.option_ids || []).some((id) => id !== optionId && selectedIds.has(id) && state.userSelected.has(id));
}

function includedRuleLocksExclusivePeer(rule) {
  const sourceGroup = optionExclusiveGroup(rule.source_id);
  const targetGroup = optionExclusiveGroup(rule.target_id);
  if (targetGroup?.selection_mode !== "single_within_group") return false;
  if (exclusiveGroupAllowsSingleSelection(sourceGroup)) return true;
  return Boolean(data.interiors?.some((interior) => interior.interior_id === rule.source_id));
}

function includedRuleAllowedReplacementPeers(rule) {
  const groups = ruleGroupsBySource.get(rule.source_id) || [];
  const group = groups.find(
    (candidate) =>
      candidate.group_type === "requires_any" &&
      ruleGroupAppliesToCurrentVariant(candidate) &&
      (candidate.target_ids || []).includes(rule.target_id)
  );
  return group ? new Set(group.target_ids || []) : null;
}

function includedRuleLocksAgainstPeer(rule, peerId) {
  const allowedReplacementPeers = includedRuleAllowedReplacementPeers(rule);
  if (allowedReplacementPeers) return !allowedReplacementPeers.has(peerId);
  return includedRuleLocksExclusivePeer(rule);
}

function includedRuleSuppressesUserPeer(rule, selectedIds) {
  const allowedReplacementPeers = includedRuleAllowedReplacementPeers(rule);
  if (!allowedReplacementPeers) return includedRuleLocksExclusivePeer(rule);
  return !(rule.target_id && [...allowedReplacementPeers].some((peerId) => peerId !== rule.target_id && selectedIds.has(peerId) && state.userSelected.has(peerId)));
}

function includedExclusiveGroupPeerReason(optionId, selectedIds = selectedContextIds()) {
  const group = optionExclusiveGroup(optionId);
  if (!exclusiveGroupAllowsSingleSelection(group) || group.selection_mode !== "single_within_group") return "";
  for (const peerId of group.option_ids || []) {
    if (peerId === optionId || !selectedIds.has(peerId)) continue;
    const rules = rulesByTarget.get(peerId) || [];
    const includeRule = rules.find(
      (rule) =>
        rule.rule_type === "includes" &&
        ruleAppliesToCurrentVariant(rule) &&
        selectedIds.has(rule.source_id) &&
        includedRuleLocksAgainstPeer(rule, optionId)
    );
    if (includeRule) {
      return `${getOptionCustomerLabel(peerId)} is included with ${includedWithSourceLabel(includeRule)}, so other ${peerUnavailableGroupLabel(peerId)} are unavailable.`;
    }
  }
  return "";
}

function sameExclusiveGroupPeer(optionId, peerId) {
  const group = optionExclusiveGroup(optionId);
  if (!exclusiveGroupAllowsSingleSelection(group)) return false;
  return (group.option_ids || []).includes(peerId);
}

function requiresAnyReason(choice, selectedIds) {
  const groups = ruleGroupsBySource.get(choice.option_id) || [];
  if (!groups.some((group) => group.group_type === "requires_any" && ruleGroupAppliesToCurrentVariant(group))) return "";
  const candidateSelectedIds = new Set(selectedIds);
  if (!candidateSelectedIds.has(choice.option_id)) {
    candidateSelectedIds.add(choice.option_id);
    for (const id of computeAutoAdded([choice.option_id]).keys()) candidateSelectedIds.add(id);
  }
  for (const group of groups) {
    if (group.group_type !== "requires_any" || !ruleGroupAppliesToCurrentVariant(group)) continue;
    if ((group.target_ids || []).some((targetId) => candidateSelectedIds.has(targetId))) continue;
    return group.disabled_reason || `Requires one of ${(group.target_ids || []).map(getEntityLabel).join(", ")}.`;
  }
  return "";
}

function sourceExcludesTargetViaGroup(sourceId, targetId) {
  const groups = ruleGroupsBySource.get(sourceId) || [];
  return groups.some(
    (group) =>
      group.group_type === "excludes_any" &&
      ruleGroupAppliesToCurrentVariant(group) &&
      (group.target_ids || []).includes(targetId)
  );
}

function excludesAnyReason(choice, selectedIds) {
  for (const sourceId of selectedIds) {
    if (!sourceExcludesTargetViaGroup(sourceId, choice.option_id)) continue;
    const group = (ruleGroupsBySource.get(sourceId) || []).find(
      (candidate) =>
        candidate.group_type === "excludes_any" &&
        ruleGroupAppliesToCurrentVariant(candidate) &&
        (candidate.target_ids || []).includes(choice.option_id)
    );
    return group?.disabled_reason || `Blocked by ${getEntityLabel(sourceId)}.`;
  }
  return "";
}

function computeAutoAdded(extraIds = []) {
  const autoAdded = new Map();
  const autoAddedSources = new Map();
  const selectedIds = new Set(state.selected);
  for (const id of extraIds) {
    if (id) selectedIds.add(id);
  }
  if (state.selectedInterior) selectedIds.add(state.selectedInterior);

  let changed = true;
  while (changed) {
    changed = false;
    for (const sourceId of [...selectedIds]) {
      const rules = ruleTargetsBySource.get(sourceId) || [];
      for (const rule of rules) {
        if (
          rule.rule_type === "includes" &&
          ruleAppliesToCurrentVariant(rule) &&
          !selectedExcludesTarget(rule.target_id, selectedIds) &&
          !shouldSuppressIncludedDefault(rule) &&
          includedTargetRequirementsMet(rule.target_id, selectedIds) &&
          (!userSelectedExclusiveGroupPeer(rule.target_id, selectedIds) || includedRuleSuppressesUserPeer(rule, selectedIds))
        ) {
          const targetGroup = optionExclusiveGroup(rule.target_id);
          let blockedBySelectedSourcePeer = false;
          if (exclusiveGroupAllowsSingleSelection(targetGroup)) {
            for (const peerId of targetGroup.option_ids || []) {
              if (peerId === rule.target_id || !autoAdded.has(peerId)) continue;
              const existingSourceId = autoAddedSources.get(peerId);
              const existingSourceIsSelected = state.selected.has(existingSourceId);
              const currentSourceIsSelected = state.selected.has(rule.source_id);
              if (existingSourceIsSelected && !currentSourceIsSelected) {
                blockedBySelectedSourcePeer = true;
                break;
              }
              if (currentSourceIsSelected && !existingSourceIsSelected) {
                autoAdded.delete(peerId);
                autoAddedSources.delete(peerId);
                selectedIds.delete(peerId);
              }
            }
          }
          if (blockedBySelectedSourcePeer) continue;
          autoAdded.set(rule.target_id, includedWithReason(rule));
          autoAddedSources.set(rule.target_id, rule.source_id);
          if (!selectedIds.has(rule.target_id)) {
            selectedIds.add(rule.target_id);
            changed = true;
          }
        }
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

function disableReasonForChoice(choice, { includeSelectedRequirements = true } = {}) {
  if (choice.active !== "True") return "Inactive in the source workbook.";
  if (choice.status === "unavailable") return "Not available for this body and trim.";

  const exception = runtimeExceptionForTarget(choice.option_id);
  if (exception) return exception.disabled_reason || `Blocked by ${getEntityLabel(exception.source_option_id)}.`;

  const selectedIds = selectedContextIds();
  const groupedReason = includeSelectedRequirements && !state.selected.has(choice.option_id) ? requiresAnyReason(choice, selectedIds) : "";
  if (groupedReason) return groupedReason;
  const groupedExclusionReason = excludesAnyReason(choice, selectedIds);
  if (groupedExclusionReason) return groupedExclusionReason;
  const includedPeerReason = includedExclusiveGroupPeerReason(choice.option_id, selectedIds);
  if (includedPeerReason) return includedPeerReason;
  const targetRules = rulesByTarget.get(choice.option_id) || [];
  for (const rule of targetRules) {
    if (rule.rule_type === "excludes" && selectedIds.has(rule.source_id) && ruleAppliesToCurrentVariant(rule)) {
      if (sameExclusiveGroupPeer(choice.option_id, rule.source_id)) continue;
      if (runtimeExceptionAllowsCandidateOverSelectedTarget(choice.option_id, rule.source_id)) continue;
      if (rule.runtime_action === "replace") return rule.disabled_reason || `${getEntityLabel(rule.source_id)} removes ${getEntityLabel(rule.target_id)}.`;
      return rule.disabled_reason || `Blocked by ${getEntityLabel(rule.source_id)}.`;
    }
  }
  for (const rule of targetRules) {
    if (
      rule.rule_type === "includes" &&
      ruleAppliesToCurrentVariant(rule) &&
      choice.selectable !== "True" &&
      choice.status !== "standard"
    ) return includedWithReason(rule);
  }

  const sourceRules = ruleTargetsBySource.get(choice.option_id) || [];
  for (const rule of sourceRules) {
    if (!ruleAppliesToCurrentVariant(rule)) continue;
    if (rule.rule_type === "requires" && !selectedIds.has(rule.target_id)) {
      return requiresReason(rule);
    }
    if (rule.rule_type === "excludes" && selectedIds.has(rule.target_id)) {
      if (rule.runtime_action === "replace") continue;
      return `Conflicts with ${getEntityLabel(rule.target_id)}.`;
    }
  }

  if (choice.selectable !== "True") return "Display-only source row.";

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

function matchingPriceRuleApplies(rule) {
  return (
    scopeMatches(rule.body_style_scope, state.bodyStyle) &&
    scopeMatches(rule.trim_level_scope, state.trimLevel) &&
    scopeMatches(rule.variant_scope, currentVariantId())
  );
}

function packageComponentPriceRules(packageOptionId) {
  const rules = (priceRulesByTarget.get(packageOptionId) || []).filter((rule) => {
    if (rule.price_rule_type !== "override" || !matchingPriceRuleApplies(rule)) return false;
    const conditionGroup = optionExclusiveGroup(rule.condition_option_id);
    return exclusiveGroupAllowsSingleSelection(conditionGroup) && Number(rule.price_value || 0) > 0;
  });
  const distinctPrices = new Set(rules.map((rule) => Number(rule.price_value || 0)));
  return distinctPrices.size > 1 ? rules : [];
}

function hasPackageComponentPricing(packageOptionId) {
  return packageComponentPriceRules(packageOptionId).length > 1;
}

function packageComponentBasePrice(packageOptionId) {
  const prices = packageComponentPriceRules(packageOptionId).map((rule) => Number(rule.price_value || 0));
  return prices.length ? Math.min(...prices) : null;
}

function packageComponentDelta(optionId, selectedIds) {
  for (const [packageOptionId, rules] of priceRulesByTarget.entries()) {
    if (!selectedIds.has(packageOptionId)) continue;
    const componentRules = packageComponentPriceRules(packageOptionId);
    if (!componentRules.length) continue;
    const rule = componentRules.find((candidate) => candidate.condition_option_id === optionId);
    if (!rule) continue;
    const basePrice = packageComponentBasePrice(packageOptionId);
    if (basePrice === null) continue;
    return Math.max(0, Number(rule.price_value || 0) - basePrice);
  }
  return null;
}

function optionPrice(optionId, candidateIds = []) {
  const selectedIds = selectedContextIds(candidateIds);
  const componentDelta = packageComponentDelta(optionId, selectedIds);
  if (componentDelta !== null) return componentDelta;
  const packageBasePrice = packageComponentBasePrice(optionId);
  if (packageBasePrice !== null && selectedIds.has(optionId)) return packageBasePrice;
  const priceRules = priceRulesByTarget.get(optionId) || [];
  for (const rule of priceRules) {
    if (!matchingPriceRuleApplies(rule)) continue;
    if (rule.price_rule_type === "override" && selectedIds.has(rule.condition_option_id)) {
      return Number(rule.price_value || 0);
    }
  }
  return Number(optionsById.get(optionId)?.base_price || 0);
}

function choiceDisplayPrice(choice) {
  return optionPrice(choice.option_id, [choice.option_id]);
}

function missingGeneratedOrderSummaryMetadata(field) {
  const modelKey = activeModel?.key || activeModelKey || data?.dataset?.model_key || data?.dataset?.model || "unknown";
  throw new Error(
    `Missing generated orderSummary.${field} metadata for active model ${modelKey}. Regenerate the model artifact and registry before loading the runtime.`
  );
}

function orderSummarySections() {
  const generated = data.orderSummary?.sections;
  if (Array.isArray(generated) && generated.length) return generated;
  return missingGeneratedOrderSummaryMetadata("sections");
}

function orderSummaryStepMap() {
  const generated = data.orderSummary?.stepMap;
  if (generated && typeof generated === "object" && Object.keys(generated).length) return generated;
  return missingGeneratedOrderSummaryMetadata("stepMap");
}

function orderSummarySectionOrder() {
  return new Map(orderSummarySections().map((section, index) => [section.section_key, Number(section.display_order || index)]));
}

function sectionKeyForStep(stepKey) {
  return orderSummaryStepMap()[stepKey] || stepKey || "vehicle";
}

function autoAddedOptionUsesRequiredSummaryBucket(option) {
  return option?.auto_added_summary_required === true;
}

function sectionKeyForOption(option, type = "") {
  if (type === "auto_added" && autoAddedOptionUsesRequiredSummaryBucket(option)) return "auto_added_required";
  return sectionKeyForStep(option?.step_key || "");
}

function sectionLabelForKey(sectionKey) {
  const section = orderSummarySections().find((row) => row.section_key === sectionKey);
  return section?.section_label || sectionKey;
}

function lineItemFromOption(option, type, price, extra = {}) {
  const sectionKey = sectionKeyForOption(option, type);
  return {
    id: option.option_id,
    rpo: option.rpo || "",
    label: option.label || "",
    description: option.description || "",
    price,
    type,
    section_key: sectionKey,
    section_label: sectionLabelForKey(sectionKey),
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
    step_key: "base_interior",
  };
}

function interiorComponents(interior) {
  return Array.isArray(interior?.interior_components) ? interior.interior_components : [];
}

function selectedInteriorReplacesSeat(interior) {
  return interiorComponents(interior).some((component) => ["seat", "r6x"].includes(component.component_type));
}

function interiorComponentPrice(component) {
  return Number(component.price || 0);
}

function lineItemFromInteriorComponent(interior, component, autoAdded) {
  return {
    id: `${interior.interior_id}__${component.rpo}`,
    rpo: component.rpo || "",
    label: component.label || "",
    description: interior.interior_name || "",
    price: interiorComponentPrice(component, autoAdded),
    type: "interior_component",
    section_key: "seats_interior",
    section_label: sectionLabelForKey("seats_interior"),
    step_key: "base_interior",
    component_type: component.component_type || "",
  };
}

function lineItemsFromInterior(interior, autoAdded) {
  const components = interiorComponents(interior);
  if (!components.length) return [lineItemFromInterior(interior)];

  const replacedSeatPrice = selectedInteriorReplacesSeat(interior) ? selectedSeatResolvedPrice() : 0;
  const componentBaseTotal = components.reduce((sum, component) => sum + Number(component.price || 0), 0);
  const identityPrice = Math.max(0, replacedSeatPrice + adjustedInteriorPrice(interior) - componentBaseTotal);
  return [
    { ...lineItemFromInterior(interior), price: identityPrice },
    ...components.map((component) => lineItemFromInteriorComponent(interior, component, autoAdded)),
  ];
}

function lineItems() {
  const autoAdded = computeAutoAdded();
  const rows = [];
  const interior = state.selectedInterior ? interiorsById.get(state.selectedInterior) : null;
  const skipSelectedSeat = interior ? selectedInteriorReplacesSeat(interior) : false;
  for (const id of state.selected) {
    if (autoAdded.has(id)) continue;
    const option = optionsById.get(id);
    if (option) {
      if (skipSelectedSeat && option.step_key === "seat") continue;
      rows.push(lineItemFromOption(option, "selected", optionPrice(id)));
    }
  }
  if (interior) {
    rows.push(...lineItemsFromInterior(interior, autoAdded));
  }
  for (const [id, reason] of autoAdded) {
    const option = optionsById.get(id);
    if (option) {
      rows.push(lineItemFromOption(option, "auto_added", optionPrice(id), { reason }));
    }
  }
  return rows;
}

function missingRequirementDetails() {
  const rows = activeChoiceRows();
  const sections = new Map();
  const selectedIds = selectedContextIds();
  const autoAdded = computeAutoAdded();
  for (const choice of rows) {
    const section = sectionsById.get(choice.section_id);
    if (!section || !(section.selection_mode === "single_select_req" || truthyValue(section.is_required))) continue;
    if (choice.step_key === "base_interior") continue;
    if (shouldHideChoice(choice)) continue;
    if (!sections.has(choice.section_id)) sections.set(choice.section_id, { section, choices: [] });
    sections.get(choice.section_id).choices.push(choice);
  }
  const missing = [];
  const missingSectionIds = new Set();
  for (const [sectionId, { section, choices }] of sections) {
    const hasSelection = [...selectedIds].some((id) => optionSectionId(id) === sectionId);
    if (!hasSelection) {
      const step = runtimeSteps.find((item) => item.step_key === choices[0]?.step_key);
      missingSectionIds.add(sectionId);
      missing.push({
        label: section.section_name,
        hasOptions: choices.some((choice) => choice.selectable === "True"),
        stepKey: choices[0]?.step_key || "",
        detail: `Choose one ${step?.step_label ? `in ${step.step_label}` : "required option"} from ${section.section_name}.`,
      });
    }
  }
  for (const group of requiredExclusiveGroups()) {
    const choices = activeChoicesForExclusiveGroup(group);
    if (!choices.length || selectedOrAutoInExclusiveGroup(group, autoAdded, selectedIds)) continue;
    const section = sectionsById.get(choices[0].section_id);
    if (section && missingSectionIds.has(section.section_id)) continue;
    const step = runtimeSteps.find((item) => item.step_key === choices[0]?.step_key);
    missing.push({
      label: section?.section_name || group.group_id,
      hasOptions: choices.some((choice) => choice.selectable === "True"),
      stepKey: choices[0]?.step_key || "",
      detail: `Choose one ${step?.step_label ? `in ${step.step_label}` : "required option"} from ${section?.section_name || group.group_id}.`,
    });
  }
  for (const sourceId of selectedIds) {
    for (const group of ruleGroupsBySource.get(sourceId) || []) {
      if (group.group_type !== "requires_any" || !ruleGroupAppliesToCurrentVariant(group)) continue;
      if ((group.target_ids || []).some((targetId) => selectedIds.has(targetId) || autoAdded.has(targetId))) continue;
      const choices = (group.target_ids || []).map((targetId) => optionsById.get(targetId)).filter(Boolean);
      const section = sectionsById.get(choices[0]?.section_id || "");
      const step = runtimeSteps.find((item) => item.step_key === choices[0]?.step_key);
      missing.push({
        label: section?.section_name || getEntityLabel(sourceId),
        hasOptions: choices.some((choice) => choice.selectable === "True" && !disableReasonForChoice(choice)),
        stepKey: choices[0]?.step_key || "",
        detail: group.disabled_reason || `Choose one ${step?.step_label ? `in ${step.step_label}` : "required option"}: ${(group.target_ids || []).map(getEntityLabel).join(", ")}.`,
      });
    }
  }
  if (!state.selectedInterior) {
    missing.push({
      label: "Interior Color",
      hasOptions: validInteriorsForSelectedSeat().length > 0,
      stepKey: "base_interior",
      detail: "Choose an interior color compatible with the selected seat and trim.",
    });
  }
  return missing;
}

function missingRequired() {
  return missingRequirementDetails().map((item) => item.label);
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
  addWorkbookDefaultChoices({ restoreSingleRequiredOnly: false });
  addGeneratedDefaultChoices(computeAutoAdded());
}

function addWorkbookDefaultChoices({ restoreSingleRequiredOnly = true } = {}) {
  const autoAdded = computeAutoAdded();
  const rows = activeChoiceRows()
    .filter(
      (choice) =>
        choice.display_behavior === "default_selected" &&
        choice.active === "True" &&
        choice.status !== "unavailable" &&
        choice.selectable === "True"
    )
    .sort((a, b) => Number(a.display_order || 0) - Number(b.display_order || 0));
  for (const choice of rows) {
    const section = sectionsById.get(choice.section_id);
    if (!section) continue;
    const group = optionExclusiveGroup(choice.option_id);
    const canRestoreDefaultGroup = group && exclusiveGroupAllowsSingleSelection(group) && !selectedOrAutoInExclusiveGroup(group, autoAdded);
    if (restoreSingleRequiredOnly && section.selection_mode !== "single_select_req" && !canRestoreDefaultGroup) continue;
    if (section.choice_mode === "single" && selectedOrAutoInSection(choice.section_id)) continue;
    if (selectedOrAutoExclusiveGroupPeer(choice.option_id, state.selected, autoAdded)) continue;
    if (disableReasonForChoice(choice)) continue;
    state.selected.add(choice.option_id);
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

function exclusiveGroupAllowsSingleSelection(group) {
  return ["single_within_group", "required_single_within_group"].includes(group?.selection_mode);
}

function exclusiveGroupRequiresSelection(group) {
  return group?.selection_mode === "required_single_within_group";
}

function activeChoicesForExclusiveGroup(group) {
  if (!group) return [];
  return (group.option_ids || [])
    .map((optionId) => choiceForCurrentVariant(optionId))
    .filter((choice) => choice && !shouldHideChoice(choice));
}

function selectedOrAutoInExclusiveGroup(group, autoAdded = computeAutoAdded(), ids = state.selected) {
  if (!group) return false;
  return (group.option_ids || []).some((id) => ids.has(id) || autoAdded.has(id));
}

function selectedOptionIdsInExclusiveGroup(group, ids = state.selected) {
  if (!group) return [];
  return (group.option_ids || []).filter((id) => ids.has(id));
}

function requiredExclusiveGroups() {
  return (data.exclusiveGroups || []).filter((group) => group.active === "True" && exclusiveGroupRequiresSelection(group));
}

function exclusiveGroupVisualLabel(group) {
  if (exclusiveGroupRequiresSelection(group)) return "Required choice";
  if (exclusiveGroupAllowsSingleSelection(group)) return "Choose one";
  return "Related options";
}

function exclusiveGroupHeading(group) {
  if (exclusiveGroupRequiresSelection(group)) return "Choose one required option";
  if (exclusiveGroupAllowsSingleSelection(group)) return "Choose one of these related options";
  return "Related options";
}

function includeRulesForChoice(choice) {
  return (ruleTargetsBySource.get(choice.option_id) || []).filter(
    (rule) => rule.rule_type === "includes" && ruleAppliesToCurrentVariant(rule) && (!rule.active || rule.active === "True")
  );
}

function relationshipBadgesForChoice(choice, { disabled = false } = {}) {
  const badges = [];
  const includeRules = includeRulesForChoice(choice);
  if (includeRules.length) {
    badges.push({
      type: "includes",
      className: `includes${disabled ? " disabled" : ""}`,
      label: `Includes ${includeRules.length} item${includeRules.length === 1 ? "" : "s"}`,
    });
  }
  return badges;
}

function renderRelationshipBadge(badge) {
  if (badge.type === "includes") {
    return `
      <span class="choice-relationship-badge ${badge.className}">
        <span>${escapeHtml(badge.label)}</span>
      </span>
    `;
  }
  return `
    <span class="choice-relationship-badge ${badge.className}" ${badge.dataAttribute || ""}>
      <span>${escapeHtml(badge.label)}</span>
    </span>
  `;
}

function renderChoiceRelationshipBadges(choice, { disabled = false } = {}) {
  const badges = relationshipBadgesForChoice(choice, { disabled });
  if (!badges.length) return "";
  return `
    <span class="choice-relationship-badges">
      ${badges.map(renderRelationshipBadge).join("")}
    </span>
  `;
}

function removeOtherExclusiveGroupOptions(optionId) {
  const group = optionExclusiveGroup(optionId);
  if (!exclusiveGroupAllowsSingleSelection(group)) return;
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

function addDefaultOption(optionId) {
  const choice = choiceForCurrentVariant(optionId) || optionsById.get(optionId);
  if (choice && !disableReasonForChoice(choice)) state.selected.add(choice.option_id);
}

function removeReplaceRuleTargets(sourceId) {
  const rules = ruleTargetsBySource.get(sourceId) || [];
  for (const rule of rules) {
    if (rule.runtime_action === "replace" && ruleAppliesToCurrentVariant(rule)) {
      // Toast only for explicit customer selections: state.userSelected holds
      // only user picks (defaults/auto-adds live in state.selected alone), and
      // the check must run before deleteSelectedOption clears the flag.
      const wasExplicitlySelected = state.userSelected.has(rule.target_id);
      deleteSelectedOption(rule.target_id);
      if (wasExplicitlySelected) {
        showEvictionToast(rule.disabled_reason || `${getEntityLabel(rule.source_id)} removes ${getEntityLabel(rule.target_id)}.`);
      }
    }
  }
}

const TOAST_TIMEOUT_MS = 8000;

function showEvictionToast(message) {
  if (!els.toastRegion || !message) return;
  const toast = document.createElement("div");
  toast.className = "toast";
  toast.setAttribute?.("role", "status");
  const text = document.createElement("span");
  text.className = "toast-message";
  text.textContent = message;
  const dismiss = document.createElement("button");
  dismiss.className = "toast-dismiss";
  dismiss.type = "button";
  dismiss.setAttribute?.("aria-label", "Dismiss notification");
  dismiss.textContent = "\u00d7";
  const remove = () => {
    window.clearTimeout?.(timer);
    toast.remove?.();
  };
  const timer = window.setTimeout?.(remove, TOAST_TIMEOUT_MS);
  dismiss.addEventListener?.("click", remove);
  toast.append?.(text, dismiss);
  els.toastRegion.append?.(toast);
}

function selectedOrAutoInSection(sectionId, autoAdded = computeAutoAdded()) {
  return (
    selectedOptionIdsInSection(sectionId).length > 0 ||
    [...autoAdded.keys()].some((id) => optionSectionId(id) === sectionId)
  );
}

function addGeneratedDefaultChoices(autoAdded = computeAutoAdded()) {
  for (const rule of generatedDefaultRules()) {
    if (!scopeMatches(rule.body_style_scope, state.bodyStyle)) continue;
    if (!scopeMatches(rule.trim_level_scope, state.trimLevel)) continue;
    if (!scopeMatches(rule.variant_scope, currentVariantId())) continue;

    const targetChoice = choiceForCurrentVariant(rule.target_option_id) || optionsById.get(rule.target_option_id);
    const targetSectionId = targetChoice?.section_id || optionSectionId(rule.target_option_id);
    const selectedIds = new Set(state.selected);
    const conditionSelected = selectedIds.has(rule.condition_id) || autoAdded.has(rule.condition_id);

    if (rule.condition_type === "unless_selected_rpo" && selectedOptionByRpo(rule.condition_id)) continue;
    if (rule.condition_type === "unless_selected_section" && selectedOrAutoInSection(rule.condition_id, autoAdded)) continue;
    if (rule.condition_type === "when_selected_unless_selected_section") {
      if (!conditionSelected) continue;
      if (targetSectionId && userSelectedInSection(targetSectionId, rule.target_option_id)) continue;
    }
    if (selectedOrAutoExclusiveGroupPeer(rule.target_option_id, selectedIds, autoAdded)) continue;

    addDefaultOption(rule.target_option_id);
  }
}

function hasIncludedFallbackForRequiredChoice(choice) {
  const section = sectionsById.get(choice.section_id);
  if (!section || section.selection_mode !== "single_select_req") return false;
  const selectedIds = new Set(state.selected);
  selectedIds.delete(choice.option_id);
  if (state.selectedInterior) selectedIds.add(state.selectedInterior);

  for (const sourceId of selectedIds) {
    const rules = ruleTargetsBySource.get(sourceId) || [];
    for (const rule of rules) {
      if (rule.rule_type !== "includes" || !ruleAppliesToCurrentVariant(rule)) continue;
      if (rule.target_id === choice.option_id || optionSectionId(rule.target_id) !== choice.section_id) continue;
      const targetChoice = choiceForCurrentVariant(rule.target_id);
      if (!targetChoice || shouldHideChoice(targetChoice)) continue;
      if (!includedTargetRequirementsMet(rule.target_id, selectedIds)) continue;
      if (selectedExcludesTarget(rule.target_id, selectedIds)) continue;
      if (userSelectedExclusiveGroupPeer(rule.target_id, selectedIds)) continue;
      return true;
    }
  }
  return false;
}

function generatedDefaultRuleCanSelect(rule, autoAdded = computeAutoAdded()) {
  if (!scopeMatches(rule.body_style_scope, state.bodyStyle)) return false;
  if (!scopeMatches(rule.trim_level_scope, state.trimLevel)) return false;
  if (!scopeMatches(rule.variant_scope, currentVariantId())) return false;

  const targetChoice = choiceForCurrentVariant(rule.target_option_id) || optionsById.get(rule.target_option_id);
  const targetSectionId = targetChoice?.section_id || optionSectionId(rule.target_option_id);
  const conditionSelected = state.selected.has(rule.condition_id) || autoAdded.has(rule.condition_id);

  if (rule.condition_type === "unless_selected_rpo" && selectedOptionByRpo(rule.condition_id)) return false;
  if (rule.condition_type === "unless_selected_section" && selectedOrAutoInSection(rule.condition_id, autoAdded)) return false;
  if (rule.condition_type === "when_selected_unless_selected_section") {
    if (!conditionSelected) return false;
    if (targetSectionId && userSelectedInSection(targetSectionId, rule.target_option_id)) return false;
  }
  if (selectedOrAutoExclusiveGroupPeer(rule.target_option_id, new Set(state.selected), autoAdded)) return false;
  return true;
}

function hasWorkbookDefaultFallbackForRequiredExclusiveChoice(choice) {
  const group = optionExclusiveGroup(choice.option_id);
  if (!exclusiveGroupRequiresSelection(group)) return false;
  const fallbackChoices = activeChoicesForExclusiveGroup(group).filter(
    (candidate) => candidate.option_id !== choice.option_id && candidate.selectable === "True"
  );
  if (!fallbackChoices.length) return false;

  const wasSelected = state.selected.has(choice.option_id);
  const wasUserSelected = state.userSelected.has(choice.option_id);
  deleteSelectedOption(choice.option_id);
  try {
    const autoAdded = computeAutoAdded();
    if (selectedOrAutoInExclusiveGroup(group, autoAdded)) return false;
    return fallbackChoices.some(
      (candidate) =>
        generatedDefaultRules().some(
          (rule) => rule.target_option_id === candidate.option_id && generatedDefaultRuleCanSelect(rule, autoAdded)
        ) && !disableReasonForChoice(candidate)
    );
  } finally {
    if (wasSelected) state.selected.add(choice.option_id);
    if (wasUserSelected) state.userSelected.add(choice.option_id);
  }
}

function wouldClearRequiredExclusiveGroup(choice, autoAdded = computeAutoAdded()) {
  const group = optionExclusiveGroup(choice.option_id);
  if (!exclusiveGroupRequiresSelection(group)) return false;
  if (hasIncludedFallbackForRequiredChoice(choice)) return false;
  if (hasWorkbookDefaultFallbackForRequiredExclusiveChoice(choice)) return false;
  const selectedIds = new Set(state.selected);
  selectedIds.delete(choice.option_id);
  return !selectedOrAutoInExclusiveGroup(group, autoAdded, selectedIds);
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

function removeLockedIncludedExclusiveGroupPeers() {
  const selectedIds = selectedContextIds();
  let removed = false;
  for (const sourceId of [...selectedIds]) {
    const rules = ruleTargetsBySource.get(sourceId) || [];
    for (const rule of rules) {
      if (rule.rule_type !== "includes" || !ruleAppliesToCurrentVariant(rule)) continue;
      const targetGroup = optionExclusiveGroup(rule.target_id);
      if (!exclusiveGroupAllowsSingleSelection(targetGroup)) continue;
      for (const peerId of targetGroup.option_ids || []) {
        if (peerId === rule.target_id || !state.selected.has(peerId) || !includedRuleLocksAgainstPeer(rule, peerId)) continue;
        deleteSelectedOption(peerId);
        removed = true;
      }
    }
  }
  return removed;
}

function reconcileSelections() {
  for (const id of [...state.selected]) {
    removeRuntimeExceptionTargets(id);
  }
  for (const id of [...state.selected]) {
    removeReplaceRuleTargets(id);
  }
  for (const id of [...state.selected]) {
    const choice = choiceForCurrentVariant(id);
    if (!choice || shouldHideChoice(choice) || disableReasonForChoice(choice, { includeSelectedRequirements: false })) deleteSelectedOption(id);
  }
  reconcileInteriorSelection();
  const autoAdded = computeAutoAdded();
  for (const id of [...state.selected]) {
    const choice = choiceForCurrentVariant(id);
    if (!choice || shouldHideChoice(choice) || disableReasonForChoice(choice, { includeSelectedRequirements: false })) deleteSelectedOption(id);
  }
  removeAutoDefaultDuplicates(autoAdded);
  if (removeLockedIncludedExclusiveGroupPeers()) {
    removeAutoDefaultDuplicates(computeAutoAdded());
  }
  const refreshedAutoAdded = computeAutoAdded();
  addWorkbookDefaultChoices();
  addGeneratedDefaultChoices(refreshedAutoAdded);
  dedupeSelectedRpos();
}

function setBodyAndTrim(bodyStyle, trimLevel, { vehicleSetupStage } = {}) {
  resetDealerSubmissionState();
  state.bodyStyle = bodyStyle;
  state.trimLevel = trimLevel;
  if (vehicleSetupStage) state.vehicleSetupStage = normalizeVehicleSetupStage(vehicleSetupStage);
  resetDefaults();
  reconcileSelections();
  render();
}

function handleContextChoice(choice) {
  const currentSetupStage = normalizeVehicleSetupStage(state.vehicleSetupStage);
  if (choice.context_type === "body_style") {
    const nextTrim = variants.find((variant) => variant.body_style === choice.value)?.trim_level;
    setBodyAndTrim(choice.value, nextTrim, { vehicleSetupStage: currentSetupStage === "body_style" ? "body_style" : "trim_level" });
    return;
  }
  if (choice.context_type === "trim_level") {
    setBodyAndTrim(choice.body_style, choice.trim_level, { vehicleSetupStage: currentSetupStage === "trim_level" ? "trim_level" : "ready" });
  }
}

function handleChoice(choice) {
  const autoAdded = computeAutoAdded();
  if (autoAdded.has(choice.option_id)) return;
  const reason = disableReasonForChoice(choice);
  if (reason) return;
  resetDealerSubmissionState();
  const section = sectionsById.get(choice.section_id);
  if (section?.choice_mode === "single") {
    if (
      state.selected.has(choice.option_id) &&
      !wouldClearRequiredExclusiveGroup(choice, autoAdded) &&
      (section.selection_mode === "single_select_opt" || hasIncludedFallbackForRequiredChoice(choice))
    ) {
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
    if (wouldClearRequiredExclusiveGroup(choice, autoAdded)) return;
    deleteSelectedOption(choice.option_id);
  } else {
    removeOtherExclusiveGroupOptions(choice.option_id);
    state.selected.add(choice.option_id);
    state.userSelected.add(choice.option_id);
  }
  removeReplaceRuleTargets(choice.option_id);
  removeRuntimeExceptionTargets(choice.option_id);
  reconcileSelections();
  render({ preserveScroll: true });
}

function handleInterior(interior) {
  const reason = disableReasonForInterior(interior);
  if (reason) return;
  resetDealerSubmissionState();
  state.selectedInterior = state.selectedInterior === interior.interior_id ? "" : interior.interior_id;
  reconcileSelections();
  render({ preserveScroll: true });
}

function currentStepSummary() {
  const steps = visibleRuntimeSteps();
  const index = Math.max(0, currentStepIndex());
  return {
    index,
    total: steps.length,
    step: steps[index],
    previous: steps[index - 1],
    next: steps[index + 1],
  };
}

function goToPreviousStep() {
  if (state.activeStep === "model" && normalizeVehicleSetupStage(state.vehicleSetupStage) !== "model") {
    previousVehicleSetupStage();
    return;
  }
  const { previous } = currentStepSummary();
  if (!previous) return;
  activateStep(previous.step_key);
}

function renderMobileProgress() {
  const { index, total, step, previous, next } = currentStepSummary();
  const setupStage = state.activeStep === "model" ? normalizeVehicleSetupStage(state.vehicleSetupStage) : "";
  const setupPreviousLabel = setupStage === "body_style" ? "Model" : setupStage === "trim_level" ? "Body Style" : setupStage === "ready" ? "Trim Level" : "";
  const setupNextLabel = setupStage === "model" ? "Body Style" : setupStage === "body_style" ? "Trim Level" : setupStage === "trim_level" ? "Review setup" : "";
  const hasPrevious = Boolean(previous || setupPreviousLabel);
  const hasNext = Boolean(next || setupNextLabel);
  const showMobileNext = hasNext;
  if (els.mobileStepCount) els.mobileStepCount.textContent = `Step ${index + 1} of ${total || 1}`;
  if (els.mobileStepName) els.mobileStepName.textContent = step?.step_label || "Step";
  if (els.mobileProgress) els.mobileProgress.dataset.hasPrevious = hasPrevious ? "true" : "false";
  if (els.mobileProgress) els.mobileProgress.dataset.hasNext = showMobileNext ? "true" : "false";
  if (els.mobilePrevStep) {
    els.mobilePrevStep.disabled = !hasPrevious;
    els.mobilePrevStep.hidden = !hasPrevious;
    els.mobilePrevStep.textContent = hasPrevious ? "Back" : "Previous";
    els.mobilePrevStep.title = setupPreviousLabel ? `Back: ${setupPreviousLabel}` : previous ? `Back: ${previous.step_label}` : "";
  }
  if (els.mobileNextStep) {
    els.mobileNextStep.disabled = !showMobileNext;
    els.mobileNextStep.hidden = !showMobileNext;
    els.mobileNextStep.textContent = showMobileNext ? "Next" : "Review";
    els.mobileNextStep.title = showMobileNext ? (setupNextLabel ? `Next: ${setupNextLabel}` : next ? `Next: ${next.step_label}` : "") : "";
  }
}

function renderStepRail() {
  const steps = visibleRuntimeSteps();
  const activeIndex = steps.findIndex((step) => normalizeStepKey(state.activeStep) === step.step_key);
  els.stepRail.innerHTML = steps
    .map((step, index) => {
      const isComplete = activeIndex >= 0 && index < activeIndex;
      return `
        <button class="step-link ${index === activeIndex ? "active" : ""}${isComplete ? " complete" : ""}" data-step="${step.step_key}" type="button">
          <span class="step-index">${isComplete ? "✓" : index + 1}</span>
          <span>${step.step_label}</span>
        </button>
      `;
    })
    .join("");
  els.stepRail.querySelectorAll(".step-link").forEach((button) => {
    button.addEventListener("click", () => {
      activateStep(button.dataset.step, { closeDrawer: true });
    });
  });
}

function renderChoiceCard(choice, autoAdded) {
  const selected = optionIsSelectedOrAuto(choice, autoAdded);
  const autoReason = autoAdded.get(choice.option_id);
  const disabledReason = autoReason ? "" : disableReasonForChoice(choice);
  const disabled = Boolean(disabledReason || autoReason);
  const mediaDisabled = Boolean(disabledReason);
  const detail = descriptiveTooltipText(choice.description) || descriptiveTooltipText(choice.status_label);
  const classes = ["choice-card"];
  if (cardHasMedia(choice)) classes.push("has-media");
  if (selected) classes.push("selected");
  if (disabledReason) classes.push("disabled");
  if (autoReason) classes.push("auto");
  const displayPrice = choiceDisplayPrice(choice);
  const priceMarkup = displayPrice === null ? "" : renderPriceSpan(displayPrice);
  return `
    <button class="${classes.join(" ")}" type="button" data-option="${choice.option_id}" ${disabled ? "aria-disabled=\"true\"" : ""}>
      ${renderCardMedia(choice, choice.label, { disabled: mediaDisabled })}
      <span class="topline"><span class="rpo">${escapeHtml(choice.rpo || choice.option_id)}</span>${priceMarkup}</span>
      <span class="choice-name"><span>${escapeHtml(choice.label)}</span>${renderInfoTooltip(detail, "Option details", { focusable: false })}</span>
      ${renderChoiceRelationshipBadges(choice, { disabled })}
      ${renderChoiceAvailability(
        disabledReason
          ? renderStatePill("Unavailable", "disabled-reason", disabledReason)
          : autoReason
            ? renderStatePill("Auto-added", "auto-reason", autoReason)
            : ""
      )}
    </button>
  `;
}

function renderModeLabel(section) {
  return section?.selection_mode_label || section?.selection_mode || "";
}

function sectionRequiresSelection(section, choices = []) {
  if (section?.selection_mode === "single_select_req" || truthyValue(section?.is_required)) return true;
  return choices.some((choice) => {
    const group = optionExclusiveGroup(choice.option_id);
    return exclusiveGroupRequiresSelection(group);
  });
}

function renderSectionTitle(section, fallbackLabel, choices = []) {
  const required = sectionRequiresSelection(section, choices);
  return `
    <div class="section-title">
      <h3>${escapeHtml(section?.section_name || fallbackLabel)}${required ? ' <span class="required-mark" aria-hidden="true">*</span><span class="sr-only"> required</span>' : ""}</h3>
    </div>
  `;
}

function renderInteriorCard(interior) {
  const selected = state.selectedInterior === interior.interior_id;
  const disabledReason = disableReasonForInterior(interior);
  const classes = ["choice-card"];
  if (cardHasMedia(interior)) classes.push("has-media");
  if (selected) classes.push("selected");
  if (disabledReason) classes.push("disabled");
  const detail = descriptiveTooltipText([interior.interior_material_family || interior.material, interior.source_note].filter(Boolean).join(" "));
  const label = interior.interior_leaf_label || interior.interior_name;
  return `
    <button class="${classes.join(" ")}" type="button" data-interior="${interior.interior_id}" ${disabledReason ? "aria-disabled=\"true\"" : ""}>
      ${renderCardMedia(interior, label, { disabled: Boolean(disabledReason) })}
      <span class="topline"><span class="rpo">${interior.interior_code}</span>${renderPriceSpan(adjustedInteriorDisplayPrice(interior))}</span>
      <span class="choice-name"><span>${escapeHtml(label)}</span>${renderInfoTooltip(detail || interior.interior_id, "Interior details", { focusable: false })}</span>
      ${renderChoiceAvailability(disabledReason ? renderStatePill("Unavailable", "disabled-reason", disabledReason) : "")}
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
  const colorGroups = groupInteriorsBy(interiors.slice().sort(sortInteriorsByDisplayOrder), "interior_color_family");
  const shouldCollapseGroups = colorGroups.some((group) => group.rows.length > 1);
  return `
    <div class="interior-layout">
      ${colorGroups
        .map((group) => {
          const materialGroups = groupInteriorsBy(group.rows, "interior_material_family");
          const materialSummary = [...new Set(group.rows.map((interior) => interior.interior_material_family).filter(Boolean))].join(" / ");
          const selectedInGroup = group.rows.some((interior) => interior.interior_id === state.selectedInterior);
          const groupHeader = `
                <span class="interior-group-heading">
                  <span class="interior-group-title">${escapeHtml(group.label)}</span>
                  ${materialSummary ? `<span class="interior-group-summary">${escapeHtml(materialSummary)}</span>` : ""}
                </span>
                <span class="interior-group-count">${group.rows.length === 1 ? "1 choice" : `${group.rows.length} choices`}</span>`;
          const groupBody = `
              <div class="interior-group-body">
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
              </div>`;
          if (!shouldCollapseGroups) {
            return `
            <section class="interior-group">
              <div class="interior-group-header">${groupHeader}
              </div>
              ${groupBody}
            </section>
          `;
          }
          return `
            <details class="interior-group"${selectedInGroup ? " open" : ""}>
              <summary class="interior-group-header">${groupHeader}
              </summary>
              ${groupBody}
            </details>
          `;
        })
        .join("")}
    </div>
  `;
}

function renderContextCard(choice, { setup = false, compact = false } = {}) {
  const selected =
    (choice.context_type === "body_style" && choice.value === state.bodyStyle) ||
    (choice.context_type === "trim_level" && choice.body_style === state.bodyStyle && choice.trim_level === state.trimLevel);
  const disabled = choice.context_type === "trim_level" && choice.body_style !== state.bodyStyle;
  const classes = ["choice-card", "context-choice-card"];
  if (setup) classes.push("setup-choice-card");
  if (cardHasMedia(choice)) classes.push("has-media");
  if (selected) classes.push("selected");
  if (disabled) classes.push("disabled");
  const price = choice.base_price ? formatMoney(choice.base_price) : "";
  const statusLabel = selected ? "Selected" : disabled ? "Unavailable" : "Select";
  const description = setup ? choice.description : compact ? "" : choice.description;
  const tooltip = choice.context_type === "trim_level" ? choice.info_tooltip : setup ? choice.info_tooltip : compact ? "" : choice.info_tooltip;
  const choiceName = description || tooltip ? `<span class="choice-name">${description ? `<span>${escapeHtml(description)}</span>` : ""}${renderInfoTooltip(tooltip, `${choice.label} details`)}</span>` : "";
  return `
    <button class="${classes.join(" ")}" type="button" data-context-choice="${choice.context_choice_id}" ${disabled ? "aria-disabled=\"true\"" : ""}>
      ${renderCardMedia(choice, choice.description || choice.label, { disabled })}
      <span class="topline"><span class="rpo">${escapeHtml(choice.label)}</span><span class="price">${price}</span></span>
      ${choiceName}
      <span class="selection-status" data-selected="${selected ? "true" : "false"}">${selected ? "✓ " : ""}${statusLabel}</span>
      ${renderChoiceAvailability(
        disabled
          ? renderStatePill(`Choose ${choice.body_style[0].toUpperCase() + choice.body_style.slice(1)} first`, "disabled-reason", `Choose ${choice.body_style[0].toUpperCase() + choice.body_style.slice(1)} body style first.`)
          : ""
      )}
    </button>
  `;
}

function modelEntries() {
  return Object.entries(registry.models || {}).map(([key, model]) => ({
    key,
    label: model.label || key,
    modelName: model.modelName || model.label || key,
    data: model.data,
    image_url: model.image_url || "",
    image_alt: model.image_alt || "",
    image_fit: model.image_fit || "",
    image_position: model.image_position || "",
    hover_image_url: model.hover_image_url || "",
    hover_image_alt: model.hover_image_alt || "",
    hover_image_position: model.hover_image_position || "",
  }));
}

function activeModelHighlight(modelKey = activeModelKey) {
  const model = registry.models?.[modelKey] || activeModel;
  return (
    vehicleSetupHighlights[modelKey] || {
      eyebrow: "Corvette foundation",
      title: `${model?.label || "Corvette"} sets the starting personality`,
      description: "Choose the model that best matches how this build should feel before moving into body style, trim, colors, and options.",
      facts: [model?.modelName || model?.label || "Corvette"],
    }
  );
}

function bodyStyleHighlight(bodyStyle = state.bodyStyle) {
  const bodyLabel = formatBodyStyle(bodyStyle) || "Body style";
  if (bodyStyle === "convertible") {
    return {
      eyebrow: "Open-air presentation",
      title: "Hardtop convertible character",
      description: "Convertible adds open-air driving with a power retractable hardtop, then lets you choose the trim that fits your comfort and feature preferences.",
      facts: ["Open-air driving", "Power retractable hardtop", "Choose trim next"],
    };
  }
  return {
    eyebrow: "Removable-roof coupe",
    title: `${bodyLabel} keeps the cockpit focused`,
    description: "Coupe preserves the classic mid-engine silhouette with a removable roof-panel experience, then lets you choose the trim that fits your comfort and feature preferences.",
    facts: ["Removable roof panel", "Focused cockpit feel", "Choose trim next"],
  };
}

function trimLevelHighlight(trimLevel = state.trimLevel) {
  const choice = trimLevelSetupChoices().find((item) => item.trim_level === trimLevel) || trimLevelSetupChoices()[0];
  const plainDetail = plainTooltipText(choice?.info_tooltip || choice?.description || "");
  return {
    eyebrow: "Trim Level",
    title: plainDetail || "Choose the comfort, technology, and interior-content level that fits how you want to use the car.",
    description: "Trim Level defines your available interior configuration, creature comforts, and safety features.",
    facts: ["Interior configuration", "Comfort and technology", "Safety features"],
  };
}

function renderVehicleSetupEquipmentItems(rows) {
  return `
    <ul class="vehicle-setup-equipment-list">
      ${rows
        .map(
          (item) =>
            `<li><span>${escapeHtml(item.label)}</span>${renderInfoTooltip(item.description, "Equipment details")}</li>`
        )
        .join("")}
    </ul>
  `;
}

function renderVehicleSetupEquipmentDisclosure() {
  const rows = trimEquipmentRows();
  if (!rows.length) return "";
  const countLabel = rows.length === 1 ? "1 included item" : `${rows.length} included items`;
  return `
    <details class="vehicle-setup-equipment-disclosure">
      <summary>
        <span>See what this trim includes</span>
        <em>${escapeHtml(countLabel)}</em>
      </summary>
      ${renderVehicleSetupEquipmentItems(rows)}
    </details>
  `;
}

function renderVehicleSetupNextAction(ctaLabel = "") {
  if (!ctaLabel) return "";
  const buttonLabel = /^(Continue|Review)\b/.test(ctaLabel) ? ctaLabel : `Continue to ${ctaLabel}`;
  return `
    <div class="vehicle-setup-next-action">
      <p>When this starting point looks right, continue with <strong>${escapeHtml(ctaLabel)}</strong>.</p>
      <button type="button" data-next-step="model">${escapeHtml(buttonLabel)}</button>
    </div>
  `;
}

function renderVehicleSetupHighlight(highlight, ctaLabel = "") {
  if (!highlight) return "";
  const classes = ["vehicle-setup-highlight"];
  if (highlight.compact) classes.push("compact");
  return `
    <aside class="${classes.join(" ")}" aria-label="Selected vehicle highlight">
      <p class="eyebrow">${escapeHtml(highlight.eyebrow || "Vehicle highlight")}</p>
      <h4>${escapeHtml(highlight.title || "Build foundation")}</h4>
      <p>${escapeHtml(highlight.description || "")}</p>
      ${
        highlight.facts?.length
          ? `<div class="vehicle-setup-facts">${highlight.facts.map((fact) => `<span>${escapeHtml(fact)}</span>`).join("")}</div>`
          : ""
      }
      ${highlight.equipmentDisclosure ? renderVehicleSetupEquipmentDisclosure() : ""}
      ${renderVehicleSetupNextAction(ctaLabel)}
    </aside>
  `;
}

function renderModelCard(model) {
  const selected = model.key === activeModelKey;
  const classes = ["choice-card", "model-choice-card"];
  if (cardHasMedia(model)) classes.push("has-media");
  if (selected) classes.push("selected");
  const descriptor = model.modelName || model.label;
  const highlight = activeModelHighlight(model.key);
  return `
    <button class="${classes.join(" ")}" type="button" data-model-choice="${escapeHtml(model.key)}" aria-pressed="${selected ? "true" : "false"}" aria-label="${escapeHtml(descriptor)}">
      ${renderCardMedia(model, model.modelName || model.label)}
      <span class="topline"><span class="rpo">${escapeHtml(model.label)}</span><span class="price">Model</span></span>
      <span class="choice-name"><span>${escapeHtml(highlight.cardSubtitle || highlight.eyebrow)}</span></span>
      <span class="selection-status" data-selected="${selected ? "true" : "false"}">${selected ? "✓ Selected" : "Select"}</span>
    </button>
  `;
}

function bodyStyleSetupChoices() {
  return data.contextChoices
    .filter((choice) => choice.step_key === "body_style")
    .map((choice) => {
      const bodyVariants = variants.filter((variant) => variant.body_style === choice.value);
      const startingPrice = Math.min(...bodyVariants.map((variant) => Number(variant.base_price || 0)).filter((price) => price > 0));
      return {
        ...choice,
        description: "",
        base_price: Number.isFinite(startingPrice) ? startingPrice : choice.base_price,
      };
    })
    .sort((a, b) => Number(a.display_order || 0) - Number(b.display_order || 0));
}

function trimLevelSetupChoices() {
  return data.contextChoices
    .filter((choice) => choice.step_key === "trim_level" && choice.body_style === state.bodyStyle)
    .sort((a, b) => Number(a.display_order || 0) - Number(b.display_order || 0));
}

function formatBodyStyle(bodyStyle) {
  return bodyStyle ? bodyStyle[0].toUpperCase() + bodyStyle.slice(1) : "";
}

function setupStageSummary(stage) {
  if (stage === "model") return activeModel.label || "Choose";
  if (stage === "body_style") return formatBodyStyle(state.bodyStyle) || "Choose";
  if (stage === "trim_level") return state.trimLevel || "Choose";
  return "Ready";
}

function renderVehicleSetupStepper() {
  const activeStage = normalizeVehicleSetupStage(state.vehicleSetupStage);
  const stageOrder = ["model", "body_style", "trim_level", "ready"];
  const activeIndex = stageOrder.indexOf(activeStage);
  const stages = [
    ["model", "Model"],
    ["body_style", "Body Style"],
    ["trim_level", "Trim"],
  ];
  return `
    <div class="vehicle-setup-stepper compact" aria-label="Vehicle setup progress">
      ${stages
        .map(([stage, label], index) => {
          const isActive = activeStage === stage;
          const isComplete = activeIndex > stageOrder.indexOf(stage);
          return `
            <button class="vehicle-setup-chip ${isActive ? "active" : ""}" type="button" data-setup-stage="${stage}" data-setup-chip-state="${isActive ? "active" : isComplete ? "complete" : "upcoming"}" aria-pressed="${isActive ? "true" : "false"}" ${isActive ? 'aria-current="step"' : ""}>
              <span>${isComplete ? "✓" : index + 1}</span>
              <strong>${label}</strong>
              <em>${escapeHtml(setupStageSummary(stage))}</em>
            </button>
          `;
        })
        .join("")}
    </div>
  `;
}

function renderVehicleSetupPanel(title, note, cardsHtml, className = "", highlight = null, nextLabel = "") {
  const compactTrimPanel = className.includes("trim-setup-group");
  return `
    <section class="vehicle-setup-panel ${className}" data-setup-panel>
      <div class="vehicle-setup-group-heading">
        <h3>${escapeHtml(title)}</h3>
        ${note ? `<p>${escapeHtml(note)}</p>` : ""}
      </div>
      <div class="choice-grid setup-choice-grid">${cardsHtml}</div>
      ${renderVehicleSetupHighlight(compactTrimPanel && highlight ? { ...highlight, compact: true } : highlight, nextLabel)}
    </section>
  `;
}

function renderVehicleSetupReadyPanel() {
  const variant = currentVariant();
  const displayName = variant?.display_name || activeModel.modelName || activeModel.label || "Corvette";
  return `
    <section class="vehicle-setup-panel vehicle-setup-ready" data-setup-panel>
      <p class="eyebrow">Ready for customization</p>
      <h3>${escapeHtml(displayName)}</h3>
      <p>Model, body style, and trim are set. Continue to paint, or use the setup choices above to adjust the starting point.</p>
      <div class="vehicle-setup-ready-meta" aria-label="Selected starting price">
        <span>Base MSRP</span>
        <strong>${formatMoney(Number(variant?.base_price || 0))}</strong>
      </div>
      ${renderVehicleSetupNextAction("Continue to Exterior Paint")}
    </section>
  `;
}

function renderVehicleSetupContent() {
  const stage = normalizeVehicleSetupStage(state.vehicleSetupStage);
  const modelCards = modelEntries().map(renderModelCard).join("");
  const bodyCards = bodyStyleSetupChoices().map((choice) => renderContextCard(choice, { setup: true, compact: true })).join("");
  const trimCards = trimLevelSetupChoices().map((choice) => renderContextCard(choice, { setup: true, compact: true })).join("");
  const selectedBody = formatBodyStyle(state.bodyStyle) || "selected body style";
  const panel =
    stage === "body_style"
      ? renderVehicleSetupPanel(
          "Choose your body style",
          "Pick the roof experience. The selection stays here so you can compare before continuing.",
          bodyCards,
          "body-setup-group",
          bodyStyleHighlight(),
          "Trim Level"
        )
      : stage === "trim_level"
        ? renderVehicleSetupPanel(
            "Choose your trim",
            `Choose the comfort, technology, and interior-content level for your ${selectedBody}.`,
            trimCards,
            "trim-setup-group",
            { ...trimLevelHighlight(), equipmentDisclosure: true },
            "Vehicle Setup Review"
          )
        : stage === "ready"
          ? renderVehicleSetupReadyPanel()
          : renderVehicleSetupPanel(
              "Choose your model",
              "Start with the Corvette personality for this build. Selection previews the highlights before the flow moves on.",
              modelCards,
              "model-setup-group",
              activeModelHighlight(),
              "Body Style"
            );
  return `
    <section class="section-block vehicle-setup-section" data-vehicle-setup-stage="${stage}">
      ${renderVehicleSetupStepper()}
      ${panel}
    </section>
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
                    `<li><span>${escapeHtml(item.label)}</span>${renderInfoTooltip(item.description, "Equipment details")}</li>`
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
  return standardEquipmentRows().filter((item) => item.standard_equipment_group_type === "trim_equipment");
}

function isMobileViewport() {
  return Boolean(window.matchMedia?.("(max-width: 760px)").matches);
}

function renderTrimStandardEquipment() {
  const openGroupName = isMobileViewport() ? "" : `${state.trimLevel} Equipment`;
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

function renderFinalStepActions() {
  const missing = missingRequired();
  const downloadTitle = missing.length ? "Complete required selections before downloading your build." : "";
  const submitTitle = missing.length ? "Complete required selections before submitting your build." : "";
  const disabled = missing.length ? "disabled" : "";
  return `
    <footer class="step-footer final-step-actions" aria-label="Build actions">
      <button type="button" data-final-download ${disabled} title="${downloadTitle}">Download Build</button>
      <button type="button" data-final-submit ${disabled} title="${submitTitle}">Submit to Dealer</button>
    </footer>
  `;
}

function renderChoiceGrid(choices, autoAdded) {
  if (!choices.length) return "";
  return `<div class="choice-grid">${choices.map((choice) => renderChoiceCard(choice, autoAdded)).join("")}</div>`;
}

function customerSafeGroupNote(group) {
  const note = String(group?.notes || "").trim();
  if (!note || /\b(option_ids?|group_id|runtime|workbook|radio peers?|inactive|source|draft|reactivation|output|selected default|cannot be cleared)\b/i.test(note)) return "";
  return note;
}

function renderChoiceRelationGroup(group, choices, autoAdded) {
  const note = customerSafeGroupNote(group);
  return `
    <div class="choice-relation-group" data-choice-relation-group="${escapeHtml(group.group_id)}">
      <div class="choice-relation-heading">
        <div>
          <h4 class="choice-relation-title">Related options</h4>
          ${note ? `<p class="choice-relation-note">${escapeHtml(note)}</p>` : ""}
        </div>
      </div>
      ${renderChoiceGrid(choices, autoAdded)}
    </div>
  `;
}

function renderStepChoiceGroups(choices, autoAdded) {
  const rendered = [];
  const consumed = new Set();
  let looseChoices = [];
  const flushLoose = () => {
    if (!looseChoices.length) return;
    rendered.push(renderChoiceGrid(looseChoices, autoAdded));
    looseChoices = [];
  };

  for (const choice of choices) {
    if (consumed.has(choice.option_id)) continue;
    const group = optionExclusiveGroup(choice.option_id);
    const peers = group && exclusiveGroupAllowsSingleSelection(group)
      ? choices.filter((candidate) => (group.option_ids || []).includes(candidate.option_id))
      : [];
    if (group && peers.length > 1) {
      flushLoose();
      for (const peer of peers) consumed.add(peer.option_id);
      rendered.push(renderChoiceRelationGroup(group, peers, autoAdded));
    } else {
      looseChoices.push(choice);
      consumed.add(choice.option_id);
    }
  }
  flushLoose();
  return rendered.join("");
}

function renderStepContent({ resetScroll = false } = {}) {
  const step = runtimeSteps.find((item) => item.step_key === state.activeStep);
  const autoAdded = computeAutoAdded();
  const isContextStep = state.activeStep === "body_style" || state.activeStep === "trim_level";
  const isModelStep = state.activeStep === "model";
  let body = "";

  if (isModelStep) {
    body = renderVehicleSetupContent();
  } else if (isContextStep) {
    const contextChoices = data.contextChoices
      .filter((choice) => choice.step_key === state.activeStep)
      .filter((choice) => choice.context_type !== "trim_level" || choice.body_style === state.bodyStyle)
      .sort((a, b) => Number(a.display_order || 0) - Number(b.display_order || 0));
    const section = sectionsById.get(state.activeStep === "body_style" ? "sec_context_body_style" : "sec_context_trim_level");
    body = `
      <section class="section-block context-step-section">
        ${renderSectionTitle(section, step?.step_label)}
        <div class="choice-grid">${contextChoices.map(renderContextCard).join("")}</div>
      </section>
      ${state.activeStep === "trim_level" ? renderTrimStandardEquipment() : ""}
    `;
  } else if (state.activeStep === "base_interior") {
    const interiors = validInteriorsForSelectedSeat();
    const selectedSeat = selectedSeatChoice();
    body = `
      <section class="section-block interior-color-section">
        ${selectedSeat ? `<p class="selected-seat-context">Showing colors compatible with ${escapeHtml(selectedSeat.rpo)} ${escapeHtml(selectedSeat.label)}.</p>` : ""}
        ${renderInteriorGroups(interiors)}
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
            ${renderSectionTitle(section, sectionId, choices)}
            ${renderStepChoiceGroups(choices, autoAdded)}
          </section>
        `;
      })
      .join("");
    if (!body) body = "<p class=\"empty\">No choices are mapped to this step for the active body and trim.</p>";
    if (state.activeStep === "paint") body = renderVehicleStage() + body;
  }

  const next = nextStep();
  const isVehicleSetupStep = isModelStep;
  const nextButtonLabel = next ? `Next: ${next.step_label}` : "";
  els.stepContent.dataset.activeStep = state.activeStep;
  els.stepContent.dataset.stepKind = isModelStep ? "model" : isContextStep ? "context" : "option";
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
      next && !isVehicleSetupStep
        ? `<footer class="step-footer"><button type="button" data-next-step="${next.step_key}">${nextButtonLabel}</button></footer>`
        : !next
          ? renderFinalStepActions()
          : ""
    }
  `;
  if (resetScroll) resetStepScroll();
  bindCustomerForm();
  els.stepContent.querySelectorAll("[data-option]").forEach((button) => {
    button.addEventListener("click", (event) => {
      if (stopEventAfterTooltipTouch(event)) return;
      const choice = activeChoiceRows().find((item) => item.option_id === button.dataset.option);
      if (choice) handleChoice(choice);
    });
  });
  els.stepContent.querySelectorAll("[data-interior]").forEach((button) => {
    button.addEventListener("click", (event) => {
      if (stopEventAfterTooltipTouch(event)) return;
      const interior = interiorsById.get(button.dataset.interior);
      if (interior) handleInterior(interior);
    });
  });
  els.stepContent.querySelectorAll("[data-context-choice]").forEach((button) => {
    button.addEventListener("click", (event) => {
      if (stopEventAfterTooltipTouch(event)) return;
      const choice = data.contextChoices.find((item) => item.context_choice_id === button.dataset.contextChoice);
      if (choice && !(choice.context_type === "trim_level" && choice.body_style !== state.bodyStyle)) handleContextChoice(choice);
    });
  });
  els.stepContent.querySelectorAll("[data-model-choice]").forEach((button) => {
    button.addEventListener("click", (event) => {
      if (stopEventAfterTooltipTouch(event)) return;
      requestModelChange(button.dataset.modelChoice);
    });
  });
  els.stepContent.querySelectorAll("[data-setup-stage]").forEach((button) => {
    button.addEventListener("click", () => {
      setVehicleSetupStage(button.dataset.setupStage);
    });
  });
  els.stepContent.querySelector("[data-next-step]")?.addEventListener("click", goToNextStep);
  els.stepContent.querySelector("[data-final-download]")?.addEventListener("click", downloadBuild);
  els.stepContent.querySelector("[data-final-submit]")?.addEventListener("click", openDealerSubmitModal);
  bindTooltips(els.stepContent);
}

function renderSummaryRpoRow(item, { includeReason = false } = {}) {
  return `
    <li class="summary-rpo-row">
      <span class="summary-rpo-code">${escapeHtml(item.rpo || item.id)}</span>
      <span class="summary-rpo-label">${escapeHtml(item.label)}</span>
      ${renderPriceSpan(item.price, "summary-rpo-price")}
      ${includeReason && item.reason ? renderInfoTooltip(item.reason, "Auto-added reason") : ""}
    </li>
  `;
}

function renderSectionedSummaryItems(items, pricing) {
  if (!items.length) return "<li class=\"empty\">No selections yet.</li>";
  const sections = sectionedOrderRecap(items, pricing).filter(
    (section) => !["vehicle", "pricing_summary", "auto_added_required"].includes(section.section_key) && section.items.length
  );
  return sections
    .map(
      (section) => `
        <li class="summary-rpo-section">
          <div class="summary-section-heading">
            <span>${escapeHtml(section.section_label)}</span>
          </div>
          <ul class="summary-rpo-rows">
            ${section.items.map((item) => renderSummaryRpoRow(item)).join("")}
          </ul>
        </li>
      `
    )
    .join("") || "<li class=\"empty\">No selections yet.</li>";
}

function renderAutoSummaryItems(items) {
  return items.map((item) => renderSummaryRpoRow(item, { includeReason: true })).join("") || "<li class=\"empty\">No auto-added RPOs.</li>";
}

function renderSummary() {
  const variant = currentVariant();
  const items = lineItems();
  const base = Number(variant?.base_price || 0);
  const optionsTotal = items.reduce((sum, item) => sum + Number(item.price || 0), 0);
  const total = base + optionsTotal;
  els.summaryBase.textContent = formatMoney(base);
  els.summaryOptions.textContent = formatMoney(optionsTotal);
  els.summaryTotal.textContent = formatMoney(total);
  els.variantName.textContent = variant?.display_name || activeModel.label || "Stingray";

  const selectedItems = items.filter((item) => item.type !== "auto_added" || item.section_key !== "auto_added_required");
  const autoItems = items.filter((item) => item.type === "auto_added" && item.section_key === "auto_added_required");
  els.selectedList.innerHTML = renderSectionedSummaryItems(selectedItems, {
    base_price: base,
    total_msrp: total,
  });
  els.autoList.innerHTML = renderAutoSummaryItems(autoItems);
  const missingDetails = missingRequirementDetails();
  const missing = missingDetails.map((item) => item.label);
  if (els.requirementsCard) els.requirementsCard.dataset.requirementsStatus = missing.length ? "open" : "complete";
  els.missingList.innerHTML =
    missingDetails
      .map(
        (item) => `
          <li class="requirement-item"><span>${escapeHtml(item.label)}</span></li>
        `
      )
      .join("") ||
    "<li class=\"empty positive\">All required selections are complete.</li>";
  els.downloadBuildButton.disabled = missing.length > 0;
  els.downloadBuildButton.title = missing.length ? "Complete required selections before downloading your build." : "";
  if (els.submitDealerButton) {
    els.submitDealerButton.disabled = missing.length > 0;
    els.submitDealerButton.title = missing.length ? "Complete required selections before submitting your build." : "";
  }
  if (els.mobileSummaryTotal) els.mobileSummaryTotal.textContent = formatMoney(total);
  if (els.mobileSummarySelected) {
    els.mobileSummarySelected.textContent =
      selectedItems.length === 1 ? "1 selected item" : `${selectedItems.length} selected items`;
  }
  if (els.mobileSummaryMissing) {
    els.mobileSummaryMissing.textContent = "›";
  }
  if (els.mobileSummaryButton) {
    const selectedLabel = selectedItems.length === 1 ? "1 selected item" : `${selectedItems.length} selected items`;
    const requirementsLabel = missing.length === 0 ? "requirements complete" : `${missing.length} required choices left`;
    els.mobileSummaryButton.setAttribute?.("aria-label", `View build summary: ${formatMoney(total)}, ${selectedLabel}, ${requirementsLabel}`);
  }
  renderStandardEquipment();

  const dataWarnings = (data.validation || []).filter((item) => item.severity === "error");
  els.alertRegion.innerHTML = dataWarnings.map((item) => `<div class="alert">${item.message}</div>`).join("");
  bindTooltips(els.summaryDrawer);
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
    <div class="standard-equipment-summary">Standard & Included <span>${rows.length}</span></div>
    ${renderStandardEquipmentGroups(rows)}
  `;
}

function vehicleInformation(variant) {
  return {
    model_year: variant?.model_year || "",
    model: activeModel.modelName || "Corvette Stingray",
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
  const summarySections = orderSummarySections();
  const sections = new Map(
    summarySections.map(({ section_key, section_label }) => [
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
  const sectionOrder = orderSummarySectionOrder();
  return [...sections.values()]
    .filter(
      (section) =>
        section.items.length ||
        ["vehicle", "pricing_summary"].includes(section.section_key)
    )
    .sort((a, b) => (sectionOrder.get(a.section_key) ?? 999) - (sectionOrder.get(b.section_key) ?? 999));
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
  const interiorComponents = items.filter((item) => item.type === "interior_component");
  const selectedInterior = items.find((item) => item.type === "selected_interior") || {};
  return {
    customer: customerInformation(),
    vehicle: vehicleInformation(variant),
    pricing,
    sections: sectionedOrderRecap(items, pricing),
    selected_options: selectedOptions,
    auto_added_options: autoAddedOptions,
    interior_components: interiorComponents,
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
      .filter((section) => !["vehicle", "pricing_summary"].includes(section.section_key))
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

function escapeHtml(value) {
  return String(value ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function titleCaseSection(label) {
  return String(label || "")
    .trim()
    .toLowerCase()
    .replace(/\b\w/g, (char) => char.toUpperCase());
}

function plainTextOrderSummary(order = compactOrder()) {
  const lines = [
    "<p>",
    `<strong>Name:</strong> ${escapeHtml(order.customer.name || "")}<br>`,
    `<strong>Email:</strong> ${escapeHtml(order.customer.email || "")}<br>`,
    `<strong>Phone:</strong> ${escapeHtml(order.customer.phone || "")}`,
  ];
  if (order.customer.comments) lines.push(`<br><strong>Comments:</strong> ${escapeHtml(order.customer.comments)}`);
  lines.push(`</p>`, `<p><strong>Submitted:</strong> ${escapeHtml(order.submitted_at)}</p>`);
  lines.push(`<p><strong><u>Variant</u></strong></p>`, `<ul><li>${escapeHtml(order.vehicle.display_name || "")}</li></ul>`);

  for (const section of order.sections) {
    lines.push(`<p><strong><u>${escapeHtml(titleCaseSection(section.section))}</u></strong></p>`, "<ul>");
    for (const item of section.items) {
      const label = `${item.rpo} ${item.label}`.trim();
      lines.push(`<li>${escapeHtml(label)}: ${escapeHtml(formatMoney(item.price))}</li>`);
    }
    lines.push("</ul>");
  }

  lines.push(`<p><strong>Total MSRP: ${escapeHtml(formatMoney(order.msrp))}</strong></p>`);
  return lines.join("");
}

function buildMarkdown(order = compactOrder()) {
  const lines = [
    `# ${order.title}`,
    "",
    `Generated: ${order.submitted_at}`,
    "",
    "### Variant",
    "",
    `- ${order.vehicle.display_name || ""}`,
    "",
  ];

  for (const section of order.sections) {
    if (!section.items.length) continue;
    lines.push(`### ${section.section}`, "");
    for (const item of section.items) {
      const rpo = item.rpo ? `${item.rpo} ` : "";
      lines.push(`- ${rpo}${item.label || ""}: ${formatMoney(item.price)}`);
    }
    lines.push("");
  }

  lines.push("### MSRP", "", `- Total MSRP: ${formatMoney(order.msrp)}`, "");
  return lines.join("\n").replace(/\n{3,}/g, "\n\n");
}

window.__orderDebug = {
  currentOrder,
  compactOrder,
  plainTextOrderSummary,
  buildMarkdown,
};

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
  download(`${activeModel.exportSlug || "stingray"}-order-summary.json`, JSON.stringify(compactOrder(), null, 2), "application/json");
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
  download(`${activeModel.exportSlug || "stingray"}-order-summary.csv`, rows.join("\n"), "text/csv");
}

function downloadBuild() {
  if (missingRequired().length > 0) return;
  download(`${activeModel.exportSlug || "stingray"}-build.md`, buildMarkdown(), "text/markdown");
}

function setDealerSubmitStatus(message, type = "") {
  if (!els.dealerSubmitStatus) return;
  els.dealerSubmitStatus.textContent = message;
  els.dealerSubmitStatus.dataset.status = type;
}

function dealerSubmitSuccessMessage() {
  const entryText = state.dealerSubmissionEntryId ? ` Confirmation ID: ${state.dealerSubmissionEntryId}.` : "";
  return `Build submitted to Stingray Chevrolet. A Corvette specialist will contact you soon.${entryText}`;
}

function setTurnstileToken(token = "") {
  state.turnstileToken = token;
}

function resetTurnstileWidget() {
  state.turnstileToken = "";
  if (window.turnstile && state.turnstileWidgetId) {
    window.turnstile.reset(state.turnstileWidgetId);
  }
}

function renderTurnstileWidget() {
  if (!els.dealerTurnstile || !window.turnstile || state.turnstileWidgetId) return;
  state.turnstileWidgetId = window.turnstile.render("#dealerTurnstile", {
    sitekey: TURNSTILE_SITE_KEY,
    callback: setTurnstileToken,
    "expired-callback": resetTurnstileWidget,
    "error-callback": resetTurnstileWidget,
  });
}

function syncDealerSubmitControls() {
  if (els.dealerSubmitConfirmButton) {
    els.dealerSubmitConfirmButton.textContent = "Submit";
    els.dealerSubmitConfirmButton.hidden = state.dealerSubmissionComplete;
    els.dealerSubmitConfirmButton.disabled = state.dealerSubmissionComplete;
  }
  if (els.dealerSubmitCancelButton) {
    els.dealerSubmitCancelButton.textContent = state.dealerSubmissionComplete ? "Close" : "Cancel";
  }
}

function resetDealerSubmissionState() {
  state.dealerSubmissionComplete = false;
  state.dealerSubmissionEntryId = "";
  resetTurnstileWidget();
  syncDealerSubmitControls();
}

function populateDealerSubmitForm() {
  if (els.dealerSubmitName) els.dealerSubmitName.value = state.customer.name;
  if (els.dealerSubmitEmail) els.dealerSubmitEmail.value = state.customer.email;
  if (els.dealerSubmitPhone) els.dealerSubmitPhone.value = state.customer.phone;
  if (els.dealerSubmitComments) els.dealerSubmitComments.value = state.customer.comments;
}

function readDealerSubmitForm() {
  state.customer.name = (els.dealerSubmitName?.value || "").trim();
  state.customer.email = (els.dealerSubmitEmail?.value || "").trim();
  state.customer.phone = (els.dealerSubmitPhone?.value || "").trim();
  state.customer.comments = (els.dealerSubmitComments?.value || "").trim();
  return customerInformation();
}

function dealerSubmitErrors(customer = readDealerSubmitForm()) {
  const errors = [];
  if (!customer.name) errors.push("Name is required.");
  if (!customer.email) {
    errors.push("Email is required.");
  } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(customer.email)) {
    errors.push("Enter a valid email address.");
  }
  return errors;
}

function dealerSubmissionPayload(order = compactOrder()) {
  return {
    model: activeModelKey,
    customer: order.customer,
    vehicle: order.vehicle,
    sections: order.sections,
    msrp: formatMoney(order.msrp),
    plain_text_summary: plainTextOrderSummary(order),
    turnstile_token: state.turnstileToken,
  };
}

async function postDealerSubmission(payload) {
  const response = await fetch(DEALER_SUBMIT_ENDPOINT, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });
  let result = {};
  try {
    result = await response.json();
  } catch {
    result = {};
  }
  if (!response.ok || result.success === false) {
    throw new Error(result.message || "Could not submit build to dealer.");
  }
  return result;
}

function openDealerSubmitModal() {
  if (missingRequired().length > 0 || !els.dealerSubmitModal) return;
  populateDealerSubmitForm();
  syncDealerSubmitControls();
  renderTurnstileWidget();
  if (state.dealerSubmissionComplete) {
    setDealerSubmitStatus(dealerSubmitSuccessMessage(), "success");
  } else {
    setDealerSubmitStatus(DEALER_SUBMIT_HELPER_TEXT, "");
  }
  els.dealerSubmitModal.hidden = false;
  els.dealerSubmitName?.focus?.();
}

function closeDealerSubmitModal() {
  if (!els.dealerSubmitModal) return;
  els.dealerSubmitModal.hidden = true;
  if (!state.dealerSubmissionComplete) setDealerSubmitStatus(DEALER_SUBMIT_HELPER_TEXT, "");
}

async function submitDealerBuild(event) {
  event?.preventDefault?.();
  if (state.dealerSubmissionComplete) {
    setDealerSubmitStatus(dealerSubmitSuccessMessage(), "success");
    syncDealerSubmitControls();
    return null;
  }
  if (missingRequired().length > 0) {
    setDealerSubmitStatus("Complete required selections before submitting your build.", "error");
    return null;
  }
  const customer = readDealerSubmitForm();
  const errors = dealerSubmitErrors(customer);
  if (errors.length) {
    setDealerSubmitStatus(errors.join(" "), "error");
    resetTurnstileWidget();
    return null;
  }
  if (!state.turnstileToken) renderTurnstileWidget();
  if (!state.turnstileToken) {
    setDealerSubmitStatus("Security check is required. Please try again.", "error");
    resetTurnstileWidget();
    return null;
  }
  const payload = dealerSubmissionPayload();
  window.__lastDealerSubmission = payload;
  setDealerSubmitStatus("Submitting build to dealer...", "");
  if (els.dealerSubmitConfirmButton) els.dealerSubmitConfirmButton.disabled = true;
  try {
    const result = await postDealerSubmission(payload);
    state.dealerSubmissionComplete = true;
    state.dealerSubmissionEntryId = result.entry_id || "";
    setDealerSubmitStatus(dealerSubmitSuccessMessage(), "success");
    syncDealerSubmitControls();
    return { payload, result };
  } catch (error) {
    setDealerSubmitStatus(error?.message || "Could not submit build to dealer.", "error");
    resetTurnstileWidget();
    return null;
  } finally {
    if (els.dealerSubmitConfirmButton && !state.dealerSubmissionComplete) els.dealerSubmitConfirmButton.disabled = false;
  }
}

function resetModelScopedState() {
  const first = variants[0] || {};
  resetDealerSubmissionState();
  state.bodyStyle = first.body_style || "";
  state.trimLevel = first.trim_level || "";
  state.selected.clear();
  state.userSelected.clear();
  state.selectedInterior = "";
  state.activeStep = "model";
  state.vehicleSetupStage = "model";
}

function renderModelChrome() {
  const title = `${activeModel.label || "Stingray"} Order Form`;
  if (els.appTitle) els.appTitle.textContent = title;
  document.title = title;
}

function activateModel(modelKey, { preserveCustomer = true, shouldRender = true, vehicleSetupStage = "model", preserveScroll = false } = {}) {
  const nextModel = registry.models[modelKey];
  if (!nextModel) return;
  activeModelKey = modelKey;
  activeModel = nextModel;
  data = activeModel.data;
  rebuildDataIndexes();
  resetModelScopedState();
  state.vehicleSetupStage = normalizeVehicleSetupStage(vehicleSetupStage);
  if (!preserveCustomer) resetCustomerInformation();
  resetDefaults();
  reconcileSelections();
  renderModelChrome();
  if (shouldRender) render(preserveScroll ? { preserveScroll: true } : { resetScroll: true });
}

function render({ resetScroll = false, preserveScroll = false } = {}) {
  const scrollPosition = preserveScroll ? captureScrollPosition() : null;
  applyAccentForPaint();
  renderModelChrome();
  renderStepRail();
  renderStepContent({ resetScroll });
  renderMobileProgress();
  renderSummary();
  restoreScrollPosition(scrollPosition);
}

function buildHasResettableChanges() {
  return state.userSelected.size > 0 || Boolean(state.selectedInterior) || state.activeStep !== "model";
}

function closeConfirmActionModal() {
  if (els.confirmActionModal) els.confirmActionModal.hidden = true;
  pendingConfirmationAction = null;
}

function openConfirmActionModal({ title, message, confirmLabel, onConfirm }) {
  pendingConfirmationAction = onConfirm;
  if (els.confirmActionTitle) els.confirmActionTitle.textContent = title;
  if (els.confirmActionMessage) els.confirmActionMessage.textContent = message;
  if (els.confirmActionConfirmButton) els.confirmActionConfirmButton.textContent = confirmLabel;
  if (els.confirmActionCancelButton) els.confirmActionCancelButton.textContent = "No, Cancel";
  if (els.confirmActionModal) els.confirmActionModal.hidden = false;
}

function confirmPendingAction() {
  const action = pendingConfirmationAction;
  closeConfirmActionModal();
  action?.();
}

function resetBuild() {
  resetDefaults();
  resetCustomerInformation();
  state.activeStep = "model";
  state.vehicleSetupStage = "model";
  reconcileSelections();
  render({ resetScroll: true });
}

function requestResetBuild() {
  if (!buildHasResettableChanges()) {
    resetBuild();
    return;
  }
  openConfirmActionModal({
    title: "Reset Build",
    message: "This will reset all selected options. Are you sure?",
    confirmLabel: "Yes, Reset",
    onConfirm: resetBuild,
  });
}

function requestModelChange(modelKey) {
  if (!modelKey || modelKey === activeModelKey) return;
  const nextSetupStage = normalizeVehicleSetupStage(state.vehicleSetupStage) === "model" ? "model" : "body_style";
  const preserveSetupScroll = state.activeStep === "model";
  if (!buildHasResettableChanges()) {
    activateModel(modelKey, { vehicleSetupStage: nextSetupStage, preserveScroll: preserveSetupScroll });
    return;
  }
  openConfirmActionModal({
    title: "Change Model",
    message: "Changing models will reset all selected options. Are you sure?",
    confirmLabel: "Yes, Change Model",
    onConfirm: () => activateModel(modelKey, { vehicleSetupStage: nextSetupStage, preserveScroll: preserveSetupScroll }),
  });
}

function init() {
  activateModel(activeModelKey, { shouldRender: false });
  els.resetButton.addEventListener("click", requestResetBuild);
  els.downloadBuildButton.addEventListener("click", downloadBuild);
  els.submitDealerButton?.addEventListener("click", openDealerSubmitModal);
  els.mobilePrevStep?.addEventListener("click", goToPreviousStep);
  els.mobileNextStep?.addEventListener("click", goToNextStep);
  els.openStepDrawerButton?.addEventListener("click", () => setMobileDrawer("steps"));
  els.closeStepDrawerButton?.addEventListener("click", closeMobileDrawers);
  els.openSummaryDrawerButton?.addEventListener("click", () => setMobileDrawer(els.appShell?.dataset.mobileDrawer === "summary" ? "" : "summary"));
  els.mobileSummaryButton?.addEventListener("click", () => setMobileDrawer(els.appShell?.dataset.mobileDrawer === "summary" ? "" : "summary"));
  els.closeSummaryDrawerButton?.addEventListener("click", closeMobileDrawers);
  els.mobileDrawerBackdrop?.addEventListener("click", closeMobileDrawers);
  document.addEventListener?.("keydown", handleMobileDrawerKeydown);
  document.addEventListener?.("wheel", handleDrawerWheel, { passive: false });
  els.dealerSubmitForm?.addEventListener("submit", submitDealerBuild);
  els.dealerSubmitCloseButton?.addEventListener("click", closeDealerSubmitModal);
  els.dealerSubmitCancelButton?.addEventListener("click", closeDealerSubmitModal);
  els.confirmActionCancelButton?.addEventListener("click", closeConfirmActionModal);
  els.confirmActionConfirmButton?.addEventListener("click", confirmPendingAction);
  render();
}

init();
