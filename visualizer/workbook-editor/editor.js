import { h, render } from "preact";
import { useEffect, useMemo, useState } from "preact/hooks";
import htm from "htm";

const html = htm.bind(h);
const PAGE_SIZE = 100;
const DEFAULT_VISIBLE_COLUMN_COUNT = 8;
const VISIBLE_COLUMNS_STORAGE_KEY = "corvetteWorkbookEditor.visibleColumns.v1";
const COLLATOR = new Intl.Collator(undefined, { numeric: true, sensitivity: "base" });

function defaultVisibleColumns(headers) {
  return headers.slice(0, Math.min(DEFAULT_VISIBLE_COLUMN_COUNT, headers.length));
}

function readVisibleColumns(sheetName, headers) {
  try {
    const parsed = JSON.parse(localStorage.getItem(VISIBLE_COLUMNS_STORAGE_KEY) || "{}");
    const stored = parsed && typeof parsed === "object" && !Array.isArray(parsed) ? parsed : {};
    const cols = Array.isArray(stored[sheetName]) ? stored[sheetName] : [];
    const valid = cols.filter((c) => headers.includes(c));
    return valid.length ? valid : defaultVisibleColumns(headers);
  } catch {
    return defaultVisibleColumns(headers);
  }
}

function writeVisibleColumns(sheetName, cols) {
  try {
    const parsed = JSON.parse(localStorage.getItem(VISIBLE_COLUMNS_STORAGE_KEY) || "{}");
    const stored = parsed && typeof parsed === "object" && !Array.isArray(parsed) ? parsed : {};
    stored[sheetName] = cols;
    localStorage.setItem(VISIBLE_COLUMNS_STORAGE_KEY, JSON.stringify(stored));
  } catch {
    // Column preferences are local convenience state; ignore storage failures.
  }
}

async function fetchJson(url) {
  const res = await fetch(url);
  const body = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(body.error || `${url} -> HTTP ${res.status}`);
  return body;
}

async function postJson(url, body) {
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const data = await res.json().catch(() => ({}));
  return { status: res.status, data };
}

function fmt(v) {
  if (v === null || v === undefined || v === "") return html`<span class="dim">—</span>`;
  if (v === true) return "True";
  if (v === false) return "False";
  return String(v);
}

const isBlank = (v) => v === null || v === undefined || v === "";

function rowIdentity(row, workbookIndex, keyCols) {
  if (keyCols.length && keyCols.every((col) => !isBlank(row[col]))) {
    return `key:${keyCols.map((col) => `${col}=${String(row[col])}`).join("|")}`;
  }
  return `row:${workbookIndex ?? ""}`;
}

function compareCellValues(a, b) {
  const aBlank = isBlank(a);
  const bBlank = isBlank(b);
  if (aBlank && bBlank) return 0;
  if (aBlank) return 1;
  if (bBlank) return -1;
  if (typeof a === "number" && typeof b === "number") return a - b;
  if (typeof a === "boolean" && typeof b === "boolean") return Number(a) - Number(b);
  return COLLATOR.compare(String(a), String(b));
}

/* ── domain helpers ───────────────────────────────────────── */

function modelsOfSheet(data, sheetName) {
  return data.models.map((m) => m.key)
    .filter((k) => (data.modelSheets[k] || []).some((e) => e.sheet === sheetName));
}

function sheetOfFamily(data, modelKey, family) {
  const entry = (data.modelSheets[modelKey] || []).find((e) => e.family === family);
  return entry ? entry.sheet : null;
}

function refOptions(data, sheetName, refKind) {
  const models = modelsOfSheet(data, sheetName);
  const dom = data.referenceDomains;
  const union = (byModel, label) => {
    const seen = new Set();
    const out = [];
    for (const m of models) {
      for (const item of byModel[m] || []) {
        if (seen.has(item.id)) continue;
        seen.add(item.id);
        out.push({ value: item.id, label: label(item) });
      }
    }
    return out;
  };
  switch (refKind) {
    case "sections":
      return dom.sections.map((s) => ({ value: s.id, label: `${s.id} — ${s.name}` }));
    case "variants":
      return union(dom.variantsByModel, (v) => `${v.id} — ${v.name || ""}`);
    case "options":
      return union(dom.optionsByModel, (o) => `${o.rpo || "—"} — ${o.name || o.id}`);
    case "rule_groups":
      return union(dom.ruleGroupsByModel, (g) => g.id);
    case "exclusive_groups":
      return union(dom.exclusiveGroupsByModel, (g) => g.id);
    case "interiors":
      return union(dom.interiorsByModel, (i) => `${i.id} — ${i.name || ""}`);
    default:
      return [];
  }
}

/* ── structured field input — no free text for constrained cols ── */

function FieldInput({ data, metaEntry, sheetName, col, value, onChange, disabled }) {
  const enums = metaEntry.enums?.[col];
  const type = metaEntry.types?.[col];
  const ref = metaEntry.refs?.[col];
  if (enums) {
    return html`<select disabled=${disabled} value=${value ?? ""}
      onChange=${(e) => onChange(e.target.value === "" ? null : e.target.value)}>
      ${enums.map((v) => html`<option value=${v} key=${v}>${v === "" ? "(blank)" : v}</option>`)}
      ${!enums.includes("") && html`<option value="" hidden>(unset)</option>`}
    </select>`;
  }
  if (ref) {
    const opts = refOptions(data, sheetName, ref);
    return html`<select disabled=${disabled} value=${value ?? ""}
      onChange=${(e) => onChange(e.target.value === "" ? null : e.target.value)}>
      <option value="">(blank)</option>
      ${opts.map((o) => html`<option value=${o.value} key=${o.value}>${o.label}</option>`)}
    </select>`;
  }
  if (type === "bool") {
    const current = value === true ? "True" : value === false ? "False" : "";
    return html`<select disabled=${disabled} value=${current}
      onChange=${(e) => onChange(e.target.value === "" ? null : e.target.value === "True")}>
      <option value="">(blank)</option>
      <option value="True">True</option>
      <option value="False">False</option>
    </select>`;
  }
  if (type === "int") {
    return html`<input type="number" disabled=${disabled} value=${value ?? ""}
      onInput=${(e) => onChange(e.target.value === "" ? null : Number(e.target.value))} />`;
  }
  return html`<input type="text" disabled=${disabled} value=${value ?? ""}
    onInput=${(e) => onChange(e.target.value)} />`;
}

/* ── row add/edit form ────────────────────────────────────── */

function RowForm({ data, sheetName, mode, initial, onQueue, onCancel }) {
  const metaEntry = data.sheets.find((s) => s.name === sheetName);
  const headers = metaEntry.headers;
  const keyCols = metaEntry.keyCols || [];
  const [draft, setDraft] = useState(() => ({ ...initial }));
  const set = (col, v) => setDraft((d) => ({ ...d, [col]: v }));

  const save = () => {
    for (const k of keyCols) {
      if (isBlank(draft[k])) { alert(`Key field required: ${k}`); return; }
    }
    if (mode === "add") {
      const row = {};
      headers.forEach((c) => { row[c] = draft[c] ?? null; });
      onQueue({ action: "add", sheet: sheetName,
                key: Object.fromEntries(keyCols.map((k) => [k, draft[k]])), row });
    } else {
      const changed = {}; const old = {};
      headers.forEach((c) => {
        if (keyCols.includes(c)) return;
        if ((draft[c] ?? null) !== (initial[c] ?? null)) {
          changed[c] = draft[c] ?? null;
          old[c] = initial[c] ?? null;
        }
      });
      if (!Object.keys(changed).length) { onCancel(); return; }
      onQueue({ action: "update", sheet: sheetName,
                key: Object.fromEntries(keyCols.map((k) => [k, initial[k]])),
                row: changed, _old: old });
    }
    onCancel();
  };

  return html`<div class="editform">
    <div class="editform-head">
      <strong>${mode === "add" ? "Add Row" : "Edit Row"} — ${sheetName}</strong>
      <button class="btn ghost" onClick=${onCancel}>✕</button>
    </div>
    <div class="fields">
      ${headers.map((col) => html`<label key=${col}>
        <span class=${keyCols.includes(col) ? "key" : ""}>${col}${keyCols.includes(col) ? " *" : ""}</span>
        <${FieldInput} data=${data} metaEntry=${metaEntry} sheetName=${sheetName} col=${col}
          value=${draft[col]} onChange=${(v) => set(col, v)}
          disabled=${keyCols.includes(col) && mode === "edit"} />
      </label>`)}
    </div>
    <div class="formactions">
      <button class="btn primary" onClick=${save}>
        ${mode === "add" ? "Queue Add" : "Queue Update"}
      </button>
      <button class="btn" onClick=${onCancel}>Cancel</button>
    </div>
  </div>`;
}

