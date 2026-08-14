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
    const err = new Error(
      body?.detail?.errors?.map((e) => e.message).join("; ") ||
        body?.detail?.message ||
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
  runImport: () => request("/api/import", { method: "POST" }),
  latestImport: () => request("/api/import/latest"),
  models: () => request("/api/models"),
  structure: (model) => request(`/api/structure/${model}`),
  collections: (model) => request(`/api/models/${model}/collections`),
  schema: (table, model = "") =>
    request(`/api/records/${table}/schema?model=${encodeURIComponent(model)}`),
  records: (table, { model = "", search = "", limit = 200, offset = 0 } = {}) =>
    request(
      `/api/records/${table}?model=${encodeURIComponent(model)}&search=${encodeURIComponent(search)}&limit=${limit}&offset=${offset}`
    ),
  dependencies: (table, modelId, key) =>
    request(`/api/records/${table}/dependencies`, {
      method: "POST",
      body: JSON.stringify({ model_id: modelId, key }),
    }),
  draftLifecycle: (draftId) => request(`/api/drafts/${draftId}`),
  saveDraftOperation: (draftId, payload) =>
    request(`/api/drafts/${draftId}/operations`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  stage: (payload) =>
    request("/api/changes", { method: "POST", body: JSON.stringify(payload) }),
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
