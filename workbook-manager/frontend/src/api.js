// Thin fetch wrapper for the workbook manager API.
async function request(path, options = {}) {
  const resp = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  let body = null;
  try {
    body = await resp.json();
  } catch {
    body = null;
  }
  if (!resp.ok) {
    if (
      Array.isArray(body?.detail?.findings)
      && typeof window !== "undefined"
      && typeof CustomEvent !== "undefined"
    ) {
      window.dispatchEvent(new CustomEvent("wbm:import-findings", {
        detail: {
          status: body.detail.status,
          findings: body.detail.findings,
        },
      }));
    }
    const err = new Error(
      body?.detail?.errors?.map((e) => e.message).join("; ") ||
        (typeof body?.detail === "string" ? body.detail : resp.statusText)
    );
    err.status = resp.status;
    err.detail = body?.detail;
    throw err;
  }
  return body;
}

export const api = {
  status: () => request("/api/status"),
  runImport: async (workbookPath) => {
    const resolvedPath = workbookPath || (
      await request("/api/status")
    ).workbook?.workbook_path;
    if (!resolvedPath) {
      throw new Error("Backend did not report a workbook path.");
    }
    return request("/api/imports", {
      method: "POST",
      body: JSON.stringify({ workbook_path: resolvedPath }),
    });
  },
  importRun: (importRunId) => request(`/api/imports/${importRunId}`),
  findings: (importRunId) => request(`/api/imports/${importRunId}/findings`),
  models: () => request("/api/models"),
  structure: async (model) => {
    const key = encodeURIComponent(model);
    const [runtime, variants] = await Promise.all([
      request(`/api/models/${key}/runtime`),
      request(`/api/models/${key}/variants`),
    ]);
    const presentations = runtime.section_presentation.map((section) => ({
      ...section,
      display_name: section.display_label,
      active: section.active ? "True" : "False",
    }));
    return {
      ...runtime,
      steps: runtime.steps.map((step) => ({
        ...step,
        display_name: step.step_label,
        active: step.active ? "True" : "False",
        sections: presentations.filter(
          (section) => section.step_key === step.step_key
        ),
      })),
      section_presentation: presentations,
      variants: variants.variants.map((variant) => ({
        ...variant,
        active: variant.active ? "True" : "False",
      })),
    };
  },
  tables: (model) =>
    request(`/api/models/${encodeURIComponent(model)}/tables`),
  schema: (role, model) => {
    const canonicalRole = role === "form_steps" ? "runtime_steps" : role;
    return request(
      `/api/models/${encodeURIComponent(model)}/tables/${encodeURIComponent(canonicalRole)}/schema`
    );
  },
  records: (role, { model, search = "", limit = 200, offset = 0 } = {}) =>
    request(
      `/api/models/${encodeURIComponent(model)}/tables/${encodeURIComponent(role)}`
      + `?search=${encodeURIComponent(search)}&limit=${limit}&offset=${offset}`
    ),
  dependencies: (role, modelKey, key) =>
    request(`/api/models/${encodeURIComponent(modelKey)}/tables/${encodeURIComponent(role)}/dependencies`, {
      method: "POST",
      body: JSON.stringify({ key }),
    }),
  stage: (payload) => {
    const tableRole = payload.table_role
      || (payload.table === "form_steps" ? "runtime_steps" : payload.table);
    const modelKey = payload.model_key || payload.model_id
      || payload.key?.model_key || payload.record?.model_key;
    return request("/api/changes", {
      method: "POST",
      body: JSON.stringify({
        model_key: modelKey,
        table_role: tableRole,
        op: payload.op,
        key: payload.key,
        record: payload.record,
        ...(payload.session_id ? { session_id: payload.session_id } : {}),
        ...(payload.confirm_dependencies
          ? { confirm_dependencies: payload.confirm_dependencies }
          : {}),
      }),
    });
  },
  changes: (status = "staged") => request(`/api/changes?status=${status}`),
  discard: (id) => request(`/api/changes/${id}`, { method: "DELETE" }),
  validateChanges: () => request("/api/changes/validate", { method: "POST" }),
  commit: (actor = "") =>
    request("/api/changes/commit", {
      method: "POST",
      body: JSON.stringify({ actor }),
    }),
  history: (params = {}) => {
    const normalized = { ...params };
    if ("model" in normalized) {
      normalized.model_key = normalized.model;
      delete normalized.model;
    }
    if ("table" in normalized) {
      normalized.table_role = normalized.table;
      delete normalized.table;
    }
    const q = new URLSearchParams(normalized).toString();
    return request(`/api/history?${q}`);
  },
  sync: (payload) =>
    request("/api/sync", { method: "POST", body: JSON.stringify(payload) }),
  exportWorkbook: () => request("/api/export", { method: "POST" }),
  backup: () => request("/api/backup", { method: "POST" }),
};