/* ── Form Structure tab (read-only, unchanged from Phase 1) ── */

function ModelCards({ models }) {
  return html`<div class="cards">
    ${models.map((m, i) => html`
      <div class=${m.active ? "card active" : "card"} key=${m.key}>
        <div class="name">${m.label}<span class="ord">#${m.displayOrder ?? i + 1}</span></div>
        <div class="badges">
          <span class=${m.active ? "badge green" : "badge"}>${m.active ? "Active" : "Scaffold"}</span>
          ${m.promoted && html`<span class="badge blue">Runtime</span>`}
          ${m.defaultModel && html`<span class="badge amber">Default</span>`}
        </div>
      </div>`)}
  </div>`;
}

function stepSections(data, modelKey, stepKey) {
  const ctx = data.contextSections
    .filter((c) => c.modelKey === modelKey && c.stepKey === stepKey)
    .map((c) => ({ id: c.sectionId, label: c.name, shared: false }));
  const pres = data.sectionPresentation
    .filter((p) => p.modelKey === modelKey && p.stepKey === stepKey)
    .sort((a, b) => (a.order || 0) - (b.order || 0))
    .map((p) => {
      const master = data.sections.find((s) => s.sectionId === p.sectionId);
      return { id: p.sectionId, label: p.label || (master && master.name) || p.sectionId, shared: false };
    });
  const seen = new Set([...ctx, ...pres].map((s) => s.id));
  const shared = data.sections
    .filter((s) => s.stepKey === stepKey && !seen.has(s.sectionId))
    .map((s) => ({ id: s.sectionId, label: s.name, shared: true }));
  return [...ctx, ...pres, ...shared];
}

function StructureTab({ data, modelKey, setModelKey }) {
  const steps = data.steps.filter((s) => s.modelKey === modelKey);
  return html`
    <section>
      <h2 class="sec">Model Registry (model_master · model_registry_promotion)</h2>
      <${ModelCards} models=${data.models} />
    </section>
    <section>
      <h2 class="sec">Runtime Steps & Sections (runtime_steps · section_presentation)</h2>
      <div class="pills">
        ${data.models.map((m) => html`
          <button
            class=${"pill" + (m.key === modelKey ? " on" : "") + (m.active ? "" : " scaffold")}
            onClick=${() => setModelKey(m.key)} key=${m.key}
          >${m.label}</button>`)}
      </div>
      ${steps.length === 0
        ? html`<p class="note">No workbook-owned runtime steps for this model — runtime_steps has no active rows for “${modelKey}”.</p>`
        : html`<div class="steps">
            ${steps.map((s) => {
              const secs = stepSections(data, modelKey, s.stepKey);
              return html`<div class="step" key=${s.stepKey}>
                <span class="num">${s.order}</span>
                <div>
                  <div class="label">${s.label}</div>
                  <div class="key mono">${s.stepKey}</div>
                </div>
                <div class="secs">
                  ${secs.length === 0
                    ? html`<span class="note">no sections (computed)</span>`
                    : secs.map((sec) => html`
                        <span class=${sec.shared ? "chip shared" : "chip"} title=${sec.id} key=${sec.id}>
                          ${sec.label}
                        </span>`)}
                </div>
              </div>`;
            })}
          </div>`}
    </section>`;
}

/* ── Sheet Browser tab ────────────────────────────────────── */

function SheetTable({ data, name, onQueue, initialQuery, focusTs, onFocusConsumed }) {
  const [sheet, setSheet] = useState(null);
  const [error, setError] = useState(null);
  const [query, setQuery] = useState("");
  const [page, setPage] = useState(0);
  const [openRowId, setOpenRowId] = useState(null);
  const [editing, setEditing] = useState(null); // {mode, initial, rowId}
  const [visibleCols, setVisibleCols] = useState([]);
  const [sort, setSort] = useState({ col: null, dir: null });

  useEffect(() => {
    setSheet(null); setError(null); setQuery(""); setPage(0); setOpenRowId(null); setEditing(null);
    setVisibleCols([]); setSort({ col: null, dir: null });
    fetchJson(`/api/sheet/${encodeURIComponent(name)}`)
      .then((payload) => {
        setSheet(payload);
        setVisibleCols(readVisibleColumns(name, payload.headers));
      })
      .catch((e) => setError(e.message));
  }, [name]);

  useEffect(() => {
    if (!focusTs || !initialQuery) return;
    setQuery(initialQuery);
    setPage(0);
    setOpenRowId(null);
    if (onFocusConsumed) onFocusConsumed();
  }, [focusTs]);

  useEffect(() => {
    if (!sheet || visibleCols.length === 0) return;
    writeVisibleColumns(name, visibleCols);
  }, [name, sheet, visibleCols]);

  const meta = data.sheets.find((s) => s.name === name) || {};
  const keyCols = meta.keyCols || [];
  const editable = meta.readOnly === false;
  const isOptionsFamily = meta.family === "options";
  const rowOrder = useMemo(() => {
    const order = new Map();
    if (sheet) sheet.rows.forEach((row, index) => order.set(row, index));
    return order;
  }, [sheet]);
  const rowIdFor = (row) => rowIdentity(row, rowOrder.get(row), keyCols);
  const filtered = useMemo(() => {
    if (!sheet) return [];
    const q = query.trim().toLowerCase();
    if (!q) return sheet.rows;
    return sheet.rows.filter((r) =>
      Object.values(r).some((v) => String(v ?? "").toLowerCase().includes(q)),
    );
  }, [sheet, query]);
  const sortedRows = useMemo(() => {
    if (!sort.col || !sort.dir) return filtered;
    return filtered
      .map((row) => ({ row, originalIndex: rowOrder.get(row) ?? 0 }))
      .sort((a, b) => {
        const cmp = compareCellValues(a.row[sort.col], b.row[sort.col]);
        if (cmp !== 0) return sort.dir === "asc" ? cmp : -cmp;
        return a.originalIndex - b.originalIndex;
      })
      .map((item) => item.row);
  }, [filtered, rowOrder, sort.col, sort.dir]);

  const pages = Math.max(1, Math.ceil(sortedRows.length / PAGE_SIZE));
  const safePage = Math.min(page, pages - 1);
  const rows = sortedRows.slice(safePage * PAGE_SIZE, safePage * PAGE_SIZE + PAGE_SIZE);
  const cols = sheet ? visibleCols.filter((c) => sheet.headers.includes(c)) : [];
  const extra = sheet ? sheet.headers.length - cols.length : 0;
  const setColumns = (cols) => {
    if (!sheet) return;
    const valid = cols.filter((c) => sheet.headers.includes(c));
    setVisibleCols(valid.length ? valid : defaultVisibleColumns(sheet.headers));
  };
  const toggleColumn = (col) => {
    if (!sheet) return;
    const selected = new Set(cols);
    if (selected.has(col)) {
      if (selected.size === 1) return;
      selected.delete(col);
    } else {
      selected.add(col);
    }
    setColumns(sheet.headers.filter((hcol) => selected.has(hcol)));
  };
  const cycleSort = (col) => {
    setSort((current) => {
      if (current.col !== col) return { col, dir: "asc" };
      if (current.dir === "asc") return { col, dir: "desc" };
      return { col: null, dir: null };
    });
    setPage(0);
    setOpenRowId(null);
    setEditing(null);
  };

  const queueDelete = (row) => {
    const label = keyCols.map((k) => row[k]).join(" / ");
    if (!window.confirm(`Queue delete of ${label} from ${name}?`)) return;
    onQueue({ action: "delete", sheet: name,
              key: Object.fromEntries(keyCols.map((k) => [k, row[k]])), _old: { ...row } });
  };

  return html`<div class="panel">
    <div class="bar">
      <span class="title">${name}</span>
      ${meta.keyCols && html`<span class="badge">key: ${meta.keyCols.join(" + ")}</span>`}
      ${meta.readOnly && html`<span class="badge">read-only</span>`}
      <span class="meta">${filtered.length} / ${meta.rowCount ?? "?"} rows${extra > 0 ? ` · +${extra} more cols in row detail` : ""}</span>
      ${editable && !isOptionsFamily && html`
        <button class="btn green" onClick=${() => setEditing({ mode: "add", initial: {} })}>+ Add Row</button>`}
      ${editable && isOptionsFamily && html`
        <span class="meta hint">options rows are added via the Add Option wizard (full OVS coverage)</span>`}
      ${sheet && html`<details class="column-picker">
        <summary class="btn">Columns (${cols.length}/${sheet.headers.length})</summary>
        <div class="column-menu">
          <div class="column-actions">
            <button class="btn tiny" onClick=${() => setColumns(defaultVisibleColumns(sheet.headers))}>First 8</button>
            <button class="btn tiny" onClick=${() => setColumns(sheet.headers)}>All</button>
          </div>
          <div class="column-options">
            ${sheet.headers.map((col) => html`<label key=${col}>
              <input type="checkbox" checked=${cols.includes(col)}
                onChange=${() => toggleColumn(col)} />
              <span>${col}</span>
            </label>`)}
          </div>
        </div>
      </details>`}
      <input type="search" placeholder="Filter rows…" value=${query}
        onInput=${(e) => { setQuery(e.target.value); setPage(0); setOpenRowId(null); }} />
    </div>
    ${error && html`<div class="error">${error}</div>`}
    ${!sheet && !error && html`<div class="loading">Loading ${name}…</div>`}
    ${editing?.mode === "add" && html`<${RowForm} data=${data} sheetName=${name} mode=${editing.mode}
        initial=${editing.initial} onQueue=${onQueue} onCancel=${() => setEditing(null)} />`}
    ${sheet && html`<div class="tablewrap"><table>
      <thead><tr>
        ${cols.map((c) => html`<th key=${c}>
          <button class=${"sort-head" + (sort.col === c ? " on" : "")}
            title=${sort.col === c ? `Sorted ${sort.dir}; click to change` : "Sort by this column"}
            onClick=${() => cycleSort(c)}>
            <span>${c}</span>
            ${sort.col === c && html`<span class="sort-mark">${sort.dir}</span>`}
          </button>
        </th>`)}
        ${editable && html`<th class="actions-col">actions</th>`}
      </tr></thead>
      <tbody>
        ${rows.length === 0 && html`<tr><td colSpan=${cols.length + 1} class="dim">No rows match.</td></tr>`}
        ${rows.map((r) => {
          const rowId = rowIdFor(r);
          return html`
            <tr class=${"row" + (editing?.mode === "edit" && editing.rowId === rowId ? " editing" : "")}
              key=${rowId} onClick=${() => setOpenRowId(openRowId === rowId ? null : rowId)}>
              ${cols.map((c) => html`<td key=${c} title=${String(r[c] ?? "")}>${fmt(r[c])}</td>`)}
              ${editable && html`<td class="actions-col" onClick=${(e) => e.stopPropagation()}>
                <button class="btn tiny" title="Edit"
                  onClick=${() => setEditing({ mode: "edit", initial: r, rowId })}>✎</button>
                <button class="btn tiny danger" title="Delete" onClick=${() => queueDelete(r)}>🗑</button>
              </td>`}
            </tr>
            ${editing?.mode === "edit" && editing.rowId === rowId && html`<tr class="inline-edit"><td colSpan=${cols.length + 1}>
              <${RowForm} data=${data} sheetName=${name} mode=${editing.mode}
                initial=${editing.initial} onQueue=${onQueue} onCancel=${() => setEditing(null)} />
            </td></tr>`}
            ${openRowId === rowId && html`<tr class="detail"><td colSpan=${cols.length + 1}>
              <dl>${sheet.headers.map((hcol) => html`
                <dt key=${"t" + hcol}>${hcol}</dt><dd key=${"d" + hcol}>${fmt(r[hcol])}</dd>`)}
              </dl>
            </td></tr>`}`;
        })}
      </tbody>
    </table></div>
    <div class="pager">
      <button disabled=${safePage === 0} onClick=${() => { setPage(safePage - 1); setOpenRowId(null); }}>‹ Prev</button>
      <span>page ${safePage + 1} / ${pages}</span>
      <button disabled=${safePage >= pages - 1} onClick=${() => { setPage(safePage + 1); setOpenRowId(null); }}>Next ›</button>
    </div>`}
  </div>`;
}

