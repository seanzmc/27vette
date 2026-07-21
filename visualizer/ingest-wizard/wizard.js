/* Ingest Wizard Pass A — read-only browser flow over the wizard JSON API. */
"use strict";

const state = {
  files: [],
  selectedFile: null,
  session: null,
  profile: null,
  roles: {},
  joinReport: null,
  candidatesPayload: null,
  expanded: new Set(),
};

const $ = (selector) => document.querySelector(selector);

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function fmtPrice(value) {
  return "$" + Number(value).toLocaleString("en-US", { maximumFractionDigits: 2 });
}

async function getJSON(path) {
  const response = await fetch(path);
  const payload = await response.json();
  if (!response.ok) throw new Error(payload.error || response.statusText);
  return payload;
}

async function postJSON(path, body) {
  const response = await fetch(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body ?? {}),
  });
  const payload = await response.json();
  if (!response.ok) throw new Error(payload.error || response.statusText);
  return payload;
}

function showError(message) {
  const banner = $("#error-banner");
  banner.textContent = message;
  banner.classList.remove("hidden");
}

function clearError() {
  $("#error-banner").classList.add("hidden");
}

const STAGES = ["files", "sheets", "candidates", "models", "compile", "exceptions", "changeset"];

function setStage(stage) {
  clearError();
  for (const name of STAGES) {
    $(`#stage-${name}`).classList.toggle("hidden", name !== stage);
  }
  const reached = STAGES.indexOf(stage);
  document.querySelectorAll("#stepper .step").forEach((el, index) => {
    el.classList.toggle("active", index === reached);
    el.classList.toggle("done", index < reached);
    if (index === reached) el.setAttribute("aria-current", "step");
    else el.removeAttribute("aria-current");
  });
  $("#run-info").textContent = state.session
    ? `${state.session.sourceFile} · run ${state.session.runId}`
    : "";
}

/* ------------------------------------------------------------ stage: files */

async function loadFiles() {
  const payload = await getJSON("/api/wizard/files");
  state.files = payload.files;
  renderFiles();
  await loadSessions();
}

async function loadSessions() {
  const payload = await getJSON("/api/wizard/sessions");
  const sessions = payload.sessions || [];
  $("#run-list").innerHTML = sessions.length
    ? sessions
        .slice(0, 12)
        .map(
          (session) => `<div class="file-row">
            <div><b>${escapeHtml(session.sourceFile)}</b><div class="cell-sub">${escapeHtml(session.runId)} · ${escapeHtml(session.state)}</div></div>
            <button class="primary resume-run" data-run-id="${escapeHtml(session.runId)}">Resume</button>
          </div>`
        )
        .join("")
    : '<div class="empty-note">No saved runs yet.</div>';
}

async function resumeSession(runId) {
  clearError();
  const detail = await getJSON(`/api/wizard/sessions/${runId}`);
  state.session = detail.session;
  state.profile = detail.profile;
  state.roles = detail.roles || {};
  state.joinReport = detail.joinReport;
  state.selectedFile = detail.session.sourceFile;
  if (!Object.keys(state.roles).length) {
    for (const card of state.profile.sheets) state.roles[card.sheetName] = card.recommendedRole;
  }
  compilerState.summary = null;
  const prepareModels = async () => {
    await loadModels();
    modelState.targets = new Set((detail.modelSelection || {}).targets || []);
    modelState.comparators = { ...((detail.modelSelection || {}).comparators || {}) };
  };
  switch (detail.session.state) {
    case "profiled":
      $("#run-parse-btn").classList.add("hidden");
      renderSheets();
      setStage("sheets");
      break;
    case "roles_confirmed":
      renderSheets();
      $("#roles-status").textContent = "Roles confirmed — ready to parse.";
      $("#run-parse-btn").classList.remove("hidden");
      setStage("sheets");
      break;
    case "parsed":
      populateSheetFilter();
      await loadCandidates();
      setStage("candidates");
      break;
    case "models_selected":
      await prepareModels();
      await enterCompile();
      break;
    case "compiled_ready":
      await prepareModels();
      await enterCompile();
      break;
    case "changeset_emitted": {
      const changeset = await getJSON(`/api/wizard/sessions/${runId}/changeset`);
      renderChangeSet(changeset);
      setStage("changeset");
      break;
    }
    case "compiled_with_exceptions":
      await prepareModels();
      await enterExceptions();
      break;

    default:
      throw new Error(`Run state ${detail.session.state} has no safe browser resume route.`);
  }
}

$("#run-list").addEventListener("click", (event) => {
  const button = event.target.closest(".resume-run");
  if (!button) return;
  button.disabled = true;
  resumeSession(button.dataset.runId).catch((error) => {
    button.disabled = false;
    showError(error.message);
  });
});

function renderFiles() {
  const list = $("#file-list");
  if (!state.files.length) {
    list.innerHTML = '<div class="empty-note">No .xlsx files found. Upload a raw order-guide export.</div>';
  } else {
    list.innerHTML = state.files
      .map(
        (file) => `
        <button type="button" class="file-row file-choice ${state.selectedFile === file.name ? "selected" : ""}" data-file="${escapeHtml(file.name)}" aria-pressed="${state.selectedFile === file.name}">
          <span class="file-name">${escapeHtml(file.name)}</span>
          <span class="badge">${escapeHtml(file.origin)}</span>
          <span class="file-meta">${(file.sizeBytes / 1024).toFixed(0)} KB</span>
        </button>`
      )
      .join("");
  }
  $("#profile-btn").disabled = !state.selectedFile;
}

$("#file-list").addEventListener("click", (event) => {
  const row = event.target.closest(".file-row");
  if (!row) return;
  state.selectedFile = row.dataset.file;
  renderFiles();
});

$("#upload-input").addEventListener("change", async (event) => {
  const file = event.target.files[0];
  if (!file) return;
  clearError();
  try {
    const body = await file.arrayBuffer();
    const response = await fetch(
      `/api/wizard/upload?filename=${encodeURIComponent(file.name)}`,
      { method: "POST", body }
    );
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.error || response.statusText);
    state.selectedFile = payload.file.name;
    await loadFiles();
  } catch (error) {
    showError(`Upload failed: ${error.message}`);
  } finally {
    event.target.value = "";
  }
});

$("#profile-btn").addEventListener("click", async () => {
  if (!state.selectedFile) return;
  clearError();
  const button = $("#profile-btn");
  button.disabled = true;
  button.textContent = "Profiling…";
  try {
    const payload = await postJSON("/api/wizard/sessions", { file: state.selectedFile });
    state.session = payload.session;
    state.profile = payload.profile;
    state.roles = {};
    for (const card of state.profile.sheets) state.roles[card.sheetName] = card.recommendedRole;
    $("#run-parse-btn").classList.add("hidden");
    $("#roles-status").textContent = "";
    renderSheets();
    setStage("sheets");
  } catch (error) {
    showError(error.message);
  } finally {
    button.disabled = false;
    button.textContent = "Profile sheets";
  }
});

/* ----------------------------------------------------------- stage: sheets */

const TYPE_LABELS = {
  options_matrix: ["Options matrix", "type-options"],
  price_sheet: ["Price sheet", "type-price"],
  unsupported: ["Unsupported", "type-unsupported"],
};

function familyLabel(card) {
  if (card.modelFamily === "mixed") return `Mixed (${card.modelFamilies.join(" + ")})`;
  if (card.modelFamily === "all") return "All models";
  return card.modelFamily;
}

