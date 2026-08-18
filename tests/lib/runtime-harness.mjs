// Shared in-process form-app harness for runtime state tests.
//
// The candidate lane points this at a temporary registry through
// CORVETTE_FORM_DATA_JS. No fallback if that override is set but unreadable —
// silently reading form-app/data.js would make a candidate stage pass while
// proving nothing about the candidate.
import fs from "node:fs";
import vm from "node:vm";

const DATA_JS_PATH = process.env.CORVETTE_FORM_DATA_JS || "form-app/data.js";

function makeElement() {
  return {
    textContent: "",
    innerHTML: "",
    value: "",
    dataset: {},
    listeners: {},
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
    change() {
      this.listeners.change?.({ target: this });
    },
  };
}

export function dataJsPath() {
  return DATA_JS_PATH;
}

export function loadDataWindow(path = DATA_JS_PATH) {
  const context = { window: {} };
  vm.runInNewContext(fs.readFileSync(path, "utf8"), context);
  return context.window;
}

export function loadRuntime({ dataPath = DATA_JS_PATH } = {}) {
  const dataWindow = loadDataWindow(dataPath);
  const downloads = [];
  const elements = new Map();
  const fetchCalls = [];
  const turnstileCalls = [];
  const scrollCalls = [];
  const document = {
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
  };
  const context = {
    window: {
      ...dataWindow,
      __downloads: downloads,
      __lastBlobContent: "",
      __lastBlobType: "",
      turnstile: {
        render(selector, options) {
          turnstileCalls.push({ fn: "render", selector, options });
          options.callback?.("test-turnstile-token");
          return "test-widget-id";
        },
        reset(widgetId) {
          turnstileCalls.push({ fn: "reset", widgetId });
        },
      },
      scrollX: 0,
      scrollY: 0,
      scrollTo(position = {}) {
        scrollCalls.push(position);
        if (typeof position.left === "number") this.scrollX = position.left;
        if (typeof position.top === "number") this.scrollY = position.top;
      },
    },
    fetch: async (url, options = {}) => {
      fetchCalls.push({ url, options });
      return {
        ok: true,
        async json() {
          return { success: true, entry_id: 445566 };
        },
      };
    },
    document,
    fetchCalls,
    elements,
    turnstileCalls,
    scrollCalls,
    Intl,
    Number,
    Set,
    Map,
    Boolean,
    Object,
    String,
    Date,
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
  const source = fs.readFileSync("form-app/app.js", "utf8").replace(
    /\ninit\(\);\s*$/,
    `
window.__testApi = {
  get activeModelKey() { return typeof activeModelKey === "undefined" ? undefined : activeModelKey; },
  get activeModelLabel() { return typeof activeModel === "undefined" ? undefined : activeModel.label; },
  get exportSlug() { return typeof activeModel === "undefined" ? undefined : activeModel.exportSlug; },
  get modelName() { return typeof activeModel === "undefined" ? undefined : activeModel.modelName; },
  get state() { return state; },
  get variants() { return typeof variants === "undefined" ? [] : variants; },
  get data() { return typeof data === "undefined" ? undefined : data; },
  setActiveData(next) { data = next; },
  activeChoiceRows,
  activateModel: typeof activateModel === "function" ? activateModel : undefined,
  requestModelChange: typeof requestModelChange === "function" ? requestModelChange : undefined,
  resetDefaults,
  reconcileSelections,
  handleChoice,
  computeAutoAdded,
  disableReasonForChoice,
  missingRequired,
  missingRequirementDetails,
  optionPrice,
  currentOrder,
  compactOrder,
  dealerSubmissionPayload,
  downloadBuild,
  fetchCalls,
  downloads: window.__downloads,
  elements,
};
init();
`
  );
  vm.runInNewContext(source, context);
  return context.window.__testApi;
}
