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

const STAGES = ["files", "sheets", "candidates", "models", "review"];

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
  const comparatorChoices = modelState.options
    .filter((m) => !m.isDefaultTarget)
    .map((m) => m.modelKey);
  $("#model-cards").innerHTML = modelState.options
    .map((model) => {
      const isTarget = modelState.targets.has(model.modelKey);
      const comparator = modelState.comparators[model.modelKey] || "";
      const comparatorSelect = isTarget
        ? `<label class="cmp-label">Reference model (workbook data used for prefill and comparisons)
            <select class="cmp-select" data-model="${escapeHtml(model.modelKey)}">
              <option value="">none</option>
              ${comparatorChoices
                .map(
                  (key) =>
                    `<option value="${escapeHtml(key)}" ${key === comparator ? "selected" : ""}>${escapeHtml(key)}</option>`
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
    renderReconciliation();
  } catch (error) {
    showError(error.message);
  }
});

function renderReconciliation() {
  const models = (modelState.reconciliation || {}).models || {};
  const blocks = Object.entries(models).map(([key, entry]) => {
    const rows = entry.exportVariants
      .map((v) => `<span class="vchip">${escapeHtml(v.modelCode)} ${escapeHtml(v.trim)} ${escapeHtml(v.bodyStyle)}</span>`)
      .join("");
    const verdict = entry.agrees
      ? '<span class="conf conf-high">matches workbook scaffold</span>'
      : `<span class="conf conf-low">disagrees — ${entry.exportOnly.length} export-only, ${entry.workbookOnly.length} workbook-only (mandatory decision)</span>`;
    return `<div class="card"><div class="card-head"><span class="card-title">${escapeHtml(key)}</span>${verdict}</div>
      <div class="variant-chips">${rows}</div></div>`;
  });
  $("#reconciliation").innerHTML = blocks.length
    ? `<h2 class="sub-h">Variant reconciliation</h2><div class="cards">${blocks.join("")}</div>
       <div class="sheet-actions"><button id="to-review-btn" class="primary">Start decision review</button></div>`
    : "";
  const toReview = $("#to-review-btn");
  if (toReview) toReview.addEventListener("click", () => enterReview());
}

$("#to-models-btn").addEventListener("click", async () => {
  clearError();
  try {
    await loadModels();
    setStage("models");
  } catch (error) {
    showError(error.message);
  }
});
$("#back-to-candidates").addEventListener("click", () => setStage("candidates"));
$("#back-to-models").addEventListener("click", () => setStage("models"));

/* --------------------------------------------------------- stage: review */

const LANES = [
  ["section", "Section assignment"],
  ["price", "Price resolution"],
  ["exclusive_group", "Exclusive groups"],
  ["relationship", "Relationships"],
  ["copy_split", "Copy split"],
  ["status_nuance", "Status nuances"],
  ["duplicate", "Duplicates"],
  ["standard_equipment", "Standard equipment"],
  ["interior_media_deferral", "Interiors / media deferrals"],
  ["presentation", "Presentation metadata"],
];

/* Stored decision values never change (Pass C reads them); these maps are the
   reviewer-facing language layer only. */
const RESOLUTION_LABELS = {
  approved_for_plan: ["Approve — write to workbook", "Goes into the apply plan in Pass C."],
  hold_for_question: ["Hold — I have a question", "Counts as reviewed; listed in the holds report until resolved."],
  not_needed: ["Skip — don't carry over", "Recorded so it never comes back as missing."],
};

const ACTION_LABELS = {
  assign_section: ["Put in section", "Places this option in the chosen form section."],
  accept_exact_price: ["Use matched price", "Takes the single price-schedule match."],
  choose_price_row: ["Pick a price row", "Choose one of several matching price rows."],
  set_reviewed_price: ["Enter a price", "Type the reviewed dollar value."],
  confirm_no_price: ["No price (included)", "Confirms this option carries no separate price."],
  defer_price_extractor: ["Defer — fix price source later", "Price stays empty in the plan until decided."],
  create_exclusive_group: ["Create pick-one group", "Members can't be ordered together."],
  create_relationship_candidate: ["Record relationship", "Requires/includes/excludes between options."],
  needs_product_decision: ["Flag for product call", "Needs a business answer before the plan."],
  split_copy: ["Set customer copy", "Name / description / fine print for the form."],
  confirm_status: ["Confirm as parsed", "The parsed availability status is right."],
  mark_unresolved_blocked: ["Can't resolve — block it", "Status can't be determined from the source."],
  classify_duplicate_source: ["Classify duplicate", "Same option or different by context?"],
  include_standard_equipment: ["Include as standard", "Shows as standard equipment for this model."],
  exclude_row: ["Leave out", "Row won't be carried into the workbook."],
  defer_item: ["Defer for later", "Named item to handle in the apply pass."],
  approve_presentation_rows: ["Approve rows", "Approves this sheet's presentation rows."],
};

const LANE_DESCRIPTIONS = {
  section: "Pick where each option lives in the form.",
  price: "Settle every option's price — matched, entered, none, or deferred.",
  exclusive_group: "Group options the customer must pick only one of.",
  relationship: "Record requires / includes / not-available-with rules between options.",
  copy_split: "The script proposed customer copy for every row — fix only the flagged ones.",
  status_nuance: "Confirm rows whose availability symbols need a human read.",
  duplicate: "Same RPO on several sheets — same option or different by context?",
  standard_equipment: "Decide which no-RPO rows show as standard equipment.",
  interior_media_deferral: "Name interior / color / image work to handle in the apply pass.",
  presentation: "Approve the form's steps, sections, and summary layout for this model.",
};

function labelFor(map, value) {
  const entry = map[value];
  return entry ? entry[0] : value.replaceAll("_", " ");
}

function titleFor(map, value) {
  const entry = map[value];
  return entry ? entry[1] : "";
}

const RELATIONSHIP_KINDS = [
  "requires",
  "not_available_with",
  "only_available_with",
  "included_with",
  "includes",
  "requires_additional_equipment",
  "deletes",
  "replaces",
  "upgradeable_to",
  "other",
];

const reviewState = {
  payload: null,
  progress: null,
  checked: new Set(),
  queueKey: "",
  lastBatch: null, // {batchId, count, queueKey}
  splitShowAll: false,
};

function currentQueueKey() {
  return [
    $("#review-model").value,
    $("#review-lane").value,
    $("#review-q").value.trim(),
    $("#review-source-section").value,
  ].join("|");
}

async function enterReview() {
  const modelSelect = $("#review-model");
  modelSelect.innerHTML = [...modelState.targets]
    .map((key) => `<option value="${escapeHtml(key)}">${escapeHtml(key)}</option>`)
    .join("");
  const laneSelect = $("#review-lane");
  laneSelect.innerHTML = LANES.map(
    ([lane, label]) => `<option value="${escapeHtml(lane)}">${escapeHtml(label)}</option>`
  ).join("");
  await refreshReview();
  setStage("review");
}

async function refreshReview() {
  const model = $("#review-model").value;
  const lane = $("#review-lane").value;
  const params = new URLSearchParams({ model, lane });
  if ($("#review-q").value.trim()) params.set("q", $("#review-q").value.trim());
  if ($("#review-source-section").value) params.set("sourceSection", $("#review-source-section").value);
  reviewState.payload = await getJSON(
    `/api/wizard/sessions/${state.session.runId}/review?${params}`
  );
  reviewState.progress = await getJSON(`/api/wizard/sessions/${state.session.runId}/progress`);
  const key = currentQueueKey();
  if (key !== reviewState.queueKey) {
    reviewState.checked = new Set();
    reviewState.queueKey = key;
  }
  populateSourceSections();
  populateCopyBar();
  renderProgress();
  renderLaneHeader();
  renderBulkBar();
  renderQueue();
}

function renderLaneHeader() {
  const lane = $("#review-lane").value;
  $("#lane-help").innerHTML = `
    <span>${escapeHtml(LANE_DESCRIPTIONS[lane] || "")}</span>
    <details class="glossary"><summary>What do these buttons mean?</summary>
      <ul>
        ${["approved_for_plan", "hold_for_question", "not_needed"]
          .map((value) => `<li><b>${escapeHtml(labelFor(RESOLUTION_LABELS, value))}</b> — ${escapeHtml(titleFor(RESOLUTION_LABELS, value))}</li>`)
          .join("")}
        <li><b>Clear</b> — removes a saved decision (kept in the audit log).</li>
        <li><b>Undo last bulk</b> — removes every decision from your most recent bulk action.</li>
      </ul>
    </details>`;
}

function populateSourceSections() {
  const select = $("#review-source-section");
  const current = select.value;
  const sections = reviewState.payload.sourceSections || [];
  select.innerHTML =
    '<option value="">All source sections</option>' +
    sections
      .map((label) => `<option value="${escapeHtml(label)}" ${label === current ? "selected" : ""}>${escapeHtml(label)}</option>`)
      .join("");
}

function populateCopyBar() {
  const current = $("#review-model").value;
  const others = [...modelState.targets].filter((key) => key !== current);
  const select = $("#copy-from-model");
  const previous = select.value;
  select.innerHTML = others
    .map((key) => `<option value="${escapeHtml(key)}" ${key === previous ? "selected" : ""}>${escapeHtml(key)}</option>`)
    .join("");
}

function renderProgress() {
  const model = $("#review-model").value;
  const entry = reviewState.progress.models[model];
  if (!entry) return;
  const chips = LANES.map(([lane, label]) => {
    const laneEntry = entry.lanes[lane] || {};
    const missing = laneEntry.missing ?? null;
    const cls = missing === null ? "" : missing === 0 ? "sum-exact" : "sum-warn";
    const text =
      missing === null
        ? `${laneEntry.decisions} decided`
        : `${(laneEntry.required ?? 0) - missing}/${laneEntry.required ?? 0}`;
    return `<span class="sum-chip ${cls}" title="${escapeHtml(label)}">${escapeHtml(label)}: <b>${text}</b></span>`;
  }).join("");
  const stateChip = entry.complete
    ? '<span class="sum-chip sum-exact"><b>complete</b></span>'
    : `<span class="sum-chip sum-warn"><b>${entry.blockers.length}</b> blockers</span>`;
  $("#progress-chips").innerHTML = stateChip + chips;
  $("#review-blockers").innerHTML = "";
}

function decisionFor(candidateId) {
  return (reviewState.payload.decisions || []).find((d) => d.candidateId === candidateId);
}

function selectControl(cls, options, current, placeholder) {
  return `<select class="${cls}">
    ${placeholder ? `<option value="">${escapeHtml(placeholder)}</option>` : ""}
    ${options
      .map(
        (value) =>
          `<option value="${escapeHtml(value)}" title="${escapeHtml(titleFor(ACTION_LABELS, value))}" ${value === current ? "selected" : ""}>${escapeHtml(labelFor(ACTION_LABELS, value))}</option>`
      )
      .join("")}
  </select>`;
}

function resolutionOptions(current) {
  return ["approved_for_plan", "hold_for_question", "not_needed"]
    .map(
      (value) =>
        `<option value="${value}" title="${escapeHtml(titleFor(RESOLUTION_LABELS, value))}" ${current === value ? "selected" : ""}>${escapeHtml(labelFor(RESOLUTION_LABELS, value))}</option>`
    )
    .join("");
}

function sectionSelect(current) {
  return `<select class="dec-section">
    <option value="">— section —</option>
    ${(reviewState.payload.sections || [])
      .map(
        (section) =>
          `<option value="${escapeHtml(section.sectionId)}" ${section.sectionId === current ? "selected" : ""}>${escapeHtml(section.sectionName)} (${escapeHtml(section.stepKey)})</option>`
      )
      .join("")}
  </select>`;
}

function laneRowControls(lane, candidate) {
  const decision = decisionFor(candidate.candidateId);
  const payload = (decision && decision.payload) || {};
  let controls = "";
  if (lane === "section") {
    const reference = ((reviewState.payload.workbookReference || {})[candidate.rpo] || [])[0];
    const useReference =
      reference && reference.sectionId
        ? `<button class="ref-use-section ghost" data-section="${escapeHtml(reference.sectionId)}" title="${escapeHtml(reference.sectionName || reference.sectionId)}">Use ${escapeHtml(reference.modelKey)}'s section</button>`
        : "";
    controls = `${sectionSelect(payload.sectionId || "")}${useReference}`;
  } else if (lane === "price") {
    const exact = candidate.priceMatch === "exact";
    const rows = (candidate.priceRows || [])
      .map(
        (row, index) =>
          `<option value="${index}" ${Number(payload.priceRowIndex) === index ? "selected" : ""}>${fmtPrice(row.listPrice)}${row.qualifier ? ` — ${escapeHtml(row.qualifier)}` : ""}</option>`
      )
      .join("");
    controls = `
      ${exact ? `<label class="dec-inline"><input type="checkbox" class="dec-price-exact" ${!decision || decision.action === "accept_exact_price" ? "checked" : ""}> accept ${fmtPrice(candidate.listPrice ?? (candidate.priceRows[0] || {}).listPrice)}</label>` : ""}
      ${rows ? `<select class="dec-price-row"><option value="">— pick price row —</option>${rows}</select>` : ""}
      <input class="dec-price-manual" type="number" step="0.01" placeholder="reviewed $" value="${payload.reviewedPrice ?? ""}">
      <label class="dec-inline"><input type="checkbox" class="dec-price-none" ${decision && decision.action === "confirm_no_price" ? "checked" : ""}> no price</label>
      <label class="dec-inline"><input type="checkbox" class="dec-price-defer" ${decision && decision.action === "defer_price_extractor" ? "checked" : ""}> defer</label>`;
  } else if (lane === "copy_split") {
    const proposal = candidate.proposedSplit || {};
    controls = `
      <input class="dec-copy-name" placeholder="customer-facing name" value="${escapeHtml(payload.name ?? proposal.name ?? "")}">
      <input class="dec-copy-desc" placeholder="description" value="${escapeHtml(payload.description ?? proposal.description ?? "")}">
      <input class="dec-copy-disc" placeholder="fine print / disclosure" value="${escapeHtml(payload.disclosure ?? proposal.disclosure ?? "")}">
      ${(proposal.flags || []).map((flag) => `<span class="sum-chip sum-warn">${escapeHtml(flag.replaceAll("_", " "))}</span>`).join("")}`;
  } else if (lane === "status_nuance") {
    controls = selectControl(
      "dec-status-action",
      ["confirm_status", "mark_unresolved_blocked"],
      decision ? decision.action : "confirm_status"
    );
  } else if (lane === "duplicate") {
    controls = selectControl(
      "dec-dup-class",
      ["same_option", "distinct_by_context"],
      payload.classification || "",
      "— classification —"
    );
  } else if (lane === "standard_equipment") {
    controls = selectControl(
      "dec-se-action",
      ["include_standard_equipment", "exclude_row"],
      decision ? decision.action : "include_standard_equipment"
    );
  }
  return `
    ${controls}
    <select class="dec-resolution">${resolutionOptions(decision ? decision.resolution : "approved_for_plan")}</select>
    <input class="dec-note" placeholder="note" value="${escapeHtml(decision ? decision.reviewerNote : "")}">
    <button class="dec-save primary" data-id="${escapeHtml(candidate.candidateId)}">Save</button>
    ${decision ? '<span class="conf conf-high">saved</span>' : ""}`;
}