/* ── Add Option wizard ────────────────────────────────────── */

function AddOptionWizard({ data, modelKey, onQueue, onClose }) {
  const optionsSheet = sheetOfFamily(data, modelKey, "options");
  const ovsSheet = sheetOfFamily(data, modelKey, "ovs");
  const metaEntry = data.sheets.find((s) => s.name === optionsSheet);
  const variants = data.referenceDomains.variantsByModel[modelKey] || [];
  const [step, setStep] = useState(1);
  const [rowsCache, setRowsCache] = useState(null);
  const [draft, setDraft] = useState({ selectable: true, active: true });
  const [idTouched, setIdTouched] = useState(false);
  const [orderTouched, setOrderTouched] = useState(false);
  const [statuses, setStatuses] = useState(() => Object.fromEntries(variants.map((v) => [v.id, ""])));
  const [bulk, setBulk] = useState("");
  const [rgMembers, setRgMembers] = useState([]);
  const [exMembers, setExMembers] = useState([]);

  useEffect(() => {
    fetchJson(`/api/sheet/${encodeURIComponent(optionsSheet)}`)
      .then((s) => setRowsCache(s.rows)).catch(() => setRowsCache([]));
  }, [optionsSheet]);

  const set = (col, v) => {
    setDraft((d) => {
      const next = { ...d, [col]: v };
      if (col === "option_id") setIdTouched(true);
      if (col === "display_order") setOrderTouched(true);
      if (col === "rpo" && !idTouched && typeof v === "string" && v.trim()) {
        next.option_id = `opt_${v.trim().toLowerCase()}_001`;
      }
      if (col === "section_id" && !orderTouched && rowsCache) {
        const orders = rowsCache.filter((r) => r.section_id === v)
          .map((r) => Number(r.display_order) || 0);
        next.display_order = (orders.length ? Math.max(...orders) : 0) + 10;
      }
      return next;
    });
  };

  const statusesComplete = variants.length > 0 && variants.every((v) => statuses[v.id]);
  const ovsEnums = (data.sheets.find((s) => s.name === ovsSheet) || {}).enums?.status || [];

  const queueComposite = () => {
    const oid = draft.option_id;
    const headers = metaEntry.headers;
    const row = {};
    headers.forEach((c) => { row[c] = draft[c] ?? null; });
    const ops = [{ action: "add", sheet: optionsSheet, key: { option_id: oid }, row }];
    for (const v of variants) {
      ops.push({ action: "add", sheet: ovsSheet, key: { option_id: oid, variant_id: v.id },
                 row: { option_id: oid, variant_id: v.id, status: statuses[v.id] } });
    }
    const rgSheet = sheetOfFamily(data, modelKey, "rule_group_members");
    for (const m of rgMembers.filter((m) => m.group_id)) {
      ops.push({ action: "add", sheet: rgSheet, key: { group_id: m.group_id, target_id: oid },
                 row: { group_id: m.group_id, target_id: oid,
                        display_order: m.display_order ?? null, active: true } });
    }
    const exSheet = sheetOfFamily(data, modelKey, "exclusive_members");
    for (const m of exMembers.filter((m) => m.group_id)) {
      ops.push({ action: "add", sheet: exSheet, key: { group_id: m.group_id, option_id: oid },
                 row: { group_id: m.group_id, option_id: oid,
                        display_order: m.display_order ?? null, active: true } });
    }
    onQueue({ kind: "composite", compositeType: "add_option",
              label: `Add option ${draft.rpo || oid} (${modelKey})`, ops });
    onClose();
  };

  const memberEditor = (members, setMembers, groups) => html`
    <div class="members">
      ${members.map((m, i) => html`<div class="memberrow" key=${i}>
        <select value=${m.group_id || ""}
          onChange=${(e) => setMembers(members.map((x, j) => j === i ? { ...x, group_id: e.target.value } : x))}>
          <option value="">(choose group)</option>
          ${groups.map((g) => html`<option value=${g.value} key=${g.value}>${g.label}</option>`)}
        </select>
        <input type="number" placeholder="display_order" value=${m.display_order ?? ""}
          onInput=${(e) => setMembers(members.map((x, j) => j === i
            ? { ...x, display_order: e.target.value === "" ? null : Number(e.target.value) } : x))} />
        <button class="btn tiny danger" onClick=${() => setMembers(members.filter((_, j) => j !== i))}>✕</button>
      </div>`)}
      <button class="btn" onClick=${() => setMembers([...members, { group_id: "", display_order: null }])}>
        + membership
      </button>
    </div>`;

  return html`<div class="wizard panel">
    <div class="bar">
      <span class="title">Add Option — ${modelKey}</span>
      <span class="meta">step ${step} of 3</span>
      <button class="btn ghost" onClick=${onClose}>✕</button>
    </div>
    ${step === 1 && html`<div class="wizbody">
      <div class="fields">
        ${metaEntry.headers.map((col) => html`<label key=${col}>
          <span class=${col === "option_id" ? "key" : ""}>${col}${col === "option_id" ? " *" : ""}</span>
          <${FieldInput} data=${data} metaEntry=${metaEntry} sheetName=${optionsSheet} col=${col}
            value=${draft[col]} onChange=${(v) => set(col, v)} />
        </label>`)}
      </div>
      <div class="formactions">
        <button class="btn primary" disabled=${isBlank(draft.option_id) || isBlank(draft.rpo)}
          onClick=${() => setStep(2)}>Next: variant coverage ›</button>
      </div>
    </div>`}
    ${step === 2 && html`<div class="wizbody">
      <p class="note">Every active ${modelKey} variant needs an explicit status — no defaults.</p>
      <div class="bulkrow">
        <span>Set all to…</span>
        <select value=${bulk} onChange=${(e) => {
          setBulk(e.target.value);
          if (e.target.value) setStatuses(Object.fromEntries(variants.map((v) => [v.id, e.target.value])));
        }}>
          <option value="">(choose)</option>
          ${ovsEnums.map((s) => html`<option value=${s} key=${s}>${s}</option>`)}
        </select>
      </div>
      <div class="ovsgrid">
        ${variants.map((v) => html`<label key=${v.id}>
          <span>${v.id} — ${v.name || ""}</span>
          <select value=${statuses[v.id] || ""}
            onChange=${(e) => setStatuses((s) => ({ ...s, [v.id]: e.target.value }))}>
            <option value="">(required)</option>
            ${ovsEnums.map((s) => html`<option value=${s} key=${s}>${s}</option>`)}
          </select>
        </label>`)}
      </div>
      <div class="formactions">
        <button class="btn" onClick=${() => setStep(1)}>‹ Back</button>
        <button class="btn primary" disabled=${!statusesComplete} onClick=${() => setStep(3)}>
          Next: groups (optional) ›</button>
      </div>
    </div>`}
    ${step === 3 && html`<div class="wizbody">
      <h3>Rule-group memberships (optional)</h3>
      ${memberEditor(rgMembers, setRgMembers, refOptions(data, optionsSheet, "rule_groups"))}
      <h3>Exclusive-group memberships (optional)</h3>
      ${memberEditor(exMembers, setExMembers, refOptions(data, optionsSheet, "exclusive_groups"))}
      <p class="note">Direct rule_mapping rows can be added afterwards on the rule sheet — pickers there too.</p>
      <div class="formactions">
        <button class="btn" onClick=${() => setStep(2)}>‹ Back</button>
        <button class="btn primary" onClick=${queueComposite}>Queue composite (${1 + variants.length
          + rgMembers.filter((m) => m.group_id).length + exMembers.filter((m) => m.group_id).length} ops)</button>
      </div>
    </div>`}
  </div>`;
}

