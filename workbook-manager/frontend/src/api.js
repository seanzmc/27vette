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
  runtime: (model) =>
    request(`/api/models/${encodeURIComponent(model)}/runtime`),
  variants: (model) =>
    request(`/api/models/${encodeURIComponent(model)}/variants`),
  tables: (model) =>
    request(`/api/models/${encodeURIComponent(model)}/tables`),
  schema: (role, model) => request(
    `/api/models/${encodeURIComponent(model)}/tables/${encodeURIComponent(role)}/schema`
  ),
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
  stage: (payload) => request("/api/changes", {
    method: "POST",
    body: JSON.stringify(payload),
  }),
  changes: (status = "staged") => request(`/api/changes?status=${status}`),
  discard: (id) => request(`/api/changes/${id}`, { method: "DELETE" }),
  validateChanges: () => request("/api/changes/validate", { method: "POST" }),
  commit: (actor = "") =>
    request("/api/changes/commit", {
      method: "POST",
      body: JSON.stringify({ actor }),
    }),
  history: (params = {}) => {
    const q = new URLSearchParams(params).toString();
    return request(`/api/history?${q}`);
  },
  sync: (payload) =>
    request("/api/sync", { method: "POST", body: JSON.stringify(payload) }),
  exportWorkbook: () => request("/api/export", { method: "POST" }),
  backup: () => request("/api/backup", { method: "POST" }),
};
