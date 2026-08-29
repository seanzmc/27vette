import React, { useEffect, useMemo, useRef, useState } from "react";
import {
  PlusCircle, Pencil, Search, Table2, Trash2, TriangleAlert,
} from "lucide-react";
import { api } from "../api.js";
import { displayId } from "../naming.js";
import RecordForm from "./RecordForm.jsx";

export default function ModelOperations({
  models, modelKey, setModelKey, draftId, draftMutable, onChanged,
  collectionsOverride = null, showModels = true,
}) {
  const [collections, setCollections] = useState([]);
  const [table, setTable] = useState("options");
  const [schema, setSchema] = useState(null);
  const [rows, setRows] = useState([]);
  const [total, setTotal] = useState(0);
  const [offset, setOffset] = useState(0);
  const [search, setSearch] = useState("");
  const [editing, setEditing] = useState(null);
  const [deps, setDeps] = useState(null);     // dependency dialog state
  const [notice, setNotice] = useState(null);
  const [loadedIdentity, setLoadedIdentity] = useState(null);
  const searchTimer = useRef(null);
  const loadToken = useRef(0);
  const LIMIT = 100;

  const activeCollection = collections.find((c) => c.table === table);
  const dataReady = loadedIdentity?.table === table
    && loadedIdentity?.modelKey === modelKey;

  useEffect(() => {
    (async () => {
      const next = collectionsOverride || (await api.collections(modelKey)).collections;
      setCollections(next);
      if (!next.some((x) => x.table === table)) {
        setTable(next[0]?.table || "options");
      }
    })();
  }, [modelKey, collectionsOverride]); // eslint-disable-line

  const loadRows = async (t = table, s = search, o = offset) => {
    const token = ++loadToken.current;
    const spec = await api.schema(t, modelKey);
    const resp = await api.records(t, {
      model: modelKey, search: s, limit: LIMIT, offset: o,
    });
    if (token !== loadToken.current) return;
    setSchema(spec);
    setRows(resp.records);
    setTotal(resp.total);
    setLoadedIdentity({ table: t, modelKey });
  };

  useEffect(() => {
    ++loadToken.current;
    setOffset(0);
    setEditing(null);
    setDeps(null);
    setLoadedIdentity(null);
    loadRows(table, search, 0);
  }, [table, modelKey]); // eslint-disable-line

  const onSearch = (value) => {
    setSearch(value);
    clearTimeout(searchTimer.current);
    searchTimer.current = setTimeout(() => {
      setOffset(0);
      loadRows(table, value, 0);
    }, 250);
  };

  const previewCols = useMemo(() => {
    if (!schema) return [];
    const keys = schema.columns.filter((c) => c.is_key);
    const active = schema.columns.filter((c) => !c.is_key && c.name === "active");
    const rest = schema.columns.filter((c) => !c.is_key && c.name !== "active");
    return [...keys, ...active, ...rest].slice(0, 7);
  }, [schema]);

  const saveDraft = (payload) => api.saveDraftOperation(draftId, {
    ...payload,
    actor: "workbook-manager-ui",
    session_id: "browser",
  });

  const capability = (action) => activeCollection?.capabilities?.[action] || {
    allowed: Boolean(activeCollection?.editable),
    blocked_reason: activeCollection?.editable ? "" : "This family is read-only.",
  };

  const editorEvidence = (row, dependents = []) => [
    `Lineage: ${row?.src_sheet || activeCollection?.sheet || "new row"}${row?.src_row ? ` · row ${row.src_row}` : ""}`,
    `Scope: ${row?.model_key || row?.model_id || row?.model_context?.join(", ") || (activeCollection?.shared ? "shared" : modelKey)}`,
    `Dependencies: ${dependents.length ? `${dependents.length} projected dependent record(s)` : "none found by the registered dependency contract"}`,
    `Active state: ${row?.active ?? "set in the authored fields below"}`,
    `Generated impact: ${activeCollection?.generated_impact || "verified during guarded Apply and Rebuild"}`,
  ];

  const openEditor = async (mode, row = null) => {
    const action = mode === "add" ? "create" : "update";
    if (!dataReady || !capability(action).allowed) return;
    try {
      let dependents = [];
      if (row && schema) {
        const key = Object.fromEntries(
          schema.key.map((name) => [name, String(row[name] ?? "")])
        );
        const result = await api.dependencies(
          table,
          schema.model_context?.required ? (schema.model_context.value || modelKey) : "",
          key,
        );
        dependents = result.dependents || [];
      }
      setEditing({ mode, initial: row, evidence: editorEvidence(row, dependents) });
    } catch (error) {
      setNotice({ kind: "err", text: `Cannot inspect registered dependencies: ${error.message}` });
    }
  };

  const saveDelete = async (row) => {
    if (!dataReady) return;
    try {
      await saveDraft({
        table,
        model_id: schema.model_context?.required
          ? (schema.model_context.value || modelKey)
          : "",
        op: "delete",
        key: Object.fromEntries(schema.key.map((k) => [k, String(row[k] ?? "")])),
      });
      setDeps(null);
      setNotice({ kind: "ok", text: "Delete saved to the durable draft. Review the complete graph in Review & Apply." });
      onChanged();
    } catch (e) {
      setNotice({ kind: "err", text: e.message });
    }
  };

  const inspectDelete = async (row) => {
    if (!dataReady) return;
    const key = Object.fromEntries(schema.key.map((name) => [name, String(row[name] ?? "")]));
    try {
      const result = await api.dependencies(
        table,
        schema.model_context?.required ? (schema.model_context.value || modelKey) : "",
        key,
      );
      if (result.dependents.length) {
        setDeps({ row, dependents: result.dependents });
      } else {
        await saveDelete(row);
      }
    } catch (e) {
      setNotice({ kind: "err", text: e.message });
    }
  };


  const saved = async (operation) => {
    setEditing(null);
    setNotice({
      kind: "ok",
      text: operation
        ? "Change saved to the durable draft. Review it in Review & Apply."
        : "No effective draft changes remain.",
    });
    await loadRows();
    onChanged();
  };

  return (
    <div>
      {showModels && (
        <div className="pill-row">
          {models.map((m) => (
            <button
              key={m.model_key}
              className={`pill ${m.model_key === modelKey ? "active" : ""} ${m.scaffold ? "disabled" : ""}`}
              onClick={() => setModelKey(m.model_key)}
            >
              {m.label}{m.scaffold ? " · scaffold" : ""}
            </button>
          ))}
        </div>
      )}
      <div className="pill-row">
        {collections.map((c) => (
          <button
            key={c.table}
            className={`pill ${c.table === table ? "active" : ""}`}
            title={c.sheet ? `sheet: ${c.sheet}` : "shared reference data"}
            onClick={() => setTable(c.table)}
          >
            {c.label}
            <span className="count">{c.count}</span>
            {c.shared ? " ·shared" : ""}
            {!c.editable ? " ·read-only" : ""}
          </button>
        ))}
      </div>

      {collectionsOverride && activeCollection && (
        <div className="panel structure-family-context">
          <div className="panel-body">
            <strong>{activeCollection.label}</strong>
            <p>{activeCollection.description}</p>
            <div className="tags">
              <span className="chip">
                {activeCollection.context === "shared" ? "Shared context" : `Model context · ${modelKey}`}
              </span>
              <span className="chip mono">{activeCollection.sheet}</span>
            </div>
            <p className="muted">{activeCollection.generated_impact}</p>
          </div>
        </div>
      )}

      <div className="panel">
        <div className="panel-head">
          <div className="toolbar">
            <Table2 size={15} color="var(--blue)" />
            <strong>{activeCollection?.label || table}</strong>
            {activeCollection?.sheet && (
              <span className="mono faint">({activeCollection.sheet})</span>
            )}
            {dataReady && schema && (
              <span className="chip">key: {schema.key.join(" + ")}</span>
            )}
            {activeCollection && !activeCollection.editable && (
              <span className="chip warn">read-only</span>
            )}
          </div>
          <div className="toolbar">
            <div style={{ position: "relative" }}>
              <Search
                size={13}
                style={{ position: "absolute", left: 8, top: 9, color: "var(--text-faint)" }}
              />
              <input
                className="text"
                style={{ paddingLeft: 26, width: 220 }}
                placeholder="Search all fields…"
                value={search}
                disabled={!dataReady}
                onChange={(e) => onSearch(e.target.value)}
              />
            </div>
            <button
              className="btn green small"
              disabled={!dataReady || !capability("create").allowed || !draftMutable}
              title={capability("create").blocked_reason || "Add a registered record"}
              onClick={() => openEditor("add")}
            >
              <PlusCircle size={14} /> Add
            </button>
          </div>
        </div>

        <div style={{ overflowX: "auto" }}>
          <table className="data">
            <thead>
              <tr>
                {previewCols.map((c) => <th key={c.name}>{c.label}</th>)}
                <th style={{ textAlign: "right" }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {!dataReady && (
                <tr>
                  <td colSpan={previewCols.length + 1} className="empty">
                    Loading registered family…
                  </td>
                </tr>
              )}
              {dataReady && rows.length === 0 && (
                <tr>
                  <td colSpan={previewCols.length + 1} className="empty">
                    No records{search ? " match the search" : ""}.
                  </td>
                </tr>
              )}
              {dataReady && rows.map((r) => (
                <tr key={r.id}>
                  {previewCols.map((c) => (
                    <td key={c.name} title={r[c.name]}>
                      {c.is_key && c.name === schema.key[0] ? (
                        <span title={`display: ${r._display_id}`}>{r[c.name]}</span>
                      ) : (
                        r[c.name] || <span className="faint">—</span>
                      )}
                    </td>
                  ))}
                  <td>
                    <div className="row-actions">
                      <button
                        className="icon-btn"
                        title={capability("update").blocked_reason || "Edit"}
                        disabled={!dataReady || !capability("update").allowed || !draftMutable}
                        onClick={() => openEditor("edit", r)}
                      >
                        <Pencil size={14} />
                      </button>
                      <button
                        className="icon-btn danger"
                        title={capability("delete").blocked_reason || "Save delete to draft"}
                        disabled={!dataReady || !capability("delete").allowed || !draftMutable}
                        onClick={() => inspectDelete(r)}
                      >
                        <Trash2 size={14} />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div className="panel-head" style={{ borderTop: "1px solid var(--border)", borderBottom: 0 }}>
          <span className="muted">
            {total} record{total === 1 ? "" : "s"}
            {total > LIMIT && ` · showing ${offset + 1}–${Math.min(offset + LIMIT, total)}`}
          </span>
          {total > LIMIT && (
            <div className="toolbar">
              <button
                className="btn small"
                disabled={!dataReady || offset === 0}
                onClick={() => { const o = Math.max(0, offset - LIMIT); setOffset(o); loadRows(table, search, o); }}
              >
                ‹ Prev
              </button>
              <button
                className="btn small"
                disabled={!dataReady || offset + LIMIT >= total}
                onClick={() => { const o = offset + LIMIT; setOffset(o); loadRows(table, search, o); }}
              >
                Next ›
              </button>
            </div>
          )}
        </div>
      </div>

      {notice && <div className={`notice ${notice.kind}`}>{notice.text}</div>}


      {dataReady && editing && schema && (
        <div style={{ marginTop: 14 }}>
          <RecordForm
            key={`${table}-${editing.mode}-${editing.initial?.id ?? "new"}`}
            schema={schema}
            mode={editing.mode}
            initial={editing.initial}
            modelKey={modelKey}
            saveFn={saveDraft}
            onSaved={saved}
            onCancel={() => setEditing(null)}
            evidence={editing.evidence}
          />
        </div>
      )}

      {deps && (
        <div className="panel" style={{ marginTop: 14, borderColor: "var(--red)" }}>
          <div className="panel-head">
            <strong style={{ color: "var(--red)", display: "flex", gap: 6, alignItems: "center" }}>
              <TriangleAlert size={15} /> Delete blocked — {deps.dependents.length} dependent record(s)
            </strong>
            <button className="btn small" onClick={() => setDeps(null)}>Cancel</button>
          </div>
          <div className="panel-body">
            <table className="data">
              <thead>
                <tr><th>Table</th><th>Record</th><th>Via Field</th><th>Sheet · Row</th></tr>
              </thead>
              <tbody>
                {deps.dependents.map((d, i) => (
                  <tr key={i}>
                    <td>{d.table}</td>
                    <td className="mono">{d.entity_key}</td>
                    <td className="mono faint">{d.field}</td>
                    <td className="mono faint">{d.src_sheet} · {d.src_row}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            <p className="muted" style={{ marginTop: 12 }}>
              Delete the parent and every listed dependent together through one
              draft ChangeSet. Final-graph preview refuses an incomplete delete.
            </p>
            <button className="btn danger small" onClick={() => saveDelete(deps.row)}>
              <Trash2 size={14} /> Save parent delete to draft
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
