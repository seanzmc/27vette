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

const STAGES = ["files", "sheets", "candidates", "models", "review", "plan"];

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
  if (payload.selection) {
    // Returning to this stage after a selection: restore the reconciliation
    // panel (and its pending mandatory decisions) instead of hiding it.
    reloadReconciliation().catch(() => {});
  }
}

function renderModels() {
  const comparatorChoices = modelState.options.filter((m) => !m.isDefaultTarget);
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
    let verdict;
    if (entry.agrees) {
      verdict = '<span class="conf conf-high">matches workbook scaffold</span>';
    } else if (!entry.workbookHasScaffold) {
      verdict = `<span class="conf conf-medium">new model — no workbook variants yet; confirm the export's ${entry.exportVariants.length}</span>`;
    } else {
      verdict = `<span class="conf conf-low">disagrees — ${entry.exportOnly.length} export-only, ${entry.workbookOnly.length} workbook-only</span>`;
    }
    let actions = "";
    if (!entry.agrees) {
      if (entry.decision) {
        actions = `<div class="card-stats">
          <span class="conf conf-high">decided — ${escapeHtml(labelFor(ACTION_LABELS, entry.decision.action))} (${escapeHtml(labelFor(RESOLUTION_LABELS, entry.decision.resolution))})</span>
          <button class="ghost recon-clear" data-decision-id="${escapeHtml(entry.decision.decisionId)}">Clear</button>
        </div>`;
      } else {
        const explain = entry.workbookHasScaffold
          ? "The export and the workbook scaffold disagree. Pick one before decisions can complete:"
          : "This model has no variant rows in the workbook yet — that's expected for a new model. Confirm the export's variants:";
        actions = `<div class="card-stats">${escapeHtml(explain)}</div>
          <div class="sheet-actions">
            <button class="primary recon-accept" data-model="${escapeHtml(key)}">Accept the export's variants</button>
            <button class="ghost recon-question" data-model="${escapeHtml(key)}">Record a business question</button>
          </div>`;
      }
    }
    return `<div class="card"><div class="card-head"><span class="card-title">${escapeHtml(key)}</span>${verdict}</div>
      <div class="variant-chips">${rows}</div>${actions}</div>`;
  });
  $("#reconciliation").innerHTML = blocks.length
    ? `<h2 class="sub-h">Variant reconciliation</h2>
       <p class="hint">The export's variant columns vs the workbook's variant rows. A mismatch is a mandatory call — decide it here (it used to hide in the review lanes).</p>
       <div class="cards">${blocks.join("")}</div>
       <div class="sheet-actions"><button id="to-review-btn" class="primary">Start decision review</button></div>`
    : "";
  const toReview = $("#to-review-btn");
  if (toReview) toReview.addEventListener("click", () => enterReview());
  document.querySelectorAll(".recon-accept, .recon-question").forEach((button) =>
    button.addEventListener("click", async () => {
      clearError();
      const question = button.classList.contains("recon-question");
      try {
        await postJSON(`/api/wizard/sessions/${state.session.runId}/decisions`, {
          decisions: [
            {
              model: button.dataset.model,
              lane: "relationship",
              groupKey: "variant_reconciliation",
              action: question ? "needs_product_decision" : "confirm_export_variants",
              payload: {
                exportVariants: (models[button.dataset.model] || {}).exportVariants || [],
              },
              resolution: question ? "hold_for_question" : "approved_for_plan",
              reviewerNote: question ? "Variant lineup needs a business answer." : "",
            },
          ],
        });
        await reloadReconciliation();
      } catch (error) {
        showError(error.message);
      }
    })
  );
  document.querySelectorAll(".recon-clear").forEach((button) =>
    button.addEventListener("click", async () => {
      clearError();
      try {
        await postJSON(`/api/wizard/sessions/${state.session.runId}/decisions/delete`, {
          decisionIds: [button.dataset.decisionId],
        });
        await reloadReconciliation();
      } catch (error) {
        showError(error.message);
      }
    })
  );
}

async function reloadReconciliation() {
  modelState.reconciliation = await getJSON(
    `/api/wizard/sessions/${state.session.runId}/reconciliation`
  );
  renderReconciliation();
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
  needs_product_decision: [
    "Record business question",
    "Saves the open question into the plan report — no rule or row is written until it's answered.",
  ],
  confirm_export_variants: ["Accept export variants", "The export's variant lineup is the right one for this model."],
  split_copy: ["Set customer copy", "Name / description / fine print for the form."],
  confirm_status: ["Confirm as parsed", "The parsed availability status is right."],
  mark_unresolved_blocked: ["Can't resolve — block it", "Status can't be determined from the source."],
  classify_duplicate_source: ["Classify duplicate", "Same option or different by context?"],
  include_standard_equipment: ["Include as standard", "Shows as standard equipment for this model."],
  exclude_row: [
    "Leave out — don't write this row",
    "The row is not carried into the workbook. Nothing that already exists is deleted.",
  ],
  defer_item: ["Defer for later", "Named item to handle in the apply pass."],
  approve_presentation_rows: ["Approve rows", "Approves this sheet's presentation rows."],
};

