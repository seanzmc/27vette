import test from "node:test";
import assert from "node:assert/strict";

import {
  blockingFindings,
  findingViewModel,
  tableViewModel,
} from "../../workbook-manager/frontend/src/tableRegistry.js";
import { api } from "../../workbook-manager/frontend/src/api.js";

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
      table: "options",
      model_id: "stingray",
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