function collectRowDecision(lane, row, candidateId) {
  const resolution = row.querySelector(".dec-resolution").value;
  const reviewerNote = row.querySelector(".dec-note").value;
  let action = "";
  let payload = {};
  if (lane === "section") {
    action = "assign_section";
    payload = { sectionId: row.querySelector(".dec-section").value };
    if (!payload.sectionId) throw new Error("Pick a section first.");
  } else if (lane === "price") {
    const exact = row.querySelector(".dec-price-exact");
    const rowSelect = row.querySelector(".dec-price-row");
    const manual = row.querySelector(".dec-price-manual");
    if (row.querySelector(".dec-price-defer").checked) {
      action = "defer_price_extractor";
    } else if (row.querySelector(".dec-price-none").checked) {
      action = "confirm_no_price";
    } else if (manual.value !== "") {
      action = "set_reviewed_price";
      payload = { reviewedPrice: Number(manual.value) };
    } else if (rowSelect && rowSelect.value !== "") {
      action = "choose_price_row";
      payload = { priceRowIndex: Number(rowSelect.value) };
    } else if (exact && exact.checked) {
      action = "accept_exact_price";
    } else {
      throw new Error("Pick a price resolution (accept, price row, reviewed value, no price, or defer).");
    }
  } else if (lane === "copy_split") {
    action = "split_copy";
    payload = {
      name: row.querySelector(".dec-copy-name").value,
      description: row.querySelector(".dec-copy-desc").value,
      disclosure: row.querySelector(".dec-copy-disc").value,
    };
    if (!payload.name) throw new Error("Customer-facing name is required.");
  } else if (lane === "status_nuance") {
    action = row.querySelector(".dec-status-action").value;
  } else if (lane === "duplicate") {
    action = "classify_duplicate_source";
    payload = { classification: row.querySelector(".dec-dup-class").value };
    if (!payload.classification) throw new Error("Pick a duplicate classification.");
  } else if (lane === "standard_equipment") {
    action = row.querySelector(".dec-se-action").value;
  }
  return {
    model: $("#review-model").value,
    lane,
    candidateId,
    action,
    payload,
    resolution,
    reviewerNote,
  };
}