function cardStats(card) {
  const stats = card.rowStats || {};
  if (card.sheetType === "price_sheet") {
    return `${stats.optionPriceRows ?? 0} option price rows · ${stats.baseModelRows ?? 0} base-model rows`;
  }
  if (card.sheetType === "options_matrix") {
    return `${stats.orderableRpoRows ?? 0} orderable options · ${stats.refOnlyRpoRows ?? 0} ref-only rows · ${card.variantColumns.length} variant columns`;
  }
  return "Layout not recognized";
}

function renderSheets() {
  $("#sheet-cards").innerHTML = state.profile.sheets
    .map((card) => {
      const [typeLabel, typeClass] = TYPE_LABELS[card.sheetType] || TYPE_LABELS.unsupported;
      const role = state.roles[card.sheetName];
      const roleButton = (value, label) => {
        const allowed =
          value === "exclude" ||
          (value === "options" && card.sheetType === "options_matrix" && card.canonicalOptionSource === true) ||
          (value === "price" && card.sheetType === "price_sheet");
        return `<button class="role-btn ${role === value ? "active" : ""}" data-sheet="${escapeHtml(card.sheetName)}" data-role="${value}" ${allowed ? "" : "disabled"}>${label}</button>`;
      };
      const subtypeNote =
        card.sheetType === "options_matrix" && card.canonicalOptionSource !== true
          ? '<div class="card-note">Excluded from canonical processing — use Interior, Exterior, or Mechanical sheets</div>'
          : card.contentSubtype === "standard_equipment"
          ? '<div class="card-note">Standard-equipment content — excluded by default</div>'
          : "";
      const reasons = card.confidenceReasons.length
        ? `<ul class="reasons">${card.confidenceReasons.map((reason) => `<li>${escapeHtml(reason)}</li>`).join("")}</ul>`
        : "";
      const variants = card.variantColumns
        .map((column) => `<span class="vchip">${escapeHtml(column.label)} ${escapeHtml(column.modelCode)} ${escapeHtml(column.trim)}</span>`)
        .join("");
      return `
      <div class="card">
        <div class="card-head">
          <span class="card-title">${escapeHtml(card.sheetName)}</span>
          <span class="type-badge ${typeClass}">${typeLabel}</span>
          <span class="conf conf-${card.confidence}">${card.confidence} confidence</span>
        </div>
        <div><span class="family-chip">${escapeHtml(familyLabel(card))}</span></div>
        <div class="card-stats">${cardStats(card)}</div>
        ${subtypeNote}
        ${variants ? `<div class="variant-chips">${variants}</div>` : ""}
        ${reasons}
        <div class="role-seg">
          ${roleButton("options", "Options")}
          ${roleButton("price", "Price")}
          ${roleButton("exclude", "Exclude")}
        </div>
      </div>`;
    })
    .join("");
}

$("#sheet-cards").addEventListener("click", (event) => {
  const button = event.target.closest(".role-btn");
  if (!button || button.disabled) return;
  state.roles[button.dataset.sheet] = button.dataset.role;
  $("#run-parse-btn").classList.add("hidden");
  $("#roles-status").textContent = "";
  renderSheets();
});

$("#confirm-roles-btn").addEventListener("click", async () => {
  clearError();
  try {
    const payload = await postJSON(`/api/wizard/sessions/${state.session.runId}/roles`, {
      roles: state.roles,
    });
    state.session = payload.session;
    $("#roles-status").textContent = "Roles confirmed — ready to parse.";
    $("#run-parse-btn").classList.remove("hidden");
  } catch (error) {
    showError(error.message);
  }
});

$("#run-parse-btn").addEventListener("click", async () => {
  clearError();
  const button = $("#run-parse-btn");
  button.disabled = true;
  button.textContent = "Parsing…";
  try {
    const payload = await postJSON(`/api/wizard/sessions/${state.session.runId}/parse`, {});
    state.session = payload.session;
    state.joinReport = payload.joinReport;
    populateSheetFilter();
    await loadCandidates();
    setStage("candidates");
  } catch (error) {
    showError(error.message);
  } finally {
    button.disabled = false;
    button.textContent = "Run first parse";
  }
});

/* ------------------------------------------------------- stage: candidates */

function populateSheetFilter() {
  const select = $("#filter-sheet");
  const optionSheets = Object.entries(state.roles)
    .filter(([, role]) => role === "options")
    .map(([sheet]) => sheet);
  select.innerHTML =
    '<option value="">All sheets</option>' +
    optionSheets.map((sheet) => `<option value="${escapeHtml(sheet)}">${escapeHtml(sheet)}</option>`).join("");
}

async function loadCandidates() {
  const params = new URLSearchParams();
  if ($("#filter-sheet").value) params.set("sheet", $("#filter-sheet").value);
  if ($("#filter-price").value) params.set("priceMatch", $("#filter-price").value);
  if ($("#filter-q").value.trim()) params.set("q", $("#filter-q").value.trim());
  const query = params.toString() ? `?${params.toString()}` : "";
  state.candidatesPayload = await getJSON(
    `/api/wizard/sessions/${state.session.runId}/candidates${query}`
  );
  state.expanded = new Set();
  renderSummary();
  renderCandidates();
}

function renderSummary() {
  const report = state.joinReport || {};
  const payload = state.candidatesPayload;
  const skippedCount = Object.values(payload.skippedRows || {}).reduce(
    (total, rows) => total + rows.length,
    0
  );
  $("#summary-chips").innerHTML = `
    <span class="sum-chip"><b>${payload.total}</b> candidates</span>
    <span class="sum-chip sum-exact"><b>${report.exactMatches ?? 0}</b> exact price matches</span>
    <span class="sum-chip sum-ambiguous"><b>${report.ambiguousMatches ?? 0}</b> ambiguous prices</span>
    <span class="sum-chip sum-none"><b>${report.missingPrices ?? 0}</b> without price</span>
    <span class="sum-chip sum-warn"><b>${(payload.unmatchedPriceRows || []).length}</b> unmatched price rows</span>
    <span class="sum-chip"><b>${skippedCount}</b> skipped rows</span>`;
}

function priceBadge(candidate) {
  if (candidate.priceMatch === "exact")
    return `<span class="price-badge pm-exact">${fmtPrice(candidate.listPrice)}</span>`;
  if (candidate.priceMatch === "ambiguous")
    return `<span class="price-badge pm-ambiguous">${candidate.priceRows.length} prices</span>`;
  if (candidate.priceMatch === "none")
    return '<span class="price-badge pm-none">no price</span>';
  return '<span class="pm-null">—</span>';
}

function statusChips(candidate) {
  return candidate.statuses
    .map(
      (status) =>
        `<span class="stchip st-${escapeHtml(status.status)}" title="${escapeHtml(
          `${status.variantLabel} ${status.modelCode} ${status.trim}: ${status.status}`
        )}">${escapeHtml(status.raw)}</span>`
    )
    .join("");
}

function evidenceBlock(candidate) {
  const cells = Object.entries(candidate.sourceEvidence.cells)
    .map(
      ([coord, value]) =>
        `<tr><td class="coord">${escapeHtml(coord)}</td><td>${escapeHtml(value)}</td></tr>`
    )
    .join("");
  const prices = (candidate.priceRows || [])
    .map(
      (row) =>
        `<tr><td class="coord">${escapeHtml(row.sourceEvidence ? `row ${row.sourceEvidence.rowIndex}` : "")}</td>` +
        `<td>${fmtPrice(row.listPrice)}${row.qualifier ? ` — ${escapeHtml(row.qualifier)}` : ""}</td></tr>`
    )
    .join("");
  return `
    <div class="evidence">
      <div>
        <h4>Source cells — ${escapeHtml(candidate.sourceEvidence.sheetName)} row ${candidate.sourceEvidence.rowIndex}</h4>
        <table>${cells}</table>
      </div>
      ${prices ? `<div><h4>Joined price rows</h4><table>${prices}</table></div>` : ""}
    </div>`;
}

