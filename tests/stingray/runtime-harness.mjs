import { execFileSync } from "node:child_process";
import fs from "node:fs";
import vm from "node:vm";

const APP_SOURCE = fs.readFileSync("form-app/app.js", "utf8");

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

export function loadGeneratedData() {
  const context = { window: {} };
  vm.runInNewContext(fs.readFileSync("form-app/data.js", "utf8"), context);
  return context.window.STINGRAY_FORM_DATA;
}

export function loadShadowData() {
  const output = execFileSync(".venv/bin/python", ["scripts/stingray_csv_shadow_overlay.py"], {
    cwd: process.cwd(),
    encoding: "utf8",
    maxBuffer: 8 * 1024 * 1024,
  });
  return JSON.parse(output);
}

export function createRuntime(data) {
  const downloads = [];
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
    document: {
      querySelector() {
        return makeElement();
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
  const source = APP_SOURCE.replace(
    /\ninit\(\);\s*$/,
    `
window.__testApi = {
  state,
  activeChoiceRows,
  resetDefaults,
  reconcileSelections,
  handleChoice,
  computeAutoAdded,
  disableReasonForChoice,
  optionPrice,
  lineItems,
  currentOrder,
  compactOrder: typeof compactOrder === "function" ? compactOrder : undefined,
  exportJson: typeof exportJson === "function" ? exportJson : undefined,
  exportCsv: typeof exportCsv === "function" ? exportCsv : undefined,
  plainTextOrderSummary: typeof plainTextOrderSummary === "function" ? plainTextOrderSummary : undefined,
  downloads: window.__downloads,
};
`
  );
  vm.runInNewContext(source, context);
  return context.window.__testApi;
}
