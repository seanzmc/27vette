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

function fmt(v) {
  if (v === null || v === undefined || v === "") return html`<span class="dim">—</span>`;
  if (v === true) return "True";
  if (v === false) return "False";
  return String(v);
}

/* ── Form Structure tab ───────────────────────────────────── */

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

function SheetTable({ data, name }) {
  const [sheet, setSheet] = useState(null);
  const [error, setError] = useState(null);
  const [query, setQuery] = useState("");
  const [page, setPage] = useState(0);
  const [open, setOpen] = useState(null);

  useEffect(() => {
    setSheet(null); setError(null); setQuery(""); setPage(0); setOpen(null);
    fetchJson(`/api/sheet/${encodeURIComponent(name)}`).then(setSheet).catch((e) => setError(e.message));
  }, [name]);

  const meta = data.sheets.find((s) => s.name === name) || {};
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

  return html`<div class="panel">
    <div class="bar">
      <span class="title">${name}</span>
      ${meta.keyCols && html`<span class="badge">key: ${meta.keyCols.join(" + ")}</span>`}
      ${meta.readOnly && html`<span class="badge">read-only</span>`}
      <span class="meta">${filtered.length} / ${meta.rowCount ?? "?"} rows${extra > 0 ? ` · +${extra} more cols in row detail` : ""}</span>
      <input type="search" placeholder="Filter rows…" value=${query}
        onInput=${(e) => { setQuery(e.target.value); setPage(0); setOpen(null); }} />
    </div>
    ${error && html`<div class="error">${error}</div>`}
    ${!sheet && !error && html`<div class="loading">Loading ${name}…</div>`}
    ${sheet && html`<div class="tablewrap"><table>
      <thead><tr>${cols.map((c) => html`<th key=${c}>${c}</th>`)}</tr></thead>
      <tbody>
        ${rows.length === 0 && html`<tr><td colSpan=${cols.length} class="dim">No rows match.</td></tr>`}
        ${rows.map((r, i) => {
          const idx = safePage * PAGE_SIZE + i;
          return html`
            <tr class="row" key=${idx} onClick=${() => setOpen(open === idx ? null : idx)}>
              ${cols.map((c) => html`<td key=${c} title=${String(r[c] ?? "")}>${fmt(r[c])}</td>`)}
            </tr>
            ${open === idx && html`<tr class="detail"><td colSpan=${cols.length}>
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

function BrowserTab({ data, modelKey, setModelKey }) {
  const modelEntries = data.modelSheets[modelKey] || [];
  const [sheetName, setSheetName] = useState(modelEntries[0]?.sheet || null);

  useEffect(() => {
    const entries = data.modelSheets[modelKey] || [];
    setSheetName(entries[0]?.sheet || null);
  }, [modelKey]);

  const modelSheetNames = new Set(modelEntries.map((e) => e.sheet));
  const otherSheets = data.sheets.map((s) => s.name).filter((n) => !modelSheetNames.has(n)).sort();

  return html`
    <div class="pills">
      ${data.models.map((m) => html`
        <button
          class=${"pill" + (m.key === modelKey ? " on" : "") + (m.active ? "" : " scaffold")}
          onClick=${() => setModelKey(m.key)} key=${m.key}
        >${m.label}${m.active ? "" : " · scaffold"}</button>`)}
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
    ${sheetName
      ? html`<${SheetTable} data=${data} name=${sheetName} key=${sheetName} />`
      : html`<p class="note">No registered source sheets for this model — pick one from “other sheets…”.</p>`}`;
}

/* ── App shell ────────────────────────────────────────────── */

function App() {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [tab, setTab] = useState("structure");
  const [modelKey, setModelKey] = useState(null);

  useEffect(() => {
    fetchJson("/api/workbook")
      .then((d) => {
        setData(d);
        const first = d.models.find((m) => m.defaultModel) || d.models[0];
        setModelKey(first ? first.key : null);
      })
      .catch((e) => setError(e.message));
  }, []);

  return html`
    <header class="app">
      <div>
        <h1>Corvette Master Workbook — Review</h1>
        <div class="sub mono">
          ${data ? `${data.workbook.path} · ${data.workbook.sheetCount} sheets · read-only (Phase 1)` : "loading…"}
        </div>
      </div>
      <nav class="tabs">
        <button class=${tab === "structure" ? "on" : ""} onClick=${() => setTab("structure")}>Form Structure</button>
        <button class=${tab === "browser" ? "on" : ""} onClick=${() => setTab("browser")}>Sheet Browser</button>
      </nav>
    </header>
    <main>
      ${error && html`<div class="error">Failed to load workbook payload: ${error}</div>`}
      ${!data && !error && html`<div class="loading">Loading workbook…</div>`}
      ${data && modelKey && tab === "structure" &&
        html`<${StructureTab} data=${data} modelKey=${modelKey} setModelKey=${setModelKey} />`}
      ${data && modelKey && tab === "browser" &&
        html`<${BrowserTab} data=${data} modelKey=${modelKey} setModelKey=${setModelKey} />`}
    </main>`;
}

render(html`<${App} />`, document.getElementById("app"));