function renderCandidates() {
  const payload = state.candidatesPayload;
  if (!payload.candidates.length) {
    $("#candidate-table").innerHTML = '<div class="empty-note">No candidates match the current filters.</div>';
    return;
  }
  const rows = payload.candidates
    .map((candidate) => {
      const expanded = state.expanded.has(candidate.candidateId);
      return `
      <tr class="cand-row">
        <td><button class="expand-btn" data-id="${escapeHtml(candidate.candidateId)}">${expanded ? "−" : "+"}</button></td>
        <td class="rpo">${escapeHtml(candidate.rpo) || `<span class="ref-rpo">${escapeHtml(candidate.refOnlyRpo)}</span>`}</td>
        <td class="desc">${escapeHtml(candidate.description)}
          <div class="cell-sub">${escapeHtml(candidate.sectionLabel)}</div></td>
        <td>${escapeHtml(candidate.modelFamily === "mixed" ? candidate.modelFamilies.join(" + ") : candidate.modelFamily)}
          <div class="cell-sub">${escapeHtml(candidate.sheetName)} · row ${candidate.rowIndex}</div></td>
        <td>${escapeHtml(candidate.rowKind === "orderable" ? "orderable" : "ref-only")}</td>
        <td><div class="stchips">${statusChips(candidate)}</div></td>
        <td>${priceBadge(candidate)}</td>
      </tr>
      ${expanded ? `<tr class="evidence-row"><td colspan="7">${evidenceBlock(candidate)}</td></tr>` : ""}`;
    })
    .join("");
  $("#candidate-table").innerHTML = `
    <table class="cand">
      <thead><tr>
        <th></th><th>RPO</th><th>Description</th><th>Model / sheet</th>
        <th>Kind</th><th>Variant statuses</th><th>Price</th>
      </tr></thead>
      <tbody>${rows}</tbody>
    </table>`;
}

$("#candidate-table").addEventListener("click", (event) => {
  const button = event.target.closest(".expand-btn");
  if (!button) return;
  const id = button.dataset.id;
  if (state.expanded.has(id)) state.expanded.delete(id);
  else state.expanded.add(id);
  renderCandidates();
});

for (const id of ["#filter-sheet", "#filter-price"]) {
  $(id).addEventListener("change", () => loadCandidates().catch((error) => showError(error.message)));
}
let searchTimer = null;
$("#filter-q").addEventListener("input", () => {
  clearTimeout(searchTimer);
  searchTimer = setTimeout(
    () => loadCandidates().catch((error) => showError(error.message)),
    250
  );
});

$("#back-to-sheets").addEventListener("click", () => setStage("sheets"));

/* ---------------------------------------------------- stage: model select */

const modelState = {
  options: [],
  targets: new Set(),
  comparators: {},
  selection: null,
  reconciliation: null,
};

async function loadModels() {
  const payload = await getJSON(`/api/wizard/sessions/${state.session.runId}/models`);
  modelState.options = payload.models;
  modelState.selection = payload.selection;
  modelState.targets = new Set(
    payload.selection ? payload.selection.targets : payload.models.filter((m) => m.isDefaultTarget).map((m) => m.modelKey)
  );
  modelState.comparators = {};
  for (const model of payload.models) {
    if (payload.selection && payload.selection.comparators[model.modelKey] !== undefined) {
      modelState.comparators[model.modelKey] = payload.selection.comparators[model.modelKey];
    } else if (model.comparatorDefault) {
      modelState.comparators[model.modelKey] = model.comparatorDefault;
    }
  }
  renderModels();
}

function renderModels() {
  const comparatorChoices = modelState.options.filter((m) => !m.isDefaultTarget);
  $("#model-cards").innerHTML = modelState.options
    .map((model) => {
      const isTarget = modelState.targets.has(model.modelKey);
      const comparator = modelState.comparators[model.modelKey] || "";
      const comparatorSelect = isTarget
        ? `<label class="cmp-label">Comparator model (corroborating context only)
            <select class="cmp-select" data-model="${escapeHtml(model.modelKey)}">
              <option value="">none</option>
              ${comparatorChoices
                .map(
                  (choice) =>
                    `<option value="${escapeHtml(choice.modelKey)}" ${choice.modelKey === comparator ? "selected" : ""}>${escapeHtml(choice.label)}</option>`
                )
                .join("")}
            </select></label>`
        : "";
      return `
      <div class="card ${isTarget ? "card-target" : ""}">
        <div class="card-head">
          <span class="card-title">${escapeHtml(model.label)}</span>
          ${model.isDefaultTarget ? '<span class="type-badge type-options">target model</span>' : '<span class="type-badge type-unsupported">live model</span>'}
        </div>
        <div class="card-stats">${model.candidateCount} candidates in scope</div>
        <div class="role-seg">
          <button class="role-btn ${isTarget ? "active" : ""}" data-target="${escapeHtml(model.modelKey)}">
            ${isTarget ? "Selected as target" : "Select as target"}
          </button>
        </div>
        ${comparatorSelect}
      </div>`;
    })
    .join("");
}

$("#model-cards").addEventListener("click", (event) => {
  const button = event.target.closest(".role-btn[data-target]");
  if (!button) return;
  const key = button.dataset.target;
  if (modelState.targets.has(key)) modelState.targets.delete(key);
  else modelState.targets.add(key);
  renderModels();
});

$("#model-cards").addEventListener("change", (event) => {
  const select = event.target.closest(".cmp-select");
  if (!select) return;
  modelState.comparators[select.dataset.model] = select.value;
});

$("#confirm-models-btn").addEventListener("click", async () => {
  clearError();
  try {
    const targets = [...modelState.targets];
    const comparators = {};
    for (const target of targets) {
      if (modelState.comparators[target]) comparators[target] = modelState.comparators[target];
    }
    const payload = await postJSON(`/api/wizard/sessions/${state.session.runId}/models`, {
      targets,
      comparators,
    });
    state.session = payload.session;
    modelState.selection = payload.selection;
    modelState.reconciliation = payload.reconciliation;
    $("#models-status").textContent = "Selection saved.";
    await enterCompile();
  } catch (error) {
    showError(error.message);
  }
});

/* -------------------------------------------------------- stage: compiler */

const compilerState = {
  summary: null,
};

function readinessLabel(value) {
  return value ? "ready" : "blocked";
}