function hintBlock(candidate, clickable = false) {
  const hints = (reviewState.payload.hints || {})[candidate.candidateId] || [];
  if (!hints.length) return "";
  const chips = hints
    .map((hint) => {
      const label = `${escapeHtml(hint.kind.replaceAll("_", " "))}${hint.rpoTokens.length ? ` → ${escapeHtml(hint.rpoTokens.join(", "))}` : ""}`;
      if (!clickable) return `<span class="sum-chip" title="${escapeHtml(hint.snippet)}">${label}</span>`;
      return `<button class="sum-chip hint-accept" title="${escapeHtml(hint.snippet)}"
        data-kind="${escapeHtml(hint.kind)}"
        data-source="${escapeHtml(candidate.rpo || candidate.refOnlyRpo)}"
        data-targets="${escapeHtml(hint.rpoTokens.join(","))}">${label}</button>`;
    })
    .join("");
  return `<div class="hints">${chips}<div class="cell-sub">Hints are suggestions only — ${clickable ? "click one to prefill the form, then edit and save" : "record them in the Relationships lane"}.</div></div>`;
}

function referenceLine(candidate) {
  const rows = (reviewState.payload.workbookReference || {})[candidate.rpo];
  if (!candidate.rpo) return "";
  if (!rows || !rows.length) {
    return '<div class="cell-sub ref-line ref-new">New to workbook — no reference</div>';
  }
  const top = rows[0];
  const price = top.price ? ` · ${fmtPrice(Number(top.price))}` : "";
  const more = rows.length > 1 ? ` (+${rows.length - 1} more)` : "";
  return `<div class="cell-sub ref-line">In workbook: <b>${escapeHtml(top.modelKey)}</b> “${escapeHtml(top.optionName)}” · ${escapeHtml(top.sectionName || top.sectionId)}${price}${more}</div>`;
}

