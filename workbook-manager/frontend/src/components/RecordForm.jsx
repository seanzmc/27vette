import React, { useState } from "react";
import { Check, X } from "lucide-react";
import { humanize } from "../naming.js";
import { fieldInputValue } from "../tableRegistry.js";

/** Schema-driven add/edit form. Stages the change through the API and
 * surfaces field-level validation errors returned by the backend. */
export default function RecordForm({
  schema, mode, initial, modelKey, onStaged, onCancel, stageFn,
}) {
  const [draft, setDraft] = useState(() => {
    const base = {};
    for (const col of schema.columns) {
      base[col.name] = fieldInputValue(col, initial?.[col.name]);
    }
    return base;
  });
  const [errors, setErrors] = useState([]);
  const [busy, setBusy] = useState(false);

  const set = (name, value) => setDraft((d) => ({ ...d, [name]: value }));

  const submit = async () => {
    setBusy(true);
    setErrors([]);
    try {
      const key = {};
      for (const k of schema.key) {
        key[k] = mode === "edit" ? String(initial?.[k] ?? "") : String(draft[k] ?? "");
      }
      await stageFn({
        model_key: modelKey,
        table_role: schema.table_role,
        op: mode === "edit" ? "update" : "add",
        key,
        record: draft,
      });
      onStaged();
    } catch (e) {
      setErrors(e.detail?.errors || [{ message: e.message, field: "" }]);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="panel" style={{ borderColor: "var(--accent)" }}>
      <div className="panel-head">
        <strong style={{ color: "var(--accent)" }}>
          {mode === "edit" ? "Edit" : "Add"} — {schema.label}
          {schema.sheet_for_model && (
            <span className="mono faint" style={{ marginLeft: 8 }}>
              → {schema.sheet_for_model}
            </span>
          )}
        </strong>
        <button className="icon-btn" onClick={onCancel}><X size={16} /></button>
      </div>
      <div className="panel-body">
        <div className="form-grid">
          {schema.columns.map((col) => {
            const isKey = col.is_key;
            const err = errors.find((e) => e.field === col.name);
            return (
              <div className="field" key={col.name}>
                <label>
                  {isKey ? <span className="key">{col.label} *</span> : col.label}
                </label>
                {col.enum.length > 0 ? (
                  <select
                    className="select"
                    value={draft[col.name] ?? ""}
                    onChange={(e) => set(col.name, e.target.value)}
                    disabled={isKey && mode === "edit"}
                  >
                    {(col.enum.includes("") ? col.enum : ["", ...col.enum]).map(
                      (v) => (
                        <option key={v} value={v}>{v === "" ? "(blank)" : v}</option>
                      )
                    )}
                  </select>
                ) : col.ctype === "bool" ? (
                  <select
                    className="select"
                    value={draft[col.name] ?? ""}
                    onChange={(e) => set(col.name, e.target.value)}
                    disabled={isKey && mode === "edit"}
                  >
                    <option value="">(blank)</option>
                    <option value="True">True</option>
                    <option value="False">False</option>
                  </select>
                ) : (
                  <input
                    className="text"
                    value={draft[col.name] ?? ""}
                    onChange={(e) => set(col.name, e.target.value)}
                    disabled={isKey && mode === "edit"}
                    placeholder={isKey ? "required key" : col.ctype === "int" ? "number" : ""}
                  />
                )}
                {col.ref && (
                  <div className="ref-hint">
                    → {col.ref.scope === "model_union"
                      ? col.ref.union.join(" | ")
                      : col.ref.table}
                    {col.ref.scope !== "global" ? ` (${modelKey})` : ""}
                  </div>
                )}
                {err && <div className="notice err">{err.message}</div>}
              </div>
            );
          })}
        </div>
        {errors.filter((e) => !schema.columns.some((c) => c.name === e.field))
          .map((e, i) => (
            <div key={i} className="notice err">{e.message}</div>
          ))}
        <div className="toolbar" style={{ marginTop: 14 }}>
          <button className="btn primary" onClick={submit} disabled={busy}>
            <Check size={15} /> {mode === "edit" ? "Stage Update" : "Stage Add"}
          </button>
          <button className="btn" onClick={onCancel}>Cancel</button>
          <span className="muted">
            Staged changes stay out of the database until you validate &
            commit them in Changes &amp; Sync.
          </span>
        </div>
      </div>
    </div>
  );
}