function renderCompilerSummary(summary) {
  compilerState.summary = summary;
  state.session = summary.session;
  const manifest = summary.counts.manifest;
  const exceptions = summary.counts.exceptions;
  const actionCounts = Object.entries(manifest.byAction || {})
    .map(([action, count]) => `<span class="sum-chip"><b>${escapeHtml(count)}</b> ${escapeHtml(action)}</span>`)
    .join("");
  const modelCards = Object.entries(summary.models || {})
    .map(([model, entry]) => {
      const gates = ["compileReady"]
        .map(
          (gate) =>
            `<span class="gate-chip ${entry[gate] ? "gate-ready" : "gate-blocked"}"><b>${escapeHtml(gate)}</b> ${readinessLabel(entry[gate])}</span>`
        )
        .join("");
      return `<div class="card readiness-card">
        <div class="card-head"><span class="card-title">${escapeHtml(model)}</span><span class="type-badge">${escapeHtml(entry.mode || "target")}</span></div>
        <div class="gate-grid">${gates}</div>
        <div class="card-stats">${escapeHtml(entry.blockerCount)} blockers · ${escapeHtml(entry.deferralCount)} deferrals</div>
      </div>`;
    })
    .join("");
  $("#compile-summary").innerHTML = `
    <div class="summary">
      <span class="sum-chip"><b>${escapeHtml(manifest.total)}</b> proposed rows</span>
      ${actionCounts}
      <span class="sum-chip ${exceptions.byState.open ? "sum-warn" : "sum-exact"}"><b>${escapeHtml(exceptions.byState.open || 0)}</b> open exceptions</span>
      <span class="sum-chip"><b>${escapeHtml(exceptions.byState.resolved || 0)}</b> resolved</span>
      <span class="sum-chip ${exceptions.byState.resolved_pending_projection ? "sum-warn" : ""}"><b>${escapeHtml(exceptions.byState.resolved_pending_projection || 0)}</b> awaiting compiler projection</span>
      <span class="sum-chip"><b>${escapeHtml(exceptions.actionable || 0)}</b> reviewer-answerable</span>
    </div>
    <div class="cards">${modelCards}</div>`;
  $("#compile-btn").textContent = "Recompile canonical rows";
  const changeSetReady =
    summary.session.state === "compiled_ready" &&
    !summary.freshness.stale &&
    Object.values(summary.models || {}).every((entry) => entry.compileReady && !entry.blockerCount);
  $("#compile-changeset-btn").classList.toggle("hidden", !changeSetReady);
  $("#review-exceptions-btn").classList.toggle("hidden", !exceptions.total);
  $("#compile-status").textContent = summary.freshness.stale
    ? `Inputs changed after compile: ${summary.freshness.reasons.join("; ")}. Recompile required.`
    : `Compiler state: ${summary.session.state}. No workbook write performed.`;
}

async function enterCompile() {
  setStage("compile");
  if (state.session && ["compiled_ready", "compiled_with_exceptions"].includes(state.session.state)) {
    const summary = await getJSON(`/api/wizard/sessions/${state.session.runId}/compile`);
    renderCompilerSummary(summary);
  } else {
    compilerState.summary = null;
    $("#compile-summary").innerHTML = '<div class="empty-note">Model selection is saved. Compile to derive canonical rows and the exact exception queue.</div>';
    $("#compile-btn").textContent = "Compile canonical rows";
    $("#compile-changeset-btn").classList.add("hidden");
    $("#review-exceptions-btn").classList.add("hidden");
    $("#compile-status").textContent = "Inputs stay read-only.";
  }
}

async function runCompile() {
  clearError();
  const button = $("#compile-btn");
  button.disabled = true;
  button.textContent = "Compiling…";
  try {
    const summary = await postJSON(`/api/wizard/sessions/${state.session.runId}/compile`, {});
    renderCompilerSummary(summary);
  } catch (error) {
    showError(error.message);
  } finally {
    button.disabled = false;
    if (!compilerState.summary) button.textContent = "Compile canonical rows";
  }
}

$("#compile-btn").addEventListener("click", runCompile);
$("#review-exceptions-btn").addEventListener("click", enterExceptions);
$("#compile-back-models").addEventListener("click", async () => {
  await loadModels();
  setStage("models");
});

/* ------------------------------------------------------- stage: exceptions */

const exceptionState = {
  payload: null,
  offset: 0,
  limit: 20,
  expandedSubjectId: null,
  pendingFocusSubjectId: null,
};

function optionSelect(name, options, placeholder) {
  return `<select name="${escapeHtml(name)}" required>
    <option value="">${escapeHtml(placeholder)}</option>
    ${(options || [])
      .map(
        (option) =>
          `<option value="${escapeHtml(option.optionId)}">${escapeHtml(option.rpo || "—")} · ${escapeHtml(option.name || option.optionId)} · ${escapeHtml(option.optionId)}</option>`
      )
      .join("")}
  </select>`;
}

function exceptionActionFields(item, action) {
  const subject = item.subject;
  const choices = item.choices || {};
  switch (action) {
    case "choose_section":
      return `<label>Canonical section
        <select name="sectionId" required><option value="">Choose one workbook section</option>
          ${(choices.sections || []).map((section) => `<option value="${escapeHtml(section.sectionId)}">${escapeHtml(section.sectionName)} · ${escapeHtml(section.sectionId)}</option>`).join("")}
        </select></label>`;
    case "keep_inactive_option":
      return `<label>Canonical section
        <select name="sectionId" required><option value="">Choose one workbook section</option>
          ${(choices.sections || []).map((section) => `<option value="${escapeHtml(section.sectionId)}">${escapeHtml(section.sectionName)} · ${escapeHtml(section.sectionId)}</option>`).join("")}
        </select></label><div class="status-note">Keep this option as inactive, nonselectable, and unpriced.</div>`;
    case "choose_relationship":
      return `<div class="typed-grid">
        <label>Source option ${optionSelect("sourceOptionId", choices.targetOptions, "Choose exact source option")}</label>
        <label>Relationship <select name="ruleType" required><option value="">Choose rule type</option>${(choices.relationshipRuleTypes || []).map((value) => `<option value="${escapeHtml(value)}">${escapeHtml(value)}</option>`).join("")}</select></label>
        <label>Target option ${optionSelect("targetOptionId", choices.targetOptions, "Choose exact target option")}</label>
      </div>`;
    case "retain_existing":
      return `<label>Established target occurrence ${optionSelect("existingId", choices.existingOptions, "Choose existing target ID")}</label>`;
    case "provide_option_copy": {
      const proposal = (subject.proposedRows || [])[0] || {};
      return `<div class="typed-grid copy-evidence-field">
        <label>Customer option name <textarea name="optionName" required>${escapeHtml(proposal.proposedOptionName || "")}</textarea></label>
        <label>Customer description <textarea name="description">${escapeHtml(proposal.proposedDescription || "")}</textarea></label>
      </div>`;
    }
    case "provide_option_behavior":
      return `<div class="typed-grid">
        <label>Active <select name="active" required><option value="true">Active</option><option value="false">Inactive</option></select></label>
        <label>Selectable <select name="selectable" required><option value="true">Selectable</option><option value="false">Not selectable</option></select></label>
      </div>`;
    case "confirm_mandatory_charge": {
      const proposal = (subject.proposedRows || [])[0] || {};
      return `<label>Confirmed whole-dollar mandatory charge <input name="priceValue" type="number" min="1" step="1" value="${escapeHtml(proposal.sourcePrice || "")}" required></label>`;
    }
    case "provide_typed_value":
      if (subject.reasonCode === "comparator_only_rule_group_proposal") {
        return '<input type="hidden" name="decision" value="confirm_proposal"><div class="status-note">Confirm the exact comparator-backed proposal shown above for this target.</div>';
      }
      if (subject.reasonCode === "comparator_only_exclusive_group_proposal") {
        return `<input type="hidden" name="decision" value="confirm_proposal"><label>Target selection behavior
          <select name="selectionMode" required><option value="">Choose target behavior</option>${(choices.exclusiveSelectionModes || []).map((value) => `<option value="${escapeHtml(value)}">${escapeHtml(value.replaceAll("_", " "))}</option>`).join("")}</select>
        </label>`;
      }
      if (subject.reasonCode === "comparator_only_default_selection_proposal") {
        return `<input type="hidden" name="decision" value="confirm_proposal"><div class="typed-grid">
          <label>Target priority <input name="priority" type="number" min="0" step="1" required></label>
          <label>Target display behavior <select name="defaultDisplayBehavior" required>
            <option value="">Choose target display behavior</option>
            <option value="default_selected">Default selected</option>
            <option value="__blank__">Normal display</option>
          </select></label>
        </div>`;
      }
      return `<div class="typed-grid">
        ${subject.reasonCode === "comparator_only_price_rule_proposal" ? '<input type="hidden" name="decision" value="confirm_proposal">' : ""}
        <label>Target price scope <select name="priceScope" required>
          <option value="">Choose one target variant scope</option>
          ${(choices.priceScopes || []).map((scope) => `<option value="${escapeHtml(JSON.stringify({ bodyStyleScope: scope.bodyStyleScope, trimLevelScope: scope.trimLevelScope, variantScope: scope.variantScope }))}">${escapeHtml(scope.label)}</option>`).join("")}
        </select></label>
        <label>Whole-dollar price <input name="priceValue" type="number" step="1" ${["unresolved_price_scope", "comparator_only_price_rule_proposal"].includes(subject.reasonCode) ? "required" : ""}></label>
      </div>`;
    case "approve_removal":
      return '<label>Why reference impact is cleared <input name="reason" required></label>';
    case "mark_not_applicable":
      if (subject.reasonCode === "missing_section") {
        return '<fieldset class="proposal-rejection"><legend>Omit this source option</legend><label><input type="checkbox" name="rejectWholeProposal" required> I understand this option and its generated rows will be omitted from the target.</label><label>Audit reason <input name="reason" required></label></fieldset>';
      }
      return '<fieldset class="proposal-rejection"><legend>Reject entire proposal — write no rows</legend><div class="source-blocker">Do not use rejection for a partial disagreement. If one member, direction, scope, or field is wrong, leave this subject blocked.</div><label><input type="checkbox" name="rejectWholeProposal" required> I understand this rejects the complete proposal, not one member, direction, scope, or field.</label><label>Optional audit note <input name="reason" placeholder="Target evidence that rejects the complete proposal"></label></fieldset>';
    case "record_allowed_deferral":
      return `<div class="typed-grid"><label>Allowed deferral kind
        <select name="kind" required><option value="">Choose allowlisted kind</option>${(choices.deferralKinds || []).map((kind) => `<option value="${escapeHtml(kind)}">${escapeHtml(kind)}</option>`).join("")}</select>
        </label><label>Reason <input name="reason" required></label></div>`;
    default:
      return "";
  }
}