const LANE_DESCRIPTIONS = {
  section: "Pick where each option lives in the form. Sections come from the workbook's section_master sheet — the same sections live models use. Skip — don't carry over saves without a section and drops the row from the plan.",
  price: "Settle every option's price. Filter by price state; single matches can be accepted wholesale. A typed reviewed $ overrides the discovered price. Rows you skipped in Section assignment don't need a price.",
  exclusive_group: "Group options the customer must pick only one of. Rarely needed for options already in a pick-one section (listed below) — the section already enforces it.",
  relationship: "Record workbook-safe option rules: Requires, Includes / auto-adds, or Not available with. Hints can prefill the form; save writes the relationship to the Pass C plan.",
  copy_split: "Names follow your comma rule: text before the first comma (LPO rows use the part between the first and second comma); the rest is description; footnote-numbered lines are fine print. Fix only the flagged exceptions — one-word names, duplicates, unmatched footnotes.",
  status_nuance: "Only rows with genuinely ambiguous availability symbols (□ upgradeable, standalone D dealer-install, unknown) — A/D is parsed as available automatically.",
  duplicate: "Same RPO on more than one source sheet in this ingest file — one option or context-distinct?",
  standard_equipment: "Rows without an orderable RPO, plus anything you assigned to a standard section. Rows that are available-to-order on this model (A statuses) are options, not standard equipment — they're excluded automatically.",
  interior_media_deferral: "Record named to-dos the wizard can't parse (interiors, colors, images) so the apply plan carries them as open items.",
  presentation: "Approve the form's skeleton for this model — steps, section display, order summary. Required before the model can go live.",
};

function labelFor(map, value) {
  const entry = map[value];
  return entry ? entry[0] : value.replaceAll("_", " ");
}

function normalizedStatusBase(raw) {
  return String(raw || "")
    .replace(/\d+$/, "")
    .replace(/[—–−]/g, "-")
    .replace(/\s+/g, "")
    .toUpperCase();
}

function titleFor(map, value) {
  const entry = map[value];
  return entry ? entry[1] : "";
}

const RELATIONSHIP_KIND_CHOICES = [
  {
    value: "requires",
    label: "Requires",
    help: "Source can be selected only when the target is also selected.",
  },
  {
    value: "includes",
    label: "Includes / auto-adds",
    help: "Selecting the source adds the target option automatically.",
  },
  {
    value: "not_available_with",
    label: "Not available with",
    help: "Source and target cannot be selected together.",
  },
];
const RELATIONSHIP_KINDS = RELATIONSHIP_KIND_CHOICES.map((choice) => choice.value);
const RELATIONSHIP_KIND_ALIASES = {
  only_available_with: "requires",
  requires_additional_equipment: "requires",
  included_with: "includes",
};
const RELATIONSHIP_KIND_LABELS = Object.fromEntries(RELATIONSHIP_KIND_CHOICES.map((choice) => [choice.value, choice.label]));

function canonicalRelationshipKind(kind) {
  const raw = String(kind || "").trim();
  return RELATIONSHIP_KINDS.includes(raw) ? raw : RELATIONSHIP_KIND_ALIASES[raw] || "";
}

function relationshipKindLabel(kind) {
  const canonical = canonicalRelationshipKind(kind);
  if (canonical) return RELATIONSHIP_KIND_LABELS[canonical];
  return kind ? `Needs manual handling: ${String(kind).replaceAll("_", " ")}` : "Needs manual handling";
}

function relationshipKindControl(current = "") {
  const selected = canonicalRelationshipKind(current);
  return `<div class="rel-kind-options" id="group-kind" role="radiogroup" aria-label="Relationship rule type">
    ${RELATIONSHIP_KIND_CHOICES.map(
      (choice) => `
        <label class="rel-kind-choice">
          <input type="radio" name="group-kind" value="${escapeHtml(choice.value)}"${choice.value === selected ? " checked" : ""}>
          <span><b>${escapeHtml(choice.label)}</b><small>${escapeHtml(choice.help)}</small></span>
        </label>`
    ).join("")}
  </div>`;
}

function selectedRelationshipKind() {
  const selected = document.querySelector('input[name="group-kind"]:checked');
  return selected ? selected.value : "";
}

function setRelationshipKind(kind) {
  const canonical = canonicalRelationshipKind(kind);
  document.querySelectorAll('input[name="group-kind"]').forEach((input) => {
    input.checked = input.value === canonical;
  });
  return canonical;
}

const reviewState = {
  payload: null,
  progress: null,
  checked: new Set(),
  queueKey: "",
  lastBatch: null, // {batchId, count, queueKey}
  lastBulkNote: "",
  splitShowAll: false,
};