function visibleQueueCandidates() {
  const lane = $("#review-lane").value;
  let rows = reviewState.payload.candidates || [];
  if (lane === "copy_split" && !reviewState.splitShowAll) {
    rows = rows.filter((c) => ((c.proposedSplit || {}).flags || []).length > 0);
  }
  return rows;
}

function renderQueue() {
  const lane = $("#review-lane").value;
  if (lane === "presentation") {
    renderPresentationQueue();
    return;
  }
  if (lane === "exclusive_group" || lane === "relationship" || lane === "interior_media_deferral") {
    renderGroupLane(lane);
    return;
  }
  const candidates = visibleQueueCandidates();
  const splitToggle =
    lane === "copy_split"
      ? `<div class="hint">Script proposals prefilled. Showing ${reviewState.splitShowAll ? "all rows" : "flagged rows only"} ·
          <button id="split-toggle" class="ghost">${reviewState.splitShowAll ? "Show flagged only" : "Show all rows"}</button></div>`
      : "";
  const rows = candidates
    .map((candidate) => {
      const decision = decisionFor(candidate.candidateId);
      const checked = reviewState.checked.has(candidate.candidateId);
      return `
      <tr class="cand-row">
        <td><input type="checkbox" class="row-check" data-id="${escapeHtml(candidate.candidateId)}" ${checked ? "checked" : ""}></td>
        <td class="rpo">${escapeHtml(candidate.rpo || candidate.refOnlyRpo)}</td>
        <td class="desc">${escapeHtml(candidate.description)}
          <div class="cell-sub">${escapeHtml(candidate.sheetName)} · row ${candidate.rowIndex} · ${escapeHtml(candidate.sectionLabel)}</div>
          ${referenceLine(candidate)}
          ${hintBlock(candidate)}</td>
        <td><div class="stchips">${statusChips(candidate)}</div></td>
        <td>${priceBadge(candidate)}</td>
        <td class="dec-cell">${laneRowControls(lane, candidate)}
          ${decision ? `<button class="dec-clear ghost" data-id="${escapeHtml(candidate.candidateId)}">Clear</button>` : ""}</td>
      </tr>`;
    })
    .join("");
  $("#review-queue").innerHTML = rows
    ? `${splitToggle}<table class="cand"><thead><tr>
        <th><input type="checkbox" id="check-all" title="Select all filtered rows"></th>
        <th>RPO</th><th>Description</th><th>Statuses</th><th>Price</th><th>Decision</th>
      </tr></thead><tbody>${rows}</tbody></table>`
    : `${splitToggle}<div class="empty-note">No candidates in this lane for the current filters.</div>`;
  const checkAll = document.querySelector("#check-all");
  if (checkAll) {
    checkAll.checked = candidates.length > 0 && candidates.every((c) => reviewState.checked.has(c.candidateId));
  }
  const splitButton = document.querySelector("#split-toggle");
  if (splitButton) {
    splitButton.addEventListener("click", () => {
      reviewState.splitShowAll = !reviewState.splitShowAll;
      renderBulkBar();
      renderQueue();
    });
  }
}