/* ── group wizards (rule + exclusive) ─────────────────────── */

function GroupWizard({ data, modelKey, kind, onQueue, onClose }) {
  const groupFamily = kind === "rule" ? "rule_groups" : "exclusive_groups";
  const memberFamily = kind === "rule" ? "rule_group_members" : "exclusive_members";
  const memberCol = kind === "rule" ? "target_id" : "option_id";
  const minMembers = kind === "rule" ? 1 : 2;
  const groupSheet = sheetOfFamily(data, modelKey, groupFamily);
  const memberSheet = sheetOfFamily(data, modelKey, memberFamily);
  const metaEntry = data.sheets.find((s) => s.name === groupSheet);
  const [draft, setDraft] = useState({ active: true });
  const [members, setMembers] = useState([]);
  const optionPicks = refOptions(data, memberSheet, "options");

  const validMembers = members.filter((m) => m.id);
  const queueComposite = () => {
    const gid = draft.group_id;
    const headers = metaEntry.headers;
    const row = {};
    headers.forEach((c) => { row[c] = draft[c] ?? null; });
    const ops = [{ action: "add", sheet: groupSheet, key: { group_id: gid }, row }];
    validMembers.forEach((m, i) => {
      ops.push({ action: "add", sheet: memberSheet,
                 key: { group_id: gid, [memberCol]: m.id },
                 row: { group_id: gid, [memberCol]: m.id,
                        display_order: (i + 1) * 10, active: true } });
    });
    onQueue({ kind: "composite", compositeType: `add_${groupFamily}`,
              label: `Add ${kind} group ${gid} (${modelKey})`, ops });
    onClose();
  };

  return html`<div class="wizard panel">
    <div class="bar">
      <span class="title">Add ${kind === "rule" ? "Rule" : "Exclusive"} Group — ${modelKey}</span>
      <button class="btn ghost" onClick=${onClose}>✕</button>
    </div>
    <div class="wizbody">
      <div class="fields">
        ${metaEntry.headers.map((col) => html`<label key=${col}>
          <span class=${col === "group_id" ? "key" : ""}>${col}${col === "group_id" ? " *" : ""}</span>
          <${FieldInput} data=${data} metaEntry=${metaEntry} sheetName=${groupSheet} col=${col}
            value=${draft[col]} onChange=${(v) => setDraft((d) => ({ ...d, [col]: v }))} />
        </label>`)}
      </div>
      <h3>Members (≥ ${minMembers}, display_order auto-stepped by 10)</h3>
      <div class="members">
        ${members.map((m, i) => html`<div class="memberrow" key=${i}>
          <select value=${m.id || ""}
            onChange=${(e) => setMembers(members.map((x, j) => j === i ? { ...x, id: e.target.value } : x))}>
            <option value="">(choose option)</option>
            ${optionPicks.map((o) => html`<option value=${o.value} key=${o.value}>${o.label}</option>`)}
          </select>
          <button class="btn tiny danger" onClick=${() => setMembers(members.filter((_, j) => j !== i))}>✕</button>
        </div>`)}
        <button class="btn" onClick=${() => setMembers([...members, { id: "" }])}>+ member</button>
      </div>
      <div class="formactions">
        <button class="btn primary"
          disabled=${isBlank(draft.group_id) || validMembers.length < minMembers}
          onClick=${queueComposite}>Queue composite (${1 + validMembers.length} ops)</button>
      </div>
    </div>
  </div>`;
}

/* ── Browser tab shell ────────────────────────────────────── */

function BrowserTab({ data, modelKey, setModelKey, onQueue, focus, onFocusConsumed }) {
  const modelEntries = data.modelSheets[modelKey] || [];
  const [sheetName, setSheetName] = useState(focus?.sheet || modelEntries[0]?.sheet || null);
  const [wizard, setWizard] = useState(null); // "option" | "rule" | "exclusive"

  useEffect(() => {
    const entries = data.modelSheets[modelKey] || [];
    setSheetName(focus?.sheet || entries[0]?.sheet || null);
    setWizard(null);
  }, [modelKey]);

  useEffect(() => {
    if (focus?.sheet) setSheetName(focus.sheet);
  }, [focus]);

  const modelSheetNames = new Set(modelEntries.map((e) => e.sheet));
  const otherSheets = data.sheets.map((s) => s.name).filter((n) => !modelSheetNames.has(n)).sort();
  const hasSheets = modelEntries.length > 0;

  return html`
    <div class="pills">
      ${data.models.map((m) => html`
        <button
          class=${"pill" + (m.key === modelKey ? " on" : "") + (m.active ? "" : " scaffold")}
          onClick=${() => setModelKey(m.key)} key=${m.key}
        >${m.label}${m.active ? "" : " · scaffold"}</button>`)}
      ${hasSheets && html`<span class="spacer"></span>
        <button class="btn green" onClick=${() => setWizard("option")}>✦ Add Option</button>
        <button class="btn" onClick=${() => setWizard("rule")}>✦ Add Rule Group</button>
        <button class="btn" onClick=${() => setWizard("exclusive")}>✦ Add Exclusive Group</button>`}
    </div>
    <div class="pills">
      ${modelEntries.map((e) => html`
        <button class=${"pill sheet" + (e.sheet === sheetName ? " on" : "")}
          onClick=${() => setSheetName(e.sheet)} title=${e.role} key=${e.sheet}
        >${e.sheet}</button>`)}
      <select class="other" value=${modelSheetNames.has(sheetName) ? "" : sheetName || ""}
        onChange=${(e) => e.target.value && setSheetName(e.target.value)}>
        <option value="">other sheets…</option>
        ${otherSheets.map((n) => html`<option value=${n} key=${n}>${n}</option>`)}
      </select>
    </div>
    ${wizard === "option" && html`<${AddOptionWizard} data=${data} modelKey=${modelKey}
        onQueue=${onQueue} onClose=${() => setWizard(null)} />`}
    ${(wizard === "rule" || wizard === "exclusive") && html`<${GroupWizard} data=${data}
        modelKey=${modelKey} kind=${wizard} onQueue=${onQueue} onClose=${() => setWizard(null)} />`}
    ${sheetName
      ? html`<${SheetTable} data=${data} name=${sheetName} key=${sheetName} onQueue=${onQueue}
          initialQuery=${focus && focus.sheet === sheetName ? focus.query : ""}
          focusTs=${focus && focus.sheet === sheetName ? focus.ts : null}
          onFocusConsumed=${onFocusConsumed} />`
      : html`<p class="note">No registered source sheets for this model — pick one from “other sheets…”.</p>`}`;
}

