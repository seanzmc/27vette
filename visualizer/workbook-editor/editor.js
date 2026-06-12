import { h, render } from "preact";
import { useEffect, useMemo, useState } from "preact/hooks";
import htm from "htm";

const html = htm.bind(h);
const PAGE_SIZE = 100;

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

function SheetTable({ data, name, onQueue }) {
  const [sheet, setSheet] = useState(null);
  const [error, setError] = useState(null);
  const [query, setQuery] = useState("");
  const [page, setPage] = useState(0);
  const [open, setOpen] = useState(null);
  const [editing, setEditing] = useState(null); // {mode, initial}

  useEffect(() => {
    setSheet(null); setError(null); setQuery(""); setPage(0); setOpen(null); setEditing(null);
    fetchJson(`/api/sheet/${encodeURIComponent(name)}`).then(setSheet).catch((e) => setError(e.message));
  }, [name]);

  const meta = data.sheets.find((s) => s.name === name) || {};
  const editable = meta.readOnly === false;
  const isOptionsFamily = meta.family === "options";
  const filtered = useMemo(() => {
    if (!sheet) return [];
    const q = query.trim().toLowerCase();
    if (!q) return sheet.rows;
    return sheet.rows.filter((r) =>
      Object.values(r).some((v) => String(v ?? "").toLowerCase().includes(q)),
    );
  }, [sheet, query]);

  const pages = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
  const safePage = Math.min(page, pages - 1);
  const rows = filtered.slice(safePage * PAGE_SIZE, safePage * PAGE_SIZE + PAGE_SIZE);
  const cols = sheet ? sheet.headers.slice(0, 8) : [];
  const extra = sheet ? sheet.headers.length - cols.length : 0;

  const queueDelete = (row) => {
    const keyCols = meta.keyCols || [];
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
      <input type="search" placeholder="Filter rows…" value=${query}
        onInput=${(e) => { setQuery(e.target.value); setPage(0); setOpen(null); }} />
    </div>
    ${error && html`<div class="error">${error}</div>`}
    ${!sheet && !error && html`<div class="loading">Loading ${name}…</div>`}
    ${editing && html`<${RowForm} data=${data} sheetName=${name} mode=${editing.mode}
        initial=${editing.initial} onQueue=${onQueue} onCancel=${() => setEditing(null)} />`}
    ${sheet && html`<div class="tablewrap"><table>
      <thead><tr>
        ${cols.map((c) => html`<th key=${c}>${c}</th>`)}
        ${editable && html`<th class="actions-col">actions</th>`}
      </tr></thead>
      <tbody>
        ${rows.length === 0 && html`<tr><td colSpan=${cols.length + 1} class="dim">No rows match.</td></tr>`}
        ${rows.map((r, i) => {
          const idx = safePage * PAGE_SIZE + i;
          return html`
            <tr class="row" key=${idx} onClick=${() => setOpen(open === idx ? null : idx)}>
              ${cols.map((c) => html`<td key=${c} title=${String(r[c] ?? "")}>${fmt(r[c])}</td>`)}
              ${editable && html`<td class="actions-col" onClick=${(e) => e.stopPropagation()}>
                <button class="btn tiny" title="Edit"
                  onClick=${() => setEditing({ mode: "edit", initial: r })}>✎</button>
                <button class="btn tiny danger" title="Delete" onClick=${() => queueDelete(r)}>🗑</button>
              </td>`}
            </tr>
            ${open === idx && html`<tr class="detail"><td colSpan=${cols.length + 1}>
              <dl>${sheet.headers.map((hcol) => html`
                <dt key=${"t" + hcol}>${hcol}</dt><dd key=${"d" + hcol}>${fmt(r[hcol])}</dd>`)}
              </dl>
            </td></tr>`}`;
        })}
      </tbody>
    </table></div>
    <div class="pager">
      <button disabled=${safePage === 0} onClick=${() => { setPage(safePage - 1); setOpen(null); }}>‹ Prev</button>
      <span>page ${safePage + 1} / ${pages}</span>
      <button disabled=${safePage >= pages - 1} onClick=${() => { setPage(safePage + 1); setOpen(null); }}>Next ›</button>
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

function BrowserTab({ data, modelKey, setModelKey, onQueue }) {
  const modelEntries = data.modelSheets[modelKey] || [];
  const [sheetName, setSheetName] = useState(modelEntries[0]?.sheet || null);
  const [wizard, setWizard] = useState(null); // "option" | "rule" | "exclusive"

  useEffect(() => {
    const entries = data.modelSheets[modelKey] || [];
    setSheetName(entries[0]?.sheet || null);
    setWizard(null);
  }, [modelKey]);

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
      ? html`<${SheetTable} data=${data} name=${sheetName} key=${sheetName} onQueue=${onQueue} />`
      : html`<p class="note">No registered source sheets for this model — pick one from “other sheets…”.</p>`}`;
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
               onQueue=${onQueue} key=${refreshKey} />`}
      ${data && tab === "pending" &&
        html`<${PendingTab} data=${data} queue=${queue} removeItem=${removeItem}
               clearQueue=${clearQueue} onApplied=${onApplied} />`}
    </main>`;
}

render(html`<${App} />`, document.getElementById("app"));