function actionLabel(action, reasonCode) {
  if (action === "provide_typed_value" && reasonCode.startsWith("comparator_only_")) {
    return "Confirm exact proposal";
  }
  return {
    choose_section: "Use this section",
    keep_inactive_option: "Keep inactive and unpriced",
    choose_relationship: "Save exact relationship",
    retain_existing: "Keep selected existing row",
    provide_option_copy: "Save reviewed copy",
    provide_option_behavior: "Save reviewed behavior",
    confirm_mandatory_charge: "Confirm mandatory charge",
    provide_typed_value: "Save typed value",
    approve_removal: "Approve exact removal",
    mark_not_applicable: "Reject entire proposal — write no rows",
    record_allowed_deferral: "Record allowed deferral",
  }[action] || action.replaceAll("_", " ");
}

function exceptionActionForm(item) {
  if (item.resolution) {
    const label = item.state === "resolved_pending_projection"
      ? "Answer saved — compiler projection still required"
      : "Resolved";
    return `<div class="exception-resolution"><b>${escapeHtml(label)}:</b> ${escapeHtml(item.resolution.action)} by ${escapeHtml(item.resolution.reviewer || "unknown reviewer")}
      <button class="ghost exception-reopen" data-subject-id="${escapeHtml(item.subject.subjectId)}" data-subject-version="${escapeHtml(item.subject.subjectVersion)}">Reopen</button></div>`;
  }
  const actions = item.availableActions || [];
  if (!actions.length) {
    const conflict = item.subject.semanticConflict || {};
    const prerequisites = item.prerequisites || {};
    const detail = conflict.overlapKind
      ? `Semantic conflict: ${conflict.overlapKind.replaceAll("_", " ")}. Affected sheets: ${(item.affectedSheets || []).join(", ") || "not yet projectable"}.`
      : prerequisites.message || "No complete workbook-writable answer is available from the current source and compiler.";
    return `<div class="source-blocker"><b>Blocked — no decision control is available.</b> ${escapeHtml(detail)}</div>`;
  }
  return `<form class="exception-resolution-form" data-action="" data-subject-id="${escapeHtml(item.subject.subjectId)}" data-subject-version="${escapeHtml(item.subject.subjectVersion)}" data-reason-code="${escapeHtml(item.subject.reasonCode)}">
    ${renderDecisionOutcomes(item)}
    <div class="conditional-action-fields"></div>
    <section class="decision-preview" aria-live="polite" hidden></section>
    <button class="primary decision-primary" type="submit" disabled>Preview effect</button>
  </form>`;
}

function renderDecisionOutcomes(item) {
  const actions = item.availableActions || [];
  return `<fieldset class="decision-outcomes"><legend>Choose one outcome</legend>
    ${actions.map((action) => `<label class="decision-outcome"><input type="radio" name="decisionAction" value="${escapeHtml(action)}"> <span>${escapeHtml(actionLabel(action, item.subject.reasonCode))}</span></label>`).join("")}
  </fieldset>`;
}

function sourceEvidenceView(candidate) {
  const evidence = candidate.sourceEvidence || {};
  const rawCells = evidence.cells || {};
  const normalizedCells = Array.isArray(rawCells)
    ? rawCells
    : Object.entries(rawCells).map(([coordinate, value]) => ({ coordinate, value }));
  const cells = normalizedCells
    .map((cell) => `<li><code>${escapeHtml(cell.coordinate || "cell")}</code> ${escapeHtml(cell.value)}</li>`)
    .join("");
  return `<div class="evidence-entry"><b>${escapeHtml(candidate.rpo || candidate.refOnlyRpo || "source row")}</b> — ${escapeHtml(candidate.description || "")}
    <div class="cell-sub">${escapeHtml(evidence.sheetName || candidate.sheetName || "source")} · ${escapeHtml(candidate.sectionLabel || "no source section")}</div>
    <ul class="evidence-cells">${cells}</ul></div>`;
}

function displayEvidenceValue(value) {
  if (value === "" || value === null || value === undefined) return "blank";
  return value && typeof value === "object" ? JSON.stringify(value) : value;
}

function evidenceValues(record, preferredKeys = []) {
  for (const key of preferredKeys) {
    const values = record[key];
    if (values && typeof values === "object" && Object.keys(values).length) return values;
  }
  return Object.fromEntries(
    Object.entries(record).filter(([key]) => !["evidenceId", "evidenceDependencies", "evidenceReferences", "proposedRows"].includes(key))
  );
}

function canonicalRowView(row) {
  const requiredConflictFields = new Set([
    "currentOptionName",
    "currentDescription",
    "proposedOptionName",
    "proposedDescription",
    "detailRaw",
    "comparator",
    "comparison",
    "behaviorEvidence",
    "placementEvidence",
    "priceEvidence",
  ]);
  const values = Object.entries(evidenceValues(row, ["values", "signature"]))
    .filter(([key, value]) => requiredConflictFields.has(key) || (value !== "" && value !== null && value !== undefined))
    .map(([key, value]) => `<span><b>${escapeHtml(key)}</b>: ${escapeHtml(displayEvidenceValue(value))}</span>`)
    .join("");
  const key = row.key && typeof row.key === "object" ? JSON.stringify(row.key) : "";
  return `<div class="evidence-entry"><b>${escapeHtml(row.sheet || row.family || "row")}</b> · ${escapeHtml(row.action || "proposal signature")}
    ${key ? `<div class="cell-sub">Key: ${escapeHtml(key)}</div>` : ""}
    <div class="row-values">${values || "No populated preview fields."}</div></div>`;
}

