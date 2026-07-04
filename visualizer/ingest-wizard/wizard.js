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

const STAGES = ["files", "sheets", "candidates"];

function setStage(stage) {
  clearError();
  for (const name of STAGES) {
    $(`#stage-${name}`).classList.toggle("hidden", name !== stage);
  }
  const reached = STAGES.indexOf(stage);
  document.querySelectorAll("#stepper .step").forEach((el, index) => {
    el.classList.toggle("active", index === reached);
    el.classList.toggle("done", index < reached);
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
}

function renderFiles() {
  const list = $("#file-list");
  if (!state.files.length) {
    list.innerHTML = '<div class="empty-note">No .xlsx files found. Upload a raw order-guide export.</div>';
  } else {
    list.innerHTML = state.files
      .map(
        (file) => `
        <div class="file-row ${state.selectedFile === file.name ? "selected" : ""}" data-file="${escapeHtml(file.name)}">
          <span class="file-name">${escapeHtml(file.name)}</span>
          <span class="badge">${escapeHtml(file.origin)}</span>
          <span class="file-meta">${(file.sizeBytes / 1024).toFixed(0)} KB</span>
        </div>`
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
          (value === "options" && card.sheetType === "options_matrix") ||
          (value === "price" && card.sheetType === "price_sheet");
        return `<button class="role-btn ${role === value ? "active" : ""}" data-sheet="${escapeHtml(card.sheetName)}" data-role="${value}" ${allowed ? "" : "disabled"}>${label}</button>`;
      };
      const subtypeNote =
        card.contentSubtype === "standard_equipment"
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

/* ------------------------------------------------------------------- init */

setStage("files");
loadFiles().catch((error) => showError(error.message));
