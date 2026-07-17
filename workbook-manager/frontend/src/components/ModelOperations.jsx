import React, { useEffect, useMemo, useRef, useState } from "react";
import {
  Columns2, PlusCircle, Pencil, Search, Table2, Trash2, TriangleAlert,
} from "lucide-react";
import { api } from "../api.js";
import { tableViewModel } from "../tableRegistry.js";
import RecordForm from "./RecordForm.jsx";

export default function ModelOperations({ models, modelKey, setModelKey, onChanged }) {
  const [tables, setTables] = useState([]);
  const [role, setRole] = useState("options");
  const [schema, setSchema] = useState(null);
  const [rows, setRows] = useState([]);
  const [total, setTotal] = useState(0);
  const [offset, setOffset] = useState(0);
  const [search, setSearch] = useState("");
  const [editing, setEditing] = useState(null);
  const [compare, setCompare] = useState([]); // selected row ids for diff
  const [deps, setDeps] = useState(null);     // dependency dialog state
  const [notice, setNotice] = useState(null);
  const [tableState, setTableState] = useState({ status: "loading", error: "" });
  const [recordState, setRecordState] = useState({ status: "idle", error: "" });
  const searchTimer = useRef(null);
  const tableRequestRef = useRef(0);
  const recordRequestRef = useRef(0);
  const LIMIT = 100;

  const activeTable = tables.find((table) => table.key === role);

  const loadTables = async (selectedModel = modelKey) => {
    const requestId = ++tableRequestRef.current;
    ++recordRequestRef.current;
    setTableState({ status: "loading", error: "" });
    setRecordState({ status: "idle", error: "" });
    setTables([]);
    setSchema(null);
    setRows([]);
    setTotal(0);
    try {
      const response = await api.tables(selectedModel);
      if (requestId !== tableRequestRef.current) return;
      const registryTables = response.tables.map(tableViewModel);
      setTables(registryTables);
      if (!registryTables.some((table) => table.key === role)) {
        setRole(registryTables[0]?.key || "");
      }
      setTableState({ status: "ready", error: "" });
    } catch (error) {
      if (requestId !== tableRequestRef.current) return;
      setTables([]);
      setSchema(null);
      setRows([]);
      setTotal(0);
      setTableState({ status: "error", error: error.message });
    }
  };

  useEffect(() => {
    loadTables(modelKey);
    return () => {
      clearTimeout(searchTimer.current);
      ++tableRequestRef.current;
      ++recordRequestRef.current;
    };
  }, [modelKey]); // eslint-disable-line

  const loadRows = async (tableRole = role, s = search, o = offset) => {
    if (!tableRole) return;
    const requestId = ++recordRequestRef.current;
    setRecordState({ status: "loading", error: "" });
    try {
      const spec = await api.schema(tableRole, modelKey);
      if (requestId !== recordRequestRef.current) return;
      const resp = await api.records(tableRole, {
        model: modelKey, search: s, limit: LIMIT, offset: o,
      });
      if (requestId !== recordRequestRef.current) return;
      setSchema(spec);
      setRows(resp.records);
      setTotal(resp.total);
      setRecordState({ status: "ready", error: "" });
    } catch (error) {
      if (requestId !== recordRequestRef.current) return;
      setSchema(null);
      setRows([]);
      setTotal(0);
      setRecordState({ status: "error", error: error.message });
    }
  };

  useEffect(() => {
    setOffset(0);
    setCompare([]);
    setEditing(null);
    setDeps(null);
    if (tableState.status === "ready" && role) {
      loadRows(role, search, 0);
    }
    return () => { ++recordRequestRef.current; };
  }, [role, modelKey, tableState.status]); // eslint-disable-line

  const onSearch = (value) => {
    setSearch(value);
    clearTimeout(searchTimer.current);
    searchTimer.current = setTimeout(() => {
      setOffset(0);
      loadRows(role, value, 0);
    }, 250);
  };

  const previewCols = useMemo(() => {
    if (!schema) return [];
    const keys = schema.columns.filter((c) => c.is_key);
    const rest = schema.columns.filter((c) => !c.is_key);
    return [...keys, ...rest].slice(0, 7);
  }, [schema]);

  const stageDelete = async (row, confirm = false) => {
    try {
      await api.stage({
        table_role: role,
        model_key: modelKey,
        op: "delete",
        key: Object.fromEntries(schema.key.map((k) => [k, String(row[k] ?? "")])),
        confirm_dependencies: confirm,
      });
      setDeps(null);
      setNotice({ kind: "ok", text: "Delete staged. Review it in Changes & Sync." });
      onChanged();
    } catch (e) {
      const blocked = e.detail?.errors?.find((x) => x.dependents?.length);
      if (blocked && !confirm) {
        setDeps({ row, dependents: blocked.dependents });
      } else {
        setNotice({ kind: "err", text: e.message });
      }
    }
  };

  const toggleCompare = (row) =>
    setCompare((cur) => {
      const id = row.id;
      if (cur.some((r) => r.id === id)) return cur.filter((r) => r.id !== id);
      return [...cur.slice(-1), row]; // keep at most two
    });

  const staged = async () => {
    setEditing(null);
    setNotice({ kind: "ok", text: "Change staged. Review it in Changes & Sync." });
    await loadRows();
    onChanged();
  };

  return (
    <div>
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
      <div className="pill-row">
        {tableState.status === "loading" && (
          <span className="muted" role="status">Loading canonical tables…</span>
        )}
        {tableState.status === "error" && (
          <div className="notice err" role="alert">
            <strong>Unable to load canonical tables.</strong>{" "}
            {tableState.error}
            <button className="btn small" style={{ marginLeft: 10 }} onClick={() => loadTables(modelKey)}>Retry</button>
          </div>
        )}
        {tableState.status === "ready" && tables.length === 0 && (
          <span className="muted">No canonical tables are registered for this model.</span>
        )}
        {tableState.status === "ready" && tables.map((table) => (
          <button
            key={table.key}
            className={`pill ${table.key === role ? "active" : ""}`}
            title={`source: ${table.sourceLabel}`}
            onClick={() => setRole(table.key)}
          >
            {table.label}
            <span className="count">{table.count}</span>
            {!table.editable ? " ·read-only" : ""}
          </button>
        ))}
      </div>

      <div className="panel">
        <div className="panel-head">
          <div className="toolbar">
            <Table2 size={15} color="var(--blue)" />
            <strong>{activeTable?.label || role}</strong>
            {activeTable && (
              <>
                <span className="chip blue mono">SQL · {activeTable.sqlTable}</span>
                <span className="chip mono">Source · {activeTable.sourceLabel}</span>
              </>
            )}
            {schema && (
              <span className="chip">key: {schema.key.join(" + ")}</span>
            )}
            {activeTable && !activeTable.editable && (
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
                onChange={(e) => onSearch(e.target.value)}
                disabled={!activeTable || recordState.status === "loading"}
              />
            </div>
            <button
              className="btn green small"
              disabled={!activeTable?.editable || recordState.status === "loading"}
              onClick={() => setEditing({ mode: "add", initial: null })}
            >
              <PlusCircle size={14} /> Add
            </button>
          </div>
        </div>

        <div style={{ overflowX: "auto" }}>
          <table className="data">
            <thead>
              <tr>
                <th title="compare"><Columns2 size={12} /></th>
                {previewCols.map((c) => <th key={c.name}>{c.label}</th>)}
                <th style={{ textAlign: "right" }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {recordState.status === "loading" && (
                <tr>
                  <td colSpan={previewCols.length + 2} className="empty" role="status">
                    Loading records…
                  </td>
                </tr>
              )}
              {recordState.status === "error" && (
                <tr>
                  <td colSpan={previewCols.length + 2}>
                    <div className="notice err" role="alert">
                      <strong>Unable to load records.</strong>{" "}
                      {recordState.error}
                      <button className="btn small" style={{ marginLeft: 10 }} onClick={() => loadRows(role, search, offset)}>Retry</button>
                    </div>
                  </td>
                </tr>
              )}
              {recordState.status === "idle" && (
                <tr>
                  <td colSpan={previewCols.length + 2} className="empty">
                    Choose a canonical table to inspect its records.
                  </td>
                </tr>
              )}
              {recordState.status === "ready" && rows.length === 0 && (
                <tr>
                  <td colSpan={previewCols.length + 2} className="empty">
                    No records{search ? " match the search" : ""}.
                  </td>
                </tr>
              )}
              {recordState.status === "ready" && rows.map((r) => (
                <tr key={r.id} className={compare.some((x) => x.id === r.id) ? "selected" : ""}>
                  <td>
                    <input
                      type="checkbox"
                      checked={compare.some((x) => x.id === r.id)}
                      onChange={() => toggleCompare(r)}
                    />
                  </td>
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
                        title="Edit"
                        disabled={!activeTable?.editable}
                        onClick={() => setEditing({ mode: "edit", initial: r })}
                      >
                        <Pencil size={14} />
                      </button>
                      <button
                        className="icon-btn danger"
                        title="Stage delete"
                        disabled={!activeTable?.editable}
                        onClick={() => stageDelete(r)}
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
                disabled={offset === 0}
                onClick={() => { const o = Math.max(0, offset - LIMIT); setOffset(o); loadRows(role, search, o); }}
              >
                ‹ Prev
              </button>
              <button
                className="btn small"
                disabled={offset + LIMIT >= total}
                onClick={() => { const o = offset + LIMIT; setOffset(o); loadRows(role, search, o); }}
              >
                Next ›
              </button>
            </div>
          )}
        </div>
      </div>

      {notice && <div className={`notice ${notice.kind}`}>{notice.text}</div>}

      {compare.length === 2 && schema && (
        <div className="panel" style={{ marginTop: 14 }}>
          <div className="panel-head">
            <strong>Record Comparison</strong>
            <button className="btn small" onClick={() => setCompare([])}>Clear</button>
          </div>
          <div className="diff-grid">
            <div className="head">Field</div>
            <div className="head mono">{compare[0][schema.key[0]]}</div>
            <div className="head mono">{compare[1][schema.key[0]]}</div>
            {schema.columns.map((c) => {
              const a = String(compare[0][c.name] ?? "");
              const b = String(compare[1][c.name] ?? "");
              const changed = a !== b;
              return (
                <React.Fragment key={c.name}>
                  <div className="field-name">{c.name}</div>
                  <div className={changed ? "changed" : ""}>{a || "—"}</div>
                  <div className={changed ? "changed" : ""}>{b || "—"}</div>
                </React.Fragment>
              );
            })}
          </div>
        </div>
      )}

      {editing && schema && (
        <div style={{ marginTop: 14 }}>
          <RecordForm
            key={`${role}-${editing.mode}-${editing.initial?.id ?? "new"}`}
            schema={schema}
            mode={editing.mode}
            initial={editing.initial}
            modelKey={modelKey}
            stageFn={api.stage}
            onStaged={staged}
            onCancel={() => setEditing(null)}
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
                    <td>{d.table_role}</td>
                    <td className="mono">{d.entity_key}</td>
                    <td className="mono faint">{d.field}</td>
                    <td className="mono faint">
                      {d.source_sheet} · {d.source_row}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            <div className="toolbar" style={{ marginTop: 12 }}>
              <button className="btn danger" onClick={() => stageDelete(deps.row, true)}>
                <Trash2 size={14} /> Stage delete anyway (I will resolve dependents)
              </button>
              <span className="muted">
                Deleting without resolving these leaves unresolved references
                that batch validation will flag before commit.
              </span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