function comparatorEvidenceView(fact) {
  const values = evidenceValues(fact, ["values", "payload", "signature"]);
  return `<div class="evidence-entry"><b>${escapeHtml(fact.comparator || fact.model || "comparator")}</b> · ${escapeHtml(fact.kind || fact.family || "fact")}
    <div class="row-values">${Object.entries(values).map(([key, value]) => `<span><b>${escapeHtml(key)}</b>: ${escapeHtml(displayEvidenceValue(value))}</span>`).join("") || escapeHtml(fact.evidenceId || "")}</div></div>`;
}

function evidenceColumn(title, entries, formatter) {
  if (!entries.length) return "";
  return `<details class="evidence-column"><summary>${escapeHtml(title)} (${entries.length})</summary>${entries.map(formatter).join("")}</details>`;
}

function decisionEffectView(preview) {
  const effect = preview.decisionEffect || {};
  const rows = effect.rows || [];
  const rowHtml = rows.length
    ? rows.map((entry) => `<div class="effect-row"><span class="type-badge">${escapeHtml(entry.effect)}</span>${canonicalRowView(entry.after || entry.before || {})}</div>`).join("")
    : '<div class="empty-note">This decision writes zero physical rows.</div>';
  const cleared = effect.removedBlockerSubjectIds || [];
  const added = effect.addedBlockerSubjectIds || [];
  const suppressed = effect.suppressedProposalRows || [];
  let summary;
  if (!preview.projectable) {
    summary = "Cannot be saved because the decision does not produce a complete workbook-safe effect.";
  } else if (suppressed.length) {
    summary = "Writes no rows and suppresses the entire proposal.";
  } else if (!effect.writesRows || !rows.length) {
    summary = "Writes no workbook rows.";
  } else {
    const additions = rows.filter((entry) => ["add", "added"].includes(entry.effect)).length;
    const updates = rows.filter((entry) => ["update", "changed"].includes(entry.effect)).length;
    const removals = rows.filter((entry) => ["remove", "removed"].includes(entry.effect)).length;
    const changes = [];
    if (additions) changes.push(`adds ${additions}`);
    if (updates) changes.push(`updates ${updates}`);
    if (removals) changes.push(`removes ${removals}`);
    summary = `${changes.join(", ") || "Changes"} workbook row${rows.length === 1 ? "" : "s"} (${rows.length} total).`;
  }
  const suppressedHtml = suppressed.length
    ? `<div class="source-blocker"><b>Entire proposal suppressed.</b>${suppressed.map(canonicalRowView).join("")}</div>`
    : "";
  return `<h3 tabindex="-1">Preview</h3>
    <p class="preview-summary">${escapeHtml(summary)} <b>The live workbook is not being written.</b></p>
    <div class="cell-sub">Clears ${escapeHtml(cleared.length)} blocker${cleared.length === 1 ? "" : "s"}; adds ${escapeHtml(added.length)} blocker${added.length === 1 ? "" : "s"}.</div>
    <details class="exact-effects"><summary>Exact workbook rows (${rows.length})</summary>${rowHtml}${suppressedHtml}</details>`;
}

function sourceSnippetView(item) {
  const source = (item.evidence.sourceEvidence || [])[0];
  if (!source) return "";
  const rpo = source.rpo || source.refOnlyRpo || "Target source";
  return `<div class="source-snippet"><span>Target source</span><b>${escapeHtml(rpo)}</b> — ${escapeHtml(source.description || "Description unavailable")}</div>`;
}

function conflictComparisonView(item) {
  const comparison = (item.presentation || {}).comparison;
  if (!comparison) return "";
  return `<section class="conflict-comparison" aria-label="Existing and proposed behavior">
    <div><span>Existing</span><p>${escapeHtml(comparison.existing)}</p></div>
    <div><span>Proposed</span><p>${escapeHtml(comparison.proposed)}</p></div>
    <p class="conflict-difference"><b>Difference:</b> ${escapeHtml(comparison.difference)}</p>
  </section>`;
}

function supportingEvidenceView(item) {
  const subject = item.subject;
  const raw = item.evidence.sourceEvidence || [];
  const existingRows = item.evidence.existingWorkbookRows || [];
  const derivedRows = item.evidence.alreadyDerivedRows || [];
  const sharedContext = item.evidence.sharedContext || [];
  const comparator = item.evidence.comparator || [];
  const proposed = subject.proposedRows || [];
  const columns = `
      ${evidenceColumn("Raw source evidence", raw, sourceEvidenceView)}
      ${evidenceColumn("Existing workbook rows", existingRows, canonicalRowView)}
      ${evidenceColumn("Already-derived rows", derivedRows, canonicalRowView)}
      ${evidenceColumn("Comparator context", comparator, comparatorEvidenceView)}
      ${evidenceColumn("Proposal to evaluate — not workbook rows", proposed, canonicalRowView)}
    `;
  return `<details class="supporting-details"><summary>Supporting details</summary>
    <div class="evidence-grid">${columns}</div>
    ${sharedContext.length ? `<details class="shared-context"><summary>Shared context — not written by this decision (${sharedContext.length})</summary>${sharedContext.map(canonicalRowView).join("")}</details>` : ""}
    <details class="debug-detail"><summary>Technical details</summary>
      <div class="gate-impact"><b>Gate impact:</b> Blocks ${escapeHtml(subject.model)} compilation.</div>
      <code>${escapeHtml(subject.reasonCode)} · ${escapeHtml(subject.subjectId)}</code>
      <div class="cell-sub">Affected sheets: ${(item.affectedSheets || []).map(escapeHtml).join(", ") || "not yet projectable"}</div>
    </details>
  </details>`;
}

function renderExpandedException(item) {
  const subject = item.subject;
  const presentation = item.presentation || {};
  const stale = (item.history.stale || []).length;
  return `<section class="exception-card ${item.state === "resolved" ? "exception-resolved" : ""}" id="exception-detail-${escapeHtml(subject.subjectId)}">
    <div class="decision-heading">
      <div><span class="decision-kicker">Decision</span><h2 tabindex="-1">${escapeHtml(presentation.title || `${subject.model} decision`)}</h2></div>
      <span class="type-badge ${subject.severity === "blocking" ? "type-unsupported" : ""}">${escapeHtml(item.reviewState.replaceAll("_", " "))}</span>
    </div>
    <p class="decision-sentence">${escapeHtml(presentation.summary || subject.question)}</p>
    <p class="why-asked"><b>Why this needs a decision:</b> ${escapeHtml(presentation.whyAsked || subject.question)}</p>
    ${sourceSnippetView(item)}
    ${conflictComparisonView(item)}
    ${stale ? `<div class="status-note">${stale} prior answer${stale === 1 ? "" : "s"} became stale when evidence changed.</div>` : ""}
    <div class="compilation-impact">Blocks ${escapeHtml(subject.model)} compilation</div>
    ${exceptionActionForm(item)}
    ${supportingEvidenceView(item)}
  </section>`;
}