function groupPayloadSummary(decision) {
  const payload = decision.payload || {};
  if (decision.lane === "relationship") {
    return `${payload.kind || ""}: ${payload.sourceRpo || ""} → ${(payload.targetRpos || []).join(", ")}${payload.note ? ` — ${payload.note}` : ""}`;
  }
  if (decision.lane === "exclusive_group") {
    return `members: ${(payload.members || []).join(", ")}`;
  }
  if (decision.lane === "interior_media_deferral") {
    return `${payload.kind || ""}${payload.note ? ` — ${payload.note}` : ""}`;
  }
  return Object.entries(payload)
    .map(([key, value]) => `${key}: ${Array.isArray(value) ? value.join(", ") : value}`)
    .join(" · ");
}

function groupFormFields(lane) {
  if (lane === "exclusive_group") {
    return `
      <input id="group-key" placeholder="exclusive group name (e.g. roof-panels)">
      <input id="group-members" placeholder="member RPOs, comma-separated (e.g. C2Q, CC3)">`;
  }
  if (lane === "relationship") {
    return `
      <input id="group-key" placeholder="relationship name (e.g. Z51-requires-E60)">
      ${selectControl("group-kind-select", RELATIONSHIP_KINDS, "", "— kind —").replace('class="group-kind-select"', 'class="group-kind-select" id="group-kind"')}
      <input id="group-source" placeholder="source RPO">
      <input id="group-targets" placeholder="target RPOs, comma-separated">
      <label class="dec-inline"><input type="checkbox" id="group-product-decision"> needs product decision</label>`;
  }
  return `
    <input id="group-key" placeholder="deferral name (e.g. gsx-interior-scope)">
    ${selectControl("x", ["interior", "color", "asset", "other"], "", "— kind —").replace('class="x"', 'id="deferral-kind"')}`;
}

function renderGroupLane(lane) {
  const decisions = reviewState.payload.decisions || [];
  const existing = decisions
    .map(
      (decision) => `
      <tr class="cand-row">
        <td class="rpo">${escapeHtml(decision.groupKey)}</td>
        <td class="desc">${escapeHtml(decision.action.replaceAll("_", " "))} · ${escapeHtml(groupPayloadSummary(decision))}</td>
        <td>${escapeHtml(decision.resolution.replaceAll("_", " "))}</td>
        <td>${escapeHtml(decision.reviewerNote)}${decision.copiedFrom ? ` <span class="cell-sub">copied from ${escapeHtml(decision.copiedFrom)}</span>` : ""}</td>
      </tr>`
    )
    .join("");
  const hintRows =
    lane === "relationship"
      ? (reviewState.payload.candidates || [])
          .filter((candidate) => (reviewState.payload.hints || {})[candidate.candidateId])
          .map(
            (candidate) => `
            <tr class="cand-row">
              <td class="rpo">${escapeHtml(candidate.rpo || candidate.refOnlyRpo)}</td>
              <td class="desc">${escapeHtml(candidate.description)}${hintBlock(candidate, true)}</td>
              <td colspan="2"></td>
            </tr>`
          )
          .join("")
      : "";
  $("#review-queue").innerHTML = `
    <div class="group-form">
      ${groupFormFields(lane)}
      <select id="group-resolution">${resolutionOptions("approved_for_plan")}</select>
      <input id="group-note" placeholder="note">
      <button id="group-save" class="primary">Save decision</button>
    </div>
    ${existing ? `<h2 class="sub-h">Recorded decisions</h2><table class="cand"><tbody>${existing}</tbody></table>` : ""}
    ${hintRows ? `<h2 class="sub-h">Candidates with relationship hints — click a hint to prefill the form</h2><table class="cand"><tbody>${hintRows}</tbody></table>` : ""}`;
  $("#group-save").addEventListener("click", async () => {
    clearError();
    try {
      await saveDecisions([collectGroupDecision(lane)]);
    } catch (error) {
      showError(error.message);
    }
  });
}

