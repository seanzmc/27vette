import React, { useEffect, useMemo, useRef, useState } from "react";
import {
  PlusCircle, Pencil, Search, Table2, Trash2, TriangleAlert,
} from "lucide-react";
import { api } from "../api.js";
import {
  dependencyDeletionOperations, optionCreationPlan,
} from "../graphOperationsModel.js";
import { fieldLabel } from "../naming.js";
import { operationModelId } from "../operationScope.js";
import RecordForm from "./RecordForm.jsx";

export default function ModelOperations({
  models, modelKey, setModelKey, draftId, draftMutable, onChanged,
  collectionsOverride = null, showModels = true,
  navigation = null, onNavigationChange = null,
}) {
  const [collections, setCollections] = useState([]);
  const [table, setTable] = useState(() => navigation?.collection || "options");
  const [schema, setSchema] = useState(null);
  const [rows, setRows] = useState([]);
  const [total, setTotal] = useState(0);
  const [offset, setOffset] = useState(() => Number(navigation?.offset || 0));
  const [search, setSearch] = useState(() => navigation?.query || "");
  const [editing, setEditing] = useState(null);
  const [deps, setDeps] = useState(null);     // dependency dialog state
  const [guidedOption, setGuidedOption] = useState(null);
  const [rawConfirm, setRawConfirm] = useState(null);
  const [undoDelete, setUndoDelete] = useState(null);
  const [notice, setNotice] = useState(null);
  const [loadedIdentity, setLoadedIdentity] = useState(null);
  const searchTimer = useRef(null);
  const loadToken = useRef(0);
  const LIMIT = 100;

  const activeCollection = collections.find((c) => c.table === table);
  const dataReady = loadedIdentity?.table === table
    && loadedIdentity?.modelKey === modelKey;

  const preserveAdvancedContext = (changes) => {
    if (!navigation || !onNavigationChange) return;
    onNavigationChange({
      ...navigation,
      collection: table,
      query: search,
      offset,
      editor: navigation.editor || "",
      ...changes,
    }, { replace: true, state: window.history.state || {} });
  };

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
    const restoredOffset = navigation?.collection === table
      ? Number(navigation?.offset || 0)
      : 0;
    const restoredSearch = navigation?.collection === table
      ? String(navigation?.query || "")
      : search;
    setOffset(restoredOffset);
    setSearch(restoredSearch);
    setEditing(null);
    setDeps(null);
    setGuidedOption(null);
    setRawConfirm(null);
    setLoadedIdentity(null);
    loadRows(table, restoredSearch, restoredOffset);
  }, [table, modelKey]); // eslint-disable-line

  const onSearch = (value) => {
    setSearch(value);
    preserveAdvancedContext({ query: value, offset: 0 });
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
      let optionContext = null;
      if (row && schema) {
        const key = Object.fromEntries(
          schema.key.map((name) => [name, String(row[name] ?? "")])
        );
        const result = await api.dependencies(
          table,
          operationModelId(schema, row, modelKey),
          key,
        );
        dependents = result.dependents || [];
      } else if (mode === "add" && table === "options") {
        optionContext = await api.guidedOptionContext(modelKey);
      }
      const editorKey = row && schema
        ? schema.key.map((name) => String(row[name] ?? "")).join("/")
        : "new";
      preserveAdvancedContext({ editor: editorKey });
      setEditing({
        mode, initial: row, evidence: editorEvidence(row, dependents), optionContext,
      });
    } catch (error) {
      setNotice({ kind: "err", text: `Cannot inspect registered dependencies: ${error.message}` });
    }
  };

  const saveEditorDraft = async (payload) => {
    if (table === "options" && editing?.mode === "add" && editing.optionContext) {
      setGuidedOption({
        optionOperation: payload,
        variants: editing.optionContext.active_variants || [],
        statuses: {},
      });
      return { guided: true };
    }
    return saveDraft(payload);
  };

  const restoreScrollPosition = (top) => {
    const left = window.scrollX;
    window.requestAnimationFrame(() => window.requestAnimationFrame(() => {
      window.scrollTo({ top, left, behavior: "auto" });
    }));
  };

  const saveDelete = async (row) => {
    if (!dataReady) return null;
    const scrollTop = window.scrollY;
    const key = Object.fromEntries(schema.key.map((k) => [k, String(row[k] ?? "")]));
    const scopedModel = operationModelId(schema, row, modelKey);
    const existing = await api.draftOperations(draftId);
    const priorOperation = (existing.operations || []).find((candidate) => (
      candidate.table_name === table
      && String(candidate.model_id ?? "") === scopedModel
      && Object.keys(key).every((name) => String(candidate.entity_key?.[name] ?? "") === key[name])
    )) || null;
    const operation = await saveDraft({
      table,
      model_id: scopedModel,
      op: "delete",
      key,
    });
    setDeps(null);
    setRawConfirm(null);
    setUndoDelete(operation ? { ...operation, priorOperation } : null);
    setNotice({ kind: "ok", text: "Delete saved to the durable draft. Review the complete graph in Review & Apply." });
    await onChanged();
    restoreScrollPosition(scrollTop);
    return operation;
  };

  const inspectDelete = async (row) => {
    if (!dataReady) return;
    const key = Object.fromEntries(schema.key.map((name) => [name, String(row[name] ?? "")]));
    const scopedModel = operationModelId(schema, row, modelKey);
    try {
      const result = await api.dependencyPlan(table, scopedModel, key, draftId);
      if (result.dependents.length) {
        setDeps({ row, root: { table, model_id: scopedModel, key }, plan: result, selections: {} });
      } else {
        setRawConfirm({ row });
      }
    } catch (e) {
      setNotice({ kind: "err", text: e.message });
    }
  };

  const saveDependencyPlan = async () => {
    const scrollTop = window.scrollY;
    const prepared = dependencyDeletionOperations(
      deps.root, deps.plan.dependents, deps.selections,
    );
    if (!prepared.complete) {
      setNotice({ kind: "err", text: "Choose Delete or Deactivate for every dependent before saving this plan." });
      return;
    }
    try {
      await api.saveDraftOperationPlan(draftId, {
        actor: "workbook-manager-ui", session_id: "browser", operations: prepared.operations,
      });
      setDeps(null);
      setNotice({ kind: "ok", text: "Complete delete plan saved atomically to the durable draft." });
      await onChanged();
      restoreScrollPosition(scrollTop);
    } catch (error) {
      setNotice({ kind: "err", text: error.message });
    }
  };

  const saveGuidedOption = async () => {
    const scrollTop = window.scrollY;
    const prepared = optionCreationPlan(
      guidedOption.optionOperation, guidedOption.variants, guidedOption.statuses,
    );
    if (!prepared.complete) {
      setNotice({ kind: "err", text: `Choose an OVS status for: ${prepared.missing_variant_ids.join(", ")}.` });
      return;
    }
    try {
      await api.saveDraftOperationPlan(draftId, {
        actor: "workbook-manager-ui", session_id: "browser", operations: prepared.operations,
      });
      setGuidedOption(null);
      setEditing(null);
      preserveAdvancedContext({ editor: "" });
      setNotice({ kind: "ok", text: "Option and complete active-variant OVS coverage saved atomically." });
      await loadRows();
      await onChanged();
      restoreScrollPosition(scrollTop);
    } catch (error) {
      setNotice({ kind: "err", text: error.message });
    }
  };

  const undoRawDelete = async () => {
    if (!undoDelete?.id) return;
    const scrollTop = window.scrollY;
    try {
      await api.discardDraftOperation(draftId, undoDelete.id);
      if (undoDelete.priorOperation) {
        const prior = undoDelete.priorOperation;
        await api.saveDraftOperation(draftId, {
          table: prior.table_name,
          model_id: prior.model_id || "",
          op: prior.action,
          key: prior.entity_key,
          record: prior.action === "delete" ? null : prior.final,
          actor: "workbook-manager-ui",
          session_id: "browser",
        });
      }
      setUndoDelete(null);
      setNotice({ kind: "ok", text: "Delete removed from the durable draft." });
      await onChanged();
      restoreScrollPosition(scrollTop);
    } catch (error) {
      setNotice({ kind: "err", text: error.message });
    }
  };

  const saved = async (operation) => {
    if (operation?.guided) return;
    const scrollTop = window.scrollY;
    setNotice({
      kind: "ok",
      text: operation
        ? "Change saved to the durable draft. Review it in Review & Apply."
        : "No effective draft changes remain.",
    });
    await loadRows();
    await onChanged();
    restoreScrollPosition(scrollTop);
  };

  const guidedPlan = guidedOption
    ? optionCreationPlan(guidedOption.optionOperation, guidedOption.variants, guidedOption.statuses)
    : null;

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
            onClick={() => {
              setTable(c.table);
              setOffset(0);
              setSearch("");
              preserveAdvancedContext({
                collection: c.table, query: "", offset: 0, editor: "",
              });
            }}
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
                {previewCols.map((c) => <th key={c.name}>
                  {fieldLabel(c)}
                  <small className="field-technical mono">{schema.table}.{c.name}</small>
                </th>)}
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
                        <span>{r[c.name]}</span>
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
                onClick={() => {
                  const o = Math.max(0, offset - LIMIT);
                  setOffset(o);
                  preserveAdvancedContext({ offset: o });
                  loadRows(table, search, o);
                }}
              >
                ‹ Prev
              </button>
              <button
                className="btn small"
                disabled={!dataReady || offset + LIMIT >= total}
                onClick={() => {
                  const o = offset + LIMIT;
                  setOffset(o);
                  preserveAdvancedContext({ offset: o });
                  loadRows(table, search, o);
                }}
              >
                Next ›
              </button>
            </div>
          )}
        </div>
      </div>

      {notice && <div className={`notice ${notice.kind}`}>{notice.text}</div>}


      {dataReady && editing && schema && !guidedOption && (
        <div style={{ marginTop: 14 }}>
          <RecordForm
            key={`${table}-${editing.mode}-${editing.initial?.id ?? "new"}`}
            schema={schema}
            mode={editing.mode}
            initial={editing.initial}
            modelKey={modelKey}
            saveFn={saveEditorDraft}
            onSaved={saved}
            onCancel={() => {
              setEditing(null);
              setGuidedOption(null);
              preserveAdvancedContext({ editor: "" });
            }}
            evidence={editing.evidence}
          />
        </div>
      )}

      {guidedOption && (
        <div className="panel" style={{ marginTop: 14 }}>
          <div className="panel-head">
            <strong>Set availability for every active variant</strong>
            <button className="btn small" onClick={() => setGuidedOption(null)}>Back</button>
          </div>
          <div className="panel-body">
            <p className="muted">
              No OVS status is assumed. The option and all rows below save together or not at all.
            </p>
            <div className="form-grid">
              {guidedOption.variants.map((variant) => (
                <label key={variant.variant_id}>
                  {variant.display_name} <span className="mono faint">{variant.variant_id}</span>
                  <select
                    value={guidedOption.statuses[variant.variant_id] || ""}
                    onChange={(event) => setGuidedOption((current) => ({
                      ...current,
                      statuses: { ...current.statuses, [variant.variant_id]: event.target.value },
                    }))}
                  >
                    <option value="">Choose OVS status…</option>
                    <option value="standard">Standard</option>
                    <option value="available">Available</option>
                    <option value="unavailable">Unavailable</option>
                  </select>
                </label>
              ))}
            </div>
            <button
              className="btn green"
              onClick={saveGuidedOption}
              disabled={!guidedPlan?.complete}
            >
              Save option + complete OVS plan
            </button>
          </div>
        </div>
      )}

      {rawConfirm && (
        <div className="panel" style={{ marginTop: 14, borderColor: "var(--red)" }}>
          <div className="panel-head"><strong>Confirm delete</strong></div>
          <div className="panel-body">
            <p>No registered dependents were found. Save this delete to the durable draft?</p>
            <div className="toolbar">
              <button className="btn danger" onClick={async () => {
                try { await saveDelete(rawConfirm.row); }
                catch (error) { setNotice({ kind: "err", text: error.message }); }
              }}>
                <Trash2 size={14} /> Confirm delete
              </button>
              <button className="btn" onClick={() => setRawConfirm(null)}>Cancel</button>
            </div>
          </div>
        </div>
      )}

      {undoDelete?.id && (
        <button className="btn small" onClick={undoRawDelete} style={{ marginTop: 10 }}>
          Undo delete
        </button>
      )}

      {deps && (
        <div className="panel" style={{ marginTop: 14, borderColor: "var(--red)" }}>
          <div className="panel-head">
            <strong style={{ color: "var(--red)", display: "flex", gap: 6, alignItems: "center" }}>
              <TriangleAlert size={15} /> Delete plan — {deps.plan.dependents.length} dependent record(s)
            </strong>
            <button className="btn small" onClick={() => setDeps(null)}>Cancel</button>
          </div>
          <div className="panel-body">
            <p className="muted">Nothing is selected automatically. Choose the complete explicit plan.</p>
            <table className="data">
              <thead>
                <tr><th>Relationship</th><th>Record</th><th>Why</th><th>Action</th></tr>
              </thead>
              <tbody>
                {deps.plan.dependents.map((dependent, index) => (
                  <tr key={`${dependent.table}-${JSON.stringify(dependent.entity_key)}`}>
                    <td>{dependent.classification} · {dependent.table}</td>
                    <td className="mono">{Object.values(dependent.entity_key).join(" / ")}</td>
                    <td className="faint">{dependent.why}</td>
                    <td>
                      <select
                        value={deps.selections[String(index)] || "keep"}
                        onChange={(event) => setDeps((current) => ({
                          ...current,
                          selections: { ...current.selections, [String(index)]: event.target.value },
                        }))}
                      >
                        <option value="keep">Keep — plan incomplete</option>
                        <option value="delete">Delete</option>
                        {dependent.allowed_actions.includes("deactivate") && (
                          <option value="deactivate">Deactivate</option>
                        )}
                      </select>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            <p className="muted" style={{ marginTop: 12 }}>
              Incomplete plans stay invalid here, and final-graph preview remains the write authority.
            </p>
            <button
              className="btn danger small"
              disabled={deps.plan.dependents.some((_, index) => !["delete", "deactivate"].includes(deps.selections[String(index)]))}
              onClick={saveDependencyPlan}
            >
              <Trash2 size={14} /> Save complete delete plan
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