/* ── Review tab (Phase 3, read-only) ──────────────────────── */

const SEVERITIES = ["error", "warning", "info"];

function LintsPanel({ onOpenRow }) {
  const [payload, setPayload] = useState(null);
  const [error, setError] = useState(null);
  const [severities, setSeverities] = useState(() => new Set(SEVERITIES));
  const [sheetFilter, setSheetFilter] = useState("");
  const [modelFilter, setModelFilter] = useState("");
  const [idFilter, setIdFilter] = useState("");

  useEffect(() => {
    fetchJson("/api/lints").then(setPayload).catch((e) => setError(e.message));
  }, []);

  if (error) return html`<div class="error">${error}</div>`;
  if (!payload) return html`<div class="loading">Running lints…</div>`;

  const lints = payload.lints;
  const sheets = [...new Set(lints.map((l) => l.sheet))].sort();
  const models = [...new Set(lints.map((l) => l.model).filter(Boolean))].sort();
  const ids = [...new Set(lints.map((l) => l.id))].sort();
  const filtered = lints.filter((l) =>
    severities.has(l.severity)
    && (!sheetFilter || l.sheet === sheetFilter)
    && (!modelFilter || l.model === modelFilter)
    && (!idFilter || l.id === idFilter));
  const shown = filtered.slice(0, 300);
  const toggleSeverity = (s) => setSeverities((prev) => {
    const next = new Set(prev);
    if (next.has(s)) next.delete(s); else next.add(s);
    return next;
  });

  return html`<div class="panel">
    <div class="bar">
      <span class="title">Lints</span>
      ${SEVERITIES.map((s) => html`
        <button key=${s} class=${"sumchip sev-" + s + (severities.has(s) ? " on" : "")}
          onClick=${() => toggleSeverity(s)}>${payload.summary[s] ?? 0} ${s}</button>`)}
      <span class="meta">structural checks on current workbook state — informational, never gates applies</span>
      <span class="spacer"></span>
      <select value=${idFilter} onChange=${(e) => setIdFilter(e.target.value)}>
        <option value="">all lints</option>
        ${ids.map((i) => html`<option value=${i} key=${i}>${i}</option>`)}
      </select>
      <select value=${modelFilter} onChange=${(e) => setModelFilter(e.target.value)}>
        <option value="">all models</option>
        ${models.map((m) => html`<option value=${m} key=${m}>${m}</option>`)}
      </select>
      <select value=${sheetFilter} onChange=${(e) => setSheetFilter(e.target.value)}>
        <option value="">all sheets</option>
        ${sheets.map((s) => html`<option value=${s} key=${s}>${s}</option>`)}
      </select>
    </div>
    <div class="tablewrap"><table>
      <thead><tr><th>severity</th><th>lint</th><th>sheet</th><th>model</th><th>key</th><th>message</th></tr></thead>
      <tbody>
        ${shown.length === 0 && html`<tr><td colSpan="6" class="dim">No lints match the filters.</td></tr>`}
        ${shown.map((l, i) => html`<tr class="row" key=${i} title="open in Sheet Browser"
            onClick=${() => onOpenRow(l)}>
          <td><span class=${"badge sev-" + l.severity}>${l.severity}</span></td>
          <td class="mono small">${l.id}</td>
          <td class="mono small">${l.sheet}</td>
          <td class="small">${l.model || html`<span class="dim">—</span>`}</td>
          <td class="mono small">${l.key}</td>
          <td class="lintmsg" title=${l.message}>${l.message}</td>
        </tr>`)}
      </tbody>
    </table></div>
    ${filtered.length > shown.length && html`
      <p class="note pad">Showing first ${shown.length} of ${filtered.length} — narrow with the filters above.</p>`}
  </div>`;
}

function diffStatusBadge(d) {
  if (d.status === "intentional")
    return html`<span class="badge st-intentional" title=${d.reason || ""}>intentional</span>`;
  if (d.status === "pending-review")
    return html`<span class="badge st-pending" title=${d.reason || ""}>pending review</span>`;
  return null;
}

function ComparePanel() {
  const [payload, setPayload] = useState(null);
  const [error, setError] = useState(null);
  const [fieldFilter, setFieldFilter] = useState("");
  const [modelFilter, setModelFilter] = useState("");
  const [showIntentional, setShowIntentional] = useState(false);
  const [query, setQuery] = useState("");

  useEffect(() => {
    fetchJson("/api/compare").then(setPayload).catch((e) => setError(e.message));
  }, []);

  if (error) return html`<div class="error">${error}</div>`;
  if (!payload) return html`<div class="loading">Comparing models…</div>`;

  const fields = [...new Set(payload.rows.flatMap((r) => r.diffs.map((d) => d.field)))].sort();
  const q = query.trim().toLowerCase();
  const visible = payload.rows
    .map((r) => ({
      ...r,
      diffs: r.diffs.filter((d) =>
        (showIntentional || d.status !== "intentional")
        && (!fieldFilter || d.field === fieldFilter)
        && (!modelFilter || (d.deviators || []).includes(modelFilter))),
    }))
    .filter((r) => r.diffs.length > 0
      && (!q || `${r.rpo || ""} ${r.name || ""} ${r.joinKey}`.toLowerCase().includes(q)));
  const intentionalCount = payload.rows.reduce(
    (n, r) => n + r.diffs.filter((d) => d.status === "intentional").length, 0);
  const modelOnlyCounts = Object.entries(payload.modelOnly || {})
    .map(([m, list]) => `${m}: ${list.length}`).join(" · ");

  return html`<div class="space">
    <div class="panel">
      <div class="bar">
        <span class="title">Cross-Model Compare</span>
        <span class="meta">${payload.sharedCount} options shared across ${payload.models.join(" / ")}
          · ${visible.length} divergent shown · model-only (expected): ${modelOnlyCounts}</span>
        <span class="spacer"></span>
        <label class="toggle">
          <input type="checkbox" checked=${showIntentional}
            onChange=${(e) => setShowIntentional(e.target.checked)} />
          show intentional (${intentionalCount})
        </label>
        <select value=${fieldFilter} onChange=${(e) => setFieldFilter(e.target.value)}>
          <option value="">all fields</option>
          ${fields.map((f) => html`<option value=${f} key=${f}>${f}</option>`)}
        </select>
        <select value=${modelFilter} onChange=${(e) => setModelFilter(e.target.value)}>
          <option value="">any deviator</option>
          ${payload.models.map((m) => html`<option value=${m} key=${m}>${m} deviates</option>`)}
        </select>
        <input type="search" placeholder="Filter by RPO / name…" value=${query}
          onInput=${(e) => setQuery(e.target.value)} />
      </div>
      ${visible.length === 0 && html`<p class="note pad">No divergences match the filters.</p>`}
      ${visible.map((r) => html`<div class="cmprow" key=${r.joinKey}>
        <div class="cmphead">
          <span class="rpo mono">${r.rpo || "—"}</span>
          <span class="cmpname">${r.name || r.joinKey}</span>
          <span class="mono small dim">${r.joinKey}</span>
          ${r.joinedVia === "rpo" && html`<span class="badge amber"
            title=${"option_id differs across models: " + Object.entries(r.optionIds).map(([m, v]) => `${m}=${v}`).join(", ")}>joined via RPO</span>`}
          ${r.models.length < payload.models.length && html`
            <span class="badge" title="not present on every compared model">${r.models.join(" + ")} only</span>`}
        </div>
        ${r.diffs.map((d) => html`<div class=${"cmpdiff" + (d.status === "intentional" ? " muted" : "")} key=${d.field}>
          <span class="badge field">${d.field}</span>
          ${diffStatusBadge(d)}
          <div class="cmpvals">
            ${payload.models.filter((m) => d.values[m] !== undefined).map((m) => html`
              <div class=${"cmpval" + ((d.deviators || []).includes(m) ? " deviator" : "")} key=${m}>
                <span class="cmpmodel">${m}
                  ${(d.deviators || []).includes(m) && html`<span class="badge dev">deviator</span>`}
                  ${d.majority !== null && d.values[m] === d.majority
                    && html`<span class="badge maj">majority</span>`}
                </span>
                <span class="cmptext">${d.values[m] === "" ? html`<span class="dim">(blank)</span>` : d.values[m]}</span>
              </div>`)}
          </div>
          ${d.reason && html`<p class="note reason">${d.reason}</p>`}
        </div>`)}
      </div>`)}
    </div>
    ${(payload.staleAllowlist || []).length > 0 && html`<div class="panel">
      <div class="bar"><span class="title">Stale allowlist entries</span>
        <span class="meta">intentional entries that no longer match any divergence — candidates for removal from intentional-differences.json</span></div>
      <ul class="errlist stale">
        ${payload.staleAllowlist.map((e, i) => html`<li key=${i} class="mono small">
          ${e.option_id || e.rpo} · ${e.field || "*"} — ${e.reason}</li>`)}
      </ul>
    </div>`}
  </div>`;
}