function renderExceptionSummary(item) {
  const subject = item.subject;
  const presentation = item.presentation || {};
  const expanded = exceptionState.expandedSubjectId === subject.subjectId;
  const rpos = (presentation.options || []).map((option) => option.rpo).filter(Boolean).join(" · ");
  return `<article class="exception-summary ${expanded ? "is-expanded" : ""} ${item.state === "resolved" ? "exception-resolved" : ""}">
    <button type="button" class="exception-summary-toggle" data-subject-id="${escapeHtml(subject.subjectId)}" aria-expanded="${expanded ? "true" : "false"}" aria-controls="exception-detail-${escapeHtml(subject.subjectId)}">
      <span class="summary-model">${escapeHtml(subject.model)}</span>
      <span class="summary-type">${escapeHtml(item.decisionType.replaceAll("_", " "))}</span>
      <span class="summary-rpos">${escapeHtml(rpos || "Source decision")}</span>
      <span class="summary-behavior">${escapeHtml(presentation.summary || subject.question)}</span>
      <span class="summary-state">${escapeHtml(item.reviewState.replaceAll("_", " "))}</span>
    </button>
    ${expanded ? renderExpandedException(item) : ""}
  </article>`;
}

function renderExceptionCard(item) {
  return renderExceptionSummary(item);
}

function toggleExpandedException(subjectId) {
  exceptionState.expandedSubjectId = exceptionState.expandedSubjectId === subjectId ? null : subjectId;
  if (exceptionState.payload) renderExceptionPage(exceptionState.payload);
}

function fillExceptionFilter(id, values, allLabel) {
  const select = $(id);
  const current = select.value;
  select.innerHTML = `<option value="">${escapeHtml(allLabel)}</option>${(values || []).map((value) => `<option value="${escapeHtml(value)}">${escapeHtml(value.replaceAll("_", " "))}</option>`).join("")}`;
  if ([...select.options].some((option) => option.value === current)) select.value = current;
}

function renderExceptionReadiness(summary) {
  $("#exception-readiness").innerHTML = Object.entries(summary.models || {})
    .map(([model, entry]) => `<span class="sum-chip ${entry.compileReady ? "sum-exact" : "sum-warn"}"><b>${escapeHtml(model)}</b>: compile ${readinessLabel(entry.compileReady)} · ${escapeHtml(entry.blockerCount)} blockers</span>`)
    .join("");
}

function renderExceptionPage(payload) {
  exceptionState.payload = payload;
  exceptionState.offset = payload.offset;
  if (
    exceptionState.expandedSubjectId &&
    !payload.items.some((item) => item.subject.subjectId === exceptionState.expandedSubjectId)
  ) {
    exceptionState.expandedSubjectId = null;
  }
  fillExceptionFilter("#exception-model", payload.filters.models, "All models");
  fillExceptionFilter("#exception-decision", payload.filters.decisionTypes, "All decision types");
  fillExceptionFilter("#exception-sheet", payload.filters.affectedSheets, "All affected sheets");
  $("#exception-queue").innerHTML = payload.items.length
    ? payload.items.map(renderExceptionCard).join("")
    : '<div class="empty-note">No exceptions match these filters.</div>';
  const first = payload.total ? payload.offset + 1 : 0;
  const last = Math.min(payload.total, payload.offset + payload.items.length);
  $("#exception-pagination").innerHTML = `
    <button id="exceptions-prev" class="ghost" ${payload.offset <= 0 ? "disabled" : ""}>Previous</button>
    <span class="status-note">Showing ${first}–${last} of ${payload.total}</span>
    <button id="exceptions-next" class="ghost" ${last >= payload.total ? "disabled" : ""}>Next</button>`;
  $("#exceptions-prev").addEventListener("click", () => loadExceptions(Math.max(0, payload.offset - payload.limit)));
  $("#exceptions-next").addEventListener("click", () => loadExceptions(payload.offset + payload.limit));
  if (exceptionState.pendingFocusSubjectId) {
    const focusId = exceptionState.pendingFocusSubjectId;
    exceptionState.pendingFocusSubjectId = null;
    requestAnimationFrame(() => {
      const buttons = [...document.querySelectorAll(".exception-summary-toggle")];
      const firstDecisionId = payload.items
        .find((item) => item.reviewState === "needs_decision")?.subject.subjectId;
      const target = buttons.find(
        (button) => button.dataset.subjectId === (
          focusId === "__first__" ? firstDecisionId : focusId
        )
      ) || buttons.find((button) => button.dataset.subjectId === firstDecisionId);
      if (target) target.focus();
    });
  }
}

async function loadExceptions(offset = 0) {
  const params = new URLSearchParams({
    model: $("#exception-model").value,
    decisionType: $("#exception-decision").value,
    sheet: $("#exception-sheet").value,
    reviewState: $("#exception-review-state").value,
    q: $("#exception-q").value.trim(),
    offset: String(offset),
    limit: String(exceptionState.limit),
  });
  const payload = await getJSON(`/api/wizard/sessions/${state.session.runId}/exceptions?${params}`);
  renderExceptionPage(payload);
}

async function enterExceptions() {
  setStage("exceptions");
  if (!compilerState.summary) {
    compilerState.summary = await getJSON(`/api/wizard/sessions/${state.session.runId}/compile`);
    state.session = compilerState.summary.session;
  }
  renderExceptionReadiness(compilerState.summary);
  await loadExceptions(0);
}

function resolutionPayload(form, action, reasonCode) {
  const data = new FormData(form);
  switch (action) {
    case "choose_section":
      return { sectionId: data.get("sectionId") };
    case "keep_inactive_option":
      return { sectionId: data.get("sectionId") };
    case "choose_relationship":
      return { sourceOptionId: data.get("sourceOptionId"), ruleType: data.get("ruleType"), targetOptionId: data.get("targetOptionId") };
    case "retain_existing":
      return { existingId: data.get("existingId") };
    case "provide_option_copy":
      return { optionName: data.get("optionName"), description: data.get("description") || "" };
    case "provide_option_behavior":
      return { active: data.get("active") === "true", selectable: data.get("selectable") === "true" };
    case "confirm_mandatory_charge":
      return { priceValue: Number(data.get("priceValue")) };
    case "provide_typed_value": {
      if (reasonCode === "comparator_only_rule_group_proposal") return { decision: "confirm_proposal" };
      if (reasonCode === "comparator_only_exclusive_group_proposal") {
        return { decision: "confirm_proposal", selectionMode: data.get("selectionMode") };
      }
      if (reasonCode === "comparator_only_default_selection_proposal") {
        const displayBehavior = data.get("defaultDisplayBehavior");
        return {
          decision: "confirm_proposal",
          priority: Number(data.get("priority")),
          displayBehavior: displayBehavior === "__blank__" ? "" : displayBehavior,
        };
      }
      const selectedScope = JSON.parse(data.get("priceScope"));
      const result = {};
      if (reasonCode === "comparator_only_price_rule_proposal") result.decision = "confirm_proposal";
      if (selectedScope.bodyStyleScope) result.bodyStyleScope = selectedScope.bodyStyleScope;
      if (selectedScope.trimLevelScope) result.trimLevelScope = selectedScope.trimLevelScope;
      if (selectedScope.variantScope) result.variantScope = selectedScope.variantScope;
      if (data.get("priceValue") !== "") result.priceValue = Number(data.get("priceValue"));
      return result;
    }
    case "approve_removal":
    case "mark_not_applicable":
      return { reason: data.get("reason") || "Reviewer rejected the entire proposal; no rows should be written." };
    case "record_allowed_deferral":
      return { kind: data.get("kind"), reason: data.get("reason") };
    default:
      return {};
  }
}

function invalidateDecisionPreview(form) {
  form.dataset.previewToken = "";
  const preview = form.querySelector(".decision-preview");
  preview.hidden = true;
  preview.innerHTML = "";
  form.querySelector('button[type="submit"]').textContent = "Preview effect";
}

