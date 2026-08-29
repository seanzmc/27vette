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

function draftQuery(draftId) {
  return draftId ? `?draft_id=${encodeURIComponent(draftId)}` : "";
}

export const api = {
  status: () => request("/api/status"),
  runImport: () => request("/api/import", { method: "POST" }),
  latestImport: () => request("/api/import/latest"),
  models: () => request("/api/models"),
  structure: (model, draftId = "") =>
    request(`/api/structure/${encodeURIComponent(model)}${draftQuery(draftId)}`),
  structureFamilies: (model) =>
    request(`/api/tables?model=${encodeURIComponent(model)}`),
  collections: (model) => request(`/api/models/${model}/collections`),
  connectedOption: (model, optionId, draftId = "") =>
    request(`/api/explorer/${encodeURIComponent(model)}/options/${encodeURIComponent(optionId)}${draftQuery(draftId)}`),
  connectedGroup: (model, groupType, groupId, draftId = "") =>
    request(`/api/explorer/${encodeURIComponent(model)}/groups/${encodeURIComponent(groupType)}/${encodeURIComponent(groupId)}${draftQuery(draftId)}`),
  connectedSection: (model, sectionId) =>
    request(`/api/explorer/${encodeURIComponent(model)}/sections/${encodeURIComponent(sectionId)}`),
  connectedRule: (model, ruleId) =>
    request(`/api/explorer/${encodeURIComponent(model)}/rules/${encodeURIComponent(ruleId)}`),
  explorerSearch: (model, query, limit = 40) =>
    request(`/api/explorer/${encodeURIComponent(model)}/search?query=${encodeURIComponent(query)}&limit=${limit}`),
  explorerDiagnostics: (model) =>
    request(`/api/explorer/${encodeURIComponent(model)}/diagnostics`),
  explorerDiagnostic: (model, key, { entityId = "", limit = 100 } = {}) =>
    request(`/api/explorer/${encodeURIComponent(model)}/diagnostics/${encodeURIComponent(key)}?entity_id=${encodeURIComponent(entityId)}&limit=${limit}`),
  assetReconciliation: (params = {}) => {
    const q = new URLSearchParams();
    Object.entries(params).forEach(([key, value]) => {
      if (value !== "" && value !== false && value != null) q.set(key, value);
    });
    return request(`/api/assets/reconciliation?${q.toString()}`);
  },
  assetMediaOptions: (query = "", limit = 50) =>
    request(`/api/assets/media-options?query=${encodeURIComponent(query)}&limit=${limit}`),
  schema: (table, model = "") =>
    request(`/api/records/${table}/schema?model=${encodeURIComponent(model)}`),
  referenceOptions: (
    table,
    field,
    { model = "", query = "", discriminator = "", limit = 25, offset = 0 } = {}
  ) => {
    const params = new URLSearchParams({
      field, model, query, discriminator, limit: String(limit), offset: String(offset),
    });
    return request(`/api/records/${table}/reference-options?${params.toString()}`);
  },
  records: (table, { model = "", search = "", limit = 200, offset = 0 } = {}) =>
    request(
      `/api/records/${table}?model=${encodeURIComponent(model)}&search=${encodeURIComponent(search)}&limit=${limit}&offset=${offset}`
    ),
  dependencies: (table, modelId, key) =>
    request(`/api/records/${table}/dependencies`, {
      method: "POST",
      body: JSON.stringify({ model_id: modelId, key }),
    }),
  drafts: (limit = 50) => request(`/api/drafts?limit=${limit}`),
  draftLifecycle: (draftId) => request(`/api/drafts/${draftId}`),
  draftOperations: (draftId) =>
    request(`/api/drafts/${draftId}/operations`),
  saveDraftOperation: (draftId, payload) =>
    request(`/api/drafts/${draftId}/operations`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  saveAssetResolution: (draftId, payload) =>
    request(`/api/drafts/${draftId}/asset-resolutions`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  saveAllSafeAssetResolutions: (draftId, payload) =>
    request(`/api/drafts/${draftId}/asset-resolutions/safe`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  commitDraft: (draftId) =>
    request(`/api/drafts/${draftId}/commit`, { method: "POST" }),
  previewDraft: (draftId) =>
    request(`/api/drafts/${draftId}/preview`, { method: "POST" }),
  approveDraft: (draftId, payload) =>
    request(`/api/drafts/${draftId}/approve`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  applyRebuildDraft: (draftId, payload) =>
    request(`/api/drafts/${draftId}/apply-rebuild`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  cancelDraft: (draftId) =>
    request(`/api/drafts/${draftId}/cancel`, { method: "POST" }),
  resolveUnknownDraft: (draftId, payload) =>
    request(`/api/drafts/${draftId}/resolve-unknown`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  workflowHistory: (params = {}) => {
    const q = new URLSearchParams(params).toString();
    return request(`/api/workflow-history?${q}`);
  },
  history: (params = {}) => {
    const q = new URLSearchParams(params).toString();
    return request(`/api/history?${q}`);
  },
  exportWorkbook: () => request("/api/export", { method: "POST" }),
  backup: () => request("/api/backup", { method: "POST" }),
};
