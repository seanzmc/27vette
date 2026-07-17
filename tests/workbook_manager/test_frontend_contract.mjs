import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

import {
  blockingFindings,
  fieldInputValue,
  findingViewModel,
  importReportViewModel,
  tableViewModel,
} from "../../workbook-manager/frontend/src/tableRegistry.js";
import { api } from "../../workbook-manager/frontend/src/api.js";
import {
  isCurrentGeneration,
  isCurrentSelection,
} from "../../workbook-manager/frontend/src/requestGuards.js";

test("uses server supplied canonical and source names", () => {
  const table = tableViewModel({
    role: "options",
    sql_table: "grand_sport_options",
    source_sheets: ["grandSport_options"],
    count: 241,
  });
  assert.equal(table.key, "options");
  assert.equal(table.sqlTable, "grand_sport_options");
  assert.equal(table.sourceLabel, "grandSport_options");
});

test("decision and contract findings are blocking", () => {
  const findings = blockingFindings([
    { status: "mapped" },
    { status: "contract_mismatch" },
    { status: "decision_required" },
  ]);
  assert.equal(findings.length, 2);
});

test("decision-required findings expose provenance but no automatic fix", () => {
  const finding = findingViewModel({
    severity: "error",
    status: "decision_required",
    model_key: "z06",
    source_sheet: "z06_options",
    source_row: 42,
    source_column: "active",
    code: "unknown_activation_rule",
    message: "A business rule is required.",
  });
  assert.equal(finding.blocking, true);
  assert.equal(finding.canAutoFix, false);
  assert.equal(finding.sourceLabel, "z06_options · row 42 · active");
});

test("API callers use encoded v2 model and role routes", async () => {
  const calls = [];
  const originalFetch = globalThis.fetch;
  globalThis.fetch = async (path, options = {}) => {
    calls.push([path, options]);
    return { ok: true, json: async () => ({}) };
  };
  try {
    await api.tables("grand sport");
    await api.schema("price rules", "grand sport");
    await api.records("option assets", {
      model: "grand sport", search: "Z 51", limit: 25, offset: 5,
    });
    await api.dependencies("option assets", "grand sport", { asset_id: "a/1" });
    await api.findings(17);
  } finally {
    globalThis.fetch = originalFetch;
  }

  assert.equal(calls[0][0], "/api/models/grand%20sport/tables");
  assert.equal(calls[1][0], "/api/models/grand%20sport/tables/price%20rules/schema");
  assert.equal(
    calls[2][0],
    "/api/models/grand%20sport/tables/option%20assets?search=Z%2051&limit=25&offset=5"
  );
  assert.equal(calls[3][0], "/api/models/grand%20sport/tables/option%20assets/dependencies");
  assert.deepEqual(JSON.parse(calls[3][1].body), { key: { asset_id: "a/1" } });
  assert.equal(calls[4][0], "/api/imports/17/findings");
});

test("import and staging use typed v2 payloads", async () => {
  const calls = [];
  const originalFetch = globalThis.fetch;
  globalThis.fetch = async (path, options = {}) => {
    calls.push([path, options]);
    return { ok: true, json: async () => ({}) };
  };
  try {
    await api.runImport("/tmp/source workbook.xlsx");
    await api.stage({
      table_role: "options",
      model_key: "stingray",
      op: "update",
      key: { option_id: "Z51" },
      record: { price: 1 },
    });
  } finally {
    globalThis.fetch = originalFetch;
  }

  assert.equal(calls[0][0], "/api/imports");
  assert.deepEqual(JSON.parse(calls[0][1].body), {
    workbook_path: "/tmp/source workbook.xlsx",
  });
  assert.equal(calls[1][0], "/api/changes");
  assert.deepEqual(JSON.parse(calls[1][1].body), {
    model_key: "stingray",
    table_role: "options",
    op: "update",
    key: { option_id: "Z51" },
    record: { price: 1 },
  });
});

test("successful import reports use exact v2 fields", () => {
  const report = importReportViewModel({
    status: "validated",
    findings: [{ status: "mapped", code: "mapped_source" }],
    decision_required: [],
    contract_differences: [],
  });
  assert.equal(report.status, "validated");
  assert.equal(report.findingCount, 1);
  assert.equal(report.blockingCount, 0);
});

test("canonical integer booleans remain editable in schema forms", () => {
  assert.equal(fieldInputValue({ ctype: "bool" }, 1), "True");
  assert.equal(fieldInputValue({ ctype: "bool" }, 0), "False");
  assert.equal(fieldInputValue({ ctype: "text" }, null), "");
});

test("checked-in React callers contain no frontend compatibility data path", () => {
  const root = new URL("../../workbook-manager/frontend/src/", import.meta.url);
  const source = (path) => readFileSync(new URL(path, root), "utf8");
  const apiSource = source("api.js");
  const recordForm = source("components/RecordForm.jsx");
  const formStructure = source("components/FormStructure.jsx");
  const changesSync = source("components/ChangesSync.jsx");
  const history = source("components/HistoryView.jsx");

  for (const legacy of ["payload.table", "model_id", "form_steps"]) {
    assert.equal(apiSource.includes(legacy), false, legacy);
  }
  assert.equal(apiSource.includes("normalized.model"), false);
  assert.match(recordForm, /model_key:\s*modelKey/);
  assert.match(recordForm, /table_role:\s*schema\.table_role/);
  assert.equal(recordForm.includes("model_id"), false);
  assert.equal(formStructure.includes("form_steps"), false);
  assert.equal(formStructure.includes("model_id"), false);
  assert.equal(changesSync.includes("importReport.run"), false);
  assert.equal(changesSync.includes("importReport.issues"), false);
  for (const field of ["model_key", "table_role", "sql_table", "entity_key"]) {
    assert.equal(changesSync.includes(field), true, field);
  }
  assert.equal(history.includes("entity_type"), false);
  assert.equal(history.includes("model_id"), false);
  assert.equal(history.includes("table_role"), true);
  assert.equal(history.includes("model_key"), true);
  assert.equal(history.includes("sql_table"), true);
  assert.equal(history.includes("entity_id"), true);
});