$("#exception-queue").addEventListener("change", (event) => {
  const outcome = event.target.closest('input[name="decisionAction"]');
  if (!outcome) return;
  const form = outcome.closest(".exception-resolution-form");
  form.dataset.action = outcome.value;
  form.querySelector(".conditional-action-fields").innerHTML = exceptionActionFields(
    exceptionState.payload.items.find((item) => item.subject.subjectId === form.dataset.subjectId),
    outcome.value
  );
  form.querySelector('button[type="submit"]').disabled = false;
  invalidateDecisionPreview(form);
});

$("#exception-queue").addEventListener("submit", async (event) => {
  const form = event.target.closest(".exception-resolution-form");
  if (!form) return;
  event.preventDefault();
  clearError();
  if (!form.dataset.action) {
    showError("Choose one outcome before previewing its effect.");
    return;
  }
  const button = form.querySelector('button[type="submit"]');
  button.disabled = true;
  try {
    const payload = resolutionPayload(form, form.dataset.action, form.dataset.reasonCode);
    const previewToken = JSON.stringify({
      subjectId: form.dataset.subjectId,
      subjectVersion: form.dataset.subjectVersion,
      action: form.dataset.action,
      payload,
    });
    if (form.dataset.previewToken !== previewToken) {
      const preview = await postJSON(`/api/wizard/sessions/${state.session.runId}/exceptions/preview`, {
        subjectId: form.dataset.subjectId,
        subjectVersion: form.dataset.subjectVersion,
        action: form.dataset.action,
        payload,
      });
      form.dataset.previewToken = previewToken;
      form.querySelector(".decision-preview").hidden = false;
      form.querySelector(".decision-preview").innerHTML = decisionEffectView(preview);
      form.querySelector(".decision-preview h3").focus();
      button.textContent = "Save exact effect";
      $("#exception-status").textContent = "Preview complete. Review the summary and exact rows, then save.";
      return;
    }
    const reviewer = $("#exception-reviewer").value.trim();
    if (!reviewer) {
      showError("Enter the reviewer name before saving an exception answer.");
      $("#exception-reviewer").focus();
      return;
    }
    const result = await postJSON(`/api/wizard/sessions/${state.session.runId}/exceptions/resolve`, {
      subjectId: form.dataset.subjectId,
      subjectVersion: form.dataset.subjectVersion,
      action: form.dataset.action,
      payload,
      reviewer,
    });
    compilerState.summary = result.summary;
    state.session = result.summary.session;
    renderExceptionReadiness(result.summary);
    $("#exception-status").textContent = "Resolution saved and compiler rerun completed.";
    const currentIndex = (exceptionState.payload.items || [])
      .findIndex((item) => item.subject.subjectId === form.dataset.subjectId);
    const next = (exceptionState.payload.items || [])
      .slice(currentIndex + 1)
      .find((item) => item.reviewState === "needs_decision");
    exceptionState.expandedSubjectId = null;
    exceptionState.pendingFocusSubjectId = next ? next.subject.subjectId : "__first__";
    await loadExceptions(exceptionState.offset);
  } catch (error) {
    showError(error.message);
  } finally {
    button.disabled = false;
  }
});

$("#exception-queue").addEventListener("input", (event) => {
  const form = event.target.closest(".exception-resolution-form");
  if (!form || !form.dataset.previewToken) return;
  invalidateDecisionPreview(form);
  $("#exception-status").textContent = "Inputs changed. Preview the effect again before saving.";
});

$("#exception-queue").addEventListener("click", async (event) => {
  const toggle = event.target.closest(".exception-summary-toggle");
  if (toggle) {
    toggleExpandedException(toggle.dataset.subjectId);
    if (exceptionState.expandedSubjectId === toggle.dataset.subjectId) {
      requestAnimationFrame(() => {
        document.getElementById(`exception-detail-${toggle.dataset.subjectId}`)?.querySelector("h2")?.focus();
      });
    }
    return;
  }
  const button = event.target.closest(".exception-reopen");
  if (!button) return;
  clearError();
  const reviewer = $("#exception-reviewer").value.trim();
  if (!reviewer) {
    showError("Enter the reviewer name before reopening an answer.");
    return;
  }
  button.disabled = true;
  try {
    const result = await postJSON(`/api/wizard/sessions/${state.session.runId}/exceptions/reopen`, {
      subjectId: button.dataset.subjectId,
      subjectVersion: button.dataset.subjectVersion,
      reviewer,
    });
    compilerState.summary = result.summary;
    state.session = result.summary.session;
    renderExceptionReadiness(result.summary);
    $("#exception-status").textContent = "Resolution reopened and compiler rerun completed.";
    await loadExceptions(exceptionState.offset);
  } catch (error) {
    showError(error.message);
  } finally {
    button.disabled = false;
  }
});

for (const id of ["#exception-model", "#exception-decision", "#exception-sheet", "#exception-review-state"]) {
  $(id).addEventListener("change", () => loadExceptions(0).catch((error) => showError(error.message)));
}
let exceptionSearchTimer = null;
$("#exception-q").addEventListener("input", () => {
  clearTimeout(exceptionSearchTimer);
  exceptionSearchTimer = setTimeout(() => loadExceptions(0).catch((error) => showError(error.message)), 250);
});
$("#exceptions-recompile-btn").addEventListener("click", async () => {
  await runCompile();
  if (compilerState.summary) await enterExceptions();
});
$("#exceptions-back-compile").addEventListener("click", enterCompile);

/* ------------------------------------------------------- stage: changeset */

function renderChangeSet(detail) {
  const changeSet = detail.changeSet;
  state.session = detail.session;
  const sheetCreates = changeSet.sheetCreates || [];
  const rowChanges = changeSet.rowChanges || [];
  const noops = changeSet.noops || [];
  const targets = changeSet.targets || [];
  const workbook = changeSet.workbookFingerprint || {};
  $("#changeset-summary").innerHTML = `
    <div class="summary">
      <span class="sum-chip"><b>${escapeHtml(targets.length)}</b> targets</span>
      <span class="sum-chip"><b>${escapeHtml(sheetCreates.length)}</b> sheet creations</span>
      <span class="sum-chip"><b>${escapeHtml(rowChanges.length)}</b> row changes</span>
      <span class="sum-chip"><b>${escapeHtml(noops.length)}</b> no-op receipts</span>
    </div>
    <p class="status-note">Targets: ${targets.map(escapeHtml).join(", ") || "none"}</p>
    <p class="status-note">Workbook fingerprint: <code>${escapeHtml(workbook.sha256 || "unavailable")}</code></p>`;
  const blob = new Blob([JSON.stringify(changeSet, null, 2) + "\n"], { type: "application/json" });
  const download = $("#changeset-download");
  if (download.dataset.objectUrl) URL.revokeObjectURL(download.dataset.objectUrl);
  download.dataset.objectUrl = URL.createObjectURL(blob);
  download.href = download.dataset.objectUrl;
  $("#changeset-download").download = "workbook-change-set.json";
  $("#changeset-status").textContent = "ChangeSet emitted. No approval or workbook apply occurred.";
}

async function createChangeSet() {
  clearError();
  const button = $("#compile-changeset-btn");
  button.disabled = true;
  button.textContent = "Creating ChangeSet…";
  try {
    const detail = await postJSON(`/api/wizard/sessions/${state.session.runId}/changeset`, {});
    renderChangeSet(detail);
    setStage("changeset");
  } catch (error) {
    showError(error.message);
  } finally {
    button.disabled = false;
    button.textContent = "Create ChangeSet";
  }
}

$("#compile-changeset-btn").addEventListener("click", createChangeSet);
$("#back-to-candidates").addEventListener("click", () => setStage("candidates"));

/* ------------------------------------------------------------------- init */

setStage("files");
loadFiles().catch((error) => showError(error.message));