function currentQueueKey() {
  return [
    $("#review-model").value,
    $("#review-lane").value,
    $("#review-q").value.trim(),
    $("#review-source-section").value,
    $("#review-decision-state").value,
    $("#review-price-state").value,
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
  const hasDecisionFilter = lane === "section" || lane === "price";
  $("#review-decision-state").classList.toggle("hidden", !hasDecisionFilter);
  if (hasDecisionFilter && $("#review-decision-state").value) {
    params.set("decisionState", $("#review-decision-state").value);
  }
  $("#review-price-state").classList.toggle("hidden", lane !== "price");
  if (lane === "price" && $("#review-price-state").value) params.set("priceMatch", $("#review-price-state").value);
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
    '<option value="">All source groups</option>' +
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
  $("#copy-from-label").textContent = select.value || others[0] || "";
  $("#copy-to-label").textContent = current;
}

$("#copy-from-model").addEventListener("change", () => {
  $("#copy-from-label").textContent = $("#copy-from-model").value;
});

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
    const workbookRpo = candidate.rpo || candidate.refOnlyRpo;
    const reference = ((reviewState.payload.workbookReference || {})[workbookRpo] || [])[0];
    const useReference =
      reference && reference.sectionId
        ? `<button class="ref-use-section ghost" data-section="${escapeHtml(reference.sectionId)}" title="${escapeHtml(reference.sectionName || reference.sectionId)}">Use ${escapeHtml(reference.modelKey)}'s section</button>`
        : "";
    controls = `${sectionSelect(payload.sectionId || "")}${useReference}
      <label class="dec-inline" title="Row is written but can't be picked — display/reference only."><input type="checkbox" class="dec-not-selectable" ${payload.selectable === false ? "checked" : ""}> not selectable</label>
      <label class="dec-inline" title="Row is written with active = false — hidden from the form until turned on."><input type="checkbox" class="dec-inactive" ${payload.active === false ? "checked" : ""}> inactive</label>`;
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
      <input class="dec-price-manual" type="number" step="0.01" placeholder="reviewed $" title="Overrides the discovered price — the plan writes this value." value="${payload.reviewedPrice ?? ""}">
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
    const explanations = (candidate.statuses || [])
      .filter((status) => {
        const flags = status.flags || [];
        const raw = normalizedStatusBase(status.raw);
        return (
          flags.includes("unknown_status_symbol") ||
          flags.includes("upgradeable_equipment_group_review") ||
          status.status === "unresolved" ||
          raw === "D"
        );
      })
      .map((status) => {
        const raw = normalizedStatusBase(status.raw);
        let why = "couldn't parse this symbol — needs a call";
        if (raw === "□") why = "□ upgradeable group — standard here, upgradeable elsewhere; confirm it reads as standard";
        else if (raw === "D") why = "dealer-installed nuance — parsed as available; confirm";
        return `<div class="cell-sub">“${escapeHtml(status.raw)}” on ${escapeHtml(status.modelCode)} ${escapeHtml(status.trim)} → parsed <b>${escapeHtml(status.status)}</b>; ${escapeHtml(why)}</div>`;
      })
      .join("");
    controls = `${explanations}${selectControl(
      "dec-status-action",
      ["confirm_status", "mark_unresolved_blocked"],
      decision ? decision.action : "confirm_status"
    )}`;
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
    <input class="dec-note" placeholder="note" title="Saved with the decision — shows on recorded decisions, the holds report, and the plan's holds list. Never written to the workbook." value="${escapeHtml(decision ? decision.reviewerNote : "")}">
    <button class="dec-save primary" data-id="${escapeHtml(candidate.candidateId)}">Save</button>
    ${decision ? '<span class="conf conf-high">saved</span>' : ""}`;
}

function collectRowDecision(lane, row, candidateId) {
  const resolution = row.querySelector(".dec-resolution").value;
  const reviewerNote = row.querySelector(".dec-note").value;
  let action = "";
  let payload = {};
  if (lane === "section") {
    const sectionId = row.querySelector(".dec-section").value;
    if (sectionId) {
      action = "assign_section";
      payload = { sectionId };
      if (row.querySelector(".dec-not-selectable").checked) payload.selectable = false;
      if (row.querySelector(".dec-inactive").checked) payload.active = false;
    } else if (resolution === "not_needed") {
      // Skip — don't carry over: valid without a section; the row stays out
      // of the plan and owes no price decision.
      action = "exclude_row";
    } else {
      throw new Error("Pick a section, or choose “Skip — don't carry over” to drop the row.");
    }
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
      const label = `${escapeHtml(relationshipKindLabel(hint.kind))}${hint.rpoTokens.length ? ` → ${escapeHtml(hint.rpoTokens.join(", "))}` : ""}`;
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
  const workbookRpo = candidate.rpo || candidate.refOnlyRpo;
  const rows = (reviewState.payload.workbookReference || {})[workbookRpo];
  if (!workbookRpo) return "";
  if (!rows || !rows.length) {
    return '<div class="cell-sub ref-line ref-new">New to workbook — no reference</div>';
  }
  const top = rows[0];
  const price = top.price ? ` · ${fmtPrice(Number(top.price))}` : "";
  const selectable = top.selectable === false ? " · not selectable" : "";
  const section = top.sectionName || top.sectionId || "no section";
  const more = rows.length > 1 ? ` (+${rows.length - 1} more)` : "";
  return `<div class="cell-sub ref-line">In workbook: <b>${escapeHtml(top.modelKey)}</b> “${escapeHtml(top.optionName || workbookRpo)}” · ${escapeHtml(section)}${price}${selectable}${more}</div>`;
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
  if (lane === "duplicate") {
    renderDuplicateLane();
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
    if (decision.action === "needs_product_decision") {
      return `Open question${payload.note ? `: ${payload.note}` : ""}`;
    }
    return `${relationshipKindLabel(payload.kind)}: ${payload.sourceRpo || ""} → ${(payload.targetRpos || []).join(", ")}${payload.note ? ` — ${payload.note}` : ""}`;
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

function exclusivePoolTable() {
  const sections = Object.fromEntries((reviewState.payload.sections || []).map((s) => [s.sectionId, s]));
  const sectionDecisions = reviewState.payload.sectionDecisions || {};
  const query = ($("#review-q").value || "").trim().toLowerCase();
  const pool = (reviewState.payload.candidates || []).filter(
    (candidate) =>
      candidate.rpo &&
      (!query || candidate.rpo.toLowerCase().includes(query) || candidate.description.toLowerCase().includes(query))
  );
  const rows = pool
    .map((candidate) => {
      const sectionId = sectionDecisions[candidate.candidateId] || "";
      const section = sections[sectionId];
      const single = section && String(section.selectionMode || "").startsWith("single");
      const sectionNote = section
        ? `${escapeHtml(section.sectionName)}${single ? ' <span class="conf conf-high">pick-one section already</span>' : ""}`
        : '<span class="cell-sub">no section yet</span>';
      return `
      <tr class="cand-row">
        <td><input type="checkbox" class="pool-check" data-rpo="${escapeHtml(candidate.rpo)}"></td>
        <td class="rpo">${escapeHtml(candidate.rpo)}</td>
        <td class="desc">${escapeHtml(candidate.description.split("\n")[0])}</td>
        <td>${sectionNote}</td>
      </tr>`;
    })
    .join("");
  return `<table class="cand"><thead><tr><th></th><th>RPO</th><th>Option</th><th>Assigned section</th></tr></thead><tbody>${rows}</tbody></table>`;
}

function groupFormFields(lane) {
  if (lane === "exclusive_group") {
    return `<input id="group-key" placeholder="exclusive group name (e.g. roof-panels)">`;
  }
  if (lane === "relationship") {
    return `
      <p class="hint rel-help">Choose the workbook rule this creates. If a phrase hint used a synonym, the wizard normalizes it to one of these three rule types before saving.</p>
      <input id="group-key" placeholder="relationship name (e.g. Z51-requires-E60)">
      ${relationshipKindControl()}
      <input id="group-source" placeholder="source RPO">
      <input id="group-targets" placeholder="target RPOs, comma-separated">`;
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
        <td class="desc">${escapeHtml(labelFor(ACTION_LABELS, decision.action))} · ${escapeHtml(groupPayloadSummary(decision))}</td>
        <td>${escapeHtml(labelFor(RESOLUTION_LABELS, decision.resolution))}</td>
        <td>${escapeHtml(decision.reviewerNote)}${decision.copiedFrom ? ` <span class="cell-sub">copied from ${escapeHtml(decision.copiedFrom)}</span>` : ""}</td>
        <td><button class="group-edit ghost" data-decision-id="${escapeHtml(decision.decisionId)}">Edit</button>
            <button class="group-clear ghost" data-decision-id="${escapeHtml(decision.decisionId)}">Clear</button></td>
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
  const pickOneSections = (reviewState.payload.sections || [])
    .filter((section) => String(section.selectionMode || "").startsWith("single"))
    .map((section) => section.sectionName);
  const exclusiveExtras =
    lane === "exclusive_group"
      ? `<p class="hint">Check the options that belong together, name the group, save. Options already in a <b>pick-one section</b> usually don't need an exclusive group — the section enforces it. Use the search box above to narrow the pool.</p>
         ${pickOneSections.length ? `<p class="hint">Pick-one sections in this workbook: <b>${pickOneSections.map(escapeHtml).join(", ")}</b>.</p>` : ""}
         ${exclusivePoolTable()}`
      : "";
  const deferralExtras =
    lane === "interior_media_deferral"
      ? `<p class="hint">This lane records named to-dos the wizard can't parse (Color &amp; Trim isn't ingested). Each recorded item is carried into the Pass C plan report as an open work item instead of silently missing.</p>
         <div class="cards">${(reviewState.payload.suggestedDeferrals || [])
           .map(
             (item) => `
             <div class="card"><div class="card-head"><span class="card-title">${escapeHtml(item.label)}</span></div>
               <div class="card-stats">${escapeHtml(item.why)}</div>
               <button class="primary defer-suggest" data-key="${escapeHtml(item.groupKey)}" data-kind="${escapeHtml(item.kind)}" data-label="${escapeHtml(item.label)}">Record this deferral</button>
             </div>`
           )
           .join("")}</div>`
      : "";
  const resolutionControl = lane === "relationship" ? "" : `<select id="group-resolution">${resolutionOptions("approved_for_plan")}</select>`;
  const saveLabel = lane === "exclusive_group" ? "Create group from checked options" : lane === "relationship" ? "Save relationship" : "Save decision";
  $("#review-queue").innerHTML = `
    ${exclusiveExtras}
    ${deferralExtras}
    <div class="group-form">
      ${groupFormFields(lane)}
      ${resolutionControl}
      <input id="group-note" placeholder="note">
      <button id="group-save" class="primary">${saveLabel}</button>
    </div>
    ${existing ? `<h2 class="sub-h">Recorded decisions</h2><table class="cand"><tbody>${existing}</tbody></table>` : ""}
    ${hintRows ? `<h2 class="sub-h">Candidates with relationship hints — click a hint to prefill the form</h2><table class="cand"><tbody>${hintRows}</tbody></table>` : ""}`;
  document.querySelectorAll(".defer-suggest").forEach((button) =>
    button.addEventListener("click", async () => {
      clearError();
      try {
        await saveDecisions([
          {
            model: $("#review-model").value,
            lane: "interior_media_deferral",
            groupKey: button.dataset.key,
            action: "defer_item",
            payload: { kind: button.dataset.kind, note: button.dataset.label },
            resolution: "approved_for_plan",
            reviewerNote: "",
          },
        ]);
      } catch (error) {
        showError(error.message);
      }
    })
  );
  $("#group-save").addEventListener("click", async () => {
    clearError();
    try {
      await saveDecisions([collectGroupDecision(lane)]);
    } catch (error) {
      showError(error.message);
    }
  });
  document.querySelectorAll(".group-clear").forEach((button) =>
    button.addEventListener("click", async () => {
      clearError();
      try {
        await postJSON(`/api/wizard/sessions/${state.session.runId}/decisions/delete`, {
          decisionIds: [button.dataset.decisionId],
        });
        await refreshReview();
      } catch (error) {
        showError(error.message);
      }
    })
  );
  document.querySelectorAll(".group-edit").forEach((button) =>
    button.addEventListener("click", () => {
      // Prefill the form from the recorded decision; saving under the same
      // name replaces it (decision ids are model:lane:groupKey).
      const decision = decisions.find((d) => d.decisionId === button.dataset.decisionId);
      if (!decision) return;
      const payload = decision.payload || {};
      $("#group-key").value = decision.groupKey;
      const resolution = $("#group-resolution");
      if (resolution) resolution.value = decision.resolution;
      $("#group-note").value = decision.reviewerNote || "";
      if (lane === "relationship") {
        setRelationshipKind(payload.kind || "");
        $("#group-source").value = payload.sourceRpo || "";
        $("#group-targets").value = (payload.targetRpos || []).join(", ");
      } else if (lane === "exclusive_group") {
        const members = new Set(payload.members || []);
        document.querySelectorAll(".pool-check").forEach((box) => {
          box.checked = members.has(box.dataset.rpo);
        });
      } else if (lane === "interior_media_deferral") {
        $("#deferral-kind").value = payload.kind || "";
      }
      $("#group-key").scrollIntoView({ behavior: "smooth", block: "center" });
    })
  );
}

function collectGroupDecision(lane) {
  const groupKey = $("#group-key").value.trim();
  if (!groupKey) throw new Error("Give the decision a name.");
  const base = {
    model: $("#review-model").value,
    lane,
    groupKey,
    resolution: lane === "relationship" ? "approved_for_plan" : $("#group-resolution").value,
    reviewerNote: $("#group-note").value,
  };
  const csv = (value) =>
    value
      .split(",")
      .map((token) => token.trim().toUpperCase())
      .filter(Boolean);
  if (lane === "exclusive_group") {
    const members = [...document.querySelectorAll(".pool-check:checked")].map((box) => box.dataset.rpo);
    if (members.length < 2) throw new Error("Check at least two options for the group.");
    return { ...base, action: "create_exclusive_group", payload: { members } };
  }
  if (lane === "relationship") {
    const kind = selectedRelationshipKind();
    const sourceRpo = $("#group-source").value.trim().toUpperCase();
    const targetRpos = csv($("#group-targets").value);
    if (!kind || !sourceRpo || !targetRpos.length) {
      throw new Error("Relationship needs one of the three rule types, a source RPO, and at least one target RPO.");
    }
    return { ...base, action: "create_relationship_candidate", payload: { kind, sourceRpo, targetRpos } };
  }
  const kind = $("#deferral-kind").value;
  if (!kind) throw new Error("Pick a deferral kind.");
  return { ...base, action: "defer_item", payload: { kind, note: $("#group-note").value } };
}

function renderDuplicateLane() {
  const groups = reviewState.payload.duplicateGroups || [];
  const decisions = reviewState.payload.decisions || [];
  const decidedByRpo = Object.fromEntries(decisions.map((decision) => [decision.groupKey, decision]));
  const byId = Object.fromEntries((reviewState.payload.candidates || []).map((c) => [c.candidateId, c]));
  if (!groups.length) {
    $("#review-queue").innerHTML =
      '<div class="empty-note">No in-file RPO collisions for this model — the same RPO never appears on more than one source sheet. Nothing to do here.</div>';
    return;
  }
  const blocks = groups
    .map((group) => {
      const decision = decidedByRpo[group.rpo];
      const rows = group.candidateIds
        .map((id) => byId[id])
        .filter(Boolean)
        .map(
          (candidate) => `
          <tr class="cand-row">
            <td class="rpo">${escapeHtml(candidate.rpo)}</td>
            <td class="desc">${escapeHtml(candidate.description)}
              <div class="cell-sub">${escapeHtml(candidate.sheetName)} · row ${candidate.rowIndex}</div></td>
            <td><div class="stchips">${statusChips(candidate)}</div></td>
          </tr>`
        )
        .join("");
      return `
      <div class="pres-sheet">
        <h2 class="sub-h">${escapeHtml(group.rpo)} appears on ${group.sheets.length} sheets
          ${decision ? '<span class="conf conf-high">decided</span>' : '<span class="conf conf-low">needs a call</span>'}</h2>
        <table class="cand"><tbody>${rows}</tbody></table>
        <div class="group-form">
          ${selectControl("dup-class", ["same_option", "distinct_by_context"], decision ? (decision.payload || {}).classification : "", "— same option or different? —").replace('class="dup-class"', `class="dup-class" data-rpo="${escapeHtml(group.rpo)}"`)}
          <button class="primary dup-save" data-rpo="${escapeHtml(group.rpo)}">Save</button>
          ${decision ? `<button class="ghost dup-clear" data-decision-id="${escapeHtml(decision.decisionId)}">Clear</button>` : ""}
        </div>
      </div>`;
    })
    .join("");
  $("#review-queue").innerHTML = `
    <p class="hint">Same RPO on more than one source sheet <b>in this ingest file</b>. Decide whether the rows describe one option (rows merge in the plan) or context-distinct entries. Workbook matches show in the reference lines of other lanes — that's separate.</p>
    ${blocks}`;
  document.querySelectorAll(".dup-clear").forEach((button) =>
    button.addEventListener("click", async () => {
      clearError();
      try {
        await postJSON(`/api/wizard/sessions/${state.session.runId}/decisions/delete`, {
          decisionIds: [button.dataset.decisionId],
        });
        await refreshReview();
      } catch (error) {
        showError(error.message);
      }
    })
  );
  document.querySelectorAll(".dup-save").forEach((button) =>
    button.addEventListener("click", async () => {
      clearError();
      try {
        const rpo = button.dataset.rpo;
        const select = document.querySelector(`.dup-class[data-rpo="${CSS.escape(rpo)}"]`);
        if (!select.value) throw new Error("Pick same option or different by context first.");
        await saveDecisions([
          {
            model: $("#review-model").value,
            lane: "duplicate",
            groupKey: rpo,
            action: "classify_duplicate_source",
            payload: { classification: select.value },
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

const PRESENTATION_SHEET_INFO = {
  runtime_steps: ["Form steps", "The ordered steps of the build form (Paint, Wheels, …)."],
  section_presentation: ["Section display", "How each section renders inside its step (labels, order, behavior)."],
  context_section_master: ["Context sections", "Body-style / trim chooser sections at the top of the form."],
  order_summary_sections: ["Order summary sections", "The buckets on the final order summary."],
  step_order_summary_map: ["Step → summary mapping", "Which step's choices land in which summary bucket."],
};

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
      const [friendly, purpose] = PRESENTATION_SHEET_INFO[sheet] || [sheet, ""];
      return `
      <div class="pres-sheet">
        <h2 class="sub-h">${escapeHtml(friendly)} <span class="cell-sub">(${escapeHtml(sheet)})</span> ${decided ? '<span class="conf conf-high">approved</span>' : `<span class="conf conf-low">${proposals.length} template rows pending</span>`}</h2>
        <div class="cell-sub">${escapeHtml(purpose)}</div>
        <table class="cand pres-table"><thead>${header}</thead><tbody>${rows}</tbody></table>
        <button class="primary pres-approve" data-sheet="${escapeHtml(sheet)}">Approve checked rows for ${escapeHtml(friendly)}</button>
      </div>`;
    })
    .join("");
  $("#review-queue").innerHTML = `
    <p class="hint">This lane builds the form's skeleton for the new model — steps, section display, and the order summary. It's a hard go-live requirement: the runtime refuses a promoted model without these rows. Everything is prefilled from <b>${escapeHtml(prefill.templateModel)}</b>'s live rows — edit any cell, uncheck rows to drop, then approve each sheet.</p>
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
    const canonicalKind = setRelationshipKind(hint.dataset.kind);
    $("#group-source").value = hint.dataset.source;
    $("#group-targets").value = hint.dataset.targets;
    $("#group-key").value = `${hint.dataset.source}-${canonicalKind || hint.dataset.kind}`.toLowerCase();
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
    const refModel = ((modelState.selection || {}).comparators || {})[$("#review-model").value] || "";
    const withRef = checked.filter(
      (c) => ((((reviewState.payload || {}).workbookReference || {})[c.rpo || c.refOnlyRpo] || [])[0] || {}).sectionId
    ).length;
    const refButton = refModel
      ? `<button id="bulk-ref-section" class="ghost" ${withRef ? "" : "disabled"} title="Each checked row takes the section its RPO already has on ${escapeHtml(refModel)} in the workbook. Rows without a match are left undecided. Every row stays editable afterwards.">Use ${escapeHtml(refModel)}'s section for ${withRef} of ${n} checked</button>`
      : "";
    controls = `
      ${sectionSelect("").replace('class="dec-section"', 'id="bulk-section"')}
      <button id="bulk-assign-section" class="primary" ${disabled}>Put ${n} checked row${n === 1 ? "" : "s"} in this section</button>
      <button id="bulk-section-skip" class="ghost" ${disabled}>Skip — don't carry over ${n} checked</button>
      ${refButton}`;
  } else if (lane === "price") {
    // Single-price matches are safe to accept wholesale — no checking needed
    // (still one batch, still undoable). Checked rows narrow it if any.
    const pool = n ? checked : visibleQueueCandidates().filter((c) => !decisionFor(c.candidateId));
    const exactCount = pool.filter((c) => c.priceMatch === "exact").length;
    controls = `<button id="bulk-accept-exact" class="primary" ${exactCount ? "" : "disabled"}>Accept ${exactCount} single-price match${exactCount === 1 ? "" : "es"} ${n ? "(checked)" : "(all filtered, undecided)"}</button>`;
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
  const note =
    reviewState.lastBulkNote && reviewState.lastBatch && reviewState.lastBatch.queueKey === reviewState.queueKey
      ? `<span class="status-note">${escapeHtml(reviewState.lastBulkNote)}</span>`
      : "";
  $("#bulk-bar").innerHTML = `
    <span class="status-note"><b>${n}</b> checked <span class="cell-sub">(header checkbox selects all filtered)</span></span>
    ${controls}
    ${undo}
    ${note}`;
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
  const bulkSave = async (rows, builder, note = "") => {
    clearError();
    try {
      const decisions = rows.map(builder);
      if (!decisions.length) return;
      const batchId = await saveDecisions(decisions, { isBulk: true });
      reviewState.lastBatch = { batchId, count: decisions.length, queueKey: reviewState.queueKey };
      reviewState.lastBulkNote = note;
      renderBulkBar();
    } catch (error) {
      showError(error.message);
    }
  };
  on("#bulk-assign-section", () => {
    const sectionId = $("#bulk-section").value;
    if (!sectionId) {
      showError("Pick a section for the checked rows first.");
      return;
    }
    bulkSave(checkedCandidates(), (candidate) => ({ ...base(candidate), action: "assign_section", payload: { sectionId } }));
  });
  on("#bulk-ref-section", () => {
    const checked = checkedCandidates();
    const rows = checked
      .map((candidate) => ({
        candidate,
        ref: (((reviewState.payload || {}).workbookReference || {})[candidate.rpo || candidate.refOnlyRpo] || [])[0],
      }))
      .filter((entry) => entry.ref && entry.ref.sectionId);
    bulkSave(
      rows,
      ({ candidate, ref }) => ({
        ...base(candidate),
        action: "assign_section",
        payload: { sectionId: ref.sectionId },
      }),
      `${rows.length} assigned from the reference model · ${checked.length - rows.length} left undecided (no workbook match)`
    );
  });
  on("#bulk-section-skip", () => {
    bulkSave(
      checkedCandidates(),
      (candidate) => ({
        ...base(candidate),
        action: "exclude_row",
        payload: {},
        resolution: "not_needed",
        reviewerNote: "bulk skip",
      }),
      "Skipped rows stay out of the plan and do not need price decisions."
    );
  });
  on("#bulk-accept-exact", () => {
    const checked = checkedCandidates();
    const pool = checked.length
      ? checked
      : visibleQueueCandidates().filter((candidate) => !decisionFor(candidate.candidateId));
    bulkSave(
      pool.filter((candidate) => candidate.priceMatch === "exact"),
      (candidate) => ({ ...base(candidate), action: "accept_exact_price", payload: {} })
    );
  });
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
    $("#review-blockers").innerHTML = '<div class="status-note">Decisions complete for all selected targets — build the apply plan when ready.</div>';
    $("#to-plan-btn").classList.remove("hidden");
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

for (const id of ["#review-model", "#review-lane", "#review-source-section", "#review-decision-state", "#review-price-state"]) {
  $(id).addEventListener("change", () => {
    if (id === "#review-model" || id === "#review-lane") {
      $("#review-source-section").value = "";
      $("#review-decision-state").value = "";
      $("#review-price-state").value = "";
    }
    refreshReview().catch((error) => showError(error.message));
  });
}
let reviewTimer = null;
$("#review-q").addEventListener("input", () => {
  clearTimeout(reviewTimer);
  reviewTimer = setTimeout(() => refreshReview().catch((error) => showError(error.message)), 250);
});

/* ------------------------------------------------------------- stage: plan */

function planBlock(title, entries, formatter) {
  if (!entries || !entries.length) return "";
  return `<h2 class="sub-h">${escapeHtml(title)}</h2><ul class="plan-list">${entries.map((e) => `<li>${formatter(e)}</li>`).join("")}</ul>`;
}

function renderPlan(detail) {
  const plan = detail.plan;
  const dryRun = detail.dryRun || {};
  const report = plan.report;
  const sheets = Object.entries(report.perSheetCounts)
    .map(
      ([sheet, counts]) =>
        `<tr class="cand-row"><td class="rpo">${escapeHtml(sheet)}</td><td>${escapeHtml(
          Object.entries(counts)
            .map(([action, count]) => `${action.replaceAll("_", " ")} ${count}`)
            .join(" · ")
        )}</td></tr>`
    )
    .join("");
  const stageChip = (label, entry) =>
    `<span class="sum-chip ${entry && entry.ok ? "sum-exact" : "sum-warn"}"><b>${escapeHtml(label)}</b>: ${escapeHtml((entry || {}).status || "—")}${entry && entry.errors && entry.errors.length ? ` — ${escapeHtml(entry.errors[0])}` : ""}</span>`;
  $("#plan-summary").innerHTML = `
    <div class="summary">
      <span class="sum-chip ${plan.valid ? "sum-exact" : "sum-warn"}"><b>plan ${plan.valid ? "valid" : "has blockers"}</b></span>
      <span class="sum-chip"><b>${plan.stage1Count}</b> scaffolding ops</span>
      <span class="sum-chip"><b>${plan.stage2Count}</b> data ops</span>
      ${stageChip("dry run: live check", dryRun.stage1)}
      ${stageChip("dry run: scratch apply", dryRun.stage1Scratch)}
      ${stageChip("dry run: data + schema", dryRun.stage2)}
      ${detail.approval ? `<span class="sum-chip sum-exact"><b>approved by ${escapeHtml(detail.approval.approvedBy)}</b> ${escapeHtml(detail.approval.approvedAt)}</span>` : ""}
    </div>
    <table class="cand"><thead><tr><th>Sheet</th><th>Ops</th></tr></thead><tbody>${sheets}</tbody></table>
    ${planBlock("Scaffold rows cleared (clean reprocess)", Object.entries(report.clearedRows), ([sheet, count]) => `${escapeHtml(sheet)}: ${count} rows replaced`)}
    ${planBlock("Script splits carried unreviewed", Object.entries(report.unreviewedSplits), ([model, rpos]) => `${escapeHtml(model)}: ${rpos.length} options (${escapeHtml(rpos.slice(0, 10).join(", "))}${rpos.length > 10 ? "…" : ""})`)}
    ${planBlock("Holds — answers still owed", report.holds, (h) => `${escapeHtml(h.model)} · ${escapeHtml(h.decisionId)} — ${escapeHtml(h.note)}`)}
    ${planBlock("Deferred work items", report.deferrals, (d) => `${escapeHtml(d.model)} · ${escapeHtml(d.groupKey)}`)}
    ${planBlock("Gaps", report.gaps, (g) => `[${escapeHtml(g.kind.replaceAll("_", " "))}] ${escapeHtml(g.model)}: ${escapeHtml(g.detail)}`)}`;
  $("#approve-plan-btn").disabled = !(state.session.state === "plan_built");
  $("#plan-status").textContent =
    state.session.state === "plan_approved"
      ? "Approved — ready for the Pass D apply step."
      : state.session.state === "plan_built"
        ? "Dry run clean — approve to sign off for apply."
        : "Plan has blockers or the dry run failed; fix and rebuild.";
}

async function buildPlan() {
  clearError();
  const button = $("#to-plan-btn");
  button.disabled = true;
  button.textContent = "Building plan…";
  try {
    const payload = await postJSON(`/api/wizard/sessions/${state.session.runId}/plan`, {});
    state.session = payload.session;
    renderPlan({ plan: payload.plan, dryRun: payload.dryRun, approval: null });
    setStage("plan");
  } catch (error) {
    showError(error.message);
  } finally {
    button.disabled = false;
    button.textContent = "Build apply plan";
  }
}

$("#to-plan-btn").addEventListener("click", buildPlan);
$("#rebuild-plan-btn").addEventListener("click", buildPlan);
$("#back-to-review").addEventListener("click", () => setStage("review"));
$("#approve-plan-btn").addEventListener("click", async () => {
  clearError();
  try {
    const payload = await postJSON(`/api/wizard/sessions/${state.session.runId}/plan/approve`, {
      approver: $("#plan-approver").value,
    });
    state.session = payload.session;
    const detail = await getJSON(`/api/wizard/sessions/${state.session.runId}/plan`);
    renderPlan(detail);
  } catch (error) {
    showError(error.message);
  }
});

/* ------------------------------------------------------------------- init */

setStage("files");
loadFiles().catch((error) => showError(error.message));