test("findings and model operations expose loading error and retry states", () => {
  const root = new URL("../../workbook-manager/frontend/src/", import.meta.url);
  const source = (path) => readFileSync(new URL(path, root), "utf8");
  const app = source("App.jsx");
  const findings = source("components/ImportFindings.jsx");
  const operations = source("components/ModelOperations.jsx");

  assert.match(app, /status:\s*"loading"/);
  assert.match(findings, /Loading import findings/);
  assert.match(findings, /Unable to load import findings/);
  assert.match(findings, />Retry</);
  assert.match(operations, /Loading canonical tables/);
  assert.match(operations, /Unable to load canonical tables/);
  assert.match(operations, /Loading records/);
  assert.match(operations, /Unable to load records/);
  assert.match(operations, /tableRequestRef/);
  assert.match(operations, /recordRequestRef/);
});

test("default import resolves the backend-owned workbook path", async () => {
  const calls = [];
  const originalFetch = globalThis.fetch;
  globalThis.fetch = async (path, options = {}) => {
    calls.push([path, options]);
    return {
      ok: true,
      json: async () => path === "/api/status"
        ? { workbook: { workbook_path: "/repo/stingray_master.xlsx" } }
        : {},
    };
  };
  try {
    await api.runImport();
  } finally {
    globalThis.fetch = originalFetch;
  }

  assert.equal(calls[0][0], "/api/status");
  assert.equal(calls[1][0], "/api/imports");
  assert.deepEqual(JSON.parse(calls[1][1].body), {
    workbook_path: "/repo/stingray_master.xlsx",
  });
});

test("blocked imports publish their evidence for the Findings tab", async () => {
  const originalFetch = globalThis.fetch;
  const originalWindow = globalThis.window;
  const originalCustomEvent = globalThis.CustomEvent;
  const events = [];
  globalThis.window = { dispatchEvent: (event) => events.push(event) };
  globalThis.CustomEvent = class {
    constructor(type, options) {
      this.type = type;
      this.detail = options.detail;
    }
  };
  globalThis.fetch = async () => ({
    ok: false,
    status: 409,
    statusText: "Conflict",
    json: async () => ({
      detail: {
        status: "decision_required",
        findings: [{
          status: "decision_required",
          code: "business_rule_required",
        }],
      },
    }),
  });
  try {
    await assert.rejects(api.runImport("/tmp/source.xlsx"));
  } finally {
    globalThis.fetch = originalFetch;
    globalThis.window = originalWindow;
    globalThis.CustomEvent = originalCustomEvent;
  }

  assert.equal(events.length, 1);
  assert.equal(events[0].type, "wbm:import-findings");
  assert.equal(events[0].detail.findings[0].code, "business_rule_required");
});

test("old-role debounced search cannot issue or win after selection changes", () => {
  const oldSearch = {
    generation: 4,
    modelKey: "stingray",
    tableRole: "options",
  };
  const selectedRole = {
    generation: 5,
    modelKey: "stingray",
    tableRole: "prices",
  };
  let issued = 0;
  let view = { schema: "prices", rows: ["current-price-row"] };

  if (isCurrentSelection(oldSearch, selectedRole)) issued += 1;
  if (isCurrentSelection(oldSearch, selectedRole)) {
    view = { schema: "options", rows: ["stale-option-row"] };
  }

  assert.equal(issued, 0);
  assert.deepEqual(view, {
    schema: "prices",
    rows: ["current-price-row"],
  });
  assert.equal(isCurrentSelection(selectedRole, selectedRole), true);

  const operations = readFileSync(
    new URL(
      "../../workbook-manager/frontend/src/components/ModelOperations.jsx",
      import.meta.url
    ),
    "utf8"
  );
  assert.match(operations, /selectionGenerationRef/);
  assert.match(operations, /isCurrentSelection/);
  assert.match(operations, /searchTimer\.current = null/);
});

test("older findings refresh success or failure cannot replace the newest run", () => {
  let currentGeneration = 1;
  const oldGeneration = currentGeneration;
  const newGeneration = ++currentGeneration;
  let findingsState = { status: "loading", items: [], error: "" };
  const settle = (generation, state) => {
    if (isCurrentGeneration(generation, currentGeneration)) {
      findingsState = state;
    }
  };

  settle(newGeneration, {
    status: "ready",
    items: [{ code: "new-run" }],
    error: "",
  });
  settle(oldGeneration, {
    status: "error",
    items: [{ code: "old-run" }],
    error: "old request failed",
  });
  assert.deepEqual(findingsState, {
    status: "ready",
    items: [{ code: "new-run" }],
    error: "",
  });

  const app = readFileSync(
    new URL("../../workbook-manager/frontend/src/App.jsx", import.meta.url),
    "utf8"
  );
  assert.match(app, /statusGenerationRef/);
  assert.match(app, /isCurrentGeneration/);
  assert.match(app, /refreshStatus\(report\)/);

  const changes = readFileSync(
    new URL(
      "../../workbook-manager/frontend/src/components/ChangesSync.jsx",
      import.meta.url
    ),
    "utf8"
  );
  assert.ok(
    changes.indexOf("onImportComplete(completedImport)")
      < changes.indexOf('api.changes("staged")'),
    "a completed import must invalidate older status work before another await",
  );
});