function collectGroupDecision(lane) {
  const groupKey = $("#group-key").value.trim();
  if (!groupKey) throw new Error("Give the decision a name.");
  const base = {
    model: $("#review-model").value,
    lane,
    groupKey,
    resolution: $("#group-resolution").value,
    reviewerNote: $("#group-note").value,
  };
  const csv = (value) =>
    value
      .split(",")
      .map((token) => token.trim().toUpperCase())
      .filter(Boolean);
  if (lane === "exclusive_group") {
    const members = csv($("#group-members").value);
    if (members.length < 2) throw new Error("An exclusive group needs at least two member RPOs.");
    return { ...base, action: "create_exclusive_group", payload: { members } };
  }
  if (lane === "relationship") {
    if ($("#group-product-decision").checked) {
      return { ...base, action: "needs_product_decision", payload: { note: $("#group-note").value } };
    }
    const kind = $("#group-kind").value;
    const sourceRpo = $("#group-source").value.trim().toUpperCase();
    const targetRpos = csv($("#group-targets").value);
    if (!kind || !sourceRpo || !targetRpos.length) {
      throw new Error("Relationship needs a kind, a source RPO, and at least one target RPO.");
    }
    return { ...base, action: "create_relationship_candidate", payload: { kind, sourceRpo, targetRpos } };
  }
  const kind = $("#deferral-kind").value;
  if (!kind) throw new Error("Pick a deferral kind.");
  return { ...base, action: "defer_item", payload: { kind, note: $("#group-note").value } };
}

function renderPresentationQueue() {
  const prefill = reviewState.payload.prefill;
  const decisions = reviewState.payload.decisions || [];
  const decidedSheets = new Set(decisions.map((decision) => decision.groupKey));
  const blocks = Object.entries(prefill.sheets)
    .map(([sheet, proposals]) => {
      const decided = decidedSheets.has(sheet);
      const columns = [...new Set(proposals.flatMap((proposal) => Object.keys(proposal.row)))];
      const header = `<tr><th></th>${columns.map((column) => `<th>${escapeHtml(column)}</th>`).join("")}</tr>`;
      const rows = proposals
        .map(
          (proposal, index) => `
          <tr class="cand-row">
            <td><input type="checkbox" class="pres-row" data-sheet="${escapeHtml(sheet)}" data-index="${index}" checked></td>
            ${columns
              .map(
                (column) =>
                  `<td><input class="pres-cell" data-sheet="${escapeHtml(sheet)}" data-index="${index}" data-column="${escapeHtml(column)}" value="${escapeHtml(proposal.row[column] ?? "")}" ${column === "model_key" ? "readonly" : ""}></td>`
              )
              .join("")}
          </tr>`
        )
        .join("");
      return `
      <div class="pres-sheet">
        <h2 class="sub-h">${escapeHtml(sheet)} ${decided ? '<span class="conf conf-high">approved</span>' : `<span class="conf conf-low">${proposals.length} template rows pending</span>`}</h2>
        <table class="cand pres-table"><thead>${header}</thead><tbody>${rows}</tbody></table>
        <button class="primary pres-approve" data-sheet="${escapeHtml(sheet)}">Approve checked rows for ${escapeHtml(sheet)}</button>
      </div>`;
    })
    .join("");
  $("#review-queue").innerHTML = `
    <p class="hint">Rows are template-derived proposals from <b>${escapeHtml(prefill.templateModel)}</b> — edit any cell, uncheck rows to drop, then approve. All five sheets need an approved row set.</p>
    ${blocks}`;
  document.querySelectorAll(".pres-approve").forEach((button) =>
    button.addEventListener("click", async () => {
      clearError();
      try {
        const sheet = button.dataset.sheet;
        const checked = [...document.querySelectorAll(`.pres-row[data-sheet="${CSS.escape(sheet)}"]`)]
          .filter((box) => box.checked)
          .map((box) => {
            const row = {};
            document
              .querySelectorAll(`.pres-cell[data-sheet="${CSS.escape(sheet)}"][data-index="${box.dataset.index}"]`)
              .forEach((cell) => {
                row[cell.dataset.column] = cell.value;
              });
            return row;
          });
        await saveDecisions([
          {
            model: $("#review-model").value,
            lane: "presentation",
            groupKey: sheet,
            action: "approve_presentation_rows",
            payload: { rows: checked, templateModel: prefill.templateModel },
            resolution: "approved_for_plan",
            reviewerNote: "",
          },
        ]);
      } catch (error) {
        showError(error.message);
      }
    })
  );
}