function ReviewTab({ onOpenRow }) {
  const [panel, setPanel] = useState("lints");
  return html`
    <div class="pills">
      <button class=${"pill" + (panel === "lints" ? " on" : "")}
        onClick=${() => setPanel("lints")}>Lints</button>
      <button class=${"pill" + (panel === "compare" ? " on" : "")}
        onClick=${() => setPanel("compare")}>Cross-Model Compare</button>
      <span class="meta">read-only review surfaces — nothing here queues or applies changes</span>
    </div>
    ${panel === "lints"
      ? html`<${LintsPanel} onOpenRow=${onOpenRow} />`
      : html`<${ComparePanel} />`}`;
}

/* ── Ingest Review tab (Pass 2, read-only) ────────────────── */

function JsonBlock({ value }) {
  return html`<pre class="jsonblock">${JSON.stringify(value ?? null, null, 2)}</pre>`;
}

function candidateLabel(row) {
  if (row.interpretation_id) return `${row.model_key || "model"} / ${row.rpo || row.interpretation_id}`;
  const normalized = row.normalized_values || {};
  return normalized.rpo || normalized.candidate_option_ref || normalized.candidate_rule_ref
    || row.candidate_id || row.unresolved_id;
}

function IngestReviewTab() {
  const [summary, setSummary] = useState(null);
  const [error, setError] = useState(null);
  const [family, setFamily] = useState("interpretations");
  const [query, setQuery] = useState("");
  const [reason, setReason] = useState("");
  const [confidence, setConfidence] = useState("");
  const [duplicate, setDuplicate] = useState("");
  const [includeAuto, setIncludeAuto] = useState(false);
  const [rows, setRows] = useState(null);
  const [selected, setSelected] = useState(null);
  const [detail, setDetail] = useState(null);
  const [decisions, setDecisions] = useState({});
  const [validation, setValidation] = useState(null);

  useEffect(() => {
    fetchJson("/api/ingest/summary").then((payload) => {
      setSummary(payload);
      setFamily(payload.interpretation_enabled ? "interpretations" : "options");
    }).catch((e) => setError(e.message));
  }, []);

  useEffect(() => {
    if (!summary?.enabled) return;
    if (family === "interpretations" && !summary.interpretation_enabled) {
      setFamily("options");
      return;
    }
    setRows(null); setDetail(null); setSelected(null);
    const params = new URLSearchParams({ limit: "200" });
    if (query.trim()) params.set("q", query.trim());
    if (family === "interpretations") {
      if (confidence) params.set("confidence", confidence);
      if (duplicate) params.set("duplicate", duplicate);
      if (reason) params.set("reason", reason);
      if (includeAuto) params.set("include_auto", "true");
      fetchJson(`/api/ingest/interpretations?${params.toString()}`)
        .then(setRows).catch((e) => setError(e.message));
      return;
    }
    params.set("family", family);
    if (family === "unresolved" && reason) params.set("reason", reason);
    fetchJson(`/api/ingest/candidates?${params.toString()}`)
      .then(setRows).catch((e) => setError(e.message));
  }, [summary?.enabled, summary?.interpretation_enabled, family, query, reason, confidence, duplicate, includeAuto]);

  const decisionKey = (row) => {
    if (family === "interpretations") return row.interpretation_id;
    return family === "unresolved" ? row.unresolved_id : row.candidate_id;
  };
  const loadDetail = (row) => {
    setSelected(row);
    const id = decisionKey(row);
    const route = family === "interpretations" ? "interpretation" : (family === "unresolved" ? "unresolved" : "candidate");
    fetchJson(`/api/ingest/${route}/${encodeURIComponent(id)}`)
      .then(setDetail).catch((e) => setError(e.message));
  };

  const setDecisionState = (row, state) => {
    const key = decisionKey(row);
    setDecisions((current) => ({ ...current, [key]: { ...(current[key] || {}), state, row, family } }));
  };
  const setDecisionNote = (row, note) => {
    const key = decisionKey(row);
    setDecisions((current) => ({ ...current, [key]: { ...(current[key] || {}), note, row, family } }));
  };

  const buildDecisionExport = () => {
    const picked = Object.values(decisions).filter((d) => d.state);
    const interpretationDecisions = picked.filter((d) => d.family === "interpretations").map((d) => ({
      interpretation_id: d.row.interpretation_id,
      model_key: d.row.model_key,
      rpo: d.row.rpo,
      interpretation_confidence: d.row.interpretation_confidence,
      decision_state: d.state,
      reviewer_notes: d.note || "",
      review_reason_codes: d.row.review_reason_codes || [],
      source_occurrences_snapshot: d.row.source_occurrences || [],
      availability_matrix_snapshot: d.row.availability_matrix || {},
      workbook_identity_match_snapshot: d.row.workbook_identity_match || {},
      workbook_status_match_snapshot: d.row.workbook_status_match || {},
      duplicate_classification_snapshot: d.row.duplicate_classification || "",
    }));
    const candidateDecisions = picked.filter((d) => d.family !== "unresolved" && d.family !== "interpretations").map((d) => ({
      candidate_id: d.row.candidate_id,
      candidate_family: d.row.candidate_family,
      decision_state: d.state,
      reviewer_notes: d.note || "",
      source_refs: d.row.source_refs || [],
      raw_values_snapshot: d.row.raw_values || {},
      normalized_values_snapshot: d.row.normalized_values || {},
      workbook_match_snapshot: d.row.workbook_match || null,
    }));
    const unresolvedDecisions = picked.filter((d) => d.family === "unresolved").map((d) => ({
      unresolved_id: d.row.unresolved_id,
      reason: d.row.reason,
      category: d.row.category,
      decision_state: d.state,
      reviewer_notes: d.note || "",
      source_refs: d.row.source_refs || [],
      raw_values_snapshot: d.row.raw_values || {},
      normalized_values_snapshot: d.row.normalized_values || {},
      candidate_refs: d.row.candidate_refs || [],
    }));
    const interpretationMode = summary.interpretation_enabled;
    return {
      version: interpretationMode ? 2 : 1,
      review_mode: interpretationMode ? "interpretation" : "raw_candidates",
      created_at: new Date().toISOString(),
      workbook: summary.workbook,
      evidence_dir: summary.evidence_dir,
      candidates_dir: summary.candidates_dir,
      interpretation_dir: summary.interpretation_dir || "",
      evidence_artifacts: summary.evidence_artifacts,
      candidate_artifacts: summary.candidate_artifacts,
      interpretation_artifacts: summary.interpretation_artifacts || {},
      candidate_summary: summary.candidate_summary,
      interpretation_summary: summary.interpretation_summary || {},
      interpretation_decisions: interpretationDecisions,
      raw_candidate_decisions: candidateDecisions,
      decisions: candidateDecisions,
      unresolved_decisions: unresolvedDecisions,
      unresolved_rollup: summary.unresolved_counts,
      notes: interpretationMode
        ? "Exported from Pass 4 reduced Ingest Review; not a workbook apply manifest."
        : "Exported from Pass 2 Ingest Review; not a workbook apply manifest.",
    };
  };

  const exportDecisions = () => {
    const blob = new Blob([JSON.stringify(buildDecisionExport(), null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `ingest-review-decisions-${new Date().toISOString().slice(0, 10)}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const validateDecisions = async () => {
    const { data } = await postJson("/api/ingest/review/validate", buildDecisionExport());
    setValidation(data);
  };

  if (error) return html`<div class="error">${error}</div>`;
  if (!summary) return html`<div class="loading">Loading ingest review payload…</div>`;
  if (!summary.enabled) return html`<div class="panel"><p class="note pad">${summary.message}</p></div>`;

  const reasons = Object.keys(summary.unresolved_counts || {}).sort();
  const interpretationSummary = summary.interpretation_summary || {};
  const modeLabel = family === "interpretations" ? "Reduced review" : "Raw candidates";
  const selectedDecision = selected ? decisions[decisionKey(selected)] || {} : {};

  return html`<div class="space ingest-review">
    <div class="panel">
      <div class="bar">
        <span class="title">Ingest Review</span>
        <span class="badge amber">review-only</span>
        <span class="meta">No workbook ops are queued or applied from this tab.</span>
        <span class="spacer"></span>
        <button class="btn" onClick=${validateDecisions}>Validate decisions</button>
        <button class="btn primary" onClick=${exportDecisions}>Export decisions JSON</button>
      </div>
      <div class="ingest-summary">
        ${summary.interpretation_enabled && html`
          <div class="metric"><b>${interpretationSummary.raw_candidate_total || 0}</b><span>raw candidates</span></div>
          <div class="metric"><b>${interpretationSummary.interpreted_option_count || 0}</b><span>model/RPO units</span></div>
          <div class="metric"><b>${interpretationSummary.visible_review_queue_count || 0}</b><span>visible queue</span></div>
          <div class="metric green"><b>${interpretationSummary.hidden_auto_confirmed_count || 0}</b><span>auto-confirmed</span></div>
          <div class="metric"><b>${interpretationSummary.mechanical_safe_count || 0}</b><span>mechanical-safe</span></div>
          <div class="metric warn"><b>${interpretationSummary.review_needed_count || 0}</b><span>review-needed</span></div>
          <div class="metric warn"><b>${interpretationSummary.blocked_count || 0}</b><span>blocked</span></div>
          <div class="metric"><b>${interpretationSummary.duplicate_rpo_count || 0}</b><span>duplicate RPOs</span></div>
          <div class="metric"><b>${interpretationSummary.reduction_status || "—"}</b><span>reduction</span></div>
        `}
        ${!summary.interpretation_enabled && Object.entries(summary.candidate_counts || {}).map(([k, v]) => html`
          <div class="metric" key=${k}><b>${v}</b><span>${k}</span></div>`)}
        ${!summary.interpretation_enabled && html`<div class="metric warn"><b>${Object.values(summary.unresolved_counts || {}).reduce((a, b) => a + b, 0)}</b><span>unresolved</span></div>`}
      </div>
      <details class="artifact-details">
        <summary>Artifact fingerprints</summary>
        <${JsonBlock} value=${{ evidence: summary.evidence_artifacts, candidates: summary.candidate_artifacts, interpretation: summary.interpretation_artifacts || {} }} />
      </details>
    </div>

    ${validation && html`<div class=${validation.ok ? "panel applied" : "panel"}>
      <div class="bar"><span class="title">${validation.ok ? "✓ Review decisions valid" : "✗ Review decisions need fixes"}</span></div>
      ${(validation.errors || []).length > 0 && html`<ul class="errlist">
        ${validation.errors.map((e, i) => html`<li key=${i}>${e}</li>`)}
      </ul>`}
    </div>`}

    <div class="panel">
      <div class="bar">
        <span class="title">${modeLabel}</span>
        <select value=${family} onChange=${(e) => { setFamily(e.target.value); setReason(""); setConfidence(""); setDuplicate(""); }}>
          ${summary.interpretation_enabled && html`<option value="interpretations">reduced review</option>`}
          ${summary.families.map((f) => html`<option value=${f} key=${f}>${f}</option>`)}
        </select>
        ${family === "interpretations" && html`<select value=${confidence} onChange=${(e) => setConfidence(e.target.value)}>
          <option value="">all visible confidence</option>
          <option value="mechanical_safe">mechanical_safe</option>
          <option value="review_needed">review_needed</option>
          <option value="blocked">blocked</option>
          <option value="auto_confirmed">auto_confirmed audit</option>
        </select>`}
        ${family === "interpretations" && html`<select value=${duplicate} onChange=${(e) => setDuplicate(e.target.value)}>
          <option value="">all duplicate classes</option>
          <option value="single_source">single_source</option>
          <option value="redundant_duplicates">redundant_duplicates</option>
          <option value="complementary_duplicates">complementary_duplicates</option>
          <option value="conflicting_duplicates">conflicting_duplicates</option>
          <option value="blocked_duplicate_review">blocked_duplicate_review</option>
        </select>`}
        ${family === "interpretations" && html`<label class="checkline"><input type="checkbox" checked=${includeAuto} onChange=${(e) => setIncludeAuto(e.target.checked)} /> include auto-confirmed</label>`}
        ${family === "unresolved" && html`<select value=${reason} onChange=${(e) => setReason(e.target.value)}>
          <option value="">all unresolved reasons</option>
          ${reasons.map((r) => html`<option value=${r} key=${r}>${r} (${summary.unresolved_counts[r]})</option>`)}
        </select>`}
        ${family === "interpretations" && html`<input type="search" placeholder="Filter model/RPO units…" value=${query}
          onInput=${(e) => setQuery(e.target.value)} />`}
        ${family !== "interpretations" && html`<input type="search" placeholder="Filter candidates…" value=${query}
          onInput=${(e) => setQuery(e.target.value)} />
        `}
      </div>
      ${!rows && html`<div class="loading">Loading ${modeLabel.toLowerCase()}…</div>`}
      ${rows && html`<div class="ingest-grid">
        <div class="ingest-list">
          <div class="meta pad">Showing ${rows.items.length} of ${rows.total} ${family === "interpretations" ? "model/RPO units" : `${rows.family} rows`}.</div>
          ${rows.items.map((row) => html`<button class=${"ingest-row" + (selected && decisionKey(selected) === decisionKey(row) ? " on" : "")}
            key=${decisionKey(row)} onClick=${() => loadDetail(row)}>
            <span class="mono strong">${candidateLabel(row)}</span>
            <span class=${"badge " + (row.interpretation_confidence === "auto_confirmed" ? "green" : row.interpretation_confidence === "blocked" ? "sev-error" : row.interpretation_confidence === "review_needed" ? "amber" : "")}>${row.interpretation_confidence || row.reason || row.resolution_status}</span>
            <span class="small dim">${row.duplicate_classification || row.category || row.candidate_family}</span>
            ${row.review_reason_codes && html`<span class="small dim">${row.review_reason_codes.join(", ") || "no review reasons"}</span>`}
          </button>`)}
        </div>
        <div class="ingest-detail">
          ${!detail && html`<p class="note pad">Select a row to inspect source evidence and record a review decision.</p>`}
          ${detail && html`<div class="detail-panels">
            <div class="panel mini">
              <div class="bar"><span class="title">Decision</span></div>
              <div class="pad decision-box">
                ${html`<!-- Legacy Pass 4 states. Pass 5 replaces this primary control with workbook-destination actions. -->`}
                <select value=${selectedDecision.state || ""} onChange=${(e) => setDecisionState(selected, e.target.value)}>
                  <option value="">undecided</option>
                  <option value="accept_for_later_apply">accept for later apply</option>
                  <option value="edit_before_apply">edit before apply</option>
                  <option value="skip">skip</option>
                  <option value="needs_source_review">needs source review</option>
                  <option value="blocked_out_of_scope">blocked out of scope</option>
                </select>
                <textarea placeholder="Reviewer notes…" value=${selectedDecision.note || ""}
                  onInput=${(e) => setDecisionNote(selected, e.target.value)} />
              </div>
            </div>
            ${detail.interpretation_id && html`<div class="panel mini"><div class="bar"><span class="title">Expert summary</span></div><div class="pad"><p>${detail.expert_summary}</p><p class="small dim">${(detail.review_reason_codes || []).join(", ") || "no review reasons"}</p></div></div>`}
            <div class="panel mini"><div class="bar"><span class="title">Source evidence</span></div><${JsonBlock} value=${detail.source_occurrences || detail.source_refs || []} /></div>
            ${detail.interpretation_id && html`<div class="panel mini"><div class="bar"><span class="title">Availability matrix</span></div><${JsonBlock} value=${detail.availability_matrix || {}} /></div>`}
            ${detail.interpretation_id && html`<div class="panel mini"><div class="bar"><span class="title">Disclosure / rule evidence</span></div><${JsonBlock} value=${detail.disclosure_evidence || {}} /></div>`}
            <div class="panel mini"><div class="bar"><span class="title">Raw values</span></div><${JsonBlock} value=${detail.raw_values || {}} /></div>
            <div class="panel mini"><div class="bar"><span class="title">Normalized values</span></div><${JsonBlock} value=${detail.normalized_values || {}} /></div>
            <div class="panel mini"><div class="bar"><span class="title">Workbook match / context</span></div><${JsonBlock} value=${detail.interpretation_id ? { identity: detail.workbook_identity_match, status: detail.workbook_status_match, duplicate: detail.duplicate_classification } : (detail.workbook_match || detail.candidate_refs || null)} /></div>
          </div>`}
        </div>
      </div>`}
    </div>
  </div>`;
}

/* ── Pending Changes tab ──────────────────────────────────── */

function opLine(o) {
  const keyText = Object.entries(o.key || {}).map(([k, v]) => `${k}=${v}`).join(", ");
  return html`
    <span class=${"badge op-" + o.action}>${o.action.toUpperCase()}</span>
    <span class="mono small">${o.sheet}</span>
    <span class="small dim">${keyText}</span>
    ${o.action === "update" && o._old && html`<span class="diff">
      ${Object.keys(o.row || {}).map((c) => html`<span class="diffcell" key=${c}>
        ${c}: <s>${String(o._old[c] ?? "—")}</s> → <b>${String(o.row[c] ?? "—")}</b>
      </span>`)}
    </span>`}`;
}

function PendingTab({ data, queue, removeItem, clearQueue, onApplied }) {
  const [valResult, setValResult] = useState(null);
  const [confirmed, setConfirmed] = useState(() => new Set());
  const [busy, setBusy] = useState(false);
  const [applyResult, setApplyResult] = useState(null);

  const buildBatch = () => ({
    version: 1,
    workbook: data.workbook.path,
    workbookMtimeNs: data.workbook.mtimeNs,
    createdAt: new Date().toISOString(),
    items: queue,
  });

  const validate = async () => {
    setBusy(true); setApplyResult(null);
    const { data: result } = await postJson("/api/validate", { batch: buildBatch() });
    setValResult(result); setBusy(false);
  };

  const apply = async () => {
    setBusy(true);
    const { status, data: result } = await postJson("/api/apply",
      { batch: buildBatch(), confirmedWarnings: [...confirmed] });
    setBusy(false);
    if (status === 200 && result.ok) {
      setApplyResult(result); setValResult(null); setConfirmed(new Set());
      clearQueue(); onApplied();
    } else {
      setValResult(result);
    }
  };

  const exportOps = () => {
    const blob = new Blob([JSON.stringify(buildBatch(), null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `workbook-ops-${new Date().toISOString().slice(0, 10)}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return html`<div class="space">
    <div class="panel">
      <div class="bar">
        <span class="title">Pending Changes (${queue.length})</span>
        <span class="spacer"></span>
        <button class="btn" disabled=${!queue.length || busy} onClick=${validate}>Validate</button>
        <button class="btn primary" disabled=${!queue.length || busy} onClick=${apply}>Apply</button>
        <button class="btn" disabled=${!queue.length} onClick=${exportOps}>Export ops.json</button>
        <button class="btn danger" disabled=${!queue.length}
          onClick=${() => { if (window.confirm("Discard all queued changes?")) { clearQueue(); setValResult(null); } }}>
          Clear</button>
      </div>
      ${queue.length === 0 && html`<p class="note pad">No queued changes. Edits made in the Sheet Browser land here — nothing touches the workbook until Apply.</p>`}
      <ul class="queue">
        ${queue.map((item, i) => html`<li key=${i}>
          ${item.kind === "composite"
            ? html`<div class="composite">
                <div class="comp-head">
                  <span class="badge amber">COMPOSITE</span> ${item.label}
                  <button class="btn tiny danger" onClick=${() => removeItem(i)}>✕</button>
                </div>
                <ul>${item.ops.map((o, j) => html`<li key=${j} class="opline">${opLine(o)}</li>`)}</ul>
              </div>`
            : html`<div class="opline">${opLine(item)}
                <button class="btn tiny danger" onClick=${() => removeItem(i)}>✕</button>
              </div>`}
        </li>`)}
      </ul>
    </div>

    ${busy && html`<div class="loading">Talking to the validation pipeline (dry-run on a temp copy)…</div>`}

    ${valResult && html`<div class="panel">
      <div class="bar"><span class="title">
        ${valResult.ok ? "✓ Batch validated (dry-run + schema clean)" : `✗ ${valResult.status}`}
      </span></div>
      ${(valResult.errors || []).length > 0 && html`<ul class="errlist">
        ${valResult.errors.map((e, i) => html`<li key=${i}>${e}</li>`)}
      </ul>`}
      ${(valResult.warnings || []).length > 0 && html`<div class="warnlist">
        <p class="note pad">Warnings must be explicitly confirmed before Apply:</p>
        ${valResult.warnings.map((w) => html`<label class="warnrow" key=${w.id}>
          <input type="checkbox" checked=${confirmed.has(w.id)}
            onChange=${(e) => setConfirmed((s) => {
              const next = new Set(s);
              if (e.target.checked) next.add(w.id); else next.delete(w.id);
              return next;
            })} />
          <span>${w.message}</span>
        </label>`)}
      </div>`}
    </div>`}

    ${applyResult && html`<div class="panel applied">
      <div class="bar"><span class="title">✓ Applied ${applyResult.applied} op(s) to ${applyResult.sheets.join(", ")}</span></div>
      <dl class="resultmeta">
        <dt>Backup</dt><dd class="mono small">${applyResult.backupPath}</dd>
        <dt>Schema</dt><dd>${applyResult.schemaResult ? `${applyResult.schemaResult.error_count} errors / ${applyResult.schemaResult.warning_count} warnings` : "n/a"}</dd>
        <dt>Log</dt><dd class="mono small">${applyResult.logPath}</dd>
      </dl>
      <div class="pad">
        <p class="note">Workbook saved. Now regenerate + run gates for the touched model(s):</p>
        <pre class="gates">${(applyResult.gateReminders || []).join("\n")}</pre>
      </div>
    </div>`}
  </div>`;
}

/* ── App shell ────────────────────────────────────────────── */

function App() {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [tab, setTab] = useState("structure");
  const [modelKey, setModelKey] = useState(null);
  const [queue, setQueue] = useState([]);
  const [refreshKey, setRefreshKey] = useState(0);
  const [browserFocus, setBrowserFocus] = useState(null);

  const loadPayload = () => fetchJson("/api/workbook")
    .then((d) => {
      setData(d);
      setModelKey((mk) => mk || (d.models.find((m) => m.defaultModel) || d.models[0] || {}).key || null);
    })
    .catch((e) => setError(e.message));

  useEffect(() => { loadPayload(); }, []);

  const onQueue = (item) => setQueue((q) => [...q, item]);
  const removeItem = (i) => setQueue((q) => q.filter((_, j) => j !== i));
  const clearQueue = () => setQueue([]);
  const onApplied = () => { loadPayload().then(() => setRefreshKey((k) => k + 1)); };

  // Review-tab click-through: land on the lint's row in the Sheet Browser.
  const openLintRow = (lint) => {
    const model = (lint.model || "").split("+")[0];
    if (model && data && data.modelSheets[model]) setModelKey(model);
    const query = lint.key && !lint.key.startsWith("row ") ? lint.key.split("+")[0] : "";
    setBrowserFocus({ sheet: lint.sheet, query, ts: Date.now() });
    setTab("browser");
  };

  return html`
    <header class="app">
      <div>
        <h1>Corvette Master Workbook</h1>
        <div class="sub mono">
          ${data ? `${data.workbook.path} · ${data.workbook.sheetCount} sheets · gated writes (Phase 2)` : "loading…"}
        </div>
      </div>
      <nav class="tabs">
        <button class=${tab === "structure" ? "on" : ""} onClick=${() => setTab("structure")}>Form Structure</button>
        <button class=${tab === "browser" ? "on" : ""} onClick=${() => setTab("browser")}>Sheet Browser</button>
        <button class=${tab === "review" ? "on" : ""} onClick=${() => setTab("review")}>Review</button>
        <button class=${tab === "ingest" ? "on" : ""} onClick=${() => setTab("ingest")}>Ingest Review</button>
        <button class=${tab === "pending" ? "on" : ""} onClick=${() => setTab("pending")}>
          Pending Changes${queue.length ? ` (${queue.length})` : ""}</button>
      </nav>
    </header>
    <main>
      ${error && html`<div class="error">Failed to load workbook payload: ${error}</div>`}
      ${!data && !error && html`<div class="loading">Loading workbook…</div>`}
      ${data && modelKey && tab === "structure" &&
        html`<${StructureTab} data=${data} modelKey=${modelKey} setModelKey=${setModelKey} />`}
      ${data && modelKey && tab === "browser" &&
        html`<${BrowserTab} data=${data} modelKey=${modelKey} setModelKey=${setModelKey}
               onQueue=${onQueue} focus=${browserFocus} onFocusConsumed=${() => setBrowserFocus(null)}
               key=${refreshKey} />`}
      ${data && tab === "review" &&
        html`<${ReviewTab} onOpenRow=${openLintRow} key=${"review" + refreshKey} />`}
      ${data && tab === "ingest" &&
        html`<${IngestReviewTab} key=${"ingest" + refreshKey} />`}
      ${data && tab === "pending" &&
        html`<${PendingTab} data=${data} queue=${queue} removeItem=${removeItem}
               clearQueue=${clearQueue} onApplied=${onApplied} />`}
    </main>`;
}

render(html`<${App} />`, document.getElementById("app"));
