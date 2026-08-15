import React, { useEffect, useMemo, useState } from "react";
import { Check, X } from "lucide-react";
import { api } from "../api.js";
import { humanize } from "../naming.js";

/** Schema-driven add/edit form. Saves durable intent through the API and
 * surfaces field-level validation errors returned by the backend. */
export default function RecordForm({
  schema, mode, initial, modelKey, onSaved, onCancel, saveFn,
}) {
  const [draft, setDraft] = useState(() => {
    const base = {};
    for (const col of schema.columns) base[col.name] = initial?.[col.name] ?? "";
    return base;
  });
  const [errors, setErrors] = useState([]);
  const [busy, setBusy] = useState(false);
  const [referenceOptions, setReferenceOptions] = useState({});
  const [referenceErrors, setReferenceErrors] = useState({});

  const set = (name, value) => setDraft((d) => ({ ...d, [name]: value }));

  const referenceSignature = useMemo(() => JSON.stringify(
    schema.columns
      .filter((column) => column.field_kind === "reference")
      .map((column) => [
        column.name,
        column.reference?.discriminator
          ? draft[column.reference.discriminator]
          : "",
      ])
  ), [schema, draft]);

  useEffect(() => {
    let active = true;
    const loadColumn = async (column) => {
      const reference = column.reference;
      let tables = [];
      if (reference.kind === "union") {
        tables = reference.union;
      } else if (reference.kind === "conditional") {
        const discriminator = draft[reference.discriminator] ?? "";
        const target = reference.targets.find((item) => item.value === discriminator);
        tables = target?.target && !target.derived ? [target.target] : [];
      } else if (reference.table) {
        tables = [reference.table];
      }
      const values = [];
      for (const table of tables) {
        const targetSchema = await api.schema(table, modelKey);
        const response = await api.records(table, {
          model: reference.scope === "global" ? "" : modelKey,
          limit: 2000,
        });
        const valueColumn = reference.kind === "union"
          ? targetSchema.key[0]
          : (reference.column || targetSchema.key[0]);
        for (const row of response.records) {
          const value = row[valueColumn];
          if (value !== null && value !== undefined && String(value) !== "") {
            values.push(String(value));
          }
        }
      }
      return [...new Set(values)].sort((a, b) => a.localeCompare(b));
    };
    (async () => {
      const next = {};
      const nextErrors = {};
      await Promise.all(schema.columns
        .filter((column) => column.field_kind === "reference")
        .map(async (column) => {
          try {
            next[column.name] = await loadColumn(column);
          } catch (e) {
            next[column.name] = [];
            nextErrors[column.name] = e.message;
          }
        }));
      if (active) {
        setReferenceOptions(next);
        setReferenceErrors(nextErrors);
      }
    })();
    return () => { active = false; };
  }, [schema, modelKey, referenceSignature]); // eslint-disable-line

  const submit = async () => {
    setBusy(true);
    setErrors([]);
    try {
      const key = {};
      for (const k of schema.key) {
        key[k] = mode === "edit" ? String(initial?.[k] ?? "") : String(draft[k] ?? "");
      }
      const operation = await saveFn({
        table: schema.table,
        model_id: schema.model_context?.required
          ? (schema.model_context.value || modelKey)
          : "",
        op: mode === "edit" ? "update" : "add",
        key,
        record: draft,
      });
      onSaved(operation);
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
                {col.field_kind === "finite" ? (
                  <select
                    className="select"
                    value={draft[col.name] ?? ""}
                    onChange={(e) => set(col.name, e.target.value)}
                    disabled={isKey && mode === "edit"}
                  >
                    {(["", ...col.finite_values.filter((value) => value !== "")]).map(
                      (v) => (
                        <option key={v} value={v}>
                          {v === "" ? (col.optional ? "(blank / SQL NULL)" : "(select)") : v}
                        </option>
                      )
                    )}
                  </select>
                ) : col.field_kind === "reference" ? (
                  <select
                    className="select"
                    value={draft[col.name] ?? ""}
                    onChange={(e) => set(col.name, e.target.value)}
                    disabled={isKey && mode === "edit"}
                  >
                    <option value="">
                      {col.optional ? "(blank / SQL NULL)" : "(select reference)"}
                    </option>
                    {draft[col.name] && !referenceOptions[col.name]?.includes(String(draft[col.name])) && (
                      <option value={draft[col.name]}>{draft[col.name]} (current)</option>
                    )}
                    {(referenceOptions[col.name] || []).map((value) => (
                      <option key={value} value={value}>{value}</option>
                    ))}
                  </select>
                ) : col.name === "setup_description" ? (
                  <textarea
                    className="text"
                    rows="3"
                    value={draft[col.name] ?? ""}
                    onChange={(e) => set(col.name, e.target.value)}
                    disabled={isKey && mode === "edit"}
                  />
                ) : (
                  <input
                    className="text"
                    value={draft[col.name] ?? ""}
                    onChange={(e) => set(col.name, e.target.value)}
                    disabled={isKey && mode === "edit"}
                    placeholder={isKey ? "required key" : col.ctype === "int" ? "number" : ""}
                  />
                )}
                {col.reference && (
                  <div className="ref-hint">
                    → {col.reference.kind === "union"
                      ? col.reference.union.join(" | ")
                      : col.reference.kind === "conditional"
                        ? `selected by ${col.reference.discriminator}`
                        : col.reference.table}
                    {col.reference.scope && col.reference.scope !== "global" ? ` (${modelKey})` : ""}
                  </div>
                )}
                {referenceErrors[col.name] && (
                  <div className="notice err">Reference choices unavailable: {referenceErrors[col.name]}</div>
                )}
                {col.optional && <div className="ref-hint">Blank is stored as SQL NULL.</div>}
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
            <Check size={15} /> {mode === "edit" ? "Save Update to Draft" : "Save Add to Draft"}
          </button>
          <button className="btn" onClick={onCancel}>Cancel</button>
          <span className="muted">
            Draft changes remain durable and do not alter the projection or workbook.
          </span>
        </div>
      </div>
    </div>
  );
}