async function saveDecisions(decisions, { isBulk = false } = {}) {
  const payload = await postJSON(`/api/wizard/sessions/${state.session.runId}/decisions`, {
    decisions,
  });
  state.session = payload.session;
  if (!isBulk) reviewState.lastBatch = null;
  await refreshReview();
  return payload.batchId;
}

$("#review-queue").addEventListener("change", (event) => {
  const box = event.target.closest(".row-check");
  if (box) {
    if (box.checked) reviewState.checked.add(box.dataset.id);
    else reviewState.checked.delete(box.dataset.id);
    renderBulkBar();
    return;
  }
  const all = event.target.closest("#check-all");
  if (all) {
    if (all.checked) {
      for (const candidate of visibleQueueCandidates()) reviewState.checked.add(candidate.candidateId);
    } else {
      reviewState.checked = new Set();
    }
    renderBulkBar();
    renderQueue();
  }
});

$("#review-queue").addEventListener("click", async (event) => {
  const clear = event.target.closest(".dec-clear");
  if (clear) {
    clearError();
    try {
      const model = $("#review-model").value;
      const lane = $("#review-lane").value;
      const payload = await postJSON(`/api/wizard/sessions/${state.session.runId}/decisions/delete`, {
        decisionIds: [`${model}:${lane}:${clear.dataset.id}`],
      });
      state.session = payload.session;
      await refreshReview();
    } catch (error) {
      showError(error.message);
    }
    return;
  }
  const useRef = event.target.closest(".ref-use-section");
  if (useRef) {
    const select = useRef.closest("tr").querySelector(".dec-section");
    if (select) select.value = useRef.dataset.section;
    return;
  }
  const hint = event.target.closest(".hint-accept");
  if (hint) {
    // Prefill the relationship form from the hint; reviewer edits then saves.
    $("#group-kind").value = RELATIONSHIP_KINDS.includes(hint.dataset.kind) ? hint.dataset.kind : "other";
    $("#group-source").value = hint.dataset.source;
    $("#group-targets").value = hint.dataset.targets;
    $("#group-key").value = `${hint.dataset.source}-${hint.dataset.kind}`.toLowerCase();
    $("#group-key").scrollIntoView({ behavior: "smooth", block: "center" });
    return;
  }
  const button = event.target.closest(".dec-save");
  if (!button) return;
  clearError();
  try {
    const row = button.closest("tr");
    await saveDecisions([collectRowDecision($("#review-lane").value, row, button.dataset.id)]);
  } catch (error) {
    showError(error.message);
  }
});

/* ------------------------------------------------------------ bulk actions */

function checkedCandidates() {
  return visibleQueueCandidates().filter((c) => reviewState.checked.has(c.candidateId));
}

function renderBulkBar() {
  const lane = $("#review-lane").value;
  const checked = checkedCandidates();
  const n = checked.length;
  const disabled = n === 0 ? "disabled" : "";
  let controls = "";
  if (lane === "section") {
    controls = `
      ${sectionSelect("").replace('class="dec-section"', 'id="bulk-section"')}
      <button id="bulk-assign-section" class="primary" ${disabled}>Put ${n} checked row${n === 1 ? "" : "s"} in this section</button>`;
  } else if (lane === "price") {
    const exactChecked = checked.filter((c) => c.priceMatch === "exact").length;
    controls = `<button id="bulk-accept-exact" class="primary" ${exactChecked ? "" : "disabled"}>Use matched price for ${exactChecked} checked row${exactChecked === 1 ? "" : "s"}</button>`;
  } else if (lane === "status_nuance") {
    controls = `<button id="bulk-confirm-status" class="primary" ${disabled}>Confirm parsed status for ${n} checked</button>`;
  } else if (lane === "standard_equipment") {
    controls = `
      <button id="bulk-se-include" class="primary" ${disabled}>Include ${n} checked</button>
      <button id="bulk-se-exclude" class="ghost" ${disabled}>Leave out ${n} checked</button>`;
  } else if (lane === "copy_split") {
    controls = `<button id="bulk-accept-split" class="primary" ${disabled}>Accept script copy for ${n} checked</button>`;
  }
  if (!controls) {
    $("#bulk-bar").innerHTML = "";
    return;
  }
  const undo =
    reviewState.lastBatch && reviewState.lastBatch.queueKey === reviewState.queueKey
      ? `<button id="bulk-undo" class="ghost">Undo last bulk (${reviewState.lastBatch.count} row${reviewState.lastBatch.count === 1 ? "" : "s"})</button>`
      : "";
  $("#bulk-bar").innerHTML = `
    <span class="status-note"><b>${n}</b> checked</span>
    <button id="bulk-select-all" class="ghost">Select all filtered</button>
    <button id="bulk-select-none" class="ghost">Clear selection</button>
    ${controls}
    ${undo}`;
  bindBulk(lane);
}

function bindBulk(lane) {
  const model = $("#review-model").value;
  const base = (candidate) => ({
    model,
    lane,
    candidateId: candidate.candidateId,
    resolution: "approved_for_plan",
    reviewerNote: "bulk",
  });
  const on = (id, handler) => {
    const el = document.querySelector(id);
    if (el) el.addEventListener("click", handler);
  };
  const bulkSave = async (rows, builder) => {
    clearError();
    try {
      const decisions = rows.map(builder);
      if (!decisions.length) return;
      const batchId = await saveDecisions(decisions, { isBulk: true });
      reviewState.lastBatch = { batchId, count: decisions.length, queueKey: reviewState.queueKey };
      renderBulkBar();
    } catch (error) {
      showError(error.message);
    }
  };
  on("#bulk-select-all", () => {
    for (const candidate of visibleQueueCandidates()) reviewState.checked.add(candidate.candidateId);
    renderBulkBar();
    renderQueue();
  });
  on("#bulk-select-none", () => {
    reviewState.checked = new Set();
    renderBulkBar();
    renderQueue();
  });
  on("#bulk-assign-section", () => {
    const sectionId = $("#bulk-section").value;
    if (!sectionId) {
      showError("Pick a section for the checked rows first.");
      return;
    }
    bulkSave(checkedCandidates(), (candidate) => ({ ...base(candidate), action: "assign_section", payload: { sectionId } }));
  });
  on("#bulk-accept-exact", () =>
    bulkSave(
      checkedCandidates().filter((candidate) => candidate.priceMatch === "exact"),
      (candidate) => ({ ...base(candidate), action: "accept_exact_price", payload: {} })
    )
  );
  on("#bulk-confirm-status", () =>
    bulkSave(checkedCandidates(), (candidate) => ({ ...base(candidate), action: "confirm_status", payload: {} }))
  );
  on("#bulk-se-include", () =>
    bulkSave(checkedCandidates(), (candidate) => ({ ...base(candidate), action: "include_standard_equipment", payload: {} }))
  );
  on("#bulk-se-exclude", () =>
    bulkSave(checkedCandidates(), (candidate) => ({ ...base(candidate), action: "exclude_row", payload: {} }))
  );
  on("#bulk-accept-split", () =>
    bulkSave(checkedCandidates(), (candidate) => ({
      ...base(candidate),
      action: "split_copy",
      payload: {
        name: (candidate.proposedSplit || {}).name || "",
        description: (candidate.proposedSplit || {}).description || "",
        disclosure: (candidate.proposedSplit || {}).disclosure || "",
      },
    }))
  );
  on("#bulk-undo", async () => {
    clearError();
    try {
      const payload = await postJSON(`/api/wizard/sessions/${state.session.runId}/decisions/delete`, {
        batchId: reviewState.lastBatch.batchId,
      });
      state.session = payload.session;
      reviewState.lastBatch = null;
      await refreshReview();
    } catch (error) {
      showError(error.message);
    }
  });
}

/* -------------------------------------------------------------- model copy */

$("#copy-decisions-btn").addEventListener("click", async () => {
  clearError();
  try {
    const payload = await postJSON(`/api/wizard/sessions/${state.session.runId}/copy-decisions`, {
      fromModel: $("#copy-from-model").value,
      toModel: $("#review-model").value,
      overwrite: $("#copy-overwrite").checked,
    });
    state.session = payload.session;
    const lanes = Object.entries(payload.copiedByLane)
      .map(([lane, count]) => `${lane.replaceAll("_", " ")} ${count}`)
      .join(", ");
    $("#copy-report").textContent = `Copied ${payload.copied}${lanes ? ` (${lanes})` : ""}; skipped ${payload.skipped.length}.`;
    await refreshReview();
  } catch (error) {
    showError(error.message);
  }
});

$("#mark-complete-btn").addEventListener("click", async () => {
  clearError();
  try {
    const payload = await postJSON(`/api/wizard/sessions/${state.session.runId}/complete`, {});
    state.session = payload.session;
    $("#review-blockers").innerHTML = '<div class="status-note">Decisions complete for all selected targets.</div>';
    await refreshReview();
  } catch (error) {
    showError(error.message);
    reviewState.progress = await getJSON(`/api/wizard/sessions/${state.session.runId}/progress`);
    renderProgress();
    const model = $("#review-model").value;
    const blockers = (reviewState.progress.models[model] || {}).blockers || [];
    $("#review-blockers").innerHTML = blockers.length
      ? `<div class="empty-note">Blocking (${model}): ${blockers
          .slice(0, 20)
          .map((blocker) => escapeHtml(`${blocker.lane}:${blocker.candidateId || blocker.groupKey}`))
          .join(", ")}${blockers.length > 20 ? " …" : ""}</div>`
      : "";
  }
});

for (const id of ["#review-model", "#review-lane", "#review-source-section"]) {
  $(id).addEventListener("change", () => {
    if (id !== "#review-source-section") $("#review-source-section").value = "";
    refreshReview().catch((error) => showError(error.message));
  });
}
let reviewTimer = null;
$("#review-q").addEventListener("input", () => {
  clearTimeout(reviewTimer);
  reviewTimer = setTimeout(() => refreshReview().catch((error) => showError(error.message)), 250);
});

/* ------------------------------------------------------------------- init */

setStage("files");
loadFiles().catch((error) => showError(error.message));
